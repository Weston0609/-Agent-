"""代码示例逐句讲解（codesplain）回归测试。

这组测试盯住三类真实事故：
  1. 拆分把三引号逐行拆成「普通语句」；
  2. try 链把后面平级的语句一起吞掉（曾吞掉 22 行）；
  3. 说明编造代码里没有的事实。
"""
import sqlite3
import unittest
from pathlib import Path

from src.pyai.core import codesplain

ROOT = Path(__file__).resolve().parent.parent
HTML = ROOT / "src/pyai/ui/web/templates/index.html"
DB = ROOT / "data/pyai.db"

SAMPLE = '''"""
演示：查询已安装的包。
"""
from importlib import metadata

# 1) 查询某个包是否已安装
try:
    dist = metadata.distribution("pip")
    print(dist.version)
except metadata.PackageNotFoundError:
    print("未找到")

# 2) 列出已安装的包
installed = sorted(
    (d.metadata["Name"], d.version) for d in metadata.distributions()
)
for name, version in installed[:10]:
    print(f"  {name}=={version}")
'''


class TestSplit(unittest.TestCase):
    def test_triple_quoted_block_is_one_unit(self):
        units = codesplain.explain(SAMPLE)
        docs = [u for u in units if u["code"].lstrip().startswith('"""')]
        self.assertEqual(len(docs), 1)
        self.assertEqual((docs[0]["line_start"], docs[0]["line_end"]), (1, 3))
        self.assertIn("三引号", docs[0]["syntax"])

    def test_docstring_text_becomes_the_meaning(self):
        units = codesplain.explain(SAMPLE)
        self.assertIn("查询已安装的包", units[0]["meaning"])

    def test_try_chain_does_not_swallow_following_statements(self):
        units = codesplain.explain(SAMPLE)
        try_unit = next(u for u in units if u["code"].startswith("try:"))
        self.assertEqual(try_unit["line_start"], 7)
        self.assertEqual(try_unit["line_end"], 11)          # 只到 except 体最后一行
        codes = [u["code"] for u in units]
        self.assertTrue(any(c.startswith("installed = sorted(") for c in codes),
                        "try 后面的赋值必须是独立单元")

    def test_multiline_assignment_keeps_whole_right_hand(self):
        units = codesplain.explain(SAMPLE)
        unit = next(u for u in units if u["code"].startswith("installed"))
        self.assertIn("metadata.distributions", unit["meaning"])
        self.assertNotEqual(unit["meaning"].strip(), "算出右边的值（`sorted(`），存进 `installed`。")


class TestMeaning(unittest.TestCase):
    def test_author_comment_is_used_verbatim(self):
        units = codesplain.explain(SAMPLE)
        c = next(u for u in units if u["code"].startswith("# 1)"))
        self.assertIn("查询某个包是否已安装", c["meaning"])
        self.assertIn("注释", c["syntax"])

    def test_import_and_alias_explained(self):
        units = codesplain.explain("import importlib.metadata as md\nimport sys\n")
        self.assertIn("导入并起别名", units[0]["syntax"])
        self.assertIn("md", units[0]["meaning"])
        self.assertIn("导入模块", units[1]["syntax"])

    def test_main_guard_explained(self):
        units = codesplain.explain('if __name__ == "__main__":\n    main()\n')
        self.assertIn("直接运行", units[0]["meaning"])

    def test_function_docstring_beats_guessing(self):
        code = 'def f(x: int) -> int:\n    """把 x 翻倍返回。"""\n    return x * 2\n'
        units = codesplain.explain(code)
        self.assertIn("翻倍", units[0]["meaning"])
        self.assertIn("定义函数", units[0]["syntax"])

    def test_every_unit_has_meaning_and_syntax(self):
        for u in codesplain.explain(SAMPLE):
            self.assertTrue(u["meaning"].strip())
            self.assertTrue(u["syntax"].strip())


class TestGotchasAndChecks(unittest.TestCase):
    def test_bad_patterns_are_caught(self):
        units = codesplain.explain('try:\n    x = 1\nexcept:\n    pass\n')
        self.assertTrue(any("裸 except" in g for g in units[0]["gotchas"]))

    def test_mutable_default_is_flagged(self):
        units = codesplain.explain('def f(a=[]):\n    return a\n')
        self.assertTrue(any("默认参数" in g for g in units[0]["gotchas"]))

    def test_compile_check_reports_syntax_error(self):
        self.assertIsNotNone(codesplain.compile_check("def f(:\n"))
        self.assertIsNone(codesplain.compile_check("x = 1\n"))

    def test_overview_mentions_flow(self):
        units = codesplain.explain(SAMPLE)
        self.assertIn("顺序执行", units[0]["overview"])
        self.assertIn("导入", units[0]["overview"])

    def test_empty_code_returns_none(self):
        self.assertIsNone(codesplain.explain(""))
        self.assertIsNone(codesplain.explain("   \n\n"))


class TestFrontendWiring(unittest.TestCase):
    def test_ui_renders_each_unit(self):
        html = HTML.read_text(encoding="utf-8")
        self.assertIn("codeOverview(kp)", html)
        self.assertIn("codeUnitMd(u)", html)
        self.assertIn("noSplit: true", html)      # 代码块不能被分页器切开
        self.assertIn("逐句讲解 · 第", html)
        self.assertIn("为什么这么写", html)
        self.assertIn("容易忽略", html)


def _db_openable() -> bool:
    """库文件存在不代表能打开：只读目录/沙箱下 sqlite 连 mode=ro 都会失败。

    只用 DB.exists() 当门槛的话，这种环境里整组测试会在 setUpClass 里 error，
    看起来像代码坏了。真开一次再决定跑不跑。
    """
    if not DB.exists():
        return False
    try:
        conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
        conn.execute("SELECT 1 FROM kp_content LIMIT 1").fetchone()
        conn.close()
        return True
    except sqlite3.Error:
        return False


@unittest.skipUnless(_db_openable(), "需要可读的 data/pyai.db")
class TestRealContent(unittest.TestCase):
    """拿库里真实讲义跑一遍：不许崩、不许有空说明。"""

    @classmethod
    def setUpClass(cls):
        conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        cls.rows = conn.execute(
            "SELECT kp_id, example_code FROM kp_content WHERE length(example_code) > 0"
        ).fetchall()
        conn.close()

    def test_real_examples_are_syntactically_valid(self):
        for r in self.rows:
            self.assertIsNone(codesplain.compile_check(r["example_code"]), r["kp_id"])

    def test_real_examples_all_explained(self):
        for r in self.rows:
            units = codesplain.explain(r["example_code"])
            self.assertTrue(units, r["kp_id"])
            for u in units:
                self.assertTrue(u["meaning"].strip(), f"{r['kp_id']} 第 {u['index']} 块没有说明")


if __name__ == "__main__":
    unittest.main()
