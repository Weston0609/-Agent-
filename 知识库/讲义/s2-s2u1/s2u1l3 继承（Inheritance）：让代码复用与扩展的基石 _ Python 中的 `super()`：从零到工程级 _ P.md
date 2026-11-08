# s2u1l3 继承（Inheritance）：让代码复用与扩展的基石 / Python 中的 `super()`：从零到工程级 / Python MRO（方法解析顺序）：从直觉到工程

> 来源 `content/lessons/s2u1l3.json`

## py.oop.inherit

# 继承（Inheritance）：让代码复用与扩展的基石

> **一句话直觉**：继承让你把“已经写好的类”当作地基，在上面盖新楼，而不是每次从零挖土。

---

## 1. 为什么需要继承？——从“复制粘贴”说起

假设你要写一个程序管理动物园的动物。没有继承时，你可能会这样写：

```python
class Dog:
    def __init__(self, name):
        self.name = name

    def eat(self):
        print(f"{self.name} 正在吃东西")

    def speak(self):
        print(f"{self.name} 汪汪叫")


class Cat:
    def __init__(self, name):
        self.name = name

    def eat(self):
        print(f"{self.name} 正在吃东西")

    def speak(self):
        print(f"{self.name} 喵喵叫")
```

`eat` 方法在两个类里一模一样，这就是重复代码。继承的核心思想是：**把共同的部分抽到一个“父类”（parent class / base class）里，让“子类”（child class / derived class）去复用并定制**。

---

## 2. 第一个继承示例：语法与 `super()`

```python
class Animal:
    """所有动物的共同父类"""
    def __init__(self, name):
        self.name = name

    def eat(self):
        print(f"{self.name} 正在吃东西")


class Dog(Animal):          # Dog 继承 Animal
    def speak(self):
        print(f"{self.name} 汪汪叫")


class Cat(Animal):          # Cat 继承 Animal
    def speak(self):
        print(f"{self.name} 喵喵叫")


d = Dog("旺财")
d.eat()      # 继承自 Animal
d.speak()    # Dog 自己定义

c = Cat("咪咪")
c.eat()
c.speak()
```

**关键点**：
- `class Dog(Animal):` 表示 `Dog` 继承 `Animal`。
- `Dog` 自动拥有 `Animal` 的 `__init__` 和 `eat`。
- 如果子类要扩展父类的 `__init__`，应使用 `super().__init__(...)`，而不是手动调用 `Animal.__init__(self, ...)`。

```python
class GuideDog(Animal):
    def __init__(self, name, owner):
        super().__init__(name)   # 调用父类构造器
        self.owner = owner

    def guide(self):
        print(f"{self.name} 正在为 {self.owner} 导盲")


g = GuideDog("小黑", "张三")
g.eat()
g.guide()
```

---

## 3. 方法重写（Override）与多态（Polymorphism）

子类可以“覆盖”父类的方法，给出自己的实现：

```python
class Animal:
    def __init__(self, name):
        self.name = name

    def speak(self):
        print(f"{self.name} 发出某种声音")


class Dog(Animal):
    def speak(self):
        print(f"{self.name} 汪汪叫")


class Cat(Animal):
    def speak(self):
        print(f"{self.name} 喵喵叫")


# 多态：同一个函数，接受不同子类对象，产生不同行为
def make_it_speak(animal: Animal):
    animal.speak()


make_it_speak(Dog("旺财"))
make_it_speak(Cat("咪咪"))
```

**多态** 的含义是：调用方只关心“这是一个 Animal”，不关心具体是 Dog 还是 Cat；具体行为由运行时对象的真实类型决定。

---

## 4. `isinstance`、`issubclass` 与继承链

继承关系可以用两个内置函数检查：

```python
class Animal: pass
class Dog(Animal): pass

print(issubclass(Dog, Animal))   # True，Dog 是 Animal 的子类
print(isinstance(Dog(), Animal)) # True，Dog 实例也是 Animal 的实例
print(isinstance(Dog(), Dog))    # True
```

**常见误区**：不要用 `type(obj) is Animal` 判断类型，因为它不考虑继承。

```python
class Animal: pass
class Dog(Animal): pass

d = Dog()
print(type(d) is Animal)        # False：type 精确匹配，不认继承
print(isinstance(d, Animal))    # True：isinstance 认继承
```

所以工程规范推荐：**类型判断用 `isinstance()`，不要直接比较 `type()`**。

---

## 5. 多重继承与 MRO（Method Resolution Order）

Python 允许一个类继承多个父类：

```python
class A:
    def hello(self):
        print("A.hello")


class B(A):
    def hello(self):
        print("B.hello")


class C(A):
    def hello(self):
        print("C.hello")


class D(B, C):
    pass


d = D()
d.hello()          # 输出 B.hello
print(D.__mro__)   # 查看方法解析顺序
```

**MRO（方法解析顺序）** 决定了当多个父类都有同名方法时，Python 按什么顺序查找。规则简单说就是：**从左到右，深度优先，但子类优先于父类**。可以用 `类名.__mro__` 或 `类名.mro()` 查看。

**工程建议**：多重继承很强大，但也容易让代码难以理解。常见用法是“混入”（Mixin）——一个只提供额外方法的轻量父类。

```python
class JsonMixin:
    def to_json(self):
        import json
        return json.dumps(self.__dict__)


class User(JsonMixin):
    def __init__(self, name, age):
        self.name = name
        self.age = age


u = User("Alice", 30)
print(u.to_json())   # {"name": "Alice", "age": 30}
```

---

## 6. 继承 vs 组合：什么时候不该用继承？

继承表达的是 **“is-a”** 关系：狗是动物。
组合表达的是 **“has-a”** 关系：汽车有引擎。

如果两个类只是“用到了对方的功能”，优先用组合：

```python
# 不推荐：为了复用功能而继承
class Engine:
    def start(self):
        print("引擎启动")


class Car(Engine):   # 汽车“是”引擎？逻辑不通
    pass


# 推荐：组合
class Car:
    def __init__(self):
        self.engine = Engine()

    def start(self):
        self.engine.start()
        print("汽车启动")


Car().start()
```

**判断原则**：
- 子类确实是父类的一种 → 用继承。
- 子类只是需要父类的某些能力 → 用组合或 Mixin。

---

## 7. 小结

| 概念 | 作用 |
|------|------|
| 继承 | 子类复用父类的属性和方法 |
| `super()` | 调用父类方法，常用于 `__init__` |
| 方法重写 | 子类提供自己的实现 |
| 多态 | 同一接口，不同对象有不同行为 |
| `isinstance` | 判断对象是否属于某类（含继承） |
| MRO | 多重继承时的方法查找顺序 |
| 组合 | “has-a”关系，通常比继承更灵活 |

继承是面向对象编程的入口。掌握它之后，你就能读懂绝大多数 Python 库的类结构，也能设计出可扩展的代码。

---

## 动手练习

**任务：设计一个“员工管理系统”的类层次**

1. 创建父类 `Employee`，包含属性 `name`、`salary`，方法 `work()` 打印“{name} 正在工作”，方法 `get_salary()` 返回薪水。
2. 创建子类 `Manager`，额外属性 `team_size`，重写 `work()` 打印“{name} 正在管理 {team_size} 人的团队”。
3. 创建子类 `Developer`，额外属性 `language`，重写 `work()` 打印“{name} 正在用 {language} 写代码”。
4. 创建一个列表，放入 `Manager` 和 `Developer` 实例，遍历调用 `work()` 和 `get_salary()`，观察多态效果。
5. 用 `isinstance` 判断每个对象是否都是 `Employee` 的实例。

**提示**：
- 子类的 `__init__` 里用 `super().__init__(name, salary)`。
- 运行后打印 `Manager.__mro__` 看看继承链。

```python
class Animal:
    """所有动物的共同父类"""
    def __init__(self, name):
        self.name = name

    def eat(self):
        print(f"{self.name} 正在吃东西")

    def speak(self):
        print(f"{self.name} 发出某种声音")


class Dog(Animal):
    """狗：继承 Animal，重写 speak"""
    def speak(self):
        print(f"{self.name} 汪汪叫")


class Cat(Animal):
    """猫：继承 Animal，重写 speak"""
    def speak(self):
        print(f"{self.name} 喵喵叫")


class GuideDog(Animal):
    """导盲犬：扩展 __init__，新增 guide 方法"""
    def __init__(self, name, owner):
        super().__init__(name)   # 调用父类构造器
        self.owner = owner

    def guide(self):
        print(f"{self.name} 正在为 {self.owner} 导盲")


def make_it_speak(animal: Animal):
    """多态：接收任意 Animal 子类实例"""
    animal.speak()


# --- 演示 ---
d = Dog("旺财")
c = Cat("咪咪")
g = GuideDog("小黑", "张三")

d.eat()        # 继承自 Animal
d.speak()      # Dog 自己的实现

c.eat()
c.speak()

g.eat()        # 继承自 Animal
g.guide()      # GuideDog 新增方法

# 多态：同一个函数，不同行为
make_it_speak(d)
make_it_speak(c)

# 类型检查
print(isinstance(d, Animal))      # True
print(issubclass(Dog, Animal))    # True

# 查看 MRO
print(Dog.__mro__)
```

## py.oop.super

# Python 中的 `super()`：从零到工程级

## 一句话直觉

**`super()` 让你在子类里“借用”父类已经写好的代码，而不用复制粘贴或写死父类名字——它是多重继承（multiple inheritance）与方法解析顺序（MRO, Method Resolution Order）的入口。**

只要你想在子类中“先做父类的事，再做自己的事”，或者处理菱形继承（diamond inheritance），`super()` 就是那把钥匙。

---

## 1. 为什么需要 `super()`？

先看不使用 `super()` 的写法：

```python
class Animal:
    def __init__(self, name):
        self.name = name
        print(f"Animal.init({name})")

class Dog(Animal):
    def __init__(self, name, breed):
        Animal.__init__(self, name)   # 直接写父类名
        self.breed = breed
        print(f"Dog.init({name}, {breed})")
```

这能跑，但有三个问题：

1. **硬编码父类名**：如果 `Dog` 的父类从 `Animal` 改成 `Pet`，你必须改一行行调用。
2. **不兼容多重继承**：`Animal.__init__` 不会继续向上调用，菱形继承时会断链。
3. **不符合协作式继承（cooperative inheritance）惯例**。

`super()` 就是官方推荐的解决方式。

---

## 2. `super()` 到底是什么？

`super()` 返回一个**代理对象（proxy object）**，它不是“父类对象”，而是“**按 MRO 顺序排在当前类之后的下一个类**”的代理。

理解这句话是核心：**`super()` 不是“父类”，而是“MRO 中的下一个”。**

```python
class A:
    def hello(self):
        print("A.hello")

class B(A):
    def hello(self):
        super().hello()   # 等价于 A.hello(self)
        print("B.hello")

B().hello()
# 输出:
# A.hello
# B.hello
```

Python 3 里 `super()` 不带参数也能工作，因为编译器会通过 `__class__` 闭包（closure）自动传入当前类与 `self`。

---

## 3. MRO：`super()` 的导航地图

每个类都有一张 MRO 表，由 C3 线性化算法（C3 linearization）生成。可以用 `Class.__mro__` 或 `Class.mro()` 查看。

```python
class A: pass
class B(A): pass
class C(A): pass
class D(B, C): pass

for cls in D.__mro__:
    print(cls.__name__)
# D
# B
# C
# A
# object
```

在 `B` 的方法里调用 `super()`，下一个是 `C`，**不是 `A`**！这就是“MRO 中下一个”的真正含义。

---

## 4. 协作式多重继承：为什么要一直向上调

下面演示标准的**协作式初始化模式**：每个 `__init__` 都调用 `super().__init__(...)`，参数一路透传。

```python
class Base:
    def __init__(self, **kwargs):
        print(f"Base got {kwargs}")
        super().__init__()   # 最终到 object

class A(Base):
    def __init__(self, a, **kwargs):
        self.a = a
        print(f"A: a={a}")
        super().__init__(**kwargs)

class B(Base):
    def __init__(self, b, **kwargs):
        self.b = b
        print(f"B: b={b}")
        super().__init__(**kwargs)

class C(A, B):
    def __init__(self, a, b):
        super().__init__(a=a, b=b)

c = C(a=1, b=2)
print(c.a, c.b)
```

输出顺序由 MRO 决定（`C -> A -> B -> Base -> object`），每个 `__init__` 负责自己那部分，参数用 `**kwargs` 一路收集与透传。这是 Django、PyTorch `nn.Module` 等大型框架的子类化基础。

---

## 5. 工程级要点速查

- **`super()` 不带参数**（Python 3）优先使用；只有在类体外部（如动态生成方法）才需要 `super(CurrentClass, self)`。
- **`__init_subclass__`、`__set_name__`** 等机制也与 `super()` 协作，共同构成类生命周期钩子。
- **不要在 `__init__` 里只调 `super().__init__()` 而不传参**——多层协作时容易丢参数。
- **`super()` 只能用于新式类（new-style class）**，Python 3 所有类都是新式类，这点已无历史负担。
- **`super()` 不能用于 `NamedTuple` 子类的方法中**（Python 3.14 起会直接抛 `TypeError`），因为 `NamedTuple` 生成的类不支持 `__class__` 闭包机制。

---

## 结尾：动手练习

在本地新建 `shape.py`，实现一个形状层级：

1. 定义 `Shape`，`__init__(self, name)`，保存 `self.name`，并打印 `Shape({name})`。
2. 定义 `Colored`，`__init__(self, color)`，保存 `self.color`，并打印 `Colored({color})`。
3. 定义 `Square(Shape, Colored)`，`__init__(self, name, color, side)`，保存 `self.side`，并通过 `super().__init__(name=name, color=color)` 走协作式初始化。
4. 打印 `Square.__mro__`，并创建 `s = Square("sq", "red", 3)`。
5. 观察输出顺序与 `s.name / s.color / s.side`，解释为什么 `Shape` 和 `Colored` 都会打印。

**加分**：给三个类各写一个 `describe(self)`，都用 `super().describe()` 串起来，返回一段描述字符串，验证 MRO 顺序。

```python
class Base:
    def __init__(self, **kwargs):
        print(f"Base got {kwargs}")
        super().__init__()  # 最终到达 object

class A(Base):
    def __init__(self, a, **kwargs):
        self.a = a
        print(f"A: a={a}")
        super().__init__(**kwargs)

class B(Base):
    def __init__(self, b, **kwargs):
        self.b = b
        print(f"B: b={b}")
        super().__init__(**kwargs)

class C(A, B):
    def __init__(self, a, b):
        super().__init__(a=a, b=b)

c = C(a=1, b=2)
print("MRO:", [cls.__name__ for cls in C.__mro__])
print("c.a =", c.a, "| c.b =", c.b)
# 输出:
# A: a=1
# B: b=2
# Base got {}
# MRO: ['C', 'A', 'B', 'Base', 'object']
# c.a = 1 | c.b = 2
```

## py.oop.mro

# Python MRO（方法解析顺序）：从直觉到工程

## 一句话直觉

当一个对象调用方法时，Python 需要沿着一条确定的“查找路线”在继承树里找到该方法——这条路线就是 **MRO（Method Resolution Order，方法解析顺序）**。不懂 MRO，多继承就会变成“玄学”；懂了 MRO，你就能精确预测和设计类的行为。

---

## 1. 什么是 MRO？为什么需要它？

Python 支持 **多继承（multiple inheritance）**：一个类可以同时继承多个父类。当多个父类都定义了同名方法时，Python 必须有一套规则决定“先用谁的”。这套规则就是 MRO。

Python 3 采用 **C3 线性化算法（C3 linearization）** 生成 MRO，保证：

1. **子类优先于父类**；
2. **多个父类按声明顺序优先**；
3. **单调性**：不会出现“父类排在子类前面”的矛盾。

每个类都有一个 `__mro__` 属性，它是一个元组，记录方法查找顺序。

```python
class A:
    def who(self):
        return "A"

class B(A):
    def who(self):
        return "B"

class C(A):
    def who(self):
        return "C"

class D(B, C):
    pass

print(D.__mro__)
print(D().who())
```

输出：

```
(<class '__main__.D'>, <class '__main__.B'>, <class '__main__.C'>, <class '__main__.A'>, <class 'object'>)
B
```

直觉：`D` 自己没有 `who`，按 MRO 先找 `B`，命中，返回 `B`。

---

## 2. C3 算法：MRO 是怎么算出来的？

C3 的合并规则可以简化为：

- 对类 `C(B1, B2, ..., Bn)`，取 `L[C] = C + merge(L[B1], L[B2], ..., L[Bn], [B1, B2, ..., Bn])`；
- `merge` 每次从列表头部取一个“不出现在其他列表尾部”的候选，加入结果，否则跳到下一个列表。

对上面的例子：

```
L[A] = [A, object]
L[B] = [B, A, object]
L[C] = [C, A, object]
L[D] = D + merge([B,A,object], [C,A,object], [B,C])
     = [D, B, C, A, object]
```

验证：

```python
print([c.__name__ for c in D.__mro__])
# ['D', 'B', 'C', 'A', 'object']
```

注意：**`object` 永远是 MRO 的最后一个**，因为所有类最终都继承自它。

---

## 3. super()：沿 MRO 前进，而不是“调用父类”

`super()` 的常见误解是“调用父类方法”。更准确的说法是：**从当前类在 MRO 中的下一个位置继续查找**。

```python
class A:
    def greet(self):
        return "A"

class B(A):
    def greet(self):
        return "B -> " + super().greet()

class C(A):
    def greet(self):
        return "C -> " + super().greet()

class D(B, C):
    def greet(self):
        return "D -> " + super().greet()

print(D().greet())
# D -> B -> C -> A
```

关键点：`B.greet` 里的 `super()` 并不是跳到 `A`，而是跳到 `D.__mro__` 中 `B` 的**下一个**：`C`。这就是 **协作式多继承（cooperative multiple inheritance）** 的基础。

---

## 4. 经典陷阱：菱形继承与“不一致的 MRO”

菱形继承（diamond inheritance）是最常见的多继承形态：`D(B, C)`，而 `B` 和 `C` 都继承 `A`。C3 能优雅地处理它。

但如果继承顺序本身矛盾，Python 会在定义类时直接报 `TypeError`：

```python
class A: pass
class B(A): pass

# 下面这行会报错：无法为 X 创建一致的 MRO
# class X(A, B): pass
```

原因：`A` 是 `B` 的父类，却想排在 `B` 前面，违反“子类优先”的单调性。

工程建议：

- 多继承尽量用于 **Mixin（混入类）**：只提供小功能，不持有状态；
- 所有 `__init__` 都用 `super().__init__(**kwargs)` 协作传递；
- 用 `ClassName.__mro__` 或 `help(ClassName)` 排查顺序。

---

## 5. 工程级用法：Mixin 与协作式初始化

```python
class LogMixin:
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        print(f"[log] {type(self).__name__} created")

class TimestampMixin:
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.created = "2025-01-01"

class Base:
    def __init__(self, name, **kwargs):
        super().__init__(**kwargs)
        self.name = name

class Service(LogMixin, TimestampMixin, Base):
    pass

s = Service(name="api")
print(s.name, s.created)
print([c.__name__ for c in Service.__mro__])
```

输出：

```
[log] Service created
api 2025-01-01
['Service', 'LogMixin', 'TimestampMixin', 'Base', 'object']
```

每个 `__init__` 都调用 `super().__init__(**kwargs)`，于是所有父类都会被按 MRO 顺序调用一次。

---

## 动手练习

完成下面的小任务，巩固 MRO：

1. 定义类 `A`、`B(A)`、`C(A)`、`D(B, C)`、`E(C, B)`。
2. 分别打印 `D.__mro__` 和 `E.__mro__` 的类名列表，观察 `B`、`C` 的顺序差异。
3. 在 `A`、`B`、`C` 中各定义一个 `tag()` 方法，返回包含类名的字符串；在 `D` 中调用 `tag()`，预测并验证输出。
4. 尝试定义 `class F(A, B): pass`，解释为什么 Python 会报 `TypeError`。

提交形式：一段可运行的 `.py` 文件 + 你对 `D.__mro__` 和 `E.__mro__` 差异的一句话解释。

```python
class A:
    def who(self):
        return "A"

class B(A):
    def who(self):
        return "B -> " + super().who()

class C(A):
    def who(self):
        return "C -> " + super().who()

class D(B, C):
    def who(self):
        return "D -> " + super().who()

# 打印 MRO
print([c.__name__ for c in D.__mro__])
# 输出: ['D', 'B', 'C', 'A', 'object']

# super() 沿 MRO 前进：D -> B -> C -> A
print(D().who())
# 输出: D -> B -> C -> A

# 协作式初始化
class LogMixin:
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        print(f"[log] {type(self).__name__} created")

class TimestampMixin:
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.created = "2025-01-01"

class Base:
    def __init__(self, name, **kwargs):
        super().__init__(**kwargs)
        self.name = name

class Service(LogMixin, TimestampMixin, Base):
    pass

s = Service(name="api")
print(s.name, s.created)
# 输出:
# [log] Service created
# api 2025-01-01
```


---

## 本课题目

### single_choice · None



- [A] A
- [B] B
- [C] 报错：B 没有 show
- [D] 输出为空

**参考答案**：0

**解析**：B 继承自 A，未定义自己的 show，因此沿 MRO 找到 A.show，输出 A。

### single_choice · None



- [A] A.f
- [B] B.f
- [C] 先 A.f 再 B.f
- [D] 报错

**参考答案**：1

**解析**：子类重写 f，调用时优先使用子类的定义。

### single_choice · None



- [A] A A
- [B] A C
- [C] B C
- [D] 报错

**参考答案**：0

**解析**：B 和 C 都未重写 f，都继承 A.f。

### single_choice · None



- [A] MRO 保证每个类只出现一次，并遵循子类在前父类在后
- [B] MRO 按类定义顺序任意排列
- [C] Python 不支持多重继承
- [D] MRO 只对单继承有意义

**参考答案**：0

**解析**：C3 线性化算法保证单调性与局部优先顺序。

### single_choice · None



- [A] A B
- [B] A A
- [C] B B
- [D] 报错：缺少 x

**参考答案**：0

**解析**：super().__init__() 设置了 x，随后 B 设置 y。

### single_choice · None



- [A] A
- [B] B
- [C] C
- [D] 报错

**参考答案**：1

**解析**：C 未定义 f，沿 MRO 找到 B.f。

### single_choice · None



- [A] 子类实例访问父类定义的方法
- [B] 父类实例访问子类新增的方法
- [C] 子类实例访问子类自己定义的方法
- [D] 通过 super() 调用父类方法

**参考答案**：1

**解析**：父类实例不知道子类扩展的方法。

### single_choice · None



- [A] A
- [B] B
- [C] BC
- [D] CB

**参考答案**：2

**解析**：C.f 调用 super().f() 得到 B，再拼接 'C'。

### single_choice · None



- [A] A
- [B] B
- [C] 报错
- [D] 无输出

**参考答案**：0

**解析**：删除后 B 继承 A.f，输出 A。

### single_choice · None



- [A] 实例属性优先于类属性，子类优先于父类
- [B] 类属性优先于实例属性
- [C] 父类属性优先于子类属性
- [D] 查找顺序与继承无关

**参考答案**：0

**解析**：属性查找先实例后类，类中沿 MRO 从子到父。

### single_choice · None



- [A] 1 2
- [B] 1 1
- [C] 2 1
- [D] 报错

**参考答案**：0

**解析**：B 通过 super 把 v 传给 A 初始化，然后设置 extra。

### single_choice · None



- [A] B 继承了 A 的 greet 方法
- [B] B 自动复制了 A 的方法
- [C] Python 会自动为 B 生成 greet 方法
- [D] B 与 A 是同一个类

**参考答案**：0

**解析**：继承使子类可以直接使用父类方法，无需复制。

### single_choice · None



- [A] B.f
- [B] A.f
- [C] object.f
- [D] 无输出

**参考答案**：1

**解析**：super() 按 MRO 查找下一个类的方法，这里找到 A.f。

### single_choice · None



- [A] 1
- [B] 0
- [C] 报错
- [D] None

**参考答案**：0

**解析**：B 继承 A 的类属性 x。

### single_choice · None



- [A] True True
- [B] True False
- [C] False True
- [D] False False

**参考答案**：2

**解析**：B 重写了 __init__ 且未调用 super().__init__，因此 x 没有被设置。

### single_choice · None



- [A] 在 B.__init__ 中先 super().__init__() 再设置自己的属性
- [B] 省略 B 的 __init__，Python 会自动合并 A 的初始化
- [C] 在 B.__init__ 中直接写 self.__init__()
- [D] 在类体里写 A.__init__(self)

**参考答案**：0

**解析**：super().__init__() 按 MRO 调用父类初始化；直接 A.__init__(self) 虽可运行但绕过 MRO，通常不推荐。

### single_choice · None



- [A] isinstance(b, A) 对子类实例返回 True
- [B] isinstance(a, B) 对父类实例返回 True
- [C] isinstance 只比较 type 是否完全相同
- [D] isinstance 不能用于继承层次

**参考答案**：0

**解析**：isinstance 会沿继承链判断，子类实例也是父类实例。

### single_choice · None



- [A] True True
- [B] True False
- [C] False True
- [D] False False

**参考答案**：1

**解析**：B 是 A 的子类，A 不是 B 的子类。

### single_choice · None



- [A] B, A, object
- [B] A, B, object
- [C] B, object, A
- [D] A, object, B

**参考答案**：0

**解析**：MRO 从类本身开始，再到父类，最后 object。

### single_choice · None



- [A] A
- [B] B
- [C] BA
- [D] AB

**参考答案**：2

**解析**：B.f 先返回 'B'，再拼接 super().f() 的结果 'A'。

### single_choice · None



- [A] 10 20
- [B] 20 20
- [C] 10 10
- [D] 20 10

**参考答案**：0

**解析**：给 B.value 赋值只影响 B 自己的命名空间，不修改 A.value。

### single_choice · None



- [A] super() 返回的是当前类的父类对象，因此只能用于单继承
- [B] super() 返回一个代理对象，按 MRO 顺序调用下一个类的方法，可用于单继承和多继承
- [C] super() 只能用在 __init__ 方法中，其他地方使用会报错
- [D] super() 会直接实例化父类并返回父类实例

**参考答案**：1

**解析**：super() 返回的是一个代理对象，它按照类的方法解析顺序（MRO）查找下一个类的方法，而不是简单地指向父类，因此在多继承和菱形继承中都有效，也不限于 __init__。

### single_choice · None



- [A] 'BA'
- [B] 'AB'
- [C] 'B'
- [D] 报错 AttributeError

**参考答案**：0

**解析**：B().greet() 返回 'B' + super().greet()，super() 按 MRO 找到 A.greet，返回 'A'，因此结果是 'BA'。

### fill_blank · None



**参考答案**：["super", "super()", "super()"]

**解析**：super() 是 Python 内置函数，返回按 MRO 查找下一个类的代理对象，是协作式多继承中调用父类方法的标准方式。

### fill_blank · None



**参考答案**：["super().__init__()", "super(B, self).__init__()"]

**解析**：在子类 __init__ 中应调用 super().__init__() 以初始化父类，写入 tag 属性，然后再设置自身的 extra 属性。

### fill_blank · None



**参考答案**：["MRO", "mro"]

**解析**：MRO 即 Method Resolution Order（方法解析顺序），由 C3 线性化算法生成，super() 正是沿着 MRO 向后查找下一个类。

### code_reading · None



**参考答案**：C->B->A

**解析**：C().f() 返回 'C->' + super().f()，super() 按 MRO 找到 B.f，返回 'B->' + super().f()，再找到 A.f 返回 'A'，拼接后为 'C->B->A'。

### scenario · None



**解析**：排查时查看类.__mro__ 确认顺序，检查是否有类直接写父类名调用而不是用 super()。修复方式是让所有相关类统一用 super() 沿 MRO 传递调用，保持方法签名兼容，从而保证每个祖先方法只执行一次。

### scenario · None



**解析**：直接写 BaseClass.__init__ 会跳过 MRO 中位于该类之后的其他类，且当多条继承路径都指向同一祖先时会重复执行。正确做法是使用 super().__init__(...) 沿 MRO 传递，确保祖先初始化只执行一次。

### scenario · None



**解析**：零参数 super() 依赖编译器在类体内方法中注入的 __class__ 单元，类外函数没有该单元。可改为在类体内的方法中调用，或使用显式形式 super(当前类, 实例) 手动指定起点。

### single_choice · None



- [A] 总是从实例所属类的直接父类开始查找
- [B] 从当前方法定义所在类在 MRO 中的下一个类开始查找
- [C] 总是从 object 开始查找，然后反向遍历 MRO
- [D] 从第一个继承了目标方法的类开始查找，与定义位置无关

**参考答案**：1

**解析**：super() 的起点是方法定义所在类在 MRO 中的下一个类，而非实例的直接父类，这正是在菱形继承中行为正确的关键。

### single_choice · None



- [A] 总是从 object 开始查找
- [B] 根据调用栈动态推断，可能出错
- [C] 根据当前方法定义所在的类以及实例的 __class__ 确定 MRO 起点
- [D] 总是从当前实例的直接父类开始，与定义位置无关

**参考答案**：2

**解析**：Python 3 中零参数 super() 依赖编译器注入的 __class__ 单元（cell），它指向方法定义所在的类，再结合 self 的实例类型计算 MRO，从定义类的下一个类开始查找。

### single_choice · None



- [A] ['B', 'C', 'A']
- [B] ['B', 'A', 'C', 'A']
- [C] ['B', 'A']
- [D] ['B', 'C', 'A', 'A']

**参考答案**：0

**解析**：D 的 MRO 是 D→B→C→A→object。B.f 调用 super().f() 按 MRO 找到 C.f，C.f 再调用 super().f() 找到 A.f。因此结果是 ['B','C','A']，A 只被调用一次。

### single_choice · None



- [A] super() 的查找起点由当前类在 MRO 中的位置决定
- [B] 使用 super() 可以保证协作式多继承中每个方法只被调用一次
- [C] super() 等价于直接写父类名调用父类方法，二者效果完全相同
- [D] MRO 由 C3 线性化算法生成，可以通过类名.__mro__ 查看

**参考答案**：2

**解析**：super() 按 MRO 调用下一个类，而直接写父类名会跳过 MRO 中位于父类之后的其他类，在多重继承中两者效果不同，因此说“完全相同”是错误的。

### single_choice · None



- [A] 单继承中 init 调用父类初始化
- [B] 菱形继承中希望父类初始化只执行一次
- [C] 没有任何继承关系的独立类
- [D] 只继承 object 的简单类

**参考答案**：1

**解析**：在菱形继承中若直接写父类名，同一个祖先类的初始化会被多次调用，而使用 super() 配合协作式设计能保证沿 MRO 每个初始化只执行一次。

### multi_choice · None



- [A] super() 可以出现在类外定义的函数中（前提是正确传入参数）
- [B] 零参数 super() 只能在类体内定义的方法中使用
- [C] super().__init__() 常用于子类初始化中调用父类初始化
- [D] super() 返回的对象本身不是类的实例，而是代理对象
- [E] super() 可以用于调用父类的类方法或静态方法

**参考答案**：[1, 2, 3, 4]

**解析**：零参数 super() 依赖编译器注入的 __class__，只能在类体内方法中使用；带参数的 super(类, 实例) 可以在类外使用，所以 A 表述过于绝对（它也可以，但选项 A 说“可以出现”其实正确，见解析）。super() 返回代理对象，可调用 __init__、类方法、静态方法。修正：所有选项表述的机制都成立，正确项为 B、C、D、E。

### multi_choice · None



- [A] 在模块级别的普通函数中调用 super()
- [B] 在类中定义的普通实例方法里调用 super()
- [C] 在类的静态方法（@staticmethod）中调用零参数 super()
- [D] 在类外部定义的、没有 __class__ 单元的函数中调用零参数 super()

**参考答案**：[0, 2, 3]

**解析**：零参数 super() 依赖编译器在类体内方法中注入的 __class__ 单元。模块级函数、静态方法、类外函数都没有这个单元，因此运行时会报 RuntimeError: super(): no arguments。

### multi_choice · None



- [A] 每个子类应通过 super() 继续沿 MRO 传递调用，而不是直接调用具体父类
- [B] 协作式设计要求所有相关方法的签名尽量兼容，避免参数不匹配
- [C] 如果不使用 super()，菱形继承中祖先方法可能被重复调用
- [D] super() 会自动去重，即使父类不协作也能保证只调用一次

**参考答案**：[0, 1, 2]

**解析**：协作式多继承要求每个类都通过 super() 把调用传递下去，且方法签名兼容；若某个类直接调用具体父类，就会破坏传递链，导致祖先方法重复执行。super() 并不会自动去重。

### multi_choice · None



- [A] Mid(1, 2).x 的值是 1
- [B] Mid(1, 2).y 的值是 2
- [C] super().__init__(x) 按照 MRO 调用 Base.__init__
- [D] Mid 的实例不会拥有 x 属性，因为 super() 不生效

**参考答案**：[0, 1, 2]

**解析**：super().__init__(x) 沿 MRO 调用 Base.__init__，将 x 写入实例；随后设置 y。因此实例同时拥有 x=1 和 y=2。

### single_choice · None



- [A] MRO 是类在定义时按继承列表中的书写顺序简单拼接而成的列表
- [B] MRO 是 Python 为每个类计算出的方法查找顺序，且满足子类先于父类、多个父类按声明顺序的线性化规则
- [C] MRO 只对单继承有意义，多继承时 Python 会随机选择一个父类的方法
- [D] MRO 是实例属性的查找顺序，与类方法无关

**参考答案**：1

**解析**：MRO 是 Python 为每个类计算的线性化顺序（C3 线性化），保证子类先于父类被查找，并且在多继承时尊重基类的声明顺序与一致性约束；它不是简单拼接，也不是随机选择，更不是实例属性的查找顺序。

### single_choice · None



- [A] A
- [B] B
- [C] C
- [D] 报错

**参考答案**：1

**解析**：D 的 MRO 为 [D, B, C, A, object]，方法查找按该顺序进行，最先找到 B.f，因此返回 'B'。这正是多继承中「左侧基类优先」的体现。

### multi_choice · None



- [A] super() 查找的是 MRO 中当前类之后的下一个类的方法
- [B] 在多个类都通过 super() 调用同名方法时，可以形成一条沿 MRO 的调用链
- [C] super() 只能用于单继承，多继承下会报错
- [D] super() 的查找起点由第一个参数（类）和实例共同决定

**参考答案**：[0, 1, 3]

**解析**：super() 依据实例所属类型（或其类）的 MRO 与指定的起始类来定位「下一个」方法，因此多继承下能形成沿 MRO 的调用链（如各 __init__ 都通过 super() 调用）。选项 C 错误：super() 恰恰是为多继承协作设计的。

### multi_choice · None



- [A] class A: pass
  class B(A): pass
  class C(A, B): pass
- [B] class A: pass
  class B: pass
  class C(A, B): pass
- [C] class A: pass
  class B(A): pass
  class C(B): pass
  class D(C, A): pass
- [D] class A: pass
  class B: pass
  class C(A, B): pass
  class D(B, A): pass

**参考答案**：[0, 3]

**解析**：选项 A：C(A, B) 与 B 继承 A 冲突（A 要求排在 B 前，而 B 自身又要求 A 在其后）。选项 D：D(B, A) 与 C(A, B) 冲突（B 与 A 的先后顺序矛盾）。选项 B、C 都能构造出合法 MRO。

### fill_blank · None



**参考答案**：["__mro__", "mro"]

**解析**：MyClass.__mro__ 返回表示方法解析顺序的元组；也可以调用 MyClass.mro() 得到列表。两者都反映 C3 线性化结果。

### fill_blank · None



**参考答案**：["B, C", "B,C", "(B, C)", "(B,C)"]

**解析**：C3 线性化下，D 先按声明顺序处理直接基类，B 在 C 之前、A 在两者之后，因此应写成 class D(B, C)，结果为 [D, B, C, A, object]。

### fill_blank · None



**参考答案**：["__mro__"]

**解析**：Python 为每个类提供 __mro__ 属性，值为元组，表示方法查找顺序。这是查看 MRO 最直接的方式之一。

### code_reading · None



**参考答案**：输出第一行是 DBCA；第二行是 ['D', 'B', 'C', 'A', 'object']。D 的 MRO 为 [D, B, C, A, object]，各 go 通过 super() 依次沿 MRO 调用，最终 A.go() 返回 'A'，故拼接结果为 'D'+'B'+'C'+'A' = 'DBCA'。

**解析**：D.go 用 super() 调用 MRO 中下一个类 B.go，B.go 再 super() 到 C.go，C.go 再 super() 到 A.go，从而形成协作式调用链。打印 MRO 名称列表即为 [D, B, C, A, object]。

### code_reading · None



**参考答案**：True

**解析**：Z.mro() 返回一个列表，Z.__mro__ 是一个元组，两者表示的顺序相同；将 __mro__ 转换为列表后与 mro() 相等，因此打印 True。

### code_reading · None



**参考答案**：运行到 class C(B, A) 时抛出 TypeError: Cannot create a consistent method resolution order (MRO) for bases A, B。因为 B 已经继承 A，A 必须排在 B 之后，但 C 的声明要求在 B 之前，约束矛盾，无法构造合法 MRO。

**解析**：Python 用 C3 线性化组合各基类的 MRO，若出现无法满足的先后约束就会报 TypeError。这题考查对 MRO 一致性约束的理解。

### scenario · None



**解析**：应让各层 render 都用 super().render(...) 而不是硬编码 BaseView.render，这样调用会沿 MRO（OrderView -> LoggedView -> ApiView -> BaseView）依次传递，把各父类的逻辑串起来。这正是协作式多继承的用法，super() 通过 MRO 定位下一个定义该方法的类。硬编码父类会破坏调用链，导致某个分支被跳过。

### scenario · None



**解析**：报错原因是 D 的声明把 A 排在 C 之前，但 C 继承 A 要求 C 在 A 之前，约束冲突，C3 线性化失败。可行的做法是去掉冗余的直接基类 A，写成 class D(B, C)，得到的 MRO 为 [D, B, C, A, object]。由于 B 和 C 都已包含 A，直接再列出 A 只会带来矛盾。

### single_choice · None



- [A] class A: pass
  class B(A): pass
- [B] class A: pass
  class B(A): pass
  class C(A): pass
  class D(B, C): pass
- [C] class A: pass
  class B(A): pass
  class C(B, A): pass
- [D] class A: pass
  class B: pass
  class C(A, B): pass

**参考答案**：2

**解析**：选项 C 中 B 已经继承 A，C(B, A) 会要求 A 既在 B 之后又直接在 B 之前出现，无法构造出一致的方法解析顺序（MRO），因此 Python 在定义 C 时报 TypeError: Cannot create a consistent method resolution order。

### scenario · None



**解析**：方法查找按 D 的 MRO 顺序进行，即 [D, B, C, A, object]，最先命中 B.to_dict 后就返回，不会自动调用 C。要让两者都执行，需在 B 和 C 的 to_dict 中使用 super().to_dict(...)（协作式调用），并让 D 不覆盖或覆盖时也调用 super()，使调用沿 MRO 链式传递，最终把 C 的逻辑也执行到。

### single_choice · None



- [A] A
- [B] B
- [C] C
- [D] AttributeError

**参考答案**：2

**解析**：C 自身定义了 f，方法查找从实例类型 C 开始，沿 MRO 最先命中 C.f，因此返回 'C'。子类自身的方法总在父类之前被找到。

### single_choice · None



- [A] A 的方法在 D 的 MRO 中会出现两次，因此会被调用两次
- [B] A 在 MRO 中只出现一次，且位于 B 和 C 之后
- [C] Python 禁止这种继承结构，会报错
- [D] A 会被自动提升到 MRO 的最前面

**参考答案**：1

**解析**：C3 线性化保证每个类在 MRO 中只出现一次。在菱形继承中 A 会排在 B 和 C 之后、object 之前，例如 D 的 MRO 为 [D, B, C, A, object]。这避免了重复调用和歧义，也不会被禁止。

### single_choice · None



- [A] 总是调用直接父类的方法
- [B] 根据当前实例所属类型的 MRO，调用排在当前类之后的下一个定义了该方法的方法
- [C] 调用继承列表中第一个父类的方法
- [D] 根据被调用方法的 self 参数的 class 属性确定

**参考答案**：1

**解析**：super() 依据实例所属类型的 MRO 以及当前类在 MRO 中的位置，去寻找「排在当前类之后的那个类」上的方法，而不是简单地调用直接父类。这使得协作式多继承能正确链式调用。

### single_choice · None



- [A] 列表 list
- [B] 元组 tuple
- [C] 字典 dict
- [D] 集合 set

**参考答案**：1

**解析**：每个类都有一个 __mro__ 属性，它是一个元组，元素按方法查找顺序排列。通过 SomeClass.__mro__ 可以查看，也可以用 SomeClass.mro() 得到列表。

### single_choice · None



- [A] [D, B, A, C, object]
- [B] [D, B, C, A, object]
- [C] [D, A, B, C, object]
- [D] [D, C, B, A, object]

**参考答案**：1

**解析**：C3 线性化的结果：D 在本类之后先处理继承列表里靠左的 B，B 继承 A，但 C 也需要在 A 之前出现，因此顺序为 D -> B -> C -> A -> object。

### multi_choice · None



- [A] 它定义了查找方法和属性时沿着类的继承结构遍历的顺序
- [B] 每个类的 MRO 中，子类一定排在其祖先类之前
- [C] MRO 的构造遵循 C3 线性化算法，保证单调性和一致性
- [D] 当多个直接父类的排列顺序无法满足所有约束时，Python 会抛出 TypeError
- [E] MRO 只影响类方法的查找，不影响实例属性的查找

**参考答案**：[0, 1, 2, 3]

**解析**：MRO 决定方法（以及通过类访问属性的）查找顺序，子类必须排在祖先之前，用 C3 线性化保证单调性，冲突时抛 TypeError。选项 E 错误：实例属性通常先查实例 __dict__，但类属性及方法都沿 MRO 查找，所以 MRO 也会影响属性的查找结果。

### multi_choice · None



- [A] 访问类的 __mro__ 属性
- [B] 调用类的 mro() 方法
- [C] 调用该类的实例的 mro() 方法
- [D] 使用内置函数 help() 查看类信息时一般也能看到 MRO

**参考答案**：[0, 1, 3]

**解析**：类有 __mro__ 属性和 mro() 方法；help() 通常会展示类的 MRO。选项 C 错误：mro() 是类方法风格的接口，通常通过类调用，而且即便通过实例访问它也返回类的 MRO，但题目问的是「做法」，实例调用并非标准写法。此处按标准做法判断。
