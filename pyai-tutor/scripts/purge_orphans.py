"""清理孤儿内容：kp_id 不在 kps 表里的 kp_content / questions。

来源是已停用的「阶段 4 知识树扩建」——它让模型凭空发明 KP id（如 s2_kp_006）
并直接写库。停用后这些 KP 的课程树行没有建起来，内容就成了悬空数据：
不属于任何课，学生永远读不到，但会污染统计（390/385）与题库总数。

默认只报告，加 --apply 才真删。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pyai.db.session import Database

APPLY = "--apply" in sys.argv

db = Database(str(Path(__file__).resolve().parents[1] / "data" / "pyai.db"))
c = db._conn

orphan_kp = [r[0] for r in c.execute(
    "SELECT kp_id FROM kp_content WHERE kp_id NOT IN (SELECT id FROM kps)"
).fetchall()]
orphan_q = c.execute(
    "SELECT COUNT(*) FROM questions WHERE kp_id NOT IN (SELECT id FROM kps)"
).fetchone()[0]

print(f"孤儿讲义 {len(orphan_kp)} 条，孤儿题目 {orphan_q} 道：")
for k in orphan_kp:
    print("  ", k)

if not APPLY:
    print("\n（只报告；加 --apply 才真删）")
    db.close()
    raise SystemExit(0)

if orphan_kp:
    marks = ",".join("?" * len(orphan_kp))
    c.execute(f"DELETE FROM kp_content WHERE kp_id IN ({marks})", orphan_kp)
    c.execute(f"DELETE FROM questions WHERE kp_id IN ({marks})", orphan_kp)
    c.commit()

print(f"\n已删除孤儿讲义 {len(orphan_kp)} 条、孤儿题目 {orphan_q} 道")
print("剩余讲义:", c.execute("SELECT COUNT(*) FROM kp_content").fetchone()[0], "/", db.kp_count())
print("剩余题目:", c.execute("SELECT COUNT(*) FROM questions").fetchone()[0])
db.close()
