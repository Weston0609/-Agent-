# s4u2l2 看懂 Python 程序的内存开销 / 用 tracemalloc 找到 Python 内存的“元凶”

> 来源 `content/lessons/s4u2l2.json`

## py.perf.memory_profiler

# py.perf.memory_profiler：看懂 Python 程序的内存开销

> 一句话直觉：写 Python 时程序“慢”只是表象，“内存悄悄涨、最后 OOM（Out Of Memory，内存耗尽）”才是真正的事故，而 `memory_profiler` 就是一把让你逐行看到内存增长的手术刀。

---

## 0. 为什么需要它？

Python 的内存管理（memory management，内存管理）是自动的：你写 `a = [0] * 10**7`，解释器（interpreter，解释器）悄悄替你分配了几十 MB。问题是：**它不会告诉你哪一行、哪个函数、哪次循环分配了内存**。

`memory_profiler` 是一个第三方库，可以在**函数级**和**行级**告诉你内存占用（RSS，Resident Set Size，常驻内存集）和每行增量，是分析内存泄漏（memory leak，内存泄漏）和优化数据结构的第一步工具。

---

## 1. 安装与最小可用示例

安装（pip 是 Python 的包管理器，package installer for Python）：

```bash
pip install memory_profiler psutil
```

`psutil`（process and system utilities，进程与系统工具）是 `memory_profiler` 依赖的底层库，用来读取进程内存。

最小示例：给函数加一个装饰器（decorator，装饰器）`@profile`，然后用 `python -m memory_profiler` 运行：

```python
# demo.py
from memory_profiler import profile

@profile
def make_big_list():
    a = [0] * 1_000_000      # 约 8 MB（每个 int 引用 8 字节）
    b = [str(i) for i in range(200_000)]  # 大量小字符串
    return a, b

if __name__ == "__main__":
    make_big_list()
```

运行：

```bash
python -m memory_profiler demo.py
```

输出会是这样（示例）：

```
Line #    Mem usage    Increment  Occurrences   Line Contents
=============================================================
     4     30.1 MiB     30.1 MiB           1   def make_big_list():
     5     38.2 MiB      8.1 MiB           1       a = [0] * 1_000_000
     6     48.9 MiB     10.7 MiB           1       b = [str(i) for i in range(200_000)]
```

关键列：
- `Mem usage`：执行到该行后进程的总内存。
- `Increment`：**相对上一行**的净增量——这就是我们要的“哪行吃内存”。
- `Occurrences`：该行被执行次数（循环里 > 1，要看 `Increment / Occurrences`）。

---

## 2. 逐行分析的原理与注意事项

`memory_profiler` 怎么做到逐行测量？它**把 `Increment` 按行前后采样差值**计算，本质上是通过 `psutil` 读取 RSS 两次做差。这带来两个重要推论：

1. **它不是精确分配器（allocator，分配器）级别的统计**，只是进程 RSS 的差分，所以：
   - 有噪声（几 MB 抖动正常）；
   - Python 可能缓存对象（small object allocator，小对象分配器），不一定立刻归还给操作系统。
2. **每一次采样都有开销**（默认 ~0.1s），所以只适合调试/定位，不适合放进生产链路。

控制采样间隔与精度：

```python
from memory_profiler import profile

# 每 0.01 秒采样一次，精度更细
@profile(precision=4, stream=None)  # precision=4 表示保留 4 位小数
# 但真正控制采样间隔的是 -m memory_profiler 的 -i 参数
```

命令行方式：

```bash
python -m memory_profiler -i 0.01 demo.py
```

> 结论：**采样间隔越密，图越准，程序越慢**。定位内存突变用 0.05~0.1s 即可。

---

## 3. 时间 + 内存一起看：`mprof`

函数级定位后，你可能还关心“随时间内存曲线”。`mprof` 是随 `memory_profiler` 安装的命令行工具，可画出时间-内存图。

```bash
mprof run demo.py        # 运行并记录内存快照
mprof plot               # 画出曲线（需要 matplotlib）
mprof list               # 列出历史记录
```

也可以在代码里手动打点，做更细的标注：

```python
# with_mprof.py
import time
from memory_profiler import memory_usage

def task(n: int) -> list:
    return [i * i for i in range(n)]

if __name__ == "__main__":
    # memory_usage 返回采样序列，可以理解成“随时间的内存轨迹”
    mu = memory_usage((task, (2_000_000,)), interval=0.05, timeout=5)
    print("Peak MiB:", max(mu))
    print("Start MiB:", mu[0])
    print("Delta MiB:", max(mu) - mu[0])
```

这段代码不需要装饰器，`memory_usage((func, args), interval=..., timeout=...)` 会在子进程里执行目标函数并周期采样。

---

## 4. 从内存数据到优化决策

拿到行级数据后，最常见的三类优化动作：

### 4.1 用生成器（generator，生成器）替代列表

```python
from memory_profiler import profile

N = 1_000_000

@profile
def use_list():
    data = [i * i for i in range(N)]        # 一次性朴素列表
    return sum(data)

@profile
def use_gen():
    data = (i * i for i in range(N))        # 惰性求值，几乎不占额外内存
    return sum(data)

if __name__ == "__main__":
    use_list()
    use_gen()
```

预期差异：`use_list` 会出现约几十 MB 的峰值分配，而 `use_gen` 几乎只在常量级内存上运行。

### 4.2 用 `__slots__` 削减实例内存

```python
from memory_profiler import profile

class PointDict:
    def __init__(self, x, y):
        self.x = x
        self.y = y

class PointSlots:
    __slots__ = ("x", "y")   # 禁用 __dict__，每个实例省 ~100 字节
    def __init__(self, x, y):
        self.x = x
        self.y = y

@profile
def build_points(cls, n=500_000):
    return [cls(i, i) for i in range(n)]

if __name__ == "__main__":
    build_points(PointDict)
    build_points(PointSlots)
```

### 4.3 用 `array` / `numpy` 替代 Python 列表

```python
from array import array
from memory_profiler import profile

N = 2_000_000

@profile
def as_list():
    return [float(i) for i in range(N)]     # Python 对象列表，约 8*N + 对象头

@profile
def as_array():
    return array("d", range(N))             # C 连续存储，每个 double 8 字节

if __name__ == "__main__":
    as_list()
    as_array()
```

关键结论：**同样的逻辑，数据结构选错，内存可能差 3~10 倍**，`memory_profiler` 是验证这一点的最快方式。

---

## 5. 工程级使用建议

- **只在本地或测试环境用**：`@profile` 会显著拖慢程序，别带进生产。
- **先粗后细**：先用 `mprof plot` 看整体峰值，再用 `@profile` 定位到具体行。
- **配合 `gc` 回顾**：如果怀疑循环引用（reference cycle，引用环），可以和 `gc.collect()`、`gc.get_objects()` 一起看。
- **配合 `tracemalloc`**：`tracemalloc` 是标准库里的分配追踪，和 `memory_profiler` 互补——前者按分配点（file:line）聚合，后者按执行行号展开。
- **不要迷信绝对值**：RSS 包含解释器、已导入库、缓存等，关注的是 **Increment / 差异**。

---

## 6. 动手练习

**任务：用 `memory_profiler` 对比三种计数方式，找出最省内存的写法。**

在本地新建 `mem_lab.py`，实现并对比下面三个函数对 `N = 3_000_000` 的内存增量：

1. `sum_of_list()`：`data = [i * i for i in range(N)]; return sum(data)`
2. `sum_of_gen()`：`data = (i * i for i in range(N)); return sum(data)`
3. `sum_of_formula()`：直接用数学公式 `N*(N-1)*(2N-1)//6`，不建任何容器。

要求：
- 每个函数加 `@profile`；
- 用 `python -m memory_profiler mem_lab.py` 运行；
- 记录每个函数中**最大 `Increment`** 和**峰值 `Mem usage`**，填入下表；
- 用 `mprof run mem_lab.py && mprof plot` 画一张曲线图，确认峰值时刻对应哪一行。

| 函数名 | 最大 Increment (MiB) | 峰值 Mem usage (MiB) | 是否推荐 |
| --- | --- | --- | --- |
| sum_of_list |  |  |  |
| sum_of_gen |  |  |  |
| sum_of_formula |  |  |  |

最后写一句总结：**为什么 `sum_of_gen` 比 `sum_of_list` 省内存，但 `sum_of_formula` 又完胜？** 用一句话解释“惰性求值 + 不建容器”在内存上的差别。

> 提示：`mprof plot` 需要 `matplotlib`，没有可跳过画图，只看 `mprof run` 输出的峰值。

## py.perf.tracemalloc

# 用 tracemalloc 找到 Python 内存的“元凶”

> **一句话直觉**：程序跑着跑着内存越来越大，`tracemalloc` 能告诉你**是哪一行代码、哪个文件分配了最多内存**，而不是只能看着 `top` 发呆。

前置知识：无，只需要会写 Python 函数与列表即可。

---

## 1. 为什么需要 tracemalloc？（直觉与痛点）

Python 的内存管理是自动的，但当程序出现**内存泄漏（memory leak）**或**内存占用过高（memory bloat）**时，光看 `sys.getsizeof` 或 `psutil` 只能知道“总量涨了”，却无法定位“是谁涨的”。

tracemalloc（trace memory allocation）是 Python 3.4+ 内置在标准库中的模块，它在解释器层面记录每一次内存分配的**调用栈（traceback）**，让你可以按“文件 + 行号”聚合统计内存。

典型使用场景：
- 服务进程长时间运行后 RSS 持续上涨；
- 怀疑某个函数/循环偷偷缓存了大量对象；
- 对比两个时间点的内存增量，找出“新增的分配点”。

---

## 2. 最小可用示例：启动、快照、对比

tracemalloc 的核心工作流是：`start()` → 运行代码 → `take_snapshot()` → 用 `Snapshot` 的 API 查看统计。

```python
import tracemalloc

tracemalloc.start()          # 开始追踪分配（会带来少量性能开销）

# 模拟一段“吃内存”的代码
cache = {}
for i in range(1000):
    cache[i] = "x" * 1000    # 每次分配一个 1000 字符的字符串

snapshot = tracemalloc.take_snapshot()   # 拍一张当前内存快照
top_stats = snapshot.statistics("lineno")  # 按“文件:行号”聚合

for stat in top_stats[:3]:
    print(stat)               # 打印最占内存的前 3 行

tracemalloc.stop()            # 关闭追踪，释放追踪自身的内存
```

关键点：`statistics(key_type)` 的 `key_type` 常用 `"lineno"`（按行）、`"filename"`（按文件）、`"traceback"`（按完整调用栈）。

---

## 3. 用快照对比定位“新增内存”

单次快照只能看到“当前谁占得多”。更实用的做法是：在关键步骤前后各拍一张快照，然后做**差分（diff）**，只看这段代码新增/释放了多少内存。

```python
import tracemalloc

tracemalloc.start()

# 第一阶段：准备基础数据
base = [str(i) for i in range(10_000)]
snap1 = tracemalloc.take_snapshot()

# 第二阶段：可能出问题的代码
extra = {i: "y" * 500 for i in range(5000)}
snap2 = tracemalloc.take_snapshot()

# 对比两张快照，找出第二阶段的净增长
for stat in snap2.compare_to(snap1, "lineno")[:3]:
    print(stat)   # 正数表示新增，负数表示释放

tracemalloc.stop()
```

`compare_to` 会按 `size_diff`（内存差值）排序，帮助你把注意力集中在“这段代码带来的变化”上。

---

## 4. 抓完整调用栈：`traceback` 模式

当同一行被多处调用，`lineno` 模式可能不够，需要看调用来源。用 `key_type="traceback"` 可以打印每条分配路径的完整堆栈。

```python
import tracemalloc

def make_chunk(n: int):
    return [b"z" * 1024 for _ in range(n)]   # 每个元素 1KB

def handler():
    return make_chunk(2000)

tracemalloc.start()
data = handler()
snap = tracemalloc.take_snapshot()

for stat in snap.statistics("traceback")[:2]:
    print("--- 分配点 ---")
    for line in stat.traceback.format():
        print(line)
    print(f"大小: {stat.size / 1024:.1f} KB, 数量: {stat.count}")

tracemalloc.stop()
```

这样就能看到：是 `handler` 调用了 `make_chunk`，还是别的地方触发了同一条分配路径。

---

## 5. 工程级用法与注意事项

1. **开启时机**：`tracemalloc.start()` 应在业务代码开始前调用，否则早期分配无法被记录。
2. **性能开销**：追踪会记录每次分配的调用栈，带来 CPU 与额外内存开销，**生产环境慎用**，多用于排查/测试阶段。
3. **参数控制**：`tracemalloc.start(nframe)` 可限制每条追踪保留的栈帧数，默认 1，减少开销同时兼顾定位。
4. **与 `gc` 配合**：tracemalloc 看“分配在哪”，`gc` 看“对象是否可达”。若发现内存没随对象释放而下降，可用 `gc.get_objects()` 进一步确认。
5. **输出解读**：`Size` 是当前追踪到的净分配字节；`Count` 是分配块数量；差分中正负号分别代表新增/释放。
6. **与外部工具互补**：tracemalloc 是标准库方案，适合快速定位；更复杂的场景可结合 `memory_profiler`、`objgraph` 等。

---

## 动手练习

**目标**：写一个脚本，找出下面代码中“哪个函数导致的累计内存最多”，并用 `tracemalloc` 输出其文件、行号和大小。

```python
import tracemalloc

def load_records(n):
    return [{"id": i, "name": f"user_{i}", "tags": ["a", "b", "c"]} for i in range(n)]

def load_images(n):
    return [b"\x00" * 2048 for _ in range(n)]

def main():
    tracemalloc.start()
    a = load_records(5000)
    b = load_images(3000)
    snap = tracemalloc.take_snapshot()
    for stat in snap.statistics("traceback")[:5]:
        print(stat)
        for line in stat.traceback.format():
            print(line)
        print("---")
    tracemalloc.stop()

if __name__ == "__main__":
    main()
```

要求：
1. 运行并回答：`load_records` 和 `load_images` 各占多少 KB？
2. 修改 `load_images` 的 `n`，观察 `Size` 与 `Count` 如何变化。
3. 增加一张 `snap_before`（在 `load_records` 之前），用 `compare_to` 对比出两次调用的净增量。

提示：注意 `statistics` 返回的 `Statistic` 对象有 `.size`（字节）、`.count`（块数）、`.traceback`。

```python
import tracemalloc

def load_records(n: int):
    # 每个元素是一个小型 dict，内含 list，分配较多小对象
    return [{"id": i, "name": f"user_{i}", "tags": ["a", "b", "c"]} for i in range(n)]

def load_images(n: int):
    # 每个元素是 2KB 的 bytes，属于大块分配
    return [b"\x00" * 2048 for _ in range(n)]

def main():
    tracemalloc.start(10)                     # 保留 10 层调用栈，便于定位
    snap_before = tracemalloc.take_snapshot() # 基线快照

    records = load_records(5000)              # 可疑点 1
    images = load_images(3000)                # 可疑点 2

    snap_after = tracemalloc.take_snapshot()  # 结束快照

    # 差分：只看这段代码新增的内存
    print("=== 按行号看净增量 Top5 ===")
    for stat in snap_after.compare_to(snap_before, "lineno")[:5]:
        print(stat)

    # 按完整调用栈看分配点
    print("\n=== 按调用栈看 Top3 ===")
    for stat in snap_after.statistics("traceback")[:3]:
        print(f"分配量: {stat.size / 1024:.1f} KB, 块数: {stat.count}")
        for line in stat.traceback.format():
            print(line)
        print("---")

    tracemalloc.stop()

if __name__ == "__main__":
    main()
```


---

## 本课题目

### single_choice · None



- [A] 直接用 python script.py 运行即可，标准输出会自动打印每行内存
- [B] 用 python -m memory_profiler script.py 运行，由该模块提供 profile 装饰器并打印逐行报告
- [C] 在脚本开头 import memory_profiler 后，解释器会自动对每行做内存采样
- [D] 必须在代码里显式调用 memory_profiler.profile() 并传入函数名

**参考答案**：1

**解析**：逐行内存分析工具通常通过 -m 方式运行目标脚本，由该模块注入并识别 @profile，从而在函数返回后打印每行的内存增量。直接用普通解释器运行会因名称 profile 未定义而报错；import 本身不会触发采样；也无需显式调用 profile()。

### single_choice · None



- [A] @profile 只能装饰类方法，不能装饰普通函数
- [B] profile 这个名字由分析模块在 -m 运行时注入，普通运行时并不存在
- [C] range(100000) 太大，装饰器无法处理
- [D] 内存分析要求函数必须带返回值，否则 profile 不会生效

**参考答案**：1

**解析**：@profile 并非内置名称，它由 -m 方式运行的分析模块在全局命名空间中提供。用普通方式运行时报 NameError。它与函数是否有返回值、参数规模无关，也能装饰普通函数。

### single_choice · None



- [A] 字节（B）
- [B] 兆字节（MiB）
- [C] 千字节（KB）
- [D] 页（page）

**参考答案**：1

**解析**：该报告通常以 MiB 为单位显示内存，便于观察较大规模的变化。它不是以字节、KB 或页为单位。

### single_choice · None



- [A] @profile 会改变函数的行为，比如增加返回值
- [B] @profile 由分析模块在 -m 运行时提供，用来标记需要逐行采样的函数
- [C] @profile 必须配合 print 才能输出报告
- [D] @profile 只能用在模块顶层函数上，不能用在嵌套函数上

**参考答案**：1

**解析**：@profile 是标记性装饰器，由 -m 方式运行的分析模块注入，用于指示需要逐行采样的函数。它不改变函数返回值，也不必配 print，且可用于嵌套函数。

### single_choice · None



- [A] 逐行报告失去意义，因为循环无法被统计
- [B] 这是预期结果，循环体内每行只做少量工作，累积效果体现在总量随迭代递增上
- [C] 说明列表在每次迭代都被重新创建
- [D] 说明该行存在内存泄漏

**参考答案**：1

**解析**：逐行报告按源码行采样，循环体每次迭代都会执行，单行增量小但总量随迭代次数累积。这不代表报告失效、列表重建或泄漏。

### single_choice · None



- [A] 在脚本里调用 report() 之类的函数把结果写盘
- [B] 在 shell 中把 -m 运行的输出重定向到文件
- [C] 使用 logging 在函数内打印每条语句的执行时间
- [D] 给每个变量包一层 wrapper 类

**参考答案**：1

**解析**：逐行报告默认输出到标准输出，重定向即可保存。脚本内并没有名为 report() 的统一 API。计时的 logging 和包装对象都不能生成内存逐行报告。

### single_choice · None



- [A] 峰值内存下降，但总运行时间一定更短
- [B] 峰值内存下降，因为不再需要一次性保存文件全部内容
- [C] 峰值内存不变，只是总分配次数变多
- [D] 峰值内存上升，因为迭代产生更多临时对象

**参考答案**：1

**解析**：逐行迭代只在内存中保留当前行，避免了整文件驻留，从而降低峰值。但它不保证总时间一定更短，也不会令峰值上升或保持不变。

### single_choice · None



- [A] 它只能分析用 Python 写的函数，对 C 扩展内部的内存分配无能为力
- [B] 它能精确追踪 C 扩展在每个 C 语句上的内存分配
- [C] 它能分析整个操作系统进程的内存分布
- [D] 它能自动优化代码而无需开发者介入

**参考答案**：0

**解析**：逐行内存分析工具面向 Python 源码行，对 C 扩展内部的分配细节无法逐行追踪。它不做系统级分析，也不会自动优化代码。

### single_choice · None



- [A] 第 5 行释放了第 4 行创建的大对象，内存回落到接近第 3 行之后
- [B] 第 5 行发生了内存泄漏
- [C] 第 4 行的增量一定是错误的
- [D] 第 3 行的 Memory 值表示该行分配的对象数

**参考答案**：0

**解析**：第 4 行增量 +8 表示创建大对象，第 5 行增量 -8 且总量回落到 15，说明该对象在此时被释放。负增量是正常的内存减少，不是泄漏；Memory 是总量而非对象计数。

### single_choice · None



- [A] 对两个版本的函数分别用逐行内存分析并比较报告
- [B] 用 tracemalloc 比较两版本的峰值内存
- [C] 用 timeit 比较两版本的耗时
- [D] 用 resource.getrusage 观察进程峰值 RSS

**参考答案**：2

**解析**：timeit 测的是时间，无法验证内存变化。逐行内存分析、tracemalloc 和 resource.getrusage 都能从不同角度反映内存使用，可用于验证。

### single_choice · None



- [A] 认为代码存在严重泄漏，立即重构
- [B] 视为正常波动，因为采样与垃圾回收时机可能带来微小抖动
- [C] 修改代码使这些行不再出现负增量
- [D] 说明该行根本没有执行

**参考答案**：1

**解析**：小幅负增量来自内存采样与回收时机的抖动，属正常现象。它不意味着泄漏，也不需要为此改代码，更不能说明该行未执行。

### single_choice · None



- [A] 两者完全等价，只是命令不同
- [B] 逐行内存分析侧重按源码行给出内存报告，tracemalloc 侧重按分配位置追踪 Python 对象分配的统计
- [C] tracemalloc 只能用于 C 扩展
- [D] 逐行内存分析不依赖 Python 源码

**参考答案**：1

**解析**：两者目标相近但视角不同：逐行内存分析按源码行输出内存报告，tracemalloc 按分配的调用栈/文件行追踪 Python 对象分配统计。二者不等价，tracemalloc 也不限于 C 扩展，逐行分析仍依赖 Python 源码。

### single_choice · None



- [A] Increment 列表示该行执行后进程当前的内存总量
- [B] Increment 列表示执行该行前后内存占用的差值，而 Memory 列是执行后的总量
- [C] Memory 列表示该行分配的对象个数
- [D] 两列都表示峰值内存，且只有在函数结束时才更新

**参考答案**：1

**解析**：报告通常有两列：Increment 为本行执行前后的内存变化量，Memory 为执行完该行后的常驻内存总量。它们都不是对象计数，也不是只在函数结束时更新。

### single_choice · None



- [A] 工具出错了，内存不可能下降
- [B] 该行创建的临时对象在后续行被回收，或分配/释放发生在行的边界之外
- [C] 说明该行的 Increment 应该为 0
- [D] 说明进程发生了内存泄漏

**参考答案**：1

**解析**：逐行采样基于各行的内存快照，临时对象、垃圾回收时机与行的边界交互会导致 Increment 与总量变化不完全同步。这并不意味着工具错误或内存泄漏。

### single_choice · None



- [A] 用 timeit 多次调用函数并取平均耗时
- [B] 对目标函数加上 @profile，再用 -m 方式运行该脚本并阅读逐行报告
- [C] 在函数内用 sys.getsizeof 对每个变量逐一打印
- [D] 用 gc.get_objects() 统计对象总数

**参考答案**：1

**解析**：逐行内存分析工具的核心用法就是 @profile 配合 -m 运行，直接给出逐行内存报告。timeit 测的是时间；sys.getsizeof 只测单个对象本身大小；gc.get_objects 统计的是对象数量，都不直接给出逐行内存峰值。

### single_choice · None



- [A] 它几乎不增加运行时间，可以长期在生产环境中开启
- [B] 逐行采样需要频繁读取进程内存状态，会显著拖慢程序，通常只在开发/调试时临时使用
- [C] 它只在函数结束时采样一次，因此对性能没有影响
- [D] 它会把程序替换为纯 Python 实现，因此只会更慢一点点

**参考答案**：1

**解析**：逐行内存分析需要在每行前后采集内存快照，开销明显，属于调试手段，不宜常驻生产环境。它并非只在函数结束时采样一次。

### single_choice · None



- [A] n = 100000
- [B] data = [str(i) for i in range(n)]
- [C] total = len(data)
- [D] return total

**参考答案**：1

**解析**：列表推导会一次性创建 n 个字符串对象与列表，是内存增长的主导行。整数赋值、len 调用和 return 都只产生极小的内存变化。

### single_choice · None



- [A] 把列表推导换成生成器表达式，并在后续处理中逐项消费
- [B] 把 range(n) 换成 list(range(n))
- [C] 把 n = 100000 改成 n = 10000
- [D] 在处理前先调用 gc.collect()

**参考答案**：0

**解析**：生成器表达式惰性产出元素，不需要一次性保存全部对象，可显著降低峰值。list(range(n)) 反而额外构造列表；改小 n 只是减少规模而非改变模式；gc.collect() 不能避免列表本身被创建。

### single_choice · None



- [A] 这是正常现象，函数结束后内存总会被回收
- [B] 循环内把对象累积到了某个在函数外部仍被引用的容器中
- [C] 工具把循环变量误统计为增量
- [D] 内存总量上升只是因为 Python 解释器预留了缓存

**参考答案**：1

**解析**：若对象被加入长期存活的容器（如全局列表、缓存），函数返回后引用仍在，内存不会回落。解释器缓存只能解释小幅波动，不能解释持续且不回收的增长。

### single_choice · None



- [A] 对被测函数加 @profile 装饰器
- [B] 用 -m 方式运行目标脚本
- [C] 在被测函数内部手动调用 sys.getsizeof 来替代逐行报告
- [D] 对比优化前后同一函数的逐行内存报告

**参考答案**：2

**解析**：逐行内存分析工具提供整套逐行采样与报告，手动用 sys.getsizeof 只能得到单个对象的表面大小，无法替代逐行报告。其余选项都是正常用法。

### single_choice · None



- [A] 它可以追踪每一行代码的 CPU 执行耗时
- [B] 它用于跟踪由 Python 分配的内存块，可给出分配位置的统计信息
- [C] 它只能统计 C 扩展分配的内存，无法统计纯 Python 对象
- [D] 它需要在解释器启动时永久开启，运行时无法启动

**参考答案**：1

**解析**：tracemalloc 追踪的是 Python 内存分配器（PyMem/PyObject）分配的内存块，并记录分配位置的调用栈，从而支持按文件和行号统计内存。它不测 CPU 时间（那是 cProfile/timeit 的领域），也不限于 C 扩展，且可以通过 tracemalloc.start() 在运行时启动。

### single_choice · None



- [A] 直接 import tracemalloc 后即可调用 tracemalloc.get_traced_memory()
- [B] 必须先调用 tracemalloc.start() 才开始追踪分配
- [C] 需要设置环境变量 PYTHONTRACEMALLOC 才可用，代码里不能启动
- [D] 必须用 python -X tracemalloc 之外没有任何启动方式

**参考答案**：1

**解析**：tracemalloc 默认不追踪，需显式调用 tracemalloc.start() 才开始记录分配；否则 get_traced_memory() 等函数返回空或零。环境变量 PYTHONTRACEMALLOC 只是让解释器启动时就开启，并非唯一方式。

### code_reading · None



**参考答案**：约等于 2097152（2 MiB，即约 200 万字节），表示新建的 bytearray 使当前追踪内存增加约 2 MiB。

**解析**：get_traced_memory() 返回 (current, peak)，这里取 after 和 before 的 current 之差。bytearray(2*1024*1024) 分配约 2 MiB 连续内存，因此差值约为 2097152 字节，实际可能略有其它分配带来的偏差。

### code_reading · None



**参考答案**：它输出两次快照之间按文件名聚合的内存增长统计，能看出列表推导式所在的文件新增了多少内存/多少个分配块，用于定位内存增长来源。

**解析**：take_snapshot 记录当前分配，compare_to(s1, 'filename') 计算两快照在文件名维度上的差异，逐项打印新增的内存大小和块数。列表推导式创建的字符串对象会体现在此文件中。

### code_reading · None



**参考答案**：输出 True。因为删除了 x 后当前内存 (cur) 低于历史峰值 (peak)，峰值记录的是同时持有 x 和 y 时的最高值。

**解析**：get_traced_memory() 的 current 反映当前存活分配，peak 反映自 start() 以来的最大同时分配量。del x 释放了一部分，所以当前值小于峰值。

### single_choice · None



- [A] 启动时设置环境变量后什么都不做即可自动定位到行
- [B] 启动追踪并用 take_snapshot(traceback=1) 后按 'lineno' 或 'traceback' 聚合比较
- [C] 调用 tracemalloc.stop() 后读取上一次结果
- [D] 用 tracemalloc.clear_traces() 清除后再调用 get_traced_memory()

**参考答案**：1

**解析**：要定位到行，需要开始追踪、采集快照并用 compare_to 按 'lineno'（或 'traceback'）聚合；take_snapshot 的 traceback 参数可保留调用栈层数。clear_traces 只是清空已记录数据，并不会帮你定位。

### single_choice · None



- [A] 停止追踪并清空当前追踪记录，之后 get_traced_memory 返回 (0, 0)
- [B] 只暂停追踪但保留计数，再次 start 时继续累加
- [C] 停止追踪但保留快照对象，快照对比功能随即失效
- [D] 等同于 shutdown，会关闭整个 Python 解释器

**参考答案**：0

**解析**：tracemalloc.stop() 会停止追踪并清除已记录的信息，此后查询返回 (0, 0)。它不是暂停续累，也不会关闭解释器；已生成的 Snapshot 对象仍可自行用于展示/比较。

### multi_choice · None



- [A] 只在需要排查的代码段前后分别 start/stop，或只在该段采集快照，以减少额外开销
- [B] 用 take_snapshot().statistics('lineno') 查看某时刻的内存分配排行
- [C] 用 Filter 在快照中忽略某些文件（如标准库）来聚焦业务代码
- [D] 由于追踪零开销，应始终在生产的每个请求中永久开启
- [E] 通过 compare_to 观察某个操作前后的增量来判断是否泄漏

**参考答案**：[0, 1, 2, 4]

**解析**：tracemalloc 有明显的运行时开销（记录调用栈、维护数据结构），应尽量缩小追踪范围和时长(A)，可用 statistics('lineno') 做排行(B)，可用 Filter 过滤无关模块(C)，也可用快照对比发现增量(E)。始终在生产永久开启(D)并不合理。

### scenario · None



**解析**：先 tracemalloc.start() 开启追踪，在疑似操作前后各 take_snapshot()，再用 compare_to 按 'lineno' 或 'traceback' 聚合，查看增长的行/调用栈；结合 get_traced_memory 的 current 与 peak 判断是否持续增长，从而定位泄漏点。

### scenario · None



**解析**：先 tracemalloc.start()，周期性调用 get_traced_memory() 打印 (current, peak)，需要行级线索时用 take_snapshot().statistics('lineno') 或与基线快照 compare_to 对比。需注意追踪本身有 CPU 与内存开销，应在调试/测试阶段启用，避免在高频生产路径永久开启。

### scenario · None



**解析**：可加大 traceback 层数、用 Filter 排除标准库或第三方库，按 traceback 聚合查看调用来源；同时需意识到 tracemalloc 只覆盖 Python 分配器内存，缓存/全局容器累积、C 扩展直接 malloc 或引用环都可能表现为持续增长，需要结合其它工具和代码审查判断。

### single_choice · None



- [A] (当前被追踪的内存字节数, 追踪至今的峰值字节数)
- [B] (追踪至今的峰值字节数, 当前被追踪的内存字节数)
- [C] (分配的总次数, 释放的总次数)
- [D] (追踪的代码行数, 追踪的调用栈深度)

**参考答案**：0

**解析**：get_traced_memory() 返回 (current, peak)，即当前追踪的内存总量和自 start() 以来的峰值，单位都是字节。顺序反了是常见错误。

### single_choice · None



- [A] 程序从启动到结束的总运行时间
- [B] 在这两段代码之间，哪一行代码分配了多少内存
- [C] data 列表中每个元素的字符串内容
- [D] 解释器总共创建了多少个线程

**参考答案**：1

**解析**：take_snapshot() 保存当前内存分配状态，compare_to() 计算两个快照之间的差异，按 'lineno' 聚合即可看到哪一行新增了多少内存。这是定位内存增长点的标准用法。

### single_choice · None



- [A] 会让快照记录更多调用栈帧，便于定位更早的调用来源，但内存和性能开销更大
- [B] 会强制所有对象立即回收，释放内存
- [C] 会把内存统计单位从字节改为千字节
- [D] 会让 compare_to 只能按 traceback 聚合，不能按 lineno 聚合

**参考答案**：0

**解析**：tracemalloc.start() 和 take_snapshot(traceback=N) 中的 traceback 控制记录多少层调用栈。层数越多，越能追溯到最初的分配调用，但存储和解析成本更高。

### single_choice · None



- [A] 会抛出 RuntimeError
- [B] 返回 (0, 0)，因为当前没有在追踪
- [C] 会自动隐式开启追踪并返回真实数据
- [D] 会返回上一次追踪遗留的旧数据

**参考答案**：1

**解析**：tracemalloc 在未启动时查询返回 (0, 0)，不会报错也不会自动开启。要获得有意义的数据必须先 start()。

### multi_choice · None



- [A] 可以按文件名和行号聚合内存分配，定位内存热点
- [B] 可以比较两个时间点的快照，找出内存增量来自哪段代码
- [C] 可以精确统计进程占用的全部物理内存，包含非 Python 部分
- [D] 可以记录分配时的调用栈信息，用于溯源
- [E] 可以替代垃圾回收器，自动释放未被引用的对象

**参考答案**：[0, 1, 3]

**解析**：tracemalloc 追踪的是 Python 分配器管理的内存，支持按 lineno/filename 聚合、快照对比和调用栈溯源(A、B、D)。它无法统计非 Python 分配的部分（如 C 库直接 malloc），也不负责回收内存（那是 GC 的职责）。

### multi_choice · None



- [A] 第二个参数（如 'lineno'、'filename'、'traceback'）决定聚合方式
- [B] 返回的是一个列表，元素通常是 StatisticDiff，包含大小和计数变化
- [C] 它会自动杀掉占用内存最多的进程
- [D] 比较结果中增长的项可以帮你定位内存泄漏的代码路径
- [E] compare_to 要求两个快照必须用同一个 tracemalloc 会话创建

**参考答案**：[0, 1, 3, 4]

**解析**：compare_to(other, key_type) 指定聚合键，返回 StatisticDiff 列表含 size/count 差值(A、B、D)。两个快照需在追踪已启动的同一会话中采集才有意义(E)。它不会干预进程(C 错误)。

### fill_blank · None



**参考答案**：["tracemalloc.start()", "start()", "tracemalloc.start", "start"]

**解析**：tracemalloc.start() 用于在当前线程/解释器开始追踪内存分配，之后才能用 get_traced_memory、take_snapshot 等获得数据。

### fill_blank · None



**参考答案**：["get_traced_memory()", "get_traced_memory", "tracemalloc.get_traced_memory()"]

**解析**：tracemalloc.get_traced_memory() 返回 (current, peak) 两个字节数。
