# s1u2l1 深入理解 `int` 类型：从零基础到工程级 / 从零理解 Python 浮点数 / 从零到工程级的布尔类型讲义 等 4 个知识点

> 来源 `content/lessons/s1u2l1.json`

## py.type.int

# 深入理解 `int` 类型：从零基础到工程级

## 一句话直觉

`int` 是 Python 中最基础的整数类型，理解它不仅是学会“写数字”，更是理解 Python 对象模型、类型注解（type annotation）和类型检查（type checking）的起点——因为一切复杂类型系统都从 `int` 这样的标量类型开始。

---

## 1. 什么是 `int`：Python 中的整数对象

在 Python 里，`int` 是一个**类（class）**，每一个整数都是这个类的一个**实例（instance）**。与 C、Java 不同，Python 的 `int` 是**任意精度（arbitrary precision）**的：你可以写一个几百位的整数，它不会溢出。

```python
# int 是类，3 是它的实例
print(type(3))            # <class 'int'>
print(isinstance(3, int)) # True

# 任意精度：Python 3 中不会溢出
big = 10 ** 100
print(big)                # 10000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000
print(type(big))          # <class 'int'>

# 整数可以参与各种运算，结果仍是 int（除法除外）
print(7 + 3)    # 10
print(7 - 3)    # 4
print(7 * 3)    # 21
print(7 // 3)   # 2  （整除，结果是 int）
print(7 % 3)    # 1  （取余，结果是 int）
print(7 ** 2)   # 49 （幂运算，结果是 int）
print(7 / 3)    # 2.3333333333333335  （真除法，结果是 float）
```

**关键结论**：`int` 是 Python 的内置类，`type(3)` 返回 `int`，整数是它的实例，且支持任意精度。

---

## 2. 类型注解中的 `int`：变量、参数与返回值

Python 是**动态类型语言（dynamically typed language）**，运行时不会强制检查类型注解，但注解可以被 **mypy、Pyright、IDE** 等工具用来做**静态类型检查（static type checking）**。

```python
# 变量注解：a 预期是 int
a: int = 3

# 函数参数与返回值注解
def add(x: int, y: int) -> int:
    return x + y

print(add(1, 2))       # 3
print(add(1.5, 2.5))   # 4.0  —— 运行时不会报错，但类型检查器会警告
```

**关键结论**：`int` 作为类型注解时，表达“这个位置期望的值是整数”，但 Python 运行时不会强制执行；它服务于类型检查器和可读性。

---

## 3. `int` 作为类对象与 `type[int]`

类型注解中有一个容易混淆的点：`int` 表示“int 的实例”，而 `type[int]` 表示“int 这个类对象本身”。这在工厂函数、注册表等场景中非常有用。

```python
# a 是 int 的实例
x = 3          # 类型是 int
y = int        # 类型是 type[int]
z = type(x)    # 也是 type[int]

# type[C] 是协变的（covariant）：子类类对象可以当父类类对象用
class User: ...
class ProUser(User): ...

def make_new_user(user_class: type[User]) -> User:
    return user_class()

make_new_user(User)      # OK
make_new_user(ProUser)   # OK：type[ProUser] 是 type[User] 的子类型
# make_new_user(int)     # 类型检查器会报错：type[int] 不是 type[User] 的子类型
```

**关键结论**：`int` 注解描述实例，`type[int]` 注解描述类对象本身；`type[C]` 是协变的，子类的类对象可以赋值给父类的类对象注解。

---

## 4. 整数与其它类型的边界：布尔、浮点、字符串转换

`int` 与 `bool` 有特殊关系：`bool` 是 `int` 的子类，`True == 1`、`False == 0`。同时 `int()` 构造函数可以从字符串、浮点数等转换，工程中要小心其截断与异常行为。

```python
# bool 是 int 的子类
print(isinstance(True, int))   # True
print(True + True)             # 2
print(True == 1)               # True

# int() 转换
print(int("123"))       # 123
print(int(3.99))        # 3   —— 截断，不是四舍五入
print(int("  -42  "))   # -42 —— 允许前后空格

# 无法转换会抛 ValueError
# int("12.5")   # ValueError
# int("abc")    # ValueError

# 浮点转 int 也可以走 math.trunc/floor 等
import math
print(math.trunc(3.99))  # 3
print(math.floor(-3.1))  # -4
```

**关键结论**：`bool` 是 `int` 的子类，`int()` 转换对字符串严格、对浮点数截断，异常情况需要处理。

---

## 5. 工程级视角：类型注解工具链与运行时反思

工程师使用 `int` 注解时，真正的价值来自工具链：类型检查器（mypy / pyright）、IDE 补全、运行时 `get_type_hints()`、以及 `Annotated` 附带的元数据。下面演示如何在运行时读取注解，以及类型检查器的行为差异。

```python
from typing import get_type_hints, Annotated

def f(x: int) -> int:
    return x * 2

# 运行时读取注解
print(get_type_hints(f))
# {'x': <class 'int'>, 'return': <class 'int'>}

# Annotated 携带元数据
PositiveInt = Annotated[int, "must be > 0"]
print(PositiveInt.__metadata__)   # ('must be > 0',)
print(get_type_hints(f))          # 普通注解已剥离
```

**关键结论**：`int` 作为类型注解在运行时可通过 `get_type_hints()` 读取；`Annotated` 还能附带元数据，服务于框架（如 FastAPI、Pydantic）的运行时校验。

---

## 动手练习

**任务**：编写一个模块 `safe_int.py`，实现一个函数 `safe_int(s)`，要求：

1. 若 `s` 是 `int`，直接返回；
2. 若 `s` 是 `bool`，抛 `TypeError`（因为 `bool` 是 `int` 子类，容易被误判）；
3. 若 `s` 是可转换的字符串（如 `"42"`、`"  -7 "`），返回其对应的 `int`；
4. 若 `s` 是浮点数，先检查是否“数学上是整数”（例如 `3.0`），是则返回 `int`，否则抛 `ValueError`；
5. 其他情况抛 `ValueError`。

写好函数签名：

```python
def safe_int(s: object) -> int:
    ...
```

并写一个 `if __name__ == "__main__":` 的自测，覆盖下面用例：

```python
print(safe_int(5))        # 5
print(safe_int("42"))     # 42
print(safe_int(" -7 "))   # -7
print(safe_int(3.0))      # 3
# safe_int(True)          # 应抛 TypeError
# safe_int(3.14)          # 应抛 ValueError
# safe_int("abc")         # 应抛 ValueError
```

**延伸**：用 `mypy safe_int.py` 检查你的注解是否正确；尝试用 `Annotated[int, "non-bool"]` 把语义写进类型里，观察 `get_type_hints(..., include_extras=True)` 的输出。

```python
from typing import get_type_hints, Annotated

# 1. int 是类，3 是实例
print(type(3))                 # <class 'int'>

# 2. 任意精度
big = 10 ** 50
print(big)                     # 100000000000000000000000000000000000000000000000000

# 3. 类型注解
x: int = 5
def add(a: int, b: int) -> int:
    return a + b
print(add(1, 2))               # 3

# 4. type[int] 表示类对象本身
class User: ...
class ProUser(User): ...
def make(cls: type[User]) -> User:
    return cls()
print(type(make(User)))        # <class '__main__.User'>
print(type(make(ProUser)))     # <class '__main__.ProUser'>

# 5. int 与 bool、float、str
print(isinstance(True, int))   # True
print(int("123"))              # 123
print(int(3.99))               # 3

# 6. 运行时读取注解 + Annotated
PositiveInt = Annotated[int, "must be > 0"]
def f(v: int) -> int:
    return v
print(get_type_hints(f))                       # {'v': <class 'int'>, 'return': <class 'int'>}
print(PositiveInt.__metadata__)                # ('must be > 0',)
```

## py.type.float

# py.type.float：从零理解 Python 浮点数

## 一句话直觉

学 `float` 是因为：现实世界里的钱、温度、比例、速度和概率几乎都不是整数，而 Python 默认用浮点数来承载这些“任意实数”的近似值。

---

## 1. 什么是 float：二进制里的“小数”

`float`（floating-point number，浮点数）是 Python 中表示实数的内置类型。你可以把它理解为“用科学计数法存下来的小数”：

```python
# float 是 Python 内置类型
x = 3.14
y = -0.001
z = 2.0

print(type(x))        # <class 'float'>
print(type(z))        # <class 'float'>，注意 2.0 是 float，不是 int
print(type(2))        # <class 'int'>，整数是 int
```

关键结论：**只要带小数点，或使用科学计数法，或参与除法 `/`，结果通常就是 `float`。**

```python
print(1 / 2)          # 0.5，除法总是产生 float
print(4 / 2)          # 2.0，即使能整除，结果也是 float
print(1e3)            # 1000.0，科学计数法
try:
    print(1 / 0)
except ZeroDivisionError as e:
    print("错误:", e)
```

---

## 2. 精度问题：0.1 + 0.2 != 0.3

这是浮点数最重要的工程属性：它用有限二进制位（bit）近似存储十进制小数，因此很多小数无法被精确表示。

```python
print(0.1 + 0.2)              # 0.30000000000000004
print(0.1 + 0.2 == 0.3)       # False

from decimal import Decimal
print(Decimal("0.1") + Decimal("0.2"))  # 0.3，精确十进制计算
```

关键结论：**不要直接用 `==` 比较两个浮点数是否“相等”，应该比较它们是否足够接近。**

```python
import math

a = 0.1 + 0.2
b = 0.3

print(math.isclose(a, b))     # True，默认相对误差 1e-9
print(abs(a - b) < 1e-9)      # True，手动设置容差（tolerance）
```

---

## 3. 特殊值：inf、-inf、nan

浮点数可以表示无穷大和“非数字”。工程中遇到除零、溢出、无效数学运算时要认识它们。

```python
import math

inf = float("inf")
print(inf)                    # inf
print(-inf)                   # -inf
print(float("nan"))           # nan

# nan 不等于任何值，包括它自己
nan = float("nan")
print(nan == nan)             # False
print(math.isnan(nan))        # True，判断 nan 用这个

# 判断有限/无限
print(math.isfinite(3.14))    # True
print(math.isinf(inf))        # True
```

关键结论：**判断 `nan` 必须用 `math.isnan()`；判断无穷用 `math.isinf()`；不要用 `==`。**

---

## 4. 类型转换与格式化：int、str、f-string

`float()` 可以把字符串或整数转成浮点数；`int()` 会截断小数部分（不是四舍五入）；`round()` 才是四舍五入。

```python
# 转换
print(float("3.14"))          # 3.14
print(float(7))               # 7.0
print(int(3.99))              # 3，直接截断
print(round(3.99))            # 4，四舍五入

# 格式化
value = 3.1415926
print(f"{value:.2f}")         # 3.14，保留两位小数
print(f"{value:10.3f}")       # '     3.142'，宽度 10、保留三位
print(format(value, ".0f"))   # '3'，格式化函数
```

关键结论：**显示金额、报表等场景用 f-string 的 `:.2f` 控制小数位，而不是直接 print 原始值。**

---

## 5. 工程中的 float：类型提示与边界

现代 Python 工程会用 type hints（类型提示）表达函数期望 `float`，工具如 mypy、IDE 会做静态检查。注意：Python 运行时不会强制检查类型。

```python
# 类型提示：参数与返回值都可能是 float
def surface_area_of_cube(edge_length: float) -> float:
    return 6 * edge_length ** 2

print(surface_area_of_cube(2.5))   # 37.5

# 运行时不会强制检查，传 int 也能跑
print(surface_area_of_cube(3))     # 54
```

关键结论：**类型提示是给人和工具看的，运行时并不阻止你传错类型；但对协作和可维护性极其重要。**

比如金额或高精度场景，应改用 `decimal.Decimal`：

```python
from decimal import Decimal

price = Decimal("19.99")
count = Decimal("3")
print(price * count)          # 59.97，精确
```

---

## 结尾：动手练习

写一个小程序 `tip_calculator.py`，要求：

1. 定义函数 `split_bill(total: float, people: int, tip_rate: float) -> float`，计算每人应付金额（含小费）。
2. 用 `Decimal` 再实现一个 `split_bill_exact`，比较两者在 `0.1 + 0.2` 类场景下的差异。
3. 用 `math.isclose` 验证两个结果是否接近。
4. 用 f-string 输出每人金额，保留两位小数。
5. 输入 `total=100.0, people=3, tip_rate=0.15`，打印结果。

示例输出应类似：

```
每人应付（float）: 38.33
每人应付（Decimal）: 38.33
两者是否接近: True
```

完成后思考：如果 total 是 `0.1 + 0.2`，结果会怎样？为什么工程中金额更倾向用 `Decimal`？

```python
import math
from decimal import Decimal


def split_bill(total: float, people: int, tip_rate: float) -> float:
    """用 float 计算每人应付含小费金额。"""
    return total * (1 + tip_rate) / people


def split_bill_exact(total: str, people: int, tip_rate: str) -> Decimal:
    """用 Decimal 做精确十进制计算，输入用字符串避免 float 污染。"""
    total_d = Decimal(total)
    tip_d = Decimal(tip_rate)
    return total_d * (Decimal(1) + tip_d) / Decimal(people)


# 普通场景
float_result = split_bill(100.0, 3, 0.15)
decimal_result = split_bill_exact("100.0", 3, "0.15")

print(f"每人应付（float）: {float_result:.2f}")
print(f"每人应付（Decimal）: {decimal_result:.2f}")
print("两者是否接近:", math.isclose(float_result, float(decimal_result)))

# 经典精度陷阱：0.1 + 0.2
print("0.1 + 0.2 =", 0.1 + 0.2)
print("是否等于 0.3:", 0.1 + 0.2 == 0.3)
print("使用 isclose 判断:", math.isclose(0.1 + 0.2, 0.3))
```

## py.type.bool

# py.type.bool：从零到工程级的布尔类型讲义

## 一句话直觉

`bool`（布尔值）是 Python 里最小的“决策单元”——它只有 `True` 和 `False` 两个值，却是所有条件判断、循环控制、类型注解和工程逻辑的起点。学会它，你才能让程序“会思考”。

---

## 1. 什么是 bool：Python 的“真/假”类型

`bool` 是 Python 的内置类型（built-in type），只有两个实例：`True` 和 `False`。它们不是字符串，也不是数字 1 和 0 的别名——虽然底层确实是 `int` 的子类。

关键结论：
- `True` 和 `False` 是关键字，首字母必须大写。
- `bool` 是 `int` 的子类：`True == 1`，`False == 0`。
- 用 `type(x) is bool` 可以精确判断一个值是不是布尔类型。

```python
# 布尔值的基本用法
print(True)              # True
print(False)             # False
print(type(True))        # <class 'bool'>

# bool 是 int 的子类
print(True == 1)         # True
print(False == 0)        # True
print(isinstance(True, int))  # True

# 精确判断布尔类型
x = True
print(type(x) is bool)   # True
```

---

## 2. 真值测试：哪些值会被当成 False？

Python 在 `if`、`while`、`and`、`or`、`not` 等场景中会自动把任意对象“转换”成布尔值，这叫真值测试（truthiness / truth value testing）。

关键结论：
- 以下值被视为假（falsy）：`False`、`None`、`0`、`0.0`、`0j`、`""`、`[]`、`()`、`{}`、`set()`。
- 其他几乎所有值都被视为真（truthy）。
- 可以用内置函数 `bool()` 显式转换。

```python
# 显式转换
def show(v):
    print(f"{v!r:>8} -> {bool(v)}")

for v in [True, False, None, 0, 1, -1, 0.0, "", "a", [], [0], {}, {1: 2}]:
    show(v)

# 真值测试在 if 中自动生效
name = ""
if not name:
    print("名字为空，视为 False")
```

---

## 3. 布尔运算：and / or / not 的短路行为

`and`、`or`、`not` 是布尔运算（boolean operations），但它们返回的不一定是 `bool`——`and` 和 `or` 返回的是参与运算的某个操作数，这叫短路求值（short-circuit evaluation）。

关键结论：
- `x and y`：若 `x` 为假，返回 `x`；否则返回 `y`。
- `x or y`：若 `x` 为真，返回 `x`；否则返回 `y`。
- `not x`：总是返回 `bool`。
- 利用短路可以写出安全代码，例如 `name and name.upper()`。

```python
# 短路行为演示
print(0 and "ok")        # 0
print(1 and "ok")        # ok
print("" or "默认值")     # 默认值
print("hi" or "默认值")   # hi
print(not 0)             # True
print(not "a")           # False

# 工程技巧：安全访问
name = ""
print(name and name.upper())  # 输出空字符串，不会报错
```

---

## 4. 类型注解中的 bool

Python 的类型注解（type hints）不会在运行时强制生效，但静态类型检查器（如 mypy、pyright）和 IDE 会用它帮你提前发现错误。`bool` 是最常见的注解类型之一。

关键结论：
- 函数参数和返回值都可以标注 `bool`。
- `bool` 和 `int` 在类型系统中不兼容，不要把 `int` 传给期望 `bool` 的参数。
- 从 Python 3.11 起可用 `typing.reveal_type()` 调试推断类型。

```python
# 类型注解示例
def is_even(n: int) -> bool:
    """判断整数是否为偶数"""
    return n % 2 == 0

print(is_even(4))   # True
print(is_even(7))   # False

# reveal_type 帮助查看静态推断类型
from typing import reveal_type
x: bool = True
reveal_type(x)      # 静态检查器会提示 bool
```

---

## 5. 工程级要点与常见坑

在真实工程中，`bool` 常常和配置、API、序列化打交道，容易踩坑。

关键结论：
- `bool` 是 `int` 的子类，所以 `1 == True`，字典里 `{1: "a", True: "b"}` 会互相覆盖。
- JSON 序列化时 `True` 变成 `true`，反序列化回来仍是 `bool`。
- 不要把 `"False"` 字符串当成 `False`——它是真值。
- 需要严格区分时，用 `is True` / `is False` 而不是 `==`。

```python
# 坑 1：bool 与 int 的相等性
d = {1: "one", True: "true"}
print(d)  # {1: 'true'}，因为 True == 1 覆盖了键

# 坑 2：字符串 "False" 是真值
flag = "False"
if flag:
    print("字符串 'False' 被视为 True")

# 坑 3：JSON 中的布尔
import json
print(json.dumps({"ok": True}))      # {"ok": true}
print(json.loads('{"ok": false}'))   # {'ok': False}
```

---

## 动手练习

写一个函数 `parse_flag(value, default=False) -> bool`，把常见的配置值安全地转成布尔：

- 输入 `True` / `False` 直接返回。
- 输入字符串 `"true"`、`"1"`、`"yes"`、`"on"`（忽略大小写）返回 `True`。
- 输入字符串 `"false"`、`"0"`、`"no"`、`"off"` 返回 `False`。
- 其他情况返回 `default`。

要求：
1. 给函数加上类型注解。
2. 用 `if __name__ == "__main__":` 写几组测试。
3. 思考：如果传入 `1` 或 `0`，应该返回什么？在代码注释里说明你的设计决定。

```python
def parse_flag(value, default=False):
    """把常见配置值转换为布尔。"""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        v = value.strip().lower()
        if v in {"true", "1", "yes", "on"}:
            return True
        if v in {"false", "0", "no", "off"}:
            return False
    return default

if __name__ == "__main__":
    assert parse_flag(True) is True
    assert parse_flag("YES") is True
    assert parse_flag("off") is False
    assert parse_flag("unknown", default=True) is True
    print("全部通过")
```

---

## 小结

| 要点 | 说明 |
| --- | --- |
| 类型 | `bool`，只有 `True` / `False` |
| 继承 | `bool` 是 `int` 的子类 |
| 真值 | 空值、0、None 等为假 |
| 运算 | `and` / `or` 短路，`not` 返回 bool |
| 注解 | 参数和返回值可标 `bool` |
| 工程 | 注意 `1 == True`、字符串 `"False"` 等坑 |

```python
from typing import reveal_type


def is_even(n: int) -> bool:
    """判断整数是否为偶数。"""
    return n % 2 == 0


def parse_flag(value, default: bool = False) -> bool:
    """把常见配置值转换为布尔。"""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        v = value.strip().lower()
        if v in {"true", "1", "yes", "on"}:
            return True
        if v in {"false", "0", "no", "off"}:
            return False
    return default


if __name__ == "__main__":
    # 基础布尔值
    print(True, False)
    print(type(True))
    print(True == 1, False == 0)

    # 真值测试
    for v in [0, 1, "", "a", [], [0], None]:
        print(repr(v), "->", bool(v))

    # 短路运算
    print(0 and "ok")
    print(1 and "ok")
    print("" or "默认值")

    # 类型注解函数
    print(is_even(4), is_even(7))

    # 解析布尔配置
    assert parse_flag(True) is True
    assert parse_flag("YES") is True
    assert parse_flag("off") is False
    assert parse_flag("unknown", default=True) is True
    print("全部通过")
```

## py.type.none

# `None` 与 `NoneType`：Python 里"什么都没有"的正式类型

> 一句话直觉：`None` 不是 `0`、不是 `""`、不是 `False`，它是 Python 用来表示"这里没有值"的唯一对象，而 `NoneType` 就是它的类型。

本讲是我们类型系统的起点。你会先认识 `None` 这个值本身，再认识它的类型 `NoneType`，最后看它在函数返回值、类型注解（type hint）与静态检查（static type checking）中扮演的角色。

---

## 1. `None` 是什么：唯一的"空值"对象

在 Python 中，`None` 是一个**单例**（singleton）对象：整个解释器里只有一个 `None` 实例。它常用来表示"无返回值"、"尚未设置"、"缺失"。

`None` 是关键字（keyword），不能重新赋值，所以 `None = 5` 会直接报 `SyntaxError`。这一点和我们常写的普通变量不同。

```python
# 1. None 是单例：任意两个 None 都是同一个对象
print(None is None)          # True
print(None == None)          # True，但规范写法是用 is

# 2. 判断是否为 None，永远用 is / is not
def f(x):
    if x is None:            # 推荐
        return "missing"
    return x

print(f(None))               # missing
print(f(0))                  # 0（0 不是 None！）
```

关键结论：**比较 `None` 用 `is`，不要用 `==`**。因为 `==` 可以被重载，而 `is` 比较的是身份（identity），对单例最安全。

---

## 2. `NoneType`：`None` 的类型

`None` 的类型叫 `NoneType`。在 Python 3.10 之前你必须用 `type(None)` 拿到它；从 3.10 起，标准库 `types` 模块直接提供了 `types.NoneType`。

```python
import types

print(type(None))                    # <class 'NoneType'>
print(type(None) is types.NoneType)  # True（3.10+）

# 布尔语境下，None 是假值（falsy）
print(bool(None))                    # False
```

关键结论：`NoneType` 只有一个实例，就是 `None`。你**不应该**写 `NoneType()` 去构造新对象。

---

## 3. 函数里的 `None`：默认返回与显式返回

任何没有显式 `return` 的函数，或者只写了 `return` 的函数，都会返回 `None`。这就是为什么类型注解里 `-> None` 表示"这个函数不返回有用的值"。

```python
def log(msg):
    print(msg)          # 没有 return

r = log("hi")           # 打印 hi
print(r)                # None

# 显式声明的等价写法
def log2(msg) -> None:
    print(msg)
```

关键结论：`-> None` 不等于"函数不能写 return"，它表达的是"调用者不应依赖返回值"。

---

## 4. 类型注解中的 `None`：`Optional` 与 `X | None`

当参数"可能是某类型，也可能缺失"时，我们用 `Optional[X]` 或 `X | None` 表达。注意：`Optional[X]` **不是**"可选参数"的意思，而是"值可以是 X 或 None"。

```python
from typing import Optional

def greet(name: Optional[str]) -> str:
    if name is None:
        return "Hello, stranger!"
    return f"Hello, {name}!"

print(greet(None))       # Hello, stranger!
print(greet("Ada"))      # Hello, Ada!

# Python 3.10+ 推荐写法
def greet2(name: str | None) -> str:
    return "Hello, stranger!" if name is None else f"Hello, {name}!"
```

关键结论：`str | None` 和 `Optional[str]` 等价；`None` 在注解里是合法成员，但**运行时解释器不会强制检查**它。

---

## 5. 静态检查视角：谁在帮你抓错

Python 运行时不执行类型注解，所以写错了也不会立刻崩。真正的检查由 mypy、pyright、IDE 等工具完成。学会用 `reveal_type` 观察推断结果非常有用。

```python
from typing import Optional

def maybe_int(flag: bool) -> Optional[int]:
    return 1 if flag else None

x = maybe_int(True)
reveal_type(x)          # 静态检查器会报：int | None

if x is not None:
    reveal_type(x)      # 收窄（narrowing）后为 int
```

关键结论：类型检查器会根据 `is None` 分支做**类型收窄**（narrowing），让你的代码在此分支里按非 `None` 处理更安全。

```python
"""演示 None / NoneType 的核心用法。直接 `python examples.py` 即可运行。"""

import types
from typing import Optional


def find_user(uid: int) -> Optional[str]:
    """返回用户名；找不到就返回 None。"""
    users = {1: "Ada", 2: "Linus"}
    return users.get(uid)   # dict.get 找不到时天然返回 None


def log(msg: str) -> None:
    """只打印，不返回值。"""
    print(f"[log] {msg}")


if __name__ == "__main__":
    # 1. None 是单例，判断用 is
    name = find_user(1)
    missing = find_user(999)
    print(name, missing)                      # Ada None
    print(missing is None)                    # True

    # 2. None 的类型是 NoneType
    print(type(None))                         # <class 'NoneType'>
    print(type(None) is types.NoneType)       # True

    # 3. 无返回值的函数隐式返回 None
    print(log("hello"))                       # 打印 [log] hello，再打印 None

    # 4. Optional / X | None 表示可空类型
    def greet(n: str | None) -> str:
        return "Hello, stranger!" if n is None else f"Hello, {n}!"

    print(greet(None))                        # Hello, stranger!
    print(greet("Grace"))                     # Hello, Grace!
```


---

## 本课题目

### single_choice · None



- [A] <class 'int'>
- [B] <class 'float'>
- [C] <class 'str'>
- [D] <class 'number'>

**参考答案**：0

**解析**：整数 10 在 Python 中的类型是 int，因此 type(x) 返回 <class 'int'>。

### single_choice · None



- [A] isinstance(n, int)
- [B] type(n) == int
- [C] n.type() == 'int'
- [D] n is int

**参考答案**：0

**解析**：isinstance(n, int) 是判断对象是否为 int 类型的标准方式；type(n) == int 也常用于精确比较，但题目中最佳实践是 isinstance。

### single_choice · None



- [A] float
- [B] int
- [C] str
- [D] bool

**参考答案**：0

**解析**：Python 中 / 运算符执行真除法，即使两个操作数都是整数，结果也是 float。

### single_choice · None



- [A] a
- [B] b
- [C] c
- [D] d

**参考答案**：0

**解析**：a 是整数字面量，类型为 int；b 是 float，c 是 str，d 是 bool。

### single_choice · None



- [A] int 类型是不可变的
- [B] int 类型是可变的
- [C] int 类型只能存储 32 位整数
- [D] int 类型不能进行算术运算

**参考答案**：0

**解析**：Python 的 int 是不可变类型，创建后值不能修改；它可以表示任意精度整数，并支持算术运算。

### single_choice · None



- [A] True
- [B] False
- [C] None
- [D] 报错

**参考答案**：0

**解析**：5 是 int 类型的实例，因此 isinstance(5, int) 返回 True。

### single_choice · None



- [A] 5 + 3
- [B] 5 / 3
- [C] 5.0 + 3
- [D] 5 + '3'

**参考答案**：0

**解析**：5 + 3 是两个整数相加，结果为 int；5 / 3 结果为 float；5.0 + 3 结果为 float；5 + '3' 会报 TypeError。

### single_choice · None



- [A] 没有限制，取决于内存
- [B] 2**31 - 1
- [C] 2**63 - 1
- [D] 2**127 - 1

**参考答案**：0

**解析**：Python 3 的 int 是任意精度整数，没有固定最大值，只受可用内存限制。

### single_choice · None



- [A] 3
- [B] 4
- [C] 3.99
- [D] 报错

**参考答案**：0

**解析**：int() 将浮点数转换为整数时会截断小数部分，而不是四舍五入，因此结果为 3。

### single_choice · None



- [A] <class 'int'> <class 'float'> <class 'complex'>
- [B] <class 'int'> <class 'float'> <class 'float'>
- [C] <class 'float'> <class 'float'> <class 'complex'>
- [D] <class 'int'> <class 'int'> <class 'complex'>

**参考答案**：0

**解析**：0 是 int，0.0 是 float，0j 是 complex，因此输出分别为对应类型。

### single_choice · None



- [A] isinstance 能正确处理子类，通常更推荐
- [B] type(x) == int 能正确处理子类
- [C] 两者完全等价
- [D] isinstance 不能用于 int

**参考答案**：0

**解析**：isinstance 会考虑继承关系，例如 bool 是 int 的子类，因此 isinstance(True, int) 为 True，而 type(True) == int 为 False。

### single_choice · None



- [A] abs(-5)
- [B] round(3.7)
- [C] len([1,2,3])
- [D] 以上都是

**参考答案**：3

**解析**：abs(-5) 返回 5，round(3.7) 返回 4，len([1,2,3]) 返回 3，这些结果都是 int 类型。

### single_choice · None



- [A] <class 'float'>
- [B] <class 'int'>
- [C] <class 'double'>
- [D] <class 'decimal'>

**参考答案**：0

**解析**：3.0 是浮点数，类型为 float，因此输出 <class 'float'>。

### single_choice · None



- [A] '123'
- [B] 123.0
- [C] True
- [D] 123

**参考答案**：3

**解析**：123 是整数字面量，类型为 int；'123' 是字符串，123.0 是浮点数，True 是 bool（bool 是 int 的子类，但通常单独看待）。

### single_choice · None



- [A] bool 是 int 的子类
- [B] int 是 bool 的子类
- [C] 两者完全无关
- [D] bool 等价于 str

**参考答案**：0

**解析**：Python 中 bool 是 int 的子类，True 和 False 分别对应 1 和 0，但通常不把布尔值当作普通整数使用。

### single_choice · None



- [A] int, 42
- [B] str, '42'
- [C] float, 42.0
- [D] int, '42'

**参考答案**：0

**解析**：int('42') 将字符串转换为整数 42，因此 n 的类型是 int，值是 42。

### single_choice · None



- [A] int
- [B] float
- [C] str
- [D] bool

**参考答案**：0

**解析**：整除运算符 // 对两个整数运算时返回整数，因此 a 的类型是 int。

### single_choice · None



- [A] int
- [B] str
- [C] float
- [D] 语法错误

**参考答案**：0

**解析**：Python 允许在数字字面量中使用下划线作为分隔符，1_000_000 仍然是 int 类型。

### single_choice · None



- [A] int('100')
- [B] int(100.9)
- [C] int(True)
- [D] 以上都可以

**参考答案**：3

**解析**：int() 可以将字符串、浮点数、布尔值等转换为整数，因此以上方式都可以创建整数对象。

### single_choice · None



- [A] int
- [B] long
- [C] float
- [D] overflow

**参考答案**：0

**解析**：Python 3 中 int 可以表示任意大小的整数，不再区分 long，因此 2 ** 100 仍然是 int。

### single_choice · None



- [A] True
- [B] False
- [C] 抛出异常
- [D] 取决于操作系统

**参考答案**：1

**解析**：由于二进制浮点数无法精确表示 0.1 和 0.2，0.1 + 0.2 的结果约为 0.30000000000000004，与 0.3 不相等，因此返回 False。

### single_choice · None



- [A] a - b == 0
- [B] abs(a - b) < 1e-9
- [C] round(a) == round(b)
- [D] a is b

**参考答案**：1

**解析**：浮点数比较应采用容差方式，abs(a - b) < 容差 是常见做法。直接 == 可能因为精度误差失败，round 会丢失精度，is 比较的是对象身份。

### multi_choice · None



- [A] float 遵循 IEEE 754 双精度标准
- [B] 0.1 + 0.2 != 0.3 是正常现象
- [C] float 可以精确表示所有十进制小数
- [D] 可以使用 decimal 模块进行高精度十进制运算
- [E] float('inf') 与 float('nan') 都是合法的浮点值

**参考答案**：[0, 1, 3, 4]

**解析**：float 是二进制双精度浮点，无法精确表示多数十进制小数；decimal 提供精确十进制支持；inf 和 nan 是合法的特殊浮点值。选项 C 说法错误。

### multi_choice · None



- [A] float('inf')
- [B] 1e400
- [C] 1.0 / 0.0
- [D] float('nan')
- [E] math.inf

**参考答案**：[0, 1, 4]

**解析**：float('inf') 和 math.inf 都是无穷大常量，1e400 因超出范围字面量解析为 inf。1.0/0.0 抛出 ZeroDivisionError，float('nan') 是非数，不表示无穷大。

### multi_choice · None



- [A] float('abc')
- [B] float('1e400')
- [C] 1.0 / 0.0
- [D] int(float('inf'))
- [E] float('3.14')

**参考答案**：[0, 1, 2, 3]

**解析**：float('abc') 抛 ValueError；float('1e400') 超出范围抛 OverflowError；除以零抛 ZeroDivisionError；int(inf) 抛 OverflowError。float('3.14') 正常返回。

### multi_choice · None



- [A] 1 == 1.0 的结果为 True
- [B] 1.0 == 1 的结果为 True
- [C] 10**20 == float(10**20) 一定为 True
- [D] 0.5 可以精确表示
- [E] int(1.9) == 1

**参考答案**：[0, 1, 3, 4]

**解析**：Python 中 int 与 float 比较时会把 int 转换为 float（或做精确比较）；1==1.0 为 True；0.5 可精确表示；int(1.9) 截断为 1。当整数超出浮点可精确表示范围时比较可能不等，因此 C 不一定为 True。

### fill_blank · None



**参考答案**：["isclose", "isclose(a, b)", "isclose(a,b)"]

**解析**：math.isclose 用于判断两个浮点数在容差范围是否近似相等，此处 a 与 b 相差约 5.5e-17，在默认容差内返回 True。

### fill_blank · None



**参考答案**：["isnan", "isnan(x)", "isnan(x)"]

**解析**：math.isnan 是标准库中用于检测 NaN 的函数；不能使用 x != x 之外的其他错误方式，也不应依赖 == 比较。

### fill_blank · None



**参考答案**：["inf", "Inf", "Infinity", "infinity"]

**解析**：float 解析字符串 'inf'（大小写不敏感，也接受 'Infinity'）得到正无穷大；math.inf 同样是无穷大常量。

### code_reading · None



**参考答案**：分别输出：True、False、True。因为 abs(x-0.3) 足够小；直接相等比较为 False；math.isclose 在默认容差下返回 True。

**解析**：该代码对比了三种浮点比较方式：容差比较、直接 == 比较、math.isclose。前两者行为差异正是浮点精度问题的核心表现。

### code_reading · None



**参考答案**：nan、nan、0.0。inf 减 inf 得 nan，inf 乘 0 得 nan，1 除以 inf 得 0.0。

**解析**：IEEE 754 规定：inf-inf 与 inf*0 是未定义形式，结果为 NaN；有限数除以 inf 结果为 0。

### scenario · None



**解析**：根本原因是二进制浮点无法精确表示多数十进制小数，累加会产生误差。应改用 decimal.Decimal（字符串构造）做金额运算，或在需要保留精度的场景使用整数分单位，并统一舍入策略。

### single_choice · None



- [A] IEEE 754 双精度浮点数
- [B] IEEE 754 单精度浮点数
- [C] 定点十进制数
- [D] 任意精度有理数

**参考答案**：0

**解析**：Python 的 float 对应 C 的 double，遵循 IEEE 754 双精度（64 位）浮点格式，因此存在二进制浮点精度问题。

### scenario · None



**解析**：浮点运算结果受编译/优化与运行时细节影响，直接 == 比较不可靠。应使用 math.isclose 或 pytest.approx 等带容差的比较；若确实要求精确十进制，应改用 Decimal。加打印改变条件时可能触发常量折叠差异，进一步暴露 == 的脆弱性。

### single_choice · None



- [A] True
- [B] False
- [C] 抛出 ValueError
- [D] 取决于 Python 版本

**参考答案**：1

**解析**：NaN 的语义规定它不等于任何值，包括它自己。判断 NaN 应使用 math.isnan()。

### single_choice · None



- [A] 1e400 会创建超大浮点数，不等于 inf
- [B] 1e400 得到 inf（无穷大）
- [C] 1e400 抛出 OverflowError
- [D] 1e400 被当作字符串处理

**参考答案**：1

**解析**：字面量 1e400 超出双精度范围，会直接解析为 inf；而 float('1e400') 则会抛出 OverflowError，两者行为不同。

### single_choice · None



- [A] 4 和 4
- [B] 3 和 4
- [C] 3 和 3
- [D] 4 和 3

**参考答案**：1

**解析**：int() 直接截断小数部分得到 3；round() 使用银行家舍入，3.5 舍入到最近的偶数 4，因此结果是 3 和 4。

### single_choice · None



- [A] 0.3
- [B] 0.30000000000000004
- [C] 0.29999999999999999
- [D] 3

**参考答案**：1

**解析**：0.1 的三倍在二进制浮点加法中产生累积误差，结果为 0.30000000000000004，是 IEEE 754 双精度的典型表现。

### single_choice · None



- [A] math
- [B] decimal
- [C] random
- [D] statistics

**参考答案**：1

**解析**：decimal 模块提供十进制浮点运算，可以按需控制精度，避免二进制浮点误差，适合金额等精确计算场景。

### single_choice · None



- [A] 1000.5
- [B] 抛出 ValueError，因为下划线不合法
- [C] 1000.0
- [D] 字符串 '1_000.5'

**参考答案**：0

**解析**：Python 允许在数字字面量中使用下划线作为分隔符，float() 解析字符串时同样支持下划线分隔，因此得到 1000.5。

### single_choice · None



- [A] 两者完全等价
- [B] isclose 考虑相对/绝对容差，更适合浮点比较
- [C] isclose 只能用于整数
- [D] a == b 更精确，应该优先使用

**参考答案**：1

**解析**：math.isclose 默认使用相对容差和绝对容差进行近似比较，能正确处理浮点误差，是推荐做法；== 在浮点上容易误判。

### single_choice · None



- [A] 0 和 1
- [B] True 和 False
- [C] "True" 和 "False"
- [D] true 和 false

**参考答案**：1

**解析**：Python 的 bool 类型只有两个实例 True 和 False（首字母大写）；0 和 1 是整数，字符串 "True" 和 "False" 是 str，小写的 true/false 在 Python 中不是内置常量。

### single_choice · None



- [A] True, True, True, True
- [B] False, False, False, False
- [C] False, True, False, True
- [D] True, False, True, False

**参考答案**：1

**解析**：0、空字符串、空列表、None 都属于「假值」(falsy)，bool() 转换后均为 False。

### single_choice · None



- [A] True
- [B] False
- [C] 报错
- [D] -1

**参考答案**：0

**解析**：只有 0 才是假值，任何非零整数（包括负数如 -1）都是真值，因此 bool(-1) 为 True。

### single_choice · None



- [A] if x == "": ...
- [B] if x is None: ...
- [C] if x: ...
- [D] if not x: ...

**参考答案**：2

**解析**：if x: 利用真值判断，x 为 None、""、0、空容器时都为假，否则为真，正好满足「非 None 且非空」的需求。

### multi_choice · None



- [A] bool([0])
- [B] bool("0")
- [C] bool([])
- [D] bool(-0.0)
- [E] bool((1,))

**参考答案**：[0, 1, 4]

**解析**：[0] 是非空列表，"0" 是非空字符串，(1,) 是非空元组，均为 True；[] 是空列表，-0.0 等于 0 为假。

### multi_choice · None



- [A] isinstance(True, int) 返回 True
- [B] True + 1 的结果是 2
- [C] False 在数值上等于 0
- [D] bool 是 int 的父类
- [E] True * 5 的结果是 5

**参考答案**：[0, 1, 2, 4]

**解析**：bool 是 int 的子类（不是父类），True 数值为 1，False 为 0，因此 True+1=2、True*5=5 均成立；选项 D 说反了继承关系。

### multi_choice · None



- [A] None
- [B] 0.0
- [C] "False"
- [D] set()
- [E] print

**参考答案**：[0, 1, 3]

**解析**：None、0.0、空集合 set() 都是假值；"False" 是非空字符串为真；函数对象 print 也是真值。

### fill_blank · None



**参考答案**：["3"]

**解析**：False 数值上等于 0，因此 False + 3 = 0 + 3 = 3，结果为整数 3。

### fill_blank · None



**参考答案**：["False", "false"]

**解析**：浮点数 0.0 等于 0，属于假值，因此 bool(0.0) 返回 False。

### code_reading · None



**参考答案**：[]

**解析**：and 遇到第一个假值就短路并返回该值。[] 是空列表（假值），因此整个表达式返回 []，不会返回右侧的 [1, 2]，打印空列表 []。

### code_reading · None



**参考答案**：default

**解析**：x 为空字符串（假值），or 返回第二个操作数 "default"，因此打印 default。这是设置默认值的常见写法。

### scenario · None



**解析**：or 会把所有假值（包括合法的端口 0 和非 None 值）当作「未设置」，导致用户显式传 0 时被错误替换为 8080。稳妥写法应显式判断：port = 8080 if user_port is None else user_port。

### single_choice · None



- [A] 它们是完全不同的对象，不能比较
- [B] True == 1 为 True，因为 bool 是 int 的子类
- [C] True == 1 为 False
- [D] True 是 1 的字符串形式

**参考答案**：1

**解析**：bool 是 int 的子类，True 等价于整数 1，False 等价于 0，因此 True == 1 返回 True，且 isinstance(True, int) 为 True。

### single_choice · None



- [A] True
- [B] 2
- [C] TypeError
- [D] False

**参考答案**：1

**解析**：因为 True 在数值上等于 1，True + True 相当于 1 + 1 = 2，结果是 int 类型 2。

### single_choice · None



- [A] 0, "0", [], {}
- [B] 0, "", [], {}
- [C] None, "None", 0
- [D] False, " ", [], 0

**参考答案**：1

**解析**：0、空字符串 ""、空列表 []、空字典 {} 都是假值。"0"、"None"、" " 是非空字符串，均为真值。

### single_choice · None



- [A] bool 是 float 的子类
- [B] bool 不能被转换成整数
- [C] bool 是 int 的子类，True 与 1、False 与 0 数值相等
- [D] bool 可以有三个取值

**参考答案**：2

**解析**：bool 继承自 int，只有 True 和 False 两个实例，数值上分别等于 1 和 0，可参与算术运算。

### single_choice · None



- [A] True
- [B] False
- [C] 报错
- [D] None

**参考答案**：0

**解析**：bool() 只判断字符串是否为空。"False" 是非空字符串，因此为 True，这会与字符串内容"False"形成常见误解。

### single_choice · None



- [A] and 和 or 总是返回 True 或 False
- [B] and 返回最后一个为真的操作数或第一个假值
- [C] or 一定返回布尔类型
- [D] and 会先计算右侧再计算左侧

**参考答案**：1

**解析**：Python 的 and / or 返回的是操作数本身，而不是强制转成 bool。a and b 当 a 为假时返回 a，否则返回 b；所以不一定返回布尔值。

### single_choice · None



- [A] True
- [B] False
- [C] 5
- [D] 3

**参考答案**：2

**解析**：3 为真，and 返回第二个操作数 5。这里返回值是 int 5，而不是 bool。

### single_choice · None



- [A] 0
- [B] "hello"
- [C] True
- [D] False

**参考答案**：1

**解析**：0 为假，or 返回第二个操作数 "hello"。or 在左侧为假时返回右侧值。

### single_choice · None



- [A] None 表示数字 0
- [B] None 是一个特殊的单例对象，表示“没有值”
- [C] None 等价于空字符串 ""
- [D] None 是一个未定义的名字，使用会报 NameError

**参考答案**：1

**解析**：None 是 Python 中唯一的 NoneType 类型对象，用来表示“无值/缺失”，它不是 0，也不是空字符串，更不是未定义名字。None 是内置常量，可直接使用。

### single_choice · None



- [A] True 和 True
- [B] True 和 False
- [C] False 和 True
- [D] False 和 False

**参考答案**：1

**解析**：x 正是 None，所以 `x is None` 为 True；None 不等于数字 0，所以 `x == 0` 为 False。两者本来也不相等。

### multi_choice · None



- [A] `None is None` 为 True
- [B] `None == None` 为 True
- [C] `None is 0` 为 True
- [D] `bool(None)` 为 False

**参考答案**：[0, 1, 3]

**解析**：None 是单例，与自身身份和相等比较都为 True；`None is 0` 为 False，因为二者不是同一对象；`bool(None)` 为 False。

### multi_choice · None



- [A] 函数只需执行副作用、不需要返回有用结果的函数
- [B] 列表的原地修改方法如 append、sort
- [C] 表示操作失败或没有找到结果时的“无值”标记
- [D] 计算两个数之和并返回结果的函数

**参考答案**：[0, 1, 2]

**解析**：None 常用于无返回值、原地操作返回值、以及“无结果/失败”的表示。求和函数应返回具体数值，不是 None。

### fill_blank · None



**参考答案**：["is", "is not", "=="]

**解析**：推荐使用身份运算符 `is` 判断是否为 None；`is not` 用于判断不是 None；`==` 也可但不如 `is` 推荐。

### fill_blank · None



**参考答案**：["NoneType", "NoneType()", "type(None)", "<class 'NoneType'>"]

**解析**：None 的类型是 NoneType，可通过 `type(None)` 验证，输出 `<class 'NoneType'>`。

### code_reading · None



**参考答案**：True
True
False

**解析**：x 和 y 都引用同一个 None 单例，所以 `is` 与 `==` 都为 True；but `bool(None)` 为 False。

### code_reading · None



**参考答案**：None
[1, 2, 3]

**解析**：list.sort() 原地排序并返回 None，排序结果保存在原列表 a 中，因此 result 打印 None，a 打印排序后的列表。

### scenario · None



**解析**：“查不到”表示无值，应返回 None，而不是 0。0 可能是一个合法值（例如 id 或计数），无法与“查不到”区分。调用方用 `if user is None:` 判断即可。

### scenario · None



**解析**：应使用 None 表示无值，因为 0 是合法数值，空字符串是合法字符串，都会与“缺失”混淆。转换后用 `if v is not None:` 或 `if v is None:` 跳过缺失项。

### single_choice · None



- [A] if x = None:
- [B] if x is None:
- [C] if x === None:
- [D] if x.isNone():

**参考答案**：1

**解析**：`is` 是 Python 的身份比较运算符，`x is None` 是正确写法。`=` 是赋值，`===` 不是 Python 语法，None 也没有 isNone 方法。

### single_choice · None



- [A] 没有 return 语句的函数调用结果
- [B] 函数中 `return` 后面什么都没写时的返回结果
- [C] `print()` 的返回值
- [D] `len([])` 的返回值

**参考答案**：3

**解析**：`len([])` 返回整数 0。没有 return 的函数、`return` 后无值、以及 `print()` 都返回 None。

### single_choice · None



- [A] if x == None:
- [B] if x is None:
- [C] if not x:
- [D] if x == 0:

**参考答案**：1

**解析**：None 是单例，用 `is` 做身份比较最准确、最推荐。`not x` 对 0、空字符串等也会为真；`== None` 虽常能用，但不推荐，且可能被自定义 `__eq__` 干扰；`== 0` 则完全错误。

### single_choice · None



- [A] 报错
- [B] None
- [C] 0
- [D] 空字符串

**参考答案**：1

**解析**：函数体只有 pass，且没有 return 语句，函数默认返回 None，所以打印 None。

### single_choice · None



- [A] None 是关键字，不能被赋值覆盖
- [B] None 只有一个实例
- [C] `type(None)` 的结果是 `<class 'NoneType'>`
- [D] None 可以用作字典的键

**参考答案**：0

**解析**：None 是内置常量而不是关键字，理论上可以被赋值（`None = 1` 会报 SyntaxError 吗？在新版本中给 None 赋值会抛 SyntaxError，因此说它不能被赋值是对的，但“关键字”表述并不准确）。实际上在 Python 3 中给 None 赋值会触发 SyntaxError，因此 A 的“是关键字”是错误描述。None 是单例，type(None) 是 NoneType，也可作为字典键。

### single_choice · None



- [A] 1
- [B] 2
- [C] 报错
- [D] 0

**参考答案**：1

**解析**：None 是对象，字符串 'None' 是另一个键，二者不相等，因此字典中有两个不同的键，长度为 2。

### single_choice · None



- [A] True
- [B] False
- [C] 报错
- [D] 取决于 Python 版本

**参考答案**：1

**解析**：None 与布尔值 False 是两个不同的对象，彼此不相等。注意 `bool(None)` 为 False，但 `None == False` 为 False。

### single_choice · None



- [A] 0
- [B] False
- [C] None
- [D] 报错

**参考答案**：2

**解析**：flag 为 False 时不进入 if，函数没有执行任何 return，因此隐式返回 None。

### multi_choice · None



- [A] print('hello')
- [B] [].append(1)
- [C] len('')
- [D] list.sort() 对列表排序后该方法的返回值（在未返回新列表的调用中）
- [E] 'abc'.upper()

**参考答案**：[0, 1, 3]

**解析**：print 返回 None，列表的 append 方法原地修改并返回 None，list.sort() 也是原地排序返回 None。len('') 返回 0，'abc'.upper() 返回新字符串 'ABC'。
