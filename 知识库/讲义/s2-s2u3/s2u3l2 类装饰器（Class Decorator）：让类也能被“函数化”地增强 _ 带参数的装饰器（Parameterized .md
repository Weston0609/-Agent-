# s2u3l2 类装饰器（Class Decorator）：让类也能被“函数化”地增强 / 带参数的装饰器（Parameterized Decorator）

> 来源 `content/lessons/s2u3l2.json`

## py.deco.class_deco

# 类装饰器（Class Decorator）：让类也能被“函数化”地增强

> 一句话直觉：**类装饰器就是“接收一个类、返回一个类”的可调用对象**，它让我们能在不改动原类源码的前提下，为类批量添加属性、方法、注册、校验或改写行为——就像函数装饰器装饰函数一样自然。

---

## 一、从函数装饰器说起：装饰器到底是什么？

装饰器（decorator）本质是一个**可调用对象**，它接收一个可调用对象，返回一个新的可调用对象。语法糖 `@deco` 等价于 `f = deco(f)`。

```python
# 最朴素的函数装饰器
def trace(func):
    def wrapper(*args, **kwargs):
        print(f"[call] {func.__name__}")
        return func(*args, **kwargs)
    return wrapper

@trace
def add(a, b):
    return a + b

add(1, 2)   # 输出: [call] add  -> 返回 3
```

**关键结论**：装饰器的输入和输出“形状”是一样的。函数进、函数出；那么**类进、类出**，就是类装饰器。

---

## 二、类装饰器的定义与最小示例

类装饰器就是“参数是类、返回值也是类”的可调用对象。因为 Python 里“类本身也是对象”（一切皆对象），所以把它当参数传递完全合法。

```python
# 最小类装饰器：为类动态添加一个类属性
def add_version(cls):
    cls.version = "1.0.0"   # 直接修改原类并返回
    return cls

@add_version
class Service:
    pass

print(Service.version)      # 1.0.0
```

也可以返回一个**全新的类**（而不是修改原类）：

```python
def wrap_repr(cls):
    class Wrapped(cls):                  # 继承原类，构造新类
        def __repr__(self):
            return f"<{cls.__name__} wrapped>"
    Wrapped.__name__ = cls.__name__      # 保持名字一致，方便调试
    return Wrapped

@wrap_repr
class User:
    pass

print(User())    # <User wrapped>
```

**关键结论**：类装饰器有两种常见策略——
1. **原地修改**：改 `cls` 的属性后 `return cls`；
2. **包装替换**：新建一个类（通常是子类）后返回它。

---

## 三、典型用法一：批量注册（Registry 模式）

工程里最常见的类装饰器用途是“把类登记到一个全局字典”，比如插件系统、模型工厂、命令分发。

```python
# 一个简单的注册表：类名 -> 类对象
REGISTRY = {}

def register(cls):
    REGISTRY[cls.__name__] = cls
    return cls

@register
class Add:
    def run(self, a, b): return a + b

@register
class Mul:
    def run(self, a, b): return a * b

# 根据名字动态取出类并实例化
op = REGISTRY["Add"]()
print(op.run(2, 3))    # 5
print(list(REGISTRY))  # ['Add', 'Mul']
```

**关键结论**：注册类装饰器的价值在于**解耦**——使用处不需要 `import` 每一个具体类，只需查表即可。

---

## 四、典型用法二：不修改源码，为类批量加能力

例如统一给类加上 `__eq__`、日志方法、序列化方法，或做参数校验。下面这个装饰器给类加一个“把实例转成字典”的方法：

```python
import functools

def add_to_dict(cls):
    @functools.wraps(cls, updated=())   # 保留原类元信息
    def to_dict(self):
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}
    cls.to_dict = to_dict
    return cls

@add_to_dict
class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

print(Point(1, 2).to_dict())   # {'x': 1, 'y': 2}
```

**关键结论**：类装饰器让“横切能力”（日志、注册、校验、序列化）集中在装饰器里，业务类保持干净。

---

## 五、带参数的类装饰器：工厂的三层结构

如果装饰器需要参数（例如 `@register("math")`），就要写成“**返回类装饰器的函数**”——三层嵌套。

```python
REGISTRY = {}

def register(category):                  # 第一层：接收参数
    def deco(cls):                        # 第二层：接收类
        REGISTRY.setdefault(category, {})[cls.__name__] = cls
        return cls
    return deco                           # 返回类装饰器

@register("math")
class Add: pass

@register("math")
class Mul: pass

@register("text")
class Upper: pass

print(REGISTRY["math"].keys())   # dict_keys(['Add', 'Mul'])
print(REGISTRY["text"].keys())   # dict_keys(['Upper'])
```

**关键结论**：记住模式——`参数 -> 类 -> 新类` 的层层返回，和带参数的函数装饰器完全同构。

---

## 六、类装饰器 vs 继承 vs 元类（metaclass）

- **继承**：子类可以覆写父类，但需要改业务代码。
- **类装饰器**：不改业务代码，一次装饰即可横切增强，适合注册、日志、校验。
- **元类**：控制“类的创建过程”，能力更强也更底层，复杂度高。

**工程选型建议**：能用装饰器解决就不要上元类；能用组合解决就不要上装饰器。类装饰器的最佳落点是**注册表、插件发现、统一附加方法**。

---

## 动手练习（本地可完成）

> 目标：写一个类装饰器 `@command(name)`，把类注册到一个 `COMMANDS` 字典里，并给它自动加上一个 `name` 类属性。

**要求：**
1. 定义 `COMMANDS = {}`；
2. 写 `command(name)`，返回一个类装饰器；
3. 装饰器把 `cls.name = name`，并执行 `COMMANDS[name] = cls`，然后返回 `cls`；
4. 用 `@command("add")` 装饰一个 `Add` 类，用 `@command("mul")` 装饰 `Mul` 类；
5. 打印 `COMMANDS` 的 key 列表；通过 `COMMANDS["add"]()` 实例化并调用它的 `run(2,3)`，应当返回 5。

**验收**：运行脚本后 `COMMANDS` 至少包含 `add`、`mul` 两个 key，且 `COMMANDS["add"]().run(2, 3) == 5`。

**加分项**：给装饰器加一个 `functools.wraps(cls, updated=())` 来保留原类的 `__doc__` 与 `__name__`。

```python
"""
演示：带参数的类装饰器实现"命令注册表"。
运行后输出注册表内容和一次调用结果。
"""
import functools

COMMANDS = {}

def command(name):
    """接收命令名，返回一个类装饰器。"""
    def deco(cls):
        # 把命令名挂到类上，方便运行时自省
        cls.name = name
        COMMANDS[name] = cls
        # 保留原类元信息（updated=() 避免覆盖 __dict__ 之类）
        @functools.wraps(cls, updated=())
        def _keep():
            pass
        return cls
    return deco

@command("add")
class Add:
    def run(self, a, b):
        return a + b

@command("mul")
class Mul:
    def run(self, a, b):
        return a * b

if __name__ == "__main__":
    print("registered:", list(COMMANDS.keys()))
    print("add(2,3) =", COMMANDS["add"]().run(2, 3))
    print("mul(2,3) =", COMMANDS["mul"]().run(2, 3))
```

## py.deco.param_deco

# 带参数的装饰器（Parameterized Decorator）

> **一句话直觉**：普通装饰器像「一次性贴纸」，贴上就固定了；带参数的装饰器像「可调旋钮的贴纸工厂」——你先把参数交给它，它再返回一个真正能贴的贴纸。这一点对 AI 工程至关重要：写训练日志、重试、计时、限流时，你几乎一定需要「可配置」的装饰器。

学习本讲后，你将能：理解装饰器的求值顺序、掌握三层嵌套工厂写法、用 `functools.wraps` 保留元数据、并写出工程可用的 `@retry(times=3, delay=0.5)`。

---

## 0. 预备：不加参数的装饰器（Decorator）复习

装饰器本质是「接收函数、返回函数」的高阶函数（higher-order function）。

```python
# 普通装饰器：没有额外参数，直接包一层
def simple_log(func):
    def wrapper(*args, **kwargs):
        print(f"[call] {func.__name__}")
        return func(*args, **kwargs)
    return wrapper

@simple_log
def add(a, b):
    return a + b

# 等价于：add = simple_log(add)
print(add(1, 2))  # [call] add  ->  3
```

关键等价式：`@simple_log` 就等于 `add = simple_log(add)`。这是理解一切装饰器（包括带参的）的基础。

---

## 1. 为什么需要「带参数的装饰器」？

普通装饰器写死了行为：

```python
def log_to_stdout(func): ...       # 只能打到 stdout
def log_to_file(func): ...         # 只能打到文件
```

但你想要的是「同一个装饰器，通过参数选择行为」：

```python
@log(where="file", path="run.log")
def train(): ...
```

这就意味着装饰器本身要先接收参数，再返回真正的装饰器。多出来的这一层，就是带参装饰器。

---

## 2. 核心结构：三层嵌套

带参数的装饰器一定是「**三层结构**」：

```
第 1 层：接收配置参数      -> 返回装饰器
第 2 层：接收被装饰的函数  -> 返回包装器
第 3 层：接收调用时实参    -> 执行原函数并加行为
```

```python
import functools

def repeat(times):                       # 1. 接收装饰器参数
    def decorator(func):                 # 2. 接收被装饰函数
        @functools.wraps(func)           #    保留函数元信息
        def wrapper(*args, **kwargs):    # 3. 接收调用实参
            for _ in range(times):
                result = func(*args, **kwargs)
            return result
        return wrapper
    return decorator

@repeat(times=3)
def greet(name):
    print(f"Hi, {name}!")

greet("Ada")
# 求值顺序：
#   repeat(times=3)  ->  decorator
#   decorator(greet) ->  wrapper
#   greet("Ada")     ->  wrapper("Ada")
```

请记住这句口诀：**「参数在最外层，函数在第二层，调用在第三层」**。看到它，你就知道这是带参装饰器。

---

## 3. `functools.wraps` 为什么必须加

不加 `functools.wraps`，被装饰函数的 `__name__`、`__doc__`、签名信息会被 `wrapper` 覆盖，导致调试、日志、文档、`inspect.signature` 全部失真。

```python
import functools

def bad(times):
    def deco(func):
        def wrapper(*a, **k):
            return func(*a, **k)
        return wrapper
    return deco

def good(times):
    def deco(func):
        @functools.wraps(func)   # 关键一行
        def wrapper(*a, **k):
            return func(*a, **k)
        return wrapper
    return deco

@bad(1)
def f(): "docstring"

@good(1)
def g(): "docstring"

print(f.__name__, f.__doc__)  # wrapper None   <- 元信息丢失
print(g.__name__, g.__doc__)  # f docstring   <- 保留
```

工程级建议：**任何装饰器第一行就写 `@functools.wraps(func)`**，没有例外。

---

## 4. 工程级范例：`@retry` 重试装饰器

这是带参装饰器最典型的工业用法（网络请求、GPU 显存抖动、分布式训练下载数据等场景）。

```python
import functools, time, random

def retry(times=3, delay=0.1, exceptions=(Exception,)):
    """失败自动重试。times: 最多重试次数；delay: 每次间隔秒数。"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_err = None
            for attempt in range(1, times + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_err = e
                    print(f"[retry] {func.__name__} attempt {attempt}/{times} failed: {e}")
                    if attempt < times:
                        time.sleep(delay)
            raise last_err
        return wrapper
    return decorator

@retry(times=3, delay=0.05)
def flaky():
    if random.random() < 0.7:
        raise RuntimeError("transient failure")
    return "ok"

print(flaky())
```

---

## 5. 进阶：带默认参数、可「无参」调用的装饰器

工程中经常希望 `@retry` 和 `@retry(times=5)` 都能用。技巧是：判断第一个参数是不是函数。

```python
import functools, time

def retry(_func=None, *, times=3, delay=0.05):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*a, **k):
            for attempt in range(1, times + 1):
                try:
                    return func(*a, **k)
                except Exception as e:
                    if attempt == times: raise
                    time.sleep(delay)
        return wrapper

    if _func is None:
        return decorator            # 带参用法: @retry(times=5)
    return decorator(_func)         # 无参用法: @retry

@retry
def a(): return 1

@retry(times=5)
def b(): return 2
```

---

## 6. 常见误区（Pitfalls）

1. **层数写错**：`@deco(arg)` 必须先返回装饰器；写成两层却在装饰器上加参数，会直接报 `'function' object is not callable`。
2. **忘记 `functools.wraps`**：导致 `__name__` 变成 `wrapper`，日志和 traceback 全部走样。
3. **可变默认参数**：`def deco(func, cache={})` 是经典陷阱，应使用 `None` 再在函数体内初始化。
4. **装饰器内阻塞**：`time.sleep`、网络等待写在 wrapper 里会拖慢同步调用；异步场景要用 `async def wrapper` 配套。
5. **丢失签名**：静态类型检查器（mypy）和 IDE 无法推断。补充 `ParamSpec` + `TypeVar` 才能真正类型安全。

```python
from typing import Callable, TypeVar, ParamSpec
import functools

P = ParamSpec("P"); R = TypeVar("R")

def logged(func: Callable[P, R]) -> Callable[P, R]:
    @functools.wraps(func)
    def wrapper(*a: P.args, **k: P.kwargs) -> R:
        print(f"call {func.__name__}")
        return func(*a, **k)
    return wrapper
```

---

## 7. 动手练习（本地完成）

**任务**：实现一个带参数的装饰器 `@timing(unit="ms")`，作用于任意函数。

- 支持 `unit="s" | "ms" | "us"` 三种单位；
- 打印格式：`[timing] <func_name> took <value> <unit>`；
- 保留原函数的 `__name__` 和 `__doc__`；
- 用它对一个 `time.sleep(0.01)` 的函数做测试，验证输出与单位换算正确；
- 加分：加 `@timing`（不带括号）也能用，实现「可选参数」装饰器。

参考骨架（自己补全，不要直接抄）：

```python
import functools, time

def timing(_func=None, *, unit="ms"):
    scale = {"s": 1.0, "ms": 1e3, "us": 1e6}[unit]
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*a, **k):
            t0 = time.perf_counter()
            try:
                return func(*a, **k)
            finally:
                dt = (time.perf_counter() - t0) * scale
                print(f"[timing] {func.__name__} took {dt:.3f} {unit}")
        return wrapper
    return decorator if _func is None else decorator(_func)
```


---

## 本课题目

### single_choice · None



- [A] 类装饰器必须继承自 object，否则无法调用
- [B] 只要类实现了 __call__ 方法，它的实例就可以像函数一样被调用，从而用作装饰器
- [C] 类装饰器只能装饰类，不能装饰函数
- [D] 类装饰器中必须定义 __init__ 和 __enter__ 两个方法

**参考答案**：1

**解析**：类装饰器的本质是让类的实例可调用，因此需要实现 __call__ 方法。__init__ 用于接收被装饰的函数，__call__ 用于执行包装逻辑。继承 object、__enter__ 都不是必要条件，类装饰器既可以装饰函数也可以装饰类。

### single_choice · None



- [A] 始终为 0，因为 count 是类属性
- [B] 每次调用 greet() 时 +1，三次后为 3
- [C] 每次调用 greet() 时 +1，但因为每次都会新建实例，所以始终为 1
- [D] 调用 greet() 不经过 __call__，因此 count 不变

**参考答案**：1

**解析**：使用 @CountCalls 装饰后，greet 这个名字绑定的是 CountCalls 的一个实例，而不是原函数。调用 greet() 实际调用实例的 __call__，每次都会给同一个实例的 self.count 加 1，所以三次后为 3。

### single_choice · None



- [A] 被装饰后，函数名仍然指向原来的函数对象
- [B] 被装饰后，函数名指向类装饰器的实例
- [C] 被装饰后，函数名指向类本身
- [D] 被装饰后，原函数会被自动删除

**参考答案**：1

**解析**：@Deco 等价于 foo = Deco(foo)，所以 foo 这个名字最终绑定到 Deco 的实例。原函数对象仍然被实例引用，并没有被删除，但函数名不再指向它。

### single_choice · None



- [A] 'hi'
- [B] '<b>hi</b>'
- [C] '<b>text</b>'
- [D] 会报 TypeError，因为 __call__ 不能接收参数

**参考答案**：1

**解析**：text 被替换为 Tag 实例。text('hi') 调用实例的 __call__('hi')，其中 self.func 是原函数，返回 'hi'，再被包裹为 '<b>hi</b>'。选项 D 错误，__call__ 接受了 *args。

### single_choice · None



- [A] 只需要 __init__
- [B] __init__ 和 __call__
- [C] __init__、__call__ 和 __enter__
- [D] __new__ 和 __del__

**参考答案**：1

**解析**：__init__ 用于保存被装饰的函数或参数，__call__ 使实例可调用，从而完成装饰和调用逻辑。__enter__/__exit__ 是上下文管理器协议，__new__/__del__ 与装饰器功能无直接关系。

### single_choice · None



- [A] 统计函数被调用的次数
- [B] 为函数结果添加缓存
- [C] 在函数调用前后记录日志
- [D] 修改函数的字节码以提升运行速度

**参考答案**：3

**解析**：类装饰器常用于添加计数、缓存、日志等横切逻辑。直接修改函数字节码不是装饰器的常规用途，装饰器通常在调用层面进行包装，而不是改写代码对象。

### single_choice · None



- [A] class Deco:
      def __init__(self, func):
          self.func = func
      def __call__(self, *args, **kwargs):
          return self.func(*args, **kwargs)
- [B] class Deco:
      def __init__(self, func):
          self.func = func
      def __call__(self):
          return self.func()
- [C] class Deco:
      def __init__(self, func):
          self.func = func
      def __call__(self, self_):
          return self.func(self_)
- [D] class Deco:
      def __init__(self, func):
          self.func = func
      def __call__(self, *args):
          return self.func()

**参考答案**：0

**解析**：方法被装饰后，调用时解析器会把实例作为第一个参数传入。装饰器实例的 __call__ 必须用 *args, **kwargs 接收并原样转发给原函数，才能保留 self 和其他参数。其他选项要么不接收参数，要么丢弃参数，都会破坏调用。

### single_choice · None



- [A] 可以装饰任意签名的函数而不必关心具体参数
- [B] 可以让装饰器实例自动变成生成器
- [C] 可以避免定义 __init__
- [D] 可以省略 functools.wraps

**参考答案**：0

**解析**：使用 *args, **kwargs 接收任意位置参数和关键字参数，再原样转发给被装饰函数，可以适配各种签名的函数。它与生成器、省略 __init__、替代 functools.wraps 都没有关系。

### single_choice · None



- [A] 同一个被装饰函数对应的装饰器实例只有一个，状态在多次调用之间保持
- [B] 每次调用被装饰函数都会新建一个装饰器实例
- [C] 装饰器实例的属性在调用后被自动重置
- [D] 装饰器实例不能保存可变对象

**参考答案**：0

**解析**：函数名绑定到唯一的装饰器实例，多次调用该函数都是调用同一个实例的 __call__，因此实例属性（如计数、缓存）会在调用之间保持。不会每次调用都新建实例，也不会自动重置，且可以保存任意可变对象。

### single_choice · None



- [A] 被装饰函数不会被调用
- [B] 被装饰函数会被调用，但调用者拿到 None
- [C] 装饰器会抛出 SyntaxError
- [D] Python 会自动补上 return

**参考答案**：1

**解析**：如果 __call__ 中调用了 self.func(*args, **kwargs) 但没有 return 其返回值，原函数仍然执行，但装饰后的调用返回 None。Python 不会自动补 return，这不是语法错误。

### single_choice · None



- [A] run run
- [B] run None
- [C] None None
- [D] 会报错

**参考答案**：1

**解析**：第一次调用 run() 时 self.done 为 False，执行原函数并返回 'run'；第二次调用时 self.done 已为 True，返回 None。因此输出为 'run None'。

### single_choice · None



- [A] 只需要简单地打印一行日志
- [B] 需要在多次调用之间维护较复杂的状态或配置，并且希望以属性方式访问
- [C] 需要装饰的函数非常多且签名字都相同
- [D] 需要在不使用装饰器语法的情况下手动包装函数

**参考答案**：1

**解析**：当装饰器需要维护较复杂的状态或配置，并希望像对象属性那样访问时，用类写装饰器更自然。简单日志、批量相同签名的场景用函数装饰器即可，手动包装函数与选择类还是函数装饰器无关。

### single_choice · None



- [A] 保存在 __call__ 方法的局部变量中
- [B] 在 __init__ 中作为实例属性保存，供 __call__ 使用
- [C] 作为类变量保存，所有实例共享
- [D] 必须保存在全局变量中，否则无法访问

**参考答案**：1

**解析**：类装饰器的典型写法是在 __init__ 中把被装饰的函数保存为实例属性（如 self.func），然后在 __call__ 中通过该属性调用原函数。局部变量无法跨方法访问，类变量会导致多个装饰实例共享，全局变量则不是必须的。

### single_choice · None



- [A] __init__ 不能接收函数作为参数
- [B] Deco 缺少 __call__ 方法，实例不可调用
- [C] 装饰器不能用于无参数的函数
- [D] foo() 的返回值 42 不能被 print 输出

**参考答案**：1

**解析**：类装饰器要求实例可调用，因此类必须实现 __call__ 方法。这里 Deco 只有 __init__，实例不可调用，所以 foo() 会抛出 TypeError。__init__ 接收函数、装饰无参函数、打印返回值本身都没有问题。

### single_choice · None



- [A] 类装饰器无法保留原函数的 __name__ 元数据
- [B] 类装饰器通过实例的 __call__ 实现调用，函数装饰器通过闭包实现调用
- [C] 类装饰器不能接受额外参数，函数装饰器可以
- [D] 类装饰器只能用于方法，不能用于普通函数

**参考答案**：1

**解析**：类装饰器的调用入口是实例的 __call__ 方法，而函数装饰器通常返回一个闭包（wrapper 函数）来完成调用。类装饰器同样可以通过 __init__ 接收额外参数，也可以通过 functools.wraps 保留元数据，函数和方法都可以被类装饰器装饰。

### single_choice · None



- [A] 'foo'
- [B] 'Deco'
- [C] '__call__'
- [D] 会报 AttributeError，因为实例没有 __name__ 属性

**参考答案**：3

**解析**：foo 被替换为 Deco 的实例，实例本身没有 __name__ 属性，直接访问会抛出 AttributeError。要在类装饰器中保留原函数元数据，可在 __init__ 中使用 functools.update_wrapper(self, func) 等手法。

### single_choice · None



- [A] 在 __call__ 中手动返回 func.__name__
- [B] 在 __init__ 中调用 functools.update_wrapper(self, func)
- [C] 让类继承自 functools.wraps
- [D] 在类中定义 __name__ = func.__name__

**参考答案**：1

**解析**：functools.update_wrapper 会把被包装函数的 __module__、__name__、__qualname__、__doc__、__dict__ 等复制到包装者上。这里包装者是 self，所以在 __init__ 中调用 functools.update_wrapper(self, func) 是常见做法。functools.wraps 是装饰器形式，通常用于函数装饰器。

### single_choice · None



- [A] class Repeat:
      def __init__(self, func):
          self.func = func
      def __call__(self):
          self.func()
- [B] class Repeat:
      def __init__(self, times):
          self.times = times
      def __call__(self, func):
          def wrapper(*a, **k):
              for _ in range(self.times):
                  func(*a, **k)
          return wrapper
- [C] class Repeat:
      def __init__(self, times):
          self.times = times
      def __call__(self):
          pass
- [D] class Repeat:
      def __call__(self, times):
          return self

**参考答案**：1

**解析**：带参数的类装饰器调用链是 Repeat(times=3) 先创建实例，然后把这个实例作为装饰器去接收函数。因此 __init__ 接收 times，__call__ 接收 func 并返回 wrapper。选项 A 的 __init__ 接收 func，无法接收 times；C 的 __call__ 不接收函数；D 的 __init__ 不接受参数。

### single_choice · None



- [A] 先调用 Repeat 的 __call__ 并传入 times=3，再调用 __init__ 传入函数
- [B] 先执行 Repeat(times=3) 创建实例，再用该实例调用函数进行装饰
- [C] 先装饰函数，再把 times=3 作为参数传给被装饰函数
- [D] times=3 会被忽略，等价于 @Repeat

**参考答案**：1

**解析**：带参数的装饰器语法 @Repeat(times=3) 会先求值 Repeat(times=3)，即调用 __init__ 得到实例；然后把这个实例作为装饰器应用到函数上，通常是调用实例的 __call__ 并传入函数。选项 A 顺序颠倒，C、D 都是常见误解。

### single_choice · None



- [A] 类装饰器运行速度一定更快
- [B] 状态可以直接保存在实例属性中，无需使用 nonlocal 或可变容器
- [C] 类装饰器不需要 __call__ 方法
- [D] 类装饰器自动支持异步函数

**参考答案**：1

**解析**：用类实现装饰器时，状态可以直接作为实例属性（如 self.count、self.cache）保存和修改，写法直观。函数装饰器若想保存状态，通常需要通过闭包加 nonlocal，或使用可变对象、函数属性等技巧。类装饰器并不自动更快，也不自动支持异步。

### single_choice · None



- [A] 带参数的装饰器本质上是一个返回装饰器的函数，需要多一层嵌套
- [B] 带参数的装饰器就是给被装饰函数多加一个普通形参
- [C] 带参数的装饰器只能用类实现，不能用函数实现
- [D] 带参数的装饰器不需要 return，只要调用即可

**参考答案**：0

**解析**：带参数的装饰器写法形如 outer(参数) 返回 decorator，decorator 再接收函数并返回 wrapper，因此比普通装饰器多一层嵌套。它并不是给被装饰函数加形参，也完全可以用函数实现。

### single_choice · None



- [A] @repeat(3)
  def f(): ...
- [B] @repeat
  def f(): ...
- [C] @repeat(3, f)
  def f(): ...
- [D] @repeat.3
  def f(): ...

**参考答案**：0

**解析**：@ 后面跟的是一个可调用对象。带参数的装饰器要写成 @repeat(3)，先调用 repeat(3) 得到真正的装饰器，再由它作用于 f。@repeat 是普通装饰器用法。

### multi_choice · None



- [A] def deco_factory(prefix): ... return decorator
- [B] 在 @ 后调用一个函数，如 @tag('ok')
- [C] 使用 functools.wraps 保留原函数元信息
- [D] @staticmethod def f(): ...（在类中直接作为无参装饰器）

**参考答案**：[0, 1, 2]

**解析**：带参数装饰器表现为 @ 后先调用工厂函数得到装饰器，工厂常配 functools.wraps。@staticmethod 是无参装饰器，不涉及参数传递。

### multi_choice · None



- [A] wrapper 会通过闭包引用外层传入的装饰器参数
- [B] 如果在外层函数里修改参数变量，通常需要 nonlocal（若在嵌套中层修改）
- [C] 装饰器参数在 wrapper 每次被调用时都会重新计算表达式
- [D] 装饰器参数值必须在 wrapper 定义前就绑定

**参考答案**：[0, 1, 3]

**解析**：wrapper 通过闭包引用外层参数；在设计上参数表达式在装饰阶段求值一次，因此调用前已绑定。若需在嵌套函数中重新绑定外层变量，需用 nonlocal。参数表达式不会在每次调用时重新求值。

### multi_choice · None



- [A] 无参装饰器直接接收被装饰函数
- [B] 带参数装饰器先执行一次带参调用，返回真正的装饰器
- [C] 带参数装饰器必须使用三层嵌套，两层一定不行
- [D] 带参数装饰器可以搭配 functools.wraps 使用

**参考答案**：[0, 1, 3]

**解析**：无参装饰器直接作用函数；带参装饰器需先调用参数表达式。它通常三层，但用类或其他技巧也可实现，并非一定三层。functools.wraps 可正常搭配使用。

### fill_blank · None



**参考答案**：["decorator", "deco"]

**解析**：外层 repeat(times) 返回中间层，中间层通常命名为 decorator（或 deco），它接收被装饰函数 func。横线处需要与 return 的 decorator 名称一致。

### fill_blank · None



**参考答案**：["*args, **kwargs", "*a, **k", "*args,**kwargs"]

**解析**：wrapper 通常定义为 def wrapper(*args, **kwargs)，转发时用 func(*args, **kwargs)，把位置与关键字参数依次解包传入。

### fill_blank · None



**参考答案**：["wraps", "functools.wraps"]

**解析**：functools.wraps 会复制 __name__、__doc__ 等元信息，常写作 @functools.wraps(func) 或 @wraps(func)。

### fill_blank · None



**参考答案**：["return deco", "return decorator"]

**解析**：外层函数必须返回中间层装饰器，即 return deco，否则 @tag('x') 得到 None，装饰会失败。

### code_reading · None



**参考答案**：输出 [7, 7]。因为 deco_factory(2) 返回 deco，deco 装饰 value 得到 wrapper；调用 value() 时执行列表推导，把 func() 的结果 7 重复收集两次，得到 [7, 7]。

**解析**：带参数装饰器 count=2 控制重复次数，wrapper 每次调用执行 count 次原函数并收集结果。

### code_reading · None



**参考答案**：@head() 在定义 msg 时立即求值：先调用 head() 得到 deco（此时 prefix 用默认值），再由 deco 装饰 msg 返回 wrapper。之后调用 msg() 执行 wrapper 并打印。即：参数表达式在装饰阶段求值一次，wrapper 在调用时执行。

**解析**：@head() 说明即使不用参数，带参装饰器也要求调用外层。它验证了装饰器求值在定义阶段，wrapper 执行在调用阶段。

### scenario · None



**解析**：需要设计三层：外层收 retry 次数与异常类型并返回装饰器；中间层收原函数并返回 wrapper；wrapper 在循环中用 try/except 捕获指定异常并重试，用 *args/**kwargs 转发参数，用 functools.wraps 保留元信息。参数通过闭包被 wrapper 引用。

### single_choice · None



- [A] X-hi bob
- [B] hi bob
- [C] X-
- [D] 报错，outer 参数不正确

**参考答案**：0

**解析**：outer('X-') 返回 deco，deco 装饰 greet 并返回 wrapper。调用 greet('bob') 实际执行 tag + func('bob')，即 'X-' + 'hi bob'，结果为 'X-hi bob'。

### scenario · None



**解析**：函数名显示 wrapper 是因为没加 functools.wraps，缺少 __name__ 等元信息；参数被误认为每次重设，通常是把参数表达式写在 wrapper 内部或在 wrapper 内重新赋值，正确做法是让参数在装饰阶段求值一次并由闭包捕获，wrapper 内只读使用。

### single_choice · None



- [A] 保留被装饰函数的名称、文档字符串等元信息
- [B] 让装饰器支持参数
- [C] 提高函数执行速度
- [D] 让 wrapper 可以接收关键字参数

**参考答案**：0

**解析**：functools.wraps 把被包装函数的 __name__、__doc__ 等元信息复制到 wrapper 上。它不影响能否传参，也不提升性能。

### single_choice · None



- [A] 最内层的 wrapper
- [B] 中间那层（通常叫 decorator）
- [C] 最外层接收装饰器参数的函数
- [D] 以上都不对，由 Python 自动分配

**参考答案**：1

**解析**：结构一般是 outer(参数) -> decorator(func) -> wrapper(*a, **k)。中间层 decorator 接收被装饰的函数，最外层接收装饰器参数，最内层是实际替换原函数的调用包装。

### single_choice · None



- [A] 装饰器参数在函数定义时求值一次，wrapper 在每次调用函数时执行
- [B] 装饰器参数和 wrapper 都在每次调用函数时求值
- [C] 装饰器参数在每次调用时求值，wrapper 只在定义时求值
- [D] 两者都只在模块导入完成时执行一次

**参考答案**：0

**解析**：定义阶段会执行 outer(参数) 和装饰过程，参数表达式只求值一次；而 wrapper 内部的代码是在每次调用被装饰函数时才执行。

### single_choice · None



- [A] 这样能兼容被装饰函数的各种参数形式
- [B] 这样可以少写一个 return 语句
- [C] 这是语法强制要求，否则报错
- [D] 这样 wrapper 会自动加上默认参数

**参考答案**：0

**解析**：被装饰函数的参数签名未知，用 *args, **kwargs 可以把所有位置参数和关键字参数原样转发，兼容任意签名。它不是语法强制，也不影响 return。

### single_choice · None



- [A] 在定义 work 函数（模块加载经过该语句）时求值一次
- [B] 在每次调用 work() 时求值
- [C] 在程序退出时求值
- [D] 永远不会求值，只是注解

**参考答案**：0

**解析**：装饰器表达式在函数定义语句处立即求值一次，得到真正的装饰器并装饰 work。work() 被调用时执行的是装饰后返回的 wrapper。

### multi_choice · None



- [A] 外层函数接收装饰器参数，并返回一个装饰器函数
- [B] 中间层函数接收被装饰的函数并返回 wrapper
- [C] wrapper 内部通常需要调用原函数并返回其结果
- [D] 带参数装饰器只能用类来实现
- [E] wrapper 必须声明与被装饰函数完全相同的形参名，否则报错

**参考答案**：[0, 1, 2]

**解析**：经典三层结构：外层收参数返回装饰器，中间层收函数返回 wrapper，wrapper 调用原函数。带参数装饰器也可以用类实现，并非只能用类；wrapper 用 *args/**kwargs 即可，不必同名。

### multi_choice · None



- [A] 限制函数被调用的最大次数
- [B] 根据传入的日志级别记录调用信息
- [C] 按指定次数重复执行被装饰函数
- [D] 改变被装饰函数的 Python 版本

**参考答案**：[0, 1, 2]

**解析**：带参数装饰器常用于让行为可配置，如次数限制、日志级别、重复次数等。它无法改变运行代码的 Python 版本，这不是装饰器能力范围内的事。
