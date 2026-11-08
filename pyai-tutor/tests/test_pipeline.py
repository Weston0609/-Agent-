import tempfile
import unittest
from pathlib import Path

from src.pyai.db.session import MIN_LECTURE_CHARS, Database
from src.pyai.learning.curriculum import load_curriculum
from src.pyai.updater.pipeline import run_weekly_update

_CURRICULUM_PATH = Path(__file__).resolve().parent.parent / "curriculum" / "full_curriculum.yaml"
CURRICULUM = load_curriculum(str(_CURRICULUM_PATH))


def _no_crawl(since_days: int = 7) -> list:
    """测试不发网络请求：抓取器注入为空。（真抓取见 tests/test_ingest.py）"""
    return []


class FakeLLM:
    """接口与 DeepSeekClient/OllamaClient 对齐的假模型：记下收到的 prompt，返回脚本化 JSON。"""

    def __init__(self, replies: list[str] | None = None) -> None:
        self.prompts: list[str] = []
        self.last_tokens = 0
        self._replies = list(replies or [])

    @property
    def configured(self) -> bool:
        return True

    def chat(self, prompt: str, system: str | None = None) -> str:
        self.prompts.append(prompt)
        return self._replies.pop(0) if self._replies else "{}"


class TestUpdatePipeline(unittest.TestCase):
    """更新管道：生成队列来自「尚无内容的 KP」；无 key 时一个 token 也不烧。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self._tmp.name) / "test.db")
        self.db.seed_curriculum(CURRICULUM)

    def tearDown(self):
        self.db.close()
        self._tmp.cleanup()

    def test_find_unfilled_kps_is_bounded_ordered_and_excludes_filled(self):
        ids = [k["kp_id"] for k in self.db.find_unfilled_kps(limit=3)]
        self.assertEqual(len(ids), 3)
        self.assertEqual(ids[0], self.db.all_kps_in_order()[0].id)   # 按课程顺序

        # 只有「讲得完」的讲义才算填充：几十字的占位文必须留在队列里重讲。
        # 手写种子每个 KP 就这么几十字，若把它当已填充，那一课永远停在占位文上，
        # 而题库照常按完整知识点生成——学生看到的就是「随堂测考的都是没教过的」。
        self.db.save_kp_content(ids[0], explain="几十字的占位文")
        self.assertEqual([k["kp_id"] for k in self.db.find_unfilled_kps(limit=1)], [ids[0]])

        self.db.save_kp_content(ids[0], explain="正" * MIN_LECTURE_CHARS)
        remaining = [k["kp_id"] for k in self.db.find_unfilled_kps(limit=1)]
        self.assertEqual(remaining, [ids[1]])

    def test_run_weekly_update_without_key_burns_nothing(self):
        result = run_weekly_update(self.db, manual=True, crawler=_no_crawl)
        self.assertEqual(result["status"], "skipped_no_key")
        self.assertEqual(result["tokens_used"], 0)
        self.assertEqual(result["kps_added"], 0)

        row = self.db._conn.execute(
            "SELECT status, tokens_used FROM updates_log"
        ).fetchone()
        self.assertEqual(row["status"], "skipped_no_key")
        self.assertEqual(row["tokens_used"], 0)

    def test_kp_generation_prompt_comes_from_template_with_prereq(self):
        """阶段 2 的 prompt 必须是渲染过的 tutor.jinja（含前置知识点），不是裸标题。"""
        kp = self.db.find_unfilled_kps(limit=1)[0]
        self.db.save_kp_content(kp["prereq"] and kp["prereq"][0] or "x", explain="占位")
        llm = FakeLLM(['{"explain": "讲解", "example_code": "print(1)", "pitfalls": "", "sources": []}',
                       "[]"])
        result = run_weekly_update(self.db, manual=True, crawler=_no_crawl, llm=llm,
                                   max_kps=1)
        self.assertEqual(result["kps_added"], 1)

        gen_prompt = llm.prompts[0]
        self.assertIn("资深 Python 与 AI 架构师导师", gen_prompt)   # 模板正文进来了
        self.assertIn(f"知识点 ID：{kp['kp_id']}", gen_prompt)
        self.assertIn("前置知识点：", gen_prompt)
        self.assertIn("请严格返回 JSON", gen_prompt)               # JSON 契约仍然拼在后面

        quiz_prompt = llm.prompts[1]
        self.assertIn("请为下列知识点生成 20 道测验题", quiz_prompt)
        self.assertIn("题型配比", quiz_prompt)                     # 要求混合题型

    def test_backfill_quiz_adds_questions_without_touching_lecture(self):
        """补题模式：只换题库，讲义必须一字不改（手写种子每 KP 仅 1 题）。"""
        kp_id = self.db.find_unfilled_kps(limit=1)[0]["kp_id"]
        self.db.save_kp_content(kp_id, explain="原始讲义，不可被覆盖")
        self.db.save_questions(kp_id, [{"type": "single_choice", "stem": "旧题",
                                        "options": ["a", "b"], "answer": 0}])
        self.assertEqual(len(self.db.questions_for(kp_id)), 1)

        # 造 5 道新题；标题字段空时回落到 kp_id
        new_qs = [{"type": "single_choice", "stem": f"新题 {i}",
                   "options": ["a", "b", "c", "d"], "answer": 1,
                   "explanation": "解析", "error_tag": "概念混淆"} for i in range(5)]
        import json as _json
        llm = FakeLLM([_json.dumps(new_qs, ensure_ascii=False)])

        result = run_weekly_update(self.db, manual=True, llm=llm, max_kps=1,
                                   backfill_quiz=True, min_questions=6)

        self.assertEqual(result["kps_added"], 1)
        self.assertEqual(len(self.db.questions_for(kp_id)), 5)          # 题库已换新
        self.assertTrue(self.db.questions_for(kp_id)[0]["stem"].startswith("新题"))
        content = self.db.get_kp_content(kp_id)
        self.assertEqual(content.explain, "原始讲义，不可被覆盖")        # 讲义未被触碰
        self.assertNotIn("资深 Python 与 AI 架构师导师", llm.prompts[0])  # 没走生成讲义那条路
        self.assertIn("请为下列知识点生成 20 道测验题", llm.prompts[0])

    def test_thin_quiz_kps_excludes_well_stocked_and_filled(self):
        """补题队列只收「有讲义但题少」的 KP。"""
        ids = self.db.all_kps_in_order()
        a, b = ids[0].id, ids[1].id
        self.db.save_kp_content(a, explain="讲义 A")           # 有讲义、0 题 -> 入选
        self.db.save_kp_content(b, explain="讲义 B")           # 有讲义、20 题 -> 排除
        self.db.save_questions(b, [{"type": "single_choice", "stem": f"q{i}",
                                    "options": ["a", "b"], "answer": 0} for i in range(20)])

        thin = [k["kp_id"] for k in self.db.find_thin_quiz_kps(min_questions=6, limit=10)]
        self.assertIn(a, thin)
        self.assertNotIn(b, thin)

    def test_seed_content_does_not_clobber_generated_content(self):
        """种子只在空缺处写入：生成内容优先，否则每次启动都会被打回种子原样。

        这是本项目最严重的一类回归——update 管道烧 token 生成的讲义与题库，
        会被 Orchestrator 构造时的 seed_content() 无声覆盖（含 DELETE-then-INSERT 题库）。
        """
        from src.pyai.db.seed_content import seed_content

        kp_id = self.db.all_kps_in_order()[0].id
        # 先按「生成」写入 20 道题 + 讲义
        self.db.save_kp_content(kp_id, explain="模型生成的讲义", source="generated")
        self.db.save_questions(kp_id, [{"type": "single_choice", "stem": f"生成题 {i}",
                                        "options": ["a", "b"], "answer": 0} for i in range(20)],
                               source="generated")
        src = Path(__file__).resolve().parent.parent / "content"
        if not (src / "lessons").exists() or not list((src / "lessons").glob("*.json")):
            self.skipTest("无 content/lessons 种子可测")

        seed_content(self.db, src)      # 模拟每次 Orchestrator 启动

        self.assertEqual(self.db.kp_content_source(kp_id) if
                         self.db.kp_content_source(kp_id) else "generated", "generated")
        self.assertEqual(self.db.get_kp_content(kp_id).explain, "模型生成的讲义")
        qs = self.db.questions_for(kp_id)
        self.assertEqual(len(qs), 20)                    # 20 道生成题没被打回 1 道
        self.assertTrue(all(q["stem"].startswith("生成题") for q in qs))


class TestEmptyContentGuard(unittest.TestCase):
    """空讲义必须报错、不得写库（曾出现 explain='' 却 verified=1、计入 added）。"""

    def test_generate_kp_content_raises_on_empty_explain(self):
        import json as _json
        from src.pyai.updater.kp_generator import GenerationError, generate_kp_content
        llm = FakeLLM([_json.dumps({"explain": "   ", "example_code": "print(1)"})])
        with self.assertRaises(GenerationError):
            generate_kp_content(llm, {"id": "py.x", "title": "py.x"})

    def test_pipeline_skips_empty_kp_without_writing_row(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        db = Database(Path(tmp.name) / "t.db")
        self.addCleanup(db.close)
        db.seed_curriculum(CURRICULUM)
        kp_id = db.find_unfilled_kps(limit=1)[0]["kp_id"]

        import json as _json
        llm = FakeLLM([_json.dumps({"explain": ""})])      # 空讲义
        result = run_weekly_update(db, manual=True, crawler=_no_crawl, llm=llm, max_kps=1)

        self.assertEqual(result["kps_added"], 0)           # 不算生成成功
        self.assertEqual(result["kps_skipped"], 1)         # 而是跳过
        self.assertIsNone(db.get_kp_content(kp_id))        # 库里没有空行


class TestQuizStemGuard(unittest.TestCase):
    """题干不得把内部 kp_id 当代码吐出来（实测 18.9% 的生成题如此，会教错）。"""

    def test_generate_quiz_drops_stems_leaking_kp_id(self):
        import json as _json
        from src.pyai.updater.kp_generator import generate_quiz
        kp = {"id": "py.env.install", "title": "py.env.install"}
        raw = [
            {"stem": "在 py.env.install 模块中，install() 函数的作用是？",
             "options": ["a", "b", "c", "d"], "answer": 0,
             "explanation": "解析", "error_tag": "概念混淆"},          # 泄漏 -> 丢
            {"stem": "安装 Python 包时，指定版本的常用做法是？",
             "options": ["a", "b", "c", "d"], "answer": 1,
             "explanation": "解析", "error_tag": "概念混淆"},          # 正常 -> 留
            {"stem": "调用 py.env.install.install(packages=[]) 会怎样？",
             "options": ["a", "b", "c", "d"], "answer": 2,
             "explanation": "解析", "error_tag": "概念混淆"},          # 泄漏 -> 丢
        ]
        out = generate_quiz(FakeLLM([_json.dumps(raw, ensure_ascii=False)]), kp)
        self.assertEqual(len(out), 1)
        self.assertIn("指定版本", out[0]["stem"])
        self.assertTrue(out[0]["id"].startswith("py.env.install-q"))   # id 仍补齐
        self.assertEqual(out[0]["kp_id"], "py.env.install")

    def test_quiz_gen_template_forbids_using_kp_id_as_api(self):
        from src.pyai.updater.kp_generator import _render
        prompt = _render(None, "quiz_gen.jinja", n=20,
                         kp_id="py.env.install", title="py.env.install")
        self.assertIn("禁止编造 API", prompt)
        self.assertIn("不是** Python", prompt.replace("**", "**"))
        self.assertIn("严禁", prompt)


class TestSourceMigration(unittest.TestCase):
    """source 列对账：老库缺列时按题 id 形状回填，且每次启动幂等重跑。"""

    def test_migration_backfills_source_from_question_id_shape(self):
        import sqlite3
        from src.pyai.db import session as _session
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "old.db"
        con = sqlite3.connect(path)
        con.executescript(_session._SCHEMA)
        con.execute("INSERT INTO semesters (id, name, \"order\") VALUES ('s1','一',1)")
        con.execute("INSERT INTO units (id, semester_id, name, \"order\") VALUES ('u1','s1','U',1)")
        con.execute("INSERT INTO lessons (id, unit_id, name, \"order\") VALUES ('l1','u1','L',1)")
        con.execute("INSERT INTO kps (id, lesson_id, title, \"order\") VALUES ('k1','l1','K',1)")
        # 最老的一版：连 source 列都没有，题 id 已带形状信息
        con.execute("INSERT INTO questions (id, kp_id, type, stem, options, answer) "
                    "VALUES ('k1-seed0','k1','single_choice','种子题','[]','0')")
        con.execute("INSERT INTO questions (id, kp_id, type, stem, options, answer) "
                    "VALUES ('k1-q0','k1','single_choice','生成题','[]','0')")
        con.commit()
        con.close()

        db = Database(path)      # 构造即触发 _migrate 对账
        db.close()               # 必须关连接，否则 Windows 下临时目录清理失败
        con = sqlite3.connect(path)
        got = dict(con.execute("SELECT id, source FROM questions").fetchall())
        con.close()
        self.assertEqual(got["k1-seed0"], "seed")           # 种子仍标 seed
        self.assertEqual(got["k1-q0"], "generated")         # 误标的生成题被纠正


if __name__ == "__main__":
    unittest.main()
