# s3u1l1 Python 并发模型全景（py.concur.model_overview） / 全局解释器锁（GIL, Global Interpreter Lock）入门

> 来源 `content/lessons/s3u1l1.json`

## py.concur.model_overview

# Python 并发模型全景（py.concur.model_overview）

> 一句话直觉：**Python 里没有“一招鲜”的并发；你必须根据任务是 CPU 密集还是 IO 密集，从线程、进程、协程三种模型里挑一个——选错了，写了半天代码反而更慢。**

在 s3u1l1 这一课，我们建立一张地图：把 CPython 里所有“同时做多件事”的手段一次讲清，后面的课再深入每一块。

---

## 1. 先分清两个词：并发 vs 并行

- **并发（Concurrency）**：程序在逻辑上“同时处理”多个任务，可以是交替推进。就像一个人一边煮面一边切菜。
- **并行（Parallelism）**：物理上真的在同一时刻执行，需要多核。就像两个厨师各自做一道菜。

并发不要求并行；但很多 IO 密集任务只要并发就够了。判断标准只有一句：**任务在等 IO，还是在烧 CPU？**

```python
# 两个任务：一个在等网络（IO 密集），一个在算π（CPU 密集）
import time

def io_task():
    time.sleep(0.5)          # 模拟等待网络/磁盘

def cpu_task():
    sum(i * i for i in range(10_000_00))  # 模拟纯计算

# 结论：io_task 用线程/协程就行，cpu_task 必须多进程
print("判断依据：任务期间 CPU 是闲还是忙")
```

---

## 2. 三大模型：threading / multiprocessing / asyncio

CPython 有三种官方并发手段，各有边界：

| 模型 | 适用 | 关键限制 |
|---|---|---|
| `threading` 线程 | IO 密集 | **GIL（Global Interpreter Lock，全局解释器锁）** 让同一时刻只有一个线程执行 Python 字节码 |
| `multiprocessing` 进程 | CPU 密集 | 进程内存不共享，启动开销大，通信要序列化 |
| `asyncio` 协程 | 高并发 IO | 必须全链路 async，混用同步阻塞会卡死事件循环 |

```python
import threading, multiprocessing, asyncio

# 线程：适合 IO
threading.Thread(target=lambda: print("thread ok")).start()

# 进程：适合 CPU
multiprocessing.Process(target=lambda: print("process ok")).start()

# 协程：适合海量 IO
async def main():
    await asyncio.sleep(0)
    print("async ok")
asyncio.run(main())
```

---

## 3. GIL：理解它的存在与不存在的场景

**GIL（全局解释器锁）** 保证同一进程内任一时刻只有一个线程执行 Python 字节码。后果：

- 多线程跑纯 Python 计算 **不会** 加速（甚至更慢，因为切换开销）。
- 但 **C 扩展可以在执行时释放 GIL**：`numpy`、`torch`、文件读写、socket 等待都算“非 Python 字节码”，此时别的线程可以跑。

```python
import time, threading

def burn(n):
    while n > 0:
        n -= 1

# 单线程 vs 双线程（纯 Python 计数）
start = time.perf_counter(); burn(30_000_000); print("1线程:", round(time.perf_counter()-start, 2))

start = time.perf_counter()
t1 = threading.Thread(target=burn, args=(15_000_000,))
t2 = threading.Thread(target=burn, args=(15_000_000,))
t1.start(); t2.start(); t1.join(); t2.join()
print("2线程:", round(time.perf_counter()-start, 2))  # 通常不会更快
```

> 工程上把这条记成口诀：**“Python 多线程不吃 CPU，只吃等待。”**

---

## 4. 模型选择决策树

写代码之前先问三个问题：

1. 我的任务在等 IO 吗？ → 用 `threading` 或 `asyncio`。
2. 我的任务在烧 CPU 吗？ → 用 `multiprocessing` 或 `concurrent.futures.ProcessPoolExecutor`。
3. 我要处理成千上万个并发连接吗？ → `asyncio`。

```python
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from time import sleep

def io_job(x):
    sleep(0.1); return x * 2

def cpu_job(x):
    return sum(i * i for i in range(x))

# IO：线程池
with ThreadPoolExecutor(max_workers=4) as ex:
    print(list(ex.map(io_job, range(6))))

# CPU：进程池
with ProcessPoolExecutor(max_workers=4) as ex:
    print(list(ex.map(cpu_job, [10_000] * 4)))
```

---

## 5. 一句话总结

- **IO 密集 → 线程或协程**（协程在高并发 IO 下最省资源）。
- **CPU 密集 → 多进程**（或把热路径下沉到 C/Rust/numpy/torch）。
- **不确定 → 先用 `time.perf_counter` 测一遍**，别凭感觉。

后面的课程会展开：`threading` 的锁与队列、`asyncio` 的事件循环与 `await`、`multiprocessing` 的 `Queue`/`Pipe`、以及线程安全和共享状态的坑。今天你只要拿到“选哪个模型”的判断力。

---

## 动手练习

**任务**：写一个 `bench.py`，把下面两个场景分别用“串行、线程池、进程池”跑，并打印耗时对比。

- 场景 A（IO 密集）：抓 8 个 URL，每个 `curl` 一次或 `time.sleep(0.3)`。
- 场景 B（CPU 密集）：对 4 个不同的 `n` 分别计算 `sum(i*i for i in range(n))`，`n=10_000_000`。

**要求**：
1. 用 `time.perf_counter()` 计时。
2. 把结果写成表格贴在你自己的 README。
3. 写出结论：场景 A 谁最快？场景 B 谁最快？为什么？

**预期**：A 中线程池 ≫ 串行；B 中进程池 ≫ 串行 ≈ 线程池。

## py.concur.gil_intro

# 全局解释器锁（GIL, Global Interpreter Lock）入门

> **一句话直觉**：GIL 就像 CPython 里唯一的一把「画笔」——同一时刻，一个 Python 进程里只有一个线程能拿着它执行 Python 字节码（bytecode），所以多线程并不会让纯 Python 计算变快，但遇到 I/O 阻塞时会主动「让笔」，从而仍然有用。

前置知识：本章是并发编程的起点，只需会写基础的 `def` 函数、`for` 循环、`import` 语句即可。

---

## 1. GIL 到底是什么？

**GIL（Global Interpreter Lock，全局解释器锁）** 是 CPython（Python 官方实现）解释器内部的一把互斥锁（mutex）。它保证 **同一进程内、同一时刻只有一个线程在执行 Python 字节码**。注意三点：

1. 它是 **CPython 特有** 的实现细节，不是 Python 语言规范；Jython、PyPy（部分模式）没有 GIL。
2. 它保护的是 **解释器内部状态**（引用计数 refcount、内存分配等），而非你业务代码里的共享数据。
3. 它只锁「Python 字节码」；调用 C 扩展时（如 NumPy、`hashlib`）通常会 **释放 GIL**。

```python
import threading, time

# 用 threading.current_thread() 观察：每个线程都有独立的名字
# 但无论开多少线程，同一时刻只有一个在跑 Python 字节码
def worker(n):
    s = 0
    for i in range(n):
        s += i
    return s  # 纯 Python 计算：受 GIL 限制，多线程不会更快

print("当前主线程:", threading.current_thread().name)
```

---

## 2. 为什么它存在？——简单与快速

CPython 用 **引用计数（reference counting）** 做内存管理。每次对象增减引用都要修改计数器，如果多个线程同时改，就需要一把锁保护 **所有** 计数器——粒度太细、开销巨大。

GIL 用一个「大锁」一次性解决：

- 单线程性能好（无细粒度锁开销）；
- C 扩展生态写起来简单（不用考虑线程安全）；
- 内存管理实现简单。

代价就是：**CPU 密集型（CPU-bound）任务无法用多线程加速**。

```python
import time

def cpu_task(n=8_000_000):
    s = 0
    for i in range(n):
        s += i * i
    return s

start = time.perf_counter()
cpu_task()
print(f"单次耗时: {time.perf_counter()-start:.3f}s")
# 若用两个线程跑两次，总时长≈两次之和，不会变成一半
```

---

## 3. GIL 不是「全锁」：I/O 时会释放

关键结论：**当线程执行阻塞型 I/O（如 `time.sleep`、读文件、网络请求）时，CPython 会释放 GIL**，让其他线程获得执行机会。

因此：

- **I/O 密集型（I/O-bound）任务：多线程有效**；
- **CPU 密集型任务：多线程无效**，应该用多进程（`multiprocessing`）或原生扩展。

```python
import threading, time

def io_task(name):
    print(f"{name} 开始，准备 sleep")
    time.sleep(1)          # sleep 会释放 GIL，其他线程得以运行
    print(f"{name} 结束")

start = time.perf_counter()
ts = [threading.Thread(target=io_task, args=(f"T{i}",)) for i in range(3)]
for t in ts: t.start()
for t in ts: t.join()
print(f"3 个 1 秒 sleep 总耗时 ≈ {time.perf_counter()-start:.2f}s")  # ≈1s 而非 3s
```

---

## 4. GIL 的调度：`sys.setswitchinterval` 与「被动让出」

GIL 并非固定时间片。CPython 3.x 使用 **时间片切换**：默认每 5 毫秒检查一次是否让出（`sys.getswitchinterval()`）。你可以在特定场景下调整它，但一般不需要。

```python
import sys
print("默认切换间隔(秒):", sys.getswitchinterval())  # 一般是 0.005
# 仅演示，不要在生产里乱改
# sys.setswitchinterval(0.001)
```

另外，某些操作（如字节码执行「检查点 checkpoint」、`time.sleep`、I/O 阻塞）会**主动释放**，无需等时间片。

---

## 5. 工程级结论：怎么用它，怎么绕过它

| 任务类型 | 推荐方案 | 原因 |
|---|---|---|
| CPU 密集型（数值计算、图像处理） | `multiprocessing` / `concurrent.futures.ProcessPoolExecutor` / NumPy | 每进程独立 GIL |
| I/O 密集型（爬虫、文件、数据库） | `threading` / `asyncio` | I/O 阻塞时释放 GIL |
| 混合 | 进程池 + 线程池组合 | 按瓶颈分配 |

```python
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import time

def io_bound(x):
    time.sleep(0.5)
    return x * 2

def cpu_bound(x):
    s = 0
    for i in range(2_000_000):
        s += i
    return s + x

with ThreadPoolExecutor(4) as ex:      # I/O：4 个任务 ≈0.5s
    print("threads:", list(ex.map(io_bound, range(4))))

with ProcessPoolExecutor(4) as ex:     # CPU：4 进程并发跑，绕开 GIL
    print("processes:", list(ex.map(cpu_bound, range(4))))
```

**Python 3.13 起** 官方提供了 **free-threaded（无 GIL）构建** 作为实验特性；但生态兼容性与性能权衡仍在演进，工程上仍需按上表选型。

---

## 动手练习

**任务：用实验证明 GIL 对两类任务的影响差异。**

1. 写两个函数：
   - `cpu_heavy(n)`：纯 Python 加法循环 `sum`（如 5,000,000 次）。
   - `io_heavy(n)`：`time.sleep(0.5)` 若干次。
2. 分别用 **单线程顺序执行 4 次** 和 **4 线程并发执行**，记录 `time.perf_counter()` 耗时。
3. 输出一张小表：

   ```
   task        serial(s)   threads(s)   加速比
   cpu_heavy   ...         ...          ...
   io_heavy    ...         ...          ...
   ```

4. 用 2~3 句话解释：为什么 `cpu_heavy` 的加速比接近 1，而 `io_heavy` 的加速比接近 4？

**提交要求**：贴出你的代码与实测表格，并给出你的结论。预期结论是——CPU 任务被 GIL 卡住、几乎无加速；I/O 任务因为 `sleep` 释放 GIL 而线性加速。

```python
import threading
import time
import sys


def cpu_heavy(n=2_000_000):
    """纯 Python 计算：受 GIL 限制，多线程不会加速"""
    s = 0
    for i in range(n):
        s += i
    return s


def io_heavy(seconds=0.5):
    """阻塞 I/O：sleep 期间释放 GIL，其他线程可运行"""
    time.sleep(seconds)
    return seconds


def run_serial(fn, n):
    t0 = time.perf_counter()
    for _ in range(n):
        fn()
    return time.perf_counter() - t0


def run_threads(fn, n):
    t0 = time.perf_counter()
    ts = [threading.Thread(target=fn) for _ in range(n)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    return time.perf_counter() - t0


if __name__ == "__main__":
    print("switch interval:", sys.getswitchinterval())
    n = 4

    ser_cpu = run_serial(cpu_heavy, n)
    thr_cpu = run_threads(cpu_heavy, n)
    print(f"cpu_heavy  serial={ser_cpu:.3f}s  threads={thr_cpu:.3f}s  speedup={ser_cpu/thr_cpu:.2f}x")

    ser_io = run_serial(io_heavy, n)
    thr_io = run_threads(io_heavy, n)
    print(f"io_heavy   serial={ser_io:.3f}s  threads={thr_io:.3f}s  speedup={ser_io/thr_io:.2f}x")
```


---

## 本课题目

### single_choice · None



- [A] 为每个请求创建一个线程，用 join 等待全部结束
- [B] 使用基于事件循环的单线程异步模型，把每个请求注册为可等待任务
- [C] 为每个请求 fork 一个子进程并发执行
- [D] 用一个线程顺序发送请求，逐条等待返回

**参考答案**：1

**解析**：大量 I/O 等待型任务适合用单线程事件循环的异步模型，避免线程创建和上下文切换开销。为每个请求建线程会因数量巨大导致资源耗尽和切换代价高；fork 子进程开销更大且不适合网络 I/O 等待；顺序执行则完全失去并发，吞吐量极低。

### single_choice · None



- [A] 在单线程中注册多个 asyncio 协程交替执行
- [B] 使用 asyncio 事件循环配合 await 让计算任务互相让出
- [C] 使用 multiprocessing 把计算分片交给多个进程
- [D] 使用一个线程配合 select 多路复用监听计算进度

**参考答案**：2

**解析**：CPU 密集任务在存在 GIL 的多线程或单线程异步模型下无法真正并行，只有多进程才能利用多核并行加速。asyncio 协程是协作式调度，计算不主动 await 就不会让出；select 用于 I/O 多路复用，不能加速计算。

### single_choice · None



- [A] 并发一定意味着同一时刻多个任务在多个核上同时运行
- [B] 并行是并发的一种，单核上也可以实现并行
- [C] 并发指多个任务在重叠的时间段内推进，并行指同一时刻真正同时执行
- [D] 并发和并行是同一概念的不同翻译，没有区别

**参考答案**：2

**解析**：并发强调任务在时间上重叠推进（可通过切换实现），并行强调物理上同一时刻同时执行，通常需要多核。单核可通过时间片或协作调度实现并发但无法并行；两者是不同概念。

### single_choice · None



- [A] 最多只有 4 个任务能被执行，其余 16 个会被丢弃
- [B] 4 个线程轮流执行任务，某个任务阻塞等待 I/O 时其他线程可继续推进，从而提升整体吞吐
- [C] 每个任务会自动分配到不同 CPU 核上真正并行运行
- [D] 线程池会自动把 I/O 等待型任务转交给事件循环处理

**参考答案**：1

**解析**：线程池用固定数量线程复用执行任务，某线程因 I/O 阻塞时其他线程可继续运行，从而在等待期间重叠工作、提高吞吐。任务不会被丢弃，只会排队；不保证每个任务落在不同核上；线程池也不会自动转交给事件循环。

### single_choice · None



- [A] 活锁
- [B] 饥饿
- [C] 死锁
- [D] 竞态条件

**参考答案**：2

**解析**：两个或多个线程循环等待对方持有的资源而永久停滞称为死锁。活锁是线程还在活动但无法推进；饥饿是某线程长期得不到资源；竞态条件指结果依赖执行时序，不一定导致停滞。

### single_choice · None



- [A] multiprocessing 中通过 Queue 传递的对象会被序列化，因此对对象有可序列化要求
- [B] threading 中通过 queue.Queue 传递的对象也必须可序列化
- [C] multiprocessing 的 Queue 与线程的 Queue 完全等价，都直接传引用
- [D] threading 中共享列表需要序列化，multiprocessing 中不需要

**参考答案**：0

**解析**：跨进程通信需要把对象转为字节流，因此要求对象可序列化；线程共享同一地址空间，queue.Queue 直接传递对象引用，无需序列化。其余选项把两种队列的机制颠倒或等同。

### single_choice · None



- [A] 在事件循环中直接调用压缩函数，让协程等它算完
- [B] 把压缩任务提交给线程池执行，利用线程与事件循环并行
- [C] 把压缩任务提交给进程池执行，通过 run_in_executor 之类的接口等待结果
- [D] 为每条长连接都创建一个独立进程来分担压缩负载

**参考答案**：2

**解析**：CPU 密集任务放入进程池可绕开 GIL 真正并行，同时不阻塞事件循环中的连接处理。直接调用会阻塞循环；线程池对 CPU 密集任务因 GIL 效果有限；为每条连接建进程开销极大且不合理。

### single_choice · None



- [A] 前一个线程会主动在每条语句后调用 yield 让出
- [B] 解释器会周期性地要求当前线程释放 GIL，让其他线程有机会运行
- [C] 操作系统会直接剥夺该线程的执行权并强制切换，无需 GIL 参与
- [D] 只有当前线程显式调用 time.sleep 时才可能切换

**参考答案**：1

**解析**：CPython 通过周期性检查让当前线程释放 GIL，供其他线程竞争，从而实现线程切换。Python 语句不会自动调用 yield；由于 GIL 存在，单靠操作系统抢占并不能让多个线程同时执行字节码；sleep 只是主动释放的一种方式，并非唯一。

### single_choice · None



- [A] 异步模型的代码中若调用了阻塞式网络接口，同样会阻塞整个事件循环
- [B] 异步模型中调用阻塞式接口不会影响其他协程，因为事件循环会自动调度
- [C] 多线程模型中某个线程阻塞会阻塞整个进程，因此多线程不适合 I/O 等待
- [D] 异步模型天然支持在阻塞调用期间并行使用多个 CPU 核

**参考答案**：0

**解析**：事件循环是单线程的，任何同步阻塞调用都会卡住整个循环。多线程中单个线程阻塞只影响该线程，其他线程仍可运行，因此适合 I/O 等待。异步模型本身不会带来多核并行。

### single_choice · None



- [A] 直接读写，因为 GIL 会保证复合操作如“读-改-写”的原子性
- [B] 用锁保护对字典的复合操作，或改用线程安全的数据结构
- [C] 把字典改成全局变量并加 nonlocal 声明即可保证安全
- [D] 为每次读写创建一个新线程，避免冲突

**参考答案**：1

**解析**：GIL 只保证单条字节码的原子性，不保证“读-改-写”这类复合操作整体原子，因此仍需锁或线程安全结构。nonlocal 只涉及变量作用域，与并发安全无关；频繁创建线程反而增加竞态与开销。

### single_choice · None



- [A] 用进程绕开 GIL 获得多核并行，用线程在进程内处理大量 I/O 等待
- [B] 用进程来处理 I/O 等待，用线程来做纯计算以充分利用 GIL
- [C] 让每个进程内的线程各自运行在独立 CPU 上，从而完全避免锁
- [D] 混合结构可以消除进程间通信的序列化开销

**参考答案**：0

**解析**：常见的混合动机是：进程负责 CPU 并行（绕开 GIL），进程内用线程处理 I/O 并发。线程并不能让纯计算真正并行，也无法避免锁；混合结构不会消除跨进程通信的序列化。

### single_choice · None



- [A] 异步模型下单个请求的延迟可能比同步调用更长，但多个请求的等待被重叠
- [B] 异步模型会冻结所有请求直到全部完成
- [C] 异步模型只能串行执行任务，无法并发
- [D] 异步模型依赖多核才能真正开始执行任何任务

**参考答案**：0

**解析**：异步的收益来自把多个等待重叠，而不是让单个等待消失；单个请求仍要经历网络延迟。它不冻结请求、不是串行、也不依赖多核即可运行。所以只有第一项正确刻画了收益来源。

### single_choice · None



- [A] 多线程共享进程内存，多进程之间默认不共享内存，需显式通信
- [B] 多进程共享内存，多线程需要显式通信
- [C] 两者都默认共享全部内存，只是调度方式不同
- [D] 两者都默认不共享内存，必须通过队列通信

**参考答案**：0

**解析**：线程属于同一进程，天然共享地址空间，因此需要锁来保护共享数据；进程各自有独立地址空间，默认不共享，需通过管道、队列、共享内存等方式通信。其余选项把两者的内存模型颠倒或一概而论，属于常见误解。

### single_choice · None



- [A] Python 的 += 不是原子操作，两个线程可能读到同一个旧值再写回，导致更新丢失
- [B] 线程启动后没有 join，主线程提前退出导致计数未完成
- [C] 全局变量在函数内赋值时必须声明 nonlocal，否则每次都是局部变量
- [D] 解释器会把 += 编译成机器指令，速度太快以至于计数被合并

**参考答案**：0

**解析**：counter += 1 包含读取、加一、写回三个步骤，GIL 可能在步骤间切换线程，造成竞态与更新丢失，因此需要用锁保护。join 缺失只会导致主线程先结束，不会让最终值偏小；模块级全局变量在函数内赋值默认是局部变量，但本题是 += 读取全局，并非该问题；计数不会被合并。

### single_choice · None



- [A] 协程由操作系统内核抢占式调度，线程由事件循环调度
- [B] 协程由事件循环协作式调度，只在 await 处让出控制权；线程调度由操作系统抢占
- [C] 两者都是抢占式，区别只在创建开销
- [D] 两者都是协作式，区别只在能否使用多核

**参考答案**：1

**解析**：协程是用户态的协作式并发，任务只在 await 时让出，调度由事件循环负责；线程由操作系统抢占式调度，随时可能被切换。协程并非内核调度，线程也非协作式，因此其余选项均错误。

### single_choice · None



- [A] GIL 使多线程在任何情况下都无法并行的说法完全正确，多线程因此毫无价值
- [B] GIL 在同一时刻只允许一个线程执行 Python 字节码，但 I/O 或部分扩展库调用期间会释放
- [C] GIL 会同时保护多进程之间的数据一致性
- [D] GIL 是用户必须手动加锁才能生效的机制

**参考答案**：1

**解析**：GIL 保证同一时刻只有一个线程执行 Python 字节码，但在阻塞式 I/O 和部分 C 扩展（如数值计算库）执行期间会释放，因此多线程仍能提升 I/O 密集型任务吞吐。GIL 不跨进程生效，也不是用户手动启用的锁。

### single_choice · None



- [A] 同时下载多个文件并等待网络返回
- [B] 在后台执行日志写入的同时继续响应界面事件
- [C] 对大规模矩阵做逐元素浮点运算并希望缩短挂钟时间
- [D] 同时等待多个数据库查询返回

**参考答案**：2

**解析**：纯计算任务受 GIL 限制，多线程无法获得真正的并行加速，应改用多进程。其余三项都是 I/O 等待或阻塞为主，多线程可以在等待期间切换，能够提升响应性或吞吐量。

### single_choice · None



- [A] asyncio 使用了多核，因此并行执行了 200 个请求
- [B] 等待网络时协程会让出控制权，事件循环在此期间推进其他请求，等待时间被重叠
- [C] asyncio 把请求合并成了一个 HTTP 请求发送
- [D] asyncio 会临时禁用网络延迟，让请求立即返回

**参考答案**：1

**解析**：异步模型的核心是把等待时间重叠起来：某个协程在等待 I/O 时 await 让出，事件循环转去推进其他已就绪的协程，从而在单线程内并发处理大量请求。它不依赖多核，也不会合并请求或消除网络延迟。

### single_choice · None



- [A] 事件循环会自动把该函数放到另一个线程执行，不影响其他任务
- [B] 整个事件循环被阻塞，其他已注册的协程在此期间无法推进
- [C] 该函数会被自动转换为协程，因此不影响调度
- [D] 事件循环会中断该函数并抛出异常，提示必须使用 await

**参考答案**：1

**解析**：事件循环是单线程协作式调度，同步阻塞调用不让出控制权，会卡住整个循环，其他协程无法推进。正确做法是用 run_in_executor 之类的方式把它移到线程或进程池。其他选项都错误假设了自动线程化、自动协程化或自动中断。

### single_choice · None



- [A] 进程创建与销毁的系统开销更大
- [B] 跨进程数据交换需要序列化，通信成本更高
- [C] 进程间共享可变状态需要额外同步机制
- [D] 无法利用多核 CPU 进行并行计算

**参考答案**：3

**解析**：多进程的核心优势恰恰是能绕开 GIL 并利用多核并行，因此“无法利用多核”不是代价而是误解。其余三项都是多进程真实的额外开销：创建开销、跨进程通信序列化、共享状态同步。

### single_choice · None



- [A] 它保证多个线程可以真正并行执行 Python 字节码
- [B] 它保证同一时刻只有一个线程执行 Python 字节码，从而简化解释器内部状态的并发保护
- [C] 它用于限制进程可创建的最大线程数量
- [D] 它会在每次函数调用时自动释放，所以多线程总能提速

**参考答案**：1

**解析**：GIL 是 CPython 解释器的一把全局互斥锁，使同一进程内同一时刻只有一个线程执行 Python 字节码，主要用于保护解释器内部共享状态。它并不保证并行，也不是线程数量限制。

### single_choice · None



- [A] 耗时约为单线程的 1/4，因为 4 个核心并行计算
- [B] 可能比单线程还慢，因为线程切换加上 GIL 无法让纯 Python 字节码并行
- [C] 耗时完全不变，因为 threading 模块会把任务合并
- [D] 会直接抛出 RuntimeError，因为 GIL 禁止纯计算多线程

**参考答案**：1

**解析**：纯 Python 字节码计算受 GIL 限制，无法在多核上并行，线程切换还带来额外开销，所以可能比单线程更慢。

### single_choice · None



- [A] C 扩展代码运行时自动不受 GIL 约束，可任意并行
- [B] C 扩展在需要时可以显式释放 GIL，从而允许其他线程运行
- [C] C 扩展调用时解释器会自动释放 GIL，无需任何处理
- [D] C 扩展无法与 Python 线程共存

**参考答案**：1

**解析**：C 扩展可在执行耗时且不访问 Python 对象的计算时显式释放 GIL（如 Py_BEGIN_ALLOW_THREADS），从而让其他线程运行；默认仍受 GIL 约束。

### multi_choice · None



- [A] 大量 HTTP 请求的等待
- [B] 密集的纯 Python 数学循环
- [C] 磁盘文件读写等待
- [D] 数据库查询的网络往返等待
- [E] 对大量字符串做纯 Python 处理

**参考答案**：[0, 2, 3]

**解析**：等待网络、磁盘、数据库等 I/O 时 GIL 会被释放，多线程可重叠等待时间；纯 Python 计算（B、E）受 GIL 限制难以提速。

### multi_choice · None



- [A] 它是 CPython 中一个全局互斥锁
- [B] 它保证同一时刻只有一个线程执行 Python 字节码
- [C] 它可以让所有 Python 操作自动线程安全
- [D] 在 I/O 阻塞时会释放
- [E] 移除它会让 CPython 的引用计数等内部机制实现更复杂

**参考答案**：[0, 1, 3, 4]

**解析**：GIL 是 CPython 的全局锁，保证单线程执行字节码并在 I/O 时释放；它不等于自动线程安全，且其存在简化了引用计数等实现，移除会带来复杂度。

### multi_choice · None



- [A] CPU 密集型任务优先考虑 multiprocessing
- [B] 认为多线程一定能让纯 Python 计算变快
- [C] I/O 密集型任务可用多线程或 asyncio
- [D] 认为有 GIL 就完全不用考虑加锁
- [E] 理解 GIL 是 CPython 实现细节而非语言规范

**参考答案**：[0, 2, 4]

**解析**：正确认知包括：CPU 密集用多进程、I/O 密集用多线程/异步、GIL 是实现细节。B 和 D 是常见误解。

### fill_blank · None



**参考答案**：["GIL", "gil", "Global Interpreter Lock", "global interpreter lock"]

**解析**：GIL 即 Global Interpreter Lock（全局解释器锁），是 CPython 的实现机制。

### fill_blank · None



**参考答案**：["释放", "release", "释放掉", "临时释放"]

**解析**：执行阻塞 I/O 前解释器会释放 GIL，完成后重新获取，这是 I/O 密集型多线程能提速的关键。

### code_reading · None



**参考答案**：不一定。counter += 1 不是原子操作，涉及读取、加一、写回。虽然 GIL 保证单条字节码不会并行执行，但线程可能在字节码之间被切换，导致两个线程读到相同的旧值从而丢失更新。要得到正确结果需使用 threading.Lock 等同步机制。

**解析**：GIL 只提供字节码级别的原子性，不保证复合操作原子化，因此多线程累加存在竞态，结果可能小于 500000。

### code_reading · None



**参考答案**：程序 B 更可能获得加速。网络请求是 I/O 操作，等待时会释放 GIL，使其他线程能运行，从而重叠等待时间；程序 A 是纯 Python 计算，受 GIL 限制字节码无法并行执行，加速有限甚至可能更慢。

**解析**：GIL 在 I/O 阻塞时释放，因此 I/O 密集型多线程可提速；纯计算任务受 GIL 限制无法多核并行。

### scenario · None



**解析**：拉取远程 API 属于 I/O 密集型，可用多线程或异步并发；纯 Python 数据清洗属于 CPU 密集型，受 GIL 限制，应使用多进程。因此不能简单地全部改成多线程。

### scenario · None



**解析**：CPU 密集的 JSON 解析受 GIL 限制，用多进程并行；I/O 密集的下载在等待时释放 GIL，用多线程或 asyncio 并发。关键是依据任务是否释放 GIL 来选择并发模型。

### single_choice · None



- [A] 对大量整数做密集的纯 Python 循环求和
- [B] 递归计算斐波那契数列
- [C] 等待多个网络请求的响应（I/O 等待为主）
- [D] 在纯 Python 中做矩阵乘法

**参考答案**：2

**解析**：I/O 操作会在阻塞时释放 GIL，使其他线程可以运行，因此 I/O 密集型任务能从多线程受益；纯 Python 计算类任务受 GIL 限制难以并行。

### single_choice · None



- [A] 整个 I/O 期间 GIL 始终被持有，其他线程无法运行
- [B] 执行阻塞 I/O 时会释放 GIL，返回后再重新获取
- [C] I/O 会临时禁用 GIL，导致解释器崩溃风险
- [D] GIL 只在主线程中才有，子线程不受影响

**参考答案**：1

**解析**：CPython 在执行可能阻塞的系统调用（如文件/网络 I/O）前会释放 GIL，完成后重新获取，这是 I/O 密集型多线程能提速的根本原因。

### single_choice · None



- [A] 多进程各进程有独立的解释器和内存空间，因此不受同一把 GIL 限制
- [B] 多进程共享同一个 GIL，所以不比多线程快
- [C] 多线程不受 GIL 影响，多进程才受影响
- [D] 多进程无法在 I/O 密集型任务中使用

**参考答案**：0

**解析**：每个进程有独立的 Python 解释器和独立 GIL，因此多进程可真正并行 CPU 密集型任务；多线程共享同一解释器与 GIL。

### single_choice · None



- [A] 有 GIL 就不需要任何同步，所有操作都是原子的
- [B] GIL 只保证单条字节码级别的原子性，复合操作（如读取-修改-写入）仍可能需要加锁
- [C] GIL 会自动把每个函数调用变成原子操作
- [D] 只要使用多线程就必须禁用 GIL

**参考答案**：1

**解析**：GIL 不能让多步复合操作原子化，例如 `x += 1` 涉及读取、计算、写回，多线程下仍可能产生竞态，需要 Lock 等同步机制。

### single_choice · None



- [A] CPU 使用率随线程数线性上升，墙钟时间下降
- [B] 任一时刻只有一个线程在跑 Python 字节码，CPU 利用率难以打满多核
- [C] 所有线程会被强制串行化到单核，且 CPU 使用率恒为 100% 单核
- [D] 线程会在启动时全部卡死，因为争抢 GIL 必然死锁

**参考答案**：1

**解析**：GIL 使 Python 字节码同一时刻只被一个线程执行，因此 CPU 密集型多线程通常只能接近单核满载，无法线性加速；但也不会必然死锁。

### single_choice · None



- [A] 所有 Python 实现（CPython、Jython、PyPy 等）都有 GIL
- [B] GIL 是 CPython 的实现细节，其他实现不一定有
- [C] GIL 是 Python 语言规范强制要求的
- [D] 只有 Python 2 有 GIL，Python 3 已完全移除

**参考答案**：1

**解析**：GIL 是 CPython 解释器的实现细节，并非语言规范强制；Jython、IronPython 等实现没有 GIL，Python 3 的 CPython 仍然有 GIL。

### single_choice · None



- [A] 全部用多线程，因为线程创建开销最小
- [B] 全部用单线程，避免 GIL 竞争
- [C] CPU 密集部分用多进程，I/O 密集部分用多线程或异步
- [D] 对 CPU 密集部分开启更多线程即可绕过 GIL

**参考答案**：2

**解析**：CPU 密集型任务应使用多进程以绕过 GIL 实现并行；I/O 密集型任务可用多线程或 asyncio。单纯增加线程无法绕过 GIL。

### single_choice · None



- [A] 多线程无法利用多核，这是操作系统限制
- [B] 在 CPython 中，纯 Python 字节码受 GIL 限制无法多核并行，加速取决于任务类型
- [C] 多线程只有当线程数等于 CPU 核数时才有效
- [D] 多线程加速需要手动关闭 GIL

**参考答案**：1

**解析**：在 CPython 中，是否加速取决于任务是否会在运行中释放 GIL；纯 Python 计算受 GIL 限制，无法多核并行。
