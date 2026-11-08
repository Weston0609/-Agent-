"""结项核验：内容完整性 + 孤儿记录排查。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pyai.db.session import Database

db = Database("data/pyai.db")
c = db._conn

print("=== 计数 ===")
print("kps        :", c.execute("SELECT COUNT(*) FROM kps").fetchone()[0])
print("kp_content :", c.execute("SELECT COUNT(*) FROM kp_content").fetchone()[0])
print("questions  :", c.execute("SELECT COUNT(*) FROM questions").fetchone()[0])

print("\n=== 孤儿讲义（kp_id 不在 kps 表里）===")
orphans = c.execute(
    "SELECT kp_id, length(coalesce(explain,'')), source FROM kp_content "
    "WHERE kp_id NOT IN (SELECT id FROM kps)"
).fetchall()
for r in orphans:
    print("  ", tuple(r))
print("  合计:", len(orphans))

print("\n=== 孤儿题目（kp_id 不在 kps 表里）===")
oq = c.execute(
    "SELECT kp_id, COUNT(*) FROM questions WHERE kp_id NOT IN (SELECT id FROM kps) GROUP BY kp_id"
).fetchall()
for r in oq:
    print("  ", tuple(r))
print("  合计 KP:", len(oq), " 题:", sum(r[1] for r in oq))

print("\n=== 仍有缺口的 KP ===")
missing = c.execute(
    "SELECT id FROM kps WHERE id NOT IN (SELECT kp_id FROM kp_content)"
).fetchall()
print("  ", [r[0] for r in missing] or "无 ✅")

print(f"\n=== 全 {c.execute('SELECT COUNT(*) FROM lessons').fetchone()[0]} 课覆盖 ===")
tot = c.execute("SELECT COUNT(*) FROM lessons").fetchone()[0]
full = c.execute(
    "SELECT COUNT(*) FROM (SELECT l.id FROM lessons l JOIN kps k ON k.lesson_id=l.id "
    "GROUP BY l.id HAVING SUM(CASE WHEN EXISTS(SELECT 1 FROM kp_content kc WHERE kc.kp_id=k.id) "
    "THEN 1 ELSE 0 END)=COUNT(*))"
).fetchone()[0]
print(f"  全部 KP 都有讲义: {full}/{tot}")

print("\n=== 无题的 KP ===")
noq = c.execute(
    "SELECT id FROM kps WHERE id NOT IN (SELECT DISTINCT kp_id FROM questions)"
).fetchall()
print("  ", [r[0] for r in noq] or "无 ✅")

db.close()
