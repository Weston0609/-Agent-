"""并发安全 + 热路径批量查询回归。

背景：Web 面板是 ThreadingHTTPServer，首屏并发拉 status/map/notifications/users。
此前全进程共用一条 sqlite3 连接，实测 6 线程 72 次调用失败 70 次，抛
InterfaceError: bad parameter or other API misuse —— 表现就是闯关地图永远「载入中…」。
"""
import tempfile
import threading
import unittest
from pathlib import Path

from src.pyai.db.models import Mastery
from src.pyai.db.session import Database
from src.pyai.learning.curriculum import load_curriculum

_ROOT = Path(__file__).resolve().parent.parent
CURRICULUM = load_curriculum(str(_ROOT / "curriculum" / "full_curriculum.yaml"))


class _DbCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self._tmp.name) / "t.db")
        self.db.seed_curriculum(CURRICULUM)

    def tearDown(self):
        self.db.close()
        self._tmp.cleanup()


class TestConcurrentAccess(_DbCase):
    def test_parallel_reads_do_not_raise(self):
        errors: list[str] = []

        def worker():
            try:
                for _ in range(6):
                    self.db.course_tree("default")
                    self.db.passed_lesson_ids("default")
                    self.db.pending_remedial("default")
            except Exception as exc:      # 记下任何一种并发异常，最后统一断言
                errors.append(f"{type(exc).__name__}: {exc}")

        threads = [threading.Thread(target=worker) for _ in range(6)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])


class TestBulkHelpers(_DbCase):
    """批量版必须与逐条版同语义 —— 否则门禁会悄悄放宽或收紧。"""

    def test_passed_lesson_ids_matches_lesson_passed(self):
        self.assertEqual(self.db.passed_lesson_ids("default"), set())
        self.db.record_lesson_score("default", "s1u1l1", 0.9)
        self.db.record_lesson_score("default", "s1u1l2", 0.10)   # 未达 75%，不算通过

        expected = {l.id for l in self.db.all_lessons_in_order()
                    if self.db.lesson_passed("default", l.id)}
        self.assertEqual(self.db.passed_lesson_ids("default"), expected)
        self.assertEqual(expected, {"s1u1l1"})

    def test_kp_lesson_map_covers_every_kp(self):
        mapping = self.db.kp_lesson_map()
        self.assertEqual(len(mapping), self.db.kp_count())
        self.assertEqual(mapping["s1u1l1_1"] if "s1u1l1_1" in mapping else mapping["py.env.install"],
                         "s1u1l1")

    def test_pending_remedial_picks_first_in_curriculum_order(self):
        """按课程顺序取第一个未掌握 KP，而不是掌握度最低的那个。"""
        kps = self.db.all_kps_in_order()
        first, later = kps[0], kps[10]
        for kp, p in ((later, 0.05), (first, 0.60)):
            self.db.save_mastery(Mastery(
                user_id="default", kp_id=kp.id, p_mastery=p, attempts=1, correct=0,
            ))
        self.assertEqual(self.db.pending_remedial("default").id, first.id)

    def test_pending_remedial_ignores_mastered_and_untouched(self):
        kps = self.db.all_kps_in_order()
        self.db.save_mastery(Mastery(                     # 接触过但已过 80% 线
            user_id="default", kp_id=kps[0].id, p_mastery=0.95, attempts=3, correct=3,
        ))
        self.assertIsNone(self.db.pending_remedial("default"))
        self.db.save_mastery(Mastery(                     # 从没作答过，不该算补强
            user_id="default", kp_id=kps[1].id, p_mastery=0.0, attempts=0, correct=0,
        ))
        self.assertIsNone(self.db.pending_remedial("default"))


if __name__ == "__main__":
    unittest.main()
