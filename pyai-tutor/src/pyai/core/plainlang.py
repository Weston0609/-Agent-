"""大白话卡片 —— 从已缓存的讲义里提炼「人话版」解释（0 token，纯离线）。

**铁律：不新增知识。** 这里只做三件事：
  1. 摘出讲义里本来就写着的「一句话直觉」；
  2. 摘出「关键结论」；
  3. 把代码示例的第一行配上「这段代码在干嘛」的说明——说明取自讲义原文，不自己编。

凡是提炼不出原文的，宁可不给卡片（返回空），也不生成一句可能教错的话。
后续接入模型生成时，只需提供同样结构的字段即可覆盖这里的结果。
"""
from __future__ import annotations

import re

_QUOTE = re.compile(r"\*\*一句话直觉\*\*\s*[:：]\s*(.+)")
_CONCLUSION = re.compile(r"\*\*关键结论\*\*\s*[:：]\s*(.+)")
_FENCE = re.compile(r"```(\w*)\n(.*?)```", re.S)

# 讲义里「一句话直觉 / 关键结论」有两种落地写法，必须都认，否则卡片是空的：
#   A. 同行式：  **一句话直觉**：xxxx。
#   B. 标题式：  ## 一句话直觉\n\nxxxx。      ← 生成讲义实际大量使用这种
# 标题式下面那一段可能是加粗，也可能直接是正文；两种都取。
_HEAD_QUOTE = re.compile(r"(?m)^#{1,4}\s*一句话直觉\s*$\s*(.+?)(?=\n#{1,4}\s|\Z)", re.S)
_HEAD_CONCL = re.compile(r"(?m)^#{1,4}\s*关键结论\s*$\s*(.+?)(?=\n#{1,4}\s|\Z)", re.S)

# 一段适合放进「大白话」卡片的句子长度上限（太长就不是人话了）。
_MAX_LEN = 120

# 讲义里作者自己举例子时的标志词。只认这些，避免把普通论述当成例子。
_EXAMPLE = re.compile(r"(假设|比如说|比如|例如|举个例子|就像|好比|相当于|想象一下|试想)")


def _clean(s: str) -> str:
    s = re.sub(r"[`*_>]", "", s).strip()
    s = re.sub(r"\s+", " ", s)
    return s


def _first(text: str) -> str:
    m = re.search(r"^(.*?[。！？!?])", text)
    return _clean(m.group(1) if m else text)


def _section_first(block: str) -> str:
    """从「## 一句话直觉」标题下的整块正文里，取第一句真正像人话的话。

    标题下可能先是加粗原句，也可能直接是解释段落；跳过空行、分隔线、代码块和列表，
    只取第一段散文的第一句。取不到就返回空——宁可不给，也不编。
    """
    for raw in re.split(r"\n\s*\n", block or ""):
        s = raw.strip()
        if not s:
            continue
        if re.fullmatch(r"-{3,}", s) or s.startswith("```") or s.startswith("|"):
            continue
        if re.match(r"^(?:[-*+] |\d+\. )", s):      # 列表项不是「一句话」
            continue
        text = _first(s)
        if len(text) >= 8:
            return text
    return ""


def _pick(explain: str, inline: re.Pattern, heading: re.Pattern) -> str:
    """先认同行式，再认标题式——两种写法覆盖全部存量讲义。"""
    m = inline.search(explain or "")
    if m:
        got = _first(m.group(1))
        if got:
            return got
    m = heading.search(explain or "")
    if m:
        return _section_first(m.group(1))
    return ""


def _example(explain: str, avoid: str = "") -> str:
    """找出讲义里作者自己举的例子，用来「加深理解」。

    只认带举例标志词的句子（假设/比如/例如/就像/好比/相当于/想象），
    并且必须和「一句话直觉」不是同一句——否则卡片上下说同一件事，白占地方。
    纯离线、只摘原文，不自己编例子。
    """
    text = explain or ""
    for m in _EXAMPLE.finditer(text):
        start = m.start()
        # 从标志词所在段落的开头取，读起来才完整
        para_start = text.rfind("\n\n", 0, start) + 2
        para = text[para_start:].split("\n\n", 1)[0]
        # 代码块、表格、标题、列表都不是「一句话例子」——列表会把整段要点拖进来。
        head = para.lstrip()
        if "```" in para or head.startswith(("|", "#", "-", "*", "+", ">")) or re.match(r"^\d+\.\s", head):
            continue
        # 「**关键结论**：- …」这类加粗标题 + 列表同样不是例子。
        if re.match(r"^\*\*[^*]{2,12}\*\*\s*[:：]\s*[-*+\d]", head):
            continue
        got = _first(para.strip())
        # 「假设你同时开发两个项目：」后面跟的是具体项目，_first 只截到冒号就没内容了；
        # 这种时候退回整段，例子才完整。
        if got.endswith(("：", ":")) or len(got) < 12:
            got = _clean(re.sub(r"\s+", " ", para))
        # 例子里不该还挂着列表符或整段要点。
        # 注意「假设有 A、B 两个项目」本身就是好例子，只有条目过多才说明是罗列而非句子。
        if len(re.findall(r"(?:^|\s)-\s", got)) >= 2 or got.count("；") >= 3:
            continue
        # 标志词得在句子前半部分出现，否则只是顺便提了一句，不是真在举例。
        if _EXAMPLE.search(got[: max(12, len(got) // 2)]) is None:
            continue
        if not got or len(got) < 12:
            continue
        if avoid and got[:20] == avoid[:20]:       # 与直觉句重复
            continue
        # 例子得是能看懂的句子，不能是一串符号
        if len(re.findall(r"[\u4e00-\u9fff]", got)) < 8:
            continue
        return got[:_MAX_LEN]
    return ""


def _code_hint(example_code: str) -> str:
    """取代码块首行注释当「这段在干嘛」——注释是作者写的说明，不自己编。

    要过滤掉三类噪音：编码声明、文件名、以及纯英文的技术注释（对"大白话"没帮助）。
    """
    for line in (example_code or "").splitlines():
        s = line.strip()
        if not s.startswith("#"):
            continue
        text = _clean(s.lstrip("#").strip())
        if not text:
            continue
        low = text.lower()
        if "-*-" in text or "coding" in low or "utf-8" in low:   # 编码声明
            continue
        if re.fullmatch(r"[\w.\-]+\.[a-z]{2,4}", text):            # 光是个文件名
            continue
        if not re.search(r"[\u4e00-\u9fff]", text):                # 没有中文 → 不是大白话
            continue
        if len(text) < 6:
            continue
        return text[:_MAX_LEN]
    return ""


def build(explain: str, example_code: str = "", pitfalls: str = "") -> dict | None:
    """返回 `{intuition, conclusion, example, code_hint, pitfall, has_any}`，无素材时返回 None。

    注意：`explain` 可以整段讲义，也可以只是**当前小节**的正文。前端按小节翻页时传小节正文进来，
    卡片内容才会跟着翻页变化（原来传整个知识点，翻遍整课卡片都不动）。
    """
    intuition = _pick(explain or "", _QUOTE, _HEAD_QUOTE)
    conclusion = _pick(explain or "", _CONCLUSION, _HEAD_CONCL)
    example = _example(explain or "", avoid=intuition)

    code_hint = _code_hint(example_code)
    pitfall = _first(pitfalls) if pitfalls else ""

    if not (intuition or conclusion or example or code_hint or pitfall):
        return None
    return {
        "intuition": intuition[:_MAX_LEN],
        "conclusion": conclusion[:_MAX_LEN],
        "example": example[:_MAX_LEN],
        "code_hint": code_hint[:_MAX_LEN],
        "pitfall": pitfall[:_MAX_LEN],
        "has_any": True,
    }
