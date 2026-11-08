"""端到端冒烟：临时 DB + 真实 content/，跑完整学习闭环（0 token）。"""
import json
import sys
import tempfile
import threading
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.pyai.config import Config
from src.pyai.core.clock import RealClock
from src.pyai.core.lesson_runner import LessonRunner
from src.pyai.core.orchestrator import Orchestrator
from src.pyai.core.time_daemon import TimeDaemon
from src.pyai.tools.notifier import Notifier

tmp = Path(tempfile.mkdtemp(prefix="pyai-e2e-"))
cfg = Config(data_dir=tmp / "data", content_dir=ROOT / "content")
orch = Orchestrator(cfg)


def best_answer(q: dict):
    """生成该题的「标准作答」，用于模拟全对。

    注意各种题型的 answer 含义不同，一律取 [0] 会造出假故障（曾让本脚本「全对只拿 56%」）：
      - multi_choice：answer 是**选中项下标**数组 → 原样提交（只交第一项会被判「少选」）。
      - fill_blank  ：answer 是**可接受答案**的字符串数组 → 取第一项。
      - scenario    ：无 answer，按 required_keywords 命中率判分 → 把关键词全写进去。
      - 其余        ：answer 即标准答案本身。
    """
    qtype = q.get("type")
    answer = q.get("answer")
    if qtype == "multi_choice":
        return list(answer or [])
    if qtype == "scenario":
        return "；".join(q.get("required_keywords") or [])
    if isinstance(answer, list):
        return answer[0] if answer else ""
    return answer


print("== 1. 初始化 ==")
st = orch.status()
print(f"  lessons={st['lessons']} kps={st['kps']} next={st['next_lesson']} 今日排课={len(st['day_plan'])} 节")
import sqlite3
con = sqlite3.connect(cfg.db_path)
filled = con.execute("SELECT COUNT(*) FROM kp_content").fetchone()[0]
qs = con.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
print(f"  离线内容：kp_content={filled} questions={qs}")

print("== 2. 完整 40 分钟课堂（8 阶段，随堂全对）==")
session = orch.start_session(orch.user_id, "s1u1l1", orch.clock.now().date().isoformat())
runner = LessonRunner(orch, orch.db, RealClock(),
                      answers_provider=lambda qs: [best_answer(q) for q in qs])
res = runner.run(session)
for p in res["phases"]:
    print(f"  {'✓' if p['completed'] else '…'} {p['phase']:<16} {p['summary']}")
prog = orch.db.get_lesson_progress(orch.user_id, "s1u1l1")
print(f"  本课成绩={prog['quiz_score']:.0%} passed={prog['passed']} attempts={prog['attempts']}")
st = orch.status()
print(f"  进度：passed_lessons={st['passed_lessons']} next={st['next_lesson']}")
assert prog["passed"] and st["next_lesson"] == "s1u1l2", "课堂通过后应解锁下一课"

print("== 3. 测验全错 → 不应推进 ==")
r = orch.submit_quiz("s1u1l2", [99, 99, 99])
print(f"  score={r['score']:.0%} passed={r['passed']} next={orch.status()['next_lesson']}")
assert r["score"] == 0.0 and not r["passed"]
assert orch.status()["next_lesson"] == "s1u1l2", "未通过不应推进"

print("== 4. 时间守护（APScheduler）==")
d = TimeDaemon(orch.db, Notifier(enabled=False), orch, tz=cfg.timezone)
d.start()
print(f"  now={d.now().isoformat()} today={d.today()} jobs={len(d.sched.get_jobs())}")
d._tick()
d.shutdown()
print("  守护 tick + shutdown 正常")

print("== 5. Web API 端到端 ==")
from src.pyai.ui.web.app import build_server  # noqa: E402

srv = build_server(cfg, 8021)
threading.Thread(target=srv.serve_forever, daemon=True).start()


def req(path, data=None):
    url = f"http://127.0.0.1:8021{path}"
    body = json.dumps(data).encode() if data is not None else None
    r = urllib.request.urlopen(urllib.request.Request(url, body, {"Content-Type": "application/json"}))
    return json.loads(r.read().decode())


s = req("/api/status")
print(f"  /api/status lessons={s['lessons']} next={s['next_lesson']}")
les = req("/api/lesson/s1u1l1")
print(f"  /api/lesson/s1u1l1 kps={len(les['kps'])} 全部有内容={all(k['ok'] for k in les['kps'])}")
qsx = req("/api/questions/s1u1l2")
print(f"  /api/questions/s1u1l2 题数={len(qsx['questions'])}")
rr = req("/api/quiz/s1u1l2", {"answers": [best_answer(q) for q in qsx["questions"]]})
print(f"  POST /api/quiz 全对 → score={rr['score']:.0%} passed={rr['passed']} next={orch.status()['next_lesson']}")
assert rr["passed"] and orch.status()["next_lesson"] == "s1u1l3"
srv.shutdown()

orch.close()
con.close()
print("\n✅ 端到端全部通过（全程 0 token）")
