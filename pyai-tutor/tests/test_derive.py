"""中文标题 + 题目难度回填的回归线。

库里 lessons.name 与 kps.title 长期等于裸 id（面板上到处是 `s1u1l1`），
questions.difficulty 也全部是常量 1（s8 的 K8s 题和 s1 的 print 题一样难）。
derive.backfill 在启动时从讲义正文与课程位置把这两列算出来。这里守住三件事：
① 三级标题回退（H1 → 术语对 → 加粗词）都能抽出中文，抽不到才退回 id 末段；
② 难度随课程位置单调上升，且被夹在 1..5；
③ 回填幂等：第二次跑靠 user_version 直接跳过，不会重写。
"""
import tempfile
import unittest
from pathlib import Path

from src.pyai.config import Config
from src.pyai.core.orchestrator import Orchestrator
from src.pyai.db import derive

_CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"


class TestTitleExtraction(unittest.TestCase):
    def test_h1_is_used_verbatim(self):
        text = "# 位置编码（Position Encoding）\n\n## 一句话直觉\n\n把第几个词写进向量。\n"
        self.assertEqual(derive.kp_title(text, "ai.llm.position_encoding"),
                         "位置编码（Position Encoding）")

    def test_kp_id_prefix_is_stripped_from_h1(self):
        text = "# py.env.install：从零搭建可复现的开发环境\n"
        self.assertEqual(derive.kp_title(text, "py.env.install"),
                         "从零搭建可复现的开发环境")

    def test_generic_heading_falls_through_to_term_pair(self):
        # 没有 H1、首行是通用小节名 —— 得靠正文里「中文（English）」这一对
        text = ("## 一句话直觉\n\n"
                "**位置编码（Position Encoding）** 就是把“第几个词”写进向量。\n")
        self.assertEqual(derive.kp_title(text, "ai.llm.position_encoding"), "位置编码")

    def test_bold_lead_is_the_last_resort(self):
        text = "## 一句话直觉\n\n**类型注解（Type Hint）** 就像给代码贴上标签。\n"
        self.assertTrue(derive.kp_title(text, "py.typehint.basic").startswith("类型注解"))

    def test_literal_backslash_n_is_unescaped_first(self):
        # 69 篇讲义把换行写成了字面 \n，整篇挤成一行 —— 不还原就抽不出 H1
        text = "# Python 注释\\n\\n## 一句话直觉\\n\\n注释是写给人看的。"
        self.assertEqual(derive.kp_title(text, "py.syntax.comment"), "Python 注释")

    def test_narrative_sentence_is_rejected(self):
        # 首段是叙述句时不能拿来当标题，宁可退回 id 末段
        text = "## 一句话直觉\n\n如果你把一个 Agent 改了一行提示词就上线，你怎么知道它没变笨？\n"
        self.assertEqual(derive.kp_title(text, "agent.eng.eval_ci"), "eval ci")

    def test_colon_inside_code_span_does_not_split(self):
        text = '# `if __name__ == "__main__":` 完全指南\n'
        self.assertEqual(derive.kp_title(text, "py.module.if_main"),
                         '`if __name__ == "__main__":` 完全指南')

    def test_unbalanced_bracket_is_dropped(self):
        self.assertEqual(derive.clip("Agent 工程中的缓存（Caching", 32),
                         "Agent 工程中的缓存")


class TestDifficulty(unittest.TestCase):
    def test_tier_spans_one_to_five_across_the_course(self):
        tiers = [derive.tier(i, 178) for i in range(178)]
        self.assertEqual(min(tiers), 1)
        self.assertEqual(max(tiers), 5)
        self.assertEqual(tiers, sorted(tiers), "课程越往后档位只能越高")

    def test_harder_question_types_get_a_bump(self):
        base, mid = 2, "中" * 60          # 题干长度落在 40..120，不触发长度修正
        self.assertEqual(derive.question_difficulty(base, "single_choice", mid), 2)
        self.assertEqual(derive.question_difficulty(base, "scenario", mid), 3)
        self.assertEqual(derive.question_difficulty(base, "code_reading", mid), 3)
        self.assertGreater(derive.question_difficulty(base, "code_reading", "```x```"),
                           derive.question_difficulty(base, "single_choice", mid))

    def test_stays_within_range(self):
        for base in (1, 3, 5):
            for qtype in ("single_choice", "multi_choice", "code_reading", "scenario", None):
                for stem in ("", "短", "长" * 200, "```\ncode\n```"):
                    d = derive.question_difficulty(base, qtype, stem)
                    self.assertGreaterEqual(d, 1)
                    self.assertLessEqual(d, 5)


class TestBackfill(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        cfg = Config(data_dir=Path(self._tmp.name) / "data", content_dir=_CONTENT_DIR)
        self.orch = Orchestrator(cfg)          # 启动时已经回填过一次
        self.addCleanup(self._tmp.cleanup)
        self.addCleanup(self.orch.close)

    def test_every_kp_and_lesson_has_a_chinese_name(self):
        db = self.orch.db
        bare_kps = db._conn.execute(
            "SELECT COUNT(*) FROM kps WHERE title = id").fetchone()[0]
        bare_lessons = db._conn.execute(
            "SELECT COUNT(*) FROM lessons WHERE name = id").fetchone()[0]
        self.assertEqual(bare_kps, 0, "知识点名不能还是裸 id")
        self.assertEqual(bare_lessons, 0, "课名不能还是裸 id")

    def test_questions_are_graded_across_all_five_levels(self):
        levels = {r[0] for r in self.orch.db._conn.execute(
            "SELECT DISTINCT difficulty FROM questions").fetchall()}
        self.assertEqual(levels, {1, 2, 3, 4, 5})

    def test_second_run_is_a_noop(self):
        self.assertEqual(derive.backfill(self.orch.db), {"skipped": True})


if __name__ == "__main__":
    unittest.main()
