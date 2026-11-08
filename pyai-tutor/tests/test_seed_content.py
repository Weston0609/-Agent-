import json
import tempfile
import unittest
from pathlib import Path

from src.pyai.db.seed_content import seed_content
from src.pyai.db.session import Database
from src.pyai.learning.curriculum import load_curriculum

_CURRICULUM_PATH = Path(__file__).resolve().parent.parent / "curriculum" / "full_curriculum.yaml"
CURRICULUM = load_curriculum(str(_CURRICULUM_PATH))


class TestSeedContent(unittest.TestCase):
    """离线种子内容：讲义按 `##` 切到 KP、题按 question["kp"] 归位。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self._tmp.name) / "test.db")
        self.db.seed_curriculum(CURRICULUM)
        self.content_dir = Path(self._tmp.name) / "content"
        (self.content_dir / "lessons").mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.db.close()
        self._tmp.cleanup()

    def _write_lesson(self, data: dict) -> None:
        path = self.content_dir / "lessons" / f"{data['id']}.json"
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def test_splits_theory_per_kp_and_routes_questions_by_kp(self):
        # 题序与 KP 序故意相反：必须靠 question["kp"] 归位（回归测试）
        self._write_lesson({
            "id": "s1u1l1",
            "kps": ["py.env.install", "py.env.venv"],
            "theory": (
                "# 标题\n\n## 1. 安装 Python\n\n去官网下载：\n\n```\npython --version\n```\n\n"
                "## 2. 虚拟环境\n\n创建环境：\n\n```\npython -m venv venv\n```\n"
            ),
            "quiz": [
                {"kp": "py.env.venv", "question": "Q-venv", "options": ["a", "b"], "answer": 1},
                {"kp": "py.env.install", "question": "Q-install", "options": ["a", "b"], "answer": 0},
            ],
        })
        stats = seed_content(self.db, self.content_dir)
        self.assertEqual(stats, {"lessons": 1, "kps": 2, "questions": 2})

        install = self.db.get_kp_content("py.env.install")
        self.assertIn("安装 Python", install.explain)
        self.assertNotIn("```", install.explain)                # 围栏代码块被剥离出正文
        self.assertIn("python --version", install.example_code)
        self.assertIn("python -m venv venv", self.db.get_kp_content("py.env.venv").example_code)

        install_qs = {q["id"]: q for q in self.db.questions_for("py.env.install")}
        self.assertEqual(install_qs["py.env.install-seed1"]["stem"], "Q-install")
        self.assertEqual(install_qs["py.env.install-seed1"]["answer"], 0)
        self.assertEqual(self.db.questions_for("py.env.venv")[0]["stem"], "Q-venv")

    def test_mismatched_sections_fall_back_to_full_theory(self):
        self._write_lesson({
            "id": "s1u1l1",
            "kps": ["py.env.install", "py.env.venv"],
            "theory": "没有二级标题的整篇讲义",
            "quiz": [],
        })
        seed_content(self.db, self.content_dir)
        for kp_id in ("py.env.install", "py.env.venv"):
            self.assertIn("整篇讲义", self.db.get_kp_content(kp_id).explain)

    def test_unknown_kp_falls_back_to_index_order(self):
        # 题没有 kp 字段（或写了未知 KP）时按序号回退，不能丢题
        self._write_lesson({
            "id": "s1u1l1",
            "kps": ["py.env.install"],
            "theory": "## 1. 安装\n内容",
            "quiz": [{"question": "Q0", "options": ["a"], "answer": 0}],
        })
        seed_content(self.db, self.content_dir)
        self.assertEqual(self.db.questions_for("py.env.install")[0]["stem"], "Q0")


if __name__ == "__main__":
    unittest.main()
