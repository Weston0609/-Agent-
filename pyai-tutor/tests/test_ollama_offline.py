import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from src.pyai.learning.curriculum import load_curriculum
from src.pyai.tools.ollama_client import OllamaClient
from src.pyai.updater.kp_generator import generate_kp_content, generate_quiz
from src.pyai.updater.pipeline import select_llm

_KP_JSON = json.dumps({
    "explain": "整数是不可变类型。",
    "example_code": "x = 1\nprint(x)",
    "pitfalls": "不要用 int 做键以外的魔术。",
    "sources": [],
}, ensure_ascii=False)

_QUIZ_JSON = json.dumps([
    {"type": "single_choice", "stem": "1+1=?", "options": ["1", "2", "3", "4"],
     "answer": 1, "explanation": "算术", "error_tag": "arith", "variant_group": "g1"},
], ensure_ascii=False)


class _StubOllama(BaseHTTPRequestHandler):
    """最小 Ollama 桩：/api/tags 探活 + /api/generate 返回按 prompt 区分的 JSON。"""

    def log_message(self, *a):  # 静音
        pass

    def do_GET(self):
        if self.path == "/api/tags":
            body = json.dumps({"models": []}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        prompt = json.loads(self.rfile.read(length).decode()).get("prompt", "")
        # 题库生成的契约要求返回数组；正文生成返回对象
        payload = _QUIZ_JSON if "JSON 数组" in prompt else _KP_JSON
        body = json.dumps({"response": payload}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class TestOllamaOfflinePath(unittest.TestCase):
    """离线生成路径（0 token）：无 API key 时应回落到本机 Ollama 并真正产出内容。"""

    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), _StubOllama)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def _client(self):
        return OllamaClient(base_url=f"http://127.0.0.1:{self.port}", model="stub")

    def test_probe_reports_configured_and_chat_returns_text(self):
        llm = self._client()
        self.assertTrue(llm.configured)
        self.assertIn("不可变", llm.chat("讲解整数"))
        self.assertEqual(llm.last_tokens, 0, "本地推理不计费")

    def test_unreachable_ollama_reports_unconfigured(self):
        dead = OllamaClient(base_url="http://127.0.0.1:1", model="stub")
        self.assertFalse(dead.configured)
        with self.assertRaises(RuntimeError):
            dead.chat("x")

    def test_select_llm_falls_back_to_ollama_without_api_key(self):
        from src.pyai.config import Config
        cfg = Config(deepseek_api_key="", ollama_url=f"http://127.0.0.1:{self.port}")
        llm, backend = select_llm(cfg)
        self.assertEqual(backend, "ollama")
        self.assertTrue(llm.configured)

    def test_plan_next_batch_drops_non_string_items(self):
        """阶段 4 的扩建计划只接受 id 字符串；模型返回对象数组时不能透传成垃圾 KP。"""
        from src.pyai.updater.kp_generator import plan_next_batch

        class _Fake:
            def chat(self, prompt):
                return json.dumps([
                    "py.new.one",
                    {"id": "py.new.two"},
                    {"title": "无 id 的对象"},
                    42,
                    "   ",
                    "",
                ])

        got = plan_next_batch(_Fake(), {"total_kps": 385, "semesters": {}})
        self.assertEqual(got, ["py.new.one", "py.new.two"])

    def test_generate_kp_content_and_quiz_parse_contract(self):
        llm = self._client()
        kp = generate_kp_content(llm, {"id": "py.type.int", "title": "整数"}, prompt_dir=None)
        self.assertEqual(kp["id"], "py.type.int")
        self.assertTrue(kp["explain"])
        self.assertEqual(kp["sources"], [])
        self.assertFalse(kp["verified"])

        questions = generate_quiz(llm, kp, n_variants=1, prompt_dir=None)
        self.assertEqual(len(questions), 1)
        self.assertEqual(questions[0]["kp_id"], "py.type.int")
        self.assertEqual(questions[0]["answer"], 1)

    def test_pipeline_writes_kp_and_quiz_into_db(self):
        """整条离线更新链：桩 Ollama → 生成 → 落库 → 讲师可离线读到内容。"""
        from src.pyai.agents.tutor import Tutor
        from src.pyai.config import Config
        from src.pyai.db.session import Database
        from src.pyai.updater.pipeline import run_weekly_update

        with tempfile.TemporaryDirectory() as tmp:
            cfg = Config(data_dir=Path(tmp), ollama_url=f"http://127.0.0.1:{self.port}")
            db = Database(Path(tmp) / "t.db")
            # 曲线必须先入库，否则 find_unfilled_kps 没东西可挑，任务是空转
            db.seed_curriculum(load_curriculum(cfg.curriculum_path))
            picked = db.find_unfilled_kps(1)[0]["kp_id"]  # 真实队列选的第一个 KP
            llm = self._client()
            try:
                result = run_weekly_update(db, manual=True, max_kps=1, llm=llm,
                                           crawler=lambda since_days=7: [])
                self.assertEqual(result["backend"], "injected")
                self.assertEqual(result["status"], "ok")
                self.assertEqual(result["tokens_used"], 0, "离线生成不烧 token")
                self.assertGreaterEqual(result["kps_added"], 1)
                self.assertTrue(db.questions_for(picked), "题也要落库，不能只存讲义")

                content = Tutor(db).teach_cached(picked)
                self.assertTrue(content["ok"], "落库后讲师应能离线读到内容")
                self.assertIn("不可变", content["explain"])
            finally:
                db.close()   # Windows: 连接不关，TemporaryDirectory 就删不掉（WinError 32）
