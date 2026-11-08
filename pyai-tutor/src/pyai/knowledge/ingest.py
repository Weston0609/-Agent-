"""知识摄取 —— 拉取白名单权威源变更（更新管道阶段 1 的数据来源）。

离线零 token：日常学习不触达这里；只有 `pyai update` / bootstrap 从这里拉变更 chunk。
只用标准库 urllib，不引入抓取框架；白名单外的域名一律跳过（W2 D1）。
"""
from __future__ import annotations

import hashlib
import html as html_lib
import logging
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime, parsedate_to_datetime
from pathlib import Path

import yaml

log = logging.getLogger(__name__)

USER_AGENT = "pyai-tutor/1.0 (offline-learning; update-only)"
TIMEOUT = 20
MAX_CHUNK_CHARS = 4000
RATE_LIMIT_SECONDS = 1.0      # 同站点两次请求的最小间隔（抓取自律）

_STRIP = re.compile(r"<(script|style|nav|footer|head)[^>]*>.*?</\1>", re.S | re.I)
_TAGS = re.compile(r"<[^>]+>")
_RUNS = re.compile(r"[ \t\r\f\v]+")
_BLANKS = re.compile(r"\n{3,}")


def load_whitelist(sources_path: Path | str | None = None) -> dict:
    """读 sources.yaml 白名单；缺文件时返回空白名单（= 不抓任何源，不静默放行）。"""
    if sources_path is None:
        from ..config import Config
        sources_path = Config().sources_path
    path = Path(sources_path)
    if not path.exists():
        log.warning("白名单文件不存在：%s，本轮不抓取", path)
        return {"domains": [], "seeds": [], "missing_citation_policy": "warn"}
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    data.setdefault("domains", [])
    data.setdefault("seeds", [])
    data.setdefault("missing_citation_policy", "warn")
    return data


def host_allowed(url: str, domains: list[str]) -> bool:
    host = (urllib.parse.urlsplit(url).hostname or "").lower()
    return any(host == d.lower() or host.endswith("." + d.lower()) for d in domains)


_ROBOTS: dict[str, urllib.robotparser.RobotFileParser | None] = {}


def robots_allows(url: str, user_agent: str = USER_AGENT) -> bool:
    """查 robots.txt（按站点缓存一次）。取不到时按「允许」处理，与主流爬虫一致。"""
    parts = urllib.parse.urlsplit(url)
    root = f"{parts.scheme}://{parts.netloc}"
    if root not in _ROBOTS:
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(f"{root}/robots.txt")
        try:
            rp.read()
        except (urllib.error.URLError, OSError, ValueError) as e:
            log.warning("robots.txt 取不到（%s）：%s，按允许处理", root, e)
            rp = None
        _ROBOTS[root] = rp
    rp = _ROBOTS[root]
    return True if rp is None else rp.can_fetch(user_agent, url)


def html_to_text(markup: str) -> str:
    text = _STRIP.sub(" ", markup)
    text = _TAGS.sub(" ", text)
    text = html_lib.unescape(text)      # 命名实体与 &#8212; 这类数字实体都还原
    text = _RUNS.sub(" ", text)
    return _BLANKS.sub("\n\n", text).strip()


def _title_of(html: str, url: str) -> str:
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
    return (html_to_text(m.group(1))[:120] if m else "") or url


def _chunks(text: str, size: int = MAX_CHUNK_CHARS) -> list[str]:
    """按段落切分，尽量不超过 size 字符。"""
    out: list[str] = []
    buf = ""
    for para in text.split("\n\n"):
        if buf and len(buf) + len(para) + 2 > size:
            out.append(buf.strip())
            buf = ""
        buf += para + "\n\n"
    if buf.strip():
        out.append(buf.strip())
    return out


def _fetch(url: str, since: datetime) -> tuple[str, datetime | None] | None:
    """GET 一个 URL；HTTP 304 或失败返回 None。成功返回 (html, last_modified)。"""
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "If-Modified-Since": format_datetime(since, usegmt=True),
    })
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            raw = resp.read()
            lm = resp.headers.get("Last-Modified")
    except urllib.error.HTTPError as e:
        if e.code != 304:
            log.warning("抓取失败 %s：HTTP %s", url, e.code)
        return None
    except (urllib.error.URLError, OSError, ValueError) as e:
        log.warning("抓取失败 %s：%s", url, e)
        return None
    try:
        lm_dt = parsedate_to_datetime(lm) if lm else None
    except (TypeError, ValueError):
        lm_dt = None
    return raw.decode("utf-8", errors="replace"), lm_dt


def crawl_whitelisted(since_days: int = 7, max_pages: int = 20,
                      sources_path: Path | str | None = None) -> list[dict]:
    """拉取白名单源中「近期有变更」的页面，返回 chunk 列表。

    每项 {url, hash, title, content, version, fetched_at}。hash = 正文 sha256 前 16 位，
    交给 Database.has_changed() 做增量去重（W2 D3）；version 交给 save_kp 记录来源版本。
    网络请求只发生在这里，且只在 update 管道阶段 1 调用 → 日常学习 0 请求 / 0 token。
    """
    cfg = load_whitelist(sources_path)
    domains, seeds = cfg["domains"], cfg["seeds"]
    since = datetime.now(timezone.utc) - timedelta(days=max(0, since_days))
    chunks: list[dict] = []
    for url in seeds[:max_pages]:
        if not host_allowed(url, domains):
            log.warning("跳过白名单外 URL：%s", url)
            continue
        if not robots_allows(url):
            log.warning("robots.txt 不允许抓取：%s", url)
            continue
        got = _fetch(url, since)
        time.sleep(RATE_LIMIT_SECONDS)      # 抓完就歇，别把人家打疼
        if got is None:
            continue
        html, last_modified = got
        if last_modified is not None and last_modified < since:
            continue
        text = html_to_text(html)
        if not text:
            continue
        title = _title_of(html, url)
        fetched_at = datetime.now().isoformat(timespec="seconds")
        for i, part in enumerate(_chunks(text)):
            chunks.append({
                "url": f"{url}#{i}" if i else url,
                "hash": hashlib.sha256(part.encode("utf-8")).hexdigest()[:16],
                "title": title,
                "content": part,
                "version": 1,
                "fetched_at": fetched_at,
            })
    log.info("抓取完成：白名单域名 %d，种子 %d，产出 chunk %d", len(domains), len(seeds), len(chunks))
    return chunks
