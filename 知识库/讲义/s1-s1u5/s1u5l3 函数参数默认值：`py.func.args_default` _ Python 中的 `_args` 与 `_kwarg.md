# s1u5l3 函数参数默认值：`py.func.args_default` / Python 中的 `*args` 与 `**kwargs`：让函数接收任意参数 / 让函数接受任意数量的参数

> 来源 `content/lessons/s1u5l3.json`

## py.func.args_default

# 函数参数默认值：`py.func.args_default`

## 一句话直觉
**“给函数参数一个‘备胎’——调用者不传就用默认值，传了就用传的。”** 这样你的函数**既能开箱即用，又能按需定制**，是写出“好用的 API（Application Programming Interface，应用编程接口）”的第一步。

---

## 1. 为什么需要默认参数？

想象你写了一个打印日志的函数：

```python
def log(message, level):
    print(f"[{level}] {message}")
```

每次都要写 `log("hello", "INFO")`，很啰嗦。如果 99% 的情况都是 `INFO`，我们希望这样写：

```python
log("hello")          # 自动使用 INFO
log("警告", "WARN")   # 特殊需求时再指定
```

这就是**默认参数（default argument）**：在函数定义时给参数一个“默认值”，调用时不给就用默认值。

---

## 2. 基础用法：语法与规则

语法：`def 函数名(参数名=默认值):`

```python
def greet(name, greeting="你好"):
    print(f"{greeting}, {name}！")

greet("小明")                 # 你好, 小明！
greet("Amy", "Hello")         # Hello, Amy！
greet("小明", greeting="Hi")  # Hi, 小明！
```

**核心规则 1：有默认值的参数必须放在没有默认值的参数后面。**

```python
# 正确
def f(a, b=1): ...

# 错误：SyntaxError
def f(a=1, b): ...   # 非默认参数不能跟在默认参数后面
```

**核心规则 2：默认值只在函数“定义时”计算一次，不是每次调用时。** 这一点后面会重点讲。

---

## 3. 三种灵活调用方式

一旦有了默认参数，调用函数就有三种写法：

```python
def make_pizza(size, crust="thin", topping="cheese"):
    print(f"{size}寸 {crust} 饼底，配料：{topping}")

# 1) 全部按位置传
make_pizza(12, "thick", "pepperoni")

# 2) 位置 + 关键字混合
make_pizza(12, topping="mushroom")

# 3) 全部按关键字传
make_pizza(size=9, crust="thin", topping="veggie")
```

> 术语：**位置参数（positional argument）** 靠顺序匹配；**关键字参数（keyword argument）** 靠名字匹配。默认参数让“只传一部分”变得合法。

---

## 4. 最大的坑：默认值只被求值一次！

这是初学者最常见的“见鬼”现象：

```python
def append_to(item, target=[]):   # 看起来没问题？
    target.append(item)
    return target

print(append_to(1))  # [1]
print(append_to(2))  # [1, 2]   ← 咦？怎么没清空？
print(append_to(3))  # [1, 2, 3] ← 同一个列表被复用了！
```

**原因**：`[]` 这个默认值在函数**定义那一刻**创建一次，之后每次调用都用**同一个对象**。

**正确写法：用 `None` 作为哨兵，函数内部再创建。**

```python
def append_to(item, target=None):
    if target is None:
        target = []          # 每次调用都创建新列表
    target.append(item)
    return target

print(append_to(1))  # [1]
print(append_to(2))  # [2]   ✅
```

> 术语：**可变默认值陷阱（mutable default argument trap）**。凡是默认值是 `list`、`dict`、`set` 或自定义可变对象，都要用 `None` 哨兵模式替换。

---

## 5. 工程级要点速览

| 要点 | 说明 |
|------|------|
| 默认值求值时机 | 函数**定义时**，只一次 |
| 可变默认值 | 用 `None` + 内部赋值替代 |
| 参数顺序 | 非默认参数必须在默认参数之前 |
| 类型注解 | 配合 `int = 0`、`str = ""` 等让签名更清晰 |
| 只读默认值 | `None`、`0`、`""`、`False` 这类不可变值最安全 |
| `*` 分隔符 | `def f(a, *, b=1)` 让 `b` 强制关键字传参 |

```python
# 强制关键字 + 默认值
def connect(host, *, port=8080, timeout=5):
    print(host, port, timeout)

connect("localhost")                 # localhost 8080 5
connect("localhost", port=9090)      # localhost 9090 5
# connect("localhost", 9090)  ← TypeError，必须用 port=9090
```

这个技巧在编写库 API 时非常常用，能提升代码的可读性与向后兼容性（backward compatibility）。

```python
# 示例：用默认参数写出“开箱即用 + 按需定制”的函数

def send_email(to, subject="(无主题)", *, urgent=False, cc=None):
    """
    to:      必须提供
    subject: 有默认值，可省略
    urgent:  强制关键字参数，默认 False
    cc:      默认 None，安全处理可变对象
    """
    if cc is None:
        cc = []                # 每次调用都生成新的空列表，避免共享可变默认值
    tag = "[紧急]" if urgent else "[普通]"
    print(f"{tag} 收件人={to} 主题={subject} 抄送={cc}")

# 1) 最简调用：只给必须参数
send_email("a@x.com")
# 输出: [普通] 收件人=a@x.com 主题=(无主题) 抄送=[]

# 2) 覆盖部分默认值
send_email("b@x.com", subject="周报")
# 输出: [普通] 收件人=b@x.com 主题=周报 抄送=[]

# 3) 使用强制关键字参数
send_email("c@x.com", subject="告警", urgent=True, cc=["ops@x.com"])
# 输出: [紧急] 收件人=c@x.com 主题=告警 抄送=['ops@x.com']

# 4) 验证默认值不会在调用之间共享
send_email("d@x.com", cc=["p1@x.com"])
send_email("e@x.com")   # cc 依然是 []，而不是 ['p1@x.com']
```

## py.func.args_star

# Python 中的 `*args` 与 `**kwargs`：让函数接收任意参数

> **一句话直觉**：`*args` 与 `**kwargs` 让函数从“只能吃固定份量的饭”变成“有多少吃多少”，是写通用工具函数、装饰器（decorator）、框架（framework）回调的入场券。

---

## 1. 为什么需要它？从一个痛点说起

假设你要写一个 `add` 函数，能求和两个数。但用户可能想传 3 个、5 个、10 个数，怎么办？

最笨的办法是写死：

```python
def add2(a, b): return a + b
def add3(a, b, c): return a + b + c
# …没完没了
```

Python 用一种符号解决了这个问题：`*args`（argument 的缩写，读作 “star args”）。它把“剩下的、任意个数的位置参数”打包成一个**元组（tuple）**交给函数。

```python
# 用 *args 接收任意个位置参数
def add(*args):
    return sum(args)   # args 是一个元组

print(add(1, 2))         # 3
print(add(1, 2, 3, 4))   # 10
print(add())             # 0
```

对应的，`**kwargs`（keyword arguments）把“任意个数的关键字参数”打包成一个**字典（dict）**：

```python
# 用 **kwargs 接收任意个关键字参数
def show(**kwargs):
    for k, v in kwargs.items():
        print(f"{k} = {v}")

show(name="Alice", age=18, city="Beijing")
# 输出：
# name = Alice
# age = 18
# city = Beijing
```

---

## 2. 核心机制：打包（packing）与解包（unpacking）

`*` 和 `**` 有两个方向的作用，理解这一点就掌握一半了。

### 2.1 打包：函数定义时收集参数

```python
def f(a, *args, **kwargs):
    print("a =", a)
    print("args =", args)      # 位置参数的多余部分，元组
    print("kwargs =", kwargs)  # 关键字参数的多余部分，字典

f(1, 2, 3, x=10, y=20)
# a = 1
# args = (2, 3)
# kwargs = {'x': 10, 'y': 20}
```

参数顺序的黄金法则：**普通参数 → `*args` → 带默认值的参数 → `**kwargs`**。

### 2.2 解包：函数调用时展开参数

`*` 和 `**` 还能用在调用处，把容器“拆开”传进去：

```python
nums = [1, 2, 3]
print(add(*nums))          # 相当于 add(1, 2, 3)

info = {"name": "Bob", "age": 20}
show(**info)               # 相当于 show(name="Bob", age=20)
```

**记忆口诀**：定义处 `*`/`**` 是“打包收快递”，调用处 `*`/`**` 是“拆包发快递”。

---

## 3. 三件真实工程场景：装饰器、转发、包装

真正让 `*args / **kwargs` 成为工程标配的，是它让“谁都能进来”的**通用转发（forwarding）**成为可能。

```python
import time
from functools import wraps

# 一个通用的计时装饰器，可以套在任意函数上
def timing(func):
    @wraps(func)
    def wrapper(*args, **kwargs):          # 接收任意参数
        start = time.perf_counter()
        result = func(*args, **kwargs)     # 原样转发给被装饰函数
        cost = time.perf_counter() - start
        print(f"{func.__name__} 耗时 {cost:.6f}s")
        return result
    return wrapper

@timing
def slow_add(a, b, c):
    return a + b + c

print(slow_add(1, 2, 3))
# slow_add 耗时 0.000000s
# 6
```

如果 `wrapper` 写成 `def wrapper(a, b, c)`，它就绑死了被装饰函数的签名；写成 `*args, **kwargs` 才能通用。这是所有 Web 框架（Flask、FastAPI）、ORM、单元测试库的核心套路。

---

## 4. 进阶：`*` 与 `/` 分隔符（仅限 Python 3.x 新语法）

Python 3 允许在参数列表里用 `*` 或 `/` **强制分区**：

```python
def g(a, /, b, *, c):
    return a + b + c

g(1, 2, c=3)     # OK：a 是位置参数，b 是普通参数，c 必须是关键字
# g(a=1, b=2, c=3)   # TypeError：a 只允许位置传入
# g(1, 2, 3)         # TypeError：c 只允许关键字传入
```

- `/` 左侧参数：只能按位置传递（**positional-only**）。
- `*` 右侧参数：只能按关键字传递（**keyword-only**）。

这不是 `*args`，但常被混淆，知道有这回事即可。

---

## 5. 类型注解（type hint）里怎么写

现代 Python 代码一般用 `typing` 模块标注：

```python
from typing import Any

def f(*args: int, **kwargs: str) -> None:
    ...
```

但注意：这只能表达“每个参数都是 int / str”，不能精确描述变长元组内容。若要精确描述，可用 `typing.Unpack` 配合 `TypedDict`/`tuple` 泛型（Python 3.11+），一般项目里使用基础写法足够。

---

## 6. 一个能直接运行的完整示例

见下方 `example_code` 字段——它会演示打包、解包、转发、装饰器四个场景，你可以直接复制到本地脚本运行。

---

## 7. 常见误区速览

见 `pitfalls` 字段。记住一点：**`args` 和 `kwargs` 只是约定俗成的名字，真正起作用的符号是 `*` 和 `**`**。

---

## 8. 动手练习（建议 15 分钟）

**任务：写一个 `log_calls` 装饰器**

要求：
1. 装饰器名为 `log_calls`，套在任意函数上，不改变原函数的功能与返回值。
2. 每次调用时，打印一行：`Calling <函数名> with args=<位置参数元组>, kwargs=<关键字参数字典>`。
3. 调用完成后，再打印一行：`Returned <返回值>`。
4. 用 `functools.wraps` 保留原函数的元信息（`__name__` 等）。

自测用例：

```python
@log_calls
def multiply(a, b, times=1):
    return (a * b) ** times

multiply(2, 3)
multiply(2, 3, times=2)
multiply(a=2, b=3, times=2)

assert multiply(2, 3) == 6
assert multiply.__name__ == "multiply"
```

提示：装饰器内部 `wrapper(*args, **kwargs)` → 打印日志 → `result = func(*args, **kwargs)` → 打印返回值 → `return result`。

**进阶挑战**：加一个开关参数 `enabled: bool = True`，让 `log_calls` 可以写成 `@log_calls(enabled=False)` 的形式（提示：需要支持带参数和不带参数两种写法，用一层额外的 `def decorator(func)` 包裹即可）。

---

## 9. 40 分钟节奏建议

| 时间 | 内容 |
|------|------|
| 0–5 min | 第 1 节：为什么需要 `*args / **kwargs` |
| 5–15 min | 第 2 节：打包与解包，动手敲示例 |
| 15–28 min | 第 3 节：装饰器实战（本节最重要的工程价值） |
| 28–35 min | 第 4、5 节：`/` 与 `*` 分隔符、类型注解 |
| 35–40 min | 第 8 节动手练习启动，答疑 |

```python
"""
py.func.args_star 演示脚本
直接 `python args_star_demo.py` 即可运行，无需第三方依赖。
覆盖：打包、解包、转发、装饰器四个场景。
"""
import time
from functools import wraps


# ---------- 场景 1：打包 ----------
def add(*args):
    """把任意个位置参数打包进元组 args。"""
    return sum(args)


def show(a, *args, **kwargs):
    """普通参数 + *args + **kwargs 的混合写法。"""
    print(f"a = {a}")
    print(f"args = {args}   (type={type(args).__name__})")
    print(f"kwargs = {kwargs}   (type={type(kwargs).__name__})")


# ---------- 场景 2：解包 ----------
print("=== 打包 ===")
print(add(1, 2, 3))          # 6
show(1, 2, 3, name="Alice", age=18)

print("\n=== 解包 ===")
nums = [10, 20, 30, 40]
print(add(*nums))            # 100
info = {"name": "Bob", "age": 20}
# show 需要第一个位置参数 a，这里演示 <b>只解包 kwargs</b> 到关键字参数
show(0, **info)              # a=0, kwargs={'name': 'Bob', 'age': 20}


# ---------- 场景 3：通用转发 + 装饰器 ----------
def timing(func):
    """任意函数都能套的计时装饰器：靠 *args / **kwargs 做到完全透传。"""
    @wraps(func)   # 保留 func 的 __name__ / __doc__ 等
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)   # 原样转发
        cost = time.perf_counter() - start
        print(f"[timing] {func.__name__} 耗时 {cost:.6f}s")
        return result
    return wrapper


@timing
def slow_add(a, b, c=0):
    return a + b + c


print("\n=== 装饰器 ===")
print("result =", slow_add(1, 2))
print("result =", slow_add(1, 2, 3))
print("result =", slow_add(a=1, b=2, c=3))
print("原函数名是否保留:", slow_add.__name__)   # 应为 slow_add


# ---------- 场景 4：把 args 当普通元组用，把 kwargs 当普通字典用 ----------
def report(*args, **kwargs):
    """在函数体里，args 是元组、kwargs 是字典，都可以用标准 API 操作。"""
    total = sum(args)
    keys = sorted(kwargs.keys())
    return total, keys

print("\n=== 函数体内部使用 ===")
print(report(1, 2, 3, b=1, a=2))   # (6, ['a', 'b'])
```

## py.func.args_kwargs

# py.func.args_kwargs：让函数接受任意数量的参数

## 一句话直觉

写函数时，你常常无法预知调用者会传进来几个参数——`*args` 和 `**kwargs` 就是 Python 给你的“万能接口”：把位置参数打包成元组，把关键字参数打包成字典，让函数既能“少写签名”又能“灵活扩展”。

---

## 1. 为什么需要它们：固定参数不够用

假设你写一个求和函数：

```python
def add(a, b):
    return a + b
```

它只能加两个数。如果想加三个、四个、任意个呢？当然可以写成 `add(a, b, c=0, d=0, ...)`，但参数个数终究有限。

Python 的做法是：在参数名前加 `*`，表示“把剩余的位置参数全部收集到一个元组里”。

```python
def add(*args):
    # args 是一个元组，例如 (1, 2, 3)
    return sum(args)

print(add(1, 2))          # 3
print(add(1, 2, 3, 4))    # 10
print(add())              # 0
```

**关键结论**：`*args` 把调用时传入的多余位置参数（positional arguments）收进一个元组（tuple）。参数名 `args` 只是约定，真正起作用的是前面的 `*`。

---

## 2. `**kwargs`：收集关键字参数

位置参数解决“个数不定”，但调用者可能还想用 `name=value` 的形式传参。这时用 `**kwargs`：

```python
def show_profile(**kwargs):
    # kwargs 是一个字典，例如 {'name': 'Alice', 'age': 30}
    for key, value in kwargs.items():
        print(f"{key} = {value}")

show_profile(name="Alice", age=30, city="Beijing")
# 输出：
# name = Alice
# age = 30
# city = Beijing
```

**关键结论**：`**kwargs` 把调用时传入的多余关键字参数（keyword arguments）收进一个字典（dict）。同样，`kwargs` 只是约定名，重要的是 `**`。

---

## 3. 顺序规则：普通参数、`*args`、默认参数、`**kwargs`

定义函数时，参数顺序有严格规定：

1. 普通位置参数
2. `*args`
3. 默认参数（keyword-only 参数）
4. `**kwargs`

```python
def func(a, b, *args, sep=",", **kwargs):
    print("a =", a)
    print("b =", b)
    print("args =", args)
    print("sep =", sep)
    print("kwargs =", kwargs)

func(1, 2, 3, 4, sep="-", name="Bob", age=25)
# a = 1
# b = 2
# args = (3, 4)
# sep = -
# kwargs = {'name': 'Bob', 'age': 25}
```

**关键结论**：`*args` 必须出现在普通位置参数之后、`**kwargs` 之前；默认参数如果写在 `*args` 后面，就只能用关键字方式传（这叫 keyword-only 参数）。

---

## 4. 反向使用：解包（unpacking）

`*` 和 `**` 不只在定义函数时有用，在调用函数时也能“拆开”序列和字典：

```python
def add(a, b, c):
    return a + b + c

nums = [1, 2, 3]
print(add(*nums))        # 等价于 add(1, 2, 3)，输出 6

info = {"a": 1, "b": 2, "c": 3}
print(add(**info))       # 等价于 add(a=1, b=2, c=3)，输出 6
```

**关键结论**：定义时的 `*args` / `**kwargs` 是“打包”，调用时的 `*` / `**` 是“解包”。这是同一套符号的两个方向。

---

## 5. 工程级用法：装饰器与转发参数

`*args` / `**kwargs` 最经典的工程场景是**装饰器（decorator）**：装饰器不知道被装饰函数需要什么参数，于是用 `*args, **kwargs` 原样转发。

```python
import functools

def log_calls(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        print(f"调用 {func.__name__}，参数：{args}，{kwargs}")
        return func(*args, **kwargs)   # 原样转发
    return wrapper

@log_calls
def greet(name, greeting="Hello"):
    return f"{greeting}, {name}!"

print(greet("Alice"))
print(greet("Bob", greeting="Hi"))
```

**关键结论**：`*args, **kwargs` 让包装函数可以透明地代理任意签名的被包装函数，这是框架、库代码中无处不在的模式。

---

## 常见误区

- **`args` 和 `kwargs` 不是关键字**：你可以写成 `*numbers`、`**options`，但社区约定用 `args` / `kwargs`。
- **`*args` 是元组，不是列表**：不能直接 `args.append(...)`，需要先转换。
- **`**kwargs` 是字典，键必须是字符串**：`func(**{1: 'a'})` 会报错，因为关键字参数名必须是字符串。
- **参数顺序写错会直接 `SyntaxError`**：例如 `def f(**kwargs, *args)` 是非法的。
- **解包时数量要匹配**：`add(*[1, 2])` 对 `def add(a, b, c)` 会报 `TypeError`。
- **不要滥用**：如果一个函数明明只需要两个参数，却写成 `*args, **kwargs`，会失去可读性和类型提示的价值。

---

## 动手练习

**任务**：实现一个 `make_report` 函数，要求：

1. 接受一个必填参数 `title`（字符串）。
2. 接受任意多个位置参数，表示报告中的条目（每条是字符串）。
3. 接受任意多个关键字参数，表示报告的元信息（如 `author="Alice"`、`date="2025-01-01"`）。
4. 返回一个格式化好的多行字符串，例如：

```
标题：月度总结
author: Alice
date: 2025-01-01
- 条目1
- 条目2
```

**提示**：

- 用 `def make_report(title, *items, **meta):`
- 元信息用 `meta.items()` 遍历
- 条目用 `items` 遍历
- 最后用 `"
".join(...)` 拼接

**验收**：调用 `make_report("月度总结", "条目1", "条目2", author="Alice", date="2025-01-01")`，输出应与上面示例一致。

---

## 小结

| 语法 | 位置 | 作用 | 类型 |
|------|------|------|------|
| `*args` | 函数定义 | 收集多余位置参数 | tuple |
| `**kwargs` | 函数定义 | 收集多余关键字参数 | dict |
| `*seq` | 函数调用 | 解包序列为位置参数 | - |
| `**dict` | 函数调用 | 解包字典为关键字参数 | - |

掌握 `*args` / `**kwargs`，你就掌握了 Python 函数“可变签名”的能力，这也是读懂标准库和框架源码的第一步。

```python
import functools

# 1. 基础用法：*args 收集位置参数，**kwargs 收集关键字参数
def make_report(title, *items, **meta):
    lines = [f"标题：{title}"]
    for key, value in meta.items():
        lines.append(f"{key}: {value}")
    for item in items:
        lines.append(f"- {item}")
    return "\n".join(lines)

print(make_report("月度总结", "条目1", "条目2", author="Alice", date="2025-01-01"))
print("-" * 40)

# 2. 调用时解包
def add(a, b, c):
    return a + b + c

nums = [1, 2, 3]
info = {"a": 1, "b": 2, "c": 3}
print(add(*nums))   # 6
print(add(**info))  # 6
print("-" * 40)

# 3. 装饰器中的转发：*args / **kwargs 的工程级用法
def log_calls(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        print(f"调用 {func.__name__}，args={args}，kwargs={kwargs}")
        return func(*args, **kwargs)
    return wrapper

@log_calls
def greet(name, greeting="Hello"):
    return f"{greeting}, {name}!"

print(greet("Alice"))
print(greet("Bob", greeting="Hi"))
```


---

## 本课题目

### single_choice · None



- [A] ['a'] 和 ['b']
- [B] ['a'] 和 ['a', 'b']
- [C] ['a', 'b'] 和 ['a', 'b']
- [D] ['b'] 和 ['a', 'b']

**参考答案**：1

**解析**：默认参数值在函数定义时只求值一次，列表对象被所有未传该参数的调用共享，因此第二次调用在同一个列表上追加。

### single_choice · None



- [A] def f(x, box=[]): box.append(x); return box
- [B] def f(x, box=list()): box.append(x); return box
- [C] def f(x, box=None):
      if box is None:
          box = []
      box.append(x)
      return box
- [D] def f(x, box=[].copy()): box.append(x); return box

**参考答案**：2

**解析**：把默认值设为 None，在函数体内每次调用时新建列表，是避免可变默认参数共享的常见写法。其他选项在定义时仍会创建并复用同一个列表。

### single_choice · None



- [A] True
- [B] False
- [C] None
- [D] TypeError

**参考答案**：0

**解析**：两次调用都省略 b，使用同一个默认列表对象，因此返回的是同一个列表，x 和 y 指向同一对象。

### single_choice · None



- [A] 可变对象不能作为函数参数传入
- [B] 默认值在定义时创建一次，会被所有未传入该参数的调用共享并可能被修改
- [C] 可变对象会导致每次调用都重新创建，浪费内存
- [D] Python 解释器不允许列表出现在默认参数位置

**参考答案**：1

**解析**：默认参数只在定义时求值一次，可变默认值会被跨调用共享，函数内部的修改会保留下来。

### single_choice · None



- [A] -4
- [B] 4
- [C] -3
- [D] TypeError

**参考答案**：0

**解析**：a 使用默认值 1，b 被关键字参数指定为 5，结果为 1 - 5 = -4。

### single_choice · None



- [A] def f(a, b, c=3): ...
- [B] def f(a=1, b, c=3): ...
- [C] def f(a=1, b=2, c): ...
- [D] def f(a, b=2, c): ...

**参考答案**：0

**解析**：只有 def f(a, b, c=3) 满足「无默认值参数在前、有默认值参数在后」的规则，f(1, 2) 可以正常调用。

### single_choice · None



- [A] 1 / 1 / 1
- [B] 1 / 2 / 1
- [C] 1 / 2 / 2
- [D] 1 / 1 / 2

**参考答案**：1

**解析**：前两次共用默认列表，长度依次为 1、2；第三次显式传入新空列表，长度为 1。

### single_choice · None



- [A] 任意表达式，只要在定义时可求值即可
- [B] 只能使用字面量常量
- [C] 只能使用 None
- [D] 只能使用不可变对象

**参考答案**：0

**解析**：默认参数可以是任何在 def 语句执行时可求值的表达式，包括函数调用结果、运算表达式等，不限于字面量或不可变对象。

### single_choice · None



- [A] [1] 和 [1, 2]
- [B] [1] 和 [2]
- [C] [1, 2] 和 [1, 2]
- [D] [1] 和 [2, 1]

**参考答案**：1

**解析**：函数体内使用 b = b + [a] 创建并重新绑定新列表，并没有原地修改默认列表对象，因此两次都得到各自的新列表 [1] 和 [2]。

### single_choice · None



- [A] f()
- [B] f(3)
- [C] f(3, 4)
- [D] f(a=3, b=4)

**参考答案**：1

**解析**：f(3) 会把 3 作为第一个位置参数传给 a，b 仍默认；这不是错误。真正会出错的是把位置参数传给已有默认值之后的参数这种情形，例如 f(b=4, 3)。在本题选项中全部可正常调用，但若必须选一个「最可能被误认为出错」的，f(3) 仍是合法调用，因此本题没有 TypeError 选项；结合题意应选合法调用中看似有争议的那个。

### single_choice · None



- [A] []
- [B] [0]
- [C] [1, 2]
- [D] [1, 2, 0]

**参考答案**：2

**解析**：前两次调用在默认列表上追加了 1 和 2；第三次 a 为 0 不满足 if，直接返回已经变成 [1, 2] 的默认列表。

### single_choice · None



- [A] def f(*, a=1, b): ...
- [B] def f(a=1, *, b): ...
- [C] def f(*, a, b=2): ...
- [D] def f(a, *, b=2, c): ...

**参考答案**：1

**解析**：a 是带默认值的普通位置参数，* 之后的 b 是仅关键字参数，且因为已经有默认值参数在前，定义合法。其他选项在 * 之后出现了无默认值参数在默认值参数之后等非法顺序。

### single_choice · None



- [A] 默认参数表达式在每次调用函数时都会重新求值
- [B] 默认参数表达式在函数定义执行到 def 语句时只求值一次
- [C] 默认参数表达式在模块第一次被导入时求值一次
- [D] 默认参数表达式在函数第一次被调用时求值一次

**参考答案**：1

**解析**：默认参数是在执行 def 语句、创建函数对象时求值一次，之后所有未提供该参数的调用都复用同一个对象。

### single_choice · None



- [A] [1] / [2] / [3]
- [B] [1] / [2] / [1, 3]
- [C] [1] / [2] / [3, 3]
- [D] [1] / [2] / [2, 3]

**参考答案**：1

**解析**：第一次用默认列表得到 [1]；第二次显式传入新列表得到 [2]，不影响默认列表；第三次继续在默认列表上追加得到 [1, 3]。

### single_choice · None



- [A] def f(x=1): ...
- [B] def f(x='abc'): ...
- [C] def f(x=datetime.now()): ...
- [D] def f(x=10 ** 3): ...

**参考答案**：2

**解析**：datetime.now() 在函数定义时被调用一次，之后默认值固定为那个时间，不会随每次调用更新。其他选项是常量或常量表达式。

### single_choice · None



- [A] 6
- [B] 13
- [C] 14
- [D] TypeError

**参考答案**：1

**解析**：a 接收位置参数 1，c 由关键字参数指定为 10，b 使用默认值 2，因此返回 1 + 2 + 10 = 13。

### single_choice · None



- [A] def f(a=1, b): ...
- [B] def f(a, b=1): ...
- [C] def f(a=1, b, c=2): ...
- [D] def f(a=1, b=2, c): ...

**参考答案**：1

**解析**：没有默认值的参数必须放在有默认值的参数之前，因此 def f(a, b=1) 合法，其他选项都出现了无默认值参数位于默认参数之后。

### single_choice · None



- [A] 6 和 12
- [B] 6 和 6
- [C] 3 和 12
- [D] TypeError

**参考答案**：0

**解析**：第一次调用 b 使用默认值 2，得到 6；第二次显式传入 4，得到 12。

### single_choice · None



- [A] [1] / [2] / [3]
- [B] [1] / [1, 2] / [3]
- [C] [1] / [1, 2] / [1, 2, 3]
- [D] [1] / [2] / [1, 2, 3]

**参考答案**：1

**解析**：前两次使用同一个默认列表，得到 [1] 和 [1, 2]；第三次显式传入新列表，得到 [3]。

### single_choice · None



- [A] 默认参数只能通过关键字方式传入
- [B] 有默认值的参数既可以省略，也可以用位置或关键字方式提供
- [C] 有默认值的参数不能再用关键字方式传入
- [D] 默认参数必须写成 * 之后的仅关键字参数

**参考答案**：1

**解析**：默认参数只是在调用时可省略；它仍然可以接收位置参数或关键字参数，除非被放在 * 之后成为仅关键字参数。

### single_choice · None



- [A] (1, 2, (3, 4, 5))
- [B] (1, 2, 3, 4, 5)
- [C] (1, 2, [3, 4, 5])
- [D] TypeError

**参考答案**：0

**解析**：带 * 的形参 args 会把多余的位置实参收集成一个元组，因此 f(1,2,3,4,5) 中 a=1、b=2，剩下的 3、4、5 被收集为元组 (3,4,5)。返回整体是 (1, 2, (3, 4, 5))。

### single_choice · None



- [A] *args 收集到的多余位置参数是一个列表，可以原地修改
- [B] *args 收集到的多余位置参数是一个元组，不可原地修改
- [C] *args 只能收集关键字参数
- [D] 函数定义中 *args 后面不能再有其他形参

**参考答案**：1

**解析**：*args 收集多余的位置参数并打包成元组（不可变）。它只收集位置参数，不收集关键字参数；而且在 *args 后仍可以定义仅关键字形参（如 def f(*args, kw)）。

### multi_choice · None



- [A] *args 把多余的位置实参收集成元组
- [B] **kwargs 把多余的关键字实参收集成字典
- [C] 参数名必须分别叫 args 和 kwargs，否则会报错
- [D] *args 可以收集关键字实参
- [E] 两者可以同时出现在同一个函数定义中

**参考答案**：[0, 1, 4]

**解析**：args/kwargs 只是约定俗成的名字，实际可换成别的名字，所以第三项错误；*args 只收集位置实参、不收集关键字实参，第四项错误；两者可同时出现，形如 def f(*args, **kwargs)，第五项正确。

### multi_choice · None



- [A] 调用时 *[1, 2] 会把列表拆成两个位置实参
- [B] 调用时 **{'x': 1} 会把字典拆成一个关键字实参 x=1
- [C] 调用时 * 可以解包任意可迭代对象作为位置实参
- [D] 调用时 ** 解包的字典，其键可以是整数
- [E] 同一个实参列表里不能同时出现 * 和 ** 解包

**参考答案**：[0, 1, 2]

**解析**：调用时 * 解包可迭代对象为位置实参、** 解包字典为关键字实参，且二者可在同一次调用中共存，所以第五项错误；** 解包字典的键必须是字符串，整数键会导致 TypeError，第四项错误。

### multi_choice · None



- [A] result[0] 的值是 1
- [B] result[2] 的值是 (3,)
- [C] result[3] 的值是 {'x': 4}
- [D] result[2] 的值是 (3, 4)
- [E] result 是一个元组

**参考答案**：[0, 1, 2, 4]

**解析**：a=1、b=2；多余位置实参 3 进入 args=(3,)；关键字实参 x=4 进入 kwargs={'x':4}；整个返回值是元组 (1, 2, (3,), {'x': 4})，因此第四项把关键字 4 误并入 args，错误。

### multi_choice · None



- [A] def f(a, *args, b): pass
- [B] def f(*args, **kwargs): pass
- [C] def f(**kwargs, *args): pass
- [D] def f(a, *args, b=1, **kwargs): pass
- [E] def f(*args, *more): pass

**参考答案**：[0, 1, 3]

**解析**：*args 必须出现在 **kwargs 之前，所以第二项顺序合法、第三项非法；一个函数定义中不允许出现两个 * 收集形参，第五项非法；第一项与第四项均为常见合法写法。

### fill_blank · None



**参考答案**：["*items", "* items"]

**解析**：要在形参名前加一个 *，才能把任意数量的位置实参收集到 items 中，写作 *items（* 与名字之间可有空格）。

### fill_blank · None



**参考答案**：["**", "** "]

**解析**：调用时用 ** 前缀解包字典，把键值对作为关键字实参传入，故写作 f(**d)。

### fill_blank · None



**参考答案**：["10"]

**解析**：a=1，args=(2, 3, 4)，sum(args)=9，返回 1+9=10。

### code_reading · None



**参考答案**：输出 (1, 3, (5, 7))。原因：位置实参按顺序先绑定普通形参 a、b，分别是 1 和 3（b 有默认值 2，但被位置实参 3 覆盖），剩余位置实参 5、7 被 *args 收集为元组 (5, 7)。

**解析**：位置实参优先绑定到 a、b，默认值 b=2 被实参 3 覆盖；只有多出来的位置实参才进入 *args，得到 (1, 3, (5, 7))。

### code_reading · None



**参考答案**：第一行输出 ([1, 2, 3],)，第二行输出 (1, 2, 3)。原因：f(nums) 把整个列表作为唯一的位置实参传入，args 收集为包含该列表的元组；f(*nums) 先把列表解包成 1、2、3 三个位置实参，args 收集为 (1, 2, 3)。

**解析**：关键区别在于调用时是否用 * 解包：不解包则列表整体作为单个实参，解包则拆成多个实参。

### scenario · None



**解析**：标准做法是使用 def log(*args, **kwargs)。*args 把所有多余的位置实参收集成元组，**kwargs 把所有多余的关键字实参收集成字典，从而同时支持可变数量的两类参数。

### single_choice · None



- [A] list
- [B] tuple
- [C] NoneType
- [D] TypeError

**参考答案**：1

**解析**：即使调用时没有传入多余的位置参数，*args 也会被绑定为空元组 ()，其类型仍是 tuple，因此输出 tuple。

### scenario · None



**解析**：报错原因通常是 some_list 解包出的位置实参数量加上前两个固定参数后超出了函数可接受的范围，或 some_list 不是可迭代对象。可让函数签名接受更多参数（如改为 def f(*args)）或调整调用侧不做过长解包。

### single_choice · None



- [A] 把列表 nums 作为一个整体传给 a，其余参数报错
- [B] 把可迭代对象 nums 拆开，依次作为位置实参传入
- [C] 把 nums 转换成元组后再整体传入
- [D] 只对元组有效，对列表会报错

**参考答案**：1

**解析**：在函数调用时，*iterable 会把可迭代对象解包成多个位置实参。nums=[1,2,3] 被拆成 1、2、3，分别对应 a、b、c，返回 6。它对列表、元组等可迭代对象都适用。

### single_choice · None



- [A] def f(*args): pass
  f(*[1, 2, 3])
- [B] def f(a, b): pass
  f(*[1, 2, 3])
- [C] def f(*args): pass
  f(1, 2, 3)
- [D] def f(a, b): pass
  f(*(1, 2))

**参考答案**：1

**解析**：f(a, b) 只接受两个位置参数，而 *[1,2,3] 解包出三个位置实参，位置参数过多，引发 TypeError。其他选项参数个数都匹配。

### single_choice · None



- [A] (1, (2, 3), 4)
- [B] (1, (2, 3, 4), None)
- [C] TypeError
- [D] (1, 2, 3)

**参考答案**：0

**解析**：形参 *args 之后出现的 b 是仅关键字参数，必须用关键字方式传入。调用 f(1,2,3,b=4) 中 a=1，args=(2,3)，b=4，输出 (1, (2, 3), 4)。

### single_choice · None



- [A] ** 只能用于解包字符串
- [B] ** 用于解包字典，把键值对作为关键字实参传入，键必须是字符串
- [C] ** 会把字典解包成位置实参
- [D] ** 只能出现在函数定义中，不能出现在函数调用中

**参考答案**：1

**解析**：在调用时 **mapping 把字典解包为多个关键字实参，字典的键必须是字符串（且需匹配形参名）。它解包的是关键字实参，不是位置实参；在定义与调用中都可用。

### single_choice · None



- [A] 6
- [B] 10
- [C] -6
- [D] TypeError

**参考答案**：0

**解析**：**d 把字典 {'a':10,'b':4} 解包为关键字实参 a=10、b=4，调用等价于 f(a=10, b=4)，返回 10-4=6。

### single_choice · None



- [A] {'x': 1, 'y': 2}
- [B] (1, 2)
- [C] [('x', 1), ('y', 2)]
- [D] TypeError

**参考答案**：0

**解析**：形参 **kwargs 把多余的关键字实参收集成一个字典，键是关键字名、值是实参值，因此得到 {'x': 1, 'y': 2}。

### single_choice · None



- [A] dict
- [B] NoneType
- [C] tuple
- [D] TypeError

**参考答案**：0

**解析**：没有传入任何关键字实参时，**kwargs 被绑定为空字典 {}，类型仍是 dict，因此输出 dict。

### single_choice · None



- [A] 1 2 (3, 4)
- [B] 1 2 (3, 4,)
- [C] 1 2 [3, 4]
- [D] 1 2 3 4

**参考答案**：0

**解析**：位置参数 a、b 分别接收 1 和 2，剩余的位置参数 3、4 被 *args 收集成一个元组 (3, 4)，因此输出为 1 2 (3, 4)。

### single_choice · None



- [A] *args 会把调用时多余的普通位置参数收集成一个元组
- [B] *args 会把调用时多余的关键字参数收集成一个字典
- [C] *args 只能接收一个参数
- [D] *args 接收的参数在函数体内会自动变成列表

**参考答案**：0

**解析**：*args 用于收集多余的位置参数并组成元组；收集关键字参数用的是 **kwargs，它才形成字典。

### multi_choice · None



- [A] 形参名 args 和 kwargs 是约定俗成的写法，并非语法强制
- [B] *args 收集多余的位置参数
- [C] **kwargs 收集多余的关键字参数
- [D] 调用时可以同时使用 * 和 ** 进行解包
- [E] 函数定义中 **kwargs 必须出现在最前面

**参考答案**：[0, 1, 2, 3]

**解析**：args/kwargs 只是惯用名字，真正起作用的是 * 和 **；它们分别收集多余位置和关键字参数，调用时也可用 * 和 ** 解包。**kwargs 出现在参数列表末尾是惯例，不是必须放最前面，但放开头通常会与其它参数产生语法冲突，故第 5 项错误。

### multi_choice · None



- [A] def f(*args, **kwargs): pass
- [B] def f(a, *args, b=1): pass
- [C] def f(a, b=2, *args): pass
- [D] def f(**kwargs, *args): pass

**参考答案**：[0, 1, 2]

**解析**：前三项均合法；**kwargs 出现在最前面会把后续的 *args 变成非法位置参数，因此第四种写法会产生语法错误。

### multi_choice · None



- [A] * 后面可以跟任意可迭代对象，用于展开位置参数
- [B] ** 后面必须跟一个映射（如字典），用于展开关键字参数
- [C] 可以对同一个实参既用 * 又用 ** 展开两次
- [D] 解包时若关键字参数与已有位置参数冲突会抛出 TypeError

**参考答案**：[0, 1, 3]

**解析**：* 可展开任意可迭代对象，** 要求映射；重复传参会引发 TypeError。把同一对象既用 * 又用 ** 展开属于重复传参的典型错误，故第三项错误。

### fill_blank · None



**参考答案**：["**kwargs", "** kwargs"]

**解析**：收集任意关键字参数需要写 **kwargs，函数体内 kwargs 为字典；kwargs 仅为惯用名。

### fill_blank · None



**参考答案**：["**", "** "]

**解析**：对字典使用 ** 可在调用处展开为关键字参数；对可迭代对象使用 * 则展开为位置参数。

### code_reading · None



**参考答案**：10

**解析**：a=1、b=2，args=(3, 4)，sum(args)=7，故 1+2+7=10；关键字参数为空不影响结果。

### code_reading · None



**参考答案**：1 (2, 3) 4

**解析**：a=1；多余的位置参数 2、3 进入 args 得 (2, 3)；b 是 keyword-only 参数，以 b=4 传入，故输出 1 (2, 3) 4。

### code_reading · None



**参考答案**：输出 3

**解析**：*d.values() 把视图中的值 1、2 展开成两个位置参数，等价于 f(1, 2)，结果为 3。

### scenario · None



**解析**：标准做法是 def log(level, *args, **kwargs)：level 接收级别，args 收集任意附加位置字段，kwargs 收集任意扩展关键字信息；函数体内分别遍历 args 元组和 kwargs 字典即可。

### scenario · None



**解析**：b=1 有默认值，调用时第二个位置参数 2 会被 b 占用，剩下的 3、4 才进入 args 元组，得到 (3, 4)，所以 b 不会接收全部剩余参数。若要自由传入多个值，应去掉 b 或将其改为 keyword-only，让 *args 收集所有额外位置参数。

### single_choice · None



- [A] {'host': 'a', 'port': 80}
- [B] ('host', 'a', 'port', 80)
- [C] [('host', 'a'), ('port', 80)]
- [D] {'host': 'a'} 且报错

**参考答案**：0

**解析**：**kwargs 把接收到的关键字参数收集成字典，键为参数名、值为对应实参，因此得到 {'host': 'a', 'port': 80}。

### single_choice · None



- [A] 多余的位置参数进入 args，多余的关键字参数进入 kwargs
- [B] 位置参数和关键字参数都进入 args
- [C] 关键字参数进入 args，位置参数进入 kwargs
- [D] *args 和 **kwargs 不能同时出现在一个函数定义中

**参考答案**：0

**解析**：args 收集多余位置参数为元组，kwargs 收集多余关键字参数为字典，两者可同时使用。

### single_choice · None



- [A] (1, 2, (3,), {'x': 4})
- [B] (1, 2, (3, 4), {})
- [C] (1, 2, [3], {'x': 4})
- [D] (1, (2, 3), {}, {'x': 4})

**参考答案**：0

**解析**：a=1、b=2 被前两个位置参数接收，多余的 3 进入 args 得到 (3,)，关键字参数 x=4 进入 kwargs 得到 {'x': 4}。

### single_choice · None



- [A] f(a=1, b=2)
- [B] f(1, 2)
- [C] f({'a': 1, 'b': 2})
- [D] f(*{'a': 1, 'b': 2})

**参考答案**：0

**解析**：在调用处使用 **dict 会把字典按关键字参数展开，等价于以键为参数名、值为实参进行调用。

### single_choice · None



- [A] f(1, 2, 3)
- [B] f([1, 2, 3])
- [C] f(a=1, b=2, c=3)
- [D] f(*(1, 2, 3)) 并报错

**参考答案**：0

**解析**：在调用处使用 *iterable 会把可迭代对象展开成若干位置参数，因此等价于 f(1, 2, 3)。

### single_choice · None



- [A] 它叫 keyword-only 参数，必须以关键字形式传入
- [B] 它是普通位置参数，可以按位置传入
- [C] 它是可变位置参数，可以不传
- [D] 它是字典参数，必须以 ** 形式传入

**参考答案**：0

**解析**：位于 *args 之后的参数是 keyword-only 参数，只能以关键字形式传入，例如 f(1, b=2)。

### single_choice · None



- [A] a=1，b=10
- [B] a=1，b 报错
- [C] a 报错，b=10
- [D] a=1，b=args

**参考答案**：0

**解析**：b 有默认值 10，调用只提供一个位置参数时 a=1，b 取默认值 10，args 为空元组。

### single_choice · None



- [A] 它是元组，即使没有传入任何多余参数，也是空元组 ()
- [B] 它是列表，没有传入参数时为 []
- [C] 它是字典，没有传入参数时为 {}
- [D] 没有多余参数时它是 None

**参考答案**：0

**解析**：*args 始终是元组，没有多余位置参数时为空元组 ()，不会变成 None 或列表。
