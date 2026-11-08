# s2u2l2 迭代器与生成器（Iterator & Generator） / 让函数拥有“暂停键”的魔法

> 来源 `content/lessons/s2u2l2.json`

## py.iter.generator

# 迭代器与生成器（Iterator & Generator）

> **一句话直觉**：想遍历一百万个数据又不想把内存撑爆？想让“产生数据”的代码和“消费数据”的代码解耦？迭代器（Iterator）和生成器（Generator）就是 Python 给出的答案——它们让数据“按需产出”，一次只算一个。

---

## 1. 为什么需要迭代器？（Iterable 和 Iterator）

在 Python 里，`for x in obj:` 之所以能工作，是因为 `obj` 是**可迭代对象**（Iterable）。它承诺自己能被遍历。

- **可迭代对象（Iterable）**：实现了 `__iter__()`，返回一个迭代器。列表、元组、字典、字符串、文件都是。
- **迭代器（Iterator）**：同时实现了 `__iter__()` 和 `__next__()`。每次调用 `__next__()` 返回下一个元素；耗尽后抛出 `StopIteration` 异常。

关键区别：可迭代对象可以反复遍历（每次 `iter()` 拿新迭代器）；迭代器只能**遍历一次**，用完就“空”了。

```python
# 演示：可迭代对象 vs 迭代器
nums = [1, 2, 3]          # 列表：可迭代
it = iter(nums)            # 拿到一个迭代器

print(next(it))  # 1
print(next(it))  # 2
print(next(it))  # 3
# print(next(it))  # 再调用会抛 StopIteration

# 对同一个迭代器再次 for 循环，会发现它已经空了
print(list(it))            # [] （已被耗尽）
print(list(nums))          # [1, 2, 3] （原列表还能再遍历）
```

> **工程意义**：所有 `for` 循环、`sum()`、`list()`、`max()`、`zip()`、`enumerate()` 底层都在用这套协议。理解协议 = 理解 Python 数据流的骨架。

---

## 2. 手写一个迭代器：理解 `__iter__` 和 `__next__`

自定义迭代器最直观的方式是写一个类。下面实现一个倒计时迭代器：

```python
class Countdown:
    """从 n 倒数到 1 的迭代器"""
    def __init__(self, n):
        self.n = n

    def __iter__(self):
        return self          # 迭代器返回自身

    def __next__(self):
        if self.n <= 0:
            raise StopIteration  # 明确的结束信号
        self.n -= 1
        return self.n + 1

for x in Countdown(3):
    print(x)   # 3, 2, 1
```

两个要点：

1. `__iter__` 必须返回一个迭代器（通常就是 `self`）。
2. `__next__` 用 `raise StopIteration` 表示结束，而不是返回 `None`——这是 Python 协议硬性规定。

写类能让我们看清协议，但每次都这么写太啰嗦。于是有了生成器。

---

## 3. 生成器（Generator）：用 `yield` 写迭代器

**生成器（Generator）** 是一种用函数语法写出来的迭代器：函数里出现 `yield`，调用它就不再执行函数体，而是返回一个生成器对象。

```python
def countdown(n):
    while n > 0:
        yield n     # 交出值并暂停，下次 next() 从这里继续
        n -= 1

for x in countdown(3):
    print(x)
```

执行流程：

- 调用 `countdown(3)` **不会**执行函数体，只创建生成器对象。
- 每次 `next()` 执行到 `yield n` 就“暂停”，把 `n` 交给调用者，并保存全部局部状态（比如 `n` 的值）。
- 下一次 `next()` 从暂停处恢复，直到再次 `yield` 或函数返回。函数返回时自动抛 `StopIteration`。

**这就是惰性（lazy）计算**：`countdown(10**9)` 几乎不占内存，因为它一次只产生一个数。

```python
# 生成器表达式：把列表推导式的 [] 换成 ()
sq = (i * i for i in range(5))
print(list(sq))   # [0, 1, 4, 9, 16]

# 大文件惰性读取（比 readlines 更省内存）
def read_lines(path):
    with open(path, encoding='utf-8') as f:
        for line in f:
            yield line.rstrip('\n')
```

> **类型标注**：生成器函数的返回类型是 `Iterator[T]`（来自 `collections.abc`），形如 `def countdown(n: int) -> Iterator[int]: ...`。`typing.Iterator`/`typing.Generator` 自 Python 3.9 起已成为 `collections.abc` 中同名类的**弃用别名**，新代码应直接从 `collections.abc` 导入。

---

## 4. `yield` 的进阶用法：`send()`、`throw()` 与双向通信

生成器不只是“产出”，还能“接收”。`yield` 是一个表达式，可以让调用者把值送回生成器内部。

```python
def echo():
    """把收到的值原样返回；收到 None 就结束"""
    while True:
        received = yield              # yield 有返回值
        if received is None:
            return
        yield received.upper()

g = echo()
next(g)                # 先推进到第一个 yield（预热）
print(g.send('hi'))    # 'HI'
print(g.send('bye'))   # 'BYE'
```

要点：

- `send(x)` 把 `x` 作为上一个 `yield` 表达式的值传回去，并推进到下一个 `yield`。
- 第一次必须用 `next(g)` 或 `g.send(None)` 预热，否则报 `TypeError`。
- 生成器还有 `throw()` 线程异常进入体内，`close()` 抛 `GeneratorExit` 终止它，`return` 值则封装在 `StopIteration.value` 里。

这在协程（coroutine）、管道（pipeline）场景中非常有用：多个生成器可以串成数据处理流水线。

---

## 5. 工程实践：惰性管道与内存对比

下面用生成器搭一条“读入 → 过滤 → 变换 → 汇总”的惰性管道：

```python
from collections.abc import Iterator

def numbers(n: int) -> Iterator[int]:
    for i in range(n):
        yield i

def only_even(it: Iterator[int]) -> Iterator[int]:
    for x in it:
        if x % 2 == 0:
            yield x

def squared(it: Iterator[int]) -> Iterator[int]:
    for x in it:
        yield x * x

pipeline = squared(only_even(numbers(10)))
print(sum(pipeline))   # 0+4+16+36+64 = 120
```

- **惰性**：一次只处理一个元素，内存和时间都按需分摊。
- **可组合**：每个生成器职责单一，通过参数拼接。
- **易测试**：每个函数都能单独验证。

如果换成一亿条记录，`list()` 版本会先吃光内存，生成器版本则坚如磐石。这就是“工程级”和“玩具级”的分界线。

---

## 动手练习

**任务**：写一个生成器函数 `take(n, it)`，从任意迭代器 `it` 中**惰性**取出前 `n` 个元素。要求：当 `it` 元素不足 `n` 时，能优雅返回、不报错；并用它配合无限生成器验证。

```python
from collections.abc import Iterator
from itertools import count   # 无限迭代器

def take(n: int, it: Iterator) -> Iterator:
    # TODO: 你的实现
    ...

# 期望：打印 0..4
for x in take(5, count()):
    print(x)

# 期望：只打印 0..2（超出部分自动停止）
print(list(take(10, iter([0, 1, 2]))))
```

**进阶（可选）**：把 `take` 改成支持负数 `n`（直接返回空生成器）；再写一个 `chunk(it, size)`，把迭代器按固定长度切成若干个 `tuple`。

```python
"""py.iter.generator 完整示例：惰性计数 + 管道组合"""
from collections.abc import Iterator
from itertools import count


def numbers(n: int) -> Iterator[int]:
    """生成 0..n-1"""
    for i in range(n):
        yield i


def only_even(it: Iterator[int]) -> Iterator[int]:
    """过滤偶数"""
    for x in it:
        if x % 2 == 0:
            yield x


def squared(it: Iterator[int]) -> Iterator[int]:
    """对每个元素求平方"""
    for x in it:
        yield x * x


if __name__ == '__main__':
    # 惰性管道：numbers -> only_even -> squared
    pipeline = squared(only_even(numbers(10)))
    print('sum =', sum(pipeline))          # sum = 120

    # 生成器表达式 + 无限迭代器切片
    first_5_squares = (i * i for i in count())
    print([next(first_5_squares) for _ in range(5)])   # [0, 1, 4, 9, 16]

    # 与 next() 的默认值配合，安全消费
    it = iter([1, 2])
    print(next(it, None), next(it, None), next(it, None))  # 1 2 None
```

## py.iter.yield

# py.iter.yield：让函数拥有“暂停键”的魔法

## 一句话直觉

`yield` 让你的函数可以“停在中途、记住现场、下次接着跑”，从而以极低的内存代价逐一产出数据流——这是 Python 迭代（iteration）与生成器（generator）体系的地基。

---

## 1. 从 for 循环说起：什么是可迭代对象？

在 Python 里，能被 `for` 循环遍历的东西都叫 **可迭代对象（iterable）**。列表、字符串、字典、文件句柄都是。它们的共同点是：实现了 `__iter__()` 方法，返回一个 **迭代器（iterator）**。

迭代器只有一个职责：每次调用 `__next__()`，吐出下一个元素；吐完了就抛出 `StopIteration`。

```python
# 一个手动实现的迭代器：从 0 数到 2
class CountToThree:
    def __init__(self):
        self.n = 0
    def __iter__(self):
        return self
    def __next__(self):
        if self.n >= 3:
            raise StopIteration   # 关键：告诉 for 循环“没数据了”
        self.n += 1
        return self.n - 1

for x in CountToThree():
    print(x)   # 输出 0 1 2
```

关键结论：**所有 `for` 循环的底层，都是 `__iter__` + `__next__` + `StopIteration` 这套协议。**

---

## 2. yield 登场：生成器函数

手写迭代器太啰嗦。只要函数体里出现 `yield`，这个函数就自动变成 **生成器函数（generator function）**——调用它不会立刻执行，而是返回一个 **生成器（generator）** 对象，该对象天生就是迭代器。

```python
def count_to_three():
    yield 0
    yield 1
    yield 2

g = count_to_three()
print(next(g))   # 0
print(next(g))   # 1
print(next(g))   # 2
# next(g) 再来一次会抛 StopIteration

# 也可以直接用 for 消费
for x in count_to_three():
    print(x)
```

关键结论：**`yield` 不是“返回值”，而是“打个暂停点并把一个值送出去”。** 函数的状态（局部变量、执行位置）都被冻结保存。

---

## 3. 惰性求值：为什么它省内存？

普通函数用 list 收集一万条数据，就要在内存里放一万条；生成器只保留“当前这一条”和函数的执行现场。这叫 **惰性求值（lazy evaluation）**。

```python
import sys

def make_list(n):
    return [i * i for i in range(n)]

def make_gen(n):
    for i in range(n):
        yield i * i

lst = make_list(1_000_000)
gen = make_gen(1_000_000)
print(sys.getsizeof(lst))   # 约 8 MB（每个 int 还要额外开销）
print(sys.getsizeof(gen))   # 约 200 字节，恒定
```

关键结论：**生成器以“时间换空间”——数据按需产生，而不是一次铺满。**

---

## 4. 无限序列 & 流水线：生成器的工程价值

因为惰性，生成器可以表示无穷序列——只要没人消费到无限远，程序就不会爆炸。

```python
def naturals():
    n = 0
    while True:
        yield n
        n += 1

# 取前 5 个即可
from itertools import islice
print(list(islice(naturals(), 5)))   # [0, 1, 2, 3, 4]
```

生成器还能像管道一样串联，每个阶段只处理一条数据，很适合读大文件、做 ETL、流式日志处理。

```python
def read_lines(path):
    with open(path) as f:
        for line in f:      # 文件句柄本身就是迭代器
            yield line.rstrip("\n")

def only_errors(lines):
    for line in lines:
        if "ERROR" in line:
            yield line

# 整条流水线不会把文件一次性载入内存
for line in only_errors(read_lines("app.log")):
    print(line)
```

关键结论：**生成器让“数据流”像 shell 管道一样可以组合，每个环节都惰性。**

---

## 5. yield 的双向能力：send / throw / close（进阶）

`yield` 其实是一个“表达式”，不仅仅输出值，还能接收调用方用 `send()` 送进来的值。这让生成器变成 **协程（coroutine）** 的雏形——也是后来 `async/await` 的思想源头。

```python
def accumulator():
    total = 0
    while True:
        x = yield total   # yield 返回 send 进来的值
        if x is None:
            break
        total += x

acc = accumulator()
next(acc)          # 启动生成器，返回 0
print(acc.send(10))  # 10
print(acc.send(5))   # 15
```

关键结论：**`yield` 是双向通道：往外送值、往里收值；这也解释了为什么 `async def` 里 `await` 与 `yield` 能共存。**

---

## 常见误区速览

- 以为调用生成器函数会立即执行：不会，只有第一次 `next()` 才启动。
- 重复遍历同一个生成器对象：第二次 `for` 会直接结束（它已耗尽）。
- `return x` 在生成器里不会作为值返回，而是作为 `StopIteration.value`。
- 生成器里忘了 `try/finally`：消费中途 break 时清理逻辑可能不执行。

```python
"""
py.iter.yield 综合示例：
用生成器构建一个惰性日志处理流水线，并演示 send 双向通信。
"""
from itertools import islice

# 1) 读取器：惰性逐行读（此处用字符串模拟文件内容）
def read_lines(text):
    for line in text.splitlines():
        yield line

# 2) 过滤器：只保留包含 ERROR 的行
def only_errors(lines):
    for line in lines:
        if "ERROR" in line:
            yield line

# 3) 转换器：给每条日志加上行号
def with_index(lines, start=1):
    for i, line in enumerate(lines, start):
        yield f"{i:03d}: {line}"

LOG = """INFO boot ok
ERROR disk full
WARN cpu high
ERROR network down
INFO shutdown
"""

pipeline = with_index(only_errors(read_lines(LOG)))
for out in pipeline:
    print(out)

# 4) 无限序列 + islice 只取前 5 个
def naturals():
    n = 0
    while True:
        yield n
        n += 1

print(list(islice(naturals(), 5)))

# 5) send 双向通信：生成器作为累加器
def accumulator():
    total = 0
    while True:
        x = yield total
        if x is None:
            break
        total += x

acc = accumulator()
next(acc)                  # 启动，返回初始 0
print(acc.send(10))        # 10
print(acc.send(5))         # 15
acc.close()                # 显式关闭
```


---

## 本课题目

### single_choice · None



- [A] created
  start
  middle
- [B] start
  middle
  created
- [C] created
  start
  middle
  2
- [D] start
  created
  middle

**参考答案**：0

**解析**：调用生成器函数只创建生成器对象，函数体不会执行，所以先打印 created；每次 next() 才推进到下一个 yield，分别在两次 next 时打印 start 和 middle。第三次输出中的 2 不会出现，因为没有再 next。

### single_choice · None



- [A] 生成器表达式会立即计算所有元素并保存在内存中
- [B] 列表推导式返回迭代器，只能遍历一次
- [C] 生成器表达式返回迭代器，按需产生元素
- [D] 两者完全等价，只是括号不同

**参考答案**：2

**解析**：生成器表达式返回生成器对象，是惰性迭代器；列表推导式立即构建完整列表，可重复遍历。A、B 分别把两者的特性弄反，D 忽略了内存模型和可重复遍历性的差异。

### single_choice · None



- [A] 生成器会一次性把所有数据装入内存，因此比列表省内存
- [B] 生成器按需产生数据，适合处理大数据流，但不支持随机索引访问
- [C] 生成器也是序列，支持 g[0] 这样的下标访问
- [D] 生成器可以像列表一样反复遍历

**参考答案**：1

**解析**：生成器惰性求值，适合流式处理大数据，但不是序列，不支持下标访问，也不能重复遍历。A、C、D 分别混淆了内存模型、序列协议和一次性特性。

### single_choice · None



- [A] [x for x in range(3)]
- [B] {x for x in range(3)}
- [C] (x for x in range(3))
- [D] tuple(x for x in range(3))

**参考答案**：2

**解析**：圆括号且不含额外函数调用的表达式是生成器表达式。方括号是列表推导式，花括号是集合推导式，tuple(...) 会消耗生成器并返回元组。

### single_choice · None



- [A] [1]
- [B] [1, 2]
- [C] [2]
- [D] 报错

**参考答案**：0

**解析**：return 会结束生成器，其后的 yield 2 永远不会执行，因此只产出 1。return 在生成器中相当于抛出 StopIteration。

### single_choice · None



- [A] 1
  2
- [B] 1
- [C] 2
- [D] 报错

**参考答案**：1

**解析**：在循环中打印 1 后立刻 close 生成器，generator 被标记为耗尽，for 下一次取下一个值时抛 StopIteration，循环结束。因此只打印 1。

### single_choice · None



- [A] [0, 1, 2]
- [B] [2, 2, 2]
- [C] [0, 0, 0]
- [D] 报错

**参考答案**：1

**解析**：生成器是惰性的，但 lambda 闭包捕获的是变量 i 本身。到列表推导式真正调用 lambda 时，生成器已经耗尽，i 的最终值为 2，因此三个函数都返回 2。

### single_choice · None



- [A] 3 []
- [B] 3 [1, 2]
- [C] 0 [1, 2]
- [D] 报错

**参考答案**：0

**解析**：consume(g) 迭代完生成器后已耗尽，所以后续 list(g) 为空。常见误解是生成器在传参后仍可重复使用。

### single_choice · None



- [A] 返回一个预先生成的巨大列表
- [B] 使用 while True 配合 yield
- [C] 使用递归并缓存所有结果
- [D] 使用全局变量数组保存所有项

**参考答案**：1

**解析**：生成器天然适合无限序列，while True 配合 yield 按需产出。预生成列表、全量缓存和全局数组都会无界占用内存，不适合无限序列。

### single_choice · None



- [A] 需要反复随机访问第 100 个元素
- [B] 读取一个超大日志文件并逐行处理
- [C] 需要对小规模数据多次排序
- [D] 需要把结果缓存起来供多次遍历

**参考答案**：1

**解析**：逐行读取超大文件时，生成器可以按需处理而不把整个文件装入内存。需要随机访问、重复遍历或多次排序的场景通常应使用列表或其他可重复序列。

### single_choice · None



- [A] a
  1
  b
  default
  default
- [B] a
  1
  b
  default
- [C] a
  1
  b
  报错
- [D] default
  default
  default

**参考答案**：0

**解析**：第一次 next 触发 print("a") 并返回 1；第二次 next 执行 print("b") 后生成器结束，返回默认值 default；第三次生成器已耗尽，也返回默认值 default。

### single_choice · None



- [A] send(None) 与 next(g) 等价，都用于启动或推进生成器
- [B] send(None) 会报错，因为 send 必须传非 None
- [C] next(g) 会给生成器发送 None，而 send(None) 不会
- [D] 只有第一次启动前才能使用 send(None)

**参考答案**：0

**解析**：对于生成器，send(None) 与 next(g) 效果相同，都可以启动或推进生成器；send 传非 None 时要求生成器已启动（否则报 TypeError）。

### single_choice · None



- [A] [1, 2] 然后 [1, 2]
- [B] [1, 2] 然后 []
- [C] [] 然后 [1, 2]
- [D] 报错，生成器不能转成列表

**参考答案**：1

**解析**：生成器是一次性迭代器，第一次 list(g) 耗尽后，第二次再迭代不会重新开始，因此得到空列表。常见误解是把它当成可重复遍历的容器。

### single_choice · None



- [A] 立即返回 5
- [B] 抛出 SyntaxError
- [C] 返回一个生成器对象
- [D] 返回 None

**参考答案**：2

**解析**：只要函数体中出现 yield，它就是生成器函数，调用时返回生成器对象，不执行函数体；return 5 会在迭代结束后作为 StopIteration 的 value 传递，但调用本身不会立即返回 5。

### single_choice · None



- [A] 0
  1
  2
  end
- [B] 0
  1
  2
  报错 StopIteration
- [C] 0
  1
  2
  None
- [D] 1
  2
  3
  end

**参考答案**：0

**解析**：前三次 next 取到 0、1、2，第四次生成器已耗尽，但 next 提供了默认值 "end"，所以返回默认值而不抛 StopIteration。若没有默认值则会抛 StopIteration。

### single_choice · None



- [A] 它只能用于列表，不能用于生成器
- [B] 它把子迭代器中的所有元素依次产出，并转发 send/throw
- [C] 它等价于 `return`，会结束当前生成器
- [D] 它只能出现在普通函数中，不能出现在生成器函数里

**参考答案**：1

**解析**：yield from 委托给子迭代器，逐个产出其元素，并且把 send/throw/close 转发给它，最终返回值成为 yield from 表达式的值。A、C、D 都是常见误解。

### single_choice · None



- [A] 1
  received 10
  None
- [B] received 10
  1
  None
- [C] 1
  received None
  None
- [D] 报错，send 不能用于刚创建的生成器

**参考答案**：0

**解析**：第一次 next 启动生成器并产出 1；send(10) 把 10 作为 yield 表达式的值赋给 x，打印 received 10，函数结束产出 StopIteration，因此第二次 print 显示 None。

### single_choice · None



- [A] def f(): return 1
- [B] def f(): yield 1
- [C] def f(): print(1)
- [D] def f(): raise 1

**参考答案**：1

**解析**：函数体内出现 yield 才是生成器函数；只有 return、print 或 raise 的函数都是普通函数。

### single_choice · None



- [A] 返回 None
- [B] 抛出 StopIteration
- [C] 抛出 GeneratorExit
- [D] 返回空列表

**参考答案**：1

**解析**：for 循环隐式调用 next()，当生成器耗尽时抛出 StopIteration，循环正常结束。None 是普通返回值，GeneratorExit 与关闭相关，空列表不是生成器迭代结束的信号。

### single_choice · None



- [A] 1
  cleanup
- [B] 1
  2
  cleanup
- [C] cleanup
  1
- [D] 1
  报错

**参考答案**：0

**解析**：close() 会在生成器暂停处抛出 GeneratorExit，从而触发 finally 中的清理代码。由于此时只产出了 1，并未执行到 yield 2，所以只打印 1 和 cleanup。

### single_choice · None



- [A] 调用该函数会立即执行函数体并返回全部结果
- [B] 调用该函数返回一个生成器对象，函数体在首次迭代时才执行
- [C] yield 只能出现在函数外部的模块层
- [D] 含有 yield 的函数必须显式 return 一个列表

**参考答案**：1

**解析**：含 yield 的函数被调用时不会执行函数体，而是返回一个生成器对象；函数体在第一次请求下一个值（如 next() 或 for 迭代）时才开始执行，并在每个 yield 处暂停。

### single_choice · None



- [A] created
  start
  1
  mid
  2
- [B] start
  created
  1
  mid
  2
- [C] created
  1
  2
- [D] start
  mid
  1
  2
  created

**参考答案**：0

**解析**：调用 g() 只创建生成器，不执行函数体，所以先打印 'created'。第一次 next() 才执行到第一个 yield，打印 'start' 并返回值 1；第二次 next() 从暂停处继续，打印 'mid' 并返回值 2。

### multi_choice · None



- [A] 该函数调用后返回生成器对象
- [B] 函数体在第一次请求元素时才开始执行
- [C] 生成器支持 send() 向其传值
- [D] 生成器迭代耗尽后可以自动重新从头迭代
- [E] yield 表达式本身可以接收外部传入的值

**参考答案**：[0, 1, 2, 4]

**解析**：A、B、C、E 都是生成器的正确特性。D 错误：生成器是单次迭代的，耗尽后再次迭代不会重新执行函数体，如需重复需重新调用函数或使用其他结构。

### multi_choice · None



- [A] 流式读取日志文件并逐行做过滤
- [B] 生成一个有限的斐波那契数列并立即对整个序列排序
- [C] 实现一个无限递增的计数器，只在需要时取前几个值
- [D] 需要多次随机访问结果集合中的任意位置
- [E] 用处理管道逐个转换数据项以避免中间列表

**参考答案**：[0, 2, 4]

**解析**：A、C、E 都只顺序消费数据，适合惰性生成。B、D 需要对全部元素进行排序或随机访问，必须物化为列表，不适合生成器。

### multi_choice · None



- [A] 生成器耗尽后再 next() 会抛 StopIteration
- [B] for 循环会自动处理 StopIteration 并正常结束
- [C] 生成器中的异常会传播给调用方
- [D] 生成器内部的 yield 必须被 try/except 包裹
- [E] 可以通过 throw() 向生成器内部注入异常

**参考答案**：[0, 1, 2, 4]

**解析**：A、B、C、E 正确。D 错误：yield 不需要强制用 try/except 包裹，是否捕获取决于业务需要（如清理资源时常用 try/finally）。

### multi_choice · None



- [A] 正常迭代完两个值后会打印 'cleanup'
- [B] 在第一次 yield 后调用 gen.close() 会打印 'cleanup'
- [C] 生成器完全耗尽时 finally 一定会执行
- [D] 如果外部通过 throw() 注入异常且未被捕获，finally 也会执行
- [E] close() 不会触发 finally

**参考答案**：[0, 1, 2, 3]

**解析**：finally 在生成器正常耗尽、被 close() 关闭、或被注入未捕获异常时都会执行，因此 A、B、C、D 都正确，E 错误。

### fill_blank · None



**参考答案**：["yield", "yield "]

**解析**：在循环中通过 yield i 逐个产出值，函数即成为生成器函数，调用它返回生成器对象。

### fill_blank · None



**参考答案**：["yield", "yield ", "(yield)"]

**解析**：yield 是表达式，可以出现在赋值右侧。第一次 next(gen) 启动生成器并推进到 yield；之后 send('hello') 使 yield 表达式返回 'hello'，赋给 v 并打印出来。

### fill_blank · None



**参考答案**：["next", "next "]

**解析**：next(gen, default) 在生成器耗尽时返回 default 而不抛异常。这里 next(gen, None) 会在耗尽时返回 None。

### code_reading · None



**参考答案**：A\ngot 1\nB

**解析**：迭代开始：打印 A 并产出 1，for 接收到 1 后打印 'got 1'。再次请求下一个值时，从 yield 1 后继续打印 B，遇到 return 结束，return 之后的 yield 2 永远不会执行。for 捕获 StopIteration 后结束。

### code_reading · None



**参考答案**：输出依次为 1\n3\n6。因为每次 yield 都把当前累加的 total 返回，total 在生成器内部持续保留，而不是每次从 0 重新开始。

**解析**：生成器暂停时会保留局部变量 total，所以每次 next 都在上次的累加基础上继续，得到前缀和 1、3、6。

### scenario · None



**解析**：答案应指出：用生成器逐行读取文件（如 for line in f，或封装为生成器函数 yield 过滤后的行），避免一次性把整个文件放入列表。生成器惰性、按需产出，内存占用接近常量，适合流式处理大文件；同时可把过滤和统计拆成可组合的生成器管道。

### single_choice · None



- [A] 返回 None
- [B] 重新从头开始执行
- [C] 抛出 StopIteration 异常
- [D] 返回最后一个 yield 的值

**参考答案**：2

**解析**：生成器耗尽后再调用 next() 会抛出 StopIteration。for 循环会自动捕获该异常并正常结束，因此手动循环时才会看到。

### scenario · None



**解析**：无限生成器不会自然耗尽，for 循环永远不会结束。安全方式包括：在循环体内用条件 break（如取到 n 个后退出），或使用 itertools.islice 或手动调用 next() 限定次数，明确终止条件。

### single_choice · None



- [A] 表达式 x = yield v 中，x 会得到调用方通过 send() 传入的值
- [B] yield 语句没有返回值，永远为 None
- [C] send() 可以用来向尚未启动的生成器传值，无需先 next()
- [D] yield 只能返回，不能接收值

**参考答案**：0

**解析**：yield 是一个表达式，它的值由外部通过 gen.send(value) 传入；但第一次启动生成器必须用 next() 或 send(None)，否则会报错。

### single_choice · None



- [A] 0 到 n 的整数（含 n）
- [B] 0 到 n-1 的整数
- [C] 1 到 n 的整数
- [D] 无限循环的整数

**参考答案**：1

**解析**：循环条件为 i < n，当 i 达到 n 时不再进入循环，因此产出 0,1,...,n-1。

### single_choice · None



- [A] 生成器在创建时就把所有结果计算并存入列表
- [B] 生成器按需产生值，通常比一次性构建完整列表更省内存
- [C] 生成器一旦迭代完还能再次完整迭代
- [D] 生成器无法用 for 循环遍历

**参考答案**：1

**解析**：生成器是惰性求值，按需产出下一个值，不需要一次性保存全部结果，因此在大数据流处理中更省内存。耗尽后不能重用。

### single_choice · None



- [A] 把方括号换成圆括号：[x*2 for x in data] → (x*2 for x in data)
- [B] 在推导式前加 yield：(yield x*2 for x in data)
- [C] 把 for 去掉：[x*2]
- [D] 使用 list(x*2 for x in data) 才叫生成器表达式

**参考答案**：0

**解析**：生成器表达式与列表推导式语法几乎相同，只需把方括号换成圆括号。list(...) 会把生成器重新物化成列表，失去惰性优势。

### single_choice · None



- [A] 需要多次随机访问同一个结果集合的中间元素
- [B] 需要多次遍历同一批数据并统计总数
- [C] 逐行读取一个超大文件并逐条处理，内存有限
- [D] 需要保证数据在所有线程间共享不可变

**参考答案**：2

**解析**：逐行处理大文件时，生成器每次只保留一行在内存中，避免把整个文件读入列表，非常适合内存受限的场景。

### single_choice · None



- [A] 都只是推进生成器，received 都是 None
- [B] next(gen) 让 received 得到 None，send('x') 让 received 得到 'x'
- [C] send('x') 会先重启生成器再打印 'x'
- [D] send('x') 等价于 next(gen)，忽略参数

**参考答案**：1

**解析**：首次 next(gen) 启动生成器并推进到 yield；之后 send('x') 会把 'x' 作为 yield 表达式的值赋给 received，因此打印 'got x'。

### single_choice · None



- [A] close() 会让生成器抛出 ValueError
- [B] close() 在生成器暂停处抛出 GeneratorExit，生成器可以捕获它做清理
- [C] close() 后会继续正常产出剩余元素
- [D] close() 只能对未启动的生成器调用

**参考答案**：1

**解析**：gen.close() 会在暂停点抛出 GeneratorExit，生成器可在 try/finally 中做资源清理；若生成器在收到 GeneratorExit 后又 yield，会触发 RuntimeError。
