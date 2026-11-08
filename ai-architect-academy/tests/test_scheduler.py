import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.models import load_curriculum
from src.scheduler import plan_day, _floor_to_lesson_slots
from src.store import Store

CURRICULUM = Path(__file__).resolve().parent.parent / "curriculum" / "curriculum.json"


class TestScheduler(unittest.TestCase):
    def setUp(self):
        self.curriculum = load_curriculum(CURRICULUM)
        self.tmpdir = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmpdir.name) / "test.db")

    def tearDown(self):
        self.store.close()
        self.tmpdir.cleanup()

    def test_every_lesson_is_40_minutes(self):
        now = datetime(2026, 10, 15, 9, 0, 0)
        plan = plan_day(self.curriculum, self.store, now=now)
        self.assertTrue(plan.entries)
        for e in plan.entries:
            self.assertEqual(e.minutes, 40)
            self.assertEqual((e.end_at - e.start_at).total_seconds(), 40 * 60)

    def test_plan_starts_from_first_unlocked(self):
        now = datetime(2026, 10, 15, 9, 0, 0)
        plan = plan_day(self.curriculum, self.store, now=now)
        self.assertEqual(plan.entries[0].lesson_id, "s1u1l1")

    def test_skips_passed_lessons(self):
        self.store.mark_lesson("s1u1l1", "passed", 1.0)
        now = datetime(2026, 10, 15, 9, 0, 0)
        plan = plan_day(self.curriculum, self.store, now=now)
        self.assertEqual(plan.entries[0].lesson_id, "s1u1l2")

    def test_respects_lessons_per_day(self):
        now = datetime(2026, 10, 15, 9, 0, 0)
        plan = plan_day(self.curriculum, self.store, now=now, lessons_per_day=3)
        self.assertEqual(len(plan.entries), 3)

    def test_floor_to_slots(self):
        # 9:10 落在 [8:40, 9:20) 槽内，向下取整到 8:40
        dt = datetime(2026, 10, 15, 9, 10, 0)
        self.assertEqual(_floor_to_lesson_slots(dt, 40), datetime(2026, 10, 15, 8, 40, 0))
        # 10:00 恰在 40 分钟槽边界（600 = 15*40），不变
        dt2 = datetime(2026, 10, 15, 10, 0, 0)
        self.assertEqual(_floor_to_lesson_slots(dt2, 40), dt2)

    def test_all_passed_no_schedule(self):
        for sem in self.curriculum.semesters:
            for u in sem.units:
                for l in u.lessons:
                    self.store.mark_lesson(l.id, "passed", 1.0)
        plan = plan_day(self.curriculum, self.store)
        self.assertEqual(plan.entries, [])
        self.assertIn("全部课程已完成", plan.note)


if __name__ == "__main__":
    unittest.main()
