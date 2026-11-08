"""验证：有讲义无题的 KP 是否因为整批题目被校验全部丢弃。"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pyai.config import Config
from pyai.updater.kp_generator import _is_wellformed, generate_quiz
from pyai.updater.pipeline import select_llm

cfg = Config.from_env()
llm, backend = select_llm(cfg)
print("backend =", backend)

# 取一个已知「有讲义无题」的 KP 实跑一次
kp_id = "py.flow.if"
kp = {"id": kp_id, "title": kp_id}
qs = generate_quiz(llm, kp, n_variants=8, prompt_dir=cfg.prompt_dir)
print(f"{kp_id}: 通过准入 {len(qs)} 道")
kinds = {}
for q in qs:
    kinds[q.get("type")] = kinds.get(q.get("type"), 0) + 1
print("题型:", kinds)
for q in qs[:4]:
    print(f"  [{q.get('type')}] {(q.get('stem') or '')[:50]!r}")
    print(f"      explanation={bool(q.get('explanation'))} error_tag={bool(q.get('error_tag'))}")
