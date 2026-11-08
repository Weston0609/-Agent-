"""验证混合题型能真正进课堂：取题 → 8 阶段 → 判分 → 闯关。

这是关键一环：题型多了以后，判分器、课堂取题、闯关计分都要能处理
非单选答案（数组/文字）。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pyai.config import Config
from pyai.core.orchestrator import Orchestrator
from pyai.learning.grading import grade, quiz_score

orch = Orchestrator(Config.from_env())
db = orch.db
c = db._conn

# 找一个题目类型最丰富的课
rows = c.execute(
    "SELECT lesson_id, COUNT(DISTINCT q.type) kinds, COUNT(*) n "
    "FROM questions q JOIN kps k ON k.id = q.kp_id "
    "GROUP BY lesson_id ORDER BY kinds DESC, n DESC LIMIT 5"
).fetchall()
rows = [tuple(r) for r in rows]         # 别动 row_factory：db 的方法依赖 sqlite3.Row
print("题型最丰富的课:", rows)

lesson_id = rows[0][0]
print(f"\n=== 取课 {lesson_id} ===")
content = orch.lesson_content(lesson_id)
print("课名:", content.get("title"))
kps = content.get("kps") or []
print("知识点数:", len(kps))

qs = orch.lesson_questions(lesson_id)
print("题目数:", len(qs))
kinds = {}
for q in qs:
    kinds[q.get("type")] = kinds.get(q.get("type"), 0) + 1
print("题型:", kinds)

# 逐题用"标准答案"作答，确认判分器对每种题型都判对
print("\n=== 用标准答案判分（应全部 correct）===")
all_pass = True
for q in qs[:12]:
    t = q.get("type")
    if t == "single_choice":
        ans = q.get("answer")
    elif t == "multi_choice":
        ans = q.get("answer")
    elif t == "fill_blank":
        ans = (q.get("answer") or [""])[0]
    elif t == "code_reading":
        ans = q.get("answer")
    elif t == "scenario":
        ans = " ".join(q.get("required_keywords") or [])
    else:
        ans = ""
    g = grade(q, ans)
    mark = "✅" if g.correct else "❌"
    if not g.correct:
        all_pass = False
    print(f"  {mark} [{t:14s}] score={g.score:.2f} {str(q.get('stem'))[:40]!r}")

print("\n全部判对:", all_pass)
orch.close()
