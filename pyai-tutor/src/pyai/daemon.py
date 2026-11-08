"""入口 —— 启动 TimeDaemon（APScheduler 常驻调度，唯一知道"现在几点"的组件）。

`python -m pyai.daemon` 启动守护进程：
  · 每 15 秒 tick：到点启动一节 40 分钟课
  · 每天 07:00 生成今日课表；21:00 缺席召回；22:00 明日预告
  · 每周日 03:00 触发系统更新（唯一用 API 的时刻）
"""
from __future__ import annotations

import time

from .config import Config
from .core.orchestrator import Orchestrator
from .core.time_daemon import TimeDaemon
from .tools.notifier import Notifier


def main() -> None:
    config = Config.from_env()
    orchestrator = Orchestrator(config)
    notifier = Notifier(orchestrator.db)
    daemon = TimeDaemon(
        orchestrator.db,
        notifier,
        orchestrator,
        tz=config.timezone,
    )
    print(f"TimeDaemon 启动：实时感知时间，排课 {config.lesson_minutes} 分钟/节")
    daemon.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        daemon.shutdown()
        print("TimeDaemon 已停止")
    finally:
        orchestrator.close()


if __name__ == "__main__":
    main()
