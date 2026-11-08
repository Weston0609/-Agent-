"""初始化数据库 —— 建表 + 默认用户 + 默认课表 + 种课程树（幂等）。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.pyai.config import Config
from src.pyai.db.derive import backfill
from src.pyai.db.seed_content import seed_content
from src.pyai.db.session import Database
from src.pyai.learning.curriculum import load_curriculum


def main() -> None:
    config = Config.from_env()
    config.ensure_dirs()
    db = Database(config.db_path)
    db.ensure_default_user(config.default_user_name, config.timezone)
    db.seed_default_schedule(config.default_user_id)
    curriculum = load_curriculum(config.curriculum_path)
    stats = db.seed_curriculum(curriculum)
    content = seed_content(db, config.content_dir)
    derived = backfill(db)
    print(f"数据库已初始化：{config.db_path}")
    print(f"课程树：{stats['semesters']} 学期 · {stats['units']} 单元 · "
          f"{stats['lessons']} 课 · {stats['kps']} 知识点")
    print(f"种子内容：{content['lessons']} 课讲义 · {content['kps']} 个知识点 · "
          f"{content['questions']} 道题（离线 0 token）")
    if not derived.get("skipped"):
        print(f"中文标题与难度：{derived['kp_titles']} 个知识点名 · "
              f"{derived['lesson_names']} 个课名 · {derived['question_difficulty']} 道题难度")
    db.close()


if __name__ == "__main__":
    main()
