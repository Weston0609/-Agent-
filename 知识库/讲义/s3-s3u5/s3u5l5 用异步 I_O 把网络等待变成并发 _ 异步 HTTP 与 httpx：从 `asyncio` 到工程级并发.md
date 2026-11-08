# s3u5l5 用异步 I/O 把网络等待变成并发 / 异步 HTTP 与 httpx：从 `asyncio` 到工程级并发

> 来源 `content/lessons/s3u5l5.json`

## py.async.aiohttp

# py.async.aiohttp：用异步 I/O 把网络等待变成并发

## 一句话直觉

**当你需要同时从 100 个网站抓数据时，同步代码会傻等 100 次网络往返；`asyncio` + `aiohttp` 能让这 100 次等待重叠发生，总耗时接近最慢的那一次。**

`aiohttp` 是建立在标准库 `asyncio`（异步 I/O 框架）之上的异步 HTTP 客户端/服务端库。理解它之前，先理解它脚下的地基。

---

## 1. 为什么需要异步：I/O 密集场景的瓶颈

普通 Python 代码是**同步（synchronous）**的：调用 `requests.get(url)` 时，整个线程会阻塞（block）在网络上，直到响应回来。CPU 大部分时间在空闲。

**异步（asynchronous）** 的思路：遇到 I/O 等待时，主动把控制权交还事件循环（event loop），让它去跑别的任务。等 I/O 就绪再回来继续。

关键概念：
- **协程（coroutine）**：用 `async def` 定义的函数，调用它不会立即执行，而是返回一个协程对象。
- **await**：在协程内部挂起当前任务，等待另一个协程完成。
- **事件循环（event loop）**：调度所有协程的“总指挥”。
- **任务（task）**：把协程包装成可被事件循环并发调度的单元。

```python
import asyncio

async def hello():
    print("Hello ...")
    await asyncio.sleep(1)   # 模拟 I/O 等待，让出控制权
    print("... World!")

asyncio.run(hello())        # 启动事件循环，运行协程
```

**结论**：`async def` + `await` 是异步编程的最小语法单元，`asyncio.run()` 是入口。

---

## 2. 并发执行多个协程：gather 与 Task

单跑一个协程没意义，异步的威力在于**同时跑很多个**。

- `asyncio.create_task(coro)`：把协程登记到事件循环，立刻返回，继续往下走。
- `asyncio.gather(*coros)`：等待一组协程全部完成，按顺序返回结果。

```python
import asyncio, time

async def fetch(name, delay):
    await asyncio.sleep(delay)     # 模拟网络请求耗时
    return f"{name} done in {delay}s"

async def main():
    start = time.perf_counter()
    # 三个任务并发执行，总耗时 ≈ 最慢的那个（1.0s）
    results = await asyncio.gather(
        fetch("A", 0.5),
        fetch("B", 1.0),
        fetch("C", 0.3),
    )
    print(results)
    print(f"total: {time.perf_counter() - start:.2f}s")

asyncio.run(main())
```

如果改用同步 `time.sleep` 顺序执行，总耗时将是 1.8s；并发后约 1.0s。

**结论**：`gather` 是“等待全部并发任务结果”的最常用工具。

---

## 3. aiohttp 登场：异步 HTTP 客户端

`asyncio` 只提供调度骨架，具体“发 HTTP 请求”需要 `aiohttp`。它的核心对象是 **`ClientSession`（会话）**——复用它来保持连接池，是性能关键。

```python
# pip install aiohttp
import asyncio
import aiohttp

async def fetch_url(session, url):
    async with session.get(url) as resp:   # 异步上下文管理器
        return resp.status, await resp.text()

async def main():
    async with aiohttp.ClientSession() as session:
        status, text = await fetch_url(session, "https://example.com")
        print(status, text[:80])

asyncio.run(main())
```

要点：
- `session.get(url)` 返回一个可 await 的响应对象；记得用 `async with` 自动释放连接。
- `await resp.text()` 才是真正读取响应体，会再次挂起。
- `ClientSession` 应该**创建一次、全程复用**，而不是每个请求新建。

**结论**：`aiohttp.ClientSession` 是异步 HTTP 请求的核心入口。

---

## 4. 并发抓取：把第二节和第三节组合起来

真实场景：给 N 个 URL 并发抓取，用 `gather` 汇总。

```python
import asyncio
import aiohttp

URLS = [
    "https://example.com",
    "https://www.python.org",
    "https://httpbin.org/get",
]

async def fetch(session, url):
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            text = await resp.text()
            return url, resp.status, len(text)
    except aiohttp.ClientError as e:      # 网络错误统一处理
        return url, "ERROR", str(e)

async def main():
    async with aiohttp.ClientSession() as session:
        results = await asyncio.gather(*(fetch(session, u) for u in URLS))
    for url, status, info in results:
        print(f"{url} -> {status} ({info})")

asyncio.run(main())
```

**结论**：并发模式固定配方 = 一个 `ClientSession` + 一组 `fetch` 协程 + `gather` 汇总。

---

## 5. 工程级要点：限流、超时、错误

- **限流（rate limiting）**：用 `asyncio.Semaphore`（信号量）控制最大并发数，避免把对方打挂或被封。
- **超时**：`aiohttp.ClientTimeout` 强制请求在限定时间内结束，防止协程卡死。
- **错误处理**：捕获 `aiohttp.ClientError`（网络/协议错误）、`asyncio.TimeoutError`。

```python
sem = asyncio.Semaphore(10)   # 最多 10 个并发

async def fetch_limited(session, url):
    async with sem:           # 超出 10 个就排队等待
        async with session.get(url) as resp:
            return await resp.text()
```

**结论**：任何生产级异步爬虫/客户端都必须加并发上限与超时，否则可能压垮服务或被封。

## py.async.httpx_async

# 异步 HTTP 与 httpx：从 `asyncio` 到工程级并发

## 一句话直觉

**当你要同时请求 100 个网页 API 时，用同步代码会排队等 100 次网络往返；用 `asyncio` + `httpx` 可以让这 100 个请求“同时飞出去”，总耗时接近最慢的那一个。**

这就是 `py.async.httpx_async` 的核心价值：**用单线程实现 I/O 密集型（I/O-bound）任务的高并发**。

---

## 第 1 节：为什么需要异步？先看“同步的世界”

在同步（synchronous）代码里，`requests.get()` 一调用，整个程序就**卡住**，直到服务器返回。假设每个请求 0.5 秒，100 个请求就要 50 秒。

```python
# 同步版本：串行阻塞，总耗时 ≈ 100 × 单次耗时
import time
import requests

def fetch(url: str) -> int:
    r = requests.get(url)
    return len(r.text)

start = time.perf_counter()
results = [fetch("https://httpbin.org/delay/0") for _ in range(20)]
print(f"同步耗时: {time.perf_counter() - start:.2f}s")
```

**问题**：CPU 在等待网络时什么都没干。异步的目标就是：**等待时去干别的活**。

---

## 第 2 节：`asyncio` 三件套 —— 协程、事件循环、`await`

`asyncio` 是 Python 标准库中编写并发代码的基础（foundation）。它提供了三个核心概念：

| 术语 | 英文 | 作用 |
|---|---|---|
| 协程 | coroutine | 用 `async def` 定义的、可暂停/恢复的函数 |
| 事件循环 | event loop | 调度器，负责在合适时机恢复协程 |
| 等待 | await | “挂起当前协程，把控制权交还给事件循环” |

```python
# 最小 asyncio 示例：同时等待两个任务
import asyncio

async def say(name: str, delay: float) -> None:
    print(f"{name} 开始")
    await asyncio.sleep(delay)   # 模拟 I/O：非阻塞等待
    print(f"{name} 结束")

async def main() -> None:
    # gather 让两个协程并发执行
    await asyncio.gather(
        say("A", 1.0),
        say("B", 1.0),
    )

# 3.7+ 推荐的入口：asyncio.run
asyncio.run(main())
# 输出：A 开始 / B 开始 / A 结束 / B 结束，总耗时约 1 秒
```

**关键结论**：`await` 不是“启动一个线程”，而是告诉事件循环“我暂时不用 CPU，你先去跑别的协程”。所以它是**协作式（cooperative）** 并发。

---

## 第 3 节：进入 `httpx.AsyncClient` —— 异步 HTTP 客户端

标准库有 `urllib`、第三方有 `requests`，但它们都是同步的。`httpx` 提供了与 `requests` 几乎一致的 API，同时支持 `async/await`。

```python
# 安装：pip install httpx
import asyncio
import httpx

async def fetch(client: httpx.AsyncClient, url: str) -> int:
    # 复用 client，await 挂起当前协程等待响应
    resp = await client.get(url)
    return len(resp.text)

async def main() -> None:
    # 使用上下文管理器确保连接池正确关闭
    async with httpx.AsyncClient(timeout=10.0) as client:
        urls = ["https://httpbin.org/get"] * 10
        # 并发发起 10 个请求
        tasks = [fetch(client, u) for u in urls]
        results = await asyncio.gather(*tasks)
    print(f"共获取 {sum(results)} 字节")

asyncio.run(main())
```

### 为什么必须用 `AsyncClient` 而不是 `httpx.get()`?

- `httpx.get()` 是**同步**快捷函数，内部仍会阻塞。
- `AsyncClient` 支持**连接池复用（connection pooling）**：多个请求共享 TCP 连接，显著降低开销。
- `AsyncClient` 必须配 `async with` 使用，退出时自动 `aclose()`，避免资源泄漏。

---

## 第 4 节：从并发到“受控并发”—— 工程级写法

一次性发 10000 个请求会打爆服务器或本机文件描述符。生产代码要加**并发上限**。Python 标准库提供 `asyncio.Semaphore`：

```python
# 使用 Semaphore 控制最大并发数
import asyncio
import httpx

async def fetch_one(client: httpx.AsyncClient, url: str,
                    sem: asyncio.Semaphore) -> str:
    async with sem:  # 超过上限时在此处挂起等待
        resp = await client.get(url)
        return resp.text[:50]

async def main() -> None:
    sem = asyncio.Semaphore(10)          # 最多 10 个请求同时在途
    limits = httpx.Limits(max_connections=20, max_keepalive_connections=10)
    async with httpx.AsyncClient(limits=limits, timeout=10.0) as client:
        urls = [f"https://httpbin.org/get?i={i}" for i in range(50)]
        # return_exceptions=True 让单个失败不影响整体
        results = await asyncio.gather(
            *(fetch_one(client, u, sem) for u in urls),
            return_exceptions=True,
        )
    ok = sum(1 for r in results if not isinstance(r, Exception))
    print(f"成功 {ok}/{len(urls)}")

asyncio.run(main())
```

### 工程级清单

1. **复用 `AsyncClient`**：一个应用一个实例，别每个请求都新建。
2. **设置 `timeout`**：默认无超时会挂死。
3. **设置 `limits`**：限制连接数，保护对端与本机。
4. **用 `Semaphore` 限流**：控制并发任务数。
5. **`gather(..., return_exceptions=True)`**：单任务失败不炸全盘。
6. **`async with`**：确保连接池关闭。

---

## 结尾：动手练习

**任务**：写一个脚本 `async_check.py`，对下面 30 个 URL 并发发起 GET 请求，输出：

1. 每个 URL 的状态码（status code）
2. 成功数 / 失败数
3. 总耗时

要求：
- 使用 `httpx.AsyncClient` + `async with`
- 用 `asyncio.Semaphore(5)` 控制并发
- 用 `asyncio.gather(..., return_exceptions=True)` 收集结果
- 单独处理 `httpx.TimeoutException` 与 `httpx.HTTPStatusError`

```python
URLS = [f"https://httpbin.org/status/{code}" for code in
        [200, 200, 200, 200, 200, 200, 200, 200, 200, 200,
         404, 404, 500, 500, 200, 200, 200, 200, 200, 200,
         200, 200, 200, 200, 200, 200, 200, 200, 200, 200]]
```

**挑战加分项**：把并发数从 5 调到 50，观察总耗时变化，并解释为什么不会线性加速（提示：网络带宽、服务器限流、GIL 与 I/O 等待的关系）。


---

## 本课题目

### single_choice · None



- [A] 在 async 函数中使用 aiohttp.ClientSession 的 get 方法并 await
- [B] 在普通函数中使用 aiohttp.ClientSession 的 get 方法并直接获取返回值
- [C] 使用 requests.get 并配合 asyncio.run 包装
- [D] 在 async 函数中使用 aiohttp.ClientSession 的 get 方法但不 await

**参考答案**：0

**解析**：aiohttp 是异步 HTTP 库，其网络请求方法返回协程，必须在 async 函数中 await 才能获得响应。选项 B 会得到协程对象而非响应；选项 C 混淆了同步库 requests 与异步库；选项 D 不 await 同样无法获得响应。

### single_choice · None



- [A] 每次请求都应创建一个新的 ClientSession，用完立即关闭
- [B] ClientSession 应在多个请求间复用，并用 async with 管理其生命周期
- [C] ClientSession 只能在同步代码中使用
- [D] ClientSession 创建后不需要关闭，Python 会自动回收连接

**参考答案**：1

**解析**：官方推荐复用 ClientSession 以利用连接池，并用 async with 确保会话正确关闭。选项 A 频繁创建会丧失连接池优势；选项 C 与异步库定位矛盾；选项 D 不关闭可能导致连接泄漏和警告。

### single_choice · None



- [A] asyncio.TimeoutError
- [B] ValueError
- [C] KeyError
- [D] TypeError

**参考答案**：0

**解析**：aiohttp 超时通常抛出 asyncio.TimeoutError（或相关超时异常）。选项 B、C、D 是通用异常，不专门表示超时。

### single_choice · None



- [A] 使用 asyncio.Semaphore 控制并发数
- [B] 使用 for 循环逐个 await 请求
- [C] 设置 aiohttp.ClientSession 的 max_connections 为 0
- [D] 使用 time.sleep 在请求之间暂停

**参考答案**：0

**解析**：asyncio.Semaphore 可用于限制并发协程数量。选项 B 是串行不是限制并发；选项 C 的 max_connections 为 0 通常表示不限制或无效配置；选项 D 会阻塞事件循环。

### single_choice · None



- [A] 每次请求创建新 session 能获得最佳性能
- [B] 复用同一个 ClientSession 可以复用底层连接，提升性能
- [C] 连接池只对同步库有效
- [D] aiohttp 不支持连接池

**参考答案**：1

**解析**：ClientSession 内部维护连接池，复用可减少连接建立开销。选项 A 反而增加开销；选项 C 错误；选项 D 错误，aiohttp 支持连接池。

### single_choice · None



- [A] resp.ok 或检查 200 <= resp.status < 300
- [B] resp.success
- [C] resp.is_ok()
- [D] resp.code == 'OK'

**参考答案**：0

**解析**：aiohttp 响应提供 ok 属性表示状态码是否小于 400，也可手动检查 status 范围。选项 B、C、D 并非 aiohttp 的标准 API。

### single_choice · None



- [A] await asyncio.sleep(1)
- [B] 在协程中调用 time.sleep(1)
- [C] await resp.text()
- [D] 使用 async with 管理会话

**参考答案**：1

**解析**：time.sleep 是同步阻塞调用，会阻塞整个事件循环。asyncio.sleep 才是异步非阻塞。选项 C、D 是异步操作。

### single_choice · None



- [A] aiohttp 会自动抛出异常，无法获取响应
- [B] 可以正常获取响应对象，其 status 为 404
- [C] aiohttp 会重试直到成功
- [D] 404 响应没有响应体

**参考答案**：1

**解析**：aiohttp 默认不会因 HTTP 错误状态码抛出异常，仍可获取响应对象并检查 status。选项 A 错误；选项 C 不会自动重试；选项 D 404 也可能有响应体。

### single_choice · None



- [A] 使用 data 参数传入文件对象即可自动处理 multipart
- [B] 使用 files 参数或 aiohttp.FormData 构造 multipart 请求
- [C] aiohttp 不支持文件上传
- [D] 必须先把文件读成字符串再通过 json 参数发送

**参考答案**：1

**解析**：aiohttp 支持 files 参数或 FormData 构造 multipart/form-data 请求。选项 A 对文件对象处理不够明确，通常推荐 files/FormData；选项 C 错误；选项 D 方式不适用于二进制文件。

### single_choice · None



- [A] session.get(url, headers={'Authorization': 'Bearer token'})
- [B] session.get(url, header={'Authorization': 'Bearer token'})
- [C] session.get(url, custom_headers={'Authorization': 'Bearer token'})
- [D] session.get(url, HTTP_HEADERS={'Authorization': 'Bearer token'})

**参考答案**：0

**解析**：aiohttp 请求方法使用 headers 参数传递请求头。选项 B、C、D 的参数名不存在。

### single_choice · None



- [A] async with aiohttp.ClientSession() as session:
      async with session.get(url) as resp:
          ...
- [B] with aiohttp.ClientSession() as session:
      with session.get(url) as resp:
          ...
- [C] async with aiohttp.ClientSession() as session:
      with session.get(url) as resp:
          ...
- [D] with aiohttp.ClientSession() as session:
      async with session.get(url) as resp:
          ...

**参考答案**：0

**解析**：ClientSession 和响应对象都支持异步上下文管理器，应使用 async with。选项 B 的 with 不适用于异步上下文管理器；选项 C、D 混用同步与异步。

### single_choice · None



- [A] await resp.read()
- [B] await resp.bytes()
- [C] await resp.content()
- [D] resp.body

**参考答案**：0

**解析**：aiohttp 响应提供 read() 协程方法返回原始字节。选项 B 的 bytes() 不是标准方法；选项 C 的 content 是流属性；选项 D 的 body 不是标准属性。

### single_choice · None



- [A] async with aiohttp.ClientSession() as session:
      async with session.get(url) as resp:
          data = await resp.json()
- [B] async with aiohttp.ClientSession() as session:
      resp = session.get(url)
      data = resp.json()
- [C] with aiohttp.ClientSession() as session:
      resp = await session.get(url)
      data = resp.json()
- [D] async with aiohttp.ClientSession() as session:
      async with session.get(url) as resp:
          data = resp.json()

**参考答案**：0

**解析**：aiohttp 的响应对象本身也是异步上下文管理器，读取 json 需要 await。选项 B 缺少 await 且未使用上下文管理；选项 C 的 with 不能用于异步上下文管理器；选项 D 读取 json 未 await。

### single_choice · None



- [A] 请求根本不会发出
- [B] 连接可能无法及时释放，导致资源泄漏或警告
- [C] aiohttp 会自动转换为同步请求
- [D] 响应内容会被自动丢弃且不会影响连接

**参考答案**：1

**解析**：aiohttp 的响应对象需要被释放，否则连接可能无法归还连接池，造成资源泄漏。选项 A 错误，请求已经发出；选项 C 不会自动转换；选项 D 连接管理会受影响。

### single_choice · None



- [A] aiohttp 可以在没有事件循环的情况下运行
- [B] aiohttp 的异步操作依赖于 asyncio 事件循环，通常在 asyncio.run 或已有循环中执行
- [C] aiohttp 自己实现了独立于 asyncio 的事件循环
- [D] aiohttp 只能在线程池中运行

**参考答案**：1

**解析**：aiohttp 构建在 asyncio 之上，异步操作需要事件循环驱动。选项 A 错误，没有循环协程无法推进；选项 C 错误，它依赖 asyncio 循环；选项 D 错误，线程池不是其运行前提。

### single_choice · None



- [A] 在循环中依次 await 每个请求，保证顺序
- [B] 使用 asyncio.gather 并发执行多个由 session.get 构成的协程
- [C] 为每个请求创建一个新线程
- [D] 使用 time.sleep 控制请求间隔以避免并发

**参考答案**：1

**解析**：asyncio.gather 可以并发调度多个协程，充分发挥异步 I/O 优势。选项 A 是串行，效率低；选项 C 引入线程不符合异步库常用模式；选项 D 与并发目标相反。

### single_choice · None



- [A] session.post(url, json={'key': 'value'})
- [B] session.post(url, data={'key': 'value'}, json=True)
- [C] session.post(url, params={'key': 'value'})
- [D] session.post(url, files={'key': 'value'})

**参考答案**：0

**解析**：aiohttp 的 post 方法支持 json 参数自动序列化并设置 Content-Type。选项 B 对 data 传 dict 会按表单编码且 json=True 无意义；选项 C 的 params 是查询字符串；选项 D 的 files 用于文件上传。

### single_choice · None



- [A] 使用 aiohttp.ClientTimeout 并通过 timeout 参数传给请求或 ClientSession
- [B] 使用 socket.setdefaulttimeout
- [C] 使用 asyncio.sleep 配合 try/except
- [D] aiohttp 不支持超时设置

**参考答案**：0

**解析**：aiohttp 提供 ClientTimeout 对象，可传给 session 或单个请求。选项 B 是全局 socket 超时，不专门适配 aiohttp；选项 C 不是超时机制；选项 D 错误。

### single_choice · None



- [A] status 是一个协程，必须 await 才能获得状态码
- [B] status 是同步属性，直接访问即可获得 HTTP 状态码
- [C] status 只在请求失败时存在
- [D] status 返回的是字符串形式的响应体

**参考答案**：1

**解析**：响应对象的 status 是普通属性，直接访问即可。选项 A 错误，读取状态码不需要 await；选项 C 错误，成功响应也有状态码；选项 D 错误，状态码是整数。

### single_choice · None



- [A] text = resp.text
- [B] text = await resp.text()
- [C] text = resp.text()
- [D] text = await resp.text

**参考答案**：1

**解析**：aiohttp 的 text() 是协程方法，需要 await 调用。选项 A 和 C 得到的是方法或协程而非文本；选项 D 未调用方法。

### single_choice · None



- [A] 每次请求都创建一个新的 AsyncClient 实例，请求完立即关闭
- [B] 在多个协程间共用一个 AsyncClient 实例，并用 async with 管理其生命周期
- [C] 把 AsyncClient 作为模块级全局变量，从不关闭
- [D] 使用同步的 Client 并在协程中直接调用，让 httpx 自动转为异步

**参考答案**：1

**解析**：httpx.AsyncClient 持有连接池，复用同一实例可减少连接建立开销；用 async with 管理可确保连接被正确关闭。每次新建实例会丧失连接复用优势，全局不关闭会泄漏连接，同步 Client 在协程中调用是阻塞的、无法获得并发收益。

### single_choice · None



- [A] 依次 await 每个请求，这样最快
- [B] 用 asyncio.gather 把多个协程任务聚合后 await
- [C] 用 for 循环直接调用请求函数，不 await
- [D] 把请求放进子线程里用 join 等待

**参考答案**：1

**解析**：asyncio.gather 可以并发地调度多个协程并等待全部完成，是并发请求的常见方式。顺序 await 是串行执行；循环中不 await 只创建了协程对象并未执行；用线程 join 会阻塞事件循环，不是异步并发的正确做法。

### multi_choice · None



- [A] 同一个 AsyncClient 实例可以在多个协程间共享，以复用连接池
- [B] 请求方法返回协程对象，需要在事件循环中被 await 调度执行
- [C] 应使用 asyncio.gather 或等价机制来并发等待多个请求
- [D] AsyncClient 必须在每次请求后重新创建，否则会出错

**参考答案**：[0, 1, 2]

**解析**：共享 AsyncClient 实例可复用连接池；其请求方法是协程函数需要 await；并发等待常用 gather。每次请求都重建实例会丧失连接复用优势，并非必须，也不会因此「出错」。

### multi_choice · None



- [A] 为请求设置合理的超时
- [B] 对可能失败的请求做异常捕获并按需重试（带退避）
- [C] 使用信号量限制并发数，避免资源耗尽
- [D] 为每个请求都忽略所有异常并丢弃失败结果

**参考答案**：[0, 1, 2]

**解析**：设置超时、异常处理与重试、并发限流都是提高健壮性的手段。忽略所有异常并丢弃失败结果会掩盖问题，无法算作健壮性做法。

### multi_choice · None



- [A] gather 会并发地调度传入的协程/任务
- [B] gather 默认在某个任务抛异常时将该异常向上传播
- [C] 可以设置 return_exceptions=True 让异常作为结果被返回而不是抛出
- [D] gather 会强制把传入的协程改成串行执行

**参考答案**：[0, 1, 2]

**解析**：gather 并发调度任务，默认传播异常，设置 return_exceptions=True 可将异常作为结果返回。它不会把协程改成串行执行。

### fill_blank · None



**参考答案**：["gather", "asyncio.gather"]

**解析**：asyncio.gather 用于并发调度多个协程/任务并等待它们全部完成，是并发请求的常见聚合方式。

### fill_blank · None



**参考答案**：["aclose", "aclose()"]

**解析**：AsyncClient 的异步关闭方法是 aclose()，配合 async with 使用可自动关闭。同步客户端用的是 close()，异步场景应使用 aclose。

### fill_blank · None



**参考答案**：["Semaphore", "asyncio.Semaphore"]

**解析**：asyncio.Semaphore 是常见的并发限流原语，通过限定同时持有的许可数来控制并发请求数量。

### code_reading · None



**参考答案**：client.get(url) 返回的是协程对象，没有被 await，因此 resp 实际是协程而不是 Response，访问 resp.status_code 会失败（协程没有该属性），并且请求根本没有真正发出。应改为 resp = await client.get(url)。此外循环中逐个 await 是串行执行，无法并发，若想并发应把多个协程交给 asyncio.gather。

**解析**：异步客户端的请求方法是协程函数，不 await 就不会执行、拿不到 Response；直接访问协程的 status_code 会报错。同时顺序 await 属于串行，若要并发需聚合多个协程。

### code_reading · None



**参考答案**：这段代码会并发地发起 len(urls) 个请求，gather 使用 return_exceptions=True，因此某个请求失败或超时不会中断整体，失败项会以异常对象形式出现在 results 中。最后筛选出类型为 httpx.Response 的成功结果并打印其数量。即输出成功返回响应的请求个数。

**解析**：gather 并发调度任务，return_exceptions=True 让异常作为结果返回而非抛出，因此可以用 isinstance 区分成功响应与异常，统计成功数量。

### scenario · None



**解析**：每个请求新建客户端会丧失连接复用；在事件循环中调用同步阻塞库会卡住整个循环。改造思路是共享一个 AsyncClient（async with 管理生命周期）、用 asyncio.gather 并发调度请求、设置超时并做异常处理、用信号量限制并发数，从而兼顾性能与稳定。

### scenario · None



**解析**：无超时导致慢请求长期占用协程与连接；一次性并发全部请求缺少并发上限，下游变慢时本地连接与内存迅速增长。改进方案包括为请求设置超时、用 Semaphore 限制并发数、用 gather 时配合 return_exceptions 做异常处理，并按需重试退避。

### single_choice · None



- [A] AsyncClient 的请求方法（如 get）是协程函数，必须被 await
- [B] AsyncClient 的请求方法返回的是普通 Response 对象，无需 await
- [C] 同步 Client 在异步函数中使用时会自动切换为非阻塞模式
- [D] AsyncClient 不能设置超时，只能依赖系统默认值

**参考答案**：0

**解析**：AsyncClient 的 get/post 等方法是 async 函数，返回协程，需要 await 才能得到 Response。同步 Client 在事件循环中调用会阻塞整个循环。AsyncClient 同样支持 timeout 参数配置超时。

### single_choice · None



- [A] 不设置超时，依赖操作系统默认行为
- [B] 在每个请求上传入较短的 timeout，或为客户端设置默认 timeout
- [C] 捕获所有异常后无限重试直到成功
- [D] 把超时设置为极大值，保证请求一定成功

**参考答案**：1

**解析**：为请求或客户端设置合理的 timeout 能避免单个慢请求长期占用连接与协程。不设超时可能导致长时间挂起；无限重试在持续失败时会放大负载；把超时设得过大同样会拖慢整体。

### single_choice · None



- [A] gather 会自动忽略该异常，返回其余结果
- [B] gather 默认会把该异常向上抛出，调用处需要 try/except 处理
- [C] gather 会把该协程从事件循环中删除且不报错
- [D] gather 会把异常转换成返回值为 None

**参考答案**：1

**解析**：asyncio.gather 默认在任一子任务抛出异常时会将该异常传播到 gather 的 await 处，除非设置 return_exceptions=True 把异常作为结果返回。它不会自动忽略异常，也不会静默删除任务。

### single_choice · None



- [A] AsyncClient 不需要关闭，Python 会自动回收所有底层连接
- [B] 应调用 aclose() 或使用 async with 上下文，确保连接池被释放
- [C] 只能通过调用同步的 close() 来关闭异步客户端
- [D] 关闭客户端会取消所有已经提交但未完成的请求，因此不应关闭

**参考答案**：1

**解析**：AsyncClient 提供了 async 的 aclose() 方法，配合 async with 可确保退出时自动关闭并释放连接池。异步客户端不应调用同步 close（应使用 aclose）。关闭客户端不会主动取消已提交请求，通常是等待或取消后再关闭。

### single_choice · None



- [A] 并发请求数量越多越好，不需要限制
- [B] 使用信号量（Semaphore）等方式限制同时进行的请求数，避免压垮服务端或耗尽本地资源
- [C] 必须把所有请求改成串行执行以保证安全
- [D] 只要使用异步就永远不会出现资源问题

**参考答案**：1

**解析**：异步并发本身不限制并发度，无节制地发起大量请求可能耗尽连接、文件描述符或压垮目标服务。使用 asyncio.Semaphore 等限流是常见做法。串行会牺牲并发收益，异步也不等于没有资源风险。

### single_choice · None



- [A] 直接访问 response.json 属性即可得到字典
- [B] 使用 await response.aread() 读取后再解析，或直接 await response.json() 之类的异步接口
- [C] 必须先用 response.text 再手动 json.loads，且不能用于异步
- [D] 异步客户端不支持读取 JSON，只能读文本

**参考答案**：1

**解析**：httpx 的异步 Response 提供了异步读取方式（如 await response.aread() 读取字节，或 await response.json() 解析），不能像同步对象那样直接同步访问已就绪的 .json() 结果。异步客户端完全支持 JSON 解析。

### single_choice · None



- [A] 复用连接会显著增加每次请求的延迟，因此不推荐
- [B] 复用连接可以减少 TCP/TLS 握手开销，提升批量请求的整体效率
- [C] 只有同步客户端才支持连接复用，异步客户端不支持
- [D] 连接复用意味着请求必须串行执行，无法并发

**参考答案**：1

**解析**：HTTP keep-alive 允许同一连接上发送多个请求，省去重复的 TCP/TLS 握手开销，对批量请求有性能收益。异步客户端同样支持连接池与复用；复用连接并不要求请求串行，只是共享底层连接。

### single_choice · None



- [A] 没有影响，异步框架会自动把阻塞调用放到别的线程
- [B] 会阻塞整个事件循环，使其他协程无法推进，丧失并发能力
- [C] 只会阻塞当前协程，其他协程仍能正常运行
- [D] 会报语法错误，无法运行

**参考答案**：1

**解析**：事件循环是单线程的，阻塞调用会卡住整个循环，导致所有协程无法推进。异步代码中应使用非阻塞的等待方式（如 asyncio.sleep），阻塞型操作应放到线程或其他执行器中。
