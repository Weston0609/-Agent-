"""课程 DAG 加载 + 解锁判定 —— 读取 full_curriculum.yaml。

数据结构与 v1 一致：Semester → Unit → Lesson → kps(list[str])。
解锁规则（strict DAG）：
- 课程内：严格串行，前一课 passed 才能解锁下一课。
- 单元间：上一单元所有课 passed 且单元考 passed。
- 学期间：上一学期所有单元考 + 期末考 passed。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class Lesson:
    id: str
    kps: list[str]
    unit_id: str = ""
    semester_id: str = ""
    index_in_unit: int = 0

    @property
    def title(self) -> str:
        return self.id


@dataclass
class Unit:
    id: str
    name: str
    lessons: list[Lesson] = field(default_factory=list)
    semester_id: str = ""


@dataclass
class Semester:
    id: str
    name: str
    units: list[Unit] = field(default_factory=list)


@dataclass
class Curriculum:
    semesters: list[Semester]
    pass_threshold: float = 0.75
    lesson_minutes: int = 40
    semester_unlock_rule: str = ""

    # 索引
    lessons_by_id: dict[str, Lesson] = field(default_factory=dict)
    units_by_id: dict[str, Unit] = field(default_factory=dict)
    semesters_by_id: dict[str, Semester] = field(default_factory=dict)

    @property
    def total_lessons(self) -> int:
        return len(self.lessons_by_id)

    @property
    def total_kps(self) -> int:
        return sum(len(l.kps) for l in self.lessons_by_id.values())

    def ordered_lessons(self) -> list[Lesson]:
        out: list[Lesson] = []
        for sem in self.semesters:
            for unit in sem.units:
                out.extend(unit.lessons)
        return out

    def prev_lesson(self, lesson: Lesson) -> Lesson | None:
        ordered = self.ordered_lessons()
        for i, l in enumerate(ordered):
            if l.id == lesson.id:
                return ordered[i - 1] if i > 0 else None
        return None

    def prev_unit(self, unit: Unit) -> Unit | None:
        for sem in self.semesters:
            for i, u in enumerate(sem.units):
                if u.id == unit.id:
                    return sem.units[i - 1] if i > 0 else None
        return None

    def prev_semester(self, semester: Semester) -> Semester | None:
        for i, s in enumerate(self.semesters):
            if s.id == semester.id:
                return self.semesters[i - 1] if i > 0 else None
        return None


# ---------- 解锁判定（strict DAG）----------

def compute_states(curriculum: Curriculum, session) -> dict[str, str]:
    """返回每课的状态：locked | unlocked | passed。

    - 第一学期第一单元第一课始终 unlocked。
    - 课内串行：前一课 passed 才解锁下一课。
    - 单元间：上一单元全课 passed 且单元考 passed。
    - 学期间：上一学期全课 + 全部单元考 + 期末考 passed。
    """
    rows = session.get_all_lessons()
    exams = session.get_all_exams()

    def is_passed(lid: str) -> bool:
        return rows.get(lid, {}).get("status") == "passed"

    def exam_passed(eid: str) -> bool:
        return bool((exams.get(eid) or {}).get("passed"))

    def unit_done(unit: Unit) -> bool:
        return all(is_passed(l.id) for l in unit.lessons)

    def semester_done(sem: Semester) -> bool:
        return all(unit_done(u) and exam_passed(u.id) for u in sem.units)

    states: dict[str, str] = {}
    prev_sem_done = True
    for si, sem in enumerate(curriculum.semesters):
        if si > 0:
            prev_sem_done = semester_done(curriculum.semesters[si - 1]) and exam_passed(
                f"{curriculum.semesters[si - 1].id}-final"
            )
        prev_unit_done = True
        for ui, unit in enumerate(sem.units):
            if ui > 0:
                prev_unit_done = unit_done(sem.units[ui - 1]) and exam_passed(sem.units[ui - 1].id)
            gate_ok = prev_sem_done and prev_unit_done
            for li, lesson in enumerate(unit.lessons):
                if is_passed(lesson.id):
                    states[lesson.id] = "passed"
                elif gate_ok and (li == 0 or is_passed(unit.lessons[li - 1].id)):
                    states[lesson.id] = "unlocked"
                else:
                    states[lesson.id] = "locked"
    return states


def next_unlocked_lesson(curriculum: Curriculum, states: dict[str, str]) -> Lesson | None:
    for lesson in curriculum.ordered_lessons():
        if states[lesson.id] == "unlocked":
            return lesson
    return None


def unit_all_passed(unit: Unit, states: dict[str, str]) -> bool:
    return all(states[l.id] == "passed" for l in unit.lessons)


def semester_progress(curriculum: Curriculum, sem: Semester, states: dict[str, str]) -> tuple[int, int]:
    total = sum(len(u.lessons) for u in sem.units)
    passed = sum(1 for u in sem.units for l in u.lessons if states[l.id] == "passed")
    return passed, total


def available_exams(curriculum: Curriculum, session) -> list[dict]:
    """当前可参加的考试：单元考（该单元全课 passed 且未考）+ 期末考（全学期课+单元考 passed 且未考）。"""
    rows = session.get_all_lessons()
    exams = session.get_all_exams()
    out: list[dict] = []
    for sem in curriculum.semesters:
        sem_lessons_done = all(rows.get(l.id, {}).get("status") == "passed" for u in sem.units for l in u.lessons)
        sem_units_done = all(bool((exams.get(u.id) or {}).get("passed")) for u in sem.units)
        final_id = f"{sem.id}-final"
        if sem_lessons_done and sem_units_done and not bool((exams.get(final_id) or {}).get("passed")):
            out.append({"id": final_id, "kind": "final", "title": f"{sem.name} · 期末考"})
        for unit in sem.units:
            unit_done = all(rows.get(l.id, {}).get("status") == "passed" for l in unit.lessons)
            if unit_done and not bool((exams.get(unit.id) or {}).get("passed")):
                out.append({"id": unit.id, "kind": "unit", "title": f"{unit.name} · 单元考"})
    return out


def load_curriculum(path: str | Path) -> Curriculum:
    path = Path(path)
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    meta = raw.get("meta", {})
    cur = Curriculum(
        semesters=[],
        pass_threshold=float(meta.get("pass_threshold", 0.75)),
        lesson_minutes=int(meta.get("lesson_minutes", 40)),
        semester_unlock_rule=str(meta.get("semester_unlock_rule", "")),
    )
    for s in raw.get("semesters", []):
        sem = Semester(id=s["id"], name=s["name"])
        for u in s.get("units", []):
            unit = Unit(id=u["id"], name=u["name"], semester_id=sem.id)
            for i, l in enumerate(u.get("lessons", [])):
                lesson = Lesson(
                    id=l["id"], kps=list(l.get("kps", [])),
                    unit_id=unit.id, semester_id=sem.id, index_in_unit=i,
                )
                unit.lessons.append(lesson)
                cur.lessons_by_id[lesson.id] = lesson
            sem.units.append(unit)
            cur.units_by_id[unit.id] = unit
        cur.semesters.append(sem)
        cur.semesters_by_id[sem.id] = sem
    return cur
