"""把 DB 里已生成的讲义与题库导出回 content/lessons/*.json（固化离线内容）。

用途：生成管道烧 token 产出的内容只落在某个 SQLite 文件里；要让它随发行版分发、
让干净部署开箱即用，必须写回种子文件。导出后 seed_content() 会把它当种子加载。

用法（在 pyai-tutor 目录下）：
    python -X utf8 scripts/export_content.py            # 只导出已有种子文件覆盖的课
    python -X utf8 scripts/export_content.py --all      # 连没有种子文件的课也生成
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.pyai.config import Config          # noqa: E402
from src.pyai.core.orchestrator import Orchestrator  # noqa: E402


def _question_to_seed(q: dict) -> dict:
    """DB 题 → 种子题格式。

    必须带上 type/explanation/error_tag/variant_group/required_keywords：
    早先只导出 {kp, question, options, answer}，回读时 seed_content 把 type 默认成
    single_choice，于是 7786 道题里的四种题型（多选/填空/代码阅读/场景）全部退化。
    """
    out = {
        "kp": q.get("kp_id"),
        "type": q.get("type", "single_choice"),
        "question": q.get("stem", ""),
        "options": q.get("options") or [],
        "answer": q.get("answer"),
        "explanation": q.get("explanation", ""),
        "error_tag": q.get("error_tag", ""),
        "variant_group": q.get("variant_group", ""),
    }
    if q.get("required_keywords"):
        out["required_keywords"] = q["required_keywords"]
    return out


def _theory_from_kps(orch, kp_ids: list[str]) -> str:
    """把一课内各 KP 的讲义拼成 Markdown，每节以 `## <kp_id>` 起头。

    标记必须原样用 kp_id：seed_content 就按 `## <kp_id>` 定位分节边界。若为了好看
    换成中文标题，回读时找不到边界，只能退回「按所有 `## ` 切」——而讲义正文自带
    `## 一句话直觉` 这类小节（385 篇里 378 篇都有），一节会碎成几十片，节数对不上
    KP 数后又退化成「每个 KP 拿整课」。kp_id 当标记还有第二个好处：回读时这行会被
    剥掉，学生不会在正文里看到 `## py.env.install` 这种机器标识。
    """
    parts = []
    for kp_id in kp_ids:
        c = orch.db.get_kp_content(kp_id)
        if not c:
            continue
        piece = f"## {kp_id}\n\n{(c.explain or '').strip()}"
        if c.example_code:
            piece += f"\n\n```python\n{c.example_code.strip()}\n```"
        parts.append(piece)
    return "\n\n".join(parts) + "\n"


def export(orch, lessons_dir: Path, all_lessons: bool, overwrite: bool) -> dict:
    lessons_dir.mkdir(parents=True, exist_ok=True)
    written = skipped = n_q = 0
    for lesson in orch.db.all_lessons_in_order():
        kp_ids = orch.db.lesson_kp_ids(lesson.id)
        path = lessons_dir / f"{lesson.id}.json"
        if path.exists() and not overwrite:
            skipped += 1
            continue
        if not all_lessons and not path.exists():
            # 只导出「本来就有种子文件」的课，避免把 178 课全铺成空壳
            skipped += 1
            continue
        questions: list[dict] = []
        for kp_id in kp_ids:
            for q in orch.db.questions_for(kp_id):
                questions.append(_question_to_seed(q))
        if not kp_ids and not questions:
            skipped += 1
            continue
        data = {
            "id": lesson.id,
            "title": lesson.name,
            "kps": kp_ids,
            "theory": _theory_from_kps(orch, kp_ids),
            "quiz": questions,
        }
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        written += 1
        n_q += len(questions)
    return {"lessons": written, "skipped": skipped, "questions": n_q}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="导出 DB 内容回种子文件")
    ap.add_argument("--all", action="store_true", help="连没有种子文件的课也导出")
    ap.add_argument("--overwrite", action="store_true", help="覆盖已存在的种子文件")
    args = ap.parse_args(argv)

    cfg = Config.from_env()
    orch = Orchestrator(cfg)
    try:
        result = export(orch, Path(cfg.content_dir) / "lessons",
                        all_lessons=args.all, overwrite=args.overwrite)
    finally:
        orch.close()
    print(f"导出完成：写 {result['lessons']} 课 · 跳过 {result['skipped']} 课 · "
          f"{result['questions']} 道题 → {Path(cfg.content_dir) / 'lessons'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
