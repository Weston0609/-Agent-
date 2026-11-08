"""编排器 —— DB 驱动的唯一入口（CLI / Web / Daemon 都经由此）。

职责：初始化（建库/默认用户/默认课表/种课程树）、状态查询、会话生命周期、
内容读取（kp_content 0 token）、判分 + BKT/FSRS 更新。
"""
from __future__ import annotations

import json
import random
from datetime import datetime, timedelta

from ..config import Config
from ..db.derive import backfill as derive_backfill
from ..db.seed_content import seed_content
from ..db.session import BOSS_PASS, KP_PASS, Database
from ..learning.bkt import update as bkt_update
from ..learning.curriculum import load_curriculum
from ..learning.fsrs import schedule_next as fsrs_schedule
from ..learning.grading import grade_quiz, quiz_score
from ..learning.scheduler import plan_lessons as _plan_lessons
from .boss import BossState, start_boss, take_hit, verdict
from .boss import from_dict as boss_from_dict
from .clock import Clock, RealClock
from .interactions import build as interactions_build
from .interactions import check as interactions_check
from .interactions import public as interactions_public
from .plainlang import build as plainlang_build
from . import codesplain
from .state import ActiveSession, PhaseResult, Stage

# 打 Boss 时每个知识点抽几道。题库每 KP 约 20 道变体，若全端上去，一节 4 KP 的课就是 80 道，
# 10 分钟的测验做不完。卷子会落库固定，重开一局（boss_restart）才重抽，且优先没打过的题。
QUIZ_PER_KP = 3


def _answer_hint(qtype: str | None, keywords: list | None) -> str:
    """告诉学习者「这题会怎么判」，但**不泄露答案**。

    场景题的关键词本身就是答案，不能下发；可只给一个字数与要点的提示，
    否则学习者面对一个空白输入框，根本不知道该答几句、答哪些方面——
    题就变成了不可赢的（实测：认真作答也只能拿 0.25，永远够不到 85% 通关线）。
    """
    if qtype == "scenario":
        keys = [str(k).strip() for k in (keywords or []) if str(k).strip()]
        if not keys:
            return ""
        # 只给数量，不给内容：知道「要覆盖 N 个要点」足以组织答案，又不等于抄答案。
        return f"这题按要点命中率评分：答出其中 {max(1, round(len(keys) * 0.7))} 个以上要点即算通过（共 {len(keys)} 个采分点）。"
    if qtype == "fill_blank":
        return "填出空格处的代码/名称即可，答案会做大小写与空白归一化。"
    if qtype == "code_reading":
        # 题库里 code_reading 全部是纯文字作答（无 options），判分见 grading.py：
        # 有采分点按命中率，没有就从标准答案抽采分点（输出值、变量名、报错类型）比对。
        keys = [str(k).strip() for k in (keywords or []) if str(k).strip()]
        if keys:
            return f"用文字写出你的推理：说中其中 {max(1, round(len(keys) * 0.7))} 个要点即算通过（共 {len(keys)} 个采分点）。"
        return "用文字写出你的推理：把**输出结果**和关键变量/函数说清楚，只说「能跑」或空泛描述不算通过。"
    return ""


class Orchestrator:
    def __init__(self, config: Config, clock: Clock | None = None, user_id: str | None = None):
        self.config = config
        self.clock = clock or RealClock()
        config.ensure_dirs()
        self.db = Database(config.db_path)
        self.user_id = user_id or config.default_user_id
        self.db.ensure_user(self.user_id, config.default_user_name, config.timezone)
        if self.db.schedule_slot_count(self.user_id) == 0:
            self.db.seed_default_schedule(self.user_id)
        if self.db.kp_count() < self._curriculum_kp_count():
            self._seed_curriculum()
        # 种子内容（随发行版提供、从第 1 课开始）每次启动都写入：它只覆盖这 10 个种子 KP，
        # 与 update 生成的另外 375 个 KP 不重叠，重复写入是幂等的。
        # ponytail: 若日后 update 重写了这 10 个 KP，重启会被种子覆盖；届时给
        # kp_content 加来源标记（seed|generated）并只在缺失时写入即可。
        self._seed_content()
        # 中文课名/知识点名与题目难度：库里这两列本来是裸 id 与常量 1，
        # 数据其实都在（讲义 H1 里有中文标题），启动时按版本号幂等回填一次。
        derive_backfill(self.db)

    def _seed_content(self) -> dict:
        return seed_content(self.db, self.config.content_dir)

    def _curriculum_kp_count(self) -> int:
        """课程树里声明的 KP 总数。库里比它少就说明 YAML 新增了课，要重种。"""
        try:
            curriculum = load_curriculum(self.config.curriculum_path)
        except (OSError, ValueError):
            return self.db.kp_count()      # 读不到就当作没变化，别把课程树删空
        return sum(len(l.kps) for s in curriculum.semesters
                   for u in s.units for l in u.lessons)

    # ---------- 初始化 ----------
    def _seed_curriculum(self) -> dict:
        curriculum = load_curriculum(self.config.curriculum_path)
        return self.db.seed_curriculum(curriculum)

    # ---------- 状态 ----------
    def status(self) -> dict:
        now = self.clock.now()
        total = self.db.lesson_count()
        passed_ids = self.db.passed_lesson_ids(self.user_id)
        passed = sum(1 for l in self.db.all_lessons_in_order() if l.id in passed_ids)
        nxt = self._next_lesson()
        day_plan = self._today_plan(now)
        due = self.db.due_reviews(self.user_id, now)
        remedial = self.db.pending_remedial(self.user_id)
        return {
            "now": now.isoformat(timespec="seconds"),
            "today": now.date().isoformat(),
            "weekday": now.weekday(),
            "user_id": self.user_id,
            "lessons": total,
            "kps": self.db.kp_count(),
            "passed_lessons": passed,
            "next_lesson": nxt.id if nxt else None,
            "day_plan": day_plan,
            "due_reviews": len(due),
            "remedial": remedial.id if remedial else None,
            "token_spend": self.db.token_spend(),
            "monthly_token_budget": self.config.monthly_token_budget,
            "exams": self._exam_overview(now),
        }

    def _exam_overview(self, now: datetime) -> dict:
        """最早一场「已就绪、未通过」的章节考/学期考。

        以前只看 next_lesson 所在学期：真实库里 178 课全过、next_lesson 在 s8，
        于是界面永远只给 s8u1，s1~s7 那几十场早就就绪的考试一个都点不到。
        按课程顺序从第一学期扫起，考完一场才轮到下一场。
        """
        lessons = self.db.all_lessons_in_order()
        if not lessons:
            return {}
        out: dict = {}
        seen_semesters: list[str] = []
        for lesson in lessons:
            if lesson.semester_id in seen_semesters:
                continue
            seen_semesters.append(lesson.semester_id)
            sem = lesson.semester_id
            out.setdefault("semester_id", sem)
            for unit in self.db.semester_unit_ids(sem):
                st = self.db.exam_status(self.user_id, "unit", unit)
                if st["ready"] and not st["passed"]:
                    out["next"] = {"scope": "unit", "scope_id": unit, **st}
                    return out
            st = self.db.exam_status(self.user_id, "semester", sem)
            if st["ready"] and not st["passed"]:
                out["next"] = {"scope": "semester", "scope_id": sem, **st}
                return out
        return out

    def _next_lesson(self):
        from ..learning.scheduler import _pick_next_lesson
        return _pick_next_lesson(self.db, self.user_id)

    def _today_plan(self, now: datetime) -> list[dict]:
        today = now.date().isoformat()
        plan = self.db.get_day_plan(self.user_id, today)
        if plan is not None:
            return plan.lessons
        available = sum(s.duration_minutes for s in self.db.slots_for(self.user_id, now.weekday()))
        lessons = _plan_lessons(self.db, self.user_id, available, now.date())
        self.db.save_day_plan(self.user_id, today, lessons)
        return lessons

    def plan_lessons(self, user_id: str, available_minutes: int, today) -> list[dict]:
        return _plan_lessons(self.db, user_id, available_minutes, today)

    def course_map(self, user_id: str | None = None) -> dict:
        """闯关地图：完整课程树（学期→单元→课）+ 每课状态 + 当前闯关位置。"""
        from ..learning.scheduler import _pick_next_lesson
        uid = user_id or self.user_id
        semesters = self.db.course_tree(uid)
        nxt = _pick_next_lesson(self.db, uid)
        return {
            "user_id": uid,
            "passed": sum(s["passed"] for s in semesters),
            "total": sum(s["total"] for s in semesters),
            "current": {"lesson_id": nxt.id, "semester_id": nxt.semester_id} if nxt else None,
            "semesters": semesters,
        }

    # ---------- 会话生命周期 ----------
    def start_session(self, user_id: str, lesson_id: str, plan_date: str) -> ActiveSession:
        sid = self.db.start_session(user_id, lesson_id, plan_date, Stage.RUNNING.value)
        return ActiveSession(id=sid, user_id=user_id, lesson_id=lesson_id, plan_date=plan_date)

    def finalize_session(self, session: ActiveSession) -> None:
        self.db.finalize_session(session.id)

    # ---------- 内容（0 token，读 kp_content）----------
    def lesson_content(self, lesson_id: str) -> dict:
        lesson = self.db.get_lesson(lesson_id)
        kps = []
        for kp in self.db.lesson_kps(lesson_id):
            c = self.db.get_kp_content(kp.id)
            if c is None:
                kps.append({"id": kp.id, "title": kp.title, "ok": False})
            else:
                kps.append({
                    "id": kp.id, "title": kp.title, "ok": True,
                    "explain": c.explain, "example_code": c.example_code,
                    "pitfalls": c.pitfalls, "sources": c.sources,
                    "plain": plainlang_build(c.explain, c.example_code, c.pitfalls),
                    # 代码逐块讲解：什么意思 / 为什么这么写 / 语法点 / 容易忽略的地方
                    "code_units": codesplain.explain(c.example_code),
                    "code_syntax": codesplain.syntax_notes(c.example_code),
                    "code_error": codesplain.compile_check(c.example_code) if c.example_code else None,
                })
        return {
            "lesson_id": lesson_id,
            "title": lesson.name if lesson else lesson_id,
            "kps": kps,
        }

    def lesson_questions(self, lesson_id: str, per_kp: int | None = None) -> list[dict]:
        """组卷（打 Boss 的题面）：每个知识点抽 per_kp 道，默认 QUIZ_PER_KP。

        卷子**落库固定**：GET /api/questions、判分、以及重复提交看到的是同一批题。
        （旧实现按 attempts 现算，而 attempts 每次提交都 +1，取题与判分必然错位，
        表现为「答对自己看到的卷子却只拿 56%」。）

        重做换卷由 boss_restart() 负责，抽题优先挑本课没打过的题，题池用完才允许重复。
        """
        n = QUIZ_PER_KP if per_kp is None else per_kp
        paper = self.db.get_paper(self.user_id, lesson_id)
        if paper:
            return self.db.questions_by_ids(paper) if per_kp is None else self._rebuild(
                lesson_id, n, paper)

        # 首次组卷：逐 KP 从「未用过」的题里随机抽 n 道。
        out: list[dict] = []
        used = self.db.unused_question_ids(self.user_id, lesson_id)
        for kp_id in self.db.lesson_kp_ids(lesson_id):
            pool = self.db.questions_for(kp_id)
            if not pool:
                continue
            fresh = [q for q in pool if q["id"] not in used]
            pick = self._draw(fresh if len(fresh) >= n else pool, n)
            out.extend(pick)
        if per_kp is None:
            self.db.save_paper(self.user_id, lesson_id, [q["id"] for q in out])
        return out

    @staticmethod
    def _draw(pool: list[dict], n: int) -> list[dict]:
        """从题池随机抽 n 道；题池不够就全给（不重复同一道）。"""
        if n <= 0:
            return []
        if len(pool) <= n:
            return list(pool)
        return random.sample(pool, n)

    # ---------- 课堂互动（每小节一个白云气泡小问）----------
    def lesson_interactions(self, lesson_id: str, user_id: str | None = None) -> dict:
        """本课每个知识点各一个互动项（0 token，题目取自已落库题库）。

        走独立于 Boss 卷子的题源：直接用该 KP 的全部题库，不消费 quiz_papers，
        所以课堂互动不会把 Boss 的卷子用掉，也不影响通关判定。
        """
        content = self.lesson_content(lesson_id)
        pools = {kp_id: self.db.questions_for(kp_id)
                 for kp_id in self.db.lesson_kp_ids(lesson_id)}
        built = interactions_build(content["kps"], pools, per_kp=1)
        return {
            "lesson_id": lesson_id,
            "items": {kp_id: interactions_public(item)
                      for kp_id, item in built["items"].items()},
        }

    def check_interaction(self, lesson_id: str, item_id: str, answer) -> dict:
        """判一道互动题。互动只给即时反馈、不计入成绩，所以不写 mastery/error_log。"""
        content = self.lesson_content(lesson_id)
        pools = {kp_id: self.db.questions_for(kp_id)
                 for kp_id in self.db.lesson_kp_ids(lesson_id)}
        built = interactions_build(content["kps"], pools, per_kp=1)
        item = next((it for it in built["items"].values() if it["id"] == item_id), None)
        if item is None:
            return {"error": "互动题不存在（可能已换课）"}
        return interactions_check(item, answer)

    def _rebuild(self, lesson_id: str, n: int, paper: list[str]) -> list[dict]:
        """按已固定的卷子取前 n 道/KP（per_kp 显式指定时用）。"""
        return self.db.questions_by_ids(paper)[: n * max(1, len(self.db.lesson_kp_ids(lesson_id)))]

    def boss_restart(self, lesson_id: str | None = None, user_id: str | None = None) -> dict:
        """重开一局：收掉进行中的战况、作废卷子，再开一局（换一批没打过的题）。

        boss_start 会续用进行中的战况（刷新页面不该重置血量），所以重开必须先收摊。
        """
        uid = user_id or self.user_id
        live = self.db.get_active_session(uid)
        if live:
            self.db.finalize_session(live["id"])
        lesson_id = lesson_id or (self.course_map(uid)["current"] or {}).get("lesson_id")
        if lesson_id:
            self.db.clear_paper(uid, lesson_id)
        return self.boss_start(lesson_id, uid)

    # ---------- 打 Boss（随堂测 = 聊天对战）----------
    def boss_start(self, lesson_id: str | None = None, user_id: str | None = None) -> dict:
        """开一局。不传 lesson_id 就用当前该打的下一课。

        卷子已由 lesson_questions 落库固定；中途刷新页面调本方法会拿到同一局战况
        （战况存在 sessions.state_json），不会重置血量。
        """
        uid = user_id or self.user_id
        lesson_id = lesson_id or (self.course_map(uid)["current"] or {}).get("lesson_id")
        if not lesson_id:
            return {"error": "没有可打的关卡（已全部通关）"}

        live = self.db.get_active_session(uid)
        if live and live.get("state_json"):
            try:
                saved = json.loads(live["state_json"])
            except (ValueError, TypeError):
                saved = None
            if saved and saved.get("lesson_id") == lesson_id:
                return self.boss_view(boss_from_dict(saved), uid)

        questions = self.lesson_questions(lesson_id)
        if not questions:
            return {"error": f"{lesson_id} 还没有题目"}
        state = start_boss(lesson_id, [q["id"] for q in questions])
        sid = self.db.start_session(uid, lesson_id, self.clock.now().date().isoformat(),
                                    Stage.RUNNING.value, json.dumps(state.to_dict()))
        return self.boss_view(state, uid, session_id=sid)

    def boss_view(self, state, user_id: str | None = None, session_id: str | None = None) -> dict:
        """当前战况 + 下一题题面（不含答案）。"""
        uid = user_id or self.user_id
        idx = state.next_index
        nxt = None
        if not state.finished:
            row = self.db.questions_by_ids([state.question_ids[idx]])
            if row:
                q = dict(row[0])
                keywords = q.pop("required_keywords", None)
                q.pop("answer", None)
                hint = _answer_hint(q.get("type"), keywords)
                if hint:
                    q["answer_hint"] = hint
                nxt = q
        out = {
            "user_id": uid,
            "lesson_id": state.lesson_id,
            "hp": state.hp,
            "max_hp": state.max_hp,
            "round": state.round,
            "hits": state.hits,
            "total": state.total,
            "combo": state.combo,
            "best_combo": state.best_combo,
            "barrage": round(state.barrage, 4),
            "need": BOSS_PASS,
            "finished": state.finished,
            "question": nxt,
        }
        if state.finished:
            out["verdict"] = verdict(state)
            out["lesson_progress"] = self.db.get_lesson_progress(uid, state.lesson_id)
        return out

    def boss_hit(self, answer, user_id: str | None = None, lesson_id: str | None = None) -> dict:
        """对 Boss 出一招：判分 → 扣血 → 存战况。回合结束若打光则结算并记录过关。"""
        uid = user_id or self.user_id
        live = self.db.get_active_session(uid)
        if not live or not live.get("state_json"):
            return {"error": "没有进行中的 Boss 战，请先 boss_start"}
        state = boss_from_dict(json.loads(live["state_json"]))
        if lesson_id and state.lesson_id != lesson_id:
            return {"error": f"当前在打 {state.lesson_id}，不是 {lesson_id}"}
        if state.finished:
            return self.boss_view(state, uid)

        q = self.db.questions_by_ids([state.question_ids[state.next_index]])[0]
        g = grade_quiz([q], [answer])[0]
        fx = take_hit(state, g.score, answer)
        # 掌握度/错题照常记，Boss 战不是另一套学习数据。
        self._apply_grades(state.lesson_id, [q], [g], [answer])
        self.db.record_question_used(uid, state.lesson_id, [q["id"]])
        self.db.update_session_state(live["id"], json.dumps(state.to_dict()))

        view = self.boss_view(state, uid, session_id=live["id"])
        view["hit"] = {**fx, "feedback": g.feedback, "explain": q.get("explanation", "")}
        if state.finished:
            result = self.submit_boss_verdict(state, uid)
            view["verdict"] = result
            view["lesson_progress"] = self.db.get_lesson_progress(uid, state.lesson_id)
        return view

    def submit_boss_verdict(self, state, uid: str) -> dict:
        """结算一场打光的 Boss 战：≥85% 记通关并收摊，<85% 作废卷子等重开。"""
        v = verdict(state)
        progress = self.db.record_lesson_score(uid, state.lesson_id, state.barrage)
        live = self.db.get_active_session(uid)
        if live:
            self.db.finalize_session(live["id"])
        if not progress["passed"]:
            # 没打过 → 作废卷子，下次重开换一批没打过的题。
            self.db.clear_paper(uid, state.lesson_id)
        return {**v, "passed": progress["passed"], "need": BOSS_PASS}

    # ---------- 判分 + 掌握度更新 ----------
    def submit_quiz(self, lesson_id: str, answers: list) -> dict:
        questions = self.lesson_questions(lesson_id)
        grades = grade_quiz(questions, answers)
        score = quiz_score(grades)
        per_kp = self._apply_grades(lesson_id, questions, grades, answers)
        # 记消费账：下次重做只要还有没打过的题，就不会再遇到这些题。
        self.db.record_question_used(self.user_id, lesson_id, [q["id"] for q in questions])
        # 学校式闯关门禁：本课测验 ≥ 单元考线（75%）即通过该课并解锁下一课。
        # 注意与知识点掌握线（KP_PASS=80%）区分：后者只驱动复习与补强，不参与硬门禁。
        # BKT 掌握度仍照常更新，供 FSRS 复习队列与补强使用（不作为硬门禁）。
        progress = self.db.record_lesson_score(self.user_id, lesson_id, score)
        if not progress["passed"]:
            # 没打过：作废本题卷，下次重开换一批新题（用户要求：重做不得重复上次的题）。
            self.db.clear_paper(self.user_id, lesson_id)
        return {
            "lesson_id": lesson_id,
            "score": score,
            "passed": progress["passed"],
            "per_kp": per_kp,
            "mastered_all": all(m["p_mastery"] >= KP_PASS for m in per_kp.values()),
            "lesson_progress": progress,
        }

    def _apply_grades(self, lesson_id: str | None, questions: list[dict], grades: list,
                      answers: list | None = None) -> dict:
        """按 KP 聚合正确率 → BKT 更新 + FSRS 调度 + 错题记录。

        lesson_id 仅用于追溯，考试（章节考/学期考）跨多课故传 None。
        """
        from ..learning.grading import Grade
        now = self.clock.now()
        answers = answers or []
        per_kp: dict[str, dict] = {}
        kp_questions: dict[str, list[tuple[dict, Grade, object]]] = {}
        for i, (q, g) in enumerate(zip(questions, grades)):
            ans = answers[i] if i < len(answers) else None
            kp_questions.setdefault(q["kp_id"], []).append((q, g, ans))

        for kp_id, pairs in kp_questions.items():
            ratio = sum(g.score for _, g, _ in pairs) / max(1, len(pairs))
            m = self.db.get_mastery(self.user_id, kp_id)
            m.p_mastery = bkt_update(m.p_mastery, ratio)
            m.attempts += 1
            m.correct += sum(1 for _, g, _ in pairs if g.correct)
            self.db.save_mastery(m)

            card = self.db.get_review_card(self.user_id, kp_id)
            card_state = card.card if card else None
            new_card, due = fsrs_schedule(card_state, ratio >= 0.5, now)
            self.db.save_review_card(self.user_id, kp_id, new_card, due)

            for q, g, ans in pairs:
                if not g.correct:
                    self.db.record_error(
                        self.user_id, kp_id, q.get("id"), str(ans),
                        g.error_type or "概念混淆",
                    )

            per_kp[kp_id] = {"ratio": ratio, "p_mastery": m.p_mastery}
        return per_kp

    # ---------- 章节考 / 学期考 ----------
    def exam_status(self, scope: str, scope_id: str) -> dict:
        return self.db.exam_status(self.user_id, scope, scope_id)

    def exam_questions(self, scope: str, scope_id: str) -> list[dict]:
        """整卷：范围内每课抽题汇总。范围未就绪（有课没过）时返回空。"""
        st = self.db.exam_status(self.user_id, scope, scope_id)
        if not st["ready"]:
            return []
        out: list[dict] = []
        for lesson_id in self.db.scope_lesson_ids(scope, scope_id):
            out.extend(self.lesson_questions(lesson_id))
        return out

    def exam_view(self, scope: str, scope_id: str) -> dict:
        """考试题面：与 boss_view 同口径剥掉 answer/required_keywords。

        GET 直接回 exam_questions() 会把标准答案发给浏览器（打开 DevTools 就能抄），
        考试比课堂小测更不该这样。题序与提交时一致（卷子落库固定），所以按题面数组
        顺序交 answers 即可。
        """
        st = self.db.exam_status(self.user_id, scope, scope_id)
        items = []
        for q in self.exam_questions(scope, scope_id):
            items.append({
                "id": q.get("id"),
                "kp_id": q.get("kp_id"),
                "type": q.get("type"),
                "difficulty": q.get("difficulty"),
                "stem": q.get("stem"),
                "options": q.get("options") or [],
                "answer_hint": _answer_hint(q.get("type"), q.get("required_keywords")),
            })
        return {"scope": scope, "scope_id": scope_id, "status": st, "questions": items}

    def submit_exam(self, scope: str, scope_id: str, answers: list) -> dict:
        """交卷。判分口径与课堂小测一致（grade_quiz/quiz_score），
        但通过线按考试层级取值：章节考 70%、学期考 75%。"""
        st = self.db.exam_status(self.user_id, scope, scope_id)
        questions = self.exam_questions(scope, scope_id)
        if not questions:
            return {"scope": scope, "scope_id": scope_id, "ok": False,
                    "reason": "该考试范围尚未就绪：需先通过范围内全部课程。"}

        grades = grade_quiz(questions, answers)
        score = quiz_score(grades)
        per_kp = self._apply_grades(None, questions, grades, answers)
        result = self.db.record_exam_score(self.user_id, scope, scope_id, score)
        return {
            "scope": scope,
            "scope_id": scope_id,
            "ok": True,
            "score": score,
            "threshold": result["threshold"],
            "passed": result["passed"],
            "attempts": result["attempts"],
            "answered": len(questions),
            "per_kp": per_kp,
        }

    # ---------- 课堂阶段处理器（供 lesson_runner 40 分钟节奏调用）----------
    def run_warmup(self, session: ActiveSession, deadline: datetime) -> PhaseResult:
        due = self.db.due_reviews(session.user_id, self.clock.now())
        warmup = self.db.pop_warmup(session.user_id)
        return PhaseResult(completed=True, summary=f"到期复习 {len(due)} 项，补强 {len(warmup)} 项")

    def preview_goals(self, session: ActiveSession, deadline: datetime) -> PhaseResult:
        kps = self.db.lesson_kp_ids(session.lesson_id)
        return PhaseResult(completed=True, summary="；".join(kps))

    def teach_phase(self, session: ActiveSession, deadline: datetime) -> PhaseResult:
        content = self.lesson_content(session.lesson_id)
        n_ok = sum(1 for k in content["kps"] if k.get("ok"))
        return PhaseResult(completed=n_ok > 0, summary=f"{n_ok}/{len(content['kps'])} 个 KP 有缓存内容")

    def guided_practice(self, session: ActiveSession, deadline: datetime) -> PhaseResult:
        content = self.lesson_content(session.lesson_id)
        n_code = sum(1 for k in content["kps"] if k.get("example_code"))
        return PhaseResult(completed=n_code > 0, summary=f"{n_code} 个可动手示例")

    def run_quiz(self, session: ActiveSession, deadline: datetime,
                 answers: list | None = None) -> PhaseResult:
        """测验阶段。传入 answers（课堂内作答）时立即判分并更新掌握度；
        为 None 时只报题量，成绩由 UI/CLI 的 submit_quiz 单独回传。"""
        qs = self.lesson_questions(session.lesson_id)
        kp_ids = self.db.lesson_kp_ids(session.lesson_id)
        first_kp = kp_ids[0] if kp_ids else ""
        if not qs:
            return PhaseResult(
                completed=False,
                pending_item={"kp_id": first_kp, "note": "本课暂无测验题"},
                summary="暂无测验题",
            )
        if answers is None:
            return PhaseResult(completed=True, summary=f"{len(qs)} 道题（待作答）")
        result = self.submit_quiz(session.lesson_id, answers)
        passed = result["passed"]
        pending = None if passed else {
            "kp_id": first_kp, "note": f"本课测验 {result['score']:.0%} 未达标，需补强",
        }
        return PhaseResult(
            completed=passed, pending_item=pending,
            summary=f"测验 {result['score']:.0%}（{'通过' if passed else '未通过'}）",
        )

    def evaluate(self, session: ActiveSession, deadline: datetime) -> PhaseResult:
        prog = self.db.get_lesson_progress(session.user_id, session.lesson_id)
        if not prog:
            return PhaseResult(completed=True, summary="本次未作答，已记入明日热身")
        return PhaseResult(
            completed=True,
            summary=f"测验 {prog['quiz_score']:.0%}，第 {prog['attempts']} 次作答",
        )

    def summarize(self, session: ActiveSession, deadline: datetime) -> PhaseResult:
        return PhaseResult(completed=True, summary="本课小结")

    def schedule_review(self, session: ActiveSession, deadline: datetime) -> PhaseResult:
        due = self.db.due_reviews(session.user_id, self.clock.now())
        return PhaseResult(completed=True, summary=f"已排 {len(due)} 项复习")

    # ---------- 三个「有数据但零入口」的后端：错题本 / 复习队列 / 考试记录 ----------
    # count 一律取总数（不是 len(items)）：列表有 limit，界面写「383 项到期」不能
    # 因为只显示 200 条就变成「200 项」。
    def review_items(self, user_id: str | None = None) -> dict:
        uid = user_id or self.user_id
        items = self.db.review_items(uid, self.clock.now())
        return {"user_id": uid,
                "count": self.db.due_review_count(uid, self.clock.now()),
                "items": items}

    def error_items(self, user_id: str | None = None) -> dict:
        uid = user_id or self.user_id
        items = self.db.error_items(uid)
        return {"user_id": uid, "count": self.db.error_count(uid), "items": items}

    def exam_results(self, user_id: str | None = None) -> dict:
        uid = user_id or self.user_id
        items = self.db.exam_results(uid)
        return {"user_id": uid, "count": len(items), "items": items}

    def ready_exams(self, user_id: str | None = None) -> dict:
        """全部「已就绪、未通过」的章节考/学期考，按课程顺序。

        真实库里 178 课全过 → 48 个单元考全就绪，但界面上只能点到「下一场」，
        其余几十场没法自己挑。这里一次列全，界面上可以逐场开考。
        """
        uid = user_id or self.user_id
        out: list[dict] = []
        seen: set[str] = set()
        for lesson in self.db.all_lessons_in_order():
            sem = lesson.semester_id
            if sem in seen:
                continue
            seen.add(sem)
            for unit in self.db.semester_unit_ids(sem):
                st = self.db.exam_status(uid, "unit", unit)
                if st["ready"] and not st["passed"]:
                    out.append({"scope": "unit", "scope_id": unit, **st})
            st = self.db.exam_status(uid, "semester", sem)
            if st["ready"] and not st["passed"]:
                out.append({"scope": "semester", "scope_id": sem, **st})
        return {"user_id": uid, "count": len(out), "items": out}

    # ---------- 通知收件箱 ----------
    def notifications(self, user_id: str | None = None, limit: int = 20) -> dict:
        uid = user_id or self.user_id
        return {
            "user_id": uid,
            "unread": self.db.unread_count(uid),
            "items": self.db.notifications(uid, limit),
        }

    def mark_notifications_read(self, user_id: str | None = None) -> int:
        return self.db.mark_notifications_read(user_id or self.user_id)

    # ---------- 工具 ----------
    def reset(self) -> None:
        self.db.reset_progress(self.user_id)

    def close(self) -> None:
        self.db.close()
