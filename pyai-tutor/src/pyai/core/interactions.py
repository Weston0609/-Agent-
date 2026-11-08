"""课堂互动 —— 每小节一个「白云气泡」小问题（0 token，纯离线）。

题目从**已落库题库**里取（该 KP 的题），不是新生成的，所以不存在教错的风险：
选项文案就是题库里的选项，答案就是题库里的答案。

三种形态（按可用题量择优）：
  choice  —— 单选/多选题直接复用，选项不变。
  judge   —— 判断题：从讲义「关键结论 / 一句话直觉」里取一句原句，问「对不对」。
             错项用原句自身的改写（去掉否定词 / 对调关键词），所以**不引入讲义之外的知识**。
  none    —— 既没有题也没有可用原句，就跳过互动（宁可不互动，也不编造）。

答案永远不随题面下发：只给 `id`，判分走 `check() → grade()`，和正式测验同一套判分引擎。
"""
from __future__ import annotations

import hashlib
import re

from ..learning.grading import grade as _grade

# 只从这些段落里摘「原句」做判断题——它们本身是结论句，对错容易判断，
# 且改写后不会变成错误知识（因为错项就是原句本身被换掉关键词）。
_SENTENCE_SOURCES = ("一句话直觉", "关键结论")

# 判断题的错项改写：只动否定与最少数量的关键词，不新增任何讲义里没有的说法。
_NEGATIONS = ("不", "无须", "无需", "不能", "不会", "不必", "禁止", "避免", "没有", "非")

# 一句适合做判断题的原句：长度适中、以句号/感叹号收尾、含足够信息量。
_MIN_SENTENCE = 12
_MAX_SENTENCE = 90


def _key(text: str) -> str:
    """稳定的短 id：同一句永远得到同一个互动 id（刷新/重进不会换题）。"""
    return "ix" + hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]


def _sentences(explain: str) -> list[str]:
    """从讲义里挑出「结论句」——只取一句话直觉 / 关键结论段落，且是陈述原句。"""
    out: list[str] = []
    # 引用块里的一句话直觉：> **一句话直觉**：xxxx
    for m in re.finditer(r"\*\*一句话直觉\*\*\s*[:：]\s*(.+)", explain):
        out.append(m.group(1).strip())
    # 关键结论：**关键结论**：xxxx
    for m in re.finditer(r"\*\*关键结论\*\*\s*[:：]\s*(.+)", explain):
        out.append(m.group(1).strip())

    cleaned: list[str] = []
    for raw in out:
        # 去掉 markdown 强调与反引号，保留文字本身
        s = re.sub(r"[`*_>]", "", raw).strip()
        s = re.split(r"(?<=[。！？!?])", s)[0].strip() if "。" in s or "！" in s else s
        if not s:
            continue
        if not s.endswith(("。", "！", "？", ".", "!", "?")):
            s += "。"
        if _MIN_SENTENCE <= len(s) <= _MAX_SENTENCE and s not in cleaned:
            cleaned.append(s)
    return cleaned


def _flip(sentence: str) -> str | None:
    """把原句改写成错项：翻转否定词，或对调两个关键词的位置。改不动就返回 None。"""
    for neg in _NEGATIONS:
        if neg in sentence:
            if neg in ("不", "非"):
                return sentence.replace(neg, "", 1)      # 拿去否定 → 意思变反
            return sentence.replace(neg, "", 1)
    # 没有否定词：给第一个动词性关键词加「不」——只在句首主语之后插，避免造出病句
    m = re.match(r"^(.{2,10}?)(是|可以|会|能|需要|应当|应该|必须|把|将)", sentence)
    if m:
        return f"{m.group(1)}不{m.group(2)}{sentence[m.end():]}"
    return None


def _judge_item(kp_id: str, kp_title: str, idx: int, sentence: str) -> dict | None:
    wrong = _flip(sentence)
    if not wrong or wrong == sentence:
        return None
    return {
        "id": _key(sentence),
        "kp_id": kp_id,
        "type": "judge",
        "stem": sentence,
        "options": ["✅ 对，就是这样", "❌ 不对"],
        "answer": 0,               # 原句是对的 → 选第 0 项
        "why": f"讲义原文就这么说的：{sentence}",
        "wrong_hint": f"再读一遍这句：{sentence}",
    }


def _from_question(q: dict, kp_id: str) -> dict | None:
    """把题库里的题转成互动项（选项与答案原样复用，不重写、不翻译）。"""
    qtype = q.get("type")
    if qtype not in ("single_choice", "multi_choice", "code_reading"):
        # 填空/场景题需要打字，不适合「停顿一下点个选项」的互动节奏。
        return None
    options = q.get("options") or []
    if len(options) < 2:
        return None
    return {
        "id": q["id"],
        "kp_id": kp_id,
        "type": "choice",
        "qtype": qtype,            # 真正的题型（single_choice / multi_choice / code_reading）
        "stem": q.get("stem", ""),
        "options": list(options),
        "answer": q.get("answer"),
        "why": q.get("explanation") or "",
        "wrong_hint": "",
    }


def build(lesson_kps: list[dict], questions_by_kp: dict[str, list[dict]],
          per_kp: int = 1) -> dict:
    """为每个知识点各挑 1 个互动项。

    lesson_kps   : orchestrator.lesson_content() 里的 kps（含 explain）
    questions_by_kp : {kp_id: [题库题, ...]}
    """
    items: dict[str, dict] = {}
    for kp in lesson_kps:
        kp_id = kp.get("id")
        if not kp_id:
            continue
        picked = None
        for q in questions_by_kp.get(kp_id, []):
            picked = _from_question(q, kp_id)
            if picked:
                break
        if picked is None:
            # 题库里没有可用的选择题 → 从讲义原句造一道判断题
            for i, s in enumerate(_sentences(kp.get("explain") or "")):
                picked = _judge_item(kp_id, kp.get("title") or kp_id, i, s)
                if picked:
                    break
        if picked:
            items[kp_id] = picked
    return {"items": items}


def check(item: dict, user_answer) -> dict:
    """判一道互动题。复用正式判分引擎，保证课堂互动与测验口径一致。"""
    if item.get("type") == "judge":
        ok = str(user_answer) == str(item.get("answer"))
        g = {"correct": ok, "score": 1.0 if ok else 0.0}
    else:
        grade = _grade({"type": item.get("qtype") or "single_choice",
                        "answer": item.get("answer")}, user_answer)
        g = {"correct": grade.correct, "score": grade.score}
    g["why"] = item.get("why") or ""
    g["hint"] = "" if g["correct"] else (item.get("wrong_hint") or g["why"])
    return g


def public(item: dict) -> dict:
    """下发给前端的题面：**不含答案**（判分只在服务端）。"""
    return {
        "id": item["id"],
        "kp_id": item["kp_id"],
        "type": item["type"],
        "stem": item["stem"],
        "options": item["options"],
    }
