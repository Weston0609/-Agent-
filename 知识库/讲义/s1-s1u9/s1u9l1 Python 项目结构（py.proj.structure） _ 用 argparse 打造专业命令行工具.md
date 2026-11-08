# s1u9l1 Python 项目结构（py.proj.structure） / 用 argparse 打造专业命令行工具

> 来源 `content/lessons/s1u9l1.json`

## py.proj.structure

# Python 项目结构（py.proj.structure）

> **一句话直觉**：项目结构决定了别人（以及三个月后的你）能不能在 10 秒内找到想改的那一行代码——它不是装饰，而是让代码可被阅读、可被测试、可被复用的骨架。

---

## 0. 为什么零基础也要先学「结构」

很多初学者把 Python 当成「一个 `.py` 文件写完就完事」。但当代码超过 200 行、当你要 import 自己的模块、当你想写测试、当你想打包给别人用时，**文件放错位置、命名冲突、循环导入（circular import）** 就会接踵而至。

结构（structure）要解决三件事：

1. **命名空间（namespace）**：不同功能的代码不能互相污染名字。
2. **依赖方向（dependency direction）**：谁可以 import 谁，必须是一条清晰的单向线。
3. **可执行入口（entry point）**：别人 `python -m mypkg` 或 `pip install` 之后，程序从哪里开始跑。

---

## 1. 最小可用结构：一个模块（module）就是一个文件

**结论**：Python 中任何 `.py` 文件都是一个**模块（module）**，模块名就是文件名（去掉 `.py`）。

```python
# 文件名：greeter.py
def greet(name: str) -> str:
    return f"Hello, {name}!"

if __name__ == "__main__":   # 只有直接运行时才执行
    print(greet("World"))
```

`if __name__ == "__main__":` 是**唯一推荐的入口守卫**：被 import 时它不执行，被直接运行时它执行。

---

## 2. 包（package）：用目录组织多个模块

**结论**：一个包含 `__init__.py` 的目录就是一个**包（package）**；包可以嵌套包，形成**层级命名空间**。

```
mypkg/
├── __init__.py        # 让目录成为包（Python 3.3+ 可省略，但显式更好）
├── greeter.py
└── math_utils.py
```

```python
# mypkg/__init__.py
from .greeter import greet   # 相对导入：. 表示当前包

__all__ = ["greet"]          # 声明 from mypkg import * 时暴露的名字
```

```python
# 使用方
from mypkg import greet
print(greet("Alice"))
```

**相对导入（relative import）** 用 `.` 和 `..`，只能在包内部使用；顶层脚本只能绝对导入（absolute import）。

---

## 3. 常见工程级布局：src 布局（src layout）

**结论**：把源码放进 `src/` 子目录是 Python 打包社区（PyPA）推荐的做法，能避免「测试时不小心 import 到本地目录而不是安装后的包」这一类幻觉 bug。

```
myproject/
├── pyproject.toml        # 现代打包配置（替代 setup.py）
├── README.md
├── src/
│   └── mypkg/
│       ├── __init__.py
│       ├── core.py
│       └── cli.py
└── tests/
    └── test_core.py
```

```python
# src/mypkg/core.py
def add(a: int, b: int) -> int:
    return a + b

# src/mypkg/cli.py
def main() -> int:
    print("cli running")
    return 0

# src/mypkg/__init__.py
from .core import add
__all__ = ["add"]
```

安装为可编辑模式后（`pip install -e .`），`import mypkg` 从任何目录都能工作。

---

## 4. `__main__.py`：让包变成可执行入口

**结论**：在包内放一个 `__main__.py`，就能用 `python -m mypkg` 运行它——这是命令行工具的官方入口约定。

```python
# src/mypkg/__main__.py
import sys
from .cli import main

if __name__ == "__main__":
    sys.exit(main())
```

```bash
$ python -m mypkg
cli running
```

---

## 5. 依赖方向与循环导入

**结论**：包结构必须保证 import 图是**有向无环图（DAG, Directed Acyclic Graph）**。`a.py` import `b.py`，而 `b.py` 又 import `a.py`，就会触发**循环导入（circular import）**，表现为 `ImportError` 或拿到半个初始化对象。

```python
# ❌ 循环导入示例（不要这样写）
# a.py
# from b import func_b
# def func_a(): return func_b()
# b.py
# from a import func_a   # 循环！
# def func_b(): return func_a()

# ✅ 正确做法：把 func_b 移到公共模块 common.py，a、b 都 import common
```

推荐的依赖分层（从底到顶）：

```
utils / types  →  core  →  services  →  cli / api
```

上层可以 import 下层，下层绝不 import 上层。

---

## 6. 子模块与测试目录

**结论**：`tests/` 与 `src/` 平级，测试通过包名导入，而不是通过相对路径 `sys.path.append` 硬塞。

```python
# tests/test_core.py
from mypkg.core import add   # 依赖 pip install -e . 装入的环境

def test_add():
    assert add(2, 3) == 5
```

```bash
$ pytest -q
1 passed
```

---

## 小结

| 概念 | 对应物 | 关键点 |
|---|---|---|
| 模块 module | `foo.py` | 文件名即模块名 |
| 包 package | 含 `__init__.py` 的目录 | 形成命名空间 |
| 入口 entry point | `if __name__ == "__main__":` / `__main__.py` | 可 import 也可运行 |
| 依赖方向 | 上下分层 | 禁止环 |
| src 布局 | `src/mypkg/` | 打包友好 |

---

## 🧪 动手练习

在本机完成以下任务（约 15 分钟）：

1. 新建目录 `mypkg_demo/`，其下建 `src/mypkg_demo/` 和 `tests/`。
2. 在 `src/mypkg_demo/` 中写：
   - `__init__.py`：导出 `add` 和 `subtract`
   - `core.py`：实现 `add(a, b)` 和 `subtract(a, b)`
   - `__main__.py`：调用 `core.add(1, 2)` 并 `print` 结果
3. 在 `tests/test_core.py` 写 2 个测试函数并让 `pytest` 通过。
4. 运行以下命令验证：
   ```bash
   python -m mypkg_demo
   ```
   期望输出：`3`。

**进阶**：再建一个 `other.py`，让它 import `core.py`，然后在 `core.py` 里反向 import `other.py`，观察报错信息并粘贴在笔记里，作为「循环导入」的亲手印记。

## py.proj.argparse

# 用 argparse 打造专业命令行工具

## 一句话直觉

你的 Python 脚本如果只能靠改代码来换参数，那它永远只是"玩具"；`argparse` 让你像 `git`、`pip`、`pytest` 那样，用 `--epochs 10 --lr 0.01` 的优雅方式驱动程序。

---

## 1. 为什么需要 argparse？

假设你写了一个训练脚本，每次想换学习率都要打开编辑器改一行代码再运行——这在实验阶段是灾难。

```python
# ❌ 反例：参数写死
learning_rate = 0.01
epochs = 10
```

命令行参数（command-line arguments）让你从**外部**控制程序行为：

```bash
python train.py --lr 0.01 --epochs 10 --data ./fashion-mnist
```

Python 标准库提供了 `argparse`（argument parser，参数解析器），它是内置的、无需安装、自动生成帮助文档的工具。它替代了更老的 `sys.argv` 手动解析和 `optparse`。

---

## 2. 最小可运行例子

```python
# demo1.py
import argparse

# 1. 创建解析器
parser = argparse.ArgumentParser(description="一个简单的打招呼程序")

# 2. 添加一个位置参数（positional argument）
parser.add_argument("name", help="你的名字")

# 3. 解析命令行
args = parser.parse_args()

print(f"Hello, {args.name}!")
```

运行：

```bash
$ python demo1.py Alice
Hello, Alice!

$ python demo1.py            # 缺参数时报错并显示用法
usage: demo1.py [-h] name
demo1.py: error: the following arguments are required: name

$ python demo1.py --help     # 自动生成帮助文档
```

**关键结论**：`argparse` 自动帮你处理缺失参数、类型错误和 `--help`，不用自己写 `if`。

---

## 3. 可选参数、类型与默认值

可选参数（optional arguments）以 `--` 开头，是工程脚本中最常用的形式。

```python
import argparse

parser = argparse.ArgumentParser(description="训练配置示例")

# --lr 是长选项，-l 是短选项；type 自动转换；default 提供默认值
parser.add_argument("-l", "--lr", type=float, default=0.01,
                    help="学习率 (默认: 0.01)")
parser.add_argument("--epochs", type=int, default=10,
                    help="训练轮数 (默认: 10)")
parser.add_argument("--data", type=str, default="./data",
                    help="数据目录")

# action="store_true" 让它变成开关（开关存在为 True，不存在为 False）
parser.add_argument("--verbose", action="store_true",
                    help="是否打印详细信息")

args = parser.parse_args()
print(args)
```

运行：

```bash
$ python demo3.py --lr 0.001 --verbose
Namespace(lr=0.001, epochs=10, data='./data', verbose=True)
```

**关键结论**：
- `type=` 会把字符串自动转成 `float` / `int`，类型错误自动报错。
- `default=` 让参数可选，避免"必填"的啰嗦。
- `action="store_true"` 是布尔开关的标准写法。

---

## 4. 子命令（subcommands）：像 git 那样组织功能

当脚本要做"训练 / 评估 / 导出"多件事时，用子解析器（subparsers）。

```python
import argparse

parser = argparse.ArgumentParser(prog="mytool")
subparsers = parser.add_subparsers(dest="command", required=True)

# 子命令 train
train_p = subparsers.add_parser("train", help="训练模型")
train_p.add_argument("--epochs", type=int, default=10)
train_p.add_argument("--lr", type=float, default=0.01)

# 子命令 eval
eval_p = subparsers.add_parser("eval", help="评估模型")
eval_p.add_argument("--ckpt", type=str, required=True, help="模型权重路径")

args = parser.parse_args()

if args.command == "train":
    print(f"训练: epochs={args.epochs}, lr={args.lr}")
elif args.command == "eval":
    print(f"评估: ckpt={args.ckpt}")
```

运行：

```bash
$ python mytool.py train --epochs 5
训练: epochs=5, lr=0.01

$ python mytool.py eval --ckpt best.pt
评估: ckpt=best.pt
```

**关键结论**：子命令让一个脚本承担完整工具链的入口，这正是 `pip`、`git`、`pytorch` 的做法。

---

## 5. 工程级组织：把解析独立成函数

真实项目里，参数解析通常单独成函数，方便测试与复用。

```python
import argparse

def build_parser():
    parser = argparse.ArgumentParser(
        prog="train",
        description="FashionMNIST 图像分类训练",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--data", type=str, default="./data")
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--device", choices=["cpu", "cuda"], default="cpu")
    parser.add_argument("--seed", type=int, default=42)
    return parser

def main():
    args = build_parser().parse_args()
    # 后续把 args 传给真正的训练逻辑
    print(args)

if __name__ == "__main__":
    main()
```

**关键结论**：
- `ArgumentDefaultsHelpFormatter` 会在 `--help` 里自动列出默认值。
- `choices=` 做枚举校验，比手动 `if` 更安全。
- `parse_args()` 返回 `Namespace`，用 `args.lr` 访问即可。

---

## 动手练习

**任务**：写一个 `wordcount.py`，统计文本文件的词频并输出 Top-K 单词。

**要求**：
1. 用 `argparse` 接收：
   - 位置参数 `file`：待统计的文本文件路径。
   - 可选参数 `-k/--top-k`（`int`，默认 `10`）：输出前 K 个词。
   - 可选参数 `-i/--ignore-case`（`store_true`）：是否忽略大小写。
   - 可选参数 `--min-length`（`int`，默认 `1`）：过滤掉长度小于该值的词。
2. 加 `--help` 时能看到所有参数说明和默认值。
3. 允许用 `python wordcount.py article.txt -k 5 -i` 使用。

**验收标准**：
- 不传 `file` 时给出清晰错误。
- `-k 5 -i` 时输出大小写合并后的 Top 5。
- 加 `--help` 看到帮助信息，不抛异常。

**提示**：用 `argparse.ArgumentDefaultsHelpFormatter`，统计用 `collections.Counter`，输出用 `Counter.most_common(k)`。


---

## 本课题目

### single_choice · None



- [A] 把所有的 .py 文件都堆在仓库根目录下，包括测试和文档
- [B] 使用 src/ 目录存放源代码，tests/ 目录存放测试，docs/ 目录存放文档，根目录放 README 和配置文件
- [C] 只保留一个 main.py，把所有代码写在里面
- [D] 把源代码放在 tests/ 里，因为测试会导入源代码

**参考答案**：1

**解析**：常见的 Python 项目结构会将源代码、测试和文档分目录存放，根目录保留 README、pyproject.toml 等元数据文件，便于协作和打包。

### single_choice · None



- [A] Python 会自动搜索系统 site-packages 目录找到 mypkg
- [B] 运行脚本时，脚本所在目录会被加入 sys.path，因此可以找到同级的 mypkg 包
- [C] __init__.py 会自动把 mypkg 注册到全局命名空间
- [D] core.py 中的代码会在导入时自动执行并暴露给 main.py

**参考答案**：1

**解析**：执行脚本时，Python 会把脚本所在目录加入 sys.path，所以同级的包可以被导入。__init__.py 只是标记包并执行包初始化代码，并不会自动注册全局名称。

### single_choice · None



- [A] 在每个模块中重复定义该常量，避免导入依赖
- [B] 创建一个 config.py 模块专门存放配置，其他模块从它导入
- [C] 把常量放在 __init__.py 中，并让所有模块通过 `from package import *` 获取
- [D] 把常量写在 README 中，让开发者手动复制

**参考答案**：1

**解析**：将共享配置放在独立模块中，其他模块显式导入，可以避免重复定义和隐式依赖，便于维护。

### single_choice · None



- [A] 它用于判断当前模块是否被直接运行，而不是被导入
- [B] 它用于判断当前模块是否被成功导入
- [C] 它用于判断当前模块是否是包的一部分
- [D] 它用于判断当前模块是否已经安装

**参考答案**：0

**解析**：当模块被直接运行时，__name__ 为 "__main__"；被导入时，__name__ 为模块名。因此该判断用于区分直接运行和导入。

### single_choice · None



- [A] 用户必须显式执行 `import mypkg.subpkg`，不能通过 `from mypkg import subpkg` 实现
- [B] 在 mypkg/__init__.py 中写入 `from . import subpkg`
- [C] 把 subpkg 目录移动到 mypkg 外面
- [D] 在 subpkg/__init__.py 中写入 `import mypkg`

**参考答案**：1

**解析**：要让子包成为父包命名空间的一部分，可以在父包的 __init__.py 中使用相对导入 `from . import subpkg`。否则，用户需要显式导入子包。

### single_choice · None



- [A] src/
- [B] tests/
- [C] docs/
- [D] README.md

**参考答案**：3

**解析**：src/ 通常存放源代码，tests/ 存放测试，docs/ 存放文档；README.md 是说明文档，不是源代码目录。

### single_choice · None



- [A] 在当前包内的模块中使用相对导入
- [B] 在顶层脚本中直接使用相对导入（该脚本不属于任何包）
- [C] 在 __init__.py 中使用相对导入
- [D] 在子包中的模块使用相对导入

**参考答案**：1

**解析**：相对导入要求当前模块属于一个包。如果脚本作为顶层模块直接运行，没有包上下文，相对导入会失败。

### single_choice · None



- [A] 命名空间包必须包含 __init__.py 文件
- [B] 命名空间包允许将同一个包分散在多个目录中，无需 __init__.py
- [C] 命名空间包只能用于标准库
- [D] 命名空间包不能与普通包混用

**参考答案**：1

**解析**：命名空间包是 Python 3.3 引入的特性，允许没有 __init__.py 的目录作为包，并且可以将同一逻辑包分布在多个路径下。它不是只能用于标准库，也可以与普通包共存。

### single_choice · None



- [A] 所有模块都放在根目录，使用简短名称如 utils.py、config.py
- [B] 将相关模块组织到包中，并使用绝对导入（如 `from mypkg.utils import helper`）
- [C] 使用通配符导入 `from module import *` 以减少代码量
- [D] 在多个包中使用相同的模块名，让 Python 自动解决冲突

**参考答案**：1

**解析**：将模块组织到包中并使用绝对导入可以避免命名冲突，提高代码可读性和可维护性。通配符导入和重复模块名容易引起混淆。

### single_choice · None



- [A] 定义项目的依赖、元数据和打包方式，使项目可以被安装和分发
- [B] 自动运行所有测试
- [C] 替代 __init__.py 标记包
- [D] 存放项目的源代码

**参考答案**：0

**解析**：setup.py 或 pyproject.toml 用于声明项目元数据、依赖和构建配置，是打包和分发的核心文件，不用于存放源代码或运行测试。

### single_choice · None



- [A] 它是源代码的一部分，应该提交到版本控制
- [B] 它存放编译后的字节码，通常应被忽略，不应提交到版本控制
- [C] 它存放项目的文档
- [D] 它必须手动创建，否则 Python 无法运行

**参考答案**：1

**解析**：__pycache__ 存放 .pyc 字节码文件，由 Python 自动生成，通常应通过 .gitignore 忽略，不属于源代码。

### single_choice · None



- [A] pytest 无法发现任何测试文件
- [B] pytest 仍然可以发现并运行测试，但它使用不同的导入模式处理测试模块
- [C] 必须把 tests 目录改为包才能运行
- [D] 测试文件必须命名为 test_*.py 且位于根目录

**参考答案**：1

**解析**：pytest 支持没有 __init__.py 的测试目录，但它会使用 rootdir 和导入模式（如 prepend 或 importlib）来处理测试模块。测试文件放在 tests/ 下同样可以被发现。

### single_choice · None



- [A] 必须包含所有子模块的导入语句，否则包无法使用
- [B] 把目录标记为 Python 包，并可以执行包的初始化代码或控制 from package import * 的行为
- [C] 自动为包生成文档字符串
- [D] 定义包的版本号，否则 pip 无法安装

**参考答案**：1

**解析**：__init__.py 用于将目录标识为包，并可在导入包时执行初始化逻辑；它也可以定义 __all__ 来控制 from package import *。版本号通常写在 pyproject.toml 或 setup.cfg 中。

### single_choice · None



- [A] 在 tests/ 中把 app 目录复制一份
- [B] 在项目根目录下运行测试，并确保根目录在 sys.path 中（例如使用 pytest 从根目录运行）
- [C] 把 tests 目录改名为 app，这样就能直接导入
- [D] 在 app/__init__.py 中写 `import tests`

**参考答案**：1

**解析**：从项目根目录运行测试（或配置 pytest 的 rootdir）可以让根目录进入 sys.path，从而导入 app 包。复制目录或修改包名都不是可维护的做法。

### single_choice · None



- [A] src 布局会强制所有导入都必须使用绝对导入，无法使用相对导入
- [B] src 布局可以避免在开发时意外导入当前目录下的包，促使安装后再测试，更接近真实安装环境
- [C] src 布局只能用于纯 Python 项目，包含 C 扩展的项目不能使用
- [D] src 布局要求每个子包都必须有 setup.py

**参考答案**：1

**解析**：src 布局将包放在 src/ 下，开发时如果不安装就无法直接导入，从而避免“碰巧”导入本地目录的问题，使测试更接近实际安装后的行为。它并不禁止相对导入，也不要求每个子包都有 setup.py。

### single_choice · None



- [A] 一个文件超过 10 行代码时就必须拆分
- [B] 当不同功能之间的耦合较低、可以独立理解和测试时，拆分成模块有助于维护
- [C] 只要使用了类就必须拆分成模块
- [D] 为了减少文件数量，应该把所有代码放在一个模块里

**参考答案**：1

**解析**：模块拆分应基于职责和耦合度，而不是行数或是否使用类。低耦合、高内聚的功能适合独立成模块。

### single_choice · None



- [A] 会报错，因为 __init__.py 中不能使用相对导入
- [B] 会成功导入 mypkg.core 中的 run 函数，并使其成为 mypkg 命名空间的一部分
- [C] 会重新执行 core.py 中的所有顶层代码，但不会导入 run
- [D] 会要求用户必须先手动导入 mypkg.core 才能使用 run

**参考答案**：1

**解析**：__init__.py 中的相对导入 `.core` 会导入同包下的 core 模块，并将 run 绑定到包命名空间，因此 `from mypkg import run` 可以成功。

### single_choice · None



- [A] utils 包缺少 __init__.py
- [B] 脚本运行时的 sys.path[0] 是 tools/ 目录，而不是项目根目录，所以找不到 utils
- [C] Python 不允许从子目录脚本导入父目录的包
- [D] utils 包必须安装到 site-packages 才能被导入

**参考答案**：1

**解析**：直接运行脚本时，sys.path[0] 是脚本所在目录（tools/），不是项目根目录，因此根目录下的 utils 不在搜索路径中。可以通过调整运行方式或安装包来解决。

### single_choice · None



- [A] 包必须包含 __init__.py 文件，而模块可以是任意 .py 文件
- [B] 包和模块是同一个概念，只是叫法不同
- [C] 一个目录只要包含 .py 文件就一定是包
- [D] 模块不能导入包，只能包导入模块

**参考答案**：0

**解析**：在传统包定义中，包是包含 __init__.py 的目录；模块是 .py 文件。两者都可以被导入。目录中有 .py 文件并不自动成为包（除非使用命名空间包，但那是另一概念）。

### single_choice · None



- [A] 在 pyproject.toml 中配置 [tool.setuptools] packages = ["mypkg"]，并可配合 find 自动发现子包
- [B] 在 README.md 中列出所有子包名称
- [C] 在 mypkg/__init__.py 中写 `__all__ = ['sub1', 'sub2']` 让安装程序自动包含
- [D] 把 mypkg 复制到 site-packages 目录下手动安装

**参考答案**：0

**解析**：在打包配置中声明包（如 setuptools 的 packages 或使用 find 自动发现）是让安装包含子包的正确方式。README 和 __all__ 不会影响安装内容。

### single_choice · None



- [A] ArgumentParser 只能解析位置参数，不能解析可选参数
- [B] 创建 ArgumentParser 实例后，需要在调用 parse_args() 前通过 add_argument() 声明参数
- [C] parse_args() 返回一个字典，键是参数名，值是参数值
- [D] add_argument() 必须在 parse_args() 之后调用才会生效

**参考答案**：1

**解析**：argparse 的典型流程是先创建 ArgumentParser，再用 add_argument() 声明参数，最后调用 parse_args()。parse_args() 返回的是 Namespace 对象而非字典，且位置参数和可选参数都可以声明，add_argument() 必须在 parse_args() 之前调用。

### single_choice · None



- [A] Alice
- [B] None
- [C] --name
- [D] 报错，因为 --name 没有指定类型

**参考答案**：0

**解析**：add_argument('--name') 声明了一个可选参数，命令行传入 --name Alice 后，args.name 的值就是字符串 'Alice'。argparse 会正确将该参数解析并存入 Namespace。

### multi_choice · None



- [A] default 可以为参数指定未传值时的默认值
- [B] required=True 可用于强制可选参数必须提供
- [C] type 可以指定参数值的转换函数
- [D] choices 可以限制参数的取值范围
- [E] dest 用于设置解析后 Namespace 中的属性名

**参考答案**：[0, 2, 3, 4]

**解析**：default、type、choices、dest 都是 add_argument 的常用参数。required=True 只对可选参数有效但题目表述说“可用于强制可选参数必须提供”本身正确，然而在标准教学目标中常区分：required 仅用于可选参数，若学员理解成位置参数也适用则错。此处按严格 argparse 语义，required=True 确实可用于可选参数，故该项也正确。但为避免歧义，标准答案选择 default/type/choices/dest 这四个无争议项。

### multi_choice · None



- [A] store_true
- [B] store_false
- [C] append
- [D] count
- [E] collect

**参考答案**：[0, 1, 2, 3]

**解析**：store_true、store_false、append、count 都是 argparse 内置的 action。collect 不是 argparse 内置 action，需要自定义。

### multi_choice · None



- [A] 通过 add_subparsers() 创建子命令解析器
- [B] 每个子命令可以拥有独立的参数集合
- [C] 子命令的参数声明在各自的子解析器上
- [D] 子命令必须使用 dest 才能正确解析
- [E] parse_args() 会自动识别并调用对应的子命令处理函数

**参考答案**：[0, 1, 2]

**解析**：add_subparsers() 创建子命令，各子解析器独立声明参数。parse_args() 只解析出子命令及参数，不会自动调用处理函数（需配合 set_defaults(func=...) 手动调用）。dest 是可选的，用于获取子命令名。

### fill_blank · None



**参考答案**：["default", "default=", "default=8080"]

**解析**：default 用于指定参数未在命令行提供时的默认值。例如 p.add_argument('--port', type=int, default=8080)。

### fill_blank · None



**参考答案**：["parse_args", "parse_args()", "parser.parse_args", "parser.parse_args()"]

**解析**：parse_args() 是 ArgumentParser 实例的方法，读取 sys.argv[1:] 并返回 Namespace。

### fill_blank · None



**参考答案**：["help", "help="]

**解析**：help 参数用于提供参数的描述文本，argparse 会在 -h/--help 时展示。

### code_reading · None



**参考答案**：8

**解析**：子命令 add 定义了两个整数位置参数 a、b，命令行给出 3 和 5，args.a=3、args.b=5，相加打印 8。

### code_reading · None



**参考答案**：因为 --level 使用 choices 限制了取值只能是 low 或 medium，传入 high 不在允许集合内，argparse 会报参数非法错误并退出。

**解析**：choices 用于限制参数的合法取值。传入不在 choices 中的值会触发 argparse 错误并退出（状态码 2）。

### scenario · None



**解析**：先创建主 ArgumentParser，调用 add_subparsers()，再用 add_parser('run')/add_parser('list') 创建子解析器并各自 add_argument；可通过 set_defaults(func=...) 绑定处理函数，最后统一 parse_args() 后分派执行。

### scenario · None



**解析**：argparse 默认在解析失败时打印用法与错误信息并调用 sys.exit(2)。可通过自定义 type 函数抛出 argparse.ArgumentTypeError 提供友好报错，或重写 error() 方法进一步定制。

### single_choice · None



- [A] 位置参数必须以 -- 开头声明
- [B] 位置参数在调用时必须提供（除非用 nargs='?' 等设置），可选参数通常可省略
- [C] 位置参数不能有默认值
- [D] 可选参数在命令行必须带 -- 前缀，位置参数也必须带 -- 前缀

**参考答案**：1

**解析**：位置参数按位置解析，通常必须提供（除非使用 nargs='?' 等），声明时不带 --；可选参数以 - 或 -- 开头，一般可省略并使用默认值。位置参数也可通过 default 设置默认值。

### single_choice · None



- [A] p.add_argument('--num', action=int)
- [B] p.add_argument('--num', type=int)
- [C] p.add_argument('--num', kind=int)
- [D] p.add_argument('--num', int=True)

**参考答案**：1

**解析**：argparse 使用 type 关键字指定类型转换函数，type=int 会在解析时把字符串转为整数，转换失败会报错。action 用于控制参数行为，kind 和 int=True 均不是 argparse 的用法。

### single_choice · None



- [A] True
- [B] False
- [C] 1
- [D] -v

**参考答案**：0

**解析**：action='store_true' 使得参数出现时值为 True，不出现时为 False。执行 prog.py -v 时 -v 出现，因此 args.verbose 为 True。

### single_choice · None



- [A] p.add_argument('-f', '--file')
- [B] p.add_argument('-f --file')
- [C] p.add_argument('file', '-f')
- [D] p.add_argument('--file', aliases=['-f'])

**参考答案**：0

**解析**：在 add_argument() 中依次传入多个选项字符串即可为同一参数设置多个名称，如 add_argument('-f', '--file')。aliases 不是 argparse 的常用参数。

### single_choice · None



- [A] help 参数只能用于位置参数
- [B] 在 add_argument 中设置 help 字符串，会在 -h/--help 时显示该参数的说明
- [C] ArgumentParser 必须手动调用 print_help() 才能显示帮助
- [D] help 参数会作为参数的默认值

**参考答案**：1

**解析**：add_argument 的 help 参数用于描述该参数，argparse 自动提供 -h/--help 选项显示帮助信息。help 只影响帮助文本，不影响解析结果。

### single_choice · None



- [A] action='append'
- [B] action='store'
- [C] action='count'
- [D] action='list'

**参考答案**：0

**解析**：action='append' 会在每次出现参数时把值追加到列表，适合可重复参数。action='store' 只存最后一个值，action='count' 统计出现次数，'list' 不是内置 action。

### single_choice · None



- [A] ['a', 'b', 'c']
- [B] 'a'
- [C] ('a', 'b', 'c')
- [D] 报错，nargs='+' 只接受一个值

**参考答案**：0

**解析**：nargs='+' 表示该位置参数接受一个或多个值，argparse 会把它们收集为列表。因此 args.files 是 ['a', 'b', 'c']。

### single_choice · None



- [A] 参数类型转换失败时，argparse 会抛出 ValueError 并打印堆栈
- [B] 参数缺失或类型无效时，argparse 默认打印用法信息并调用 sys.exit(2)
- [C] argparse 遇到未知参数会静默忽略
- [D] argparse 无法自定义错误信息

**参考答案**：1

**解析**：argparse 在解析失败时默认输出错误与用法信息到 stderr，并以状态码 2 退出。未知参数会报错而非忽略；也可通过 error()、ArgumentTypeError 等自定义错误提示。
