# s3u3l1 Python 多进程编程入门 / `multiprocessing.Pool`：让 Python 真正并行起来

> 来源 `content/lessons/s3u3l1.json`

## py.mp.process_basic

# py.mp.process_basic：Python 多进程编程入门

> **一句话直觉**：当你想让 Python 真正同时做几件事、绕开 GIL(全局解释器锁，Global Interpreter Lock) 时，`multiprocessing` 模块就是让代码“开分身”的最简单方式。

---

## 0. 为什么要学 `multiprocessing`？

Python 有两个常见的并发(Concurrency)方案：`threading`(线程) 和 `multiprocessing`(多进程，Multi-Processing)。因为 CPython 有 GIL，同一时刻只有一个线程执行 Python 字节码，所以**CPU 密集型(CPU-bound)任务用线程几乎无法加速**，而多进程每个进程有独立的 Python 解释器和独立内存空间，可以真正并行跑满多核。

几个关键结论先记住：

1. **线程共享内存**，**进程各自独立内存**，进程间通信(IPC, Inter-Process Communication)需要显式手段。
2. **进程更重**：创建/销毁开销比线程大，适合“任务粗、量大”的场景。
3. **进程更安全**：一个子进程崩了不会拖垮主进程，也不会因共享状态被破坏而相互污染。

---

## 1. 最小可用：`Process` 启动一个子进程

`multiprocessing.Process` 是最基础的入口。它的用法与 `threading.Thread` 几乎一样：传入 `target` 和 `args`，然后 `start()` 和 `join()`。

- `start()`：真正 fork/spawn 出子进程并开始运行。
- `join()`：主进程阻塞等待该子进程结束。
- `pid`：进程 ID，可以用来验证“确实开了新进程”。

```python
import os
import multiprocessing as mp

def worker(name: str):
    # 每个子进程都有自己的 PID 和内存空间
    print(f"[{name}] 子进程 pid={os.getpid()}, 父进程 ppid={os.getppid()}")

if __name__ == "__main__":
    print(f"主进程 pid={os.getpid()}")
    p = mp.Process(target=worker, args=("A",))
    p.start()   # 启动子进程
    p.join()    # 主进程等它结束
    print("主进程结束")
```

**直觉**：`Process` 就是“开一个新的 Python 解释器跑你的函数”。

---

## 2. 关键陷阱：为什么必须写 `if __name__ == "__main__"`？

在 Linux/macOS 上，`multiprocessing` 默认使用 `fork`，父进程内存直接复制给子进程，通常不加 `__main__` 保护也能跑。但 **Windows 和 macOS 的新默认(start method = `spawn`)** 会重新导入主模块，如果模块顶层直接写 `p.start()`，就会被**无限递归地创建进程**。

所以工程级代码必须无条件加上这层保护：

```python
import multiprocessing as mp

def work():
    print("running")

if __name__ == "__main__":   # 必须！否则 spawn 模式会递归 import 自己
    p = mp.Process(target=work)
    p.start()
    p.join()
```

**记住**：不论什么平台，脚本都写 `if __name__ == "__main__":`，这是多进程的“安全带”。你还可以用 `mp.get_start_method()` 查看当前默认，或用 `mp.set_start_method("spawn")` 显式指定。

---

## 3. 让多进程真正“并行”：`Pool` 与 `map`

一个个手写 `Process` 太累。`Pool`(进程池) 帮你管理固定数量的工作进程，最常用的两个 API：

- `pool.map(func, iterable)`：**阻塞**，返回结果列表，顺序与输入一致。
- `pool.imap` / `imap_unordered`：**惰性**返回迭代器，`unordered` 版本更快但顺序不定。

```python
import multiprocessing as mp

def cpu_heavy(n: int) -> int:
    return sum(i * i for i in range(n))

if __name__ == "__main__":
    data = [100_000, 200_000, 300_000, 400_000]
    with mp.Pool(processes=4) as pool:   # 4 个工作进程
        results = pool.map(cpu_heavy, data)
    print(results)
```

**为什么这里能变快？** 每个 `cpu_heavy` 在独立进程里跑，4 个核真的同时在算。若换成 `threading`，受 GIL 限制这部分几乎不会加速。

---

## 4. 进程间通信：`Queue` 和 `Pipe`

进程之间内存独立，所以**不能直接读写同一个变量**。`multiprocessing` 提供了几种同步原语：

- `Queue`：多生产者/多消费者，天然线程+进程安全。
- `Pipe`：双向管道，一端发一端收，速度快但连接数固定。
- `Value` / `Array`：带锁的共享内存块，适合小规模共享。
- `Manager`：更高级，可共享 `dict`、`list` 等。

下面是 `Queue` 的经典模式：

```python
import multiprocessing as mp

def producer(q: mp.Queue):
    for i in range(5):
        q.put(i)              # 子进程写

def consumer(q: mp.Queue):
    while True:
        item = q.get()        # 子进程读
        if item is None:      # 哨兵(sentinel)，表示生产结束
            break
        print("消费:", item)

if __name__ == "__main__":
    q = mp.Queue()
    pc = mp.Process(target=producer, args=(q,))
    cc = mp.Process(target=consumer, args=(q,))
    pc.start(); cc.start()
    pc.join()
    q.put(None)               # 主进程投递“结束”信号
    cc.join()
```

**工程习惯**：用 `None` 作为哨兵通知消费者退出，是最常见的约定。

---

## 5. 与 GIL 的关系：什么时候该用它？

一句话总结选型思路：

| 场景 | 推荐 |
|---|---|
| CPU 密集（如数值计算、图像处理）| ✅ `multiprocessing` / `Pool` |
| I/O 密集（如网络请求、读写文件）| `threading` 或 `asyncio` 就够 |
| 需要隔离、需要崩溃容错 | ✅ `multiprocessing` |
| 任务很小、调用很频繁 | 慎用，进程启动开销可能抵消收益 |

**关键结论**：多进程解决的是“并行跑满 CPU 核”，而不是“让一切更快”。一定要先判断任务类型。

---

## 6. 一个可运行的综合示例

```python
# 运行环境：Python 3.8+
# 演示：Pool.map 并行 + Queue 回传中间结果

import multiprocessing as mp
import os

def square(x: int) -> int:
    return x * x

def emit(x: int, q: mp.Queue):
    q.put((os.getpid(), x, x * x))

if __name__ == "__main__":
    mp.set_start_method("spawn", force=True)  # 跨平台一致

    with mp.Pool(4) as pool:
        print(pool.map(square, [1, 2, 3, 4, 5]))

    q = mp.Queue()
    procs = [mp.Process(target=emit, args=(i, q)) for i in range(5)]
    for p in procs: p.start()
    for p in procs: p.join()

    while not q.empty():
        print(q.get())
```

---

## 7. 动手练习

**任务**：写一个脚本 `pi_mp.py`，用蒙特卡洛(Monte Carlo)方法估算 π。

要求：
1. 写一个函数 `estimate(n)`，随机撒 `n` 个点(x, y)，x, y ∈ [-1, 1]，返回落在单位圆内的比例 × 4。
2. 用 `mp.Pool` 并行执行 8 个子任务，每个任务撒 1,000,000 个点，最后对 8 个结果求平均，作为 π 的估计值。
3. 打印：
   - 每个子任务返回的估计值
   - 最终平均值
   - 与 `math.pi` 的误差
4. 计时：分别用 **串行 for 循环** 和 **Pool** 跑同样的总点数，比较耗时，写下你的观察。

提示：8 × 100 万 = 800 万点，串行可能需要数秒。

完成后请回答一句话：在你机器上多进程比串行快了多少倍？如果你的机器只有 4 核，为什么加速比不会达到 8？

## py.mp.pool

# `multiprocessing.Pool`：让 Python 真正并行起来

## 一句话直觉

当你有 100 张图片要处理后分类、1000 个网页要下载、10 万条数据要做数值计算时，**`multiprocessing.Pool`（进程池）就是把这堆活按 CPU 核数分工、并自动回收结果的“包工头”**。

---

## 1. 为什么需要它？从 GIL 说起

Python 有一个名叫 **GIL（Global Interpreter Lock，全局解释器锁）** 的机制：同一时刻，一个 Python 进程里**只允许一个线程执行 Python 字节码**。所以：

- 用 `threading` 做 CPU 密集任务（大量计算）→ 毫无加速，甚至更慢。
- 用 `multiprocessing` 开多个**进程** → 每个进程有独立的解释器和 GIL，可以真正跑满多核 CPU。

> 结论：I/O 密集（网络、磁盘）用线程或 asyncio；**CPU 密集（计算、图像处理）用 `multiprocessing`**。

```python
# 演示：单进程 vs 多进程做 CPU 密集任务
import time
from multiprocessing import Pool

def cpu_task(n):
    # 纯计算任务，用来烧 CPU
    return sum(i * i for i in range(n))

if __name__ == "__main__":
    N = 2_000_000
    data = [N] * 8

    t0 = time.time()
    [cpu_task(x) for x in data]
    print("串行耗时:", round(time.time() - t0, 2), "秒")

    t0 = time.time()
    with Pool() as pool:                 # 默认使用 os.cpu_count() 个进程
        pool.map(cpu_task, data)
    print("进程池耗时:", round(time.time() - t0, 2), "秒")
```

在多核机器上，进程池版本通常能快数倍。

---

## 2. 进程池的核心 API：`Pool`

`multiprocessing.Pool` 的用法非常像一个“任务调度器”：你只管把 **函数** 和 **一批数据** 交进去，它负责拆分、分发、收集。

最常用的四个方法：

| 方法 | 作用 | 是否阻塞 | 返回 |
|---|---|---|---|
| `map(func, iterable)` | 批量映射，保持顺序 | 阻塞 | 结果列表 |
| `imap(func, iterable)` | 惰性版 map | 不阻塞 | 迭代器 |
| `apply(func, args)` | 单次调用 | 阻塞 | 结果 |
| `apply_async(func, args)` | 单次异步调用 | 不阻塞 | `AsyncResult` |

、`imap_unordered`、`starmap` 等是常见变体：

- `imap_unordered`：结果顺序＝完成顺序（适合只关心结果不关心顺序的场景，更快）。
- `starmap`：参数是 (`args`, `kwargs`) 元组序列时使用，等价于对多参数函数做 map。

```python
from multiprocessing import Pool

def square(x):
    return x * x

def power(base, exp):
    return base ** exp

if __name__ == "__main__":
    with Pool(processes=4) as pool:          # 指定 4 个进程
        # 1) map：标准批量映射
        print(pool.map(square, range(5)))    # [0, 1, 4, 9, 16]

        # 2) starmap：多参数版本
        print(pool.starmap(power, [(2, 3), (3, 3)]))  # [8, 27]

        # 3) apply_async：异步提交，稍后取结果
        res = pool.apply_async(square, (10,))
        print(res.get(timeout=5))            # 100
```

注意：`if __name__ == "__main__":` **必须加**，否则在 Windows / macOS 上会无限递归创建进程（后面“误区”章节详解）。

---

## 3. 并行 + 惰性：`imap` 与结果流

当输入数据很大（比如读一个巨大的日志文件），`map` 会把所有结果先算完再返回；而 `imap` 返回一个**迭代器**，谁先完成谁先产出，内存更省，用户体验更好。

```python
import time
from multiprocessing import Pool

def slow_square(x):
    time.sleep(0.2)          # 模拟耗时任务
    return x * x

if __name__ == "__main__":
    with Pool(4) as pool:
        # 谁先算完谁先返回（完成顺序可能乱序）
        for result in pool.imap_unordered(slow_square, range(8)):
            print("收到结果:", result)
```

`imap` 保序，`imap_unordered` 更快。选择哪个取决于你是否需要顺序。

---

## 4. 共享数据与“不可 pickle”问题

进程之间**不共享内存**，参数和返回值都要通过 **pickle（Python 对象序列化）** 传过去。这意味着：

- 传过去的函数和参数，**必须能被 pickle**。
- 顶层函数、普通变量没问题；
- **lambda、闭包、本地定义的函数、打开的 file 对象、数据库连接、锁** 通常不行。

```python
from multiprocessing import Pool

# ❌ 错误：lambda 不能被 pickle
try:
    with Pool(2) as pool:
        pool.map(lambda x: x * 2, range(5))
except Exception as e:
    print("失败:", type(e).__name__, e)

# ✅ 正确：用顶层命名函数
def double(x):
    return x * 2

if __name__ == "__main__":
    with Pool(2) as pool:
        print(pool.map(double, range(5)))
```

如果确实需要共享状态，可以使用 `Manager`（如 `Manager().dict()` / `Manager().list()`），代价是比普通变量慢。

---

## 5. 如何选择进程数与使用场景

经验法则：

- **CPU 密集型**：`processes = os.cpu_count()` 或稍少一点。
- **I/O 密集型**：进程数可以几十上百，或者干脆用 `ThreadPool`。
- **进程创建有成本**：如果任务非常短小（毫秒级），开进程池的收益可能被通信成本吃掉。

```python
import os
from multiprocessing import Pool

def work(x):
    return x + 1

if __name__ == "__main__":
    # 根据 CPU 核数决定进程数
    n = os.cpu_count() or 1
    with Pool(processes=n) as pool:
        print("使用", n, "个进程, 结果:", pool.map(work, range(5)))
```

---

## 6. 资源管理：`with` 与 `close/join`

推荐使用 `with Pool(...) as pool:`，等价于：

```python
pool = Pool()
try:
    ...
finally:
    pool.close()   # 不再接受新任务
    pool.join()    # 等待所有子进程退出
```

`close()` 表示“不再接新任务”，`join()` 表示“等所有任务做完”。二者缺一都可能让程序卡住或僵尸进程残留。

```python
from multiprocessing import Pool

def f(x):
    return x * 10

if __name__ == "__main__":
    pool = Pool(2)
    try:
        print(pool.map(f, range(4)))
    finally:
        pool.close()
        pool.join()
```

---

## 动手练习

**任务**：本地写一个脚本 `word_count_mp.py`，统计一个目录下所有 `.txt` 文件的总字数。

要求：

1. 使用 `multiprocessing.Pool`，进程数 = `os.cpu_count()`。
2. 用 `glob` 或 `pathlib` 找出目录下所有 `.txt` 文件。
3. 每个进程负责读一个文件并返回 `(文件名, 字数)`，用 `pool.map` 汇总。
4. 打印每个文件的字数，以及所有文件的总字数。
5. **难度加码**：改用 `imap_unordered`，观察输出顺序的变化，并说明为什么在“只要总字数”的场景下这样做可能更快。

提示：读取文件时注意编码，用 `open(path, encoding="utf-8")`。字数统计可用 `len(open(...).read())` 或 `len(text.split())`，两者含义不同——请自己选一个并注释说明。

---

## 常见误区速览

- 忘记 `if __name__ == "__main__":` → Windows/macOS 无限递归。
- 用 `lambda` 或闭包当任务函数 → `PicklingError`。
- CPU 密集却用线程 → 被 GIL 卡死，没加速。
- 忘调用 `pool.close()` / `pool.join()` → 进程泄漏。
- 任务太轻（<1ms）还开进程池 → 通信开销让程序更慢。


---

## 本课题目

### single_choice · None



- [A] start() 会阻塞当前进程，直到子进程执行完毕才返回
- [B] start() 启动子进程，调用后子进程与父进程并发执行，父进程可继续往下走
- [C] start() 必须传入目标函数作为参数，否则会抛出 TypeError
- [D] start() 只能被调用一次，但重复调用不会报错，会静默忽略

**参考答案**：1

**解析**：start() 的作用是启动子进程并使其开始运行，属于非阻塞调用，父进程随后继续执行。重复调用同一个 Process 对象会抛出 RuntimeError，不是静默忽略。

### single_choice · None



- [A] 让子进程立即终止
- [B] 阻塞当前进程，等待该子进程结束后再继续执行
- [C] 把子进程的返回值传递给父进程
- [D] 将子进程加入到一个全局进程池中统一管理

**参考答案**：1

**解析**：join() 用于等待进程结束，是同步手段；它不会终止进程，也不负责传返回值。终止用 terminate()，返回值需要通过 Queue 等机制传递。

### single_choice · None



- [A] p1.join(); p2.join()
- [B] p1.join(); p2.join() 与 p2.join(); p1.join() 结果不同，必须按启动顺序
- [C] 只要调用主进程的 join() 即可
- [D] 必须先 terminate() 再 join()

**参考答案**：0

**解析**：对每个子进程调用 join() 即可等待其结束，先后顺序不影响最终“都结束”的效果，只是阻塞顺序不同。

### single_choice · None



- [A] 必须同时指定 target 和 pid
- [B] target 指定子进程要执行的函数，pid 不是创建进程时手动指定的参数
- [C] target 只能是匿名函数
- [D] target 必须是无参函数，不能传 args

**参考答案**：1

**解析**：创建进程时应通过 target 指定可调用对象，可用 args/kwargs 传参；pid 是只读属性，不是构造参数。

### single_choice · None



- [A] 立刻在主进程中以相同类型抛出
- [B] 子进程打印错误信息并退出，主进程不会自动收到该异常对象
- [C] 被自动忽略，不会有任何输出
- [D] 转换为一个 Queue 消息自动放入父进程

**参考答案**：1

**解析**：子进程异常不会自动传播到父进程；需要在子进程内捕获并通过 IPC 反馈，或检查 exitcode。

### single_choice · None



- [A] 进程未结束时 exitcode 已经是 0
- [B] 进程正常结束通常为 0，异常终止为非 0，进程仍在运行时为 None
- [C] exitcode 只有在调用 terminate() 后才有意义
- [D] exitcode 是字符串类型

**参考答案**：1

**解析**：exitcode 是整数，未结束时为 None，正常退出为 0，非正常终止为非零值。

### single_choice · None



- [A] 在 if __name__ == '__main__': 块外直接创建并启动 Process
- [B] 使用了 Queue
- [C] 使用了 join()
- [D] 使用了 Pool

**参考答案**：0

**解析**：Windows 采用 spawn 启动方式，模块被重新导入，若启动代码在顶层会再次执行，导致重复创建进程。

### single_choice · None



- [A] 唯一标识进程，可用于查找
- [B] 给进程起一个可读的名称，便于调试和日志区分
- [C] 指定子进程要执行的函数名
- [D] 设置进程优先级

**参考答案**：1

**解析**：name 只是可读标签，不保证唯一，也不影响执行逻辑；唯一标识用 pid。

### single_choice · None



- [A] 多进程通过创建独立解释器进程，使 CPU 密集型任务可以真正并行
- [B] 多进程通过让多个线程共享 GIL 来并行
- [C] 多进程只是模拟并行，实际上仍然受 GIL 限制
- [D] 多进程可以替代所有多线程场景且没有额外开销

**参考答案**：0

**解析**：GIL 是每个解释器进程内的锁，多进程各进程独立解释器，因此可并行执行 CPU 密集任务，但进程创建与通信有额外开销。

### single_choice · None



- [A] 数据会自动共享，无需关心
- [B] 每个子进程可能各自拥有一份拷贝，内存占用会成倍增加
- [C] 必须用 global 声明才能访问
- [D] 只能用 one-time 传递，之后无法读取

**参考答案**：1

**解析**：进程内存隔离，子进程会复制或重新构造数据，大数据结构会导致内存开销显著上升，必要时考虑共享内存或内存映射。

### single_choice · None



- [A] 两者完全等价
- [B] 加了 join() 后主进程会阻塞到子进程结束，失去并发效果
- [C] 加了 join() 后子进程不会运行
- [D] 加了 join() 后子进程变成守护进程

**参考答案**：1

**解析**：join() 是同步等待；紧跟 start() 后调用会让父进程一直等到子进程结束，从而只表现为“顺序执行”而非并发。

### single_choice · None



- [A] 两者都共享同一内存空间
- [B] Process 有独立内存空间，Thread 共享同一进程内存
- [C] Process 启动开销比 Thread 小
- [D] Thread 受 GIL 限制，Process 也受同一 GIL 限制

**参考答案**：1

**解析**：进程内存隔离、启动与切换开销更大；线程共享内存但受 GIL 约束。

### single_choice · None



- [A] 把 p.start() 换成 p.run()
- [B] 在 p.start() 之后加上 p.join()
- [C] 在 p.start() 之前加上 p.join()
- [D] 把 Process 换成 Thread

**参考答案**：1

**解析**：join() 会等待子进程结束；start() 前调用 join() 会因进程尚未启动而报错；run() 是同步执行不会并发；换成 Thread 改变的是并发模型而非等待语义。

### single_choice · None



- [A] run() 会启动一个新进程，start() 只是普通函数调用
- [B] run() 在当前进程中同步执行target，start() 才真正创建并启动新进程
- [C] 两者完全等价，只是命名不同
- [D] start() 只能调用一次，run() 可以被自动多次调用

**参考答案**：1

**解析**：run() 只是承载目标代码的方法，直接调用它不会创建新进程；start() 才会真正创建子进程并调用 run()。

### single_choice · None



- [A] 多进程共享内存，但 G 需要声明为 volatile
- [B] 每个子进程有独立的内存空间，对全局变量的修改不会反映到父进程
- [C] G 必须定义为列表才能跨进程修改
- [D] target 函数必须返回新值，父进程才会更新全局变量

**参考答案**：1

**解析**：多进程不共享内存，子进程对全局变量的修改只在其自身地址空间内有效。跨进程通信需要用 Queue、Pipe 或共享内存等机制。

### single_choice · None



- [A] daemon=True 的进程会在主进程结束后被自动终止
- [B] daemon=True 的进程必须调用 join() 才能启动
- [C] 守护进程不能调用 start()
- [D] 守护进程会自动把返回值传给父进程

**参考答案**：0

**解析**：守护进程随主进程结束而终止，适合后台辅助任务；它依然需要 start() 启动，也不会自动传递返回值。

### single_choice · None



- [A] 放在函数内部即可
- [B] 放在 if __name__ == '__main__': 代码块内
- [C] 放在模块最顶层的全局作用域
- [D] 放在 try/except 中

**参考答案**：1

**解析**：Windows 使用 spawn 方式启动子进程，会重新导入主模块；将创建进程的代码放在 if __name__ == '__main__': 下可避免无限递归创建。

### single_choice · None



- [A] 返回一个布尔值，表示进程是否仍在运行
- [B] 返回进程的退出码
- [C] 返回子进程的 PID
- [D] 返回子进程运行了多长时间

**参考答案**：0

**解析**：is_alive() 返回进程是否存活；退出码用 exitcode，PID 用 pid 属性。

### single_choice · None



- [A] 立即变成僵尸进程并永久存在
- [B] 被强制终止，随后可通过 join() 回收资源
- [C] 变成守护进程继续在后台运行
- [D] 自动重启一个新的子进程

**参考答案**：1

**解析**：terminate() 会发送终止信号，之后应调用 join() 等待其真正结束并回收资源。

### single_choice · None



- [A] 直接读写同一个全局字典
- [B] 使用 multiprocessing.Queue
- [C] 使用模块级变量
- [D] 使用 os.environ 在运行时修改

**参考答案**：1

**解析**：Queue 是进程安全的通信机制；全局字典、模块变量在不同进程中互不共享；os.environ 的修改通常不会同步到其他进程。

### single_choice · None



- [A] Pool 只能在 Linux 上创建，Windows 上不可用
- [B] Pool(processes=n) 中 n 表示最多同时运行的子进程数量，默认取 os.cpu_count()
- [C] Pool 创建的进程是守护线程，主进程退出后它们会自动被回收但结果会丢失
- [D] Pool 只能通过 with 语句使用，否则无法工作

**参考答案**：1

**解析**：Pool 的 processes 参数指定工作进程数量，默认值取自 os.cpu_count()。Pool 是跨平台的，且并非必须使用 with（但推荐用它确保资源释放）。

### single_choice · None



- [A] [1, 4, 9, 16]
- [B] [1, 2, 3, 4]
- [C] [1, 4, 9, 16, 25]
- [D] 抛出 TypeError

**参考答案**：0

**解析**：p.map 会把可迭代对象中的每个元素依次传给 square，并按输入顺序返回结果列表，因此是 [1, 4, 9, 16]。

### fill_blank · None



**参考答案**：["starmap", "starmap()"]

**解析**：starmap 会把每个元组解包后作为位置参数传给目标函数；map 则把每个元素当成单个参数传入。

### fill_blank · None



**参考答案**：["__name__"]

**解析**：Windows 使用 spawn 启动子进程，会重新导入主模块，若不加 if __name__ == '__main__' 保护，子进程导入时会再次执行创建 Pool 的代码。

### code_reading · None



**参考答案**：输出 caught: bad。因为 map 在汇总所有子任务结果时会把子进程中抛出的异常重新抛出到主进程，捕获后打印 'caught: bad'，整个 map 调用不会返回结果列表。

**解析**：Pool 的子进程异常会通过内部机制传回主进程，map 在收集结果时重新抛出，所以需要 try/except 处理，且整个批次会因一个异常而失败。

### code_reading · None



**参考答案**：输出 9 1 4。imap 按输入顺序返回结果，输入 [3, 1, 2] 对应平方 [9, 1, 4]，即使某些任务先完成，也仍按输入次序产出。

**解析**：imap 返回迭代器，产出顺序与输入顺序一致，只是不需要等待全部完成即可迭代。

### scenario · None



**解析**：推荐使用 pool.imap 或 imap_unordered 搭配 chunksize，返回迭代器按完成情况逐步消费结果，避免一次性加载所有结果；对每条结果做错误捕获；若需要对应输入索引，可传入带索引的元组或使用 starmap。

### scenario · None



**解析**：Windows 使用 spawn 方式启动子进程，会重新导入主模块，如果没有 if __name__ == '__main__' 保护，创建 Pool 的代码会被子进程再次执行，导致无限递归或崩溃。修复方法是将 Pool 创建和主逻辑放入 if __name__ == '__main__': 块中。

### single_choice · None



- [A] 函数可以是任意嵌套的闭包，Pool 会自动序列化
- [B] 函数必须是模块顶层可导入的定义，lambda 和局部函数通常不能被 pickle
- [C] 只要函数没有参数就能被 pickle
- [D] 只有内置函数才能被 Pool 使用

**参考答案**：1

**解析**：Pool 通过 pickle 把任务函数和参数传给子进程，因此函数必须能按模块路径找到，lambda 和嵌套函数通常不可 pickle。

### single_choice · None



- [A] pool.map
- [B] pool.apply
- [C] pool.imap_unordered
- [D] pool.close

**参考答案**：2

**解析**：imap_unordered 返回迭代器，哪个任务先完成就先产出结果，适合不关心顺序、希望尽快消费结果的场景。

### multi_choice · None



- [A] 被提交的函数是定义在函数内部的嵌套函数
- [B] 子进程任务修改了全局变量，主进程期望看到变化
- [C] 在 Windows 上没有把创建 Pool 的代码放入 __main__ 保护块
- [D] 任务函数返回可 pickle 的对象

**参考答案**：[0, 1, 2]

**解析**：嵌套函数不可 pickle；子进程有独立内存，全局变量修改不会同步到主进程；Windows 上缺少保护块会导致递归创建进程。返回可 pickle 的对象是正常且必须的，不会导致失败。

### fill_blank · None



**参考答案**：["close", "close()"]

**解析**：close() 停止接收新任务并通知工作进程在完成剩余任务后退出，随后调用 join() 等待所有工作进程结束。

### single_choice · None



- [A] map 返回列表并等待全部完成，imap 返回迭代器，可边完成边产出结果
- [B] map 只能处理一个参数，imap 可以处理多个参数
- [C] imap 只能在 Windows 上使用，map 只能在 Linux 上使用
- [D] 两者完全等价，只是命名不同

**参考答案**：0

**解析**：map 会阻塞直到所有任务完成并返回完整列表；imap 返回一个迭代器，任务完成一个就可以取出一个，内存占用更友好。

### code_reading · None



**参考答案**：输出 11 21。apply 是同步的，直接返回 11；apply_async 返回 AsyncResult，调用 get() 阻塞等待结果得到 21。

**解析**：apply 阻塞到结果返回；apply_async 立即返回对象，get() 时才等待并取出结果。

### single_choice · None



- [A] pool.map(add, [1, 3], [2, 4])
- [B] pool.starmap(add, [(1, 2), (3, 4)])
- [C] pool.map(add, [(1, 2), (3, 4)])
- [D] pool.apply(add, [(1, 2), (3, 4)])

**参考答案**：1

**解析**：starmap 会把每个元组解包后作为位置参数传给函数。map 只接受一个可迭代对象，pool.map(add, [(1,2),(3,4)]) 会把元组当成单个参数传入，导致 add 少一个参数报错。

### single_choice · None



- [A] apply 是非阻塞的，apply_async 是阻塞的
- [B] apply 会阻塞直到任务完成并返回结果，apply_async 立即返回 AsyncResult 对象
- [C] 两者都返回 AsyncResult 对象
- [D] apply_async 不能设置回调函数

**参考答案**：1

**解析**：apply 是同步阻塞调用，直接返回结果；apply_async 立即返回 AsyncResult，可以通过 .get() 拿结果，并支持 callback/error_callback。

### single_choice · None



- [A] result.value()
- [B] result.get()
- [C] result.fetch()
- [D] result()

**参考答案**：1

**解析**：apply_async 返回 AsyncResult，调用其 get() 方法获取计算结果；若任务未完成，get() 会阻塞。

### single_choice · None



- [A] close() 会立即终止所有工作进程，terminate() 会等待任务完成后再关闭
- [B] close() 停止接收新任务并等待已提交任务完成，terminate() 立即停止所有工作进程
- [C] 两者作用完全相同
- [D] close() 只能对 map 使用，terminate() 只能对 apply_async 使用

**参考答案**：1

**解析**：close() 阻止继续提交任务，之后需要 join() 等待所有已提交任务完成；terminate() 则立即中止工作进程，未完成的任务会丢失。

### single_choice · None



- [A] [0, 1, 2]
- [B] [1, 2, 3]
- [C] [1, 1, 1]
- [D] 运行时报错

**参考答案**：1

**解析**：map 将 0、1、2 分别传入 f，各自加 1，按输入顺序返回 [1, 2, 3]。

### multi_choice · None



- [A] Pool 中的任务是分发到多个独立的操作系统进程上执行的，可绕过 GIL
- [B] Pool 对象可以通过 with 语句管理，退出时会自动调用 terminate
- [C] map 和 apply 都会阻塞，直到对应任务完成
- [D] Pool 中的子进程可以共享父进程的内存变量并直接修改它们
- [E] Pool 的进程池大小可以在运行时动态增大

**参考答案**：[0, 2]

**解析**：Pool 使用独立进程绕过 GIL（A 正确）；map 和 apply 都是同步阻塞调用（C 正确）。with 退出时调用的是 terminate 还是 close+join 取决于实现细节，但主要是释放资源；子进程有独立内存空间，不能直接共享修改变量；Pool 大小通常在创建时固定。

### multi_choice · None



- [A] 对 apply_async 使用 error_callback 处理异常
- [B] 对返回的 AsyncResult 调用 get() 时用 try/except 捕获异常
- [C] 使用 terminate() 立即结束池而不调用 join()
- [D] 在函数内部自行捕获异常并返回错误标记

**参考答案**：[0, 1, 3]

**解析**：error_callback 能捕获异步任务中的异常；get() 会重新抛出子进程中的异常，需要 try/except；函数内自捕获也是常见做法。terminate 会直接杀死进程，反而会丢失结果，不能避免异常。
