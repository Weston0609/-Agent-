"""/api/code/run —— 课堂「试一试」的执行通道。

守两件事：
① 真能跑学员代码并把 stdout/stderr 原样带回（这条通道以前根本不存在，示例代码只能看不能跑）；
② 信任边界上的校验不能省：空代码、超长代码直接 400，不能拿去喂子进程。
"""
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from src.pyai.config import Config
from src.pyai.ui.web import app as webapp
from src.pyai.ui.web.app import _MAX_CODE_BYTES, build_server

_CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"


class TestCodeRunRoute(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        cfg = Config(data_dir=Path(self._tmp.name) / "data", content_dir=_CONTENT_DIR)
        self._srv = build_server(cfg, port=0)
        self._base = f"http://127.0.0.1:{self._srv.server_address[1]}"
        threading.Thread(target=self._srv.serve_forever, daemon=True).start()

    def tearDown(self):
        self._srv.shutdown()
        self._srv.server_close()
        # 服务端按用户缓存 Orchestrator，不关掉就还占着 pyai.db，临时目录删不掉。
        for orch in webapp._ORCHESTRATORS.values():
            orch.close()
        webapp._ORCHESTRATORS.clear()
        self._tmp.cleanup()

    def _post(self, code):
        req = urllib.request.Request(
            self._base + "/api/code/run",
            data=json.dumps({"code": code}).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.status, json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode("utf-8"))

    def test_runs_code_and_returns_output(self):
        status, d = self._post("print(sum(range(5)))")
        self.assertEqual(status, 200)
        self.assertEqual(d["exit_code"], 0)
        self.assertEqual(d["stdout"].strip(), "10")

    def test_runtime_error_comes_back_as_stderr_not_a_crash(self):
        status, d = self._post("1/0")
        self.assertEqual(status, 200)
        self.assertNotEqual(d["exit_code"], 0)
        self.assertIn("ZeroDivisionError", d["stderr"])

    def test_empty_and_oversized_code_are_rejected(self):
        self.assertEqual(self._post("   ")[0], 400)
        self.assertEqual(self._post("x=1\n" * (_MAX_CODE_BYTES // 4 + 10))[0], 400)


if __name__ == "__main__":
    unittest.main()
