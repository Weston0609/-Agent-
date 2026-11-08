import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from src.pyai.db.session import Database
from src.pyai.learning.fsrs import schedule_next

NOW = datetime(2026, 1, 1, 12, 0, 0)


class TestFSRS(unittest.TestCase):
    def test_new_card_good_returns_dict_and_future_due(self):
        card, due = schedule_next(None, True, NOW)
        self.assertIsInstance(card, dict)
        self.assertGreater(due, NOW)

    def test_again_due_within_ten_minutes(self):
        _, due = schedule_next(None, False, NOW)
        self.assertLess(due - NOW, timedelta(minutes=10))

    def test_roundtrip_card_state(self):
        card, _ = schedule_next(None, True, NOW)
        later = NOW + timedelta(minutes=10)
        card2, due2 = schedule_next(card, True, later)
        self.assertIsInstance(card2, dict)
        self.assertGreater(due2, later)


class TestReviewCardDBRoundtrip(unittest.TestCase):
    """回归：卡片经数据库存/取后必须还能重建（第二次复习曾崩 KeyError: 'card_id'）。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self._tmp.name) / "t.db")

    def tearDown(self):
        self.db.close()
        self._tmp.cleanup()

    def test_saved_card_survives_db_roundtrip(self):
        card, due = schedule_next(None, True, NOW)
        self.db.save_review_card("u1", "py.env.install", card, due)

        stored = self.db.get_review_card("u1", "py.env.install")
        self.assertIsNotNone(stored)
        self.assertIn("card_id", stored.card)

        later = NOW + timedelta(days=1)
        card2, due2 = schedule_next(stored.card, True, later)   # 曾在此抛 KeyError
        self.assertIn("card_id", card2)
        self.assertGreater(due2, later)


if __name__ == "__main__":
    unittest.main()
