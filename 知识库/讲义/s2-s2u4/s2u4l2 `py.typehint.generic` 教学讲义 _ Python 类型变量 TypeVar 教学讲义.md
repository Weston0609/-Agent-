# s2u4l2 `py.typehint.generic` 教学讲义 / Python 类型变量 TypeVar 教学讲义

> 来源 `content/lessons/s2u4l2.json`

## py.typehint.generic

# `py.typehint.generic` 教学讲义

## 一句话直觉

泛型（Generic）就是给“类型”留一个参数位：`list[int]`、`dict[str, User]` 里的方括号，让同一套代码在保持类型安全的前提下适配不同的具体类型。

## 为什么要学它

写库、写业务模型、写异步任务时，你会反复遇到“这个容器/函数/类装的是什么类型？”的问题。泛型让静态类型检查器（mypy、pyright）替你回答这个问题，从而在运行前发现错误。它不是语法糖，而是现代 Python 工程化的基础设施。

---

## 1. 从“具体类型”到“类型参数”

最朴素的想法是给每个类型都写一份函数，例如 `first_int(xs: list[int]) -> int`、`first_str(xs: list[str]) -> str`。泛型把这个“具体类型”抽象成一个类型变量（TypeVar，类型变量），让函数只写一次。

```python
from typing import TypeVar

# T 是一个类型变量，使用时由调用方决定是 int、str 还是别的类型
T = TypeVar("T")

def first(xs: list[T]) -> T:
    return xs[0]

reveal_type(first([1, 2, 3]))      # list[int]  ->  int
reveal_type(first(["a", "b"]))    # list[str]  ->  str
```

关键结论：`T` 本身不是“任意类型”`Any`，而是一个占位符；同一个 `T` 在签名里出现多次，就表示“输入和输出是同一个具体类型”。

---

## 2. 用户自定义泛型类（PEP 695 新语法）

Python 3.12 起，可以直接在类名后写 `[T]` 定义泛型类，不需要再显式继承 `Generic`。类内部的 `T` 会作为该类的类型参数生效。

```python
class Box[T]:
    def __init__(self, value: T) -> None:
        self.value = value

    def get(self) -> T:
        return self.value

b = Box(123)
reveal_type(b.get())          # int
s = Box("hello")
reveal_type(s.get())          # str
```

关键结论：`Box[int]`、`Box[str]` 是同一个类在运行时的“参数化视图”；类体内部的 `T` 会被替换成具体类型参与静态检查。旧代码（Python ≤3.11）通过 `class Box(Generic[T])` 表达同样的语义，二者等价。

---

## 3. 标准库里的泛型：容器、迭代器、协程

标准库的 `list`、`dict`、`Iterable`、`Iterator`、`Coroutine` 全部是泛型。理解它们的参数含义，就能读懂绝大多数类型签名。

```python
from collections.abc import Iterable, Iterator, Coroutine

# Iterable[T] 表示“可迭代出 T 的东西”
def total(xs: Iterable[int]) -> int:
    return sum(xs)

# Iterator[T] 表示“既能迭代又支持 next() 的迭代器”
def counter() -> Iterator[int]:
    yield from range(3)

# Coroutine[Yield, Send, Return] 三参数分别对应 yield / send / return
async def make_coro() -> Coroutine[list[str], str, int]:
    ...
```

关键结论：异步函数用 `AsyncGenerator[YieldType, SendType]`、`AsyncIterator[T]`、`Coroutine[Y, S, R]` 标注；泛型参数越多，类型信息越精确。

---

## 4. 泛型别名与参数约束

用 `type` 语句（Python 3.12+）可以给泛型起别名，并用 `bound` 或元组形式约束类型参数，让类型检查更严格。

```python
from collections.abc import Iterable

# 泛型别名：Response[str] 等价于 Iterable[str] | int
type Response[S] = Iterable[S] | int

def handle() -> Response[str]:
    return ["a", "b"]

# 约束：T 只能是 int / float / complex
def dot[T: (int, float, complex)](xs: list[T], ys: list[T]) -> T:
    return sum(x * y for x, y in zip(xs, ys))
```

关键结论：约束（constraint）用元组 `(int, float)` 表达，上界（bound）用 `T: SomeBase` 表达。它们防止泛型被“乱用”，把错误提前到静态检查阶段。

---

## 5. 旧语法对照与 `Any` 的边界

在 Python 3.11 及更早版本中，泛型必须显式继承 `Generic[T]`，并用 `TypeVar` 声明变量。理解旧写法对阅读遗留代码至关重要。

```python
from typing import TypeVar, Generic, Any

T = TypeVar("T")

class OldBox(Generic[T]):
    def __init__(self, value: T) -> None:
        self.value = value

a: Any = 1
a = "now a string"        # Any 可以赋任意值
def foo(x: Any) -> None:
    x.anything()          # 静态检查不报错——Any 会“短路”检查
```

关键结论：`Any` 是类型系统的逃生舱，用多了会失去泛型带来的保护；`Generic[T]` 与 `class C[T]` 语义一致，只是语法年代不同。

```python
from typing import TypeVar, Generic, Any
from collections.abc import Iterable, Iterator, Coroutine

# ---------- 旧语法：显式 Generic ----------
T = TypeVar("T")

class OldBox(Generic[T]):
    def __init__(self, value: T) -> None:
        self.value = value
    def get(self) -> T:
        return self.value

# ---------- 新语法：PEP 695 ----------
class NewBox[T]:
    def __init__(self, value: T) -> None:
        self.value = value
    def get(self) -> T:
        return self.value

# ---------- 泛型函数与约束 ----------
def first(xs: list[T]) -> T:
    return xs[0]

def dot[T: (int, float, complex)](xs: list[T], ys: list[T]) -> T:
    return sum(x * y for x, y in zip(xs, ys))

# ---------- 标准库泛型 ----------
def total(xs: Iterable[int]) -> int:
    return sum(xs)

def counter() -> Iterator[int]:
    yield from range(3)

# ---------- 泛型别名 ----------
type Response[S] = Iterable[S] | int

def handle() -> Response[str]:
    return ["a", "b"]

# ---------- 运行 ----------
if __name__ == "__main__":
    print(OldBox(1).get())            # 1
    print(NewBox("hi").get())         # hi
    print(first([10, 20, 30]))        # 10
    print(dot([1, 2], [3, 4]))        # 11
    print(total([1, 2, 3]))           # 6
    print(list(counter()))            # [0, 1, 2]
    print(list(handle()))             # ['a', 'b']

    # Any 的“短路”效果：静态检查不报错
    a: Any = 1
    a = "string"
    def foo(x: Any) -> None:
        x.whatever()
```

## py.typehint.typevar

# Python 类型变量 TypeVar 教学讲义

## 一句话直觉

`TypeVar` 是 Python 类型系统中用来表达“**同一个类型在多个位置保持一致**”的工具——它让类型检查器（type checker）能推断出“输入是什么类型，输出就是什么类型”，而不是把类型写死成 `Any`。

---

## 1. 为什么需要 TypeVar：从“丢失类型”说起

假设你写了一个函数，接收一个列表，返回列表的第一个元素。如果不用 `TypeVar`，你只能这样标注：

```python
from typing import Any

def first(l: list[Any]) -> Any:
    return l[0]
```

这样写的问题在于：类型检查器完全不知道返回值和输入元素类型之间的关系。你传入 `list[int]`，它只知道返回 `Any`，后续代码里对返回值做 `+ 1` 它不会报错，做 `.upper()` 它也不会报错——类型信息在这里断掉了。

我们真正想表达的是：“如果输入是 `list[int]`，输出就是 `int`；如果输入是 `list[str]`，输出就是 `str`。”这种“类型与类型之间的绑定关系”，就是 **泛型（generics）** 的核心，而 `TypeVar` 就是泛型的参数。

---

## 2. TypeVar 的基本用法

`TypeVar` 用来声明一个“类型变量”，它代表一个尚未确定的类型，会在调用时被具体类型替换。

传统写法（Python 3.11 及以前，仍然完全有效）：

```python
from typing import TypeVar

T = TypeVar('T')  # 声明一个类型变量 T
```

Python 3.12 起，推荐使用新的 **类型参数语法（type parameter syntax）**，直接写在函数或类名后面的方括号里：

```python
# Python 3.12+
def first[T](l: list[T]) -> T:
    return l[0]
```

两种写法等价。新语法更简洁，而且类型检查器会自动推断 **型变（variance）**，稍后会讲。

关键点：`TypeVar` 本身是给**静态类型检查器**（如 mypy、pyright）看的。运行时 `isinstance(x, T)` 会直接抛出 `TypeError`。

---

## 3. 三种 TypeVar：无约束、有界、受限

`TypeVar` 有三种形态，语义差别非常大，这是最容易混淆的部分。

### 3.1 无约束 TypeVar

```python
T = TypeVar('T')  # 可以是任何类型

def identity[T](x: T) -> T:
    return x
```

调用 `identity(42)` 返回 `int`，调用 `identity("hi")` 返回 `str`。类型检查器按“最具体的实际类型”来解。

### 3.2 有界 TypeVar（bounded）

用 `bound=` 指定一个**上界**，表示“必须是这个类型或其子类型”：

```python
S = TypeVar('S', bound=str)   # 老式写法
# 或新语法：
def print_capitalized[S: str](x: S) -> S:
    print(x.capitalize())
    return x
```

有界 TypeVar 的求解规则是：**用最具体的类型**。

```python
class StringSubclass(str):
    pass

x = print_capitalized("a")                 # x 推断为 str
y = print_capitalized(StringSubclass("b")) # y 推断为 StringSubclass
```

上界可以是具体类、抽象基类（ABC）、Protocol，甚至联合类型：

```python
U = TypeVar('U', bound=str | bytes)
```

### 3.3 受限 TypeVar（constrained）

用位置参数列出**若干个具体候选类型**，表示“只能是其中之一”：

```python
A = TypeVar('A', str, bytes)  # 老式写法
# 或新语法：
def concatenate[A: (str, bytes)](x: A, y: A) -> A:
    return x + y
```

受限 TypeVar 的求解规则是：**收缩到候选类型本身，而不是具体子类**。

```python
a = concatenate('one', 'two')
# a 的类型是 str，而不是某个 str 子类

b = concatenate(StringSubclass('one'), StringSubclass('two'))
# 依然是 str！受限 TypeVar 不会保留子类信息

concatenate('one', b'two')  # 类型错误：一次调用中必须同为 str 或同为 bytes
```

**核心区别一句话总结**：有界用“最具体”，受限用“候选之一，且全程一致”。

一个重要限制：**一个 TypeVar 不能同时既有 bound 又有 constraints**。

---

## 4. 型变（Variance）：协变、逆变、不变

型变描述的是“子类型关系在泛型容器中如何传递”。

- **不变（invariant）**：`A` 是 `B` 的子类型，但 `list[A]` 和 `list[B]` 没有子类型关系。手动创建的 `TypeVar` 默认就是这个。
- **协变（covariant）**：子类型关系同向传递。`Sequence` 就偏向协变——`Sequence[A]` 可以当作 `Sequence[B]` 用。
- **逆变（contravariant）**：子类型关系反向传递。典型是“函数参数”位置。

手动创建时：

```python
T_co = TypeVar('T_co', covariant=True)
T_contra = TypeVar('T_contra', contravariant=True)
```

用新式类型参数语法（或 `infer_variance=True`）时，类型检查器会**自动推断**型变，你一般不需要手动指定。初学者建议：**能用新语法就用新语法，不要手写型变**。

---

## 5. TypeVar 在泛型类中的应用

泛型类同样依赖 TypeVar。新式写法：

```python
class LoggedVar[T]:
    def __init__(self, value: T, name: str) -> None:
        self.value = value
        self.name = name

    def get(self) -> T:
        return self.value

    def set(self, new: T) -> None:
        self.value = new
```

老式写法（兼容 3.11 及以前）：

```python
from typing import TypeVar, Generic

T = TypeVar('T')

class LoggedVar(Generic[T]):
    ...
```

几个工程细节：

- 每个 `Generic[...]` 参数必须是不同的 TypeVar。`class Pair[T, T]:` 是语法错误。
- 泛型类可以继承其他类，只固定部分参数：`class MyDict[T](Mapping[str, T]): ...`。
- 不写类型参数就使用泛型类，等价于每个位置填 `Any`。

---

## 6. 动手练习

**任务：实现一个类型安全的 `Stack`（栈）泛型类。**

要求：

1. 使用 Python 3.12+ 的 `class Stack[T]:` 新式语法（如果你用旧版本，用 `Generic[T]` 的写法也行）。
2. 实现 `push(item: T) -> None`、`pop() -> T`、`peek() -> T`、`__len__() -> int` 四个方法。
3. 再写一个泛型函数 `first_or_default[T](items: list[T], default: T) -> T`，返回第一个元素，空列表时返回 `default`。
4. 写一个 `bounded` 版本的函数 `describe[S: str](x: S) -> str`：返回 `f"{x} has length {len(x)}"`。
5. 用 mypy 或 pyright 检查：
   - `Stack[int]().push("hi")` 应该报错。
   - `first_or_default([], 0)` 推断为 `int`。
   - `first_or_default([1, 2], "x")` 应该报错。

**加分题**：把 `Stack` 改成 `Stack[A: (int, str)]`，观察受限 TypeVar 与有界 TypeVar 在类型推断上的差异。

**验收标准**：类型检查器零报错，且能复现上面三条例外情况。

```python
from collections.abc import Sequence

# ---------- 1. 新式类型参数语法（Python 3.12+）----------
def first[T](l: Sequence[T]) -> T:
    """返回序列的第一个元素，保留元素的具体类型。"""
    return l[0]

# ---------- 2. 受限 TypeVar ----------
def concatenate[A: (str, bytes)](x: A, y: A) -> A:
    """拼接两个同为 str 或同为 bytes 的对象。"""
    return x + y

# ---------- 3. 有界 TypeVar ----------
class StringSubclass(str):
    pass

def print_capitalized[S: str](x: S) -> S:
    """打印首字母大写，并原样返回（保留具体子类型）。"""
    print(x.capitalize())
    return x

# ---------- 4. 泛型类 ----------
class Stack[T]:
    def __init__(self) -> None:
        self._items: list[T] = []

    def push(self, item: T) -> None:
        self._items.append(item)

    def pop(self) -> T:
        return self._items.pop()

    def peek(self) -> T:
        return self._items[-1]

    def __len__(self) -> int:
        return len(self._items)

if __name__ == "__main__":
    print(first([1, 2, 3]))                 # 1
    print(first(["a", "b"]))               # a
    print(concatenate("one", "two"))       # onetwo
    print(concatenate(b"one", b"two"))     # b'onetwo'

    s: Stack[int] = Stack()
    s.push(10)
    s.push(20)
    print(s.peek(), len(s), s.pop())        # 20 2 20

    y = print_capitalized(StringSubclass("hello"))
    print(type(y).__name__)                 # StringSubclass
```


---

## 本课题目

### single_choice · None



- [A] Box 是一个只能存放 int 的普通类，不能存放其他类型
- [B] Box[int] 创建了一个新的子类，其类型参数被绑定为 int
- [C] Box[int] 表示一个类型，其中泛型参数 T 被具体化为 int，供类型检查器理解
- [D] Box[int] 会在运行时把 value 强制转换为 int

**参考答案**：2

**解析**：泛型下标 Box[int] 是给类型检查器的类型信息，表示 T 被具体化为 int；运行时不会创建新类，也不会做强制转换。选项 A 错在泛型不限制运行时；B 错在下标不创建子类；D 错在类型注解不做运行时转换。

### single_choice · None



- [A] T = TypeVar('T', int, str)
- [B] T = TypeVar('T')
- [C] T = TypeVar('T', bound=int)
- [D] T = TypeVar('T', covariant=True)

**参考答案**：1

**解析**：不带约束的 TypeVar 表示任意类型，但在同一次调用中会被推断为同一个具体类型，因此两个参数类型必须一致。A 把 T 限制为 int 或 str；C 限制为上界 int 及其子类；D 的 covariant 用于定义泛型类时的型变，不是用来表示任意类型。

### single_choice · None



- [A] List[int] 只在运行时有效，list[int] 只在类型检查时有效，二者不兼容
- [B] List[int] 是旧式写法，list[int] 是 Python 3.9+ 支持的内置泛型写法，二者语义等价
- [C] list[int] 表示一个只含一个整数的列表，而 List[int] 表示任意长度
- [D] List[int] 表示列表里可以放 int 或 None，而 list[int] 只允许 int

**参考答案**：1

**解析**：从 typing 导入的 List[int] 与 3.9+ 内置的 list[int] 都表示元素为 int 的列表，语义等价。A、C、D 都是对两种写法的错误区分。

### single_choice · None



- [A] identity(1) 推断 T 为 int
- [B] identity('a') 推断 T 为 str
- [C] identity([1, 2]) 推断 T 为 list[int]
- [D] identity(1) 推断 T 为 object，因为返回值被拓宽了

**参考答案**：3

**解析**：identity 保持输入输出同一类型，identity(1) 应推断为 int，而不是被拓宽为 object。A、B、C 都符合 TypeVar 的推断规则。

### single_choice · None



- [A] Protocol 不能带类型参数，只有 Generic 可以
- [B] Protocol 可以与 Generic 组合，写出带类型参数的结构化类型协议
- [C] Generic 只能用于类，不能与 Protocol 一起使用
- [D] Protocol 与 Generic 都只在运行时生效，与类型检查无关

**参考答案**：1

**解析**：Protocol 类可以继承 Generic[T] 等形式，定义带类型参数的结构化协议。A、C 否认了二者组合的可能；D 错在它们主要服务于静态类型检查。

### single_choice · None



- [A] 定义新函数 def f_int(x: int) -> int: return f(x)
- [B] 直接写 f[int](1)，通过下标显式指定类型参数
- [C] 直接写 f[int](1) 并依赖运行时检查强制转换
- [D] 在函数内部用 assert isinstance(x, int)

**参考答案**：1

**解析**：Python 支持对泛型函数显式提供类型参数，如 f[int](1)，这不是运行时转换，而是给类型检查器的信息。A 是一个新函数而非特化；C 混淆了显式类型参数与运行时转换；D 是运行时断言，不是特化。

### single_choice · None



- [A] T 可以任意为 int 或 str 的子类，包括 bool
- [B] T 被约束为 int 或 str 之一，且推断时不能超出这两个类型
- [C] T 表示 int 与 str 的联合类型，因此值可以是两者混合
- [D] T 会在运行时对传入值做 isinstance 检查并抛错

**参考答案**：1

**解析**：带约束的 TypeVar 把可接受的类型限定为列出的具体类型；在同一次调用中，推断出的类型必须恰好是其中之一。A 把约束与 bound 混淆；C 混淆约束与联合类型；D 错在类型注解不做运行时检查。

### single_choice · None



- [A] 容器类希望保留元素类型信息，并在取出元素时得到精确类型
- [B] 希望关闭类型检查，让任何操作都通过
- [C] 函数参数可以是任意类型且返回类型与输入无关
- [D] 只想在运行时做动态属性访问

**参考答案**：0

**解析**：泛型的核心价值是保留类型参数与元素类型信息，从而在取出元素时给出精确类型。B、C、D 都是 Any 或忽略类型检查的典型用途，与泛型目的相反。

### single_choice · None



- [A] 因为 int 不是 object 的子类
- [B] 因为 list 对其元素类型是不变的，list[int] 不是 list[object] 的子类型
- [C] 因为 list 是协变的，方向反了才能赋值
- [D] 因为 list 在运行时会拒绝这种赋值并抛 TypeError

**参考答案**：1

**解析**：list 是可变的，类型参数不变，因此 list[int] 与 list[object] 没有子类型关系；若允许赋值，就可能向其中插入非 int 元素。A 错在 int 确实是 object 子类；C 方向说反；D 错在运行时通常不会因此抛错。

### single_choice · None



- [A] 它让类在运行时检查类型参数并做转换
- [B] 它向类型检查器声明该类是泛型类，并引入类型参数 T
- [C] 它让类自动获得 T 的默认值
- [D] 它只能用于抽象基类，普通类不能用

**参考答案**：1

**解析**：继承 Generic[T] 是声明泛型类、引入类型参数的常用方式，主要服务于类型检查器。A 错在它不做运行时检查与转换；C 错在类型参数没有所谓默认值；D 错在普通类也可以使用。

### single_choice · None



- [A] 运行时会为每个类型参数创建独立的类对象
- [B] 删除类型注解后程序行为不变，但类型检查器会失去这些泛型信息
- [C] 泛型会在运行时自动调用 isinstance 检查参数类型
- [D] 泛型会自动为每个类型参数生成 __init__ 方法

**参考答案**：1

**解析**：Python 的类型注解在运行时通常不改变程序行为，泛型信息主要供静态类型检查器使用。A、C、D 都错误地把泛型当成运行时会生成代码或做检查的机制。

### single_choice · None



- [A] Repo[T]
- [B] Repo[int]
- [C] Repo()
- [D] Repo[Generic[int]]

**参考答案**：1

**解析**：Repo[int] 把类型参数 T 具体化为 int，表示元素为 int 的 Repo。A 没有具体化；C 是实例化而非类型标注；D 把 Generic 嵌套进下标，不是正确写法。

### single_choice · None



- [A] T 只允许是 Animal 这一个类，子类都不允许
- [B] T 必须是 Animal 或其子类，从而可以调用 Animal 上定义的方法
- [C] T 必须是 Animal 的父类，以便向上转型
- [D] bound 表示 T 的默认类型是 Animal

**参考答案**：1

**解析**：bound 给 TypeVar 设上界，T 可以是 Animal 或其任意子类，因此在泛型函数体内可以安全使用 Animal 上定义的方法。A 忽略了子类；C 把上界误解为父类约束；D 把 bound 当成默认类型。

### single_choice · None



- [A] Sequence[int]
- [B] int
- [C] T
- [D] object

**参考答案**：1

**解析**：传入 list[int] 与 Sequence[T] 匹配后 T 被推断为 int，因此返回类型为 int。A 是参数类型而非返回类型；C 是未具体化的类型变量；D 是过宽的兜底类型。

### single_choice · None



- [A] 来自方法自身的局部 TypeVar，与类无关
- [B] 来自类的 Generic[T] 声明，方法的签名中可以直接引用
- [C] 来自内置模块自动注入的全局变量
- [D] 来自 self 的运行时类型检查结果

**参考答案**：1

**解析**：泛型类的类型参数由类声明中的 Generic[T] 引入，类体内的方法可以直接引用该 T。A 错在把它当成方法局部类型变量；C、D 与泛型参数来源无关。

### single_choice · None



- [A] 默认情况下，泛型类对其类型参数是不变的（invariant）
- [B] 默认情况下，泛型类对其类型参数是协变的（covariant）
- [C] 默认情况下，泛型类对其类型参数是逆变的（contravariant）
- [D] 型变只能用于函数，不能用于类

**参考答案**：0

**解析**：Python 的泛型类默认不变，即 List[int] 与 List[object] 之间没有子类型关系（尽管二者运行时都是 list）。B、C 错在默认型变不是协变或逆变；D 错在型变主要就是针对泛型类定义的。

### single_choice · None



- [A] b: Box[Animal] = Box[Dog]()
- [B] b: Box[Dog] = Box[Animal]()
- [C] b: Box[Dog] = Box[int]()
- [D] 协变类型之间不能有任何赋值

**参考答案**：0

**解析**：协变表示若 Dog 是 Animal 的子类型，则 Box[Dog] 也是 Box[Animal] 的子类型，因此可以赋值给 Box[Animal]。B 方向相反；C 的类型参数之间没有子类关系；D 否认了协变的可用性。

### single_choice · None



- [A] 因为协变会降低运行时性能
- [B] 因为协变允许把子类型容器当成父类型容器，写入时可能破坏类型安全
- [C] 因为 Python 不支持协变
- [D] 因为协变会让类型检查器不再检查该参数

**参考答案**：1

**解析**：若可变容器协变，可以把 Box[Dog] 当作 Box[Animal] 使用并写入其他 Animal 子类，从而破坏原本只应含 Dog 的容器，类型不安全。A、C、D 都不是正确原因。

### single_choice · None



- [A] covariant=True，因为它有返回值
- [B] contravariant=True，因为它有参数
- [C] 不变（invariant），因为 T 同时出现在输入和输出位置
- [D] 无所谓，Python 运行时不检查型变

**参考答案**：2

**解析**：T 同时出现在方法的参数（逆变位置）和返回值（协变位置），若声明协变或逆变都会在某些使用场景下不安全，因此应保持不变。A、B 只根据单一位置判断；D 忽略了静态类型检查的意义。

### single_choice · None



- [A] tuple 是泛型类，tuple[int, str] 是它带两个类型参数的具体化形式
- [B] tuple 不是泛型，下标写法只是类型检查器的特殊语法，与泛型无关
- [C] tuple[int, str] 表示两个元素的联合类型 int | str
- [D] tuple[int, str] 会在运行时创建新的 tuple 子类

**参考答案**：0

**解析**：内置 tuple 支持泛型下标，tuple[int, str] 表示一个二元组，第一个元素为 int，第二个为 str。B 否定了 tuple 的泛型特性；C 混淆了元组与联合类型；D 混淆了类型注解与运行时类创建。

### single_choice · None



- [A] T = TypeVar('T')，并写成 def f(x: T) -> T
- [B] T = TypeVar('T')，并写成 def f(x: T) -> object
- [C] T = object，并写成 def f(x: T) -> T
- [D] 直接写成 def f(x: type) -> type

**参考答案**：0

**解析**：TypeVar 的典型用途是建立参数与返回值之间的类型关联。T = TypeVar('T') 后，def f(x: T) -> T 表示返回类型与参数类型一致；若返回 object 会丢失具体类型，用 object 或 type 则不具备这种关联。

### single_choice · None



- [A] constrained TypeVar 只能取列出的若干个具体类型之一；有 bound 的 TypeVar 可接受该上界的任意子类型
- [B] constrained TypeVar 和 bound TypeVar 完全等价，只是写法不同
- [C] bound 只能用于表示多个具体类型，constrained 只能表示一个
- [D] 两者都只能接受恰好一个具体类型

**参考答案**：0

**解析**：约束写法 TypeVar('T', int, str) 表示 T 必须是 int 或 str 之一；而 bound 写法 TypeVar('T', bound=Number) 表示 T 可以是 Number 的任意子类型。二者语义不同，约束是枚举式限制，bound 是子类型上界。

### multi_choice · None



- [A] TypeVar 可用于在类内部表达与实例自身类型一致的元素
- [B] 递归泛型在类型检查器中的推断可能更复杂，需要谨慎声明
- [C] 只要用了 TypeVar，类型检查器就一定能完整推断递归结构
- [D] 类型参数可用于嵌套结构，如 Node[T] 中的子节点

**参考答案**：[0, 1, 3]

**解析**：TypeVar 能表达自引用和嵌套结构，但类型检查器的推断能力有限，复杂递归有时需要显式标注，不能保证完全自动推断，所以第三项错误。

### multi_choice · None



- [A] 为每个 TypeVar 使用有意义且不冲突的名字，避免全局重名
- [B] 在不需要类型关联的函数中避免滥用 TypeVar
- [C] 用 TypeVar 替代所有普通类型注解以追求泛化
- [D] 协变/逆变只在确实需要子类型关系时声明

**参考答案**：[0, 1, 3]

**解析**：合理做法包括命名清晰、按需使用、谨慎声明变型。把所有注解都换成 TypeVar 会造成不必要的复杂度和类型推断困难，故第三项错误。

### fill_blank · None



**参考答案**：["int, str", "int,str", "int 和 str"]

**解析**：约束式 TypeVar 把允许的类型作为后续位置参数列出：TypeVar('T', int, str) 表示 T 只能是 int 或 str。

### fill_blank · None



**参考答案**：["bound", "bound=Base"]

**解析**：bound 关键字用于指定 TypeVar 的上界，允许任意子类型通过类型检查。

### fill_blank · None



**参考答案**：["covariant"]

**解析**：协变通过在 TypeVar 上设置 covariant=True 声明，前提是该类型参数只用于只读位置。

### code_reading · None



**参考答案**：a 推断为 int，b 推断为 str。因为 T 在 list[T] 参数和返回值之间建立了关联，类型检查器会根据实参列表的元素类型推断 T，再回填到返回值。

**解析**：这是 TypeVar 建立参数与返回值类型关联的典型示例。传入 list[int] 时 T 推断为 int，返回 int；传入 list[str] 时 T 推断为 str。

### code_reading · None



**参考答案**：不会报错（取决于具体检查器）。int 在数值类型中通常被视为与 float 兼容，因此可接受；若上界与实参类型不兼容则会在相应检查器上报错。

**解析**：本题考查 bound 的接受范围。bound=float 表示上界 float，能接受其子类型或兼容类型；int 在数值上常被接受，因此通常不报错。具体行为取决于所用类型检查器的数值兼容规则。

### code_reading · None



**参考答案**：问题在于协变类型参数 T 被用在了 set 方法的参数（可写）位置。协变量只应用在只读位置，写入位置会破坏协变的安全性，类型检查器可能报错。

**解析**：协变要求类型参数只出现在只读位置。set 方法接收 T 并写回属性，属于可写位置，与协变声明冲突，因此不被允许。

### scenario · None



**解析**：正确答案应指出用 TypeVar 声明一个类型参数，并在两个参数和返回值上都使用同一个 TypeVar，从而在类型检查器中建立它们必须是同一类型的关联。

### scenario · None



**解析**：关键点：协变要求类型参数只出现在只读位置；可写的 add 方法会把类型参数放在可写位置，与协变冲突。常见做法是拆分接口，把只读的协变部分与可写的可变部分分开，或对可写类使用不变类型参数。

### single_choice · None



- [A] Dog（Dog 是 Animal 的子类）
- [B] int（与 Animal 无继承关系）
- [C] 任意类型都可以
- [D] 只能是 Animal 本身，子类不行

**参考答案**：0

**解析**：bound=Animal 表示上界为 Animal，任何 Animal 的子类型（如 Dog）都被接受。int 不在该约束范围内；子类是可以的，所以不是只能传 Animal 本身。

### scenario · None



**解析**：应选择 bound 式 TypeVar，因为「具有 name 属性的对象」可由一个上界类或协议来表示，bound 接受其任意子类型；约束式 TypeVar 只能枚举几个具体类型，无法表达任意子类的开放集合。

### single_choice · None



- [A] 协变表示子类型关系与容器方向一致；逆变表示方向相反；两者需要显式声明
- [B] 协变和逆变由 Python 自动推断，不能显式声明
- [C] 只有协变存在，逆变在类型提示中无意义
- [D] 协变意味着类型检查器会忽略类型参数

**参考答案**：0

**解析**：在 typing 中可通过 covariant=True / contravariant=True 显式声明变型。协变保持子类型方向，逆变反转方向，省略时默认为不变（invariant），并非自动推断。

### single_choice · None



- [A] 类型检查器报错，因为 float 不在 int 或 str 约束中
- [B] 类型检查器通过，结果类型为 float
- [C] 类型检查器报错，因为 T 同时用于参数和返回值
- [D] 类型检查器通过，因为 Python 不检查数值类型

**参考答案**：0

**解析**：约束式 TypeVar 只允许列出的类型，float 不在 int、str 之内，因此静态类型检查器会报错。运行时 Python 不会阻止，但本题问的是类型检查结果。

### single_choice · None



- [A] T = TypeVar('T', covariant=True) 并在类中把 T 用在只读位置
- [B] T = TypeVar('T', contravariant=True)
- [C] T = TypeVar('T', bound=object)
- [D] 使用普通 TypeVar，协变会自动生效

**参考答案**：0

**解析**：要获得协变行为，需声明 covariant=True，且类型参数只出现在只读位置。contravariant 方向相反；默认 TypeVar 是不变的，不会自动协变。

### single_choice · None



- [A] 把协变的类型参数同时用在可写（接收）位置
- [B] 把 TypeVar 只用在返回值位置
- [C] 把 TypeVar 只用在只读属性位置
- [D] 把 TypeVar 用于函数内部的局部变量

**参考答案**：0

**解析**：协变类型参数若出现在接收参数（可写）位置，会与协变假设冲突，导致类型不安全。只出现在返回或只读位置才安全。局部变量与只读位置通常不影响变型。

### multi_choice · None



- [A] TypeVar 用来在多个签名之间建立类型关联，而不是表示某一个具体类型
- [B] 同一个泛型函数中重复使用同一个 TypeVar，表示这些位置必须是同一类型
- [C] 带约束的 TypeVar 允许传入约束列表中任意类型对应的子类型
- [D] TypeVar 在运行时具有强制类型检查作用，会拒绝不匹配的实参

**参考答案**：[0, 1]

**解析**：TypeVar 的核心是类型关联与复用；重复出现表示同一类型。约束式 TypeVar 只接受明确列出的类型之一，其子类型不被接受（这与 bound 不同），所以第三项错误。TypeVar 不产生运行时强制检查，第四项错误。

### multi_choice · None



- [A] 通过字符串指定多个约束类型，如 TypeVar('T', int, str)
- [B] 通过 bound 指定上界，如 TypeVar('T', bound=Animal)
- [C] 通过 covariant 或 contravariant 指定变型
- [D] 通过 default 指定默认类型（较新版本 Python 支持）
- [E] 通过 runtime=True 开启运行时类型校验

**参考答案**：[0, 1, 2, 3]

**解析**：TypeVar 支持约束、bound、变型参数，较新版本还支持 default 默认类型。它并没有 runtime=True 这类开启运行时校验的参数，运行时不会因类型不匹配抛错。

### multi_choice · None



- [A] 希望接受上界类的任意子类时
- [B] 希望表达「可以调用上界类上定义的方法」时
- [C] 希望严格限制为仅某几个具体类型时
- [D] 希望在类型间保留子类型关系时

**参考答案**：[0, 1, 3]

**解析**：bound 适用于接受任意子类、表达可调用上界方法、并保留子类型关系的场景。若想严格限制为几个具体类型，应该使用约束列表，故第三项不选。
