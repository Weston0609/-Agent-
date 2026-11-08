import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.models import load_curriculum
from src.store import Store
from src.unlock import available_exams, compute_states, next_unlocked_lesson, semester_passed

CURRICULUM = Path(__file__).resolve().parent.parent / "curriculum" / "curriculum.json"


class TestUnlock(unittest.TestCase):
    def setUp(self):
        self.curriculum = load_curriculum(CURRICULUM)
        self.tmpdir = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmpdir.name) / "test.db")

    def tearDown(self):
        self.store.close()
        self.tmpdir.cleanup()

    def test_initial_state_single_unlocked(self):
        states = compute_states(self.curriculum, self.store)
        unlocked = [lid for lid, s in states.items() if s.status == "unlocked"]
        self.assertEqual(unlocked, ["s1u1l1"])
        # 其余全部 locked
        locked = [lid for lid, s in states.items() if s.status == "locked"]
        self.assertEqual(len(locked), self.curriculum.total_lessons - 1)

    def test_next_unlocked_is_first_lesson(self):
        states = compute_states(self.curriculum, self.store)
        self.assertEqual(next_unlocked_lesson(self.curriculum, states).id, "s1u1l1")

    def test_serial_unlock_within_unit(self):
        # 通过 s1u1l1 后，s1u1l2 解锁
        self.store.mark_lesson("s1u1l1", "passed", 1.0)
        states = compute_states(self.curriculum, self.store)
        self.assertEqual(states["s1u1l1"].status, "passed")
        self.assertEqual(states["s1u1l2"].status, "unlocked")
        self.assertEqual(states["s1u1l3"].status, "locked")

    def test_unit_gate_requires_exam(self):
        # 学完整个 s1u1 的课，但没考单元考，s1u2l1 仍锁
        for lid in ("s1u1l1", "s1u1l2", "s1u1l3"):
            self.store.mark_lesson(lid, "passed", 1.0)
        states = compute_states(self.curriculum, self.store)
        self.assertEqual(states["s1u2l1"].status, "locked")
        # 考过单元考后解锁
        self.store.record_exam("s1u1", "unit", 0.875, True)
        states = compute_states(self.curriculum, self.store)
        self.assertEqual(states["s1u2l1"].status, "unlocked")

    def test_semester_gate_requires_final(self):
        # 通过 s1 全部课 + 全部单元考，但期末考没过，s2 仍锁
        for sem in self.curriculum.semesters[0].units:
            for lesson in sem.lessons:
                self.store.mark_lesson(lesson.id, "passed", 1.0)
        for sem in self.curriculum.semesters[0].units:
            self.store.record_exam(sem.id, "unit", 1.0, True)
        # 没考期末
        states = compute_states(self.curriculum, self.store)
        self.assertEqual(states["s2u1l1"].status, "locked")
        # 考过期末后解锁 s2
        self.store.record_exam("s1-final", "final", 1.0, True)
        states = compute_states(self.curriculum, self.store)
        self.assertEqual(states["s2u1l1"].status, "unlocked")

    def test_total_counts(self):
        # 课程总课数 = 各学期之和（忠实转录原 YAML：178 课 / 385 个知识点）
        self.assertEqual(self.curriculum.total_lessons, 178)
        self.assertEqual(
            self.curriculum.total_lessons,
            sum(len(u.lessons) for s in self.curriculum.semesters for u in s.units),
        )
        self.assertEqual(self.curriculum.total_kps, 385)
        # 知识点无重复
        all_kps = [k for s in self.curriculum.semesters for u in s.units for l in u.lessons for k in l.kps]
        self.assertEqual(len(set(all_kps)), len(all_kps))


    def test_available_exams_unit_and_final(self):
        # 学完 s1u1 的课 → 出现 s1u1 单元考
        for lid in ("s1u1l1", "s1u1l2", "s1u1l3"):
            self.store.mark_lesson(lid, "passed", 1.0)
        exams = available_exams(self.curriculum, self.store)
        self.assertEqual([e["id"] for e in exams], ["s1u1"])
        # 通过 s1u1 单元考后，s1u1 从列表消失（未学完 s1u2，期末考也不出现）
        self.store.record_exam("s1u1", "unit", 1.0, True)
        exams = available_exams(self.curriculum, self.store)
        self.assertEqual(exams, [])
        # 学完整个 s1 + 全部单元考 → 出现 s1 期末考
        for unit in self.curriculum.semesters[0].units:
            for lesson in unit.lessons:
                self.store.mark_lesson(lesson.id, "passed", 1.0)
        for unit in self.curriculum.semesters[0].units:
            self.store.record_exam(unit.id, "unit", 1.0, True)
        exams = available_exams(self.curriculum, self.store)
        self.assertEqual([e["id"] for e in exams], ["s1-final"])


if __name__ == "__main__":
    unittest.main()
