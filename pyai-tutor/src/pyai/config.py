"""全局配置 —— 从环境变量 + 默认值构造，零依赖。

配置只在进程启动时读取一次，运行时不可变，便于测试注入。
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent  # pyai-tutor/


def _f(key: str, default: float) -> float:
    try:
        return float(os.environ.get(key, default))
    except (TypeError, ValueError):
        return default


def load_dotenv(path: Path | None = None) -> int:
    """把 .env 读进 os.environ（已存在的环境变量优先，不覆盖）。

    .env.example 里列了变量名，但此前代码只读 os.environ、从不读文件，
    于是「照着 example 建好 .env」并不会生效。这里补上这最后一步。

    返回写入的变量个数。文件不存在时静默返回 0（正常情况：只用环境变量）。
    """
    env_file = path or (PROJECT_ROOT / ".env")
    if not env_file.is_file():
        return 0
    n = 0
    for raw in env_file.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        # 去掉成对的引号；不处理转义（.env 里放路径/密钥不需要）
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if key and key not in os.environ:
            os.environ[key] = value
            n += 1
    return n


@dataclass(frozen=True)
class Config:
    """全局配置。字段名即 .env.example 中的环境变量名。"""

    # 学习参数
    lesson_minutes: int = 40
    # 课级闯关门禁 = 单元考线 75%（注意：知识点线是 80%，见 db.session.KP_PASS）
    pass_threshold: float = 0.75
    lessons_per_day: int = 3
    learning_start_hour: int = 8
    learning_end_hour: int = 22

    # 用户与课表（参考学校模式）
    timezone: str = "Asia/Shanghai"
    default_user_id: str = "default"
    default_user_name: str = "学习者"

    # DeepSeek（仅更新阶段）
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    # 每月 token 预算上限（0 = 不限制）。超限后更新管道不再发起在线生成。
    monthly_token_budget: int = 6_000_000

    # 本地 Ollama（离线推理，可选）
    ollama_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5:7b"

    # 路径
    root: Path = field(default_factory=lambda: PROJECT_ROOT)
    data_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "data")
    curriculum_path: Path = field(default_factory=lambda: PROJECT_ROOT / "curriculum" / "full_curriculum.yaml")
    sources_path: Path = field(default_factory=lambda: PROJECT_ROOT / "curriculum" / "sources.yaml")
    content_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "content")
    prompt_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "curriculum" / "prompt_templates")

    @property
    def db_path(self) -> Path:
        return self.data_dir / "pyai.db"

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_env(cls) -> "Config":
        load_dotenv()          # 先补 .env，再读 os.environ
        return cls(
            lesson_minutes=int(os.environ.get("LESSON_MINUTES", 40)),
            pass_threshold=_f("PASS_THRESHOLD", 0.75),
            lessons_per_day=int(os.environ.get("LESSONS_PER_DAY", 3)),
            learning_start_hour=int(os.environ.get("LEARNING_START_HOUR", 8)),
            learning_end_hour=int(os.environ.get("LEARNING_END_HOUR", 22)),
            timezone=os.environ.get("TIMEZONE", "Asia/Shanghai"),
            default_user_id=os.environ.get("DEFAULT_USER_ID", "default"),
            default_user_name=os.environ.get("DEFAULT_USER_NAME", "学习者"),
            deepseek_api_key=os.environ.get("DEEPSEEK_API_KEY", ""),
            deepseek_base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            deepseek_model=os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"),
            monthly_token_budget=int(os.environ.get("MONTHLY_TOKEN_BUDGET", 6_000_000)),
            ollama_url=os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434"),
            ollama_model=os.environ.get("OLLAMA_MODEL", "qwen2.5:7b"),
            # 数据目录可覆盖：换库/多份进度/把学习数据放别处都靠它。
            # （此前这是个只存在于文档里的开关：from_env 从来不读它，写进 .env 也不生效。）
            data_dir=Path(os.environ["PYAI_DATA_DIR"]) if os.environ.get("PYAI_DATA_DIR")
            else PROJECT_ROOT / "data",
        )
