# pyai-tutor · Python & AI 架构师离线学习系统

闯关式、学校模式、**40 分钟一节课自动排课**、**离线学习零 token** 的 Python 与 AI 架构师完整学习系统。

从 `print("hello")` 的 Python 基础，一路学到 AI 架构师（分布式训练 / 推理服务 / MLOps / 系统设计），覆盖 8 学期、186 节课、401 个知识点。

## 核心特性

| 特性 | 说明 |
|------|------|
| 🎯 闯关模式 | 每节课都是一道关：随堂测验 ≥ 75% 才通过并解锁下一节；上学期全部通过才解锁下学期 |
| 🕹️ 像素三页 | Web 面板拆成三块独立全屏界面：**首页**（选关/看数据）、**课堂页**（学）、**闯关页**（打 BOSS），靠 `#/home` `#/class/<课>` `#/boss/<课>` 路由切换 |
| 🗺️ 关卡地图 | 课程树铺成马里奥式关卡格子，当前关/已通关/未解锁三态一眼分辨，点格子直接进课堂 |
| ☁️ 白云互动 | 每小节末尾弹一朵白云小问题（选题自题库，0 token）；答对给鼓励 🎉、答错给安慰 💡，**对错都继续讲**，不卡进度 |
| 🧠 大白话卡片 | 讲义下方补一块「人话版」：说白了 / 记这一句 / 代码里 / 容易踩 —— 全部摘自已缓存讲义原句，不新增知识 |
| ⚔️ 街机对战 | 打 BOSS 是左右对战的街机画面（YOU vs BUG KING）：出拳位移、命中飘字、连击徽标、血条，正确率 ≥ 85% 才通关 |
| ⏱️ 40 分钟/节 | 8 阶段节奏：热身 4′ → 目标 2′ → 讲授 12′ → 引导练习 4′ → 随堂测验 10′ → 评估 4′ → 小结 3′ → 排复习 1′ |
| 📅 自动排课 | `TimeDaemon` 每天 07:00 依据课表空档与进度自动排课（默认周一至五 19:00–21:00） |
| 🕐 实时时间 | 守护进程每 15 秒感知当前时间日期，保证计时与进度精度 |
| 🔔 通知收件箱 | 上课提醒（到点）/ 缺席召回（21:00）/ 更新完成，全部落库离线可读 |
| 💰 零 token 离线 | 学习全程读数据库里的预生成内容；只有 `pyai update` 才调用 DeepSeek |
| 🧠 记忆引擎 | BKT 贝叶斯知识追踪（掌握度）+ FSRS 间隔重复（复习队列）+ 错题本 |
| 🗄️ DB 驱动 | 课程树 / 内容 / 题库 / 掌握度 / 复习队列全在 SQLite，不依赖运行时读 YAML |
| 🌐 真抓取（更新时） | 按 `sources.yaml` 白名单抓权威源：stdlib `urllib`，robots 自律 + 速率限制 + 失败重试 + 内容哈希去重与版本化 |
| 🧩 Chroma 自适应 | 检测到 `chromadb` 自动用本地持久化向量库，否则回退内存向量 —— 两种路径都离线可用 |
| 🦙 Ollama 回退 | 没有 DeepSeek key 时可走本地 Ollama 生成内容，云端 token 仍为 0 |
| 👥 多用户 | 每个用户独立进度/掌握度/错题/复习队列；CLI `--user` / Web 右上角切换 |
| 💸 花费可见 | `updates_log` 累计 token 与轮次在 CLI `status` 与 Web 面板直接显示 |

## 怎么打开（最简单的方式）

**双击项目根目录下的 `启动学习系统.bat`。**

会弹出一个黑色窗口（学习系统的后台，关闭它即退出），几秒后浏览器自动打开面板：

```
http://127.0.0.1:8000
```

进去就能直接上课：首页「闯关地图」点任意亮起的关卡 → 进入**课堂页**（全屏）一节一节学；
学完点「挑战 BOSS」进入**闯关页**（全屏街机对战），正确率 ≥85% 通关。
点左上角「◀ 返回首页」随时回到选关页。

> 首次使用如果提示找不到 Python：装好 Python 3.10+（安装时勾选 **Add Python to PATH**），
> 然后在项目目录执行 `python -m venv .venv` 和
> `.venv\Scripts\python -m pip install pyyaml jinja2 apscheduler fsrs` 即可。
> 项目自带的 `.venv/` 已装好依赖，正常情况无需任何配置。

## 快速开始（命令行方式）

```bash
pip install -e .                 # 安装（四个轻依赖，无重包）

python scripts/init_db.py        # 建库 + 种课程树 + 载入离线内容（幂等）
pyai status                      # 查看进度与今日排课
pyai class s1u1l1                # 上一节 40 分钟课（8 阶段 + 随堂测验）
pyai web                         # 打开 Web 面板 http://127.0.0.1:8000
```

命令行全貌（全局 `--user <id>` 指定学习者，默认 `default`）：

```bash
pyai status                  # 进度 + 今日排课 + 到期复习 + 补强提示 + token 累计
pyai schedule                # 今日排课
pyai learn <lesson_id>       # 只读内容（0 token）
pyai class <lesson_id>       # 完整 40 分钟课堂（8 阶段，含随堂测验）
pyai boss [lesson_id]        # 打 BOSS：逐题对战，正确率 ≥85% 通关（HP 清空才算赢）
pyai quiz <lesson_id>        # 单独做一次测验（判分 + BKT/FSRS 更新）
pyai update [--max N]        # 联网抓取 + 生成内容：唯一烧 token 的地方
pyai web [--port N]          # Web 面板
pyai notify [--read]         # 查看通知收件箱（--read 全部标记已读）
pyai daemon                  # 常驻守护进程（实时排课 + 提醒 + 周更）
pyai reset                   # 清空学习进度（保留课程与内容）
```

守护进程（实时排课 + 提醒）：

```bash
python -m pyai.daemon         # 常驻：15s tick 到点开课；07:00 排课；21:00 缺席召回；22:00 明日预告；周日 03:00 更新
```

## 离线 vs 在线（token）

- **离线学习（0 token）**：`status` / `schedule` / `learn` / `class` / `quiz` / `web` 全部读本地 SQLite，不联网。
  内容在库初始化时由 `content/lessons/*.json` 离线种子写入 `kp_content` + `questions`。
- **系统更新（烧 token）**：只有 `pyai update` 或 `python scripts/weekly_update.py` 才调用 DeepSeek。

```bash
export DEEPSEEK_API_KEY="sk-..."
pyai update --max 20         # 单轮最多生成 20 个 KP（控花费）
```

没有 key 也能跑（**0 云端 token**）：

```bash
# 选项 A：完全跳过生成，只做抓取与审计
pyai update                  # 记 skipped_no_key，抓取与审计仍然执行

# 选项 B：走本地 Ollama（模型在本机，不产生云端费用）
export PYAI_OLLAMA_URL="http://127.0.0.1:11434"
export PYAI_OLLAMA_MODEL="qwen2.5:14b"
pyai update --max 5
```

更新管道 5 阶段：① 按白名单真抓取 + 确定生成队列（0 token，含"尚无内容的知识点"）
② 生成讲义 + 题库 + 代码沙箱验证（烧 token 或走 Ollama）
③ 陈旧内容打补丁（烧 token）④ 知识树扩建（烧 token）⑤ 审计（0 token，查引用与重复）。花费逐轮记入 `updates_log`，`pyai status` 直接可见。

## 项目结构

```
pyai-tutor/
├── curriculum/            # 课程数据
│   ├── full_curriculum.yaml   # 8 学期课程树（权威源，建库时种入 DB）
│   ├── sources.yaml           # 权威源白名单
│   └── prompt_templates/      # tutor / quiz_gen / evaluator / updater
├── content/lessons/       # 离线种子内容（建库时载入 DB）
├── src/pyai/
│   ├── config.py          # 全局配置（环境变量 + 默认值）
│   ├── daemon.py          # 入口：启动 TimeDaemon 常驻
│   ├── core/              # orchestrator / clock / state / lesson_runner / time_daemon / boss / interactions / plainlang
│   ├── learning/          # curriculum / scheduler / grading / bkt / fsrs
│   ├── agents/            # tutor（缓存讲授，0 token）
│   ├── knowledge/         # ingest（真抓取）/ vector_store / retriever / claim_verifier
│   ├── updater/           # pipeline / kp_generator / audit（唯一烧 token）
│   ├── tools/             # deepseek_client / ollama_client / code_sandbox / notifier
│   ├── db/                # schema.sql / models / session / seed_content
│   └── ui/                # cli（argparse）+ web（http.server 零依赖；templates/index.html 是像素三页 SPA）
├── deploy/                # pyai-daemon.service（Linux systemd 用户服务）
├── .github/workflows/     # CI：3.11/3.12 跑全部测试 + 端到端冒烟
├── tests/                 # 129 个测试：grading / bkt / fsrs / scheduler / lesson_runner / boss / classroom / seed_content / pipeline / course_map / notifications …
└── scripts/               # init_db / seed_curriculum / bootstrap_knowledge / weekly_update / smoke_e2e / genall / export_content / run_daemon.bat
```

## 测试与验证

```bash
python -m unittest discover -s tests        # 129 个测试
python scripts/smoke_e2e.py                 # 端到端冒烟：课堂 + 守护 + Web（临时库，不污染数据）
```

## 部署（常驻运行）

学习系统要"知道现在几点"，所以守护进程要常驻。两种方式：

**Windows**（开机自启）：双击 `scripts\run_daemon.bat`，或把它的快捷方式丢进 `shell:startup`。

**Linux**（systemd 用户服务）：

```bash
cp deploy/pyai-daemon.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now pyai-daemon
journalctl --user -u pyai-daemon -f
```

CI 打任何分支/PR 都会在 Python 3.11 与 3.12 上跑单元测试 + 端到端冒烟，全程离线、不需要 API key（见 `.github/workflows/ci.yml`）。

## 设计原则

- **核心零依赖**：核心引擎只用标准库 + `pyyaml` / `jinja2` / `apscheduler` / `fsrs` 四个轻依赖，离线学习不需任何重包；`chromadb` 与 Ollama 都是可选加速项，缺失时自动回退。
- **时钟抽象**：业务层走 `Clock`，不直接 `datetime.now()`，排课与计时可确定性测试。
- **多用户隔离**：所有学习状态（进度 / 掌握度 / 错题 / 复习 / 通知）按 `user_id` 隔离，CLI `--user` 与 Web 面板均可切换，默认 `default`。
- **降级回退**：无 DeepSeek key → 先试 Ollama，再不行就跳过生成并记 `skipped_no_key`（抓取与审计照常）；无 Docker → 本地子进程执行代码；无 Chroma → 内存向量。
- **抓取自律**：只抓 `sources.yaml` 白名单域名，先看 `robots.txt`，逐站限速，按内容哈希去重，失败重试后放弃并记录。
