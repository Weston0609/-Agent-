"""命令行界面 —— 标准库 argparse（零依赖）。

全局参数：
  --user <id>                指定学习用户（多用户；默认 default）

命令：
  pyai status                查看进度 / 今日排课 / token 计费
  pyai schedule              查看今日排课
  pyai learn <lesson_id>     读缓存内容（0 token）
  pyai class <lesson_id>     上一节 40 分钟课（8 阶段节奏，含随堂测验）
  pyai quiz <lesson_id>      随堂测验（判分 + BKT/FSRS 更新）
  pyai update [--max N]      拉取权威源并生成内容（唯一烧 token 处；无 key 时用本机 Ollama）
  pyai notify [--read]       查看/清理通知收件箱
  pyai daemon                启动常驻守护进程（自动排课/提醒/周更）
  pyai web [--port N]        启动 Web 面板
  pyai reset                 清空学习进度
"""
from __future__ import annotations

import argparse
import sys

from ..config import Config
from ..core.orchestrator import Orchestrator


def _extract_user(argv: list[str]) -> tuple[str | None, list[str]]:
    """取出任意位置的 `--user X` / `--user=X`（多用户），返回 (user, 其余参数)。"""
    rest: list[str] = []
    user: str | None = None
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--user" and i + 1 < len(argv):
            user, i = argv[i + 1], i + 2
            continue
        if a.startswith("--user="):
            user, i = a.split("=", 1)[1], i + 1
            continue
        rest.append(a)
        i += 1
    return user, rest


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    user_id, argv = _extract_user(argv)

    parser = argparse.ArgumentParser(
        prog="pyai",
        description="Python & AI 架构师离线学习系统（多用户：pyai --user <id> status）",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("status", help="查看进度与今日排课")
    sub.add_parser("schedule", help="查看今日排课")
    learn = sub.add_parser("learn", help="读缓存内容")
    learn.add_argument("lesson_id")
    cls = sub.add_parser("class", help="上一节 40 分钟课（8 阶段）")
    cls.add_argument("lesson_id")
    quiz = sub.add_parser("quiz", help="随堂测验")
    quiz.add_argument("lesson_id")
    boss = sub.add_parser("boss", help="打 Boss：把一节课的随堂测当作聊天对战（正确率 ≥85% 才算通关）")
    boss.add_argument("lesson_id", nargs="?", help="关卡 id，默认当前该打的下一关")
    boss.add_argument("--restart", action="store_true", help="重开一局（换一批没打过的题）")
    upd = sub.add_parser("update", help="联网生成内容（唯一烧 token 处）")
    upd.add_argument("--max", type=int, default=5, help="本轮最多生成几个知识点（默认 5）")
    upd.add_argument("--backfill-quiz", action="store_true",
                     help="补题模式：只给题量不足的 KP 补题，讲义不动")
    web = sub.add_parser("web", help="启动 Web 面板")
    web.add_argument("--port", type=int, default=8000)
    sub.add_parser("reset", help="清空学习进度")
    notif = sub.add_parser("notify", help="查看通知收件箱（上课提醒/召回/更新）")
    notif.add_argument("--read", action="store_true", help="全部标记为已读")
    sub.add_parser("daemon", help="常驻守护进程（15s tick + 07:00 排课 + 21:00 召回 + 周日更新）")
    exam = sub.add_parser("exam", help="章节考（unit，≥70%）/ 学期考（semester，≥75%）")
    exam.add_argument("scope", choices=["unit", "semester"], help="考试层级")
    exam.add_argument("scope_id", help="单元 id（如 s1u1）或学期 id（如 s1）")

    args = parser.parse_args(argv)
    config = Config.from_env()
    if args.command == "daemon":
        from ..daemon import main as run_daemon
        run_daemon()
        return 0
    orch = Orchestrator(config, user_id=user_id)

    try:
        if args.command in (None, "status"):
            return _status(orch)
        if args.command == "schedule":
            return _schedule(orch)
        if args.command == "learn":
            return _learn(orch, args.lesson_id)
        if args.command == "class":
            return _class(orch, args.lesson_id)
        if args.command == "quiz":
            return _quiz(orch, args.lesson_id)
        if args.command == "boss":
            return _boss(orch, args.lesson_id, args.restart)
        if args.command == "update":
            return _update(orch, args.max, getattr(args, "backfill_quiz", False))
        if args.command == "web":
            return _web(config, args.port)
        if args.command == "reset":
            orch.reset()
            print("学习进度已清空")
            return 0
        if args.command == "notify":
            if args.read:
                n = orch.mark_notifications_read()
                print(f"已标记 {n} 条通知为已读")
            return _notify(orch)
        if args.command == "exam":
            return _exam(orch, args.scope, args.scope_id)
    finally:
        orch.close()
    return 0


def _status(orch: Orchestrator) -> int:
    s = orch.status()
    print(f"用户：{s['user_id']}")
    print(f"现在：{s['now']}  ({s['today']})")
    print(f"进度：{s['passed_lessons']}/{s['lessons']} 课，{s['kps']} 个知识点")
    print(f"下一课：{s['next_lesson'] or '（全部完成）'}")
    _print_token_spend(s["token_spend"])
    _print_exam_overview(s.get("exams") or {})
    _print_day_plan(s["day_plan"])
    return 0


def _print_exam_overview(ex: dict) -> None:
    if not ex:
        return
    nxt = ex.get("next")
    if nxt:
        label = "章节考" if nxt["scope"] == "unit" else "学期考"
        print(f"可考：{label} {nxt['scope_id']}（通过线 {nxt['threshold']:.0%}）"
              f"—— `pyai exam {nxt['scope']} {nxt['scope_id']}`")
    else:
        print(f"考试：{ex.get('semester_id', '')} 暂无就绪的章节考/学期考")


def _print_token_spend(ts: dict) -> None:
    last = ts.get("last")
    tail = (f"最近一次 {last['ended_at']} [{last['status']}] 烧 {last['tokens_used']} token"
            if last else "尚未跑过更新")
    print(f"Token：累计 {ts['tokens']}（更新 {ts['runs']} 次，新增 KP {ts['kps_added']}）—— {tail}")

    budget = Config.from_env().monthly_token_budget
    month = ts.get("month", "")
    used = ts.get("month_tokens", 0)
    if budget > 0:
        pct = used * 100 // budget
        flag = "⚠️ " if used >= budget else ""
        print(f"本月预算：{flag}{used}/{budget}（{pct}%，{month}）")
    else:
        print(f"本月预算：不限（{month} 已用 {used}）")


def _schedule(orch: Orchestrator) -> int:
    _print_day_plan(orch.status()["day_plan"])
    return 0


def _notify(orch: Orchestrator) -> int:
    inbox = orch.notifications(limit=30)
    print(f"通知（未读 {inbox['unread']}）")
    if not inbox["items"]:
        print("  （暂无通知）")
        return 0
    for n in inbox["items"]:
        mark = " " if n.get("read_at") else "●"
        print(f"  {mark} [{n['kind']}] {n['created_at']}  {n['message']}")
    return 0


def _print_day_plan(day_plan: list[dict]) -> None:
    if day_plan:
        print("今日排课：")
        for e in day_plan:
            status = e.get("status", "pending")
            print(f"  [{status}] {e.get('type')}  {e.get('minutes')}min  "
                  f"{e.get('title', e.get('lesson_id', ''))}")
    else:
        print("今日无排课")


def _learn(orch: Orchestrator, lesson_id: str) -> int:
    content = orch.lesson_content(lesson_id)
    print(f"课程：{content['title']}（{lesson_id}）")
    for kp in content["kps"]:
        print("=" * 56)
        print(f"◆ {kp['id']}")
        if not kp.get("ok"):
            print("  （内容尚未生成，运行 `pyai update` 补齐）")
            continue
        print(f"讲解：{kp['explain']}")
        if kp.get("example_code"):
            print(f"示例：\n{kp['example_code']}")
        if kp.get("pitfalls"):
            print(f"误区：{kp['pitfalls']}")
    return 0


def _ask_answers(questions: list[dict]) -> list:
    answers: list = []
    for i, q in enumerate(questions, 1):
        print(f"\n{i}. [{q.get('type')}] {q.get('stem')}")
        options = q.get("options") or []
        for j, opt in enumerate(options):
            print(f"   {j}) {opt}")
        ans = input("你的答案（多选用逗号分隔）：").strip()
        if q.get("type") == "multi_choice" and ans:
            answers.append([int(x) for x in ans.split(",") if x.isdigit()])
        elif q.get("type") == "single_choice" and ans.isdigit():
            answers.append(int(ans))
        else:
            answers.append(ans)
    return answers


def _class(orch: Orchestrator, lesson_id: str) -> int:
    """上一节 40 分钟课：8 阶段节奏，讲授阶段读缓存（0 token），测验阶段随堂作答。"""
    from ..core.clock import RealClock
    from ..core.lesson_runner import LessonRunner

    session = orch.start_session(orch.user_id, lesson_id, orch.clock.now().date().isoformat())
    print(f"上课：{lesson_id}（40 分钟 · 8 阶段）")
    runner = LessonRunner(orch, orch.db, RealClock(), answers_provider=_ask_answers)
    result = runner.run(session)
    print("\n课堂记录：")
    for p in result["phases"]:
        print(f"  {'✓' if p['completed'] else '…'} {p['phase']:<16} {p['summary']}")
    prog = orch.db.get_lesson_progress(orch.user_id, lesson_id)
    if prog:
        verdict = "通过 ✅ 已解锁下一课" if prog["passed"] else "未通过 ❌ 明日补强"
        print(f"\n本课成绩：{prog['quiz_score']:.0%}  {verdict}")
    return 0


def _quiz(orch: Orchestrator, lesson_id: str) -> int:
    questions = orch.lesson_questions(lesson_id)
    if not questions:
        print(f"{lesson_id} 暂无题目（运行 `pyai update` 生成）")
        return 0
    print(f"随堂测验：{lesson_id}（{len(questions)} 题）")
    result = orch.submit_quiz(lesson_id, _ask_answers(questions))
    print(f"\n得分：{result['score']:.0%}，{'通过 ✅' if result['passed'] else '未通过 ❌'}")
    print(f"掌握度：{ {k: round(v['p_mastery'], 2) for k, v in result['per_kp'].items()} }")
    return 0


def _answer_one(q: dict) -> object:
    """问一道题（Boss 战逐题交手用）。"""
    print(f"\n[{q.get('type')}] {q.get('stem')}")
    for j, opt in enumerate(q.get("options") or []):
        print(f"   {j}) {opt}")
    ans = input("你的答案（多选用逗号分隔，回车＝跳过）：").strip()
    if q.get("type") == "multi_choice" and ans:
        return [int(x) for x in ans.split(",") if x.strip().isdigit()]
    if q.get("type") == "single_choice" and ans.isdigit():
        return int(ans)
    return ans


def _boss(orch: Orchestrator, lesson_id: str | None, restart: bool = False) -> int:
    """打 Boss：一题一回合，答对扣血、答错断连击，打完结算（正确率 ≥85% 通关）。"""
    if restart:
        view = orch.boss_restart(lesson_id)
        print(f"已重开一局：{view.get('lesson_id') or lesson_id}（BOSS 回满血，换一批没打过的题）")
    else:
        view = orch.boss_start(lesson_id)
    if view.get("error"):
        print(view["error"])
        return 0

    if view["round"] == 0:
        print(f"▶ BOSS 战：{view['lesson_id']}　血量 {view['max_hp']}　"
              f"共 {view['total']} 回合　通关线 {view['need']:.0%}")
    else:
        print(f"▶ 继续 BOSS 战：{view['lesson_id']}　血压 {view['hp']}/{view['max_hp']}　"
              f"已交手 {view['round']} 回合")

    while not view.get("finished"):
        q = view["question"]
        print(f"\n— 回合 {view['round'] + 1}/{view['total']}　"
              f"BOSS {'█' * int(10 * view['hp'] / view['max_hp'])}{'░' * (10 - int(10 * view['hp'] / view['max_hp']))} "
              f"{view['hp']}/{view['max_hp']}　当前正确率 {view['barrage']:.0%}")
        answer = _answer_one(q)
        view = orch.boss_hit(answer, lesson_id=view["lesson_id"])
        if view.get("error"):
            print(view["error"])
            return 0
        hit = view.get("hit") or {}
        if hit.get("perfect"):
            print(f"  ⚔️ 命中！-{hit['damage']} 血　连击 ×{view['combo']}"
                  + ("　🔥 连击奖励" if view["combo"] >= 3 else ""))
        elif hit.get("damage"):
            print(f"  ⚡ 擦到，-{hit['damage']} 血（未满分，连击中断）")
        else:
            print("  💥 打空了（答错），连击中断")
        if hit.get("feedback"):
            print(f"  {hit['feedback']}")
        if hit.get("explain"):
            print(f"  解析：{hit['explain']}")

    v = view.get("verdict") or {}
    print(f"\n{'🏆' if v.get('passed') else '💀'} 结算：正确率 {v.get('score', 0):.0%}"
          f"（通关线 {v.get('need', 0):.0%}）　命中 {v.get('hits')}/{v.get('total')}"
          f"　最高连击 ×{v.get('best_combo')}")
    if v.get("passed"):
        print(f"  BOSS 已被击败，已解锁下一关：{orch.status()['next_lesson'] or '（全部通关）'}")
    else:
        print("  BOSS 还没倒下。重来一次会换一批没打过的题："
              f"`pyai boss {view['lesson_id']} --restart`")
    return 0


def _exam(orch: Orchestrator, scope: str, scope_id: str) -> int:
    st = orch.exam_status(scope, scope_id)
    label = "章节考" if scope == "unit" else "学期考"
    print(f"{label}：{scope_id}（通过线 {st['threshold']:.0%}）")
    print(f"范围：{st['lessons_passed']}/{st['lessons']} 课已通过", end="")
    if st["passed"]:
        print(f"　已通过（{st['score']:.0%}，第 {st['attempts']} 次）")
    else:
        print()
    if not st["ready"]:
        print("尚未就绪：需先通过范围内全部课程。")
        return 0

    questions = orch.exam_questions(scope, scope_id)
    if not questions:
        print("范围内暂无题目（运行 `pyai update` 生成内容后再考）。")
        return 0
    print(f"\n共 {len(questions)} 题，请作答：")
    result = orch.submit_exam(scope, scope_id, _ask_answers(questions))
    print(f"\n得分：{result['score']:.0%}，"
          f"{'通过 ✅' if result['passed'] else '未通过 ❌'}（通过线 {result['threshold']:.0%}）")
    return 0


def _update(orch: Orchestrator, max_kps: int = 5, backfill_quiz: bool = False) -> int:
    from ..updater.pipeline import run_weekly_update
    if backfill_quiz:
        print(f"开始补题…（只补题库，讲义不动）本轮最多 {max_kps} 个知识点")
    else:
        print(f"开始更新…（唯一联网/烧 token 时刻）本轮最多 {max_kps} 个知识点")
    result = run_weekly_update(orch.db, manual=True, max_kps=max_kps, backfill_quiz=backfill_quiz)
    print(f"完成：后端 {result['backend']}，烧 {result['tokens_used']} token，"
          f"新增 {result['kps_added']}，跳过 {result['kps_skipped']}（{result['status']}）")
    return 0


def _web(config: Config, port: int) -> int:
    from .web.app import serve
    serve(config, port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
