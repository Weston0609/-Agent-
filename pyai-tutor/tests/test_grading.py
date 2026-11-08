import unittest

from src.pyai.learning.grading import grade, grade_quiz, model_answer, passed, quiz_score


class TestCodeReadingIsWinnable(unittest.TestCase):
    """回归：code_reading 曾经是整串比对，参考答案是整段自然语言 → 永远答不对。

    Boss 卷子里只要抽到 1 道就够不到 85% 通关线（12 题里错 1 道 = 91.7% 还行，
    但 2 道就只剩 83.3%）——这是实测把玩家卡死的真实缺陷。
    """

    LONG_ANSWER = ("会安装到当前用户级的 site-packages（用户目录下的 Python 用户包目录），"
                   "而不是系统全局 site-packages。因为使用了 --user，pip 将包安装到用户目录。")

    def test_freeform_answer_scores_above_zero(self):
        q = {"type": "code_reading", "answer": self.LONG_ANSWER, "required_keywords": []}
        g = grade(q, "用了 --user，装到用户目录的 site-packages，不写系统目录")
        self.assertTrue(g.correct, "用自己的话讲清楚必须算对")
        # 不再要求满分：说中了 site / packages / user 三个采分点但漏了 python，
        # 覆盖度 0.75 过线即可。满分留给逐字复述。
        self.assertGreaterEqual(g.score, 0.5)

    def test_verbatim_answer_still_full_marks(self):
        q = {"type": "code_reading", "answer": self.LONG_ANSWER, "required_keywords": []}
        self.assertEqual(grade(q, self.LONG_ANSWER).score, 1.0)

    def test_empty_and_lazy_answers_fail(self):
        q = {"type": "code_reading", "answer": self.LONG_ANSWER, "required_keywords": []}
        self.assertFalse(grade(q, "").correct)
        self.assertFalse(grade(q, "   ").correct)
        self.assertFalse(grade(q, "不知道").correct, "敷衍不能算答对")

    def test_required_keywords_take_precedence(self):
        q = {"type": "code_reading", "answer": "x",
             "required_keywords": ["--user", "用户目录", "site-packages"]}
        self.assertTrue(grade(q, "--user 装到用户目录的 site-packages").correct)
        self.assertFalse(grade(q, "--user 装到 site-packages").correct)

    def test_long_but_empty_answer_fails(self):
        """回归：以前「够 12 个字」就满分，写一坨废话也能过 Boss。"""
        q = {"type": "code_reading", "answer": self.LONG_ANSWER, "required_keywords": []}
        lazy = "随便写一点内容凑够十二个字就行了啊反正老师也不知道"
        self.assertFalse(grade(q, lazy).correct, "没说到任何采分点不能算对")

    def test_answer_naming_the_output_passes(self):
        """真实题（py.type.str_index-q15）：问输出，答对输出值就算过——这是多数 code_reading 的形态。"""
        q = {"type": "code_reading", "answer": '"e"', "required_keywords": [],
             "stem": '阅读代码并写出输出：\ns = "abcdef"\nprint(s[1:5][-1])'}
        self.assertTrue(grade(q, "打印出 e，因为切片后最后一个字符是 e").correct)
        self.assertFalse(grade(q, "打印出 a，因为下标从 0 开始").correct)

    def test_model_answer_gets_full_marks(self):
        q = {"type": "code_reading", "answer": self.LONG_ANSWER, "required_keywords": []}
        self.assertEqual(grade(q, model_answer(q)).score, 1.0)

    def test_option_form_is_graded_like_single_choice(self):
        """前端把带 options 的 code_reading 画成单选按钮、交选项下标。

        这条不测就等于没修：整串比对时代这里的下标永远不等于字符串答案。
        """
        q = {"type": "code_reading", "options": ["装到用户目录", "装到系统目录"],
             "answer": 0, "required_keywords": []}
        self.assertTrue(grade(q, 0).correct)
        self.assertFalse(grade(q, 1).correct)
        self.assertFalse(grade(q, -1).correct, "没选不能算对")

    def test_boss_paper_is_winnable_with_perfect_play(self):
        """整卷一题不错时必须正好 100%——这是 85% 通关线存在的前提。"""
        from src.pyai.learning.grading import grade_quiz
        qs = [
            {"type": "single_choice", "answer": 0, "options": ["a", "b"]},
            {"type": "code_reading", "answer": 1, "options": ["x", "y"]},
            {"type": "code_reading", "answer": self.LONG_ANSWER, "required_keywords": []},
            {"type": "multi_choice", "answer": [0, 1]},
            {"type": "fill_blank", "answer": ["venv"]},
        ]
        answers = [0, 1, self.LONG_ANSWER, [0, 1], "venv"]
        self.assertAlmostEqual(quiz_score(grade_quiz(qs, answers)), 1.0)


class TestGrading(unittest.TestCase):
    def test_single_choice(self):
        q = {"type": "single_choice", "answer": 0}
        self.assertTrue(grade(q, 0).correct)
        self.assertEqual(grade(q, 0).score, 1.0)
        self.assertFalse(grade(q, 1).correct)
        self.assertEqual(grade(q, 1).error_type, "概念混淆")

    def test_multi_choice_exact(self):
        q = {"type": "multi_choice", "answer": [0, 1]}
        self.assertTrue(grade(q, [0, 1]).correct)
        self.assertEqual(grade(q, [0, 1]).score, 1.0)

    def test_multi_choice_partial_score(self):
        q = {"type": "multi_choice", "answer": [0, 1, 2]}
        g = grade(q, [0, 1])
        self.assertFalse(g.correct)
        self.assertAlmostEqual(g.score, 2 / 3)

    def test_fill_blank_normalizes(self):
        q = {"type": "fill_blank", "answer": ["Hello World"]}
        self.assertTrue(grade(q, " hello, world ").correct)

    def test_scenario_keyword_match(self):
        q = {"type": "scenario", "required_keywords": ["cache", "async"]}
        self.assertTrue(grade(q, "we use cache and async").correct)

    def test_quiz_score_and_passed(self):
        qs = [
            {"type": "single_choice", "answer": 0},
            {"type": "single_choice", "answer": 1},
        ]
        grades = grade_quiz(qs, [0, 0])
        self.assertAlmostEqual(quiz_score(grades), 0.5)
        self.assertFalse(passed(quiz_score(grades), 0.75))
        self.assertTrue(passed(0.75, 0.75))


if __name__ == "__main__":
    unittest.main()
