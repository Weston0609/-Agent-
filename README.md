# 软件作品集

个人项目集合，全部使用 Python 标准库实现，零第三方运行时依赖。

## 项目

| 目录 | 说明 | 技术栈 |
|------|------|--------|
| `pyai-tutor/` | Python & AI 架构师离线学习系统（8 学期 / 186 课 / 401 知识点），含 BKT+FSRS 记忆引擎、SQLite 存储、Web 学习面板、多用户、自动排课 | Python 标准库、SQLite、HTML/JS |
| `ai-architect-academy/` | 闯关式离线学习系统，DAG 前置解锁、40 分钟排课、DeepSeek 一次性生成课程内容后全程离线 | Python 标准库、SQLite、http.server |
| `知识库/` | 配套课程讲义与知识笔记（Markdown） | Markdown |

## 快速开始

```bash
# 以 pyai-tutor 为例
cd pyai-tutor
python -m src.web          # 打开 Web 学习面板
python -m src.cli status   # 查看学习进度
```

无需安装任何第三方包，Python 3.x 即可运行。

## 设计原则

- **离线优先**：学习过程零 token、零联网，只有更新课程内容时才调用 API
- **标准库实现**：SQLite 存进度、http.server 做面板、urllib 调接口
- **可验证**：附带测试脚本与回归测试

## 测试

```bash
cd pyai-tutor && python -m unittest discover tests -v
```
