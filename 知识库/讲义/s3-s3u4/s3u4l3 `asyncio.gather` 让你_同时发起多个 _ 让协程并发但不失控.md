# s3u4l3 `asyncio.gather` 让你**同时发起多个 / 让协程并发但不失控

> 来源 `content/lessons/s3u4l3.json`

## py.async.gather

## 一句话直觉

`asyncio.gather` 让你**同时发起多个 IO 等待**，然后一次性把它们的结果收集齐——比如同时下载 10 张图片，总耗时约等于最慢的那一张，而不是 10 张加起来。

---

## 1. 先理解「协程」和「事件循环」

`async def` 定义的函数叫**协程函数**（coroutine function），调用它并不会立刻执行，而是返回一个**协程对象**（coroutine object）。协程只有在被 **`await`** 或被事件循环调度时才会真正跑起来。

- **事件循环**（event loop）：asyncio 的「调度中心」，负责在等待 IO 时切走、IO 就绪时切回。
- **`asyncio.run(main())`**：启动事件循环，跑完 `main` 再关闭，是程序的入口。

```python
import asyncio

async def main():
    print('Hello ...')
    await asyncio.sleep(1)  # 挂起 1 秒，期间事件循环可以去做别的事
    print('... World!')

asyncio.run(main())
```

**关键点**：`await` 不是「阻塞等待」，而是「挂起自己，把控制权交还事件循环」。

---

## 2. 顺序 await 的问题：时间被白白叠加

最直觉的写法是先 `await` 第一个、再 `await` 第二个。但它们**不是在等待中并行**，而是严格串行。

```python
import asyncio, time

async def fetch(name, delay):
    await asyncio.sleep(delay)   # 模拟一次网络 IO
    return f'{name} done'

async def main():
    t0 = time.perf_counter()
    r1 = await fetch('A', 1)     # 等 1 秒
    r2 = await fetch('B', 1)     # 再等 1 秒
    print(r1, r2, f'{time.perf_counter() - t0:.2f}s')

asyncio.run(main())
# 输出大约：A done B done 2.00s
```

**关键点**：串行 `await` 的总耗时是各任务之和。IO 密集场景下这非常浪费。

---

## 3. `asyncio.gather`：并发收集结果

`asyncio.gather(*aws)` 接收多个 **awaitable**（协程、Task、Future），把它们**同时调度**到事件循环上，等全部完成后返回一个**结果列表**，顺序与传入顺序一致。

```python
import asyncio, time

async def fetch(name, delay):
    await asyncio.sleep(delay)
    return f'{name} done'

async def main():
    t0 = time.perf_counter()
    results = await asyncio.gather(
        fetch('A', 1),
        fetch('B', 1),
        fetch('C', 1),
    )
    print(results)
    print(f'{time.perf_counter() - t0:.2f}s')

asyncio.run(main())
# 输出大约：['A done', 'B done', 'C done']  1.00s
```

**关键点**：三个任务共享同一个 1 秒等待窗口，总耗时 ≈ 1 秒而非 3 秒。返回值是**列表**，顺序和传入顺序一致，和谁先完成无关。

---

## 4. 用列表动态传入任务

实际工程里任务数量往往不固定。`gather` 支持 `*args` 解包，所以把协程放进列表再 `*` 展开即可。

```python
import asyncio, time

async def fetch(i):
    await asyncio.sleep(0.5)
    return i * i

async def main():
    tasks = [fetch(i) for i in range(5)]  # 注意：这里还没开始跑
    results = await asyncio.gather(*tasks)
    print(results)   # [0, 1, 4, 9, 16]

asyncio.run(main())
```

**关键点**：构造协程对象本身不执行任何事；真正「开始」发生在 `gather` 调度它们的瞬间。

---

## 5. 错误处理与 `return_exceptions`

默认情况下，只要**任何一个任务抛异常**，`gather` 会立刻把该异常抛出，其余任务虽然继续跑，但它们的结果你不会拿到。工程上常用 `return_exceptions=True` 让所有任务都跑完，异常作为**结果项**返回。

```python
import asyncio

async def ok():
    return 'OK'

async def boom():
    raise ValueError('出错了')

async def main():
    # 默认：第一个异常直接向上抛
    try:
        await asyncio.gather(ok(), boom())
    except ValueError as e:
        print('默认捕获到:', e)

    # 收集模式：异常作为结果返回
    results = await asyncio.gather(ok(), boom(), return_exceptions=True)
    print(results)   # ['OK', ValueError('出错了')]

asyncio.run(main())
```

**关键点**：`return_exceptions=True` 是「不中断、全收集」的模式；`except` 时要判断类型。

---

## 6. 进阶：`gather` 返回的 Future 与取消

`gather` 返回一个 **Future**（`asyncio.Future`）。在 await 它之前，你其实已经持有它了；可以调用 `.cancel()` 取消整体。协程默认**不被事件循环持有**，`gather` 会先把它们包装成 **Task** 再调度——所以取消才能穿透。

```python
import asyncio

async def slow():
    await asyncio.sleep(5)
    return 'never'

async def main():
    fut = asyncio.gather(slow(), slow())
    loop = asyncio.get_running_loop()
    loop.call_later(0.5, fut.cancel)   # 半秒后取消全部
    try:
        await fut
    except asyncio.CancelledError:
        print('已被取消')

asyncio.run(main())
```

**关键点**：`gather` 的返回对象可被当作句柄；取消它会连带取消内部所有子任务。

---

## 7. 与 `asyncio.TaskGroup`（3.11+）的关系

Python 3.11 引入了结构化并发的 **`TaskGroup`**，语义上比 `gather` 更严格：任务必须全部成功，否则整体取消。`gather` 依然适合「我要逐个收结果、允许部分失败」的场景。

```python
import asyncio

async def fetch(i):
    await asyncio.sleep(0.1)
    return i

async def main():
    async with asyncio.TaskGroup() as tg:
        t1 = tg.create_task(fetch(1))
        t2 = tg.create_task(fetch(2))
    print(t1.result(), t2.result())   # 1 2

asyncio.run(main())
```

**关键点**：`gather` 是「收集式」；`TaskGroup` 是「团队式」（一个失败，全体取消）。二者互补。

---

## 8. 小结

| 场景 | 推荐写法 |
|---|---|
| 定长并发、需要结果列表 | `await asyncio.gather(*coros)` |
| 允许部分失败 | `await asyncio.gather(*coros, return_exceptions=True)` |
| 失败即全体取消 | `async with asyncio.TaskGroup()` |
| 需要任务句柄 | `task = asyncio.create_task(coro)` |

---

## 动手练习

写一个脚本 `bench_gather.py`：

1. 定义 `async def fetch(url_id: int) -> str`，内部 `await asyncio.sleep(random.uniform(0.5, 1.5))`，返回 `f'url_{url_id} 响应完成'`。
2. 用**串行 await** 跑 5 个 `fetch`，记录耗时。
3. 用 **`asyncio.gather`** 跑同样 5 个 `fetch`，记录耗时。
4. 打印两次耗时，并解释为什么 `gather` 那次大约只有串行的一半以内。
5. 加分项：把其中一个 `fetch` 改成抛异常，分别测试默认行为和 `return_exceptions=True` 的行为，打印结果。

运行方式：`python bench_gather.py`（Python 3.10+ 均可）。

```python
import asyncio
import random
import time


async def fetch(url_id: int) -> str:
    """模拟一次耗时的网络请求。"""
    await asyncio.sleep(random.uniform(0.5, 1.5))
    return f'url_{url_id} 响应完成'


async def serial() -> None:
    t0 = time.perf_counter()
    results = [await fetch(i) for i in range(5)]  # 串行 await
    print('串行结果:', results)
    print(f'串行耗时: {time.perf_counter() - t0:.2f}s')


async def concurrent() -> None:
    t0 = time.perf_counter()
    results = await asyncio.gather(*(fetch(i) for i in range(5)))
    print('并发结果:', results)
    print(f'并发耗时: {time.perf_counter() - t0:.2f}s')


async def main() -> None:
    await serial()
    print('-' * 30)
    await concurrent()


if __name__ == '__main__':
    asyncio.run(main())
```

## py.async.wait

# py.async.wait：让协程并发但不失控

## 一句话直觉

> 你有一堆异步任务要并发跑，但你不想让它们无限等待——`asyncio.wait()` 就是你的“超时控制器”和“第一个完成就继续”的工具。

---

## 1. 为什么需要 asyncio.wait？

在 Python 异步编程中，`asyncio` 是标准库提供的异步 I/O（Asynchronous I/O）框架。你可以用 `async def` 定义**协程（coroutine）**，用 `await` 等待它执行。

但问题来了：如果你有 10 个网络请求，一个一个 `await`，总耗时是它们的和——这太慢了。你需要**并发（concurrency）**。

`asyncio.gather()` 可以并发等待所有任务，但它有个限制：**你必须等全部完成**。如果你只想要“谁先完成就先处理谁”，或者“最多等 3 秒，没完成的就放弃”，`gather()` 就做不到了。

这时候 `asyncio.wait()` 登场。它是 `asyncio` 中用于**并发等待多个任务（Task）或 Future** 的低层但灵活的工具。

```python
# 对比：gather 必须等全部完成
results = await asyncio.gather(task1, task2, task3)  # 全部完成才返回

# wait 可以控制等待条件
done, pending = await asyncio.wait(
    [task1, task2, task3],
    timeout=3.0,                  # 最多等 3 秒
    return_when=asyncio.FIRST_COMPLETED  # 有一个完成就返回
)
# done 是已完成的任务集合，pending 是还没完成的任务集合
```

---

## 2. 基本用法：三个关键参数

`asyncio.wait()` 的签名（简化版）如下：

```python
asyncio.wait(aws, *, timeout=None, return_when=ALL_COMPLETED)
```

### 参数说明

| 参数 | 含义 | 默认值 |
|------|------|--------|
| `aws` | 可等待对象（awaitable）的**可迭代集合**，通常是 `Task` 或 `Future` | 必填 |
| `timeout` | 超时秒数（float），超时后未完成的任务会被放入 `pending` | `None`（永不超时） |
| `return_when` | 何时返回，有三个常量 | `ALL_COMPLETED` |

### `return_when` 的三个取值

- `asyncio.ALL_COMPLETED`：所有任务完成才返回（默认）
- `asyncio.FIRST_COMPLETED`：任意一个任务完成就返回
- `asyncio.FIRST_EXCEPTION`：任意一个任务**抛出异常**就返回；如果都没异常，则等全部完成

### 返回值

返回一个**二元组** `(done, pending)`：

- `done`：已完成的任务集合（`set` of `Task`）
- `pending`：未完成的任务集合（`set` of `Task`）

> ⚠️ 注意：`wait()` **不会取消** `pending` 中的任务。你需要自己决定是否 `cancel()` 它们。

```python
import asyncio

async def worker(name: str, delay: float) -> str:
    """一个模拟耗时的异步任务。"""
    await asyncio.sleep(delay)
    return f"{name} 完成（耗时 {delay}s）"

async def main():
    # 创建 3 个任务
    tasks = [
        asyncio.create_task(worker("A", 1.0)),
        asyncio.create_task(worker("B", 2.0)),
        asyncio.create_task(worker("C", 0.5)),
    ]

    # 等待第一个完成
    done, pending = await asyncio.wait(
        tasks,
        return_when=asyncio.FIRST_COMPLETED
    )

    print(f"已完成: {len(done)} 个, 未完成: {len(pending)} 个")
    for t in done:
        print("  ->", t.result())

    # 取消剩余任务
    for t in pending:
        t.cancel()
    await asyncio.gather(*pending, return_exceptions=True)

asyncio.run(main())
```

---

## 3. 超时控制：timeout 参数的威力

`timeout` 是 `wait()` 区别于 `gather()` 的核心能力之一。设想你在写一个爬虫，某个网站响应极慢，你不想无限等下去。

```python
import asyncio
import time

async def fetch(url: str, delay: float) -> str:
    """模拟网络请求。"""
    await asyncio.sleep(delay)
    return f"{url} 响应成功"

async def main():
    start = time.perf_counter()

    tasks = [
        asyncio.create_task(fetch("site-fast.com", 0.5)),
        asyncio.create_task(fetch("site-slow.com", 5.0)),   # 很慢
        asyncio.create_task(fetch("site-medium.com", 1.5)),
    ]

    done, pending = await asyncio.wait(tasks, timeout=2.0)

    elapsed = time.perf_counter() - start
    print(f"实际耗时: {elapsed:.2f}s")  # 约 2 秒，而不是 5 秒
    print(f"成功: {len(done)} 个, 超时: {len(pending)} 个")

    for t in done:
        print("  ✓", t.result())

    # 超时的任务必须取消，否则会继续在后台运行
    for t in pending:
        t.cancel()
        print("  ✗ 已取消:", t.get_name())

    await asyncio.gather(*pending, return_exceptions=True)

asyncio.run(main())
```

**关键结论**：`timeout` 到点后，`wait()` 立即返回，但 `pending` 里的任务**仍在事件循环中运行**。不取消它们，程序退出时可能报 `Task was destroyed but it is pending!` 警告。

---

## 4. 实战模式：谁先完成就用谁（竞速）

一个经典场景：你有多个数据源（比如多个镜像站点），想取**最快响应**的那个结果。

```python
import asyncio
import random

async def mirror_fetch(mirror: str) -> str:
    """模拟从镜像站取数据，响应时间随机。"""
    delay = random.uniform(0.3, 2.0)
    await asyncio.sleep(delay)
    return f"数据来自 {mirror}（{delay:.2f}s）"

async def main():
    mirrors = ["mirror-1", "mirror-2", "mirror-3", "mirror-4"]
    tasks = [asyncio.create_task(mirror_fetch(m)) for m in mirrors]

    done, pending = await asyncio.wait(
        tasks,
        return_when=asyncio.FIRST_COMPLETED
    )

    # 取第一个完成的结果
    winner = next(iter(done))
    print("最快结果:", winner.result())

    # 取消其他的
    for t in pending:
        t.cancel()
    await asyncio.gather(*pending, return_exceptions=True)

asyncio.run(main())
```

---

## 5. 与 gather 的对比与选择

| 特性 | `asyncio.wait()` | `asyncio.gather()` |
|------|------------------|---------------------|
| 等待条件 | 可配置（全部/首个/首个异常） | 固定：全部完成 |
| 超时支持 | ✅ `timeout` 参数 | ❌ 需配合 `asyncio.wait_for()` |
| 返回值 | `(done, pending)` 集合 | 结果列表（保持顺序） |
| 异常处理 | 需手动检查 | 可 `return_exceptions=True` |
| 适合场景 | 竞速、超时控制、部分完成就处理 | 批量等待全部结果 |

**选择原则**：
- 要全部结果 → `gather()`
- 要超时控制或首个完成 → `wait()`
- 要取消超时任务，`wait()` + 手动 `cancel()`

---

## 6. Python 3.11+ 的变化（工程级注意）

> **重要**：Python 3.11 起，`asyncio.wait()` **不再接受协程（coroutine）对象**，必须传入 `Task` 或 `Future`。

```python
# ❌ Python 3.11+ 会报 TypeError
await asyncio.wait([my_coro(), my_coro()])

# ✅ 必须用 create_task 包装
await asyncio.wait([
    asyncio.create_task(my_coro()),
    asyncio.create_task(my_coro()),
])
```

在 3.8 之前会隐式包装成 Task，但 3.8 起弃用，3.11 起移除。这是生产代码中最容易踩的坑。

---

## 7. 动手练习

**任务**：写一个“多源竞速下载器”。

要求：
1. 定义 `async def fake_download(source: str, delay: float) -> str`，`await asyncio.sleep(delay)` 后返回 `f"{source} 下载完成"`。
2. 创建 5 个任务，delay 分别在 0.5 到 5.0 秒之间随机。
3. 用 `asyncio.wait()` 设置 **3 秒超时**，`return_when=FIRST_COMPLETED`。
4. 打印：
   - 总耗时
   - 已完成的任务及其结果
   - 超时/未完成的任务数量
5. 取消所有 `pending` 任务，并用 `asyncio.gather(*pending, return_exceptions=True)` 等待清理。

**进阶挑战**：改成“**先完成 2 个就返回**”的行为。提示：循环调用 `wait()`，每次从 `pending` 中剔除已完成的，直到 `done` 累计到 2 个。

参考代码框架：

```python
import asyncio
import random
import time

async def fake_download(source: str, delay: float) -> str:
    await asyncio.sleep(delay)
    return f"{source} 下载完成"

async def main():
    sources = [f"source-{i}" for i in range(1, 6)]
    tasks = [
        asyncio.create_task(fake_download(s, random.uniform(0.5, 5.0)))
        for s in sources
    ]

    start = time.perf_counter()
    done, pending = await asyncio.wait(tasks, timeout=3.0)
    elapsed = time.perf_counter() - start

    print(f"总耗时: {elapsed:.2f}s")
    print(f"已完成 {len(done)} 个, 未完成 {len(pending)} 个")
    for t in done:
        print("  ✓", t.result())

    for t in pending:
        t.cancel()
    await asyncio.gather(*pending, return_exceptions=True)

asyncio.run(main())
```

```python
import asyncio
import random
import time

async def fake_download(source: str, delay: float) -> str:
    """模拟异步下载，延迟 delay 秒后返回结果。"""
    await asyncio.sleep(delay)
    return f"{source} 下载完成（耗时 {delay:.2f}s）"

async def main():
    sources = [f"source-{i}" for i in range(1, 6)]
    delays = [random.uniform(0.5, 5.0) for _ in sources]

    # 创建任务（Python 3.11+ 必须传入 Task，不能传协程对象）
    tasks = [
        asyncio.create_task(fake_download(s, d))
        for s, d in zip(sources, delays)
    ]

    start = time.perf_counter()
    # 超时 3 秒，首个完成就返回
    done, pending = await asyncio.wait(
        tasks,
        timeout=3.0,
        return_when=asyncio.FIRST_COMPLETED,
    )
    elapsed = time.perf_counter() - start

    print(f"总耗时: {elapsed:.2f}s")
    print(f"已完成 {len(done)} 个, 未完成 {len(pending)} 个")
    for t in done:
        print("  ✓", t.result())

    # 取消未完成的任务，避免后台悬挂
    for t in pending:
        t.cancel()
    await asyncio.gather(*pending, return_exceptions=True)

asyncio.run(main())
```


---

## 本课题目

### single_choice · None



- [A] 它接收一组协程或可等待对象，并发调度它们，并返回一个按传入顺序排列的结果列表
- [B] 它只能接收一个协程，返回该协程的返回值
- [C] 它接收一组可调用对象，在事件循环中顺序执行它们
- [D] 它返回一个协程对象，必须再被 run 一次才会开始执行

**参考答案**：0

**解析**：asyncio.gather 接收多个 awaitable（协程、Task、Future），并发调度并按传入顺序返回结果列表，本身是一个可等待对象。

### single_choice · None



- [A] [2, 4, 6]
- [B] [6, 4, 2]
- [C] 2
- [D] (2, 4, 6)

**参考答案**：0

**解析**：gather 按传入顺序收集结果并返回 list，因此是 [2, 4, 6]。返回类型是 list 而不是 tuple。

### single_choice · None



- [A] 默认情况下，gather 内部尚未完成的子任务也会被取消
- [B] 子任务完全不受影响，会一直运行到结束
- [C] 子任务会自动重新启动一遍
- [D] 只有第一个子任务会被取消，其他继续运行

**参考答案**：0

**解析**：gather 的 Future 被取消时，会将取消传播给所有尚未完成的子任务（如它们尚未完成）。

### single_choice · None



- [A] 同时发起多个独立的网络请求，等全部返回后汇总结果
- [B] 顺序执行多个有依赖关系的步骤
- [C] 用多线程加速 CPU 密集型计算
- [D] 在同步函数中阻塞等待多个线程结束

**参考答案**：0

**解析**：gather 适合并发等待多个相互独立的 I/O 任务并汇总结果；有依赖步骤应顺序 await；CPU 密集型应使用多进程。

### single_choice · None



- [A] 写法一并发执行两个 f，写法二顺序执行
- [B] 写法一顺序执行，写法二并发执行
- [C] 两种写法完全等价
- [D] 写法一会在两个线程中运行，写法二在主线程运行

**参考答案**：0

**解析**：gather 把两个协程并发调度，而两次独立 await 是顺序等待。

### single_choice · None



- [A] gather 直接返回按传入顺序的结果列表；wait 返回 (done, pending) 两个集合
- [B] gather 返回 (done, pending)；wait 返回结果列表
- [C] 两者返回结构相同，只是参数名不同
- [D] wait 不能处理协程，只能处理 Task

**参考答案**：0

**解析**：gather 返回结果列表；wait 返回已完成和未完成集合，需要自己从任务对象取结果。

### single_choice · None



- [A] asyncio.gather(*[f(i) for i in range(5)], return_exceptions=True)
- [B] for i in range(5): await f(i)
- [C] asyncio.gather(*[f(i) for i in range(5)])
- [D] asyncio.wait([f(i) for i in range(5)])

**参考答案**：0

**解析**：return_exceptions=True 让异常也作为结果返回，配合 gather 可以拿到全部 5 项结果。

### single_choice · None



- [A] 它们不会被自动取消，仍会继续运行到结束，但结果无法通过 gather 返回值获取
- [B] 它们会立即被取消
- [C] 它们会被重新调度一次
- [D] 只有 f(1) 会继续，f(3) 被取消

**参考答案**：0

**解析**：默认情况下异常向调用方传播，但 gather 不会取消其他子任务；只是返回值不再可用，需要自行管理任务引用。

### single_choice · None



- [A] await asyncio.gather(*coros)
- [B] await asyncio.gather(coros)
- [C] await asyncio.gather(list(coros))
- [D] await asyncio.gather(*[coros])

**参考答案**：0

**解析**：gather 接收的是位置参数，需要把可迭代对象解包传入；直接传列表会被当成一个 awaitable 处理而报错。

### single_choice · None



- [A] gather 接收多个位置参数，可以是协程、Task 或 Future
- [B] gather 只接收 Future，不能接收协程
- [C] gather 接收一个列表，元素必须是 Task
- [D] gather 接收关键字参数 coros=[...]

**参考答案**：0

**解析**：gather 的位置参数可以是协程、Task 或 Future，内部统一包装为 Future 调度。

### single_choice · None



- [A] gather 会等待所有任务完成后才返回
- [B] gather 返回结果的顺序与传入顺序一致
- [C] gather 可以把协程包装成 Task 并发调度
- [D] gather 返回列表中的元素类型一定与每个任务的返回类型一致（return_exceptions=True 时异常对象除外）

**参考答案**：0

**解析**：在 return_exceptions=False 时，只要有一个任务抛异常，gather 会立刻向外抛出异常，不会等待其他任务完成，所以『等待所有完成后才返回』不成立。

### single_choice · None



- [A] gather 会并发调度未完成者，已完成的 Future 直接取其结果，最终结果仍按传入顺序排列
- [B] 不允许混用，会抛 TypeError
- [C] 已完成的 Future 会被丢弃，结果列表中对应位置为 None
- [D] 混用时会退化为顺序执行

**参考答案**：0

**解析**：gather 对每个 awaitable 统一处理：已完成的直接用其结果，未完成的调度执行，结果仍按传入顺序汇总。

### single_choice · None



- [A] ['a', 'b']
- [B] ['b', 'a']
- [C] ['b']
- [D] 报错，因为完成顺序与传入顺序不一致

**参考答案**：0

**解析**：gather 的返回列表顺序永远与传入参数顺序一致，与各任务完成先后无关。

### single_choice · None



- [A] asyncio.TaskGroup 配合 asyncio.timeout
- [B] threading.Timer
- [C] multiprocessing.Pool
- [D] asyncio.Queue

**参考答案**：0

**解析**：Python 3.11 引入 TaskGroup 与 asyncio.timeout，可与 gather 配合或替代其部分场景做结构化并发和超时控制。

### single_choice · None



- [A] 逐个 await 协程是顺序执行，gather 会并发调度它们
- [B] 逐个 await 协程也是并发执行，两者等价
- [C] gather 会把协程放到线程池里并发执行
- [D] gather 内部使用了多进程来并发执行

**参考答案**：0

**解析**：直接对协程逐个 await 会按顺序等待，而 gather 会在事件循环中把多个 awaitable 并发调度，从而缩短总耗时。gather 不涉及线程/进程池。

### single_choice · None



- [A] 异常会立刻传播给 gather 的 await 方，其他任务不会被取消但结果无法从 gather 取回
- [B] 所有传入的任务会被自动取消，异常被吞掉
- [C] 异常会被收集到返回列表中对应位置，其他结果正常返回
- [D] 异常被转换为 None 放入结果列表

**参考答案**：0

**解析**：默认 return_exceptions=False 时，第一个抛出的异常会立即向调用方传播；其他任务不会被自动取消，但 gather 的结果无法通过返回值获取。

### single_choice · None



- [A] asyncio.gather(*aws, return_exceptions=True)
- [B] asyncio.gather(*aws, ignore_errors=True)
- [C] asyncio.gather(*aws, suppress=True)
- [D] asyncio.gather(*aws).catch()

**参考答案**：0

**解析**：return_exceptions=True 时，异常会作为结果对象放入返回列表，而不是向外传播。其他关键字参数名不存在。

### single_choice · None



- [A] ['int', 'ValueError']
- [B] ['int', 'NoneType']
- [C] ['ValueError', 'int']
- [D] 程序抛出 ValueError

**参考答案**：0

**解析**：return_exceptions=True 时异常对象原样作为结果返回，位置与传入顺序对应。

### single_choice · None



- [A] 传入协程时，gather 会先把它们包装成 Task 再并发调度
- [B] 传入协程时 gather 会顺序 await，因为协程本身不能并发
- [C] gather 会把协程提交到后台线程执行以并发
- [D] gather 只在传入 Task 时才并发，传入协程时会顺序执行

**参考答案**：0

**解析**：gather 对传进来的协程调用 ensure_future 包装为 Task（或直接调度 Future），因此它们会在事件循环中并发推进。

### single_choice · None



- [A] 几乎立即结束并给出 'coroutine was never awaited' 类警告
- [B] 阻塞 1 秒后正常结束
- [C] 抛出 RuntimeError
- [D] 卡死不动

**参考答案**：0

**解析**：gather 返回的是 awaitable，没有被 await，创建的协程/任务不会等待；协程未被 await 会触发警告。

### single_choice · None



- [A] 它返回一个 Future，可被 await，结果在完成后取回
- [B] 它返回一个列表，可以直接下标取值
- [C] 它返回一个协程对象，必须用 asyncio.run 运行
- [D] 它返回 None，结果通过回调获取

**参考答案**：0

**解析**：gather 返回一个聚合 Future，await 它才能拿到结果列表。

### single_choice · None



- [A] asyncio.wait 接受一个协程列表，返回它们的返回值列表
- [B] asyncio.wait 接受一个 Task/Future 集合，返回 (done, pending) 两个集合
- [C] asyncio.wait 会按传入顺序返回结果
- [D] asyncio.wait 只能等待单个协程

**参考答案**：1

**解析**：asyncio.wait 接收的是可等待对象（通常已包装为 Task/Future）的集合，返回 (done, pending) 两个集合，并不保证顺序，也不返回返回值本身。

### single_choice · None



- [A] asyncio.wait(coro1, coro2)
- [B] asyncio.wait([coro1, coro2]) —— 传入未包装的协程列表
- [C] asyncio.wait({task1, task2}) —— 传入 Task 的集合
- [D] asyncio.wait(task1)

**参考答案**：2

**解析**：在 Python 3.8+ 中，asyncio.wait 要求传入可等待对象（通常为 Task/Future）的可迭代集合；直接传协程在 3.8 起会报错，且位置参数必须是单个可迭代对象而非多个参数。

### multi_choice · None



- [A] 传入可等待对象前先用 asyncio.create_task 包装为 Task
- [B] 超时后对不再需要的 pending 任务调用 cancel()
- [C] 依赖返回顺序来匹配任务与结果
- [D] 通过 task.result() 或 task.exception() 获取 done 中的结果或异常
- [E] 把 timeout 当作每个任务的独立超时

**参考答案**：[0, 1, 3]

**解析**：wait 的返回不保序，不能依赖集合顺序匹配结果；timeout 是对整体等待的上限，不是每个任务独立超时。包装为 Task、显式取消、正确取结果都是推荐做法。

### multi_choice · None



- [A] asyncio.Task 实例
- [B] asyncio.Future 实例
- [C] 未包装的协程对象
- [D] 实现了 __await__ 的普通可等待对象

**参考答案**：[0, 1, 3]

**解析**：在 3.8+ 中，wait 要求传入可等待对象的集合，通常为 Task/Future；直接传协程会报 TypeError，因为协程在传入后无法被调度跟踪。可等待对象理论上也可，但推荐包装为 Task。

### multi_choice · None



- [A] 两者都是 set 类型
- [B] done 中的任务已完成（成功、异常或取消）
- [C] pending 中的任务一定被取消了
- [D] 没有超时且全部完成时 pending 为空集
- [E] done 集合中的 Task 已经无法访问其异常信息

**参考答案**：[0, 1, 3]

**解析**：wait 返回两个 set；done 包含已完成任务（正常/异常/取消），pending 包含尚未完成任务，全完成后 pending 为空。done 中的 Task 仍可通过 exception() 访问异常。

### fill_blank · None



**参考答案**：["pending"]

**解析**：asyncio.wait 返回 (done, pending)，pending 是尚未完成的任务集合。

### fill_blank · None



**参考答案**：["FIRST_COMPLETED", "asyncio.FIRST_COMPLETED"]

**解析**：return_when=asyncio.FIRST_COMPLETED 表示任一任务完成即返回。

### fill_blank · None



**参考答案**：["ALL_COMPLETED", "asyncio.ALL_COMPLETED"]

**解析**：默认 return_when 为 ALL_COMPLETED，即全部任务完成后返回。

### code_reading · None



**参考答案**：大约 1 与 2（done 至少包含 sleep(1) 对应的已完成任务，其余因 1.5 秒超时仍在 pending 中）。

**解析**：timeout=1.5 秒内只有 sleep(1) 会完成；sleep(2)、sleep(3) 未完成，因此 done≈1、pending≈2。wait 不会自动取消 pending。

### code_reading · None



**参考答案**：通常输出 ['A']，pending 中还包含 t2。

**解析**：FIRST_COMPLETED 下 sleep(0.1) 先完成，done 只有 t1，其结果为 'A'；t2 尚未完成，留在 pending 中且不会被自动取消。

### code_reading · None



**参考答案**：输出 True 0；因为无 timeout 且默认 ALL_COMPLETED，所有任务完成，done 为包含 3 个任务的 set，pending 为空集。

**解析**：默认等待全部完成，因此 pending 为空；asyncio.wait 返回两个 set 对象。

### scenario · None



**解析**：asyncio.wait 超时后不会自动取消 pending；若不显式 cancel 并 await 它们，任务会继续在后台运行，导致额外请求与退出延迟。正确做法是遍历 pending 调用 task.cancel()，并用 asyncio.gather(*pending, return_exceptions=True) 等方式 await 收尾。

### single_choice · None



- [A] 每个任务单独的最长运行时间
- [B] 所有任务合计允许运行的最长时间，超时后未完成的任务会被放入 pending
- [C] 等待第一个任务完成的最长时间
- [D] 重启任务的间隔时间

**参考答案**：1

**解析**：timeout 是对整体等待时间的上限，超时后返回的 pending 集合包含尚未完成的任务；它们不会被自动取消。

### scenario · None



**解析**：若优先要最早结果，用 FIRST_COMPLETED；若要尽早捕获异常，用 FIRST_EXCEPTION。返回后遍历 done，用 task.exception() 判断是否异常、task.result() 取值，遍历 pending 处理未完成任务（是否取消）。

### single_choice · None



- [A] asyncio.FIRST_COMPLETED
- [B] asyncio.FIRST_EXCEPTION
- [C] asyncio.ALL_COMPLETED
- [D] asyncio.NONE_COMPLETED

**参考答案**：2

**解析**：默认 return_when 是 ALL_COMPLETED，即所有任务完成或超时后才返回。

### single_choice · None



- [A] asyncio.FIRST_COMPLETED
- [B] asyncio.FIRST_EXCEPTION
- [C] asyncio.ALL_COMPLETED
- [D] asyncio.LAST_COMPLETED

**参考答案**：3

**解析**：asyncio.wait 仅支持 FIRST_COMPLETED、FIRST_EXCEPTION、ALL_COMPLETED 三个常量。

### single_choice · None



- [A] 当任何一个任务完成或取消时立即返回
- [B] 只有当所有任务都成功完成时才返回
- [C] 当第一个任务抛出未处理异常时返回
- [D] 永不返回，需立即取消

**参考答案**：0

**解析**：FIRST_COMPLETED 表示任一任务完成（包括被取消）即返回，返回的 pending 中仍有未完成的任务。

### single_choice · None



- [A] 任何任务产生未处理异常时返回，否则等全部完成
- [B] 只有全部任务都抛异常时才返回
- [C] 任何异常都被吞掉，正常返回全部结果
- [D] 第一次调用即返回

**参考答案**：0

**解析**：FIRST_EXCEPTION 会在有任务抛出未处理异常时提前返回；若没有异常，则行为等价于 ALL_COMPLETED。

### single_choice · None



- [A] 直接迭代 done，每个元素就是结果值
- [B] 对 done 中的 Task 调用 .result()
- [C] 调用 asyncio.gather 再取结果
- [D] 结果已经丢失，无法获取

**参考答案**：1

**解析**：done 中的元素是已完成的 Task/Future，需要通过 .result() 获取其返回值，或 .exception() 检查异常。

### single_choice · None



- [A] pending 中的任务会被自动取消
- [B] pending 中的任务继续运行，需要调用方自行决定是否取消
- [C] pending 中的任务会被自动重新执行
- [D] pending 集合总是为空

**参考答案**：1

**解析**：asyncio.wait 不会自动取消未完成的任务，若不再需要应显式调用 task.cancel()，否则它们会继续后台运行。

### multi_choice · None



- [A] gather 按输入顺序返回结果，wait 返回 (done, pending) 集合
- [B] wait 支持 return_when 控制提前返回，gather 默认等全部完成
- [C] gather 若某个任务抛异常会传播，wait 不会主动抛出任务异常
- [D] 两者都必须传入协程对象，不能传 Task

**参考答案**：[0, 1, 2]

**解析**：gather 返回结果列表并保持顺序、异常会向上传播；wait 返回 done/pending 集合、提供 return_when，任务异常不会由 wait 本身抛出。两者都可接收协程或 Task。
