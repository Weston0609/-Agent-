# s3u2l2 线程安全三件套：RLock（可重入锁）与 Semaphore（信号量） / 多线程协作的"传送门"

> 来源 `content/lessons/s3u2l2.json`

## py.thread.rlock_semaphore

# 线程安全三件套：RLock（可重入锁）与 Semaphore（信号量）

> **一句话直觉**：当多个线程同时抢同一份资源时，普通 `Lock` 容易把自己也锁死，`RLock` 让你能“同一线程重复进门”，`Semaphore` 则像停车场闸机——只允许有限数量的车同时进去。

前置：本课是起点，假设你会写 `def`、会用 `with`，但不要求你学过多线程。

---

## 1. 为什么需要锁？——从数据竞争说起

多线程（thread）共享同一块内存。Python 有 GIL（Global Interpreter Lock，全局解释器锁），很多人误以为“有 GIL 就不用锁”。**错**：GIL 只保证单条字节码（bytecode）原子性，像 `counter += 1` 这种“读—加—写”三步操作会被线程切换打断，结果丢更新。

```python
import threading

counter = 0

def worker():
    global counter
    for _ in range(100_000):
        counter += 1   # 非原子！可能丢更新

threads = [threading.Thread(target=worker) for _ in range(5)]
for t in threads: t.start()
for t in threads: t.join()

print("期望 500000，实际", counter)  # 几乎总是小于 500000
```

**结论 1**：只要涉及共享可变状态（mutable state）的复合操作，就需要同步（synchronization）原语。

---

## 2. Lock：最基础的互斥锁

`threading.Lock` 是互斥锁（mutual exclusion lock）。`with lock:` 会自动获取与释放，等价于 `lock.acquire()` / `lock.release()`。

```python
import threading

counter = 0
lock = threading.Lock()

def worker():
    global counter
    for _ in range(100_000):
        with lock:          # 同一时刻只有一个线程进入
            counter += 1

threads = [threading.Thread(target=worker) for _ in range(5)]
for t in threads: t.start()
for t in threads: t.join()
print("现在正确：", counter)  # 500000
```

**结论 2**：`Lock` 不可重入——同一线程重复 `acquire()` 会**死锁**（deadlock），因为它已经在等自己释放。

---

## 3. RLock：可重入锁（Reentrant Lock）

`RLock` 记录“谁持有 + 持有几次”。同一线程可以多次 `acquire()`，必须相应次数 `release()` 才真正释放，允许递归调用与带锁的方法互相调用。

```python
import threading

rlock = threading.RLock()

def outer():
    with rlock:
        print("进入 outer")
        inner()          # 同一线程再次进入，不会死锁

def inner():
    with rlock:
        print("进入 inner")

outer()

# 反例：换成 threading.Lock() 后运行会直接卡死，需要 Ctrl+C 停止
```

**结论 3**：`RLock` 的代价是稍慢、稍重；只在“同一线程会重入”的场景用它，否则用 `Lock` 更清晰。

---

## 4. Semaphore：限制“同时进行”的数量

`threading.Semaphore(n)` 内部维护一个计数器，`acquire()` 减一、`release()` 加一，减到 0 时阻塞。典型用途：连接池、限流、生产者—消费者里的空位/满位计数。`BoundedSemaphore` 会防止 `release()` 超过初值。

```python
import threading, time, random

sem = threading.Semaphore(2)   # 最多 2 个线程同时进入

def task(i):
    with sem:
        print(f"任务 {i} 开始")
        time.sleep(random.uniform(0.2, 0.5))
        print(f"任务 {i} 结束")

threads = [threading.Thread(target=task, args=(i,)) for i in range(6)]
for t in threads: t.start()
for t in threads: t.join()
```

**结论 4**：`Lock` 是 `Semaphore(1)` 的特例；`Semaphore` 是“计数型”的权限发放器。

---

## 5. 选型与工程经验

| 需求 | 选择 |
|---|---|
| 简单互斥，无重入 | `Lock` |
| 同一线程可能重入（递归/互调） | `RLock` |
| 限制并发数 / 资源池 | `Semaphore` / `BoundedSemaphore` |
| 线程间等待某个条件 | `Condition` |
| 只读共享、低频写 | `threading.local` 或干脆不用共享 |

工程习惯：
- 一律用 `with`，不要手写 `acquire`/`release`；
- 锁的作用域越短越好，绝不在持锁时做 I/O；
- 锁对象与它保护的数据放在一起命名（如 `counter_lock`）；
- 需要多把锁时统一加锁顺序，避免死锁。

**结论 5**：正确性 > 性能。先保证没有数据竞争，再考虑减少锁粒度。

```python
import threading
import time
import random

# ---------- 1) RLock：同一线程可重入 ----------
print("=== RLock 演示 ===")
rlock = threading.RLock()

def outer():
    with rlock:
        print("outer 持有锁")
        inner()          # 同一线程再次 with，不会死锁
    print("outer 释放锁")

def inner():
    with rlock:
        print("  inner 也拿到锁（可重入）")

outer()

# ---------- 2) Semaphore：限流 ----------
print("\n=== Semaphore 演示（最多 2 个并发）===")
sem = threading.Semaphore(2)

def worker(i):
    with sem:
        print(f"worker {i} 开始")
        time.sleep(random.uniform(0.1, 0.3))
        print(f"worker {i} 结束")

threads = [threading.Thread(target=worker, args=(i,)) for i in range(6)]
for t in threads:
    t.start()
for t in threads:
    t.join()

# ---------- 3) 对照：普通 Lock 的计数保护 ----------
print("\n=== Lock 保护 counter ===")
counter = 0
lock = threading.Lock()

def add():
    global counter
    for _ in range(50_000):
        with lock:
            counter += 1

ts = [threading.Thread(target=add) for _ in range(4)]
for t in ts: t.start()
for t in ts: t.join()
print("counter =", counter, "（期望 200000）")
```

## py.thread.queue

# py.thread.queue：多线程协作的"传送门"

## 一句话直觉

**多个线程（thread）要一起干活时，谁来把任务递给谁？`queue.Queue` 就是那条安全、不会丢件的传送带——生产者往里放，消费者从里取，互不打架。**

---

## 第一节：为什么需要 Queue？——从"抢一个变量"说起

多线程（multithreading）让多个执行流同时跑。它们共享同一块内存。如果两个线程同时读写一个普通列表（list），就可能出现"读到一半被改写"的错乱。

`queue.Queue` 是 Python 标准库提供的**线程安全队列（thread-safe queue）**，内部用锁（lock）保护，你不用自己写锁。

```python
# 反例：裸 list 在并发下不安全
import threading

shared = []

def bad_producer():
    for i in range(1000):
        shared.append(i)  # CPython 运气好时没问题，但语义上不保证

# 正例：queue.Queue 天生线程安全
import queue

q = queue.Queue()
q.put(1)          # 放入
q.put(2)
print(q.get())    # 取出：1
print(q.get())    # 取出：2
```

关键结论：**只要涉及多线程交换数据，首选 `queue.Queue`，别自己维护共享变量。**

---

## 第二节：三种队列形态——FIFO / LIFO / 优先队列

`queue` 模块提供三种实现，接口几乎一样：

| 类 | 行为 | 英文名 |
|---|---|---|
| `queue.Queue` | 先进先出 | FIFO |
| `queue.LifoQueue` | 后进先出（像栈） | LIFO |
| `queue.PriorityQueue` | 按优先级出队 | priority queue |

```python
import queue

fifo = queue.Queue()
fifo.put("a"); fifo.put("b")
print(fifo.get(), fifo.get())   # a b

lifo = queue.LifoQueue()
lifo.put("a"); lifo.put("b")
print(lifo.get(), lifo.get())   # b a

pq = queue.PriorityQueue()
pq.put((3, "低")); pq.put((1, "高"))
print(pq.get(), pq.get())       # (1, '高') (3, '低')
```

关键结论：**默认用 `Queue`；需要"最近的任务先处理"用 `LifoQueue`；需要按优先级调度用 `PriorityQueue`。**

---

## 第三节：阻塞与超时——put/get 的三种表情

`put()` 和 `get()` 都会"阻塞（block）"，即队列满/空时调用线程会等待：

- `get()`：队列空 → 等到有元素
- `put()`：队列满（设置了 `maxsize`）→ 等到有空位
- 想立刻返回？加 `block=False` 或 `timeout=秒数`

```python
import queue, threading, time

q = queue.Queue(maxsize=1)
q.put(1)               # 塞满

try:
    q.put(2, block=False)   # 满，立即抛异常
except queue.Full:
    print("队列满了，不等")

try:
    q.get_nowait()          # 同 block=False
except queue.Empty:
    pass

# 超时用法
q2 = queue.Queue()
try:
    q2.get(timeout=0.5)     # 0.5 秒内没东西就抛 Empty
except queue.Empty:
    print("等超时了")
```

关键结论：**`Full` 和 `Empty` 是"阻塞+超时"的伴侣异常；生产环境建议总用 `timeout`，避免线程永久卡死。**

---

## 第四节：结束信号——哨兵（sentinel）与 `task_done`/`join`

消费者怎么知道"没活了"可以退出？两种主流做法：

1. **哨兵值（sentinel）**：生产者发一个特殊对象，消费者收到就 break。
2. **`task_done()` + `join()`**：每处理完一个任务调用 `task_done()`，主线程 `join()` 等全部完成。

```python
import queue, threading

q = queue.Queue()
DONE = object()      # 独一无二的哨兵

def worker():
    while True:
        item = q.get()
        if item is DONE:
            q.task_done()
            break
        print("处理", item)
        q.task_done()

t = threading.Thread(target=worker, daemon=True)
t.start()

for i in range(3):
    q.put(i)
q.put(DONE)

q.join()    # 等所有 task_done 被调用
t.join()
print("全部完成")
```

关键结论：**`get()` 之后必须 `task_done()`，否则 `join()` 会永远等下去——这是新手最常踩的坑。**

---

## 第五节：一个可用的生产者-消费者骨架

把前面拼起来，就是一个标准模式：

- 生产者：不断 `put` 任务
- 消费者：循环 `get`，处理，`task_done`
- 主线程：`join` 所有队列，回收线程

这套骨架是后面学习线程池（`concurrent.futures`）、异步（`asyncio.Queue`）、消息中间件（如 RabbitMQ）的思想起点。**先掌握 `queue.Queue`，后面所有"任务分发"都是它的变体。**

```python
import queue
import threading
import time


def producer(q: "queue.Queue", n: int) -> None:
    """生产者：向队列放入 n 个任务。"""
    for i in range(n):
        time.sleep(0.05)          # 模拟生产耗时
        q.put(i)
        print(f"[生产] {i}")
    q.put(None)                   # 哨兵：通知消费者收工


def consumer(q: "queue.Queue") -> None:
    """消费者：循环取任务，直到遇到哨兵。"""
    while True:
        item = q.get()
        if item is None:
            q.task_done()
            break
        time.sleep(0.1)           # 模拟处理耗时
        print(f"[消费] {item}")
        q.task_done()             # 必须调用，join 才能返回


if __name__ == "__main__":
    q: "queue.Queue" = queue.Queue(maxsize=5)

    t_prod = threading.Thread(target=producer, args=(q, 5))
    t_cons = threading.Thread(target=consumer, args=(q,))

    t_prod.start()
    t_cons.start()

    q.join()                      # 等所有 task_done 完成
    t_prod.join()
    t_cons.join()
    print("主线程结束")
```


---

## 本课题目

### single_choice · None



- [A] 该线程必须释放相同次数才能真正释放锁，其他线程才能获取
- [B] 只要释放一次就会完全释放锁，其他线程即可获取
- [C] 多次获取会立即造成死锁，因为锁不允许同线程重复获取
- [D] 每次获取都会创建一把新锁，释放时只释放最近获取的那把

**参考答案**：0

**解析**：可重入锁允许同一线程重复获取，但内部维护计数，必须释放与获取相同的次数后，锁才会真正释放给其他线程。

### single_choice · None



- [A] 信号量内部维护一个计数器，acquire 时计数减一，计数为零时阻塞
- [B] 信号量同一线程可以无限次获取而不会阻塞
- [C] 信号量只能取值 0 或 1，等价于互斥锁
- [D] 信号量用 release 增加计数，acquire 也增加计数

**参考答案**：0

**解析**：信号量通过内部计数器控制并发访问数量：acquire 使计数减一，计数为 0 时调用线程阻塞；release 使计数加一。

### single_choice · None



- [A] 同一线程在递归函数或多层调用中需要重复获取同一把锁时
- [B] 多个线程需要严格交替执行时
- [C] 需要限制同时访问资源的线程数量时
- [D] 需要在线程之间传递数据时

**参考答案**：0

**解析**：RLock 主要解决同一线程在递归或嵌套调用中重复获取同一把锁的问题，避免自死锁。

### single_choice · None



- [A] 另一个线程会阻塞，因为锁还未完全释放
- [B] 另一个线程立即获取成功
- [C] 另一个线程会收到异常
- [D] 锁自动重置，另一个线程也能获取

**参考答案**：0

**解析**：只 release 一次时重入计数仍为 1，锁仍被原线程持有，其他线程 acquire 会阻塞。

### single_choice · None



- [A] 如果计数大于零，acquire 会减少计数并立即返回；否则阻塞
- [B] 无论计数多少，acquire 总是立即返回
- [C] acquire 会增加计数，release 会减少计数
- [D] acquire 只能由主线程调用

**参考答案**：0

**解析**：信号量 acquire 在计数大于零时减少计数并成功返回；计数为零时阻塞等待，直到 release 增加计数。

### single_choice · None



- [A] 通常会抛出 RuntimeError，因为释放了未持有的锁
- [B] 计数变为负数，锁被其他线程持有
- [C] 没有任何影响，锁继续正常工作
- [D] 锁自动转移到等待时间最长的线程

**参考答案**：0

**解析**：RLock 在释放次数超过获取次数时会抛出 RuntimeError，因为该线程并未持有足够的锁计数。

### single_choice · None



- [A] 信号量只能用于线程之间的互斥，不能用于控制并发数量
- [B] 信号量可以限制同时访问某资源的线程数量
- [C] 信号量的 release 可以由非获取线程调用
- [D] 信号量计数为零时 acquire 会阻塞

**参考答案**：0

**解析**：信号量不仅可以实现互斥，还可以通过初始计数控制同时访问资源的线程数量，因此选项 A 的说法是错误的。

### single_choice · None



- [A] T2 阻塞，直到 T1 完全释放锁（计数减到 0）
- [B] T2 立即获取成功，计数变为 1
- [C] T2 获取失败并抛出异常
- [D] T2 获取成功，计数变为 3

**参考答案**：0

**解析**：RLock 只允许持有它的线程重入；其他线程必须等锁完全释放（计数归零）后才能获取。

### single_choice · None



- [A] 同一线程在已持有锁的情况下再次尝试获取同一把锁
- [B] 两个线程各自持有不同的锁并互相等待
- [C] 一个线程释放了不属于它的锁
- [D] 一个线程在获取锁之前先释放锁

**参考答案**：0

**解析**：普通 Lock 不可重入，同一线程重复获取会阻塞自己造成自死锁；RLock 允许同一线程重入，从而避免该问题。

### single_choice · None



- [A] 计数在创建时指定，acquire 减少计数，release 增加计数
- [B] 计数在创建时指定，acquire 和 release 都减少计数
- [C] 计数只能为 0 或 1，不能在创建时指定为其他值
- [D] 计数在运行时自动调整，不能由程序控制

**参考答案**：0

**解析**：信号量在创建时指定初始计数，acquire 使计数减一，release 使计数加一。

### single_choice · None



- [A] 可能永久阻塞，因为锁没有被释放
- [B] 自动获取锁，因为线程退出会自动释放
- [C] 立即抛出异常并退出
- [D] 切换为使用信号量继续执行

**参考答案**：0

**解析**：线程异常退出不会自动释放它持有的 RLock（除非使用上下文管理器），其他线程可能永久阻塞等待。

### single_choice · None



- [A] 可以用信号量限制同时访问数据库连接池的线程数量
- [B] 信号量只能用于保护单个变量，不能用于资源池
- [C] 信号量的 acquire 和 release 必须在同一线程中配对调用
- [D] 信号量不能用于多线程环境

**参考答案**：0

**解析**：信号量常用于限制同时访问资源池（如数据库连接池）的线程数量，且 acquire/release 不要求同一线程配对。

### single_choice · None



- [A] 第 4 个线程立即获取成功，信号量计数变为 -1
- [B] 第 4 个线程阻塞，直到某个已获取的线程调用 release
- [C] 第 4 个线程抛出异常，程序终止
- [D] 信号量自动扩容，第 4 个线程直接通过

**参考答案**：1

**解析**：信号量计数为 0 时，继续 acquire 会阻塞调用线程，直到有线程 release 释放资源。

### single_choice · None



- [A] RLock 允许同一线程多次获取，Lock 在同一线程第二次获取时会阻塞
- [B] Lock 允许同一线程多次获取，RLock 不允许
- [C] 两者完全等价，没有区别
- [D] RLock 只能用于读操作，Lock 只能用于写操作

**参考答案**：0

**解析**：RLock 可重入，同一线程可重复获取；普通 Lock 不可重入，同一线程重复获取会阻塞（或死锁）。

### single_choice · None



- [A] 锁处于被持有状态，计数为 2
- [B] 锁处于被持有状态，计数为 1
- [C] 第二次 acquire 会阻塞该线程
- [D] 第二次 acquire 抛出 RuntimeError

**参考答案**：0

**解析**：RLock 内部记录持有线程和重入次数，第二次 acquire 使计数增加到 2，不会阻塞同一线程。

### single_choice · None



- [A] 二者都能实现互斥，但信号量不一定绑定持有线程，释放可由其他线程执行
- [B] 二者完全相同，包括释放必须由持有者执行
- [C] 信号量容量为 1 时不能用于互斥
- [D] Lock 允许同一线程重入，信号量不允许

**参考答案**：0

**解析**：容量为 1 的信号量可以实现互斥效果，但与 Lock 不同，信号量的 release 不要求由获取它的线程执行。

### single_choice · None



- [A] 可以由任何线程调用，不要求是执行 acquire 的那个线程
- [B] 必须由执行 acquire 的同一线程调用，否则抛异常
- [C] 只能由主线程调用
- [D] release 不会影响信号量的计数

**参考答案**：0

**解析**：信号量的 release 通常可由任意线程调用，它只负责增加计数并可能唤醒等待线程，没有线程绑定要求。

### single_choice · None



- [A] 必须由持有该锁的线程调用 release，且每次 release 使计数减一
- [B] 任意线程都可以 release，计数每次减一
- [C] 必须一次 release 就将计数减到零
- [D] release 不会减少计数，只解除阻塞

**参考答案**：0

**解析**：RLock 要求由持有锁的线程释放，每次 release 使重入计数减一，减到零时锁才真正释放。

### single_choice · None



- [A] 同时最多有 2 个线程能通过 acquire，其余线程需等待
- [B] 5 个线程都能同时通过 acquire，不会阻塞
- [C] 只有第 1 个线程能通过，其余全部阻塞
- [D] 信号量会自动调整容量以容纳 5 个线程

**参考答案**：0

**解析**：信号量容量为 2 表示最多允许 2 个线程同时持有，其他线程在 acquire 时会被阻塞直到有 release。

### single_choice · None



- [A] 限制同时访问某资源的线程数量不超过 N 个
- [B] 保护一段只允许一个线程进入的临界区
- [C] 实现线程之间的单向消息传递
- [D] 保证同一线程可以重复进入临界区

**参考答案**：0

**解析**：信号量通过初始计数控制并发访问数量，适合限制同时进入的线程数；互斥锁只保证同一时刻一个线程进入。

### single_choice · None



- [A] 队列的 put 和 get 操作内部已经处理了线程同步，通常不需要再额外加锁
- [B] 使用队列传递数据时，必须自己为 put 和 get 手动加锁，否则会数据错乱
- [C] 队列只能在同一线程内使用，跨线程使用会抛出异常
- [D] 队列是后进先出结构，因此适合做生产者消费者模型

**参考答案**：0

**解析**：queue.Queue 内部使用锁和条件变量实现了线程安全的 put/get，多线程共享同一个队列时一般无需再手动加锁。B 是常见误解，其实不需要额外加锁；C 错误，队列专为跨线程通信设计；D 错误，默认 Queue 是先进先出（FIFO），后进先出是 LifoQueue。

### single_choice · None



- [A] 10
- [B] 20
- [C] None
- [D] 抛出异常

**参考答案**：0

**解析**：queue.Queue 默认是先进先出（FIFO）队列，先放入的 10 会先被取出，所以 x 为 10，20 留在队列中。

### single_choice · None



- [A] 它们是 block=False 的便捷写法：put_nowait 满时抛 Full，get_nowait 空时抛 Empty
- [B] 它们等价于 put/get 但永不抛异常，满/空时返回 None
- [C] 它们会阻塞直到成功
- [D] 它们会清空队列

**参考答案**：0

**解析**：put_nowait 等价于 put(item, block=False)，队列满时抛 Full；get_nowait 等价于 get(block=False)，队列空时抛 Empty。它们不阻塞，也不返回 None。

### multi_choice · None



- [A] 队列内部的 put/get 已保证线程安全，通常不必再包一层锁
- [B] get 在队列为空且默认参数下会阻塞，可用 block=False 改为抛出 Empty
- [C] task_done 与 join 配合可用于等待所有已入队任务被处理完毕
- [D] 必须用 qsize() 来判断队列是否为空后再 get，否则一定出错

**参考答案**：[0, 1, 2]

**解析**：A、B、C 均正确。D 错误：qsize 返回值是近似值，不能依赖它做严格同步判断，且用 try/except Empty 或 block 参数才是稳健做法，并非必须用 qsize。

### multi_choice · None



- [A] 对已满的队列调用 put_nowait
- [B] 对为空的队列调用 get_nowait
- [C] 对普通空队列调用 get()（不带参数，且无其他线程放入）
- [D] 对未满的队列调用 put

**参考答案**：[0, 1]

**解析**：put_nowait 满时抛 Full，get_nowait 空时抛 Empty，故 A、B 正确。C 描述的是默认 get 对空队列会阻塞而非抛异常（无超时情况下），说法不成立；D 正常成功放入，不抛异常。

### multi_choice · None



- [A] 生产者放入任务用 put，需要时用哨兵值（如 None）通知消费者结束
- [B] 消费者处理完一个任务后调用 task_done 以配合 join 等待完成
- [C] 用 queue.Queue(maxsize=n) 限制缓冲，起到背压/限流作用
- [D] 多个消费者直接读取队列内部私有属性以避免锁开销

**参考答案**：[0, 1, 2]

**解析**：A、B、C 都是标准做法。D 错误：访问内部私有属性绕过了线程安全保障，会导致竞态和难以排查的 bug。

### fill_blank · None



**参考答案**：["task_done", "task_done()", "q.task_done()"]

**解析**：task_done 告知队列一个已取出的任务处理完毕，内部未完成计数递减；当计数归零时 join() 返回。若不调用，join() 会一直阻塞。

### fill_blank · None



**参考答案**：["get_nowait", "get_nowait()", "q.get_nowait()"]

**解析**：get_nowait 是 get(block=False) 的便捷写法，队列为空时抛出 queue.Empty 而不会阻塞。

### fill_blank · None



**参考答案**：["阻塞等待", "阻塞", "阻塞直到有空位", "blocked", "阻塞等待直到有空间"]

**解析**：put 默认 block=True，队列满时会阻塞直到有空位；若传 block=False 或超时则抛 Full。

### code_reading · None



**参考答案**：[1, 2, 3]

**解析**：Queue 为先进先出，依次放入 1、2、3 后，依次取出顺序仍为 1、2、3。注意 empty() 在单线程且无其他线程干扰时此处可用，结果列表为 [1,2,3]。

### code_reading · None



**参考答案**：b a

**解析**：LifoQueue 后进先出，最后放入的 'b' 最先取出，随后取出 'a'，因此打印 'b a'。

### scenario · None



**解析**：队列的任务计数在 get 后需由 task_done 递减。若线程在处理任务途中因异常退出而未调用 task_done，计数无法归零，join() 就永远阻塞。修复思路：在消费者循环中用 try/finally 确保无论成功或异常都调用 task_done，同时捕获并记录异常避免线程无声退出。

### single_choice · None



- [A] 默认会阻塞，直到有元素可取；可用 block=False 让其不阻塞并抛出 Empty 异常
- [B] 默认立即返回 None
- [C] 默认立即抛出 IndexError
- [D] 默认会一直返回 None 直到有元素为止

**参考答案**：0

**解析**：Queue.get 默认 block=True，队列为空时会阻塞等待。传 block=False（或 timeout 超时）时，若为空则抛出 queue.Empty。它不会返回 None，也不抛 IndexError。

### scenario · None



**解析**：应创建带 maxsize 的有界队列并在队列满时让 put 阻塞（或超时/丢弃策略），从而对生产者形成背压，使生产速度受消费者吞吐约束，避免任务无界堆积导致内存耗尽。有界队列 + 阻塞 put 是常见限流方案。

### single_choice · None



- [A] LifoQueue 是后进先出，get 取出的顺序与 put 的顺序相反
- [B] LifoQueue 是先进先出，与 Queue 行为完全相同
- [C] Queue 是后进先出，LifoQueue 是先进先出
- [D] 两者都只能在单线程内使用

**参考答案**：0

**解析**：LifoQueue 是后进先出（栈式），最后放入的元素最先被取出，取出顺序与放入顺序相反。Queue 是先进先出。两者都是线程安全的，可用于多线程。

### single_choice · None



- [A] 每处理完一个从队列取出的任务后调用 task_done，join() 才能正确判断所有任务已完成
- [B] put 一个元素后必须调用 task_done，否则队列会阻塞
- [C] task_done 用于清空整个队列
- [D] 不调用 task_done 队列也能正常工作，join 会立即返回

**参考答案**：0

**解析**：task_done 用于告知队列某个已取出的任务处理完成，使内部未完成任务计数递减；当计数为 0 时，处于阻塞的 join() 会返回。若取出后不调用 task_done，join() 会一直阻塞。task_done 不清空队列，也不是 put 后调用。

### single_choice · None



- [A] 默认会阻塞，直到队列中腾出空间；可用 block=False 让其抛出 Full 异常
- [B] 立即成功放入，队列自动扩容
- [C] 立即抛出 ValueError
- [D] 立即丢弃多余元素

**参考答案**：0

**解析**：当队列达到 maxsize 时，put 默认 block=True 会阻塞等待空位。传 block=False（或 timeout 超时）时会抛出 queue.Full。队列不会自动扩容，也不会静默丢弃元素。

### single_choice · None



- [A] 返回的是调用瞬间的近似大小，之后可能立即被其他线程改变，不应据此做严格同步判断
- [B] 返回值永远精确，可放心用它判断是否为空再决定 get
- [C] 调用 qsize() 会阻塞直到队列非空
- [D] qsize() 只能返回 0 或 1

**参考答案**：0

**解析**：qsize() 返回的是某一瞬间的近似值，由于其他线程可能立即改变队列，不能依赖它做严格的同步控制（例如先判断非空再 get 仍可能被抢空而阻塞或抛 Empty）。正确做法是用 try/except Empty 或 block/timeout。

### single_choice · None



- [A] while True: 尝试 get（可设超时或用哨兵值），取到任务处理后调用 task_done，收到结束信号则 break
- [B] 先 while q.qsize()==0: 空转等待，再用 q[0] 取元素
- [C] 直接对队列进行 for 循环遍历取元素
- [D] consumer 直接访问队列内部 deque 私有属性取元素

**参考答案**：0

**解析**：标准写法是在循环中 get（常配合超时或哨兵结束值），处理任务后调用 task_done，收到终止信号时退出。qsize 轮询、下标索引和访问内部私有属性都不是线程安全的正确做法。

### single_choice · None



- [A] 它们都是线程安全的，可在多线程间安全地 put 和 get
- [B] 它们都是线程不安全的，需要手动加锁
- [C] 它们都只支持单生产者单消费者
- [D] 它们都按插入顺序取出元素

**参考答案**：0

**解析**：这三个队列类都实现了内部的锁机制，是线程安全的，支持多生产者多消费者。它们取出顺序不同（FIFO/LIFO/优先级），但都保证线程安全。

### single_choice · None



- [A] 1
- [B] 5
- [C] 3
- [D] 先放入的 5

**参考答案**：0

**解析**：PriorityQueue 每次 get 取出优先级最小（值最小）的元素，因此这里先取出 1。注意它不是 FIFO，与放入顺序无关。
