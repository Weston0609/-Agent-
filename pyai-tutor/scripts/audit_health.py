"""确认净化后的题库状态。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pyai.db.session import Database

db = Database(str(Path(__file__).resolve().parents[1] / "data" / "pyai.db"))
c = db._conn
c.row_factory = None

empty = c.execute("SELECT COUNT(*) FROM questions WHERE coalesce(trim(stem),'')=''").fetchone()[0]
total = c.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
lect = c.execute("SELECT COUNT(*) FROM kp_content").fetchone()[0]
print(f"题库总数: {total}   空题干: {empty}   讲义: {lect}/{db.kp_count()}")

print()
print("受影响 4 个 KP 的现状（题数 / 是否有讲义）:")
for k in ("py.stdlib.collections", "py.io.with", "py.func.args_default", "ai.embed.bge_m3"):
    n = c.execute("SELECT COUNT(*) FROM questions WHERE kp_id=?", (k,)).fetchone()[0]
    has = c.execute("SELECT 1 FROM kp_content WHERE kp_id=?", (k,)).fetchone() is not None
    print(f"  {k:26s} 题数={n:3d}  讲义={has}")
db.close()
