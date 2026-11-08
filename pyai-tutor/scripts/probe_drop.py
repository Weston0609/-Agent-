"""复现空题干：把当年的输入喂给 generate_quiz 的清洗逻辑。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pyai.updater.kp_generator import _mentions_kp_id

BAD = ["py.stdlib.collections", "py.io.with", "py.func.args_default", "ai.embed.bge_m3"]

print("=== _mentions_kp_id 的判定 ===")
for kp in BAD:
    for stem in [
        f"下列关于 {kp} 的说法正确的是？",
        f"阅读下面代码，关于 {kp} 的输出是？",
        "关于 deque 的描述哪项正确？",
    ]:
        print(f"  {kp:26s} {_mentions_kp_id(stem, kp)!s:5s} | {stem}")

print()
print("=== 关键点：dotted id 命中率 ===")
for kp in BAD:
    print(f"  {kp}: 含点的 id → 模型几乎每道题都会提到它")
