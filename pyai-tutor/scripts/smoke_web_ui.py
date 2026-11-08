"""端到端验证像素闯关面板：真起 Web 服务 + 真 HTTP，走一遍「载入讲义 → 交卷 → 解锁下一关」。

面板的交互是 JS，这里验证的是它依赖的接口数据流真的通（内容按小节拆分所需的字段、
判分 ≥75% 通关、通关后地图解锁、下一关切换）。用法：python -X utf8 scripts/smoke_web_ui.py
"""
from __future__ import annotations

import dataclasses
import json
import sys
import tempfile
import threading
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from pyai.config import Config  # noqa: E402
from pyai.ui.web.app import build_server  # noqa: E402


def answer_key(question: dict) -> object:
    """按判分规则给出这道题的标准答案（仅本地校验用，前端拿不到 answer）。"""
    kind, answer = question["type"], question["answer"]
    if kind == "single_choice":
        return int(answer)
    if kind == "multi_choice":
        return [int(a) for a in answer]
    if kind in ("fill_blank", "code_reading"):
        return answer if isinstance(answer, str) else str(answer[0] if answer else "")
    return " ".join(question.get("required_keywords") or ["无"])   # scenario 按关键词命中


def get(base: str, path: str) -> dict:
    with urlopen(base + path, timeout=10) as r:
        return json.loads(r.read().decode("utf-8"))


def post(base: str, path: str, payload: dict) -> dict:
    req = Request(base + path, data=json.dumps(payload).encode("utf-8"),
                  headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode("utf-8"))


def main() -> int:
    failures: list[str] = []

    def check(label: str, condition: bool, detail: str = "") -> None:
        print(("  ✓ " if condition else "  ✗ ") + label + (f" — {detail}" if detail else ""))
        if not condition:
            failures.append(label)

    tmp = Path(tempfile.mkdtemp(prefix="pyai-webui-"))
    try:
        cfg = dataclasses.replace(Config(), data_dir=tmp)
        server = build_server(cfg, port=0)
        host, port = server.server_address[:2]
        base = f"http://127.0.0.1:{port}"
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            lesson_id = "s1u1l1"
            print("1) 地图：当前关 =", lesson_id)
            m = get(base, "/api/map?user=default")
            check("地图给出当前关", m["current"]["lesson_id"] == lesson_id, m["current"]["lesson_id"])
            sess = next(s for s in m["semesters"] if s["id"] == "s1")
            lessons = [l for u in sess["units"] for l in u["lessons"]]
            check("第一学期全可打（unlocked）", all(l["state"] == "unlocked" for l in lessons))
            check("第二学期首关上锁", m["semesters"][1]["units"][0]["lessons"][0]["state"] == "locked")

            print("2) 载入讲义：小节拆分所需的字段齐备")
            lesson = get(base, f"/api/lesson/{lesson_id}?user=default")
            check("有 title", bool(lesson.get("title")), str(lesson.get("title")))
            for kp in lesson["kps"]:
                check(f"{kp['id']} ok/explain 可用于分卡片",
                      bool(kp["ok"]) and len(kp["explain"]) > 50, f"{len(kp.get('explain') or '')} 字")

            print("3) 交卷：全对应过关并解锁下一关")
            qs = get(base, f"/api/questions/{lesson_id}?user=default")["questions"]
            check("题目数量够一次测验", len(qs) >= 5, f"{len(qs)} 题")
            # 面板拿不到答案；用库里的答案键算出满分卷，验证「>=75% 通关 → 解锁下一关」这条硬链路。
            import sqlite3
            con = sqlite3.connect(str(cfg.db_path))
            con.row_factory = sqlite3.Row
            keys = {r["id"]: dict(r) for r in con.execute("SELECT * FROM questions")}
            con.close()
            answers = []
            for q in qs:
                row = keys[q["id"]]
                for col in ("options", "answer", "required_keywords"):
                    try:
                        row[col] = json.loads(row[col] or "[]")
                    except (ValueError, TypeError):
                        row[col] = []
                answers.append(answer_key(row))
            res = post(base, f"/api/quiz/{lesson_id}?user=default", {"answers": answers, "user": "default"})
            check("满分卷判定通过", res["passed"] and res["score"] >= 0.75,
                  f"score={res['score']} passed={res['passed']}")

            m2 = get(base, "/api/map?user=default")
            check("通关一关后地图推进", m2["passed"] == 1 and m2["current"]["lesson_id"] == "s1u1l2",
                  f"passed={m2['passed']} current={m2['current']['lesson_id']}")
            st2 = get(base, "/api/status?user=default")
            check("状态页下一关同步", st2["next_lesson"] == "s1u1l2", st2["next_lesson"])

            print("4) 面板轮询接口")
            st = get(base, "/api/status?user=default")
            check("/api/status 有 lessons/kps/next_lesson",
                  all(k in st for k in ("lessons", "kps", "next_lesson")),
                  f"{st.get('lessons')} 课 / {st.get('kps')} KP / next={st.get('next_lesson')}")
            check("/api/notifications 可读", "items" in get(base, "/api/notifications?user=default"))
            check("/api/users 可读", len(get(base, "/api/users").get("users", [])) >= 1)
        finally:
            server.shutdown()
            server.server_close()
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)

    print("\n" + ("✅ Web 面板端到端通过" if not failures else f"❌ {len(failures)} 项失败：{failures}"))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
