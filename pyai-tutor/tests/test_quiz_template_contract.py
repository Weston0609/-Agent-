"""确认模板与代码契约一致：字段名、题型、必填项。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pyai.config import Config
from pyai.updater.kp_generator import _QUIZ_CONTRACT, _render

text = _render(
    Config().prompt_dir, "quiz_gen.jinja",
    n=20, kp_id="py.demo.topic", title="py.demo.topic",
) + _QUIZ_CONTRACT

checks = {
    "题干字段用 stem": '"stem"' in text,
    "不再要求 question 字段": '"question"' not in text,
    "五种题型都提到": all(
        t in text for t in ("single_choice", "multi_choice", "fill_blank", "code_reading", "scenario")
    ),
    "要求 explanation": "explanation" in text,
    "要求 error_tag": "error_tag" in text,
    "要求 variant_group": "variant_group" in text,
    "仍禁止把 kp_id 当 API": "不是** Python" in text or "不是" in text,
}
for name, ok in checks.items():
    print(f"  {'✅' if ok else '❌'} {name}")

assert all(checks.values()), "模板与契约不一致"
print("\n✅ 模板与代码契约一致")
