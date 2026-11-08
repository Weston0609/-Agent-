# s4u2l1 Python 性能剖析：认识 cProfile / 用 Python 自带的“性能侦察兵”定位热点

> 来源 `content/lessons/s4u2l1.json`

## py.perf.profiling_cprofile

# Python 性能剖析：认识 cProfile

> **一句话直觉**：程序的“慢”往往不是你以为的那一行，`cProfile` 就是 Python 自带的“X 光机”，能告诉你每一行函数到底被调用了多少次、累计花了多少秒。

---

## 1. 为什么要学 cProfile？

写 Python 时最怕的不是报错，而是**代码能跑，但慢得让人抓狂**。直觉常常骗人：你以为慢的是数据库查询，结果 90% 时间却浪费在一个无关紧要的字符串拼接上。

**Profiling（性能剖析）** 就是用数据代替直觉，量化地找出“热点（hot spot）”。Python 标准库自带 `cProfile`（用 C 实现，性能开销小），是工程中最常用的入口工具。

它的核心价值：
- 零依赖，标准库自带，任何环境都能用；
- 记录每个函数被调用的**次数（ncalls）**、**总耗时（tottime）**、**累计耗时（cumtime）**；
- 输出可以被 `pstats` 读取，也可以可视化（如 `snakeviz`）。

---

## 2. 最小可用示例：一次完整的剖析

`cProfile` 有三种典型用法：命令行（`python -m cProfile`）、代码内 `cProfile.run()`、以及装饰/上下文方式。先看最简的。

```python
import cProfile

def slow_square(n):
    # 故意写得很慢：每次循环都做一次无关的计算
    total = 0
    for i in range(n):
        total += i * i
    return total

def main():
    for _ in range(100):
        slow_square(10_000)

# 直接在代码中启动剖析，结果会打印到 stdout
cProfile.run("main()")
```

输出会是一张表，列含义：

| 列名 | 含义 |
|------|------|
| `ncalls` | 被调用次数 |
| `tottime` | 该函数自身执行耗时（不含子调用） |
| `percall` | `tottime / ncalls` |
| `cumtime` | 含子调用的累计耗时 |
| `filename:lineno(function)` | 函数位置 |

**关键结论**：看瓶颈先看 `tottime`，看调用链回溯用 `cumtime`。

---

## 3. 用 pstats 做排序与过滤，定位真正的热点

`cProfile.run()` 打印的表格往往很长。用 `pstats`（Profile Statistics）可以按任意维度排序、只看前 N 行。

```python
import cProfile, pstats, io

def main():
    for _ in range(100):
        slow_square(10_000)

# 把结果写入内存里的“文件对象”，避免落盘
pr = cProfile.Profile()
pr.enable()
main()
pr.disable()

s = io.StringIO()
ps = pstats.Stats(pr, stream=s).sort_stats("cumulative")
ps.print_stats(10)   # 只打印前 10 行
print(s.getvalue())
```

**要点**：`Profile.enable()/disable()` 可以让你只剖析关心的代码段，而不污染整个程序的启动过程。

---

## 4. 输出到文件 + 离线分析（工程常用姿势）

线上或长时间运行的任务，通常不在同一进程分析，而是先收集再离线看。

```python
import cProfile, pstats

def main():
    for _ in range(100):
        slow_square(10_000)

cProfile.run("main()", "profile.out")   # 结果存到文件

# 另一个 Python 会话里读取它
ps = pstats.Stats("profile.out")
ps.sort_stats("tottime").print_stats(5)
```

也可以直接命令行：

```bash
python -m cProfile -o profile.out your_script.py
python -m pstats profile.out
```

---

## 5. 读取真实场景：找出真正的瓶颈并验证优化

下面给一个“看起来很正常但很慢”的例子——拼字符串。用它来演示如何从剖析结果推理并验证优化。

```python
import cProfile, pstats, io

def concat_by_plus(n):
    s = ""
    for _ in range(n):
        s += "x"          # 每次都创建新字符串，O(n^2)
    return s

def concat_by_join(n):
    return "".join("x" for _ in range(n))

def main_bad():
    concat_by_plus(20_000)

def main_good():
    concat_by_join(20_000)

for name, fn in [("bad", main_bad), ("good", main_good)]:
    pr = cProfile.Profile()
    pr.enable()
    fn()
    pr.disable()
    s = io.StringIO()
    pstats.Stats(pr, stream=s).sort_stats("tottime").print_stats(3)
    print(f"===== {name} =====\n{s.getvalue()}")
```

运行后你会看到 `bad` 版本里 `concat_by_plus` 自己占的时间远大于 `good` 版本。这就是 **tottime 的价值**：它把“到底是不是这一行慢”这件事变成了可测量的数据。

---

## 结语

`cProfile` 教会我们的不是“怎么优化”，而是**先测量、再优化**的工程习惯。它本身几乎零成本，却能把 90% 的猜测误差消除掉。

```python
import cProfile
import pstats
import io


def slow_square(n):
    """故意写成慢版本：循环里做无意义的平方累加。"""
    total = 0
    for i in range(n):
        total += i * i
    return total


def main():
    for _ in range(100):
        slow_square(10_000)


if __name__ == "__main__":
    # 1) 用 Profile 对象只剖析我们关心的 main()
    pr = cProfile.Profile()
    pr.enable()
    main()
    pr.disable()

    # 2) 用 pstats 按累计耗时排序，打印前 8 行
    s = io.StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats("cumulative")
    ps.print_stats(8)
    print(s.getvalue())

    # 3) 也可以把结果保存到文件，方便离线分析
    cProfile.run("main()", "profile.out")
    offline = pstats.Stats("profile.out")
    offline.sort_stats("tottime").print_stats(5)
```

## py.perf.py_spy

# py.perf.py_spy：用 Python 自带的“性能侦察兵”定位热点

## 一句话直觉

> 你不需要猜代码哪里慢——`cProfile` + `pstats` 这对内置组合就是 Python 自带的“性能侦察兵（spy）”，它会如实记录每个函数被调用了多少次、花了多少时间，让你把优化精力用在真正的大头（hotspot，热点）上。

本讲标题里的 `py.perf.py_spy` 可以这样拆开理解：`py.perf` = Python performance（Python 性能），`spy` = 侦察/监视。我们要学的，就是如何在**不引入任何第三方库**的前提下，用一个标准的“间谍流程”完成性能分析（profiling，性能剖析）：

1. 装好间谍：`cProfile`
2. 让间谍跑一遍你的代码：`cProfile.run(...)` 或 `Profile` 对象
3. 读间谍报告：`pstats.Stats`
4. 从报告里挑出真正的瓶颈函数
5. 有针对性地优化，并再次“侦察”验证效果

下面分 5 个小节循序渐进。

---

## 第 1 节：为什么需要 profiler（性能分析器）

性能优化最大的坑是**凭感觉优化**。你可能花了两小时重写一个函数，结果它只占总耗时的 2%。更靠谱的办法是：先测量，再优化。

Python 标准库自带两个 profiler（性能分析器）：

- `cProfile`：用 C 实现，开销小（overhead，额外开销），适合生产前压测。
- `profile`：纯 Python 实现，开销大，已不推荐日常使用，主要用作教学参考。

`time.time()` 只能测“总墙钟时间（wall-clock time）”，它无法告诉你时间花在**哪个函数**上。`cProfile` 能。

```python
# 用 time 只能拿到整体耗时，拿不到“哪个函数慢”
import time

def slow_sum(n):
    total = 0
    for i in range(n):
        total += i
    return total

t0 = time.perf_counter()
slow_sum(1_000_000)
print("总耗时：", time.perf_counter() - t0)
# 输出：总耗时：约 0.05 秒（具体因机器而异）
# 但它没告诉你时间花在哪一行、哪个函数上
```

**结论**：想知道“哪慢”，必须上 profiler。

---

## 第 2 节：最小的 cProfile 用法——“间谍装好，跑一遍”

最简单的用法是 `cProfile.run()`，它会直接打印一份统计表。

```python
import cProfile

def fib(n):
    # 故意用朴素递归制造一个“慢函数”，方便观察
    if n < 2:
        return n
    return fib(n - 1) + fib(n - 2)

# 让 cProfile 在这个表达式上跑一遍，并打印结果
cProfile.run("fib(25)")
# 输出示例（截取）：
#          2692539 function calls (2692537 primitive calls) in 0.532 seconds
#    Ordered by: standard name
#    ncalls  tottime  percall  cumtime  percall filename:lineno(function)
#   2692537    0.532    0.000    0.532    0.000 <string>:1(fib)
```

关键列解释（**记住这 4 列就够用了**）：

| 列名 | 含义 |
|------|------|
| `ncalls` | 被调用的次数（次数特别大的函数往往值钱）|
| `tottime` | **函数体本身**消耗的时间，不含子函数 |
| `cumtime` | 累积时间（cumulative time），含它调用的所有子函数 |
| `percall` | 每次调用平均时间 |

常见误读：**优化看 `tottime`，不是 `cumtime`**。因为 `cumtime` 会被子函数“传染”，最外层的 `main` 永远是 cumtime 最大的，改它没用。

---

## 第 3 节：用 Profile 对象，把“间谍报告”导出并排序

`cProfile.run()` 是快速版；真实工程里我们更常用 `cProfile.Profile` 对象，因为能把数据保存下来，用 `pstats` 反复分析、排序、过滤。

```python
import cProfile
import pstats
import io

def a(n):
    return sum(range(n))

def b(n):
    return [x * x for x in range(n)]

def main():
    a(200_000)
    b(200_000)

# 1) 创建 profiler
pr = cProfile.Profile()
# 2) 开启/执行/关闭（用 enable/disable 包裹要分析的代码）
pr.enable()
main()
pr.disable()

# 3) 用 pstats 读取数据，并按 tottime 排序
stream = io.StringIO()
stats = pstats.Stats(pr, stream=stream).sort_stats("tottime")
stats.print_stats(5)      # 只打印前 5 个最耗时的函数
print(stream.getvalue())
```

输出会按 `tottime` 降序排出热点函数。`sort_stats` 支持的常用键：

- `"tottime"`：函数体自身耗时（**优化首选**）
- `"cumtime"`：累积耗时，用来找“入口函数”
- `"calls"`：调用次数

>`pstats.Stats(...).strip_dirs()` 可以去掉冗长的目录路径，让报告更清爽。

---

## 第 4 节：一个完整的“侦察—优化—复测”工作流

真正的工程用法是这样的闭环：

```python
import cProfile
import pstats
import io
from functools import lru_cache

# ---- 版本 1：朴素递归 ----
def fib_v1(n):
    if n < 2:
        return n
    return fib_v1(n - 1) + fib_v1(n - 2)

# ---- 版本 2：加缓存（memoization，记忆化）----
@lru_cache(maxsize=None)
def fib_v2(n):
    if n < 2:
        return n
    return fib_v2(n - 1) + fib_v2(n - 2)

def profile_call(fn, *args, label=""):
    pr = cProfile.Profile()
    pr.enable()
    fn(*args)
    pr.disable()
    s = io.StringIO()
    pstats.Stats(pr, stream=s).sort_stats("tottime").print_stats(3)
    print(f"--- {label} ---")
    print(s.getvalue())

profile_call(fib_v1, 30, label="v1 朴素递归")
profile_call(fib_v2, 30, label="v2 加 lru_cache")
```

你会看到：

- `v1`：`fib_v1` 被调用了数百万次（`ncalls` 巨大），是明显的热点。
- `v2`：`ncalls` 骤然降到几十次，整体耗时被压缩了几个数量级。

**这就是 py_spy 的标准节奏**：profile → 读 ncalls/tottime → 找到热点 → 优化 → 再 profile 验证。

---

## 第 5 节：进阶——命令行侦察与内存侦察

### 5.1 命令行方式

不写代码也能分析整个脚本：

```bash
# 会让你的脚本在 cProfile 下运行，并把结果写入 out.prof
python -m cProfile -o out.prof myscript.py

# 然后从命令行读取报告，按 tottime 排序，展示前 20 行
python -m pstats out.prof
# 进入交互后输入： stats 20  然后回车；输入 quit 退出
```

### 5.2 内存侧的“侦察兵”

`cProfile` 只看时间，不看内存。想看对象占多少内存，标准库给了 `tracemalloc`：

```python
import tracemalloc

tracemalloc.start()

big = [str(i) * 100 for i in range(10_000)]   # 造一批字符串

snapshot = tracemalloc.take_snapshot()
top = snapshot.statistics("lineno")[:3]
for stat in top:
    print(stat)   # 每一行都显示“哪个文件哪一行，占了多少内存”
```

**口诀**：时间热点找 `cProfile`，内存热点找 `tracemalloc`。两个工具都是标准库，零依赖。

---

## 小结

| 你想要的 | 用什么 |
|---|---|
| 看某段代码耗时分布 | `cProfile.Profile` + `pstats.Stats.sort_stats("tottime")` |
| 快速看一个表达式 | `cProfile.run("expr")` |
| 不写代码分析整个脚本 | `python -m cProfile -o out.prof script.py` |
| 看内存占用 | `tracemalloc` |

**核心心法**：热点看 `tottime`，不看 `cumtime`；优化前先测量，优化后再测量。

---

## 动手练习

写一个脚本 `profile_me.py`，完成下列任务：

1. 实现两个函数：
   - `contains_duplicate_slow(nums)`：用嵌套循环判断列表里是否有重复元素（O(n²)）。
   - `contains_duplicate_fast(nums)`：用 `set` 判断列表里是否有重复元素（平均 O(n)）。
2. 构造一个约 5000 个整数、且包含重复的列表，分别调用这两个函数。
3. 用 `cProfile.Profile` 对每个函数分别做一次 profile，用 `pstats` 按 `tottime` 排序，各打印前 3 行。
4. **对比两次报告的 `ncalls` 列**，用一句话解释为什么 `fast` 版本运行得快。
5. 挑战：把 `cProfile.Profile` 包成一个上下文管理器 `spy()`（用 `contextlib.contextmanager`），让调用者只需 `with spy("fast"):` 就能自动打印报告。

提交物：`profile_me.py` 文件 + 一段不超过 5 行的分析结论说明。

```python
import cProfile
import pstats
import io


def contains_duplicate_slow(nums):
    # O(n^2)：两两比较，热点会出现在这个双层循环里
    for i in range(len(nums)):
        for j in range(i + 1, len(nums)):
            if nums[i] == nums[j]:
                return True
    return False


def contains_duplicate_fast(nums):
    # 平均 O(n)：用 set 去重后比较长度
    return len(set(nums)) != len(nums)


def run_and_report(fn, data, label):
    # 通用侦察流程：enable -> 跑 -> disable -> 读报告
    pr = cProfile.Profile()
    pr.enable()
    fn(data)
    pr.disable()

    s = io.StringIO()
    stats = pstats.Stats(pr, stream=s).sort_stats("tottime")
    stats.strip_dirs().print_stats(3)   # 只打印前 3 个热点
    print(f"=== {label} ===")
    print(s.getvalue())


if __name__ == "__main__":
    # 造一个包含重复元素的数据集
    nums = list(range(2500)) * 2

    run_and_report(contains_duplicate_slow, nums, "slow 版本")
    run_and_report(contains_duplicate_fast, nums, "fast 版本")

    # 观察点：slow 的 ncalls 会是几百万级别；fast 只有个位数
    # 结论：ncalls + tottime 双高，就是我们要消灭的热点
```


---

## 本课题目

### single_choice · None



- [A] python script.py profile
- [B] python -m cProfile script.py
- [C] python profile script.py
- [D] python cProfile.run(script.py)

**参考答案**：1

**解析**：分析工具可以作为模块通过 -m 参数运行，从而对目标脚本进行性能统计；直接在脚本后加参数或把脚本当作参数传给工具都不符合调用约定。

### single_choice · None



- [A] cumtime 表示函数自身执行所消耗的时间，不含子函数调用
- [B] tottime 表示函数及其所有子函数调用所消耗的累计时间
- [C] cumtime 表示函数及其所有子函数调用所消耗的累计时间
- [D] ncalls 表示函数被调用的次数，但只统计非递归调用

**参考答案**：2

**解析**：cumtime 是包含子调用在内的累计耗时；tottime 才是不含子调用的自身耗时；ncalls 会统计所有调用，包括递归。

### single_choice · None



- [A] 该函数的耗时主要来自其自身代码，而不是子函数调用
- [B] 该函数的耗时主要来自子函数调用
- [C] 该函数没有被调用过
- [D] 该函数只被调用了一次

**参考答案**：0

**解析**：cumtime 与 tottime 接近说明子调用占比较小，耗时主要发生在函数自身。

### single_choice · None



- [A] 程序运行结果不正确，需要定位逻辑错误
- [B] 程序运行缓慢，需要找出耗时最多的函数
- [C] 程序出现未捕获异常，需要查看调用栈
- [D] 程序内存占用过大，需要定位内存泄漏

**参考答案**：1

**解析**：性能分析工具主要关注函数调用次数与耗时，适合定位性能瓶颈；逻辑错误、异常栈、内存问题需要其他手段。

### single_choice · None



- [A] 排在最前面的函数一定是自身耗时最长的函数
- [B] 排在最前面的函数通常包含子调用在内的累计耗时较高，可能是调用链入口
- [C] 排序结果与函数调用次数完全无关
- [D] 排序结果不能通过任何参数调整

**参考答案**：1

**解析**：按累计时间排序时，靠前的往往是包含大量子调用的上层函数，不能直接等同于自身耗时最长。

### single_choice · None



- [A] -s tottime
- [B] -s cumtime
- [C] -t tottime
- [D] -c tottime

**参考答案**：0

**解析**：cProfile 命令行支持 -s 指定排序字段，如 -s tottime 按自身耗时排序。

### single_choice · None



- [A] 递归调用会被合并为一次调用统计
- [B] 递归调用会被多次统计，报告中的 ncalls 可能包含递归次数
- [C] 递归函数无法被性能分析工具分析
- [D] 递归函数的 tottime 一定为 0

**参考答案**：1

**解析**：分析工具会统计每次调用，包括递归产生的调用，因此 ncalls 可能较大。

### single_choice · None



- [A] ncalls
- [B] tottime
- [C] cumtime
- [D] memory_usage

**参考答案**：3

**解析**：ncalls、tottime、cumtime 是分析报告的典型字段；memory_usage 不是该报告的标准字段。

### single_choice · None



- [A] 分析工具会完全阻止程序运行
- [B] 分析过程会引入额外开销，通常会拖慢程序
- [C] 分析工具只能分析内存，不能分析时间
- [D] 分析工具只能在程序结束后使用，不影响运行

**参考答案**：1

**解析**：性能分析会记录函数调用与耗时，带来额外开销，因此程序在分析时通常会变慢。

### single_choice · None



- [A] 把代码片段封装成函数或字符串，用分析工具的 run() 执行并输出统计
- [B] 必须对整个脚本重新运行，无法只分析片段
- [C] 只能通过修改解释器源码实现
- [D] 只能使用操作系统自带的性能计数器

**参考答案**：0

**解析**：可以把待分析代码封装为函数或字符串，交给分析工具执行，从而只关注目标片段。

### single_choice · None



- [A] 分析结果中的时间绝对精确，可直接作为优化后的性能指标
- [B] 分析结果受运行时环境、输入规模等影响，应结合多次运行和基准测试判断
- [C] 分析结果只与代码有关，与机器负载无关
- [D] 分析结果中的调用次数一定是准确的，时间一定不准确

**参考答案**：1

**解析**：性能分析结果会受环境与输入影响，应多次测量并结合基准测试，不宜直接当作绝对指标。

### single_choice · None



- [A] 必须重新运行程序才能查看结果
- [B] 可以使用 pstats 模块读取保存的统计文件并排序、过滤
- [C] 保存的文件是二进制格式，无法被任何工具读取
- [D] 保存的文件只能在相同的 Python 版本中查看，跨版本一定失败

**参考答案**：1

**解析**：pstats 可以读取分析工具保存的统计文件，并支持排序、过滤等操作。

### single_choice · None



- [A] 调用 cProfile.run() 并传入要执行的代码字符串或函数调用表达式
- [B] 调用 cProfile.start() 启动分析，再用 cProfile.stop() 停止
- [C] 调用 time.time() 在函数前后记录时间差
- [D] 调用 sys.settrace() 手动记录每一行执行时间

**参考答案**：0

**解析**：cProfile.run() 可以接收代码字符串或表达式并执行后输出统计；该模块没有 start/stop 这样的函数；time/sys.settrace 不是该分析模块的用法。

### single_choice · None



- [A] -o output_file
- [B] -f output_file
- [C] --save output_file
- [D] -w output_file

**参考答案**：0

**解析**：cProfile 命令行支持 -o 将统计结果写入文件；其他选项不是该工具用于保存结果到文件的参数。

### single_choice · None



- [A] 该函数自身平均每次耗时约 0.5 毫秒，子调用合计约 0.7 秒
- [B] 该函数自身平均每次耗时约 1.2 毫秒，子调用合计约 0.5 秒
- [C] 该函数自身总耗时约 1.2 秒，子调用总耗时约 0.5 秒
- [D] 该函数自身总耗时约 0.5 秒，但不包含任何子调用

**参考答案**：0

**解析**：tottime 是自身总耗时，0.5 秒除以 1000 次约为 0.5 毫秒；cumtime 包含子调用，因此子调用总耗时约为 1.2 - 0.5 = 0.7 秒。

### single_choice · None



- [A] 分析过程不会影响程序行为，可以完全真实地反映原始性能
- [B] 分析会带来额外开销，可能改变程序运行时间，应结合多次测量综合判断
- [C] 分析只会影响内存占用，不会影响运行时间
- [D] 分析结果中的时间单位一定是秒，且不受任何开销影响

**参考答案**：1

**解析**：性能分析本身有开销，会拖慢程序，因此结果用于相对比较和热点定位，不应被当作绝对精确时间。

### single_choice · None



- [A] 在代码中插入大量 print 语句输出时间
- [B] 使用性能分析工具对目标代码段进行统计并输出报告
- [C] 使用断言 assert 检查每行代码是否执行
- [D] 使用 try/except 捕获每一行可能出现的异常

**参考答案**：1

**解析**：性能分析工具可以系统性地统计函数调用次数与耗时，print、assert、异常捕获都不是性能分析手段。

### single_choice · None



- [A] cProfile 是纯 Python 实现，profile 是 C 实现
- [B] cProfile 是 C 实现，开销相对较小，通常优先使用
- [C] 两者完全等价，没有任何实现和性能差异
- [D] profile 只能分析函数，cProfile 只能分析模块

**参考答案**：1

**解析**：cProfile 基于 C 实现，开销较小，是推荐使用的分析器；profile 是纯 Python 实现，开销更大。

### single_choice · None



- [A] pstats
- [B] statistics
- [C] traceback
- [D] inspect

**参考答案**：0

**解析**：pstats 可以读取保存的统计文件并对数据进行排序、过滤等处理，常与分析工具配合使用。

### single_choice · None



- [A] import cProfile; cProfile.run('func()')
- [B] import cProfile; cProfile.analyze(func)
- [C] import cProfile; cProfile.profile(func)
- [D] import cProfile; cProfile.trace(func)

**参考答案**：0

**解析**：cProfile.run() 接受代码字符串并执行后输出统计；analyze、profile、trace 不是该模块提供的这些用法。

### single_choice · None



- [A] 在代码各段插入 print 打印当前时间并肉眼比较
- [B] 使用 cProfile 运行程序，再查看累计耗时（cumtime）与自身耗时（tottime）排序
- [C] 把程序跑两遍，比较总耗时差
- [D] 增加一个循环计数器统计执行次数

**参考答案**：1

**解析**：cProfile 是标准库中的确定性性能分析器，能给出每个函数的调用次数、tottime 与 cumtime，适合定位热点函数与代码行。print 打时间只能粗略分区，循环计数器只反映次数不反映耗时，跑两遍比较总耗时无法定位到函数级别。

### single_choice · None



- [A] 该函数自身计算量大，但被调用的次数很少
- [B] 该函数本身几乎不耗时，但它的时间主要花在调用其他被调函数上
- [C] 分析器把该函数的时间统计错了，应忽略 cumtime
- [D] 该函数被递归调用，分析器无法统计

**参考答案**：1

**解析**：tottime 是函数自身代码耗时（不含子调用），cumtime 是包含子调用的累计耗时。tottime 小、cumtime 大，说明耗时在它调用的下游函数里，应继续下钻。

### fill_blank · None



**参考答案**：["cProfile", "profile", "cprofile"]

**解析**：cProfile 是 CPython 标准库中推荐的确定性性能分析器，profile 是同功能但纯 Python 实现的旧模块。二者都能统计函数级调用次数与耗时。

### fill_blank · None



**参考答案**：["timeit", "Timeit"]

**解析**：timeit 模块通过重复运行代码片段并多次取最小值的方法，降低单次测量的噪声，是测量短小代码片段的标准工具。

### fill_blank · None



**参考答案**：["tottime", "tot time", "自身耗时"]

**解析**：cProfile/pstats 的输出中，tottime 是函数自身代码耗时，不含子调用；cumtime 是包含子调用的累计耗时。区分两者是阅读剖析结果的关键。

### code_reading · None



**参考答案**：它用 time.time() 单次测量 compute() 的耗时。time.time() 基于系统时钟，可能受系统时间调整影响，不单调；单次测量没有重复，容易受调度、GC、缓存预热等噪声影响，因此结果不稳定、不可靠。应改用 time.perf_counter()，并对可重复的调用用 timeit 做多次重复取最小值。

**解析**：关键点有二：一是计时器选择（应使用单调的 perf_counter 而非可能回拨的 time.time），二是单次测量缺少重复，无法压低噪声。

### code_reading · None



**参考答案**：inner 的 tottime 大、cumtime 与 tottime 接近（它几乎不做子调用）；outer 的 tottime 很小，但 cumtime 明显大于 tottime，因为它自身的循环代码很轻，绝大部分时间花在多次调用 inner 上。结论：outer 的耗时主要出现在被调用的 inner 中，热点在 inner。

**解析**：cumtime 包含子调用时间，tottime 不含。outer 自身只是循环调用 inner，所以自身耗时小、累计耗时长；inner 的实际计算在自身，故 tottime 高。

### code_reading · None



**参考答案**：写法 B 通常更快。写法 A 每次迭代都要调用 len、构造索引、再执行一次下标访问 items[i]，多出多次字节码操作；写法 B 直接迭代迭代器，只做一次取值并把元素绑定到 item，省去索引构造与下标访问，循环开销更小。

**解析**：直接迭代把「取下一个元素」交给迭代器协议，比手写索引 + 下标访问的字节码更少；在高频循环中这些节省会累积。

### code_reading · None



**参考答案**：它测量的是「在给定 parts 已构造好的前提下，两种拼接方式各执行 1000 次的总耗时」。把 parts 放在计时循环外，是为了让被测区间只包含目标操作（拼接）本身，不含输入构造开销，否则测量的就不只是拼接性能，结果会失真。

**解析**：性能测量的核心原则之一是隔离目标操作：准备数据应在计时区间外完成，否则会把准备开销计入，导致结论误导。

### scenario · None



**解析**：先粗后细、先测量后优化是定位性能问题的通用方法：用分段计时/日志粗测圈定大致范围；再用函数级剖析（如 cProfile）找出热点；对热点下钻到行级；定位后在受控环境做优化前后对比，确认收益，而不是凭猜测改代码。

### scenario · None



**解析**：单次 time.time() 测量不可靠：计时器可能受系统时间调整影响且不单调；单次结果易被调度、GC、缓存预热等噪声左右。应改用单调计时器、在相同受控环境下用 timeit 或多次重复取统计值，对优化前后做同条件对比，才能得出可信结论。

### scenario · None



**解析**：剖析器在每个函数进入/退出时触发回调，对被高频调用的小函数而言，回调开销占比可能远高于函数本身，从而放大其耗时并拖慢整体。可用抽样类分析器降低开销、缩小剖析范围、或在受控条件下对比启用/不启用剖析的结果来校正。

### single_choice · None



- [A] 两者都可用来统计每个函数的调用次数
- [B] timeit 适合测量小段代码的重复执行耗时，cProfile 适合知道程序里各函数的时间分布
- [C] timeit 只能用于多线程代码，cProfile 只能用于单线程
- [D] cProfile 的测量精度不如 timeit，所以定位热点时应优先用 timeit

**参考答案**：1

**解析**：timeit 通过多次重复运行取最小值来测量一段表达式/语句的执行时间，噪声小但粒度粗；cProfile 提供函数级/行级的时间与调用次数分布，用于定位热点。二者用途不同，不能互相替代。

### single_choice · None



- [A] 用 sys.setprofile 注册回调，记录进入/退出函数的时间
- [B] 在关键代码前后调用 time.perf_counter() 并记录差值
- [C] 用 dis 反汇编函数字节码
- [D] 用 sys.settrace 逐行跟踪所有代码

**参考答案**：1

**解析**：sys.settrace 逐行跟踪开销极大；sys.setprofile 仍是全函数级回调，开销高于手动打点；dis 只做静态反汇编。对少量关键路径用 perf_counter 手动计时开销最小、最可控。

### single_choice · None



- [A] 改用 while 循环手写索引
- [B] 改用 for x in data: total += x（直接迭代可迭代对象）
- [C] 把 data 转成字符串再解析
- [D] 给循环加 try/except 捕获异常

**参考答案**：1

**解析**：直接迭代省去每次下标访问与 range 取值，通常更快；while 手写索引开销更大；转字符串再解析是反向操作；try/except 与加速无关且可能掩盖错误。

### single_choice · None



- [A] 只调用一次并用 time.time() 记录
- [B] 用 timeit.repeat 多次重复，取各轮最小值
- [C] 用 time.clock() 取单次结果
- [D] 直接用 os.times() 的总和

**参考答案**：1

**解析**：timeit.repeat 会重复多轮并返回每轮耗时，取最小值可有效排除因调度、GC、缓存预热等引入的偶发高值噪声。单次测量和已废弃的 time.clock 都不适合。

### multi_choice · None



- [A] 分析器本身引入的额外开销，可能改变程序的时间分布
- [B] 分析结果受被分析程序运行环境（如解释器版本、机器负载）影响
- [C] 对短小函数而言，函数调用回调的开销占比可能被放大
- [D] 分析器会自动把 I/O 阻塞时间从统计中剔除，因此结果永远精确

**参考答案**：[0, 1, 2]

**解析**：分析器有额外开销，会扭曲时间分布；不同环境结果不可直接横向比较；对被频繁调用的小函数，回调开销占比高，可能失真。分析器不会自动剔除 I/O 阻塞，也不会让结果「永远精确」，故 D 错误。

### multi_choice · None



- [A] time.perf_counter() 提供单调、分辨率较高的计时器，适合测量耗时
- [B] time.time() 可能受系统时钟调整影响，不适合精确测量时间间隔
- [C] timeit 适合测量极短代码片段，会自动做多次重复以降低噪声
- [D] time.process_time() 统计的是挂钟时间，包含进程等待 I/O 的时间

**参考答案**：[0, 1, 2]

**解析**：perf_counter 单调且分辨率高，适合测间隔；time() 会受系统时钟调整影响；timeit 会自动重复以降低噪声。process_time 统计的是 CPU 时间，不含 I/O 等待，故 D 错误。

### multi_choice · None



- [A] 先用粗粒度计时（分段计时）圈定大致范围，再对热点区域细粒度剖析
- [B] 用 cProfile 得到函数级热点后，再逐步下钻到更细的函数或代码行
- [C] 在优化前后用相同环境、相同输入做对比基准测试，避免凭感觉判断
- [D] 直接用最快的算法重写全部代码，不需要先做任何测量

**参考答案**：[0, 1, 2]

**解析**：定位性能问题的通用流程是：粗测圈定范围 → 细测下钻热点 → 在受控环境下做前后对比。不测量就重写一切属于盲目优化，违反「先度量、后优化」原则。

### multi_choice · None



- [A] 在计时循环外预先构造好输入数据，循环内只做目标操作
- [B] 把本应统计在内的准备工作（数据构造、结果合并）排除在计时区间之外
- [C] 对同一代码用不同数据规模分别测量并混在一起比较结论
- [D] 测量时同时运行大量其他负载程序，导致机器整体繁忙

**参考答案**：[1, 2, 3]

**解析**：把准备工作排除在计时外会让结果偏乐观，属于选择性计时偏差；用不同数据规模混在一起比较结论不成立；机器被其他负载干扰会让结果偏慢且不可复现。选项 A 是合理做法（隔离目标操作），不是偏差来源。
