"""章节考 / 学期考层级。

第六部分约束表：章节考 ≥70%，学期考 ≥75%，知识点 ≥80%，单元考 ≥75%。
本文件锁住四条线的分工，以及「范围内课程全过才能考」的门禁。
"""
import tempfile
import unittest
from pathlib import Path

from src.pyai.config import Config
from src.pyai.core.orchestrator import Orchestrator
from src.pyai.db.session import CHAPTER_PASS, KP_PASS, LESSON_PASS, SEMESTER_PASS

ROOT = Path(__file__).resolve().parent.parent


class TestExamTiers(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.orch = Orchestrator(Config(data_dir=Path(self._tmp.name)))
        self.addCleanup(self._tmp.cleanup)
        self.addCleanup(self.orch.close)

    def _pass_all_lessons(self, scope: str, scope_id: str, score: float = 1.0):
        """把范围内每课都考到满分（模拟学生学完）。"""
        for lesson_id in self.orch.db.scope_lesson_ids(scope, scope_id):
            self.orch.db.record_lesson_score(self.orch.user_id, lesson_id, score)

    def _perfect_answers(self, questions):
        """按题型给出真正满分的作答——必须照判分规则来，不能一律取 answer[0]。

        多选只给第一项会按部分分扣（15 道多选就能把满分卷拉到 0.43），
        填空的 answer 是可接受写法列表，场景题没有标准答案、按 required_keywords 命中。
        """
        out = []
        for q in questions:
            answer = q.get("answer")
            if q["type"] == "multi_choice":
                out.append(list(answer or []))
            elif q["type"] == "fill_blank":
                out.append((answer or [""])[0])
            elif q["type"] == "scenario":
                out.append("、".join(q.get("required_keywords") or []))
            else:
                out.append(answer)
        return out

    def test_thresholds_match_spec(self):
        self.assertEqual((KP_PASS, LESSON_PASS, CHAPTER_PASS, SEMESTER_PASS),
                         (0.80, 0.75, 0.70, 0.75))

    def test_unit_exam_locked_until_all_lessons_passed(self):
        st = self.orch.exam_status("unit", "s1u1")
        self.assertFalse(st["ready"], "一节课都没过时不该可考")
        self.assertEqual(st["lessons"], 3)
        self.assertEqual(st["lessons_passed"], 0)
        self.assertEqual(self.orch.exam_questions("unit", "s1u1"), [])

        self.orch.db.record_lesson_score(self.orch.user_id, "s1u1l1", 1.0)
        self.assertFalse(self.orch.exam_status("unit", "s1u1")["ready"], "只过一课仍不可考")
        self.assertEqual(self.orch.exam_questions("unit", "s1u1"), [],
                         "未就绪时不给卷")

    def test_unit_exam_passes_at_chapter_threshold(self):
        self._pass_all_lessons("unit", "s1u1")
        st = self.orch.exam_status("unit", "s1u1")
        self.assertTrue(st["ready"])
        self.assertEqual(st["threshold"], CHAPTER_PASS)

        qs = self.orch.exam_questions("unit", "s1u1")
        self.assertTrue(qs, "就绪后应有整卷题目")
        result = self.orch.submit_exam("unit", "s1u1", self._perfect_answers(qs))
        self.assertTrue(result["ok"])
        self.assertEqual(result["score"], 1.0)
        self.assertTrue(result["passed"])
        self.assertTrue(self.orch.db.exam_passed(self.orch.user_id, "unit", "s1u1"))

    def test_chapter_line_is_lower_than_lesson_line(self):
        """章节考 70% 该过，课堂小测 75% 该不过 —— 两条线必须真正分开。

        不通过整卷得分来验证：种子卷只有 12 题，粒度 1/12≈8.3%，
        没有任何档位落在 (70%,75%) 之间（6/12=50%、7/12=58%、8/12=67%、9/12=75%）。
        这是内容粒度的限制，不是判分逻辑的问题，所以直接比对同一分数在两条线上的结论。
        """
        self.assertLess(CHAPTER_PASS, LESSON_PASS)
        boundary = 0.72                      # 落在 (70%, 75%) 之间
        self.assertGreater(boundary, CHAPTER_PASS)
        self.assertLess(boundary, LESSON_PASS)

        self._pass_all_lessons("unit", "s1u1")

        # 同一分数：章节考判定通过
        exam = self.orch.db.record_exam_score(self.orch.user_id, "unit", "s1u1", boundary)
        self.assertTrue(exam["passed"], "章节考线 70%，72% 该过")

        # 同一分数：课级闯关门禁判定不通过
        # 必须换一节没通过过的课：lesson_progress 的 passed 是粘滞的，
        # 对已通过的 s1u1l1 再记 72% 不会、也不该把它打回未通过。
        self.orch.db.record_lesson_score(self.orch.user_id, "s1u2l1", boundary)
        self.assertFalse(self.orch.db.lesson_passed(self.orch.user_id, "s1u2l1"),
                         "单元考线 75%，72% 不该过")

    def test_semester_exam_spans_all_units_and_uses_75(self):
        """学期考覆盖面 ≥ 单元考之和，且用 75% 线。

        注意：整学期 33 课目前只有 3 课有种子内容（s1u1），所以这里只验证
        「范围/线值/覆盖面一致性」，不假设整卷可答（内容补齐后才会）。
        """
        units = self.orch.db.semester_unit_ids("s1")
        self.assertGreater(len(units), 1)
        all_lessons = self.orch.db.scope_lesson_ids("semester", "s1")
        self.assertEqual(all_lessons,
                         [l for u in units for l in self.orch.db.scope_lesson_ids("unit", u)],
                         "学期课表必须是其单元课表的顺序拼接")

        self._pass_all_lessons("semester", "s1")
        st = self.orch.exam_status("semester", "s1")
        self.assertTrue(st["ready"])
        self.assertEqual(st["threshold"], SEMESTER_PASS)
        self.assertEqual(st["lessons"], len(all_lessons))

        # 覆盖面：整卷题目数 == 各单元卷题目数之和
        qs = self.orch.exam_questions("semester", "s1")
        per_unit = sum(len(self.orch.exam_questions("unit", u)) for u in units)
        self.assertEqual(len(qs), per_unit)
        self.assertGreater(len(qs), 0, "s1u1 有种子题目，学期卷至少该有这些")

    def test_semester_line_is_higher_than_chapter_line(self):
        self.assertGreater(SEMESTER_PASS, CHAPTER_PASS)

    def test_failed_attempt_does_not_mark_passed(self):
        self._pass_all_lessons("unit", "s1u1")
        qs = self.orch.exam_questions("unit", "s1u1")
        answers = ["__错__"] * len(qs)
        result = self.orch.submit_exam("unit", "s1u1", answers)
        self.assertFalse(result["passed"])
        self.assertEqual(self.orch.exam_status("unit", "s1u1")["attempts"], 1)
        self.assertFalse(self.orch.db.exam_passed(self.orch.user_id, "unit", "s1u1"))

    def test_passed_stays_passed_on_retry(self):
        self._pass_all_lessons("unit", "s1u1")
        qs = self.orch.exam_questions("unit", "s1u1")
        self.orch.submit_exam("unit", "s1u1", self._perfect_answers(qs))
        bad = self.orch.submit_exam("unit", "s1u1", ["__错__"] * len(qs))
        self.assertTrue(bad["passed"], "已通过的考试不该因重考变差而回退")
        self.assertEqual(bad["attempts"], 2)

    def test_reset_clears_exam_results(self):
        self._pass_all_lessons("unit", "s1u1")
        qs = self.orch.exam_questions("unit", "s1u1")
        self.orch.submit_exam("unit", "s1u1", self._perfect_answers(qs))
        self.assertTrue(self.orch.db.exam_passed(self.orch.user_id, "unit", "s1u1"))

        self.orch.reset()
        self.assertFalse(self.orch.db.exam_passed(self.orch.user_id, "unit", "s1u1"))

    def test_next_exam_is_the_earliest_ready_one(self):
        """界面上「下一场考试」必须按课程顺序取最早一场。

        曾经只看 next_lesson 所在学期：真实库里 178 课全过、next_lesson 在 s8，
        界面就永远只给 s8u1，s1~s7 几十场早就就绪的考试一个都点不到。
        这里把除 s8 最后一课以外的课全判过，模拟「下一课在很后面」的局面。
        """
        lessons = self.orch.db.all_lessons_in_order()
        skip = lessons[-1].id
        for lesson in lessons:
            if lesson.id != skip:
                self.orch.db.record_lesson_score(self.orch.user_id, lesson.id, 1.0)

        nxt = self.orch._next_lesson()
        self.assertIsNotNone(nxt)
        self.assertNotEqual(nxt.semester_id, "s1", "前提：下一课已经跑到很后面的学期")

        exam = self.orch.status()["exams"]["next"]
        self.assertEqual((exam["scope"], exam["scope_id"]), ("unit", "s1u1"),
                         "最早就绪的考试是 s1u1，不能因为 next_lesson 在 s8 就跳过它")

    def test_unknown_scope_is_rejected(self):
        with self.assertRaises(ValueError):
            self.orch.db.scope_lesson_ids("chapter", "x")


if __name__ == "__main__":
    unittest.main()
