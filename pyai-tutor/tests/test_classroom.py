"""课堂升级的两个离线模块：大白话卡片 + 课堂互动。

两个模块的铁律是同一句：**不新增知识**。所以测试盯的也是这条——
提炼不出原文就宁可不出卡片，选项与答案必须原样来自题库。
"""
import unittest

from src.pyai.core import interactions, plainlang


class TestPlainLang(unittest.TestCase):
    def test_extracts_intuition_and_conclusion_from_lecture_text(self):
        explain = (
            "> **一句话直觉**：虚拟环境就是给每个项目一个独立的小房间。\n\n"
            "正文……\n\n"
            "**关键结论**：不同项目的依赖互不打架。\n"
        )
        p = plainlang.build(explain)
        self.assertTrue(p["has_any"])
        self.assertIn("小房间", p["intuition"])
        self.assertIn("互不打架", p["conclusion"])
        # 标签本身不该被抄进卡片里
        self.assertNotIn("一句话直觉", p["intuition"])
        self.assertNotIn("关键结论", p["conclusion"])

    def test_code_hint_uses_authored_chinese_comment_only(self):
        code = "# -*- coding: utf-8 -*-\n# demo.py\n# venv/virtualenv 会设置 sys.prefix != sys.baseprefix\nprint(1)\n"
        p = plainlang.build("正文", code)
        self.assertEqual(p["code_hint"], "venv/virtualenv 会设置 sys.prefix != sys.baseprefix")

    def test_returns_none_when_nothing_extractable(self):
        # 没有一句话直觉/结论/中文注释/坑 → 宁可不给卡片，也不编一句话
        self.assertIsNone(plainlang.build("一段没有任何标记的普通正文。", "# plain english comment\nx=1"))
        self.assertIsNone(plainlang.build("", ""))

    def test_pitfall_only_is_enough_to_show_card(self):
        p = plainlang.build("正文", "", pitfalls="1. 忘记激活虚拟环境就装包，会污染全局。")
        self.assertTrue(p["has_any"])
        self.assertIn("污染全局", p["pitfall"])
        self.assertEqual(p["intuition"], "")


class TestInteractions(unittest.TestCase):
    # 能被 _flip 改写的句子：含否定词，或句首主语+动词性关键词。故意选前者（最稳）。
    FLIPPABLE = "pip 不会把包装进系统 Python 的全局环境里。"

    def _kp(self, kp_id="py.demo", title="演示", explain=""):
        return {"id": kp_id, "title": title, "ok": True, "explain": explain, "example_code": "", "pitfalls": ""}

    def _judge_explain(self):
        return f"> **一句话直觉**：{self.FLIPPABLE}"

    def test_public_payload_never_leaks_the_answer(self):
        kp = self._kp(explain=self._judge_explain())
        built = interactions.build([kp], {}, per_kp=1)
        item = built["items"]["py.demo"]
        self.assertEqual(item["type"], "judge")
        self.assertIn("answer", item)                            # 服务端判分要用
        self.assertNotIn("answer", interactions.public(item))    # 下发前端必须剥掉
        self.assertNotIn("wrong_hint", interactions.public(item))

    def test_check_judges_synthetic_sentence_items(self):
        item = interactions.build([self._kp(explain=self._judge_explain())], {}, per_kp=1)["items"]["py.demo"]
        self.assertTrue(interactions.check(item, item["answer"])["correct"])
        self.assertFalse(interactions.check(item, 1 - int(item["answer"]))["correct"])

    def test_judge_item_comes_from_the_lecture_sentence_itself(self):
        item = interactions.build([self._kp(explain=self._judge_explain())], {}, per_kp=1)["items"]["py.demo"]
        # 题干就是讲义原句：不新增讲义之外的知识
        self.assertEqual(item["stem"], self.FLIPPABLE)

    def test_bank_question_is_reused_verbatim_with_its_own_answer(self):
        kp = self._kp()
        pool = {"py.demo": [{"id": "q1", "type": "single_choice", "stem": "print 的作用？",
                             "options": ["输出到控制台", "保存文件", "读输入"],
                             "answer": 0, "explanation": "print 输出到标准输出。"}]}
        item = interactions.build([kp], pool, per_kp=1)["items"]["py.demo"]
        self.assertEqual(item["id"], "q1")
        self.assertEqual(item["stem"], "print 的作用？")
        self.assertEqual(item["answer"], 0)
        self.assertEqual(item["options"], ["输出到控制台", "保存文件", "读输入"])
        self.assertTrue(interactions.check(item, 0)["correct"])
        self.assertFalse(interactions.check(item, 1)["correct"])
        # 答错的提示应指向讲义解释，而不是空话
        self.assertIn("print", interactions.check(item, 1)["hint"])

    def test_typing_questions_are_skipped(self):
        # 填空/场景题要打字，不适合「停顿一下点个选项」的互动节奏
        kp = self._kp()
        pool = {"py.demo": [{"id": "q1", "type": "fill_blank", "stem": "写个关键字", "answer": "def"}]}
        self.assertEqual(interactions.build([kp], pool, per_kp=1)["items"], {})

    def test_unflippable_sentence_yields_no_item(self):
        # 既没题、原句又改不动 → 跳过互动本身，不硬凑一道（宁可不互动也不教错）
        kp = self._kp(explain="> **一句话直觉**：pip 从包索引下载并安装发行包。")
        self.assertEqual(interactions.build([kp], {}, per_kp=1)["items"], {})

    def test_id_is_stable_across_rebuilds(self):
        # 刷新/重进课堂不能换题：同一个句子必须得到同一个 id
        kp = self._kp(explain=self._judge_explain())
        a = interactions.build([kp], {}, per_kp=1)["items"]["py.demo"]["id"]
        b = interactions.build([kp], {}, per_kp=1)["items"]["py.demo"]["id"]
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
