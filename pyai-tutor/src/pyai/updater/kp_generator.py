"""知识点内容生成 —— 更新管道阶段 2/3/4 的模型调用。

prompt 正文来自 `curriculum/prompt_templates/*.jinja`（用户可直接改这些模板来调教学风格）；
本模块只负责渲染模板、拼上机器可读的 JSON 契约、解析返回。
生成后端由 pipeline.select_llm 决定（DeepSeek 或本机 Ollama）。
"""
from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path

import jinja2

log = logging.getLogger(__name__)

_KP_CONTRACT = (
    "\n\n请严格返回 JSON（不要额外文字）：\n"
    '{"explain": 讲解正文(Markdown), "example_code": 一段可运行示例代码, '
    '"pitfalls": 常见误区, "sources": [{"url": "引用来源 URL", "hash": "内容哈希"}]}'
)

_QUIZ_CONTRACT = (
    "\n\n请严格返回 JSON 数组（不要额外文字）。每项必须含 type 与 stem："
    '{"type": "single_choice|multi_choice|fill_blank|code_reading|scenario", '
    '"stem": 题干(非空), "options": [选项], "answer": 答案, '
    '"explanation": 解析(非空), "error_tag": 错误类型, "variant_group": 变体组名}。'
    "answer 的形态随题型而定：单选为下标 int，多选为下标数组，"
    "填空为可接受答案字符串数组，代码阅读为字符串，场景题为 required_keywords 数组。"
    "题干字段名必须是 stem；残缺题（空题干、选项不足、答案越界）会被系统丢弃。"
)


@lru_cache(maxsize=8)
def _env(prompt_dir: str) -> jinja2.Environment:
    return jinja2.Environment(
        loader=jinja2.FileSystemLoader(prompt_dir),
        trim_blocks=True, lstrip_blocks=True,
    )


def _render(prompt_dir: Path | str | None, template: str, **ctx) -> str:
    """渲染模板；prompt_dir 缺省时用发行版自带模板。模板缺失则抛错（不静默降级）。"""
    if prompt_dir is None:
        from ..config import Config
        prompt_dir = Config().prompt_dir
    return _env(str(prompt_dir)).get_template(template).render(**ctx)


class GenerationError(RuntimeError):
    """模型返回的内容不可用（空讲义 / 解析失败）。调用方应跳过该 KP，不要写库。"""


def _loads(raw: str):
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def generate_kp_content(llm, chunk, refresh: bool = False,
                        prompt_dir: Path | str | None = None) -> dict:
    """生成单个 KP 的结构化内容。返回 {id, explain, example_code, pitfalls, sources, verified}。"""
    if isinstance(chunk, str):
        chunk = {"id": chunk, "title": chunk, "content": ""}
    kp_id = chunk.get("id") or chunk.get("kp_id") or ""
    title = chunk.get("title") or kp_id

    prompt = _render(
        prompt_dir, "tutor.jinja",
        kp_id=kp_id, title=title,
        prerequisites=chunk.get("prereq") or chunk.get("prerequisites") or [],
        lesson_title=chunk.get("lesson_name") or chunk.get("lesson_title") or "",
    )
    material = chunk.get("content") or ""
    if material:
        prompt += f"\n\n可参考的权威源材料：\n{material}"
    if refresh:
        prompt += "\n\n注意：这是在更新一份已有讲义，请给出更准确、更贴合当前版本的说法。"
    prompt += _KP_CONTRACT

    data = _loads(llm.chat(prompt)) or {}
    sources = data.get("sources") or chunk.get("sources") or (
        [{"url": chunk["url"], "hash": chunk.get("hash", ""), "fetched_at": chunk.get("fetched_at", "")}]
        if chunk.get("url") else []
    )
    explain = (data.get("explain") or "").strip()
    if not explain:
        # 空讲义曾被当作成功写库（verified=1、计入 added），学生上课看到空白页。
        # 宁可不写：该 KP 会留在待生成队列里下次重试。
        raise GenerationError(f"{kp_id}：模型未返回讲义正文（explain 为空）")
    return {
        "id": kp_id,
        "explain": explain,
        "example_code": data.get("example_code", "") or "",
        "pitfalls": data.get("pitfalls", "") or "",
        "sources": sources,
        "verified": False,
    }


def _mentions_kp_id(stem: str, kp_id: str) -> bool:
    """题干是否把内部 kp_id 当成代码/模块名吐了出来。

    模型看到 `py.env.install` 这种点分标识符，容易脑补成「模块.函数」并编出不存在的
    API（实测 18.9% 的题如此）。这类题会教错，必须拦在第一入口，不能只靠 prompt 约束。
    """
    if not kp_id:
        return False
    return kp_id in stem


def _is_wellformed(q: dict) -> bool:
    """题是否可以直接给学生做。

    实测模型偶发返回空题干（4 个 KP、80 道题），但选项和答案齐全，
    于是这些题带着空 stem 写进题库：学生看到空白题、判分无从下手。
    各题型的答案形态不同，逐类型校验，否则判分器会把它当错题。
    """
    stem = str(q.get("stem") or "").strip()
    if not stem:
        return False
    # 解析是错题本的教学载体（学生做错要看到为什么）；error_tag 是 error_log 的分类键。
    # 实测场景题常整题缺这两项，缺了照样能判分，但错题本就失效了。
    if not str(q.get("explanation") or "").strip():
        return False
    if not str(q.get("error_tag") or "").strip():
        return False
    qtype = q.get("type", "single_choice")

    if qtype in ("single_choice", "multi_choice"):
        opts = q.get("options")
        if not isinstance(opts, list) or len(opts) < 2:
            return False
        if any(not str(o).strip() for o in opts):
            return False
        ans = q.get("answer")
        if qtype == "single_choice":
            try:
                return 0 <= int(ans) < len(opts)
            except (TypeError, ValueError):
                return False
        picks = ans if isinstance(ans, list) else [ans]
        if len(picks) < 2:                       # 多选题至少 2 个正确项
            return False
        if not all(isinstance(p, int) and 0 <= p < len(opts) for p in picks):
            return False
        return len(set(picks)) == len(picks)     # 下标不能重复

    if qtype == "fill_blank":
        # grading 把 answer 当可接受答案数组遍历，字符串会被逐字符拆开判分
        ans = q.get("answer")
        return isinstance(ans, list) and any(str(a).strip() for a in ans)

    if qtype == "code_reading":
        return str(q.get("answer") or "").strip() != ""

    if qtype == "scenario":
        keys = q.get("required_keywords")
        return isinstance(keys, list) and any(str(k).strip() for k in keys)

    return False                                  # 未知题型：不收


def generate_quiz(llm, kp, n_variants: int = 20,
                  prompt_dir: Path | str | None = None) -> list[dict]:
    """为一个 KP 生成 n 道变体题。返回 questions 列表（含 kp_id）。"""
    kp_id = kp.get("id") if isinstance(kp, dict) else kp
    title = kp.get("title", kp_id) if isinstance(kp, dict) else kp_id

    prompt = _render(prompt_dir, "quiz_gen.jinja", n=n_variants, kp_id=kp_id, title=title)
    prompt += _QUIZ_CONTRACT

    data = _loads(llm.chat(prompt))
    questions = data if isinstance(data, list) else (data or {}).get("questions", [])
    out: list[dict] = []
    dropped = malformed = 0
    for q in questions:
        if not isinstance(q, dict):
            malformed += 1
            continue
        if _mentions_kp_id(str(q.get("stem", "")), kp_id):
            dropped += 1                      # 题干泄漏内部标识符 → 丢弃，不污染题库
            continue
        if not _is_wellformed(q):
            malformed += 1                    # 空题干 / 答案越界 → 丢弃
            continue
        q.setdefault("id", f"{kp_id}-q{len(out)}")
        q.setdefault("kp_id", kp_id)
        out.append(q)
    if dropped:
        log.warning("%s：丢弃 %d 道把 kp_id 当代码的题", kp_id, dropped)
    if malformed:
        log.warning("%s：丢弃 %d 道残缺题（空题干/选项或答案不合法）", kp_id, malformed)
    return out


def refresh_kp_content(llm, kp_row: dict, old_summary: str = "", sources: list | None = None,
                       prompt_dir: Path | str | None = None) -> dict:
    """阶段 3：判断一条已有讲义是否需要更新，需要则给出新正文（用 updater.jinja）。"""
    kp_id = kp_row.get("kp_id") or kp_row.get("id") or ""
    prompt = _render(
        prompt_dir, "updater.jinja",
        kp_id=kp_id, title=kp_row.get("title") or kp_id,
        sources=[s.get("url", "") for s in (sources or [])] or ["（无）"],
        summary=old_summary or "（无）",
    )
    data = _loads(llm.chat(prompt)) or {}
    return {
        "id": kp_id,
        "explain": data.get("new_content", "") or "",
        "example_code": "",
        "pitfalls": "",
        "sources": sources or [],
        "verified": False,
        "needs_update": bool(data.get("needs_update")),
        "reason": data.get("reason", "") or "",
    }


def plan_next_batch(llm, covered: dict, target_size: int = 2000) -> list:
    """规划下一批待建知识点（仅更新管道阶段 4 调用）。对 DeepSeek / Ollama 都适用。"""
    prompt = (
        f"当前已覆盖 {covered.get('total_kps', 0)} 个知识点，目标规模 {target_size}。\n"
        f"各学期填充情况：{json.dumps(covered.get('semesters', {}), ensure_ascii=False)}\n"
        "请返回 JSON 数组，每项为一个待新增知识点 id 字符串。"
    )
    data = _loads(llm.chat(prompt))
    items = data if isinstance(data, list) else (data or {}).get("kps", [])
    # 只接受字符串 id：模型偶尔返回对象数组，直接透传会让阶段 4 落库一堆空 id 的垃圾 KP
    out: list[str] = []
    for it in items or []:
        if isinstance(it, str) and it.strip():
            out.append(it.strip())
        elif isinstance(it, dict):
            kid = it.get("id") or it.get("kp_id")
            if isinstance(kid, str) and kid.strip():
                out.append(kid.strip())
    return out
