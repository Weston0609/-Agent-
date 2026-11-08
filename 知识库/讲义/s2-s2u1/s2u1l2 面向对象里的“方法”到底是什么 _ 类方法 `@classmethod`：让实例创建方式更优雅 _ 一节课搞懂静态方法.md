# s2u1l2 面向对象里的“方法”到底是什么 / 类方法 `@classmethod`：让实例创建方式更优雅 / 一节课搞懂静态方法

> 来源 `content/lessons/s2u1l2.json`

## py.oop.method

# py.oop.method：面向对象里的“方法”到底是什么

> **一句话直觉**：方法（method）就是“绑定在类里的函数”，它让数据（属性）和行为（操作）住在一起，从而把复杂系统拆成一个个能独立思考和复用的小对象。

---

## 1. 从函数到方法：为什么要 `self`？

普通函数是“谁调用都一样”；方法的核心区别是**它会自动接收调用它的实例**。

在 Python 中，定义在类（class）里的函数就是方法。第一个参数通常命名为 `self`（英文：self，指“这个实例”），Python 会在通过实例调用时自动把它传进去。

```python
class Counter:
    def __init__(self):          # 初始化方法（initializer），构造实例时自动调用
        self.value = 0           # 实例属性（instance attribute）

    def add(self, n):            # 实例方法（instance method）
        self.value += n
        return self.value

c = Counter()
c.add(3)
print(c.add(4))  # 输出 7
```

**关键结论**：`c.add(4)` 等价于 `Counter.add(c, 4)`。`self` 不是关键字，只是约定俗成的名字。

---

## 2. 三种方法：实例方法、类方法、静态方法

- **实例方法（instance method）**：第一个参数是 `self`，能访问实例属性和类属性。
- **类方法（class method）**：用 `@classmethod` 装饰，第一个参数是 `cls`（class），常做“替代构造器”。
- **静态方法（static method）**：用 `@staticmethod` 装饰，不接收 `self` 或 `cls`，只是放在类命名空间里的普通函数。

```python
class Temperature:
    unit = "C"  # 类属性（class attribute）

    def __init__(self, celsius):
        self.celsius = celsius

    @classmethod
    def from_fahrenheit(cls, f):
        # 不需要实例，只用类本身
        return cls((f - 32) * 5 / 9)

    @staticmethod
    def is_freezing(celsius):
        # 逻辑上属于这个类，但不依赖实例或类
        return celsius <= 0

print(Temperature.from_fahrenheit(32).celsius)  # 0.0
print(Temperature.is_freezing(-1))              # True
```

**关键结论**：
- 需要“读写实例数据” → 实例方法。
- 需要“根据类来构造/配置” → 类方法。
- 只是“把这个函数放在类里组织起来” → 静态方法。

---

## 3. 特殊方法（dunder）：让对象“像内置类型一样工作”

Python 里以双下划线开头和结尾的方法叫**特殊方法（special method / dunder method）**。它们由语言在特定语法下自动调用，而不是你手动写名字去调。

最常见的几个：

- `__init__`：实例初始化。
- `__repr__` / `__str__`：打印与调试显示。
- `__len__`：支持 `len(obj)`。
- `__eq__`：支持 `==`。
- `__iter__`：支持 `for ... in obj`。
- `__getitem__`：支持 `obj[key]`。

```python
class Playlist:
    def __init__(self, songs):
        self.songs = list(songs)

    def __len__(self):
        return len(self.songs)

    def __getitem__(self, i):
        return self.songs[i]

    def __repr__(self):
        return f"Playlist({self.songs!r})"

p = Playlist(["A", "B", "C"])
print(len(p))     # 3
print(p[1])       # B
print(p)          # Playlist(['A', 'B', 'C'])
```

**关键结论**：写特殊方法，本质是让自定义对象参与 Python 的“协议（protocol）”。你不需要继承某个固定基类，只要实现对应方法，就支持对应语法。

---

## 4. 从“协议”看方法：对象能力由方法定义

Python 的许多能力不是“类型声明”，而是“有没有实现某个方法”。

例如：
- 实现 `__iter__` → 可被 `for` 迭代。
- 实现 `__len__` → 可被 `len()` 调用。
- 实现 `__bytes__` / `__int__` / `__float__` → 可被 `bytes()` / `int()` / `float()` 转换。
- 实现 `__str__` → 可被 `str()` 友好输出。

这就是**鸭子类型（duck typing）**：看起来像鸭子、叫起来像鸭子，那就是鸭子。方法签名，就是“叫声”。

```python
class Money:
    def __init__(self, amount):
        self.amount = amount

    def __str__(self):
        return f"{self.amount} 元"

    def __add__(self, other):
        return Money(self.amount + other.amount)

print(str(Money(10) + Money(5)))  # 15 元
```

**关键结论**：一个对象“能做什么”，取决于它实现了哪些方法，而不是它继承自哪个类。

---

## 5. 工程级视角：方法的设计原则

1. **单一职责（single responsibility）**：一个方法只做一件事，名字说清楚做什么。
2. **高内聚（high cohesion）**：与数据强相关的操作放在类里；纯工具函数用静态方法或模块函数。
3. **避免 God Object**：方法过多、职责过杂的类会难以测试和维护。
4. **优先组合与协议**：不要为了“复用”滥用继承；先看对象是否实现了所需方法。
5. **特殊方法保持一致语义**：`__eq__` 若重写，通常还要重写 `__hash__` 以保持一致性。

```python
class InvalidAmount(ValueError):
    pass

class Wallet:
    def __init__(self):
        self._balance = 0

    def deposit(self, amount):
        if amount <= 0:
            raise InvalidAmount("存款金额必须为正数")
        self._balance += amount
        return self._balance

    @property
    def balance(self):
        return self._balance

w = Wallet()
w.deposit(100)
print(w.balance)  # 100
```

**关键结论**：好的方法设计让对象“自己管好自己的状态”，外部只通过清晰接口交互。

---

## 动手练习：做一个可迭代的“成绩册”

**任务**：实现 `ScoreBook` 类，满足以下要求：

1. `__init__(self, scores)` 保存一个成绩列表。
2. `__len__` 返回成绩数量。
3. `__getitem__` 支持 `book[0]` 取第一个成绩。
4. `__iter__` 支持 `for s in book` 遍历成绩。
5. `__repr__` 返回类似 `ScoreBook([90, 80, 70])`。
6. 加一个实例方法 `average(self)` 返回平均分；空列表返回 `0`。
7. 加一个类方法 `from_str(cls, text)`，把 `"90,80,70"` 转成 `ScoreBook`。

**验收示例**：

```python
book = ScoreBook.from_str("90,80,70")
assert len(book) == 3
assert book[0] == 90
assert list(book) == [90, 80, 70]
assert book.average() == 80.0
print(book)
```

**进阶**：重写 `__add__`，让两个 `ScoreBook` 可以直接相加合并成绩。

```python
class ScoreBook:
    def __init__(self, scores):
        # 保存成绩副本，避免外部列表被修改影响内部状态
        self.scores = list(scores)

    def __len__(self):
        # 支持 len(book)
        return len(self.scores)

    def __getitem__(self, i):
        # 支持 book[0]
        return self.scores[i]

    def __iter__(self):
        # 支持 for s in book
        return iter(self.scores)

    def __repr__(self):
        # 支持 print(book) 时显示可读内容
        return f"ScoreBook({self.scores!r})"

    def average(self):
        # 实例方法：计算平均分
        if not self.scores:
            return 0
        return sum(self.scores) / len(self.scores)

    @classmethod
    def from_str(cls, text):
        # 类方法：从字符串构造实例
        parts = text.split(",")
        scores = [int(x) for x in parts if x.strip()]
        return cls(scores)


if __name__ == "__main__":
    book = ScoreBook.from_str("90,80,70")
    assert len(book) == 3
    assert book[0] == 90
    assert list(book) == [90, 80, 70]
    assert book.average() == 80.0
    print(book)
```

## py.oop.classmethod

# 类方法 `@classmethod`：让实例创建方式更优雅

## 一句话直觉

**`@classmethod`（类方法）** 让你在不需要“先造出一个对象”的前提下，就能调用类里的函数；它最典型的用途是写“替代构造函数”（alternative constructor），用一个更直观的方式创建实例。

---

## 1. 先回忆：普通实例方法长什么样

在 Python 里，类（class）定义对象（instance/object）的模板。普通方法第一个参数是 `self`，代表“调用这个方法的实例”。

```python
class User:
    def __init__(self, name: str, age: int):
        self.name = name
        self.age = age

    def greet(self) -> str:
        # self 指向具体实例
        return f"Hi, I am {self.name}, {self.age} years old."

# 普通方法必须通过实例调用
u = User("Alice", 30)
print(u.greet())   # Hi, I am Alice, 30 years old.
```

**关键结论**：普通实例方法依赖 `self`，所以必须先有实例。

---

## 2. 类方法是什么：第一个参数是 `cls`

用 `@classmethod` 装饰器（decorator）标记后，方法的第一个参数自动变成 **类本身**，习惯叫 `cls`（class 的缩写）。

```python
class User:
    def __init__(self, name: str, age: int):
        self.name = name
        self.age = age

    @classmethod
    def species(cls) -> str:
        # cls 就是 User 这个类本身，而不是某个实例
        return cls.__name__

# 直接用类调用，不需要实例
print(User.species())   # User
```

**关键结论**：类方法绑定的是“类”，不是“实例”，所以可以直接用 `ClassName.method()` 调用。

---

## 3. 为什么需要它：替代构造函数

假设用户信息有时以 `"Alice,30"` 这样的字符串传来。如果每次都写 `User(*s.split(","))` 很难读，也容易出错。用类方法可以把它变成清晰的构造函数。

```python
class User:
    def __init__(self, name: str, age: int):
        self.name = name
        self.age = age

    @classmethod
    def from_string(cls, raw: str) -> "User":
        # cls(...) 会调用当前类的构造函数，支持子类继承
        name, age_str = raw.split(",")
        return cls(name.strip(), int(age_str))

u = User.from_string("Bob, 25")
print(u.name, u.age)   # Bob 25
```

**关键结论**：`cls(...)` 就是“用当前类来创建实例”，这是替代构造函数的标准写法。

---

## 4. 类方法与继承：`cls` 会跟随子类变化

子类继承父类时，通过 `cls` 创建的实例会是子类的类型，而不是硬编码的父类。

```python
class User:
    def __init__(self, name: str, age: int):
        self.name = name
        self.age = age

    @classmethod
    def from_string(cls, raw: str) -> "User":
        name, age_str = raw.split(",")
        return cls(name.strip(), int(age_str))

class Admin(User):
    def __init__(self, name: str, age: int, level: int = 9):
        super().__init__(name, age)
        self.level = level

# cls 是 Admin，因此构造出的是 Admin 实例
a = Admin.from_string("Carol, 40")
print(type(a).__name__, a.level)   # Admin 9
```

**关键结论**：在类方法里用 `cls(...)` 而不是写死 `User(...)`，可以让子类自动获得正确的构造行为。这也是官方推荐用 `Self` 作为返回注解的原因：

```python
from typing import Self

class User:
    @classmethod
    def from_string(cls, raw: str) -> Self:
        ...
```

这样类型检查器（type checker，如 mypy/pyright）就知道：`Admin.from_string(...)` 返回的是 `Admin`，而不是 `User`。

---

## 5. 类方法 vs 实例方法 vs 静态方法

| 类型 | 第一个参数 | 绑定对象 | 典型用途 |
|---|---|---|---|
| 实例方法 | `self` | 实例 | 访问/修改实例数据 |
| 类方法 | `cls` | 类 | 替代构造函数、需要知道“当前类”的逻辑 |
| 静态方法 | 无 | 都不绑定 | 与类相关但不依赖类或实例的工具函数 |

```python
class MathUtil:
    factor = 2

    def scale_instance(self, x: int) -> int:
        return x * self.factor          # 依赖实例

    @classmethod
    def scale_class(cls, x: int) -> int:
        return x * cls.factor            # 依赖类属性

    @staticmethod
    def add(a: int, b: int) -> int:
        return a + b                     # 与类/实例都无关

print(MathUtil.scale_class(3))   # 6
print(MathUtil.add(1, 2))        # 3
```

---

## 6. 工程级用法：工厂模式与配置

实际项目中，`@classmethod` 常用来做“工厂”（factory）：根据不同的输入来源（文件、字典、环境变量）统一构造对象。

```python
import json
from typing import Self

class Config:
    def __init__(self, debug: bool, port: int):
        self.debug = debug
        self.port = port

    @classmethod
    def from_json(cls, text: str) -> Self:
        data = json.loads(text)
        return cls(data["debug"], data["port"])

    @classmethod
    def default(cls) -> Self:
        return cls(debug=False, port=8080)

c1 = Config.from_json('{"debug": true, "port": 9000}')
c2 = Config.default()
print(c1.debug, c1.port)   # True 9000
print(c2.debug, c2.port)   # False 8080
```

---

## 结尾：动手练习

**任务**：实现一个 `Point` 类，支持三种创建方式。

1. `Point(x, y)`：普通构造。
2. `Point.origin()`：类方法，返回原点 `(0, 0)`。
3. `Point.from_string("3,4")`：类方法，从字符串解析出坐标。
4. 再定义一个子类 `Point3D`，验证 `Point3D.origin()` 返回的实例类型是 `Point3D`。

**提示**：类方法里返回实例时使用 `cls(...)`，返回类型注解可用 `Self`。

```python
from typing import Self

class Point:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y

    @classmethod
    def origin(cls) -> Self:
        return cls(0, 0)

    @classmethod
    def from_string(cls, raw: str) -> Self:
        x, y = raw.split(",")
        return cls(float(x), float(y))

class Point3D(Point):
    def __init__(self, x: float, y: float, z: float = 0.0):
        super().__init__(x, y)
        self.z = z

# 请自行补全并打印类型验证
```

```python
from typing import Self

class Temperature:
    """温度值，支持多种构造方式。"""

    def __init__(self, celsius: float):
        self.celsius = celsius

    @classmethod
    def from_fahrenheit(cls, value: float) -> Self:
        # 替代构造函数：从华氏度创建实例
        return cls((value - 32) * 5 / 9)

    @classmethod
    def from_kelvin(cls, value: float) -> Self:
        return cls(value - 273.15)

    def __repr__(self) -> str:
        return f"Temperature(celsius={self.celsius:.2f})"


class FahrenheitTemperature(Temperature):
    """子类：返回类型会自动跟随 cls。"""
    pass


if __name__ == "__main__":
    t1 = Temperature.from_fahrenheit(212)
    t2 = Temperature.from_kelvin(300)
    print(t1)                              # Temperature(celsius=100.00)
    print(t2)                              # Temperature(celsius=26.85)

    t3 = FahrenheitTemperature.from_fahrenheit(32)
    print(type(t3).__name__, t3)           # FahrenheitTemperature Temperature(celsius=0.00)
```

## py.oop.staticmethod

# py.oop.staticmethod：一节课搞懂静态方法

## 一句话直觉

`@staticmethod`（静态方法）就是「写在类里、但不依赖实例和类状态的普通函数」——它只是**逻辑上归属**这个类，调用时不用先 `self` 或 `cls`。

---

## 1. 为什么需要它？

你写了一个 `Circle` 类，需要计算圆的面积。这个公式只和「半径」有关，和某个具体实例、和整个类的统计信息都无关——它就是一个数学工具函数。

你希望它「住」在 `Circle` 里，方便别人一看就知道「这是圆相关的工具」：

```python
import math

class Circle:
    def __init__(self, radius: float) -> None:
        self.radius = radius

    @staticmethod
    def area(radius: float) -> float:
        # 不需要 self，也不需要 cls
        return math.pi * radius ** 2

# 可以直接通过类调用，不创建实例
print(Circle.area(2))        # 12.566...
```

关键点：**不需要 `self`，也不需要 `cls`**。这是它和普通方法、类方法最本质的区别。

---

## 2. 三种方法对比：instance / class / static

在 Python 里，类里面的方法有三种「绑定方式」：

| 类型 | 第一个参数 | 访问的对象 | 装饰器 |
|------|-----------|-----------|--------|
| 实例方法 instance method | `self` | 实例 | 无 |
| 类方法 class method | `cls` | 类 | `@classmethod` |
| 静态方法 static method | 无 | 都不访问 | `@staticmethod` |

```python
class Demo:
    class_attr = "I am class-level"

    def instance_m(self):
        return f"instance sees {self.class_attr}"

    @classmethod
    def class_m(cls):
        return f"class sees {cls.class_attr}"

    @staticmethod
    def static_m():
        return "I don't see anything automatically"

d = Demo()
print(d.instance_m())   # instance sees I am class-level
print(Demo.class_m())   # class sees I am class-level
print(Demo.static_m())  # I don't see anything automatically
```

记忆口诀：
- `self` = 我（当前实例）
- `cls` = 我们（类本身）
- 静态方法 = **谁也不**，就是一段纯函数

---

## 3. 它和「模块级普通函数」有什么区别？

从执行角度看，`Circle.area(2)` 和把 `area` 单独写在模块里几乎没有区别。差异主要在**代码组织和语义**：

1. **命名空间归属**：看到 `Circle.area` 就知道它服务于 `Circle` 这个领域。
2. **可被继承/覆写**：子类可以覆盖 `area`，调用方代码不用改。
3. **工具发现性**：IDE 中打 `Circle.` 就能列出所有相关工具。

```python
class Circle:
    @staticmethod
    def area(r: float) -> float:
        return 3.14159 * r * r

class UnitCircle(Circle):
    @staticmethod
    def area(r: float = 1.0) -> float:
        # 子类可以替换实现
        return super(UnitCircle, UnitCircle).area(r)

print(UnitCircle.area(2))  # 12.56636
```

结论：**需要「归属感」和「可被覆写」，但不需要实例/类状态**时，用 `@staticmethod`。

---

## 4. 什么时候该用（和不该用）

**该用**：
- 纯工具函数：字符串转换、校验、数学计算、格式解析。
- 工厂辅助：类的构造函数里调用的、不需要状态的辅助逻辑。
- 明确表达「这个功能属于这个类」的语义。

**不该用**：
- 需要访问 `self.xxx` 时 → 必须用实例方法。
- 需要访问 `cls.xxx` 或创建 `cls(...)` 时 → 用 `@classmethod`。
- 确实只是模块内工具、跟类毫无关系 → 直接写模块级函数更简单。

```python
class Temperature:
    def __init__(self, celsius: float) -> None:
        self.celsius = celsius

    @staticmethod
    def c_to_f(c: float) -> float:
        # 纯工具函数：不访问 self，也不访问 cls
        return c * 9 / 5 + 32

    def fahrenheit(self) -> float:
        # 需要 self.celsius，必须是实例方法
        return self.c_to_f(self.celsius)

t = Temperature(25)
print(t.fahrenheit())            # 77.0
print(Temperature.c_to_f(25))    # 77.0
```

---

## 5. 常见误区速查

1. **误加 `self`**：`@staticmethod` 下的函数如果还写 `self`，会报 `TypeError: ... takes 1 positional argument but 2 were given`。
2. **以为不能通过实例调用**：其实 `t.c_to_f(25)` 也能跑，只是不会自动传 `self`。
3. **该用 `@classmethod` 时误用**：需要访问 `cls`（比如返回子类实例）时，`@staticmethod` 做不到多态。
4. **滥用**：把所有函数都塞进类里当静态方法，会让模块级工具函数变得啰嗦。

---

## 动手练习

写一个 `Validator` 类，包含：

1. 一个 `@staticmethod` 方法 `is_email(text: str) -> bool`，用简单的规则判断（包含 `@`，`@` 后面有 `.`，且非空）。
2. 一个 `@staticmethod` 方法 `normalize(text: str) -> str`，返回去掉首尾空格并转小写的结果。
3. 一个实例方法 `check(self, text: str) -> bool`，先 `normalize` 再 `is_email`。

测试要求：
- 用 `Validator.is_email("a@b.com")` 直接调用，返回 `True`。
- 用 `v = Validator(); v.check("  A@B.COM ")` 返回 `True`。
- 尝试给 `is_email` 加上 `self` 参数，观察报错，理解为什么静态方法不能要 `self`。

提示：`normalize` 里可以用 `text.strip().lower()`。

```python
import math

class Circle:
    def __init__(self, radius: float) -> None:
        self.radius = radius

    @staticmethod
    def area(radius: float) -> float:
        """纯函数：与实例、类状态无关"""
        return math.pi * radius ** 2

    def area_of_self(self) -> float:
        """实例方法可以复用静态方法"""
        return Circle.area(self.radius)


class Temperature:
    def __init__(self, celsius: float) -> None:
        self.celsius = celsius

    @staticmethod
    def c_to_f(c: float) -> float:
        return c * 9 / 5 + 32

    def fahrenheit(self) -> float:
        return self.c_to_f(self.celsius)


if __name__ == "__main__":
    # 1) 直接通过类调用静态方法，不需要实例
    print(Circle.area(2))                      # 12.566370614359172

    # 2) 通过实例调用静态方法（也会工作，但不会自动传 self）
    c = Circle(2)
    print(c.area(3))                           # 28.274333882308138
    print(c.area_of_self())                    # 12.566370614359172

    # 3) 静态方法 vs 实例方法对比
    t = Temperature(25)
    print(Temperature.c_to_f(25))              # 77.0
    print(t.fahrenheit())                      # 77.0
```


---

## 本课题目

### single_choice · None



- [A] 只能通过实例调用，不能通过类调用
- [B] 可以通过实例调用，也可以通过类调用（需显式传入实例）
- [C] 只能通过类调用，不能通过实例调用
- [D] 必须使用 @staticmethod 装饰后才能调用

**参考答案**：1

**解析**：实例方法既可通过实例调用（自动传入 self），也可通过类调用，但需要显式传入实例对象作为第一个参数。

### single_choice · None



- [A] 报错：缺少参数 self
- [B] A.f
- [C] None
- [D] 打印函数对象地址

**参考答案**：1

**解析**：通过实例调用 f() 时，Python 会自动将 a 作为 self 传入，返回 'A.f'。

### single_choice · None



- [A] self
- [B] cls，代表类本身
- [C] instance
- [D] 没有参数

**参考答案**：1

**解析**：类方法自动接收类对象作为第一个参数，通常命名为 cls，用于操作类级别的属性或构造实例。

### single_choice · None



- [A] 6
- [B] 报错：f 需要 self
- [C] None
- [D] 3

**参考答案**：0

**解析**：静态方法可以直接通过类调用，传入参数 3，返回 6，不需要实例。

### single_choice · None



- [A] A
- [B] B
- [C] 报错
- [D] None

**参考答案**：1

**解析**：类方法通过子类 B 调用时，cls 是 B，因此返回 B 的类名 'B'。

### single_choice · None



- [A] 返回 None
- [B] 报错：AttributeError，A 没有属性 x
- [C] 返回 0
- [D] 自动创建 x 并返回

**参考答案**：1

**解析**：A 类没有定义实例属性 x，访问 self.x 会引发 AttributeError。

### single_choice · None



- [A] 2 2
- [B] 2 3
- [C] 1 2
- [D] 报错

**参考答案**：1

**解析**：每次调用 f 都会修改实例属性 self.x，第一次返回 2，第二次返回 3。

### single_choice · None



- [A] 是公开方法，任何地方都能直接访问
- [B] 名称会被改写为 _类名__f，起到一定私有化作用
- [C] 是魔术方法，会自动被调用
- [D] 必须通过 super 调用

**参考答案**：1

**解析**：Python 的名称改写机制会将 __f 改写为 _类名__f，这是一种弱私有化，防止意外覆盖。

### single_choice · None



- [A] A
- [B] B
- [C] AB
- [D] 报错

**参考答案**：1

**解析**：g 中调用 self.f()，由于多态，self 是 B 的实例，因此调用 B 重写的 f，返回 'B'。

### single_choice · None



- [A] 实例方法在定义时就绑定到具体实例
- [B] 实例方法在通过实例访问时才会绑定，返回绑定方法对象
- [C] 实例方法通过类访问时也自动绑定到类
- [D] 实例方法无法作为普通函数对象传递

**参考答案**：1

**解析**：实例方法在通过实例访问时发生绑定，生成绑定方法对象；通过类访问时得到函数对象，需要手动传实例。

### single_choice · None



- [A] A
- [B] 报错：m 需要 self
- [C] None
- [D] 打印方法对象

**参考答案**：0

**解析**：a.f 是绑定方法，已绑定实例 a，赋值给 m 后调用 m() 不需要再传 self，返回 'A'。

### single_choice · None



- [A] A
- [B] 报错：m 需要 self
- [C] None
- [D] 打印函数对象

**参考答案**：0

**解析**：A.f 是未绑定的函数对象，赋值给 m 后调用需要显式传入实例，这里传入 A()，返回 'A'。

### single_choice · None



- [A] A.f
- [B] 报错：f 需要 0 个参数但传入了 1 个
- [C] 报错：self 未定义
- [D] None

**参考答案**：0

**解析**：通过类调用实例方法时，不会自动绑定实例，必须手动传入一个实例作为 self，这里传入了 A()，返回 'A.f'。

### single_choice · None



- [A] self 是 Python 关键字，必须命名为 self
- [B] self 是约定俗成的名字，可以改成其他名字，但必须是第一个参数
- [C] self 只存在于 __init__ 中，其他方法不能有
- [D] self 是自动传入的，方法定义时不能写 self

**参考答案**：1

**解析**：self 不是关键字，只是约定名称；它代表调用该方法的实例，必须是定义的第一个参数。

### single_choice · None



- [A] 3
- [B] 报错：f 未定义
- [C] 2
- [D] None

**参考答案**：0

**解析**：在 g 中通过 self.f(2) 调用同一实例的 f 方法，传入 2 返回 3。

### single_choice · None



- [A] A
- [B] B
- [C] AB
- [D] 报错

**参考答案**：1

**解析**：B 重写了父类 A 的 f 方法，实例 b 调用的是 B 中定义的 f，返回 'B'。

### single_choice · None



- [A] self.super().f()
- [B] super().f()
- [C] parent.f()
- [D] super.f()

**参考答案**：1

**解析**：super() 返回父类代理对象，通过 super().f() 可调用父类方法；self.super() 和 super.f() 均不存在。

### single_choice · None



- [A] AB
- [B] BA
- [C] A
- [D] B

**参考答案**：0

**解析**：B.f 先通过 super().f() 调用父类 A.f 得到 'A'，再拼接 'B' 得到 'AB'。

### single_choice · None



- [A] A
- [B] B
- [C] 报错：B 不是 A 的实例
- [D] None

**参考答案**：0

**解析**：B 继承自 A，B() 是 A 的实例；通过 A.f 调用时传入 B() 作为 self，执行的是 A 中定义的 f，返回 'A'。

### single_choice · None



- [A] 静态方法不能有返回值
- [B] 静态方法不会自动接收 self 或 cls 参数
- [C] 静态方法只能通过类调用
- [D] 静态方法不能访问类的任何属性

**参考答案**：1

**解析**：静态方法不需要 self 或 cls 参数，它只是放在类命名空间中的普通函数，可通过类或实例调用。

### single_choice · None



- [A] 只能通过实例调用，如 Circle(2).from_diameter(10)
- [B] 可以通过类调用，如 Circle.from_diameter(10)，此时 cls 自动绑定为 Circle
- [C] 必须显式传入类作为第一个参数，如 Circle.from_diameter(Circle, 10)
- [D] 只能通过子类调用，父类无法调用类方法

**参考答案**：1

**解析**：classmethod 会把类本身作为第一个参数自动传入（惯例命名为 cls），因此既可用类名调用，也可用实例调用；用类名调用时 cls 就是该类，且子类调用时 cls 会是子类。显式传类会导致参数重复。

### single_choice · None



- [A] 只有 create，因为 cls 会绑定实际调用的类
- [B] 只有 info，因为 staticmethod 不依赖实例
- [C] create 和 info 都能感知子类类型
- [D] 都不能，必须创建实例后才能调用

**参考答案**：0

**解析**：classmethod 的 cls 参数会绑定到实际调用该方法的类（含子类），因此子类调用 create 时会构造子类实例；staticmethod 不接收 cls 或 self，无法感知调用者的类型。

### multi_choice · None



- [A] cls 指向实际调用 register 的类
- [B] cls._items 在子类未覆盖 _items 时与父类共享同一列表对象
- [C] 每次调用 cls._items.append(item) 会原地修改共享列表
- [D] cls 是实例，等价于 self
- [E] cls 必须显式作为参数传入

**参考答案**：[0, 1, 2]

**解析**：cls 是调用者所属的类而非实例。子类若不重新定义 _items，就沿用父类属性，两者指向同一个可变列表，所以 append 会影响两边的视图。

### fill_blank · None



**参考答案**：["classmethod"]

**解析**：classmethod 是内置装饰器，用来声明类方法，它的第一个参数通常命名为 cls，由解释器自动传入调用类。

### fill_blank · None



**参考答案**：["Shape", "Shape 类", "Shape类"]

**解析**：通过 Shape.create(3) 调用时，解释器自动把 Shape 类绑定给 cls，所以 cls 就是 Shape。

### fill_blank · None



**参考答案**：["Base Sub", "Base Sub "]

**解析**：cls 分别绑定 Base 和 Sub，因此 cls.__name__ 分别为 'Base' 和 'Sub'，打印结果为 'Base Sub'。

### code_reading · None



**参考答案**：输出依次为 1、2、2。cls.count += 1 读取类属性 count 并加一后写回类属性，因此三次打印分别为 1、2、2。

**解析**：cls.count 访问的是类属性；+= 会读值、加一、再赋值回类属性。类方法通过 cls 修改的是类的属性而不是实例属性，因此 Counter.count 最终为 2。

### code_reading · None



**参考答案**：输出为 'Special special'。cls 绑定的是 Special，因此 cls() 构造的是 Special 实例，实例上读到的 kind 是子类覆盖后的 'special'。

**解析**：类方法的 cls 指向实际调用的类，Special.make() 时 cls 即 Special，所以返回 Special 实例；子类重新定义了 kind，属性查找优先命中子类值。

### code_reading · None



**参考答案**：能运行，输出 'A'。虽然参数命名为 self，但类方法依然会传入类对象，类对象也有 __name__ 属性，因此输出类名 'A'。

**解析**：参数名称不影响绑定规则，类方法始终自动传入调用类。把参数命名为 self 只是容易误导读者，并不是语法错误。

### scenario · None



**解析**：用 classmethod 并接收 cls，在方法体内返回 cls(...)，这样通过子类调用时能构造子类实例，符合多态与可扩展要求。

### scenario · None



**解析**：若方法既不使用 self 也不使用 cls，说明它不依赖实例或调用类，写成 staticmethod 更准确地表达意图，避免误导调用者以为它依赖类信息，也减少与子类绑定的隐含语义。

### single_choice · None



- [A] 100.0
- [B] 212.0
- [C] 32.0
- [D] 180.0

**参考答案**：0

**解析**：from_fahrenheit 是类方法，调用时 cls 绑定为 Temperature，构造出实例并设置 celsius 为 (212-32)*5/9 = 100.0。

### single_choice · None



- [A] Dog.name() 返回 'Animal'，因为 cls 总是指向定义该方法的类
- [B] Dog.name() 返回 'Dog'，因为调用时 cls 绑定为实际调用的子类
- [C] Dog.name() 会报错，因为子类没有重新定义 name
- [D] Dog.name() 返回 'Dog'，因为 classmethod 会自动创建子类实例

**参考答案**：1

**解析**：classmethod 的 cls 绑定的是实际被调用的类对象，所以通过子类调用时 cls 是子类，cls.__name__ 即为 'Dog'。

### single_choice · None



- [A] @staticmethod
  def parse(s):
      return MyClass(...)
- [B] @classmethod
  def parse(cls, s):
      return cls(...)
- [C] def parse(self, s):
      return MyClass(...)
- [D] @property
  def parse(self):
      return ...

**参考答案**：1

**解析**：替代构造器需要能构造调用者所属的类（便于被继承扩展），所以用 classmethod 接收 cls，并返回 cls(...) 而非硬编码类名。staticmethod 无法感知调用类，实例方法需要先有实例。

### single_choice · None



- [A] classmethod 的第一个参数惯例是 self
- [B] classmethod 的第一个参数惯例是 cls，代表调用该方法的类
- [C] classmethod 不需要任何参数
- [D] classmethod 的第一个参数名字必须叫 cls，否则语法错误

**参考答案**：1

**解析**：classmethod 自动接收调用类作为第一个参数，惯例命名为 cls；名字本身不是强制的，但约定用 cls 以免混淆。用 self 命名会引发可读性问题但不会直接报错。

### single_choice · None



- [A] 用普通实例方法，先创建空实例再修改属性
- [B] 用类方法接收 cls，并返回 cls(...)
- [C] 用静态方法，在内部硬编码类名
- [D] 用私有名称改写，强行规定只能由父类创建

**参考答案**：1

**解析**：类方法通过 cls 能感知调用的具体子类，便于被继承和多态扩展；硬编码类名的静态方法会失去这种灵活性，实例方法需要先有实例。

### multi_choice · None



- [A] classmethod 可以通过类名直接调用
- [B] classmethod 可以通过实例调用，此时 cls 绑定该实例所属的类
- [C] classmethod 的第一个参数是调用该方法时自动传入的类对象
- [D] classmethod 内部不能访问类属性
- [E] classmethod 只能用于构造函数场景

**参考答案**：[0, 1, 2]

**解析**：类方法既可通过类调用也可通过实例调用；无论哪种方式，cls 都是调用者所属的类。它也可以访问类属性（cls.attr），用途也不限于构造，比如工厂、注册、替代构造器等。

### multi_choice · None



- [A] 从 JSON 字符串解析并创建对象（替代构造器）
- [B] 在类级别维护并返回注册表（比如子类自动登记）
- [C] 需要获取调用者所属子类信息并据此构造实例
- [D] 仅对单个实例的私有属性做一次性修改
- [E] 在实例内部修改 self 的某个属性

**参考答案**：[0, 1, 2]

**解析**：替代构造器、类级别注册/统计、利用 cls 感知子类，都是 classmethod 的典型用途。仅操作某个实例的状态用普通实例方法更合适。

### multi_choice · None



- [A] classmethod 的第一参数是 cls，staticmethod 不接收隐式参数
- [B] classmethod 能感知调用它的类，staticmethod 不能
- [C] 两者都可以通过类名或实例调用
- [D] staticmethod 必须先创建实例才能调用
- [E] classmethod 不能被子类继承

**参考答案**：[0, 1, 2]

**解析**：classmethod 接收自动绑定的 cls，能感知调用类；staticmethod 不接收隐式参数，退化为普通函数。两者都可通过类名或实例调用。staticmethod 不需要实例，类方法也可继承。

### single_choice · None



- [A] 只能通过实例调用，不能通过类调用
- [B] 只能通过类调用，不能通过实例调用
- [C] 既可以通过类名调用，也可以通过实例调用
- [D] 必须显式传入 self 才能调用

**参考答案**：2

**解析**：静态方法与普通函数类似，不绑定实例或类，因此通过类名和实例都能调用，且不会自动传入 self 或 cls。

### single_choice · None



- [A] 10
- [B] 5
- [C] 会报错，缺少 self 参数
- [D] 会报错，staticmethod 不能这样用

**参考答案**：0

**解析**：静态方法 double 接收一个参数 x，通过类名传入 5，返回 5*2=10，不涉及 self。

### multi_choice · None



- [A] 静态方法不会自动接收 self 参数
- [B] 静态方法不会自动接收 cls 参数
- [C] 静态方法可以通过实例对象调用
- [D] 静态方法必须定义在模块顶层，不能放在类中
- [E] 静态方法可以用子类或父类名调用

**参考答案**：[0, 1, 2, 4]

**解析**：静态方法不绑定 self 或 cls，可通过类名或实例调用，也可被继承后调用。它必须定义在类中（或用 staticmethod 包装后赋值给类），不能放在类外作为类方法。

### multi_choice · None



- [A] 实现一个与实例状态无关的字符串格式化工具函数
- [B] 进行数据校验，只依赖传入的参数
- [C] 需要修改类级别的计数器
- [D] 实现与类相关的纯计算逻辑，方便归类管理
- [E] 需要访问实例的私有属性

**参考答案**：[0, 1, 3]

**解析**：静态方法适合与实例、类状态无关的纯逻辑。修改类级别状态应使用类方法；访问实例私有属性需要实例方法。

### multi_choice · None



- [A] 静态方法本质上是一个定义在类命名空间中的普通函数
- [B] 静态方法在被调用时不会发生自动的参数绑定
- [C] 静态方法可以直接访问所在类的类属性，无需通过类名
- [D] staticmethod 是一个内置的描述符类型
- [E] 静态方法只能通过类名访问

**参考答案**：[0, 1, 3]

**解析**：静态方法定义在类命名空间中，行为类似普通函数，无自动绑定，staticmethod 是内置描述符。访问类属性需要通过类名显式引用。静态方法也可通过实例访问。

### multi_choice · None



- [A] 子类可以直接调用继承来的静态方法
- [B] 子类可以重写父类的静态方法
- [C] 在子类中重写静态方法后，通过子类调用的是子类的版本
- [D] 静态方法会自动绑定到子类，传入 cls
- [E] 父类中定义的静态方法，子类无法访问

**参考答案**：[0, 1, 2]

**解析**：静态方法能被继承、重写和覆盖，且不会自动接收 cls。子类可以访问父类静态方法。

### fill_blank · None



**参考答案**：["staticmethod", "staticmethod"]

**解析**：不接收 self 或 cls 的方法需要 @staticmethod 装饰，才能通过类或实例调用不报错。

### fill_blank · None



**参考答案**：["无", "无参数", "不传", "不会传入", "none"]

**解析**：静态方法调用时不进行参数绑定，实例调用也不会自动传入实例或类。

### code_reading · None



**参考答案**：APP_debug

**解析**：静态方法内部通过类名 Config 显式访问类属性 prefix，拼接 'debug' 得到 'APP_debug'。静态方法本身不会自动获得类引用，必须显式通过类名访问。

### code_reading · None



**参考答案**：报错，NameError: name 'count' is not defined（或 UnboundLocalError）。静态方法没有 self/cls，也无法直接访问类属性 count，必须写成 Counter.count。

**解析**：静态方法内部作用域不包含自动传入的类或实例引用，直接用 count 会被当作局部变量，导致未定义错误。应显式使用 Counter.count。

### code_reading · None



**参考答案**：9 9.0

**解析**：子类重写了父类的静态方法，通过 Shape 调用得到整数 9，通过 Square 调用得到浮点 9.0。静态方法支持重写且不涉及参数绑定。

### scenario · None



**解析**：该方法不依赖实例属性和类属性，只是纯校验逻辑，属于类命名空间下的工具方法，适合用 @staticmethod。静态方法不自动绑定 self 或 cls，因此实例调用和类调用都不会自动多传参数，行为一致。

### single_choice · None



- [A] 两者都会自动接收第一个参数
- [B] 静态方法自动接收 cls，类方法自动接收 self
- [C] 静态方法不自动接收任何参数，类方法自动接收 cls
- [D] 两者都不自动接收参数

**参考答案**：2

**解析**：静态方法本质上就是普通函数，不自动传参；类方法会自动把类本身作为第一个参数 cls 传入。

### scenario · None



**解析**：该方法依赖实例属性 first_name 和 last_name，本质上是实例行为，写成实例方法后 self 会自动传入，调用更自然；用静态方法却接收名为 self 的参数，只是把实例显式当普通参数传，违背了静态方法只处理与实例无关逻辑的定位。

### single_choice · None



- [A] Hello, World
- [B] TypeError: greet() missing 1 required positional argument
- [C] Hello, a
- [D] 会报错，因为静态方法不能用实例调用

**参考答案**：0

**解析**：实例调用静态方法时不会把实例作为第一个参数传入，name 被赋值为 'World'，正常输出 Hello, World。

### single_choice · None



- [A] 方法需要访问实例属性
- [B] 方法需要访问类属性并可能修改类状态
- [C] 方法只依赖传入的参数完成计算，与实例和类都无关
- [D] 方法需要被子类重写以改变多态行为

**参考答案**：2

**解析**：静态方法适用于不与实例状态、类状态交互的纯工具型逻辑，只是逻辑上归属于该类。

### single_choice · None



- [A] 打印 base
- [B] 报错，静态方法不能被继承
- [C] 打印 Child
- [D] 报错，Child 没有定义 util

**参考答案**：0

**解析**：静态方法像普通属性一样可以被子类继承，Child.util() 直接调用父类定义的静态方法，返回 'base'。

### single_choice · None



- [A] 正常输出 4
- [B] 报错，因为缺少 self 参数
- [C] 输出 3
- [D] 输出 NotImplemented

**参考答案**：0

**解析**：通过类名调用未加装饰器的普通方法时，相当于调用普通函数，Python 不会自动传 self，所以 B.calc(3) 正常返回 4。但通过实例调用就会出错。

### single_choice · None



- [A] 15 25
- [B] 5 20
- [C] 报错，默认参数不能与静态方法一起用
- [D] 15 20

**参考答案**：0

**解析**：静态方法支持默认参数，C.add(5) 使用默认 b=10 返回 15；C.add(5,20) 返回 25。

### single_choice · None



- [A] 静态方法不能访问实例属性
- [B] 静态方法不能访问类属性（需要通过类名显式访问）
- [C] 静态方法定义时必须包含 self 参数
- [D] 静态方法可以在不创建实例的情况下调用

**参考答案**：2

**解析**：静态方法不需要 self 参数，也不会自动接收任何绑定参数。若需要访问类属性可显式通过类名访问。

### single_choice · None



- [A] setattr(MyClass, 'foo', staticmethod(func))
- [B] setattr(MyClass, 'foo', func)
- [C] MyClass.foo = classmethod(func)
- [D] MyClass.foo = property(func)

**参考答案**：0

**解析**：staticmethod 是一个描述符，可以在赋值时显式包装函数，将函数作为静态方法绑定到类上。直接赋值普通函数会变成普通方法，通过实例调用时会自动传 self。
