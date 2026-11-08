# s1u6l3 Python 模块与包：从零到工程级 / `py.module.init`：模块初始化与模块级元数据

> 来源 `content/lessons/s1u6l3.json`

## py.module.package

# Python 模块与包：从零到工程级

> 一句话直觉：**模块（module）是一个 `.py` 文件，包（package）是一个装模块的文件夹；学会它们，你才能把代码拆开、复用、共享，而不是把所有东西塞进一个文件里。**

---

## 1. 为什么需要模块与包？

写代码时你很快会遇到三个问题：

1. **文件太长**：几千行代码挤在一个 `.py` 文件里，找函数像大海捞针。
2. **重复代码**：多个项目都要用同一个工具函数，复制粘贴很痛苦。
3. **命名冲突**：两个人都写了一个 `utils.py`，怎么在同一个程序里同时用？

模块和包就是 Python 给出的答案：

- **模块（module）**：任何 `.py` 文件都是一个模块，文件名就是模块名。
- **包（package）**：一个包含 `__init__.py` 的文件夹是一个包，里面可以放多个模块和子包。
- **导入（import）**：把别人写好的模块拿进来用。

---

## 2. 模块：最小的可复用单元

### 2.1 定义一个模块

新建 `greet.py`：

```python
# greet.py
"""一个简单的问候模块。"""

def hello(name):
    """返回一句问候语。"""
    return f"Hello, {name}!"

PI = 3.14159
```

### 2.2 导入并使用

```python
# main.py
import greet                     # 导入整个模块
from greet import hello, PI      # 导入特定名字

print(greet.hello("Alice"))      # 用模块名访问
print(hello("Bob"))              # 直接使用导入的名字
print(PI)
```

**关键点**：
- `import greet` 让整个模块作为一个对象可用，通过 `greet.xxx` 访问。
- `from greet import hello` 把名字直接引入当前命名空间，可能与本地名字冲突。
- 模块只在第一次被导入时执行一次，之后 Python 会缓存它（放在 `sys.modules`）。

### 2.3 模块的“魔法”变量

| 变量 | 含义 |
| --- | --- |
| `__name__` | 模块名；直接运行时为 `"__main__"` |
| `__file__` | 模块文件的路径 |
| `__all__` | 控制 `from module import *` 时导出的名字 |
| `__doc__` | 模块的文档字符串 |

最常见的用法：

```python
# greet.py 底部
if __name__ == "__main__":
    print(hello("World"))   # 只有直接运行 greet.py 时才执行
```

---

## 3. 包：把模块装进文件夹

### 3.1 最小包结构

```
myproject/
├── main.py
└── utils/
    ├── __init__.py
    ├── math_tools.py
    └── string_tools.py
```

`__init__.py` 可以为空，也可以写初始化代码。它让 Python 把 `utils` 当作一个包。

### 3.2 导入包里的模块

```python
# main.py
from utils import math_tools
from utils.string_tools import shout

print(math_tools.add(1, 2))
print(shout("hi"))
```

### 3.3 相对导入 vs 绝对导入

- **绝对导入（absolute import）**：`from utils.math_tools import add`，清晰，推荐。
- **相对导入（relative import）**：`from . import math_tools`，只能在包内部使用，适合深层目录。

```python
# utils/__init__.py
from . import math_tools          # 相对导入
from .string_tools import shout   # 相对导入
```

### 3.4 `__all__` 与 `__version__`

```python
# utils/__init__.py
"""Utils package."""

__all__ = ["math_tools", "shout"]
__version__ = "0.1.0"
__author__ = "Your Name"
```

`__all__` 决定 `from utils import *` 时导出哪些名字；同时它也是一种“公开 API”声明。工程代码应避免 `import *`，但 `__all__` 仍建议写上。

---

## 4. 工程级实践：命名、导入顺序、可维护性

### 4.1 命名规范（PEP 8）

- 模块名：短、全小写、可含下划线，如 `math_tools.py`。
- 包名：短、全小写、**不推荐下划线**，如 `utils`、`datatools`。
- 类名：`CapWords`，如 `HttpServerError`。
- 函数/变量：`lower_case_with_underscores`。
- 常量：`UPPER_CASE_WITH_UNDERSCORES`。
- 内部使用：单下划线前缀 `_internal_func`。
- 避免用 `l`、`O`、`I` 作为单字符变量名。

### 4.2 导入顺序（三组，空行分隔）

```python
# 1. 标准库
import os
import sys

# 2. 第三方库
import requests

# 3. 本项目内部
from myproject.utils import math_tools
```

每行只导入一个模块（`from subprocess import Popen, PIPE` 除外）。

### 4.3 模块级 dunder 的位置

按 PEP 8：**文档字符串之后、其他 import 之前**（`__future__` 除外，它必须最靠前）。

```python
"""My module docstring."""

from __future__ import annotations

__all__ = ["a", "b", "c"]
__version__ = "0.1"
__author__ = "Cardinal Biggles"

import os
import sys
```

### 4.4 常见反模式

- ❌ `from module import *`：污染命名空间，读者不知道名字从哪来。
- ❌ 循环导入：`a.py` 导入 `b.py`，`b.py` 又导入 `a.py`。解耦或延迟导入。
- ❌ 把可执行代码写在模块顶层，导入时产生副作用。
- ❌ 包目录层级过深（超过 3~4 层），增加维护成本。

---

## 5. 动手练习

**任务**：创建一个名为 `shapes` 的包，包含两个模块 `rectangle.py` 和 `circle.py`：

1. `rectangle.py` 提供 `area(width, height)` 与 `perimeter(width, height)`。
2. `circle.py` 提供 `area(radius)` 与 `circumference(radius)`，使用 `math.pi`。
3. 在 `shapes/__init__.py` 中写 `__all__ = ["rectangle", "circle"]` 和 `__version__ = "1.0.0"`。
4. 在包外写 `demo.py`，用**绝对导入**调用两个模块，打印一个 3×4 矩形和一个半径 2 的圆的结果。
5. 每个模块都加上 `if __name__ == "__main__":` 的自测代码。

**验收**：`python demo.py` 能正常输出；`python -m shapes.rectangle` 也能单独运行模块自测。

---

## py.module.init

# `py.module.init`：模块初始化与模块级元数据

> **一句话直觉**：Python 里每个 `.py` 文件在被 `import` 的那一刻，会从上到下“执行一遍”，而 `__init__`、`__all__`、`__version__` 这些“模块级 dunder 名称”就是你在这一刻向解释器、导入系统和其他开发者递出的名片。

---

## 1. 什么是“模块初始化”？

当你写 `import mymod` 时，Python 并不只是“打开文件读定义”，而是**真正执行 `mymod.py` 的顶层代码**：

- 创建模块对象（module object），放入 `sys.modules`；
- 在模块的命名空间（namespace）中逐行执行语句；
- 执行完后，`import` 语句把模块对象绑定到你当前的名字空间。

因此**顶层代码的副作用（side effect）就是初始化行为**，例如打印日志、注册插件、读取配置。

```python
# mymod.py
print("mymod is being initialized")  # 顶层代码，import 时都会执行

CONFIG = {"debug": False}

def hello():
    return "hi"
```

```python
# main.py
import mymod           # 输出: mymod is being initialized
import mymod           # 无输出，因为 sys.modules 里已缓存
print(mymod.hello())   # hi
```

> **关键结论 1**：模块只在**第一次**被导入时初始化一次；之后的 `import` 只是从 `sys.modules` 缓存里取出模块对象。

---

## 2. 模块级 dunder：`__name__` 与 `__file__`

Python 在导入时自动为模块注入一批“双下划线包裹”的属性（dunder, double underscore），最常用的两个是：

- `__name__`：模块名字符串。作为脚本直接运行时是 `"__main__"`，被 import 时是模块名。
- `__file__`：模块文件路径（部分内置模块没有）。

```python
# mymod.py
print("__name__ =", __name__)
print("__file__ =", __file__)

if __name__ == "__main__":
    print("被当作脚本直接运行")
else:
    print("被其他模块 import")
```

```bash
$ python mymod.py
__name__ = __main__
__file__ = /abs/path/mymod.py
被当作脚本直接运行

$ python -c "import mymod"
__name__ = mymod
__file__ = /abs/path/mymod.py
被其他模块 import
```

> **关键结论 2**：`if __name__ == "__main__":` 是“既能当模块又能当脚本”的惯用法（idiom），让顶层“执行入口”只在直接运行时触发。

---

## 3. 模块文档与 `__doc__`：模块的自我介绍

模块最开头的一个字符串字面量会成为 `__doc__`，也就是模块的 docstring。PEP 257 要求：

- 单行 docstring：开头和结尾的 `"""` 写在同一行，例如 `"""Return an ex-parrot."""`；
- 多行 docstring：首行是概述，空一行后是细节，最后一行的 `"""` 单独成行。

```
"""mymod 模块：演示模块 docstring。

这是一个多行 docstring 示例。
"""

__version__ = "0.1"


def frobnicate():
    """Return an ex-parrot."""
    return "ex-parrot"
```

```python
import mymod
print(mymod.__doc__)          # 打印上面那段说明
print(mymod.frobnicate.__doc__)  # Return an ex-parrot.
```

> **关键结论 3**：模块 docstring 是**第一个语句**才有效；被注释或赋值语句挡在前面的字符串不会成为 `__doc__`。

---

## 4. 显式声明公共接口：`__all__`

`__all__` 是一个字符串列表（list of str），决定 `from mymod import *` 时**哪些名字会被导出**。

```python
# mymod.py
__all__ = ["a", "b", "c"]

a = 1
b = 2
c = 3
d = 4        # 不在 __all__ 中
_internal = 5  # 下划线开头，本就默认不导出
```

```python
from mymod import *
print(a, b, c)   # 1 2 3
# print(d)       # NameError: name 'd' is not defined
# print(_internal)  # NameError
```

> **关键结论 4**：`__all__` 是模块**作者主动声明的公共 API 清单**；不写也可以，但下划线开头的名字默认不会被 `import *` 导入（weak internal use 惯例）。

---

## 5. 元数据与命名惯例：`__version__`、`__author__` 与 PEP 8

模块级元数据（metadata）不是语言强制的，但社区很常见：

```python
"""This module does stuff."""

__all__     = ["a", "b", "c"]
__version__ = "0.1"
__author__  = "Cardinal Biggles"
```

PEP 8 给出的命名风格建议（新模块、新包应遵守）：

- **模块名**：短小的 `lowercase`，必要时可用 `lower_case_with_underscores`；包名同样小写，但**不建议下划线**。
- **类名**：`CapWords`（又名 CamelCase），例如 `HTTPServerError`（缩写全大写，比 `HttpServerError` 更规范）。
- **常量**：`UPPER_CASE_WITH_UNDERSCORES`。
- **单下划线前缀** `_name`：弱“内部使用”标记，`from M import *` 不会导入。
- **双下划线前后** `__name__`：属于“魔术”（magic）dunder，**只能按文档使用，绝不要自造**。
- **避免**单字符 `l`、`O`、`I`：与数字 `1`、`0` 视觉混淆。

```python
# 命名示例
MAX_RETRY = 3              # 常量
class HTTPServerError(Exception): ...   # CapWords, 缩写大写

def _parse_raw(text):      # 内部函数
    return text.strip()
```

> **关键结论 5**：`__init__`、`__file__`、`__all__` 等 dunder 是解释器/社区的约定，**不要在业务代码里自造新的 dunder 名称**，否则会和未来 Python 版本或工具冲突。

---

## 6. 进阶：`TYPE_CHECKING` 与延迟导入

有时为了类型注解（type annotation），需要引入一个代价很高的模块，但运行时又不需要它。`typing.TYPE_CHECKING` 在运行时为 `False`，但静态类型检查器（如 mypy、pyright）会把它当作 `True`：

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import expensive_mod   # 运行时不会真的导入

def fun(arg: "expensive_mod.SomeType") -> None:  # 用字符串注解避免运行时求值
    ...
```

> **关键结论 6**：`TYPE_CHECKING` 让你在享受类型检查的同时，避免模块初始化阶段付出昂贵的导入代价。

---

## 结尾：动手练习

**任务：写一个“可当模块、可当脚本”的统计工具 `stats.py`。**

要求：

1. 模块开头写多行 docstring，说明用途。
2. 声明 `__all__ = ["mean", "median"]`、`__version__`、`__author__`。
3. 实现 `mean(xs)` 与 `median(xs)` 两个函数，各写单行 docstring。
4. 在 `if __name__ == "__main__":` 分支里读取命令行数字并打印 `mean` 与 `median`。
5. 另写一个 `main.py`，`from stats import *`，调用 `mean` 并验证 `median` 也可用；再加一个内部辅助函数 `_helper`，验证 `from stats import *` **不会**导入它。

运行：

```bash
python stats.py 1 2 3 4
# mean=2.5 median=2.5

python main.py
```

完成后，你应该能直观体会“模块初始化”“`__all__`”“dunder 元数据”“`__main__` 惯用法”在一次导入里各自扮演什么角色。


---

## 本课题目

### single_choice · None



- [A] 先执行 utils.py，再执行 __init__.py
- [B] 先定位 mypkg 并执行 __init__.py，再定位 utils 并执行它
- [C] 由于 utils.py 不是包的一部分，会报 ModuleNotFoundError
- [D] 只执行 utils.py，__init__.py 仅在语句为 `from mypkg import utils` 时才执行

**参考答案**：1

**解析**：import mypkg.utils 会依次导入 mypkg 和 mypkg.utils，因此会先执行 mypkg/__init__.py，再执行 utils.py。

### single_choice · None



- [A] importlib.reload 每次执行都会打印，因此不能只打印一次
- [B] `import helper` 会在每次执行导入语句时都重新执行 helper.py
- [C] `import helper` 只在第一次导入时执行 helper.py；之后同进程再次 import 会复用已缓存的模块
- [D] `import helper` 不执行文件，只是声明一个名称

**参考答案**：2

**解析**：模块在第一次导入时执行并缓存到 sys.modules，后续 import 只取缓存，不会重复执行。

### single_choice · None



- [A] 使用 importlib.reload 重新加载同一模块
- [B] 在多个文件中通过 import 导入同一个模块
- [C] 在同一个文件中多次书写 import 同一模块
- [D] 在函数内部导入模块

**参考答案**：0

**解析**：importlib.reload 会重新执行模块顶层代码；普通重复 import 不会重复执行。

### single_choice · None



- [A] 该判断用于区分模块是被直接运行还是被其他模块导入，从而决定是否执行测试或启动逻辑
- [B] 该判断用于判断当前文件是否是可执行文件
- [C] 该判断用于创建包结构，缺少它就无法导入模块
- [D] 该判断只在 __init__.py 中有效

**参考答案**：0

**解析**：__name__ 在被直接运行时为 '__main__'，被导入时为模块名，因此常用于放置仅在直接运行时执行的代码。

### single_choice · None



- [A] students.py 必须作为包 school 的一部分被导入，而不是作为顶层脚本直接执行
- [B] helper 必须位于 Python 安装目录
- [C] students.py 必须包含 __main__ 判断
- [D] helper 必须是第三方库

**参考答案**：0

**解析**：相对导入需要当前模块有包上下文；若 students.py 被直接当作脚本运行，则相对导入会失败。

### single_choice · None



- [A] 会一次性把 a、a.b、a.b.c 全部导入并执行各自包/模块的初始化代码
- [B] 只执行 a.b.c，不执行 a 和 a.b
- [C] 只把 c 绑定到当前命名空间
- [D] 会报错，因为不能导入多级子模块

**参考答案**：0

**解析**：导入多级模块时，父包会被依次导入并执行其初始化代码，最终 a.b.c 被绑定为 a.b.c 模块对象。

### single_choice · None



- [A] sys.path
- [B] path.sys
- [C] sys().path
- [D] import sys.path

**参考答案**：0

**解析**：sys 是模块对象，sys.path 是其属性；其他写法不成立。

### single_choice · None



- [A] 在模块中定义 __all__，显式列出可导出的名称；导入方使用 from module import 名称
- [B] 把模块改名为包并删除所有函数
- [C] 在模块内部使用 global 声明所有变量
- [D] 在每个使用处都使用 import *

**参考答案**：0

**解析**：__all__ 可控制 from module import * 的导出列表，但更推荐显式导入具体名称。

### single_choice · None



- [A] 它必须显式创建 __init__.py 才能工作
- [B] 它允许将同一个包的多个部分分布在不同目录或路径中，而不需要 __init__.py
- [C] 它是用来存放全局变量的特殊字典
- [D] 它只能在 Windows 上使用

**参考答案**：1

**解析**：命名空间包可以没有 __init__.py，并可由多个路径片段共同组成同一包。

### single_choice · None



- [A] 任何 .py 文件既可以作为模块被导入，也可以作为脚本直接运行
- [B] 只有包中的 __init__.py 才能作为脚本运行
- [C] 模块不能包含顶层可执行语句
- [D] 脚本必须放在 site-packages 目录下

**参考答案**：0

**解析**：Python 源文件既可被导入为模块，也可直接运行；是否运行顶层逻辑可用 __name__ 判断来控制。

### single_choice · None



- [A] dir(module)
- [B] help.path(module)
- [C] module().dir()
- [D] import dir.module

**参考答案**：0

**解析**：内置函数 dir() 返回对象的属性名列表，可用于查看模块公开属性。

### single_choice · None



- [A] 会导入 a.b，并把顶层名称 ab 绑定到 a.b 模块对象
- [B] 只导入 a，并把 a 重命名为 ab
- [C] 导入后可以使用 ab.b 访问 b 子模块
- [D] 该语法不合法，as 只能用于 from import

**参考答案**：0

**解析**：import ... as ... 会把指定模块（此处为 a.b）绑定到别名 ab。

### single_choice · None



- [A] 输出 3.141592653589793，因为 math 是标准库模块
- [B] 报 NameError，因为 pi 没有定义在当前命名空间
- [C] 报 ImportError，因为 pi 不是模块级属性
- [D] 报 AttributeError，因为 pi 不属于 math

**参考答案**：0

**解析**：引入模块后通过模块名.属性访问，可以取得 math.pi；这不会污染当前命名空间。

### single_choice · None



- [A] 总是导入包，因为包优先于模块
- [B] 总是导入 foo.py，因为文件优先于目录
- [C] 取决于 import 顺序与路径查找，可能按 package 或 module 之一被解析，行为容易混淆
- [D] 两者都会合并为一个模块

**参考答案**：2

**解析**：同名模块与包在同一路径下会产生命名冲突；实际解析取决于多种因素，应避免这种命名。

### single_choice · None



- [A] 任何以 .py 结尾的文件都称为包
- [B] 包含 __init__.py 的目录（常规包）或具有命名空间包结构，用于组织多个模块
- [C] 只能通过 pip 安装到 site-packages 的第三方库
- [D] 一个带有 main 函数的可执行文件

**参考答案**：1

**解析**：包用于组织模块；常规包通常包含 __init__.py，此外还存在命名空间包。

### single_choice · None



- [A] 报 NameError，因为 dumps 未导入
- [B] 输出 {"a": 1}
- [C] 输出 {'a': 1}
- [D] 报 AttributeError，因为 json 模块没有 dumps

**参考答案**：1

**解析**：导入 json 后，通过 json.dumps 调用，得到合法 JSON 字符串 {"a": 1}。

### single_choice · None



- [A] 该语句把 sqrt 名称引入当前命名空间，之后可直接使用 sqrt(4)
- [B] 该语句等价于 import math.sqrt
- [C] 该语句必须后接 as 重命名，否则语法错误
- [D] 该语句会导入整个 math 模块，但 sqrt 不能独立使用

**参考答案**：0

**解析**：from ... import ... 将指定名称绑定到当前命名空间，因此可以直接调用 sqrt。

### single_choice · None



- [A] a.x 变为 2，因为导入的是同一个对象
- [B] a.x 仍为 1，因为 x = 2 只是将 b 模块中的名称 x 重新绑定
- [C] 导入会失败，因为 x 不可修改
- [D] a.x 变为 None

**参考答案**：1

**解析**：from a import x 只是把对象绑定到 b 的命名空间；再赋值 x = 2 只改变 b 的绑定，不影响 a.x。

### single_choice · None



- [A] import module.MyClass
  module.MyClass()
- [B] from module import MyClass
  MyClass()
- [C] import MyClass from module
  MyClass()
- [D] include module
  module.MyClass()

**参考答案**：1

**解析**：from module import MyClass 后可直接通过 MyClass() 使用。其他写法不符合 Python 语法。

### single_choice · None



- [A] 导入父目录下的 sub 模块并暴露 func
- [B] 使用相对导入，从当前包内导入 sub 中的 func，使包级命名空间可直接访问 func
- [C] 绝对导入，等价于 from sub import func
- [D] 会报 ImportError，因为相对导入不能用于包的 __init__.py

**参考答案**：1

**解析**：. 表示当前包，相对导入从当前包内的 sub 模块导入 func。

### single_choice · None



- [A] 它只在模块被其他模块导入时执行
- [B] 它只在模块作为主程序直接运行时执行
- [C] 无论导入还是直接运行都会执行
- [D] 它等价于定义了一个名为 __main__ 的函数

**参考答案**：1

**解析**：当模块被直接运行时，其 __name__ 被设为 "__main__"，条件成立；被导入时 __name__ 为模块名，条件不成立。它并不是函数定义，只是一条判断语句。

### single_choice · None



- [A] __main__
- [B] A
- [C] A.py
- [D] 什么都不输出

**参考答案**：1

**解析**：被导入时模块的 __name__ 是该模块的名字（去掉 .py 后缀），即 "A"；只有直接运行才会是 "__main__"。

### multi_choice · None



- [A] 比较的是字符串 "__main__"
- [B] 使用 == 而不是 is 更稳妥
- [C] 该条件在该模块被导入时为 False
- [D] 该条件在该模块被直接运行时为 True

**参考答案**：[0, 1, 2, 3]

**解析**：这里比较的是字符串内容（应使用 ==，避免依赖对象身份）；导入时为 False，直接运行时为 True。四项均正确。

### fill_blank · None



**参考答案**：["__main__", "__main__ "]

**解析**：直接运行时模块的 __name__ 为字符串 "__main__"，因此填空处应为 __main__。

### fill_blank · None



**参考答案**：["名字", "名称", "模块名"]

**解析**：被导入时 __name__ 是模块的名字（字符串），如导入 utils 则为 "utils"。

### fill_blank · None



**参考答案**：["守卫", "保护", "guard"]

**解析**：入口守卫（main guard）用于保护主流程代码，使其仅在直接运行时执行。

### code_reading · None



**参考答案**：先输出 top level，再输出 in bar

**解析**：顶层 print 总会执行；由于直接运行且 __name__ 为 "__main__"，守卫块内的 bar() 也被调用，因此顺序是 top level、in bar。

### code_reading · None



**参考答案**：只输出 top level

**解析**：导入时 __name__ 为 "foo"，守卫条件为 False，bar() 不执行；但顶层 print 依然执行，所以只输出 top level。

### code_reading · None



**参考答案**：a imported as a

**解析**：main.py 被直接运行，其 __name__ 为 "__main__"，但它没有打印语句；导入 a 时 a 的 __name__ 为 "a"，故输出 "a imported as a"。

### scenario · None



**解析**：问题在于测试代码写在模块顶层，导入时会被执行。应把测试/主流程代码放入 if __name__ == "__main__": 守卫块中，这样导入时不会执行，而直接运行 tools.py 时仍会执行。

### scenario · None



**解析**：顶层代码在导入时就会执行，input() 会阻塞等待输入，导致测试卡住。应把这部分交互逻辑移到 if __name__ == "__main__": 守卫块内，避免导入时执行。

### single_choice · None



- [A] 每个模块都有一个 __name__ 属性
- [B] __name__ 的值取决于该模块是如何被使用的
- [C] 直接运行脚本时 __name__ 的值为 "__main__"
- [D] __name__ 必须由程序员手动赋值，否则会报 NameError

**参考答案**：3

**解析**：__name__ 由解释器自动设置，无需手动赋值。A、B、C 都是正确的描述。

### single_choice · None



- [A] A.greet()
- [B] greet() 直接调用即可
- [C] import A 之后调用 A.greet()
- [D] import greet

**参考答案**：2

**解析**：要先 import A，然后通过 A.greet() 访问（选项 A 缺少导入，B 缺少命名空间前缀，D 导入的是不存在的模块名）。

### single_choice · None



- [A] 什么都不输出
- [B] 输出 hello
- [C] 报 ImportError
- [D] 输出 utils

**参考答案**：1

**解析**：没有守卫时，模块顶层代码在导入期间会被执行，因此会打印 hello。守卫的作用正是避免导入时执行测试/主程序代码。

### single_choice · None



- [A] 不执行
- [B] 执行，因为 __name__ 此时是 "__main__"
- [C] 执行，因为 __name__ 此时是 "m"
- [D] 取决于是否安装了 m 包

**参考答案**：1

**解析**：直接以脚本方式运行时，__name__ 被设为 "__main__"，条件成立，分支代码执行。

### multi_choice · None



- [A] 模块顶层代码在导入时会执行
- [B] if __name__ == "__main__": 内的代码在导入时不会执行
- [C] 把测试代码放进入口守卫中，可以避免导入时被意外运行
- [D] 入口守卫会把模块名改成 __main__

**参考答案**：[0, 1, 2]

**解析**：顶层代码导入即执行；守卫块只在此模块作为主程序运行时才执行，所以适合放测试/主流程；但它并不会改变模块名，__name__ 的值是解释器设定的。

### multi_choice · None



- [A] 把可复用的函数/类定义在模块顶层
- [B] 把仅用于直接运行的主流程放进 if __name__ == "__main__": 中
- [C] 在被导入的模块顶层直接调用 sys.exit()
- [D] 在守卫块中调用 main() 函数

**参考答案**：[0, 1, 3]

**解析**：顶层定义可复用内容、守卫块承载主流程（常调用 main()）是推荐模式；在被导入模块顶层调用 sys.exit() 会在导入时就终止程序，属于错误做法。

### multi_choice · None



- [A] 作为包被导入的子模块，其 __name__ 含包名前缀（如 pkg.mod）
- [B] 直接运行某文件时，其 __name__ 为 "__main__"
- [C] __name__ 是字符串类型
- [D] __name__ 在交互式解释器中不存在

**参考答案**：[0, 1, 2]

**解析**：包内子模块的 __name__ 是带点号的完整名；直接运行的文件为 "__main__"；它是 str。交互式解释器中 __name__ 也存在（值为 "__main__"），故 D 错误。

### multi_choice · None



- [A] 把大量测试打印写在模块顶层
- [B] 把主流程写在 if __name__ == "__main__": 之外
- [C] 在模块顶层直接调用 input() 等待用户输入
- [D] 把可复用函数写在模块顶层

**参考答案**：[0, 1, 2]

**解析**：顶层代码在导入时都会执行，因此顶层打印、顶层主流程、顶层 input() 都会在导入时被触发；而在顶层定义函数只是绑定名字，不会执行函数体，是安全的。
