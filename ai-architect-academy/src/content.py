"""课程内容存储与生成 —— 离线优先，token 仅用于"系统更新"。

设计原则（硬约束）：
- 学习过程 100% 离线、零 token：课程正文 + 测验 + 考试题目都来自
  content/ 目录下的本地 JSON 文件（由种子内容 + DeepSeek 更新生成后缓存）。
- DeepSeek 只在用户显式执行"更新/生成内容"命令时被调用，结果写回本地文件，
  之后照常离线读取。这样 token 只在"系统更新"时消耗一次。

content/ 目录结构：
  content/lessons/{lesson_id}.json   每节课正文 + 随堂测验
  content/exams/{exam_id}.json       单元考(s1u1) / 期末考(s1-final)
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

DEEPSEEK_API_URL = os.environ.get("DEEPSEEK_API_URL", "https://api.deepseek.com/chat/completions")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")


@dataclass(frozen=True)
class Question:
    question: str
    options: tuple[str, ...]
    answer: int  # 正确选项下标（从 0 开始）


@dataclass(frozen=True)
class LessonContent:
    id: str
    title: str
    kps: tuple[str, ...]
    theory: str  # markdown 正文
    quiz: tuple[Question, ...]


@dataclass(frozen=True)
class ExamContent:
    id: str
    kind: str  # unit | final
    title: str
    questions: tuple[Question, ...]


def _q_from_dict(d: dict) -> Question:
    return Question(
        question=d["question"],
        options=tuple(d.get("options", [])),
        answer=int(d["answer"]),
    )


def _lesson_from_dict(d: dict) -> LessonContent:
    return LessonContent(
        id=d["id"],
        title=d.get("title", d["id"]),
        kps=tuple(d.get("kps", [])),
        theory=d.get("theory", ""),
        quiz=tuple(_q_from_dict(q) for q in d.get("quiz", [])),
    )


def _exam_from_dict(d: dict) -> ExamContent:
    return ExamContent(
        id=d["id"],
        kind=d.get("kind", "unit"),
        title=d.get("title", d["id"]),
        questions=tuple(_q_from_dict(q) for q in d.get("questions", [])),
    )


def _placeholder_lesson(lesson_id: str, kps: tuple[str, ...]) -> LessonContent:
    """内容缺失时的离线兜底：给出课程骨架，提示用 update 命令生成正文。"""
    theory = (
        f"# {lesson_id}\n\n"
        f"知识点：{', '.join(kps)}\n\n"
        "> 本节正文尚未生成。运行 `python -m src.cli update` 可调用 DeepSeek 生成完整内容。\n"
    )
    quiz = (Question("本节内容尚未生成，占位题：请选择 A", ("A", "B"), 0),)
    return LessonContent(id=lesson_id, title=lesson_id, kps=kps, theory=theory, quiz=quiz)


class ContentStore:
    """从本地 content/ 目录加载课程内容，缺文件时返回占位。"""

    def __init__(self, content_dir: Path | str):
        self.root = Path(content_dir)
        self.lessons_dir = self.root / "lessons"
        self.exams_dir = self.root / "exams"

    def has_lesson(self, lesson_id: str) -> bool:
        return (self.lessons_dir / f"{lesson_id}.json").exists()

    def has_exam(self, exam_id: str) -> bool:
        return (self.exams_dir / f"{exam_id}.json").exists()

    def lesson(self, lesson_id: str, kps: tuple[str, ...] = ()) -> LessonContent:
        path = self.lessons_dir / f"{lesson_id}.json"
        if path.exists():
            return _lesson_from_dict(json.loads(path.read_text(encoding="utf-8")))
        return _placeholder_lesson(lesson_id, kps)

    def exam(self, exam_id: str, kind: str = "unit") -> ExamContent:
        path = self.exams_dir / f"{exam_id}.json"
        if path.exists():
            return _exam_from_dict(json.loads(path.read_text(encoding="utf-8")))
        return ExamContent(id=exam_id, kind=kind, title=exam_id, questions=())

    def save_lesson(self, content: LessonContent) -> None:
        self.lessons_dir.mkdir(parents=True, exist_ok=True)
        (self.lessons_dir / f"{content.id}.json").write_text(
            json.dumps(
                {
                    "id": content.id,
                    "title": content.title,
                    "kps": list(content.kps),
                    "theory": content.theory,
                    "quiz": [
                        {"question": q.question, "options": list(q.options), "answer": q.answer}
                        for q in content.quiz
                    ],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def save_exam(self, content: ExamContent) -> None:
        self.exams_dir.mkdir(parents=True, exist_ok=True)
        (self.exams_dir / f"{content.id}.json").write_text(
            json.dumps(
                {
                    "id": content.id,
                    "kind": content.kind,
                    "title": content.title,
                    "questions": [
                        {"question": q.question, "options": list(q.options), "answer": q.answer}
                        for q in content.questions
                    ],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )


# ---------------------------------------------------------------------------
# DeepSeek 生成器 —— 仅在"系统更新"时调用（消耗 token）
# ---------------------------------------------------------------------------

class DeepSeekGenerator:
    """用 DeepSeek Chat Completions 生成课程正文/题目。

    不引入第三方库，直接用 urllib 发 HTTP 请求。
    API key 从环境变量 DEEPSEEK_API_KEY 读取，未设置则抛错。
    """

    def __init__(self, api_key: str | None = None, *, model: str = DEEPSEEK_MODEL, url: str = DEEPSEEK_API_URL):
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise RuntimeError("未设置 DEEPSEEK_API_KEY 环境变量，无法调用 DeepSeek")
        self.model = model
        self.url = url

    def _chat(self, system: str, user: str, max_tokens: int = 4096) -> str:
        import urllib.request

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": max_tokens,
            "temperature": 0.3,
        }
        req = urllib.request.Request(
            self.url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]

    def generate_lesson(self, lesson_id: str, kps: tuple[str, ...]) -> LessonContent:
        """生成一节课：markdown 正文 + 3 道随堂测验，并要求输出 JSON。"""
        system = (
            "你是资深 Python 与 AI 架构师讲师。只输出合法 JSON，不要 markdown 代码块围栏，"
            '格式：{"title": str, "theory": markdown字符串, "quiz": [{"question": str, "options": [str,...], "answer": int}]}。'
            "quiz 固定 4 道单选题，answer 为正确选项下标。theory 需完整覆盖给出的知识点，面向初学者循序渐进。"
        )
        user = f"课程 ID：{lesson_id}\n知识点：{', '.join(kps)}\n请生成这节课的完整教学内容。"
        raw = self._chat(system, user)
        data = json.loads(raw)
        data["id"] = lesson_id
        data["kps"] = list(kps)
        return _lesson_from_dict(data)

    def generate_exam(self, exam_id: str, kind: str, scope: str) -> ExamContent:
        """生成一场考试（unit 8 题 / final 20 题）。"""
        n = 20 if kind == "final" else 8
        system = (
            "你是资深 Python 与 AI 架构师讲师。只输出合法 JSON，不要 markdown 代码块围栏，"
            f'格式：{{"title": str, "questions": [{{"question": str, "options": [str,...], "answer": int}}]}}。'
            f"questions 固定 {n} 道单选题，answer 为正确选项下标，覆盖给出的知识点范围。"
        )
        user = f"考试 ID：{exam_id}（{kind}）\n考察范围：{scope}\n请生成这套考试题。"
        raw = self._chat(system, user)
        data = json.loads(raw)
        data["id"] = exam_id
        data["kind"] = kind
        return _exam_from_dict(data)
