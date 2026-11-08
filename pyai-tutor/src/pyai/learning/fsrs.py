"""FSRS 复习调度 —— 基于 fsrs 包。

schedule_next(card_state, correct, now) -> (card_dict, due)
"""
from __future__ import annotations

from datetime import datetime, timezone

from fsrs import Card, Rating, Scheduler

_scheduler = Scheduler()


def schedule_next(card_state: dict | None, correct: bool, now: datetime) -> tuple[dict, datetime]:
    if card_state is None:
        card = Card()
    else:
        card = Card.from_dict(card_state)

    # fsrs 要求 tz-aware UTC；应用内时钟是 naive（本地），统一按 UTC 墙钟处理，
    # 相对偏移一致，单机离线场景正确。返回前去掉 tzinfo 保持 naive 约定。
    aware = now.replace(tzinfo=timezone.utc) if now.tzinfo is None else now.astimezone(timezone.utc)
    rating = Rating.Good if correct else Rating.Again
    card, _log = _scheduler.review_card(card, rating, review_datetime=aware)
    return card.to_dict(), card.due.replace(tzinfo=None)
