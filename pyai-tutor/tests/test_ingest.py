import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src.pyai.knowledge import ingest


class TestWhitelist(unittest.TestCase):
    """白名单是抓取的信任边界：只有白名单域名（含子域）可抓。"""

    DOMAINS = ["docs.python.org", "python.org"]

    def test_exact_and_subdomain_allowed(self):
        self.assertTrue(ingest.host_allowed("https://docs.python.org/3/tutorial/index.html", self.DOMAINS))
        self.assertTrue(ingest.host_allowed("https://python.org/", self.DOMAINS))
        self.assertTrue(ingest.host_allowed("https://blog.python.org/x", self.DOMAINS))

    def test_lookalike_and_hostless_rejected(self):
        self.assertFalse(ingest.host_allowed("https://evil-python.org/x", self.DOMAINS))
        self.assertFalse(ingest.host_allowed("https://notpython.org/x", self.DOMAINS))
        self.assertFalse(ingest.host_allowed("https://docs.python.org.evil.com/x", self.DOMAINS))
        self.assertFalse(ingest.host_allowed("file:///etc/passwd", self.DOMAINS))


class TestHtmlToText(unittest.TestCase):
    def test_strips_script_style_and_tags_decodes_entities(self):
        markup = ("<html><head><title>T</title></head><body>"
                  "<script>evil()</script><style>p{}</style>"
                  "<p>A &amp; B</p><p>&lt;tag&gt;</p><p>&#8212;dash</p></body></html>")
        text = ingest.html_to_text(markup)
        self.assertIn("A & B", text)
        self.assertIn("<tag>", text)
        self.assertIn("—dash", text)          # 数字实体也要还原（&#8212; → —）
        self.assertNotIn("evil()", text)
        self.assertNotIn("p{}", text)
        self.assertNotIn("<p>", text)

    def test_title_falls_back_to_url(self):
        self.assertEqual(ingest._title_of("<html><title> 好标题 </title></html>", "u"), "好标题")
        self.assertEqual(ingest._title_of("<html></html>", "https://x/y"), "https://x/y")


class TestChunks(unittest.TestCase):
    def test_splits_on_paragraphs_and_keeps_short_text(self):
        self.assertEqual(ingest._chunks("aaaaa\n\nbbbbb", size=8), ["aaaaa", "bbbbb"])
        self.assertEqual(ingest._chunks("short", size=100), ["short"])
        self.assertEqual(ingest._chunks("   \n\n  "), [])


class TestLoadWhitelistAndCrawl(unittest.TestCase):
    def test_missing_file_yields_empty_whitelist(self):
        missing = Path(tempfile.gettempdir()) / "pyai-no-such-sources.yaml"
        wl = ingest.load_whitelist(missing)
        self.assertEqual(wl["domains"], [])
        self.assertEqual(wl["seeds"], [])

    def test_shipped_sources_seeds_are_all_whitelisted(self):
        wl = ingest.load_whitelist()
        self.assertTrue(wl["domains"])
        self.assertTrue(wl["seeds"])
        for url in wl["seeds"]:
            self.assertTrue(ingest.host_allowed(url, wl["domains"]), url)

    def test_crawl_skips_seeds_outside_whitelist_without_network(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "sources.yaml"
            p.write_text("domains: [docs.python.org]\nseeds: ['https://evil.example.com/x']\n",
                         encoding="utf-8")
            self.assertEqual(ingest.crawl_whitelisted(sources_path=p), [])

    def test_robots_failure_fails_open_and_is_cached(self):
        ingest._ROBOTS.clear()
        with mock.patch.object(ingest.urllib.robotparser.RobotFileParser, "read",
                               side_effect=OSError("no net")) as read:
            self.assertTrue(ingest.robots_allows("https://docs.python.org/3/"))
            self.assertTrue(ingest.robots_allows("https://docs.python.org/3/library/asyncio.html"))
        self.assertEqual(read.call_count, 1, "robots.txt 应按站点缓存，只取一次")
        ingest._ROBOTS.clear()


if __name__ == "__main__":
    unittest.main()
