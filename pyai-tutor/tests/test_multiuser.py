import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from src.pyai.config import Config
from src.pyai.core.orchestrator import Orchestrator
from src.pyai.learning.grading import model_answer

_CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"


class TestMultiUser(unittest.TestCase):
    """多用户隔离：进度 / 通知 / 课程地图各看各的，互不串味。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.cfg = Config(data_dir=Path(self._tmp.name) / "data", content_dir=_CONTENT_DIR)
        self.alice = Orchestrator(self.cfg, user_id="alice")
        self.bob = Orchestrator(self.cfg, user_id="bob")

    def tearDown(self):
        self.alice.close()
        self.bob.close()
        self._tmp.cleanup()

    def test_progress_is_per_user(self):
        questions = self.alice.lesson_questions("s1u1l1")
        result = self.alice.submit_quiz("s1u1l1", [model_answer(q) for q in questions])
        self.assertTrue(result["passed"])
        self.assertEqual(self.alice.status()["next_lesson"], "s1u1l2")

        self.assertEqual(self.bob.status()["next_lesson"], "s1u1l1")
        self.assertFalse(self.bob.db.lesson_passed("bob", "s1u1l1"))

    def test_notifications_are_per_user(self):
        self.alice.db.add_notification("alice", "reminder", "alice 的提醒")
        self.bob.db.add_notification("bob", "reminder", "bob 的提醒")

        self.assertEqual([n["message"] for n in self.alice.notifications()["items"]], ["alice 的提醒"])
        self.assertEqual([n["message"] for n in self.bob.notifications()["items"]], ["bob 的提醒"])

        self.alice.mark_notifications_read()
        self.assertEqual(self.alice.notifications()["unread"], 0)
        self.assertEqual(self.bob.notifications()["unread"], 1)

    def test_both_users_are_listed(self):
        self.assertLessEqual({"alice", "bob"}, {u.id for u in self.alice.db.active_users()})


class TestTokenSpend(unittest.TestCase):
    """计费可见：只有更新烧 token，累计与最近一次都要能查到。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.cfg = Config(data_dir=Path(self._tmp.name) / "data", content_dir=_CONTENT_DIR)
        self.orch = Orchestrator(self.cfg)

    def tearDown(self):
        self.orch.close()
        self._tmp.cleanup()

    def test_status_reports_zero_before_any_update(self):
        ts = self.orch.status()["token_spend"]
        self.assertEqual((ts["runs"], ts["tokens"]), (0, 0))
        self.assertIsNone(ts["last"])

    def test_token_spend_accumulates_and_keeps_last_run(self):
        start = datetime.now()
        db = self.orch.db
        db.log_update("weekly", start, start, 300, 2, 0, "ok")
        db.log_update("manual", start, start + timedelta(seconds=5), 120, 1, 1, "skipped_no_key")

        ts = self.orch.status()["token_spend"]
        self.assertEqual(ts["runs"], 2)
        self.assertEqual(ts["tokens"], 420)
        self.assertEqual(ts["kps_added"], 3)
        self.assertEqual(ts["last"]["kind"], "manual")
        self.assertEqual(ts["last"]["tokens_used"], 120)
        self.assertEqual(ts["last"]["status"], "skipped_no_key")


if __name__ == "__main__":
    unittest.main()
