"""体检已生成的讲义与题库。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pyai.db.session import Database

db = Database(str(Path(__file__).resolve().parents[1] / "data" / "pyai.db"))
c = db._conn

print("=== 短讲义全文（<200 字）===")
for kid, ex in c.execute(
    "SELECT kp_id, explain FROM kp_content WHERE length(explain)<200 ORDER BY length(explain)"
):
    print(f"  [{kid}] ({len(ex or '')}字) {(ex or '')[:100]!r}")

print()
print("=== 无解析的题 ===")
for qid, kid, stem in c.execute(
    "SELECT id, kp_id, stem FROM questions WHERE coalesce(explanation,'')='' LIMIT 12"
):
    print(f"  {qid} | {kid} | {(stem or '')[:60]}")

print()
print("=== 无 error_tag 的题 ===")
for qid, kid, stem in c.execute(
    "SELECT id, kp_id, stem FROM questions WHERE coalesce(error_tag,'')='' LIMIT 12"
):
    print(f"  {qid} | {kid} | {(stem or '')[:60]}")

print()
print("=== 每 KP 题数分布 ===")
dist = dict(c.execute("SELECT n, COUNT(*) FROM (SELECT kp_id, COUNT(*) n FROM questions GROUP BY kp_id) GROUP BY n").fetchall())
print(" ", dict(sorted(dist.items())))
print("  有讲义的 KP 数:", c.execute("SELECT COUNT(*) FROM kp_content").fetchone()[0])
print("  有题目的 KP 数:", c.execute("SELECT COUNT(DISTINCT kp_id) FROM questions").fetchone()[0])
db.close()
