"""内容审计 —— 检查哪些课/考还缺内容，决定更新优先级。

离线零 token：只扫描缓存目录，不联网。
"""
from __future__ import annotations

from pathlib import Path


class Audit:
    def __init__(self, curriculum, content_dir: Path | str) -> None:
        self.curriculum = curriculum
        self.content_dir = Path(content_dir)

    def missing_lessons(self) -> list[str]:
        missing = []
        for lesson in self.curriculum.ordered_lessons():
            if not (self.content_dir / "lessons" / f"{lesson.id}.json").exists():
                missing.append(lesson.id)
        return missing

    def missing_exams(self) -> list[str]:
        missing = []
        for sem in self.curriculum.semesters:
            for unit in sem.units:
                if not (self.content_dir / "exams" / f"{unit.id}.json").exists():
                    missing.append(unit.id)
            if not (self.content_dir / "exams" / f"{sem.id}-final.json").exists():
                missing.append(f"{sem.id}-final")
        return missing

    def report(self) -> dict:
        return {
            "missing_lessons": self.missing_lessons(),
            "missing_exams": self.missing_exams(),
        }


def run_audit(db) -> dict:
    """DB 驱动审计（0 token）：统计哪些 KP 尚无内容。"""
    summary = db.covered_summary()
    total = summary.get("total_kps", 0)
    filled = summary.get("with_content", 0)
    return {
        "total_kps": total,
        "with_content": filled,
        "missing": total - filled,
        "semesters": summary.get("semesters", {}),
    }
