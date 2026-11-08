# s4u3l1 弱引用（Weak Reference）：让对象“可被回收”，让缓存“不泄漏” / Python 中的循环引用与内存管理 / py.mem.leak_debug —— Python 内存泄漏调试

> 来源 `content/lessons/s4u3l1.json`

## py.mem.weakref

# 弱引用（Weak Reference）：让对象“可被回收”，让缓存“不泄漏”

> 一句话直觉：**弱引用（weak reference）让你“看着”一个对象，但不阻止它被垃圾回收（garbage collection）——这是缓存、观察者、图结构等场景避免内存泄漏的关键工具。**

---

## 1. 为什么需要弱引用：强引用（strong reference）的“粘连”问题

在 Python 中，**变量名绑定的都是对象的引用（reference）**。默认的引用计数（reference counting）机制让对象只要被引用就不会被回收。

```python
import sys

class Node:
    pass

n = Node()
print(sys.getrefcount(n))  # 输出引用计数（含 getrefcount 自身的临时引用）
```

问题在于：很多“辅助”数据结构并不想拥有对象的所有权。比如缓存、监听器列表——如果它们**强引用**对象，对象永远无法释放，就是典型的**内存泄漏（memory leak）**。

```python
# 一个经典泄漏：对象注册到全局字典后再也删不掉
_registry = {}

class Widget:
    def __init__(self, name):
        self.name = name
        _registry[name] = self  # 强引用导致 Widget 永不释放

w = Widget("a")
del w  # 期待释放，但 _registry 还持有它
print(list(_registry))
```

**弱引用**就是为这种“我关心你，但不拥有你”的关系设计的。

---

## 2. 最小可用：`weakref.ref`

标准库 `weakref` 提供 `ref(obj)` 返回一个弱引用对象。调用它可以在对象仍存活时得到原对象，对象被回收后返回 `None`。

```python
import weakref

class Node:
    def __init__(self, name):
        self.name = name
    def __repr__(self):
        return f"Node({self.name})"

n = Node("A")
r = weakref.ref(n)

print(r())            # 对象还活着：<Node A>
print(r() is n)       # True
del n                 # 删除唯一的强引用
print(r())            # 对象已被回收：None
```

关键点：**弱引用自身不是强引用**，它不增加目标的引用计数。

```python
import sys, weakref

class T: pass
t = T()
print(sys.getrefcount(t))
r = weakref.ref(t)
print(sys.getrefcount(t))  # 数值不变，弱引用不增加计数
```

---

## 3. 回调（callback）：对象“临终”时通知你

`weakref.ref(obj, callback)` 支持对象被回收前调用回调，常用于清理索引、取消注册。

```python
import weakref

class Connection:
    def __init__(self, name):
        self.name = name

c = Connection("db-1")

def on_gone(ref):
    print(f"{ref} 引用的对象已被回收")

r = weakref.ref(c, on_gone)
print("before del")
del c                 # 触发回调
print("after del")
```

> 注意：回调里 `ref()` 通常已经返回 `None`，只能拿到弱引用本身（比如用于字典 key 匹配）。

---

## 4. 三大实用容器：`WeakValueDictionary` / `WeakKeyDictionary` / `WeakSet`

### 4.1 `WeakValueDictionary`：缓存首选

值被弱引用持有，值一旦无强引用即从字典中自动消失——正是缓存想要的语义。

```python
import weakref

class Expensive:
    def __init__(self, key):
        self.key = key

cache = weakref.WeakValueDictionary()

def get(key):
    obj = cache.get(key)
    if obj is None:
        obj = Expensive(key)
        cache[key] = obj
    return obj

a = get("x")
print(list(cache))   # ['x']
del a                # 唯一强引用消失
gc.collect() if False else None
import gc; gc.collect()
print(list(cache))   # [] —— 条目自动清理
```

### 4.2 `WeakKeyDictionary`：给对象“贴便签”

常用于给对象附加元数据而不阻止其被回收。

```python
import weakref

class Session:
    pass

meta = weakref.WeakKeyDictionary()
s = Session()
meta[s] = "user=alice"
print(meta[s])
del s
import gc; gc.collect()
print(len(meta))     # 0
```

### 4.3 `WeakSet`：观察者/监听器列表

```python
import weakref

class Listener:
    pass

listeners = weakref.WeakSet()
l1, l2 = Listener(), Listener()
listeners.add(l1); listeners.add(l2)
print(len(listeners))   # 2
del l1
import gc; gc.collect()
print(len(listeners))   # 1
```

> 模块本身还提供 `WeakSet` 的类 `weakref.WeakSet`；注意名字与内置 `set` 不同。

---

## 5. 手动管理：`WeakMethod` 与 `finalize`

- `weakref.WeakMethod`：弱引用绑定方法（bound method），避免因持有方法而拖住 `self`。
- `weakref.finalize`：更安全、可控的清理器，可在对象销毁时执行任意清理逻辑，并支持取消。

```python
import weakref

class Handler:
    def handle(self):
        print("handling")

h = Handler()
m = weakref.WeakMethod(h.handle)
print(m() is not None)  # True
del h
import gc; gc.collect()
print(m())              # None

class Resource:
    def close(self):
        print("resource closed")

res = Resource()
fin = weakref.finalize(res, res.close)
print(fin.alive)        # True
del res; import gc; gc.collect()
print(fin.alive)        # False，且打印 'resource closed'
```

---

## 6. 局限与工程注意

- **不是所有对象都能弱引用**：`list`、`dict`、`tuple`、`int`、`str` 等内置类型不支持弱引用；自定义类、`list` 子类通常可以。
  ```python
  import weakref
  weakref.ref([1, 2, 3])   # TypeError: cannot create weak reference to 'list' object
  class MyList(list): pass
  weakref.ref(MyList())    # OK
  ```
- **弱引用可能提前“消失”**：不要缓存 `r()` 的结果到长时间存活的变量，否则又变成强引用。
- **循环引用 + 弱引用的组合**：弱引用不会阻止循环被 GC，但你要理解何时触发；必要时用 `gc.collect()` 验证。
- **多线程场景**：弱引用容器不是线程安全的，读写需要外部同步。

---

## 7. 小结

| 工具 | 适用场景 |
|---|---|
| `weakref.ref` | 单个对象的“观察”而不拥有 |
| `weakref.ref(obj, cb)` | 对象回收时回调清理 |
| `WeakValueDictionary` | 缓存（值可回收） |
| `WeakKeyDictionary` | 给对象附加元数据 |
| `WeakSet` | 观察者 / 监听器集合 |
| `WeakMethod` | 弱引用绑定方法 |
| `weakref.finalize` | 显式、可取消的清理器 |

**记忆口诀**：缓存、观察、便签、清理 —— 弱引用四大用途。

```python
import gc
import weakref


class Image:
    def __init__(self, name: str, data: bytes):
        self.name = name
        self.data = data

    def __repr__(self):
        return f"Image({self.name})"


# 1) 用 WeakValueDictionary 做一个“不占内存”的图片缓存
cache: "weakref.WeakValueDictionary[str, Image]" = weakref.WeakValueDictionary()


def load(name: str) -> Image:
    img = cache.get(name)
    if img is None:
        img = Image(name, b"...")   # 模拟从磁盘加载
        cache[name] = img
    return img


# 使用：调用方持有强引用，缓存只是“看着”
a = load("cat.png")
print("cache keys:", list(cache))

# 调用方释放后，缓存条目自动消失
del a
gc.collect()
print("cache keys after del:", list(cache))


# 2) finalize：对象销毁时自动清理外部资源
class FileHandle:
    def __init__(self, path: str):
        self.path = path

    def close(self):
        print(f"closed {self.path}")


fh = FileHandle("/tmp/demo.txt")
cleaner = weakref.finalize(fh, fh.close)
print("alive before del:", cleaner.alive)
del fh
gc.collect()
print("alive after del:", cleaner.alive)
```

## py.mem.cycle

# py.mem.cycle：Python 中的循环引用与内存管理

## 一句话直觉

Python 的垃圾回收（Garbage Collection, GC）主要靠“引用计数”（Reference Counting），但当两个或多个对象**互相引用**时，引用计数永远不归零，对象就泄漏了——理解循环引用（Reference Cycle）是写出不爆内存的 Python 程序的第一步。

---

## 1. 为什么会有这个问题：引用计数不是万能的

Python 里每个对象都有一个计数器，记录“有多少个变量/容器指向我”。当计数变为 0，CPython 立即释放这块内存。这是最主流、最及时的回收方式。

```python
import sys

a = []
print(sys.getrefcount(a))  # 2：一个是 a，一个是 getrefcount 的临时参数

b = a
print(sys.getrefcount(a))  # 3：a、b、临时参数

del b
print(sys.getrefcount(a))  # 2：回到初始
```

当 `del b` 执行后，`a` 的计数减 1；如果 `a` 也 `del`，计数归零，列表立刻被释放。

**关键结论**：引用计数只能处理“单向”的引用，一旦形成环，计数永远不会降到 0。

---

## 2. 循环引用长什么样

最常见的形式是**对象自己引用自己**，或**两个对象互相引用**。

```python
import gc
import sys

class Node:
    def __init__(self, name):
        self.name = name
        self.parent = None
        self.children = []

# 经典循环：parent 持有 child，child 又反过来持有 parent
parent = Node("parent")
child = Node("child")
parent.children.append(child)
child.parent = parent

# 此刻 parent 和 child 互相引用
del parent
del child

# 即使删掉了外部变量，两个对象仍然活在 GC 的“不可达但未回收”集合里
print("collectable:", gc.collect())  # 返回被回收的对象数，通常是 2
```

运行以上代码，`gc.collect()` 至少返回 2，说明 CPython 的分代 GC 帮你收拾了这个环。但如果你把 `gc.disable()`，这两个对象就会**永久驻留内存**。

---

## 3. Python 的兜底机制：分代 GC（Generational GC）

Python 自己也知道引用计数不够用，所以内置了一个**循环垃圾回收器**：

- 它跟踪所有“可能是容器”的对象（list、dict、自定义对象等）。
- 定期扫描，找出**只被环内对象引用**的集合，把它们整体回收。
- 分三代（0/1/2），越老的对象扫描频率越低，以节省成本。

```python
import gc

print(gc.get_threshold())   # 默认 (700, 10, 10)
print(gc.isenabled())       # True

# 手动触发一次全量回收
n = gc.collect()
print("collected:", n)

# 查看当前代中被跟踪的对象数量
print(gc.get_count())
```

**关键结论**：循环引用最终能被回收，但不是“立刻”，也不保证“永远”。在长期运行的服务中，GC 停顿和内存峰值往往是循环引用导致的。

---

## 4. 循环引用的四大常见来源

工程中真正让内存爆掉的往往是下面几种：

1. **父子双向引用**：树结构里父节点存 child、child 又存 parent。
2. **回调/闭包持有 self**：`self.handler = lambda: self.do()`。
3. **异常回溯**：`except Exception as e: ...` 里 `e` 持有整条调用栈。
4. **缓存（cache）**：缓存对象引用外部大对象，外部又引用缓存。

```python
# 陷阱 1：闭包持有 self
class Worker:
    def __init__(self):
        self.data = [0] * 1_000_000
        self.cb = lambda: self.data  # 闭包持有 self → 循环

w = Worker()
del w
import gc
print("闭包循环回收:", gc.collect())

# 陷阱 2：异常对象持有 traceback
import sys
def risky():
    try:
        raise ValueError("boom")
    except ValueError as e:
        return e  # e 持有 traceback，traceback 持有帧，帧持有局部变量

err = risky()
del err
print("异常循环回收:", gc.collect())
```

---

## 5. 工程做法：用 `weakref` 和 `__del__` 主动打断环

最优雅的方式是**让其中一条边变成弱引用（weak reference）**，这样它不增加引用计数，环就断了。

```python
import weakref

class Node:
    def __init__(self, name):
        self.name = name
        self.children = []
        self._parent = None  # 弱引用存 parent

    @property
    def parent(self):
        return self._parent() if self._parent else None

    @parent.setter
    def parent(self, p):
        self._parent = weakref.ref(p) if p else None

root = Node("root")
leaf = Node("leaf")
root.children.append(leaf)
leaf.parent = root  # 只在 leaf 里存弱引用，不构成环

del root
import gc
print("weakref 后 GC 次数:", gc.collect())  # 通常为 0，因为没有环
```

如果必须保留强引用并且要在对象销毁时做清理，可以定义 `__del__`，但注意：**在循环里的 `__del__` 会让 GC 变得复杂**（3.4 起才安全支持）。现代写法更推荐 `weakref.finalize`。

```python
import weakref

class Resource:
    def __init__(self, name):
        self.name = name
        self._finalizer = weakref.finalize(self, self._cleanup, name)

    @staticmethod
    def _cleanup(name):
        print(f"释放资源: {name}")

r = Resource("db-conn")
del r
# 输出：释放资源: db-conn
```

---

## 动手练习

**任务：给一个“双向链表”打断循环引用。**

1. 定义 `Node` 类，包含 `value`、`next`、`prev` 三个属性。
2. 构造一个 3 个节点的双向链表。
3. 用 `gc.collect()` 观察删除所有外部引用后是否产生循环。
4. 把 `prev` 改成 `weakref.ref`，再测一次，验证 `gc.collect()` 返回 0。
5. 在注释里写出结论：为什么双向链表天然容易形成循环引用？

参考骨架：

```python
import gc, weakref

class Node:
    def __init__(self, value):
        self.value = value
        self.next = None
        self.prev = None  # ← 改成 weakref.ref 试试

# 构造 3 节点双向链表 > 删除外部引用 > 调用 gc.collect()
# 对比两种 prev 实现时的 collect 返回值
```

完成后你应该能回答：**“为什么 Python 有了引用计数，还需要 GC？”**

```python
import gc
import sys
import weakref


class Node:
    """双向链表节点，prev 使用弱引用避免循环。"""
    def __init__(self, value):
        self.value = value
        self.next = None
        self._prev = None  # 弱引用

    @property
    def prev(self):
        return self._prev() if self._prev else None

    @prev.setter
    def prev(self, node):
        self._prev = weakref.ref(node) if node else None


def build_strong_cycle():
    """构造强引用循环，演示引用计数无法回收。"""
    a = Node(1); b = Node(2); c = Node(3)
    a.next = b; b.prev = a
    b.next = c; c.prev = b
    # 此时 a<->b<->c 通过 next/prev 形成强引用环
    return a, b, c


def build_weak_cycle():
    """构造弱引用版本，环被打断。"""
    a = Node(1); b = Node(2); c = Node(3)
    a.next = b; b.prev = a
    b.next = c; c.prev = b
    return a, b, c


if __name__ == "__main__":
    gc.disable()
    try:
        a, b, c = build_strong_cycle()
        del a, b, c
        # 强引用环：引用计数不归零，GC 关闭时无法回收
        print("强引用环（GC 关闭）collect:", gc.collect())  # 0
    finally:
        gc.enable()

    print("强引用环（GC 开启）collect:", gc.collect())  # 至少 3

    a, b, c = build_weak_cycle()
    del a, b, c
    # 弱引用版本：对象立即被引用计数回收
    print("弱引用环 collect:", gc.collect())  # 0
```

## py.mem.leak_debug

# py.mem.leak_debug —— Python 内存泄漏调试

> **一句话直觉**：程序越跑越慢、内存越吃越多，最后被系统 OOM（Out Of Memory，内存耗尽）杀掉——学完这节，你能自己定位“谁在偷偷攒对象不放手”，而不是靠重启续命。

前置知识：无。你只需要会写最基础的 Python 函数和 `class`。

---

## 0. 先分清“长胖”和“泄漏”

Python 有自动垃圾回收（Garbage Collection, GC），大多数临时对象用完就被回收。但如果一个对象**被某个长生命周期的容器、闭包、全局变量、缓存、循环引用链一直引用**，它就永远回收不掉。

- **正常增长**：启动时构建缓存、连接池，内存上升后稳定。
- **内存泄漏（Memory Leak）**：持续运行中对象只增不减，`gc.collect()` 也收不回。

第一件事就是**观察曲线**：是台阶式稳定，还是近似线性上升？

```python
# 最小可跑的“泄漏 vs 正常”对照
import gc, sys

class Node:
    def __init__(self, name):
        self.name = name

def make_cycle():
    a = Node("a")
    b = Node("b")
    a.peer = b
    b.peer = a
    return [a, b]   # 外部还引用，无法回收

leaked = []         # 全局容器，故意“藏”对象
for i in range(1000):
    leaked.append(make_cycle())

print("gc 前:", len(gc.get_objects()))
gc.collect()
print("gc 后:", len(gc.get_objects()))  # 几乎不变，说明确实被 leaked 引用着
```

---

## 1. 三个核心工具：`tracemalloc`、`gc`、`objgraph`

### 1.1 `tracemalloc` —— 官方“内存快照对比”

它记录**每一次分配发生在哪一行**，能直接告诉你“哪个文件哪一行在涨”。

```python
import tracemalloc, linecache

tracemalloc.start(10)                    # 保留 10 层调用栈
snap1 = tracemalloc.take_snapshot()

# —— 模拟可疑业务 ——
_cache = {}
for i in range(10000):
    _cache[i] = "x" * 1000

snap2 = tracemalloc.take_snapshot()

for stat in snap2.compare_to(snap1, 'lineno')[:3]:
    print(stat)                           # 显示增长最多的行

for stat in snap2.compare_to(snap1, 'lineno')[:1]:
    for frame in stat.traceback:
        print("  来源:", linecache.getline(frame.filename, frame.lineno).strip())
```

**结论**：`compare_to` 是最有价值的 API——两次快照做差，增长量＋调用栈 = 嫌疑点。

### 1.2 `gc` —— 看谁把对象“抓住”了

```python
import gc

# 找到所有被引用但疑似泄漏的类型实例
objs = [o for o in gc.get_objects() if isinstance(o, dict)]
print("dict 数量:", len(objs))

# 关闭/开启自动 GC，确认泄漏是否来自循环引用
gc.disable()
print("gc 是否开启:", gc.isenabled())
gc.enable()
```

**结论**：如果只有 `gc.disable()` 才涨，是循环引用；如果 `gc.collect()` 后仍涨，是外部强引用（全局变量、缓存、闭包、单例）。

### 1.3 `objgraph` —— 可视化引用链（工程级神器）

```python
# pip install objgraph
import objgraph

class Session:
    pass

_sessions = []
for _ in range(100):
    _sessions.append(Session())

objgraph.show_most_common_types(limit=5)
objgraph.show_backrefs([_sessions[0]], max_depth=3, filename="refs.png")
```

**结论**：`show_backrefs` 把“谁引用了我”画成图，一眼看穿泄漏源头。

---

## 2. 工程中 5 个最常见的泄漏模式

| 模式 | 例子 | 识别信号 | 修复 |
|------|------|----------|------|
| 全局缓存无上限 | `CACHE[key] = data` | 部署时间长就涨 | 用 `functools.lru_cache(maxsize=N)` 或 `cachetools` |
| 闭包捕获大对象 | 回调里引用大 DataFrame | 回调活着就不释放 | 显式 `del`，或把依赖拆成小参数 |
| 循环引用 + `__del__` | 自定义 `__del__` 阻止 GC | GC 后不下降 | 避免 `__del__`，改 `weakref.finalize` |
| 未关闭的资源 | 未关闭的文件/DB 连接 | 句柄数持续上升 | 用 `with` 或显式 `close()` |
| 全局事件监听器 | `signal.connect` 后从不 `disconnect` | 监听器列表越来越长 | 使用弱引用的信号（`weakref`） |

用弱引用验证“谁该被释放”：

```python
import weakref, gc

class Big:
    pass

b = Big()
ref = weakref.ref(b)
print("存活:", ref() is not None)   # True
del b
gc.collect()
print("存活:", ref() is not None)   # False —— 说明没被别处强引用
```

**结论**：`weakref` 是判断“我是否被别的地方悄悄持有”的最快方法。

---

## 3. 标准调试流程（照抄即可）

1. **复现**：写脚本循环触发可疑逻辑，`time.sleep` 观察 RSS；用 `psutil.Process().memory_info().rss` 打印。
2. **快照**：`tracemalloc.start()` → 跑一轮 → `take_snapshot()` → 再跑一轮 → `take_snapshot()` → `compare_to`。
3. **定位**：看增长最多的 1~3 行源码。
4. **确认引用链**：`objgraph.show_backrefs([obj], max_depth=5)`。
5. **修复**：加 `maxsize` / `weakref` / `contextlib.closing` / `del`。
6. **回归**：同样的脚本再跑一轮，`compare_to` 应该趋近 0。

```python
import psutil, os, gc, time

def rss_mb() -> float:
    return psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024

_cache = {}
for i in range(5):
    for j in range(100_000):
        _cache[(i, j)] = j
    gc.collect()
    print(f"第 {i} 轮后 RSS = {rss_mb():.1f} MB，缓存大小 = {len(_cache)}")
    time.sleep(0.5)
```

**结论**：缓存大小与 RSS 同步增长 = 上限缺失，直接给 `_cache` 加 `maxsize` 或换成 `lru_cache`。

---

## 4. 防患于未然：三条工程习惯

1. **一切缓存必须有上限**：`lru_cache(maxsize=...)` 或 `cachetools.TTLCache`。
2. **一切长生命周期对象尽量用 `weakref`**：监听器、观察者、父节点反向引用。
3. **CI 里加内存回归测试**：跑 1000 次业务循环，断言 RSS 增幅 < 阈值。

```python
from functools import lru_cache

@lru_cache(maxsize=1024)     # 上限 1024，超出按 LRU 淘汰
def heavy(x: int) -> int:
    return sum(range(x))

for i in range(100_000):
    heavy(i % 2048)          # 永远不会无限增长
print(heavy.cache_info())    # 看命中率、淘汰数
```

**结论**：内存泄漏 90% 不是 Python 的错，而是“作者忘了给缓存加边界”。

---

## 5. 动手练习

> **任务**：写一个故意泄漏的小服务，再用你学到的工具把它修好。

**步骤**：
1. 新建 `leaky.py`，实现 `class Order`，以及一个全局 `ORDERS = []`，写一个 `place_order(i)` 把新 `Order` 塞进 `ORDERS`，**不清理**。
2. 写 `loop()`：循环调用 `place_order` 共 200_000 次，每 50_000 次打印 `psutil` 的 RSS 和 `len(ORDERS)`。
3. 运行，记录 RSS 曲线——应该线性上升。
4. 用 `tracemalloc` 的快照对比，把增长最大的一行打印出来。
5. 修复：把 `ORDERS` 换成 `collections.deque(maxlen=1000)`。
6. 再跑一遍，验证 RSS 稳定在某个值附近，`tracemalloc.compare_to` 的增长接近 0。

**验收标准**：
- 修复前 RSS 单调上升；修复后 RSS 在前 50_000 次后基本持平（波动 < 10 MB）。
- 打印出 `tracemalloc` 对比报告，指出泄漏行就是 `ORDERS.append(...)`。

**提示**：
- `pip install psutil objgraph`。
- 如果你希望看引用链，用 `objgraph.show_backrefs([ORDERS[0]], max_depth=4)`。

做完这道题，你就掌握了从“观察现象 → 快照对比 → 定位行 → 查引用链 → 加边界 → 回归验证”完整的一条工程级内存泄漏调试链路。


---

## 本课题目

### single_choice · None



- [A] 0
- [B] 1
- [C] 2
- [D] 运行时报错，因为 WeakValueDictionary 不允许删除键

**参考答案**：1

**解析**：WeakValueDictionary 只对值保持弱引用。变量 a 被 del 后，Obj 实例没有强引用，被 GC 回收，对应条目自动消失；b 仍被变量 b 强引用，所以 cache 中只剩 'b' 一个条目。

### single_choice · None



- [A] 它返回 obj 的一个浅拷贝，修改拷贝会影响原对象
- [B] 它返回一个可调用对象，调用后若原对象还存活则返回该对象，否则返回 None
- [C] 它返回一个整数内存地址，可以用于还原对象
- [D] 它返回 obj 本身，只是不增加引用计数

**参考答案**：1

**解析**：weakref.ref 返回一个弱引用对象；它可被调用以获取原对象，若原对象已被回收则返回 None。它不阻止对象的回收，也不是拷贝或地址。

### single_choice · None



- [A] 返回 None
- [B] 抛出 ReferenceError
- [C] 返回原对象的副本
- [D] 自动重新创建原对象

**参考答案**：1

**解析**：weakref.proxy 创建的代理在原对象被回收后，任何访问都会抛出 ReferenceError。而 weakref.ref 则是调用后返回 None。

### single_choice · None



- [A] 父对象强引用子对象，子对象需要阻止父对象被回收
- [B] 对象之间互相强引用形成循环，希望打破循环以便回收
- [C] 需要确保对象在程序结束前一直存活
- [D] 需要复制一个对象并保持两者独立

**参考答案**：1

**解析**：弱引用常用于打破循环引用，让对象可以在没有外部强引用时被回收。选项 A 和 C 都要求延长对象生命周期，与弱引用目的相反；D 与弱引用无关。

### single_choice · None



- [A] callback 在弱引用对象被创建时立即执行一次
- [B] callback 在原对象被回收时被调用，并接收弱引用对象作为参数
- [C] callback 必须返回原对象，否则弱引用无效
- [D] callback 只有在手动调用 weakref.ref 实例时才会执行

**参考答案**：1

**解析**：weakref.ref(obj, callback) 中的 callback 会在原对象被回收时被调用，参数是弱引用对象本身。它不会在创建时执行，也与手动调用弱引用无关。

### single_choice · None



- [A] 0
- [B] 1
- [C] 2
- [D] 抛出 KeyError

**参考答案**：1

**解析**：WeakKeyDictionary 的键是弱引用。i1 被删除并回收后，对应的条目自动移除；i2 仍存活，因此只剩一个条目。

### single_choice · None



- [A] 因为它们是不可变对象
- [B] 因为它们没有实现 __weakref__ 槽，不支持弱引用
- [C] 因为它们总是被解释器缓存，永远不回收
- [D] 因为弱引用只能用于自定义类

**参考答案**：1

**解析**：许多内置类型没有为弱引用留出槽位（不支持 __weakref__），因此不能直接创建弱引用。不可变性不是根本原因，模块等可变类型也可能不支持或支持。

### single_choice · None



- [A] __slots__ = ('x',) 已经足够，无需修改
- [B] __slots__ = ('x', '__weakref__')
- [C] __slots__ = ('x', '__dict__')
- [D] 在类中定义 __del__ 方法

**参考答案**：1

**解析**：使用 __slots__ 的类默认不支持弱引用，必须在 __slots__ 中包含 '__weakref__'。加入 '__dict__' 可以恢复实例字典，但并不直接解决弱引用问题。

### single_choice · None



- [A] 它存储元素的强引用，元素不会被自动移除
- [B] 它存储元素的弱引用，元素被回收后自动从集合中移除
- [C] 它只能存储可哈希的弱引用对象，其它类型会报错
- [D] 它是内置 set 的子类，行为完全相同

**参考答案**：1

**解析**：WeakSet 对元素保持弱引用，元素被回收后自动从集合中移除。它要求元素可弱引用且可哈希，但不是内置 set 的子类。

### single_choice · None



- [A] ref.get()
- [B] ref()
- [C] ref.value
- [D] ref.target

**参考答案**：1

**解析**：weakref.ref 实例是可调用的，调用 ref() 返回原对象或 None。它没有 get 方法（那是某些语言的习惯），也没有 value/target 属性。

### single_choice · None



- [A] 因为弱引用列表遍历速度更快
- [B] 避免被观察对象长期持有观察者，导致观察者无法被回收
- [C] 因为弱引用可以自动排序观察者
- [D] 因为弱引用列表支持自动去重

**参考答案**：1

**解析**：如果被观察者用强引用保存观察者，可能会阻止观察者被回收，造成内存泄漏。使用弱引用可以让观察者在不被其他地方引用时被正常回收。

### single_choice · None



- [A] 立即执行回调并移除 finalize 对象
- [B] 取消已注册的回调，使其在目标对象回收时不再执行
- [C] 删除目标对象并触发回调
- [D] 将回调改为强引用，延长目标对象生命周期

**参考答案**：1

**解析**：finalize 对象提供 cancel() 用于取消回调，取消后即使目标对象被回收，回调也不会执行。cancel() 本身不会立即执行回调或删除对象。

### single_choice · None



- [A] 自定义类的实例
- [B] Python 的 list 实例
- [C] 字典中的值（自定义对象）
- [D] 模块对象

**参考答案**：1

**解析**：内置的 list、dict、tuple 等类型默认不支持弱引用，不能直接创建 weakref.ref；而自定义类实例、模块对象等通常支持。

### single_choice · None



- [A] 在类中定义 __weakref__ 属性
- [B] 在类中定义 __slots__ 且不包含 '__weakref__'
- [C] 在类中定义 __del__ 方法
- [D] 任何自定义类实例都天然支持，无需额外声明

**参考答案**：0

**解析**：普通类实例默认支持弱引用，因为类字典中隐含 __weakref__ 槽；但定义了 __slots__ 的类必须在 __slots__ 中显式加入 '__weakref__' 才能支持弱引用。选项 B 恰好相反，C 无关，D 对 __slots__ 类不成立。

### single_choice · None



- [A] True 然后 一个 A 实例
- [B] False 然后 None
- [C] True 然后 None
- [D] False 然后 一个 A 实例

**参考答案**：2

**解析**：对象存活时，r() 返回原对象，因此 r() is obj 为 True。删除 obj 并回收后，弱引用失效，r() 返回 None。

### single_choice · None



- [A] 前者对键弱引用，后者对值弱引用
- [B] 前者对值弱引用，后者对键弱引用
- [C] 两者都对键和值同时弱引用
- [D] 两者都是普通字典，只是线程安全

**参考答案**：0

**解析**：WeakKeyDictionary 的键是弱引用，WeakValueDictionary 的值是弱引用。当键（或值）对象被回收时，对应条目自动从字典中移除。

### single_choice · None



- [A] 立即调用 callback 并返回结果
- [B] 在 obj 被垃圾回收时调用 callback，除非之前显式调用 finalize 对象的 cancel()
- [C] 阻止 obj 被垃圾回收，直到 callback 执行完成
- [D] 把 callback 注册为 obj 的方法

**参考答案**：1

**解析**：finalize 注册一个在目标对象被回收时执行的回调，通常用于清理资源；返回的 finalize 对象可以调用 cancel() 取消。它不会立即执行，也不会阻止对象回收。

### single_choice · None



- [A] 创建弱引用会增加对象的引用计数
- [B] 创建弱引用不会增加对象的引用计数，因此不会阻止其被回收
- [C] 弱引用会强制对象一直存活，直到弱引用被删除
- [D] 弱引用只在多线程程序中有意义

**参考答案**：1

**解析**：弱引用的核心特点是不增加目标对象的引用计数，从而不阻止垃圾回收。它常用于缓存、观察者列表等避免循环引用或延长生命周期的场景。

### single_choice · None



- [A] 缓存条目永不失效，访问速度更快
- [B] 当缓存的值对象不再被其他地方引用时，条目会自动移除，避免内存泄漏
- [C] 它支持更快的哈希查找
- [D] 它能自动序列化缓存内容

**参考答案**：1

**解析**：WeakValueDictionary 的值是弱引用，当值对象没有其他强引用时会被回收，对应条目自动消失，适合做缓存而不必手动管理生命周期。

### single_choice · None



- [A] Node
- [B] weakref
- [C] ProxyType
- [D] NoneType

**参考答案**：2

**解析**：weakref.proxy 返回一个代理对象，其类型是 weakref.ProxyType（或 CallableProxyType），通过它可以直接访问原对象的属性，但原对象被回收后使用代理会抛出 ReferenceError。

### single_choice · None



- [A] 循环引用会导致引用计数永远不为零，因此 CPython 中这类对象永远无法被回收
- [B] 循环引用会立即导致程序内存泄漏，必须手动打破
- [C] CPython 的分代垃圾回收器能够检测并回收不可达的循环引用对象
- [D] 只有使用 weakref 才能避免循环引用造成的内存无法释放

**参考答案**：2

**解析**：引用计数确实无法单独回收循环引用，但 CPython 自带的分代 GC（gc 模块）会周期性地检测不可达的循环并回收它们，因此并非永远无法回收。选项 A、B 夸大了后果，D 中 weakref 只是打破循环的一种手段而非唯一方式。

### single_choice · None



- [A] a = []; b = [a]; a.append(b)
- [B] a = []; b = a; a.append(1)
- [C] a = {}; b = a.copy()
- [D] a = (1, 2, 3); b = a[:1]

**参考答案**：0

**解析**：选项 A 中 a 引用 b，b 又引用 a，形成双向引用环。B 是共享引用但无环，C 是浅拷贝生成新对象，D 是切片生成新元组，都不构成环。

### multi_choice · None



- [A] gc.set_debug(gc.DEBUG_LEAK) 可用于观察回收情况
- [B] gc.get_referrers(obj) 可以查看谁引用了 obj
- [C] gc.get_referents(obj) 可以查看 obj 引用了谁
- [D] gc.disable() 后仍会自动回收循环引用
- [E] gc.isenabled() 可以判断自动回收是否开启

**参考答案**：[0, 1, 2, 4]

**解析**：A、B、C、E 都是 gc 模块提供的调试/查询能力。D 错误：gc.disable() 会关闭循环引用的自动检测，需手动 collect。

### multi_choice · None



- [A] 它是垃圾回收器无法回收对象的列表
- [B] 通常为空，除非有不可回收的对象
- [C] 可以手动向其中添加对象
- [D] 向其中添加对象会阻止该对象被回收
- [E] 它里面存放的是所有被回收过的对象

**参考答案**：[0, 1, 3]

**解析**：gc.garbage 保存 GC 无法回收的对象，通常为空。手动向其添加对象会阻止回收。E 错误：它不是“回收记录”，而是“无法回收”的集合。C 虽然可以 append，但它本身是容器，向其中添加对象是其被用作阻断回收的方式，D 才是该行为的因果关系，故不选 C。

### fill_blank · None



**参考答案**：["gc", "GC", "在 gc 中", "gc 模块"]

**解析**：标准库 gc 模块提供垃圾回收与调试接口。

### fill_blank · None



**参考答案**：["weakref", "weakref 模块", "weakref.ref", "弱引用", "weakref 弱引用"]

**解析**：weakref 模块提供弱引用支持，弱引用不增加被引用对象的引用计数。

### fill_blank · None



**参考答案**：["不可达但被回收的对象数量", "回收的对象数", "被回收对象数量", "回收的对象数目", "number of unreachable objects collected"]

**解析**：gc.collect() 返回本次回收到的不可达对象数量。

### code_reading · None



**参考答案**：不会归零。a 与 b 互相作为对方的强引用形成引用环，即便 del a, b 删除了外部引用，环内引用计数仍大于零；它们需要由 CPython 的分代 gc 检测并回收（如 gc.collect()），引用计数机制本身无法打破环。

**解析**：关键点是环内互相引用使计数不能下降到零，需 GC 介入。

### code_reading · None



**参考答案**：先输出 True，后输出 True。因为弱引用 r 不增加 a 的引用计数，r() 仍能取回 a 对象；del a 且无强引用后对象被回收，r 变为失效弱引用，r() 返回 None。

**解析**：弱引用本身不影响对象生命周期，对象无强引用后即被回收。

### scenario · None



**解析**：回答应包含：用 gc 模块/对象引用遍历（如 get_referrers/get_referents、gc.collect 或内存剖析）定位循环；将双向关系的一侧改为 weakref 弱引用以打破环；必要时调整或触发 gc；理解引用计数与分代 GC 的协作。

### scenario · None



**解析**：可通过 gc 调试（gc.set_debug、get_referrers）确认环的存在；将闭包对外层对象的强引用改为弱引用或重构解耦；用 gc.collect 观察回收情况；对关键路径进行内存剖析以避免延迟释放。

### single_choice · None



- [A] 引用计数和 GC 相互竞争，应关闭其中之一
- [B] 引用计数处理大部分即时回收，GC 主要弥补循环引用等计数失效的场景
- [C] GC 会替代引用计数，禁用后引用计数仍然工作且能处理环
- [D] 引用计数不会影响 GC 的触发频率

**参考答案**：1

**解析**：两者是互补关系：引用计数负责大部分对象即时释放，分代 GC 专门处理计数无法覆盖的循环不可达对象。

### single_choice · None



- [A] 自动归零并立即被引用计数机制回收
- [B] 始终大于零，直到垃圾回收器介入才能被回收
- [C] 抛出 ReferenceError
- [D] 会被立刻存入 gc.garbage 并永久保留

**参考答案**：1

**解析**：环内对象互相持有引用，引用计数不会降到零；只有分代 GC 检测到它们不可达后才会回收。不会抛出异常，也不一定进入 gc.garbage（仅当定义了 __del__ 且不可回收等特殊情况）。

### single_choice · None



- [A] 调用 gc.get_referrers(obj)
- [B] 访问 obj.__refcount__ 属性
- [C] 调用 id(obj) 的返回值
- [D] 使用 sys.setrecursionlimit(obj)

**参考答案**：0

**解析**：gc.get_referrers(obj) 返回直接引用 obj 的对象列表，是常用的调试手段。其他选项与查看引用来源无关。

### single_choice · None



- [A] __del__ 一定会在循环对象被 GC 回收时按定义顺序调用
- [B] 在较新的 CPython 中，带 __del__ 的循环对象通常仍可被 GC 回收
- [C] 只要对象定义了 __del__，就永远不会被回收
- [D] 定义了 __del__ 的对象无法参与循环引用

**参考答案**：1

**解析**：历史上带 __del__ 的循环对象难以回收，但 Python 3.4 起 GC 已能处理大多数此类情况，将其回收。因此 A、C、D 均不正确。

### single_choice · None



- [A] 双向关联时，一侧使用 weakref 弱引用
- [B] 把所有对象都放入全局列表
- [C] 给每个对象都定义 __del__
- [D] 频繁调用 gc.disable()

**参考答案**：0

**解析**：弱引用不增加引用计数，因此不会形成强引用环。放入全局列表、定义 __del__、禁用 GC 都会加重问题而非缓解。

### single_choice · None



- [A] 清空所有对象的引用计数
- [B] 强制触发一次完整的垃圾回收，包括检测循环引用
- [C] 释放当前函数的所有局部变量
- [D] 关闭自动垃圾回收

**参考答案**：1

**解析**：gc.collect() 触发一次完整回收，主要用于处理循环引用。它不重置引用计数，也与局部变量释放无关，关闭自动回收是 gc.disable()。

### single_choice · None



- [A] 新创建的对象会被先放入第 0 代，存活越久越可能被移入更高代
- [B] 所有对象都在同一代中，没有分代概念
- [C] 越老的对象检查越频繁
- [D] gc 只处理第 0 代，其余代永不回收

**参考答案**：0

**解析**：CPython 使用三代回收：新对象进入第 0 代，经过多次回收仍存活则晋升到更高代，高代检查频率更低。其余选项与实现相反。

### multi_choice · None



- [A] 引用计数无法单独处理循环引用，需要分代 GC 辅助
- [B] weakref 弱引用不会增加对象的引用计数
- [C] gc.collect() 可以强制触发一次完整回收
- [D] 只要禁用 gc，循环引用的内存就一定不会泄漏
- [E] gc.get_objects() 返回所有被跟踪对象的列表

**参考答案**：[0, 1, 2, 4]

**解析**：A、B、C、E 均为事实描述。D 错误：禁用 gc 后循环引用反而无法被回收，会导致内存持续增长。

### multi_choice · None



- [A] 父子对象互相持有对方的强引用
- [B] 对象把自身加入自己维护的列表中
- [C] 两个对象相互作为属性引用
- [D] 仅把对象放入一个局部变量后函数返回
- [E] 闭包中引用了包含该闭包的对象自身

**参考答案**：[0, 1, 2, 4]

**解析**：A、B、C、E 都可能形成引用环。D 只是普通局部引用，函数返回后引用即消失，不构成环。

### multi_choice · None



- [A] 弱引用不会阻止被引用对象被回收
- [B] 容器（如字典、列表）中的弱引用项在被引用对象消失后会自动失效或移除
- [C] weakref.ref(obj) 拿到弱引用后，取对象需要调用它本身
- [D] 弱引用可以让循环引用变成非循环的强引用
- [E] 普通对象没有定义 __weakref__ 时也可能无法被弱引用

**参考答案**：[0, 1, 2, 4]

**解析**：A、B、C、E 正确描述了弱引用行为。D 错误：弱引用不是“把弱引用变成强引用”，它本身不阻止回收。

### single_choice · None



- [A] 内存泄漏（对象仍被引用而无法回收）
- [B] 内存碎片化导致的分配失败
- [C] 栈溢出（递归过深）
- [D] 引用计数在 CPython 中失效

**参考答案**：0

**解析**：全局容器长期持有对象引用，使这些对象始终可达，垃圾回收不会释放它们，内存占用持续上升，这是典型的内存泄漏。栈溢出与递归深度有关，碎片化与回收机制有关，均与本题现象不符。

### single_choice · None



- [A] 引用计数为 0 的对象会立即被释放，但相互引用的循环需要分代回收器处理
- [B] 只要有循环引用，对象就永远不会被回收
- [C] 分代回收器会释放所有仍被全局变量引用的对象
- [D] 引用计数无法处理任何对象的释放

**参考答案**：0

**解析**：CPython 中引用计数为 0 立即释放；循环引用使计数不为 0，需要垃圾回收器（分代回收）来检测并回收不可达的循环。B 错在『永远』，C 错在会释放仍可达对象，D 明显错误。

### multi_choice · None



- [A] tracemalloc 快照对比
- [B] gc 模块获取被跟踪对象
- [C] objgraph 查看对象引用关系
- [D] 用 print 输出当前时间戳

**参考答案**：[0, 1, 2]

**解析**：tracemalloc、gc、objgraph 都是内存诊断工具。打印时间戳与内存泄漏无关，属于干扰项。

### multi_choice · None



- [A] 两个对象互相持有对方作为属性
- [B] 父对象持有子对象，子对象又回头引用父对象
- [C] 对象引用自身形成闭环
- [D] 对象仅被一个局部变量引用

**参考答案**：[0, 1, 2]

**解析**：互相引用、父子互引、自引用都会形成循环，使引用计数无法归零。仅被一个局部变量引用不构成循环，局部变量离开作用域后可正常释放。

### fill_blank · None



**参考答案**：["引用", "引用计数", "reference"]

**解析**：CPython 使用引用计数作为主要回收机制，当对象的引用计数降为 0 时立即释放；循环引用则交给分代 GC 处理。

### fill_blank · None



**参考答案**：["tracemalloc"]

**解析**：tracemalloc 是标准库中用于追踪内存分配的模块，支持 take_snapshot 和快照比较，适合定位泄漏来源。

### fill_blank · None



**参考答案**：["弱", "weak", "弱引用"]

**解析**：weakref 提供的弱引用不计入引用计数，对象在没有强引用时可被回收，是避免缓存型泄漏的常用手段。

### code_reading · None



**参考答案**：能回收。cache 中保存的是弱引用（weakref.ref），不会增加对象的引用计数。run() 返回后若调用方不保留返回值，data 对象的强引用消失，引用计数降为 0，对象被回收，之后通过该弱引用访问会得到 None。

**解析**：本题考察弱引用与强引用的区别：弱引用不保活，因此对象在失去强引用后可被回收。

### code_reading · None



**参考答案**：因为 register 把对象存入了模块级全局字典 registry，使其仍然可达，引用计数不为 0，所以对象不会被释放，形成被全局容器持有的引用型泄漏。

**解析**：对象进入全局容器后长期可达，即使函数返回、返回值被丢弃，对象也不会被回收。

### code_reading · None



**参考答案**：执行 del a 和 del b 后，两个对象互相引用，引用计数都不为 0，无法靠引用计数立即释放；它们成为不可达的循环引用，需要垃圾回收器（分代回收）检测后回收。

**解析**：循环引用导致引用计数无法归零，这正是需要 GC 处理循环的原因。

### scenario · None



**解析**：排查内存泄漏需要先稳定复现并监控内存曲线，再用内存快照对比定位增长点，进一步统计可疑对象数量并分析它们的引用持有者，最终确认未被释放的原因并修复。

### single_choice · None



- [A] 在关键时间点做快照并比较两次快照的差异，查看分配增长最多的调用栈
- [B] 只打印当前进程占用的总内存数值
- [C] 在程序启动时调用一次 gc.collect()
- [D] 把对象都改成全局变量以便观察

**参考答案**：0

**解析**：tracemalloc 的核心能力是按调用栈追踪分配，通过 take_snapshot 并在不同时间点比较，可以定位增长最多的代码位置。只打印总量无法定位来源，gc.collect 只触发回收，全局变量反而增加引用。

### single_choice · None



- [A] 弱引用不会增加对象的引用计数，因此不会阻止对象被回收
- [B] 弱引用会使对象永远存活
- [C] 弱引用可以替代所有强引用来避免泄漏
- [D] 只有内置类型才能被弱引用

**参考答案**：0

**解析**：weakref 持有的引用不计入引用计数，对象在没有强引用时可被回收；因此缓存或观察者常使用弱引用避免泄漏。弱引用不会使对象存活，也不能替代所有强引用，且并非只有内置类型可被弱引用（取决于是否支持 __weakref__）。

### single_choice · None



- [A] 全局回调列表持有了该对象的强引用
- [B] 该对象使用了太多内存
- [C] 函数返回导致局部变量被销毁
- [D] Python 不会回收函数内创建的对象

**参考答案**：0

**解析**：对象被全局容器引用后仍可达，引用计数不为 0，因此不会被回收，属于被引用型泄漏。内存大小本身不影响可达性，局部变量销毁是正常行为，Python 会回收函数内创建的对象（当无引用时）。

### single_choice · None



- [A] gc.get_objects() 可以列出当前被垃圾回收器跟踪的对象，便于查找可疑对象
- [B] gc.collect() 能释放仍被引用的对象
- [C] gc.disable() 会加快内存回收速度
- [D] gc 模块只能用于查看内存总量

**参考答案**：0

**解析**：gc.get_objects() 返回被 GC 跟踪的对象集合，配合类型统计可发现异常增长的对象。gc.collect() 只回收不可达对象，gc.disable() 会关闭自动回收可能加重泄漏，gc 模块功能远不止看总量。

### single_choice · None



- [A] 找出某个类型对象的增长趋势或对象的引用者，帮助定位持有点
- [B] 自动修复泄漏代码
- [C] 把程序内存占用降到零
- [D] 替代 Python 的垃圾回收机制

**参考答案**：0

**解析**：objgraph 能统计对象数量、展示引用链，帮助找到是谁在持有对象；它不自动修复代码、不降低总内存、也不替代 GC。

### single_choice · None



- [A] 内存在使用高峰后未立即归还操作系统，而是保留在解释器内存池中供复用
- [B] 对象被全局变量引用
- [C] 存在循环引用
- [D] 回调未取消注册

**参考答案**：0

**解析**：Python 的内存分配器会保留已申请的内存以复用，导致 RSS 不下降但对象其实已释放，这是分配器缓存而非泄漏。其余三项都是真实泄漏的常见原因。

### multi_choice · None



- [A] 在不再需要时取消注册的回调或事件监听
- [B] 对缓存使用弱引用或设置过期/上限策略
- [C] 及时关闭文件、网络连接等资源并释放其引用
- [D] 把所有对象都放入全局字典以便管理
- [E] 定期做快照对比，监控可疑类型的对象数量

**参考答案**：[0, 1, 2, 4]

**解析**：取消注册、弱引用或限容缓存、及时释放资源、持续监控都是防泄漏的有效手段。把所有对象放入全局字典反而增加强引用，是泄漏的常见来源。

### multi_choice · None



- [A] 强引用会使对象保持存活
- [B] 弱引用不阻止对象被回收
- [C] 对象可能同时被多个强引用和弱引用指向
- [D] 弱引用在对象被回收后仍然可以取回原对象

**参考答案**：[0, 1, 2]

**解析**：强引用保活，弱引用不保活，两者可并存。对象被回收后，弱引用会失效（访问返回 None 或抛出异常），无法取回原对象。
