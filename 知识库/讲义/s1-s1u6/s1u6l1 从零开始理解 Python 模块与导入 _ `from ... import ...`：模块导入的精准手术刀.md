# s1u6l1 从零开始理解 Python 模块与导入 / `from ... import ...`：模块导入的精准手术刀

> 来源 `content/lessons/s1u6l1.json`

## py.module.import

# py.module.import：从零开始理解 Python 模块与导入

## 一句话直觉

你写 Python 时反复写 `import math`、`from pathlib import Path`，背后的机制就是 **模块（module）** 与 **导入（import）**：它让代码可以拆分到多个文件、按需复用，也让标准库和第三方库能接入你的程序。

这节课我们把 `import` 从“会写”讲到“懂原理、能排错、写出工程级代码”。

---

## 1. 什么是模块？为什么需要 import？

**模块（module）** 就是一个 `.py` 文件。文件名去掉 `.py` 就是模块名，例如 `utils.py` 的模块名是 `utils`。

当你执行 `import utils` 时，Python 会：

1. 找到 `utils.py`；
2. 执行这个文件中的顶层代码；
3. 把执行后产生的名字绑定到一个模块对象上；
4. 在你当前命名空间里创建变量 `utils`，指向这个模块对象。

```python
# math 是标准库模块，导入后通过 math.sqrt 访问其中的函数
import math

print(math.sqrt(16))  # 4.0
print(math.pi)        # 3.141592653589793
```

关键结论：`import module` 导入的是 **模块对象本身**，不是模块里的所有名字。

---

## 2. import 的四种常用写法

### 2.1 `import module`

导入模块对象，通过 `module.name` 访问。

```python
import os

print(os.getcwd())  # 当前工作目录
```

### 2.2 `import module as alias`

给模块起别名，常用于长模块名或避免冲突。

```python
import numpy as np  # 第三方库常见别名；若未安装会报 ModuleNotFoundError

# print(np.array([1, 2, 3]))
```

### 2.3 `from module import name`

只把模块中的某个名字导入当前命名空间。

```python
from math import sqrt, pi

print(sqrt(25))  # 5.0
print(pi)        # 3.141592653589793
```

### 2.4 `from module import name as alias`

导入时重命名，避免和本地名字冲突。

```python
from math import sqrt as square_root

print(square_root(36))  # 6.0
```

关键结论：`from ... import ...` 导入的是模块里的 **具体名字**；`import module` 导入的是 **模块对象**。

---

## 3. import 的搜索路径与模块缓存

### 3.1 搜索路径

Python 导入模块时，会按顺序查找：

1. 内置模块（built-in modules），如 `sys`、`math`；
2. `sys.path` 中的目录列表，通常包括：
   - 当前脚本所在目录；
   - 环境变量 `PYTHONPATH` 指定的目录；
   - 标准库目录；
   - 第三方包安装目录（如 `site-packages`）。

```python
import sys

# 打印前 5 个搜索路径，便于理解“为什么 my_module 能被找到”
for path in sys.path[:5]:
    print(path)
```

### 3.2 模块缓存 `sys.modules`

模块第一次被导入后，会缓存在 `sys.modules` 中。再次 `import` 同一个模块不会重新执行文件。

```python
import sys
import math

# math 已经在 sys.modules 中
print('math' in sys.modules)  # True

# 再次导入不会重新执行 math.py（标准库也不会重复初始化）
import math as math_again
print(math is math_again)     # True
```

关键结论：同一个进程内，同一模块只会被真正执行一次，后续导入命中缓存。

---

## 4. 包（package）与 `__init__.py`

**包（package）** 是包含多个模块的目录。传统上，包目录下需要有一个 `__init__.py`，Python 会把它当作包的初始化模块。

例如：

```text
myproject/
  main.py
  mypkg/
    __init__.py
    math_utils.py
    string_utils.py
```

`mypkg/math_utils.py`：

```python
# 一个普通模块，供包内其他文件导入
def add(a, b):
    return a + b
```

`main.py` 中可以写：

```python
# 绝对导入：从包名开始写，推荐做法
from mypkg.math_utils import add

print(add(2, 3))  # 5
```

关键结论：包让多个模块组织成一个命名空间；绝对导入（absolute import）可读性最好。

---

## 5. `__name__`、`__all__` 与脚本/模块双身份

### 5.1 `__name__`

每个模块都有一个 `__name__`。直接运行文件时，`__name__ == '__main__'`；被导入时，`__name__` 是模块名。

```python
# demo_name.py
def main():
    print('作为脚本运行')

if __name__ == '__main__':
    main()
```

```bash
python demo_name.py        # 输出：作为脚本运行
python -c "import demo_name"  # 无输出，因为 __name__ 不是 '__main__'
```

### 5.2 `__all__`

`__all__` 是一个列表，控制 `from module import *` 时哪些名字会被导出。

```python
# mymod.py
__all__ = ['public_func']

def public_func():
    return 'public'

def _private_func():
    return 'private'
```

```python
from mymod import *

print(public_func())  # public
# print(_private_func())  # NameError，因为不在 __all__ 中
```

关键结论：工程代码中应避免 `from module import *`，因为它会污染命名空间、让名字来源不清晰。

---

## 6. 常见导入错误与排查思路

- `ModuleNotFoundError`：模块不存在或路径不对。检查模块名、`sys.path`、是否安装第三方包。
- `ImportError`：模块存在，但里面的名字不存在或循环导入。
- 循环导入（circular import）：A 导入 B，B 又导入 A。解决方式：延迟导入、重构依赖、把导入放到函数内部。
- 导入副作用：模块顶层代码在导入时执行。不要把耗时或带副作用的逻辑放在顶层。

```python
# 不好的做法：导入时执行耗时/副作用代码
def _heavy_init():
    return sum(range(10_000_000))

# _result = _heavy_init()  # 导入这个模块会立刻计算，拖慢启动

# 更好的做法：惰性计算
def get_result():
    return _heavy_init()
```

---

## 7. 工程级 import 规范

参考 PEP 8 和官方风格指南，推荐：

1. import 放在文件顶部，模块注释和文档字符串之后；
2. 分组顺序：标准库 → 第三方库 → 本地应用/库；
3. 每组之间空一行；
4. 每行只导入一个模块，除非是 `from subprocess import Popen, PIPE` 这种明确同源导入；
5. 优先使用绝对导入；
6. 避免通配符导入 `from module import *`；
7. 模块级 dunder（如 `__all__`、`__version__`）放在文档字符串之后、普通 import 之前，但 `from __future__ import ...` 必须最靠前（文档字符串之后）。

```python
"""示例模块：展示推荐的 import 顺序。"""

from __future__ import annotations  # 必须最靠前（文档字符串之后）

__all__ = ['main']
__version__ = '0.1'

# 标准库
import os
import sys
from pathlib import Path

# 第三方库（示例，若未安装请注释）
# import requests

# 本地模块
# from mypkg import utils


def main() -> None:
    print(Path.cwd())
    print(sys.version)


if __name__ == '__main__':
    main()
```

---

## 动手练习

创建一个本地项目目录 `import_lab/`，完成以下任务：

1. 新建 `import_lab/main.py`；
2. 新建 `import_lab/tools/__init__.py`；
3. 新建 `import_lab/tools/math_tools.py`，其中定义：
   - `add(a, b)` 返回两数之和；
   - `_secret()` 返回 `'secret'`；
   - 设置 `__all__ = ['add']`；
4. 在 `main.py` 中：
   - 使用 `from tools.math_tools import add` 导入并打印 `add(3, 4)`；
   - 使用 `import tools.math_tools as mt` 再次导入并打印 `mt.add(10, 20)`；
   - 打印 `mt.__name__`，观察模块名；
   - 尝试 `from tools.math_tools import *`，然后调用 `add`，确认 `_secret` 不可直接访问；
   - 用 `sys.modules` 验证 `tools.math_tools` 已被缓存。

完成后，尝试把 `main.py` 直接运行，也尝试在 `import_lab/` 上一级目录用 `python -m import_lab.main` 运行，观察 `sys.path` 和导入行为差异。

```python
"""
可运行示例：演示 import 的常见写法、__name__、__all__ 与模块缓存。
保存为 import_demo.py 后直接运行。
"""
import sys
import math
import math as math_alias
from math import sqrt, pi
from math import sqrt as square_root

# 1. import module：导入模块对象
print('1.', math.sqrt(16))

# 2. import module as alias
print('2.', math_alias.sqrt(25))

# 3. from module import name
print('3.', sqrt(36), pi)

# 4. from module import name as alias
print('4.', square_root(49))

# 5. __name__：直接运行 vs 被导入
print('5. __name__ =', __name__)

# 6. 模块缓存：同一个模块只执行一次
print('6. math in sys.modules =', 'math' in sys.modules)
print('7. math is math_alias =', math is math_alias)

# 8. __all__ 演示：定义一个临时模块对象不现实，这里展示语法意义
# 真实项目中：mymod.py 中写 __all__ = ['public_func']，from mymod import * 只导入 public_func

# 9. 安全地作为脚本运行
def main() -> None:
    print('9. main() 被调用，当前模块作为脚本运行。')

if __name__ == '__main__':
    main()
```

## py.module.from_import

# `from ... import ...`：模块导入的精准手术刀

## 一句话直觉

`import math` 是把整个工具箱搬回家，用的时候得写 `math.sqrt`；而 `from math import sqrt` 是直接从工具箱里只拿一把螺丝刀，用的时候直接 `sqrt`。**它就是「只取我要的，不要多余的」的导入方式。**

---

## 1. 为什么需要 `from ... import ...`？

Python 里一切皆模块（module）。一个 `.py` 文件就是一个模块，模块里可以定义变量、函数、类。要使用别的模块里的东西，就需要「导入」。

最基础的导入是 `import 模块名`：

```python
import math
print(math.sqrt(16))   # 必须写 math. 前缀
```

但如果我只用 `sqrt` 一个函数，每次都写 `math.` 太啰嗦，而且代码意图不够聚焦。这时 `from ... import ...` 就派上用场：

```python
from math import sqrt
print(sqrt(16))        # 直接调用，省去前缀
```

**核心结论**：`from 模块 import 名字` 的作用是：先加载整个模块，然后只把指定的「名字」绑定到当前命名空间（namespace），让你可以不带前缀地使用。

---

## 2. 一次导入多个名字，以及用 `as` 起别名

`from ... import ...` 支持一次拿多个名字，用逗号分隔；也支持用 `as` 起别名（alias），解决命名冲突或缩短名字。

```python
# 一次导入多个
from math import sqrt, pi, factorial
print(sqrt(9), pi, factorial(5))

# 起别名：当名字冲突或太长时很有用
from math import sqrt as square_root
print(square_root(25))

# 常见工程用法：把 numpy 的常用函数直接拿来
# from numpy import array as arr
```

**核心结论**：`as` 只是给导入进来的名字换个「本地称呼」，模块本名不受影响。

---

## 3. `from 模块 import *` 是什么？以及为什么工程上要慎用

`*` 表示「把模块里所有公开名字都导入当前命名空间」。听起来方便，但它是工程上的「反模式」。

模块可以通过 `__all__` 来显式声明「公开名字」——当定义了 `__all__` 时，`import *` 只会导入 `__all__` 里列出的名字。例如官方文档中示例模块：

```python
# 某模块内部
__all__ = ['a', 'b', 'c']
```

那么 `from 模块 import *` 只会导入 `a, b, c`，而不会导入模块内其他非公开名字。

```python
# 演示 __all__ 的效果（用一个临时模块模拟）
import types

m = types.ModuleType('demo')
m.a = 1
m.b = 2
m.c = 3
m._secret = 999        # 下划线开头，默认不被 import * 导入
m.__all__ = ['a', 'b', 'c']

ns = {}
exec('from demo import *', {'__builtins__': __builtins__, 'demo': m}, ns)
print(sorted(k for k in ns if not k.startswith('_')))  # ['a', 'b', 'c']
```

**核心结论**：
- `import *` 会污染当前命名空间，可能意外覆盖你已有的变量。
- 它让「这个名字从哪来」变得难以追踪（工具、IDE、静态检查都不友好）。
- **工程上推荐**：显式写出要导入的名字，或整个 `import 模块` 后再用前缀。

---

## 4. 模块级的「元信息」与隐藏约定

每个模块都可以带有一些「魔法」属性（dunder attributes，双下划线属性），它们是模块的元信息：

- `__all__`：`import *` 时公开的名字列表。
- `__version__`、`__author__`：版本与作者信息，社区约定俗成。
- `__doc__`：模块的文档字符串（docstring）。

```python
# 一个符合规范的模块头部写法
"""小工具模块。"""

__all__ = ['add', 'sub']
__version__ = '0.1'
__author__ = 'Your Name'

def add(a, b):
    return a + b

def sub(a, b):
    return a - b

def _internal():
    """下划线开头：弱内部标记，不被 import * 带走。"""
    return 'private'
```

**核心结论**：写模块时定义 `__all__` 是对使用者的礼貌——它明确告诉别人「哪些是我希望你用的」。

---

## 5. 进阶：`from ... import ...` 的常见陷阱与类型检查技巧

### 5.1 循环导入（circular import）

如果 `a.py` 里 `from b import X`，而 `b.py` 里又 `from a import Y`，就会循环导入，常见报错 `ImportError` / `AttributeError`。工程做法：把导入放到函数内部（延迟导入），或重构依赖关系。

### 5.2 只给类型检查用的导入：`TYPE_CHECKING`

有些模块（比如某些重型库）只在类型注解里用到，运行时导入它会很慢。可以用 `typing.TYPE_CHECKING` 做一个「只对类型检查器可见」的导入：

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import expensive_mod   # 运行时不会真的导入

def fun(arg: "expensive_mod.SomeType") -> None:
    ...
```

**核心结论**：`TYPE_CHECKING` 在运行时是 `False`，但在静态类型检查器眼里是 `True`，因此既能被类型检查，又不拖慢运行时。

### 5.3 惰性求值的注解

要注意，注解里的名字如果在运行时未定义，普通写法可能触发 `NameError`；可以用字符串形式或 `annotationlib` 的 `Format.STRING` / `Format.FORWARDREF` 来安全获取注解。

---

## 动手练习

**任务**：创建一个「数学小工具」模块，并用 `from ... import ...` 的三种方式分别使用它。

1. 新建文件 `math_utils.py`，内容包含：
   - 模块 docstring（一行即可）。
   - `__all__ = ['square', 'cube']`
   - `__version__ = '0.1'`
   - 公开函数 `square(x)`、`cube(x)`。
   - 一个下划线开头的函数 `_helper()`，不要放进 `__all__`。
2. 新建 `main.py`，依次做三件事并打印结果：
   - 用 `from math_utils import square` 导入并使用。
   - 用 `from math_utils import cube as cb` 导入并起别名。
   - 用 `import math_utils` 整模块导入，调用 `math_utils.square`。
3. **思考题**：如果你在 `main.py` 里写 `from math_utils import *`，`_helper` 会被导入吗？为什么？请动手验证并写出结论。

**验收标准**：`python main.py` 能正常打印三组结果，并且你能口头解释 `__all__` 与下划线前缀在 `import *` 中的区别。


---

## 本课题目

### single_choice · None



- [A] 先输出 hello，再输出 True
- [B] 只输出 True，因为标准库的 math 优先于同目录同名文件
- [C] 抛出错 ImportError
- [D] 输出 hello 后出错，因为 math 里没有 pi

**参考答案**：1

**解析**：Python 在查找模块时会先搜索脚本所在目录。若本地目录存在 math.py，它会覆盖标准库的 math，因此 import math 得到的不是标准库模块，访问 math.pi 会抛 AttributeError。选项 A 是常见误解，但无论如何不会既打印 hello 又成功访问 pi。

### single_choice · None



- [A] 可以访问 pkg.sub，因为导入包时会自动导入所有子模块
- [B] 可以访问 pkg.sub，因为 __init__.py 中显式导入了子模块
- [C] 报 AttributeError，因为 import pkg 只绑定顶层包名
- [D] 报 ImportError，循环导入导致的

**参考答案**：1

**解析**：导入包时执行 __init__.py，其中 `from . import sub` 会把 sub 注册到包命名空间，因此 pkg.sub 可用。选项 A 的误解在于认为导入包会自动导入全部子模块，实际上只有当 __init__.py 或其它地方显式导入才会绑定到包命名空间。选项 C 在未显式导入 sub 时才成立。

### single_choice · None



- [A] 报 NameError
- [B] 报 ImportError
- [C] 正常绑定 random，模块代码不重复执行（仍在 sys.modules）
- [D] 正常绑定 random，且模块代码会再执行一次

**参考答案**：2

**解析**：del 只删除当前命名空间中的名字绑定，sys.modules 里的模块对象仍在，因此再次 import 只是重新绑定名字，不重复执行模块代码。

### single_choice · None



- [A] m 会被绑定到当前命名空间
- [B] 只有 a、b 被绑定，m 本身不绑定
- [C] 如果 m 中还有 c，会一并导入
- [D] 必须 m 是包，不能是普通模块

**参考答案**：1

**解析**：from ... import ... 只把列出的名字引入当前命名空间，模块名 m 本身不会被绑定（除非另有绑定）。m 可以是普通模块也可以是包。

### single_choice · None



- [A] 使 foo 成为模块内唯一可访问的名字
- [B] 影响 `from m import *` 时被导入的名字集合
- [C] 决定模块能否被 import
- [D] 决定 foo 是否对外私有

**参考答案**：1

**解析**：__all__ 主要控制 `from m import *` 导入哪些名字；它不影响常规 import、不影响模块可被导入与否，也不阻止通过 `from m import 具体名字` 导入其它名字，更不是访问控制。

### single_choice · None



- [A] import os
- [B] import os.path
- [C] from os import *
- [D] import numpy as np

**参考答案**：2

**解析**：`from m import *` 会把大量名字一次性引入当前命名空间，容易覆盖已有名字，可读性也差，因此普遍不被推荐。其余写法都明确具体。

### single_choice · None



- [A] 把包目录标记为可导入的包（在旧式命名空间包语义下讨论时）
- [B] 执行包的初始化代码
- [C] 为包命名空间绑定子模块或变量
- [D] 自动把包内所有子模块都导入进来

**参考答案**：3

**解析**：__init__.py 在包被导入时执行，可以执行初始化、绑定名字，也被用作普通包的标记；但它不会自动导入包内的所有子模块，除非显式写出导入语句。

### single_choice · None



- [A] 完全等价，运行结果相同
- [B] 相对导入依赖当前包名，绝对导入硬编码包名，包被重命名时相对导入更稳
- [C] 相对导入更快
- [D] 绝对导入在包内不可使用

**参考答案**：1

**解析**：相对导入相对于当前包，包里代码整体被重命名时仍可用；绝对导入写死了顶层包名。两者语义在正常情况下等价，但可移植性不同。

### single_choice · None



- [A] 正常输出 greet 的返回值
- [B] 会因为没有把 utils 加入 sys.path 而失败
- [C] 会触发循环导入
- [D] 会因为缺少 setup.py 而失败

**参考答案**：0

**解析**：main.py 所在目录会在启动时加入 sys.path，且 utils 是带 __init__.py 的包，因此 `from utils.helper import greet` 可正常解析（前提是 helper.py 中定义了 greet）。是否安装与 setup.py 无关（选项 D 的误解），与 sys.path 的手工添加也无关（选项 B 的误解）。

### single_choice · None



- [A] 报 ModuleNotFoundError
- [B] 正常完成，import 会从 sys.modules 取到该占位对象
- [C] 报 TypeError，因为 not a module
- [D] 会把 sys.modules 清空

**参考答案**：1

**解析**：import 首先查询 sys.modules，若已存在直接将其绑定为导入结果，不会检查它是否真的是模块对象。因此该对象会被绑定到名字 nonexist。这是常见的“缓存优先”机制体现，但实际项目不应这么用。

### single_choice · None



- [A] 脚本所在目录或当前工作目录相关路径
- [B] 环境变量 PYTHONPATH 指定的目录
- [C] 标准库安装目录
- [D] 操作系统内核模块列表

**参考答案**：3

**解析**：Python 的模块搜索路径由 sys.path 决定，通常包括脚本目录、PYTHONPATH、标准库目录及 site-packages 等；与操作系统内核模块无关。

### single_choice · None



- [A] `import a.b` 后可以用 b 直接访问
- [B] 两者都会把 b 绑定到当前命名空间
- [C] `import a.b` 绑定 a，`from a import b` 绑定 b
- [D] `from a import b` 会同时导入 a.b.c

**参考答案**：2

**解析**：`import a.b` 把顶层名 a 绑定进当前命名空间，需要通过 a.b 访问 b；`from a import b` 则把 b 直接绑定。两种写法都不会把顶层 a 同时绑定为 b 以外的名字，也不会自动导入更深层模块。

### single_choice · None



- [A] 两者都会把 os 绑定到当前命名空间
- [B] `import os.path` 只把 os 绑定进来，随后可以用 os.path 访问
- [C] `from os import path` 后可以直接用 path.join(...)，但也必须用 os.path.join(...)
- [D] `from os import path` 会把整个 os 模块绑定进来

**参考答案**：1

**解析**：`import os.path` 绑定的是顶层名称 os（随后可用 os.path 访问），不会绑定名称 path；`from os import path` 则只绑定 path，可以直接用 path.join。选项 A、D 混同了两者的绑定行为，选项 C 自相矛盾。

### single_choice · None



- [A] 双方都能顺利导入，因为 import 机制会自动解决循环依赖
- [B] 抛 ImportError，提示 cannot import name（或 partially initialized module 相关错误）
- [C] 抛 SyntaxError
- [D] 只会导入 a，b 被忽略

**参考答案**：1

**解析**：循环导入时，某一边会先执行到一半，被导入方尝试从尚未完全初始化的模块中取出尚未定义的名字，因而报错。选项 A 的误解常见于认为解释器能自动化解循环依赖。

### single_choice · None



- [A] 正常工作，模块名不受变量赋值影响
- [B] 抛 AttributeError，因为 json 现在指向字典
- [C] 抛 ImportError，模块被重新导入
- [D] 抛 TypeError，dumps 不存在于字典

**参考答案**：1

**解析**：import 只是把模块对象绑定到一个名字，之后可以把该名字重新绑定为其它对象，原来的模块仍然存在但名字丢失。再次调用 json.dumps 相当于对字典取属性 dumps，因此 AttributeError。选项 A 误解了名字绑定的可覆盖性。

### single_choice · None



- [A] 导入 numpy 并创建别名 np，之后只能用 np 访问，numpy 不再绑定
- [B] 同时绑定 numpy 和 np 两个名字
- [C] 如果 numpy 未安装，import 会静默失败，np 为 None
- [D] np 是 numpy 的副本，修改 numpy 不影响 np

**参考答案**：0

**解析**：`import X as Y` 只把模块对象绑定到 Y，不绑定原名称 X（除非 X 本就是其它已有名字）。选项 B 误以为两个名字都会被绑定，选项 C、D 完全不符合 import 语义。

### single_choice · None



- [A] foo.py 必须作为顶层脚本直接运行
- [B] foo.py 必须位于某个包内，且该包被以包的形式导入
- [C] bar 必须是标准库模块
- [D] 必须已经执行过 import foo

**参考答案**：1

**解析**：相对导入要求模块所属的包可确定，通常意味着脚本位于包内并以包成员身份被导入（或使用 -m 运行包内模块）。直接运行脚本时 __package__ 为空，相对导入会失败。

### single_choice · None



- [A] AttributeError
- [B] ModuleNotFoundError（ImportError 的子类）
- [C] FileNotFoundError
- [D] SyntaxError

**参考答案**：1

**解析**：找不到模块时 Python 抛 ModuleNotFoundError，它是 ImportError 的子类。AttributeError 是找到了模块但名字不存在；FileNotFoundError 与文件操作有关；SyntaxError 是语法问题。

### single_choice · None



- [A] 模块名拼写错误
- [B] 包里没有这个子模块
- [C] 模块存在，但 from m import name 中的 name 不存在
- [D] 目标模块没有 __init__.py

**参考答案**：2

**解析**：模块本身能定位到但所需名字不存在，抛 ImportError（常带 cannot import name）。前两者及缺少 __init__.py（对普通包而言）通常表现为找不到模块，抛 ModuleNotFoundError。

### single_choice · None



- [A] 每次都重新执行 os 模块代码
- [B] 第一次执行后模块缓存在 sys.modules，后续 import 直接复用
- [C] 第二次会抛 ImportError，模块不可重复导入
- [D] 只有第一次 import 会绑定名字，之后 import 语句是语法错误

**参考答案**：1

**解析**：解释器把已导入模块缓存在 sys.modules，后续 import 语句会命中缓存，只做名字绑定而不重复执行模块顶层代码。选项 A 的误解是以为 import 会反复执行。

### single_choice · None



- [A] 前者把 sqrt 直接引入当前命名空间，可以直接调用 sqrt()；后者需要通过 math.sqrt() 调用
- [B] 前者会加载整个 math 模块的所有函数，后者只加载 sqrt
- [C] 前者只能导入函数，后者只能导入模块
- [D] 两者完全等价，只是写法不同

**参考答案**：0

**解析**：`from math import sqrt` 把 sqrt 这个名字直接绑定到当前命名空间，可直接调用；`import math` 只绑定模块名 math，需要 math.sqrt() 访问。两种方式都会完整加载模块，区别仅在于名字绑定。

### single_choice · None



- [A] <class 'float'>
- [B] <class 'module'>
- [C] <class 'function'>
- [D] 报错：pi 未定义

**参考答案**：0

**解析**：`from math import pi` 把 math 模块中的 pi 常量绑定到当前命名空间，pi 是浮点数，因此 type(pi) 是 float。它不再是模块对象。

### single_choice · None



- [A] True，a 与 math.pi 指向同一个浮点对象
- [B] False，as 会复制一份新的对象
- [C] 报错，a 与 math.pi 不可比较
- [D] True，但 a 是字符串

**参考答案**：0

**解析**：from import 只是名字绑定，不会复制对象。a 和 math.pi 指向同一个对象，因此比较相等并返回 True。

### multi_choice · None



- [A] 它要求当前文件属于一个包（有 __init__.py 或作为包的一部分）
- [B] 在直接以脚本方式运行的顶层模块中通常不能使用
- [C] 它导入的是同一包内的 sibling 子模块
- [D] 它可以替代所有绝对导入的写法
- [E] 它在包的 __init__.py 中也可使用

**参考答案**：[0, 1, 2, 4]

**解析**：相对导入要求模块处于包结构中；直接运行顶层脚本时 __package__ 为空，相对导入会失败；它导入同包的 sibling；在 __init__.py 中也可用。D 错误，相对导入不能替代全部绝对导入，特别是跨包场景。

### fill_blank · None



**参考答案**：["sqrt, pi", "sqrt,pi", "pi, sqrt", "pi,sqrt"]

**解析**：from import 支持用逗号分隔一次导入多个名字，顺序无关紧要，因此 sqrt, pi 或 pi, sqrt 均可。

### fill_blank · None



**参考答案**：["as", "As", "AS"]

**解析**：Python 使用 as 关键字为导入的名字设置别名，写法为 from math import sqrt as sq。

### fill_blank · None



**参考答案**：["as OD", "as  OD"]

**解析**：别名写法为 `as OD`，关键字 as 后面跟别名。

### code_reading · None



**参考答案**：输出 6.28。sqrt(4) 返回 2.0，math.pi 约为 3.14159，相乘得约 6.283，round 保留两位小数为 6.28。这里 sqrt 是通过 from math import 直接绑定的名字，math.pi 通过模块访问。

**解析**：考察 from import 绑定与模块属性访问混用的场景。sqrt(4) = 2.0，math.pi ≈ 3.14159，乘积约为 6.28318，round 到两位是 6.28。

### code_reading · None



**参考答案**：输出 shadowed。函数定义 sqrt 覆盖了之前 from math import 绑定的 sqrt 名字，因此调用的是本模块定义的函数，返回字符串 'shadowed'。

**解析**：from import 的名字与普通名字一样存储在当前命名空间，后续 def 定义同名函数会覆盖它。这是导入名字被覆盖的典型例子。

### code_reading · None



**参考答案**：不会报错，输出 3.0 3.0。from math import sqrt 绑定 sqrt 到当前命名空间，import math 绑定模块名 math，两者互不冲突，可同时使用。

**解析**：两种导入方式可以在同一模块共存，因为绑定的名字不同（sqrt 与 math）。它们指向同一模块的同一对象。

### scenario · None



**解析**：常见做法包括：1) 用 `import utils` 并通过 utils.read_config() 访问，明确限定命名空间；2) 使用 as 起别名，如 `from utils import read_config as utils_read_config`；3) 对两个来源都使用别名以彻底避免同名冲突。核心是让名字来源清晰、命名空间可控。

### scenario · None



**解析**：直接运行 b.py 时，b.py 被视为顶层脚本，其所在目录而非包的父目录被加入 sys.path，找不到 mypkg 包，因此绝对导入失败。可行方案：1) 使用 `python -m mypkg.b` 以模块方式运行；2) 在 b.py 中改用相对导入 `from .a import helper` 并保证通过包方式运行；3) 确保从包的父目录启动并配置好 PYTHONPATH。核心是保证模块处于正确的包上下文中。

### single_choice · None



- [A] 前者把 os.path 子模块绑定为名字 path；后者把 os 绑定到当前命名空间，通过 os.path 访问
- [B] 前者会导入整个 os 模块的所有子模块
- [C] 后者无法使用 os.path 的任何函数
- [D] 前者和后者都会把 path 作为顶层名字引入

**参考答案**：0

**解析**：`from os import path` 把子模块 path 绑定为当前命名空间的 path；`import os.path` 则绑定 os 名字，需用 os.path 访问。两者都可用，但命名空间绑定不同。

### single_choice · None



- [A] 9
- [B] 3.0
- [C] 报错：不能给导入的名字赋值
- [D] None

**参考答案**：0

**解析**：from import 只是把名字绑定到当前命名空间，sqrt 可以被重新赋值为 9，此后 sqrt 不再是函数。这是覆盖导入名字的常见陷阱。

### single_choice · None



- [A] a.x 仍然是 1，因为这是两个独立的命名空间绑定
- [B] a.x 会变成 2，因为是引用传递
- [C] 会报错，导入的名字不可修改
- [D] 取决于 Python 版本

**参考答案**：0

**解析**：from import 把对象绑定到当前命名空间的名字上，重新赋值只改变当前模块的绑定，不影响原模块 a 中的 x。

### single_choice · None



- [A] 它会把 math 模块中所有不以双下划线开头的公开名字导入当前命名空间
- [B] 它只导入 math 模块中定义在 __all__ 之外的私有名字
- [C] 它等价于 import math，不改变命名空间
- [D] 它一定会导入所有名字，包括以 _ 开头的

**参考答案**：0

**解析**：星号导入默认导入模块中不以下划线开头的公开名字；若模块定义了 __all__，则按 __all__ 列表导入。它容易造成命名冲突，通常不推荐。

### multi_choice · None



- [A] 它把 name 直接绑定到当前命名空间
- [B] 被导入的 name 可以与本模块已有的名字发生覆盖
- [C] 它要求 module 必须已经安装或位于可导入路径中
- [D] 它只能一次导入一个名字
- [E] 导入后仍然可以通过 name.__module__ 之类的属性追溯来源

**参考答案**：[0, 1, 2]

**解析**：A 正确，名字被直接绑定；B 正确，会覆盖同名绑定；C 正确，模块必须可导入。D 错误，可一次导入多个名字（用逗号分隔）。E 说法不严谨/并非总是成立，取决于对象类型，通常不作为可靠特性。

### multi_choice · None



- [A] from collections import defaultdict, Counter
- [B] from os import path as p
- [C] from math import sqrt as s, pi as p
- [D] from import math sqrt
- [E] from json import dumps

**参考答案**：[0, 1, 2, 4]

**解析**：A、B、C、E 都是合法的 from import 写法，支持逗号分隔多个名字和 as 别名。D 语法错误，import 关键字位置不对。

### single_choice · None



- [A] 2
- [B] 1
- [C] 'a'
- [D] KeyError

**参考答案**：0

**解析**：Counter 统计每个字符出现次数，'aabbc' 中 'a' 出现 2 次，因此 c['a'] 返回 2。as 只是给 Counter 起别名 C，语义不变。

### single_choice · None



- [A] 可以执行，最终 sqrt 仍然只有一份绑定，指向 math.sqrt
- [B] 会抛出 SyntaxError
- [C] 会导入两次，产生两个 sqrt
- [D] 只会导入第一个，第二个被忽略并报错

**参考答案**：0

**解析**：重复导入同名名字不会报错，最终命名空间中 sqrt 仍只有一个绑定。Python 允许这种冗余写法，不产生额外效果。
