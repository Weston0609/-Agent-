# s2u2l1 Python 迭代协议（Iterator Protocol） / 迭代器与 next()：Python 数据流的引擎

> 来源 `content/lessons/s2u2l1.json`

## py.iter.protocol

# Python 迭代协议（Iterator Protocol）

> **一句话直觉**：迭代协议是 Python `for` 循环背后的“契约”——只要对象按约定提供 `__iter__` 和 `__next__`，Python 就能自动把它“遍历”出来，无需继承任何特殊基类。

本讲属于课程 `s2u2l1`，是起点知识点。学完之后你将能：读懂 `for x in obj` 到底在做什么、自己写一个可迭代对象、理解生成器与迭代器之间的关系、并知道在工程中如何用 `iter()`/`next()`/`StopIteration` 写出健壮的代码。

---

## 1. 从 `for` 循环说起：迭代协议（Iteration Protocol）是什么

Python 的 `for` 并不认识你的类，它只认两个“魔术方法”（magic method / dunder method）：

- `__iter__`：返回一个**迭代器**（iterator）。
- `__next__`：迭代器每调用一次，返回下一个元素；没有元素时抛 `StopIteration`。

**结论 1**：`for x in obj` 等价于先 `it = iter(obj)`，再反复 `next(it)`，直到捕获 `StopIteration`。

```python
# 手动模拟 for 循环的内部机制
nums = [10, 20]
it = iter(nums)          # 调用 nums.__iter__()
print(next(it))          # 10
print(next(it))          # 20
try:
    next(it)             # 没有更多元素了
except StopIteration:    # 迭代协议用这个异常表示“结束”
    print("迭代结束")
```

---

## 2. 可迭代对象（Iterable） vs 迭代器（Iterator）

- **可迭代对象**：实现了 `__iter__`，可以被 `iter()` 转换。列表、字符串、字典都是。
- **迭代器**：同时实现了 `__iter__` 和 `__next__`。它的 `__iter__` 通常 `return self`。

**结论 2**：迭代器一定是可迭代对象，但可迭代对象不一定是迭代器。

```python
nums = [1, 2, 3]
print(hasattr(nums, "__iter__"))    # True，可迭代
print(hasattr(nums, "__next__"))    # False，列表本身不是迭代器

it = iter(nums)
print(hasattr(it, "__iter__"))      # True
print(hasattr(it, "__next__"))      # True，真迭代器
print(iter(it) is it)               # True：迭代器的 __iter__ 返回自身
```

---

## 3. 亲手实现一个迭代器

下面写一个“倒数计数器”，从 `n` 迭代到 `1`。

```python
class Countdown:
    """一个从 n 倒数到 1 的迭代器。"""
    def __init__(self, n):
        self.current = n

    def __iter__(self):          # 迭代器协议要求：返回自身
        return self

    def __next__(self):          # 返回下一个值，或抛 StopIteration
        if self.current <= 0:
            raise StopIteration  # 告诉 for：结束了
        value = self.current
        self.current -= 1
        return value

for x in Countdown(3):
    print(x)                     # 3, 2, 1
```

**结论 3**：`StopIteration` 不是错误，而是“正常终止信号”。`for` 会静默吞掉它。

---

## 4. 惰性求值（lazy evaluation）与内存优势

迭代器是**惰性**的：下一个元素只在被请求时才计算。这对处理大文件、无限序列很关键。

```python
# 生成器（generator）是写迭代器最省事的方式
# 函数里出现 yield 就自动实现了 __iter__ 和 __next__
def fib():
    a, b = 0, 1
    while True:                  # 无限序列！
        yield a
        a, b = b, a + b

it = fib()
for _ in range(6):
    print(next(it))              # 0 1 1 2 3 5
# 只计算用到的部分，不会撑爆内存
```

**结论 4**：能用生成器表达“逐次生成”的逻辑时，优先使用它——代码短，内存省。

---

## 5. 工程视角：`iter()` 的三种用法

`iter()` 除了常规调用外，还有一种“哨兵模式”（sentinel form）：`iter(callable, sentinel)`，一直调用 `callable` 直到返回等于 `sentinel` 的值。

```python
import random

# 逐行读文件（经典用法，避免 .readlines() 一次性加载）
with open("demo.txt", "w") as f:
    f.write("a\nb\nc\n")
with open("demo.txt") as f:
    for line in f:               # 文件对象本身就是迭代器
        print(line.strip())

# 哨兵模式：不断取值直到命中停止条件
it = iter(lambda: random.randint(1, 6), 6)
print(list(it))                 # 随机数序列，遇到 6 停止
```

**结论 5**：`iter(obj)` 把可迭代对象升级为迭代器；`iter(callable, sentinel)` 可以把你手写的“取一次”逻辑变成一个迭代器——这是工程里处理流式输入、传感器采样、网络响应时非常实用的 idioms。

---

## 小结表

| 概念 | 关键方法 | 生命周期 | 典型例子 |
|------|----------|----------|----------|
| 可迭代对象 Iterable | `__iter__` | 可被多次遍历 | list、str、dict |
| 迭代器 Iterator | `__iter__` + `__next__` | 一次性、有状态 | `iter([1,2])`、生成器 |
| 生成器 Generator | 含 `yield` 的函数 | 惰性 | `fib()` |

记住一句话：**`for` 只跟协议打交道，不跟类型打交道**。任何实现了协议的对象都能被 `for`、`sum`、`list()`、解构赋值等消费。

```python
"""
演示 Python 迭代协议：手写一个可迭代对象 + 生成器 + iter 哨兵模式。
运行：python demo.py
"""

class NumberBox:
    """可迭代对象：只实现 __iter__，返回一个独立的迭代器。
    这样即使多次 for 循环也不会互相干扰。"""
    def __init__(self, *items):
        self._items = list(items)

    def __iter__(self):
        return NumberBoxIterator(self._items)


class NumberBoxIterator:
    """真正的迭代器：实现 __iter__ 和 __next__。"""
    def __init__(self, items):
        self._items = items
        self._index = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self._index >= len(self._items):
            raise StopIteration
        value = self._items[self._index]
        self._index += 1
        return value


# 1) 常规迭代
box = NumberBox(10, 20, 30)
for n in box:
    print("for:", n)

# 2) 可重复迭代：证明 NumberBox 是“可迭代”而不是“迭代器”本身
print("two passes:", list(box), list(box))

# 3) 手动用 iter / next
it = iter(box)
print("next:", next(it), next(it))

# 4) 生成器版本：等价但更短
def evens(limit):
    for i in range(0, limit, 2):
        yield i

print("generator:", list(evens(10)))

# 5) iter(callable, sentinel) 哨兵模式
import random
random.seed(0)
get_dice = lambda: random.randint(1, 6)
stream = iter(get_dice, 4)      # 一直掷骰子，直到出现 4 停止
print("dice until 4:", list(stream))
```

## py.iter.iter_next

# 迭代器与 next()：Python 数据流的引擎

## 一句话直觉

学它是因为：Python 的 for 循环、生成器、文件读取、深度学习中的数据加载，**底层都靠迭代器（iterator）和 next() 驱动**——理解它们，你才能写出真正高效的流水线代码。

---

## 1. 什么是可迭代对象与迭代器？

在 Python 中，**可迭代对象（iterable）** 是任何能交给 `for` 循环的东西，比如 `list`、`str`、`dict`、文件对象。
**迭代器（iterator）** 是真正“记住当前走到哪”的对象——它内部保存状态，每次调用 `next()` 就吐出下一个元素。

关键规则：
- 可迭代对象需要实现 `__iter__()`，返回一个迭代器。
- 迭代器需要实现 `__next__()`，返回下一个元素；没有元素时抛出 `StopIteration`。

```python
# 列表是可迭代对象，但本身不是迭代器
nums = [10, 20, 30]
print(hasattr(nums, '__iter__'))   # True
print(hasattr(nums, '__next__'))   # False

# iter() 把可迭代对象变成迭代器
it = iter(nums)
print(hasattr(it, '__next__'))     # True
```

---

## 2. next()：手动推进一步

`next(iterator)` 是驱动迭代器的核心函数：每调用一次，取下一个值；取完后再调用，会抛出 `StopIteration` 异常。

`next(iterator, default)` 可以给一个默认值，取完时不抛异常而是返回默认值。

```python
it = iter([1, 2, 3])
print(next(it))   # 1
print(next(it))   # 2
print(next(it))   # 3
print(next(it, 'END'))  # END —— 用默认值避免异常
```

---

## 3. for 循环背后的秘密

`for x in obj:` 的等价逻辑是：先 `iter(obj)` 拿到迭代器，然后不断 `next()`，直到 `StopIteration` 结束。

理解这一点，你就明白为什么：
- 迭代器只能遍历一次（状态被消耗了）。
- 生成器函数天然就是迭代器生产者。

```python
# 手动模拟 for 循环
it = iter(['a', 'b', 'c'])
while True:
    try:
        val = next(it)
        print(val)
    except StopIteration:
        break
```

---

## 4. 生成器：用 yield 写迭代器

写一个类去实现 `__iter__` / `__next__` 很啰嗦。**生成器（generator）** 用 `yield` 一个关键字就搞定——函数一执行到 `yield` 就“暂停”，下次 `next()` 从暂停处继续。

```python
def countdown(n):
    while n > 0:
        yield n   # 暂停，把 n 交出去
        n -= 1

for x in countdown(3):
    print(x)   # 3 2 1

g = countdown(2)
print(next(g))  # 2
print(next(g))  # 1
```

---

## 5. 工程级用法：惰性流水线

在机器学习 / 数据处理中，迭代器让你**不用一次性把整个数据集加载到内存**。例如逐行读一个大文件、分批（batch）喂给模型，都是迭代器思想。

```python
# 只读第一行，不把整个文件读进内存
with open('big.txt') as f:
    it = iter(f)
    first_line = next(it, None)
    print(first_line)

# 自定义一个批迭代器（batch iterator）
def batches(data, size):
    batch = []
    for x in data:
        batch.append(x)
        if len(batch) == size:
            yield batch
            batch = []
    if batch:            # 最后不足一批也要吐出来
        yield batch

for b in batches(range(7), 3):
    print(b)   # [0,1,2] [3,4,5] [6]
```

这就是 PyTorch `DataLoader` 的简化思想：**惰性、按需、可组合**。

---

## 6. 小结

- 可迭代对象 → `iter()` → 迭代器 → `next()` → 值 / `StopIteration`。
- `for` 循环就是 `next()` + `try/except StopIteration` 的语法糖。
- 生成器用 `yield` 以最简方式写出迭代器。
- 工程上用迭代器做惰性、流式、低内存的数据处理。

```python
# 用生成器实现一个“斐波那契迭代器”，并用 next() 手动推进

def fibonacci(limit):
    """生成不超过 limit 的斐波那契数列。"""
    a, b = 0, 1
    while a <= limit:
        yield a          # 交出一个值，暂停在这里
        a, b = b, a + b

# 方式一：for 循环（内部自动调用 iter() 和 next()）
print("for 循环:", list(fibonacci(50)))

# 方式二：手动 next()，感受迭代器的状态
it = iter(fibonacci(50))
print(next(it))          # 0
print(next(it))          # 1
print(next(it))          # 1

# 方式三：带默认值，避免 StopIteration 异常
print(next(it, "NO_MORE"))

# 演示一个已耗尽的迭代器
empty_it = iter([])
print(next(empty_it, "EMPTY"))   # EMPTY
```


---

## 本课题目

### single_choice · None



- [A] __next__
- [B] __iter__
- [C] __getitem__
- [D] __call__

**参考答案**：0

**解析**：迭代器协议要求对象实现 __iter__（返回迭代器自身）和 __next__（返回下一个值或抛出 StopIteration）。__iter__ 已给出，缺少的是 __next__。__getitem__ 可让对象支持下标遍历，但本类已按迭代器协议实现；__call__ 与迭代无关。

### single_choice · None



- [A] 一个列表 [1, 2, 3]
- [B] 一个字符串 "abc"
- [C] 一个实现了 __iter__ 且返回 self、并实现了 __next__ 的对象
- [D] 一个只实现了 __getitem__ 的对象

**参考答案**：2

**解析**：可迭代对象只需实现 __iter__；迭代器需要实现 __iter__（返回自身）和 __next__。列表、字符串是可迭代对象但不是迭代器；只实现 __getitem__ 的对象可通过旧式序列协议被遍历，但也不是迭代器。

### single_choice · None



- [A] 生成器函数调用后返回一个生成器对象，它自动实现了迭代器协议
- [B] 生成器只是一种语法糖，不能被 next() 调用
- [C] 生成器必须手动实现 __next__ 才能用 for 遍历
- [D] 生成器不是可迭代对象

**参考答案**：0

**解析**：含 yield 的函数是生成器函数，调用它得到生成器对象；生成器自动实现了 __iter__ 和 __next__，因此既是可迭代对象又是迭代器，可以直接用 next() 和 for 遍历，无需手写这两个方法。

### single_choice · None



- [A] [1, 2]
  []
- [B] [1, 2]
  [1, 2]
- [C] 报错，因为 __iter__ 应返回 self
- [D] []
  [1, 2]

**参考答案**：1

**解析**：这里 __iter__ 每次都返回底层列表的一个新迭代器，因此每次调用 list(c) 都能从头遍历得到 [1, 2]。这与迭代器自身的 __iter__ 必须返回 self 不同——可迭代对象的 __iter__ 可以每次返回新的迭代器。

### single_choice · None



- [A] 没有定义 __iter__，对象不是可迭代对象，for 会抛 TypeError
- [B] pop() 方法不存在
- [C] for 循环不能遍历自定义类
- [D] 缺少 __init__

**参考答案**：0

**解析**：只有 __next__ 而没有 __iter__，对象不满足可迭代对象协议，iter() 无法调用它，for 循环会抛 TypeError: not iterable。需要补充 __iter__（返回迭代器，例如 self）。

### single_choice · None



- [A] hasattr(obj, '__iter__')
- [B] hasattr(obj, '__next__') and hasattr(obj, '__iter__')
- [C] isinstance(obj, list)
- [D] len(obj) > 0

**参考答案**：1

**解析**：迭代器需同时具备 __iter__ 和 __next__。仅检查 __iter__ 只能判断可迭代；isinstance(obj, list) 只针对列表；len(obj) 与是否为迭代器无关。

### single_choice · None



- [A] 1
  end
- [B] 1
  报错 StopIteration
- [C] 1
  None
- [D] 报错，因为第二次调用不合法

**参考答案**：0

**解析**：next(iterator, default) 在迭代器耗尽时返回给定默认值而不是抛 StopIteration。第一次 next 取到 1，第二次已耗尽，返回 'end'。

### single_choice · None



- [A] 可迭代对象一定实现了 __next__
- [B] 迭代器一定实现了 __getitem__
- [C] 可迭代对象的 __iter__ 通常每次返回一个新的迭代器，而迭代器的 __iter__ 返回自身
- [D] 两者完全相同，没有区别

**参考答案**：2

**解析**：可迭代对象只需能产生迭代器，其 __iter__ 通常每次返回新迭代器，因而可以被多次遍历；迭代器既实现 __iter__ 又实现 __next__，其 __iter__ 返回自身，遍历一次后耗尽。

### single_choice · None



- [A] 在 __iter__ 中返回 iter(self.data)，每次调用得到新迭代器
- [B] 在 __iter__ 中返回 self，并让类实现 __next__ 从列表中逐个弹出元素
- [C] 在 __iter__ 中返回 self.data 本身（列表）
- [D] 在 __iter__ 中什么都不返回

**参考答案**：0

**解析**：在 __iter__ 中返回 iter(self.data) 会每次产生新的迭代器，因此对象可多次从头遍历。返回 self 并在 __next__ 中弹出元素会消耗列表，第二次遍历就为空。返回列表本身不满足迭代器要求（__iter__ 应返回迭代器）。不返回则得到 None，for 会报错。

### single_choice · None



- [A] [1, 2, 3]
- [B] [3]
- [C] []
- [D] [2, 3]

**参考答案**：1

**解析**：for 循环在 x == 2 时 break，此时迭代器已消耗 1 和 2，剩余元素 3。因此 list(it) 得到 [3]。迭代器状态在 break 后保留。

### single_choice · None



- [A] 必须返回一个列表
- [B] 必须返回一个迭代器对象
- [C] 可以返回任意非 None 值
- [D] 必须返回整数下标

**参考答案**：1

**解析**：可迭代对象的 __iter__ 必须返回一个迭代器对象，供 for/iter() 使用。返回列表（本身可迭代但非迭代器）、返回任意值或整数都不符合迭代器协议。

### single_choice · None



- [A] while True:
      x = next(it)
      print(x)
- [B] while True:
      try:
          x = next(it)
      except StopIteration:
          break
      print(x)
- [C] for _ in range(len(it)):
      print(next(it))
- [D] print(list(it))

**参考答案**：1

**解析**：for 循环的底层是：获取迭代器，反复 next()，捕获 StopIteration 后退出。选项 A 缺少异常处理会报错；选项 C 中迭代器没有 len；选项 D 虽然能输出元素但不打印每个值，语义不同。

### single_choice · None



- [A] 10
  20
  [10, 20, 30]
- [B] 10
  20
  [30]
- [C] 10
  20
  []
- [D] 报错，因为迭代器不能两次使用

**参考答案**：1

**解析**：迭代器是「一次性」的，每次 next 消耗一个元素。前两次 next 取走 10 和 20，list(it) 只能取到剩余元素 30。迭代器耗尽后不会重置，但也不会报错。

### single_choice · None



- [A] [1, 2, 3]
  [1, 2, 3]
- [B] [1, 2, 3]
  []
- [C] []
  []
- [D] 报错，因为每次创建新对象

**参考答案**：0

**解析**：每处 list(R()) 都创建了一个全新的 R 实例，其 i 从 0 开始，所以两次都得到 [1, 2, 3]。注意与复用同一个迭代器对象不同。

### single_choice · None



- [A] for 循环会先调用该对象的 __iter__ 获得迭代器，再反复调用 next
- [B] for 循环直接调用对象的 __next__ 方法
- [C] for 循环要求对象必须是列表或元组
- [D] for 循环结束后迭代器会自动重置

**参考答案**：0

**解析**：for 循环的标准流程是：对可迭代对象调用 iter() 得到迭代器，然后反复调用 next() 直到捕获 StopIteration。对象本身不必是 __next__ 实现者；不必是列表/元组；迭代器耗尽后不会自动重置。

### single_choice · None



- [A] 1
  1
- [B] 1
  报错 StopIteration
- [C] 1
  1 然后无限重复
- [D] 报错，因为没有定义 __init__

**参考答案**：0

**解析**：__next__ 每次直接返回 1，从不抛出 StopIteration，因此每次 next 都返回 1。这个迭代器是无限的，不会报错（除非用 for 循环会一直运行）。

### single_choice · None



- [A] 抛出 TypeError，因为缺少 __iter__
- [B] Python 会从下标 0 开始依次调用 __getitem__，直到 IndexError
- [C] 只遍历一次后停止
- [D] 没有任何输出，直接跳过

**参考答案**：1

**解析**：旧式序列协议允许对象只实现 __getitem__ 就能被迭代：Python 从索引 0 开始调用 __getitem__，遇到 IndexError 停止。这是 __iter__ 出现之前的机制，仍被支持。

### single_choice · None



- [A] True
  True
- [B] False
  True
- [C] True
  False
- [D] False
  False

**参考答案**：1

**解析**：列表是可迭代对象但不是迭代器，没有 __next__；iter(lst) 返回的 list_iterator 是迭代器，拥有 __next__。因此分别是 False 和 True。

### single_choice · None



- [A] 每次遍历前重新调用 iter() 获取新的迭代器
- [B] 保存了迭代器对象并在多个循环中重复使用同一个迭代器
- [C] 使用 list() 从头构建新列表
- [D] 在循环外先对可迭代对象调用 len()

**参考答案**：1

**解析**：迭代器是有状态的、一次性的。如果保存同一个迭代器对象并在多个循环中复用，前面的循环已经消耗了部分元素，后续循环就只能看到剩余元素。每次调用 iter() 会得到新的迭代器，不会出现该问题。

### single_choice · None



- [A] 一个新的列表副本
- [B] 迭代器对象自身（return self）
- [C] None
- [D] 被迭代对象的长度

**参考答案**：1

**解析**：迭代器协议要求迭代器的 __iter__ 返回迭代器自身，这样 for 循环中 iter(it) 返回的就是同一个可继续消费的迭代器。返回列表副本、None 或长度都不符合协议。

### single_choice · None



- [A] next(it) 第一次
- [B] next(it) 第二次
- [C] next(it) 第三次
- [D] iter(it)

**参考答案**：2

**解析**："ab" 只有两个字符，前两次 next 返回 'a'、'b'，第三次已耗尽，抛出 StopIteration。iter(it) 对迭代器调用会返回自身（迭代器本身也是可迭代对象），不抛异常。

### single_choice · None



- [A] 它接收一个可迭代对象作为参数，并返回该对象的第一个元素
- [B] 它无参数调用，每次返回下一个元素，元素耗尽时应抛出 StopIteration
- [C] __next__ 是一个类方法，需要显式传入 cls 参数
- [D] 它必须返回一个列表，否则会被解释器认为迭代结束

**参考答案**：1

**解析**：迭代器协议的 __next__ 方法不接受额外参数（除 self），每次调用返回下一个元素；当没有更多元素时，必须抛出 StopIteration 来通知调用方迭代结束。选项 A 混淆了 iter() 与 next()；C 把实例方法说成类方法；D 错误地要求返回列表。

### single_choice · None



- [A] next(it) 返回迭代器 it 的下一个元素
- [B] next(it, default) 在迭代器耗尽时返回 default 而不抛异常
- [C] next(it) 在迭代器耗尽时会抛出 StopIteration
- [D] next(it, default) 在迭代器耗尽时会抛出 StopIteration 而不是返回 default

**参考答案**：3

**解析**：next(it, default) 提供默认值时，迭代器耗尽会返回 default 而非抛异常，这正是它的用途。A、B、C 都正确描述了 next() 的行为，只有 D 说反了。

### single_choice · None



- [A] for 循环直接在原对象上调用 __next__，不经过 iter()
- [B] for 循环先对对象调用 iter() 获得迭代器，然后反复调用其 __next__，直到捕获 StopIteration
- [C] for 循环每次循环都重新调用一次 iter() 以获得新的迭代器
- [D] for 循环通过索引下标访问元素，与迭代器协议无关

**参考答案**：1

**解析**：for 语句先调用 iter(对象) 得到迭代器（只调用一次），然后循环调用 next()，直到捕获 StopIteration 才结束。它不会每次循环重新 iter()，也不依赖索引。

### multi_choice · None



- [A] 迭代器必须实现 __next__ 方法
- [B] 迭代器的 __iter__ 方法通常返回它自身
- [C] 迭代器是有状态的，会记录当前遍历位置
- [D] 迭代器可以被多次完整遍历而无需重建
- [E] 所有可迭代对象都必须是迭代器

**参考答案**：[0, 1, 2]

**解析**：迭代器需要 __next__，其 __iter__ 一般返回自身，且内部保存状态以记录位置，A、B、C 正确。D 错误：迭代器是单向的，耗尽后不能自动重复遍历。E 错误：可迭代对象只需实现 __iter__ 产出迭代器，自身不必是迭代器。

### multi_choice · None



- [A] 已经取完所有元素后再次调用 next()
- [B] 对一个空的迭代器第一次调用 next()
- [C] 生成器函数内部执行到 return 后再次调用 next()
- [D] 调用 next(it, default) 且迭代器已耗尽
- [E] 对一个尚未开始遍历的迭代器调用 next()

**参考答案**：[0, 1, 2]

**解析**：A、B、C 都会在没有剩余元素时抛出 StopIteration。D 不会抛出，因为有 default 时会返回默认值。E 也不会抛出，尚未开始遍历的迭代器首次调用通常会返回第一个元素。

### multi_choice · None



- [A] next(it) 本质上是调用 it.__next__() 并返回其结果
- [B] 定义 __next__ 后，对象就能被 next() 直接使用
- [C] next(it, default) 会在捕获 StopIteration 后返回 default
- [D] next() 只接受迭代器，不接收其他任何对象

**参考答案**：[0, 1, 2]

**解析**：next(it) 内部就是调用 it 的 __next__；实现了 __next__ 的对象即可用 next() 调用；带默认值时 next 捕获 StopIteration 并返回 default，A、B、C 正确。D 不准确，因为 next() 只要求对象具备 __next__，并不局限于严格意义的迭代器名称，且它总要求该属性存在。

### multi_choice · None



- [A] iter([1, 2, 3]) 的返回值
- [B] [1, 2, 3] 这个列表本身
- [C] (x for x in range(3)) 这个生成器表达式的结果
- [D] range(3) 这个 range 对象

**参考答案**：[0, 2]

**解析**：iter([1,2,3]) 返回列表迭代器，生成器表达式产生生成器，二者都是迭代器，可用于 next()。列表是可迭代对象但不是迭代器；range 对象是可迭代对象，同样不是迭代器（需先 iter()）。

### fill_blank · None



**参考答案**：["default", "默认值", "传入的 default 值"]

**解析**：next() 的第二个参数是默认值，当迭代器耗尽时返回该默认值而不是抛出 StopIteration，常用于安全取值。

### fill_blank · None



**参考答案**：["StopIteration", "StopIteration 异常", "StopIteration 异常对象"]

**解析**：迭代器协议规定，__next__ 在元素耗尽时必须抛出 StopIteration，这样 for、next 等机制才能正确识别遍历结束。

### code_reading · None



**参考答案**：输出：1、2、3、done。for 循环遍历了迭代器 it 的全部元素，迭代结束后 it 已耗尽；随后 next(it, 'done') 因迭代器已耗尽而返回默认值 'done'，不抛异常。

**解析**：关键点在于 for 循环会耗尽同一个迭代器对象，循环结束后 it 处于耗尽状态，因此带默认值的 next() 返回默认值。这考察「for 耗尽迭代器」和「next 默认值」两个知识点的结合。

### code_reading · None



**参考答案**：第一次打印 [1, 2]，第二次打印 []。因为 Counter 的 __iter__ 返回自身，该对象同时是可迭代对象又是迭代器，其遍历状态保存在 self.i 上；第一次 list(c) 把内部计数耗尽后，第二次再遍历时 self.i 已等于 n，__next__ 立即抛出 StopIteration，因此第二次得到空列表。

**解析**：这考察「迭代器有状态且耗尽后不能自动重置」这一核心概念。__iter__ 返回自身导致同一对象的遍历状态被复用，这是常见的陷阱。

### scenario · None



**参考答案**：原因：__iter__ 返回的是缓存/共享的同一个迭代器（例如把迭代器保存在实例属性上并反复返回），迭代器是单向有状态的，第一次遍历耗尽后再返回同一个已耗尽的迭代器，导致第二次遍历为空。修复：每次调用 __iter__ 都返回一个全新的迭代器（例如 return iter(self._data) 或 return self._data[:] 的迭代），而不是复用同一个迭代器对象。

**解析**：考察对「迭代器有状态、可迭代对象应每次产生新迭代器」的工程理解。共享迭代器是常见 bug 来源，正确做法是每次 __iter__ 返回新的迭代器。

### single_choice · None



- [A] 10
  20
  end
- [B] 10
  20
  StopIteration
- [C] 10
  end
  end
- [D] 20
  end
  end

**参考答案**：0

**解析**：第一次 next(it) 返回 10；第二次 next(it, 'end') 返回 20（迭代器仍有元素，default 不生效）；第三次元素已耗尽，返回默认值 'end'。所以输出为 10、20、end。

### single_choice · None



- [A] 实现 __next__ 方法即可
- [B] 实现 __iter__ 方法，并且它返回一个迭代器对象
- [C] 实现 __len__ 方法，且返回长度大于 0
- [D] 实现 __getitem__ 方法并返回值，但参数必须是整数索引

**参考答案**：1

**解析**：可迭代对象需要实现 __iter__，其返回值是一个迭代器（即实现了 __next__ 的对象）。仅实现 __next__ 得到的是迭代器而非可迭代对象；__len__ 不足以支持迭代；__getitem__ 虽可支持老式序列迭代，但只要不是整数索引或中断方式不当就不是充分且标准的做法。

### single_choice · None



- [A] 列表是迭代器，因为它可以被遍历
- [B] 迭代器一定是可迭代对象，但可迭代对象不一定是迭代器
- [C] 可迭代对象一定是迭代器，但迭代器不一定是可迭代对象
- [D] 两者是完全等价的，只是叫法不同

**参考答案**：1

**解析**：迭代器实现了 __iter__（返回自身）和 __next__，因此它自身就是可迭代对象；而像 list 这样的可迭代对象能通过 iter() 产出迭代器，但它本身并不实现 __next__，所以不是迭代器。故 B 正确。

### single_choice · None



- [A] 自动从头开始重新迭代
- [B] 返回 None
- [C] 抛出 StopIteration 异常
- [D] 抛出 RuntimeError 异常

**参考答案**：2

**解析**：迭代器是有状态的单向对象，一旦耗尽，后续调用 __next__ 会持续抛出 StopIteration。它不会自动重置，也不会返回 None。要重新遍历需重新获取迭代器。

### single_choice · None



- [A] 返回 obj 自身作为迭代器
- [B] 抛出 TypeError
- [C] 返回 None
- [D] 返回一个空的迭代器

**参考答案**：1

**解析**：当 iter() 收到的对象既没有 __iter__ 也不支持序列协议（__getitem__）时，会抛出 TypeError（'object is not iterable'）。不会返回自身、None 或空迭代器。

### single_choice · None



- [A] 1
  2
  X
- [B] 1
  2
  StopIteration
- [C] 1
  X
  X
- [D] 1
  1
  2

**参考答案**：0

**解析**：生成器是迭代器。前两次 next 依次得到 1 和 2；生成器此时已耗尽，第三次带默认值调用返回 'X'，所以输出为 1、2、X。

### single_choice · None



- [A] 迭代器耗尽后，其内部会保留一个可克隆的副本供再次遍历
- [B] 一旦迭代器耗尽，它始终保持耗尽状态，除非重新创建或重置
- [C] 对已耗尽的迭代器调用 next 会返回最后一个元素
- [D] 已耗尽的迭代器在被 for 循环遍历时会自动恢复

**参考答案**：1

**解析**：标准迭代器没有自动重置机制，耗尽后一直保持耗尽状态。除非重新调用 iter() 获取新迭代器或像某些含 reset 语义的对象主动重置，否则不会恢复。A、C、D 均为常见误解。

### single_choice · None



- [A] next(iterator)
- [B] next(iterator, 5, 10)
- [C] next()
- [D] next(iterator, start=0)

**参考答案**：0

**解析**：next() 接受一个迭代器以及可选的 default（第二个位置参数），不接受关键字参数 start，也不允许三个参数或无参调用。因此只有 next(iterator) 是正确形式。
