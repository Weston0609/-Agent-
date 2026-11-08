"""系统更新管道 —— 唯一烧 token 的入口（weekly / manual 触发）。

5 阶段：
  阶段1 拉取权威源变更 + 检索匹配待生成 KP（0 token / 有网络）
  阶段2 生成 KP 内容 + 题库（烧 token 或本地 Ollama 0 token）+ 引用校验 + 代码沙箱验证
  阶段3 陈旧内容打补丁（烧 token）
  阶段4 知识树扩建（烧 token）
  阶段5 审计（0 token）

后端选择：有 DEEPSEEK_API_KEY → 在线生成（计费）；否则探活本机 Ollama → 离线生成（0 token）；
两者都没有 → 跳过生成阶段（status=skipped_no_key），不改动任何已有内容。

原骨架 async；本应用同步架构，故 run_weekly_update 为同步函数。
"""
from __future__ import annotations

import logging
from datetime import datetime

log = logging.getLogger(__name__)


def select_llm(cfg) -> tuple[object, str]:
    """挑选本轮生成后端。返回 (client, backend_name)；都不行时返回未配置的 DeepSeek。"""
    from ..tools.deepseek_client import DeepSeek
    from ..tools.ollama_client import Ollama

    ds = DeepSeek(api_key=cfg.deepseek_api_key, model=cfg.deepseek_model)
    if ds.configured:
        return ds, "deepseek"
    ollama = Ollama(base_url=cfg.ollama_url, model=cfg.ollama_model)
    if ollama.configured:
        log.info("未设 DEEPSEEK_API_KEY，改用本机 Ollama（%s，离线 0 token）", cfg.ollama_model)
        return ollama, "ollama"
    return ds, "none"


def _build_queue(db, cfg, max_kps: int, crawler=None) -> tuple[list[dict], int]:
    """阶段 1：抓取白名单变更 → 建检索索引 → 给待生成 KP 配参考材料。

    返回 (queue, 抓到的新 chunk 数)。queue 项恒有 id=kp_id（旧实现把裸 chunk 直接塞进队列，
    导致生成出 id='' 的 KP）。`crawler` 可注入（测试离线跑，默认真抓取）。
    """
    from ..knowledge.ingest import crawl_whitelisted
    from ..knowledge.retriever import Retriever
    from ..knowledge.vector_store import VectorStore

    crawler = crawler or crawl_whitelisted
    changed = [c for c in crawler(since_days=7) if db.has_changed(c)]
    vs = VectorStore()
    for c in changed:
        vs.add(c["url"], c["content"], {"title": c["title"], "url": c["url"],
                                        "hash": c["hash"], "version": c.get("version", 1)})
    retriever = Retriever(vs)

    queue: list[dict] = []
    for k in db.find_unfilled_kps(limit=max_kps):
        hits = retriever.retrieve(f"{k['title']} {k['lesson_name']}", top_k=3) if len(vs) else []
        queue.append({
            "id": k["kp_id"],
            "title": k["title"] or k["kp_id"],
            "prereq": k.get("prereq") or [],
            "lesson_name": k.get("lesson_name") or "",
            "content": "\n\n".join(h["text"] for h in hits),
            "sources": [{"url": h["meta"]["url"], "hash": h["meta"]["hash"],
                         "fetched_at": ""} for h in hits],
        })
    return queue, len(changed)


def _build_quiz_backfill_queue(db, max_kps: int, min_questions: int) -> list[dict]:
    """补题队列：已有讲义但题量不足的 KP。复用 find_thin_quiz_kps，不抓网。"""
    queue = []
    for k in db.find_thin_quiz_kps(min_questions=min_questions, limit=max_kps):
        queue.append({
            "id": k["kp_id"],
            "title": k["title"] or k["kp_id"],
            "prereq": k.get("prereq") or [],
            "lesson_name": k.get("lesson_name") or "",
            "explain": k.get("explain") or "",
        })
    return queue


def run_weekly_update(db, manual: bool = False, max_kps: int = 5, llm=None,
                      crawler=None, cfg=None, backend: str | None = None,
                      backfill_quiz: bool = False, min_questions: int = 6) -> dict:
    """跑一轮更新。`max_kps` 限制单轮最多生成几个 KP（控 token 花费）。

    `cfg` / `backend` 可注入，便于测试与别处复用；省略则按环境自行挑选后端。

    `backfill_quiz=True` 时改走「补题队列」：只给已有讲义但题量不足的 KP 补题，
    **不改动讲义本身**。用于修复手写种子（每 KP 1 题）撑不住 10 分钟测验的问题。
    """
    from ..config import Config
    from ..knowledge.claim_verifier import ClaimVerifier
    from ..knowledge.ingest import load_whitelist
    from ..tools.code_sandbox import verify_code
    from .audit import run_audit
    from .kp_generator import (GenerationError, generate_kp_content, generate_quiz,
                               plan_next_batch, refresh_kp_content)

    cfg = cfg or Config()
    if llm is None:
        llm, backend = select_llm(cfg)
    elif backend is None:
        backend = "injected"

    start = datetime.now()
    tokens = 0
    kps_added = 0
    kps_updated = 0
    kps_skipped = 0
    status = "ok"

    try:
        # ---------- 阶段 1：抓取 + 排队（0 token） ----------
        if backfill_quiz:
            queue = _build_quiz_backfill_queue(db, max_kps, min_questions)
            n_chunks = 0
            log.info("补题模式：待补题 KP %d（讲义不动）", len(queue))
        else:
            queue, n_chunks = _build_queue(db, cfg, max_kps, crawler)
            log.info("阶段1完成：抓取新 chunk %d，待生成 KP %d", n_chunks, len(queue))

        if llm.configured:
            # 预算闸门：在线后端才可能烧 token，超限就地停手（离线 Ollama 不计费，放行）
            budget = getattr(cfg, "monthly_token_budget", 0) or 0
            if backend == "deepseek" and budget > 0:
                spent = db.month_tokens()
                if spent >= budget:
                    log.warning("本月 token 已用 %d / 预算 %d，跳过在线生成", spent, budget)
                    status = "skipped_over_budget"
                    print(
                        f"本月 token 已达上限，跳过一次在线生成（未花钱）。\n"
                        f"  已用 {spent} / 预算 {budget}（{db.token_spend()['month']}）\n"
                        f"  提高到 env MONTHLY_TOKEN_BUDGET，或改用离线 Ollama（0 token）。"
                    )
                    db.save_audit(run_audit(db))
                    return {"backend": backend, "tokens_used": tokens, "kps_added": kps_added,
                            "kps_updated": kps_updated, "kps_skipped": kps_skipped, "status": status}

            wl = load_whitelist(cfg.sources_path)
            verifier = ClaimVerifier(set(wl["domains"]), wl["missing_citation_policy"])

            # ---------- 阶段 2：生成 KP 内容 + 题库 ----------
            for chunk in queue:
                if backfill_quiz:
                    # 只补题：讲义一字不改，save_questions 按 kp_id 覆盖式重写
                    kp = dict(chunk)
                    kp["verified"] = True
                    questions = generate_quiz(llm, kp, n_variants=20, prompt_dir=cfg.prompt_dir)
                    db.save_questions(kp["id"], questions, source="generated")
                    kps_added += 1
                    tokens += getattr(llm, "last_tokens", 0)
                    continue

                try:
                    kp = generate_kp_content(llm, chunk, prompt_dir=cfg.prompt_dir)
                except GenerationError as exc:
                    log.warning("跳过 %s：%s", chunk.get("id"), exc)
                    kps_skipped += 1
                    tokens += getattr(llm, "last_tokens", 0)
                    continue
                cites = [s.get("url", "") for s in (kp.get("sources") or [])]
                check = verifier.verify(kp.get("explain", ""), cites)
                kp["verified"] = check["verified"]
                if not check["verified"]:
                    log.warning("引用未通过核验 %s：missing=%s", kp["id"], check["missing"])
                    if check["policy"] == "reject":
                        kps_skipped += 1
                        continue

                example = kp.get("example_code", "")
                if example and not verify_code(example, py_version="3.12"):
                    kp["example_code"] = ""
                    log.warning("代码未通过验证：%s", example[:50])

                questions = generate_quiz(llm, kp, n_variants=20, prompt_dir=cfg.prompt_dir)
                db.save_kp(kp, questions, version=chunk.get("version", 1))
                kps_added += 1
                tokens += getattr(llm, "last_tokens", 0)

            # ---------- 阶段 3：陈旧内容打补丁 ----------
            # 补题模式只动题库，绝不碰讲义，故跳过阶段 3/4。
            for kp in ([] if backfill_quiz else db.find_stale_kps(max_age_days=90)):
                row = {"kp_id": kp["kp_id"], "title": kp.get("title") or kp["kp_id"]}
                updated = refresh_kp_content(llm, row, prompt_dir=cfg.prompt_dir)
                tokens += getattr(llm, "last_tokens", 0)
                if not updated.get("needs_update"):
                    log.info("无需更新，跳过 %s：%s", kp["kp_id"], updated.get("reason", ""))
                    continue
                db.update_kp_content(kp["kp_id"], updated)
                kps_updated += 1

            # ---------- 阶段 4：知识树扩建（已停用） ----------
            # 原实现让模型凭空发明 KP id 并写入 kps 表，等于运行时改写课程结构：
            # 新增的 KP 不属于任何课（lesson_id 为空），学生永远学不到，且每次更新都会
            # 再堆一批（旧约束只有 kp_count < 2000）。规格里的「~2000 KP」是课程设计
            # 目标，不是让程序自动扩课。课程结构只应由 curriculum/full_curriculum.yaml 决定。
            # ponytail: 若将来要真扩建，应先改 YAML 再重跑 seed，而不是让模型直接写库。
            if not backfill_quiz and db.kp_count() < 2000:
                log.info("阶段 4（知识树扩建）已停用：课程结构以 curriculum YAML 为准")
        else:
            log.info("无 DEEPSEEK_API_KEY 且本机 Ollama 不可达，跳过生成阶段（阶段 2/3/4）")
            status = "skipped_no_key"
            hint = (
                f"没有可用生成后端（0 条内容被改动，也没有烧掉 token）。\n"
                f"  本机 Ollama：{cfg.ollama_url}（模型 {cfg.ollama_model}）探活失败\n"
                f"  二选一即可开跑：\n"
                f"    A. 离线 0 token —— 装好 Ollama 并拉模型：\n"
                f"         ollama pull {cfg.ollama_model}\n"
                f"         然后重跑本脚本，全程不花钱。\n"
                f"    B. 在线生成 —— 设置 DEEPSEEK_API_KEY 后重跑（会消耗 token）。"
            )
            cov = db.covered_summary()
            print(hint + f"\n  当前进度：{cov['with_content']}/{cov['total_kps']} 个知识点已有讲义。")

        # ---------- 阶段 5：审计（0 token） ----------
        db.save_audit(run_audit(db))

    finally:
        db.log_update(
            kind="manual" if manual else "weekly",
            started_at=start, ended_at=datetime.now(),
            tokens_used=tokens, kps_added=kps_added, kps_updated=kps_updated,
            status=status,
        )
        log.info("更新完成：backend=%s tokens=%d added=%d updated=%d skipped=%d status=%s",
                 backend, tokens, kps_added, kps_updated, kps_skipped, status)
    return {"backend": backend, "tokens_used": tokens, "kps_added": kps_added,
            "kps_updated": kps_updated, "kps_skipped": kps_skipped, "status": status}
