# s2u1l4 Python 属性（property）：从直觉到工程级 / `__slots__` 是 Python 类里一个「省内

> 来源 `content/lessons/s2u1l4.json`

## py.oop.property

# Python 属性（property）：从直觉到工程级

## 一句话直觉

**属性（property）让你像访问普通变量一样访问方法，从而在不破坏调用方代码的前提下，把"裸数据"升级为"带校验、可计算、可读写控制"的智能属性。**

---

## 第一节：为什么需要 property？——从"裸属性"说起

在 Python 中，类的实例属性（instance attribute）默认是公开的，谁都可以随意读写：

```python
class Circle:
    def __init__(self, radius):
        self.radius = radius

c = Circle(5)
c.radius = -3          # 没人拦住你，但这是无意义的负数
print(c.radius)        # -3
```

问题来了：如果某天你想加一个"半径必须为正"的校验，传统做法是改成方法：

```python
class Circle:
    def set_radius(self, value):
        if value <= 0:
            raise ValueError("半径必须为正")
        self._radius = value
```

但这样一来，所有原来写 `c.radius = 5` 的代码都得改成 `c.set_radius(5)`——**接口被破坏**。

`property` 就是为了解决这个矛盾：**保持 `c.radius = 5` 的写法不变，却在背后做校验。** 这是面向对象封装（encapsulation）最常用的手段之一。

---

## 第二节：property 的三种用法

### 2.1 装饰器写法（推荐）

用 `@property`、`@xxx.setter`、`@xxx.deleter` 三个装饰器分别定义读、写、删：

```python
class Circle:
    def __init__(self, radius):
        self._radius = None
        self.radius = radius          # 触发 setter 校验

    @property
    def radius(self):                 # getter
        return self._radius

    @radius.setter
    def radius(self, value):          # setter
        if value <= 0:
            raise ValueError("半径必须为正")
        self._radius = value

    @property
    def area(self):                   # 只读的计算属性
        return 3.14159 * self._radius ** 2


c = Circle(5)
print(c.radius)      # 5     —— 读时走 getter
print(c.area)        # 78.5  —— 计算属性，无需存值
c.radius = 10
print(c.area)        # 314.0
# c.area = 100       # AttributeError，只读
# c.radius = -1      # ValueError，setter 拦截
```

### 2.2 只有 getter = 只读属性

只定义 `@property` 不定义 setter，该属性就是只读的——写入会抛 `AttributeError`。上面 `area` 就是例子。

### 2.3 经典函数写法

`property(fget, fset, fdel, doc)` 也能用，但可读性差，工程上基本不用。这里知道即可。

---

## 第三节：property 的执行时机与常见坑

理解 property 的关键是：**它本质是一个数据描述符（data descriptor），定义在类上，拦截对同名实例属性的访问。**

几点推论：

1. **property 必须定义在类上**，不能定义在实例上。这点和普通属性不同。
2. **内部存储要用不同名字**（如 `self._radius`），否则 setter 里写 `self.radius = value` 会无限递归。
3. **访问顺序**：Python 查属性时，类上的数据描述符（如 property）优先于实例字典 `__dict__`。

```python
class Demo:
    def __init__(self):
        self.__dict__['x'] = 100   # 直接写进实例字典

    @property
    def x(self):
        return 999                 # property 会赢过实例字典

d = Demo()
print(d.x)   # 999，不是 100
```

---

## 第四节：工程级应用——从校验到缓存

property 在生产代码里最典型的两类用途：

### 4.1 数据校验与规范化（validation / normalization）

```python
class User:
    def __init__(self, name):
        self.name = name

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        if not isinstance(value, str):       # 用 isinstance 而非 type()
            raise TypeError("name 必须是字符串")
        value = value.strip()
        if not value:
            raise ValueError("name 不能为空")
        self._name = value.title()           # 规范化


u = User("  alice ")
print(u.name)   # Alice
```

### 4.2 惰性计算 + 缓存（lazy / cached property）

计算开销大的属性，只算一次并缓存：

```python
class DataSet:
    def __init__(self, raw):
        self._raw = raw
        self._stats = None

    @property
    def stats(self):
        if self._stats is None:
            print("计算中……（只出现一次）")
            self._stats = {
                "n":  len(self._raw),
                "sum": sum(self._raw),
            }
        return self._stats

ds = DataSet([1, 2, 3, 4, 5])
print(ds.stats)   # 计算一次
print(ds.stats)   # 直接命中缓存
```

Python 3.8+ 还提供 `functools.cached_property`，一行搞定：

```python
from functools import cached_property

class DataSet:
    def __init__(self, raw):
        self._raw = raw

    @cached_property
    def stats(self):
        return {"n": len(self._raw), "sum": sum(self._raw)}
```

---

## 第五节：property vs 普通属性 vs 方法——怎么选？

| 场景 | 建议 |
|------|------|
| 纯数据容器，无校验、无计算 | 直接用普通属性 |
| 需要读写校验、格式转换 | 用 property |
| 计算代价大或有副作用 | 用方法（显式调用），避免误以为"便宜" |
| 计算便宜且无副作用 | 可用 property，UI 更干净 |

**经验法则**：property 应该是"廉价、无副作用、幂等"的。如果一次访问可能耗时 1 秒，就别做成 property——用户看不出这是一次昂贵调用。

---

## 动手练习

写一个 `Temperature` 类，满足：

1. 构造时接受摄氏度（Celsius）数值，存入内部属性。
2. `celsius` 属性：可读可写；写入时若小于绝对零度（-273.15）抛 `ValueError`。
3. `fahrenheit` 属性：**只读**，返回 `celsius * 9/5 + 32`，且保留两位小数。
4. `kelvin` 属性：**只读**，返回 `celsius + 273.15`。

验证：

```python
t = Temperature(25)
assert t.fahrenheit == 77.0
assert t.kelvin == 298.15
t.celsius = -300        # 应抛 ValueError
t.fahrenheit = 100      # 应抛 AttributeError
```

**进阶**：给 `fahrenheit` 加一个 `fahrenheit.setter`，让它接受华氏度并反算存储的摄氏度；然后思考：这样会不会让"只读"和"可写"的语义变得混乱？在什么场景下这种双向属性是合理的？

```python
class Temperature:
    """温度类：演示 property 的读/写/只读三种形态。"""

    ABSOLUTE_ZERO_C = -273.15

    def __init__(self, celsius):
        self._celsius = None
        self.celsius = celsius          # 触发 setter 做校验

    # ---- 可读可写：摄氏度 ----
    @property
    def celsius(self):
        return self._celsius

    @celsius.setter
    def celsius(self, value):
        if value < self.ABSOLUTE_ZERO_C:
            raise ValueError(f"温度不能低于绝对零度 {self.ABSOLUTE_ZERO_C}°C")
        self._celsius = float(value)

    # ---- 只读：华氏度（计算属性） ----
    @property
    def fahrenheit(self):
        return round(self._celsius * 9 / 5 + 32, 2)

    # ---- 只读：开尔文 ----
    @property
    def kelvin(self):
        return round(self._celsius + 273.15, 2)


if __name__ == "__main__":
    t = Temperature(25)
    print(t.celsius, t.fahrenheit, t.kelvin)   # 25.0 77.0 298.15

    t.celsius = 0
    print(t.fahrenheit)                        # 32.0

    try:
        t.celsius = -300
    except ValueError as e:
        print("被拦截:", e)

    try:
        t.fahrenheit = 100                     # 没有 setter → AttributeError
    except AttributeError as e:
        print("只读保护:", e)
```

## py.oop.slots

## 一句话直觉

`__slots__` 是 Python 类里一个「省内存」的小开关：加上它，对象就不能再随手加新属性，实例内存可减少 30%~60%，在需要创建几十万个小对象时（比如机器学习里的样本、图节点、Token）差别巨大。

> 前置：`__slots__` 属于 Python 面向对象（OOP, Object-Oriented Programming）的基础，是「类属性」的一部分，零基础同学也能直接上手。

---

## 1. 没有 `__slots__` 时，对象把钱花在哪？

默认情况下，每个 Python 实例都有一个隐藏字典 `__dict__`，所有属性都存在里面。字典非常灵活，但每个实例都要单独维护一个哈希表，内存开销很大。

```python
class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

p = Point(1, 2)
print(p.__dict__)   # {'x': 1, 'y': 2}，属性存在字典里
p.z = 3             # 可以随时添加新属性（字典的优点，也是缺点）
print(p.__dict__)   # {'x': 1, 'y': 2, 'z': 3}
```

关键结论：**没有 `__slots__` 的类是「字典驱动」的，灵活但占用大。**

---

## 2. 加上 `__slots__`：从字典切换成定长数组

在类中声明 `__slots__ = (...)`，Python 就不再为每个实例创建 `__dict__`，而是用一块固定大小的连续内存保存这些属性。

```python
class Point:
    __slots__ = ("x", "y")   # 只允许这两个属性

    def __init__(self, x, y):
        self.x = x
        self.y = y

p = Point(1, 2)
print(p.x, p.y)     # 1 2，正常读写
print(hasattr(p, "__dict__"))   # False，没有实例字典了

# p.z = 3          # ❌ AttributeError: 'Point' object has no attribute 'z'
```

关键结论：**`__slots__` 用「固定字段」换「内存和速度」，代价是失去动态加属性的能力。**

---

## 3. 内存到底省多少？动手量一下

光说不练不行，用 `sys.getsizeof` 看单个对象，再用 `tracemalloc` 看整体。

```python
import sys, tracemalloc

class WithDict:
    def __init__(self, x, y):
        self.x = x
        self.y = y

class WithSlots:
    __slots__ = ("x", "y")
    def __init__(self, x, y):
        self.x = x
        self.y = y

# 单个对象大小（不含 dict 本身）
print(sys.getsizeof(WithDict(1, 2)))    # 通常 48 字节（仅对象头部）
print(sys.getsizeof(WithSlots(1, 2)))   # 通常 48 字节 + 两个指针
print(sys.getsizeof(WithDict(1, 2).__dict__))  # 额外 104+ 字节的字典

# 十个小对象总内存对比
tracemalloc.start()
objs1 = [WithDict(i, i) for i in range(10)]
print("dict 版:", tracemalloc.get_traced_memory()[1])
tracemalloc.stop()

tracemalloc.start()
objs2 = [WithSlots(i, i) for i in range(10)]
print("slots 版:", tracemalloc.get_traced_memory()[1])
tracemalloc.stop()
```

关键结论：**对象越多，`__slots__` 的收益越明显；几千个以内通常感觉不出来，几十万级就是「必选项」。**

---

## 4. 继承里的坑：每个类都要显式声明

`__slots__` 不会被自动继承成「子类也能省内存」。如果父类有、子类没写，子类又会恢复 `__dict__`。

```python
class Base:
    __slots__ = ("a",)

class ChildNoSlots(Base):
    pass

class ChildWithSlots(Base):
    __slots__ = ("b",)     # 只列自己新增的，别重复 a

c1 = ChildNoSlots()
c1.a = 1
c1.b = 2            # ✅ 可以，因为字类自动有 __dict__
print(hasattr(c1, "__dict__"))   # True，前功尽弃

c2 = ChildWithSlots()
c2.a = 1
c2.b = 2
# c2.c = 3         # ❌ AttributeError
print(hasattr(c2, "__dict__"))   # False，内存保住了
```

关键结论：**想让整条继承链都省内存，每个子类都必须写 `__slots__`，且只列新增字段。**

---

## 5. 工程级用法：和 `dataclass`、PyTorch 场景配合

Python 3.10+ 的 `dataclass` 直接支持 `slots=True`，不用手写 `__slots__`：

```python
from dataclasses import dataclass

@dataclass(slots=True)
class Sample:
    x: float
    y: float
    label: int

s = Sample(1.0, 2.0, 0)
print(s)                        # Sample(x=1.0, y=2.0, label=0)
print(hasattr(s, "__dict__"))   # False
```

在深度学习里，一次训练动辄要构造几十万个小样本（pixels、token、图节点），用 `slots=True` 的 dataclass 可以明显降低 Python 侧的常驻内存。PyTorch 官方教程在数据结构章节也提倡优先使用 `dataclass` 风格来组织样本，避免为每个样本额外开字典。

关键结论：**能用 `dataclass(slots=True)` 就别手写 `__slots__`，更安全也更省心。**

---

## 常见误区

- **误区 1：`__slots__` 是「性能银弹」**。它主要省内存，对访问速度的提升很有限，别指望靠它把算力瓶颈干掉。
- **误区 2：子类会自动继承 `__slots__`**。不会，每个子类都要单独声明自己的新增字段。
- **误区 3：可以随便在实例上加属性**。用了 `__slots__` 后不能，只能声明里出现过的字段。
- **误区 4：写了 `__slots__` 就完全没字典**。只要任一父类没写，`__dict__` 仍会被创建；并且 `__slots__` 的类仍然会有类级别的字典用于方法等。
- **误区 5：字段名重复声明**。父类已声明的字段在子类里再放一次，会导致部分版本下报错或产生多余描述符。

---

## 动手练习

在你的本地环境完成以下小任务：

1. 写两个类 `UserDict` 和 `UserSlots`，都保存 `name`（字符串）和 `age`（整数）两个字段。前者普通写法，后者用 `__slots__ = ("name", "age")`。
2. 用 `tracemalloc` 分别创建 100000 个实例，记录峰值内存并打印对比。
3. 尝试给两种实例各加一个字段 `city`，观察分别是成功还是抛出 `AttributeError`。
4. 把 `UserSlots` 改写成 `@dataclass(slots=True)` 版本，重新测一遍内存，比较手写与自动生成两种写法的结果是否一致。

完成后用一句话写下你的观察：在 10 万实例规模下，`__slots__` 大约省了百分之几的内存？

```python
import sys
import tracemalloc
from dataclasses import dataclass


class UserDict:
    def __init__(self, name, age):
        self.name = name
        self.age = age


class UserSlots:
    __slots__ = ("name", "age")

    def __init__(self, name, age):
        self.name = name
        self.age = age


@dataclass(slots=True)
class UserDataclass:
    name: str
    age: int


def measure(cls, n=100_000):
    tracemalloc.start()
    objs = [cls("alice", 30) for _ in range(n)]
    peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    return objs, peak


if __name__ == "__main__":
    _, d = measure(UserDict)
    _, s = measure(UserSlots)
    _, dc = measure(UserDataclass)
    print(f"UserDict       : {d:,} bytes")
    print(f"UserSlots      : {s:,} bytes")
    print(f"UserDataclass  : {dc:,} bytes")

    # 动态属性行为对比
    u1 = UserDict("bob", 20)
    u1.city = "SH"          # 普通类可以
    print(u1.__dict__)

    u2 = UserSlots("bob", 20)
    try:
        u2.city = "SH"
    except AttributeError as e:
        print("UserSlots 拒绝新增属性:", e)
```


---

## 本课题目

### single_choice · None



- [A] 12.56
- [B] <property object>
- [C] 报错：'property' object is not callable
- [D] None

**参考答案**：0

**解析**：@property 把 area 变成一个描述符，通过实例访问 c.area 会自动调用被装饰的 getter 方法并返回其返回值 3.14*4=12.56，而不是返回 property 对象本身。

### single_choice · None



- [A] 25
- [B] 报错：'int' object is not callable
- [C] 报错：celsius 需要一个参数
- [D] <property object>

**参考答案**：1

**解析**：加了 @property 之后，t.celsius 已经是取值结果（25），再对它加 () 相当于调用整数 25，因此抛出 'int' object is not callable。这是把 property 当成普通方法调用的常见错误。

### single_choice · None



- [A] 100
- [B] 1
- [C] 报错：私有属性不能访问
- [D] 报错：setter 未定义

**参考答案**：1

**解析**：类中使用双下划线前缀 __x 会被名称改写为 _C__x。外部执行 c.__x=100 创建的是新属性 __x，并未改动被改名的 _C__x，所以 property 读到的仍是 1。

### single_choice · None



- [A] 5
- [B] 0
- [C] 报错：can't delete attribute
- [D] None

**参考答案**：1

**解析**：deleter 被 del t.c 触发，把 _c 重置为 0，随后 print(t.c) 输出 0。property 可以同时提供 getter、setter 和 deleter 三个方法。

### single_choice · None



- [A] 1
- [B] 2
- [C] 报错：不能覆盖 property
- [D] 报错：A 的 x 是只读的

**参考答案**：1

**解析**：子类用自己的 property 覆盖父类的同名 property 是允许的，实例访问走的是子类定义，返回 2。Python 的属性查找遵循 MRO 从左到右的规则。

### single_choice · None



- [A] 1
- [B] 7
- [C] 报错：属性名冲突
- [D] <property object>

**参考答案**：1

**解析**：property(fget, fset) 同时注册取值和赋值方法，赋值 c.v=7 调用 _set_v，读取 c.v 调用 _get_v，输出 7。这是 property 的经典用法。

### single_choice · None



- [A] 无异常，c.v 变为 10
- [B] 抛出 AttributeError（只读）
- [C] 抛出 TypeError
- [D] 属性值被 property 忽略但不报错

**参考答案**：1

**解析**：只提供 getter 的 property 是只读的，赋值会触发 property 的 __set__，抛出 AttributeError，不会静默忽略或改变值。

### single_choice · None



- [A] 3
- [B] 6
- [C] 9
- [D] 报错：重复定义 setter

**参考答案**：1

**解析**：后面的 @x.setter 会覆盖前面的 setter 注册，最终生效的是 v*2，赋值 3 后 _x=6，读取得到 6。重复定义不会报错，后定义者胜出。

### single_choice · None



- [A] 1
- [B] 无限递归导致 RecursionError
- [C] 0
- [D] 报错：property 未定义

**参考答案**：1

**解析**：getter 中 return self.x 又触发 property 自身，形成无限递归，最终抛出 RecursionError。正确做法是内部使用 self._x。

### single_choice · None



- [A] 100
- [B] 212.0
- [C] 37.8
- [D] 报错：fahrenheit 是只读的

**参考答案**：1

**解析**：getter 把摄氏度转换成华氏度：100*9/5+32=212.0。只读 property 不妨碍读取，它常用于派生/计算属性。

### single_choice · None



- [A] 报错：can't set attribute
- [B] [1]
- [C] []
- [D] 报错：'list' object has no attribute 'append'

**参考答案**：1

**解析**：只读 property 禁止的是对 c.items 赋值，返回的列表对象本身是可变的，对其调用 append 合法，因此输出 [1]。这是返回可变对象的常见陷阱。

### single_choice · None



- [A] 5
- [B] 1
- [C] AttributeError
- [D] 报错：set_x 不是 property

**参考答案**：2

**解析**：@x.setter 要求被装饰的方法名与属性名一致（x），这里写成了 set_x，实际并没有为 x 注册 setter，x 仍是只读，赋值触发 AttributeError。这是一个常见书写错误。

### single_choice · None



- [A] 100
- [B] 12
- [C] 报错：can't set attribute
- [D] 报错：property 'area' has no setter

**参考答案**：2

**解析**：只定义了 getter 的 property 是只读的，对它赋值会抛出 AttributeError（常见的提示为 can't set attribute 或 property 'area' has no setter），不会覆盖属性的值。

### single_choice · None



- [A] '  Jerry  '
- [B] 'Jerry'
- [C] '  Tom  '
- [D] 报错：can't set attribute

**参考答案**：1

**解析**：@name.setter 注册的 setter 在赋值 p.name='  Jerry  ' 时被调用，内部做了 strip()，因此读回时是 'Jerry'。注意 setter 装饰器必须复用同一个属性名。

### single_choice · None



- [A] caught: must be non-negative
  -5
- [B] caught: must be non-negative
  1
- [C] 报错：can't set attribute
- [D] -5

**参考答案**：1

**解析**：setter 中校验 v<0 时抛出 ValueError，赋值失败，内部 _v 仍为初始值 1；异常被捕获后打印 b.value 得到 1。这体现了 property 做输入校验时不会破坏原值。

### single_choice · None



- [A] 0 1 2
- [B] 1 2 3
- [C] 1 1 1
- [D] 报错：property 不能在 getter 中修改状态

**参考答案**：1

**解析**：property 的 getter 本质上就是一个普通方法，每次访问 c.n 都会执行，内部累加 _n。因此三次访问输出 1、2、3。property 并不会缓存结果，也不禁止在 getter 中修改状态。

### single_choice · None



- [A] A().x 和 B().x 都是方法对象
- [B] A().x 得到 1，B().x 得到绑定方法对象
- [C] 两者都不能访问，必须加括号
- [D] A().x 是 property 对象，B().x 是 1

**参考答案**：1

**解析**：A 中 x 被 @property 装饰后，实例访问触发 getter 返回 1；B 中 x 是普通方法，实例访问得到绑定方法对象（bound method），需要 B().x() 才会调用。

### single_choice · None



- [A] 报错：property 只能用于装饰器语法
- [B] 1
- [C] <property object>
- [D] get_x

**参考答案**：1

**解析**：property(fget) 是 property 的经典构造函数用法，把 get_x 注册为取值方法。f.x 触发 get_x 返回 1。装饰器语法和显式构造是等价的。

### single_choice · None



- [A] 10
- [B] 报错：can't set attribute
- [C] 3
- [D] 报错：x 不是 property

**参考答案**：0

**解析**：这里 x 就是普通实例属性，没有使用 property，赋值与读取都会正常进行，输出 10。很多初学者看到类似题目会误以为所有属性都是只读的。

### single_choice · None



- [A] 1
- [B] <property object>
- [C] 报错：需要实例才能访问
- [D] None

**参考答案**：1

**解析**：通过类（而不是实例）访问 property 时，property 对象自身不会调用 getter，得到的是 property 对象。只有通过实例访问才会触发 getter 返回 1。

### single_choice · None



- [A] 禁止该类实例添加 __slots__ 中未声明的属性
- [B] 自动把所有属性变成只读
- [C] 让该类不能被继承
- [D] 让所有属性变成类属性

**参考答案**：0

**解析**：__slots__ 的核心作用是限制实例可绑定的属性集合，实例不能再随意新增未声明的属性；它不会自动把属性变成只读（只读需要 property 或 __setattr__ 等配合），也不阻止继承，也不会把实例属性变成类属性。

### single_choice · None



- [A] 输出 3
- [B] 输出 33
- [C] 抛出 AttributeError，因为 z 不在 __slots__ 中
- [D] 抛出 TypeError，因为 __slots__ 必须是列表

**参考答案**：2

**解析**：p.x 和 p.y 可以赋值，但 p.z 不在 __slots__ 元组中，给实例绑定未声明属性会触发 AttributeError。因此程序在 print 之前就报错，不会输出 3。

### single_choice · None



- [A] 槽位 x 和方法 x 可以共存，互不影响
- [B] 方法 x 会遮蔽槽位 x，导致实例无法正常通过 x 属性保存值
- [C] 定义类时直接抛出 SyntaxError
- [D] 槽位优先，方法会被自动删除

**参考答案**：1

**解析**：同名方法属于类属性，会遮蔽 __slots__ 生成的槽位描述符，使该槽位无法正常工作。实际中应避免方法名与槽位名冲突。

### multi_choice · None



- [A] __slots__ 可以是一个字符串序列，常见形式是元组或列表
- [B] 使用 __slots__ 后，实例通常不再有 __dict__
- [C] __slots__ 会限制实例可绑定的属性名
- [D] __slots__ 会让类的所有方法都变成类方法
- [E] __slots__ 能完全替代 dataclass 或属性校验

**参考答案**：[0, 1, 2]

**解析**：__slots__ 接受字符串序列，用于限制属性并通常去掉实例 __dict__；它不改变方法的绑定性质，也不提供属性校验或替代数据类功能。

### multi_choice · None



- [A] 子类的可用槽位是父类与子类 __slots__ 的并集
- [B] 父类和子类不应重复声明同名槽位，否则浪费空间且易混淆
- [C] 若子类未定义 __slots__，子类实例会重新获得 __dict__
- [D] 父类定义 __slots__ 后，子类一定也不能有 __dict__
- [E] 多继承中多个父类都有非空 __slots__ 会引发冲突

**参考答案**：[0, 1, 2, 4]

**解析**：槽位沿继承链累积；重复声明同名槽位会浪费空间并可能造成误解；子类未定义 __slots__ 时会重新获得 __dict__；多继承中多个父类都有非空 __slots__ 通常会发生布局冲突而报错。因此“子类一定也不能有 __dict__”错误。

### multi_choice · None



- [A] instance.a = 1
- [B] instance.c = 3
- [C] del instance.a
- [D] instance.__dict__ = {}
- [E] instance.b = 2

**参考答案**：[1, 3]

**解析**：a 和 b 是已声明槽位，可正常赋值和删除；c 未声明会触发 AttributeError；实例没有 __dict__，给 __dict__ 赋值也会失败。del instance.a 是允许的。

### fill_blank · None



**参考答案**：["__slots__", "slots", "__slots__ "]

**解析**：Python 使用特殊类属性 __slots__ 来声明槽位，其值应为字符串组成的序列，如元组或列表。

### fill_blank · None



**参考答案**：["__weakref__", "weakref", "__weakref__ "]

**解析**：默认情况下，使用 __slots__ 后实例没有 __dict__ 也没有 __weakref__，因此不能被弱引用。把 '__weakref__' 加入 __slots__ 可以恢复弱引用支持。

### code_reading · None



**参考答案**：输出两行：第一行 1，第二行 err。因为 x 是已声明槽位可正常赋值；y 未在 __slots__ 中，给实例绑定未声明属性会抛出 AttributeError，被 except 捕获后打印 err。

**解析**：__slots__ 限制了实例的属性集合，已声明槽位正常访问，未声明属性触发 AttributeError。

### code_reading · None



**参考答案**：输出 True。因为 B 没有定义 __slots__，所以 B 的实例重新获得了 __dict__，可以添加属性 y，并且 hasattr(b, '__dict__') 为 True。

**解析**：子类未定义 __slots__ 时会引入 __dict__，从而突破父类的槽位限制，这也是使用 __slots__ 时容易忽略的继承陷阱。

### scenario · None



**解析**：__slots__ 通过去掉每个实例的 __dict__ 来降低内存占用，把属性存放在固定槽位中。设计时要注意：实例只能使用声明的属性，未声明属性会报错；继承时要小心子类未定义 __slots__ 会重新获得 __dict__，使节省效果失效，同时避免与父类重复声明同名槽位或与类属性同名。

### scenario · None



**解析**：在定义 __slots__ 的类中，实例默认没有 __weakref__ 槽位，因此不能创建弱引用。解决方式是在 __slots__ 中显式加入 '__weakref__'，这样既保留槽位带来的内存优势，又恢复弱引用支持；若继承链已有父类提供该槽位则不必重复添加。

### single_choice · None



- [A] 定义 __slots__ 后，实例一定仍然拥有 __dict__
- [B] 定义 __slots__ 后，通常该类的实例不再有 __dict__（除非显式把 __dict__ 放进 __slots__ 或来自父类）
- [C] 定义 __slots__ 会把 __dict__ 变成只读字典
- [D] 定义 __slots__ 会删除类的 __dict__

**参考答案**：1

**解析**：使用 __slots__ 的主要收益之一是去掉实例的 __dict__，从而节省内存。但若在 __slots__ 中包含 '__dict__'，或继承自未定义 __slots__ 的父类，实例仍可能拥有 __dict__。类本身始终有 __dict__。

### single_choice · None



- [A] 正常，name 来自 Animal 的 __slots__
- [B] 抛出 AttributeError，因为 Dog 必须重复声明 name
- [C] 抛出 TypeError，因为两个 __slots__ 冲突
- [D] 正常，但 name 会存到 Dog.__dict__ 中

**参考答案**：0

**解析**：__slots__ 在继承链中会累积：子类实例可用的槽位是各层 __slots__ 的并集。Dog 的实例既可以使用 Animal 声明的 name，也可以使用 Dog 声明的 breed，不需要重复声明。

### single_choice · None



- [A] 仍然没有 __dict__，完全受父类槽位限制
- [B] 会重新获得 __dict__，可以添加任意新属性
- [C] 会抛出 TypeError，类定义失败
- [D] 会继承父类槽位并自动变成只读

**参考答案**：1

**解析**：如果子类没有定义 __slots__，Python 会给子类实例加上 __dict__，因此可以动态添加属性。这意味着父类的内存节省效果在未定义 __slots__ 的子类上会失效。

### single_choice · None



- [A] 如果类属性与槽位同名，类属性会直接覆盖槽位，使槽位失效
- [B] 同名时类属性会被忽略，仍可正常使用槽位
- [C] 同名会直接抛出 ValueError
- [D] 同名时实例读取到的一定是类属性

**参考答案**：0

**解析**：如果某个类属性与 __slots__ 中的名字相同，类属性会遮蔽槽位描述符，导致该槽位无法按预期工作，实例读取会拿到类属性。因此应避免这种命名冲突。

### single_choice · None



- [A] __slots__ 可以减少每个实例的内存占用
- [B] __slots__ 可以限制实例可添加的属性
- [C] __slots__ 会让属性访问速度在所有情况下都必然更快
- [D] __slots__ 可以配合继承使用

**参考答案**：2

**解析**：去掉了 __dict__ 后，属性访问通常更快，但说“所有情况下必然更快”是过度绝对化的误解；性能受描述符、继承、访问模式等影响。其余三项都是 __slots__ 的正当用途。

### single_choice · None



- [A] __slots__ 中的名字只是属性名，不会创建默认值，因此不能靠 __slots__ 给实例赋初值
- [B] __slots__ 会自动为每个槽位创建默认值 None
- [C] __slots__ 只能放可变对象，不能放字符串
- [D] __slots__ 会自动调用 __init__ 初始化所有槽位

**参考答案**：0

**解析**：__slots__ 只声明可用的属性名，并不会为这些属性创建默认值或自动初始化。若需要初始值，仍然要在 __init__ 等方法中显式赋值。

### single_choice · None



- [A] 定义了 __slots__ 的类，其实例默认一定支持弱引用
- [B] 定义了 __slots__ 的类，若未在 __slots__ 中包含 '__weakref__'，其实例通常不能创建弱引用
- [C] __slots__ 与弱引用完全无关
- [D] 只要继承自 object 就一定能对任何实例创建弱引用

**参考答案**：1

**解析**：实例若没有 __dict__ 也没有 __weakref__ 槽位，通常无法被 weakref 引用。需要在 __slots__ 中显式加入 '__weakref__'，除非父类已经提供。

### single_choice · None



- [A] True
- [B] False
- [C] 抛出 AttributeError
- [D] 抛出 TypeError

**参考答案**：1

**解析**：A 定义了 __slots__ 且父类为 object（没有提供 __dict__），因此其实例没有 __dict__，hasattr(a, '__dict__') 返回 False。
