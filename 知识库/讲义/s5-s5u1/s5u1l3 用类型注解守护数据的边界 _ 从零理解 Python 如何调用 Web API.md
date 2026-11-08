# s5u1l3 用类型注解守护数据的边界 / 从零理解 Python 如何调用 Web API

> 来源 `content/lessons/s5u1l3.json`

## py.web.pydantic_v2

# py.web.pydantic_v2：用类型注解守护数据的边界

## 一句话直觉

你写的 Web 接口每天都在和「不可信数据」打交道：前端传来的 JSON、第三方回调的 payload、数据库里读出的脏记录。**Pydantic v2 让你用普通的 Python 类型注解，自动完成数据校验、类型转换、序列化与文档生成**——让「数据形状」这件事从运行时的口口相传，变成可执行、可验证的代码契约。

它之所以重要，是因为在现代 Python Web 栈（FastAPI、SQLModel、LangChain、各类 AI Agent 框架）中，Pydantic v2 几乎是事实上的数据层标准。学它，等于拿到了整条工具链的入口钥匙。

---

## 1. 为什么需要数据校验：从「防御式 if」到「声明式模型」

在没有 Pydantic 的时代，你要手写大量 `if not isinstance(x, int)` 之类的代码，既啰嗦又容易漏。Pydantic 的核心思想是 **声明式（declarative）**：你把字段和类型写清楚，校验逻辑由框架推导。

Pydantic v2 的核心引擎用 Rust 重写（`pydantic-core`），速度相比 v1 提升 5–50 倍，同时 API 更统一：**校验入口只有一个**——`model_validate`。

```python
# 最小的 Pydantic 模型
from pydantic import BaseModel

class User(BaseModel):
    id: int
    name: str
    is_active: bool = True   # 带默认值，可省略

# 从 dict 校验并构造
user = User(id=1, name="Alice")
print(user)                 # id=1 name='Alice' is_active=True
print(user.model_dump())    # {'id': 1, 'name': 'Alice', 'is_active': True}
```

关键结论：`BaseModel` 的子类在实例化时自动校验，类型不符会抛 `ValidationError`，而不是悄悄放过。

---

## 2. 校验 + 强制转换：Pydantic 的「智能」边界

Pydantic 默认是 **宽松模式（lax mode）**：能无损转换就转，不能转才报错。例如字符串 `"42"` 可以变成整数 `42`，但 `"abc"` 不行。这符合 Web 场景——HTTP 传过来的永远都是字符串或 JSON。

如果要求严格模式（strict mode），加 `model_config = ConfigDict(strict=True)` 即可。

```python
from pydantic import BaseModel, ConfigDict, ValidationError

class Item(BaseModel):
    price: float
    quantity: int

# 宽松模式下："9.9" -> 9.9, "3" -> 3
item = Item(price="9.9", quantity="3")
print(item)                      # price=9.9 quantity=3

# 严格模式：不再做隐式转换
class StrictItem(BaseModel):
    model_config = ConfigDict(strict=True)
    price: float
    quantity: int

try:
    StrictItem(price="9.9", quantity=3)
except ValidationError as e:
    print(e.errors()[0]["type"])  # float_parsing
```

关键结论：默认宽松，符合 Web 输入现实；需要强约束时显式开 `strict=True`。

---

## 3. 嵌套与容器：描述真实世界的复杂结构

真实数据从来不是扁平的。Pydantic 让你直接使用 `list[...]`、`dict[...]`、`Optional[...]` 以及嵌套模型。

```python
from typing import Optional
from pydantic import BaseModel

class Address(BaseModel):
    city: str
    zipcode: str

class User(BaseModel):
    id: int
    name: str
    address: Optional[Address] = None
    tags: list[str] = []

# 嵌套 dict 自动转成 Address 实例，tags 自动校验
raw = {
    "id": 1,
    "name": "Bob",
    "address": {"city": "Shanghai", "zipcode": "200000"},
    "tags": ["vip", "new"],
}
u = User.model_validate(raw)
print(type(u.address).__name__)  # Address
print(u.address.city)            # Shanghai
```

关键结论：用类型组合描述嵌套结构，是 Pydantic 最强大的能力之一；`model_validate` 是 v2 推荐的统一入口（v1 的 `parse_obj` 已不推荐）。

---

## 4. 序列化与 JSON 边界：出入成对

校验（in）和序列化（out）是一对孪生问题。Pydantic v2 把两者方法名统一为 `model_validate` / `model_dump` / `model_dump_json`。

- `model_dump()`：转成 Python 原生 dict（适合内部传递）
- `model_dump_json()`：直接转 JSON 字符串（适合 HTTP 响应）
- `model_dump(mode="json")`：让 datetime、UUID 等变成 JSON 友好格式

```python
from datetime import datetime
from pydantic import BaseModel

class Event(BaseModel):
    name: str
    ts: datetime

e = Event(name="login", ts="2025-01-01T10:00:00")
# Python 模式：ts 是 datetime 对象
print(type(e.model_dump()["ts"]).__name__)     # datetime
# JSON 模式：ts 变成 ISO 字符串
print(e.model_dump(mode="json"))                # {'name': 'login', 'ts': '2025-01-01T10:00:00'}
print(e.model_dump_json())                      # {"name":"login","ts":"2025-01-01T10:00:00"}
```

关键结论：Web 场景下返回 `model_dump_json()` 或 `model_dump(mode="json")` 最省心。

---

## 5. 校验器与自定义约束：把业务规则写进模型

有时类型本身不够，你需要「价格必须大于 0」「密码必须含数字」这类业务规则。

- **约束类型**：`Annotated[int, Field(gt=0)]` —— 声明式、性能好
- **字段校验器**：`@field_validator` —— 单字段逻辑
- **模型校验器**：`@model_validator` —— 跨字段逻辑

```python
from typing import Annotated
from pydantic import BaseModel, Field, field_validator, model_validator

class Order(BaseModel):
    price: Annotated[float, Field(gt=0)]     # 必须 > 0
    quantity: Annotated[int, Field(ge=1)]    # 必须 >= 1
    discount: float = 0.0

    @field_validator("discount")
    @classmethod
    def discount_not_exceed_price(cls, v: float) -> float:
        if v < 0:
            raise ValueError("discount must be >= 0")
        return v

    @model_validator(mode="after")
    def check_total(self) -> "Order":
        # 跨字段：折扣不能超过总价
        if self.discount > self.price * self.quantity:
            raise ValueError("discount exceeds total")
        return self

print(Order(price=10, quantity=2, discount=5))   # OK
# Order(price=1, quantity=1, discount=100) 会抛 ValidationError
```

关键结论：能用 `Field` 约束就优先用它；单字段规则用 `@field_validator`；跨字段用 `@model_validator(mode="after")`。

---

## 6. 工程级实践：配置、别名与模型复用

Web 接口的字段名常和 Python 命名规则冲突（如 `user-id`），或需要从环境变量读配置。Pydantic 提供 `alias`、`populate_by_name`，以及配套的 `pydantic-settings`。

```python
from pydantic import BaseModel, ConfigDict, Field

class ApiUser(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    user_id: int = Field(alias="userId")     # 兼容外部命名
    user_name: str = Field(alias="userName")

# 既支持 "userId" 也支持 Python 风格
print(ApiUser(userId=1, userName="Alice"))
print(ApiUser(user_id=2, user_name="Bob"))
```

配置类（替代 v1 的 `Config` 内部类）统一用 `model_config = ConfigDict(...)`，常用项：`extra="forbid"`（拒绝未知字段）、`frozen=True`（不可变）、`str_strip_whitespace=True`。

关键结论：v2 的一切「模型级配置」都通过 `model_config = ConfigDict(...)` 声明，这是 v1 迁移时最容易踩坑的地方。

---

## 动手练习

**任务：写一个「用户注册请求」的校验模型**

要求：
1. 定义 `RegisterRequest`，字段包括：
   - `username`：3–20 个字符
   - `email`：字符串类型（提示：可以直接用 `str`，或尝试 `pydantic.EmailStr`）
   - `age`：整数，范围 18–120
   - `password`：至少 8 位
   - `confirm_password`：与 `password` 一致
   - `tags`：字符串列表，可为空，默认 `[]`
2. 用 `model_validator(mode="after")` 校验 `password == confirm_password`
3. 用 `model_config = ConfigDict(extra="forbid")` 拒绝未知字段
4. 用一段 `try/except ValidationError` 演示错误输出格式（打印 `e.errors()`）
5. 最后用 `model_dump(exclude={"password", "confirm_password"})` 演示安全序列化

完成后，你就能直接把这个模型接到 FastAPI 的 POST 请求里。

## py.web.openapi

# py.web.openapi：从零理解 Python 如何调用 Web API

> **一句话直觉**：学 OpenAPI，本质上就是学会“用 Python 跟网上的服务对话”——就像给远方的服务器写信、等回信、解析回信，一切都有一套标准格式。

---

## 1. 什么是 Web API 和 OpenAPI？

**Web API（Web Application Programming Interface，网络应用编程接口）** 是运行在远程服务器上的“函数”，你通过 HTTP（HyperText Transfer Protocol，超文本传输协议）向它发请求，它返回数据（通常是 JSON，JavaScript Object Notation，JavaScript 对象表示法）。

**OpenAPI（Open Application Programming Interface Specification，开放 API 规范）** 是一份用 JSON 或 YAML 写成的“说明书”，描述一个 Web API 有哪些端点（endpoint）、需要什么参数、返回什么结构。工具可以根据它自动生成客户端代码。

为什么学它？因为**几乎所有现代软件都要联网**：查询天气、调用大模型、读取数据库、对接支付……而 Python 是最常用的“胶水语言”，90% 的联网请求都用 `requests` 或 `httpx` 完成。

```python
# 最小示例：用 requests 访问一个公开 API
import requests

# GET 请求：向服务器“索要”数据
resp = requests.get("https://api.github.com/zen")
print(resp.status_code)   # 200 表示成功
print(resp.text)          # 服务器返回的短句
```

---

## 2. HTTP 请求的四要素：方法、URL、头、体

每次请求都像寄一封信：

| 要素 | 类比 | 例子 |
|------|------|------|
| 方法（Method） | 你要做什么 | GET（读）、POST（建）、PUT（改）、DELETE（删） |
| URL | 收件地址 | `https://api.example.com/users` |
| 请求头（Headers） | 信封上的备注 | `Authorization: Bearer xxx`、`Content-Type: application/json` |
| 请求体（Body） | 信的内容 | POST 时发送的 JSON 数据 |

```python
import requests

# POST 带 JSON 体与自定义头
resp = requests.post(
    "https://httpbin.org/post",
    headers={"Content-Type": "application/json"},
    json={"name": "Alice", "age": 30},
)
print(resp.json())  # 服务器把收到的数据原样返回
```

**关键结论**：方法决定语义，URL 决定目标，头决定“你是谁/发什么格式”，体决定“发什么内容”。

---

## 3. 状态码与错误处理：不是每次都能成功

服务器用 **状态码（Status Code）** 告诉你结果：

- `2xx` 成功（200 OK、201 Created）
- `4xx` 你错了（400 参数错、401 未认证、404 找不到）
- `5xx` 服务器错了（500 内部错误）

```python
import requests

resp = requests.get("https://api.github.com/users/torvalds")

# 主动抛异常而不是静默失败
if resp.status_code == 200:
    data = resp.json()
    print(data["login"], data["public_repos"])
else:
    print(f"请求失败：{resp.status_code}")
```

**工程级做法**：用 `resp.raise_for_status()`，它会在 4xx/5xx 时自动抛出异常，配合 `try/except` 使用。

---

## 4. OpenAPI 规范：自动生成客户端代码

如果服务端提供了 OpenAPI 文档（通常位于 `/openapi.json`），你可以用工具一键生成 Python 客户端，避免手写每个请求。

```python
# 示例：读取一份 OpenAPI 文档的骨架
import requests

doc = requests.get("https://petstore3.swagger.io/api/v3/openapi.json").json()
print(doc["info"]["title"])      # 服务名
print(list(doc["paths"].keys())) # 所有端点
```

**为什么重要**：在微服务（Microservices）和 AI 应用（如调用大模型）中，接口经常变动；用 OpenAPI 生成客户端，能让代码随文档自动同步，减少手工出错。

---

## 5. 从脚本到工程：超时、重试、异步

一个健壮的客户端至少要有：

- **超时（Timeout）**：网络可能永远不返回，必须设上限。
- **重试（Retry）**：瞬时故障很常见。
- **异步（Async）**：并发调用上百个端点时不能顺序等待。

```python
import asyncio
import httpx

async def fetch(url):
    async with httpx.AsyncClient(timeout=5.0) as client:
        r = await client.get(url)
        return r.status_code

async def main():
    # 并发请求多个 URL
    urls = ["https://api.github.com/zen"] * 3
    results = await asyncio.gather(*(fetch(u) for u in urls))
    print(results)

asyncio.run(main())
```

**关键结论**：单线程下 `httpx.AsyncClient` + `asyncio.gather` 能轻松并发几十上百个请求，而不会因等待 I/O 而阻塞。


---

## 本课题目

### single_choice · None



- [A] name: str = Field(alias='full_name')
- [B] name: str = Field(alias_name='full_name')
- [C] name: str = Field(alias='full_name', populate_by_name=True)
- [D] name: str = Field(alias='full_name', allow_population_by_field_name=True)

**参考答案**：2

**解析**：Pydantic v2 中通过 Field(alias=...) 设置别名，若还要允许用字段原名填充，需设置 populate_by_name=True。A 项只设置别名，默认不再接受原字段名；B 项 alias_name 不存在；D 项 allow_population_by_field_name 是 v1 的参数，v2 已改名。

### single_choice · None



- [A] model_dump()
- [B] dict()
- [C] model_to_dict()
- [D] to_dict()

**参考答案**：0

**解析**：Pydantic v2 推荐使用 model_dump() 导出字典，v1 的 .dict() 虽仍可用但已弃用。dict() 是内置函数，不能直接调用；model_to_dict() 和 to_dict() 都不是 Pydantic 的 API。

### single_choice · None



- [A] model_dump(exclude_none=True)
- [B] model_dump(skip_none=True)
- [C] model_dump(exclude_unset=True)
- [D] model_dump(remove_none=True)

**参考答案**：0

**解析**：model_dump(exclude_none=True) 会排除值为 None 的字段。exclude_unset=True 排除未设置的字段；skip_none 和 remove_none 不是有效参数。

### single_choice · None



- [A] Field 只能用于设置默认值，不能设置校验约束
- [B] Field 可以设置默认值、别名、描述、数值范围等约束
- [C] Field 是装饰器，必须写在方法上方
- [D] Field 只能用于 Optional 字段

**参考答案**：1

**解析**：Pydantic v2 的 Field 是一个函数，用于为字段提供默认值、别名、描述、约束（如 gt、le、min_length）等元数据。它不是装饰器，也不限于 Optional 字段。

### single_choice · None



- [A] 严格模式（strict mode）
- [B] 类型强制转换（type coercion）
- [C] 惰性验证（lazy validation）
- [D] 序列化（serialization）

**参考答案**：1

**解析**：Pydantic 默认会进行类型强制转换，将兼容的输入转换为目标类型；严格模式会禁止这种转换。惰性验证和序列化与此场景无关。

### single_choice · None



- [A] dict[str, int]
- [B] Dict[str, int] 必须从 typing 导入
- [C] map(str, int)
- [D] dictionary(str, int)

**参考答案**：0

**解析**：Pydantic v2 支持 Python 3.9+ 的内置泛型写法 dict[str, int]，也支持 typing.Dict[str, int]。map 和 dictionary 不是类型注解。

### single_choice · None



- [A] BaseModel 子类实例化时会自动运行校验，校验失败抛出 ValidationError
- [B] BaseModel 子类只在调用 validate() 时才校验
- [C] BaseModel 子类不会自动类型转换，需要手动转换
- [D] BaseModel 子类必须实现 __init__ 方法

**参考答案**：0

**解析**：Pydantic v2 的 BaseModel 在实例化时自动进行校验和类型转换，失败时抛出 ValidationError。不需要手动调用 validate()，也不需要自定义 __init__。

### single_choice · None



- [A] str
- [B] Literal['a', 'b', 'c']
- [C] Enum('a', 'b', 'c')
- [D] Union[str, str, str]

**参考答案**：1

**解析**：typing.Literal 可以限定字段只能取指定字面量之一。Enum('a','b','c') 写法不正确；Union[str, str, str] 等价于 str，不能限制取值；str 不做限制。

### single_choice · None



- [A] model_dump_json()
- [B] model_json()
- [C] to_json()
- [D] json()

**参考答案**：0

**解析**：Pydantic v2 使用 model_dump_json() 导出 JSON 字符串，v1 的 .json() 已弃用。model_json()、to_json() 不是 Pydantic API。

### single_choice · None



- [A] 校验失败，因为 '2' 不是 int
- [B] 字符串 '2' 被转换为整数 2，校验通过
- [C] 整个列表被拒绝，因为包含字符串
- [D] 列表被转换为字符串

**参考答案**：1

**解析**：Pydantic 默认开启类型强制转换，'2' 会被转换为 int 2，因此校验通过。只有在严格模式下才会拒绝字符串。

### single_choice · None



- [A] ValidationError 是一个普通的 Exception，不包含字段信息
- [B] ValidationError 包含每个字段的错误详情，可通过 errors() 方法获取
- [C] ValidationError 只能通过 try/except 捕获，不能获取详细信息
- [D] ValidationError 在严格模式下才会抛出

**参考答案**：1

**解析**：Pydantic v2 的 ValidationError 继承自 ValueError，包含详细的字段错误信息，可用 errors() 获取结构化列表。无论是否严格模式，校验失败都会抛出。

### single_choice · None



- [A] 使用 @field_serializer 装饰器为字段定义序列化函数
- [B] 使用 @validator 装饰器修改字段值
- [C] 在 model_dump 中传入 json_encoder 参数
- [D] 重写 __str__ 方法

**参考答案**：0

**解析**：Pydantic v2 提供 @field_serializer 装饰器用于自定义字段的序列化行为。@validator 是 v1 的校验装饰器，不负责序列化；model_dump 没有 json_encoder 参数；__str__ 与 JSON 序列化无关。

### single_choice · None



- [A] model_config 是一个类属性，用于集中设置模型行为，如 extra='forbid'
- [B] model_config 是一个实例方法，必须在 __init__ 中调用
- [C] model_config 只能通过 Config 内部类设置，不能作为类属性
- [D] model_config 仅用于设置字段别名，不能控制额外字段

**参考答案**：0

**解析**：Pydantic v2 使用 model_config = ConfigDict(...) 作为类属性来配置模型，例如 extra='forbid' 禁止额外字段。B 项错误，它不是方法；C 项错误，v2 推荐用 model_config 而非 Config 内部类；D 项错误，extra 等也在 model_config 中设置。

### single_choice · None



- [A] @validator
- [B] @field_validator
- [C] @root_validator
- [D] @model_validator

**参考答案**：1

**解析**：Pydantic v2 使用 @field_validator 定义字段级校验器，替代 v1 的 @validator。@root_validator 和 @model_validator 用于模型级校验，其中 @model_validator 是 v2 的模型级校验装饰器。

### single_choice · None



- [A] mode='before'
- [B] mode='after'
- [C] pre=True
- [D] before=True

**参考答案**：0

**解析**：@field_validator 通过 mode 参数控制运行时机，mode='before' 表示在类型转换之前运行，mode='after' 表示之后。pre=True 是 v1 的参数，before=True 不是有效参数。

### single_choice · None



- [A] 使用 @field_validator 分别校验两个字段
- [B] 使用 @model_validator(mode='after') 访问 self 进行跨字段校验
- [C] 使用 @root_validator(pre=True) 进行校验
- [D] 在 __init__ 中手动抛出 ValueError

**参考答案**：1

**解析**：Pydantic v2 推荐使用 @model_validator(mode='after') 进行模型级校验，此时可以访问 self 的多个字段。@field_validator 只能拿到单个字段值；@root_validator 是 v1 API；在 __init__ 中手动校验不是 Pydantic 的推荐方式。

### single_choice · None



- [A] Model.parse_raw()
- [B] Model.model_validate_json()
- [C] Model.parse_json()
- [D] Model.from_json()

**参考答案**：1

**解析**：Pydantic v2 使用 model_validate_json() 解析 JSON 字符串，v1 的 parse_raw() 已弃用。parse_json() 和 from_json() 都不是 Pydantic 的 API。

### single_choice · None



- [A] name: Optional[str]
- [B] name: Optional[str] = None
- [C] name: str = None
- [D] name: str | None

**参考答案**：1

**解析**：在 Pydantic v2 中，声明可选且默认 None 应写成 Optional[str] = None 或 str | None = None。只写 Optional[str] 没有默认值，字段仍是必填；name: str = None 类型不匹配；name: str | None 同样没有默认值。

### single_choice · None



- [A] extra = 'ignore'
- [B] extra = 'allow'
- [C] extra = 'forbid'
- [D] extra = 'deny'

**参考答案**：2

**解析**：extra='forbid' 表示遇到未声明字段时抛出验证错误；extra='ignore' 会忽略；extra='allow' 会保留。'deny' 不是有效取值。

### single_choice · None



- [A] Model.parse_obj(data)
- [B] Model.model_validate(data)
- [C] Model.validate(data)
- [D] Model.from_dict(data)

**参考答案**：1

**解析**：Pydantic v2 使用 model_validate() 验证字典或其他对象并返回模型实例，v1 的 parse_obj() 已弃用。validate() 和 from_dict() 都不是 Pydantic 的 API。

### single_choice · None



- [A] OpenAPI 规范只能用于生成人类可读的 Markdown 文档，无法用于生成代码
- [B] OpenAPI 规范是一份与语言无关的接口描述契约，可用于生成文档、客户端 SDK、服务端桩代码等
- [C] OpenAPI 规范是 Python 独有的接口定义格式，只能被 Python 项目使用
- [D] OpenAPI 规范规定的是数据库表结构，而不是 HTTP 接口

**参考答案**：1

**解析**：OpenAPI 是一份语言无关、与实现无关的 REST 接口描述契约（通常用 YAML/JSON 编写），生态工具可据此生成文档、客户端 SDK、服务端桩代码、校验逻辑等。它不是 Python 专属，也不描述数据库表结构，更不局限于文档生成。

### single_choice · None



- [A] components
- [B] paths
- [C] servers
- [D] info

**参考答案**：1

**解析**：paths 是 OpenAPI 文档中描述各接口路径及其下 HTTP 操作（get/post/...）的顶层字段。components 用于存放可复用的 schema、参数、响应等；servers 描述服务的基础 URL 列表；info 提供标题、版本等元信息。

### single_choice · None



- [A] 数据必须同时满足其中所有子 schema
- [B] 数据必须恰好满足其中一个子 schema
- [C] 数据只需满足其中任意一个子 schema 即可，且不限制满足几个
- [D] 数据不属于其中任何一个子 schema

**参考答案**：1

**解析**：oneOf 表示数据必须恰好符合其中一个子 schema。allOf 表示同时满足全部；anyOf 表示满足任意一个（一个或多个均可）；not 表示不满足。

### multi_choice · None



- [A] 作为前后端、外部调用方之间的接口契约，减少沟通歧义
- [B] 据此自动生成客户端 SDK 或服务端桩代码
- [C] 作为接口的机器可读描述，用于自动化测试或请求校验
- [D] 替代数据库迁移工具，直接根据 schema 修改数据库表结构
- [E] 自动保证后端业务逻辑的正确性

**参考答案**：[0, 1, 2]

**解析**：OpenAPI 的价值在于作为接口契约、生成代码/文档、支撑自动化测试和校验。它描述的是 HTTP 接口，不能代替数据库迁移工具，也不能保证业务逻辑正确——规范描述的是接口形状，不是实现正确性。

### multi_choice · None



- [A] 它用于存放可复用的对象，如 schemas、parameters、responses、securitySchemes
- [B] 其中定义的内容通常通过 $ref 被 paths 等位置引用
- [C] components 中定义但未被引用的条目仍会出现在接口路径列表中
- [D] 它可以替代 paths，直接定义接口路径
- [E] components 只能存放 schema，不能存放安全方案

**参考答案**：[0, 1]

**解析**：components 是复用容器，存放 schemas、parameters、responses、securitySchemes 等，并通过 $ref 引用。未被引用的组件只是定义存在，并不会凭空产生接口路径；paths 才是定义接口路径的地方；components 也可存放 securitySchemes，并非只能放 schema。

### multi_choice · None



- [A] in: query 表示该参数出现在 URL 查询字符串中
- [B] required: false 表示调用方可以不提供该参数
- [C] schema 下的 type 用于约束该参数的数据类型
- [D] in: query 的参数必须出现在路径模板中才能生效
- [E] name 字段可以随意填写，与实际参数名无关

**参考答案**：[0, 1, 2]

**解析**：查询参数用 in: query 表示，required 控制是否必填，schema 约束类型。查询参数不需要出现在路径模板中（那是路径参数的要求），name 必须与实际使用的参数名一致。

### multi_choice · None



- [A] required 用于声明对象中哪些属性是必须存在的
- [B] enum 用于限定取值必须在给定集合内
- [C] minimum / maximum 用于限定数值的上下界
- [D] additionalProperties 用于限定数组元素的最大个数
- [E] items 用于描述数组元素的类型

**参考答案**：[0, 1, 2, 4]

**解析**：required 声明对象必填属性，enum 限定取值集合，minimum/maximum 限定数值范围，items 描述数组元素类型。additionalProperties 控制的是对象是否允许出现未声明的额外属性，而非数组元素个数（那是 maxItems 的作用）。

### fill_blank · None



**参考答案**：["components"]

**解析**：OpenAPI 3.x 中可复用组件位于 components 下，引用内部 schema 的写法是 '#/components/schemas/User'。空处应填 components。

### fill_blank · None



**参考答案**：["query"]

**解析**：参数的 in 字段可取 path、query、header、cookie 等。位于查询字符串中的参数取值为 query。

### code_reading · None



**参考答案**：该接口要求请求体必填（required: true），媒体类型为 application/json；请求体结构须符合 components/schemas/Item，即一个对象，name 为必填字符串，price 为可选数值。成功时返回 201。

**解析**：requestBody.required 为 true 表示必须有请求体；content 下的键指定媒体类型为 application/json；schema 通过 $ref 指向 Item。Item 声明 required: [name]，所以 name 必填，price 未列入 required 故可选。响应 '201' 表示创建成功。

### code_reading · None



**参考答案**：一份合法的 Pet 数据必须恰好符合 Cat 与 Dog 两个 schema 中的一个（不能两个都符合，也不能都不符合）。

**解析**：oneOf 表示数据必须恰好满足其中一个子 schema。若两个都不满足则不合法；若同时满足两者（例如两者约束过于宽泛导致重叠）也视为不合法。

### scenario · None



**解析**：核心在于把 OpenAPI 文档作为代码生成的产物而非手写产物：通过支持根据路由与类型注解自动生成规范的框架/扩展，使文档与实现同步。其价值是形成接口契约，前端据此生成/对齐请求代码，测试据此自动校验请求与响应，减少字段名、类型、必填性上的返工。

### single_choice · None



- [A] responses
- [B] parameters
- [C] requestBody
- [D] security

**参考答案**：2

**解析**：对于带有请求体的操作（如 POST/PUT/PATCH），OpenAPI 用 requestBody 字段描述其内容及媒体类型。parameters 描述路径/查询/头部等参数，responses 描述响应，security 描述安全要求。

### single_choice · None



- [A] in: path 的参数必须在 URL 路径模板中以 {id} 形式出现，且 required 必须为 true
- [B] in: path 的参数可以不出现在路径模板中，只要名字一样即可
- [C] in: path 的参数 required 可以省略或为 false，因为路径参数总是可选的
- [D] in: path 的参数类型只能是字符串，不能声明为 integer

**参考答案**：0

**解析**：路径参数（in: path）必须与路径模板中的占位符（如 {id}）一一对应，并且 OpenAPI 规定路径参数 required 必须为 true。参数可以有 schema 类型（如 integer），并非只能是字符串。

### single_choice · None



- [A] definitions
- [B] schemas
- [C] models
- [D] types

**参考答案**：1

**解析**：在 OpenAPI 3.x 中，可复用的数据模型定义在 components/schemas 下，通过 $ref 引用。definitions 是已废弃的 Swagger 2.0 写法；models 和 types 不是 OpenAPI 的标准顶层字段。

### single_choice · None



- [A] 手写一份与代码无关的静态 YAML，修改接口时人工同步
- [B] 使用能根据路由与视图函数/类型注解自动生成 OpenAPI 文档的框架或扩展，从代码生成规范
- [C] 在接口里硬编码一段 JSON 字符串返回给调用方当文档
- [D] 不用文档，直接让调用方阅读源码

**参考答案**：1

**解析**：要让文档与代码保持同步、避免人工维护两份内容，常见做法是使用支持根据路由与类型注解自动生成 OpenAPI 规范的框架/扩展。手写静态 YAML 容易与实现脱节，硬编码 JSON 或看源码都不是可持续方案。

### single_choice · None



- [A] $ref 用于在文档中引用其他位置定义的组件，避免重复定义
- [B] $ref 用于引用 Python 模块，从而在文档中直接调用后端逻辑
- [C] $ref 只能引用外部 URL，不能引用同一文档内的片段
- [D] $ref 等价于代码中的 import，可用于加载第三方库

**参考答案**：0

**解析**：$ref 是 OpenAPI 中的引用机制，用于指向同一文档或外部文档中的组件（如 #/components/schemas/User），从而复用定义、减少重复。它是文档内的结构引用，不是 Python 的 import，也不是直接调用后端逻辑。

### single_choice · None



- [A] responses 下的 '200' 条目中，用 content 指定媒体类型并给出 schema
- [B] requestBody 下的 '200' 条目中
- [C] parameters 下名为 200 的参数中
- [D] security 下的 '200' 条目中

**参考答案**：0

**解析**：响应定义放在 responses 下，键为状态码（如 '200'），其中通过 content 指定媒体类型（如 application/json）并给出对应 schema。requestBody 描述请求体，parameters 描述参数，security 描述安全方案。

### single_choice · None



- [A] 一个必须是合法日期时间字符串的值
- [B] 一个 Python 的 datetime 对象实例
- [C] 一个表示时区偏移量的整数
- [D] 一个存放日期的数据库列

**参考答案**：0

**解析**：type: string 表示值为字符串，format: date-time 是 OpenAPI/JSON Schema 约定的一种字符串格式约束，通常对应 RFC 3339 的日期时间表示。它描述的是字符串的格式，不是语言里的对象实例，也不是整数或数据库列。

### single_choice · None



- [A] 声明该 API 可用的基础 URL 列表，用于拼接实际请求地址
- [B] 声明后端运行的服务器进程数量
- [C] 声明用于部署 API 的物理机 IP
- [D] 声明该 API 支持的 HTTP 状态码集合

**参考答案**：0

**解析**：servers 用于声明 API 的基础 URL（可含变量），工具会用它拼接出完整的请求地址。它与部署机器数量、物理机 IP 或状态码集合无关。
