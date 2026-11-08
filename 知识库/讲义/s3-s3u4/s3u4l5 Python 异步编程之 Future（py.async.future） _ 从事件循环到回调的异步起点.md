# s3u4l5 Python 异步编程之 Future（py.async.future） / 从事件循环到回调的异步起点

> 来源 `content/lessons/s3u4l5.json`

## py.async.future

# Python 异步编程之 Future（py.async.future）

> 一句话直觉：**Future 是 asyncio 里“一张取餐小票”——它代表一个“此刻还没结果、将来会有结果”的异步操作，你拿着它可以在需要的时候 `await` 取出真正的结果。**

---

## 1. 为什么要学 Future？

在现实世界里，“等” 无处不在：等网络响应、等磁盘 IO、等数据库返回。如果我们用同步代码（synchronous code）一行一行地等，CPU 就在原地发呆。asyncio 的目标就是让你写**并发（concurrent）** 代码：一个任务在等 IO 时，事件循环（event loop）切去跑别的任务。

那么问题来了：**一个异步操作刚开始跑时还没结果，事件循环怎么“记住”它？任务结束时怎么“通知”等待它的代码？** 答案就是 Future：它是一块“占位牌”，内部维护三种状态：

- **PENDING（未完成）**
- **FINISHED（已完成，含正常结果）**
- **CANCELLED（被取消）**

一句话：**Task 是 Future 的子类，`await` 的东西背后往往就是 Future。学会 Future 就掌握了 asyncio 调度的“底层货币”。**

---

## 2. 第一印象：Future 就是一个“结果票据”

最简单的用法是创建一个 Future，稍后手动设置结果，另一边 `await` 它：

```python
import asyncio

async def main():
    loop = asyncio.get_running_loop()
    fut = loop.create_future()          # 创建一张空票据
    loop.call_later(1, fut.set_result, "蛋糕好了")  # 1 秒后放入结果
    print("先干点别的...")
    result = await fut                  # 挂起，直到有结果
    print("拿到:", result)

asyncio.run(main())
```

**关键点**：`await fut` 不会阻塞线程；它把当前协程挂起，控制权交回事件循环。事件循环在 1 秒后调用 `set_result`，唤醒等待者。

---

## 3. Future 的三种典型操作：set / await / cancel

Future 的核心 API 很少，但语义很关键：

1. `set_result(value)` —— 成功完成。
2. `set_exception(exc)` —— 以异常完成。
3. `cancel()` —— 取消（等价于 `set_exception(CancelledError())`）。
4. `await fut` —— 等待结果；若失败会抛出对应异常。
5. `fut.done()` / `fut.result()` / `fut.exception()` —— 同步检查与取值。

下面演示异常与取消：

```python
import asyncio

async def main():
    loop = asyncio.get_running_loop()

    # 场景 A：以异常完成
    f1 = loop.create_future()
    loop.call_soon(f1.set_exception, ValueError("坏掉了"))
    try:
        await f1
    except ValueError as e:
        print("捕获异常:", e)

    # 场景 B：取消
    f2 = loop.create_future()
    f2.cancel()
    print("f2.cancelled() =", f2.cancelled())   # True
    try:
        await f2
    except asyncio.CancelledError:
        print("被取消了")

asyncio.run(main())
```

**记住一条规则**：一个 Future 只能被“完成”一次，第二次调用 `set_result` / `set_exception` / `cancel` 会抛 `InvalidStateError`。

---

## 4. Task：Future 最常用的“孩子”

平时你很少手动创建裸 Future，更多用的是 `asyncio.create_task(coro)`，它把协程包装成一个 **Task**；而 `Task` 继承自 `Future`。所以“等待一个任务”本质上就是“等待一个 Future”。

```python
import asyncio

async def fetch(name, delay):
    await asyncio.sleep(delay)
    return f"{name} 完成"

async def main():
    t1 = asyncio.create_task(fetch("A", 1))
    t2 = asyncio.create_task(fetch("B", 2))
    # gather 内部就是等待一堆 Future/Task
    results = await asyncio.gather(t1, t2)
    print(results)
    print("t1 is Future?", isinstance(t1, asyncio.Future))  # True
    print("t1 is Task?  ", isinstance(t1, asyncio.Task))    # True

asyncio.run(main())
```

**要点**：`create_task` 会立刻把协程排入事件循环，开始并发执行；返回的 Task 就是一张“票据”。

---

## 5. 工程化视角：什么时候该用 Future？

日常业务里，优先用**协程 + Task**；只有在下面两种场景才需要**手写 Future**：

- 把**回调式（callback-based）** 的老库桥接到 `async/await`（例如某些底层 socket 或 GUI 库）；
- 实现自定义的“未来才会发生的事件”语义（如“等用户点击”）。

示例：把回调函数包装成可 `await` 的 Future：

```python
import asyncio

def legacy_callback_based(on_done):
    # 模拟 1 秒后异步回调
    asyncio.get_running_loop().call_later(1, on_done, 42)

async def call_legacy():
    loop = asyncio.get_running_loop()
    fut = loop.create_future()
    legacy_callback_based(lambda v: fut.set_result(v))  # 回调里塞结果
    return await fut

async def main():
    print(await call_legacy())

asyncio.run(main())
```

**架构层面一句话**：Future 是 asyncio 的“完成协议”——只要你想让一段异步代码能够“未来某刻交付结果”，就把它表示成一个 Future。

---

## 6. 小结对照表

| 概念 | 说明 | 典型创建方式 |
| --- | --- | --- |
| Coroutine | `async def` 定义的函数调用后得到的对象 | `coro = fetch()` |
| Future | 一个“未来会有结果”的占位符 | `loop.create_future()` |
| Task | Future 的子类，协程的调度单元 | `asyncio.create_task(coro)` |
| `await` | 挂起当前协程等 Future 完成 | `await fut` |

---

## 7. 常见误区速览

- ❌ 直接 `await coro` 而不是 `create_task` 时不会并发——一个 `await` 接一个，本质是串行。
- ❌ 对一个已经被完成/取消的 Future 再 `set_result`，会得到 `InvalidStateError`。
- ❌ 忘记 `await` 一个 Task，可能在程序退出时看到 “Task was destroyed but it is pending” 警告。
- ❌ 在 Future 上调用 `result()` 之前没有检查 `done()`，会抛异常。

---

## 8. 动手练习（本地完成）

**任务**：实现 `wait_first(coros)`，传入多个协程，返回**最先完成**的那个协程的结果；其余协程应当被取消，避免资源泄漏。

要求：
1. 用 `asyncio.create_task` 把协程包装成 Task；
2. 用 `asyncio.wait(..., return_when=asyncio.FIRST_COMPLETED)` 等待；
3. 取消其余未完成的 Task；
4. 返回第一个任务的 `result()`；
5. 用两个 `asyncio.sleep` 协程（1 秒和 3 秒）测试，打印结果应为 1 秒那个。

提示骨架：

```python
import asyncio

async def wait_first(coros):
    tasks = [asyncio.create_task(c) for c in coros]
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    # TODO: 取消 pending，返回 done 中某个任务的结果
```

完成后思考：如果不取消 `pending`，事件循环关闭时会发生什么？

```python
import asyncio

async def fetch(name, delay):
    await asyncio.sleep(delay)
    return f"{name} 完成（耗时 {delay}s）"

async def main():
    loop = asyncio.get_running_loop()

    # 1) 裸 Future：手动设置结果
    fut = loop.create_future()
    loop.call_later(0.5, fut.set_result, "Hello Future")
    print(await fut)

    # 2) Task 是 Future 的子类
    t1 = asyncio.create_task(fetch("A", 1))
    t2 = asyncio.create_task(fetch("B", 2))
    print("t1 is Future:", isinstance(t1, asyncio.Future))

    # 3) 用 wait 取“最先完成”的任务
    done, pending = await asyncio.wait(
        [t1, t2], return_when=asyncio.FIRST_COMPLETED
    )
    for t in done:
        print("先完成:", t.result())
    for t in pending:
        t.cancel()
    # 让取消生效
    await asyncio.gather(*pending, return_exceptions=True)

asyncio.run(main())
```

## py.async.callback

# py.async.callback：从事件循环到回调的异步起点

## 一句话直觉（为什么要学它）

因为 **asyncio 的底层就是回调（callback）**：你写的 `async/await` 最终会被事件循环（event loop）翻译成“什么时候调用哪个函数”。理解回调，你才能看懂 asyncio 的调度、超时、事件通知，也才能把老的回调式库接入现代的 async/await 代码。

---

## 1. 什么是回调（Callback）？

回调就是：**把一个函数作为参数传给另一个函数，等某个事情发生时再调用它**。

在 asyncio 里，事件循环（event loop）负责管理所有异步任务。你可以让事件循环在“稍后”或“某个时间点”调用一个普通函数，这就是最基础的回调。

`loop.call_soon(callback, *args)`：把 `callback` 排入事件循环的待执行队列，下一轮循环时调用它。

```python
import asyncio

async def main():
    loop = asyncio.get_running_loop()

    def hello(name):
        print(f"回调被调用: {name}")

    # call_soon 不会阻塞，它只是把 hello 排进队列
    loop.call_soon(hello, "world")
    print("main 结束前")

asyncio.run(main())
```

输出顺序：

```text
main 结束前
回调被调用: world
```

**关键结论**：`call_soon` 是“尽快调用”，不是“立刻同步调用”。回调会在当前协程让出控制权后执行。

---

## 2. 定时回调：call_later / call_at

除了“尽快”，事件循环还能按时间调度回调。

- `loop.call_later(delay, callback, *args)`：延迟 `delay` 秒后调用。
- `loop.call_at(when, callback, *args)`：在事件循环时间 `when` 时调用。

```python
import asyncio
import time

async def main():
    loop = asyncio.get_running_loop()

    def wake_up(msg):
        print(f"[{time.strftime('%X')}] {msg}")

    loop.call_later(1, wake_up, "1 秒后执行")
    loop.call_later(2, wake_up, "2 秒后执行")

    await asyncio.sleep(2.5)  # 等待回调全部执行完

asyncio.run(main())
```

**关键结论**：定时回调不会阻塞事件循环，它们只是被登记为“未来某个时间点要执行的动作”。

---

## 3. 回调与协程（coroutine）的关系

你写的 `async def` 函数叫协程函数，调用它得到协程对象（coroutine object）。协程对象本身不会运行，必须被 `await` 或包装成任务（Task）。

而 Task 的内部实现，本质上就是**用回调驱动协程的恢复**：当 `await` 的 I/O 完成时，事件循环通过回调把结果送回协程，让协程继续往下执行。

下面这个例子展示：普通回调可以安排一个协程任务。

```python
import asyncio

async def work(n):
    await asyncio.sleep(0.1)
    print(f"协程 work({n}) 完成")

async def main():
    loop = asyncio.get_running_loop()

    def schedule():
        # 在回调里创建任务，让协程进入事件循环
        asyncio.create_task(work(42))

    loop.call_soon(schedule)
    await asyncio.sleep(0.2)

asyncio.run(main())
```

**关键结论**：回调是事件循环的“最小执行单元”；协程是建立在回调之上的更高层抽象。

---

## 4. 异步迭代器与回调的边界

typing / collections.abc 里的 `AsyncIterator`、`AsyncGenerator`、`Coroutine` 描述了异步对象的类型。它们不是回调本身，但帮助你在工程里给回调、协程、异步流加上类型标注。

例如，一个异步生成器：

```python
from collections.abc import AsyncIterator

async def count_up(start: int) -> AsyncIterator[int]:
    while True:
        yield start
        start += 1
```

在工程中，你可以把“产生数据”的异步流与“消费数据”的回调组合起来，形成类似事件驱动（event-driven）的结构。

**关键结论**：回调负责“接收事件”，异步迭代器负责“持续产生事件”，二者可以互相配合。

---

## 5. 工程级视角：什么时候直接用回调，什么时候用 async/await

- 写业务逻辑：优先用 `async/await`，可读性更好。
- 接入旧库：如果旧库只提供回调 API，用 `loop.call_soon`、`Future.add_done_callback` 或 `asyncio.to_thread` + 回调桥接。
- 底层框架：直接控制事件循环时，回调是核心机制。
- 定时/延迟任务：`call_later` / `call_at` 非常直接。

```python
import asyncio

async def main():
    loop = asyncio.get_running_loop()
    fut = loop.create_future()

    def on_done(f):
        print("Future 完成，结果:", f.result())

    fut.add_done_callback(on_done)

    # 模拟某个异步操作完成后设置结果
    loop.call_later(0.5, fut.set_result, "OK")
    await fut

asyncio.run(main())
```

**关键结论**：`Future` 是回调与 `await` 之间的桥梁：你可以 `await` 它，也可以给它挂回调。

---

## 动手练习

**任务**：写一个脚本，模拟“下载 3 个文件”的事件驱动流程。

要求：

1. 用 `loop.call_later` 注册 3 个回调，分别在 0.5、1.0、1.5 秒后打印 `下载完成: file1.txt`、`file2.txt`、`file3.txt`。
2. 用 `asyncio.sleep` 等待全部完成。
3. 再加一个 `loop.call_soon`，在事件循环第一轮打印 `开始下载...`。
4. 观察输出顺序，理解“回调不是同步立即执行”。

完成后，尝试把其中某个回调改成 `async def` 协程，并用 `asyncio.create_task` 在回调里启动它。

```python
import asyncio
import time

async def main():
    loop = asyncio.get_running_loop()

    def log(msg):
        print(f"[{time.strftime('%X')}] {msg}")

    # 1. 尽快执行的回调
    loop.call_soon(log, "开始下载...")

    # 2. 定时回调，模拟三个文件先后完成
    loop.call_later(0.5, log, "下载完成: file1.txt")
    loop.call_later(1.0, log, "下载完成: file2.txt")
    loop.call_later(1.5, log, "下载完成: file3.txt")

    # 3. 等待所有回调执行完毕
    await asyncio.sleep(2.0)
    log("全部结束")

asyncio.run(main())
```


---

## 本课题目

### single_choice · None



- [A] 状态变为 Pending，结果被暂存，待被 await 时才生效
- [B] 状态变为 Finished，result() 会返回 42，且所有等待它的协程都会被唤醒
- [C] 状态变为 Cancelled，result() 会抛出 CancelledError
- [D] 状态仍为 Pending，但 result() 立刻返回 42，await 则会抛异常

**参考答案**：1

**解析**：set_result 将 Future 从 Pending 转为 Finished 并保存结果，所有在其上 await 的协程被唤醒并拿到 42；Pending 状态下 result() 会抛 InvalidStateError，Cancelled 需由 cancel() 触发。

### single_choice · None



- [A] 返回 None，表示尚无结果
- [B] 阻塞当前线程直到有结果为止
- [C] 抛出 InvalidStateError，因为结果不可用
- [D] 返回一个占位字符串，稍后可被覆盖

**参考答案**：2

**解析**：result() 在 Pending 状态会抛 InvalidStateError；想要阻塞等待应使用 asyncio 的同步原语或在协程中 await，而不是在 Pending 的 Future 上调用 result()。

### single_choice · None



- [A] ensure_future 只能接受协程，create_task 只能接受 Future
- [B] ensure_future 接受协程或 Future 并返回 Future/Task，create_task 只接受协程并返回 Task
- [C] 两者完全等价，只是历史命名不同
- [D] create_task 会阻塞，ensure_future 不会阻塞

**参考答案**：1

**解析**：ensure_future 更通用：传入协程会包装为 Task，传入 Future 则原样返回（或包装为兼容 Future）；create_task 只接受协程并返回 Task。两者都不阻塞。

### single_choice · None



- [A] 正常等待 1 秒后返回
- [B] 返回一个未来对象，可稍后 await
- [C] 抛出 TypeError，因为 asyncio.sleep 是协程函数，必须 await
- [D] 立即返回 None，因为缺少事件循环

**参考答案**：2

**解析**：asyncio.sleep 是协程函数，调用它只创建协程对象，必须 await 或在事件循环中调度；在同步函数中直接调用且不使用返回值会得到 RuntimeWarning 'coroutine was never awaited'，但如果传入非数字参数会先抛 TypeError。

### single_choice · None



- [A] f = asyncio.Future()
  print(f.result())
- [B] async def w():
      f = asyncio.Future()
      return await f
- [C] f = asyncio.Future()
  f.done()
- [D] f = asyncio.Future()
  f.set_result(f.result())

**参考答案**：1

**解析**：必须在协程中通过 await 等待 Future；Pending 状态直接调用 result() 会抛 InvalidStateError，done() 只返回布尔值，set_result(f.result()) 会在 Pending 时抛异常。

### single_choice · None



- [A] 结果被设置，Future 状态变为 Finished
- [B] 抛出 InvalidStateError，因为 Future 已处于终态
- [C] set_result 被忽略，Future 保持 Cancelled
- [D] Future 状态回滚为 Pending，等待下一次完成

**参考答案**：1

**解析**：Cancelled 是终态，不允许再 set_result/set_exception，会抛 InvalidStateError；同样，Finished 状态也不能再次设置结果。

### single_choice · None



- [A] done() 为 True 时 result() 一定返回正常值
- [B] done() 为 True 且 cancelled() 为 True 时，result() 抛 CancelledError
- [C] done() 为 True 时 cancelled() 一定为 True
- [D] cancelled() 为 True 时 done() 一定为 False

**参考答案**：1

**解析**：done() 表示 Future 已处于终态（Finished 或 Cancelled）；若因取消而完成，result() 会抛 CancelledError 而不是返回 None。cancelled() 为 True 时 done() 必为 True。

### single_choice · None



- [A] 立即完成，因为 ensure_future 会同步执行 setter
- [B] 在 setter 执行到 set_result('ok') 时完成，await 随后返回 'ok'
- [C] main 返回后由事件循环自动完成
- [D] 永远不会完成，因为 Future 不能跨协程传递

**参考答案**：1

**解析**：setter 被调度为 Task，sleep(0.1) 之后调用 set_result 将 fut 置为 Finished，main 中 await fut 得到 'ok'。Future 可以跨协程传递，且 ensure_future 不会同步执行协程体。

### single_choice · None



- [A] Future 立即变为 Cancelled，持有者后续 set_result 会抛 InvalidStateError
- [B] cancel() 抛 RuntimeError，提示无法取消
- [C] Future 保持 Pending，直到持有者完成时才决定是否取消
- [D] cancel() 无任何效果，因为 Future 只能由创建者取消

**参考答案**：0

**解析**：对 Pending 的 Future 调 cancel() 会将其置为 Cancelled；持有者之后调用 set_result 会因终态抛 InvalidStateError。这正是取消与完成之间需要协作的原因。

### single_choice · None



- [A] loop.call_soon(callback, 1)
- [B] loop.call_later(1, callback)
- [C] loop.call_at(1, callback)
- [D] await asyncio.sleep(1); callback()

**参考答案**：1

**解析**：call_later(delay, callback) 按相对延迟调度；call_soon 是立即调度，call_at 需要绝对时间（loop.time() 基准），最后一个选项会阻塞式等待并非调度回调。

### single_choice · None



- [A] Future 被回收时会自动取消并抛出 CancelledError 到创建它的协程
- [B] 若 Future 因异常完成而异常未被取用，回收时事件循环会记录 'exception was never retrieved' 警告
- [C] Future 被回收时结果会被写入日志
- [D] Future 不会触发回收，因为事件循环持有所有 Future 的强引用

**参考答案**：1

**解析**：Future 被回收时若存在未取用的异常，事件循环的异常处理器会记录警告；它不会自动把异常抛到任意协程，也不会记录正常结果。事件循环并不强引用所有 Future。

### single_choice · None



- [A] Future 一定被自动取消，无论它是否被其他任务共享
- [B] Future 一定保持 Pending，因为取消只作用于协程
- [C] Future 是否被取消取决于 await 的实现：asyncio 的等待会尝试取消该 Future
- [D] Future 会被置为 Finished 并返回 None

**参考答案**：2

**解析**：await 一个 Future 时协程被取消，asyncio 的等待逻辑会尝试取消该 Future；但若该 Future 被多个任务共享，取消可能影响其他等待者，因此需要谨慎。它不会自动变 Finished 返回 None。

### single_choice · None



- [A] False，因为取消操作异步执行，需要再 await 一次才生效
- [B] True，cancel() 成功后 Future 即进入 Cancelled 状态
- [C] 抛出 InvalidStateError，因为 Pending 状态不允许取消
- [D] 抛出 CancelledError，取消必须由外部 await 触发

**参考答案**：1

**解析**：对 Pending 的 Future 调用 cancel() 会请求取消，若尚未完成则立即转为 Cancelled，cancelled() 返回 True；CancelledError 是在 await 该 Future 时抛出的，而不是 cancelled() 本身。

### single_choice · None



- [A] 回调只能在 Future 处于 Pending 时添加，一旦完成添加即抛异常
- [B] 若 Future 已完成，新加的回调不会被调用，必须先取消再重加
- [C] 若 Future 已完成，回调会被立即调度，否则在 Future 完成时被调度
- [D] 回调必须返回一个 Future，否则会被忽略

**参考答案**：2

**解析**：add_done_callback 对已完成 Future 会立即安排回调执行，对未完成 Future 则在完成时调度；回调通过事件循环的 call_soon 调度，返回值没有要求。

### single_choice · None



- [A] 返回 None，取消是静默的
- [B] 抛出 CancelledError，协程的取消由此向外传播
- [C] 抛出 InvalidStateError，不能 await 已取消的 Future
- [D] 返回 False，表示该 Future 被取消

**参考答案**：1

**解析**：await 一个 Cancelled 状态的 Future 会抛 CancelledError，使取消沿调用链传播；InvalidStateError 出现在 Pending 时调用 result()/exception()，而不是 await 已取消的 Future。

### single_choice · None



- [A] bad
- [B] 抛出 InvalidStateError，因为异常不能直接设置
- [C] None，异常会被静默吞掉
- [D] 抛出 ValueError 但 e 为 None

**参考答案**：0

**解析**：set_exception 将异常存入 Future，await 时会重新抛出该异常；只要在协程中捕获即可得到 'bad'。异常不会在 set_exception 调用时立即抛出。

### single_choice · None



- [A] 调用 set_exception 的瞬间立即抛出
- [B] 在下一次事件循环 tick 时无条件抛出，与 await 无关
- [C] 当有人 await 该 Future 或调用 result()/exception() 时
- [D] 只有当 Future 被垃圾回收时才抛出

**参考答案**：2

**解析**：set_exception 只负责记录异常；异常在 await 时重新抛出，或在调用 result()/exception() 时被取出。如果不被取用，事件循环可能在对象销毁时记录 'exception was never retrieved' 警告。

### single_choice · None



- [A] 异常永久丢失，没有任何提示
- [B] 异常会在事件循环关闭时自动重新抛出到主线程
- [C] 异常被保留，可能在对象被回收时触发 'exception was never retrieved' 警告
- [D] 立即抛出到创建它的协程中

**参考答案**：2

**解析**：Future 会保留异常直到被取用；若始终无人取用，被垃圾回收时事件循环记录警告。它不会自动重新抛到主线程，也不会立刻抛回创建者。

### single_choice · None



- [A] 会自动 await 它，因为返回值是可等待的
- [B] 会忽略返回值，若为协程则产生 'coroutine was never awaited' 警告
- [C] 会把它包装成 Task 并继续调度
- [D] 会抛出 RuntimeError，禁止回调返回可等待对象

**参考答案**：1

**解析**：loop.call_soon/call_later 只调度普通可调用对象，不会 await 返回值；如果返回协程而不消费，会得到 'coroutine was never awaited' 警告。要调度协程应使用 create_task 或 ensure_future。

### single_choice · None



- [A] 什么也不输出，因为回调注册晚于 set_result
- [B] 输出 'done'，因为已完成 Future 的回调会被立即调度
- [C] 抛出 InvalidStateError，因为已完成 Future 不能注册回调
- [D] 输出 'done' 两次，因为回调被重复触发

**参考答案**：1

**解析**：在已完成 Future 上 add_done_callback 会立即通过事件循环调度回调，所以 sleep(0) 让出控制权后 'done' 被打印；不会重复触发，也不抛异常。

### single_choice · None



- [A] result = do_work(); print(result)
- [B] do_work(callback=lambda r: print(r))
- [C] print(do_work())
- [D] with do_work() as r: print(r)

**参考答案**：1

**解析**：回调式异步把「做完之后做什么」作为参数传入，调用方不必在原地等待结果；其余写法都是同步地立即取得返回值。

### single_choice · None



- [A] 回调必须是匿名函数，不能是具名函数
- [B] 回调就是把一个函数作为参数传给另一个函数，由后者在合适时机调用
- [C] 回调只能用于网络编程
- [D] 回调是一种 Python 关键字

**参考答案**：1

**解析**：回调是「函数作为一等对象被传递并延后调用」这一机制的统称，具名函数、lambda、可调用对象都可以充当回调。

### single_choice · None



- [A] 同步函数不能被调用
- [B] 同步回调中的阻塞调用会卡住事件循环，使其它任务无法推进
- [C] 同步函数的返回值会被丢弃
- [D] 同步函数不能接收参数

**参考答案**：1

**解析**：在事件循环线程里执行阻塞的同步回调，会阻塞整个循环；应改用非阻塞调用或放到线程/进程池。

### single_choice · None



- [A] on_finish 回调 start_task
- [B] start_task 在任务完成后回调 on_finish
- [C] 两者互相回调
- [D] 没有回调关系

**参考答案**：1

**解析**：on_finish 被作为参数交给 start_task，由 start_task 在适当时机调用它，因此是被调用方（回调）。

### fill_blank · None



**参考答案**：["__call__", "__call__()", "call"]

**解析**：实现了 __call__ 的实例是可调用对象，可像函数一样接受调用，适合做带状态的回调。

### fill_blank · None



**参考答案**：["partial", "functools.partial", "partial()"]

**解析**：functools.partial 把部分参数预先绑定，生成一个新的可调用对象，避免闭包延迟绑定问题。

### code_reading · None



**参考答案**：[0, 10, 20]

**解析**：回调依次以 i=0,1,2 被调用，追加 0、10、20，最终打印列表 [0, 10, 20]。

### code_reading · None



**参考答案**：[2, 2, 2]

**解析**：lambda 捕获的是变量 i 而非其当前值，循环结束后 i 为 2，三个回调都返回 2。

### scenario · None



**解析**：可提供默认 on_error（如记录日志/重新抛出，避免静默吞掉异常）；或将成功与失败统一到一个结果通道（Future/Promise 的回调接口），减少遗漏分支的概率。

### scenario · None



**解析**：同步文件读取是阻塞调用，会卡住事件循环线程，影响其它任务；应改用异步/非阻塞 I/O，或把阻塞工作提交到线程池/进程池执行。

### scenario · None



**解析**：可引入 Future/Promise 或 async/await 把嵌套回调改写为顺序写法，使错误集中到一处处理，降低「回调地狱」带来的维护成本。

### single_choice · None



- [A] 在 print('A') 之前
- [B] 在 print('A') 与 print('B') 之间
- [C] 在 print('B') 之后
- [D] 永远不会执行

**参考答案**：1

**解析**：run 先打印 A，再显式调用 cb()，因此 'C' 出现在 A 与 B 之间，最后打印 B。

### single_choice · None



- [A] 无法传递参数
- [B] 容易遗漏错误分支，导致异常被吞掉或错误无处处理
- [C] 回调函数不能是 lambda
- [D] 会让程序变成同步的

**参考答案**：1

**解析**：双回调要求调用方两处都写逻辑，遗漏 on_error 分支是常见事故来源；这正是后来出现 Future/Promise/async-await 的动机之一。

### single_choice · None



- [A] 3
- [B] 6
- [C] lambda v: v * 2
- [D] 报错，lambda 不能作为参数

**参考答案**：1

**解析**：f 被赋值为 lambda，f(3) 即 3*2=6。lambda 可以作为普通函数对象传递。

### single_choice · None



- [A] for i in range(3): callbacks.append(lambda i=i: print(i))
- [B] for i in range(3): callbacks.append(lambda: print(i))
- [C] for i in range(3): callbacks.append(functools.partial(print, i))
- [D] for i in range(3): callbacks.append((lambda v: (lambda: print(v)))(i))

**参考答案**：1

**解析**：闭包捕获的是变量而非当时的值，循环结束后 i 已是最后一个值，所有回调会打印相同结果。用默认参数或 partial 可绑定当前值。

### single_choice · None



- [A] 异常会被自动转成返回值
- [B] 异常会向上传播或由框架记录，可能中断当前调度，导致后续回调不再执行
- [C] 异常会被忽略且无任何提示
- [D] 回调会被自动重试

**参考答案**：1

**解析**：回调没有调用方 try/except 保护时，异常不会被自动处理，可能打断事件循环或只被框架打印日志，属于常见陷阱。

### multi_choice · None



- [A] 调用方不必在等待 I/O 期间阻塞线程
- [B] 可以注册在事件发生后自动执行的逻辑
- [C] 天然避免回调地狱
- [D] 适合处理大量并发 I/O

**参考答案**：[0, 1, 3]

**解析**：回调避免了阻塞并支持并发 I/O，但层叠回调恰恰是「回调地狱」的来源，不是它的优势。

### multi_choice · None



- [A] 函数在 Python 中是第一类对象，可以赋值、传参和返回
- [B] 回调可以是类实例，只要实现了 __call__
- [C] 回调必须声明返回类型注解
- [D] functools.partial 可以把部分参数预先绑定后作为回调使用

**参考答案**：[0, 1, 3]

**解析**：回调只要求「可调用」，类型注解是可选的，不是必须。__call__ 使实例可调用，partial 可预绑定参数。

### multi_choice · None



- [A] 每一步异步操作的结果都要在回调里再发起下一步操作
- [B] 错误处理在每一层回调里各自嵌套
- [C] 把所有回调注册到同一个列表中依次执行
- [D] 用回调串联超过三层的依赖调用

**参考答案**：[0, 1, 3]

**解析**：回调地狱指串行依赖被写成层层嵌套；把回调收集到列表统一执行并不会产生嵌套。
