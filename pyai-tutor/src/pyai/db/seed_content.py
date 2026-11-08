"""课程种子内容 —— 把 content/lessons/*.json 的讲义与测验写入 kp_content + questions。

离线 0 token：随发行版提供的起步内容，保证"从 Python 基础第一课开始"开箱即可学习。
后续正文由 updater 管道生成，落在同样这两张表，学习路径无需改动。

种子文件格式（与 v1 一致）：
    {"id", "title", "kps": [kp_id...], "theory": markdown, "quiz": [{question, options, answer}]}
theory 每个 KP 一节，节首是 `## <kp_id>` 标记（export_content 写出的就是它）；
找不到这种标记时（v1 手写种子）退回按 `## ` 标题切、第 i 节对应第 i 个 KP。
题目按顺序挂到 KP 上（循环），题自带 `kp` 字段时以它为准。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

_FENCE = re.compile(r"```[a-zA-Z0-9]*[ \t]*\n(.*?)```", re.DOTALL)
_HEADING = re.compile(r"^##\s+", re.MULTILINE)


def _split_by_kp(theory: str, kp_ids: list[str]) -> list[str] | None:
    """按 `## <kp_id>` 标记精确切分；标记不全时返回 None 让调用方回退。

    为什么不能只按 `## ` 切：讲义正文自己就带 `## 一句话直觉` 这类小节
    （385 篇里 378 篇都有），切出来节数是 KP 数的好几倍，对不上号后又退化成
    「每个 KP 都拿整课」——学生点开第一节却看到一整课的内容。
    标记用 kp_id 而不是中文标题，因为 kp_id 唯一、机器生成，不会与正文标题撞车。
    """
    marks = []
    for kp_id in kp_ids:
        m = re.search(rf"^##\s+{re.escape(kp_id)}\s*$", theory, re.MULTILINE)
        if not m:
            return None
        marks.append(m)
    return [
        theory[m.end():(marks[i + 1].start() if i + 1 < len(marks) else len(theory))].strip()
        for i, m in enumerate(marks)
    ]


def _split_sections(theory: str, kp_ids: list[str] | None = None) -> list[str]:
    """按 KP 标记切分讲义；没有标记则按 `## ` 标题切；连标题都没有就整体算一节。"""
    if kp_ids:
        by_kp = _split_by_kp(theory, kp_ids)
        if by_kp is not None:
            return by_kp
    starts = [m.start() for m in _HEADING.finditer(theory)]
    if not starts:
        return [theory.strip()] if theory.strip() else []
    return [
        theory[s:(starts[i + 1] if i + 1 < len(starts) else len(theory))].strip()
        for i, s in enumerate(starts)
    ]


def _split_code(md: str) -> tuple[str, str]:
    """拆出围栏代码块：返回 (正文, 代码拼接)。"""
    codes = [c.strip() for c in _FENCE.findall(md)]
    return _FENCE.sub("", md).strip(), "\n\n".join(codes)


def _to_question(q: dict, kp_id: str, i: int) -> dict:
    """种子题 → v2 题库结构。

    必须原样带过 type/explanation/error_tag/variant_group/required_keywords：
    早先只映射 {question, options, answer}，type 被默认成 single_choice，
    导出再回读时四种题型就全退化了（实测 7786 道全变成单选）。
    """
    return {
        "id": f"{kp_id}-seed{i}",
        "type": q.get("type", "single_choice"),
        "difficulty": q.get("difficulty", 1),
        "stem": q.get("question") or q.get("stem", ""),
        "options": q.get("options", []),
        "answer": q.get("answer"),
        "explanation": q.get("explanation", ""),
        "error_tag": q.get("error_tag", "概念混淆"),
        "variant_group": q.get("variant_group", ""),
        "required_keywords": q.get("required_keywords", []),
    }


def seed_content(db, content_dir: Path | str) -> dict:
    """读取 content/lessons/*.json 写入 kp_content + questions。

    只补空缺，不覆盖已有：种子的职责是"开箱即可学"，不是真理来源。
    update 管道烧 token 生成的讲义与题库优先于种子——若这里无脑覆盖，
    每次启动 Orchestrator（上课/开 Web/跑 CLI）都会把生成结果打回种子原样。
    已是种子自身的 KP 可被种子文件更新（便于修订 content/lessons/*.json）。
    """
    lessons_dir = Path(content_dir) / "lessons"
    n_kp = n_q = n_lessons = 0
    for path in sorted(lessons_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        kp_ids = data.get("kps") or []
        if not kp_ids:
            continue
        n_lessons += 1

        sections = _split_sections(data.get("theory", ""), kp_ids)
        if len(sections) == len(kp_ids):
            per_kp = dict(zip(kp_ids, sections))
        else:  # 节数与 KP 数不符 → 整篇给每个 KP，避免空内容
            whole = data.get("theory", "")
            per_kp = {kp: whole for kp in kp_ids}
        for kp_id, section in per_kp.items():
            if db.kp_content_source(kp_id) == "generated":
                continue                      # 生成内容优先，种子不覆盖
            prose, code = _split_code(section)
            db.save_kp_content(kp_id, explain=prose, example_code=code, source="seed")
            n_kp += 1

        by_kp: dict[str, list] = {}
        for i, q in enumerate(data.get("quiz") or []):
            # 题自带 `kp` 时以它为准（种子文件的题序与 KP 序并不一致）；否则按序回退。
            kp_id = q.get("kp") or kp_ids[i % len(kp_ids)]
            if kp_id not in kp_ids:
                kp_id = kp_ids[i % len(kp_ids)]
            by_kp.setdefault(kp_id, []).append(_to_question(q, kp_id, i))
        for kp_id, questions in by_kp.items():
            if db.kp_quiz_source(kp_id) == "generated":
                continue                      # 生成题库优先，种子不覆盖
            db.save_questions(kp_id, questions, source="seed")
            n_q += len(questions)
    return {"lessons": n_lessons, "kps": n_kp, "questions": n_q}
