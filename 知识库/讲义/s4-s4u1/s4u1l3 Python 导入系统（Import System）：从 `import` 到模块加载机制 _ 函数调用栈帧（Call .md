# s4u1l3 Python 导入系统（Import System）：从 `import` 到模块加载机制 / 函数调用栈帧（Call Frame）：Python 运行时的「现场记录」

> 来源 `content/lessons/s4u1l3.json`

## py.cpy.import_system

# Python 导入系统（Import System）：从 `import` 到模块加载机制

## 一句话直觉

`import` 不只是“把文件里的代码搬过来”，而是 Python 在背后按一套**搜索路径、缓存、模块对象、包结构**的规则，把外部代码安全、可复用、可维护地接入当前程序的过程。

学习导入系统，能让你明白：为什么有时候 `import` 会失败、为什么包能组织大型项目、为什么 AI 工程里要把数据、模型、训练、工具函数拆成不同模块。

---

## 1. 模块（Module）与包（Package）：导入的基本单位

### 1.1 模块是什么？

在 Python 中，一个 `.py` 文件就是一个**模块（module）**。模块是代码复用和命名空间隔离的基本单位。

例如，创建 `math_tools.py`：

```python
# math_tools.py
PI = 3.14159

def square(x):
    return x * x
```

在另一个文件中可以这样使用：

```python
import math_tools

print(math_tools.PI)
print(math_tools.square(3))
```

关键结论：`import math_tools` 后，Python 会执行 `math_tools.py`，并把其中定义的全局名字放进一个**模块对象（module object）**中，通过 `math_tools.xxx` 访问。

### 1.2 包是什么？

**包（package）**是存放多个模块的目录。传统包目录中需要有一个 `__init__.py` 文件，Python 会把它当作包来导入。

目录示例：

```text
my_project/
    main.py
    utils/
        __init__.py
        text.py
        math.py
```

其中 `utils` 是一个包，`utils.text` 和 `utils.math` 是子模块。

```python
# main.py
from utils.text import clean_text
from utils.math import average

print(clean_text("  Hello  "))
print(average([1, 2, 3]))
```

关键结论：包让大型项目可以按功能拆分，例如 AI 项目中常见的 `data/`、`models/`、`train/`、`utils/`。

---

## 2. `import` 的几种写法与命名空间

### 2.1 四种常见写法

```python
# 1. 导入整个模块
import math
print(math.sqrt(16))

# 2. 从模块中导入指定名字
from math import sqrt
print(sqrt(16))

# 3. 导入时起别名
import numpy as np
print(np.array([1, 2, 3]))

# 4. 从模块中导入并起别名
from math import sqrt as square_root
print(square_root(16))
```

关键结论：

- `import module` 保留模块命名空间，最清晰，适合大型工程。
- `from module import name` 直接引入名字，代码更短，但容易造成命名冲突。
- 别名（alias）常用于社区约定，例如 `import numpy as np`、`import pandas as pd`、`import torch`。

### 2.2 不要随便使用 `from module import *`

```python
# 不推荐
from math import *

print(sqrt(16))
print(pi)
```

问题是：你无法清楚知道哪些名字被导入，可能覆盖已有变量。

关键结论：工程中应避免 `from module import *`，除非模块通过 `__all__` 明确声明了公开接口。

---

## 3. Python 如何找到模块：搜索路径与 `sys.path`

当你写 `import something` 时，Python 会按顺序查找：

1. 内置模块（built-in modules），例如 `sys`、`math`。
2. `sys.path` 中的目录列表。
3. 已安装的第三方包目录，例如 `site-packages`。

可以打印 `sys.path` 观察：

```python
import sys

for p in sys.path:
    print(p)
```

典型输出会包含：

- 当前脚本所在目录
- Python 标准库目录
- `site-packages` 第三方包目录

关键结论：`sys.path` 是模块搜索路径列表。如果模块找不到，通常是路径不对、包没安装、或文件名冲突。

### 3.1 临时添加路径

```python
import sys
sys.path.append("/path/to/my/modules")

import my_module
```

但工程中更推荐使用虚拟环境、`pip install -e .` 或正确设置项目结构，而不是到处 `append` 路径。

---

## 4. 模块缓存：为什么模块只执行一次？

Python 导入模块后，会把模块对象放入 `sys.modules` 缓存。

关键结论：同一个模块在同一个 Python 进程中通常只执行一次。后续 `import` 会直接复用缓存中的模块对象。

```python
import sys
import math

print("math" in sys.modules)   # True
print(sys.modules["math"] is math)  # True
```

这意味着：

- 模块顶层代码只运行一次。
- 如果模块内部有全局状态，多次导入不会重新初始化。
- 修改模块文件后，需要重启解释器或使用 `importlib.reload()` 才能重新加载。

```python
import importlib
import my_module

importlib.reload(my_module)
```

但生产代码中应谨慎使用 `reload()`，因为它不会自动更新已经引用旧对象的代码。

---

## 5. `__name__` 与 `if __name__ == "__main__"`

每个模块都有一个内置变量 `__name__`。

- 当模块被直接运行时，`__name__` 是 `"__main__"`。
- 当模块被导入时，`__name__` 是模块名。

```python
# demo.py
print(f"当前模块名: {__name__}")

def main():
    print("执行主逻辑")

if __name__ == "__main__":
    main()
```

直接运行：

```bash
python demo.py
```

输出：

```text
当前模块名: __main__
执行主逻辑
```

被导入：

```python
import demo
```

输出：

```text
当前模块名: demo
```

关键结论：`if __name__ == "__main__":` 让一个文件既能作为脚本运行，又能作为模块被导入，是 Python 工程中的标准写法。

---

## 6. 绝对导入与相对导入

### 6.1 绝对导入（absolute import）

从项目根包开始写完整路径：

```python
from my_project.utils.text import clean_text
```

清晰、推荐，适合大型项目。

### 6.2 相对导入（relative import）

在当前包内部用 `.` 和 `..` 表示相对位置：

```python
# 在 my_project/train/trainer.py 中
from ..utils.text import clean_text
```

其中：

- `.` 表示当前包。
- `..` 表示上一级包。

关键结论：相对导入只能用于包内部，不能用于直接运行的脚本。工程中通常推荐绝对导入，可读性更强。

---

## 7. AI 工程中的导入系统

在一个典型 AI 项目中，你可能这样组织代码：

```text
ai_project/
    train.py
    data/
        __init__.py
        dataset.py
    models/
        __init__.py
        mlp.py
    utils/
        __init__.py
        seed.py
```

`train.py` 中导入：

```python
from data.dataset import get_dataloader
from models.mlp import MLP
from utils.seed import set_seed

set_seed(42)
model = MLP()
dataloader = get_dataloader()
```

关键结论：导入系统让 AI 项目可以模块化：数据、模型、训练、工具函数各自独立，便于测试、复用和协作。

---

## 8. 常见导入错误与排查思路

### 8.1 `ModuleNotFoundError`

表示 Python 找不到模块。常见原因：

- 模块没有安装。
- 当前工作目录不对。
- 包路径不在 `sys.path` 中。
- 文件名拼写错误。

排查：

```python
import sys
print(sys.path)
```

### 8.2 `ImportError`

表示模块找到了，但导入的名字不存在。例如：

```python
from math import sqrt2  # 不存在
```

应检查模块中是否真的定义了该名字。

### 8.3 循环导入（circular import）

`a.py` 导入 `b.py`，`b.py` 又导入 `a.py`，容易出错。

解决思路：

- 把公共依赖抽到第三个模块。
- 延迟导入，把 `import` 放到函数内部。
- 使用类型检查专用导入 `if TYPE_CHECKING:`。

---

## 9. 工程级建议

1. **优先使用绝对导入**，结构清晰。
2. **避免 `from module import *`**。
3. **模块顶层只做定义，不要执行重副作用代码**。
4. 用 `if __name__ == "__main__":` 保护脚本入口。
5. 大型项目用包组织代码，例如 `data/`、`models/`、`utils/`。
6. 用虚拟环境隔离依赖，避免不同项目互相污染。
7. 理解 `sys.path` 和 `sys.modules`，排查导入问题会快很多。

---

## 动手练习

### 任务：创建一个小型包并正确导入

在本地创建一个项目目录：

```text
import_practice/
    main.py
    tools/
        __init__.py
        text.py
        number.py
```

要求：

1. 在 `tools/text.py` 中定义函数 `clean_text(s)`，去掉字符串两端空白并转小写。
2. 在 `tools/number.py` 中定义函数 `average(nums)`，返回列表平均值。
3. 在 `tools/__init__.py` 中暴露这两个函数：

```python
from .text import clean_text
from .number import average
```

4. 在 `main.py` 中：
   - 从 `tools` 导入 `clean_text` 和 `average`。
   - 打印 `clean_text("  Hello World  ")`。
   - 打印 `average([10, 20, 30])`。
   - 使用 `if __name__ == "__main__":` 保护主逻辑。

5. 运行：

```bash
cd import_practice
python main.py
```

预期输出类似：

```text
hello world
20.0
```

进阶：

- 打印 `__name__` 观察直接运行与导入时的区别。
- 尝试在 `main.py` 中写 `import tools`，然后调用 `tools.clean_text(...)`，比较两种导入方式。

## py.cpy.frame

# 函数调用栈帧（Call Frame）：Python 运行时的「现场记录」

> **一句话直觉**：当 Python 执行一个函数调用时，它会在内存中开辟一块「现场记录」——栈帧（**frame**，也叫调用帧），用来保存这个函数当前的局部变量、参数、执行到哪一行、上一个调用者是谁。理解了帧，你就能看懂调用栈、调试器、递归、装饰器、`inspect`、异常回溯这些「高级」话题的本质。

本讲义对应知识点 `py.cpy.frame`（Python 调用帧）。前置知识为零，从零栈帧讲起。

---

## 1. 为什么需要「帧」——从一次函数调用说起

Python 解释器（**CPython**）执行代码时，本质是在一个「调用栈（**call stack**）」上不断压入/弹出帧对象。

- **调用栈（call stack）**：一个后进先出（LIFO）的帧序列，栈顶是当前正在执行的函数。
- **帧对象（frame object）**：Python 中类型为 `types.FrameType` 的运行时对象，保存：
  - `f_locals`：当前函数的局部变量字典；
  - `f_globals`、`f_builtins`：模块全局与内建命名空间；
  - `f_code`：对应的 **code object**（编译后的字节码）；
  - `f_lineno`：当前执行到的行号；
  - `f_back`：调用链上的上一帧（即「谁调用了当前函数」）。

直觉：`f_back` 就是「上一层的现场」，把它串起来就是完整的调用栈。

```python
# 一次简单调用，观察帧对象的来源
import sys

def inner():
    # sys._getframe(0) 就是当前帧（inner 自己的帧）
    f = sys._getframe(0)
    print("当前函数:", f.f_code.co_name)       # inner
    print("当前行号:", f.f_lineno)              # 打印这一行的行号
    print("调用者函数:", f.f_back.f_code.co_name)  # outer

 def outer():
    inner()

outer()
```

> 注：示例中 `def outer` 前有一个多余空格，运行前请删除缩进错误，保证脚本能跑通。

**关键结论**：Python 没有「显式传递调用者」语法，`sys._getframe` 或 `inspect.currentframe()` 是拿到当前帧的唯一入口。

---

## 2. 帧对象的三件套：`f_back`、`f_code`、`f_locals`

### 2.1 `f_back`：向上追溯整个调用栈

```python
import sys

def a():
    b()

def b():
    c()

def c():
    f = sys._getframe(0)
    chain = []
    while f is not None:
        chain.append(f.f_code.co_name)
        f = f.f_back
    print("调用栈（从内到外）:", chain)  # ['c', 'b', 'a', '<module>']

a()
```

异常回溯打印的 `Traceback (most recent call last)`，本质上就是把 `f_back` 链从外到内走了一遍。

### 2.2 `f_code`：代码对象（code object）

`f_code` 是编译阶段生成的、不可变的字节码描述，包含：

- `co_name`：函数名；
- `co_filename`：源文件；
- `co_argcount`：参数个数；
- `co_varnames`：局部变量名元组；
- `co_consts`：常量池。

```python
import sys

def add(x, y=1):
    z = x + y
    f = sys._getframe(0)
    print("函数名:", f.f_code.co_name)         # add
    print("参数个数:", f.f_code.co_argcount)   # 2
    print("局部变量名:", f.f_code.co_varnames) # ('x', 'y', 'z')
    return z

add(2, 3)
```

**关键结论**：同一函数的每次调用，`f_code` 是共享的；帧本身是每次调用新建的。因此 `f_code` 是「函数身份」，帧是「一次执行的现场」。

### 2.3 `f_locals`：当前局部变量

```python
import sys

def demo(a, b):
    c = a * b
    f = sys._getframe(0)
    print(f.f_locals)   # {'a': 2, 'b': 3, 'c': 6}
    return c

demo(2, 3)
```

注意：`f_locals` 在 CPython 中是一个「快照式」字典（Python 3.13+ 对 `FrameLocalsProxy` 有变化），修改它**不保证**写回真实局部变量，具体见误区章节。

---

## 3. 帧与函数调用、递归、装饰器的关系

### 3.1 函数调用 = 压栈；返回 = 弹栈

```python
import sys

def depth():
    n = 0
    f = sys._getframe(0)
    while f is not None:
        n += 1
        f = f.f_back
    return n

def outer():
    def middle():
        def inner():
            return depth()
        return inner()
    return middle()

print("栈深度:", outer())  # 约 5 层（含模块层）
```

递归容易 `RecursionError`，本质就是栈帧数量达到解释器限制（`sys.getrecursionlimit()`）。

### 3.2 装饰器：包了一层帧

```python
import functools, sys

def trace(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        caller = sys._getframe(1).f_code.co_name  # 谁调用了 wrapper
        print(f"[trace] {caller} -> {fn.__name__}")
        return fn(*args, **kwargs)
    return wrapper

@trace
def greet(name):
    return f"Hello, {name}"

def main():
    print(greet("Ada"))

main()
```

**关键结论**：`f_back` 让任何工具（调试器、日志、APM）都能感知「谁调用了谁」。

### 3.3 帧与异常回溯

`raise` 时 CPython 把帧信息写入 `traceback object`，于是你能看到每一层的文件名和行号。`traceback.walk_tb(tb)` 遍历的就是帧链。

---

## 4. 工程级：如何安全、正确地使用帧

### 4.1 正确拿帧：优先用 `inspect`

`sys._getframe` 是 CPython 私有的加速入口；跨实现更稳妥的是 `inspect.currentframe()`。

```python
import inspect

def probe():
    f = inspect.currentframe()
    try:
        print(f.f_code.co_name, "->", f.f_back.f_code.co_name)
    finally:
        # 手动断开引用，避免循环引用（帧会引用其局部变量，可能拖慢 GC）
        del f

probe()
```

### 4.2 帧会延长对象生命周期

帧对象持有 `f_locals`、`f_back`，一旦被外部变量引用，整条调用链及其局部变量都无法回收——这是内存泄漏的经典来源（例如把帧存到全局缓存、闭包以外的容器）。

```python
import sys, gc

saved = []

def leak():
    big = [0] * 10_000_000   # 大对象
    saved.append(sys._getframe(0))  # 危险：帧连同 big 一起被引用

leak()
print("saved 里存了帧，big 无法释放")
del saved
gc.collect()
print("清理后恢复正常")
```

**关键结论**：用完帧立刻 `del`，不要把它长期存在容器/全局里。

### 4.3 修改局部变量：`f_locals` 不可靠

在 CPython 3.13 之前，`f_locals` 是快照；3.13+ 用 `FrameLocalsProxy` 实现了写回，但仍然不应依赖此行为做业务逻辑。正确做法是把数据通过参数/返回值显式传递。

---

## 5. 动手练习：自实现一个迷你「异常回溯打印器」

**任务**：写一个 `mini_traceback.py`，在不使用 `traceback` 模块的前提下，利用帧对象打印出从当前函数到模块顶层的调用路径，格式与 Python 官方 Traceback 类似：

```
Traceback (most recent call last):
  File "demo.py", line XX, in <module>
    main()
  File "demo.py", line YY, in main
    foo()
  File "demo.py", line ZZ, in foo
    bar()
  ...
```

要求：
1. 用 `sys._getframe(0)` 拿当前帧，沿 `f_back` 一路向顶层遍历。
2. 每帧输出 `f_code.co_filename`、`f_lineno`、`f_code.co_name`。
3. 最后再调用一次官方 `traceback.print_stack()` 做对比，验证两者一致。
4. 写一个 4 层嵌套函数调用（`main → foo → bar → baz`）来触发，观察输出。

**验收点**：能解释为什么栈顺序与官方一致（因为 `f_back` 就是按执行顺序链接的）。

```python
import sys
import traceback


def render_frame(f):
    return '  File "{file}", line {line}, in {name}'.format(
        file=f.f_code.co_filename,
        line=f.f_lineno,
        name=f.f_code.co_name,
    )


def print_mini_traceback():
    print("Mini Traceback (most recent call last):")
    frames = []
    f = sys._getframe(0)
    while f is not None:
        frames.append(f)
        f = f.f_back
    # 从外层到内层打印（与官方 Traceback 顺序一致）
    for frame in reversed(frames):
        print(render_frame(frame))


def baz():
    print_mini_traceback()


def bar():
    baz()


def foo():
    bar()


def main():
    print("=== mini traceback ===")
    foo()

    print("\n=== official traceback ===")
    traceback.print_stack()


if __name__ == "__main__":
    main()
```


---

## 本课题目

### single_choice · None



- [A] mypkg 被导入，同时会触发导入 mypkg.sub，且 mypkg 命名空间中会有 sub 这个属性
- [B] 只会导入 mypkg，sub 需要外部代码再单独 `import mypkg.sub` 才会被导入
- [C] 会抛出 ImportError，因为包内不能用相对导入
- [D] 会导入 mypkg.sub，但 mypkg 命名空间中不会有 sub，只能通过 `from mypkg import sub` 访问

**参考答案**：0

**解析**：__init__.py 在包被导入时执行，其中的相对导入 `from . import sub` 会导入子模块，并把 sub 绑定为包的属性。

### single_choice · None



- [A] 只执行 a.b.c 模块，a 与 a.b 不会执行
- [B] 依次执行 a、a.b、a.b.c 三个模块，并把名字 a 绑定到当前命名空间
- [C] 依次执行 a、a.b、a.b.c 三个模块，并把名字 c 绑定到当前命名空间
- [D] 只执行 a.b.c 模块，并把名字 a、b、c 都绑定到当前命名空间

**参考答案**：1

**解析**：import a.b.c 会导入并执行父包 a 和 a.b，最终把顶层名 a 绑定到当前命名空间；不会绑定 b 或 c。

### single_choice · None



- [A] 可以，因为包初始化时导入的名字会成为包的属性
- [B] 不可以，包初始化时导入的名字只存在于 __init__.py 内部
- [C] 可以，但只限于 os 是标准库模块的情况
- [D] 不可以，除非在 __init__.py 中写 __all__ = ['os']

**参考答案**：0

**解析**：包初始化时导入的子模块或名字会绑定为包的属性，因此 mypkg.os 可以访问。

### single_choice · None



- [A] 当模块作为主程序直接运行时，__name__ 的值为 '__main__'
- [B] 当模块被导入时，__name__ 的值为 '__main__'
- [C] 任何情况下 __name__ 都等于模块文件名（不含扩展名）
- [D] 只有包内的模块才有 __name__ 属性

**参考答案**：0

**解析**：模块直接运行时 __name__ 为 '__main__'；被导入时为模块的限定名。

### single_choice · None



- [A] 等价于 `import json.decoder`，并在当前命名空间绑定 json
- [B] 等价于动态导入 json.decoder 并返回该模块对象，但不自动在当前命名空间绑定名字
- [C] 等价于 `from json import decoder`，并在当前命名空间绑定 decoder
- [D] 只能导入顶层模块，不能导入带点的子模块

**参考答案**：1

**解析**：importlib.import_module 返回被导入的模块对象，不自动把名字绑定到调用者的命名空间。

### single_choice · None



- [A] 每个模块被导入后，其模块对象会缓存在 sys.modules 中，后续导入直接复用
- [B] 导入缓存只缓存包，不缓存普通模块
- [C] 导入缓存每次程序启动时都会清空，且运行中无法访问
- [D] 删除 sys.modules 中的条目不会影响后续导入行为

**参考答案**：0

**解析**：导入成功后模块对象保存在 sys.modules，后续导入命中缓存，不重复执行模块代码。

### single_choice · None



- [A] pkg 目录下同时存在 mod.py 和 helper.py，且 pkg 可被正常导入
- [B] helper.py 必须与 mod.py 在文件系统同一层，但不需要 pkg 是包
- [C] helper.py 必须位于 mod.py 的同级目录并命名为 __init__.py
- [D] helper 必须是 pkg 的顶层属性，而不能是子模块

**参考答案**：0

**解析**：相对导入要求模块处于包上下文中，同包下的子模块可以通过 `from . import helper` 导入。

### single_choice · None



- [A] 它会导入模块中所有以下划线开头的名字
- [B] 如果模块定义了 __all__，则只导入 __all__ 中列出的名字；否则通常不导入下划线开头的名字
- [C] 它等价于 `import module`，只是写法不同
- [D] 它只能用于包，不能用于普通模块

**参考答案**：1

**解析**：未定义 __all__ 时，`import *` 不会导入下划线开头的名字；定义了 __all__ 时以其为准。

### single_choice · None



- [A] 两种情况下 run() 都会被自动调用
- [B] 直接执行时 __name__ 为 '__main__'，会调用 run()；被导入时不会自动调用
- [C] 被导入时 __name__ 为 '__main__'，会调用 run()；直接执行时不会
- [D] 两种情况下都不会调用 run()，因为 python 不会执行模块顶层代码

**参考答案**：1

**解析**：直接运行时 __name__ 为 '__main__'，条件成立；被导入时 __name__ 为模块名，条件不成立。

### single_choice · None



- [A] 仍然支持，写 `import helper` 会自动优先查找同包内的 helper
- [B] 已不再支持，包内引用同级模块需要显式相对导入或绝对导入
- [C] 仅在 __init__.py 中支持，普通模块中不支持
- [D] 仅在命名空间包中支持

**参考答案**：1

**解析**：Python 3 取消了隐式相对导入，包内应使用显式相对导入（from . import helper）或绝对导入。

### single_choice · None



- [A] `from pkg.util import f`
- [B] `from .util import f`
- [C] `from util import f`
- [D] `import f`

**参考答案**：0

**解析**：main.py 直接运行时没有包上下文，应使用绝对导入 `from pkg.util import f`。相对导入在直接运行的脚本中会失败。

### single_choice · None



- [A] 总是先查找内置模块，再按 sys.path 顺序查找文件系统
- [B] 只查找文件系统，不查找内置模块
- [C] 先查找第三方 site-packages，再查找标准库
- [D] 查找顺序与 sys.path 无关，只由环境变量决定

**参考答案**：0

**解析**：导入时先查内置模块，再按 sys.path 中的条目顺序查找。

### single_choice · None



- [A] 绑定了 a
- [B] 绑定了 b
- [C] 绑定了 c
- [D] 同时绑定了 a、b、c

**参考答案**：2

**解析**：from ... import ... 只把 import 后列出的名字绑定到当前命名空间，因此只绑定 c。

### single_choice · None



- [A] 第一次导入会执行 a 和 a.b，第二次不会重复执行 a.b 的顶层代码
- [B] 两次导入都会重新执行 a.b 的顶层代码
- [C] 第二次导入会报错，因为 a.b 已经被导入过
- [D] 第一次导入只会执行 a，第二次才会执行 a.b

**参考答案**：0

**解析**：第二次导入同一个模块时，模块缓存会命中，故不会重复执行顶层代码；第一次导入会依次执行父包与子模块。

### single_choice · None



- [A] `from .sub import thing`（sub 为同包下的子模块）
- [B] `import .sub`
- [C] `from .. import sub`（sub 为同包下的子模块）
- [D] `import pkg.sub`（假定 pkg 尚未被导入）

**参考答案**：0

**解析**：相对导入使用 from ... import 形式；`import .sub` 语法非法。同包内引用同级子模块可用 `from .sub import thing`。

### single_choice · None



- [A] 正常工作，因为 . 表示当前目录
- [B] 报 ImportError，因为此时模块没有包上下文
- [C] 正常工作，因为 Python 会自动推断包名
- [D] 只在 Python 2 中会报错，Python 3 中正常工作

**参考答案**：1

**解析**：直接运行脚本时，该模块不以包成员身份加载，缺少包上下文，因此相对导入会失败。

### single_choice · None



- [A] 它限制 `import module` 时能访问哪些属性，未列出的属性会消失
- [B] 它控制 `from module import *` 时导入哪些名字，未列出的名字不会因 * 被导入
- [C] 它是必须定义的，否则 `from module import *` 会报错
- [D] 它只对包有效，普通模块中定义没有作用

**参考答案**：1

**解析**：__all__ 是给 `from module import *` 使用的白名单，不影响普通属性访问或显式导入。

### single_choice · None



- [A] 它是一个只读元组，不能修改
- [B] 它是模块查找路径的列表，运行时可插入自定义目录来影响后续导入
- [C] 它只包含当前工作目录，不包含标准库目录
- [D] 它由 PYTHONPATH 完全决定，运行时修改无效

**参考答案**：1

**解析**：sys.path 是列表，用于模块查找；运行时修改它可以影响后续导入查找。

### single_choice · None



- [A] 正常导入，因为 Python 会自动处理循环导入
- [B] 可能出现部分初始化的模块对象，进而引发 AttributeError 或 ImportError
- [C] 一定报 SyntaxError
- [D] 一定报 RuntimeError，因为检测到循环依赖

**参考答案**：1

**解析**：循环导入时，一个模块可能在另一个模块执行完之前就被引用，拿到的是部分初始化的模块对象，从而出错。

### single_choice · None



- [A] 它要求每个子目录都包含 __init__.py
- [B] 它允许把同一逻辑包的多个部分分散在不同的目录中，而不需要 __init__.py
- [C] 它只能用于标准库，用户代码无法创建
- [D] 它与常规包在导入机制上完全一样，只是少了 __init__.py

**参考答案**：1

**解析**：命名空间包（PEP 420）允许没有 __init__.py 的目录片段共同组成同一个包，可以跨多个 sys.path 条目。

### single_choice · None



- [A] 绿线程的调度完全由操作系统内核负责
- [B] 绿线程在用户态进行调度，切换开销远小于操作系统线程
- [C] 每个绿线程都必须绑定一个独立的内核线程才能运行
- [D] 绿线程之间无法共享同一个进程的内存空间

**参考答案**：1

**解析**：绿线程（greenlet/协程）由用户态代码或运行时库自行调度，不经过内核，因此上下文切换开销小；而操作系统线程的调度由内核负责，切换需要陷入内核态。绿线程仍属于同一进程，共享内存空间。

### single_choice · None



- [A] 这些 greenlet 会在多个 CPU 核心上真正并行执行
- [B] 这些 greenlet 并发但不会并行，因为它们共享同一个 OS 线程
- [C] 操作系统会自动把这些 greenlet 分配到不同核心
- [D] greenlet 切换会自动获得 GIL 并释放，实现并行

**参考答案**：1

**解析**：并发（concurrency）指多个任务交替推进，并行（parallelism）指同一时刻真正同时执行。单个 OS 线程内的多个 greenlet 只能交替运行，属于并发而非并行。

### multi_choice · None



- [A] 某个 greenlet 执行了一个长时间不切换的纯计算循环
- [B] 某个 greenlet 进行了阻塞式文件读写并且没有让出控制权
- [C] 某个 greenlet 在循环中定期显式切换到其他 greenlet
- [D] 某个 greenlet 持锁等待时直接忙等且不切换

**参考答案**：[0, 1, 3]

**解析**：协作式调度依赖显式切换点，任何长时间不让出控制权的行为都会阻塞同线程的其他 greenlet，包括纯计算、阻塞 I/O、忙等。定期显式切换则允许其他 greenlet 运行，不会阻塞。

### fill_blank · None



**参考答案**：["协作", "协作式", "cooperative", "cooperative scheduling"]

**解析**：greenlet 的核心特征是协作式调度（cooperative scheduling），切换由程序主动触发而非内核抢占。对比操作系统线程的抢占式调度。

### fill_blank · None



**参考答案**：["并发", "concurrency", "concurrent"]

**解析**：同一线程内的 greenlet 交替执行属于并发；并行需要多个执行流同时在不同核心上运行，这要求多线程/多进程或释放 GIL 的机制。

### fill_blank · None



**参考答案**：["栈", "调用栈", "stack", "执行栈"]

**解析**：每个 greenlet 拥有独立调用栈，切换时保存当前栈、恢复目标栈。这种用户态栈管理避免了陷入内核的开销。

### code_reading · None



**参考答案**：A1 -> B1 -> A2 -> B2

**解析**：task_a 先打印 A1，然后显式切换到 task_b；task_b 打印 B1，再切换回 task_a；task_a 从切换点继续打印 A2，然后 task_a 结束并把控制权交还；最后 task_b 恢复打印 B2。整个顺序由显式切换点决定，体现了协作式调度的可预测性。

### code_reading · None



**参考答案**：打印顺序为 before -> inside -> after；worker 结束后控制权回到启动它的父 greenlet（即主 greenlet），继续执行 after。

**解析**：创建 greenlet 不会立即运行，只有调用 switch 才会进入 worker 打印 inside。worker 函数返回后，控制权自动交还给父 greenlet，主流程继续执行 after。

### code_reading · None



**参考答案**：other 只在 busy 让出控制权时才会运行。由于 busy 的循环中没有显式切换点，它不会主动让出控制权，因此在整个循环执行期间 other 无法运行，会被阻塞到 busy 结束或自行让出为止。

**解析**：协作式调度下，切换只发生在显式让出点。纯计算长循环不含切换点，会一直占住 OS 线程，导致同线程其他 greenlet 得不到执行机会。

### scenario · None



**解析**：根因是 greenlet 为协作式调度，只有在显式切换点才会让出控制权。长时间不切换的复杂计算会占住唯一的 OS 线程，其他任务无法推进。改进思路包括：把长计算拆分成若干小段，在段间显式让出；引入定期让出机制；或将 CPU 密集部分放到独立进程/线程执行。

### scenario · None



**解析**：阻塞式系统调用会占住整个 OS 线程，协作式调度无法在阻塞期间把控制权交给其他 greenlet。正确方向是改用非阻塞 I/O 并配合事件循环，或在等待前显式让出控制权由事件循环统一驱动。

### scenario · None



**解析**：该方案不合理。greenlet 运行在单个 OS 线程内，受 GIL 约束，无法利用多核实现并行；对 CPU 密集型任务，greenlet 只能算并发而非并行，不会提升吞吐。CPU 密集型任务应使用多进程或能释放 GIL 的方案。

### single_choice · None



- [A] greenlet 会在任意字节码指令处被操作系统的时钟中断抢占式切换
- [B] greenlet 只有在显式调用切换操作时才会发生控制权转移
- [C] greenlet 依赖操作系统的调度器进行时间片轮转
- [D] greenlet 只能在 sleep 时被切换，其他情况不能切换

**参考答案**：1

**解析**：greenlet 是协作式（cooperative）的，控制权转移只发生在显式切换调用点，不会被时钟中断抢占。这也意味着一个长时间不切换的 greenlet 会阻塞同线程内其他 greenlet。

### single_choice · None



- [A] 其他 greenlet 会自动接管该线程继续运行
- [B] 整个线程被阻塞，同线程内的其他 greenlet 也无法推进
- [C] 操作系统会为其他 greenlet 创建新的线程来运行
- [D] 阻塞读取会自动转为非阻塞并切换到其他 greenlet

**参考答案**：1

**解析**：greenlet 是协作式调度的，阻塞系统调用会占住整个 OS 线程，同线程内其他 greenlet 无法运行。要实现非阻塞并发，需要配合事件循环或非阻塞 I/O。

### single_choice · None



- [A] 所有 greenlet 共享同一份调用栈
- [B] 每个 greenlet 拥有自己独立的调用栈，切换时保存和恢复各自的栈
- [C] greenlet 没有栈的概念，只有寄存器
- [D] greenlet 的栈由操作系统内核统一分配和管理

**参考答案**：1

**解析**：每个 greenlet 维护自己的执行栈，切换时保存当前栈并切换到目标栈，这也是切换开销虽小但并非零成本的原因。栈由运行时库在用户态管理。

### single_choice · None



- [A] 直接终止整个进程
- [B] 自动返回其父 greenlet（即创建或切换到它的那个 greenlet）
- [C] 永远挂起，需要手动删除
- [D] 抛出一个未捕获异常导致崩溃

**参考答案**：1

**解析**：greenlet 结束时会把控制权交还给其父 greenlet。父 greenlet 关系在创建或切换时确立，这正是 greenlet 能嵌套恢复的基础。

### single_choice · None



- [A] 使用 greenlet 可以绕过 GIL 实现多核 CPU 并行
- [B] greenlet 运行在单一线程内，由于这个线程受 GIL 约束，CPU 密集型任务无法靠 greenlet 获得多核加速
- [C] greenlet 会为每个协程创建一个 GIL
- [D] GIL 只对 IO 操作生效，对 greenlet 无影响

**参考答案**：1

**解析**：GIL 是解释器级别的锁，约束的是线程。greenlet 在同一线程内切换，不会增加可用于 CPU 并行的核心数，因此 CPU 密集型任务无法通过 greenlet 提速。

### multi_choice · None



- [A] 切换点由程序显式控制，更容易推理数据一致性
- [B] 一个不主动让出控制权的任务会阻塞整组任务
- [C] 调度器可以随时用时间片强行中断任务
- [D] 切换通常不进入内核态，开销较小

**参考答案**：[0, 1, 3]

**解析**：协作式的优点是切换点明确、开销小；缺点是缺少抢占能力，一个不切换的任务会饿死其他任务。选项 C 描述的是抢占式调度，属于操作系统线程的特点。

### multi_choice · None



- [A] 要求在同一线程内保持大量轻量执行单元、频繁切换的 I/O 密集场景
- [B] 需要在多个 CPU 核心上并行计算大量纯 CPU 任务
- [C] 希望在用户态实现自定义调度逻辑
- [D] 希望在切换开销上低于操作系统线程

**参考答案**：[0, 2, 3]

**解析**：greenlet 适合 I/O 密集、需要在用户态自定义调度、且关注切换开销的场景。要利用多核并行 CPU 任务，应使用多进程或原生线程配合释放 GIL，greenlet 无法做到。

### multi_choice · None



- [A] greenlet 本身不提供事件循环，需要外部库或框架来驱动
- [B] 配合事件循环时，可以把阻塞式 I/O 改造成让出控制权的形式
- [C] greenlet 会自动启动一个事件循环，无需任何外部依赖
- [D] 通过让出控制权，事件循环可以在等待 I/O 时运行其他任务

**参考答案**：[0, 1, 3]

**解析**：greenlet 只是切换机制，不包含事件循环。要发挥非阻塞并发的效果，需要事件循环来驱动并在等待 I/O 时调度其他任务。C 项错误，greenlet 不会自动创建事件循环。
