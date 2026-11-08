# s1u6l2 `if __name__ == "__main__":` 完全指南 / 模块的名字与身份

> 来源 `content/lessons/s1u6l2.json`

## py.module.if_main

# `if __name__ == "__main__":` 完全指南

> **一句话直觉**：这段代码的意思是——"如果我这个文件是被**直接运行**的，就执行下面的代码；如果我被别人 **import 导入**，就安静地当个工具库"。

学 Python 的第一周你就会看到别人这样写，但很多人写了三年也说不清它到底在做什么。这一节课我们把这件事彻底讲透。

---

## 一、Python 文件是怎么被执行的？

Python 里有两种方式让一个 `.py` 文件"跑起来"：

1. **直接运行**：`python foo.py`，此时 Python 把 `foo.py` 当作**主程序**（main script）。
2. **被导入**：在别的文件里 `import foo`，此时 Python 把 `foo.py` 当作一个**模块**（module），只加载它、不主动执行它"对外暴露逻辑"。

不管哪种方式，Python 在加载文件之前都会先给这个文件配置一个特殊变量 `__name__`（双下划线 name，读作 "dunder name"）。

- 直接运行时：`__name__ == "__main__"`（固定字符串 `"__main__"`）。
- 被导入时：`__name__` 等于模块名（不带 `.py` 的文件名）。

所以 `if __name__ == "__main__":` 本质上就是一句"运行方式判断"。

```python
# file: greet.py
print(f"我被加载了，此时 __name__ = {__name__!r}")
```

- 执行 `python greet.py` → 输出 `__name__ = '__main__'`
- 在别的文件里 `import greet` → 输出 `__name__ = 'greet'`

---

## 二、为什么需要它？——"可导入"与"可运行"的双重身份

假设你写了一个模块 `math_utils.py`，里面同时有"工具函数"和"演示代码"：

```python
# 反例：没有 if __name__ 保护
# file: math_utils.py
def add(a, b):
    return a + b

# 演示代码也放在顶层，导入时会被意外执行！
print("演示：1 + 2 =", add(1, 2))
```

此时如果别人写 `from math_utils import add`，会**顺带在屏幕上打印一行无关的 "演示：..."**——这就是模块的**副作用**（side effect）。大型项目里，一个副作用可能触发数据库连接、写文件、启动服务，后果很严重。

正确写法：把演示逻辑塞进 `if __name__ == "__main__":` 里面。

```python
def add(a, b):
    return a + b

if __name__ == "__main__":
    # 只在直接运行时执行，被 import 时跳过
    print("演示：1 + 2 =", add(1, 2))
```

这样 `math_utils.py` 就有了两种干净的身份：
- **当作库**：只提供 `add`，零副作用。
- **当作脚本**：`python math_utils.py` 时运行演示/CLI 逻辑。

这是 Python 里最常用的"一鱼两吃"模式。

---

## 三、和 `import`、`__all__`、`__version__` 的配合

官方推荐的模块头部通常会写元信息（metadata），并用 `__all__` 声明"对外公开的名字"：

```python
"""math_utils: 演示一个规整的模块头部。"""

__all__ = ["add", "sub"]          # from math_utils import * 时只导出这两个
__version__ = "0.1.0"
__author__ = "Your Name"

def add(a, b): ...
def sub(a, b): ...
def _internal_helper(): ...        # 单下划线开头：约定为"内部使用"
```

要点：
- `__all__` 只影响 `from m import *`，不禁止别人显式 `from m import _internal_helper`。
- `__version__` / `__author__` 是社区惯例，工具（打包、日志、诊断）会读它。
- 想要"被执行"的入口逻辑，全部放进 `if __name__ == "__main__":` 块里。

---

## 四、标准工程结构：把 `main()` 单拎出来

当入口逻辑变长，最佳实践是：**定义 `main()` 函数**，然后在守卫块里调用它。这样 `main` 本身也可被测试、被复用。

```python
import sys

def main(argv: list[str]) -> int:
    print("参数：", argv)
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))  # 用返回值作为退出码
```

- `raise SystemExit(code)` 是比裸 `sys.exit(code)` 更"库化"的写法：它不依赖你 `import sys` 之外的任何东西。
- 退出码 `0` = 成功，非 0 = 失败。这是 Linux/macOS 脚本的通用约定。
- 单元测试可以直接 `from math_utils import main` 后调用 `main([...])`，无需真的 `subprocess` 起进程。

---

## 五、进阶：`TYPE_CHECKING`——同一个思想在类型注解上的延伸

同一个"只在某条件下执行"的模式，在类型系统里还有一位哥哥：`typing.TYPE_CHECKING`。它的取值在**运行时是 `False`**，但在**静态类型检查器眼里是 `True`**。

> 场景：某个模块**只用于类型标注**，但导入它很慢或很重（比如 `pandas`、`torch`）。用 `if TYPE_CHECKING:` 包起来，运行时就不会真去导入它。

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import expensive_mod   # 运行时不会真的 import

def fun(arg: "expensive_mod.SomeType") -> None:
    ...
```

注意注解里要写成**字符串**（或使用 `from __future__ import annotations`），因为在运行时 `expensive_mod` 这个名字并不存在。

---

## 六、总结：一张心法

| 需求 | 写法 |
|---|---|
| 这个文件被直接跑时才执行 | `if __name__ == "__main__":` |
| 被 import 时只提供能力 | 顶层只放 `def` / `class` / 常量 |
| 暴露公开 API | `__all__ = [...]` |
| 可测试的入口 | `def main(): ...` + 守卫块 |
| 只在静态检查时导入的重模块 | `if TYPE_CHECKING:` |

背下第一条，理解其余四条，你就掌握了 Python 模块系统的"入口思维"。

```python
"""
demo: 一个可运行、可导入、可测试的完整模块示例。
运行：python demo.py Alice
导入：from demo import greet
"""

__all__ = ["greet", "main"]
__version__ = "1.0.0"
__author__ = "Tutor"

import sys


def greet(name: str) -> str:
    """返回一句问候语。"""
    return f"Hello, {name}!"


def main(argv: list[str]) -> int:
    """命令行入口：把 argv 里的名字逐个问候。"""
    names = argv or ["World"]
    for name in names:
        print(greet(name))
    return 0


# 关键：只有被直接运行（__name__ == "__main__"）时才执行 main。
if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

## py.module.name

# py.module.name：模块的名字与身份

> **一句话直觉**：模块（module）不是「一段代码文件」，而是一个**有名有姓、可被重新命名、可查询全名的对象**——`py.module.name` 就是问「我现在到底是谁、从哪来」。

课程：`s1u6l2` · 前置：无（本知识点是全课程的起点之一）

---

## 1. 模块是什么：文件的「身份证」

Python 里，任何一个 `.py` 文件被导入（import）后，都会变成一个 `module`（模块）对象。这个对象的身份里，最重要的两个属性就是：

- `__name__`：模块的名字。作为脚本直接运行时是 `"__main__"`；被导入时是「包名.模块名」。
- `__file__`：模块来自哪个文件（包 `__init__` 可能没有）。

为什么先学这个？因为后面所有关于包（package）、导入路径、`if __name__ == "__main__"`、`from M import *` 的行为，都建立在这两个属性之上。

```python
# demo_name.py（一个普通模块）
print("我的 __name__ 是:", __name__)

if __name__ == "__main__":
    # 只有「直接运行 python demo_name.py」时才执行
    print("我是被当作脚本运行的")
else:
    # 被别的模块 import 时才执行
    print("我是被导入的")
```

运行 `python demo_name.py`：输出 `__main__`。  
在另一个文件里 `import demo_name`：输出 `demo_name`。

> 记住：`__name__` 是**运行时**决定的值，不是文件里写死的。

---

## 2. 模块名与「全名」：`__name__` vs `__qualname__`

- `__name__`（模块层）：模块的导入名。
- `__qualname__`（类 / 函数层）：带层级路径的「限定名」（qualified name），用于调试和反射。

```python
import os  # 标准库模块

print("模块名:", os.__name__)          # 'os'
print("来自文件:", os.__file__)        # '/usr/lib/python3.x/os.py' 类似路径

class Outer:
    class Inner:
        def method(self): ...

print("类全名:", Outer.Inner.__qualname__)       # 'Outer.Inner'
print("方法全名:", Outer.Inner.method.__qualname__)  # 'Outer.Inner.method'
```

要点：
- 模块只有 `__name__`（没有 `__qualname__`）。
- 类和方法有 `__qualname__`，比 `__name__` 更适合在日志里打印「我是谁里面的谁」。

---

## 3. 名字冲突与「重命名」：`import as`

模块名和变量名一样，可以绑定到任何名字上：

```python
import numpy as np                # 常见的别名重命名
from collections import OrderedDict as OD

print(np.__name__)   # 'numpy'
print(OD.__module__) # 'collections' —— 对象所在模块
```

注意一个容易混淆的点：**对象上的 `__module__`** 是「定义它的模块名」，而 `__name__` 是「这个模块本身的名字」。

```python
def f():
    pass

print(f.__module__)  # '__main__'（如果定义在脚本里）
print(f.__name__)    # 'f'
```

---

## 4. 模块的「公开名字」：`__all__`

按 PEP 8 风格：想让 `from M import *` 只导出你允许的名字，就设置模块级变量 `__all__`（一个字符串列表）。

```python
# mymod.py
__all__ = ["a", "b", "c"]   # 只导出 a、b、c

a = 1
b = 2
c = 3
d = 4                     # 不会被 `from mymod import *` 导出
```

```python
from mymod import *
print(a, b, c)   # 1 2 3
print(d)         # NameError: name 'd' is not defined
```

- `__all__` 为空列表 `[]` 表示：这个模块**没有公开 API**。
- 而非公开的全局变量按惯例用**单下划线**前缀（如 `_internal_cache`）。

> 注意：`__all__` **只影响 `*` 导入**，用 `from mymod import d` 仍可显式拿到 `d`。

---

## 5. 模块的元信息：`__version__` / `__author__` / `__doc__`

工程级代码会把「作者、版本、文档」作为模块的元数据放在顶部：

```python
# mypkg/mod.py
"""这个模块做了一些有用的事情。"""

__version__ = "0.1"
__author__ = "Cardinal Biggles"
__all__ = ["a", "b", "c"]

a = b = c = 1
```

用起来：

```python
import mypkg.mod as m
print(m.__doc__)      # '这个模块做了一些有用的事情。'
print(m.__version__)  # '0.1'
print(m.__author__)   # 'Cardinal Biggles'
print(m.__name__)     # 'mypkg.mod'
```

工程习惯：
- 包级别的身份也常用包的 `__init__.py` 里的 `__version__` 暴露出来。
- 发布到 PyPI 时，`__version__` 常与 `pyproject.toml` 的版本保持一致。

---

## 6. 一段完整的记忆图

| 名字 | 属于谁 | 含义 |
|------|--------|------|
| `__name__` | 模块 / 类 / 函数 | 名字（模块为导入名，脚本时为 `"__main__"`） |
| `__qualname__` | 类 / 函数 | 带层级路径的限定名 |
| `__module__` | 类 / 函数 | 定义它的模块名 |
| `__file__` | 模块 | 源文件路径 |
| `__doc__` | 模块 / 类 / 函数 | 文档字符串 |
| `__all__` | 模块 | `from M import *` 的公开名单 |
| `__version__` / `__author__` | 模块 | 元数据（约定，非解释器强制） |


---

## 本课题目

### single_choice · None



- [A] 只会定义 greet 函数，不会输出任何内容
- [B] 会输出 Hello, Alice，因为模块顶层的 print 在导入时也会执行
- [C] 会抛出 ImportError，因为被导入的模块不能有顶层代码
- [D] 会把 greet 变成内置函数，之后无需前缀即可调用

**参考答案**：1

**解析**：导入模块会执行该模块顶层的全部语句，因此顶层 print 会输出。A 是常见误解，认为 import 只做定义。C 错误，模块允许有顶层代码。D 混淆了导入与内置函数。

### single_choice · None



- [A] def __main__():
      run_tests()
- [B] if __name__ == "__main__":
      run_tests()
- [C] if __main__ == True:
      run_tests()
- [D] while __name__ == "main":
      run_tests()

**参考答案**：1

**解析**：标准写法是判断 __name__ 是否等于 "__main__"。A 只是定义函数不会调用。C 非法，__main__ 不是变量。D 条件错误且用 while 不合适。

### single_choice · None



- [A] import sys 必须放在 if 块内部才能生效
- [B] 字符串引号不匹配，__main__ 后缺一个引号，会导致语法错误
- [C] main 函数不能访问 sys.argv
- [D] if 块中不能调用函数，只能写 print

**参考答案**：1

**解析**：字符串 "__main__ 缺少右侧引号，会引发 SyntaxError。A、C、D 都是常见误解，与 Python 规则不符。

### single_choice · None



- [A] 甲对，导入时 __name__ 就是 "__main__"
- [B] 乙对，导入时 __name__ 是模块名，条件不成立
- [C] 两人都对，取决于操作系统
- [D] 两人都错，__name__ 在导入时不存在

**参考答案**：1

**解析**：导入模块时 __name__ 被设为模块名，而不是 "__main__"。A 与 C、D 都是对 __name__ 机制的错误理解。

### single_choice · None



- [A] if __name__ != "__main__":
- [B] if __name__ == "__main__":
- [C] if __name__ is "__main__":
- [D] if "__main__" == __name__:

**参考答案**：0

**解析**：!= 与 == 语义相反。B 相同。C 使用 is 比较字符串不是惯用写法但语义上仍为真时相同；D 是等价的交换顺序写法。

### single_choice · None



- [A] "mymodule"
- [B] "mypackage.mymodule"
- [C] "__main__"
- [D] "mypackage"

**参考答案**：2

**解析**：以 -m 运行模块时，该模块作为主程序执行，__name__ 为 "__main__"。A、B、D 是把它当作普通导入时的模块名。

### single_choice · None



- [A] 不会执行任何顶层代码，只有函数被导入
- [B] 会执行 print 和 do_heavy_work，导致导入变慢
- [C] 只会执行 print，不会执行 do_heavy_work
- [D] 会报错，因为导入模块时不允许顶层语句

**参考答案**：1

**解析**：导入会执行顶层语句，因此 print 与耗时函数都会运行。A、C 误以为顶层代码被跳过。D 错误，顶层语句允许存在。

### single_choice · None



- [A] 里面的代码必须比 if 行多缩进一级，否则会抛出 IndentationError
- [B] 里面的代码必须与 if 行完全对齐，Python 允许这样
- [C] 里面的代码不能有缩进，否则会被当作注释
- [D] 缩进层级可以随意变化，Python 不检查缩进

**参考答案**：0

**解析**：Python 使用缩进划分语句块，if 块内的语句必须多缩进一级。B、C、D 都违背 Python 缩进规则。

### single_choice · None



- [A] 会，因为 print 总会执行
- [B] 不会，因为 __name__ 被重新赋值为 "something"，条件不成立
- [C] 会，因为解释器会忽略用户的赋值
- [D] 不会，因为不能给 __name__ 赋值

**参考答案**：1

**解析**：虽然通常由解释器自动设置，但用户可重新赋值，之后条件不成立，print 不执行。A、C 误判执行行为。D 错误，赋值本身语法合法。

### single_choice · None



- [A] 输出 A
- [B] 不输出 A，但会执行 a.py 中 if 块之外的顶层代码
- [C] 抛出 ImportError
- [D] 输出两次 A

**参考答案**：1

**解析**：导入时 a 的 __name__ 为 "a"，if 块不执行；但其顶层其他语句会执行。A、D 误以为入口块会执行。C 不成立。

### single_choice · None



- [A] def process():
      ...
  
  process()
- [B] def process():
      ...
  
  if __name__ == "__main__":
      process()
- [C] if __name__ == "process":
      process()
- [D] process()
  
  if __name__ == "__main__":
      def process():
          ...

**参考答案**：1

**解析**：B 先定义函数，再在入口块中调用。A 导入时会执行。C 条件字符串错误。D 把函数定义放进入口块且顶层先调用，逻辑混乱且导入时可能报错。

### single_choice · None



- [A] `__main__` 是一个模块名，表示程序入口模块；`__name__` 是当前模块的字符串名称
- [B] 两者都是函数，可以调用
- [C] `__name__` 是模块名，`__main__` 是它的返回值
- [D] 两者都由用户手动创建，不存在于标准运行时

**参考答案**：0

**解析**：__main__ 是入口模块的名称，__name__ 保存当前模块名称字符串。B 错，二者都不是函数。C 错，__main__ 不是返回值。D 错，由解释器自动设置。

### single_choice · None



- [A] 直接运行输出 utils，导入时输出 __main__
- [B] 两种情况都输出 utils
- [C] 两种情况都输出 __main__
- [D] 直接运行输出 __main__，导入时输出 utils

**参考答案**：3

**解析**：直接运行的文件其 __name__ 为 "__main__"；被导入时 __name__ 为模块名 utils。A 与实际情况相反。B、C 都对 __name__ 的取值机制理解错误。

### single_choice · None



- [A] print("v1.0")
  if __name__ == "__main__":
      pass
- [B] if __name__ == "__main__":
      print("v1.0")
- [C] if __name__ == "v1.0":
      print("v1.0")
- [D] print("v1.0") 放在函数内部但不调用

**参考答案**：1

**解析**：把打印放进入口块，导入时不执行。A 顶层就打印了。C 条件错误。D 若不调用函数则不打印，且未体现直接运行与导入的区别。

### single_choice · None



- [A] 因为 __name__ 在运行时总是 "__main__"，所以总会执行
- [B] 因为该判断只在被导入时成立，所以总会执行
- [C] 因为直接运行该文件时 __name__ 就是 "__main__"，判断成立，代码会执行
- [D] 因为 Python 会忽略 if 语句，直接执行里面的内容

**参考答案**：2

**解析**：直接运行该文件时 __name__ 为 "__main__"，条件为真所以执行。A 错误地认为任何情况下都执行。B 说反了。D 违背 Python 语法规则。

### single_choice · None



- [A] 确保 main() 只在模块作为程序入口运行时调用，被导入时不会自动调用
- [B] 确保 main() 只在模块被导入时调用，直接运行时不调用
- [C] 确保 main() 被调用两次，一次导入一次运行
- [D] 定义了一个名为 __main__ 的函数

**参考答案**：0

**解析**：该判断用于区分「直接运行」与「被导入」两种场景，直接运行时调用 main()，导入时不调用。B 说反。C 臆造。D 把 __name__ 与函数定义混淆。

### single_choice · None



- [A] 先输出 3 再输出 7
- [B] 只输出 3，不会输出 7
- [C] 只返回 7，不会输出 3
- [D] 会抛出错误，因为顶层有 if 语句

**参考答案**：2

**解析**：导入时 __name__ 为 math_utils，if 块不执行，所以不会输出 3；调用 add(3,4) 返回 7。A、B 误以为导入会执行 if 块。D 错误，if 语句合法。

### single_choice · None



- [A] 它是用户必须手动定义的全局变量，否则程序无法运行
- [B] __name__ 的值在所有模块中都相同，都是文件名
- [C] 它是 Python 自动设置的，直接运行时值为 "__main__"，被导入时为模块名
- [D] 它只在类的内部存在，模块级别没有 __name__

**参考答案**：2

**解析**：__name__ 是解释器自动设置的模块级变量。A 错误，不需要手动定义。B 错误，取值随运行方式变化。D 错误，模块级同样存在。

### single_choice · None



- [A] def main():
      print("run")
  
  if __name__ == "__main__":
      main()
- [B] def main():
      print("run")
  
  main()
  
  if __name__ == "__main__":
      main()
- [C] if __name__ == "__main__":
      main()
  
  def main():
      print("run")
- [D] def main():
      print("run")
  
  if __name__ == "__main__":
      pass

**参考答案**：1

**解析**：B 在顶层先调用一次 main()，if 块中又调用一次，直接运行时会打印两次。A 正常一次。C 会因 main 未定义而报错。D 不会调用 main。

### single_choice · None



- [A] 会执行，因为 "main" 和 "__main__" 在 Python 中等价
- [B] 会执行，因为字符串比较忽略下划线
- [C] 不会执行，因为 __name__ 的值是 "__main__"，不等于 "main"
- [D] 不会执行，因为 if 语句缺少 else 分支

**参考答案**：2

**解析**：条件应为 "__main__"，写成 "main" 时比较为假，run() 不执行。A、B 是对字符串比较的错误理解。D 与 else 无关。

### single_choice · None



- [A] 提高程序运行速度，减少导入时间到零
- [B] 使模块既能作为脚本直接运行，又能被安全导入而不产生副作用
- [C] 让模块中的函数自动变为私有，无法被外部调用
- [D] 强制 Python 在导入时跳过整个模块的解析

**参考答案**：1

**解析**：该写法的核心价值是区分入口与库两种用法，避免导入时执行脚本逻辑。A 夸大性能作用。C 与访问控制无关。D 错误，导入仍需解析模块。

### single_choice · None



- [A] __main__
- [B] 模块的文件名
- [C] None
- [D] 模块所在包的名称

**参考答案**：0

**解析**：当一个文件被直接运行时，其 __name__ 被设为 '__main__'；只有被 import 导入时，__name__ 才是模块名。这是使用 if __name__ == '__main__' 保护入口代码的原理。

### single_choice · None



- [A] b
- [B] a
- [C] __main__
- [D] 什么都不输出

**参考答案**：1

**解析**：运行 b.py 时会导入模块 a，此时 a.py 中的 __name__ 为 'a'（模块名），而不是 '__main__'，因为 a.py 不是直接入口文件。

### multi_choice · None



- [A] 一个 .py 文件本身就是一个模块
- [B] 包是可以包含多个模块的目录，通常含有 __init__.py（常规包）
- [C] 导入模块时，模块中的顶层语句会在首次导入时执行
- [D] 模块一旦被导入，就永远无法被重新加载
- [E] 命名空间包必须包含 __init__.py

**参考答案**：[0, 1, 2]

**解析**：.py 文件即模块，含 __init__.py 的目录为常规包，导入时顶层语句执行一次。模块可以通过 importlib.reload 重新加载，所以 D 错；命名空间包不需要 __init__.py，所以 E 错。

### multi_choice · None



- [A] 在不同的 Python 进程中重新导入该模块
- [B] 在同一进程中使用 importlib.reload(mod)
- [C] 删除 sys.modules 中的条目后再 import 该模块
- [D] 在同一进程中重复执行 import mod 语句

**参考答案**：[0, 1, 2]

**解析**：模块顶层代码在首次导入时执行一次。不同进程有独立解释器，故会重新执行；reload 和先删除 sys.modules 缓存后重新导入也会触发执行。同一进程内重复 import 命中缓存，不再执行。

### multi_choice · None



- [A] 绝对导入从顶层包名开始书写，语义清晰，推荐使用
- [B] 相对导入用前导点表示当前包及上层包
- [C] 相对导入在直接运行脚本时可能失败
- [D] 相对导入可以跨 Python 版本被任意重命名而不受影响

**参考答案**：[0, 1, 2]

**解析**：绝对导入从顶层包名开始，推荐且清晰；相对导入用点号表示层级；直接运行脚本时缺少包上下文会导致相对导入失败。相对导入的路径随文件位置变动而变化，不能说「任意重命名不受影响」。

### multi_choice · None



- [A] 它是一个 dict，缓存已导入的模块对象
- [B] 导入模块时会先检查其中是否已有目标模块
- [C] 手工修改它会影响后续的导入行为
- [D] 它是只读结构，不能被修改

**参考答案**：[0, 1, 2]

**解析**：sys.modules 是记录已导入模块的字典，导入系统会先查它。它是可变的，删除或替换条目会影响后续导入，但通常不建议随意修改。

### fill_blank · None



**参考答案**：["__main__", "main"]

**解析**：直接运行时 __name__ == '__main__'，这也是 if __name__ == '__main__': 惯用法的依据。

### fill_blank · None



**参考答案**：["__init__.py", "init.py"]

**解析**：常规包要求目录内存在 __init__.py（可以为空），PEP 420 之后没有该文件也可作为命名空间包，但常规包习惯保留它以便初始化。

### code_reading · None



**参考答案**：依次输出 init、mod，且各只输出一次

**解析**：首次导入 pkg.mod 时会先导入父包 pkg，执行 pkg/__init__.py 输出 init，再执行 pkg/mod.py 输出 mod。第二次 import pkg.mod 命中 sys.modules 缓存，不再重复执行，因此不再输出。

### code_reading · None



**参考答案**：输出 [1, 2, 3]。原因：from mod import x 让 main 中的名字 x 与 mod.x 引用同一个列表对象，x.append(3) 原地修改该对象，因此 mod 中的 x 也被改变。

**解析**：from ... import 绑定的是对象的引用；对可变对象的原地修改（append）会同时反映到两个名称看到的同一个对象。若改为 x = x + [3] 重新绑定则不会影响 mod.x。注意：用 __import__('mod') 只是取出已经导入的 mod 模块对象。

### scenario · None



**解析**：直接以脚本路径运行 main.py 时，该模块的 __name__ 为 '__main__'，没有所属包的信息，相对导入无法确定父包，故抛出该错误。推荐用 python -m app.main 从项目根目录以包成员方式运行，这样模块具有包上下文，相对导入有效；或将相对导入改为绝对导入（如 from app import service / import app.service）并确保项目根在 sys.path 上。

### single_choice · None



- [A] 命名空间包必须显式包含 __init__.py 文件
- [B] 命名空间包不需要 __init__.py，可以跨多个目录共同组成同一个包
- [C] 命名空间包只能在 Python 2 中使用
- [D] 命名空间包不能被 import 语句导入

**参考答案**：1

**解析**：PEP 420 引入隐式命名空间包：当一个目录中没有 __init__.py 但其子目录被作为包搜索路径的一部分时，可组成命名空间包。它让同一个顶层包分散在多个 site-packages 目录成为可能。

### single_choice · None



- [A] 可以把它当作脚本直接运行时相对导入仍然有效
- [B] 相对导入基于当前模块的 __name__ 确定其所属包，所以只有当模块被作为包的一部分导入时才有效
- [C] 相对导入中的点号代表当前工作目录
- [D] 相对导入只能导入函数，不能导入模块

**参考答案**：1

**解析**：相对导入依赖模块的 __package__ / __name__ 来定位包。直接以脚本方式运行时模块没有包上下文，相对导入会报 ImportError，因此推荐用 -m 方式运行或保持包导入方式。

### single_choice · None



- [A] Python 总是先搜索内置模块，再搜索 sys.path 中的路径
- [B] Python 先搜索 sys.path 中的路径，找不到再搜索内置模块
- [C] Python 按字母顺序搜索所有已安装包
- [D] Python 只搜索当前工作目录

**参考答案**：0

**解析**：导入时解释器会先查找内建模块（built-ins），然后按 sys.path 顺序查找已安装模块与文件。sys.path 的顺序会影响同名模块的优先选择，这也是本地模块可能覆盖第三方模块的原因。

### single_choice · None



- [A] 在包内的模块里写了 from ..sibling import x，但该模块被以顶层脚本方式直接运行
- [B] 包的 __init__.py 文件为空
- [C] 使用了 importlib.import_module
- [D] 模块的 __name__ 是 '__main__'

**参考答案**：0

**解析**：当模块没有已知的父包上下文（例如以脚本直接运行）时，相对导入无法确定包层级，会抛出该错误。这与 __init__.py 是否为空无关，importlib 也不直接造成该错误（它只是改变了导入方式）。

### single_choice · None



- [A] 它必须包含至少一行可执行代码，否则包无法导入
- [B] 它可以用来初始化包的命名空间，例如控制 from pkg import * 的行为（__all__）
- [C] 它的存在会使包内所有模块都在导入包时被自动导入
- [D] 它只能包含 import 语句

**参考答案**：1

**解析**：__init__.py 在包被导入时执行，可定义 __all__、版本号或便捷子模块导入。它可以是空文件，子模块也不会因为你没有显式导入而自动加载（除非在 __init__ 中写了导入）。

### single_choice · None



- [A] 会，因为 mod.name 也被改为 'new'
- [B] 不会，因为 from ... import name 把值绑定到调用方的名字，与 mod 内的名字相互独立
- [C] 会，因为字符串是可变对象
- [D] 取决于是否在 mod 中定义了 __all__

**参考答案**：1

**解析**：from mod import name 相当于把 mod 中 name 当前引用的对象绑定到调用方的名字上，二者是两个独立的名称绑定。重新赋值调用方的名字不会改变 mod 模块中的 name。

### single_choice · None



- [A] import 每次执行都会重新从头运行被导入模块的代码
- [B] 被导入模块的顶层代码在首次导入时执行一次，之后从 sys.modules 缓存中取用
- [C] import 只读取文件不执行任何代码
- [D] 只有使用 from ... import 时才会执行模块代码

**参考答案**：1

**解析**：模块在第一次导入时被编译并执行顶层代码，执行结果放入 sys.modules；后续重复导入直接复用缓存中的模块对象。若要强制重新加载可用 importlib.reload。

### single_choice · None



- [A] 模块 A 在顶层 import B，而模块 B 在顶层 import A
- [B] 模块 A 使用 importlib.import_module 延迟导入 B
- [C] 模块 A 在函数内部导入 B
- [D] 模块 A 只导入标准库

**参考答案**：0

**解析**：A 顶层导入 B、B 顶层又导入 A 时，两者都在对方尚未初始化完成时就引用对方，容易得到半成品模块或报 ImportError。常见缓解方式是延迟导入（函数内导入）或调整依赖结构。
