# s2u5l1 Python 结构化子类型协议（Protocol）入门 / 把「打开—使用—关闭」变成自动化流程

> 来源 `content/lessons/s2u5l1.json`

## py.ctx.protocol

# py.ctx.protocol：Python 结构化子类型协议（Protocol）入门

## 一句话直觉

**Protocol 让你“只看对象会做什么，不看它是什么类”**——只要一个对象实现了协议要求的方法或属性，它就能被当作该协议的实例，无需继承、无需注册，从而写出更灵活、解耦、可测试的代码。

> 术语：Protocol（协议，结构化子类型 structural subtyping）、duck typing（鸭子类型）、nominal typing（名义子类型，靠继承关系）。

---

## 1. 为什么需要 Protocol：从“鸭子类型”到“可检查的鸭子类型”

Python 传统上依靠 duck typing：如果它走起来像鸭子、叫起来像鸭子，就当成鸭子。问题是**类型检查器（type checker，如 mypy、pyright）看不懂“像不像”**，只能靠继承关系（nominal typing）判断。

`typing.Protocol` 填补了这个空档：它把“鸭子类型”显式声明成一种类型，让静态检查器也能验证结构。

```python
from typing import Protocol

# 定义一个协议：凡是有 quack() 和 walk() 方法的对象，都符合 Duck 协议
class Duck(Protocol):
    def quack(self) -> str: ...
    def walk(self) -> None: ...

# 这个类完全没有继承 Duck，但结构上满足它
class RubberDuck:
    def quack(self) -> str:
        return "squeak"
    def walk(self) -> None:
        print("waddle")

def use_duck(d: Duck) -> None:
    print(d.quack())

use_duck(RubberDuck())   # 类型检查器通过：RubberDuck 结构上就是 Duck
```

**关键结论**：Protocol 是“结构化的类型”，只要方法/属性齐备即可，无需显式继承。

---

## 2. 定义 Protocol：方法、属性与 `...` 省略体

Protocol 类通常继承 `Protocol`，方法体写作 `...`（或者 `raise NotImplementedError`）。属性用注解声明，不要赋值。

```python
from typing import Protocol

class Sized(Protocol):
    # 属性：只声明类型，不赋值
    name: str
    # 方法：用 ... 省略实现
    def size(self) -> int: ...

class MyList:
    name = "mylist"
    def size(self) -> int:
        return 42

def report(s: Sized) -> str:
    return f"{s.name}: {s.size()}"

print(report(MyList()))  # mylist: 42
```

注意：Protocol **不能被实例化**（它相当于接口），直接 `Duck()` 会报错。

---

## 3. 运行时检查：`@runtime_checkable` 与它的“浅检查”陷阱

默认 Protocol 只在静态检查器里生效；要在运行时用 `isinstance()` / `issubclass()` 判断，必须加 `@runtime_checkable` 装饰器。

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class Reversible(Protocol):
    def __reversed__(self): ...

class MySeq:
    def __reversed__(self):
        return iter([])

print(isinstance(MySeq(), Reversible))  # True
print(isinstance(123, Reversible))      # False
```

**极其重要的注意点**（来自官方文档）：`@runtime_checkable` **只检查成员是否存在，不检查类型签名**。例如 `ssl.SSLObject` 虽然 `__init__` 只会抛异常（无法实例化），但结构上仍可能通过某些协议检查。

另一个坑：运行时 `isinstance()` 对协议的性能比普通类差很多，在性能敏感路径中可考虑用 `hasattr()` 等结构检查替代。

此外 Python 3.12 起：
- 运行时检查改用 `inspect.getattr_static()`，避免触发属性求值副作用；
- 协议的成员在类创建后即“冻结”，动态 monkey-patch 不再影响 `isinstance()`。

---

## 4. 内省 Protocol：`is_protocol`、`get_protocol_members` 等

Python 3.13 提供了直接查看协议内部信息的工具：

```python
from typing import Protocol, is_protocol, get_protocol_members, runtime_checkable

class P(Protocol):
    def a(self) -> str: ...
    b: int

print(is_protocol(P))                       # True
print(get_protocol_members(P))              # frozenset({'a', 'b'})
print(is_protocol(int))                     # False

# 注意：泛型别名不是协议类本身
from typing import TypeVar
T = TypeVar("T")
class GenericP(Protocol[T]):
    def a(self) -> T: ...
print(is_protocol(GenericP[int]))           # False
```

如果对非协议类调用 `get_protocol_members` 会抛 `TypeError`。

---

## 5. 标准库里的 Protocol 与工程用法

`typing` 里已经内置了不少常用协议：

- `SupportsInt` / `SupportsFloat` / `SupportsIndex` / `SupportsBytes` / `SupportsComplex` / `SupportsRound`
- `io.Reader`、`io.Writer`（`typing.IO` 是普通 ABC，不是协议，不要混淆）

工程中用 Protocol 的典型动机：

1. **解耦**：业务逻辑只依赖接口，不依赖具体实现。
2. **便于测试**：mock 对象只要实现协议方法即可，不必继承。
3. **避免深继承树**：用结构而非类系来表达“能力”。

```python
from typing import Protocol

class Storage(Protocol):
    def save(self, key: str, value: bytes) -> None: ...
    def load(self, key: str) -> bytes: ...

class MemoryStorage:                # 真实实现
    def __init__(self): self._d = {}
    def save(self, key, value): self._d[key] = value
    def load(self, key): return self._d[key]

class FakeStorage:                  # 测试替身，也满足协议
    def save(self, key, value): pass
    def load(self, key): return b""

def backup(s: Storage) -> None:
    s.save("hello", b"world")

backup(MemoryStorage())
backup(FakeStorage())
```

---

## 常见误区

1. **以为 Protocol 可以实例化**。错。它只是接口，实例化会报 `TypeError`。
2. **以为 `@runtime_checkable` 会校验类型签名**。错。它只检查成员是否存在，返回类型、参数类型一概不看。
3. **在非协议类上用 `@runtime_checkable`**。会抛 `TypeError`，该装饰器只能用于协议。
4. **在性能敏感代码里滥用 `isinstance(x, SomeProtocol)`**。运行时协议检查比普通类慢很多，可换成 `hasattr`。
5. **以为协议支持运行时 monkey-patch 后能被识别**。Python 3.12 起协议成员在类创建后冻结，动态加成员不再影响 `isinstance`。
6. **在 3.15+ 对未显式 `@runtime_checkable` 但继承自可检查协议的类做 `isinstance`**。已弃用，3.20 将报错。

---

## 动手练习

写一个“可序列化”协议，并让两个完全不同的类去满足它：

1. 定义 `@runtime_checkable` 的 `Serializable` 协议，要求实现 `to_dict(self) -> dict`。
2. 定义两个类，比如 `User` 和 `Order`，都没有继承 `Serializable`，但都实现 `to_dict`。
3. 写函数 `dump(obj: Serializable) -> dict`，返回 `obj.to_dict()`。
4. 用 `isinstance(obj, Serializable)` 验证两个对象都通过运行时检查。
5. 再造一个没有任何 `to_dict` 的类，确认 `isinstance` 返回 `False`。

预期结果：能体会“结构化子类型”的灵活性和 `@runtime_checkable` 的浅检验边界。

```python
from typing import Protocol, runtime_checkable

# 1) 运行时可见的协议：只要求结构成员存在
@runtime_checkable
class Serializable(Protocol):
    def to_dict(self) -> dict: ...

# 2) 两个完全不继承 Serializable 的类
class User:
    def __init__(self, name, age):
        self.name = name
        self.age = age
    def to_dict(self):
        return {"name": self.name, "age": self.age}

class Order:
    def __init__(self, oid, amount):
        self.oid = oid
        self.amount = amount
    def to_dict(self):
        return {"id": self.oid, "amount": self.amount}

# 3) 只依赖协议的业务函数
def dump(obj: Serializable) -> dict:
    return obj.to_dict()

# 4) 运行时检查
for obj in (User("Alice", 30), Order(1001, 99.5)):
    print(type(obj).__name__, isinstance(obj, Serializable), dump(obj))

# 5) 不满足协议的类应返回 False
class Plain:
    pass
print("Plain:", isinstance(Plain(), Serializable))  # False
```

## py.ctx.contextlib

# py.ctx.contextlib：把「打开—使用—关闭」变成自动化流程

> **一句话直觉**：`contextlib` 让你把「进入 / 退出」这类成对出现的收尾逻辑（打开文件、加锁、连接数据库、切换环境）交给 `with` 语句自动管理，即使中途抛异常也保证清理，代码更短、更安全。

---

## 1. 为什么需要它：手写 try/finally 的痛点

任何「先申请资源、用完必须释放」的操作，都要求成对出现。最原始写法：

```python
# 手动管理：必须记得关闭，异常路径也要处理
f = open("data.txt", "w")
try:
    f.write("hello")
finally:
    f.close()
```

问题：文件句柄、锁、数据库连接、临时目录……每个都要重复写 `try/finally`，容易漏，也难复用。Python 为此引入**上下文管理器（context manager）**协议：实现 `__enter__()` 和 `__exit__()` 的对象，就能用 `with` 语句。

```python
# with 语句：进入时调用 __enter__，退出时无论是否异常都调用 __exit__
with open("data.txt", "w") as f:
    f.write("hello")
# 到这里文件一定已关闭
```

**结论**：`with` 是语法糖，背后是「上下文管理器协议」。`contextlib` 则是帮你**低成本地写出**上下文管理器的标准库工具集。

---

## 2. 协议本身：`__enter__` 与 `__exit__`

自己写一个类就理解了协议：

```python
class Managed:
    def __enter__(self):
        print("enter")
        return self           # 这个返回值绑定给 as 后的变量

    def __exit__(self, exc_type, exc_val, exc_tb):
        print("exit")
        return False          # 返回 False/None：不吞掉异常

with Managed() as m:
    print("body")
# 输出：enter -> body -> exit
```

关键点：
- `__enter__` 的返回值就是 `with ... as x` 里的 `x`。
- `__exit__(exc_type, exc_val, exc_tb)`：正常退出时三个参数都是 `None`；有异常时是异常信息。
- `__exit__` 返回 **真值** 会「吞掉」异常（不推荐滥用）；返回 `False` 则异常继续向上传播。

**结论**：`contextlib` 里的所有工具，最终都产出满足这个协议的对象。

---

## 3. 核心工具一：`@contextmanager`——用生成器写上下文管理器

写一个类太啰嗦。`@contextmanager` 允许你把「进入逻辑」和「退出逻辑」写在一个生成器函数里：`yield` 之前是进入，`yield` 之后是退出。

```python
from contextlib import contextmanager

@contextmanager
def tag(name):
    print(f"<{name}>")   # 进入：等价于 __enter__
    try:
        yield name        # yield 的值就是 as 后拿到的对象
    finally:
        print(f"</{name}>")  # 退出：即使抛异常也执行（等价于 __exit__）

with tag("h1") as t:
    print("  hello", t)
# 输出：<h1> -> hello h1 -> </h1>
```

`try/finally` 是这里的标准写法，保证清理逻辑一定执行。如果需要根据是否有异常做不同处理，可以捕获 `except`。

**结论**：`@contextmanager` 是 90% 场景的首选，代码量远小于写类。

---

## 4. 核心工具二：`contextlib` 常用组件速查

`contextlib` 里除了 `@contextmanager`，还有一批开箱即用的工具：

```python
import contextlib

# 1) closing：给「有 .close() 但没有上下文协议」的对象套壳
with contextlib.closing(open("a.txt")) as f:
    print(f.read())

# 2) suppress：静默吞掉指定异常（比 try/except/pass 更清晰）
with contextlib.suppress(FileNotFoundError):
    open("missing.txt")

# 3) redirect_stdout：临时把 stdout 重定向
import io
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    print("captured")
print("captured?", buf.getvalue())

# 4) ExitStack：动态管理数量不定的资源
with contextlib.ExitStack() as stack:
    files = [stack.enter_context(open(f"f{i}.txt", "w")) for i in range(3)]
    # 离开 with 时 3 个文件按相反顺序关闭
```

`ExitStack` 特别适合「资源个数运行时才知道」的场景，例如批量打开文件、动态加载插件。

**结论**：能用现成的就用现成的；`suppress` 和 `closing` 是日常最常踩坑时的救命工具。

---

## 5. 进阶：错误处理策略与异步上下文

### 5.1 用 `__exit__` 决定是否吞异常

```python
from contextlib import contextmanager

@contextmanager
def ignore_value_error():
    try:
        yield
    except ValueError:
        pass          # 吞掉 ValueError，其他异常继续抛出

with ignore_value_error():
    raise ValueError("被忽略")
print("继续执行")
```

### 5.2 异步上下文管理器

`async with` 对应 `__aenter__` / `__aexit__`，`contextlib` 用 `@asynccontextmanager` 装饰异步生成器：

```python
import asyncio
from contextlib import asynccontextmanager

@asynccontextmanager
async def aopen():
    print("aenter")
    try:
        yield "resource"
    finally:
        print("aexit")

async def main():
    async with aopen() as r:
        print("use", r)

asyncio.run(main())
```

### 5.3 类型注解

`contextlib.AbstractContextManager` 是这些对象的抽象基类（ABC, Abstract Base Class）。类型标注时可直接用它，例如 `def f() -> AbstractContextManager[int]: ...`。早期 `typing.ContextManager` 是它的别名，自 Python 3.9 起已被弃用，建议直接使用 `contextlib.AbstractContextManager`。

**结论**：掌握 `@contextmanager` + `suppress` + `ExitStack`，已经能覆盖绝大多数生产场景。

---

## 动手练习

**任务**：写一个 `@contextmanager` 装饰的 `timer(name)`，功能为：进入时记录起始时间，退出时打印 `name` 和耗时（秒）。要求在 `with` 体内抛异常时也能正确打印耗时，并把异常继续抛出。

**验收**：

1. 正常代码块：输出 `任务: xxx, 耗时: 0.xx 秒` 之类格式。
2. 抛出 `ValueError` 的代码块：先打印耗时，再看到 `ValueError` 传播出来。

**提示骨架**：

```python
import time
from contextlib import contextmanager

@contextmanager
def timer(name):
    start = time.perf_counter()
    try:
        yield
    finally:
        # 在 finally 里计算并打印，保证异常路径也执行
        ...
```

**拓展**：把 `timer` 改成默认静默记录到 `logging`，只在名字含 `critical` 时才打印到 stdout。

```python
import time
from contextlib import contextmanager

@contextmanager
def timer(name):
    # 进入阶段：记录开始时间
    start = time.perf_counter()
    try:
        yield  # 把控制权交给 with 代码块
    finally:
        # 退出阶段：无论正常还是异常都会执行
        elapsed = time.perf_counter() - start
        print(f"[{name}] 耗时: {elapsed:.3f} 秒")

# 正常路径
with timer("正常任务"):
    time.sleep(0.1)

# 异常路径：耗时仍会打印，异常继续传播
try:
    with timer("异常任务"):
        time.sleep(0.05)
        raise ValueError("boom")
except ValueError as e:
    print("捕获到异常:", e)
```


---

## 本课题目

### single_choice · None



- [A] 基于回调的事件注册与注销机制
- [B] 基于生成器的上下文协议，使对象可被 with 语句管理
- [C] 基于线程的信号量同步机制
- [D] 基于进程的共享内存通信机制

**参考答案**：1

**解析**：`async with` 依赖对象实现异步上下文管理协议（__aenter__/__aexit__），从而在进入和退出时自动完成资源获取与释放。

### single_choice · None



- [A] 正常运行，只是不会自动释放资源
- [B] 抛出 AttributeError，因为 with 语句要求对象同时具备 __enter__ 和 __exit__
- [C] 抛出 SyntaxError，因为 with 语句要求类必须继承 contextlib.ContextDecorator
- [D] 自动调用 __del__ 替代 __exit__ 完成释放

**参考答案**：1

**解析**：with 语句在进入时调用 __enter__、退出时调用 __exit__，缺少 __exit__ 会触发属性查找失败。

### single_choice · None



- [A] 三者都为 None
- [B] 三者都是字符串 'None'
- [C] exc_type 为 Exception，exc 与 tb 为 None
- [D] 只有 tb 为 None，其余为当前异常类

**参考答案**：0

**解析**：没有异常时，__exit__ 的三个参数均接收 None。

### single_choice · None



- [A] 不能，协议规定一个实例只能进入一次且不可重复使用
- [B] 可以，但具体是否安全取决于类对状态的实现；协议本身不禁止重复使用
- [C] 可以，并且 Python 会自动为每次 with 创建新实例
- [D] 不能，因为 with 会消耗掉实例的 __enter__ 方法

**参考答案**：1

**解析**：PEP 343 并未规定上下文管理器只能使用一次，能否重用取决于实现；有些一次性资源类的重用会出错。

### single_choice · None



- [A] 不会调用，return 会直接跳过清理逻辑
- [B] 在 return 之前调用，方法会收到 None 作为异常参数
- [C] 在函数返回到调用者之后才调用
- [D] 只有在代码块外显式 catch 异常时才会调用

**参考答案**：1

**解析**：无论代码块如何离开（正常、return、break、异常），__exit__ 都会在离开前被调用，return 时参数为 None。

### single_choice · None



- [A] obj = C(); obj.open() 之后手动 obj.close()
- [B] with C() as c: 使用 c，由协议保证退出时清理
- [C] c = C(); c.__enter__(); c.__exit__()
- [D] 把 C 的实例保存到全局列表以避免被回收

**参考答案**：1

**解析**：with 通过协议在退出路径上自动调用清理逻辑，即使代码块内提前 return 或抛异常也能保证执行。

### single_choice · None



- [A] C 的实例本身，因为 with 总是返回被管理的对象
- [B] __enter__ 的返回值
- [C] __init__ 的返回值
- [D] None，因为 with 不接收返回值

**参考答案**：1

**解析**：with 语句将 __enter__ 的返回值绑定到 as 后面的目标，而非必然是被管理的实例本身。

### single_choice · None



- [A] 只实现 __enter__ 和 __exit__，async with 会自动复用它们
- [B] 分别实现 __enter__/__exit__ 和 __aenter__/__aexit__，让两种协议各自独立可用
- [C] 只实现 __aenter__ 和 __aexit__，并在 __enter__ 中调用它们
- [D] 实现 __iter__ 和 __next__，因为 with 会退化为迭代

**参考答案**：1

**解析**：同步与异步上下文管理协议是两套独立方法，需要分别实现才能同时支持 with 和 async with。

### single_choice · None



- [A] 两者完全等价，都依赖 __enter__ 和 __exit__
- [B] 上下文管理协议关注进入/退出时的资源管理，迭代协议关注逐个产生元素
- [C] 上下文管理协议只能用于文件对象，迭代协议只能用于列表
- [D] 上下文管理协议是异步的，迭代协议是同步的

**参考答案**：1

**解析**：上下文管理协议由 __enter__/__exit__ 定义，用于 with 的资源管理；迭代协议由 __iter__/__next__ 定义，用于遍历。

### single_choice · None



- [A] enter → 42 → exit
- [B] 42 → enter → exit
- [C] enter → exit → 42
- [D] exit → 42 → enter

**参考答案**：0

**解析**：yield 前代码在进入 with 时执行，yield 值绑定为 as 变量，退出时 finally 中的代码再执行。

### single_choice · None



- [A] 会，__enter__ 抛异常时也会调用 __exit__
- [B] 不会，因为上下文尚未成功进入，__exit__ 不会被调用
- [C] 会，但只会调用一次之后对象被销毁
- [D] 会，并且异常会被 __exit__ 自动吞掉

**参考答案**：1

**解析**：只有 __enter__ 成功返回后才视为进入上下文；若它抛出异常，with 不会调用 __exit__。

### single_choice · None



- [A] __init__ 方法中
- [B] __enter__ 方法中
- [C] __exit__ 方法中，或使用 try/finally 配合 yield（生成器版）
- [D] 模块顶层，因为模块退出时会自动执行

**参考答案**：2

**解析**：清理逻辑应放在 __exit__ 或生成器上下文管理器的 finally 中，以保证多个退出路径都会执行。

### single_choice · None



- [A] __init__ 与 __del__
- [B] __enter__ 与 __exit__
- [C] __aenter__ 与 __aexit__
- [D] __iter__ 与 __next__

**参考答案**：1

**解析**：同步 with 语句依赖 __enter__ 和 __exit__；__aenter__/__aexit__ 是异步版本，__iter__/__next__ 属于迭代协议。

### single_choice · None



- [A] with 语句自动退化为异步上下文管理，正常工作
- [B] 解释器抛出 TypeError，因为同步 with 不会 await __aenter__ 返回的对象
- [C] with 语句会先调用 __aexit__ 再调用 __aenter__
- [D] 实例会被自动放入线程池中执行

**参考答案**：1

**解析**：同步 with 要求 __enter__/__exit__，对只有异步协议方法的对象会报类型错误。

### single_choice · None



- [A] 返回值必须是 True，否则资源无法释放
- [B] 返回 True 表示异常被吞掉，返回 False 或 None 则异常继续向外传播
- [C] 返回值只能是 None，其他值都会引发 TypeError
- [D] 返回值决定 with 块是否会被再次执行

**参考答案**：1

**解析**：`__exit__` 的三个参数接收异常信息，返回真值会抑制异常，否则异常继续抛出，返回 None 效果等同于 False。

### single_choice · None



- [A] 程序崩溃，ValueError 会被抛出并终止
- [B] 程序打印 done，因为 __exit__ 返回 True 抑制了异常
- [C] 程序进入死循环，因为 __exit__ 返回 True
- [D] 程序抛出 TypeError，因为 __exit__ 的返回值不合法

**参考答案**：1

**解析**：__exit__ 返回真值会吞掉 with 块内抛出的异常，因此继续执行到 print('done')。

### single_choice · None



- [A] 异常被静默忽略，程序继续执行
- [B] 异常继续向外传播，并可能被外层 try/except 捕获
- [C] with 语句自动重试一次代码块
- [D] 解释器抛出 RuntimeError 表示返回值非法

**参考答案**：1

**解析**：__exit__ 返回 False (或 None) 表示不抑制异常，异常会沿调用栈继续传播。

### single_choice · None



- [A] yield 之前对应 __enter__，yield 之后对应 __exit__
- [B] yield 之前对应 __exit__，yield 之后对应 __enter__
- [C] 两者都对应 __exit__，__enter__ 没有对应代码
- [D] yield 之前对应 __init__，yield 之后对应 __del__

**参考答案**：0

**解析**：@contextmanager 把生成器中 yield 之前的执行当作进入上下文，yield 之后（含 finally）当作退出上下文。

### single_choice · None



- [A] 被装饰的生成器函数必须恰好 yield 一次，否则可能报错或行为异常
- [B] 被装饰的函数可以是普通函数，只要它在结尾 return 一个对象
- [C] 该装饰器只能用于类，不能用于函数
- [D] 该装饰器会强制把生成器转换为线程

**参考答案**：0

**解析**：@contextmanager 要求生成器恰好 yield 一次，否则会抛出 RuntimeError 表示生成器未正确暂停或恢复。

### single_choice · None



- [A] __enter__ 与 __exit__，因为同步方法优先
- [B] __aenter__ 与 __aexit__，因为 async with 使用异步上下文管理协议
- [C] 两对方法都会被交替调用
- [D] __init__ 与 __del__

**参考答案**：1

**解析**：async with 专门查找并 await 异步上下文管理协议方法 __aenter__ 与 __aexit__。

### single_choice · None



- [A] 生成器中 yield 之前的代码相当于 __enter__，yield 之后的代码相当于 __exit__，且生成器最多只能 yield 一次
- [B] 生成器可以 yield 任意多次，每次 yield 都会重新执行 with 块
- [C] 被装饰的函数必须返回一个上下文管理器对象，而不是生成器
- [D] yield 抛出的异常会被自动忽略，不会传播回生成器内部

**参考答案**：0

**解析**：contextmanager 把生成器转换成上下文管理器：yield 前是进入逻辑，yield 后是退出逻辑。生成器只能 yield 一次，第二次 yield 会触发 RuntimeError（generator didn't stop）。若 with 块内抛出异常，该异常会被 throw 回生成器的 yield 处，因此可用 try/except/finally 处理。

### single_choice · None



- [A] enter
  42
  exit
- [B] enter
  exit
  42
- [C] 42
  enter
  exit
- [D] enter
  42

**参考答案**：0

**解析**：进入 with 时执行 yield 之前的 print('enter')，yield 的值 42 被赋给 v，with 体内打印 42，离开 with 时 finally 执行 print('exit')，顺序为 enter、42、exit。

### fill_blank · None



**参考答案**：["closing", "closing"]

**解析**：contextlib.closing 在退出 with 时调用对象的 close() 方法，适用于只有 close() 而没有实现 __enter__/__exit__ 的对象。两处空白都填 closing。

### fill_blank · None



**参考答案**：["contextmanager", "@contextmanager", "contextlib.contextmanager"]

**解析**：contextmanager 装饰器把 yield 一次（且仅一次）的生成器函数变成上下文管理器对象。需要从 contextlib 导入。

### code_reading · None



**参考答案**：输出 'a'、1，然后在 yield 处被 throw ValueError，因生成器未捕获该异常，异常继续向外传播，'b' 不会被打印。关键点：with 块内抛出的异常会被 throw 回生成器的 yield 处；若生成器未处理则异常向外传播，yield 之后的正常代码不执行。

**解析**：contextmanager 依赖生成器把异常 throw 回 yield 处。没有 try/finally 保护时，yield 后的 print('b') 不会执行，ValueError 向上传播。

### code_reading · None



**参考答案**：输出 ['body', 'second', 'first']。callback 按注册顺序注册，但退出时按后进先出（LIFO）执行，因此 'second' 先于 'first' 被追加，而 with 体内的 'body' 先追加。

**解析**：ExitStack 的清理顺序是 LIFO，与嵌套 with 的语义一致；注册的顺序不影响最终结果反过来，最后注册的最先执行。

### code_reading · None



**参考答案**：输出 [10, 5]。val 为 1 时 10//1=10 加入；val 为 0 时 ZeroDivisionError 被 suppress 吞掉，append 不执行；val 为 2 时加入 5；val 为 0 再次被忽略。最终 [10, 5]。

**解析**：suppress 抑制指定异常，块内出错时跳过剩余语句，但循环继续，不影响其他迭代。

### scenario · None



**解析**：标准做法是用 contextlib.redirect_stdout 配合 io.StringIO：with redirect_stdout(buf): ... 在 with 块内 sys.stdout 被替换为 buf，退出时自动恢复原值。如果直接赋值 sys.stdout = buf 而不恢复，会污染后续代码与测试之间的全局状态。

### scenario · None



**解析**：使用 ExitStack：with ExitStack() as stack: 中循环调用 stack.enter_context(cm) 动态注册资源。退出时按 LIFO 顺序自动释放；即使中途抛异常也能保证已注册的资源被释放。手动维护列表容易在异常路径下漏掉释放。

### single_choice · None



- [A] 抑制 with 块内指定类型的异常，其他异常仍然会抛出
- [B] 抑制 with 块内所有异常，等价于裸 except:
- [C] 把指定异常转换成返回值返回给 with 的目标变量
- [D] 只在异常发生时才执行 with 块内代码

**参考答案**：0

**解析**：suppress 只吞掉列出的异常类型，等价于 try/except SomeError: pass。未列出的异常会正常传播，因此不等价于裸 except。它也不返回异常对象。

### single_choice · None



- [A] done
- [B] 抛出 FileNotFoundError 并终止
- [C] 什么都不输出
- [D] 输出删除失败信息

**参考答案**：0

**解析**：suppress 会抑制 FileNotFoundError，with 块正常结束，继续执行 print('done')。这正是 suppress 的常见用法：忽略特定异常。

### single_choice · None



- [A] ExitStack 允许动态注册任意数量的清理回调，退出时按后进先出顺序调用
- [B] ExitStack 只能注册一个上下文管理器，注册多个会报错
- [C] ExitStack 中注册的回调按注册顺序依次调用
- [D] ExitStack 只能用于 with 语句，不能手动调用 close()

**参考答案**：0

**解析**：ExitStack 用于管理数量不定的上下文管理器和清理回调，支持 enter_context、callback、push 等方法，退出时（或调用 close() 时）按 LIFO 顺序执行，这与嵌套 with 的语义一致。

### single_choice · None



- [A] 为只有 close() 方法、但没有实现上下文管理协议的对象提供 with 支持
- [B] 自动关闭 with 块内创建的所有对象
- [C] 在异常发生时才关闭对象
- [D] 把 close() 方法的返回值作为 with 目标变量

**参考答案**：0

**解析**：closing(thing) 在退出 with 时调用 thing.close()，用于那些有 close() 但未实现 __enter__/__exit__ 的对象。with closing(obj) as x 中 x 就是 obj 本身。

### single_choice · None



- [A] 它临时把 sys.stdout 重定向到指定的类文件对象，退出时恢复原值
- [B] 它会永久修改 sys.stdout，无法恢复
- [C] 它只能重定向 stderr，不能重定向 stdout
- [D] 它要求目标对象必须是真实的文件描述符

**参考答案**：0

**解析**：redirect_stdout(new_target) 是一个上下文管理器，在 with 块期间 sys.stdout 被替换为 new_target，退出时恢复原值。常用于捕获输出到 StringIO 进行测试。

### single_choice · None



- [A] 进入时不执行任何操作，退出时也不执行任何操作，可选地在进入时返回指定值
- [B] 总是返回 None，无法返回其他值
- [C] 进入时关闭资源，退出时重新打开
- [D] 等价于 suppress(Exception)

**参考答案**：0

**解析**：nullcontext(enter_result=None) 是一个什么都不做的上下文管理器，进入时返回 enter_result。常用于需要可选上下文管理器的场景，避免写两个分支。

### single_choice · None



- [A] with open('a') as f1, open('b') as f2: ...
- [B] with open('a'), open('b') as f1, f2: ...
- [C] with (open('a'), open('b')) as f1, f2: ...
- [D] 以上都不行，必须嵌套两个 with

**参考答案**：0

**解析**：Python 支持在单个 with 中用逗号分隔多个上下文管理器，等价于嵌套 with。退出时按后进先出顺序调用各自的 __exit__。选项 B 语法错误，选项 C 会试图对元组使用 with。

### single_choice · None



- [A] 返回真值表示异常已被处理，不再向外传播；返回假值则异常继续传播
- [B] 返回值只影响 __enter__ 的返回值
- [C] __exit__ 必须返回 None
- [D] 返回真值会把异常转换成返回值返回给 with 目标变量

**参考答案**：0

**解析**：__exit__(exc_type, exc_val, tb) 返回真值时，with 语句会抑制异常；返回假值（含 None）时异常继续向外传播。这也是 suppress 的实现原理之一。
