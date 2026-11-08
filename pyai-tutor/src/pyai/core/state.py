"""运行时状态：会话级 Stage + 一次课堂的 SessionState。

8 阶段课堂节奏（Phase）定义在 lesson_runner.py，这里只放会话级状态。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class Stage(str, Enum):
    """一次学习会话的粗粒度阶段（写入 sessions.stage）。"""
    IDLE = "idle"           # 未开始
    RUNNING = "running"     # 进行中
    DONE = "done"           # 已结束


@dataclass
class SessionState:
    """一次 40 分钟课堂的运行时状态。"""
    user_id: str = "default"
    lesson_id: str = ""
    plan_date: str = ""
    stage: Stage = Stage.IDLE
    phase: str = "warmup"          # 当前 Phase（字符串，由 lesson_runner 驱动）
    started_at: datetime | None = None
    quiz_answers: list = field(default_factory=list)
    score: float | None = None
    mastered: bool | None = None

    def elapsed_minutes(self, now: datetime) -> float:
        if self.started_at is None:
            return 0.0
        return max(0.0, (now - self.started_at).total_seconds() / 60.0)


@dataclass
class ActiveSession:
    """已入库的一次学习会话（sessions 表行）。"""
    id: str
    user_id: str
    lesson_id: str
    plan_date: str = ""
    stage: Stage = Stage.RUNNING


@dataclass
class PhaseResult:
    """一个课堂阶段的执行结果。"""
    completed: bool = True
    pending_item: str | None = None      # 未完成项，扔进明日 warmup
    summary: str = ""
