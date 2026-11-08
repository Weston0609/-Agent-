# s2u1l7 Python 抽象类与协议（Abstract Class & Protocol） / Python 协议（Protocol）：让鸭子类型（Duck Typing）可被静态类型检查器理解 / 鸭子类型（Duck Typing）：Python 动态多态的精髓

> 来源 `content/lessons/s2u1l7.json`

## py.oop.abstract

# Python 抽象类与协议（Abstract Class & Protocol）

## 一句话直觉

抽象类和协议就是“接口合同”：它们不关心你怎么实现，只强制规定你必须提供哪些方法，这样调用方就能放心地依赖“能力”而不是具体类型。

这是面向对象设计（Object-Oriented Design）的起点，也是大型工程中解耦模块的关键机制。

---

## 1. 为什么需要抽象？——从“必须是某类”到“能做事就行”

在 Python 中，函数常常需要对参数做某种操作，比如“把对象转成整数”、“读取一行文本”。如果只依赖具体类（如 `int`、`list`），代码就会绑死；如果依赖“具备某方法”的能力，代码就能接受很多不同对象。

**抽象类（Abstract Base Class, ABC）** 就是用来声明这种“必须具备哪些方法”的工具。凡是继承它的类，如果不实现这些方法，就无法实例化。

```python
from abc import ABC, abstractmethod

class Shape(ABC):
    @abstractmethod
    def area(self) -> float:
        """返回面积"""
        ...

# Shape()  # 会报错：Cannot instantiate abstract class

class Circle(Shape):
    def __init__(self, r: float):
        self.r = r

    def area(self) -> float:
        return 3.14159 * self.r ** 2

print(Circle(2).area())  # 12.56636
```

要点：
- `ABC` 是抽象基类；`@abstractmethod` 标记必须被重写的方法。
- 只要还有未实现的抽象方法，子类就不能实例化。
- 抽象类不能直接 `Shape()`，它只是“合同”。

---

## 2. 抽象类与普通类的区别：强制 vs 建议

普通类可以被任意继承和覆盖；抽象类不同：它明确告诉你“这些方法是必须的”，否则连对象都创建不了。

```python
from abc import ABC, abstractmethod

class Payment(ABC):
    @abstractmethod
    def pay(self, amount: float) -> bool:
        ...

class WeChatPay(Payment):
    def pay(self, amount: float) -> bool:
        print(f"微信支付 {amount} 元")
        return True

class Alipay(Payment):
    def pay(self, amount: float) -> bool:
        print(f"支付宝支付 {amount} 元")
        return True

for p in [WeChatPay(), Alipay()]:
    p.pay(100.0)
```

要点：
- 抽象方法是“编译期/实例化时”的强制检查。
- 不同子类只要实现了 `pay`，就可以被统一调用，这叫多态（Polymorphism）。
- 抽象类适合“同一家族、共享部分实现”的场景，也可以在 ABC 中提供普通方法。

---

## 3. 协议（Protocol）：比抽象类更轻的“鸭子类型合同”

Python 有句名言：如果它走起来像鸭子、叫起来像鸭子，那它就是鸭子（Duck Typing）。`typing.Protocol` 把这种思想用类型系统（Type System）表达出来：只要对象有某些方法/属性，就满足协议，不要求继承。

```python
from typing import Protocol

class SupportsRead(Protocol):
    def read(self) -> str:
        ...

def load_text(source: SupportsRead) -> str:
    return source.read()

class StringFile:
    def read(self) -> str:
        return "hello"

class OtherReader:
    def read(self) -> str:
        return "world"

print(load_text(StringFile()))  # hello
print(load_text(OtherReader())) # world
# 这两个类都没有继承 SupportsRead，却都满足协议
```

标准库也大量使用协议，例如：
- `typing.SupportsInt`：只要有 `__int__`。
- `typing.SupportsBytes`：只要有 `__bytes__`。
- `typing.SupportsFloat`：只要有 `__float__`。
- `typing.SupportsRound`：只要有 `__round__`。
- `typing.IO`、`TextIO`、`BinaryIO`：表示文件流类型，但它们不是协议，接口比较宽。
- `io.Reader`、`io.Writer`：更简单的协议，只要求 `read` 或 `write`。

要点：
- 协议不要求继承，只看“有没有这些方法”。
- 协议让类型检查器（如 mypy、pyright）能帮你在静态检查时发现错误。
- 协议适合“不同来源、不同类层次，但能力相同”的场景。

---

## 4. 抽象类 vs 协议：怎么选？

| 维度 | 抽象类 ABC | 协议 Protocol |
|------|------------|---------------|
| 是否要求继承 | 是 | 否 |
| 是否能在运行时强制检查 | 是（实例化时） | 一般靠静态类型检查 |
| 适用场景 | 同一家族、共享实现 | 跨家族、只需能力 |
| 典型例子 | `Shape`、`Payment` | `SupportsInt`、`io.Reader` |

一句话选型：**要“血脉传承”就用抽象类；要“能力匹配”就用协议。**

---

## 5. 工程级用法：按接口编程，不按实现编程

大型工程中，模块之间只通过抽象类或协议交互，具体实现可替换。这叫依赖倒置（Dependency Inversion）。

```python
from abc import ABC, abstractmethod
from typing import Protocol

# 存储抽象：可以是内存、文件、数据库
class Storage(ABC):
    @abstractmethod
    def save(self, key: str, value: str) -> None: ...
    @abstractmethod
    def load(self, key: str) -> str | None: ...

class MemoryStorage(Storage):
    def __init__(self):
        self._data: dict[str, str] = {}
    def save(self, key: str, value: str) -> None:
        self._data[key] = value
    def load(self, key: str) -> str | None:
        return self._data.get(key)

# 日志协议：只要有 write 方法就行
class Writer(Protocol):
    def write(self, s: str) -> int: ...

def audit(storage: Storage, logger: Writer) -> None:
    storage.save("user:1", "Alice")
    logger.write("saved user:1\n")

import sys
audit(MemoryStorage(), sys.stdout)
```

要点：
- 抽象类可以作为“必需实现”的骨架。
- 协议可以让第三方对象（如 `sys.stdout`）无缝接入，无需继承你的类。
- 你的业务代码只依赖接口，测试时可注入假的实现。

---

## 6. 常见误区与注意事项

- **抽象类不能被实例化**，但可以包含已实现的方法，供子类复用。
- **协议不等于运行时检查**：`Protocol` 主要服务于静态类型检查；运行时不会自动阻止你传入不满足的对象。
- **不要滥用抽象**：只有一个实现时，过早抽象会增加复杂度。
- **抽象方法名大小写敏感**：`area` 和 `Area` 不同。
- **`ABC` 与 `Protocol` 可配合使用**：`Protocol` 本身也可以有抽象属性/方法，甚至可 `@runtime_checkable` 做有限的运行时检查。

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class HasLen(Protocol):
    def __len__(self) -> int: ...

print(isinstance([1, 2, 3], HasLen))  # True
print(isinstance(42, HasLen))          # False
```

---

## 动手练习

**任务：设计一个可插拔的“数据导出器”。**

要求：
1. 定义一个抽象类 `Exporter`，包含抽象方法 `export(self, rows: list[dict]) -> str`。
2. 实现两个子类：`CsvExporter`（把行转成 CSV 字符串）和 `JsonExporter`（把行转成 JSON 字符串）。
3. 定义一个协议 `Writable`，要求有 `write(self, s: str) -> int` 方法。
4. 写一个函数 `run(exporter: Exporter, sink: Writable) -> None`，调用 `exporter.export(...)` 并把结果写入 `sink`。
5. 用一个假的 `MemorySink` 类（只需有 `write` 方法）验证协议式调用；再用 `sys.stdout` 直接测试。
6. 额外挑战：给 `Writable` 加上 `@runtime_checkable`，用 `isinstance` 验证 `sys.stdout` 和 `MemorySink` 都满足协议。

提示：
- `CsvExporter` 可用 `"
".join(",".join(row.values()) for row in rows)`。
- `JsonExporter` 用 `import json; json.dumps(rows, ensure_ascii=False)`。
- 运行命令建议：`python -m mypy your_file.py` 观察类型检查结果。

完成后你会同时掌握：抽象类强制接口、协议按能力匹配、以及依赖注入（Dependency Injection）的基本形态。

```python
from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable
import json
import sys


class Exporter(ABC):
    """抽象类：任何导出器必须实现 export"""

    @abstractmethod
    def export(self, rows: list[dict]) -> str:
        """把行数据导出为字符串"""
        ...


class CsvExporter(Exporter):
    def export(self, rows: list[dict]) -> str:
        if not rows:
            return ""
        header = ",".join(rows[0].keys())
        body = "\n".join(
            ",".join(str(v) for v in row.values()) for row in rows
        )
        return f"{header}\n{body}"


class JsonExporter(Exporter):
    def export(self, rows: list[dict]) -> str:
        return json.dumps(rows, ensure_ascii=False, indent=2)


@runtime_checkable
class Writable(Protocol):
    """协议：只要有 write(str) 方法就满足"""

    def write(self, s: str) -> int: ...


class MemorySink:
    """不继承 Writable，但满足协议"""

    def __init__(self) -> None:
        self.buffer: list[str] = []

    def write(self, s: str) -> int:
        self.buffer.append(s)
        return len(s)


def run(exporter: Exporter, sink: Writable) -> None:
    rows = [
        {"id": 1, "name": "Alice"},
        {"id": 2, "name": "Bob"},
    ]
    sink.write(exporter.export(rows))


if __name__ == "__main__":
    # 使用抽象类子类 + 满足协议的内存 sink
    mem = MemorySink()
    run(CsvExporter(), mem)
    print("MemorySink 收到的内容：")
    print("".join(mem.buffer))

    # 使用 JSON 导出器 + 标准输出（满足 Writable 协议）
    print("\n--- 使用 sys.stdout ---")
    run(JsonExporter(), sys.stdout)

    # 运行时协议检查
    print("\n\nsys.stdout 满足 Writable？", isinstance(sys.stdout, Writable))
    print("mem 满足 Writable？", isinstance(mem, Writable))

    # 尝试实例化抽象类会失败，取消注释可验证：
    # Exporter()  # TypeError: Can't instantiate abstract class
```

## py.oop.protocol

# Python 协议（Protocol）：让鸭子类型（Duck Typing）可被静态类型检查器理解

> **一句话直觉**：Python 是“鸭子类型”的语言——“看起来像鸭子、走起来像鸭子，就是鸭子”。但类型检查器（mypy、pyright）看不懂这种“看起来像”，`Protocol` 就是把这句口头禅写成一份可被静态检查的“接口合同（interface contract）”。

---

## 1. 从“鸭子类型”的痛点讲起

传统 Python 面向对象（OOP）用继承表达“是什么”：

```python
class Dog:
    def quack(self): print("woof")

def say(q):          # 注解写什么？
    q.quack()
```

`say()` 参数注解如果写 `Dog`，那么任何“不是 Dog 但有 `quack`”的对象在 mypy 下都会报错——而这恰恰是 Python 运行时最常用的用法。问题核心：**运行时看的是“有没有这个方法”，静态检查看的是“是不是这个类”。**

`Protocol` 解决这个裂缝：用结构（structure）而不是继承（inheritance）作为类型依据。

---

## 2. 定义并实现一个 Protocol

`Protocol`（协议）来自标准库 `typing`。定义时用 `class X(Protocol)`，方法体用 `...` 表示只声明、不实现。任何类只要“结构对得上”，就被静态类型检查器视为该协议的实例——**不需要显式继承**。

```python
from typing import Protocol

class Quacker(Protocol):
    def quack(self) -> str: ...

class Duck:
    def quack(self) -> str:
        return "quack"

class Robot:
    def quack(self) -> str:
        return "beep"

def announce(q: Quacker) -> None:
    print(q.quack())

announce(Duck())   # OK
announce(Robot())  # OK —— 没有继承 Quacker，也通过类型检查
```

**关键结论**：协议是“隐式实现（implicit implementation）”。类型检查器只看方法/属性的名字是否齐全，不管继承链。

---

## 3. 用 @runtime_checkable 做运行时检查

默认情况下，`Protocol` 只在**静态类型检查**阶段生效，`isinstance()` / `issubclass()` 会直接抛 `TypeError`。如果你想在**运行时**也用 `isinstance` 判断，需要加 `@runtime_checkable` 装饰器。

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class Quacker(Protocol):
    def quack(self) -> str: ...

print(isinstance(Duck(), Quacker))   # True
print(isinstance(Robot(), Quacker))  # True
print(isinstance(42, Quacker))       # False
```

**必须记住的两个陷阱**：

1. `@runtime_checkable` **只检查方法/属性是否存在，不检查类型签名**。例如 `ssl.SSLObject` 有 `__init__`，所以能通过 `Callable` 的 `issubclass` 检查，但它在运行时其实不可调用（只用于抛 `TypeError`）。
2. 对 `runtime_checkable` 协议做 `isinstance` 检查**性能明显慢于普通类**——在性能敏感代码里，可以退化为 `hasattr()` 手动判断。
3. 从 Python 3.12 起，内部实现改用 `inspect.getattr_static()` 查找属性（以前是 `hasattr()`），且协议成员在类创建后“冻结”：即使后续 monkey-patch 增加属性，也不会影响 `isinstance` 结果。
4. Python 3.15 起，对“**未显式加 `@runtime_checkable`**、但继承自 runtime-checkable 协议的类”调用 `isinstance` / `issubclass` 已弃用，将在 3.20 抛 `TypeError`——**装饰器要写在直接被检查的协议上**。

---

## 4. 让协议更有表达力：属性、泛型与工具函数

协议里不仅可以写方法，还可以写**属性**（只需注解，不赋值）：

```python
from typing import Protocol, get_protocol_members

class Sized2(Protocol):
    size: int
    def resize(self, n: int) -> None: ...

print(get_protocol_members(Sized2))
# frozenset({'size', 'resize'})   —— Python 3.13+
```

协议支持泛型（使用 PEP 695 语法）：

```python
from typing import Protocol

class Container[T](Protocol):
    def get(self) -> T: ...
```

标准库还提供了一组**开箱即用的协议**，比如 `SupportsInt`、`SupportsFloat`、`SupportsBytes`、`SupportsIndex`、`SupportsRound`——当你只想表达“这个对象能 `int()` 出来”时，用它们远比写一个自定义类更贴切。

---

## 5. 与 abc/ABC、TypedDict 的关系（一句话区分）

- `abc.ABC`：**显式继承**才成为子类，运行时 `isinstance` 靠 `__subclasshook__` / 注册。
- `Protocol`：**隐式结构匹配**，天然贴合 Python 动态风格；`@runtime_checkable` 后既能过 mypy，又能过 `isinstance`。
- `TypedDict`：把“字典”的结构约束下来，同样只在静态阶段检查，运行时仍是普通 `dict`。它跟 Protocol 都是“结构类型（structural typing）”家族，但用途不同。

---

## 动手练习

**任务**：定义一个 `Repository` 协议，要求实现方具备 `get(id: int) -> dict` 与 `save(data: dict) -> None`。

1. 不加 `@runtime_checkable`，写两个实现类：一个是真的内存仓库 `MemoryRepo`，一个是“伪装仓库” `FakeRepo`（只有 `get` 没有 `save`）。用 mypy 检查，`FakeRepo` 应该被报错。
2. 给 `Repository` 加上 `@runtime_checkable`，在运行时用 `isinstance` 判断上面两个实例，并打印结果（提示：`FakeRepo` 会返回 `False`，因为缺 `save`）。
3. 思考题：为什么 `isinstance(FakeRepo(), Repository)` 返回 `False`，即使 `FakeRepo` 有 `get` 方法？把它写在代码注释里。

**进阶**：把 `Repository` 改成泛型协议 `Repository[T]`，`get` 返回 `T`，`save` 接收 `T`，然后用 `MemoryRepo` 实现 `Repository[dict]`。

```python
# 可运行示例：Protocol 的静态 + 运行时双向检查
from typing import Protocol, runtime_checkable

@runtime_checkable
class Repository(Protocol):
    def get(self, id: int) -> dict: ...
    def save(self, data: dict) -> None: ...

class MemoryRepo:
    def __init__(self) -> None:
        self._db: dict[int, dict] = {}
    def get(self, id: int) -> dict:
        return self._db.get(id, {})
    def save(self, data: dict) -> None:
        self._db[data['id']] = data

class FakeRepo:
    def get(self, id: int) -> dict:   # 缺 save，结构不完整
        return {'id': id}

m, f = MemoryRepo(), FakeRepo()
print(isinstance(m, Repository))  # True：get 和 save 都具备
print(isinstance(f, Repository))  # False：缺 save

# 注意：@runtime_checkable 只查名字，不查签名
# 下面这个类 get 的参数类型不对，但仍会通过 isinstance
class SloppyRepo:
    def get(self, id: str) -> dict: ...
    def save(self, data: dict) -> None: ...
print(isinstance(SloppyRepo(), Repository))  # True —— 运行时不检查签名
```

## py.oop.duck_typing

# 鸭子类型（Duck Typing）：Python 动态多态的精髓

## 一句话直觉

**“如果它走起来像鸭子，叫起来像鸭子，那它就是鸭子。”**  
在 Python 中，你不需要关心对象“是什么类”，只需要关心它“能做什么”——只要对象有你需要的方法或属性，就可以拿来用。这就是鸭子类型（Duck Typing），它让代码更灵活、更通用，也是 Python 多态（polymorphism）最自然的实现方式。

---

## 1. 为什么需要鸭子类型？从“类型检查”说起

在静态类型语言（如 Java、C++）中，函数通常要求参数必须是某个特定类或其子类。例如，一个 `print_area(shape)` 函数可能要求 `shape` 是 `Shape` 类型。但在 Python 中，我们更关心对象**是否支持我们调用的操作**。

```python
# 示例：两个毫不相关的类，只要都有 area() 方法，就能被同一个函数处理
class Circle:
    def __init__(self, r):
        self.r = r
    def area(self):
        return 3.14 * self.r ** 2

class Rectangle:
    def __init__(self, w, h):
        self.w = w
        self.h = h
    def area(self):
        return self.w * self.h

def print_area(shape):
    # 不检查 shape 是什么类型，只调用它的 area() 方法
    print(f"面积是: {shape.area()}")

print_area(Circle(2))       # 面积是: 12.56
print_area(Rectangle(3, 4)) # 面积是: 12
```

**关键结论**：Python 的函数参数没有类型限制，只要传入的对象**在运行时**拥有所需的方法（这里是 `area()`），调用就能成功。这就是鸭子类型的核心——**运行时决定，而非编译时决定**。

---

## 2. 鸭子类型与多态：同一接口，不同实现

多态（polymorphism）指“同一操作作用于不同对象，产生不同结果”。鸭子类型让多态变得极其简单：不需要继承同一个基类，也不需要实现同一个接口，只要方法名相同即可。

```python
class Dog:
    def speak(self):
        return "汪汪"

class Cat:
    def speak(self):
        return "喵喵"

class Robot:
    def speak(self):
        return "哔哔"

def make_sound(animal):
    # 传入任何有 speak() 方法的对象都可以
    print(animal.speak())

for obj in [Dog(), Cat(), Robot()]:
    make_sound(obj)
# 输出：汪汪 / 喵喵 / 哔哔
```

**关键结论**：鸭子类型实现了“隐式接口”——不靠 `interface` 关键字，而靠**方法的存在性**来约定协议。这使代码更松耦合，更容易扩展：新增一个类，只要实现 `speak()`，就能无缝接入。

---

## 3. 鸭子类型与内置协议：Python 的“魔法方法”

Python 中许多内置操作都依赖鸭子类型。例如，`len(obj)` 实际上调用 `obj.__len__()`；`for x in obj` 调用 `obj.__iter__()`。任何实现了这些方法的类，都能融入 Python 的语法生态。

```python
class MyList:
    def __init__(self, data):
        self.data = data
    def __len__(self):
        return len(self.data)
    def __iter__(self):
        return iter(self.data)

ml = MyList([1, 2, 3])
print(len(ml))        # 3，因为实现了 __len__
for x in ml:          # 可迭代，因为实现了 __iter__
    print(x)
```

**关键结论**：鸭子类型不仅适用于自定义方法，也适用于 Python 的**数据模型协议**（如 `__len__`、`__iter__`、`__getitem__` 等）。实现这些“魔法方法”，对象就能像内置类型一样被使用。

---

## 4. 鸭子类型 vs 类型提示（Type Hints）：互补而非冲突

Python 3.5+ 引入了类型提示（type hints），但它**不会在运行时强制检查**。类型提示主要用于静态分析工具（如 mypy、IDE），帮助提前发现错误。鸭子类型依然有效：你可以写 `def f(x: SomeProtocol)` 来声明“x 需要满足某些方法”，但运行时仍接受任何有这些方法的对象。

```python
from typing import Protocol

class Speaker(Protocol):
    def speak(self) -> str: ...

def greet(s: Speaker) -> None:
    print(s.speak())

class Duck:
    def speak(self) -> str:
        return "嘎嘎"

greet(Duck())  # 合法：Duck 有 speak 方法，即使没有显式继承 Speaker
```

**关键结论**：`Protocol` 是鸭子类型的“静态表达”。它让类型检查器理解“只要满足方法签名即可”，而不是要求继承。运行时依旧遵循鸭子类型——有方法就能用。

---

## 5. 工程实践：如何用好鸭子类型？

- **优点**：灵活、可扩展、代码简洁，适合快速开发和插件式架构。
- **风险**：错误可能延迟到运行时才暴露（如拼错方法名）。
- **应对**：
  - 使用 `hasattr()` 或 `callable()` 做防御性检查（慎用，可能破坏多态）。
  - 结合 `Protocol` 和类型检查器（mypy）提前发现接口不匹配。
  - 编写清晰的文档，说明期望的方法。
  - 单元测试覆盖不同实现。

```python
def safe_call(obj):
    if hasattr(obj, 'speak') and callable(obj.speak):
        obj.speak()
    else:
        print("对象不支持 speak 方法")
```

**关键结论**：鸭子类型是 Python 动态多态的基石。理解它，就能写出更 Pythonic、更灵活的代码；配合类型提示，可以在灵活性和安全性之间取得平衡。

---

## 动手练习

**任务**：创建一个 `Playlist` 类，它内部存储一个列表。要求：
- 实现 `__len__`，使 `len(playlist)` 返回歌曲数量。
- 实现 `__iter__`，使 `for song in playlist` 能遍历歌曲。
- 实现 `add_song(song)` 方法添加歌曲。
- 再写一个函数 `play_all(playlist)`，它接受任何“可迭代且长度可用”的对象（即实现了 `__iter__` 和 `__len__`），打印每首歌并显示总数。
- 测试：用 `Playlist` 实例和一个普通列表分别调用 `play_all`，观察鸭子类型如何让两者都能工作。

```python
# 你的代码写在这里
```

**提示**：普通列表本身就有 `__len__` 和 `__iter__`，所以 `play_all(["a", "b"])` 应该也能运行。

```python
# 鸭子类型完整示例：不同类只要方法相同，就能被同一函数处理

class Duck:
    def quack(self):
        return "嘎嘎叫"

class Person:
    def quack(self):
        return "模仿鸭子叫"

class Robot:
    def quack(self):
        return "电子合成嘎嘎声"

def make_it_quack(duck_like):
    # 不检查类型，只调用 quack 方法
    print(duck_like.quack())

# 三个完全无关的类，都能被 make_it_quack 处理
for obj in [Duck(), Person(), Robot()]:
    make_it_quack(obj)

# 输出：
# 嘎嘎叫
# 模仿鸭子叫
# 电子合成嘎嘎声
```


---

## 本课题目

### single_choice · None



- [A] 使用 @abc.abstractmethod 装饰器修饰方法，并让类继承 abc.ABC
- [B] 在方法体里写 raise NotImplementedError 即可，无需任何装饰器
- [C] 使用 @abstractmethod 装饰器，但类不需要继承任何基类
- [D] 把方法名前面加上两个下划线使其变为抽象方法

**参考答案**：0

**解析**：abc.ABC 与 @abc.abstractmethod 搭配是标准做法；仅 raise NotImplementedError 只是运行时报错，不阻止实例化；@abstractmethod 必须与 ABC 或 ABCMeta 元类配合才生效；双下划线只是名称改写，与抽象无关。

### single_choice · None



- [A] 正常创建 Base 实例
- [B] 抛出 TypeError，提示不能实例化抽象类
- [C] 抛出 AttributeError
- [D] 抛出 NotImplementedError

**参考答案**：1

**解析**：含有未实现抽象方法的 ABC 子类无法被实例化，Python 会抛出 TypeError。NotImplementedError 只是方法体内 raise 时才触发，与实例化无关。

### single_choice · None



- [A] 不能，因为 super().f() 不存在
- [B] 可以，Sub 已覆盖实现 f
- [C] 不能，因为 Base.f 没有函数体
- [D] 不能，因为 ABC 子类必须先注册

**参考答案**：1

**解析**：Sub 覆盖了抽象方法 f，满足实例化条件；Base.f 虽然函数体为空仍然是可调用对象，且代码中 if False 使该分支不会真正执行。

### single_choice · None



- [A] @classmethod
  @abc.abstractmethod
  def m(cls): ...
- [B] @abc.abstractmethod
  @classmethod
  def m(cls): ...
- [C] @abc.abstractclassmethod
  def m(cls): ...
- [D] @abc.abstractmethod
  def m(self): ... 并加 @staticmethod

**参考答案**：0

**解析**：正确顺序是 @classmethod 在最外层、@abc.abstractmethod 在内层，这样类方法保持抽象性。顺序反了会退化为普通类方法，abstractclassmethod 已被弃用。

### single_choice · None



- [A] True
- [B] False
- [C] 抛出 TypeError
- [D] 打印 None

**参考答案**：0

**解析**：B 实现了抽象方法，可以实例化且是 A 的实例，isinstance 返回 True。抽象基类仍遵循常规继承关系。

### single_choice · None



- [A] register 可把不相关的类注册为抽象基类的虚拟子类，但不检查抽象方法实现
- [B] register 会强制被注册类实现所有抽象方法
- [C] register 只能注册抽象类本身
- [D] register 会把被注册类的抽象方法自动实现

**参考答案**：0

**解析**：register 用于声明虚拟子类关系，isinstance/issubclass 会返回 True，但不会检查或补全抽象方法实现。

### single_choice · None



- [A] 抽象类本身不可被实例化，即使它的抽象方法都有默认实现
- [B] 抽象类可以被实例化，只要不调用抽象方法
- [C] 抽象类可以被实例化，Python 会自动用 None 实现抽象方法
- [D] 抽象类可以被实例化，但必须先删除抽象方法

**参考答案**：0

**解析**：只要类中仍标记有未被子类覆盖的抽象方法，即使抽象方法体有默认实现，该抽象类也不能被实例化。

### single_choice · None



- [A] 可以实例化，C 实现了 m，抽象约束沿继承链传递
- [B] 不能实例化，因为 B 是抽象类
- [C] 不能实例化，因为 C 没有直接继承 A
- [D] 不能实例化，因为抽象方法不能被多层覆盖

**参考答案**：0

**解析**：抽象方法沿继承链传递，C 通过覆盖 m 满足了所有要求，因此可以实例化。

### single_choice · None



- [A] import abc 时
- [B] 定义 class B 时
- [C] 执行 b = B() 时
- [D] 不会抛异常

**参考答案**：2

**解析**：定义 B 时不会立即检查抽象方法实现；异常在尝试实例化 B 时以 TypeError 形式抛出。

### single_choice · None



- [A] @abc.abstractproperty 已弃用，推荐用 @property 叠加 @abc.abstractmethod
- [B] 两者效果完全相同，没有弃用问题
- [C] @property 不能与 @abc.abstractmethod 组合
- [D] @abc.abstractproperty 只能用于类属性

**参考答案**：0

**解析**：从 Python 3.3 起 @abc.abstractproperty 被弃用，推荐将 @property 与 @abc.abstractmethod 组合使用。

### single_choice · None



- [A] 15
- [B] 10
- [C] 抛出 TypeError
- [D] 抛出 NotImplementedError

**参考答案**：0

**解析**：抽象方法允许有实现体，B.m 通过 super().m() 调用父类默认实现返回 10，再加 5 得到 15。

### single_choice · None



- [A] 调用抽象基类的 register 方法注册该类
- [B] 在第三方类上加 @abc.abstractmethod
- [C] 修改第三方类的 __bases__ 使其继承抽象基类再回滚
- [D] 在抽象基类中实现第三方类的所有方法

**参考答案**：0

**解析**：register 提供虚拟子类注册机制，使得第三方类通过 isinstance/issubclass 检查而不需要真正改变继承结构。其他选项要么不成立，要么是错误做法。

### single_choice · None



- [A] Child 没有实现 foo
- [B] Child 没有实现 bar
- [C] Child 没有继承 abc.ABC
- [D] Child 的 foo 返回值类型不对

**参考答案**：1

**解析**：子类必须实现父类中全部抽象方法才能实例化；Child 仅实现了 foo，缺少 bar。返回值类型与抽象方法约束无关。

### single_choice · None



- [A] 它只能用于静态方法，不能用于普通实例方法
- [B] 它修饰的方法可以包含实现代码，子类可用 super() 调用它
- [C] 被它修饰的方法在父类中不能有函数体
- [D] 它只能和 @property 一起使用

**参考答案**：1

**解析**：抽象方法允许有实现体，子类可以覆盖后通过 super() 调用；它可用于实例方法、类方法、静态方法等多种形式；父类中也可以写函数体；与 @property 搭配是可选用法之一，但不是唯一用法。

### single_choice · None



- [A] 可以，Square 实现了所有抽象方法
- [B] 不可以，Shape 仍有抽象方法
- [C] 不可以，__init__ 也需要是抽象方法
- [D] 不可以，ABC 需要显式调用 __init__

**参考答案**：0

**解析**：Square 完整实现了 area，因此可以实例化。ABC 不需要在子类中显式调用 __init__，__init__ 也不是抽象方法。

### single_choice · None



- [A] Mixin 中可以同时包含抽象方法和普通方法
- [B] Mixin 中的所有方法都会自动变成抽象方法
- [C] 普通方法 helper 会阻止 Mixin 被继承
- [D] ABC 子类不允许定义普通方法

**参考答案**：0

**解析**：抽象基类可同时包含抽象方法和普通（已实现）方法，子类只需实现抽象方法即可。其他选项均属误解。

### single_choice · None



- [A] 无输出，Q 可以实例化
- [B] 输出 TypeError
- [C] 输出 NotImplementedError
- [D] 输出 AttributeError

**参考答案**：1

**解析**：Q 未实现抽象方法 m，因此实例化时会抛出 TypeError，被 except 捕获并打印。

### single_choice · None



- [A] 必须写成 pass 或 ...，不能有任何语句
- [B] 可以写实现代码，子类常用 super() 调用
- [C] 不能包含 return 语句
- [D] 只能写 raise NotImplementedError

**参考答案**：1

**解析**：抽象方法可以写实现体，常见模式是父类提供默认逻辑，子类通过 super() 复用；并不强制只能写 pass、... 或 raise。

### single_choice · None



- [A] A 未继承 abc.ABC 或使用 ABCMeta，抽象约束不生效，a 能创建
- [B] abstractmethod 装饰器不存在，会 ImportError
- [C] a 的创建会抛出 TypeError
- [D] m 会被自动转成类方法

**参考答案**：0

**解析**：仅使用 @abstractmethod 而不通过 ABC 或 ABCMeta 元类时，抽象约束不会生效，类仍可实例化。装饰器确实存在于 abc 模块中，不会 ImportError。

### single_choice · None



- [A] 它是 abc 模块提供的元类，可让普通类具备抽象约束能力
- [B] 它只能用于 Python 2，Python 3 中已移除
- [C] 它能自动为子类生成所有抽象方法的实现
- [D] 它只能用于多重继承场景

**参考答案**：0

**解析**：ABCMeta 是 abc 模块中的元类，Python 3 仍然可用；它不会自动生成实现；也不限于多重继承。

### single_choice · None



- [A] 一个类必须显式继承某个抽象基类，才能被 for 循环迭代
- [B] 只要对象实现了所需的方法（如 __iter__、__len__），它就能配合相应的语法或内置函数工作
- [C] 协议要求对象必须注册到某个全局注册表中才生效
- [D] 只有内置类型才能满足协议，用户自定义类无法满足

**参考答案**：1

**解析**：Python 采用「鸭子类型」式的协议：只要对象在运行时具备所需的方法（如 __iter__ 支持迭代、__len__ 支持 len()），就能配合相应语法工作，无需继承或注册。

### single_choice · None



- [A] __length__
- [B] __size__
- [C] __len__
- [D] __count__

**参考答案**：2

**解析**：len() 会调用对象的 __len__ 方法，它应返回一个非负整数。其它名称并非 Python 的协议方法。

### single_choice · None



- [A] 1 2 2
- [B] 0 0 0
- [C] 1 1 1
- [D] 报错：Counter 不可调用

**参考答案**：0

**解析**：实现了 __call__ 的实例可像函数一样被调用。每次调用 n 自增 1，所以返回 1、2，n 最终为 2。这体现了可调用对象协议。

### single_choice · None



- [A] class MyClass(Protocol): pass
- [B] 让类结构化地实现所需方法；在静态类型检查语境下用 Protocol 做结构化子类型标注
- [C] 在类中写 @protocol 装饰器
- [D] 调用 register(MyClass) 注册到 typing 模块

**参考答案**：1

**解析**：typing.Protocol 支持结构化子类型：只要类实现了协议中声明的方法，类型检查器就认为它满足该协议，无需显式继承。@protocol 装饰器并不存在。

### multi_choice · None



- [A] __iter__
- [B] __len__
- [C] __enter__ 和 __exit__
- [D] __repr__
- [E] __main__

**参考答案**：[0, 1, 2, 3]

**解析**：__iter__ 支持迭代，__len__ 支持 len()，__enter__/__exit__ 支持 with，__repr__ 支持 repr()。__main__ 只是一个模块级名称约定，不是特殊方法。

### multi_choice · None



- [A] 对象未定义 __bool__ 时，会退回到调用 __len__
- [B] __bool__ 应返回一个布尔值
- [C] 只要对象非 None，bool(obj) 一定为 True
- [D] 如果同时定义了 __bool__ 和 __len__，优先使用 __bool__
- [E] bool(obj) 会直接调用 __nonzero__（Python 3 中）

**参考答案**：[0, 1, 3]

**解析**：Python 3 中：优先 __bool__，其次 __len__（返回 0 则假）；__bool__ 应返回布尔值。__nonzero__ 是 Python 2 的名字，Python 3 不再使用。对象为假不一定只因是 None，例如空列表也为假。

### multi_choice · None



- [A] 定义 __iter__ 返回 self，并定义 __next__ 在耗尽时抛出 StopIteration
- [B] 定义 __iter__ 返回一个生成器对象
- [C] 只定义 __next__ 而不定义 __iter__
- [D] 定义 __iter__ 返回一个列表
- [E] 定义 __iter__ 返回新的独立迭代器对象，每次迭代互不影响

**参考答案**：[0, 1, 4]

**解析**：迭代器协议要求 __iter__（返回迭代器自身或新迭代器）和 __next__（返回值或抛 StopIteration）。只定义 __next__ 不是迭代器（for 会报 TypeError）；__iter__ 返回列表是「可迭代对象」而非迭代器本身，但它确实能被 for 使用——不过在「作为迭代器」的标准语义上应返回迭代器。第 5 项是更安全的可迭代对象做法。

### fill_blank · None



**参考答案**：["__enter__ __exit__", "__enter__,__exit__", "__enter__ 和 __exit__", "__enter__和__exit__"]

**解析**：with 语句依赖上下文管理器协议，要求 __enter__（进入时调用）和 __exit__（退出时调用，负责清理/异常处理）同时存在。

### fill_blank · None



**参考答案**：["__len__ __getitem__", "__len__, __getitem__", "__len__ 和 __getitem__", "__len__和__getitem__"]

**解析**：len() 调用 __len__，下标读取 obj[key] 调用 __getitem__。两者都是常见的协议方法。

### code_reading · None



**参考答案**：[10, 20, 30]

**解析**：Wrap 没有定义 __iter__，但定义了 __getitem__，Python 会使用旧式序列迭代协议，从下标 0 开始依次取元素直到 IndexError，因此 list(w) 得到 [10, 20, 30]。

### code_reading · None



**参考答案**：因为 Point 实现了 __repr__，repr() 会调用它，返回自定义字符串 "Point(1, 2)"，而不是默认的 <Point object at 0x...>。

**解析**：__repr__ 属于对象表示协议。实现后，repr() 和交互式回显都会使用它；未定义时才退回默认形式（含内存地址）。

### scenario · None



**解析**：需要实现上下文管理器协议：__enter__ 建立/返回连接（供 as 使用），__exit__ 负责关闭连接；即使 with 块抛出异常，__exit__ 也会被调用，可在其中清理资源。

### single_choice · None



- [A] __next__
- [B] __iter__
- [C] __getitem__ 且必须同时实现 __len__
- [D] __iter__ 或 __getitem__ 之一即可（旧式序列协议）

**参考答案**：3

**解析**：现代做法是实现 __iter__ 返回迭代器；作为兼容，若类实现了 __getitem__，Python 也能以整数下标方式迭代（旧式序列协议）。因此 __iter__ 或 __getitem__ 之一即可让 for 工作。

### scenario · None



**解析**：只实现 __getitem__ 的对象可被 for 迭代（旧式序列协议），属于「可迭代对象」，但它本身不是迭代器（未定义 __iter__ 和 __next__）。若希望在多次迭代中互不影响、语义清晰，应实现 __iter__ 返回一个新的独立迭代器。

### single_choice · None



- [A] True 3
- [B] False 3
- [C] True 0
- [D] 报错：Box 没有定义 __bool__

**参考答案**：0

**解析**：当对象没有定义 __bool__ 时，bool() 会退回到调用 __len__；长度为 3 非零，因此为 True。这也是「真值测试协议」的一部分。

### single_choice · None



- [A] 只要实现了 __enter__ 就能用于 with 语句，__exit__ 可选
- [B] 必须同时实现 __enter__ 和 __exit__，with 语句才会正常工作
- [C] 上下文管理器必须继承 contextlib.ContextDecorator
- [D] with 语句只能用于文件对象

**参考答案**：1

**解析**：with 语句要求对象同时具备 __enter__ 和 __exit__ 两个方法，构成完整的上下文管理器协议。缺少任一个都会在运行时报错。

### single_choice · None



- [A] 协议必须通过继承实现，抽象基类通过实现方法即可
- [B] 抽象基类需要显式继承或注册，协议是隐式的、只在运行时检查所需方法
- [C] 两者完全等价，只是名字不同
- [D] 协议只能用于内置类型，抽象基类只能用于自定义类型

**参考答案**：1

**解析**：抽象基类通过继承或 register 建立名义上的关联；协议（如迭代、上下文管理）是隐式的，只要对象具备相应方法即可，无需继承关系。

### single_choice · None



- [A] __eq__
- [B] __cmp__
- [C] __equals__
- [D] __compare__

**参考答案**：0

**解析**：== 运算符会调用左操作数的 __eq__ 方法。__cmp__ 是 Python 2 的旧协议，Python 3 已移除。

### single_choice · None



- [A] def __enter__(self): return self
- [B] def __enter__(self, exc_type): return self
- [C] def __enter__(): pass
- [D] def __enter__(self): pass  # 无需返回值

**参考答案**：0

**解析**：__enter__ 接收 self 并返回一个值，该值赋给 as 后的变量。第一项符合协议；第三项缺少 self；第二项参数签名错误；第四项返回 None 使 as 变量为 None。

### single_choice · None



- [A] 只要实现了 __getitem__，就一定能对对象使用 for 循环（旧式协议）
- [B] 实现了 __getitem__ 后必须再实现 __iter__ 才能 for 循环
- [C] __getitem__ 与迭代完全无关
- [D] __getitem__ 只能接受字符串键

**参考答案**：0

**解析**：若对象没有 __iter__ 但有 __getitem__，for 会从索引 0 开始依次调用 obj[0]、obj[1]……直到 IndexError。这就是旧式序列迭代协议。

### single_choice · None



- [A] __plus__
- [B] __add__
- [C] __concat__
- [D] __sum__

**参考答案**：1

**解析**：二元 + 运算符会调用左操作数的 __add__（必要时回退到右操作数的 __radd__）。其它名称不是 Python 协议方法。

### single_choice · None



- [A] 一个对象只要继承自某个特定基类，就能被当作该类型使用
- [B] 一个对象只要具备所需的方法/属性，就能在该场景中被当作相应类型使用
- [C] 只有显式实现了某个接口（Protocol）并注册的对象才能被使用
- [D] 鸭子类型要求对象的类型在运行时不能被修改

**参考答案**：1

**解析**：鸭子类型的核心是「关注行为而非类型」：只要对象提供了调用方需要的方法或属性，就可以在该场景中使用，不要求继承关系。继承是名义类型（nominal typing）的思路；Protocol 是静态检查工具对结构化类型的支持，并非运行时前提；鸭子类型与对象能否被修改无关。

### single_choice · None



- [A] list 和 2
- [B] str 和 [a, b, c]
- [C] list 和 [a, b, c]
- [D] TypeError 和 2

**参考答案**：0

**解析**：process 只依赖传入对象具有 parse 方法，这就是鸭子类型。Parser.parse 返回 list，Counter.parse 返回 int（'a,b,c' 中有 2 个逗号）。因此第一次打印类型名 list，第二次打印 2。两个类没有继承关系也不影响调用。

### multi_choice · None



- [A] 在文档或类型注解中明确说明对象需要提供哪些方法/属性
- [B] 对外部传入的对象做必要的属性检查或使用 try/except 处理缺失方法
- [C] 为协作的多个实现类抽取共同的 Protocol 或用测试固定其接口
- [D] 把所有对象的类型都限制为 object，避免任何类型信息
- [E] 依赖对象恰好有某个方法，出错时不做任何处理

**参考答案**：[0, 1, 2]

**解析**：文档/注解说明接口、属性检查与异常处理、用 Protocol 或测试固定接口，都能在保持鸭子类型灵活性的同时降低运行时风险。把类型都放宽到 object 并放弃信息，或者完全不处理错误，只会让问题更晚暴露。

### multi_choice · None



- [A] 鸭子类型不要求两个类之间有继承关系
- [B] 一个类即使不继承任何基类，只要具备所需方法也能被鸭子类型使用
- [C] 鸭子类型意味着继承完全无用
- [D] 继承仍可用于复用实现，而鸭子类型关注的是行为兼容
- [E] 如果一个对象没有继承某个类，就一定不能被传给需要该类型的方法

**参考答案**：[0, 1, 3]

**解析**：鸭子类型不依赖继承，具备所需行为即可使用；继承仍然有价值，用于复用实现和表达「是某种类型」的关系，两者关注点不同。真正不成立的是「没有继承就一定不能用」以及「继承完全无用」，它们把继承和鸭子类型对立化了。

### fill_blank · None



**参考答案**：["duck typing", "duck_typing", "Duck typing", "Duck Typing"]

**解析**：这种按行为而非类型判断的风格即 duck typing（鸭子类型）。它不要求继承关系，只要对象能响应被调用的方法或属性即可。

### fill_blank · None



**参考答案**：["area", "area()", "area 方法", ".area", "area方法"]

**解析**：列表推导对每个 s 调用 s.area()，因此鸭子类型视角下要求每个元素具备 area 方法（可调用），具体是什么类并不重要。

### fill_blank · None



**参考答案**：["AttributeError", "AttributeError异常", "attributeerror", "Attribute Error"]

**解析**：属性查找失败（例如对象没有该属性/方法）会抛出 AttributeError，这是鸭子类型调用常见的失败形式。它不是类型继承检查失败，而是属性访问失败。

### code_reading · None



**参考答案**：AB

**解析**：talk 只依赖参数具备 speak 方法，A 和 B 都满足，因此 talk(A()) 返回 'A'，talk(B()) 返回 'B'，字符串相加得到 'AB'。这里没有继承关系，体现了鸭子类型。

### code_reading · None



**参考答案**：第一次输出 'LOG: hi'，第二次输出 'no logger'。record 通过 hasattr 检测对象是否具备 log 能力，从而在缺失该方法时走兜底分支，避免直接调用抛出 AttributeError。

**解析**：鸭子类型的理想情况是「有方法就调用」，但可选能力需要用能力检测（hasattr/getattr/try-except）来安全处理。Logger 有 log，所以返回格式化字符串；Silent 没有 log，被兜底分支处理，避免了 AttributeError。

### code_reading · None



**参考答案**：会抛出 AttributeError，因为 Touchpad 没有 click 方法，use_device 在运行时调用 device.click() 时属性查找失败。问题在于把「有 click 能力」当成了隐含前提，而传入的对象不具备该能力。

**解析**：这是鸭子类型常见的运行时失败：调用方隐式要求 click 方法，但传入对象只提供 tap。若要支持多种设备，应统一接口（例如都提供 click），或在调用前做能力检查，或使用 Protocol 明确契约。

### scenario · None



**解析**：该函数依赖对象具备 write 能力，属于鸭子类型。由于类型信息在运行时才解析，缺少方法只能在调用时暴露为 AttributeError。改进方式包括：用文档/类型注解或 Protocol 明确 write 契约；在函数入口做 hasattr/callable 能力检查或输入校验；统一协作对象的接口（让新对象也提供 write）；在测试中覆盖不同实现的接口一致性。

### scenario · None



**解析**：这些代码能工作是因为 Python 的许多操作按能力判断：可迭代只要求 __iter__（或 __getitem__），len() 只要求 __len__，+ 只要求实现了相应运算符方法，这就是鸭子类型。为每个对象强加显式继承并不必要：继承可用于复用实现或表达类型关系，但并不会自动带来鸭子类型所要求的接口兼容；更合适的做法是用 Protocol/文档/测试明确这些能力契约，并在必要处做能力检查。

### single_choice · None



- [A] 鸭子类型只能用于静态类型语言
- [B] 基于继承的多态要求对象属于同一继承体系，而鸭子类型只要求对象具备相容的行为
- [C] 鸭子类型不允许把一个类的实例传给另一个类的参数
- [D] 基于继承的多态在运行时无法解析方法调用

**参考答案**：1

**解析**：基于继承的多态通过共同的基类/虚函数建立「是某种类型」的关系；鸭子类型不关心继承，只关心对象是否能响应调用方使用的方法或属性。其余选项均与实际相反：鸭子类型常见于动态类型语言，实例可以跨类传递，方法在运行时才解析。

### scenario · None



**解析**：isinstance(obj, A) 基于名义类型，只接受 A 及其子类，与鸭子类型「按能力判断」的思想冲突：B 明明有 save 能力，却因不属于 A 继承体系而被拒。更符合鸭子类型的写法是检查能力（如 hasattr(obj, 'save') 或 callable(getattr(obj, 'save', None))），并用 Protocol/文档/测试明确 save 契约，让 A 和 B 都能被接受。

### single_choice · None



- [A] 只用一个实现了全部所需方法的「理想」对象进行测试
- [B] 用一个缺少某个所需方法的对象测试，看是否抛出 AttributeError
- [C] 只测试函数在空输入下的返回值
- [D] 只看函数的文档字符串是否符合规范

**参考答案**：1

**解析**：鸭子类型的风险在于运行时才发现接口不匹配。用一个缺少所需方法的对象去调用，可以验证程序是否会抛出 AttributeError，从而暴露对具体方法的隐式依赖。只测理想对象或空输入都可能掩盖问题。

### single_choice · None



- [A] 正常返回 'woof'
- [B] 抛出 AttributeError，因为 NoQuack 没有 quack 方法
- [C] 抛出 TypeError，因为 NoQuack 不是 Duck 的子类
- [D] 返回 None

**参考答案**：1

**解析**：鸭子类型只要求对象在运行时提供被调用的方法。NoQuack 只有 bark，没有 quack，调用 duck.quack() 会在运行时抛出 AttributeError。它不是类型检查错误，而是属性查找失败。

### single_choice · None



- [A] 因为 Python 禁止任何鸭子类型调用
- [B] 因为调用方无法预知对象是否具备某个可选方法，直接调用可能抛出 AttributeError
- [C] 因为显式检查会让代码运行得更快
- [D] 因为显式检查可以替代所有类型注解

**参考答案**：1

**解析**：当某个方法是可选的（有的对象有、有的没有）时，直接调用可能触发 AttributeError。常用做法是 hasattr(obj, 'method')、callable(getattr(obj, 'method', None)) 或 try/except，把「能力检测」显式化。性能或替代类型注解都不是主要动机。

### single_choice · None



- [A] 使用静态检查器就必须放弃鸭子类型的所有用法
- [B] 结构化类型（如 typing.Protocol）可以在静态检查中表达鸭子类型的接口约束
- [C] Protocol 只能在运行时使用，无法用于静态检查
- [D] 静态检查器会逐行执行代码来验证鸭子类型

**参考答案**：1

**解析**：Protocol 是结构化类型的表达方式，它不要求显式继承，只要求对象提供相应的方法/属性，因此可以在静态检查中描述鸭子类型的接口约束。静态检查器做的是静态分析而非逐行执行。

### single_choice · None



- [A] isinstance(obj, SomeClass) 检查继承关系
- [B] for x in obj 只要求 obj 实现了 __iter__ 或 __getitem__
- [C] class Sub(Base) 显式继承
- [D] typing.cast(obj, SomeClass) 强制转换

**参考答案**：1

**解析**：for 循环不检查对象是否继承自某个迭代器基类，只要求它能通过 __iter__（或旧式的 __getitem__）产生元素，这正是鸭子类型：按能力而非类型判断。isinstance 和显式继承基于名义类型。

### multi_choice · None



- [A] 函数接收一个对象，只调用其 read() 方法，不关心它是不是某种 IO 基类的子类
- [B] 用 for 循环遍历一个自定义对象，因为它实现了 __iter__
- [C] 用 isinstance 判断对象是否属于某个具体类后再决定是否调用方法
- [D] 调用 len(obj) 时，只要 obj 实现了 __len__ 就能工作
- [E] 强制要求参数必须是 str 类型，否则报错

**参考答案**：[0, 1, 3]

**解析**：鸭子类型关注对象是否具备所需能力：只调用 read、实现 __iter__ 支持迭代、实现 __len__ 支持 len，都属于按能力判断。isinstance 判断具体类属于名义类型；强制 str 是显式类型限制，都与鸭子类型思想相反。

### multi_choice · None



- [A] 调用 obj.method() 但 obj 没有 method 属性
- [B] 对 obj 使用 for 迭代但 obj 既无 __iter__ 也无 __getitem__
- [C] 对定义了 __len__ 的对象调用 len(obj)
- [D] 调用 obj() 但 obj 不是可调用对象
- [E] 对实现了 __add__ 的两个对象使用 + 运算符

**参考答案**：[0, 1, 3]

**解析**：鸭子类型的失败通常发生在运行时属性/协议查找失败：缺方法会 AttributeError，不可迭代会 TypeError，不可调用会 TypeError。而实现了 __len__ 的对象调用 len、实现了 __add__ 的对象使用 + 都是正常成功的，不属于失败情形。
