"""排课引擎 —— 40 分钟一节课，基于实时日期时间自动排课。

核心思路（学校模式）：
- 课程按 DAG 顺序线性推进，一次只解锁/安排"下一节课"。
- 每节课固定 40 分钟（lesson_minutes）。同一天可安排多节，节间不强制休息。
- 排课结果由"当前实时时间 + 已学进度"共同决定，不写死日期：
  下次排课时间 = 基于今天已安排课节数顺延，每节占 40 分钟。
- 系统通过 datetime.now() 实时感知"现在"，从而判断：
  · 今天已经上过几节（store.get_sessions_today）
  · 当前是否在上课时间窗口内（用于提醒/自动推进）
  · 下一节课建议何时开始

全部用 stdlib datetime，零依赖。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from .models import Curriculum
from .unlock import compute_states


@dataclass
class ScheduleEntry:
    lesson_id: str
    start_at: datetime
    end_at: datetime
    minutes: int


@dataclass
class SchedulePlan:
    generated_at: datetime
    entries: list[ScheduleEntry] = field(default_factory=list)
    note: str = ""

    @property
    def total_minutes(self) -> int:
        return sum(e.minutes for e in self.entries)


def _floor_to_lesson_slots(dt: datetime, minutes: int) -> datetime:
    """把时间对齐到 lesson_minutes 的整数倍槽位（每天 00:00 起算）。"""
    day_start = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    elapsed = (dt - day_start).total_seconds()
    slots = int(elapsed // (minutes * 60))
    return day_start + timedelta(minutes=minutes * slots)


def plan_day(
    curriculum: Curriculum,
    store,
    *,
    now: datetime | None = None,
    lessons_per_day: int = 3,
    start_hour: int = 8,
    end_hour: int = 22,
) -> SchedulePlan:
    """为"今天"生成排课计划。

    - 从当前第一个未通过的课开始，最多安排 lessons_per_day 节。
    - 每节 40 分钟；第一节从 start_hour 开始，若当前已过开始时间则顺延到下一槽。
    - 已学过（passed）的课跳过，直接排下一个。
    - 若今天已有上课记录，已安排节数相应扣减，避免重复排课。
    """
    now = now or datetime.now()
    states = compute_states(curriculum, store)
    ordered = curriculum.ordered_lessons()

    # 跳过已通过，只排未通过的
    pending = [l for l in ordered if states[l.id].status != "passed"]
    if not pending:
        return SchedulePlan(generated_at=now, note="全部课程已完成，无需排课")

    done_today = len(store.get_sessions_today())
    remaining_slots = max(0, lessons_per_day - done_today)
    if remaining_slots == 0:
        return SchedulePlan(generated_at=now, note=f"今天已排满 {lessons_per_day} 节，明天继续")

    minutes = curriculum.lesson_minutes  # 40
    first_start = now.replace(hour=start_hour, minute=0, second=0, microsecond=0)
    if first_start < now:
        # 已过 start_hour，从下一个 40 分钟槽开始
        first_start = _floor_to_lesson_slots(now, minutes) + timedelta(minutes=minutes)

    entries: list[ScheduleEntry] = []
    cursor = first_start
    for lesson in pending[:remaining_slots]:
        if cursor.hour >= end_hour:
            cursor = (cursor + timedelta(days=1)).replace(
                hour=start_hour, minute=0, second=0, microsecond=0
            )
        end = cursor + timedelta(minutes=minutes)
        entries.append(
            ScheduleEntry(lesson_id=lesson.id, start_at=cursor, end_at=end, minutes=minutes)
        )
        cursor = end

    note = f"今日 {now.date().isoformat()}，安排 {len(entries)} 节（每节 {minutes} 分钟）"
    return SchedulePlan(generated_at=now, entries=entries, note=note)


def current_lesson(
    curriculum: Curriculum, store, *, now: datetime | None = None
) -> ScheduleEntry | None:
    """返回"此刻"应在上的一节课（用于实时进度/提醒）。

    逻辑：今天最近一次 start_session 且未 end_session 的课，视为当前进行中的课。
    """
    for s in store.get_sessions_today():
        if s.get("ended_at") is None:
            started = datetime.fromisoformat(s["started_at"])
            return ScheduleEntry(
                lesson_id=s["lesson_id"],
                start_at=started,
                end_at=started + timedelta(minutes=curriculum.lesson_minutes),
                minutes=curriculum.lesson_minutes,
            )
    return None


def next_lesson_start(
    curriculum: Curriculum, store, *, now: datetime | None = None
) -> datetime:
    """下一次排课建议开始时间 = 今天最后一段 40 分钟槽之后。"""
    now = now or datetime.now()
    plan = plan_day(curriculum, store, now=now)
    if plan.entries:
        return plan.entries[0].start_at
    return _floor_to_lesson_slots(now, curriculum.lesson_minutes) + timedelta(
        minutes=curriculum.lesson_minutes
    )
