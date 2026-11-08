"""本地 Web 面板 —— 纯标准库 http.server，零依赖。

运行：python -m src.web  （或 python -m src.cli web）
浏览器打开 http://127.0.0.1:8000

API：
  GET  /                    面板首页（web/index.html）
  GET  /api/status          进度总览 + 今日排课 + 实时时间
  GET  /api/lesson/<id>     课程正文 + 随堂测验（不含答案）
  POST /api/quiz/<id>       提交随堂测验 {answers: [int,...]}
  GET  /api/exam/<id>       考试题目（不含答案）
  POST /api/exam/<id>       提交考试 {answers: [int,...]}
  POST /api/reset           清空进度
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .content import ContentStore
from .grading import grade, grade_and_record, grade_lesson_quiz
from .models import load_curriculum
from .scheduler import plan_day, current_lesson
from .store import Store
from .unlock import available_exams, compute_states, next_unlocked_lesson, semester_progress

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CURRICULUM_PATH = PROJECT_ROOT / "curriculum" / "curriculum.json"
CONTENT_DIR = PROJECT_ROOT / "content"
WEB_DIR = PROJECT_ROOT / "web"
DB_PATH = PROJECT_ROOT / "data" / "progress.db"


def _load():
    curriculum = load_curriculum(CURRICULUM_PATH)
    store = Store(DB_PATH)
    content = ContentStore(CONTENT_DIR)
    return curriculum, store, content


def _status_payload(curriculum, store) -> dict:
    states = compute_states(curriculum, store)
    total = curriculum.total_lessons
    passed = sum(1 for s in states.values() if s.status == "passed")
    unlocked = sum(1 for s in states.values() if s.status == "unlocked")
    nxt = next_unlocked_lesson(curriculum, states)
    now = datetime.now()

    plan = plan_day(curriculum, store, now=now)
    cur = current_lesson(curriculum, store)

    return {
        "now": now.isoformat(timespec="seconds"),
        "total_lessons": total,
        "total_kps": curriculum.total_kps,
        "passed": passed,
        "unlocked": unlocked,
        "next_lesson": nxt.id if nxt else None,
        "current_lesson": cur.lesson_id if cur else None,
        "schedule": [
            {
                "lesson_id": e.lesson_id,
                "start": e.start_at.strftime("%H:%M"),
                "end": e.end_at.strftime("%H:%M"),
            }
            for e in plan.entries
        ],
        "schedule_note": plan.note,
        "semesters": [
            {
                "id": sem.id,
                "name": sem.name,
                "passed": semester_progress(curriculum, sem, states)[0],
                "total": semester_progress(curriculum, sem, states)[1],
            }
            for sem in curriculum.semesters
        ],
        "pass_threshold": curriculum.pass_threshold,
        "lesson_minutes": curriculum.lesson_minutes,
        "available_exams": available_exams(curriculum, store),
    }


def _lesson_payload(curriculum, content, lesson_id: str) -> dict:
    lesson = curriculum.lessons_by_id.get(lesson_id)
    if lesson is None:
        return {"error": f"未知课程 {lesson_id}"}
    lc = content.lesson(lesson.id, lesson.kps)
    return {
        "id": lc.id,
        "title": lc.title,
        "kps": list(lc.kps),
        "theory": lc.theory,
        "quiz": [
            {"question": q.question, "options": list(q.options)} for q in lc.quiz
        ],
        "quiz_total": len(lc.quiz),
    }


def _exam_payload(content, exam_id: str, kind: str) -> dict:
    ec = content.exam(exam_id, kind)
    return {
        "id": ec.id,
        "kind": ec.kind,
        "title": ec.title,
        "questions": [
            {"question": q.question, "options": list(q.options)} for q in ec.questions
        ],
    }


class Handler(BaseHTTPRequestHandler):
    curriculum = None
    store = None
    content = None

    def log_message(self, fmt, *args):  # 静默日志
        pass

    def _send_json(self, obj: dict, status: int = 200) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, path: Path) -> None:
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path in ("/", "/index.html"):
            return self._send_html(WEB_DIR / "index.html")

        if path == "/api/status":
            return self._send_json(_status_payload(self.curriculum, self.store))

        if path.startswith("/api/lesson/"):
            lid = path.rsplit("/", 1)[1]
            return self._send_json(_lesson_payload(self.curriculum, self.content, lid))

        if path.startswith("/api/exam/"):
            eid = path.rsplit("/", 1)[1]
            kind = "final" if eid.endswith("-final") else "unit"
            return self._send_json(_exam_payload(self.content, eid, kind))

        return self._send_json({"error": "not found"}, 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        data = self._read_json()
        threshold = self.curriculum.pass_threshold

        if path.startswith("/api/quiz/"):
            lid = path.rsplit("/", 1)[1]
            lesson = self.curriculum.lessons_by_id.get(lid)
            if lesson is None:
                return self._send_json({"error": f"未知课程 {lid}"}, 404)
            lc = self.content.lesson(lesson.id, lesson.kps)
            submitted = data.get("answers", [])
            result = grade_lesson_quiz(
                self.store, lid,
                [{"answer": q.answer} for q in lc.quiz],
                submitted, threshold,
            )
            return self._send_json(result)

        if path.startswith("/api/exam/"):
            eid = path.rsplit("/", 1)[1]
            kind = "final" if eid.endswith("-final") else "unit"
            ec = self.content.exam(eid, kind)
            submitted = data.get("answers", [])
            result = grade_and_record(
                self.store, eid, kind,
                [{"answer": q.answer} for q in ec.questions],
                submitted, threshold,
            )
            return self._send_json(result)

        if path == "/api/reset":
            self.store.reset()
            return self._send_json({"ok": True})

        return self._send_json({"error": "not found"}, 404)


def serve(host: str = "127.0.0.1", port: int = 8000) -> None:
    curriculum, store, content = _load()
    Handler.curriculum = curriculum
    Handler.store = store
    Handler.content = content

    server = ThreadingHTTPServer((host, port), Handler)
    url = f"http://{host}:{port}"
    print(f"学习面板已启动：{url}", file=sys.stderr)
    print("按 Ctrl+C 停止。", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        store.close()


if __name__ == "__main__":
    serve()
