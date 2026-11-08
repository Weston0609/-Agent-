"""时间守护进程 —— APScheduler 常驻调度（唯一知道"现在几点"的组件）。

适配说明（原骨架用 AsyncIOScheduler）：整个应用是同步架构（stdlib Web/CLI），
改用 BackgroundScheduler（线程）+ 同步 job 函数，语义一致。

定时任务：
  · 每 15 秒 tick：检查是否有用户到了学习时间（到点 → 启动一节 40 分钟课）
  · 每天 07:00：生成今日课表
  · 每天 22:00：推送明日预告
  · 每周日 03:00：触发系统更新（唯一用 API 的时刻）
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

log = logging.getLogger(__name__)


class TimeDaemon:
    def __init__(self, db, notifier, orchestrator, tz: str = "Asia/Shanghai"):
        self.db = db
        self.notifier = notifier
        self.orch = orchestrator
        self.tz = ZoneInfo(tz)
        self.sched = BackgroundScheduler(timezone=self.tz)

    # ---------- 时间接口 ----------
    def now(self) -> datetime:
        return datetime.now(self.tz)

    def today(self) -> date:
        return self.now().date()

    # ---------- 生命周期 ----------
    def start(self) -> None:
        self.sched.add_job(self._tick, "interval", seconds=15, id="tick")
        self.sched.add_job(self._plan_day, CronTrigger(hour=7, minute=0), id="plan_day")
        self.sched.add_job(self._recall_missed, CronTrigger(hour=21, minute=0), id="recall")
        self.sched.add_job(self._preview_tomorrow, CronTrigger(hour=22, minute=0), id="preview")
        self.sched.add_job(
            self._weekly_update, CronTrigger(day_of_week="sun", hour=3, minute=0),
            id="weekly_update",
        )
        self.sched.start()
        log.info("TimeDaemon started, tz=%s, now=%s", self.tz, self.now())

    def shutdown(self) -> None:
        self.sched.shutdown(wait=False)

    # ---------- 核心 tick ----------
    def _tick(self) -> None:
        now = self.now()
        for user in self.db.active_users():
            slots = self.db.slots_for(user.id, now.weekday())
            now_minutes = now.hour * 60 + now.minute
            in_slot = any(
                s.start_minute <= now_minutes < s.start_minute + s.duration_minutes
                for s in slots
            )
            if not in_slot:
                continue
            if self.db.get_active_session(user.id) is not None:
                continue
            self._start_lesson(user, now)

    def _start_lesson(self, user, now: datetime) -> None:
        plan = self.db.get_day_plan(user.id, self.today().isoformat())
        if not plan:
            return
        next_lesson = self._pick_next_pending(plan)
        if not next_lesson:
            return
        session = self.orch.start_session(
            user_id=user.id, lesson_id=next_lesson["lesson_id"], plan_date=self.today().isoformat(),
        )
        self.notifier.send(
            user.id,
            f"🔔 {now:%H:%M} 上课啦！\n"
            f"本节课：{next_lesson['title']}\n"
            f"时长：40 分钟\n点击开始 →",
            kind="class",
        )

    @staticmethod
    def _pick_next_pending(plan) -> dict | None:
        for lesson in plan.lessons:
            if lesson.get("status") == "pending" and lesson.get("type") == "new":
                return lesson
        return None

    # ---------- 排课 ----------
    def _plan_day(self) -> None:
        today = self.today()
        for user in self.db.active_users():
            slots = self.db.slots_for_weekday(user.id, today.weekday())
            total = sum(s.duration_minutes for s in slots)
            lessons = self.orch.plan_lessons(user.id, total, today)
            self.db.save_day_plan(user.id, today.isoformat(), lessons)
            self.notifier.send(user.id, f"📅 今日课表：{len(lessons)} 节，共 {total} 分钟", kind="plan")

    def _recall_missed(self) -> None:
        """缺席召回：今日课表里仍未开始的新课，晚间提醒（进度自然顺延到明日排课）。"""
        today = self.today().isoformat()
        for user in self.db.active_users():
            plan = self.db.get_day_plan(user.id, today)
            if not plan:
                continue
            pending = [
                l for l in plan.lessons
                if l.get("type") == "new" and l.get("status") == "pending"
            ]
            if not pending:
                continue
            names = "、".join(l.get("lesson_id", "") for l in pending)
            self.notifier.send(
                user.id,
                f"⏰ 今日还有 {len(pending)} 节未完成：{names}。明天排课会自动顺延。",
                kind="recall",
            )

    def _preview_tomorrow(self) -> None:
        tomorrow = self.today() + timedelta(days=1)
        for user in self.db.active_users():
            due = self.db.due_reviews(user.id, tomorrow)
            self.notifier.send(user.id, f"🌙 明日预告：{len(due)} 项到期复习", kind="preview")

    def _weekly_update(self) -> None:
        from ..updater.pipeline import run_weekly_update
        log.info("Weekly update triggered at %s", self.now())
        result = run_weekly_update(db=self.db, manual=False)
        status = result.get("status", "ok") if isinstance(result, dict) else "ok"
        for user in self.db.active_users():
            self.notifier.send(user.id, f"🔄 系统更新完成（{status}）", kind="update")
