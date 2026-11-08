# s3u6l1 在异步代码中调用阻塞函数 / `py.async.run_in_executor`：让异步世界里也能跑同步阻塞代码

> 来源 `content/lessons/s3u6l1.json`

## py.async.blocking_call

# py.async.blocking_call：在异步代码中调用阻塞函数

## 一句话直觉

**当你在 `async def` 里调用一个会“卡住”的同步函数（比如 `time.sleep`、`requests.get`、磁盘 IO），整个事件循环（event loop）都会被冻住 —— `asyncio.to_thread` / `run_in_executor` 就是把它“扔到别的线程去跑”，让主循环继续处理其它任务。**

关键词首次出现：
- **异步（asynchronous）**：单线程内通过“协作式切换”并发处理多个任务。
- **协程（coroutine）**：用 `async def` 定义的函数，可被 `await` 挂起。
- **事件循环（event loop）**：`asyncio` 的调度器，负责在协程挂起时切到别的协程。
- **阻塞调用（blocking call）**：在返回前不把控制权交还调用者的函数，例如 `time.sleep`、`socket.recv`（同步版）、`requests`。
- **执行器（executor）**：`concurrent.futures` 提供的线程/进程池，用来跑阻塞代码。

---

## 第 1 节：先看“卡住”的后果

`asyncio` 是**单线程**的。如果你在一个协程里做了一次阻塞，其它协程全部得等它。

```python
import asyncio, time

async def ticker():
    for i in range(3):
        print(f"tick {i}")
        await asyncio.sleep(0.5)

async def bad():
    time.sleep(2)          # 阻塞！事件循环被冻住 2 秒
    return "done"

async def main():
    await asyncio.gather(ticker(), bad())

asyncio.run(main())
```

你会看到 `tick 0` 之后卡顿 2 秒才出现剩下内容。因为 `time.sleep` 不让出控制权。

---

## 第 2 节：把它丢到线程里 —— `asyncio.to_thread`

Python 3.9+ 提供最简写法：

```python
import asyncio, time

async def main():
    # to_thread 把阻塞函数放到默认线程池
    result = await asyncio.to_thread(time.sleep, 1)
    print("sleep done")

asyncio.run(main())
```

`await asyncio.to_thread(fn, *args)` 的语义：
- 立刻把 `fn(*args)` 提交到线程池；
- 当前协程挂起，事件循环继续跑别的任务；
- 完成后返回 `fn` 的结果。

---

## 第 3 节：更底层的写法 `loop.run_in_executor`

3.9 之前 / 需要自定义执行器（比如进程池）：

```python
import asyncio, time
from concurrent.futures import ThreadPoolExecutor

async def main():
    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor(max_workers=4) as pool:
        r = await loop.run_in_executor(pool, time.sleep, 1)
    print("ok", r)

asyncio.run(main())
```

`run_in_executor(None, fn, *args)` 的 `None` 表示用事件循环默认的 `ThreadPoolExecutor`。

---

## 第 4 节：为什么“就一次”也值得改？

两个典型场景：

1. **IO 密集**：`requests`、`psycopg2`、`boto3` 等同步客户端在 `async` 程序里调用会拖垮整个服务。
2. **CPU 密集**：`to_thread` 不解决 GIL，需用 `ProcessPoolExecutor`：

```python
import asyncio, hashlib
from concurrent.futures import ProcessPoolExecutor

def heavy(n: int) -> str:
    return hashlib.sha256(str(n).encode()).hexdigest()

async def main():
    loop = asyncio.get_running_loop()
    with ProcessPoolExecutor() as pool:
        # 必须用默认参数之外的位置参数传入
        results = await asyncio.gather(*[
            loop.run_in_executor(pool, heavy, i) for i in range(4)
        ])
    print(results[0][:16])

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 第 5 节：工程级原则

- **边界原则**：只在 async 与 sync 的**边界**上做桥接；异步协程内部不要粗心混用阻塞调用。
- **池要复用**：高频调用时把 `ThreadPoolExecutor` / `ProcessPoolExecutor` 作为长生命周期对象；避免每次 `to_thread` 创建大量线程。
- **超时**：`await asyncio.wait_for(asyncio.to_thread(fn), timeout=5)`。
- **取消**：`wait_for` 超时后会取消 future，但线程本身可能仍在跑 —— 无法真正“杀死”线程，需让被调函数自己支持取消（如检查标志位）。
- **不要**在线程里再调 `asyncio.run`。
- **想彻底异步**：优先选支持 async 的库（`httpx`、`asyncpg`、`aiohttp`），`to_thread` 是兜底方案，不是默认答案。

```python
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor


def blocking_db_query(user_id: int) -> dict:
    """模拟同步 IO：真实场景可能是 requests.get 或 psycopg2 查询。"""
    time.sleep(1.0)
    return {"user_id": user_id, "name": f"user-{user_id}"}


async def fetch_user(user_id: int) -> dict:
    # 用 asyncio.to_thread 把阻塞函数扔到线程池
    return await asyncio.to_thread(blocking_db_query, user_id)


async def main() -> None:
    t0 = time.perf_counter()
    # 3 个请求并发执行，总耗时 ~1 秒而非 3 秒
    users = await asyncio.gather(*(fetch_user(i) for i in (1, 2, 3)))
    print(users)
    print(f"elapsed: {time.perf_counter() - t0:.2f}s")

    # 方式二：显式线程池，适合需要控制并发数的工程场景
    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor(max_workers=4) as pool:
        r = await loop.run_in_executor(pool, blocking_db_query, 99)
        print("via executor:", r)


if __name__ == "__main__":
    asyncio.run(main())
```

## py.async.run_in_executor

# `py.async.run_in_executor`：让异步世界里也能跑同步阻塞代码

> **一句话直觉**：`run_in_executor` 是 `asyncio`（异步 I/O 框架）用于把**同步阻塞函数**（如 `time.sleep`、`requests.get`、CPU 密集计算）丢到**线程池/进程池**里执行的桥梁，让事件循环（event loop）不被阻塞，从而继续并发处理其他协程（coroutine）。

---

## 1. 为什么需要它？——异步世界的“阻塞”之痛

`asyncio` 的核心思想是**单线程事件循环 + 协作式多任务**：所有协程在 `await` 处主动让出控制权，事件循环在等待期间去跑别的任务。

但如果某个协程里直接调用了 `time.sleep(2)` 或 `requests.get(...)`，它会**霸占事件循环 2 秒**，期间所有其他协程全被卡死——这叫做“阻塞事件循环（blocking the event loop）”。

```python
import asyncio, time

async def bad():
    # ❌ 同步阻塞，整个事件循环被冻结 2 秒
    time.sleep(2)
    return "done"

async def main():
    start = time.perf_counter()
    await asyncio.gather(bad(), bad(), bad())
    # 大约 6 秒，因为三个任务串行阻塞事件循环
    print(f"阻塞版耗时: {time.perf_counter() - start:.2f}s")

asyncio.run(main())
```

**关键结论**：`async def` 里出现任何同步阻塞调用，就等于放弃了并发的意义。

---

## 2. 解法：`loop.run_in_executor` 把阻塞扔出主线程

`loop.run_in_executor(executor, func, *args)` 会把同步函数 `func(*args)` 投递到一个**执行器**（executor，`concurrent.futures.Executor` 的实现）中运行，并返回一个可 `await` 的 **Future**。事件循环只需在等待 Future 完成时去处理其他任务。

- `executor=None`：使用事件循环默认的 **ThreadPoolExecutor**（线程池）。
- `executor=ProcessPoolExecutor(...)`：使用**进程池**，绕过 GIL（全局解释器锁），适合 CPU 密集任务。

```python
import asyncio, time

def blocking_task(n):
    time.sleep(2)          # 同步阻塞，在别的线程里跑
    return f"task-{n} done"

async def main():
    loop = asyncio.get_running_loop()
    start = time.perf_counter()
    # 三个阻塞任务并发丢进默认线程池
    results = await asyncio.gather(
        loop.run_in_executor(None, blocking_task, 1),
        loop.run_in_executor(None, blocking_task, 2),
        loop.run_in_executor(None, blocking_task, 3),
    )
    # 约 2 秒完成（并发），而非 6 秒
    print(f"并发版耗时: {time.perf_counter() - start:.2f}s")
    print(results)

asyncio.run(main())
```

**关键结论**：`run_in_executor` 让同步代码“寄宿”在其它线程/进程，事件循环得以继续调度其他协程。

---

## 3. 正确获取 loop，以及参数如何传

`run_in_executor(self, executor, func, *args)` 是 **event loop 的方法**，不是 `asyncio` 顶层函数。常用写法：

```python
import asyncio

def add(a, b):
    return a + b

async def main():
    loop = asyncio.get_running_loop()          # 3.7+ 推荐
    # 注意：参数是位置参数，用 lambda 或 functools.partial 传关键字参数
    fut = loop.run_in_executor(None, add, 3, 5)
    print(await fut)                            # 8

    # 需要关键字参数时用 partial
    from functools import partial
    fut2 = loop.run_in_executor(None, partial(add, a=10, b=20))
    print(await fut2)                           # 30

asyncio.run(main())
```

**关键结论**：`run_in_executor` 只接受位置参数，关键字参数用 `functools.partial` 绑定。

---

## 4. 线程池 vs 进程池：该选哪个？

| 场景 | 推荐执行器 | 原因 |
| --- | --- | --- |
| I/O 阻塞（`requests`、文件读写、`time.sleep`） | `ThreadPoolExecutor`（默认） | GIL 在 I/O 时会释放，线程有效 |
| CPU 密集（数值计算、图像处理） | `ProcessPoolExecutor` | 绕过 GIL，真正并行 |
| 高度受限的并发量 | 自定义 `max_workers` | 避免线程/进程爆炸 |

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

def compute(n):
    return sum(i * i for i in range(n))

async def main():
    loop = asyncio.get_running_loop()
    # I/O 用线程池
    with ThreadPoolExecutor(max_workers=4) as tpool:
        r1 = await loop.run_in_executor(tpool, compute, 1000)
    # CPU 密集用进程池（注意：被调用函数必须可 pickle）
    with ProcessPoolExecutor(max_workers=2) as ppool:
        r2 = await loop.run_in_executor(ppool, compute, 10_000)
    print(r1, r2)

asyncio.run(main())
```

**关键结论**：I/O 密集型用线程池，CPU 密集型用进程池；进程池要求函数、参数、返回值都可被序列化。

---

## 5. 与 `asyncio.to_thread` 的关系（3.9+ 的语法糖）

Python 3.9 起提供 `asyncio.to_thread(func, *args)`，本质就是 `loop.run_in_executor(None, func, *args)` 的便捷封装：

```python
import asyncio, time

def blocking():
    time.sleep(1)
    return "ok"

async def main():
    # 两行等价
    r1 = await asyncio.get_running_loop().run_in_executor(None, blocking)
    r2 = await asyncio.to_thread(blocking)
    print(r1, r2)

asyncio.run(main())
```

**关键结论**：日常用默认线程池时，`asyncio.to_thread` 更简洁；需要自定义执行器（尤其是进程池）时，仍要直接使用 `run_in_executor`。

```python
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor

# 模拟一个同步阻塞的 I/O 任务（例如 requests.get）
def fetch(url_id: int) -> str:
    time.sleep(1)                 # 模拟网络延迟
    return f"url-{url_id} 的内容"

async def fetch_all():
    loop = asyncio.get_running_loop()
    start = time.perf_counter()

    # 在并发协程里，用线程池跑 5 个同步阻塞任务
    with ThreadPoolExecutor(max_workers=5) as pool:
        tasks = [loop.run_in_executor(pool, fetch, i) for i in range(1, 6)]
        results = await asyncio.gather(*tasks)

    elapsed = time.perf_counter() - start
    for r in results:
        print(r)
    print(f"总耗时: {elapsed:.2f}s（并发约为 1s，而非 5s）")

if __name__ == "__main__":
    asyncio.run(fetch_all())
```


---

## 本课题目

### single_choice · None



- [A] time.sleep(2) 只会暂停任务 A，任务 B 可以继续运行
- [B] time.sleep(2) 会阻塞整个事件循环，任务 B 在这 2 秒内无法得到执行
- [C] time.sleep(2) 会自动被 asyncio 转换为异步等待，两个任务轮流执行
- [D] 任务 B 会抢在 time.sleep(2) 之前执行完毕，然后事件循环再处理任务 A

**参考答案**：1

**解析**：time.sleep 是同步阻塞调用，会占住当前线程，而 asyncio 事件循环运行在该线程上，因此整个循环被卡住，其他任务无法推进。

### single_choice · None



- [A] requests.get 不是协程，语法错误，程序无法运行
- [B] requests.get 会立即返回一个 Future 对象，需要 await
- [C] requests.get 是同步阻塞调用，会卡住事件循环，使其他任务无法并发执行
- [D] requests.get 会自动运行在子线程中，因此不会阻塞事件循环

**参考答案**：2

**解析**：requests 是同步 HTTP 库，在协程中直接调用会阻塞事件循环。要避免应使用 asyncio 兼容库或通过 executor 卸载到线程。

### single_choice · None



- [A] 调用 time.sleep(5)
- [B] 调用 requests.post(url, data=payload)
- [C] await asyncio.sleep(5)
- [D] 在一个大列表上执行同步的 sorted() 且数据量极大

**参考答案**：2

**解析**：await asyncio.sleep 是异步等待，会挂起当前任务；其余三项都是同步操作，会占用事件循环线程。

### single_choice · None



- [A] 使用 asyncio.to_thread 将调用卸载到线程池
- [B] 使用 loop.run_in_executor 将调用卸载到线程池
- [C] 直接在协程中调用该同步库，依赖 asyncio 自动调度
- [D] 在进程池中执行该同步库调用，并通过 await 获取结果

**参考答案**：2

**解析**：asyncio 不会自动调度同步阻塞调用，直接调用会阻塞事件循环。推荐用线程池或进程池卸载。

### single_choice · None



- [A] 每 0.5 秒让出一次控制权，其他任务可以并发执行
- [B] 整个循环期间事件循环被阻塞，其他任务无法运行
- [C] time.sleep 会自动转换为 asyncio.sleep，效果相同
- [D] 循环中的 print 会阻塞事件循环，time.sleep 不会

**参考答案**：1

**解析**：time.sleep 是同步阻塞调用，整个循环期间事件循环被占用，其他任务无法推进。

### single_choice · None



- [A] 默认线程池大小无限，可以随意提交大量阻塞任务
- [B] 默认线程池有大小限制，过度提交阻塞任务可能导致后续任务排队等待
- [C] 线程池中的任务不会被事件循环调度，因此无法通过 await 获取结果
- [D] 线程池只能运行纯计算函数，不能运行 I/O 函数

**参考答案**：1

**解析**：默认 ThreadPoolExecutor 的线程数有限，若大量阻塞任务占满线程，后续任务会排队；通过 await 仍可获得 executor 的结果。

### single_choice · None



- [A] 把事件循环的 debug 模式打开
- [B] 使用 asyncio.run 多次启动事件循环
- [C] 把同步阻塞调用放到线程池或进程池中执行
- [D] 在同步阻塞调用前加 await

**参考答案**：2

**解析**：把阻塞调用卸载到线程池/进程池可以避免阻塞事件循环；debug 模式、多次启动循环、给同步函数加 await 都不能解决阻塞。

### single_choice · None



- [A] asyncio.sleep
- [B] asyncio.gather
- [C] time.sleep
- [D] asyncio.wait_for

**参考答案**：2

**解析**：time.sleep 是同步阻塞函数；其他三项都是 asyncio 提供的异步工具，不会长时间阻塞事件循环。

### single_choice · None



- [A] 事件循环会检测到阻塞并自动切换到其他任务
- [B] 其他任务会暂时无法运行，直到该同步调用返回
- [C] 同步调用会立即抛出 BlockingIOError
- [D] 事件循环会创建一个新线程来接管其他任务

**参考答案**：1

**解析**：同步调用会占住事件循环线程，其他任务只能等待直到调用返回；asyncio 不会自动检测并切换，也不会自动创建接管线程。

### single_choice · None



- [A] 把同步 I/O 换成对应的异步库，并使用 await 调用
- [B] 在同步 I/O 外层加一个 for 循环
- [C] 把同步 I/O 放在 async def 函数中直接调用
- [D] 给同步 I/O 函数加装饰器 @asyncio.coroutine

**参考答案**：0

**解析**：使用对应的异步库并通过 await 调用是根本解决办法；仅把同步调用放进 async def 或用已废弃的装饰器都无法避免阻塞。

### single_choice · None



- [A] 该视图函数会自动在子线程中执行，不影响其他请求
- [B] 整个服务进程可能无法及时处理其他并发请求
- [C] 框架会自动抛出异常并拒绝该请求
- [D] 同步操作会被自动转换为异步操作，性能不受影响

**参考答案**：1

**解析**：同步耗时操作会阻塞事件循环，导致整个服务进程无法及时处理其他并发请求；框架不会自动把它转到子线程或转为异步。

### single_choice · None



- [A] 两者没有区别，都会阻塞当前线程
- [B] 在协程中调用会阻塞事件循环，影响同一循环上的其他任务；在同步函数中调用只影响当前线程
- [C] 在协程中调用不会阻塞任何东西，因为协程是可中断的
- [D] 在同步函数中调用会自动转为异步，不会阻塞

**参考答案**：1

**解析**：两者都会阻塞当前线程，但当当前线程是事件循环线程时，阻塞会波及循环上的所有任务；在普通同步函数中调用只影响该线程自身。

### single_choice · None



- [A] 直接调用同步函数，并在前面加 await
- [B] 使用 asyncio.to_thread 或 loop.run_in_executor 把同步函数放到线程/进程池中执行
- [C] 用 asyncio.create_task 包装同步函数，让它变成协程
- [D] 在同步函数前加 async 关键字，把它改成异步函数

**参考答案**：1

**解析**：把阻塞函数交给 executor 是标准做法，可以避免阻塞事件循环；await 同步函数、create_task 包装普通函数、给同步函数加 async 都不能解决阻塞问题。

### single_choice · None



- [A] 它会把传入的函数自动转换为协程函数，之后不再阻塞
- [B] 它会在线程池中执行传入的同步函数，并返回可等待对象
- [C] 它会终止当前事件循环并重新启动一个新循环
- [D] 它只能用于 CPU 密集任务，不能用于 I/O 密集任务

**参考答案**：1

**解析**：asyncio.to_thread 将同步函数卸载到默认线程池执行，返回一个可 await 的对象。它不会改变函数本身的性质，也不重启事件循环。

### single_choice · None



- [A] 两者都会让出控制权，只是精度不同
- [B] time.sleep 会阻塞事件循环；asyncio.sleep 会挂起当前任务并让事件循环继续调度其他任务
- [C] asyncio.sleep 不能睡整数秒，只能接收小数
- [D] time.sleep 只能在主线程使用，asyncio.sleep 只能在子线程使用

**参考答案**：1

**解析**：asyncio.sleep 是协程，await 时会挂起当前任务并交还控制权；time.sleep 是同步阻塞调用，会卡住整个事件循环。

### single_choice · None



- [A] 因为 open(...).read() 是同步 I/O，会阻塞事件循环
- [B] 因为 async def 定义的函数默认在独立线程运行
- [C] 因为 return 前必须调用 await，否则事件循环不会继续
- [D] 因为 asyncio 不支持文件操作，任何文件读取都会报错

**参考答案**：0

**解析**：同步文件 I/O 会阻塞当前线程，而事件循环运行在该线程上，所以其他任务无法推进。应使用异步文件库或 executor。

### single_choice · None



- [A] await asyncio.sleep(0.1)
- [B] await asyncio.gather(task1, task2)
- [C] socket.recv(1024) 在非阻塞套接字上调用
- [D] urllib.request.urlopen('https://example.com').read()

**参考答案**：3

**解析**：urllib.request.urlopen 是同步 HTTP 调用，会阻塞事件循环；asyncio.sleep 与 gather 是异步等待，非阻塞套接字上的 recv 也不会长时间阻塞。

### single_choice · None



- [A] CPU 密集计算不会阻塞事件循环，因为 asyncio 会自动切换任务
- [B] 只要计算函数是 async def 定义，就不会阻塞事件循环
- [C] CPU 密集计算会占用事件循环线程，应放到进程池或线程池中执行
- [D] CPU 密集计算必须用 await 调用，否则会抛出异常

**参考答案**：2

**解析**：CPU 密集计算会持续占用事件循环线程，asyncio 不会自动抢占；应通过 executor 或 ProcessPoolExecutor 卸载。

### single_choice · None



- [A] await blocking_func()
- [B] async with blocking_func():
- [C] loop.run_in_executor(None, blocking_func)
- [D] asyncio.create_task(blocking_func())

**参考答案**：2

**解析**：run_in_executor 把同步函数交给线程/进程池执行；await 同步函数会报错或无效，async with 需要异步上下文管理器，create_task 需要协程对象。

### single_choice · None



- [A] 同步数据库驱动查询会阻塞事件循环，使其他请求无法及时处理
- [B] 异步服务器不能连接任何数据库，必须改用同步服务器
- [C] 同步数据库驱动会自动把请求排队到下一轮事件循环
- [D] 数据库驱动本身是异步的，只是版本过低

**参考答案**：0

**解析**：同步驱动在事件循环线程中执行阻塞 I/O，导致其他请求无法推进。应使用异步驱动或把调用卸载到线程池。

### single_choice · None



- [A] 直接在协程里调用该同步函数，因为它很快
- [B] 使用 loop.run_in_executor 把它提交给线程池或进程池执行
- [C] 用 asyncio.sleep 包裹该函数
- [D] 把该函数改成 async def 并直接 await

**参考答案**：1

**解析**：run_in_executor 的作用就是把阻塞式可调用对象提交给 executor（线程池或进程池）执行，避免阻塞事件循环；直接调用会卡住整个循环，asyncio.sleep 无法解决阻塞，仅改成 async def 也不会真正并行。

### single_choice · None



- [A] 表示不执行该函数，直接返回 None
- [B] 表示使用事件循环默认的 ThreadPoolExecutor
- [C] 表示必须在主线程中同步执行
- [D] 表示使用 ProcessPoolExecutor

**参考答案**：1

**解析**：当 executor 传 None 时，事件循环会使用其默认的线程池（ThreadPoolExecutor）。它不会拒绝执行，也不代表进程池。

### multi_choice · None



- [A] 线程池中的函数无法直接调用 asyncio 的协程 API
- [B] 通过 asyncio.wait_for 超时不会强制终止已在运行的同步函数
- [C] 默认线程池大小可能成为性能瓶颈，必要时需自行创建 executor
- [D] run_in_executor 提交的函数返回值必须可被 pickle

**参考答案**：[0, 1, 2]

**解析**：工作线程没有运行的事件循环，不能直接调用协程 API；超时只取消等待；默认线程池默认 max_workers 有限，高并发时可能成为瓶颈。只有使用进程池时才涉及 pickle 序列化，线程池不要求。

### multi_choice · None



- [A] 用 functools.partial 预先固定参数
- [B] 在函数内部捕获异常并返回错误标识，避免异常在 Future 中丢失
- [C] 把事件循环对象传给该同步函数，让它在内部调用 loop.call_soon
- [D] 为高并发场景自定义 ThreadPoolExecutor 并控制 max_workers

**参考答案**：[0, 1, 3]

**解析**：partial 便于传参，捕获异常可避免漏处理，自定义 executor 可控制并发；把事件循环对象传给同步函数并调用 loop 方法并非推荐做法，容易引发线程安全问题。

### fill_blank · None



**参考答案**：["None", "none"]

**解析**：executor 参数为 None 时表示使用事件循环默认的 ThreadPoolExecutor。

### fill_blank · None



**参考答案**：["partial", "functools.partial"]

**解析**：functools.partial 可以预先把关键字参数绑定到可调用对象上，再整体交给 run_in_executor。

### fill_blank · None



**参考答案**：["Process", "ProcessPoolExecutor", "ProcessPool"]

**解析**：进程池使用独立进程，绕开 GIL 限制，适合 CPU 密集型任务。

### code_reading · None



**参考答案**：约 1 秒。因为四个 work 调用被提交到默认线程池并发执行，每个睡眠 1 秒，gather 等待所有结果，线程池默认允许至少 4 个 worker 并行，所以总耗时接近 1 秒而非 4 秒。

**解析**：run_in_executor 返回的多个 awaitable 被 asyncio.gather 一起等待，线程池可以并行处理这些阻塞调用，因此总时长由最慢的一个决定。

### code_reading · None



**参考答案**：打印 caught。同步函数在线程池中抛出的异常会被保存到返回的 Future，await 该 Future 时会重新抛出 ZeroDivisionError。

**解析**：run_in_executor 返回对象在被 await 时，会把工作线程中的异常传播到协程，因此 try/except 可以捕获到。

### scenario · None



**解析**：把阻塞的同步写日志调用通过 loop.run_in_executor 提交到线程池，可以让事件循环不再被 fsync 阻塞，其他协程得以继续调度，从而提高并发吞吐。

### scenario · None



**解析**：executor 为 None 时默认使用线程池，而线程池中的 Python 代码受 GIL 限制，CPU 密集型任务无法真正并行。应改用 ProcessPoolExecutor（或 concurrent.futures.ProcessPoolExecutor）来绕开 GIL。

### scenario · None



**解析**：wait_for 超时只是取消等待，线程池中的同步函数不会收到取消信号，会继续占用线程直至结束。可通过限制并发、为这类任务使用独立且有上限的 executor、设置合理的超时与队列策略、或为阻塞操作使用支持取消的异步替代方案来缓解。

### single_choice · None



- [A] 事件循环被阻塞 2 秒，然后打印 42
- [B] blocking 在线程池中执行，事件循环在此期间仍可调度其他任务，2 秒后打印 42
- [C] 程序立即打印 42
- [D] 抛出 RuntimeError，因为不能在协程里使用线程池

**参考答案**：1

**解析**：run_in_executor 将 blocking 交给默认线程池，await 期间事件循环可继续运行其他任务，blocking 完成后返回 42。

### single_choice · None



- [A] 任务主要是等待网络 I/O
- [B] 任务是 CPU 密集型计算，且受 GIL 限制无法通过线程并行
- [C] 任务只是简单的字符串拼接
- [D] 任务需要访问 asyncio 的事件循环对象

**参考答案**：1

**解析**：CPU 密集型任务受 GIL 影响，线程无法真正并行，使用进程池可绕开 GIL；网络 I/O 用线程池即可；简单计算没必要；进程池中的对象无法直接访问父进程的事件循环。

### single_choice · None



- [A] 一个普通的 Python 值
- [B] 一个 concurrent.futures.Future
- [C] 一个 asyncio.Future（通常并非直接返回）
- [D] 一个可等待的 asyncio.Task 对象

**参考答案**：1

**解析**：run_in_executor 返回 concurrent.futures.Future 的包装结果，在 asyncio 里表现为可 await 的对象，但其底层是 concurrent.futures.Future。常见误解是认为它直接返回普通值或 asyncio.Future。

### single_choice · None



- [A] 对 run_in_executor 返回的 awaitable 使用 asyncio.wait_for 超时后，线程池中的函数一定立即停止
- [B] 对 run_in_executor 返回的 awaitable 使用 asyncio.wait_for 超时后，await 会抛出 TimeoutError，但线程池中的函数可能仍在继续运行
- [C] run_in_executor 提交的任务一旦开始就无法被取消
- [D] 只有进程池中的任务才能被取消

**参考答案**：1

**解析**：asyncio.wait_for 取消的是等待，线程池中的同步函数不会收到取消信号，通常会继续执行到结束。因此超时只影响等待方，不会强制终止底层函数。

### single_choice · None



- [A] 不会，每次都创建新的线程池
- [B] 会，executor 为 None 时使用循环的默认线程池，两次调用共享
- [C] 取决于 func1 和 func2 是否相同
- [D] 只有在同一协程中才会共享

**参考答案**：1

**解析**：executor 为 None 时使用事件循环的默认 ThreadPoolExecutor，多次调用共享同一个默认线程池。

### single_choice · None



- [A] run_in_executor 直接支持 **kwargs，直接写 loop.run_in_executor(None, func, a=1)
- [B] run_in_executor 只接受位置参数，需用 functools.partial 包装后再提交
- [C] 必须先定义带默认值的包装函数，不能用 partial
- [D] 只能传一个参数

**参考答案**：1

**解析**：run_in_executor 只把额外参数作为位置参数传递给底层函数，不支持 **kwargs；常见做法是用 functools.partial 固定关键字参数。

### multi_choice · None



- [A] 它可以把阻塞调用移出事件循环线程，避免阻塞其他协程
- [B] executor 为 None 时使用默认线程池
- [C] 被提交的函数一定在事件循环所在线程中运行
- [D] 它返回的对象可以被 await

**参考答案**：[0, 1, 3]

**解析**：run_in_executor 的核心价值是把阻塞调用移出事件循环线程，返回可 await 的对象，executor=None 使用默认线程池；被提交的函数在线程池/进程池的工作线程中运行，不在事件循环线程中。

### multi_choice · None



- [A] 调用只提供同步接口的第三方库（如某些数据库驱动）
- [B] 执行 CPU 密集型计算并希望利用多核
- [C] 使用 requests 发起阻塞式 HTTP 请求
- [D] 在协程中需要 sleep 一段时间

**参考答案**：[0, 1, 2]

**解析**：同步第三方库、CPU 密集型计算、阻塞式 HTTP 请求都可借助 run_in_executor 放到线程/进程池；协程中睡眠应直接用 await asyncio.sleep，无需 executor。
