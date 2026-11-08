import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.grading import grade, passed


class TestGrading(unittest.TestCase):
    def test_full_correct(self):
        q = [{"answer": 0}, {"answer": 1}, {"answer": 2}, {"answer": 0}]
        self.assertEqual(grade(q, [0, 1, 2, 0]), 1.0)

    def test_three_of_four(self):
        q = [{"answer": 0}, {"answer": 1}, {"answer": 2}, {"answer": 0}]
        self.assertAlmostEqual(grade(q, [0, 1, 2, 3]), 0.75)

    def test_short_submit_counts_wrong(self):
        q = [{"answer": 0}, {"answer": 1}]
        self.assertEqual(grade(q, [0]), 0.5)

    def test_empty(self):
        self.assertEqual(grade([], []), 0.0)

    def test_threshold(self):
        self.assertTrue(passed(0.75, 0.75))
        self.assertFalse(passed(0.749, 0.75))
        # 4 题通过需 3 题 = 75%
        self.assertTrue(passed(3 / 4, 0.75))


if __name__ == "__main__":
    unittest.main()
