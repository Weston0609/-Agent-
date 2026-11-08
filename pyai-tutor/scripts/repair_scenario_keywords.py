"""场景题关键词修复：从已有的 explanation（模型给出的标准答案）回填 required_keywords。

背景（真 bug）：`questions.required_keywords` 列在 410 道场景题生成时并不存在，
`_is_wellformed` 校验的是内存里的 dict（通过），但 INSERT 没这一列 → 关键词被静默丢弃。
后果：`grading.grade()` 对场景题算 `hit/max(1,len(keys))` = `0/1` = 0.0，
这 410 道题**无论答什么都判 0 分**。

修复策略：不重新烧 token 生成。场景题的 explanation 就是模型写出的标准答案，
从中抽取领域术语作为关键词即可——离线、0 token、可重复执行。

用法：
    python -X utf8 scripts/repair_scenario_keywords.py --dry-run   # 只看抽到什么
    python -X utf8 scripts/repair_scenario_keywords.py             # 写库
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from pyai.db.session import Database  # noqa: E402

# 英文/标识符术语：Decimal、math.isclose、assert、float 等，长度 >= 3 避开 a/of 之类噪声
_EN = re.compile(r"[A-Za-z_][A-Za-z0-9_]{2,}(?:\.[A-Za-z_][A-Za-z0-9_]*)*")

# 高频技术名词表：中文关键词无法靠形态切分，用受控词表命中。
# 只收「答案里出现就该算答对」的领域术语，不含「应该/需要」这类通用词。
_ZH_TERMS = [
    "最小化", "去标识化", "脱敏", "加密", "显式同意", "可撤回", "保留期限", "审计",
    "数据处理协议", "权限", "访问控制", "身份认证", "鉴权", "隔离", "沙箱",
    "幂等", "原子性", "事务", "索引", "缓存", "限流", "熔断", "降级", "重试",
    "背压", "并发", "并行", "异步", "协程", "锁", "死锁", "竞态",
    "容差", "浮点", "精度", "舍入", "十进制", "整数分", "溢出", "边界",
    "监控", "日志", "告警", "追踪", "指标", "可观测",
    "备份", "容灾", "灰度", "回滚", "版本", "迁移", "兼容",
    "压测", "基准", "性能分析", "瓶颈", "复杂度", "内存", "泄漏",
    "分层", "解耦", "抽象", "接口", "契约", "依赖注入", "单例", "工厂",
    "隐私", "合规", "最小权限", "分片", "复制", "一致性", "可用性",
]

# 通用词黑名单：出现频率高但不构成「答对」的证据。
# 也滤掉示例字面量（report.txt / A2B3C / line 这类）——它们是题干里的样本数据，
# 学生答对概念却不照抄字面量就会被误判，不能当关键词。
_STOP = {"应该", "可以", "需要", "使用", "进行", "如果", "因为", "所以", "以及",
         "并且", "或者", "问题", "方案", "做法", "原因", "情况", "时候",
         "new", "the", "and", "for", "with", "not", "but", "you", "your",
         "line", "file", "text", "test", "value", "list", "dict", "str",
         "int", "len", "print", "code", "data", "time", "name",
         "report", "result", "output", "input", "item", "case", "type"}

# 纯 ASCII 且无点号的短词多半是示例数据（A2B3C、report.txt 的基名）而非 API 名。
# 判据从严：只有「异常类名 / 带点号的调用形式 / 受控词表里的库名」才算术语。
# 示例字面量（A2B3C、report.txt）无论长得像什么都不是概念，必须滤掉——
# 学生答对概念却不照抄字面量就会被误判。
_KNOWN_LIBS = {
    "decimal", "math", "pytest", "assert", "float", "int", "str", "list", "dict",
    "set", "tuple", "json", "re", "os", "sys", "logging", "threading", "asyncio",
    "sqlite3", "urllib", "subprocess", "pathlib", "dataclass", "typing", "enum",
    "functools", "itertools", "collections", "datetime", "time", "random", "hashlib",
    "redis", "kafka", "docker", "kubernetes", "pytorch", "torch", "numpy", "pandas",
    "fastapi", "pydantic", "sqlalchemy", "git", "http", "https", "ssl", "tls",
    "cpu", "gpu", "ram", "json", "yaml", "csv", "xml", "html", "api", "sdk", "url",
}


def _is_meaningful_en(term: str) -> bool:
    """英文术语是否值得当关键词：排除示例字面量，只收真术语。"""
    low = term.lower()
    if low in _STOP or len(term) < 3:
        return False
    # 异常/告警类名：ValueError、IndexError、RuntimeWarning
    if re.fullmatch(r"[A-Z][A-Za-z]*(?:Error|Warning|Exception|Iterable|Iterator)", term):
        return True
    # 带点号的调用形式：math.isclose / pytest.approx / decimal.Decimal
    # 注意排除文件/域名样式（report.txt、config.json）——点号后是已知数据扩展名即为字面量
    if "." in term:
        parts = term.split(".")
        if parts[-1].lower() in {"txt", "json", "csv", "xml", "yaml", "yml", "log",
                                 "py", "md", "html", "db", "sql", "ini", "toml"}:
            return False
        head = parts[0].lower()
        return head in _KNOWN_LIBS or parts[-1][:1].islower()
    # 受控词表里的库/概念名
    if low in _KNOWN_LIBS:
        return True
    # 全大写缩写（CPU/HTTP）且非混合数字
    if term.isupper() and 2 <= len(term) <= 6 and not any(ch.isdigit() for ch in term):
        return True
    # 其余一律不收：report.txt / A2B3C / line / new 都是示例数据或通用词
    return False


def extract_keywords(explanation: str, limit: int = 6) -> list[str]:
    """从标准答案抽关键词。英文术语优先，再补中文领域词；去重保序。"""
    text = explanation or ""
    out: list[str] = []
    seen: set[str] = set()

    for m in _EN.finditer(text):
        term = m.group(0)
        low = term.lower()
        if low in seen or not _is_meaningful_en(term):
            continue
        seen.add(low)
        out.append(term)
        if len(out) >= limit:
            return out

    for term in _ZH_TERMS:
        if len(out) >= limit:
            break
        if term in text and term not in seen:
            seen.add(term)
            out.append(term)

    return out


_LLM_PROMPT = """下面是一道工程场景题的题干与标准答案。请给出 3-5 个「必须出现在正确回答里」
的关键词/术语，用于自动判分。

要求：
- 只给术语本身，不要解释、不要编号、不要标点。
- 术语应是领域概念（如 `监控`、`decimal.Decimal`、`索引`），
  **不要**题干里的示例数据/变量名/文件名（如 `report.txt`、`A2B3C`）。
- 一个术语一行。

题干：{stem}

标准答案：{explanation}

关键词："""


def repair_with_llm(db, llm, rows, apply: bool = True) -> dict:
    """对关键词过弱（<2 个）的场景题，用模型补关键词。返回统计。"""
    import re as _re

    ok = failed = 0
    for r in rows:
        prompt = _LLM_PROMPT.format(stem=(r["stem"] or "")[:600],
                                    explanation=(r["explanation"] or "")[:800])
        try:
            raw = llm.chat(prompt) or ""
        except Exception as exc:                      # 网络/余额问题不该中断整批
            print(f"  ! {r['id']}: {exc}")
            failed += 1
            continue
        keys = [ln.strip().lstrip("-•*0123456789. ").strip()
                for ln in raw.splitlines()]
        keys = [k for k in keys if k and 1 < len(k) <= 40 and not k.endswith("：")]
        if not keys:
            failed += 1
            continue
        keys = keys[:5]
        ok += 1
        if apply:
            db._conn.execute("UPDATE questions SET required_keywords=? WHERE id=?",
                             (json.dumps(keys, ensure_ascii=False), r["id"]))
            db._conn.commit()
        if ok <= 5:
            print(f"  {r['id']:<36} {keys}")
    return {"ok": ok, "failed": failed}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(ROOT / "data" / "pyai.db"))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--llm", action="store_true",
                    help="关键词不足 2 个的题改用模型补（烧 token）")
    ap.add_argument("--limit", type=int, default=0, help="限制处理条数（控花费）")
    args = ap.parse_args()

    db = Database(args.db)
    # 待修复 = 关键词为空 **或** 过弱（<2 个）。单词命中意味着蒙对一个词就满分，
    # 判分不可靠，同样要交给模型补。
    rows = db._conn.execute(
        "SELECT id, stem, explanation, required_keywords FROM questions "
        "WHERE type='scenario' AND (required_keywords IS NULL "
        "  OR TRIM(required_keywords) IN ('','[]') "
        "  OR (LENGTH(TRIM(required_keywords)) - LENGTH(REPLACE(TRIM(required_keywords), ',', '')) < 1))"
    ).fetchall()
    print(f"待修复场景题：{len(rows)}（空关键词 或 仅 1 个）")

    fixed = empty = 0
    weak: list = []
    samples = []
    for r in rows:
        keys = extract_keywords(r["explanation"] or "")
        if not keys:
            empty += 1
            weak.append(r)
            continue
        if len(keys) < 2:
            weak.append(r)                # 单词命中 = 蒙对就满分，也算不可靠
        fixed += 1
        if len(samples) < 8:
            samples.append((r["id"], keys))
        if not args.dry_run:
            db._conn.execute(
                "UPDATE questions SET required_keywords=? WHERE id=?",
                (json.dumps(keys, ensure_ascii=False), r["id"]),
            )

    if not args.dry_run:
        db._conn.commit()

    for qid, keys in samples:
        print(f"  {qid:<36} {keys}")
    print(f"\n离线抽出关键词：{fixed}   抽不出：{empty}   判分不可靠（<2 个）合计：{len(weak)}")

    if args.llm and weak:
        from pyai.config import Config
        from pyai.updater.pipeline import select_llm
        cfg = Config.from_env()
        llm, backend = select_llm(cfg)
        if not llm.configured:
            print("无可用后端（设 DEEPSEEK_API_KEY 或起 Ollama），跳过模型补词")
        else:
            todo = weak[:args.limit] if args.limit else weak
            print(f"\n用 {backend} 补关键词（{len(todo)} 条）…")
            res = repair_with_llm(db, llm, todo, apply=not args.dry_run)
            print(f"模型补词：成功 {res['ok']}  失败 {res['failed']}")

    if args.dry_run:
        print("（--dry-run，未写库）")
    db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
