# s3u6l3 Python 异步优雅关闭（Graceful Shutdown）

> 来源 `content/lessons/s3u6l3.json`

## py.async.graceful_shutdown

# Python 异步优雅关闭（Graceful Shutdown）

> 一句话直觉：程序总有一天要退出，但**“退出”不等于“立刻断电”**——优雅关闭就是让正在跑的任务先把手上那一点活干完、把资源还回去，再安安静静地走人。

---

## 0. 为什么这件事非学不可？

在同步代码里，`KeyboardInterrupt` 一来，栈帧一退，进程就没了。但在 `asyncio`（异步 I/O 框架）里，事件循环（event loop）可能同时挂着几十个协程（coroutine），有的在等 socket，有的在写数据库，有的持着锁。如果你直接 `sys.exit()`：

- 请求被从中间截断 → 客户端收到半截响应；
- 数据库连接没 commit → 数据不一致；
- 文件缓冲没 flush → 日志丢了。

**优雅关闭**要做的，就是给这些任务一个“体面离场”的机会。这几乎是所有生产级异步服务的必修课：Web 服务器、消息消费者、爬虫、gRPC 服务都离不开它。

本讲用 5 个小节，从“认识协程”一路走到“工业级关闭模式”。

---

## 1. 起点：协程、任务与事件循环

三个核心术语先厘清：

- **协程（coroutine）**：用 `async def` 定义的函数，调用它不会立即执行，返回一个协程对象。
- **任务（Task）**：用 `asyncio.create_task()` 把协程包成可在后台并发调度的对象。
- **事件循环（event loop）**：调度器本身，负责在 await 点切换任务。

`asyncio.run(main())` 做三件事：建循环 → 跑 main 协程 → 关循环。它就是我们的“入口与出口”。

```python
import asyncio

async def worker(name: str, n: int):
    # 模拟一项分 n 步、每步耗时的 I/O 工作
    for i in range(n):
        await asyncio.sleep(0.5)
        print(f"{name}: step {i+1}/{n}")

async def main():
    # create_task 让协程立刻进入后台调度，不等它
    t1 = asyncio.create_task(worker("A", 3))
    t2 = asyncio.create_task(worker("B", 3))
    # gather 并发等待两个任务全部结束
    await asyncio.gather(t1, t2)

asyncio.run(main())
```

**关键结论**：`create_task` 之后必须有人 `await` 或 `await gather(...)`，否则任务可能被垃圾回收，也会在关程序时被硬切断。

---

## 2. 取消机制：异步世界的“停止按钮”

`asyncio` 里的取消不是抢占式的，而是**协作式**的：

- 调用 `task.cancel()` 只是在目标任务的当前 await 点上抛出一个 `asyncio.CancelledError`；
- 目标协程可以捕获它，用来做清理（关闭连接、回滚事务）；
- 如果它不吞掉异常，最终会以“已取消”状态结束。

```python
import asyncio

async def long_job():
    try:
        while True:
            await asyncio.sleep(1)
            print("still working...")
    except asyncio.CancelledError:
        print("被取消了，做清理：flush 日志、关连接")
        raise  # 必须重新抛出，让调用者知道已取消

async def main():
    t = asyncio.create_task(long_job())
    await asyncio.sleep(3)
    t.cancel()
    try:
        await t
    except asyncio.CancelledError:
        print("main: 任务已取消")

asyncio.run(main())
```

**关键结论**：捕获 `CancelledError` 后**一定要 `raise` 再抛出去**，否则取消会“被吃掉”，事件循环无法正确追踪任务状态——这是新手最常见的坑。

---

## 3. 信号处理：让 Ctrl+C 变得温柔

在 Unix/Linux/macOS 上，Ctrl+C 会发出 `SIGINT`，`kill` 发出 `SIGTERM`。`asyncio` 允许我们把信号变成事件循环里的一个回调：

```python
import asyncio, signal

async def main():
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()

    def request_stop():
        print("收到停止请求")
        stop.set()

    # add_signal_handler 把 OS 信号接进事件循环
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, request_stop)

    print("服务运行中，按 Ctrl+C 试试")
    await stop.wait()
    print("开始优雅退出")

asyncio.run(main())
```

**关键结论**：`loop.add_signal_handler` 只在 Unix 上可用；Windows 上要用 `signal.signal` + `loop.call_soon_threadsafe`（或直接依赖 `KeyboardInterrupt` 兜底）。写出跨平台代码时要区分。

---

## 4. 优雅关闭的标准骨架

把前面几块拼起来，得到一个可复用的模式：

1. 主协程持有一个 `Event`（停止信号）和一组后台 `Task`。
2. 收到 `SIGINT/SIGTERM` 时 `set()` 事件，不再接受新工作。
3. 等待正在跑的任务做完（或给定超时）。
4. 超时后 `cancel()` 剩下不听话的任务。
5. `await asyncio.gather(*tasks, return_exceptions=True)` 收集结果，记录异常。

```python
import asyncio, signal

async def handle(job_id: int):
    try:
        print(f"开始 job {job_id}")
        await asyncio.sleep(2)     # 模拟实际业务
        print(f"完成 job {job_id}")
    except asyncio.CancelledError:
        print(f"job {job_id} 被强制取消，做清理")
        raise

async def serve(stop: asyncio.Event, tasks: list):
    # 模拟持续接收新任务
    for i in range(10):
        if stop.is_set():
            break
        tasks.append(asyncio.create_task(handle(i)))
        await asyncio.sleep(0.3)

async def main():
    stop = asyncio.Event()
    tasks: list[asyncio.Task] = []
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)

    producer = asyncio.create_task(serve(stop, tasks))
    await stop.wait()          # 等停止信号
    producer.cancel()          # 不再接新任务

    # 给已有任务一个收尾窗口
    try:
        await asyncio.wait_for(
            asyncio.gather(*tasks, return_exceptions=True),
            timeout=3,
        )
    except asyncio.TimeoutError:
        print("超时，强制取消剩余任务")
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    print("优雅关闭完成")

asyncio.run(main())
```

**关键结论**：`return_exceptions=True` 非常关键——它让 gather 不会因为某个任务抛异常就中断等待，我们才能把**所有任务**都收干净。

---

## 5. 工程级要点 & 常见陷阱

把上面的骨架放进真实项目时，还要记住这些：

- **双层超时**：先给一个正常的 grace 期（如 30s），再给一个硬超时（如 5s）兜底强制取消。
- **资源顺序**：先停“入口”（不再收新请求），再停“处理”（消化队列），最后停“出口”（关连接池、flush 日志）。
- **幂等清理**：清理函数要能在重复调用下不炸，因为信号可能收到多次。
- **别用 `sys.exit()` 打断 await**：它会在事件循环还未跑完清理的时候就杀掉进程。
- **cancelled 不等于 completed**：任务被取消后 `t.result()` 会抛 `CancelledError`，要用 `t.cancelled()` 判断。
- **Windows 兼容**：`add_signal_handler` 不可用，需要降级方案（见第 3 节）。

---

## 动手练习

**任务：写一个“可优雅关闭的”异步倒计时服务。**

要求：

1. 启动 5 个后台任务，每个任务每隔 1 秒打印一次 `job-N tick`，最多运行 20 秒。
2. 主程序监听 `SIGINT`（Ctrl+C）和 `SIGTERM`。
3. 收到信号后：
   - 停止创建新任务（如果采用生产者/消费者结构）；
   - 给现有任务 3 秒的 grace 期；
   - 3 秒后强制 `cancel()`，并打印每个任务最终是 `done` / `cancelled` / `exception` 中的哪一种。
4. 所有任务结束后，打印一句“服务已优雅退出”，并记录总耗时。

**验证方式**：
- 运行后等 5 秒按 Ctrl+C，观察是否所有 job 都成功收尾；
- 再运行一次，在 Ctrl+C 后立刻检查是否 3 秒内完成优雅关闭。

**进阶挑战**：把 grace 期改成从命令行参数读取，并对比 `asyncio.gather(..., return_exceptions=True)` 与逐个 `await t` 在处理 `CancelledError` 时的差异。


---

## 本课题目

### single_choice · None



- [A] 直接调用 sys.exit() 强制退出进程
- [B] 向任务发送取消，并在协程内部捕获取消异常后完成清理再重新抛出
- [C] 忽略信号，让操作系统在超时后强杀进程
- [D] 使用 time.sleep 阻塞事件循环以避免任务被中断

**参考答案**：1

**解析**：优雅关闭的核心是让协程在收到取消时有机会执行清理逻辑。捕获 asyncio.CancelledError 后做清理并重新抛出，是常见的正确模式；直接强制退出或忽略信号都会跳过清理。

### single_choice · None



- [A] 取消会被静默忽略，协程继续执行到结束
- [B] 会抛出 asyncio.CancelledError，若未捕获则沿调用栈传播，任务进入已取消状态
- [C] 会立即终止整个事件循环
- [D] 会触发进程信号处理函数，默认重新启动事件循环

**参考答案**：1

**解析**：取消在协程内部以 asyncio.CancelledError 形式出现，未捕获时会向上传播并使任务被标记为已取消。认为取消会被忽略或直接杀掉整个循环都是常见误解。

### single_choice · None



- [A] 因为阻塞操作会占用线程并阻止事件循环处理其他协程的清理和取消
- [B] 因为阻塞操作总是会引发 CancelledError
- [C] 因为阻塞操作无法在 finally 块中执行
- [D] 因为事件循环会自动把阻塞操作转换为异步操作

**参考答案**：0

**解析**：事件循环是单线程协作式调度，长时间阻塞会阻止其他协程运行，导致取消和清理无法及时推进。可以用 run_in_executor 或异步方式执行清理。

### single_choice · None



- [A] sleep 会继续执行完 10 秒，取消在结束后才生效
- [B] sleep 会立即抛出 CancelledError，协程可在该点进行清理
- [C] cancel() 会立即终止进程，不抛异常
- [D] sleep 会返回 None，协程继续执行下一行

**参考答案**：1

**解析**：取消会向任务投递 CancelledError，正在等待的 await 点（如 sleep）会收到该异常，协程可在该点捕获并清理。认为 sleep 会继续执行完是常见误解。

### single_choice · None



- [A] wait_for 超时后会取消任务并抛出 TimeoutError，而 cancel() 只是投递取消请求
- [B] wait_for 不会取消任务，只是返回 None
- [C] cancel() 会等待任务完成，wait_for 不会
- [D] 两者完全等价，没有任何区别

**参考答案**：0

**解析**：wait_for 在超时后会取消内部任务并抛出 TimeoutError，适合带超时的关闭流程；而 task.cancel() 只是请求取消，需要调用方 await 任务以等待其结束。

### single_choice · None



- [A] shield 可以让被包裹的协程免受取消影响，常用于保护关键清理步骤
- [B] shield 会阻止所有协程被取消
- [C] shield 会把 CancelledError 转换为 TimeoutError
- [D] shield 只能在 Python 3.6 之前使用

**参考答案**：0

**解析**：asyncio.shield 用于保护一个 awaitable 不被外部取消直接传播，但外部协程本身仍可能被取消；它常用于确保关键操作不被中途取消。

### single_choice · None



- [A] 不会有问题，finally 中的 await 总是安全执行
- [B] 如果该协程已被取消，在 finally 中再次 await 可能立即抛出 CancelledError，导致清理被跳过一半
- [C] await 在 finally 中不允许出现，会引发 SyntaxError
- [D] sleep 在 finally 中会变成同步阻塞

**参考答案**：1

**解析**：被取消后，任务处于取消状态，在 finally 中再次 await 可能立刻再次抛出 CancelledError，使清理逻辑中断。可以用 shield 或同步清理来避免。

### single_choice · None



- [A] 它会自动取消所有任务并忽略 CancelledError
- [B] 它会等待所有任务完成，并把异常作为结果收集，避免因单个任务异常而中断等待
- [C] 它会让所有任务共享同一个取消信号
- [D] 它会将任务转换为线程执行

**参考答案**：1

**解析**：return_exceptions=True 时，gather 会等待所有任务结束并把异常作为结果返回，而不是在第一个异常时提前抛出，适合关闭时统一等待。

### single_choice · None



- [A] 因为 Python 事件循环不允许在取消任务的同时接受新连接
- [B] 因为如果继续接收新任务，关闭可能永远无法完成，资源也无法及时释放
- [C] 因为取消任务会自动关闭所有套接字，无法再接受新连接
- [D] 因为先停止接收新任务会立即终止事件循环

**参考答案**：1

**解析**：优雅关闭的常见顺序是先停止接受新工作，再处理已有任务；否则不断有新任务进入，关闭流程会被无限推迟。

### single_choice · None



- [A] 当组内任一任务失败时，TaskGroup 会取消组内其他任务，并等待它们结束后再抛出异常
- [B] TaskGroup 会忽略所有子任务的异常，直接退出
- [C] TaskGroup 不允许在 with 块内创建任务
- [D] TaskGroup 会在退出时自动把子任务转为同步执行

**参考答案**：0

**解析**：TaskGroup 在子任务失败时会取消组内其他任务并等待它们结束，然后抛出异常（ExceptionGroup），这有助于结构化的优雅关闭。

### single_choice · None



- [A] 取消请求仍会被处理，但调用方无法感知任务是否真正结束，可能造成资源泄漏或“任务已被销毁但仍在等待”的警告
- [B] 取消请求会被自动忽略，任务继续正常运行
- [C] 任务会立即从事件循环中移除，不会有任何副作用
- [D] 会引发 RuntimeError，程序立即崩溃

**参考答案**：0

**解析**：cancel() 只是请求取消，必须 await 任务（或 gather 等）以确认其结束；否则可能无法感知取消是否完成，并出现任务未回收的警告。

### single_choice · None



- [A] 使用 `async with` 管理资源，让 `__aexit__` 在退出时执行清理
- [B] 使用 `try/finally` 并假定 finally 中所有 `await` 一定成功
- [C] 在 `__del__` 中执行 `await` 清理
- [D] 使用 `atexit.register` 注册异步清理函数并直接调用

**参考答案**：0

**解析**：async with 会在退出时调用 __aexit__ 执行异步清理，是管理异步资源的推荐方式。在 __del__ 中 await 不可靠，atexit 注册的函数默认也不会在异步上下文中 await。

### single_choice · None



- [A] try: await work() except asyncio.CancelledError: cleanup(); raise
- [B] try: await work() finally: cleanup()
- [C] try: await work() except Exception: cleanup(); raise
- [D] async with resource: await work()

**参考答案**：2

**解析**：asyncio.CancelledError 在较新的 Python 中继承自 BaseException 而非 Exception，因此只捕获 Exception 的写法不会捕获取消，清理逻辑会跳过。finally 和 async with 都能保证清理执行。

### single_choice · None



- [A] 它继承自 Exception，因此普通 except Exception 可以捕获
- [B] 它继承自 BaseException，因此普通 except Exception 无法捕获
- [C] 它继承自 SystemExit，应像系统退出一样处理
- [D] 它继承自 KeyboardInterrupt，需要单独处理

**参考答案**：1

**解析**：在 Python 3.8 及以后，asyncio.CancelledError 继承自 BaseException，故意让 except Exception 不捕获它，避免清理逻辑误吞取消。

### single_choice · None



- [A] 调用 asyncio.run() 多次，每次处理一个任务
- [B] 使用 asyncio.Event 或 Future 作为停止信号，协程在循环中检查该信号后退出
- [C] 调用 loop.stop() 会立即停止所有协程并执行其 finally 块
- [D] 使用 os._exit(0) 结束进程，让操作系统回收资源

**参考答案**：1

**解析**：优雅关闭通常通过共享的停止信号（如 asyncio.Event）通知所有协程，协程在安全点退出并清理。loop.stop() 只是停止事件循环，不会自动执行协程的 finally；os._exit 更不会触发清理。

### single_choice · None



- [A] 因为 loop.close() 是同步函数，总是会抛出 RuntimeError
- [B] 因为关闭前未完成的协程不会自动执行其 finally 清理，可能丢失资源释放
- [C] 因为 loop.close() 会阻塞当前线程直到所有任务完成
- [D] 因为 loop.close() 只能关闭默认事件循环，其他循环无法关闭

**参考答案**：1

**解析**：loop.close() 只是关闭循环对象，不会自动取消或等待未完成任务，协程的清理逻辑可能不会执行。它也不会自动阻塞等待任务完成。

### single_choice · None



- [A] 在协程中轮询 signal.getsignal(signal.SIGINT)
- [B] 使用 loop.add_signal_handler(signal.SIGINT, callback) 注册回调
- [C] 使用 signal.pause() 在协程中等待信号
- [D] 使用 asyncio.sleep(0) 轮询信号状态

**参考答案**：1

**解析**：在 asyncio 中，推荐使用 loop.add_signal_handler 将信号转换为事件循环内的回调，从而安全地设置停止信号或取消任务。轮询或 signal.pause() 会阻塞事件循环。

### single_choice · None



- [A] 因为重新抛出会让清理逻辑执行两次，确保安全
- [B] 因为不重新抛出会吞掉取消，调用方可能误以为任务正常完成并继续等待
- [C] 因为重新抛出会强制事件循环立即退出，实现优雅关闭
- [D] 因为 asyncio.CancelledError 必须由解释器自动重新抛出

**参考答案**：1

**解析**：捕获取消后重新抛出是让取消状态继续传播的标准做法；如果吞掉取消，上层可能无法感知任务已被取消，从而造成等待或关闭流程无法完成。

### single_choice · None



- [A] asyncio.Queue 的 join() 可以等待所有任务结束
- [B] asyncio.gather 的 return_exceptions=True 可以等待任务完成并收集结果
- [C] asyncio.sleep 可以无限等待直到任务自然结束
- [D] socket.setblocking(False) 可以暂停取消直到任务完成

**参考答案**：1

**解析**：asyncio.gather 可以等待一组任务完成，配合 return_exceptions=True 还能收集异常而不影响其他任务。Queue.join() 只等待队列项被处理完，不直接等价于等待所有任务。

### single_choice · None



- [A] 没有任何问题，finally 一定会执行 cleanup
- [B] 如果 long_running_task 被取消，CancelledError 不会被 except Exception 捕获，但 finally 仍会执行 cleanup，不过取消状态可能被吞掉
- [C] 问题在于 cleanup() 不是异步的，所以不会执行
- [D] 问题在于 try 块中不能使用 await

**参考答案**：1

**解析**：CancelledError 在 Python 3.8+ 中不是 Exception 的子类，所以不会被捕获，但 finally 仍会执行清理。若在 except 中捕获了 CancelledError 却不重新抛出，才会吞掉取消。
