# s3u2l3 用线程池把并发跑起来 / 让 Python 真正“同时跑”起来的第一把钥匙

> 来源 `content/lessons/s3u2l3.json`

## py.thread.threadpool

# py.thread.threadpool：用线程池把并发跑起来

> 一句话直觉：当你有成百上千个「等 IO、等网络、等磁盘」的小任务时，别一个个排队跑，也别手忙脚乱开一万个线程，用线程池（Thread Pool）让一小队线程帮你复用干活，代码短、性能稳、还能防止线程爆炸。

---

## 1. 为什么需要线程池？从「串行」到「并发」

**线程（Thread）** 是操作系统能调度的最小执行单元；**并发（Concurrency）** 指多个任务在时间上重叠推进。  
Python 里启动一个线程很简单：`threading.Thread(target=fn).start()`。但手写线程有两个致命问题：

1. **创建/销毁开销大**：每来一个任务就 new 一个线程，上下文切换成本高。
2. **数量不可控**：任务一多就 OOM（Out Of Memory），甚至把系统拖垮。

**线程池**的核心思想是复用：预先启动 N 个线程，把任务丢进一个队列（Queue），线程从队列里取任务执行。Python 标准库的 `concurrent.futures.ThreadPoolExecutor` 就是这个思想的官方实现。

```python
# 演示：手动开 3 个线程 vs 线程池，观察线程复用
import threading, time
from concurrent.futures import ThreadPoolExecutor

def job(n):
    time.sleep(0.1)
    return n * n

# 手动方式：5 个任务 = 5 个新线程
for i in range(5):
    threading.Thread(target=job, args=(i,)).start()

# 线程池方式：只开 3 个线程，循环处理 5 个任务
with ThreadPoolExecutor(max_workers=3) as pool:
    results = list(pool.map(job, range(5)))
print(results)  # [0, 1, 4, 9, 16]
```

---

## 2. 两种提交任务的方式：`submit` 与 `map`

`ThreadPoolExecutor` 提供两个主力 API：

- `executor.submit(fn, *args)` → 返回一个 **Future（未来对象）**，可以之后 `.result()` 拿结果，或者 `.add_done_callback()` 挂回调。
- `executor.map(fn, iterable)` → 类似内置 `map`，按输入顺序返回迭代器，**结果顺序与输入顺序一致**，内部并发执行。

`Future` 是「占位符」：提交那一刻可能还没执行完，调用 `.result()` 会**阻塞**当前线程直到有结果（或抛异常）。`map` 则是把「提交 + 收集」打包成一步，适合「一批独立任务，顺序返回结果」的场景。

```python
from concurrent.futures import ThreadPoolExecutor

def fetch(url):
    return f"got:{url}"

with ThreadPoolExecutor(max_workers=4) as pool:
    # map：批量、按输入顺序返回结果
    for r in pool.map(fetch, ["a", "b", "c"]):
        print(r)

    # submit：单个提交，返回 Future
    fut = pool.submit(fetch, "d")
    print(fut.result())  # 阻塞直到拿到结果
```

---

## 3. GIL 与线程池：为什么「CPU 密集」不是它的菜

**GIL（Global Interpreter Lock，全局解释器锁）** 保证同一时刻只有一个线程执行 Python 字节码。这意味着：

- **IO 密集型任务**（网络、文件、数据库）→ 线程在等待时释放 GIL，其他线程可以跑，**线程池有效**。
- **CPU 密集型任务**（大量计算）→ 线程互相抢 GIL，反而可能比单线程还慢。CPU 密集应改用 `ProcessPoolExecutor`（进程池）。

所以选线程池的前提是：**任务是等待型，不是计算型**。

```python
import time
from concurrent.futures import ThreadPoolExecutor

def io_task(i):
    time.sleep(0.5)   # 模拟等待，sleep 会释放 GIL
    return i

start = time.time()
with ThreadPoolExecutor(max_workers=5) as pool:
    list(pool.map(io_task, range(5)))
print(f"5 个 0.5s 的 IO 任务耗时约 {time.time()-start:.2f}s")  # ≈0.5s，而非 2.5s
```

---

## 4. 线程安全：共享变量要加锁

线程池里多个线程共用同一份内存，一旦同时**读改写**共享数据就会出问题。用 **锁（Lock）** 保护临界区（Critical Section）。Python 里推荐用 `with lock:` 上下文管理器，保证异常也能释放锁。

想象一个计数器：不加锁时 `counter += 1` 实际是「读-加-写」三步，多线程交错就会丢更新。

```python
import threading
from concurrent.futures import ThreadPoolExecutor

counter = 0
lock = threading.Lock()

def safe_inc(_):
    global counter
    with lock:              # 同一时刻只有一个线程能进入
        counter += 1

with ThreadPoolExecutor(max_workers=10) as pool:
    list(pool.map(safe_inc, range(1000)))
print(counter)  # 稳定输出 1000
```

---

## 5. 工程实践：异常处理、超时与关闭

真实代码要考虑三件事：

1. **异常传播**：任务函数抛异常时，`Future.result()` 会重新抛出；`map` 则在迭代到该位置时抛。用 `try/except` 包好。
2. **超时**：`future.result(timeout=秒)` 防止单个任务卡死；`pool.map` 也支持 `timeout`。
3. **关闭**：用 `with ThreadPoolExecutor(...) as pool:` 会自动 `shutdown(wait=True)`，等待所有任务结束；显式调用时可用 `shutdown(wait=False, cancel_futures=True)` 取消未开始的任务。

```python
from concurrent.futures import ThreadPoolExecutor, TimeoutError

def may_fail(x):
    if x == 2:
        raise ValueError("boom")
    return x * 10

with ThreadPoolExecutor(max_workers=3) as pool:
    futs = [pool.submit(may_fail, i) for i in range(4)]
    for i, f in enumerate(futs):
        try:
            print(i, f.result(timeout=2))
        except ValueError as e:
            print(i, "任务出错:", e)
        except TimeoutError:
            print(i, "超时")
```

---

## 动手练习

**任务：用线程池并发下载并统计 8 个网页的总字节数。**

要求：
1. 用 `ThreadPoolExecutor(max_workers=4)`。
2. 每个任务是 `urllib.request.urlopen(url).read()` 的字节长度。
3. 用 `submit` + `as_completed` 收集已完成结果（真正的「谁先好谁先算」）。
4. 任意任务出错要捕获并打印，不能中断整体。
5. 打印「每个 URL 的字节数」和「总耗时/总字节数」。

提示：允许在无网络环境下把 `urlopen` 换成 `time.sleep(随机秒)` + `random.randint(1000, 5000)` 模拟返回长度，先打通逻辑再加网络。

对照 API：
```python
from concurrent.futures import ThreadPoolExecutor, as_completed
with ThreadPoolExecutor(max_workers=4) as pool:
    futures = {pool.submit(fn, u): u for u in urls}
    for fut in as_completed(futures):
        url = futures[fut]
        try:
            print(url, fut.result())
        except Exception as e:
            print(url, "失败:", e)
```

```python
# 可运行示例：线程池下载（无网络时用 sleep 模拟）
import time, random
from concurrent.futures import ThreadPoolExecutor, as_completed

URLS = [f"https://example.com/{i}" for i in range(8)]

def fake_fetch(url: str) -> int:
    """模拟网络 IO：随机等待后返回字节数。"""
    time.sleep(random.uniform(0.2, 0.8))
    if random.random() < 0.15:
        raise RuntimeError(f"网络抖动: {url}")
    return random.randint(1000, 5000)

def main():
    start = time.time()
    total = 0
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(fake_fetch, u): u for u in URLS}
        for fut in as_completed(futures):
            url = futures[fut]
            try:
                size = fut.result(timeout=5)
                total += size
                print(f"OK   {url} -> {size} bytes")
            except Exception as e:
                print(f"FAIL {url} -> {e}")
    print(f"\n总字节数: {total}, 总耗时: {time.time()-start:.2f}s")

if __name__ == "__main__":
    main()
```

## py.thread.concurrent_futures

# py.thread.concurrent_futures：让 Python 真正“同时跑”起来的第一把钥匙

> 一句话直觉：当你要同时下载 100 张图片、并发调用 20 个 API 时，难道要手动创建 100 个线程、维护一个队列去收集结果吗？`concurrent.futures` 就是标准库给你的一层“线程池 + 任务提交 + 结果收集”的高级封装，让你用 5 行代码写出并发程序，而不是 50 行。

---

## 1. 为什么需要它：从“单线程等待”到“并发执行”

普通 Python 代码默认是**同步（synchronous）**的：一行执行完才执行下一行。如果某一行要等网络 2 秒，程序就干等 2 秒。

```python
import time

def slow_task(n):
    time.sleep(1)   # 模拟 I/O 等待（比如下载）
    return n * n

# 同步版本：3 个任务要 3 秒
start = time.time()
results = [slow_task(i) for i in range(3)]
print('同步耗时:', round(time.time() - start, 2), '秒')
print('结果:', results)
```

`concurrent.futures` 让你把这些任务**同时提交（submit）**到一个**线程池（ThreadPoolExecutor）**里，由池中的工作线程并行执行，主线程边等边收集结果。**I/O 密集型（I/O-bound）**任务（网络、文件、数据库）能因此提速数倍。

---

## 2. 核心对象：Executor 和 Future

`concurrent.futures` 的两个核心概念：

- **Executor（执行器）**：管理线程/进程池的对象，最常用的是 `ThreadPoolExecutor`。
- **Future（未来对象）**：提交任务后立即返回的“占位符”，代表“未来某个时刻会得到的结果”。它有三个关键方法：
  - `.result()`：阻塞直到结果就绪并返回；
  - `.done()`：任务是否已完成；
  - `.exception()`：任务抛出的异常。

```python
from concurrent.futures import ThreadPoolExecutor
import time

def slow_task(n):
    time.sleep(1)
    return n * n

# 创建一个最多 3 个工作线程的池
with ThreadPoolExecutor(max_workers=3) as executor:
    # submit 立即返回 Future，不会阻塞
    futures = [executor.submit(slow_task, i) for i in range(3)]
    # 收集结果：.result() 会等待对应任务完成
    results = [f.result() for f in futures]

print('结果:', results)   # 三个任务几乎同时跑完
```

注意最后的 `with` 语句：**退出时会自动调用 `executor.shutdown(wait=True)`**，等待所有线程结束，避免“程序退出时线程被杀”。这是必须养成的习惯。

---

## 3. map：更简洁的批量提交方式

如果你有一批相同的入参要跑同一个函数，用 `executor.map()` 比手写 `submit` 更简洁。它**按提交顺序**返回结果（内部也是通过 Future 实现）。

```python
from concurrent.futures import ThreadPoolExecutor

def square(n):
    return n * n

with ThreadPoolExecutor(max_workers=4) as executor:
    # map 返回一个迭代器，按输入顺序产出结果
    results = list(executor.map(square, range(10)))

print(results)   # [0, 1, 4, 9, 16, 25, 36, 49, 64, 81]
```

⚠️ 小陷阱：`map` 的结果**顺序固定**，但**完成顺序不固定**；如果你更关心“谁先完成先处理”，需要改用 `as_completed`（见下一节）。

---

## 4. as_completed：谁先跑完谁先处理

爬虫、批量请求这类场景，任务耗时差异很大。等你用 `f.result()` 按顺序收集，会被最慢的那一个拖住。`as_completed` 会**按完成顺序**逐个 yield 出 Future。

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

def task(name, delay):
    time.sleep(delay)
    return f'{name} 完成（耗时 {delay}s）'

with ThreadPoolExecutor(max_workers=3) as executor:
    futures = [
        executor.submit(task, 'A', 2),
        executor.submit(task, 'B', 1),
        executor.submit(task, 'C', 3),
    ]
    for f in as_completed(futures):
        print(f.result())   # 输出顺序：B -> A -> C
```

这个模式最大的价值是：**你可以在每个任务完成的瞬间就处理它的结果**，而不是傻等所有任务结束。

---

## 5. 工程要点：异常、超时、GIL 与选择

### 5.1 异常捕获

`.result()` 抛出的是任务内部异常本身，捕获方式很自然：

```python
from concurrent.futures import ThreadPoolExecutor

def risky(x):
    if x == 0:
        raise ValueError('不能除以 0')
    return 10 / x

with ThreadPoolExecutor() as executor:
    f = executor.submit(risky, 0)
    try:
        f.result()
    except ValueError as e:
        print('捕获到:', e)
```

### 5.2 超时控制

`.result(timeout=...)` 和 `as_completed(..., timeout=...)` 都支持超时，抛 `TimeoutError`：

```python
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import time

def sleepy():
    time.sleep(10)
    return 'done'

with ThreadPoolExecutor() as executor:
    f = executor.submit(sleepy)
    try:
        f.result(timeout=1)
    except TimeoutError:
        print('任务超时')
```

### 5.3 关于 GIL（Global Interpreter Lock，全局解释器锁）

这是初学者最容易踩的坑：

- **I/O 密集型任务**：`ThreadPoolExecutor` **有效**。线程等待 I/O 时会释放 GIL，其他线程能跑。
- **CPU 密集型任务**：`ThreadPoolExecutor` **几乎无效甚至更慢**。因为大量计算时间都握着 GIL，同一时刻只有一个线程真正在跑 Python 字节码。此时应该用 `ProcessPoolExecutor`。

```python
from concurrent.futures import ProcessPoolExecutor

def cpu_heavy(n):
    return sum(i * i for i in range(n))

if __name__ == '__main__':   # Windows/macOS 上用进程池必须放在 main 保护里
    with ProcessPoolExecutor() as executor:
        results = list(executor.map(cpu_heavy, [10**6] * 4))
    print(results)
```

### 5.4 选择决策表

| 场景 | 推荐 |
|---|---|
| 网络请求、文件读写、数据库查询 | `ThreadPoolExecutor` |
| 纯 CPU 计算、图像处理、数值计算 | `ProcessPoolExecutor` |
| 需要控制并发度上限 | `max_workers=N` |
| 需要按完成顺序处理 | `as_completed` |
| 需要按提交顺序处理 | `map` 或 `submit` + `[f.result() for f in futures]` |

---

## 结语

`concurrent.futures` 用一套统一 API（`submit` / `map` / `as_completed` + `Future`）把“线程池、任务队列、结果收集、异常传播”全都封装好了。记住三条铁律：

1. **永远用 `with` 管理 Executor**，确保线程池被正确关闭；
2. **I/O 用线程，CPU 用进程**；
3. **`as_completed` 处理“先完成先处理”，`map` 处理“按顺序拿结果”**。

下面是一个综合示例，把这堂课的要点串起来。

```python
import time
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError

def fetch(url):
    # 用 sleep 模拟网络 I/O，不同 URL 耗时不同
    delay = {'a': 0.3, 'b': 0.1, 'c': 0.5, 'd': 0.2}[url]
    time.sleep(delay)
    if url == 'c':
        raise RuntimeError(f'{url} 请求失败')
    return f'{url} 成功（{delay}s）'

urls = ['a', 'b', 'c', 'd']
start = time.time()

with ThreadPoolExecutor(max_workers=3) as executor:
    # 逐个提交，得到 Future 列表
    futures = {executor.submit(fetch, u): u for u in urls}

    # 谁先完成先处理
    for f in as_completed(futures, timeout=2):
        url = futures[f]
        try:
            print(f.result())
        except Exception as e:
            print(f'[{url}] 出错:', e)

print(f'总耗时: {time.time() - start:.2f}s （同步约需 1.1s）')
```


---

## 本课题目

### single_choice · None



- [A] 为每个任务手动创建一个 threading.Thread 并立即 start 和 join
- [B] 把大量短小任务提交给线程池，由池中固定数量的工作线程复用执行
- [C] 每次提交任务前都新建一个线程池对象，提交后立即关闭
- [D] 只用主线程串行执行任务，避免创建任何线程

**参考答案**：1

**解析**：线程池的核心价值是复用固定数量的工作线程来执行大量短小任务，避免频繁创建和销毁线程带来的开销。A 是手动建线程，C 会不断创建销毁池，D 完全没有使用并发，均不符合线程池的设计初衷。

### single_choice · None



- [A] submit 会阻塞直到任务执行完成并返回结果
- [B] submit 返回一个 Future 对象，可用于查询状态或获取结果
- [C] submit 提交的任务会立即在当前线程中同步执行
- [D] submit 只能提交无参数函数，无法传入参数

**参考答案**：1

**解析**：submit 是非阻塞的，它把任务交给线程池后立即返回一个 Future 对象，通过该对象可以查询任务状态、取消任务或用 result() 获取返回值。A 错在混淆了阻塞行为，C 错在任务由工作线程异步执行，D 错在 submit 支持通过位置和关键字参数传参。

### single_choice · None



- [A] 该异常被忽略，继续产出后续任务的结果
- [B] 在迭代到该任务对应的结果时抛出该异常
- [C] 所有已完成任务的结果都被丢弃
- [D] map 会立即返回一个空列表

**参考答案**：1

**解析**：map 返回的迭代器在推进到抛出异常的那个任务的结果位置时，会把该异常重新抛出。A 错在不会静默忽略，C 错在不会丢弃已完成结果，D 与 map 行为无关。

### single_choice · None



- [A] 每个提交的任务都会创建一个全新线程，任务结束后线程销毁
- [B] 工作线程在执行完一个任务后会回到池中等待下一个任务
- [C] 线程池中的线程一旦创建就永不结束，即使池已关闭
- [D] 线程复用只对 CPU 密集型任务有效

**参考答案**：1

**解析**：线程池的工作线程执行完一个任务后会返回池中空闲队列，等待领取下一个任务，这正是复用的含义。A 描述的是手动建线程，C 错在线程池关闭后线程会退出，D 与任务类型无关。

### single_choice · None



- [A] 不会出现任何问题，因为 GIL 保证了复合操作的原子性
- [B] 可能出现丢失更新，需要使用锁保护该复合操作
- [C] 线程池会自动为该操作加锁
- [D] count += 1 会自动被转换为原子操作

**参考答案**：1

**解析**：count += 1 不是原子操作，GIL 并不保证这种读-改-写复合操作的原子性，多个线程交错执行可能丢失更新，需要用 Lock 等同步机制保护。A、C、D 都错误理解了 GIL 与线程池的作用范围。

### single_choice · None



- [A] 有了线程池就能绕过 GIL，使纯 Python 计算真正并行
- [B] GIL 仍然存在，但 I/O 等待期间线程会释放 GIL，因此线程池对 I/O 密集型任务有效
- [C] 线程池中的线程不参与 GIL 的竞争
- [D] 使用线程池后 GIL 会被自动禁用

**参考答案**：1

**解析**：GIL 依然存在，线程池并不会绕过它。对于 I/O 密集型任务，线程在等待 I/O 时会释放 GIL，其他线程得以运行，因此线程池仍然有效；纯 Python 计算则难以真正并行。A、C、D 均与事实不符。

### single_choice · None



- [A] 只能通过继承 ThreadPoolExecutor 并重写 run 方法来使用
- [B] 可以直接实例化 ThreadPoolExecutor，并通过 submit 或 map 提交任务
- [C] 必须通过 concurrent.futures 模块级函数 thread_pool() 创建
- [D] 必须与 asyncio 事件循环一起使用，否则无法工作

**参考答案**：1

**解析**：ThreadPoolExecutor 可直接实例化，通过 submit 提交单个任务或 map 批量提交。A 描述的是 Thread 子类化，C 中不存在这样的模块级函数，D 错在它与 asyncio 不是绑定关系。

### single_choice · None



- [A] 对每个 Future 依次调用 result()，或使用 wait 等待整组 Future
- [B] 调用 threading.sleep 足够长时间
- [C] 在每个任务末尾调用 sys.exit
- [D] 反复轮询线程池的内部变量直到它变为空

**参考答案**：0

**解析**：对每个 Future 调用 result() 会阻塞直到该任务完成，从而保证全部完成；也可以使用 concurrent.futures.wait 等待一组 Future。B 依赖时间猜测不可靠，C 会终止程序，D 依赖内部实现且不可取。

### single_choice · None



- [A] 任务一定严格按照提交顺序开始执行
- [B] 任务一定严格按照提交顺序完成
- [C] 任务的开始和完成顺序可能因线程调度而与提交顺序不同
- [D] 线程池会按任务大小排序后再执行

**参考答案**：2

**解析**：线程池只是把任务放入队列，由空闲线程领取，具体开始和完成顺序受调度影响，可能与提交顺序不同。A、B 把顺序绝对化，D 描述的行为并不存在。

### single_choice · None



- [A] 任务执行速度一定会成倍提升
- [B] 线程数量过多会增加内存和调度开销，甚至降低整体吞吐
- [C] 线程池会自动把多余线程转为进程
- [D] Python 会直接拒绝启动程序

**参考答案**：1

**解析**：线程并非越多越好，过多线程会带来内存占用、上下文切换和调度开销，反而可能降低吞吐。A 过于绝对，C 不会自动转进程，D 不会直接拒绝启动。

### single_choice · None



- [A] 批量发送 HTTP 请求
- [B] 并发读取多个文件
- [C] 执行大量纯 Python 数值计算以追求多核加速
- [D] 并发查询多个数据库

**参考答案**：2

**解析**：纯 Python 数值计算受 GIL 限制，线程池无法带来多核并行加速，此类 CPU 密集型任务更适合多进程。A、B、D 都属于 I/O 密集型，适合线程池。

### single_choice · None



- [A] 调用 cancel() 尝试取消尚未开始执行的任务
- [B] 调用 set_result() 直接修改任务结果
- [C] 调用 join() 等待该单个任务完成
- [D] 调用 start() 启动任务

**参考答案**：0

**解析**：Future 提供 cancel() 尝试取消尚未开始的任务、result() 获取结果、done() 判断是否完成等。set_result() 通常由执行者调用而非使用者，join() 是线程的方法，Future 没有 start()。

### single_choice · None



- [A] 一个 Future 对象列表
- [B] 一个可迭代对象，按提交顺序产出各任务的返回值
- [C] 任务完成顺序排列的返回值列表
- [D] 一个字典，键为函数名，值为结果

**参考答案**：1

**解析**：map 返回一个迭代器，它会按照输入可迭代对象的顺序依次产出每个任务的结果，结果顺序与提交顺序一致而非完成顺序。A 是 submit 的返回形式，C 混淆了完成顺序与提交顺序，D 与 map 的语义完全无关。

### single_choice · None



- [A] result() 永不阻塞，总能立即拿到结果
- [B] result() 会阻塞直到任务完成，若任务抛出异常则在此处重新抛出
- [C] result() 返回 True 或 False 表示任务是否成功
- [D] result() 只能调用一次，第二次会抛异常

**参考答案**：1

**解析**：Future.result() 在任务未完成时会阻塞等待，任务完成后返回其返回值；如果任务内部抛出了异常，该异常会在调用 result() 时被重新抛出。A 错在它可能阻塞，C 错在返回值是任务结果而非布尔状态，D 错在可以多次调用。

### single_choice · None



- [A] 创建 100 个线程，每个线程负责一个网页，彼此独立
- [B] 创建一个包含适量工作线程的线程池，把所有下载任务提交进去
- [C] 只创建一个线程顺序下载全部网页
- [D] 为每个网页创建一个新的进程池

**参考答案**：1

**解析**：I/O 密集型任务适合用线程池：适量工作线程即可覆盖等待时间，避免创建过多线程。A 线程数过多会增加调度和内存开销，C 没有并发，D 进程池更适合 CPU 密集型且开销更大。

### single_choice · None



- [A] 它指定线程池中同时存在的工作线程数量上限
- [B] 它指定可提交的任务总数上限，超出会立即报错
- [C] 它必须大于等于任务数量，否则任务永远得不到执行
- [D] 它指定每个任务内部可创建的子线程数量

**参考答案**：0

**解析**：max_workers 限定线程池中同时可存在的工作线程数量，多余的任务会排队等待空闲线程。B 错在它不是任务数上限，C 错在任务是排队而非丢弃，D 与任务内部行为无关。

### single_choice · None



- [A] 纯 Python 的大规模数值计算，需要充分利用多核 CPU
- [B] 大量网络请求、文件读写等 I/O 等待型任务
- [C] 需要严格串行顺序且彼此有依赖的任务链
- [D] 需要长期运行且从不结束的后台服务主循环

**参考答案**：1

**解析**：线程池适合 I/O 密集型任务，因为线程在等待 I/O 时会释放 GIL，多个线程可以重叠等待时间。A 受 GIL 限制，纯 Python 计算用多进程更合适；C 有依赖的任务不适合无差别并发；D 长期任务会长期占用线程，不适合共享池。

### single_choice · None



- [A] 退出 with 块时会立即强制杀死所有正在运行的任务
- [B] 退出 with 块时会调用 shutdown(wait=True)，等待已提交任务完成后关闭线程池
- [C] with 语句只对文件操作有效，对线程池无效
- [D] 退出 with 块时会自动取消所有尚未开始的任务

**参考答案**：1

**解析**：ThreadPoolExecutor 支持上下文管理器协议，退出 with 块时等价于调用 shutdown(wait=True)，即不再接受新任务并等待已提交任务执行完毕。A 不会强制杀死，C 错误，D 不会自动取消未开始的任务。

### single_choice · None



- [A] 所有尚未开始的任务会被立即取消，正在运行的任务被中断
- [B] 线程池不再接受新任务，但已提交的任务仍会继续执行
- [C] 线程池立即被销毁，任何后续操作都会抛异常
- [D] shutdown 与 wait 参数无关，behavior 永远相同

**参考答案**：1

**解析**：shutdown(wait=False) 表示不再接受新任务，但已提交的任务仍会继续执行，只是调用方不等待它们完成。A 错在不会取消或中断已有任务，C 错在资源会在任务结束后释放，D 错在 wait 参数确实改变是否阻塞等待。

### single_choice · None



- [A] 异常被线程池静默吞掉，调用方永远无法得知
- [B] 异常会导致整个线程池立即崩溃，后续任务全部失败
- [C] 异常被保存在对应的 Future 中，调用 result() 时重新抛出
- [D] 异常会直接终止主线程

**参考答案**：2

**解析**：任务中未捕获的异常会被记录在对应的 Future 中，当调用该 Future 的 result() 时会重新抛出。A 错在并非静默吞掉，B 错在不会拖垮整个池，D 错在不会直接终止主线程。

### single_choice · None



- [A] ThreadPoolExecutor 中每个任务都会新建一个线程，任务结束后线程立即销毁
- [B] ThreadPoolExecutor 复用固定数量的工作线程，通过任务队列调度提交的任务
- [C] ThreadPoolExecutor 的 submit 方法会阻塞直到任务执行完成才返回
- [D] ThreadPoolExecutor 只能执行不接受参数的函数

**参考答案**：1

**解析**：线程池预先创建并复用一定数量的工作线程，任务被放入队列由空闲线程取出执行，因此选项 B 正确。A 错误，这会失去池化的意义；C 错误，submit 立即返回 Future，不阻塞；D 错误，submit 可以传递任意参数。

### single_choice · None



- [A] 它本身就是任务的返回值
- [B] 它是一个可调用对象，调用它才会真正启动任务
- [C] 它是一个 Future，可用于查询状态、取消任务以及获取最终结果或异常
- [D] 它只能用来记录任务提交时间

**参考答案**：2

**解析**：submit 返回 Future 对象。通过 result() 获取返回值（会阻塞直到完成），done()/cancelled()/exception() 等方法查询状态，add_done_callback 注册回调。

### multi_choice · None



- [A] 任务函数抛出的异常不会直接传播到 submit 的调用点
- [B] 异常被保存在对应 Future 中，只有在调用 result() 或 exception() 时才被观察到
- [C] 如果没有任何地方调用 result()，异常可能被静默忽略
- [D] 任务抛异常会立即终止整个线程池
- [E] map 返回的迭代器在对某个结果取值时，会把对应任务抛出的异常抛出

**参考答案**：[0, 1, 2, 4]

**解析**：线程池捕获任务异常并存入 Future，须通过 result()/exception() 观察，否则可能被忽略；map 遍历时也会抛出对应异常。个别任务异常不会终止整个线程池，故 D 错误。

### fill_blank · None



**参考答案**：["submit", "submit()", "map", "map()"]

**解析**：submit 提交单个可调用对象并返回 Future；map 类似于内置 map，提交多个任务并返回按输入顺序的迭代器。

### fill_blank · None



**参考答案**：["as_completed", "as_completed()"]

**解析**：as_completed(fs) 在任一 Future 完成时产出它，用于实现「谁先完成先处理」。

### fill_blank · None



**参考答案**：["result", "result()"]

**解析**：result() 会阻塞等待并在任务异常时重新抛出该异常，timeout 可限定等待秒数。

### code_reading · None



**参考答案**：依次打印 0、10、err: bad、30。因为 result() 按提交顺序阻塞获取结果，n==2 的任务抛出的 ValueError 在调用对应 Future 的 result() 时被重新抛出并被捕获打印 'err: bad'；其余任务正常返回 n*10，即 0、10、30。

**解析**：任务异常存储在 Future 中，只有在 result() 时才抛出。循环按列表顺序取结果，所以第三个输出是异常信息而非数字。

### code_reading · None



**参考答案**：打印 10。因为 total 累加 0+1+2+3+4=10。as_completed 让循环按任务完成顺序产出 Future，但不影响各任务返回值，求和结果与顺序无关。

**解析**：as_completed 只改变获取结果的顺序（完成即产出），不改变返回值内容，因此累加结果仍为全部返回值之和。

### scenario · None



**解析**：I/O 密集型任务使用线程池，等待网络时可释放 GIL。用 submit 提交每个 URL 返回 Future，通过 as_completed 或 map 收集结果；对每个 Future 调用 result() 并捕获异常，避免单个失败拖垮整批；或用 exception() 检查。进程池开销大且需序列化返回数据，不适合这种网络 I/O 场景。

### scenario · None



**解析**：在循环内反复创建线程池会导致频繁创建/销毁线程，开销巨大且可能造成线程数量暴涨。改进方式是在循环外创建一个复用的 ThreadPoolExecutor，循环内只 submit 任务，循环结束后再用 with 或 shutdown 统一等待回收。

### single_choice · None



- [A] 线程池能绕过 GIL 实现真正的并行计算
- [B] 线程池通过复用线程和统一管理生命周期，减少了线程创建销毁开销并便于收集结果与异常
- [C] 线程池的线程之间不能共享数据
- [D] 线程池不需要处理线程安全

**参考答案**：1

**解析**：线程池的核心价值在于复用线程、统一调度与结果管理。它不能绕过 GIL，线程仍共享内存，因此仍需考虑线程安全。

### single_choice · None



- [A] 任务正在运行中时
- [B] 任务已经完成时
- [C] 任务尚未开始执行且成功被取消时
- [D] 任务抛出了异常时

**参考答案**：2

**解析**：cancel() 只有在任务尚未开始执行时才能成功取消并返回 True；若任务已开始或已完成，则返回 False。

### single_choice · None



- [A] result() 总是立即返回，没完成时返回 None
- [B] result() 在任务未完成时会阻塞，可传 timeout 限定等待秒数；任务抛异常时 result() 会重新抛出该异常
- [C] result() 会取消任务后再返回
- [D] result() 只能获取字符串结果

**参考答案**：1

**解析**：result() 默认会阻塞等待任务完成，支持 timeout 参数。若任务内部抛出异常，调用 result() 时会将该异常重新抛出，这是把并发异常带回主线程的常用方式。

### single_choice · None



- [A] 任务是 CPU 密集型，需要绕过 GIL 做大量数值计算
- [B] 任务主要是网络请求、文件读写等 I/O 等待，且需要共享内存中的数据结构
- [C] 任务需要跨进程隔离，避免一个任务崩溃影响其他任务
- [D] 任务需要在多个 CPU 核心上真正并行执行 Python 字节码

**参考答案**：1

**解析**：线程池适合 I/O 密集型任务，等待时可释放 GIL，并且线程间共享内存便于交换数据。CPU 密集型受 GIL 限制，通常应使用进程池。

### single_choice · None



- [A] 立即强制杀死所有正在运行的线程
- [B] 调用 shutdown(wait=True)，等待已提交的任务全部完成后回收线程
- [C] 什么都不做，线程继续在后台运行且从不回收
- [D] 丢弃尚未开始的任务并立即返回

**参考答案**：1

**解析**：上下文管理器退出时等价于调用 shutdown(wait=True)，会等待已提交任务完成。注意默认不会取消队列中未执行的任务，只是等待它们执行完。

### single_choice · None



- [A] 必须显式指定，否则会报错
- [B] 它决定同时可以运行的最大工作线程数，不指定时使用库根据 CPU 数推导的默认值
- [C] 它决定任务队列的最大长度，超过就拒绝任务
- [D] 它等于提交的任务总数

**参考答案**：1

**解析**：max_workers 控制线程池中同时工作的线程数上限。若不指定，从 Python 3.8 起默认值基于 CPU 数推导（约 min(32, CPU+4)）。它控制线程数而非队列长度或任务总数。

### single_choice · None



- [A] map 返回一个 Future 对象
- [B] map 返回一个迭代器，按输入顺序产出结果，并且会阻塞等待每个结果就绪
- [C] map 返回结果的顺序取决于任务完成先后
- [D] map 立即返回一个列表，未完成的位置是 None

**参考答案**：1

**解析**：Executor.map 返回迭代器，其结果顺序与输入顺序一致（内部按顺序取每个 Future 的结果），因此遍历时会阻塞等待。如需按完成顺序获取，应使用 as_completed。

### single_choice · None



- [A] 使用 Future.result() 按提交顺序依次获取
- [B] 使用 concurrent.futures.as_completed 迭代 Future 集合
- [C] 使用 ThreadPoolExecutor 的 shutdown 方法
- [D] 使用 threading.Lock

**参考答案**：1

**解析**：as_completed 在任一 Future 完成时就产出它，从而实现「先完成先处理」。按提交顺序获取则使用 map 或依次调用 result()。

### multi_choice · None



- [A] done() 返回布尔值，表示任务是否已结束（完成、被取消或抛异常）
- [B] cancel() 请求取消任务，若任务已在运行则返回 False
- [C] exception() 在任务已结束且未抛异常时返回 None，任务抛异常时返回该异常对象
- [D] add_done_callback(fn) 会在任务结束时把该 Future 作为参数传给 fn
- [E] result() 一定不会抛出任务内产生的异常

**参考答案**：[0, 1, 2, 3]

**解析**：done、cancel、exception、add_done_callback 的描述均正确。result() 会在任务内抛出异常时重新抛出该异常，因此选项 E 错误。

### multi_choice · None



- [A] 用 with 语句管理其生命周期，确保任务完成后回收线程
- [B] 对每个小任务单独创建一个新的 ThreadPoolExecutor
- [C] 使用 as_completed 按完成顺序处理结果
- [D] 在 submit 得到的 Future 上通过 result(timeout=...) 设置等待上限
- [E] 把线程池对象设计成长期复用的全局单例，避免频繁创建销毁

**参考答案**：[0, 2, 3, 4]

**解析**：with 管理、as_completed、result 超时、复用池都是推荐做法。选项 B 为每个小任务新建池会频繁创建销毁线程，违背池化目的。
