# s2u3l3 元类（Metaclass）：从「类也是对象」到「控制类的创建」 / Python 描述符（Descriptor）：从属性访问到框架级抽象

> 来源 `content/lessons/s2u3l3.json`

## py.meta.metaclass

# 元类（Metaclass）：从「类也是对象」到「控制类的创建」

> **一句话直觉**：在 Python 里，类本身也是对象，而元类就是「生产类的类」——它让你在类被创建的那一刻插手，改写类的名字、属性、方法，甚至决定这个类到底长什么样。

---

## 1. 先搞清楚：类也是对象

在多数语言里，类是「模板」，对象是「模板的实例」。但在 Python 中，`class` 关键字执行后，会创建一个**类对象**（class object）。既然它是对象，就一定有「谁创建了它」。创建普通对象的是类；创建类对象的，就是**元类（metaclass）**。

默认情况下，所有类都由 `type` 创建。`type` 既是「查看对象类型」的函数，也是**所有类的默认元类**。它有两种用法：

- `type(obj)`：返回对象的类型。
- `type(name, bases, dict)`：动态创建一个新类。

```python
# 普通类定义
class Dog:
    sound = "wang"

    def speak(self):
        return self.sound

# 完全等价的动态创建（底层就是 type 在做的事）
Dog2 = type("Dog2", (), {
    "sound": "wang",
    "speak": lambda self: self.sound,
})

print(type(Dog))        # <class 'type'>   -> Dog 是 type 的实例
print(type(Dog2))       # <class 'type'>
print(Dog2().speak())   # wang
```

**关键结论**：`type` 是所有类的默认元类；`class` 语句本质上是调用元类来构造一个类对象。

---

## 2. 类的创建流程：`__new__` 与 `__init__`

当你写 `class Foo: ...` 时，CPython 大致会做三件事：

1. 收集类的命名空间（name、bases、属性字典）。
2. 找到合适的元类（默认 `type`）。
3. 调用 `元类(name, bases, namespace)` 生成类对象。

元类本身也是一个类，它继承自 `type`。它的构造过程由两个方法控制：

- `__new__(mcls, name, bases, namespace)`：**真正创建类对象**，返回类。
- `__init__(cls, name, bases, namespace)`：**初始化已创建的类**，无返回值。

```python
class Meta(type):
    def __new__(mcls, name, bases, namespace):
        print(f"[__new__] 正在创建类: {name}")
        return super().__new__(mcls, name, bases, namespace)

    def __init__(cls, name, bases, namespace):
        print(f"[__init__] 正在初始化类: {name}")
        super().__init__(name, bases, namespace)

class Foo(metaclass=Meta):
    pass

# 输出顺序：
# [__new__] 正在创建类: Foo
# [__init__] 正在初始化类: Foo
```

**关键结论**：想在类创建前修改 `name/bases/namespace`，用 `__new__`；想在类已存在后补装饰属性，用 `__init__`。

---

## 3. 第一个真正有用的元类：自动登记子类

元类最常见的用途之一是**注册表模式（registry pattern）**：每当一个类被创建，就自动记录到注册表中，便于后续按名字查找、做插件系统或 ORM 映射。

```python
registry = {}

class RegisterMeta(type):
    def __new__(mcls, name, bases, namespace):
        cls = super().__new__(mcls, name, bases, namespace)
        # 只登记业务子类，跳过基类本身
        if bases:
            registry[name] = cls
        return cls

class Base(metaclass=RegisterMeta):
    pass

class UserModel(Base):
    pass

class OrderModel(Base):
    pass

print(registry)  # {'UserModel': <class 'UserModel'>, 'OrderModel': <class 'OrderModel'>}
```

**关键结论**：元类能把「重复性登记、校验、注入」这类逻辑从每个子类中抽出来，统一在类创建时执行。

---

## 4. 元类与 `__init_subclass__`、类装饰器的关系

在 Python 3.6+，很多「元类的活」可以用更轻量的 **`__init_subclass__`** 或**类装饰器（class decorator）**完成。选择顺序建议：

1. 只处理「每个子类创建时」的逻辑 → 用 `__init_subclass__`。
2. 只会临时改一下类 → 用类装饰器。
3. 需要同时控制多个类族、修改命名空间、影响 `isinstance` 行为、或与 `abc`/`typing` 等协作 → 才用元类。

```python
# 方案 A：__init_subclass__（更简单）
class BaseA:
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        print(f"子类 {cls.__name__} 被创建")

class A1(BaseA):
    pass

# 方案 B：类装饰器（最轻）
def tag(cls):
    cls.tagged = True
    return cls

@tag
class B1:
    pass

print(B1.tagged)  # True
```

**关键结论**：元类不是首选，而是「最后手段」。能用 `__init_subclass__` 或装饰器解决就别用元类。

---

## 5. 元类与 `abc.ABC`、`typing` 的协作（工程视角）

标准库 `abc` 就是通过元类实现抽象类的：`ABCMeta` 拦截子类创建，检查抽象方法是否被实现。`typing` 的 `@dataclass_transform` 也是给类型检查器（type checker）看的「元类/装饰器意图声明」。理解元类后，你才能看懂下面这类代码为什么合法：

```python
from abc import ABC, abstractmethod

class Repo(ABC):
    @abstractmethod
    def get(self, key): ...

class MemoryRepo(Repo):
    def get(self, key):
        return {"k": "v"}.get(key)

# Repo() 会报错；MemoryRepo() 正常
print(MemoryRepo().get("k"))  # v
```

**关键结论**：`ABCMeta` 是元类在标准库中最经典的落地。写框架、插件系统、ORM、DI 容器时，元类是你构建「类层面的切面」的入口。

```python
# 综合示例：用元类做一个「强制属性命名检查 + 自动注册」的迷你 ORM 骨架
registry = {}

class ModelMeta(type):
    def __new__(mcls, name, bases, namespace):
        # 1) 跳过基类 Model 本身的检查
        if bases:
            for field in namespace:
                if field.startswith("_") or field in ("__module__", "__qualname__"):
                    continue
                # 强制字段小写，避免脏命名
                if not field.islower():
                    raise TypeError(f"字段名必须小写: {name}.{field}")
        cls = super().__new__(mcls, name, bases, namespace)
        # 2) 自动注册业务子类
        if bases:
            registry[name] = cls
        return cls

class Model(metaclass=ModelMeta):
    """所有模型基类"""
    pass

class User(Model):
    id = 1
    name = "alice"

# 下面这行会抛 TypeError: 字段名必须小写: Bad.age
# class Bad(Model):
#     Age = 18

print("已注册模型:", list(registry.keys()))
print("User 的字段:", [k for k in User.__dict__ if k.islower() and not k.startswith("_")])
```

## py.meta.descriptor

# Python 描述符（Descriptor）：从属性访问到框架级抽象

> 一句话直觉：**描述符让你在「类属性」这一层挂上"拦截器"——别人读写 `obj.x` 时，实际执行的是你写的 `__get__/__set__/__delete__`，这是 Python 中 property、方法绑定、ORM 字段、Django Model、PyTorch Module 参数访问等一切"魔法属性"的底层机制。**

本讲从零基础讲到工程级，共 5 个小节：
1. 属性访问的默认规则（回顾对象模型）
2. 描述符协议：三个魔术方法
3. 数据描述符 vs 非数据描述符（优先级之争）
4. 实战：用描述符手写一个 `property` 和类型校验字段
5. 工程级应用：方法绑定、缓存、ORM 风格字段

---

## 1. 属性访问的默认规则

当你写 `obj.attr` 时，Python 默认做三件事：
1. 去 `type(obj).__mro__` 里找 `attr`；
2. 如果找到的是一个 **描述符对象**，就调用它的描述符协议；
3. 否则返回实例 `obj.__dict__['attr']`（如果存在）。

这解释了为什么 `p.name = 10` 覆盖不了 `property`——因为 `property` 是一个描述符，它抢在实例字典之前生效。

```python
# 演示：普通类属性 vs 实例属性
class Plain:
    x = 'class-level'

p = Plain()
p.x = 'instance-level'
print(p.x)              # instance-level（实例字典优先）
print(Plain.x)          # class-level
print(p.__dict__)       # {'x': 'instance-level'}
```

关键词中英对照：**属性（attribute）**、**类属性（class attribute）**、**实例属性（instance attribute）**、**方法解析顺序（MRO, Method Resolution Order）**。

---

## 2. 描述符协议：三剑客 `__get__/__set__/__delete__`

如果类 A 定义了以下任意方法，A 的实例就被称为**描述符（descriptor）**：

| 方法 | 触发时机 | 签名 |
|---|---|---|
| `__get__(self, obj, objtype=None)` | 读取属性 | `instance.attr` 或 `Class.attr` |
| `__set__(self, obj, value)` | 赋值属性 | `instance.attr = value` |
| `__delete__(self, obj)` | 删除属性 | `del instance.attr` |

```python
class Logged:
    \"\"\"最小的描述符：每次读写都打印日志\"\"\"
    def __init__(self, name):
        self.name = name

    def __get__(self, obj, objtype=None):
        if obj is None:              # 通过类访问：Class.attr
            return self
        print(f'[GET] {self.name}')
        return obj.__dict__.get(self.name)

    def __set__(self, obj, value):
        print(f'[SET] {self.name} = {value!r}')
        obj.__dict__[self.name] = value

    def __delete__(self, obj):
        print(f'[DEL] {self.name}')
        obj.__dict__.pop(self.name, None)

class User:
    name = Logged('name')

u = User()
u.name = 'alice'    # 触发 __set__
print(u.name)      # 触发 __get__

```

注意：通过类访问 `User.name` 时 `obj is None`，描述符必须自己决定返回什么（通常返回 `self`）。这是描述符的**约定俗成协议**，不是语言强制。

---

## 3. 数据描述符 vs 非数据描述符

- **数据描述符（data descriptor）**：同时定义了 `__get__` 和 `__set__`（或 `__delete__`）。
- **非数据描述符（non-data descriptor）**：只定义了 `__get__`。

**优先级规则（重要）**：
> 数据描述符 > 实例 `__dict__` > 非数据描述符

这就是为什么 `property`（数据描述符）能挡住实例字典的赋值，而**普通函数**（非数据描述符）可以被实例属性覆盖。

```python
class NonData:
    def __get__(self, obj, objtype=None):
        return 'from descriptor'

class C:
    x = NonData()

c = C()
print(c.x)          # from descriptor（实例字典为空）
c.__dict__['x'] = 'from instance'
print(c.x)          # from instance（非数据描述符被实例字典覆盖）
```

---

## 4. 手写 property：看穿内置机制

`property` 就是标准库提供的一个数据描述符。我们可以自己实现一个 `MyProperty` 来验证理解。

```python
class MyProperty:
    \"\"\"简化版 property：支持 getter/setter\"\"\"
    def __init__(self, fget=None, fset=None):
        self.fget = fget
        self.fset = fset

    def setter(self, fset):
        self.fset = fset
        return self

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        if self.fget is None:
            raise AttributeError('unreadable attribute')
        return self.fget(obj)

    def __set__(self, obj, value):
        if self.fset is None:
            raise AttributeError(\"can't set attribute\")
        self.fset(obj, value)

class Temperature:
    def __init__(self, celsius=0):
        self._celsius = celsius

    @MyProperty
    def celsius(self):
        return self._celsius

    @celsius.setter
    def celsius(self, v):
        if v < -273.15:
            raise ValueError('低于绝对零度')
        self._celsius = v

t = Temperature(25)
print(t.celsius)       # 25
t.celsius = 30
print(t.celsius)       # 30
```

---

## 5. 工程级应用：类型校验字段 + 方法绑定

### 5.1 类型校验描述符（ORM 风格）

```python
class Typed:
    \"\"\"带类型检查的描述符：类似 SQLAlchemy / Pydantic 字段\"\"
    def __init__(self, name, expected_type):
        self.name = name
        self.expected_type = expected_type

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return obj.__dict__.get(self.name)

    def __set__(self, obj, value):
        if not isinstance(value, self.expected_type):
            raise TypeError(f'{self.name} 必须是 {self.expected_type.__name__}')
        obj.__dict__[self.name] = value

class Person:
    name = Typed('name', str)
    age  = Typed('age', int)

    def __init__(self, name, age):
        self.name = name
        self.age = age

p = Person('Bob', 30)
print(p.name, p.age)
try:
    p.age = 'thirty'   # TypeError
except TypeError as e:
    print(e)
```

### 5.2 方法绑定也是描述符

函数对象实现了 `__get__`，因此 `obj.method` 会返回一个**绑定方法（bound method）**，把 `obj` 作为第一个参数塞进去。这就是为什么 Python 方法要写 `self`——它是描述符协议的产物，不是语法糖。

```python
class Greeter:
    def hi(self):
        return f'hi, I am {self}'

g = Greeter()
bound = g.hi           # 触发 function.__get__(g, Greeter)
print(bound)           # <bound method ...>
print(bound.__self__ is g)  # True
print(Greeter.hi)      # <function ...>（obj 为 None 时返回原函数）
```

---

## \u2705 动手练习

**任务**：实现一个 `@cached_property` 描述符，行为与 `functools.cached_property` 类似：

1. 第一次访问时执行被装饰的函数；
2. 把结果**写回实例 `__dict__`**，第二次访问直接从实例字典拿，不再调用函数；
3. 通过类访问 `Class.attr` 时返回描述符自身；
4. 用一段测试验证：调用计数 = 1，且第二次访问速度明显更快。

```python
import time

class cached_property:
    def __init__(self, func):
        self.func = func
        self.__doc__ = func.__doc__

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        # TODO: 执行 self.func(obj) 并写入 obj.__dict__[self.func.__name__]
        ...

class Heavy:
    @cached_property
    def result(self):
        time.sleep(0.5)
        return 42

h = Heavy()
t0 = time.time(); h.result; t1 = time.time(); h.result; t2 = time.time()
print(f'first={t1-t0:.3f}s, second={t2-t1:.6f}s')  # 第一次≈0.5s，第二次≈0
```

提示：`cached_property` 属于**非数据描述符**（只定义 `__get__`），所以一旦把值写入实例 `__dict__`，实例字典就会覆盖描述符——这是它工作快的根本原因。请体会并口述这条优先级规则。

```python
import time

class cached_property:
    """非数据描述符：只在 __get__ 中计算一次，然后写入实例 __dict__。"""
    def __init__(self, func):
        self.func = func
        self.__doc__ = func.__doc__
        self.name = func.__name__

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        # 第一次访问：调用函数并把结果写入实例字典
        value = self.func(obj)
        obj.__dict__[self.name] = value   # 写入后实例字典优先于非数据描述符
        return value


class Heavy:
    @cached_property
    def result(self):
        time.sleep(0.5)
        return 42


if __name__ == '__main__':
    h = Heavy()
    t0 = time.perf_counter()
    _ = h.result
    t1 = time.perf_counter()
    _ = h.result
    t2 = time.perf_counter()
    print(f'first={t1 - t0:.3f}s, second={t2 - t1:.6f}s')  # 0.500s vs ~0s
    print('cached in instance dict:', h.__dict__)          # {'result': 42}
```


---

## 本课题目

### single_choice · None



- [A] 所有类都由同一种默认机制创建，无法自定义
- [B] 类也是对象，其创建过程可由元类控制
- [C] 只有继承自 object 的类才由元类创建
- [D] 元类只能影响实例的属性，不能影响类的创建

**参考答案**：1

**解析**：在 Python 中类本身也是对象，默认由 type 创建；通过元类可以介入类的创建过程（如修改类命名空间、属性等）。A 错误，因为可通过 metaclass 自定义；C 错误，所有类创建都经过元类机制；D 错误，元类主要作用于类的创建阶段。

### single_choice · None



- [A] 先调用 Meta，再调用 type
- [B] 只调用 Meta，不调用 type
- [C] 只调用 object
- [D] 只调用 A 的 __init__ 方法

**参考答案**：0

**解析**：指定 metaclass=Meta 后，类 A 本身由 Meta 创建；Meta 若继承自 type，通常会在其 __new__/__init__ 中配合 type 完成实际创建。B 暗示不等同于简单地“只调用 Meta”而不涉及 type 机制，A 更准确描述过程。

### single_choice · None



- [A] meta
- [B] AttributeError
- [C] None
- [D] type

**参考答案**：0

**解析**：元类的 __init__ 在类创建后运行，这里给 cls 设置 tag='meta'，因此 A.tag 输出 meta。A 是正确项；B/C/D 与该设置不符。

### single_choice · None



- [A] 在类的每个方法中手动注册
- [B] 在元类的 __new__ 或 __init__ 中把新类加入注册表
- [C] 在模块导入时用 globals() 扫描
- [D] 在类的 __init__ 中注册

**参考答案**：1

**解析**：元类的 __new__/__init__ 在类创建时被调用，最适合做自动注册。A 繁琐且不自动；C 会漏掉动态创建的类；D 的 __init__ 是实例初始化，不是类创建。

### single_choice · None



- [A] 装饰器只能装饰函数，不能装饰类
- [B] 元类可以影响类创建，类装饰器也可以修改类，但作用时机略有不同
- [C] 元类与类装饰器完全等价，可以随意互换
- [D] 类装饰器在类创建之前执行，元类在之后执行

**参考答案**：1

**解析**：类装饰器在类对象创建之后作用于类，元类在类创建过程中介入。两者都可修改类，但时机不同，不等价。A 错误，装饰器也能装饰类；C 错误，不等价；D 把时机说反。

### single_choice · None



- [A] 只有 c
- [B] a 和 c
- [C] a、b、c
- [D] 只有 b

**参考答案**：2

**解析**：ns['a']=1 在创建前加入命名空间，c=3 来自类体，cls.b=2 在创建后设置，三者都成为 A 的属性。

### single_choice · None



- [A] 只能在运行时通过 instance.__dict__ 检测
- [B] 可以在元类 __new__ 中检查命名空间，若发现冲突抛出异常阻止类创建
- [C] 必须用元类的 __getattr__ 在访问时检测
- [D] 元类无法访问类的命名空间

**参考答案**：1

**解析**：元类 __new__ 会收到命名空间，可在类创建前检查冲突并抛异常，从而阻止类创建。A 时机太晚；C 检测时刻错；D 错误，元类能访问命名空间。

### single_choice · None



- [A] 抽象基类必须用元类实现，因为实例化检查只能在元类中完成
- [B] abc.ABCMeta 是一个元类，用于支持抽象基类机制
- [C] 抽象基类不能与自定义元类一起使用
- [D] 抽象方法的检查发生在实例 __init__ 中

**参考答案**：1

**解析**：abc.ABCMeta 是标准库提供的元类，负责抽象方法检查与注册等机制。A 太绝对；C 错误，自定义元类可继承 ABCMeta；D 错误，检查发生在实例化阶段而非 __init__ 内部。

### single_choice · None



- [A] 无输出
- [B] creating instance
- [C] 报错，因为元类不能定义 __call__
- [D] 输出 A

**参考答案**：1

**解析**：元类的 __call__ 控制类实例化过程，A() 会先调用 Meta.__call__，打印 creating instance，再通过 super().__call__ 创建实例。

### single_choice · None



- [A] 元类可以拦截类属性的读取，但不能拦截实例属性的读取
- [B] 元类既可以拦截类属性也能直接拦截实例属性的读取
- [C] 元类只能影响实例属性的读取
- [D] 元类无法影响属性访问

**参考答案**：0

**解析**：元类作用于类对象，因此可拦截类属性的读取；实例属性的读取由类上的 __getattribute__/__getattr__ 控制，而非元类直接拦截。B/C/D 均夸大了元类的能力。

### single_choice · None



- [A] 自动忽略 metaclass，使用父类的元类
- [B] 抛出 TypeError，无法创建该类
- [C] 自动把 metaclass 改为 type
- [D] 只影响实例化，不影响类创建

**参考答案**：1

**解析**：当指定元类与父类元类不满足子类关系时，Python 在创建类阶段抛出 TypeError。A/C 描述的是不存在的自动降级机制；D 错误，问题发生在类创建时。

### single_choice · None



- [A] 为每个实例保存不同数据
- [B] 在类定义阶段自动收集所有子类并做统一校验
- [C] 在实例方法中计算属性值
- [D] 在模块级别定义常量

**参考答案**：1

**解析**：元类介入类创建阶段，适合自动收集子类、统一校验等跨类行为。A 属于实例属性；C 属于普通方法；D 属于模块级定义，均不需要元类。

### single_choice · None



- [A] type 只能用来查询对象的类型，不能用来创建类
- [B] type 可以动态地创建类，例如 type('A', (), {})
- [C] type 是 object 的子类，因此可以创建 object
- [D] type 创建的类不能再有子类

**参考答案**：1

**解析**：type 既是函数又是元类，可以用 type(name, bases, namespace) 动态创建新类。A 错误，type 可以创建类；C 错误，object 是 type 的实例，type 不是 object 的子类；D 错误，type 创建的类同样可被继承。

### single_choice · None



- [A] 类不是对象，所以不存在类的类
- [B] 类也是对象，其类型就是元类；默认情况下类由 type 创建
- [C] 所有类的元类都必须是 object
- [D] 元类只能有一个实例

**参考答案**：1

**解析**：类本身是对象，它的类型是元类，默认是 type，因此“元类是类的类”成立。A 忽略类也是对象；C 错误，object 不是元类；D 错误，元类可以有多个实例（即多个类）。

### single_choice · None



- [A] AttributeError
- [B] 42
- [C] None
- [D] 0

**参考答案**：1

**解析**：元类 Meta 的 __new__ 在创建类 A 之前向命名空间 ns 中加入了 x=42，因此类 A 拥有属性 x，输出 42。若不调用 super().__new__ 或未加入命名空间，则可能出错或没有该属性。

### single_choice · None



- [A] __new__ 负责初始化类属性，__init__ 负责创建类对象
- [B] __new__ 负责创建并返回类对象，__init__ 在类对象创建后对其初始化
- [C] 两者完全等价，用哪个都可以
- [D] 只有 __init__ 能修改类命名空间

**参考答案**：1

**解析**：元类的 __new__ 用于创建并返回类对象，__init__ 在类对象创建之后进行初始化。A 把职责说反；C 错在两者职责不同；D 错误，__new__ 也能通过命名空间修改类属性。

### single_choice · None



- [A] super().__new__ 的第一个参数应为 mcls
- [B] super().__new__ 不应传入 name
- [C] super().__new__ 不应传入 bases
- [D] 这段代码不会出错

**参考答案**：3

**解析**：上述写法是标准且正确的元类 __new__ 模式：super().__new__(mcls, name, bases, ns)。A/B/C 都是常见误解，但此代码本身没有问题。

### single_choice · None



- [A] Python 会自动把它转成类对象
- [B] Python 会抛出 TypeError，创建类失败
- [C] 仍然可以正常使用，只是没有元类效果
- [D] 会忽略返回值，继续按默认机制创建类

**参考答案**：1

**解析**：元类 __new__ 必须返回一个类对象（通常是 type 实例）。若返回非类对象，解释器在构建类时无法完成绑定，会抛出 TypeError。

### single_choice · None



- [A] __getattribute__（定义在类上）
- [B] __getattr__（定义在类上）
- [C] __getattribute__（定义在元类上）
- [D] __setattr__（定义在类上）

**参考答案**：2

**解析**：类属性的读取由元类的 __getattribute__/__getattr__ 控制。定义在类上的 __getattribute__ 影响的是实例属性读取。D 影响的是实例属性赋值，不是读取。

### single_choice · None



- [A] 前者创建的不是类对象
- [B] 两者都会调用 Meta，但语法形式不同，本质机制一致
- [C] 前者不会触发 Meta.__new__
- [D] 后者无法使用元类

**参考答案**：1

**解析**：class A(metaclass=Meta) 等价于使用 Meta 作为元类来创建类，其创建过程与 Meta('A', (), {}) 本质一致。A 错误，Name 等参数决定结果仍是类对象；C 错误，都会触发元类 __new__；D 错误，class 语法正是使用元类的方式。

### single_choice · None



- [A] 类的元类必须与父类的元类完全相同
- [B] 类的元类必须是父类元类的子类（或相同）
- [C] 子类总是使用 type 作为元类，与父类无关
- [D] 元类不能被继承

**参考答案**：1

**解析**：Python 要求子类的元类必须是其所有父类元类的（非严格）子类，以保证类创建过程兼容。A 太严格；C 错误，会考虑父类元类；D 错误，元类可以被继承。

### single_choice · None



- [A] 数据描述符
- [B] 非数据描述符
- [C] 类描述符
- [D] 实例描述符

**参考答案**：1

**解析**：只定义了 __get__ 而未定义 __set__ 或 __delete__ 的描述符被称为非数据描述符。数据描述符需要同时定义 __set__ 或 __delete__。

### single_choice · None



- [A] 实例字典中的值
- [B] 数据描述符的 __get__ 返回值
- [C] 抛出 AttributeError
- [D] 非数据描述符的返回值

**参考答案**：1

**解析**：数据描述符的优先级高于实例字典。当同时存在数据描述符和同名实例属性时，Python 会优先调用数据描述符的 __get__ 方法。

### multi_choice · None



- [A] __get__ 和 __set__
- [B] __get__ 和 __delete__
- [C] 仅 __get__
- [D] __get__、__set__ 和 __delete__

**参考答案**：[0, 1, 3]

**解析**：数据描述符需要定义 __set__ 或 __delete__。仅定义 __get__ 的是非数据描述符。因此选项 A、B、D 都属于数据描述符，C 不是。

### multi_choice · None



- [A] 数据描述符优先于实例字典
- [B] 实例字典优先于非数据描述符
- [C] 非数据描述符优先于实例字典
- [D] 实例字典优先于数据描述符

**参考答案**：[0, 1]

**解析**：属性查找顺序为：数据描述符 > 实例字典 > 非数据描述符 > 类属性。因此数据描述符优先于实例字典，实例字典优先于非数据描述符。

### multi_choice · None



- [A] 描述符必须是类属性才能生效
- [B] 非数据描述符的优先级低于实例字典
- [C] __set_name__ 在类创建时自动调用
- [D] 所有描述符都必须实现 __get__ 方法

**参考答案**：[0, 1, 2]

**解析**：描述符必须作为类属性才能触发协议；非数据描述符优先级低于实例字典；__set_name__ 在类创建时自动调用。描述符不必须实现 __get__，只实现 __set__ 也可以。

### multi_choice · None



- [A] 普通函数
- [B] staticmethod
- [C] classmethod
- [D] property

**参考答案**：[0, 1, 2]

**解析**：普通函数、staticmethod、classmethod 都只实现了 __get__，属于非数据描述符。property 实现了 __get__、__set__ 和 __delete__，是数据描述符。

### fill_blank · None



**参考答案**：["数据", "data"]

**解析**：定义了 __set__ 或 __delete__ 的描述符称为数据描述符，否则为非数据描述符。

### fill_blank · None



**参考答案**：["__get__", "__get__方法", "__get__()"]

**解析**：描述符通过 __get__(self, instance, owner) 方法实现属性读取。

### fill_blank · None



**参考答案**：["__set_name__", "__set_name__方法", "__set_name__()"]

**解析**：__set_name__ 在类创建时自动被调用，参数为 owner 类和属性名字符串。

### code_reading · None



**参考答案**：descriptor

**解析**：D 是非数据描述符。属性查找顺序为：数据描述符 > 实例字典 > 非数据描述符。由于 D 是非数据描述符，实例字典优先，因此输出应为 'instance'？等等——注意 D 只定义了 __get__，是非数据描述符，实例字典优先级更高，所以输出是 'instance'。正确答案应为 'instance'。

### code_reading · None



**参考答案**：descriptor

**解析**：D 是数据描述符（定义了 __set__）。数据描述符优先级高于实例字典，因此即使 __set__ 中向实例字典写入了 'x'，读取 c.x 时仍然调用 __get__，返回 'descriptor'。

### scenario · None



**解析**：应使用数据描述符：定义 __get__ 和 __set__ 方法，将字段描述符作为类属性。__set__ 中做类型校验，__get__ 中返回存储值。数据描述符优先级高于实例字典，确保每次赋值和读取都经过校验逻辑。

### single_choice · None



- [A] instance 始终是类的实例，owner 始终是类本身
- [B] 当通过类访问描述符时，instance 为 None，owner 为类本身
- [C] 当通过实例访问描述符时，owner 为 None
- [D] instance 和 owner 不能同时为 None

**参考答案**：1

**解析**：通过类访问描述符时，instance 参数为 None，owner 为拥有该描述符的类。通过实例访问时，instance 为该实例，owner 为该实例的类。

### scenario · None



**解析**：描述符协议只在描述符作为类属性时生效。如果将描述符实例赋给实例属性，Python 不会触发 __get__ 和 __set__。修复方案是将描述符定义为类属性，通过类来管理属性访问。

### single_choice · None



- [A] classmethod
- [B] staticmethod
- [C] property
- [D] 普通函数

**参考答案**：2

**解析**：property 实现了 __get__、__set__ 和 __delete__，是典型的数据描述符。staticmethod 和 classmethod 是非数据描述符。普通函数只实现了 __get__，也是非数据描述符。

### single_choice · None



- [A] 因为函数是数据描述符，__get__ 返回绑定方法
- [B] 因为函数是非数据描述符，__get__ 返回绑定方法
- [C] 因为 Python 在实例化时自动将所有函数转为方法
- [D] 因为函数对象在类创建时被替换为 method 对象

**参考答案**：1

**解析**：函数实现了 __get__ 方法，属于非数据描述符。当通过实例访问类中的函数时，__get__ 返回一个绑定方法，将实例作为第一个参数绑定。

### single_choice · None



- [A] 42
- [B] 抛出 AttributeError
- [C] <__main__.D object at ...>
- [D] None

**参考答案**：0

**解析**：D 是非数据描述符，访问 c.x 时调用 D.__get__，返回 42。

### single_choice · None



- [A] 它在每次设置描述符值时被调用
- [B] 它在类创建时自动被调用，用于告知描述符其被绑定的属性名
- [C] 它只能用于数据描述符
- [D] 它必须手动调用才能生效

**参考答案**：1

**解析**：__set_name__ 在类创建时由 Python 自动调用，传入 owner 类和属性名，使描述符知道自己在类中的名称。

### single_choice · None



- [A] 返回描述符对象本身
- [B] 抛出 AttributeError
- [C] 返回 None
- [D] 调用 __set__ 并返回其结果

**参考答案**：0

**解析**：只有 __set__ 没有 __get__ 的对象仍然是数据描述符（因为定义了 __set__），但读取时会因为缺少 __get__ 而返回描述符对象本身（通过类属性查找找到描述符，但没有 __get__ 可调用）。

### single_choice · None



- [A] 在实例字典中设置 c.__dict__['x'] = 10
- [B] 调用 D.__set__，将 10 存入 c._x
- [C] 抛出 AttributeError
- [D] 调用 D.__get__ 并返回 10

**参考答案**：1

**解析**：D 是数据描述符，赋值时会调用 __set__ 方法，将值存入 obj._x。

### single_choice · None



- [A] 描述符必须是实例属性
- [B] 描述符必须是类属性
- [C] 描述符可以是任意属性
- [D] 描述符必须同时定义了 __get__ 和 __set__

**参考答案**：1

**解析**：描述符机制只在描述符作为类属性时生效。如果描述符是实例属性，不会触发描述符协议。
