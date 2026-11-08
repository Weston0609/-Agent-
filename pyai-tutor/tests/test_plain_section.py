"""大白话卡片必须跟着小节翻页变化（回归测试，纯字符串层面，不起浏览器）。

前端 `sectionPlain()` 在 index.html 里，这里按同一套规则复刻一份最小实现做对拍，
保证「不同小节 -> 不同卡片」和「代码块/标点不会被当成说白了」两条不变量。
"""
import re
import unittest
from pathlib import Path

HTML = Path(__file__).resolve().parent.parent / "src/pyai/ui/web/templates/index.html"


def section_plain(md: str):
    """与 index.html 里 sectionPlain() 同规则的最小复刻。"""
    text = str(md or "")
    if not text.strip():
        return None

    def plain(s):
        s = re.sub(r"```[\s\S]*?```", "", str(s))
        s = re.sub(r"^#{1,6}\s*", "", s, flags=re.M)
        s = re.sub(r"[`*_>|]", "", s)
        return re.sub(r"\s+", " ", s).strip()

    def cut(s):
        t = plain(s)
        m = re.match(r"(.*?[。！？!?])", t)
        return (m.group(1) if m else t)[:120]

    example = ""
    ex = re.search(r"(假设|比如说|比如|例如|举个例子|就像|好比|相当于)[^\n]{8,}", text)
    if ex:
        line = text[ex.start():].split("\n\n")[0]
        if not re.match(r"^[-*+\d#|]", line.strip()) and "```" not in line:
            example = cut(line)
    key = ""
    bold = re.search(r"\*\*([^*\n]{6,110})\*\*", text)
    if bold:
        key = plain(bold.group(1))[:110]
    if not example and not key:
        first = next((s.strip() for s in re.split(r"\n\s*\n", text)
                      if s.strip() and not re.match(r"^[-*+\d#|>]", s.strip())
                      and not s.strip().startswith("```") and not re.fullmatch(r"-{3,}", s.strip())), "")
        if first:
            key = cut(first)
    if not example and not key:
        return None
    return {"intuition": key, "example": example, "has_any": True}


class TestSectionPlain(unittest.TestCase):
    def test_sections_yield_different_cards(self):
        md = ("## 0. 为什么先装环境\n\n写代码前你要先让 Python 跑起来。\n\n"
              "## 1. 安装\n\n务必勾选 Add Python to PATH。\n\n"
              "## 2. pip\n\npip 是官方包管理器。\n")
        sections = [s for s in re.split(r"(?m)^##\s+", md) if s.strip()]
        cards = [section_plain(s) for s in sections]
        self.assertEqual(len({c["intuition"] for c in cards}), len(cards))

    def test_code_block_is_not_used_as_plain_language(self):
        card = section_plain("```python\nimport requests\nprint(requests.__version__)\n```")
        self.assertIsNone(card)

    def test_punctuation_only_section_yields_nothing(self):
        self.assertIsNone(section_plain("---\n\n---"))

    def test_example_sentence_is_preferred(self):
        card = section_plain("假设你有两个项目，各自需要不同版本的库，它们就会互相打架。")
        self.assertIn("互相打架", card["example"] or card["intuition"])

    def test_frontend_wires_section_into_plain_card(self):
        html = HTML.read_text(encoding="utf-8")
        self.assertIn("plainCard(kp, part)", html, "renderStep 必须把当前小节传给 plainCard")
        self.assertIn("function sectionPlain(md)", html)
        self.assertIn("sectionPlain(part.body)", html)


if __name__ == "__main__":
    unittest.main()
