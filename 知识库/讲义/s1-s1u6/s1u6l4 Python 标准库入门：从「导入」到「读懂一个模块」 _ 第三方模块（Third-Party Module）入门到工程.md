# s1u6l4 Python 标准库入门：从「导入」到「读懂一个模块」 / 第三方模块（Third-Party Module）入门到工程实践

> 来源 `content/lessons/s1u6l4.json`

## py.module.stdlib_intro

# Python 标准库入门：从「导入」到「读懂一个模块」

> 一句话直觉：你写 Python 时 90% 的时间不是发明新东西，而是学会「站在标准库（Standard Library）的肩膀上」——它是 Python 自带的一整箱现成工具，学它就像学用手机自带的 App，而不是每次都自己造。

本讲义假设你**没有任何** Python 导入与模块的背景知识，从零建立三个核心能力：

1. 知道 `import` 到底做了什么；
2. 会读一个标准库模块的「门面」（`__all__`、`__version__`、docstring 等）；
3. 能区分「运行时真的导入」和「只给类型检查器看的导入」。

—— 40 分钟，走完这三步，你就拥有阅读任何标准库模块最基础的「读心术」。

---

## 1. 什么是「模块」与「标准库」

**模块（module）**：一个 `.py` 文件，里面装着一堆变量、函数、类，可以被别的程序「导入」使用。
**标准库（standard library）**：Python 官方随解释器一起发布的模块集合，不需要 `pip install` 就能用，比如 `math`、`os`、`json`、`typing`。

`import` 发生时，Python 会：

1. 找到对应的 `.py` 文件或内建模块；
2. **执行**该文件里的顶层代码（所以模块顶层不要写耗时操作）；
3. 把结果放进 `sys.modules` 缓存，后续 `import` 直接复用。

```python
import sys
import math

# 模块被缓存到 sys.modules 里，第二次 import 不会再执行一次
print("math" in sys.modules)        # True
print(math.sqrt(16))                # 4.0

# 模块对象也是一个「普通对象」，它的属性就是里面定义的名字
print(math.pi)
```

> 结论：**导入 = 执行一次 + 缓存**。理解这一点，后面所有「懒导入」、「只在类型检查时导入」才有意义。

---

## 2. 一个模块的「门面」：docstring、`__all__`、`__version__`

打开任何一个标准库源文件，最上面常常看到这样的结构（这是官方推荐的写法）：

```python
"""This module does stuff."""

__all__ = ['a', 'b', 'c']
__version__ = '0.1'
__author__ = 'Cardinal Biggles'
```

逐个解释：

- **docstring**：模块最顶部的字符串，用 `help(模块)` 或 `模块.__doc__` 读到。
- **`__all__`**：一个字符串列表，告诉 `from m import *` 应该导出哪些名字。**没有 `__all__`** 时，`import *` 会导出所有不以 `_` 开头的名字。
- **`__version__` / `__author__`**：社区约定俗成的元数据，方便使用者了解版本和作者。

```python
# 假设模块 my_mod.py 内容为：
# """Demo module."""
# __all__ = ['a']
# a = 1
# b = 2
# _c = 3

from my_mod import *
print(a)     # 1
# print(b)   # NameError：b 不在 __all__ 中，不会被 * 导入
# print(_c)  # NameError：下划线开头的名字默认不被导出
```

> 结论：**`__all__` 是模块的公开 API 声明**。阅读陌生模块时，先看 `__all__` 和 docstring，就知道「作者想让你用什么」。

---

## 3. 命名约定：一眼看出「公开 / 内部 / 魔法」

看完门面，再看里面的名字。Python 用**下划线**来编码「可见性」：

| 写法 | 含义 |
|---|---|
| `name` | 公开 |
| `_name` | 弱内部：`from m import *` 不会导入 |
| `__name`（类属性） | 会触发名字改写（name mangling），如 `_Class__name` |
| `__name__` | 魔法（magic / dunder）名字，由 Python 自己使用 |

命名风格：

- 模块/包：`lower_case`（小写下划线）；
- 类：`CapWords`（驼峰）；
- 函数/变量：`lower_case`；
- 常量：`UPPER_CASE`；
- 类型变量：`T`、`AnyStr` 等简短 `CapWords`。

```python
class FooBar:
    def __init__(self):
        self.__boo = 1        # 实际名字变成 _FooBar__boo

fb = FooBar()
print(fb._FooBar__boo)        # 1，能读但不该读写
# print(fb.__boo)             # AttributeError
```

> 结论：**不要创造 `__xxx__` 风格的名字**，那是留给 Python 的；对内部实现，用单个下划线前缀就够。

---

## 4. 一个容易被忽略的高级技巧：`TYPE_CHECKING`

有些模块只在「类型注解」里被引用，运行时其实不需要真的导入（例如它会拉一大堆依赖、拖慢启动）。`typing.TYPE_CHECKING` 就是为这种情况准备的：

- 运行时它是 `False`；
- 静态类型检查器（mypy、pyright 等）分析时把它当作 `True`。

所以你可以在 `if TYPE_CHECKING:` 下写导入，运行时被跳过，检查器却能看到类型。

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import expensive_mod  # 只给静态分析看，运行时不真的导入

def fun(arg: "expensive_mod.SomeType") -> None:
    ...
```

注意：注解用引号包成字符串（或使用 PEP 649 的延迟求值）才安全，否则运行时求值会报 `NameError`。

> 结论：**`TYPE_CHECKING` 是「只在类型世界导入」的开关**，能显著减少重依赖模块的启动开销。

---

## 5. 一点点关于 `typing` 的现状（为什么你会在源文件里看到一堆 `typing.List`）

早期想给 `list`、`dict` 加泛型参数时只能写 `typing.List[int]`。从 Python 3.9（PEP 585）开始，内建容器自己就支持 `list[int]`、`dict[str, int]`，于是 `typing.Dict`、`typing.List`、`typing.Set`、`typing.FrozenSet` 成为**已弃用别名（deprecated alias）**——仍能用，但新代码推荐直接写内建类型，或在需要抽象时用 `collections.abc.Mapping` / `Sequence`。

```python
# 旧写法（仍可用，但不推荐）
from typing import List, Dict

def f1(x: List[int]) -> Dict[str, int]: ...

# 新写法（Python 3.9+）
def f2(x: list[int]) -> dict[str, int]: ...

# 更抽象、更推荐（接受任何映射/序列）
from collections.abc import Mapping, Sequence

def f3(x: Sequence[int]) -> Mapping[str, int]: ...
```

> 结论：**看到 `typing.List` 不要慌，那只是历史遗产**；新代码优先用 `list[int]` 或 `collections.abc` 里的抽象类型。

```python
"""演示：读一个模块的门面 + `__all__` + `TYPE_CHECKING`。
运行：python example.py
"""

# ---------- 第一步：看门面 ----------
import json

print("json.__doc__ 开头:", (json.__doc__ or "").strip().splitlines()[0])
print("json.__all__ 前 5 个:", json.__all__[:5])

# ---------- 第二步：__all__ 控制 import * ----------
# 用一个临时模块演示
import textwrap, sys, types

mod_src = textwrap.dedent('''
    """Demo module."""
    __all__ = ["a"]
    a = 1
    b = 2
    _c = 3
''')
mod = types.ModuleType("demo_mod")
exec(mod_src, mod.__dict__)
sys.modules["demo_mod"] = mod

ns = {}
exec("from demo_mod import *", ns)
print("通过 * 拿到的名字:", [k for k in ns if not k.startswith('__')])

# ---------- 第三步：TYPE_CHECKING ----------
from typing import TYPE_CHECKING

print("运行时 TYPE_CHECKING =", TYPE_CHECKING)  # False

if TYPE_CHECKING:
    import decimal  # 只在类型检查器眼里存在

def price(x: "decimal.Decimal") -> str:
    # 注意：注解是字符串，运行时不会真的去找 decimal
    return f"{x:.2f}"

print("price(3.14159):", price(3.14159))
```

## py.module.third_party

# 第三方模块（Third-Party Module）入门到工程实践

> 一句话直觉：标准库只是 Python 自带的口袋工具，而第三方模块（third-party module）是全世界的开发者已经造好的「零件库」—— 学会找到、安装、使用并管理它们，是你从「会写 Python」迈向「能用 Python 造东西」的关键一步。

---

## 一、什么是第三方模块，为什么必须学它

Python 的代码组织单元从大到小依次是：包（package）→ 模块（module）→ 函数/类。

- **标准库（standard library）**：Python 官方随解释器一起发布的模块，例如 `os`、`json`、`typing`。安装 Python 就有了。
- **第三方模块（third-party module）**：由社区、公司或个人发布，需要**额外安装**才能使用的模块，例如 `requests`、`numpy`、`pandas`、`flask`。
- **本地模块（local module）**：你自己项目里写的 `.py` 文件。

为什么必须学？因为你 90% 的实际项目都不会从零造轮子：发 HTTP 请求用 `requests`，处理表格用 `pandas`，做深度学习用 `torch`。**你的生产力 = 标准库 + 第三方模块 + 少量自研代码**。

---

## 二、认识一个模块：`__name__`、`__all__`、`__version__`

一个写好的模块，通常会在文件开头声明一些「元信息（metadata）」，让使用者知道它是谁、怎么用。

```python
# mymodule.py
"""This module does stuff.

Optional plotz says to frobnicate the bizbaz first.
"""

__all__ = ['a', 'b', 'c']        # 声明 from mymodule import * 时导出哪些名字
__version__ = '0.1'              # 版本号，方便排查兼容问题
__author__ = 'Cardinal Biggles'  # 作者信息

a, b, c = 1, 2, 3
d = 999  # 不出现在 __all__ 里，不会被打包导出
```

记住两条工程习惯：

- `__all__` 决定 `from mod import *` 时暴露的公共接口（public API）。
- `__version__` 让使用者能判断自己用的是哪个版本，出问题时能定位。

---

## 三、安装第三方模块：pip 与虚拟环境（virtual environment）

第三方模块的生态中枢是 **PyPI（Python Package Index，Python 包索引）**。安装工具是 `pip`。

最小可用流程（命令行执行）：

```bash
python -m venv .venv              # 为当前项目创建独立虚拟环境
source .venv/bin/activate         # macOS/Linux 激活
# .venv\Scripts\activate          # Windows 激活
python -m pip install requests    # 安装第三方模块
python -m pip freeze > requirements.txt  # 冻结依赖清单
```

为什么必须用虚拟环境？因为不同项目可能依赖同一个库的不同版本，全局安装会互相污染。虚拟环境让**每个项目有自己独立的依赖（dependency）**。

---

## 四、使用第三方模块：import 的三种姿势与命名空间

导入模块时，命名空间（namespace）的写法决定代码是否可读：

```python
import requests                       # 推荐：前缀清晰
import numpy as np                    # 约定俗成的别名
from collections import OrderedDict    # 只取一个名字
```

工程建议：

- 优先 `import x` 或 `import x as y`，避免 `from x import *`，否则命名空间被污染，很难看出名字来自哪个模块。
- 别名要遵循社区惯例（`numpy as np`、`pandas as pd`、`matplotlib.pyplot as plt`），别人才能秒懂。
- 模块名本身遵守社区命名约定：**包和模块短小写，类名 CapWords，常量 UPPER_CASE**。

---

## 五、工程级技巧：延迟导入与 `typing.TYPE_CHECKING`

大型项目中，有些模块导入成本很高（例如加载 C 扩展），但只用来做**类型注解（type annotation）**。这时可以用 `TYPE_CHECKING`：静态检查器认为它是 `True`，运行时是 `False`，从而**避免运行时真正导入**。

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import expensive_mod  # 静态分析时会导入；运行时不会

def fun(arg: "expensive_mod.SomeType") -> None:
    ...
```

这是一个把「类型安全」和「启动速度」同时兼顾的模式，是资深工程师常用技巧。

---

## 小结

1. 第三方模块 = 别人写好、发布到 PyPI、你通过 pip 安装后即可使用的模块。
2. 元信息 `__all__ / __version__ / __author__` 是一个模块对外的「名片」。
3. 使用虚拟环境隔离依赖，用 `requirements.txt` 复现环境。
4. 导入要用清晰命名空间；只做类型注解的重型模块可用 `TYPE_CHECKING` 延迟导入。

下次遇到「这个功能好像应该有人写过」，先想到 PyPI，再想到虚拟环境，再想到 `import`。


---

## 本课题目

### single_choice · None



- [A] 标准库是随 Python 解释器一起安装、无需额外下载即可导入使用的模块集合
- [B] 标准库是需要通过 pip 单独安装后才能使用的第三方模块集合
- [C] 标准库只包含用 C 语言实现的底层模块，不包含纯 Python 模块
- [D] 标准库中的所有模块在任何平台上都必须显式 import 才能生效，且无法禁用

**参考答案**：0

**解析**：Python 标准库随解释器一同分发，属于安装即得的模块集合，因此选项 A 正确。选项 B 描述的是第三方包的分发方式；选项 C 忽略了标准库中大量纯 Python 模块；选项 D 的『无法禁用』说法错误，且并非所有模块都需要显式导入才『生效』（如 builtins 已默认加载）。

### single_choice · None



- [A] 输出 4.0，因为 math 是标准库模块，可直接导入
- [B] 报错 ModuleNotFoundError，因为 math 需要先 pip install
- [C] 输出 4，因为 sqrt 返回整数
- [D] 报错 SyntaxError，因为 import 不能单独成行

**参考答案**：0

**解析**：math 是 Python 标准库模块，无需安装即可 import，sqrt(16) 返回浮点数 4.0，因此 A 正确。B 把第三方安装流程误用到标准库；C 错在 sqrt 返回 float；D 错在 import 语句完全合法。

### single_choice · None



- [A] json.dumps 把 Python 对象序列化为 JSON 字符串，json.loads 把 JSON 字符串解析为 Python 对象
- [B] json.dumps 把 Python 对象直接写入文件，json.loads 从文件读取
- [C] json.dumps 只能处理字符串，json.loads 只能处理数字
- [D] json.dumps 与 json.loads 分别是第三方库的方法，标准库中不存在

**参考答案**：0

**解析**：json.dumps/loads 分别负责序列化到字符串与从字符串反序列化，A 正确。B 描述的是 json.dump/load（操作文件）而非 dumps/loads；C 错误地限制了数据类型；D 错在 json 是标准库模块。

### single_choice · None



- [A] 让代码块只在文件被直接运行时执行，被当作模块导入时不执行
- [B] 让代码块只在文件被导入时执行
- [C] 让代码块被自动执行两次
- [D] 判断当前文件是否是标准库模块

**参考答案**：0

**解析**：当文件被直接运行时 __name__ 为 '__main__'，被导入时则等于模块名，因此该判断用于区分直接运行与导入，A 正确。B 与事实相反；C 无依据；D 混淆了 __name__ 的含义。

### single_choice · None



- [A] argparse
- [B] click
- [C] requests
- [D] pandas

**参考答案**：0

**解析**：argparse 是标准库中处理命令行参数的模块，A 正确。click 是第三方命令行库；requests 用于 HTTP；pandas 用于数据分析，三者都需要额外安装。

### single_choice · None



- [A] 内置函数如 len、print 无需 import 即可直接使用；标准库模块通常需要 import
- [B] 内置函数如 len、print 需要先 import builtins 才能使用
- [C] 标准库模块中的函数也全部无需 import 即可使用
- [D] 内置函数和标准库模块是同一概念，没有任何区别

**参考答案**：0

**解析**：内置函数来自 builtins 命名空间，默认可用；标准库模块需要显式 import，因此 A 正确。B 错在默认已可用；C 忽略了需要导入这一事实；D 混淆了两个概念。

### single_choice · None



- [A] 输出 a.txt
- [B] 报错，因为 os.path 不能单独 import
- [C] 输出 /tmp/a.txt
- [D] 输出 tmp/a.txt

**参考答案**：0

**解析**：os.path 是真实存在的子模块，可以单独导入，basename 返回路径最后一部分 a.txt，因此 A 正确。B 与事实相反；C、D 混淆了 basename 与 dirname 或其它函数的行为。

### single_choice · None



- [A] 不同 Python 版本的标准库可能有增减或行为变化，写代码时应查阅对应版本文档
- [B] 标准库在所有 Python 版本中完全一致，永远不会变化
- [C] 标准库只在主版本号变化时才更新，次版本号变化时不会更新
- [D] 标准库一旦发布就冻结，新增功能只能通过第三方库实现

**参考答案**：0

**解析**：标准库会随 Python 版本演进，存在新增、弃用与行为调整，因此需查阅对应版本文档，A 正确。B、D 与事实相反；C 忽略了次版本中也可能有标准库变化。

### single_choice · None



- [A] 它会导入 math 中所有不以单下划线开头的公开名称，可能污染命名空间，通常不推荐在大型代码中使用
- [B] 它会导入 math 模块对象本身，并绑定为 *
- [C] 它会导入 math 中所有名称，包括以下划线开头的私有名称
- [D] 它会报 SyntaxError，因为标准库模块不允许使用 * 导入

**参考答案**：0

**解析**：通配符导入会引入公开名称，容易造成命名冲突，因此通常不推荐，A 正确。B 完全误解语法；C 忽略了 __all__ 与下划线约定；D 与事实相反，语法是合法的。

### single_choice · None



- [A] 无需安装即可使用 re 做正则匹配、使用 datetime 处理日期时间、使用 collections 提供额外容器类型
- [B] 必须安装后才可使用 re、datetime、collections
- [C] 标准库只能处理文本，无法处理日期时间和容器类型
- [D] 标准库只提供数学计算能力，其它能力均需第三方库

**参考答案**：0

**解析**：re、datetime、collections 均为标准库模块，覆盖文本、时间与容器等常见需求，A 正确。B 错在需要安装；C、D 都严重低估了标准库范围。

### single_choice · None



- [A] winreg 是平台相关的标准库模块，只在 Windows 上可用
- [B] winreg 是第三方库，在 Linux 上未安装
- [C] winreg 是标准库模块，Linux 上报错说明 Python 安装损坏
- [D] winreg 是标准库模块，需要先 import os 才能加载

**参考答案**：0

**解析**：标准库中部分模块具有平台相关性，winreg 仅 Windows 提供，因此 A 正确。B 忽略了它属于标准库但平台受限；C、D 都是对标准库平台差异的常见误解。

### single_choice · None



- [A] 标准库不需要在依赖清单中声明，第三方库通常需要记录在 requirements.txt 或类似清单中
- [B] 标准库与第三方库都必须在 requirements.txt 中声明
- [C] 标准库必须声明，第三方库因为是全局安装所以不需要声明
- [D] 两者都不需要声明，Python 会自动处理所有依赖

**参考答案**：0

**解析**：标准库随解释器提供，不进入第三方依赖清单；第三方库通常需要显式记录以便复现环境，因此 A 正确。B、C 混淆了两类库的管理方式；D 忽略了依赖管理的必要性。

### single_choice · None



- [A] 前者把 os 模块对象绑定到当前命名空间的 os 名称；后者只把 os.path 子模块绑定到 path 名称
- [B] 两者完全等价，都会把 os 下所有名称导入当前命名空间
- [C] 前者会执行 os 模块代码两次，后者只执行一次
- [D] 后者会报错，因为 os.path 不是模块

**参考答案**：0

**解析**：import os 绑定模块名 os；from os import path 只引入 os.path 子模块并绑定为 path，因此 A 正确。B 误以为 from ... import * 才是等价；C 错在模块只会执行一次；D 错在 os.path 是真实存在的子模块。

### single_choice · None



- [A] os
- [B] sys
- [C] math
- [D] json

**参考答案**：0

**解析**：os 模块提供 os.getcwd() 等与操作系统交互的能力，因此 A 正确。sys 主要用于解释器相关信息与运行时参数；math 提供数学函数；json 处理 JSON 序列化，均不直接提供获取当前工作目录的常用接口。

### single_choice · None



- [A] requests 不是 Python 标准库模块，需要先安装才能使用
- [B] requests 是标准库模块，报错说明 Python 安装损坏
- [C] requests 是标准库模块，但必须先 import json 才能加载
- [D] requests 是标准库模块，报错说明代码中拼写错误，应该是 request

**参考答案**：0

**解析**：requests 是流行的第三方 HTTP 库，不属于标准库，因此需要 pip 安装后使用，A 正确。B、C、D 都错误地把 requests 当作标准库，属于常见误解。

### single_choice · None



- [A] 同一个模块在一次程序运行中即使被多次 import，也只会执行一次模块顶层代码
- [B] 每次 import 同一个模块都会重新执行一遍模块顶层代码
- [C] 标准库模块无法被重复导入，第二次 import 会抛异常
- [D] 只有使用 importlib.reload 才能让模块顶层代码首次执行

**参考答案**：0

**解析**：Python 的导入系统会缓存已导入模块，后续 import 直接复用缓存，因此顶层代码只执行一次，A 正确。B 与缓存机制矛盾；C 与事实相反；D 混淆了 reload 的用途，reload 是重新执行已加载模块，而不是首次执行。

### single_choice · None



- [A] 1
- [B] 0
- [C] 每次运行结果不同
- [D] 报错，因为 randint 的上下界不能相同

**参考答案**：0

**解析**：random.randint(a, b) 在闭区间内返回整数，当 a=b=1 时必然返回 1，因此 A 正确。B 把下界误当结果；C 忽略了参数使取值唯一；D 错在 randint 允许区间退化为单点。

### single_choice · None



- [A] import statistics; print(statistics.mean([1, 2, 3]))
- [B] import numpy; print(numpy.mean([1, 2, 3]))
- [C] import pandas; print(pandas.Series([1, 2, 3]).mean())
- [D] import flask; print(flask.__version__)

**参考答案**：0

**解析**：statistics 是标准库模块，导入即可用，符合开箱即用，A 正确。numpy、pandas、flask 都是第三方库，必须先安装，因此 B、C、D 不符合题意。

### single_choice · None



- [A] import 模块时，Python 会按 sys.path 中的顺序查找模块文件
- [B] import 模块时，Python 只在当前工作目录查找，找不到就报错
- [C] import 模块时，Python 会先在网络上搜索，再查本地
- [D] import 模块时，Python 会从标准库目录开始查找，并忽略 sys.path

**参考答案**：0

**解析**：sys.path 是一个路径列表，导入系统会按顺序在其中查找模块，因此 A 正确。B 忽略了标准库与 site-packages 等路径；C 与事实相反；D 忽略了 sys.path 的作用，标准库目录通常也在其中。

### single_choice · None



- [A] <class 'list'>
- [B] <class 'str'>
- [C] <class 'tuple'>
- [D] <class 'dict'>

**参考答案**：0

**解析**：sys.argv 是命令行参数列表，类型为 list，因此 A 正确。B 是单个参数的类型；C 常见误解为元组；D 与事实不符。

### single_choice · None



- [A] 第三方库必须放在标准库目录下才能被 import
- [B] 第三方库不是 Python 语言自带的，需通过包管理工具安装后使用
- [C] 第三方库只能用 C 语言编写
- [D] 第三方库无法通过 import 语句引入

**参考答案**：1

**解析**：第三方库是由社区或组织开发、独立于 Python 标准库分发的库，通常需要先安装（如用 pip）再通过 import 使用，并非放在标准库目录下，也不限于 C 语言编写。

### single_choice · None



- [A] requests 是标准库，不需要安装，写法有误
- [B] 安装到了另一个 Python 环境，而当前运行环境未安装
- [C] import 语句必须放在文件最后一行
- [D] requests 只能通过 from requests import * 引入

**参考答案**：1

**解析**：最常见的坑是 pip 安装的 Python 环境与运行脚本的环境不是同一个（如系统 Python 与虚拟环境），导致当前环境缺失该包。

### single_choice · None



- [A] 所有第三方库都可随意用于闭源商业项目
- [B] 使用第三方库应关注其许可证条款，并遵守相应要求
- [C] 第三方库没有许可证
- [D] 只要安装了就自动取得版权

**参考答案**：1

**解析**：不同第三方库使用不同开源或商业许可证，使用前应了解并遵守其条款（如署名、开源传染等）。

### multi_choice · None



- [A] requests
- [B] json
- [C] numpy
- [D] os

**参考答案**：[0, 2]

**解析**：requests 和 numpy 是典型的第三方库，需安装；json 和 os 属于标准库，随 Python 提供。

### multi_choice · None



- [A] 可以指定版本进行安装
- [B] 安装时可能自动安装其依赖包
- [C] 可以卸载已安装的包
- [D] pip 安装的包一定只在当前目录有效
- [E] 未安装的包在 import 时会报错

**参考答案**：[0, 1, 2, 4]

**解析**：pip 支持版本约束、自动解析依赖、卸载包；未安装的包 import 会报 ModuleNotFoundError。包安装到环境而非「只在当前目录有效」，故 D 错误。

### multi_choice · None



- [A] 隔离不同项目的依赖，避免版本冲突
- [B] 便于用 requirements.txt 复现环境
- [C] 让所有项目共享同一套包版本
- [D] 减少对系统级全局环境的污染

**参考答案**：[0, 1, 3]

**解析**：虚拟环境提供依赖隔离、环境可复现、避免污染全局环境；恰恰不是让所有项目共享同一套版本，那样反而会引发冲突。

### multi_choice · None



- [A] 在 requirements.txt 中固定版本号
- [B] 把本地虚拟环境目录提交到仓库
- [C] 记录明确的环境与依赖清单
- [D] 使用不同开发者随机升级依赖

**参考答案**：[0, 2]

**解析**：固定版本、维护依赖清单可提升可复现性；提交整个虚拟环境目录通常不推荐，随机升级依赖会破坏可复现性。

### fill_blank · None



**参考答案**：["import", "import:"]

**解析**：import 语句用于引入模块，`import requests` 即可在安装后使用该第三方库。

### fill_blank · None



**参考答案**：["freeze", "freeze --all"]

**解析**：`pip freeze` 输出当前环境中已安装的包及其精确版本，常用于生成 requirements.txt。

### code_reading · None



**参考答案**：可以。因为 math 是 Python 标准库，随解释器一起提供，无需额外安装即可 import 使用，输出 3.0。

**解析**：判断是否需要安装取决于该模块是标准库还是第三方库；math 属于标准库，因此可直接使用。

### code_reading · None



**参考答案**：不依赖。datetime 是 Python 标准库模块，可直接导入使用，因此无需安装第三方库，输出为 datetime。

**解析**：datetime 属于标准库，与第三方库无关；此题用于区分标准库与第三方库的安装需求。

### scenario · None



**解析**：典型的环境不一致问题：新成员所在环境未安装 pandas，或未激活项目对应虚拟环境。应先确认使用的 Python 环境与项目一致，再依据依赖清单安装缺失的第三方库。

### single_choice · None



- [A] pip 是 Python 标准库中的一个模块，无需安装
- [B] pip 是常用的 Python 包管理工具，用于安装、卸载和查看第三方包
- [C] pip 只能安装，不能卸载包
- [D] pip 安装的包只能被 pip 自己使用

**参考答案**：1

**解析**：pip 是 Python 的包管理工具，支持安装、卸载、升级、列出第三方包等操作，是使用第三方库的主要途径。

### single_choice · None



- [A] numpy 属于标准库，直接可运行
- [B] 需先安装第三方库 numpy，否则 import 会失败
- [C] 需把文件命名为 numpy.py
- [D] 需将 numpy 放入标准库目录

**参考答案**：1

**解析**：numpy 是第三方库，未安装时 import numpy 会抛出 ModuleNotFoundError；安装后即可正常使用。

### single_choice · None



- [A] python mytool
- [B] import mytool
- [C] 直接执行 mytool（需该脚本在 PATH 中）
- [D] python -c mytool

**参考答案**：2

**解析**：许多第三方库安装时会注册命令行脚本到可执行目录，安装后可直接在命令行调用该命令（前提是脚本目录在 PATH 中）。

### single_choice · None



- [A] 虚拟环境之间共享已安装的第三方库
- [B] 每个虚拟环境有独立的 site-packages，安装互不影响
- [C] 虚拟环境只能安装标准库
- [D] 虚拟环境不能使用 pip

**参考答案**：1

**解析**：虚拟环境的核心作用就是隔离依赖，每个虚拟环境有独立的第三方包安装目录，避免不同项目间版本冲突。

### single_choice · None



- [A] 安装 packageA 的最新版本
- [B] 安装不低于 1.2.0 的版本
- [C] 安装指定版本 1.2.0
- [D] 卸载 packageA 的 1.2.0 版本

**参考答案**：2

**解析**：`==` 是精确版本约束，会安装指定的 1.2.0 版本；`>=` 才表示不低于该版本。

### single_choice · None



- [A] pip list --outdated
- [B] pip freeze > requirements.txt
- [C] python -m venv .
- [D] pip download requirements

**参考答案**：1

**解析**：`pip freeze` 会输出当前已安装包及版本，重定向到 requirements.txt 便于他人用 `pip install -r` 复现环境。

### single_choice · None



- [A] 标准库需要额外安装，第三方库不需要
- [B] 标准库随 Python 一起提供，第三方库通常需要单独安装
- [C] 两者都必须编译，无法直接用 import
- [D] 第三方库一旦安装就无法卸载

**参考答案**：1

**解析**：标准库随 Python 解释器一同分发，开箱即用；第三方库由外部提供，通常需借助包管理工具安装，且可卸载。

### single_choice · None



- [A] 未安装该库时会打印 missing，程序可继续执行
- [B] 无论是否安装都会打印 missing
- [C] ImportError 无法被捕获
- [D] 导入失败会导致解释器崩溃

**参考答案**：0

**解析**：当第三方库缺失时，import 会抛出 ImportError（或其子类 ModuleNotFoundError），被 except 捕获后可优雅降级或提示用户安装。
