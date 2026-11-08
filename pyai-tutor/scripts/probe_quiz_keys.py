"""抓一次真实模型返回，看题目字段到底叫什么名字。"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pyai.config import Config
from pyai.updater.kp_generator import _QUIZ_CONTRACT, _render
from pyai.updater.pipeline import select_llm

cfg = Config.from_env()
llm, backend = select_llm(cfg)
print("backend =", backend)
assert backend != "none", "没有可用后端"

kp_id = "py.stdlib.collections"
prompt = _render(cfg.prompt_dir, "quiz_gen.jinja", n=3, kp_id=kp_id, title=kp_id)
prompt += _QUIZ_CONTRACT

raw = llm.chat(prompt)
print("=== 原始返回（前 1600 字符）===")
print(raw[:1600])
print()
print("=== 解析后的键名 ===")
data = json.loads(raw)
if isinstance(data, dict):
    data = data.get("questions", [])
for i, q in enumerate(data[:3]):
    print(f"  [{i}] 键 = {list(q.keys())}")
    print(f"      stem  = {q.get('stem')!r}")
    print(f"      question = {q.get('question')!r}")
    print(f"      title = {q.get('title')!r}")
