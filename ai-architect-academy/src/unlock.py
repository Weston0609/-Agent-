"""解锁逻辑 —— DAG 严格前置 + 学期解锁规则。

学期 N 解锁条件（来自课程规格）：
  · 学期 N-1 的所有单元考试 >= 75%
  · 学期 N-1 期末考 >= 75%
  · 学期 N-1 无挂起补强项（即有未通过课程则视为未完成）

单元内课程严格串行：上一课 passed 才能解锁下一课。
单元之间串行：上一单元的所有课 passed + 单元考 passed 才解锁下一单元。
"""
from __future__ import annotations

from dataclasses import dataclass

from .models import Curriculum, Lesson, Semester, Unit


@dataclass(frozen=True)
class LessonState:
    lesson: Lesson
    status: str  # locked | unlocked | passed
    quiz_score: float | None


def compute_states(curriculum: Curriculum, store) -> dict[str, LessonState]:
    """返回所有 lesson 的当前状态（幂等、纯读，不写库）。"""
    lesson_rows = store.get_all_lessons()
    exam_rows = store.get_all_exams()
    states: dict[str, LessonState] = {}

    for sem in curriculum.semesters:
        sem_unlocked = _semester_unlocked(curriculum, sem, exam_rows, lesson_rows)
        for unit in sem.units:
            unit_unlocked = sem_unlocked and _unit_unlocked(curriculum, unit, exam_rows, lesson_rows)
            for lesson in unit.lessons:
                row = lesson_rows.get(lesson.id)
                if row and row["status"] == "passed":
                    states[lesson.id] = LessonState(lesson, "passed", row["quiz_score"])
                elif unit_unlocked and _lesson_prereq_met(curriculum, lesson, lesson_rows):
                    states[lesson.id] = LessonState(lesson, "unlocked", None)
                else:
                    states[lesson.id] = LessonState(lesson, "locked", None)
    return states


def _lesson_prereq_met(curriculum: Curriculum, lesson: Lesson, lesson_rows: dict) -> bool:
    prev = curriculum.prev_lesson(lesson)
    if prev is None:
        return True
    row = lesson_rows.get(prev.id)
    return bool(row and row["status"] == "passed")


def _unit_unlocked(curriculum: Curriculum, unit: Unit, exam_rows: dict, lesson_rows: dict) -> bool:
    prev_unit = curriculum.prev_unit(unit)
    if prev_unit is None:
        return True
    # 上一单元所有课 passed
    if not all(lesson_rows.get(l.id, {}).get("status") == "passed" for l in prev_unit.lessons):
        return False
    # 上一单元考试 passed
    exam = exam_rows.get(prev_unit.id)
    return bool(exam and exam["passed"])


def _semester_unlocked(
    curriculum: Curriculum, semester: Semester, exam_rows: dict, lesson_rows: dict
) -> bool:
    if semester.index == 0:
        return True
    prev = curriculum.prev_semester(semester)
    return semester_passed(curriculum, prev, exam_rows, lesson_rows)


def semester_passed(
    curriculum: Curriculum, semester: Semester, exam_rows: dict, lesson_rows: dict
) -> bool:
    """学期是否已通过：所有单元考 >= 阈值 且 期末考 >= 阈值 且 无挂起补强项。"""
    threshold = curriculum.pass_threshold
    # 期末考
    final = exam_rows.get(f"{semester.id}-final")
    if not final or not final["passed"] or (final["score"] or 0) < threshold:
        return False
    # 所有单元考
    for unit in semester.units:
        exam = exam_rows.get(unit.id)
        if not exam or not exam["passed"] or (exam["score"] or 0) < threshold:
            return False
    # 无挂起补强项：所有课必须 passed
    for unit in semester.units:
        for lesson in unit.lessons:
            if lesson_rows.get(lesson.id, {}).get("status") != "passed":
                return False
    return True


def next_unlocked_lesson(curriculum: Curriculum, states: dict[str, LessonState]) -> Lesson | None:
    """按 DAG 顺序返回第一个 unlocked（未通过）的课，用于排课/继续学习。"""
    for lesson in curriculum.ordered_lessons():
        if states[lesson.id].status == "unlocked":
            return lesson
    return None


def unit_all_passed(curriculum: Curriculum, unit: Unit, states: dict[str, LessonState]) -> bool:
    return all(states[l.id].status == "passed" for l in unit.lessons)


def available_exams(curriculum: Curriculum, store) -> list[dict]:
    """返回当前可参加的考试，按学习顺序排列。

    规则：
    - 单元考：该单元所有课已 passed，且该单元考尚未 passed。
    - 期末考：该学期所有课 + 所有单元考已 passed，且期末考尚未 passed。

    返回 [{"id": str, "kind": "unit"|"final", "title": str}]。
    """
    lesson_rows = store.get_all_lessons()
    exam_rows = store.get_all_exams()
    out: list[dict] = []

    for sem in curriculum.semesters:
        sem_all_lessons_passed = all(
            lesson_rows.get(l.id, {}).get("status") == "passed"
            for u in sem.units
            for l in u.lessons
        )
        sem_all_unit_exams_passed = all(
            bool((exam_rows.get(u.id) or {}).get("passed")) for u in sem.units
        )
        final_id = f"{sem.id}-final"
        if (
            sem_all_lessons_passed
            and sem_all_unit_exams_passed
            and not bool((exam_rows.get(final_id) or {}).get("passed"))
        ):
            out.append({"id": final_id, "kind": "final", "title": f"{sem.name} · 期末考"})

        for unit in sem.units:
            unit_lessons_passed = all(
                lesson_rows.get(l.id, {}).get("status") == "passed"
                for l in unit.lessons
            )
            if unit_lessons_passed and not bool((exam_rows.get(unit.id) or {}).get("passed")):
                out.append({"id": unit.id, "kind": "unit", "title": f"{unit.name} · 单元考"})

    return out


def semester_progress(
    curriculum: Curriculum, semester: Semester, states: dict[str, LessonState]
) -> tuple[int, int]:
    """返回 (已通过课数, 总课数)。"""
    total = sum(len(u.lessons) for u in semester.units)
    passed = sum(
        1 for u in semester.units for l in u.lessons if states[l.id].status == "passed"
    )
    return passed, total
