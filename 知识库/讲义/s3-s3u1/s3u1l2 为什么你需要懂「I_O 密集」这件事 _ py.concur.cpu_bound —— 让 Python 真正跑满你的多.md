# s3u1l2 为什么你需要懂「I/O 密集」这件事 / py.concur.cpu_bound —— 让 Python 真正跑满你的多核 CPU

> 来源 `content/lessons/s3u1l2.json`

## py.concur.io_bound

# py.concur.io_bound：为什么你需要懂「I/O 密集」这件事

**一句话直觉**：当你的程序大部分时间不是在算，而是在「等」——等网络、等磁盘、等数据库——再快的 CPU 也救不了它；这时候你需要的是**并发（concurrency）**，而不是更快的算法。

---

## 1. 先分清：CPU 密集 vs I/O 密集

**CPU 密集（CPU-bound）**：任务时间几乎全花在计算上，例如矩阵乘法、图像滤波、加密哈希。**I/O 密集（I/O-bound）**：任务时间几乎全花在等待外部资源上，例如 `requests.get()`、`open().read()`、数据库查询、`time.sleep()`。

判断标准很简单：**把等待时间拿掉，任务还剩多少纯计算？**

```python
import time

# I/O 密集：99% 的时间都在 sleep 等待，CPU 几乎空闲
def io_task():
    time.sleep(1)      # 模拟网络请求的等待
    return "done"

# CPU 密集：全部时间在做计算
def cpu_task(n=10_000_000):
    return sum(i * i for i in range(n))
```

对 I/O 密集任务，**串行执行 N 个任务 ≈ N × 单个任务等待时间**；而并发可以让这些等待互相重叠。

---

## 2. Python 并发的三件套，先选对工具

| 工具 | 适用场景 | 关键机制 |
|---|---|---|
| `threading` | I/O 密集 | OS 线程，GIL 在 I/O 时会释放 |
| `asyncio` | 高并发 I/O | 单线程事件循环 + `await` 让出控制权 |
| `multiprocessing` | CPU 密集 | 多进程绕开 GIL |

**核心结论**：I/O 密集用 `threading` 或 `asyncio` 都能提速；CPU 密集必须用 `multiprocessing`。

```python
import threading, time

def fetch(name):
    time.sleep(1)                          # 模拟 I/O
    print(f"{name} done at {time.time():.2f}")

start = time.time()
threads = [threading.Thread(target=fetch, args=(f"t{i}",)) for i in range(5)]
for t in threads: t.start()
for t in threads: t.join()
print(f"总耗时: {time.time() - start:.2f}s")   # 约 1s，而不是 5s
```

---

## 3. 线程池：工程里最常用的写法

手动 `Thread` 容易泄漏、难管数量。标准库提供 `concurrent.futures.ThreadPoolExecutor`，一行拿到并发。

```python
from concurrent.futures import ThreadPoolExecutor
import time

def fetch(i):
    time.sleep(0.5)
    return i * i

start = time.time()
with ThreadPoolExecutor(max_workers=8) as ex:   # 复用 8 个线程
    results = list(ex.map(fetch, range(20)))
print(results[:5], f"耗时 {time.time() - start:.2f}s")  # 约 1.25s
```

`max_workers` 的经验值：I/O 密集 ≈ `CPU 核数 × (5~10)`，或直接按对端服务的并发上限设置。

---

## 4. asyncio：单线程里塞进上千个并发

当并发数量很大（比如 1000 个 HTTP 请求）时，线程切换开销会显现，此时 `async/await` 更合适。

```python
import asyncio

async def fetch(i):
    await asyncio.sleep(0.5)         # await 时让出控制权，别人可以跑
    return i * i

async def main():
    tasks = [fetch(i) for i in range(20)]
    return await asyncio.gather(*tasks)

print(asyncio.run(main())[:5])
```

**关键理解**：`await` 不会阻塞事件循环；但**任何同步阻塞调用（如 `time.sleep`、`requests.get`）都会卡死整个循环**。

---

## 5. 误区与选型决策树

- 任务在等外部资源？→ 用 `ThreadPoolExecutor` 或 `asyncio`。
- 任务在烧 CPU？→ `ProcessPoolExecutor`，不要用线程。
- 什么都不知道？→ **先测量**，用 `time.perf_counter()` 给不同方案计时，用数据做决定。

并发不是银弹：它带来**竞态条件（race condition）**、**死锁（deadlock）**、**调试困难**。只在等待确实占大头时才引入，并优先用高层 API（`ThreadPoolExecutor`）而不是裸线程。

---

## 动手练习

写一个脚本 `io_bench.py`，完成：

1. 定义函数 `slow_fetch(i)`，内部 `time.sleep(0.3)`，返回 `i * i`。
2. 用**串行**跑 `range(30)`，记录耗时。
3. 用 `ThreadPoolExecutor(max_workers=10)` 跑同样的 30 个任务，记录耗时。
4. 用 `asyncio.gather` 跑一遍异步版本，记录耗时。
5. 打印三种方式耗时，并解释为什么结果符合「I/O 密集」的预期。

**验收标准**：线程 / 异步版本耗时接近串行的 1/10，并能在 README 中用一句话说明原因。

## py.concur.cpu_bound

# py.concur.cpu_bound —— 让 Python 真正跑满你的多核 CPU

> **一句话直觉**：Python 的 `threading`（线程）对「算数学」几乎没用，因为 GIL（Global Interpreter Lock，全局解释器锁）同一时刻只允许一个线程执行 Python 字节码；要做**计算密集型**（CPU-bound）任务，必须用 `multiprocessing`（多进程），让每个进程拥有独立的 Python 解释器和 GIL，从而真正并行吃满多核。

---

## 0. 先分清两类任务：CPU-bound vs I/O-bound

在写并发代码之前，先问自己一句：**我的程序时间花在「算」还是「等」？**

| 类型 | 特征 | 例子 | 推荐方案 |
|---|---|---|---|
| CPU-bound（计算密集型） | 时间花在 CPU 运算上，几乎不等待外部 | 大整数运算、图像处理、加解密、科学计算、模型推理 | `multiprocessing` / `ProcessPoolExecutor` |
| I/O-bound（I/O 密集型） | 时间花在等待磁盘、网络、数据库 | 爬虫、读写文件、请求 API | `threading` / `asyncio` |

```python
# 判断标准：如果加 CPU 核数能让程序变快，它就是 CPU-bound
# 如果加 CPU 核数没用，但把 1 个请求拆成 100 个并发请求会变快，它就是 I/O-bound
```

**关键结论**：本讲义只处理 CPU-bound。选错并发模型，代码可能比串行还慢。

---

## 1. 为什么 `threading` 救不了 CPU-bound？——GIL 登场

Python 的参考实现 CPython（最常见的那种 Python）里有一把**全局锁 GIL**：任意时刻，**只有一个线程**能执行 Python 字节码。

这就像一个厨房只有一把菜刀：
- 想切菜的人（线程）很多；
- 但一次只能一个人握刀；
- 其他人只能排队等——**并行变成轮流**。

```python
import threading, time

def cpu_work(n):
    # 纯计算：模拟 CPU-bound 任务
    total = 0
    for i in range(n):
        total += i * i
    return total

N = 3_000_000

# 串行：一次算一个
t0 = time.perf_counter()
for _ in range(4):
    cpu_work(N)
t_serial = time.perf_counter() - t0

# 多线程：用 4 个线程「同时」算
t0 = time.perf_counter()
threads = [threading.Thread(target=cpu_work, args=(N,)) for _ in range(4)]
for t in threads: t.start()
for t in threads: t.join()
t_thread = time.perf_counter() - t0

print(f"串行耗时   : {t_serial:.2f}s")
print(f"4 线程耗时 : {t_thread:.2f}s   ← 通常和串行差不多，甚至更慢")
```

你会在大多数机器上看到：**线程版本几乎不加速**。原因就是 GIL——4 个线程只是在轮流用同一把锁。

**关键结论**：CPU-bound 场景下，`threading` 不是工具。想加速必须**绕过 GIL**。

---

## 2. 绕过 GIL：`multiprocessing` 让每个进程拥有自己的解释器

**进程（process）** 是操作系统层面的独立执行单元。每个 Python 进程有：
- 独立的 Python 解释器；
- 独立的 GIL；
- 独立的内存空间。

所以多个进程可以**真正同时**在不同 CPU 核上跑 Python 字节码。

```python
import multiprocessing as mp
import time

def cpu_work(n):
    total = 0
    for i in range(n):
        total += i * i
    return total

N = 3_000_000

if __name__ == "__main__":  # Windows/macOS spawn 模式必须写这行保护
    # 串行基线
    t0 = time.perf_counter()
    for _ in range(4):
        cpu_work(N)
    t_serial = time.perf_counter() - t0

    # 多进程：4 个进程真并行
    t0 = time.perf_counter()
    with mp.Pool(processes=4) as pool:
        pool.map(cpu_work, [N, N, N, N])
    t_parallel = time.perf_counter() - t0

    print(f"串行      : {t_serial:.2f}s")
    print(f"4 进程并行: {t_parallel:.2f}s   ← 理想情况下接近 1/4")
```

**关键结论**：`multiprocessing` 用**多份解释器**换掉 GIL 的限制，这是 Python 里 CPU-bound 加速的正统路子。

---

## 3. 更现代的写法：`concurrent.futures.ProcessPoolExecutor`

`multiprocessing.Pool` 是老 API。工程里推荐 `ProcessPoolExecutor`，因为它：
- 接口和 `ThreadPoolExecutor` 一致，方便切换；
- 用 `Future` 对象统一表示「未来会有结果」，方便 `as_completed` 处理完成顺序；
- 上下文管理器 `with` 自动回收进程。

```python
from concurrent.futures import ProcessPoolExecutor, as_completed
import time

def cpu_work(n):
    return sum(i * i for i in range(n))

if __name__ == "__main__":
    tasks = [3_000_000, 3_000_000, 3_000_000, 3_000_000]

    t0 = time.perf_counter()
    # max_workers 默认 = os.cpu_count()
    with ProcessPoolExecutor(max_workers=4) as ex:
        futures = [ex.submit(cpu_work, n) for n in tasks]
        for fut in as_completed(futures):
            print("完成一个任务，结果 =", fut.result())
    print(f"总耗时: {time.perf_counter() - t0:.2f}s")
```

**关键结论**：新代码优先用 `ProcessPoolExecutor`——同一个接口还能换 `ThreadPoolExecutor` 做对照实验。

---

## 4. 进程的代价：序列化、启动开销与「不要传大对象」

进程之间**不共享内存**。主进程要把参数发给子进程，必须**序列化（serialize / pickle）**；子进程算完再把结果序列化回来。这有两层代价：

1. **每次 `submit` 都有通信成本**：任务太碎，多进程反而慢；
2. **返回值必须可 pickle**：不能返回打开的文件句柄、锁、lambda、局部函数等。

```python
from concurrent.futures import ProcessPoolExecutor

def is_prime(x: int) -> bool:
    if x < 2: return False
    for d in range(2, int(x ** 0.5) + 1):
        if x % d == 0: return False
    return True

if __name__ == "__main__":
    nums = list(range(10_000_000, 10_000_500))  # 一段大区间

    # ❌ 反例：把整个 500 个数一次性发给一个任务，并行度太低
    # ex.submit(is_prime_chunk, nums)

    # ✅ 正例：把大任务切成小块，交给多个进程
    CHUNK = 50
    chunks = [nums[i:i + CHUNK] for i in range(0, len(nums), CHUNK)]

    with ProcessPoolExecutor() as ex:
        results = list(ex.map(lambda c: [n for n in c if is_prime(n)], chunks))

    print("找到素数数量:", sum(len(r) for r in results))
```

**注意**：上面的 `lambda` 在 `ProcessPoolExecutor` 里 **会报错**（lambda 不可 pickle）。正确写法是把切片函数放到模块顶层。

**关键结论**：多进程的黄金法则是「**任务粒度别太碎、返回值别太大、函数定义在模块顶层**」。

---

## 5. 怎么选？一张决策流程图

```
性能不够？
  ├─ 程序时间主要花在等 I/O？ ── Yes ─▶ threading / asyncio
  └─ 程序时间主要花在算？    ── Yes ─▶ multiprocessing / ProcessPoolExecutor
                                        ├─ 任务数多且小  → 合并成一批
                                        ├─ 任务数少且大  → 直接分成 N 份
                                        └─ 要共享数据   → multiprocessing.Manager / Queue
```

**关键结论**：**先判断 workload 类型**，再决定线程/进程/协程；选错工具，越优化越慢。


---

## 本课题目

### single_choice · None



- [A] 同时下载 1000 个网页并等待响应
- [B] 对一段视频进行逐帧滤波计算
- [C] 训练一个神经网络模型
- [D] 对一张 4K 图像做像素级压缩

**参考答案**：0

**解析**：下载网页属于 I/O 密集型任务，大部分时间在等待网络响应，asyncio 能在单线程内通过事件循环高效切换，避免线程/进程开销。其余选项均为 CPU 密集型，应使用多进程或原生扩展并行。

### single_choice · None



- [A] asyncio 无法与文件 I/O 一起使用
- [B] 普通的阻塞式文件读取函数不会让出事件循环，需借助 executor 等机制
- [C] asyncio 只能用于网络编程
- [D] asyncio 的协程不能返回值

**参考答案**：1

**解析**：文件 I/O 属于阻塞调用，直接调用 open/read 会卡住事件循环。可用 loop.run_in_executor 包装，或使用三方异步文件库。A、C、D 都是对 asyncio 的常见误解。

### single_choice · None



- [A] 让事件循环暂停执行
- [B] 把阻塞函数放到线程或进程池中执行，避免阻塞事件循环
- [C] 使协程可以返回值
- [D] 替代 asyncio.gather 实现并发

**参考答案**：1

**解析**：run_in_executor 将同步阻塞调用交给线程/进程池，事件循环可继续调度其他任务。它不暂停循环、不改变返回值机制，也不是 gather 的替代品。

### single_choice · None



- [A] 直接用 asyncio 并在协程内调用同步库
- [B] 使用线程池并限制并发数量，避免资源耗尽
- [C] 为每个请求创建一个新进程
- [D] 禁用 GIL 以提升性能

**参考答案**：1

**解析**：同步库无法 await，用线程池（如 ThreadPoolExecutor）能利用 I/O 释放 GIL 的特性，并可通过信号量限制并发。A 会阻塞事件循环；C 进程开销过大；D 普通情况下无法禁用 GIL。

### single_choice · None



- [A] I/O 密集型只能用 asyncio，CPU 密集型只能用多进程
- [B] I/O 密集型任务大部分时间在等待，适合协程或多线程；CPU 密集型需要真正并行，适合多进程
- [C] 两者都应统一使用多线程
- [D] CPU 密集型任务无法使用任何并发模型

**参考答案**：1

**解析**：I/O 密集因等待多，协程/线程可重叠等待时间；CPU 密集受 GIL 限制，多线程无法并行，需多进程或原生扩展。A、C、D 都过于绝对。

### single_choice · None



- [A] 它只能用于 CPU 密集型任务
- [B] 它把同步函数放到默认线程池执行并返回可 await 的对象
- [C] 它会创建新的进程来运行函数
- [D] 它要求函数必须是 async 函数

**参考答案**：1

**解析**：asyncio.to_thread 是 asyncio 提供的便捷接口，将同步函数提交到默认 ThreadPoolExecutor，返回可 await 的协程对象。它不创建进程，也不要求函数为 async。

### single_choice · None



- [A] requests 会自动改用异步模式
- [B] 事件循环被阻塞，其他协程无法推进
- [C] 程序抛出 TypeError
- [D] requests 会创建子进程来执行

**参考答案**：1

**解析**：requests.get 是同步阻塞调用，会卡住事件循环直到返回，导致其他协程无法运行。A、C、D 均不符合 requests 行为。

### single_choice · None



- [A] 全部使用多进程
- [B] HTTP 使用异步客户端，文件读取用 run_in_executor 包装
- [C] 全部使用 asyncio 并直接调用 open()
- [D] 全部使用单线程串行执行

**参考答案**：1

**解析**：HTTP 可异步，磁盘文件是阻塞调用，需放入 executor，这样能兼顾两类 I/O 且不阻塞事件循环。A 进程开销大，C 会阻塞循环，D 无并发。

### single_choice · None



- [A] asyncio 一定比多线程快，因为零开销
- [B] asyncio 单线程内可支持大量并发连接，线程模型受线程数量和切换开销限制
- [C] 多线程无法处理 I/O 等待
- [D] asyncio 不能与线程池共存

**参考答案**：1

**解析**：asyncio 在单线程内用事件循环调度大量协程，扩展性好；线程数量多时切换和内存开销上升。A 忽略了 asyncio 也有调度开销，C、D 明显错误。

### single_choice · None



- [A] for url in urls:
      await fetch(url)
- [B] await asyncio.gather(*(fetch(u) for u in urls))
- [C] for url in urls:
      asyncio.create_task(fetch(url))
  # 循环结束后不等待
- [D] threading.Thread(target=fetch, args=(url,)).start() for url in urls

**参考答案**：1

**解析**：gather 会并发调度所有 fetch 并等待全部完成。A 是串行；C 创建任务后不等待，主程序可能在任务完成前退出；D 语法错误且 fetch 是协程，不能直接作为线程 target。

### single_choice · None



- [A] 同时等待多个网络请求返回
- [B] 等待数据库查询结果
- [C] 对海量图片做压缩处理
- [D] 从多个 socket 读取数据

**参考答案**：2

**解析**：图片压缩是 CPU 密集型任务，需要多进程绕过 GIL 实现并行。其余三项是 I/O 等待，asyncio 更轻量。

### single_choice · None



- [A] 日志库会变成异步
- [B] 每次同步写文件都会短暂阻塞事件循环，影响并发性能
- [C] 程序会崩溃
- [D] 日志会丢失

**参考答案**：1

**解析**：同步文件写入是阻塞调用，频繁调用会阻塞事件循环，降低并发吞吐。可改用异步日志或放入 executor。A、C、D 不是必然结果。

### single_choice · None



- [A] 程序报错，因为 to_thread 只能用于 I/O
- [B] 由于 GIL，多线程不会带来真正的并行加速
- [C] asyncio.run 会拒绝执行含有 to_thread 的协程
- [D] heavy 会在主线程中串行执行，因为 to_thread 只是语法糖

**参考答案**：1

**解析**：asyncio.to_thread 把任务交给线程池，但 CPython 的 GIL 使 CPU 密集任务无法真正并行，多线程反而可能因切换开销更慢。A、C、D 均为对 to_thread 的错误理解。

### single_choice · None



- [A] 直接调用，因为网络 I/O 会自动让出
- [B] 使用 run_in_executor 或 asyncio.to_thread 将其放到线程池执行
- [C] 改用多进程，每个请求一个进程
- [D] 在协程内使用 time.sleep 等待

**参考答案**：1

**解析**：同步函数不会自动让出事件循环，但因其耗时是 I/O，可用线程池执行。A 会阻塞；C 进程开销过大；D 只会增加阻塞。

### single_choice · None



- [A] await asyncio.sleep(1)
- [B] await asyncio.gather(tasks)
- [C] time.sleep(1)
- [D] await asyncio.wait_for(task, 1)

**参考答案**：2

**解析**：time.sleep 是同步阻塞调用，会卡住事件循环；asyncio.sleep、gather、wait_for 都会在等待期间让出控制权。

### single_choice · None



- [A] 为每个 URL 创建一个进程
- [B] 使用 ThreadPoolExecutor 并设置 200 个线程
- [C] 使用 asyncio 配合一个支持异步的 HTTP 客户端
- [D] 串行 for 循环逐个请求

**参考答案**：2

**解析**：I/O 密集任务用 asyncio + 异步 HTTP 客户端可在单线程内处理大量并发连接，内存和上下文切换开销都远小于多进程或大量线程。A 进程开销大，B 线程数量过多反而增加切换成本，D 完全串行无并发。

### single_choice · None



- [A] start 1 / end 1 / start 2 / end 2
- [B] start 1 / start 2 / end 1 / end 2
- [C] start 1 / start 2 / end 2 / end 1
- [D] end 1 / start 1 / end 2 / start 2

**参考答案**：1

**解析**：gather 会并发启动两个协程，各自先打印 start，随后在 await asyncio.sleep(0) 处让出，事件循环按调度顺序恢复它们，因此 start 1、start 2 先输出，再 end 1、end 2。A 是串行误解，C 的结束顺序不确定但此处通常按创建顺序恢复，D 不符合协程执行顺序。

### single_choice · None



- [A] await asyncio.sleep(0.5)
- [B] 调用第三方同步数据库驱动的 execute() 并等待结果
- [C] await asyncio.Queue().put(item)
- [D] await asyncio.gather(*coros)

**参考答案**：1

**解析**：同步数据库驱动会阻塞线程，必须用异步驱动或 run_in_executor 包装。其余选项本身就是异步 API，不会阻塞事件循环。

### single_choice · None



- [A] 多进程总是比多线程快，因为不受 GIL 限制
- [B] 多线程在 I/O 等待时会释放 GIL，因此常适合 I/O 密集场景
- [C] GIL 的存在使多线程完全不能用于 I/O 密集任务
- [D] asyncio 与多线程不能同时使用

**参考答案**：1

**解析**：I/O 阻塞时 CPython 会释放 GIL，因此多线程能有效并发处理 I/O。多进程有创建和通信开销，未必更快；GIL 不影响 I/O 等待；asyncio 可配合 executor 使用线程。

### single_choice · None



- [A] 每个连接一个进程
- [B] 每个连接一个线程并阻塞读取
- [C] 基于事件循环的异步 I/O
- [D] 每个连接启动一个定时轮询线程

**参考答案**：2

**解析**：大量长连接属于典型 I/O 密集高并发场景，事件循环异步 I/O 能以少量线程支撑数万连接。进程/线程方案开销大，轮询浪费 CPU。

### single_choice · None



- [A] 因为没有使用 asyncio.run
- [B] 因为两个 await 顺序执行，前一个未完成前不会启动后一个
- [C] 因为 work 不是 async 函数
- [D] 因为缺少 asyncio.gather，所以报错

**参考答案**：1

**解析**：顺序 await 会等待前一个协程完成再执行下一个，因此是串行。要并发需用 gather、create_task 等。A 与是否 run 无关，C、D 描述错误。

### single_choice · None



- [A] 等待网络响应、大量 I/O 阻塞的任务
- [B] 进行大量数学计算、长时间占用 CPU 的任务
- [C] 读取多个本地小文件的任务
- [D] 维护一个共享计数器的任务

**参考答案**：1

**解析**：由于 CPython 存在全局解释器锁（GIL），同一时刻只有一个线程能执行 Python 字节码，因此 CPU 密集型任务用多线程无法真正并行。多进程各自拥有独立解释器和内存空间，能绕过 GIL 真正并行利用多核，适合 CPU 密集型任务。I/O 密集型任务在等待时会释放 GIL，用多线程即可。

### single_choice · None



- [A] GIL 使得多线程程序完全无法并行执行任何代码
- [B] GIL 保证同一进程内同一时刻只有一个线程执行 Python 字节码，但执行 C 扩展或 I/O 时可能释放
- [C] GIL 只存在于 Python 2，Python 3 已彻底移除
- [D] GIL 的存在使多进程也失去了并行能力

**参考答案**：1

**解析**：GIL 保证 CPython 中同一进程内同一时刻只有一个线程执行 Python 字节码，但在执行阻塞式 I/O 或某些 C 扩展（如 numpy 的部分运算）时会被释放。它并未被移除，也不影响多进程的并行能力。

### multi_choice · None



- [A] spawn 会启动全新的解释器进程，子进程不继承父进程的全局状态
- [B] fork 会复制父进程的内存（在支持它的平台上），启动更快但可能与线程一起使用时出问题
- [C] forkserver 会先启动一个服务器进程再从中派生，适用于某些场景
- [D] 不同操作系统支持的默认启动方式可能不同

**参考答案**：[0, 1, 2, 3]

**解析**：spawn、fork、forkserver 是常见的三种启动方式：spawn 启动新解释器不继承全局状态；fork 复制父进程内存、快速但在有线程时可能有风险；forkserver 通过一个服务器进程派生；各平台默认方式不同，例如 Windows 只支持 spawn，因此需要 __main__ 保护。

### multi_choice · None



- [A] 将任务拆分为尽量独立、粒度适中的子任务
- [B] 尽量减少子进程与主进程之间传输的数据量
- [C] 让每个子任务返回尽可能大的中间对象以便共享
- [D] 根据 CPU 核心数合理设置进程数量
- [E] 在子进程中执行阻塞式 I/O 等待以提高 CPU 利用率

**参考答案**：[0, 1, 3]

**解析**：拆分独立子任务、减少跨进程数据传输、按核心数设置进程数有利于并行效率。返回大对象会加重序列化开销，反而降低性能；CPU 密集型任务里做阻塞 I/O 等待与提高 CPU 利用率无关。

### multi_choice · None



- [A] 多进程能绕过 GIL，真正利用多核做 CPU 并行计算
- [B] 多进程创建和切换的开销通常比线程大
- [C] 多进程间通信需要序列化，开销通常高于线程间共享内存
- [D] 多进程中的共享状态修改比线程更容易且无需任何同步

**参考答案**：[0, 1, 2]

**解析**：多进程可绕过 GIL 实现真正的 CPU 并行，但进程创建、切换开销大，且进程间通信需要序列化。共享状态在多进程中并不更容易，反而需要共享内存/Manager 及同步机制。

### fill_blank · None



**参考答案**：["GIL", "gil", "Global Interpreter Lock", "global interpreter lock"]

**解析**：该机制就是全局解释器锁（Global Interpreter Lock，简称 GIL）。它只约束同一进程中的线程，因此 CPU 密集型任务更适合用多进程绕过它。

### fill_blank · None



**参考答案**：["ProcessPoolExecutor", "processpoolexecutor"]

**解析**：该类为 concurrent.futures.ProcessPoolExecutor，用于在进程池中并行执行可调用对象；与之相对的线程版本是 ThreadPoolExecutor。

### fill_blank · None



**参考答案**：["if __name__ == '__main__'", "if __name__ == \"__main__\"", "__main__ 保护", "main guard"]

**解析**：Windows 采用 spawn 启动方式，子进程会重新导入主模块，若不把创建进程的代码放在 if __name__ == '__main__' 内，就会递归地不断创建新进程。

### code_reading · None



**参考答案**：因为计算循环几乎不释放 GIL，同一时刻只有一个线程执行 Python 字节码，多线程无法真正并行利用多核，反而可能因锁竞争和线程切换开销而变慢。

**解析**：该任务是纯 Python 字节码的 CPU 密集型计算，GIL 不会在循环中释放，因此多线程无法并行。要利用多核应改用多进程。

### code_reading · None



**参考答案**：打印 [0, 1, 4, 9, 16, 25, 36, 49, 64, 81]；这是进程池并行处理 CPU 密集/可并行任务的典型用法（master 进程分发任务，多个子进程分别计算并返回结果）。

**解析**：square 对 0..9 逐个求平方，map 保持顺序输出，故结果为 0 到 81 的平方序列。使用进程池意味着把任务分发给多个进程，适合可并行、偏 CPU 的任务。

### scenario · None



**参考答案**：[]

**解析**：逐像素滤镜计算是典型的 CPU 密集型任务，任务之间独立可并行；由于 CPython 的 GIL 使多线程无法真正并行，应选择多进程（如进程池）。要点包括：把每张图作为独立任务分发、按 CPU 核心数设置进程数、尽量减少返回的巨大图像数据跨进程传输（可让子进程写文件后只返回路径）、注意 __main__ 保护。

### scenario · None



**参考答案**：[]

**解析**：下载主要是 I/O 等待，等待时会释放 GIL，多线程通常能获得加速；但正则解析属于 CPU 密集型，多线程受 GIL 限制无法并行，因此整体加速不明显。改进思路是把两类工作拆分：I/O 部分用多线程或异步并发，CPU 解析部分用多进程（进程池）并行，二者配合以充分利用带宽和多核。

### single_choice · None



- [A] 把大任务拆成多个独立的小任务提交给进程池
- [B] 让每个子进程返回较小的结果，主进程负责汇总
- [C] 在 Windows 上直接依赖模块顶层代码创建进程而不加 if __name__ == '__main__' 保护
- [D] 为进程池设置合理的进程数量

**参考答案**：2

**解析**：在 Windows（以及 macOS 的 spawn 启动方式）上，子进程会重新导入主模块，若创建进程的代码写在模块顶层且没有 __name__ == '__main__' 保护，会导致无限递归创建进程。其他选项都是推荐做法。

### single_choice · None



- [A] 多进程之间默认共享同一块内存，因此变量修改互相可见
- [B] 多线程之间默认不共享内存，需要通过队列通信
- [C] 多进程之间默认内存相互独立，数据传递通常需要序列化（如 pickle）
- [D] 多线程无法访问主线程创建的全局变量

**参考答案**：2

**解析**：每个进程有独立的内存空间，进程间传递数据需要序列化（如 pickle），开销比线程间共享更大。线程共享同一进程的内存空间，因此可直接访问全局变量，但需要加锁保护。

### single_choice · None



- [A] 程序获得接近线程数的加速比
- [B] 由于 GIL，线程相互竞争解释器锁，可能比单线程还慢
- [C] 程序会直接抛出异常无法运行
- [D] 操作系统会自动把线程转换为进程

**参考答案**：1

**解析**：CPU 密集型任务中线程不会主动释放 GIL，线程频繁切换争夺锁会带来额外开销，可能导致性能不升反降。它们不会自动变成进程，也不会直接报错。

### single_choice · None



- [A] max_workers 表示所有进程加起来的线程总数
- [B] max_workers 表示进程池中同时运行的最大进程数
- [C] max_workers 必须等于机器的 CPU 核心数，否则报错
- [D] max_workers 表示任务队列的最大长度

**参考答案**：1

**解析**：ProcessPoolExecutor 的 max_workers 指定进程池中同时活动的最大工作进程数，默认通常为 CPU 核心数，但可以手动设置，并非必须等于核心数。它不限制任务队列长度，也与线程总数无关。

### single_choice · None



- [A] 子进程返回的对象会以引用方式直接共享给主进程
- [B] 子进程返回的对象会被序列化后传回主进程，因此返回大对象开销较大
- [C] 子进程的返回值只能通过全局变量传递
- [D] 子进程无法向主进程返回任何数据

**参考答案**：1

**解析**：进程间数据必须跨内存边界传递，返回值需要序列化（pickle）回主进程，返回大对象会带来额外的序列化和传输开销。它们不共享引用，也能通过返回值或队列传递数据。

### single_choice · None



- [A] 普通列表在多个子进程间修改后会自动同步
- [B] 可以使用 multiprocessing 提供的共享内存或 Manager 对象在进程间共享状态，但需注意同步
- [C] 子进程对全局变量的修改会反映到主进程
- [D] 多进程之间不能共享任何形式的数据

**参考答案**：1

**解析**：普通对象在子进程中是独立副本，修改不会同步回主进程。multiprocessing 提供 Value、Array 等共享内存对象以及 Manager 管理的对象来实现共享，但需要同步控制。进程间并非完全不能共享数据。

### single_choice · None



- [A] 进程数设得越多越好，开 1000 个进程一定最快
- [B] 进程数一般与可用 CPU 核心数相当，过多反而因调度和切换开销降低效率
- [C] 进程数必须固定为 1
- [D] 进程数应等于内存大小除以 1024

**参考答案**：1

**解析**：对于 CPU 密集型任务，进程数接近核心数通常效率最佳。进程过多会导致上下文切换、内存占用和调度开销上升，反而降低整体性能。

### multi_choice · None



- [A] 任务大部分时间在解码视频、做数值积分等计算上
- [B] 任务大部分时间在等待数据库或网络返回
- [C] 任务在图片上做大量像素级数学变换
- [D] 任务只是循环发起 HTTP 请求并等待响应
- [E] 任务对大规模数据进行加密/哈希计算

**参考答案**：[0, 2, 4]

**解析**：视频解码、数值积分、像素运算、加密哈希等都以 CPU 计算为主，属于 CPU 密集型，适合多进程。等待数据库/网络返回、发起并等待 HTTP 请求属于 I/O 密集型，多线程或异步更合适。
