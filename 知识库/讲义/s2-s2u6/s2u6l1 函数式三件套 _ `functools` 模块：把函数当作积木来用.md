# s2u6l1 函数式三件套 / `functools` 模块：把函数当作积木来用

> 来源 `content/lessons/s2u6l1.json`

## py.fp.map_filter_reduce

# py.fp.map_filter_reduce：函数式三件套

> **一句话直觉**：当你要对一堆数据“逐个变换 → 筛掉不要的 → 汇总成一个结果”时，`map` / `filter` / `reduce` 就是把这三种最常见的批量操作各压缩成一行的工具。

---

## 1. 为什么要学它：从“写循环”到“说意图”

假设你手上有一个分数列表，想求“所有及格分数的平方和”。零基础写法通常是这样：

```python
scores = [88, 45, 92, 60, 30]
total = 0
for s in scores:
    if s >= 60:
        total += s * s
print(total)  # 88*88 + 92*92 + 60*60 = 7744 + 8464 + 3600 = 19808
```

循环当然没错，但它把三件事混在一起：**筛（if）→ 变换（s*s）→ 汇总（+=）**。
`map` / `filter` / `reduce` 的价值，是让你把每一步单独说出来：

```python
from functools import reduce

scores = [88, 45, 92, 60, 30]
total = reduce(
    lambda acc, x: acc + x,                       # 汇总：累加
    map(lambda s: s * s,                          # 变换：平方
        filter(lambda s: s >= 60, scores))        # 筛选：及格
)
print(total)  # 19808
```

在读代码时，你一眼就知道“及格 → 平方 → 求和”，而不是先去读循环体里的细节。这是**函数式编程（functional programming）** 的典型思路：用函数组合来描述数据流。

---

## 2. `map`：对每个元素做同一种变换

`map(function, iterable)` 把 `function` 依次作用在每个元素上，返回一个 map 对象（惰性迭代器，lazy iterator）。

```python
# map 基本用法：把每个字符串变成整数
str_nums = ["1", "2", "3"]
int_nums = list(map(int, str_nums))
print(int_nums)  # [1, 2, 3]

# map 也可以配合 lambda 做任意变换
squared = list(map(lambda x: x * x, [1, 2, 3, 4]))
print(squared)  # [1, 4, 9, 16]
```

关键点：
- 返回的不是列表，而是**迭代器**。想复用或看内容，要 `list()` 或 `for` 一遍。
- 多个 iterable 可以并行传入：`map(lambda a, b: a+b, [1,2], [10,20])` → `[11, 22]`，长度按最短的算。

---

## 3. `filter`：只保留让谓词为真的元素

`filter(predicate, iterable)` 用 `predicate`（谓词，返回布尔值的函数）判断每个元素，只保留为真的。

```python
nums = [1, -2, 3, -4, 5]
positives = list(filter(lambda x: x > 0, nums))
print(positives)  # [1, 3, 5]

# 常见用法：过滤掉空值
mixed = ["apple", "", None, "banana", 0]
nonempty = list(filter(None, mixed))  # 传 None 表示“保留真值元素”
print(nonempty)  # ['apple', 'banana']
```

关键点：
- `predicate` 必须返回可被 `bool()` 判定的值；传 `None` 是“保留所有真值”的语法糖。
- 同样返回迭代器，不会立刻计算。

---

## 4. `reduce`：把一串值折叠成一个值

`reduce(function, iterable[, initial])` 会把前两个元素喂给 `function`，得到结果后再与下一个元素组合，像“滚雪球”一样压成一个最终值。它属于 `functools` 模块。

```python
from functools import reduce

nums = [1, 2, 3, 4]
product = reduce(lambda a, b: a * b, nums)
print(product)  # 1*2*3*4 = 24

# 带初始值：初始值会作为第一次调用的“左边”
total = reduce(lambda a, b: a + b, nums, 100)
print(total)  # 100+1+2+3+4 = 110
```

关键点：
- 没给 `initial` 且可迭代对象为空时会 `TypeError`；给了 `initial` 则直接返回它。
- 不是“原地改”，而是每次产生新中间值。

---

## 5. 组合使用：把三步写成一条数据流水线

真实工程里常见“读 → 清洗 → 统计”的链条，`map` / `filter` / `reduce` 可以自然串起来：

```python
from functools import reduce

orders = [
    {"item": "book",  "price": 30, "qty": 2},
    {"item": "pen",   "price":  5, "qty": 0},
    {"item": "bag",   "price": 80, "qty": 1},
]

# 1) filter：只要数量 > 0 的订单
# 2) map：算出每笔小计
# 3) reduce：求和
revenue = reduce(
    lambda acc, subtotal: acc + subtotal,
    map(lambda o: o["price"] * o["qty"],
        filter(lambda o: o["qty"] > 0, orders))
)
print(revenue)  # 30*2 + 80*1 = 140
```

这是理解 `map` / `filter` / `reduce` 最实用的场景：它们不是三件孤立的工具，而是**可拼接的算子**。

---

## 6. 何时不用它们：可读性优先

Python 社区对 `map`/`filter` 的态度是：能用**列表推导式（list comprehension）** 或 **生成器表达式（generator expression）** 表达得更清楚时，优先用后者。

```python
nums = [1, 2, 3, 4, 5]

# 等价写法，通常更 Pythonic
squares_of_evens = [x * x for x in nums if x % 2 == 0]
print(squares_of_evens)  # [4, 16]

# map + filter 版本
from functools import reduce
squares_of_evens2 = list(map(lambda x: x * x, filter(lambda x: x % 2 == 0, nums)))
print(squares_of_evens2)  # [4, 16]
```

`reduce` 在 Python 3 已被移到 `functools`，官方建议：求和/求积等常见聚合，优先用 `sum`、`math.prod`、`min`、`max`；只有自定义的二元合并逻辑才用 `reduce`。

---

## 7. 与函数式编程的关系

- `map` / `filter` / `reduce` 是函数式编程（functional programming）中高阶函数（higher-order function）的入门三件套：它们接收函数作为参数。
- 它们天然支持**惰性求值（lazy evaluation）**：`map` 和 `filter` 返回迭代器，只有真正迭代时才计算，适合处理大文件或流式数据。
- 现代 Python 中，`itertools` 和生成器表达式是它们的重要补充；`functools.reduce` 是它们的收尾聚合器。

---

## 动手练习

**任务**：给定一个商品价格列表（用 `dict` 表示），完成一条数据处理流水线。

```python
products = [
    {"name": "笔记本", "price": 4999, "in_stock": True},
    {"name": "钢笔",   "price":  39,  "in_stock": False},
    {"name": "背包",   "price":  299, "in_stock": True},
    {"name": "橡皮",   "price":    3, "in_stock": True},
]
```

**要求**：
1. 用 `filter` 筛出 `in_stock` 为 `True` 的商品。
2. 用 `map` 给每个商品打 9 折（`price * 0.9`）。
3. 用 `reduce` 求打折后所有商品价格之和。
4. 把结果打印出来，并用列表推导式写一个等价版本作对比。

**期望输出**：`4860.9`（4999*0.9 + 299*0.9 + 3*0.9）。

**进阶**：把 `filter` + `map` 替换成生成器表达式，观察代码是不是更短更清晰。

```python
from functools import reduce

# ---------- map：逐元素变换 ----------
str_nums = ["1", "2", "3"]
int_nums = list(map(int, str_nums))
print("map 结果:", int_nums)  # [1, 2, 3]

# ---------- filter：按条件筛选 ----------
nums = [1, -2, 3, -4, 5]
positives = list(filter(lambda x: x > 0, nums))
print("filter 结果:", positives)  # [1, 3, 5]

# ---------- reduce：折叠成一个值 ----------
product = reduce(lambda a, b: a * b, [1, 2, 3, 4])
print("reduce 结果:", product)  # 24

# ---------- 三件套组合：及格分数的平方和 ----------
scores = [88, 45, 92, 60, 30]
total = reduce(
    lambda acc, x: acc + x,
    map(lambda s: s * s,
        filter(lambda s: s >= 60, scores))
)
print("组合结果:", total)  # 19808

# ---------- 工程小案例：统计在售商品打折后总收入 ----------
products = [
    {"name": "笔记本", "price": 4999, "in_stock": True},
    {"name": "钢笔",   "price":   39, "in_stock": False},
    {"name": "背包",   "price":  299, "in_stock": True},
    {"name": "橡皮",   "price":    3, "in_stock": True},
]

revenue = reduce(
    lambda acc, p: acc + p,
    map(lambda p: p["price"] * 0.9,
        filter(lambda p: p["in_stock"], products))
)
print("流水线结果:", revenue)  # 4860.9
```

## py.fp.functools

# `functools` 模块：把函数当作积木来用

> **一句话直觉（Why）**：Python 里函数是一等公民（first-class citizen），`functools` 就是官方提供的“函数工具箱”，让你能缓存、冻结参数、组合、比较、归约——把函数当成积木一样拼装，而不必重复造轮子。

本讲共 5 节：1) 什么是高阶函数（higher-order function）与 `functools` 的定位；2) `partial` 冻结参数；3) `lru_cache`/`cache` 记忆化；4) `reduce`/`wraps`/`singledispatch`；5) 组合拳与工程场景。

---

## 0. 前置：`functools` 是什么

`functools`（function tools，函数工具）是 Python 标准库模块，专门处理**高阶函数**——即接受函数作为参数、或返回函数的函数。它不引入新语法，只是一组经过优化的工具函数。

```python
import functools
print(functools.__name__)  # 模块本身，随时可用
```

本节结论：**只要你在写“包装/复用/优化函数”的代码，先想想 `functools` 里有没有现成的。**

---

## 1. `functools.partial`：冻结部分参数

**直觉**：调用函数时反复传同一个参数很烦。`partial`（偏函数）能预先“锁”住一部分参数，生成一个新函数。

```python
from functools import partial

def power(base, exponent):
    return base ** exponent

square = partial(power, exponent=2)   # 冻结 exponent=2
cube   = partial(power, exponent=3)

print(square(5))   # 25
print(cube(2))     # 8
```

结论：`partial(f, *a, **kw)` 返回一个新可调用对象，调用它时等价于 `f(*a, *your_args, **kw)`。

---

## 2. `functools.lru_cache` / `cache`：记忆化（memoization）

**直觉**：纯函数（pure function，相同输入必得相同输出）重复计算是浪费。给函数套一层缓存装饰器即可。

```python
from functools import lru_cache
import time

@lru_cache(maxsize=None)   # maxsize=None 等价于 @cache
 def fib(n):
    return n if n < 2 else fib(n - 1) + fib(n - 2)

t0 = time.perf_counter()
print(fib(35))              # 9227465
print('耗时:', time.perf_counter() - t0)   # 几乎瞬间，指数级变线性
```

结论：`lru_cache`（Least Recently Used cache，最近最少使用缓存）以参数为键缓存返回值。Python 3.9+ 可直接用更简单的 `@cache`。

注意：参数必须**可哈希（hashable）**，且函数需无副作用，否则缓存会返回过期结果。

---

## 3. `functools.reduce`：把序列折叠成一个值

**直觉**：`sum` 只能求和；`reduce`（归约）能把**任意二元函数**从左到右折叠到序列上。

```python
from functools import reduce

nums = [1, 2, 3, 4, 5]

print(reduce(lambda a, b: a * b, nums))          # 120
print(reduce(lambda a, b: a + b, nums, 100))     # 115，带初始值
```

结论：签名 `reduce(func, iterable[, initial])`。逻辑等价于 `f(f(f(x1, x2), x3), x4) ...`。

---

## 4. `functools.wraps`：写装饰器必用

**直觉**：装饰器会“偷走”被包装函数的身份（`__name__`、文档字符串等），`wraps` 把这些元数据还回去。

```python
from functools import wraps

def log_calls(func):
    @wraps(func)                 # 保留原函数元数据
    def wrapper(*args, **kwargs):
        print(f'调用 {func.__name__}')
        return func(*args, **kwargs)
    return wrapper

@log_calls
def greet(name):
    '打招呼'
    return f'Hello, {name}'

greet('Ada')                     # 调用 greet
print(greet.__name__)            # greet（若不用 wraps，这里会是 wrapper）
print(greet.__doc__)             # 打招呼
```

结论：**任何自己写的装饰器，内部包装函数前都应加 `@wraps(func)`。**

---

## 5. `functools.singledispatch` 与 `total_ordering`

**`singledispatch`（单分派）**：按第一个参数的类型选择实现，替代冗长的 `isinstance` 分支。

```python
from functools import singledispatch

@singledispatch
def describe(x):
    return f'未知类型: {type(x).__name__}'

@describe.register
def _(x: int):
    return f'整数 {x}'

@describe.register
def _(x: list):
    return f'列表，长度 {len(x)}'

print(describe(42))       # 整数 42
print(describe([1, 2]))   # 列表，长度 2
print(describe('hi'))     # 未知类型: str
```

**`total_ordering`（全序）**：只需实现 `__eq__` 和一个比较方法，就能补齐其余比较运算符。

```python
from functools import total_ordering

@total_ordering
class Version:
    def __init__(self, n): self.n = n
    def __eq__(self, other): return self.n == other.n
    def __lt__(self, other): return self.n < other.n

print(Version(1) < Version(2))    # True
print(Version(2) >= Version(2))   # True（自动推导）
```

结论：`singledispatch` 让“按类型分派”优雅；`total_ordering` 让自定义类少写 4 个比较方法。

---

## 6. 工程级组合：把 `lru_cache` 与 `partial` 一起用

```python
from functools import lru_cache, partial

@lru_cache(maxsize=128)
def fetch(user_id, endpoint):
    # 假装的昂贵网络请求
    return f'user={user_id} @ {endpoint}'

fetch_profile = partial(fetch, endpoint='/profile')
print(fetch_profile(7))   # user=7 @ /profile
print(fetch_profile(7))   # 命中缓存
```

结论：真实项目里 `functools` 各工具常**叠加使用**：`partial` 制造特化函数，`lru_cache` 做记忆化，`wraps` 保元数据，`reduce` 做聚合。

---

## 动手练习（Local Practice）

**任务**：实现一个“带缓存的斐波那契 + 调用统计”小工具。

1. 用 `functools.lru_cache(maxsize=None)` 实现 `fib(n)`。
2. 写一个装饰器 `count_calls`，用 `functools.wraps` 保留原函数信息，统计每个函数被实际执行的次数（注意：要统计**未命中缓存**的真实调用次数，可以让装饰器包在缓存外层）。
3. 计算 `fib(30)`，打印结果、缓存信息（`fib.cache_info()`）以及真实执行次数。
4. 用 `functools.partial` 创建一个 `fib10 = partial(fib, 10)`，调用它并说明结果。

**验收标准**：`fib(30)` 的真实调用次数应接近 31 次（而非 2^30 级），并能看到 `hits/misses` 统计输出。

```python
from functools import lru_cache, partial, wraps, reduce

# 1) 记忆化
@lru_cache(maxsize=None)
def fib(n):
    return n if n < 2 else fib(n - 1) + fib(n - 2)

# 2) 调用统计装饰器
def count_calls(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        wrapper.calls += 1
        return func(*args, **kwargs)
    wrapper.calls = 0
    return wrapper

@count_calls
def slow_add(a, b):
    return a + b

# 3) 使用
print('fib(30) =', fib(30))
print('cache info:', fib.cache_info())
for _ in range(5):
    slow_add(1, 2)
print('slow_add calls =', slow_add.calls)

# 4) partial
fib10 = partial(fib, 10)
print('fib10() =', fib10())

# 5) reduce
print('product =', reduce(lambda a, b: a * b, [1, 2, 3, 4, 5]))
```


---

## 本课题目

### single_choice · None



- [A] [1, 2, 3, 4]
- [B] [2, 4, 6, 8]
- [C] [1, 4, 9, 16]
- [D] [2, 4, 6, 8, 10]

**参考答案**：1

**解析**：map 会把函数依次作用到可迭代对象的每个元素上，lambda 返回 x*2，因此结果是 [2,4,6,8]。

### single_choice · None



- [A] [1, 3, 5]
- [B] [2, 4]
- [C] [True, False, True, False, True]
- [D] [1, 2, 3, 4, 5]

**参考答案**：1

**解析**：filter 会保留使函数返回真值的元素，偶数满足条件，因此结果是 [2,4]。

### single_choice · None



- [A] [4, 6, 8, 10, 12]
- [B] [8, 10, 12]
- [C] [4, 5, 6]
- [D] [2, 4, 6, 8, 10, 12]

**参考答案**：1

**解析**：先 map 得到 [2,4,6,8,10,12]，再 filter 保留大于 3 的，即 [8,10,12]。

### single_choice · None



- [A] 10
- [B] 6
- [C] 4
- [D] 2

**参考答案**：1

**解析**：filter 先保留偶数 [2,4]，reduce 求和得到 6。

### single_choice · None



- [A] map 返回列表，列表推导式返回生成器
- [B] map 返回迭代器，列表推导式返回列表
- [C] 两者都返回列表
- [D] 两者都返回迭代器

**参考答案**：1

**解析**：map 返回惰性迭代器；列表推导式立即构造并返回列表。

### single_choice · None



- [A] [5, 8]
- [B] [8, 5]
- [C] [1, 3]
- [D] [5, 3, 8]

**参考答案**：0

**解析**：filter 保留大于 3 的 [5,8]，sorted 默认升序得到 [5,8]。

### single_choice · None



- [A] abc
- [B] ['a', 'b', 'c']
- [C] TypeError
- [D] a

**参考答案**：0

**解析**：reduce 对字符串同样做累积：'a'+'b'+'c' 得到 'abc'。

### single_choice · None



- [A] [11, 22, 33]
- [B] [10, 20, 30]
- [C] [1, 2, 3]
- [D] TypeError

**参考答案**：0

**解析**：map 可以接收多个可迭代对象，按位置并行传入函数，结果为 [11,22,33]。

### single_choice · None



- [A] [2, 4]
- [B] [False, True, False, True]
- [C] [True, False, True, False]
- [D] [1, 0, 1, 0]

**参考答案**：1

**解析**：map 不筛选，只是把每个元素映射为布尔值：1→False、2→True、3→False、4→True。

### single_choice · None



- [A] 3
- [B] 7
- [C] 9
- [D] TypeError

**参考答案**：2

**解析**：reduce 用二元函数逐步比较，最终保留最大值 9。

### single_choice · None



- [A] [2, 4]
- [B] [1, 3]
- [C] [1, 2, 3, 4]
- [D] []

**参考答案**：1

**解析**：x % 2 对奇数返回 1（真值），对偶数返回 0（假值），因此保留奇数 [1,3]。

### single_choice · None



- [A] TypeError
- [B] []
- [C] [None]
- [D] 0

**参考答案**：1

**解析**：空可迭代对象经 map 仍为空迭代器，转换为列表后得到 []。

### single_choice · None



- [A] [1, 2, 3, 4]
- [B] 10
- [C] 24
- [D] 4

**参考答案**：1

**解析**：reduce 会用二元函数对元素从左到右累积归约：((1+2)+3)+4=10。

### single_choice · None



- [A] 3
- [B] 83
- [C] 93
- [D] -93

**参考答案**：1

**解析**：提供初始值 100 后，计算过程为 ((100-10)-5)-2 = 83。若不含初始值，则结果为 10-5-2=3。

### single_choice · None



- [A] list
- [B] tuple
- [C] map
- [D] generator

**参考答案**：2

**解析**：map 返回一个 map 迭代器对象，而不是列表或生成器；需要 list() 等才能得到列表。

### single_choice · None



- [A] [10, 20, 30]
  [10, 20, 30]
- [B] [10, 20, 30]
  []
- [C] []
  [10, 20, 30]
- [D] [10, 20, 30]
  [None, None, None]

**参考答案**：1

**解析**：map 是惰性迭代器，第一次 list(m) 已耗尽迭代器，第二次再取就为空。

### single_choice · None



- [A] [1, 2, 3, 4]
- [B] []
- [C] [1, 1, 1, 1]
- [D] [None, None, None, None]

**参考答案**：0

**解析**：当 filter 的第一个参数为 None 时，会保留所有真值元素；1~4 都是真值，所以原样保留。

### single_choice · None



- [A] [0, 1, 2, 3]
- [B] [1, 2, 3]
- [C] [0]
- [D] [True, True, True, True]

**参考答案**：1

**解析**：filter(None, ...) 会过滤掉假值元素，0 是假值，所以只剩下 [1,2,3]。

### single_choice · None



- [A] 10
- [B] 24
- [C] 4
- [D] 1

**参考答案**：1

**解析**：reduce 做连乘：1*2*3*4 = 24。

### single_choice · None



- [A] list(filter(lambda x: x * 4, nums))
- [B] list(map(lambda x: x * 4, nums))
- [C] list(map(lambda x: x + 4, nums))
- [D] list(filter(lambda x: x + 4, nums))

**参考答案**：1

**解析**：要得到每个元素乘 4 的新列表，应使用 map 做变换；filter 只做筛选。

### single_choice · None



- [A] 10
- [B] 24
- [C] 120
- [D] 报错

**参考答案**：1

**解析**：reduce 依次累积相乘：((1*2)*3)*4 = 24。若误认为是求和会得 10；若以为需要初始值会报错，但 reduce 在无初始值且序列非空时合法。

### single_choice · None



- [A] 0
- [B] 128
- [C] None
- [D] 256

**参考答案**：1

**解析**：lru_cache 默认 maxsize=128，表示最多缓存 128 个不同调用结果。maxsize=None 表示无上限；maxsize=0 等价于不缓存。

### fill_blank · None



**参考答案**：["wraps", "functools.wraps", "@wraps", "wraps()"]

**解析**：functools.wraps 会把原函数的元数据复制到包装函数上，是编写装饰器时的惯用做法。

### fill_blank · None



**参考答案**：["20"]

**解析**：以 10 为初始值累积相加：10+1+2+3+4 = 20。容易忽略 initializer 而答成 10。

### fill_blank · None



**参考答案**：["maxsize"]

**解析**：maxsize 决定缓存的最大条目数，默认为 128。typed 参数控制是否区分不同类型的等价参数，不是数量上限。

### code_reading · None



**参考答案**：2

**解析**：square(3) 第一次调用会执行函数并把 3 记入 calls；第二次 square(3) 命中缓存不再执行；square(4) 是新参数，执行一次。因此 calls 中有 [3, 4]，长度为 2。

### code_reading · None



**参考答案**：25

**解析**：partial 预先固定了关键字参数 exp=2，调用 square(5) 相当于 power(5, exp=2) = 25。partial 返回的是可调用对象，调用时才执行。

### code_reading · None



**参考答案**：9

**解析**：reduce 用二元函数依次累积取较大值，等价于求最大值，结果为 9。它不返回列表，而是返回单个累积值。

### scenario · None



**解析**：lru_cache 默认 maxsize=128，但若显式设为 None 表示无上限，缓存项会随不同参数不断累积而占满内存。应设置合理的 maxsize 上限，让 LRU 策略自动淘汰旧条目，从而在命中率与内存之间取得平衡。

### scenario · None



**解析**：包装函数 wrapper 覆盖了原函数的元数据。应在定义 wrapper 时加上 @functools.wraps(原函数)，把 __name__、__doc__、__module__、__wrapped__ 等复制到 wrapper 上，从而保留原函数的身份信息。

### scenario · None



**解析**：可用 functools.partial 预先固定 host 与 timeout 等参数，得到一个调用时只需传入剩余参数的偏函数对象。注意 partial 是调用该对象时才执行原函数；固定的关键字参数可被再次覆盖；偏函数可继续被 partial 包装。

### scenario · None



**解析**：缓存实现通常以参数为键，要求参数可哈希。列表不可哈希，因此抛 TypeError。修复方向：一是把参数转换为可哈希形式（如元组）后再传入；二是不对含不可哈希参数的函数使用缓存，或改用在函数内部自行做键规范化。

### single_choice · None



- [A] 它返回一个绑定了部分参数的新可调用对象
- [B] 它会立即调用原函数并返回结果
- [C] 它只能固定第一个参数
- [D] 它修改了原函数的默认参数

**参考答案**：0

**解析**：partial 返回一个偏函数对象，预先固定任意位置/关键字参数，调用该对象时才真正执行。它不改变原函数，也不立即执行。

### single_choice · None



- [A] 正常返回结果但不缓存
- [B] 抛出 TypeError
- [C] 抛出 ValueError
- [D] 自动把列表转成元组

**参考答案**：1

**解析**：lru_cache 内部用参数作为字典键，参数必须可哈希。传入列表这类不可哈希对象会抛 TypeError。它不会自动转换，也不会静默跳过缓存。

### single_choice · None



- [A] 给被装饰函数加锁
- [B] 把被包装函数的元数据（__name__、__doc__ 等）复制到包装函数上
- [C] 缓存函数的返回值
- [D] 限制函数的调用次数

**参考答案**：1

**解析**：wraps 是装饰器工厂，用于在编写装饰器时保留原函数的 __name__、__doc__、__module__、__wrapped__ 等，帮助调试与文档生成。它与缓存、锁、限次无关。

### single_choice · None



- [A] 随机淘汰任意缓存项
- [B] 淘汰最早加入的项（FIFO）
- [C] 淘汰最久未被使用的项（LRU）
- [D] 淘汰访问次数最少的项（LFU）

**参考答案**：2

**解析**：LRU = Least Recently Used，淘汰最久未被访问的条目。它不是 FIFO 也不是 LFU，随机淘汰更不对。理解策略名称含义即可。

### multi_choice · None



- [A] 纯函数且参数可哈希、调用重复度高
- [B] 递归计算斐波那契数列
- [C] 每次调用都读取实时变化的外部文件内容
- [D] 根据固定参数反复解析同一配置文件
- [E] 参数包含不可哈希的字典对象

**参考答案**：[0, 1, 3]

**解析**：lru_cache 适合纯函数、参数可哈希、重复调用多的场景（递归、重复解析固定内容）。实时变化的数据不应缓存（结果会过期），不可哈希参数无法作为键。

### multi_choice · None



- [A] 它把二元函数依次作用在序列元素上做累积
- [B] 提供了 initializer 时可指定初始值
- [C] 对空序列且无 initializer 会抛 TypeError
- [D] 它等同于内置的 map 函数
- [E] 它的返回值一定是一个列表

**参考答案**：[0, 1, 2]

**解析**：reduce 做累积归约，可用 initializer 指定初值；空序列且无初值时报 TypeError。它不同于 map（map 是逐元素映射且返回迭代器），返回值是单个累积值而非列表。

### multi_choice · None



- [A] 可以在原函数参数基础上额外传入关键字参数
- [B] 调用返回的偏函数对象时才执行原函数
- [C] partial 会把固定参数与原函数签名合并检查
- [D] partial 对象可以再次被 partial 包装
- [E] partial 会改变原函数本身的行为

**参考答案**：[0, 1, 3]

**解析**：partial 允许预先固定部分参数，调用时才执行；偏函数对象还能继续被 partial 包装。partial 不修改原函数。它本身不进行完整的签名绑定检查（参数错误通常在调用时才暴露）。

### multi_choice · None



- [A] lru_cache
- [B] partial
- [C] reduce
- [D] wraps
- [E] namedtuple

**参考答案**：[0, 1, 2, 3]

**解析**：lru_cache、partial、reduce、wraps 都在 functools 中。namedtuple 属于 collections 模块，不属于 functools。
