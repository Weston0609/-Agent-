"""批量生成离线讲义 —— 可中断、可续跑。

用法：python -X utf8 -u scripts/genall.py [每轮 KP 数]
反复调用 run_weekly_update 直到没有待生成 KP，或连续多轮零进展。
进程被 Ctrl-C / 杀死后直接重跑即可，find_unfilled_kps 天然只返回还没讲的。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pyai.config import Config  # noqa: E402
from pyai.core.orchestrator import Orchestrator  # noqa: E402
from pyai.updater.pipeline import run_weekly_update  # noqa: E402

BATCH = int(sys.argv[1]) if len(sys.argv) > 1 else 3
MAX_ROUNDS = 400
IDLE_TOLERANCE = 3  # 连续多少轮零进展就收工

orch = Orchestrator(Config.from_env())
db = orch.db
conn = db._conn
t0 = time.time()
spent = added = skipped = 0
idle = 0

print(f"起始：{db.kp_count()} 个知识点，待生成 {len(db.find_unfilled_kps(limit=9999))}", flush=True)

try:
    for i in range(MAX_ROUNDS):
        if not db.find_unfilled_kps(limit=1):
            print("✅ 全部知识点都有讲义了", flush=True)
            break

        r = run_weekly_update(db, manual=True, max_kps=BATCH)
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

        left = len(db.find_unfilled_kps(limit=9999))
        done = conn.execute("SELECT COUNT(*) FROM kp_content").fetchone()[0]
        print(
            f"[{time.time() - t0:6.0f}s] 第{i + 1:3d}轮 "
            f"+{r['kps_added']} 跳{r['kps_skipped']} "
            f"{r['tokens_used']:6d}tok  剩{left:3d}  共{done}/{db.kp_count()}",
            flush=True,
        )
finally:
    print(flush=True)
    print(
        f"累计：+{added} 跳过{skipped}  {spent} token  {(time.time() - t0) / 60:.1f} 分钟",
        flush=True,
    )
    print(f"有讲义：{conn.execute('SELECT COUNT(*) FROM kp_content').fetchone()[0]} / {db.kp_count()}", flush=True)
    print(f"本月 token：{db.month_tokens()}", flush=True)
    orch.close()
