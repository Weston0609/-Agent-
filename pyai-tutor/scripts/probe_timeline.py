"""核对空题干 KP 的写入时间线与当前队列状态。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pyai.db.session import Database

db = Database(str(Path(__file__).resolve().parents[1] / "data" / "pyai.db"))
c = db._conn
c.row_factory = None

BAD = ("py.stdlib.collections", "py.io.with", "py.func.args_default", "ai.embed.bge_m3")

print("=== 空题干 KP 的讲义生成时间 ===")
for kp in BAD:
    row = c.execute(
        "SELECT generated_at, source, verified, version FROM kp_content WHERE kp_id=?", (kp,)
    ).fetchone()
    print(f"  {kp:26s} {row}")

print()
print("=== 全库讲义生成时间范围（判断这些是不是最早那批）===")
print(" ", c.execute("SELECT MIN(generated_at), MAX(generated_at) FROM kp_content").fetchone())
print(" 共", c.execute("SELECT COUNT(*) FROM kp_content").fetchone()[0], "条")

print()
print("=== 最早 12 条讲义 ===")
for kp, ts in c.execute(
    "SELECT kp_id, generated_at FROM kp_content ORDER BY generated_at LIMIT 12"
).fetchall():
    print(f"  {ts}  {kp}")

print()
print("=== 空题干题的 id 是否带 -qN 后缀（generate_quiz 打的）===")
for r in c.execute(
    "SELECT id, stem IS NULL, length(coalesce(stem,'')) FROM questions "
    "WHERE kp_id='py.io.with' LIMIT 4"
).fetchall():
    print(" ", r)

print()
print("=== 这 4 个 KP 现在还在待生成队列里吗 ===")
for kp in BAD:
    in_content = c.execute("SELECT 1 FROM kp_content WHERE kp_id=?", (kp,)).fetchone()
    print(f"  {kp:26s} 有讲义={bool(in_content)}")
db.close()
