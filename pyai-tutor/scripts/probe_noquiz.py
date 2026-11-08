"""排查：31 个有讲义却无题的 KP，是生成了被删，还是压根没生成题。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pyai.db.session import Database

db = Database("data/pyai.db")
c = db._conn

NOQ = [r[0] for r in c.execute(
    "SELECT id FROM kps WHERE id NOT IN (SELECT DISTINCT kp_id FROM questions)"
).fetchall()]
print(f"有讲义无题的 KP: {len(NOQ)}")

print("\n=== 它们的讲义状态 ===")
for k in NOQ[:8]:
    r = c.execute(
        "SELECT length(coalesce(explain,'')), length(coalesce(example_code,'')), source, generated_at "
        "FROM kp_content WHERE kp_id=?", (k,)
    ).fetchone()
    print(f"  {k:28s} {tuple(r) if r else None}")

print("\n=== 全库讲义生成时间（按小时）===")
for r in c.execute(
    "SELECT substr(generated_at,1,13) h, COUNT(*) n FROM kp_content GROUP BY h ORDER BY h"
).fetchall():
    print("  ", tuple(r))

print("\n=== 这些 KP 分布在哪些课 ===")
for r in c.execute(
    "SELECT l.id, COUNT(*) n FROM lessons l JOIN kps k ON k.lesson_id=l.id "
    "WHERE k.id NOT IN (SELECT DISTINCT kp_id FROM questions) GROUP BY l.id ORDER BY l.id"
).fetchall():
    print("  ", tuple(r))
db.close()
