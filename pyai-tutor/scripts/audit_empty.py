"""定位空题干/空讲义的来源。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pyai.db.session import Database

db = Database(str(Path(__file__).resolve().parents[1] / "data" / "pyai.db"))
c = db._conn
c.row_factory = None  # 用元组，避免 sqlite3.Row 刷屏

print("=== 空题干涉及的 KP ===")
for kid, n in c.execute(
    "SELECT kp_id, COUNT(*) FROM questions WHERE coalesce(trim(stem),'')='' GROUP BY kp_id"
).fetchall():
    print(f"  {kid}: {n} 道空题")

print()
print("=== 这些 KP 的讲义状态 (len, source, verified, generated_at) ===")
for (kid,) in c.execute(
    "SELECT DISTINCT kp_id FROM questions WHERE coalesce(trim(stem),'')=''"
).fetchall():
    row = c.execute(
        "SELECT length(explain), source, verified, generated_at FROM kp_content WHERE kp_id=?", (kid,)
    ).fetchone()
    print(f"  {kid}: {row}")

print()
print("=== 该 KP 的原始 YAML 定义 (id, lesson_id, title) ===")
print(" ", c.execute("SELECT id, lesson_id, title FROM kps WHERE id='py.stdlib.collections'").fetchone())

print()
print("=== 空题干总数 ===")
print(" ", c.execute("SELECT COUNT(*) FROM questions WHERE coalesce(trim(stem),'')=''").fetchone()[0])
print("=== 空讲义总数(trim 后) ===")
print(" ", c.execute("SELECT COUNT(*) FROM kp_content WHERE coalesce(trim(explain),'')=''").fetchone()[0])

print()
print("=== 这四个 KP 的完整题目样本 ===")
for r in c.execute(
    "SELECT id,type,stem,options,answer,explanation,error_tag,variant_group,source "
    "FROM questions WHERE kp_id='py.stdlib.collections' LIMIT 2"
).fetchall():
    print(" ", r)
db.close()
