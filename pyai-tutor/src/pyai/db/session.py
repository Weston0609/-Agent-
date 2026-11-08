"""数据访问层 —— stdlib sqlite3 直连，线程安全。

多表仓储：users / schedule_slots / 课程树(semesters→units→lessons→kps) /
kp_content / questions / mastery / review_queue / error_log / warmup_items /
sessions / day_plans / updates_log / audit_log。

schema 权威源见同目录 schema.sql，这里按同一结构读写。
"""
from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import datetime
from pathlib import Path

from ..db.models import (
    DayPlan,
    KP,
    KPContent,
    Lesson,
    Mastery,
    ReviewCard,
    ScheduleSlot,
    User,
)

_SCHEMA = (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8")

DEFAULT_USER_ID = "default"

# 第六部分约束表：知识点通过线 ≥80%，单元考 ≥75%，章节考 ≥70%，学期考 ≥75%。
KP_PASS = 0.80          # 知识点掌握线（p_mastery）
BOSS_PASS = 0.85        # 打 Boss（随堂测）通过线——比单元考更严，通过才算通关并解锁下一关
LESSON_PASS = 0.75      # 单元考通过线（章节/学期卷里的逐课判定）
CHAPTER_PASS = 0.70     # 章节考通过线（单元整卷）
SEMESTER_PASS = 0.75    # 学期考通过线（整学期整卷）
MASTERY_PASS = LESSON_PASS   # 兼容旧引用

# 讲义的最小学得会的长度。手写种子每个 KP 只有几十字（够开箱即用，撑不起 12 分钟讲授），
# 题库却按完整知识点生成了每 KP 20 道——于是「随堂测考的都是没教过的」。
# 凡是短于此的 kp_content 一律视为尚未填充，交给 update 管道重讲。
# 实测真讲义中位数约 3900 字、最短 2000+，手写种子 19~643 字，中间是断档，取 800 分界。
MIN_LECTURE_CHARS = 800


class _LockedCursor:
    """已物化的游标：execute 一返回，行就全在内存里，不再持有 sqlite 语句。"""
    __slots__ = ("_rows", "_pos", "lastrowid", "rowcount")

    def __init__(self, rows, lastrowid=None, rowcount=-1):
        self._rows = rows
        self._pos = 0
        self.lastrowid = lastrowid
        self.rowcount = rowcount

    def fetchone(self):
        if self._pos >= len(self._rows):
            return None
        self._pos += 1
        return self._rows[self._pos - 1]

    def fetchall(self):
        rest = self._rows[self._pos:]
        self._pos = len(self._rows)
        return rest

    def __iter__(self):
        return iter(self._rows)


class _LockedConnection:
    """给 sqlite3 连接套一把可重入锁，并把每次 execute 的结果立即物化。

    共用一条连接本身没问题，问题是「一个线程的游标还在迭代时，另一个线程 execute」——
    会抛 InterfaceError: bad parameter or other API misuse（sqlite3.threadsafety==3 也只
    保证 C 层内部状态，不保证 Python 游标对象）。物化之后语句立刻收尾，跨线程互踩消失。

    只实现本项目实际用到的四个方法（grep 确认无 cursor() / rollback）。
    """

    def __init__(self, conn: sqlite3.Connection, lock):
        self._conn = conn
        self._lock = lock

    def execute(self, sql: str, params=()) -> _LockedCursor:
        with self._lock:
            cur = self._conn.execute(sql, params)
            rows = cur.fetchall()
            return _LockedCursor(rows, cur.lastrowid, cur.rowcount)

    def executemany(self, sql: str, seq) -> _LockedCursor:
        with self._lock:
            cur = self._conn.executemany(sql, seq)
            return _LockedCursor([], cur.lastrowid, cur.rowcount)

    def executescript(self, sql: str):
        with self._lock:
            return self._conn.executescript(sql)

    def commit(self) -> None:
        with self._lock:
            self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()


class Database:
    """数据库仓储（连接 + 全部读写方法，线程安全）。

    user_id 约定：单默认用户 "default"，多用户 schema 保留但 UI/CLI 暂不做用户管理。
    """

    def __init__(self, db_path: Path | str):
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout = 5000")   # 与守护进程跨进程并发写时等待而非报错
        conn.execute("PRAGMA journal_mode = WAL")    # 读写不互斥，面板轮询不再被写事务卡住
        # 可重入：写方法本身已 `with self._lock`，内层 _conn.execute 还要再锁一次。
        self._lock = threading.RLock()
        self._conn = _LockedConnection(conn, self._lock)
        self._index_cache: dict | None = None        # 课程树静态索引（seed_curriculum 后失效）
        self._conn.executescript(_SCHEMA)
        self._conn.commit()
        self._migrate()

    def _migrate(self) -> None:
        """轻量迁移：CREATE TABLE IF NOT EXISTS 不会给老库加列，这里补齐。"""
        cols = {r["name"] for r in self._conn.execute("PRAGMA table_info(review_queue)")}
        if "card_json" not in cols:
            self._conn.execute("ALTER TABLE review_queue ADD COLUMN card_json TEXT")
            self._conn.commit()

        # source 列：区分手写种子与管道生成，决定谁能覆盖谁。
        # 只加列不回填是不够的——列若以错误默认值建立，老库会永远误标：
        #   kp_content 误标 generated → 种子再也更新不了它（种子只在 source=seed 时写）
        #   questions  误标 seed      → 生成题库被 content/lessons/*.json 打回原样
        # 故每次启动幂等对账一次。判据是「id 形状」——种子内容由 seed_content 写入，
        # 目前全部来自 content/lessons/*.json 导出的文件，其题 id 为 `<kp_id>-seed<i>`。
        for table in ("kp_content", "questions"):
            have = {r["name"] for r in self._conn.execute(f"PRAGMA table_info({table})")}
            if "source" not in have:
                self._conn.execute(
                    f"ALTER TABLE {table} ADD COLUMN source TEXT DEFAULT 'generated'")
                self._conn.commit()

        # required_keywords：场景题判分靠它，老库没有这一列
        qcols = {r["name"] for r in self._conn.execute("PRAGMA table_info(questions)")}
        if "required_keywords" not in qcols:
            self._conn.execute(
                "ALTER TABLE questions ADD COLUMN required_keywords TEXT DEFAULT '[]'")
            self._conn.commit()

        self._conn.execute(
            "UPDATE questions SET source='seed' WHERE id LIKE '%-seed%' AND source<>'seed'")
        self._conn.execute(
            "UPDATE questions SET source='generated' WHERE id NOT LIKE '%-seed%' AND source<>'generated'")
        self._conn.commit()

    # ---------- 工具 ----------
    def _now(self) -> str:
        return datetime.now().isoformat(timespec="seconds")

    # =====================================================================
    # 用户与课表
    # =====================================================================
    def active_users(self) -> list[User]:
        rows = self._conn.execute("SELECT * FROM users ORDER BY created_at").fetchall()
        return [User(id=r["id"], name=r["name"], level=r["level"], timezone=r["timezone"]) for r in rows]

    def get_user(self, user_id: str) -> User | None:
        r = self._conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return User(id=r["id"], name=r["name"], level=r["level"], timezone=r["timezone"]) if r else None

    def ensure_user(self, user_id: str, name: str = "学习者",
                    timezone: str = "Asia/Shanghai") -> str:
        """确保用户存在（多用户入口）。已存在则原样返回，不改名。"""
        with self._lock:
            if self.get_user(user_id) is None:
                self._conn.execute(
                    "INSERT INTO users (id, name, level, timezone) VALUES (?, ?, 'beginner', ?)",
                    (user_id, name, timezone),
                )
                self._conn.commit()
        return user_id

    def ensure_default_user(self, name: str = "学习者", timezone: str = "Asia/Shanghai") -> str:
        return self.ensure_user(DEFAULT_USER_ID, name, timezone)

    def seed_default_schedule(self, user_id: str = DEFAULT_USER_ID) -> None:
        """默认周课表：周一至周五 19:00–21:00（120 分钟，可排 3 节 × 40 分钟）。"""
        with self._lock:
            self._conn.execute("DELETE FROM schedule_slots WHERE user_id = ?", (user_id,))
            for weekday in range(5):   # 周一(0) ~ 周五(4)
                self._conn.execute(
                    "INSERT INTO schedule_slots (user_id, weekday, start_minute, duration_minutes, enabled)"
                    " VALUES (?, ?, ?, 120, 1)",
                    (user_id, weekday, 19 * 60),
                )
            self._conn.commit()

    def slots_for(self, user_id: str, weekday: int) -> list[ScheduleSlot]:
        rows = self._conn.execute(
            "SELECT * FROM schedule_slots WHERE user_id = ? AND weekday = ? AND enabled = 1 ORDER BY start_minute",
            (user_id, weekday),
        ).fetchall()
        return [
            ScheduleSlot(
                user_id=r["user_id"], weekday=r["weekday"], start_minute=r["start_minute"],
                duration_minutes=r["duration_minutes"], enabled=bool(r["enabled"]), id=r["id"],
            )
            for r in rows
        ]

    def slots_for_weekday(self, user_id: str, weekday: int) -> list[ScheduleSlot]:
        return self.slots_for(user_id, weekday)

    def schedule_slot_count(self, user_id: str) -> int:
        return self._conn.execute(
            "SELECT COUNT(*) FROM schedule_slots WHERE user_id = ?", (user_id,)
        ).fetchone()[0]

    # =====================================================================
    # 课程树（读）
    # =====================================================================
    def _index(self) -> dict:
        """课程树静态索引（课表 + kp→课 映射），惰性加载一次。

        此前 all_lessons_in_order 每节课打 2 条 SQL（kp_ids + prereqs）＝356 条，
        而一次 status() 要调它十几遍 → 单个请求 1740 条 SQL。课程结构只在
        seed_curriculum 时变，故缓存；结构变更处调 _invalidate_index()。
        """
        if self._index_cache is None:
            rows = self._conn.execute(
                """SELECT l.id, l.unit_id, u.semester_id, l.name, l.[order]
                   FROM lessons l
                   JOIN units u ON u.id = l.unit_id
                   JOIN semesters s ON s.id = u.semester_id
                   ORDER BY s.[order], u.[order], l.[order]"""
            ).fetchall()
            kp_rows = self._conn.execute(
                'SELECT id, lesson_id, prereq FROM kps ORDER BY lesson_id, "order"'
            ).fetchall()
            kps_by_lesson: dict[str, list] = {}
            kp_lesson: dict[str, str] = {}
            for k in kp_rows:
                kps_by_lesson.setdefault(k["lesson_id"], []).append(k)
                kp_lesson[k["id"]] = k["lesson_id"]
            lessons: list[Lesson] = []
            for r in rows:
                ks = kps_by_lesson.get(r["id"], [])
                prereq: list[str] = []
                if ks:
                    try:
                        prereq = json.loads(ks[0]["prereq"]) or []
                    except (ValueError, TypeError):
                        prereq = []
                lessons.append(Lesson(
                    id=r["id"], unit_id=r["unit_id"], semester_id=r["semester_id"],
                    name=r["name"] or r["id"], order=r["order"],
                    kps=[k["id"] for k in ks], prereq_kps=prereq,
                ))
            self._index_cache = {"lessons": lessons, "kp_lesson": kp_lesson}
        return self._index_cache

    def _invalidate_index(self) -> None:
        self._index_cache = None

    def all_lessons_in_order(self) -> list[Lesson]:
        return list(self._index()["lessons"])

    def kp_lesson_map(self) -> dict[str, str]:
        """kp_id → 所属课 id。kp_passed 的批量版：判定某 kp 是否通过＝它的课是否通过。"""
        return self._index()["kp_lesson"]

    def course_tree(self, user_id: str) -> list[dict]:
        """学期 → 单元 → 课 完整课程树，每课带闯关状态。

        全开放：**任何一关都可以直接学**，不再要求先通关前一关、也不要求学期齐通。
        想学什么学什么——闯关只影响「有没有打过勾」，不构成通行证。
        state 只剩两种：passed（已通过）/ unlocked（可学）。
        """
        passed = {
            r["lesson_id"] for r in self._conn.execute(
                "SELECT lesson_id FROM lesson_progress WHERE user_id = ? AND passed = 1", (user_id,)
            )
        }

        lessons_by_unit: dict[str, list[Lesson]] = {}
        for les in self.all_lessons_in_order():
            lessons_by_unit.setdefault(les.unit_id, []).append(les)

        sem_rows = self._conn.execute('SELECT id, name FROM semesters ORDER BY "order"').fetchall()
        unit_rows = self._conn.execute('SELECT id, semester_id, name FROM units ORDER BY "order"').fetchall()

        tree: list[dict] = []
        for sr in sem_rows:
            units: list[dict] = []
            total = done = 0
            for u in [row for row in unit_rows if row["semester_id"] == sr["id"]]:
                lessons = []
                for les in lessons_by_unit.get(u["id"], []):
                    state = "passed" if les.id in passed else "unlocked"
                    if state == "passed":
                        done += 1
                    total += 1
                    lessons.append({"id": les.id, "name": les.name, "state": state})
                units.append({"id": u["id"], "name": u["name"], "lessons": lessons})
            tree.append({"id": sr["id"], "name": sr["name"], "units": units,
                         "total": total, "passed": done})
        return tree

    def _lesson_prereqs(self, lesson_id: str) -> list[str]:
        """一课的门槛 = 其首个 KP 的前置（线性链：严格串行）。"""
        row = self._conn.execute(
            'SELECT prereq FROM kps WHERE lesson_id = ? ORDER BY "order" LIMIT 1', (lesson_id,)
        ).fetchone()
        if row is None:
            return []
        try:
            return json.loads(row["prereq"]) or []
        except (ValueError, TypeError):
            return []

    def lesson_kp_ids(self, lesson_id: str) -> list[str]:
        rows = self._conn.execute(
            'SELECT id FROM kps WHERE lesson_id = ? ORDER BY "order"', (lesson_id,)
        ).fetchall()
        return [r["id"] for r in rows]

    def get_lesson(self, lesson_id: str) -> Lesson | None:
        for l in self.all_lessons_in_order():
            if l.id == lesson_id:
                return l
        return None

    def lesson_kps(self, lesson_id: str) -> list[KP]:
        rows = self._conn.execute(
            'SELECT * FROM kps WHERE lesson_id = ? ORDER BY "order"', (lesson_id,)
        ).fetchall()
        return [self._row_to_kp(r) for r in rows]

    def get_kp(self, kp_id: str) -> KP | None:
        r = self._conn.execute("SELECT * FROM kps WHERE id = ?", (kp_id,)).fetchone()
        return self._row_to_kp(r) if r else None

    def all_kps_in_order(self) -> list[KP]:
        rows = self._conn.execute(
            """SELECT k.* FROM kps k
               JOIN lessons l ON l.id = k.lesson_id
               JOIN units u ON u.id = l.unit_id
               JOIN semesters s ON s.id = u.semester_id
               ORDER BY s."order", u."order", l."order", k."order\""""
        ).fetchall()
        return [self._row_to_kp(r) for r in rows]

    @staticmethod
    def _row_to_kp(r) -> KP:
        try:
            prereq = json.loads(r["prereq"]) or []
        except (ValueError, TypeError):
            prereq = []
        return KP(
            id=r["id"], lesson_id=r["lesson_id"], title=r["title"] or r["id"],
            difficulty=r["difficulty"], prereq=prereq, weight=r["weight"], order=r["order"],
        )

    def kp_count(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM kps").fetchone()[0]

    def lesson_count(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM lessons").fetchone()[0]

    # =====================================================================
    # 学习状态（BKT mastery）
    # =====================================================================
    def get_mastery(self, user_id: str, kp_id: str) -> Mastery:
        r = self._conn.execute(
            "SELECT * FROM mastery WHERE user_id = ? AND kp_id = ?", (user_id, kp_id)
        ).fetchone()
        if r is None:
            return Mastery(user_id=user_id, kp_id=kp_id)
        return Mastery(
            user_id=r["user_id"], kp_id=r["kp_id"], p_mastery=r["p_mastery"],
            attempts=r["attempts"], correct=r["correct"], last_seen=r["last_seen"],
        )

    def save_mastery(self, m: Mastery) -> None:
        with self._lock:
            self._conn.execute(
                """INSERT INTO mastery (user_id, kp_id, p_mastery, attempts, correct, last_seen)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(user_id, kp_id) DO UPDATE SET
                     p_mastery=excluded.p_mastery, attempts=excluded.attempts,
                     correct=excluded.correct, last_seen=excluded.last_seen""",
                (m.user_id, m.kp_id, m.p_mastery, m.attempts, m.correct, self._now()),
            )
            self._conn.commit()

    def kp_passed(self, user_id: str, kp_id: str) -> bool:
        """KP「通过」= 它所属那节课的测验已通过（对应原始规格的「单元考试 ≥75%」）。

        掌握度 p_mastery 不参与硬门禁，只驱动 FSRS 复习队列与补强（见 pending_remedial）。
        """
        kp = self.get_kp(kp_id)
        return bool(kp and self.lesson_passed(user_id, kp.lesson_id))

    def get_lesson_progress(self, user_id: str, lesson_id: str) -> dict | None:
        r = self._conn.execute(
            "SELECT * FROM lesson_progress WHERE user_id = ? AND lesson_id = ?",
            (user_id, lesson_id),
        ).fetchone()
        return dict(r) if r else None

    def record_lesson_score(self, user_id: str, lesson_id: str, score: float) -> dict:
        """记录打 Boss 成绩。达到 Boss 线（85%）即通关该关并解锁下一关，
        通关后保持通关（补强/复述不影响已解锁的进度）。"""
        prev = self.get_lesson_progress(user_id, lesson_id)
        attempts = (prev["attempts"] if prev else 0) + 1
        passed = 1 if (score >= BOSS_PASS or (prev and prev["passed"])) else 0
        with self._lock:
            self._conn.execute(
                """INSERT INTO lesson_progress (user_id, lesson_id, quiz_score, attempts, passed, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(user_id, lesson_id) DO UPDATE SET
                     quiz_score=excluded.quiz_score, attempts=excluded.attempts,
                     passed=excluded.passed, updated_at=excluded.updated_at""",
                (user_id, lesson_id, score, attempts, passed, self._now()),
            )
            self._conn.commit()
        return {"quiz_score": score, "attempts": attempts, "passed": bool(passed)}

    def lesson_passed(self, user_id: str, lesson_id: str) -> bool:
        p = self.get_lesson_progress(user_id, lesson_id)
        return bool(p and p["passed"])

    # ---------- 卷子（打 Boss） ----------
    def get_paper(self, user_id: str, lesson_id: str) -> list[str] | None:
        """当前卷子的题号（有序）。没有卷子返回 None。"""
        r = self._conn.execute(
            "SELECT question_ids FROM quiz_papers WHERE user_id = ? AND lesson_id = ?",
            (user_id, lesson_id),
        ).fetchone()
        if not r:
            return None
        try:
            ids = json.loads(r["question_ids"]) or []
        except (ValueError, TypeError):
            return None
        return ids or None

    def save_paper(self, user_id: str, lesson_id: str, question_ids: list[str]) -> None:
        with self._lock:
            self._conn.execute(
                """INSERT INTO quiz_papers (user_id, lesson_id, question_ids, created_at)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(user_id, lesson_id) DO UPDATE SET
                     question_ids=excluded.question_ids, created_at=excluded.created_at""",
                (user_id, lesson_id, json.dumps(question_ids, ensure_ascii=False), self._now()),
            )
            self._conn.commit()

    def clear_paper(self, user_id: str, lesson_id: str) -> None:
        """只作废当前卷子，**保留消费账**。

        消费账记着「哪些题打过了」，是重做换新题的依据；清掉它等于让题池回到起点，
        重做就会再抽到打过的题（与「题库用完才允许重复」相反）。
        题池真用完时，抽题端会退化为从全池抽，天然允许循环复用，不需要在这里清账。
        """
        with self._lock:
            self._conn.execute(
                "DELETE FROM quiz_papers WHERE user_id = ? AND lesson_id = ?", (user_id, lesson_id))
            self._conn.commit()

    def unused_question_ids(self, user_id: str, lesson_id: str) -> set[str]:
        """本课还没被打过的题号。"""
        rows = self._conn.execute(
            "SELECT question_id FROM quiz_history WHERE user_id = ? AND lesson_id = ?",
            (user_id, lesson_id),
        ).fetchall()
        return {r["question_id"] for r in rows}

    def record_question_used(self, user_id: str, lesson_id: str, question_ids: list[str]) -> None:
        with self._lock:
            self._conn.executemany(
                """INSERT INTO quiz_history (user_id, lesson_id, question_id, used_at)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(user_id, lesson_id, question_id) DO UPDATE SET used_at=excluded.used_at""",
                [(user_id, lesson_id, qid, self._now()) for qid in question_ids],
            )
            self._conn.commit()

    def passed_lesson_ids(self, user_id: str) -> set[str]:
        """一次取全已通过的课。门禁/闯关/排课都要逐课判定，热路径必须走这个批量版，
        否则每课一次查询（178 课 → 178 条 SQL，而 status() 每秒被调一次）。"""
        return {r["lesson_id"] for r in self._conn.execute(
            "SELECT lesson_id FROM lesson_progress WHERE user_id = ? AND passed = 1",
            (user_id,))}

    # =====================================================================
    # 章节考 / 学期考（学校式层级门禁）
    # =====================================================================
    def unit_lesson_ids(self, unit_id: str) -> list[str]:
        rows = self._conn.execute(
            'SELECT id FROM lessons WHERE unit_id = ? ORDER BY "order"', (unit_id,)
        ).fetchall()
        return [r["id"] for r in rows]

    def semester_unit_ids(self, semester_id: str) -> list[str]:
        rows = self._conn.execute(
            'SELECT id FROM units WHERE semester_id = ? ORDER BY "order"', (semester_id,)
        ).fetchall()
        return [r["id"] for r in rows]

    def scope_lesson_ids(self, scope: str, scope_id: str) -> list[str]:
        """考试范围包含的课 id 列表。scope=unit → 该单元的课；semester → 该学期所有单元的课。"""
        if scope == "unit":
            return self.unit_lesson_ids(scope_id)
        if scope == "semester":
            out: list[str] = []
            for uid in self.semester_unit_ids(scope_id):
                out.extend(self.unit_lesson_ids(uid))
            return out
        raise ValueError(f"未知考试范围：{scope}")

    def get_exam_result(self, user_id: str, scope: str, scope_id: str) -> dict | None:
        r = self._conn.execute(
            "SELECT * FROM exam_results WHERE user_id = ? AND scope = ? AND scope_id = ?",
            (user_id, scope, scope_id),
        ).fetchone()
        return dict(r) if r else None

    def record_exam_score(self, user_id: str, scope: str, scope_id: str, score: float) -> dict:
        """记录章节考（≥70%）/ 学期考（≥75%）。通过后粘滞，重考不倒退。"""
        threshold = CHAPTER_PASS if scope == "unit" else SEMESTER_PASS
        prev = self.get_exam_result(user_id, scope, scope_id)
        attempts = (prev["attempts"] if prev else 0) + 1
        passed = 1 if (score >= threshold or (prev and prev["passed"])) else 0
        with self._lock:
            self._conn.execute(
                """INSERT INTO exam_results (user_id, scope, scope_id, score, attempts, passed, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(user_id, scope, scope_id) DO UPDATE SET
                     score=excluded.score, attempts=excluded.attempts,
                     passed=excluded.passed, updated_at=excluded.updated_at""",
                (user_id, scope, scope_id, score, attempts, passed, self._now()),
            )
            self._conn.commit()
        return {"score": score, "attempts": attempts, "passed": bool(passed),
                "threshold": threshold}

    def exam_passed(self, user_id: str, scope: str, scope_id: str) -> bool:
        r = self.get_exam_result(user_id, scope, scope_id)
        return bool(r and r["passed"])

    def exam_status(self, user_id: str, scope: str, scope_id: str) -> dict:
        """某场考试是否「可考」：范围内的课必须先全部通过（考完才能考期末）。"""
        lessons = self.scope_lesson_ids(scope, scope_id)
        passed_ids = self.passed_lesson_ids(user_id)
        done = [l for l in lessons if l in passed_ids]
        r = self.get_exam_result(user_id, scope, scope_id)
        threshold = CHAPTER_PASS if scope == "unit" else SEMESTER_PASS
        return {
            "scope": scope,
            "scope_id": scope_id,
            "threshold": threshold,
            "lessons": len(lessons),
            "lessons_passed": len(done),
            "ready": len(lessons) > 0 and len(done) == len(lessons),
            "passed": bool(r and r["passed"]),
            "score": r["score"] if r else None,
            "attempts": r["attempts"] if r else 0,
        }

    def pending_remedial(self, user_id: str) -> KP | None:
        """返回第一个已接触但未掌握（attempts>0 且 p_mastery<知识点线 80%）的 KP，用于补强。

        单条 JOIN 取代「遍历 385 个 KP 各查一次 mastery」——它在 status() 里每秒被调一次。
        排序与 all_kps_in_order 一致，保证「第一个」的课程顺序语义不变。
        """
        r = self._conn.execute(
            """SELECT k.* FROM mastery m
               JOIN kps k ON k.id = m.kp_id
               JOIN lessons l ON l.id = k.lesson_id
               JOIN units u ON u.id = l.unit_id
               JOIN semesters s ON s.id = u.semester_id
               WHERE m.user_id = ? AND m.attempts > 0 AND m.p_mastery < ?
               ORDER BY s."order", u."order", l."order", k."order" LIMIT 1""",
            (user_id, KP_PASS),
        ).fetchone()
        return self._row_to_kp(r) if r else None

    # =====================================================================
    # 复习队列（FSRS）
    # =====================================================================
    def get_review_card(self, user_id: str, kp_id: str) -> ReviewCard | None:
        r = self._conn.execute(
            "SELECT * FROM review_queue WHERE user_id = ? AND kp_id = ?", (user_id, kp_id)
        ).fetchone()
        if r is None:
            return None
        # 优先用全量 fsrs Card JSON 无损重建；老行（迁移前）无此列则回落为 None（视作新卡）
        card = json.loads(r["card_json"]) if r["card_json"] else None
        return ReviewCard(user_id=r["user_id"], kp_id=r["kp_id"], due_at=r["due_at"], card=card)

    def save_review_card(self, user_id: str, kp_id: str, card: dict, due_at) -> None:
        with self._lock:
            due = due_at.isoformat(timespec="seconds") if hasattr(due_at, "isoformat") else str(due_at)
            self._conn.execute(
                """INSERT INTO review_queue (user_id, kp_id, due_at, stability, difficulty, reps, lapses, last_review, card_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(user_id, kp_id) DO UPDATE SET
                     due_at=excluded.due_at, stability=excluded.stability,
                     difficulty=excluded.difficulty, reps=excluded.reps,
                     lapses=excluded.lapses, last_review=excluded.last_review,
                     card_json=excluded.card_json""",
                (
                    user_id, kp_id, due,
                    card.get("stability", 1.0), card.get("difficulty", 5.0),
                    card.get("reps", 0), card.get("lapses", 0), self._now(),
                    json.dumps(card, ensure_ascii=False, default=str),
                ),
            )
            self._conn.commit()

    def due_reviews(self, user_id: str, now) -> list[dict]:
        # 接受 datetime 或 date：date 视为当日 23:59:59（当日到期全含）
        if isinstance(now, datetime):
            ref = now.isoformat(timespec="seconds")
        else:
            ref = f"{now.isoformat()}T23:59:59"
        rows = self._conn.execute(
            "SELECT * FROM review_queue WHERE user_id = ? AND due_at <= ? ORDER BY due_at",
            (user_id, ref),
        ).fetchall()
        return [dict(r) for r in rows]

    def review_items(self, user_id: str, now, limit: int = 200) -> list[dict]:
        """到期复习清单（带知识点标题与所属课），供界面直接渲染。

        due_reviews 只回 review_queue 的裸行，界面上没有 kp 标题就只是一串
        `py.env.pip` 裸 id；这里 JOIN 出标题和课号，一次查询够用。
        """
        ref = (now.isoformat(timespec="seconds") if isinstance(now, datetime)
               else f"{now.isoformat()}T23:59:59")
        rows = self._conn.execute(
            """SELECT r.kp_id, r.due_at, r.reps, r.lapses,
                      k.title AS kp_title, k.lesson_id, l.name AS lesson_name
               FROM review_queue r
               JOIN kps k ON k.id = r.kp_id
               JOIN lessons l ON l.id = k.lesson_id
               WHERE r.user_id = ? AND r.due_at <= ?
               ORDER BY r.due_at LIMIT ?""",
            (user_id, ref, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def due_review_count(self, user_id: str, now) -> int:
        """到期复习总数（不受 review_items 的 limit 影响，界面要显示真数）。"""
        ref = (now.isoformat(timespec="seconds") if isinstance(now, datetime)
               else f"{now.isoformat()}T23:59:59")
        r = self._conn.execute(
            "SELECT COUNT(*) AS n FROM review_queue WHERE user_id = ? AND due_at <= ?",
            (user_id, ref),
        ).fetchone()
        return int(r["n"]) if r else 0

    # =====================================================================
    # 错题 / 补强
    # =====================================================================
    def error_items(self, user_id: str, limit: int = 200) -> list[dict]:
        """错题本：error_log 一直是只写不读（67 条记录、零个入口）。

        按时间倒序，JOIN 出知识点标题、课号与原题题干；题干可能已被清空（题库重建），
        所以用 LEFT JOIN，宁可显示空题干也不能整行消失。
        """
        rows = self._conn.execute(
            """SELECT e.kp_id, e.question_id, e.user_answer, e.error_type, e.at,
                      k.title AS kp_title, k.lesson_id, q.stem, q.type
               FROM error_log e
               LEFT JOIN kps k ON k.id = e.kp_id
               LEFT JOIN questions q ON q.id = e.question_id
               WHERE e.user_id = ?
               ORDER BY e.id DESC LIMIT ?""",
            (user_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def error_count(self, user_id: str) -> int:
        """错题总数（不受 error_items 的 limit 影响）。"""
        r = self._conn.execute(
            "SELECT COUNT(*) AS n FROM error_log WHERE user_id = ?", (user_id,)
        ).fetchone()
        return int(r["n"]) if r else 0

    def exam_results(self, user_id: str) -> list[dict]:
        """全部考试记录（原先只能按 scope 单查一条，界面上拿不到「考过哪些」）。"""
        rows = self._conn.execute(
            """SELECT e.scope, e.scope_id, e.score, e.attempts, e.passed, e.updated_at,
                      COALESCE(u.name, s.name) AS name
               FROM exam_results e
               LEFT JOIN units u ON e.scope = 'unit' AND u.id = e.scope_id
               LEFT JOIN semesters s ON e.scope = 'semester' AND s.id = e.scope_id
               WHERE e.user_id = ?
               ORDER BY e.updated_at DESC""",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def record_error(self, user_id: str, kp_id: str, question_id: str | None,
                     user_answer: str, error_type: str) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO error_log (user_id, kp_id, question_id, user_answer, error_type) VALUES (?, ?, ?, ?, ?)",
                (user_id, kp_id, question_id, user_answer, error_type),
            )
            self._conn.commit()

    def append_to_warmup(self, user_id: str, items: list) -> None:
        with self._lock:
            for it in items:
                kp_id = it if isinstance(it, str) else it.get("kp_id", "")
                note = "" if isinstance(it, str) else it.get("note", "")
                self._conn.execute(
                    "INSERT INTO warmup_items (user_id, kp_id, note) VALUES (?, ?, ?)",
                    (user_id, kp_id, note),
                )
            self._conn.commit()

    def pop_warmup(self, user_id: str) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM warmup_items WHERE user_id = ? ORDER BY id", (user_id,)
            ).fetchall()
            items = [dict(r) for r in rows]
            self._conn.execute("DELETE FROM warmup_items WHERE user_id = ?", (user_id,))
            self._conn.commit()
        return items

    # =====================================================================
    # 知识点内容（kp_content）+ 题库
    # =====================================================================
    def get_kp_content(self, kp_id: str) -> KPContent | None:
        r = self._conn.execute("SELECT * FROM kp_content WHERE kp_id = ?", (kp_id,)).fetchone()
        if r is None:
            return None
        try:
            sources = json.loads(r["sources"]) or []
        except (ValueError, TypeError):
            sources = []
        return KPContent(
            kp_id=r["kp_id"], explain=r["explain"], example_code=r["example_code"],
            pitfalls=r["pitfalls"], sources=sources, version=r["version"],
            verified=bool(r["verified"]),
        )

    def save_kp_content(self, kp_id: str, explain: str = "", example_code: str = "",
                        pitfalls: str = "", sources: list | None = None, verified: bool = False,
                        source: str = "generated") -> None:
        """source: 'generated'（update 管道/模型生成）或 'seed'（content/lessons 手写种子）。

        种子只补空缺、不覆盖 generated —— 否则每次启动都会把烧 token 生成的内容打回原样。
        """
        with self._lock:
            sources_json = json.dumps(sources or [], ensure_ascii=False)
            self._conn.execute(
                """INSERT INTO kp_content (kp_id, explain, example_code, pitfalls, sources, version, generated_at, verified, source)
                   VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?)
                   ON CONFLICT(kp_id) DO UPDATE SET
                     explain=excluded.explain, example_code=excluded.example_code,
                     pitfalls=excluded.pitfalls, sources=excluded.sources,
                     version=kp_content.version + 1, generated_at=excluded.generated_at,
                     verified=excluded.verified, source=excluded.source""",
                (kp_id, explain, example_code, pitfalls, sources_json, self._now(),
                 1 if verified else 0, source),
            )
            self._conn.commit()

    def kp_content_source(self, kp_id: str) -> str | None:
        """该 KP 讲义来源：'generated' / 'seed' / None（无内容）。"""
        row = self._conn.execute(
            "SELECT source FROM kp_content WHERE kp_id = ?", (kp_id,)
        ).fetchone()
        return row["source"] if row else None

    def kp_quiz_source(self, kp_id: str) -> str | None:
        """该 KP 题库来源：全部题都来自种子则 'seed'，否则视为 'generated'（含混合）。"""
        rows = self._conn.execute(
            "SELECT source FROM questions WHERE kp_id = ?", (kp_id,)
        ).fetchall()
        if not rows:
            return None
        return "seed" if all((r["source"] or "seed") == "seed" for r in rows) else "generated"

    def save_questions(self, kp_id: str, questions: list, source: str = "generated") -> int:
        with self._lock:
            self._conn.execute("DELETE FROM questions WHERE kp_id = ?", (kp_id,))
            n = 0
            for q in questions:
                qid = q.get("id") or f"{kp_id}-q{n}"
                self._conn.execute(
                    """INSERT INTO questions (id, kp_id, type, difficulty, stem, options, answer,
                                              explanation, error_tag, source_ref, variant_group,
                                              required_keywords, source)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        qid, kp_id, q.get("type", "single_choice"), q.get("difficulty", 1),
                        q.get("stem", ""), json.dumps(q.get("options", []), ensure_ascii=False),
                        json.dumps(q.get("answer"), ensure_ascii=False), q.get("explanation", ""),
                        q.get("error_tag"), q.get("source_ref"), q.get("variant_group"),
                        json.dumps(q.get("required_keywords", []), ensure_ascii=False),
                        q.get("source") or source,
                    ),
                )
                n += 1
            self._conn.commit()
        return n

    def questions_for(self, kp_id: str) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM questions WHERE kp_id = ? ORDER BY id", (kp_id,)
        ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            for key in ("options", "answer", "required_keywords"):
                try:
                    d[key] = json.loads(d[key] or "[]")
                except (ValueError, TypeError):
                    d[key] = []
            out.append(d)
        return out

    def questions_by_ids(self, question_ids: list[str]) -> list[dict]:
        """按给定题号取题，**保持传入顺序**（卷子顺序即判分顺序）。"""
        if not question_ids:
            return []
        marks = ",".join("?" * len(question_ids))
        rows = self._conn.execute(
            f"SELECT * FROM questions WHERE id IN ({marks})", tuple(question_ids)
        ).fetchall()
        by_id = {}
        for r in rows:
            d = dict(r)
            for key in ("options", "answer", "required_keywords"):
                try:
                    d[key] = json.loads(d[key] or "[]")
                except (ValueError, TypeError):
                    d[key] = []
            by_id[d["id"]] = d
        return [by_id[qid] for qid in question_ids if qid in by_id]

    # =====================================================================
    # 更新管道辅助
    # =====================================================================
    def has_changed(self, chunk: dict) -> bool:
        """chunk = {"url", "hash"}；URL 已存在且 hash 相同 → 未变。"""
        url, h = chunk.get("url"), chunk.get("hash")
        if not url:
            return True
        rows = self._conn.execute("SELECT kp_id, sources FROM kp_content WHERE sources != '[]'").fetchall()
        for r in rows:
            try:
                sources = json.loads(r["sources"]) or []
            except (ValueError, TypeError):
                continue
            for s in sources:
                if s.get("url") == url:
                    return s.get("hash") != h
        return True

    def save_kp(self, kp: dict, questions: list, source: str | None = None, version: int = 1) -> None:
        sources = kp.get("sources") or []
        if source and not any(s.get("url") == source for s in sources):
            sources.append({"url": source, "hash": "", "fetched_at": self._now()})
        self.save_kp_content(
            kp_id=kp["id"], explain=kp.get("explain", ""), example_code=kp.get("example_code", ""),
            pitfalls=kp.get("pitfalls", ""), sources=sources, verified=kp.get("verified", False),
        )
        self.save_questions(kp["id"], questions, source="generated")

    def update_kp_content(self, kp_id: str, updated: dict) -> None:
        self.save_kp_content(
            kp_id=kp_id, explain=updated.get("explain", ""),
            example_code=updated.get("example_code", ""), pitfalls=updated.get("pitfalls", ""),
            sources=updated.get("sources"), verified=updated.get("verified", False),
        )

    def find_stale_kps(self, max_age_days: int = 90) -> list[dict]:
        cutoff = datetime.now().isoformat(timespec="seconds")
        rows = self._conn.execute(
            "SELECT kp_id, generated_at FROM kp_content WHERE generated_at IS NOT NULL"
        ).fetchall()
        # generated_at 存 ISO 字符串；简单按字典序比较（ISO 序 == 时间序）
        stale = []
        for r in rows:
            try:
                gen = datetime.fromisoformat(r["generated_at"])
            except (ValueError, TypeError):
                continue
            if (datetime.now() - gen).days > max_age_days:
                stale.append(dict(r))
        return stale

    def find_unfilled_kps(self, limit: int = 5) -> list[dict]:
        """还没有讲义的 KP（按课程顺序），是 update 管道的真实生成队列。

        「没有」包含两种：kp_content 行不存在，或行在但短于 MIN_LECTURE_CHARS
        （手写种子留下的几十字占位）。后者若也算「已填充」，那几个 KP 就永远停在
        一页纸的占位文上，而题库照常按完整知识点生成——学生看到的正是这一幕。

        附带 prereq（前置知识点 id 列表），供生成 prompt 填入 `prerequisites`。
        """
        rows = self._conn.execute(
            """SELECT k.id AS kp_id, k.title, k.prereq, l.id AS lesson_id, l.name AS lesson_name
               FROM kps k
               JOIN lessons l ON l.id = k.lesson_id
               LEFT JOIN kp_content kc ON kc.kp_id = k.id
               WHERE kc.kp_id IS NULL OR length(COALESCE(kc.explain, '')) < ?
               ORDER BY k."order"
               LIMIT ?""",
            (MIN_LECTURE_CHARS, limit),
        ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            try:
                d["prereq"] = json.loads(d.get("prereq") or "[]")
            except (ValueError, TypeError):
                d["prereq"] = []
            out.append(d)
        return out

    def find_thin_quiz_kps(self, min_questions: int = 6, limit: int = 5) -> list[dict]:
        """已有讲义但题库过薄的 KP（按课程顺序）——补题队列。

        手写种子内容每个 KP 只有 1 道题，撑不住 10 分钟的测验阶段；
        生成内容每 KP 20 道。这里找出题量不足 min_questions 的。
        """
        rows = self._conn.execute(
            """SELECT k.id AS kp_id, k.title, k.prereq, l.id AS lesson_id, l.name AS lesson_name,
                      kc.explain
               FROM kps k
               JOIN lessons l ON l.id = k.lesson_id
               JOIN kp_content kc ON kc.kp_id = k.id
               LEFT JOIN (SELECT kp_id, COUNT(*) AS n FROM questions GROUP BY kp_id) q
                      ON q.kp_id = k.id
               WHERE COALESCE(q.n, 0) < ?
               ORDER BY k."order"
               LIMIT ?""",
            (min_questions, limit),
        ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            try:
                d["prereq"] = json.loads(d.get("prereq") or "[]")
            except (ValueError, TypeError):
                d["prereq"] = []
            out.append(d)
        return out

    def covered_summary(self) -> dict:
        total = self.kp_count()
        with_content = self._conn.execute("SELECT COUNT(*) FROM kp_content").fetchone()[0]
        sem_rows = self._conn.execute(
            """SELECT s.id, COUNT(k.id) AS kps, COUNT(kc.kp_id) AS filled
               FROM semesters s
               JOIN units u ON u.semester_id = s.id
               JOIN lessons l ON l.unit_id = u.id
               JOIN kps k ON k.lesson_id = l.id
               LEFT JOIN kp_content kc ON kc.kp_id = k.id
               GROUP BY s.id ORDER BY s."order\""""
        ).fetchall()
        return {
            "total_kps": total,
            "with_content": with_content,
            "semesters": {r["id"]: {"kps": r["kps"], "filled": r["filled"]} for r in sem_rows},
        }

    def month_tokens(self) -> int:
        """本月已烧 token，预算判断用。"""
        month = datetime.now().strftime("%Y-%m")
        return self._conn.execute(
            "SELECT COALESCE(SUM(tokens_used), 0) FROM updates_log WHERE substr(ended_at, 1, 7) = ?",
            (month,),
        ).fetchone()[0]

    def save_audit(self, audit) -> None:
        with self._lock:
            summary = json.dumps(audit, ensure_ascii=False) if not isinstance(audit, str) else audit
            self._conn.execute("INSERT INTO audit_log (summary) VALUES (?)", (summary,))
            self._conn.commit()

    def log_update(self, kind: str, started_at, ended_at, tokens_used: int,
                   kps_added: int, kps_updated: int, status: str = "ok") -> None:
        with self._lock:
            self._conn.execute(
                """INSERT INTO updates_log (kind, started_at, ended_at, tokens_used, kps_added, kps_updated, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    kind,
                    started_at.isoformat(timespec="seconds") if hasattr(started_at, "isoformat") else str(started_at),
                    ended_at.isoformat(timespec="seconds") if hasattr(ended_at, "isoformat") else str(ended_at),
                    tokens_used, kps_added, kps_updated, status,
                ),
            )
            self._conn.commit()

    def token_spend(self) -> dict:
        """累计计费概览：更新次数 / 总 token / 新增与更新 KP 数 / 最近一次更新。

        另含本月用量，供预算上限与告警使用（month_tokens / month_runs）。
        """
        row = self._conn.execute(
            """SELECT COUNT(*) AS runs, COALESCE(SUM(tokens_used), 0) AS tokens,
                      COALESCE(SUM(kps_added), 0) AS kps_added,
                      COALESCE(SUM(kps_updated), 0) AS kps_updated
               FROM updates_log"""
        ).fetchone()
        out = dict(row)
        month = datetime.now().strftime("%Y-%m")
        mrow = self._conn.execute(
            """SELECT COUNT(*) AS runs, COALESCE(SUM(tokens_used), 0) AS tokens
               FROM updates_log WHERE substr(ended_at, 1, 7) = ?""",
            (month,),
        ).fetchone()
        out["month"] = month
        out["month_tokens"] = mrow["tokens"]
        out["month_runs"] = mrow["runs"]
        last = self._conn.execute(
            "SELECT kind, ended_at, status, tokens_used FROM updates_log ORDER BY id DESC LIMIT 1"
        ).fetchone()
        out["last"] = dict(last) if last else None
        return out

    # =====================================================================
    # 通知收件箱
    # =====================================================================
    def add_notification(self, user_id: str, kind: str, message: str) -> int:
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO notifications (user_id, kind, message) VALUES (?, ?, ?)",
                (user_id, kind, message),
            )
            self._conn.commit()
            return cur.lastrowid

    def notifications(self, user_id: str = DEFAULT_USER_ID, limit: int = 20) -> list[dict]:
        rows = self._conn.execute(
            "SELECT id, kind, message, created_at, read_at FROM notifications"
            " WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def unread_count(self, user_id: str = DEFAULT_USER_ID) -> int:
        r = self._conn.execute(
            "SELECT COUNT(*) AS n FROM notifications WHERE user_id = ? AND read_at IS NULL",
            (user_id,),
        ).fetchone()
        return r["n"]

    def mark_notifications_read(self, user_id: str = DEFAULT_USER_ID) -> int:
        with self._lock:
            cur = self._conn.execute(
                "UPDATE notifications SET read_at = ? WHERE user_id = ? AND read_at IS NULL",
                (self._now(), user_id),
            )
            self._conn.commit()
            return cur.rowcount

    # =====================================================================
    # 学习会话
    # =====================================================================
    def start_session(self, user_id: str, lesson_id: str, plan_date: str, stage: str,
                      state_json: str = "") -> str:
        with self._lock:
            sid = uuid.uuid4().hex
            self._conn.execute(
                """INSERT INTO sessions (id, user_id, lesson_id, plan_date, stage, state_json, started_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (sid, user_id, lesson_id, plan_date, stage, state_json, self._now()),
            )
            self._conn.commit()
            return sid

    def finalize_session(self, session_id: str) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE sessions SET ended_at = ? WHERE id = ?", (self._now(), session_id)
            )
            self._conn.commit()

    def get_session(self, session_id: str) -> dict | None:
        r = self._conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        return dict(r) if r else None

    def get_active_session(self, user_id: str) -> dict | None:
        r = self._conn.execute(
            "SELECT * FROM sessions WHERE user_id = ? AND ended_at IS NULL ORDER BY started_at DESC LIMIT 1",
            (user_id,),
        ).fetchone()
        return dict(r) if r else None

    def update_session_state(self, session_id: str, state_json: str) -> None:
        """覆盖会话状态（Boss 战况逐回合存这里，刷新页面不丢）。"""
        with self._lock:
            self._conn.execute(
                "UPDATE sessions SET state_json = ? WHERE id = ?", (state_json, session_id))
            self._conn.commit()

    # =====================================================================
    # 每日排课
    # =====================================================================
    def get_day_plan(self, user_id: str, plan_date: str) -> DayPlan | None:
        r = self._conn.execute(
            "SELECT * FROM day_plans WHERE user_id = ? AND plan_date = ?", (user_id, plan_date)
        ).fetchone()
        if r is None:
            return None
        try:
            lessons = json.loads(r["lessons"]) or []
        except (ValueError, TypeError):
            lessons = []
        return DayPlan(user_id=r["user_id"], plan_date=r["plan_date"], lessons=lessons)

    def save_day_plan(self, user_id: str, plan_date: str, lessons: list) -> None:
        with self._lock:
            self._conn.execute(
                """INSERT INTO day_plans (user_id, plan_date, lessons, generated_at)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(user_id, plan_date) DO UPDATE SET
                     lessons=excluded.lessons, generated_at=excluded.generated_at""",
                (user_id, plan_date, json.dumps(lessons, ensure_ascii=False), self._now()),
            )
            self._conn.commit()

    # =====================================================================
    # 种子 / 重置
    # =====================================================================
    def seed_curriculum(self, curriculum) -> dict:
        """把课程树种入 DB（semesters→units→lessons→kps）。

        curriculum 需提供 .semesters（每个 .id/.name/.units；unit .id/.name/.lessons；
        lesson .id/.kps）。KP 前置按全局顺序链成线性 DAG（严格串行，不允许跳跃）。
        """
        with self._lock:
            self._conn.executescript(
                "DELETE FROM kps; DELETE FROM lessons; DELETE FROM units; DELETE FROM semesters;"
            )
            # 学期门禁（学校模式）：学期 N 的首个 KP 前置 = 学期 N-1 的全部 KP；
            # 学期内各课按顺序排、不做逐课门禁，故一天可排多节连续新课。
            sem_ids = [sem.id for sem in curriculum.semesters]
            sem_kp_ids: dict[str, list[str]] = {}
            for sem in curriculum.semesters:
                ids: list[str] = []
                for unit in sem.units:
                    for lesson in unit.lessons:
                        ids.extend(lesson.kps)
                sem_kp_ids[sem.id] = ids

            sem_count = unit_count = lesson_count = kp_count = 0
            for si, sem in enumerate(curriculum.semesters):
                gate_prereq = sem_kp_ids[sem_ids[si - 1]] if si > 0 else []
                self._conn.execute(
                    "INSERT INTO semesters (id, name, \"order\") VALUES (?, ?, ?)",
                    (sem.id, sem.name, si),
                )
                sem_count += 1
                first_kp = True
                for ui, unit in enumerate(sem.units):
                    self._conn.execute(
                        "INSERT INTO units (id, semester_id, name, \"order\") VALUES (?, ?, ?, ?)",
                        (unit.id, sem.id, unit.name, ui),
                    )
                    unit_count += 1
                    for li, lesson in enumerate(unit.lessons):
                        self._conn.execute(
                            "INSERT INTO lessons (id, unit_id, name, \"order\") VALUES (?, ?, ?, ?)",
                            (lesson.id, unit.id, lesson.id, li),
                        )
                        lesson_count += 1
                        for ki, kp_id in enumerate(lesson.kps):
                            prereq = gate_prereq if first_kp else []
                            self._conn.execute(
                                "INSERT INTO kps (id, lesson_id, title, difficulty, prereq, weight, \"order\")"
                                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                                (kp_id, lesson.id, kp_id, self._difficulty(sem.id), json.dumps(prereq), 3, ki),
                            )
                            kp_count += 1
                            first_kp = False
            self._conn.commit()
        self._invalidate_index()
        # 课程树重建后 lessons.name / kps.title 又变回裸 id，让 derive 的回填重跑一遍
        self._conn.execute("PRAGMA user_version = 0")
        self._conn.commit()
        return {
            "semesters": sem_count, "units": unit_count,
            "lessons": lesson_count, "kps": kp_count,
        }

    @staticmethod
    def _difficulty(semester_id: str) -> int:
        try:
            return max(1, min(5, int(semester_id[1:])))
        except (ValueError, IndexError):
            return 1

    def reset_progress(self, user_id: str = DEFAULT_USER_ID) -> None:
        with self._lock:
            self._conn.executescript(
                "DELETE FROM mastery; DELETE FROM review_queue; DELETE FROM error_log;"
                "DELETE FROM lesson_progress; DELETE FROM exam_results;"
                "DELETE FROM warmup_items;"
                "DELETE FROM sessions; DELETE FROM day_plans;"
            )
            self._conn.commit()

    def reset(self) -> None:
        """清空全部数据（含课程树与内容），仅保留 schema。"""
        with self._lock:
            self._conn.executescript(
                "DELETE FROM mastery; DELETE FROM review_queue; DELETE FROM error_log;"
                "DELETE FROM lesson_progress; DELETE FROM exam_results;"
                "DELETE FROM warmup_items;"
                "DELETE FROM sessions; DELETE FROM day_plans;"
                "DELETE FROM kp_content; DELETE FROM questions;"
                "DELETE FROM kps; DELETE FROM lessons; DELETE FROM units; DELETE FROM semesters;"
                "DELETE FROM updates_log; DELETE FROM audit_log;"
            )
            self._conn.commit()

    def close(self) -> None:
        self._conn.close()
