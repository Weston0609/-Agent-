"""随堂测验组卷。

原实现把题库全端上去：题库每 KP 约 20 道变体，一节 4 KP 的课就是 80 道题，而 QUIZ 阶段一共
只有 10 分钟——根本做不完。每 KP 存 20 道变体本来就是为了重做时换题，全端上去等于白存。

这里守住两条不变量：
① 每个知识点抽到的题数有上限；
② 「取到的题」与「判分用的题」必须是同一批——否则答案下标错位，全对也会被判错。
"""
import tempfile
import unittest
from pathlib import Path

from src.pyai.config import Config
from src.pyai.core.orchestrator import QUIZ_PER_KP, Orchestrator
from src.pyai.learning.grading import model_answer

_CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"
_POOL = 20          # 每个 KP 造 20 道题，模拟真实题库规模


class TestQuizSampling(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.cfg = Config(data_dir=Path(self._tmp.name) / "data", content_dir=_CONTENT_DIR)
        self.orch = Orchestrator(self.cfg)
        self.lesson_id = self.orch.status()["next_lesson"]
        self.kp_ids = self.orch.db.lesson_kp_ids(self.lesson_id)
        self.assertGreaterEqual(len(self.kp_ids), 1)
        for kp_id in self.kp_ids:
            self.orch.db.save_questions(kp_id, [
                {"type": "single_choice", "stem": f"{kp_id} 第 {i} 题",
                 "options": ["a", "b", "c", "d"], "answer": i % 4,
                 "explanation": "x", "error_tag": "概念混淆"}
                for i in range(_POOL)
            ])

    def tearDown(self):
        self.orch.close()
        self._tmp.cleanup()

    def test_each_kp_is_capped(self):
        counts: dict[str, int] = {}
        for q in self.orch.lesson_questions(self.lesson_id):
            counts[q["kp_id"]] = counts.get(q["kp_id"], 0) + 1
        self.assertEqual(set(counts), set(self.kp_ids), "每个知识点都要出到题")
        for kp_id, n in counts.items():
            self.assertEqual(n, QUIZ_PER_KP, f"{kp_id} 抽了 {n} 道，应恰好 {QUIZ_PER_KP} 道")

    def test_questions_fetched_are_the_ones_graded(self):
        """取题后照抄答案交卷必须满分——抽题与判分不同批就会错位。"""
        questions = self.orch.lesson_questions(self.lesson_id)
        result = self.orch.submit_quiz(self.lesson_id, [model_answer(q) for q in questions])
        self.assertEqual(result["score"], 1.0, "取到的题与判分用的题不是同一批")
        self.assertTrue(result["passed"])

    def test_paper_is_stable_until_a_retake(self):
        """同一局里反复取题拿到的是同一份卷子（旧实现按 attempts 现算 → 每次都不一样）。"""
        first = [q["id"] for q in self.orch.lesson_questions(self.lesson_id)]
        again = [q["id"] for q in self.orch.lesson_questions(self.lesson_id)]
        self.assertEqual(first, again, "同一局内卷子必须固定，否则取题与判分错位")

    def test_retake_rotates_the_pool(self):
        """没打过 → 重开一局换一批题（每 KP 20 道变体的意义所在）。"""
        first = [q["id"] for q in self.orch.lesson_questions(self.lesson_id)]
        self.orch.submit_quiz(self.lesson_id, [])                # 全错，交白卷
        second = [q["id"] for q in self.orch.lesson_questions(self.lesson_id)]
        self.assertNotEqual(first, second, "重做应换一批题")
        self.assertFalse(set(first) & set(second), "重做不该再遇到打过的题")


if __name__ == "__main__":
    unittest.main()
