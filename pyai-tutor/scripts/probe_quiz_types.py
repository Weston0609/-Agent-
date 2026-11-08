"""实跑一次新模板，看模型是否真的产出多题型。"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pyai.config import Config
from pyai.updater.kp_generator import generate_quiz
from pyai.updater.pipeline import select_llm
from pyai.learning.grading import grade

cfg = Config.from_env()
llm, backend = select_llm(cfg)
print("backend =", backend)

kp = {"id": "py.stdlib.collections", "title": "py.stdlib.collections"}
qs = generate_quiz(llm, kp, n_variants=8, prompt_dir=cfg.prompt_dir)
print(f"通过准入的题数: {len(qs)}")
print()
kinds = {}
for q in qs:
    kinds[q.get("type")] = kinds.get(q.get("type"), 0) + 1
print("题型分布:", kinds)
print()
for q in qs:
    print(f"[{q.get('type')}] {(q.get('stem') or '')[:64]}")
    print(f"    answer={q.get('answer')!r}  error_tag={q.get('error_tag')!r}")
    print(f"    explanation={(q.get('explanation') or '')[:50]!r}")
    # 每种题型都真的过一遍判分器
    if q.get("type") == "single_choice":
        g = grade(q, q.get("answer"))
    elif q.get("type") == "multi_choice":
        g = grade(q, q.get("answer"))
    elif q.get("type") == "fill_blank":
        g = grade(q, (q.get("answer") or [""])[0])
    elif q.get("type") == "code_reading":
        g = grade(q, q.get("answer"))
    elif q.get("type") == "scenario":
        g = grade(q, " ".join(q.get("required_keywords") or []))
    else:
        continue
    print(f"    → 判分: correct={g.correct} score={g.score:.2f}")
    print()
