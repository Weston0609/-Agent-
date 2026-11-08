"""清理已落库的残缺题，并报告会受影响的 KP。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pyai.db.session import Database
from pyai.updater.kp_generator import _is_wellformed

db = Database(str(Path(__file__).resolve().parents[1] / "data" / "pyai.db"))
c = db._conn
c.row_factory = None

rows = c.execute(
    "SELECT id, kp_id, type, stem, options, answer FROM questions"
).fetchall()
print("清理前题数:", len(rows))

bad_ids = []
per_kp_ok: dict[str, int] = {}
for qid, kp, qtype, stem, opts, ans in rows:
    import json as _json
    try:
        o = _json.loads(opts) if opts else []
    except Exception:
        o = []
    try:
        a = _json.loads(ans) if ans is not None else None
    except Exception:
        a = ans
    q = {"type": qtype, "stem": stem, "options": o, "answer": a}
    if _is_wellformed(q):
        per_kp_ok[kp] = per_kp_ok.get(kp, 0) + 1
    else:
        bad_ids.append((qid, kp))

print("残缺题:", len(bad_ids))
by_kp: dict[str, int] = {}
for qid, kp in bad_ids:
    by_kp[kp] = by_kp.get(kp, 0) + 1
print("涉及 KP:", by_kp)

print()
print("=== 清理后每个受影响 KP 还剩多少题 ===")
for kp in by_kp:
    print(f"  {kp:26s} 剩 {per_kp_ok.get(kp, 0)} 道")

print()
print("=== 清理后整库题数 ===")
print(" ", len(rows) - len(bad_ids))
print()
print("=== 每个 KP 题数 < 10 的（可能影响出卷）===")
thin = [(k, n) for k, n in per_kp_ok.items() if n < 10]
print(" ", thin or "无")
db.close()
