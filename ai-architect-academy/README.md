# Python & AI 架构师离线学习系统

一个**完全离线、零 token** 的闯关式学习系统：从 `print("hello")` 开始，一路学到 AI 架构师。
参考学校模式，按 DAG 严格前置解锁，每节课固定 **40 分钟**，系统**实时感知当前日期时间**来自动排课。

> DeepSeek 只在"更新课程内容"时被调用一次并缓存到本地，之后照常离线学习，**不消耗 token**。

## 核心特性

| 特性 | 说明 |
| --- | --- |
| 🌐 完全离线 | 课程正文、随堂测验、考试题目全部来自本地 JSON，学习过程零 token、零联网 |
| 🔓 闯关解锁 | DAG 严格前置：上一课通过才解锁下一课；单元考通过才进下一单元；学期考通过才进下一学期 |
| ⏱️ 40 分钟排课 | 每节固定 40 分钟，按实时时间自动生成今日排课表 |
| 🕐 实时时间 | 系统用 `datetime.now()` 实时感知日期时间，驱动排课与进度精度 |
| 🧠 8 大学期 | Python 基础 → 进阶 → 异步并发 → 底层性能 → Web/数据 → AI 基础 → AI Agent → AI 架构师 |
| 🤖 DeepSeek 更新 | `update` 命令按需生成/刷新课程内容（唯一消耗 token 的入口） |

## 快速开始

```bash
# 1. 启动本地 Web 学习面板（推荐）
python -m src.web
#    浏览器打开 http://127.0.0.1:8000

# 2. 或使用命令行
python -m src.cli status       # 查看进度 + 今日排课
python -m src.cli schedule     # 查看今日 40 分钟排课
python -m src.cli learn        # 开始下一节课（正文 + 随堂测验）
python -m src.cli exam s1u1    # 参加单元考试
python -m src.cli update       # 调用 DeepSeek 生成/更新内容（消耗 token）
python -m src.cli reset        # 清空进度
```

零第三方依赖，只需 Python 3.10+（3.12 已验证）。

## 课程结构

`curriculum/curriculum.json` 是权威课程表，结构：

```
学期(semester) → 单元(unit) → 课(lesson) → 知识点(kp)
```

- **8 学期** · **55 单元** · **178 节课** · **385 个知识点**（无重复）
- 通过线：**75%**（`meta.pass_threshold`），每课 **40 分钟**（`meta.lesson_minutes`）

**学期解锁规则**（在 `src/unlock.py` 实现）：

```
学期 N 解锁条件：
  · 学期 N-1 的所有单元考试 ≥ 75%
  · 学期 N-1 期末考 ≥ 75%
  · 学期 N-1 无挂起补强项（所有课已通过）
```

> ⚠️ 说明：原始规划文档写了"约 1900 个知识点 / 约 400 节课"，但其实际列出的课程表只有
> 178 节课、385 个知识点。本系统**忠实转录了实际列出的完整清单**，没有凭空编造内容。
> 若要把 385 个知识点细化到 1900 个，可用 `update` 命令让 DeepSeek 逐点扩写，系统会自动缓存。

## 八学期地图

| 学期 | 主题 | 课数 |
| --- | --- | --- |
| s1 | Python 入门：从零到能写程序 | 33 |
| s2 | Python 进阶：工程级代码（OOP/元编程/类型） | 32 |
| s3 | 异步与并发：高吞吐系统（重点） | 24 |
| s4 | 底层原理与性能工程（CPython/C 扩展） | 9 |
| s5 | 服务化与数据工程（FastAPI/DB/MQ） | 13 |
| s6 | AI 基础：张量到 Transformer | 18 |
| s7 | AI Agent 工程（重点） | 31 |
| s8 | AI 架构师：系统设计与规模化 | 18 |

## 目录结构

```
ai-architect-academy/
├── curriculum/
│   └── curriculum.json      # 权威课程 DAG（8 学期完整清单）
├── content/
│   ├── lessons/*.json       # 每节课正文 + 随堂测验（离线）
│   └── exams/*.json         # 单元考 / 期末考（离线）
├── src/
│   ├── models.py            # 数据模型 + 课程加载
│   ├── store.py             # sqlite3 进度持久化（零依赖）
│   ├── unlock.py            # DAG 解锁 + 学期门禁
│   ├── scheduler.py         # 40 分钟排课 + 实时时间
│   ├── grading.py           # 判分（75% 通过线）
│   ├── content.py           # 内容加载 + DeepSeek 生成器
│   ├── cli.py               # 命令行入口
│   └── web.py               # 本地 Web 面板（stdlib http.server）
├── web/
│   └── index.html           # 前端面板（实时时钟 + 闯关进度）
├── tests/                   # unittest 测试（17 个）
└── data/progress.db         # 学习进度（自动生成，git 忽略）
```

## 架构说明

- **零第三方依赖**：核心学习路径只用标准库（`sqlite3` 存进度、`http.server` 做面板、`urllib` 调 DeepSeek）。
- **离线优先**：学习完全读本地 `content/` 文件；DeepSeek 仅 `update` 时联网，结果写回本地缓存。
- **进度持久化**：`data/progress.db` 记录每课状态、考试分数、学习会话（支撑排课与时间精度）。

## 调用 DeepSeek（可选）

```bash
# 设置 API Key
set DEEPSEEK_API_KEY=sk-xxxx        # Windows
# export DEEPSEEK_API_KEY=sk-xxxx   # Linux/macOS

python -m src.cli update s1u1l4     # 生成单节课
python -m src.cli update s1u1       # 生成一个单元考
python -m src.cli update            # 生成第 1 学期全部内容
```

## 测试

```bash
python -m unittest discover -s tests -v
```

## 上传 GitHub

```bash
git init
git add .
git commit -m "init: Python & AI 架构师离线学习系统"
git branch -M main
git remote add origin <你的仓库地址>
git push -u origin main
```
