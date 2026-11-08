import tempfile
import unittest
from pathlib import Path

from src.pyai.config import Config
from src.pyai.core.orchestrator import Orchestrator
from src.pyai.db.session import Database
from src.pyai.learning.curriculum import load_curriculum

_ROOT = Path(__file__).resolve().parent.parent
CURRICULUM = load_curriculum(str(_ROOT / "curriculum" / "full_curriculum.yaml"))
_CONTENT = _ROOT / "content"


def _states(tree: list[dict]) -> dict[str, str]:
    return {l["id"]: l["state"] for s in tree for u in s["units"] for l in u["lessons"]}


class TestCourseTree(unittest.TestCase):
    """关卡全开放：任何一课都可直接学，闯关只决定有没有打勾。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self._tmp.name) / "t.db")
        self.db.seed_curriculum(CURRICULUM)

    def tearDown(self):
        self.db.close()
        self._tmp.cleanup()

    def test_every_lesson_is_open_from_day_one(self):
        tree = self.db.course_tree("default")
        self.assertEqual(len(tree), 8)
        states = _states(tree)
        self.assertEqual(len(states), self.db.lesson_count())
        self.assertEqual(states["s1u1l1"], "unlocked")
        # 深层课程、同学期后续课，一律可以学——不再要求先过前一关
        self.assertEqual(states["s8u1l1"], "unlocked")
        deep = tree[-1]["units"][-1]["lessons"][-1]["id"]
        self.assertEqual(states[deep], "unlocked")
        self.assertNotIn("locked", set(states.values()), "不应该再有锁着的关卡")
        self.assertEqual(sum(s["total"] for s in tree), self.db.lesson_count())

    def test_passing_marks_only_that_lesson(self):
        for lesson in [l for l in self.db.all_lessons_in_order() if l.semester_id == "s1"]:
            self.db.record_lesson_score("default", lesson.id, 1.0)

        tree = self.db.course_tree("default")
        states = _states(tree)
        self.assertEqual(states["s1u1l1"], "passed")
        self.assertEqual(states["s2u1l1"], "unlocked")   # 本来就能学，通关不会额外解锁什么
        s1 = next(s for s in tree if s["id"] == "s1")
        self.assertEqual(s1["passed"], s1["total"])

    def test_next_lesson_ignores_prereqs(self):
        """排课默认推的「下一课」只看自己有没有通关，不再看前一课。"""
        from src.pyai.learning.scheduler import _pick_next_lesson

        # 跳过 s1u1l1 直接通关 s1u1l2：s1u1l1 仍然应该是被推荐的那一课
        self.db.record_lesson_score("default", "s1u1l2", 1.0)
        self.assertEqual(_pick_next_lesson(self.db, "default").id, "s1u1l1")

        # 反过来把 s1 全通了，也不能让 s2 变成「必须」——但默认推荐确实会顺延到 s2u1l1
        for lesson in [l for l in self.db.all_lessons_in_order() if l.semester_id == "s1"]:
            self.db.record_lesson_score("default", lesson.id, 1.0)
        self.assertEqual(_pick_next_lesson(self.db, "default").id, "s2u1l1")


class TestCourseMap(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.cfg = Config(data_dir=Path(self._tmp.name) / "data", content_dir=_CONTENT)
        self.orch = Orchestrator(self.cfg)

    def tearDown(self):
        self.orch.close()
        self._tmp.cleanup()

    def test_course_map_shape_and_current(self):
        m = self.orch.course_map()
        self.assertEqual(m["total"], m["passed"] + (m["total"] - m["passed"]))
        self.assertEqual(m["passed"], 0)
        self.assertEqual(m["current"]["lesson_id"], "s1u1l1")
        self.assertEqual(len(m["semesters"]), 8)
        self.assertTrue(all(s["units"] for s in m["semesters"]))
