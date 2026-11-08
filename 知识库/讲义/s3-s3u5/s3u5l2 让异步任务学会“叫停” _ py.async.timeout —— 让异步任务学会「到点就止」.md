# s3u5l2 让异步任务学会“叫停” / py.async.timeout —— 让异步任务学会「到点就止」

> 来源 `content/lessons/s3u5l2.json`

## py.async.cancel

# py.async.cancel：让异步任务学会“叫停”

**一句话直觉**：在并发世界里，任务不是永远该跑完的——用户取消订单、请求超时、页面关闭，都需要“干净地停下来”，`asyncio` 的取消（cancel）机制就是这套“叫停协议”。

---

## 一、为什么要学取消？从“任务”说起

用 `asyncio` 写并发代码时，我们通常把协程（coroutine）包装成任务（Task）丢给事件循环（event loop）去跑：

```python
import asyncio

async def work():
    await asyncio.sleep(10)
    return "done"

async def main():
    task = asyncio.create_task(work())   # 注册到事件循环
    await task

asyncio.run(main())
```

Task 是“可被调度、可被观测、也可被取消”的协程容器。**取消（cancellation）** 是 `asyncio` 的核心能力：外部在任务还没结束前请求它停止，任务本身可以选择响应、清理资源后退出。

学它的意义：超时控制、用户主动中断、父任务失败时联动清理子任务，都靠它。

---

## 二、第一原则：取消是“请求”，不是“强杀”

`task.cancel()` 并不立刻杀死协程，它只是向任务投递一个取消请求。

- 如果任务正卡在 `await` 的可取消点（如 `asyncio.sleep`），它会立刻收到 `CancelledError`。
- 如果任务正在做同步计算，取消请求会排队，等它下次 `await` 时才被抛出。

```python
import asyncio

async def worker():
    print("worker: 开始")
    try:
        await asyncio.sleep(5)
    except asyncio.CancelledError:
        print("worker: 收到取消")
        raise                 # 强烈建议：清理完再重新抛出
    print("worker: 正常结束")

async def main():
    task = asyncio.create_task(worker())
    await asyncio.sleep(0.5)
    task.cancel()             # 发出取消请求
    try:
        await task            # 等待它真正结束
    except asyncio.CancelledError:
        print("main: 确认任务被取消")

asyncio.run(main())
```

**关键结论**：捕获 `CancelledError` 后，除非你确实要“吞掉”取消，否则必须 `raise` 重新抛出，让上层知道取消已生效。

---

## 三、取消的边界：`CancelledError` 是 `BaseException` 的子类

在 Python 3.8+，`asyncio.CancelledError` 继承自 `BaseException`，而不再是 `Exception`。这意味着：

```python
async def bad():
    try:
        await asyncio.sleep(5)
    except Exception:        # 捕不到 CancelledError
        print("这里不会打印")
```

为什么这样设计？因为取消涉及“任务生命周期”，不应被 `except Exception` 这种宽泛兜底吞掉。写清理代码时应显式处理：

```python
async def good():
    try:
        await asyncio.sleep(5)
    except asyncio.CancelledError:
        print("执行清理")
        raise
    finally:
        print("finally 一定会执行")
```

---

## 四、结构化取消：`asyncio.timeout` 与父任务联动

实际工程中我们很少手写 `cancel()`，而是用更高层的原语表达意图。

### 1）超时取消：`asyncio.timeout`（Python 3.11+）

```python
import asyncio

async def slow():
    await asyncio.sleep(10)

async def main():
    try:
        async with asyncio.timeout(1):   # 1 秒后请求取消
            await slow()
    except TimeoutError:
        print("超时，已取消")

asyncio.run(main())
```

低版本可用 `asyncio.wait_for(slow(), timeout=1)`，语义相近。

### 2）父任务取消：`TaskGroup` 自动联动

```python
import asyncio

async def child(name):
    try:
        await asyncio.sleep(10)
    except asyncio.CancelledError:
        print(f"{name} 被清理")
        raise

async def main():
    async with asyncio.TaskGroup() as tg:
        tg.create_task(child("A"))
        tg.create_task(child("B"))
        # 任一子任务异常或外部取消，其它兄弟任务会被自动取消

asyncio.run(main())
```

**关键结论**：优先用 `asyncio.timeout` / `TaskGroup` 表达“取消意图”，把手工 `cancel()` 留给真正需要细粒度控制的场景。

---

## 五、取消的“坑位清单”

1. **不要吞掉 `CancelledError`**：除非你明确要把取消转成别的语义，否则捕获后必须 `raise`。
2. **`shield` 不是万能盾**：`asyncio.shield(coro)` 可以保护内层不被外层取消波及，但外层任务一旦被取消，`await shield` 本身仍会抛 `CancelledError`。
3. **同步阻塞代码无法被取消**：`time.sleep`、CPU 密集计算不会在取消请求时中断；需要把它们放入线程/进程执行器（`run_in_executor`）或者配合 `await asyncio.sleep(0)` 让出控制权。
4. **资源清理要放在 `finally` 或 `except CancelledError`**：否则连接、文件、锁可能泄漏。

---

## 动手练习（建议 15 分钟）

实现一个 `fetch_with_retry` 异步函数，要求：

1. 接受一个协程工厂 `make_coro()`（返回协程），最多重试 3 次；
2. 使用 `asyncio.timeout(0.5)` 给每次尝试加上 0.5 秒超时；
3. 超时视为一次失败并重试，但**整体函数**如果被外部取消，必须立刻停止重试并向上抛出 `CancelledError`；
4. 在本地用一个会 `sleep(2)` 的假协程和一个会立即返回的假协程分别测试，观察是否重试、是否响应外部取消。

提示：区分“内部 `TimeoutError`”与“外部 `CancelledError`”是本题的关键。

```python
import asyncio

async def worker(name: str) -> None:
    try:
        print(f"{name}: 开始")
        await asyncio.sleep(5)
    except asyncio.CancelledError:
        print(f"{name}: 收到取消，做清理")
        raise  # 重要：清理后重新抛出，让调用者感知取消已生效
    finally:
        print(f"{name}: finally 清理")

async def main() -> None:
    task = asyncio.create_task(worker("task-1"))
    await asyncio.sleep(0.5)     # 让它先跑一会儿
    task.cancel()                # 投递取消请求
    try:
        await task               # 等待取消真正落地
    except asyncio.CancelledError:
        print("main: 确认任务已取消")

    # 使用 asyncio.timeout 做超时取消
    try:
        async with asyncio.timeout(0.3):
            await asyncio.sleep(2)
    except TimeoutError:
        print("main: 超时取消完成")

if __name__ == "__main__":
    asyncio.run(main())
```

## py.async.timeout

# py.async.timeout —— 让异步任务学会「到点就止」

> **一句话直觉**：在异步代码里，一个 `await` 可能永远不返回（网络卡住、服务挂掉）；`asyncio.timeout` 就是给你的 `await` 装一个「闹钟」，到点自动抛异常，让程序不会被一个慢调用拖死。

---

## 1. 为什么需要超时：异步不等于万能

**asyncio**（异步 I/O 库）让我们可以用 `async/await` 语法写并发代码。它的核心优势是：单个线程里，当一个协程（**coroutine**）在等待 I/O 时，事件循环（**event loop**）可以切去运行别的协程。

但异步也有一个隐形的坑：**它没有自动的「保护机制」**。同步代码里线程卡住你还能 `kill`，但在 `await` 点上，如果对端永远不响应，这个协程就会永久挂在那里，事件循环里其他任务可能还在跑，你自己却「永远等不到结果」。

```python
# 没有超时保护：如果 slow_server 不响应，这一行会永久挂住
result = await slow_server_call()
```

**结论**：任何涉及网络、子进程、外部服务的 `await`，都应该考虑加超时。

---

## 2. 三种超时方案，先看历史

Python 的 asyncio 超时 API 经历了三代演化：

| 方案 | 出现版本 | 状态 |
|---|---|---|
| `asyncio.wait_for(coro, timeout)` | 3.4 | 仍可用，但取消语义不够干净 |
| `asyncio.wait(...)` 带 timeout | 3.4 | 只在等待多任务时用 |
| **`asyncio.timeout(delay)`** | **3.11** | **官方推荐，本文主角** |

`asyncio.timeout` 是一个 **异步上下文管理器**（async context manager），配合 `async with` 使用。它把「这段代码必须在 N 秒内跑完」表达得非常清楚。

---

## 3. `asyncio.timeout` 基本用法

```python
import asyncio

async def slow_task():
    await asyncio.sleep(10)   # 假装一个慢操作
    return "done"

async def main():
    try:
        # 给下面这一整块代码 1 秒的预算
        async with asyncio.timeout(1):
            result = await slow_task()
            print(result)
    except TimeoutError:
        print("超时了！")

asyncio.run(main())
```

关键点：

- `asyncio.timeout(1)` 参数单位是**秒**，也可以是 `None`（表示不超时）。
- 超时发生时，`async with` 块**内部正在 await 的协程会被取消**（raise `CancelledError`），然后 `asyncio.timeout` 把它转换成 `TimeoutError` 抛到 `async with` 之外。
- 捕获的异常是内置的 `TimeoutError`（Python 3.11+ 起，`asyncio.TimeoutError` 是它的别名）。

---

## 4. 超时预算可以动态调整与查询

`asyncio.timeout` 返回一个 `Timeout` 对象，它有两个实用能力：

1. **`.expired()`**：判断是否已经超时（在 `except` 里用）。
2. **`.reschedule(when)`**：重新设定截止时间，适合「分段预算」场景。

```python
import asyncio

async def fetch():
    await asyncio.sleep(0.1)
    return "ok"

async def main():
    try:
        async with asyncio.timeout(0.5) as cm:
            await fetch()
            # 发现前半段很快，给后半段更多时间
            cm.reschedule(asyncio.get_running_loop().time() + 2)
            await fetch()
    except TimeoutError:
        assert cm.expired()
        print("确实超时了")

asyncio.run(main())
```

这比 `wait_for` 灵活得多：**预算是可以谈判的**。

---

## 5. 与取消、清理、嵌套的配合

超时本质上是「**自动取消**」。理解这点，才能写出健壮的代码：

- `async with asyncio.timeout(t):` 超时后，内部协程收到 `CancelledError`。
- 你的 `try/finally` 或 `async with` 资源清理逻辑**仍会执行**，这是好事。
- 但如果你在 `finally` 里再 `await`，那也要加超时，否则取消可能被「吃掉」。
- **可以嵌套**：外层超时是整体预算，内层超时是子任务预算。

```python
import asyncio

async def step(name, t):
    try:
        async with asyncio.timeout(t):
            await asyncio.sleep(t + 1)  # 必定超时
    except TimeoutError:
        print(f"{name} 超时")

async def main():
    # 外层给整个流程 5 秒，内层两步各 0.3 秒
    try:
        async with asyncio.timeout(5):
            await step("第一步", 0.3)
            await step("第二步", 0.3)
    except TimeoutError:
        print("整体超时")

asyncio.run(main())
```

嵌套的语义是：**谁先到点谁触发**。内层先超时，就会把 `TimeoutError` 往上传；外层超时则直接终止整块。

---

## 动手练习

**任务**：写一个 `fetch_with_retry(urls, per_try_timeout=0.5, total_timeout=2.0)` 异步函数。

要求：

1. 输入一个 URL 列表（可以用 `asyncio.sleep(random.uniform(0, 1))` 模拟网络请求）。
2. 每次请求都套上 `asyncio.timeout(per_try_timeout)`；超时就重试一次，最多两次。
3. 整个函数再套一层 `asyncio.timeout(total_timeout)`，保证总时长不超过 2 秒。
4. 打印每个 URL 的最终结果：成功 / 单次超时 / 整体超时。

本地运行提示：

```python
import asyncio, random

async def fake_fetch(url):
    await asyncio.sleep(random.uniform(0, 1.0))
    return f"{url} 的内容"

# 你的实现...
```

写完后再问自己两个问题：

- 如果 `per_try_timeout` 之和超过 `total_timeout`，会发生什么？
- 如何在 `finally` 里安全地记录日志（提示：不要在 `finally` 里做长时间 await）？

```python
import asyncio
import random

async def fake_fetch(url: str, delay: float) -> str:
    """模拟一次网络请求：耗时 delay 秒后返回内容。"""
    await asyncio.sleep(delay)
    return f"{url} -> OK (delay={delay:.2f}s)"

async def fetch_with_retry(url: str, per_try_timeout: float = 0.5) -> str:
    """单 URL 抓取：最多两次尝试，每次使用 asyncio.timeout 限时。"""
    for attempt in range(1, 3):
        try:
            async with asyncio.timeout(per_try_timeout) as cm:
                # 每次延迟随机，模拟真实网络波动
                delay = random.uniform(0, 1.0)
                return await fake_fetch(url, delay)
        except TimeoutError:
            assert cm.expired()
            print(f"[retry] {url} 第 {attempt} 次超时")
    return f"{url} -> FAILED (all attempts timeout)"

async def main():
    urls = ["https://a.example", "https://b.example", "https://c.example"]
    # 整个批次的总预算 2 秒
    try:
        async with asyncio.timeout(2.0):
            tasks = [asyncio.create_task(fetch_with_retry(u)) for u in urls]
            results = await asyncio.gather(*tasks)
            for r in results:
                print(r)
    except TimeoutError:
        print("整体超时：未能在 2 秒内完成所有 URL")

if __name__ == "__main__":
    asyncio.run(main())
```


---

## 本课题目

### single_choice · None



- [A] CancelledError
- [B] TimeoutError
- [C] RuntimeError
- [D] StopIteration

**参考答案**：0

**解析**：任务取消通过在挂起点向协程抛出 CancelledError 实现。TimeoutError 用于超时（Python 3.11 起为内置），StopIteration 表示迭代结束，RuntimeError 是通用运行时错误。

### single_choice · None



- [A] 先打印 cancelled，再打印 main caught
- [B] 只打印 cancelled
- [C] 只打印 main caught
- [D] 什么都不打印，程序静默结束

**参考答案**：0

**解析**：worker 捕获后重新 raise，取消继续传播；await t 会抛出 CancelledError，被 main 捕获后打印 main caught。若 worker 不重新抛出，任务会变成正常完成而不是取消。

### single_choice · None



- [A] 返回 False，任务保持正常完成状态，结果不受影响
- [B] 返回 True，任务被改为已取消状态
- [C] 返回 True，但结果被丢弃
- [D] 抛出 RuntimeError，因为任务不可取消

**参考答案**：0

**解析**：cancel() 若发现任务已完成则返回 False，不改变其结果与状态。它不会抛异常，也不会把已完成任务标记为取消。

### single_choice · None



- [A] 任务因未处理异常而失败，但从未被 await 也未被检查
- [B] 任务被取消且从未被 await
- [C] 任务正常完成且从未被 await
- [D] 任务使用 asyncio.gather 并且设置了 return_exceptions=True

**参考答案**：0

**解析**：未取回的异常在任务被垃圾回收时触发该警告。取消属于预期控制流，正常完成无结果问题；gather 的 return_exceptions=True 会取回异常。

### single_choice · None



- [A] 取消 gather 返回的外层 future 会向所有未完成的子任务传播取消
- [B] 取消外层 future 只停止等待，子任务继续在后台运行直到完成
- [C] 一旦有子任务被取消，gather 会立即抛出 CancelledError，与其他子任务无关
- [D] gather 的 return_exceptions=True 会把 CancelledError 转成普通结果返回

**参考答案**：0

**解析**：取消 gather 的外层 future 会逐个取消尚在运行的子任务。return_exceptions=True 不把取消转成返回值；取消是传播性的，而非仅停止等待。

### single_choice · None



- [A] 取消被等待的任务并抛出 TimeoutError（Python 3.11 起为内置 TimeoutError）
- [B] 直接丢弃 coro 并返回 None
- [C] 阻塞事件循环直到 coro 完成，然后抛出 TimeoutError
- [D] 只抛出 TimeoutError，coro 继续在后台执行且不会被取消

**参考答案**：0

**解析**：wait_for 通过取消内部任务实现超时，并对外抛出 TimeoutError。它不会阻塞循环，也不会放任任务继续运行（除非任务吞掉取消）。

### single_choice · None



- [A] 使内部 awaitable 不受外层取消影响，但外层仍会收到取消（内部继续运行）
- [B] 完全阻止取消向外传播，使外层协程无法被取消
- [C] 将取消转换为普通异常返回给调用者
- [D] 让内部任务在独立线程中运行以避免取消

**参考答案**：0

**解析**：shield 保护内部对象不被取消波及，使它可以继续运行；但外层等待者仍会被取消，需要自行处理内部任务的结果或异常，否则可能产生未取回异常。

### single_choice · None



- [A] 用户离开页面后，停止仍在轮询远程接口的后台任务
- [B] 需要等待多个任务全部完成时
- [C] 需要将同步函数放到事件循环中运行时
- [D] 任务抛出了未捕获异常需要重试时

**参考答案**：0

**解析**：取消适用于不再需要的结果场景，如用户离去后的后台轮询。等待全部完成用 gather，运行同步函数用 to_thread，异常重试与取消无关。

### single_choice · None



- [A] task.uncancel()，并检查 cancelling() 计数
- [B] task.cancel(None)
- [C] asyncio.clear_cancelled()
- [D] 直接 pass 即可，取消状态会自动清除

**参考答案**：0

**解析**：3.11 引入 uncancel()/cancelling() 用于在抑制取消后正确维护取消计数。取消状态不会因 pass 自动消失；canceling(None) 不是合法 API，asyncio.clear_cancelled 不存在。

### single_choice · None



- [A] 取消被吞掉，任务可能继续运行，外层误以为任务仍在正常工作
- [B] 取消仍然生效，因为解释器会强制重新抛出
- [C] 任务会立即崩溃并打印 traceback
- [D] 事件循环会检测到并自动再次取消该任务

**参考答案**：0

**解析**：把 CancelledError 转成普通异常会破坏协作式取消协议，使取消丢失、任务继续运行。解释器不会强制重抛，也没有自动重取消机制。

### single_choice · None



- [A] 可以调用，但取消的实际效果依赖事件循环稍后调度，非线程安全需谨慎
- [B] 会直接抛出 RuntimeError，因为必须在协程内调用
- [C] 会立即中断目标任务并执行清理
- [D] 只能在 asyncio.run 内部调用，否则无效果

**参考答案**：0

**解析**：cancel() 不是协程函数，可在同步上下文调用，会安排取消；但跨线程调用 asyncio 对象通常需要 call_soon_threadsafe，否则不是线程安全的。它不会立即中断任务。

### single_choice · None



- [A] A 和 B 都能保证异常/取消时释放锁
- [B] 只有 A 能，B 在取消时不会执行 finally
- [C] 只有 C 能，因为显式 release 最可靠
- [D] 只有 D 能，因为其它写法会死锁

**参考答案**：0

**解析**：async with 等价于带 finally 的 acquire/release，取消或异常时都会释放；B 显式使用 try/finally 同样安全。C 缺少 finally，取消时会泄漏锁；D 根本没执行工作。

### single_choice · None



- [A] 它返回一个布尔值，表示取消请求是否成功发出
- [B] 它立即终止目标任务，且保证任务不会再执行任何代码
- [C] 它会同步等待目标任务结束
- [D] 它只能取消尚未开始执行的任务

**参考答案**：0

**解析**：cancel() 只是发出取消请求并返回是否成功安排（例如任务已完成时返回 False）。真正的取消发生在下次挂起点，任务仍可能执行清理代码。它不会同步等待，也不限于未开始的任务。

### single_choice · None



- [A] 取消请求要等该协程再次 await 时才会生效，当前循环会一直跑完
- [B] 协程会立刻在循环中被打断并抛出 CancelledError
- [C] 事件循环会强制杀死该任务线程
- [D] cancel() 会直接返回 False，因为任务不可取消

**参考答案**：0

**解析**：取消依赖挂起点。没有 await 的同步代码无法被中断，取消请求会挂起并在下次真正 await 时抛出 CancelledError。事件循环是单线程协作式的，不会强杀任务。

### single_choice · None



- [A] 任务会被视为正常完成，取消被吞掉，调用方 await 不会收到 CancelledError
- [B] 任务仍会被标记为已取消，调用方仍会收到 CancelledError
- [C] 解释器会报错并终止程序
- [D] 取消请求会被自动重新发送一次

**参考答案**：0

**解析**：取消通过异常传播，吞掉异常就等于吞掉取消信号，任务以正常结果结束。因此清理代码后应重新 raise，否则会破坏取消语义（如 asyncio.timeout 等依赖取消的机制）。

### single_choice · None



- [A] 它是 BaseException 的子类，不是 Exception 的子类
- [B] 它是 Exception 的子类，因此会被 except Exception 捕获
- [C] 它直接继承自 object
- [D] 它同时是 Exception 和 BaseException 的直接子类

**参考答案**：0

**解析**：Python 3.8 起 CancelledError 继承 BaseException 而非 Exception，所以 except Exception 不会误吞取消信号。这也是为什么清理逻辑里要显式处理它并重新抛出。

### single_choice · None



- [A] 不会，CancelledError 继承自 BaseException，'caught by Exception' 不打印，最终打印 main caught
- [B] 会，先打印 caught by Exception 再打印 main caught
- [C] 会，只打印 caught by Exception
- [D] 不会，且 main caught 也不会打印，因为任务悄然消失

**参考答案**：0

**解析**：CancelledError 不是 Exception 的子类，故 except Exception 不捕获它；异常继续传播到 await t 处被 main 捕获。若写成 except BaseException 才会捕获。

### single_choice · None



- [A] try/finally 中写清理代码，让 CancelledError 自然传播
- [B] except BaseException 中写清理代码并 pass 忽略
- [C] except CancelledError 中写清理代码但不重新抛出
- [D] 在协程末尾写清理代码，因为取消不会跳过它

**参考答案**：0

**解析**：try/finally 保证无论正常结束、异常还是取消都会执行清理，且不改变异常传播。吞掉异常（pass/不 re-raise）会破坏取消语义。取消会跳过后续同步代码，故末尾写清理不可靠。

### single_choice · None



- [A] 若任务此时被再次取消，挂起点会立刻再次抛出 CancelledError，可能中断清理逻辑
- [B] await 在 finally 中是非法的，会抛 SyntaxError
- [C] 事件循环会自动屏蔽取消，保证清理完整执行
- [D] 只要清理不超过一秒就不会有任何影响

**参考答案**：0

**解析**：清理代码中的挂起点仍是取消注入点，尤其 uncancel/重复取消场景下会被打断。需要保护式清理时可考虑 asyncio.shield 或临时抑制取消，但需谨慎处理取消状态。

### single_choice · None



- [A] task.cancelled() 为 True，task.done() 为 True，再次 await 它仍会抛出 CancelledError
- [B] task.cancelled() 为 False，因为异常已经抛出过了
- [C] task.done() 为 False，任务仍可被恢复执行
- [D] 再次 await 会返回 None，因为取消已被消费

**参考答案**：0

**解析**：取消后任务进入已取消的完成态；cancelled() 和 done() 均为 True，且异常会保留，重复 await 会再次抛出 CancelledError。任务不可恢复。

### single_choice · None



- [A] 超时只适用于同步阻塞函数，异步函数无法设置超时
- [B] 异步超时通常通过在等待协程时限定最大等待时间来触发，超时后需处理被取消的等待
- [C] 设置超时后，一定会在规定时间内强制终止正在运行的协程，无论它是否可取消
- [D] 超时机制只对 I/O 操作有效，对纯计算任务没有意义

**参考答案**：1

**解析**：异步超时本质是对 await 的等待时间做限制，超时后等待会被取消并抛出超时异常，但需要协程自身可被取消才能真正停下来。A、C、D 都是常见误解。

### single_choice · None



- [A] 程序直接崩溃退出，无法捕获
- [B] 等待被取消，并抛出可捕获的超时异常
- [C] 该协程会被自动重启并重新等待
- [D] 超时被静默忽略，继续无限等待

**参考答案**：1

**解析**：异步超时通常表现为等待被取消并抛出可捕获的异常，调用方可据此进行重试或降级，而不是崩溃或忽略。

### fill_blank · None



**参考答案**：["超时", "超时时间", "timeout"]

**解析**：限制等待最长时长的机制就是超时，它通常以取消等待并抛异常的形式体现。

### fill_blank · None



**参考答案**：["递减", "减少", "缩短", "变小"]

**解析**：这正是超时预算的核心：总上限固定，随消耗递减，避免各子步骤各自使用全量超时。

### fill_blank · None



**参考答案**：["降级", "fallback", "兜底"]

**解析**：捕获超时异常后执行降级是常见做法，可保证在部分依赖变慢时整体服务仍可用。

### code_reading · None



**参考答案**：超时会尝试取消这次等待，但由于 slow_call 内部没有 await 点、无法响应取消，实际执行不会在 2 秒时立刻停止；协程要等到该阻塞操作结束后才真正返回，此时才会体现出超时/取消异常。也就是说超时依赖协作式取消，不可中断的阻塞操作会削弱超时效果。

**解析**：关键点是超时通过取消生效，而取消是协作式的，需要 await 点配合；不可中断的计算会拖延取消的实际生效时间。

### code_reading · None



**参考答案**：最可能输出 'timeout caught'。因为等待超过 1 秒后触发超时，抛出可捕获的超时异常，被 except 分支捕获，而 print('done') 不会执行。

**解析**：考察超时异常的捕获路径：超时抛出 TimeoutError 一类的异常，被捕获后执行 except 分支，成功分支被跳过。

### code_reading · None



**参考答案**：体现的是超时预算思想：总上限为 3 秒，子步骤共享该预算，通过获取剩余时间传给后续步骤。若 step1 耗时 2.5s，则 step2 只剩约 0.5s 的预算，可用超时相应缩短。

**解析**：总时间上限固定，子步骤消耗后剩余时间递减并传递给后续步骤，防止每个子步骤都使用完整超时导致总耗时超限。

### scenario · None



**解析**：回答应围绕总超时预算、并行调用的超时与取消、超时后的降级、有限重试等展开，而不是简单地给每个调用设一个固定的较大值。

### scenario · None



**解析**：关键点是取消是协作式的：协程内部缺少 await 点，无法在超时时被及时打断。改进方向包括在长循环中插入 await 点、把任务分片、使用可中断的等待方式等。

### scenario · None



**解析**：排查方向包括确认清理逻辑是否放在 finally 或上下文管理器中、清理逻辑本身是否阻塞或不可取消、是否吞掉了取消/超时异常等。修复应保证清理逻辑能响应取消并确实执行。

### single_choice · None



- [A] 为一次请求分配的总时间上限，子步骤共享该预算，剩余时间随消耗递减
- [B] 每个子步骤都独立使用完整的总超时时间
- [C] 超时时间必须是固定常数，不能动态计算
- [D] 超时预算只与内存占用有关

**参考答案**：0

**解析**：超时预算强调总时间上限在多个子步骤之间共享，前序步骤消耗后，后续步骤的可用时间应相应减少，而不是各自使用全量超时。

### single_choice · None



- [A] 等价于永不超时
- [B] 通常表示立即超时或参数非法，应避免这种用法
- [C] 会自动调整为默认最大值
- [D] 与设置为正数效果完全相同

**参考答案**：1

**解析**：超时时间应为正数；0 或负数通常被视为非法参数或立即超时，依赖这种边界行为容易出问题，最佳做法是显式校验参数。

### single_choice · None



- [A] 显著缩短总耗时
- [B] 重试风暴，放大下游压力并加剧资源消耗
- [C] 自动修复网络故障
- [D] 超时时间会自适应变长

**参考答案**：1

**解析**：无限制重试在下游已超时时会形成重试风暴，进一步压垮服务。应配合重试上限、退避和超时预算。

### single_choice · None



- [A] 清理逻辑也必须能响应取消，避免长时间阻塞导致取消无法及时完成
- [B] 清理逻辑完全不会被执行
- [C] 清理逻辑中不能再有 await
- [D] 取消后 finally 会被跳过

**参考答案**：0

**解析**：取消会注入到 await 点，finally 通常会执行，但清理逻辑本身若长时间阻塞或不可取消，则可能拖延甚至阻碍取消的完成。

### multi_choice · None



- [A] 超时通常是取消等待的协程并抛出可捕获的异常
- [B] 协程内若存在不可取消的阻塞操作，超时可能无法真正停止它
- [C] 超时时间应结合下游服务的实际响应时间来设置，而不是随意取值
- [D] 设置超时后，超时永远不会抛出异常，只会返回 None
- [E] 在有限时间的等待场景中，超时与取消机制常常配合使用

**参考答案**：[0, 1, 2, 4]

**解析**：A、B、C、E 描述正确。D 错误，因为超时通常通过抛出异常来表达，可通过捕获异常来处理。

### multi_choice · None



- [A] 为整条调用链设定总超时预算，并在子步骤间递减
- [B] 对超时失败设计退避与重试上限
- [C] 把超时时间设置为一个极大值以「避免误报」
- [D] 在超时异常中记录上下文信息以方便排查
- [E] 忽略超时异常，当作成功继续执行下游逻辑

**参考答案**：[0, 1, 3]

**解析**：A、B、D 是合理工程实践。C 变相等于没有超时，E 忽略异常会导致状态不一致。

### multi_choice · None



- [A] 超时可以看作一种带时间条件的自动取消
- [B] 被取消的协程有机会通过异常处理或 finally 做清理
- [C] 取消一定会在任意时刻立即生效，即使协程正在执行不可中断的计算
- [D] 超时发生后，调用方可以选择捕获异常并执行降级逻辑
- [E] 取消与超时是完全无关的两套机制

**参考答案**：[0, 1, 3]

**解析**：C 错误，取消依赖协作，不可中断的计算无法立即被停止；E 错误，超时通常借助取消机制实现。

### multi_choice · None



- [A] 协程内部执行长时间的纯计算且没有 await 点
- [B] 下游调用本身不响应取消
- [C] 使用过大的超时值，导致等待时间远超可接受范围
- [D] 在等待上设置了合理的超时并正确处理了异常

**参考答案**：[0, 1, 2]

**解析**：A、B、C 都会削弱超时效果；D 是正确用法，不在失效之列。
