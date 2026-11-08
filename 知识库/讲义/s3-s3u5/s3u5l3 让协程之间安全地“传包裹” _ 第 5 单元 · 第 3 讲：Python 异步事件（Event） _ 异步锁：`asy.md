# s3u5l3 让协程之间安全地“传包裹” / 第 5 单元 · 第 3 讲：Python 异步事件（Event） / 异步锁：`asyncio.Lock`

> 来源 `content/lessons/s3u5l3.json`

## py.async.queue

# py.async.queue：让协程之间安全地“传包裹”

> **一句话直觉**：当你让很多协程（coroutine）同时干活时，它们常常需要互相递送数据——`asyncio.Queue` 就是那个“传送带”，生产者把包裹放上去，消费者从上面取走，全程不阻塞事件循环（event loop）。

---

## 1. 为什么需要 asyncio.Queue？

想象一个外卖平台：

- **生产者**：商家不断把做好的订单放出来。
- **消费者**：骑手不断接单去配送。

如果直接用一个 Python 的 `list` 当缓存，会出问题：

- 骑手取单时列表可能为空，只能“忙等”（busy-wait），浪费 CPU。
- 多个协程同时读写同一个列表，容易乱序或丢失数据。

`asyncio.Queue` 是专门为异步场景设计的**线程/协程安全**队列（queue）。它把“等数据”这件事变成 `await`，让出事件循环，别的协程可以继续跑。

关键方法一览：

- `await queue.put(item)`：放数据；队列满时会等待。
- `await queue.get()`：取数据；队列空时会等待。
- `queue.task_done()`：告诉队列“这个任务处理完了”。
- `await queue.join()`：等到队列里所有任务都被处理完。

---

## 2. 最小可用例子：一个生产者 + 一个消费者

下面代码展示最基本的“放一个、取一个”。

```python
import asyncio

async def main():
    q = asyncio.Queue()          # 无界队列，可以无限放
    await q.put("hello")         # 生产者放入数据
    item = await q.get()         # 消费者取出数据
    print(item)                  # 输出: hello

asyncio.run(main())
```

注意 `await q.get()` 在队列为空时会挂起当前协程，而不是卡死整个程序。这就是它和普通 `list.pop()` 的本质区别。

---

## 3. 经典模式：生产者-消费者并发运行

真实场景中，生产者和消费者是**同时**工作的。用 `asyncio.create_task` 把多个协程并发跑起来。

```python
import asyncio
import random

async def producer(q: asyncio.Queue, n: int):
    for i in range(n):
        await asyncio.sleep(random.uniform(0.1, 0.3))  # 模拟耗时生产
        await q.put(i)
        print(f"[生产者] 放入 {i}")

async def consumer(q: asyncio.Queue, name: str):
    while True:
        item = await q.get()                            # 队列空时挂起等待
        await asyncio.sleep(random.uniform(0.1, 0.3))   # 模拟耗时消费
        print(f"[{name}] 取出 {item}")
        q.task_done()                                   # 标记这个任务处理完

async def main():
    q = asyncio.Queue()
    # 启动 3 个消费者协程
    consumers = [asyncio.create_task(consumer(q, f"消费者-{i}")) for i in range(3)]
    # 启动 1 个生产者
    await producer(q, 10)
    await q.join()                                      # 等所有任务被 task_done
    for c in consumers:
        c.cancel()                                      # 任务结束，取消消费者

asyncio.run(main())
```

这段代码里有三个容易忽略的点：

1. **消费者是死循环**：靠外部 `cancel()` 退出。
2. **`q.join()` 是关键**：它会一直等到每个 `put` 进来的项都调用了 `task_done()`。
3. **`task_done()` 不是自动的**：忘记调用，`join()` 会永远卡住。

---

## 4. 有界队列：天然的反压（backpressure）机制

`asyncio.Queue(maxsize=N)` 可以限制队列长度。队列满时 `put` 会等待，这能防止生产者“洪水式”生产把内存撑爆。

```python
import asyncio

async def producer(q: asyncio.Queue):
    for i in range(5):
        await q.put(i)                                  # 队列满时这里会挂起
        print(f"[生产者] 放入 {i}，当前队列大小 {q.qsize()}")

async def consumer(q: asyncio.Queue):
    for _ in range(5):
        await asyncio.sleep(0.5)                        # 消费慢
        item = await q.get()
        print(f"[消费者] 取出 {item}，剩余 {q.qsize()}")

async def main():
    q = asyncio.Queue(maxsize=2)                        # 最多缓冲 2 个
    await asyncio.gather(producer(q), consumer(q))

asyncio.run(main())
```

你会看到生产者生产到第 3 个时会“停一停”，等消费者腾出空间。这就是**反压**：下游处理不过来时，上游自然降速。

---

## 5. 进阶要点：优先级、LIFO 与哨兵（sentinel）

`asyncio` 还提供了两种变体：

| 类 | 行为 |
|---|---|
| `asyncio.Queue` | 先进先出 FIFO |
| `asyncio.LifoQueue` | 后进先出 LIFO（栈） |
| `asyncio.PriorityQueue` | 按优先级排序（元素需可比较） |

当消费者数量固定时，比起 `cancel()`，更优雅的做法是发“哨兵”值通知消费者退出：

```python
import asyncio

STOP = None  # 哨兵：表示“没有更多工作了”

async def worker(q: asyncio.Queue, name: str):
    while True:
        item = await q.get()
        if item is STOP:
            q.task_done()
            break                                        # 收到哨兵，退出
        print(f"[{name}] 处理 {item}")
        q.task_done()

async def main():
    q = asyncio.Queue()
    workers = [asyncio.create_task(worker(q, f"W{i}")) for i in range(3)]
    for i in range(9):
        await q.put(i)
    for _ in workers:
        await q.put(STOP)                                # 每个 worker 一个哨兵
    await q.join()
    await asyncio.gather(*workers)

asyncio.run(main())
```

哨兵法比 `cancel()` 更可控：消费者有机会处理完手头工作、清理资源，再有序退出。

---

## 6. 与其他同步原语的对比

- `asyncio.Queue`：**传递数据**，一对一领取，天然带等待语义。
- `asyncio.Event`：**广播信号**，所有等待者被唤醒，不携带数据。
- `asyncio.Semaphore`：**限制并发数**，不传递数据。

一句话：要传数据就选 Queue；要同步“事件发生了”就选 Event；要限流就选 Semaphore。

---

## 7. 何时该用 asyncio.Queue？

适合：

- 爬虫、API 网关：请求抓取和解析解耦。
- 日志/指标收集：多个任务写，一个后台任务批量刷盘。
- 任务调度：动态产生任务、动态消费。

不适合：

- CPU 密集任务（用 `multiprocessing`）。
- 跨进程或跨机器（用 Redis、RabbitMQ、Kafka 等消息队列）。
- 需要持久化的场景（`asyncio.Queue` 只在内存中）。

```python
import asyncio
import random

# 一个完整的“生产者-消费者 + 哨兵退出”的演示
STOP = object()  # 唯一哨兵，比 None 更安全，不会和真实数据冲突

async def producer(q: asyncio.Queue, n: int, num_workers: int):
    for i in range(n):
        await asyncio.sleep(random.uniform(0.05, 0.15))
        await q.put(i)
        print(f"[生产者] 放入任务 {i}")
    # 生产完，给每个消费者发一个哨兵，通知它们退出
    for _ in range(num_workers):
        await q.put(STOP)

async def worker(q: asyncio.Queue, name: str):
    while True:
        item = await q.get()
        if item is STOP:
            print(f"[{name}] 收到停止信号，准备退出")
            q.task_done()
            return
        await asyncio.sleep(random.uniform(0.1, 0.3))  # 模拟处理任务
        print(f"[{name}] 完成任务 {item}")
        q.task_done()

async def main():
    q = asyncio.Queue(maxsize=5)  # 有界队列，触发反压
    num_workers = 3
    workers = [asyncio.create_task(worker(q, f"消费者-{i}")) for i in range(num_workers)]
    await producer(q, 10, num_workers)
    await q.join()                # 等所有任务被 task_done
    await asyncio.gather(*workers) # 等所有消费者真正退出
    print("全部完成")

if __name__ == "__main__":
    asyncio.run(main())
```

## py.async.event

# 第 5 单元 · 第 3 讲：Python 异步事件（Event）

> **一句话直觉**：`asyncio.Event` 是协程之间的“信号旗”——有人把它举起（`set()`），所有在等的协程立即被放行；没人举时它会让等待者优雅地“睡下”，而不是浪费 CPU 空转。

本讲面向毫无异步经验的读者，但收尾会落到工程可用的层次：从“为什么需要它”，到“行为细节”，再到“实战任务协调模式”。

---

## 1. 为什么需要 Event？——从“轮询”说起

假设你写了一个后台协程，需要等另一件事发生（比如“配置加载完毕”“服务已就绪”）才能继续。最朴素的写法是**轮询**（polling）：

```python
# 反例：轮询 —— 浪费 CPU，还容易错过瞬间状态
while not ready:
    await asyncio.sleep(0.1)
```

它有三个毛病：
1. **浪费 CPU**：即使没事发生，协程也会被反复唤醒。
2. **响应有延迟**：`sleep(0.1)` 意味着最快也要 100ms 才能察觉。
3. **共享状态不可靠**：一个普通 `bool` 变量无法安全地在多个协程之间传达“状态变化”。

`asyncio.Event`（事件）就是解决这类问题的原语：**它把“等待某个条件成立”变成一次挂起，而不是循环检查**。

它是 `asyncio` 提供的**同步原语**（synchronization primitive）之一；同类还有 `Lock`（锁）、`Semaphore`（信号量）、`Condition`（条件变量）、`Queue`（队列）。

> 📌 术语：
> - **协程**（coroutine）：用 `async def` 定义的函数，调用后得到协程对象，需 `await` 才会真正执行。
> - **任务**（task）：被事件循环（event loop）调度的协程，通过 `asyncio.create_task()` 创建。
> - **事件循环**（event loop）：`asyncio` 的核心，负责在多个协程之间切换。
> - **同步原语**（synchronization primitive）：协调多个并发单元行为的工具。

---

## 2. 最小用法：一把可以举起/放下的旗子

`Event` 的内部只有一个布尔标志（flag），加一个“等待者队列”。它的全部 API 只有四个：

| 方法 | 作用 |
|---|---|
| `set()` | 把标志设为 `True`，**唤醒所有等待者** |
| `clear()` | 把标志设为 `False`（注意：已唤醒的协程不会被“撤回”） |
| `is_set()` | 返回当前标志，`True` / `False` |
| `wait()` | 协程方法；若标志为 `False`，就一直挂起直到被 `set()` |

关键语义分两点：

- **一次性还是可重复**？`Event` 是**一次性信号**（level-triggered）。`set()` 之后 `wait()` 会立刻返回；想重复使用必须手动 `clear()`。
- **唤醒谁**？`set()` 唤醒**所有**当前正在 `wait()` 的协程——这点和 `Condition`（需 `notify` 指定数量）不同。

```python
import asyncio

async def worker(evt: asyncio.Event, name: str):
    print(f"[{name}] 等待信号...")
    await evt.wait()      # 挂起，直到 evt.set()
    print(f"[{name}] 收到信号，开工！")

async def main():
    evt = asyncio.Event()
    # 假设同一事件要给多个 worker 广播
    workers = [asyncio.create_task(worker(evt, f"w{i}")) for i in range(3)]
    await asyncio.sleep(0.5)      # 让 worker 都进入等待
    print("[main] set() 广播信号")
    evt.set()                    # 一次性唤醒全部等待者
    await asyncio.gather(*workers)

asyncio.run(main())
```

运行后你会看到：三个 worker 先挂起、`main` 举起旗子后**同时**被唤醒。这就是 `Event` 最基本的价值——**一对多、零延迟的信号传播**。

---

## 3. 结合 `timeout` 与超时控制

真实系统里“永远等下去”通常不可接受。`asyncio.wait_for()` 可以给事件等待加一个时限：

```python
async def wait_with_timeout(evt: asyncio.Event, timeout: float):
    try:
        await asyncio.wait_for(evt.wait(), timeout=timeout)
        return "ok"
    except asyncio.TimeoutError:
        return "timeout"
```

一个常见工程模式是“**启动屏障**”：主程序创建多个服务协程，它们全部 `await start_event.wait()`；所有资源就绪后，主程序 `start_event.set()`，服务们齐刷刷启动，避免抢跑。

> ⚠️ 注意：`asyncio.wait_for` 超时后会**取消**内部的 `wait()` 任务。`Event` 本身对取消是安全的——协程被取消后会从等待队列里移除，不会留下悬空的唤醒。

---

## 4. 不能“传递数据”？——区分 Event 与 Queue / Condition

初学者最常见的误用是把 `Event` 当消息通道用。请记住它的**定位边界**：

- `Event`：**广播“某事发生了”**，不携带载荷（payload）。
- `Queue`（`asyncio.Queue`）：**传递具体数据**，有背压/缓冲。
- `Condition`：**等待某个更复杂的状态条件**（例如“队列非空且未关闭”），可以反复 `notify`。

如果你的需求是“等某文件写完 → 读它”，正确做法是把 `Event` 当**触发**，把数据放在共享对象或 `Queue` 里；`Event` 只负责通知“可以读了”。

```python
# Event 作为“触发点”，数据通过普通变量传递
shared: dict = {}
ready = asyncio.Event()

async def producer():
    shared["payload"] = "42"     # 1. 先放数据
    ready.set()                  # 2. 再广播给等待者

async def consumer():
    await ready.wait()           # 等“数据已就绪”这个事实
    print("收到:", shared["payload"])
```

---

## 5. 用 `Event` 优雅地“停机”

长生命周期程序（服务、爬虫、监控循环）通常需要一个**停止信号**。经典写法是让所有工作协程循环里 `await stop_event.wait()` 配合 `timeout` 实现可中断睡眠：

```python
async def loop_forever(stop: asyncio.Event):
    while not stop.is_set():
        print("working...")
        try:
            # 睡眠 1 秒，但一旦 stop.set() 就立即返回
            await asyncio.wait_for(stop.wait(), timeout=1.0)
        except asyncio.TimeoutError:
            pass
    print("已停机")
```

这是生产代码中非常常用的模式：**把 `Event.wait()` 当作“可被立刻打断的 sleep”**，从而在不引入复杂取消逻辑的前提下实现平滑停机。

> 🔑 抽象出心法：`Event` 是异步世界里的“**通知总线的最简形态**”；一旦你发现自己写 `while ...: await sleep(...)`，就应立刻考虑换成 `Event`。

---

## 小结

- `Event` 是一个**布尔标志 + 等待队列**，用 `set()`/`clear()` 控制、`wait()` 等待。
- `set()` 是**广播**行为，唤醒所有等待者；`Event` 不携带数据。
- 典型用途：**启动屏障、停机信号、状态翻转通知、可中断 sleep**。
- 选用原则：**只传达“发生了”用 `Event`；要传数据用 `Queue`；要复杂条件用 `Condition`**。

```python
import asyncio


async def service(name: str, start: asyncio.Event, stop: asyncio.Event):
    print(f"[{name}] 等待启动信号...")
    await start.wait()                          # 启动屏障：一起等
    print(f"[{name}] 已启动，开始工作")

    while not stop.is_set():
        print(f"[{name}] 工作中...")
        try:
            # 可被 stop.set() 立刻打断的“睡眠”
            await asyncio.wait_for(stop.wait(), timeout=1.0)
        except asyncio.TimeoutError:
            pass

    print(f"[{name}] 收到停机信号，退出")


async def main():
    start = asyncio.Event()      # 启动屏障
    stop = asyncio.Event()       # 停机信号

    tasks = [
        asyncio.create_task(service("svc-A", start, stop)),
        asyncio.create_task(service("svc-B", start, stop)),
    ]

    await asyncio.sleep(0.5)
    print("[main] 所有资源就绪，set(start)")
    start.set()                  # 一次 set，广播给所有等待者

    await asyncio.sleep(2.0)
    print("[main] 发出停机信号")
    stop.set()                   # 也是广播：所有协程立刻跳出循环

    await asyncio.gather(*tasks)
    print("[main] 全部退出")


asyncio.run(main())
```

## py.async.lock

# 异步锁：`asyncio.Lock`

## 一句话直觉

当多个协程（coroutine）同时读写同一块共享状态时，`asyncio.Lock` 保证**同一时刻只有一个协程能进入临界区**，像给共享资源加了一把钥匙，谁拿到钥匙谁才能改。

---

## 1. 为什么需要锁？先看没有锁会发生什么

在 `asyncio` 中，协程是**协作式**调度的：只有当协程执行到 `await` 时，事件循环（event loop）才可能切换到其他协程。这意味着如果两个协程都对同一变量做「读—改—写」，中间恰好有 `await`，就会互相覆盖。

```python
import asyncio

counter = 0

async def bad_add():
    global counter
    tmp = counter          # 读
    await asyncio.sleep(0) # 在这里让出控制权 -> 另一个协程可能已经改了 counter
    counter = tmp + 1      # 写

async def main():
    await asyncio.gather(bad_add(), bad_add())
    print(counter)  # 期望 2，实际很多时候是 1

asyncio.run(main())
```

**结论**：只要有 `await` 穿插在「读」和「写」之间，共享状态就不安全。

---

## 2. 用 `asyncio.Lock` 保护临界区

`Lock` 的用法几乎和线程里的 `threading.Lock` 一样：`async with lock:` 或 `await lock.acquire()` / `lock.release()`。关键是**获取锁时必须 `await`**，因为等锁期间要让出控制权，别的事件循环任务才能跑。

```python
import asyncio

counter = 0
lock = asyncio.Lock()  # 注意：锁必须在事件循环内部创建（见第 4 节）

async def safe_add():
    global counter
    async with lock:               # 进入前若锁被占，就 await 等待
        tmp = counter
        await asyncio.sleep(0)     # 即使里面还有 await，别人也进不来
        counter = tmp + 1

async def main():
    await asyncio.gather(safe_add(), safe_add())
    print(counter)  # 一定是 2

asyncio.run(main())
```

**结论**：`async with lock:` 是一次「拿钥匙—干活—还钥匙」的原子操作，无论里面包含多少 `await`，其他协程都不会插进来。

---

## 3. 锁的语义细节：谁先到、谁等待

- `Lock()` 初始为**未锁定**状态。
- 第一个 `acquire` 立即成功（表现为 `async with` 不暂停执行）。
- 后续 `acquire` 会挂起当前协程，直到持锁者 `release`。
- 释放的顺序是 **FIFO**（先进先出）：先等待的协程先拿到锁，避免饥饿（starvation）。
- 同一个协程**重复获取同一把非重入锁会死锁**（因为它自己在等自己）。如需重入，请用 `asyncio.Condition` 或自己组合（`asyncio.Lock` 不提供 `RLock`）。

```python
import asyncio

async def worker(name, lock):
    async with lock:
        print(f"{name} got lock")
        await asyncio.sleep(0.2)
        print(f"{name} releasing")

async def main():
    lock = asyncio.Lock()
    await asyncio.gather(
        worker("A", lock),
        worker("B", lock),
        worker("C", lock),
    )

asyncio.run(main())
# 输出稳定为 A -> B -> C，说明等待队列是 FIFO
```

**结论**：`asyncio.Lock` 不只是「互斥」，还提供公平的等待队列。

---

## 4. 常见坑点：锁的创建时机与超时

### 4.1 锁必须在事件循环里创建

`asyncio.Lock()` 在旧版本（Python 3.10 之前）会绑定当前事件循环，如果在模块加载时创建、随后在 `asyncio.run()` 里用，可能报 `RuntimeError: got Future attached to a different loop`。稳妥写法是**在协程内部或 `main()` 里创建**。

```python
import asyncio

# ✅ 推荐：在 async 函数内创建
async def main():
    lock = asyncio.Lock()
    ...

# ❌ 不推荐：模块级创建（跨事件循环时容易出错）
# lock = asyncio.Lock()
```

### 4.2 避免无限等待：用 `asyncio.wait_for`

如果某个协程持锁太久，其他协程会一直挂起。给获取锁加超时：

```python
import asyncio

async def main():
    lock = asyncio.Lock()

    async def slow_holder():
        async with lock:
            await asyncio.sleep(10)

    async def impatient():
        try:
            await asyncio.wait_for(lock.acquire(), timeout=1)
            try:
                print("impatient acquired")
            finally:
                lock.release()
        except asyncio.TimeoutError:
            print("impatient gave up after 1s")

    await asyncio.gather(slow_holder(), impatient())

asyncio.run(main())
```

**结论**：能拿到锁不代表要无限等；超时是把异步应用的「韧性」设计进去。

---

## 5. 什么时候不该用 `asyncio.Lock`

- 如果你只是**读**共享数据，且写操作本身是原子的（比如给 `dict` 赋一个完整的新值），可以不加锁。
- 如果你要限制**并发量**而不是互斥，用 `asyncio.Semaphore`（信号量）。
- 如果你要在**线程**之间同步，用 `threading.Lock`；`asyncio.Lock` 只对同一事件循环内的协程有意义。
- 如果你在写库里需要线程安全的装饰器，参考 `typing.Concatenate` + `threading.Lock` 的模式，那是线程级同步，不是协程级。

```python
import asyncio

# 限制同时最多 3 个任务访问下游资源
sem = asyncio.Semaphore(3)

async def limited(i):
    async with sem:
        print(f"task {i} running")
        await asyncio.sleep(0.1)

async def main():
    await asyncio.gather(*(limited(i) for i in range(10)))

asyncio.run(main())
```

**结论**：锁是「互斥」工具，不要拿它当「限流」工具。

---

## 6. 总结

| 场景 | 该用什么 |
| --- | --- |
| 同一事件循环内协程保护共享状态 | `asyncio.Lock` |
| 跨线程共享状态 | `threading.Lock` |
| 限制并发数 | `asyncio.Semaphore` |
| 等待某条件成立 | `asyncio.Condition` / `asyncio.Event` |

记住三点：**一把锁、一个临界区、所有 `await` 都在里面**；锁要在事件循环里建；等待要能超时。

```python
import asyncio

# 共享资源
balance = 100
lock = asyncio.Lock()  # 也可以放到 main() 里创建

async def withdraw(name: str, amount: int):
    global balance
    async with lock:                      # 进入临界区，自动加锁/解锁
        current = balance
        await asyncio.sleep(0.05)          # 模拟 I/O 等待，故意插入 await
        if current >= amount:
            balance = current - amount
            print(f"{name} 取款 {amount}, 余额 {balance}")
        else:
            print(f"{name} 余额不足, 当前 {current}")

async def main():
    await asyncio.gather(
        withdraw("A", 80),
        withdraw("B", 80),
        withdraw("C", 50),
    )
    print("最终余额:", balance)

asyncio.run(main())
```


---

## 本课题目

### single_choice · None



- [A] 每个等待的 get() 都会拿到同一个元素，因为是广播
- [B] 先进入等待的 get() 先被唤醒并取走元素，通常遵循等待顺序
- [C] 所有等待者会随机竞争，谁拿到元素完全不确定
- [D] 队列会一次性把全部新元素分发给所有等待者，直到队列空

**参考答案**：1

**解析**：asyncio.Queue 的 get() 等待者内部由等待队列管理，put 唤醒等待者时通常按等待先后顺序恢复，且每个元素只会被一个 get() 取走，不是广播。

### single_choice · None



- [A] 两者完全一样，只是 asyncio.Queue 多了一个 async 前缀
- [B] asyncio.Queue 的阻塞式获取通过 await queue.get() 实现，而 queue.Queue 使用阻塞的 get()
- [C] queue.Queue 只能在多线程中使用，asyncio.Queue 只能在多进程中使用
- [D] asyncio.Queue 不支持设置队列容量上限

**参考答案**：1

**解析**：asyncio.Queue 面向协程，put/get 是异步等待；queue.Queue 是线程安全的同步队列，使用阻塞调用。两者用途不同，且 asyncio.Queue 可设置 maxsize。

### single_choice · None



- [A] 1
- [B] 2
- [C] None
- [D] 抛出 QueueEmpty 异常

**参考答案**：0

**解析**：asyncio.Queue 是先进先出（FIFO），先 put 的 1 会先被 get 取出，因此打印 1。

### single_choice · None



- [A] asyncio.Queue
- [B] asyncio.LifoQueue
- [C] asyncio.PriorityQueue
- [D] asyncio.Semaphore

**参考答案**：2

**解析**：asyncio 提供 PriorityQueue 按优先级排序取出元素，LifoQueue 是后进先出，Semaphore 是信号量，不是队列。

### single_choice · None



- [A] LifoQueue 的 get 总是取出最后放入的元素，Queue 取出最先放入的元素
- [B] LifoQueue 不支持 maxsize 参数
- [C] LifoQueue 的 put 操作会覆盖旧元素
- [D] LifoQueue 只能用于单生产者单消费者场景

**参考答案**：0

**解析**：LifoQueue 是后进先出（栈式），Queue 是先进先出。两者都支持 maxsize，也可有多种生产/消费组合。

### single_choice · None



- [A] 队列变成 ['a','b']
- [B] 抛出 asyncio.QueueFull 异常
- [C] 阻塞直到有人 get
- [D] 'b' 被静默丢弃，无异常

**参考答案**：1

**解析**：put_nowait 不等待，容量为 1 且已满时直接抛出 asyncio.QueueFull。

### single_choice · None



- [A] 生产者会立即被阻塞，程序很快死锁
- [B] 队列无限增长，内存占用持续上升
- [C] 消费者会收到 QueueFull 异常
- [D] put 会自动丢弃旧元素以控制内存

**参考答案**：1

**解析**：无界队列不会让 put 等待，生产速度过快会导致元素堆积，内存持续增长。需要设置 maxsize 做背压。

### single_choice · None



- [A] 在消费者协程中捕获 asyncio.CancelledError，清理资源后重新抛出
- [B] 捕获 Exception 并忽略所有异常
- [C] 调用 queue.close() 强制关闭队列
- [D] 不允许取消消费者，否则队列会损坏

**参考答案**：0

**解析**：CancelledError 在 Python 3.8+ 中继承自 BaseException，通常应捕获做清理后重新抛出，让取消语义继续传播。忽略异常会破坏取消机制。

### single_choice · None



- [A] 它内部使用线程锁来保证线程安全
- [B] 它使用 collections.deque 保存元素，并维护 getter/putter 的等待队列
- [C] 它底层是一个固定长度的数组，无法动态扩容
- [D] 它通过轮询队列状态来实现阻塞与唤醒

**参考答案**：1

**解析**：asyncio.Queue 内部通常用 deque 存储元素，并通过 Future 管理等待的 getter 和 putter，并非线程锁或轮询。

### single_choice · None



- [A] 该异常会导致整个事件循环停止，无法继续
- [B] 队列会自动取消该消费者的等待，但消费者任务可能已结束，需要重新创建任务
- [C] 队列中已取出的元素会自动放回队列头部
- [D] 需要调用 queue.reset() 才能恢复队列

**参考答案**：1

**解析**：未捕获异常会终止该消费者任务，队列本身不会自动恢复该任务。需要重新创建消费者，或在外层捕获异常后继续循环。

### single_choice · None



- [A] 它返回队列当前元素个数，可用来判断队列是否为空，但并发下结果可能过期
- [B] 它返回队列最大容量
- [C] 它返回已调用 task_done() 的次数
- [D] 它返回活跃消费者协程的数量

**参考答案**：0

**解析**：qsize() 返回当前元素数量，是瞬时快照，多协程并发时可能随即变化。它不返回容量、完成计数或消费者数量。

### single_choice · None



- [A] while queue.empty(): await asyncio.sleep(0.1); item = queue.get_nowait()
- [B] item = await queue.get()
- [C] while not queue.empty(): item = queue.get_nowait()
- [D] item = queue.get()

**参考答案**：1

**解析**：await queue.get() 在队列为空时会挂起当前协程，有元素时自动唤醒，避免忙等待。轮询 empty() 会浪费 CPU 且存在竞态。

### single_choice · None



- [A] 当队列已有 3 个元素时，继续 await queue.put(x) 会立即抛出 QueueFull 异常
- [B] 当队列已有 3 个元素时，继续 await queue.put(x) 会挂起，直到有消费者取走元素
- [C] maxsize 只限制 get 的次数，不限制 put 的次数
- [D] maxsize=3 表示最多可以同时有 3 个生产者协程访问队列

**参考答案**：1

**解析**：有界 asyncio.Queue 在满时 put 会异步等待，直到有空间，而不是立即抛异常；QueueFull 通常出现在非等待的 put_nowait 调用中。

### single_choice · None



- [A] 方法会返回 False，表示未放入成功
- [B] 方法会一直等待，直到队列有空位
- [C] 方法会抛出 asyncio.QueueFull 异常
- [D] 方法会覆盖队列中最旧的元素，保证放入成功

**参考答案**：2

**解析**：put_nowait 不会等待，队列满时直接抛出 asyncio.QueueFull。若希望等待，应使用 await put()。

### single_choice · None



- [A] 第二次 get 会立即返回 None
- [B] 第二次 get 会抛出 RuntimeError
- [C] 如果另一协程在 join() 上等待，join() 可能永远不返回
- [D] 队列会自动重置未完成计数，所以没有影响

**参考答案**：2

**解析**：join() 等待未完成任务数为 0。每次 get 后应配对调用 task_done()，否则未完成计数不会归零，join() 会一直等待。

### single_choice · None



- [A] 使用 queue.get_nowait() 并配合轮询 sleep，避免阻塞
- [B] 直接 await queue.get() 即可，asyncio 取消会正常中断该等待
- [C] 必须改用线程队列，asyncio.Queue 无法被取消
- [D] 需要在 get() 外层捕获 BaseException 并手动重启事件循环

**参考答案**：1

**解析**：await queue.get() 是可取消的等待操作，当任务被 cancel 时，等待中的 get() 会收到 CancelledError，可以正常响应取消。轮询反而浪费且不必要。

### single_choice · None



- [A] empty() 返回 True 时，后续 await get() 一定不会阻塞
- [B] full() 返回 True 时，后续 await put() 一定不会阻塞
- [C] 它们只是瞬时状态快照，在多协程并发下调用后状态可能立即改变
- [D] 这两个方法不存在，asyncio.Queue 只提供 qsize()

**参考答案**：2

**解析**：empty()/full() 反映调用瞬间的状态，其他协程可能马上 put/get，因此不能据此做同步决策。正确做法是直接 await get()/put() 并处理等待。

### single_choice · None



- [A] 在多个独立进程之间传递大型二进制数据
- [B] 在同一个事件循环内的多个协程之间传递数据并协调生产/消费速度
- [C] 替换数据库连接池来管理数据库连接
- [D] 在同步函数中实现线程安全的全局缓存

**参考答案**：1

**解析**：asyncio.Queue 用于同一事件循环内的协程间通信与流量控制。进程间通信需要 multiprocessing 队列，线程安全缓存需要线程锁或 queue.Queue。

### single_choice · None



- [A] 无限容量，put 永远不会因为队列满而等待
- [B] 默认容量为 0，put 总是立即阻塞
- [C] 默认容量为 1，同一时间只能存一个元素
- [D] 容量由事件循环自动决定，通常等于 CPU 核心数

**参考答案**：0

**解析**：asyncio.Queue() 默认 maxsize=0，表示无界队列，put 不会因容量满而等待；但仍可能在极少数情况下受内部实现影响，通常可视为无界。

### single_choice · None



- [A] 等待队列中至少出现一个元素
- [B] 等待队列变为空且所有已取出的元素都已调用 task_done()
- [C] 等待所有生产者协程结束并退出
- [D] 等待队列被垃圾回收

**参考答案**：1

**解析**：join() 等待未完成任务计数归零。当队列为空并且每个已 get 的元素都调用了 task_done() 时，join() 才会返回。

### single_choice · None



- [A] 在多个协程之间传递数据对象
- [B] 让一个或多个协程等待某个条件被设置后再继续执行
- [C] 限制同时运行的协程数量
- [D] 定时触发某个协程执行

**参考答案**：1

**解析**：asyncio.Event 是一种协程间同步原语，它维护一个内部标志，协程可以用 await event.wait() 阻塞直到标志被 set()，从而等待某个条件成立。它不传数据、不限并发数、也不做定时。

### single_choice · None



- [A] 标志初始为 True，调用 wait() 会立即返回
- [B] 标志初始为 False，调用 wait() 会阻塞直到被 set()
- [C] 标志没有初始值，必须显式设置
- [D] 标志只能被设置一次，之后再也不能清除

**参考答案**：1

**解析**：asyncio.Event 创建时内部标志默认为 False，此时 wait() 会挂起协程；调用 set() 后标志变为 True，所有等待者被唤醒且后续 wait() 立即返回。clear() 可把标志重置为 False。

### multi_choice · None



- [A] 等待某个后台任务完成信号，多个消费者协程随后开始处理
- [B] 限制同时访问某资源的协程不超过 3 个
- [C] 在启动阶段等配置加载完成后放行所有依赖组件
- [D] 实现一个可在关闭时唤醒所有等待者的停止标志
- [E] 在两个协程之间安全传递字符串消息

**参考答案**：[0, 2, 3]

**解析**：Event 适合等待/广播某条件成立，如完成信号、启动放行、停止标志。限制并发数应用 Semaphore；传递消息应用 Queue。

### multi_choice · None



- [A] Event 只有一个布尔标志，Condition 可关联更复杂的条件判断
- [B] Event 的 set() 会唤醒所有等待者，Condition 可用 notify() 只唤醒一个
- [C] Condition 需要配合 Lock 使用，Event 不需要
- [D] Event 的 wait() 会阻塞线程，Condition 不会
- [E] 两者都属于 asyncio 提供的同步原语

**参考答案**：[0, 1, 2, 4]

**解析**：Event 是单标志广播；Condition 支持 notify 单独唤醒并需锁保护。二者都是 asyncio 同步原语。Event 的 wait() 是协程不阻塞线程，因此‘阻塞线程’错误。

### fill_blank · None



**参考答案**：["wait"]

**解析**：等待事件的方法名为 wait()，需用 await 调用，如 await e.wait()。

### fill_blank · None



**参考答案**：["set"]

**解析**：set() 是同步方法，将标志置 True 并广播唤醒所有等待者。

### fill_blank · None



**参考答案**：["clear"]

**解析**：clear() 将标志重置为 False，之后 wait() 会重新挂起协程。

### code_reading · None



**参考答案**：输出 True。因为 set() 已把标志置为 True，wait() 不会挂起而是立即返回 True，所以打印 True。

**解析**：Event 在标志为 True 时 wait() 立即返回 True，因此协程不被阻塞，直接打印 True。

### code_reading · None



**参考答案**：先打印 'before set'，随后 A、B 被 set() 唤醒并打印（A、B 的先后顺序不严格保证，通常按创建顺序）。理由：两个等待者在 sleep(0) 后均阻塞在 wait()，set() 广播唤醒所有等待者。

**解析**：create_task 后经一次 sleep(0) 让两个协程运行到 wait() 并挂起，主协程打印 'before set'，e.set() 唤醒全部等待者，A 与 B 相继打印。两者的相对顺序取决于事件循环调度，通常按就绪顺序即创建顺序。

### code_reading · None



**参考答案**：代码会抛出 asyncio.TimeoutError。因为 clear() 把标志重置为 False，wait() 会一直阻塞，被 wait_for 在 0.05 秒超时中断。若不调用 clear，wait() 会立即返回。

**解析**：clear() 将标志恢复为 False，使得后续 wait() 再次挂起。此处用 wait_for 加超时，以便观察到挂起状态并抛出超时异常。

### scenario · None



**解析**：Event 初始标志为 False，请求协程 await event.wait() 挂起；配置加载完成后调用 event.set() 广播唤醒所有等待者。相比轮询布尔变量，Event 由事件循环调度、无忙等待、能一次唤醒全部等待者，更高效且避免竞态。

### single_choice · None



- [A] 抛出异常，因为重复等待
- [B] 协程立即继续执行，不会被挂起
- [C] 协程被挂起，直到再次调用 set()
- [D] wait() 返回 False

**参考答案**：1

**解析**：当标志为 True 时，wait() 是一个非阻塞操作，直接返回并让协程继续运行，这正是 Event 作为一次性‘闸门’语义的体现。

### single_choice · None



- [A] 只有第一个等待的协程被唤醒
- [B] 所有正在等待的协程都会被唤醒
- [C] 等待的协程不会被唤醒，需要手动通知
- [D] set() 是异步方法，必须 await

**参考答案**：1

**解析**：set() 会把内部标志置为 True，并唤醒所有当前在该 Event 上等待的协程（类似‘广播’）。set() 是普通同步方法，不需要 await。

### single_choice · None



- [A] wait() 是同步方法，直接调用即可
- [B] wait() 是协程方法，需要用 await 调用
- [C] wait() 返回被设置的值
- [D] wait() 会永久阻塞，无法取消

**参考答案**：1

**解析**：wait() 是一个协程方法，必须用 await event.wait() 调用，返回值为 True（在较新版本中始终返回 True）。等待期间若协程被取消，会抛出 CancelledError，因此并非不可取消。

### single_choice · None



- [A] 删除该 Event 对象并释放资源
- [B] 把内部标志重置为 False，使后续 wait() 再次阻塞
- [C] 唤醒所有等待者
- [D] 返回当前标志的值

**参考答案**：1

**解析**：clear() 把标志重置为 False。之后调用 wait() 的协程会再次阻塞，直到下次 set()。clear() 不影响已经因 set() 而恢复运行的协程。

### single_choice · None



- [A] 两者完全一样，可以互相替换
- [B] asyncio.Event 的 wait() 是协程需要 await，threading.Event 的 wait() 是阻塞调用
- [C] threading.Event 不支持 set()
- [D] asyncio.Event 只能被一个协程使用

**参考答案**：1

**解析**：两者语义相似，但 asyncio.Event 面向单线程事件循环，wait() 是协程不会阻塞线程；threading.Event 面向多线程，wait() 会阻塞当前线程。二者不可直接互换。

### single_choice · None



- [A] asyncio.Lock
- [B] asyncio.Semaphore
- [C] asyncio.Event
- [D] asyncio.Queue

**参考答案**：2

**解析**：Event 用于‘等待某条件成立’并可广播唤醒所有等待者，正好匹配‘等待初始化完成再一起继续’。Lock 是互斥，Semaphore 限流，Queue 传数据，都不符合该语义。

### single_choice · None



- [A] 第二次 set() 会抛出 RuntimeError
- [B] 重复 set() 是幂等的，标志保持 True，不会出错
- [C] 重复 set() 会清除之前的等待者
- [D] 只有第一次 set() 有效，之后调用都会被忽略并报错

**参考答案**：1

**解析**：set() 是幂等的：如果标志已是 True，再次调用不产生副作用也不会报错。对已经唤醒的等待者也不会造成问题。

### multi_choice · None



- [A] 它维护一个布尔型内部标志
- [B] 调用 set() 会唤醒所有当前等待的协程
- [C] wait() 在标志为 True 时立即返回
- [D] clear() 之后标志变为 False
- [E] set() 必须由 await 调用

**参考答案**：[0, 1, 2, 3]

**解析**：Event 维护布尔标志，set() 广播唤醒全部等待者，标志为 True 时 wait() 立即返回，clear() 重置为 False。set() 是普通同步方法，不需要 await，故最后一项错误。

### single_choice · None



- [A] 因为协程是并行运行的，会同时修改内存导致数据竞争
- [B] 因为协程会在 await 处让出控制权，中途可能被其他协程插入执行
- [C] 因为 Python 的 GIL 无法保护任何变量
- [D] 因为 asyncio 的锁可以提升协程执行速度

**参考答案**：1

**解析**：asyncio 是单线程并发，协程只在 await 处让出控制权。若在读取共享状态后、写回之前发生 await，其他协程可能插入并修改该状态，导致逻辑上的竞态。锁的作用是把这段临界区变成不可被插入的整体。

### single_choice · None



- [A] async def inc():
      lock = asyncio.Lock()
      async with lock:
          counter += 1
- [B] async def inc(lock):
      lock.acquire()
      try:
          counter += 1
      finally:
          lock.release()
- [C] async def inc(lock):
      async with lock:
          counter += 1
- [D] async def inc(lock):
      with lock:
          counter += 1

**参考答案**：2

**解析**：asyncio.Lock 必须用 async with 或 await lock.acquire()/lock.release() 使用。选项 A 每次都新建锁，等于没锁；选项 B 忘了 await，acquire 返回的是协程对象；选项 D 用了同步 with，asyncio.Lock 不支持。

### multi_choice · None



- [A] 在 await 前读、await 后写同一个共享变量
- [B] 多个协程共享一个连接池并需要互斥地重建连接
- [C] 临界区内没有任何 await，纯 CPU 计算
- [D] 多个协程竞争同一份文件句柄的写入顺序
- [E] 只需读取一个从不修改的常量

**参考答案**：[0, 1, 3]

**解析**：需要锁的是「跨 await 的读改写」「互斥地重建共享资源」「控制对共享资源的写入顺序」等场景。无 await 的临界区是原子的，不需要锁；只读常量不涉及竞争。

### multi_choice · None



- [A] 可以用 async with 自动获取和释放
- [B] 如果不用 async with，必须保证 release 在 finally 中调用
- [C] acquire 时如果锁已被占用，协程会挂起而非阻塞事件循环
- [D] 可以在没有持有锁的协程中调用 release 而不会报错
- [E] 锁一旦创建就不能被任何协程获取

**参考答案**：[0, 1, 2]

**解析**：asyncio.Lock 支持 async with；手动模式需 try/finally 保证释放；等待锁时协程挂起，事件循环可继续运行其他任务。release 只能在持有锁时调用，否则抛 RuntimeError。

### multi_choice · None



- [A] A
- [B] B
- [C] C
- [D] D
- [E] E

**参考答案**：[0, 2, 3]

**解析**：A 每次新建锁，没有共享对象，无法互斥；C 忘记 await，acquire 返回协程对象未真正加锁；D 用同步 with，asyncio.Lock 不支持。B、E 是正确用法。

### multi_choice · None



- [A] 应使用 threading.Lock 保护跨线程共享状态，而不是 asyncio.Lock
- [B] 若必须在两个线程间互斥，应把异步任务全部调度到拥有事件循环的那个线程，用 loop.call_soon_threadsafe
- [C] 直接在另一个线程里 await 该 asyncio.Lock 即可
- [D] asyncio.Lock 可以在任意线程中被安全 acquire

**参考答案**：[0, 1]

**解析**：asyncio.Lock 绑定事件循环，不是线程安全的跨线程锁。跨线程共享应使用 threading.Lock，或把所有操作通过 call_soon_threadsafe 集中到事件循环线程执行。

### fill_blank · None



**参考答案**：["acquire"]

**解析**：asyncio.Lock 的获取方法是协程 acquire，需要 await；释放方法 release 是普通方法，但仍需在持锁时调用。

### fill_blank · None



**参考答案**：["死锁", "deadlock"]

**解析**：同一协程重复获取不可重入的锁，会永久等待自己释放，造成死锁。需要重入语义时应改用可重入锁或重新设计临界区。

### fill_blank · None



**参考答案**：["协程", "coroutine"]

**解析**：asyncio 的锁在 await acquire 时挂起当前协程，把控制权交还事件循环，其他任务得以继续执行。它不是阻塞线程，因此不会卡死整个循环。

### code_reading · None



**参考答案**：输出顺序为 enter 1 / leave 1 / enter 2 / leave 2（或 1、2 顺序互换但内部成对）。因为锁保证同一时刻只有一个协程进入临界区，即使临界区内有 await，另一个协程也会等锁释放后再进入。

**解析**：锁把临界区变成互斥区间。task(1) 先获得锁并 print enter，遇 await sleep 让出；task(2) 尝试 acquire 被挂起，直到 task(1) 打印 leave 并退出 async with 释放锁，task(2) 才继续。

### scenario · None



**解析**：读-判断-写之间跨了 await，其他协程可能插入，导致基于旧值写回覆盖新值，即竞态条件。应把这段逻辑放入由全局唯一 asyncio.Lock 保护的临界区，用 async with lock 包裹读改写过程，确保互斥。

### scenario · None



**解析**：吞吐下降通常因为临界区过大、其中包含耗时的 await（如网络请求），导致其他协程长时间等锁；死锁往往是同一协程在持锁期间又去获取同一把不可重入锁（如嵌套调用）。改进方向：缩小锁的粒度，只保护真正的共享状态读写，把 I/O 移出临界区；避免在同一协程内重复获取同一把锁，必要时拆分成不同锁或重新设计调用链。

### single_choice · None



- [A] 它可以在多个线程之间安全共享，实现跨线程互斥
- [B] 它绑定到创建它的事件循环，不应跨事件循环使用
- [C] 它一旦被获取就会阻塞整个事件循环
- [D] 它支持重入，同一个协程可以重复 acquire 而不死锁

**参考答案**：1

**解析**：asyncio.Lock 是绑定事件循环的，不应跨不同事件循环共享。它不是线程锁；获取时协程会挂起而非阻塞整个循环；它不可重入，同一协程重复 acquire 会死锁。

### single_choice · None



- [A] 1
- [B] 2
- [C] 0
- [D] 不确定，取决于调度顺序

**参考答案**：1

**解析**：锁保证了临界区的互斥。每个协程在持锁期间完成「读-改-写」，即使中间有 await 让出，其他协程也无法进入临界区，因此两次自增得到 2。

### single_choice · None



- [A] 1
- [B] 2
- [C] 0
- [D] 运行时报错

**参考答案**：1

**解析**：去掉锁后，由于 await asyncio.sleep(0) 处会让出控制权，两个协程可能都先读到 tmp=0，再各自写回 1，但经典演示中常观察到结果为 1；不过 sleep(0) 的调度会让两次都可能读到中间值，题意问『最可能』——在等长让出场景下两步读改写会丢失一次更新得到 1。为保证题目稳健，实际正确判断是『丢失更新』导致小于 2，标准答案为 1。

### single_choice · None



- [A] asyncio.Lock 的 acquire 是协程，需要 await；threading.Lock 的 acquire 是阻塞调用
- [B] 两者都可以在 async 函数里直接用 with 语句
- [C] asyncio.Lock 可以被多个线程同时持有
- [D] threading.Lock 只能在事件循环里使用

**参考答案**：0

**解析**：asyncio.Lock.acquire 返回协程，需 await，挂起的是协程而非线程；threading.Lock.acquire 会阻塞线程。asyncio.Lock 不支持同步 with，也不能跨线程持有。

### single_choice · None



- [A] 需要，任何共享访问都必须加锁
- [B] 不需要，因为没有 await 就不会让出控制权，其他协程无法插入
- [C] 需要，因为 GIL 不保证原子性
- [D] 不需要，因为 asyncio 本来就是串行的

**参考答案**：1

**解析**：asyncio 协程协作式调度，只在 await 处切换。如果没有 await，临界区会原子地跑完，不会被其他协程插入，因此单个事件循环内无需加锁（但跨线程场景另当别论）。

### single_choice · None



- [A] async with lock:
      async with lock:
          pass
- [B] await lock.acquire()
  await lock.release()
- [C] async with lock:
      await asyncio.sleep(1)
- [D] lock = asyncio.Lock()
  async with lock:
      pass

**参考答案**：0

**解析**：asyncio.Lock 不可重入。同一协程在已持锁时再次 acquire 会永远等待自己释放，造成死锁。其余选项都是正确用法。

### single_choice · None



- [A] 在每次进入协程时新建一个 Lock 对象
- [B] 在模块顶层或应用初始化时创建一次，供所有协程共享
- [C] 在事件循环里用 loop.create_lock() 每次创建
- [D] 用 asyncio.new_event_loop() 为每个协程创建锁

**参考答案**：1

**解析**：锁要保护同一份共享状态，必须是被所有相关协程共享的同一个对象，通常在模块层或初始化阶段创建一次。每次新建锁等于没锁。

### single_choice · None



- [A] 没有任何问题，推荐显式传 loop
- [B] 若传入的 loop 与当前运行的 loop 不一致，会抛出 RuntimeError 或行为异常
- [C] 会让锁退化成线程锁
- [D] 会自动禁用异步特性

**参考答案**：1

**解析**：锁绑定到创建时的 loop。若与当前运行的 loop 不一致（例如在另一个 loop 中 await 该锁），会报错。较新版本已移除构造中的 loop 参数，推荐不传，让它使用当前运行的 loop。
