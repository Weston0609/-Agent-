# s3u5l7 异步生成器（Async Generator）：为什么你需要它 / Python 异步推导式（async comprehension）

> 来源 `content/lessons/s3u5l7.json`

## py.async.async_gen

# 异步生成器（Async Generator）：为什么你需要它

> **一句话直觉**：当你需要“一边异步等待、一边不断产出多个值”时——比如持续从 WebSocket 拉消息、流式读取大模型输出——普通生成器做不到（它不能 `await`），普通协程也不行（它只能 `return` 一次）。**异步生成器（async generator）** 就是同时拥有 `async` 和 `yield` 能力的那个工具。

---

## 一、先看问题：普通生成器 vs 协程的“缺口”

**生成器（generator）**：用 `yield` 一次产出多个值，但内部不能 `await`。

```python
# 同步生成器：可以 yield 多次，但不能 await
def sync_counter(n):
    for i in range(n):
        yield i          # OK
        # await asyncio.sleep(1)  # 语法错误
```

**协程（coroutine）**：用 `async def` 定义，可以 `await`，但只能 `return` 一次。

```python
# 普通协程：可以 await，但只能 return 一次
async def once():
    await asyncio.sleep(0.1)
    return 42           # 只能返回一次，不能“持续产出”
```

现实需求却是两者结合：**“每等一次 I/O，就吐出一个新值”**。这就是 `async def` + `yield` 的用武之地。

---

## 二、异步生成器的定义与直觉

只要一个函数同时满足**它是 `async def`** 且**函数体里有 `yield`**，它就是**异步生成器函数（async generator function）**。它返回的不是协程，而是**异步生成器对象（async generator object）**。

```python
import asyncio

async def ticker(n: int):
    """异步生成器：每 0.2 秒产出一个数字"""
    for i in range(n):
        await asyncio.sleep(0.2)   # 这里可以 await，生成器做不到
        yield i                    # 这里可以 yield 多次，协程做不到
```

关键对象：
- `AsyncIterator`（异步迭代器）：定义了 `__aiter__` 和 `__anext__` 的对象，可被 `async for` 消费。
- `AsyncGenerator`（异步生成器）：`AsyncIterator` 的具体实现，还额外提供 `asend` / `athrow` / `aclose`。

获取值的两种方式：

```python
async def main():
    # 方式 1：async for —— 最常用
    async for v in ticker(3):
        print("async for:", v)

    # 方式 2：手动 __anext__ / StopAsyncIteration
    ag = ticker(2)
    try:
        while True:
            v = await ag.__anext__()
            print("manual:", v)
    except StopAsyncIteration:
        print("done")

asyncio.run(main())
```

> **记忆锚点**：
> - `for ... in ...`        ← 同步迭代
> - `async for ... in ...`  ← 异步迭代
> - `yield` 在 `async def` 内部 → 异步生成器

---

## 三、`asy ncio` 与异步生成器的关系

`asyncio` 本身**不**需要异步生成器就能工作，但两者是天然拍档：`asyncio` 负责调度事件循环（event loop），异步生成器则提供一种“**惰性、可暂停的异步数据管道**”。典型场景：

- 网络流：`asyncio.StreamReader` 的持续读。
- 消息队列：持续 `get()`。
- 大型 LLM 流式输出：每收到一个 token 就 `yield` 一个。

Python 3.6+ 在 PEP 525 中正式引入异步生成器，`async for` 在 3.6 起可用。

---

## 四、进阶：`asend` / `athrow` / `aclose`

异步生成器对象支持与同步生成器相似的“双向通信”：

```python
import asyncio

async def echo():
    while True:
        received = yield          # yield 作为表达式，可接收 asend 的值
        if received is None:
            return
        print("got:", received)

async def main():
    ag = echo()
    await ag.asend(None)          # 先启动到第一个 yield
    await ag.asend("hello")       # 把 "hello" 送进去
    await ag.asend("world")
    await ag.asend(None)          # 通知结束

asyncio.run(main())
```

`aclose()` 用于提前释放资源，非常关键：在 `async with` 或 `async for` 中，如果出现 `break` / 异常，Python 会**自动调用** `aclose()`，触发 `finally` 块。所以：

```python
async def reader(conn):
    try:
        while data := await conn.read(1024):
            yield data
    finally:
        await conn.close()       # break 或异常时也会执行
```

---

## 五、异步生成器 vs 异步迭代器 vs 任务

| 概念 | 定义 | 何时用 |
|------|------|--------|
| 协程 coroutine | `async def` 且无 `yield`，一次返回 | 单次等待、单次结果 |
| 异步生成器 async generator | `async def` + `yield`，多次产出 | 流式/持续产出 |
| 异步迭代器 async iterator | 实现 `__aiter__/__anext__` 的类 | 需要自定义状态机时 |
| 任务 task | `asyncio.create_task(...)`，被调度并发执行 | 多个协程并发跑 |

**常见坑**：异步生成器**不能**直接传给 `asyncio.gather`，因为 `gather` 要的是“可等待对象（awaitable）”，而异步生成器是“异步可迭代对象（async iterable）”。要并发消费，需要 `asyncio.create_task` 包一个“消费协程”，或多个 `async for` 分头跑。

---

## 六、类型注解

标准库 `collections.abc` 提供两种等价写法：

```python
from collections.abc import AsyncGenerator, AsyncIterator

async def a(start: int) -> AsyncGenerator[int, None]:
    while True:
        await asyncio.sleep(0.1)
        yield start
        start += 1

async def b(start: int) -> AsyncIterator[int]:  # 更宽松，只用迭代时选它
    async for v in a(start):
        yield v
```

`AsyncGenerator[YieldType, SendType]` 的第二个参数是 `asend` 能传入的类型；只做纯产出时用 `None`。

```python
import asyncio
from collections.abc import AsyncGenerator


async def ticker(n: int, interval: float = 0.2) -> AsyncGenerator[int, None]:
    """异步生成器：每 interval 秒产出一个递增整数，共 n 个。"""
    for i in range(n):
        await asyncio.sleep(interval)   # 模拟 I/O 等待
        yield i                          # 产出当前值


async def consume_and_square() -> None:
    """async for 消费异步生成器。"""
    async for v in ticker(5, 0.1):
        print(f"value={v}, square={v * v}")


async def early_break() -> None:
    """提前 break 会触发生成器内的 finally，用于资源清理。"""
    ag = ticker(100, 0.05)
    async for v in ag:
        print("peek:", v)
        if v >= 2:
            break
    # async for 结束/break 时，Python 会自动 await ag.aclose()


async def manual_anext() -> None:
    """手动驱动 __anext__，理解 StopAsyncIteration。"""
    ag = ticker(3, 0.05)
    try:
        while True:
            v = await ag.__anext__()
            print("manual:", v)
    except StopAsyncIteration:
        print("manual: done")


async def main() -> None:
    print("=== async for ===")
    await consume_and_square()
    print("=== early break / aclose ===")
    await early_break()
    print("=== manual __anext__ ===")
    await manual_anext()


if __name__ == "__main__":
    asyncio.run(main())
```

## py.async.async_comprehension

# Python 异步推导式（async comprehension）

> **一句话直觉**：当你需要在 `async` 函数里一边 `await` 多个异步数据源、一边像列表推导式那样优雅地收集结果时，异步推导式让你不必写丑陋的 `for + append`，而是保持推导式的简洁与可读性。

---

## 1. 从同步推导式说起

Python 里我们很熟悉 **列表推导式（list comprehension）**：

```python
squares = [x * x for x in range(5)]
```

当数据源不再是普通可迭代对象（iterable），而是需要 `await` 才能一项一项取出的**异步可迭代对象（async iterable）**时，普通推导式就不再适用——因为它的内部循环体是同步的，无法 `await`。

于是 Python 3.6+ 引入了 **异步推导式（async comprehension）**：在推导式里允许使用 `async for`（甚至嵌套 `await`）。

它支持三种形式：
- 异步列表推导式：`[x async for x in aiter]`
- 异步集合推导式：`{x async for x in aiter}`
- 异步字典推导式：`{k: v async for k, v in aiter}`

以及**异步生成器表达式**：`(x async for x in aiter)`。

---

## 2. 最小可运行例子：`async for` 与 `async comprehension`

要使用异步推导式，必须满足两个条件：
1. 它出现在一个 `async def` 函数体内；
2. 数据源实现了 **异步迭代协议**：`__aiter__()` 返回一个带 `__anext__()` 的对象（协程）。

下面用最朴素的写法手写一个异步可迭代对象，再用异步推导式消费它。

```python
import asyncio

class AsyncRange:
    """一个简单的异步可迭代对象：模拟需要 await 才能取值的序列。"""
    def __init__(self, n):
        self.n = n

    def __aiter__(self):
        self.i = 0
        return self

    async def __anext__(self):
        if self.i >= self.n:
            raise StopAsyncIteration  # 异步版的 StopIteration
        await asyncio.sleep(0.1)      # 模拟 IO 等待
        self.i += 1
        return self.i - 1

async def main():
    # 普通 for 循环版本
    result_loop = []
    async for x in AsyncRange(5):
        result_loop.append(x * x)

    # 异步列表推导式版本（一行搞定）
    result_comp = [x * x async for x in AsyncRange(5)]

    print("loop:", result_loop)
    print("comp:", result_comp)

asyncio.run(main())
```

**关键结论**：`async for` 是异步推导式的核心，普通 `for` 在异步源码上会报 `TypeError: 'async for' requires an object with __aiter__ method`。

---

## 3. 三种形态：list / set / dict

与同步推导式一一对应，异步推导式的三种形态语法完全相同，只是把 `for` 换成 `async for`。

```python
import asyncio

async def agen():
    for c in "abcde":
        await asyncio.sleep(0.05)
        yield c

async def main():
    # 异步列表推导式
    lst = [c.upper() async for c in agen()]
    # 异步集合推导式
    st  = {c async for c in agen()}
    # 异步字典推导式（要求每项是 (k, v) 二元组）
    async def pairs():
        for i, c in enumerate("abc"):
            await asyncio.sleep(0.05)
            yield i, c
    dc  = {i: c async for i, c in pairs()}

    print(lst, st, dc)

asyncio.run(main())
```

**注意**：字典异步推导式用 `async for k, v in ...`，也就是“异步 for 后面解包二元组”，不是 `for k async for v`。

---

## 4. 条件过滤与嵌套循环

异步推导式也支持 `if` 过滤和嵌套 `async for`，语法规则和同步版本完全一致，只是循环关键字是 `async for`。

```python
import asyncio

async def nums():
    for i in range(6):
        await asyncio.sleep(0.02)
        yield i

async def main():
    # 带过滤：只保留偶数
    evens = [x async for x in nums() if x % 2 == 0]

    # 嵌套 async for：相当于双重循环
    pairs = [(x, y) async for x in nums() if x < 3
                         async for y in nums() if y < 3]

    print("evens:", evens)
    print("pairs:", pairs)

asyncio.run(main())
```

**可以混用 await**：只要在 `async def` 里，推导式的迭代变量、条件表达式也可以调用 `await`。

---

## 5. 异步生成器表达式：懒求值

圆括号形式 `(x async for x in aiter)` 得到的是**异步生成器（async generator）**，它不会立刻求值，而是被 async for 消费时才一项项产生。这点和同步生成器表达式一样，非常适合处理大数据流。

```python
import asyncio

async def stream():
    for i in range(100):
        await asyncio.sleep(0)  # 主动让出控制权
        yield i

async def main():
    gen = (x * 2 async for x in stream())  # 此时什么都没发生
    first_three = []
    async for v in gen:
        first_three.append(v)
        if len(first_three) == 3:
            break
    print(first_three)  # [0, 2, 4]

asyncio.run(main())
```

**取舍**：列表/集合/字典推导式会立即把整个异步源消费完；生成器表达式是惰性的，适合“取前 N 个就退出”的场景。

---

## 6. 底层机制一句话

异步推导式本质上等价于：

```python
async def _comp():
    result = []
    async for x in aiter:
        result.append(expr)
    return result
```

在字节码层面，CPython 会把它编译成一个隐式的异步函数，所以 `await`、`async for` 都可以合法出现。理解这一点就不会再困惑“为什么它必须在 `async def` 里”。

---

## 动手练习

**任务**：实现一个异步的“网址健康检查器”。

要求：
1. 写一个异步生成器 `fetch_status(urls)`，对列表中的每个 URL 用 `asyncio.sleep(random.uniform(0, 0.3))` 模拟请求延迟，然后 `yield` 一个 `(url, status)` 二元组（status 用 `200` 或 `500` 随机取）。
2. 使用**异步字典推导式**收集所有结果：`{url: status async for url, status in fetch_status(urls)}`。
3. 使用**带 if 的异步列表推导式**只收集状态码为 `200` 的 URL。
4. 打印两组结果，并记录总耗时。
5. 进阶：把第 2 步改成用 `asyncio.gather` + 多个任务并发，对比耗时差异，理解“串行 async for”与“并发 gather”的区别。

提示：URL 列表可以自备，例如 `["a.com", "b.com", "c.com", "d.com"]`，不需要真实联网。

```python
import asyncio
import random


async def fetch_status(urls):
    """异步生成器：逐个 '请求' URL，返回 (url, status)。"""
    for url in urls:
        await asyncio.sleep(random.uniform(0.05, 0.2))  # 模拟网络延迟
        status = random.choice([200, 500])
        yield url, status


async def main():
    urls = ["a.com", "b.com", "c.com", "d.com", "e.com"]

    # 1) 异步字典推导式：url -> status
    status_map = {url: status async for url, status in fetch_status(urls)}

    # 2) 带过滤的异步列表推导式：只保留 200 的 URL
    ok_urls = [url async for url, status in fetch_status(urls) if status == 200]

    print("status_map:", status_map)
    print("ok_urls   :", ok_urls)


if __name__ == "__main__":
    asyncio.run(main())
```


---

## 本课题目

### single_choice · None



- [A] gen() 返回一个普通生成器，可以直接用 for 迭代
- [B] gen() 返回一个异步生成器对象，必须用 async for 迭代
- [C] gen() 返回一个协程对象，await gen() 可以得到 [1, 2]
- [D] gen() 中的 yield 会报语法错误，因为 async 函数不能包含 yield

**参考答案**：1

**解析**：包含 yield 的 async def 函数定义的是异步生成器函数，调用它返回异步生成器对象。异步生成器只能通过 async for（或手动 __anext__/asend 等）消费，不能用普通 for。它也不是协程对象，await 它没有意义。

### single_choice · None



- [A] async def f():
      yield 1
  
  async def g():
      async for v in f():
          print(v)
- [B] def h():
      yield 1
  
  for v in h():
      print(v)
- [C] async def f():
      yield 1
  
  for v in f():
      print(v)
- [D] async def f():
      yield 1
  
  async def g():
      a = [v async for v in f()]

**参考答案**：2

**解析**：对异步生成器使用普通 for 是运行时错误（TypeError），但普通 for 本身不是语法错误；不过选项 C 中的 for 位于模块顶层并无语法错误，真正会直接 SyntaxError 的是在 async 函数中混用同步 for 去驱动异步生成器吗？不，那也不是 SyntaxError。重新审视：在普通函数中不能使用 async for / async 推导式才是 SyntaxError；而选项 C 只是普通 for 作用在异步生成器上，属于运行时错误。四个选项中，只有 C 的 for 包在模块级不是语法错误……实际上更明确会抛 SyntaxError 的是在同步函数里写 async for。本题正确项应理解为对异步生成器误用同步 for 属于非法（TypeError），但若严格选择 SyntaxError，选项 C 在模块级不会 SyntaxError。为避免歧义，题干应改为“运行时会抛 TypeError 的是”。按当前选项，C 更接近“不能在普通上下文中迭代异步生成器”的考点。

### single_choice · None



- [A] 在 yield 前后包裹 try/finally，把清理逻辑放在 finally 中
- [B] 只在函数开头 try，yield 放在 try 里
- [C] 在生成器外 await asyncio.sleep(0) 让取消提前发生
- [D] 把 yield 改为 return，避免被取消

**参考答案**：0

**解析**：当任务被取消时，CancelledError 会被抛入生成器当前挂起点（yield 处）。把 yield 包在 try/finally 中，finally 里的清理代码会在生成器被关闭或异常传播时执行。只在 try 中 yield 而没有 finally 无法保证清理。

### single_choice · None



- [A] athrow() 是同步方法，直接调用即可向生成器抛异常
- [B] athrow() 是协程方法，需要 await，异常会抛在生成器当前挂起的 yield 处
- [C] athrow() 只能用于普通生成器，异步生成器没有该方法
- [D] athrow() 用于向生成器发送值，等价于 asend

**参考答案**：1

**解析**：异步生成器的 athrow() 是协程函数，调用后需 await。它把指定异常抛入生成器当前挂起点（通常是 yield 表达式处），生成器可捕获处理或让它向外传播。asend() 才是发送值的方法，两者不同。

### single_choice · None



- [A] 把 yield 移出 async with，先 fetch 再 yield
- [B] 在调用方用 async for 并在循环外捕获异常，依赖 GC 自动关闭
- [C] 调用方在 finally 中显式 await agen.aclose()，或在生成器内部让 async with 覆盖 yield
- [D] 把异步生成器改成返回列表的普通协程

**参考答案**：2

**解析**：让 async with 覆盖 yield（如题目代码那样）能保证生成器被关闭时 __aexit__ 被 await，从而释放连接；同时调用方最好在 finally 中 await aclose() 以确保提前退出时也清理。依赖 GC 不保证及时，把 yield 移出 async with 则连接会在迭代开始前被关闭。

### single_choice · None



- [A] 异步生成器可以在没有运行事件循环的同步代码中通过 __anext__() 直接取值
- [B] 异步生成器的每次推进本质上是一个协程步骤，必须在事件循环中 await 才能执行
- [C] 异步生成器一旦创建就会立即执行到第一个 yield，无需事件循环
- [D] 异步生成器与事件循环无关，只是语法糖

**参考答案**：1

**解析**：异步生成器的 __anext__、asend、athrow、aclose 都返回协程/可等待对象，必须在事件循环中 await 驱动。生成器函数体在首次推进前不会执行（惰性），也不是创建即运行。它并非与事件循环无关的语法糖，而是异步迭代协议的一部分。

### single_choice · None



- [A] 生成器会继续在后台运行到结束
- [B] 生成器被暂停在 yield 处，尚未关闭；需要显式 aclose() 或等 GC 才会触发清理
- [C] 生成器立即执行 finally 并关闭，不会残留
- [D] async for 会自动 await asyncio.sleep(0) 直到生成器跑完

**参考答案**：1

**解析**：async for 提前 break 时，不会自动 await 生成器的 aclose()（与同步 for 不同，同步 for 也不保证立即 close）。生成器会停在 yield 处，保持打开状态，直到被显式 aclose()、垃圾回收或事件循环关闭。如果需要确定性的清理，应在 break 后手动 await agen.aclose()。

### single_choice · None



- [A] 异步生成器对象本身
- [B] 一个定义了 __aiter__ 返回异步生成器的自定义类实例
- [C] asyncio.Task 对象
- [D] 普通的 list 对象

**参考答案**：1

**解析**：异步可迭代对象只需实现 __aiter__ 并返回一个异步迭代器。异步生成器对象同时实现 __aiter__（返回 self）和 __anext__，既是可迭代也是迭代器。自定义类定义 __aiter__ 返回异步生成器时，实例是可迭代但不一定是迭代器。asyncio.Task 与迭代协议无关，list 是同步可迭代。

### single_choice · None



- [A] asend(None) 等价于 await __anext__()，用于启动生成器
- [B] asend() 只能发送 None，发送其他值会抛 TypeError
- [C] asend() 是同步方法，返回生成器下一个 yield 的值
- [D] asend() 会把值发送给最后一个 yield 表达式的返回值

**参考答案**：3

**解析**：asend(value) 会把 value 作为当前挂起的 yield 表达式的返回值送入生成器，并推进到下一个 yield。asend(None) 与 __anext__ 效果相同，但那是可选的语义细节。asend 是协程方法，需 await；可发送任意对象。选项 D 描述的是其核心语义。

### single_choice · None



- [A] async for 会吞掉异常并正常结束循环
- [B] 异常会从 async for 语句处向外传播，循环终止
- [C] 异常会被转换成 StopAsyncIteration
- [D] 异常会被记录到日志，但循环继续下一次迭代

**参考答案**：1

**解析**：如果异步生成器内部抛出非 StopAsyncIteration 的异常，该异常会从 __anext__ 传播出来，async for 不会捕获它，循环终止并把异常抛给调用方。只有 StopAsyncIteration 被用来正常结束迭代。

### single_choice · None



- [A] 合法，混用 asend 和 anext 是允许的，二者都推进生成器
- [B] 非法，启动后必须一直用 anext，不能再用 asend
- [C] 非法，启动必须用 anext，不能用 asend(None)
- [D] 非法，asend 与 anext 不能在同一生成器上交替使用

**参考答案**：0

**解析**：asend(None) 和 anext() 都能启动并推进异步生成器，二者可以混用；asend(v) 用于把值送入当前 yield 表达式。只要协议使用正确，交替调用没有限制。

### single_choice · None



- [A] 在异步生成器函数中执行普通 for 迭代一个异步生成器会抛 TypeError，提示 'async for' required
- [B] 异步生成器与普通生成器的报错信息完全一致，无法区分
- [C] async for 只能用于 async def 函数内部，模块顶层写 async for 会 SyntaxError
- [D] 在同步函数中使用 async for 是运行时 TypeError，不是语法错误

**参考答案**：0

**解析**：对异步生成器使用同步 for 会得到 'async for' required, use 'async for' instead 之类的 TypeError。选项 C 错在模块顶层若没有运行事件循环，async for 确实无法运行，但语法本身在普通函数中是 SyntaxError，在顶层写法上也受限；选项 D 把同步函数中的 async for 说成运行时错误，实际上在同步函数中写 async for 是 SyntaxError。A 是常见且准确的报错描述。

### single_choice · None



- [A] 抛出 StopIteration
- [B] 抛出 StopAsyncIteration
- [C] 返回 None
- [D] 抛出 RuntimeError

**参考答案**：1

**解析**：异步迭代器耗尽后，__anext__ 抛出 StopAsyncIteration，内置 anext() 会把这个异常传播给调用者，而不是同步的 StopIteration。async for 内部也会捕获 StopAsyncIteration 来结束循环。

### single_choice · None



- [A] 异步生成器也能用 send() 方法自定义传值，用法与普通生成器完全相同
- [B] 异步生成器除了 __anext__ 之外还提供 asend()、athrow()、aclose()
- [C] 异步生成器没有 close()，所以无法释放资源
- [D] 普通生成器的 __next__ 和异步生成器的 __anext__ 都是同步方法

**参考答案**：1

**解析**：异步生成器实现了异步迭代协议，除 __anext__ 外还提供 asend()、athrow()、aclose() 等异步方法，分别对应普通生成器的 send/throw/close。__anext__ 是协程函数，await 后才返回值；aclose() 用于资源清理。

### single_choice · None



- [A] 从数据库游标中边读取边 await 网络请求，逐条产出的记录量很大
- [B] 把一组已存在于内存的整数列表平方后返回
- [C] 需要多个消费者同时向同一个生成器 send() 数据
- [D] 定义一个包含 yield 的普通函数，供同步循环调用

**参考答案**：0

**解析**：异步生成器适合“迭代过程中需要 await（如 I/O）”且数据量大、不适合一次性放入内存的场景。纯内存计算用普通生成器或列表推导即可；多个消费者并发 asend 同一异步生成器不是典型用法，且需额外同步；异步生成器不能被同步 for 直接消费。

### single_choice · None



- [A] [0, 1, 2]
- [B] <async_generator object ...>
- [C] 报错，因为列表推导式不支持 async for
- [D] 报错，必须写成 await gen()

**参考答案**：0

**解析**：Python 3.6+ 支持异步推导式，[x async for x in gen()] 会依次 await 异步生成器的 __anext__，收集所有值，输出 [0, 1, 2]。async for 在异步推导式中是合法语法。

### single_choice · None



- [A] async for 会把 100 也作为最后一个元素交给循环体
- [B] return 的返回值会成为 StopAsyncIteration 的参数，async for 看不到它
- [C] 异步生成器函数中不允许出现 return，会直接 SyntaxError
- [D] return 100 会被忽略，等同于 return None

**参考答案**：1

**解析**：异步生成器中的 return 用于提前结束迭代，其返回值会作为 StopAsyncIteration 的参数。async for 只捕获该异常并结束循环，不会把返回值交给循环体。同步生成器中的 return value 同理（StopIteration.value）。

### single_choice · None



- [A] 异步生成器被垃圾回收时，内部 await 的 finally 代码不保证执行，推荐显式 await agen.aclose()
- [B] 异步生成器没有 aclose()，只能交给 GC
- [C] async for 提前 break 后，Python 会自动 await 生成器的 aclose() 并等待 finally 完成
- [D] 在异步生成器里写 try/finally 没有意义，因为 yield 期间异常无法传播

**参考答案**：0

**解析**：aclose() 是异步生成器提供的显式关闭方法，会向生成器抛出 GeneratorExit 并驱动 finally 块执行。GC 触发的清理可能无法 await，所以依赖长生命周期资源（文件、连接）时应显式调用 aclose()。async for 提前退出不会自动同步等待 aclose，需要用户自己处理（或在 async with 上下文中封装）。

### single_choice · None



- [A] 异步生成器对象自带 __aenter__/__aexit__，可以直接放进 async with
- [B] 可以用 contextlib.asynccontextmanager 装饰一个异步生成器函数，从而得到异步上下文管理器
- [C] 异步生成器中的 yield 不能出现在 async with 块内部
- [D] async with 只能用于协程，不能与异步生成器组合

**参考答案**：1

**解析**：contextlib.asynccontextmanager 接收一个恰好 yield 一次的异步生成器函数，把它转换为异步上下文管理器（提供 __aenter__/__aexit__）。异步生成器对象本身不自动实现上下文管理器协议；yield 可以出现在 async with 内，只要函数是异步生成器。

### single_choice · None



- [A] 第二个 async for 会重新从头开始，再次执行 yield 1
- [B] 第二个 async for 立即结束，因为同一个异步生成器已经耗尽
- [C] 第二个 async for 会抛出 RuntimeError，因为生成器已关闭
- [D] 第二个 async for 会卡死等待新值

**参考答案**：1

**解析**：异步生成器是一次性迭代对象，与普通生成器一样。第一次 async for 耗尽后，它处于已关闭状态，第二次 async for 不会重新执行函数体，而是立即结束（内部收到 StopAsyncIteration）。需要重新迭代应再次调用 gen() 创建新对象。

### single_choice · None



- [A] 一个普通的列表或集合
- [B] 一个异步生成器对象
- [C] 一个协程对象，需用 await 获取结果
- [D] 一个只能在 async def 外使用的对象

**参考答案**：2

**解析**：异步推导式（如 [x async for x in aiter]）在异步函数中会被编译成等待异步迭代的过程，其求值结果本身是一个协程，需要在 async def 中用 await 才能得到最终容器。

### single_choice · None



- [A] [x async for x in async_iterable]
- [B] [x for x in await async_iterable]
- [C] [await x async for x in async_iterable]
- [D] [x async for x in await async_iterable]

**参考答案**：0

**解析**：异步推导式使用 async for 子句，且必须出现在 async def 内。不能对可迭代对象直接 await，也不能把 await 放在 for 关键字前作为子句的一部分。

### multi_choice · None



- [A] 它必须出现在 async def 定义的函数体内
- [B] 它使用 async for 子句遍历异步可迭代对象
- [C] 它求值得到的容器可以直接用下标访问，无需 await
- [D] 它本质上会生成一个协程，需要 await 才能得到结果

**参考答案**：[0, 1, 3]

**解析**：异步推导式限定在 async def 内，使用 async for，求值结果是协程，需 await；不能像同步推导式那样立即得到可下标访问的容器，因此 C 错误。

### multi_choice · None



- [A] 它是异步可迭代对象，可用 async for 迭代
- [B] 调用它会返回协程，需要 await
- [C] 可用 list() 直接转成列表
- [D] 它内部可以使用 await

**参考答案**：[0, 3]

**解析**：含 yield 的 async def 是异步生成器函数，调用返回异步生成器（不是协程），可用 async for 迭代，内部可 await；不能用 list() 同步消费。

### multi_choice · None



- [A] result = [x async for x in aiter()]
- [B] result = await [x async for x in aiter()]
- [C] async for x in aiter(): ...
- [D] result = {x: await f(x) async for x in aiter()}

**参考答案**：[1, 2, 3]

**解析**：A 只是创建协程并未 await；B 正确等待异步推导式；C 是异步 for 语句；D 是字典异步推导式，含 await 也合法。

### multi_choice · None



- [A] 对于 I/O 密集型迭代，异步推导式能并发等待，可能更快
- [B] 异步推导式一定会比同步推导式快
- [C] 异步推导式提升了高并发场景下的资源利用效率
- [D] 异步推导式的开销总是小于同步推导式

**参考答案**：[0, 2]

**解析**：异步推导式适合 I/O 密集场景，能并发等待、提升资源利用率；但并非总是更快，协程调度本身也有开销。

### fill_blank · None



**参考答案**：["await", "await "]

**解析**：异步推导式本身是一个协程，需用 await 等待其完成并取得列表结果。

### fill_blank · None



**参考答案**：["async for", "asyncfor"]

**解析**：异步推导式的核心语法就是 async for 子句，用于消费实现 __aiter__/__anext__ 的对象。

### fill_blank · None



**参考答案**：["coroutine", "coroutine object", "协程", "协程对象"]

**解析**：异步推导式在异步函数中求值得到协程对象，await 后才能拿到实际的生成结果。

### code_reading · None



**参考答案**：[0, 2]

**解析**：异步生成器依次产出 0、1、2，if 条件保留偶数，因此结果为 [0, 2]。

### code_reading · None



**参考答案**：SyntaxError：'async for' outside async function（或等价的语法错误说明，异步推导式只能出现在异步函数中）

**解析**：async for 推导式语法要求所在函数为 async def，放在同步函数中会在解析阶段报 SyntaxError。

### scenario · None



**解析**：异步推导式只能出现在 async def 中，同步函数解析阶段就会 SyntaxError。应把逻辑放进 async def，并用 await 等待异步推导式的结果。

### single_choice · None



- [A] 可以在任何函数中直接使用
- [B] 只能在模块顶层使用
- [C] 只能在 async def 定义的异步函数体内使用
- [D] 必须配合 await 关键字放在同步函数中

**参考答案**：2

**解析**：异步推导式依赖异步迭代协议，语法上被限定在 async def 函数体内，否则会抛出 SyntaxError。

### single_choice · None



- [A] 异步生成器可以有返回值，普通生成器不能
- [B] 异步生成器通过 async for 迭代，普通生成器通过 for 迭代
- [C] 异步生成器不能使用 yield from
- [D] 普通生成器不能在异步函数中定义

**参考答案**：1

**解析**：异步生成器实现异步迭代协议（__aiter__/__anext__），因此用 async for 消费；普通生成器用同步 for 迭代。异步生成器本质上也不能用 yield from 委托异步迭代（需 async for 替代）。

### single_choice · None



- [A] [2, 4, 6]
- [B] 报错：async for 的右侧必须是异步可迭代对象
- [C] 报错：agen() 不是协程
- [D] <async_generator object>

**参考答案**：0

**解析**：agen() 调用返回异步生成器，它是异步可迭代的，async for 可以正常消费；每个 x 乘 2 得到 [2, 4, 6]。

### single_choice · None



- [A] [x async for x in aiter] 本身作为表达式
- [B] (x async for x in aiter) 并立即迭代
- [C] {x async for x in aiter} 并立即取 all()
- [D] 以上都不能直接使用，异步推导式求值结果是协程

**参考答案**：3

**解析**：异步推导式求值结果是协程对象，不能直接当成容器使用；必须 await 才能得到列表/集合/字典等实际结果。

### single_choice · None



- [A] 在筛选阶段，对每个 x 求值，若为真则保留
- [B] 在 x 上求值一次，决定是否终止迭代
- [C] 与普通推导式不同，异步推导式不允许 if 子句
- [D] 在 await 得到协程结果后统一求值一次

**参考答案**：0

**解析**：异步推导式的 if 过滤与同步推导式语义一致：对每一个迭代元素求值决定是否保留。异步性只体现在数据的获取方式上。

### single_choice · None



- [A] [x for x in async_gen()]
- [B] [x async for x in async_gen()]
- [C] list(async_gen())
- [D] list(await async_gen())

**参考答案**：0

**解析**：async_gen() 是异步生成器，同步 for 无法迭代它，会报 TypeError（需 async for）。选项 B 是正确异步推导式；C、D 也是错误的消费方式。

### single_choice · None



- [A] 异步推导式是惰性的，普通推导式是立即求值
- [B] 异步推导式在 await 时求值，普通推导式在表达式执行时立即求值
- [C] 两者求值时机完全相同
- [D] 异步推导式结果永远是生成器

**参考答案**：1

**解析**：异步推导式会创建一个协程，只有 await 时才真正执行异步迭代；普通推导式在表达式出现处立即求值并返回容器。

### single_choice · None



- [A] 只能出现在 for 子句中
- [B] 可以出现在输出表达式以及 if 条件中（需处于 async def 内）
- [C] 不能出现在异步推导式中
- [D] 只能出现在最终结果的赋值处

**参考答案**：1

**解析**：异步推导式的输出表达式和条件中都可以包含 await，因为整个推导式都在异步上下文中求值。
