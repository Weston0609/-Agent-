"""通知 —— 到点提醒（上课/召回/更新）。

离线零 token：默认打印到 stdout；接入 Database 时同时写入通知收件箱，
Web/CLI 可离线查看（不依赖任何网络或推送服务）。
"""
from __future__ import annotations


class Notifier:
    def __init__(self, db=None, enabled: bool = True) -> None:
        self.db = db
        self.enabled = enabled

    def notify(self, title: str, message: str) -> None:
        if not self.enabled:
            return
        print(f"[{title}] {message}")

    def send(self, user_id: str, message: str, kind: str = "info") -> None:
        """向用户推送：落库（收件箱）+ 打印。"""
        if not self.enabled:
            return
        if self.db is not None:
            self.db.add_notification(user_id, kind, message)
        self.notify(user_id, message)
