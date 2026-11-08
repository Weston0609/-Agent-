# s2u8l1 pyproject：Python 项目的“总施工图” / 现代 Python 项目与依赖管理 / Wheel：Python 包的分发格式

> 来源 `content/lessons/s2u8l1.json`

## py.pkg.pyproject

# pyproject：Python 项目的“总施工图”

> **一句话直觉**：当你把代码从“一个 .py 文件”升级成“一个可安装、可分享、可复现的 Python 项目”时，`pyproject.toml` 就是那个放在项目根目录、告诉 pip / 构建后端 / 类型检查器 / 测试工具“这个项目长什么样、依赖谁、怎么打包”的**唯一权威配置文件**。

---

## 1. 背景：为什么会有 pyproject.toml？

在它出现之前，Python 项目配置是“碎片化”的：

- `setup.py`：命令式脚本，要运行才能知道包信息，甚至有安全风险（安装时执行任意代码）。
- `setup.cfg`：声明式但只覆盖一部分工具。
- `requirements.txt`：只能描述运行依赖，管不了构建依赖。

**PEP 518 / PEP 517 / PEP 621** 逐步确立了新标准：用一个 **TOML（Tom's Obvious Minimal Language）** 格式的文件 `pyproject.toml`，统一声明：

1. 构建这个项目需要什么工具（build-system）；
2. 项目元数据（project：名字、版本、依赖……）；
3. 各工具的配置（tool.*）。

它现在是**事实标准**：PyTorch 生态、几乎所有现代 Python 库、pip 只要看到它就会优先采用。

---

## 2. 一个最小可用的 pyproject.toml

TOML 用 `[表名]` 划分区块。最简单的 pyproject.toml 只需要两段：**构建系统** 和 **项目元数据**。

```toml
[build-system]
requires = ["setuptools>=68"]      # 构建时需要的工具
build-backend = "setuptools.build_meta"  # 用哪个后端来打包

[project]
name = "my-torch-demo"
version = "0.1.0"
description = "A tiny demo package"
requires-python = ">=3.9"
dependencies = [
    "torch>=2.0",
    "numpy>=1.24",
]

[project.optional-dependencies]
DEV = ["pytest", "ruff"]           # pip install .[dev] 时额外装的依赖
```

关键字段含义：

| 字段 | 作用 |
|---|---|
| `[build-system].requires` | 建包时 pip 先临时装的工具 |
| `build-backend` | 真正执行“把源码变成 whl/sdist”的后端 |
| `project.name` | 包名（pip install 的名字） |
| `project.version` | 版本号（可用动态方式从代码读取） |
| `requires-python` | 支持的 Python 版本范围 |
| `dependencies` | 运行依赖 |
| `optional-dependencies` | 可选依赖组 |

---

## 3. 用代码来“读”它：用标准库解析

`pyproject.toml` 是 TOML，Python 3.11+ 内置 `tomllib` 直接读；老版本用第三方 `tomli`。

```python
# demo_read_pyproject.py
# 目标：把 pyproject.toml 当成结构化数据读进来

from pathlib import Path

try:
    import tomllib           # Python 3.11+
except ModuleNotFoundError:
    import tomli as tomllib  # pip install tomli

# 假设脚本和 pyproject.toml 在同一目录
pyproject_path = Path(__file__).with_name("pyproject.toml")

with pyproject_path.open("rb") as f:
    data = tomllib.load(f)

print("包名:", data["project"]["name"])
print("版本:", data["project"]["version"])
print("依赖:", data["project"]["dependencies"])
print("构建后端:", data["build-system"]["build-backend"])
```

要点：**TOML 读取后是普通的 dict / list**，不需要任何魔法，工具链就是这么干的。

---

## 4. 包结构 + pyproject.toml 如何协作

一个最小可用包的目录结构：

```
my_torch_demo/
├── pyproject.toml
├── README.md
└── src/
    └── my_torch_demo/
        ├── __init__.py
        └── ops.py
```

`src/` 布局（src layout）是社区推荐做法：**源码和安装后的包分开**，避免“在源码目录下 import 到同名目录”这种隐蔽 bug。

在 pyproject.toml 里告诉 setuptools 去 src 下找包：

```toml
[tool.setuptools.packages.find]
where = ["src"]
```

真正可运行的调用示例：

```python
# 安装后（pip install -e .）在任何地方都能这样用
from my_torch_demo.ops import add
print(add(1, 2))
```

---

## 5. 工程级用法：把工具配置也收进来

`pyproject.toml` 的 `[tool.*]` 是给各个工具留的命名空间，避免项目根目录堆满 `.flake8`、`.isort.cfg`、`pytest.ini`……

```toml
[tool.ruff]
line-length = 100
target-version = "py39"

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.mypy]
python_version = "3.9"
strict = true
```

现代工具（ruff / pytest / mypy / black / torch 生态中的打包脚本）基本都优先读 `pyproject.toml`。**一个文件，一处真相（single source of truth）**。

更进一步，版本号可以动态化，避免和 `__version__` 两处维护：

```toml
[project]
name = "my-torch-demo"
dynamic = ["version"]

[tool.setuptools.dynamic]
version = {attr = "my_torch_demo.__version__"}
```

这样 `version` 只在 `__init__.py` 里写一次：

```python
# src/my_torch_demo/__init__.py
__version__ = "0.1.0"
```

```python
#!/usr/bin/env python3
"""pyproject.toml 最小可运行示例：

1. 生成一个临时项目（pyproject.toml + src 布局）
2. 用 tomllib 解析并打印关键字段

运行： python example_pyproject.py
"""

import tempfile
import textwrap
from pathlib import Path

try:
    import tomllib
    _LOADER = "tomllib"
except ModuleNotFoundError:  # Python < 3.11
    import tomli as tomllib
    _LOADER = "tomli (backport)"


PYPROJECT_CONTENT = textwrap.dedent(
    """
    [build-system]
    requires = ["setuptools>=68", "wheel"]
    build-backend = "setuptools.build_meta"

    [project]
    name = "my-torch-demo"
    version = "0.1.0"
    description = "A tiny demo package"
    requires-python = ">=3.9"
    dependencies = ["torch>=2.0", "numpy>=1.24"]

    [project.optional-dependencies]
    dev = ["pytest", "ruff"]

    [tool.setuptools.packages.find]
    where = ["src"]

    [tool.ruff]
    line-length = 100
    """
).strip()


def main() -> None:
    print(f"[info] TOML 读取器: {_LOADER}")

    # 1) 在临时目录中构造一个最小项目
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "pyproject.toml").write_text(PYPROJECT_CONTENT, encoding="utf-8")
        pkg_dir = root / "src" / "my_torch_demo"
        pkg_dir.mkdir(parents=True)
        (pkg_dir / "__init__.py").write_text('__version__ = "0.1.0"\n', encoding="utf-8")

        # 2) 解析 pyproject.toml
        with (root / "pyproject.toml").open("rb") as f:
            data = tomllib.load(f)

        project = data["project"]
        build = data["build-system"]

        print("包名     :", project["name"])
        print("版本     :", project["version"])
        print("Python   :", project["requires-python"])
        print("运行依赖 :", project["dependencies"])
        print("开发依赖 :", project["optional-dependencies"]["dev"])
        print("构建后端 :", build["build-backend"])
        print("Ruff 行长:", data["tool"]["ruff"]["line-length"])

        # 3) 演示 keyError 防御式读取
        get = project.get("description", "<no description>")
        print("描述     :", get)


if __name__ == "__main__":
    main()
```

## py.pkg.uv_poetry

# py.pkg.uv_poetry：现代 Python 项目与依赖管理

## 一句话直觉

你写完代码要发给同事时，对方总是问「你装了什么库、什么版本」，而 `requirements.txt` 经常装出不同环境——`uv` 和 `Poetry` 就是为了让「依赖声明 + 锁定 + 虚拟环境 + 打包」变成一条命令的现代工具。

---

## 1. 为什么需要依赖管理（Dependency Management）

Python 自带 `pip` 只能「装」，不能「锁」。例如 `pip install requests` 今天装 2.31，半年后可能装 2.32，行为就可能改变。更糟的是 `pip install -r requirements.txt` 时，间接依赖（Transitive Dependency）并没有版本约束。

依赖管理工具要做到三件事：

1. **声明**：在配置文件里写明直接依赖。
2. **锁定**：生成 `lock` 文件记录所有依赖的精确版本与哈希（Hash）。
3. **可复现**：任何机器按 lock 文件安装得到完全一致的依赖树。

---

## 2. Poetry：经典的项目管理器

Poetry 用 `pyproject.toml` 声明依赖，用 `poetry.lock` 锁定。它同时管虚拟环境（Virtual Environment）、构建（Build）与发布（Publish）。

```bash
# 初始化项目，生成 pyproject.toml
poetry new demo
cd demo

# 添加运行时依赖，自动写入 pyproject.toml 并更新 lock
poetry add requests

# 添加仅开发用的依赖（如测试、格式化工具）
poetry add --group dev pytest

# 按 lock 文件安装（CI 里必须用这个，保证可复现）
poetry install

# 在项目虚拟环境中执行命令
poetry run pytest
```

`pyproject.toml` 片段：

```toml
[tool.poetry]
name = "demo"
version = "0.1.0"
description = ""
authors = ["You <you@example.com>"]

[tool.poetry.dependencies]
python = "^3.11"
requests = "^2.31"

[tool.poetry.group.dev.dependencies]
pytest = "^8.0"
```

---

## 3. uv：极快的统一工具

`uv` 由 Astral 出品（Ruff 团队），用 Rust 实现，速度常比 `pip`/`poetry` 快 10~100 倍。它把「Python 解释器管理 + 虚拟环境 + 依赖解析 + 锁定 + 运行脚本」都统一到一条命令。

```bash
# 安装 uv（官方脚本方式）
# curl -LsSf https://astral.sh/uv/install.sh | sh

# 创建项目（生成 pyproject.toml）
uv init demo
cd demo

# 添加依赖，自动创建 .venv 并更新 uv.lock
uv add requests
uv add --dev pytest

# 按 lock 文件同步环境（CI 里必须用这个）
uv sync

# 直接运行项目脚本，无需手动激活虚拟环境
uv run pytest
```

`uv` 完全兼容 `pyproject.toml` 标准（PEP 621），Poetry 项目的 `[project]` 段通常也能直接跑。

---

## 4. 该选哪个？

| 维度 | Poetry | uv |
| --- | --- | --- |
| 速度 | 中 | 极快 |
| 成熟度 | 高，生态广 | 新，但已生产可用 |
| 解释器管理 | 不负责 | 可 `uv python install 3.12` |
| 配置文件 | `pyproject.toml` + `poetry.lock` | `pyproject.toml` + `uv.lock` |
| 适合场景 | 传统库/长期项目发布 | 追求速度、单文件工具、CI |

两者都遵循 PEP 518（`pyproject.toml`）与 PEP 621（项目元数据）。选一个熟练即可，锁文件不要提交两份。

---

## 5. 工程实践要点

- **提交 lock 文件**：只有它保证「队友/CI/生产」装出一致依赖。
- **区分运行时与开发依赖**：用 `--group dev`（Poetry）或 `--dev`（uv）。
- **CI 使用 `install`/`sync`**：不带参数才能走 lock 文件；不要用 `add` 改动锁。
- **虚拟环境不要提交**：`.venv/` 放入 `.gitignore`。
- **Python 版本也写进配置**：`requires-python` 让解析器知道允许版本。

---

## 动手练习

在你本地完成以下任务，并截图或复制命令输出到笔记：

1. 用 `uv init mycli` 创建一个新项目，进入目录。
2. 用 `uv add rich` 添加 `rich` 依赖；用 `uv add --dev pytest` 添加开发依赖。
3. 新建 `main.py`，使用 `rich.print("[bold green]Hello, uv!")`。
4. 用 `uv run python main.py` 运行并看到彩色输出。
5. 执行 `uv sync`，确认 `.venv/` 与 `uv.lock` 存在。
6. 把项目 `git init` 并提交，`.gitignore` 中包含 `.venv/`。

加分项：把同一份 `pyproject.toml` 复制到另一个目录，用 Poetry 读取 `[project]` 段并生成 `poetry.lock`，对比两者锁文件里 `rich` 的版本号是否一致。

## py.pkg.wheel

# Wheel：Python 包的分发格式

## 一句话直觉

Wheel（`.whl`）是 Python 包的一种**预编译、可直接安装**的分发格式，能让 `pip install` 跳过“现场编译”，几秒钟就把包装好。

---

## 1. 为什么需要 Wheel？从源码包说起

早期 Python 社区用源码分发（sdist，source distribution），也就是一个 `.tar.gz`。安装时 `pip` 要先下载、解压，再在**你的机器上现场编译**。问题在于：

- 编译要装编译器，Windows 用户尤其痛苦；
- 每次安装都要重复编译，慢；
- 环境稍有差异就编译失败。

Wheel 的思路很简单：**把编译这件事提前到打包阶段做一次**，用户拿到的是已经构建好的成品。

```python
# 查看 pip 是否支持 wheel（现代 pip 默认支持）
import subprocess, sys
print(subprocess.run([sys.executable, "-m", "pip", "--version"],
                     capture_output=True, text=True).stdout)
```

---

## 2. Wheel 长什么样？文件名就是“身份证”

一个 wheel 文件名例如：

```
numpy-1.26.4-cp312-cp312-manylinux_2_17_x86_64.whl
```

用 `-` 分成 5 段，含义是：

| 段 | 例子 | 含义 |
|---|---|---|
| 包名 | `numpy` | 项目名 |
| 版本 | `1.26.4` | 版本号 |
| Python 标签 | `cp312` | 适用于 CPython 3.12 |
| ABI 标签 | `cp312` | 二进制接口版本 |
| 平台标签 | `manylinux_2_17_x86_64` | 操作系统 + 架构 |

如果最后一段是 `py3-none-any`，就代表**纯 Python、跨平台**，谁都能装。

```python
# 用标准库解析 wheel 文件名
from packaging.utils import parse_wheel_filename

name, ver, build, tags = parse_wheel_filename(
    "numpy-1.26.4-cp312-cp312-manylinux_2_17_x86_64.whl"
)
print(name, ver, tags)
```

---

## 3. Wheel 内部结构：其实就是个 zip

Wheel 本质是 **ZIP 压缩包**，里面装的是已经排好目录的 Python 文件。用标准库就能拆开看。

```python
import zipfile

# 假设本地有个 wheel 文件
# with zipfile.ZipFile("somepkg-0.1-py3-none-any.whl") as z:
#     for info in z.infolist():
#         print(info.filename)

# 演示：手动列出一个 wheel 里常见的文件布局
layout = [
    "somepkg/__init__.py",       # 真正的 Python 包代码
    "somepkg/utils.py",
    "somepkg-0.1.dist-info/METADATA",  # 包名、版本、依赖
    "somepkg-0.1.dist-info/RECORD",    # 每个文件的哈希，用于校验
    "somepkg-0.1.dist-info/WHEEL",     # wheel 版本与标签
]
for line in layout:
    print(line)
```

关键目录是 **`*.dist-info/`**：`METADATA` 记录元数据，`RECORD` 记录每个文件的哈希，安装时用来校验完整性。

---

## 4. 构建一个自己的 Wheel

构建 wheel 的现代工具是 `build`（PEP 517 标准）。流程：写好 `pyproject.toml` → 运行 `python -m build` → 在 `dist/` 里得到 `.whl`。

```python
# pyproject.toml 示例（内容写入文件后即可构建）
PYPROJECT = '''
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "hello-wheel"
version = "0.1.0"
'''

print(PYPROJECT)
# 然后执行：
#   python -m build
# 会生成 dist/hello_wheel-0.1.0-py3-none-any.whl
```

安装时：

```bash
pip install dist/hello_wheel-0.1.0-py3-none-any.whl
```

---

## 5. 工程视角：为什么它重要

- **CI/CD 提速**：wheel 直接复制文件，不用编译，构建流水线秒级安装。
- **可复现**：RECORD 里有哈希，保证依赖内容不被篡改。
- **跨平台分发**：发布多个平台标签的 wheel（`manylinux`、`macosx`、`win_amd64`），`pip` 自动挑匹配的那一个。
- **私有源**：公司内网 `pip index` 上放 wheel，比放源码包更稳。

---

## 动手练习

**任务**：在本地构建并安装你自己的第一个 wheel。

1. 新建目录 `hello_wheel/`，里面写一个 `hello_wheel/__init__.py`：
   ```python
   def greet(name: str) -> str:
       return f"Hello, {name}!"
   ```
2. 在上一级目录写 `pyproject.toml`（内容参考第 4 节）。
3. 运行 `python -m pip install build`，再运行 `python -m build`。
4. 到 `dist/` 里找到 `hello_wheel-0.1.0-py3-none-any.whl`，用 `pip install` 装上。
5. 在任意目录打开 Python，执行：
   ```python
   import hello_wheel
   print(hello_wheel.greet("Wheel"))
   ```
   看到 `Hello, Wheel!` 就成功了。
6. 加分项：用 `zipfile` 打开你的 `.whl`，打印里面所有文件名，对照第 3 节讲解看看结构。

完成这个练习，你就走通了 wheel 的“构建 → 分发 → 安装 → 使用”全流程。


---

## 本课题目

### single_choice · None



- [A] 作为项目元数据和构建系统配置的标准声明文件
- [B] 作为 Python 解释器的启动脚本
- [C] 作为记录已安装第三方包版本的锁定文件
- [D] 作为存放项目源代码的默认目录

**参考答案**：0

**解析**：pyproject.toml 是 PEP 518 引入的标准配置文件，用于声明构建系统依赖以及项目元数据（名称、版本、依赖等）。解释器启动脚本通常不叫这个名字；记录已安装包版本是 lock 文件的职责；源代码应放在源码目录而不是 pyproject.toml 中。

### single_choice · None



- [A] 依据 setup.py 中是否包含 setup() 调用
- [B] 依据 pyproject.toml 中 [build-system] 的 build-backend 字段（若未写则回退到默认约定）
- [C] 依据当前 Python 解释器的版本号自动选择
- [D] 依据 setup.cfg 中 metadata 段的完整性

**参考答案**：1

**解析**：PEP 517 规定构建前端读取 pyproject.toml 的 [build-system] 表，其中 build-backend 指明后端模块；未显式指定时，setuptools 有历史默认约定。setup.py、setup.cfg 或解释器版本不是选择构建后端的直接依据。

### single_choice · None



- [A] 在依赖字符串后附加环境标记（marker），例如 `somelib; python_version < "3.10"`
- [B] 在 pyproject.toml 中写 if/else 语句
- [C] 为该依赖单独创建一个 pyproject.toml 文件
- [D] 把依赖名改成不同的大小写来区分环境

**参考答案**：0

**解析**：PEP 508 环境标记（marker）可附加在依赖字符串后，根据 python_version、sys_platform 等条件决定是否安装。TOML 不是编程语言，不能写 if/else；每个依赖单独文件没有这种机制；大小写不用于区分环境。

### single_choice · None



- [A] 构建前端在隔离环境中安装 requires 中声明的依赖后仍找不到该后端，于是构建失败并报错
- [B] 构建前端自动把该模块名替换成 setuptools 并继续构建
- [C] 构建前端忽略 build-backend，直接执行同目录的 setup.py
- [D] 构建前端把该模块名当作可选字段，正常跳过并生成空包

**参考答案**：0

**解析**：build-backend 指向的模块必须由 [build-system].requires 中的依赖提供，否则构建前端无法导入该后端，构建会失败。它不会被静默替换或忽略；也不会无条件回退到 setup.py。

### single_choice · None



- [A] 它是 JSON 格式的配置文件，必须用双引号包裹所有键
- [B] 它是 TOML 格式，支持表、数组、字符串等，可读性较好
- [C] 它是 YAML 格式，依赖缩进来表达层级
- [D] 它是 INI 格式，与 setup.cfg 完全等价

**参考答案**：1

**解析**：pyproject.toml 使用 TOML 格式，通过 [table] 表达层级、通过数组表达列表，键通常不带引号（除非含特殊字符）。它不是 JSON、YAML 或 INI；虽然 setup.cfg 也是配置文件，但格式不同。

### single_choice · None



- [A] python = "^3.10"
- [B] name = "my-project"
- [C] requires = ["poetry-core>=1.0.0"]
- [D] build-backend = "poetry.core.masonry.api"

**参考答案**：0

**解析**：在使用 Poetry 时，[tool.poetry.dependencies] 声明项目依赖，常包含对 Python 版本的要求如 python = "^3.10"。name 属于项目元数据；requires 和 build-backend 属于 [build-system] 表，不是 dependencies 表的内容。

### single_choice · None



- [A] 项目运行时依赖 hatchling
- [B] 项目使用 hatchling 作为构建后端，构建前端需要在隔离环境中安装它
- [C] hatchling 是一个命令行工具，与构建无关
- [D] 该配置是无效的，因为 requires 与 build-backend 不能同时出现

**参考答案**：1

**解析**：[build-system].requires 声明构建依赖，build-backend 指定构建后端模块；hatchling 作为后端被声明的依赖提供，供构建前端在隔离环境中安装调用。它不进入运行时依赖；它确实是构建后端而非无关命令；两者完全可以同时出现。

### single_choice · None



- [A] version 字段由构建后端在构建时动态提供，而不是在 pyproject.toml 中静态写出
- [B] version 字段被声明为可选，缺省时自动填 0.0.0
- [C] 项目在运行时会动态生成版本号
- [D] version 字段被忽略，项目无法被安装

**参考答案**：0

**解析**：PEP 621 的 dynamic 字段用于声明某些元数据不由 pyproject.toml 静态指定，而由构建后端在构建时提供（例如从 VCS 标签或模块属性中读取）。它不是可选字段的标记，也不是运行时行为，更不会使项目无法安装。

### single_choice · None



- [A] 在 [project] 中写多个同名的 dependencies 键，靠顺序区分平台
- [B] 使用环境标记，例如 `pywin32; sys_platform == "win32"`
- [C] 为每个平台创建独立的 pyproject.toml 并手动切换文件名
- [D] 把依赖名统一改为大写，让构建工具按大小写判断平台

**参考答案**：1

**解析**：PEP 508 环境标记（如 sys_platform == "win32"）是声明平台相关依赖的标准方式。TOML 不允许同一表内出现重复键；多文件按平台命名并非标准机制；大小写与平台判断无关。

### single_choice · None



- [A] 声明一个属于名为 some.group 的入口点组的扩展点，供其他工具发现插件
- [B] 声明项目对某个名为 some.group 的第三方包的依赖
- [C] 声明构建该 group 所需的编译工具链
- [D] 声明该项目只能被 some.group 这个组织发布

**参考答案**：0

**解析**：entry-points 用于声明入口点，按组名组织；插件系统常通过自定义组名发现第三方扩展。它不是依赖声明，不涉及编译工具链，也不限制发布组织。

### single_choice · None



- [A] pyproject.toml 提供标准声明，setup.py 可能保留用于兼容旧工具或执行动态逻辑
- [B] setup.py 会覆盖 pyproject.toml 中的所有声明
- [C] 两者同时存在会导致 pip 无法安装该项目
- [D] pyproject.toml 会被当作 setup.py 的备份文件，构建时忽略

**参考答案**：0

**解析**：在过渡期，项目常用 pyproject.toml 承载标准元数据与构建声明，同时保留 setup.py 以兼容旧工具或处理动态构建逻辑。二者可以共存且通常不会被拒绝安装；不存在 setup.py 覆盖全部声明或 pyproject.toml 被忽略的通用规则。

### single_choice · None



- [A] [project].dependencies（PEP 621 标准依赖数组）
- [B] [build-system].requires
- [C] [tool.poetry.dependencies]
- [D] [project.entry-points]

**参考答案**：2

**解析**：caret（^）版本约束是 Poetry 的语法，常出现在 [tool.poetry.dependencies] 中。PEP 621 的 [project].dependencies 及 [build-system].requires 使用 PEP 440/PEP 508 风格约束（如 >=、~=），不采用 caret；entry-points 与版本约束无关。

### single_choice · None



- [A] [project]
  requires = ["requests>=2.28"]
- [B] [project]
  dependencies = ["requests>=2.28"]
- [C] [build-system]
  dependencies = ["requests>=2.28"]
- [D] [tool.setuptools]
  install_requires = ["requests>=2.28"]

**参考答案**：1

**解析**：PEP 621 规定项目运行时依赖写在 [project] 表的 dependencies 数组中。requires 用于 [build-system] 声明构建依赖，不是运行时依赖字段；把依赖放进 [build-system] 只影响构建过程；[tool.setuptools] 下的 install_requires 是旧式写法，不是 pyproject.toml 的规范字段。

### single_choice · None



- [A] pyproject.toml 对 TOML 语法有严格要求，格式错误会导致解析失败
- [B] pyproject.toml 只能在特定操作系统上解析
- [C] 缺少右方括号会被自动补全，报错另有原因
- [D] 构建工具会跳过无法解析的表并继续构建

**参考答案**：0

**解析**：pyproject.toml 必须符合 TOML 语法；表头缺少右方括号属于语法错误，解析阶段即会失败。它不依赖特定操作系统；TOML 解析器不会自动补全错误的表头；构建前端通常不会静默跳过解析失败的文件。

### single_choice · None



- [A] 它声明构建项目所需的依赖以及构建后端，供构建前端在隔离环境中安装使用
- [B] 它声明项目运行时的所有第三方依赖
- [C] 它只能由 Poetry 使用，setuptools 不支持
- [D] 它用于指定项目在 PyPI 上的发布分类标签

**参考答案**：0

**解析**：[build-system] 表包含 requires（构建依赖）和 build-backend（构建后端模块），构建前端据此创建隔离环境并调用后端。运行时依赖属于 [project].dependencies；该表是通用标准，setuptools、hatchling、poetry-core 等均可使用；分类标签属于项目元数据。

### single_choice · None



- [A] [project]
- [B] [build-system]
- [C] [tool.<工具名>]
- [D] [metadata]

**参考答案**：2

**解析**：社区约定使用 [tool.<工具名>] 表存放各工具专属配置，例如 [tool.black]、[tool.ruff]。这些内容不属于 PEP 621 的项目元数据，也不属于构建系统声明，[metadata] 是 setup.cfg 的旧式写法。

### single_choice · None



- [A] 构建前端读取 pyproject.toml，创建隔离环境安装构建依赖，然后调用声明的构建后端生成发行包
- [B] Python 解释器直接执行 pyproject.toml，把它当作脚本运行
- [C] 构建过程完全忽略 pyproject.toml，只依赖 setup.py
- [D] 构建前端会先把项目安装到当前环境的 site-packages 中再打包

**参考答案**：0

**解析**：python -m build 是 PEP 517 构建前端，读取 pyproject.toml 的 [build-system]，在隔离环境中安装构建依赖并调用 build-backend 生成 sdist/wheel。pyproject.toml 是 TOML 配置而不是可执行脚本；在存在 [build-system] 时不会忽略它；构建并不需要先把项目装进 site-packages。

### single_choice · None



- [A] 一旦有 pyproject.toml，setup.py 就永远不会被读取
- [B] pyproject.toml 可以承载原本写在 setup.py/setup.cfg 中的元数据与构建配置，从而在多数场景下替代它们
- [C] pyproject.toml 只能与 setup.py 同时使用，不能单独存在
- [D] pyproject.toml 出现后 setup.cfg 被立即废弃，不再被任何工具支持

**参考答案**：1

**解析**：pyproject.toml 能表达项目元数据（PEP 621）和构建系统配置（PEP 518/517），因此在很多项目中可以取代 setup.py 和 setup.cfg。但它并非强制性排他：某些场景仍可能需要 setup.py 做动态逻辑；它也可以单独存在；setup.cfg 在一些工具链中仍被读取。

### single_choice · None



- [A] [project.scripts]
  mycli = "mypkg.cli:main"
- [B] [project]
  command = "mypkg.cli:main"
- [C] [build-system]
  scripts = ["mypkg.cli:main"]
- [D] [tool.pip]
  entry_points = ["mycli=mypkg.cli:main"]

**参考答案**：0

**解析**：PEP 621 规定命令行入口点写在 [project.scripts] 表中，键是命令名，值是 "模块:函数" 形式。command 不是标准字段；构建依赖表不用于入口点；[tool.pip] 也不是声明入口点的规范位置（旧式写法在 setup.py 的 entry_points 中）。

### single_choice · None



- [A] 构建该项目的依赖列表
- [B] 项目的可安装入口点
- [C] 项目的基础元数据，如名称、版本和说明文件
- [D] 项目在开发环境中使用的格式化工具配置

**参考答案**：2

**解析**：name、version、readme 都属于 PEP 621 的 [project] 项目元数据。构建依赖属于 [build-system].requires；入口点属于 [project.scripts] 或 [project.entry-points]；格式化工具配置属于 [tool.*]。

### single_choice · None



- [A] 声明构建项目所必需的依赖
- [B] 声明可选的功能依赖组，供用户按需安装，例如 pip install 包名[extra]
- [C] 声明项目运行时绝不会用到的依赖
- [D] 声明操作系统级别的系统库依赖

**参考答案**：1

**解析**：optional-dependencies 定义可选依赖组（extras），例如 test、docs 等，用户可用方括号语法安装。构建依赖在 [build-system].requires；可选依赖是项目功能的可选部分，而非永远不用；系统级库不在这一字段中声明。

### single_choice · None



- [A] uv 只能管理虚拟环境，不能安装依赖
- [B] Poetry 使用 pyproject.toml 管理依赖，uv 也可以读取 pyproject.toml 来同步依赖
- [C] uv 是 Poetry 的一个子命令
- [D] Poetry 只能用于发布包，不能用于本地开发环境管理

**参考答案**：1

**解析**：Poetry 是较早的依赖管理与打包工具，使用 pyproject.toml 与 poetry.lock；uv 是较新的高速工具，同样支持读取 pyproject.toml 并生成/同步锁文件，也能创建虚拟环境。A、C、D 均与事实不符。

### single_choice · None



- [A] requests 被写入全局 Python 安装目录，但不影响项目
- [B] pyproject.toml 的依赖声明被更新，同时 poetry.lock 被更新以锁定版本
- [C] 只更新 poetry.lock，不修改 pyproject.toml
- [D] 生成 requirements.txt 并删除 pyproject.toml

**参考答案**：1

**解析**：poetry add 会解析依赖、把新依赖加入 pyproject.toml，并更新 poetry.lock 以固定可复现的版本组合。它不会把包写入全局环境作为目标，也不会只动 lock 或删除 pyproject.toml。

### single_choice · None



- [A] Poetry 始终静默忽略 lock，不会提示任何问题
- [B] Poetry 可能提示 lock 文件过期（out of date），需要重新锁定以保持一致
- [C] pyproject.toml 会被自动删除
- [D] 虚拟环境会被自动销毁

**参考答案**：1

**解析**：当 pyproject.toml 中声明的依赖与锁文件不一致时，Poetry 通常会提示锁文件过期，需要重新生成锁文件；不会自动删除 pyproject.toml 或销毁环境。

### single_choice · None



- [A] 必须重启操作系统
- [B] 激活该虚拟环境，或通过工具提供的运行方式让命令在该环境中执行
- [C] 把虚拟环境目录加入 PYTHONPATH 后即可，无需激活
- [D] uv 虚拟环境无法生效

**参考答案**：1

**解析**：虚拟环境需要激活或通过工具的运行入口执行命令，使解释器与 PATH 指向该环境；仅添加 PYTHONPATH 并不等价于激活环境。

### multi_choice · None



- [A] 两者都能读取 pyproject.toml 来表达项目依赖
- [B] 两者都支持通过锁文件保证依赖可复现
- [C] 两者都只能用于发布包，不能用于本地开发
- [D] 两者都可以创建/管理项目虚拟环境

**参考答案**：[0, 1, 3]

**解析**：uv 与 Poetry 都围绕 pyproject.toml 工作，都提供锁文件机制，也都能管理项目虚拟环境；它们并非只能用于发布包，本地开发是主要场景之一。

### multi_choice · None



- [A] 把锁文件提交到版本控制
- [B] 删除锁文件并在不同机器上各自重新解析依赖
- [C] 只记录顶层依赖而不记录解析出的精确版本
- [D] 在 CI 中基于锁文件安装依赖

**参考答案**：[1, 2]

**解析**：提交锁文件、在 CI 中基于锁文件安装都有助于可复现；删除锁文件各自解析、只记录顶层依赖不记录精确版本会导致不同环境拿到不同版本，破坏可复现性。

### multi_choice · None



- [A] 可以按用途区分运行依赖与开发依赖
- [B] 安装时可以按需选择是否安装某些分组
- [C] 分组只能有一个，不能有多个
- [D] 分组有助于减小生产环境的安装体积

**参考答案**：[0, 1, 3]

**解析**：分组用于按用途组织依赖，安装时可选择是否包含，有助于控制生产环境安装内容与体积；分组可以有多个，并非只能一个。

### fill_blank · None



**参考答案**：["pyproject.toml", "pyproject.toml 文件", "“pyproject.toml”"]

**解析**：pyproject.toml 是 PEP 518/621 等定义的通用项目配置文件，uv、Poetry 等都会读取其中的相关表。

### fill_blank · None



**参考答案**：["锁", "lock", "lock 文件", "锁文件", "locking"]

**解析**：锁文件记录依赖解析后的精确版本与来源，是保证可复现安装的关键；不同工具命名可能不同，但概念一致。

### code_reading · None



**参考答案**：因为 pytest 位于开发依赖分组中，生产安装时可选择不安装该分组（例如只安装主依赖或排除开发组），从而不安装 pytest；具体命令取决于工具，但思路是按分组控制安装范围。

**解析**：依赖分组的意义在于按用途区分安装范围；把测试工具放进 dev 分组后，生产安装可以排除该组，避免引入不必要的包。

### code_reading · None



**参考答案**：风险是依赖解析结果可能与锁文件不一致，不同环境/不同时间可能拿到不同版本，导致结果不可复现，甚至出现本地能跑、CI 或他人机器失败的情况。

**解析**：锁文件固定了解析后的精确版本；跳过锁文件手动安装顶层依赖，传递依赖的版本可能随解析时间变化，破坏可复现性。

### scenario · None



**解析**：核心是把解析结果固定到锁文件并提交，CI 基于锁文件同步安装，从而避免上游新版本带来的随机失败，实现可复现构建。

### single_choice · None



- [A] 每人手动执行 pip install 逐个安装依赖
- [B] 使用 uv 的同步命令依据 uv.lock 安装，例如 uv sync
- [C] 删除 uv.lock 后重新解析依赖
- [D] 把 uv.lock 加入 .gitignore 以避免冲突

**参考答案**：1

**解析**：锁文件的意义在于可复现。uv 的同步命令会读取锁文件并让环境与之保持一致，从而保证团队成员依赖版本一致。手动逐个安装、删除锁文件或忽略锁文件都会破坏可复现性。

### scenario · None



**解析**：稳妥做法是保留原有 pyproject.toml 结构，让 uv 读取同一份 pyproject.toml 并生成新的锁文件，在分支或独立环境中并行验证安装与测试，确认无误后再切换；保留原流程便于回滚。

### single_choice · None



- [A] [build-system]
- [B] [tool.poetry.dependencies]
- [C] [project.scripts]
- [D] [tool.black]

**参考答案**：1

**解析**：Poetry 传统上把运行依赖写在 [tool.poetry.dependencies] 中；开发依赖写在 [tool.poetry.group.dev.dependencies] 等分组中。[build-system] 描述构建后端，[project.scripts] 定义入口脚本，[tool.black] 是格式化工具配置。

### single_choice · None



- [A] uv 只能使用系统 Python，无法创建虚拟环境
- [B] uv 可以创建虚拟环境，并可根据 pyproject.toml/uv.lock 将依赖同步到该环境中
- [C] uv 生成的锁文件不能跨平台使用，因此团队无法共享
- [D] uv 不支持从 pyproject.toml 解析依赖

**参考答案**：1

**解析**：uv 既支持虚拟环境管理，也支持基于 pyproject.toml 与锁文件解析/同步依赖。它并非只能使用系统 Python，也不是不支持 pyproject.toml。锁文件的跨平台行为取决于依赖本身，不能一概而论说不能共享。

### single_choice · None



- [A] 开发依赖组中的包在生产安装时通常不安装，主依赖会安装
- [B] 开发依赖组中的包无法被卸载
- [C] 两者完全等价，只是名字不同
- [D] 主依赖只能放标准库，开发依赖只能放第三方库

**参考答案**：0

**解析**：依赖分组用于区分运行依赖与开发/测试等依赖，生产环境可只安装主依赖而不安装开发组。它们并非等价，且分组与是否为标准库无关。

### single_choice · None



- [A] 直接运行代码，不处理依赖
- [B] 执行解析/锁定依赖的命令生成锁文件，并把锁文件提交到版本控制
- [C] 把 pyproject.toml 改名成 requirements.txt
- [D] 在每个开发者的机器上手动固定版本

**参考答案**：1

**解析**：锁文件用于记录精确解析结果，保证可复现。生成并提交锁文件是标准做法；改名、手动固定和不处理都不能达到可复现目标。

### single_choice · None



- [A] 它只能被 Poetry 使用，uv 完全无法读取
- [B] 它是 Python 项目元数据与工具配置的通用文件，多个工具可以读取其中的不同表
- [C] 它必须与 setup.py 同时存在才能安装依赖
- [D] 它只能声明依赖，不能配置构建后端

**参考答案**：1

**解析**：pyproject.toml 是 PEP 518/621 等定义的通用项目配置文件，不同工具读取 [tool.*] 等不同表。它不限于 Poetry，也不要求与 setup.py 并存，并且可以声明构建后端。

### single_choice · None



- [A] 忽略锁文件，每次重新解析最新版本
- [B] 根据 pyproject.toml 与 poetry.lock 安装依赖到项目虚拟环境
- [C] 只把依赖下载到缓存，不安装到环境
- [D] 删除现有虚拟环境后强制使用系统 Python

**参考答案**：1

**解析**：poetry install 会基于 pyproject.toml 与已有的 poetry.lock 安装依赖到项目环境，若锁文件不存在会解析并创建。它不会默认忽略锁文件或强制使用系统 Python。

### single_choice · None



- [A] uv 是 pip 的别名，两者行为完全相同
- [B] uv 是独立的包管理工具，提供更快的解析与安装，也支持 pip 风格的接口
- [C] uv 只能安装标准库
- [D] uv 不能安装 wheel 包，只能安装源码包

**参考答案**：1

**解析**：uv 是独立实现的高性能 Python 包/环境管理工具，并非 pip 的别名，功能上更广且速度更快；它并非只能装标准库，也不限制只能源码包。

### single_choice · None



- [A] wheel 是源码分发格式，安装时需要重新编译
- [B] wheel 是预编译的二进制分发格式，安装时通常无需编译
- [C] wheel 文件本质是一个 zip 归档，文件扩展名为 .whl
- [D] wheel 只能用于 Windows 平台

**参考答案**：2

**解析**：wheel 是一种预编译的分发格式（内为 zip 归档，扩展名 .whl），可跨平台使用（取决于文件名中的平台标签）。选项 A 把 wheel 与 sdist 混淆；选项 B 表述不严谨，wheel 不保证一定无需编译；选项 D 错误，wheel 支持多平台，但需匹配平台标签。C 正确描述了其文件格式本质。

### single_choice · None



- [A] 支持的 Python 实现及版本为 CPython 3.11
- [B] 该 wheel 的版本号
- [C] 支持的 C 编译器版本
- [D] 该包的构建编号

**参考答案**：0

**解析**：wheel 文件名的标准格式为 `{distribution}-{version}(-{build tag})?-{python tag}-{abi tag}-{platform tag}.whl`。cp311 是 python tag，表示 CPython 3.11。版本号是 1.26.4；构建编号是可选字段；平台上标签是 manylinux_2_17_x86_64。

### multi_choice · None



- [A] python tag 表示该 wheel 支持的 Python 实现与版本
- [B] abi tag 为 none 时表示不依赖具体 ABI 细节
- [C] platform tag 为 any 表示与操作系统和 CPU 架构无关
- [D] 同一版本、同一平台可以同时存在多个不同 build tag 的 wheel，编号高者优先
- [E] abi tag 只能是 none

**参考答案**：[0, 1, 2, 3]

**解析**：A、B、C 分别正确描述三个标签的含义。D 正确：build tag 用于标识同一版本同一平台的多次构建，数字越大越新。E 错误：abi tag 可以是 cp311、abi3、none 等多种取值。

### multi_choice · None



- [A] wheel 的 python tag 与当前解释器版本不匹配
- [B] wheel 的 platform tag 与当前操作系统/架构不匹配
- [C] wheel 的 abi tag 与当前解释器 ABI 不兼容
- [D] wheel 的版本号高于当前项目约束所允许的范围
- [E] wheel 的构建时间早于 2020 年

**参考答案**：[0, 1, 2, 3]

**解析**：pip 依据 python tag、abi tag、platform tag 判断 wheel 是否与当前环境兼容，并依据版本约束筛选候选。构建时间与兼容性判断无关，故 E 错误。

### multi_choice · None



- [A] 安装时通常无需执行构建步骤，安装速度更快
- [B] 安装过程更可预测，因为产物已在发布方构建好
- [C] 可以避免终端用户在本地安装编译工具链
- [D] wheel 天然包含所有 Python 版本的兼容性，无需区分 python tag
- [E] wheel 文件是 zip 归档，便于分发与缓存

**参考答案**：[0, 1, 2, 4]

**解析**：A、B、C、E 都是 wheel 的工程优势。D 错误：wheel 仍带有 python tag 与 abi tag，需要针对目标解释器版本构建；纯 Python 包才可用 `none-any`。

### multi_choice · None



- [A] 可以在 `[build-system]` 中指定 `requires` 列出构建后端依赖
- [B] 可以在 `[build-system]` 中通过 `build-backend` 指定构建后端
- [C] 在 `[project]` 中声明 name、version 等元数据是推荐的现代写法
- [D] 构建 wheel 必须提供 setup.py 文件
- [E] 构建 wheel 的输出文件扩展名为 .whl

**参考答案**：[0, 1, 2, 4]

**解析**：A、B、C 描述 pyproject.toml 中构建系统与项目元数据的标准用法。E 正确，wheel 输出扩展名为 .whl。D 错误：使用 pyproject.toml 声明构建后端后，不再强制需要 setup.py。

### multi_choice · None



- [A] 针对每个目标 Python 版本分别构建匹配的 wheel
- [B] 对含 C 扩展的包，在目标平台（或兼容的 manylinux 镜像）上构建以获得可用的 platform tag
- [C] 使用 `python -m build` 等前端工具调用 pyproject.toml 中声明的构建后端
- [D] 构建完成后在同一流程中把 wheel 上传到包索引
- [E] 为了让 wheel 通用，把 platform tag 手动改为 any 而无需实际适配

**参考答案**：[0, 1, 2, 3]

**解析**：A、B、C、D 都是合理的 CI 发布实践。E 错误：手动篡改平台标签会造成错误分类的 wheel，安装后可能在运行时或加载扩展时失败，属于典型反模式。

### fill_blank · None



**参考答案**：["abi, platform", "abi,platform", "abi platform"]

**解析**：wheel 文件名格式为 `{distribution}-{version}(-{build tag})?-{python tag}-{abi tag}-{platform tag}.whl`，三个核心标签依次为 python tag、abi tag、platform tag。

### fill_blank · None



**参考答案**：["any, none", "any,none", "any none"]

**解析**：纯 Python 包不依赖特定平台与 ABI，因此 platform tag 为 any、abi tag 为 none，整体常见形如 `py3-none-any.whl`。

### code_reading · None



**参考答案**：(1) True，因为 wheel 文件本身就是一种 zip 归档；(2) 可以。文件名中的 `py3` 表示支持 Python 3，`none-any` 表示不依赖具体 ABI 与平台，因此是纯 Python 的通用 wheel。

**解析**：wheel 文件是基于 zip 的归档格式，因此 zipfile.is_zipfile 对 .whl 返回 True。文件名标签 `py3-none-any` 分别对应 python tag=py3、abi tag=none、platform tag=any，说明该包是纯 Python 且跨平台的。

### code_reading · None



**参考答案**：(1) 强制 pip 只使用二进制分发（wheel），不允许回退到 sdist。(2) 由于禁止使用 sdist 而没有可用的 wheel，pip 会因为无法满足约束而失败（报错）。

**解析**：`--only-binary=:all:` 将所有包都限定为二进制分发（wheel）。在不提供 sdist 回退的情况下，如某包只有 sdist，pip 无法满足该约束，会直接失败，这在需要确保只使用 wheel 的场景（如离线、无编译环境）中常用。

### scenario · None



**解析**：含 C 扩展的库其二进制与特定平台和解释器 ABI 强相关，不能用 none-any 标签。`py3-none-any` 只适用于纯 Python 包。合理做法是针对每个目标平台和 Python 版本分别构建匹配 python tag、abi tag、platform tag 的 wheel（如在相应平台或兼容的 manylinux 镜像中构建），再统一上传。

### single_choice · None



- [A] python tag
- [B] abi tag
- [C] platform tag
- [D] build tag

**参考答案**：2

**解析**：wheel 文件名三个核心标签依次为 python tag、abi tag、platform tag。`win_amd64` 描述目标平台（Windows 64 位），属于 platform tag。`cp39` 是 python tag，第二个 `cp39` 是 abi tag。

### scenario · None



**解析**：第一个 wheel 的 python tag 为 cp311，与本机 CPython 3.10 的 python tag（cp310）不兼容，pip 会跳过它候选。`py3-none-any` 是纯 Python 通用 wheel，通常可被优先选中并安装成功。若它不存在，则只能回退到 sdist，需要在本地构建；若缺乏构建依赖或编译环境，安装就会失败。

### single_choice · None



- [A] any 和 none
- [B] none 和 any
- [C] any 和 cp311
- [D] manylinux 和 none

**参考答案**：0

**解析**：纯 Python 包的分发标签应为 `py3-none-any`，即 abi tag 为 none、platform tag 为 any，表示与具体 ABI 及平台无关。选项顺序是被刻意打乱的，正确组合是 platform=any、abi=none。

### single_choice · None



- [A] sdist，因为源码更安全
- [B] wheel，因为它是预编译的，安装更快且无需本地构建过程
- [C] 随机选择
- [D] 总是 sdist，wheel 只用于上传到 PyPI

**参考答案**：1

**解析**：pip 在解析依赖时会优先选择与当前解释器、ABI、平台匹配的 wheel，因为它免去本地构建步骤，安装更快、更可靠。只有在没有可用的 wheel 时才回退到 sdist。

### single_choice · None



- [A] 一个包只能发布 wheel，不能发布 sdist
- [B] wheel 中包含的是已构建好的文件，sdist 中包含的是构建所需的源文件
- [C] sdist 安装时必须联网才能完成
- [D] wheel 中必须包含 setup.py 才能被 pip 安装

**参考答案**：1

**解析**：sdist 是源代码归档，安装时通常需要构建（可能需编译扩展）；wheel 是已构建产物，安装时直接解包。wheel 不需要包含 setup.py，pip 通过 .dist-info 元数据安装。sdist 安装不一定要联网。

### single_choice · None



- [A] requirements.txt
- [B] pyproject.toml
- [C] setup.cfg
- [D] MANIFEST.in

**参考答案**：1

**解析**：PEP 517/518 引入了 pyproject.toml，其中 [build-system] 表声明构建后端（如 setuptools、hatchling、flit 等）。构建前端据此创建隔离环境并调用后端生成 wheel。setup.cfg 与 MANIFEST.in 仅被某些后端（如 setuptools）使用，不是构建系统的通用入口。

### single_choice · None



- [A] 一定能安装成功，因为 pip 会选用 sdist
- [B] 若存在与本机平台/ABI 匹配的 wheel，可离线安装成功；否则只能回退到需要本地构建的 sdist，可能失败
- [C] pip 会自动下载联网获取缺失依赖
- [D] 只会安装 sdist，忽略所有 wheel

**参考答案**：1

**解析**：离线环境下 pip 不能下载缺失依赖，但如果缓存或本地有匹配的 wheel，可直接安装。若只有 sdist 且本机缺编译器，构建就会失败。选项 A/C 忽略了离线与构建约束。

### single_choice · None



- [A] 它存放包的所有 Python 源码
- [B] 它用于在安装时把文件按类别放到目标环境的特定位置（如 scripts、data、headers）
- [C] 它是 wheel 的元数据，包含依赖信息
- [D] 它仅用于调试，正式 wheel 不允许包含

**参考答案**：1

**解析**：wheel 允许包含 `{distribution}-{version}.data/` 目录，其中的子目录（purelib、platlib、scripts、data、headers）会在安装时被重定位到目标环境的对应位置。包的元数据则位于 `.dist-info` 目录。

### single_choice · None



- [A] 1.2.3
- [B] cp311
- [C] 1abc
- [D] manylinux_2_17

**参考答案**：2

**解析**：build tag 以数字开头，后跟可选的字母数字，如 `1`、`1abc`。1.2.3 是版本号，cp311 是 python tag，manylinux_2_17 属于平台标签的一部分。
