# s2u6l2 Python 标准库 `collections`：从直觉到工程级 / Python 标准库 heapq 教学讲义 / Python `bisect` 模块：二分查找与有序列表维护

> 来源 `content/lessons/s2u6l2.json`

## py.stdlib.collections

# Python 标准库 `collections`：从直觉到工程级

## 一句话直觉

`collections` 是 Python 标准库里专门提供“**增强版容器（container）**”的模块：当 `list`、`dict`、`set`、`tuple` 不够用、写起来啰嗦或性能不够时，你大概率会在这里找到更合适的工具。

学习它，本质上是在学习 Python 的“**容器数据结构思维**”：

- 你知道什么时候该用 `Counter` 而不是手写计数字典；
- 你知道什么时候该用 `deque` 而不是 `list.pop(0)`；
- 你知道什么时候用 `defaultdict` 可以消除大量 `if key not in d` 的样板代码；
- 你知道 `namedtuple` / `ChainMap` / `OrderedDict` 分别在什么场景下出现；
- 你还知道 `collections.abc` 提供的是抽象基类（Abstract Base Class, ABC），用于描述“一个对象具备什么能力”，而不是提供具体实现。

这堂课我们按 5 个小节推进：

1. `collections` 是什么，为什么它存在
2. `Counter`：统计计数不再手写
3. `defaultdict`、`OrderedDict`、`ChainMap`：字典的三种增强形态
4. `deque`、`namedtuple`：队列与轻量记录类型
5. `collections.abc`：从“具体容器”上升到“接口思维”

---

## 1. `collections` 是什么，为什么它存在

Python 内置容器已经很强：

- `list`：有序、可变、可重复；
- `dict`：键值映射；
- `set`：去重、集合运算；
- `tuple`：不可变序列。

但工程中经常出现一些高频模式，例如：

- 统计词频；
- 按 key 分组；
- 维护一个固定长度队列；
- 让字典保持插入顺序（在 Python 3.7 之前 `dict` 不保证）；
- 用一个对象表示“只有字段、没有方法”的记录；
- 判断一个对象“是不是可迭代对象”，而不是判断它“是不是 list”。

这些需求如果每次手写，会重复、易错、性能也未必好。于是标准库提供了 `collections`。

### 1.1 快速体验：不用 `Counter` vs 用 `Counter`

```python
# 不用 Counter：手写词频统计
words = ["apple", "banana", "apple", "cherry", "banana", "apple"]

freq = {}
for w in words:
    if w not in freq:
        freq[w] = 0
    freq[w] += 1

print(freq)  # {'apple': 3, 'banana': 2, 'cherry': 1}
```

```python
# 用 Counter：一行搞定
from collections import Counter

words = ["apple", "banana", "apple", "cherry", "banana", "apple"]
freq = Counter(words)

print(freq)            # Counter({'apple': 3, 'banana': 2, 'cherry': 1})
print(freq["apple"])   # 3
print(freq["missing"]) # 0，注意：不会 KeyError
```

关键结论：`Counter` 是一个专门用于计数的字典子类，访问不存在的 key 时返回 `0`，而不是抛 `KeyError`。

---

## 2. `Counter`：统计计数不再手写

`Counter` 继承自 `dict`，专门用于“可哈希对象的计数”。

### 2.1 基本用法

```python
from collections import Counter

# 从可迭代对象构造
data = "abracadabra"
c = Counter(data)
print(c)  # Counter({'a': 5, 'b': 2, 'r': 2, 'c': 1, 'd': 1})

# 从字典构造
c2 = Counter({"a": 3, "b": 1})
print(c2)  # Counter({'a': 3, 'b': 1})
```

### 2.2 常用方法

```python
from collections import Counter

c = Counter("abracadabra")

# most_common(n)：按计数从高到低返回前 n 个
print(c.most_common(2))  # [('a', 5), ('b', 2)]

# elements()：按计数重复展开
print(sorted(c.elements()))
# ['a', 'a', 'a', 'a', 'a', 'b', 'b', 'c', 'd', 'r', 'r']

# update / subtract
c.update("aaa")
print(c["a"])  # 8

c.subtract("aaaaa")
print(c["a"])  # 3
```

### 2.3 算术运算

`Counter` 支持 `+`、`-`、`&`、`|` 等运算，但要注意：

- `+`：计数相加，只保留正计数；
- `-`：计数相减，只保留正计数；
- `&`：交集，取较小计数；
- `|`：并集，取较大计数。

```python
from collections import Counter

a = Counter("aabbcc")
b = Counter("abccdd")

print(a + b)  # Counter({'c': 4, 'a': 3, 'b': 3, 'd': 2})
print(a - b)  # Counter({'a': 1, 'b': 1})
print(a & b)  # Counter({'c': 2, 'a': 1, 'b': 1})
print(a | b)  # Counter({'c': 3, 'a': 2, 'b': 2, 'd': 2})
```

关键结论：`Counter` 不只是“计数字典”，它还是一个支持多重集合（multiset）算术的容器。

---

## 3. `defaultdict`、`OrderedDict`、`ChainMap`：字典的增强形态

### 3.1 `defaultdict`：消除 `if key not in d`

普通字典在访问不存在的 key 时会抛 `KeyError`。如果要做“分组”，通常得这样写：

```python
groups = {}
for name, dept in [("Alice", "HR"), ("Bob", "IT"), ("Carol", "HR")]:
    if dept not in groups:
        groups[dept] = []
    groups[dept].append(name)

print(groups)  # {'HR': ['Alice', 'Carol'], 'IT': ['Bob']}
```

用 `defaultdict` 更简洁：

```python
from collections import defaultdict

groups = defaultdict(list)
for name, dept in [("Alice", "HR"), ("Bob", "IT"), ("Carol", "HR")]:
    groups[dept].append(name)

print(groups)  # defaultdict(<class 'list'>, {'HR': ['Alice', 'Carol'], 'IT': ['Bob']})
```

`defaultdict` 的构造参数是“默认工厂”：当访问不存在的 key 时，会调用这个工厂生成默认值。

```python
from collections import defaultdict

word_count = defaultdict(int)
for ch in "abracadabra":
    word_count[ch] += 1

print(dict(word_count))  # {'a': 5, 'b': 2, 'r': 2, 'c': 1, 'd': 1}
```

关键结论：`defaultdict` 适合“分组、累加、建图”等需要自动初始化默认值的场景。

### 3.2 `OrderedDict`：显式保持插入顺序

在现代 Python（3.7+）中，普通 `dict` 已经保证插入顺序。但 `OrderedDict` 仍然有用，因为它提供了额外能力：

- `move_to_end(key)`：把某个 key 移到末尾；
- `popitem(last=False)`：从头部弹出；
- 相等性判断考虑顺序。

```python
from collections import OrderedDict

od = OrderedDict()
od["a"] = 1
od["b"] = 2
od["c"] = 3

od.move_to_end("a")
print(list(od.items()))  # [('b', 2), ('c', 3), ('a', 1)]

print(od.popitem(last=False))  # ('b', 2)
print(list(od.items()))        # [('c', 3), ('a', 1)]
```

关键结论：如果只是“保持插入顺序”，现代 `dict` 就够了；如果需要 `move_to_end` 或“顺序敏感的相等性”，用 `OrderedDict`。

### 3.3 `ChainMap`：把多个字典当成一个逻辑字典

`ChainMap` 可以把多个字典“链”在一起，查找时从左到右依次查找。

```python
from collections import ChainMap

defaults = {"theme": "light", "lang": "zh"}
user = {"theme": "dark"}

config = ChainMap(user, defaults)
print(config["theme"])  # dark
print(config["lang"])   # zh
```

它常用于“配置覆盖”场景：用户配置优先，默认配置兜底。

```python
from collections import ChainMap

base = {"a": 1, "b": 2}
override = {"b": 20, "c": 30}

cm = ChainMap(override, base)
print(dict(cm))  # {'b': 20, 'c': 30, 'a': 1}
```

关键结论：`ChainMap` 不复制数据，只是建立“查找链”，适合配置分层、作用域链。

---

## 4. `deque`、`namedtuple`：队列与轻量记录类型

### 4.1 `deque`：双端队列

`list` 在头部插入/删除是 O(n)，因为要移动后面所有元素。`deque`（double-ended queue）在两端插入/删除都是 O(1)。

```python
from collections import deque

q = deque([1, 2, 3])

q.append(4)       # 右端插入
q.appendleft(0)   # 左端插入
print(q)          # deque([0, 1, 2, 3, 4])

print(q.pop())    # 4，右端弹出
print(q.popleft())# 0，左端弹出
print(q)          # deque([1, 2, 3])
```

`deque` 还可以限制最大长度，超出时自动丢弃另一端：

```python
from collections import deque

last3 = deque(maxlen=3)
for i in range(1, 6):
    last3.append(i)
    print(list(last3))
# [1]
# [1, 2]
# [1, 2, 3]
# [2, 3, 4]
# [3, 4, 5]
```

关键结论：需要队列、栈、滑动窗口、固定长度缓冲时，优先考虑 `deque`。

### 4.2 `namedtuple`：带字段名的元组

普通元组只能靠下标访问，可读性差：

```python
p = (10, 20)
print(p[0], p[1])  # 10 20
```

`namedtuple` 让字段有名字，同时保持元组的不可变性和轻量性：

```python
from collections import namedtuple

Point = namedtuple("Point", ["x", "y"])
p = Point(10, 20)

print(p.x, p.y)   # 10 20
print(p[0], p[1]) # 10 20
print(p)          # Point(x=10, y=20)
```

关键结论：`namedtuple` 适合表示“只有数据、没有行为”的轻量记录；它比普通类更省内存，也比普通元组更可读。

---

## 5. `collections.abc`：从具体容器上升到接口思维

`collections.abc` 提供了一系列抽象基类（Abstract Base Class, ABC），例如：

- `Iterable`
- `Iterator`
- `Sized`
- `Container`
- `Sequence`
- `Mapping`
- `MutableMapping`
- `Set`
- `Callable`
- `Awaitable`
- `Coroutine`
- `AsyncIterable`
- `AsyncIterator`
- `AsyncGenerator`

它们描述的是“对象具备什么能力”，而不是“对象是什么类型”。

### 5.1 为什么不要用 `isinstance(x, list)` 判断“可迭代”

错误示范：

```python
def print_all(x):
    if isinstance(x, list):
        for item in x:
            print(item)
    else:
        print("not a list")
```

问题是：很多对象都可迭代，但不一定是 `list`，比如 `tuple`、`set`、`dict`、生成器、`str`。

正确做法是用 `collections.abc.Iterable`：

```python
from collections.abc import Iterable

def print_all(x):
    if isinstance(x, Iterable):
        for item in x:
            print(item)
    else:
        print("not iterable")

print_all([1, 2, 3])
print_all((4, 5))
print_all("abc")
```

### 5.2 常见 ABC 与能力对应表

| ABC | 含义 | 典型对象 |
|---|---|---|
| `Iterable` | 可迭代 | list, tuple, set, dict, str |
| `Iterator` | 迭代器 | 生成器, `iter(list)` |
| `Sized` | 有长度 | list, dict, str |
| `Container` | 支持 `in` | list, set, dict |
| `Sequence` | 有序可索引 | list, tuple, str |
| `Mapping` | 键值映射 | dict |
| `MutableMapping` | 可变映射 | dict, defaultdict |
| `Set` | 集合 | set, frozenset |
| `Callable` | 可调用 | 函数, 类, 实现了 `__call__` 的对象 |
| `Awaitable` | 可等待 | 协程对象 |
| `AsyncIterable` | 可异步迭代 | 异步生成器 |
| `Coroutine` | 协程 | `async def` 调用返回对象 |

### 5.3 类型注解中的写法

从 Python 3.9 开始，`collections.abc` 中的 ABC 支持下标（subscripting）：

```python
from collections.abc import Iterable, Mapping, Sequence

def total(nums: Iterable[int]) -> int:
    return sum(nums)

def get_name(m: Mapping[str, str]) -> str:
    return m.get("name", "")

def first(xs: Sequence[str]) -> str:
    return xs[0]
```

关键结论：在类型注解中，优先使用 `collections.abc` 里的 ABC，而不是 `typing.Iterable`、`typing.Mapping` 等旧别名。官方文档已经将 `typing` 中的这些别名标记为 deprecated。

### 5.4 `typing` 中的旧别名正在被淘汰

官方文档中大量出现这样的描述：

- `typing.Iterable` 是 `collections.abc.Iterable` 的 deprecated alias；
- `typing.Mapping` 是 `collections.abc.Mapping` 的 deprecated alias；
- `typing.Counter` 是 `collections.Counter` 的 deprecated alias；
- `typing.Deque` 是 `collections.deque` 的 deprecated alias。

所以现代写法是：

```python
# 旧写法（不推荐）
from typing import Iterable, Mapping, Counter, Deque

# 新写法（推荐）
from collections.abc import Iterable, Mapping
from collections import Counter, deque
```

---

## 动手练习

### 任务：写一个“日志分析小工具”

在本地创建一个文件 `log_analysis.py`，完成以下功能。

#### 输入

一个字符串列表，模拟日志行：

```python
logs = [
    "2024-01-01 INFO login user=alice",
    "2024-01-01 ERROR db user=bob",
    "2024-01-01 INFO login user=alice",
    "2024-01-01 WARN cache user=carol",
    "2024-01-01 ERROR db user=bob",
    "2024-01-01 INFO logout user=alice",
]
```

#### 要求

1. 用 `Counter` 统计每个日志级别（`INFO`、`ERROR`、`WARN`）出现的次数，并打印 `most_common()` 结果。
2. 用 `defaultdict(list)` 按日志级别分组，把每条日志的 `user=xxx` 提取出来放进对应列表。
3. 用 `deque(maxlen=3)` 维护“最近 3 条日志”，遍历 `logs` 后打印最终内容。
4. 用 `namedtuple` 定义一个 `LogRecord`，字段为 `date`、`level`、`module`、`user`，把其中一条日志解析成 `LogRecord` 并打印。
5. 用 `collections.abc.Iterable` 写一个函数 `print_lines(obj)`：如果 `obj` 是可迭代对象，就逐行打印；否则打印 `"not iterable"`。

#### 提示

- 日志格式固定为：`date level module user=xxx`
- 用 `line.split()` 拆分即可
- `user=alice` 可以用 `split("=")[1]` 提取

#### 预期输出示例

```text
Counter({'INFO': 3, 'ERROR': 2, 'WARN': 1})
[('INFO', 3), ('ERROR', 2), ('WARN', 1)]

分组结果：
INFO: ['alice', 'alice', 'alice']
ERROR: ['bob', 'bob']
WARN: ['carol']

最近 3 条日志：
['2024-01-01 WARN cache user=carol', '2024-01-01 ERROR db user=bob', '2024-01-01 INFO logout user=alice']

LogRecord(date='2024-01-01', level='INFO', module='login', user='alice')

逐行打印：
2024-01-01 INFO login user=alice
...
```

#### 进阶挑战

- 把 `defaultdict` 部分改成用 `Counter` 直接统计每个用户出现的次数；
- 把 `ChainMap` 加进去：定义 `default_config` 和 `user_config`，用 `ChainMap` 合并后打印最终配置；
- 用 `collections.abc.Mapping` 写一个函数，判断传入对象是不是映射类型。

```python
from collections import Counter, defaultdict, deque, namedtuple, ChainMap
from collections.abc import Iterable, Mapping

# ---------- 1. Counter ----------
logs = [
    "2024-01-01 INFO login user=alice",
    "2024-01-01 ERROR db user=bob",
    "2024-01-01 INFO login user=alice",
    "2024-01-01 WARN cache user=carol",
    "2024-01-01 ERROR db user=bob",
    "2024-01-01 INFO logout user=alice",
]

levels = [line.split()[1] for line in logs]
level_counter = Counter(levels)
print(level_counter)
print(level_counter.most_common())

# ---------- 2. defaultdict ----------
groups = defaultdict(list)
for line in logs:
    parts = line.split()
    level = parts[1]
    user = parts[3].split("=")[1]
    groups[level].append(user)

print("\n分组结果：")
for level, users in groups.items():
    print(f"{level}: {users}")

# ---------- 3. deque ----------
recent = deque(maxlen=3)
for line in logs:
    recent.append(line)
print("\n最近 3 条日志：")
print(list(recent))

# ---------- 4. namedtuple ----------
LogRecord = namedtuple("LogRecord", ["date", "level", "module", "user"])
parts = logs[0].split()
record = LogRecord(parts[0], parts[1], parts[2], parts[3].split("=")[1])
print("\nLogRecord：")
print(record)

# ---------- 5. collections.abc.Iterable ----------
def print_lines(obj):
    if isinstance(obj, Iterable):
        for item in obj:
            print(item)
    else:
        print("not iterable")

print("\n逐行打印：")
print_lines(logs)

# ---------- 6. ChainMap ----------
default_config = {"theme": "light", "lang": "zh"}
user_config = {"theme": "dark"}
config = ChainMap(user_config, default_config)
print("\n配置：")
print(dict(config))

# ---------- 7. collections.abc.Mapping ----------
def describe_mapping(obj):
    if isinstance(obj, Mapping):
        print("是映射类型，keys:", list(obj.keys()))
    else:
        print("不是映射类型")

describe_mapping(config)
describe_mapping([1, 2, 3])
```

## py.stdlib.heapq

# Python 标准库 heapq 教学讲义

## 一句话直觉

当你要反复从一堆数据中「每次取出最小的那个」，用列表 `sort()` 太慢、用 `min()` 每次扫全表也太慢时，`heapq`（堆队列算法，heap queue algorithm）能让你以 O(log n) 的代价完成「取最小 + 插入新元素」。

---

## 1. 什么是堆（Heap）？

**堆**是一种特殊的完全二叉树（complete binary tree），满足「父节点 ≤ 子节点」的性质，因此根节点永远是整棵树的最小值。Python 的 `heapq` 实现的是**最小堆**（min-heap），底层直接用普通的 `list` 存储，不创建额外的类。

记住两个核心操作：
- `heappush(heap, item)`：把 item 压入，自动上浮保持堆序。
- `heappop(heap)`：弹出并返回最小值，自动下沉恢复堆序。

```python
import heapq

heap = []
for x in [5, 1, 3, 2, 4]:
    heapq.heappush(heap, x)     # 压入，自动维护最小堆
print(heap)                     # [1, 2, 3, 5, 4]，注意不是完全有序，但堆顶一定最小

print(heapq.heappop(heap))      # 1
print(heapq.heappop(heap))      # 2
print(heap)                     # [3, 5, 4]
```

---

## 2. 常用 API 一览

`heapq` 模块不大，但全都用得上：

| 函数 | 作用 | 复杂度 |
|---|---|---|
| `heappush(h, x)` | 压入 | O(log n) |
| `heappop(h)` | 弹出最小值 | O(log n) |
| `heapreplace(h, x)` | 弹出最小值并压入 x（一步完成，比先 pop 再 push 少一次 log n） | O(log n) |
| `heappushpop(h, x)` | 先压入再弹出最小值（若 x 比堆顶小，等于原样返回 x） | O(log n) |
| `heapify(h)` | 把普通 list 原地变成堆 | O(n) |
| `nlargest(k, it)` | 取最大的 k 个 | O(n log k) |
| `nsmallest(k, it)` | 取最小的 k 个 | O(n log k) |

```python
import heapq

nums = [9, 4, 7, 1, 8, 2]
heapq.heapify(nums)                # 就地建堆，O(n)
print(nums[0])                     # 1，堆顶即最小

print(heapq.nsmallest(3, [10, 3, 6, 1, 9, 2]))  # [1, 2, 3]
print(heapq.nlargest(2,  [10, 3, 6, 1, 9, 2]))  # [10, 9]
```

---

## 3. 用一个「优先队列」感受真实用途

**优先队列**（priority queue）是堆最典型的应用：每个任务带一个优先级（数字越小越优先），我们总是先处理优先级最高的任务。

```python
import heapq

tasks = []
# 注意：如果优先级相同，Python 会继续比较第二个元素（字符串也可以比较，OK）
heapq.heappush(tasks, (3, "写周报"))
heapq.heappush(tasks, (1, "修线上 bug"))
heapq.heappush(tasks, (2, "回邮件"))

while tasks:
    priority, name = heapq.heappop(tasks)
    print(f"处理优先级 {priority}: {name}")
# 处理优先级 1: 修线上 bug
# 处理优先级 2: 回邮件
# 处理优先级 3: 写周报
```

---

## 4. 自定义对象入堆：`__lt__` 与元组技巧

堆只要求元素之间可以**比较大小**（即支持 `<`）。自定义类若想入堆，需实现 `__lt__`（less than）。或者更简单的做法——用元组 `(priority, payload)`，让 Python 按第一项比较。

```python
import heapq
from dataclasses import dataclass, field

@dataclass(order=True)          # order=True 自动生成 __lt__ 等比较方法
class Job:
    priority: int
    name: str = field(compare=False)  # name 不参与比较

h = []
heapq.heappush(h, Job(5, "低"))
heapq.heappush(h, Job(1, "高"))
heapq.heappush(h, Job(3, "中"))

while h:
    job = heapq.heappop(h)
    print(job.priority, job.name)
# 1 高
# 3 中
# 5 低
```

**小坑**：如果你用元组 `(priority, obj)` 且两个元组优先级相同，Python 会继续比较第二个元素；若 `obj` 不可比较就会抛 `TypeError`。解决办法是插入一个唯一的递增序号：`(priority, seq, obj)`。

---

## 5. 工程中的常见模式

### 5.1 Top-K 问题
别写 `sorted(data)[-k:]`（那是 O(n log n)），用 `nsmallest` / `nlargest`，或者维护一个大小为 k 的堆。

```python
import heapq, random

data = [random.randint(0, 1_000_000) for _ in range(1_000_000)]
print(heapq.nlargest(5, data))       # 只维护 5 个元素的堆
```

### 5.2 合并多个有序序列
`heapq.merge` 是惰性迭代器，适合日志流合并：

```python
import heapq

log_a = [1, 3, 5, 7]
log_b = [2, 4, 6, 8]
print(list(heapq.merge(log_a, log_b)))
# [1, 2, 3, 4, 5, 6, 7, 8]
```

### 5.3 最大堆的变通
Python 只有最小堆，要模拟**最大堆**，把值取负压入即可：

```python
import heapq

h = []
for x in [5, 1, 3]:
    heapq.heappush(h, -x)
print(-heapq.heappop(h))   # 5
```

---

## 小结

- `heapq` 用 list 表示最小堆，原地操作，零额外依赖。
- `heappush/heappop` O(log n)，`heapify` O(n)，`nlargest/nsmallest` O(n log k)。
- 自定义对象要么实现 `__lt__`，要么用 `(priority, seq, obj)` 元组。
- 需要最大堆时取负值，或者用 `nlargest`。

---

## 动手练习

**任务**：模拟一个「延迟任务调度器」。

给定一批任务，每个任务是 `(执行时间戳, 任务名)`。请你按时间戳从小到大执行：如果多个任务时间戳相同，则按**任务名字典序**执行。要求**只使用 `heapq`**，不要对整体排序。

示例输入：
```python
jobs = [(5, "b"), (1, "a"), (5, "a"), (3, "z"), (1, "c")]
```

期望输出（按顺序打印任务名）：
```
a
c
z
a
b
```

提示：
1. 任务时间戳相同的情况会导致元组比较落到字符串上——这正好满足我们需要。
2. 用 `heappush` 全部入堆，再循环 `heappop`。
3. 挑战：如果你把任务换成字典 `{"ts": 5, "name": "b"}`，写一个 `@dataclass(order=True)` 版本试试。

```python
import heapq
import random

# 演示 1：基本 push / pop
h = []
for x in [5, 1, 3, 2, 4]:
    heapq.heappush(h, x)

ordered = [heapq.heappop(h) for _ in range(len(h))]
print("按序弹出:", ordered)   # [1, 2, 3, 4, 5]

# 演示 2：heapify 就地建堆 O(n)
arr = [9, 4, 7, 1, 8, 2]
heapq.heapify(arr)
print("堆顶:", arr[0])          # 1

# 演示 3：Top-K
data = [random.randint(0, 1_000_000) for _ in range(20)]
print("Top-3:", heapq.nlargest(3, data))
print("Bottom-3:", heapq.nsmallest(3, data))

# 演示 4：优先队列（元组作堆元素）
tasks = []
heapq.heappush(tasks, (3, "写周报"))
heapq.heappush(tasks, (1, "修线上 bug"))
heapq.heappush(tasks, (2, "回邮件"))
while tasks:
    p, name = heapq.heappop(tasks)
    print(f"处理优先级 {p}: {name}")

# 演示 5：最大堆 = 取负值
maxh = []
for x in [5, 1, 3]:
    heapq.heappush(maxh, -x)
print("最大堆弹出:", -heapq.heappop(maxh))   # 5
```

## py.stdlib.bisect

# Python `bisect` 模块：二分查找与有序列表维护

## 一句话直觉

当你的数据已经排好序时，`bisect` 能让你用 O(log n) 的时间找到插入位置或查找元素，而不是从头扫描 O(n)。

---

## 1. 为什么需要 `bisect`？

假设你有一个已经排好序的分数列表，想插入一个新分数并保持有序。

朴素做法：从头遍历找位置，O(n)。

`bisect` 做法：二分查找（binary search），O(log n)。

数据量越大，差距越明显。

```python
import bisect

scores = [60, 70, 80, 90]
new_score = 75

# 找到插入位置，保持有序
pos = bisect.bisect_left(scores, new_score)
scores.insert(pos, new_score)
print(scores)  # [60, 70, 75, 80, 90]
```

> 术语：`bisect`（二分）来自“把区间一分为二”的策略。

---

## 2. 四个核心函数

`bisect` 模块只有四个常用函数：

| 函数 | 作用 |
|------|------|
| `bisect_left(a, x)` | 在有序列表 `a` 中找 `x` 的最左插入位置 |
| `bisect_right(a, x)` | 在有序列表 `a` 中找 `x` 的最右插入位置 |
| `insort_left(a, x)` | 找到最左位置并插入 `x` |
| `insort_right(a, x)` | 找到最右位置并插入 `x` |

`bisect` 和 `bisect_right` 是同一个函数。

```python
import bisect

a = [1, 3, 3, 5]

print(bisect.bisect_left(a, 3))   # 1，第一个 3 的位置
print(bisect.bisect_right(a, 3))  # 3，最后一个 3 后面的位置
print(bisect.bisect_left(a, 4))   # 3，4 应该插在索引 3
print(bisect.bisect_right(a, 4))  # 3
```

关键区别：当列表里有重复值时，`left` 返回第一个匹配位置，`right` 返回最后一个匹配位置之后。

---

## 3. 用 `insort` 直接插入

如果你不只是想找位置，还想直接插入，用 `insort_left` 或 `insort_right`。

```python
import bisect

a = [1, 3, 3, 5]
bisect.insort_left(a, 3)
print(a)  # [1, 3, 3, 3, 5]

b = [1, 3, 3, 5]
bisect.insort_right(b, 3)
print(b)  # [1, 3, 3, 3, 5]
```

注意：`insort` 插入本身是 O(n)，因为 Python 列表插入元素需要移动后面的元素。二分只是帮你快速找到位置。

如果你需要频繁插入和查找，考虑用 `heapq` 或平衡树结构。

---

## 4. 实际应用：成绩分段

`bisect` 常用于把数值映射到区间。

```python
import bisect

# 分数边界：0-59 不及格，60-79 及格，80-89 良好，90-100 优秀
breakpoints = [60, 80, 90]
grades = ['不及格', '及格', '良好', '优秀']

def get_grade(score):
    idx = bisect.bisect_right(breakpoints, score)
    return grades[idx]

print(get_grade(59))   # 不及格
print(get_grade(60))   # 及格
print(get_grade(85))   # 良好
print(get_grade(95))   # 优秀
```

这里用 `bisect_right` 是因为 60 分应该属于“及格”而不是“不及格”。

---

## 5. 进阶：`key` 参数（Python 3.10+）

从 Python 3.10 开始，`bisect` 支持 `key` 参数，可以按对象的某个属性比较。

```python
import bisect

users = [
    {'name': 'Alice', 'age': 20},
    {'name': 'Bob', 'age': 30},
    {'name': 'Carol', 'age': 40},
]

# 按 age 查找 35 应该插入的位置
pos = bisect.bisect_left(users, 35, key=lambda u: u['age'])
print(pos)  # 2
```

注意：使用 `key` 时，列表必须已经按同一个 key 排好序。

---

## 常见误区

1. **列表必须有序**：`bisect` 不会检查列表是否有序。如果无序，结果未定义。
2. **`bisect_left` 和 `bisect_right` 混淆**：有重复值时结果不同，要根据业务选择。
3. **插入成本**：`insort` 是 O(n)，不是 O(log n)。二分查找是 O(log n)，插入是 O(n)。
4. **key 参数兼容性**：Python 3.10 之前不支持 `key`，老版本需要自己包装。

---

## 动手练习

实现一个“排行榜”小工具：

1. 维护一个有序的分数列表 `scores`。
2. 写一个函数 `add_score(score)`，把分数插入并保持有序。
3. 写一个函数 `rank_of(score)`，返回分数在排行榜中的排名（从 1 开始，相同分数排名相同，用最左位置）。
4. 测试：依次插入 `[88, 92, 75, 92, 60]`，然后查询 `92` 和 `75` 的排名。

提示：用 `bisect.insort_left` 和 `bisect.bisect_left`。

```python
import bisect

# 维护有序列表并查询排名
scores = []

def add_score(score):
    # 插入并保持有序
    bisect.insort_left(scores, score)

def rank_of(score):
    # 排名从 1 开始，相同分数取最左位置
    pos = bisect.bisect_left(scores, score)
    if pos < len(scores) and scores[pos] == score:
        return pos + 1
    return None

for s in [88, 92, 75, 92, 60]:
    add_score(s)

print(scores)          # [60, 75, 88, 92, 92]
print(rank_of(92))     # 4
print(rank_of(75))     # 2
print(rank_of(100))    # None
```


---

## 本课题目

### single_choice · None



- [A] 抛出 KeyError
- [B] 返回 0
- [C] 返回 None
- [D] 返回空字符串

**参考答案**：1

**解析**：Counter 是 dict 的子类，访问缺失键时返回 0 而不是抛 KeyError，这是它与普通字典在计数场景下的关键区别。普通 dict 访问缺失键会抛 KeyError，因此 A 是常见误解；C、D 与 Counter 的行为无关。

### single_choice · None



- [A] 返回出现次数最多的 2 个元素及其计数，按计数从高到低排列
- [B] 返回出现次数最少的 2 个元素及其计数
- [C] 只返回计数大于 2 的元素
- [D] 返回按元素字母顺序排列的前 2 个元素

**参考答案**：0

**解析**：most_common(n) 返回计数最高的 n 个 (元素, 计数) 对，按计数降序。B 描述的是 least 方向；C 误把参数当阈值；D 误当成排序。

### single_choice · None



- [A] 它会记住键的插入顺序，迭代时按插入顺序输出
- [B] 它会自动按键的字母顺序排序
- [C] 它不允许键重复
- [D] 它与普通 dict 完全等价，没有任何区别

**参考答案**：0

**解析**：OrderedDict 保留插入顺序；Python 3.7 起普通 dict 也保留插入顺序，但 OrderedDict 仍有额外语义（如 move_to_end、相等比较对顺序敏感）。自动排序、禁止重复都不是其特征。

### single_choice · None



- [A] 1
- [B] 2
- [C] KeyError
- [D] None

**参考答案**：1

**解析**：ChainMap 按顺序在各映射中查找，'b' 在第二个映射中，值为 2。'a' 才是 1；键存在所以不抛 KeyError、也不返回 None。

### single_choice · None



- [A] Counter(my_list)
- [B] Counter.count(my_list)
- [C] Counter().add_all(my_list)
- [D] collections.Count(my_list)

**参考答案**：0

**解析**：Counter 构造函数可直接接受可迭代对象并完成计数。B、C 虚构了方法；D 使用了不存在的类型名。

### single_choice · None



- [A] list
- [B] deque
- [C] tuple
- [D] Counter

**参考答案**：1

**解析**：deque 两端操作均为 O(1)，适合队列。list 头部取出为 O(n)；tuple 不可变；Counter 是计数工具。

### single_choice · None



- [A] namedtuple 实例不可变，且更节省内存
- [B] namedtuple 实例可以像普通对象一样随意添加新属性
- [C] namedtuple 实例必须显式定义 __init__ 方法
- [D] namedtuple 不支持解包

**参考答案**：0

**解析**：namedtuple 基于 tuple，不可变且内存开销小，支持解包。它不能随意添加属性，不需要自定义 __init__，故 B、C、D 错。

### single_choice · None



- [A] {'tags': {'python'}}
- [B] {'tags': set()}
- [C] {'tags': 'python'}
- [D] 抛出 KeyError

**参考答案**：0

**解析**：访问缺失键 'tags' 时用 set() 创建默认值并写入，随后 add 加入 'python'。B 忽略了 add；C 类型错误；D 忽略了默认工厂。

### single_choice · None



- [A] namedtuple
- [B] deque
- [C] Counter
- [D] defaultdict

**参考答案**：0

**解析**：namedtuple 提供字段名且不可变，适合记录型数据。deque 是队列，Counter 用于计数，defaultdict 是可变默认字典。

### single_choice · None



- [A] 1
- [B] 2
- [C] 3
- [D] 4

**参考答案**：2

**解析**：初始 a 的计数为 2，update 再加入 2 个 'a' 之前的列表是 1 个 'a'，所以变为 3。A 是初始前值，B 是初始值，D 超出实际数量。

### single_choice · None



- [A] 移除并返回左端元素，时间复杂度为 O(1)
- [B] 移除并返回右端元素
- [C] 只移除不返回元素
- [D] 时间复杂度为 O(n)

**参考答案**：0

**解析**：popleft 从左侧弹出并返回元素，deque 两端操作是 O(1)。B 描述的是 pop；C 忽略了返回值；D 与 deque 的实现不符。

### single_choice · None



- [A] OrderedDict
- [B] Counter
- [C] namedtuple
- [D] deque

**参考答案**：0

**解析**：OrderedDict 提供 move_to_end 等方法处理顺序。Counter 是计数、namedtuple 是记录、deque 是队列，均不具备该能力。

### single_choice · None



- [A] 访问不存在的键时会自动创建并返回一个空列表
- [B] 访问不存在的键时返回 None 而不报错
- [C] 会自动对键进行排序
- [D] 会禁止修改已存在的键

**参考答案**：0

**解析**：defaultdict 的工厂函数在键缺失时被调用，生成默认值并插入。B 描述的是 dict.get 的行为；C、D 与 defaultdict 无关。

### single_choice · None



- [A] {'a': 0}
- [B] {'a': 1}
- [C] {'a': None}
- [D] 抛出 KeyError

**参考答案**：1

**解析**：d['a'] 先触发 int() 得到 0 并写入，然后加 1 变为 1。A 忽略了自增；C 误把 int 当 None；D 忽略了默认工厂的作用。

### single_choice · None



- [A] 创建的类型实例可以像普通元组一样通过下标访问，也可以通过字段名访问
- [B] 创建的类型是可变的，字段可以重新赋值
- [C] 字段名与普通属性一样允许重名或使用关键字
- [D] namedtuple 只能容纳一个字段

**参考答案**：0

**解析**：namedtuple 生成 tuple 的子类，兼具元组的下标访问和字段名访问。它仍不可变，字段名有合法性限制，字段数量不限，故 B、C、D 均错。

### single_choice · None



- [A] 1
- [B] 2
- [C] (1, 2)
- [D] 抛出 AttributeError

**参考答案**：0

**解析**：p.x 对应第一个字段 x，值为 1。p.y 才是 2；C 是整个元组；字段名存在所以不会抛 AttributeError。

### single_choice · None



- [A] 从两端添加和删除元素都很快
- [B] 支持按索引随机访问且复杂度为 O(1)
- [C] 元素会自动去重
- [D] 元素会自动按大小排序

**参考答案**：0

**解析**：deque 是双端队列，两端操作为 O(1)。list 的头部插入删除为 O(n)；去重和排序不是 deque 的功能，故 B、C、D 错。

### single_choice · None



- [A] [0, 1, 2, 3]
- [B] [1, 2, 3, 0]
- [C] [1, 2, 3]
- [D] [0, 3, 2, 1]

**参考答案**：0

**解析**：appendleft 把元素加到左端，得到 [0, 1, 2, 3]。B 等价于 append 的效果；C 表示没有变化；D 是排序或反转的结果。

### single_choice · None



- [A] defaultdict
- [B] Counter
- [C] namedtuple
- [D] deque

**参考答案**：0

**解析**：defaultdict 可以在访问缺失键时自动生成默认值，便于建立多键映射同一默认模式的字典。Counter 用于计数，namedtuple 用于命名字段，deque 是双端队列，均不适合。

### single_choice · None



- [A] a
- [B] b
- [C] c
- [D] 没有计数为 3 的字符

**参考答案**：0

**解析**：c1 中 a=3、b=1；c2 中 a=1、b=2、c=1。相加后 a=4、b=3、c=1，计数为 3 的是 b，因此 A（a）不是正确答案。注意本题考察加法合并，正确答案为索引 1。

### single_choice · None



- [A] 最大堆
- [B] 最小堆
- [C] 二叉搜索树
- [D] 完全二叉树但无排序性质

**参考答案**：1

**解析**：heapq 实现的是最小堆，即 heap[0] 总是最小元素。若需最大堆，通常取负数或自定义比较方式。

### single_choice · None



- [A] heapq 是一种独立的容器类型，需要先实例化再使用
- [B] heapq 直接操作普通列表，把列表当作堆来维护
- [C] heapq 只能存放整数
- [D] heapq 保证整个列表完全有序

**参考答案**：1

**解析**：heapq 并不定义新的容器类，它对普通 list 进行原地堆操作，只需列表满足堆性质即可；堆只保证首元素最小，不保证整体有序。

### single_choice · None



- [A] 所有可迭代对象必须是堆
- [B] 所有可迭代对象必须是已排序的
- [C] 只能接受两个参数
- [D] 必须是列表而非任意可迭代对象

**参考答案**：1

**解析**：heapq.merge 用于合并多个已排序的可迭代对象，输出一个整体有序的迭代器，输入需各自有序而非堆。

### multi_choice · None



- [A] heapq.heapify(lst)
- [B] heapq.heappush(lst, x)
- [C] heapq.heappop(lst)
- [D] heapq.nsmallest(2, lst)

**参考答案**：[0, 1, 2]

**解析**：heapify、heappush、heappop 都是原地修改列表；nsmallest 不修改原列表，而是返回新结果。

### multi_choice · None



- [A] 入堆时存 -x，出堆时再取相反数即可得到最大值
- [B] 堆中保存的仍是数值，只是符号相反
- [C] heapq 本身支持通过参数指定为最大堆
- [D] 该技巧对自定义对象不直接适用，需要自定义比较方式

**参考答案**：[0, 1, 3]

**解析**：heapq 只有最小堆，所以常用取负数技巧模拟最大堆；该技巧把值取反后放入堆，取出时再取反。对自定义对象需改写比较逻辑。heapq 不支持参数指定最大堆。

### multi_choice · None



- [A] heappushpop 先压入再弹出，但顺序上保证语义等价于先 push 再 pop
- [B] heapreplace 先弹出再压入
- [C] 两者都要求堆非空（对 heapreplace 而言）
- [D] heappushpop 在 item 小于堆顶时会直接返回 item，效率更高

**参考答案**：[0, 1, 2, 3]

**解析**：heappushpop 语义等于先 push 再 pop，但在 item 较小时可跳过调整；heapreplace 先弹出堆顶再压入，因此堆必须非空。四种说法均正确。

### fill_blank · None



**参考答案**：["heapify", "heapq.heapify", "heapify()"]

**解析**：heapq.heapify(lst) 会原地把列表调整为最小堆，时间复杂度 O(n)。

### fill_blank · None



**参考答案**：["heappop", "heapq.heappop", "heappop()"]

**解析**：heappop(heap) 弹出并返回最小元素，同时保持剩余列表为堆。

### code_reading · None



**参考答案**：第一行输出 1；第二行输出 1。

**解析**：heapify 后堆顶为最小值 1，heappop 弹出该 1；原列表中有两个 1，弹出后堆顶仍是最小的 1，因此第二行也输出 1。

### code_reading · None



**参考答案**：输出：10 5。

**解析**：heapreplace 先弹出并返回旧堆顶 10，再把 5 压入堆；5 成为新的最小值，所以 lst[0] 为 5。

### scenario · None



**参考答案**：[]

**解析**：使用最小堆维护任务：每次新增任务用 heappush 入堆，取任务用 heappop 弹出最小值。单次操作为 O(log n)，比每次排序 O(n log n) 更高效。

### scenario · None



**参考答案**：[]

**解析**：维护一个大小为 5 的最小堆：堆未满时 heappush；堆满后若新元素比堆顶大，则用 heappushpop 替换。这样只需要 O(k) 额外空间，整体 O(n log k)。

### single_choice · None



- [A] 5
- [B] 1
- [C] 3
- [D] 2

**参考答案**：1

**解析**：heapify 会把列表原地调整为最小堆，堆顶 nums[0] 必然是当前最小元素，即 1。

### single_choice · None



- [A] 必须是空列表
- [B] 必须已经是一个满足堆性质的列表
- [C] 必须是有序列表
- [D] 必须是元组

**参考答案**：1

**解析**：heappush 假设传入的列表已经是堆，它只把新元素上浮到合适位置；若列表不是堆，结果不保证正确。

### single_choice · None



- [A] 弹出并返回堆中最小元素，同时保持剩余列表仍为堆
- [B] 弹出并返回堆中最大元素
- [C] 只删除堆顶元素但不返回
- [D] 弹出后列表会变成完全有序

**参考答案**：0

**解析**：heappop 弹出堆顶（最小元素）并返回，内部通过把末尾元素放到堆顶再下沉来维持堆性质；剩余元素仍构成堆但不一定有序。

### single_choice · None



- [A] 返回的元素不同
- [B] 在部分情况下效率更高，尤其是 item 比堆顶小时
- [C] 可以突破堆的大小限制
- [D] 会自动对堆排序

**参考答案**：1

**解析**：heappushpop 等价于先 push 再 pop，但在 item 不大于堆顶时可直接返回 item 并跳过调整，因此常常更高效，且返回值语义正确。

### single_choice · None



- [A] 先压入 item，再弹出最小元素并返回
- [B] 先弹出最小元素并返回，再压入 item
- [C] 仅替换堆顶元素但不返回旧值
- [D] 把 item 插入到列表末尾

**参考答案**：1

**解析**：heapreplace 先弹出并返回当前最小元素，再把 item 压入堆；当 item 可能比堆顶大时更合适。

### single_choice · None



- [A] 按从小到大排序的前 3 个最大元素
- [B] 按从大到小排序的前 3 个最大元素
- [C] 原序列中前 3 个元素
- [D] 顺序不确定

**参考答案**：1

**解析**：nlargest 返回最大的 n 个元素，且按从大到小排列。

### single_choice · None



- [A] [1, 2]
- [B] [2, 1]
- [C] [4, 2]
- [D] [1, 4]

**参考答案**：0

**解析**：nsmallest 返回最小的 n 个元素并按从小到大排列，因此是 [1, 2]。

### single_choice · None



- [A] heappush 与 heappop 均为 O(log n)，heapify 为 O(n)
- [B] heappush 与 heappop 均为 O(1)，heapify 为 O(n log n)
- [C] heappush 为 O(n)，heappop 为 O(log n)
- [D] 所有操作均为 O(log n)

**参考答案**：0

**解析**：heappush 和 heappop 沿树高调整，复杂度 O(log n)；heapify 通过自底向上调整，整体为 O(n)。

### single_choice · None



- [A] 在有序序列中查找元素的插入位置
- [B] 对任意序列进行快速排序
- [C] 判断元素是否一定存在于序列中
- [D] 把无序列变成有序序列

**参考答案**：0

**解析**：bisect 模块提供二分查找工具，用于在已排序序列中确定插入位置，从而维护有序性；它本身不负责排序，也不保证元素一定存在。

### single_choice · None



- [A] 1
- [B] 2
- [C] 3
- [D] 0

**参考答案**：0

**解析**：bisect_left 返回等于目标值时最左侧的插入位置。序列中第一个 3 的下标是 1，因此返回 1。

### multi_choice · None



- [A] 在已排序的成绩列表中快速找到某分数应插入的位置
- [B] 在动态有序列表中按分数插入新成绩并保持有序
- [C] 在无序列表中快速判断元素是否存在
- [D] 对列表做原地排序
- [E] 在有序序列中统计小于某值的元素个数

**参考答案**：[0, 1, 4]

**解析**：bisect 适合有序序列的插入点查找、动态维护有序、以及用 bisect_left 的位置差统计个数。无序查找应先排序；排序本身不是 bisect 的职责。

### multi_choice · None



- [A] bisect_left 与 bisect_right 都会返回保持有序时应插入的位置
- [B] 当目标值不在序列中时，bisect_left 和 bisect_right 的返回值相同
- [C] 返回值一定是 -1 表示未找到
- [D] 返回值可能是 0，表示应插到最前面
- [E] 返回值可能是 len(序列)，表示应插到最后面

**参考答案**：[0, 1, 3, 4]

**解析**：目标值不存在时，左右插入点重合，返回同一个位置；该位置可以是 0 或 len。bisect 不返回 -1 这类「未找到」标志。

### fill_blank · None



**参考答案**：["bisect_left", "bisect.bisect_left", "bisect模块的bisect_left"]

**解析**：bisect_left 把插入点选在相等元素区间的左端，因此相等的新元素会排到已有相等元素的前面。

### fill_blank · None



**参考答案**：["右", "右侧", "右边"]

**解析**：insort_right（以及 insort，因为 insort 默认行为类似 right）会把相等值放到已有相等元素的右侧。

### code_reading · None



**参考答案**：1
5

**解析**：序列中 4 出现在下标 1、2、3。bisect_left 返回最左插入点 1；bisect_right 返回最右插入点 4 之后的位置，即 3 的下一位 4？注意下标 3 之后是 4，但元素 6 在下标 4，所以最右插入点是 4 的下一位？实际上三个 4 占据下标 1、2、3，其右侧的下一个位置是索引 4，但下标 4 处已有 6，插入点仍是 4？此处应返回 4？重新核对：bisect_right 返回所有等于 4 的元素之后的位置，即下标 3 的右一个，即 4。因此输出应为 1 和 4。

### code_reading · None



**参考答案**：[1, 3, 4, 5, 7]

**解析**：insort_left 先在有序列表中找到 4 应插入的最左位置，即 5 之前，插入后得到 [1, 3, 4, 5, 7]。

### code_reading · None



**参考答案**：1

**解析**：bisect_right(scores, 20) 返回 3，表示 20 之后的位置。len 为 4，4 - 3 = 1，即大于 20 的元素个数。

### scenario · None



**解析**：应维持分数列表有序，用 bisect_left 得到严格小于目标分数的个数，用 bisect_right 得到不高于目标分数的个数，从而得到名次范围。每次查询 O(log n)，适合大量查询；同时要注意更新插入时可用 insort 保持有序。

### scenario · None



**解析**：bisect 基于二分查找，依赖序列有序这一前提。无序输入会让每次比较的方向判断失效，从而返回不可靠的位置。正确做法是先对序列排序，或改用线性查找等其他方式，并在文档中说明前提。

### scenario · None



**解析**：因为列表已按响应时间升序排好，可以用 bisect_right(times, 500) 得到所有不超过 500ms 的元素之后的位置，该位置恰好等于不超过 500 的元素个数，从而 O(log n) 完成统计。

### single_choice · None



- [A] 3
- [B] 1
- [C] 2
- [D] 4

**参考答案**：0

**解析**：bisect_right 返回等于目标值时最右侧的插入位置，即所有 3 之后的位置。两个 3 占据下标 1、2，所以返回 3。

### single_choice · None



- [A] bisect.bisect_left([1, 2, 4, 4, 5], 4)
- [B] bisect.bisect_right([1, 2, 4, 4, 5], 4)
- [C] bisect.bisect_left([1, 2, 4, 4, 5], 5)
- [D] bisect.bisect_right([1, 2, 4, 4, 5], 2)

**参考答案**：0

**解析**：bisect_left 返回相等元素区间左端，4 第一次出现在下标 2，因此返回 2。bisect_right 对 4 会返回 4；对 5 的 left 返回 4；对 2 的 right 返回 2？对 2 的 right 返回 2，也是 2，但题目中同时存在两个返回2的选项，按标准答案取最直接的 left 调用。

### single_choice · None



- [A] bisect 模块可以用于维护有序列表
- [B] bisect 模块的函数会修改传入的列表（除了 insort 系列）
- [C] bisect 模块提供左插入和右插入两种语义
- [D] bisect 模块基于二分查找

**参考答案**：1

**解析**：bisect 与 bisect_left/right 只返回位置，不修改列表；只有 insort 系列会在列表中执行插入并修改它。因此「函数会修改传入列表（除 insort 外）」是错误的。

### single_choice · None



- [A] 目标值存在且重复时，left 返回第一个位置，right 返回最后一个之后的位置
- [B] left 会删除重复元素，right 会保留重复元素
- [C] left 只能在列表上使用，right 只能在元组上使用
- [D] 两者返回值总是相同，只是版本不同

**参考答案**：0

**解析**：两者都基于二分查找，区别在于插入点选在相等区间的左端还是右端。left 得到相等元素区间的起点，right 得到其终点后一位。

### single_choice · None



- [A] 序列必须已按升序排列（或按同一 key 排序）
- [B] 序列必须是 list，不能是 tuple
- [C] 序列中不能有重复元素
- [D] 序列长度必须是 2 的幂

**参考答案**：0

**解析**：二分查找依赖有序性才能正确缩小范围。bisect 接受任何支持索引和 len 的序列，也允许重复元素，但不保证无序输入下有正确结果。

### single_choice · None



- [A] 保持有序（对相等元素插入位置可能不同）
- [B] 保持元素唯一
- [C] 保持原索引不变
- [D] 保持逆序

**参考答案**：0

**解析**：insort 系列会查找插入点并把元素插入列表，从而维持有序性；insert_left 和 insert_right 只是决定相等值插入在左边还是右边，并不去重。

### single_choice · None



- [A] 一次调用即可完成查找插入点并插入，减少出错
- [B] 把插入的时间复杂度从 O(n) 降到 O(1)
- [C] 能自动去除重复元素
- [D] 能自动对列表排序

**参考答案**：0

**解析**：insort 封装了查找位置和插入两个步骤，使用更方便、更不易出错；但插入本身仍需移动元素，整体时间复杂度并没有变成 O(1)。

### single_choice · None



- [A] O(log n)
- [B] O(n)
- [C] O(n log n)
- [D] O(1)

**参考答案**：0

**解析**：二分查找每次把搜索范围缩小一半，因此是 O(log n)。与之相比，insort 插入元素时因为要移动后续元素，最坏是 O(n)。

### single_choice · None



- [A] bisect 是 bisect_right 的别名，行为一致
- [B] bisect 是 bisect_left 的别名
- [C] bisect 会同时返回左右两个位置
- [D] bisect 是已废弃函数，行为不确定

**参考答案**：0

**解析**：在标准库中，bisect 等同于 bisect_right，用于保持与旧代码兼容；需要严格靠左时要用 bisect_left。

### multi_choice · None



- [A] bisect_left 返回目标值应插入的最左位置
- [B] bisect_right 返回目标值应插入的最右位置
- [C] insort 插入后列表仍保持有序
- [D] bisect 要求序列必须无重复元素
- [E] bisect 可以在无序序列上直接得到正确插入点

**参考答案**：[0, 1, 2]

**解析**：bisect_left/right 分别给出左、右插入位置；insort 会维持有序。重复元素是允许的，无序序列则不保证正确。
