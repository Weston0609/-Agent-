"""种课程树 —— 从 full_curriculum.yaml 读入并写入 DB（semesters→units→lessons→kps）。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.pyai.config import Config
from src.pyai.db.derive import backfill
from src.pyai.db.session import Database
from src.pyai.learning.curriculum import load_curriculum


def main() -> None:
    config = Config.from_env()
    config.ensure_dirs()
    db = Database(config.db_path)
    curriculum = load_curriculum(config.curriculum_path)
    stats = db.seed_curriculum(curriculum)
    derived = backfill(db)
    print(f"课程树种入：{stats['semesters']} 学期 · {stats['units']} 单元 · "
          f"{stats['lessons']} 课 · {stats['kps']} 知识点")
    if not derived.get("skipped"):
        print(f"中文标题与难度：{derived['kp_titles']} 个知识点名 · "
              f"{derived['lesson_names']} 个课名 · {derived['question_difficulty']} 道题难度")
    for sem in curriculum.semesters:
        lessons = sum(len(u.lessons) for u in sem.units)
        print(f"  {sem.id} {sem.name}: {len(sem.units)} 单元 · {lessons} 课")
    db.close()


if __name__ == "__main__":
    main()
