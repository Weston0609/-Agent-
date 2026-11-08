"""三个「有数据但零入口」的后端：错题本 / 到期复习 / 考试记录。

以前 error_log 只写不读、review_queue 只在首页显示一个数字、exam_results 只能按
scope 单查——数据都在库里，界面上一个入口都没有。这里守住三件事：
① 三个读接口都返回带知识点标题的行（否则界面上只有 `py.env.pip` 这种裸 id）；
② 考试题面不下发 answer / required_keywords（考试比课堂小测更不该泄题）；
③ 跨用户隔离：A 的错题不会出现在 B 的错题本里。
"""
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from src.pyai.config import Config
from src.pyai.core.orchestrator import Orchestrator

_CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"


class TestReviewSurfaces(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        cfg = Config(data_dir=Path(self._tmp.name) / "data", content_dir=_CONTENT_DIR)
        self.orch = Orchestrator(cfg)
        self.addCleanup(self._tmp.cleanup)
        self.addCleanup(self.orch.close)

    def _seed_error(self, kp_id: str, question_id: str | None = None) -> None:
        if question_id is None:
            pool = self.orch.db.questions_for(kp_id)
            question_id = pool[0]["id"] if pool else None
        self.orch.db.record_error(self.orch.user_id, kp_id, question_id, "我的错答", "理解偏差")

    def _seed_due_card(self, kp_id: str) -> None:
        due = self.orch.clock.now() - timedelta(days=1)
        self.orch.db.save_review_card(self.orch.user_id, kp_id,
                                      {"stability": 1.0, "difficulty": 5.0, "reps": 2, "lapses": 0},
                                      due)

    def test_error_items_carry_kp_title_and_lesson(self):
        kp_id = self.orch.db.lesson_kp_ids("s1u1l1")[0]
        self._seed_error(kp_id)

        d = self.orch.error_items()
        self.assertEqual(d["count"], 1)
        row = d["items"][0]
        self.assertEqual(row["kp_id"], kp_id)
        self.assertTrue(row["kp_title"], "错题卡要能显示知识点名")
        self.assertEqual(row["lesson_id"], "s1u1l1")
        self.assertEqual(row["user_answer"], "我的错答")
        self.assertIsNotNone(row["question_id"])

    def test_error_items_are_per_user(self):
        kp_id = self.orch.db.lesson_kp_ids("s1u1l1")[0]
        self._seed_error(kp_id)
        other = Orchestrator(self.orch.config, user_id="someone-else")
        self.addCleanup(other.close)
        self.assertEqual(other.error_items()["count"], 0, "错题本不能串用户")

    def test_review_items_join_title_and_only_due(self):
        kp_id = self.orch.db.lesson_kp_ids("s1u1l1")[0]
        self._seed_due_card(kp_id)
        # 一张还没到期的卡不该出现
        future_kp = self.orch.db.lesson_kp_ids("s1u1l2")[0]
        self.orch.db.save_review_card(self.orch.user_id, future_kp,
                                      {"stability": 30.0, "difficulty": 5.0, "reps": 1, "lapses": 0},
                                      self.orch.clock.now() + timedelta(days=30))

        d = self.orch.review_items()
        self.assertEqual(d["count"], 1)
        row = d["items"][0]
        self.assertEqual(row["kp_id"], kp_id)
        self.assertIn("kp_title", row)
        self.assertIn("lesson_name", row)

    def test_exam_results_lists_recorded_exams(self):
        self.assertEqual(self.orch.exam_results()["count"], 0)
        for lesson_id in self.orch.db.scope_lesson_ids("unit", "s1u1"):
            self.orch.db.record_lesson_score(self.orch.user_id, lesson_id, 1.0)
        qs = self.orch.exam_questions("unit", "s1u1")
        self.orch.submit_exam("unit", "s1u1", ["__错__"] * len(qs))

        d = self.orch.exam_results()
        self.assertEqual(d["count"], 1)
        row = d["items"][0]
        self.assertEqual((row["scope"], row["scope_id"]), ("unit", "s1u1"))
        self.assertEqual(row["attempts"], 1)
        self.assertFalse(row["passed"])

    def test_exam_view_does_not_leak_answers(self):
        for lesson_id in self.orch.db.scope_lesson_ids("unit", "s1u1"):
            self.orch.db.record_lesson_score(self.orch.user_id, lesson_id, 1.0)
        view = self.orch.exam_view("unit", "s1u1")
        self.assertGreater(len(view["questions"]), 0)
        for q in view["questions"]:
            self.assertNotIn("answer", q, "考试题面不能带标准答案")
            self.assertNotIn("required_keywords", q, "关键词就是答案，不能下发")
            self.assertTrue(q["stem"], "题干必须有")
        # 与交卷时的题序一致，否则按题面顺序交上去的答案会错位
        self.assertEqual([q["id"] for q in view["questions"]],
                         [q["id"] for q in self.orch.exam_questions("unit", "s1u1")])

    def test_exam_view_locked_scope_has_no_questions(self):
        view = self.orch.exam_view("unit", "s1u1")
        self.assertEqual(view["questions"], [])
        self.assertFalse(view["status"]["ready"])


if __name__ == "__main__":
    unittest.main()
