# s2u5l2 异步上下文管理器（async with）

> 来源 `content/lessons/s2u5l2.json`

## py.ctx.async_ctx

# 异步上下文管理器（async with）

> 一句话直觉：当你打开一个“需要时间的资源”（比如网络连接、数据库会话、异步锁），你希望无论代码成功还是出错，都能自动、优雅地把它关掉——`async with` 就是干这个的。

前置说明：本讲虽是 s2u5l2 的起点，但会顺带回顾 `with`，因为理解同步版本是理解异步版本的最快路径。

---

## 1. 从 `with` 到 `async with`：为什么需要它

`with` 语句（上下文管理器，context manager）让你用一个代码块管理资源的获取和释放，避免忘记关闭：

```python
with open("data.txt") as f:
    data = f.read()   # 离开块时自动 close()
```

它背后靠的是两个“魔法方法”（magic method / dunder method）：`__enter__` 和 `__exit__`。

当资源操作本身是 `await` 的（例如打开一个网络连接要等 I/O），同步的 `__enter__/__exit__` 就无法表达“等待”。Python 3.5 引入了 **异步上下文管理器（asynchronous context manager）**：

- 对象实现 `__aenter__` 和 `__aexit__`，它们都是 `async def` 方法。
- 用 `async with obj as x:` 调用，块离开时会 `await obj.__aexit__(...)`。
- 只能在 `async def` 函数内部使用。

### 关键代码示例

```python
import asyncio

class AsyncResource:
    """一个模拟需要异步打开/关闭的资源"""
    def __init__(self, name):
        self.name = name

    async def __aenter__(self):
        print(f"[enter] 正在异步打开 {self.name} ...")
        await asyncio.sleep(0.1)      # 模拟 I/O 等待
        print(f"[enter] {self.name} 已打开")
        return self                   # 返回给 as 后面的变量

    async def __aexit__(self, exc_type, exc, tb):
        print(f"[exit] 正在关闭 {self.name} ...")
        await asyncio.sleep(0.1)
        print(f"[exit] {self.name} 已关闭")
        return False                  # False 表示异常继续向外抛

async def main():
    async with AsyncResource("db") as r:
        print(f"使用 {r.name} 做点事")

asyncio.run(main())
```

运行输出（顺序固定）：
1. enter 打开
2. 使用资源
3. exit 关闭

---

## 2. `__aexit__` 的三个参数与返回值

`__aexit__(self, exc_type, exc, tb)` 三个参数和同步 `__exit__` 一样：

- `exc_type`：异常类（如 `ValueError`），正常退出时为 `None`。
- `exc`：异常实例。
- `tb`：traceback。

返回值决定是否“吞掉”异常：

- 返回 `False`（或 `None`）：异常继续传播。
- 返回 `True`：异常被抑制，`async with` 块后的代码继续执行。

```python
import asyncio

class SuppressAll:
    async def __aenter__(self):
        return self
    async def __aexit__(self, exc_type, exc, tb):
        if exc_type is not None:
            print(f"吞掉异常: {exc_type.__name__}: {exc}")
            return True      # 抑制异常
        return False

async def main():
    async with SuppressAll():
        raise ValueError("boom")
    print("异常已抑制，继续执行到这里")

asyncio.run(main())
```

---

## 3. 用 `contextlib.asynccontextmanager` 快速写异步上下文

手写 `__aenter__/__aexit__` 很啰嗦。Python 3.7 起，`contextlib` 提供了 `asynccontextmanager`，让你把“yield 前 = 进入，yield 后 = 退出”写成一个 async 生成器：

```python
import asyncio
from contextlib import asynccontextmanager

@asynccontextmanager
async def open_conn(name):
    print(f"打开 {name}")
    await asyncio.sleep(0.05)
    try:
        yield f"conn:{name}"      # yield 的值就是 as 后面拿到的东西
    finally:
        print(f"关闭 {name}")
        await asyncio.sleep(0.05)  # 清理也可以是异步的

async def main():
    async with open_conn("redis") as c:
        print("使用", c)

asyncio.run(main())
```

> 注意：`try/finally` 是必需的，保证即使块内抛异常也能执行清理。

---

## 4. 典型工程用途：`asyncio.Lock`、`aiofiles`、数据库连接

标准库和常见第三方库已经大量使用异步上下文管理器。三个最典型的场景：

```python
import asyncio

async def main():
    # 1) asyncio.Lock 支持 async with
    lock = asyncio.Lock()
    async with lock:
        print("拿到锁，操作共享状态")

    # 2) aiofiles 异步文件 I/O（需 pip install aiofiles）
    # import aiofiles
    # async with aiofiles.open("data.txt") as f:
    #     content = await f.read()

    # 3) 异步 HTTP 会话也可这样管理（如 aiohttp）
    # async with aiohttp.ClientSession() as session:
    #     async with session.get(url) as resp:
    #         print(await resp.text())

asyncio.run(main())
```

**心智模型**：凡是“打开—使用—关闭”模式，且打开/关闭需要 `await`，就用 `async with`。

---

## 5. 与 `with`、`try/finally` 的关系

三种写法的语义等价关系（示意）：

| 写法 | 进入 | 退出 |
|---|---|---|
| `with x:` | `x.__enter__()` | `x.__exit__(...)` |
| `async with x:` | `await x.__aenter__()` | `await x.__aexit__(...)` |
| 手写 `try/finally` | 手动打开 | `finally` 中关闭 |

关键区别：`async with` 里的等待不会阻塞事件循环，其他协程可以趁机执行。这也是它在异步 I/O 中不可替代的原因。

---

### 动手练习

**任务**：写一个“异步限速器”上下文管理器。

要求：
1. 用 `@asynccontextmanager` 实现 `limit_rate(interval)`：进入时记录时间戳，退出时若距今不足 `interval` 秒，则 `await asyncio.sleep(...)` 补足，保证两次调用之间至少间隔 `interval`。
2. 并发运行 5 个任务，每个任务通过 `async with limit_rate(0.3)` 打印当前时间。
3. 观察输出时间戳，验证相邻两次最多相差一个 `interval`（± 误差）。
4. 若块内抛异常，确认退出逻辑依然执行（打印 “cleanup done”）。

提示骨架：
```python
@asynccontextmanager
async def limit_rate(interval):
    start = asyncio.get_event_loop().time()
    try:
        yield
    finally:
        elapsed = asyncio.get_event_loop().time() - start
        if elapsed < interval:
            await asyncio.sleep(interval - elapsed)
```

本地运行（Python 3.8+），观察输出即可。

```python
import asyncio
from contextlib import asynccontextmanager

@asynccontextmanager
async def limit_rate(interval):
    loop = asyncio.get_event_loop()
    start = loop.time()
    try:
        yield
    finally:
        elapsed = loop.time() - start
        if elapsed < interval:
            await asyncio.sleep(interval - elapsed)
        print("cleanup done")

async def job(i):
    async with limit_rate(0.3):
        print(f"job {i} at {asyncio.get_event_loop().time():.3f}")

async def main():
    await asyncio.gather(*(job(i) for i in range(5)))

asyncio.run(main())
```


---

## 本课题目

### single_choice · None



- [A] 它必须同时实现 __enter__ 和 __exit__ 方法
- [B] 它必须实现 __aenter__ 和 __aexit__ 方法，并且可以配合 async with 使用
- [C] 它只能通过 asyncio.Lock 这类内置对象获得，无法自定义
- [D] 它和普通上下文管理器完全等价，只是名字不同

**参考答案**：1

**解析**：异步上下文管理器通过 __aenter__/__aexit__ 实现，并配合 async with 使用。A 描述的是同步上下文管理器；C 错误，用户可以自定义；D 错误，二者协议不同。

### single_choice · None



- [A] enter
  body
  exit
- [B] enter
  body
- [C] body
  enter
  exit
- [D] 程序抛出 TypeError

**参考答案**：0

**解析**：async with 会先 await __aenter__（输出 enter），执行 body（输出 body），再 await __aexit__（输出 exit）。

### single_choice · None



- [A] __aexit__ 仍然会被调用
- [B] __aexit__ 不会被调用，异常直接向外传播
- [C] __aenter__ 会被自动重试
- [D] async with 会静默忽略该异常

**参考答案**：1

**解析**：只有在 __aenter__ 成功返回后，进入 with 体并与 __aexit__ 配对。若 __aenter__ 抛异常，则 __aexit__ 不会被调用。

### single_choice · None



- [A] 不允许嵌套 async with
- [B] 可以嵌套，退出顺序与进入顺序相反（后进先出）
- [C] 嵌套时只有最外层的 __aexit__ 会被调用
- [D] 嵌套时必须把内层放在外层之前

**参考答案**：1

**解析**：async with 与普通 with 一样可以嵌套，退出时按后进先出的顺序依次调用各自的 __aexit__。

### single_choice · None



- [A] A in
  B in
  body
  B out
  A out
- [B] A in
  B in
  body
  A out
  B out
- [C] B in
  A in
  body
  A out
  B out
- [D] A in
  body
  B in
  B out
  A out

**参考答案**：0

**解析**：嵌套时先进先出进入，后进先出退出，所以是 A in、B in、body、B out、A out。

### single_choice · None



- [A] Lock 是普通上下文管理器，只能用 with
- [B] Lock 对象实现了异步上下文管理器协议，可在 async with 中自动获取和释放锁
- [C] Lock 只能通过 lock.acquire() 使用
- [D] async with lock 会立即返回而不等待锁

**参考答案**：1

**解析**：asyncio.Lock 支持异步上下文管理器协议，async with lock 会等待获取锁并在退出时释放。

### single_choice · None



- [A] __aenter__
- [B] __aexit__
- [C] __enter__
- [D] __aiter__

**参考答案**：3

**解析**：异步上下文管理器要求 __aenter__ 和 __aexit__；__enter__ 属于同步协议；__aiter__ 属于异步迭代协议，与之无关。

### single_choice · None



- [A] 它是一个协程函数，需要 await
- [B] 它是一个异步上下文管理器，可用于 async with，超时后取消内部操作
- [C] 它只能用于同步代码
- [D] 它和 async with 不兼容

**参考答案**：1

**解析**：asyncio.timeout 返回一个异步上下文管理器，在 async with 块内超时会取消当前任务，并与内部 await 配合产生 TimeoutError。

### single_choice · None



- [A] 返回值会被丢弃，无法获取
- [B] 返回值会赋给 as 后面的变量
- [C] 必须是 True 或 False
- [D] 只能是 self

**参考答案**：1

**解析**：async with EXPR as VAR 中，VAR 会被绑定为 await __aenter__() 的结果，与同步 with 一致。

### single_choice · None



- [A] 它只接收一个参数 self
- [B] 它接收 (exc_type, exc, tb) 三个参数，无异常时三者均为 None
- [C] 它接收的异常参数始终为 None
- [D] 它只能接收 exc_type 一个参数

**参考答案**：1

**解析**：__aexit__ 的签名与 __exit__ 一致，接收异常类型、异常对象和回溯信息；无异常时均为 None。

### single_choice · None



- [A] __aenter__ 中同步返回连接，__aexit__ 中不做任何事
- [B] __aenter__ 中 await 获取连接，__aexit__ 中 await 释放/归还连接
- [C] 把连接获取放在 __init__ 中完成
- [D] 把连接的获取与释放都放在普通函数中

**参考答案**：1

**解析**：资源获取/释放常涉及异步 I/O，应分别在 __aenter__ 和 __aexit__ 中 await 完成，以保证正确释放。

### single_choice · None



- [A] async with 内部不能使用 await
- [B] async with 本质上等价于在进入和退出时对 __aenter__/__aexit__ 调用 await
- [C] async with 只是语法糖，不会真的 await 任何东西
- [D] async with 会阻塞整个事件循环

**参考答案**：1

**解析**：async with 会在进入和退出时分别 await __aenter__() 和 __aexit__(...)，这允许在协议方法中执行异步操作。

### single_choice · None



- [A] 和 with 行为一致，可以正常运行
- [B] 解释时会报 SyntaxError，因为 async with 只能出现在 async 函数中
- [C] 运行时自动把函数变成协程函数
- [D] 运行到 async with 时抛出 TypeError

**参考答案**：1

**解析**：async with 是异步语法，必须出现在 async def 定义的函数体内，否则在编译阶段就会报 SyntaxError。

### single_choice · None



- [A] 它必须是同步方法，否则会报错
- [B] 它可以返回 False 来抑制异常，返回 True 则传播异常
- [C] 返回 True 会抑制异常，返回 False 或 None 则异常继续传播
- [D] 它的返回值会被忽略，无法影响异常传播

**参考答案**：2

**解析**：__aexit__ 返回真值会抑制 with 块内抛出的异常，返回假值则异常继续向外传播，与同步 __exit__ 语义一致。

### single_choice · None



- [A] class M:
      def __enter__(self): ...
      def __exit__(self, *a): ...
  
  async with M(): ...
- [B] class M:
      async def __aenter__(self): ...
      async def __aexit__(self, *a): ...
  
  async with M(): ...
- [C] class M:
      async def __enter__(self): ...
      async def __exit__(self, *a): ...
  
  async with M(): ...
- [D] class M:
      def __aenter__(self): ...
      def __aexit__(self, *a): ...
  
  with M(): ...

**参考答案**：1

**解析**：异步上下文管理器要求 __aenter__ 和 __aexit__ 都是可等待的（通常为 async def）。A 是同步协议；C 方法名不对；D 方法不是协程同时还用了 with。

### single_choice · None



- [A] 它和 `contextlib.contextmanager` 完全一样，可以互换使用
- [B] 它装饰的生成器函数中必须使用 yield，且 yield 前后的代码分别对应进入和退出
- [C] 它装饰的函数必须是普通 def，不能是 async def
- [D] 它只能用于同步 with 语句

**参考答案**：1

**解析**：asynccontextmanager 用于把一个 async 生成器函数转换为异步上下文管理器，yield 之前的代码相当于 __aenter__，之后的相当于 __aexit__。

### single_choice · None



- [A] 这不是合法的，yield 前必须至少 await 一次
- [B] 这仍然合法，生成器本身是 async 的即可
- [C] 会抛出 RuntimeError
- [D] 必须改成普通 contextmanager

**参考答案**：1

**解析**：只要生成器函数是 async 生成器，即使 yield 前没有 await，也可以被 asynccontextmanager 包装。

### single_choice · None



- [A] A
  B
  C
- [B] A
  C
  B
- [C] C
  A
  B
- [D] A
  C

**参考答案**：1

**解析**：yield 之前打印 A，进入 with 体打印 C，退出时继续执行 yield 之后打印 B。

### single_choice · None



- [A] 异步上下文管理器只能在多线程中使用
- [B] 异步上下文管理器在进入和退出时可以 await 异步操作，而普通上下文管理器不能
- [C] 普通上下文管理器不能用于文件操作
- [D] 异步上下文管理器不支持异常处理

**参考答案**：1

**解析**：异步上下文管理器的核心价值在于进入/退出阶段可以挂起等待 I/O，普通上下文管理器无法在协议方法中 await。

### single_choice · None



- [A] with 体内发生异常时，__aexit__ 不会被调用
- [B] with 体内发生异常时，__aexit__ 会被调用，并接收异常信息
- [C] 只有在 __aenter__ 中发生异常时 __aexit__ 才会被调用
- [D] 异常会被自动忽略，不会传播

**参考答案**：1

**解析**：无论 with 体是否发生异常，只要成功进入，__aexit__ 都会被调用并接收异常类型、值和回溯信息，由返回值决定是否抑制。
