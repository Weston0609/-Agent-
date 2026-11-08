"""从已有内容推导缺失的展示元数据：中文标题 + 题目难度。

为什么需要这一层：lessons.name 与 kps.title 在 seed_curriculum 里被写死成 id
（面板上到处是 `s1u1l1` 这种裸 id），questions.difficulty 也全部默认成 1
（s8 的 K8s 题和 s1 的 print 题难度完全一样）。这两列的数据其实**已经在库里**：
- 中文标题就写在讲义正文的 H1（kp_content.explain 开头一行 `# 中文标题`）；
- 难度可由「课在 178 课中的位置 + 题型 + 题干长度」推出来，不烧 token。

所以不重跑内容生成、也不改 content/lessons/*.json（种子只补空缺、且真实库
385 篇讲义与 7787 道题全是 generated，改种子根本不生效），而是在启动时幂等回填。

回填靠 PRAGMA user_version 做版本闸：同版本只算一次，课程树重建时归零重跑。
另外只在值真的不同时才 UPDATE —— 无条件写会把 WAL 撑大，也会让下游缓存失效。
"""
from __future__ import annotations

import re

# 讲义里当标题用、但其实是通用小节的 H1（"# 一句话直觉" 之类），不能当知识点名
_GENERIC_HEAD = re.compile(
    r"^(?:[一二三四五六七八九十]+[、.．]\s*)?(?:一句话直觉|为什么(?:要|需要|学)|本节|小结|总结|"
    r"引言|前言|课程目标|学习目标|动手|练习|自测|回顾|参考|延伸)"
)
_H1 = re.compile(r"^# +(.+?) *$", re.MULTILINE)
_FENCE_LINE = re.compile(r"^\s*```")
_ENUM = re.compile(r"^(?:[一二三四五六七八九十]+|\d+)\s*[、.．)）]\s*")
_KNOW_NOISE = re.compile(r"^(?:知识点|考点|主题)\s*[：:]\s*")
_LECTURE_NOISE = re.compile(r"(?:40\s*分钟)?(?:课程|教学|学习)?讲义\s*[：:]?\s*")
_LEVEL_NOISE = re.compile(
    r"[：:，,]?\s*(?:40\s*分钟)?(?:从零|从直觉)?(?:基础)?到工程(?:级|实践|化)?\s*$")
# 「（40 分钟）」「教学讲义」这类课时标注不是标题的一部分
_DURATION = re.compile(r"[（(]?\s*(?:\d{2})\s*(?:分钟|min(?:utes)?)\s*[）)]?", re.IGNORECASE)
_BOLD_WRAP = re.compile(r"^\*\*(.+)\*\*$")
_BOLD_LEAD = re.compile(r"^\*\*(.+?)\*\*")
_BOLD_ANY = re.compile(r"\*\*(.+?)\*\*")
_LEAD_NOISE = re.compile(r"^(?:一句话直觉|一句话|直觉|先说结论)\s*[：:，,]\s*")
# 术语对：中文（English） / English（中文）——无 H1 的 49 篇讲义靠它在正文里锚定术语。
# 两侧都可能被反引号包着（`` `ai.nn.optim`（优化器，optimizer） ``），故允许 ` 出现，事后再剥。
_PAIR = re.compile(
    r"([\u4e00-\u9fa5A-Za-z0-9 ._/+·`\-]{2,40}?)\s*[（(]\s*([^）)]{2,44}?)\s*[）)]")
_CJK = re.compile(r"[\u4e00-\u9fa5]")
# 叙述句的开头，命中说明抽到的是句子不是术语
_NARRATIVE = re.compile(
    r"^(?:而|且|但|也|就|还|则|因此|所以|如果|当你|我们|它|这|那|因为|虽然|不仅|"
    r"本|该|其|此|学|做|第|一堂)")
# 按「反引号代码段」为最小单元切，避免把 `*args` / `**kwargs` 截成半个
_CHUNK = re.compile(r"`[^`]*`|[^`]")
_SENT_END = re.compile(r"[。？！]")
_TAIL = " 　：:、，。;；——-|·「（("
_CONJ = ("与", "和", "及", "或", "而", "的", "是", "把", "从", "在", "让", "对", "用", "给", "为", "等")

KP_TITLE_MAX = 32
LESSON_TITLE_MAX = 24

# 「一堂课讲透 X」「40 分钟掌握 X」这类营销式开头，剥掉留术语
_VERBOSE_LEAD = re.compile(
    r"^(?:一堂课|一篇文章|一文|一节课)?\s*"
    r"(?:讲透|讲清|搞懂|掌握|学会|入门|带你|手把手教你|彻底搞懂|深入理解)\s*")
_TITLE_COLON = re.compile(r"[：:]")

# 回填版本号，存在 SQLite 的 user_version 里。改标题/难度规则时 +1 即可让老库重算一遍；
# 否则每次启动都扫 385 篇讲义 + 7787 道题，纯属浪费。
# ponytail: 讲义若被 updater 重写、H1 变了，标题会停留在旧值，直到 +1。目前 updater
# 只补空缺不改已有正文，暂不触发。
DERIVE_VERSION = 2

# 题型对难度的修正：要自己组织语言的、要读代码的，比单纯认单选难一档
_TYPE_DELTA = {"multi_choice": 1, "code_reading": 1, "scenario": 1}
_LONG_STEM = 120     # 题干 ≥120 字算长题（多一层背景/多个陷阱）
_SHORT_STEM = 40     # 题干 <40 字算短题（纯记忆）


def _tidy(text: str) -> str:
    t = (text or "").strip().strip(_TAIL)
    while t and t[-1] in _CONJ:      # 「Python 中的」这种断在连接词上的收尾
        t = t[:-1].strip(_TAIL)
    # 截断常把「（Caching」的右括号切掉，宁可丢掉半个括注也别留半个
    for left, right in (("（", "）"), ("(", ")"), ("「", "」"), ("“", "”"), ('"', '"')):
        if left == right:                 # 直引号不分左右，只能靠奇偶
            if t.count(left) % 2:
                t = t[: t.rfind(left)].strip(_TAIL)
        elif t.count(left) > t.count(right):
            t = t[: t.rfind(left)].strip(_TAIL)
    return t


def clip(text: str, limit: int) -> str:
    """按反引号代码段整体截断，不切坏 `*args` 这类片段。

    略超上限（≤3 字）时宁可整段留着：「完全指南」被切成「完全指」比多 2 个字更糟。
    """
    t = _tidy(text)
    if len(t) <= limit + 3:
        return t
    out = ""
    for chunk in _CHUNK.findall(t):
        if len(out) + len(chunk) > limit:
            break
        out += chunk
    return _tidy(out) or _tidy(t[:limit])


def _unescape(md: str) -> str:
    """69 篇讲义把换行写成了字面 \\n（整篇挤成一行）。围栏代码块里是真的 \\n，不能动。"""
    if "\\n" not in (md or ""):
        return md or ""
    out, in_fence = [], False
    for line in md.splitlines():
        if _FENCE_LINE.match(line):
            in_fence = not in_fence
            out.append(line)
        else:
            out.append(line if in_fence else line.replace("\\n", "\n"))
    return "\n".join(out)


def _strip_fences(md: str) -> str:
    kept, in_fence = [], False
    for line in (md or "").splitlines():
        if _FENCE_LINE.match(line):
            in_fence = not in_fence
            continue
        if not in_fence:
            kept.append(line)
    return "\n".join(kept)


def _usable(t: str, kp_id: str) -> bool:
    """标题得像名字：不能是空、不能等于 id、不能是被截断的句子碎片。"""
    if not t or t == kp_id or len(t) < 2:
        return False
    if _NARRATIVE.match(t):
        return False
    # 句末标点说明抽到的是句子，不是名字
    if re.search(r"[。！？]", t):
        return False
    # 截断常停在虚词上（「…就上线，你」「…就像学」），这类一律不要
    if t[-1] in "的了吗呢吧你我在和与或就都也学说是能有把让给对从":
        return False
    return True


_PAIRS = (("（", "）"), ("(", ")"), ("「", "」"), ("“", "”"), ("《", "》"))


def _strip_edges(t: str) -> str:
    """剥掉首尾标点；若首尾正好是一对括号就成对剥，不留半个「…）」."""
    edge = " 　：:、，。;；——-|·"
    t = t.strip(edge)
    while t:
        if t[0] in "（）()「」“”《》":
            for left, right in _PAIRS:
                if t[0] == left:
                    t = t[1:].strip(edge)
                    if t.endswith(right):
                        t = t[:-1].strip(edge)
                    break
            else:
                t = t[1:].strip(edge)
            continue
        break
    return t


def _in_code_span(text: str, pos: int) -> bool:
    """pos 处的字符是否落在反引号代码段内（前面有奇数个反引号）。"""
    return text.count("`", 0, pos) % 2 == 1


def _clean(raw: str, kp_id: str, limit: int = KP_TITLE_MAX) -> str:
    t = (raw or "").strip().splitlines()[0] if (raw or "").strip() else ""
    if not t:
        return ""
    m = _BOLD_WRAP.match(t)
    if m:
        t = m.group(1)
    t = _ENUM.sub("", t.strip())
    t = _KNOW_NOISE.sub("", t)
    # kp_id 常被反引号包着（`py.io.print_format`），故按词边界全局删而不是锚定行首
    t = re.sub(rf"`?\b{re.escape(kp_id)}\b`?", "", t)
    t = _DURATION.sub("", t)
    t = _LECTURE_NOISE.sub("", t)
    t = _LEVEL_NOISE.sub("", t)
    t = _VERBOSE_LEAD.sub("", t)
    # 「LangGraph Checkpoint：给 AI 工作流装上存档」→ 冒号后是解释；
    # 「第 5 单元 · 第 3 讲：Python 异步事件」→ 冒号前是课时编号。
    # 两边都可能才是真标题，取第一个像名字的。反引号代码段里的冒号不算
    # （`` `if __name__ == "__main__":` 完全指南 `` 得整段留着）。
    for m in _TITLE_COLON.finditer(t):
        if _in_code_span(t, m.start()):
            continue
        for cand in (t[: m.start()], t[m.end():]):
            cand = cand.strip(_TAIL)
            if len(cand) >= 3 and _usable(cand, kp_id) and not _GENERIC_HEAD.match(cand):
                t = cand
                break
        break
    t = re.sub(r"[：:，,]{2,}", "：", t)
    t = _strip_edges(t)
    m = _SENT_END.search(t)
    if m and m.start() >= 6:          # 太短的首句可能是「注意：」之类的残句
        t = t[:m.start()]
    return clip(t, limit)


def _humanize(kp_id: str) -> str:
    tail = kp_id.rsplit(".", 1)[-1].replace("_", " ").strip()
    return tail or kp_id


def kp_title(explain: str, kp_id: str, limit: int = KP_TITLE_MAX) -> str:
    """从一篇讲义正文里抽知识点中文标题。

    三级回退，越靠后越粗：
    1. H1（333/385 篇讲义的第一行就是 `# 中文标题`）；
    2. 术语对 —— 无 H1 的 49 篇里，正文首段通常有 `**术语（English）**`，
       用 kp_id 尾段（如 `position_encoding`）去锚定 `中文（English）` 的配对；
    3. 首段第一个加粗词；
    最后退回 id 末段（`slots` → `slots`）。
    """
    body = _strip_fences(_unescape(explain))
    for m in _H1.finditer(body):
        raw = m.group(1).strip()
        if _GENERIC_HEAD.match(raw):
            continue
        t = _clean(raw, kp_id, limit)
        if _usable(t, kp_id):
            return t
    t = _clean(_pair_term(body, kp_id), kp_id, limit)
    if _usable(t, kp_id):
        return t
    t = _clean(_bold_lead(body), kp_id, limit)
    if _usable(t, kp_id):
        return t
    return _humanize(kp_id)


def _pair_term(body: str, kp_id: str) -> str:
    """在正文里找「中文（English）」且 English 含 kp_id 尾段的那一对，返回中文。"""
    tail = re.sub(r"[^a-z0-9]", "", kp_id.rsplit(".", 1)[-1].lower())
    if not tail:
        return ""
    for m in _PAIR.finditer(body[:3000]):
        outside, inside = m.group(1).strip(), m.group(2).strip()
        if _CJK.search(inside) and not _CJK.search(outside):
            cn, en = inside, outside          # English（中文）
        elif _CJK.search(outside) and not _CJK.search(inside):
            cn, en = outside, inside          # 中文（English）
        else:
            continue
        if tail in re.sub(r"[^a-z0-9]", "", en.lower()) and 2 <= len(cn) <= 24:
            return cn.strip(_TAIL)
    return ""


def _bold_lead(body: str) -> str:
    """首段第一个加粗词（`**类型注解（Type Hint）** 就像给代码…`）。"""
    for line in body.splitlines():
        s = line.strip()
        if not s or s[0] in "#->|" or s.startswith(("- ", "* ")):
            continue
        m = _BOLD_LEAD.match(s)
        if m:
            return m.group(1)
        s = _LEAD_NOISE.sub("", s)
        m = _SENT_END.search(s)
        return s[:m.start()] if m else s
    return ""


def lesson_name(titles: list[str], lesson_id: str) -> str:
    """课名取该课第一个知识点的标题（178 课里没有一课自带中文名）。"""
    for t in titles:
        if t and t != lesson_id:
            return clip(t, LESSON_TITLE_MAX)
    return _humanize(lesson_id)


def question_difficulty(base: int, qtype: str | None, stem: str) -> int:
    """题目难度 1..5 = 课的位置分档 + 题型修正 + 题干长度修正。"""
    d = base + _TYPE_DELTA.get(qtype or "", 0)
    s = stem or ""
    if "```" in s or len(s) >= _LONG_STEM:
        d += 1
    elif len(s) < _SHORT_STEM:
        d -= 1
    return max(1, min(5, d))


def tier(index: int, total: int) -> int:
    """课在全部课程序列里的位置 → 1..5 分档（第 1 课 1 档、最后一课 5 档）。"""
    if total <= 0:
        return 1
    return max(1, min(5, 1 + 5 * index // total))


def backfill(db) -> dict:
    """幂等回填 lessons.name / kps.title / questions.difficulty。

    靠 PRAGMA user_version 做版本闸：已经回填过同版本就整体跳过（启动耗时从
    「扫 8172 行」降到「读一个整数」）。_migrate 里没有版本号机制，这里就地用。
    """
    if db._conn.execute("PRAGMA user_version").fetchone()[0] >= DERIVE_VERSION:
        return {"skipped": True}
    n_title = n_lesson = n_diff = 0
    with db._lock:
        rows = db._conn.execute("SELECT kp_id, explain FROM kp_content").fetchall()
        titles: dict[str, str] = {}
        for r in rows:
            t = kp_title(r["explain"] or "", r["kp_id"])
            titles[r["kp_id"]] = t
            cur = db._conn.execute(
                "UPDATE kps SET title = ? WHERE id = ? AND title <> ?", (t, r["kp_id"], t))
            n_title += cur.rowcount if cur.rowcount > 0 else 0

        per_lesson: dict[str, list[str]] = {}
        for r in db._conn.execute(
                """SELECT l.id AS lesson_id, k.id AS kp_id FROM lessons l
                   JOIN kps k ON k.lesson_id = l.id
                   ORDER BY l.id, k."order" """).fetchall():
            per_lesson.setdefault(r["lesson_id"], []).append(titles.get(r["kp_id"], r["kp_id"]))
        for lesson_id, kp_titles in per_lesson.items():
            name = lesson_name(kp_titles, lesson_id)
            cur = db._conn.execute(
                "UPDATE lessons SET name = ? WHERE id = ? AND name <> ?", (name, lesson_id, name))
            n_lesson += cur.rowcount if cur.rowcount > 0 else 0

        order = db.all_lessons_in_order()
        base = {l.id: tier(i, len(order)) for i, l in enumerate(order)}
        qs = db._conn.execute("SELECT id, kp_id, type, stem, difficulty FROM questions").fetchall()
        kp_lesson = {r["id"]: r["lesson_id"]
                     for r in db._conn.execute("SELECT id, lesson_id FROM kps").fetchall()}
        for q in qs:
            d = question_difficulty(base.get(kp_lesson.get(q["kp_id"]), 1), q["type"], q["stem"] or "")
            if d != q["difficulty"]:
                db._conn.execute("UPDATE questions SET difficulty = ? WHERE id = ?", (d, q["id"]))
                n_diff += 1
        db._conn.execute(f"PRAGMA user_version = {DERIVE_VERSION}")
        db._conn.commit()
    db._invalidate_index()   # lessons.name/kps.title 改了，课程树索引缓存作废
    return {"kp_titles": n_title, "lesson_names": n_lesson, "question_difficulty": n_diff}
