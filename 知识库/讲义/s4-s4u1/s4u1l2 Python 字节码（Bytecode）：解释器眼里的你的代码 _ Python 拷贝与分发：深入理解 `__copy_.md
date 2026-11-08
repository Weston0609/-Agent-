# s4u1l2 Python 字节码（Bytecode）：解释器眼里的你的代码 / Python 拷贝与分发：深入理解 `__copy__` 与 `__deepcopy__`

> 来源 `content/lessons/s4u1l2.json`

## py.cpy.bytecode

# Python 字节码（Bytecode）：解释器眼里的你的代码

> **一句话直觉**：你写的 `.py` 源码，CPython 不会直接执行，而是先编译成一串叫“字节码”的中间指令交给虚拟机跑；看懂它，你就能知道一次函数调用、一次属性访问、一次循环，在底层究竟发生了什么。

前置：无。本讲假设你会写基本 Python 函数、列表、循环。

---

## 1. 什么是字节码：从源码到执行的三段式

CPython（Python 的官方实现）执行代码分三步：

1. **编译（compile）**：把 `.py` 源码解析成抽象语法树（AST，Abstract Syntax Tree），再编译成 **代码对象（code object）**，里面装的就是字节码指令序列。
2. **字节码（bytecode）**：一组面向栈的虚拟指令，每条指令 1 字节操作码（opcode）加可能的参数，形如 `LOAD_FAST`、`BINARY_OP`、`RETURN_VALUE`。
3. **虚拟机（VM，Virtual Machine）**：CPython 主循环逐条读取 opcode，在一个“值栈”上 push/pop 执行运算。

字节码不是机器码，也不是 C 代码；它是 CPython 专属的中间表示（IR，Intermediate Representation）。不同 Python 实现（PyPy、Jython）有自己的 IR，所以字节码不能跨实现通用。

```python
# 查看一个函数编译出来的代码对象
import dis

def add(a, b):
    return a + b

code = add.__code__          # 代码对象
print(type(code))            # <class 'code'>
print(code.co_code[:8])      # 原始字节码字节串（bytes）
print(code.co_consts)        # 常量表
print(code.co_varnames)      # 局部变量名表
```

**结论**：函数对象的 `__code__` 属性保存了字节码及所有静态元信息，是一切反汇编（disassemble）的入口。

---

## 2. 用 dis 模块反汇编：人类可读的字节码

`dis` 是标准库自带的 **反汇编器**，把 opcode 翻译成可读文本。

```python
import dis

def add(a, b):
    return a + b

dis.dis(add)
# 输出类似（Python 3.12+）：
#   0 RESUME              0
#   2 LOAD_FAST           0 (a)
#   4 LOAD_FAST           1 (b)
#   6 BINARY_OP           0 (+)
#  10 RETURN_VALUE
```

读法：
- 最左列是**偏移量**（offset），字节为单位。
- 中间是 opcode 名称。
- 右边是参数，例如 `LOAD_FAST 0 (a)` 表示把第 0 号局部变量 `a` 压栈。

执行 `a + b` 的过程：把 `a` 压栈 → 把 `b` 压栈 → `BINARY_OP` 弹出两个值做加法并把结果压栈 → `RETURN_VALUE` 弹出返回。

```python
import dis

def add(a, b):
    return a + b

# 机器友好版本：返回结构化列表
for instr in dis.get_instructions(add):
    print(instr.offset, instr.opname, instr.argval)
```

**结论**：字节码严格遵循“栈式求值”，所有运算都通过一个隐式的值栈（value stack）完成，不存在寄存器。

---

## 3. 几类最常见的指令族

学会识别下面几族，你就能读懂 80% 的反汇编结果：

- **加载/保存变量**：`LOAD_FAST`（局部变量）、`LOAD_GLOBAL`（全局）、`LOAD_ATTR`（属性 `obj.x`）、`STORE_FAST`、`STORE_ATTR`。
- **常量与字面量**：`LOAD_CONST`（数字、字符串、`None`、元组等常量，存在 `co_consts` 里）。
- **运算**：`BINARY_OP`（加、减、乘、比较等，参数区分具体运算）、`UNARY_OP`。
- **控制流**：`JUMP_FORWARD`、`POP_JUMP_IF_FALSE` 等跳转指令；`FOR_ITER` 用于 `for` 循环。
- **调用与返回**：`CALL`（3.11 起用统一的 `CALL` 替代多套旧指令）、`RETURN_VALUE`。

```python
import dis

def demo(x):
    if x > 0:
        y = x * 2
    else:
        y = -x
    return y

dis.dis(demo)
# 你会看到 LOAD_FAST x, LOAD_CONST 0, COMPARE_OP > ...
# 以及两处 JUMP，体现 if/else 的分支结构
```

**结论**：高层语法（`if`、`for`、属性访问）都会**降级**成少数几种栈式指令；控制流由跳转指令表达。

---

## 4. 编译缓存与 .pyc：字节码也会被“存档”

每次 import 一个模块，Python 会把编译结果写入 `__pycache__/xxx.cpython-3xx.pyc`，下次直接读缓存，跳过编译。这就是 `.pyc` 文件就是**序列化的代码对象**。

```python
import py_compile, tempfile, os

src = tempfile.NamedTemporaryFile(suffix='.py', delete=False, mode='w')
src.write('def hello(name):\n    return f"hi {name}"\n')
src.close()

# 显式编译成 .pyc，返回值是生成的文件路径
pyc_path = py_compile.compile(src.name)
print(pyc_path)
print(os.path.getsize(pyc_path), 'bytes')
```

`.pyc` 只与**具体 Python 版本**兼容：3.11 编译的 `.pyc` 不能被 3.12 加载。魔法数字（magic number）头会校验版本。

**结论**：字节码是跨进程复用的产物，`.pyc` 缓存让模块导入更快；但它不是可移植的，实现/版本变了就作废。

---

## 5. 为什么要懂字节码：三个真实工程场景

- **性能调优**：知道 `LOAD_GLOBAL` 比 `LOAD_FAST` 慢，就能理解“把热点函数里的全局变量绑定为局部变量”为什么有效；知道 `for` 循环里 `attr` 访问是 `LOAD_ATTR`，就能理解 `obj.method` 缓存成局部变量为什么提速。
- **调试与反编译**：拿到没有源码的 `.pyc`，可用 `dis`、`uncompyle` 分析逻辑；排查 `SyntaxError`、`ImportError` 时看字节码能定位问题。
- **框架与工具**：`inspect`、`pytest`、`numba`、`torch.compile` 等都在字节码/代码对象层面工作；写元编程、字节码改写工具时，这是基础。

```python
import dis, timeit

def slow():
    total = 0
    for i in range(1000):
        total += len(str(i))   # len 是内置名 -> LOAD_GLOBAL
    return total

def fast():
    total = 0
    _len = len                 # 把内置绑定到局部 -> LOAD_FAST
    for i in range(1000):
        total += _len(str(i))
    return total

print(timeit.timeit(slow, number=2000))
print(timeit.timeit(fast, number=2000))
dis.dis(fast)
# 观察：进入循环后 _len 走 LOAD_FAST，比 slow 里的 LOAD_GLOBAL 少一层查找
```

**结论**：字节码是“源码 → 性能 → 工具”之间的可观测层，掌握它能让你从“会写 Python”升级到“知道 Python 怎么跑”。

---

## 动手练习

**任务**：写一个名为 `analyze.py` 的脚本：

1. 定义两个功能等价的函数：
   - `sum_squares_loop(n)`：用 `for` 循环累加 `i*i`。
   - `sum_squares_comp(n)`：用 `sum(i*i for i in range(n))`。
2. 用 `dis.dis` 分别反汇编两个函数，把输出打印出来。
3. 用 `dis.get_instructions` 统计每个函数各自出现了哪些指令，并打印每个函数里 `CALL`、`LOAD_FAST`、`LOAD_GLOBAL` 的出现次数。
4. 用 `timeit.timeit`（各跑 10000 次，n=100）比较两者耗时，打印结果。
5. 在注释里用两三句话回答：从字节码角度看，为什么其中一个更快？

**验收标准**：脚本能直接 `python analyze.py` 运行，输出反汇编、指令计数和时间对比，注释里给出你的结论。

```python
import dis
import timeit


def sum_squares_loop(n):
    total = 0
    for i in range(n):
        total += i * i
    return total


def sum_squares_comp(n):
    return sum(i * i for i in range(n))


# 1) 反汇编
print('=== sum_squares_loop ===')
dis.dis(sum_squares_loop)
print('\n=== sum_squares_comp ===')
dis.dis(sum_squares_comp)


# 2) 指令计数
def count_ops(func):
    counts = {}
    for instr in dis.get_instructions(func):
        counts[instr.opname] = counts.get(instr.opname, 0) + 1
    return counts


for fn in (sum_squares_loop, sum_squares_comp):
    c = count_ops(fn)
    print(f'\n{fn.__name__}: CALL={c.get("CALL", 0)}, '
          f'LOAD_FAST={c.get("LOAD_FAST", 0)}, '
          f'LOAD_GLOBAL={c.get("LOAD_GLOBAL", 0)}')


# 3) 时间对比
n = 100
reps = 10000
t_loop = timeit.timeit(lambda: sum_squares_loop(n), number=reps)
t_comp = timeit.timeit(lambda: sum_squares_comp(n), number=reps)
print(f'\nloop: {t_loop:.4f}s  comp: {t_comp:.4f}s')
```

## py.cpy.dis

# Python 拷贝与分发：深入理解 `__copy__` 与 `__deepcopy__`

### 一句话直觉

**为什么学它？** 当你写 `a = b` 时，你并没有复制数据，只是给同一个对象起了个别名。学会区分「浅拷贝」和「深拷贝」，并知道如何自定义拷贝行为，是掌握 Python 对象模型、避免踩坑的关键一步。

---

## 1. 从「别名」说起：为什么 `a = b` 不是复制

在 Python 中，变量是**对象的引用**（reference），不是盒子。

```python
# 示例 1：别名陷阱
original = [1, 2, 3]
alias = original          # 这不是复制，只是多了一个名字
alias.append(4)
print(original)           # [1, 2, 3, 4] —— original 也变了！
```

要真正得到一份独立的数据，必须使用 **拷贝（copy）**。Python 标准库提供了 `copy` 模块，其中有两个核心函数：

- `copy.copy(x)` —— **浅拷贝（shallow copy）**
- `copy.deepcopy(x)` —— **深拷贝（deep copy）**

---

## 2. 浅拷贝 vs 深拷贝：一层之差，天壤之别

| 类型 | 行为 | 适用场景 |
|------|------|----------|
| 浅拷贝 | 创建一个新容器，但内部元素仍是原对象的引用 | 内部元素不可变，或你确实想共享 |
| 深拷贝 | 递归复制所有嵌套对象，完全独立 | 嵌套可变结构，需要彻底隔离 |

```python
import copy

# 示例 2：浅拷贝与深拷贝对比
inner = [1, 2, 3]
outer = [inner, 4, 5]

shallow = copy.copy(outer)       # 浅拷贝
shallow[0].append(99)
print(outer)                     # [inner 变了] -> [1, 2, 3, 99], 4, 5]

deep = copy.deepcopy(outer)      # 深拷贝
deep[0].append(777)
print(outer)                     # 不受影响 -> [1, 2, 3, 99], 4, 5]
```

**关键结论**：浅拷贝只复制「最外层」，内部引用依然共享；深拷贝递归复制所有层级。

---

## 3. 拷贝的底层协议：`__copy__` 与 `__deepcopy__`

当你调用 `copy.copy(x)` 时，Python 内部会按以下顺序查找拷贝方法：

1. 如果 `x` 定义了 `__copy__()` 方法 → 调用它。
2. 否则，检查 `x` 是否支持 `__reduce_ex__` / `__reduce__`（pickle 相关）。
3. 否则，对列表/字典等内置类型走默认浅拷贝路径。

对于 `copy.deepcopy(x)`：

1. 如果 `x` 定义了 `__deepcopy__(self, memo)` → 调用它（`memo` 是已拷贝对象的缓存字典，用于处理循环引用）。
2. 否则递归处理。

```python
# 示例 3：自定义 __copy__ 与 __deepcopy__
import copy

class Box:
    def __init__(self, items):
        self.items = items

    def __copy__(self):
        print("调用 __copy__")
        return Box(self.items)            # 浅拷贝：共享 items 列表

    def __deepcopy__(self, memo):
        print("调用 __deepcopy__")
        new_items = copy.deepcopy(self.items, memo)
        new_box = Box(new_items)
        memo[id(self)] = new_box          # 记录映射，避免循环引用死循环
        return new_box

b = Box([1, 2, 3])
shallow = copy.copy(b)
deep = copy.deepcopy(b)
```

**为什么需要自定义？** 当类内部持有不可拷贝的资源（如文件句柄、数据库连接、锁）时，默认深拷贝可能失败或语义不正确，这时需要你自己控制拷贝逻辑。

---

## 4. 循环引用与 `memo` 参数

```python
# 示例 4：循环引用的深拷贝
import copy

a = []
a.append(a)          # a 引用自己

b = copy.deepcopy(a)
print(b is b[0])     # True —— 深拷贝正确保持了循环结构
```

`deepcopy` 的 `memo` 字典记录了「原对象 id → 新对象」的映射，保证：
- 同一对象不会被拷贝多次；
- 循环引用不会导致无限递归。

---

## 5. 分发的含义：为什么叫「拷贝与分发」

在工程中，「分发（dispatch）」指的是：**根据对象的类型或协议，决定调用哪个拷贝实现**。Python 的 `copy` 模块本质上是一个**分发器**：

- 对内置类型（list、dict、set）直接走 C 层快速路径；
- 对自定义类，检查用户是否实现了 `__copy__` / `__deepcopy__`；
- 否则回退到 `__reduce_ex__` 协议。

理解这一点，你就能预测任何对象的拷贝行为，也能在需要时精准地插入自己的实现。

---

## 动手练习

**任务：实现一个可安全拷贝的 `Matrix` 类**

1. 定义 `Matrix` 类，内部用嵌套列表 `self.data` 存储二维整数矩阵。
2. 实现 `__copy__`，使浅拷贝后两个 Matrix 共享同一个 `data` 对象（用 `is` 验证）。
3. 实现 `__deepcopy__(self, memo)`，使深拷贝后 `data` 完全独立，且支持循环引用（在 `memo` 中登记自身）。
4. 写一段测试代码：修改原对象的 `data[0][0]`，验证浅拷贝受影响、深拷贝不受影响。

**提示**：深拷贝内部嵌套列表时调用 `copy.deepcopy(self.data, memo)` 即可，关键是别忘了 `memo[id(self)] = new_obj`。


---

## 本课题目

### single_choice · None



- [A] 它是 Python 源代码被编译后得到的中间表示，由虚拟机逐条解释执行
- [B] 它是 CPU 可直接执行的机器指令，无需解释器参与
- [C] 它是在导入模块时由 C 编译器生成的本地可执行文件
- [D] 它是 Python 源码经过 JIT 编译后缓存到磁盘上的机器码

**参考答案**：0

**解析**：CPython 先将源码编译为字节码（中间表示），再由 CPython 虚拟机逐条解释执行；字节码不是机器码。

### single_choice · None



- [A] 查看模块对应的 .pyc 文件
- [B] 查看模块对应的 .pyo 文件
- [C] 查看模块对应的 .so 文件
- [D] 查看模块对应的 .pyd 文件

**参考答案**：0

**解析**：CPython 会把编译后的字节码保存为 .pyc 文件（pycache 中）。.pyo 是旧版本优化字节码扩展名，.so/.pyd 是二进制扩展模块。

### single_choice · None



- [A] 源码编译为字节码的阶段
- [B] 虚拟机解释执行字节码的阶段
- [C] 模块被垃圾回收的阶段
- [D] import 语句查找模块路径的阶段

**参考答案**：0

**解析**：常量折叠是编译器优化，在生成字节码之前/之中完成，而不是在解释执行或 GC 阶段。

### single_choice · None



- [A] 局部变量通常通过快速局部变量机制（如 LOAD_FAST）访问，全局变量通过名字查找（如 LOAD_GLOBAL）
- [B] 所有变量都通过字典查找，因此局部变量和全局变量访问速度完全相同
- [C] 局部变量访问必须先查全局字典，再查局部字典
- [D] 全局变量访问使用 LOAD_FAST，局部变量访问使用 LOAD_GLOBAL

**参考答案**：0

**解析**：CPython 局部变量有专门的快速访问指令，全局/属性访问涉及名字查找或字典查找，速度不同。

### single_choice · None



- [A] 可调用对象以及已经压入栈中的参数
- [B] 仅函数名字符串，参数从源码中重新解析
- [C] 仅字节码行号，参数从磁盘上的 .pyc 读取
- [D] 仅返回地址，参数由操作系统寄存器传递

**参考答案**：0

**解析**：CPython 虚拟机基于栈，调用前会把可调用对象和参数压栈，CALL 指令消费这些栈元素。

### single_choice · None



- [A] 该模块已经在当前进程中导入过，sys.modules 中保留了旧模块对象，不会重新执行源码
- [B] 解释器把 .py 文件编译成了机器码并缓存，源码修改无效
- [C] Python 不允许重复导入同一模块，必须重启操作系统
- [D] 字节码文件 .pyc 被设置为只读，导致源码无法生效

**参考答案**：0

**解析**：已导入模块保存在 sys.modules 中，重复 import 不会重新执行；需要重新加载或重启进程。

### single_choice · None



- [A] 每个正在执行的函数调用通常对应一个栈帧，用于保存局部变量和求值栈等信息
- [B] 所有函数调用共享同一个栈帧，因此局部变量会互相覆盖
- [C] 栈帧只在编译阶段存在，运行时不存在
- [D] 栈帧只保存函数名，不保存任何局部变量

**参考答案**：0

**解析**：CPython 运行时为每个调用创建帧对象，保存局部变量、求值栈、指令指针等；帧不是编译期概念，也不会所有调用共享。

### single_choice · None



- [A] 解释器循环不断取出下一条字节码指令并执行相应操作
- [B] 解释器循环把字节码一次性全部翻译成机器码后再执行
- [C] 解释器循环只在程序启动时运行一次，之后不再参与执行
- [D] 解释器循环负责把机器码反向翻译成字节码

**参考答案**：0

**解析**：CPython 的核心是一个取指-执行循环，逐条处理字节码指令；它不一次性全部翻译成机器码。

### single_choice · None



- [A] 不合理，字节码仍需要对应的 CPython 虚拟机来执行
- [B] 合理，字节码就是机器码，可被操作系统直接加载
- [C] 合理，只要把 .pyc 文件复制过去即可，无需其他依赖
- [D] 不合理，因为字节码只能被 C 编译器执行

**参考答案**：0

**解析**：字节码是中间表示，必须由对应版本的 CPython 解释器执行；它不是机器码，也不能脱离解释器运行。

### single_choice · None



- [A] 优化级别可能影响是否生成断言相关的字节码，从而改变程序行为
- [B] 优化级别会把所有全局名字查找改成 C 函数调用
- [C] 优化级别会把字节码转换为 LLVM IR 并生成原生代码
- [D] 优化级别只改变 .pyc 文件扩展名，不影响字节码内容

**参考答案**：0

**解析**：例如 -O 会忽略 assert 语句，影响生成的字节码；CPython 的标准 -O 并不会生成原生代码或改用 LLVM。

### single_choice · None



- [A] 不准确，字节码仍需逐条解释执行，性能提升通常来自避免重复编译而非运行期加速
- [B] 准确，因为字节码已经是机器码，执行时没有任何翻译开销
- [C] 准确，因为字节码把 Python 动态类型变成了静态类型
- [D] 不准确，因为字节码比源码更大，执行一定更慢

**参考答案**：0

**解析**：生成字节码主要节省导入时的编译开销，运行时仍需解释执行；它不会把动态类型静态化，也不保证更快。

### single_choice · None



- [A] C 扩展模块编译为本地机器码，被调用时不一定经过 Python 字节码解释
- [B] C 扩展模块必须先编译成 Python 字节码才能被导入
- [C] C 扩展模块的字节码会被保存在 .pyc 文件中
- [D] C 扩展模块不能与字节码解释器共存于同一进程

**参考答案**：0

**解析**：C 扩展是本地机器码，调用时直接进入 C 函数；它们不会先变成 Python 字节码，也不会存为 .pyc。

### single_choice · None



- [A] 不准确，CPython 会先把源码编译为字节码，再由虚拟机执行字节码
- [B] 准确，CPython 逐字符读取源码并直接执行，不产生任何中间形式
- [C] 不准确，CPython 会先把源码编译为机器码，再直接运行机器码
- [D] 准确，但只对 .pyc 文件成立，对 .py 文件不成立

**参考答案**：0

**解析**：CPython 的流程是源码 -> 字节码 -> 虚拟机解释执行，因此「逐行读源码执行」的说法不准确。

### single_choice · None



- [A] 函数对象持有对代码对象（code object）的引用，代码对象中包含该函数的字节码
- [B] 函数对象直接保存机器码，调用时跳转到机器码入口
- [C] 函数对象在每次调用时重新把源码编译为字节码
- [D] 函数对象只保存参数数量和名字，字节码统一存放在解释器全局表中

**参考答案**：0

**解析**：函数对象引用 code object，code object 包含字节码、常量、变量名等信息；字节码不是每次调用时重新生成。

### single_choice · None



- [A] 缓存编译结果，避免每次导入模块时重新编译源码
- [B] 把 Python 程序打包成可独立运行的可执行文件
- [C] 对源码进行加密，使他人无法阅读源代码
- [D] 把字节码转换为 C 源码，以便用 C 编译器优化

**参考答案**：0

**解析**：.pyc 只是编译缓存，加速模块导入；它不用于打包、加密，也不会转成 C。

### single_choice · None



- [A] 源文件被修改，其修改时间或大小与 .pyc 中记录的不一致
- [B] 解释器版本号中的补丁号发生变化
- [C] 该模块被 import 了两次以上
- [D] 该模块中定义的函数被调用次数超过阈值

**参考答案**：0

**解析**：CPython 通过比较源文件元数据判断缓存是否失效；重复导入或函数调用次数不会直接触发重新编译。

### single_choice · None



- [A] 操作码（opcode）或指令名
- [B] 机器指令助记符
- [C] AST 节点类型名
- [D] C 函数名

**参考答案**：0

**解析**：这些是字节码指令的操作码名称，不是 CPU 机器指令、AST 节点类型名或 C 函数名。

### single_choice · None



- [A] 使用标准库 dis 模块对函数进行反汇编
- [B] 使用 sys.getsizeof 查看函数对象大小
- [C] 使用 inspect.getsource 打印函数源码
- [D] 使用 gc.get_objects 列出所有对象

**参考答案**：0

**解析**：dis 模块提供字节码反汇编功能；其余选项分别与对象大小、源码查看、对象枚举有关。

### single_choice · None



- [A] 不同 Python 主/次版本之间字节码不保证兼容，.pyc 通常带有版本标记
- [B] 字节码在所有 Python 3 版本之间完全兼容，可跨版本直接使用
- [C] 字节码与 Python 2 和 Python 3 完全兼容
- [D] 字节码由操作系统决定，与 Python 版本无关

**参考答案**：0

**解析**：CPython 字节码随版本变化，.pyc 带有 magic number 等标记，不同版本不保证兼容。

### single_choice · None



- [A] 源码要先通过解析和编译阶段，才能得到对应的字节码
- [B] 字节码直接由词法分析器逐字符产生，不经过语法树
- [C] 任何 Python 语法结构都对应唯一的单条字节码指令
- [D] 字节码中保留了完整的源码注释信息

**参考答案**：0

**解析**：CPython 编译流程通常包括词法/语法分析与编译，生成字节码；复杂语法会对应多条指令，注释也不会保留在字节码中。

### single_choice · None



- [A] copy.copy(x) 只复制对象的顶层，嵌套的可变对象仍共享引用；copy.deepcopy(x) 递归复制所有层级
- [B] copy.copy(x) 递归复制所有层级；copy.deepcopy(x) 只复制顶层
- [C] 两者完全相同，只是函数名不同
- [D] copy.copy(x) 只能用于不可变对象，copy.deepcopy(x) 只能用于可变对象

**参考答案**：0

**解析**：浅拷贝（copy.copy）只复制最外层容器，内部嵌套对象仍是共享引用；深拷贝（copy.deepcopy）会递归复制所有嵌套对象，因此两者在嵌套可变对象上的行为不同。

### single_choice · None



- [A] 浅拷贝和深拷贝都会产生完全不同的新对象
- [B] 浅拷贝和深拷贝通常返回同一个对象或等价内容，因为不可变对象的内部不可被修改
- [C] 深拷贝会报错，因为不可变对象不支持深拷贝
- [D] 浅拷贝会修改原对象，深拷贝不会

**参考答案**：1

**解析**：不可变对象的内容不会被原地修改，因此浅拷贝和深拷贝在很多情况下返回的对象与原对象等价，甚至可能返回同一个对象。深拷贝并不会因为对象不可变而报错。

### multi_choice · None



- [A] 对象内部只有不可变数据
- [B] 只需要复制顶层容器，嵌套对象共享是期望行为
- [C] 性能敏感且不需要完全独立的副本
- [D] 需要修改嵌套可变对象且不影响原对象

**参考答案**：[0, 1, 2]

**解析**：浅拷贝适用于内部不可变、共享嵌套对象可接受、性能敏感的场景；若需要修改嵌套对象且不影响原对象，则应使用深拷贝。

### fill_blank · None



**参考答案**：["copy, deepcopy", "copy,deepcopy"]

**解析**：copy.copy 进行浅拷贝，copy.deepcopy 进行深拷贝。

### fill_blank · None



**参考答案**：["memo", "memoization", "备忘录"]

**解析**：deepcopy 使用 memo 字典缓存已复制对象，处理循环引用。

### code_reading · None



**参考答案**：[[1, 2, 99], [3, 4]]
2 3

**解析**：浅拷贝后 b 与 a 共享内层列表，修改 b[0] 会影响 a；但 b.append 只修改 b 本身，不影响 a。因此 a 变为 [[1, 2, 99], [3, 4]]，长度分别为 2 和 3。

### code_reading · None



**参考答案**：[1, [2, 3]]
[100, [2, 3, 4]]

**解析**：深拷贝后 b 与 a 完全独立，修改 b 不会影响 a，因此 a 保持不变。

### code_reading · None



**参考答案**：对于不可变对象元组，浅拷贝和深拷贝都可能返回原对象本身，因此 a is b 和 a is c 都为 True。

**解析**：元组不可变，内部元素也不可变，copy 模块对这类对象通常会直接返回原对象以避免不必要的复制。

### scenario · None



**解析**：因为需要修改嵌套字段且不影响原配置，浅拷贝会共享嵌套引用导致默认配置被修改，因此必须使用深拷贝保证嵌套层完全独立。

### scenario · None



**解析**：列表内部只有不可变数据，浅拷贝即可保证安全性，且比深拷贝更快，适合性能敏感场景。

### scenario · None



**解析**：可以在类中实现 __deepcopy__(self, memo) 方法，手动控制深拷贝行为，对不可序列化属性跳过或不复制。

### scenario · None



**解析**：可以分析哪些部分真正需要深拷贝，对不可变部分使用浅拷贝或共享引用，或通过 __deepcopy__ 自定义减少不必要的递归复制。

### single_choice · None



- [A] [[1, 2], [3, 4]]
- [B] [[1, 2, 99], [3, 4]]
- [C] [[1, 2], [3, 4, 99]]
- [D] 报错，因为浅拷贝后不能修改嵌套列表

**参考答案**：1

**解析**：浅拷贝只复制外层列表，内层子列表仍与原列表共享引用，因此修改 b[0] 会同时影响 a[0]，输出 [[1, 2, 99], [3, 4]]。

### single_choice · None



- [A] [[1, 2, 99], [3, 4]]
- [B] [[1, 2], [3, 4]]
- [C] [[1, 2], [3, 4, 99]]
- [D] 报错

**参考答案**：1

**解析**：深拷贝会递归复制所有嵌套对象，b 与 a 完全独立，修改 b 不会影响 a，因此 a 保持原样。

### single_choice · None



- [A] 深拷贝遇到循环引用会无限递归并导致栈溢出
- [B] 深拷贝无法处理循环引用，会直接报错
- [C] 深拷贝通过 memo 字典记录已复制对象，能够正确处理循环引用
- [D] 只有浅拷贝才能处理循环引用

**参考答案**：2

**解析**：深拷贝内部使用 memo 字典缓存已复制对象，遇到循环引用时直接返回缓存结果，避免无限递归。

### single_choice · None



- [A] copy.deepcopy(obj)
- [B] list(obj) 或 obj.copy()
- [C] pickle.loads(pickle.dumps(obj))
- [D] json.loads(json.dumps(obj))

**参考答案**：1

**解析**：list(obj)、obj.copy()、切片等只复制顶层，属于浅拷贝；deepcopy、pickle、json 序列化反序列化通常会生成深拷贝效果。

### single_choice · None



- [A] 不会影响原实例，因为浅拷贝会复制属性
- [B] 会影响原实例，因为列表属性是共享引用
- [C] 只会影响原实例的类属性，不影响实例属性
- [D] 取决于列表长度

**参考答案**：1

**解析**：浅拷贝不会复制属性所指向的对象，只复制引用，因此副本和原实例的列表属性指向同一个列表，修改会互相影响。

### single_choice · None



- [A] 只复制对象的 __dict__ 引用
- [B] 递归地深拷贝对象的属性，除非对象定义了 __deepcopy__ 方法
- [C] 调用对象的 __init__ 重新构造
- [D] 报错，因为自定义对象不支持深拷贝

**参考答案**：1

**解析**：默认情况下 deepcopy 会递归复制对象的属性；如果对象实现了 __deepcopy__，则优先使用该方法。

### multi_choice · None



- [A] list(a)
- [B] a.copy()
- [C] copy.copy(a)
- [D] copy.deepcopy(a)

**参考答案**：[0, 1, 2]

**解析**：list(a)、a.copy()、copy.copy(a) 都只复制顶层，属于浅拷贝；copy.deepcopy(a) 是深拷贝。

### multi_choice · None



- [A] 深拷贝会递归复制嵌套的可变对象
- [B] 深拷贝可以正确处理循环引用
- [C] 深拷贝一定比浅拷贝快
- [D] 对不可变对象深拷贝可能返回原对象

**参考答案**：[0, 1, 3]

**解析**：深拷贝递归复制、能处理循环引用、对不可变对象可能返回原对象；但它通常比浅拷贝慢，因此“一定更快”错误。
