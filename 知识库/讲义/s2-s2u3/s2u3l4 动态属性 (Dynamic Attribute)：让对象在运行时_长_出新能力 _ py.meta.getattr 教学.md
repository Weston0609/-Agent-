# s2u3l4 动态属性 (Dynamic Attribute)：让对象在运行时"长"出新能力 / py.meta.getattr 教学讲义

> 来源 `content/lessons/s2u3l4.json`

## py.meta.dynamic_attr

# 动态属性 (Dynamic Attribute)：让对象在运行时"长"出新能力

> **一句话直觉**：Python 的对象不是"出厂即冻结"的，你可以在程序运行时随时给它挂上新属性、新方法，甚至改写已有行为——这正是框架、ORM、测试 mock 能存在的根本原因。

---

## 1. 从"普通属性"说起：属性其实是存放在字典里的

在 Python 里，几乎每个对象背后都藏着一个 `__dict__`（命名空间字典 namespace dictionary）。你写 `obj.x = 1`，本质是把 `'x': 1` 塞进了 `obj.__dict__`。理解这一点，就理解了动态属性的钥匙。

```python
class Dog:
    pass

# 创建一个实例
d = Dog()
d.name = "旺财"          # 直接挂属性
d.age = 3

# 查看对象内部的字典
print(d.__dict__)        # {'name': '旺财', 'age': 3}
```

**结论**：实例属性只是字典里的一对键值，运行期随时可增删改。

---

## 2. 用 `getattr` / `setattr` / `delattr` 动态操作属性

属性名如果是一个**字符串变量**，就不能用 `obj.x` 这种点号写法。这时要用三个内置函数：`getattr`（读）、`setattr`（写）、`delattr`（删）。

```python
class Config:
    pass

cfg = Config()

# 模拟从配置文件读进来的一组键值对
settings = {"host": "localhost", "port": 8080, "debug": True}

for k, v in settings.items():
    setattr(cfg, k, v)        # 动态设置属性

print(getattr(cfg, "host"))   # localhost
print(getattr(cfg, "port"))   # 8080
print(cfg.debug)              # 直接用点号也可以

# 安全读取：属性不存在时给默认值，避免 AttributeError
print(getattr(cfg, "timeout", 30))   # 30
```

**结论**：`getattr` 的第三个参数是默认值，这是读取"可能不存在的属性"的标准写法。

---

## 3. 给实例挂一个方法：函数的"绑定"机制

函数本身也是对象。把一个函数赋给实例属性后，我们要注意它是普通函数，不会自动绑定 `self`。想要"变成方法"，需要用 `types.MethodType` 做绑定。

```python
import types

class Counter:
    def __init__(self):
        self.n = 0

def shout(self):
    self.n += 1
    print(f"第 {self.n} 次调用")

c = Counter()

# 直接赋值：这是普通函数，不绑定实例
c.shout = shout
c.shout(c)         # 手动把 c 传进去，等价于 self=c

# 正确绑定：让 c.shout() 自动把 c 当 self 传入
c.yell = types.MethodType(shout, c)
c.yell()           # 第 2 次调用
```

**结论**：`types.MethodType(func, instance)` 可以把函数绑定到某个实例上，从此点号调用会自动传入实例。

---

## 4. `__getattr__` 与 `__getattribute__`：让属性"按需计算"

有时你希望属性不是提前存好的，而是**访问时才生成**。这就是动态属性最常用的魔法：`__getattr__`——只有当正常查找失败时才被调用。

```python
class LazyConfig:
    def __init__(self, data: dict):
        self._data = data          # 真正数据藏在 _data

    def __getattr__(self, name):
        # 只在常规查找失败时触发
        if name in self._data:
            return self._data[name]
        raise AttributeError(f"没有属性 {name!r}")

lc = LazyConfig({"host": "db.local", "port": 5432})
print(lc.host)              # db.local，来自 __getattr__
print(lc.port)              # 5432
# print(lc.missing)         # 会抛 AttributeError
```

对比 `__getattribute__`：它在**每次**访问属性时都会先被调用，能力更强但也更容易写崩，一般只在框架级别使用。

**结论**：`__getattr__` 用于"缺省时补位"，是构造动态视图、懒加载、代理对象的利器。

---

## 5. `__slots__` 与 `property`：什么时候不该动态？

动态属性很强，但并非万能。`__slots__` 会**禁止**实例新增 `__dict__` 之外的属性；`property` 把属性变成方法驱动的"受控访问"。二者是工程里"收窄自由度"的常见手段。

```python
class Point:
    __slots__ = ("x", "y")     # 不允许新增其它实例属性
    def __init__(self, x, y):
        self.x = x
        self.y = y

p = Point(1, 2)
# p.z = 3                      # 报 AttributeError，被 __slots__ 拦住

class Temperature:
    def __init__(self, celsius):
        self._celsius = celsius

    @property
    def celsius(self):          # 读时会调用这个方法
        return self._celsius

    @celsius.setter
    def celsius(self, v):       # 写时会做校验
        if v < -273.15:
            raise ValueError("低于绝对零度")
        self._celsius = v

t = Temperature(25)
print(t.celsius)                # 25
t.celsius = 30
# t.celsius = -300              # ValueError
```

**结论**：动态属性给自由，`__slots__` 和 `property` 给约束；工程中要根据场景选合适的工具。

---

## 动手练习

写一个 `FlexibleRecord` 类，要求：

1. 用构造函数接收一个 `dict`，把内容存到内部 `_fields`；
2. 实现 `__getattr__`，让 `record.xxx` 可以读取字典里的键；
3. 实现一个 `add(name, value)` 方法，运行期向 `_fields` 添加新键；
4. 当访问不存在的键时，抛出带清晰提示的 `AttributeError`；
5. 在本地写 3~5 行测试：读取已有键、添加新键后再读取、尝试读不存在的键并捕获异常。

写完后思考：为什么用 `__getattr__` 而不是 `__getattribute__`？（提示：想清楚"兜底"和"全覆盖"的区别。）

```python
import types


class FlexibleRecord:
    """一个可以用字典当属性访问的动态记录对象。"""

    def __init__(self, data: dict):
        # 用 object.__setattr__ 避免触发下面的 __setattr__（若有）
        object.__setattr__(self, "_fields", dict(data))

    def __getattr__(self, name):
        # 只有常规属性查找失败时才会走到这里
        fields = object.__getattribute__(self, "_fields")
        if name in fields:
            return fields[name]
        raise AttributeError(f"FlexibleRecord 没有属性 {name!r}")

    def add(self, name: str, value):
        """运行期新增一个字段。"""
        self._fields[name] = value

    def __repr__(self):
        return f"FlexibleRecord({self._fields!r})"


if __name__ == "__main__":
    r = FlexibleRecord({"name": "Alice", "score": 90})
    print(r.name)              # Alice
    print(r.score)             # 90

    r.add("city", "Shanghai") # 动态添加
    print(r.city)              # Shanghai

    try:
        print(r.height)        # 不存在
    except AttributeError as e:
        print("捕获异常：", e)

    # 顺带演示给实例挂方法
    def hello(self):
        return f"Hi, {self.name}"

    r.greet = types.MethodType(hello, r)
    print(r.greet())           # Hi, Alice
```

## py.meta.getattr

# py.meta.getattr 教学讲义

## 一句话直觉

`getattr` 让你用「字符串名字」去拿对象的属性，还能在属性不存在时给个默认值——这是 Python 元编程（metaprogramming）的起点，也是框架、ORM、序列化库、插件系统每天都在用的核心工具。

---

## 1. 为什么需要 getattr？

普通写法 `obj.name` 要求你在写代码时就知道属性名。但很多场景下属性名是**运行时才知道的**：

- 配置系统：`config.get(key)`
- 序列化：把 dict 的键映射到对象属性
- 插件加载：根据字符串调用不同方法
- 框架：Django ORM 的 `Model.objects.filter(**kwargs)`

`getattr(object, name[, default])` 就是解决这个问题的内置函数（built-in function）。

```python
class User:
    def __init__(self, name, age):
        self.name = name
        self.age = age

u = User("Alice", 30)

# 普通访问
print(u.name)                    # Alice

# 字符串访问——getattr 的威力
key = "age"
print(getattr(u, key))           # 30

# 属性不存在时给默认值
print(getattr(u, "email", "N/A")) # N/A
```

---

## 2. getattr 的签名与行为

```python
getattr(object, name[, default])
```

- `object`：任意对象（实例、类、模块、函数……）
- `name`：字符串，属性名
- `default`：可选。若省略，属性不存在会抛 `AttributeError`

```python
class Config:
    debug = True

c = Config()

# 存在
print(getattr(c, "debug"))         # True

# 不存在 + 有默认值
print(getattr(c, "host", "localhost"))  # localhost

# 不存在 + 无默认值 → 抛异常
try:
    getattr(c, "missing")
except AttributeError as e:
    print("AttributeError:", e)
```

> 关键点：`getattr` 的查找顺序和 `obj.name` 完全一致——先实例字典（instance `__dict__`），再类及继承链，最后走 `__getattr__` / `__getattribute__` 钩子。

---

## 3. 与相关 API 的关系

`getattr` 是一个家族的一员，理解它们的分工很重要：

| 函数 | 用途 |
|------|------|
| `getattr(obj, name, default)` | 读属性 |
| `setattr(obj, name, value)` | 写属性 |
| `hasattr(obj, name)` | 判断属性是否存在（内部调用 `getattr` 捕获异常） |
| `delattr(obj, name)` | 删除属性 |

```python
class Box:
    pass

b = Box()
setattr(b, "color", "red")
print(hasattr(b, "color"))    # True
print(getattr(b, "color"))    # red
delattr(b, "color")
print(hasattr(b, "color"))    # False
```

典型应用：把 dict 转为对象属性。

```python
data = {"host": "127.0.0.1", "port": 8080, "debug": True}

class Settings:
    pass

s = Settings()
for k, v in data.items():
    setattr(s, k, v)

for k in data:
    print(k, "=", getattr(s, k))
```

---

## 4. 工程级用法：动态分发与方法调用

`getattr` 最常见的工程模式是「根据字符串找方法并调用」，这也是插件系统、命令行的底层机制。

```python
class Calculator:
    def add(self, a, b): return a + b
    def sub(self, a, b): return a - b
    def mul(self, a, b): return a * b

def dispatch(calc, op_name, a, b):
    # 安全取方法，找不到就返回 None
    method = getattr(calc, op_name, None)
    if method is None or not callable(method):
        raise ValueError(f"Unknown op: {op_name}")
    return method(a, b)

c = Calculator()
print(dispatch(c, "add", 3, 4))   # 7
print(dispatch(c, "mul", 3, 4))   # 12
```

`getattr` 也是 PEP 698 中 `@override` 装饰器的运行时检查手段：装饰器会在被装饰对象上设置 `__override__ = True`，之后可用 `getattr(obj, "__override__", False)` 在运行时判断某个方法是否被标记为覆写。

---

## 5. 与 `__getattr__` 钩子的配合

当你定义一个类并实现 `__getattr__(self, name)` 时，只有在**常规属性查找失败之后**，Python 才会调用它。`getattr(obj, name, default)` 遇到缺失属性时，如果类定义了 `__getattr__`，会先走这个钩子；钩子若再抛 `AttributeError`，才会返回 `default`。

```python
class Defaults:
    def __getattr__(self, name):
        # 只有缺失的属性才会走到这里
        return f"<default:{name}>"

d = Defaults()
print(d.foo)                      # <default:foo>
print(getattr(d, "bar"))          # <default:bar>
print(getattr(d, "baz", "X"))     # <default:baz>  注意 default 不会被用到
```

> 这是很多框架实现「配置默认值」「代理对象」「懒加载属性」的基础。

---

## 动手练习

**任务：写一个 `DotDict` 类，让嵌套字典可以用点号访问，并且缺失键返回 `None` 而不报错。**

要求：
1. 初始化时接收一个普通 dict。
2. 访问 `obj.key` 时，如果 value 是 dict，自动包装成 `DotDict`。
3. 访问不存在的键返回 `None`（用 `__getattr__` + `getattr` 的默认值思想实现）。
4. 提供 `to_dict()` 方法还原成普通 dict。

参考骨架：

```python
class DotDict:
    def __init__(self, data):
        self._data = data

    def __getattr__(self, name):
        ...

    def to_dict(self):
        ...

cfg = DotDict({"db": {"host": "localhost", "port": 5432}})
print(cfg.db.host)      # localhost
print(cfg.db.port)      # 5432
print(cfg.missing)      # None
```

完成后思考：为什么 `__getattr__` 里不能直接写 `self._data`？提示：`__init__` 之前被调用的边界情况。

```python
class User:
    def __init__(self, name, age):
        self.name = name
        self.age = age


u = User("Alice", 30)

# 1) 用字符串名读取属性
key = "age"
assert getattr(u, key) == 30

# 2) 缺失属性给默认值，避免崩溃
assert getattr(u, "email", "N/A") == "N/A"

# 3) 缺失且无默认值会抛 AttributeError
try:
    getattr(u, "missing")
except AttributeError:
    pass
else:
    raise AssertionError("should have raised")

# 4) 与 hasattr / setattr / delattr 配合
setattr(u, "role", "admin")
assert hasattr(u, "role") is True
assert getattr(u, "role") == "admin"
delattr(u, "role")
assert hasattr(u, "role") is False

# 5) 动态方法分发：根据字符串调用方法
class Calculator:
    def add(self, a, b): return a + b
    def sub(self, a, b): return a - b

def dispatch(calc, op_name, a, b):
    method = getattr(calc, op_name, None)
    if not callable(method):
        raise ValueError(f"Unknown op: {op_name}")
    return method(a, b)

c = Calculator()
assert dispatch(c, "add", 3, 4) == 7
assert dispatch(c, "sub", 3, 4) == -1

# 6) 与 __getattr__ 钩子配合：缺失属性走自定义逻辑
class Defaults:
    def __getattr__(self, name):
        return f"<default:{name}>"

d = Defaults()
assert d.foo == "<default:foo>"
assert getattr(d, "bar") == "<default:bar>"
# __getattr__ 已经处理了缺失，所以 default 不会生效
assert getattr(d, "baz", "X") == "<default:baz>"

print("All assertions passed.")
```


---

## 本课题目

### single_choice · None



- [A] 10
- [B] AttributeError
- [C] None
- [D] 报错：实例不能动态添加属性

**参考答案**：0

**解析**：普通类的实例默认支持动态添加属性，赋值 a.x = 10 后即可通过 a.x 访问。

### single_choice · None



- [A] 禁止该类实例动态添加未在 __slots__ 中声明的属性
- [B] 禁止该类的方法被重写
- [C] 禁止类被继承
- [D] 自动把所有属性变成只读

**参考答案**：0

**解析**：定义了 __slots__ 后，实例只能拥有其中声明的属性，无法再动态添加新属性。

### single_choice · None



- [A] 两者效果相同，属性名都可以使用动态字符串
- [B] 前者要求类必须定义 __slots__
- [C] 后者不可以动态设置属性名
- [D] 前者不能触发 __setattr__

**参考答案**：0

**解析**：setattr(obj, 'x', 1) 与 obj.x = 1 等价，都能动态设置属性，也会触发 __setattr__。

### single_choice · None



- [A] 'missing'
- [B] AttributeError
- [C] None
- [D] ''

**参考答案**：0

**解析**：getattr 的第三个参数是默认值，当属性不存在时返回默认值 'missing'。

### single_choice · None



- [A] 没有，除非显式在 __slots__ 中包含 '__dict__'
- [B] 有，始终存在
- [C] 有，但为空字典
- [D] 取决于是否继承自 object

**参考答案**：0

**解析**：默认情况下 __slots__ 会阻止实例创建 __dict__，只有显式声明 '__dict__' 时才保留。

### single_choice · None



- [A] 数据描述符优先于实例字典，实例字典优先于非数据描述符
- [B] 实例字典优先于所有描述符
- [C] 类属性总是优先于实例属性
- [D] 非数据描述符优先于实例字典

**参考答案**：0

**解析**：属性查找顺序大致为：数据描述符 > 实例 __dict__ > 非数据描述符/类属性 > __getattr__。

### single_choice · None



- [A] 2 1
- [B] 1 1
- [C] 2 2
- [D] 1 2

**参考答案**：0

**解析**：给实例赋值会创建实例属性 x=2，不影响类属性 A.x=1。

### single_choice · None



- [A] AttributeError: x
- [B] None
- [C] ''
- [D] 不会报错，输出 'x'

**参考答案**：0

**解析**：__getattr__ 显式抛出 AttributeError 时，属性访问失败并显示异常信息。

### single_choice · None



- [A] 访问已存在于实例字典中的属性，避免再次触发 __getattr__
- [B] 删除属性
- [C] 设置新属性
- [D] 调用父类的 __getattr__

**参考答案**：0

**解析**：由于 __getattr__ 只在属性查找失败时调用，直接访问 __dict__ 可绕过属性协议获取已有值。

### single_choice · None



- [A] 5
- [B] AttributeError
- [C] None
- [D] TypeError

**参考答案**：0

**解析**：直接操作实例 __dict__ 也能设置属性，效果与普通赋值相同。

### single_choice · None



- [A] 等价于 obj.__dict__，返回实例属性字典
- [B] 返回类属性字典
- [C] 返回所有可调用属性
- [D] 返回属性名列表

**参考答案**：0

**解析**：vars(obj) 返回 obj.__dict__，即实例的动态属性字典。

### single_choice · None



- [A] 1
- [B] AttributeError
- [C] None
- [D] TypeError

**参考答案**：0

**解析**：__slots__ 中声明的 'x' 可以在 __init__ 中正常赋值和访问。

### single_choice · None



- [A] 1
- [B] AttributeError
- [C] None
- [D] TypeError

**参考答案**：1

**解析**：因为 A 定义了 __slots__ 且未包含 'y'，所以给 a.y 赋值会抛出 AttributeError。

### single_choice · None



- [A] 存储在实例的 __dict__ 字典中
- [B] 存储在类的 __dict__ 中
- [C] 存储在 __slots__ 中
- [D] 存储在全局命名空间中

**参考答案**：0

**解析**：普通实例的动态属性保存在自身的 __dict__ 属性字典里，类的 __dict__ 保存类属性和方法。

### single_choice · None



- [A] {'x': 1, 'y': 2}
- [B] {'x': 1}
- [C] {'y': 2}
- [D] {}

**参考答案**：0

**解析**：动态赋值会依次写入实例的 __dict__，因此包含 x 和 y 两个键。

### single_choice · None



- [A] 'default'
- [B] AttributeError
- [C] None
- [D] 不会输出任何内容

**参考答案**：0

**解析**：当访问不存在的属性时会调用 __getattr__，这里返回 'default'。

### single_choice · None



- [A] __getattr__ 仅在属性常规查找失败时调用，__getattribute__ 对每次属性访问都调用
- [B] 两者完全等价，可以互换使用
- [C] __getattribute__ 仅在属性不存在时调用
- [D] __getattr__ 会对每次属性访问都调用

**参考答案**：0

**解析**：__getattribute__ 拦截所有属性访问，只有常规查找失败时才回退到 __getattr__。

### single_choice · None



- [A] setting x
- [B] 没有任何输出
- [C] AttributeError
- [D] TypeError

**参考答案**：0

**解析**：__setattr__ 在每次属性赋值时被调用，这里打印 'setting x' 后调用父类实现完成赋值。

### single_choice · None



- [A] 递归调用导致无限递归
- [B] 正常执行，x 被赋值为 1
- [C] 抛出 AttributeError
- [D] 抛出 TypeError

**参考答案**：0

**解析**：在 __setattr__ 内使用 self.name = value 会再次触发 __setattr__，造成无限递归。应使用 super().__setattr__ 或 object.__setattr__。

### single_choice · None



- [A] deleting x
- [B] 没有任何输出
- [C] AttributeError
- [D] 不会删除属性

**参考答案**：0

**解析**：del a.x 会触发 __delattr__，打印 'deleting x' 后由父类实现真正删除。

### single_choice · None



- [A] 直接抛出 AttributeError，不做任何额外尝试
- [B] 先查找实例字典，再查找类属性，最后尝试调用类的 __getattr__ 方法
- [C] 只在类中查找，实例字典不参与
- [D] 先调用 __getattribute__，若其内部抛出 AttributeError，再调用 __getattr__

**参考答案**：3

**解析**：属性访问总是先经过 __getattribute__；只有当它在查找失败时抛出 AttributeError，解释器才会回退调用 __getattr__。__getattr__ 是查找失败后的钩子，而不是最先被调用的。

### single_choice · None



- [A] 两者完全等价，只是名字不同
- [B] __getattr__ 在每次属性访问时都被调用，__getattribute__ 只在属性不存在时调用
- [C] __getattribute__ 处理所有属性访问，__getattr__ 只在该访问失败（抛 AttributeError）后作为后备被调用
- [D] __getattr__ 只能处理方法，不能处理数据属性

**参考答案**：2

**解析**：__getattribute__ 是所有属性访问的入口，__getattr__ 是失败后的兜底机制。二者调用频率和触发条件不同。

### single_choice · None



- [A] __getattr__ 必须返回 None，否则报错
- [B] __getattr__ 可以返回任意对象，该返回值即作为属性访问的结果
- [C] __getattr__ 只能返回字符串
- [D] __getattr__ 不能返回值，只能抛出异常

**参考答案**：1

**解析**：__getattr__ 的返回值就是属性访问表达式的值，可以是任意类型；若它抛 AttributeError，则属性访问最终失败。

### multi_choice · None



- [A] 访问对象上确实不存在的属性，且类中定义了 __getattr__
- [B] 访问对象的类属性，该属性存在
- [C] 对象的 __getattribute__ 因属性缺失而抛出 AttributeError
- [D] 访问对象上存在的实例属性

**参考答案**：[0, 2]

**解析**：__getattr__ 仅在常规属性查找失败（__getattribute__ 抛 AttributeError）时被调用。属性存在（无论实例还是类属性）时不会触发。

### multi_choice · None



- [A] 当属性存在时返回属性值
- [B] 当属性不存在且提供了 default 时返回 default
- [C] 当属性不存在且未提供 default 时抛出 AttributeError
- [D] getattr 总是会触发 __getattr__，即使属性存在

**参考答案**：[0, 1, 2]

**解析**：getattr 在属性存在时返回其值，缺失时返回默认值或抛 AttributeError。它并不会在属性存在时触发 __getattr__。

### multi_choice · None



- [A] __getattribute__ 在每次属性访问时都被调用
- [B] __getattr__ 只在属性查找失败后作为后备被调用
- [C] 两者在属性存在时都会被执行
- [D] 在 __getattr__ 中调用 object.__getattribute__ 可以帮助避免递归

**参考答案**：[0, 1, 3]

**解析**：__getattribute__ 是入口，每次访问都调用；__getattr__ 是失败后的后备。属性存在时不会执行 __getattr__。使用 object.__getattribute__ 可绕过自定义逻辑从而避免递归。

### fill_blank · None



**参考答案**：["__getattr__", "__getattr__()"]

**解析**：__getattr__ 是属性查找失败后的钩子，接收属性名字符串作为参数。

### fill_blank · None



**参考答案**：["getattr", "getattr()"]

**解析**：getattr(obj, name, default) 是内置函数，提供默认值可避免 AttributeError。

### code_reading · None



**参考答案**：{'error': 'oops'}

**解析**：访问 lg.log_error 时，log_error 未在实例或类中找到，触发 __getattr__('log_error')。name 以 'log_' 开头，返回一个 lambda，该 lambda 把 name[4:] 即 'error' 作为键，把 'oops' 存入 _data，因此输出 {'error': 'oops'}。

### scenario · None



**解析**：应实现 __getattr__ 方法（而不是 __getattribute__），在其中用传入的属性名去查字典：存在则返回对应值；不存在时记录警告并返回 None，而不是抛 AttributeError。因为 __getattr__ 只在常规查找失败时触发，正好符合“字典里没有才兜底”的需求。

### scenario · None



**解析**：在 __getattr__ 内部访问 self.__dict__ 时，若 __dict__ 本身也触发了失败查找，就会再次进入 __getattr__，从而递归。修复方案：一是指向确实存在的属性，如用 object.__getattribute__(self, '__dict__') 或用 __name__ 之外的稳定方式访问；二是直接在 __getattr__ 中访问已经保存在局部或通过 object.__getattribute__ 获取的属性，避免再次触发失败查找。

### single_choice · None



- [A] 返回 None
- [B] 抛出 AttributeError
- [C] 抛出 KeyError
- [D] 返回一个空字符串

**参考答案**：1

**解析**：getattr 有三个参数形式；不提供默认值时，属性缺失会抛出 AttributeError，这与直接点号访问失败一致。提供了 default 才返回默认值。

### single_choice · None



- [A] 抛出 AttributeError
- [B] foo
- [C] default_foo
- [D] None

**参考答案**：2

**解析**：实例 a 没有 foo 属性，常规查找失败后触发 __getattr__('foo')，返回 'default_foo'。

### single_choice · None



- [A] Python 自动返回 None
- [B] 无限递归，最终抛出 RecursionError
- [C] 静默忽略该次访问
- [D] 触发 __getattribute__ 而不进入 __getattr__

**参考答案**：1

**解析**：若 __getattr__ 内部又触发了对不存在属性的访问，会再次进入 __getattr__，形成递归，超过递归深度后抛 RecursionError。常见修复是访问已知存在的属性或使用 object.__getattribute__。

### single_choice · None



- [A] getattr 内置函数只会调用 __getattr__ 方法，不经过 __getattribute__
- [B] getattr 内置函数触发的属性查找流程与点号访问一致，都会先经过 __getattribute__，必要时再进入 __getattr__
- [C] getattr 内置函数绕过所有魔法方法
- [D] __getattr__ 只在 getattr 内置函数被调用时触发，点号访问不会触发

**参考答案**：1

**解析**：getattr(obj, name) 与 obj.name 的查找语义相同，都遵循 __getattribute__ 优先、失败后回退 __getattr__ 的流程。

### single_choice · None



- [A] 10
- [B] missing
- [C] default
- [D] None

**参考答案**：0

**解析**：x 是类属性，能正常查找到，不会触发 __getattr__，因此返回 10。默认值 'default' 也不会用到。

### single_choice · None



- [A] 两个方法都会被调用
- [B] 只调用 __getattribute__，__getattr__ 不参与
- [C] 只调用 __getattr__
- [D] 先调用 __getattr__ 再调用 __getattribute__

**参考答案**：1

**解析**：属性存在时 __getattribute__ 成功返回，不抛异常，因此不会回退到 __getattr__。只有 __getattribute__ 失败（抛 AttributeError）才会触发 __getattr__。

### single_choice · None



- [A] 强制类型转换
- [B] 对未定义属性做动态代理或提供默认行为
- [C] 替代 __init__ 进行实例初始化
- [D] 实现多重继承的方法解析顺序

**参考答案**：1

**解析**：__getattr__ 只在属性查找失败时被调用，适合做动态代理、懒加载或为缺失属性提供默认值等场景。

### single_choice · None



- [A] FOO
- [B] foo
- [C] 抛出 AttributeError
- [D] None

**参考答案**：0

**解析**：访问 d.foo，foo 属性不存在，进入 __getattr__('foo')，name != 'missing'，返回 'foo'.upper() 即 'FOO'。
