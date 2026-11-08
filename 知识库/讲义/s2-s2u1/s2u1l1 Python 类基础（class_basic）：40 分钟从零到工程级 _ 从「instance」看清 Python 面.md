# s2u1l1 Python 类基础（class_basic）：40 分钟从零到工程级 / 从「instance」看清 Python 面向对象的第一步 / `__init__`：对象诞生的第一行代码

> 来源 `content/lessons/s2u1l1.json`

## py.oop.class_basic

# Python 类基础（class_basic）：40 分钟从零到工程级

## 一句话直觉

类（class）是“把数据 + 操作数据的方法打包在一起”的模板；有了它，你就能从“写一堆散落的函数和字典”升级到“写一个可复用、可扩展、可维护的对象模型”。

---

## 1. 为什么需要类：先看“没有类”的痛苦

假设要表示一个学生，含姓名和成绩。用字典可以，但很快会乱：

```python
# 用字典表示学生
s1 = {"name": "Alice", "score": 90}
s2 = {"name": "Bob", "score": 85}

def average_score(students):
    return sum(s["score"] for s in students) / len(students)

print(average_score([s1, s2]))  # 87.5
```

问题：
- 字段名靠约定，写错 `"socre"` 不会报错，运行时才炸。
- 相关函数（如加分、排名）散落各处，没有“归属感”。
- 想加一个“是否及格”的规则，每次都要手动传字典。

**类解决的就是：把“数据”和“针对这些数据的操作”绑在一起，并给出一个明确的类型。**

---

## 2. 类的定义与实例化：`class` 关键字

`class` 定义一个类，类名惯例用大驼峰（CapWords）。`__init__` 是初始化方法（initializer），`self` 表示“当前实例”。

```python
# 定义一个最简单的类
class Student:
    """学生类：封装姓名与成绩。"""

    def __init__(self, name: str, score: int) -> None:
        # self.name / self.score 是实例属性（instance attribute）
        self.name = name
        self.score = score

    def is_pass(self) -> bool:
        # 方法（method）：第一个参数永远是 self
        return self.score >= 60


# 实例化（instantiation）：调用类名像调用函数
s = Student("Alice", 90)
print(s.name)        # Alice
print(s.is_pass())   # True
```

关键点：
- `__init__` 不是构造函数（constructor），实例已经创建后才调用它。
- `self` 不是关键字，只是约定俗成的第一个参数名，但强烈建议不要改。
- 属性访问用 `.`，如 `s.name`、`s.score`。

---

## 3. 实例属性 vs 类属性：别把两者搞混

- **实例属性（instance attribute）**：写在 `__init__` 里，用 `self.xxx`，每个实例各有一份。
- **类属性（class attribute）**：直接写在类体里，所有实例共享。

```python
class Student:
    school = "Online Academy"   # 类属性：所有学生共享

    def __init__(self, name: str, score: int) -> None:
        self.name = name        # 实例属性：每个学生不同
        self.score = score


a = Student("Alice", 90)
b = Student("Bob", 85)

print(a.school, b.school)   # Online Academy Online Academy
print(a.name, b.name)       # Alice Bob

# 修改类属性会影响所有实例
Student.school = "New Academy"
print(a.school, b.school)   # New Academy New Academy

# 给实例单独赋值，会“遮蔽”类属性，不影响别人
a.school = "Alice School"
print(a.school, b.school)   # Alice School New Academy
```

工程建议：
- 可变对象（如 `list`、`dict`）不要直接做类属性，否则所有实例共享同一份，容易引发 bug。
- 需要“默认值”时，在 `__init__` 里创建新对象。

```python
class Bad:
    tags = []          # 危险：所有实例共享同一个列表

class Good:
    def __init__(self) -> None:
        self.tags = []  # 安全：每个实例独立
```

---

## 4. 方法、`self` 与类型注解：工程级写法

类的方法（method）第一个参数是 `self`。Python 3.5+ 支持类型注解（type hint），配合 mypy、IDE 能提前发现错误。

```python
class Student:
    def __init__(self, name: str, score: int) -> None:
        self.name: str = name
        self.score: int = score

    def add_score(self, delta: int) -> None:
        """给成绩加分，delta 可正可负。"""
        self.score += delta

    def is_pass(self) -> bool:
        return self.score >= 60

    def describe(self) -> str:
        # 用 f-string 格式化输出
        status = "及格" if self.is_pass() else "不及格"
        return f"{self.name}: {self.score} 分（{status}）"


s = Student("Alice", 58)
print(s.describe())    # Alice: 58 分（不及格）
s.add_score(5)
print(s.describe())    # Alice: 63 分（及格）
```

工程要点：
- 用类型注解（PEP 484）表达意图，运行时不会强制检查，但工具会帮你查错。
- 比较类型用 `isinstance(obj, int)`，不要用 `type(obj) is type(1)`。
- 判断空序列用 `if not seq:`，不要写 `if len(seq):`。
- 布尔值不要与 `True`/`False` 用 `==` 比较，直接 `if flag:`。

---

## 5. 封装与“私有”约定：工程中怎么保护数据

Python 没有真正的 `private`，但用下划线表达意图：

- `_name`：单下划线，约定“内部使用”。
- `__name`：双下划线，触发名称改写（name mangling），外部访问会变成 `_ClassName__name`。

```python
class BankAccount:
    def __init__(self, owner: str, balance: float = 0.0) -> None:
        self.owner = owner
        self._balance = balance  # 约定：不要直接访问

    def deposit(self, amount: float) -> None:
        if amount <= 0:
            raise ValueError("存款金额必须为正数")
        self._balance += amount

    def withdraw(self, amount: float) -> None:
        if amount <= 0:
            raise ValueError("取款金额必须为正数")
        if amount > self._balance:
            raise ValueError("余额不足")
        self._balance -= amount

    @property
    def balance(self) -> float:
        """只读属性：外部只能读，不能直接改。"""
        return self._balance


acc = BankAccount("Alice", 100.0)
acc.deposit(50)
print(acc.balance)   # 150.0
# acc.balance = 999  # 会报错：property 没有 setter
```

工程级建议：
- 对外暴露“行为”（方法），而不是裸数据。
- 需要只读字段时用 `@property`。
- 需要校验时在方法里 `raise ValueError(...)`，配合 `try/except` 使用。
- 自定义异常继承 `Exception`，让调用方可以精确捕获。

---

## 6. 组合与 `if __name__ == "__main__"`：把类放进真正的项目

实际项目里，一个类通常放在一个模块（module）里，测试代码放在 `if __name__ == "__main__":` 下面。

```python
# student.py
class Student:
    def __init__(self, name: str, score: int) -> None:
        self.name = name
        self.score = score

    def is_pass(self) -> bool:
        return self.score >= 60


def main() -> None:
    students = [Student("Alice", 90), Student("Bob", 55)]
    for s in students:
        print(s.name, s.is_pass())


if __name__ == "__main__":
    main()
```

运行方式：
- `python student.py`：会执行 `main()`。
- `from student import Student`：不会执行 `main()`，只导入类。

这就是“可测试、可复用”的基本结构。

---

## 结尾：动手练习

**任务：写一个 `Book` 类，并完成一个小书架。**

要求：
1. `Book` 类有属性：`title`（str）、`author`（str）、`pages`（int）。
2. 方法 `is_long(self) -> bool`：页数大于 300 返回 `True`，否则 `False`。
3. 方法 `describe(self) -> str`：返回形如 `《Python入门》 by Alice, 320页` 的字符串。
4. 再加一个 `Shelf` 类，内部用列表保存多本 `Book`，提供：
   - `add(self, book: Book) -> None`
   - `long_books(self) -> list[Book]`：返回所有 `is_long()` 为 `True` 的书。
5. 在 `if __name__ == "__main__":` 里创建 3 本书，加入书架，打印所有“长书”的 `describe()`。

提示：
- 用类型注解。
- 用 `isinstance(book, Book)` 做校验（可选）。
- 用 f-string 格式化输出。

完成后再想一想：如果以后要加“电子书”类型，你会怎么改？这就是下一课“继承”的入口。

```python
# student_demo.py
# 可直接运行：python student_demo.py

class Student:
    """学生类：演示类基础。"""

    school = "Online Academy"  # 类属性：所有实例共享

    def __init__(self, name: str, score: int) -> None:
        self.name = name        # 实例属性
        self.score = score

    def is_pass(self) -> bool:
        return self.score >= 60

    def describe(self) -> str:
        status = "及格" if self.is_pass() else "不及格"
        return f"{self.name}: {self.score} 分（{status}）"


def main() -> None:
    students = [
        Student("Alice", 90),
        Student("Bob", 58),
        Student("Cindy", 72),
    ]
    for s in students:
        print(s.describe())
    print("学校：", Student.school)


if __name__ == "__main__":
    main()
```

## py.oop.instance

# py.oop.instance：从「instance」看清 Python 面向对象的第一步

## 一句话直觉

**Instance（实例）就是你用类（class）这个「模具」真正造出来的那个「具体对象」；没有实例，类只是一张图纸。**

例如，`Dog` 是类（图纸），`dog = Dog()` 里的 `dog` 才是实例（真狗）。学 OOP（Object-Oriented Programming，面向对象编程）的第一步，就是分清「类」和「实例」：类是抽象定义，实例是具体存在。

---

## 1. 类（class）与实例（instance）：图纸与实物

- **类（class）**：定义一类事物「长什么样、能做什么」。
- **实例（instance）**：按照类创建出来的具体对象，拥有自己的属性值。

创建实例的过程叫 **实例化（instantiation）**，写法是 `类名(...)`。

```python
class Dog:
    # 类属性：所有实例共享
    species = "Canis lupus familiaris"

    def __init__(self, name):
        # 实例属性：每个实例各自拥有
        self.name = name

# 实例化：dog1、dog2 是两个不同的实例
# __init__ 会自动被调用，name 被写入 self
```

关键结论：`Dog` 是类，`Dog()` 才产生实例；`self` 代表「当前这个实例」。

---

## 2. 实例属性和实例方法：数据挂在谁身上

`self.name = name` 表示「把 `name` 挂到当前实例上」。之后用 `实例.属性` 读取。
方法的第一个参数必须是 `self`，调用时 Python 自动把实例传进去。

```python
# 实例属性和实例方法：属性属于具体实例，方法通过 self 访问它
class Dog:
    def __init__(self, name):
        self.name = name

    def bark(self):
        # self 指向调用这个方法的实例
        return f"{self.name} 在汪汪叫"

# 创建两个实例，各有独立 name
dog1 = Dog("旺财")
dog2 = Dog("小黑")
# 各自调用方法，结果不同，证明属性是实例自己的
assert dog1.bark() == "旺财 在汪汪叫"
assert dog2.bark() == "小黑 在汪汪叫"
```

关键结论：实例属性通过 `self.x` 定义；实例方法第一个参数为 `self`，调用时不用手动传。

---

## 3. 动起来：给实例增删属性、判断它属于谁

Python 的实例是动态的，可以在运行时添加、删除、读取属性；也能通过 `isinstance` 判断一个对象是不是某个类的实例。

```python
class Dog:
    def __init__(self, name):
        self.name = name

# 动态添加实例属性：只影响这个实例
d = Dog("旺财")
d.age = 3
d.age = 4 if d.age == 3 else d.age
# 删除实例属性：再访问会报 AttributeError
# del d.age
# print(d.age)  # AttributeError

# isinstance(实例, 类)：判断 d 是否是 Dog 的实例
assert isinstance(d, Dog) is True
assert isinstance("hello", Dog) is False
```

关键结论：实例属性只属于那个实例；`isinstance(obj, Cls)` 是工程中最常用的实例判断方式。

---

## 4. 工程视角：实例、类、类型注解与自省

在真实工程里，实例常常配合**类型注解（type hints）** 与**自省（introspection）** 使用。`typing.get_type_hints()` 可以取出类上的注解；注意：**它不直接接受实例，要传它的类**。

```python
from typing import get_type_hints

class Dog:
    name: str
    age: int

    def __init__(self, name: str, age: int):
        self.name = name
        self.age = age

# 取出类上的类型注解
type_hints = get_type_hints(Dog)
# {'name': <class 'str'>, 'age': <class 'int'>}
assert type_hints["name"] is str
assert type_hints["age"] is int

# 对实例取注解要先用 type(实例) 拿到类
d = Dog("旺财", 3)
type_hints_on_instance = get_type_hints(type(d))
assert type_hints_on_instance["name"] is str
```

关键结论：`get_type_hints()` 传类或函数，不传实例；需要实例的注解时，用 `type(obj)` 取类。

---

## 5. 常见误区

1. **把类当实例用**  
   `Dog.name` 是类属性，`Dog("旺财").name` 才是实例属性，二者含义不同。

2. **忘记 `self`**  
   实例方法第一个参数必须是 `self`，但调用时不用传。

3. **把可变对象当类属性**  
   列表、字典等可变对象若放在类属性上，会被所有实例共享，容易踩坑。

4. **对实例调用 `get_type_hints()`**  
   这是不被支持的，应改为 `get_type_hints(type(obj))`。

```python
from typing import get_type_hints

class Dog:
    name: str

    def __init__(self, name):
        self.name = name

d = Dog("旺财")
# 正确：对类调用
assert get_type_hints(Dog)["name"] is str
# 正确：对实例先取类
assert get_type_hints(type(d))["name"] is str

# 错误示范（会抛 TypeError）：
# get_type_hints(d)
```

---

## 动手练习

**任务：写一个 `Book` 类，并观察实例行为。**

1. 定义 `Book` 类，类属性 `category = "图书"`。
2. `__init__` 接收 `title`、`author`，保存为实例属性。
3. 增加实例方法 `describe()`，返回 `"《title》 by author，属于 图书"`。
4. 创建两个不同的 `Book` 实例，分别打印 `describe()`，确认属性互不影响。
5. 给其中一个实例动态添加 `year = 2024`，打印它；确认另一个实例没有 `year`（用 `hasattr` 判断）。
6. （进阶）给 `Book` 加上类型注解 `title: str`、`author: str`，用 `get_type_hints(type(book))` 打印注解，并用 `isinstance(book, Book)` 验证。

参考代码骨架：

```python
from typing import get_type_hints

class Book:
    category = "图书"

    def __init__(self, title: str, author: str):
        self.title = title
        self.author = author

    def describe(self) -> str:
        return f"《{self.title}》 by {self.author}，属于 {Book.category}"

if __name__ == "__main__":
    b1 = Book("小王子", "圣埃克苏佩里")
    b2 = Book("局外人", "加缪")

    print(b1.describe())
    print(b2.describe())

    b1.year = 2024
    assert hasattr(b1, "year") is True
    assert hasattr(b2, "year") is False

    assert isinstance(b1, Book) is True
    print(get_type_hints(type(b1)))
```

完成标准：程序能运行、输出正确、两个实例属性互不干扰、`hasattr` 与 `isinstance` 断言通过。

## py.oop.init

# `__init__`：对象诞生的第一行代码

> **一句话直觉**：`__init__` 是 Python 对象“出生时”自动调用的初始化方法——它决定了你 `CustomerModel(id=1, name='Tom')` 时，`id` 和 `name` 到底是怎么落到 `self` 身上的。

---

## 1. 为什么需要 `__init__`？

在面向对象（Object-Oriented Programming, OOP）里，类（class）是“模板”，实例（instance）是“产品”。但光有模板不够：每个产品出厂时得带上自己的数据。

不写 `__init__` 会怎样？

```python
class Customer:
    pass

c = Customer()
c.id = 1          # 只能手动一个个挂
c.name = 'Tom'
```

问题是：**没有办法强制调用方传入必要数据**，很容易漏设属性、写出半成品对象。`__init__` 就是解决这个问题的入口。

> 术语：`__init__` 是 Python 的“魔术方法”（magic method / dunder method），名字前后各有两个下划线，会在特定时机被解释器自动调用。

---

## 2. 最基础写法：`self` 是谁？

```python
class Customer:
    def __init__(self, id: int, name: str) -> None:
        self.id = id
        self.name = name

c = Customer(1, 'Tom')
print(c.id, c.name)   # 1 Tom
```

关键点：

- **`self` 是实例本身**，由 Python 自动传入，不需要你手动给；`Customer(1, 'Tom')` 等价于 `Customer.__init__(c, 1, 'Tom')`。
- **`self` 只是约定名**（PEP 8 推荐），换成 `this` 也能跑，但没人这么写。
- 赋值到 `self.xxx` 的属性，会跟着实例走；只赋值给局部变量 `xxx` 的，函数结束就没了。

```python
class Bad:
    def __init__(self, id):
        id = id          # ❌ 只改了局部变量，实例上没有 id

b = Bad(1)
print(hasattr(b, 'id'))  # False
```

---

## 3. 默认值、关键字参数与 `dataclass` 的等价物

`__init__` 就是普通函数，可以用默认值、`*args`、`**kwargs`、关键字参数（keyword-only, kw-only）。

```python
class Customer:
    def __init__(self, id: int, name: str, vip: bool = False) -> None:
        self.id = id
        self.name = name
        self.vip = vip

Customer(1, 'Tom')                 # vip=False
Customer(1, 'Tom', vip=True)       # 用关键字更清楚
```

**规则**：有默认值的参数必须放在没有默认值的参数之后，否则会报 `SyntaxError`。

### `dataclass`：自动生成 `__init__`

写多了会发现 `self.x = x` 很啰嗦。标准库 `dataclasses` 帮我们自动生成：

```python
from dataclasses import dataclass

@dataclass
class Customer:
    id: int
    name: str

c = Customer(1, 'Tom')
print(c)   # Customer(id=1, name='Tom')
```

这背后等价于手写了 `__init__(self, id, name)`。类型检查器（type checker，如 mypy）也会把它当作有 `id`、`name` 两个参数的 `__init__`。

在 PEP 681 的 `@dataclass_transform` 里，还有一组**字段说明符（field specifier）参数**可以精细控制 `__init__` 的行为，其中最重要的是：

- **`init`**：该字段是否进入生成的 `__init__`。默认 `True`；设为 `False` 就不出现在构造参数里。
- **`default` / `default_factory`**：默认值，或一个在运行时生成默认值的回调（可变默认值必须用它）。
- **`kw_only`**：是否设为仅关键字（keyword-only）参数。
- **`alias`**：在生成的 `__init__` 里使用的替代名。

对应到实际代码：

```python
from dataclasses import dataclass, field

@dataclass
class Customer:
    id: int
    name: str
    tags: list = field(default_factory=list)   # ✅ 可变默认值用 factory
    cached: bool = field(default=False, init=False)  # ❌ 不进 __init__

c = Customer(1, 'Tom')   # cached 不用传，也没有对应参数
```

---

## 4. 一个常见陷阱：可变默认值

```python
class Bag:
    def __init__(self, items=[]):   # ❌ 危险！默认值只在定义时创建一次
        self.items = items

a = Bag(); a.items.append('x')
b = Bag()
print(b.items)  # ['x']  两个实例共享同一个列表
```

**正确写法**：默认值设为 `None`，函数体内再创建新对象。

```python
class Bag:
    def __init__(self, items=None):
        self.items = list(items) if items is not None else []
```

> 记忆口诀：**可变默认值 ≈ 全局共享**。

---

## 5. `__init__` 与 `__new__`、继承的关系（工程视角）

- `__new__` 负责**创建**实例（返回对象）；`__init__` 负责**初始化**这个已存在的实例。绝大多数情况只写 `__init__`。
- **子类如果不写 `__init__`**，会继承父类的 `__init__`；如果写了，需要显式调用 `super().__init__(...)`，否则父类的初始化被跳过。

```python
class Base:
    def __init__(self, id: int) -> None:
        self.id = id

class Customer(Base):
    def __init__(self, id: int, name: str) -> None:
        super().__init__(id)   # 别忘了这一句
        self.name = name
```

- `__init__` 的返回值**必须是 `None`**（准确说：绝对不能 `return 非None`）——它的职责就是改 `self`，不是造新值。

---

## 小结

1. `__init__` 是实例的初始化钩子，第一个参数 `self` 由 Python 自动传入。
2. 属性写在 `self` 上，参数默认值、关键字参数规则与普通函数一致。
3. `@dataclass` 能自动生成 `__init__`；字段可用 `init` / `default` / `default_factory` / `kw_only` / `alias` 精细控制。
4. 可变默认值必须用 `None` + 内部创建或 `default_factory`。
5. 子类自定义 `__init__` 时要调 `super().__init__(...)`。

---

## 动手练习

**任务**：实现一个迷你订单系统，用 `__init__` 和 `@dataclass` 两种方式各写一遍，对比差异。

**要求**：

1. 定义 `Order` 类，字段：
   - `order_id: int`（必填）
   - `customer_name: str`（必填）
   - `items: list[str]`（可选，默认为空列表，**务必避免可变默认值陷阱**）
   - `paid: bool`（默认 `False`，且**不进入 `__init__` 参数列表**）
2. 用**手写 `__init__`** 实现一版 `OrderManual`。
3. 用 **`@dataclass` + `field(default_factory=...)` + `field(init=False)`** 实现一版 `OrderData`。
4. 写一个函数 `total_items(order)`，返回 `len(order.items)`，两个类都要能传进去。
5. 创建一个 `OrderManual(1, 'Tom')` 和一个 `OrderData(1, 'Tom')`，分别往 `items` 里加一个字符串，打印结果，验证两个实例的 `items` 互不影响。

**验收标准**：

- 两版行为一致；
- `OrderData` 的构造函数签名里**没有** `paid` 参数；
- 两个订单的 `items` 各自独立。

**扩展思考（选做）**：如果把 `paid` 从 `init=False` 改成普通字段，会有什么后果？再加上继承再想一想。

```python
# 例 1：手写 __init__
class OrderManual:
    def __init__(self, order_id: int, customer_name: str, items=None) -> None:
        self.order_id = order_id
        self.customer_name = customer_name
        # 关键：避免可变默认值共享
        self.items = list(items) if items is not None else []
        self.paid = False  # 不暴露给构造参数


# 例 2：dataclass 等价写法
from dataclasses import dataclass, field

@dataclass
class OrderData:
    order_id: int
    customer_name: str
    items: list = field(default_factory=list)   # 每个实例独立列表
    paid: bool = field(default=False, init=False)  # 不进 __init__


def total_items(order) -> int:
    return len(order.items)


if __name__ == '__main__':
    a = OrderManual(1, 'Tom')
    b = OrderData(1, 'Tom')

    a.items.append('apple')
    b.items.append('banana')

    print(a.items, total_items(a))    # ['apple'] 1
    print(b.items, total_items(b))    # ['banana'] 1

    # 验证两个实例的 items 互不影响
    c = OrderManual(2, 'Jerry')
    d = OrderData(2, 'Jerry')
    print(c.items, d.items)           # [] []

    # OrderData 的 paid 不在构造参数里
    import inspect
    print(inspect.signature(OrderData.__init__))
```


---

## 本课题目

### single_choice · None



- [A] wang
- [B] 报错：bark 需要参数
- [C] None
- [D] Dog

**参考答案**：0

**解析**：d.bark() 调用实例方法时，Python 自动把 d 作为 self 传入，因此不需要额外参数，返回字符串 "wang"。

### single_choice · None



- [A] 它必须显式调用才能创建实例
- [B] 它在实例创建后自动被调用，常用来初始化属性
- [C] 它的返回值会成为新实例
- [D] 它只能定义在继承自 object 的类中

**参考答案**：1

**解析**：创建实例时 Python 会自动调用 __init__ 进行初始化，它不应返回非 None 值；实例本身由 __new__ 创建。

### single_choice · None



- [A] self 是 Python 关键字，必须命名为 self
- [B] self 是实例方法的第一个参数，调用时由 Python 自动传入
- [C] self 只能在 __init__ 中使用
- [D] self 指向类本身，不是实例

**参考答案**：1

**解析**：self 只是约定名称，表示当前实例，由 Python 在调用实例方法时自动传入；它不是关键字，也不指向类。

### single_choice · None



- [A] 1
- [B] 2
- [C] 报错
- [D] None

**参考答案**：0

**解析**：a.x 与 b.x 是各自实例的属性，互不影响；修改 b.x 不会改变 a.x。

### single_choice · None



- [A] "ok"
- [B] 报错：缺少参数
- [C] None
- [D] self

**参考答案**：0

**解析**：实例方法中可以通过 self 调用同一对象的其他方法，self.g() 返回 "ok"。

### single_choice · None



- [A] A
  A
- [B] A
  报错
- [C] 报错
  A
- [D] A
  None

**参考答案**：0

**解析**：a.f() 会自动把 a 作为 self 传入；A.f(a) 则显式传入 a，二者结果相同，都返回 "A"。

### single_choice · None



- [A] 类是实例的模板，实例是类创建出来的对象
- [B] 实例是类的模板，类是实例创建出来的对象
- [C] 类与实例是同一个对象
- [D] 实例必须先创建类才能存在

**参考答案**：0

**解析**：类定义对象的模板和属性方法，实例是根据类创建的具体对象。

### single_choice · None



- [A] d = Dog
- [B] d = Dog("Bob")
- [C] d = Dog.__init__("Bob")
- [D] d = new Dog("Bob")

**参考答案**：1

**解析**：创建实例使用类名加括号并传入 __init__ 所需参数；Dog 本身只是类对象，不带括号不会创建实例。

### single_choice · None



- [A] x
- [B] y
- [C] x 和 y 都是实例属性
- [D] x 和 y 都是类属性

**参考答案**：1

**解析**：在类体中直接赋值的 x 是类属性；在 __init__ 中通过 self.y 赋值的是实例属性。

### single_choice · None



- [A] 1
- [B] 报错：缺少位置参数 self
- [C] None
- [D] 0

**参考答案**：1

**解析**：通过类直接调用实例方法时不会自动传入 self，因此缺少参数会报错；应写成 A().f() 或 A.f(instance)。

### single_choice · None



- [A] 它可以返回实例对象
- [B] 它可以返回任意值
- [C] 它应返回 None，否则会报 TypeError
- [D] 它必须返回 self

**参考答案**：2

**解析**：__init__ 是初始化方法，应返回 None；如果真的 return 非 None 值，会引发 TypeError。

### single_choice · None



- [A] 15 15
- [B] 10 15
- [C] 15 10
- [D] 10 10

**参考答案**：1

**解析**：a.x += 5 等价于 a.x = a.x + 5，会创建实例属性 x=15，类属性 A.x 仍为 10。

### single_choice · None



- [A] True
- [B] False
- [C] 报错
- [D] None

**参考答案**：1

**解析**：每次调用类名都会创建一个新的实例对象，c1 与 c2 是两个不同对象，因此 is 比较为 False。

### single_choice · None



- [A] 10
- [B] 20
- [C] 报错
- [D] None

**参考答案**：1

**解析**：a 没有自己的实例属性 x，属性查找会回到类属性；类属性 A.x 被改为 20 后，a.x 读到 20。

### single_choice · None



- [A] 10
- [B] 99
- [C] 报错
- [D] None

**参考答案**：0

**解析**：a.x = 99 创建的是实例属性，只影响 a 自身，不会修改类属性 A.x。

### single_choice · None



- [A] 0
- [B] 1
- [C] 2
- [D] 报错

**参考答案**：2

**解析**：每次创建实例都会调用 __init__，通过类名访问并修改类属性 count，因此两次创建后为 2。

### single_choice · None



- [A] def show(): pass
- [B] def show(self): pass
- [C] def show(this): pass  # 只能叫 self
- [D] static show(self): pass

**参考答案**：1

**解析**：实例方法第一个参数通常命名为 self，但名字不是强制的；只要第一个参数能接收实例即可。def show(self): pass 是标准写法。

### single_choice · None



- [A] Tom
- [B] name
- [C] 报错：缺少参数
- [D] None

**参考答案**：0

**解析**：创建实例时传入 "Tom"，__init__ 将其保存为实例属性 self.name，因此 p.name 为 "Tom"。

### single_choice · None



- [A] 输出 None
- [B] 输出 0
- [C] 抛出 AttributeError
- [D] 输出空字符串

**参考答案**：2

**解析**：类 A 中未定义属性 x，访问不存在的类属性会抛出 AttributeError。

### single_choice · None



- [A] 1
- [B] 一个函数对象
- [C] 一个方法对象
- [D] 报错

**参考答案**：1

**解析**：通过类访问函数属性得到的是普通函数对象（在 Python 3 中），只有通过实例访问才会绑定成方法。

### single_choice · None



- [A] 实例属性定义在类体中，所有实例共享同一份
- [B] 实例属性通常通过 self.attr 在方法中赋值，每个实例各自持有一份
- [C] 实例属性必须定义在 __init__ 中，否则无法访问
- [D] 实例属性只能读取，不能修改

**参考答案**：1

**解析**：实例属性是与具体实例绑定的数据，通常在方法里通过 self.attr 赋值，每个实例拥有独立的副本，可以在任意方法中创建和修改，并非必须在 __init__ 中定义。选项 A 描述的是类属性的特征。

### single_choice · None



- [A] 旺财
- [B] 小黑
- [C] 大黄
- [D] 报错

**参考答案**：1

**解析**：每个实例的 name 是各自独立的实例属性，修改 a.name 不会影响 b.name，因此 b.name 仍为 '小黑'。

### multi_choice · None



- [A] 在 __init__ 中 self.x = 1
- [B] 在类外 obj.x = 1
- [C] 使用 setattr(obj, 'x', 1)
- [D] 仅写 Class.x = 1
- [E] 使用 obj.__dict__['x'] = 1

**参考答案**：[0, 1, 2, 4]

**解析**：A、B、C、E 都是直接作用于实例的赋值方式；Class.x = 1 修改的是类属性，不会创建实例属性。

### multi_choice · None



- [A] 它保存实例自己的属性映射
- [B] 修改它可直接增删实例属性
- [C] 所有实例共享同一个 __dict__ 对象
- [D] 它通常是一个普通字典

**参考答案**：[0, 1, 3]

**解析**：实例 __dict__ 是每个实例独立的属性字典（默认情况下），可直接操作；它并不被所有实例共享，C 错误。

### fill_blank · None



**参考答案**：["self.name", "self.name=", "self.name ="]

**解析**：实例方法通过 self 引用当前实例，赋值 self.name = name 即创建/修改实例属性。

### fill_blank · None



**参考答案**：["__dict__", "dict"]

**解析**：实例的 __dict__ 是一个字典，存放该实例自己的属性名与值。

### fill_blank · None



**参考答案**：["size"]

**解析**：version 定义在类体中属于类属性，size 通过 self 赋值属于实例属性。

### code_reading · None



**参考答案**：输出 []。因为 self.data = [] 在 __init__ 中为每个实例分别创建了独立的列表，a1 与 a2 各自持有不同的 data，a1.add 只影响 a1 的列表。

**解析**：关键区别在于这里是在 __init__ 中通过 self.data = [] 创建实例属性，而不是在类体中定义可变类属性，因此各实例相互独立。

### code_reading · None



**参考答案**：先输出 {'name': 'x'}，再输出 x。a.__dict__ 显示实例自己的属性字典；getattr(a, 'name') 按属性名取值，得到实例属性 'x'。

**解析**：实例属性被记录在实例 __dict__ 中，getattr 是等价的动态取属性方式。

### code_reading · None



**参考答案**：A.greet() 会抛出 TypeError，提示缺少位置参数 self。因为通过类名调用实例方法时不会自动传入实例，需要显式传入：A.greet(a)。

**解析**：实例方法只有在通过实例调用时才自动绑定 self；通过类调用需要手动提供实例参数。

### scenario · None



**解析**：类体中定义的 items 是类属性，被所有实例共享；如果在 __init__ 中写成 self.items = []，就为每个实例创建独立的实例属性，从而避免互相影响。

### scenario · None



**解析**：Python 的实例属性是动态的，可在运行期通过 obj.attr = value 或 setattr 添加，存于实例 __dict__。需要注意：访问未设置的属性会抛 AttributeError，getattr 可提供默认值；同时避免与类属性/方法名冲突，且动态添加不利于静态类型检查和可读性。

### single_choice · None



- [A] self 是 Python 关键字，必须命名为 self
- [B] self 在调用方法时由解释器自动传入，指向调用该方法的实例
- [C] self 指向类本身
- [D] self 只能在 __init__ 中使用

**参考答案**：1

**解析**：self 只是约定俗成的参数名，不是关键字，可以改成别的名字；它由解释器在通过实例调用方法时自动传入，指向当前实例（类方法中指向类的是 cls），且可用于任何实例方法。

### single_choice · None



- [A] 0
- [B] 1
- [C] 2
- [D] 报错

**参考答案**：2

**解析**：count 是类属性，每次实例化都会执行 Counter.count += 1，因此创建两个实例后类属性变为 2。

### single_choice · None



- [A] __init__ 在实例创建后自动被调用，用于初始化实例属性
- [B] __init__ 的返回值必须是 None
- [C] __init__ 是实例的构造器，负责分配对象内存
- [D] 在 __init__ 之前对象已经被创建

**参考答案**：2

**解析**：__init__ 是初始化方法而非构造器；真正的对象创建由 __new__ 完成，__init__ 只是对已创建好的实例做初始化，且其返回值必须为 None。

### single_choice · None



- [A] 1
- [B] no attr
- [C] None
- [D] 0

**参考答案**：1

**解析**：实例属性 x 只有在 set() 被调用后才会被创建，此时 a 尚未调用 set，因而访问 a.x 触发 AttributeError，被捕获后打印 no attr。

### single_choice · None



- [A] 永远读取类属性
- [B] 优先读取实例属性，若实例命名空间中不存在才回退到类属性
- [C] 直接报错
- [D] 两者会相加

**参考答案**：1

**解析**：属性查找遵循实例 __dict__ 优先，找不到时沿 MRO 去类中查找，因此同名时实例属性覆盖类属性。

### single_choice · None



- [A] []
- [B] [1]
- [C] 报错
- [D] [1, 1]

**参考答案**：1

**解析**：items 是类属性，两个实例共享同一个列表；self.items.append 并未创建实例属性，只修改了共享列表，因此 p2.items 也是 [1]。

### multi_choice · None



- [A] 实例属性保存在实例的 __dict__ 中
- [B] 实例属性可以通过 setattr 动态添加
- [C] 不同实例的同名实例属性互相独立
- [D] 实例属性必须先声明再使用，否则会报错
- [E] 实例属性可以在类外通过 obj.attr = value 设置

**参考答案**：[0, 1, 2, 4]

**解析**：实例属性存于实例 __dict__，可动态添加/删除，彼此独立，也能在类外直接赋值；Python 不要求属性预先声明，D 错误。

### multi_choice · None



- [A] __init__ 是初始化实例属性的常用位置
- [B] 实例属性也可以在非 __init__ 的方法中定义
- [C] __init__ 必须显式 return self 才能返回实例
- [D] 若 __init__ 返回非 None，会在实例化时抛出 TypeError

**参考答案**：[0, 1, 3]

**解析**：__init__ 常用于初始化，但不是唯一位置，实例属性可在任意方法中定义；它不应 return self（构造由 __new__ 负责），且返回非 None 会触发 TypeError。

### single_choice · None



- [A] 在类定义时自动调用一次
- [B] 在每次通过类创建实例对象时自动调用
- [C] 需要手动调用 obj.__init__() 才会执行
- [D] 只有在使用继承时才会被调用

**参考答案**：1

**解析**：__init__ 是实例初始化方法，每当通过类名调用创建新对象时，Python 会自动先创建实例再调用该实例的 __init__ 完成初始化。类定义本身不会调用它，也不需要手动调用，它与继承无关。

### single_choice · None



- [A] 7
- [B] 34
- [C] 报错：缺少参数
- [D] None

**参考答案**：0

**解析**：创建 Point(3, 4) 时 __init__ 将 self.x 设为 3、self.y 设为 4，因此 p.x + p.y 为 7。这里都是整数相加，不会做字符串拼接，也不会报错。

### multi_choice · None



- [A] 它在实例被创建后自动调用
- [B] 它的第一个参数通常命名为 self
- [C] 它可以有多个参数并带默认值
- [D] 它的返回值会被用作新实例
- [E] 它内部可以调用其他方法

**参考答案**：[0, 1, 2, 4]

**解析**：__init__ 在实例创建后自动执行，第一个参数约定为 self，可以有多个参数和默认值，方法体内也可调用其他方法。它的返回值必须为 None，不会成为新实例，所以第 4 项错误。

### multi_choice · None



- [A] 把默认值设为 None，在 __init__ 内按需新建列表或字典
- [B] 直接在默认参数里写 {}
- [C] 在 __init__ 内用 self.items = list(items) 复制一份
- [D] 每次创建对象前手动清空默认参数

**参考答案**：[0, 2]

**解析**：以 None 为默认值并在体内新建容器是标准做法；用 list(items) 复制也能避免共享引用。直接写 {} 会复现共享问题；手动清空默认参数不可靠也不推荐。

### multi_choice · None



- [A] 让它返回一个非 None 的值，如 return 1
- [B] 把第一个参数命名成 cls
- [C] 用 function 关键字代替 def
- [D] 参数列表写成了 def __init__ self, x):

**参考答案**：[0, 2, 3]

**解析**：返回非 None 会触发 TypeError；Python 中没有 function 关键字会在语法解析阶段报错；括号不匹配也是语法错误。把第一个参数命名成 cls 虽然不推荐但语法合法，不会报错。

### fill_blank · None



**参考答案**：["__init__"]

**解析**：实例初始化方法固定名为 __init__，两侧各两条下划线。缺一或多一条下划线都不会被识别为初始化方法，创建对象时不会执行该方法。

### fill_blank · None



**参考答案**：["self"]

**解析**：实例方法第一个参数约定为 self，代表当前实例。使用 self.w = w 才能把 w 绑定到实例上。虽然参数名可换成其他合法标识符，但标准答案与惯例都是 self。

### fill_blank · None



**参考答案**：["None", "None "]

**解析**：把不可变且语义中性的 None 作为默认值是最常见的做法，User() 调用时 role 即为 None。用可变对象（如 [] 或 {}）作默认值容易引发共享状态问题。

### code_reading · None



**参考答案**：创建 Product(10) 时会立即抛出 TypeError，因为 __init__ 返回了非 None 的 price。__init__ 必须返回 None，它的职责是初始化而不是产出实例。

**解析**：__init__ 无返回值语义，显式返回非 None 值会被解释器判定为错误，触发 TypeError。若删掉 return price 则一切正常。

### code_reading · None



**参考答案**：输出 3。每创建一次 Logger 实例，__init__ 就把类属性 instances 加一并写回类，共创建 3 次，因此打印 3。

**解析**：类属性 instances 被所有实例共享。通过 Logger.instances 显式读写类属性，每实例化一次就累加，因此最终值是 3。若写成 self.instances += 1，则创建的是实例属性，类属性不会被正确累加。

### code_reading · None



**参考答案**：输出 a b。Child 的 __init__ 先通过 super().__init__(tag) 调用父类构造，设置 self.tag，再设置 self.extra，因此两个属性都可用。

**解析**：子类覆盖了 __init__，必须显式调用父类初始化，否则父类负责的属性不会被设置。super().__init__(tag) 把 tag 传给 Base 完成父类部分的初始化，之后子类再补充自己的属性。

### scenario · None



**解析**：默认参数在函数定义时求值一次，所有未显式传参的调用共享同一个列表对象，导致跨实例污染。应改为 items=None，在 __init__ 内判断后 self.items = list(items) if items else []。

### single_choice · None



- [A] def __init__(self, name):
- [B] def init(self, name):
- [C] function __init__(self, name):
- [D] def __init__(name):

**参考答案**：0

**解析**：Python 中实例方法定义必须以 def 开头，第一个参数约定为 self，特殊方法名 __init__ 两侧各有两个下划线。init 没有双下划线不会被当作初始化方法；function 不是 Python 关键字；缺少 self 会导致实例调用时参数错位。

### scenario · None



**解析**：子类 __init__ 应先调用 super().__init__(color) 复用父类的校验与赋值逻辑，再设置自己新增的属性。若省略该调用，父类负责的属性（如 color）不会被初始化，访问时会抛 AttributeError；直接复制父类代码又会导致重复与维护困难。

### single_choice · None



- [A] self 是 Python 的关键字，必须这样写
- [B] self 指向正在被初始化的那个实例对象
- [C] self 是类本身，等价于 Counter
- [D] self 可以省略不写

**参考答案**：1

**解析**：self 只是约定俗成的参数名，代表当前实例对象。通过 self.count 把 count 绑定到该实例上。它不是关键字（换成别的名字也能运行），它指向实例而非类，且在实例方法中不能省略。

### single_choice · None



- [A] name 自动为 None
- [B] 正常创建，稍后赋值即可
- [C] 抛出 TypeError，提示缺少参数
- [D] 抛出 AttributeError

**参考答案**：2

**解析**：User() 没传 name，而 __init__ 需要 name 参数，Python 会在实例创建阶段抛出 TypeError 指出缺少必需的位置参数。它不会静默设为 None，也不是 AttributeError。

### single_choice · None



- [A] 不输出任何内容
- [B] 输出 A init
- [C] 抛出 AttributeError
- [D] 输出 B init

**参考答案**：1

**解析**：B 没有定义 __init__，会沿继承链继承 A.__init__，因此创建 B() 时执行 A 的初始化并打印 'A init'。B 本身没有初始化方法，所以不会打印 'B init'。

### single_choice · None



- [A] 必须返回 self，否则创建失败
- [B] 必须返回 None，否则会报错
- [C] 可以返回任意对象，会被当作实例
- [D] 返回值会被自动忽略，可返回任意值

**参考答案**：1

**解析**：__init__ 是初始化方法而非构造方法，它不负责返回实例。若返回非 None 的值，Python 会抛出 TypeError。因此它只能返回 None（即不写 return 或写 return None）。

### single_choice · None



- [A] def __init__(self, name):
- [B] def __init__(self, name=None):
- [C] def __init__(self, name=):
- [D] def __init__(self, =name):

**参考答案**：1

**解析**：给参数设置默认值 name=None 后，调用时可以不传。其他写法要么没有默认值，要么是语法错误。注意可变默认值（如 name=[]）通常是反模式，但 None 作为默认值是安全的。

### single_choice · None



- [A] 输出 []
- [B] 输出 ['x']
- [C] 抛出 TypeError
- [D] 输出 None

**参考答案**：1

**解析**：默认参数 items=[] 在函数定义时只创建一次并被所有调用共享。b1 向其 append 后，b2 拿到的是同一个列表，因此打印 ['x']。正确做法是以 None 为默认值，在函数体内新建列表。

### single_choice · None



- [A] self.x = 1 创建实例属性，各实例互不影响
- [B] self.x = 1 修改的是类属性
- [C] 类属性一旦定义就不能被访问
- [D] 实例属性和类属性完全等价

**参考答案**：0

**解析**：self.x = 值 会在该实例上创建或覆盖实例属性，实例之间彼此独立。类属性定义在类体中，所有实例共享。两者不等价，类属性可被访问，也可被实例属性遮蔽。
