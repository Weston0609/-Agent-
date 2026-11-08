"""数据模型 —— stdlib dataclass 表示（非 SQLAlchemy）。

ponytail: 本地单机 sqlite 场景，SQLAlchemy 是无收益的额外依赖，故用 dataclass +
sqlite3 直连。升级路径 = 迁移到真实 RDBMS（Postgres）时再引入 SQLAlchemy。
schema 权威源见同目录 schema.sql。
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class User:
    id: str
    name: str = ""
    level: str = "beginner"
    timezone: str = "Asia/Shanghai"


@dataclass
class ScheduleSlot:
    user_id: str = ""
    weekday: int = 0
    start_minute: int = 0
    duration_minutes: int = 40
    enabled: bool = True
    id: int | None = None


@dataclass
class Lesson:
    id: str
    unit_id: str = ""
    semester_id: str = ""
    name: str = ""
    order: int = 0
    kps: list[str] = field(default_factory=list)
    prereq_kps: list[str] = field(default_factory=list)   # 由 kps.prereq 聚合


@dataclass
class KP:
    id: str
    lesson_id: str = ""
    title: str = ""
    difficulty: int = 1
    prereq: list[str] = field(default_factory=list)
    weight: int = 3
    order: int = 0


@dataclass
class KPContent:
    kp_id: str
    explain: str = ""
    example_code: str = ""
    pitfalls: str = ""
    sources: list = field(default_factory=list)
    version: int = 1
    verified: bool = False

    @property
    def title(self) -> str:
        return self.kp_id


@dataclass
class Mastery:
    user_id: str
    kp_id: str
    p_mastery: float = 0.2
    attempts: int = 0
    correct: int = 0
    last_seen: str | None = None


@dataclass
class ReviewCard:
    user_id: str
    kp_id: str
    due_at: str | None = None
    card: dict = field(default_factory=dict)   # fsrs Card.to_dict()


@dataclass
class DayPlan:
    user_id: str
    plan_date: str
    lessons: list = field(default_factory=list)
