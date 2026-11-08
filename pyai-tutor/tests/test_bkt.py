import unittest

from src.pyai.db.session import KP_PASS, LESSON_PASS
from src.pyai.learning.bkt import BKTParams, fit_params, update


class TestBKT(unittest.TestCase):
    def test_correct_increases_mastery(self):
        self.assertGreater(update(0.2, 1.0), 0.2)

    def test_incorrect_decreases_mastery(self):
        self.assertLess(update(0.2, 0.0), 0.2)

    def test_repeated_correct_converges_high(self):
        p = 0.2
        for _ in range(20):
            p = update(p, 1.0)
        self.assertGreater(p, 0.9)

    def test_clamped_to_unit_interval(self):
        self.assertGreaterEqual(update(0.99, 0.0), 0.0)
        self.assertLessEqual(update(0.99, 1.0), 1.0)

    def test_fit_params_returns_defaults(self):
        self.assertEqual(fit_params([]), BKTParams())

    def test_mastery_line_is_reachable_but_not_on_first_attempt(self):
        """第六部分约束：知识点线 80%。BKT 是阶跃的，第 1 次必然到不了、第 2 次必到，
        且 75%/80% 两条线落在同一台阶之间（改阈值不改变闯关行为）。"""
        self.assertEqual((KP_PASS, LESSON_PASS), (0.80, 0.75))

        first = update(0.2, 1.0)
        self.assertLess(first, KP_PASS, "第一次作答不应直接判定掌握")
        self.assertLess(first, LESSON_PASS)

        second = update(first, 1.0)
        self.assertGreaterEqual(second, KP_PASS, "第二次作答应跨越知识点线")


if __name__ == "__main__":
    unittest.main()
