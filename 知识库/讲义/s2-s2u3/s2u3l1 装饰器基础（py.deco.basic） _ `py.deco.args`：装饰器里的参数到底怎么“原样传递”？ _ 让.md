# s2u3l1 装饰器基础（py.deco.basic） / `py.deco.args`：装饰器里的参数到底怎么“原样传递”？ / 让装饰器不再“毁尸灭迹”

> 来源 `content/lessons/s2u3l1.json`

## py.deco.basic

# 装饰器基础（py.deco.basic）

> **一句话直觉**：装饰器（Decorator）让你在不修改原函数代码的前提下，给函数「穿上外套」——增加日志、计时、权限校验等横切功能，一行 `@` 语法就能完成。

---

## 1. 为什么需要装饰器？先看一个痛点

假设你写了 10 个函数，突然老板说：「每个函数被调用时都要打印进入和离开的日志」。最笨的办法是逐个函数内部加 `print`：

```python
# 笨办法：每个函数都要改，重复、易漏、难维护
def add(a, b):
    print(f"进入 add")            # 重复代码
    result = a + b
    print(f"离开 add")            # 重复代码
    return result
```

问题：**功能（加法）与横切关注点（日志）耦合在一起**。装饰器就是把「日志」抽出来，包装在原函数外面。

---

## 2. 第一层理解：函数是「一等公民」（First-class Citizen）

Python 中函数和整数、字符串一样，可以被赋值、当参数传、当返回值。这是装饰器能存在的根本原因。

```python
# 函数可以被赋值给变量
def greet(name):
    return f"Hello, {name}"

f = greet              # f 指向同一个函数对象
print(f("Alice"))      # Hello, Alice

# 函数可以作为参数传入
def call_twice(func, arg):
    return func(arg), func(arg)

print(call_twice(greet, "Bob"))   # ('Hello, Bob', 'Hello, Bob')
```

**结论**：既然函数能作为参数传入、能被返回，那么「接受一个函数、返回一个新函数」的高阶函数（Higher-order Function）就能实现包装逻辑。

---

## 3. 第二层理解：手写一个「包装函数」

先不用 `@` 语法，用最朴素的方式给函数加日志：

```python
def my_decorator(func):
    def wrapper(*args, **kwargs):     # 接收任意参数，转发给原函数
        print(f"[LOG] 调用 {func.__name__}")
        result = func(*args, **kwargs)   # 真正调用原函数
        print(f"[LOG] 结束 {func.__name__}")
        return result
    return wrapper          # 返回新函数，不调用它

def add(a, b):
    return a + b

add_with_log = my_decorator(add)   # 手动包装
print(add_with_log(2, 3))
# [LOG] 调用 add
# [LOG] 结束 add
# 5
```

关键三点：
1. `my_decorator` 接收一个函数 `func`；
2. 内部定义 `wrapper`，在调用 `func` 前后加逻辑；
3. **返回 `wrapper`（函数对象本身），而不是 `wrapper()` 的结果**。

---

## 4. 第三层理解：`@` 语法糖（Syntactic Sugar）

`@decorator` 就是 `func = decorator(func)` 的简写。

```python
def my_decorator(func):
    def wrapper(*args, **kwargs):
        print(f"[LOG] 开始 {func.__name__}")
        result = func(*args, **kwargs)
        print(f"[LOG] 结束 {func.__name__}")
        return result
    return wrapper

@my_decorator            # 等价于 add = my_decorator(add)
def add(a, b):
    return a + b

print(add(2, 3))
# [LOG] 开始 add
# [LOG] 结束 add
# 5
```

**注意时机**：装饰发生在 **定义时**（导入模块时），而不是调用时。所以 `@my_decorator` 在 `def add` 执行完就立刻被调用一次。

---

## 5. 第四层理解：保留原函数元信息 —— `functools.wraps`

不加处理时，被装饰后的 `add.__name__` 会变成 `"wrapper"`，签名、文档字符串也丢了。这在调试和框架里是灾难。

```python
import functools

def my_decorator(func):
    @functools.wraps(func)          # 把 func 的元信息复制到 wrapper 上
    def wrapper(*args, **kwargs):
        """这是 wrapper 的文档"""
        return func(*args, **kwargs)
    return wrapper

@my_decorator
def add(a, b):
    """两数相加"""
    return a + b

print(add.__name__)     # add   （不加 wraps 会是 wrapper）
print(add.__doc__)      # 两数相加
```

**工程级习惯**：写装饰器时，`@functools.wraps(func)` 是标配。

---

## 6. 第五层理解：带参数的装饰器（Decorator with Arguments）

如果装饰器本身要接收参数（比如 `@repeat(3)`），就再加一层函数：

```python
import functools

def repeat(times):                # 最外层：接收装饰器参数
    def decorator(func):          # 中层：接收函数
        @functools.wraps(func)
        def wrapper(*args, **kwargs):   # 内层：接收调用参数
            result = None
            for _ in range(times):
                result = func(*args, **kwargs)
            return result
        return wrapper
    return decorator

@repeat(3)
def say_hi(name):
    print(f"Hi, {name}")

say_hi("Alice")
# Hi, Alice
# Hi, Alice
# Hi, Alice
```

**三层结构口诀**：`参数 → 函数 → 调用参数`。

---

## 7. 常见工程场景速览

| 场景 | 装饰器作用 |
|------|-----------|
| 计时 | 用 `time.perf_counter()` 包裹函数 |
| 缓存 | `functools.lru_cache` |
| 重试 | 失败时自动重试 N 次 |
| 权限 | Web 框架中校验用户是否登录 |
| 注册 | 把函数注册到某个字典（如 Flask 路由） |

---

## 8. 一句话总结

装饰器 = **接收函数、返回新函数的高阶函数**；`@` 只是语法糖；带参数时多加一层闭包；工程上记得 `functools.wraps`。

```python
import time
import functools


def timer(func):
    """打印函数执行耗时的装饰器。"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        print(f"[timer] {func.__name__} 耗时 {elapsed:.4f}s")
        return result
    return wrapper


def repeat(times):
    """带参数装饰器：把函数重复执行 times 次。"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = None
            for _ in range(times):
                result = func(*args, **kwargs)
            return result
        return wrapper
    return decorator


@timer
@repeat(3)
def heavy_task(n):
    """模拟一个耗时的计算任务。"""
    total = sum(i * i for i in range(n))
    return total


if __name__ == "__main__":
    result = heavy_task(100_000)
    print("结果:", result)
    print("函数名:", heavy_task.__name__)
    print("文档:", heavy_task.__doc__)
```

## py.deco.args

# `py.deco.args`：装饰器里的参数到底怎么“原样传递”？

## 一句话直觉

写装饰器时，最怕把原函数的参数写死；`py.deco.args` 要解决的就是：**让装饰器接住任意 `*args` 和 `**kwargs`，再原封不动地传给被包装函数，同时还能在类型层面保留原函数的参数签名。**

---

## 1. 为什么装饰器会“吃掉”参数？

装饰器（decorator）本质是一个函数：它接收一个函数，返回一个新函数。

```python
def simple_decorator(func):
    def wrapper():
        print("before")
        func()          # 这里没有参数
        print("after")
    return wrapper

@simple_decorator
def greet(name):
    print(f"Hello, {name}")

# greet("Alice")  # 会报错：wrapper() 不接受参数
```

问题在于：`wrapper()` 没有声明参数，所以它无法接收原函数 `greet` 需要的 `name`。

要写出通用装饰器，第一反应是用 `*args` 和 `**kwargs`。

---

## 2. 运行时通用写法：`*args` + `**kwargs`

```python
def simple_decorator(func):
    def wrapper(*args, **kwargs):   # 接住任意位置参数和关键字参数
        print("before")
        result = func(*args, **kwargs)  # 原样转发
        print("after")
        return result
    return wrapper

@simple_decorator
def greet(name):
    print(f"Hello, {name}")

greet("Alice")
```

输出：

```text
before
Hello, Alice
after
```

这是运行时可用的基础写法。

但有两个问题：

1. 类型检查器（type checker）不知道 `wrapper` 的参数类型。
2. `greet` 被装饰后，函数签名（signature）信息会丢失。

---

## 3. 保留函数元信息：`functools.wraps`

```python
import functools

def simple_decorator(func):
    @functools.wraps(func)  # 把 __name__、__doc__ 等复制到 wrapper
    def wrapper(*args, **kwargs):
        print("before")
        return func(*args, **kwargs)
    return wrapper

@simple_decorator
def greet(name):
    """Say hello."""
    return f"Hello, {name}"

print(greet.__name__)  # greet
print(greet.__doc__)   # Say hello.
```

`functools.wraps` 解决的是**元信息**问题，不解决静态类型检查问题。

---

## 4. 类型层面保留参数：`ParamSpec`

Python 3.10+ 引入 `ParamSpec`（参数规格变量），它专门用来描述“一个可调用对象的参数列表”。

对装饰器而言，`ParamSpec` 的作用是：

- `P` 代表原函数的参数列表；
- `Callable[P, T]` 表示“参数为 P、返回值为 T 的可调用对象”；
- 装饰器返回的 `wrapper` 也是 `Callable[P, T]`，参数和返回值都不变。

在 Python 3.12+ 中可以用新语法：

```python
from collections.abc import Callable

def add_logging[T, **P](f: Callable[P, T]) -> Callable[P, T]:
    def inner(*args: P.args, **kwargs: P.kwargs) -> T:
        print(f"{f.__name__} was called")
        return f(*args, **kwargs)
    return inner

@add_logging
def add_two(x: float, y: float) -> float:
    return x + y

add_two(1.0, 2.0)  # 类型检查器知道这里需要 float, float
```

关键点：

- `P.args` 只能标注 `*args`；
- `P.kwargs` 只能标注 `**kwargs`；
- 它们必须在同一个函数作用域内使用；
- 运行时 `P.args` / `P.kwargs` 分别是 `ParamSpecArgs` / `ParamSpecKwargs` 实例，主要用于静态检查。

如果是 Python 3.11 及更早版本，可以这样写：

```python
from typing import Callable, ParamSpec, TypeVar

P = ParamSpec("P")
T = TypeVar("T")

def add_logging(f: Callable[P, T]) -> Callable[P, T]:
    def inner(*args: P.args, **kwargs: P.kwargs) -> T:
        return f(*args, **kwargs)
    return inner
```

---

## 5. 装饰器改参数：`Concatenate`

有些装饰器不是“原样转发”，而是会**增加、删除或变换参数**。

例如：给函数自动注入一个锁对象 `Lock` 作为第一个参数。

这时用 `Concatenate[Lock, P]`：

- 原函数签名是 `Callable[Concatenate[Lock, P], R]`；
- 返回的 `wrapper` 签名是 `Callable[P, R]`；
- 也就是：调用 `wrapper` 时不需要传锁，装饰器内部自己补上。

```python
from collections.abc import Callable
from threading import Lock
from typing import Concatenate

my_lock = Lock()

def with_lock[**P, R](f: Callable[Concatenate[Lock, P], R]) -> Callable[P, R]:
    def inner(*args: P.args, **kwargs: P.kwargs) -> R:
        with my_lock:
            return f(my_lock, *args, **kwargs)
    return inner
```

这里 `py.deco.args` 相关的核心思想再次出现：

- `P.args` 接住调用者传的位置参数；
- `P.kwargs` 接住调用者传的关键字参数；
- 装饰器可以决定“补一个参数”“删一个参数”或“改一个参数”。

---

## 6. 工程级装饰器模板

把上面几点合起来，一个工程级装饰器通常长这样：

```python
import functools
from collections.abc import Callable

def my_decorator[T, **P](func: Callable[P, T]) -> Callable[P, T]:
    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        # 前置逻辑
        result = func(*args, **kwargs)
        # 后置逻辑
        return result
    return wrapper
```

它同时满足：

- 运行时：能接任意参数；
- 元信息：`__name__`、`__doc__` 保留；
- 类型：参数和返回值签名被保留。

---

## 动手练习

写一个装饰器 `retry`，要求：

1. 被装饰函数失败时自动重试最多 3 次；
2. 能接收任意位置参数和关键字参数；
3. 原样转发给被装饰函数；
4. 使用 `functools.wraps`；
5. 如果使用 Python 3.12+，尝试加上 `ParamSpec` 类型标注。

示例目标：

```python
@retry
def unstable_add(a: int, b: int = 0) -> int:
    ...

u = unstable_add(1, b=2)
print(u)
```

完成后，再写一个测试函数，让它在第一次或第二次调用时故意抛异常，验证重试确实生效。

```python
import functools
from collections.abc import Callable


def retry[T, **P](func: Callable[P, T]) -> Callable[P, T]:
    """A simple retry decorator.

    Retries the decorated function up to 3 times if it raises an exception.
    Works with arbitrary positional and keyword arguments.
    """

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        last_error: Exception | None = None

        for attempt in range(1, 4):
            try:
                return func(*args, **kwargs)
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                print(f"attempt {attempt} failed: {exc}")

        assert last_error is not None
        raise last_error

    return wrapper


if __name__ == "__main__":
    calls = {"count": 0}

    @retry
    def unstable_add(a: int, b: int = 0) -> int:
        calls["count"] += 1
        if calls["count"] < 3:
            raise ValueError("not yet")
        return a + b

    print("result:", unstable_add(1, b=2))
    print("calls:", calls["count"])
```

## py.deco.functools_wraps

# py.deco.functools_wraps：让装饰器不再“毁尸灭迹”

## 一句话直觉

**装饰器（decorator）本质上是“函数替换”，如果不做处理，被装饰函数的身份信息（名字、文档、参数签名）会被替换成内层包装函数（wrapper）的信息——`functools.wraps` 就是用来把这些元数据（metadata）原样搬回去的“身份还原器”。**

---

## 1. 为什么需要它：一个“丢失身份”的装饰器

装饰器的典型写法是：接收一个函数，返回一个新的函数。返回的新函数通常叫 `wrapper`，它在调用原函数前后加一些逻辑。

问题来了：调用者拿到的函数对象不是原来的那个函数了，而是 `wrapper`。

```python
def my_decorator(func):
    def wrapper(*args, **kwargs):
        print('before')
        result = func(*args, **kwargs)
        print('after')
        return result
    return wrapper

@my_decorator
def greet(name):
    """向某人问好。"""
    return f'Hello, {name}'

print(greet.__name__)   # 输出: wrapper，而不是 greet！
print(greet.__doc__)    # 输出: None，而不是 '向某人问好。'！
```

这就是问题：函数名、文档字符串、类型注解、模块归属等元数据全部被 `wrapper` 覆盖了。对于调试、日志、自动生成文档、IDE 提示、类型检查器来说，这会造成严重困扰。

---

## 2. `functools.wraps` 是什么

`functools.wraps` 是标准库 `functools` 模块提供的一个**装饰器工厂**（decorator factory）。它的作用是：把一个“被包装函数”的关键元数据复制到“包装函数”上。

它本身是一个函数，接收“被包装的函数”，返回一个装饰器，用来装饰 `wrapper`。

```python
from functools import wraps

def my_decorator(func):
    @wraps(func)              # 关键：把 func 的元数据复制到 wrapper
    def wrapper(*args, **kwargs):
        print('before')
        result = func(*args, **kwargs)
        print('after')
        return result
    return wrapper

@my_decorator
def greet(name):
    """向某人问好。"""
    return f'Hello, {name}'

print(greet.__name__)   # 输出: greet
print(greet.__doc__)    # 输出: 向某人问好。
```

一句话：`@wraps(func)` 写在 `wrapper` 上方，相当于把 `func` 的“身份证”贴到 `wrapper` 脸上。

---

## 3. 它具体复制了哪些属性

`functools.wraps` 默认会复制以下属性（如果被包装函数有的话）：

- `__module__`：定义该函数的模块名
- `__name__`：函数名
- `__qualname__`：限定名（用于嵌套函数，比如 `outer.<locals>.inner`）
- `__doc__`：文档字符串
- `__dict__`：函数自定义属性字典（会更新到 wrapper 的 `__dict__`）
- `__wrapped__`：指向被包装函数的引用（Python 3.2+ 新加）

另外，Python 3.4 之后，如果 `func` 有 `__annotations__`，也会被复制。

```python
from functools import wraps

def deco(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

@deco
def add(x: int, y: int) -> int:
    """两数相加。"""
    return x + y

print(add.__name__)          # add
print(add.__qualname__)      # add
print(add.__doc__)           # 两数相加。
print(add.__annotations__)   # {'x': <class 'int'>, 'y': <class 'int'>, 'return': <class 'int'>}
print(add.__wrapped__)       # <function add at 0x...>
```

特别说明 `__wrapped__`：它让你可以通过 `inspect.unwrap()` 一路剥开所有装饰器，拿到最原始的函数。

```python
import inspect

@deco
@deco
def f():
    pass

print(inspect.unwrap(f).__name__)   # f
print(f.__wrapped__.__wrapped__)    # 原函数 f
```

---

## 4. 不写 `@wraps` 的后果有多严重

先看一个反例：一个没有用 `wraps` 的计时装饰器，被用在 Web 框架的视图函数上。

```python
def timer(func):
    import time
    def wrapper(*args, **kwargs):
        t0 = time.perf_counter()
        r = func(*args, **kwargs)
        print(f'{func.__name__} took {time.perf_counter()-t0:.4f}s')
        return r
    return wrapper

@timer
def get_user(user_id: int) -> dict:
    """根据 ID 获取用户。"""
    return {'id': user_id}

print(get_user.__name__)   # wrapper
print(get_user.__doc__)    # None
```

后果包括：

1. **调试困难**：traceback 里显示的是 `wrapper`，找不到真正的函数。
2. **文档丢失**：`help(get_user)` 显示的是 wrapper 的签名和空文档。
3. **IDE 提示错误**：编辑器无法正确推断参数类型和返回值。
4. **类型检查器报错**：mypy、pyright 看到的是 `(*args, **kwargs)`，与真实签名不符。
5. **框架行为异常**：某些框架（如 Flask 早期版本）根据函数名注册路由，重复的函数名会导致冲突。

加上 `@wraps(func)` 后，这些信息全部恢复。

---

## 5. 工程实践：什么时候必用、什么时候可省

**必用场景：**

- 任何会被外部调用、被工具分析的装饰器：Web 视图、API 注册、类型检查、文档生成。
- 多个装饰器叠加时（保证 `inspect.unwrap` 能正确工作）。
- 需要让 `functools.singledispatch`、`functools.lru_cache` 等与自定义装饰器协作时。

**可省场景：**

- 纯粹的内部一次性包装，不暴露给外部，不过没关系；但工程上建议一律加上，成本极低。

**标准写法模板：**

```python
from functools import wraps

def my_decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        # 前置逻辑
        result = func(*args, **kwargs)
        # 后置逻辑
        return result
    return wrapper
```

**带参数的装饰器** 也要正确使用 `wraps`：

```python
from functools import wraps

def repeat(times):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = None
            for _ in range(times):
                result = func(*args, **kwargs)
            return result
        return wrapper
    return decorator

@repeat(3)
def say(msg):
    """打印消息。"""
    print(msg)

say('hi')             # 打印三次 hi
print(say.__name__)   # say
print(say.__doc__)    # 打印消息。
```

只要记住一点：**只要写了 `wrapper`，就在它上面写 `@wraps(func)`。**

---

## 动手练习

**任务**：写一个装饰器 `log_calls`，用于记录函数被调用时的参数和返回值；要求：

1. 使用 `functools.wraps` 保留原函数元数据。
2. 被装饰后，`func.__name__`、`func.__doc__`、`func.__annotations__` 都必须与原始函数一致。
3. 再写一个 `count_calls` 装饰器，统计函数被调用的次数，挂在函数属性 `func.call_count` 上；同样使用 `wraps`。
4. 把两个装饰器叠加使用，验证 `inspect.unwrap()` 能拿到最原始函数。

**验收标准**：在本地运行后，`print(add.__name__)` 输出 `add`，`print(add.call_count)` 输出正确次数，`inspect.unwrap(add)` 返回未被包装的原函数。

```python
from functools import wraps
import inspect


def log_calls(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        print(f'[log] calling {func.__name__} args={args} kwargs={kwargs}')
        result = func(*args, **kwargs)
        print(f'[log] {func.__name__} returned {result!r}')
        return result
    return wrapper


def count_calls(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        wrapper.call_count += 1
        return func(*args, **kwargs)
    wrapper.call_count = 0
    return wrapper


@log_calls
@count_calls
def add(x: int, y: int) -> int:
    """两数相加。"""
    return x + y


print(add(1, 2))
print(add(3, 4))
print('name:', add.__name__)
print('doc :', add.__doc__)
print('ann :', add.__annotations__)
print('calls:', add.call_count)
print('unwrap name:', inspect.unwrap(add).__name__)
```


---

## 本课题目

### single_choice · None



- [A] 装饰器是一个接收函数并返回函数的可调用对象
- [B] 装饰器是 Python 的语法糖，无法用任何等价形式表达
- [C] 装饰器只能作用于类，不能作用于普通函数
- [D] 装饰器在调用被装饰函数时才执行装饰逻辑

**参考答案**：0

**解析**：装饰器本质上是一个可调用对象，接收被装饰的函数作为参数并返回一个替代函数（或原函数）。@语法只是 func = decorator(func) 的等价简写，装饰逻辑在函数定义时即执行。

### single_choice · None



- [A] 装饰中
  定义完成后
- [B] 定义完成后
  装饰中
- [C] 装饰中
  hello
  定义完成后
- [D] 定义完成后
  装饰中
  hello

**参考答案**：0

**解析**：装饰器在函数定义时立即应用，因此 '装饰中' 先于 '定义完成后' 打印；hello 从未被调用，所以不会打印 'hello'。

### single_choice · None



- [A] 装饰器定义的包装层越靠外层，函数调用时越先执行其函数体
- [B] 装饰器定义的包装层越靠内层，函数调用时越先执行其函数体
- [C] 所有装饰器的包装层在调用时同时执行，无先后
- [D] 执行顺序由被装饰函数的定义顺序决定，与装饰器无关

**参考答案**：0

**解析**：装饰器从上到下的书写顺序对应 b 先应用、a 后应用，因此 a 的包装在最外层，调用时最外层包装体先执行，其后才进入下一层。

### single_choice · None



- [A] __init__ 和 __call__
- [B] __new__ 和 __del__
- [C] __enter__ 和 __exit__
- [D] __get__ 和 __set__

**参考答案**：0

**解析**：类实例作为装饰器需要 __init__ 保存被装饰函数，__call__ 使实例可调用以替代原函数。__enter__/__exit__ 用于上下文管理器，__new__ 用于构造，均非必需。

### single_choice · None



- [A] 0
- [B] 1
- [C] 2
- [D] 报错：f 已不是函数

**参考答案**：2

**解析**：每次调用 f() 实际是调用 Count 实例的 __call__，内部 n 累加；两次调用后 n 为 2。实例本身仍然可调用，因此不会报错。

### single_choice · None



- [A] 装饰器必须返回被装饰的原函数，否则会出错
- [B] 装饰器可以返回任意可调用对象，它将替代原函数的绑定
- [C] 装饰器必须返回 None
- [D] 装饰器只能返回函数，不能返回类实例

**参考答案**：1

**解析**：装饰器返回的对象会替换原名称的绑定，只要后续调用方式相容即可，可以是函数、lambda、类实例等。返回原函数会丢失装饰效果。

### single_choice · None



- [A] 装饰器定义时立刻报语法错误
- [B] 被装饰函数一旦传入参数就会抛出 TypeError
- [C] 被装饰函数的返回值被自动丢弃
- [D] 装饰器只会对第一个参数生效，其余被忽略

**参考答案**：1

**解析**：包装函数签名未包含 *args/**kwargs 时只能接受规定的参数，透传调用 f() 不含额外参数，原函数带参调用时会因包装函数签名不匹配而 TypeError。

### single_choice · None



- [A] f(*args, **kwargs)
- [B] return f(*args, **kwargs)
- [C] return wrapper(*args, **kwargs)
- [D] f(args, kwargs)

**参考答案**：1

**解析**：需要把原函数调用的返回值作为 wrapper 的返回值传出。选项 A 丢弃了返回值，C 造成无限递归，D 传递方式错误。

### single_choice · None



- [A] 为多个函数统一添加日志记录、计时等横切关注点
- [B] 替代循环语句以提高遍历效率
- [C] 定义一个新的数据类型
- [D] 管理多个模块之间的导入顺序

**参考答案**：0

**解析**：装饰器适合在不修改函数体的前提下统一添加横切功能（日志、计时、缓存、权限等）。其他选项与装饰器用途无关。

### single_choice · None



- [A] 1
- [B] 42
- [C] TypeError，因为 42 不可调用
- [D] None

**参考答案**：2

**解析**：装饰后名称 f 绑定到整数 42，调用 f() 时整数不可调用，抛 TypeError。这说明装饰器应返回可调用对象。

### single_choice · None



- [A] 它们属于自定义装饰器，必须由用户自行实现
- [B] 它们是 Python 内置的装饰器，用于改变类中方法的绑定行为
- [C] 它们只能装饰类而不能装饰方法
- [D] 它们会修改方法的返回类型

**参考答案**：1

**解析**：@staticmethod 和 @classmethod 是 Python 内置装饰器，用于控制方法绑定对象（无绑定 / 绑定到类），并不修改方法返回值类型。

### single_choice · None



- [A] 被装饰函数的 __doc__ 一定丢失，无法通过工具恢复
- [B] 使用 functools.wraps 后，help() 能显示原函数的文档字符串
- [C] 装饰后的函数不再拥有 __wrapped__ 属性
- [D] functools.wraps 只能用于类装饰器

**参考答案**：1

**解析**：functools.wraps 会复制 __doc__ 等元信息，并设置 __wrapped__ 指向原函数，因此 help() 可显示原文档字符串；它适用于函数装饰器。

### single_choice · None



- [A] deco = f = deco(f)
- [B] f = deco(f)
- [C] f = deco(deco)
- [D] deco(f); f = f()

**参考答案**：1

**解析**：@deco 等价于在 def f 之后执行 f = deco(f)。选项 A 是错误嵌套，C 传入了装饰器自身，D 会调用结果而不是回绑。

### single_choice · None



- [A] def wrapper():
- [B] def wrapper(func):
- [C] def wrapper(*args, **kwargs):
- [D] def wrapper(f, *args):

**参考答案**：2

**解析**：包装函数需要透传原函数的所有位置参数和关键字参数，因此使用 *args, **kwargs；参数中不应再包含原函数本身。

### single_choice · None



- [A] 装饰器返回了原函数但未更改任何属性
- [B] 装饰器返回了内部定义的包装函数，且未使用 functools.wraps 保留元信息
- [C] 装饰器在返回前显式设置了 __name__ = 'wrapper' 之外还调用了 functools.wraps
- [D] 装饰器本身是一个类实例且定义了 __call__

**参考答案**：1

**解析**：包装函数替换了原函数，其 __name__ 默认为 'wrapper'；functools.wraps 会把原函数的元信息（含 __name__）复制到包装函数上，可避免此问题。

### single_choice · None



- [A] 让包装函数运行得更快
- [B] 保留被装饰函数的名称、文档字符串等元信息
- [C] 强制检查被装饰函数的参数类型
- [D] 让装饰器能够装饰类方法

**参考答案**：1

**解析**：functools.wraps 是一个方便拷贝 __module__、__name__、__qualname__、__doc__、__dict__ 等的装饰器工厂，用于保留元信息，不影响性能或类型检查。

### single_choice · None



- [A] hi
- [B] hi
  hi
- [C] hi
  hi
  hi
  hi
- [D] 报错：wrapper 未返回

**参考答案**：1

**解析**：twice 返回的 wrapper 会调用原 say 两次，因此输出两遍 'hi'。wrapper 无需返回值，原函数也无返回值。

### single_choice · None



- [A] 带参数的装饰器在被装饰函数定义时会先调用带参工厂，再返回装饰器
- [B] 带参数的装饰器与普通装饰器等价，参数只是被忽略
- [C] 带参数的装饰器不能使用 @ 语法
- [D] 带参数的装饰器必须返回被装饰函数本身

**参考答案**：0

**解析**：带参装饰器写法为 @factory(arg)，等价于 factory(arg) 先得到一个装饰器，然后再应用到函数上，即存在三层可调用结构。

### single_choice · None



- [A] go
- [B] go
  go
- [C] go
  go
  go
- [D] 报错：repeat 缺少参数

**参考答案**：2

**解析**：@repeat(3) 先调用 repeat(3) 得到 deco，再用 deco 装饰 go，包装函数循环调用 go 三次。

### single_choice · None



- [A] f = a(b(f))
- [B] f = b(a(f))
- [C] f = a(f); f = b(f)
- [D] f = b(f); f = a(f)

**参考答案**：0

**解析**：多个装饰器从上到下写在语法上，其应用顺序是自下而上：先 b 后 a，等价于 f = a(b(f))。运行时调用则按 a 的包装外层先触发。

### single_choice · None



- [A] (1, 2) {}
- [B] 1 2
- [C] (1, 2)
- [D] args=(1,2) kwargs={}

**参考答案**：0

**解析**：wrapper 使用 *args 收集位置参数为元组 (1, 2)，**kwargs 收集关键字参数为空字典 {}，因此 print 输出 (1, 2) {}。

### single_choice · None



- [A] foo(5, y=20)，x=5，y=20
- [B] foo(5, 20)，x=5，y=20
- [C] foo(5)，y 使用默认值 10
- [D] 会抛出 TypeError，因为参数形式不匹配

**参考答案**：0

**解析**：*args 收集 (5,)，**kwargs 收集 {'y': 20}，再通过 func(*args, **kwargs) 展开传回，等价于 foo(5, y=20)，结果 x=5，y=20。

### single_choice · None



- [A] wrapper 不需要关心默认值，交给原函数处理即可
- [B] wrapper 必须显式复制原函数的默认值
- [C] 默认值会在装饰时被丢弃
- [D] 使用 *args/**kwargs 会导致默认值失效

**参考答案**：0

**解析**：wrapper 只是转发参数，默认值由原函数签名处理。只要调用时未传该参数，原函数就会使用其默认值。

### multi_choice · None



- [A] *args 将以元组形式收集多余的位置参数
- [B] **kwargs 将以字典形式收集多余的关键字参数
- [C] 转发时应写成 func(*args, **kwargs)
- [D] 只有被装饰函数含任意参数时才能用 *args/**kwargs

**参考答案**：[0, 1, 2]

**解析**：A、B、C 正确描述了 *args/**kwargs 的收集与转发机制。D 错误：任何函数都可以用这种透明转发方式，不要求原函数本身带 *args 或 **kwargs。

### multi_choice · None



- [A] 用 *args 和 **kwargs 接收任意参数并原样转发
- [B] 用 functools.wraps 保留原函数元信息
- [C] 确保 wrapper 返回原函数的返回值
- [D] 装饰器必须抛出异常才算有效

**参考答案**：[0, 1, 2]

**解析**：通用装饰器需要参数透明转发、保留元信息（wraps）、并 return 原函数调用结果。装饰器不需要抛出异常。

### multi_choice · None



- [A] 带参数装饰器需要额外一层函数嵌套
- [B] 最外层函数接收装饰器参数
- [C] 中间层函数接收被装饰函数
- [D] @deco(5) 等价于 deco = deco(5)

**参考答案**：[0, 1, 2]

**解析**：A、B、C 正确描述了带参装饰器的结构。D 错误：写法应为 func = deco(5)(func)，而非对名字 deco 重新赋值。

### multi_choice · None



- [A] __name__
- [B] __doc__
- [C] __module__
- [D] __version__

**参考答案**：[0, 1, 2]

**解析**：wraps 会复制 __name__、__doc__、__module__、__qualname__、__dict__ 等标准属性。__version__ 不是函数的标准属性，不会被自动复制。

### fill_blank · None



**参考答案**：["*args, **kwargs", "*args,**kwargs"]

**解析**：转发时要分别展开位置参数和关键字参数，写成 func(*args, **kwargs)，缺一不可。

### fill_blank · None



**参考答案**：["wraps"]

**解析**：functools.wraps 是标准做法，用于把原函数的元信息复制到 wrapper 上。

### code_reading · None



**参考答案**：依次输出：先 'before'，再 'after'，最后 '6'。原因是 wrapper 先打印 'before'，用收集到的 (3,) 和空 kwargs 调用 multiply，mulitply 使用默认 b=2 返回 6；接着打印 'after'，最后外层 print 输出 6。

**解析**：本题考查对整个调用链及参数转发的理解：默认值 b=2 由原函数处理，wrapper 只负责前后打印和转发返回值。

### code_reading · None



**参考答案**：执行流程：先用 'b' 调用 emphasize，返回 decorator；decorator 接收 hello 并返回 wrapper；之后调用 hello('Bob') 实际是调用 wrapper('Bob')，wrapper 用 <b> 和 </b> 包裹原函数返回值 'Hi, Bob'，最终打印 '<b>Hi, Bob</b>'。

**解析**：这是带参数装饰器的典型三层结构：外层接收装饰器参数 tag，中间层接收被装饰函数，内层 wrapper 负责实际调用和参数转发。

### single_choice · None



- [A] return func(*args, **kwargs)
- [B] return func(args, kwargs)
- [C] return func(*kwargs)
- [D] return func(**args)

**参考答案**：0

**解析**：标准做法是用 *args 和 **kwargs 同时展开转发，才能兼容位置参数和关键字参数两种调用方式。其他选项要么传入了元组/字典本身，要么展开了错误的容器。

### single_choice · None



- [A] 装饰器是一个接收函数并返回新函数的可调用对象
- [B] 装饰器必须定义在类内部
- [C] 装饰器只能装饰无参函数
- [D] 装饰器语法 @deco 等价于 deco() 调用被装饰函数

**参考答案**：0

**解析**：装饰器的本质是可调用对象，接收一个函数（或类）作为参数并返回新的可调用对象。@deco 语法等价于 func = deco(func)，与是否在类中、是否带参无关。

### single_choice · None



- [A] functools.wraps
- [B] functools.reduce
- [C] functools.lru_cache
- [D] functools.partial

**参考答案**：0

**解析**：functools.wraps 是一个装饰器工厂，它会复制被包装函数的 __name__、__doc__、__module__ 等属性到 wrapper 上。其他几个函数用途不同。

### single_choice · None



- [A] def deco(func): return 一个 wrapper 函数
- [B] def deco(): return 一个 wrapper 函数
- [C] def deco(func, option): return 一个 wrapper 函数
- [D] def deco(*options): return func

**参考答案**：0

**解析**：不带参数的装饰器接收一个被装饰函数 func，内部定义 wrapper，最后返回 wrapper。若装饰器本身要带参数，需要多一层嵌套。

### single_choice · None



- [A] 最外层接收装饰器参数，中间层接收被装饰函数，最内层是 wrapper
- [B] 最外层接收被装饰函数，中间层接收装饰器参数，最内层是 wrapper
- [C] 只需要一层，接收所有参数
- [D] 装饰器参数必须放在被装饰函数之后

**参考答案**：0

**解析**：带参装饰器需要三层：外层函数接收装饰器参数并返回 decorator，decorator 接收被装饰函数并返回 wrapper，wrapper 负责实际调用。

### single_choice · None



- [A] 让装饰后的函数可以接收任意形式的参数，保持与原函数调用方式一致
- [B] 提高函数运行速度
- [C] 让参数可以自动转换为字典
- [D] 避免使用 return 语句

**参考答案**：0

**解析**：*args 和 **kwargs 让 wrapper 无需知道原函数签名就能透明转发参数，是通用装饰器的关键技巧。它与性能、类型转换无关。

### single_choice · None



- [A] 先打印 args: ('Anna',)，再打印 Hello, Anna!
- [B] 先打印 args: ('Anna',)，再打印 Hello, Anna! 并返回 None
- [C] 打印 args: ('Anna',) 后程序报错
- [D] 直接打印 Hello, Anna!

**参考答案**：0

**解析**：wrapper 打印收集到的位置参数元组 ('Anna',)，然后通过 func(*args, **kwargs) 调用 greet，返回 'Hello, Anna!' 并由外层 print 输出。

### single_choice · None



- [A] func = deco(func)
- [B] func = deco()(func)
- [C] deco(func)
- [D] func(func)

**参考答案**：0

**解析**：@deco 语法糖等价于 func = deco(func)，即把原函数作为参数传给 deco，再把返回值重新绑定到名字 func 上。

### single_choice · None



- [A] functools.wraps 会把被装饰函数的字节码复制到包装函数上
- [B] functools.wraps 是一个装饰器工厂，用于把被包装函数的元数据（如 __name__、__doc__、__module__、__qualname__、__dict__、__wrapped__）复制到包装函数上
- [C] functools.wraps 会阻止包装函数被再次装饰
- [D] functools.wraps 只能用于类，不能用于函数

**参考答案**：1

**解析**：functools.wraps 接受一个函数并返回一个装饰器，用来更新包装函数的 __name__、__doc__、__module__、__qualname__、__dict__，并把原函数写入 __wrapped__ 属性。它不复制字节码，也不阻止再次装饰，函数和类装饰器都可使用。

### single_choice · None



- [A] greet 返回问候语
- [B] wrapper None
- [C] deco 返回问候语
- [D] wrapper 返回问候语

**参考答案**：1

**解析**：未使用 wraps 时，greet 实际指向 wrapper，其 __name__ 为 'wrapper'，__doc__ 为 None；原函数的名称和文档字符串没有被复制过来。

### single_choice · None



- [A] 它会清空 wrapper 原有的 __dict__
- [B] 它使用 update 方式把原函数的 __dict__ 合并进 wrapper 的 __dict__
- [C] 它不处理 __dict__
- [D] 它只复制原函数 __dict__ 中名字以双下划线开头的项

**参考答案**：1

**解析**：functools.wraps 会对 wrapper.__dict__ 调用 update，用原函数的 __dict__ 合并进去，不会清空原有内容，也不只针对双下划线项。

### multi_choice · None



- [A] 它接收被装饰的原始函数作为参数并返回一个装饰器
- [B] 使用后包装函数的 __name__ 默认会与原始函数相同
- [C] 它会把原始函数保存到包装函数的 __wrapped__ 属性
- [D] 它会把原始函数的源码行号 __code__.co_firstlineno 一并复制
- [E] 它只能用于同步函数，不能用于异步函数

**参考答案**：[0, 1, 2]

**解析**：wraps 是接收原始函数、返回装饰器的工厂；它会更新 __name__ 等元数据并设置 __wrapped__。它不复制 __code__ 相关行号；对 async 包装函数同样可以配合使用。

### multi_choice · None



- [A] 被装饰函数的 __name__ 变成包装函数的名字
- [B] 被装饰函数的 __doc__ 变为 None
- [C] inspect.signature 显示包装函数的 (*args, **kwargs) 而不是原签名
- [D] 被装饰函数每次调用都会抛出 TypeError
- [E] 依赖 __wrapped__ 的工具无法追溯到原函数

**参考答案**：[0, 1, 2, 4]

**解析**：不使用 wraps 会丢失名称、文档、签名信息和 __wrapped__ 链，但通常不会造成调用时报 TypeError（除非包装函数参数处理有误）。

### multi_choice · None



- [A] inspect.signature 默认会沿 __wrapped__ 链解析真实签名
- [B] functools.wraps 设置的 __wrapped__ 让 inspect.unwrap 能找到原始函数
- [C] inspect.getdoc 会受 functools.wraps 是否使用的影响
- [D] functools.wraps 会自动修改原始函数的 __name__
- [E] 使用 wraps 后 help() 显示的信息会更接近原始函数

**参考答案**：[0, 1, 2, 4]

**解析**：wraps 设置 __wrapped__，配合 inspect.signature/unwrap 可还原签名，getdoc 和 help 也更接近原函数。它不会修改原始函数本身的属性。

### multi_choice · None



- [A] __module__
- [B] __qualname__
- [C] __annotations__
- [D] __closure__
- [E] __doc__

**参考答案**：[0, 1, 2, 4]

**解析**：wraps 默认更新 __module__、__name__、__qualname__、__annotations__、__doc__、__dict__，并设置 __wrapped__；__closure__ 属于函数实现细节，不会被复制。

### fill_blank · None



**参考答案**：["@functools.wraps(f)", "@functools.wraps(f)\\n", "functools.wraps(f)"]

**解析**：在包装函数定义上方使用 @functools.wraps(f)，把原函数 f 的元数据复制到 wrapper，从而保留 __name__、__doc__ 等。

### code_reading · None



**参考答案**：6 foo foo docs foo

**解析**：wrapper 调用 foo 得 2*3=6；wraps 将 __name__ 设为 'foo'，__doc__ 设为 'foo docs'，并把原函数存入 __wrapped__，其 __name__ 也是 'foo'。

### code_reading · None



**参考答案**：因为 outer 中的 wrapper 没有使用 functools.wraps(f)，inner 这个名称实际指向 wrapper 函数，其 __name__ 是 'inner'？注意：此处输出 'wrapper'。正确说明：装饰后 inner 变量指向 wrapper，未使用 wraps 使其 __name__ 保持为 'wrapper'。

**解析**：本题关键：未使用 functools.wraps 时，装饰后的名字被绑定到 wrapper，因此 inner.__name__ 输出 'wrapper'。标准答案应指出输出为 'wrapper' 并说明原因。

### fill_blank · None



**参考答案**：["__wrapped__", "wrapped"]

**解析**：functools.wraps 会把被包装函数赋给包装函数的 __wrapped__ 属性，供 inspect.unwrap 等工具使用。

### scenario · None



**解析**：原因是包装函数没有复制原函数的元数据，导致 __name__、__doc__ 等都指向 wrapper，Sphinx/inspect 拿到的也是包装函数签名。修复方式是给内层包装函数加上 @functools.wraps(被装饰函数)，这样会复制名称、文档等元数据并设置 __wrapped__，使 Sphinx 与 inspect.signature 能沿链还原原始签名。

### single_choice · None



- [A] __name__
- [B] __doc__
- [C] __wrapped__
- [D] __defaults__

**参考答案**：3

**解析**：functools.wraps 默认更新 __module__、__name__、__qualname__、__annotations__、__doc__ 以及 __dict__，并设置 __wrapped__。它不复制 __defaults__ 等函数签名相关的底层属性，这正是需要 functools.wraps 配合 signature 追踪或使用其他工具的原因。

### single_choice · None



- [A] 让包装函数在被调用时直接转发到原函数
- [B] 使 inspect.signature 等自省工具能够沿 __wrapped__ 链访问原始函数的签名
- [C] 使包装函数无法被垃圾回收
- [D] 让包装函数继承原函数的所有闭包变量

**参考答案**：1

**解析**：functools.wraps 会把原函数赋给包装函数的 __wrapped__ 属性，inspect.signature 等工具默认会沿着 __wrapped__ 链查找真实签名。它不改变调用行为，也不影响垃圾回收或闭包。

### single_choice · None



- [A] 3 add 两数相加
- [B] 6 add 两数相加
- [C] 6 wrapper 两数相加
- [D] 6 add None

**参考答案**：1

**解析**：wrapper 调用 f(1,2)=3 后乘 2 得 6；由于使用了 functools.wraps，add.__name__ 仍是 'add'，__doc__ 仍是 '两数相加'。

### single_choice · None



- [A] @functools.wraps(wrapper) 放在 wrapper 定义之前
- [B] @functools.wraps(f) 放在 wrapper 定义之前，f 是被装饰的原始函数
- [C] functools.wraps(wrapper, f) 需要在 return 之后调用
- [D] functools.wraps 必须配合 @staticmethod 使用

**参考答案**：1

**解析**：标准用法是把 @functools.wraps(原始函数) 作为装饰器放在内层包装函数定义之上；它接收原始函数作为参数，返回用于装饰包装函数的装饰器。

### single_choice · None



- [A] 被装饰函数的调用结果会出错
- [B] help() 或文档生成工具显示的是包装函数的文档而不是原函数的
- [C] 原函数会被自动删除
- [D] 装饰器无法接收参数

**参考答案**：1

**解析**：不使用 wraps 不会影响调用结果，但会让 __name__、__doc__ 等元数据变成包装函数的，导致 help()、文档生成和调试信息失真。

### single_choice · None



- [A] 放在最外层装饰器工厂函数上
- [B] 放在内层真正包装被装饰函数的那层函数上
- [C] 放在 return 语句之后，通过赋值设置
- [D] 带参数装饰器不能使用 functools.wraps

**参考答案**：1

**解析**：带参数装饰器有三层结构：最外层接收装饰器参数，第二层接收被装饰函数，最内层是包装函数。functools.wraps(被装饰函数) 应放在最内层包装函数上。

### single_choice · None



- [A] 保证 wrapper 的签名与 f 完全一致并能自动转发参数
- [B] 让 wrapper 保留 f 的名称和文档等元数据，便于日志与自省
- [C] 让 print 输出被缓存
- [D] 让 wrapper 成为 f 的子类

**参考答案**：1

**解析**：wrapper(*a, **k) 本身负责转发参数；functools.wraps 只负责把 f 的元数据复制到 wrapper，使日志和自省显示原始函数信息。

### single_choice · None



- [A] 在 @functools.wraps(f) 之前给 wrapper 赋值
- [B] 在 @functools.wraps(f) 之后再给 wrapper 赋值，或在包装函数体内赋值
- [C] 无法实现，wraps 会覆盖所有属性
- [D] 只能通过继承实现

**参考答案**：1

**解析**：functools.wraps 会先把原函数的 __dict__ 更新到 wrapper，因此自定义属性应在 wraps 之后添加，否则可能被覆盖。
