# s3u5l6 py.async.aiofiles 教学讲义 / 异步迭代（Async Iteration）

> 来源 `content/lessons/s3u5l6.json`

## py.async.aiofiles

# py.async.aiofiles 教学讲义

> 一句话直觉：当你要用 `asyncio` 写高并发程序，却发现普通的 `open()` / `read()` / `write()` 会把整个事件循环（event loop）卡死时，`aiofiles` 就是那把把文件 I/O 也变成 `await`-友好的钥匙。

本讲义面向零基础到工程级读者，前置知识为零。共 5 个小节，40 分钟节奏：0~6 分钟铺垫同步 I/O 的问题，6~15 分钟理解 `aiofiles` 的机制，15~30 分钟上手 API，30~36 分钟看典型工程模式，36~40 分钟做练习。

---

## 0. 为什么需要它：同步文件 I/O 会阻塞事件循环

`asyncio`（异步 I/O）是 Python 标准库里写并发代码的库，用 `async` / `await` 语法（语法糖）来组织协程（coroutine）。它擅长 **I/O 密集型（I/O-bound）** 任务，例如网络请求。

但 Python 内置的 `open()`、`file.read()`、`file.write()` 都是 **同步阻塞（synchronous blocking）** 调用。它们执行时会把当前线程挂起，而 `asyncio` 的事件循环（event loop，负责调度所有协程的调度器）就跑在单线程上。一旦你 `await` 的协程里混进一个同步 `time.sleep(1)` 或者一次慢速磁盘读，整个循环都会被卡住——其他本该并发的协程全部挨饿。

```python
import asyncio

async def fetch(name, delay):
    await asyncio.sleep(delay)   # 非阻塞：让出控制权给事件循环
    return name

async def main():
    # 两个协程并发执行，总耗时约 1 秒
    a, b = await asyncio.gather(fetch("A", 1), fetch("B", 1))
    print(a, b)

asyncio.run(main())
```

结论：**要想真正并发，所有阻塞调用都必须被替换成异步版本。** 文件 I/O 也是其中之一。

---

## 1. `aiofiles` 是什么：把同步文件 I/O 包成 `await`-友好接口

`aiofiles` 是一个第三方库，专门为 `asyncio` 提供异步版本的文件操作。它的核心思想是：**把阻塞的文件读写扔到线程池（thread pool）或进程池（executor）里执行，事件循环继续跑其他协程**。

它提供两个常用入口：

- `aiofiles.open(...)` — 异步版本的 `open()`，返回一个支持 `async with` 的上下文管理器。
- 生成的文件对象支持 `await f.read()`、`await f.write(...)`、`await f.readline()`、`async for line in f` 等异步方法。

安装：

```bash
pip install aiofiles
```

最小示例：

```python
import asyncio
import aiofiles

async def main():
    # async with 会在退出时自动 await 关闭文件
    async with aiofiles.open("demo.txt", mode="w", encoding="utf-8") as f:
        await f.write("hello aiofiles\n")

    async with aiofiles.open("demo.txt", mode="r", encoding="utf-8") as f:
        content = await f.read()
        print(content)

asyncio.run(main())
```

对比记忆：`open` → `aiofiles.open`，`with` → `async with`，`f.read()` → `await f.read()`。

---

## 2. 逐行解读：`async with` 与 `await` 的语义

理解三个关键词，`aiofiles` 就算入门：

1. **`async with`**：异步上下文管理器（async context manager）。进入 / 退出时会调用协程方法 `__aenter__` / `__aexit__`，退出时确保文件被异步关闭。
2. **`await`**：把控制权交还给事件循环，直到这个异步操作完成。`await f.read()` 期间事件循环可以去跑别的任务。
3. **`async for`**：异步迭代（async iteration）。逐行读取大文件时，它不会一次性把整个文件读进内存。

```python
import asyncio
import aiofiles

async def main():
    # 先写几行
    async with aiofiles.open("lines.txt", mode="w", encoding="utf-8") as f:
        for i in range(3):
            await f.write(f"line-{i}\n")

    # async for：逐行读，适合大文件
    async with aiofiles.open("lines.txt", mode="r", encoding="utf-8") as f:
        async for line in f:
            print("读到:", line.strip())

asyncio.run(main())
```

---

## 3. 并发读多个文件：`gather` 的力量

`aiofiles` 真正发光的地方是并发。假设你要读 5 个日志文件并统计行数，同步版本只能一个接一个；异步版本可以同时发起、同时等待。

```python
import asyncio
import aiofiles

async def count_lines(path):
    n = 0
    async with aiofiles.open(path, mode="r", encoding="utf-8") as f:
        async for _ in f:
            n += 1
    return path, n

async def main():
    # 准备几个测试文件
    for i in range(5):
        async with aiofiles.open(f"log{i}.txt", mode="w", encoding="utf-8") as f:
            await f.write("x\n" * (i + 1))

    # 并发地读 5 个文件
    results = await asyncio.gather(*(count_lines(f"log{i}.txt") for i in range(5)))
    for path, n in results:
        print(path, "->", n, "行")

asyncio.run(main())
```

> 关键点：`aiofiles` 内部使用线程池（executor），所以它能并发，但 **不会** 突破磁盘本身的吞吐瓶颈；它的收益来自「等待磁盘时不让 CPU 空转、不让其他协程饿死」。

---

## 4. 工程模式与边界：什么时候该用 / 不该用

**该用的场景：**

- Web 服务 / 爬虫 / 消息队列消费者里夹杂的日志写入、配置读取、上传文件落盘。
- 需要在同一事件循环里同时处理网络 + 文件，避免文件 I/O 拖垮网络并发。
- 读写很多小文件，且希望并发调度。

**不该用 / 要小心：**

- 单个超大文件的纯 CPU 计算（如逐字节解析）—— 那属于 CPU 密集，应该用多进程。
- 极端高吞吐的日志写入 —— 用专门的异步日志库（如 `aiologger`）或直接批量落盘更合适。
- 忘记 `async with` 关闭文件 → 文件描述符泄漏。
- 在 UI 主线程里把 `aiofiles` 当“万能非阻塞”用 —— 它仍然依赖线程池，池子满了会排队。

工程级示例：给一个异步爬虫加“结果落盘”步骤。

```python
import asyncio
import aiofiles

async def save_result(idx, text):
    async with aiofiles.open(f"result_{idx}.txt", mode="w", encoding="utf-8") as f:
        await f.write(text)

async def fake_fetch(idx):
    await asyncio.sleep(0.1)          # 模拟网络请求
    return f"data-{idx}"

async def main():
    tasks = []
    for i in range(10):
        async def worker(i=i):
            data = await fake_fetch(i)
            await save_result(i, data)
        tasks.append(worker())
    await asyncio.gather(*tasks)
    print("全部完成")

asyncio.run(main())
```

---

## 5. 动手练习

**任务：异步合并多个日志文件**

1. 用 `aiofiles` 并发创建 5 个文件 `part_0.txt` ~ `part_4.txt`，每个文件写入 1000 行内容，格式 `part-<i> line-<j>`。
2. 用 `asyncio.gather` 并发读取这 5 个文件，把所有行收集到一个列表。
3. 用 `aiofiles` 把合并后的内容写入 `merged.txt`（每个文件的原始行顺序要保持）。
4. 最后打印 `merged.txt` 的总行数，应为 5000。

**提示**：定义 `write_part(i)` 和 `read_part(i)` 两个异步函数，用 `asyncio.gather` 分两批并发调用；写入 `merged.txt` 时用 `aiofiles.open(..., "a")` 追加模式即可保持顺序。

**验收标准**：脚本 `python merge_logs.py` 一次跑通，输出 `total lines: 5000`。

**加分项**：给每个阶段加 `asyncio.sleep(0)`，观察事件循环里任务的切换顺序（可以用 `asyncio.current_task().get_name()` 打印任务名）。

## py.async.async_iter

# py.async.async_iter：异步迭代（Async Iteration）

> **一句话直觉**：当你需要“一个一个地、但每次取一个可能要等（比如等网络、等文件）”地处理数据时，普通 `for` 会卡住整个程序，而 `async for` 让等待时间被让出去，程序继续跑别的活儿。

---

## 0. 为什么需要“异步迭代”？

同步世界里，我们这样遍历一个列表：

```python
for x in [1, 2, 3]:
    print(x)
```

它的前提是：**每个元素都已经在内存里，取出不需要等待**。

但现实中的数据常常是“一个个流出来的”：

- 从 WebSocket（网络长连接）一条条收消息；
- 从数据库游标（cursor）一行行读；
- 从 LLM（大语言模型）流式接口一个字一个字吐 token；
- 从 Kafka 队列持续消费事件。

这些场景里，“取下一个元素”本身是一个**异步操作**（asynchronous operation），需要 `await` 等待。普通 `for` 不能 `await`，于是 Python 引入了 **异步迭代协议**：`__aiter__` / `__anext__`，以及语法糖 `async for`。

---

## 1. 协议层：`__aiter__` 与 `__anext__`

Python 的异步迭代（asynchronous iteration）由两个魔术方法（magic method）组成：

| 同步版本 | 异步版本 | 作用 |
|---|---|---|
| `__iter__` | `__aiter__` | 返回一个异步迭代器 |
| `__next__` | `__anext__` | 返回可等待对象，产出下一个值 |
| 抛 `StopIteration` | 抛 `StopAsyncIteration` | 表示迭代结束 |

也就是说，**异步迭代器 = 实现 `__aiter__` 和 `__anext__` 的对象**，并且 `__anext__` 必须是一个协程（coroutine）。

我们手写一个：

```python
import asyncio

class CountDown:
    """一个手写的异步可迭代对象：倒计时。"""
    def __init__(self, start: int):
        self.n = start

    def __aiter__(self):
        return self  # 自己就是迭代器

    async def __anext__(self) -> int:
        if self.n <= 0:
            raise StopAsyncIteration  # 结束信号（固定写法）
        await asyncio.sleep(0.3)      # 模拟异步等待
        self.n -= 1
        return self.n + 1

async def main():
    async for value in CountDown(3):   # 关键语法：async for
        print("取到:", value)

asyncio.run(main())
```

运行输出会每 0.3 秒打印一个数字：`3, 2, 1`。

**关键结论**：所谓 `async for`，本质上就是不断 `await obj.__anext__()`，直到捕获 `StopAsyncIteration`。

---

## 2. 更常用的写法：异步生成器（`async def` + `yield`）

手写 `__aiter__` / `__anext__` 太啰嗦。Python 提供了**异步生成器（async generator）**：只要在 `async def` 里 `yield`，就自动获得完整的异步迭代器协议。

```python
import asyncio

async def ticker(n: int):
    """每 0.5 秒产出一个计数。"""
    for i in range(n):
        await asyncio.sleep(0.5)
        yield i           # 注意：这里是 yield，不是在普通 def 里

async def main():
    async for i in ticker(3):
        print("tick", i)

asyncio.run(main())
```

`ticker` 既是**异步可迭代对象**（AsyncIterable），也是**异步迭代器**（AsyncIterator）。这是工程中最常见的写法。

**关键结论**：`async def` + `yield` = 异步生成器 = 自动实现异步迭代协议。写异步流，优先用这种写法。

---

## 3. 并发地把多个异步流合并

真实场景中，你可能要同时监听多个来源。`asyncio` 提供 `asyncio.Queue` 和 `asyncio.gather` 来组合。

下面示例模拟“两个传感器并发推数据，主循环消费”：

```python
import asyncio

async def producer(name: str, n: int, q: asyncio.Queue):
    """异步生成器，把数据放到队列。"""
    for i in range(n):
        await asyncio.sleep(0.4)
        await q.put(f"{name}-{i}")

async def main():
    q: asyncio.Queue[str] = asyncio.Queue()
    # 两个生产者并发执行
    await asyncio.gather(
        producer("A", 3, q),
        producer("B", 2, q),
    )
    # 消费直到队列为空
    while not q.empty():
        item = await q.get()
        print("收到:", item)

asyncio.run(main())
```

**关键结论**：异步迭代解决“逐个取值”的问题；并发（`gather` / `Queue` / `TaskGroup`）解决“多个流一起跑”的问题。二者常常配合使用。

---

## 4. 工程级模式：`async for` + 超时 / 取消 / 背压

生产代码里，异步流往往需要：

- **超时（timeout）**：单个元素等太久就放弃；
- **取消（cancellation）**：外部要求停止；
- **背压（backpressure）**：生产太快，消费者跟不上就阻塞生产者；
- **异常清理**：`async for` 提前 `break` 时能正确关闭资源。

`asyncio.timeout`（3.11+）与 `async for` 结合：

```python
import asyncio

async def slow_stream():
    for i in range(10):
        await asyncio.sleep(1)
        yield i

async def main():
    try:
        # 整体给整个循环 3.5 秒上限
        async with asyncio.timeout(3.5):
            async for v in slow_stream():
                print("处理:", v)
    except TimeoutError:
        print("总时超时，退出")

asyncio.run(main())
```

**关键结论**：`async for` 本身只是语法，工程鲁棒性依赖于 `asyncio.timeout`、`CancelledError`、`finally` 等机制。

---

## 5. 常见误区速览

- ❌ `async for` 用在普通对象上 → 报 `TypeError`，对象必须有 `__aiter__`。
- ❌ 在异步生成器里写 `return value` 想“返回值” → 语法错误，`async def` 生成器只能 `yield`。
- ❌ 忘记 `await obj.__anext__()` 里的 `await` → 得到的是协程对象而非值。
- ❌ 在 `async for` 里做 CPU 密集任务 → 事件循环被阻塞，异步白搭。
- ❌ 提前 `break` 不清理 → 用 `try/finally` 或 async context manager 释放资源。

---

## 6. 动手练习

**任务**：模拟一个“日志流处理器”。

要求：

1. 写一个异步生成器 `log_stream(path: str)`，逐行 `await asyncio.sleep(0.1)` 后 `yield` 一行；
2. 用 `async for` 消费，遇到包含 `"ERROR"` 的行立即停止（`break`）；
3. 统计并打印：处理了多少行、耗时多少秒；
4. 加一条总超时 2 秒（用 `asyncio.timeout`），超时后打印提示并优雅退出。

**验收点**：运行正常输出、断点行为正确、超时分支被触发过。

---

## 7. 一句话总结

> **`async for` = 让“取下一个元素”这件事也可以 `await`**；实现方式是 `__aiter__` / `__anext__`，写起来最方便是 `async def` + `yield`；工程上再叠加超时、取消、队列即可支撑真实异步数据流。

```python
import asyncio

# 1) 异步生成器：产生一个可被 async for 消费的异步流
async def countdown(start: int):
    for i in range(start, 0, -1):
        await asyncio.sleep(0.3)   # 模拟异步 IO 等待
        yield i

# 2) 主流程：使用 async for 逐个消费并设置总超时
async def main():
    total = 0
    try:
        async with asyncio.timeout(2.0):   # Python 3.11+
            async for value in countdown(5):
                print("取到:", value)
                total += value
    except TimeoutError:
        print("超时，提前退出")
    print("累计和:", total)

asyncio.run(main())
```


---

## 本课题目

### single_choice · None



- [A] 直接使用内置的 open() 读取，因为它在协程里会自动变成非阻塞
- [B] 使用支持异步的文件操作库，用 await 读取，避免阻塞事件循环
- [C] 把 open() 放进 asyncio.to_thread() 但忽略返回值
- [D] 用 time.sleep() 等待文件就绪后再用 open() 读取

**参考答案**：1

**解析**：内置 open() 是同步阻塞的，不会因为出现在协程里就变非阻塞；异步文件库通过 await 把实际 IO 交给线程池执行，从而不阻塞事件循环。

### single_choice · None



- [A] 读取文件内容必须用 await，因为返回的是协程对象
- [B] 写入文件内容必须用 await，因为返回的是协程对象
- [C] 读和写的操作通常都需要 await，因为它们返回可等待对象
- [D] 读写操作都不需要 await，只是普通同步函数

**参考答案**：2

**解析**：异步文件库的打开、读取、写入等 IO 操作通常都是协程函数，需要 await 才能执行；只对其中一个操作加 await 是常见误解。

### single_choice · None



- [A] 用 await 串行依次打开、读取每个文件
- [B] 用 asyncio.gather 并发地 await 多个文件的读取协程
- [C] 用一个全局锁保护所有文件读取，避免竞争
- [D] 用 while 循环轮询每个文件是否可读

**参考答案**：1

**解析**：asyncio.gather 可以并发等待多个协程，提高多文件 IO 的吞吐；串行 await 会一个接一个执行，全局锁反而限制并发。

### single_choice · None



- [A] 异步打开文件时不能指定 encoding 参数
- [B] 异步打开文件时可以像内置 open() 一样指定 encoding 参数
- [C] encoding 只能在读取时指定，写入时不能指定
- [D] 异步文件库总是使用系统默认编码，无法更改

**参考答案**：1

**解析**：异步文件库通常兼容内置 open() 的参数风格，支持 encoding 等参数；认为异步场景不能指定编码是常见误解。

### single_choice · None



- [A] 依赖垃圾回收自动关闭，不需要显式关闭
- [B] 使用 async with 或在 finally 中 await 关闭文件
- [C] 使用 synchronous close() 立即关闭，因为 close 不阻塞
- [D] 只要读取完成，文件句柄会自动异步释放

**参考答案**：1

**解析**：异步文件对象应显式关闭，async with 或 finally 配合 await close 能确保资源释放；依赖 GC 或同步 close 都不可靠。

### single_choice · None



- [A] 异步文件操作可以避免阻塞事件循环
- [B] 异步文件操作通常返回可等待对象
- [C] 异步文件操作保证比同步文件操作速度更快
- [D] 异步文件操作适合与 asyncio 一起使用

**参考答案**：2

**解析**：异步文件操作的主要目标是不阻塞事件循环，并不保证绝对速度更快；由于线程池等开销，小文件场景甚至可能更慢。

### single_choice · None



- [A] 直接得到文件内容字符串
- [B] 得到一个协程对象，实际读取不会发生
- [C] 抛出 SyntaxError
- [D] 自动同步执行并返回结果

**参考答案**：1

**解析**：协程函数调用后返回协程对象，不 await 就不会执行；这是异步编程中非常常见的错误。

### single_choice · None



- [A] 同步 open() 在协程中使用时也会自动让出控制权
- [B] 同步 open() 在协程中会阻塞事件循环，应改用异步方式或线程池
- [C] 同步 open() 不能读取文本文件，只能读取二进制文件
- [D] 同步 open() 只能在主线程使用，异步库只能在子线程使用

**参考答案**：1

**解析**：同步 open 是阻塞调用，直接在协程中执行会卡住事件循环；它并不自动让出控制权，也没有只读文本等限制。

### single_choice · None



- [A] 每次写日志都 await 打开、写入、关闭，或长期保持文件对象并 await 写入
- [B] 用同步 open('a') 写入，因为日志量小不会阻塞
- [C] 把日志内容拼成字符串后交给同步 print() 输出到文件
- [D] 用 os.write() 直接写入，忽略事件循环

**参考答案**：0

**解析**：异步日志写入应使用异步文件接口并正确 await；同步 open 或 os.write 都会阻塞事件循环，日志量小也不是理由。

### single_choice · None



- [A] 需要高并发地读写大量文件，同时保持事件循环响应
- [B] 单线程 CPU 密集计算任务
- [C] 只需要读取一个几 KB 的配置文件一次
- [D] 需要调用本地同步数据库驱动完成事务

**参考答案**：0

**解析**：异步文件操作适合高并发 IO 场景；CPU 密集和少量小文件读取优势不明显，同步数据库驱动则需要专门的异步驱动。

### single_choice · None



- [A] 用 try/except 包住 await 的文件操作，在 finally 中 await 关闭文件
- [B] 不能对异步文件操作使用 try/except，因为异常不会抛出
- [C] 必须使用同步的 except 块且不能包含 await
- [D] 异步文件操作的异常会在事件循环结束时统一忽略

**参考答案**：0

**解析**：异步代码中的异常同样可以用 try/except 捕获，finally 中也可以 await 关闭资源；异常不会自动被忽略。

### single_choice · None



- [A] 它直接用操作系统异步 IO 接口，完全不使用线程
- [B] 它通常把阻塞的文件 IO 交给线程池执行，并通过 await 等待结果
- [C] 它在每次读写时新建一个进程来执行
- [D] 它要求文件必须位于网络文件系统上才能异步

**参考答案**：1

**解析**：多数异步文件库通过线程池执行阻塞 IO，再以可等待对象的形式返回结果；并非所有平台都提供直接的无阻塞文件 IO。

### single_choice · None



- [A] aio_open 的返回值没有被 await，得到的是协程对象而不是文件对象
- [B] read() 不是协程，不能加 await
- [C] close() 应该改为 f.close_sync()
- [D] 文件打开模式 'r' 在异步库中不合法

**参考答案**：0

**解析**：异步打开文件本身也是需要 await 的协程调用，漏掉 await 会把协程对象赋给 f，后续 await f.read() 会报错。

### single_choice · None



- [A] 先用 read() 一次性读出全部内容，再 splitlines()
- [B] 用 async for 迭代文件对象逐行处理
- [C] 用 for line in f.readlines() 同步遍历
- [D] 用 os.read() 配合 select 手动轮询

**参考答案**：1

**解析**：异步文件对象通常支持 async for 逐行异步迭代，避免一次性把大文件读入内存；一次性 read 和同步遍历都会带来内存或阻塞问题。

### single_choice · None



- [A] 异步文件操作完全不使用线程，因此比同步文件 IO 更快
- [B] 异步文件操作通常借助线程池执行实际 IO，避免阻塞事件循环
- [C] 异步文件操作会阻塞事件循环，所以只能用在小文件上
- [D] 异步文件操作要求运行在单独进程中，不能与 asyncio 共用

**参考答案**：1

**解析**：很多异步文件库底层用线程池执行阻塞 IO，从而不阻塞事件循环；它并不保证绝对更快，也不是在独立进程或完全无线程下运行。

### single_choice · None



- [A] async with aio_open('a.txt') as f: content = await f.read()
- [B] with aio_open('a.txt') as f: content = await f.read()
- [C] async with await aio_open('a.txt') as f: content = f.read()
- [D] with await aio_open('a.txt') as f: content = f.read()

**参考答案**：0

**解析**：异步文件对象提供异步上下文管理器，应使用 async with 打开，并在内部 await 读取；普通 with 不支持 await 的异步进入退出。

### single_choice · None



- [A] 改用异步文件操作库，并用 await 读取
- [B] 加一个 await asyncio.sleep(0) 放在 open() 前面即可
- [C] 把 open() 改成 async open() 内置语法
- [D] 用 threading.Thread 包装 open() 并直接取回结果

**参考答案**：0

**解析**：Python 没有 async open 内置语法，加 sleep(0) 也不能把阻塞调用变成异步；应使用异步文件库或把阻塞调用放入线程池。

### single_choice · None



- [A] 写入内容通常要 await，写入完成后还需要 await 关闭文件
- [B] 写入内容不需要 await，只有关闭文件需要 await
- [C] 写入和关闭都不需要 await，因为写操作不阻塞
- [D] 写入需要 await，但关闭文件必须用同步的 close()

**参考答案**：0

**解析**：异步文件的 write 和 close 通常都是协程，需 await；只 await 其中一个或把 close 改成同步调用是常见错误。

### single_choice · None



- [A] 使用 asyncio.to_thread() 包装同步读取函数并 await 结果
- [B] 在协程中直接调用同步函数，事件循环会自动切换线程
- [C] 使用 asyncio.sleep() 包住同步读取函数
- [D] 把同步读取函数声明为 async def 后直接调用

**参考答案**：0

**解析**：asyncio.to_thread 可以把同步阻塞函数放到线程池执行并返回可等待对象；把函数声明为 async 并不会让内部阻塞调用变成非阻塞。

### single_choice · None



- [A] await aio_open('big.txt') 会阻塞事件循环
- [B] f.read() 之前漏写 await，会以同步方式执行并阻塞
- [C] await f.close() 会阻塞事件循环
- [D] 文件路径 big.txt 不存在导致阻塞

**参考答案**：1

**解析**：漏写 await 时 f.read() 返回的是协程对象而不会执行，或者在某些实现中触发同步路径；异步读取必须正确 await 才会异步执行。

### single_choice · None



- [A] 对象只需实现 __aiter__ 方法即可用于 async for
- [B] __anext__ 必须是一个普通函数，返回下一个值
- [C] __aiter__ 应返回一个异步迭代器，该迭代器实现 __anext__ 方法
- [D] async for 会自动把同步可迭代对象包装成异步迭代

**参考答案**：2

**解析**：__aiter__ 应返回异步迭代器，该迭代器实现 __anext__（通常是协程函数），await 后返回下一个值或抛 StopAsyncIteration。仅实现 __aiter__ 不够；__anext__ 通常是协程；async for 不会自动包装同步迭代对象。

### single_choice · None



- [A] StopIteration
- [B] StopAsyncIteration
- [C] GeneratorExit
- [D] RuntimeError

**参考答案**：1

**解析**：异步迭代协议用 StopAsyncIteration 表示迭代结束；在协程中抛 StopIteration 会被转换为 RuntimeError，是常见错误。

### multi_choice · None



- [A] 每次循环会 await 下一次取值
- [B] 循环体内部也是异步执行的，可以包含 await
- [C] async for 会自动并发消费所有元素
- [D] 对象必须先调用 __aiter__ 获得异步迭代器

**参考答案**：[0, 1, 3]

**解析**：async for 每次 await 一次 __anext__，循环体内可含 await；它会先调用 __aiter__。它是顺序消费，不会自动并发。

### fill_blank · None



**参考答案**：["StopAsyncIteration", "StopAsyncIteration()"]

**解析**：异步迭代协议规定耗尽时抛 StopAsyncIteration；抛同步的 StopIteration 在协程中会被转成 RuntimeError。

### fill_blank · None



**参考答案**：["yield"]

**解析**：async def 函数体内含 yield 时会被编译为异步生成器，同时实现 __aiter__ 与 __anext__。

### fill_blank · None



**参考答案**：["__anext__", "__anext__()", "__anext__ "]

**解析**：异步迭代器通过 await it.__anext__() 取下一个值；__aiter__ 只用于获取迭代器本身。

### code_reading · None



**参考答案**：依次输出：1、2、cleanup

**解析**：async for 顺序消费 1、2，生成器耗尽后 finally 块执行输出 cleanup。说明异步生成器的 finally 在迭代正常结束时也会执行。

### code_reading · None



**参考答案**：输出 done；提前 break 会触发异步生成器被关闭（相当于 await aclose()），生成器在暂停点注入 GeneratorExit 进行清理

**解析**：async for 在 break 退出时会关闭异步迭代器，等价于 await aclose()，向生成器抛 GeneratorExit 以运行 finally 清理。

### code_reading · None



**参考答案**：错误：对异步生成器使用了同步 for，会报 TypeError（'async_generator' object is not iterable）。修正：改为 async for x in agen():

**解析**：异步生成器实现的是 __aiter__/__anext__，不具备 __iter__，普通 for 无法消费，应使用 async for。

### scenario · None



**解析**：应把接收端封装成异步迭代器/异步生成器，用 async for 逐块消费，实现流式处理与背压；取消时通过 aclose/GeneratorExit 进入 finally 释放底层连接。对比一次性读取会占内存且无法及时停止。

### scenario · None



**解析**：正确做法：用 async for + break 结束迭代（会自动关闭生成器），或显式 await it.aclose()。两者都会在暂停点向生成器注入 GeneratorExit，触发 finally 清理（关闭连接/会话）。提前 return 若不触发关闭则可能泄漏资源。

### scenario · None



**解析**：__anext__ 应为协程：在队列空时用 await asyncio.sleep 或异步等待机制让出控制权，而非同步阻塞；取尽时抛 StopAsyncIteration。要点是保持协程、非阻塞、正确终止。

### single_choice · None



- [A] def agen(): yield 1
- [B] async def agen(): return 1
- [C] async def agen(): yield 1
- [D] def async agen(): yield 1

**参考答案**：2

**解析**：在 async def 函数体内使用 yield 即定义异步生成器，它同时实现 __aiter__ 和 __anext__。普通 def + yield 是同步生成器；async def 里只有 return 是协程。

### single_choice · None



- [A] [1, 2]
- [B] [<async_generator object agen at ...>]
- [C] 报错：async for 不能在列表推导中使用
- [D] [1, 2] 但顺序不确定

**参考答案**：0

**解析**：异步生成器可以在异步列表推导中使用，async for 会依次消费，输出 [1, 2]，顺序由生成器 yield 顺序决定。

### single_choice · None



- [A] aclose() 是同步方法，直接调用即可
- [B] 调用 aclose() 会在生成器暂停处抛出 GeneratorExit，可用于清理资源
- [C] aclose() 只能在生成器耗尽后调用
- [D] aclose() 等价于 close()，两者可互换

**参考答案**：1

**解析**：异步生成器的 aclose() 是协程，需 await；它在暂停点注入 GeneratorExit 以触发 finally 清理。同步 close() 不适用于异步生成器。

### single_choice · None



- [A] async for 可以遍历普通列表，只要外层在协程里
- [B] async for 只能遍历实现了异步迭代协议的对象
- [C] async for 内部会自动创建事件循环
- [D] async for 不能用在函数内的 try/finally 中

**参考答案**：1

**解析**：async for 要求对象实现异步迭代协议（__aiter__/__anext__）；列表是同步可迭代对象，普通 for 即可；async for 不会自己创建事件循环，也可正常放在 try/finally 中。

### single_choice · None



- [A] agen() 应该用 return 而不是 yield
- [B] next() 不能用于异步生成器，应使用 await it.__anext__() 或 async for
- [C] range(3) 在异步生成器中不可用
- [D] main() 不是协程函数，会直接报错

**参考答案**：1

**解析**：异步生成器不是同步迭代器，不能调用内置 next()；应 await it.__anext__() 或用 async for 消费。

### multi_choice · None



- [A] __aiter__ 方法
- [B] __anext__ 方法
- [C] 迭代结束时抛出 StopAsyncIteration
- [D] __next__ 方法
- [E] __iter__ 方法

**参考答案**：[0, 1, 2]

**解析**：异步迭代器需实现 __aiter__（返回自身或新迭代器）和 __anext__，耗尽时抛 StopAsyncIteration。__next__/__iter__ 是同步迭代协议，不要求。

### multi_choice · None



- [A] 异步生成器用 async def + yield 定义
- [B] 异步生成器只能通过 async for 或 __anext__ 消费
- [C] 异步生成器支持 asend() 发送值
- [D] 异步生成器可被 send() 直接驱动
- [E] 异步生成器的 aclose() 是协程需 await

**参考答案**：[0, 1, 2, 4]

**解析**：异步生成器定义用 async def+yield；通过 async for/__anext__ 消费；支持 asend()；aclose() 是协程需 await。同步的 send() 不能直接驱动异步生成器。

### multi_choice · None



- [A] 逐条读取网络流式响应（如分块下载）
- [B] 对内存中的大列表做快速排序
- [C] 从数据库游标分批异步拉取记录
- [D] 遍历本地字典的键值对

**参考答案**：[0, 2]

**解析**：异步迭代适合 I/O 密集、流式/分批获取的数据源（网络流、异步数据库游标）。本地列表排序、遍历字典是同步数据，用普通方式即可。
