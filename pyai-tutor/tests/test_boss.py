"""打 Boss —— 随堂测变聊天对战。

守住用户点名要的四条规则：
① 正确率 ≥ 85% 才算合格（比单元考线 75% 严）；
② 重来换一批没打过的题（题库用完才允许重复）；
③ 战况（血量/回合/连击）落库，刷新页面不重置；
④ 题面不下发答案（含场景题关键词＝答案）。
"""
import tempfile
import unittest
from pathlib import Path

from src.pyai.config import Config
from src.pyai.core.orchestrator import Orchestrator
from src.pyai.db.session import BOSS_PASS
from src.pyai.learning.grading import model_answer

_CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"


class TestBoss(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        cfg = Config(data_dir=Path(self._tmp.name) / "data", content_dir=_CONTENT_DIR)
        self.orch = Orchestrator(cfg)

    def tearDown(self):
        self.orch.close()
        self._tmp.cleanup()

    def _answer_for(self, view: dict) -> str:
        """取当前题的满分作答。"""
        real = self.orch.db.questions_by_ids([view["question"]["id"]])[0]
        return model_answer(real)

    def _fight(self, wrong_first: int = 0) -> dict:
        """打完整场：前 wrong_first 题故意答错，其余满分。"""
        view = self.orch.boss_start()
        i = 0
        while not view.get("finished"):
            answer = "肯定错的答案" if i < wrong_first else self._answer_for(view)
            view = self.orch.boss_hit(answer)
            i += 1
        return view

    def test_boss_line_is_85_percent(self):
        """错 1/12 = 91.7% 应过关。"""
        self.assertEqual(BOSS_PASS, 0.85)
        win = self._fight(wrong_first=1)
        self.assertGreater(win["barrage"], BOSS_PASS)
        self.assertTrue(win["verdict"]["passed"], "91.7% 应当过关")
        self.assertEqual(self.orch.status()["next_lesson"], "s1u1l2")

    def test_below_85_percent_does_not_unlock(self):
        """错 2/12 = 83.3% 不该过关，关卡不解锁。"""
        view = self._fight(wrong_first=2)
        self.assertLess(view["barrage"], BOSS_PASS)
        self.assertFalse(view["verdict"]["passed"], "83.3% 不该过关")
        self.assertEqual(self.orch.status()["next_lesson"], "s1u1l1")

    def test_hp_drops_to_zero_on_a_clean_win(self):
        view = self._fight()
        self.assertEqual(view["hp"], 0)
        self.assertEqual(view["barrage"], 1.0)
        self.assertEqual(view["best_combo"], view["total"])

    def test_question_never_leaks_the_answer(self):
        """题面不能带 answer / required_keywords（场景题关键词就是答案）。"""
        q = self.orch.boss_start()["question"]
        self.assertNotIn("answer", q)
        self.assertNotIn("required_keywords", q)

    def test_written_questions_carry_a_grading_hint_but_not_the_answer(self):
        """场景题/填空题必须给出「怎么判」的提示，否则空白输入框等于无解。

        这两条是一起的：既要可赢（有 answer_hint），又不能把答案发下去
        （没有 required_keywords / answer）。
        """
        view = self.orch.boss_start()
        hints = {}
        while not view.get("finished"):
            q = view["question"]
            hints[q["type"]] = q.get("answer_hint") or ""
            self.assertNotIn("answer", q)
            self.assertNotIn("required_keywords", q, "关键词是答案，任何题型都不能下发")
            view = self.orch.boss_hit("随便答一句")

        # 这份卷子里这两种需要写字的题型都得有提示才算「可作答」
        for qtype in ("scenario", "fill_blank"):
            if qtype in hints:
                self.assertTrue(hints[qtype], f"{qtype} 必须带 answer_hint，否则考生不知道答什么")

    def test_scenario_hint_reveals_no_keyword(self):
        """提示只能说「要几个要点」，绝不能把关键词本身漏出去。"""
        view = self.orch.boss_start()
        # 打完所有回合仍没有场景题时 question 是 None，这不是失败，只是这份卷子没这种题型。
        while not view.get("finished") and (view.get("question") or {}).get("type") != "scenario":
            view = self.orch.boss_hit("随便答一句")
        q = view.get("question") or {}
        if q.get("type") != "scenario":
            self.skipTest("这份卷子没有场景题")
        real = self.orch.db.questions_by_ids([q["id"]])[0]
        hint = q.get("answer_hint") or ""
        for kw in (real.get("required_keywords") or []):
            kw = str(kw).strip()
            if len(kw) >= 3:                     # 太短的关键词（如「非」）本来就可能出现在正常句子里
                self.assertNotIn(kw.lower(), hint.lower(),
                                 f"提示里泄露了采分关键词 {kw!r}")

    def test_every_question_is_answerable(self):
        """每道题都必须渲染出一个能提交的控件——这是「有些题不显示、无法作答」的回归线。

        前端的规则（index.html bossControl）：有 options 就渲染选项，没有就渲染输入框，
        并要求后端给出 answer_hint。这里用同一套规则逐题核对整份卷子：
        code_reading 曾经被写死成「渲染 options 里的单选」，而题库里它 486 道全无 options，
        于是渲染出零个控件、提交被拦，整题不可答。
        """
        view = self.orch.boss_start()
        while not view.get("finished"):
            q = view["question"]
            opts = q.get("options") or []
            if not opts:
                self.assertTrue(
                    q.get("answer_hint"),
                    f"{q['type']} 题 {q['id']} 没有选项也没给提示，前端只能给一个空白输入框",
                )
            if q["type"] == "code_reading" and not opts:
                # 无选项的 code_reading 走文字作答，必须真的判得动，不能一提交就 0 分
                real = self.orch.db.questions_by_ids([q["id"]])[0]
                self.assertIsInstance(real.get("answer"), str,
                                      "无选项的 code_reading 参考答案应为自然语言，才能按文字判分")
                view = self.orch.boss_hit(model_answer(real))
                self.assertTrue(view["hit"]["perfect"],
                                f"照标准答案作答却判错：{view['hit'].get('feedback')}")
                continue
            view = self.orch.boss_hit("随便答一句")

    def test_fight_survives_a_refresh(self):
        """刷新页面（重新 boss_start）不该重置血量与回合。"""
        self.orch.boss_start()
        view = self.orch.boss_hit("肯定错的答案")
        hp, rnd = view["hp"], view["round"]
        again = self.orch.boss_start()
        self.assertEqual(again["hp"], hp, "刷新后血量应保持")
        self.assertEqual(again["round"], rnd, "刷新后回合数应保持")

    def test_retake_swaps_in_unseen_questions(self):
        """没打过 → 重开一局的第一题必须是没打过的题。"""
        first = self._fight(wrong_first=99)
        self.assertFalse(first["verdict"]["passed"])
        used = self.orch.db.unused_question_ids(self.orch.user_id, first["lesson_id"])
        self.assertTrue(used, "打了一场就该留下消费账")
        second = self.orch.boss_start()
        self.assertNotIn(second["question"]["id"], used, "重开后不该再抽到打过的题")

    def test_boss_restart_resets_hp_and_round(self):
        """boss_restart 必须收掉旧战况、回满血、回到回合 1（否则重开等于续打）。"""
        self.orch.boss_start()
        self.orch.boss_hit("肯定错的答案")
        self.orch.boss_hit("还是错的")
        fresh = self.orch.boss_restart()
        self.assertEqual(fresh["round"], 0, "重开后回合数应归零")
        self.assertEqual(fresh["hp"], fresh["max_hp"], "重开后应回满血")
        self.assertEqual(fresh["combo"], 0, "重开后连击应归零")
        self.assertFalse(fresh.get("finished"), "重开后不该是已结束状态")


if __name__ == "__main__":
    unittest.main()
