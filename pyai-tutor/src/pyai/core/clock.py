"""时钟抽象 —— 把"现在几点"与业务逻辑解耦。

生产用 RealClock（datetime.now）；测试注入 FrozenClock 冻结时间，
保证排课 / 40 分钟课堂计时 / 会话时长都可确定性验证。
"""
from __future__ import annotations

from datetime import datetime, timedelta


class Clock:
    def now(self) -> datetime:
        raise NotImplementedError

    def monotonic(self) -> float:
        """单调时钟（秒），用于测量课堂已进行时长，不受系统改时间影响。"""
        raise NotImplementedError


class RealClock(Clock):
    def now(self) -> datetime:
        return datetime.now()

    def monotonic(self) -> float:
        return datetime.now().timestamp()


class FrozenClock(Clock):
    """测试用：固定在某一时刻，可手动推进。"""

    def __init__(self, start: datetime) -> None:
        self._now = start
        self._tick = start.timestamp()

    def now(self) -> datetime:
        return self._now

    def monotonic(self) -> float:
        return self._tick

    def advance(self, delta: timedelta) -> None:
        self._now += delta
        self._tick += delta.total_seconds()
