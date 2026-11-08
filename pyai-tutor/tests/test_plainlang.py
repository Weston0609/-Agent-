"""大白话卡片提炼 —— 必须认得讲义里「一句话直觉」的两种写法。

背景：生成讲义绝大多数用「## 一句话直觉」标题式，而旧实现只认「**一句话直觉**：」同行式，
导致 178 课里 51% 的知识点卡片只剩一行代码注释，等于没做。
"""
from __future__ import annotations

import unittest

from src.pyai.core.plainlang import build


class TestInlineStyle(unittest.TestCase):
    """A 型：**一句话直觉**：xxxx。"""

    def test_inline_quote(self):
        out = build("**一句话直觉**：`print` 是程序对外说话的第一句。\n\n后面是正文。")
        self.assertEqual(out["intuition"], "print 是程序对外说话的第一句。")

    def test_inline_conclusion(self):
        out = build("**关键结论**：`print` 把参数转成人类可读文本。")
        self.assertEqual(out["conclusion"], "print 把参数转成人类可读文本。")


class TestHeadingStyle(unittest.TestCase):
    """B 型：## 一句话直觉 换行 正文（存量讲义大量使用这种）。"""

    def test_heading_quote_bold_paragraph(self):
        explain = (
            "## 一句话直觉\n\n"
            "**写 Python 代码之前，先让 Python 能跑起来，且各项目依赖不打架。**\n\n"
            "## 1. 为什么需要它\n\n正文……\n"
        )
        out = build(explain)
        self.assertEqual(
            out["intuition"],
            "写 Python 代码之前，先让 Python 能跑起来，且各项目依赖不打架。",
        )

    def test_heading_quote_plain_paragraph(self):
        explain = "## 一句话直觉\n\n程序需要从外部拿数据才能活起来。\n\n## 1. 什么是输入\n\n……\n"
        out = build(explain)
        self.assertEqual(out["intuition"], "程序需要从外部拿数据才能活起来。")

    def test_heading_conclusion(self):
        explain = "## 关键结论\n\n`sep` 管参数之间怎么连，`end` 管结尾补什么。\n\n## 2. 下一节\n\n……\n"
        out = build(explain)
        self.assertEqual(out["conclusion"], "sep 管参数之间怎么连，end 管结尾补什么。")

    def test_heading_section_stops_at_next_heading(self):
        """标题式只取本节内容，不能把后面几节的正文吞进来。"""
        explain = (
            "## 一句话直觉\n\n第一句就是重点。\n\n"
            "## 1. 下一节\n\n这里的内容绝不能被当成直觉。\n"
        )
        self.assertEqual(build(explain)["intuition"], "第一句就是重点。")


class TestNoFabrication(unittest.TestCase):
    """铁律：抽不出原文就不给，绝不自己编一句。"""

    def test_no_section_returns_none(self):
        self.assertIsNone(build("## 1. 随便一节\n\n正文，没有一句话直觉。\n"))

    def test_list_item_is_not_used_as_intuition(self):
        """标题下若是列表而不是散文，不算「一句话」。"""
        explain = "## 一句话直觉\n\n- 要点一\n- 要点二\n"
        self.assertIsNone(build(explain))

    def test_heading_needs_own_line(self):
        """正文里顺口提到「一句话直觉」四个字，不应被当成标题。"""
        explain = "这段话里提到一句话直觉但并不是标题。\n\n## 1. 正文\n\n……\n"
        self.assertIsNone(build(explain))


class TestExampleExtraction(unittest.TestCase):
    """「举个例」必须来自原文标志词，且不能是列表/要点罗列。"""

    def test_extracts_sentence_with_marker(self):
        explain = "## 1. 为什么需要虚拟环境\n\n假设你同时开发两个项目，它们要的 requests 版本不一样。\n"
        self.assertIn("假设", build(explain)["example"])

    def test_skips_list_paragraph(self):
        explain = "假设有三点：\n- 第一点内容比较长\n- 第二点内容比较长\n- 第三点内容比较长\n"
        out = build(explain)
        self.assertTrue(out is None or not out.get("example"))

    def test_skips_code_block(self):
        explain = "比如下面这段：\n\n```python\nprint(1)\n```\n"
        out = build(explain)
        self.assertTrue(out is None or not out.get("example"))

    def test_example_differs_from_intuition(self):
        """例子和「一句话直觉」不能是同一句，否则卡片上下重复。"""
        same = "虚拟环境就是给每个项目一个小房间，让依赖互不打架。"
        explain = f"## 一句话直觉\n\n{same}\n\n## 1. 正文\n\n{same}\n"
        out = build(explain)
        self.assertTrue(out is None or not out.get("example"))


if __name__ == "__main__":
    unittest.main()
