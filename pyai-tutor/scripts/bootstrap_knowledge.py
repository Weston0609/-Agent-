"""首次知识库引导 —— 触发一次更新管道生成内容（消耗 token，仅初始化时运行一次）。

日常离线学习不调用本脚本。
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
    print(f"首次知识库引导完成：{result}")
    db.close()


if __name__ == "__main__":
    main()
