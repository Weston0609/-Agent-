# s3u5l1 `asyncio.TaskGroup`（任务组）是 Py / 结构化并发（Structured Concurrency）：从零到工程级

> 来源 `content/lessons/s3u5l1.json`

## py.async.taskgroup

## 一句话直觉

`asyncio.TaskGroup`（任务组）是 Python 3.11 引入的高层并发原语（high-level API），它让你能像写 `with open(...)` 一样，用一个 `async with` 块**同时启动一堆任务（Task）、等它们全部结束、并在任意一个失败时自动取消其余任务**——不用再手写 `gather` 加异常处理，从根上避免“孤儿任务”和“异常被吞掉”这两大并发噩梦。

> 为什么值得学：并发代码最大的坑不是“跑不快”，而是“人跑了任务还在偷偷跑”和“一个任务炸了其他任务还在假装没事”。TaskGroup 用结构化的方式（structured concurrency，结构化并发）把这两件事一次性解决。

---

## 1. 为什么需要 TaskGroup：从 `gather` 的痛点说起

在讲 TaskGroup 之前，先看老办法 `asyncio.gather`（收集器）的问题。

```python
import asyncio

async def ok(n):
    await asyncio.sleep(n)
    return f"ok-{n}"

async def boom():
    await asyncio.sleep(0.5)
    raise ValueError("出错了")

async def main():
    # gather 默认会在第一个异常时抛出，但剩下的任务仍在后台悄悄执行
    results = await asyncio.gather(ok(1), boom(), ok(3))
    print(results)

asyncio.run(main())
```

`gather` 的问题：
- 一个任务失败，其余任务**不会被取消**，可能继续消耗资源、往数据库里写数据。
- 如果设置 `return_exceptions=True`，异常被塞进结果列表，**很容易被忘掉**，变成“静默失败”。
- 任务和它们的生命周期不绑定在一个代码块里，控制流是散的。

`TaskGroup` 的设计目标是让“启动/等待/取消/异常传播”这四件事**粘在同一个 `async with` 块上**，这就叫 **结构化并发（structured concurrency）**：子任务的生命周期不允许超出父代码块。

---

## 2. 最小可用示例：`async with TaskGroup()`

`TaskGroup` 是 `asyncio` 模块下的一个类。用法三步走：`async with` 打开 → `create_task` 派活 → 块结束时自动等待全部完成。

```python
import asyncio

async def worker(name, delay):
    await asyncio.sleep(delay)
    print(f"{name} 完成，用时 {delay}s")
    return name

async def main():
    async with asyncio.TaskGroup() as tg:      # 1. 打开任务组
        tg.create_task(worker("A", 1))          # 2. 派发任务（立即开始调度）
        tg.create_task(worker("B", 2))
        tg.create_task(worker("C", 0.5))
    # 3. 执行到这里时，上面 3 个任务已全部结束
    print("全部任务结束")

asyncio.run(main())
```

关键点：`async with` 的 **`__aexit__`** 会等待所有子任务；块内任何代码都不用显式 `await` 这些任务，**离开块本身就是一次等待**。

---

## 3. 异常传播：一个失败，全组取消

这是 TaskGroup 最核心的价值。**任意一个子任务抛出未被捕获的异常，TaskGroup 会取消组内其他所有任务，然后把这个异常（或多个异常打包成 `ExceptionGroup`）向外抛出。**

```python
import asyncio

async def ok(n):
    try:
        await asyncio.sleep(n)
        print(f"ok-{n} 完成")
    except asyncio.CancelledError:
        print(f"ok-{n} 被取消")
        raise  # 取消异常不要吞掉

async def boom():
    await asyncio.sleep(0.3)
    raise ValueError("我炸了")

async def main():
    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(ok(2))
            tg.create_task(boom())
            tg.create_task(ok(5))
    except* ValueError as eg:            # 注意：Python 3.11+ 的 except* 语法
        print(f"捕获到 {len(eg.exceptions)} 个 ValueError: {eg.exceptions}")
    print("main 继续运行")

asyncio.run(main())
```

输出大致是：
```
ok-2 被取消
捕获到 1 个 ValueError: (ValueError('我炸了'),)
main 继续运行
```

三个要点：
1. **`boom` 抛异常后，`ok(2)` 和 `ok(5)` 会被自动取消**（你会看到 `CancelledError`）。
2. 异常被打包成 **`ExceptionGroup`（异常组）**，用 `except*` 捕获（这是 3.11 与 TaskGroup 一起引入的语法）。
3. 多个任务同时失败时，`ExceptionGroup` 会包含所有的异常，**一个都不丢**。

---

## 4. 并发与限流：`create_task` 不会自动限制并发

TaskGroup 本身**不限制并发数**。如果你需要“一次最多跑 N 个”，得配合 **`asyncio.Semaphore`（信号量）**。

```python
import asyncio

async def fetch(i, sem):
    async with sem:                 # 同时最多 N 个任务进入临界区
        print(f"开始 {i}")
        await asyncio.sleep(1)
        print(f"结束 {i}")

async def main():
    sem = asyncio.Semaphore(3)       # 最多 3 个并发
    async with asyncio.TaskGroup() as tg:
        for i in range(10):
            tg.create_task(fetch(i, sem))

asyncio.run(main())
```

对比一下：`asyncio` 里的“并发”是**协作式**的——只有遇到 `await` 且等待未就绪时，控制权才交还给事件循环（event loop）。所以**CPU 密集（CPU-bound）的任务不适合放进 TaskGroup**，那应该用 `ProcessPoolExecutor`。

---

## 5. 工程级要点与对比小结

| 维度 | `asyncio.gather` | `asyncio.TaskGroup` |
|---|---|---|
| 引入版本 | 3.4+ | **3.11+** |
| 一失败其他任务 | 继续跑（除非手动取消） | **自动全部取消** |
| 异常表现 | 首个异常 / 结果列表里混杂 | **`ExceptionGroup`**，一个不漏 |
| 生命周期绑定 | 松（裸任务可能逃逸） | **紧**（结构化并发） |
| 取消语义 | 需手动 `cancel()` | `__aexit__` 统一处理 |

工程建议：
- **新代码优先用 `TaskGroup`**，除非有特殊兼容性需求（如需要兼容 3.10）。
- 子任务里如果需要“清理资源”，用 `try/finally` 或 `contextlib.aclosing`，**不要吞 `CancelledError`**。
- 捕获异常**一定用 `except*`**；普通 `except ValueError` 捕不到 `ExceptionGroup`。
- TaskGroup 的任务必须在组内启动，**不要用外部已存在的 Task 塞进去**（不支持）。

---

## 动手练习

写一个脚本 `taskgroup_demo.py`，实现以下需求：

1. 有 5 个模拟“下载”任务的协程 `download(url, delay)`，每个任务随机 sleep 0.2~1.5 秒后返回 `f"{url} 下载完成"`，并打印完成信息。
2. 用 `TaskGroup` 同时启动这 5 个任务。
3. **故意让其中 URL 为 `"http://bad"` 的那个任务在 sleep 后抛出 `RuntimeError("服务器 500")`**。
4. 在 `main()` 里用 `except* RuntimeError` 捕获，打印捕获到的异常个数。
5. 观察并解释：其他 4 个任务的输出表明它们发生了什么？为什么？

**进阶**：加一个 `asyncio.Semaphore(2)`，把并发数限制到 2，观察输出顺序的变化。

```python
import asyncio
import random

async def download(url: str, delay: float) -> str:
    try:
        await asyncio.sleep(delay)
        if url == "http://bad":
            raise RuntimeError("服务器 500")
        msg = f"{url} 下载完成（{delay:.2f}s）"
        print(msg)
        return msg
    except asyncio.CancelledError:
        print(f"{url} 被取消")
        raise

async def main() -> None:
    urls = [f"http://site{i}" for i in range(4)] + ["http://bad"]
    sem = asyncio.Semaphore(2)

    async def bounded(u: str) -> str:
        async with sem:
            return await download(u, random.uniform(0.2, 1.5))

    try:
        async with asyncio.TaskGroup() as tg:
            for u in urls:
                tg.create_task(bounded(u))
    except* RuntimeError as eg:
        print(f"捕获到 {len(eg.exceptions)} 个 RuntimeError: {eg.exceptions}")

    print("main 结束")

if __name__ == "__main__":
    asyncio.run(main())
```

## py.async.structured_concurrency

# 结构化并发（Structured Concurrency）：从零到工程级

> **一句话直觉**：就像 `if`/`for` 会给代码块划定清晰的边界一样，结构化并发要求**每个并发任务都必须有一个明确的“父作用域”**——谁创建、谁等待、谁负责传播异常与取消，全都有迹可循，从而杜绝“幽灵后台任务”和“静默吞异常”。

---

## 1. 为什么需要“结构化”并发？

在早期异步编程里，你常常这样写：

```python
asyncio.create_task(worker())   # 扔出去就不管了
```

问题随之而来：
- 任务失败时异常被静默吞掉；
- 主程序退出后，任务还在后台悄悄跑；
- 想统一取消所有任务，需要手动维护一堆 `Task` 引用；
- 程序出现“任务泄漏”（task leak），资源无法释放。

**结构化并发（Structured Concurrency）** 的核心思想：并发任务必须像代码块一样，有一个确定的**生命周期作用域**。父作用域不结束，子任务不能“逃逸”；子任务出错，父作用域必须感知。

Python 的 `asyncio` 提供了两个关键 API 来实现这一思想：
- `asyncio.TaskGroup`（3.11+）：**承诺语义**——要么全部成功，要么一起取消。
- `asyncio.timeout` / `asyncio.timeout_at`（3.11+）：为作用域施加时间边界。

---

## 2. 并发单元：Coroutine、Task、Future

- **协程（Coroutine）**：`async def` 定义的函数，调用后返回一个协程对象，**必须被 await 或被包装成 Task 才会执行**。
- **任务（Task）**：`asyncio.create_task()` 或 `TaskGroup.create_task()` 把协程包装为 Task，交给事件循环（event loop）调度。
- **未来（Future）**：一个“占位符”，表示将来会有结果；Task 是 Future 的子类。

```python
import asyncio

async def hello(name: str) -> str:
    await asyncio.sleep(0.1)
    return f"hi, {name}"

async def main():
    coro = hello("world")          # 只是协程对象，还没执行
    task = asyncio.create_task(coro)  # 交给事件循环
    print(await task)               # 等待结果

asyncio.run(main())
```

---

## 3. TaskGroup：结构化的核心

**关键结论**：`async with asyncio.TaskGroup() as tg:` 建立的作用域退出时，**会自动等待里面所有 task 完成**；若任一 task 抛异常，其余 task 会被取消，异常以 `ExceptionGroup` 形式抛出。

```python
import asyncio

async def fetch(name: str, delay: float, fail: bool = False):
    await asyncio.sleep(delay)
    if fail:
        raise RuntimeError(f"{name} 失败")
    print(f"{name} 完成")
    return name

async def main():
    async with asyncio.TaskGroup() as tg:
        tg.create_task(fetch("A", 0.2))
        tg.create_task(fetch("B", 0.1))
        tg.create_task(fetch("C", 0.3))
    # 直到 A、B、C 全部完成才会走到这里
    print("全部结束")

asyncio.run(main())
```

失败场景演示：

```python
async def main():
    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(fetch("A", 0.5))       # 会被取消
            tg.create_task(fetch("B", 0.1, fail=True))
    except* RuntimeError as eg:
        for e in eg.exceptions:
            print("捕获到:", e)

asyncio.run(main())
```

注意使用的是 `except*`（异常组语法），这是与 `TaskGroup` 配套的异常处理方式。

---

## 4. 为作用域设定边界：超时与取消

**关键结论**：`asyncio.timeout()` 给一段代码块加“秒表”；超时会向内部所有任务抛出 `CancelledError`，退出后抛出 `TimeoutError`。它天然和 `TaskGroup` 组合。

```python
import asyncio

async def slow():
    await asyncio.sleep(10)

async def main():
    try:
        async with asyncio.timeout(1):
            async with asyncio.TaskGroup() as tg:
                tg.create_task(slow())
                tg.create_task(slow())
    except TimeoutError:
        print("整体超时，所有子任务已被取消")

asyncio.run(main())
```

**取消（cancellation）** 在结构化并发中是“合作式”的：任务需要在 `await` 点响应 `CancelledError`。切勿在 `except CancelledError` 中吞掉它，否则结构化语义会被破坏。

---

## 5. 工程级实践建议

- **不要裸用 `asyncio.create_task()`**：优先用 `TaskGroup.create_task()`，让生命周期受控。
- **作用域嵌套**：内层 TaskGroup 退出时保证子任务完毕，外层再继续，天然形成树状结构。
- **异常用 `except*`**：从 `ExceptionGroup` 里按类型提取错误。
- **超时放在 TaskGroup 外或内**：`timeout` 在外可保证整体时限；在内可对子任务单独限时。
- **配合队列（Queue）做生产者/消费者**：用 `tg.create_task(producer())` 和 `tg.create_task(consumer())` 在同一作用域内成对出现，作用域退出即代表整条流水线结束。

```python
import asyncio

async def producer(q: asyncio.Queue):
    for i in range(5):
        await q.put(i)
        await asyncio.sleep(0.05)
    await q.put(None)  # 结束信号

async def consumer(q: asyncio.Queue):
    while True:
        item = await q.get()
        if item is None:
            return
        print("消费:", item)

async def main():
    q: asyncio.Queue = asyncio.Queue()
    async with asyncio.TaskGroup() as tg:
        tg.create_task(producer(q))
        tg.create_task(consumer(q))
    print("流水线完成")

asyncio.run(main())
```

---

## 动手练习

**任务**：写一个“并发抓取 N 个 URL”的脚本（可用 `asyncio.sleep` 模拟网络延迟）。

要求：
1. 使用 `async with asyncio.TaskGroup() as tg:` 并发启动 5 个模拟抓取任务；
2. 每个任务随机延迟 0.1~0.5 秒，第二个人为抛错；
3. 用 `except*` 捕获错误并打印所有失败的 URL；
4. 用 `asyncio.timeout(1)` 给整体流程加 1 秒超时；
5. 打印每个任务的实际耗时与总耗时。

提示骨架：

```python
import asyncio, time, random

async def fake_fetch(url: str) -> str:
    await asyncio.sleep(random.uniform(0.1, 0.5))
    if "bad" in url:
        raise RuntimeError(f"{url} 抓取失败")
    return url

async def main():
    urls = ["u1", "u2", "bad-u3", "u4", "u5"]
    start = time.perf_counter()
    try:
        async with asyncio.timeout(2):
            async with asyncio.TaskGroup() as tg:
                for u in urls:
                    tg.create_task(fake_fetch(u))
    except* RuntimeError as eg:
        for e in eg.exceptions:
            print("错误:", e)
    except TimeoutError:
        print("总超时")
    print("总耗时:", time.perf_counter() - start)

asyncio.run(main())
```

**验收标准**：
- 任务确实并发（总耗时近似于最慢任务，而非累加）；
- 失败 URL 通过 `except*` 被打印；
- 超时后所有任务被取消，程序正常退出，无 `Task was destroyed but it is pending` 警告。


---

## 本课题目

### single_choice · None



- [A] asyncio.gather()
- [B] asyncio.create_task()
- [C] asyncio.TaskGroup
- [D] asyncio.run()

**参考答案**：2

**解析**：TaskGroup 是 asyncio 中的结构化并发原语，能统一管理一组任务的启动与等待，并在任一子任务失败时取消其余子任务。gather 不会自动取消其余任务；create_task 只创建单个任务；run 用于运行顶层协程。

### single_choice · None



- [A] 它只能使用同步上下文管理器 with 语法
- [B] 它必须使用 async with 语法进入
- [C] 它可以直接用 await 调用，不需要 anync with
- [D] 它只能管理一个任务

**参考答案**：1

**解析**：TaskGroup 是异步上下文管理器，需要用 async with 进入。它可管理多个任务，不能直接 await 调用，也不是同步上下文管理器。

### single_choice · None



- [A] TaskGroup 可以重复进入 async with 使用
- [B] TaskGroup 的一次 async with 块退出后，不应再向其中添加任务
- [C] TaskGroup 必须在模块顶层创建
- [D] TaskGroup 只能用于 Python 3.6 以下版本

**参考答案**：1

**解析**：TaskGroup 与一次 async with 块绑定，退出后不应再添加任务。它是在 Python 3.11 引入的，需在异步上下文中使用。

### single_choice · None



- [A] 在子任务失败时取消其余任务
- [B] 通过 create_task 添加任务
- [C] 等待所有子任务完成
- [D] 自动为每个任务设置超时时间

**参考答案**：3

**解析**：TaskGroup 不自动设置每个任务的超时时间。超时需要通过 asyncio.wait_for 或 asyncio.timeout 等方式自行处理。其他三项都是 TaskGroup 的能力。

### single_choice · None



- [A] asyncio.TaskGroup
- [B] asyncio.gather
- [C] asyncio.StructuredConcurrency
- [D] asyncio.TaskManager

**参考答案**：1

**解析**：TaskGroup 在 Python 3.11 才引入，之前常用 asyncio.gather 或手动创建任务后再等待。StructuredConcurrency 和 TaskManager 不是标准库 API。

### single_choice · None



- [A] create_task 不是 TaskGroup 的方法
- [B] TaskGroup 需要使用 async with 而不是 with
- [C] coro() 应该直接 await
- [D] TaskGroup 不能创建任务

**参考答案**：1

**解析**：TaskGroup 是异步上下文管理器，必须使用 async with 进入。create_task 是 TaskGroup 的方法，coro() 用于创建任务是正确的。

### single_choice · None



- [A] 忽略取消，继续运行
- [B] 将 CancelledError 作为异常组的一部分传播
- [C] 自动重启被取消的任务
- [D] 把取消转换为 TimeoutError

**参考答案**：1

**解析**：如果子任务被取消，TaskGroup 会将 CancelledError 传播，可能以异常组形式出现。不会忽略取消、重启任务或转换为 TimeoutError。

### single_choice · None



- [A] 仍然检测到异常并取消其他任务
- [B] 认为该任务成功完成，不影响其他任务
- [C] 抛出 RuntimeError
- [D] 无限等待该任务

**参考答案**：1

**解析**：如果子任务内部自行处理了异常且正常返回，TaskGroup 会认为该任务成功完成，不会因为该任务失败而取消其他任务。

### single_choice · None



- [A] 结构化并发
- [B] 多进程并行
- [C] 线程池调度
- [D] 事件循环策略

**参考答案**：0

**解析**：TaskGroup 是结构化并发（structured concurrency）的体现，用于将一组任务的生命周期绑定到一个作用域中。它不涉及多进程、线程池或事件循环策略。

### single_choice · None



- [A] 抛出 ValueError
- [B] 正常退出，不抛出异常
- [C] 阻塞等待，直到超时
- [D] 进入无限循环

**参考答案**：1

**解析**：空的 TaskGroup 在退出时会正常退出，不会抛出异常，也不会阻塞。TaskGroup 并不要求至少有一个任务。

### single_choice · None



- [A] TaskGroup 只会传播第一个失败的异常，忽略其余
- [B] TaskGroup 会收集所有失败任务的异常并以 ExceptionGroup 形式抛出
- [C] TaskGroup 不会传播异常，需要手动检索任务状态
- [D] TaskGroup 只传播取消异常

**参考答案**：1

**解析**：TaskGroup 会收集多个失败任务的异常，并以 ExceptionGroup（或 BaseExceptionGroup）的形式统一抛出，而不是只传播第一个。

### single_choice · None



- [A] 它会返回一个 Task 对象
- [B] 它返回协程对象
- [C] 它返回 None 且无法获取任务状态
- [D] 它只能在同步函数中调用

**参考答案**：0

**解析**：TaskGroup.create_task() 会返回一个 asyncio.Task 对象，可以用于后续检查状态或获取结果。它必须在异步上下文中调用。

### single_choice · None



- [A] group.add(coro())
- [B] group.create_task(coro())
- [C] group.submit(coro())
- [D] group.run(coro())

**参考答案**：1

**解析**：TaskGroup 提供 create_task() 方法来创建并添加任务。add、submit、run 都不是 TaskGroup 的 API。

### single_choice · None



- [A] TaskGroup 会强制终止它
- [B] async with 退出会一直等待该任务结束
- [C] TaskGroup 会跳过该任务
- [D] 事件循环会崩溃

**参考答案**：1

**解析**：TaskGroup 在退出时需要等待所有子任务结束。如果某个任务不响应取消，async with 退出会一直等待，可能导致阻塞。不会强制终止或跳过。

### single_choice · None



- [A] 其余子任务继续运行直到自然结束
- [B] TaskGroup 会立即取消其余所有子任务
- [C] 异常被静默忽略
- [D] TaskGroup 会重启失败的任务

**参考答案**：1

**解析**：TaskGroup 在任一子任务失败时，会取消该组中其余尚未完成的任务，并将异常以 ExceptionGroup 形式抛出。不会静默忽略或重启任务。

### single_choice · None



- [A] 直接抛出原始异常
- [B] BaseExceptionGroup 或 ExceptionGroup
- [C] RuntimeError
- [D] SystemExit

**参考答案**：1

**解析**：当 TaskGroup 中有多个任务失败时，会以 BaseExceptionGroup/ExceptionGroup 的形式抛出，可能包含多个异常。单个异常也会被包装进 ExceptionGroup。

### single_choice · None



- [A] 立即抛出 TimeoutError
- [B] 正常退出代码块，继续执行后续代码
- [C] 自动调用 asyncio.run()
- [D] 所有任务结果被丢弃

**参考答案**：1

**解析**：当所有子任务成功完成时，TaskGroup 会让 async with 正常退出，执行流程继续。不会抛出异常，也不会自动调用 asyncio.run。

### single_choice · None



- [A] TaskGroup 会自动把结果汇总成列表返回
- [B] 在任务中把结果写入外部变量或集合
- [C] TaskGroup.results() 会返回结果列表
- [D] await taskgroup 会返回结果元组

**参考答案**：1

**解析**：TaskGroup 不直接返回结果列表，但创建出的任务对象可通过 task.result() 获取结果，常见做法是在任务中把结果写入外部容器。TaskGroup 本身没有 results() 方法。

### single_choice · None



- [A] 两者在子任务失败时的取消行为完全相同
- [B] gather 默认不会自动取消其余任务，TaskGroup 会在失败时取消其余任务
- [C] gather 是异步上下文管理器，TaskGroup 不是
- [D] TaskGroup 不能与 async with 一起使用

**参考答案**：1

**解析**：gather 默认在某个任务失败时不会自动取消其他任务；TaskGroup 会在子任务失败时取消其余子任务。两者在取消语义上有明显区别。

### single_choice · None



- [A] async with asyncio.TaskGroup() as tg:
      tg.create_task(coro1())
      tg.create_task(coro2())
- [B] with asyncio.TaskGroup() as tg:
      tg.add_task(coro1())
      tg.add_task(coro2())
- [C] tg = asyncio.TaskGroup()
  tg.run(coro1())
  tg.run(coro2())
  await tg
- [D] await asyncio.TaskGroup([coro1(), coro2()])

**参考答案**：0

**解析**：TaskGroup 需要用 async with 进入，并用 create_task() 添加任务。其他选项使用了不存在的 API 或错误的进入方式。

### single_choice · None



- [A] 用 .exceptions 属性获取所有子异常
- [B] 直接用 except ValueError 捕获所有子异常
- [C] ExceptionGroup 不能遍历
- [D] 只能重新抛出，无法检查

**参考答案**：0

**解析**：ExceptionGroup 有 exceptions 属性，可以获取组内所有异常。不能直接用 except ValueError 捕获所有子异常（除非使用 except* 语法），但可以遍历 exceptions。

### single_choice · None



- [A] 任务的生命周期不应超过创建它的代码块，父任务离开作用域前必须等待或取消所有子任务
- [B] 多个协程必须运行在同一个事件循环中才能并发执行
- [C] 使用 asyncio.gather 就是结构化并发的一种实现
- [D] 并发任务的异常应当被立即忽略，以免影响其他任务

**参考答案**：0

**解析**：结构化并发的核心是控制流嵌套与生命周期绑定：子任务不能存活于父任务作用域之外，父级退出前必须对其负责（等待或取消）。B 项混淆了并发与结构化，C 项中 asyncio.gather 只是聚集任务，并不自动保证生命周期绑定与取消传播，D 项与结构化并发「异常需向上传播并处理」的原则相反。

### single_choice · None



- [A] 继续正常执行完毕，异常被静默丢弃
- [B] 被取消（收到取消信号），父级在退出作用域时把异常向上传播
- [C] 自动重试直到成功
- [D] 脱离父作用域成为后台任务

**参考答案**：1

**解析**：结构化并发强调错误传播：一个子任务失败通常会导致同一作用域内其他兄弟任务被取消，父级在退出作用域时抛出异常。这避免了「孤儿任务」和无感知的失败。A 项违背错误传播原则，C 项无此自动重试语义，D 项正是结构化并发要消除的现象。

### single_choice · None



- [A] 子作用域内的任务可以逃逸到父作用域之外继续运行
- [B] 子作用域必须先于父作用域结束，形成类似调用栈的嵌套结构
- [C] 嵌套会降低协程数量上限
- [D] 嵌套作用域会共享同一个 Task 对象

**参考答案**：1

**解析**：结构化并发的嵌套类似函数调用栈：内层作用域必须先退出并完成其任务，外层才能退出，从而保证任务生命周期不逃逸。每个 create_task 产生的仍是独立 Task 对象，嵌套也不会改变协程数量上限。

### single_choice · None



- [A] 只抛出第一个异常，其余丢弃
- [B] 抛出 ExceptionGroup（可能嵌套多个异常）
- [C] 把所有异常拼接成一个字符串
- [D] 返回一个包含异常的列表而不抛出

**参考答案**：1

**解析**：TaskGroup 会把多个子任务的失败聚合成 ExceptionGroup（可用 except* 语法分别处理）。A 会丢失信息，C、D 不符合 Python 的异常抛出语义。

### multi_choice · None



- [A] 任务不再泄漏，父级退出时保证子任务已处理完毕
- [B] 取消信号能沿作用域层级正确传播
- [C] 异常有明确的归属，便于统一处理
- [D] 并发任务的执行顺序被严格保证为代码书写顺序
- [E] 能自动修复子任务中的业务逻辑错误

**参考答案**：[0, 1, 2]

**解析**：结构化并发带来生命周期绑定、取消传播、异常归属三方面收益。它不保证任务按书写顺序执行（并发本质决定顺序不确定），也不会修复业务逻辑错误。

### multi_choice · None



- [A] 使用裸 create_task 且不保存引用、不等待，可能导致泄漏
- [B] 泄漏的任务可能在主逻辑结束后仍继续运行，导致资源占用或结果丢失
- [C] 结构化并发通过作用域绑定来防止任务泄漏
- [D] 只要使用了 asyncio.run 就一定不会发生任务泄漏
- [E] 任务泄漏只会在多线程中发生，与 asyncio 无关

**参考答案**：[0, 1, 2]

**解析**：任务泄漏源于任务失去归属：裸 create_task 不保存引用、不等待时会泄漏；泄漏任务可能在主流程结束后运行，造成资源或结果问题。结构化并发用作用域绑定解决。asyncio.run 只保证主协程结束并做一些清理，不保证所有游离任务被妥善处理；任务泄漏与线程无关，是异步任务的常见问题。

### multi_choice · None



- [A] 使用 async with 的 TaskGroup 作用域创建并等待所有子任务
- [B] 父级在退出作用域前确保取消或等待所有子任务
- [C] 把取消异常当作普通业务异常直接吞掉
- [D] 让子任务的生命周期始终不超过创建它的作用域
- [E] 把子任务引用存到全局变量以便随时访问，不关心何时结束

**参考答案**：[0, 1, 3]

**解析**：结构化并发要求作用域绑定、退出前处理子任务、生命周期不逃逸。吞掉 CancelledError 会破坏取消传播，是反模式；全局保存引用而不关心结束时间则是典型的非结构化做法。

### fill_blank · None



**参考答案**：["TaskGroup", "asyncio.TaskGroup"]

**解析**：asyncio.TaskGroup 是 Python 3.11 引入的结构化并发原语，通过 async with 进入作用域，用 create_task 创建子任务，退出时保证所有子任务完成并聚合异常。

### fill_blank · None



**参考答案**：["CancelledError", "asyncio.CancelledError"]

**解析**：取消通过向协程抛出 asyncio.CancelledError 实现。正确处理方式是做资源清理后重新抛出（或让异常自然传播），静默吞掉会破坏取消语义并导致任务「卡死」。

### code_reading · None



**参考答案**：不会打印 'done'。因为 B 任务抛出 ValueError 后，TaskGroup 会取消同一作用域内的其他子任务（A 会被取消），并在退出 async with 时以 ExceptionGroup 形式把异常传播出去，导致 main 提前抛出异常，因此 print('done') 不会执行。A 会在取消前执行 finally 清理（打印 'A cleanup'），但不会返回正常结果。

**解析**：该题考察结构化并发的「一处失败，整组取消并传播异常」语义，以及 finally 中清理逻辑仍会执行这一点。

### code_reading · None



**参考答案**：输出 'ok'。sleep(1) 这个后台任务没有被 await、也没有保存引用，当 main 结束、asyncio.run 关闭事件循环时它会被取消/丢弃，属于典型的任务泄漏（fire-and-forget）。它体现了缺乏结构化并发绑定：父级不知道也不负责子任务的结束与异常，可能造成结果丢失或异常无人处理。

**解析**：该题对比非结构化任务与结构化并发的差异：未绑定的任务在父协程结束后被取消，异常无法被感知。若用 TaskGroup 包裹则可保证等待或取消。

### scenario · None



**解析**：参考答案应说明：把三个调用放进同一个结构化并发作用域（如 async with asyncio.TaskGroup()），子任务失败时其余任务被取消，退出作用域前保证整体完成，异常以 ExceptionGroup 抛出并可统一处理；这样消除了后台游离任务，保证结果完整性和异常可感知。关键词覆盖 TaskGroup、作用域、取消、异常组、生命周期。

### single_choice · None



- [A] 异常被自动吞掉，程序安静退出
- [B] 抛出 RuntimeError 并打印 'Task exception was never retrieved' 之类的告警
- [C] child 会被自动重试
- [D] asyncio.run 会捕获异常并返回 None

**参考答案**：1

**解析**：create_task 创建的任务若未被 await、异常未被取回，任务对象被垃圾回收时会打印 'Task exception was never retrieved'。这正体现了「无结构化绑定」带来的问题：父级不知晓子任务的失败。结构化并发通过作用域绑定让父级必须处理子任务异常。

### scenario · None



**解析**：参考答案应指出：该任务脱离了任何作用域，其生命周期不受父级约束，导致主流程结束时可能未完成或被取消（资源没清理），也缺乏对异常和完成状态的统一管理（可能重复清理）。改造方向是把清理逻辑纳入结构化作用域：用 TaskGroup 或显式 await 管理，保证父级退出前等待其完成、取消能正确传播、异常能被感知与处理。

### single_choice · None



- [A] 等所有任务完成后，返回部分结果列表并忽略异常
- [B] 立即向上抛出该异常，其余任务默认不会被自动取消
- [C] 自动取消所有其他任务并抛出异常
- [D] 把异常包装成返回值放入结果列表

**参考答案**：1

**解析**：asyncio.gather 默认在第一个异常发生时立即向上抛出，但并**不**自动取消其他仍然运行的任务——它们会变成游离任务。这与结构化并发「一处失败取消整个作用域」的语义不同，gather 需要手动 cancel 才能达到类似效果。若给 gather 传 return_exceptions=True，则改为收集异常到结果列表。

### single_choice · None



- [A] 它是 asyncio.gather 的别名，行为完全一致
- [B] 它保证在 with 块退出前所有子任务都已结束，且任一子任务失败会取消其余任务并抛出异常组
- [C] 它只支持同时运行两个任务
- [D] 它创建的协程是同步阻塞执行的

**参考答案**：1

**解析**：TaskGroup 是结构化并发的典型实现：退出 with 块时保证所有子任务已完成（等待或取消），子任务失败会取消其余任务并以 ExceptionGroup 形式抛出。它不是 gather 的别名，也不限制任务数量，更不会阻塞事件循环。

### single_choice · None



- [A] 先打印 0.1 再打印 0.2
- [B] 打印 '0.2 0.1'（任务完成顺序不同不影响 result 顺序）
- [C] 抛出异常，因为不能在 with 外访问 result
- [D] 只打印 0.1

**参考答案**：1

**解析**：TaskGroup 在退出 async with 时保证所有任务已完成，因此之后可以安全读取 result()。t1 对应 work(0.2)、t2 对应 work(0.1)，虽然 t2 先完成，但 result() 按各自任务对象取值，打印顺序与变量书写顺序一致，即 '0.2 0.1'。

### single_choice · None



- [A] 子任务继续运行到自然结束
- [B] 子任务被取消，父级在退出作用域前等待它们处理完取消
- [C] 子任务被转移到全局事件循环继续运行
- [D] 子任务立即被强制终止，不允许清理资源

**参考答案**：1

**解析**：取消传播是结构化的：父级取消会传递到子任务，子任务收到 CancelledError 可做清理，父级在退出作用域时等待子任务真正结束。A、C 会产生孤儿任务，D 与「允许清理」的语义矛盾。

### single_choice · None



- [A] 让协程运行速度更快
- [B] 避免任务泄漏、保证取消与异常传播、让任务生命周期与作用域绑定
- [C] 让异步代码变成同步代码
- [D] 消除所有并发错误

**参考答案**：1

**解析**：结构化并发解决的是生命周期与错误管理问题：防止任务泄漏、确保取消传播、让异常有归属（作用域）。它不会提升性能，也不会把异步变同步，更不会消除逻辑错误。

### single_choice · None



- [A] 用 asyncio.wait_for 包裹每个单个任务
- [B] 用 asyncio.timeout 上下文管理器包裹整个任务组的作用域
- [C] 在任务里各自 sleep 限制时间
- [D] 依赖操作系统杀死进程

**参考答案**：1

**解析**：结构化并发把超时也作用在作用域上：用 asyncio.timeout（3.11+）包裹整个 async with 作用域，超时会取消作用域内所有子任务并传播。给每个任务单独 wait_for 无法保证整体时间上限，也不会统一取消。

### single_choice · None



- [A] 结构化并发鼓励大量使用 fire-and-forget 以提升吞吐
- [B] 结构化并发认为无归属的后台任务难以保证取消与错误处理，应显式管理其生命周期
- [C] 结构化并发禁止使用 asyncio.create_task
- [D] 后台任务在结构化并发中会被自动放到独立线程

**参考答案**：1

**解析**：结构化并发强调任务要有明确的父级归属，所以对 fire-and-forget 持谨慎态度：要么放入作用域管理，要么显式持有引用并负责其取消与异常。它不禁止 create_task，只是要求你负责其生命周期。
