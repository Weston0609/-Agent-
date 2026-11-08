# s4u1l1 Python 并发对象模型（py.cpy.object_model）教学讲义 / Python 引用计数（Reference Counting） / Python 引用计数与垃圾回收

> 来源 `content/lessons/s4u1l1.json`

## py.cpy.object_model

# Python 并发对象模型（py.cpy.object_model）教学讲义

> **一句话直觉**：Python 的并发能力受限于它的对象模型——`GIL`、引用计数、可变/不可变对象、对象在进程/线程/协程之间的可见性，决定了你写的每一段 `thread`、`multiprocessing`、`asyncio` 代码到底是快、是慢、还是不安全。

在学完线程、进程、协程之后，你可能会有一个困惑：为什么有些代码在多线程下能提速，有些反而更慢？为什么改一个 `int` 不生效，改一个 `list` 就生效？这些现象的背后，全部是 CPython（Python 官方解释器）的**对象模型**在起作用。本节课我们用 4 个小节把这件事讲透。

---

## 第 1 节：一切皆对象，一切皆引用

在 Python 里，**变量不是盒子**，变量只是**指向对象的引用（reference）**。

- 每个对象有 3 个核心属性：**id（身份）**、**type（类型）**、**value（值）**。
- `is` 比较的是 `id`，`==` 比较的是 `value`。
- 赋值 `b = a` 只是让 `b` 和 `a` 指向同一个对象，**不会复制**。

这是理解后面所有并发问题的地基。

```python
# demo1_reference.py
import sys

a = [1, 2, 3]
b = a               # b 与 a 指向同一个 list 对象
b.append(4)
print(a)            # [1, 2, 3, 4] —— a 也被改了！

print(id(a) == id(b))   # True，同一个对象
print(sys.getrefcount(a))  # 引用计数，通常比看到的 +1（getrefcount 自身会加一次）

# 不可变对象示例
x = 10
y = x
y += 1              # 这里其实创建了一个新 int 对象，x 不变
print(x, y)         # 10 11
```

**关键结论**：可变对象（mutable，如 `list`/`dict`/`set`）在多个并发单元间共享时，天然存在被同时修改的风险；不可变对象（immutable，如 `int`/`str`/`tuple`）一旦创建就不变，天然线程安全。

---

## 第 2 节：引用计数与 GIL —— 为什么多线程不能跑满多核

CPython 用**引用计数（reference counting）** 管理内存：每个对象有一个计数器，赋值/传参会让计数 +1，离开作用域/重新赋值让计数 -1，计数归零就立刻回收。

为了让引用计数在多线程下不崩，CPython 引入了 **全局解释器锁（GIL，Global Interpreter Lock）**：**任意时刻，只有一个线程能执行 Python 字节码**。

所以：

- **IO 密集型（I/O bound）** 任务：线程在 `time.sleep`、`socket.recv` 等时会释放 GIL，多线程**有效**。
- **CPU 密集型（CPU bound）** 任务：线程一直抢着 GIL，多线程**几乎没有提速**，甚至更慢；要用 `multiprocessing` 绕开 GIL。

```python
# demo2_gil.py
import time, threading, multiprocessing

def cpu_work(n=10**7):
    s = 0
    for i in range(n):
        s += i * i
    return s

# 单线程
t0 = time.perf_counter()
cpu_work(); cpu_work()
print("single :", round(time.perf_counter()-t0, 3), "s")

# 多线程（受 GIL 限制，几乎不会变快）
t0 = time.perf_counter()
ts = [threading.Thread(target=cpu_work) for _ in range(2)]
[t.start() for t in ts]; [t.join() for t in ts]
print("thread :", round(time.perf_counter()-t0, 3), "s")

# 多进程（各自有独立解释器和 GIL，真正并行）
t0 = time.perf_counter()
ps = [multiprocessing.Process(target=cpu_work) for _ in range(2)]
[p.start() for p in ps]; [p.join() for p in ps]
print("process:", round(time.perf_counter()-t0, 3), "s")
```

**关键结论**：

| 场景 | 推荐 |
| --- | --- |
| I/O 密集 | `threading` / `asyncio` |
| CPU 密集 | `multiprocessing` / 原生扩展 / Cython |
| 高并发网络 | `asyncio` + `aiohttp`/`httpx` |

---

## 第 3 节：对象在进程、线程、协程间的“可见性”

同一个对象在不同并发模型里的命运完全不同：

- **线程之间**：共享同一个解释器内存，变量**天然共享**。但要注意**竞态条件（race condition）**，需要 `Lock` / `RLock` / `Queue`。
- **进程之间**：各自有独立内存。传递对象必须**序列化（pickling）**，且是最常见的坑之一；跨进程共享内存要用 `multiprocessing.shared_memory` 或 `Value`/`Array`。
- **协程之间**：同一个线程内协作式调度，共享内存但**不能在 await 中让出时被外部同时改**；用 `asyncio.Lock` 等异步同步原语保护，且注意不要在其中执行阻塞调用（用 `run_in_executor`）。

```python
# demo3_visibility.py
import threading

counter = 0
def add():
    global counter
    for _ in range(100_000):
        counter += 1  # 这不是原子操作：读-改-写三步！

ts = [threading.Thread(target=add) for _ in range(4)]
[t.start() for t in ts]; [t.join() for t in ts]
print("no lock :", counter)  # 往往小于 400000

lock = threading.Lock()
counter = 0
def add_safe():
    global counter
    for _ in range(100_000):
        with lock:            # 加锁保证读-改-写是原子的
            counter += 1

ts = [threading.Thread(target=add_safe) for _ in range(4)]
[t.start() for t in ts]; [t.join() for t in ts]
print("with lock:", counter)  # 恰好 400000
```

**关键结论**：Python 的 `+=` 在字节码层面是 `LOAD / BINARY_OP / STORE` 三步，非原子。任何跨并发单元修改共享可变对象，都要问自己：“**我加锁了吗？**”

---

## 第 4 节：可运行示例 —— 用合适的并发对象模型解决合适的问题

下面这段代码把上面所有知识点串起来：**IO 密集用线程，CPU 密集用进程，且各自注意可见性**。

（见 `example_code` 字段。）

运行后你会看到：线程 `sleep` 的 IO 任务几乎同时完成，而进程的 CPU 任务才真正并行起来。

---

## 动手练习

**任务：写一个“混合并发”脚本**

1. 定义两个函数：
   - `io_task(name)`：`time.sleep(0.5)` 后打印 `f"{name} done"`，共 5 个任务。
   - `cpu_task(n=2*10**6)`：做整数平方和，返回结果，共 2 个任务。
2. 用 `concurrent.futures.ThreadPoolExecutor` 并发跑 5 个 `io_task`，记录耗时。
3. 用 `concurrent.futures.ProcessPoolExecutor` 并发跑 2 个 `cpu_task`，记录耗时。
4. 再做一次对照：把步骤 3 换成 `ThreadPoolExecutor`，比较耗时差异。
5. 写一段简短总结（3~5 行），解释为什么步骤 3 和步骤 4 结果不同。

**提示**：
- 用 `time.perf_counter()` 计时。
- 注意 `if __name__ == "__main__":` 保护（`spawn` 模式必须）。
- 如果觉得结果不明显，把 `cpu_task` 的 `n` 调到 `10**7`。

## py.cpy.refcount

# Python 引用计数（Reference Counting）

## 一句话直觉

**Python 里每个对象都有一个「被多少人牵着」的计数器；计数器归零，对象立即被回收。** 理解引用计数（reference counting），你就理解了 Python 内存管理的底层逻辑，也就能解释「为什么我的对象提前被释放了」「为什么循环引用会造成内存泄漏」这类工程级问题。

---

## 1. 什么是引用计数？

在 CPython（Python 的官方实现）中，每一个 Python 对象（object）在内存里都有一个隐藏字段 `ob_refcnt`，称为**引用计数（reference count）**。它记录「当前有多少个地方正在引用这个对象」。

- 每多一个引用 → 计数 +1
- 每少一个引用 → 计数 −1
- 计数归零 → 该对象立即被销毁，占用内存被归还

我们可以用 Python 内置的 `sys.getrefcount()` 观察这个值：

```python
import sys

a = []                 # 创建一个 list 对象，被 a 引用
print(sys.getrefcount(a))  # 通常输出 2：a 本身 + getrefcount 的参数

b = a                  # b 也指向同一个对象
print(sys.getrefcount(a))  # 输出 3

del b                  # 删除 b 这个引用
print(sys.getrefcount(a))  # 回到 2
```

> 小提示：`getrefcount()` 的参数本身会临时给对象加 1，所以看到的数字总是「真实引用数 +1」。

---

## 2. 什么操作会改变引用计数？

CPython 在字节码层面通过 `Py_INCREF` / `Py_DECREF` 两个宏来增减计数。日常写代码时，下面这些操作都会影响计数：

| 操作 | 效果 |
|---|---|
| 赋值 `b = a` | +1 |
| 放进容器 `lst.append(a)` | +1 |
| 作为函数参数传入（绑定到形参） | +1 |
| `del b` | −1 |
| 变量被重新赋值 | 旧对象 −1，新对象 +1 |
| 变量离开作用域（函数返回） | −1 |
| 容器被销毁 | 容器内所有元素 −1 |

```python
import sys

obj = {"k": "v"}
print("初始:", sys.getrefcount(obj))

container = [obj, obj]          # 同一对象被引用两次
print("放入容器后:", sys.getrefcount(obj))

def f(x):
    print("函数内部:", sys.getrefcount(x))

f(obj)                          # 传参也会临时 +1

del container
print("容器销毁后:", sys.getrefcount(obj))
```

这套机制的关键含义是：**Python 对象不需要程序员手动 free。作用域结束、变量被覆盖、容器被销毁，都会自动触发引用计数下降。**

---

## 3. 引用计数如何触发对象销毁？

当一个对象的引用计数降到 0 时，CPython 会立刻调用它的析构方法 `__del__`（如果定义了），然后释放内存。

```python
class Probe:
    def __init__(self, name):
        self.name = name
        print(f"[{self.name}] 创建")
    def __del__(self):
        print(f"[{self.name}] 销毁")

p = Probe("A")        # 输出：[A] 创建
del p                  # 输出：[A] 销毁
print("程序结束前")
```

运行结果里你会看到 `[A] 销毁` 出现在 `del p` 之后、`程序结束前` 之前 —— 这就是**引用计数归零立即回收**的特征，也是它和垃圾回收（GC, Garbage Collection）里「标记-清除（mark-sweep）」最大的区别：即时性。

---

## 4. 引用计数解决不了什么？——循环引用

引用计数有一个众所周知的短板：**循环引用（reference cycle）** 会让计数永远无法归零。

```python
class Node:
    def __init__(self):
        self.peer = None
    def __del__(self):
        print("Node 被销毁")

a = Node()
b = Node()
a.peer = b        # a 引用 b
b.peer = a        # b 引用 a —— 形成环
del a
del b

import gc
print("手动触发 gc 前")
gc.collect()
print("手动触发 gc 后")
```

即便 `del a` 和 `del b` 都执行了，两个 Node 的引用计数都还剩 1（彼此互相引用），所以「立即回收」失效。此时需要 CPython 的**分代垃圾回收器（generational GC）** 定期扫描，找出不可达的循环并清除。所以引用计数只是 Python 内存管理的一半，另一半是 GC。

---

## 5. 工程上为什么要关心引用计数？

在真实项目中，这些场景都跟引用计数直接相关：

1. **对象的生命周期时机**：`__del__`、上下文管理器（context manager）的清理逻辑，什么时候被唤起，与引用计数密不可分。
2. **资源释放延迟**：如果一个文件对象、socket 被其他结构偷偷持有了引用，它就不会及时关闭。
3. **循环引用泄漏**：缓存容器、双向链表、父子节点对象，都可能制造长久不被回收的环。
4. **CPython 的实现细节**：其它 Python 实现（如 PyPy、Jython）用的是完全不同的内存模型，因此官方文档警告「不要依赖 CPython 的引用计数行为写代码」。

一个简单判断「对象是否仍被引用」的辅助函数：

```python
import sys

def alive_count(obj):
    # 返回减掉 getrefcount 自身参数后的引用数
    return sys.getrefcount(obj) - 1

x = object()
print(alive_count(x))       # 1
holder = {"x": x}
print(alive_count(x))       # 2
holder.clear()
print(alive_count(x))       # 1
```

---

## 动手练习（建议 15~20 分钟）

**目标**：亲手观察引用计数在「传参 / 容器 / 循环引用」三种场景下的变化。

1. 定义类 `Tracker`，在 `__init__` 里 `print("创建", id(self))`，在 `__del__` 里 `print("销毁", id(self))`。
2. 用 `sys.getrefcount` 写一个辅助函数 `count(obj)`，返回真实引用数。
3. 依次完成下列实验并记录每次 `count` 的输出以及 `创建/销毁` 打印的时机：
   - 创建对象绑定到变量 `t`
   - 把 `t` 放进一个 list
   - 把 `t` 作为参数传给一个普通函数
   - `del t`
   - `list.clear()`
4. 再创建两个 `Tracker` 对象，让它们互相通过属性引用形成环。执行 `del` 后检查 `__del__` **是否被触发**；然后调用 `gc.collect()`，再观察。

**提交要求**：提交你的脚本和运行输出，并用三句话解释：
- 为什么 `__del__` 有时立即打印，有时要等 `gc.collect()`？
- 引用计数在什么情况下失效？
- 在写工程代码时，你会怎样避免意外的循环引用？

```python
import sys
import gc


def count(obj):
    """返回去掉 getrefcount 自身参数后的真实引用数。"""
    return sys.getrefcount(obj) - 1


class Tracker:
    def __init__(self, name):
        self.name = name
        self.peer = None
        print(f"创建 {self.name} id={id(self)}")

    def __del__(self):
        print(f"销毁 {self.name} id={id(self)}")


# 1) 基本引用计数变化
t = Tracker("A")
print("绑定变量后 count =", count(t))

lst = [t]
print("放入 list 后 count =", count(t))


def take(x):
    print("函数内部 count =", count(x))


take(t)
print("函数返回后 count =", count(t))

del t
print("del t 后（对象仍在 list 中）count 无法直接测，因变量已删）")

lst.clear()   # 这里会触发 __del__
print("---- list.clear() 之后应看到 '销毁 A' 打印 ----")

# 2) 循环引用场景
print("\n=== 循环引用实验 ===")
a = Tracker("X")
b = Tracker("Y")
a.peer = b
b.peer = a
del a
del b
print("del 之后，X / Y 尚未被 __del__（因为有环）")

collected = gc.collect()
print(f"gc.collect() 回收对象数 = {collected}")
```

## py.cpy.gc

# py.cpy.gc：Python 引用计数与垃圾回收

> **一句话直觉**：Python 帮你自动管理内存，但你必须知道「什么时候对象会被回收、什么时候不会」——否则会写出悄悄泄漏内存的代码。

本知识点讲解 Python 的 **引用计数（Reference Counting）** 与 **垃圾回收（Garbage Collection，简称 GC）** 机制。这是 Python 内存管理的核心，也是从零基础走向工程级必须跨过的一道坎。

---

## 1. 为什么需要它：内存不是无限的

程序运行的每一个对象（数字、字符串、列表、类的实例）都占用内存。手动管理内存（像 C 语言那样 `malloc` / `free`）容易出错：忘释放 → 内存泄漏；释放两次 → 崩溃。Python 采用**自动内存管理（Automatic Memory Management）**，你只管创建对象，回收由解释器负责。

理解这套机制能帮你回答三类工程问题：
- 为什么我的程序内存一直涨？（循环引用、全局缓存）
- 为什么对象没有立刻被销毁？（还有引用存在）
- 为什么大数据集迟迟不释放？（容器仍持有引用）

---

## 2. 引用计数：对象生命的「计数器」

Python 中每个对象都有一个 **引用计数（reference count）**，记录有多少个地方指向它。

- 赋值、传参、放入容器 → 计数 +1
- 变量被重新赋值、离开作用域、从容器中删除 → 计数 -1
- 计数降为 **0** → 对象立即被释放

可以用 `sys.getrefcount()` 观察（注意：调用这个函数本身会临时 +1）。

```python
import sys

x = []                    # 创建空列表，引用计数至少为 1
print(sys.getrefcount(x)) # 通常是 2（x + getrefcount 的临时参数）

y = x                     # 又多一个引用
print(sys.getrefcount(x)) # 变成 3

del y                     # 少一个引用
print(sys.getrefcount(x)) # 回到 2
```

**关键结论**：引用计数是「即时」的，一旦计数归零，CPython 会立刻回收内存，不等 GC。

---

## 3. 引用计数的死穴：循环引用

如果两个对象互相引用，即使外部已经没有任何变量指向它们，它们的计数也不会归零——因为它们互相「支撑」着对方。

```python
a = {}
b = {}
a['b'] = b   # a 引用 b
b['a'] = a   # b 引用 a

del a
del b
# 此时两个字典已经没有外部引用，但它们互相引用
# 引用计数都不为 0，光靠引用计数无法回收！
```

这就是为什么 Python 还需要第二个机制：**垃圾回收器（Garbage Collector）**。

---

## 4. 分代垃圾回收：专治循环引用

Python 的 `gc` 模块实现了一个 **分代回收器（Generational GC）**，专门检测并回收「循环引用但不可达」的对象。

核心思想：
- 对象被分到 3 代：第 0 代（新对象）、第 1 代、第 2 代（存活久的老对象）。
- 新对象频繁被检查，老对象检查频率低——因为「活得越久，越可能继续活」。
- 触发条件由阈值控制，可以用 `gc.get_threshold()` 查看。

```python
import gc

print(gc.get_threshold())     # 默认 (700, 10, 10)
print(gc.isenabled())         # True，GC 默认开启

# 手动触发一次完整回收（调试时常用）
collected = gc.collect()
print('回收对象数:', collected)
```

**工程要点**：
- 大多数时候你不需要手动调用 `gc.collect()`。
- 处理大对象图（如大型图结构、缓存）后，手动回收一次可以立刻释放内存。
- 极端性能场景下可 `gc.disable()`，但要非常谨慎，容易内存泄漏。

---

## 5. 弱引用：不增加计数的「安全指针」

有时你想「观察」一个对象，但不想阻止它被回收。这时用 **弱引用（weak reference）**。

```python
import weakref

class Node:
    pass

n = Node()
r = weakref.ref(n)       # 弱引用，不增加 n 的引用计数
print(r() is n)          # True，对象还活着

del n                    # 强引用消失
print(r())               # None，对象已被回收
```

弱引用常用于缓存、观察者模式、父子对象关系，避免「缓存把对象永远钉住」这类内存泄漏。

---

## 小结

| 机制 | 作用 | 触发时机 |
|------|------|----------|
| 引用计数 | 回收无引用对象 | 计数归零立即回收 |
| 分代 GC | 回收循环引用对象 | 达到阈值或手动调用 |
| 弱引用 | 不阻止回收的引用 | 对象被回收后返回 None |

掌握这三者，你就能写出「内存行为可预测」的 Python 代码。

```python
import sys
import gc
import weakref

# 1) 引用计数演示
x = []
base = sys.getrefcount(x)
y = x
assert sys.getrefcount(x) == base + 1
del y

# 2) 循环引用 + GC 回收演示
class Node:
    def __init__(self, name):
        self.name = name
        self.partner = None

a = Node('A')
b = Node('B')
a.partner = b
b.partner = a

ref = weakref.ref(a)      # 用弱引用观察 a 是否被回收
print('before del, alive:', ref() is not None)

del a
del b
# 此时两个对象循环引用，引用计数不为 0
print('after del, alive:', ref() is not None)  # 仍可能是 True

gc.collect()             # 手动触发分代 GC
print('after gc, alive:', ref() is not None)   # 应该是 False

# 看出区别了吗？引用计数处理不了循环引用，GC 才能。
```


---

## 本课题目

### single_choice · None



- [A] [1, 2, 3]
- [B] [1, 2, 3, 4]
- [C] [4]
- [D] 报错

**参考答案**：1

**解析**：b = a 只是让 b 和 a 指向同一个列表对象，修改 b 也会反映到 a 上，因此输出 [1, 2, 3, 4]。

### single_choice · None



- [A] 10
- [B] 20
- [C] None
- [D] 报错

**参考答案**：0

**解析**：整数是不可变对象，y = 20 只是让 y 重新绑定到一个新对象，不会影响 x，所以 x 仍然是 10。

### single_choice · None



- [A] [1, 2, 3]
- [B] [1, 2, 3, 4]
- [C] [4]
- [D] 报错

**参考答案**：1

**解析**：对于列表，+= 会调用 __iadd__ 进行原地扩展，a 和 b 仍指向同一个列表，所以 a 也会变成 [1, 2, 3, 4]。

### single_choice · None



- [A] 变量是存储值的容器，赋值时值被复制进变量
- [B] 变量是指向对象的引用，赋值时绑定到对象
- [C] 变量和对象是同一个概念
- [D] 变量只能指向不可变对象

**参考答案**：1

**解析**：Python 中变量是名字到对象的引用绑定，赋值只是让变量指向某个对象，而不是把值复制到变量里。

### single_choice · None



- [A] 1
- [B] 2
- [C] 报错
- [D] None

**参考答案**：0

**解析**：dict.copy() 是浅拷贝，b 是新的字典对象，修改 b['x'] 不会影响 a['x']，因此输出 1。

### single_choice · None



- [A] [1, 2]
- [B] [1, 2, 3]
- [C] [3]
- [D] 报错

**参考答案**：1

**解析**：dict.copy() 只是浅拷贝，字典中嵌套的列表仍是同一个对象，所以修改 b['x'] 会影响 a['x']。

### single_choice · None



- [A] (1, 2, 3)
- [B] (1, 2, 3, 4)
- [C] 报错
- [D] None

**参考答案**：0

**解析**：元组不可变，t2 += (4,) 会创建一个新元组并让 t2 指向它，t 仍指向原来的元组。

### single_choice · None



- [A] abc
- [B] abcd
- [C] 报错
- [D] None

**参考答案**：0

**解析**：字符串不可变，y += 'd' 会创建新字符串并让 y 指向它，x 仍指向原来的 'abc'。

### single_choice · None



- [A] [0] [0, 1]
- [B] [0, 1] [0, 1]
- [C] [0] [0]
- [D] [0, 1] [0]

**参考答案**：0

**解析**：函数内 lst = lst + [1] 创建了新列表并让局部变量 lst 指向它，不会修改传入的 a，因此 a 仍为 [0]，b 为 [0, 1]。

### single_choice · None



- [A] [0] [0, 1]
- [B] [0, 1] [0, 1]
- [C] [0] [0]
- [D] [0, 1] [0]

**参考答案**：1

**解析**：函数内 lst.append(1) 是原地修改，a 和 b 都指向同一个列表，因此两者都是 [0, 1]。

### single_choice · None



- [A] 99
- [B] 1
- [C] 报错
- [D] None

**参考答案**：1

**解析**：list(a) 创建了一个新列表（浅拷贝），修改 b 不会影响 a，因此 a[0] 仍为 1。

### single_choice · None



- [A] True True
- [B] True False
- [C] False True
- [D] False False

**参考答案**：1

**解析**：b = a 让 b 和 a 指向同一个对象，a is b 为 True；c = a[:] 创建了新列表，a is c 为 False。

### single_choice · None



- [A] 100
- [B] 1
- [C] None
- [D] 报错

**参考答案**：1

**解析**：切片 a[:] 会创建一个新的列表对象（浅拷贝），修改 b 不会影响 a，因此 a[0] 仍为 1。

### single_choice · None



- [A] [1, 2]
- [B] [1, 2, 99]
- [C] [99]
- [D] 报错

**参考答案**：1

**解析**：切片是浅拷贝，外层列表是新的，但内层列表仍是同一个对象，所以修改 b[0] 会影响 a[0]。

### single_choice · None



- [A] [1, 2]
- [B] [1, 2, 99]
- [C] [99]
- [D] 报错

**参考答案**：0

**解析**：deepcopy 会递归复制嵌套对象，b 和 a 完全独立，修改 b[0] 不会影响 a[0]。

### single_choice · None



- [A] (1, 2, [3, 4])
- [B] (1, 2, [3, 4, 5])
- [C] 报错
- [D] (1, 2, 3, 4, 5)

**参考答案**：1

**解析**：元组本身不可变，但元组中存储的列表对象是可变的，可以修改该列表的内容。

### single_choice · None



- [A] True
- [B] False
- [C] 报错
- [D] 不确定

**参考答案**：0

**解析**：小整数在 CPython 中会被缓存复用，a 和 b 指向同一个整数对象，因此 a is b 为 True。

### single_choice · None



- [A] True True
- [B] True False
- [C] False True
- [D] False False

**参考答案**：1

**解析**：== 比较值是否相等，is 比较是否为同一个对象。a 和 b 值相等但不是同一对象，所以输出 True False。

### single_choice · None



- [A] [1]
  [1]
- [B] [1]
  [1, 1]
- [C] [1, 1]
  [1, 1]
- [D] 报错

**参考答案**：1

**解析**：默认参数在函数定义时只求值一次，可变默认参数会被多次调用共享，因此第一次输出 [1]，第二次输出 [1, 1]。

### single_choice · None



- [A] [1, 2, 3]
- [B] [1, 2, 3, 4]
- [C] [4]
- [D] 报错

**参考答案**：0

**解析**：b = b + [4] 创建了一个新列表并让 b 指向它，不会修改原来的 a，所以 a 仍为 [1, 2, 3]。

### single_choice · None



- [A] 引用计数记录的是对象被多少个变量名或容器引用，当计数变为 0 时对象通常会被立即回收
- [B] 引用计数记录的是对象在内存中的字节数，当其归零时对象被回收
- [C] 引用计数只在垃圾回收器运行时才会更新，平时不变化
- [D] 引用计数只能由 gc 模块手动增减，解释器不会自动维护

**参考答案**：0

**解析**：CPython 的核心内存管理机制之一是引用计数：每个对象维护一个被引用的次数，当引用计数降为 0 时，对象会立即被释放。它记录的是引用数量而非字节数，并且由解释器自动维护，不需要手动调用 gc 模块。

### single_choice · None



- [A] 创建时计数为 1，b = a 后变为 2，del a 后减为 1，对象仍然存活
- [B] 创建时计数为 1，b = a 后仍为 1（因为 b 只是别名不增加计数）
- [C] del a 后计数变为 0，列表对象立即被回收
- [D] b = a 会复制对象，因此产生两个独立对象，各自计数为 1

**参考答案**：0

**解析**：b = a 只是让 b 指向同一个列表对象，引用计数从 1 增加到 2；del a 只删除名字 a 的绑定，计数减为 1，对象仍被 b 引用所以不会回收。赋值不会复制对象。

### multi_choice · None



- [A] 引用计数无法回收互相引用的对象，需要 gc 处理
- [B] gc 模块可以检测并回收循环引用
- [C] 引用计数和 gc 是两套互补的机制，共同管理内存
- [D] 启用了引用计数就不需要 gc，循环引用也会自动归零
- [E] gc.collect() 可以主动触发一轮循环垃圾回收

**参考答案**：[0, 1, 2, 4]

**解析**：引用计数与循环 gc 互补：前者处理计数归零，后者处理循环引用。gc.collect 可手动触发回收。认为“有引用计数就不需要 gc”是常见误解，循环引用不会自动归零。

### multi_choice · None



- [A] 它返回的值通常比对象“真实”引用数多 1
- [B] 它需要 import sys 才能使用
- [C] 它可以用来观察某对象被引用的多少
- [D] 它返回的是对象的字节大小
- [E] 调用它不会对对象产生任何临时引用

**参考答案**：[0, 1, 2]

**解析**：getrefcount 属于 sys 模块，返回计数并因传参多 1，可用于观察引用情况。它不返回字节大小，且调用时确实会产生一个临时引用。

### multi_choice · None



- [A] 每个对象都维护一个引用计数
- [B] 引用计数由解释器自动维护，开发者通常无需手动增减
- [C] 引用计数归零时对象被释放是确定性的
- [D] 引用计数无法处理循环引用
- [E] 引用计数需要开发者手动调用才能更新

**参考答案**：[0, 1, 2, 3]

**解析**：引用计数由解释器自动维护，每个对象有一个计数，归零即释放（确定性），且无法处理循环引用。它不需要开发者手动更新，故最后一项错误。

### fill_blank · None



**参考答案**：["0", "零"]

**解析**：引用计数的核心规则：计数降为 0 时对象被立即释放（在没有循环引用等特殊情况时）。

### fill_blank · None



**参考答案**：["getrefcount", "sys.getrefcount"]

**解析**：sys.getrefcount(obj) 用于返回对象的引用计数，注意返回值通常比真实引用数多 1。

### fill_blank · None



**参考答案**：["循环", "circular", "循环引用"]

**解析**：循环引用使对象的计数都不为 0，引用计数无法释放它们，需要循环垃圾回收器（gc）处理。

### code_reading · None



**参考答案**：输出为 4。a 本身、b、lst 中的元素各持有一个引用（共 3 个），再加上 getrefcount 传参产生的临时引用，共 4。

**解析**：a 和 b 指向同一列表，lst 又持有一个引用，实际引用数为 3；getrefcount 调用时把 a 作为实参传入，多一个临时引用，因此返回 4。这体现了“比真实引用多 1”的规则。

### code_reading · None



**参考答案**：每个 Node 对象仍被对方通过 other 属性引用，引用计数各为 1，不为 0，因此不会因引用计数归零而被回收；它们构成循环引用，只能由循环垃圾回收器（gc）来检测和回收。

**解析**：del n1, n2 只删除了外部名字，但两个对象通过实例属性互相引用，计数保持为 1。引用计数无法处理这种情况，正是循环 gc 存在的意义。

### code_reading · None



**参考答案**："abc" 仍被 s2 引用，引用计数为 1，不会被回收；而 "xyz" 被 s1 引用，计数为 1。

**解析**：s2 = s1 使 "abc" 计数增至 2；s1 = "xyz" 只是把名字 s1 重新绑定到新对象，"abc" 计数减为 1，因仍被 s2 引用而不回收。

### scenario · None



**解析**：对象之间互相引用使各自引用计数都不为 0，引用计数机制无法回收它们，导致内存持续增长。解决方向包括：使用 gc 模块的循环垃圾回收（必要时手动触发）、打破循环引用（如使用弱引用 weakref）、或在业务层清理不再使用的缓存条目。

### single_choice · None



- [A] 它返回对象的引用计数，但由于调用时会把 obj 作为参数传入，返回值通常比实际引用数多 1
- [B] 它返回对象当前的精确引用计数，没有任何偏差
- [C] 它返回对象的字节大小
- [D] 它返回一个布尔值，表示对象是否只被引用一次

**参考答案**：0

**解析**：sys.getrefcount 在调用时会把 obj 临时作为实参传入，这个临时引用会使计数 +1，因此返回值通常比“真实”引用数多 1，常被称为“比实际多 1”的计数。它不返回字节大小或布尔值。

### single_choice · None



- [A] 把对象放入一个列表，例如 lst.append(obj)
- [B] 对对象执行 del 语句
- [C] 对象离开其所在函数的局部作用域
- [D] 把一个变量重新绑定到别的对象

**参考答案**：0

**解析**：将对象放入容器（如 append）会让容器持有对该对象的引用，引用计数增加。del、离开作用域、重新绑定都会减少原有对象的引用计数。

### single_choice · None



- [A] 函数 f 执行完毕、局部名字 s 被销毁时
- [B] 函数 f 被调用之前
- [C] 字符串对象永远不会被回收
- [D] 只有在解释器退出时才会被回收

**参考答案**：0

**解析**：局部变量 s 在函数返回后随栈帧销毁，其引用的字符串对象引用计数减为 0（若无其他引用），CPython 会立即回收它。这体现了引用计数“实时回收”的特点。

### single_choice · None



- [A] 循环引用（对象之间相互引用）可能使引用计数都不为 0，需要额外的循环垃圾回收器来处理
- [B] 引用计数可以自动回收所有对象，包括循环引用，所以不需要其他机制
- [C] 引用计数会主动检测并打破循环引用
- [D] 只要使用列表就不会产生循环引用

**参考答案**：0

**解析**：引用计数只能处理引用数归零的情况。若两个对象互相引用，各自的计数都不为 0，无法靠引用计数释放，需要 CPython 的循环垃圾回收器（gc）来检测并回收。

### single_choice · None



- [A] 2
- [B] 1
- [C] 0
- [D] 不确定，取决于对象类型

**参考答案**：0

**解析**：x 本身持有一个引用，加上 getrefcount 传参时的临时引用，共 2。因此返回值通常为 2（比实际 1 多 1）。这是对 getrefcount “多 1”特性的直接应用。

### single_choice · None



- [A] 小整数会被缓存复用，多个变量可能引用同一对象，因此其引用计数可能大于 1 且不由单个变量独占
- [B] 每个整数都是全新对象，引用计数始终为 1
- [C] 整数对象不参与引用计数
- [D] 小整数缓存会导致整数无法被回收

**参考答案**：0

**解析**：CPython 缓存一定范围内的小整数，多个变量可能指向同一对象，因此该对象的引用计数反映的是所有引用它的地方之和，而非某个变量独占。它不影响引用计数的正常增减。

### single_choice · None



- [A] 当最后一个引用被移除的瞬间，对象即被释放，回收是确定性的
- [B] 对象总是在程序退出时才被统一回收
- [C] 必须显式调用 gc.collect() 才会回收
- [D] 只有在内存不足时才会回收

**参考答案**：0

**解析**：引用计数的一个重要优势是回收的确定性：当最后一个引用消失、计数归零时对象立即被释放，不需要等到程序结束或手动触发。gc.collect 主要针对循环引用。

### multi_choice · None



- [A] del 一个引用该对象的变量
- [B] 把该变量重新绑定到另一个对象
- [C] 该对象作为局部变量所在的函数返回
- [D] 把该对象追加进一个列表
- [E] 删除包含该对象的容器元素

**参考答案**：[0, 1, 2, 4]

**解析**：del、重新绑定、离开作用域、从容器中删除元素都会移除对对象的引用，使计数减少。而把对象放入容器（如列表追加）会增加引用，不是减少。

### single_choice · None



- [A] 新创建的对象默认位于最老的一代，以减少扫描次数
- [B] 第 0 代对象经过一次回收存活后会被提升到第 1 代
- [C] 引用计数无法处理任何循环引用，只能靠分代回收解决
- [D] 分代回收会在每次分配对象时都扫描全部三代对象

**参考答案**：1

**解析**：CPython 将对象按存活时间分为三代，新对象在第 0 代，经过一次回收仍存活会被提升到下一代。选项 A 错在默认位于第 0 代；选项 C 错在引用计数能处理大部分垃圾，只是处理不了循环引用；选项 D 错在分代回收按阈值触发且通常优先扫描年轻代。

### single_choice · None



- [A] 对象的引用计数变为 0
- [B] 对象被一个全局变量引用
- [C] 两个对象互相引用，但外部已无引用指向它们
- [D] 对象仅被局部变量引用，且函数尚未返回

**参考答案**：2

**解析**：循环引用会使彼此的引用计数都不为 0，引用计数机制无法检测，需要分代回收来处理。选项 A 会立即触发回收；B、D 都是正常的可达引用，本就不该被回收。

### single_choice · None



- [A] Python 会立即抛出异常并终止程序
- [B] __del__ 方法会被自动忽略，不影响回收
- [C] 在较新的 CPython 中，带 __del__ 的对象也能被回收，但顺序无法保证，早期版本可能无法回收
- [D] __del__ 会阻止对象进入第 0 代

**参考答案**：2

**解析**：循环引用加 __del__ 曾在旧版本中导致对象无法回收；较新的 CPython 改进了对带 __del__ 循环的收集能力，但析构顺序仍不确定。因此不能依赖 __del__ 做关键资源清理。

### single_choice · None



- [A] 返回一个整数，表示当前第 0 代的阈值
- [B] 返回一个元组 (threshold0, threshold1, threshold2)
- [C] 返回当前已分配但未回收的对象数量
- [D] 返回上次回收耗时（秒）

**参考答案**：1

**解析**：gc.get_threshold() 返回包含三个整数的元组，对应各代触发回收的阈值；gc.set_threshold() 用于修改它们。

### single_choice · None



- [A] 判断对象是否被引用计数管理
- [B] 判断对象是否被当前 GC 跟踪，可能参与循环引用的处理
- [C] 判断对象是否已经死亡
- [D] 判断对象是否支持弱引用

**参考答案**：1

**解析**：gc.is_tracked() 返回对象是否在 GC 的跟踪集合中。不包含引用其他被跟踪对象的原子类型通常返回 False。

### single_choice · None



- [A] 回收第 0 代对象，常用于短生命周期对象较多的场景
- [B] 只回收第 2 代对象，减少对年轻代的干扰
- [C] 清空引用计数为 0 的对象并重置阈值
- [D] 冻结当前对象集合，防止它们被回收

**参考答案**：0

**解析**：gc.collect(0) 只回收第 0 代，即最年轻的一代，常用于高频短生命周期对象的场景中及时释放内存，开销比全代回收小。

### multi_choice · None



- [A] 引用计数是主要的、即时性的内存回收方式
- [B] 分代回收用于处理引用计数无法处理的循环引用
- [C] gc.collect() 只能回收第 0 代对象
- [D] gc.disable() 会停止自动分代回收，但引用计数仍然工作
- [E] 所有 Python 对象都会被分代回收器跟踪

**参考答案**：[0, 1, 3]

**解析**：A、B、D 分别描述引用计数的作用、分代回收的定位、gc.disable 的语义，均正确。C 错在 gc.collect() 默认回收全部代；E 错在原子类型等对象通常不被跟踪。

### multi_choice · None



- [A] 将双向引用改为单向引用
- [B] 使用 weakref 存储反向引用
- [C] 在长生命周期对象上使用 __del__ 来主动释放
- [D] 在合适时机手动调用 gc.collect()

**参考答案**：[0, 1, 3]

**解析**：打破或弱化循环、适时手动回收都是有效手段。C 中依赖 __del__ 不可靠：带 __del__ 的循环在历史上可能无法回收，析构顺序也不确定，因此不能作为缓解手段。

### multi_choice · None



- [A] gc.collect(1) 回收第 0 代和第 1 代
- [B] gc.get_count() 返回一个三元组，表示各代当前计数
- [C] gc.set_threshold(700, 10, 10) 修改各代回收阈值
- [D] gc.get_referrers(obj) 返回直接引用 obj 的对象列表
- [E] gc.collect() 会同时强制清空所有弱引用指向的对象

**参考答案**：[0, 1, 2, 3]

**解析**：A、B、C、D 都是 gc 模块公开接口的正确描述。E 错在回收行为不应被理解为强制清空所有弱引用对象；弱引用目标只有在没有强引用时才会被回收。

### fill_blank · None



**参考答案**：["分代", "分代回收", "generational", "generational GC", "gc", "垃圾回收"]

**解析**：CPython 的垃圾回收由引用计数和分代回收（generational GC）共同完成，分代回收用于清理引用计数无法处理的循环引用。

### fill_blank · None



**参考答案**：["disable", "disable()"]

**解析**：gc.disable() 停用自动分代回收，但引用计数仍正常工作；gc.enable() 用于恢复。

### code_reading · None



**参考答案**：del a 和 del b 只删除了外部对这两个对象的强引用。由于 a.next 和 b.next 彼此引用，两个对象的引用计数都不为 0，引用计数机制无法回收它们。它们成为不可达的循环引用，需要 gc.collect() 触发（或自动触发的分代回收）才能被回收。gc.collect() 返回本次回收到的不可达对象数，是合法调用，结果通常是非负整数。

**解析**：本题考察循环引用与分代回收的分工：引用计数处理普通垃圾，循环引用交由 GC。del 仅减少外部引用，不会立即回收互为引用的对象。

### single_choice · None



- [A] 第 0 代对象数量减去第 1 代对象数量达到该值时触发第 1 代回收
- [B] 分配对象数减去释放对象数达到该值时触发第 0 代回收
- [C] 第 2 代回收的最大对象数量
- [D] 手动调用 gc.collect() 时需要等待的毫秒数

**参考答案**：1

**解析**：gc 内部维护分配计数与释放计数之差，当该差值超过 threshold0 时触发第 0 代回收。threshold1 和 threshold2 分别控制第 1、2 代回收的触发条件。

### scenario · None



**解析**：应从循环引用入手：用弱引用或单向引用打破父子互指；在合适时机手动触发 gc.collect() 或调整分代回收阈值；避免依赖 __del__ 做关键清理，因为析构顺序不确定且历史版本可能阻碍循环回收；gc.disable() 只会让循环引用更晚释放，不是解决方案。

### single_choice · None



- [A] 只回收第 0 代对象
- [B] 回收全部三代对象，等价于 gc.collect(2)
- [C] 仅清理已断开的循环引用，不触碰存活对象
- [D] 强制将回收阈值重置为默认值

**参考答案**：1

**解析**：gc.collect() 默认参数为 generation=2，执行一次完整的全代回收。它会遍历各代并回收不可达对象，但不会改变阈值设置。

### single_choice · None



- [A] 完全关闭引用计数机制，垃圾不再被回收
- [B] 仅关闭自动分代回收，手动调用 gc.collect() 仍可执行回收
- [C] 禁止创建任何新对象
- [D] 清空当前所有可回收对象

**参考答案**：1

**解析**：gc.disable() 只停用自动触发的分代回收，引用计数仍在工作，且手动 gc.collect() 依旧可以运行。选项 A 是对引用计数的误解。

### single_choice · None



- [A] 返回当前被 GC 跟踪的所有对象列表
- [B] 返回所有仍被引用的对象及其引用计数字典
- [C] 返回下一次回收将释放的对象列表
- [D] 返回历史上被回收过的对象总数

**参考答案**：0

**解析**：gc.get_objects() 返回当前被垃圾回收器跟踪的对象列表，常用于调试内存问题，但它不保证包含全部对象（如部分内置类型可能不被跟踪）。

### single_choice · None



- [A] 自定义类实例
- [B] 包含其他对象引用的列表
- [C] 只包含不可变原子类型（如整数）的对象
- [D] 协程对象

**参考答案**：2

**解析**：GC 只跟踪可能形成循环引用的容器类型对象。整数等原子类型不包含对其他被跟踪对象的引用，通常不被 GC 跟踪，它们靠引用计数即可回收。

### single_choice · None



- [A] 冻结当前所有存活对象，使它们不再参与后续的 GC 扫描
- [B] 阻止新对象被分配到第 0 代
- [C] 将对象永久锁定在内存中，无法被任何机制回收
- [D] 暂停 GC 直到调用 gc.unfreeze()

**参考答案**：0

**解析**：gc.freeze() 将当前所有被跟踪对象移出 GC 各代，之后不再扫描它们，常用于 fork 前减少写时复制开销。它不改变引用计数语义，也不能阻止对象在未来被引用计数释放。

### single_choice · None



- [A] 调用 gc.disable() 关闭回收以减少开销
- [B] 使用 gc.set_debug(gc.DEBUG_LEAK) 观察回收情况并用 gc.get_referrers 分析引用
- [C] 用 del 删除所有全局变量
- [D] 把 sys.setrecursionlimit 调大

**参考答案**：1

**解析**：定位循环引用可用 gc 的调试与内省接口，如开启 DEBUG_LEAK 查看难以回收的对象，再用 gc.get_referrers / gc.get_referents 分析引用链。关闭回收或改递归限制都与问题无关。

### single_choice · None



- [A] 弱引用会增加对象的引用计数，从而阻止其被回收
- [B] 弱引用不会增加引用计数，因此不阻止对象被垃圾回收
- [C] 只有被 GC 跟踪的对象才能被弱引用
- [D] 弱引用只能指向不可变对象

**参考答案**：1

**解析**：弱引用不增加目标对象的引用计数，因此目标对象在仅有弱引用时仍可被引用计数或分代回收释放。部分内置类型（如 list、tuple）不支持弱引用，但不限于不可变对象。
