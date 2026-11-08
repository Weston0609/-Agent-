# s2u4l5 类型提示与 Pydantic 入门

> 来源 `content/lessons/s2u4l5.json`

## py.typehint.pydantic_basic

# 类型提示与 Pydantic 入门

## 一句话直觉

**Python 的类型提示（type hints）就像给变量、函数贴"标签"，让 IDE 和自动化工具能在你运行代码之前，就发现"把字符串传给需要数字的函数"这类错误；而 Pydantic 则把这种标签变成"运行时自动校验器"，专门帮你守护从外部（用户输入、API、配置文件）进来的数据。**

在生产级代码里，光靠 "人手检查" 或者 `if not isinstance(x, int)` 是远远不够的——注释会过时，文档会撒谎，但类型提示和 Pydantic 不会被跳过。

---

## 第 1 节：为什么需要类型提示？

Python 是一门动态类型语言，`def add(a, b): return a + b` 对 `1 + 2` 和 `"a" + "b"` 都成立，但对 `1 + "a"` 就会在运行时崩溃。问题在于：**错误发生得太晚**，可能是在凌晨三点的生产环境上。

类型提示（type hints，PEP 484 引入）让我们在声明的层面写出意图：

```python
# 声明：a 和 b 是 int，返回也是 int
def add(a: int, b: int) -> int:
    return a + b
```

运行时 Python 解释器**不执行**这些提示（所以不会有性能损失，也不会因提示错误而拒绝运行），但 mypy、pyright、IDE 会读它们。这就是 PEP 484 说的"类型检查器是可选的、独立的工具"。

```python
# 一个简单的类型提示示例
# 运行此代码不会报错，但 mypy 会警告 `add("a", "b")`
def add(a: int, b: int) -> int:
    return a + b

print(add(1, 2))       # 正常运行：3
print(add("a", "b"))  # 运行时也 OK："ab"（因为 + 对字符串也可用）
```

---

## 第 2 节：类型提示的基本语法

### 变量注解（variable annotations, PEP 526）

```python
# 模块级/局部变量注解
name: str = "Alice"     # 冒号后一个空格，等号两侧各一个空格
age: int = 30

# 只注解不赋值也合法
email: str
```

### 函数注解（function annotations）

```python
# 参数名: 类型；-> 返回类型
def greet(name: str, times: int = 1) -> str:
    return ("Hi " + name + "! ") * times
```

### 常用容器类型

从 Python 3.9 起可以直接用内置泛型 `list`、`dict`、`tuple`；更复杂的用 `typing` 模块。

```python
# Python 3.9+
from typing import Optional

def scores(names: list[str]) -> dict[str, int]:
    return {n: 0 for n in names}

# Optional[X] 等价于 X | None，表示"要么是 X，要么是 None"
def maybe_id(prefix: str) -> Optional[int]:
    return int(prefix) if prefix.isdigit() else None
```

### 类型别名（type alias）让复杂签名清晰可读

```python
# Python 3.12 用 type 语句，老版本用赋值
# type Vector = list[float]
Vector = list[float]  # 老写法仍然完全可用

def scale(scalar: float, vector: Vector) -> Vector:
    return [scalar * x for x in vector]
```

---

## 第 3 节：运行时真的检查吗？—— Pydantic 登场

类型提示本身**只是元数据**。如果你从一个 HTTP 请求里拿到了用户数据 `{"age": "abc"}`，Python 不会主动报错。这就是 Pydantic 存在的意义：**把类型提示变成运行时的自动校验 + 数据转换**。

Pydantic 的核心是 `BaseModel` 的子类：

```python
# 安装：pip install pydantic
# Pydantic v2 写法
from pydantic import BaseModel, ValidationError

class User(BaseModel):
    name: str
    age: int
    email: str

# 正常构造：合法数据会被直接接受
u = User(name="Alice", age=30, email="a@b.com")
print(u)

# 不合法数据：字符串 "30" 会被自动转成 int（默认宽松模式）
u2 = User(name="Bob", age="30", email="b@c.com")
print(u2.age, type(u2.age))  # 30 <class 'int'>

# 无法转换的数据：抛 ValidationError
try:
    User(name="C", age="not-a-number", email="c@d.com")
except ValidationError as e:
    print("校验失败:", e.errors()[0]["msg"])
```

### 关键优势

1. **早失败**：数据进入你的业务逻辑之前就被校验。
2. **自动类型转换**：JSON 里的字符串 `"30"` 变成 `int` 30。
3. **IDE 友好**：`u.age` 会被识别为 `int`，有自动补全。
4. **可序列化**：`u.model_dump()` 返回 dict，`u.model_dump_json()` 返回 JSON 字符串。

```python
# 序列化示例（Pydantic v2）
from pydantic import BaseModel

class User(BaseModel):
    name: str
    age: int

u = User(name="Alice", age=30)
print(u.model_dump())          # {'name': 'Alice', 'age': 30}
print(u.model_dump_json())     # '{"name":"Alice","age":30}'
```

---

## 第 4 节：更贴近工程的用法——嵌套、默认值、约束

真实场景里模型往往嵌套，且有默认值或校验约束。

```python
from pydantic import BaseModel, Field
from typing import Optional

class Address(BaseModel):
    city: str
    zipcode: str

class User(BaseModel):
    name: str
    age: int = Field(ge=0, le=150)         # 数值范围约束
    email: Optional[str] = None            # 可选字段，默认 None
    tags: list[str] = []                   # 可变默认值，Pydantic 会正确处理
    address: Optional[Address] = None      # 嵌套模型

# 嵌套和默认值一起用
u = User(
    name="Alice",
    age=30,
    address={"city": "Beijing", "zipcode": "100000"},  # dict 会自动转成 Address
)
print(u.address.city)  # Beijing

# 校验约束：年龄超范围直接报错
try:
    User(name="B", age=200)
except Exception as e:
    print("年龄超范围:", str(e).splitlines()[-1])
```

### 用模型替代原始 dict 的价值

在没有 Pydantic 的代码里，你经常写 `data["user"]["age"]`，一旦字段名拼错、层级变深就会崩。用了模型后：

- 字段名拼错 → IDE 立刻提示（不再等到运行时）。
- 数据类型不对 → 构造时立刻报错，知道是哪一行数据。
- 文档自动化：FastAPI 等框架直接读取 Pydantic 模型生成 OpenAPI 文档。

---

## 第 5 节：把类型提示和 Pydantic 落到工程实践

**原则 1：公共函数/边界处一定加类型提示。** 特别是团队共享的模块、对外 API 的入口/出口。

```python
# 边界：外部来的数据先用 Pydantic 校验，内部逻辑再用纯函数
from pydantic import BaseModel

def parse_user(payload: dict) -> "User":
    return User(**payload)

def user_display(user: User) -> str:
    return f"{user.name} ({user.age})"
```

**原则 2：类型检查器可选但强烈建议装。** 在 IDE 中打开 mypy/pyright，或在 CI 里跑一次：

```bash
pip install mypy
mypy your_module.py
```

**原则 3：使用类型别名（type aliases）和 `NewType` 防止把不同语义的同类值混用。**

```python
from typing import NewType

UserId = NewType("UserId", int)
OrderId = NewType("OrderId", int)

def get_user_name(uid: UserId) -> str:
    return f"user-{uid}"

# 显式构造才能通过类型检查
print(get_user_name(UserId(42)))
```

**原则 4：运行时和静态检查分工。** 静态检查器负责代码结构；Pydantic 负责数据边界（用户输入、配置文件、API 响应）。两者互补，不是二选一。

---

## 动手练习

**任务：写一个"用户注册数据"的 Pydantic 模型并通过一组数据验证它。**

步骤：

1. 在本地新建文件 `pydantic_practice.py`。
2. 安装依赖：`pip install pydantic`。
3. 定义 `User` 模型，字段包含：
   - `username: str`（长度 3~20，用 `Field(min_length=3, max_length=20)`）
   - `age: int`（0~150）
   - `email: str`
   - `tags: list[str] = []`
   - `nickname: Optional[str] = None`
4. 准备一份 `data` 列表，包含：
   - 一条合法的 dict；
   - 一条 `age` 是字符串 `"20"` 的（应被 Pydantic 自动转成 int）；
   - 一条 `age` 是 `-5` 的（应触发校验错误）；
   - 一条 `username` 只有 2 个字符的（应触发校验错误）。
5. 遍历数据，用 `try/except ValidationError` 打印成功结果或错误信息。
6. 额外：对第一条成功的用户调用 `model_dump_json()`，打印 JSON 字符串。
7. 进阶：给 `User` 添加 `model_config = {"extra": "forbid"}`，再传入带多余字段 `"role": "admin"` 的数据，观察 Pydantic 的行为。

预期结果：你会看到合法的通过、可转换的被修复、非法的抛出清晰的错误信息——这就是 Pydantic 在生产里最常用的工作模式。


---

## 本课题目

### single_choice · None



- [A] A. `age="25"` 会抛出错误，因为字符串不能自动转成整数
- [B] B. `age=25` 会抛出错误，因为模型字段必须用字符串传入
- [C] C. `age="abc"` 会抛出错误，因为该字符串无法解析为整数
- [D] D. `age=25.0` 会抛出错误，因为浮点数不能赋给整型字段

**参考答案**：2

**解析**：在带类型校验的模型里，通常会对可解析的数值字符串做强制转换，但 `"abc"` 无法解析成整数，因此会在实例化时抛出校验错误。`age="25"` 通常可被转成 25；`age=25` 是标准用法；`age=25.0` 一般也能被接受并可能被转成 25（具体取决于严格模式设置，但在默认非严格模式下通常不会直接报错）。

### single_choice · None



- [A] A. 只有序列化时才校验
- [B] B. 实例化时通常执行校验，不符合则抛异常
- [C] C. 运行时完全不产生校验行为
- [D] D. 只在定义时校验字段名，不校验字段值

**参考答案**：1

**解析**：这类模型的核心能力之一就是在实例化时对输入数据做运行时校验，不符合类型或约束会抛出校验异常。选项 A、C、D 都是常见误解：把静态类型注解或序列化阶段误当成唯一校验时机。

### single_choice · None



- [A] A. 合法列表，元素均为整数
- [B] B. 元素无法解析为整数，会触发校验错误
- [C] C. 空列表合法
- [D] D. 元组通常可被转换为列表

**参考答案**：1

**解析**：`List[int]` 要求每个元素都能解析为整数。`["a", "b"]` 中的元素无法解析为整数，因此会触发校验错误。A、C 均合法；D 中元组通常会被转换为列表并通过校验（具体取决于严格模式设置，但默认行为通常如此）。

### single_choice · None



- [A] A. 子类可以覆盖父类字段，并非只能新增
- [B] B. 子类可继承父类字段，并可重新声明覆盖
- [C] C. 继承后父类字段不会被全部清除
- [D] D. 字段顺序通常与类定义顺序有关

**参考答案**：1

**解析**：模型类支持继承，子类会继承父类字段，并且可以在子类中重新声明同名字段以覆盖类型或默认值。A、C、D 与常见的继承行为不符。

### single_choice · None



- [A] A. 有默认值 0，通常非必填
- [B] B. 没有默认值，通常视为必填
- [C] C. 默认值为 None，通常非必填
- [D] D. 可选且默认 None，通常非必填

**参考答案**：1

**解析**：没有默认值的字段通常被视为必填，实例化时必须提供。A、C、D 都给出了默认值，因此通常不是必填。

### single_choice · None



- [A] A. 不只抛 ValueError，且通常包含字段级错误信息
- [B] B. 通常抛出专门校验异常，包含字段错误详情
- [C] C. 通常抛异常而非仅返回 False
- [D] D. 不会自动忽略并继续实例化

**参考答案**：1

**解析**：这类模型在校验失败时通常会抛出专门的校验异常，异常对象可提供按字段组织的错误列表，便于定位问题。A、C、D 都低估了错误信息的结构化程度或误解了失败时的处理方式。

### single_choice · None



- [A] A. 常见日期字符串通常可被解析为 datetime
- [B] B. 整数通常不被直接解析为日期
- [C] C. 列表通常不被直接解析为日期
- [D] D. 字典通常不被直接解析为日期

**参考答案**：0

**解析**：在默认非严格模式下，`datetime` 字段通常可以接受符合常见格式的字符串并自动解析。整数、列表、字典一般不会被直接解析为日期对象，因此更可能报错。

### single_choice · None



- [A] A. 类型相同不一定相等，还需字段值相同
- [B] B. 通常所有字段值相等时视为相等
- [C] C. 通常支持相等比较，不限于 is
- [D] D. 不会自动忽略默认值字段

**参考答案**：1

**解析**：模型实例通常基于字段值进行相等比较，且要求类型一致。A 忽略了字段值的比较；C 与常见行为不符；D 没有依据。

### single_choice · None



- [A] A. 实例化后直接赋值是否触发校验取决于配置，并非总是自动拒绝
- [B] B. 使用校验器可在赋值或实例化时进行校验和转换
- [C] C. 覆盖 __init__ 不是推荐做法且可能破坏模型机制
- [D] D. setattr 不一定绕过校验，且并非稳定可靠的方案

**参考答案**：1

**解析**：这类模型通常提供校验器机制，可在字段赋值或实例化时执行自定义校验和转换逻辑，是扩展校验的推荐方式。A、D 的行为依赖配置且不稳定；C 容易破坏模型内部机制。

### single_choice · None



- [A] A. 别名通常也可用于反序列化输入
- [B] B. 别名可用于输入映射，并可配置是否用于输出
- [C] C. 设置别名后字段原名通常仍可访问
- [D] D. 别名可以是任意字符串，不要求是合法标识符

**参考答案**：1

**解析**：字段别名常用于处理输入键与字段名不一致的情况，同时可通过模型配置决定导出时是否使用别名。别名也能用于反序列化输入；原字段名通常仍可访问；别名可以是任意字符串。

### single_choice · None



- [A] A. 通常用于解析字典，不是只能解析字符串
- [B] B. 通常用于把字典解析成模型实例并执行校验
- [C] C. 通常会执行校验，不会跳过字段检查
- [D] D. 顶层和嵌套模型通常都可使用

**参考答案**：1

**解析**：从字典解析的方法通常用于将原始字典数据转换为模型实例，并执行与直接构造类似的字段校验。A、C、D 都与常见语义不符。

### single_choice · None



- [A] A. 通常不需要手动拼接
- [B] B. 使用模型提供的 JSON 导出方法，通常自动处理嵌套与类型转换
- [C] C. str(obj) 通常不是合法 JSON
- [D] D. 使用 eval 不是正确或安全的做法

**参考答案**：1

**解析**：这类模型通常提供导出 JSON 字符串的方法，会自动处理嵌套模型、日期等类型的转换。手动拼接、`str(obj)` 或 `eval` 都不是可靠的做法。

### single_choice · None



- [A] A. `name: str` 表示可选字段且有默认值
- [B] B. `name: Optional[str] = None` 表示字段可为空且默认值为 None
- [C] C. `name: str = ...` 表示默认值是省略号字符串
- [D] D. `name: str()` 是声明字段的合法语法

**参考答案**：1

**解析**：`Optional[str]` 表示类型可为字符串或 None，配合 `= None` 给出默认值，是声明可选字段的常见写法。选项 A 不带默认值，通常是必填；C 中的 `...` 一般表示必填且无默认值；D 不是合法的字段声明语法。

### single_choice · None



- [A] A. 有默认值 0，不会因缺字段报错
- [B] B. 没有默认值，未传 `x` 会因缺少必填字段报错
- [C] C. 显式传了 `x=2`，不会因缺字段报错
- [D] D. 有默认值 "a"，不会因缺字段报错

**参考答案**：1

**解析**：在类型校验模型中，没有默认值的字段通常视为必填，实例化时未提供会抛出校验错误。A、C、D 都有默认值或显式传参，不会因为缺少该字段而报错。

### single_choice · None



- [A] A. 只能接收模型实例，不能接收字典
- [B] B. 通常可接收字典，并自动转换为嵌套模型
- [C] C. 父模型实例化时不校验嵌套字段
- [D] D. 必须声明为 Any 才能使用

**参考答案**：1

**解析**：在嵌套模型字段中，传入字典时通常会自动解析并转换为对应的嵌套模型实例，同时执行嵌套校验。选项 A、C、D 都是常见误解：忽略了自动转换能力、误解了校验递归性，或误以为必须使用 `Any`。

### single_choice · None



- [A] A. 默认忽略额外字段，不保留
- [B] B. 自动加入模型并可直接访问
- [C] C. 导致类定义失败
- [D] D. 自动转字符串保存

**参考答案**：0

**解析**：在默认配置下，未声明的额外字段通常会被忽略，不会成为模型属性。若需要保留额外字段，需要显式配置 extra 行为。选项 B、C、D 都是对默认行为或配置方式的误解。

### single_choice · None



- [A] A. 只是默认值 0，没有大于 0 的约束
- [B] B. 使用 `Field(gt=0)` 设置大于 0 的校验约束
- [C] C. `GreaterThan` 不是标准字段约束声明方式
- [D] D. 不是合法的类型注解语法

**参考答案**：1

**解析**：在常见的数据校验模型中，使用 `Field` 并传入 `gt` 等参数可声明数值范围约束。选项 A 只是默认值；C 并非标准写法；D 不是合法的注解语法。

### single_choice · None



- [A] A. 注释提醒不是运行时校验，无法阻止非法值
- [B] B. 使用枚举类型作为字段类型，可实现取值约束与校验
- [C] C. int 类型不限制字符串取值，文档说明也不校验
- [D] D. Any 类型本身不做任何约束，手动检查容易被遗漏

**参考答案**：1

**解析**：将字段类型声明为枚举类，可以让模型在实例化时自动校验输入值是否属于允许的枚举成员，是最直接且可维护的做法。其余选项都依赖人工约定，无法在数据入口处提供可靠的自动校验。

### single_choice · None



- [A] A. 只能在模块顶层设置，不能按类设置
- [B] B. 通常可通过内部类或类属性按模型单独设置
- [C] C. 设置后所有模型共享且无法覆盖
- [D] D. 只能通过环境变量设置

**参考答案**：1

**解析**：这类模型通常支持按模型类单独配置行为（例如额外字段处理、严格模式等），常见方式是通过内部配置类或类属性。A、C、D 都不符合常见的配置机制。

### single_choice · None



- [A] A. 通常可导出声明字段，嵌套模型会递归转成字典
- [B] B. 导出一般不再触发输入校验
- [C] C. 导出通常不会修改原对象
- [D] D. 导出通常返回字典而非只能返回字符串

**参考答案**：0

**解析**：模型实例通常提供导出为字典的方法，会把声明字段按结构化方式输出，嵌套模型会递归转换。导出过程一般不再做输入校验，也不会修改原对象，因此 B、C、D 不正确。
