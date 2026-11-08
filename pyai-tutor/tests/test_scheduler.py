import tempfile
import unittest
from datetime import date
from pathlib import Path

from src.pyai.db.session import Database
from src.pyai.learning.curriculum import load_curriculum
from src.pyai.learning.scheduler import _pick_next_lesson, plan_lessons

_CURRICULUM_PATH = Path(__file__).resolve().parent.parent / "curriculum" / "full_curriculum.yaml"
CURRICULUM = load_curriculum(str(_CURRICULUM_PATH))


def make_db() -> tuple[Database, tempfile.TemporaryDirectory]:
    tmp = tempfile.TemporaryDirectory()
    db = Database(Path(tmp.name) / "test.db")
    db.seed_curriculum(CURRICULUM)
    return db, tmp


def pass_lesson(db: Database, lesson_id: str, user_id: str = "default", score: float = 1.0) -> None:
    """学校式闯关门禁：测验达标即通过该课（通过后课程 DAG 才放行）。"""
    db.record_lesson_score(user_id, lesson_id, score)


class TestScheduler(unittest.TestCase):
    def setUp(self):
        self.db, self._tmp = make_db()

    def tearDown(self):
        self.db.close()
        self._tmp.cleanup()

    def test_plan_three_consecutive_lessons(self):
        # 学校模式：学期内无逐课门禁，120 分钟排 3 节连续新课（40 分钟/节，无重复）
        plan = plan_lessons(self.db, "default", 120, date(2026, 1, 5))
        self.assertEqual(len(plan), 3)
        ids = [e["lesson_id"] for e in plan]
        self.assertEqual(ids, ["s1u1l1", "s1u1l2", "s1u1l3"])
        self.assertEqual(len(set(ids)), 3)
        self.assertTrue(all(e["minutes"] == 40 for e in plan))

    def test_pick_next_skips_passed_lesson(self):
        self.assertEqual(_pick_next_lesson(self.db, "default").id, "s1u1l1")
        pass_lesson(self.db, "s1u1l1")
        self.assertEqual(_pick_next_lesson(self.db, "default").id, "s1u1l2")

    def test_failed_quiz_does_not_advance(self):
        pass_lesson(self.db, "s1u1l1", score=0.5)   # 未达标
        self.assertFalse(self.db.lesson_passed("default", "s1u1l1"))
        self.assertEqual(_pick_next_lesson(self.db, "default").id, "s1u1l1")

    def test_semester_gate_opens_after_previous_semester_done(self):
        # 未完成学期 1 前，停留在学期 1 内
        self.assertEqual(_pick_next_lesson(self.db, "default").semester_id, "s1")
        # 通过学期 1 全部课的测验 → 解锁学期 2
        for lesson in [l for l in self.db.all_lessons_in_order() if l.semester_id == "s1"]:
            pass_lesson(self.db, lesson.id)
        self.assertEqual(_pick_next_lesson(self.db, "default").semester_id, "s2")

    def test_plan_empty_when_all_done(self):
        for lesson in self.db.all_lessons_in_order():
            pass_lesson(self.db, lesson.id)
        self.assertEqual(plan_lessons(self.db, "default", 120, date(2026, 1, 5)), [])


if __name__ == "__main__":
    unittest.main()
