"""结项体检：内容覆盖 / 题库质量 / 全课可上性 / token 用量。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pyai.db.session import Database

db = Database("data/pyai.db")
c = db._conn

print("=== 讲义覆盖 ===")
print(db.covered_summary())

print("\n=== 题库 ===")
print("总题数:", c.execute("SELECT COUNT(*) FROM questions").fetchone()[0])
rows = c.execute("SELECT type, COUNT(*) FROM questions GROUP BY type").fetchall()
print("题型:", {r[0]: r[1] for r in rows})
empty = c.execute("SELECT COUNT(*) FROM questions WHERE stem IS NULL OR TRIM(stem)=''").fetchone()[0]
print("空题干:", empty)
bad_opt = c.execute(
    "SELECT COUNT(*) FROM questions WHERE type IN ('single_choice','multi_choice') "
    "AND (options IS NULL OR options IN ('','[]','null'))"
).fetchone()[0]
print("无选项的选择题:", bad_opt)

print(f"\n=== 全 {c.execute('SELECT COUNT(*) FROM lessons').fetchone()[0]} 课可上性 ===")
tot = c.execute("SELECT COUNT(*) FROM lessons").fetchone()[0]
any_ok = c.execute(
    "SELECT COUNT(*) FROM (SELECT l.id FROM lessons l JOIN kps k ON k.lesson_id=l.id "
    "JOIN kp_content kc ON kc.kp_id=k.id GROUP BY l.id)"
).fetchone()[0]
full = c.execute(
    "SELECT COUNT(*) FROM (SELECT l.id FROM lessons l JOIN kps k ON k.lesson_id=l.id "
    "GROUP BY l.id HAVING SUM(CASE WHEN EXISTS(SELECT 1 FROM kp_content kc WHERE kc.kp_id=k.id) "
    "THEN 1 ELSE 0 END)=COUNT(*))"
).fetchone()[0]
print(f"至少一个 KP 有讲义（能开课）: {any_ok}/{tot}")
print(f"全部 KP 都有讲义（完整）    : {full}/{tot}")

print("\n=== 讲义长度分布 ===")
lens = [len(r[0] or "") for r in c.execute("SELECT explain FROM kp_content").fetchall()]
lens.sort()
if lens:
    print(f"min={lens[0]} 中位={lens[len(lens)//2]} max={lens[-1]} 平均={sum(lens)//len(lens)}")
    print("过短(<200字):", sum(1 for x in lens if x < 200))

print("\n=== 按月 token ===")
for r in c.execute(
    "SELECT substr(started_at,1,7) m, SUM(tokens_used) t, COUNT(*) n FROM updates_log "
    "GROUP BY m ORDER BY m"
).fetchall():
    print(f"  {r[0]}: {r[1]} token / {r[2]} 次")

db.close()
