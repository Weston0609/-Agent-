"""Web 面板 —— 标准库 http.server 实现（零依赖，离线）。

JSON API + 单页 HTML。内容与判分全部走 orchestrator（DB 驱动）。
多用户（W8 D5）：所有接口都接受 `?user=<id>`（POST 也可放在 body.user），按用户缓存 Orchestrator。
"""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from ...config import Config
from ...core.orchestrator import Orchestrator
from ...tools.code_sandbox import CodeSandbox

_TEMPLATE_DIR = Path(__file__).parent / "templates"

# 学员代码与输出的上限：不设的话一个死循环能刷出几 MB 把浏览器和响应卡死。
_MAX_CODE_BYTES = 20_000
_MAX_OUTPUT_CHARS = 8_000

_CONFIG: Config = None  # type: ignore[assignment]
_ORCHESTRATORS: dict[str, Orchestrator] = {}


def _orch_for(user_id: str | None) -> Orchestrator:
    key = user_id or _CONFIG.default_user_id
    orch = _ORCHESTRATORS.get(key)
    if orch is None:
        orch = Orchestrator(_CONFIG, user_id=key)
        _ORCHESTRATORS[key] = orch
    return orch


class _Handler(BaseHTTPRequestHandler):
    def _json(self, data, status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def _query_user(self) -> str | None:
        raw = parse_qs(urlparse(self.path).query).get("user", [""])[0].strip()
        return raw or None

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        orch = _orch_for(self._query_user())
        if path in ("/", "/index.html"):
            self._serve_index()
        elif path == "/api/status":
            self._json(orch.status())
        elif path == "/api/map":
            self._json(orch.course_map())
        elif path == "/api/notifications":
            self._json(orch.notifications())
        elif path == "/api/review":
            # 到期复习清单（原先只有一个数字，没有可消费的列表）
            self._json(orch.review_items())
        elif path == "/api/errors":
            # 错题本（error_log 一直只写不读）
            self._json(orch.error_items())
        elif path == "/api/exams":
            # 考试记录 + 全部可考清单（exam_results 原先只能按 scope 单查）
            d = orch.exam_results()
            d["ready"] = orch.ready_exams()["items"]
            self._json(d)
        elif path == "/api/users":
            self._json({"users": [{"id": u.id, "name": u.name} for u in orch.db.active_users()],
                        "current": orch.user_id})
        elif path.startswith("/api/lesson/"):
            self._json(orch.lesson_content(path.rsplit("/", 1)[-1]))
        elif path.startswith("/api/interactions/"):
            # 课堂互动的题面（不含答案，判分在服务端）
            self._json(orch.lesson_interactions(path.rsplit("/", 1)[-1]))
        elif path == "/api/boss":
            # 开一局 / 续一局（战况在 sessions.state_json，刷新不重置）
            lesson_id = parse_qs(urlparse(self.path).query).get("lesson", [""])[0].strip()
            self._json(orch.boss_start(lesson_id or None))
        elif path.startswith("/api/questions/"):
            lesson_id = path.rsplit("/", 1)[-1]
            self._json({"lesson_id": lesson_id, "questions": orch.lesson_questions(lesson_id)})
        elif path.startswith("/api/exam/"):
            # /api/exam/<scope>/<scope_id>
            parts = path.strip("/").split("/")
            if len(parts) != 4 or parts[1] != "exam":
                self._json({"error": "bad request"}, 400)
                return
            scope, scope_id = parts[2], parts[3]
            try:
                # 题面走 exam_view：剥掉 answer/required_keywords，别把标准答案发给浏览器。
                self._json(orch.exam_view(scope, scope_id))
            except ValueError as exc:
                self._json({"error": str(exc)}, 400)
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        payload = self._read_json() if path != "/api/reset" else {}
        orch = _orch_for(payload.get("user") or self._query_user())
        if path.startswith("/api/quiz/"):
            self._json(orch.submit_quiz(path.rsplit("/", 1)[-1], payload.get("answers", [])))
        elif path.startswith("/api/exam/"):
            parts = path.strip("/").split("/")
            if len(parts) != 4:
                self._json({"error": "bad request"}, 400)
                return
            try:
                self._json(orch.submit_exam(parts[2], parts[3], payload.get("answers", [])))
            except ValueError as exc:
                self._json({"error": str(exc)}, 400)
        elif path == "/api/boss/hit":
            self._json(orch.boss_hit(payload.get("answer"),
                                     lesson_id=payload.get("lesson_id")))
        elif path == "/api/interactions/check":
            self._json(orch.check_interaction(
                payload.get("lesson_id", ""), payload.get("id", ""),
                payload.get("answer")))
        elif path == "/api/code/run":
            # 课堂里的「试一试」：学员改示例代码、跑、看输出。判分与内容生成用同一个沙箱。
            code = str(payload.get("code") or "")
            if not code.strip():
                self._json({"exit_code": -1, "stdout": "", "stderr": "代码是空的"}, 400)
                return
            if len(code) > _MAX_CODE_BYTES:
                self._json({"exit_code": -1, "stdout": "",
                            "stderr": f"代码太长（上限 {_MAX_CODE_BYTES} 字符）"}, 400)
                return
            result = CodeSandbox(timeout_seconds=10).run(code)
            # 死循环能刷出几 MB 输出，截断后再回前端，避免浏览器卡死。
            result["stdout"] = (result.get("stdout") or "")[:_MAX_OUTPUT_CHARS]
            result["stderr"] = (result.get("stderr") or "")[:_MAX_OUTPUT_CHARS]
            self._json(result)
        elif path == "/api/boss/restart":
            self._json(orch.boss_restart(payload.get("lesson_id")))
        elif path == "/api/notifications/read":
            self._json({"marked": orch.mark_notifications_read()})
        elif path == "/api/reset":
            orch.reset()
            self._json({"ok": True})
        else:
            self._json({"error": "not found"}, 404)

    def _serve_index(self) -> None:
        idx = _TEMPLATE_DIR / "index.html"
        body = idx.read_bytes() if idx.exists() else b"<h1>pyai-tutor</h1>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        pass  # 静默日志


def build_server(config: Config, port: int = 8000) -> ThreadingHTTPServer:
    """建好监听中的 HTTP 服务（不阻塞）—— serve() 与冒烟测试共用同一接缝。"""
    global _CONFIG
    config.ensure_dirs()
    _CONFIG = config
    _orch_for(config.default_user_id)     # 启动即初始化默认用户，失败早暴露
    return ThreadingHTTPServer(("127.0.0.1", port), _Handler)


def serve(config: Config, port: int = 8000) -> None:
    server = build_server(config, port)
    print(f"pyai-tutor Web 面板：http://127.0.0.1:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        for orch in _ORCHESTRATORS.values():
            orch.close()
        _ORCHESTRATORS.clear()
        server.server_close()
