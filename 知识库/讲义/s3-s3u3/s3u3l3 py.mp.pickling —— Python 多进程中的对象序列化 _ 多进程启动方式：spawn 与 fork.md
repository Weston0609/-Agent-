# s3u3l3 py.mp.pickling —— Python 多进程中的对象序列化 / 多进程启动方式：spawn 与 fork

> 来源 `content/lessons/s3u3l3.json`

## py.mp.pickling

# py.mp.pickling —— Python 多进程中的对象序列化

> **一句话直觉**：多进程（multiprocessing）要把一个 Python 对象交给另一个进程时，必须先把对象“冻僵”（序列化成字节流）再送过去——这就是 pickling；不理解它，你的多进程代码就会莫名报错或悄悄变慢。

前置：无。本节从“为什么需要序列化”讲到“如何为自定义类定制序列化规则”。

---

## 1. 为什么需要 pickling？进程之间不共享内存

我们先用一个最小例子感受“进程隔离”。普通 Python 程序里，线程（thread）共享同一块内存，所以变量可以互相看见；但进程（process）有独立的地址空间，一个进程里创建的对象，另一个进程根本看不到。

要让子进程拿到对象，操作系统只能帮你搬运**字节**。于是 Python 需要一套“对象 ↔ 字节”的双向转换协议，这就是 pickle。

```python
import pickle

data = {"name": "小明", "scores": [90, 85, 78], "active": True}

# 序列化（serialize / pickle）：对象 -> bytes
blob = pickle.dumps(data)
print(type(blob), len(blob))   # <class 'bytes'> 一段二进制

# 反序列化（deserialize / unpickle）：bytes -> 对象
restored = pickle.loads(blob)
print(restored == data)        # True
print(restored is data)        # False —— 是一个全新的对象
```

这就是 pickling 的本质：**把一个对象图（object graph）压成字节流，之后可以在同一个或不同的进程里重建它**。

---

## 2. pickle 的协议版本与常见用法

pickle 有多个**协议版本（protocol）**，版本越高，压缩率/速度通常越好，但对 Python 版本有要求。Pickle Protocol 5（Python 3.8+）支持 out-of-band 缓冲区，能把大数组零拷贝地传出去。

```python
import pickle

obj = list(range(10))

# 默认使用当前解释器支持的最高协议
b_default = pickle.dumps(obj)

# 显式指定协议版本（推荐写清楚，便于跨环境复现）
b5 = pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL)

# 保存到文件
with open("obj.pkl", "wb") as f:      # 注意 'wb'：二进制写
    pickle.dump(obj, f)

# 从文件读取
with open("obj.pkl", "rb") as f:      # 注意 'rb'：二进制读
    loaded = pickle.load(f)
print(loaded)
```

工程上应当养成两个习惯：明确写 `protocol=`，保存文件时永远用二进制模式（`'b'`）。

---

## 3. 哪些东西能 pickle，哪些不能

pickle 并非万能。它大致能处理：数字、字符串、字节、列表、元组、字典、集合、**用户自定义类的实例**（前提是类可以在反序列化进程里被导入）、以及实现 `__reduce__` / `__getstate__` 等协议方法的对象。

**不能** pickle 的典型对象有：打开的文件句柄、socket、线程、数据库连接、lambda 函数（部分情况）、在 `__main__` 之外无法导入的本地函数、带有不可序列化属性的对象等。

```python
import pickle

class Point:
    def __init__(self, x, y):
        self.x, self.y = x, y
    def __repr__(self):
        return f"Point({self.x}, {self.y})"

p = Point(1, 2)
b = pickle.dumps(p)
print(pickle.loads(b))          # Point(1, 2) —— 自定义类 OK

# 但这些会失败：
f = open("obj.pkl", "rb")
try:
    pickle.dumps(f)
except TypeError as e:
    print("无法 pickle：", e)  # cannot pickle '_io.BufferedReader' object
f.close()
```

> 一个常见陷阱：在类里定义了 `__init__` 后，pickle 默认**不会调用 `__init__`** 来恢复对象，而是绕过它、直接往 `__dict__` 里塞数据。这意味着初始化逻辑不会重新执行。

---

## 4. 在 multiprocessing 中的 pickling

`multiprocessing` 正是 pickle 的主战场。用 `Process(target=..., args=...)` 启动子进程、用 `Queue` / `Pipe` 传数据、返回任务结果，背后全都是 pickle。

```python
import multiprocessing as mp

def square(x):
    return x * x

def worker(input_q, output_q):
    while True:
        item = input_q.get()
        if item is None:      # 毒丸，通知退出
            break
        output_q.put(square(item))   # 结果会被 pickle 后送回去

if __name__ == "__main__":            # Windows 上必须有这一行
    in_q, out_q = mp.Queue(), mp.Queue()
    p = mp.Process(target=worker, args=(in_q, out_q))
    p.start()

    for i in [1, 2, 3]:
        in_q.put(i)
    in_q.put(None)

    results = [out_q.get() for _ in range(3)]
    p.join()
    print(results)                    # [1, 4, 9]
```

几个必须记住的工程要点：

1. **`if __name__ == "__main__":`**：在 spawn 启动方式（Windows、macOS 默认）下，子进程会重新导入主模块；不写这行会无限递归启动子进程。
2. **pickle 是深拷贝（deep copy）式的**：通过 Queue 传一个 100 MB 的 dict，接收端拿到的是一份**完全独立的副本**，不是共享引用。这既安全也昂贵。
3. **共享内存（shared memory）才是不拷贝的方案**：`mp.Value`、`mp.Array`、`mp.shared_memory` 用于真正需要跨进程共享的场景，但它们只支持有限的原始类型/字节块。

---

## 5. 定制自己的 pickling 行为

有时候默认的序列化太大、太慢，或者要序列化一个带资源句柄的对象。这时可以实现以下方法之一（优先级从高到低）：

- `__reduce__` —— 最底层、最灵活，返回 `(callable, args)` 或五元组；
- `__getstate__` / `__setstate__` —— 控制对象“内容”的写出与恢复，最常用；
- `__getnewargs__` —— 控制传给 `__new__` 的参数。

```python
import pickle

class Session:
    def __init__(self, user, token, socket_like):
        self.user = user
        self.token = token
        self.socket_like = socket_like   # 不可序列化的资源

    def __getstate__(self):
        # 只保存能序列化的字段，丢弃资源句柄
        state = self.__dict__.copy()
        state.pop("socket_like", None)
        return state

    def __setstate__(self, state):
        # 反序列化时恢复字段，并重建资源
        self.__dict__.update(state)
        self.socket_like = object()      # 真实工程里这里要重建连接

s = Session("小明", "t0ken", object())
b = pickle.dumps(s)
s2 = pickle.loads(b)
print(s2.user, s2.token, s2.socket_like is not None)
# 小明 t0ken True
```

这个模式在多进程工程中非常关键：**进程间传递的对象往往带有不可序列化的运行时资源，需要你显式裁剪状态**。

---

### 小结

| 概念 | 作用 |
| --- | --- |
| pickle.dumps / load(s) | 内存里的对象 ↔ 字节 |
| pickle.dump / load | 对象 ↔ 文件 |
| protocol | 控制输出格式与兼容性 |
| `__getstate__` / `__setstate__` | 定制对象序列化行为 |
| multiprocessing | 靠 pickle 跨进程搬运对象 |
| shared_memory / Value / Array | 真正的跨进程共享，避免拷贝 |

---

## 动手练习

**任务**：写一个进程池（`multiprocessing.Pool`），并行地把一个 `list[dict]` 里所有的“学生记录”处理一番，并把结果由子进程返回主进程。

要求：

1. 定义一个 `Student` 类，包含 `name`、`scores`（list）和一个**不可序列化的属性** `meta_handle = open(...)`（或任意文件对象），实现 `__getstate__` / `__setstate__` 让它在 pickle 时被自动丢弃、反序列化时被重建为 `None`。
2. 定义一个顶层函数 `avg_score(student: Student) -> dict`，返回 `{"name": ..., "avg": ...}`。
3. 主进程用 `Pool(4).map(avg_score, students)`，输出每个学生的平均分。
4. 故意尝试把 `Student` 中的一个属性设为 `lambda x: x`，观察报错信息（`AttributeError: Can't pickle local object ...`），并在注释里说明原因。
5. 写完后，把 `Pool` 换成 `mp.Queue` + 多个 `Process`，对比两种写法的代码量与出错点。

交付物：一个可运行的 `try_pickle.py` 源文件 + 一段不超过 10 行的 README，说明你从“pickle 失败”中学到了什么。

## py.mp.spawn_fork

# 多进程启动方式：spawn 与 fork

## 一句话直觉

当你用 `multiprocessing` 启动子进程时，Python 必须先决定“如何把一个进程复制/创建出来”；`spawn` 和 `fork` 就是两种最常见的启动方式（start method），选错会导致性能差异、死锁、甚至跨平台失败。

---

## 1. 为什么需要“启动方式”这个概念

Python 的 `multiprocessing`（多进程）不是直接调用操作系统内核创建进程就完事。它有一个 **启动方式（start method）** 的概念，用来决定：

- 子进程如何获得父进程的代码和内存状态；
- 子进程如何导入主模块；
- 父进程与子进程之间如何共享/传递数据。

不同操作系统默认不同：

| 平台 | 默认启动方式 |
|------|--------------|
| Linux | `fork` |
| macOS (Python 3.8+) | `spawn` |
| Windows | `spawn` |

所以，如果你的代码只在 Linux 上跑，默认可能是 `fork`；一旦迁移到 Windows/macOS，行为会变，这就是为什么要显式理解并控制它。

---

## 2. fork 是什么：复制当前进程

`fork`（分叉）是 Unix 系统调用。调用后，操作系统会复制当前进程的整个内存空间给子进程。

**关键结论：**

- 子进程一开始几乎和父进程一模一样（代码、变量、打开的文件等）。
- 启动快，内存是写时复制（copy-on-write，写时复制）。
- 在多线程程序中，`fork` 可能造成子进程只复制了部分线程状态，容易死锁。
- 在 macOS 上已不推荐，因为系统底层限制。

```python
# fork 示例：子进程能直接看到父进程定义的全局变量
import multiprocessing as mp
import os

# 只有 Unix 才支持 fork
if hasattr(os, "fork"):
    mp.set_start_method("fork", force=True)

    GLOBAL_VALUE = "我在父进程里"

    def worker():
        # fork 方式下，子进程直接继承了 GLOBAL_VALUE
        print(f"[fork 子进程] 看到全局变量: {GLOBAL_VALUE}")

    if __name__ == "__main__":
        p = mp.Process(target=worker)
        p.start()
        p.join()
```

> 注意：Windows 没有 `os.fork`，这段代码在 Windows 上会跳过 `set_start_method`，行为不同。

---

## 3. spawn 是什么：启动一个全新的 Python 解释器

`spawn`（孵化）会启动一个全新的 Python 解释器进程。

**关键结论：**

- 子进程不会继承父进程的内存状态，只继承必要的信息。
- 子进程会重新导入主模块（`__main__`），所以必须用 `if __name__ == "__main__":` 保护启动代码。
- 启动比 `fork` 慢，但更安全、跨平台一致。
- 所有需要传给子进程的数据必须可序列化（pickle，序列化）。

```python
# spawn 示例：必须用 if __name__ == "__main__" 保护
import multiprocessing as mp

mp.set_start_method("spawn", force=True)

def worker(name):
    # name 是通过 pickle 序列化传进来的，不是继承父进程内存
    print(f"[spawn 子进程] 收到参数: {name}")

if __name__ == "__main__":
    p = mp.Process(target=worker, args=("hello",))
    p.start()
    p.join()
```

---

## 4. 什么时候用哪个：工程判断

**关键结论：**

- 需要跨平台一致：用 `spawn`。
- 程序里有多线程，或用了 CUDA/某些 C 扩展：优先 `spawn`，避免 `fork` 死锁。
- 只跑 Linux，追求启动速度、想临时继承父进程状态：可以考虑 `fork`。
- 想手动控制：用 `mp.get_context("spawn")` 或 `mp.get_context("fork")`，而不是只改全局。

```python
# 用 get_context 显式选择启动方式，比全局 set_start_method 更干净
import multiprocessing as mp

def worker(msg):
    print(f"[{mp.current_process().name}] {msg}")

if __name__ == "__main__":
    # 显式使用 spawn 上下文
    ctx = mp.get_context("spawn")
    p = ctx.Process(target=worker, args=("来自 spawn 上下文",))
    p.start()
    p.join()

    # 在支持的平台上，也可以显式使用 fork 上下文
    import os
    if hasattr(os, "fork"):
        ctx_fork = mp.get_context("fork")
        p2 = ctx_fork.Process(target=worker, args=("来自 fork 上下文",))
        p2.start()
        p2.join()
```

---

## 5. spawn 的代价与 pickle 要求

`spawn` 需要把目标函数、参数、返回值都通过 **pickle**（Python 对象序列化）在进程间传递。

**关键结论：**

- 传给子进程的函数必须是模块顶层可导入的函数。
- 局部函数、lambda、不可 pickle 的对象会失败。
- 大量数据用 `spawn` 传递会较慢，应尽量用 `Queue`、`Pipe`、共享内存（shared memory）等机制。

```python
# spawn 下，函数必须定义在模块顶层，不能是闭包里的局部函数
import multiprocessing as mp

def top_level_func(x):
    return x * x

if __name__ == "__main__":
    ctx = mp.get_context("spawn")
    with ctx.Pool(2) as pool:
        # top_level_func 可被 pickle，所以 spawn 能正常调用
        results = pool.map(top_level_func, [1, 2, 3])
    print("结果:", results)
```

---

## 6. 总结对照表

| 维度 | fork | spawn |
|------|------|-------|
| 内存继承 | 继承父进程内存 | 全新解释器，不继承 |
| 启动速度 | 快 | 慢 |
| 跨平台 | 仅 Unix | Windows/macOS/Linux |
| 多线程安全 | 差，易死锁 | 好 |
| 必须 `__main__` 保护 | 不强制 | 强制 |
| 数据传递 | 可直接共享部分状态 | 必须 pickle |

---

## 动手练习

**任务：写一个跨平台的多进程“平方计算器”，分别用 `spawn` 和（在支持的平台上）`fork` 运行，观察差异。**

要求：

1. 定义一个模块顶层函数 `square(n)`，返回 `n * n`。
2. 用 `mp.get_context("spawn")` 创建 `Pool`，对 `[1, 2, 3, 4, 5]` 做 map，打印结果。
3. 判断当前系统是否支持 `fork`（`hasattr(os, "fork")`）。如果支持，再用 `mp.get_context("fork")` 做同样的事，打印结果。
4. 记录两次运行的时间（用 `time.perf_counter()`），比较启动速度差异。
5. 把代码保存为 `mp_compare.py`，在本地终端运行 `python mp_compare.py`，观察输出。

提示：Windows 上第 3 步会跳过，这是正常的。


---

## 本课题目

### single_choice · None



- [A] pickle 只能序列化内置的基础数据类型，无法处理自定义类的实例
- [B] pickle 可以把对象转换为字节流，并在之后反序列化还原该对象
- [C] pickle 序列化后的结果一定是人类可读的 JSON 文本
- [D] pickle 反序列化时不会执行任何代码，因此可以安全地加载任意不可信数据

**参考答案**：1

**解析**：pickle 的核心功能就是把 Python 对象转成字节流（序列化），并能在之后还原为原对象（反序列化）。它可以处理大多数自定义类实例（只要可被 pickle 协议支持），输出的是二进制字节而非可读文本；同时反序列化过程可能执行代码，因此不能用来加载不可信数据。

### single_choice · None



- [A] dumps / loads，它们直接读写文件对象
- [B] dump / load，它们面向文件对象；dumps / loads 面向字节串
- [C] encode / decode，它们负责字节与字符串互转
- [D] open / close，它们负责序列化协议协商

**参考答案**：1

**解析**：pickle.dump(obj, file) 把对象写入文件对象，pickle.load(file) 从文件对象读出对象；而 pickle.dumps(obj) 返回 bytes，pickle.loads(data) 从 bytes 还原对象。encode/decode 是字符串编解码，与 pickle 无关。

### multi_choice · None



- [A] 反序列化不可信来源的 pickle 数据可能导致任意代码执行
- [B] pickle 适合用于进程间传递可信的、由本程序自身生成的数据
- [C] pickle 适合作为对外开放接口的数据交换格式
- [D] pickle 可以通过设置某个参数变成绝对安全的沙箱格式

**参考答案**：[0, 1]

**解析**：pickle 反序列化不可信数据存在代码执行风险，因此适合在可信边界内传递本程序生成的数据，不适合作为对外开放的交换格式；pickle 没有可靠的“安全沙箱参数”。

### multi_choice · None



- [A] 由嵌套 dict、list、tuple 组成的数据结构
- [B] 在模块顶层定义的普通类实例
- [C] 打开的网络 socket 对象
- [D] 整数、浮点数、字符串和布尔值

**参考答案**：[0, 1, 3]

**解析**：容器与基础类型、模块顶层定义的普通类实例一般都可序列化；而 socket 属于操作系统级资源，不能被默认序列化。

### multi_choice · None



- [A] 在调用序列化时显式指定一个较低的协议版本
- [B] 避免使用仅在较新 Python 中才支持的序列化相关新特性
- [C] 始终使用默认的最高协议版本
- [D] 把对象先转成 JSON 字符串再 pickle

**参考答案**：[0, 1]

**解析**：显式指定较低协议版本、并避免依赖新版本独有的特性，有助于兼容旧解释器。使用最高协议版本恰好相反；把对象转 JSON 后再 pickle 仍会以当前协议序列化那个字符串，并不能保证协议层兼容。

### multi_choice · None



- [A] protocol 决定序列化时使用的数据格式版本
- [B] 不同的 protocol 可能产生不同的字节结果
- [C] protocol 取值只能是 0 或 1
- [D] 不指定 protocol 时通常使用当前解释器的默认协议

**参考答案**：[0, 1, 3]

**解析**：protocol 控制格式版本，不同版本输出的字节可能不同，缺省时使用默认协议。protocol 的取值覆盖多个版本（如 0、1、2、…、最高版本），并不限于 0 或 1。

### fill_blank · None



**参考答案**：["dump"]

**解析**：pickle.dump(obj, f) 会把 obj 序列化并直接写入文件对象 f；而 dumps 返回 bytes，不负责写文件。

### fill_blank · None



**参考答案**：["loads", "load"]

**解析**：pickle.loads(data) 从 bytes 还原对象；若数据来自文件对象则用 pickle.load。对 bytes 而言 loads 是标准答案，load 在部分语境下也被接受。

### fill_blank · None



**参考答案**：["bytes"]

**解析**：dumps 返回二进制字节串，即 bytes 类型。

### code_reading · None



**参考答案**：打印 True。因为 pickle 能把包含字典、列表、元组等可序列化容器的对象完整地序列化为字节串，再通过 loads 还原为等值的对象，还原后的结构与原对象相等。

**解析**：pickle 支持嵌套的常见容器类型，序列化再反序列化后得到与原来相等的对象，因此相等比较为 True。

### code_reading · None



**参考答案**：打印 Point 1 2。因为模块顶层定义的普通类实例默认可被 pickle 序列化，反序列化后会重新创建该类的实例并恢复其实例属性，因此类型名和属性值都与原对象相同。

**解析**：pickle 会记录对象的类信息与实例状态，还原时重建同类实例并恢复属性，所以输出类型名 Point 及属性值 1 和 2。

### scenario · None



**解析**：pickle 反序列化不可信数据可能导致任意代码执行。既然缓存文件可能来自外部，就不应再用 pickle 加载，而应改用 JSON 等更安全的格式，或对来源做严格校验与隔离。

### single_choice · None



- [A] 包含嵌套列表和字典的元组
- [B] 模块中定义的普通类实例
- [C] 打开的文件对象（file object）
- [D] 由整数和字符串组成的集合

**参考答案**：2

**解析**：打开的文件对象持有一个操作系统级别的句柄，无法被序列化，pickle 会抛出异常。嵌套容器、普通类实例、基础类型的集合通常都可以被序列化。

### scenario · None



**解析**：在数据来源可信、两端都由本团队控制的前提下，pickle 可以用来传递自定义对象，但需注意协议版本对应的解释器兼容性，并始终牢记不可用于不可信来源。

### single_choice · None



- [A] 只要数据是用 pickle 序列化的，就一定安全
- [B] 反序列化恶意构造的数据可能执行任意代码，因此不可信数据不应使用 pickle 加载
- [C] pickle 有内置的沙箱机制，会自动阻止危险操作
- [D] 只要使用最高协议版本就不再有任何安全风险

**参考答案**：1

**解析**：pickle 的反序列化过程会通过特定机制还原对象，攻击者可构造数据触发危险行为，从而执行任意代码。pickle 没有可靠沙箱，也不因协议版本提高而变安全。因此来自不可信来源的数据应改用更安全的数据格式。

### single_choice · None



- [A] 总是使用最高的协议版本
- [B] 指定一个较低的协议版本，以兼容旧解释器
- [C] 改用 JSON 格式即可自动兼容
- [D] 把协议版本设为 0 以下的值

**参考答案**：1

**解析**：pickle 的协议版本从 0 逐步演进，高版本协议可能无法被旧版本 Python 读取。若要兼容旧解释器，应显式指定较低的协议版本；协议版本不能为负。JSON 与 pickle 是不同格式，不能解决 pickle 协议兼容问题。

### single_choice · None



- [A] str
- [B] bytes
- [C] bytearray
- [D] memoryview

**参考答案**：1

**解析**：dumps 返回的是 bytes 对象，即二进制字节串。它不是文本 str，通常也不直接返回 bytearray 或 memoryview。

### single_choice · None



- [A] pickle 是一种通用标准格式，可以被 Java、Go 等语言直接解析
- [B] pickle 是 Python 专用的，其他语言一般不直接支持，且不同 Python 版本间也存在协议兼容问题
- [C] pickle 只能在生成它的同一台机器上还原，无法跨机器使用
- [D] pickle 序列化结果与 Python 版本完全无关，可在任意版本间自由交换

**参考答案**：1

**解析**：pickle 是 Python 专有的序列化格式，其他语言没有内建支持；跨 Python 版本时也受协议版本影响。它可以跨机器传输，并不绑定特定机器。

### single_choice · None



- [A] 一个只包含整数列表的类实例
- [B] 一个持有数据库连接或线程锁等无法直接序列化资源的类实例
- [C] 一个继承自 dict 的类实例
- [D] 一个只包含字符串属性的简单数据类实例

**参考答案**：1

**解析**：数据库连接、线程锁等资源无法被默认序列化，需要在自定义方法中决定如何表示和重建这些状态。纯数据的实例通常无需自定义即可序列化。

### single_choice · None



- [A] 只要对象未变，结果一定是完全相同的字节序列
- [B] 结果可能因协议版本、对象内部状态等不同而不同，不保证每次字节完全一致
- [C] dumps 只能对同一对象调用一次
- [D] dumps 会修改原对象，使它之后无法再被序列化

**参考答案**：1

**解析**：pickle 的输出取决于协议版本和对象实际状态等因素，不保证字节级完全一致；但 dumps 不会修改原对象，且可多次调用。

### single_choice · None



- [A] pickle 会陷入无限递归并崩溃
- [B] pickle 能正确处理循环引用，还原后仍保持循环结构
- [C] pickle 会自动把循环引用替换为 None
- [D] 只有使用协议版本 0 才能处理循环引用

**参考答案**：1

**解析**：pickle 通过对象引用跟踪机制可以正确处理循环引用，并在反序列化时还原出相同的循环结构。它不会因循环引用而无限递归崩溃。

### single_choice · None



- [A] 子进程会重新导入主模块，因此必须放在 if __name__ == '__main__' 保护块中
- [B] 子进程会继承父进程当前的内存状态，包括已创建的全局对象
- [C] 父进程中已启动的线程不会被子进程继承
- [D] 子进程与父进程共享同一份 Python 对象，修改会互相影响

**参考答案**：1

**解析**：fork 通过复制父进程的地址空间来创建子进程，子进程获得父进程当前内存状态的拷贝，因此会继承已创建的全局对象。选项 A 描述的是 spawn 的特点；选项 C 说反了，fork 会复制调用线程，但其他线程不会被复制；选项 D 错误，是拷贝而非共享。

### single_choice · None



- [A] 正常运行并输出 hi
- [B] 抛出异常，提示需要 if __name__ == '__main__' 保护
- [C] 子进程静默失败，没有任何提示
- [D] 父进程会先输出 hi，然后子进程再输出一次

**参考答案**：1

**解析**：Windows 上 multiprocessing 只能使用 spawn 启动方式，spawn 会重新导入主模块，若不放在 if __name__ == '__main__' 保护块中，会在导入时再次创建进程，导致 RuntimeError。

### multi_choice · None



- [A] 把进程/池的创建代码放在 if __name__ == '__main__' 保护块中
- [B] 目标函数定义在模块顶层，且不依赖运行时全局状态
- [C] 通过参数传递数据，而不是依赖子进程自动继承全局变量
- [D] 使用 lambda 作为进程 target 以简化代码

**参考答案**：[0, 1, 2]

**解析**：跨平台（包含 spawn）要求目标可导入、参数可 pickle、不依赖继承的全局状态。lambda 无法被 pickle，因此 D 错误。

### multi_choice · None



- [A] fork 子进程可能继承父进程尚未刷新的缓冲输出，导致重复打印
- [B] spawn 子进程不会继承父进程的线程锁状态
- [C] fork 子进程会复制父进程已设置的随机数种子等状态
- [D] spawn 子进程会与父进程共享同一份模块级可变对象

**参考答案**：[0, 1, 2]

**解析**：fork 复制内存状态，可能继承输出缓冲、随机种子、锁状态等；spawn 不继承这些状态，而是重新导入模块，因此 D 错误。

### fill_blank · None



**参考答案**：["set_start_method"]

**解析**：multiprocessing.set_start_method() 用于设置全局启动方式，必须在任何进程创建前调用且只能调用一次。

### fill_blank · None



**参考答案**：["导入", "重新导入", "import"]

**解析**：spawn 会重新导入主模块，若创建进程的代码不在保护块中，会在导入阶段再次执行并导致递归创建进程。

### fill_blank · None



**参考答案**：["序列化", "pickle", "pickled", "序列化(pickle)"]

**解析**：spawn 通过 pickle 序列化目标函数与参数传给子进程，因此它们必须可 pickle（可序列化）。

### code_reading · None



**参考答案**：在 Linux 默认使用 fork 时可以正常运行，输出 'child' 和 'main'（顺序可能因刷新而略有差异）。但在使用 spawn 的平台（或显式设置为 spawn）上，由于没有 if __name__ == '__main__' 保护块，重新导入模块时会再次执行 p.start()，导致子进程递归创建进程并抛出 RuntimeError。

**解析**：fork 通过复制父进程执行，不需要重新导入主模块，因此可以工作；spawn 需要重新导入主模块，未加保护会导致重复创建。

### code_reading · None



**参考答案**：在 fork 下子进程会输出 100，因为 fork 复制父进程在创建进程那一刻的内存状态，此时 value 已被赋值为 100。如果使用 spawn，由于子进程重新导入模块，模块级 value 初始化为 42，且运行时对全局变量的修改不会传递，因此会输出 42。

**解析**：fork 复制的是 fork 时刻的内存快照，spawn 则重新导入模块，二者对运行时全局变量修改的可见性不同。

### scenario · None



**解析**：macOS 默认 spawn，会重新导入主模块并 pickle 目标函数与参数。库应确保进程创建代码不依赖调用方处于主模块顶层执行，目标函数定义在模块顶层、参数可 pickle，并建议调用方在保护块中触发；也可用 get_context('spawn') 明确上下文。

### scenario · None



**解析**：Linux 默认 fork，会复制父进程的文件描述符、套接字与锁状态。父进程持有的数据库连接和线程锁在子进程中可能处于不一致状态，导致挂起或损坏。建议改用 spawn 或 forkserver 上下文，或只在子进程中建立各自连接，避免继承不安全的资源。

### scenario · None



**解析**：跨平台必须兼容 spawn，因此目标函数要定义在模块顶层、数据通过参数传递且可 pickle，避免依赖父进程全局变量。在 Linux 上可考虑 fork 以利用内存快照提升性能，但为统一行为可用 get_context 显式选择，并确保不依赖继承的可变状态。

### single_choice · None



- [A] spawn 会完整拷贝父进程内存，因此比 fork 更快
- [B] fork 会重新启动解释器，spawn 不会
- [C] spawn 会启动新的解释器进程，只传递必要的参数和模块，启动开销通常比 fork 大
- [D] 两者在内存使用和启动速度上没有区别，只是平台默认值不同

**参考答案**：2

**解析**：spawn 会启动一个全新的 Python 解释器进程，只序列化传递目标函数、参数和必要模块，启动慢但更干净；fork 复制父进程内存，启动快但可能继承不期望的状态。

### scenario · None



**解析**：forkserver 先启动一个干净的单线程服务器进程，后续子进程由该服务器 fork 出来，结合了 fork 的速度与 spawn 的安全性，常用于避免多线程父进程中 fork 带来的死锁，但并非等同于普通 fork。

### single_choice · None



- [A] 主进程为只读数据的纯计算程序
- [B] 父进程中已经持有了数据库连接、锁或打开了大量文件描述符
- [C] 子进程只做简单的字符串拼接
- [D] 父进程刚启动，尚未创建任何全局对象

**参考答案**：1

**解析**：fork 会复制父进程的文件描述符和锁状态，子进程继承数据库连接、线程锁等可能在子进程中处于不一致状态，导致死锁或数据损坏，因此这类场景风险最大。

### single_choice · None



- [A] spawn 比 fork 更快
- [B] fork 在 macOS 上与系统底层（如 CoreFoundation）不兼容，容易导致崩溃
- [C] spawn 支持更多的参数类型
- [D] fork 无法在 macOS 上使用

**参考答案**：1

**解析**：macOS 的系统框架对 fork 后的子进程使用诸多 API 不安全，容易引发崩溃，因此官方将默认启动方式改为 spawn，以避免相关兼容性问题。

### single_choice · None



- [A] fork 仅在类 Unix 系统（包括 Linux）上可用
- [B] spawn 在所有支持 multiprocessing 的平台上都可用
- [C] forkserver 是 fork 的一种改进，先启动一个服务器进程再从中 fork
- [D] spawn 创建的进程会继承父进程的所有全局变量

**参考答案**：3

**解析**：spawn 会启动全新解释器并重新导入模块，父进程的全局变量不会自动传递到子进程（除非通过参数或模块级初始化）。其余选项描述正确。

### single_choice · None



- [A] 在创建进程之前调用 multiprocessing.set_start_method('spawn')，且只调用一次
- [B] 在每个子进程函数内部调用 multiprocessing.set_start_method('spawn')
- [C] 在 multiprocessing.Process 构造时传入 start_method='spawn' 参数
- [D] 设置环境变量 PYTHON_START_METHOD=spawn

**参考答案**：0

**解析**：set_start_method 用于设置全局的启动方式，且必须在任何进程创建之前调用、只能调用一次。Process 构造没有 start_method 参数。

### single_choice · None



- [A] get_context() 只能用于获取与当前全局启动方式相同的上下文
- [B] get_context('spawn') 返回一个使用指定启动方式的上下文对象，可用它创建不依赖全局设置的进程/pool
- [C] get_context('spawn') 会永久修改全局启动方式
- [D] get_context() 必须传入启动方式参数，否则报错

**参考答案**：1

**解析**：get_context 返回一个上下文对象，其创建的 Process/Pool 等使用指定启动方式，适合在库代码中避免依赖全局设置。它不会修改全局启动方式。

### multi_choice · None



- [A] 目标函数定义在模块顶层之外，比如嵌套在另一个函数内部
- [B] 进程创建代码没有放在 if __name__ == '__main__' 保护块中
- [C] 通过参数传递了不可 pickle 的对象（如 lambda 或打开的文件句柄）
- [D] 子进程内访问了父进程在运行时才创建的全局变量

**参考答案**：[0, 1, 2, 3]

**解析**：spawn 需要重新导入主模块并 pickle 目标函数与参数，因此目标函数必须可导入、参数必须可 pickle、创建进程的代码不能在被导入时再次执行、父进程运行时创建的全局状态不会自动传递。

### multi_choice · None



- [A] 启动速度通常比 spawn 快
- [B] 子进程可以访问父进程在 fork 时已存在的内存对象
- [C] 在所有平台上都能使用
- [D] 不需要 pickle 目标函数和参数

**参考答案**：[0, 1, 3]

**解析**：fork 复制父进程内存，启动快、无需 pickle、可看到已有内存对象；但它并非所有平台可用（如 Windows 不支持），因此 C 错误。
