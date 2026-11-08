# s2u1l5 魔法方法入门（Dunder Methods） / Python 对象表示：`__repr__` 与 `__str__` / 让对象“可比较、可去重、可当字典键”

> 来源 `content/lessons/s2u1l5.json`

## py.oop.dunder_intro

# 魔法方法入门（Dunder Methods）

## 一句话直觉

**魔术方法（magic methods）**，又叫 **dunder methods**（double underscore，双下划线方法），是 Python 中形如 `__xxx__` 的特殊方法。它们让你自定义的类可以像内置类型一样工作——能被 `print`、能被 `len` 取长度、能用 `+` 相加、能用 `for` 遍历。**学习它们，就是让你的对象从"能用"变成"好用"。**

---

## 1. 为什么需要魔法方法？

先看一个普通类：

```python
class Dog:
    def __init__(self, name):
        self.name = name

d = Dog('旺财')
print(d)   # <__main__.Dog object at 0x...>
```

`print(d)` 输出的是一串看不懂的地址。我们希望能打印出 `Dog(旺财)`，希望两个 Dog 能相加，希望 `len(d)` 有意义——这一切都靠魔法方法。

**核心直觉**：Python 的设计哲学是"一切皆对象"，而对象之间靠一套**协议（protocol）**沟通。魔法方法就是协议的钩子（hook）。你实现它，Python 就会在对应语法场景自动调用它。

---

## 2. `__init__` 与 `__repr__` / `__str__`

- `__init__(self, ...)`：构造对象时自动调用，用来初始化属性。
- `__repr__(self)`：给开发者看的字符串，目标是无歧义（理想情况下能 `eval` 回去）。
- `__str__(self)`：给用户看的字符串，`print` 时优先用它。若没定义 `__str__`，会退回到 `__repr__`。

```python
class Point:
    def __init__(self, x, y):
        self.x, self.y = x, y

    def __repr__(self):
        # 开发者视角：Python 交互式环境直接显示这个
        return f'Point({self.x}, {self.y})'

    def __str__(self):
        # 用户视角：print() 时显示这个
        return f'({self.x}, {self.y})'

p = Point(1, 2)
print(p)        # (1, 2)      -> __str__
p               # Point(1, 2) -> __repr__
```

---

## 3. 容器协议：`__len__` 与 `__getitem__`

实现这两个方法后，你的对象就"像一个序列"了：支持 `len()`、下标访问、`for` 循环。

```python
class Playlist:
    def __init__(self, songs):
        self.songs = list(songs)

    def __len__(self):
        # 支持 len(playlist)
        return len(self.songs)

    def __getitem__(self, i):
        # 支持 playlist[0] 和 for 循环（for 会自动从 0 开始调用直到 IndexError）
        return self.songs[i]

pl = Playlist(['A', 'B', 'C'])
print(len(pl))            # 3
print(pl[1])              # B
for s in pl:              # for 循环靠 __getitem__ 驱动
    print(s)
```

> **小知识**：只要类实现了 `__getitem__`，`for` 循环就能工作，因为 Python 会一直用 `0,1,2,...` 去索引直到抛 `IndexError`。

---

## 4. 运算符重载：`__add__`、`__eq__`

`+`、`==`、`<` 等运算符都可以被重载。

```python
class Vector:
    def __init__(self, x, y):
        self.x, self.y = x, y

    def __add__(self, other):
        # 支持 v1 + v2
        return Vector(self.x + other.x, self.y + other.y)

    def __eq__(self, other):
        # 支持 v1 == v2
        return (self.x, self.y) == (other.x, other.y)

    def __repr__(self):
        return f'Vector({self.x}, {self.y})'

v = Vector(1, 2) + Vector(3, 4)
print(v)                       # Vector(4, 6)
print(Vector(1, 2) == Vector(1, 2))  # True
```

> **注意**：定义了 `__eq__` 后，对象默认变得不可哈希（unhashable），因为 Python 认为你改变了"相等"的语义。如果还想放进 `set` 或做 `dict` 的键，需要一并实现 `__hash__`。

---

## 5. 工程视角：魔法方法让自定义类融入 Python 生态

当你的类实现了 `__iter__`、`__len__`、`__getitem__`、`__contains__` 等，它就能直接被`list()`、`sum()`、`in`、解构赋值、`sorted()` 等内置函数使用，无需适配层。这就是**协议导向编程（protocol-oriented programming）**的威力。

```python
class MyRange:
    def __init__(self, n):
        self.n = n

    def __iter__(self):
        # 支持 for / list() / sum() 等
        return iter(range(self.n))

    def __contains__(self, v):
        # 支持 3 in obj
        return 0 <= v < self.n

print(list(MyRange(3)))   # [0, 1, 2]
print(sum(MyRange(4)))    # 6
print(2 in MyRange(5))    # True
```

---

## 动手练习

**任务**：实现一个 `Matrix2x2` 类，表示 2×2 矩阵。要求：

1. `__init__(self, a, b, c, d)` 保存四个元素（行优先：`[[a, b], [c, d]]`）。
2. `__repr__` 输出 `Matrix2x2(a, b, c, d)` 格式。
3. `__str__` 输出类似 `[a b; c d]` 的矩阵形状。
4. `__add__` 支持两个矩阵相加，返回新矩阵。
5. `__eq__` 判断两个矩阵元素是否全等。
6. `__getitem__` 支持 `m[0]` 返回第一行 `[a, b]`（提示：`i` 为 0 或 1）。

**验证代码**：

```python
m1 = Matrix2x2(1, 2, 3, 4)
m2 = Matrix2x2(5, 6, 7, 8)

assert repr(m1) == 'Matrix2x2(1, 2, 3, 4)'
assert str(m1) == '[1 2; 3 4]'
assert (m1 + m2) == Matrix2x2(6, 8, 10, 12)
assert m1[0] == [1, 2] and m1[1] == [3, 4]
print('All passed!')
```

**延伸挑战**：加上 `__mul__` 实现矩阵乘法（2×2 乘 2×2）。

```python
class Point:
    def __init__(self, x, y):
        self.x, self.y = x, y

    def __repr__(self):
        return f'Point({self.x}, {self.y})'

    def __str__(self):
        return f'({self.x}, {self.y})'

    def __add__(self, other):
        return Point(self.x + other.x, self.y + other.y)

    def __eq__(self, other):
        return (self.x, self.y) == (other.x, other.y)


if __name__ == '__main__':
    p1 = Point(1, 2)
    p2 = Point(3, 4)
    print(p1)              # (1, 2)
    print(repr(p1))        # Point(1, 2)
    print(p1 + p2)         # (4, 6)
    print(p1 == Point(1, 2))  # True
```

## py.oop.repr_str

# Python 对象表示：`__repr__` 与 `__str__`

> **一句话直觉**：当你 `print(obj)` 或在交互式解释器里输入 `obj`、在调试器里查看变量、在 Jupyter 里显示对象时，Python 到底显示什么，完全由 `__repr__` 和 `__str__` 这两个“魔法方法（magic method / dunder method）”决定。学会它们，你的代码可调试性、可读性与工程化水平立刻上一个台阶。

本讲所属课程：`s2u1l5`，知识点 `py.oop.repr_str`，前置无（起点）。

---

## 1. 为什么需要“对象的字符串表示”？

在任何语言里，把对象“变成一段文字”是极高频的操作：打印日志、报错信息、调试、序列化前的预览、Jupyter 单元格的展示……

Python 为这件事设计了两套接口：

- `__repr__(self)`：**面向开发者（developer）**的表示，目标是**无歧义（unambiguous）**，理想情况下能被 `eval()` 还原成等值对象。
- `__str__(self)`：**面向用户（user）**的表示，目标是**可读（readable）**。

内置函数 `repr(x)` 调用 `x.__repr__()`，`str(x)` 调用 `x.__str__()`，`print(x)` 内部使用 `str(x)`，而交互式解释器与容器（list/dict）内部使用 `repr(x)`。

```python
# demo1.py —— 默认行为：所有对象都存在 __repr__/__str__
class Point:
    def __init__(self, x, y):
        self.x, self.y = x, y

p = Point(1, 2)
print(repr(p))   # <__main__.Point object at 0x...> —— 只有地址，很不友好
print(str(p))    # 同上（因为默认 __str__ 会回退到 __repr__）
print([p, p])    # 列表里用的是 repr，所以看到 <__main__.Point object at ...>
```

**结论**：不定义这两个方法，你就只能看到类型名和内存地址，调试成本和协作成本都很高。

---

## 2. `__repr__`：开发者的“可复原”表示

工程约定（参见 Python 官方文档 `repr()` 与 PEP 3140 精神）：

1. `repr` 的返回值应尽量是**合法的 Python 表达式**；
2. 能唯一标识对象的关键状态；
3. 优先用 `Class(...)` 形式，字段用 `name=value`；
4. 不要返回 `None`，必须返回 `str`。

```python
# demo2.py —— 实现符合约定的 __repr__
class Point:
    def __init__(self, x, y):
        self.x, self.y = x, y

    def __repr__(self) -> str:
        # 推荐模式：ClassName(field=value, ...)
        return f"Point(x={self.x!r}, y={self.y!r})"

p = Point(1, 2)
print(repr(p))        # Point(x=1, y=2)
print(p)              # 若未定义 __str__，print 会用 __repr__ → Point(x=1, y=2)
print([p, p])         # [Point(x=1, y=2), Point(x=1, y=2)]  ——容器也友好
# 用 eval 验证可复原性（危险操作，仅演示，请勿对不受控字符串用 eval）
p2 = eval(repr(p))
print(p2.x, p2.y)     # 1 2
```

注意上面用到的 `!r`：这是 f-string 的**转换标志（conversion flag）**，等价于 `repr(value)`。对字符串字段来说，`!r` 会带上引号，从而保持 `repr` 结果仍是合法表达式。

---

## 3. `__str__`：用户友好的显示

`__str__` 不需要可 eval，只需要“好看、好懂”。当类没定义 `__str__` 时，Python 会**自动回退**到 `__repr__`。

```python
# demo3.py —— 同时定义 __repr__ 和 __str__
class Point:
    def __init__(self, x, y):
        self.x, self.y = x, y

    def __repr__(self) -> str:
        return f"Point(x={self.x!r}, y={self.y!r})"

    def __str__(self) -> str:
        return f"({self.x}, {self.y})"

p = Point(3, 4)
print(repr(p))    # Point(x=3, y=4)     ← 开发者视角
print(str(p))     # (3, 4)              ← 用户视角
print(p)          # (3, 4)              ← print 走 __str__
print([p])         # [Point(x=3, y=4)]  ← 容器走 __repr__
f"{p}"            # '(3, 4)'            ← f-string 默认走 __str__
f"{p!r}"          # 'Point(x=3, y=4)'   ← 强制走 __repr__
```

**记忆口诀（口诀很重要）**：

- `repr` —— 给代码、给日志、给容器、给调试器；
- `str` —— 给终端用户、给 `print`、给 f-string 默认。

---

## 4. 与其他 OOP 机制的配合

### 4.1 与 `__eq__` 配合
如果重写 `__eq__`，通常也应重写 `__repr__`（便于比较失败时定位问题）。反之 `__repr__` 不依赖 `__eq__`。

```python
# demo4.py —— __eq__ 与 __repr__ 协作
class Point:
    def __init__(self, x, y):
        self.x, self.y = x, y

    def __repr__(self) -> str:
        return f"Point(x={self.x!r}, y={self.y!r})"

    def __eq__(self, other) -> bool:
        if not isinstance(other, Point):
            return NotImplemented
        return (self.x, self.y) == (other.x, other.y)

assert Point(1, 2) == Point(1, 2)
assert Point(1, 2) != Point(2, 1)
print(Point(1, 2) == Point(1, 2))   # True
```

返回 `NotImplemented`（不是 `False`）是让 Python 尝试反向比较的关键工程细节。

### 4.2 与 `dataclasses` 配合（工程化简易路径）
标准库 `dataclasses` 会自动生成 `__repr__`（可以通过 `repr=False` 关闭）。

```python
# demo5.py —— 用 dataclass 自动生成 __repr__
from dataclasses import dataclass

@dataclass
class Point:
    x: float
    y: float

print(repr(Point(1, 2)))   # Point(x=1, y=2)
```

### 4.3 递归对象要小心
如果对象互相引用，直接递归 `repr` 会导致 `RecursionError`。标准做法是用 `reprlib.recursive_repr` 装饰。

```python
# demo6.py —— 防止 repr 无限递归
from reprlib import recursive_repr

class Node:
    def __init__(self, name):
        self.name = name
        self.parent = None

    @recursive_repr()
    def __repr__(self) -> str:
        parent = self.parent.name if self.parent else None
        return f"Node(name={self.name!r}, parent={parent!r})"

root = Node("root")
child = Node("child")
child.parent = root
root.parent = child      # 制造循环引用
print(repr(root))        # Node(name='root', parent='child') —— 不会爆栈
```

---

## 5. 工程级实践与常见误区速览

- **不要**在 `__repr__` 里做**有副作用（side effect）**的事情，比如发网络请求、读文件、写数据库。
- **不要**返回非字符串。如果返回 `None`，`repr(obj)` 会抛 `TypeError`。
- **不要**让 `__str__` 与 `__repr__` 完全一样 —— 除非你只有一个视角需要服务，且愿意这样省事（很多“小工具类”确实这么干）。
- **应当**让 `repr` 输出包含所有关键属性，字段较多时可考虑 `reprlib` 截断长序列。
- **应当**在 f-string 中习惯用 `!r` 打印调试信息，因为你看到的是无歧义形式（字符串带引号，`None` 显式）。
- 对**敏感信息**（例如密码）不要在 `__repr__` 中泄露明文。

```python
# demo7.py —— 敏感字段脱敏
class Credential:
    def __init__(self, user, password):
        self.user = user
        self.password = password

    def __repr__(self) -> str:
        return f"Credential(user={self.user!r}, password=***)"

print(repr(Credential("alice", "s3cr3t")))
# Credential(user='alice', password=***)
```

---

## 动手练习（建议 20 分钟）

实现一个 `Money` 类，要求：

1. 属性：`amount`（分，整数）与 `currency`（如 `"CNY"`、`"USD"`）。
2. `__repr__` 返回形如 `Money(amount=1250, currency='CNY')` 的字符串，并通过 `eval` 能复原一个等值对象。
3. `__str__` 返回形如 `12.50 CNY` 的字符串（`amount` 以分换算为两位小数的金额）。
4. 实现 `__eq__`：仅当 `amount` 和 `currency` 均相同才认为相等；对不同类型返回 `NotImplemented`。
5. 附加：写一小段自测代码，验证
   - `repr(m)` 结果可通过 `eval` 还原出相等对象；
   - `str(m)` 符合“`X.XX CUR`”格式；
   - `[m]` 打印时与 `repr(m)` 结果一致。

**学习目标对照**：完成这个练习后，你应该能清晰区分“开发者视角 / 用户视角”，并能在任何自定义类中习惯性地补上 `__repr__`。

```python
# money.py —— 综合示例：__repr__ / __str__ / __eq__ 的完整落地
from __future__ import annotations


class Money:
    """表示一定货币金额，amount 以“分”为单位避免浮点误差。"""

    def __init__(self, amount: int, currency: str = "CNY") -> None:
        if not isinstance(amount, int):
            raise TypeError("amount must be int (units of minor currency)")
        self.amount = amount
        self.currency = currency.upper()

    # 开发者视角：无歧义、可 eval 复原
    def __repr__(self) -> str:
        return f"Money(amount={self.amount!r}, currency={self.currency!r})"

    # 用户视角：可读
    def __str__(self) -> str:
        major, minor = divmod(abs(self.amount), 100)
        sign = "-" if self.amount < 0 else ""
        return f"{sign}{major}.{minor:02d} {self.currency}"

    # 与 __repr__ 配套：让比较语义明确
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        return (self.amount, self.currency) == (other.amount, other.currency)

    # 因为定义了 __eq__，显式关闭 __hash__ 或按需实现；这里选择按值可哈希
    def __hash__(self) -> int:
        return hash((self.amount, self.currency))


if __name__ == "__main__":
    m = Money(1250, "cny")
    print(repr(m))          # Money(amount=1250, currency='CNY')
    print(str(m))           # 12.50 CNY
    print(m)                # 12.50 CNY
    print([m, Money(-5, "USD")])  # 容器用 repr

    # 可 eval 复原
    m2 = eval(repr(m))
    print("roundtrip eq:", m == m2)    # True
    print("hash eq:", hash(m) == hash(m2))  # True

    # f-string 两种视角
    print(f"user={m}")      # user=12.50 CNY
    print(f"dev={m!r}")     # dev=Money(amount=1250, currency='CNY')
```

## py.oop.eq_hash

# py.oop.eq_hash：让对象“可比较、可去重、可当字典键”

> **一句话直觉**：当你想判断两个对象是不是“同一个东西”、想把它们放进 `set` 或当 `dict` 的键时，Python 需要你告诉它“什么算相等、相等时哈希值是多少”。学会 `__eq__`（equal，相等比较）和 `__hash__`（hash，哈希值），你的自定义对象才能像内置类型一样自然地去重、查找、比较。

---

## 1. 为什么需要 `__eq__` 和 `__hash__`？

Python 中每个对象默认来自 `object` 类。默认规则很“物理”：

- **默认 `__eq__`**：比较两个变量是否指向同一个内存地址（即 `is` 的效果）。
- **默认 `__hash__`**：根据对象的 `id()` 生成一个整数。

这意味着：两个内容完全一样的对象，默认并不相等，也不能在 `set` 里被去重。

```python
class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

p1 = Point(1, 2)
p2 = Point(1, 2)

print(p1 == p2)        # False：默认比较的是地址
print(len({p1, p2}))   # 2：默认哈希基于 id，两个对象被当成两个不同元素
```

工程上我们往往希望“值相等”就视为同一个对象，例如：两个坐标相同的点、两个内容相同的订单行、两个字段一致的配置项。这时就需要自定义 `__eq__` 和 `__hash__`。

---

## 2. 只实现 `__eq__` 会发生什么？

`__eq__` 决定了 `==` 的结果。实现它之后，两个值相同的对象就“相等”了：

```python
class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __eq__(self, other):
        # 只与同类对象比较，避免 AttributeError
        if not isinstance(other, Point):
            return NotImplemented
        return self.x == other.x and self.y == other.y

p1 = Point(1, 2)
p2 = Point(1, 2)

print(p1 == p2)        # True
print(len({p1, p2}))   # 2：仍然无法去重！
```

**关键结论**：在 Python 中，只要你定义了 `__eq__` 而没定义 `__hash__`，Python 会把该类的 `__hash__` 自动设为 `None`，使实例**不可哈希（unhashable）**。

`set` 和 `dict` 键都依赖哈希。上面这段代码如果直接放入 `set`，在某些 Python 版本中会抛 `TypeError: unhashable type`。这就是初学者最常见的坑：**改了相等规则，忘了同步哈希规则**。

---

## 3. `__hash__` 的契约：相等必同哈希

自定义 `__hash__` 必须满足两个契约（contract，约定）：

1. **一致性**：同一次运行中，同一个对象多次调用 `__hash__` 应返回相同值（对象属性若可变，就不要改用于哈希的属性）。
2. **相等必同哈希**：若 `a == b`，则 `hash(a) == hash(b)` 必须成立。反之不要求：哈希相同不一定相等（哈希碰撞，hash collision，正常现象）。

推荐做法：把参与相等判断的字段组成一个元组，交给内置 `hash()`：

```python
class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __eq__(self, other):
        if not isinstance(other, Point):
            return NotImplemented
        return (self.x, self.y) == (other.x, other.y)

    def __hash__(self):
        # 用与 __eq__ 相同的字段计算哈希，天然满足契约
        return hash((self.x, self.y))

p1 = Point(1, 2)
p2 = Point(1, 2)

print(p1 == p2)              # True
print(hash(p1) == hash(p2))  # True
print(len({p1, p2}))         # 1：成功去重
print({p1: 'origin-like'})   # 可作为 dict 键
```

---

## 4. 与 `is`、`=` 赋值、`__ne__`、`dataclass` 的关系

- **`a is b`** 判断身份（同一对象），**`a == b`** 判断相等。永远不要用 `==` 判断 `None`，应使用 `is None`。
- `a = b` 只是让两个名字指向同一对象，与相等无关。
- 定义了 `__eq__` 后，`!=` 默认是 `__eq__` 结果取反，通常无需额外写 `__ne__`。
- 如果类要作为**字典键或集合元素**，请保证用于哈希与相等的字段是**不可变字段**；若字段可变，就把类设计为不可哈希（`__hash__ = None`）并改用 `list` 存。
- `dataclasses.dataclass`（数据类）在 `frozen=True` 时会自动生成基于字段的 `__eq__` 和 `__hash__`；`frozen=False` 时生成 `__eq__` 但 `__hash__` 为 `None`。

```python
from dataclasses import dataclass

@dataclass(frozen=True)   # 冻结：字段不可变，自动生成 __eq__ 与 __hash__
class PointDC:
    x: int
    y: int

print(len({PointDC(1, 2), PointDC(1, 2)}))  # 1

@dataclass                # 非冻结：有 __eq__，但不可哈希
class MutablePoint:
    x: int
    y: int

try:
    {MutablePoint(1, 2)}
except TypeError as e:
    print('TypeError:', e)  # unhashable type: 'MutablePoint'
```

---

## 5. 工程级实践清单

1. **成对出现**：只要实现了 `__eq__`，就要明确 `__hash__` 是“按字段算”还是“禁用”。
2. **不可变才可哈希**：参与 `__eq__`/`__hash__` 的字段应不可变；否则对象放入 `set` 后改字段会“找不到自己”。
3. **`NotImplemented` 而非 `False`**：`__eq__` 遇到不支持的类型应返回 `NotImplemented`，让 Python 尝试反向比较，而不是直接判 `False`。
4. **优先 `dataclass`**：纯数据类用 `@dataclass(frozen=True)` 少写样板代码。
5. **可读性**：`__hash__` 使用与 `__eq__` 完全相同的字段元组，契约自动成立。

---

## 动手练习

在本地创建 `inventory.py`，完成以下任务：

1. 定义类 `Product`，字段 `sku: str`、`name: str`、`price: float`。
2. 实现 `__eq__`：仅当 `sku` 相同时视为同一商品（价格变动不影响相等性）。
3. 实现 `__hash__`：保证与 `__eq__` 契约一致，使 `Product` 可作为 `set` 元素与 `dict` 键。
4. 用至少 3 个 `Product` 实例验证：
   - 相同 `sku`、不同 `price` 的两个对象相等且哈希相同；
   - 放入 `set` 后被正确去重；
   - 用其中一个对象作 `dict` 键存储库存数量并能正确读出。
5. 再写一个 `MutableProduct` 类（`@dataclass` 非 frozen），尝试放入 `set`，观察并解释 `TypeError`。

**提示**：只要 `__hash__` 基于 `(self.sku,)` 计算，与 `__eq__` 的判断字段一致即可。

```python
from dataclasses import dataclass


class Product:
    """商品：以 sku（stock keeping unit，库存单位）作为唯一标识。"""

    def __init__(self, sku: str, name: str, price: float):
        self.sku = sku
        self.name = name
        self.price = price

    def __eq__(self, other):
        # 只与 Product 比较；不认识的类型交给对方或返回 NotImplemented
        if not isinstance(other, Product):
            return NotImplemented
        return self.sku == other.sku

    def __hash__(self):
        # 与 __eq__ 使用的字段保持一致，满足“相等必同哈希”契约
        return hash((self.sku,))

    def __repr__(self):
        return f"Product(sku={self.sku!r}, name={self.name!r}, price={self.price})"


# --- 验证相等与哈希 ---
p1 = Product("A100", "键盘", 199.0)
p2 = Product("A100", "键盘", 259.0)  # sku 相同、价格不同
a3 = Product("B200", "鼠标", 89.0)

print("p1 == p2 :", p1 == p2)               # True
print("hash equal:", hash(p1) == hash(p2))   # True
print("p1 == a3 :", p1 == a3)               # False

# --- 在 set 中去重 ---
bucket = {p1, p2, a3}
print("set size :", len(bucket))             # 2，p1 与 p2 去重

# --- 作为 dict 键 ---
stock = {p1: 10}
stock[p2] = stock.get(p2, 0) + 5             # 同一 sku，累加库存
print("stock    :", stock[p1])               # 15

# --- 对照：非 frozen 的 dataclass 有 __eq__ 但不可哈希 ---
@dataclass
class MutableProduct:
    sku: str
    name: str
    price: float

try:
    {MutableProduct("A100", "键盘", 199.0)}
except TypeError as e:
    print("TypeError:", e)                    # unhashable type: 'MutableProduct'
```


---

## 本课题目

### single_choice · None



- [A] 它们必须由开发者显式调用才会生效，例如手动写 obj.__str__()
- [B] 它们通常由 Python 的内置操作（如 print、len、+ 等）自动触发
- [C] 它们只能定义在模块级别，不能定义在类里
- [D] 它们的名字前后各有一个下划线，例如 _init_

**参考答案**：1

**解析**：魔术方法是被内置语法/内置函数隐式调用的钩子，如 print(obj) 会触发 __str__，len(obj) 会触发 __len__。选项 A 错在「必须显式调用」；选项 C 错在它们正是定义在类中的；选项 D 描述的是单下划线，名称不正确。

### single_choice · None



- [A] Point(3)
- [B] <__main__.Point object at 0x...>
- [C] 3
- [D] 报错，因为 __str__ 不能返回字符串

**参考答案**：0

**解析**：print() 会调用对象的 __str__ 方法，返回 'Point(3)' 并打印。选项 B 是没有定义 __str__ 时的默认表示；选项 C 忽略了格式化字符串；选项 D 说反了，__str__ 正是要求返回字符串。

### single_choice · None



- [A] 没有定义 __str__ 也没有定义 __repr__
- [B] 定义了 __str__ 但返回了一个整数
- [C] 只定义了 __repr__ 且返回字符串
- [D] 定义了 __str__ 且返回字符串

**参考答案**：1

**解析**：__str__ 必须返回字符串，返回非字符串会引发 TypeError。选项 A、C、D 都不会抛出异常：A 用默认表示，C 使用 __repr__ 作为回退，D 正常返回字符串。

### single_choice · None



- [A] True
- [B] False
- [C] 报错，因为 __eq__ 不能自定义
- [D] None

**参考答案**：0

**解析**：a == b 会调用 a.__eq__(b)，比较两个实例的 v 值均为 1，返回 True。若未定义 __eq__，默认为基于身份比较，此时可能为 False；但本题已重载。C、D 明显错误。

### single_choice · None



- [A] Temp(20)
- [B] <__main__.Temp object at 0x...>
- [C] 20
- [D] 报错，因为没有定义 __str__

**参考答案**：0

**解析**：当未定义 __str__ 时，print() 会回退到 __repr__，从而打印 'Temp(20)'。选项 B 是完全没有定义两者的默认情况；选项 D 错误，__str__ 不是必需的。

### single_choice · None



- [A] 魔术方法都必须在类中显式以 obj.__method__() 方式调用
- [B] 魔术方法的名称由 Python 语言规范定义，实现后可让对象与内置语法自然协作
- [C] 任意双下划线开头和结尾的方法都是魔术方法
- [D] 魔术方法只能用于数字类型

**参考答案**：1

**解析**：魔术方法的名字是语言规范约定的，实现后能让对象支持 +、len、print 等操作。选项 A 与「由内置操作隐式调用」相悖；选项 C 错误，需是规范定义的名字；选项 D 错误，任何类都可用。

### single_choice · None



- [A] __loop__
- [B] __iter__
- [C] __for__
- [D] __next__ 单独即可，无需 __iter__

**参考答案**：1

**解析**：iter(obj) 与 for 循环会调用 __iter__ 获取迭代器；迭代器自身需实现 __next__。单有 __next__ 而没有 __iter__ 通常不足以让对象直接用于 for，因为缺少获取迭代器的入口。__loop__ 和 __for__ 不是 Python 内置魔术方法。

### single_choice · None



- [A] 打印 ten
- [B] 打印 3
- [C] 引发 TypeError，因为 __len__ 必须返回非负整数
- [D] print 会忽略 __len__ 并打印 0

**参考答案**：2

**解析**：__len__ 要求返回非负整数，返回字符串会触发 TypeError。选项 A、B、D 都假设 Python 会接受或忽略错误返回值，与语言规范不符。

### single_choice · None



- [A] 只有在使用切片语法时才会被调用
- [B] obj[key] 这样的下标访问会调用它
- [C] 它必须返回一个整数
- [D] 它与 __setitem__ 完全一样

**参考答案**：1

**解析**：obj[key] 会触发 __getitem__；传入切片对象时也可处理切片。它不要求返回整数，且与负责赋值 obj[key] = value 的 __setitem__ 职责不同。因此 A、C、D 错误。

### single_choice · None



- [A] S 然后 R
- [B] R 然后 R
- [C] S 然后 S
- [D] R 然后 S

**参考答案**：0

**解析**：print(obj) 使用 __str__ 输出 'S'；内置函数 repr(obj) 使用 __repr__ 输出 'R'。因此顺序为 S、R。选项 B、C、D 都混淆了两者的调用来源。

### single_choice · None



- [A] __del__
- [B] __destroy__
- [C] __close__
- [D] __end__

**参考答案**：0

**解析**：对象被垃圾回收时会调用 __del__，可用于清理，但不保证及时执行。__destroy__、__close__、__end__ 都不是 Python 中对象销毁对应的魔术方法；__close__ 常用于上下文管理器，但需搭配 __enter__/__exit__。

### single_choice · None



- [A] operator.add(a, b) 会绕过 __add__，直接做数值加法
- [B] operator.add(a, b) 最终也会调用 a.__add__(b)，行为一致
- [C] 两者完全无关
- [D] 只有 operator.add 能处理自定义对象

**参考答案**：1

**解析**：operator.add(a, b) 与 a + b 语义相同，都会调用 a.__add__(b)（在可行时）。它不会绕过魔术方法，也不是只能用于自定义对象，因此 A、C、D 错误。

### single_choice · None



- [A] __size__
- [B] __length__
- [C] __len__
- [D] __count__

**参考答案**：2

**解析**：内置函数 len(obj) 会调用对象的 __len__ 方法。__size__、__length__、__count__ 都不是 Python 中与 len() 对应的魔术方法，属于命名上的常见误解。

### single_choice · None



- [A] a 的 __add__ 方法，且 other 是 b
- [B] b 的 __add__ 方法，且 other 是 a
- [C] 内置函数 add()
- [D] Python 会随机选择一方的方法调用

**参考答案**：0

**解析**：a + b 等价于 a.__add__(b)，即调用左侧对象的 __add__ 并传入右侧对象。Python 不会默认调用右侧或使用随机选择。内置的 operator.add 最终也是走 __add__，但不是直接命中。

### single_choice · None



- [A] __init__、__str__、__len__、__eq__
- [B] __init__、__print__、__size__、__equal__
- [C] __construct__、__str__、__length__、__compare__
- [D] __new__、__say__、__count__、__same__

**参考答案**：0

**解析**：__init__、__str__、__len__、__eq__ 都是 Python 内置的魔术方法。其余选项中的 __print__、__size__、__equal__、__construct__、__length__、__compare__、__say__、__count__、__same__ 均不是 Python 定义的魔术方法。

### single_choice · None



- [A] 两者必须返回完全相同的字符串
- [B] __str__ 面向用户友好展示，__repr__ 更偏向开发者调试时的准确表示
- [C] 只有 __repr__ 会被 print() 使用，__str__ 完全不会被调用
- [D] 如果只定义了 __repr__，print() 一定不会使用它

**参考答案**：1

**解析**：__str__ 期望返回对用户友好的字符串；__repr__ 期望返回对开发者更有用、可重建对象的字符串。print() 优先调用 __str__，若未定义 __str__ 会退回到 __repr__，因此选项 C、D 错误；选项 A 错误，两者通常不同。

### single_choice · None



- [A] 两行都会打印 5
- [B] 第一行打印 5，第二行打印类似 <__main__.Box object at 0x...> 的默认表示
- [C] 第一行报错，因为 n 是私有属性
- [D] 第二行报错，因为 Box 没有 __str__

**参考答案**：1

**解析**：b.n 可直接访问打印 5；由于 Box 未定义 __str__ 或 __repr__，print(b) 会使用 object 的默认表示。属性 n 并非私有，没有 __str__ 也不会导致 print 报错，因此 A、C、D 错误。

### single_choice · None



- [A] __in__
- [B] __contains__
- [C] __has__
- [D] __find__

**参考答案**：1

**解析**：in 运算符会调用右侧对象的 __contains__ 方法。__in__、__has__、__find__ 都不是 Python 中与 in 对应的魔术方法，属于常见臆造名称。

### single_choice · None



- [A] __init__ 负责创建对象并返回该对象
- [B] __init__ 在对象已经创建之后被调用，用于初始化实例属性
- [C] __init__ 必须显式 return self
- [D] __init__ 与 __new__ 是完全等价的

**参考答案**：1

**解析**：__init__ 是在实例被创建（由 __new__ 完成）之后调用的初始化方法，用于设置实例属性，不应返回对象。选项 A、C 把 __new__ 的职责错放到 __init__ 上；选项 D 错误，两者职责不同。

### single_choice · None



- [A] 0
- [B] 3
- [C] 报错，因为自定义对象不能用于 len()
- [D] 打印对象本身

**参考答案**：1

**解析**：len(c) 会调用 c.__len__()，返回 self.data 的长度 3。因为已定义 __len__，自定义对象同样可用于 len()，所以选项 C 错误；A、D 均不符合代码逻辑。

### single_choice · None



- [A] `__str__` 面向最终用户，应返回可读性好的描述；`__repr__` 面向开发者，应尽量返回能重建对象的信息
- [B] `__repr__` 面向最终用户，`__str__` 面向开发者
- [C] 两者完全等价，Python 总是优先调用 `__str__`
- [D] `__str__` 只用于交互式解释器显示，`__repr__` 只用于 `print`

**参考答案**：0

**解析**：官方约定：`__repr__` 目标是「无歧义、面向开发者、理想情况下可用 eval 重建」，`__str__` 目标是「可读、面向用户」。当只定义了 `__repr__` 时，`str()` 会退回到 `__repr__`；反过来则不成立。

### single_choice · None



- [A] 抛出 AttributeError
- [B] 返回 `<object object at 0x...>` 形式
- [C] 退回到调用 `__repr__` 的结果
- [D] 返回空字符串

**参考答案**：2

**解析**：`object.__str__` 的默认实现就是调用 `__repr__`。所以只重写 `__repr__` 时，`str()`、`print()`、f-string 都会使用该 `__repr__` 的结果。

### multi_choice · None



- [A] 只定义 `__repr__` 时，`str()` 会使用 `__repr__`
- [B] 只定义 `__str__` 时，`repr()` 会使用 `__str__`
- [C] `print(obj)` 通常使用 `str(obj)`
- [D] 交互式解释器回显使用 `repr(obj)`
- [E] 容器（如 list）打印内部元素时，使用元素的 `__repr__`

**参考答案**：[0, 2, 3, 4]

**解析**：回退关系是单向的：`__str__` 缺失时退到 `__repr__`，但 `__repr__` 缺失不会退到 `__str__`。print 用 str，解释器回显用 repr，容器内元素的显示用 repr。

### multi_choice · None



- [A] 包含类名，便于在复杂输出中识别对象类型
- [B] 对属性值使用 `!r` 转换，保证字符串等值显示无歧义
- [C] 为避免泄露信息，把 `__repr__` 固定返回 `'<object>'`
- [D] 返回能唯一区分对象的关键属性值
- [E] 把耗时 I/O 或网络请求放进 `__repr__` 以显示实时数据

**参考答案**：[0, 1, 3]

**解析**：repr 应无歧义、信息量够、且调用开销小、无副作用。固定返回占位字符串会丢失可辨识性；在 repr 中做 I/O 会在调试/日志中产生意外副作用。

### multi_choice · None



- [A] `print(m)` 输出 `10.00 元`
- [B] `print([m])` 显示 `[Money(10)]`
- [C] `print(repr(m))` 输出 `10.00 元`
- [D] `f"{m}"` 输出 `Money(10)`
- [E] `print(str(m))` 输出 `10.00 元`

**参考答案**：[0, 1, 4]

**解析**：`str(m)` 与 f-string 默认走 `__str__`，`repr(m)` 走 `__repr__`，容器 `[m]` 打印元素时用 repr，所以显示 `[Money(10)]`。

### multi_choice · None



- [A] 返回非字符串会在调用 repr() 时抛 TypeError
- [B] `__repr__` 内部的递归调用可能导致递归深度错误
- [C] 在 `__repr__` 中调用 `str(self)` 且 `__str__` 又调用 `repr(self)` 会死循环
- [D] `__repr__` 只能被显式调用，打印容器时不会被使用
- [E] 若 `__repr__` 依赖的属性尚未初始化，可能抛 AttributeError

**参考答案**：[0, 1, 2, 4]

**解析**：打印容器时会对元素调用 repr，所以选项 D 错误。其余都是常见陷阱：类型错误、self 引用导致的递归、str/repr 互相调用导致无限递归、初始化未完成时访问属性失败。

### fill_blank · None



**参考答案**：["!r", "!r`", "!r ", "r"]

**解析**：f-string 用 `{value!r}` 调用 repr(value)，`!s` 调用 str，`!a` 调用 ascii。

### fill_blank · None



**参考答案**：["__repr__", "__repr__(self)", "object.__repr__"]

**解析**：`object.__str__` 默认委托给 `__repr__`。所以 `str()` 在缺少 `__str__` 时会使用 `__repr__`。

### code_reading · None



**参考答案**：[P(1), P(2)]

**解析**：列表打印时对每个元素使用 repr。因为定义了 `__repr__` 返回 `P(n)`，因此输出 `[P(1), P(2)]`；若用 str 则会得到 `[p-1, p-2]`。

### code_reading · None



**参考答案**：抛出 TypeError：__repr__ returned non-string (type int)。因为 __repr__ 必须返回 str 类型，返回 int 时 repr() 会报错。

**解析**：__repr__ 的返回值会被 `object.__repr__` 或内置 repr() 直接使用；若非字符串类型，解释器在拼装结果时抛 TypeError。

### scenario · None



**解析**：调试和日志场景应实现 `__repr__`，返回包含类名和关键属性的字符串，对属性值使用 `!r` 保证无歧义。这样 repr、日志、容器显示都能识别对象。

### scenario · None



**解析**：应向用户展示时实现 `__str__` 返回可读文案；面向开发者调试时实现 `__repr__` 返回含类名与关键属性的无歧义字符串。二者用途不同，混用会导致用户看到难以理解的内部状态，或调试时信息不足。

### single_choice · None



- [A] `__str__` 返回的内容
- [B] 默认的 `<ClassName object at 0x...>` 形式
- [C] `TypeError`
- [D] 对象的 `__dict__` 内容

**参考答案**：1

**解析**：交互式解释器使用 `repr()` 来显示表达式结果，而 `repr()` 不会退回到 `__str__`。因此只重写 `__str__` 时，交互式显示的仍是默认的 `__repr__`。

### single_choice · None



- [A] `return self.name`
- [B] `return f"<{type(self).__name__} name={self.name!r}>"`
- [C] `return str(self.__dict__)`
- [D] `return "对象"`

**参考答案**：1

**解析**：规范做法是包含类名和关键属性，并对属性值用 `!r` 保证无歧义（字符串带引号、可区分类型）。只返回属性值或固定提示文本都缺乏可辨识性。

### single_choice · None



- [A] `Point(1, 2)`
- [B] `<__main__.Point object at 0x...>`
- [C] `{'x': 1, 'y': 2}`
- [D] 抛出异常

**参考答案**：1

**解析**：没有定义 `__repr__` 时，使用 `object.__repr__`，返回形如 `<模块名.类名 object at 地址>` 的字符串。具体地址每次运行不同。

### single_choice · None



- [A] 可以返回非字符串类型，Python 会自动转换
- [B] 必须返回字符串，否则会抛 TypeError
- [C] 只能返回单行字符串，多行会报错
- [D] 返回 None 表示使用默认实现

**参考答案**：1

**解析**：`__repr__`（以及 `__str__`）必须返回字符串对象，返回非 str 会在调用 repr() 时抛 TypeError。多行是允许的，只是惯例上单行更友好。

### single_choice · None



- [A] `!r` 表示对表达式结果调用 `repr()`，`!s` 表示调用 `str()`
- [B] `!r` 表示对表达式结果调用 `str()`
- [C] `!r` 只在调试模式下生效
- [D] `!r` 只能用于自定义对象，不能用于字符串

**参考答案**：0

**解析**：`{value!r}` 调用 repr(value)，`{value!s}` 调用 str(value)，`{value!a}` 调用 ascii(value)。在 `__repr__` 中给属性加 `!r` 可以保证嵌套值的显示无歧义。

### single_choice · None



- [A] `return f"Box({self.items})"`
- [B] `return f"Box({self.items!r})"`
- [C] `return "Box(" + str(self.items) + ")"`
- [D] `return "Box(" + len(self.items) + ")"`

**参考答案**：1

**解析**：`!r` 保证列表中的字符串等元素带引号显示（如 `['a']` 而非 `[a]`），符合 repr 的无歧义要求。直接插值调用的是 `str`。

### single_choice · None



- [A] `__repr__` 的返回值必须能被 `json.loads` 解析
- [B] 对于简单对象，`eval(repr(obj))` 应能构造出一个等价对象
- [C] `__repr__` 必须调用构造函数
- [D] `__repr__` 的返回值必须是对象的序列化字节

**参考答案**：1

**解析**：官方的建议是「如果可能，让 repr 看起来像能重建该对象的表达式」。这适用于简单值对象；对含不可重建状态的对象不做强求。

### single_choice · None



- [A] 日志调试时展示对象内部状态
- [B] 在交互式解释器中查看对象
- [C] 向终端用户展示友好信息，如错误提示、界面文本
- [D] 为对象生成唯一编码

**参考答案**：2

**解析**：`__str__` 面向最终用户，用于 `print`、界面文本等场景；调试和解释器显示属于 `__repr__` 的职责。

### single_choice · None



- [A] 任何自定义类的实例默认都是可哈希的
- [B] 只有定义了 __eq__ 的类实例才可哈希
- [C] 定义了 __eq__ 但未定义 __hash__ 的类，其 __hash__ 会被设为 None，实例不可哈希
- [D] 定义了 __hash__ 的类实例一定可哈希，与 __eq__ 无关

**参考答案**：2

**解析**：当类定义了 __eq__ 而没有定义 __hash__ 时，Python 会把该类的 __hash__ 隐式置为 None，导致实例不可哈希。若希望保持可哈希，需显式定义 __hash__。

### single_choice · None



- [A] 两个对象若不相等，则它们的哈希值一定不同
- [B] 两个对象若相等，则它们的哈希值必须相同
- [C] 哈希值相同的对象一定相等
- [D] 对象的哈希值与其相等性判断完全无关

**参考答案**：1

**解析**：这是哈希协议的核心约定：若 a == b 为真，则 hash(a) 必须等于 hash(b)。反过来不成立：哈希相同的对象不一定相等（允许哈希冲突）。

### multi_choice · None



- [A] 定义了 __eq__ 但未定义 __hash__
- [B] __hash__ 基于参与 __eq__ 的属性计算
- [C] 对象存入 set 后修改了参与哈希的属性
- [D] __eq__ 与 __hash__ 基于不同的属性集

**参考答案**：[0, 2, 3]

**解析**：选项 0 会使实例不可哈希；选项 2 会让哈希值在存入后改变，导致查找失败；选项 3 违反「相等则哈希相同」。选项 1 是正确做法。

### multi_choice · None



- [A] 对象在其生命周期内哈希值应保持稳定
- [B] 可变对象通常不应参与哈希计算
- [C] 任何对象只要不是 None 就可哈希
- [D] 实现 __hash__ 时通常应基于不可变属性

**参考答案**：[0, 1, 3]

**解析**：可哈希要求哈希值在对象作为键的期间稳定，因此应基于不可变属性。可变对象参与哈希容易破坏稳定性。选项 2 错误：不可哈希的对象很多，如 list、dict、set。

### multi_choice · None



- [A] 默认的 __eq__ 比较的是对象身份（id），即是否为同一对象
- [B] 默认的 __eq__ 会逐属性比较
- [C] 两个内容相同但不同的实例默认不相等
- [D] 重写 __eq__ 会影响该类的 __hash__ 默认行为

**参考答案**：[0, 2, 3]

**解析**：默认 __eq__ 基于身份比较，内容相同但不同实例默认不相等。重写 __eq__ 时若未定义 __hash__，Python 会把 __hash__ 置为 None，从而改变默认可哈希行为，故选项 3 正确；选项 1 是错的（逐属性比较需要自己实现）。

### multi_choice · None



- [A] 同时实现 __eq__ 与 __hash__
- [B] 确保相等对象返回相同哈希
- [C] 用于哈希和相等判断的属性应保持不可变
- [D] 让 __hash__ 返回 id(self) 即可

**参考答案**：[0, 1, 2]

**解析**：选项 0、1、2 都是保证哈希容器正确工作的要点。选项 3 不合适：基于 id 的哈希与基于属性的相等判断不一致，会违反「相等则哈希相同」的约定。

### fill_blank · None



**参考答案**：["None", "none", "None值"]

**解析**：定义 __eq__ 而未定义 __hash__ 时，Python 会把该类的 __hash__ 隐式设为 None，使实例不可哈希。

### fill_blank · None



**参考答案**：["不可变", "immutable", "不可变属性"]

**解析**：基于不可变属性计算哈希，才能保证对象作为键期间哈希值不变，避免查找失败。

### fill_blank · None



**参考答案**：["hash(b)", "hash（b）", "hash(b)的值"]

**解析**：这是哈希协议的核心约定：相等对象必须有相同的哈希值。

### scenario · None



**解析**：必须同时实现 __eq__ 与 __hash__，并保证基于同一组属性（如账号名）计算，且这些属性应不可变，以满足「相等则哈希相同」并保证哈希值稳定。

### scenario · None



**解析**：对象存入 set/dict 时其哈希值决定存放位置。若参与哈希的属性被修改，哈希值改变，原位置无法再被定位，导致查找失败。修复思路是让参与哈希的属性不可变，或在修改后重新插入。

### single_choice · None



- [A] __init__ 与 __new__
- [B] __eq__ 与 __hash__
- [C] __str__ 与 __repr__
- [D] __len__ 与 __getitem__

**参考答案**：1

**解析**：__eq__ 定义了相等性语义，__hash__ 定义了哈希值。二者必须遵循「相等则哈希相同」的约定，否则在基于哈希的容器中会出现查找失败、重复元素等问题。

### single_choice · None



- [A] 可变对象只要实现了 __hash__ 就适合作为键
- [B] 列表等可变内置类型不可哈希，因此不能作为 dict 的键
- [C] 字典的键可以是任意对象，包括列表
- [D] 字符串是不可变的，所以不能作为 dict 的键

**参考答案**：1

**解析**：list、dict、set 等可变内置类型未实现 __hash__（其 __hash__ 为 None），因此不可哈希，不能作键。字符串不可变且可哈希，完全可以作键。

### single_choice · None



- [A] 正常放入，且能正确去重
- [B] 抛出 TypeError: unhashable type
- [C] 抛出 ValueError: hash not defined
- [D] 能放入，但相等对象会被当成不同元素

**参考答案**：1

**解析**：重写 __eq__ 而未定义 __hash__ 时，Python 会将该类的 __hash__ 设为 None，尝试哈希会抛出 TypeError: unhashable type。

### single_choice · None



- [A] 只定义 __eq__，让 Python 自动推导哈希
- [B] 只定义 __hash__，相等性用默认的同一性判断
- [C] 同时定义 __eq__ 和 __hash__，并保证相等对象的哈希一致
- [D] 定义 __eq__，并在每次比较时手动更新哈希

**参考答案**：2

**解析**：要同时支持语义相等和哈希容器，必须同时实现 __eq__ 与 __hash__，且二者满足「相等则哈希相同」的约定。

### single_choice · None



- [A] 默认的 __hash__ 基于对象的内存地址（id）计算，因此同一对象在生命周期内哈希值一般稳定
- [B] 默认的 __hash__ 基于对象的所有属性值计算
- [C] 默认的 __hash__ 每次调用都会返回不同的随机值
- [D] 默认的 __hash__ 对于任何对象都会抛出异常

**参考答案**：0

**解析**：object 的默认 __hash__ 基于 id 计算，同一对象在其生命周期内哈希值保持稳定。它不考虑属性值，因此两个内容相同但不同实例的对象默认不相等、哈希也不同。

### single_choice · None



- [A] 对象实现了 __eq__ 但没有实现 __hash__
- [B] 对象参与哈希的属性在存入后被修改
- [C] 对象实现了 __hash__ 返回常量
- [D] 对象没有实现 __repr__

**参考答案**：1

**解析**：对象存入 dict 时其哈希值被用于定位桶。如果参与哈希计算的属性之后被修改，哈希值改变，原来存入的位置就找不到了，导致查找失败。

### single_choice · None



- [A] 违反「相等则哈希相同」的约定，可能破坏哈希容器
- [B] 完全没有风险，是推荐做法
- [C] 会导致 __eq__ 无法被调用
- [D] 会使对象自动变为可哈希

**参考答案**：0

**解析**：如果让不同类的实例在属性相同时相等，就必须保证它们的 __hash__ 也一致。否则在 dict/set 中会出现相等对象哈希不同、查找失败的情况，违反哈希协议。

### single_choice · None



- [A] 让 __hash__ 返回固定常量 0
- [B] 让 __hash__ 基于与 __eq__ 相同的一组属性计算
- [C] 让 __hash__ 返回 id(self)
- [D] 不实现 __eq__，仅实现 __hash__

**参考答案**：1

**解析**：只要 __hash__ 基于与 __eq__ 判定相同的那组属性计算，相等的对象就必然得到相同的哈希值。返回常量也能满足约定，但会严重降低性能；返回 id(self) 与基于属性的相等判断不一致。
