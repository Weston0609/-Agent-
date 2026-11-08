# s1u4l3 Python 元组类型 `tuple` 完全指南 / 元组解包（Tuple Unpacking）：一句话直觉

> 来源 `content/lessons/s1u4l3.json`

## py.type.tuple

# Python 元组类型 `tuple` 完全指南

## 一句话直觉

**元组（tuple）是 Python 中“不可变的有序容器”——一旦创建就不能增删改元素，这让它天生适合表达“固定结构的数据”，例如坐标 `(x, y)`、RGB 颜色 `(r, g, b)`、数据库查询的一行结果。**

学习 `tuple` 类型注解（type annotation）的意义在于：让类型检查器（type checker，如 mypy、pyright）能帮你在运行前发现“长度不对”“元素类型写错”的问题。

---

## 第 1 节：元组本身——不可变、可迭代、可解包

元组用圆括号 `()` 定义（逗号才是关键，括号可以省略）。它支持索引、切片、迭代、解包，但**不支持原地修改**。

```python
# 01_basic_tuple.py
point = (3, 5)             # 一个二元元组
empty = ()                 # 空元组
single = (42,)             # 单元素元组：必须有逗号！
not_a_tuple = (42)         # 这不是元组，就是整数 42

print(type(point))         # <class 'tuple'>
print(point[0], point[1])  # 3 5

x, y = point               # 解包（unpacking）
print(x + y)               # 8

# point[0] = 99            # 会抛 TypeError：'tuple' object does not support item assignment
```

**关键结论：**
- 逗号才决定是不是元组，`(42)` 是整数，`(42,)` 才是元组。
- 元组不可变 → 可以作为字典的键（key）、集合的元素；列表不行。

---

## 第 2 节：注解的三种“形状”——定长、变长、空

Python 3.9+ 起可以直接写内置泛型 `tuple[...]`（无需 `from typing import Tuple`）。类型注解里元组有**三种形态**：

1. **定长元组** `tuple[T1, T2, ...]`：长度和每个位置类型都固定。
2. **变长同型元组** `tuple[T, ...]`：任意长度，所有元素都是 `T`。
3. **空元组** `tuple[()]`：只允许 `()`。

```python
# 02_annotation_shapes.py

# 形态 1：定长，位置类型固定
rgb: tuple[int, int, int] = (255, 0, 128)

# 形态 2：变长，所有元素同型
scores: tuple[int, ...] = (90, 85)
scores = (90, 85, 77)      # OK：变长
scores = ()                # OK：空也符合

# 形态 3：只允许空元组
never_has_content: tuple[()] = ()

# 一个经典的“写错”示例：
bad: tuple[int] = (1, 2, 3)   # 类型检查器会报错：长度为 1
```

**为什么 `tuple[int]` 表示“长度恰好为 1”？**
因为 `tuple[int]` 是“定长元组”形态的语法糖，它等价于 `tuple[int]`（长度为 1，位置 0 是 int）。要表达“任意长度的 int 元组”，必须写 `tuple[int, ...]`。

---

## 第 3 节：裸 `tuple` vs `tuple[Any, ...]`

不带方括号的 `tuple` 是合法注解，它等价于 `tuple[Any, ...]`——即“任意长度、任意元素”，基本等于放弃检查。

```python
# 03_plain_vs_any.py
z: tuple = ("foo", "bar")   # 等价于 tuple[Any, ...]
z = (1, 2, 3)                # OK
z = ()                       # OK

# 但如果想约束元素类型，就必须显式写变长形态：
x: tuple[int, ...] = (1, 2)
x = (1, 2, 3)                # OK
# x = ("foo", "bar")         # 类型检查器报错：元素必须是 int
```

**经验法则：** 生产代码里尽量避免裸 `tuple`，要么写清长度（定长），要么写 `tuple[T, ...]`（变长），让类型系统真正发挥作用。

---

## 第 4 节：`type[C]`——变量装的是“类本身”而不是“类的实例”

这是一个常被混淆的概念。`x: C` 表示 `x` 是 `C` 的实例；而 `x: type[C]` 表示 `x` 是 `C` 这个类对象本身（可以调用它来构造实例）。

```python
# 04_type_of_classes.py
class User:
    def __init__(self, name: str = "anon") -> None:
        self.name = name

class ProUser(User):
    pass

# 工厂函数：接收一个“类”作为参数，返回它的实例
def make_new_user(user_class: type[User]) -> User:
    return user_class()

print(make_new_user(User).name)      # anon
print(make_new_user(ProUser).name)   # anon
# make_new_user(User())              # 类型检查器报错：传了实例而不是类
# make_new_user(int)                 # 类型检查器报错：int 不是 User 子类
```

**关键结论：**
- `type[User]` 是**协变（covariant）**的：`type[ProUser]` 可以当作 `type[User]` 使用。
- `type[Any]` 等价于裸 `type`，是所有元类（metaclass）体系的根。

---

## 第 5 节：工程进阶——`*Ts` 变长类型参数

PEP 646 引入的“类型变量元组（TypeVarTuple）”让元组注解可以在泛型里“展开”，用于精确表达“变长但每个位置类型都被跟踪”的场景（例如张量的形状）。

```python
# 05_variadic.py
from typing import TypeVarTuple, Unpack  # Python 3.11+ 也可以用内置写法

Ts = TypeVarTuple("Ts")

def move_first_to_last(tup: tuple[int, Unpack[Ts]]) -> tuple[Unpack[Ts], int]:
    first, *rest = tup
    return (*rest, first)

# 简单演示（实际返回值类型由类型检查器推导）
print(move_first_to_last((1, "spam", 3.0)))  # ('spam', 3.0, 1)
```

> 提示：本节是“进阶视野”，初学阶段只需知道有这种能力；日常业务代码用 `tuple[T, ...]` 和 `tuple[A, B]` 已经覆盖 95% 场景。

---

## 常见误区（pitfalls）

1. **`(42)` 不是元组**：必须写 `(42,)`。单元素元组少了逗号就是整数。
2. **`tuple[int]` 不等于 `tuple[int, ...]`**：前者长度必须是 1，很多初学者以为它表示“int 的元组”。要变长必须加 `...`。
3. **裸 `tuple` 不做任何检查**：它等价于 `tuple[Any, ...]`，会绕过类型检查器。
4. **`type[C]` 和 `C` 完全不同**：前者指“类对象”，后者指“实例”。工厂函数参数要用 `type[C]`。
5. **类型注解运行时不强制**：Python 解释器不会因为注解不匹配而抛错，只有类型检查器（mypy/pyright）和 IDE 会提示，别指望它代替运行时校验。
6. **`*Ts` 每次只允许出现一次**：`tuple[*Ts, *Ts]` 非法；同一参数列表里最多一个 `TypeVarTuple`。

---

## 动手练习

**任务：写一个“颜色工具”小模块**

1. 定义类型别名 `RGB = tuple[int, int, int]`，写函数 `to_hex(color: RGB) -> str`，把 `(255, 0, 128)` 转成 `'#ff0080'`（每段用 `format(v, '02x')`，注意越界要抛 `ValueError`）。
2. 写函数 `mix(colors: tuple[RGB, ...]) -> RGB`，输入任意长度的 RGB 元组，返回各通道平均值（取整）的 RGB。
3. 写函数 `make_palette(factory: type[tuple]) -> tuple`，用 `type[...]` 注解演示“传入类对象”的用法（可以先返回 `factory((1, 2, 3))`）。
4. 用 `mypy` 或 VS Code Pylance 检查：故意写 `c: tuple[int] = (1, 2, 3)`，确认工具报错。

**验收标准：** `to_hex((255, 0, 128)) == '#ff0080'`；`mix(((0,0,0), (10,10,10))) == (5, 5, 5)`；类型检查器能捕捉到 `tuple[int]` 长度不匹配的错误。

```python
# example.py —— 可直接运行：元组类型注解核心演示
from typing import TypeVarTuple, Unpack

# 1) 三种元组注解形态
rgb: tuple[int, int, int] = (255, 0, 128)   # 定长：位置类型固定
scores: tuple[int, ...] = (90, 85, 77)      # 变长：任意长度，同型
always_empty: tuple[()] = ()                # 只允许空元组

# 2) 裸 tuple 等价于 tuple[Any, ...]
z: tuple = ("foo", "bar")
z = (1, 2, 3)   # OK
z = ()          # OK

# 3) type[C]：变量装的是“类本身”
class User:
    def __init__(self, name: str = "anon") -> None:
        self.name = name

class ProUser(User):
    pass

def make_new_user(user_class: type[User]) -> User:
    return user_class()

assert make_new_user(User).name == "anon"
assert make_new_user(ProUser).name == "anon"

# 4) 变长类型参数（PEP 646 风格，Python 3.11+）
Ts = TypeVarTuple("Ts")

def move_first_to_last(tup: tuple[int, Unpack[Ts]]) -> tuple[Unpack[Ts], int]:
    first, *rest = tup
    return (*rest, first)

assert move_first_to_last((1, "spam", 3.0)) == ("spam", 3.0, 1)

print("all assertions passed")
```

## py.type.tuple_unpack

# 元组解包（Tuple Unpacking）：一句话直觉

**为什么学它？** 因为元组解包让你用「左边一排变量，右边一个容器」的方式，一次性把数据拆开赋值，代码短、可读性高，是 Python 里最常用的语法糖之一。

---

## 1. 什么是元组解包（Tuple Unpacking）

元组（tuple）是有序、不可变的容器；解包（unpacking）就是把容器里的元素「按位置」分配给左边的一组变量。

```python
# 最基础的形式：左边变量数 = 右边元素数
point = (3, 5)
x, y = point          # 把 point 的两个元素分别赋给 x、y
print(x, y)           # 3 5
```

**关键结论 1**：解包不要求右边是 tuple，任何可迭代对象（iterable）都可以。

```python
# 列表、字符串、range 都能解包
a, b = [10, 20]
c, d = "hi"           # 字符串也是可迭代对象
print(a, b, c, d)     # 10 20 h i
```

---

## 2. 用星号 `*` 收集剩余元素（Starred Assignment）

当元素个数不固定时，可以用一个带 `*` 的变量「兜住」剩下的元素，得到的是一个列表（list）。

```python
# *rest 收集中间所有剩余元素
first, *middle, last = [1, 2, 3, 4, 5]
print(first)    # 1
print(middle)   # [2, 3, 4]
print(last)     # 5
```

**关键结论 2**：一个解包表达式中最多只能出现一个 `*`，它负责收集，不会报「数量不匹配」。

```python
# 只留第一个，其余全收
head, *tail = ("a", "b", "c", "d")
print(head, tail)   # a ['b', 'c', 'd']
```

---

## 3. 嵌套解包（Nested Unpacking）

右边元素本身也可以是容器，只要左边的结构「形状匹配」就能递归拆开。

```python
# 嵌套结构：(姓名, (年, 月, 日))
record = ("Alice", (1995, 6, 18))
name, (year, month, day) = record
print(name, year, month, day)   # Alice 1995 6 18
```

**关键结论 3**：嵌套解包要求左右两侧结构一一对应，多一层少一层都会 `ValueError`。

```python
# 配合 * 收集嵌套里的剩余项
(a, b), *rest = ((1, 2), 3, 4)
print(a, b, rest)   # 1 2 [3, 4]
```

---

## 4. 在函数参数与返回中使用

解包在函数定义和调用里非常常见：`*args` 收集位置参数，`**kwargs` 收集关键字参数；函数返回元组时可以直接解包接收。

```python
def min_max(nums):
    # 返回一个元组
    return min(nums), max(nums)

# 调用方直接解包接收
lo, hi = min_max([3, 1, 4, 1, 5, 9])
print(lo, hi)   # 1 9
```

**关键结论 4**：`*` 在「赋值左边」表示收集，在「调用实参」表示展开，两者方向相反但同名。

```python
def add3(a, b, c):
    return a + b + c

args = (1, 2, 3)
print(add3(*args))   # 6，把元组展开成三个实参
```

---

## 5. 交换变量与循环解包：工程里最常见的两种用法

```python
# 用法一：一行交换两个变量（本质是元组解包）
x, y = 1, 2
x, y = y, x
print(x, y)   # 2 1

# 用法二：遍历 dict.items() 时直接解包键值对
prices = {"apple": 3, "banana": 5}
for name, price in prices.items():
    print(name, price)
```

**关键结论 5**：`for a, b in iterable` 是工程代码里解包出现频率最高的场景，能把「取元组再索引」变成一行。

```python
# 对比：不用解包 vs 用解包
pairs = [(1, "one"), (2, "two")]

for pair in pairs:
    print(pair[0], pair[1])   # 老写法

for num, word in pairs:
    print(num, word)          # 解包写法，更清晰
```

---

## 动手练习（Local Exercise）

**任务**：写一个函数 `split_scores(scores)`，接收一个分数列表（如 `[88, 92, 79, 95, 60]`），返回一个元组 `(highest, lowest, middle_list)`：
- `highest` 是最高分
- `lowest` 是最低分
- `middle_list` 是去掉最高分和最低分后剩下的分数列表

要求：
1. 先把列表排序；
2. **必须使用带 `*` 的解包** 把去掉首尾后的中间部分收集成一个列表；
3. 调用时用元组解包接收三个返回值并打印。

提示骨架：

```python
def split_scores(scores):
    ordered = sorted(scores)
    lowest, *middle, highest = ordered   # 你的解包在这里
    return highest, lowest, middle

hi, lo, mid = split_scores([88, 92, 79, 95, 60])
print(hi, lo, mid)
```

完成后思考：如果传入空列表或只有一个元素，会怎样？如何用条件判断让函数更健壮？

```python
# 可运行示例：元组解包的 5 种典型用法

# 1) 基础解包
point = (3, 5)
x, y = point
print("基础:", x, y)                      # 3 5

# 2) 星号收集剩余元素
first, *middle, last = [1, 2, 3, 4, 5]
print("星号:", first, middle, last)       # 1 [2, 3, 4] 5

# 3) 嵌套解包
record = ("Alice", (1995, 6, 18))
name, (year, month, day) = record
print("嵌套:", name, year, month, day)    # Alice 1995 6 18

# 4) 函数返回元组 + 调用方解包
def min_max(nums):
    return min(nums), max(nums)

lo, hi = min_max([3, 1, 4, 1, 5, 9])
print("函数:", lo, hi)                    # 1 9

# 5) 循环里解包键值对
prices = {"apple": 3, "banana": 5}
for fruit, price in prices.items():
    print("循环:", fruit, price)
```


---

## 本课题目

### single_choice · None



- [A] <class 'list'>
- [B] <class 'tuple'>
- [C] <class 'set'>
- [D] <class 'str'>

**参考答案**：1

**解析**：圆括号括起来、用逗号分隔的多个值是元组，type() 返回 <class 'tuple'>。

### single_choice · None



- [A] <class 'tuple'>
- [B] <class 'int'>
- [C] <class 'list'>
- [D] 报错 TypeError

**参考答案**：1

**解析**：括号里只有一个元素时，括号只起分组作用，t 实际是整数。单元素元组必须写成 (1,)。

### single_choice · None



- [A] True
- [B] False
- [C] 2
- [D] 报错 TypeError

**参考答案**：0

**解析**：in 运算符用于成员判断，元素 2 在元组中存在，结果 True。

### single_choice · None



- [A] 1
- [B] 2
- [C] 3
- [D] 4

**参考答案**：1

**解析**：count() 统计元素出现次数，2 出现了两次。

### single_choice · None



- [A] 1
- [B] 2
- [C] 3
- [D] 报错 ValueError

**参考答案**：0

**解析**：index() 返回元素第一次出现的下标，'b' 首次出现在下标 1。

### single_choice · None



- [A] 第 1 行
- [B] 第 2 行
- [C] 第 3 行
- [D] 不会产生异常

**参考答案**：1

**解析**：元组没有 append() 方法，第 2 行会抛出 AttributeError。

### single_choice · None



- [A] 1 2
- [B] (1, 2) (1, 2)
- [C] 报错 ValueError
- [D] 2 1

**参考答案**：0

**解析**：元组支持解包赋值，按位置把 1 和 2 分别赋给 a、b。

### single_choice · None



- [A] 1 2
- [B] 1 3
- [C] 2 3
- [D] 报错 ValueError

**参考答案**：3

**解析**：解包时左右数量必须一致，左边 2 个变量对应右边 3 个元素会抛 ValueError。

### single_choice · None



- [A] 报错 TypeError
- [B] (1, [2, 3, 4])
- [C] (1, [2, 3])
- [D] (1, 2, 3, 4)

**参考答案**：1

**解析**：元组本身不可变，但其中元素可以是可变对象；这里修改的是列表本身，所以能成功。

### single_choice · None



- [A] (1, 2, [5, 6])
- [B] (1, 2, [3, 4])
- [C] 报错 TypeError
- [D] 报错 IndexError

**参考答案**：2

**解析**：给元组的元素重新赋值等同于修改元组结构，会抛出 TypeError，即使该位置原本是列表。

### single_choice · None



- [A] ()
- [B] []
- [C] {}
- [D] (None)

**参考答案**：0

**解析**：() 是空元组；[] 是空列表；{} 是空字典；(None) 是值为 None 的表达式。

### single_choice · None



- [A] 3 3 1
- [B] 3 1 3
- [C] 1 3 3
- [D] 报错 TypeError

**参考答案**：0

**解析**：len() 返回元素个数 3，max() 返回最大值 3，min() 返回最小值 1。

### single_choice · None



- [A] <class 'tuple'> 1
- [B] <class 'int'> 1
- [C] <class 'tuple'> 0
- [D] 报错 SyntaxError

**参考答案**：0

**解析**：(5,) 中的逗号使其成为只有一个元素的元组，长度为 1。

### single_choice · None



- [A] (100, 2, 3)
- [B] (1, 2, 3)
- [C] 报错 TypeError
- [D] 报错 IndexError

**参考答案**：2

**解析**：元组是不可变序列，不支持项目赋值，会抛出 TypeError。

### single_choice · None



- [A] 1
- [B] 2
- [C] 3
- [D] 报错 IndexError

**参考答案**：1

**解析**：元组支持下标访问，下标从 0 开始，t[1] 取第二个元素 2。

### single_choice · None



- [A] 1
- [B] 3
- [C] 4
- [D] 报错 IndexError

**参考答案**：2

**解析**：负数下标从末尾计数，-1 表示最后一个元素 4。

### single_choice · None



- [A] (1, 2, 3)
- [B] (1, 2, 3, 4)
- [C] (0, 1, 2, 3)
- [D] (0, 1, 2, 3, 4)

**参考答案**：0

**解析**：切片 [1:4] 包含起始下标 1、不包含结束下标 4，得到 (1, 2, 3)，且结果为元组。

### single_choice · None



- [A] (1, 2, 3)
- [B] (3, 2, 1)
- [C] (1, 3)
- [D] 报错 TypeError

**参考答案**：1

**解析**：切片步长为 -1 时反转序列，结果为 (3, 2, 1)，元组切片仍返回元组。

### single_choice · None



- [A] (1, 2, 3, 4)
- [B] (4, 6)
- [C] (1, 2, (3, 4))
- [D] 报错 TypeError

**参考答案**：0

**解析**：元组的 + 运算符表示拼接，返回新元组 (1, 2, 3, 4)。

### single_choice · None



- [A] (1, 2, 1, 2, 1, 2)
- [B] (3, 6)
- [C] (3, 3)
- [D] 报错 TypeError

**参考答案**：0

**解析**：元组与整数相乘表示重复拼接，得到 (1, 2, 1, 2, 1, 2)。

### single_choice · None



- [A] x=1, y=2, z=3
- [B] x=(1,), y=(2,), z=(3,)
- [C] x=1, y=2, z=(3,)
- [D] 抛出 ValueError

**参考答案**：0

**解析**：元组解包会把可迭代对象 t 中的三个元素依次分配给左侧三个变量，因此 x、y、z 分别是 1、2、3。

### single_choice · None



- [A] a=1, b=2，剩余元素被忽略
- [B] a=1, b=2, 3 被赋给 b 成为 (2,3)
- [C] 抛出 ValueError: too many values to unpack
- [D] 抛出 TypeError

**参考答案**：2

**解析**：左侧变量数量少于右侧元素数量时（无星号收集），Python 会抛出 ValueError: too many values to unpack。

### single_choice · None



- [A] a, (b, c) = (1, (2, 3))
- [B] (a, b), c = (1, 2), 3
- [C] a, b = (1, 2), (3, 4)
- [D] a, (b, c) = (1, 2, 3)

**参考答案**：3

**解析**：嵌套解包要求结构匹配。a, (b, c) = (1, 2, 3) 中右侧第二项是整数 3，不可再解包，会抛 TypeError。其余选项结构均匹配。

### multi_choice · None



- [A] 一个赋值目标中最多只能有一个星号变量
- [B] 星号变量收集到的结果是一个列表
- [C] 星号变量收集到的结果是一个元组
- [D] 星号变量可以为空列表（当没有剩余元素时）
- [E] 星号变量必须放在最左边

**参考答案**：[0, 1, 3]

**解析**：赋值解包中星号变量最多一个，收集结果为 list，且当没有剩余元素时为空列表 []；星号变量可出现在任意位置，不必在最左边。

### multi_choice · None



- [A] 元组
- [B] 列表
- [C] 字符串
- [D] 生成器
- [E] 整数

**参考答案**：[0, 1, 2, 3]

**解析**：元组、列表、字符串、生成器都是可迭代对象，可被解包；整数不可迭代，放在右侧会抛 TypeError。

### multi_choice · None



- [A] a, b, *c = t
- [B] *a, b, c = t
- [C] a, *b, c = t
- [D] a, *b, *c = t
- [E] *a = t

**参考答案**：[0, 1, 2]

**解析**：星号变量最多一个且位置任意，故 a,b,*c / *a,b,c / a,*b,c 都合法；两个星号非法，单独 *a 也非法（星号变量必须与其他目标共存）。

### multi_choice · None



- [A] 嵌套结构的内层必须也是可迭代对象
- [B] 嵌套解包的括号可以省略，如 a, b, c = 1, 2, 3
- [C] 嵌套解包要求两侧结构完全一致才能成功
- [D] 嵌套解包中可以使用多个星号

**参考答案**：[0, 1, 2]

**解析**：嵌套解包要求结构匹配，内层须是可迭代对象，括号可省略；但整个模式中仍最多一个星号，不能多个。

### fill_blank · None



**参考答案**：["nums", "nums"]

**解析**：函数定义中 *nums 把多余位置实参收集为元组，函数体内可直接对其求和，故两处都填 nums（变量名可自定义但需一致）。

### fill_blank · None



**参考答案**：["[2, 3] list", "[2, 3], list", "[2, 3] list"]

**解析**：星号变量收集剩余元素为列表，故输出 [2, 3] list。

### code_reading · None



**参考答案**：10 [20, 30, 40] 50

**解析**：first 取第一个元素 10，last 取最后一个元素 50，中间的 *middle 收集剩余元素成为列表 [20, 30, 40]。

### code_reading · None



**参考答案**：左侧有三个变量但右侧只有两个元素，值不足以解包，抛出 ValueError: not enough values to unpack (expected 3, got 2)。

**解析**：无星号收集时，变量数必须与元素数相等。这里元素少于变量数，抛 ValueError not enough values to unpack。

### scenario · None



**参考答案**：["根号"]

**解析**：由于元素数量可变，不能写成固定三变量解包，否则缺元素时会抛 ValueError。可用 a, b, *rest = record，rest 收集剩余元素为列表；然后判断 rest 是否为空来处理 extra 缺失。星号收集能容忍数量变化。

### single_choice · None



- [A] a=(1,), rest=[2,3,4]
- [B] a=1, rest=[2,3,4]
- [C] a=1, rest=(2,3,4)
- [D] 语法错误，元组不能用星号解包

**参考答案**：1

**解析**：带星号的变量会收集剩余所有元素，并且总是生成列表（list），因此 rest 为 [2, 3, 4]。

### scenario · None



**参考答案**：["根号"]

**解析**：get_point() 返回的元素数量多于左侧变量数时会抛 ValueError: too many values to unpack。稳健改法可写成 a, b, *rest = get_point()，用星号收集多余元素，或先接收整个返回值再按需取前两个。

### single_choice · None



- [A] *a, b = (1, 2, 3)
- [B] a, *b, *c = (1, 2, 3)
- [C] *a = (1, 2, 3)
- [D] a, b, *c, d = (1, 2, 3, 4)

**参考答案**：0

**解析**：一个解包目标中最多只能有一个星号变量，且星号变量可以出现在任意位置；*a, b = (1,2,3) 合法。多个星号、单独星号、星号后仍有普通变量均非法。

### single_choice · None



- [A] 解包赋值的右侧只能是元组，列表不行
- [B] 解包赋值的右侧可以是任意可迭代对象
- [C] 解包赋值只能用于元组，字符串不能被解包
- [D] 解包时左侧变量数必须严格等于右侧元素数

**参考答案**：1

**解析**：解包的本质是迭代右侧对象，任何可迭代对象（列表、字符串、生成器、字典等）都可以被解包；变量数可不相等（借助星号收集）。

### single_choice · None



- [A] 1 2
- [B] 2 1
- [C] 2 2
- [D] 抛出错误

**参考答案**：1

**解析**：右侧 b, a 先被求值为一个元组 (2, 1)，再解包赋给 a, b，实现安全交换，输出 2 1。

### single_choice · None



- [A] 1 2
- [B] x y
- [C] (1, 2)
- [D] 抛出 ValueError

**参考答案**：1

**解析**：对字典解包时迭代的是它的键，因此 a、b 得到字符串 'x'、'y'，输出 x y。要解包值需用 d.values()。

### single_choice · None



- [A] (1, [2, 3, 4], 4)
- [B] (1, [2, 3, 5], 4)
- [C] (1, [2, 3], 4)
- [D] 抛出 TypeError

**参考答案**：1

**解析**：解包只是重新绑定引用，b 与 t 中第二个元素指向同一列表，修改列表内容会反映到元组中。元组本身不可变但内部可变对象可被修改。

### single_choice · None



- [A] 把 a 之后的位置参数收集为一个元组
- [B] 把 a 之后的位置参数收集为一个列表
- [C] 表示参数 a 是关键字参数
- [D] 表示必须传入恰好两个参数

**参考答案**：0

**解析**：函数定义中的 *args 会把多余的位置实参收集成一个元组（tuple），这与赋值语句里星号变量收集成 list 不同。

### single_choice · None



- [A] f(t)
- [B] f(t[0], t[1], t[2])
- [C] f([1, 2, 3])
- [D] f(1, 2, 3) 且会创建列表

**参考答案**：1

**解析**：调用处的 *t 会把可迭代对象 t 展开为逐个位置实参，等价于 f(t[0], t[1], t[2])，即 f(1, 2, 3)。
