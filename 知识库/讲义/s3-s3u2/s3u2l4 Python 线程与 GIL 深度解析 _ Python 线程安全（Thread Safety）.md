# s3u2l4 Python 线程与 GIL 深度解析 / Python 线程安全（Thread Safety）

> 来源 `content/lessons/s3u2l4.json`

## py.thread.gil_detail

# py.thread.gil_detail：Python 线程与 GIL 深度解析

## 一句话直觉

学它是因为：**你以为开了 10 个线程就能让 Python 计算快 10 倍，结果发现比单线程还慢——这不是你的错，是 GIL（Global Interpreter Lock，全局解释器锁）在“作妖”。** 不理解它，你就无法正确决定什么时候用线程、什么时候用进程、什么时候用 asyncio。

---

## 1. 什么是 GIL？先把“锁”这件事讲清楚

Python 解释器（这里指 CPython，官方实现）内部有一把**全局互斥锁**，任何时刻**只允许一个线程执行 Python 字节码（bytecode）**。

注意关键词：
- **全局**：进程内所有线程共享同一把锁。
- **字节码级**：它锁的是“Python 虚拟机执行指令”这件事，不是你的整段代码。
- **互斥**：同一时刻只能有一个线程“持有”它。

所以从 CPU 角度看，CPython 的纯 Python 计算**天生是串行的**：`thread1` 执行一会儿 → 释放 GIL → `thread2` 拿到并执行一会儿 → 再切换回来……

> 直觉类比：一个厨房只有一把菜刀（GIL）。10 个厨师（线程）轮流用这把刀切菜，谁也快不了，还要花时间交接刀。

```python
import threading

counter = 0  # 全局计数器

def add_many():
    global counter
    for _ in range(1_000_000):
        counter += 1  # 每次 += 都会反复获取/释放 GIL

threads = [threading.Thread(target=add_many) for _ in range(4)]
for t in threads: t.start()
for t in threads: t.join()

print("期望:", 4_000_000, "实际:", counter)  # 实际几乎不可能等于期望值
```

运行后你会发现两个现象：
1. 结果**远小于** 4,000,000（因为 `counter += 1` 不是原子操作）。
2. 总耗时**和单线程差不多**甚至更慢（GIL 切换开销）。

这就暴露了 GIL 的两大副作用：**不能并行计算** + **不保证复合操作的原子性**。

---

## 2. GIL 的切换机制：为什么“看起来像并行”？

CPython 并不是让一个线程霸占 GIL 直到结束，它会周期性释放：

- **基于时间片**：默认每 **5 毫秒**（`sys.setswitchinterval()` 可调）尝试释放一次，让其他线程有机会。
- **遇到阻塞调用**：如 `time.sleep`、文件 IO、网络 IO、`socket.recv`，**主动释放 GIL**，让别人跑。
- **C 扩展可以显式释放**：NumPy、PyTorch 的多数算子内部会调 `Py_BEGIN_ALLOW_THREADS` 主动放锁。

这解释了为什么 **IO 密集（I/O-bound）任务用线程仍然有效**：等待磁盘/网络时，GIL 是“空闲”的，其他线程能用。

```python
import threading, time

def io_task(n):
    time.sleep(1)          # 阻塞期间 GIL 被释放，其他线程可以跑
    return n * n

start = time.perf_counter()
threads = [threading.Thread(target=io_task, args=(i,)) for i in range(5)]
for t in threads: t.start()
for t in threads: t.join()
print(f"5 个 sleep(1) 线程总耗时: {time.perf_counter() - start:.2f}s")  # 约 1s，不是 5s
```

对比：如果把 `io_task` 换成 CPU 密集循环，**总耗时 ≈ 单线程的 N 倍**（甚至更差）。

---

## 3. CPU 密集 vs IO 密集：一张决策表

| 任务类型 | 例子 | 推荐方案 | 原因 |
|---|---|---|---|
| IO 密集 | 网络爬虫、文件读写、数据库查询 | `threading` / `asyncio` | 阻塞时释放 GIL |
| CPU 密集（纯 Python） | 数值迭代、字符串处理 | `multiprocessing` / `concurrent.futures.ProcessPoolExecutor` | 绕开 GIL，多核并行 |
| CPU 密集（C 扩展已放锁） | NumPy 矩阵乘法、PyTorch 训练 | `threading` 也有效 | C 代码内部释放 GIL |
| 需要极致并发 | 高并发网关、海量连接 | `asyncio` | 单线程事件循环，无锁开销 |

```python
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import time

def cpu_work(n):
    s = 0
    for i in range(n): s += i*i
    return s

N = 5_000_000

# 线程池：受 GIL 限制，几乎无加速
start = time.perf_counter()
with ThreadPoolExecutor(4) as ex:
    list(ex.map(cpu_work, [N]*4))
print(f"线程池 4 任务: {time.perf_counter()-start:.2f}s")

# 进程池：真正并行，通常加速 3~4 倍
start = time.perf_counter()
with ProcessPoolExecutor(4) as ex:
    list(ex.map(cpu_work, [N]*4))
print(f"进程池 4 任务: {time.perf_counter()-start:.2f}s")
```

经验法则：**看到 `for` 循环里都是 Python 运算 → 用进程；看到 `requests.get`/`open`/`sleep` → 用线程。**

---

## 4. GIL 与线程安全：别把“有 GIL”当成“免死金牌”

新手常犯的误区：**以为有 GIL 就不用加锁**。错。

GIL 保证的是“一条字节码”的原子性，但你的业务逻辑通常是**多条字节码的组合**，中途随时可能被切换。典型例子：

- `counter += 1` 实际是 `LOAD / ADD / STORE` 三条字节码，可被切。
- `list.append` 是原子的（C 实现），但 `if not in list: list.append` 不是。
- 多字段更新（转账扣款）显然不是原子的。

```python
import threading

balance = 0
lock = threading.Lock()

def deposit():
    global balance
    for _ in range(100_000):
        with lock:              # 必须自己加锁保护复合操作
            balance += 1

ts = [threading.Thread(target=deposit) for _ in range(4)]
for t in ts: t.start()
for t in ts: t.join()
print("加锁后:", balance)   # 稳定输出 400000
```

规则：**读写共享可变状态（mutable state）时，要么使用时序严格的原子结构（`queue.Queue`），要么加锁。** 不要依赖 GIL 来“免费”保证线程安全。

---

## 5. GIL 的未来：free-threaded Python

- **PEP 703**（Python 3.13 起）引入实验性的 **free-threaded（无 GIL）** 构建，可通过 `python3.13t` 或安装选项启用。
- 该模式下，多线程可以真正并行执行字节码，但需要更细粒度的锁，单线程性能略降（目前约 5%–10%）。
- **PEP 779** 在 3.14 将其升级为官方支持（但仍非默认）。
- 生态（NumPy、Cython、各类 C 扩展）正在逐步适配，短期内**不能假设“GIL 没了”**。

实务建议：写代码时**按“GIL 存在”来设计**（IO 用线程/异步、CPU 用多进程），这样未来无论 GIL 是否移除，代码都不会崩。

---

## 动手练习

**任务：用实验数据说服你自己——“线程不适合 CPU 密集，适合 IO 密集”。**

1. 写两个函数：
   - `cpu_bound(n)`：纯 Python 循环累加，例如 `sum(i*i for i in range(n))`，`n=10_000_000`。
   - `io_bound()`：调用 `time.sleep(0.5)`。
2. 分别测三种运行方式的耗时（用 `time.perf_counter`）：
   - 串行执行 4 次。
   - 用 `threading.Thread` 开 4 个线程并发。
   - 用 `concurrent.futures.ProcessPoolExecutor(4)` 并发。
3. 输出的表格应类似：

   | 任务 | 串行 | 4 线程 | 4 进程 |
   |---|---|---|---|
   | CPU 密集 ×4 | T | ≈T（受 GIL 限制） | ≈T/4 |
   | IO 密集 ×4 | 2.0s | ≈0.5s | ≈0.5s（进程创建开销更大） |

4. 在代码注释里写下一句你从数据中得到的结论。

**拓展（可选）**：把 `cpu_bound` 换成一个 NumPy 的大矩阵乘法，再测一遍线程版本，观察是否加速——用来验证“C 扩展释放 GIL”这条规律。

---

## 一页总结

- GIL = CPython 内部的全局互斥锁，保证同一时刻只有一个线程跑字节码。
- 结果：**纯 Python CPU 密集任务无法用线程并行**；**IO 密集任务线程照样有效**。
- GIL ≠ 线程安全：复合操作仍需加锁。
- 实践准则：**IO → 线程/异步；CPU → 多进程；用 C 扩展 → 线程可以。**
- 未来：PEP 703/779 让 free-threaded Python 成为可能，但短期内请按“GIL 存在”写代码。

## py.thread.thread_safety

# Python 线程安全（Thread Safety）

## 一句话直觉

当多个线程（thread）同时读写同一份数据时，如果没有协调机制，结果就会像两个人同时往同一个户口本上写名字——最后谁的名字都没写全。**线程安全**就是让多个线程在共享数据面前"排队办事"的规则。

---

## 第 1 节：为什么需要线程安全

Python 的线程（thread）由 `threading` 模块提供。多个线程共享同一进程的内存空间，因此它们可以同时访问同一个变量、同一个列表、同一个对象。

问题在于：**`x += 1` 不是原子操作（atomic operation）**。它实际分三步：读取 `x`、计算 `x+1`、写回 `x`。如果两个线程在"读取"和"写回"之间交错执行，其中一个线程的修改就会被覆盖——这叫做**竞态条件（race condition）**。

```python
import threading

counter = 0

def worker():
    global counter
    for _ in range(100_000):
        counter += 1   # 非原子：读-改-写三步可能被打断

threads = [threading.Thread(target=worker) for _ in range(2)]
for t in threads: t.start()
for t in threads: t.join()

print(counter)  # 期望 200000，实际往往小于该值
```

---

## 第 2 节：GIL 不是线程安全的护身符

很多人听说"Python 有全局解释器锁（GIL, Global Interpreter Lock），所以不用管线程安全"。这是**误解**。

GIL 保证的是"同一时刻只有一个线程执行 Python 字节码（bytecode）"，但它**不保证多条字节码组成的操作是原子的**。`counter += 1` 会被切成多条字节码，GIL 可能在任意字节码之间切换线程。

```python
import dis

def inc():
    global counter
    counter += 1

dis.dis(inc)
# LOAD_GLOBAL counter
# LOAD_CONST  1
# BINARY_OP   +=
# STORE_GLOBAL counter
# 四条字节码之间都可能发生线程切换
```

结论：**GIL 只保护单个字节码，不保护复合操作。**

---

## 第 3 节：用 Lock 保护临界区

最基础的线程安全工具是**互斥锁（mutex）**，在 Python 中就是 `threading.Lock`（互斥锁）。加锁后，同一时刻只有一个线程能进入**临界区（critical section）**。

推荐用 `with lock:` 语法，它会自动在异常时释放锁，避免死锁。

```python
import threading

counter = 0
lock = threading.Lock()

def worker():
    global counter
    for _ in range(100_000):
        with lock:          # 进入临界区
            counter += 1    # 现在这三步是"打包"的

threads = [threading.Thread(target=worker) for _ in range(2)]
for t in threads: t.start()
for t in threads: t.join()

print(counter)  # 稳定输出 200000
```

---

## 第 4 节：不止是 Lock——常见线程安全工具

- **`threading.RLock`（可重入锁）**：同一个线程可以多次获取，适用于递归函数。
- **`threading.Semaphore`（信号量）**：限制同时进入的线程数量（比如连接池）。
- **`queue.Queue`**：自带锁的线程安全队列，生产者-消费者模式首选。
- **`collections.defaultdict` 等内置容器**：单个方法通常原子，但"检查-然后-修改"（check-then-act）仍需要锁。

```python
import threading, queue

q: queue.Queue[int] = queue.Queue()
results = []

lock = threading.Lock()

def producer():
    for i in range(5):
        q.put(i)          # 内部已加锁
    q.put(None)           # 结束信号

def consumer():
    while True:
        item = q.get()
        if item is None: break
        with lock:
            results.append(item * 2)

t_prod = threading.Thread(target=producer)
t_cons = threading.Thread(target=consumer)
t_prod.start(); t_cons.start()
t_prod.join(); t_cons.join()

print(sorted(results))  # [0, 2, 4, 6, 8]
```

---

## 第 5 节：装饰器模式统一加锁

工程中常常需要"给任意函数加锁"。可以用装饰器（decorator）把锁注入进去，避免散落各处、忘记加锁。

```python
import threading
from functools import wraps

_lock = threading.Lock()

def with_lock(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        with _lock:
            return func(*args, **kwargs)
    return wrapper

@with_lock
def sum_threadsafe(numbers: list[float]) -> float:
    '''以线程安全的方式对一组数求和。'''
    return sum(numbers)

print(sum_threadsafe([1.1, 2.2, 3.3]))  # 6.6
```

---

## 动手练习

**任务：线程安全的银行账户**

1. 写一个 `Account` 类，内部保存 `balance: int`（初始 0），并提供 `deposit(n)` 与 `withdraw(n)` 方法；
2. 要求两个方法都使用 `threading.Lock` 保护，且 `withdraw` 在余额不足时抛出 `ValueError`；
3. 启动 10 个线程，每个线程执行 10000 次 deposit(1)，最后断言 `balance == 100_000`；
4. 再用 10 个线程，每个线程随机执行 deposit/withdraw，最终余额应等于所有操作净和；跑 100 次，验证结果始终一致。

提示：
- 用 `with self._lock:` 包住对 `self.balance` 的读改写；
- 不要在持有锁时调用可能阻塞很久的外部 I/O；
- 不要在 `with` 块内 `raise` 之后再访问共享资源。

```python
import threading
from dataclasses import dataclass, field


@dataclass
class Account:
    balance: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def deposit(self, n: int) -> None:
        with self._lock:
            self.balance += n

    def withdraw(self, n: int) -> None:
        with self._lock:
            if self.balance < n:
                raise ValueError("insufficient funds")
            self.balance -= n


def run_once() -> int:
    acc = Account()

    def deposit_worker():
        for _ in range(10_000):
            acc.deposit(1)

    threads = [threading.Thread(target=deposit_worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return acc.balance


if __name__ == "__main__":
    # 每次都应该输出 100000，而不是随机偏小
    for _ in range(5):
        print(run_once())
```


---

## 本课题目

### single_choice · None



- [A] 用 threading 启动多个线程，各自对一个大整数做大量加减乘除运算
- [B] 用 threading 启动多个线程，各自调用 time.sleep(1)
- [C] 用 threading 启动多个线程，各自等待一个网络返回结果
- [D] 用 asyncio 启动多个协程，各自等待文件读取完成

**参考答案**：0

**解析**：GIL 规定同一时刻只有一个线程执行 Python 字节码，因此纯 Python CPU 密集计算的多线程无法并行利用多核。sleep、网络等待、文件读取等待都会释放 GIL，因此不是最可能受 GIL 限制的情形。

### single_choice · None



- [A] 因为 GIL 只限制多进程，不限制多线程
- [B] 因为 GIL 会在执行阻塞式 I/O 等操作时被释放，其他线程可以继续运行
- [C] 因为只要线程数超过 CPU 核数，GIL 就会自动消失
- [D] 因为 threading 模块默认会关闭 GIL

**参考答案**：1

**解析**：GIL 并不能一概否定多线程：线程执行会释放 GIL 的阻塞操作（如 I/O 等待）时，其他线程可继续运行，所以 I/O 密集型任务仍可能从多线程受益。其他选项是对 GIL 作用范围的误读。

### single_choice · None



- [A] list.append 是复合操作，所以 GIL 保证了它一定线程安全
- [B] list.append 主要由单条或少量字节码对应的 C 操作完成，受 GIL 保护，因此常见情况下不易出错；但这不等于所有复合操作都安全
- [C] list.append 会主动释放 GIL，因此多个线程可以同时修改列表
- [D] Python 的 list 会自动为每个元素加锁

**参考答案**：1

**解析**：append 对应的 C 操作在持有 GIL 时执行，常见情况不易被交错；但不能推广为“GIL 让所有操作线程安全”，更复杂复合操作仍需同步。

### single_choice · None



- [A] 它可以关闭 GIL，使多个线程同时执行 Python 字节码
- [B] 它可以调整解释器建议的线程切换时间间隔，但不能移除 GIL
- [C] 它只能用于多进程，不能用于多线程
- [D] 它会强制每个线程在固定毫秒数后终止

**参考答案**：1

**解析**：`sys.setswitchinterval` 影响线程切换的时间间隔建议值，不能关闭或移除 GIL，也不会终止线程。

### single_choice · None



- [A] 对超大矩阵做纯 Python 循环乘法
- [B] 从多个远程 HTTP 接口并发下载数据并等待响应
- [C] 计算大整数的高次幂
- [D] 对一张大图像逐像素执行自定义 Python 变换

**参考答案**：1

**解析**：等待网络响应时线程会释放 GIL，其他线程可以继续发起或处理请求，因此 I/O 密集型任务适合多线程。纯 Python CPU 密集任务受 GIL 限制，更适合多进程。

### single_choice · None



- [A] 在函数一开始调用 `threading.acquire_gil()` 把 GIL 永久锁住
- [B] 在函数执行计算期间使用 `Py_BEGIN_ALLOW_THREADS` / `Py_END_ALLOW_THREADS` 释放 GIL，并确保不访问受 GIL 保护的 Python 对象状态
- [C] 把函数注册到 `sys.gil_exempt` 列表
- [D] 让函数返回一个特殊对象，解释器会自动为它关闭 GIL

**参考答案**：1

**解析**：C 扩展可通过 `Py_BEGIN_ALLOW_THREADS` / `Py_END_ALLOW_THREADS` 在计算期间释放 GIL，但在此期间不能随意操作需要 GIL 的 Python 对象。其他选项虚构了 API。

### single_choice · None



- [A] GIL 是用户可调用的锁对象，而普通锁是解释器内部机制
- [B] GIL 是解释器内部的全局互斥机制，普通锁是用户代码中用于保护临界区的同步原语
- [C] GIL 可以替代所有普通锁，因此用户代码不应再使用 Lock
- [D] 普通锁会释放 GIL，而 GIL 不会影响普通锁

**参考答案**：1

**解析**：GIL 属于解释器内部机制，普通锁如 `threading.Lock` 是用户级同步工具，用于保护复合操作。GIL 不能替代用户锁。

### single_choice · None



- [A] GIL 保证所有线程严格按创建顺序轮流执行，是绝对公平的
- [B] GIL 本身不保证线程调度的公平性，某个线程可能在释放后很快再次获得 GIL
- [C] GIL 由操作系统内核直接实现，因此调度完全由内核决定
- [D] GIL 会把执行权平均分配给每个线程，每个线程运行完全相同的时间

**参考答案**：1

**解析**：GIL 只提供互斥，不保证公平轮转；调度行为受解释器和操作系统影响，某个线程可能连续获得 GIL。

### single_choice · None



- [A] 其他线程自动被操作系统杀死了
- [B] 该 C 扩展函数没有在计算期间释放 GIL，导致其他线程无法获取 GIL 执行字节码
- [C] CPython 规定 C 扩展函数运行时必须独占解释器，这是设计限制
- [D] GIL 在检测到 C 扩展后会从全局锁变成全局禁用

**参考答案**：1

**解析**：如果 C 扩展长时间持有 GIL 且不释放，其他线程就没有机会获取 GIL，表现为线程被“卡住”。这不是 CPython 强制 C 扩展独占解释器的规定。

### single_choice · None



- [A] 获取普通锁会隐含释放 GIL，因此不会造成死锁
- [B] 普通锁用于保护用户级临界区；一个线程持有普通锁等待时仍可能持有或释放 GIL，锁的获取和释放不替代 GIL 的作用
- [C] 只要使用普通锁，就不再需要 GIL，GIL 会自动被禁用
- [D] GIL 会在检测到普通锁竞争时自动升级为更细粒度的锁

**参考答案**：1

**解析**：普通锁和 GIL 解决不同层面的问题。普通锁保护用户代码的临界区，GIL 保护解释器内部状态；使用普通锁不会禁用 GIL。

### single_choice · None



- [A] 多进程无法在 Python 中创建
- [B] 多进程会带来进程创建、序列化、内存占用和进程间通信等额外开销，I/O 密集型任务用多线程可能更简单高效
- [C] 多进程会绕过 GIL，因此不安全
- [D] 多进程只能用于 Windows 系统

**参考答案**：1

**解析**：多进程可绕过 GIL，但有额外成本；是否使用应视任务类型而定。I/O 密集型任务可能更适合多线程/异步。

### single_choice · None



- [A] 所有 Python 实现都使用完全相同的 GIL 实现
- [B] CPython 有 GIL；Jython、IronPython 等实现没有同样的 GIL，因此多线程行为可能不同
- [C] 只有 Python 2 有 GIL，Python 3 已完全移除 GIL
- [D] PyPy 没有 GIL，因此其 CPython 兼容行为完全一致

**参考答案**：1

**解析**：GIL 是 CPython 的实现特征；Jython、IronPython 等没有同样的全局锁，所以多线程并行能力不同。Python 3 的 CPython 默认仍有 GIL。

### single_choice · None



- [A] GIL 会阻止多个线程同时访问同一变量，因此增量操作被禁止
- [B] 多线程共享解释器状态，GIL 切换可能发生在字节码之间，使读-改-写不是原子操作
- [C] Python 的 int 是不可变类型，所以不能在线程间共享
- [D] threading.Thread 默认不会同步任何变量，必须手动加 GIL

**参考答案**：1

**解析**：`total += 1` 实际包含读取、加法、写回等多个字节码操作，GIL 可能在字节码之间释放并切换线程，导致丢失更新。GIL 并不保证复合操作原子性，也不是禁止访问共享变量。

### single_choice · None



- [A] GIL 是 Python 语言规范强制要求的，所有 Python 实现都必须有 GIL
- [B] GIL 是 CPython 解释器的一种实现细节，用于保护解释器内部状态
- [C] GIL 可以保证用户程序中所有共享数据访问都是线程安全的
- [D] GIL 会在每个 Python 函数调用结束后立即切换到另一个线程

**参考答案**：1

**解析**：GIL 是 CPython 的实现细节，不是 Python 语言标准的一部分；其他实现如 Jython、IronPython 没有同样的 GIL。它保护解释器内部状态，但不保证用户级复合操作的线程安全，也不会固定在每个函数结束时切换。

### single_choice · None



- [A] 完全无法加速，因为任何函数调用都受 GIL 限制且不会释放
- [B] 可能获得一定加速，因为部分 C 扩展/内置函数在执行计算时会释放 GIL
- [C] 必然比单线程慢两倍，因为 GIL 在函数调用时强制串行化
- [D] 必然获得线性加速，因为 math 模块会自动创建独立解释器

**参考答案**：1

**解析**：部分用 C 实现且声明释放 GIL 的内置或扩展函数在计算时可不持有 GIL，因此可能与其他线程并行。但不能保证完全线性加速，也不是所有函数调用都释放 GIL。

### single_choice · None



- [A] 该线程在睡眠期间仍持续持有 GIL，其他线程无法执行 Python 字节码
- [B] 该线程在进入 sleep 前会释放 GIL，睡眠期间其他线程可以运行
- [C] sleep 会强制终止其他所有线程，直到睡眠结束
- [D] sleep 会关闭 GIL，但只允许主线程继续运行

**参考答案**：1

**解析**：阻塞式等待如 sleep 会使当前线程释放 GIL，让其他线程有机会运行；这也是 I/O 密集型多线程可能有效的原因。

### single_choice · None



- [A] GIL 能防止多个线程同时修改同一个列表，因此 list.append 在多线程下总是安全的
- [B] GIL 不能防止多线程同时执行 `x = x + 1` 这类复合操作产生竞态条件
- [C] 因为 GIL 存在，所以 Python 中不需要任何锁机制
- [D] GIL 会在检测到竞态条件时自动抛出异常

**参考答案**：1

**解析**：GIL 只保证单条字节码层面的互斥，不保证多条字节码组成的复合操作原子性。`x = x + 1` 这类读-改-写仍可能交错，需要锁来保护。

### single_choice · None



- [A] 必须改用多进程，因为只要涉及网络 I/O 就不能用多线程
- [B] 可以用多线程或 asyncio 管理 I/O 等待，同时用多进程承载 CPU 密集的解析部分
- [C] 应该创建尽可能多的线程，因为线程数越多 GIL 越容易被绕过
- [D] 应该在每个线程里手动调用 `sys.setswitchinterval(0)` 来彻底移除 GIL

**参考答案**：1

**解析**：I/O 等待期间 GIL 会释放，因此多线程/异步适合 I/O 密集部分；真正 CPU 密集部分可用多进程绕过 GIL。线程数并非越多越好，也没有可以彻底移除 GIL 的常规开关。

### single_choice · None



- [A] 增加 threading 线程数量，因为线程数一旦超过 CPU 核数就会并行执行字节码
- [B] 使用 multiprocessing 创建多个进程，每个进程有独立的解释器和 GIL
- [C] 在代码开头调用 `threading.disable_gil()`
- [D] 把计算函数加上 `@threading.no_gil` 装饰器

**参考答案**：1

**解析**：每个进程拥有独立的解释器状态和 GIL，因此多进程可以并行使用多核。Python 没有 `threading.disable_gil()` 或 `@threading.no_gil` 这类标准 API。

### single_choice · None



- [A] GIL 只会在当前线程显式调用 `threading.yield_()` 时释放
- [B] GIL 可能在当前线程执行若干字节码后释放，也可能在阻塞操作前释放，具体时机由解释器调度
- [C] GIL 一旦被某个线程获取，就会一直持有到该线程结束
- [D] GIL 只在主线程中生效，子线程不受其约束

**参考答案**：1

**解析**：CPython 会基于字节码计数/时间片等因素在适当时候释放 GIL 并允许其他线程获取，阻塞操作前也会释放；并非必须显式调用某个不存在的方法，也不是线程结束才释放。

### single_choice · None



- [A] 一定是 2000
- [B] 一定是 1000
- [C] 可能小于 2000，因为 `+=` 不是原子操作
- [D] 可能大于 2000，因为线程会重复计数

**参考答案**：2

**解析**：`count += 1` 在字节码层面是 LOAD、ADD、STORE 三步，线程可能在中间被切换，导致丢失更新，因此结果通常小于 2000，绝不会大于 2000。

### single_choice · None



- [A] 有了 GIL，所有 Python 代码都自动是线程安全的
- [B] GIL 只保证单条字节码不被并发执行，复合操作仍可能竞态
- [C] GIL 会在每次函数调用时自动加锁保护共享变量
- [D] 只要用多线程就必须关闭 GIL，否则程序无法运行

**参考答案**：1

**解析**：GIL 保证同一时刻只有一个线程执行字节码，但一个逻辑操作往往由多条字节码组成，线程仍可能在中间被切换，所以复合操作不是线程安全的。

### multi_choice · None



- [A] 竞态只在多个线程写同一共享数据时才可能出现
- [B] 竞态的结果可能依赖线程调度的时序，因而难以复现
- [C] 只要临界区代码很短就不会有竞态
- [D] 使用锁把临界区串行化可以消除该竞态
- [E] 把变量声明为全局会让它自动线程安全

**参考答案**：[0, 1, 3]

**解析**：竞态需要并发写共享数据；其结果依赖调度时序；加锁可消除。代码短不代表原子（如 `+=` 只有三条字节码仍会竞态），全局变量也不会自动安全。

### multi_choice · None



- [A] 单次 `list.append(x)` 调用
- [B] 单个 `dict[key] = value` 赋值
- [C] 「检查 key 是否存在，不存在则写入」这两步组合
- [D] 多个线程并发对同一 list 做「取出并删除最后一个元素」的组合操作
- [E] 对 `threading.local()` 中属于当前线程的属性读写

**参考答案**：[0, 1, 4]

**解析**：单次 append、单次 dict 赋值在 CPython 中是原子的；`threading.local` 数据按线程隔离。检查再写入以及「读+删」都是复合操作，会竞态。

### fill_blank · None



**参考答案**：["GIL", "gil", "Global Interpreter Lock", "global interpreter lock"]

**解析**：GIL（Global Interpreter Lock）是 CPython 的全局解释器锁，作用是让同一时刻只有一个线程执行字节码，但它不保证复合操作的原子性。

### fill_blank · None



**参考答案**：["Lock", "lock", "RLock", "rlock"]

**解析**：`threading.Lock` 是基本互斥锁；需要同一线程可重入时用 `threading.RLock`。配合 `with` 可自动获取和释放。

### fill_blank · None



**参考答案**：["Queue", "queue", "LifoQueue", "PriorityQueue"]

**解析**：`queue.Queue` 内部用锁实现，是典型的生产者-消费者线程安全队列；`LifoQueue`、`PriorityQueue` 同样线程安全。

### code_reading · None



**参考答案**：输出通常小于 400000，且每次运行结果可能不同。因为 `count += 1` 由多条字节码组成（读取、加一、写回），4 个线程会在中间被切换，发生丢失更新，属于竞态条件。用锁（如 with threading.Lock()）或改用 queue 汇总可得到正确结果 400000。

**解析**：该代码展示了共享可变的全局计数器在无同步下的竞态；GIL 不能保护多步操作，故结果不可预测且一般偏小。

### code_reading · None



**参考答案**：会造成死锁：线程 a 已持有 lock，在调用 b() 时再次尝试 acquire 同一把非可重入锁，会永久阻塞。应改用 threading.RLock()，或避免在持锁期间重复获取同一把锁。

**解析**：普通 Lock 不具有可重入性，同一线程重复获取会死锁；RLock 允许同一线程重入计数。

### code_reading · None



**参考答案**：在 put/get 层面是线程安全的，因为 queue.Queue 内部使用锁保护。但 consumer 的 while True 若没有终止条件（如 get(timeout) 或哨兵值）会一直阻塞，这是设计问题而非线程安全问题。

**解析**：queue.Queue 保证队列操作的原子性，是推荐的多线程数据传递方式；但消费循环需要合理的退出机制。

### scenario · None



**解析**：对字典的「读取当前值-加一-写回」是多步复合操作，多线程交错会产生丢失更新；虽然单次 dict 赋值原子、GIL 存在，但复合操作不原子。用互斥锁保护临界区（或用线程安全队列/累加器汇总）即可修复。

### scenario · None



**解析**：文件写操作尤其是多步写入（如分别写时间戳和内容）不是原子的，多线程交错导致输出错乱。可用互斥锁把整条日志写入作为临界区，或让各线程把日志消息放入 queue.Queue，由单独一个写线程串行落盘。

### single_choice · None



- [A] `x = x + 1`
- [B] `x += 1`
- [C] `lst.append(item)`
- [D] 先 `if x not in lst:` 再 `lst.append(x)`

**参考答案**：2

**解析**：`list.append` 由 C 实现且不释放 GIL，单次调用是原子的。`x = x + 1` 和 `x += 1` 是多步操作，检查再追加属于复合操作，都不是原子的。

### single_choice · None



- [A] 仍需加锁，否则读取会得到错误数据
- [B] 不需要加锁，因为只读且对象不可变，不会产生竞态
- [C] 必须改用进程才能安全读取
- [D] 需要把元组转成列表再读才安全

**参考答案**：1

**解析**：竞态发生在至少有一个写者时。不可变对象的只读访问没有写操作，不产生数据竞争，因此无需加锁。

### single_choice · None



- [A] 用普通全局 int 加 `time.sleep(0)` 让线程切换更均匀
- [B] 用 `threading.Lock` 保护累加操作，或用 `queue.Queue` 汇总结果
- [C] 把 int 换成 float，因为浮点运算更快
- [D] 给每个线程设置不同的线程名

**参考答案**：1

**解析**：互斥锁能保证读-改-写三步不被其他线程打断；`queue.Queue` 内部已加锁，是常见的线程安全通信方式。sleep 和线程名都不解决竞态。

### single_choice · None



- [A] 因为 list 不能存储任意类型对象
- [B] 因为 Queue 的 put/get 是线程安全的，list 的 append 与 pop 组合后不是原子的
- [C] 因为 Queue 比 list 访问速度快得多
- [D] 因为 list 只能在单线程中创建

**参考答案**：1

**解析**：`Queue` 内部使用锁，保证生产者-消费者操作安全。list 虽单次 append 原子，但「取出并删除」等多步组合操作会竞态。

### single_choice · None



- [A] 先 `lock.acquire()`，业务代码写在中间，最后不管是否异常都 `lock.release()`
- [B] 用 `with lock:` 上下文管理器包裹临界区
- [C] 在函数开头 acquire，在另一个函数结尾 release
- [D] 只在线程启动时 acquire 一次，之后不再释放

**参考答案**：1

**解析**：`with lock:` 能在异常或提前返回时自动释放锁，避免死锁。手动 acquire/release 容易漏掉 release，跨函数配对更是反模式。

### single_choice · None



- [A] 抛出 SyntaxError
- [B] 自动检测并跳过重复加锁
- [C] 死锁，线程永久阻塞（若锁是非重入的）
- [D] 锁被自动升级为可重入锁

**参考答案**：2

**解析**：普通 `threading.Lock` 不可重入，同一线程再次 acquire 会永久阻塞，形成死锁。需要可重入时应使用 `threading.RLock`。

### multi_choice · None



- [A] 用互斥锁保护所有读-改-写共享状态的临界区
- [B] 尽量使用不可变对象或让每个线程持有独立的数据副本
- [C] 用 `queue.Queue` 在线程间传递数据，而不是共享可变的全局变量
- [D] 为了性能，去掉所有锁并依赖 GIL 保证正确性
- [E] 在临界区里执行耗时的 I/O 或网络请求

**参考答案**：[0, 1, 2]

**解析**：锁、不可变/线程局部数据和线程安全队列都是常见手段。依赖 GIL 无法保证复合操作正确，在临界区做耗时 I/O 会严重降低并发度。

### multi_choice · None



- [A] 两个线程以相反顺序获取两把锁可能造成死锁
- [B] 线程持有锁后等待另一个永远不会到来的条件也可能造成死锁
- [C] 规定全局统一的加锁顺序可以降低死锁风险
- [D] 只要使用多线程就必然死锁，无法避免
- [E] 设置超时（如 `lock.acquire(timeout=...)`）有助于打破某些死锁

**参考答案**：[0, 1, 2, 4]

**解析**：死锁可由循环等待、无限等待等引起；统一加锁顺序、使用超时是常见缓解手段。多线程并不必然死锁，所以 D 错误。
