# s5u1l1 Python HTTP 基础（py.web.http_basic） / FastAPI 基础入门：从 Hello World 到可上线的 API

> 来源 `content/lessons/s5u1l1.json`

## py.web.http_basic

# Python HTTP 基础（py.web.http_basic）

> **一句话直觉**：HTTP 是 Web 世界的“普通话”——你写的任何爬虫、API、Web 服务，本质上都在收发一段符合 HTTP 协议的文本。学会它，你才能和整个互联网对话。

---

## 一、HTTP 到底是什么？

**HTTP（HyperText Transfer Protocol，超文本传输协议）** 是应用层协议，核心规则非常简单：**客户端发一段格式化的文本（请求），服务器回一段格式化的文本（响应）**。就这么两件事。

一段 HTTP 请求长这样（原始字节）：

```
GET /index.html HTTP/1.1\r\n
Host: example.com\r\n
User-Agent: curl/8.0\r\n
\r\n
```

几个关键点：
- 第一行叫 **请求行（request line）**：方法 + 路径 + 版本
- 后面若干行是 **请求头（request headers）**：`Key: Value` 形式
- 一个**空行**（`\r
\r
`）表示头部结束，后面才是 **请求体（body）**
- 换行在 HTTP/1.1 规范里必须用 `\r
`（CRLF），不是 `
`

响应结构完全对称：状态行（`HTTP/1.1 200 OK`）+ 响应头 + 空行 + 响应体。

---

## 二、用 Python 最底层的方式发一次请求

先不借助任何库，直接开一个 **socket（套接字）**，亲手拼出 HTTP 请求字符串，看看服务器返回什么。

```python
import socket

# 1. 建立 TCP 连接（HTTP 建立在 TCP 之上）
s = socket.create_connection(("example.com", 80), timeout=5)

# 2. 手工构造 HTTP/1.1 请求字节（注意 \r\n 是协议规定的换行）
request = (
    "GET / HTTP/1.1\r\n"
    "Host: example.com\r\n"
    "Connection: close\r\n"   # 告诉服务器返回后关闭连接，方便读取
    "\r\n"
)
s.sendall(request.encode("ascii"))

# 3. 循环读取响应，直到服务器关闭连接
chunks = []
while True:
    data = s.recv(4096)
    if not data:
        break
    chunks.append(data)
s.close()

raw = b"".join(chunks)
print(raw.decode("utf-8", errors="replace")[:500])  # 打印前 500 个字符
```

跑通一次，你就真正理解了：**HTTP 不是什么魔法，就是一段有格式约定的字符串。** 由此也能解释为什么 `
` 和 `
` 混用会导致协议错误，为什么“空行”不能少。

---

## 三、更实用：用标准库 `http.client`

手写 socket 太累。**标准库 `http.client`** 已经帮你处理了协议细节（状态解析、Content-Length、分块编码等）。

```python
import http.client

conn = http.client.HTTPSConnection("example.com", timeout=5)
conn.request("GET", "/", headers={"User-Agent": "demo/1.0"})
resp = conn.getresponse()          # 拿到的就是结构化响应对象

print("状态码:", resp.status)       # 200
print("原因短语:", resp.reason)     # OK
print("Content-Type:", resp.getheader("Content-Type"))
body = resp.read()                  # 读取响应体（bytes）
print("响应体前80字节:", body[:80])
conn.close()
```

注意几点：
- `status` 是 **HTTP 状态码（status code）**：2xx 成功、3xx 重定向、4xx 客户端错误、5xx 服务端错误
- 响应体是 `bytes`，要转文本得知道字符集（响应头里的 `Content-Type: text/html; charset=utf-8`）
- `HTTPSConnection` 自动做 **TLS 握手**，你不用手写加密

---

## 四、工业级入口：`urllib.request` 与 `requests`

生产代码几乎不会直接写 `http.client`。首选两种：

**1) 标准库 `urllib.request`（零依赖）**

```python
import urllib.request

req = urllib.request.Request(
    "https://example.com",
    headers={"User-Agent": "demo/1.0"},
)
with urllib.request.urlopen(req, timeout=5) as resp:
    print(resp.status, resp.headers["Content-Type"])
    html = resp.read().decode("utf-8", errors="replace")
    print(html[:80])
```

**2) 第三方 `requests`（更友好，pip 安装）**

```python
# pip install requests
import requests

r = requests.get("https://example.com", timeout=5)
r.raise_for_status()                       # 4xx/5xx 直接抛异常
print(r.status_code, r.headers["Content-Type"])
print(r.text[:80])                         # 自动按响应头解码
print(r.json() if "json" in r.headers["Content-Type"] else "(非 JSON)")
```

工程选择建议：
- **脚本/一次性任务** → `requests`
- **零依赖/部署受限** → `urllib.request`
- **协议实验/教学** → `http.client`、`socket`
- **高并发批量请求** → `asyncio` + `aiohttp` / `httpx`（下一步学习）

---

## 五、拿数据：GET 参数、POST 表单与 JSON

HTTP 请求携带数据的两种最常见形式：

```python
import requests, json

# GET：数据放 URL 查询字符串
r = requests.get(
    "https://httpbin.org/get",
    params={"q": "python", "page": 1},   # 会自动编码成 ?q=python&page=1
    timeout=5,
)
print("GET 结果:", r.json()["args"])

# POST 表单：Content-Type 为 application/x-www-form-urlencoded
r = requests.post(
    "https://httpbin.org/post",
    data={"user": "alice", "pwd": "secret"},
    timeout=5,
)
print("表单结果:", r.json()["form"])

# POST JSON：Content-Type 为 application/json
r = requests.post(
    "https://httpbin.org/post",
    json={"name": "alice", "age": 30},
    timeout=5,
)
print("JSON 结果:", r.json()["json"])
```

记住语义差异：
- **GET**：只读、可缓存、参数在 URL、幂等
- **POST**：提交/创建、参数在 body、不幂等
- 幂等性决定了重试是否安全：GET/PUT/DELETE 一般可重试，POST 要小心

---

## 六、状态码与错误处理，别让脚本“突然死掉”

健壮的 HTTP 客户端必须处理超时、连接失败、非 2xx 状态码。

```python
import requests
from requests.exceptions import Timeout, ConnectionError, HTTPError

def fetch(url, retries=3):
    for i in range(retries):
        try:
            r = requests.get(url, timeout=(3, 10))  # (连接, 读取) 超时
            r.raise_for_status()
            return r
        except Timeout:
            print(f"第 {i+1} 次超时，重试...")
        except ConnectionError as e:
            print(f"连接失败: {e}，重试...")
        except HTTPError as e:
            # 4xx 通常重试无用，直接抛出
            print(f"服务端返回异常状态: {e}")
            raise
    raise RuntimeError("重试全部失败")

r = fetch("https://example.com")
print("成功，长度:", len(r.content))
```

要点：
- **必须设 timeout**，否则线程会挂死
- 区分**可重试**（超时、5xx、网络抖动）与**不可重试**（4xx，除 429）
- 生产环境要加 **指数退避（exponential backoff）** 和 **限速**

---

## 七、动手练习

**任务：写一个“迷你网页健康检查器”。**

1. 读入一个 URL 列表（写在代码里即可，例如 `["https://example.com", "https://httpbin.org/status/500", "https://httpbin.org/delay/5"]`）。
2. 对每个 URL：
   - 用 `requests.get` 发送请求，**设置 timeout=3**
   - 记录**状态码**、**响应时间（毫秒）**、**Content-Type**
   - 遇到异常不要崩溃，记录异常类型字符串即可
3. 把结果打印成一张对齐的表格（`str.ljust` 或 `f-string` 都可以）。
4. 额外挑战：把 timeout 改成 `(1, 1)`，观察 `httpbin.org/delay/5` 的表现，验证超时参数确实生效。

**验收标准**：程序不会因任何单个 URL 出错而退出；表格中能看到每个 URL 的成功/失败状态与耗时。

**进阶（可选）**：把循环改成 `concurrent.futures.ThreadPoolExecutor(max_workers=5)` 并发执行，让总耗时从“串行相加”变成“最慢那一个”，体会 IO 密集型任务的并发收益。

## py.web.fastapi_basic

# FastAPI 基础入门：从 Hello World 到可上线的 API

> **一句话直觉**：FastAPI 让你用「写普通 Python 函数」的方式，几行代码就能搭出一个带自动文档、类型校验、异步高并发的 Web API（Web Application Programming Interface，网络应用编程接口）——这是把 AI 模型变成「别人能调用的服务」的最短路径。

---

## 0. 为什么是 FastAPI？

在 AI 工程里，你的模型训练完之后，通常不是给自己看的，而是要给别人用：前端、App、其他微服务。这时候你要把模型包成一个 **HTTP 服务**（HyperText Transfer Protocol，超文本传输协议 服务）。

传统方案 Flask/Django 需要你手写请求解析、参数校验、文档。FastAPI 的核心卖点是三样：

1. **基于类型注解（Type Hints）** 自动校验和转换参数；
2. **自动生成的交互式文档**（Swagger UI / ReDoc）；
3. **原生支持 async/await**，适合 IO 密集型任务（比如调用大模型 API）。

它底层基于 **Starlette**（Web 框架）和 **Pydantic**（数据校验库）。

---

## 1. 安装与第一个 Hello World

先装依赖（`uvicorn` 是 ASGI 服务器，负责真正跑起来你的应用）：

```bash
pip install "fastapi[standard]"
```

写你的第一个应用：

```python
# main.py
from fastapi import FastAPI

app = FastAPI()  # 创建应用实例

@app.get("/")            # 装饰器：把函数绑定到 GET /
 def read_root():         # 注意缩进不要有前导空格
    return {"message": "Hello FastAPI"}
```

跑起来：

```bash
uvicorn main:app --reload
```

`main` 是文件名，`app` 是 FastAPI 实例变量名，`--reload` 让改动代码自动重启（开发用，生产别开）。

浏览器打开 `http://127.0.0.1:8000/docs`，你会看到自动生成的交互式文档——这就是 FastAPI 最爽的地方。

**关键结论**：一个路径 + 一个函数 + 一个装饰器 = 一个接口。返回值是 `dict`，FastAPI 自动序列化成 JSON。

---

## 2. 路径参数、查询参数与类型校验

Web API 的参数主要有两种来源：

- **路径参数（Path Parameter）**：写在 URL 路径里，如 `/items/42` 的 `42`；
- **查询参数（Query Parameter）**：写在 `?` 后面，如 `/items?skip=0&limit=10`。

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/items/{item_id}")
def read_item(item_id: int, q: str | None = None):
    # item_id 声明为 int，FastAPI 会自动把 "42" 转成 42，非数字返回 422 错误
    # q 有默认值 None，说明它是可选的查询参数
    return {"item_id": item_id, "q": q}
```

**关键结论**：

- 出现在路径里的参数 → 路径参数；
- 函数里带默认值的参数 → 查询参数；
- 类型注解不是装饰品，FastAPI 用它做 **运行时校验（Runtime Validation）**，类型错误自动返回 HTTP 422。

---

## 3. 请求体与 Pydantic 模型

POST/PUT 请求通常带 JSON body。FastAPI 用 **Pydantic 模型（Model）** 来描述和校验它——这也是它和 Flask 差异最大的地方。

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Item(BaseModel):          # 继承 BaseModel 即可定义 schema
    name: str
    price: float
    in_stock: bool = True       # 有默认值 → 可选字段

@app.post("/items")
def create_item(item: Item):    # 类型是 Pydantic 模型 → FastAPI 从 JSON body 解析
    return {"received": item, "total": item.price * 2}
```

试试在 `/docs` 里发一个 `{"name": "book", "price": 9.9}`，会成功；发 `{"name": "book"}`（缺 price）或 `price: "abc"`，会自动返回详细的 422 错误。你几乎没写校验代码——这就是 FastAPI 的工程价值。

---

## 4. 异步接口：什么时候用 async def

FastAPI 支持两种函数签名：

- `def f(): ...`  → 在线程池里跑，适合**同步阻塞**代码；
- `async def f(): ...` → 在事件循环里跑，适合 `await` 异步 IO（数据库、HTTP 调用、大模型 API）。

```python
import asyncio
from fastapi import FastAPI

app = FastAPI()

@app.get("/slow")
async def slow():
    await asyncio.sleep(1)     # 模拟异步 IO，不阻塞事件循环
    return {"slept": 1}
```

**关键结论**：如果接口里会 `await`（比如用 `httpx.AsyncClient` 调大模型），就用 `async def`；如果只是同步的 `requests.get` 或 CPU 重的推理，就保持 `def`，交给线程池，不要写 `async def` 里面又调阻塞代码——那会拖垮整个事件循环。

---

## 5. 工程化：分层、路由与错误处理

玩具代码写在 `main.py` 就够了，真实项目要分层：

```
app/
├── main.py            # 创建 FastAPI() 实例，注册路由
├── routers/
│   └── items.py       # APIRouter 按业务拆分
└── schemas.py         # Pydantic 模型集中放
```

```python
# app/routers/items.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/items", tags=["items"])

class Item(BaseModel):
    name: str
    price: float

@router.get("/{item_id}")
def get_item(item_id: int):
    if item_id <= 0:
        raise HTTPException(status_code=404, detail="item not found")
    return {"item_id": item_id}

# app/main.py
from fastapi import FastAPI
from app.routers import items

app = FastAPI(title="My API", version="0.1.0")
app.include_router(items.router)   # 把子路由挂到主应用
```

**关键结论**：

- 用 `APIRouter` 按业务拆分，避免 `main.py` 膨胀；
- 业务错误用 `raise HTTPException(status_code=..., detail=...)`，FastAPI 会返回标准 JSON 错误；
- 用 `include_router` 统一挂载，配合 `prefix` 和 `tags` 让文档更清晰。

到这里，你已经具备把一个 AI 模型封装成 HTTP 服务的最小能力了。


---

## 本课题目

### single_choice · None



- [A] 1xx
- [B] 2xx
- [C] 3xx
- [D] 4xx

**参考答案**：1

**解析**：2xx 类状态码表示请求已被成功接收、理解并处理，如 200 OK、201 Created。1xx 为信息性响应，3xx 为重定向，4xx 为客户端错误。

### single_choice · None



- [A] GET
- [B] POST
- [C] PUT
- [D] DELETE

**参考答案**：1

**解析**：POST 用于提交数据，通常不是幂等的，多次提交可能创建多个资源。GET 用于获取资源且幂等，PUT 用于更新或创建且幂等，DELETE 用于删除且幂等。

### single_choice · None



- [A] params
- [B] data
- [C] headers
- [D] cookies

**参考答案**：1

**解析**：data 参数用于提交表单数据，会被编码为 application/x-www-form-urlencoded。params 用于 URL 查询参数，headers 用于请求头，cookies 用于 Cookie。

### single_choice · None



- [A] GET 请求的参数通常放在 URL 中，POST 请求的参数通常放在请求体中
- [B] GET 请求不能携带任何参数
- [C] POST 请求只能用于上传文件
- [D] GET 请求必须使用 HTTPS

**参考答案**：0

**解析**：GET 请求的参数通过 URL 查询字符串传递；POST 请求的参数通常放在请求体中。GET 也可以带参数，POST 不限于上传文件，GET 不强制 HTTPS。

### single_choice · None



- [A] Content-Type
- [B] Content-Length
- [C] User-Agent
- [D] Accept

**参考答案**：0

**解析**：Content-Type 指示响应体的媒体类型，如 text/html、application/json。Content-Length 表示长度，User-Agent 是请求头，Accept 是请求头。

### single_choice · None



- [A] response.status
- [B] response.status_code
- [C] response.code
- [D] response.http_status

**参考答案**：1

**解析**：response.status_code 返回整数状态码。response.status 和 response.code 不存在，response.http_status 也不是标准属性。

### single_choice · None



- [A] 服务器内部错误
- [B] 请求的资源不存在
- [C] 客户端未授权
- [D] 请求被永久重定向

**参考答案**：0

**解析**：500 Internal Server Error 表示服务器在处理请求时发生内部错误。404 表示资源不存在，401 表示未授权，301 表示永久重定向。

### single_choice · None



- [A] Cookie
- [B] Set-Cookie
- [C] Authorization
- [D] Referer

**参考答案**：0

**解析**：客户端通过 Cookie 请求头将 Cookie 发送给服务器。Set-Cookie 是服务器响应头，Authorization 用于认证，Referer 表示来源页面。

### single_choice · None



- [A] response.json()
- [B] response.parse_json()
- [C] response.to_json()
- [D] response.loads()

**参考答案**：0

**解析**：response.json() 会将响应体解析为 Python 对象（字典或列表）。其他方法名不是 requests 的标准 API。

### single_choice · None



- [A] 重定向
- [B] 请求成功
- [C] 客户端错误
- [D] 服务器错误

**参考答案**：0

**解析**：3xx 类状态码表示重定向，如 301、302、304。2xx 表示成功，4xx 表示客户端错误，5xx 表示服务器错误。

### single_choice · None



- [A] URL 可以包含协议、主机、端口、路径、查询字符串和片段
- [B] URL 中不能包含端口号
- [C] URL 的片段部分会随请求发送到服务器
- [D] URL 只能使用 HTTP 协议

**参考答案**：0

**解析**：URL 由协议、主机、端口（可选）、路径、查询字符串和片段组成。片段（# 后内容）不会发送到服务器；URL 可用于多种协议。

### single_choice · None



- [A] response.headers
- [B] response.header
- [C] response.head
- [D] response.meta

**参考答案**：0

**解析**：response.headers 返回一个字典-like 对象，包含响应头。其他属性名不是 requests 的标准属性。

### single_choice · None



- [A] 请求的资源已被永久移动到新位置
- [B] 请求的资源暂时不可用
- [C] 客户端没有权限访问该资源
- [D] 服务器内部发生错误

**参考答案**：0

**解析**：301 Moved Permanently 表示资源已被永久重定向到新 URL。302 表示临时重定向，403 表示禁止访问，500 表示服务器内部错误。

### single_choice · None



- [A] Content-Type
- [B] 200 OK
- [C] GET /index.html HTTP/1.1
- [D] HTTP/1.1

**参考答案**：0

**解析**：Content-Type 是常见的请求头字段，用于描述请求体的媒体类型。200 OK 是状态行，GET /index.html HTTP/1.1 是请求行，HTTP/1.1 是协议版本。

### single_choice · None



- [A] requests.get('https://example.com')
- [B] requests.GET('https://example.com')
- [C] requests.get(url='https://example.com', method='GET')
- [D] requests.request('https://example.com')

**参考答案**：0

**解析**：requests.get(url) 是发送 GET 请求的标准写法。requests.GET 不存在；method 参数不是 get 的用法；requests.request 的第一个参数应为 HTTP 方法名。

### single_choice · None



- [A] 服务器无法找到请求的资源
- [B] 请求成功
- [C] 服务器内部错误
- [D] 请求被重定向

**参考答案**：0

**解析**：404 Not Found 表示服务器找不到请求的资源。200 表示成功，500 表示服务器内部错误，3xx 表示重定向。

### single_choice · None



- [A] 服务器不会在两个请求之间保留任何客户端上下文信息
- [B] 服务器会自动记住每个用户的登录状态
- [C] HTTP 请求必须携带 Cookie 才能工作
- [D] HTTP 连接一旦建立就永久保持

**参考答案**：0

**解析**：HTTP 是无状态协议，服务器默认不保留请求间的客户端状态。登录状态通常借助 Cookie/Session 等机制实现，并非协议本身自动记住。

### single_choice · None



- [A] text 返回解码后的字符串，content 返回原始字节
- [B] text 返回字节，content 返回字符串
- [C] 两者完全等价，没有区别
- [D] text 只能用于 JSON 响应，content 只能用于 HTML

**参考答案**：0

**解析**：response.text 会根据响应头中的编码将字节解码为字符串；response.content 返回原始字节数据，适合处理二进制内容。

### single_choice · None



- [A] 路径之后，以 ? 开始，键值对用 & 分隔
- [B] 请求头中，以 Query- 开头
- [C] 请求体中，以 JSON 格式发送
- [D] URL 的域名部分之前

**参考答案**：0

**解析**：查询参数附加在 URL 路径之后，以 ? 引导，多个参数用 & 连接，例如 /search?q=python&page=1。

### single_choice · None



- [A] 200
- [B] 301
- [C] 400
- [D] 500

**参考答案**：2

**解析**：400 Bad Request 表示客户端请求有误。200 表示成功，301 表示永久重定向，500 表示服务器内部错误。

### single_choice · None



- [A] 路径操作函数的返回值必须是 dict，否则 FastAPI 无法序列化
- [B] 使用 @app.get("/") 装饰器可以将函数注册为处理 GET 请求的路径操作
- [C] 必须手动继承某个基类才能让函数被 FastAPI 识别为路由
- [D] 路径只能通过 @app.route 装饰器注册，没有其他语法糖

**参考答案**：1

**解析**：FastAPI 使用 @app.get/@app.post 等装饰器把普通函数注册为路径操作，函数无需继承基类，返回值可以是 dict、Pydantic 模型、列表等，FastAPI 会通过 jsonable_encoder 处理序列化。

### single_choice · None



- [A] 字符串，因为 URL 中的部分都是文本
- [B] 自动转换为 int，若转换失败返回 422 请求错误
- [C] 自动转换为 int，若转换失败静默地变成 0
- [D] 必须显式加 Query(...) 才会转换类型

**参考答案**：1

**解析**：FastAPI 根据函数签名的类型注解进行参数解析和校验。声明为 int 时会将路径字符串转为整数，转换失败会返回 422 Unprocessable Entity。

### single_choice · None



- [A] 必须在代码中手动启用 /docs，否则默认不提供
- [B] 默认提供 /docs（Swagger UI）和 /redoc（ReDoc），基于 OpenAPI 规范生成
- [C] 只有 /redoc 是自动生成的，/docs 需要自己写
- [D] 文档只能描述 GET 接口

**参考答案**：1

**解析**：FastAPI 默认启用 /docs 与 /redoc，基于自动生成的 OpenAPI schema，覆盖所有路由与模型。

### multi_choice · None



- [A] 普通带注解的标量参数默认被当作查询参数
- [B] 路径中出现的 {name} 且函数参数同名时为路径参数
- [C] 声明为 Pydantic BaseModel 的参数会被当作请求体
- [D] Header、Cookie、Form 参数需要通过对应参数类（如 Header、Cookie、Form）显式声明
- [E] 所有参数默认都从请求体读取

**参考答案**：[0, 1, 2, 3]

**解析**：FastAPI 依据参数位置、名字与声明方式确定参数来源：标量为 Query、同路径名为 Path、Pydantic 模型为 Body，Header/Cookie/Form 需显式声明。参数并非默认从请求体读取。

### multi_choice · None



- [A] 共享数据库会话
- [B] 实现认证与权限校验
- [C] 抽取公共查询参数
- [D] 在函数间共享并复用业务逻辑
- [E] 替代所有中间件功能

**参考答案**：[0, 1, 2, 3]

**解析**：依赖注入常用于数据库会话、认证、公共参数与逻辑复用。它不等同于中间件，中间件处理请求/响应生命周期，二者用途不同。

### multi_choice · None



- [A] async def 在事件循环中执行，应避免内部存在阻塞 IO
- [B] def 路径操作会被放入线程池执行
- [C] 在 async def 中调用阻塞的 requests.get 会阻塞事件循环
- [D] 在 async def 中可以使用 await asyncio.sleep 让出控制权
- [E] def 与 async def 不能同时出现在同一项目中

**参考答案**：[0, 1, 2, 3]

**解析**：FastAPI 支持两种写法：async def 在事件循环中执行，需避免阻塞；def 会被放入线程池。它们可以混用。

### multi_choice · None



- [A] 在装饰器中设置 @app.post("/x", status_code=201)
- [B] 在函数中返回 Response 并指定 status_code
- [C] 在函数中返回 JSONResponse(content=..., status_code=201)
- [D] 在函数中 raise HTTPException(status_code=201)
- [E] 在函数参数中加 status_code=201

**参考答案**：[0, 1, 2]

**解析**：可通过装饰器的 status_code、Response/JSONResponse 的 status_code 指定成功状态码。HTTPException 用于错误响应，不应把 201 作为异常抛出。

### fill_blank · None



**参考答案**：["None", "null"]

**解析**：在 FastAPI 中，带类型注解的参数只要给出默认值就是可选查询参数。q: str = None 表示可选、默认 None。

### fill_blank · None



**参考答案**：["asyncio.sleep(1)", "await asyncio.sleep(1)"]

**解析**：在 async def 中应使用 await asyncio.sleep 让出事件循环。time.sleep 是阻塞调用，会阻塞整个事件循环。

### fill_blank · None



**参考答案**：["HTTPException", "fastapi.HTTPException"]

**解析**：FastAPI 提供 HTTPException，用于抛出 HTTP 错误，配合 status_code 和 detail 使用。

### code_reading · None



**参考答案**：返回 422 Unprocessable Entity，因为 item_id 被声明为 int，但路径中传入的 "abc" 无法转换为整数，FastAPI 的参数校验失败。

**解析**：FastAPI 依据类型注解做自动校验与转换，转换失败会返回 422，而非 500 或其他状态码。

### single_choice · None



- [A] def read(q: str):
- [B] def read(q: str = None):
- [C] def read(q: str = ...):
- [D] def read(*, q: str):

**参考答案**：1

**解析**：在 FastAPI 中，给带类型注解的参数提供默认值即表示它是可选查询参数。q: str = None 表示可选、默认 None；q: str 则为必填；q: str = ... 表示必填（等价于 Query(...)）。

### single_choice · None



- [A] 继承 pydantic.BaseModel 定义字段，并在路径操作函数中声明该类型参数
- [B] 直接把 dict 作为参数类型注解即可自动校验
- [C] 必须使用 dataclasses.dataclass 才能被识别为请求体
- [D] 请求体只能用 Form 形式，不能用 JSON

**参考答案**：0

**解析**：FastAPI 使用 Pydantic 模型定义请求体，函数中声明为某个 BaseModel 子类即可自动解析、校验并生成文档。

### single_choice · None



- [A] 只有 async def 定义的路径操作函数才支持并发
- [B] 普通 def 函数会被 FastAPI 放到线程池中执行，不会阻塞事件循环
- [C] async def 函数内部可以直接调用阻塞的 time.sleep 而不影响其他请求
- [D] FastAPI 不支持同步函数作为路径操作

**参考答案**：1

**解析**：FastAPI 中普通 def 路径操作会被放到线程池运行；async def 在事件循环中运行，如果内部有阻塞调用（如 time.sleep）会阻塞整个事件循环，应使用 await asyncio.sleep。

### single_choice · None



- [A] return {"status_code": 404}
- [B] raise HTTPException(status_code=404, detail="Not found")
- [C] return JSONResponse(content={}, status_code=200)
- [D] 直接 sys.exit(404)

**参考答案**：1

**解析**：FastAPI 提供 HTTPException，抛出后会生成对应状态码的 JSON 错误响应。也可以返回 Response/JSONResponse 并指定 status_code。

### single_choice · None



- [A] def read(db = Depends(get_db)):
- [B] def read(db: Session):
- [C] def read(db = get_db()):
- [D] def read(db: Depends[get_db]):

**参考答案**：0

**解析**：FastAPI 使用 Depends(get_db) 作为参数的默认值来声明依赖，FastAPI 会在调用前解析依赖。直接调用 get_db() 会在导入时执行函数，不是依赖注入。

### single_choice · None



- [A] 在函数 docstring 中写 Markdown 即可自动作为 summary
- [B] 使用 @app.get("/x", tags=["items"], summary="...", description="...")
- [C] 只能修改 openapi.json，无法通过装饰器设置
- [D] 必须手动维护 /docs 页面，FastAPI 不能自动生成

**参考答案**：1

**解析**：路径操作装饰器支持 tags、summary、description、response_model 等参数，用于丰富自动生成的 OpenAPI 文档。

### single_choice · None



- [A] response_model 只是文档用途，不影响实际响应内容
- [B] response_model 会对返回值做过滤与序列化，只保留模型声明的字段
- [C] response_model 必须与实际返回类型完全一致，否则报错
- [D] response_model 只能用于 POST 接口

**参考答案**：1

**解析**：response_model 既用于文档，也用于响应过滤和序列化，只输出 Pydantic 模型中声明的字段，多余字段会被过滤掉。

### single_choice · None



- [A] python app.py 直接运行即可（无热重载）
- [B] uvicorn app:app --reload
- [C] gunicorn app:app --reload
- [D] flask run

**参考答案**：1

**解析**：FastAPI 基于 ASGI，本地开发常用 uvicorn app:app --reload 启动并开启热重载。生产环境常用 gunicorn 与 uvicorn worker 组合。
