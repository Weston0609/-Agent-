"""40 分钟课堂执行器 —— 8 阶段节奏，超时强制推进（同步适配）。

原骨架用 async；本应用同步架构，故 run() 与阶段处理器均为同步方法，
时序逻辑（累计 deadline、硬时限、未完成项转明日 warmup）保持一致。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum


class Phase(str, Enum):
    WARMUP = "warmup"
    GOAL = "goal"
    TEACHING = "teaching"
    GUIDED = "guided_practice"
    QUIZ = "quiz"
    EVALUATE = "evaluate"
    SUMMARY = "summary"
    SCHEDULE = "schedule_review"
    DONE = "done"


@dataclass
class PhaseSpec:
    phase: Phase
    duration_sec: int
    hard_limit: bool = True


LESSON_40MIN: list[PhaseSpec] = [
    PhaseSpec(Phase.WARMUP, 4 * 60),
    PhaseSpec(Phase.GOAL, 2 * 60),
    PhaseSpec(Phase.TEACHING, 12 * 60),
    PhaseSpec(Phase.GUIDED, 4 * 60),
    PhaseSpec(Phase.QUIZ, 10 * 60),
    PhaseSpec(Phase.EVALUATE, 4 * 60),
    PhaseSpec(Phase.SUMMARY, 3 * 60),
    PhaseSpec(Phase.SCHEDULE, 1 * 60),
]


class LessonRunner:
    def __init__(self, orchestrator, db, clock, answers_provider=None):
        self.orch = orchestrator
        self.db = db
        self.clock = clock
        # 课堂内作答回调：questions -> answers。为 None 时测验阶段只报题量，
        # 由 UI/CLI 的 submit_quiz 单独提交（Web 面板即走这条路）。
        self.answers_provider = answers_provider

    def run(self, session) -> dict:
        started = self.clock.now()
        carry_over: list = []
        phases: list[dict] = []

        for spec in LESSON_40MIN:
            deadline = self._deadline_for(started, spec)
            result = self._run_phase(session, spec, deadline)
            if not result.completed and result.pending_item:
                carry_over.append(result.pending_item)
            phases.append({"phase": spec.phase.value, "completed": result.completed, "summary": result.summary})

        if carry_over:
            self.db.append_to_warmup(session.user_id, carry_over)

        self.orch.finalize_session(session)
        return {"session_id": session.id, "phases": phases}

    def _accumulated(self, spec: PhaseSpec) -> timedelta:
        total = 0
        for s in LESSON_40MIN:
            total += s.duration_sec
            if s.phase == spec.phase:
                return timedelta(seconds=total)
        return timedelta(0)

    def _deadline_for(self, started: datetime, spec: PhaseSpec) -> datetime:
        return started + self._accumulated(spec)

    def _run_phase(self, session, spec: PhaseSpec, deadline: datetime):
        handler = getattr(self, f"_phase_{spec.phase.value}")
        return handler(session, deadline)

    # ---------- 各阶段（委托 orchestrator 的阶段处理器）----------
    def _phase_warmup(self, session, deadline):
        return self.orch.run_warmup(session, deadline)

    def _phase_goal(self, session, deadline):
        return self.orch.preview_goals(session, deadline)

    def _phase_teaching(self, session, deadline):
        return self.orch.teach_phase(session, deadline)

    def _phase_guided_practice(self, session, deadline):
        return self.orch.guided_practice(session, deadline)

    def _phase_quiz(self, session, deadline):
        questions = self.orch.lesson_questions(session.lesson_id)
        answers = self.answers_provider(questions) if self.answers_provider else None
        return self.orch.run_quiz(session, deadline, answers)

    def _phase_evaluate(self, session, deadline):
        return self.orch.evaluate(session, deadline)

    def _phase_summary(self, session, deadline):
        return self.orch.summarize(session, deadline)

    def _phase_schedule_review(self, session, deadline):
        return self.orch.schedule_review(session, deadline)
