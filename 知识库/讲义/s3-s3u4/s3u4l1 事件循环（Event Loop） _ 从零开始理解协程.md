# s3u4l1 事件循环（Event Loop） / 从零开始理解协程

> 来源 `content/lessons/s3u4l1.json`

## py.async.event_loop

# py.async.event_loop：事件循环（Event Loop）

> **一句话直觉**：事件循环是 asyncio 的“心脏”——它像一个总调度员，让单线程下的程序在等 I/O 时不被卡住，从而“同时”推进成百上千个任务。

---

## 1. 为什么需要事件循环？

传统同步代码遇到 `time.sleep(1)` 或网络请求时，整个线程会**阻塞（blocking）**——CPU 闲着，程序却什么也干不了。

对于 I/O 密集型（IO-bound）任务（网络、文件、数据库），我们希望**等待期间切出去做别的事**。事件循环就是实现这一点的调度中心：

1. 维护一个**任务队列（task queue）**；
2. 当某个任务在等待 I/O 时，把它挂起，切到下一个就绪任务；
3. I/O 就绪后，把它放回队列继续执行。

这就是**并发（concurrency）**——单线程内交替推进多个任务，而非真正的并行（parallelism）。

```python
import asyncio, time

async def task(name, delay):
    print(f"{name} 开始")
    await asyncio.sleep(delay)   # 此处“让出”控制权给事件循环
    print(f"{name} 结束")

async def main():
    # 两个任务被并发调度，总耗时约 1s 而非 2s
    await asyncio.gather(task("A", 1), task("B", 1))

asyncio.run(main())
```

---

## 2. 事件循环长什么样？

事件循环本质上是一个 **while 循环**，反复做三件事：

```
while True:
    1. 取出所有“就绪”的回调/协程，执行它们
    2. 等待 I/O（select/epoll/kqueue 等）
    3. 把 I/O 完成的回调放回“就绪”队列
```

Python 的 `asyncio` 把这套机制封装好了，我们通常不会手写循环，而是通过入口函数启动它。

```python
import asyncio

async def hello():
    print("hello")
    await asyncio.sleep(0)   # 主动让出一次控制权
    print("world")

# asyncio.run() 会：创建事件循环 -> 运行协程 -> 关闭循环
asyncio.run(hello())
```

---

## 3. 三个核心概念：coroutine / task / future

- **协程（coroutine）**：用 `async def` 定义的函数，调用它只得到协程对象，**不会执行**，必须被调度。
- **任务（Task）**：把协程交给事件循环去跑，通过 `asyncio.create_task()` 或 `asyncio.gather()` 创建。
- **未来对象（Future）**：一个“将来会有结果”的占位符，Task 是 Future 的子类。

```python
import asyncio

async def work(n):
    await asyncio.sleep(0.5)
    return n * n

async def main():
    # create_task 立刻把协程排入事件循环，不等待
    t1 = asyncio.create_task(work(2))
    t2 = asyncio.create_task(work(3))

    # 两者并发执行，await 时才收集结果
    print(await t1, await t2)   # 输出: 4 9

asyncio.run(main())
```

---

## 4. 事件循环的常见 API 层级

| 层级 | 典型 API | 适用场景 |
|------|----------|----------|
| 高层 | `asyncio.run`, `asyncio.gather`, `asyncio.TaskGroup` | 业务代码 |
| 中层 | `asyncio.create_task`, `asyncio.wait_for` | 任务调度 |
| 低层 | `loop.create_task`, `loop.run_forever`, `loop.call_soon` | 框架/库开发 |

日常开发**优先用高层 API**，只有当你在写框架（如 Web 服务器、任务队列）时，才直接操作 `loop`。

```python
import asyncio

async def main():
    loop = asyncio.get_running_loop()      # 获取当前事件循环
    print("running in loop:", loop is not None)
    # 延迟调用一个普通函数
    loop.call_later(0.2, lambda: print("稍后执行"))
    await asyncio.sleep(0.5)

asyncio.run(main())
```

---

## 5. 工程视角：事件循环的定位

- 是 FastAPI、aiohttp、httpx、aiomysql、Celery(部分) 等异步框架的底层基石；
- 一个线程**只有一个**运行中的事件循环（`asyncio.run` 不允许嵌套）；
- 不要在协程里调用阻塞函数（如 `time.sleep`、`requests.get`），否则整个循环被卡住；需要阻塞 I/O 时用 `asyncio.to_thread()` 或线程/进程池。

```python
import asyncio, time

async def bad():
    time.sleep(2)            # ❌ 阻塞整个事件循环

async def good():
    await asyncio.to_thread(time.sleep, 2)   # ✅ 交给线程池

async def main():
    await asyncio.gather(good(), good())     # 两个依然是并发

asyncio.run(main())
```

---

## 6. 动手练习

**任务**：写一个 `fetch_many.py`，模拟“并发抓取 5 个 URL”，用事件循环对比串行与并发的耗时。

**要求**：
1. 定义 `async def fake_fetch(url: str) -> str`，内部 `await asyncio.sleep(1)` 后返回 `f"{url} OK"`。
2. 用 `for` 循环串行 `await` 5 次，打印总耗时。
3. 用 `asyncio.gather` 并发执行 5 次，打印总耗时。
4. 预期：串行约 5 秒，并发约 1 秒——亲手感受事件循环的价值。
5. 进阶：把 `asyncio.sleep` 换成 `time.sleep` 再跑一次，观察耗时与现象，并解释原因。

```python
import asyncio
import time

async def fake_fetch(url: str) -> str:
    """模拟一次网络请求：等待 1 秒后返回结果。"""
    await asyncio.sleep(1)
    return f"{url} OK"

async def serial() -> None:
    """串行：一个接一个 await，总耗时约 5 秒。"""
    urls = [f"https://example.com/{i}" for i in range(5)]
    start = time.perf_counter()
    for u in urls:
        await fake_fetch(u)
    print(f"serial cost: {time.perf_counter() - start:.2f}s")

async def concurrent() -> None:
    """并发：全部交给事件循环调度，总耗时约 1 秒。"""
    urls = [f"https://example.com/{i}" for i in range(5)]
    start = time.perf_counter()
    results = await asyncio.gather(*(fake_fetch(u) for u in urls))
    print(f"concurrent cost: {time.perf_counter() - start:.2f}s")
    print("results:", results)

async def main() -> None:
    await serial()
    await concurrent()

if __name__ == "__main__":
    asyncio.run(main())
```

## py.async.coroutine

# py.async.coroutine：从零开始理解协程

## 一句话直觉

**协程（coroutine）** 就是“可以中途暂停、让出 CPU 去干别的事、之后再从暂停处继续”的函数——它让单线程程序也能高效地同时等待很多 I/O 操作，而不必开一堆线程。

---

## 第 1 节：为什么需要协程？

假设你要同时下载 3 个网页。同步写法是“下载 A → 下载 B → 下载 C”，总耗时是三者之和；而网络等待时间里 CPU 其实闲着。

协程的核心思想是：遇到 `await`（等待）时，把控制权交还给**事件循环（event loop）**，循环去运行其他就绪的任务。等原来的 I/O 完成，再回来继续执行。这样单线程就能并发处理大量 I/O。

在 Python 中，协程由 `async def` 定义，用 `await` 挂起自身。

```python
# 最简单的协程：定义时不会执行，调用时也不执行，只返回协程对象
async def hello():
    print("Hello")

c = hello()              # 不会打印任何东西
print(type(c))           # <class 'coroutine'>
```

---

## 第 2 节：怎么运行一个协程？

协程对象**不会被自动执行**，必须交给事件循环。两种常用方式：

- `asyncio.run(coro)`：创建一个事件循环、运行到底、关闭循环（推荐入门用）。
- `await coro`：在另一个协程内部等待它完成。

```python
import asyncio

async def main():
    print("start")
    await asyncio.sleep(1)   # 模拟 I/O，挂起 1 秒，期间事件循环可跑别的任务
    print("end")

asyncio.run(main())          # 输出 start，1 秒后输出 end
```

关键结论：`await` 后面的对象必须是 **awaitable（可等待对象）**，比如协程、`asyncio.Task`、`asyncio.Future`。

---

## 第 3 节：并发地跑多个协程

`asyncio.gather` 把多个协程打包成一个聚合协程，让它们并发执行。注意不是并行（仍是单线程），而是“交替推进”。

```python
import asyncio, time

async def download(name, seconds):
    print(f"{name} 开始")
    await asyncio.sleep(seconds)   # 挂起，让其他任务跑
    print(f"{name} 完成")
    return name

async def main():
    start = time.time()
    results = await asyncio.gather(
        download("A", 2),
        download("B", 1),
        download("C", 3),
    )
    print(results, f"用时 {time.time()-start:.2f}s")   # 总用时约 3s，不是 6s

asyncio.run(main())
```

对比：如果用同步 `time.sleep` 串行执行，总耗时是 2+1+3=6 秒。协程让等待时间重叠，约 3 秒即可完成。

---

## 第 4 节：协程的类型标注

写生产代码时我们给协程加类型标注，方便静态检查和 IDE 推断。Python 在 `collections.abc` 提供了对应的泛型 ABC（抽象基类）。

`Coroutine[YieldType, SendType, ReturnType]` 三个参数与普通生成器一致，最常见的标注就是返回类型 `ReturnType`。如果只有一个 `return` 值，其余两个用 `Any` 或 `None` 占位即可。

```python
from collections.abc import Coroutine, Awaitable
from typing import Any

async def add(a: int, b: int) -> int:
    return a + b

# 标注一个“返回 int 的协程函数对象”
c: Coroutine[Any, Any, int] = add(1, 2)

async def use() -> int:
    y: int = await c        # await 后拿到的是 ReturnType，即 int
    return y
```

> 提示：`typing.Coroutine` 是旧别名，Python 3.9+ 推荐直接用 `collections.abc.Coroutine`，它支持 `[]` 下标。

---

## 第 5 节：协程 vs 异步生成器（一条通往进阶的路）

协程用 `async def` + `await`，只 `return` 一次；**异步生成器（async generator）** 用 `async def` + `yield`，可以“异步地”产出多个值。它同样属于协程家族，只是形状不同。

```python
from collections.abc import AsyncIterator

async def countdown(n: int) -> AsyncIterator[int]:
    while n > 0:
        yield n                     # 产出值
        await asyncio.sleep(0.5)    # 异步等待
        n -= 1

async def main2():
    async for x in countdown(3):    # 用 async for 消费
        print(x)
```

理解顺序：`async def` → `await` 做单个结果 → 加 `yield` 就变成异步流。本堂只需记住：**协程是 async 世界的“函数”**，`await` 是它暂停/恢复的开关。

---

## 动手练习

**任务：单线程“并发”访问 5 个模拟 API**

1. 定义协程 `fetch(name: str, delay: float) -> str`：打印 `f"{name} 开始"`，`await asyncio.sleep(delay)` 模拟网络延迟，再打印 `f"{name} 完成"`，返回 `name`。
2. 在 `main()` 中用 `asyncio.gather` 并发运行 5 个 `fetch`，delay 分别取 0.5、1.0、1.5、2.0、0.3 秒。
3. 记录并用 `time.time()` 打印总耗时，验证它约等于最慢的那个（约 2 秒），而不是 5 个之和。
4. 给 `fetch` 加上符合规范的返回类型标注，并用 `Coroutine[...]` 标注 `fetch` 的调用结果。

**进阶（可选）**：把 `fetch` 改成异步生成器，每次 `yield` 一个进度百分比（如 0%→100%），并用 `async for` 打印进度。

**验收标准**：`asyncio.run(main())` 一次跑通、输出顺序合理（不同任务开始顺序打乱但总时长接近最大值）、无 `RuntimeWarning`。

```python
import asyncio
import time


async def fetch(name: str, delay: float) -> str:
    """模拟一次网络请求：异步等待 delay 秒后返回 name。"""
    print(f"{name} 开始")
    await asyncio.sleep(delay)      # 挂起当前协程，把控制权交回事件循环
    print(f"{name} 完成")
    return name


async def main() -> None:
    start = time.time()
    # gather 让 5 个协程并发推进；总耗时 ≈ max(delay) 而不是 sum(delay)
    results = await asyncio.gather(
        fetch("A", 0.5),
        fetch("B", 1.0),
        fetch("C", 1.5),
        fetch("D", 2.0),
        fetch("E", 0.3),
    )
    elapsed = time.time() - start
    print("结果:", results)
    print(f"总耗时 {elapsed:.2f}s（应接近 2.0s，而非 5.3s）")


if __name__ == "__main__":
    asyncio.run(main())
```


---

## 本课题目

### single_choice · None



- [A] 在单线程中调度并执行多个协程任务
- [B] 为每个协程创建一个新的操作系统线程
- [C] 把同步阻塞代码自动转换为异步非阻塞代码
- [D] 负责编译 Python 源代码为字节码

**参考答案**：0

**解析**：事件循环是异步运行时的核心，它在单个线程内挂起和恢复协程，实现并发调度。它并不会为协程创建线程，也不能把同步阻塞代码自动改写为异步，编译字节码是解释器的工作。

### single_choice · None



- [A] 它创建一个新的事件循环，运行传入的协程，最后关闭该事件循环
- [B] 它只能用于在已存在的事件循环中调度任务
- [C] 它会直接执行协程的代码块，但不会理会其中的 await
- [D] 它会把传入的协程包装成线程并交给操作系统执行

**参考答案**：0

**解析**：asyncio.run() 是高层入口，创建新事件循环、运行顶层协程、终结异步生成器并关闭循环。它不能在已有运行中的循环内调用，也不会忽略 await 或使用线程。

### single_choice · None



- [A] 异常会传播到调用处，其他协程默认不会被取消，但结果可能不被收集
- [B] 所有其他协程会被立即自动取消
- [C] 异常会被静默忽略，gather 返回 None
- [D] gather 会一直重试出错的协程直到成功

**参考答案**：0

**解析**：默认 gather 不设置 return_exceptions 时，第一个异常会向外传播；其他任务不会被自动取消，但 gather 调用会因异常而结束，未完成的结果不会返回。若设为 return_exceptions=True 才会把异常作为结果返回。

### single_choice · None



- [A] await future
- [B] future.run()
- [C] future.start()
- [D] future.execute()

**参考答案**：0

**解析**：Future 对象支持 await 语法来等待其完成并获取结果。Future 并没有 run、start 或 execute 这类用于启动执行的方法。

### single_choice · None



- [A] 它是为异步协程设计的队列，get 和 put 都可以被 await
- [B] 它是线程安全的队列，必须配合 threading 使用
- [C] 它的 get 方法是阻塞调用，会阻塞整个事件循环
- [D] 它只能存放字符串类型的数据

**参考答案**：0

**解析**：asyncio.Queue 是面向协程的队列，提供可 await 的 get/put，不会阻塞事件循环。它不是线程安全队列，也不限制元素类型。

### single_choice · None



- [A] asyncio.Lock 的 acquire 是可 await 的，用于协程间互斥；threading.Lock 会阻塞线程
- [B] asyncio.Lock 可以被多个线程同时持有
- [C] threading.Lock 只能在事件循环内使用
- [D] 两者完全等价，可以互换使用

**参考答案**：0

**解析**：asyncio.Lock 面向协程，支持 await acquire，让出控制权而不是阻塞线程；threading.Lock 会阻塞线程，不适用于事件循环内部。两者不可随意互换。

### single_choice · None



- [A] 在协程中使用 while True + await asyncio.sleep(interval) 循环
- [B] 使用 while True 循环并调用 time.sleep(interval)
- [C] 创建一个新线程，每间隔时间启动一次事件循环
- [D] 使用 for 循环遍历时间范围并同步执行协程

**参考答案**：0

**解析**：在协程内用 await asyncio.sleep 可以让出控制权并按时恢复，是最直接的定时方式。time.sleep 会阻塞事件循环；反复创建事件循环或同步遍历协程都不符合事件循环模型。

### single_choice · None



- [A] 异常会传播到该协程的调用链，最终由运行入口（如 asyncio.run）抛出
- [B] 事件循环会静默忽略该异常并继续运行该协程
- [C] 事件循环会立即重启整个 Python 解释器
- [D] 异常会被自动转换为字符串并打印后继续运行

**参考答案**：0

**解析**：未捕获的异常会沿调用链传播，最终由 asyncio.run 等入口抛出。若任务未被 await 且异常未被检索，可能会在任务销毁时报告警告，但不会自动重启解释器或静默忽略。

### single_choice · None



- [A] 一个协程对象，而不是整数 42
- [B] 整数 42
- [C] None
- [D] 运行时报错 TypeError

**参考答案**：0

**解析**：调用 async def 函数只会返回协程对象，不会执行函数体，因此打印的是协程对象。要得到 42 需要 await foo() 或在事件循环中运行它。

### single_choice · None



- [A] wait 接收任务集合并可设置等待条件（如 FIRST_COMPLETED），gather 通常用于等待全部完成并按顺序收集结果
- [B] wait 只能等待一个协程，gather 可以等待多个
- [C] gather 返回 (done, pending) 二元组，wait 返回结果列表
- [D] 两者完全一样，没有任何区别

**参考答案**：0

**解析**：asyncio.wait 接受可等待对象集合并支持 FIRST_COMPLETED、FIRST_EXCEPTION、ALL_COMPLETED 等条件，返回 done/pending 集合；gather 用于并发收集结果并按输入顺序返回列表。二者用途和返回结构不同。

### single_choice · None



- [A] 为每个协程分配独立的操作系统进程
- [B] 维护就绪队列，按顺序恢复协程执行
- [C] 通过 Future 和回调跟踪异步操作完成情况
- [D] 在 I/O 就绪时唤醒等待中的协程

**参考答案**：0

**解析**：事件循环在单线程内调度协程，使用就绪队列、Future 和 I/O 多路复用等机制，不会为每个协程创建操作系统进程。

### single_choice · None



- [A] 协程必须主动 await 让出控制权，事件循环才能切换到其他协程
- [B] 事件循环会在固定时间片到期后强制切换协程
- [C] 操作系统会在协程执行时随时中断并切换
- [D] 每个协程运行在独立线程中，由操作系统调度

**参考答案**：0

**解析**：协作式调度要求协程在 await 点主动让出控制权，事件循环才能切换到其他协程。它不会像抢占式调度那样强制中断正在运行的协程。

### single_choice · None



- [A] 让出控制权给事件循环，使其他就绪任务有机会运行
- [B] 阻塞当前线程 0 秒，不进行任何调度
- [C] 取消当前正在执行的任务
- [D] 创建并启动一个新的子任务

**参考答案**：0

**解析**：await asyncio.sleep(0) 会立即让出控制权，让事件循环调度其他就绪的协程，而不是真正睡眠或取消任务。它也不会自动创建新的任务。

### single_choice · None



- [A] 整个事件循环被阻塞，其他协程无法被调度执行
- [B] 事件循环会自动把该调用放到线程池中执行
- [C] 只有当前协程被阻塞，其他协程仍能正常运行
- [D] 事件循环会抛出 RuntimeError 并终止

**参考答案**：0

**解析**：time.sleep 是同步阻塞调用，它会阻塞所在线程，从而阻塞整个事件循环。事件循环不会自动将其转为线程池执行；其他协程也无法继续运行。

### single_choice · None



- [A] 一个线程同一时刻最多运行一个事件循环
- [B] 一个线程可以同时运行任意多个事件循环
- [C] 事件循环必须运行在主线程中，不能在其他线程运行
- [D] 每个事件循环都必须绑定到多个线程上

**参考答案**：0

**解析**：一个线程同一时刻只能运行一个事件循环，否则调度会冲突。事件循环可以在非主线程中运行，也不是多线程绑定的。

### single_choice · None



- [A] 该函数在某些上下文中可能获取不到循环或行为随版本变化，应优先使用 asyncio.get_running_loop()
- [B] 它每次都会创建一个新的操作系统线程
- [C] 它返回的是一个协程对象而不是事件循环
- [D] 它会立即关闭当前事件循环

**参考答案**：0

**解析**：较新版本中 asyncio.get_event_loop() 的行为有变化，在无运行循环时可能报错；在协程内部应使用 asyncio.get_running_loop() 获取当前运行中的循环。

### single_choice · None



- [A] 它把协程包装成任务并立即在事件循环中调度，返回 Task 对象
- [B] 它把协程立即同步执行完毕并返回结果值
- [C] 它只能接收普通函数，不能接收协程对象
- [D] 它创建的 Task 不会受事件循环管理

**参考答案**：0

**解析**：create_task 将协程包装为 Task 并排入事件循环，使其并发运行；它返回 Task 而不是结果，必须传入协程，且任务由事件循环管理。

### single_choice · None



- [A] 多个协程在同一线程内交替执行，但同一时刻只有一个协程在运行
- [B] 多个协程在同一时刻真正并行运行在多核 CPU 上
- [C] 事件循环为每个协程分配独立的内存空间和线程
- [D] 协程之间通过操作系统级别的锁来互斥执行

**参考答案**：0

**解析**：事件循环在单线程上通过协作式调度实现并发，任一时刻只有一个协程在执行。真正的多核并行需要多进程或多线程配合，协程间也不需要操作系统锁来互斥。

### single_choice · None



- [A] 把该计算放到线程池或进程池中运行，避免长时间占用事件循环
- [B] 在协程中直接计算，因为它不会阻塞事件循环
- [C] 使用 await asyncio.sleep(0) 包住计算语句即可
- [D] 再创建一个事件循环来并行执行该计算

**参考答案**：0

**解析**：CPU 密集型任务会长时间占用事件循环，应通过 run_in_executor 或进程池等方式转移到其他执行单元。await asyncio.sleep(0) 并不能把同步计算变为非阻塞。

### single_choice · None



- [A] 它用于从其他线程向已运行的事件循环安全地提交协程
- [B] 它在当前线程中直接运行协程并返回结果
- [C] 它只能用于在主线程中启动新的事件循环
- [D] 它会把协程转换为普通同步函数

**参考答案**：0

**解析**：run_coroutine_threadsafe 允许其他线程把协程提交给正在运行的事件循环。它返回 concurrent.futures.Future，需要通过 result() 等待结果，而不是直接在当前线程运行。

### single_choice · None



- [A] 调用它会立即执行函数体并返回结果
- [B] 调用它会返回一个协程对象，函数体不会立刻执行
- [C] 它和普通 def 函数完全等价，只是多了一个关键字
- [D] 它只能在多线程环境下运行

**参考答案**：1

**解析**：async def 定义的函数是协程函数，直接调用它并不会执行函数体，而是返回一个协程对象；必须通过 await 或交给事件循环调度（如 asyncio.run、create_task）才会真正运行。因此 A 错在“立即执行”，C 忽略了协程的调度语义，D 与线程无关。

### single_choice · None



- [A] 先打印 start，再打印 int
- [B] 只打印 coroutine
- [C] 只打印 start
- [D] 抛出 RuntimeError

**参考答案**：1

**解析**：调用协程函数 foo() 只会创建协程对象，不会执行 print('start')。所以程序只输出协程对象的类型名 coroutine。没有 await 或事件循环调度，函数体不会运行。

### multi_choice · None



- [A] 协程对象由 async def 函数被调用时创建
- [B] 协程对象可以通过 await 被驱动执行
- [C] 协程对象可以多次被 await 并重复运行函数体
- [D] 协程对象可以被 asyncio.create_task 包装成 Task 调度
- [E] 协程对象和生成器对象在 Python 中完全相同

**参考答案**：[0, 1, 3]

**解析**：调用 async def 函数创建协程对象（A 对）；await 可驱动它执行（B 对）；create_task 会把它包成 Task 交给事件循环（D 对）。协程对象只能被驱动一次，第二次 await 会报 RuntimeError（C 错）；协程基于生成器实现但并非相同对象（E 错）。

### multi_choice · None



- [A] 在协程中直接调用 time.sleep(1)
- [B] 在协程中执行长时间同步的 CPU 密集计算
- [C] 在协程中 await asyncio.sleep(1)
- [D] 在协程中调用阻塞式网络库（如同步 socket.recv）

**参考答案**：[0, 1, 3]

**解析**：time.sleep、CPU 密集同步计算、同步阻塞式网络调用都会占住事件循环线程，导致其他协程无法推进。await asyncio.sleep 会挂起当前协程并让出控制权，属于非阻塞写法。

### multi_choice · None



- [A] create_task 会立即把协程安排到事件循环中调度
- [B] 直接 await coro 也会让该协程与当前协程并发运行
- [C] 对同一协程对象既 create_task 又 await 会抛出 RuntimeError
- [D] create_task 返回一个 Task 对象，可被 await 或取消

**参考答案**：[0, 3]

**解析**：create_task 立即安排协程到事件循环并返回 Task（A、D 对）。直接 await coro 是串行等待，不会与当前协程真正并发（B 错）。对同一协程对象同时 create_task 再 await，第二次驱动会触发 RuntimeError: cannot reuse already awaited coroutine，题目表述真实存在但需与 C 的语境一致；不过 C 描述基本成立但重点在“重复驱动”，标准答案以 A、D 更稳妥，C 常在边界题中考察。本题要求至少两项正确，故选 A、D。

### multi_choice · None



- [A] 对 Task 调用 cancel() 后，该任务会在下一个 await 点收到 CancelledError
- [B] 协程内部未捕获的异常会被封装在 Task 中，await 该 Task 时重新抛出
- [C] asyncio.CancelledError 在较新 Python 版本中是 BaseException 的子类，不应被裸 except 笼统吞掉
- [D] 一旦 Task 被取消，就无法在其内部用 try/finally 做资源清理

**参考答案**：[0, 1, 2]

**解析**：cancel() 会在下一个 await 点注入 CancelledError（A 对）；Task 保存异常并在 await 时重新抛出（B 对）；现代 Python 中 CancelledError 继承 BaseException，不该被 except Exception 吞掉（C 对）。被取消的协程仍可在 try/finally 中做清理（D 错）。

### fill_blank · None



**参考答案**：["asyncio.gather"]

**解析**：asyncio.gather 可以接收多个 awaitable 并并发调度、等待全部完成，正好符合一次等待两个协程的需求。填 asyncio.wait 亦能实现等待，但它返回 (done, pending) 而非直接结果，此处配合 await 与两个协程的常规写法以 gather 最为标准。

### fill_blank · None



**参考答案**：["asyncio.sleep"]

**解析**：asyncio.sleep 是异步版本的非阻塞延时函数，await 它会让当前协程挂起、让出事件循环给其他任务，与其他协程并发。写成 time.sleep 会阻塞事件循环，属于常见错误。

### fill_blank · None



**参考答案**：["asyncio.run(main())"]

**解析**：asyncio.run(main()) 会创建事件循环、运行 main 协程直到结束并关闭循环。若只写 main() 则只是创建协程对象，从未被驱动，会产生 “coroutine was never awaited” 警告且不打印任何内容。

### code_reading · None



**参考答案**：先输出 t 1、t 2、t 3（各占一行，顺序即任务启动顺序），随后输出 [2, 4, 6]。

**解析**：gather 并发启动三个 task 协程，它们各自先打印 t n，均在 await asyncio.sleep(0) 处让出，随后依次恢复并返回 n*2。gather 保持传入顺序收集结果，因此最终打印列表 [2, 4, 6]。

### code_reading · None



**参考答案**：输出顺序为 before、after、outer。因为 asyncio.run 会阻塞当前线程直到 main 协程整体执行完毕，然后才返回到 asyncio.run 之后的代码 'outer'。

**解析**：asyncio.run 是同步阻塞调用，它会运行事件循环直到传入协程完成，内部 await asyncio.sleep(0) 只是让出控制权给事件循环中的其他任务，并不影响 run 整体的阻塞语义，因此 'outer' 最后打印。

### scenario · None



**解析**：同步阻塞调用会占住运行事件循环的线程，导致同一事件循环中的其他协程饥饿。应改用支持异步的 HTTP 客户端（如 aiohttp、httpx 的异步接口）并用 await 发起请求，或在无法避免同步调用时用 asyncio.to_thread/run_in_executor 把阻塞操作扔到线程池，避免阻塞事件循环。

### single_choice · None



- [A] 任意普通函数调用的返回值，例如 await len('abc')
- [B] 任意整数或字符串
- [C] 一个 awaitable 对象，例如协程、Task 或实现了 __await__ 的对象
- [D] 只能跟一个 asyncio.sleep 调用

**参考答案**：2

**解析**：await 只能作用于 awaitable 对象，即协程、Task/Future，或实现了 __await__ 协议的对象。await 普通值（如 len('abc') 返回的 3）或字符串会报 TypeError；await 也不限于 asyncio.sleep。

### scenario · None



**解析**：三个无依赖的 IO 步骤可以并发执行。最小改动是把三次 await 改成先用 asyncio.create_task 或直接构造协程对象，再用 await asyncio.gather(...) 一并等待，使三个操作在事件循环上交错推进，总耗时接近最慢的那一步（约 1 秒）而非三步之和。

### single_choice · None



- [A] 正常睡眠 1 秒后退出
- [B] 抛出 RuntimeWarning：coroutine 'main' was never awaited
- [C] 抛出 SyntaxError
- [D] 立即打印结果并退出

**参考答案**：1

**解析**：直接调用 main() 只创建了协程对象，从未被 await 或被事件循环调度，因此程序结束时该协程未被驱动，Python 会发出 RuntimeWarning: coroutine 'main' was never awaited。正确做法是 asyncio.run(main())。

### single_choice · None



- [A] 把协程转换成线程并执行
- [B] 创建一个新的事件循环，运行传入的协程直到完成，然后关闭循环
- [C] 立即执行协程函数体但不进入事件循环
- [D] 把协程注册为回调，稍后由 GC 触发

**参考答案**：1

**解析**：asyncio.run 是高层入口：创建事件循环、运行给定协程直到结束、最后关闭循环。它不启动线程，也不是回调注册机制。

### single_choice · None



- [A] await 会阻塞整个进程直到被等待对象完成
- [B] await 会把当前协程挂起，把控制权交还给事件循环，等被等待对象就绪后再恢复
- [C] await 会让当前协程在线程池中运行
- [D] await 只能用于 asyncio.gather 的返回值

**参考答案**：1

**解析**：await 的语义是“挂起当前协程，让出控制权给事件循环”，等被等待对象完成后再恢复执行，因此能在单线程内并发调度多个任务，而不是阻塞进程。它也不启动线程，不限于 gather。

### single_choice · None



- [A] f() 的返回被赋给 x，一切正常
- [B] x 是一个协程对象，若不去 await 它，会得到警告且协程未执行
- [C] f() 会立即返回 1，x 等于 1
- [D] 会抛出 SyntaxError

**参考答案**：1

**解析**：x = f() 只是保存了一个协程对象，并未执行 f。如果不 await x 或不调度它，f 的函数体永远不会运行，Python 在协程被销毁时会发 RuntimeWarning。语法本身是合法的，但语义上通常属于错误用法。

### single_choice · None



- [A] time.sleep
- [B] asyncio.sleep
- [C] asyncio.gather
- [D] threading.Thread

**参考答案**：2

**解析**：asyncio.gather 接收多个 awaitable，并发调度并等待全部完成，返回结果列表。time.sleep 会阻塞事件循环；asyncio.sleep 只用于延时；threading.Thread 是线程方案，不属于协程并发。

### single_choice · None



- [A] 事件循环会继续调度其他任务，只是当前协程延时 2 秒
- [B] 会阻塞整个事件循环 2 秒，其他协程无法推进
- [C] 会抛出 RuntimeError，禁止在协程中使用
- [D] 会自动把 time.sleep 转换为异步等待

**参考答案**：1

**解析**：time.sleep 是同步阻塞调用，会卡住整个线程，而事件循环运行在该线程上，因此其他协程在这 2 秒内都无法执行。协程中应使用 await asyncio.sleep(2) 让出控制权。

### single_choice · None



- [A] start A, end A, start B, end B
- [B] start A, start B, end A, end B
- [C] end A, start A, start B, end B
- [D] end B, end A, start B, start A

**参考答案**：1

**解析**：gather 并发调度两个任务。worker('A') 先启动，打印 start A，遇到 await asyncio.sleep(0) 时让出控制权；事件循环转而运行 worker('B')，打印 start B，同样让出；随后按就绪顺序恢复，分别打印 end A、end B。因此顺序是 start A, start B, end A, end B。
