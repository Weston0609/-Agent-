# s5u1l2 用 async/await 写出高并发 Web 接口 / FastAPI 依赖注入（Depends）40 分钟讲义

> 来源 `content/lessons/s5u1l2.json`

## py.web.fastapi_async

# py.web.fastapi_async：用 async/await 写出高并发 Web 接口

> 一句话直觉：FastAPI 的异步接口，就是让一个 Python 进程在等数据库、等网络的时候“顺手去干别的活”，从而用很少的资源扛住大量并发请求。

---

## 1. 为什么需要 async：从“排队打饭”说起

先看同步（synchronous）代码的问题。假设每个请求都要等 1 秒 IO：

```python
# 同步版本：一个请求把线程占满 1 秒
import time

def fetch_user():
    time.sleep(1)          # 模拟数据库/网络 IO
    return {"id": 1}

def handle_request():
    return fetch_user()
```

如果 10 个请求同时来，同步模型要么排队（总耗时 10 秒），要么开 10 个线程（内存和上下文切换开销大）。

**异步（asynchronous）** 的核心思想：遇到 IO 等待时，把 CPU 让出去执行其他任务，等 IO 完成后再回来继续。Python 用 `async def` / `await` 语法表达这件事，底层由 **事件循环（event loop）** 调度。

```python
import asyncio

async def fetch_user():
    await asyncio.sleep(1)   # 关键：await 会把控制权交还事件循环
    return {"id": 1}

async def main():
    # 并发发起 10 个请求，总耗时约 1 秒，而不是 10 秒
    results = await asyncio.gather(*(fetch_user() for _ in range(10)))
    print(len(results))

asyncio.run(main())
```

**结论**：`await` 不是“等待”，而是“暂停当前协程（coroutine），让事件循环去跑别的协程”。

---

## 2. FastAPI 如何把 async 变成 Web 服务

**FastAPI** 是一个现代 Python Web 框架，它原生支持 `async def` 路由。当你的路径操作函数（path operation function）写成 `async def` 时，FastAPI 会在同一个事件循环里调度它。

```python
# 安装：pip install fastapi uvicorn
from fastapi import FastAPI

app = FastAPI()

@app.get("/sync")
def sync_hello():
    # 同步函数：FastAPI 会把它丢到线程池执行
    return {"mode": "sync"}

@app.get("/async")
async def async_hello():
    # 异步函数：直接在事件循环里执行
    return {"mode": "async"}
```

关键对比：

| 写法 | 执行位置 | 适合场景 |
|------|----------|----------|
| `def` | 线程池（threadpool） | 调用阻塞库（如 `requests`、同步 DB 驱动） |
| `async def` | 事件循环（event loop） | 调用异步库（如 `httpx`、`asyncpg`） |

**结论**：写成 `async def` 却调用阻塞函数，反而会卡死整个事件循环——这是新手最常见的坑。

---

## 3. 在 FastAPI 里真正做异步 IO

要让异步有价值，IO 操作本身也必须是异步的。下面用 `httpx` 的异步客户端调用外部 API：

```python
import httpx
from fastapi import FastAPI

app = FastAPI()

@app.get("/proxy")
async def proxy():
    async with httpx.AsyncClient() as client:
        # await 让出控制权，其他请求可以继续被处理
        resp = await client.get("https://httpbin.org/get")
    return {"status": resp.status_code}
```

如果这里换成同步的 `requests.get(...)`，事件循环会被阻塞，多个请求会串行排队。

**依赖注入（dependency injection）** 也可以异步：

```python
from fastapi import Depends

async def get_db():
    # 模拟异步获取数据库连接
    await asyncio.sleep(0.01)
    yield {"conn": "db"}

@app.get("/items")
async def items(db=Depends(get_db)):
    return {"db": db["conn"]}
```

---

## 4. 并发控制与后台任务

异步不等于“随便并发”。大量并发可能压垮下游，需要用信号量（semaphore）限流：

```python
import asyncio

sem = asyncio.Semaphore(5)   # 最多 5 个并发

async def limited_task(i):
    async with sem:
        await asyncio.sleep(0.1)
        return i
```

FastAPI 还提供 `BackgroundTasks` 处理“返回响应后再执行”的工作：

```python
from fastapi import BackgroundTasks

def write_log(msg: str):
    print("log:", msg)

@app.post("/notify")
async def notify(background_tasks: BackgroundTasks):
    background_tasks.add_task(write_log, "user notified")
    return {"ok": True}
```

**结论**：异步编程的两个核心工具是 `asyncio.gather`（并发）和 `Semaphore`（限流），配合 FastAPI 的 `BackgroundTasks` 能覆盖大多数 Web 场景。

---

## 5. 常见误区与工程建议

- **不要**在 `async def` 里写 `time.sleep`、同步 DB 查询、`requests`，否则事件循环会被阻塞。
- **不要**为了“看起来高级”全用 `async def`；如果底层库是同步的，用普通 `def` 让 FastAPI 丢线程池反而更安全。
- 调试时可用 `uvicorn main:app --reload` 启动，并观察并发行为。
- 生产环境建议用异步数据库驱动（如 `asyncpg`、`motor`）和异步 HTTP 客户端（`httpx`）。

记住一句话：**异步的收益来自“IO 等待时能切走”，没有异步 IO 库时，async 只是换了个写法而已。**

## py.web.fastapi_depends

# FastAPI 依赖注入（Depends）40 分钟讲义

## 一句话直觉

> **依赖注入（Dependency Injection）** 就是：让框架在调用你的接口函数前，自动把接口需要的“公共东西”（数据库连接、当前用户、配置、分页参数……）准备好并塞进参数里——你只写业务逻辑，不写重复的准备代码。

学它的理由：几乎所有真实 FastAPI 项目都靠 `Depends` 复用鉴权、数据库会话、分页、限流等横切逻辑。不会 `Depends`，就只会写玩具接口。

---

## 小节 1：为什么需要依赖？先看“没有依赖注入”的痛点

假设三个接口都需要“校验 token 并拿到用户”。最笨的写法是每个函数里复制一遍校验代码：

```python
# 反面示例：重复逻辑
from fastapi import FastAPI, Header, HTTPException

app = FastAPI()

def check(token: str):
    if token != "secret":
        raise HTTPException(status_code=401, detail="invalid token")
    return {"user": "alice"}

@app.get("/a")
def a(token: str = Header(...)):
    user = check(token)
    return {"route": "a", "user": user}

@app.get("/b")
def b(token: str = Header(...)):
    user = check(token)
    return {"route": "b", "user": user}
```

问题：逻辑重复、难测试、改动一处要改多处。**依赖注入**把这个公共逻辑抽成一个函数，交给 FastAPI 自动调用。

---

## 小节 2：`Depends` 最小示例——把函数变成“可注入依赖”

`Depends(dependency)` 传入一个可调用对象（函数、类、生成器）。FastAPI 会在请求进入时调用它，把返回值注入到参数上。

```python
# 最小可用示例
from fastapi import FastAPI, Depends, Header, HTTPException

app = FastAPI()

# 依赖：一个普通函数
def get_current_user(token: str = Header(...)):
    """FastAPI 也会解析依赖函数的参数声明（这里是 Header）。"""
    if token != "secret":
        raise HTTPException(status_code=401, detail="invalid token")
    return {"user": "alice"}

@app.get("/me")
def read_me(user: dict = Depends(get_current_user)):
    # user 就是 get_current_user 的返回值
    return {"hello": user["user"]}
```

要点：
- 参数默认值写成 `Depends(...)`，实际外部请求**不需要**传这个参数。
- 依赖函数里的参数（如 `token`）同样会被 FastAPI 解析和校验。

---

## 小节 3：依赖可以嵌套，形成“依赖树”

依赖本身还能依赖别的依赖。FastAPI 会构建依赖图（Dependency Graph），并按拓扑顺序执行、对同一请求内相同依赖做缓存（默认 `use_cache=True`）。

```python
# 嵌套依赖
from fastapi import FastAPI, Depends

app = FastAPI()

def get_config():
    return {"env": "dev"}

def get_db(config: dict = Depends(get_config)):
    # 假装连接数据库，用配置里的 env
    return {"db": f"db-{config['env']}"}

@app.get("/info")
def info(db: dict = Depends(get_db), config: dict = Depends(get_config)):
    # 同一请求内 get_config 只会执行一次（默认缓存）
    return {"db": db, "config": config}
```

---

## 小节 4：用 `yield` 写“带清理”的依赖（数据库会话的经典姿势）

数据库连接需要在请求结束后关闭。用 `yield` 的生成器依赖：`yield` 之前是准备，`yield` 的值会被注入，请求结束后继续执行 `yield` 之后的清理代码。

```python
# yield 依赖：请求前建立资源，请求后释放
from fastapi import FastAPI, Depends

app = FastAPI()

class FakeSession:
    def __init__(self): self.opened = True
    def close(self): self.opened = False

def get_session():
    session = FakeSession()
    try:
        yield session          # 注入给接口
    finally:
        session.close()        # 请求结束（含异常）后一定执行

@app.get("/db")
def use_db(session: FakeSession = Depends(get_session)):
    return {"session_opened": session.opened}
```

要点：
- `try/finally` 保证清理一定执行。
- 即使接口里抛异常，`finally` 也会运行。

---

## 小节 5：三类常用依赖写法（工程级套路）

1. **函数依赖**：最常用（鉴权、分页参数、配置读取）。
2. **类依赖**：把参数封装成类，`Depends(SomeClass)` 时 FastAPI 会实例化它，`__init__` 的参数同样会被解析。
3. **全局依赖**：`FastAPI(dependencies=[Depends(...)])` 或路由级 `dependencies=[...]`，对所有接口生效（如统一鉴权）。

```python
# 类依赖 + 路由级全局依赖
from fastapi import FastAPI, Depends, APIRouter, Header, HTTPException

class Pagination:
    def __init__(self, skip: int = 0, limit: int = 10):
        self.skip, self.limit = skip, limit

def require_token(token: str = Header(...)):
    if token != "secret":
        raise HTTPException(401, "invalid token")

router = APIRouter(dependencies=[Depends(require_token)])  # 该 router 下所有接口都要 token

@router.get("/items")
def list_items(page: Pagination = Depends(Pagination)):
    return {"skip": page.skip, "limit": page.limit}

app = FastAPI()
app.include_router(router)
```

你可以本地跑：

```bash
pip install fastapi uvicorn
uvicorn main:app --reload
# 访问 http://127.0.0.1:8000/docs 用 Swagger UI 直接测试
```

---

## 常见误区（Pitfalls）

1. **把 `Depends` 当装饰器用**：它只能作为参数默认值，或写在 `dependencies=[...]` 里。
2. **依赖函数带 async/sync 混用出错**：依赖函数可以是 `async def` 或 `def`，FastAPI 会正确调度；但别在 `def` 依赖里调用 `await`。
3. **误以为依赖每次请求都重新执行**：同一请求内相同依赖默认缓存；如需每次都执行，传 `Depends(fn, use_cache=False)`。
4. **`yield` 依赖里忘了 `try/finally`**：清理代码在接口抛异常时可能不执行。
5. **循环依赖**：A 依赖 B，B 又依赖 A，FastAPI 会启动失败——依赖图必须是有向无环图（DAG）。
6. **把依赖当全局单例**：依赖函数每次请求都会被调用（缓存仅限单请求内），跨请求共享状态要用数据库/外部存储。

---

## 动手练习

**任务**：写一个 FastAPI 应用 `main.py`，实现下面功能，并用 `uvicorn main:app --reload` 跑起来，在 `/docs` 里验证：

1. 写一个依赖 `get_api_key`：从请求头 `X-API-Key` 读取，若值不是 `"secret"` 就返回 `401`。
2. 写一个 `yield` 依赖 `get_resource`：`yield` 前打印 `"open"`，`finally` 里打印 `"close"`，`yield` 一个字典 `{"id": 42}`。
3. 写一个路由 `GET /protected`，同时注入上面两个依赖，返回 `{"resource": resource, "ok": True}`。
4. 用 `curl` 验证：
   - `curl -H "X-API-Key: secret" http://127.0.0.1:8000/protected` 返回 200；
   - `curl http://127.0.0.1:8000/protected` 返回 401。
5. **进阶**：把 `get_api_key` 通过 `APIRouter(dependencies=[...])` 挂到整个 router 上，让 `/protected` 之外再加一个 `/hello` 也自动受保护。

提示：在接口里故意 `raise` 一个异常，观察终端里 `"close"` 是否仍然打印——这验证 `yield` 依赖的清理语义。


---

## 本课题目

### single_choice · None



- [A] 由于函数是 async 定义的，阻塞调用会被自动放进线程池，不影响事件循环
- [B] 阻塞调用会占用事件循环线程，期间该 worker 无法处理其它请求
- [C] FastAPI 会在检测到阻塞时自动终止该请求并返回 500
- [D] 只有使用 def 定义的路由才会阻塞，async def 中的同步调用不会阻塞

**参考答案**：1

**解析**：async def 路由运行在事件循环线程中，任何同步阻塞调用都会卡住整个事件循环，导致同一 worker 上其它请求无法被处理。async def 不会自动把同步调用移入线程池。

### single_choice · None



- [A] 直接在事件循环线程中同步执行，因此会阻塞事件循环
- [B] 放入线程池执行，避免阻塞事件循环
- [C] 必须显式标注为线程执行，否则启动时报错
- [D] 转换为协程后在事件循环中执行

**参考答案**：1

**解析**：FastAPI 对普通 def 路由函数会通过线程池（anyio/starlette 的 run_in_threadpool）执行，从而不阻塞事件循环。它不会直接在事件循环线程中执行。

### single_choice · None



- [A] 用 asyncio.gather 并发执行这些任务，即可利用多核
- [B] 用线程池执行，因为线程可以绕过 GIL 做 CPU 并行
- [C] 交给进程池或后台任务进程处理，因为 asyncio 无法让 CPU 密集任务并行利用多核
- [D] 在事件循环中串行执行，因为没有更好的办法

**参考答案**：2

**解析**：asyncio 解决的是 I/O 并发，不是 CPU 并行；线程池受 GIL 限制也难以真正并行 CPU 任务。CPU 密集型应使用进程池等真正的多进程方案。

### single_choice · None



- [A] 用 asyncio.create_task 创建任务后，无需保存引用也不会被回收
- [B] 用 asyncio.create_task 创建任务时，应保存引用以防止任务被垃圾回收，且注意异常处理
- [C] 后台任务必须用 def 定义
- [D] 后台任务不能是协程，只能是普通函数

**参考答案**：1

**解析**：asyncio.create_task 创建的任务如果没有保存强引用，可能被垃圾回收导致任务提前取消；同时任务内异常需要妥善处理，否则可能被忽略。后台任务可以是协程。

### single_choice · None



- [A] 用 run_in_threadpool 在需要时把部分逻辑放到线程池
- [B] 改用进程池执行该 CPU 密集函数
- [C] 在 async 路由中直接同步调用该 CPU 密集函数
- [D] 将其作为独立服务或任务异步处理

**参考答案**：2

**解析**：在 async 路由中直接同步调用 CPU 密集函数会长时间阻塞事件循环，是最不推荐的做法。线程池、进程池或拆分服务都是更合理的缓解方式（CPU 密集更推荐进程）。

### single_choice · None



- [A] 中间件只能是同步函数，FastAPI 会在线程池中运行它
- [B] 中间件可以是 async 函数，也可以是普通函数，async 中间件中可以 await
- [C] 中间件中不能使用 await，否则请求会失败
- [D] 中间件必须继承自某个特定基类，且基类方法必须是同步的

**参考答案**：1

**解析**：FastAPI/Starlette 的中间件函数/类可以是 async 或普通函数，async 中间件中可以使用 await。并非只能同步，也不是不能 await。

### single_choice · None



- [A] 路由内需要做大量复杂矩阵运算，CPU 占用很高
- [B] 路由内主要通过 await 调用远程 API 和异步数据库
- [C] 路由内需要调用一个无法替换的同步阻塞 SDK
- [D] 路由内需要读写本地大文件并使用同步文件 API

**参考答案**：1

**解析**：async def 适合 I/O 密集型且使用异步客户端的场景，await 期间可让出事件循环。CPU 密集、无法替换的同步阻塞、同步文件 I/O 都不适合直接在 async 路由中执行。

### single_choice · None



- [A] open 会自动转为异步，没有问题
- [B] 读取期间会阻塞事件循环，影响同一 worker 上的其它请求
- [C] FastAPI 会拒绝在 async 路由中使用 open
- [D] 只有写文件会阻塞，读文件不会阻塞

**参考答案**：1

**解析**：同步 open/read 是阻塞调用，在 async 路由中执行会阻塞事件循环。应使用异步文件库或把文件操作放到线程池。读和写都会阻塞。

### single_choice · None



- [A] gather 会等待所有任务完成并返回结果列表，异常处理需注意
- [B] gather 只等待第一个完成的任务，其余会被取消
- [C] gather 只能用于普通函数，不能用于协程
- [D] gather 会阻塞事件循环直到所有任务完成

**参考答案**：0

**解析**：asyncio.gather 并发调度多个可等待对象，等待全部完成并返回结果列表；默认某个任务抛异常时会传播，需根据需求处理。它不会阻塞事件循环，而是挂起当前协程。

### single_choice · None



- [A] result1 = await op1(); result2 = await op2(result1)
- [B] result1 = op1(); result2 = op2(result1)
- [C] result1, result2 = await asyncio.gather(op1(), op2(result1))
- [D] await op1(); op2() 无需 await 即可

**参考答案**：0

**解析**：依赖关系下应按顺序 await：先 await op1 得到结果，再 await op2。不 await 会得到协程对象而非结果；gather 也不适合有依赖且 op2 需要 result1 的场景；op2 调用必须 await。

### single_choice · None



- [A] 必须返回可 JSON 序列化的对象，返回协程会由框架自动 await
- [B] 可以直接返回协程而无需 await，框架会处理
- [C] 返回普通 dict/list 会被自动序列化为 JSON
- [D] 必须返回 Response 对象，返回 dict 会报错

**参考答案**：2

**解析**：FastAPI 路由返回 dict/list 等会被自动序列化为 JSON；返回协程对象并非正确用法（框架不会替你 await 任意返回的协程），通常也不需要强制返回 Response 对象。

### single_choice · None



- [A] 用 try/except 捕获异常并用 raise HTTPException 转换为 HTTP 响应
- [B] 因为 async 中不能抛异常，只能返回错误码
- [C] 后台任务中未捕获的异常会自动转为 4xx 响应
- [D] 在 async 路由中不能用 try/except

**参考答案**：0

**解析**：在 async 路由中可以用 try/except 捕获异常，并用 HTTPException 或异常处理器转换成合适的 HTTP 响应。后台任务中未捕获的异常不会自动转成客户端响应。

### single_choice · None



- [A] 直接调用该同步函数，因为 async 上下文会自动并发
- [B] 用 asyncio.get_event_loop().run_until_complete(...) 直接执行它
- [C] 使用异步兼容的库；若无法替换，可用 run_in_threadpool 等把调用放到线程池
- [D] 在函数前加 await 关键字即可让它变为非阻塞

**参考答案**：2

**解析**：同步阻塞函数无法通过加 await 变为非阻塞；应改用异步库，或用 starlette.concurrency.run_in_threadpool（或 anyio.to_thread）把阻塞调用放到线程池。run_until_complete 在运行中的事件循环里会报错。

### single_choice · None



- [A] await 会让当前请求暂停，事件循环可在此期间处理其它任务
- [B] await 会阻塞整个事件循环直到被等待的操作完成
- [C] await 只能用于 def 定义的路由函数
- [D] await 的对象必须是普通函数，协程不能 await

**参考答案**：0

**解析**：await 会挂起当前协程并把控制权交还事件循环，使循环能运行其它任务，这正是异步并发的关键。await 用于可等待对象（协程、Future、Task 等），且必须在 async 函数内使用。

### single_choice · None



- [A] 依次 await 两个请求，因为 await 本身就会并行
- [B] 用 asyncio.gather 把两个协程一起调度，再 await 结果
- [C] 用 time.sleep 分隔两个请求以避免竞争
- [D] 把两个请求写在同一行用逗号分隔即可并发

**参考答案**：1

**解析**：依次 await 是串行的，总耗时是两者之和；asyncio.gather 可以把多个协程并发调度，总耗时接近较慢的那个。time.sleep 是阻塞调用，反而会卡住事件循环。

### single_choice · None



- [A] 该请求等待 5 秒，其它请求不受影响，因为各自独立
- [B] 事件循环被阻塞 5 秒，该 worker 上的其它请求也被延迟
- [C] time.sleep 在 async 函数中会抛出 RuntimeError
- [D] FastAPI 会自动把 time.sleep 转为异步等待

**参考答案**：1

**解析**：time.sleep 是同步阻塞调用，在事件循环线程中执行会阻塞整个循环，导致同 worker 上其它请求被延迟。异步代码中应使用 asyncio.sleep。

### single_choice · None



- [A] 依赖项必须是 async 函数，否则无法使用
- [B] 依赖项可以是 async 也可以是普通 def，框架会按相应方式执行
- [C] 依赖项只在路由为 async 时才会被解析
- [D] 依赖项中不能使用 await

**参考答案**：1

**解析**：FastAPI 依赖项既可以是 async def 也可以是 def；async 依赖会在事件循环中 await，普通 def 依赖会在线程池中执行。依赖项中可以使用 await（当它是 async 时）。

### single_choice · None



- [A] 在 async 路由中直接调用同步 ORM，因为 ORM 很快
- [B] 改用异步 ORM（如支持 async 的驱动），或用线程池执行同步 ORM 调用
- [C] 把路由改为 async 并加 await 在同步 ORM 调用前即可
- [D] 在同步 ORM 调用后加 asyncio.sleep(0) 就不会阻塞

**参考答案**：1

**解析**：同步 ORM 在 async 路由中会阻塞事件循环；应使用异步 ORM/驱动，或通过线程池执行。加 await 或 asyncio.sleep(0) 都不能消除同步阻塞。

### single_choice · None



- [A] async def 路由一定比 def 路由更快，无论内部做什么
- [B] 当路由内部进行 await I/O 时，能在等待期间让出事件循环以处理其它请求
- [C] async def 路由会自动启用多进程
- [D] async def 路由无需经过线程池，因此永远比 def 路由并发高

**参考答案**：1

**解析**：async def 的优势在于 await I/O 期间可以释放事件循环，提高 I/O 密集型并发；若内部是 CPU 密集或同步阻塞，优势不成立甚至更差。它不会自动多进程，也不能一概而论更快。

### single_choice · None



- [A] await asyncio.sleep(1)
- [B] await some_async_db.fetch()
- [C] requests.get('http://example.com')
- [D] await asyncio.gather(task1, task2)

**参考答案**：2

**解析**：requests.get 是同步阻塞调用，在 async 路由中会阻塞事件循环。asyncio.sleep、异步 DB 的 await、asyncio.gather 都是非阻塞或并发调度的写法。

### single_choice · None



- [A] 它会在每次请求处理前自动执行依赖函数，并把返回值作为参数注入到路径操作函数中
- [B] 它只能用于注入数据库连接对象，不能注入普通函数返回值
- [C] 它只在应用启动时执行一次，并把结果缓存给所有请求
- [D] 它必须通过装饰器 @Depends 显式声明在路径操作函数上

**参考答案**：0

**解析**：FastAPI 的依赖注入通过 Depends() 声明，在每次请求处理时执行依赖函数，并将其返回值注入到路径操作函数的参数中。它不是仅限数据库连接，也不是只执行一次，更不是用装饰器声明而是用参数默认值 Depends()。

### single_choice · None



- [A] 每次请求执行一次
- [B] 只在应用启动时执行一次
- [C] 每次请求执行两次
- [D] 从不执行，除非显式调用

**参考答案**：0

**解析**：默认情况下，Depends 的依赖函数在每次请求处理时都会被执行一次，不会缓存跨请求的结果。

### fill_blank · None



**参考答案**：["Depends", "fastapi.Depends", "Depends()"]

**解析**：FastAPI 通过在参数默认值中写 Depends(dependency) 来声明依赖注入，Depends 从 fastapi 导入。

### fill_blank · None



**参考答案**：["use_cache", "use_cache=False"]

**解析**：Depends(use_cache=False) 可禁用同一请求内的依赖结果缓存，使依赖在同一请求中每次被引用时都重新执行。

### fill_blank · None



**参考答案**：["之后", "后面", "after", "yield之后"]

**解析**：带 yield 的依赖，yield 之前的代码是 setup，yield 之后的代码是 teardown，会在响应发送后执行，用于资源清理。

### code_reading · None



**参考答案**：每次请求 get_db 执行一次（打印一次 "open db"），db 参数的值是 get_db 的返回值 "DB"。

**解析**：Depends(get_db) 会在每次请求时执行 get_db，默认在同一请求内缓存；其返回值被注入到 db 参数中。因此每次请求打印一次并返回 "DB"。

### code_reading · None



**参考答案**：输出顺序为：setup -> handler -> teardown。

**解析**：带 yield 的依赖：yield 之前的 setup 先执行；然后进入路径操作函数打印 handler；响应发送后回到 yield 之后打印 teardown。

### code_reading · None



**参考答案**：token 的值是 "abc"，由 FastAPI 自动调用 get_token 得到，不需要手动调用。

**解析**：Depends(get_token) 让 FastAPI 在请求处理时自动调用 get_token，并把返回值 "abc" 注入到 token 参数，无需手动调用。

### code_reading · None



**参考答案**：同一请求中 dep 只执行一次（只打印一次 "run"），a 和 b 都得到 1。

**解析**：FastAPI 默认 use_cache=True，同一请求内对同一依赖的多次引用只执行一次并复用结果，因此 a 和 b 都为 1。

### scenario · None



**解析**：应把用户信息读取和数据库会话分别封装为依赖函数，通过 Depends 注入到各路径操作。当前用户获取可用普通函数依赖返回用户对象；数据库会话应用带 yield 的依赖，yield 前创建会话、yield 后关闭，保证请求结束时释放资源。

### scenario · None



**解析**：直接在函数体内调用另一个依赖会绕过 FastAPI 的依赖解析，可能导致该依赖重复执行、无法复用请求内缓存、无法参与依赖树与校验等。正确做法是在依赖函数的参数上用 Depends(other_dep) 声明，由 FastAPI 解析嵌套依赖。

### scenario · None



**解析**：可把依赖写在路径操作装饰器的 dependencies=[Depends(...)] 中，这样适合做纯校验/副作用且返回值不注入。与作为函数参数默认值声明的区别在于：后者会在函数签名中出现参数并接收返回值，前者不会注入返回值。

### single_choice · None



- [A] use_cache=False 时，同一个请求中多次使用同一依赖会重复执行依赖函数
- [B] use_cache=False 时，依赖函数的结果会被永久缓存到磁盘
- [C] use_cache 默认值为 False
- [D] use_cache=True 时，依赖函数只在应用启动时执行一次

**参考答案**：0

**解析**：FastAPI 默认 use_cache=True，在同一请求内多次声明同一依赖时只执行一次并复用结果；设置 use_cache=False 会禁用该请求内缓存，导致重复执行。use_cache 不影响跨请求行为，默认也不是 False。

### scenario · None



**解析**：把会话等请求级资源缓存为全局变量会导致并发请求共享同一资源，引发数据串扰、事务混乱和会话泄漏，且难以正确关闭。更合适的做法是用 Depends 每请求创建/注入会话，带 yield 的依赖在响应后关闭，利用请求级隔离保证并发安全。

### single_choice · None



- [A] yield 之前的代码在请求处理前执行，yield 之后的代码在响应发送后执行，可用于清理资源
- [B] yield 之后的代码永远不会执行
- [C] 带 yield 的依赖不能用于依赖注入
- [D] yield 之后的代码在 yield 语句处立即执行

**参考答案**：0

**解析**：FastAPI 支持带 yield 的依赖，yield 前相当于 setup，路径操作函数执行并生成响应后，会回到 yield 之后执行 teardown/清理逻辑，类似上下文管理器。

### single_choice · None



- [A] 返回值不会被注入到路径操作函数参数中，仅用于执行校验或副作用
- [B] 返回值会自动作为第一个参数传入路径操作函数
- [C] 返回值必须为布尔类型，否则会报错
- [D] 返回值会被自动写入响应体

**参考答案**：0

**解析**：在路径操作装饰器的 dependencies 参数中声明的依赖，其返回值不会注入到函数参数，只用于执行校验、副作用等；只有作为函数参数默认值声明的依赖才会注入返回值。

### single_choice · None



- [A] 在依赖函数的参数中使用 param: Type = Depends(other_dep)
- [B] 在依赖函数体内调用 other_dep()
- [C] 使用 @Depends(other_dep) 装饰器装饰依赖函数
- [D] 在依赖函数上使用 @inject 装饰器

**参考答案**：0

**解析**：依赖可以嵌套：在依赖函数的参数上使用 Depends(other_dep)，FastAPI 会解析依赖树并逐层注入。直接调用 other_dep() 会绕过 FastAPI 的注入机制。

### single_choice · None



- [A] Depends 可以接受一个类作为依赖，FastAPI 会调用该类来创建实例并注入
- [B] Depends 只能接受函数，不能接受类
- [C] Depends 接受的类必须继承自 Depends 基类
- [D] Depends 接受类时，会直接注入类本身而不是实例

**参考答案**：0

**解析**：Depends 可以接受可调用对象，类也是可调用对象，FastAPI 会用其构造实例并注入。并不要求继承特定基类，注入的是实例而非类本身。

### multi_choice · None



- [A] 依赖可以形成嵌套依赖树，FastAPI 会自动解析
- [B] 同一请求内，默认对同一依赖只执行一次（use_cache=True）
- [C] 依赖函数的返回值一定会被注入到路径操作函数的参数中
- [D] 依赖可以声明在路径操作装饰器的 dependencies 参数中以执行校验
- [E] 带 yield 的依赖可用于请求结束后的资源清理

**参考答案**：[0, 1, 3, 4]

**解析**：依赖支持嵌套、默认请求内缓存、可放在装饰器 dependencies 中做校验、带 yield 可做清理。但只有在函数参数上声明为默认值的依赖，其返回值才会注入；装饰器 dependencies 中的依赖返回值不会注入，故 C 错。

### multi_choice · None



- [A] 在多个路径操作中复用数据库会话的获取与释放逻辑
- [B] 统一进行身份认证与权限校验
- [C] 在请求处理前后执行公共的日志或计时逻辑
- [D] 替代 Python 的 import 语句来加载模块
- [E] 分页参数的公共解析与校验

**参考答案**：[0, 1, 2, 4]

**解析**：依赖注入适合复用公共逻辑：数据库会话管理、认证鉴权、公共前置/后置处理、分页参数等。它不能替代 import 语句来加载模块，二者是完全不同的机制。

### multi_choice · None



- [A] yield 之前的代码在请求处理前运行
- [B] yield 之后的代码在响应发送完成后运行
- [C] 如果路径操作函数中抛出异常，yield 之后的代码仍有机会执行（取决于异常处理）
- [D] 带 yield 的依赖不能抛出 HTTPException
- [E] 带 yield 的依赖必须返回值，否则无法使用

**参考答案**：[0, 1, 2]

**解析**：带 yield 的依赖：yield 前是 setup，yield 后是 teardown，响应发送后执行；异常情况下 teardown 仍会执行。它可以在 yield 前后抛 HTTPException，也不要求必须有返回值（可以只做副作用）。
