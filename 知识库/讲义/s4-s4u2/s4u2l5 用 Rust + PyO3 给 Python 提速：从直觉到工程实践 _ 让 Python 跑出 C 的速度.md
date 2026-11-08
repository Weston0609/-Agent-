# s4u2l5 用 Rust + PyO3 给 Python 提速：从直觉到工程实践 / 让 Python 跑出 C 的速度

> 来源 `content/lessons/s4u2l5.json`

## py.perf.rust_pyo3

# 用 Rust + PyO3 给 Python 提速：从直觉到工程实践

> **一句话直觉**：当 Python 代码在关键路径上慢得让你抓狂时，不要急着换语言重写整个项目——把最慢的那 5% 用 Rust 写好，通过 PyO3 暴露成普通 Python 模块，通常就能拿到 10x~100x 的加速，而其余 95% 的 Python 代码原封不动。

---

## 1. 为什么需要 PyO3：Python 的性能天花板

Python 是解释型语言，每个字节码都要经过 CPython 解释器（interpreter）循环调度，还有 GIL（Global Interpreter Lock，全局解释器锁）让多线程无法真正并行执行 CPU 密集任务。纯 Python 的计数循环、数值密集型计算、字符串处理，往往比 C/Rust 慢几十到上百倍。

常见加速方案：
- **Cython / C 扩展**：成熟但语法繁琐，内存安全靠人。
- **NumPy 向量化**：只适用于数组类操作，逻辑复杂的循环无能为力。
- **多进程**：绕过 GIL，但进程间通信（IPC）开销大，状态难共享。
- **Rust + PyO3**：现代、内存安全、无 GIL 限制、工具链好（cargo + maturin），是当下最推荐的“渐进式加速”方案。

**核心洞察**：性能优化要做“局部手术”，而不是“全身换血”。PyO3 让你把 Rust 编译成 `.so`/`.pyd`，Python 里 `import` 即用，接口上完全无感。

---

## 2. PyO3 是什么：Rust 与 Python 的双向桥

PyO3（读作 “pie-oh-three”）是一个 Rust crate（库），它提供：
- 从 Rust 调用 Python 对象（`PyAny`、`PyList`、`PyDict`）。
- 把 Rust 函数/类暴露给 Python（`#[pyfunction]`、`#[pymodule]`、`#[pyclass]`）。
- 自动处理引用计数、异常转换、类型转换。

配合 **maturin**（构建工具），你可以在一个纯 Cargo 工程里写出可被 `pip install` 的 Python 包：

```
my_ext/
├── Cargo.toml
├── pyproject.toml
└── src/
    └── lib.rs
```

构建完直接 `import my_ext`，Python 完全感知不到背后是 Rust。

---

## 3. 第一个 PyO3 模块：斐波那契

先看 Python 版（递归版慢得离谱，这里用循环版作对照）：

```python
# fib_py.py
def fib(n: int) -> int:
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a
```

对应的 Rust 版本（`src/lib.rs`）：

```rust
use pyo3::prelude::*;

/// 计算第 n 个斐波那契数（从 0 开始）
#[pyfunction]
fn fib(n: u64) -> u64 {
    let (mut a, mut b) = (0u64, 1u64);
    for _ in 0..n {
        let t = a + b;
        a = b;
        b = t;
    }
    a
}

/// 模块入口：Python 中 `import my_ext` 后调用 `my_ext.fib(100)`
#[pymodule]
fn my_ext(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(fib, m)?)?;
    Ok(())
}
```

`Cargo.toml`：

```toml
[package]
name = "my_ext"
version = "0.1.0"
edition = "2021"

[lib]
name = "my_ext"
crate-type = ["cdylib"]

[dependencies]
pyo3 = { version = "0.23", features = ["extension-module"] }
```

`pyproject.toml`：

```toml
[build-system]
requires = ["maturin>=1.7,<2.0"]
build-backend = "maturin"

[project]
name = "my_ext"
version = "0.1.0"
requires-python = ">=3.8"
```

编译安装：

```bash
pip install maturin
maturin develop --release   # 开发模式，装进当前 venv
```

Python 端：

```python
import my_ext
print(my_ext.fib(50))   # 12586269025
```

**关键点**：`#[pyfunction]` 把 Rust 函数包装成 Python 可调用的函数，`#[pymodule]` 注册模块。`pyo3` 自动完成 `u64` ↔ Python int 的转换。

---

## 4. 释放 GIL：让 CPU 密集任务真正并行

默认情况下，Rust 代码调用时会持有 GIL，仍然阻止其他 Python 线程执行。但只要函数不碰 Python 对象，就可以用 `Python::allow_threads` 临时释放 GIL，让多个线程真正并行：

```rust
use pyo3::prelude::*;
use pyo3::types::PyModule;

#[pyfunction]
fn heavy_sum(n: u64) -> u64 {
    // 这里不访问任何 Python 对象，可以安全地释放 GIL
    (0..n).map(|x| x.wrapping_mul(x)).sum()
}

#[pyfunction]
fn heavy_sum_parallel(py: Python<'_>, n: u64) -> PyResult<u64> {
    // allow_threads 期间其他 Python 线程可以继续跑
    py.allow_threads(|| Ok(heavy_sum(n)))
}

#[pymodule]
fn my_ext(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(heavy_sum, m)?)?;
    m.add_function(wrap_pyfunction!(heavy_sum_parallel, m)?)?;
    Ok(())
}
```

Python 端用 `concurrent.futures.ThreadPoolExecutor` 跑 4 个任务：

```python
from concurrent.futures import ThreadPoolExecutor
import my_ext, time

def run():
    return my_ext.heavy_sum_parallel(10_000_000)

t0 = time.perf_counter()
with ThreadPoolExecutor(max_workers=4) as ex:
    list(ex.map(lambda _: run(), range(4)))
print(f"elapsed: {time.perf_counter() - t0:.2f}s")
```

对比不释放 GIL 的版本，多线程会退化到串行速度。这是 PyO3 相较于 Cython 的显著优势之一——释放 GIL 只需一行 `py.allow_threads(...)`。

---

## 5. 传数据：NumPy 数组与 Rust 切片

真实场景里最多的是数组运算，用 `numpy` crate（PyO3 的官方 NumPy 绑定）可以零拷贝访问 NumPy 数组：

```rust
use pyo3::prelude::*;
use numpy::PyReadonlyArray1;

/// 对一维 f64 数组求和（零拷贝）
#[pyfunction]
fn sum_array(arr: PyReadonlyArray1<f64>) -> f64 {
    let view = arr.as_array();   // ndarray::ArrayView1
    view.iter().sum()
}

#[pymodule]
fn my_ext(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(sum_array, m)?)?;
    Ok(())
}
```

`Cargo.toml` 中加：

```toml
numpy = "0.23"
```

Python 端：

```python
import numpy as np, my_ext
x = np.random.rand(10_000_000)
print(my_ext.sum_array(x))
```

**要点**：`PyReadonlyArray1<f64>` 只读借用，不复制数据，性能接近原生 Rust。如果想要写回，用 `PyReadwriteArray1<f64>`。

---

## 6. 从 Rust 调 Python：回调和异常

PyO3 是双向的。你可以接受 Python 的 callable 并在 Rust 中调用：

```rust
use pyo3::prelude::*;

#[pyfunction]
fn apply_twice(f: Bound<'_, PyAny>, x: f64) -> PyResult<f64> {
    let y = f.call1((x,))?;       // 调用 f(x)
    let z = f.call1((y,))?;       // 调用 f(y)
    z.extract::<f64>()
}

#[pymodule]
fn my_ext(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(apply_twice, m)?)?;
    Ok(())
}
```

Python 端：

```python
import my_ext
print(my_ext.apply_twice(lambda v: v * 2, 3.0))   # 12.0
```

Rust 中的 `Result::Err` 会自动转换成 Python 异常，用 `PyErr::new::<PyValueError, _>(...)` 可以抛自定义异常。

---

## 7. 工程实践建议

- **先 Profile 再优化**：用 `cProfile`、`py-spy`、`line_profiler` 找到热点，只 Rust 化真正的瓶颈。
- **接口要窄**：一次调用处理一个大任务，而不是每次处理一个元素——减少跨语言调用开销。
- **`--release` 构建**：`maturin develop --release`，否则慢得和 Python 差不多。
- **测试**：Rust 端用 `cargo test`，Python 端用 `pytest`，两边都测。
- **错误处理**：Rust 的 `Result` ↔ Python 的 `Exception` 映射要明确，别吞异常。
- **分发**：`maturin build --release` 产出 wheel，可以像普通包一样发布到 PyPI。

---

## 动手练习

**任务**：给你一个 Python 函数，统计字符串列表里所有字符的总数，并用它处理 100 万条随机字符串。

1. 写一个纯 Python 版（`count_chars_py`），用 `time.perf_counter` 测时间。
2. 用 PyO3 写一个 Rust 版 `count_chars_rs(list: Vec<String>) -> usize`，函数体内用 `list.iter().map(|s| s.len()).sum()`。
3. 用 `maturin develop --release` 编译，比较两版耗时。
4. 尝试进阶：把函数改成接收 Python `list` 后再用 `py.allow_threads` 释放 GIL，用 `ThreadPoolExecutor` 并行处理 4 份数据，看看加速比。

**验收标准**：能拿到一个可 `import` 的扩展模块，并给出两版耗时的对比数据；Rust 版本应至少有 5x 加速。

## py.perf.c_extension

# py.perf.c_extension：让 Python 跑出 C 的速度

## 一句话直觉

当 Python 代码成为性能瓶颈时，**用 C 语言写扩展模块（C Extension）**，把热点逻辑下沉到 C，能拿到 10~100 倍的加速——这是 NumPy、PyTorch、Pandas 等所有高性能库的秘密武器。

学完本讲，你就能理解：为什么 `torch.matmul` 比手写 Python 循环快几千倍，以及如何亲手写一个自己的 C 扩展。

---

## 1. 为什么需要 C 扩展：Python 的“慢”到底慢在哪

Python 是**解释型语言（interpreted language）**，每条字节码（bytecode）都要经过解释器（interpreter）循环分发；同时 Python 对象是高度封装的动态结构（`PyObject`），每次运算都要做类型检查、引用计数（reference counting）、字典查找。结果：一次整数加法的开销可能是 C 的几十倍。

看一个直观的例子：

```python
import time

def py_sum(n):
    s = 0
    for i in range(n):          # 每次循环都是一堆字节码
        s += i * i
    return s

start = time.perf_counter()
py_sum(10_000_000)
print(f"Python 版本: {time.perf_counter() - start:.3f}s")
```

在普通机器上，这段纯 Python 大约要 1 秒左右。而等价 C 代码只要几毫秒。**差距不是 Python 笨，而是每一层抽象都要付费**。C 扩展就是用来“退到抽象底层”，直接和机器对话。

---

## 2. C 扩展的三种落地方式

| 方式 | 特点 | 适用场景 |
|---|---|---|
| **纯 C API**（`Python.h`） | 最底层、最灵活、最啰嗦 | 写核心库、CPython 内部工具 |
| **Cython** | 写 `.pyx`，Cython 编译成 C 再编译 | 用 Python 语法写扩展，最快上手 |
| **cffi / ctypes** | 调用已有 C 动态库，无需编译 | 复用现成 `.so`/`.dll` |

作为起点，我们先用 **ctypes** 感受“调用 C 就是这么快”，再理解底层 C API 的机制。

**用 ctypes 调一段 C 代码（零编译）**：

```python
import ctypes, time

# 直接在 Python 里拿到 libc 的 sqrt 函数
libc = ctypes.CDLL("libc.so.6")   # macOS 上是 libSystem.B.dylib
libc.sqrt.restype = ctypes.c_double
libc.sqrt.argtypes = [ctypes.c_double]

start = time.perf_counter()
for i in range(1_000_000):
    libc.sqrt(i)
print(f"C sqrt x1M: {time.perf_counter() - start:.3f}s")
```

即便每次调用都跨越 Python/C 边界，依然比纯 Python 实现快数倍。

---

## 3. 亲手写一个最小 C 扩展（CPython C API）

C 扩展的本质：**一个 C 函数 + 一张“方法表” + 一个模块定义结构**。

`fastmath.c`：

```c
#define PY_SSIZE_T_CLEAN
#include <Python.h>

/* 计算平方和：Python 传进来的参数在 args 里，返回 Python 对象 */
static PyObject* square_sum(PyObject* self, PyObject* args) {
    long n;
    if (!PyArg_ParseTuple(args, "l", &n))   /* 解析参数 */
        return NULL;                          /* 出错自动抛异常 */

    long long s = 0;
    for (long i = 0; i < n; i++) s += (long long)i * i;

    return PyLong_FromLongLong(s);            /* 打包成 Python int */
}

/* 方法表：告诉 Python 这个模块有哪些函数 */
static PyMethodDef FastMathMethods[] = {
    {"square_sum", square_sum, METH_VARARGS, "计算 0^2+1^2+...+n^2"},
    {NULL, NULL, 0, NULL}
};

/* 模块定义 */
static struct PyModuleDef fastmathmodule = {
    PyModuleDef_HEAD_INIT, "fastmath", NULL, -1, FastMathMethods
};

/* 入口函数，名字必须是 PyInit_<模块名> */
PyMODINIT_FUNC PyInit_fastmath(void) {
    return PyModule_Create(&fastmathmodule);
}
```

`setup.py`：

```python
from setuptools import setup, Extension

setup(
    name="fastmath",
    ext_modules=[Extension("fastmath", ["fastmath.c"])],
)
```

编译并使用：

```bash
python setup.py build_ext --inplace
```

```python
import fastmath, time

start = time.perf_counter()
fastmath.square_sum(10_000_000)
print(f"C 扩展版本: {time.perf_counter() - start:.3f}s")
```

对比第 1 节的纯 Python 版本，你会看到从“秒级”跌到“毫秒级”的直观落差。

---

## 4. 性能之外的三条硬约束

1. **GIL（Global Interpreter Lock）**：C 扩展持有 GIL 才能操作 Python 对象；若你的 C 代码是纯计算，用 `Py_BEGIN_ALLOW_THREADS / Py_END_ALLOW_THREADS` 释放 GIL，才能真正并行。
2. **引用计数（refcount）**：每个 `PyObject*` 都有计数；不返回的对象要 `Py_DECREF`，否则内存泄漏。
3. **跨边界成本**：C 扩展不是越快越好——如果函数体只做一次加法，光是打包/解包参数就比 Python 还慢。**只把热点逻辑下沉**。

工程决策口诀：**profile 先找热点 → 热点用 C/Cython → 边界尽量粗粒度 → 其余留在 Python**。

---

## 5. 现代主流路线：Cython 一步到位

纯 C API 写起来太啰嗦。工程中更常用 **Cython**：用近似 Python 的语法写，编译器生成 C 代码。

`fastmath.pyx`：

```cython
# cython: language_level=3
def square_sum(long n):
    cdef long long s = 0
    cdef long i
    for i in range(n):         # 这里是 C 循环，不是 Python 循环
        s += i * i
    return s
```

配合 `setup.py` 里的 `cythonize("fastmath.pyx")`，一行命令就能得到同等性能、可读性却好得多的扩展。

---

## 6. 一句话总结

> **Python 的便利与 C 的速度不可兼得时，用 C 扩展做“边界”：把 Python 保留为主控层，把热点交给 C。**

这正是 PyTorch 从 `tensor + autograd` 到 `libtorch`（C++ 后端）的架构哲学。


---

## 本课题目

### single_choice · None



- [A] Rust 的语法比 Python 更简洁，便于快速开发
- [B] Rust 可以在不引入 GIL 的情况下执行计算密集任务，从而突破 CPython 单线程限制
- [C] Rust 可以直接替换掉 CPython 解释器，使 Python 代码运行更快
- [D] Rust 编写的扩展模块会自动并行化所有 Python 循环

**参考答案**：1

**解析**：PyO3 允许 Rust 扩展在调用期间释放 GIL，从而让计算密集代码真正多核并行，这是其主要性能优势。A 项与语法简洁性无关；C 项误解为替换解释器；D 项不存在自动并行化。

### single_choice · None



- [A] &str
- [B] Py<PyAny> 或 Bound<'py, PyAny> 等智能指针/句柄类型
- [C] std::rc::Rc<PyObject>
- [D] 拥有所有权的 Vec<u8>

**参考答案**：1

**解析**：PyO3 提供 Py<T>、Bound<'py, T> 等类型来安全持有 Python 对象并管理引用计数。&str 只是借用字符串；Rc 不是 PyO3 的引用计数机制；Vec<u8> 可能用于字节数据但并非通用对象表示。

### single_choice · None



- [A] 返回成功时得到 T 包装的 Python 对象，出错时会抛出对应的 Python 异常
- [B] Rust 的 Result 会被忽略，Python 只能拿到 None
- [C] 必须先在 Python 中 import result 才能接收
- [D] 出错时 Python 进程会直接崩溃

**参考答案**：0

**解析**：PyO3 会把 Ok(T) 转换为对应的 Python 返回值，把 Err(PyErr) 转换为 Python 异常。B、C、D 项都是对错误处理机制的误解。

### single_choice · None



- [A] PyO3 完全不需要编译，直接解释执行
- [B] PyO3 提供更安全的引用计数与类型封装，减少手动 Py_INCREF/Py_DECREF 出错
- [C] PyO3 生成的扩展可以同时在 CPython 和 PyPy 上运行且无需适配
- [D] PyO3 会自动把 Python 代码转为 Rust 重写

**参考答案**：1

**解析**：PyO3 通过 Rust 类型系统与智能指针封装 Python 引用计数，降低 C API 手动管理出错的风险。A、C、D 项均不符合实际。

### single_choice · None



- [A] 在 Rust 中一次批量处理数据后返回
- [B] 在 Rust 循环中反复通过 Python C API 创建小 Python 对象
- [C] 把热点计算放在释放 GIL 的代码块中
- [D] 使用 PyBytes 一次性复制字节数据

**参考答案**：1

**解析**：频繁跨语言边界创建 Python 对象会带来巨大开销，抵消原生代码优势。A、C、D 项都是提高性能的常见做法。

### single_choice · None



- [A] 只要在 Rust 代码里写多线程就自动释放 GIL
- [B] 只有当代码块内不再访问任何 Python 对象时，释放 GIL 才是安全的
- [C] 释放 GIL 后 Rust 代码不能再做任何计算
- [D] 释放 GIL 需要先调用 Python 的 gc.collect

**参考答案**：1

**解析**：释放 GIL 期间不能安全地操作 Python 对象，因此只有在不访问 Python 对象的纯计算段才适合释放。A、C、D 项均不正确。

### single_choice · None



- [A] 作为 Python 运行时依赖，写在 dependencies 下由 pip 安装
- [B] 作为 Rust crate 依赖，写在 [dependencies] 下由 cargo 拉取
- [C] 作为系统库，必须通过 apt 安装
- [D] 作为 CPython 的内置模块，无需声明

**参考答案**：1

**解析**：pyo3 是 Rust crate，通过 Cargo.toml 的 [dependencies] 声明并由 cargo 管理。A 项混淆了 Python 包与 Rust crate；C、D 项错误。

### single_choice · None



- [A] Rust 编译器没有开启优化
- [B] 热点函数并非真正的性能瓶颈，或跨语言调用次数过多导致边界开销占比高
- [C] Python 解释器版本太新，不支持 Rust 扩展
- [D] PyO3 只对数值计算有效，字符串处理无效

**参考答案**：1

**解析**：性能优化应先确认瓶颈，若边界调用频繁或热点定位错误，单次加速不会带来整体收益。A 项可能是次要因素但非首要；C、D 项是错误断言。

### single_choice · None



- [A] 直接返回 Rust HashMap，PyO3 会自动零成本映射为 dict
- [B] 把 HashMap 中的键值逐个插入到 PyDict 中再返回
- [C] 把 HashMap 序列化为字符串返回
- [D] Rust 的 HashMap 无法转换为 Python 对象

**参考答案**：1

**解析**：PyO3 不会零成本自动把 Rust HashMap 映射为 dict，需要在 PyDict 中逐项插入或借助 IntoPy 的相应实现。A 项高估了自动转换；C 项引入不必要序列化；D 项过于绝对。

### single_choice · None



- [A] 扩展模块可以同时在 Windows 和 Linux 上运行而无需分别编译
- [B] 一个扩展 wheel 可以兼容多个 CPython 版本，减少为每个小版本单独构建
- [C] 扩展模块不再需要 GIL
- [D] Python 代码会自动编译为 Rust

**参考答案**：1

**解析**：abi3 提供稳定的受限 API，使一个 wheel 能覆盖多个 CPython 版本，减少构建矩阵。A 项跨操作系统仍需分别构建；C、D 项与该特性无关。

### single_choice · None



- [A] Python 函数调用会自动在 Rust 中并行执行
- [B] 跨语言调用与 GIL 获取有固定开销，频繁调用会显著拖慢程序
- [C] Rust 无法调用 Python 函数，只能被 Python 调用
- [D] 调用 Python 函数必须先把参数转成字符串

**参考答案**：1

**解析**：从 Rust 调回 Python 需要获取 GIL 并跨语言边界，频繁调用开销大。A 项不符；C 项错误，PyO3 支持双向调用；D 项无此要求。

### single_choice · None



- [A] 代码行数很多但几乎不执行
- [B] 代码在性能剖析中占比很高，且是 CPU 密集型、无复杂 Python 对象交互的热点
- [C] 代码频繁调用第三方 Web API
- [D] 代码主要做字符串拼接和日志输出

**参考答案**：1

**解析**：Rust 重写适合 CPU 密集、剖析占比高且跨语言交互少的热点。A 项不影响性能；C 项受 I/O 限制；D 项通常不是计算瓶颈。

### single_choice · None



- [A] #[pymodule]
- [B] #[pyfunction]
- [C] #[pyclass]
- [D] #[pymethods]

**参考答案**：1

**解析**：#[pyfunction] 用于把 Rust 函数包装成 Python 可调用函数；#[pymodule] 标记模块初始化函数；#[pyclass] 标记 Python 类；#[pymethods] 用于类的方法块。

### single_choice · None



- [A] 在 Rust 函数中调用 Python 的 time.sleep
- [B] 使用 Python::allow_threads 释放 GIL 后再执行计算
- [C] 把 Rust 代码编译为 no_std 模式
- [D] 在 Cargo.toml 中开启 parallel 特性

**参考答案**：1

**解析**：Python::allow_threads（或 Python::with_gil 中调用 allow_threads）会释放 GIL，使其他 Python 线程得以运行。A 项反而会阻塞；C 项与 GIL 无关；D 项并非 PyO3 的标准特性开关。

### single_choice · None



- [A] PyO3 扩展模块是纯文本 .py 文件，可直接复制使用
- [B] PyO3 扩展模块需要编译为平台相关的动态库（如 .so/.pyd），再通过 wheel 分发
- [C] PyO3 扩展模块只能在开发机上运行，无法打包分发
- [D] PyO3 扩展模块必须重新编译整个 CPython 解释器

**参考答案**：1

**解析**：PyO3 产出的是编译后的原生扩展，需要针对目标平台编译并打包为 wheel 分发。A 项错误，不是纯文本；C 项错误，可以分发；D 项错误，不需要重编解释器。

### single_choice · None



- [A] requires-python
- [B] build-system 的 requires 和 build-backend 指向 maturin
- [C] dependencies 中列出 pyo3
- [D] tool.setuptools 配置

**参考答案**：1

**解析**：maturin 作为构建后端时，需要在 [build-system] 中把 build-backend 设为 maturin 并在 requires 中声明。requires-python 只是版本约束；pyo3 是 Rust 依赖而非 Python 依赖；setuptools 不是 maturin 的配置。

### single_choice · None



- [A] 逐元素调用 Python 的 int() 构造
- [B] PyBytes::new 或 Bound<PyBytes> 的相关构造方法
- [C] 先把 Vec<u8> 序列化为 JSON 字符串再传给 Python
- [D] 使用 format! 拼接为字符串再编码

**参考答案**：1

**解析**：PyBytes::new（或 Bound 版本）可以一次性把字节切片转为 Python bytes，避免逐元素或字符串中转的开销。A 项逐个构造极慢；C、D 项引入不必要的序列化与编码转换。

### single_choice · None



- [A] 参数必须是 Python 的 None
- [B] 参数可以是任意 Python 对象，由函数内部自行判断类型
- [C] 参数必须是 Python 的 int
- [D] 参数必须是 Rust 原生类型，不能是 Python 对象

**参考答案**：1

**解析**：PyAny 表示任意 Python 对象，Bound 是带生命周期的句柄，因此参数可以是任意对象，需要运行时做类型检查。A、C 项把范围限死；D 项与 PyAny 的含义相反。

### single_choice · None



- [A] #[pyclass] 用于结构体，#[pymethods] 用于方法实现块
- [B] #[pyfunction] 用于结构体，#[pymodule] 用于方法块
- [C] #[pymethods] 用于结构体，#[pyclass] 用于方法块
- [D] #[pymodule] 用于结构体，#[pyfunction] 用于方法块

**参考答案**：0

**解析**：#[pyclass] 标记要暴露给 Python 的 Rust 结构体，#[pymethods] 标记其方法实现块。其余选项把宏的用途张冠李戴。

### single_choice · None



- [A] Rust 编译后的代码自动使用了 GPU 加速
- [B] Rust 代码在计算期间不解释执行，且可释放 GIL 实现并行
- [C] Rust 编译器把 Python 代码也一起优化了
- [D] PyO3 会在运行时把 Python 字节码翻译成 Rust

**参考答案**：1

**解析**：Rust 是编译型语言，没有解释开销，并且配合释放 GIL 可实现多线程并行加速。A、C、D 项均是对编译与加速机制的常见误解。

### single_choice · None



- [A] 用 time.time() 粗略测量整个程序的运行时间，若超过 1 秒就决定用 C 重写
- [B] 用性能分析工具（如 cProfile）定位热点函数，确认瓶颈确实集中在被高频调用的纯 Python 计算上
- [C] 先把所有函数改写为递归形式，再观察内存占用
- [D] 把变量名改短以减少解释器查找字典的开销

**参考答案**：1

**解析**：判断是否需要 C 扩展，必须先定位真正的热点。cProfile 等剖析工具能给出各函数调用次数与累计耗时，确认瓶颈是 CPU 密集的纯 Python 计算后，才有理由考虑用 C 扩展。仅凭总时间长短、改写递归或改变量名都无法可靠判定瓶颈，改短变量名对性能的影响微乎其微。

### single_choice · None



- [A] C 扩展代码运行在 Python 解释器进程内，通过 CPython 提供的 C API 与解释器交互，因此不受 GIL 的影响而能自动并行执行
- [B] C 扩展必须完全重写整个程序，不能在现有 Python 程序中只替换某个函数
- [C] C 扩展可与 Python 代码混用，通常只把关键的少数函数用 C 实现，其余逻辑仍用 Python 编写
- [D] 只要用 C 编写，任何代码都会比 Python 快，无需考虑算法复杂度

**参考答案**：2

**解析**：C 扩展的核心价值是「局部替换」：把热点函数用 C 实现，其余仍用 Python，通过 C API 与解释器交互。C 扩展默认仍持有 GIL，并不会自动并行；也无需重写整个程序；性能提升仍受算法复杂度制约，糟糕的算法用 C 写也不会快。

### multi_choice · None



- [A] 热点是纯 CPU 密集的逐元素数值计算，纯 Python 循环开销明显
- [B] 热点是等待磁盘或网络 I/O，CPU 基本空闲
- [C] 需要复用已有的成熟 C/C++ 库来完成计算
- [D] 需要精细控制内存布局以提升缓存局部性
- [E] 热点函数只被调用一次，耗时 0.1 毫秒

**参考答案**：[0, 2, 3]

**解析**：C 扩展适合 CPU 密集计算、复用已有 C/C++ 库、需要精细内存/缓存控制等场景。I/O 等待瓶颈用 C 重写无法缩短等待时间；只调用一次且极短的函数不是热点，优化收益可忽略。

### multi_choice · None



- [A] 通过 C API 获得「新引用」后，开发者有责任在不再使用时释放它
- [B] 「借用引用」不应被随意释放，除非先正确地增加引用计数
- [C] 对长时间、不触碰 Python 对象的计算，可以显式释放 GIL 以便其他线程运行
- [D] 只要在 C 代码里执行，引用计数就完全由解释器自动管理，开发者无需关心

**参考答案**：[0, 1, 2]

**解析**：C API 区分新引用与借用引用：获得新引用需负责释放，借用引用不应擅自释放。长时间纯计算可显式释放 GIL。引用计数在 C 扩展中并非全自动，正因需要手工配对操作才容易出错，故最后一项错误。

### multi_choice · None



- [A] 解析参数失败（类型不符、数量不对）时应设置异常并返回错误指示
- [B] 返回错误指示前要保证已获取的资源被正确清理，避免泄漏
- [C] 为省事可以忽略解析失败，直接按错误类型读写内存
- [D] 解析成功后才继续业务逻辑，避免在无效指针上操作

**参考答案**：[0, 1, 3]

**解析**：正确做法是：解析失败时设置异常并返回错误指示，返回前清理已获取资源，解析成功后再继续。忽略解析失败并按错误类型读写内存会造成未定义行为，是必须避免的错误实践。

### multi_choice · None



- [A] 每次调用的数据量很小，但 Python 与 C 之间的参数转换开销相对很大
- [B] 热点其实位于另一个已经用 C 实现的库中
- [C] 瓶颈是 I/O 等待而非 CPU 计算
- [D] 热点是大量逐元素纯计算且调用频次很高

**参考答案**：[0, 1, 2]

**解析**：跨语言调用有固定开销，小数据量高频调用时转换开销可能抵消收益；若瓶颈本就在已有的 C 库或 I/O 等待上，替换 Python 层无济于事。相反，高频的逐元素纯计算正是 C 扩展的用武之地，收益明显。

### fill_blank · None



**参考答案**：["GIL", "gil", "Global Interpreter Lock", "全局解释器锁"]

**解析**：该机制是 GIL（Global Interpreter Lock，全局解释器锁）。它保证同一时刻只有一个线程执行 Python 字节码，因此 C 扩展执行长时间计算时若想不阻塞其他线程，需要显式释放 GIL。

### fill_blank · None



**参考答案**：["引用", "reference", "引用计数", "reference count", "refcount"]

**解析**：CPython 的内存管理核心是引用计数。C 扩展通过 C API 操作对象时需手动配对增减引用计数，忘记减少即导致对象无法回收、内存泄漏。

### fill_blank · None



**参考答案**：[".so", "so", ".pyd", "pyd"]

**解析**：C 扩展编译后是平台相关的共享库：Linux/macOS 上通常为 .so，Windows 上为 .pyd。它由打包工具在构建阶段生成，而非源码 .py 文件。

### code_reading · None



**参考答案**：应在步骤1完成、步骤2开始前显式释放 GIL，并在步骤2结束后、步骤3开始前重新获取 GIL。因为步骤2只操作 C 数据、不触碰 Python 对象，释放 GIL 可让其他线程运行；而步骤1和步骤3要访问 Python 对象，必须持有 GIL。

**解析**：GIL 只保护对 Python 对象/解释器状态的访问。步骤2是纯 C 计算，不依赖 GIL，可在其前后成对地释放/重新获取 GIL，从而不阻塞其他线程；步骤1、3涉及 Python 对象操作，必须在持有 GIL 时进行。

### code_reading · None



**参考答案**：存在两个问题：一是解析失败时未设置异常就返回空指针，调用方无法通过异常得知失败原因，会得到难以排查的静默错误；二是对获得的新引用 obj 在使用完毕后没有释放，会造成引用计数泄漏。正确做法是：解析失败时先设置相应异常再返回错误指示；在返回前对不再需要的新引用做释放（减引用计数），并确保异常路径上同样做好清理。

**解析**：C 扩展的错误处理要求：失败时设置异常并返回错误指示，不能让调用方收到「无异常的空结果」。同时必须配对管理引用计数，新引用用完要释放，异常分支也不能漏。

### scenario · None



**解析**：应先确认剖析结论、热点确为 CPU 密集的纯计算；准备阶段确定函数边界与数据形式，评估 Python/C 之间的参数转换开销。改写时注意正确管理引用计数、在纯计算段成对释放/重新获取 GIL、严格处理参数解析失败。改写后用控制变量的基准测试对比，确认收益真实且未引入内存泄漏或崩溃。

### single_choice · None



- [A] 进入 C 扩展后 GIL 会被自动释放，因此 C 扩展天然可以多线程并行
- [B] C 扩展在执行期间默认仍持有 GIL，若要在长时间计算中释放它，需要显式调用释放 GIL 的 API
- [C] C 扩展根本无法访问 Python 对象，因此与 GIL 无关
- [D] 只要 C 扩展不抛出异常，GIL 就会被永久移除

**参考答案**：1

**解析**：CPython 的 C 扩展在调用期间默认持有 GIL。若扩展要执行长时间、不触碰 Python 对象的计算，可以显式释放 GIL 以允许其他线程运行，计算完成后重新获取。GIL 不会因进入 C 代码而自动释放，也不会被永久移除。

### single_choice · None



- [A] 程序立即抛出 SyntaxError
- [B] 内存泄漏，长时间运行后内存占用持续增长
- [C] GIL 被自动关闭
- [D] Python 解释器会把该对象自动转为 C 的栈变量，不产生任何影响

**参考答案**：1

**解析**：CPython 使用引用计数管理内存。在 C 扩展中手动增加引用计数后若未配对减少，对象的引用计数永不归零，导致内存泄漏。C 扩展的引用计数管理是常见易错点，与语法错误、GIL 无关。

### single_choice · None



- [A] 热点函数包含大量逐元素的数值循环，且每轮循环都在做简单算术
- [B] 热点函数主要在做网络请求等待
- [C] 热点函数调用的是另一个已经很慢的第三方 C 库
- [D] 热点函数每次只被调用一次，但参数解析很复杂

**参考答案**：0

**解析**：C 扩展最能加速的是 CPU 密集、逐元素、循环体内的纯计算，因为可避免解释器逐条执行字节码的开销。网络等待属于 I/O 阻塞，C 扩展无法减少等待时间；若瓶颈本在另一个 C 库则替换无益；只调用一次的热点也不是热点。

### single_choice · None



- [A] 称为「序列化」，因为要把对象写成字节流存盘
- [B] 称为「参数解析/类型转换」，若转换失败需正确返回错误而不能让程序崩溃
- [C] 称为「垃圾回收」，因为要释放所有传入对象
- [D] 称为「编译优化」，因为转换在编译期完成

**参考答案**：1

**解析**：C 扩展需要用参数解析工具把 Python 对象转换为 C 类型（如整数、浮点、字符串）。转换可能失败（类型不符、溢出等），此时应设置异常并返回错误指示，否则会引发未定义行为甚至崩溃。这与序列化、垃圾回收、编译期优化无关。

### single_choice · None



- [A] C 扩展不需要编译，直接以 .py 文件形式被导入
- [B] 可以使用标准库中的构建工具（如 setuptools）在打包时编译 C 扩展，生成可导入的扩展模块
- [C] C 扩展只能在 Windows 上编译，Linux 不支持
- [D] C 扩展必须手工逐行汇编，不能用 C 编译器

**参考答案**：1

**解析**：C 扩展需要编译为平台相关的共享库（如 .so / .pyd）后才能被导入。通常借助 setuptools 等构建工具在安装/打包时编译。它不是 .py 文件，也不限平台，更不需要手写汇编。

### single_choice · None



- [A] 只测一次调用所花的时间，取最小值作为结论
- [B] 在相同输入规模与相同运行环境下，多次运行取稳定统计量（如中位数），并确认纯 Python 版本确实受解释器开销拖累
- [C] 把 C 版本和 Python 版本放在不同机器上比较
- [D] 只看代码行数，行数少的就是更快

**参考答案**：1

**解析**：可信的性能对比要求控制变量：相同输入规模、相同环境、多次运行取稳定统计量，并先确认瓶颈确实在解释器开销上。单次测量噪声大，跨机器比较无效，代码行数与性能无必然关系。

### single_choice · None



- [A] 所有其他 Python 线程被阻塞，程序看似卡死
- [B] 解释器会自动把该调用移到后台线程
- [C] GIL 会立刻被销毁，程序退出
- [D] Python 对象会被自动复制一份以避免阻塞

**参考答案**：0

**解析**：GIL 被当前线程长时间持有时，其他需要 GIL 的 Python 线程无法运行，表现为程序卡顿。对这类长时间阻塞调用，扩展应显式释放 GIL 后再执行，完成后再重新获取。解释器不会自动搬移调用或销毁 GIL。

### single_choice · None



- [A] 解释器不再支持异常处理
- [B] 手动管理内存与引用计数不当会导致崩溃或内存泄漏，且调试更困难
- [C] Python 代码将无法再调用该扩展
- [D] 扩展模块不能被打包分发

**参考答案**：1

**解析**：C 扩展把内存/引用计数管理责任交给开发者，出错可能导致段错误、内存泄漏，且调试比纯 Python 困难得多。它仍支持异常、可被 Python 调用、也可打包分发，因此这些不是新增风险。
