# s4u2l3 算法优先的性能优化 / py.perf.cache_lru —— 用 `functools.lru_cache` 给函数装上"记忆大脑"

> 来源 `content/lessons/s4u2l3.json`

## py.perf.algorithm_first

# py.perf.algorithm_first：算法优先的性能优化

## 一句话直觉

**在优化任何 Python 代码之前，先问一句：算法能不能换？** 因为算法复杂度（Algorithmic Complexity）的降维打击，往往比任何微优化（Micro-optimization）都强几个数量级——把 O(n²) 换成 O(n log n)，可能让程序从 1 小时变成 1 秒。

---

## 1. 为什么算法放在第一位

假设你要在 100 万条数据里查一个元素：

- 逐个遍历（线性查找，Linear Search）：平均 50 万次比较。
- 用集合（Set）或字典（Dict）做哈希查找（Hash Lookup）：约 1 次比较。

如果靠“优化循环写法”去提速，最多快 2~3 倍；而换算法，直接快 50 万倍。这就是为什么**算法优先**是性能工程的第一原则，而不是先调参数、换语言、上 C 扩展。

```python
import time

N = 200_000
data_list = list(range(N))
data_set = set(data_list)
target = N - 1  # 最坏情况：最后一个

# 线性查找 O(n)
t0 = time.perf_counter()
for _ in range(100):
    _ = target in data_list
t1 = time.perf_counter()
print(f"list 查找 100 次耗时: {t1 - t0:.4f}s")

# 哈希查找 O(1)
t0 = time.perf_counter()
for _ in range(100):
    _ = target in data_set
t1 = time.perf_counter()
print(f"set  查找 100 次耗时: {t1 - t0:.4f}s")
```

运行后你会发现耗时差了几个数量级。**结论：先选对数据结构（Data Structure），再谈代码写法。**

---

## 2. 先量复杂度，再动手

写代码前，用**大 O 记号（Big-O Notation）** 心算一遍输入规模 n 增长时会发生什么：

| 复杂度 | n=10 | n=1000 | n=10⁶ | 典型场景 |
|---|---|---|---|---|
| O(1) | 1 | 1 | 1 | 哈希查表 |
| O(log n) | 3 | 10 | 20 | 二分查找（Binary Search） |
| O(n) | 10 | 1000 | 10⁶ | 遍历一遍 |
| O(n log n) | 33 | 10⁴ | 2×10⁷ | 排序（Sorting） |
| O(n²) | 100 | 10⁶ | 10¹² | 双层循环 |

当 n=10⁶ 时，O(n²) 的 10¹² 次运算在普通机器上要几分钟甚至几小时；O(n log n) 只需零点几秒。**算法选择直接决定了问题能不能在可接受时间内解出。**

```python
def find_duplicates_naive(items):
    """O(n^2): 每个元素跟后面所有元素比一遍"""
    dups = []
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            if items[i] == items[j]:
                dups.append(items[i])
    return dups

def find_duplicates_fast(items):
    """O(n): 用 set 记录见过的元素"""
    seen, dups = set(), set()
    for x in items:
        if x in seen:
            dups.add(x)
        else:
            seen.add(x)
    return list(dups)

import random
random.seed(0)
arr = [random.randint(0, 1000) for _ in range(5000)]

import time
t0 = time.perf_counter(); find_duplicates_naive(arr); t1 = time.perf_counter()
t2 = time.perf_counter(); find_duplicates_fast(arr);  t3 = time.perf_counter()
print(f"naive O(n^2): {t1-t0:.4f}s")
print(f"fast  O(n):   {t3-t2:.4f}s")
```

---

## 3. 常见「算法升级」套路

拿到一段慢代码，先按下面的清单扫一遍，往往立刻有突破口：

1. **嵌套循环查存在性** → 换成 set/dict 哈希表。
2. **反复排序同一批数据** → 排一次，缓存副本。
3. **手动累加/拼接字符串** → 用 `list.append` + `''.join`（线性时间）。
4. **线性查找有序数组** → `bisect` 二分（O(log n)）。
5. **重复计算同一子问题** → 加缓存（Memoization）/ 动态规划（Dynamic Programming）。
6. **用 `in list` 做大量成员判断** → 换 `set`。

```python
import bisect

# 有序列表查元素：线性 vs 二分
sorted_arr = list(range(1_000_000))
target = 999_999

idx_linear = sorted_arr.index(target)                 # O(n)
idx_bisect = bisect.bisect_left(sorted_arr, target)   # O(log n)
print(idx_linear, idx_bisect)
```

---

## 4. 复杂度相同，再谈常数因子

只有当算法的**复杂度级别**一致时，微优化（比如局部变量、`for` 代替 `while`、避免属性查找）才有意义。顺序永远不能颠倒：

> **先算法 → 再数据结构 → 再实现细节 → 最后才是 C 扩展 / 多进程 / GPU。**

```python
import time

# 同一个 O(n) 算法的两种写法，差距是常数因子级别
N = 1_000_000
data = list(range(N))

# 写法 A：每次循环都做方法查找
t0 = time.perf_counter()
out = []
for x in data:
    out.append(x * 2)
t1 = time.perf_counter()

# 写法 B：列表推导式（List Comprehension），C 层驱动
t2 = time.perf_counter()
out = [x * 2 for x in data]
t3 = time.perf_counter()

print(f"for+append: {t1-t0:.4f}s")
print(f"comprehension: {t3-t2:.4f}s")
```

两种写法都是 O(n)，差距只体现在常数上；但相比第 1 节那种数量级的提升，这属于「调味料」而非「主菜」。

---

## 5. 工程落地的思考框架

面对真正的性能问题，用这套顺序思考：

1. **先测量，不猜**：用 `time.perf_counter`、`cProfile` 找出热点。
2. **判断瓶颈复杂度**：热点函数是大 O 里的哪一档？
3. **能不能降复杂度**：是否用了合适的数据结构？能否一次遍历完成？
4. **再考虑常量优化**：内置函数、切片、推导式、避免多余拷贝。
5. **最后才用重武器**：`numpy`、`numba`、Cython、多进程——它们只能压常数，压不了复杂度。

```python
import cProfile, pstats, io

def hot(n):
    total = 0
    for i in range(n):
        for j in range(n):
            total += i * j
    return total

# 用 cProfile 定位热点函数
pr = cProfile.Profile()
pr.enable()
hot(300)
pr.disable()

buf = io.StringIO()
pstats.Stats(pr, stream=buf).sort_stats('cumulative').print_stats(3)
print(buf.getvalue())
```

看到热点后，第一个问题永远是「它的复杂度能降吗？」，而不是「它能不能跑得更快一点？」。

```python
import time, random, bisect

# 场景：统计 10 万条日志里出现过的各种错误码，并对有序数组做快速查找
random.seed(42)
logs = [random.randint(0, 5000) for _ in range(100_000)]

# --- 反面教材：O(n^2) 判断重复 ---
def dedup_slow(items):
    result = []
    for i, x in enumerate(items):
        if x not in result:      # 每次都在 list 里做 O(n) 查找
            result.append(x)
    return result

# --- 正确做法：O(n) 用 set 做哈希 ---
def dedup_fast(items):
    return list(dict.fromkeys(items))  # 保序去重，平均 O(n)

t0 = time.perf_counter(); slow = dedup_slow(logs[:5000]); t1 = time.perf_counter()
t2 = time.perf_counter(); fast = dedup_fast(logs);        t3 = time.perf_counter()
print(f"O(n^2) 5000 条: {t1-t0:.4f}s -> {len(slow)} 个唯一值")
print(f"O(n)  100000 条: {t3-t2:.4f}s -> {len(fast)} 个唯一值")

# --- 有序数组用二分代替线性查找 ---
sorted_codes = sorted(set(logs))
target = sorted_codes[-1]
print("linear index:", sorted_codes.index(target))
print("bisect index:", bisect.bisect_left(sorted_codes, target))
```

## py.perf.cache_lru

# py.perf.cache_lru —— 用 `functools.lru_cache` 给函数装上"记忆大脑"

> 一句话直觉：**当一个函数的输入 → 输出是稳定的映射时，把结果记在小本本上，下次遇到相同输入直接抄答案，而不是重新算一遍。**

这个知识点属于 Python 性能优化（performance optimization）的起点，几乎所有对纯函数（pure function）做加速的场景，第一反应都应该是 `lru_cache`。

---

## 1. 为什么需要缓存：从递归的痛开始

考虑最经典的 Fibonacci 数列：

```python
def fib(n):
    if n < 2:
        return n
    return fib(n - 1) + fib(n - 2)
```

`fib(30)` 看上去只有 30，但实际会调用上百万次——因为 `fib(28)`、`fib(27)` 被反复重算。这就是**重复计算（redundant computation）**。

**核心结论：如果同一个函数用相同参数被反复调用，结果又不会变，那就没必要算第二次。**

---

## 2. 手写一个"缓存"，理解它的本质

缓存（cache）本质就是一个字典：**参数作 key，返回值作 value**。

```python
cache = {}

def fib_memo(n):
    if n in cache:
        return cache[n]      # 命中缓存：直接返回
    if n < 2:
        result = n
    else:
        result = fib_memo(n - 1) + fib_memo(n - 2)
    cache[n] = result        # 写入缓存
    return result
```

`fib_memo(30)` 现在是毫秒级。这就是**记忆化（memoization）**——缓存技术里最常用的一种形式。

---

## 3. 标准库方案：`functools.lru_cache`

Python 从 3.2 起，把上面的模式封装成了一个装饰器（decorator）：`functools.lru_cache`。

- **LRU** = Least Recently Used（最近最少使用）。当缓存容量满时，丢弃"最久没被访问"的那一项。
- 它自动处理 key 的构造、线程安全（thread-safe）、命中率统计。

```python
from functools import lru_cache

@lru_cache(maxsize=None)          # None 表示不限制容量
 def fib(n):
    if n < 2:
        return n
    return fib(n - 1) + fib(n - 2)
```

注意 `maxsize=None` 时缓存不会淘汰任何条目，等价于无限记忆化（unbounded memoization）。

---

## 4. 用 `cache_info` / `cache_clear` 观察和控制

`lru_cache` 给被装饰的函数挂上了两个实用方法：

- `cache_info()` → 返回 `hits`、`misses`、`maxsize`、`currsize`
- `cache_clear()` → 清空缓存

```python
@lru_cache(maxsize=128)
def add(a, b):
    return a + b

add(1, 2)
add(1, 2)   # 命中
add(3, 4)
print(add.cache_info())   # CacheInfo(hits=1, misses=2, maxsize=128, currsize=2)
add.cache_clear()
print(add.cache_info())   # currsize 归零
```

`cache_info` 是判断"加缓存有没有用"的第一手证据：**如果 hits 一直上不去，说明缓存是无效负担。**

---

## 5. 什么时候适合用、什么时候会踩坑

**适合用的三个条件：**
1. **纯函数**：输出只依赖输入，不依赖外部可变状态。
2. **调用重复率高**：相同参数被反复调用。
3. **单次计算成本可观**：缓存查询的代价明显低于重算。

**不适合甚至有害：**
- 函数有副作用（写文件、打日志、发请求）——缓存会"跳过"副作用。
- 参数是不可哈希（unhashable）对象，比如 `list`、`dict`——会直接报 `TypeError`。
- 参数空间巨大且几乎不重复——缓存只是白占内存。

```python
@lru_cache(maxsize=32)
def f(x):
    return x * 2

f([1, 2, 3])   # TypeError: unhashable type: 'list'
```

**工程建议：**线上服务里给 `maxsize` 一个明确上限（比如 128、1024），防止长期运行的内存泄露（memory leak）。Python 3.9 还提供了无参版本 `@cache`，等价于 `@lru_cache(maxsize=None)`，见 PEP 584 / bpo-39245。

---

## 6. 动手练习

写一个带缓存的"耗时的平方根计算器"，并验证缓存确实生效：

1. 自定义一个 `slow_sqrt(x)` 函数：内部用 `time.sleep(0.5)` 模拟耗时，返回 `x ** 0.5`。
2. 用 `@lru_cache(maxsize=32)` 装饰它。
3. 连续调用同一个值 3 次（比如 `slow_sqrt(2)`），计时，观察第 2、3 次是否几乎瞬时完成。
4. 打印 `slow_sqrt.cache_info()`，解释 `hits` 和 `misses` 的数值。
5. 把 `maxsize` 改成 1，再连续调用 `slow_sqrt(1)`、`slow_sqrt(2)`、`slow_sqrt(1)`，观察第三次调用是否又"变慢"了——并说明原因。

**提交要求**：贴出代码、`cache_info` 输出，以及第 5 步里你对"第三次调用慢"的解释。

```python
import time
from functools import lru_cache


@lru_cache(maxsize=128)
def slow_sqrt(x: float) -> float:
    """模拟一个昂贵的计算：额外 0.5 秒。"""
    time.sleep(0.5)
    return x ** 0.5


if __name__ == "__main__":
    # 第一次调用：miss，会真的 sleep 0.5 秒
    t0 = time.perf_counter()
    print(slow_sqrt(2))
    print(f"1st call: {time.perf_counter() - t0:.3f}s")

    # 第二次调用同一参数：hit，几乎瞬时
    t0 = time.perf_counter()
    print(slow_sqrt(2))
    print(f"2nd call: {time.perf_counter() - t0:.6f}s")

    # 查看命中统计
    print(slow_sqrt.cache_info())

    # 清空后 currsize 归零
    slow_sqrt.cache_clear()
    print(slow_sqrt.cache_info())
```


---

## 本课题目

### single_choice · None



- [A] 使用循环逐个累加，并尝试用 C 扩展加速这个循环
- [B] 使用公式 n*(n+1)//2 直接计算
- [C] 使用递归并开启 PyPy 的 JIT 来加速
- [D] 使用多线程把累加任务分配给多个线程

**参考答案**：1

**解析**：该问题的数学结构允许 O(1) 公式求解，直接改变了算法复杂度，收益远大于在 O(n) 循环上做微优化。其余选项都是在既有算法上做常数级加速。

### single_choice · None



- [A] 双重循环两两比较，返回是否发现相等元素
- [B] 先对列表排序，再相邻比较
- [C] 使用 set 记录已见元素，遍历一次判断是否有重复
- [D] 对每个元素调用 list.count() 判断其出现次数是否大于 1

**参考答案**：2

**解析**：使用 set 遍历一次是 O(n)。双重循环和逐个 count 都是 O(n²)，排序是 O(n log n)，均不如集合方案。

### single_choice · None



- [A] 直接使用 set(list)，接受顺序丢失
- [B] 使用 dict.fromkeys(list) 或借助集合记录已见元素来顺序去重
- [C] 对列表排序后去掉相邻重复
- [D] 使用双重循环逐一检查重复

**参考答案**：1

**解析**：利用字典有序特性或「已见集合」可在近似线性时间内去重并保留顺序。排序会改变顺序，双重循环为 O(n²)。

### single_choice · None



- [A] Dijkstra 算法（使用优先队列）
- [B] 广度优先搜索（BFS）
- [C] 深度优先搜索（DFS）并记录路径
- [D] Floyd-Warshall 算法

**参考答案**：1

**解析**：边权均为 1 时 BFS 即为 O(V+E) 的最短路径算法；Dijkstra 在此场景下做的是多余工作，BFS 更简洁也更高效。

### single_choice · None



- [A] 先用最直观的算法实现，再用性能分析工具优化热点代码
- [B] 先评估问题规模与可接受的复杂度，选择合适算法后再考虑常数优化
- [C] 使用更快语言重写所有模块以保证速度
- [D] 尽可能地为所有函数都加上缓存

**参考答案**：1

**解析**：算法优先强调先选择合适的算法与数据结构，再在必要时做常数优化。仅仅换语言或加缓存可能无法改变复杂度量级。

### single_choice · None



- [A] 立刻把循环体里的每一行都做微优化
- [B] 用性能分析工具定位耗时部分，并评估其算法复杂度是否合理
- [C] 把 Python 代码整体翻译成 C 语言
- [D] 给函数加上更多的日志输出

**参考答案**：1

**解析**：先定位瓶颈和评估算法复杂度，才能判断该改算法还是做常数优化。直接微优化或换语言可能没有抓住主要矛盾。

### single_choice · None



- [A] 把列表遍历中的属性访问改为局部变量
- [B] 把 O(n²) 的算法替换为 O(n log n) 的算法
- [C] 给热点函数加上 @staticmethod
- [D] 把 print 输出重定向到 /dev/null

**参考答案**：1

**解析**：改变复杂度量级才是数量级提升；其余都是常数级优化，不改变渐进复杂度。

### single_choice · None



- [A] 对 10⁶ 条数据做两两比较查找重复
- [B] 对少量（比如 10 条）数据做简单的顺序查找
- [C] 在有序大数组中做元素查找
- [D] 对大量文本做频繁的子串搜索

**参考答案**：1

**解析**：数据规模很小时，简单算法与高效算法的差距通常微不足道，此时优化算法收益有限；其余场景规模大，算法选择影响显著。

### single_choice · None



- [A] 只要常数因子足够小，任何算法都能在任意规模下胜过 O(log n) 的算法
- [B] 大 O 表示法描述的是增长趋势，低阶算法最终会胜过高阶算法
- [C] 常数因子与复杂度无关，因此完全不需要考虑
- [D] 所有 O(n) 算法在相同规模下运行时间都相同

**参考答案**：1

**解析**：大 O 描述渐进增长；对于足够大的 n，低阶算法终将胜过更高阶的算法，尽管小规模时可能相反。常数因子实际中仍有影响但不会改变趋势。

### single_choice · None



- [A] 对整个列表排序后取前 k 个
- [B] 使用大小受限的最小堆维护当前最大的 k 个元素
- [C] 使用双重循环逐一比较所有元素
- [D] 对列表做多次线性扫描，每次找最大并移除

**参考答案**：1

**解析**：维护大小为 k 的堆为 O(n log k)，优于整体排序的 O(n log n)，更优于 O(n²) 或多次扫描。

### single_choice · None



- [A] 把匹配函数用汇编重写
- [B] 改用诸如 KMP 或 Boyer-Moore 等线性或近线性复杂度的算法
- [C] 把待匹配字符串先转换成一个大的整数再比较
- [D] 给匹配函数加上缓存并限制最大长度

**参考答案**：1

**解析**：选用更优的字符串匹配算法可降低最坏情况复杂度，是算法层面的改进。其余做法要么是常数优化，要么不改变最坏复杂度。

### single_choice · None



- [A] O(log n)
- [B] O(n)
- [C] O(n²)
- [D] O(1)

**参考答案**：2

**解析**：输入规模翻倍、时间变为约 4 倍，符合 O(n²) 的增长；O(n) 应约翻倍，O(log n) 增长更慢。

### single_choice · None



- [A] 无论 n 多大，算法甲都更快
- [B] 无论 n 多大，算法乙都更快
- [C] 存在某个 n 之后，算法乙会比算法甲慢
- [D] 两者运行时间始终相等

**参考答案**：2

**解析**：当 n 超过 100000 左右时，n²/100 会超过 1000n，即乙会变慢。常数因子只影响交叉点位置，不改变增长趋势的结论。

### single_choice · None



- [A] 把列表换成元组以减少内存开销
- [B] 把列表预先转换成集合或字典来支持近似 O(1) 的成员查询
- [C] 在查询前把列表复制一份以避免修改原数据
- [D] 使用 for 循环加 break 来提前退出查询

**参考答案**：1

**解析**：把线性查找结构换成哈希结构使单次查询从 O(n) 降到平均 O(1)，这是算法/数据结构层面的改进。其余为微小优化。

### single_choice · None



- [A] 对第一个列表每个元素用 in 检查是否在第二个列表中
- [B] 对两个列表排序后用双指针求交集
- [C] 用两层 for 循环逐一比较
- [D] 把两个列表都转换成集合后求交集

**参考答案**：3

**解析**：集合求交集平均为 O(n)。排序加双指针为 O(n log n)，两个线性扫描方案为 O(n²)。

### single_choice · None



- [A] 在循环中用 += 逐个拼接
- [B] 先把片段收集到列表中，最后用 join 一次性拼接
- [C] 每拼接一次就把结果复制到一个新变量以「保留备份」
- [D] 使用多个线程分别拼接再合并

**参考答案**：1

**解析**：循环中反复 += 在很多实现下会造成重复复制，整体代价偏二次；先收集后用 join 一次完成，线性代价。

### single_choice · None



- [A] 把计算常量表的循环改用 while 代替 for
- [B] 把常量表移到模块级或使用缓存，使其只计算一次
- [C] 给函数加上类型注解
- [D] 把常量表计算的结果打印出来以便检查

**参考答案**：1

**解析**：避免重复计算属于算法/设计层面的改进，消除了冗余工作。其余选项不改变重复计算的次数。

### single_choice · None



- [A] O(n)
- [B] O(n log n)
- [C] O(2^n)
- [D] O(1)

**参考答案**：2

**解析**：朴素递归会重复求解大量子问题，时间复杂度约为指数级 O(2^n)。加上记忆化后可降到 O(n)。

### single_choice · None



- [A] 顺序遍历整个数组
- [B] 二分查找
- [C] 把数组转换成集合后再查找
- [D] 随机打乱数组后再顺序查找

**参考答案**：1

**解析**：有序数组适合二分查找，复杂度 O(log n)，明显优于顺序遍历的 O(n)。

### single_choice · None



- [A] 购买更快的硬盘来缩短读写时间
- [B] 把数据的读写合并为一次遍历完成
- [C] 把文件打开模式从文本改为二进制
- [D] 增加操作系统的文件缓存大小

**参考答案**：1

**解析**：将两次遍历合并为一次遍历减少了算法层面的工作量，是数量级上的改进，而不是硬件层面的等比例加速。

### single_choice · None



- [A] 缓存键由函数的位置参数和关键字参数共同构成，因此调用时参数写法不同可能命中不同缓存
- [B] 缓存键只由位置参数构成，关键字参数会被忽略
- [C] 缓存键只由函数名构成，同一函数的所有调用都共享一个缓存
- [D] 缓存键由参数和返回值共同构成

**参考答案**：0

**解析**：lru_cache 以调用的实参（位置参数与关键字参数）作为键。因此 f(1, 2) 与 f(a=1, b=2) 可能被视为不同键，导致重复计算。返回值为缓存的值，不参与键的构成。

### single_choice · None



- [A] 整数
- [B] 字符串
- [C] 列表
- [D] 元组

**参考答案**：2

**解析**：lru_cache 内部将参数作为字典的键，因此参数必须是可哈希（hashable）的对象。list 不可哈希，会抛出 TypeError。int、str、tuple（其元素也可哈希时）都是可哈希的。

### multi_choice · None



- [A] maxsize=None 时缓存条目无上限，可能持续增长
- [B] 缓存会持有键和值的引用，可能延长相关对象寿命
- [C] 在实例方法上使用且 maxsize=None 可能使实例无法被回收
- [D] 缓存一定不会造成内存问题，因为 lru_cache 会自动适配

**参考答案**：[0, 1, 2]

**解析**：A、B、C 均正确。无上限缓存、引用保持、实例方法导致的实例泄露都是真实风险。D 错误：lru_cache 不会自动感知内存压力，maxsize 需要合理设置。

### multi_choice · None



- [A] lru_cache 本身不感知函数依赖的外部数据是否变化
- [B] 可以通过 cache_clear() 手动使整个缓存失效
- [C] 当 maxsize 有限时，新条目可能挤掉旧条目，这是一种隐式失效
- [D] lru_cache 会自动检测被缓存函数源代码是否改变并重新计算

**参考答案**：[0, 1, 2]

**解析**：lru_cache 只按参数键匹配，不监控外部数据或源码变化。手动清理与达到 maxsize 后淘汰都是缓存失效的来源。D 错误：源码改动不会自动触发重算（需重启或清理）。

### fill_blank · None



**参考答案**：["cache_info", "cache_info()"]

**解析**：被装饰的函数会获得 cache_info() 方法，返回包含 hits、misses、maxsize、currsize 的命名元组。

### fill_blank · None



**参考答案**：["128", "一百二十八"]

**解析**：lru_cache 默认 maxsize=128，即最多缓存 128 个不同的参数组合，超出后按 LRU 策略淘汰。

### code_reading · None



**参考答案**：输出为先打印一次 computing，然后打印 1 1。因为 add(1, 2) 首次计算未命中（miss），add(1, 2) 第二次命中（hit）；add(2, 1) 的参数与 (1, 2) 不同，属于新的键，再次未命中并打印 computing。故 hits=1，misses=2。

**解析**：缓存键由参数组合构成，(1,2) 与 (2,1) 是不同键。因此 computing 打印两次，最终 hits 为 1、misses 为 2。注意题干最后一行打印的是 hits 与 misses。若只统计一次调用链，结果应表述为 computing 出现两次、hits=1、misses=2。

### code_reading · None



**参考答案**：会抛出 TypeError，提示 unhashable type: 'list'。因为 lru_cache 需要把参数当作缓存字典的键，而列表是不可哈希的，无法用作键。

**解析**：lru_cache 通过参数构成键来查表，参数必须可哈希。list（以及 dict、set）不可哈希，传入时会在查表阶段报 TypeError。解决办法是传入 tuple 或在函数内部转换。

### code_reading · None



**参考答案**：第一次输出 5，第二次输出 7（或理解为缓存中存有从 fib(0) 到 fib(5) 共 6~7 个条目，取决于计数细节；标准解释是 fib(5)=5，currsize 记录缓存条目数）。核心是递归子问题被缓存复用，使原本指数级复杂度降为线性。

**解析**：lru_cache 让递归中的重复子问题（如 fib(2)、fib(3)）只计算一次。fib(5)=5。currsize 表示当前缓存条目数，随不同 n 的取值累加。关键是理解缓存把重叠子问题复用，从而将时间复杂从 O(2^n) 降至 O(n)。

### scenario · None



**参考答案**：该方案存在风险。parse_config(text) 的参数 text 是字符串，可哈希，技术上可以缓存；但配置文本会随时间变化，而 lru_cache 不感知外部数据变化，可能返回过期结果。若一定要缓存，需要在文本变化时调用 cache_clear() 使缓存失效，或改用带过期时间(TTL)的缓存（如 cachetools 的 TTLCache），或直接不缓存、改为在解析层面优化。

**解析**：lru_cache 只按参数键匹配并永久保留（直到被淘汰或手动清理），不监控文件/外部状态变化。此场景的关键不是可哈希性（字符串可哈希），而是缓存正确性：输入相同但外部状态已变，缓存值会过期。应通过手动清理、TTL 缓存或不缓存来保证正确性。

### scenario · None



**参考答案**：最可能的原因有两方面：一是 maxsize=None 使缓存条目无上限，查询字符串多样时不断累积；二是在实例方法上使用时 self 会成为缓存键的一部分，缓存强引用实例，导致实例无法被回收。改进方案包括：把 maxsize 设为有限值让 LRU 自动淘汰；避免在实例方法上直接装饰（改为在函数级或类级缓存，或使用 weakref 相关方案）；必要时定期调用 cache_clear()。

**解析**：maxsize=None 表示永不主动淘汰，配合大量不同输入会造成缓存持续增长。实例方法上的 lru_cache 会把 self 计入键并强引用实例，增大内存泄露风险。限定 maxsize、调整装饰位置、手动清理是常见缓解手段。

### scenario · None



**参考答案**：报错原因是 list 不可哈希，而 lru_cache 需要把参数当作缓存键，因此抛出 TypeError: unhashable type: 'list'。改造思路：一是在调用缓存函数前把 list 转成 tuple 再传入（自建一个包装函数或在内部转换），因为 tuple 可哈希；二是给函数增加一层可哈希参数的薄封装，把原始 list 转为 tuple 后调用被缓存的内部函数，对外仍暴露原接口。

**解析**：lru_cache 基于哈希查表，键必须可哈希。list 不可哈希，tuple（元素可哈希时）可以。常见做法是用 tuple 替代 list 作为缓存边界，或在缓存层与业务层之间加适配层。

### single_choice · None



- [A] 前者不限制缓存条目数，后者默认 maxsize 为 128
- [B] 前者默认 maxsize 为 128，后者不限制
- [C] 两者完全等价，没有区别
- [D] 前者只能用于方法，后者只能用于函数

**参考答案**：0

**解析**：functools.lru_cache 的默认 maxsize 是 128。显式传 maxsize=None 表示缓存无上限，会一直增长，可能导致内存问题。

### single_choice · None



- [A] 调用 cache_info() 可以查看 hits、misses、maxsize、currsize 等信息
- [B] 缓存统计信息无法获取，只能靠外部计时推断
- [C] cache_info() 返回的是每个被缓存参数的列表
- [D] hits 表示未命中的次数

**参考答案**：0

**解析**：被 lru_cache 装饰的函数带有 cache_info() 方法，返回命名元组 CacheInfo(hits, misses, maxsize, currsize)。hits 是命中次数，misses 是未命中次数。

### single_choice · None



- [A] 淘汰最久未被访问的条目，为新条目腾出空间
- [B] 淘汰最近刚被访问的条目
- [C] 随机淘汰一个条目
- [D] 直接拒绝新条目，不再缓存

**参考答案**：0

**解析**：LRU 即 Least Recently Used，优先淘汰最久未被访问的条目。这正是它区别于 FIFO 等策略的地方。

### single_choice · None



- [A] 对一个输入规模有限、纯函数式的递归计算（如斐波那契数列）进行加速
- [B] 对一个会读写数据库且结果随时间变化的函数进行缓存
- [C] 对一个依赖全局可变状态的函数进行缓存
- [D] 对一个参数是大型 numpy 数组且频繁变化的函数进行缓存

**参考答案**：0

**解析**：lru_cache 适合纯函数：相同输入总是产生相同输出，且输入可哈希。依赖外部可变状态、结果随时间变化的函数缓存后可能返回过期数据；不可哈希参数无法作为键。

### single_choice · None



- [A] self 会成为缓存键的一部分，导致每个实例都持有独立缓存，且实例无法被垃圾回收（内存泄漏风险）
- [B] 装饰器无法作用于实例方法，会直接报语法错误
- [C] lru_cache 会自动忽略 self，因此没有任何问题
- [D] 只有把 maxsize 设为 None 才能用于方法

**参考答案**：0

**解析**：实例方法被装饰后，self 作为参数进入缓存键。这会导致缓存按实例隔离（可能不符合预期），并且缓存会强引用 self，使实例无法被回收，除非调用 cache_clear()。常见做法是把缓存放到类级别或使用其他方式。

### single_choice · None



- [A] 清空该函数当前所有缓存条目，并重置统计信息
- [B] 只清除最近一次调用产生的缓存
- [C] 禁用该函数的缓存功能，之后调用不再缓存
- [D] 只是把 hits 和 misses 计数归零，缓存条目保留

**参考答案**：0

**解析**：cache_clear() 会清空缓存中的所有条目并重置 hits/misses 等统计。它不会永久禁用缓存，后续调用仍会正常缓存。

### multi_choice · None



- [A] 被装饰的函数必须接受可哈希的参数
- [B] 默认 maxsize 为 128
- [C] 它为函数的返回值建立缓存，相同参数再次调用时可能直接返回缓存值
- [D] 它适合所有函数，包括有副作用的函数
- [E] cache_info() 可以查看命中与未命中次数

**参考答案**：[0, 1, 2, 4]

**解析**：A、B、C、E 均正确。D 错误：对有副作用的函数使用缓存会导致副作用只执行一次或被跳过，通常不符合预期。

### multi_choice · None



- [A] 函数参数包含不可哈希的对象（如 list、dict）
- [B] 函数读取了随时间变化的文件或网络数据
- [C] 函数的输入空间非常大且几乎不重复
- [D] 函数是纯函数且输入空间有限
- [E] 函数内部依赖了未被声明为参数的外部可变全局变量

**参考答案**：[0, 1, 2, 4]

**解析**：A 会直接报错；B 会返回过期缓存；C 会持续占用内存且几乎无命中收益；E 因外部状态变化而缓存结果失准。D 恰恰是 lru_cache 的理想场景，不是问题。
