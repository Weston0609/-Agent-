"""系统更新层 —— 全系统唯一烧 token 的地方。

离线学习 0 token；只有 weekly 定时任务或显式 `pyai update` 才生成/更新内容。
无 DEEPSEEK_API_KEY 时自动改用本机 Ollama（离线 0 token），都不可用则跳过生成。
"""
from .audit import Audit, run_audit
from .kp_generator import generate_kp_content, generate_quiz, plan_next_batch
from .pipeline import run_weekly_update, select_llm

__all__ = [
    "Audit", "run_audit", "generate_kp_content", "generate_quiz",
    "plan_next_batch", "run_weekly_update", "select_llm",
]
