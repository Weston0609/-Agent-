"""讲师 —— 缓存教学（0 token）。

从 kp_content 表直接读预生成内容。内容缺失时给出明确提示（下次系统更新补齐），
不触网、不烧 token。
"""
from __future__ import annotations


class Tutor:
    def __init__(self, db) -> None:
        self.db = db

    def teach_cached(self, kp_id: str) -> dict:
        """完全离线：从 kp_content 表读预生成内容。0 token。"""
        content = self.db.get_kp_content(kp_id)
        if not content:
            return {
                "ok": False,
                "reason": "该知识点尚未生成内容，将在下次系统更新时补齐。",
                "fallback": "你可以点「立即更新」触发一次生成（会消耗少量 token）。",
            }
        return {
            "ok": True,
            "title": content.title,
            "explain": content.explain,
            "example_code": content.example_code,
            "pitfalls": content.pitfalls,
            "sources": content.sources,
        }
