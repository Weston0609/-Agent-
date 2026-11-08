"""命令行入口 —— 把核心引擎串成可用的学习软件。

命令：
  status          查看学习进度、当前解锁状态、今日排课
  schedule        查看今日 40 分钟排课计划
  learn           开始下一节解锁的课（正文 + 随堂测验）
  exam <exam_id>  参加考试（单元考 s1u1 / 期末考 s1-final）
  update          调用 DeepSeek 生成/更新课程内容（消耗 token）
  reset           清空全部学习进度（危险，需二次确认）

用法：python -m src.cli <command>
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

# Windows 控制台默认 GBK，强制 UTF-8 输出避免中文乱码
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

from .content import ContentStore, DeepSeekGenerator
from .grading import grade, grade_and_record, grade_lesson_quiz
from .models import load_curriculum
from .scheduler import plan_day, current_lesson
from .store import Store
from .unlock import compute_states, next_unlocked_lesson, semester_progress

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CURRICULUM_PATH = PROJECT_ROOT / "curriculum" / "curriculum.json"
CONTENT_DIR = PROJECT_ROOT / "content"
DB_PATH = PROJECT_ROOT / "data" / "progress.db"


def _load() -> tuple:
    curriculum = load_curriculum(CURRICULUM_PATH)
    store = Store(DB_PATH)
    content = ContentStore(CONTENT_DIR)
    return curriculum, store, content


def _overview(curriculum, store) -> str:
    states = compute_states(curriculum, store)
    total = curriculum.total_lessons
    passed = sum(1 for s in states.values() if s.status == "passed")
    unlocked = sum(1 for s in states.values() if s.status == "unlocked")
    nxt = next_unlocked_lesson(curriculum, states)

    lines = [
        f"总进度：{passed}/{total} 课已通过（{passed / total * 100:.1f}%）",
        f"当前可解锁：{unlocked} 课",
    ]
    if nxt:
        lines.append(f"下一节课：{nxt.id}（知识点 {len(nxt.kps)} 个）")
    else:
        lines.append("下一节课：无（全部通过或全部锁定）")

    for sem in curriculum.semesters:
        p, t = semester_progress(curriculum, sem, states)
        lines.append(f"  {sem.id} {sem.name}：{p}/{t} 课通过")
    return "\n".join(lines)


def cmd_status(args) -> int:
    curriculum, store, _ = _load()
    print(_overview(curriculum, store))

    now = datetime.now()
    plan = plan_day(curriculum, store, now=now)
    print(f"\n[今日排课] {now.strftime('%Y-%m-%d %H:%M')} 实时时间")
    if plan.entries:
        for e in plan.entries:
            print(f"  {e.lesson_id}  {e.start_at.strftime('%H:%M')} - {e.end_at.strftime('%H:%M')}")
    print(f"  备注：{plan.note}")

    cur = current_lesson(curriculum, store)
    if cur:
        print(f"\n[进行中] {cur.lesson_id}（{cur.start_at.strftime('%H:%M')} 开始）")
    return 0


def cmd_schedule(args) -> int:
    curriculum, store, _ = _load()
    now = datetime.now()
    plan = plan_day(curriculum, store, now=now)
    print(f"排课时间：{plan.generated_at.strftime('%Y-%m-%d %H:%M:%S')}")
    print(plan.note)
    for e in plan.entries:
        print(f"  {e.start_at.strftime('%H:%M')} - {e.end_at.strftime('%H:%M')}  {e.lesson_id}")
    return 0


def _ask_quiz(content, threshold: float) -> tuple[list, float]:
    """交互式答题，返回 (submitted, score)。"""
    questions = content.quiz
    submitted: list = []
    print(f"随堂测验（{len(questions)} 题，通过需 {threshold * 100:.0f}%）")
    for i, q in enumerate(questions):
        print(f"\n[{i + 1}/{len(questions)}] {q.question}")
        for j, opt in enumerate(q.options):
            print(f"  {j + 1}. {opt}")
        while True:
            raw = input("你的答案（数字）> ").strip()
            if raw.isdigit() and 1 <= int(raw) <= len(q.options):
                submitted.append(int(raw) - 1)
                break
            print(f"请输入 1-{len(q.options)}")
    return submitted, grade([{"answer": q.answer} for q in questions], submitted)


def cmd_learn(args) -> int:
    curriculum, store, content = _load()
    states = compute_states(curriculum, store)
    lesson = next_unlocked_lesson(curriculum, states)
    if lesson is None:
        # 允许重做 in_progress 的课
        for l in curriculum.ordered_lessons():
            if states[l.id].status == "in_progress":
                lesson = l
                break
    if lesson is None:
        print("没有可学习的课（可能全部通过，或下一课被前置锁定）。")
        return 0

    lesson_content = content.lesson(lesson.id, lesson.kps)
    session_id = store.start_session(lesson.id)
    start = time.time()

    print(f"\n{'=' * 60}\n课程：{lesson_content.title}（{lesson.id}）\n知识点：{', '.join(lesson.kps)}\n{'=' * 60}")
    print(lesson_content.theory)
    print(f"\n（本节为 40 分钟课时，请认真学习后再答题）")

    submitted, score = _ask_quiz(lesson_content, curriculum.pass_threshold)
    result = grade_lesson_quiz(store, lesson.id, [{"answer": q.answer} for q in lesson_content.quiz], submitted, curriculum.pass_threshold)

    elapsed = int((time.time() - start) / 60)
    minutes = max(40, elapsed) if result["passed"] else elapsed
    store.end_session(session_id, minutes)

    verdict = "✅ 通过" if result["passed"] else "❌ 未通过（请复习后重试）"
    print(f"\n得分：{result['score'] * 100:.0f}%  {verdict}")
    if result["passed"]:
        nxt = next_unlocked_lesson(curriculum, compute_states(curriculum, store))
        print(f"下一课：{nxt.id if nxt else '（该单元完成，请参加单元考试）'}")
    return 0


def cmd_exam(args) -> int:
    curriculum, store, content = _load()
    exam_id = args.exam_id
    kind = "final" if exam_id.endswith("-final") else "unit"
    exam_content = content.exam(exam_id, kind)
    if not exam_content.questions:
        print(f"考试 {exam_id} 暂无题目，请先运行 `python -m src.cli update` 生成。")
        return 1

    print(f"\n{'=' * 60}\n考试：{exam_content.title}（{exam_id}）\n题目数：{len(exam_content.questions)}\n{'=' * 60}")
    submitted: list = []
    for i, q in enumerate(exam_content.questions):
        print(f"\n[{i + 1}/{len(exam_content.questions)}] {q.question}")
        for j, opt in enumerate(q.options):
            print(f"  {j + 1}. {opt}")
        while True:
            raw = input("你的答案 > ").strip()
            if raw.isdigit() and 1 <= int(raw) <= len(q.options):
                submitted.append(int(raw) - 1)
                break
            print(f"请输入 1-{len(q.options)}")

    result = grade_and_record(
        store, exam_id, kind,
        [{"answer": q.answer} for q in exam_content.questions],
        submitted, curriculum.pass_threshold,
    )
    verdict = "✅ 通过" if result["passed"] else "❌ 未通过"
    print(f"\n得分：{result['score'] * 100:.0f}%  {verdict}（通过线 {curriculum.pass_threshold * 100:.0f}%）")
    return 0


def cmd_update(args) -> int:
    curriculum, store, content = _load()
    gen = DeepSeekGenerator()
    target = args.target

    if target and not target.endswith("-final"):
        # 单节课
        lesson = curriculum.lessons_by_id[target]
        print(f"调用 DeepSeek 生成课程 {target} ...")
        lc = gen.generate_lesson(target, lesson.kps)
        content.save_lesson(lc)
        print(f"已保存 content/lessons/{target}.json")
    elif target and target.endswith("-final"):
        sem_id = target.split("-")[0]
        sem = curriculum.semesters_by_id[sem_id]
        scope = "；".join(f"{u.name}" for u in sem.units)
        print(f"调用 DeepSeek 生成期末考试 {target} ...")
        ec = gen.generate_exam(target, "final", scope)
        content.save_exam(ec)
        print(f"已保存 content/exams/{target}.json")
    elif target:
        # 单元考
        unit = curriculum.units_by_id[target]
        scope = "；".join(f"{l.id}" for l in unit.lessons)
        print(f"调用 DeepSeek 生成单元考 {target} ...")
        ec = gen.generate_exam(target, "unit", scope)
        content.save_exam(ec)
        print(f"已保存 content/exams/{target}.json")
    else:
        # 生成首学期全部（s1 的课 + 考试）
        s1 = curriculum.semesters[0]
        print(f"生成第 1 学期 {s1.name} 的全部内容（消耗 token）...")
        for unit in s1.units:
            for lesson in unit.lessons:
                lc = gen.generate_lesson(lesson.id, lesson.kps)
                content.save_lesson(lc)
                print(f"  ✓ {lesson.id}")
            scope = "；".join(l.id for l in unit.lessons)
            ec = gen.generate_exam(unit.id, "unit", scope)
            content.save_exam(ec)
            print(f"  ✓ 单元考 {unit.id}")
        ec = gen.generate_exam(f"{s1.id}-final", "final", s1.name)
        content.save_exam(ec)
        print(f"  ✓ 期末考 {s1.id}-final")
    return 0


def cmd_reset(args) -> int:
    _, store, _ = _load()
    confirm = input("确定清空全部学习进度？输入 YES 确认：").strip()
    if confirm == "YES":
        store.reset()
        print("已清空进度。")
    else:
        print("已取消。")
    return 0


def cmd_web(args) -> int:
    from .web import serve
    serve(port=args.port)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ai-architect-academy", description="Python & AI 架构师离线学习系统")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="查看学习进度与今日排课")
    sub.add_parser("schedule", help="查看今日 40 分钟排课计划")
    sub.add_parser("learn", help="开始下一节解锁的课")
    p_exam = sub.add_parser("exam", help="参加考试")
    p_exam.add_argument("exam_id", help="考试 id，如 s1u1 或 s1-final")
    p_update = sub.add_parser("update", help="调用 DeepSeek 生成内容（消耗 token）")
    p_update.add_argument("target", nargs="?", default=None, help="可选：lesson id / unit id / semester-final id，缺省生成 s1 全部")
    p_web = sub.add_parser("web", help="启动本地 Web 面板")
    p_web.add_argument("--port", type=int, default=8000, help="端口，默认 8000")
    sub.add_parser("reset", help="清空全部进度")

    args = parser.parse_args(argv)
    handlers = {
        "status": cmd_status,
        "schedule": cmd_schedule,
        "learn": cmd_learn,
        "exam": cmd_exam,
        "update": cmd_update,
        "web": cmd_web,
        "reset": cmd_reset,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
