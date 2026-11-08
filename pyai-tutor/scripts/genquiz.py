"""给「有讲义但没题」的 KP 补题，直到全部补齐。

可中断可续跑：find_thin_quiz_kps 只返回题量不足 min_questions 的 KP。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pyai.config import Config  # noqa: E402
from pyai.core.orchestrator import Orchestrator  # noqa: E402
from pyai.updater.pipeline import run_weekly_update  # noqa: E402

MIN_Q = int(sys.argv[1]) if len(sys.argv) > 1 else 6
BATCH = int(sys.argv[2]) if len(sys.argv) > 2 else 4
MAX_ROUNDS = 200
IDLE_TOLERANCE = 3

orch = Orchestrator(Config.from_env())
db = orch.db
conn = db._conn

t0 = time.time()
spent = added = skipped = 0
idle = 0
print(f"起始：待补题 KP {len(db.find_thin_quiz_kps(min_questions=MIN_Q, limit=9999))}", flush=True)

try:
    for i in range(MAX_ROUNDS):
        if not db.find_thin_quiz_kps(min_questions=MIN_Q, limit=1):
            print("✅ 所有 KP 的题量都达标了", flush=True)
            break
        r = run_weekly_update(db, manual=True, max_kps=BATCH,
                              backfill_quiz=True, min_questions=MIN_Q)
        spent += r["tokens_used"]
        added += r["kps_added"]
        skipped += r["kps_skipped"]
        if r["kps_added"] == 0 and r["kps_skipped"] == 0:
            idle += 1
        else:
            idle = 0
        if idle >= IDLE_TOLERANCE:
            print(f"⚠️ 连续 {idle} 轮零进展，停止", flush=True)
            break
        left = len(db.find_thin_quiz_kps(min_questions=MIN_Q, limit=9999))
        noq = conn.execute(
            "SELECT COUNT(*) FROM kps WHERE id NOT IN (SELECT DISTINCT kp_id FROM questions)"
        ).fetchone()[0]
        print(f"[{time.time() - t0:6.0f}s] 第{i + 1:3d}轮 +{added} 跳{skipped} "
              f"{r['tokens_used']:6d}tok  待补{left:3d}  无题KP{noq:3d}", flush=True)
finally:
    noq = conn.execute(
        "SELECT COUNT(*) FROM kps WHERE id NOT IN (SELECT DISTINCT kp_id FROM questions)"
    ).fetchone()[0]
    print(flush=True)
    print(f"累计：+{added} 跳过{skipped}  {spent} token  {(time.time() - t0) / 60:.1f} 分钟", flush=True)
    print(f"仍无题的 KP：{noq}", flush=True)
    print(f"本月 token：{db.month_tokens()}", flush=True)
    orch.close()
