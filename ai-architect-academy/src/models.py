"""数据模型与课程加载。

课程结构：学期(semester) -> 单元(unit) -> 课(lesson) -> 知识点(kp)
DAG 前置关系由顺序隐式表达，另加显式的 semester 解锁规则。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Lesson:
    id: str
    kps: tuple[str, ...]
    unit_id: str
    semester_id: str
    # 在所属 unit 内的顺序索引（从 0 开始），DAG 前置 = 上一个 lesson
    index_in_unit: int


@dataclass(frozen=True)
class Unit:
    id: str
    name: str
    lessons: tuple[Lesson, ...]
    semester_id: str
    index_in_semester: int


@dataclass(frozen=True)
class Semester:
    id: str
    name: str
    units: tuple[Unit, ...]
    index: int


@dataclass(frozen=True)
class Curriculum:
    semesters: tuple[Semester, ...]
    pass_threshold: float
    lesson_minutes: int

    # 快速索引
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
        """按学习顺序返回所有 lesson（DAG 拓扑序）。"""
        out: list[Lesson] = []
        for sem in self.semesters:
            for unit in sem.units:
                out.extend(unit.lessons)
        return out

    def prev_lesson(self, lesson: Lesson) -> Lesson | None:
        """返回同一 unit 内上一课（DAG 直接前置），无则 None。"""
        if lesson.index_in_unit == 0:
            return None
        unit = self.units_by_id[lesson.unit_id]
        return unit.lessons[lesson.index_in_unit - 1]

    def prev_unit(self, unit: Unit) -> Unit | None:
        if unit.index_in_semester == 0:
            return None
        sem = self.semesters_by_id[unit.semester_id]
        return sem.units[unit.index_in_semester - 1]

    def prev_semester(self, semester: Semester) -> Semester | None:
        if semester.index == 0:
            return None
        return self.semesters[semester.index - 1]


def load_curriculum(path: Path | str) -> Curriculum:
    """从 curriculum.json 加载并构建索引。"""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    meta = raw["meta"]
    semesters: list[Semester] = []
    lessons_by_id: dict[str, Lesson] = {}
    units_by_id: dict[str, Unit] = {}
    semesters_by_id: dict[str, Semester] = {}

    for si, sem_raw in enumerate(raw["semesters"]):
        units: list[Unit] = []
        for ui, unit_raw in enumerate(sem_raw["units"]):
            lessons: list[Lesson] = []
            for li, lesson_raw in enumerate(unit_raw["lessons"]):
                lesson = Lesson(
                    id=lesson_raw["id"],
                    kps=tuple(lesson_raw["kps"]),
                    unit_id=unit_raw["id"],
                    semester_id=sem_raw["id"],
                    index_in_unit=li,
                )
                lessons.append(lesson)
                lessons_by_id[lesson.id] = lesson
            unit = Unit(
                id=unit_raw["id"],
                name=unit_raw["name"],
                lessons=tuple(lessons),
                semester_id=sem_raw["id"],
                index_in_semester=ui,
            )
            units.append(unit)
            units_by_id[unit.id] = unit
        semester = Semester(
            id=sem_raw["id"],
            name=sem_raw["name"],
            units=tuple(units),
            index=si,
        )
        semesters.append(semester)
        semesters_by_id[semester.id] = semester

    return Curriculum(
        semesters=tuple(semesters),
        pass_threshold=float(meta["pass_threshold"]),
        lesson_minutes=int(meta["lesson_minutes"]),
        lessons_by_id=lessons_by_id,
        units_by_id=units_by_id,
        semesters_by_id=semesters_by_id,
    )
