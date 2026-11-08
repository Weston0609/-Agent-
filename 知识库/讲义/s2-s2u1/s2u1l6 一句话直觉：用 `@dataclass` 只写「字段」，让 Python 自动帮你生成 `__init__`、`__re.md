# s2u1l6 一句话直觉：用 `@dataclass` 只写「字段」，让 Python 自动帮你生成 `__init__`、`__repr__`、`__eq__`，把「一堆重复样板代码」压缩成几行声明。 / 给元组起名字

> 来源 `content/lessons/s2u1l6.json`

## py.oop.dataclass

# 一句话直觉：用 `@dataclass` 只写「字段」，让 Python 自动帮你生成 `__init__`、`__repr__`、`__eq__`，把「一堆重复样板代码」压缩成几行声明。

---

## 1. 为什么需要 dataclass（英文：data class）

在没有 `dataclass` 之前，如果你想用一个类来「装数据」，通常要手写：`__init__`、`__repr__`、`__eq__`，甚至 `__lt__`。字段一多，样板代码（英文：boilerplate code）成倍增长，还容易写错。

```python
# 传统写法：30 行只为了装 3 个字段
class User:
    def __init__(self, name: str, age: int, email: str):
        self.name = name
        self.age = age
        self.email = email

    def __repr__(self):
        return f"User(name={self.name!r}, age={self.age!r}, email={self.email!r})"

    def __eq__(self, other):
        if not isinstance(other, User):
            return NotImplemented
        return (self.name, self.age, self.email) == (other.name, other.age, other.email)

u = User("Alice", 30, "alice@example.com")
print(u)             # User(name='Alice', age=30, email='alice@example.com')
print(u == User("Alice", 30, "alice@example.com"))  # True
```

`dataclass` 的核心承诺：**你只声明字段，其余自动生成**。

---

## 2. 最小可用示例：3 行得到一个数据类

`@dataclass`（英文：decorator，装饰器）来自标准库 `dataclasses`。它读取类体里的类型注解（英文：type annotation），自动生成方法。

```python
from dataclasses import dataclass

@dataclass
class User:
    name: str
    age: int
    email: str

u = User("Alice", 30, "alice@example.com")
print(u)                                   # User(name='Alice', age=30, email='alice@example.com')
print(u == User("Alice", 30, "alice@example.com"))  # True
print(u.name, u.age)                       # Alice 30
```

关键结论：
- 字段顺序就是 `__init__` 的位置参数顺序。
- 默认生成 `__repr__` 和 `__eq__`。
- 类型注解是「声明」而非「运行时强制」，运行时不会自动做类型检查（英文：type checking）。

---

## 3. 默认值、默认工厂与不可变对象

`dataclass` 支持默认值，但**可变默认值必须用 `field(default_factory=...)`**，否则会像普通函数默认参数一样被所有实例共享——这是经典陷阱。

```python
from dataclasses import dataclass, field

@dataclass
class Cart:
    owner: str
    items: list[str] = field(default_factory=list)  # 每个实例独立列表
    total: float = 0.0

c1 = Cart("Alice")
c2 = Cart("Bob")
c1.items.append("apple")
print(c1.items)   # ['apple']
print(c2.items)   # []   —— 没被污染，说明 default_factory 生效
```

冻结（英文：frozen）可让实例不可变，并获得 `__hash__`，可以放进 `set` 或作为 `dict` 的 key。

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Point:
    x: int
    y: int

p = Point(1, 2)
# p.x = 10        # 抛出 FrozenInstanceError
try:
    p.x = 10
except Exception as e:
    print(type(e).__name__, e)

print({p, Point(1, 2)})   # 集合去重：{Point(x=1, y=2)}
```

---

## 4. 进阶控制：排序、关键字参数与后置处理

`@dataclass(order=True)` 会按字段顺序自动生成 `<`、`<=`、`>`、`>=`。`kw_only=True` 强制所有字段必须用关键字传入。`__post_init__` 可以在生成 `__init__` 之后做校验或派生字段。

```python
from dataclasses import dataclass, field

@dataclass(order=True)
class Version:
    major: int
    minor: int

print(Version(1, 2) < Version(1, 10))   # True
print(sorted([Version(2, 0), Version(1, 5)]))

@dataclass(kw_only=True)
class Config:
    host: str
    port: int = 8080

cfg = Config(host="localhost")          # 只能用关键字
print(cfg)

@dataclass
class Rectangle:
    width: float
    height: float
    area: float = field(init=False)      # 不进入 __init__

    def __post_init__(self):
        self.area = self.width * self.height

print(Rectangle(3, 4).area)              # 12.0
```

---

## 5. 与静态类型和生态的配合

`dataclass` 最常见的搭配是类型注解，配合静态类型检查器（如 mypy、pyright）能提前发现错误。调试类型推断时可以用 `typing.reveal_type`（Python 3.11+）查看推断结果；它会在运行时向 `sys.stderr` 打印真实类型，并原样返回参数。

```python
from dataclasses import dataclass
from typing import reveal_type

@dataclass
class User:
    name: str
    age: int

u = User("Alice", 30)
reveal_type(u)      # 静态检查器：Revealed type is "User"；运行时打印 Runtime type is User
print(u)            # 仍可正常使用
```

生态上，很多框架（如 Pydantic、SQLModel、attrs）提供「dataclass 样式」的行为。`typing.dataclass_transform`（Python 3.11+）是给这些框架作者用的「声明我这个装饰器/基类会像 dataclass 一样工作」的标记，让类型检查器理解这些第三方结构。

```python
from typing import dataclass_transform

@dataclass_transform()
def my_model(cls):
    return cls

@my_model
class Customer:
    id: int
    name: str

c = Customer()
c.id = 1
c.name = "Alice"   # 类型检查器已知这是 dataclass-like 结构
print(c.id, c.name)
```

---

## 动手练习

写一个 `Student` 数据类：
1. 字段：`name: str`、`scores: list[int] = field(default_factory=list)`、`gpa: float = field(init=False, default=0.0)`。
2. 在 `__post_init__` 中计算 `gpa` 为 `scores` 的平均分（空列表时为 `0.0`）。
3. 使用 `@dataclass(order=True)`，让 `Student` 按 `name` 排序。
4. 创建两个 `Student`，给一个添加分数，验证两个实例的 `scores` 互不影响，并打印排序结果与 `gpa`。

提示：`sum(self.scores) / len(self.scores) if self.scores else 0.0`。

```python
from dataclasses import dataclass, field

@dataclass(order=True)
class Student:
    name: str
    scores: list[int] = field(default_factory=list)   # 每个实例独立列表
    gpa: float = field(init=False, default=0.0)       # 不进入 __init__

    def __post_init__(self):
        # 在 __init__ 之后计算派生字段
        self.gpa = sum(self.scores) / len(self.scores) if self.scores else 0.0

a = Student("Alice")
b = Student("Bob", scores=[90, 80, 100])

a.scores.append(100)          # 只影响 a
print(a)                      # Student(name='Alice', scores=[100], gpa=100.0)
print(b)                      # Student(name='Bob', scores=[90, 80, 100], gpa=90.0)
print(sorted([b, a]))         # 按 name 排序：Alice 在 Bob 前
print(a == Student("Alice", scores=[100]))  # True，__eq__ 比较字段值
```

## py.oop.namedtuple

# py.oop.namedtuple：给元组起名字

## 一句话直觉

**`namedtuple`（具名元组）就是"带字段名的元组"**——它保留了普通元组不可变、可解包、省内存的优点，同时让你用 `emp.name` 而不是 `emp[0]` 来访问数据，可读性和可维护性大幅提升。

---

## 1. 为什么需要它：普通元组和普通类的痛点

假设你要表示一个员工：

```python
# 普通元组：短小但不可读
emp = ('Guido', 3)
print(emp[0])  # 0 是什么？阅读代码的人必须去翻定义

# 普通类：可读但啰嗦
class Employee:
    def __init__(self, name, id):
        self.name = name
        self.id = id

emp = Employee('Guido', 3)
print(emp.name)  # 可读，但写起来繁琐，且实例可变
```

`namedtuple` 在两者之间找到了平衡点：**像类一样可读，像元组一样轻量、不可变、可解包**。

---

## 2. 最小可用示例：`collections.namedtuple`

标准库里最基础的用法来自 `collections`：

```python
from collections import namedtuple

# 第一个参数是类型名，第二个参数是字段名列表
Employee = namedtuple('Employee', ['name', 'id'])

emp = Employee('Guido', 3)
print(emp.name)        # Guido，按字段名访问
print(emp[0])          # Guido，仍可按索引访问（兼容元组用法）
print(emp)             # Employee(name='Guido', id=3)，自带美丽 repr

# 仍是元组：可解包、可比较、不可变
name, eid = emp
print(name, eid)
```

关键结论：

- **不可变（immutable）**：创建后不能修改字段，天然适合做"值对象（value object）"。
- **兼容元组**：索引、切片、解包、`len()`、迭代全部可用。
- **自带 `repr` 和相等性**：调试友好，`==` 按字段值比较。

---

## 3. 更好的写法：`typing.NamedTuple`

从 Python 3.6 起，`typing.NamedTuple` 支持**类声明式语法 + 类型注解**，IDE 和类型检查器都能识别字段类型：

```python
from typing import NamedTuple

class Employee(NamedTuple):
    name: str
    id: int = 3          # 支持默认值

emp = Employee('Guido')
print(emp)               # Employee(name='Guido', id=3)
print(emp.id)            # 3

# 等价于：
# Employee = collections.namedtuple('Employee', ['name', 'id'])
# Employee.__new__.__defaults__ = (3,)
```

它还能：

- **添加默认值**（必须放在无默认值字段之后，和函数参数规则一样）。
- **添加文档字符串和方法**：

```python
class Employee(NamedTuple):
    """表示一名员工。"""
    name: str
    id: int = 3

    def greet(self) -> str:
        return f'Hello, {self.name}'

print(Employee('Guido').greet())   # Hello, Guido
```

- **支持泛型**（Python 3.11+）：

```python
class Group[T](NamedTuple):
    key: T
    members: list[T]
```

- **支持函数式写法**（等价于 `collections.namedtuple`）：

```python
Employee = NamedTuple('Employee', [('name', str), ('id', int)])
```

---

## 4. 关键属性与内省能力

无论用哪种创建方式，生成的类都携带以下属性，非常适合做序列化、反射和测试：

```python
from typing import NamedTuple

class Employee(NamedTuple):
    name: str
    id: int = 3

print(Employee._fields)          # ('name', 'id')
print(Employee._field_defaults)  # {'id': 3}
print(Employee._asdict(Employee('Guido')))  # {'name': 'Guido', 'id': 3}

# 从字典重建
Employee(**{'name': 'Ada', 'id': 7})

# 替换某个字段（返回新实例，原实例不变）
emp = Employee('Guido', 3)
new_emp = emp._replace(id=10)
print(emp, new_emp)  # Employee(name='Guido', id=3) Employee(name='Guido', id=10)
```

这些方法让 `namedtuple` 非常适合充当**轻量级的领域数据模型（domain model）**或**不可变配置对象**。

---

## 5. 何时用 / 何时不用

**适合的场景**

- 需要一个字段固定、不可变的小数据容器（坐标 `Point(x, y)`、员工记录、API 返回值）。
- 想从元组获得可读性，但不想引入完整类的开销。
- 需要能被解包、能被哈希、能放进 `set` 或做 `dict` 键。

**不适合的场景**

- 需要可变字段：请用 `dataclass`（`@dataclass`）或普通类。
- 字段很多（> 10）且需要复杂行为、继承、属性验证：用 `dataclass` 或手写类。
- 需要 `__post_init__`、`property`、`__slots__` 等高级特性：`dataclass` 更合适。

一句话记忆：**"只读的小结构体" → namedtuple；"会变或有行为" → dataclass / 普通类。**

---

## 动手练习

**任务：用 `namedtuple` 写一个二维点集分析器。**

1. 用 `typing.NamedTuple` 定义 `Point`，字段为 `x: float`、`y: float`（无默认值）。
2. 给 `Point` 加一个方法 `distance_to(self, other: 'Point') -> float`，返回两点欧氏距离。
3. 写一个函数 `closest_pair(points: list[Point]) -> tuple[Point, Point]`，返回距离最近的一对点（点数 < 2 时抛 `ValueError`）。
4. 在 `if __name__ == '__main__':` 下构造 5 个随机点并打印最近的一对。

**提示**：距离公式 `((x1-x2)**2 + (y1-y2)**2) ** 0.5`；可以用 `itertools.combinations` 枚举对。

**加分**：把 `Point` 改成 `collections.namedtuple('Point', ['x', 'y'])` 的写法，观察两者的行为和 `repr` 差异。

```python
from typing import NamedTuple

class Employee(NamedTuple):
    """表示一名员工的不可变记录。"""
    name: str
    id: int = 3          # 默认值字段必须排在最后

    def greet(self) -> str:
        return f'Hello, {self.name}'

# 创建实例
alice = Employee('Alice')          # id 使用默认值 3
bob   = Employee('Bob', 42)

# 字段访问、打印、解包
print(alice)                        # Employee(name='Alice', id=3)
print(bob.name, bob.id)             # Bob 42
name, eid = bob
print(name, eid)                    # Bob 42

# 内省属性
print(Employee._fields)             # ('name', 'id')
print(Employee._field_defaults)     # {'id': 3}

# 不可变性：修改字段会报错
# alice.id = 99  # AttributeError: can't set attribute

# 用 _replace 生成新实例（原实例不变）
bob2 = bob._replace(id=100)
print(bob, bob2)                    # Employee(name='Bob', id=42) Employee(name='Bob', id=100)

# 用 _asdict 转成普通字典（便于序列化）
print(bob._asdict())                # {'name': 'Bob', 'id': 42}

# 可用作字典键 / 放集合中（因为可哈希）
seen = {alice, bob, Employee('Alice', 3)}
print(len(seen))                    # 2，因为 alice 和 Employee('Alice', 3) 相等

print(alice.greet())                # Hello, Alice
```


---

## 本课题目

### single_choice · None



- [A] Point(x=1, y=0)
- [B] Point(1, 0)
- [C] Point(x=1)
- [D] 抛出 TypeError，因为 y 没有传值

**参考答案**：0

**解析**：dataclass 会自动生成 __repr__，格式为「类名(字段名=值, ...)」，并包含已使用默认值的字段；y 有默认值 0，因此输出 Point(x=1, y=0)。

### single_choice · None



- [A] True，因为 dataclass 自动生成了按字段比较的 __eq__
- [B] False，因为默认比较的是对象身份
- [C] 报错，dataclass 不会生成 __eq__
- [D] True，因为两个对象哈希值相同

**参考答案**：0

**解析**：默认 eq=True，dataclass 会生成 __eq__，按字段元组逐一比较，因此 a 和 b 相等。

### single_choice · None



- [A] __post_init__ 多出的参数没有对应的 InitVar 声明，调用时会缺参数
- [B] __post_init__ 不能有返回值
- [C] 数据类不允许定义普通方法
- [D] x 应该声明为 InitVar

**参考答案**：0

**解析**：__post_init__ 只接收 __init__ 传入的 InitVar 参数；未声明的 y 不会被传入，因而调用报错。

### single_choice · None



- [A] __init__ 参数顺序为 a、b，且 Child 的 __eq__ 会比较 a 和 b
- [B] __init__ 参数顺序为 b、a，且只比较 b
- [C] 子类必须重新声明 a 字段
- [D] 子类不能是 dataclass

**参考答案**：0

**解析**：子类字段追加在父类字段之后，生成的 __eq__ 和 __init__ 都包含继承的全部字段。

### single_choice · None



- [A] 默认使用 __slots__ 风格存储，实例没有 __dict__ 属性
- [B] 实例字典包含 x 和 y 两个键
- [C] 实例字典为空，字段保存在类属性中
- [D] 实例字典包含方法而不是字段

**参考答案**：0

**解析**：默认参数 slots=False 时实例会有 __dict__ 存放字段；若设置 slots=True 才会用槽位存储而不再有 __dict__。此处考察默认行为的常见混淆点，正确描述是默认有 __dict__ 并可存字段，因此“实例没有 __dict__ 属性”是错误的；本题正确项为默认情况下字段进入 __dict__……

### single_choice · None



- [A] 实例字段改用槽位存储，实例不再有 __dict__，也不能随意添加新属性
- [B] 实例字段改用字典存储，访问速度变慢
- [C] 禁止使用默认值
- [D] 自动生成 __hash__ 方法

**参考答案**：0

**解析**：slots=True 会生成 __slots__，字段用槽位保存，实例没有 __dict__，未声明的属性赋值会抛 AttributeError。

### single_choice · None



- [A] y: int = field(repr=False)
- [B] y: int = field(compare=False)
- [C] y: int = field(default=0)
- [D] y: int = field(init=False)

**参考答案**：0

**解析**：field(repr=False) 让该字段不出现在自动生成的 __repr__ 中；compare=False 只影响相等比较，init=False 只影响构造参数。

### single_choice · None



- [A] 抛出 TypeError，提示 unhashable
- [B] 正常运行，集合中有两个元素
- [C] 正常运行，集合中有一个元素
- [D] 抛出 ValueError，字段重复

**参考答案**：0

**解析**：默认 eq=True 且 frozen=False 时，dataclass 将 __hash__ 设为 None，实例不可哈希，不能放入 set。

### single_choice · None



- [A] 可哈希，可以放入 set
- [B] 不可哈希，因为 eq=True
- [C] 可哈希，但只能作为 dict 的值
- [D] 不可哈希，因为 frozen=True 会移除 __hash__

**参考答案**：0

**解析**：frozen=True 且 eq=True 时 dataclass 会生成 __hash__，因此实例可哈希，可用于 set 和 dict 键。

### single_choice · None



- [A] 自动生成 __init__、__repr__、__eq__ 等样板方法，字段集中声明
- [B] 自动实现多继承
- [C] 自动把类变成不可变类型
- [D] 自动为字段提供类型检查

**参考答案**：0

**解析**：dataclass 的主要价值是减少样板代码；它不会自动实现多继承、不可变或运行时类型检查。

### single_choice · None



- [A] 2
- [B] 1
- [C] None
- [D] 报错，因为 scale 不是字段

**参考答案**：0

**解析**：InitVar 声明的参数会传给 __init__ 并进一步传给 __post_init__，但不会成为实例字段；未传值时使用默认值 2。

### single_choice · None



- [A] 在类中定义 __post_init__，把 w*h 赋给 self.r
- [B] 在类体中直接写 r = w * h
- [C] 把 r 声明为带 default 的字段并写 r = w * h
- [D] 使用 @property 装饰器把 r 变成类变量

**参考答案**：0

**解析**：派生字段应在 __post_init__ 中计算并赋给 self，类体执行时 w、h 还不是实例属性值，直接写 r = w * h 会 NameError。

### single_choice · None



- [A] 带默认值的字段必须放在不带默认值的字段之后
- [B] 字段顺序无所谓，默认值可以随意放置
- [C] name 也会自动获得默认值 None
- [D] debug 没有默认值，必须显式传入

**参考答案**：0

**解析**：数据类字段生成 __init__ 参数时，有默认值的参数必须排在没有默认值的参数之后，否则会抛出 TypeError。

### single_choice · None



- [A] 抛出 ValueError，因为 list 这类可变默认值不被允许
- [B] 正常运行，每个实例的 tags 都是同一个空列表
- [C] 正常运行，每个实例都会获得新的空列表
- [D] 抛出 TypeError，因为 list 不是合法类型标注

**参考答案**：0

**解析**：dataclass 禁止字段默认值为 list、dict、set 等可变对象，会抛出 ValueError，提示使用 default_factory。

### single_choice · None



- [A] tags: list = field(default_factory=list)
- [B] tags: list = field(default=list())
- [C] tags: list = []
- [D] tags: list = field(default=list)

**参考答案**：0

**解析**：default_factory 接收一个可调用对象，每次创建实例时调用它生成新对象，因此用 list 而不是 list() 或 list 本身。

### single_choice · None



- [A] 抛出 FrozenInstanceError
- [B] 输出 2
- [C] 输出 1
- [D] 抛出 AttributeError，提示没有 x 属性

**参考答案**：0

**解析**：frozen=True 会阻止对实例字段赋值，修改时由自动生成的 __setattr__ 抛出 FrozenInstanceError。

### single_choice · None



- [A] 实例不可修改，并且自动生成 __hash__，可作为字典键
- [B] 实例不可修改，但仍不可哈希
- [C] 实例可修改，只是不能添加新属性
- [D] 实例可修改，但字段顺序被冻结

**参考答案**：0

**解析**：frozen=True 让实例成为不可变对象，此时 dataclass 会生成 __hash__，因此可哈希；普通 dataclass 默认 eq=True 且 frozen=False 时 __hash__ 被设为 None。

### single_choice · None



- [A] 报错 NameError，因为类体中 w 和 h 此时并不是可用的值
- [B] 输出 6
- [C] 输出 0
- [D] 输出 None

**参考答案**：0

**解析**：类体执行时字段注解只是注解，w 和 h 尚未作为实例属性存在，类体中直接引用它们会 NameError；计算派生值应使用 __post_init__ 或属性。

### single_choice · None



- [A] 6
- [B] 0
- [C] None
- [D] 报错，因为 area 没有声明为字段

**参考答案**：0

**解析**：__post_init__ 在 __init__ 之后调用，此时 w 和 h 已赋值，可以给实例添加未声明的属性 area。

### single_choice · None



- [A] 只有 name
- [B] name 和 age
- [C] name 和 token
- [D] 全部三个字段

**参考答案**：0

**解析**：compare=False 的 age 不参与比较，token 默认参与比较只是不出现在 repr 中，因此参与相等比较的只有 name。

### single_choice · None



- [A] 它创建的是一个普通字典的子类
- [B] 它创建的是一个元组的子类，字段可通过属性名访问
- [C] 它创建的是一个列表的子类，支持按索引和名称访问
- [D] 它创建的是一个抽象基类，必须再继承才能使用

**参考答案**：1

**解析**：namedtuple 返回的新类是 tuple 的子类，实例既支持普通元组的索引访问，也支持通过字段名以属性方式访问。它并非 dict、list 或抽象基类。

### single_choice · None



- [A] p == (1, 2)
- [B] p.x == p['x']
- [C] p[0] == 1
- [D] 以上都为 True

**参考答案**：3

**解析**：namedtuple 实例与等价普通元组比较相等；字段既能用属性访问也能用索引/键名访问；索引 0 对应字段 x。三项都成立。

### single_choice · None



- [A] p 变为 Point(x=5, y=6)
- [B] p 保持不变，_make 返回一个新的 Point(x=5, y=6)
- [C] p 变为普通元组 (5, 6)
- [D] 抛出异常，因为 p 不可变

**参考答案**：1

**解析**：_make 是一个类方法，用给定可迭代对象构造一个新的实例并返回，原实例不受影响。

### multi_choice · None



- [A] 实例是元组的子类，支持索引访问
- [B] 实例可通过字段名以属性方式访问
- [C] 实例是可变的，可随时修改字段
- [D] 实例可哈希，只要所有字段值都可哈希
- [E] 实例与等价的普通元组比较相等

**参考答案**：[0, 1, 3, 4]

**解析**：namedtuple 实例是元组子类，支持索引和属性访问，与等价元组相等，且当字段值都可哈希时可哈希。实例不可变，因此“可变”的说法错误。

### multi_choice · None



- [A] _replace
- [B] _asdict
- [C] _fields
- [D] _make
- [E] _append

**参考答案**：[0, 1, 2, 3]

**解析**：_replace、_asdict、_fields、_make 都是 namedtuple 提供的接口；元组没有 _append，namedtuple 也不提供该方法。

### multi_choice · None



- [A] 字段可用名称访问，提升代码可读性
- [B] 可用于解包赋值，如 x, y = p
- [C] 自动实现字段级校验，拒绝类型不匹配的值
- [D] 相比等价的普通元组，内存开销几乎相同
- [E] 便于通过字段名生成字典或替换字段

**参考答案**：[0, 1, 3, 4]

**解析**：namedtuple 提升可读性，支持解包、_asdict、_replace，且内存与普通元组接近。它不做字段类型校验，因此“自动校验类型”错误。

### multi_choice · None



- [A] namedtuple 实例不可变，普通类默认可变
- [B] namedtuple 自动提供按名称访问字段，不需要手写 __init__
- [C] namedtuple 和普通类一样可以随意添加新的实例属性
- [D] namedtuple 是元组，因此可用于需要元组的地方
- [E] namedtuple 适合表示轻量的、字段固定的记录

**参考答案**：[0, 1, 3, 4]

**解析**：namedtuple 不可变、自动提供命名访问、本质是元组、适合轻量记录。它因为有 __slots__ 限制，不能随意添加新实例属性，故该项错误。

### fill_blank · None



**参考答案**：["_fields"]

**解析**：namedtuple 生成类提供 _fields 类属性，返回字段名组成的元组。

### fill_blank · None



**参考答案**：["_replace"]

**解析**：_replace 返回替换了指定字段的新实例，由于不可变性原实例保持不变。

### code_reading · None



**参考答案**：3 4 (3, 4)

**解析**：p.x 按字段名得到 3；p[1] 按索引得到第二个字段值 4；tuple(p) 将 namedtuple 转换为普通元组 (3, 4)。

### code_reading · None



**参考答案**：输出为 Point(x=1, y=2) Point(x=10, y=20) False。_replace 返回替换了字段的新实例，原实例 p 不变，因此二者不相等。

**解析**：namedtuple 不可变，_replace 生成新实例；p 的值未被修改，所以 p 与 q 不相等，输出 False。

### scenario · None



**解析**：可以把每行数据构造成 namedtuple，比如以经度、纬度作为字段名，让访问从索引升级为可读的名称访问；好处是提升可读性、减少字段错位；注意点是 namedtuple 不可变，若需要更新应使用 _replace 生成新实例。

### single_choice · None



- [A] 读取 p.x
- [B] 通过索引读取 p[0]
- [C] 执行 p.x = 10 重新赋值
- [D] 把 p 放入集合 set 中

**参考答案**：2

**解析**：namedtuple 实例是元组，元组不可变，因此对字段赋值会抛出 AttributeError。读取字段、索引访问、放入集合（因为可哈希）都是合法操作。

### single_choice · None



- [A] 正常创建，字段名可以是任意合法标识符
- [B] 抛出 ValueError，因为字段名不能以下划线开头
- [C] 自动去掉下划线前缀
- [D] 创建成功但该字段只能通过索引访问

**参考答案**：1

**解析**：namedtuple 拒绝以下划线开头的字段名，会抛出 ValueError，以避免与内部方法和属性冲突。

### single_choice · None



- [A] 它就地修改当前实例的某个字段值
- [B] 它返回一个新实例，用给定值替换指定字段，原实例不变
- [C] 它只能替换第一个字段的值
- [D] 它返回一个普通元组而非 namedtuple 实例

**参考答案**：1

**解析**：_replace 生成并返回一个新的 namedtuple 实例，替换指定字段，原实例因为不可变而保持不变。

### single_choice · None



- [A] 一个列表 [('x', 3), ('y', 4)]
- [B] 一个普通的字典 {'x': 3, 'y': 4}，字段名映射到值
- [C] 一个 namedtuple 实例
- [D] 一个集合 {3, 4}

**参考答案**：1

**解析**：_asdict 返回一个字典，键为字段名、值为对应字段值。在较新版本中返回的是普通 dict（早期为 OrderedDict，行为类似）。

### single_choice · None



- [A] 只能用逗号分隔
- [B] 可以只用空格或逗号分隔，也可混合使用
- [C] 必须用分号分隔
- [D] 不接受字符串形式，只能用列表

**参考答案**：1

**解析**：namedtuple 的字段名既可传列表，也可传字符串；字符串中字段名可用空格或逗号（或两者混合）分隔。

### single_choice · None



- [A] namedtuple 不支持默认值
- [B] defaults 参数为最右侧的若干字段提供默认值，顺序从右往左对应
- [C] defaults 为最左侧的若干字段提供默认值
- [D] 只能给第一个字段设置默认值

**参考答案**：1

**解析**：defaults 为最右侧字段提供默认值，从左到右的字段依次对应 defaults 中的值；因此在创建时可以省略尾部字段。

### single_choice · None



- [A] 直接给 namedtuple 实例动态添加方法
- [B] 通过继承 namedtuple 生成的类来扩展新的属性和方法
- [C] 修改 namedtuple 类的 __dict__
- [D] namedtuple 生成的类无法扩展

**参考答案**：1

**解析**：由于实例不可变且生成的类有 __slots__，通常通过继承该 namedtuple 类来添加方法或属性，这也是官方推荐的扩展方式。

### single_choice · None



- [A] _fields 是实例属性，返回该实例的值
- [B] _fields 是类属性，返回包含所有字段名的元组
- [C] _fields 返回字段名到值的映射
- [D] _fields 在实例创建后才能访问，且每次返回不同结果

**参考答案**：1

**解析**：_fields 是类级属性，是一个包含所有字段名字符串的元组，与具体实例无关。
