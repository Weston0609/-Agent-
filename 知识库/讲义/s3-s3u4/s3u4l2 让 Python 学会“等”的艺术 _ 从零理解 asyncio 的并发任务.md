# s3u4l2 让 Python 学会“等”的艺术 / 从零理解 asyncio 的并发任务

> 来源 `content/lessons/s3u4l2.json`

## py.async.await

# py.async.await：让 Python 学会“等”的艺术

> **一句话直觉**：`await` 就是告诉 Python——“我要等一件事做完，但别傻站着，先去干别的活。”

本讲面向零基础读者，目标是让你从“完全没听过 async”到“能读懂并写出工程级异步代码”。我们会围绕 Python 标准库 `asyncio`（Asynchronous I/O，异步 I/O）逐步展开。

---

## 1. 为什么需要 await？——先看一个痛点

假设你要同时下载 3 张图片，每张耗时 1 秒。

- **同步（synchronous）写法**：串行执行，总耗时 3 秒。
- **异步（asynchronous）写法**：几乎同时发起，总耗时约 1 秒。

关键点在于：等待网络 I/O 时，CPU 其实是空闲的。`await` 的作用就是**把这个空闲时间交还给事件循环（event loop）**，让它去运行别的任务。

术语说明：
- **协程（coroutine）**：用 `async def` 定义的函数，调用后不会立即执行，而是返回一个协程对象。
- **事件循环（event loop）**：负责任务调度的大脑，由 `asyncio.run()` 自动启动。
- **await**：挂起当前协程，等待另一个协程/可等待对象完成，同时把控制权交还事件循环。

```python
import asyncio
import time

# async def 定义一个协程函数
async def download(name: str, seconds: float) -> str:
    print(f"{name} 开始下载")
    # await 挂起当前协程，把控制权交还事件循环
    await asyncio.sleep(seconds)
    print(f"{name} 下载完成")
    return f"{name} 的内容"

async def main():
    start = time.perf_counter()
    # create_task 把协程包装成任务，可并发调度
    tasks = [asyncio.create_task(download(f"图片{i}", 1)) for i in range(1, 4)]
    results = await asyncio.gather(*tasks)  # 并发等待全部完成
    print("结果:", results)
    print(f"总耗时: {time.perf_counter() - start:.2f} 秒")

# 入口：启动事件循环并运行 main 协程
asyncio.run(main())
```

---

## 2. await 到底能“等”什么？

`await` 后面只能接**可等待对象（awaitable）**，主要有三类：

1. **协程对象**：调用 `async def` 函数得到的返回值。
2. **Task（任务）**：用 `asyncio.create_task()` 包装后的协程，会被事件循环调度。
3. **Future（未来对象）**：底层的结果占位符，通常不直接写。

如果你 `await` 一个普通函数返回值（比如 `await time.sleep(1)`），会直接报 `TypeError`。这是一个非常经典的入门坑。

```python
import asyncio

async def add(a: int, b: int) -> int:
    await asyncio.sleep(0.1)  # 模拟异步操作
    return a + b

async def main():
    # 1) await 协程对象
    result = await add(1, 2)
    print("await 协程:", result)

    # 2) await Task
    task = asyncio.create_task(add(3, 4))
    print("await Task:", await task)

    # 3) await Future
    loop = asyncio.get_running_loop()
    future = loop.create_future()
    loop.call_soon(future.set_result, "Future 完成")
    print("await Future:", await future)

asyncio.run(main())
```

---

## 3. await 与并发：不是“多线程”，而是“协作式”

很多人误以为 `async/await` 等于多线程。其实它是**单线程内的协作式并发（cooperative concurrency）**：

- 只有遇到 `await` 时，协程才会让出控制权。
- 如果某个协程里有耗时 CPU 计算且不 await，它会卡住整个事件循环。

所以：**I/O 密集（IO-bound）任务适合 asyncio；CPU 密集（CPU-bound）任务应该用多进程（multiprocessing）。**

```python
import asyncio
import time

async def io_bound(name: str):
    await asyncio.sleep(1)          # 会让出控制权，其他任务可以跑
    return name

async def cpu_bound_bad():
    # 错误示范：这里没有 await，会阻塞整个事件循环
    total = 0
    for i in range(10_000_000):
        total += i
    return total

async def main():
    start = time.perf_counter()
    # 并发跑 3 个 I/O 任务，理论总耗时 ~1 秒
    results = await asyncio.gather(io_bound("A"), io_bound("B"), io_bound("C"))
    print("并发 I/O 结果:", results)
    print(f"并发 I/O 耗时: {time.perf_counter() - start:.2f} 秒")

asyncio.run(main())
```

---

## 4. 工程级要点：超时、异常、取消

在真实项目里，光会 `await` 还不够，你还需要处理：

- **超时（timeout）**：`asyncio.wait_for()` 或 `asyncio.timeout()`。
- **异常（exception）**：`await` 会把协程内部异常重新抛出，用 `try/except` 捕获。
- **取消（cancellation）**：任务可以被 `task.cancel()` 取消，协程内会收到 `asyncio.CancelledError`。

```python
import asyncio

async def risky_task(name: str, delay: float):
    try:
        await asyncio.sleep(delay)
        if name == "B":
            raise ValueError(f"{name} 出错了")
        return f"{name} 成功"
    except asyncio.CancelledError:
        print(f"{name} 被取消")
        raise  # 取消异常应该继续向上抛

async def main():
    # 超时控制
    try:
        result = await asyncio.wait_for(risky_task("A", 2), timeout=0.5)
        print(result)
    except asyncio.TimeoutError:
        print("A 超时了")

    # 异常传播
    try:
        await risky_task("B", 0.1)
    except ValueError as e:
        print(f"捕获异常: {e}")

    # 取消任务
    task = asyncio.create_task(risky_task("C", 5))
    await asyncio.sleep(0.1)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        print("C 已确认取消")

asyncio.run(main())
```

---

## 5. 标准库最小可运行骨架

官方文档给出的 Hello World 结构，是每个异步程序的最小骨架：

```python
import asyncio

async def main():
    print('Hello ...')
    await asyncio.sleep(1)
    print('... World!')

asyncio.run(main())
```

记住三件事：
1. `async def` 定义协程函数。
2. `await` 等待异步操作完成。
3. `asyncio.run()` 是同步世界进入异步世界的入口。

---

## 动手练习

**任务**：写一个异步脚本，模拟“同时请求 5 个 URL”，每个请求耗时随机 0.5~2 秒，要求：

1. 使用 `asyncio.gather()` 并发执行。
2. 每个任务返回 `(url, 耗时)`。
3. 给整体加一个 3 秒超时，超时后打印“整体超时”并取消所有未完成任务。
4. 打印每个任务的结果和总耗时。

提示：可用 `asyncio.sleep(random.uniform(0.5, 2))` 模拟网络延迟，用 `asyncio.wait_for(..., timeout=3)` 控制整体超时。

完成后对比：如果改成同步串行，耗时大约是多少？为什么异步更快？

```python
import asyncio
import random
import time

async def fetch(url: str):
    # 模拟网络请求耗时
    delay = random.uniform(0.5, 2.0)
    await asyncio.sleep(delay)
    return url, round(delay, 2)

async def main():
    urls = [f"https://example.com/{i}" for i in range(1, 6)]
    start = time.perf_counter()
    try:
        # 整体超时 3 秒
        results = await asyncio.wait_for(
            asyncio.gather(*(fetch(u) for u in urls)),
            timeout=3,
        )
        for url, cost in results:
            print(f"{url} -> {cost}s")
    except asyncio.TimeoutError:
        print("整体超时，已取消未完成任务")
    print(f"总耗时: {time.perf_counter() - start:.2f}s")

asyncio.run(main())
```

## py.async.task

# py.async.task：从零理解 asyncio 的并发任务

## 一句话直觉

`asyncio` 让你用**单线程**写出「同时干很多件等待型事情」的程序，而 `Task`（任务）就是把协程交给事件循环去真正并行调度的那个「编排器」。

前置知识：无。本文从 `async def` 讲起，一直讲到工程中如何管理一批任务。

---

## 第 1 节：为什么需要它——同步代码的等待浪费

普通函数遇到 I/O（读文件、请求网络、查数据库）时会**阻塞**（block）：CPU 只能干等。如果同时要请求 10 个接口，同步写法需要 10 倍时间；而它们实际上大部分时间都在等网络。

`asyncio` 的核心思想：**当协程（coroutine）遇到等待点时主动让出控制权**，事件循环（event loop）趁机去跑别的协程。这就是异步 I/O（asynchronous I/O）。

Python 用两个关键字表达这件事：

- `async def`：定义一个协程函数，调用它不会立刻执行，而是返回一个协程对象。
- `await`：在协程内部挂起自己，等另一个协程完成后继续。

```python
import asyncio

async def say(name, delay):
    # await 处会挂起当前协程，把控制权还给事件循环
    await asyncio.sleep(delay)
    print(f"hello {name}")

async def main():
    # 直接依次 await，仍然是串行，总耗时 = 1 + 1 = 2 秒
    await say("A", 1)
    await say("B", 1)

asyncio.run(main())
```

上面这段仍然是串行的——**仅仅写上 `async`，并不会自动并发**。要真正并发，就需要本节的主角：`Task`。

---

## 第 2 节：协程、Task、Future——三个概念的区分

这三个词初学者最容易混，一句话划清边界：

| 名词 | 是什么 | 谁在驱动 |
| --- | --- | --- |
| 协程 coroutine | `async def` 返回的对象，一段待执行的异步逻辑 | 被 `await` 时才跑 |
| 任务 Task | 把协程**交给事件循环立刻开始调度**的包装 | 事件循环 |
| 未来对象 Future | 一个「将来会有结果」的占位符 | 底层由 loop 完成 |

关键点：**`Task` 一旦创建，事件循环就会开始推进它，不需要你 `await`**。这正是并发的来源。

```python
import asyncio

async def work(name, delay):
    await asyncio.sleep(delay)
    return f"{name} done"

async def main():
    # create_task 立即把协程排入事件循环，两个任务开始并发
    t1 = asyncio.create_task(work("A", 1))
    t2 = asyncio.create_task(work("B", 1))

    # await 只是等待结果，不负责“启动”
    r1 = await t1
    r2 = await t2
    print(r1, r2)

asyncio.run(main())  # 总耗时约 1 秒，而不是 2 秒
```

要点：`asyncio.create_task()` 是 Python 3.7+ 推荐写法（旧代码里的 `loop.create_task` 已过时）。

---

## 第 3 节：并发跑一批任务——gather 与 as_completed

实际工程中，任务数量往往不固定（比如 100 个 URL 需要抓取）。这时用列表推导批量创建 Task，再用 `asyncio.gather` 一把收齐。

```python
import asyncio

async def fetch(url_id):
    await asyncio.sleep(0.5)
    return f"data-{url_id}"

async def main():
    # 批量创建任务
    tasks = [asyncio.create_task(fetch(i)) for i in range(5)]

    # gather：等到全部完成，按输入顺序返回结果列表
    results = await asyncio.gather(*tasks)
    print(results)

    # as_completed：谁先完成先拿到谁，适合边跑边处理
    tasks = [asyncio.create_task(fetch(i)) for i in range(5)]
    for coro in asyncio.as_completed(tasks):
        print(await coro)

asyncio.run(main())
```

对比记忆：

- `gather`：等全部完成、保序返回，最常用。
- `as_completed`：完成即回调，适合流式处理。
- `wait`：更底层，可控制 `return_when=...`（如 FIRST_COMPLETED）。

---

## 第 4 节：任务的生命周期与取消

Task 是有状态的，主要状态有：`PENDING` → `RUNNING` → `DONE`（或 `CANCELLED`）。工程中常见需求：超时、取消、异常处理。

```python
import asyncio

async def long_job():
    try:
        await asyncio.sleep(10)
    except asyncio.CancelledError:
        # 被取消时的清理逻辑，注意要重新抛出
        print("cleanup before cancel")
        raise

async def main():
    t = asyncio.create_task(long_job())
    await asyncio.sleep(0.2)

    # 取消任务：被 await 时会抛 CancelledError
    t.cancel()
    try:
        await t
    except asyncio.CancelledError:
        print("task cancelled")

    # 超时控制（Python 3.11+ 推荐 asyncio.timeout 上下文管理器）
    try:
        async with asyncio.timeout(0.5):
            await asyncio.sleep(5)
    except TimeoutError:
        print("timeout")

asyncio.run(main())
```

要点：

- **必须 `await` 或保留对 Task 的引用**，否则任务可能被垃圾回收，出现「任务莫名消失」。
- 捕获 `CancelledError` 后**要么处理完重新 `raise`，要么明确吞掉**，不要静默忽略。
- Python 3.11 起 `asyncio.timeout()` 取代了 `asyncio.wait_for()` 的多数场景。

---

## 第 5 节：工程级模式——TaskGroup 与结构化并发

Python 3.11 引入 `asyncio.TaskGroup`（结构化并发 structured concurrency）：一个 TaskGroup 里的任一任务抛异常，会**自动取消兄弟任务**并把异常聚合成 `ExceptionGroup`。这比 `gather` 更安全，是新一代推荐写法。

```python
import asyncio

async def good(name, delay):
    await asyncio.sleep(delay)
    print(f"{name} ok")

async def bad():
    await asyncio.sleep(0.1)
    raise ValueError("boom")

async def main():
    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(good("A", 0.5))
            tg.create_task(good("B", 0.5))
            tg.create_task(bad())
    except* ValueError as eg:
        # Python 3.11+ 的 ExceptionGroup 语法
        print("caught:", eg.exceptions)

asyncio.run(main())
```

工程建议：

1. 优先用 `TaskGroup`，次选 `gather`，不要手动管 loop。
2. 每个 IO 边界都设超时，别让任务无限挂起。
3. 用 `asyncio.Semaphore` 限制并发数量，避免打爆下游。 ⬇

```python
import asyncio

sem = asyncio.Semaphore(3)  # 最多 3 个并发

async def limited(i):
    async with sem:
        await asyncio.sleep(0.5)
        return i

async def main():
    results = await asyncio.gather(*(limited(i) for i in range(10)))
    print(results)

asyncio.run(main())
```

---

## 小结

- `async def` 定义协程，`await` 挂起自己。
- `asyncio.create_task()` 让协程**真正并发**跑起来。
- `gather` / `as_completed` / `TaskGroup` 是三种批量调度方式。
- 三大工程要点：超时、取消、限流。

```python
import asyncio
import time

# 模拟一个网络请求：耗时 delay 秒后返回结果
async def fake_fetch(url: str, delay: float) -> str:
    await asyncio.sleep(delay)          # 遇到 await 会让出事件循环
    return f"{url} -> 200 ({delay}s)"

async def main():
    start = time.perf_counter()

    # 用 TaskGroup 并发发起 5 个请求，最慢的那个决定总耗时
    results = []
    async with asyncio.TaskGroup() as tg:
        tasks = [
            tg.create_task(fake_fetch(f"https://example.com/{i}", 0.5))
            for i in range(5)
        ]

    # TaskGroup 退出时保证所有任务已完成
    for t in tasks:
        results.append(t.result())

    elapsed = time.perf_counter() - start
    for r in results:
        print(r)
    print(f"total elapsed: {elapsed:.2f}s (远小于 5 * 0.5s)")

if __name__ == "__main__":
    asyncio.run(main())
```


---

## 本课题目

### single_choice · None



- [A] 调用它就会立刻执行函数体内的代码
- [B] 调用它会返回一个协程对象，需要被 await 或交给事件循环调度才会执行
- [C] 它和普通函数完全等价，只是写法不同
- [D] 它内部不能调用普通函数

**参考答案**：1

**解析**：async def 定义的函数是协程函数，直接调用只创建协程对象，不会执行函数体。必须通过 await 或 asyncio.run / create_task 等方式交给事件循环才能真正运行，因此 B 正确。A 是常见的「调用即执行」误解。

### single_choice · None



- [A] C A B D
- [B] A B C D
- [C] C A D B
- [D] A C B D

**参考答案**：0

**解析**：同步代码先执行 print('C')，然后 asyncio.run(main()) 启动事件循环执行 main：先打印 A，await asyncio.sleep(0) 让出控制权但随后继续，打印 B，main 结束后 asyncio.run 返回，最后打印 D。顺序为 C A B D。

### single_choice · None



- [A] await 一个由 async def 函数返回的协程对象
- [B] await 一个 asyncio.Task 对象
- [C] await 一个普通整数 5
- [D] await 一个 asyncio.Future 对象

**参考答案**：2

**解析**：await 只能作用于可等待对象。协程对象、Task、Future 都是可等待的，而普通整数 5 不是，await 5 会抛 TypeError: object int can't be used in 'await' expression。

### multi_choice · None



- [A] 由 async def 函数调用返回的协程对象
- [B] asyncio.create_task 返回的 Task 对象
- [C] asyncio.Future 实例
- [D] 普通生成器对象 generator
- [E] 字符串 'abc'

**参考答案**：[0, 1, 2]

**解析**：可等待对象包括协程对象、Task、Future 以及实现了 __await__ 的对象。普通生成器（用 yield 而非 async def 定义）不是可等待对象；字符串也不是。await 生成器或字符串会报 TypeError。

### multi_choice · None



- [A] 直接在一个协程里顺序写多次 await，多个操作是串行执行的
- [B] 用 asyncio.gather 配合 await 可以让多个协程并发执行
- [C] asyncio.create_task 会把协程包装成 Task 并安排进事件循环，即使不 await 也会被调度（但需保留引用）
- [D] await 会为每个协程自动创建独立线程从而实现并发
- [E] 只有多线程才能真正实现异步并发，协程做不到

**参考答案**：[0, 1, 2]

**解析**：顺序 await 是串行的；gather、create_task 等手段可实现单线程事件循环内的并发。await 不创建线程，协程是协作式并发，无需多线程即可处理 IO 并发。D 和 E 是常见误解。

### multi_choice · None



- [A] 同步阻塞调用会占住事件循环线程，使其他任务无法推进
- [B] await 一个 IO 操作会把控制权交回事件循环，让其他任务得以运行
- [C] 在协程中做 CPU 密集型计算并长时间不 await，会拖慢甚至卡住其他协程
- [D] 只要是协程函数，内部任何耗时操作都不会阻塞事件循环
- [E] await 总是立即完成，不会真正挂起

**参考答案**：[0, 1, 2]

**解析**：协程是协作式的，只有遇到 await 才让出控制权。同步阻塞调用或长时间 CPU 计算若不让出，就会霸占线程，阻塞其他任务。D 忽略了内部阻塞，E 误解了 await 的挂起语义。

### multi_choice · None



- [A] async def 定义的协程函数体中
- [B] async for 循环体内
- [C] async with 语句块内
- [D] 普通 def 函数体中
- [E] 模块顶层直接写 await

**参考答案**：[0, 1, 2]

**解析**：await 只能出现在 async def 协程内部，包括 async for / async with 块中。普通 def 函数体和模块顶层（除非启用某些运行时特性）不能使用 await；在普通函数中写 await 是语法错误。

### fill_blank · None



**参考答案**：["await", "await ", " await"]

**解析**：在协程中等待另一个协程执行，需要在其前面加上 await 关键字。await 表达式会挂起当前协程直到 fetch_data() 执行完成并返回结果，因此结果被赋给 result。

### code_reading · None



**参考答案**：输出顺序为 B 然后 A。原因：gather 并发调度两个任务，二者几乎同时开始等待 sleep。B 的延迟 0.1 秒，先到期所以先打印 B；A 延迟 0.2 秒，后到期打印 A。说明 gather 内部两个任务在单线程事件循环中被并发调度，await 各自挂起，不互相阻塞。

**解析**：gather 将多个协程作为任务并发运行，它们的挂起与恢复由事件循环按各自完成时间调度，因此先完成 sleep 的任务先打印。若改成顺序 await，则会等待 A 完成再执行 B，顺序相反且总耗时相加。

### code_reading · None



**参考答案**：因为 create_task 只是把 helper() 包装成 Task 并安排到事件循环中，它不会等待任务完成就立即返回。因此 main 继续执行 print('done')，此时 helper 可能还没运行完。之后 main 结束，asyncio.run 在退出前会等待挂起的任务完成，才会打印 'helper finished'。这体现了「创建任务」与「await 等待完成」的区别。

**解析**：create_task 是安排任务而非等待任务。若不 await 该 Task 也不保留引用，任务仍可能被调度（但引用丢失可能被垃圾回收提前取消）。若希望等待完成，应写 await t。

### scenario · None



**解析**：顺序 await 本身不会并发；同步库 requests 会阻塞事件循环，使其他协程无法推进。应使用异步 HTTP 库（如 aiohttp/httpx.AsyncClient），并用 asyncio.gather 或 create_task 一次性调度多个请求，让它们在同一事件循环内并发挂起等待。避免在协程里做同步阻塞调用，必要时用 run_in_executor 放到线程池。

### scenario · None



**解析**：同一个协程对象只能被 await 一次，因为它内部有状态，执行完毕或抛异常后即耗尽，再次 await 会抛 RuntimeError。要执行两次需分别调用 fetch() 生成两个新的协程对象，例如 await fetch() 写两次（每次都是新对象），或先保存函数再调用。

### single_choice · None



- [A] asyncio.sleep(1)
- [B] await asyncio.sleep(1)
- [C] yield asyncio.sleep(1)
- [D] asyncio.run(asyncio.sleep(1))

**参考答案**：1

**解析**：await 表达式必须作用于可等待对象，await asyncio.sleep(1) 才能挂起当前协程并等待。直接写 asyncio.sleep(1) 只创建协程对象而不执行；yield 用于生成器；在已运行的事件循环内再调用 asyncio.run 会抛错。

### single_choice · None



- [A] 一个普通的列表 [1, 2, 3]
- [B] 一个由 async def 函数调用后返回的协程对象
- [C] 一个 int 数字
- [D] 一个字符串 'hello'

**参考答案**：1

**解析**：await 只能用于可等待对象，主要包括协程对象、实现了 __await__ 的对象以及 asyncio.Future/Task。列表、数字、字符串都不是可等待对象，await 它们会抛 TypeError。

### single_choice · None



- [A] 正常运行，和协程中一样
- [B] 运行时报错，await 不能出现在普通函数体内
- [C] 语法错误，无法通过编译/解析
- [D] 只有 sleep 为 0 时才能运行

**参考答案**：2

**解析**：await 只能出现在 async def 定义的协程函数内部（或 async for/async with 中），在普通 def 函数体里使用 await 是语法错误，代码在解析阶段就会报 SyntaxError，而不是运行时才报错。

### single_choice · None



- [A] 没有任何问题，两者效果完全一样
- [B] 会抛出异常，无法运行
- [C] 会阻塞事件循环线程，其他协程在这 3 秒内无法推进
- [D] 只会阻塞当前协程，其他协程照常运行

**参考答案**：2

**解析**：time.sleep 是同步阻塞调用，会占住事件循环所在的线程，导致同一线程上的其他协程都无法运行。而 await asyncio.sleep 会挂起当前协程并把控制权交还事件循环，让其他任务继续执行。所以答案是 C。

### single_choice · None



- [A] await 会启动一个新线程去执行目标协程
- [B] await 会挂起当前协程，把控制权交回事件循环，等目标完成后恢复执行
- [C] await 只是注释性质的语法，不影响调度
- [D] await 会立即返回，不等目标完成

**参考答案**：1

**解析**：await 的核心语义是把当前协程挂起，将控制权交还给事件循环，让循环去调度其他任务；当被等待的对象完成后再恢复当前协程继续执行。它并不创建线程，也不是立即返回。

### single_choice · None



- [A] int
- [B] coroutine
- [C] NoneType
- [D] Task

**参考答案**：1

**解析**：调用 async def 函数 work() 只是创建了一个协程对象，并没有等待其执行，因此 result 是协程对象，type 名字为 coroutine。要得到 42 必须写 result = await work()。

### single_choice · None



- [A] 正常运行两次，得到两个结果
- [B] 第二次 await 会抛 RuntimeError，因为协程已被等待过且不能重复等待
- [C] 第二次 await 会重新执行整个协程
- [D] 不会有任何输出，静默失败

**参考答案**：1

**解析**：Python 协程对象是一次性的，一旦被 await 执行完毕（或被取消、抛异常）后就不能再次 await，否则会抛出 RuntimeError: cannot reuse already awaited coroutine。若要多次执行需重新调用协程函数生成新对象。

### single_choice · None



- [A] await 可以在任意函数中使用，asyncio.run 只能用于协程
- [B] asyncio.run 用于启动事件循环并运行顶层协程，await 则用于在协程内部等待其他可等待对象
- [C] 两者是同义词，可以互相替换
- [D] asyncio.run 内部不能调用 await 表达式

**参考答案**：1

**解析**：asyncio.run 是入口，负责创建事件循环并运行传入的顶层协程；await 则是协程内部等待其他可等待对象的语法。二者职责不同，不能互相替换。

### single_choice · None



- [A] 协程对象被创建后会自动开始执行
- [B] Task 是对协程的封装，创建后会被调度执行，而裸协程对象需要被 await 或包装成 Task 才会运行
- [C] Task 只能通过 await 才能创建
- [D] 协程对象和 Task 完全等价，可以互换使用

**参考答案**：1

**解析**：裸协程对象只是可等待对象，调用协程函数不会执行其函数体；只有被 await、包装成 Task 或通过事件循环调度后才会真正运行。Task 会立即被安排到事件循环中调度。

### single_choice · None



- [A] worker start / worker end / main after create
- [B] main after create / worker start / worker end
- [C] worker start / main after create / worker end
- [D] main after create / worker end / worker start

**参考答案**：2

**解析**：create_task 会把 worker 排入事件循环，但当前 main 协程不会立刻被打断，直到遇到 await。因此先打印 'main after create' 之前，worker 先运行到第一个 await（打印 'worker start'），交出控制权后 main 继续打印，最后 worker 恢复打印 'worker end'。

### single_choice · None



- [A] await asyncio.sleep(1)
- [B] await task
- [C] 在协程中调用 time.sleep(1)
- [D] await asyncio.gather(*tasks)

**参考答案**：2

**解析**：time.sleep 是同步阻塞调用，会锁住整个线程，从而阻塞事件循环。其余三个都是可等待操作，会挂起当前协程而非阻塞循环。

### multi_choice · None



- [A] Task 是 Future 的子类
- [B] Task 可以通过 asyncio.ensure_future 创建
- [C] Task 一旦创建就立即同步执行到第一个 await
- [D] 取消 Task 后会抛出 CancelledError 到协程内部
- [E] Task 对象不能被多次 await

**参考答案**：[0, 1, 3]

**解析**：Task 继承自 Future，可由 ensure_future 或 create_task 创建，取消会通过 CancelledError 传播。选项 C 表述不准确：Task 被排入循环调度是异步的，并非 create_task 时同步执行；选项 E 错误，Task 可被多次 await。

### multi_choice · None



- [A] 在协程中执行大量同步计算
- [B] 在协程中调用 requests.get
- [C] 使用 await asyncio.sleep(0) 让出控制权
- [D] 使用 time.sleep 进行等待

**参考答案**：[0, 1, 3]

**解析**：同步计算、requests.get 等同步 IO、time.sleep 都会阻塞事件循环。asyncio.sleep(0) 是主动让出，不会阻塞。

### multi_choice · None



- [A] 调用 cancel() 是请求取消，不是立即终止
- [B] 如果协程捕获了 CancelledError 且不重新抛出，取消可能被吞掉
- [C] 被取消的 Task await 时会抛出 CancelledError
- [D] cancel() 一定会立刻抛出异常到调用点
- [E] 可以使用 asyncio.shield 保护某段协程不被外部取消

**参考答案**：[0, 1, 2, 4]

**解析**：cancel() 只是安排取消；只有在协程下次挂起点才抛出 CancelledError。若被吞掉则取消失效。await 已取消任务会抛 CancelledError。shield 用于保护内部协程。选项 D 错误，cancel 不是同步抛出。

### multi_choice · None



- [A] 协程对象（coroutine object）
- [B] Task 对象
- [C] Future 对象
- [D] 普通列表
- [E] 带 __await__ 方法且返回迭代器的对象

**参考答案**：[0, 1, 2, 4]

**解析**：可等待对象包括协程、Task、Future 以及实现了 __await__ 协议的对象。普通列表不是可等待的。

### multi_choice · None



- [A] 默认值为 False
- [B] 当设为 True 时，异常会作为结果返回而不立即抛出
- [C] 当设为 False 时，第一个异常会传播，但其它任务不会被自动取消
- [D] 当设为 True 时，必须至少有一个任务失败

**参考答案**：[0, 1, 2]

**解析**：gather 的 return_exceptions 默认为 False。为 True 时异常作为结果返回。为 False 时异常传播，其它任务继续运行、不会被 gather 自动取消。选项 D 错误，没有此约束。

### fill_blank · None



**参考答案**：["asyncio.create_task", "asyncio.ensure_future", "create_task", "ensure_future"]

**解析**：create_task 是 Python 3.7 引入的推荐写法，ensure_future 也能把协程转为 Task，语义更通用。

### fill_blank · None



**参考答案**：["gather"]

**解析**：asyncio.gather 用于并发运行可等待对象并收集结果。

### code_reading · None



**参考答案**：A\nB\nA2\nB2

**解析**：create_task 先排入 a，再排入 b，但 main 直到 await t1 才让出控制权。事件循环先运行 a 至 sleep(0)（打印 A），再运行 b 至 sleep(0)（打印 B），随后恢复 a（A2）、恢复 b（B2）。

### scenario · None



**参考答案**：把同步阻塞调用放入线程池执行，通过 loop.run_in_executor 或 asyncio.to_thread 以 await 方式等待，从而释放事件循环。

**解析**：同步调用会阻塞事件循环，应使用 run_in_executor 或 asyncio.to_thread 丢到线程池，主循环可继续调度其它协程。

### single_choice · None



- [A] gather 会串行执行传入的协程，create_task 才会并发
- [B] gather 会并发调度传入的可等待对象并返回结果列表，create_task 只是包装单个协程为 Task
- [C] 两者都立即返回结果而不需要 await
- [D] gather 只能接受 Task，不能接受裸协程

**参考答案**：1

**解析**：asyncio.gather 接受多个可等待对象并并发调度，返回聚合结果；create_task 只把单个协程包装成 Task 并排入循环。gather 也能接受裸协程。

### single_choice · None



- [A] 调用 task.stop()
- [B] 调用 task.cancel()，并在协程内部正确处理 CancelledError
- [C] 直接 del task 对象
- [D] 调用 task.close()

**参考答案**：1

**解析**：Task 没有 stop() 或 close() 方法。取消通过 cancel() 请求，会在协程挂起点抛出 CancelledError。删除引用不会取消任务，反而可能造成任务悬挂。

### single_choice · None



- [A] 直接 pass 忽略即可
- [B] 记录日志后 raise 重新抛出，或使用 try/finally 保证清理后再传播
- [C] 把 CancelledError 转换为普通异常再抛出
- [D] 将 CancelledError 替换为 RuntimeError

**参考答案**：1

**解析**：CancelledError 在 Python 3.8+ 继承自 BaseException。捕获后如果不重新抛出，会吞掉取消信号，破坏取消机制。正确做法是清理资源后重新 raise。

### single_choice · None



- [A] 它等价于 gather，但语法更短
- [B] 它保证组内任一任务出错时，其余任务会被取消并等待结束，实现结构化并发
- [C] 它只能在 Python 3.6 中使用
- [D] 它不支持取消操作

**参考答案**：1

**解析**：TaskGroup（Python 3.11+）提供结构化并发：当组内某个任务异常退出时，会取消同组其它任务并等待全部结束，再抛出 ExceptionGroup。这是它与 gather 的一个重要区别。

### single_choice · None



- [A] 它是阻塞式睡眠，会卡住事件循环
- [B] 它是非阻塞挂起，会把控制权让给事件循环，其它任务可继续执行
- [C] 它必须在 Task 外调用
- [D] 它的作用是让当前线程 sleep

**参考答案**：1

**解析**：asyncio.sleep 是可等待对象，挂起当前协程并把控制权交还事件循环，不会阻塞整个线程。而 time.sleep 才是阻塞线程。

### single_choice · None



- [A] 它可以在已有事件循环运行时再次调用
- [B] 它创建一个新的事件循环，运行传入的协程直到结束，随后关闭循环
- [C] 它不会关闭事件循环
- [D] 它用于把普通函数变为协程

**参考答案**：1

**解析**：asyncio.run 会创建新事件循环、运行顶层协程、收尾后关闭循环。若当前线程已有运行中的循环，会抛出 RuntimeError。它不改变函数性质。

### single_choice · None



- [A] 会，因为 Task 已创建
- [B] 不一定，main 返回后 asyncio.run 会关闭循环，未完成的 Task 可能被取消
- [C] 不会，因为 create_task 返回的是协程
- [D] 会，因为 Task 会自动等待

**参考答案**：1

**解析**：创建 Task 只代表排入调度，不保证其执行完毕。asyncio.run 在顶层协程结束后会取消未完成的任务并关闭循环，因此可能出现任务被截断。

### single_choice · None



- [A] 裸协程对象
- [B] asyncio.Task 对象
- [C] 生成器
- [D] 普通函数

**参考答案**：1

**解析**：裸协程被 await 后即被耗尽，再次 await 会抛 RuntimeError。Task 可被多次 await，会得到相同结果或抛出相同异常。生成器不是可等待对象（除非被装饰）。
