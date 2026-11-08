import tempfile
import unittest
from pathlib import Path

from src.pyai.db.session import Database
from src.pyai.tools.notifier import Notifier


class TestNotifications(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self._tmp.name) / "t.db")
        self.db.ensure_default_user()

    def tearDown(self):
        self.db.close()
        self._tmp.cleanup()

    def test_add_and_unread_counter(self):
        self.assertEqual(self.db.unread_count("default"), 0)
        self.db.add_notification("default", "class", "上课啦")
        self.db.add_notification("default", "recall", "还有 1 节未完成")
        self.assertEqual(self.db.unread_count("default"), 2)
        self.assertEqual(self.db.notifications("default")[0]["kind"], "recall")  # 最新在前

    def test_mark_read_is_idempotent(self):
        self.db.add_notification("default", "info", "x")
        self.assertEqual(self.db.mark_notifications_read("default"), 1)
        self.assertEqual(self.db.unread_count("default"), 0)
        self.assertEqual(self.db.mark_notifications_read("default"), 0)

    def test_notifier_persists_to_inbox(self):
        Notifier(self.db).send("default", "上课啦", kind="class")
        items = self.db.notifications("default")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["message"], "上课啦")
        self.assertEqual(items[0]["kind"], "class")

    def test_notifier_disabled_does_not_persist(self):
        Notifier(self.db, enabled=False).send("default", "x")
        self.assertEqual(self.db.unread_count("default"), 0)

    def test_notifier_without_db_still_works(self):
        Notifier().send("default", "hello")   # 仅打印


if __name__ == "__main__":
    unittest.main()
