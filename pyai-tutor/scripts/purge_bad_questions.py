"""清理残缺题，并让受影响的 KP 重新进入生成队列。

残缺题（空题干/答案越界）是旧代码没有准入校验时落库的。清掉之后，
这些 KP 会变成「有讲义但没题」，不能只删题——要把讲义也撤掉，
让 find_unfilled_kps 重新看见它们，下一轮连同题库一起重生。

默认只报告，加 --apply 才真删。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pyai.db.session import Database
from pyai.updater.kp_generator import _is_wellformed

APPLY = "--apply" in sys.argv

db = Database(str(Path(__file__).resolve().parents[1] / "data" / "pyai.db"))
c = db._conn
c.row_factory = None

import json as _json

rows = c.execute("SELECT id, kp_id, type, stem, options, answer FROM questions").fetchall()

bad: dict[str, list[str]] = {}
for qid, kp, qtype, stem, opts, ans in rows:
    try:
        o = _json.loads(opts) if opts else []
    except Exception:
        o = []
    try:
        a = _json.loads(ans) if ans is not None else None
    except Exception:
        a = ans
    if not _is_wellformed({"type": qtype, "stem": stem, "options": o, "answer": a}):
        bad.setdefault(kp, []).append(qid)

print(f"残缺题 {sum(len(v) for v in bad.values())} 道，涉及 {len(bad)} 个 KP：")
for kp, ids in bad.items():
    print(f"  {kp}: {len(ids)} 道")

if not APPLY:
    print()
    print("（只报告；加 --apply 才真删）")
    db.close()
    raise SystemExit(0)

if bad:
    for kp, ids in bad.items():
        marks = ",".join("?" * len(ids))
        c.execute(f"DELETE FROM questions WHERE id IN ({marks})", ids)
        c.execute("DELETE FROM kp_content WHERE kp_id = ?", (kp,))
    c.commit()

print()
print(f"已删除残缺题 {sum(len(v) for v in bad.values())} 道，"
      f"并撤销 {len(bad)} 个 KP 的讲义使其重新入队")
print("剩余题数:", c.execute("SELECT COUNT(*) FROM questions").fetchone()[0])
print("剩余讲义:", c.execute("SELECT COUNT(*) FROM kp_content").fetchone()[0])
print("待生成:", len(db.find_unfilled_kps(limit=9999)))
db.close()
