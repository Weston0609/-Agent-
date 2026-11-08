"""手动触发更新 —— 运行 5 阶段更新管道（唯一烧 token 的常规入口）。

用法：python scripts/weekly_update.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.pyai.config import Config
from src.pyai.db.session import Database
from src.pyai.updater.pipeline import run_weekly_update


def main() -> None:
    config = Config.from_env()
    config.ensure_dirs()
    db = Database(config.db_path)
    result = run_weekly_update(db, manual=True)
    print(f"更新完成：{result}")
    db.close()


if __name__ == "__main__":
    main()
