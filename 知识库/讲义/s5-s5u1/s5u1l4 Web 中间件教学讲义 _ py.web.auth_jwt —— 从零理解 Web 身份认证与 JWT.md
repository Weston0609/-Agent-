# s5u1l4 Web 中间件教学讲义 / py.web.auth_jwt —— 从零理解 Web 身份认证与 JWT

> 来源 `content/lessons/s5u1l4.json`

## py.web.middleware

# py.web.middleware：Web 中间件教学讲义

## 一句话直觉

中间件（middleware）就是「横切在请求与响应之间的处理流水线」——你的业务代码只关心「谁请求了什么」，而认证、日志、限流、CORS 等公共逻辑都可以放到中间件里，让每个请求自动经过它们。

---

## 1. 为什么需要中间件：从「每个视图手写一遍」说起

假设你写了一个最朴素的 Web 应用。每写一个接口，你都要：记录日志、检查登录、加上 CORS 头、捕获异常。如果每个函数都复制这些代码，维护就是灾难。

中间件把这条「请求进来 → 处理 → 响应出去」的公共通道抽象成一个可插拔的函数。在 Python 生态里，最主流的两类中间件模型是：

- **WSGI 中间件**：以 Flask / Django 传统模式为代表，中间件是一个 `callable(environ, start_response)`。
- **ASGI 中间件**：以 FastAPI / Starlette 为代表，中间件是一个 `async def (scope, receive, send)`。

先用一个最小的 WSGI 例子感受「中间件 = 包在应用外层的函数」。

```python
# 一个最朴素的 WSGI 应用：接收 environ，返回响应
# WSGI 规定应用必须是 callable(environ, start_response)
def app(environ, start_response):
    start_response("200 OK", [("Content-Type", "text/plain")])
    return [b"Hello, world"]

# 手写一个中间件：在应用外面套一层日志
# 注意它接收一个 app，返回一个新的 app（装饰器模式）
def logging_middleware(inner_app):
    def wrapped(environ, start_response):
        print(f"[REQ] {environ['REQUEST_METHOD']} {environ['PATH_INFO']}")
        return inner_app(environ, start_response)
    return wrapped

# 组合：wrapped_app 才是最终运行的应用
wrapped_app = logging_middleware(app)

# 用标准库 wsgi 简单跑一下（Python 3 内置 wsgiref）
from wsgiref.simple_server import make_server

with make_server("", 8000, wrapped_app) as httpd:
    print("Serving on http://localhost:8000")
    httpd.handle_request()  # 只处理一个请求，便于演示
```

**关键结论**：中间件本质是「高阶函数」——输入一个 app，输出一个增强后的 app。多个中间件可以层层嵌套，形成「洋葱模型」。

---

## 2. 洋葱模型：请求下行，响应上行

当你有多个中间件时，执行顺序是这样的：

```
Client → MW1 → MW2 → MW3 → 你的视图
Client ← MW1 ← MW2 ← MW3 ← 你的视图
```

请求先经过 MW1、MW2、MW3 的**前置逻辑**，到达视图；响应再按相反顺序经过 MW3、MW2、MW1 的**后置逻辑**。理解这个「套娃」顺序，是排查中间件 bug 的第一把钥匙。

```python
# 演示洋葱模型：用嵌套函数模拟三层中间件
def make_mw(name):
    def middleware(inner):
        def wrapped(req):
            print(f"-> {name} 进入")       # 请求下行阶段
            resp = inner(req)               # 调用内层
            print(f"<- {name} 离开")       # 响应上行阶段
            return resp
        return wrapped
    return middleware

@make_mw("MW1")
@make_mw("MW2")
@make_mw("MW3")
def view(req):
    print("== 到达视图 ==")
    return "ok"

view("请求")
# 输出顺序:
# -> MW1 进入
# -> MW2 进入
# -> MW3 进入
# == 到达视图 ==
# <- MW3 离开
# <- MW2 离开
# <- MW1 离开
```

**关键结论**：越靠外的中间件越早看到请求、越晚看到响应。想做「全局计时」的中间件要放在最外层；想做「异常兜底」的中间件也应尽量放外层。

---

## 3. ASGI 中间件：异步时代的现代写法

FastAPI、Starlette、Django 3+ 都基于 ASGI 协议。ASGI 中间件是 `async def (scope, receive, send)`，其中 `scope` 描述连接信息，`receive` 是接收消息的异步函数，`send` 是发送消息的异步函数。

```python
# 一个 ASGI 中间件的最小骨架（不依赖任何框架）
import asyncio

# 真正的应用：发一条 http.response.start 和一条 http.response.body
async def app(scope, receive, send):
    assert scope["type"] == "http"
    await send({
        "type": "http.response.start",
        "status": 200,
        "headers": [(b"content-type", b"text/plain")],
    })
    await send({
        "type": "http.response.body",
        "body": b"Hello ASGI",
    })

# 中间件：给每个响应加一个自定义头 X-Elapsed
# 并在应用执行前后统计耗时
def timing_middleware(inner_app):
    async def wrapped(scope, receive, send):
        if scope["type"] != "http":
            return await inner_app(scope, receive, send)

        import time
        start = time.perf_counter()

        # 劫持 send，在响应开始前插入自定义头
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                elapsed = time.perf_counter() - start
                headers.append((b"x-elapsed", f"{elapsed:.4f}".encode()))
                message = {**message, "headers": headers}
            await send(message)

        await inner_app(scope, receive, send_wrapper)

    return wrapped

# 用 uvicorn 运行（pip install uvicorn）
# 保存为 demo.py，然后执行: uvicorn demo:timing_middleware(app) 需要包一层
# 更简单的方式：直接用 asyncio 手动驱动一次，便于验证
async def _manual_test():
    sent = []
    async def send(msg):
        sent.append(msg)
    async def receive():
        return {"type": "http.request"}

    scope = {"type": "http", "method": "GET", "path": "/"}
    await timing_middleware(app)(scope, receive, send)
    print(sent)

asyncio.run(_manual_test())
```

**关键结论**：ASGI 中间件通过「包装 send / receive」来改写通信过程。这一思想在 FastAPI 中表现为 `@app.middleware("http")`，在 Starlette 中表现为 `BaseHTTPMiddleware`。

---

## 4. 在真实框架里用中间件：FastAPI 快速上手

FastAPI 直接提供了 `@app.middleware("http")` 装饰器，让你不用手写 ASGI 细节。

```python
# 需要: pip install fastapi uvicorn
import time
from fastapi import FastAPI, Request

app = FastAPI()

# 一个记录耗时的中间件，给每个响应加上 X-Process-Time 头
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)   # 调用后续中间件或视图
    elapsed = time.perf_counter() - start
    response.headers["X-Process-Time"] = f"{elapsed:.4f}"
    return response

@app.get("/")
async def read_root():
    return {"message": "Hello"}

# 运行: uvicorn <文件名>:app --reload
# 然后 curl -i http://127.0.0.1:8000/ 可以看到 X-Process-Time 头
```

**关键结论**：框架级中间件 = 帮你把 ASGI 的「包装 send/receive」变成更友好的 `(request, call_next)` 接口。你只需关心 `call_next` 前后放什么逻辑。

---

## 5. 中间件的工程实践：顺序、异常与副作用

工程中，中间件最常见的用途有四类：

1. **日志 / 可观测性**：记录耗时、状态码、请求 ID。
2. **认证鉴权**：解析 token，注入 `request.state.user`。
3. **跨域（CORS）**：统一加 `Access-Control-Allow-*` 头。
4. **限流 / 熔断**：在进入业务前拦截。

顺序非常重要。比如认证中间件必须比业务路由先执行（放外层）；CORS 中间件通常也应该靠外层，否则错误响应不会被加上 CORS 头。

```python
# FastAPI 中注册多个中间件：注册顺序决定洋葱顺序
# 先 add_middleware 的在外层，后 add_middleware 的在内层
# from fastapi.middleware.cors import CORSMiddleware
# app.add_middleware(CORSMiddleware, allow_origins=["*"])
# app.add_middleware(OtherMiddleware)   # 这层在内侧
```

**关键结论**：中间件执行顺序 = 注册顺序；调试时如果发现响应头缺失或异常没被兜住，先检查「洋葱」的层序。

---

## 动手练习

**任务**：写一个 FastAPI 应用，实现一个「请求 ID」中间件。

要求：
1. 每个请求进入时生成一个 UUID（或递增序号），写入 `request.state.request_id`。
2. 在响应头中加入 `X-Request-ID`。
3. 在中间件里 `print` 一行日志：`[request_id] METHOD path`。
4. 定义两个接口：`GET /hello` 和 `GET /bye`，各自返回带 `request_id` 的 JSON。
5. 用 `curl -i` 验证：响应头里有 `X-Request-ID`，且 JSON 里的 id 与响应头一致。

提示：在中间件里用 `request.state.request_id = str(uuid.uuid4())`，视图函数通过 `request: Request` 参数读取。

进阶（可选）：再加一个「限流中间件」，对同一 IP 每秒最多 2 次请求，超出返回 429。

## py.web.auth_jwt

# py.web.auth_jwt —— 从零理解 Web 身份认证与 JWT

> **一句话直觉**：Web 服务器天生“健忘”，每个请求都是陌生人；JWT（JSON Web Token，JSON 网络令牌）就是服务器发给客户端的一张“防伪身份证”，客户端每次访问出示它，服务器不用查数据库也能立刻验证“你是谁、你能干什么、这张证什么时候过期”。

学完本节，你将能：说清认证（Authentication）与授权（Authorization）的区别；理解 JWT 的三段结构；用 Python 独立签发和校验 Token；并知道工程中必须避开的坑。

---

## 1. 为什么需要 JWT：HTTP 是“无状态”的

HTTP（HyperText Transfer Protocol，超文本传输协议）是**无状态（stateless）**协议：服务器收到第 2 个请求时，默认完全不记得第 1 个请求是谁发的。但登录后的页面显然需要“记住我”，于是有两种主流方案：

- **Session（会话）+ Cookie**：服务器把登录状态存在自己的内存/数据库里，只给客户端一个随机 ID（Session ID）。缺点是服务器要存状态，多台机器要共享存储。
- **Token（令牌）**：服务器把“身份信息”本身**签名后交给客户端保管**，客户端每次带上它。服务器不存状态，只要用密钥验证签名即可——这就是 JWT 的思路。

JWT 的核心价值：**无状态、可自包含（self-contained）、跨服务易传递**。代价是：一旦签发，在过期前很难主动作废（后面会讲缓解方案）。

---

## 2. 认证 vs 授权，以及 JWT 的三段结构

- **认证（Authentication，你是谁）**：验证用户名密码、验签 Token。
- **授权（Authorization，你能干什么）**：检查 Token 里的角色/权限（scope、role）。

一个 JWT 是形如 `xxxxx.yyyyy.zzzzz` 的字符串，由**三个 Base64URL 编码段**用点号拼接：

1. **Header（头部）**：说明签名算法，如 `{"alg": "HS256", "typ": "JWT"}`。
2. **Payload（载荷）**：存放声明（claims），如 `sub`（主体）、`exp`（过期时间）、`iat`（签发时间）以及自定义字段。
3. **Signature（签名）**：用密钥对 `header.payload` 做 HMAC（Hash-based Message Authentication Code，基于哈希的消息认证码）或 RSA/ECDSA 签名。

⚠️ **关键认知**：Header 和 Payload 只是 Base64URL 编码，**不是加密**！任何人都能解开看到内容。JWT 保证的是**完整性（没被篡改）**，不是**机密性（不被看见）**。

---

## 3. 用 Python 亲手签发与校验一个 JWT

工业界标准库是 `PyJWT`：`pip install PyJWT`。下面代码演示 HS256 的完整流程。

```python
import jwt  # 需要先 pip install PyJWT
import time

SECRET = "dev-secret-do-not-use-in-prod"  # 生产环境请从环境变量/密钥管理服务读取

# 1) 签发 Token
def create_token(user_id: str) -> str:
    payload = {
        "sub": user_id,          # subject：这个 token 代表谁
        "role": "admin",         # 自定义声明：授权信息
        "iat": int(time.time()), # issued at：签发时间
        "exp": int(time.time()) + 3600,  # expiration：1 小时后过期
    }
    # 用密钥 + HS256 算法签名
    return jwt.encode(payload, SECRET, algorithm="HS256")

# 2) 校验 Token
def verify_token(token: str) -> dict | None:
    try:
        # decode 会自动校验签名与 exp，失败会抛异常
        return jwt.decode(token, SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        print("Token 已过期")
    except jwt.InvalidTokenError as e:
        print(f"Token 非法: {e}")
    return None

token = create_token("user-42")
print("Token:", token)
print("解出的 payload:", verify_token(token))

# 篡改一个字符，签名立刻失效
bad = token[:-1] + ("a" if token[-1] != "a" else "b")
print("篡改后:", verify_token(bad))
```

跑一遍你会看到：正常 Token 能解出 payload；篡改后 `InvalidTokenError` 被触发。这验证了“防伪身份证”的比喻——**改动一个字，防伪标记就不匹配**。

---

## 4. 在 Web 框架中使用：从请求头取出 Token

真实场景中，客户端通常把 Token 放在 HTTP 头：`Authorization: Bearer <token>`。下面用 FastAPI 风格演示一个最小中间件。

```python
# 伪代码风格，示范拦截与校验流程
def get_current_user(request):
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise Exception("缺少认证头")
    token = auth.removeprefix("Bearer ")
    payload = verify_token(token)   # 复用上一节的函数
    if payload is None:
        raise Exception("未认证")
    return payload
```

**工程要点**：
- 用 `algorithms=["HS256"]` **白名单**，避免 `alg=none` 攻击（攻击者把算法改成 none 绕过签名）。
- 密钥**不要硬编码**，放在环境变量或密钥管理服务。
- 生产多服务建议用 **RS256**（RSA 非对称签名），签名私钥只有认证服务持有，其他服务用公钥验签。

---

## 5. 进阶：无状态带来的三个必修课

1. **过期与刷新**：`exp` 要短（如 15 分钟），配合 **Refresh Token（刷新令牌）** 单独换新，兼顾安全与体验。
2. **注销（unable to revoke）难题**：JWT 撤不回来。解决方案：维护一个短生命周期的**黑名单（blocklist）**，或把关键状态放进服务端 Redis 并以 jti（JWT ID）为键。
3. **不要在 Payload 放敏感数据**：它只是 Base64 编码，密码、身份证号会被任何人读到。

---

## 动手练习

**任务**：写一个 `jwt_demo.py`，包含：

1. `create_token(user_id, role, ttl=60)`：`ttl` 为有效期秒数。
2. `verify_token(token)`：校验签名、过期时间，返回 payload 或 `None`。
3. 用 `time.sleep(2)` 签发一个 `ttl=1` 的 Token，再验证，断言它已过期（`assert verify_token(t) is None`）。
4. **加分项**：把 SECRET 从 `os.environ["JWT_SECRET"]` 读取；再加一个字段 `scope`，写一个 `require_role(payload, role)` 返回 bool。

完成后你在本机就能完整跑通“签发 → 传输 → 校验 → 过期”的闭环。

> 小提醒：`pip install PyJWT` 装的包名是小写 `jwt`，不要和 Django 的 `djangorestframework-simplejwt` 混淆。


---

## 本课题目

### single_choice · None



- [A] 在处理函数内部，每条业务逻辑前后都手动记录一次时间
- [B] 编写一个可插拔的组件，包裹后续的请求处理流程，在处理前后记录时间，并可选择放行或拦截请求
- [C] 在服务器启动脚本里注册一个全局变量，把开始时间写入文件供处理函数读取
- [D] 为每个 URL 路由单独注册一个装饰器，在每个视图函数里重复相同的计时代码

**参考答案**：1

**解析**：中间件的核心是「包裹并串联请求处理流程」的可插拔组件，可以在请求进入视图前后统一插入横切逻辑；其他选项要么重复代码、要么破坏分层，不属于中间件式做法。

### single_choice · None



- [A] A 前、A 后、B 前、B 后
- [B] B 前、B 后、A 前、A 后
- [C] A 前、B 前、B 后、A 后
- [D] A 前、B 前、A 后、B 后

**参考答案**：2

**解析**：中间件采用包裹式调用，进入时按注册顺序执行「前」逻辑，到达视图后按相反顺序执行「后」逻辑，因此是 A 前→B 前→B 后→A 后。

### single_choice · None



- [A] 每个视图函数内部手动设置一次
- [B] 在中间件中统一为经过的响应添加 CORS 头
- [C] 在前端 JavaScript 中拦截响应后添加
- [D] 在数据库触发器中为查询结果附加 CORS 信息

**参考答案**：1

**解析**：CORS 是典型的横切关注点，中间件统一处理可避免每个视图重复；视图重复易漏，前端无法修改服务端响应头，数据库触发器与此无关。

### single_choice · None



- [A] 一个中间件只能有前处理，不能有后处理
- [B] 前处理在调用下游之前执行，后处理在调用下游返回之后执行
- [C] 后处理必须在视图函数内部编写，不能出现在中间件里
- [D] 前处理和后处理必须分别写在两个不同的中间件中

**参考答案**：1

**解析**：包裹式中间件天然支持在调用下游前后分别执行逻辑；A、C、D 都是对中间件能力的错误限制。

### single_choice · None



- [A] 数据竞争导致缓存内容错乱或程序异常
- [B] Python 解释器自动将列表改为线程安全
- [C] 请求会被自动串行化执行
- [D] 网络带宽自动翻倍

**参考答案**：0

**解析**：中间件共享状态需考虑并发安全，未加锁的可变结构在并发下会出现竞争；Python 不会自动保护自定义列表的复合操作，也不保证请求串行化；带宽与题干无关。

### single_choice · None



- [A] 能够统一拦截所有目标请求，避免在每个视图里重复编写限流代码
- [B] 可以让限流完全绕过网络层，直接修改 TCP 协议
- [C] 可以让限流逻辑运行在浏览器而不是服务器上
- [D] 可以让限流结果自动写入数据库表结构

**参考答案**：0

**解析**：中间件的价值在于对目标请求统一生效，减少重复；限流仍在应用层、服务器侧完成，与 TCP、浏览器执行、修改数据库结构无关。

### single_choice · None



- [A] 属于中间件的合法用途，因为它在响应阶段对统一路径的响应做了后处理
- [B] 不合法，中间件只能修改请求，不能修改响应
- [C] 不合法，404 必须在路由层拦截，中间件无法看到
- [D] 不合法，因为状态码是只读的，任何层都无法改变

**参考答案**：0

**解析**：响应后处理中间件可以检查并修改响应状态码或响应体，用于统一错误格式；B、C、D 都是对响应修改能力的错误否定。

### single_choice · None



- [A] 请求阶段从链头到链尾，响应阶段从链尾到链头，形成包裹结构
- [B] 请求阶段和响应阶段都按注册顺序从链头到链尾执行
- [C] 请求阶段从链尾到链头，响应阶段也从链尾到链头执行
- [D] 请求阶段和响应阶段没有固定方向，取决于视图函数

**参考答案**：0

**解析**：包裹式中间件链在进入请求时从外层到内层，响应返回时从内层到外层，因此请求与响应方向相反。

### single_choice · None



- [A] 在每个视图函数开头生成 UUID 并打印日志
- [B] 在中间件中为请求生成请求 ID，并把它放入请求上下文，供下游视图和日志使用
- [C] 在前端页面的 JavaScript 中生成 ID，然后通过 Cookie 传给后端
- [D] 在数据库中为每个请求插入一行，视图再从数据库读取该 ID

**参考答案**：1

**解析**：中间件适合集中生成请求级上下文（如请求 ID）并向下游透传；视图重复、前端生成不可信、依赖数据库读回增加耦合与开销，均不是首选。

### single_choice · None



- [A] 请求处理链断裂，下游中间件或视图无法正确获得请求，导致报错或行为异常
- [B] 框架会自动补全参数，使用者无需关心
- [C] 下游视图会自动改用上一个请求的数据继续运行
- [D] 浏览器会自动重新发起一次请求

**参考答案**：0

**解析**：中间件链依赖正确传递请求/响应等对象，传参错误会破坏链式调用；框架不会替开发者补全，也不会复用旧请求或让浏览器自动重发。

### single_choice · None



- [A] 两者完全等价，中间件必然由装饰器实现
- [B] 两者都可用于横切逻辑，但中间件通常作用于整个请求处理链，装饰器通常作用于单个函数或视图
- [C] 装饰器只能用于类，中间件只能用于函数
- [D] 中间件在浏览器执行，装饰器在服务器执行

**参考答案**：1

**解析**：两者都是横切关注点的实现手段，但作用范围与机制不同；中间件作用于请求链，装饰器作用于被装饰对象，二者并不必然互相实现。

### single_choice · None



- [A] 请求体被读取后无法再被下游读取，导致下游拿不到数据
- [B] 中间件会自动把大文件上传到磁盘
- [C] 服务器内存占用激增，甚至引发内存不足
- [D] 框架会自动拒绝所有超过 1KB 的请求

**参考答案**：2

**解析**：把大请求体一次性放入内存会造成内存压力；A 是否可重复读取取决于具体框架与实现，并非必然；B、D 与题干行为无直接因果关系。

### single_choice · None



- [A] 中间件在收到请求后只记录了 GET 请求，忽略了 POST 请求
- [B] 中间件未在框架规定的注册位置挂载，或某些特殊路由/静态资源在中间件链之前就被处理
- [C] 中间件里使用了 print 而不是 logging 模块
- [D] 中间件把请求的 User-Agent 当作大小写敏感字段来处理

**参考答案**：1

**解析**：中间件只有被正确注册并处于请求处理链上才会生效；未挂载或某些路径在链路之前被提前处理都会导致绕过。选项 A 并非“绕过”，而是过滤逻辑；C、D 与是否执行无关。

### single_choice · None



- [A] 中间件应该尽量包含业务逻辑，视图只负责返回模板
- [B] 中间件适合处理认证、日志、CORS 等横切关注点，视图应聚焦于具体业务
- [C] 中间件与视图职责完全相同，可以随意替换
- [D] 中间件只能处理请求，不能影响响应内容

**参考答案**：1

**解析**：中间件的定位是处理跨多个视图的横切关注点（认证、日志、CORS、压缩等），视图聚焦业务逻辑；中间件也能处理后端返回的响应。

### single_choice · None



- [A] 短路（提前拦截并返回响应，不再继续调用后续处理）
- [B] 回滚（撤销已经执行的事务）
- [C] 熔断（因错误率过高而暂停服务）
- [D] 缓存穿透（请求绕过缓存直接打到后端）

**参考答案**：0

**解析**：中间件不调用下游而直接产生响应称为短路；回滚是事务概念，熔断是容错策略，缓存穿透是缓存场景，均不符合题干。

### single_choice · None



- [A] 中间件之间通过全局变量直接互相调用
- [B] 每个中间件接收一个表示「链中后续处理」的可调用对象，并在合适时机调用它
- [C] 中间件之间通过数据库表传递请求对象
- [D] 中间件由浏览器按顺序逐个发起 HTTP 请求来执行

**参考答案**：1

**解析**：中间件链的典型实现是把「后续处理」作为参数传递给当前中间件，由它决定何时继续；其他选项把进程内调用误解为全局变量、数据库或浏览器行为。

### single_choice · None



- [A] 中间件无权访问响应对象，因此该做法一定会报错
- [B] 中间件可以访问并修改响应，只要框架允许在调用下游之后获得响应对象
- [C] 只有在响应已经发送给客户端之后，中间件才能修改响应
- [D] 中间件修改响应会导致请求被重新路由到其他视图

**参考答案**：1

**解析**：包裹式中间件在调用下游后可拿到响应对象并修改（如加响应头、压缩、改写内容）；A 过于绝对，C 时序错误，D 与路由无关。

### single_choice · None



- [A] 在调用下游处理的代码块外使用 try/except 包裹，捕获异常后构造并返回错误响应
- [B] 在中间件初始化时用 try/except 包裹注册语句，注册失败时返回错误页
- [C] 在视图函数内部用 try/except 包裹，每个视图重复写一次
- [D] 在服务器的启动参数里加上 --error-page，由运行时自动生成

**参考答案**：0

**解析**：中间件包裹下游调用，可在其外围捕获异常并统一处理，是异常处理中间件的典型实现；初始化时包裹注册语句与请求无关，视图内重复违背中间件初衷，启动参数不涉及异常页生成。

### single_choice · None



- [A] 中间件的执行顺序由字母顺序决定，与注册顺序无关
- [B] 认证中间件一般应放在日志中间件之前，以便未认证请求不被记录
- [C] 中间件的顺序会影响请求与响应阶段的执行次序，应结合依赖关系合理安排
- [D] 中间件的顺序不会影响功能，只要都注册了就能保证正确性

**参考答案**：2

**解析**：中间件顺序同时影响请求进入方向与响应返回方向的执行次序，依赖关系不同会改变结果，需要合理编排；字母顺序、固定前后、顺序无关的说法均不成立。

### single_choice · None



- [A] 连接数持续增长，最终耗尽数据库连接资源
- [B] 中间件将被框架自动卸载
- [C] 请求会被自动重定向到 /health
- [D] 视图函数将无法再被调用

**参考答案**：0

**解析**：中间件中管理连接属于资源生命周期问题，只创建不释放会导致连接泄漏；B、C、D 描述的行为与连接未关闭没有因果关系。

### single_choice · None



- [A] Header、Payload、Signature
- [B] Username、Password、Token
- [C] Session、Cookie、Nonce
- [D] Public Key、Private Key、Hash

**参考答案**：0

**解析**：JWT 结构固定为头部(Header)声明算法与类型、载荷(Payload)放声明、签名(Signature)用于校验完整性，三者以点号连接。

### single_choice · None



- [A] Payload 被加密，只有持有密钥者能读取
- [B] Payload 可被任何人解码读取，因此不应放敏感信息
- [C] Payload 一旦编码就无法修改
- [D] Payload 只有签名验证通过后才能解码

**参考答案**：1

**解析**：Base64Url 是编码而非加密，任何人都能解开查看内容，所以载荷中不能存放密码等敏感数据；防篡改靠的是签名。

### single_choice · None



- [A] 用户的角色标识
- [B] 令牌的签发时间 iat
- [C] 用户的明文登录密码
- [D] 令牌的唯一编号 jti

**参考答案**：2

**解析**：Payload 可被任何持有者解码读取，明文密码属于敏感信息绝不能放入；角色、iat、jti 等声明是常见且合适的用法。

### multi_choice · None



- [A] 服务端显式限定允许的签名算法白名单
- [B] 在 Payload 中存放用户明文密码以便免查库
- [C] 设置合理的短有效期并支持刷新令牌
- [D] 仅在 HTTPS 下传输令牌
- [E] 把签名密钥硬编码在客户端代码里

**参考答案**：[0, 2, 3]

**解析**：限定算法白名单可防算法混淆，短有效期与刷新令牌限制泄露窗口，HTTPS 防止中间人窃取。Payload 放明文密码和把密钥硬编码在客户端都是严重错误。

### multi_choice · None



- [A] 必须验证签名，不能只做 Base64 解码就信任内容
- [B] 必须检查 exp 等时间声明是否在有效期内
- [C] 应校验 iss、aud 等声明以确认令牌由预期的签发方、面向预期的受众
- [D] 只要 Payload 中有 role: admin 就可以直接授予管理员权限，无需签名校验

**参考答案**：[0, 1, 2]

**解析**：JWT 内容可被任意解码，只有通过签名与声明校验才可信任；iss/aud 防止令牌被挪用到其他系统。仅凭可读字段判断权限相当于完全放弃认证。

### multi_choice · None



- [A] 访问令牌有效期通常较短，用于访问受保护资源
- [B] 刷新令牌有效期更长，用于换取新的访问令牌
- [C] 刷新令牌泄露的危害通常比访问令牌更大，应更严格保护并支持吊销
- [D] 访问令牌应始终保持永久有效，避免用户重复登录

**参考答案**：[0, 1, 2]

**解析**：访问令牌短命、刷新令牌长命，是常见的折中方案。刷新令牌能换取新令牌，泄露后果更严重，需要更强的保护和吊销机制；访问令牌永久有效会极大放大泄露风险。

### multi_choice · None



- [A] 令牌签发后在过期前难以撤销，需要额外的黑名单或版本号机制
- [B] 无法在服务端直接修改令牌中的声明，只能重新签发
- [C] 令牌体积通常比会话 ID 大，会增加每次请求的传输开销
- [D] 无法在 Payload 中表达用户身份信息

**参考答案**：[0, 1, 2]

**解析**：无状态意味着服务端不保存储会话，撤销与修改声明需要额外机制；令牌自包含也带来体积开销。Payload 恰恰可以携带身份相关信息，故最后一项错误。

### fill_blank · None



**参考答案**：["exp", "exp claim", "expiration time", "exp(过期时间)"]

**解析**：exp 是 Expiration Time 的标准声明，用于表示令牌的过期时间点，校验时必须检查。

### fill_blank · None



**参考答案**：["aud", "audience", "aud claim"]

**解析**：aud 即 Audience，用于限定令牌的目标接收方；校验 aud 可以防止一个系统的令牌被拿到另一个系统上使用。

### code_reading · None



**参考答案**：它只对 Payload 做了 Base64Url 解码就依据其中的 role 字段授予权限，完全没有验证签名（也没有检查 exp 等声明）。由于 Payload 可被任何人解码甚至篡改，攻击者可以自行构造 role 为 admin 的载荷并得到管理员权限。正确做法是先验证签名与声明，再信任其中的内容。

**解析**：JWT 的安全性来自签名校验，而不是内容不可读。跳过验签直接使用声明等同于放弃认证，是最典型的 JWT 误用。

### code_reading · None



**参考答案**：它完全信任令牌头中的 alg 字段，并在 HS256 分支里用公开的公钥当作 HMAC 共享密钥来验签。攻击者可以把 alg 改成 HS256，并用已知的公钥对伪造载荷签名，从而通过校验。正确做法是服务端用白名单固定允许的算法，绝不接受来自令牌头的任意算法选择。

**解析**：这是典型的算法混淆攻击。验签方必须自行决定算法，不能由攻击者可控的令牌头来指定。

### scenario · None



**解析**：可行的改造包括：把令牌改存到 HttpOnly + Secure 的 Cookie，使脚本无法读取以缓解 XSS 窃取；若改用 Cookie 自动携带，需引入 CSRF 防护（SameSite 或 CSRF 令牌）；全站强制 HTTPS 防止传输窃听；同时配合短有效期与刷新令牌进一步压缩泄露窗口。

### single_choice · None



- [A] 因为算法字段决定了令牌的有效期
- [B] 因为不同算法的密钥长度不同
- [C] 因为如果不限定算法，攻击者可能把算法改为 none 或改用非对称公钥当作对称密钥来伪造签名
- [D] 因为算法字段会影响 Base64 解码结果

**参考答案**：2

**解析**：典型攻击包括算法置为 none 绕过验签、或把 RS256 公钥当 HS256 的密钥使用。因此服务端应显式白名单允许的算法，不能盲信令牌头。

### scenario · None



**解析**：常见做法有：维护令牌黑名单（按 jti 标识被吊销的令牌），但需要共享存储、回到部分有状态；或者给用户维护一个令牌版本号/密钥派生计数器，改密码或注销时递增，使旧令牌版本不匹配而失效；也可缩短有效期并配合刷新令牌，把失效延迟控制在较小范围。每种方案都要在安全性与存储、复杂度之间权衡。

### single_choice · None



- [A] 把密钥写在前端代码里，便于统一管理
- [B] 把密钥硬编码在客户端与服务端同一份源码中
- [C] 密钥只保存在服务端，通过环境变量或密钥管理服务注入，并定期轮换
- [D] 把密钥放进 JWT 的 Payload 里随令牌下发

**参考答案**：2

**解析**：签名密钥一旦泄露即可伪造任意令牌，必须只存在于服务端，通过环境变量或专用密钥管理服务注入，并支持轮换。

### single_choice · None



- [A] 忽略 exp，只要签名有效就继续放行
- [B] 自动把 exp 改成未来的时间后重新签名使用
- [C] 拒绝该令牌并要求客户端重新登录或刷新令牌
- [D] 仅当请求来自内网时才放行

**参考答案**：2

**解析**：exp 是过期时间声明，校验通过意味着令牌已失效，服务端应拒绝并引导重新认证。放宽过期检查会显著扩大令牌泄露的窗口期。

### single_choice · None



- [A] 减少服务端存储用户信息的空间
- [B] 在令牌泄露时把攻击窗口限制在较短时间内，同时用刷新令牌维持用户体验
- [C] 让每次请求都不必验签，提升性能
- [D] 避免使用 HTTPS

**参考答案**：1

**解析**：短命访问令牌降低泄露危害，刷新令牌用于换取新的访问令牌，从而兼顾安全性与用户不必频繁登录的体验。

### single_choice · None



- [A] 令牌不会被服务器读取
- [B] JavaScript 无法读取该 Cookie，降低 XSS 场景下令牌被窃取的风险
- [C] 可以完全免除 CSRF 攻击
- [D] 令牌长度会被自动压缩

**参考答案**：1

**解析**：HttpOnly 使脚本不能读取 Cookie，减小 XSS 直接偷走令牌的概率；但它并不免除 CSRF，仍需要 SameSite 或 CSRF 令牌等防护。

### single_choice · None



- [A] 一对公私钥中的私钥
- [B] 一对公私钥中的公钥
- [C] 同一个共享密钥
- [D] 用户的明文密码

**参考答案**：2

**解析**：HS256 等对称算法用同一密钥签名与验签，因此双方必须安全共享该密钥；RS256 等非对称算法才使用私钥签名、公钥验签。

### single_choice · None



- [A] 把它当作合法令牌，缺失的签名部分视作空串
- [B] 按无效令牌拒绝，因为合法 JWT 必须包含头、载荷、签名三段
- [C] 自动补一个签名段后接受
- [D] 只校验前两段即可放行

**参考答案**：1

**解析**：JWT 的紧凑序列化格式固定为三段，任何段缺失都说明令牌不合法，应当直接拒绝而不是做容错补全。

### single_choice · None



- [A] 没有风险，因为签名永远有效
- [B] 缓存若未与 exp 对齐，可能在令牌已过期后仍放行请求
- [C] 缓存能自动更新 exp 字段
- [D] 会导致签名算法被篡改

**参考答案**：1

**解析**：缓存必须覆盖包含 exp 在内的全部校验结论，并确保在令牌过期前失效；否则会出现已过期令牌仍被放行的窗口。
