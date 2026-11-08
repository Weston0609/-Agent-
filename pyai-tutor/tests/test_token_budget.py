"""每月 token 预算上限与告警。

约束（第六部分）：每月 token 预算约 6M，超限后不能再花钱。
在线后端（DeepSeek）受限；离线 Ollama 不计费，不受限。
"""
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from src.pyai.config import Config
from src.pyai.db.session import Database
from src.pyai.learning.curriculum import load_curriculum
from src.pyai.updater.pipeline import run_weekly_update

ROOT = Path(__file__).resolve().parent.parent


class _SpyLLM:
    """已配置的后端替身：记录是否真的被调用过。"""

    def __init__(self):
        self.calls = 0
        self.last_tokens = 0

    @property
    def configured(self):
        return True

    def chat(self, prompt):
        self.calls += 1
        return "{}"


class TestTokenBudget(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.db = Database(self.tmp / "t.db")
        self.db.seed_curriculum(load_curriculum(ROOT / "curriculum" / "full_curriculum.yaml"))
        self.addCleanup(self._tmp.cleanup)
        self.addCleanup(self.db.close)

    def _spend(self, tokens: int, when: datetime | None = None):
        when = when or datetime.now()
        self.db.log_update("weekly", when, when, tokens, 0, 0, "ok")

    def test_month_tokens_counts_only_current_month(self):
        self._spend(1000)
        self.assertEqual(self.db.month_tokens(), 1000)

        last_month = datetime.now().replace(day=1) - __import__("datetime").timedelta(days=1)
        self._spend(999_999, when=last_month)
        self.assertEqual(self.db.month_tokens(), 1000, "上个月的用量不该算进本月")

    def test_token_spend_reports_month_fields(self):
        self._spend(500)
        ts = self.db.token_spend()
        self.assertEqual(ts["month_tokens"], 500)
        self.assertEqual(ts["month_runs"], 1)
        self.assertEqual(ts["month"], datetime.now().strftime("%Y-%m"))
        self.assertEqual(ts["tokens"], 500, "累计字段保持原语义")

    def test_over_budget_skips_online_generation(self):
        """超限时必须停在花钱之前：后端一次都不许被调用。"""
        self._spend(6_000_000)
        spy = _SpyLLM()
        result = run_weekly_update(self.db, manual=True, max_kps=1, llm=spy, backend="deepseek",
                                   cfg=Config(monthly_token_budget=6_000_000),
                                   crawler=lambda since_days=7: [])
        self.assertEqual(result["status"], "skipped_over_budget")
        self.assertEqual(result["kps_added"], 0)
        self.assertEqual(result["tokens_used"], 0)
        self.assertEqual(spy.calls, 0, "超限后不应再发起任何生成请求")

    def test_under_budget_still_runs(self):
        self._spend(1_000_000)
        spy = _SpyLLM()
        result = run_weekly_update(self.db, manual=True, max_kps=1, llm=spy, backend="deepseek",
                                   cfg=Config(monthly_token_budget=6_000_000),
                                   crawler=lambda since_days=7: [])
        self.assertNotEqual(result["status"], "skipped_over_budget")
        self.assertGreater(spy.calls, 0, "未超限应正常调用后端")

    def test_offline_backend_is_exempt_from_budget(self):
        """离线 Ollama 不计费，即使本月用量已超预算也不该被拦。"""
        self._spend(99_000_000)
        spy = _SpyLLM()
        result = run_weekly_update(self.db, manual=True, max_kps=1, llm=spy, backend="ollama",
                                   cfg=Config(monthly_token_budget=6_000_000),
                                   crawler=lambda since_days=7: [])
        self.assertNotEqual(result["status"], "skipped_over_budget")
        self.assertGreater(spy.calls, 0)

    def test_zero_budget_means_unlimited(self):
        self._spend(99_000_000)
        spy = _SpyLLM()
        result = run_weekly_update(self.db, manual=True, max_kps=1, llm=spy, backend="deepseek",
                                   cfg=Config(monthly_token_budget=0),
                                   crawler=lambda since_days=7: [])
        self.assertNotEqual(result["status"], "skipped_over_budget")


if __name__ == "__main__":
    unittest.main()
