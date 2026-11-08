"""验证种子文件能完整重建题库（含全部题型与字段）。"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pyai.config import Config
from pyai.core.orchestrator import Orchestrator

tmp = Path(tempfile.mkdtemp(prefix="verify-seed-"))
orch = Orchestrator(Config(data_dir=tmp / "data", content_dir=Path("content")))
c = orch.db._conn

print("讲义:", c.execute("SELECT COUNT(*) FROM kp_content").fetchone()[0], "/", orch.db.kp_count())
print("题目:", c.execute("SELECT COUNT(*) FROM questions").fetchone()[0])
print("题型:", {r[0]: r[1] for r in c.execute(
    "SELECT type, COUNT(*) FROM questions GROUP BY type").fetchall()})

empty = c.execute(
    "SELECT COUNT(*) FROM questions WHERE stem IS NULL OR TRIM(stem)=''").fetchone()[0]
noexp = c.execute(
    "SELECT COUNT(*) FROM questions WHERE explanation IS NULL OR TRIM(explanation)=''").fetchone()[0]
print("空题干:", empty, " 空解析:", noexp)

sc = c.execute(
    "SELECT COUNT(*) FROM questions WHERE type='scenario' "
    "AND (required_keywords IS NULL OR required_keywords IN ('','[]'))").fetchone()[0]
print("缺 required_keywords 的场景题:", sc)

tot = c.execute("SELECT COUNT(*) FROM lessons").fetchone()[0]
full = c.execute(
    "SELECT COUNT(*) FROM (SELECT l.id FROM lessons l JOIN kps k ON k.lesson_id=l.id "
    "GROUP BY l.id HAVING SUM(CASE WHEN EXISTS(SELECT 1 FROM kp_content kc WHERE kc.kp_id=k.id) "
    "THEN 1 ELSE 0 END)=COUNT(*))"
).fetchone()[0]
print(f"完整可上课: {full}/{tot}")

orch.close()
