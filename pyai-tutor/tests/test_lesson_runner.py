import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace

from src.pyai.core.clock import FrozenClock
from src.pyai.core.lesson_runner import LESSON_40MIN, LessonRunner, Phase


class _Result:
    def __init__(self, completed: bool = True, pending_item: str | None = None, summary: str = ""):
        self.completed = completed
        self.pending_item = pending_item
        self.summary = summary


class _FakeOrch:
    def __init__(self):
        self.calls: list[str] = []
        self.finalized = 0
        self.quiz_answers = "unset"

    def run_warmup(self, session, deadline): self.calls.append("warmup"); return _Result(True)
    def preview_goals(self, session, deadline): self.calls.append("goal"); return _Result(True)
    def lesson_questions(self, lesson_id): return [{"id": "q1"}, {"id": "q2"}]
    def teach_phase(self, session, deadline):
        self.calls.append("teaching")
        return _Result(False, pending_item="py.env.install", summary="缺内容")
    def guided_practice(self, session, deadline): self.calls.append("guided"); return _Result(True)
    def run_quiz(self, session, deadline, answers=None):
        self.calls.append("quiz"); self.quiz_answers = answers; return _Result(True)
    def evaluate(self, session, deadline): self.calls.append("evaluate"); return _Result(True)
    def summarize(self, session, deadline): self.calls.append("summary"); return _Result(True)
    def schedule_review(self, session, deadline): self.calls.append("schedule"); return _Result(True)
    def finalize_session(self, session): self.finalized += 1


class _FakeDB:
    def __init__(self):
        self.warmup: list = []

    def append_to_warmup(self, user_id, items):
        self.warmup.extend(items)


class TestLessonRunner(unittest.TestCase):
    def _make(self):
        clock = FrozenClock(datetime(2026, 1, 1, 8, 0))
        orch = _FakeOrch()
        db = _FakeDB()
        session = SimpleNamespace(id="s1", user_id="u1", lesson_id="l1")
        return LessonRunner(orch, db, clock), orch, db, session

    def test_runs_all_eight_phases_in_order(self):
        runner, orch, db, session = self._make()
        result = runner.run(session)
        self.assertEqual(result["session_id"], "s1")
        self.assertEqual(len(result["phases"]), 8)
        self.assertEqual([p["phase"] for p in result["phases"]],
                         [spec.phase.value for spec in LESSON_40MIN])
        self.assertEqual(orch.finalized, 1)

    def test_carry_over_incomplete_phase_to_warmup(self):
        runner, orch, db, session = self._make()
        runner.run(session)
        self.assertEqual(db.warmup, ["py.env.install"])

    def test_deadline_accumulates_to_40_minutes(self):
        started = datetime(2026, 1, 1, 8, 0)
        runner = LessonRunner(None, None, FrozenClock(started))
        self.assertEqual(runner._deadline_for(started, LESSON_40MIN[0]),
                         started + timedelta(minutes=4))
        self.assertEqual(runner._deadline_for(started, LESSON_40MIN[-1]),
                         started + timedelta(minutes=40))
        self.assertEqual(LESSON_40MIN[0].phase, Phase.WARMUP)
        self.assertEqual(LESSON_40MIN[-1].phase, Phase.SCHEDULE)

    def test_quiz_phase_forwards_answers_provider(self):
        # 课堂内作答：answers_provider 的返回值必须透传给测验阶段（否则 evaluate 无从判分）
        clock = FrozenClock(datetime(2026, 1, 1, 8, 0))
        orch, db = _FakeOrch(), _FakeDB()
        session = SimpleNamespace(id="s1", user_id="u1", lesson_id="l1")
        runner = LessonRunner(orch, db, clock, answers_provider=lambda qs: [7, 8])
        runner.run(session)
        self.assertEqual(orch.quiz_answers, [7, 8])

    def test_quiz_phase_passes_none_without_provider(self):
        runner, orch, _, session = self._make()
        runner.run(session)
        self.assertIsNone(orch.quiz_answers)


if __name__ == "__main__":
    unittest.main()
