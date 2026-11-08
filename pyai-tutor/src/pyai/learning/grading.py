"""规则判分引擎 —— 0 token 判客观题。

支持题型：single_choice / multi_choice / fill_blank / code_reading / scenario。
多选有部分分；填空做归一化；场景题按 required_keywords 命中率打分。
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass
class Grade:
    correct: bool
    score: float
    error_type: str | None = None
    feedback: str = ""


def _normalize(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[，。；！？,.;!?]", "", s)
    return s


# code_reading 的「采分点」：标准答案里的硬信息——引号内字面量、数字、标识符、
# 长度≥4 的英文词。中文虚词与解释性长句不进 token 表，所以「写满 50 字但什么都没说中」
# 拿不到分，而「说中了输出和关键变量」就能拿到。
_TOKEN_STOP = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "in", "on", "of",
    "to", "for", "and", "or", "not", "it", "this", "that", "with", "as", "at",
    "by", "from", "if", "then", "else", "but", "so", "you", "we", "i", "will",
    "can", "no", "yes", "do", "does", "did", "have", "has", "had", "output",
    "print", "result", "value", "type", "code",
}
_TOKEN_QUOTED = re.compile(r"'([^']{1,40})'|\"([^\"]{1,40})\"")
_TOKEN_NUM = re.compile(r"\d+(?:\.\d+)?")
_TOKEN_IDENT = re.compile(r"[A-Za-z_][A-Za-z_0-9]*(?:\.[A-Za-z_0-9]+)*")

# 采分点覆盖到这个比例算通过。实测 444 道能抽出采分点的真实 code_reading：
# 标准答案自身 100% 通过；「随便写一点内容凑够十二个字」这类敷衍 0% 通过。
# 但整段比会误杀「只答对了输出」的认真作答（只有 46% 过），所以另加两条宽松口子
# 见 _code_reading_score。
_CODE_READING_PASS = 0.6
# 只写出输出值也算过：题目问的就是「输出是什么」，答对了核心事实。
_OUTPUT_PASS = 0.7


def _hard_tokens(answer: str) -> list[str]:
    """从标准答案里抽采分点（去重、保序、小写）。"""
    out: list[str] = []
    seen: set[str] = set()

    def add(token: str) -> None:
        token = token.strip().lower()
        if token and token not in seen and token not in _TOKEN_STOP:
            seen.add(token)
            out.append(token)

    for m in _TOKEN_QUOTED.finditer(answer):
        add(m.group(1) or m.group(2))
    for m in _TOKEN_NUM.finditer(answer):
        add(m.group(0))
    for m in _TOKEN_IDENT.finditer(answer):
        tok = m.group(0)
        if tok.isupper() or "_" in tok or "." in tok or any(c.isupper() for c in tok[1:]):
            add(tok)
        elif len(tok) >= 4:
            add(tok)
    return out


def _coverage(tokens: list[str], text: str) -> float | None:
    """tokens 在已归一化文本里的命中率；token 也要归一化（答案里常带标点）。"""
    if not tokens:
        return None
    hit = sum(1 for t in tokens if _normalize(t) and _normalize(t) in text)
    return hit / len(tokens)


def _first_sentence(s: str) -> str:
    return re.split(r"[。；\n]", s.strip())[0].strip() or s.strip()


def _output_literals(s: str) -> list[str]:
    """首句里的输出值（数字 / 引号内字面量）——code_reading 问的多半就是这些。"""
    seen: set[str] = set()
    out: list[str] = []
    quoted = [a or b for a, b in _TOKEN_QUOTED.findall(s)]
    for v in quoted + _TOKEN_NUM.findall(s):
        v = v.strip()
        if v and v.lower() not in seen:
            seen.add(v.lower())
            out.append(v)
    return out


def _code_reading_score(answer: str, raw: str, stem: str = "") -> tuple[float, str]:
    """按采分点覆盖度给 code_reading 打分，返回 (score, feedback)。"""
    text = _normalize(raw)
    tokens = _hard_tokens(answer)
    if not tokens:
        # 抽不出采分点的只有极短答案（'e' / '[]' / '中' 这类「输出就是这一个字」的题，
        # 实测 6 道）。整段答案本身就是唯一采分点，别退化成数长度——
        # 那样标准答案 'e' 自己都判不过。
        core = _normalize(answer)
        if not core:
            return 0.0, "答案太短，请写出你的推理"
        hit = 1.0 if core in text else 0.0
        return (round(hit, 3), "" if hit else f"输出应该是「{answer}」，再想想为什么")
    # ① 整段采分点覆盖
    whole = _coverage(tokens, text) or 0.0
    # ② 首句（通常就是「输出是什么」）覆盖——只答核心事实也该算对
    core = _coverage(_hard_tokens(_first_sentence(answer)), text) or 0.0
    score = max(whole, core)
    # 反抄题：整段答案直接是题干的一部分，等于把题目念了一遍。
    # 题干里的代码本来就含答案字面量（'abcdef' 里就有 'e'），不拦的话抄题干 72% 能过。
    # ponytail: 只拦「整段照抄」，抄一半改写一半仍可能蒙过；升级路径 = 前端把题干代码
    # 遮起来让学习者先自己写答案。
    if stem and len(text) >= 12 and text in _normalize(stem):
        return 0.0, "这是题目原文，请写出你自己的推理和输出结果"
    if score >= _CODE_READING_PASS:
        return round(score, 3), ""
    # ③ 输出值兜底：题目问输出，值答对了就是答对了
    outputs = _output_literals(_first_sentence(answer))
    hit_out = _coverage(outputs, text) if outputs else None
    if hit_out is not None and hit_out >= _OUTPUT_PASS:
        return round(max(score, _CODE_READING_PASS), 3), ""
    hit = sum(1 for t in tokens if _normalize(t) and _normalize(t) in text)
    return round(score, 3), (f"说到了 {hit}/{len(tokens)} 个采分点，"
                             f"把代码的输出和关键变量讲清楚")


def grade(question: dict, user_answer: Any) -> Grade:
    qtype = question.get("type", "single_choice")

    if qtype == "single_choice":
        ok = str(user_answer) == str(question.get("answer"))
        return Grade(ok, 1.0 if ok else 0.0,
                     None if ok else question.get("error_tag", "概念混淆"))

    if qtype == "multi_choice":
        # 容错：前端偶尔送来标量（只勾一项却交成 int）或 None。set(int) 会抛 TypeError
        # 并把整份卷子的提交打挂，所以先归一成列表。
        if user_answer is None:
            picked: list = []
        elif isinstance(user_answer, (list, tuple, set)):
            picked = list(user_answer)
        else:
            picked = [user_answer]
        ans = set(picked)
        ref = set(question.get("answer") or [])
        if not ans:
            return Grade(False, 0.0, question.get("error_tag", "概念混淆"), "未作答")
        if ans == ref:
            return Grade(True, 1.0)
        hit = len(ans & ref)
        wrong = len(ans - ref)
        miss = len(ref - ans)
        score = max(0.0, (hit - wrong) / max(1, len(ref)))
        return Grade(False, score, question.get("error_tag", "概念混淆"),
                     f"少选 {miss} 项，多选 {wrong} 项")

    if qtype == "fill_blank":
        norm = _normalize(str(user_answer))
        accepted = [_normalize(a) for a in question.get("answer", [])]
        ok = norm in accepted
        return Grade(ok, 1.0 if ok else 0.0,
                     None if ok else "记忆缺失")

    if qtype == "code_reading":
        # 曾经是 `user_answer == answer` 的整串比对，而 answer 是一整段自然语言
        # （「会安装到用户级 site-packages……因为使用了 --user……」），逐字复述不可能，
        # 这类题成了**永远打不赢的题**：Boss 卷子里抽到 1 道就够不到 85% 通关线。
        #
        # 还有第二层坑：前端把带 options 的 code_reading 渲染成**单选按钮**（交下标），
        # 不带 options 才渲染成输入框（交文字）。所以两种作答都必须能判。
        ref = question.get("required_keywords") or []
        answer = question.get("answer")
        options = question.get("options") or []

        # ① 交的是选项下标 → 按单选处理
        if options and isinstance(user_answer, int) and not isinstance(user_answer, bool):
            if answer is not None and not isinstance(answer, str) and str(user_answer) == str(answer):
                return Grade(True, 1.0)
            if user_answer < 0:
                return Grade(False, 0.0, "理解偏差", "未作答")
            return Grade(False, 0.0, question.get("error_tag", "理解偏差"))

        raw = str(user_answer or "").strip()
        if not raw:
            return Grade(False, 0.0, "理解偏差", "未作答")
        if isinstance(answer, str) and _normalize(answer) == _normalize(raw):
            return Grade(True, 1.0)                      # 逐字复述当然算对
        if ref:
            text = _normalize(raw)
            hit = sum(1 for k in ref if _normalize(str(k)) and _normalize(str(k)) in text)
            score = hit / max(1, len(ref))
            return Grade(score >= 0.7, score,
                         None if score >= 0.7 else "理解偏差",
                         "" if score >= 0.7 else f"说到了 {hit}/{len(ref)} 个要点")
        # 无 required_keywords 时（题库里 486 道 code_reading 全是这种情况），
        # 拿标准答案自己抽采分点，看用户说中了多少。以前这里只数「够不够 12 个字」，
        # 于是「随便写一点内容凑够十二个字」也能满分。
        score, feedback = _code_reading_score(answer, raw, str(question.get("stem") or ""))
        ok = score >= _CODE_READING_PASS
        return Grade(ok, score,
                     None if ok else "理解偏差",
                     "" if ok else feedback)

    if qtype == "scenario":
        keys = question.get("required_keywords", [])
        hit = sum(1 for k in keys if k.lower() in str(user_answer).lower())
        score = hit / max(1, len(keys))
        return Grade(score >= 0.7, score,
                     None if score >= 0.7 else "理解偏差")

    return Grade(False, 0.0, "未知题型")


def grade_quiz(questions: list[dict], answers: list) -> list[Grade]:
    """批量判分。answers 与 questions 按下标对齐，缺省按 0 分。"""
    grades = []
    for i, q in enumerate(questions):
        ans = answers[i] if i < len(answers) else None
        grades.append(grade(q, ans))
    return grades


def quiz_score(grades: list[Grade]) -> float:
    """平均分 0..1。"""
    if not grades:
        return 0.0
    return sum(g.score for g in grades) / len(grades)


def model_answer(question: dict):
    """该题的「满分作答」——模拟全对时用它，不要直接用 question['answer']。

    answer 的含义随题型变化，一把梭会造出「全对却不及格」的假故障：
      - multi_choice：answer 是**选中项下标**数组 → 原样交（只交第一项会被判「少选」）。
      - fill_blank  ：answer 是**可接受答案**的字符串数组 → 取第一项（整串交必然判错）。
      - scenario    ：没有 answer，按 required_keywords 命中率判分 → 把关键词全写进去。
      - 其余        ：answer 就是标准答案本身。
    """
    qtype = question.get("type")
    answer = question.get("answer")
    if qtype == "multi_choice":
        return list(answer or [])
    if qtype == "scenario":
        return "；".join(question.get("required_keywords") or [])
    if isinstance(answer, list):
        return answer[0] if answer else ""
    return answer


def passed(score: float, threshold: float = 0.75) -> bool:
    return score >= threshold
