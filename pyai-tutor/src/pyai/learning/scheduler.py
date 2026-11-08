"""排课算法 —— 基于周课表槽位的总时长，排当天学习内容。

优先级：昨日 warmup → 到期复习(FSRS) → 挂起补强 → 新内容(DAG 顺序)。
"""
from __future__ import annotations

from datetime import date

from ..db.session import Database


def plan_lessons(db: Database, user_id: str, available_minutes: int, today: date) -> list[dict]:
    lessons: list[dict] = []
    minutes = available_minutes

    # 1) 昨日遗留 warmup
    warmup = db.pop_warmup(user_id)
    if warmup:
        lessons.append({
            "type": "warmup", "status": "pending",
            "items": warmup, "minutes": min(10, minutes),
            "title": f"补强（{len(warmup)} 项）",
        })
        minutes -= 10

    # 2) 到期复习（FSRS）
    due = db.due_reviews(user_id, today)
    if due:
        lessons.append({
            "type": "review", "status": "pending",
            "items": due, "minutes": min(10, minutes),
            "title": f"到期复习（{len(due)} 项）",
        })
        minutes -= 10

    # 3) 挂起的补强
    pending = db.pending_remedial(user_id)
    if pending:
        lessons.append({
            "type": "remedial", "status": "pending",
            "kp_id": pending.id, "minutes": 40,
            "title": f"补强：{pending.title}",
        })
        return lessons       # 补强优先，不再排新内容

    # 4) 新内容：按 DAG 顺序
    planned: set[str] = set()
    while minutes >= 40:
        nxt = _pick_next_lesson(db, user_id, planned)
        if not nxt:
            break
        lessons.append({
            "type": "new", "status": "pending",
            "lesson_id": nxt.id, "minutes": 40,
            "title": nxt.name or nxt.id,
        })
        planned.add(nxt.id)
        minutes -= 40

    return lessons


def _pick_next_lesson(db: Database, user_id: str, skip: set[str] | None = None):
    """按课程顺序找「第一个还没通过的课」；全开放，不看前置是否通关。

    全开放 = 任何一关都能直接学。这里只决定「自动排课 / 开始当前关」默认推到哪一课：
    按 order 取第一个未通关的，相当于替学习者顺着往下走；想跳着学就直接选关，
    前端与 boss_start 都接受任意 lesson_id。
    批量取「已通过的课」，避免逐课查询（status() 每秒都会调到这里）。
    """
    skip = skip or set()
    passed = db.passed_lesson_ids(user_id)
    for lesson in db.all_lessons_in_order():
        if lesson.id in skip or lesson.id in passed:
            continue
        return lesson
    return None
