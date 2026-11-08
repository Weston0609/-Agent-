"""题库准入：残缺题必须在入口被丢弃，不能写进库让学生做。"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pyai.updater.kp_generator import _is_wellformed, generate_quiz


class _ScriptedLLM:
    """按脚本返回模型输出，用于构造各种残缺题库。"""

    def __init__(self, payload: str):
        self.payload = payload
        self.last_tokens = 0

    def chat(self, prompt: str) -> str:  # noqa: ARG002
        return self.payload


class TestIsWellformed(unittest.TestCase):
    def test_accepts_normal_single_choice(self):
        self.assertTrue(_is_wellformed({
            "type": "single_choice", "stem": "print(1) 输出什么？",
            "options": ["1", "2", "报错", "None"], "answer": 0,
            "explanation": "就是打印 1", "error_tag": "概念混淆",
        }))

    def test_requires_explanation_and_error_tag(self):
        """解析撑起错题本；error_tag 是 error_log 的分类键。实测场景题常整题缺。"""
        base = {
            "type": "single_choice", "stem": "题",
            "options": ["a", "b"], "answer": 0,
        }
        self.assertFalse(_is_wellformed(base))
        self.assertFalse(_is_wellformed({**base, "explanation": "因为"}))
        self.assertFalse(_is_wellformed({**base, "error_tag": "概念混淆"}))
        self.assertFalse(_is_wellformed({**base, "explanation": "  ", "error_tag": "概念混淆"}))
        self.assertTrue(_is_wellformed({**base, "explanation": "因为", "error_tag": "概念混淆"}))

    def test_rejects_empty_stem(self):
        """实测 4 个 KP 共 80 道题就是这样落库的。"""
        base = {"explanation": "x", "error_tag": "y"}
        self.assertFalse(_is_wellformed({
            **base, "type": "single_choice", "stem": "", "options": ["a", "b"], "answer": 0,
        }))
        self.assertFalse(_is_wellformed({
            **base, "type": "single_choice", "stem": "   ", "options": ["a", "b"], "answer": 0,
        }))

    def test_rejects_out_of_range_answer(self):
        self.assertFalse(_is_wellformed({
            "type": "single_choice", "stem": "题", "options": ["a", "b"], "answer": 5,
        }))
        self.assertFalse(_is_wellformed({
            "type": "single_choice", "stem": "题", "options": ["a", "b"], "answer": -1,
        }))

    def test_rejects_non_numeric_answer(self):
        self.assertFalse(_is_wellformed({
            "type": "single_choice", "stem": "题", "options": ["a", "b"], "answer": "a",
        }))

    def test_rejects_too_few_or_blank_options(self):
        self.assertFalse(_is_wellformed({
            "type": "single_choice", "stem": "题", "options": ["a"], "answer": 0,
        }))
        self.assertFalse(_is_wellformed({
            "type": "single_choice", "stem": "题", "options": ["a", "  "], "answer": 0,
        }))

    def test_non_choice_types_need_their_own_answer_shape(self):
        """题型不同，答案形态不同；形态不对判分器会直接判错。"""
        need = {"explanation": "x", "error_tag": "y"}
        # 填空：Grading 把 answer 当数组遍历，字符串会被逐字符拆开
        self.assertTrue(_is_wellformed(
            {**need, "type": "fill_blank", "stem": "题干", "answer": ["list", "列表"]}))
        self.assertFalse(_is_wellformed(
            {**need, "type": "fill_blank", "stem": "题干", "answer": "list"}))
        self.assertFalse(_is_wellformed(
            {**need, "type": "fill_blank", "stem": "题干", "answer": []}))
        # 代码阅读：答案是非空文字
        self.assertTrue(_is_wellformed(
            {**need, "type": "code_reading", "stem": "题干", "answer": "输出 3"}))
        self.assertFalse(_is_wellformed(
            {**need, "type": "code_reading", "stem": "题干", "answer": "  "}))
        # 场景：靠 required_keywords 命中率判分
        self.assertTrue(_is_wellformed(
            {**need, "type": "scenario", "stem": "题干", "required_keywords": ["索引"]}))
        self.assertFalse(_is_wellformed(
            {**need, "type": "scenario", "stem": "题干"}))
        self.assertFalse(_is_wellformed(
            {**need, "type": "scenario", "stem": "题干", "required_keywords": []}))
        # 未知题型不收
        self.assertFalse(_is_wellformed({**need, "type": "essay", "stem": "题干"}))

    def test_multi_choice_needs_two_distinct_valid_picks(self):
        base = {
            "type": "multi_choice", "stem": "题干", "options": ["a", "b", "c"],
            "explanation": "x", "error_tag": "y",
        }
        self.assertTrue(_is_wellformed({**base, "answer": [0, 2]}))
        self.assertTrue(_is_wellformed({**base, "answer": [0, 1, 2]}))
        self.assertFalse(_is_wellformed({**base, "answer": [0]}))          # 只选一个不算多选
        self.assertFalse(_is_wellformed({**base, "answer": [0, 5]}))       # 越界
        self.assertFalse(_is_wellformed({**base, "answer": [1, 1]}))       # 重复下标
        self.assertFalse(_is_wellformed({**base, "answer": []}))


class TestGenerateQuizDrops(unittest.TestCase):
    KP = {"id": "py.demo.topic", "title": "py.demo.topic"}

    def _gen(self, questions: list) -> list:
        import json
        return generate_quiz(_ScriptedLLM(json.dumps(questions)), self.KP, n_variants=10)

    def test_keeps_good_drops_malformed_and_leaky(self):
        out = self._gen([
            {"type": "single_choice", "stem": "好题一", "options": ["a", "b"], "answer": 0,
             "explanation": "因为 a", "error_tag": "概念混淆"},
            {"type": "single_choice", "stem": "", "options": ["a", "b"], "answer": 0, "explanation": "x", "error_tag": "y"},
            {"type": "single_choice", "stem": "答案越界", "options": ["a", "b"], "answer": 9, "explanation": "x", "error_tag": "y"},
            {"type": "single_choice", "stem": "泄漏 py.demo.topic 的题", "options": ["a", "b"], "answer": 0, "explanation": "x", "error_tag": "y"},
            {"type": "single_choice", "stem": "好题二", "options": ["a", "b"], "answer": 1,
             "explanation": "因为 b", "error_tag": "边界错误"},
        ])
        self.assertEqual([q["stem"] for q in out], ["好题一", "好题二"])

    def test_generated_ids_have_no_gaps(self):
        """丢弃后重新编号：id 要连续，不能留下 q3、q7 这种空洞。"""
        out = self._gen([
            {"type": "single_choice", "stem": "", "options": ["a", "b"], "answer": 0, "explanation": "x", "error_tag": "y"},
            {"type": "single_choice", "stem": "留下的", "options": ["a", "b"], "answer": 0, "explanation": "x", "error_tag": "y"},
        ])
        self.assertEqual([q["id"] for q in out], ["py.demo.topic-q0"])

    def test_empty_quiz_returns_empty_list(self):
        self.assertEqual(self._gen([]), [])


class TestScenarioKeywordsSurviveRoundtrip(unittest.TestCase):
    """回归：场景题的 required_keywords 必须在「生成 → 落库 → 取回」全程不丢。

    真 bug 背景：questions 表早期没有 required_keywords 列，_is_wellformed 校验的是
    内存里的 dict（通过），但 INSERT 无此列 → 关键词被静默丢弃。结果 410 道场景题
    的 keys=[]，grading 算 hit/max(1,0)=0.0，**无论答什么都判 0 分**。
    这个测试覆盖的正是"校验通过但落库丢失"这条缝。
    """
    KP = "py.demo.scenario"

    def setUp(self):
        import tempfile
        from pyai.db.session import Database
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.tmp.name) / "t.db")
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(self.db.close)

    def test_keywords_persist_and_grade_correctly(self):
        import json
        from pyai.learning.grading import grade

        payload = json.dumps([{
            "type": "scenario", "stem": "线上超时如何排查？",
            "required_keywords": ["监控", "日志", "瓶颈"],
            "explanation": "先看监控与日志，定位瓶颈。", "error_tag": "概念混淆",
        }])
        qs = generate_quiz(_ScriptedLLM(payload), {"id": self.KP, "title": "t"}, n_variants=1)
        self.assertEqual(len(qs), 1)

        self.db.save_questions(self.KP, qs, source="generated")
        back = self.db.questions_for(self.KP)

        self.assertEqual(back[0]["required_keywords"], ["监控", "日志", "瓶颈"],
                         "关键词在落库/取回链路里丢了——场景题会永远判 0 分")
        self.assertTrue(grade(back[0], "先看监控和日志，找到瓶颈").correct)
        self.assertFalse(grade(back[0], "不知道").correct)

    def test_scenario_without_keywords_is_rejected(self):
        """没有关键词的场景题判分恒为 0，必须在入口丢弃而不是入库。"""
        import json
        payload = json.dumps([{
            "type": "scenario", "stem": "题", "explanation": "因为", "error_tag": "概念混淆",
        }])
        self.assertEqual(generate_quiz(_ScriptedLLM(payload), {"id": self.KP, "title": "t"}), [])


if __name__ == "__main__":
    unittest.main()
