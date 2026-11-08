# s3u3l2 用 `multiprocessing` 做进程间通信 / `multiprocessing.shared_memory`：让多个进程共享同一块内存

> 来源 `content/lessons/s3u3l2.json`

## py.mp.ipc

# py.mp.ipc：用 `multiprocessing` 做进程间通信

## 一句话直觉

当你的 Python 程序需要**同时利用多个 CPU 核心**（绕过 GIL），就得把工作拆到多个进程里；多个进程既然分开了，就必须像同事之间传纸条一样互相**传数据、传任务、传结果**——这就是 IPC（Inter-Process Communication，进程间通信）。

---

## 1. 为什么需要 IPC：进程之间是「孤岛」

Python 的 `multiprocessing` 会创建**独立的内存地址空间**的进程（process），而不是线程（thread）。好处是可以真正并行；代价是：

- 一个进程里定义的普通变量，另一个进程**看不见**。
- 全局变量、闭包变量、类实例状态，默认**不会被复制过去**（除了通过 `fork` 继承时的初始快照）。

所以要让多个进程协作，必须通过**显式的通信通道**：管道（Pipe）、队列（Queue）、共享内存（shared memory）、管理器（Manager）。这就是本节要讲的核心。

> 关键记忆：**多进程 = 并行能力 + 隔离代价**；IPC 就是为「隔离」付出的沟通成本买单。

---

## 2. 三种主力通道：`Queue`、`Pipe`、`Manager`

按使用频率从高到低：

| 通道 | 场景 | 特点 |
| --- | --- | --- |
| `multiprocessing.Queue` | 生产者-消费者、多对多 | 进程安全，可传任意 pickle 得对象，稍慢 |
| `multiprocessing.Pipe` | 两个进程一对一 | 最快，但只支持两个端点 |
| `multiprocessing.Manager` | 共享 dict/list 等复杂结构 | 方便，但走代理慢 |

```python
# demo_queue_basic.py
import multiprocessing as mp

def worker(q: mp.Queue):
    # 从队列里取任务，把结果放回另一个队列
    while True:
        item = q.get()
        if item is None:  # 约定的「收工信号」
            break
        q.put(item * item)

if __name__ == "__main__":
    q = mp.Queue()
    p = mp.Process(target=worker, args=(q,))
    p.start()

    for n in [1, 2, 3, 4]:
        q.put(n)
    q.put(None)  # 结束信号

    p.join()
    results = [q.get() for _ in range(4)]
    print(results)  # [1, 4, 9, 16]
```

注意点：
- **必须在 `if __name__ == "__main__":` 内启动**，否则 Windows/macOS 的 spawn 模式会无限递归创建进程。
- `Queue` 是跨进程的，不是 `queue.Queue`（那个只在单进程内有效）。

---

## 3. 用 `Pool` 做「任务分发 + 结果收集」

最常用的工程模式：主进程分发任务，子进程算完把结果返回。`Pool` 的 `map` / `apply_async` 内部已经封装了 IPC，不必手写队列。

```python
# demo_pool.py
import multiprocessing as mp

def heavy(x: int) -> int:
    return x * x

if __name__ == "__main__":
    with mp.Pool(processes=4) as pool:
        # 阻塞版：一次性拿到所有结果
        print(pool.map(heavy, range(8)))  # [0, 1, 4, 9, 16, 25, 36, 49]

        # 非阻塞版：按提交顺序异步收集
        async_results = [pool.apply_async(heavy, (i,)) for i in range(8)]
        print([r.get() for r in async_results])
```

工程提示：传给 `Pool` 的函数和参数必须能被 **pickle** 序列化（模块顶层函数、普通类型即可；lambda、闭包、打开的文件句柄不行）。

---

## 4. 两个进程一对一：`Pipe`

`Pipe()` 返回 `(conn1, conn2)` 一对端点。`duplex=True` 时双向，`duplex=False` 时第一个只收、第二个只发。

```python
# demo_pipe.py
import multiprocessing as mp

def sender(conn):
    conn.send({"cmd": "sum", "data": [1, 2, 3]})
    conn.close()

def receiver(conn):
    msg = conn.recv()
    print("got:", msg, "-> result:", sum(msg["data"]))

if __name__ == "__main__":
    a, b = mp.Pipe()          # 默认 duplex=True
    p1 = mp.Process(target=sender, args=(a,))
    p2 = mp.Process(target=receiver, args=(b,))
    p1.start(); p2.start(); p1.join(); p2.join()
```

`Pipe` 底层性能比 `Queue` 好，但只适合两点通信；一旦多个进程同时读写同一端点，需要自己加锁。

---

## 5. 共享状态：`Manager` 与 `shared_memory`

要在进程之间共享一个 dict 或 list，用 `Manager`：

```python
# demo_manager.py
import multiprocessing as mp

def add(shared_list, n):
    shared_list.append(n * n)

if __name__ == "__main__":
    with mp.Manager() as mgr:
        shared = mgr.list()
        procs = [mp.Process(target=add, args=(shared, i)) for i in range(5)]
        for p in procs: p.start()
        for p in procs: p.join()
        print(sorted(shared))  # [0, 1, 4, 9, 16]
```

`Manager` 是把数据放在主进程里的「代理」，操作时会走 IPC，**不适用于高频大量读写**。

如果要共享的是大块数值数组（比如 NumPy），用 Python 3.8+ 的 `multiprocessing.shared_memory.SharedMemory`，能让多个进程直接看到同一段内存，无需序列化：

```python
# demo_shm.py
import multiprocessing as mp
from multiprocessing import shared_memory
import numpy as np

def worker(name):
    shm = shared_memory.SharedMemory(name=name)
    arr = np.ndarray((4,), dtype=np.float64, buffer=shm.buf)
    arr *= 2  # 原地修改，主进程可见
    shm.close()

if __name__ == "__main__":
    a = np.array([1.0, 2.0, 3.0, 4.0])
    shm = shared_memory.SharedMemory(create=True, size=a.nbytes)
    shared_arr = np.ndarray(a.shape, dtype=a.dtype, buffer=shm.buf)
    shared_arr[:] = a[:]
    p = mp.Process(target=worker, args=(shm.name,)); p.start(); p.join()
    print(shared_arr)  # [2. 4. 6. 8.]
    shm.close(); shm.unlink()
```

---

## 选型速查

- 任务分发 / 结果收集 → `Pool`
- 生产者-消费者、多对多 → `Queue`
- 两个进程点对点 → `Pipe`
- 共享 dict/list 等小结构 → `Manager`
- 共享大块数值内存 → `shared_memory`

---

## 动手练习

**目标**：写一个 `word_count_parallel.py`，用多进程统计多个文本文件里所有单词出现次数。

要求：

1. 主进程用 `Pool`，把每个文件路径分给一个子进程。
2. 子进程读文件、分词（`.lower().split()`）、返回一个 `dict[单词, 次数]`。
3. 主进程把所有的 dict 合并，按次数降序打印前 20。
4. 在 `if __name__ == "__main__":` 下运行，并用自己的 README.md 或其他文本文件测试。
5. 进阶：把子进程改成通过 `Queue` 把中间结果发回来，主进程边收边合并。

验收标准：反复运行结果一致；对比如 5000 行文本，4 进程版本比单进程快。

## py.mp.shared_memory

# `multiprocessing.shared_memory`：让多个进程共享同一块内存

## 一句话直觉

**当你用 `multiprocessing` 开多个进程时，数据默认是「复制」的；而 `shared_memory`（共享内存）让多个进程直接读写同一块内存，避免大数组被来回拷贝，从而又快又省内存。**

---

## 1. 为什么需要共享内存？

Python 的 `multiprocessing`（多进程）在启动子进程时，默认使用 **pickle（序列化）** 把参数传给子进程。这意味着：

- 一个 1GB 的 NumPy 数组传 4 个子进程 → 可能多出 4GB 内存占用；
- 每个进程修改的数据 **互相看不见**，因为它们是独立的副本。

而 **shared memory（共享内存）** 是操作系统提供的一种机制：一块物理内存被映射到多个进程的地址空间中，任何一个进程的写入，其他进程立即可见。

Python 3.8 起在标准库中提供了 `multiprocessing.shared_memory`，最常用的两个类：

- `SharedMemory`：直接管理一块原始字节块；
- `ShareableList`：基于共享内存的列表，可直接放基本类型。

> 记忆点：**「共享内存 = 多进程版的全局变量，但是更快更省内存。」**

---

## 2. `SharedMemory`：裸内存块

它的用法非常像 `mmap` 或 `bytearray`：创建时指定字节数，之后可以通过 `.buf` 拿到一个 memoryview（内存视图）来读写。

关键 API：

| 方法/属性 | 作用 |
|---|---|
| `SharedMemory(name=None, create=False, size=0)` | 创建或附着一块共享内存 |
| `shm.buf` | memoryview，用于读写 |
| `shm.name` | 共享内存的名字，其他进程用它来附着 |
| `shm.close()` | 当前进程断开映射（不销毁） |
| `shm.unlink()` | 删除共享内存块（最后一个用户负责）|

代码示例（创建、写入、另一个进程读取）：

```python
from multiprocessing import shared_memory, Process
import numpy as np

# 1) 主进程创建一块能放下 5 个 int64 的共享内存
shm = shared_memory.SharedMemory(create=True, size=5 * 8)

# 2) 把它当成一个长度为 5 的 int64 数组
arr = np.ndarray((5,), dtype=np.int64, buffer=shm.buf)
arr[:] = [1, 2, 3, 4, 5]

# 3) 子进程通过名字附着到同一块内存
def worker(name):
    existing = shared_memory.SharedMemory(name=name)
    a = np.ndarray((5,), dtype=np.int64, buffer=existing.buf)
    a[0] = 999                      # 直接改写
    existing.close()

p = Process(target=worker, args=(shm.name,))
p.start(); p.join()

print(arr)         # [999 2 3 4 5] —— 主进程看到了修改
shm.close()
shm.unlink()        # 由创建者最后清理
```

**三个关键结论**：

1. 每块共享内存都有一个 `name`（字符串），子进程靠它附着；
2. `buf` 是 raw bytes，用 `numpy.ndarray(..., buffer=...)` 或 `struct` 解释成你需要的类型；
3. **`close()` 必须两件事分开做**：每个进程都要 `close()`；由创建者调用一次 `unlink()`。

---

## 3. `ShareableList`：更好用的封装

如果你只是想共享一个「列表」，不需要裸 memoryview，可以用 `ShareableList`。它支持 `int / float / str / bytes / None / bool`（定长字符串）。

```python
from multiprocessing import shared_memory, Process

sl = shared_memory.ShareableList([1, 2.5, 'hi', None])

def worker(name):
    other = shared_memory.ShareableList(name=name)
    other[0] = 42
    print('子进程看到:', list(other))
    other.shm.close()

p = Process(target=worker, args=(sl.shm.name,))
p.start(); p.join()

print('主进程看到:', list(sl))   # [42, 2.5, 'hi', None]
sl.shm.close()
sl.shm.unlink()
```

**要点**：

- `ShareableList` 内部就是包了一个 `SharedMemory`，可通过 `sl.shm` 拿到；
- 元素类型在创建时确定，之后不能改变元素类型；
- 字符串是定长的（用最大长度决定），比普通 `list` 更节省。

---

## 4. 同步问题：共享 ≠ 安全

共享内存只解决「数据在哪里」，**不解决「谁先写、谁读到了半成品」**。多个进程同时写同一块内存时，必须自己加锁。

```python
from multiprocessing import shared_memory, Process, Lock
import numpy as np

shm = shared_memory.SharedMemory(create=True, size=4)
arr = np.ndarray((1,), dtype=np.int32, buffer=shm.buf)
arr[0] = 0
lock = Lock()

def inc(name, lock):
    other = shared_memory.SharedMemory(name=name)
    a = np.ndarray((1,), dtype=np.int32, buffer=other.buf)
    for _ in range(100_000):
        with lock:      # 关键：读-改-写必须原子
            a[0] += 1
    other.close()

ps = [Process(target=inc, args=(shm.name, lock)) for _ in range(4)]
[p.start() for p in ps]; [p.join() for p in ps]
print(arr[0])   # 400000
shm.close(); shm.unlink()
```

> 一句话：**共享内存给「位置」，锁给「秩序」。**

---

## 5. 生命周期与资源泄漏

`shared_memory` 有两个容易踩的生命周期坑：

1. **`close()` 只是当前进程脱离映射**，物理内存仍然存在；
2. **`unlink()` 才真正删除**，但已有映射的进程仍可继续访问，直到它们也 `close()`；
3. 如果程序崩溃没 `unlink()`，名字会残留在 `/dev/shm` 下（Linux）或系统句柄表中。

工程写法：用 `try/finally` 保证清理。

```python
from multiprocessing import shared_memory

shm = shared_memory.SharedMemory(create=True, size=1024)
try:
    ...  # 业务逻辑，可能会异常
finally:
    shm.close()
    shm.unlink()
```

---

## 6. 什么时候用、什么时候别用

| 场景 | 建议 |
|---|---|
| 大数组、图像、模型权重多进程共享 | ✅ 用 `SharedMemory` + `numpy` |
| 简单的小 list / 一两个标量 | ✅ 用 `ShareableList` 或直接 `multiprocessing.Value/Array` |
| 结构化对象、字典 | ❌ 需要自己序列化放到 buffer，不如用管道或 `Manager` |
| 跨机器 | ❌ 共享内存只在本机有效 |
| 不希望自己管锁 | ❌ 优先考虑 `Queue` / `Pool`，复杂度更低 |

**原则**：先问「数据大不大、是不是频繁读」；大且只读 → 共享内存收益最大；小或需要复杂同步 → 用更高级的抽象。

---

## 术语速查

- **shared memory（共享内存）**：多个进程可见的同一块物理内存。
- **memoryview（内存视图）**：Python 中零拷贝访问 buffer 的协议对象。
- **serialization / pickle（序列化）**：把 Python 对象转成字节流以便传输。
- **unlink（解链）**：删除共享内存对象的名字，使之后无法再被附着。

```python
import numpy as np
from multiprocessing import Process, Lock
from multiprocessing import shared_memory


def worker_accumulate(name, lock, iters):
    """子进程：通过名字附着共享内存，对第一个 int64 累加。"""
    shm = shared_memory.SharedMemory(name=name)
    arr = np.ndarray((1,), dtype=np.int64, buffer=shm.buf)
    for _ in range(iters):
        with lock:            # 读-改-写需要互斥
            arr[0] += 1
    shm.close()               # 只脱离映射，不销毁


if __name__ == '__main__':
    n_proc, iters = 4, 100_000

    # 1) 主进程创建共享内存：1 个 int64
    shm = shared_memory.SharedMemory(create=True, size=8)
    arr = np.ndarray((1,), dtype=np.int64, buffer=shm.buf)
    arr[0] = 0
    lock = Lock()

    try:
        # 2) 启动多个子进程，各自累加
        ps = [Process(target=worker_accumulate,
                      args=(shm.name, lock, iters)) for _ in range(n_proc)]
        for p in ps: p.start()
        for p in ps: p.join()

        # 3) 主进程直接读到最终结果，无需 IPC 回传
        print('final =', arr[0], '(expected', n_proc * iters, ')')
    finally:
        # 4) 创建者负责清理
        shm.close()
        shm.unlink()
```


---

## 本课题目

### single_choice · None



- [A] Queue 中的对象会被直接共享，子进程修改对象会影响父进程中的同一对象
- [B] Queue 通过序列化（pickle）传递数据，因此传递的是对象的副本而非引用
- [C] Queue 只能传递字符串和数字，不能传递自定义类的实例
- [D] Queue 的 put 方法在队列满时一定会抛出 QueueFull 异常

**参考答案**：1

**解析**：multiprocessing.Queue 在进程间通过 pickle 序列化传输数据，接收方得到的是反序列化后的副本，因此对副本的修改不会影响发送方。A 错在进程间内存不共享（除非用共享内存/Manager）；C 错在自定义对象只要可 pickle 就能传；D 错在默认 put 会阻塞而非一定抛异常。

### single_choice · None



- [A] 输出 hello
- [B] 抛出 EOFError，因为子进程关闭了连接
- [C] 输出 None
- [D] 程序死锁

**参考答案**：0

**解析**：子进程通过 child 端 send 数据，父进程通过 parent 端 recv 能正常收到 'hello'。EOFError 只在另一端已关闭且没有数据可读时发生；这里先 send 再 close，数据仍在管道中。

### single_choice · None



- [A] 队列自动扩容，不会出问题
- [B] 队列满后 put 默认阻塞，可能导致所有放入进程挂起
- [C] 队列满后自动丢弃旧数据
- [D] 队列满后 put 立即抛出异常

**参考答案**：1

**解析**：multiprocessing.Queue 有容量上限（默认较大但有界），当队列满时 put 默认阻塞，若没有消费者，生产者会一直等待。不会自动扩容、自动丢弃或默认抛异常。

### single_choice · None



- [A] Queue 基于 Pipe 和锁实现，提供更高级的接口和更好的多生产者多消费者支持
- [B] Pipe 基于 Queue 实现，所以 Queue 更底层
- [C] Pipe 只能用于两个进程，Queue 也只能用于两个进程
- [D] Queue 内部不使用任何锁，因此速度总是比 Pipe 快

**参考答案**：0

**解析**：multiprocessing.Queue 内部使用 Pipe 和锁实现，支持多个生产者和消费者，接口更高级。B 颠倒关系；C 错在 Queue 可支持多进程；D 错在 Queue 内部使用锁，且速度不一定比 Pipe 快。

### single_choice · None



- [A] 父进程先 join 子进程，子进程试图向 Queue 放入大量数据而父进程尚未取出
- [B] 父进程先启动子进程，然后从 Queue 取数据，最后 join
- [C] 使用 Queue 传递小量数据
- [D] 使用 Pipe 进行双向通信

**参考答案**：0

**解析**：如果子进程向 Queue 放入大量数据而队列缓冲区满，子进程会阻塞在 put；此时父进程若先 join 等待子进程结束，就会形成死锁。应先消费队列数据再 join，或使用有界数据量。

### single_choice · None



- [A] 管道自动扩容，正常完成
- [B] 由于管道缓冲区有限，双方可能互相阻塞导致死锁
- [C] 数据被自动丢弃
- [D] 程序抛出 ValueError

**参考答案**：1

**解析**：管道有有限的缓冲区。如果双方都只 send 不 recv，当缓冲区写满后 send 会阻塞，双方互相等待，形成死锁。不会自动扩容或丢数据。

### single_choice · None



- [A] Connection 对象可以安全地被多个进程同时读写
- [B] Connection 对象应避免被多个进程同时使用，通常一端只由一个进程使用
- [C] Connection 对象只能在创建它的进程中使用
- [D] Connection 对象没有 recv 方法

**参考答案**：1

**解析**：Connection 对象不是进程安全的，多个进程同时读写同一端可能导致数据混乱。通常一端给一个进程使用。A、C、D 都不正确。

### single_choice · None



- [A] 主进程读取完所有预期结果后，直接调用 terminate 杀掉所有子进程
- [B] 主进程读取完所有结果后，先 join 所有子进程，再关闭 Queue
- [C] 子进程写入后立即调用 Queue.close()，主进程继续读取
- [D] 不进行任何关闭操作，程序结束后系统自动回收

**参考答案**：1

**解析**：合理的做法是主进程收集完结果后 join 子进程，确保子进程已退出，再关闭队列。直接 terminate 可能丢失数据；子进程 close 会影响其他进程；不关闭虽在程序退出时可能被回收，但不够规范。

### single_choice · None



- [A] Queue 和 Pipe 都是 multiprocessing 模块提供的进程间通信方式
- [B] 进程间通信的数据通常需要可序列化（pickle）
- [C] multiprocessing 的共享内存对象（Value、Array）可以完全替代 Queue 的所有功能
- [D] Manager 可以创建可在进程间共享的代理对象

**参考答案**：2

**解析**：共享内存只适合简单数据类型，不能完全替代 Queue 传递任意可 pickle 对象的功能。A、B、D 都是正确的描述。

### single_choice · None



- [A] 会丢失，因为子进程退出后队列被销毁
- [B] 不会丢失，数据已写入队列，父进程仍可读取
- [C] 取决于数据大小，小数据会丢失
- [D] 取决于操作系统，Windows 上一定丢失

**参考答案**：1

**解析**：数据一旦成功 put 到 Queue 中，就保存在队列的内部缓冲区里，子进程退出不会清除已放入的数据（只要父进程仍持有队列引用并读取）。因此不会丢失。

### single_choice · None



- [A] 字符串
- [B] 列表和字典
- [C] 打开的文件对象
- [D] 自定义的可 pickle 类的实例

**参考答案**：2

**解析**：打开的文件对象通常不可 pickle，因此不能直接通过 Queue 传递。字符串、列表、字典以及可 pickle 的自定义对象都可以传递。

### single_choice · None



- [A] 它们提供了基于网络或管道的更底层的进程间通信接口
- [B] 它们只能在同一台机器上的父子进程间使用
- [C] 它们完全等同于 Queue，没有区别
- [D] 它们只能传递字符串

**参考答案**：0

**解析**：multiprocessing.connection 提供 Listener/Client，可基于套接字或管道进行更灵活的进程间通信，甚至可跨机器（使用网络地址）。B 错在可跨机器；C 错在与 Queue 接口和用途不同；D 错在可传可 pickle 对象。

### single_choice · None



- [A] Pipe() 默认返回两个连接对象，分别用于两个进程，且数据只能单向流动
- [B] Pipe() 返回的两个连接对象都是双向的，任一端都可以 send 和 recv
- [C] Pipe 底层使用网络套接字，因此只能用于跨主机通信
- [D] Pipe 返回的连接对象不能被多个进程同时使用

**参考答案**：1

**解析**：multiprocessing.Pipe() 默认 duplex=True，返回的两个 Connection 都是双向的，两端都可 send/recv。A 描述的是 duplex=False 的情况；C 错在 Pipe 基于管道（或本地套接字），不是网络套接字；D 表述过于绝对，两端各给一个进程是常见用法。

### single_choice · None



- [A] 把 Queue 对象作为参数传给 Process 的 target 函数
- [B] 把 Queue 对象定义为模块级全局变量，在 if __name__ == '__main__' 之前创建
- [C] 把 Queue 对象定义为全局变量，在 if __name__ == '__main__' 块外声明但块内使用
- [D] 把 Queue 对象放在 if __name__ == '__main__' 块内创建并传给子进程

**参考答案**：1

**解析**：Windows 使用 spawn 启动方式，会重新导入主模块。若 Queue 在模块顶层（if __name__ 之前）创建，子进程导入模块时会重新创建另一个 Queue，导致父子进程使用的不是同一个对象。应在 __main__ 保护块内创建并作为参数传递。

### single_choice · None



- [A] 两者都可以直接在进程之间安全传递数据
- [B] multiprocessing.Queue 可用于进程间通信，而 queue.Queue 只适合线程间通信
- [C] queue.Queue 比 multiprocessing.Queue 更适合跨进程，因为它更快
- [D] 两者内部实现完全相同，只是模块名不同

**参考答案**：1

**解析**：queue.Queue 基于线程锁，只保证线程安全，不保证跨进程安全；multiprocessing.Queue 专为进程间通信设计（底层有管道和锁）。A、C、D 都错误地认为 queue.Queue 可以安全跨进程。

### single_choice · None



- [A] 立即抛出 Empty 异常
- [B] 立即返回 None
- [C] 阻塞等待，直到有数据或超时（若设置了 timeout）
- [D] 导致整个程序崩溃

**参考答案**：2

**解析**：multiprocessing.Queue.get() 默认是阻塞的，会一直等待直到有数据。若设置了 timeout 参数并且超时，才抛出 queue.Empty。立即返回 None 或崩溃都不正确。

### single_choice · None



- [A] 输出 [1, 2, 3]
- [B] 输出 [1, 2, 3, 99]
- [C] 输出 [99]
- [D] 抛出异常，因为列表不能通过 Queue 传递

**参考答案**：1

**解析**：列表是可 pickle 的对象，可以放入 Queue。子进程取出的是副本，修改后放回，父进程再取出的是修改后的副本，因此输出 [1, 2, 3, 99]。A 忽略了子进程的修改；C 错误；D 错误，列表完全可以通过 Queue 传递。

### single_choice · None



- [A] 立即抛出 EOFError
- [B] 立即返回 None
- [C] 一直阻塞等待数据
- [D] 自动创建新进程

**参考答案**：2

**解析**：recv() 是阻塞调用，只要连接的另一端没有关闭且没有数据，就会一直等待。只有在对端关闭后仍无数据才抛 EOFError。立即返回 None 或自动创建进程都不对。

### single_choice · None



- [A] Manager().Queue() 可以跨越多台机器使用
- [B] Manager().Queue() 支持更复杂的对象代理，但通常比 multiprocessing.Queue 慢
- [C] multiprocessing.Queue() 不能传递自定义对象
- [D] 两者性能完全相同，可以随意替换

**参考答案**：1

**解析**：Manager().Queue() 通过管理器进程代理，支持更灵活的对象共享，但每次操作涉及进程间通信，通常比 multiprocessing.Queue 慢。A 错在不能跨机器；C 错在 multiprocessing.Queue 可以传可 pickle 的自定义对象；D 错在性能不同。

### single_choice · None



- [A] 需要传递大量数据且对性能敏感，多个进程频繁读写同一块数据
- [B] 需要传递 Python 对象图（如嵌套字典和自定义类实例）
- [C] 需要保证消息的顺序性
- [D] 需要解耦生产者和消费者，生产者不关心消费者何时处理

**参考答案**：0

**解析**：共享内存适合高频读写同一块简单数据，避免序列化开销。B 更适合 Queue 或 Manager；C 队列本身保证顺序；D 是队列的典型解耦场景。

### single_choice · None



- [A] 共享内存中的数据默认会被进程间的锁保护，读写是原子的
- [B] 共享内存让多个进程可以直接读写同一块物理内存，绕过了常规的序列化/管道传输
- [C] 共享内存只能用于同一台机器上的线程，不能跨进程
- [D] 共享内存中的对象会自动进行垃圾回收，进程退出后会立刻释放

**参考答案**：1

**解析**：共享内存的核心价值是多个进程映射同一块物理内存区域，直接读写而不必通过 pickle 在管道/队列中序列化传输。它本身不提供锁，读写并非自动原子，也不会在进程退出时自动释放（需要显式关闭和 unlink）。

### single_choice · None



- [A] array 模块的 array
- [B] numpy 的 ndarray，通过 numpy.ndarray 指定 buffer 和 shape/dtype
- [C] struct 模块的 pack
- [D] memoryview 会自动提供多维索引

**参考答案**：1

**解析**：numpy.ndarray 支持通过 buffer 参数直接映射共享内存，从而以指定 dtype 和 shape 读写，无需复制。array 与 memoryview 只能提供一维/字节级视图，struct 用于打包单个值。

### multi_choice · None



- [A] 它属于标准库的一部分，无需额外安装
- [B] 共享内存块可以通过名字被其它进程附着
- [C] close 会删除底层共享内存块
- [D] unlink 用于请求删除底层共享内存块
- [E] 默认情况下它会对并发访问加锁

**参考答案**：[0, 1, 3]

**解析**：shared_memory 是标准库模块；块可用名字被其它进程映射；unlink 请求删除底层块。close 只是解除当前进程映射，默认也不提供锁。

### multi_choice · None



- [A] 配合 multiprocessing.Lock 保护临界区
- [B] 使用数组下标划分各进程负责的区间，避免写同一位置
- [C] 依赖 memoryview 自动加锁
- [D] 使用原子化的操作或分块归约后再汇总
- [E] 让各进程通过 Queue 发送指令，用共享内存只做单向写入

**参考答案**：[0, 1, 3, 4]

**解析**：共享内存无内置锁。可用 Lock、划分区间、分块归约或与 Queue 协同使用来减少竞态。memoryview 不会自动加锁。

### multi_choice · None



- [A] 最后不再使用时应调用 unlink 请求删除底层块
- [B] close 用于释放当前进程对该块的映射
- [C] 如果所有进程都未 unlink，某些平台上共享内存块可能残留到重启
- [D] unlink 会立即让所有进程无法继续访问映射
- [E] 创建共享内存时系统会自动设置过期时间

**参考答案**：[0, 1, 2]

**解析**：close 解除映射、unlink 请求删除底层块；若无人 unlink，块可能在系统中残留。unlink 不会让已有映射立刻失效（取决于平台/引用计数），系统也不会自动设置过期时间。

### fill_blank · None



**参考答案**：["name", ".name"]

**解析**：SharedMemory 实例的 name 属性保存该块的名字，其它进程可用它来附着（create=False）。

### fill_blank · None



**参考答案**：["unlink", "unlink()"]

**解析**：unlink 请求删除共享内存块，通常由最后一个使用完毕的进程调用；close 只是解除当前映射。

### fill_blank · None



**参考答案**：["ndarray", "numpy.ndarray", "np.ndarray"]

**解析**：numpy.ndarray 支持 buffer 协议，可基于共享内存的 buf 创建数组视图，配合 dtype、shape 直接读写。

### code_reading · None



**参考答案**：创建时应使用 SharedMemory(create=True, size=8) 并记录 shm.name；子进程附着时应使用 SharedMemory(name=name, create=False)。若子进程用 create=True 并用相同名字，会因同名块已存在而抛 FileExistsError，而不是附着到已有块。

**解析**：共享内存以名字标识。create=True 表示新建，同名冲突会报错；附着已有块必须 create=False 并传 name。

### code_reading · None



**参考答案**：好处是避免了通过 pickle 序列化并经由管道复制传输整块数组的开销，多个进程可直接读写同一物理内存。buffer=shm.buf 让 numpy 在这块共享内存字节缓冲区之上创建数组视图，写入即直接写入共享内存，无需额外拷贝。

**解析**：共享内存的核心优势是零拷贝直读直写；ndarray 的 buffer 参数把共享内存映射为按 dtype/shape 解释的数组视图。

### code_reading · None



**参考答案**：通常不能。unlink 请求删除底层共享内存块后，用 name='foo' 再附着一般会失败（找不到该名字并抛 FileNotFoundError）；close 只解除当前进程映射。若要多个进程先后使用，应在所有使用者释放后再由一方 unlink。

**解析**：unlink 请求删除块，名字随之失效；必须在所有使用者完成后再删除，否则后续按名字附着会失败。

### scenario · None



**解析**：结果错乱通常是因为多个进程并发读写同一区域而无同步，产生竞态；残留是因为进程未在适当时候 close 并 unlink 共享内存。改进：用 Lock（或划分区间）保护临界区，确保各进程 close 后由一方 unlink，并处理异常路径下的清理。

### single_choice · None



- [A] 父进程创建后立即 unlink，子进程结束后再 close
- [B] 所有使用该共享内存的进程都先 close，最后一个进程再 unlink
- [C] 只需要父进程 close 即可，子进程无需处理
- [D] unlink 会自动关闭所有进程的映射，所以先 unlink 再 close

**参考答案**：1

**解析**：close 释放当前进程对该共享内存的映射，unlink 请求删除底层共享内存块。若在其它进程仍在使用时 unlink，可能造成悬空或资源被提前回收。规范做法是各进程 close 后再由一方 unlink。

### single_choice · None



- [A] 共享内存块完全在磁盘上，与操作系统无关
- [B] 底层实现依赖操作系统的共享内存机制，不同平台创建/回收的细节不同，曾有平台相关的差异与 bug
- [C] 在 Windows 上 unlink 是禁止调用的
- [D] Windows 只能通过文件读写来模拟共享内存

**参考答案**：1

**解析**：共享内存依赖操作系统的共享内存实现（如 POSIX shm 与 Windows 命名共享内存），不同平台的创建、回收细节与历史行为存在差异，因此跨平台时要注意生命周期管理。

### single_choice · None



- [A] 创建一个新的共享内存块，如果同名已存在会抛出 FileExistsError
- [B] 总是创建或复用同名块，不怕重名
- [C] 仅在 Windows 上有效
- [D] 创建后自动 unlink

**参考答案**：0

**解析**：create=True 表示请求创建新块；若同名块已存在会抛 FileExistsError。若要附着到已有块，应使用 create=False 并传入 name。

### single_choice · None



- [A] 调用 SharedMemory(name=已知名字, create=False)
- [B] 调用 SharedMemory(size=同样大小, create=True)
- [C] 调用 SharedMemory.create(name)
- [D] 重新创建同名块即可自动合并

**参考答案**：0

**解析**：附着已有块需用已知的名字并设置 create=False，这样会映射到已存在的共享内存而不是新建。传入相同的 size 并 create=True 会导致 FileExistsError。

### single_choice · None



- [A] Queue 底层也是共享内存，所以性能相同
- [B] 共享内存适合大块数据的高频读写，但需要自行同步；Queue/Pipe 自带同步但需序列化，数据量大时开销更高
- [C] Pipe 不需要序列化，因此总是比共享内存快
- [D] 共享内存不能与 Queue 同时使用

**参考答案**：1

**解析**：共享内存避免序列化开销，适合大块/高频数据，但不自带锁，需要自行同步；Queue/Pipe 基于管道并对对象做 pickle 序列化，因此在大数据量时开销更大。

### single_choice · None



- [A] 在进程间传递少量字符串命令
- [B] 多个进程频繁读写同一幅大尺寸图像数组
- [C] 需要严格顺序地传输日志行
- [D] 传递不可 pickle 的 lambda 函数

**参考答案**：1

**解析**：大尺寸数组的高频读写用共享内存可避免反复序列化拷贝，性能优势明显。少量消息、严格顺序传输更适合 Queue；而不可 pickle 的对象通过 Queue/共享内存都难以直接传递。

### single_choice · None



- [A] buf 是一个 memoryview，可切片或交给 numpy 等库按字节映射
- [B] buf 是 Python list，可以直接 append
- [C] buf 只在 Windows 上存在
- [D] buf 每次访问都会复制一份数据

**参考答案**：0

**解析**：buf 提供的是一个 memoryview，指向共享内存的字节缓冲区，可切片或传给 numpy.ndarray 等按 buffer 协议映射，通常不会复制。

### single_choice · None



- [A] 操作系统保证写入串行化，结果始终一致
- [B] 没有内置同步，可能出现竞态，读到中间状态或最终值不确定
- [C] 会直接抛出异常并终止进程
- [D] 共享内存会自动加读写锁，等同于互斥量

**参考答案**：1

**解析**：SharedMemory 只提供内存映射，不提供同步原语。并发写入会产生竞态，结果不确定，需要配合 multiprocessing.Lock 等同步手段。
