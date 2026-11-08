# s1u1l1 从零搭建可复现的 Python 开发环境 / Python 虚拟环境入门 / Python 包管理的起点 等 4 个知识点

> 来源 `content/lessons/s1u1l1.json`

## py.env.install

# py.env.install：从零搭建可复现的 Python 开发环境

## 一句话直觉

**写 Python 代码之前，你首先得让 Python 能在你的电脑上跑起来，并且每个项目用到的第三方库互不打架——这就是 `py.env.install` 要解决的事。**

Python 本身很小，真正让它强大的是成千上万的第三方包（package）。但如果你把所有包都塞进同一个全局环境，不同项目的依赖（dependency）很快会冲突。工程级做法是：**为每个项目建一个独立的虚拟环境（virtual environment），再在其中安装依赖。**

本讲按照“装解释器 → 建虚拟环境 → 装包 → 固定依赖 → 复现”的顺序，层层递进。

---

## 第 1 节｜安装 Python 解释器（Interpreter）

**解释器**是运行 `.py` 文件的程序。官方推荐从 [python.org](https://www.python.org/downloads/) 下载。

- Windows：安装时**务必勾选 “Add Python to PATH”**，否则命令行找不到 `python`。
- macOS：可用官方安装包，或用 Homebrew：`brew install python`。
- Linux：多数发行版自带的 `python3` 即可；建议用 `sudo apt install python3 python3-pip python3-venv`。

验证安装是否成功：

```bash
python --version      # Windows
python3 --version     # macOS / Linux
```

> 说明：macOS 与多数 Linux 上系统命令是 `python3`，本节命令请按你的系统替换。

---

## 第 2 节｜pip 与虚拟环境

**pip** 是 Python 的官方包管理器（package manager）。**虚拟环境** 是一个独立目录，里面有一套隔离的 Python 与 pip，不会污染全局。

Python 3.3+ 自带 `venv` 模块。标准工作流：

```bash
# 1. 进入项目目录
cd my_project

# 2. 创建名为 .venv 的虚拟环境（名字任意，约定用 .venv）
python3 -m venv .venv

# 3. 激活它
source .venv/bin/activate      # macOS / Linux
.venv\Scripts\activate         # Windows (cmd/PowerShell)

# 4. 激活后提示符前会出现 (.venv)
# 5. 退出
# deactivate
```

判断是否激活成功：`python -c "import sys; print(sys.prefix)"` 应输出 `.venv` 目录路径。

---

## 第 3 节｜用 pip 安装第三方包

```bash
# 安装单个包
pip install requests

# 安装指定版本（生产环境强烈建议）
pip install "requests==2.32.3"

# 一次安装多个
pip install requests httpx rich

# 升级 pip 自身
python -m pip install --upgrade pip

# 查看已安装
pip list
```

安装完成后即可导入：

```python
import requests
print(requests.__version__)
```

---

## 第 4 节｜固定依赖：requirements.txt

只写下包名不够——以后别人（或未来的你）在另一台机器上安装时，可能拿到不同版本，导致行为不一致。解决办法是**冻结**（freeze）当前版本列表：

```bash
# 生成依赖清单
pip freeze > requirements.txt

# 别人拿到项目后，一键还原
pip install -r requirements.txt
```

`requirements.txt` 内容示例：

```
requests==2.32.3
httpx==0.27.2
rich==13.9.4
```

---

## 第 5 节｜工程级实践清单

1. **每个项目一个虚拟环境**，目录名用 `.venv`，并写进 `.gitignore`。
2. **不要用 `sudo pip install`**：会污染系统 Python，很多发行版已拒绝执行。
3. **锁定版本**：把 `requirements.txt` 提交到 Git。
4. **大型项目考虑现代工具**：`pip-tools`、`poetry`、`uv`、`pdm` 提供更严格的锁定与解析。
5. **依赖来源**：默认走 [PyPI](https://pypi.org/)。国内网络慢可加镜像：
   ```bash
   pip install -i https://pypi.tuna.tsinghua.edu.cn/simple requests
   ```

---

## 常见误区（Pitfalls）

- **忘了激活虚拟环境**：装包装到了全局，项目却 import 失败。激活后再 `pip install`。
- **Windows PowerShell 激活被策略阻止**：执行 `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` 后重试。
- **`pip` 与 `python` 对应不上**：永远用 `python -m pip ...` 而非裸 `pip ...`，可避免装错解释器。
- **提交 `.venv` 到 Git**：体积巨大且无意义，写进 `.gitignore`。
- **不锁版本**：某天上游发新版，代码意外报错。
- **删掉 `.venv` 后忘了重建**：`pip install -r requirements.txt` 即可复原。

---

## 动手练习

**任务：从零创建一个可复现的小项目。**

1. 新建目录 `hello-env` 并进入。
2. 创建虚拟环境 `.venv`，激活它。
3. 安装 `rich` 的任意版本，并升级 `pip`。
4. 写一个 `app.py`，用 `rich` 打印一句彩色问候：
   ```python
   from rich import print
   print("[bold magenta]Hello, Python environment![/bold magenta]")
   ```
5. 运行 `python app.py`，确认输出正常。
6. 执行 `pip freeze > requirements.txt`。
7. **验证隔离性**：删除 `.venv`，重新创建并激活，运行 `pip install -r requirements.txt`，再次 `python app.py`，确认一切正常。
8. 提交最终目录结构（`app.py` + `requirements.txt` + `.gitignore`，忽略 `.venv/`）。

```python
"""
演示 py.env.install 的完整流程（在已激活的虚拟环境中运行本脚本）：
  1) 检查当前解释器是否为虚拟环境
  2) 打印已安装的第三方包
  3) 探测 requirements.txt 是否存在
注意：本脚本只做检查，不执行安装；安装请用命令行 pip。
"""
import sys
import importlib.metadata as md
from pathlib import Path


def in_virtualenv() -> bool:
    """判断当前解释器是否运行在虚拟环境中。"""
    # venv/virtualenv 会设置 sys.prefix != sys.base_prefix
    return sys.prefix != sys.base_prefix


def list_packages(limit: int = 10) -> list[tuple[str, str]]:
    """列出已安装的第三方包（名称, 版本），最多 limit 个。"""
    dists = sorted(
        ((d.metadata["Name"], d.version) for d in md.distributions()),
        key=lambda x: x[0].lower(),
    )
    return dists[:limit]


def main() -> None:
    print(f"Python 版本      : {sys.version.split()[0]}")
    print(f"解释器路径       : {sys.executable}")
    print(f"sys.prefix       : {sys.prefix}")
    print(f"是否虚拟环境     : {in_virtualenv()}")

    req = Path("requirements.txt")
    print(f"requirements.txt : {'存在' if req.exists() else '不存在'}")

    print("\n前若干个已安装的包：")
    for name, ver in list_packages(10):
        print(f"  - {name}=={ver}")


if __name__ == "__main__":
    main()
```

## py.env.venv

# py.env.venv：Python 虚拟环境入门

> **一句话直觉**：虚拟环境（virtual environment）就是给你的每个 Python 项目一个独立的“小房间”，让不同项目依赖的包互不打架。

---

## 1. 为什么需要虚拟环境？

假设你同时开发两个项目：
- 项目 A 需要 `requests==2.25.0`
- 项目 B 需要 `requests==2.31.0`

如果所有包都装在系统 Python 里，后装的版本会覆盖前一个，项目 A 可能直接崩溃。虚拟环境让每个项目拥有独立的 `site-packages`（第三方包的安装目录），从根源上消除依赖冲突（dependency conflict）。

```python
# 演示：查看当前 Python 解释器所在位置
import sys

print(sys.executable)          # 系统 Python 的路径
print(sys.prefix)              # 当前环境的根目录
# 如果 sys.prefix 指向项目下的 .venv，说明你正处在虚拟环境中
```

---

## 2. venv 是什么？

`venv` 是 Python 标准库（standard library）自带的模块，从 Python 3.3 起可用。它能在指定目录下生成一个独立的 Python 环境：
- 复制一份 Python 解释器（interpreter）的入口；
- 创建独立的 `site-packages` 目录；
- 提供激活脚本（activation script），让 shell 的 `python` / `pip` 优先指向该环境。

```python
# 查看 venv 是否可用（标准库自带，无需安装）
import venv

print(venv.__file__)
# 输出类似：/usr/lib/python3.11/venv/__init__.py
# 只要 Python 版本 >= 3.3，venv 就天然存在
```

---

## 3. 创建与激活：命令行三步走

虚拟环境通过命令行创建和激活，这是每个 Python 工程师的基本功。

```bash
# 第 1 步：在项目根目录创建虚拟环境，目录名通常叫 .venv
python -m venv .venv

# 第 2 步：激活（不同平台命令不同）
# macOS / Linux
source .venv/bin/activate
# Windows (PowerShell)
# .venv\Scripts\Activate.ps1
# Windows (cmd)
# .venv\Scripts\activate.bat

# 第 3 步：验证并安装依赖
which python        # 应指向 .venv/bin/python
pip install requests==2.25.0

# 退出虚拟环境
deactivate
```

激活后，`python` 与 `pip` 都指向 `.venv` 内部，所有安装的包只影响本项目。

---

## 4. 在 Python 代码中感知虚拟环境

程序运行时可以通过 `sys.prefix` 与 `sys.base_prefix` 判断自己是否在虚拟环境中。这是工具链（如 pip、poetry）常用的技巧。

```python
import sys

def in_venv() -> bool:
    """判断当前解释器是否运行在虚拟环境中。
    原理：虚拟环境中 sys.prefix != sys.base_prefix。
    """
    return sys.prefix != sys.base_prefix

print("当前是否在 venv 中：", in_venv())
print("当前 prefix     ：", sys.prefix)
print("基础 prefix     ：", sys.base_prefix)
```

---

## 5. 依赖固化：requirements.txt

团队协作时，需要把依赖固定下来，让其他人一键复现环境。

```bash
# 导出当前环境所有依赖及精确版本
pip freeze > requirements.txt

# 在新机器上复现环境
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

`requirements.txt` 通常与 `.venv` 一起被纳入版本控制策略：`.venv` 要写进 `.gitignore`，`requirements.txt` 要提交到仓库。

---

## 动手练习

**任务**：为一个名为 `hello-venv` 的小项目创建独立环境，并验证依赖隔离。

步骤：
1. 新建目录 `hello-venv`，进入该目录。
2. 执行 `python -m venv .venv` 创建虚拟环境。
3. 激活它（macOS/Linux 用 `source .venv/bin/activate`）。
4. 写入一个 `check.py`，内容使用第 4 节的 `in_venv()` 函数，运行并确认输出 `True`。
5. 执行 `pip install requests`，再用 `pip freeze > requirements.txt`，查看 `requirements.txt` 内容。
6. 执行 `deactivate` 退出，再运行 `python check.py`，确认输出 `False`（回到系统环境）。
7. 把 `.venv/` 加入 `.gitignore`，把 `check.py` 和 `requirements.txt` 提交到 Git。

**验收标准**：能在几秒内解释“为什么激活后 `pip list` 看到的内容不同”，并能独立为任意新项目重复这套流程。

## py.env.pip

# py.env.pip：Python 包管理的起点

> **一句话直觉**：`pip` 是 Python 的"应用商店"，让你用一行命令把全世界共享的第三方库装进自己的项目——不会用它，你就只能用标准库造轮子。

---

## 1. 为什么需要 pip？（Why）

Python 自带的标准库（standard library）已经很强，但真正的工程能力来自**生态**：`requests` 发 HTTP、`numpy` 做数值、`pandas` 分析数据、`fastapi` 写服务。这些都不是 Python 自带的，需要从 [PyPI](https://pypi.org/)（Python Package Index，Python 包索引）下载安装。

`pip` 就是官方推荐的安装器（package installer），全称 **"Pip Installs Packages"**。它是你从"会写 Python"到"能用 Python 做工程"的第一道门槛。

**核心心智模型**：

```
你  ──pip install──▶  PyPI（云端仓库）──下载──▶ 你的 Python 环境 site-packages/
```

---

## 2. 检查与基础命令：pip 在哪里、能做什么

### 2.1 确认 pip 是否可用

```bash
python -m pip --version
# 输出示例：pip 24.x from .../site-packages/pip (python 3.12)
```

> **推荐永远写 `python -m pip` 而不是裸 `pip`**：这样能保证 pip 与你当前调用的 `python` 解释器绑定，避免"装了但 import 不到"的经典事故。

### 2.2 四个高频命令

| 命令 | 作用 |
|---|---|
| `pip install <pkg>` | 安装包 |
| `pip uninstall <pkg>` | 卸载包 |
| `pip list` | 列出已安装包 |
| `pip show <pkg>` | 查看某包的版本、依赖、安装位置 |

用 Python 代码验证 pip 是否在解释器里可用（本章节第一个可运行示例）：

```python
import subprocess
import sys

# 用当前解释器调用 pip，保证一致性
result = subprocess.run(
    [sys.executable, "-m", "pip", "--version"],
    capture_output=True, text=True
)
print("returncode:", result.returncode)
print(result.stdout.strip())
```

---

## 3. 隔离：虚拟环境（virtual environment）

### 3.1 为什么必须隔离？

假设 A 项目要 `requests==2.28`，B 项目要 `requests==2.31`。如果都装进全局 Python，必然冲突。**虚拟环境**为每个项目创建一份独立的 `site-packages`，互不干扰。

### 3.2 创建与激活

```bash
# 创建：在项目目录下生成 .venv 文件夹
python -m venv .venv

# 激活
# Windows (PowerShell):  .venv\Scripts\Activate.ps1
# macOS / Linux:         source .venv/bin/activate

# 激活后提示符会出现 (.venv)，此时 pip install 只影响当前项目
deactivate   # 退出
```

> **工程惯例**：每个项目一个 `.venv`，并把 `.venv/` 写进 `.gitignore`，不要提交到 Git。

---

## 4. 版本控制与可复现：`requirements.txt`

### 4.1 三种写法

```
requests             # 任意版本
requests==2.31.0     # 精确锁定（生产环境推荐）
requests>=2.28,<3    # 区间约束
```

### 4.2 导出与还原

```bash
pip freeze > requirements.txt          # 导出当前环境的精确版本
pip install -r requirements.txt        # 在别的机器上完整复现
```

这一步是团队协作与 CI/CD 的基石——没有它，"我本地能跑"就是常态。

---

## 5. pip 与 Python 程序的关系：在代码里查询包信息

pip 安装的包，最终会出现在 `sys.path` 能搜到的 `site-packages` 目录里。用 `importlib.metadata` 可以在运行时查询已安装包的版本和元数据——这是写"自检脚本"的常用手法。

> 小结：`pip` 负责"装"，`venv` 负责"隔"，`requirements.txt` 负责"锁"，三者构成 Python 环境管理的三件套。

```python
"""
演示：用 Python 代码查询当前环境里已安装的包信息。
无需第三方依赖，标准库即可运行。
"""
from importlib import metadata

# 1) 查询某个包是否已安装（以 pip 自身为例，它总是存在）
try:
    dist = metadata.distribution("pip")
    print(f"pip version: {dist.version}")
    print(f"安装位置: {dist.locate_file('')}")
except metadata.PackageNotFoundError:
    print("未找到 pip")

# 2) 列出前 10 个已安装的包（按字母序）
installed = sorted(
    (d.metadata["Name"], d.version) for d in metadata.distributions()
)
print("\n已安装包（前 10 个）:")
for name, version in installed[:10]:
    print(f"  {name}=={version}")

# 3) 检查某个常用第三方包是否可用（不 import，避免副作用）
for pkg in ["requests", "numpy", "flask"]:
    try:
        v = metadata.version(pkg)
        print(f"\n{pkg} 已安装，版本 {v}")
    except metadata.PackageNotFoundError:
        print(f"\n{pkg} 未安装，可执行：python -m pip install {pkg}")
```

## py.hello.print

# py.hello.print：从 `print` 理解程序与世界的第一次对话

> **一句话直觉**：`print` 是程序向外部世界说出的第一句话——学会它，你就能让代码“开口”，并且开始验证你写的每一行逻辑。

---

## 0. 为什么第一课是 `print`？

学习任何语言，第一步都不是语法本身，而是**获得反馈（feedback）**。在 Python 里，`print` 是最简单、最直接的反馈工具：它把值写到标准输出（standard output，通常就是终端/命令行窗口）。

没有 `print`，你写的变量、表达式、分支和循环都像在黑屋子里运行。有了 `print`，你能观察、调试、验证，从而建立“代码 → 结果”的直觉。

---

## 1. 最小可用惊喜：`print` 就是“打印”

`print` 是 Python 的内置函数（built-in function），你无须 `import` 就能用。

```python
# 最基本的用法：把字符串打印到屏幕
print("Hello, Python!")
```

运行后终端会显示：

```text
Hello, Python!
```

**关键结论**：`print` 把参数转换成人类可读的文本，再输出到标准输出。

---

## 2. `print` 可以打印“值”，不只是一句话

你不需要手动把数字、布尔值、列表转成字符串——`print` 会自动做**字符串化（string conversion）**。

```python
# 打印不同类型的值：字符串、整数、浮点数、布尔值、列表
print("整句话")
print(42)
print(3.14)
print(True)
print([1, 2, 3])
```

输出：

```text
整句话
42
3.14
True
[1, 2, 3]
```

**关键结论**：`print` 接受任意类型的对象，并在输出前调用其人类友好的文本表示。

---

## 3. 多个值、分隔符与结尾：`sep` 和 `end`

`print` 可以一次打印多个值，默认用空格分隔。你还可以用 `sep`（separator，分隔符）和 `end`（结尾字符）改变行为。

```python
# 多个值：默认用空格分隔
print("姓名:", "小明", "年龄:", 18)

# 自定义分隔符：用 " | " 隔开
print("苹果", "香蕉", "橘子", sep=" | ")

# end 默认是换行符 \n；改成空字符串，下一句 print 会接在同一行
print("加载中", end="")
print("...", end="")
print("完成!")
```

输出：

```text
姓名: 小明 年龄: 18
苹果 | 香蕉 | 橘子
加载中...完成!
```

**关键结论**：`sep` 控制多个参数之间的连接方式；`end` 控制这次 `print` 结束后追加什么字符。

---

## 4. 让输出“有结构”：f-string 格式化

工程里很少只打印裸变量。更常见的是把变量嵌进一句话，用 **f-string（formatted string literal，格式化字符串字面量）**。

```python
# f-string：在字符串前加 f，用 {} 嵌入表达式
name = "Alice"
score = 95.5

print(f"学生 {name} 的分数是 {score}")
print(f"分数保留一位小数：{score:.1f}")
```

输出：

```text
学生 Alice 的分数是 95.5
分数保留一位小数：95.5
```

**关键结论**：`print` 负责输出，f-string 负责在输出前把值安全、清晰地组合成文本。

---

## 5. 工程级视角：`print` 不是日志（logging）

`print` 适合学习和临时调试，但它有几个工程限制：

- 无法方便地分级（debug/info/warning/error）；
- 无法自动带上时间、模块、行号；
- 无法按环境（开发/生产）过滤；
- 大量输出时性能和管理都不如 `logging`。

所以工程中常见的做法是：学习和快速验证用 `print`，正式项目用 `logging`。

```python
# 快速调试可以用 print
x = 10
y = 0

print("调试：x =", x, "y =", y)

# 正式项目更推荐 logging（这里只做对比，不展开）
import logging
logging.basicConfig(level=logging.INFO)
logging.info("x=%s y=%s", x, y)
```

**关键结论**：`print` 是起点，不是终点。理解它的边界，是从“会写代码”走向“会做工程”的第一步。

---

## 动手练习

**任务：写一个“个人名片打印器”**

1. 新建一个文件 `card.py`。
2. 定义三个变量：`name`（字符串）、`age`（整数）、`hobby`（字符串）。
3. 用 `print` 和 f-string 输出一张三行名片，例如：

```text
====================
姓名：小明
年龄：18
爱好：写代码
====================
```

4. 再额外打印一行：把 `age` 加 1，输出“明年我 19 岁”。

**验收标准**：终端输出必须包含 5 行，且姓名、年龄、爱好来自变量，而不是写死在字符串里。

---

## 小结

- `print` 是 Python 的**内置函数**，负责把值输出到标准输出。
- 它能自动处理多种类型，支持多参数、`sep` 和 `end`。
- f-string 让输出更可读、更工程化。
- `print` 适合学习和调试，正式项目应逐步过渡到 `logging`。

```python
# 一个可直接运行的完整示例：展示 print 的核心用法

name = "小明"
age = 18
hobby = "写代码"

# 1) 基本打印
print("Hello, Python!")

# 2) 多值 + 自定义分隔符
print("姓名:", name, "年龄:", age, sep=" | ")

# 3) end 控制结尾，让两次 print 接在同一行
print("加载中", end="")
print("...", end="")
print("完成!")

# 4) f-string 格式化输出
print(f"{name} 的爱好是 {hobby}。")
print(f"明年他 {age + 1} 岁。")

# 5) 打印一个列表和布尔值
print([1, 2, 3])
print(age > 10)
```


---

## 本课题目

### single_choice · None



- [A] 从 Python 官方标准库目录中复制
- [B] 从配置的包索引（默认是 PyPI）下载对应发行包并安装
- [C] 从当前工作目录中查找同名 .py 文件直接加载
- [D] 从操作系统自带的软件仓库中安装

**参考答案**：1

**解析**：pip 是 Python 的包安装工具，默认从配置的索引（通常为 PyPI）解析并下载发行包（wheel/sdist）后安装，而不是从标准库或当前目录加载文件。

### single_choice · None



- [A] 每次安装都加上 --force-reinstall 参数
- [B] 把 numpy 卸载后再重新安装旧版本
- [C] 为每个项目创建独立的虚拟环境，在各自环境内安装依赖
- [D] 把 numpy 源码复制到项目目录里随项目一起提交

**参考答案**：2

**解析**：全局安装会让所有项目共享同一版本，容易产生版本冲突。为每个项目使用独立虚拟环境可隔离依赖，从根本上避免相互影响。

### multi_choice · None



- [A] 该包从未在当前使用的解释器环境中安装
- [B] 安装该包时使用的 pip 属于另一个解释器环境
- [C] 包已安装但名字写错（大小写或拼写错误）
- [D] 该包已安装且版本满足当前 Python 版本要求

**参考答案**：[0, 1, 2]

**解析**：未安装、装错环境、名字拼写错误都会导致导入失败；若已安装且版本兼容，导入会成功。

### multi_choice · None



- [A] 可以事先在有网环境用 pip 下载 wheel 文件，再拷贝到离线机器安装
- [B] 离线机器上的 pip 无法从 PyPI 拉取包，需要指定本地文件或目录
- [C] 只要包名写对，离线环境下 pip 仍能自动联网获取
- [D] 可以在有网环境构建好 wheel，然后离线安装以规避本地编译依赖

**参考答案**：[0, 1, 3]

**解析**：离线时 pip 无法访问远端索引，需要提供本地 wheel/目录。预先构建 wheel 可避免目标机器缺少编译工具链。C 项与离线前提矛盾。

### fill_blank · None



**参考答案**：["-r", "--requirement", "-r ", "--requirement="]

**解析**：pip 通过 -r/--requirement 指定需求文件，从文件中读取并安装依赖列表。

### fill_blank · None



**参考答案**：["venv"]

**解析**：Python 3 从 3.3 起在标准库中提供了 venv 模块用于创建虚拟环境。

### fill_blank · None



**参考答案**：["activate", "activate.sh"]

**解析**：虚拟环境提供 activate 脚本，source 该脚本后当前 shell 的解释器路径切换到该环境。

### code_reading · None



**参考答案**：报告的是 .venv 这个虚拟环境中的 pip。因为激活 .venv 后，shell 的 PATH 优先指向 .venv 的 bin 目录，pip 与 python 都指向该虚拟环境；且用 python -m pip 安装的 requests 也装进了该环境。

**解析**：激活虚拟环境后，PATH 被前置，pip 与 python 均解析到虚拟环境内的可执行文件，因此 pip 属于该虚拟环境，安装也落在其 site-packages。

### code_reading · None



**参考答案**：会安装到当前用户级的 site-packages（用户目录下的 Python 用户包目录），而不是系统全局 site-packages。因为使用了 --user，pip 将包安装到用户目录，避免写入系统目录；-m pip 保证使用的是 /usr/bin/python3 对应的 pip。

**解析**：--user 将安装限定在当前用户可见的用户站点目录，配合 `python -m pip` 确保了安装目标解释器与所调用的解释器一致。

### scenario · None



**解析**：典型原因是他在全局环境中安装，且此前已存在不满足约束的旧版本，或 requirements.txt 未固定版本。应先用独立虚拟环境隔离，确认 pip 与解释器一致，再核对依赖版本约束并补全固定版本。

### scenario · None



**解析**：应在有网且有编译环境处预先构建好 wheel，再拷贝到离线机器用本地 wheel 安装，从而规避目标机器缺编译工具链的问题，也保证依赖版本一致。

### single_choice · None



- [A] 它会下载并安装 myenv 这个第三方包
- [B] 它会创建一个名为 myenv 的目录，其中包含一套独立的 Python 运行环境
- [C] 它会把当前解释器升级到最新版本
- [D] 它只能用于 Python 2，Python 3 需要使用 virtualenv

**参考答案**：1

**解析**：venv 是标准库模块，`python -m venv myenv` 会在 myenv 目录下创建独立的 Python 环境（含解释器链接、pip 等），与下载第三方包无关。

### single_choice · None



- [A] 在脚本里用 try/except 包住 import
- [B] 把包名重新拼写一遍再安装
- [C] 用 B 环境对应的 python 执行 `python -m pip install 包名`
- [D] 把该包的源码手动复制到 site-packages 之外

**参考答案**：2

**解析**：问题根源是安装目标和运行目标不是同一个解释器。使用 `python -m pip` 可确保 pip 属于当前解释器，从而安装到正确的环境。

### single_choice · None



- [A] 记录项目源码中所有函数的定义
- [B] 声明项目所依赖的包及其版本约束，便于他人复现环境
- [C] 保存 Python 解释器的编译参数
- [D] 列出项目所有的测试用例名称

**参考答案**：1

**解析**：requirements.txt 用于声明依赖及版本，配合 `pip install -r requirements.txt` 可以复现依赖环境。

### single_choice · None



- [A] 前者精确锁定到该版本，后者允许安装不低于该版本的任意兼容版本
- [B] 两者完全等价，只是书写风格不同
- [C] 前者安装源码，后者安装二进制包
- [D] 前者安装到全局，后者安装到虚拟环境

**参考答案**：0

**解析**：== 是精确版本约束，>= 是最低版本约束。二者只影响版本解析，与安装来源或环境无关。

### single_choice · None



- [A] 源码分发包 sdist（.tar.gz）
- [B] 二进制轮子 wheel（.whl）
- [C] 操作系统原生安装包（.deb / .msi）
- [D] 压缩后的 .pyc 字节码文件

**参考答案**：1

**解析**：wheel 是预编译的二进制分发格式，安装时无需本地构建。pip 默认优先选择 wheel，只有在没有匹配 wheel 时才回退到 sdist。

### single_choice · None



- [A] 它只在一个新的虚拟环境中生效
- [B] 它会把已安装的该包升级到满足约束的较新版本，而不是重复安装旧版本
- [C] 它会卸载该包及其所有依赖
- [D] 它等价于 `pip uninstall 包名`

**参考答案**：1

**解析**：--upgrade 会让 pip 在解析依赖时允许替换已安装版本为更新的版本，而非固定保留旧版本。

### multi_choice · None



- [A] 在 requirements.txt 中记录依赖并固定版本
- [B] 把项目依赖安装到全局 site-packages 而不做任何记录
- [C] 使用虚拟环境隔离项目依赖
- [D] 在文档中说明所用的 Python 版本

**参考答案**：[0, 2, 3]

**解析**：记录并固定依赖、隔离环境、说明解释器版本都有助于复现；无记录的全局安装恰恰是环境不可复现的常见原因。

### multi_choice · None



- [A] 虚拟环境拥有自己独立的 site-packages，安装的包默认只影响该环境
- [B] 激活虚拟环境后，命令行中的 python 通常指向该环境的解释器
- [C] 虚拟环境会自动隔离操作系统级别的系统库（如 libc）
- [D] 无论是否激活，只要用 `python -m pip` 都能保证装到当前解释器对应环境

**参考答案**：[0, 1, 3]

**解析**：虚拟环境隔离的是 Python 层面的包与解释器，不隔离操作系统系统库，因此 C 项错误。用 `python -m pip` 可确保 pip 与解释器一致。

### single_choice · None



- [A] venv 是第三方库，必须先 pip install venv 才能使用
- [B] venv 是标准库模块，可用 python -m venv 命令创建虚拟环境
- [C] venv 只能创建 Python 3.3 以下版本的虚拟环境
- [D] venv 创建的虚拟环境必须联网才能激活

**参考答案**：1

**解析**：venv 自 Python 3.3 起加入标准库，无需额外安装，可用 python -m venv <目录> 创建虚拟环境。A 错在它是标准库；C 错在版本方向相反；D 激活与网络无关。

### single_choice · None



- [A] 直接运行 python，会自动进入虚拟环境
- [B] 在 Windows 上执行 .venv\Scripts\activate，在类 Unix 上执行 source .venv/bin/activate
- [C] 执行 .venv/activate.py
- [D] 把 .venv 目录加入 PYTHONPATH 即可，无需激活

**参考答案**：1

**解析**：venv 的激活脚本位于 Scripts（Windows）或 bin（类 Unix）下。修改 PYTHONPATH 不等于激活，也不会切换解释器与 pip。

### single_choice · None



- [A] 把 env 中已安装的第三方包升级到最新版
- [B] 就地更新 env 环境，使其与运行该命令所用的 Python 解释器版本保持一致
- [C] 把 env 环境复制到另一个目录
- [D] 把 env 环境导出为 requirements.txt

**参考答案**：1

**解析**：--upgrade 用于升级环境本身（如跟随新的基础解释器版本），并非升级其中的第三方包（那是 pip 的职责）。

### multi_choice · None



- [A] 虚拟环境是一个包含独立解释器入口和 site-packages 的目录
- [B] 激活虚拟环境会修改当前 shell 的 PATH，使 python/pip 指向该环境
- [C] 删除虚拟环境目录即等于卸载该环境
- [D] 虚拟环境创建后必须联网才能使用
- [E] 虚拟环境能让不同项目使用互不冲突的依赖版本

**参考答案**：[0, 1, 2, 4]

**解析**：venv 的本质是目录，激活通过 PATH 生效，删除目录即移除环境，核心价值是依赖隔离。使用虚拟环境完全不需要联网。

### multi_choice · None



- [A] 每个项目使用独立的虚拟环境
- [B] 把虚拟环境目录加入 .gitignore
- [C] 依赖清单（如 requirements.txt）提交到版本库
- [D] 为了避免重建，把 .venv 一起提交以便他人直接使用
- [E] 升级基础 Python 后，必要时用 --upgrade 更新已有环境

**参考答案**：[0, 1, 2, 4]

**解析**：按项目隔离环境、忽略环境目录、提交依赖清单是通行实践；提交 .venv 会因平台差异和体积带来问题，不推荐。

### multi_choice · None



- [A] Windows 下激活脚本在 Scripts 目录，类 Unix 下在 bin 目录
- [B] 激活脚本会把环境的可执行目录置于 PATH 前面
- [C] 未激活时直接使用环境的绝对路径 python 也是可行的
- [D] 激活脚本会修改项目源码
- [E] 激活是使用虚拟环境的唯一途径

**参考答案**：[0, 1, 2]

**解析**：激活主要靠 PATH 前置实现；直接调用 .venv/bin/python 也可使用环境，所以激活并非唯一途径。激活脚本不会改动项目源码。

### multi_choice · None



- [A] 创建时不使用 --system-site-packages
- [B] 在激活状态下用该环境的 pip 安装依赖
- [C] 用全局 pip 安装项目依赖
- [D] 在依赖清单中明确记录所需包与版本
- [E] 多处项目共用同一个虚拟环境目录

**参考答案**：[0, 1, 3]

**解析**：默认隔离（不加 --system-site-packages）、在环境内安装、用清单声明依赖都能维持隔离与可复现。全局 pip 安装和多项目共用环境都会破坏隔离。

### fill_blank · None



**参考答案**：["venv"]

**解析**：标准做法是 python -m venv .venv，venv 是标准库中负责创建虚拟环境的模块。

### fill_blank · None



**参考答案**：["bin", "bin/"]

**解析**：类 Unix 下可执行文件与激活脚本位于 bin 目录；Windows 下则位于 Scripts 目录。

### fill_blank · None



**参考答案**：["pyvenv", "pyvenv.cfg"]

**解析**：该文件是 pyvenv.cfg，描述环境创建时所用的解释器信息，不是依赖清单。

### code_reading · None



**参考答案**：会指向全局解释器前缀。因为创建虚拟环境不会自动激活；未激活时当前 shell 中的 python 仍解析为全局解释器，sys.prefix 反映的是该全局环境。若希望指向 env，需要先激活（或在类 Unix 下直接执行 env/bin/python）。

**解析**：考察点是「创建」与「激活」是两步且相互独立，创建后不激活不改变当前 shell 的解释器解析。

### code_reading · None



**参考答案**：A 创建的默认环境是隔离的，看不到全局 site-packages 中已安装的包，import 该包会失败（除非该环境内也装了）。B 使用 --system-site-packages，环境可以访问全局 site-packages，因此能 import 成功。

**解析**：考察隔离性开关。默认隔离；--system-site-packages 会放开对全局包的可见性，但这也可能引入版本不确定性。

### single_choice · None



- [A] 禁止虚拟环境访问全局安装的包
- [B] 让虚拟环境可以使用全局 site-packages 中已安装的包
- [C] 把虚拟环境中的包安装到全局 site-packages
- [D] 只在系统 Python 版本上创建环境

**参考答案**：1

**解析**：该选项使新环境继承全局 site-packages 的可见性。默认情况下虚拟环境是隔离的，不会看到全局包。

### scenario · None



**解析**：正确流程：用 python -m venv 创建环境 → 激活 → 用该环境的 pip 依据 requirements.txt 安装依赖 → 再运行程序。直接运行失败是因为依赖未被安装到当前全局解释器，虚拟环境尚未创建/激活，体现了依赖隔离的必要性。

### scenario · None



**解析**：全局升级会影响其他依赖旧版本的项目，可能造成版本冲突，是脆弱做法。更稳妥的是为该项目创建独立虚拟环境，在其中安装所需的新版本，并用 requirements.txt 固定依赖，从而实现项目间的依赖隔离。

### single_choice · None



- [A] 虚拟环境只隔离 pip，不隔离已安装的第三方包
- [B] 在虚拟环境中 pip install 的包默认只安装到该环境，不影响全局
- [C] 激活虚拟环境后，python 命令仍指向全局解释器
- [D] 虚拟环境之间共享 site-packages 目录

**参考答案**：1

**解析**：虚拟环境的核心价值是依赖隔离：其 site-packages 独立，pip 安装落在环境内。激活后 python/pip 都指向该环境。

### single_choice · None



- [A] 执行 pip uninstall venv
- [B] 执行 python -m venv --delete <目录>
- [C] 直接删除虚拟环境所在的整个目录
- [D] 运行 deactivate 后环境即被删除

**参考答案**：2

**解析**：虚拟环境本质上是一个自包含目录，删除目录即可移除环境。deactivate 只是退出当前会话的激活状态，不删除环境。venv 没有 --delete 选项。

### single_choice · None



- [A] 它是激活虚拟环境必须执行的脚本
- [B] 它记录了该环境的基础解释器路径、版本等信息
- [C] 它列出了环境内已安装的所有第三方包及其版本
- [D] 它是 Python 源码文件，可被 import

**参考答案**：1

**解析**：pyvenv.cfg 描述环境的创建信息（如 home、version 等）。它不是可执行脚本，也不是依赖清单；依赖清单由 pip freeze 生成。

### single_choice · None



- [A] requests 被安装进 env 虚拟环境
- [B] requests 被安装进全局解释器环境，因为未激活虚拟环境
- [C] 命令会报错，提示必须先激活
- [D] pip 会自动激活 env 后再安装

**参考答案**：1

**解析**：创建虚拟环境不会自动激活。未激活时终端里的 pip 仍指向全局解释器，因此包会装到全局环境。

### single_choice · None



- [A] venv 可以管理非 Python 的系统级依赖，conda 不能
- [B] venv 面向 Python 包依赖隔离，conda 还能管理非 Python 的二进制依赖
- [C] 两者本质相同，conda 只是 venv 的图形界面
- [D] venv 创建的环境不能被 pip 使用

**参考答案**：1

**解析**：venv 只隔离 Python 层面的包；conda 是跨语言的包与环境管理器，可管理如编译器、本地库等非 Python 依赖。

### single_choice · None



- [A] 虚拟环境被删除
- [B] 退出当前虚拟环境，终端恢复到激活前的解释器环境
- [C] 卸载环境中所有已安装的包
- [D] 重新创建虚拟环境

**参考答案**：1

**解析**：deactivate 只是退出激活状态，恢复 PATH 及相关环境变量，不会删除环境或卸载包。

### single_choice · None



- [A] 把整个 .venv 目录提交进 Git
- [B] 提交用 pip freeze 导出的 requirements.txt，并在 .gitignore 中忽略 .venv
- [C] 只提交 pyvenv.cfg
- [D] 提交虚拟环境中的 python 可执行文件

**参考答案**：1

**解析**：虚拟环境目录大且与平台相关，不应入库；依赖应通过 requirements.txt 等清单文件表达，他人可据此重建环境。

### single_choice · None



- [A] python -m pip install 包名
- [B] python install pip 包名
- [C] pip install python 包名
- [D] install pip 包名

**参考答案**：0

**解析**：推荐使用 `python -m pip install 包名`，它会明确使用当前 python 解释器对应的 pip，避免多环境混乱。其他写法把模块名和参数顺序搞错，不是合法命令。

### single_choice · None



- [A] 从本地 Python 安装目录中查找
- [B] 从 Python 官方包索引 PyPI 下载
- [C] 从 GitHub 仓库克隆源码编译
- [D] 从操作系统自带的软件源安装

**参考答案**：1

**解析**：pip 默认从 PyPI（Python Package Index）下载包及其依赖。本地目录、GitHub、系统软件源都不是默认来源。

### single_choice · None



- [A] 包的版本号
- [B] 包的作者或主页信息
- [C] 包的依赖列表
- [D] 该包在 PyPI 上的累计下载量

**参考答案**：3

**解析**：`pip show` 会显示名称、版本、摘要、作者、主页、依赖等元数据，但不包含 PyPI 上的下载统计信息。

### multi_choice · None



- [A] 为每个项目创建独立的虚拟环境
- [B] 用 requirements.txt 记录并固定依赖版本
- [C] 把所有包都安装到系统全局环境
- [D] 在项目中使用带版本约束的依赖声明

**参考答案**：[0, 1, 3]

**解析**：虚拟环境隔离、固定版本记录、版本约束声明都能降低冲突。把包统统装进系统全局环境恰恰是冲突的主要来源。

### multi_choice · None



- [A] 用 `pip install --upgrade 包名` 升级到较新版本
- [B] 用 `pip install --force-reinstall 包名` 强制重新安装
- [C] 直接忽略提示，因为已安装的版本一定满足需求
- [D] 用 `pip show 包名` 先确认当前已安装的版本

**参考答案**：[0, 1, 3]

**解析**：升级、强制重装、先确认版本都是合理做法。直接忽略提示并不安全，因为已安装版本可能不满足当前项目的版本要求。

### multi_choice · None



- [A] install
- [B] uninstall
- [C] list
- [D] compile

**参考答案**：[0, 1, 2]

**解析**：`install`、`uninstall`、`list` 都是 pip 的子命令；`compile` 不是 pip 的子命令（Python 有 compileall 模块用于编译字节码，但那是另一回事）。

### multi_choice · None



- [A] 它只安装指定的包，不自动安装其依赖
- [B] 使用后可能导致运行时缺少依赖而报错
- [C] 它会自动把所有依赖降级到最低版本
- [D] 它可用于只想单独获取某个包文件的场景

**参考答案**：[0, 1, 3]

**解析**：`--no-deps` 就是不安装依赖，因此可能造成运行时缺依赖，也可用于只拿单个包。它并不做任何降级操作。

### fill_blank · None



**参考答案**：["show"]

**解析**：`pip show 包名` 用于显示已安装包的元数据。`list` 只列出名称和版本，信息不如 show 详细。

### fill_blank · None



**参考答案**：["-r", "--requirement", "-r ", " --requirement"]

**解析**：`-r`（或长写 `--requirement`）用于指定需求文件，pip 会读取其中列出的包并安装。

### code_reading · None



**参考答案**：该命令通过 `==` 指定了精确版本号，pip 会安装 requests 的 2.31.0 版本，而不是默认可用的最新版本。这有助于固定依赖版本、保证环境可复现。

**解析**：在需求规格中使用 `==` 表示精确版本匹配。直接安装不带版本约束时 pip 通常选择满足条件的最新版本，可能随发布时间变化。

### code_reading · None



**参考答案**：pip 会选择版本号大于等于 2.28 且小于 3.0 的 requests 最新可用版本。这样写既保证获得包含所需修复的较新版本，又避免升级到可能存在不兼容变更的 3.0 及更高主版本。

**解析**：`>=` 和 `<` 组合形成版本区间，允许一定灵活性的同时防止跨主版本升级带来的破坏性变更。

### scenario · None



**解析**：最常见原因是 requirements.txt 是从旧环境导出、遗漏了后来新增的依赖，或开发者手动维护时忘记添加。应在新环境中补全依赖并用 `pip freeze` 重新导出更新后的 requirements.txt。

### single_choice · None



- [A] 两者完全相同，只是名称不同
- [B] `pip install` 下载并安装，`pip download` 只下载不安装
- [C] `pip download` 下载并安装，`pip install` 只下载
- [D] `pip install` 只能装标准库，`pip download` 只能装第三方库

**参考答案**：1

**解析**：`pip install` 会下载并安装包；`pip download` 只把包文件下载到本地而不安装，常用于离线部署。两者都不限于标准库或第三方库。

### scenario · None



**解析**：应使用 `pip install --user 包名`，它把包安装到当前用户的主目录站点包目录，无需管理员权限，也不会改动系统全局环境，因此不影响其他用户。

### single_choice · None



- [A] 列出当前环境中已安装的包及其版本
- [B] 列出 PyPI 上所有可安装的包
- [C] 列出 pip 支持的子命令
- [D] 列出包的依赖关系树

**参考答案**：0

**解析**：`pip list` 显示当前环境中已安装的包和版本。查看依赖树应使用 `pip show` 或专门工具；查看 pip 子命令用 `pip help`。

### single_choice · None



- [A] pip update 包名
- [B] pip upgrade 包名
- [C] pip install --upgrade 包名
- [D] pip install --latest 包名

**参考答案**：2

**解析**：pip 没有独立的 `update` 或 `upgrade` 子命令，升级包要使用 `pip install --upgrade 包名`（可简写 `-U`）。`--latest` 也不是有效选项。

### single_choice · None



- [A] pip delete 包名
- [B] pip remove 包名
- [C] pip uninstall 包名
- [D] pip erase 包名

**参考答案**：2

**解析**：pip 卸载包使用 `pip uninstall 包名`。`delete`、`remove`、`erase` 都不是 pip 的子命令。

### single_choice · None



- [A] 把包安装到当前用户的主目录下，而非系统级目录
- [B] 把包安装为所有用户都可用的系统级包
- [C] 以 root 权限执行安装
- [D] 把包安装到当前工作目录

**参考答案**：0

**解析**：`--user` 表示安装到用户级目录（如用户主目录下的站点包目录），无需管理员权限，也不会影响系统级环境。

### single_choice · None



- [A] 把当前环境已安装包及版本写入 requirements.txt
- [B] 把 requirements.txt 中的包全部安装一遍
- [C] 锁定项目源代码的版本
- [D] 冻结 pip 使其无法再安装新包

**参考答案**：0

**解析**：`pip freeze` 输出当前环境中已安装包及其精确版本，重定向到 requirements.txt 常用于记录依赖以便后续复现环境。反向操作是 `pip install -r requirements.txt`。

### single_choice · None



- [A] 把当前环境所有包导出到 requirements.txt
- [B] 按照 requirements.txt 中列出的依赖进行安装
- [C] 只安装 requirements.txt 中缺少的标准库
- [D] 删除 requirements.txt 中列出的包

**参考答案**：1

**解析**：`-r` 表示从给定的需求文件读取依赖列表并安装。导出用 `pip freeze`，删除用 `pip uninstall`。

### single_choice · None



- [A] 用 `pip install --index-url <镜像地址> 包名` 指定镜像源
- [B] 用 `pip install --no-deps 包名` 跳过所有依赖
- [C] 用 `pip install --force-reinstall 包名` 强制重装
- [D] 用 `pip install --ignore-installed 包名` 忽略已装包

**参考答案**：0

**解析**：更换源应通过 `--index-url`（或 `-i`）指定镜像地址。`--no-deps` 只跳过依赖安装，`--force-reinstall`、`--ignore-installed` 解决的是重装/覆盖问题，都不能解决访问源的问题。

### single_choice · None



- [A] 把数据保存到文件
- [B] 把数据输出到控制台（标准输出）
- [C] 从用户读取输入
- [D] 计算表达式的值

**参考答案**：1

**解析**：print 用于把对象转换成文本显示到标准输出，不负责读取输入（那是 input 的职责），也不负责持久化存储。

### single_choice · None



- [A] HelloWorld
- [B] Hello World
- [C] Hello, World
- [D] Hello
  World

**参考答案**：1

**解析**：print 在多个参数之间默认插入一个空格作为分隔符，因此是 Hello World。

### multi_choice · None



- [A] print("a", end="")
- [B] print("a", end="
  ")
- [C] print("a", end="--")
- [D] print("a")

**参考答案**：[0, 2]

**解析**：end 参数决定末尾字符。end="" 不换行，end="--" 添加 --；end="\n" 和不传 end 都是默认换行，与题意（非换行字符）不符。

### multi_choice · None



- [A] 第一行输出 a*b*c
- [B] 第一行输出 a b c
- [C] 第二行输出 end
- [D] 整体输出只有一行

**参考答案**：[0, 2]

**解析**：sep="*" 使第一行成为 a*b*c 并以换行结束，第二行独立输出 end，所以有两行。

### fill_blank · None



**参考答案**：["end", "END"]

**解析**：控制输出结尾字符的参数名是 end，设为空字符串即可不换行。

### fill_blank · None



**参考答案**：["\"-\"", "'-'", "-"]

**解析**：sep 的值是字符串，写成 "-" 或 '-'，输出时用短横线连接各参数。

### fill_blank · None



**参考答案**：["A B", "A B\\n（即A空格B）"]

**解析**：多参数默认以空格分隔，故显示 A B。

### code_reading · None



**参考答案**：123

**解析**：前两次调用 end="" 不换行，第三次默认换行；因此三个数字连成一行 123。

### code_reading · None



**参考答案**：py-is-fun

**解析**：sep="-" 将三个参数用短横线连接，输出 py-is-fun。

### scenario · None



**解析**：关键在于把 print 的 end 参数设为空字符串（或不换行的字符），从而不自动换行；若还需控制多参数间分隔，可用 sep 指定为空格。

### scenario · None



**解析**：最常见原因是 sep 参数名拼写错误、把分隔符写在字符串里而没有用 sep 关键字，或误以为默认就已生效；正确写法是 print(a, b, sep="|")，确保关键字参数名和值都正确。

### scenario · None



**解析**：把 sep 设为空字符串 sep=""，即可去掉参数之间默认的空格分隔，得到 abc。

### single_choice · None



- [A] a-b
- [B] a b
- [C] a,b
- [D] ab

**参考答案**：0

**解析**：sep 参数用于指定多个参数之间的分隔字符串，sep="-" 时用短横线连接。

### single_choice · None



- [A] a b
- [B] ab
- [C] a
  b
  （即 a 和 b 各占一行）
- [D] a
  b（同一行显示）

**参考答案**：2

**解析**：print 默认以换行结尾（end="\n"），因此每次调用都会换行，a 和 b 各占一行。

### single_choice · None



- [A] a
  b
- [B] ab
- [C] a b
- [D] a
  b
  

**参考答案**：1

**解析**：第一个 print 的 end 被设为空字符串，因此不换行；第二个 print 接着输出 b，最终显示 ab。

### single_choice · None



- [A] print(1, 2, 3)
- [B] print("1"+"2"+"3")
- [C] print(1 2 3)
- [D] print(1; 2; 3)

**参考答案**：0

**解析**：print 接受多个参数并以空格分隔。选项 B 只输出 123，选项 C、D 是语法错误。

### single_choice · None



- [A] "1 + 2"
- [B] 3
- [C] "3"（带引号）
- [D] 报错

**参考答案**：1

**解析**：print 会先计算参数表达式的值，1+2 得到整数 3，然后打印其文本形式 3（不带引号）。

### single_choice · None



- [A] 返回输出的字符串
- [B] 返回输出的字符个数
- [C] 返回 None
- [D] 返回 True 表示成功

**参考答案**：2

**解析**：print 只负责输出，不返回有用结果，其返回值是 None。

### single_choice · None



- [A] x y!
- [B] xy!
- [C] x-y!
- [D] xy

**参考答案**：1

**解析**：sep="" 去掉了参数间分隔符，多余空格消失，得到 xy，再以 end="!" 结尾。

### multi_choice · None



- [A] print 默认在参数之间用一个空格分隔
- [B] print 默认在输出末尾添加换行符
- [C] print 可以一次输出多个参数
- [D] print 的返回值是输出内容的字符串

**参考答案**：[0, 1, 2]

**解析**：print 默认 sep=' '，默认 end='\n'，可接受多个参数；但其返回值是 None，故选项 D 错误。
