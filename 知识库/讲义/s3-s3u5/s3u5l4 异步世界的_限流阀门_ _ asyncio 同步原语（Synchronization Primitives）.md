# s3u5l4 异步世界的"限流阀门" / asyncio 同步原语（Synchronization Primitives）

> 来源 `content/lessons/s3u5l4.json`

## py.async.semaphore

# py.async.semaphore：异步世界的"限流阀门"

> **一句话直觉**：当你的程序同时发起 1000 个网络请求把对方服务器打爆、或者同时打开 10000 个文件把你自己的电脑卡死时，`asyncio.Semaphore`（信号量）就是那个站在门口、手里只有 N 把钥匙、多一个都不放行的"门卫"。

---

## 1. 为什么需要信号量？先从"并发失控"说起

`asyncio`（异步 I/O）的核心魅力，是让成千上万个任务"并发"运行而不阻塞。但**并发 ≠ 无限**。每个并发任务背后都可能对应一个数据库连接、一个文件句柄、一个 HTTP 连接、一段 GPU 显存——这些都是**稀缺资源（scarce resource）**，超过上限系统就会崩溃或报错。

信号量（Semaphore）来自操作系统经典概念，本质是一个**内部计数器（counter）**：
- 初始值为 N（例如 3）；
- 每有一个协程（coroutine）要进入临界区，就执行一次"获取"（`acquire`），计数器减 1；
- 计数为 0 时，后来的协程会被**挂起等待**，直到有人"释放"（`release`），计数器加 1。

这就是它和普通锁（`Lock`）的区别：`Lock` 的计数器永远是 1（互斥），`Semaphore` 可以是任意 N（限流）。

```python
import asyncio

async def worker(sem: asyncio.Semaphore, name: str):
    async with sem:           # 获取信号量：计数 -1
        print(f"{name} 开始工作")
        await asyncio.sleep(1) # 模拟耗时 I/O
        print(f"{name} 完成")
    # 退出 async with：自动释放，计数 +1

async def main():
    sem = asyncio.Semaphore(2)   # 只允许 2 个任务同时进入
    await asyncio.gather(*(worker(sem, f"任务{i}") for i in range(5)))

asyncio.run(main())
```

**关键结论**：信号量是一种**异步同步原语（synchronization primitive）**，用来"限流"而不是"互斥"。`asyncio.Semaphore` 必须在事件循环（event loop）内使用，也不能跨进程或跨线程共享。

---

## 2. `asyncio.Semaphore` 的用法：`acquire` / `release` 与 `async with`

`asyncio.Semaphore` 提供了两种使用方式：

1. **手动模式**：`await sem.acquire()` 与 `sem.release()`；
2. **推荐模式**：`async with sem:`，等价于 `try/finally` 里执行上面两步，**即使中途抛异常也能正确释放**。

```python
import asyncio

async def fetch(sem: asyncio.Semaphore, i: int):
    await sem.acquire()            # 手动获取
    try:
        print(f"fetch {i} 正在执行")
        await asyncio.sleep(0.5)
        if i == 2:
            raise ValueError("模拟请求失败")
    finally:
        sem.release()              # 保证一定释放，否则会泄漏"名额"

async def main():
    sem = asyncio.Semaphore(3)
    tasks = [asyncio.create_task(fetch(sem, i)) for i in range(6)]
    # 个别任务抛异常不影响其他任务继续排队
    results = await asyncio.gather(*tasks, return_exceptions=True)
    print("结果：", results)

asyncio.run(main())
```

**关键结论**：
- 永远优先用 `async with sem:`，避免漏写 `release()` 导致"名额泄漏"（leak），继而让整个程序死锁。
- `Semaphore` 的构造函数参数必须是**正整数**，`Semaphore(0)` 会让所有协程永久挂起。

---

## 3. 典型工程场景：用信号量包装"有上限"的资源池

真实项目中最常见的一个模式是：**一万个 URL，但只允许同时 20 个 HTTP 请求**。这就是信号量的最佳舞台。下面这段示例不引入第三方库，用 `asyncio.sleep` 模拟网络延迟：

```python
import asyncio
import time

async def download(url: str, sem: asyncio.Semaphore):
    async with sem:                       # 最多 N 个协程同时进入
        print(f"[开始] {url}")
        await asyncio.sleep(0.8)          # 模拟网络 I/O
        print(f"[完成] {url}")
        return len(url)

async def main():
    urls = [f"https://example.com/page/{i}" for i in range(10)]
    sem = asyncio.Semaphore(3)            # 最多 3 个并发

    start = time.perf_counter()
    results = await asyncio.gather(*(download(u, sem) for u in urls))
    elapsed = time.perf_counter() - start

    print(f"处理 {len(results)} 个 URL，耗时 {elapsed:.2f}s")
    # 若无限并发 → 约 0.8s；若完全串行 → 约 8s；
    # 限流为 3 时，理论耗时 ≈ ceil(10/3) * 0.8 ≈ 3.2s

asyncio.run(main())
```

**关键结论**：信号量把"并发度"从"无限"收敛到"可控"，是**背压（backpressure）**思想最轻量的实现。它在爬虫、数据库连接池、SDK 调用限流中无处不在。

---

## 4. 与 `BoundedSemaphore`、`Lock`、`TaskGroup` 的关系

`asyncio` 中同步原语家族包括：`Lock`、`Event`、`Condition`、`Semaphore`、`BoundedSemaphore`。其中：
- **`BoundedSemaphore`**：多了一层保护——如果你 `release()` 次数多于 `acquire()`，它会抛 `ValueError`，帮你及早发现 bug。
- **`Lock`** 就是 `Semaphore(1)` 的特例。
- **Python 3.11+ 的 `asyncio.TaskGroup`** 负责"一起启动 / 一起收尾"，与信号量互补：TaskGroup 管结构，Semaphore 管流量。

```python
import asyncio

async def main():
    # BoundedSemaphore：多 release 会立刻报错，方便定位 bug
    sem = asyncio.BoundedSemaphore(1)
    await sem.acquire()
    try:
        sem.release()
        sem.release()   # 第二次 release 触发 ValueError
    except ValueError as e:
        print("捕获到：", e)

    # TaskGroup + Semaphore 的现代写法（Python 3.11+）
    limiter = asyncio.Semaphore(2)

    async def job(i: int):
        async with limiter:
            await asyncio.sleep(0.3)
            print(f"job {i} done")

    async with asyncio.TaskGroup() as tg:
        for i in range(5):
            tg.create_task(job(i))

asyncio.run(main())
```

**关键结论**：
- 生产代码里推荐用 `BoundedSemaphore`，因为"多释放"几乎总是逻辑 bug 的信号；
- 和 `TaskGroup` 组合，是 Python 3.11+ 最优雅的异步并发模板。

---

## 5. 心智模型小结（记住这五句话）

1. 信号量 = 一个初始值为 N 的计数器 + 一个等待队列。
2. `acquire` 减 1，`release` 加 1；计数为 0 时调用者挂起。
3. `async with sem:` 是最安全的写法，异常也会释放。
4. 信号量解决的是"并发度上限"，不是"数据一致"——后者用 `Lock`。
5. 它只在同一个事件循环内有效，不能跨线程、跨进程共享。

---

## 动手练习

**任务**：写一个"批量图片下载模拟器"。

要求：
1. 定义 30 个假图片 URL（如 `f"https://img.test/{i}.jpg"`）；
2. 用一个全局 `asyncio.Semaphore(5)` 限制同时最多 5 个"下载"；
3. 每个下载任务用 `await asyncio.sleep(random.uniform(0.1, 0.5))` 模拟耗时；
4. 在下载开始时打印 `开始 <url>`，结束时打印 `完成 <url>`；
5. 用 `time.perf_counter()` 统计总耗时，并用注释写清楚：为什么它不是 30 个任务耗时之和，也不是最慢那个任务的耗时；
6. **加分题**：把 `Semaphore` 换成 `BoundedSemaphore`，并故意在代码中多调用一次 `release()`，观察报错；
7. **挑战题**：把并发上限从 5 改成 1、10、30，分别跑一次，画出"并发上限 vs 总耗时"的粗略规律。

提示：使用 `asyncio.gather`（Python < 3.11）或 `asyncio.TaskGroup`（3.11+）组织任务。

```python
import asyncio
import random
import time

async def download_image(url: str, sem: asyncio.Semaphore):
    async with sem:                                  # 进入临界区：最多 N 个并发
        print(f"开始 {url}")
        await asyncio.sleep(random.uniform(0.1, 0.5))  # 模拟网络 I/O
        print(f"完成 {url}")
        return url

async def main():
    urls = [f"https://img.test/{i}.jpg" for i in range(30)]
    sem = asyncio.Semaphore(5)                        # 并发上限 = 5

    start = time.perf_counter()
    results = await asyncio.gather(*(download_image(u, sem) for u in urls))
    elapsed = time.perf_counter() - start

    print(f"\n共处理 {len(results)} 张图片，总耗时 {elapsed:.2f}s")

asyncio.run(main())
```

## py.async.sync_primitives

# asyncio 同步原语（Synchronization Primitives）

## 一句话直觉

当多个协程（coroutine）并发地抢同一份资源时，你需要“红绿灯”来协调它们——`asyncio` 的同步原语就是协程世界里的锁、信号量和事件。

---

## 1. 为什么需要同步原语：并发不等于没有竞争

`asyncio` 用单线程事件循环（event loop）跑并发协程，看起来“同一时刻只有一个协程在跑”，但**协程会在 `await` 处主动让出控制权**。这就意味着：

```python
balance = 100

async def withdraw(amount):
    global balance
    if balance >= amount:   # 检查
        await asyncio.sleep(0.1)  # 这里让出控制权，另一个协程可能也通过了检查
        balance -= amount   # 修改
```

两个协程同时调用 `withdraw(100)`，可能都通过检查，最终余额变成 -100。这就是典型的竞态条件（race condition）。

同步原语就是用来保证**临界区（critical section）**互不干扰的工具。

```python
import asyncio

balance = 100

async def bad_withdraw(amount):
    global balance
    if balance >= amount:
        await asyncio.sleep(0.1)  # 模拟 IO 让出控制权
        balance -= amount

async def main():
    await asyncio.gather(bad_withdraw(100), bad_withdraw(100))
    print(balance)  # 结果常常是 -100，而不是 0

asyncio.run(main())
```

---

## 2. Lock：最基本的互斥锁

`asyncio.Lock` 保证同一时刻只有一个协程进入临界区。用法和 `threading.Lock` 类似，但必须用 `async with`：

```python
import asyncio

balance = 100
lock = asyncio.Lock()

async def good_withdraw(amount):
    global balance
    async with lock:                 # 获取锁；若已被占用，则 await 等待
        if balance >= amount:
            await asyncio.sleep(0.1)
            balance -= amount

async def main():
    await asyncio.gather(good_withdraw(100), good_withdraw(100))
    print(balance)  # 结果一定是 0

asyncio.run(main())
```

关键点：
- `async with lock:` 自动在退出时释放锁，即使抛异常也安全。
- 不要用 `with lock:`，因为 `asyncio.Lock` 的获取是异步操作。

---

## 3. Event：一次性通知，广播唤醒

`asyncio.Event` 是一个布尔标志位加等待队列。常用于“A 就绪后通知 B”的场景，比如初始化完成后放行所有等待者。

```python
import asyncio

async def waiter(name, event):
    print(f"{name} 正在等待信号...")
    await event.wait()          # 阻塞直到 set() 被调用
    print(f"{name} 收到信号，开始工作")

async def main():
    event = asyncio.Event()
    # 启动三个等待者
    tasks = [asyncio.create_task(waiter(f"worker-{i}", event)) for i in range(3)]
    await asyncio.sleep(1)
    print("发出信号！")
    event.set()                  # 唤醒所有等待者
    await asyncio.gather(*tasks)

asyncio.run(main())
```

要点：
- `set()` 后 Event 保持“已触发”状态，之后调用 `wait()` 会立即返回。
- `clear()` 可以复位；`is_set()` 查询状态。
- 如果只需要“一次性”的事件，Event 就够了；如果需要“计数”，用 `Semaphore`。

---

## 4. Semaphore：限制并发数量的闸门

`asyncio.Semaphore(n)` 允许最多 n 个协程同时通过。典型用途：限制对数据库、HTTP 接口的并发访问。

```python
import asyncio

sem = asyncio.Semaphore(3)      # 最多 3 个并发

async def access_resource(i):
    async with sem:
        print(f"task-{i} 进入资源")
        await asyncio.sleep(1)
        print(f"task-{i} 释放资源")

async def main():
    await asyncio.gather(*[access_resource(i) for i in range(10)])
    # 同一时刻最多看到 3 条 "进入资源" 日志

asyncio.run(main())
```

与 `Lock` 的关系：`Lock` 相当于 `Semaphore(1)`，但两者是独立实现。

---

## 5. Condition 与 Queue（进阶速览）

- `asyncio.Condition`：配合 `wait()` / `notify()` 实现“等某个条件成立再继续”，常用于生产者-消费者模式中需要精细化通知的场景。
- `asyncio.Queue`：跨协程的安全队列，是异步任务分发的首选。生产用 `await q.put(x)`，消费用 `await q.get()`。

```python
import asyncio

async def producer(q):
    for i in range(5):
        await q.put(i)
        await asyncio.sleep(0.1)
    await q.put(None)           # 结束哨兵

async def consumer(q):
    while True:
        item = await q.get()
        if item is None:
            break
        print("处理", item)

async def main():
    q = asyncio.Queue()
    await asyncio.gather(producer(q), consumer(q))

asyncio.run(main())
```

工程实践中，Queue 比手动用 Condition 写生产者-消费者更不易出错。

---

## 小结对照表

| 原语 | 语义 | 典型场景 |
|------|------|----------|
| `Lock` | 互斥 | 保护共享变量 |
| `Event` | 一次性广播 | 初始化完成通知 |
| `Semaphore` | 限流 | 控制并发连接数 |
| `Condition` | 条件等待 | 精细同步 |
| `Queue` | 数据传递 | 生产者-消费者 |

```python
import asyncio

# 演示：用 Lock 修复竞态，用 Semaphore 限流，用 Event 广播唤醒

balance = 100
lock = asyncio.Lock()
sem = asyncio.Semaphore(2)
ready = asyncio.Event()

async def withdraw(amount):
    global balance
    async with lock:                    # 互斥保护临界区
        if balance >= amount:
            await asyncio.sleep(0.1)
            balance -= amount

async def limited_worker(i):
    async with sem:                     # 最多 2 个同时运行
        print(f"[worker-{i}] 进入")
        await ready.wait()              # 等待统一信号
        await asyncio.sleep(0.5)
        print(f"[worker-{i}] 完成")

async def main():
    # 1) 并发扣款：正确结果应为 0，不会出现负数
    await asyncio.gather(withdraw(100), withdraw(100))
    print("balance =", balance)

    # 2) 限流 + 事件广播
    workers = [asyncio.create_task(limited_worker(i)) for i in range(5)]
    await asyncio.sleep(1)
    print("发信号，全体放行")
    ready.set()
    await asyncio.gather(*workers)

asyncio.run(main())
```


---

## 本课题目

### single_choice · None



- [A] 限制同时访问某个外部资源的协程数量，例如最多同时发起 5 个网络请求
- [B] 让某个协程等待另一个协程完成后继续执行
- [C] 在多个线程之间安全地共享一个普通整数
- [D] 取消已经启动但尚未完成的协程

**参考答案**：0

**解析**：Semaphore 用于限制同时进入临界区的协程数量，典型场景是限制并发连接数或并发任务数。选项 B 更像 Event 或 await task；选项 C 是线程同步问题，不是 asyncio Semaphore 的主要用途；选项 D 是 Task.cancel。

### single_choice · None



- [A] 0
- [B] 1
- [C] 2
- [D] 取决于事件循环当前是否正在运行

**参考答案**：2

**解析**：Semaphore(value) 的 value 表示初始可用许可数，默认构造时传入 2，因此初始计数为 2。它不依赖事件循环是否正在运行，也不是 0 或 1。

### single_choice · None



- [A] release 必须与 acquire 在同一协程中调用，否则无效
- [B] release 会将内部计数加 1，并且可能唤醒一个等待中的 acquire
- [C] release 只能在计数为 0 时调用，否则抛出异常
- [D] release 是协程方法，必须 await

**参考答案**：1

**解析**：release 是普通方法，不需要 await，会将计数加 1 并可能唤醒等待者。它不要求与 acquire 在同一协程中，也不要求计数为 0 才能调用。

### single_choice · None



- [A] 信号量计数会比预期多 1，从而允许比设定值更多的并发任务
- [B] 程序立即抛出 ValueError
- [C] 信号量会被自动销毁
- [D] 所有等待中的协程会被取消

**参考答案**：0

**解析**：release 不要求与 acquire 配对检查，多调用会使计数上溢，从而实际允许的并发数超过初始设定。它不会自动抛 ValueError、销毁信号量或取消等待者。

### single_choice · None



- [A] sem = asyncio.Semaphore(5)
  async def worker():
      sem.acquire()
      try:
          await do_work()
      finally:
          sem.release()
- [B] sem = asyncio.Semaphore(5)
  async def worker():
      await sem.acquire()
      try:
          await do_work()
      finally:
          sem.release()
- [C] sem = asyncio.Semaphore(5)
  async def worker():
      async with sem:
          await do_work()
      sem.release()
- [D] sem = asyncio.Semaphore(5)
  async def worker():
      sem.acquire()
      await do_work()
      sem.release()

**参考答案**：1

**解析**：正确做法是 await sem.acquire()，并在 try/finally 中 release。选项 A 和 D 缺少 await；选项 C 使用 async with 后额外 release 会导致计数上溢。

### single_choice · None



- [A] BoundedSemaphore 的 release 会检查计数是否超过初始值，超过时抛出 ValueError
- [B] BoundedSemaphore 不能用于协程，只能用于线程
- [C] Semaphore 的 release 也会检查上界并抛出 ValueError
- [D] BoundedSemaphore 的 acquire 不需要 await

**参考答案**：0

**解析**：BoundedSemaphore 在 release 时若计数将超过初始值会抛出 ValueError，有助于发现 release 次数过多的问题。普通 Semaphore 不检查上界。二者都用于协程，acquire 都需要 await。

### single_choice · None



- [A] Lock 可以允许多个协程同时进入，Semaphore 只能允许一个
- [B] Semaphore 可以设置大于 1 的初始许可数，从而允许多个协程同时进入；Lock 本质上只允许一个协程持有
- [C] Lock 只能用于多线程，Semaphore 只能用于多进程
- [D] Semaphore 不能被 await，Lock 可以

**参考答案**：1

**解析**：asyncio.Lock 是互斥锁，同一时刻只允许一个协程持有；Semaphore 可以设置多个许可，允许多个协程同时进入。二者都用于协程，acquire 都是 awaitable。

### single_choice · None



- [A] asyncio.Event
- [B] asyncio.Condition
- [C] asyncio.Semaphore(10)
- [D] asyncio.Queue()

**参考答案**：2

**解析**：Semaphore(10) 直接表示最多 10 个许可，适合限制并发任务数。Event 用于通知，Condition 用于条件等待，Queue 用于生产者消费者模式，虽然也能间接限流但不如 Semaphore 直接。

### single_choice · None



- [A] 等待者总是按后进先出的顺序被唤醒
- [B] 等待者按先进先出的顺序等待唤醒，但不应依赖过于严格的顺序保证
- [C] 等待者会被随机唤醒，没有队列
- [D] 只有第一个等待者会被唤醒，其他等待者永远不会被唤醒

**参考答案**：1

**解析**：asyncio 内部通常维护等待者队列，按先进先出唤醒，但实现细节可能变化，业务代码不应强依赖严格顺序。不是后进先出、随机或只唤醒第一个。

### single_choice · None



- [A] 进入时自动 await acquire，退出时自动 release，即使发生异常也会释放
- [B] 把 sem 的初始计数临时改为 3
- [C] 让 do_work 变成同步函数
- [D] 取消所有其他正在等待 sem 的协程

**参考答案**：0

**解析**：asyncio.Semaphore 支持异步上下文管理器协议，async with 会在进入时 await acquire，退出时 release，并在异常时保证释放。它不会修改初始计数、改变 do_work 类型或取消其他协程。

### single_choice · None



- [A] 立即获得许可并继续执行
- [B] 一直等待，因为许可没有被释放
- [C] 抛出 RuntimeError 并结束
- [D] 自动获得一个新的许可，计数变为 2

**参考答案**：1

**解析**：许可被第一个协程消耗且未释放，计数保持为 0，第二个协程会一直等待。它不会立即获得许可、抛错或自动增加计数。

### single_choice · None



- [A] 使用 async with sem 包裹临界区
- [B] 在 await sem.acquire() 之后、release 之前，代码抛出异常且没有 try/finally
- [C] 在 release 之后再次调用 acquire
- [D] 把 Semaphore 对象作为参数传给多个协程

**参考答案**：1

**解析**：acquire 之后若发生异常但没有释放，许可就会泄漏。async with 会保证释放；release 后再 acquire 是正常使用；跨协程传递 Semaphore 对象也是常见且正确的做法。

### single_choice · None



- [A] 它是普通同步方法，调用后立即返回 True 或 False
- [B] 它是一个 awaitable，计数大于 0 时会减少计数并继续，否则会挂起当前协程等待
- [C] 它只能在创建 Semaphore 的同一个协程中调用
- [D] 它会阻塞整个事件循环直到获得许可

**参考答案**：1

**解析**：asyncio.Semaphore.acquire 是一个协程方法，需要 await。计数可用时立即减少并返回；不可用时当前协程被挂起，而不是阻塞整个事件循环。它不要求必须在创建它的协程中调用。

### single_choice · None



- [A] 计数可以为负数，表示欠了多少许可
- [B] 计数在 acquire 成功时减 1，release 时加 1；等待中的 acquire 不会减少计数
- [C] 计数只能等于 0 或初始值，不能是中间值
- [D] 计数由事件循环自动维护，调用者无法通过 acquire/release 影响

**参考答案**：1

**解析**：成功 acquire 使计数减 1，release 使计数加 1；等待中的 acquire 尚未消耗许可，因此不减少计数。计数通常不会变为负数，也可以处于 0 和初始值之间的中间值，并且正是由 acquire/release 改变的。

### single_choice · None



- [A] 0
- [B] 1
- [C] 2
- [D] 取决于 with 语句块中是否发生异常

**参考答案**：1

**解析**：acquire 使计数从 1 减到 0，release 使计数加 1，因此恢复为 1。release 本身不会改变为其他值；异常处理若使用 try/finally 也通常会 release，但题中已明确执行 release。

### single_choice · None



- [A] 表示永远无法获得许可，因此 acquire 会立即抛出异常
- [B] 作为初始不可用的门闩，等待其他协程 release 后再放行等待者
- [C] 表示无限制并发，等同于不加限制
- [D] 表示信号量已损坏，不应再使用

**参考答案**：1

**解析**：Semaphore(0) 初始没有可用许可，await acquire 会挂起等待，直到其他协程调用 release 使计数增加。它不会立即抛异常，也不代表无限制并发或损坏。

### single_choice · None



- [A] 所有等待者会同时被唤醒并获得许可
- [B] 唤醒其中一个等待者，使其获得许可并继续执行
- [C] 不会唤醒任何等待者，只是增加内部计数
- [D] 唤醒顺序一定与协程创建顺序相反

**参考答案**：1

**解析**：release 增加计数，并唤醒一个等待中的 acquire 调用者，使其获得许可继续执行；不会一次唤醒全部。唤醒顺序通常按等待顺序，但不应依赖为与创建顺序相反。

### single_choice · None



- [A] 两者完全等价，可以互换使用
- [B] asyncio.Semaphore 用于协程间同步，acquire 需要 await；threading.Semaphore 用于线程间同步，acquire 是阻塞调用
- [C] asyncio.Semaphore 只能用于多线程，threading.Semaphore 只能用于多进程
- [D] threading.Semaphore 也必须在 async 函数中使用 await

**参考答案**：1

**解析**：asyncio.Semaphore 是协程同步原语，acquire 是 awaitable；threading.Semaphore 是线程同步原语，acquire 会阻塞当前线程。二者不能直接互换，也不存在只能用于多线程或仅能 await 的限定。

### single_choice · None



- [A] 因为 acquire 必须在 release 之前调用，否则会报语法错误
- [B] 为了确保即使临界区代码抛出异常，也能 release 许可，避免信号量计数永久减少
- [C] 因为 async with 会自动把信号量计数重置为初始值
- [D] 因为 release 只能在异常处理块中调用

**参考答案**：1

**解析**：如果在获得许可后进入临界区时发生异常但没有 release，许可会泄漏，其他协程可能永远等待。try/finally 或 async with 能保证释放。async with 不会自动重置为初始值，release 也不要求必须在异常块中调用。

### single_choice · None



- [A] Semaphore 不能在循环中使用
- [B] acquire 是协程方法，这里没有 await；而且 try/finally 缺失，异常时会泄漏许可
- [C] release 必须传入参数 i
- [D] do_work 不能是协程函数

**参考答案**：1

**解析**：asyncio.Semaphore.acquire 需要 await，否则不会真正等待许可，还可能产生警告。同时缺少异常安全的 release。Semaphore 可以在循环中使用，release 不需要参数，do_work 作为协程函数也没有问题。

### single_choice · None



- [A] 立即获得许可并继续执行
- [B] 被挂起，等待其他协程 release
- [C] 抛出 RuntimeError
- [D] 自动将信号量计数增加到 3

**参考答案**：1

**解析**：初始计数 2，A 和 B 各消耗 1，计数变为 0；C 再 await acquire 时会挂起等待 release。它不会立即获得许可、抛错或自动增加计数。

### single_choice · None



- [A] asyncio.Event
- [B] asyncio.Lock
- [C] asyncio.Queue
- [D] asyncio.Semaphore(0)

**参考答案**：1

**解析**：asyncio.Lock 用于保证同一时刻只有一个协程进入临界区，是最直接的互斥原语。Event 用于通知，Queue 用于生产者-消费者解耦，Semaphore(0) 初始为 0 会一直阻塞。

### single_choice · None



- [A] acquire 是同步方法，不会阻塞事件循环
- [B] acquire 是协程，必须 await，未获取时会挂起当前协程而不阻塞事件循环
- [C] release 必须由最先获取锁的协程调用，否则抛异常
- [D] Lock 不支持 async with 语法

**参考答案**：1

**解析**：asyncio.Lock.acquire() 是协程函数，需 await。未获取到锁时挂起当前协程，让出事件循环给其他任务，而不是阻塞线程。release 不强制必须是获取者调用（但逻辑上应成对），Lock 支持 async with。

### multi_choice · None



- [A] asyncio.Lock
- [B] asyncio.Semaphore
- [C] asyncio.Condition
- [D] asyncio.RLock
- [E] asyncio.Event

**参考答案**：[0, 1, 2, 4]

**解析**：asyncio 提供 Lock、Semaphore、BoundedSemaphore、Event、Condition、Barrier（3.11+）等。没有 asyncio.RLock；RLock 是 threading 的。

### multi_choice · None



- [A] Semaphore 可以超过初始值释放而不会报错
- [B] BoundedSemaphore 释放超过初始值会抛 ValueError
- [C] 两者都可用于限制并发数
- [D] Semaphore 只能在同步函数中使用

**参考答案**：[0, 1, 2]

**解析**：Semaphore 允许 release 使计数超过初始值（不报错但通常是 bug）。BoundedSemaphore 会检查上界并抛 ValueError，用来捕获误用。两者都是协程原语，不能直接在同步函数中 await。

### multi_choice · None



- [A] 让一个协程等待某个启动信号后再继续
- [B] 在所有初始化完成前阻塞多个消费者协程
- [C] 替代互斥锁保护临界区
- [D] 实现一次性广播通知

**参考答案**：[0, 1, 3]

**解析**：Event 用于「等待/通知」语义：等待信号、等待初始化完成、一次性广播。保护临界区互斥应该用 Lock，Event 不具备互斥语义。

### multi_choice · None



- [A] wait() 必须在已经持有 condition 的情况下调用
- [B] wait() 会释放内部锁，被唤醒后重新获取锁
- [C] notify() 必须在持有 condition 的情况下调用
- [D] notify_all() 会唤醒所有等待者，它们依次竞争锁

**参考答案**：[0, 1, 2, 3]

**解析**：Condition.wait/notify 都要求调用者持有底层锁。wait 释放锁并在被唤醒后重新获取。notify 唤醒一个等待者，notify_all 唤醒全部等待者，它们醒来后需要重新竞争锁。

### fill_blank · None



**参考答案**：["Semaphore", "asyncio.Semaphore"]

**解析**：Semaphore 通过计数限制同时进入的协程数量，是最常见的并发限制手段。

### fill_blank · None



**参考答案**：["Condition", "asyncio.Condition"]

**解析**：Condition 内部持有锁，允许等待条件并在条件满足时被通知，是等待/通知语义的经典实现。

### fill_blank · None



**参考答案**：["Lock", "asyncio.Lock"]

**解析**：Lock 的互斥语义正好保证同一时刻只有一个协程在临界区。

### code_reading · None



**参考答案**：在 tmp = counter 与 counter = tmp + 1 之间的 await asyncio.sleep(0) 会让出事件循环，另一个协程可能读到过期的 counter，导致更新丢失（竞态）。修复：用 asyncio.Lock 包住整个读-改-写序列（async with lock: ...），避免中间被其他协程插入。

**解析**：await 点是协程切换点，读-改-写不是原子操作。用锁即可恢复原子性；移除 sleep 或改成同步循环也能规避，但正确做法是加同步原语。

### code_reading · None



**参考答案**：会永远卡住。Queue.get() 在队列为空时会挂起消费者协程，主协程又 await task 等待它结束，而没有任何生产者调用 put，因此 consumer 永远阻塞、main 也永远等待，形成死锁式挂起。修复：加入生产者 put 数据，或在合适时取消该任务并处理 CancelledError。

**解析**：Queue 的 get 在空队列时挂起是设计行为，但如果没有任何生产者且调用方又同步等待任务完成，就会永久挂起。同步原语的挂起需要有人推进状态。

### scenario · None



**解析**：用 Semaphore(5) 限制并发数；用 asyncio.gather(..., return_exceptions=True) 并发执行并收集结果、避免单点失败拖垮整体；如果多个协程需要更新同一配置字典，用 Lock 保护写操作；用 Event 作为「配置就绪」信号，让其他等待启动的协程在事件被 set 后再继续。

### single_choice · None



- [A] 最多允许 3 个协程同时进入受保护的代码段
- [B] 第 3 个到达的协程才能进入临界区
- [C] 每次进入需要等待 3 秒
- [D] 必须同时启动 3 个协程，否则报错

**参考答案**：0

**解析**：Semaphore(3) 初始化计数为 3，最多允许 3 个协程同时持有，常用于限制并发数量。它不涉及时间延迟，也不要求恰好 3 个协程。

### single_choice · None



- [A] 立即返回 True
- [B] 抛出 RuntimeError
- [C] 挂起当前协程直到事件被 set
- [D] 返回 None 并继续执行

**参考答案**：2

**解析**：Event 初始为未设置状态，wait() 会挂起调用者，直到其他协程调用 set()。这常用于「等待某个条件发生」的同步场景。

### single_choice · None



- [A] 可以跨进程使用
- [B] 支持在持有锁的基础上等待某个条件并释放锁，条件满足后重新获取锁
- [C] 可以限制并发数量
- [D] 可以在同步函数中直接使用

**参考答案**：1

**解析**：Condition 内部包含一个锁，wait() 会在等待时释放锁，被 notify 唤醒后重新获取锁。这使它能表达「等待条件成立」的语义，Lock 只能表达互斥。

### single_choice · None



- [A] start 1 / start 2 / end 1 / end 2
- [B] start 1 / end 1 / start 2 / end 2（或先 2 后 1，但不会交错）
- [C] start 2 / end 1 / start 1 / end 2
- [D] end 1 / end 2 / start 1 / start 2

**参考答案**：1

**解析**：Lock 保证临界区互斥，因此一个 worker 的 start/end 会连续出现，另一个才进入。两个 worker 谁先获取锁取决于调度顺序，但不会出现 start/start/end/end 的交错。

### single_choice · None



- [A] asyncio 版本使用线程阻塞等待
- [B] asyncio 版本通过挂起协程让出事件循环，不阻塞线程
- [C] 两者完全相同，可以互换使用
- [D] asyncio 版本只能用在多线程环境

**参考答案**：1

**解析**：asyncio 原语是协程友好的：等待时会 await，让出事件循环以便其他任务运行。threading 原语会真正阻塞操作系统线程，混用会卡死事件循环。

### single_choice · None



- [A] 一定正确，因为协程是单线程的
- [B] 可能出现竞态，因为 await 处会让出控制权
- [C] 一定报错
- [D] asyncio 禁止共享变量

**参考答案**：1

**解析**：asyncio 单线程并不意味着自动安全：在 await 点协程可能被挂起，其他协程可能读到中间状态，从而产生竞态。需要 Lock 保护读-改-写序列。

### single_choice · None



- [A] 限制同时运行的任务数
- [B] 在生产者和消费者之间缓冲数据并同步它们的进度
- [C] 存储协程对象以供调度
- [D] 替代 asyncio.gather

**参考答案**：1

**解析**：asyncio.Queue 提供 put/get 的异步接口，当队列满或空时会挂起相应协程，天然用于生产者-消费者解耦。限制并发通常用 Semaphore。

### single_choice · None



- [A] 可以用 async with 语法管理获取和释放
- [B] 同一个协程可以多次 acquire 而不释放导致死锁
- [C] 它保证同一时刻只有一个协程在临界区内
- [D] 它必须绑定到特定的事件循环，可以在任意线程的任意循环中直接使用

**参考答案**：3

**解析**：asyncio 的同步原语与创建它们时的事件循环绑定（新版会在首次使用时绑定到运行中的循环），跨事件循环使用通常是不安全或不被支持的。A、B、C 均正确。
