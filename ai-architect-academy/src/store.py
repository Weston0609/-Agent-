"""进度持久化 —— 纯标准库 sqlite3。

表：
- lesson_progress: 每节课的完成状态、测验得分
- exam_progress:   单元考 / 期末考 得分
- sessions:        学习会话记录（用于排课与时间精度）
"""
from __future__ import annotations

import sqlite3
import threading
from datetime import datetime
from pathlib import Path


class Store:
    def __init__(self, db_path: Path | str):
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        # check_same_thread=False：Web 面板用 ThreadingHTTPServer，多线程共享一个连接。
        # 安全依据：sqlite3.threadsafety == 3（serialized 模式），底层 C 库自行串行化。
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()  # 写操作串行，避免并发写交错
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS lesson_progress (
                lesson_id  TEXT PRIMARY KEY,
                status     TEXT NOT NULL DEFAULT 'locked',  -- locked | unlocked | in_progress | passed
                quiz_score REAL,
                attempts   INTEGER NOT NULL DEFAULT 0,
                completed_at TEXT
            );
            CREATE TABLE IF NOT EXISTS exam_progress (
                exam_id    TEXT PRIMARY KEY,   -- 例: s1u1 (单元考) / s1-final (期末考)
                kind       TEXT NOT NULL,      -- unit | final
                score      REAL,
                attempts   INTEGER NOT NULL DEFAULT 0,
                passed     INTEGER NOT NULL DEFAULT 0,
                taken_at   TEXT
            );
            CREATE TABLE IF NOT EXISTS sessions (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                lesson_id  TEXT NOT NULL,
                started_at TEXT NOT NULL,
                ended_at   TEXT,
                minutes    INTEGER
            );
            """
        )
        self._conn.commit()

    # ---------- 课时 ----------
    def get_lesson(self, lesson_id: str) -> dict | None:
        row = self._conn.execute(
            "SELECT * FROM lesson_progress WHERE lesson_id = ?", (lesson_id,)
        ).fetchone()
        return dict(row) if row else None

    def get_all_lessons(self) -> dict[str, dict]:
        rows = self._conn.execute("SELECT * FROM lesson_progress").fetchall()
        return {r["lesson_id"]: dict(r) for r in rows}

    def mark_lesson(self, lesson_id: str, status: str, quiz_score: float | None = None) -> None:
        with self._lock:
            now = datetime.now().isoformat(timespec="seconds")
            cur = self.get_lesson(lesson_id)
            if cur is None:
                self._conn.execute(
                    """INSERT INTO lesson_progress (lesson_id, status, quiz_score, attempts, completed_at)
                       VALUES (?, ?, ?, ?, ?)""",
                    (lesson_id, status, quiz_score, 1 if status == "passed" else 0,
                     now if status == "passed" else None),
                )
            else:
                attempts = cur["attempts"] + (1 if status == "passed" else 0)
                self._conn.execute(
                    """UPDATE lesson_progress
                       SET status = ?, quiz_score = ?, attempts = ?, completed_at = ?
                       WHERE lesson_id = ?""",
                    (status, quiz_score, attempts, now if status == "passed" else cur["completed_at"], lesson_id),
                )
            self._conn.commit()

    # ---------- 考试 ----------
    def get_exam(self, exam_id: str) -> dict | None:
        row = self._conn.execute(
            "SELECT * FROM exam_progress WHERE exam_id = ?", (exam_id,)
        ).fetchone()
        return dict(row) if row else None

    def get_all_exams(self) -> dict[str, dict]:
        rows = self._conn.execute("SELECT * FROM exam_progress").fetchall()
        return {r["exam_id"]: dict(r) for r in rows}

    def record_exam(self, exam_id: str, kind: str, score: float, passed: bool) -> None:
        with self._lock:
            now = datetime.now().isoformat(timespec="seconds")
            cur = self.get_exam(exam_id)
            if cur is None:
                self._conn.execute(
                    """INSERT INTO exam_progress (exam_id, kind, score, attempts, passed, taken_at)
                       VALUES (?, ?, ?, 1, ?, ?)""",
                    (exam_id, kind, score, 1 if passed else 0, now),
                )
            else:
                self._conn.execute(
                    """UPDATE exam_progress
                       SET score = ?, attempts = attempts + 1, passed = ?, taken_at = ?
                       WHERE exam_id = ?""",
                    (score, 1 if passed else 0, now, exam_id),
                )
            self._conn.commit()

    # ---------- 会话 ----------
    def start_session(self, lesson_id: str) -> int:
        with self._lock:
            now = datetime.now().isoformat(timespec="seconds")
            cur = self._conn.execute(
                "INSERT INTO sessions (lesson_id, started_at) VALUES (?, ?)", (lesson_id, now)
            )
            self._conn.commit()
            return cur.lastrowid

    def end_session(self, session_id: int, minutes: int) -> None:
        with self._lock:
            now = datetime.now().isoformat(timespec="seconds")
            self._conn.execute(
                "UPDATE sessions SET ended_at = ?, minutes = ? WHERE id = ?",
                (now, minutes, session_id),
            )
            self._conn.commit()

    def get_sessions_today(self) -> list[dict]:
        today = datetime.now().date().isoformat()
        rows = self._conn.execute(
            "SELECT * FROM sessions WHERE started_at LIKE ? ORDER BY started_at",
            (today + "%",),
        ).fetchall()
        return [dict(r) for r in rows]

    def reset(self) -> None:
        with self._lock:
            self._conn.executescript(
                "DELETE FROM lesson_progress; DELETE FROM exam_progress; DELETE FROM sessions;"
            )
            self._conn.commit()

    def close(self) -> None:
        self._conn.close()
