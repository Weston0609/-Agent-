# s3u2l1 线程基础（Thread Basics）：让程序同时做几件事 / 让多线程不再“撞车”

> 来源 `content/lessons/s3u2l1.json`

## py.thread.thread_basic

# 线程基础（Thread Basics）：让程序同时做几件事

> **一句话直觉**：线程（Thread）是操作系统调度的最小单位，它让一个程序里“同时”跑多段代码——就像一个人可以一边煮饭一边切菜，而不是先切完再煮。

---

## 1. 为什么需要线程？

想象你要下载 10 张图片，如果一张一张下，必须等第 1 张完成才能开始第 2 张。但网络请求大部分时间在**等待**（I/O 阻塞）。

- **单线程（single-thread）**：串行等待，总时间 = 所有等待之和。
- **多线程（multithreading）**：等待时切到另一个线程，总时间 ≈ 最长的一个任务。

线程的价值主要在两处：
1. **I/O 密集（I/O-bound）**：网络、文件、数据库——线程能显著提速。
2. **保持界面响应**：主线程处理 UI，后台线程干活，窗口不会“卡死”。

> ⚠️ 注意：因为 **GIL（Global Interpreter Lock，全局解释器锁）** 的存在，纯 Python 代码的 **CPU 密集（CPU-bound）** 任务用线程几乎不会加速，这种场景应使用 `multiprocessing`。

---

## 2. 最小的线程：`threading.Thread`

Python 标准库用 `threading` 模块提供线程。启动线程只需 3 步：定义函数 → 创建 `Thread` 对象 → `.start()`。

```python
import threading
import time

def worker(name):
    print(f"[{name}] 开始")
    time.sleep(1)          # 模拟 I/O：这里会释放 GIL，其他线程可运行
    print(f"[{name}] 结束")

# 创建两个线程
t1 = threading.Thread(target=worker, args=("A",))
t2 = threading.Thread(target=worker, args=("B",))

t1.start()  # 启动后立即返回，主线程继续往下走
t2.start()

print("主线程：已启动完毕")
t1.join()   # 阻塞主线程，直到 t1 完成
t2.join()
print("主线程：全部线程结束")
```

**关键细节**：
- `.start()` **不会** 等待函数跑完，它只是“把活派出去”。真正的等待是 `.join()`。
- 如果不调用 `.join()`，主线程可能在子线程还在跑时就退出，进程结束，子线程被杀。

---

## 3. 用 `Lock` 保护共享数据

多个线程访问**同一份可写数据**时，会出现**竞态条件（race condition）**：因为 `x += 1` 不是原子操作，实际是「读 → 加 → 写」三步，可能被中途打断。

解决办法：用 `Lock`（互斥锁）把这一段包起来，同一时刻只允许一个线程进入。

```python
import threading

counter = 0
lock = threading.Lock()

def increment(n):
    global counter
    for _ in range(n):
        with lock:              # 进入临界区（critical section）
            counter += 1        # 只有持锁线程能执行这三步

threads = [threading.Thread(target=increment, args=(100_000,)) for _ in range(4)]
for t in threads: t.start()
for t in threads: t.join()

print("预期:", 400_000, "实际:", counter)   # 有锁 → 稳定输出 400000
```

把 `with lock:` 去掉、多跑几次，你就能观察到 counter 小于 400000 的“丢更新”现象——这是最直观的竞态演示。

---

## 4. 用 `ThreadPoolExecutor` 优雅地管理线程

手动 `start()` / `join()` 适合少量线程。任务一多，就该用线程池（thread pool）：复用线程、自动排队、返回 Future 拿结果。

```python
from concurrent.futures import ThreadPoolExecutor
import time

def fetch(url):
    time.sleep(0.5)             # 模拟网络请求
    return f"OK:{url}"

urls = [f"http://site/{i}" for i in range(8)]

# 最多同时 4 个线程干活
with ThreadPoolExecutor(max_workers=4) as pool:
    results = list(pool.map(fetch, urls))   # 按输入顺序返回结果

print(results)
```

`ThreadPoolExecutor` 是工程实践中绝大多数「I/O 并发」场景的首选——比手搓 `Thread` 更安全、更简洁。

---

## 5. 什么时候**不要**用线程？

| 场景 | 推荐方案 |
|---|---|
| 网络 / 文件 / 数据库 I/O 并发 | **线程** 或 `asyncio` |
| 纯 Python 的 CPU 密集计算 | **`multiprocessing`**（绕开 GIL） |
| 成千上万的长连接 | **`asyncio`**（协程更轻） |
| 简单并行跑几个函数 | `ThreadPoolExecutor` / `ProcessPoolExecutor` |

记住一句话：**线程解决“等待”，进程解决“算力”。**

```python
import threading
import time
from concurrent.futures import ThreadPoolExecutor

# --- 1. 最基础的线程 ---
def worker(name: str, delay: float) -> None:
    print(f"[{name}] 开始")
    time.sleep(delay)              # 模拟 I/O，sleep 会释放 GIL
    print(f"[{name}] 结束")

threads = [threading.Thread(target=worker, args=(f"T{i}", 0.5)) for i in range(3)]
for t in threads: t.start()        # 启动，不阻塞
for t in threads: t.join()         # 等待全部结束

# --- 2. 用 Lock 保护共享计数器 ---
counter = 0
lock = threading.Lock()

def safe_add(n: int) -> None:
    global counter
    for _ in range(n):
        with lock:
            counter += 1

workers = [threading.Thread(target=safe_add, args=(50_000,)) for _ in range(4)]
for t in workers: t.start()
for t in workers: t.join()
assert counter == 200_000, f"期望 200000，实际 {counter}"
print("Lock 生效，counter =", counter)

# --- 3. 用 ThreadPoolExecutor 管理并发 ---
def fetch(url: str) -> str:
    time.sleep(0.3)
    return f"OK:{url}"

with ThreadPoolExecutor(max_workers=4) as pool:
    results = list(pool.map(fetch, [f"url{i}" for i in range(6)]))
print("池化结果:", results)
```

## py.thread.lock

# py.thread.lock：让多线程不再“撞车”

> **一句话直觉**：当多个线程同时改同一个数据时，结果会随机出错；`Lock`（锁）就是那把“同一时刻只允许一个人进房间”的钥匙。

前置：无。你只需要会写普通的 Python 函数与 `for` 循环即可。

---

## 0. 开场：为什么需要锁？

CPU 执行 `x = x + 1` 并不是“一步完成”，它至少分三步：

1. 读 `x` 的当前值；
2. 计算 `x + 1`；
3. 写回 `x`。

如果两个线程交替执行这三步，就可能发生 **竞态条件（race condition）**：两个线程都读到了旧值，各自加 1，最终只加了 1 次。下面这段代码你会看到“丢失更新”。

```python
# demo_race.py —— 不加锁，结果通常小于 200000
import threading

counter = 0

def worker():
    global counter
    for _ in range(100_000):
        counter += 1   # 危险：读-改-写不是原子操作

ts = [threading.Thread(target=worker) for _ in range(2)]
for t in ts: t.start()
for t in ts: t.join()

print("期望 200000，实际 =", counter)   # 每次运行结果几乎都不同
```

**结论**：只要多线程共享可变状态，并且存在“读-改-写”模式，就必须考虑同步（synchronization）。`Lock` 是最基础的同步原语（synchronization primitive）。

---

## 1. Lock 是什么：一个布尔开关 + 两个动作

`threading.Lock` 是一个互斥锁（mutex，mutual exclusion lock）。它只有两种状态：**已锁（locked）** 和 **未锁（unlocked）**，对应两个动作：

- `acquire()`：尝试上锁。如果已被别人锁住，就**阻塞等待**，直到对方 `release()`。
- `release()`：解锁，把锁让给下一个等待者。

最关键的一点：**`acquire` 与 `release` 之间的代码，同一时刻只会有一个线程在执行**，这段区域叫 **临界区（critical section）**。

```python
import threading

lock = threading.Lock()

lock.acquire()
try:
    print("临界区：只有我能进来")
finally:
    lock.release()   # 必须释放，否则其他线程永远卡住
```

`try/finally` 是为了保证即使临界区里抛异常，锁也能被释放。

---

## 2. 推荐写法：`with lock:` 上下文管理器

每次都写 `try/finally` 很啰嗦，`Lock` 支持上下文管理器（context manager）协议，等价且更安全：

```python
import threading

lock = threading.Lock()

with lock:                      # 进入时自动 acquire()
    print("临界区")
                                # 退出时自动 release()，异常也不会漏掉
```

**工程建议**：除非有特殊原因（例如需要 `acquire(timeout=...)` 或 `acquire(blocking=False)`），都优先用 `with lock:`。

---

## 3. 修复竞态：给计数器加锁

把第 0 节的 `counter += 1` 包进临界区：

```python
import threading

counter = 0
lock = threading.Lock()

def worker():
    global counter
    for _ in range(100_000):
        with lock:              # 同一时刻只有一个线程能执行下面一行
            counter += 1

ts = [threading.Thread(target=worker) for _ in range(2)]
for t in ts: t.start()
for t in ts: t.join()

print("结果 =", counter)        # 稳定输出 200000
```

**核心思想**：锁保护的**不是**某一行代码，而是“共享状态的不变量（invariant）”。只要一个不变量被多个步骤破坏再重建，整个过程都要放进临界区。

---

## 4. 进阶要点：死锁、超时、可重入

### 4.1 死锁（deadlock）

如果两个线程以**不同顺序**获取两把锁，就可能互相等待：

```python
lock_a.acquire()
lock_b.acquire()   # 线程 A 拿 a 等 b
# 同时线程 B 拿 b 等 a  → 死锁
```

**防死锁口诀**：所有线程都按同一种**固定顺序**获取多把锁；能不用多锁就别用多锁。

### 4.2 带超时的获取：`acquire(timeout=...)`

```python
if lock.acquire(timeout=0.5):
    try:
        ...
    finally:
        lock.release()
else:
    print("等太久，先做别的事")
```

### 4.3 `RLock`：同一线程可重复进入

普通 `Lock` 被同一线程再次 `acquire` 会**自锁死**。`threading.RLock`（可重入锁，reentrant lock）允许同一线程多次进入，必须一一对应地 `release` 相同次数才能放开。

```python
import threading
rlock = threading.RLock()
with rlock:
    with rlock:      # 普通 Lock 会死锁，RLock 不会
        print("嵌套安全")
```

**何时用 RLock？** 当一个已加锁的方法内部又调用另一个已加锁的方法时。**能用普通 Lock 就用普通 Lock**，RLock 会掩盖设计问题。

---

## 5. 心智模型：锁 = 用并发性能换正确性

- **加锁的代价**：加锁区域会串行化，削弱并发的收益。
- **加锁的目标**：保证共享状态的一致性。**先正确，再快**。
- **能用别的手段就避免共享**：用 `queue.Queue`、`concurrent.futures`、不可变数据、线程本地存储（`threading.local`）等，很多时候比手动加锁更简单、更不容易出错。
- **锁是最小可用的同步原语**，理解它之后，`Event`、`Semaphore`、`Condition` 都是它的推广。

---

## 6. 动手练习（本地完成，约 20~30 分钟）

**任务**：写一个 `safe_account.py`，实现一个线程安全的“银行账户”：

1. 账户有 `balance`（初始 1000）和 `deposit(amount)` / `withdraw(amount)` 两个方法。
2. 用 `threading.Lock` 保证任意时刻只有一条线程能修改 `balance`。
3. 启动 **10 个线程**，每个线程**随机存取 1000 次**（金额 1~10），总存取次数 10000 次。
4. 全部 `join` 后打印最终余额，并额外记录：“存款总额 - 取款总额 应该等于 最终余额 - 初始余额”。
5. **对照实验**：把 `with lock:` 去掉再跑一次，观察最终余额每次是否都不一致。

**验收标准**：
- 加锁版本“存款-取款 = 余额变化”恒成立；
- 不加锁版本会经常不等；
- 代码能连续运行 10 次不崩。

**挑战（选做）**：把 `Lock` 换成一个“双锁版本”（存款用 `lock_a`，取款用 `lock_b`），看看是否会出现死锁，并解释原因。

```python
# safe_counter.py —— Lock 最小可运行示例
# 运行环境：Python 3.9+

import threading

# 1) 共享状态 + 一把锁
counter = 0
lock = threading.Lock()

ITER = 100_000
THREADS = 4


def worker():
    global counter
    for _ in range(ITER):
        # 2) 临界区：acquire/release 由 with 自动完成
        with lock:
            counter += 1


if __name__ == "__main__":
    # 3) 启动多线程
    threads = [threading.Thread(target=worker) for _ in range(THREADS)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    expected = ITER * THREADS
    print(f"期望 = {expected}, 实际 = {counter}")
    assert counter == expected, "加锁后结果必须稳定"

    # 4) 对照：不加锁会丢失更新
    counter = 0
    def worker_unsafe():
        global counter
        for _ in range(ITER):
            counter += 1

    threads = [threading.Thread(target=worker_unsafe) for _ in range(THREADS)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    print(f"不加锁：期望 = {expected}, 实际 = {counter}（通常偏小，且每次都不同）")
```


---

## 本课题目

### single_choice · None



- [A] import threading; t = threading.Thread(target=task); t.start()
- [B] import threading; t = threading.Thread(target=task); t.run()
- [C] import threading; t = threading.Thread(target=task); t.join()
- [D] import threading; threading.Thread(target=task)

**参考答案**：0

**解析**：创建 Thread 对象后需要调用 start() 才会在新线程中执行 target。直接调用 run() 只是在当前线程同步执行；join() 是等待线程结束；只创建对象不启动不会运行。

### single_choice · None



- [A] 一定先输出 worker，再输出 main
- [B] 一定先输出 main，再输出 worker
- [C] worker 和 main 的先后顺序不确定
- [D] 只输出 main，worker 不会执行

**参考答案**：2

**解析**：start() 后新线程与主线程并发执行，调度顺序由操作系统决定，因此两条打印的先后顺序不确定。

### single_choice · None



- [A] 需要大量 CPU 密集型计算来加速
- [B] 需要同时等待多个网络请求返回
- [C] 需要保证数据绝对不被并发修改
- [D] 需要让程序只用一个线程运行

**参考答案**：1

**解析**：多线程适合 I/O 密集型任务，如网络请求、文件读写。CPU 密集型受 GIL 影响通常更适合多进程；线程安全需要同步机制保证。

### single_choice · None



- [A] 网络爬虫等待响应
- [B] 文件读写等待磁盘
- [C] 纯 Python 的数值计算
- [D] 等待用户输入

**参考答案**：2

**解析**：GIL 使得同一时刻只有一个线程执行 Python 字节码，因此纯 Python 的 CPU 密集型计算难以通过多线程获得并行加速。

### single_choice · None



- [A] 会，主线程一定等到 done 输出后才退出
- [B] 不会，主线程退出时守护线程被强制结束，可能看不到 done
- [C] 会，因为 start() 会自动 join
- [D] 不会，因为子线程根本没有运行

**参考答案**：1

**解析**：daemon 线程不会阻止主线程退出，主线程打印后立即结束，守护线程可能来不及输出 done。

### single_choice · None



- [A] 多个线程同时修改共享变量一定不会出问题
- [B] 多个线程同时修改共享变量可能产生竞态条件
- [C] 只要使用多线程就自动线程安全
- [D] 线程安全只与函数返回值有关

**参考答案**：1

**解析**：多个线程并发读写共享数据可能导致竞态条件，需要锁等同步机制保证线程安全。

### single_choice · None



- [A] 提高 count += 1 的执行速度
- [B] 保证同一时刻只有一个线程执行 count += 1
- [C] 让 count 变成线程局部变量
- [D] 自动启动多个线程

**参考答案**：1

**解析**：Lock 用于互斥访问临界区，保证同一时刻只有一个线程执行受保护的代码，避免竞态条件。它不会自动启动线程，也不改变变量作用域。

### single_choice · None



- [A] threading.Thread(target=work, args=(1,), kwargs={"b": 2}).start()
- [B] threading.Thread(target=work, args={"a": 1, "b": 2}).start()
- [C] threading.Thread(target=work, kwargs=(1, 2)).start()
- [D] threading.Thread(target=work(1, b=2)).start()

**参考答案**：0

**解析**：args 必须是元组，kwargs 必须是字典。选项 B 把字典当 args；C 把元组当 kwargs；D 直接调用函数并传入返回值作为 target。

### single_choice · None



- [A] name 是只读的，不能修改
- [B] 可以在创建 Thread 时通过 name 参数指定，也可以后续修改
- [C] name 必须是唯一的整数
- [D] name 决定线程的优先级

**参考答案**：1

**解析**：Thread 支持 name 参数设置线程名，也可以后续通过属性修改。线程名不要求唯一，也不决定优先级。

### single_choice · None



- [A] False 然后 True
- [B] True 然后 False
- [C] True 然后 True
- [D] False 然后 False

**参考答案**：1

**解析**：start() 后线程正在运行，is_alive() 返回 True；join() 后线程已结束，is_alive() 返回 False。

### single_choice · None



- [A] 让每个线程使用不同的 Thread 对象名
- [B] 使用 Lock 保护写入文件的代码块
- [C] 把 daemon 设为 True
- [D] 增加线程的 name 长度

**参考答案**：1

**解析**：文件写入是共享资源，需用锁互斥访问。线程名、daemon 属性与互斥无关。

### single_choice · None



- [A] 线程可以在同一进程内共享内存
- [B] 线程的创建和切换开销通常小于进程
- [C] 多个线程可以并行执行 Python 字节码而不受任何限制
- [D] 线程之间通信通常比进程之间更方便

**参考答案**：2

**解析**：在 CPython 中由于 GIL，多个线程不能真正并行执行 Python 字节码，因此 C 项错误。其余关于线程共享内存、开销和通信的说法基本正确。

### single_choice · None



- [A] 调用 join() 会立即终止目标线程
- [B] 调用 join() 会阻塞当前线程，直到目标线程结束
- [C] 调用 join() 会让目标线程进入休眠状态
- [D] 调用 join() 会启动目标线程

**参考答案**：1

**解析**：join() 的作用是等待目标线程执行完毕，调用者会被阻塞。它不会终止、休眠或启动线程。

### single_choice · None



- [A] 保证 done 一定在 working 之前输出
- [B] 保证 working 一定在 done 之前输出
- [C] 使 work 函数执行两次
- [D] 阻止 work 函数执行

**参考答案**：1

**解析**：t.join() 会等待 t 执行结束，因此 work 中的打印一定先于 join 之后的 print("done")。

### single_choice · None



- [A] daemon 线程会阻止主程序退出
- [B] daemon 线程在主程序退出时会被强制结束
- [C] daemon 线程必须手动 join 才能结束
- [D] daemon 属性只能在 start() 之后设置

**参考答案**：1

**解析**：守护线程不会阻止解释器退出，主线程结束时守护线程会被直接结束。daemon 需要在 start() 之前设置。

### single_choice · None



- [A] 没有问题，可以正常运行
- [B] setDaemon 必须在 start() 之前调用
- [C] setDaemon 只能用于主线程
- [D] setDaemon 的参数必须是字符串

**参考答案**：1

**解析**：daemon 状态必须在线程启动前设置，start() 之后再调用 setDaemon 会抛出 RuntimeError。

### single_choice · None



- [A] threading.Thread(target=work, args=("A", 3)).start()
- [B] threading.Thread(target=work("A", 3)).start()
- [C] threading.Thread(target=work, args={"A", 3}).start()
- [D] threading.Thread(target=work, kwargs=("A", 3)).start()

**参考答案**：0

**解析**：位置参数通过 args 以元组形式传入；kwargs 用于关键字参数；直接在 target 位置调用函数会先执行函数并把返回值当作 target。

### single_choice · None



- [A] run 只输出一次
- [B] run 输出两次，且两次都在新线程中执行
- [C] 第一次 run 在主线程中同步执行，第二次在新线程中执行
- [D] 程序会直接报错

**参考答案**：2

**解析**：run() 只是普通方法调用，会在当前线程同步执行；随后 start() 再启动一个新线程执行 target，因此 run 会输出两次，但只有第二次在新线程中。

### single_choice · None



- [A] 会再启动一个新线程
- [B] 会抛出 RuntimeError
- [C] 会重新执行一次 run() 但不开新线程
- [D] 没有任何影响，静默忽略

**参考答案**：1

**解析**：同一个 Thread 对象只能启动一次，重复调用 start() 会抛出 RuntimeError。

### single_choice · None



- [A] 它返回当前正在执行的线程对象
- [B] 它返回主线程对象，无论在哪里调用
- [C] 它返回一个布尔值表示是否在主线程
- [D] 它返回当前线程的名字字符串

**参考答案**：0

**解析**：current_thread() 返回调用处所在的线程对象；线程名字通过 Thread 对象的 name 属性获取。

### single_choice · None



- [A] GIL 只保证字节码指令级别的互斥，`count += 1` 是读取-计算-写回多步操作，线程可能在中途被切换
- [B] GIL 会阻止所有线程并发执行，因此结果不可能出错
- [C] `+=` 在 Python 中是原子操作，出错只可能因为内存不足
- [D] 只有多进程才会出现竞争，多线程不会

**参考答案**：0

**解析**：GIL 只保证同一时刻只有一个线程执行字节码，但 `count += 1` 由读、加、写多条字节码组成，线程可能在这些步骤之间被切换，导致更新丢失，因此仍需锁保护。

### single_choice · None



- [A] 同一线程可以多次 acquire 同一个 Lock 而不会阻塞
- [B] Lock 是可重入的，重复 acquire 只会增加计数
- [C] 未经 acquire 就调用 release 会抛出 RuntimeError
- [D] Lock 可以在不同进程之间共享

**参考答案**：2

**解析**：`threading.Lock` 是普通互斥锁，不是可重入锁（可重入的是 `threading.RLock`）。对未持有的锁调用 release 会抛出 RuntimeError；同一线程重复 acquire 同一把 Lock 会自己把自己阻塞。

### single_choice · None



- [A] 线程各自持有私有变量副本，锁用于同步这些副本
- [B] 锁主要保证临界区互斥，从而避免交错更新的问题；变量的最新值通常由共享对象自然可见
- [C] 必须调用锁的 flush 方法才能看到别的线程写入的值
- [D] 锁会改变 GIL 的行为

**参考答案**：1

**解析**：在 CPython 中对象位于共享内存，锁的核心作用是保证临界区互斥，避免读-改-写交错；不像某些平台需要额外的内存屏障语义。

### multi_choice · None



- [A] 它是一把互斥锁，用于保护临界区
- [B] 它可以作为上下文管理器用于 with 语句
- [C] 它是可重入的，同一线程可多次 acquire
- [D] 未持有时 release 会抛出 RuntimeError

**参考答案**：[0, 1, 3]

**解析**：Lock 是普通互斥锁、支持 with，未持有时 release 会抛 RuntimeError；它不可重入，因此第二项说法错误。

### multi_choice · None



- [A] 为多个锁规定统一的获取顺序
- [B] 使用 acquire(timeout=...) 并处理超时
- [C] 在持锁期间调用另一个可能长时间阻塞的操作
- [D] 使用 try/finally 或 with 确保锁被释放

**参考答案**：[0, 1, 3]

**解析**：统一顺序、超时获取、确保释放都能降低死锁风险；在持锁期间调用可能长时间阻塞的操作反而容易诱发死锁。

### multi_choice · None



- [A] 临界区应只包含访问共享可变状态的必要操作
- [B] 为了安全，应把尽可能多的代码放进临界区
- [C] 在临界区内执行耗时 IO 会拖慢其他线程
- [D] 把无关计算移出临界区通常能改善并发性能

**参考答案**：[0, 2, 3]

**解析**：临界区应尽可能小以缩短串行化时间；把大量无关代码或耗时 IO 放入临界区会降低并发效率。

### fill_blank · None



**参考答案**：["lock", "lock "]

**解析**：with 后应跟锁对象 lock，进入临界区自动获取，退出自动释放，保证 `count += 1` 的读-改-写不被其他线程交错。

### fill_blank · None



**参考答案**：["blocking=False", "blocking=false", "blocking = False"]

**解析**：acquire(blocking=False) 表示锁不可用时立即返回 False，而不是等待。

### fill_blank · None



**参考答案**：["Lock RLock", "Lock,RLock", "Lock、RLock", "Lock RLock "]

**解析**：`threading.Lock` 是普通互斥锁，`threading.RLock` 是可重入锁，后者允许同一线程重复获取。

### code_reading · None



**参考答案**：第一次输出 True，第二次输出 False。

**解析**：`locked()` 反映锁当前是否被持有：acquire 后为 True，release 后为 False。

### code_reading · None



**参考答案**：输出为：True False。因为第一次非阻塞获取成功返回 True 并持有了锁；锁已被持有，第二次非阻塞获取立即返回 False。

**解析**：非阻塞 acquire 在锁不可用时不会等待，直接返回 False，因此同一线程也无法再次获取已被自己持有的普通 Lock。

### scenario · None



**参考答案**：[]

**解析**：持锁期间执行耗时的网络 IO 把不必要的操作串行化，导致其他线程长时间等待锁，吞吐下降。应把远程调用移出临界区，只把必要的共享状态更新放在锁内，从而缩小临界区、提高并发度。

### single_choice · None



- [A] 能自动让代码运行得更快
- [B] 能保证进入临界区时不会被其他线程看到
- [C] 即使临界区内发生异常也能确保锁被释放
- [D] 能自动完成线程之间的数据同步传递

**参考答案**：2

**解析**：`with lock:` 使用上下文管理器，在块退出时（包括异常路径）自动调用 release，避免因异常导致锁长期不释放而出现死锁。

### single_choice · None



- [A] 打印一次 "in"，正常结束
- [B] 抛出 RuntimeError
- [C] 程序永久阻塞（死锁）
- [D] 打印两次 "in"

**参考答案**：2

**解析**：普通 Lock 不可重入，外层 with 已持有该锁，内层再次 acquire 会阻塞当前线程，而锁又不会被释放，于是死锁。

### single_choice · None



- [A] 无论锁是否可用，都会一直等待直到拿到锁
- [B] 锁可用时返回 True 并获取锁，不可用时立即返回 False
- [C] 锁不可用时抛出异常
- [D] 该参数只对 RLock 有效，对 Lock 无效

**参考答案**：1

**解析**：非阻塞获取：锁空闲则获取并返回 True，否则立即返回 False，不会等待也不会抛异常。

### single_choice · None



- [A] 其他线程仍然可以无视该锁进入临界区
- [B] 锁会被 Python 自动释放
- [C] 会显著降低并发效率，其他线程可能长时间被阻塞
- [D] 会触发 GIL 自动解除限制

**参考答案**：2

**解析**：临界区应尽量短。若在持锁期间阻塞，其他需要该锁的线程会被长时间挂起，严重时导致死锁或性能雪崩。

### single_choice · None



- [A] 只要有两个以上的锁就必然死锁
- [B] 多个线程以不同顺序获取多把锁，可能形成环路从而互相等待
- [C] 循环等待只存在于多进程
- [D] 使用 with 语句可以完全消除循环等待

**参考答案**：1

**解析**：当线程 A 持锁1等锁2、线程 B 持锁2等锁1时形成循环等待。统一加锁顺序、使用超时或尝试性获取可打破该条件。

### single_choice · None



- [A] 在所有线程中按相同顺序获取这些锁
- [B] 把锁的粒度尽可能放大，用一个锁包住所有操作
- [C] 尽量使用 blocking=False 并忽略返回值
- [D] 把锁对象设为全局变量以加快访问

**参考答案**：0

**解析**：统一加锁顺序可以消除循环等待条件，是最常用的死锁预防手段。

### single_choice · None



- [A] 它和 Lock 完全等价，只是性能更好
- [B] 它记录持有线程与递归次数，同一线程可重复获取，需相同次数释放
- [C] 它不支持 with 语句
- [D] 它必须由不同线程来释放

**参考答案**：1

**解析**：RLock 是可重入锁，内部记录持有者和递归计数，同一线程可多次 acquire，每次 release 递减计数，计数归零才真正释放。

### single_choice · None



- [A] 锁的开销可以忽略，可以任意频繁使用
- [B] 锁越多越细，程序一定越安全
- [C] 锁会带来获取/释放开销并可能造成阻塞，应在正确性前提下尽量缩小临界区
- [D] 单线程程序中加锁是完全没有意义的

**参考答案**：2

**解析**：锁保障正确性但引入开销和竞争，设计时应保证正确性同时让临界区尽可能短，减少串行化范围。
