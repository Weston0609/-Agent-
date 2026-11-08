"""配置加载：.env 文件必须真的被读到。

此前 config.from_env() 只读 os.environ，于是「照 .env.example 建好 .env」
并不会生效 —— 这是用户报告「我配好了却不生效」的根因。
"""
import os
import tempfile
import unittest
from pathlib import Path

from src.pyai.config import Config, load_dotenv

_KEYS = ["DEEPSEEK_API_KEY", "DEEPSEEK_MODEL", "OLLAMA_URL", "MONTHLY_TOKEN_BUDGET"]


class TestDotenvLoading(unittest.TestCase):
    def setUp(self):
        # 备份并清掉，避免宿主环境干扰
        self._saved = {k: os.environ.get(k) for k in _KEYS}
        for k in _KEYS:
            os.environ.pop(k, None)
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.addCleanup(self._restore)

    def _restore(self):
        for k, v in self._saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def _write(self, text: str) -> Path:
        p = Path(self._tmp.name) / ".env"
        p.write_text(text, encoding="utf-8")
        return p

    def test_loads_values_skipping_comments_and_junk(self):
        p = self._write(
            "# 这是注释\n"
            "\n"
            "DEEPSEEK_API_KEY=sk-abc123\n"
            "OLLAMA_URL=http://127.0.0.1:11434\n"
            "这行没有等号\n"
        )
        n = load_dotenv(p)
        self.assertEqual(n, 2)
        self.assertEqual(os.environ["DEEPSEEK_API_KEY"], "sk-abc123")
        self.assertEqual(os.environ["OLLAMA_URL"], "http://127.0.0.1:11434")

    def test_strips_matching_quotes(self):
        p = self._write('DEEPSEEK_MODEL="deepseek-chat"\n')
        load_dotenv(p)
        self.assertEqual(os.environ["DEEPSEEK_MODEL"], "deepseek-chat")

    def test_real_env_wins_over_dotenv(self):
        """已存在的环境变量优先 —— 否则一个遗留 .env 会悄悄覆盖用户的 shell 设置。"""
        os.environ["DEEPSEEK_API_KEY"] = "sk-from-shell"
        p = self._write("DEEPSEEK_API_KEY=sk-from-file\n")
        load_dotenv(p)
        self.assertEqual(os.environ["DEEPSEEK_API_KEY"], "sk-from-shell")

    def test_missing_file_is_not_an_error(self):
        self.assertEqual(load_dotenv(Path(self._tmp.name) / "nope.env"), 0)

    def test_from_env_picks_up_dotenv_in_project_root(self):
        """端到端：把 .env 放到 PROJECT_ROOT，from_env() 应读到它。"""
        from src.pyai import config as cfg_mod
        target = cfg_mod.PROJECT_ROOT / ".env"
        if target.exists():
            self.skipTest("项目根已有 .env，跳过以免覆盖用户配置")
        target.write_text("DEEPSEEK_API_KEY=sk-from-root-dotenv\n", encoding="utf-8")
        self.addCleanup(lambda: target.unlink(missing_ok=True))

        conf = Config.from_env()
        self.assertEqual(conf.deepseek_api_key, "sk-from-root-dotenv")


if __name__ == "__main__":
    unittest.main()
