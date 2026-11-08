# s4u2l4 向量化运算：NumPy Vectorization / Cython 入门：让 Python 代码跑出 C 的速度 / 40 分钟教学讲义：`py.perf.numba`

> 来源 `content/lessons/s4u2l4.json`

## py.perf.numpy_vector

# 向量化运算：NumPy Vectorization

> **一句话直觉**：当你要对成千上万个数据做同一种算术运算时，别用 Python 循环一个个算，而是让 NumPy 一次性把整块数组算完——快几十到几百倍。

---

## 1. 为什么需要向量化（Vectorization）？

Python 是解释型语言，`for` 循环的每一次迭代都要做类型检查、字节码分派，开销很大。NumPy 的数组（`ndarray`，N-dimensional array）底层用 C 实现连续内存块，配合 SIMD 指令（Single Instruction, Multiple Data）一次处理多个数据，因此同样的计算量，向量化写法比纯 Python 循环快得多。

```python
import numpy as np, time

n = 1_000_000
a = list(range(n))
b = list(range(n))

# 纯 Python 循环
start = time.perf_counter()
c = [a[i] + b[i] for i in range(n)]
print('Python loop:', round(time.perf_counter() - start, 4), 's')

# NumPy 向量化
na = np.arange(n)
nb = np.arange(n)
start = time.perf_counter()
nc = na + nb
print('NumPy vector:', round(time.perf_counter() - start, 4), 's')
```

典型结果：Python 循环约 0.05~0.1 秒，NumPy 约 0.002 秒，差 20~50 倍。

---

## 2. 核心概念：ndarray 与“形状”

NumPy 的主角是 `ndarray`，它有三个关键属性：

- `dtype`：元素类型（如 `int64`, `float32`）
- `shape`：每个维度的长度，例如 `(3, 4)`
- `ndim`：维度数量

```python
import numpy as np

x = np.array([[1, 2, 3], [4, 5, 6]])
print(x.shape)   # (2, 3)
print(x.ndim)    # 2
print(x.dtype)   # int64
```

**关键点**：NumPy 中所有元素类型必须一致，这让它会用整齐的内存布局，从而能向量化。

---

## 3. 向量化的三种写法

### 3.1 逐元素运算符

`+ - * / **` 等运算符作用于数组时，是对每个元素分别运算。

```python
x = np.array([1, 2, 3, 4])
y = np.array([10, 20, 30, 40])

print(x + y)     # [11 22 33 44]
print(x * 2)     # [2 4 6 8]     广播：标量自动作用于每个元素
print(x ** 2)    # [ 1  4  9 16]
```

### 3.2 通用函数（ufunc，universal function）

NumPy 提供大量作用于整块数组的数学函数，例如 `np.sqrt`, `np.exp`, `np.log`, `np.sin`，它们都自动向量化。

```python
a = np.array([1.0, 4.0, 9.0, 16.0])
print(np.sqrt(a))       # [1. 2. 3. 4.]
print(np.log(a))        # 自然对数
```

### 3.3 广播（Broadcasting）

不同形状的数组在一定规则下可以“自动对齐”参与运算。最常见的：标量与数组、`(N,)` 与 `(1,)` 或 `(N, 1)`。

```python
m = np.array([[1, 2, 3],
              [4, 5, 6]])           # shape (2, 3)
row_mean = m.mean(axis=1, keepdims=True)  # shape (2, 1)
centered = m - row_mean            # (2,3) - (2,1) → (2,3)
print(centered)
```

---

## 4. 条件筛选也要向量化

用布尔掩码（Boolean mask）替代循环里的 if。

```python
scores = np.array([45, 88, 67, 92, 55, 73])
mask = scores >= 60                # [False True True True False True]
print(scores[mask])                # [88 67 92 73]

# 也可以用 np.where
passed  = scores[scores >= 60]
failed  = scores[scores <  60]
print(passed, failed)
```

`np.where(condition, A, B)` 等价于三目运算的向量化版本：

```python
labels = np.where(scores >= 60, 'pass', 'fail')
print(labels)
```

---

## 5. 归约（Reduction）与轴（axis）

求和、均值、最大/最小值会“压扁”某个维度。`axis` 参数指定压扁哪一维。

```python
m = np.array([[1, 2, 3],
              [4, 5, 6]])

print(m.sum())            # 21，全部相加
print(m.sum(axis=0))      # [5 7 9]   按列压扁（每列的和）
print(m.sum(axis=1))      # [6 15]    按行压扁（每行的和）
```

**记忆技巧**：`axis=k` 表示“把第 k 维消掉”。

---

## 6. 实战模板：一份数据流水线

任务：对一批人的身高（cm）和体重（kg）计算 BMI，然后分类。

```python
import numpy as np

heights = np.array([170, 165, 180, 155, 175], dtype=np.float64)
weights = np.array([ 65,  55,  80,  45,  70], dtype=np.float64)

bmi = weights / (heights / 100.0) ** 2

labels = np.where(bmi < 18.5, 'underweight',
         np.where(bmi < 25.0, 'normal', 'overweight'))

print(np.round(bmi, 2))
print(labels)
```

整段代码没有 for 循环，但处理了 5 个人；换成 5 百万人依然是一行。这就是向量化的工程级价值。

---

## 小结

| 场景 | 不要这样写 | 应该这样写 |
| --- | --- | --- |
| 逐元素加 | `[a[i]+b[i] for i ...]` | `x + y` |
| 判断满足条件 | Python `if` 循环 | `x >= 60`，布尔掩码 |
| 求和/均值 | 手写循环累加 | `x.sum()`, `x.mean(axis=...)` |
| 分段赋值 | `for i: if...` | `np.where(cond, A, B)` |

核心心法：**先想数组操作，再想单个元素**。看到 for 循环处理数值数组，先问一句“这一步能不能向量化？”

```python
# 可运行示例：向量化筛选 + 计算
import numpy as np

# 1. 生成模拟数据
rng = np.random.default_rng(seed=42)          # 固定种子，便于复现
n = 1_000_000
heights = rng.normal(170, 8, n)               # 身高 ~ N(170, 8) cm
weights = rng.normal(65, 12, n)               # 体重 ~ N(65, 12) kg

# 2. 向量化计算 BMI（高度单位转米）
bmi = weights / (heights / 100.0) ** 2

# 3. 向量化筛选与统计
normal_mask = (bmi >= 18.5) & (bmi < 25.0)    # 布尔掩码，& 表示逻辑与
print('样本数:', n)
print('BMI 均值:', round(float(bmi.mean()), 2))
print('BMI 标准差:', round(float(bmi.std()), 2))
print('正常体重比例:', round(float(normal_mask.mean()), 4))

# 4. 向量化分段标签
labels = np.where(bmi < 18.5, 'underweight',
         np.where(bmi < 25.0, 'normal', 'overweight'))
for name in ('underweight', 'normal', 'overweight'):
    print(f'{name:>12}: {int((labels == name).sum())}')
```

## py.perf.cython

# Cython 入门：让 Python 代码跑出 C 的速度

> **一句话直觉**：当你的 Python 代码在循环里慢得让人抓狂时，Cython 能让你几乎不改几行代码，就把速度提升几十倍——它把 Python 翻译成 C，再编译成机器码。

---

## 0. 为什么需要 Cython？

Python 写起来爽，是因为它是**动态类型（dynamic typing）**语言：变量类型在运行时才确定，解释器（interpreter）每执行一行都要做大量类型检查、对象装箱拆卸。代价就是——纯 Python 计算密集型代码（比如大循环、数值积分、嵌套 list 操作）往往比 C 慢 50~200 倍。

Cython 的思路很朴素：**让你用类似 Python 的语法，加上可选的静态类型声明（static type declaration），自动生成 C 源码，再编译成 Python 扩展模块（extension module）**。运行速度可接近原生 C。

它跟你熟悉的工具不同：
- 不像 Numba 只做 JIT（即时编译）；Cython 是**提前编译（AOT, ahead-of-time）**。
- 不像 C 扩展那样要手写 PyObject 引用计数；Cython 帮你自动管理。
- 可保留为 `.pyx` 文件，也可使用纯 Python 模式 `%%cython` 在 notebook 里临时加速。

学习收益：一旦你掌握了 Cython，**Python 性能瓶颈**里“解释器开销”这一类问题就有了一把直接可用的刀。

---

## 1. 第一个例子：先看纯 Python 有多慢

我们写一个经典的累加求和，对比一下耗时基线。

```python
# baseline.py —— 纯 Python 慢速基线
import time

def sum_py(n: int) -> int:
    s = 0
    for i in range(n):
        s += i
    return s

t0 = time.perf_counter()
print(sum_py(100_000_000))       # 1e8 次循环
t1 = time.perf_counter()
print(f"python: {t1 - t0:.3f}s")
```

在一般笔记本上，这段大约 5~8 秒。这就是我们后面要“干掉”的时间。

---

## 2. 把它编译成 C：`pyx` 文件与 `cythonize`

Cython 源码文件后缀是 `.pyx`。语法几乎是 Python，但可加 `cdef` 来声明 C 类型。

**慢速版 `.pyx`（先和 Python 逻辑一致）**

```cython
# sum_slow.pyx
def sum_cy_slow(int n):
    cdef long s = 0
    cdef int i
    for i in range(n):
        s += i
    return s
```

**再写 `setup.py` 编译**

```python
# setup.py
from setuptools import setup
from Cython.Build import cythonize

setup(
    ext_modules=cythonize("sum_slow.pyx", language_level="3"),
)
```

命令行执行：

```bash
pip install cython
python setup.py build_ext --inplace
```

编译产物 `sum_slow.*.so`（Linux）/ `.pyd`（Windows）就能像普通模块一样 `import`。

> 关键点：**加 `cdef` 声明 C 类型后，`for` 循环里的 `i` 是 C 的 `int`，`s` 是 C 的 `long`，不再走 Python 对象的加减**。这是加速的核心。

---

## 3. 直冲 C 级速度：函数声明为 `cpdef` / `cdef`

`def` 函数仍然可以被 Python 调用，但参数和返回值会被自动转换成 Python 对象。如果你只在 Cython 内部调用这个函数，用 `cdef` 或 `cpdef` 能进一步减少开销。

```cython
# sum_fast.pyx
cpdef long sum_cy_fast(long n):
    cdef long s = 0
    cdef long i
    for i in range(n):
        s += i
    return s
```

- `cdef`：只能被 Cython 内部调用，最快。
- `cpdef`：既能被 Cython 调用，也能被 Python 调用；推荐写库时使用。
- `def`：纯 Python 接口，参数进出会有装箱开销。

把原来的 `def` 换成 `cpdef` 并给参数加类型，速度通常能再提升一截。

---

## 4. 在 Jupyter 里快速验证：`%%cython` 魔法命令

不想建工程？在 notebook 里装 `cython` 后：

```python
%load_ext cython
```

```python
%%cython -a
cpdef long sum_cy(long n):
    cdef long s = 0
    cdef long i
    for i in range(n):
        s += i
    return s
```

- `-a` 会生成一份 HTML 报告，**黄色越深表示那段代码残余的 Python 操作越多**。目标是把循环内的黄色刷白。
- 这是排查“为什么我加速不明显”的最佳工具——很多时候是因为某个变量仍然是 Python 对象。

验证性能：

```python
import time
n = 100_000_000
t0 = time.perf_counter(); sum_cy(n); t1 = time.perf_counter()
print(f"cython: {t1 - t0:.3f}s")
```

通常能从 5~8 秒降到 **0.05~0.1 秒**，接近 C 的水平。

---

## 5. 工程级建议：什么时候该用 Cython？

**适合用：**
- 数值循环、图像像素遍历、仿真内核、字符串批量处理。
- 已有 Python 代码，只想对最热的那 5% 函数加速。
- 需要把热点代码分发给别人，且有编译环境。

**不适合用：**
- 逻辑简单、只在 I/O 上耗时（网络、磁盘）——加速无意义。
- 算法复杂度本身是主要瓶颈（先换算法，再换语言）。
- 一次性脚本——编译链路维护成本 > 收益。

**工程实践小贴士：**
- 先 `cProfile` 找到瓶颈，再上 Cython，别全项目乱撒。
- 用 `# cython: boundscheck=False`、`wraparound=False`、`cdivision=True` 等编译指令关掉安全检查，能再快一点。
- 库里对外暴露的函数用 `cpdef`，内部用 `cdef`。
- 保持 Python 版本回归：给 `.pyx` 也写测试，用 `pytest` 一起跑。

> 把 Cython 当作一把**外科手术刀**，而不是重写整个项目。这是从“会写 Python”到“能优化 Python”的关键分水岭。

```python
# 完整可运行示例：一个文件跑通"纯 Python vs Cython"对比
# 依赖：pip install cython
# 运行：python demo.py build_ext --inplace 2>/dev/null || true
#      python demo_run.py

# ---------- demo.py (编译脚本) ----------
"""
from setuptools import setup
from Cython.Build import cythonize

setup(
    ext_modules=cythonize(
        "fastsum.pyx",
        language_level="3",
        compiler_directives={
            "boundscheck": False,
            "wraparound": False,
            "cdivision": True,
        },
    ),
)
"""

# ---------- fastsum.pyx ----------
"""
cpdef long sum_fast(long n):
    cdef long s = 0
    cdef long i
    for i in range(n):
        s += i
    return s
"""

# ---------- demo_run.py (本文件) ----------
import time

# 1) 纯 Python 基线
def sum_py(n: int) -> int:
    s = 0
    for i in range(n):
        s += i
    return s

# 2) Cython 版本（需先编译出 fastsum 模块；若未编译则跳过）
try:
    from fastsum import sum_fast
    has_cy = True
except ImportError:
    has_cy = False
    print("[提示] 未找到 fastsum 模块，请先运行编译步骤。")

N = 100_000_000

t0 = time.perf_counter()
sum_py(N)
t1 = time.perf_counter()
print(f"pure python : {t1 - t0:.3f}s")

if has_cy:
    t0 = time.perf_counter()
    sum_fast(N)
    t1 = time.perf_counter()
    print(f"cython      : {t1 - t0:.3f}s")
```

## py.perf.numba

# 40 分钟教学讲义：`py.perf.numba`

> **一句话直觉**：Python 写起来舒服，但纯 Python 循环慢得像蜗牛；Numba 让你在代码几乎不改的情况下，把关键函数即时编译（Just-In-Time, JIT）成机器码，提速几十到几百倍。

---

## 0. 为什么要学 Numba？

很多 AI / 工程场景里，Python 的性能瓶颈往往不是框架本身，而是你自己写的一段 `for` 循环：

- 数值模拟、蒙特卡洛、金融回测、物理引擎、图像逐像素处理。
- 想用 NumPy 向量化，但算法天然带依赖、写不整齐。
- 重写成 C / C++ / Cython 成本高，还要维护两份代码。

Numba 的定位：**给 Python 函数加一个装饰器，就能获得接近 C 的运行速度**，不需要离开 Python 生态。

安装：

```bash
pip install numba
# Numba 会自带 llvmlite，依赖 LLVM 做即时编译
```

---

## 1. 第一口：`@njit` 让循环快起来

核心 API 就是 `numba.njit`（`nopython=True` 的 `jit` 简写）。它告诉 Numba：**这个函数里所有操作都必须能被编译成机器码，不许回退到 Python 解释器**。做不到就报错，非常严格，也非常可靠。

```python
import time
import numpy as np
from numba import njit

def python_sum(x):
    total = 0.0
    for v in x:
        total += v
    return total

@njit
def numba_sum(x):
    total = 0.0
    for v in x:
        total += v
    return total

x = np.arange(10_000_000, dtype=np.float64)

# 预热：第一次调用会触发编译
numba_sum(x)

t0 = time.perf_counter(); python_sum(x); t1 = time.perf_counter()
t2 = time.perf_counter(); numba_sum(x);  t3 = time.perf_counter()
print(f"Python : {t1-t0:.3f}s")
print(f"Numba  : {t3-t2:.3f}s")
```

典型输出：Python 约 0.5 秒，Numba 约 0.005 秒，**提速约 100 倍**。

---

## 2. 关键机制：即时编译（JIT）与类型特化

Numba 第一次调用被装饰的函数时，会：

1. 检查你传入的参数类型（比如 `float64[:]`，即一维 float64 数组）。
2. 针对这些类型**现场编译**一份机器码。
3. 后续用相同类型再次调用时，直接复用已编译版本（缓存，cache）。

这就是**类型特化（type specialization）**：`numba_sum` 传 float64 数组和传 int64 数组，会生成两份不同机器码。

```python
from numba import njit

@njit
def add(a, b):
    return a + b

print(add(1, 2))          # 生成 int64 版本
print(add(1.0, 2.0))      # 生成 float64 版本
print(add.signatures)     # 查看已编译的签名列表
```

**要点**：第一次调用有编译开销（0.1 秒左右很常见）。所以：

- 性能测试一定要**先预热**再计时。
- 高频小函数可以用 `@njit(cache=True)` 把编译结果缓存到磁盘，下次启动直接读。

```python
@njit(cache=True)
def f(x):
    return x * 2
```

---

## 3. 必须守住的红线：nopython 模式

`@njit` 是 `@jit(nopython=True)` 的缩写。**nopython 模式意味着函数体里不能出现 Python 解释器才能处理的对象**。以下代码会报 `TypingError`：

```python
from numba import njit

@njit
def bad(n):
    d = {}            # 字典字面量虽然支持有限
    s = "hello"       # 字符串支持非常有限
    return [str(i) for i in range(n)]  # str() 不支持
```

Numba 支持的常见类型：

| 类别 | 支持 |
|---|---|
| 标量 | `int`、`float`、`complex`、`bool` |
| 数组 | NumPy `ndarray`（任意维、常用 dtype） |
| 元组 | 同构、异构元组均支持 |
| 容器 | `typed.List`、`typed.Dict`（需从 `numba.typed` 导入） |
| 结构化 | `numba.types` 中的 `Record`、`NamedTuple` |

**不支持**：普通 Python `list`（作为元素类型不确定的容器）、`dict`、`set`、字符串拼接、大多数标准库对象、生成器、`yield`（Numba 有自己的生成器但受限）。

处理 “想让 list 也进 Numba” 的标准做法是用 `numba.typed.List`：

```python
from numba import njit
from numba.typed import List

@njit
def total(lst):
    s = 0
    for x in lst:
        s += x
    return s

lst = List()
lst.append(1.0)
lst.append(2.0)
lst.append(3.0)
print(total(lst))   # 6.0
```

---

## 4. 工程级用法：并行、向量化、`prange`

Numba 提供 `@njit(parallel=True)` + `numba.prange`，自动把循环切到多核。这在纯 Python 里要用 `multiprocessing` 才能勉强做到。

```python
import numpy as np
from numba import njit, prange

@njit(parallel=True)
def pairwise_dist(X, Y):
    n, m = X.shape[0], Y.shape[0]
    D = np.empty((n, m), dtype=np.float64)
    for i in prange(n):                 # 并行维度
        for j in range(m):
            d = 0.0
            for k in range(X.shape[1]):
                diff = X[i, k] - Y[j, k]
                d += diff * diff
            D[i, j] = d
    return D

X = np.random.rand(2000, 64)
Y = np.random.rand(2000, 64)
pairwise_dist(X, Y)   # 预热
```

多核会带来几倍加速，但要注意：

- `prange` 的循环体**不能有跨迭代的依赖**（比如累加同一个标量）。
- 并行开销存在，小任务反而变慢。

---

## 5. 与 NumPy 的关系：先向量化，再 Numba

一个常被后人踩的顺序问题：

1. **能向量化就向量化**（NumPy 数组运算，一次 C 循环）。
2. **向量化写不整齐**（滑动窗口、递归、逐元素带状态），再上 Numba。
3. Numba 函数里能调 NumPy 的 `np.exp`、`np.dot` 等，但每个元素函数也是编译过的版本。

```python
import numpy as np
from numba import njit

@njit
def moving_average(x, w):
    n = x.size
    out = np.empty(n - w + 1, dtype=np.float64)
    s = 0.0
    for i in range(w):
        s += x[i]
    out[0] = s / w
    for i in range(1, out.size):
        s += x[i + w - 1] - x[i - 1]
        out[i] = s / w
    return out

x = np.random.rand(1_000_000)
print(moving_average(x, 10).shape)   # (999991,)
```

这是一个 NumPy 也能写，但 Numba 写起来更直观、性能也很接近的例子。

---

## 小结

- 一句话定位：**Numba = 让 Python 函数 JIT 成机器码**。
- 核心装饰器：`@njit`（严格 nopython 模式）。
- 首次调用有编译开销：先预热再计时；用 `cache=True` 保存编译结果。
- 守住红线：函数里只使用 Numba 支持的类型（标量、NumPy 数组、元组、`typed.List` / `typed.Dict`）。
- 工程进阶：`parallel=True` + `prange` 做多核；`numpy` 向量化优先于 Numba，Numba 用于向量化写不整齐的场合。

---

## 动手练习

**任务**：把下面这段纯 Python 的 “滑动窗口最大值”（每一步取 w 个元素的最大值）改写成 Numba 版本，并比较性能。

```python
def sliding_max_py(x, w):
    n = len(x)
    out = [0.0] * (n - w + 1)
    for i in range(n - w + 1):
        m = x[i]
        for j in range(i + 1, i + w):
            if x[j] > m:
                m = x[j]
        out[i] = m
    return out
```

要求：

1. 输入改为 NumPy 一维数组，`w` 为整数。
2. 用 `@njit` 装饰，函数体内只使用 NumPy 数组与标量。
3. 用 `np.random.rand(1_000_000)` 和 `w=64` 做测试，先预热 Numba 版本，再分别计时。
4. 报告你的加速比，并解释为什么第一次调用 Numba 版本反而可能更慢。
5. 加分：用 `@njit(parallel=True)` + `prange` 在输出维度并行，看看能不能再快一截。

提示：返回数组用 `np.empty(n - w + 1, dtype=x.dtype)` 预分配。


---

## 本课题目

### single_choice · None



- [A] 使用列表推导式 [a + b for a, b in zip(list_a, list_b)]
- [B] 使用 for 循环逐个元素相加并追加到新列表
- [C] 使用 numpy 数组，直接执行 array_a + array_b
- [D] 使用 map(lambda x, y: x + y, list_a, list_b)

**参考答案**：2

**解析**：numpy 的向量化运算在底层用 C 完成批量运算，避免了 Python 层的逐元素循环开销，通常远快于列表推导、for 循环和 map。

### single_choice · None



- [A] numpy 数组只能存放同一种数据类型，因此适合批量数值运算
- [B] numpy 数组可以像列表一样随时存放不同类型的元素，且运算更快
- [C] Python 列表的整数相加会自动执行逐元素相加
- [D] numpy 数组的加法默认会把所有元素拼接成一个更长的数组

**参考答案**：0

**解析**：numpy 数组要求同质数据类型，这使其内存布局紧凑并支持向量化运算；列表可混存类型，[1,2]+[3,4] 是拼接而非逐元素相加。

### single_choice · None



- [A] numpy 会自动补齐较短的数组并继续运算
- [B] numpy 会抛出形状不匹配的错误
- [C] numpy 会只对重叠部分进行运算，忽略多余元素
- [D] numpy 会返回一个空数组

**参考答案**：1

**解析**：广播有明确规则，不满足规则时 numpy 不会猜测或截断，而是抛出 ValueError 之类的形状不匹配错误。

### single_choice · None



- [A] result = np.empty(n); for i in range(n): result[i] = a[i] * b[i]
- [B] result = a * b  // a、b 是形状相同的 numpy 数组
- [C] result = [a[i] * b[i] for i in range(n)]  // a、b 是 numpy 数组
- [D] result = []; for x, y in zip(a, b): result.append(x * y)

**参考答案**：1

**解析**：a * b 直接由 numpy 向量化执行逐元素乘法，避免了 Python 层循环，通常性能更好。

### single_choice · None



- [A] 向量化运算在底层通常由编译语言实现，减少 Python 解释器开销
- [B] 向量化运算可以一次处理整个数组，而不是逐个元素在 Python 层循环
- [C] 向量化运算一定比任何 Python 循环都快，包括调用外部库的循环
- [D] 向量化运算依赖数组的连续内存和同质数据类型

**参考答案**：2

**解析**：向量化通常更快，但“一定比任何 Python 循环都快”过于绝对；例如调用已优化 C 扩展的循环可能仍有竞争力，且小数组时 Python 循环开销未必明显。

### single_choice · None



- [A] True
- [B] False
- [C] [False, True, True]
- [D] [1, 2, 3]

**参考答案**：2

**解析**：对 numpy 数组使用比较运算符会返回逐元素的布尔数组，因此 a > 1 得到 [False, True, True]。

### single_choice · None



- [A] 因为 numpy 数组可以直接用 print 输出更美观
- [B] 因为 numpy 数组支持向量化和高效的内存布局，适合批量数值运算
- [C] 因为嵌套列表不能存储数字
- [D] 因为 numpy 数组会自动并行使用多核 CPU

**参考答案**：1

**解析**：numpy 数组的同质连续内存和向量化运算使其在图像、数值等批量数据上更高效；它并不自动使用多核，也不影响 print 美观。

### single_choice · None



- [A] A
- [B] B
- [C] C
- [D] D

**参考答案**：2

**解析**：arr = arr + 1 先计算新数组再重新绑定变量，不会就地修改原数组；A、B、D 都会影响原数组内容。

### single_choice · None



- [A] numpy 数组不支持 for 循环，会直接报错
- [B] 每次循环都要经过 Python 解释器的逐元素开销，无法利用底层批量优化
- [C] for 循环会自动把数组转成列表，因此变慢
- [D] numpy 数组在 for 循环中会被冻结，无法读取元素

**参考答案**：1

**解析**：numpy 数组可以迭代，但在 Python 层逐元素循环会引入解释器开销，丧失向量化批量执行的优势。

### single_choice · None



- [A] ufunc 只能一次处理一个标量，不能处理数组
- [B] ufunc 对数组逐元素进行运算，并支持广播，是向量化的重要工具
- [C] ufunc 会改变输入数组的数据类型为 object
- [D] ufunc 只能用于加法，不能用于三角函数等数学函数

**参考答案**：1

**解析**：ufunc 是 numpy 中逐元素运算的通用函数，支持数组输入和广播，如 np.add、np.sqrt、np.sin 等，不是只能处理标量或只能做加法。

### single_choice · None



- [A] [1, 2, 3, 1, 2, 3]
- [B] [2, 4, 6]
- [C] 报错，数组不能与标量相乘
- [D] [1, 4, 9]

**参考答案**：1

**解析**：numpy 数组与标量相乘会执行逐元素乘法，结果为 [2, 4, 6]；数组与标量运算会触发广播。

### single_choice · None



- [A] count = 0; for x in arr: if x > 0: count += 1
- [B] count = sum(1 for x in arr if x > 0)
- [C] count = np.count_nonzero(arr > 0)
- [D] count = len([x for x in arr if x > 0])

**参考答案**：2

**解析**：arr > 0 生成布尔数组，np.count_nonzero 在底层统计非零（即 True）个数，属于向量化统计；其余选项都在 Python 层循环。

### single_choice · None



- [A] [1, 2, 3, 10, 20, 30]
- [B] [11, 22, 33]
- [C] [10, 40, 90]
- [D] 报错，numpy 数组不支持 + 运算

**参考答案**：1

**解析**：两个形状相同的 numpy 数组相加执行逐元素加法，结果为 [11, 22, 33]；拼接是列表的行为，不是数组加法的默认语义。

### single_choice · None



- [A] result = [x * 2 for x in data]  // data 是 numpy 数组
- [B] result = np.zeros(len(data)); for i in range(len(data)): result[i] = data[i] * 2
- [C] result = data * 2  // data 是 numpy 数组
- [D] result = list(map(lambda x: x * 2, data))  // data 是 numpy 数组

**参考答案**：2

**解析**：data * 2 直接对整个 numpy 数组执行标量乘法，属于向量化写法；其余选项都在 Python 层逐元素循环。

### single_choice · None



- [A] 对长度很大的数组进行逐元素算术运算
- [B] 在循环中反复把很小的 Python 列表转换成 numpy 数组再转回列表
- [C] 对两个形状相同的大数组做逐元素乘法
- [D] 对一个大数组整体应用数学函数

**参考答案**：1

**解析**：numpy 的优势来自批量处理；若在 Python 循环中反复做小数组与列表之间的转换，转换开销会抵消收益，甚至比纯 Python 更慢。

### single_choice · None



- [A] 广播要求两个数组的形状完全一致，否则一定报错
- [B] 广播会把较小的数组自动复制到与较大数组相同的形状后再运算
- [C] 广播只能用于加法，不能用于乘法和比较运算
- [D] 广播会修改原数组的形状，使其永久变为较大数组的形状

**参考答案**：1

**解析**：广播按规则在逻辑上扩展较小数组以匹配较大数组的形状，从而支持逐元素运算；它不要求形状完全一致，也不限于加法，更不会永久改变原数组形状。

### single_choice · None



- [A] 报错，形状不匹配
- [B] [[11, 22, 33], [14, 25, 36]]
- [C] [[11, 22, 33], [44, 55, 66]]
- [D] [10, 40, 90]

**参考答案**：1

**解析**：形状 (2,3) 与 (3,) 满足广播规则，b 被广播到每一行，因此结果为 [[11,22,33],[14,25,36]]。

### single_choice · None



- [A] 使用 math.sqrt 配合 for 循环逐个元素计算
- [B] 使用列表推导式 [math.sqrt(x) for x in data]
- [C] 使用 numpy 的 np.sqrt(data) 对整个数组运算
- [D] 使用 while 循环配合索引逐个元素计算

**参考答案**：2

**解析**：np.sqrt 对整个数组进行向量化运算，在底层实现批量计算，通常比 math.sqrt 配合 Python 循环快很多。

### single_choice · None



- [A] numpy 数组在内存中连续存储同类型数据，访问和批量运算更高效
- [B] numpy 数组与 Python 列表一样，每个元素都是独立的 Python 对象指针
- [C] Python 列表在内存中连续存储同类型数据，因此数值运算更快
- [D] numpy 数组的元素访问比列表慢，因为需要类型检查

**参考答案**：0

**解析**：numpy 数组使用连续的同质内存块，有利于缓存和向量化；列表存储的是指向 Python 对象的指针，逐个运算需要 Python 解释器逐元素处理。

### single_choice · None



- [A] A
- [B] B
- [C] C
- [D] D

**参考答案**：2

**解析**：C 在 Python 层显式循环逐个修改元素，没有利用向量化；A、B、D 都是 numpy 的向量化操作或布尔索引。

### single_choice · None



- [A] 把 Python 源码逐行解释执行，省去编译步骤
- [B] 把带类型标注的 Python 风格代码编译成 C 扩展模块
- [C] 在运行时用 JIT 把热点函数编译成机器码
- [D] 把 Python 字节码翻译成汇编后直接嵌入解释器

**参考答案**：1

**解析**：Cython 是静态编译器，它接受（近似）Python 语法的源码并生成 C 代码，再编译成可供 Python 导入的扩展模块；它不是解释器，也不是 JIT。

### single_choice · None



- [A] cdef 定义的函数只能被 Python 调用，不能被 C 调用
- [B] def 定义的函数只能在模块内部使用
- [C] cdef 函数是 C 级函数，调用开销低，但默认不能被 Python 直接调用
- [D] def 和 cdef 生成的函数在调用开销上完全等价

**参考答案**：2

**解析**：cdef 声明的是 C 函数，绕过 Python 调用协议，开销小，但默认对 Python 层不可见；def 生成普通 Python 函数，可被外部调用。

### multi_choice · None



- [A] 热循环中大量操作 Python 对象且无法进行类型推断
- [B] 代码几乎不包含重复计算，主要耗时在 IO 等待上
- [C] 把核心数值循环的变量都声明为 C 类型并移除冗余边界检查
- [D] 频繁在 C 与 Python 层之间来回转换、反复装箱拆箱

**参考答案**：[0, 1, 3]

**解析**：Cython 只加速 CPU 密集且可类型化的部分；IO 等待、无法类型化的对象操作、频繁装箱拆箱都不会得到明显收益。

### multi_choice · None



- [A] 通常需要把 .pyx 交给 Cython 编译器生成 C 源码
- [B] 生成的 C 源码需要再用 C 编译器编译为扩展模块
- [C] 编译产物是可被 Python 直接 import 的扩展模块
- [D] 编译后运行不再需要 Python 解释器

**参考答案**：[0, 1, 2]

**解析**：Cython 流程是 .pyx → C 源码 → C 编译 → 扩展模块，最终仍由 Python 解释器 import 使用，所以运行时依然需要解释器。

### fill_blank · None



**参考答案**：["cdef double", "cdef double ", "cdef  double"]

**解析**：cdef 用于声明 C 类型变量，double 是 C 的浮点类型，因此写作 cdef double x。

### fill_blank · None



**参考答案**：["cimport", "cimport "]

**解析**：cimport 在编译期导入 C 级声明，与运行期的 import 不同。

### fill_blank · None



**参考答案**：["boundscheck", "boundscheck "]

**解析**：boundscheck(False) 关闭索引边界检查以提速，前提是索引本身安全。

### code_reading · None



**参考答案**：i 和 s 都是原生 C 整数（long）。由于用 cdef 声明了类型，循环被编译为 C 层的 for 循环，累加是机器整数加法，不创建 Python int 对象、不经过动态派发，因此比纯 Python 循环快。

**解析**：关键在于 cdef 声明使变量具有 C 类型，从而消除逐次的对象装箱与解释开销。

### code_reading · None



**参考答案**：因为数组元素被声明为 float64 并可通过缓冲区直接以 C 方式读写，避免每次索引都创建 Python float 对象、走 NumPy 的通用分派。索引安全由 Cython 的 boundaries 检查保证（默认开启边界检查），如关闭需自行保证 i 在范围内。

**解析**：类型化的缓冲访问是 Cython 提速数值代码的核心机制，边界检查默认提供安全性。

### code_reading · None



**参考答案**：不能直接调用。inc 是用 cdef 声明的 C 方法，对 Python 层不可见，只能在本模块或其他 Cython 模块内部（通过 cimport）调用。若希望 Python 也能调用，应改用 def 或 cpdef。

**解析**：cdef 方法的可见性限制在 C 层，这是常见的接口设计陷阱。

### scenario · None



**解析**：仅改后缀通常收益很小，关键是对热点循环做类型声明（cdef）、减少 Python 对象操作，并先用剖析确认瓶颈确在此循环。

### scenario · None



**解析**：该逻辑几乎全是 Python 对象操作，Cython 无法把循环下沉到 C 层，反而可能因跨层调用产生额外开销；应先定位热点，能类型化的部分用 C 类型，并把重操作尽量留在 Python 或改用专用库。

### single_choice · None



- [A] 在循环前写 cdef int i，并把循环写成 for i in range(n)
- [B] 在循环前写 i = 0，循环写成 while i < n
- [C] 在循环内使用 i = int(i) 强制转换
- [D] 在文件顶部写 # cython: language_level=3

**参考答案**：0

**解析**：用 cdef 声明 C 类型变量后，range 循环会被编译为 C 的 for 循环，i 是原生整数；仅写 Python 赋值或 int() 转换不会消除对象开销。

### single_choice · None



- [A] memoryview 只能用于一维数组，多维必须用 ndarray
- [B] memoryview 提供带边界与类型检查的缓冲访问，可避免逐元素 Python 对象开销
- [C] memoryview 会自动把数据复制一份，因此更安全
- [D] memoryview 只能读不能写

**参考答案**：1

**解析**：Cython 的 typed memoryview 直接访问缓冲区并带类型/维度校验，能显著降低逐元素访问成本，也不会自动复制数据。

### single_choice · None



- [A] 循环体内全部是对 Python 对象调用方法、无法做类型推断时
- [B] 循环包含大量整数运算、且变量已声明为 C 类型时
- [C] 循环包含大量字符串拼接时
- [D] 循环中频繁调用 Python 内置函数时

**参考答案**：1

**解析**：Cython 的收益主要来自把类型明确的数值运算下沉到 C 层，减少 Python 对象创建与动态派发；无法类型推断的代码收益有限。

### single_choice · None



- [A] 让代码在数组越界时抛 Python 异常
- [B] 关闭索引边界检查与负索引回绕，减少访问开销，但需自行保证索引合法
- [C] 让 Cython 自动把数组转为 Python list
- [D] 把编译模式切换为解释模式以便调试

**参考答案**：1

**解析**：这两个指示用于在确保索引安全的前提下省去每次访问的检查和回绕计算，从而提速，代价是失去自动保护。

### single_choice · None



- [A] .pyx 存放实现，.pxd 用于声明可被其他模块 cimport 的 C 级接口
- [B] .pxd 存放实现，.pyx 只用于声明
- [C] 两者必须同名且内容相同
- [D] .pxd 只能放 Python 函数定义，不能放 cdef 声明

**参考答案**：0

**解析**：.pyx 是编译实现文件，.pxd 是类似 C 头文件的声明文件，用于暴露 C 级接口供其他 Cython 模块 cimport。

### single_choice · None



- [A] import
- [B] from ... import
- [C] cimport
- [D] require

**参考答案**：2

**解析**：cimport 用于在编译期导入 C 级声明（如 .pxd 中声明的 cdef 函数/类型），import 只能拿到 Python 可见对象。

### multi_choice · None



- [A] 把循环变量和累积变量声明为 C 数值类型
- [B] 在热循环中避免创建 Python 对象（如临时 list、str）
- [C] 为热循环启用 boundscheck(False) 且确保索引安全
- [D] 在热循环内频繁调用 Python 层的 print 观察中间值
- [E] 把纯 Python 函数整个用 def 保持不动，仅改文件后缀为 .pyx

**参考答案**：[0, 1, 2]

**解析**：C 类型、减少对象创建、关闭冗余边界检查都能提速；循环内 print 会引入大量 Python 调用反而拖慢；仅改后缀而不做类型标注通常收益极小。

### multi_choice · None



- [A] 它的属性可以用 cdef 声明为 C 类型，访问开销低于普通实例属性
- [B] 它可以定义 cdef 方法，这类方法不能被 Python 直接调用
- [C] 它默认和普通 Python class 在属性访问与内存布局上完全一致
- [D] 它可以被其他 Cython 模块通过 cimport 使用其 C 级接口

**参考答案**：[0, 1, 3]

**解析**：cdef class 使用结构化内存布局，属性可声明为 C 类型，访问更快；cdef 方法对 Python 不可见；可通过 .pxd 暴露接口。它与普通 class 的布局并不相同。

### single_choice · None



- [A] Numba 通过把 Python 字节码解释执行得更快，从而提升性能
- [B] Numba 在运行时将热点函数编译为机器码，从而绕过 CPython 解释器的开销
- [C] Numba 把所有 Python 对象自动转换为 C++ 对象并缓存到磁盘
- [D] Numba 只能加速字符串处理，对数值计算无效

**参考答案**：1

**解析**：Numba 是一个即时（JIT）编译器，它在运行时把被装饰的 Python 函数编译为针对当前 CPU 的机器码，使数值循环等热点代码脱离 CPython 解释器的逐条字节码开销。它并非缓存 C++ 对象到磁盘，也不限于字符串处理。

### single_choice · None



- [A] 一个只做一次字典查找、立即返回的短函数
- [B] 一个对大型 NumPy 数组逐元素做数值循环的函数，会被调用很多次
- [C] 一个负责打开网络连接并解析 JSON 的函数
- [D] 一个调用第三方 C 扩展完成全部计算的包装函数

**参考答案**：1

**解析**：Numba 的收益来自把大量重复的数值运算编译为机器码，因此对大型数组的逐元素循环类热点函数收益最大。单次字典查找、网络 I/O、JSON 解析这类非计算型或已由 C 扩展完成的函数，加速空间很小，甚至因编译开销而变慢。

### single_choice · None



- [A] 调用 numpy 的向量化函数对整个数组做运算
- [B] 在函数内定义一个闭包并返回它供外部使用
- [C] 在函数内动态创建新的 Python 类
- [D] 使用 pandas DataFrame 做按列分组聚合

**参考答案**：0

**解析**：Numba 支持相当一部分 NumPy 的数组运算，可以高效执行。动态创建类、pandas 的复杂表格操作、返回闭包等不属于其支持的 nopython 特性。

### multi_choice · None



- [A] 在基准测试中先对函数做若干次预热调用，再开始计时
- [B] 用 cache=True 把编译结果缓存到磁盘，减少重复编译
- [C] 在装饰器中提供显式签名，避免每次调用重新推断类型
- [D] 在每次请求中都重新定义并重新装饰同一个函数

**参考答案**：[0, 1, 2]

**解析**：预热调用、磁盘缓存、显式签名都能减少或摊销编译成本。而在每次请求中重新定义并装饰函数，会反复触发编译，反而放大开销。

### multi_choice · None



- [A] 函数中对类型不断变化的变量反复赋值，使类型无法静态推断
- [B] 函数中调用了 Numba 不支持的标准库或第三方库函数
- [C] 函数中使用了结构固定的 NumPy 数组运算
- [D] 函数中访问了全局的、运行时才确定的 Python 对象

**参考答案**：[0, 1, 3]

**解析**：类型不稳定、调用不受支持的库函数、依赖运行时的全局 Python 对象，都可能让 Numba 无法完成 nopython 编译。结构固定的 NumPy 数组运算恰恰是受支持的典型用法。

### multi_choice · None



- [A] 并行并不总是更快，小规模循环或启动开销大时可能变慢
- [B] 共享状态的读改写必须在并行循环中妥善处理，否则结果不确定
- [C] prange 标记的循环一定安全，无需检查数据依赖
- [D] 并行化后的性能还受核心数、内存带宽等因素影响

**参考答案**：[0, 1, 3]

**解析**：并行有启动和调度开销，数据量小或任务轻时可能得不偿失；存在共享写时必须处理竞争；核心数、内存带宽等硬件因素也影响收益。prange 只是提示可并行，不能保证循环无数据依赖，因此“一定安全”是错误的。

### multi_choice · None



- [A] 应先用性能分析工具定位真正的热点，再决定是否用 Numba 加速
- [B] 把 I/O、网络等待等非计算部分也放进被编译函数，能显著提速
- [C] 将纯数值计算与 I/O 分离，只对计算部分使用 Numba，往往更有效
- [D] 对已经由高度优化的 C 库完成的运算再套一层 Numba，收益通常有限

**参考答案**：[0, 2, 3]

**解析**：优化的前提是定位热点；把 I/O 等非计算部分放进编译函数并不会加速，反而可能无法编译或引入抖动；对已高度优化的 C 库运算再包一层，收益通常有限。因此正确做法是分离计算与 I/O。

### fill_blank · None



**参考答案**：["cache"]

**解析**：Numba 的 cache 参数（如 @njit(cache=True)）会把编译产物缓存到磁盘，同一函数在后续运行中可直接加载，减少重复编译开销。

### fill_blank · None



**参考答案**：["prange", "numba.prange"]

**解析**：prange 是 Numba 提供的并行循环构造，配合 parallel=True 使用，告诉编译器该循环的迭代可以分配到多个线程执行。

### code_reading · None



**参考答案**：可以成功编译为 nopython 模式，输出为 10.0。因为循环边界由静态可知的 arr.shape[0] 决定，累加变量是固定类型的 float64 标量，arr[i] 是 NumPy 标量，全部类型可静态推断，符合 nopython 编译要求。

**解析**：该函数只使用定长数组的索引循环和标量累加，类型稳定、无 Python 对象动态操作，因此可编译；np.arange(5) 之和为 0+1+2+3+4=10.0。

### code_reading · None



**参考答案**：该函数很可能无法完成 nopython 编译，或报类型推断错误。原因是在不同分支里变量 x 被赋予了不同的类型（int 与 str），导致同一变量类型不一致，Numba 无法为其分配统一类型进行静态编译。

**解析**：Numba 的 nopython 编译要求变量具有一致且可静态推断的类型。同一变量在不同分支返回不同类型会破坏类型一致性，从而编译失败。改写时应让各分支返回相同类型。

### scenario · None



**解析**：先用分析工具确认这个逐元素函数确实是热点；把纯数值计算从 I/O、数据库操作中分离出来，只对该计算函数应用编译。测试时先预热若干次再做基准，避免首次编译耗时计入结果；可用显式签名稳定类型、用并行（parallel+prange）提升吞吐，同时注意并行安全与共享写。这样既得到加速，又避免 I/O 部分无法编译或抖动。

### single_choice · None



- [A] Numba 需要把结果写入磁盘缓存，写入很耗时
- [B] 首次调用触发类型推断与 JIT 编译，这段编译时间被计入首次调用
- [C] Numba 会在首次调用时向网络请求优化配置
- [D] 首次调用必须解释执行整个 Python 标准库

**参考答案**：1

**解析**：Numba 是即时编译，函数第一次被调用时才知道参数的实际类型，从而完成类型推断和编译，这段编译耗时体现在首次调用上。后续调用使用已编译版本，因此快很多。这是基准测试时必须留意的预热效应。

### single_choice · None



- [A] @njit 等价于 @jit(nopython=True)，要求函数完全脱离 Python 对象模式编译
- [B] @njit 是 @jit 的旧写法，两者完全无关
- [C] @njit 允许回退到对象模式，而 @jit 禁止回退
- [D] @njit 只能用于类方法，@jit 只能用于普通函数

**参考答案**：0

**解析**：@njit 是 @jit(nopython=True) 的简写，它强制以 nopython 模式编译：如果无法脱离 Python 对象编译就会报错。这让问题更早暴露，避免“看似加速实则仍走对象模式”的陷阱。

### single_choice · None



- [A] 对一维 NumPy 数组做 for 循环并累加
- [B] 使用 math.sqrt 对单个数值求平方根
- [C] 对一个元素类型混杂、结构随机的 Python list 做动态增删和类型转换
- [D] 使用 numpy 数组的 shape 属性

**参考答案**：2

**解析**：nopython 模式需要静态可推断的类型。对结构、类型不固定的 Python 容器做动态增删和类型转换，往往无法被编译，从而报错或回退。而数组循环、math 标量函数、数组属性都是受支持的典型用法。

### single_choice · None



- [A] 在装饰器中传入 signature 参数，例如 @njit(float64(float64[:]))
- [B] 在函数体内写 assert isinstance(x, np.ndarray)
- [C] 在函数上方加 @staticmethod
- [D] 用 eval() 动态生成类型声明

**参考答案**：0

**解析**：Numba 允许通过装饰器的 signature 参数显式声明参数与返回类型，形式类似返回类型(参数类型)。显式签名可以避免每次调用重新做类型推断，也能提前发现类型不匹配。assert isinstance 不改变 Numba 的编译策略。

### single_choice · None



- [A] lazy 编译在函数定义时立即编译，eager 编译在首次调用时编译
- [B] eager 编译在提供显式签名时于装饰阶段完成编译，lazy 编译在首次调用时才编译
- [C] 两者没有区别，只是命名不同
- [D] eager 编译只能用于返回值为 None 的函数

**参考答案**：1

**解析**：当装饰器里给出显式签名时，Numba 可以在装饰阶段就完成编译，称为 eager 编译；若不给签名，则在首次调用时根据实际类型编译，称为 lazy 编译。

### single_choice · None



- [A] 让函数在多个 CPU 核心上并行执行循环迭代，以缩短墙钟时间
- [B] 把结果持久化到磁盘以便下次直接读取
- [C] 降低内存占用，使数组更小
- [D] 自动把 Python 代码转换成 C++ 源码

**参考答案**：0

**解析**：parallel=True 启用 Numba 的自动并行化，配合 prange 显式标记可并行的循环，把迭代分配到多个线程/核心上执行，从而缩短墙钟时间。它不负责落盘或内存压缩。

### single_choice · None



- [A] 在并行循环体内对共享的一个 Python 整数变量做 s = s + x[i]
- [B] 在并行循环体内对共享的 NumPy 标量做自增
- [C] 每个迭代只写入独立的下标位置，例如 out[i] = f(x[i])
- [D] 在循环体内修改循环变量 i 本身

**参考答案**：2

**解析**：并行安全的关键是各迭代写入互不重叠的独立内存位置。对共享标量做读改写会形成数据竞争，结果不确定；修改循环变量同样破坏并行语义。仅有 out[i] = f(x[i]) 这类各写各的元素是安全的。

### single_choice · None



- [A] 对固定长度数组的数值循环
- [B] 包含大量分支判断的逐元素计算
- [C] 包含反复抛出和捕获 Python 异常的复杂控制流
- [D] 基于索引的矩阵元素访问与累加

**参考答案**：2

**解析**：Numba 对数值循环和分支支持良好，但异常处理的复杂控制流大多无法在 nopython 模式下编译。逐元素分支、定长数组循环、索引访问都是其擅长的场景。
