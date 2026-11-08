# s2u7l4 Python 代码质量：Lint（静态代码检查） / Ruff：用极快的速度守护 Python 代码质量 / 让代码质量检查自动发生在提交之前

> 来源 `content/lessons/s2u7l4.json`

## py.quality.lint

# Python 代码质量：Lint（静态代码检查）

> **一句话直觉**：Lint 就像一位不厌其烦的代码校对员，在你运行程序之前，就提前帮你找出拼写错误、未使用的变量、风格问题甚至潜在 Bug——让机器替你做枯燥的代码审查。

---

## 1. 为什么需要 Lint（代码静态检查）

写 Python 时你肯定遇到过这些情况：变量名拼错、导入了一个包却从来没用、函数定义了却没有被调用、缩进混用 Tab 和空格……这些错误**不会在语法层面报错**，但往往会在运行时才暴露，浪费大量调试时间。

**Lint**（Linter，源自 Unix 时代的 `lint` 工具）指的是一类**静态分析（static analysis）工具**：它**不运行代码**，只读取源码的语法树（AST，Abstract Syntax Tree），根据预定义规则给出警告或错误。它是「质量保障」的第一道防线：

- **早发现**：写代码时立刻纠错，而不是等到测试/上线。
- **统一风格**：团队协作时代码风格一致，减少无意义的 review 争论。
- **交接安全**：捕获未使用变量、可变默认参数、可疑的比较等隐藏问题。

Python 官方对类型提示（type hints）的说明也明确指出：*"The Python runtime does not enforce function and variable type annotations. They can be used by third party tools such as type checkers, IDEs, linters, etc."*——也就是说，Lint 和类型检查是让 Python「动态语言也能获得静态保障」的关键手段。

---

## 2. 最小可用：用 `pyflakes` 找出真 Bug

`pyflakes` 是最轻量的 Python linter，**只关心逻辑错误**，不管代码风格（比如它不会抱怨你用了几个空格缩进）。

安装：

```bash
pip install pyflakes
```

它会报告：
- 未使用的 import / 变量
- 使用未定义的名称
- f-string 中重复的字段
- 语法级问题

---

## 3. 工程级标准：`ruff` 一站式解决

`ruff` 是用 Rust 写的现代 linter，速度极快，且**兼容 pyflakes、pycodestyle、isort、flake8 的规则集**，是目前社区的主流选择。它能同时做：

- 逻辑检查（未使用变量、未定义名）
- 风格检查（PEP 8，行长、命名规范）
- import 排序
- 自动修复（`--fix`）

安装与使用：

```bash
pip install ruff
ruff check .          # 检查当前目录
ruff check . --fix    # 自动修复可修复项
ruff format .         # 类似 black 的格式化
```

配置文件 `pyproject.toml` 中常用配置：

```toml
[tool.ruff]
line-length = 88
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP"]
# E=pycodestyle, F=pyflakes, I=isort, B=bugbear, UP=pyupgrade
```

---

## 4. 与类型提示（Type Hints）协同

Lint 抓的是「语法与逻辑」，**类型检查器（type checker）** 如 `mypy`、`pyright` 抓的是「类型」。两者互补：

```python
def surface_area_of_cube(edge_length: float) -> str:
    return f"The surface area of the cube is {6 * edge_length ** 2}."
```

Lint 会警告你没用到的变量、不规范的导入；`mypy` 会警告你把 `str` 传进了期望 `float` 的参数。工程上通常二者一起接入 CI。

---

## 5. 接入开发流程：从本地到 CI

- **编辑器内**：VS Code 装 Ruff / Pylance 插件，边写边提示。
- **提交前**：`pre-commit` 钩子自动跑 ruff。
- **CI 中**：GitHub Actions 中运行 `ruff check .`，不通过则拒绝合并。
- **一次性隔离**：`ruff check path/to/file.py`。

一个典型的 `.pre-commit-config.yaml`：

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.0
    hooks:
      - id: ruff
      - id: ruff-format
```

---

## 6. 常见 Lint 规则速查（记住几条就够）

| 代码 | 含义 | 典型触发场景 |
| --- | --- | --- |
| F401 | 导入了但未使用 | `import os` 后从没用 |
| F841 | 局部变量赋值但未使用 | `x = calc()` 后没用 x |
| E501 | 行太长 | 超过 `line-length` |
| E711 | 与 None 比较 | `if x == None` |
| B006 | 可变默认参数 | `def f(a=[])` |
| I001 | import 顺序不规范 | 未分组/未排序 |
| UP | 可以用新语法 | 用旧式 `Optional[X]` 等 |

记住：**Lint 报告不是敌人，是朋友——喜欢挑毛病的朋友。**

```python
# demo_lint.py
# 先安装依赖：pip install ruff pyflakes
# 然后运行：ruff check demo_lint.py 或 pyflakes demo_lint.py

import os  # (F401) 导入但未使用—— lint 会提醒
import sys


def compute_mean(numbers=[]):  # (B006) 可变默认参数，危险！
    total = 0
    unused = 42  # (F841) 赋值但未使用
    for n in numbers:
        total += n
    return total / len(numbers) if numbers else 0


def classify(x):
    # (E711) 应该用 `is None` 而不是 `== None`
    if x == None:
        return "none"
    # (E712) 与 True 比较，应直接 `if x:`
    if x == True:
        return "true"
    return "other"


# (E501) 下面这一行超过 88 字符会报 E501（若配置 line_length=88）
long_message = "This line is intentionally exceedingly long to trigger E501 during the ruff lint demonstration."


if __name__ == "__main__":
    # 正确写法示例（修复后）
    import sys as _sys  # 使用别名仍然算「使用了 sys」
    print(compute_mean([1, 2, 3]))
    print(classify(None))
    print(classify(True))
    print(long_message)
    print(_sys.version_info[:2])

# ruff 预期报告（示意）：
# demo_lint.py:6:8: F401 `os` imported but unused
# demo_lint.py:10:26: B006 Do not use mutable data structures for argument defaults
# demo_lint.py:12:5: F841 Local variable `unused` is assigned to but never used
# demo_lint.py:21:10: E711 Comparison to `None` should be `cond is None`
# demo_lint.py:24:8: E712 Comparison to `True` should be `if cond:` or `if not cond:`
```

## py.quality.ruff

# Ruff：用极快的速度守护 Python 代码质量

> **一句话直觉**：Ruff 是一个用 Rust 写的 Python **linter（代码检查器）** 和 **formatter（格式化器）**，它把 Flake8、isort、pyupgrade、Black 等一堆工具的活全干了，而且快到几乎感觉不到它在运行。

---

## 1. 为什么需要 Ruff？从「代码质量」说起

写 Python 时，下面这些情况你一定见过：

- 导入了 `os` 却从没用过（**未使用导入**，unused import）
- 变量名 `TempValue` 不符合 Python 的 snake_case 命名约定
- 两个不同的模块循环互相 `import`，一跑就报错
- 明明写了 `if x == None:`，Python 不会报错，但这是 bug 温床
- 团队里每个人代码风格不一样，code review（代码评审）一半时间花在空格和引号上

**linter** 就是在你运行代码之前，静态扫描源码、指出这类问题的工具。传统的选择是 Flake8 + isort + pyupgrade + pydocstyle …… 装一堆、配置一堆、跑得很慢。Ruff 用一个二进制、一份 `pyproject.toml`、毫秒级的速度，把它们统一了。

**记住这个结论**：Ruff 的价值 = 覆盖面广（800+ 条规则）+ 速度极快（Rust）+ 配置统一（一份 toml）。

---

## 2. 安装与第一次运行

Ruff 是一个命令行工具，通过 pip 安装：

```bash
pip install ruff
```

装好后你会得到两个核心命令：

- `ruff check` —— 检查（lint）代码
- `ruff format` —— 格式化代码

假设你有一个 `demo.py`：

```python
import os
import sys


def BadName(x):
    return x == None
```

运行：

```bash
ruff check demo.py
```

你会看到类似输出：

```
demo.py:1:8: F401 [*] `os` imported but unused
demo.py:9:14: E711 Comparison to `None` should be `cond is None`
demo.py:5:5: N802 Function name `BadName` should be lowercase
```

每行都包含 **文件:行:列 规则码 说明**。方括号里的 `[*]` 表示这条问题 Ruff 可以自动修。

**记住这个结论**：`ruff check` 的输出格式是 `文件:行:列 错误码 描述`，`[*]` 代表可自动修复。

---

## 3. 规则码与自动修复

Ruff 的规则来自多个「规则集」，每个集合有前缀字母：

| 前缀 | 来源 | 举例 |
|------|------|------|
| `E` / `W` | pycodestyle | `E711` 与 None 比较 |
| `F` | Pyflakes | `F401` 未使用导入 |
| `I` | isort | `I001` 导入未排序 |
| `N` | pep8-naming | `N802` 函数名应小写 |
| `UP` | pyupgrade | 建议用新语法 |
| `B` | flake8-bugbear | 潜在 bug |

默认 Ruff 只启用一小部分（`E4/E7/E9/F`）。想开启更多，用 `--select`：

```bash
ruff check demo.py --select E,W,F,I,N,UP,B
```

对可以自动修的问题，加上 `--fix`：

```bash
ruff check demo.py --select E,W,F,I,N,UP,B --fix
```

Ruff 会直接改写文件，把 `x == None` 变成 `x is None`，把没用的 `import os` 删掉。

**记住这个结论**：选规则靠 `--select`，自动修靠 `--fix`；生产项目里习惯先 `check` 再 `check --fix`。

---

## 4. 用 `pyproject.toml` 做项目级配置

命令行参数写多了会累。项目根目录建一个 `pyproject.toml`，Ruff 会自动读取：

```toml
[tool.ruff]
# 单行最大长度
line-length = 88

# 针对的最低 Python 版本，影响 UP 等规则的推断
target-version = "py311"

[tool.ruff.lint]
# 启用的规则集
select = ["E", "W", "F", "I", "N", "UP", "B"]
# 忽略特定规则（比如不想强制文档字符串）
ignore = ["E501"]

[tool.ruff.lint.per-file-ignores]
# 测试文件里允许 assert 和未使用变量
"tests/**/*.py" = ["S101", "F841"]

[tool.ruff.format]
# 与 Black 保持一致的双引号风格
quote-style = "double"
```

Ruff 会自动向上查找最近的 `pyproject.toml`，所以只要放在项目根目录就行。

**记住这个结论**：配置写在 `pyproject.toml` 的 `[tool.ruff]` 下，规则用 `select`/`ignore` 控制，可以按文件路径单独豁免。

---

## 5. 格式化：`ruff format`

Ruff 的 formatter 与 **Black** 高度兼容（目标：99.9% 一致性）。使用方法和 Black 类似：

```bash
ruff format .              # 格式化当前目录
ruff format --check .      # 只检查不改，CI 里用
ruff format --diff demo.py # 显示会改什么
```

在 CI（持续集成，Continuous Integration）里常用组合：

```bash
ruff check . --output-format=github   # 输出 GitHub Actions 注解
ruff format . --check
```

**记住这个结论**：`ruff format` 是格式化，`ruff check` 是找问题；CI 中一律加 `--check`，只报错不改文件。

---

## 6. 在编辑器/IDE 里集成

以 **VS Code** 为例，安装官方扩展 `charliermarsh.ruff`，然后在 `settings.json` 里：

```json
{
  "editor.formatOnSave": true,
  "editor.defaultFormatter": "charliermarsh.ruff",
  "editor.codeActionsOnSave": {
    "source.fixAll.ruff": "explicit",
    "source.organizeImports.ruff": "explicit"
  }
}
```

保存文件时，Ruff 会自动修复 + 整理导入 + 格式化。把问题在写代码那一刻就消灭掉，比等到 review 阶段高效得多。

**记住这个结论**：编辑器集成的核心是「保存即格式化 + 保存即自动修复」，这是 Ruff 相比传统工具体验最好的地方之一。

---

## 7. 小结

| 你想做的事 | 命令 |
|-----------|------|
| 检查代码 | `ruff check .` |
| 自动修复 | `ruff check . --fix` |
| 格式化 | `ruff format .` |
| CI 只检查不改 | `ruff check .` + `ruff format . --check` |
| 配置 | `pyproject.toml` 中的 `[tool.ruff]` |

学到这里，你已经可以在任何 Python 项目里把 Ruff 当作默认的代码质量守门员。

```python
"""演示 Ruff 常见问题的可运行示例。

在项目根目录运行:
    ruff check examples/ruff_demo.py
    ruff check examples/ruff_demo.py --fix
    ruff format examples/ruff_demo.py
观察 Ruff 报告的问题与自动修改结果。
"""

import os          # F401: 未使用导入
import sys         # F401: 未使用导入
from typing import List  # UP006: 建议用 list[int] 而非 List[int]


# N802: 函数名应小写
# B006: 可变默认参数应避免
def Compute(values: List[int] = []) -> int:  # noqa: B006
    total = 0
    for v in values:
        if v == None:          # E711: 与 None 比较应使用 is
            continue
        total = total + v      # SIM 系列可简化为 total += v
    return total


# F841: 局部变量被赋值但未使用
# E501: 行太长（默认 88 字符）——下面这行刻意写得非常非常非常非常非常非常非常非常非常非常非常非常非常非常长
result = Compute([1, 2, 3])
unused = 42

print(result)
```

## py.quality.precommit

# py.quality.precommit：让代码质量检查自动发生在提交之前

## 一句话直觉

`pre-commit` 是一个 Git 钩子（Git hook）管理框架：在每次执行 `git commit` 时，它会自动帮你运行格式化、类型检查、lint 等工具，**把“不达标”的代码挡在版本库之外**。

---

## 1. 为什么需要 pre-commit？

在没有 pre-commit 的项目里，团队通常靠“自觉”和 CI（持续集成，Continuous Integration）来保证质量。问题是：

- 本地忘记跑格式化，CI 报错后还要多提交一次 `fix format`；
- 代码风格、导入顺序、类型注解检查分散在多个工具里，配置麻烦；
- 不同成员本地工具版本不一致，结果不可复现。

`pre-commit` 解决的是：**把“质量检查”变成一次提交流程中的固定步骤，并用固定版本的工具执行。**

它本身不是代码检查工具，而是“钩子调度器”。真正的检查工作由 `black`、`ruff`、`mypy`、`flake8`、`isort` 等工具完成。

---

## 2. 三个核心概念

### 2.1 Git hook（Git 钩子）

Git 在特定事件（如 commit、push）发生时会执行 `.git/hooks/` 下的脚本。`pre-commit` 这个钩子会在你输入提交信息之前运行。

如果钩子返回非零退出码，提交就会被中断。

### 2.2 `.pre-commit-config.yaml`

这是 pre-commit 的配置文件。它声明：用哪些仓库、哪个版本、启用哪些钩子。

### 2.3 Hook（钩子项）

一个 hook 就是一个可执行工具。例如 `black` 负责格式化，`ruff` 负责 lint。

> 术语：
> - lint（代码静态检查）：不运行代码，仅分析源码以发现风格、潜在 bug。
> - type checker（类型检查器）：根据类型注解（type hints）判断类型是否一致，例如 mypy、pyright。

---

## 3. 最小可运行示例

先安装：

```bash
pip install pre-commit
```

在项目根目录创建 `.pre-commit-config.yaml`：

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.9
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
```

然后执行：

```bash
pre-commit install
```

它会在 `.git/hooks/pre-commit` 写入一个入口脚本。此后每次 `git commit`，pre-commit 都会：

1. 找出本次暂存（staged）的文件；
2. 按配置安装/复用工具环境（首次会下载依赖，通常较慢）；
3. 对文件运行钩子；
4. 如果钩子修改了文件或报告错误，提交失败，你需要重新 `git add` 后再提交。

---

## 4. 常用工具组合（Python 工程级）

典型配置会组合以下工具：

- `ruff`：快速 lint + 自动修复（autofix）。
- `ruff-format` 或 `black`：格式化。
- `mypy`：类型检查。
- `trailing-whitespace`、`end-of-file-fixer`、`check-yaml`：通用的文本卫生钩子（来自 `pre-commit/pre-commit-hooks`）。

示例：

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.9
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.11.2
    hooks:
      - id: mypy
```

`rev` 要写具体的 tag 或 commit hash，保证团队成员安装同一个版本。

---

## 5. 与类型注解（type hints）的关系

Python 运行时不会强制类型注解，注解主要供第三方工具使用。`pre-commit` 是把“注解的价值”兑现的地方之一：通过 mypy 在提交前发现类型不一致，而不是等到运行时报错。

示例：

```python
def add(a: int, b: int) -> int:
    return a + b

add("1", 2)  # mypy 会报 error，Python 运行时不会
```

在 pre-commit 中启用 mypy 后，这一行会在提交时被拦下。

---

## 6. 工程级实践建议

- **只在暂存文件上运行**：pre-commit 默认如此，避免全仓库扫描拖慢速度。
- **CI 里也跑一遍**：`pre-commit run --all-files`，防止有人用 `--no-verify` 跳过。
- **固定 `rev` 版本**：避免“昨天能过今天过不了”。
- **用 `--fix` 自动化**：失败常见原因是格式被自动改了，重新 `git add` 即可。
- **慎用 `--no-verify`**：`git commit --no-verify` 会跳钩子，团队应约定仅在紧急情况下使用。

---

## 7. 动手练习

在你的一个 Python 项目里完成下面任务：

1. 运行 `pip install pre-commit`。
2. 新建 `.pre-commit-config.yaml`，包含 `trailing-whitespace`、`end-of-file-fixer`、`ruff`、`ruff-format`、`mypy`。
3. 运行 `pre-commit install`。
4. 故意在一个 `.py` 文件里：
   - 行末留一个空格；
   - 文件末尾不换行；
   - 写一行 `x: int = "hello"`。
5. 执行 `git add . && git commit -m "test pre-commit"`。
6. 观察输出，根据提示修复（大多数格式问题会被自动修复），再次 `git add` 并提交。

目标：提交成功，说明你的钩子链配置正确。

```python
# 文件名: demo_precommit.py
# 先在本文件所在目录执行: pip install pre-commit
# 然后创建 .pre-commit-config.yaml 并执行: pre-commit install
# 本文件故意包含会被钩子拦下的问题

# 1) 行末多余空格（trailing-whitespace 会修复）
def add(a: int, b: int) -> int:  
    return a + b

# 2) 类型不匹配（mypy 会报错）
x: int = "hello"  # type: ignore[assignment]

# 3) 未使用的导入（ruff 会提示）
import os  # noqa: F401

if __name__ == "__main__":
    print(add(1, 2))

# 4) 文件末尾没有换行（end-of-file-fixer 会修复）
```


---

## 本课题目

### single_choice · None



- [A] 在函数中给变量赋值但之后从未读取它
- [B] 在模块顶部导入一个只用于类型注解的模块并使用 from __future__ import annotations
- [C] 为公开函数补写 docstring
- [D] 把魔法数字提取为具名常量

**参考答案**：0

**解析**：给变量赋值但从未读取它是“未使用变量”的典型触发条件；其余选项通常不会触发该类 lint 警告。

### single_choice · None



- [A] 导入的模块名与当前模块中的某个变量重名
- [B] 导入了某个模块但在本文件中从未引用该名称
- [C] 导入语句放在文件中间而不是全部放在文件顶部
- [D] 导入的模块没有安装在该环境中

**参考答案**：1

**解析**：未使用的导入指的是导入了一个名字但在当前文件中没被使用；模块重名或位置问题属于其他类别的检查，而模块未安装通常表现为 ImportError 或专门的导入解析检查。

### single_choice · None



- [A] 重命名该变量以避免遮蔽内置名称
- [B] 在文件顶部把内置名称删除
- [C] 在代码中加 # noqa 注释忽略所有规则
- [D] 把该变量改成全大写

**参考答案**：0

**解析**：lint 提示遮蔽内置名称是为了避免可读性与潜在错误，通常应重命名；删除内置名称或全面忽略检查都不是推荐做法，全大写也不解决遮蔽问题。

### single_choice · None



- [A] os 被导入但未使用
- [B] sys 被导入但未使用
- [C] import 语句必须放在函数内部
- [D] print 应该改为 sys.stdout.write

**参考答案**：0

**解析**：os 被导入但在该文件中没有使用，因此会被标记为未使用的导入；sys 被使用了，所以不会被标记。import 语句可以放在模块顶部。

### single_choice · None



- [A] for 循环变量未在循环体之外使用，可能提示未使用变量
- [B] range 应该改为 xrange
- [C] print 应该改为 logging
- [D] 循环变量 i 必须声明类型

**参考答案**：0

**解析**：循环变量只用于循环体内部，循环外未使用，部分规则会提示；xrange 只存在于 Python 2 的讨论中，print/logging 与类型声明属于其他关注点。

### single_choice · None



- [A] 正确，lint 通过等于逻辑正确
- [B] 不正确，lint 主要发现风格与可疑模式，不能替代测试与运行时验证
- [C] 正确，因为 lint 会执行所有分支
- [D] 不正确，因为 lint 只检查注释拼写

**参考答案**：1

**解析**：lint 是静态分析，主要针对风格与可疑模式，不执行代码，也无法保证逻辑正确或覆盖所有运行时情况。

### single_choice · None



- [A] 两台机器上的 lint 工具版本或配置文件不同
- [B] Python 代码在不同机器上运行速度不同
- [C] lint 结果依赖操作系统字体
- [D] lint 只在有网络时工作

**参考答案**：0

**解析**：lint 结果取决于工具版本、已启用的规则与配置文件，因此统一版本与配置是保证结果一致的关键；运行速度、字体与网络不是常见原因。

### single_choice · None



- [A] 代码中有一处确实需要与规则冲突的写法，并希望保留可追溯的说明
- [B] 希望让 CI 中所有 lint 规则都不再报告问题
- [C] 希望隐藏代码中的语法错误
- [D] 希望提高程序运行速度

**参考答案**：0

**解析**：临时禁用应针对特定行并配合说明，用于合理的例外；全局关闭会失去检查价值，隐藏语法错误或提升速度都不是禁用 lint 的目标。

### single_choice · None



- [A] 让格式化工具负责排版，让 lint 负责逻辑与风格规则中格式化工具未覆盖的部分
- [B] 只用 lint，禁止使用任何格式化工具
- [C] 只用格式化工具，不需要任何 lint
- [D] 让两者互相覆盖对方的配置

**参考答案**：0

**解析**：两者职责通常互补：格式化工具处理代码排版，lint 关注其余风格与可疑模式；让两者互相覆盖配置容易造成冲突与反复修改。

### single_choice · None



- [A] 未使用的变量或常量
- [B] 常量命名不符合约定
- [C] 布尔值不能赋值给变量
- [D] 模块级变量必须放在函数内部

**参考答案**：0

**解析**：定义但从未读取的模块级名称常被报告为未使用；命名约定规则针对格式（如是否全大写），而不是“未读取”这一事实。

### single_choice · None



- [A] return 之后的代码不可达
- [B] 函数缺少参数
- [C] print 应该使用单引号
- [D] 函数名 f 太短

**参考答案**：0

**解析**：return 之后的语句永远不会执行，属于不可达代码；参数缺失、引号风格与函数名长度属于其他检查。

### single_choice · None



- [A] 在 CI 中运行 lint，并将结果作为合并请求的检查项之一
- [B] 只在开发者本地偶尔运行 lint
- [C] 把 lint 结果写入日志但从不查看
- [D] 要求所有开发者禁用 lint 规则以保证 CI 通过

**参考答案**：0

**解析**：在 CI 中运行并作为检查项，能让问题在合并前被发现；只在本地偶尔运行、只记录不查看或全面禁用规则都会削弱 lint 的价值。

### single_choice · None



- [A] 函数缺少返回类型注解
- [B] 函数在某些输入下会返回 None，但调用方可能期待非 None 值
- [C] 函数名不符合命名规范
- [D] 函数定义没有文档字符串

**参考答案**：1

**解析**：当 x <= 0 时函数隐式返回 None，这种不一致的返回路径常被 lint 类工具标记；命名规范、docstring 与类型注解属于其他规则。

### single_choice · None



- [A] assert 语句在优化模式下可能被移除，因此不应用它做运行时校验
- [B] assert 不能用于类型检查
- [C] isinstance 只能用于自定义类
- [D] int 不是合法的类型

**参考答案**：0

**解析**：使用 assert 做运行时校验在 -O 优化模式下可能被跳过，因此常被 lint 提示；assert 本身可以用于检查条件，isinstance 与 int 的用法也没有问题。

### single_choice · None



- [A] 使用了未定义的变量 x
- [B] 比较表达式的结果没有被使用，可能是误把赋值写成了比较
- [C] 数字 5 应该定义为常量
- [D] 缺少分号结尾

**参考答案**：1

**解析**：单独一行的 x == 5 只是计算比较结果并丢弃，常见于误写；Python 中语句末尾不需要分号。

### single_choice · None



- [A] 只要把该规则改为 warning，同样的代码就不会再被报告
- [B] 该代码一定存在运行时错误
- [C] lint 失败说明单元测试一定也失败
- [D] 把该规则改为 warning 后，CI 仍然会因为这个规则失败

**参考答案**：0

**解析**：规则严重级别决定是否让 CI 失败；改为 warning 通常不会让 CI 因该规则中断，但代码问题仍然会被报告。lint 失败并不等同于运行时会出错，也不代表单元测试一定失败。

### single_choice · None



- [A] None 不能与 == 比较，会抛出异常
- [B] 建议使用 is None 而不是 == None
- [C] None 必须写成 null
- [D] 应当使用 isinstance(x, None)

**参考答案**：1

**解析**：对 None 的身份比较应使用 is / is not，因此许多风格检查会建议改为 x is None；== None 本身不会抛异常，Python 中也没有 null 字面量。

### single_choice · None



- [A] 函数参数默认值使用了可变对象，可能在多次调用之间共享状态
- [B] 函数没有对 items 做类型检查
- [C] items 变量名太短
- [D] 函数没有返回类型注解

**参考答案**：0

**解析**：可变默认参数会在多次调用之间复用同一对象，这是常见的隐患；类型检查、命名长度与返回注解属于其他规则。

### single_choice · None



- [A] 未定义名称 / 可能拼写错误
- [B] 命名风格不符合约定
- [C] 导入顺序不正确
- [D] 缺少模块级文档字符串

**参考答案**：0

**解析**：使用了一个从未被定义过的名称，常被报告为未定义名称或可能的拼写错误；命名风格规则针对的是命名格式而不是名称是否存在。

### single_choice · None



- [A] 不应捕获 Exception，且捕获后什么都不做会隐藏错误
- [B] try 块中只能放一行代码
- [C] except 子句必须指定具体异常类型，否则语法错误
- [D] pass 不能出现在 except 块中

**参考答案**：0

**解析**：捕获过宽的异常并静默 pass 常被标记为可能掩盖问题；except 后不写异常类型在语法上是允许的，pass 也可用于 except 块。

### single_choice · None



- [A] 超过行长度限制会导致程序运行变慢
- [B] 行长度限制是风格约定，可通过配置调整或换行改写来消除提示
- [C] 行长度限制是 Python 解释器强制要求的，超过会报语法错误
- [D] 行长度限制只对注释生效

**参考答案**：1

**解析**：行长度属于风格规则，不影响运行时行为，也不是解释器语法限制；它可通过配置或代码换行来满足。

### single_choice · None



- [A] 把工具的规则全部关闭，只保留格式检查
- [B] 启用包括逻辑错误类规则在内的规则集，并配合格式化工具使用
- [C] 只依赖人工代码评审，不引入自动化检查
- [D] 把所有规则都设为忽略，仅当作占位符使用

**参考答案**：1

**解析**：代码检查工具（linter）的核心价值在于静态分析，能发现风格及潜在逻辑问题；格式化工具负责排版。二者配合、开启逻辑类规则才能覆盖题目期望。关闭规则或仅人工评审都失去了工具价值；全设忽略等于没启用。

### single_choice · None



- [A] 两者功能完全相同，选其一即可
- [B] 检查工具专注发现问题（含风格与逻辑），格式化工具专注按规则重排代码
- [C] 格式化工具能替代检查工具发现未使用变量
- [D] 检查工具运行后一定能自动修复所有问题

**参考答案**：1

**解析**：检查工具做静态分析、报告问题（部分可自动修复）；格式化工具只负责按规则重写排版。格式化工具不分析变量是否被使用，因此无法替代检查工具；检查工具也不能保证修复全部问题。

### multi_choice · None



- [A] 可在 CI 中运行检查命令以统一把关代码质量
- [B] CI 中检查失败通常应导致流水线失败
- [C] 检查工具只能在本地运行，无法用于 CI
- [D] 可在 CI 中先用检查工具自动修复再重新检查

**参考答案**：[0, 1, 3]

**解析**：检查工具可在 CI 中运行并据退出码决定流水线成败；也可先自动修复再复查。说它“只能在本地运行”是错误的，CI 是其典型使用场景之一。

### fill_blank · None



**参考答案**：["per-file-ignores", "per file ignores", "按文件忽略", "文件级忽略"]

**解析**：整体忽略用 ignore；针对特定文件（如测试文件）忽略更适合用 per-file-ignores 这类文件级忽略配置，避免影响其他文件。

### fill_blank · None



**参考答案**：["退出码", "exit code", "退出状态码", "非零退出码"]

**解析**：CI 依据命令的退出码判断成败；检查发现告警时返回非零退出码，CI 据此失败并阻止合并。

### fill_blank · None



**参考答案**：["noqa", "noqa:", "flake8: noqa"]

**解析**：许多检查工具支持 noqa 风格的行内注释来抑制该行告警，无需改动全局规则配置。

### code_reading · None



**参考答案**：未使用的导入：代码导入了 json 但实际使用了 json.load，哦——等等，这里 json.load 用到了 json，因此没有未使用导入问题；该代码本身没有明显的未使用导入告警。

**解析**：题目意在提醒：是否报告“未使用导入”取决于名称是否在后续被引用。此处 json.load 引用了 json，所以不会报告未使用导入。若把 import json 换成某个从未被引用的名称才会触发。

### code_reading · None



**参考答案**：未使用的导入：os 被导入但没有在任何地方被引用，因此会触发未使用导入告警。

**解析**：os 导入后从未使用，属于典型的未使用导入；sys 被 sys.argv 引用，不报告。

### code_reading · None



**参考答案**：未使用的变量：局部变量 x 被赋值但没有被使用（同时返回值 2 与 x 无关），检查工具通常会报告未使用变量。

**解析**：x 赋值后未被读取，属于未使用变量，是检查工具常见规则。这不是语法错误，代码可正常运行。

### scenario · None



**解析**：面对历史项目大量告警，宜采用渐进策略：先启用基础规则集、对存量问题通过 ignore 或行级抑制做可控例外，再随着代码修改逐步启用更严格规则；CI 可先从不阻断（或仅对新增代码阻断）过渡到全量阻断。关键词体现“渐进/逐步”“忽略”“规则集”“CI”等思路。

### scenario · None



**解析**：把规则集中写入项目配置文件（如 pyproject.toml）以保证团队一致；在本地钩子（如 pre-commit）中运行以便提交前拦截；在 CI 中再次运行以保证合并环节把关。关键词体现“配置文件/pyproject.toml”“本地钩子/提交”“CI”。

### scenario · None



**解析**：应使用行级抑制注释（如 noqa 风格）在该行做局部例外，而不是全局 ignore 该规则，并可在注释中说明原因，必要时附带工单号以便后续清理。关键词体现“行内/noqa/注释”“抑制/例外”。

### single_choice · None



- [A] 把该规则名从配置里删掉即可自动关闭
- [B] 在该工具的配置段中把对应规则加入 ignore 列表
- [C] 把整个配置文件清空
- [D] 必须修改源代码才能关闭规则

**参考答案**：1

**解析**：常见检查工具支持在配置文件的工具段中用 select/ignore（或类似机制）来启用或忽略规则；把规则名加入 ignore 即整体关闭。删除配置项通常只是采用默认值，不等于关闭；清空配置也不是正确做法。

### single_choice · None



- [A] 语法错误
- [B] 未使用的导入
- [C] 缩进错误
- [D] 类型不匹配

**参考答案**：1

**解析**：导入后未在任何地方引用，属于“未使用导入”，是检查工具的经典规则。它不是语法错误（import 语句本身合法），也不是缩进或类型问题。

### single_choice · None



- [A] 可以在行末用注释（如 `# noqa`）来抑制该行的告警
- [B] 必须删除该行代码才能在检查中通过
- [C] 行内注释无法影响检查结果
- [D] 只能用命令行参数忽略，不能按行忽略

**参考答案**：0

**解析**：许多检查工具支持行级抑制注释（如 noqa 风格），可在特定行抑制特定或全部告警，用于确有必要的例外。删除代码并非唯一途径；行内注释通常有效；按行忽略是常见能力。

### single_choice · None



- [A] 让检查命令在发现告警时返回非零退出码，并在 CI 中据此失败
- [B] 在 CI 中忽略检查命令的退出码
- [C] 只在本地运行检查，不使用 CI
- [D] 把检查工具的输出重定向到 /dev/null

**参考答案**：0

**解析**：CI 依据命令退出码判断成败。检查工具发现告警时通常返回非零退出码，CI 据此失败即可阻止合并。忽略退出码、只在本地运行、丢弃输出都无法在 CI 中阻断问题。

### single_choice · None



- [A] 所有规则都支持自动修复
- [B] 部分规则支持自动修复，其余仍需人工修改
- [C] 自动修复会破坏代码语义，因此永不使用
- [D] 自动修复功能与检查工具无关

**参考答案**：1

**解析**：检查工具的自动修复只覆盖可安全改写的规则（如未使用导入、可简化的写法等），很多规则（如潜在逻辑错误）无法或不宜自动修改。因此部分可修、部分需人工，且修复通常保持语义安全。

### single_choice · None



- [A] 规则越多越严格一定越好，无需考虑项目现状
- [B] 应根据项目阶段和团队接受度逐步启用更严格的规则
- [C] 基础规则集已涵盖所有逻辑错误，无需扩展
- [D] 启用更严格规则集后无法再单独忽略某条规则

**参考答案**：1

**解析**：启用更严格的规则集往往会引入大量历史代码告警，宜按项目阶段和团队接受度渐进启用，并可用 ignore/行内注释做例外。规则并非越多越好；基础规则集不覆盖全部逻辑问题；扩展后仍可单独忽略规则。

### multi_choice · None



- [A] 未使用的导入
- [B] 未定义的变量名
- [C] 运行时的除零错误
- [D] 行尾多余空白等风格问题

**参考答案**：[0, 1, 3]

**解析**：检查工具通过静态分析可发现未使用导入、未定义名称、风格问题等。运行时的除零错误取决于实际执行的数据，静态分析通常无法确定，需依靠测试或运行。

### multi_choice · None



- [A] 在项目配置文件中集中声明启用的规则集
- [B] 对确有必要的个别代码行使用行内抑制注释
- [C] 为每条规则单独写一个配置文件
- [D] 把工具接入本地钩子或 CI 流程中自动运行

**参考答案**：[0, 1, 3]

**解析**：集中配置规则集、按需行级抑制、接入本地钩子或 CI，都是常见实践。为每条规则单独建一个配置文件并非合理做法，只会增加维护负担。

### single_choice · None



- [A] 让代码在推送到远程仓库前自动运行测试并阻止所有失败提交
- [B] 在代码提交前自动执行格式化、静态检查等钩子，尽早发现低级问题
- [C] 替代 CI 流水线，把全部集成测试都放到本地执行
- [D] 强制所有开发者使用统一的编辑器配置

**参考答案**：1

**解析**：pre-commit 的核心价值是把格式化、lint 等快速检查前移到提交阶段，让问题在进入仓库前暴露。它不能替代 CI（CI 仍要跑完整测试），也无法强制编辑器配置，A 项‘阻止所有失败提交’也过于绝对。

### single_choice · None



- [A] 钩子配置必须写在 setup.py 的 entry_points 里
- [B] 钩子集中配置在一个名为 .pre-commit-config.yaml 的文件中，由 pre-commit 读取
- [C] 每个钩子必须自己实现 Git 的对象校验逻辑
- [D] 钩子只能由 CI 系统触发，本地无法运行

**参考答案**：1

**解析**：pre-commit 通过仓库根目录下的 .pre-commit-config.yaml 声明钩子来源与参数，工具会据此安装并调用各钩子。钩子无需自己处理 Git 对象，本地和 CI 都能运行。

### single_choice · None



- [A] 指定该钩子仓库的版本/标签，保证不同机器上使用相同的钩子代码
- [B] 指定要检查的文件版本号
- [C] 指定提交信息必须包含的版本字符串
- [D] 指定钩子运行的最低 Python 版本

**参考答案**：0

**解析**：rev 用于锁定远程仓库的提交/标签，确保团队成员和 CI 使用同一份钩子实现，是可复现性的关键。

### single_choice · None



- [A] 他的电脑上没装 Git
- [B] 他克隆仓库后没有运行 pre-commit install 安装钩子
- [C] .pre-commit-config.yaml 一定被删除了
- [D] pre-commit 只在 Linux 上可用

**参考答案**：1

**解析**：钩子脚本需要安装到本地 .git/hooks 才会被触发；克隆仓库并不会自动安装。其余选项与症状不符。

### multi_choice · None



- [A] 代码格式化（如 black、ruff format）
- [B] 静态检查/风格检查（如 ruff、flake8）
- [C] 提交信息格式校验（commit-msg 阶段）
- [D] 在生产服务器上做压力测试
- [E] 在提交时自动部署到线上环境

**参考答案**：[0, 1, 2]

**解析**：pre-commit 适合快速、本地的格式化、lint 与提交信息校验。压力测试和部署属于耗时或高风险操作，应放在 CI/CD 流程中，不适合提交前钩子。

### multi_choice · None



- [A] pre-commit 侧重快速反馈，在提交阶段拦截明显问题
- [B] CI 可以运行更完整、更耗时的测试，作为合并门禁
- [C] CI 中运行 pre-commit 有助于防止开发者绕过本地钩子
- [D] 有了 pre-commit 后 CI 中的测试可以全部删除
- [E] pre-commit 与 CI 互斥，只能选其一

**参考答案**：[0, 1, 2]

**解析**：两者是互补关系：pre-commit 提供本地快速反馈，CI 提供权威的、不可绕过的门禁。CI 中额外运行 pre-commit 可覆盖被 --no-verify 绕过的提交。删除全部 CI 测试或认为二者互斥都是错误理解。

### multi_choice · None



- [A] 把钩子配置和版本锁定提交到仓库，随代码一起评审
- [B] 在 README 或贡献指南中写明需要先执行 pre-commit install
- [C] 选择运行很快的检查，避免拖慢每次提交
- [D] 让每个开发者各自在本地随意修改钩子配置且不提交
- [E] 在 CI 中复用同一份配置，保证检查一致

**参考答案**：[0, 1, 2, 4]

**解析**：配置入库、文档说明安装步骤、保持钩子快速、CI 复用同一配置，都是常见最佳实践。允许各自随意修改且不入库会导致检查不可复现。

### fill_blank · None



**参考答案**：[".pre-commit-config.yaml", ".pre-commit-config.yml"]

**解析**：pre-commit 默认读取仓库根目录的 .pre-commit-config.yaml（.yml 也可被接受）。这是声明 repo、rev、hooks 等信息的核心文件。

### fill_blank · None



**参考答案**：["--all-files", "--all_files"]

**解析**：--all-files 指示 pre-commit 把仓库中全部被跟踪的文件传给钩子，常用于首次引入或修复问题后做全量验证。

### code_reading · None



**参考答案**：pre-commit 会调用 ruff 钩子；由于加了 --fix，ruff 会尝试自动修复它支持修复的问题。如果文件被修改，pre-commit 会判定本次提交失败并提示文件已被改动。开发者需要重新查看改动、git add 这些文件后再次提交；若仍有无法自动修复的问题，须手动修改后再提交。

**解析**：带 --fix 的钩子会就地修改文件，触发 pre-commit 的‘文件被修改即失败’机制，从而要求开发者重新审阅并暂存修改，避免未经验证的内容被提交。

### code_reading · None



**参考答案**：.git/hooks/pre-commit 是 pre-commit 安装到本地仓库的钩子入口脚本，缺失意味着钩子没有被安装，因此 git commit 时不会触发检查。修复办法是在仓库根目录执行 pre-commit install，它会重新生成该钩子脚本。

**解析**：pre-commit 依靠 .git/hooks 中的脚本被 Git 调用；克隆仓库不会自动写入，必须通过 pre-commit install 安装，这也是新成员常见问题。

### scenario · None



**解析**：提交前钩子应保持轻量、秒级完成，用于格式化和 lint 等快速检查；耗时的测试、依赖安装等应放到 CI 流水线。把重活塞进钩子会拖慢提交，诱使开发者用 --no-verify 绕过，反而失去检查效果。合理方案是钩子只留快速检查，完整测试交给 CI 作为合并门禁。

### single_choice · None



- [A] 运行 pre-commit install，把钩子脚本写入 .git/hooks
- [B] 运行 pip install .pre-commit-config.yaml
- [C] 手动在每个提交里加上 --no-verify 参数
- [D] 把 .pre-commit-config.yaml 复制到用户主目录

**参考答案**：0

**解析**：pre-commit install 会在 .git/hooks 中生成对应的钩子脚本，之后 git commit 才会触发。仅克隆仓库不会自动安装钩子；--no-verify 恰恰是绕过检查。

### single_choice · None



- [A] 直接放行提交，忽略文件已被修改这一事实
- [B] 阻止提交并提示文件已被修改，需重新添加并再次提交
- [C] 自动把修改后的文件重新 git add 后继续提交
- [D] 回滚格式化结果，恢复原始文件

**参考答案**：1

**解析**：当钩子改动了被暂存的文件，pre-commit 会判定为失败，防止未经验证的修改被提交。用户需要重新 git add 被修改的文件并再次提交。它不会替你自动 add。

### single_choice · None



- [A] 默认总是检查整个仓库的所有文件，无论是否暂存
- [B] 默认只把本次提交涉及的文件（staged files）传给钩子
- [C] 默认只检查最后一个提交的 diff
- [D] 默认只检查被 git 跟踪且刚刚新建的文件

**参考答案**：1

**解析**：pre-commit 默认把本次暂存的文件列表传给钩子，这样检查是增量的，速度快。若要检查全部文件可手动传 --all-files。

### single_choice · None



- [A] pre-commit run --all-files
- [B] pre-commit run --commit-all
- [C] pre-commit install --all
- [D] pre-commit check --everywhere

**参考答案**：0

**解析**：--all-files 让 pre-commit 把仓库中全部（被跟踪的）文件交给钩子检查，常用于首次引入或修复后全量验证。其余选项都是不存在的用法。

### single_choice · None



- [A] 在每次 git commit 生成提交信息之后、提交完成之前运行
- [B] 在文件被暂存（git add）时运行
- [C] 在代码推送到远程仓库前运行
- [D] 在创建分支时运行

**参考答案**：0

**解析**：commit-msg 阶段的钩子接收提交信息文件，用于校验提交信息格式（如是否符合 Conventional Commits），发生在提交信息生成之后、提交落盘之前。

### single_choice · None



- [A] 这是禁止行为，Git 会因此拒绝后续推送
- [B] 这是合法逃生通道，但应有意识地避免，因为它会把问题带到仓库
- [C] 这会使 .pre-commit-config.yaml 失效并被自动删除
- [D] 这只在 CI 未配置时才允许使用

**参考答案**：1

**解析**：--no-verify 是 Git 提供的合法绕过机制，用于紧急情况；但滥用会让未格式化和有缺陷的代码进入历史，团队通常要求事后再补跑检查。

### single_choice · None



- [A] 在 CI 中执行 pre-commit run --all-files（或等价命令）
- [B] 在 CI 中运行 git commit --no-verify
- [C] 在 CI 中删除 .pre-commit-config.yaml 再重建
- [D] 让每个开发者在本地手动运行检查即可，CI 不需要

**参考答案**：0

**解析**：CI 中运行 pre-commit（常见做法是全量 run --all-files）可以防止开发者本地绕过或未安装钩子导致的问题，保证检查一致性。

### single_choice · None



- [A] 钩子只能使用本地仓库自身编写的脚本，不能引用外部仓库
- [B] 既可以通过 repo 字段引用外部 Git 仓库的钩子，也可以使用本地（local）仓库定义的钩子
- [C] 每个钩子必须发布到 PyPI 才能被引用
- [D] 钩子必须用 Python 编写，不支持其他语言

**参考答案**：1

**解析**：在 .pre-commit-config.yaml 中，repo 可以指向远程 Git 仓库并指定 rev，也可以用 repo: local 定义本仓库内的钩子；钩子本身可以是任意语言的可执行命令。
