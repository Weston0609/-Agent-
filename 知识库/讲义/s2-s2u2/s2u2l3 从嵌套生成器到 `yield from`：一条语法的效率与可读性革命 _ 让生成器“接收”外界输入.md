# s2u2l3 从嵌套生成器到 `yield from`：一条语法的效率与可读性革命 / 让生成器“接收”外界输入

> 来源 `content/lessons/s2u2l3.json`

## py.iter.yield_from

# 从嵌套生成器到 `yield from`：一条语法的效率与可读性革命

> **一句话直觉**：当你需要在一个生成器里"转发"另一个生成器的产出时，`yield from` 让 Python 帮你自动完成循环 + 异常传播 + 返回值传递，代码从 5 行变成 1 行，而且性能更好。

---

## 第 1 节：先搞懂生成器（generator）为什么需要"嵌套"

**生成器**是一种惰性产出值的函数，用 `yield` 关键字代替 `return`。每次调用 `next()`，函数从上次暂停的位置继续执行。

现实中，一个生成器常常需要"消费另一个生成器"，最典型的例子是**递归遍历树**。

```python
# 用生成器惰性地遍历一棵二叉树的所有值
def inorder(node):
    if node is None:
        return
    yield from inorder(node.left)   # 左子树
    yield node.value                # 自己
    yield from inorder(node.right)  # 右子树

class Node:
    def __init__(self, value, left=None, right=None):
        self.value, self.left, self.right = value, left, right

root = Node(2, Node(1), Node(3))
print(list(inorder(root)))  # [1, 2, 3]
```

**关键结论**：生成器可以嵌套。当外层生成器需要把内层生成器的所有值原样转发出去时，`yield from` 就是专门为此设计的语法。

---

## 第 2 节：`yield from` 的等价展开（先理解它到底做了什么）

`yield from iterable` 的最基础语义，等价于：

```python
for item in iterable:
    yield item
```

但它远不止于此。下面这段代码展示了"手写转发"和 `yield from` 的对比：

```python
# 手写转发：啰嗦而且容易漏掉 StopIteration 处理
def chain_manual(*iterables):
    for it in iterables:
        for x in it:
            yield x

# 使用 yield from：语义相同，更短、更快
def chain_yf(*iterables):
    for it in iterables:
        yield from it

print(list(chain_manual([1, 2], "ab")))  # [1, 2, 'a', 'b']
print(list(chain_yf([1, 2], "ab")))       # [1, 2, 'a', 'b']
```

**关键结论**：`yield from` 是 `for + yield` 的超集。除了转发值之外，它还自动处理**异常传播**和**返回值传递**（下一节展开）。

---

## 第 3 节：`yield from` 的隐藏能力——返回值与异常传播

很多人以为 `yield from` 只是个语法糖，其实它做了两件额外的事：

1. **把子生成器的 `return` 值作为 `yield from` 表达式的结果**。
2. **把外部 `send()` / `throw()` / `close()` 直接透传给子生成器**（PEP 380 定义的"委托"机制）。

```python
# 子生成器结束时 return 的值，会被 yield from "接住"
def child():
    yield 1
    yield 2
    return "done"          # 注意：这是 return，不是 yield

def parent():
    result = yield from child()  # result 收到子生成器的返回值
    print("child returned:", result)
    yield result

print(list(parent()))
# 输出：
# child returned: done
# [1, 2, 'done']
```

**关键结论**：`yield from` 不只是"值转发"，它建立一个**双向委托通道**——外部的 `send()` / `throw()` 会进入子生成器，子生成器的 `return` 值会回到父生成器。这正是 `asyncio` 中 `await` 的底层原型。

---

## 第 4 节：工程级用法——`await` 的前身与协程组合

在 Python 3.4 时代，`yield from` 就是协程（coroutine）的骨架。3.5 之后 `async def` / `await` 成为主流，但 `await` 本质上就是"带调度语义的 `yield from`"。

```python
import asyncio

async def fetch_id():
    await asyncio.sleep(0.01)
    return 42

async def main():
    # await 与 yield from 在同一条设计血脉上
    value = await fetch_id()
    print("got:", value)

asyncio.run(main())  # got: 42
```

同时，`yield from` 也可以把多个可迭代对象"拉平"成一条流水线，这是数据管道（data pipeline）的常见写法：

```python
import itertools

def read_lines(lines):
    yield from (ln.strip() for ln in lines)

def non_empty(lines):
    yield from (ln for ln in lines if ln)

raw = ["hello\n", "  \n", "world\n", "\n"]
pipeline = non_empty(read_lines(raw))
print(list(pipeline))  # ['hello', 'world']
```

**关键结论**：`yield from` 是构建"惰性数据管道"和"协程骨架"的通用积木。掌握它，你就理解了 `asyncio`、`trio` 这类异步框架的最底层机制。

---

## 第 5 节：性能与可读性——为什么官方推荐它

CPython 对 `yield from` 做了优化：值转发发生在 C 层，比 Python 层 `for + yield` 更快、更省栈。此外，`yield from` 明确表达"我在委托"这一意图，让代码审查者一眼看懂控制流。

```python
import timeit

def gen_manual(n):
    def inner():
        for i in range(n):
            yield i
    for x in inner():
        yield x

def gen_yf(n):
    def inner():
        for i in range(n):
            yield i
    yield from inner()

N = 100_000
print("manual:", timeit.timeit(lambda: list(gen_manual(N)), number=50))
print("yieldfrom:", timeit.timeit(lambda: list(gen_yf(N)), number=50))
# 典型结果：yield from 明显更快
```

**关键结论**：在任何"我需要原样转发另一个可迭代对象"的场景，优先用 `yield from`：代码更短、意图更清晰、运行更快。

```python
import math
from collections.abc import Iterable


def flatten(nested):
    """把任意深度的嵌套可迭代对象展平成一层。

    这是 yield from 最经典的应用：递归 + 委托。
    """
    for item in nested:
        if isinstance(item, Iterable) and not isinstance(item, (str, bytes)):
            yield from flatten(item)   # 递归委托
        else:
            yield item


def squares(nums):
    """子生成器：产出平方值，并 return 一个统计值。"""
    count = 0
    for n in nums:
        yield math.sqrt(n)
        count += 1
    return count  # 通过 yield from 把结果传回父生成器


def pipeline(nums):
    """父生成器：消费 squares 的结果。"""
    total = yield from squares(nums)  # total 收到 squares 的 return 值
    print(f"processed: {total} items")
    yield total


if __name__ == "__main__":
    # 1) 展平嵌套结构
    data = [1, [2, [3, 4]], (5, 6), [7]]
    print("flatten:", list(flatten(data)))

    # 2) 委托 + 返回值
    print("pipeline:", list(pipeline([1, 4, 9, 16])))
```

## py.iter.send

# py.iter.send：让生成器“接收”外界输入

> 一句话直觉：普通的 `yield` 只能“往外吐”数据，而 `send()` 可以让生成器“往里吃”数据——它把生成器从一个数据源，升级成了一个可双向通信的协程（coroutine）雏形。

---

## 0. 开场：为什么需要 `send`？

你已经知道：一个带 `yield` 的函数调用后会返回一个**生成器（generator）**，每次 `next()` 它就从上次暂停的地方继续跑，吐出一个值。

但问题来了：如果生成器在暂停时，我们想**告诉它一些新信息**再让它继续，怎么办？

例如：一个“累加器”生成器，每收到一个数就吐出当前总和。这个“收到的数”不能通过函数参数传（函数早就调用完了），只能通过生成器对象的 `.send(value)` 方法传进去。

这就是 `py.iter.send` 要解决的问题。

---

## 1. 基础机制：`yield` 是一个表达式，不只是语句

关键结论 1：`yield x` 在生成器**暂停时**会“向外”返回 `x`，同时**恢复时**它的**返回值**是外界通过 `send()` 传进来的东西。

```python
# 1_basic_yield.py
def echo():
    """第一次 next() 启动；之后每次 send(v) 都会打印 v"""
    print("生成器已启动")
    while True:
        received = yield  # yield 的值默认是 None
        print(f"收到：{received}")

g = echo()
next(g)                 # 启动：必须先 next() 或 send(None) 把它推到第一个 yield
# 输出：生成器已启动
g.send("hello")         # 恢复，received = "hello"
# 输出：收到：hello
g.send(42)
# 输出：收到：42
```

要点：
- 第一次必须用 `next(g)` 或 `g.send(None)` 启动，否则会抛 `TypeError: can't send non-None value to a just-started generator`。
- `send(x)` 的语义 = “让生成器从暂停处继续，把 `x` 作为 `yield` 表达式的值”，然后**返回下一个 `yield` 出来的值**。

---

## 2. `send` 有返回值：一个完整的双向通道

关键结论 2：`g.send(v)` 本身的返回值，就是生成器被恢复后**下一个 `yield` 出的值**。

```python
# 2_send_returns.py
def running_total():
    """每次收到一个数，就吐出累计和"""
    total = 0
    while True:
        n = yield total      # 先吐出当前 total；恢复时把 send 的值赋给 n
        total += n

g = running_total()
total = next(g)              # 启动，得到初始 total = 0
print("初始:", total)         # 初始: 0

total = g.send(10)           # 送 10 进去，得到新的 total
print("送 10 后:", total)      # 送 10 后: 10

total = g.send(5)
print("送 5 后:", total)       # 送 5 后: 15
```

此时生成器已经从“单向数据管道”变成“双向通道”：

```
调用方  ──send(v)──▶  生成器内部 (yield 的返回值 = v)
调用方  ◀──yield x─   生成器吐出下个值 (send 的返回值 = x)
```

---

## 3. 与 `for` 循环不兼容：`send` 是一个“半协程”

关键结论 3：`for x in g` 只会做 `next()`，无法把值送进去；要 `send` 就必须手动 `next()` 驱动。

```python
# 3_no_for_loop.py
def counter():
    i = 0
    while True:
        cmd = yield i
        if cmd == "stop":
            return           # StopIteration 结束
        i += 1

g = counter()
next(g)                      # 启动，返回 0
print(g.send("go"))          # 1
print(g.send("go"))          # 2

# 尝试用 for 循环会失败：for 只会 next()，无法 send 语义
try:
    for v in g:              # 会一直跑，永远停不下来，且无法 stop
        pass
except Exception as e:
    print(e)
```

这就是官方文档把这种生成器归类为**协程（coroutine）**而非普通迭代器的原因：它有“接收”能力，`collections.abc.Coroutine` 的签名就是 `Coroutine[YieldType, SendType, ReturnType]`。

---

## 4. 典型工程模式：用 `send` 做流式状态机 / 累加 / 调度

关键结论 4：当你在做“流式处理、状态机、简易协程调度、生产者-消费者解耦”时，`send` 是标准工具。

```python
# 4_state_machine.py
def traffic_light():
    """用 send 做状态机：send('next') 切换到下一个灯色"""
    state = "红"
    while True:
        cmd = yield state      # 向外报告当前状态
        if cmd == "next":
            state = {"红": "绿", "绿": "黄", "黄": "红"}[state]
        elif cmd == "reset":
            state = "红"

light = traffic_light()
print(next(light))             # 红
print(light.send("next"))      # 绿
print(light.send("next"))      # 黄
print(light.send("reset"))     # 红
```

工程场景举例：
- **流式聚合**：日志按行 `send` 进去，生成器返回滑动窗口统计。
- **协议解析**：逐字节 `send`，返回解析出的消息帧。
- **简易调度器**：`send` 充当任务间通信的“信箱”。

注：Python 3.5 之后 `async/await` 是更正式的协程方案，但 `send` 的语义仍然是 `async` 协程的底层基础。

---

## 5. 与类型标注结合：`Generator[Y, S, R]`

关键结论 5：类型层面，`send` 接收的类型由 `Generator[YieldType, SendType, ReturnType]` 的**第二个参数**声明。

```python
# 5_typing.py
from typing import Generator

def running_total() -> Generator[int, int, None]:
    """yield int，send 也是 int，最终 return None"""
    total = 0
    while True:
        n = yield total
        total += n
```

- `Generator[int, int, None]` 分别对应：吐出的值类型 / 送进去的值类型 / `return` 的类型。
- `collections.abc.Coroutine[YieldType, SendType, ReturnType]` 是异步版本的对应签名。

---

## 小结

| 动作 | 含义 |
|---|---|
| `next(g)` | 恢复生成器，`yield` 表达式取值为 `None` |
| `g.send(v)` | 恢复生成器，`yield` 表达式取值为 `v`，返回下一个 `yield` 出的值 |
| 首次启动 | 只能用 `next(g)` 或 `g.send(None)` |
| 结束 | 生成器 `return` 会抛 `StopIteration` |

---

## 动手练习

**任务：实现一个“滑动窗口均值”生成器 `sliding_avg(window)`**

要求：
1. 通过 `.send(number)` 送进数字；生成器每次吐回当前窗口内的平均值（浮点数）。
2. 第一次 `next()` 只做启动，不送数据。
3. 通过 `.send(None)` 表示“关闭”，生成器 `return` 退出，并在 `StopIteration.value` 中返回平均值总量（或 `None`）。
4. 用类型标注 `Generator[float, int | None, int]` 声明签名。

参考用法：

```python
g = sliding_avg(3)
next(g)
for x in [1, 2, 3, 4, 5]:
    print(g.send(x))
# 期望：1.0, 1.5, 2.0, 3.0, 4.0
try:
    g.send(None)
except StopIteration as e:
    print("总计:", e.value)   # 总计: 5
```

提示：用 `collections.deque(maxlen=window)` 保存窗口；每次 `send` 收到 `None` 时 `return len(window_so_far)`。


---

## 本课题目

### single_choice · None



- [A] yield from 只能用于列表，不能用于生成器
- [B] yield from 可以把一个可迭代对象中的元素逐个委托给当前生成器产出
- [C] yield from 会立即把可迭代对象转换成列表并返回
- [D] yield from 只能出现在普通函数中，不能出现在生成器函数中

**参考答案**：1

**解析**：yield from 用于委托迭代，将子可迭代对象的元素逐个产出，而不是转换成列表或限制在列表上。

### single_choice · None



- [A] [1, 2, 3]
- [B] [1, 2]
- [C] [3]
- [D] [1, 2, [3]]

**参考答案**：0

**解析**：yield from [1, 2] 先产出 1 和 2，随后 yield 3 再产出 3，因此列表为 [1, 2, 3]。

### single_choice · None



- [A] 子迭代对象中抛出的异常会被自动忽略
- [B] 子迭代对象中抛出的异常会传播到外层生成器
- [C] yield from 无法处理异常，必须用 try 包裹整个程序
- [D] yield from 会自动把异常转换为 StopIteration

**参考答案**：1

**解析**：子迭代对象中未捕获的异常会传播到委托它的外层生成器，行为与普通迭代类似。

### single_choice · None



- [A] [1, 2, 'done']
- [B] [1, 'done']
- [C] ['done']
- [D] 报错，因为 inner 中有 return

**参考答案**：1

**解析**：inner 中 return 2 不会作为 yield 产出，只会作为 yield from 表达式的值；列表只包含 yield 产出的 1 和 'done'。

### single_choice · None



- [A] 需要把多个生成器串联成一个生成器时
- [B] 需要把生成器转换为列表时
- [C] 需要立即计算所有元素时
- [D] 需要修改生成器中的元素时

**参考答案**：0

**解析**：yield from 常用于将多个子生成器串联成一个统一的生成器，按顺序产出所有子生成器的元素。

### single_choice · None



- [A] 它的结果始终是 None
- [B] 它的结果始终是子迭代对象的最后一个元素
- [C] 它的结果取决于子迭代对象如何结束，可能是 return 的值
- [D] 它的结果始终是子迭代对象的长度

**参考答案**：2

**解析**：yield from 表达式的值由子迭代对象的结束方式决定：普通耗尽时为 None，若子生成器有 return 则可能得到返回值。

### single_choice · None



- [A] [0, 1, 2, 0, 1, 2]
- [B] [0, 1, 2]
- [C] [0, 1, 2, 3]
- [D] 报错，yield from 只能出现一次

**参考答案**：0

**解析**：可以多次使用 yield from，每次都会委托新的可迭代对象，因此依次产出两组 0、1、2。

### single_choice · None



- [A] yield from 只能用于递归生成器中
- [B] yield from 可以让当前生成器暂停并转发所有迭代操作
- [C] yield from 只能在类的方法中使用
- [D] yield from 不能与普通 yield 混用

**参考答案**：1

**解析**：yield from 会委托迭代操作，当前生成器暂停并转发所有产出，直到子迭代对象结束。

### single_choice · None



- [A] [1, 2, [3, 4], 5]
- [B] [1, 2, 3, 4, 5]
- [C] [1, [2, [3, 4]], 5]
- [D] 报错，递归中不能使用 yield from

**参考答案**：1

**解析**：递归地使用 yield from 展开嵌套列表，最终产出扁平化的 [1, 2, 3, 4, 5]。

### single_choice · None



- [A] [1, 2, 99]
- [B] [1, 2]
- [C] [99]
- [D] 报错，生成器中不能 return 非 None

**参考答案**：1

**解析**：生成器中的 return 值不会作为元素产出，因此列表只包含 yield from 产出的 1 和 2。

### single_choice · None



- [A] yield from 不支持 send()，只能用于简单迭代
- [B] yield from 可以转发 send() 到子生成器
- [C] yield from 会自动把 send() 转换为 next()
- [D] yield from 只能接收 None

**参考答案**：1

**解析**：yield from 在协程场景下可以转发 send() 调用的值到子生成器，实现委托。

### single_choice · None



- [A] A B [1, 2]
- [B] A [1, 2] B
- [C] [1, 2] A B
- [D] B A [1, 2]

**参考答案**：0

**解析**：生成器逐步执行：先打印 A，产出 1，再打印 B，产出 2；list 收集完所有值后程序继续，因此打印顺序为 A、B，然后输出列表。

### single_choice · None



- [A] outer 函数本身
- [B] inner 函数本身
- [C] inner() 返回的生成器对象
- [D] yield 关键字

**参考答案**：2

**解析**：yield from 后面跟的是 inner() 调用后返回的生成器对象，outer 会委托该生成器产出值。

### single_choice · None



- [A] 抛出 StopIteration
- [B] 输出 []
- [C] 输出 [1]
- [D] 输出 [None, 1]

**参考答案**：2

**解析**：委托空列表不会产出任何元素，随后继续执行 yield 1，因此输出 [1]。

### single_choice · None



- [A] yield from 完全等价于手写 for 循环加 yield，但更简洁
- [B] yield from 只能用于字符串，for 循环只能用于列表
- [C] yield from 会跳过子迭代对象中的异常，for 循环不会
- [D] yield from 不能嵌套使用，for 循环可以

**参考答案**：0

**解析**：在基本委托语义上，yield from iterable 等价于 for item in iterable: yield item，但语法更简洁。

### single_choice · None



- [A] 1
- [B] 2
- [C] None
- [D] StopIteration

**参考答案**：2

**解析**：当子迭代对象耗尽后，yield from 表达式的值默认为 None，除非使用 return 传递值。因此 x 为 None。

### single_choice · None



- [A] 任何可迭代对象
- [B] 只能是生成器对象
- [C] 只能是列表
- [D] 只能是元组

**参考答案**：0

**解析**：yield from 可以委托任何可迭代对象，包括列表、元组、字符串、生成器等。

### single_choice · None



- [A] ['a', 'b']
- [B] ['ab']
- [C] ['a', 'b', 'ab']
- [D] 报错

**参考答案**：0

**解析**：字符串 'ab' 是可迭代对象，会逐个产出字符 'a' 和 'b'，因此列表为 ['a', 'b']。

### single_choice · None



- [A] yield from 可以简化嵌套生成器的代码
- [B] yield from 可以获取子生成器的返回值
- [C] yield from 必须放在函数最后一行
- [D] yield from 后面可以跟另一个 yield from 表达式

**参考答案**：2

**解析**：yield from 不必放在函数最后一行，后面可以继续写其他 yield 或语句。

### single_choice · None



- [A] [0, 1, 2]
- [B] [0, 1, 2, 3]
- [C] range(0, 3)
- [D] 报错，因为不能委托生成器表达式

**参考答案**：0

**解析**：生成器表达式是可迭代对象，yield from 会逐个产出 0、1、2，因此列表为 [0, 1, 2]。

### single_choice · None



- [A] send 可以向生成器内部发送值，并恢复执行到下一个 yield
- [B] send 只能发送 None，发送其他值会报错
- [C] send 可以在生成器外部任意暂停执行
- [D] send 的返回值总是 None

**参考答案**：0

**解析**：send(value) 会把 value 作为当前暂停的 yield 表达式的值传入生成器内部，并继续执行到下一个 yield，返回下一个 yield 的值（或抛出 StopIteration）。它并非只能发送 None（next 相当于 send(None)），也不能从外部暂停生成器，返回值也不总是 None。

### single_choice · None



- [A] 1
  received: hello
  2
- [B] received: hello
  1
  2
- [C] 1
  2
  received: hello
- [D] TypeError

**参考答案**：0

**解析**：第一次 next(g) 启动生成器，执行到 yield 1 并返回 1。然后 send('hello') 把 'hello' 作为 yield 1 表达式的值赋给 x，继续执行 print('received:', x) 输出 received: hello，再执行到 yield 2 返回 2。

### fill_blank · None



**参考答案**：["send"]

**解析**：生成器通过 send 方法向暂停中的 yield 表达式发送值。首次必须 next 启动，随后才能 send('hi')。

### fill_blank · None



**参考答案**：["next", "next()", "send(None)", "g.send(None)"]

**解析**：未启动的生成器不允许发送非 None 值，需先用 next(g) 或 g.send(None) 启动到第一个 yield。

### fill_blank · None



**参考答案**：["yield"]

**解析**：send(data) 会把 data 作为暂停处 yield 表达式的求值结果（如 x = yield 中，x 得到 data），然后继续执行到下一个 yield 并返回其值。

### code_reading · None



**参考答案**：start
10
got a
20
got b
（最后一次 send('b') 后生成器继续执行到函数结束，抛出 StopIteration；若无捕获则该行会以 StopIteration 结束。严格输出为：start、10、got a、20、got b，随后 StopIteration）

**解析**：next(g) 启动执行打印 start 并 yield 10，返回 10。send('a') 把 a 赋给 x，打印 got a，执行到 yield 20 返回 20。send('b') 把 b 赋给 y，打印 got b，函数结束抛 StopIteration。

### code_reading · None



**参考答案**：1
closing
done

**解析**：next(g) 返回 1。close() 在挂起的 yield 1 处抛出 GeneratorExit，生成器打印 closing 并 re-raise，close 正常返回。因此再打印 done。注意捕获 GeneratorExit 后不能再 yield。

### code_reading · None



**参考答案**：TypeError：不能向刚创建、尚未启动的生成器发送非 None 值（can't send non-None value to a just-started generator）。应先 next(it) 或 it.send(None) 启动到第一个 yield，再用 send(5)。

**解析**：生成器必须先启动到第一个 yield 处，才能接收非 None 的 send 值。直接 send(5) 会触发 TypeError。

### scenario · None



**解析**：应在生成器内部用变量记录状态，用 x = yield value 接收 send 值并据此分支；首次必须先 next() 或 send(None) 启动；循环结束/生成器耗尽后 send 会抛 StopIteration，需要处理或正常结束。

### scenario · None



**解析**：原因是生成器尚未启动到第一个 yield 就 send 了非 None 值，触发 TypeError。修复：在 send 非 None 值之前先调用 next(gen) 或 gen.send(None) 启动生成器。

### scenario · None



**解析**：send 传值并推进到下一个 yield；throw 在暂停处注入异常，可被内部捕获；close 在暂停处抛出 GeneratorExit 用于清理。捕获 GeneratorExit 后不能再 yield，否则抛 RuntimeError；清理完毕应让异常继续传播（raise）或直接 return。

### single_choice · None



- [A] 2
- [B] 10
- [C] 20
- [D] None

**参考答案**：2

**解析**：next(it) 执行到 yield 1 暂停。send(10) 把 10 赋给 x，执行 return x*2，生成器结束并抛出 StopIteration，其 value 为 20，因此打印 20。

### single_choice · None



- [A] 正常把 1 发送进去并执行到第一个 yield
- [B] 抛出 TypeError，因为不能用非 None 值启动生成器
- [C] 抛出 StopIteration
- [D] 返回 None

**参考答案**：1

**解析**：生成器未启动时不能 send 非 None 值，否则抛出 TypeError: can't send non-None value to a just-started generator。必须先 next() 或 send(None) 启动到第一个 yield 后才能发送非 None 值。

### single_choice · None



- [A] yield from 会把 send 的值直接传给外层生成器，不会转发给子生成器
- [B] yield from 会把 send 的值转发给被委托的子生成器
- [C] yield from 子生成器结束后，send 的值会被丢弃
- [D] yield from 不能与 send 一起使用

**参考答案**：1

**解析**：yield from 会把外部的 send/throw/close 转发给被委托的子生成器；子生成器 return 的值会成为 yield from 表达式的值。因此 B 正确，A、C、D 错。

### multi_choice · None



- [A] 对已启动并暂停在 yield 处的生成器，send(v) 会恢复执行并返回下一个 yield 的值
- [B] send 传入的值会替换掉 yield 表达式的原本结果
- [C] 如果生成器内部在接收值前发生异常，send 会把异常传播给调用者
- [D] send 与 next 完全无关

**参考答案**：[0, 1, 2]

**解析**：A、B、C 正确。send(v) 恢复并返回下一个 yield 的值；yield 表达式的结果就是 send 的值（首次启动时相当于 None，被 next 或 send(None) 替换）；生成器内部异常会向调用者传播。send(None) 与 next 等价，所以 D 错。

### single_choice · None



- [A] 两者完全等价，效果相同
- [B] next(gen) 等价于 gen.send(None)，但 send(None) 不能用于停止状态下的恢复
- [C] send(None) 会向生成器传入 None 并在内部打印
- [D] next 只能在生成器上使用，send 只能用于协程

**参考答案**：1

**解析**：next(g) 语义上等价于 g.send(None)。两者都用于恢复执行：如果传 None，send 不会把特殊值抛到 yield 表达式（yield 得到 None）。不过 when 生成器已结束再调用都会抛 StopIteration。选项 B 的表述有些绕，但相对其他选项更贴近正确概念；关键在于 send(None) 与 next 效果一致。

### single_choice · None



- [A] 生成器重新启动并执行到第一个 yield
- [B] 抛出 StopIteration
- [C] 返回 3
- [D] 抛出 ValueError

**参考答案**：1

**解析**：生成器耗尽后，其帧已结束，再次 send 或 next 都会抛出 StopIteration（Python 3.7+ 后行为一致）。它不会自动重启。

### single_choice · None



- [A] close() 会在生成器暂停的 yield 处抛出 GeneratorExit
- [B] close() 后仍可继续 send
- [C] close() 会先执行完剩余代码再退出
- [D] close() 等同于 send(None)

**参考答案**：0

**解析**：close() 会在生成器当前暂停的 yield 处抛出 GeneratorExit，生成器可以捕获并做清理，但不能在捕获后再次 yield（否则 RuntimeError）。close 之后生成器不可再 send。close 不等于 send(None)。

### single_choice · None



- [A] 1
- [B] 'caught'
- [C] None
- [D] 抛出 ValueError 不再返回

**参考答案**：1

**解析**：throw(ValueError) 在生成器暂停处抛出异常。生成器内部捕获后执行 yield 'caught'，因此 throw 调用返回 'caught'。若未被捕获，throw 会把异常传播给调用者。

### multi_choice · None



- [A] 首次恢复生成器时应用 next() 或 send(None)
- [B] send 的返回值是下一个 yield 产出的值
- [C] send 可以把值传给生成器，也可以用来关闭生成器
- [D] 生成器内部可以通过赋值 y = yield 接收 send 传入的值
- [E] send 可以在生成器外部直接修改其局部变量

**参考答案**：[0, 1, 3]

**解析**：首次必须用 None 启动（A）。send 返回下一个 yield 的值（B）。send 传入的值被赋给暂停处 yield 表达式（D）。close() 才是关闭生成器，C 错。send 不能从外部直接改局部变量，E 错。

### multi_choice · None



- [A] 生成器耗尽后再 send 会抛 StopIteration
- [B] 对刚创建的生成器 send 非 None 值会抛 TypeError
- [C] send 到已关闭的生成器会抛 StopIteration 或 ValueError（视情况）
- [D] send 可以唤醒已耗尽但被重置的生成器

**参考答案**：[0, 1, 2]

**解析**：A、B、C 均正确。生成器耗尽后再 send 抛 StopIteration；刚启动前 send 非 None 抛 TypeError；已 close 后 send 会抛 StopIteration（某些实现下也表现为直接结束）。生成器没有重置机制，D 错。

### multi_choice · None



- [A] 调用 next(g) 后 n 为 0 并暂停在 yield n
- [B] send('inc') 后生成器内 cmd 为 'inc' 并执行 n+=1
- [C] send('inc') 的返回值是 1
- [D] send('inc') 后生成器会立即回到循环顶部再次 yield

**参考答案**：[0, 1, 2, 3]

**解析**：next(g) 启动循环，yield 0，n=0（A）。send('inc') 把 'inc' 赋给 cmd，执行 n+=1（B），然后循环回到 yield n 返回 1（C），生成器再次暂停（D）等待下一次 send。
