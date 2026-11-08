# s2u4l4 Python 类型注解（type hint）默认只是“文 / Python 类型注解（Type Hints）与 Pyright 静态检查

> 来源 `content/lessons/s2u4l4.json`

## py.typehint.mypy

## 一句话直觉

Python 类型注解（type hint）默认只是“文档”，运行时不会报错；而 **mypy** 是一个静态类型检查器（static type checker），它在程序运行之前读取这些注解并告诉你“这里类型对不上”。学习 mypy，就是把类型注解从注释升级为**可自动验证的契约**。

---

## 1. 为什么需要 mypy：类型注解本身不检查

Python 官方文档明确写道：

> The Python runtime does not enforce function and variable type annotations. They can be used by third party tools such as type checkers, IDEs, linters, etc.

也就是说：

```python
def add(a: int, b: int) -> int:
    return a + b

print(add("hello", "world"))  # 运行时照样跑，结果是 'helloworld'
```

注解 `int` 没有阻止字符串传入。mypy 的作用就是**在运行前**发现这种错误。

---

## 2. 安装并运行 mypy

mypy 是一个独立工具，推荐安装在虚拟环境中。

```bash
pip install mypy
mypy your_script.py
```

一个典型输出：

```
error: Argument 1 to "add" has incompatible type "str"; expected "int"  [arg-type]
Found 1 error in 1 file (checked 1 source file)
```

关键点：

- 注解 = 契约；
- mypy = 契约检查器；
- Python 解释器 = 不管契约的执行者。

---

## 3. 基本类型注解语法

### 3.1 函数参数与返回值

```python
def surface_area_of_cube(edge_length: float) -> str:
    return f"The surface area of the cube is {6 * edge_length ** 2}."
```

- `edge_length: float`：参数期望是浮点数；
- `-> str`：函数期望返回字符串。

### 3.2 变量注解

```python
count: int = 0
name: str = "mypy"
ratio: float
```

PEP 526 规定：冒号后一个空格，等号两侧各一个空格。

### 3.3 容器类型

Python 3.9+ 可以直接用内置泛型：

```python
names: list[str] = ["a", "b"]
mapping: dict[str, int] = {"a": 1}
pair: tuple[str, int] = ("a", 1)
```

---

## 4. 进阶类型：别名、NewType、复合类型

### 4.1 类型别名（type alias）

Python 3.12+ 推荐用 `type` 语句：

```python
type Vector = list[float]

def scale(scalar: float, vector: Vector) -> Vector:
    return [scalar * num for num in vector]
```

旧版本可写成 `Vector = list[float]` 或 `Vector: TypeAlias = list[float]`。

### 4.2 NewType：语义上不同的类型

```python
from typing import NewType

UserId = NewType("UserId", int)

def get_user_name(user_id: UserId) -> str:
    return f"user-{user_id}"

get_user_name(UserId(42))     # OK
get_user_name(42)             # mypy 报错
```

### 4.3 复合签名简化

```python
from collections.abc import Sequence

type Address = tuple[str, int]
type ConnectionOptions = dict[str, str]
type Server = tuple[Address, ConnectionOptions]

def broadcast_message(message: str, servers: Sequence[Server]) -> None:
    ...
```

mypy 会把它当作展开后的 `Sequence[tuple[tuple[str, int], dict[str, str]]]` 检查。

---

## 5. 工程实践要点

- **stub 文件（.pyi）**：PEP 484 建议为无注解的第三方库提供 `.pyi`，mypy 会优先读取 stub 而不是 `.py`。
- **抑制检查**：在文件顶部加 `# type: ignore`，可让类型检查器忽略整个文件；也可在具体行使用。
- **IDE / CI 集成**：mypy 常配合 VS Code、PyCharm、pre-commit、GitHub Actions 使用。
- **渐进式**：可以先只注释公共 API，再逐步收紧；对老代码友好。
- **官方口径**：类型检查器是**可选、独立的工具**，Python 解释器不因注解改变行为。

---

## 6. 一个最小可运行示例

下面这段代码可以直接保存为 `demo.py`，然后用 `mypy demo.py` 检查。

```python
"""demo.py —— 用 mypy 检查的小例子。

运行：
    pip install mypy
    mypy demo.py
    python demo.py
"""
from typing import NewType


UserId = NewType("UserId", int)


def surface_area_of_cube(edge_length: float) -> str:
    # 类型注解仅是契约，运行时不强制
    return f"The surface area of the cube is {6 * edge_length ** 2}."


def get_user_name(user_id: UserId) -> str:
    return f"user-{user_id}"


def add(a: int, b: int) -> int:
    return a + b


if __name__ == "__main__":
    # 正确调用：mypy 通过
    print(surface_area_of_cube(2.0))
    print(get_user_name(UserId(42)))
    print(add(1, 2))

    # 下面这行 Python 能跑，但 mypy 会报 arg-type 错误：
    # print(add("hello", "world"))

    # 下面这行 Python 能跑，但 mypy 会报 NewType 不匹配：
    # print(get_user_name(42))
```

## py.typehint.pyright

# Python 类型注解（Type Hints）与 Pyright 静态检查

> **一句话直觉**：类型注解是写给"未来的自己、同事和 IDE"看的注释，Pyright 是一个不用运行代码就能帮你发现类型错误的检查器——它们让 Python 从"运行时才发现 bug"升级为"写代码时就发现 bug"。

---

## 1. 为什么需要类型注解？

Python 是动态类型（dynamic typing）语言：变量在运行时才知道类型。这很灵活，但项目一大就容易出现"这个函数到底该传什么"的困惑。

**类型注解（type hint）** 让你在源码里写明"我期望的类型"。注意：**Python 运行时并不强制检查注解**——官方文档明确说它们主要用于第三方工具（type checkers、IDE、linters）。

```python
# 没有注解，调用者不知道 edge_length 该传什么
def surface_area_of_cube(edge_length):
    return 6 * edge_length ** 2

# 有注解，签名即文档
def surface_area_of_cube(edge_length: float) -> float:
    return 6 * edge_length ** 2
```

注解的价值：
- **IDE 自动补全与悬浮提示** 变得精确；
- **静态类型检查器（static type checker）** 可以在你没有运行代码时发现错误；
- **重构更安全**：改了一个函数签名，工具会帮你找出所有不匹配的调用点。

---

## 2. 基础语法：函数、变量与返回值

`typing` 模块自 Python 3.5 加入标准库。基本规则：

- 参数：`name: Type`
- 返回值：`-> Type`
- 变量：`name: Type = value`
- 无返回：`-> None`

```python
from typing import Optional

def greet(name: str, times: int = 1) -> str:
    return ("Hello, " + name + "! ") * times

def find_user(user_id: int) -> Optional[str]:
    # Optional[str] 等价于 str | None
    return "Alice" if user_id == 1 else None
```

基础类型直接用内置名字：`int`、`float`、`str`、`bool`、`bytes`、`None`。容器用 `list[int]`、`dict[str, int]`、`tuple[str, int]`（Python 3.9+ 可直接用内置泛型）。

---

## 3. 进阶：别名、NewType 与联合类型

**类型别名（type alias）** 用来给复杂类型起名字。Python 3.12 引入 `type` 语句：

```python
# Python 3.12+
type Vector = list[float]
type Server = tuple[tuple[str, int], dict[str, str]]

# 旧版兼容写法
from typing import TypeAlias
Vector: TypeAlias = list[float]
```

**NewType** 创建"看起来像但类型检查器视为不同"的类型，用来区分逻辑上不同的值：

```python
from typing import NewType

UserId = NewType("UserId", int)

# 求两个 UserId 的和在语义上没意义，NewType 帮你暴露这种错误
def get_user_name(user_id: UserId) -> str:
    return f"user-{user_id}"

uid: UserId = UserId(42)      # 需要显式转换
name = get_user_name(uid)     # OK
# get_user_name(42)           # 类型检查器会报错
```

**联合类型（union）** 用 `X | Y`（3.10+）代替 `Union[X, Y]`：

```python
def parse(value: int | str) -> int:
    return int(value)
```

---

## 4. Pyright：不运行代码就能查错

**Pyright** 是微软开发的静态类型检查器，也是 VS Code 的 Pylance 引擎。它扫描源码、根据注解和推断推理类型，报告不一致。

**安装与运行**：

```bash
# 安装（npm 或 pip 均可）
pip install pyright

# 检查整个项目
pyright .

# 检查单个文件
pyright example.py
```

**Pyright 能帮我们发现什么？**

```python
def add(a: int, b: int) -> int:
    return a + b

add(1, 2)         # OK
add("1", 2)       # Pyright 报告：Argument of type "str" cannot be assigned to parameter "a" of type "int"
add(1)            # Pyright 报告：缺少参数 b
add(1, 2, 3)      # Pyright 报告：参数过多
total: str = add(1, 2)   # Pyright 报告：int 不能赋给 str
```

**配置**：在项目根目录建 `pyrightconfig.json`：

```json
{
  "include": ["src"],
  "exclude": ["**/node_modules", "**/__pycache__"],
  "typeCheckingMode": "strict"
}
```

`typeCheckingMode` 可选 `off`、`basic`、`standard`、`strict`。新项目建议直接 `strict`。

---

## 5. 工程实践：从注解到 CI 门禁

工程级项目的典型做法：

1. **所有对外函数、公共类显式注解**（对内代码可依赖推断）；
2. **关键数据模型用 `dataclass` 或 `pydantic` 配合注解**；
3. **把 Pyright 放进 CI**，PR 有类型错误就阻塞合并；
4. **渐进式迁移**：老代码先用 `basic`，新模块用 `strict`，逐步收紧。

```python
from dataclasses import dataclass

@dataclass
class Point:
    x: float
    y: float

    def translate(self, dx: float, dy: float) -> "Point":
        return Point(self.x + dx, self.y + dy)
```

Pyright 会检查 `Point("a", 1.0)` 这类构造错误、方法参数错误以及访问不存在属性的错误。

---

## 6. 小结与心智模型

| 概念 | 角色 |
|---|---|
| 类型注解 | 源码中声明期望类型 |
| `typing` 模块 | 提供复杂类型工具 |
| Pyright | 静态读取注解并报告不一致 |
| 运行时 | **不**校验注解，注解不影响执行 |

记住一句话：**注解是契约，Pyright 是契约的审计员**。

```python
# example.py —— 直接 `pyright example.py` 或 `python example.py` 均可运行
from typing import Optional, NewType
from dataclasses import dataclass

# 1) 基础函数注解
def surface_area_of_cube(edge_length: float) -> float:
    return 6 * edge_length ** 2

# 2) Optional 表示可能为 None
def find_user(user_id: int) -> Optional[str]:
    return "Alice" if user_id == 1 else None

# 3) 类型别名（简化复杂签名）
type Vector = list[float]

def scale(scalar: float, vector: Vector) -> Vector:
    return [scalar * num for num in vector]

# 4) NewType 区分逻辑上不同的值
UserId = NewType("UserId", int)

def get_user_name(user_id: UserId) -> str:
    return f"user-{user_id}"

# 5) dataclass 配合注解
type Address = tuple[str, int]
type ConnectionOptions = dict[str, str]
type Server = tuple[Address, ConnectionOptions]

@dataclass
class Point:
    x: float
    y: float

    def translate(self, dx: float, dy: float) -> "Point":
        return Point(self.x + dx, self.y + dy)


if __name__ == "__main__":
    print(surface_area_of_cube(2.0))            # 24.0
    print(find_user(1), find_user(2))           # Alice None
    print(scale(2.0, [1.0, -4.2, 5.4]))         # [2.0, -8.4, 10.8]
    print(get_user_name(UserId(42351)))         # user-42351
    print(Point(0.0, 0.0).translate(1.5, 2.5))  # Point(x=1.5, y=2.5)

    # 下面这些行 Pyright 会报错，但 Python 运行时不一定报错：
    # surface_area_of_cube("2")                 # 参数类型错误
    # get_user_name(42351)                      # 应传 UserId，不是裸 int
    # Point("a", 1.0)                            # 构造参数类型错误
```


---

## 本课题目

### single_choice · None



- [A] 类型注解在运行时会被强制检查，类型不匹配会抛出 TypeError
- [B] 类型注解本质上是元数据，运行时默认不做类型检查，需要借助 mypy 等工具静态检查
- [C] 只有 Python 3.5 以上版本才允许写类型注解，3.4 及以下会报 SyntaxError
- [D] 类型注解只能用在内置类型上，用户自定义类不能作为注解

**参考答案**：1

**解析**：Python 的类型注解不会在运行时强制检查，它们是可供静态检查工具（如 mypy）读取的元数据，运行时仅存储在 __annotations__ 中。

### single_choice · None



- [A] 运行时会抛出 TypeError，因为传入了字符串
- [B] 运行时正常返回 'ab'，类型注解不参与运行
- [C] 解释器会在定义 add 时报错
- [D] 只有在开启 -X typehints 后才会报错

**参考答案**：1

**解析**：Python 不会在运行时校验类型注解，'a' + 'b' 会正常拼接成 'ab'。static 检查工具如 mypy 才会报告类型错误。

### single_choice · None



- [A] --strict 会启用一系列更严格的检查选项，如禁止未注解的函数、禁止隐式 Optional 等
- [B] --strict 会强制 Python 解释器在运行时做类型检查
- [C] --strict 只能用于 Python 3.10 及以上版本
- [D] --strict 会把所有 Any 替换为 object

**参考答案**：0

**解析**：--strict 是 mypy 的一组严格模式选项的集合，用于提升检查强度，不会影响运行时行为。

### single_choice · None



- [A] def f(x: Union[int, str]) -> None: ...
- [B] def f(x: int or str) -> None: ...
- [C] def f(x: (int, str)) -> None: ...
- [D] def f(x: int | str) -> None 只能在 Python 2 中使用

**参考答案**：0

**解析**：Union[int, str] 表示参数可以是 int 或 str；Python 3.10+ 也可用 int | str，但 Union 更通用。

### single_choice · None



- [A] # type: ignore 会让 mypy 忽略该行所有类型错误
- [B] # type: ignore 会让 Python 运行时跳过该行代码
- [C] # type: ignore 只能用在函数定义行
- [D] # type: ignore 会改变变量的推断类型

**参考答案**：0

**解析**：# type: ignore 是给 mypy 的抑制注释，用于忽略该行的类型错误，不影响运行时执行。

### single_choice · None



- [A] 报告默认值 None 与参数类型 str 不兼容
- [B] 无错误，因为默认值可被忽略
- [C] 报告 'hi ' + name 可能为 str 与 None 相加
- [D] 报告 greet 缺少返回值注解

**参考答案**：0

**解析**：mypy 会检查默认值是否与参数类型兼容，把 None 作为 str 的默认值会报 "Incompatible default for argument"。

### single_choice · None



- [A] .pyi 文件用于给没有类型注解的库提供类型信息，供 mypy 等工具使用
- [B] .pyi 文件是 Python 编译后的字节码文件
- [C] .pyi 文件在运行时会被自动导入以加速执行
- [D] .pyi 文件只能存放变量，不能声明函数

**参考答案**：0

**解析**：stub 文件（.pyi）提供纯类型声明，不包含实现，运行时不会被自动导入，用于让静态检查器了解无注解库的类型。

### single_choice · None



- [A] Any 可赋值给任何类型且可调用任意方法，object 只能调用所有对象共有的方法
- [B] Any 是 object 的子类，object 是 Any 的子类
- [C] Any 只能在 Python 2 使用，object 只能在 Python 3 使用
- [D] Any 会在运行时做类型检查，object 不会

**参考答案**：0

**解析**：Any 是静态检查的逃生舱，与所有类型互相兼容；object 是最宽泛的具体类型，只包含所有对象都有的操作。

### single_choice · None



- [A] Callable[[int, str], bool] 表示接受 int 和 str 两个参数并返回 bool 的可调用对象
- [B] Callable[int] 表示接受任意参数并返回 int 的可调用对象
- [C] Callable 只能用于函数，不能用于类
- [D] Callable 等价于 typing.Any

**参考答案**：0

**解析**：Callable[[参数类型...], 返回类型] 描述可调用对象的签名；Callable[...] 中的中括号参数列表是必需的（或使用省略号表示任意参数）。

### single_choice · None



- [A] 推断为 List[Any]，因为初始值没有提供元素类型
- [B] 推断为 List[int]，因为之后 append 了 int
- [C] 推断为 list，无法用于 mypy
- [D] 报错，因为空列表不能作为变量初始值

**参考答案**：0

**解析**：空列表字面量在没有上下文时，mypy 通常推断其元素为 Any（在 strict 下可能要求显式注解），后续 append 不会改变推断。

### single_choice · None



- [A] reveal_type(x) 会让 mypy 打印出 x 的推断类型，但该调用是用于调试的，运行时一般应删除
- [B] reveal_type 是内置函数，运行时会打印类型
- [C] reveal_type 会修改 x 的类型
- [D] reveal_type 只能用于模块顶层

**参考答案**：0

**解析**：reveal_type 是 mypy 识别的特殊调用，用于输出推断类型便于调试；Python 运行时并没有该内置函数，通常会配合 # type: ignore 或删除。

### single_choice · None



- [A] 整个项目统一使用 --strict，无需区分模块
- [B] 只对核心业务模块启用严格检查，对第三方或旧代码放宽检查
- [C] 希望 mypy 在运行时自动修复类型错误
- [D] 想让 mypy 只检查单元测试文件

**参考答案**：1

**解析**：mypy 支持在配置文件中对不同模块设置不同严格程度，适合渐进式引入类型检查：核心模块严格、旧代码或第三方放宽。

### single_choice · None



- [A] 无错误，因为返回值是 int 也可当 str 用
- [B] 报告 "Incompatible return value type (got "int", expected "str")"
- [C] 报告 NameError: name 'str' is not defined
- [D] 报告语法错误，函数必须有返回值

**参考答案**：1

**解析**：mypy 会检查函数声明的返回类型与实际返回表达式类型是否兼容，返回 int 但声明为 str 会报 "Incompatible return value type"。

### single_choice · None



- [A] 参数只在 0 和 1 之间取值，表示布尔
- [B] 参数可能为 None，也可能是 int
- [C] 参数必须是正整数，其它值无效
- [D] 参数只能是 int 的子类

**参考答案**：1

**解析**：Optional[int] 等价于 Union[int, None]，表示值可以是 int 或 None，与是否为正整数或子类无关。

### single_choice · None



- [A] x 的类型会被推断为 Union[int, str]
- [B] x 第一次被标注为 int，第二次赋值 str 时 mypy 会报告类型不兼容
- [C] x 是 Any 类型，mypy 不会报告
- [D] Python 会抛出 SyntaxError

**参考答案**：1

**解析**：显式注解 x: int 之后，x 的类型被固定为 int；再赋 str 会与声明的类型冲突，mypy 会报 "Incompatible types in assignment"。

### single_choice · None



- [A] mypy 只会检查带有类型注解的函数和变量，未注解的代码默认不检查
- [B] 只要文件扩展名为 .py，mypy 就会对所有代码做严格类型检查
- [C] mypy 需要运行时才生效，不能在 CI 中离线运行
- [D] mypy 只能检查 Python 2 代码

**参考答案**：0

**解析**：mypy 默认对未注解的函数体不做严格检查，只有显式注解或推断出的类型才会被检查；可以开启 --disallow-untyped-defs 等选项加强。

### single_choice · None



- [A] 在 import 语句后加 # type: ignore，并在 mypy 配置中开启 follow_imports=skip 或对该模块设置 ignore_missing_imports
- [B] 把该包的源码文件全部改名为 .pyi 并删除实现
- [C] 在代码中不用 import，用 __import__ 动态加载
- [D] 在项目根目录放一个空 setup.py

**参考答案**：0

**解析**：mypy 支持通过 per-module 配置或 follow_imports=skip 忽略特定模块；ignore_missing_imports 也可让缺桩的包不报错。

### single_choice · None



- [A] 函数可以返回任意值，但推荐返回 None
- [B] 函数不返回任何有意义的值，等价于返回 None
- [C] 函数必须显式写 return None，否则 mypy 会报错
- [D] 函数不能有 return 语句

**参考答案**：1

**解析**：-> None 表示函数返回 None；即使函数体没有显式 return，也隐式返回 None，mypy 不会因此报错。

### single_choice · None



- [A] List[int] 只能在 Python 2 使用，list[int] 只能在 Python 3 使用
- [B] List[int] 来自 typing 模块，list[int] 是 Python 3.9+ 内建泛型写法，二者语义基本一致
- [C] list[int] 会在运行时创建新类型，List[int] 不会
- [D] List[int] 表示可变列表，list[int] 表示不可变列表

**参考答案**：1

**解析**：typing.List[int] 与内建泛型 list[int]（3.9+）语义相同，均表示元素为 int 的列表；后者需要较新版本的 Python。

### single_choice · None



- [A] result 被推断为 Any，因为没有显式注解
- [B] result 被推断为 int，因为函数的返回类型是 int
- [C] result 被推断为 List[int]
- [D] mypy 会报错，因为没有给 result 加注解

**参考答案**：1

**解析**：mypy 会根据被调用函数的返回类型注解自动推断变量的类型，因此 result 为 int。

### single_choice · None



- [A] Pyright 是 Mypy 的插件，必须先安装 Mypy 才能运行
- [B] Pyright 与 Mypy 是相互独立、可同时使用的两类静态类型检查器
- [C] Pyright 只能检查运行时报错，不能做静态类型推断
- [D] Pyright 是 Python 官方内置模块，导入即可使用

**参考答案**：1

**解析**：Pyright 与 Mypy 是两套独立实现的静态类型检查工具，都读取 PEP 484 风格的类型注解，但推断规则与默认严格度存在差异，可同时用于同一项目做交叉检查。Pyright 并非 Python 标准库的一部分，也不需要依赖 Mypy 运行。

### single_choice · None



- [A] 在代码每个文件顶部加 # type: ignore，整文件忽略检查
- [B] 修改 Python 解释器的版本，解释器越新检查越严格
- [C] 通过配置中的类型检查模式（如 off/basic/strict）来调节
- [D] 无法调整，Pyright 的严格程度由操作系统决定

**参考答案**：2

**解析**：Pyright 的严格程度由配置项（例如 VS Code 设置里的类型检查模式）决定，可在 off、basic、strict 等档位间切换；# type: ignore 是局部压制的临时手段，不能作为整体调节方式。

### fill_blank · None



**参考答案**：["cast", "typing.cast", "cast()"]

**解析**：`typing.cast(T, value)` 会告诉静态检查器把 value 视作类型 T，且不会做任何运行时转换，常用于检查器无法推断而开发者确知的场景。

### fill_blank · None



**参考答案**：["# type: ignore", "#type: ignore", "# type:ignore"]

**解析**：`# type: ignore` 是标准的单行类型检查忽略注释，Mypy 与 Pyright 都支持；应尽量只用在确有理由的个别行上。

### fill_blank · None



**参考答案**：["int | None", "int|None"]

**解析**：PEP 604 引入了 `X | Y` 语法来表达联合类型，`int | None` 与 `Optional[int]` 等价，Pyright 在合适的 Python 版本目标下都支持。

### code_reading · None



**参考答案**：会在 get_name 中 `return None` 那一处报「返回类型不兼容 / 可能为 None」类的错误，因为函数声明返回 str，但该分支返回 None；由于返回类型没有被声明为 Optional[str]，调用方也无法预知可能得到 None，因此后续 n.upper() 也处于不安全的假设之下。修正方式是把返回类型改为 Optional[str]，或在 None 分支改为返回空字符串等合法 str，再让调用方做相应判断。

**解析**：Pyright 依据函数返回注解做契约检查：声明 str 就要求所有 return 分支都产出 str。返回 None 违反契约，而契约错误会在使用点连带造成风险。

### code_reading · None



**参考答案**：会在 `print(p.y)` 这一行报错，因为 Point 中没有定义属性 y（实例属性 x 已通过 self.x 声明），Pyright 依据类的属性集合判断 p.y 不存在，因此给出「类型 Point 上不存在属性 y」一类的错误。

**解析**：Pyright 会根据类定义推断对象上可访问的属性集合。访问未声明的属性会被识别为错误，这也是它擅长发现的一类拼写或设计问题。

### code_reading · None



**参考答案**：不会报错。因为 total 初始化为 0（int），迭代源 nums 声明为 list[int]，for 循环中的 n 因而被推断为 int，`total += n` 是 int 与 int 相加，结果仍是 int，与返回注解 int 一致。

**解析**：该例是 Pyright 能正确推断的典型场景：初始化值的类型、容器元素类型和返回注解三者自洽，所以即使在较严格模式下也不会报错。

### scenario · None



**解析**：新增代码需严格、历史代码渐进修复，是团队落地的核心矛盾；通过限定检查范围（按目录/文件）并把新增部分调至严格模式，再对遗留问题用局部忽略或 cast 过渡、逐步修复，可以避免一次性大规模改动阻塞开发。

### scenario · None



**解析**：大量使用 `# type: ignore` 只是掩盖了真正的不确定性，没有解决可空性设计问题。更合适的做法是先通过 `if x is not None` 等控制流收窄，或修改类型注解表达真实的 Optional 契约，仅在确实无法静态化时用 cast 或局部忽略，并留下理由说明。

### single_choice · None



- [A] 这类报错总是运行时会崩溃的充分证据，必须立刻修
- [B] 这类报错提示的是契约层面的不一致，可能在某些运行路径下才真正出问题
- [C] 只要运行时没崩，就说明 Pyright 的报错完全无效，可以全部忽略
- [D] Pyright 只检查语法，不做任何跨行推断

**参考答案**：1

**解析**：静态检查是在分析所有可能的运行路径，因此报出的问题未必在本次执行中触发，但不代表它不存在。把它理解为契约不一致更准确：可能在某些分支下才暴露。它远超语法检查，会做跨行的类型推断。

### single_choice · None



- [A] 决定哪些文件参与类型检查，从而控制检查范围
- [B] 决定运行时使用哪个 Python 解释器
- [C] 决定 Pyright 是否联网更新
- [D] 决定代码的格式化缩进宽度

**参考答案**：0

**解析**：include/exclude 用于选择被检查的文件范围，配合渐进式引入非常关键。它与运行解释器、网络或格式化缩进无关。

### single_choice · None



- [A] 没有提示，因为运行时能自动把 123 转成字符串
- [B] 实参类型与形参声明不匹配（int 传给 str 参数）
- [C] 返回值缺少类型注解
- [D] 函数名 greet 与内置函数冲突

**参考答案**：1

**解析**：name 标注为 str，传入 123 是 int，属于参数类型不兼容。Python 运行时会抛 TypeError 而不是自动转换，所以「运行时能转换」的说法错误；返回值已有注解；函数名也不与内置函数冲突。

### single_choice · None



- [A] 它能在不运行代码的情况下指出某个分支返回值与注解不符
- [B] 它能替代所有单元测试
- [C] 它能自动修复业务逻辑 bug
- [D] 它能保证程序在所有输入下都不出错

**参考答案**：0

**解析**：静态类型检查的价值在于不运行即可发现契约与类型问题，例如某个分支的返回值与声明不符。它不能替代测试，也不自动修业务 bug，更无法保证所有输入都正确。

### single_choice · None



- [A] 在使用前直接赋值 x = None
- [B] 在使用前用 if x is not None: 进行收窄判断
- [C] 把变量注解改成 None
- [D] 在使用处加注释 # noqa

**参考答案**：1

**解析**：Pyright 支持基于控制流的类型收窄：在 `if x is not None:` 分支内会把 Optional[T] 收窄为 T，从而允许安全使用。直接赋 None 只会让类型更糟，注解成 None 也不能通过检查，# noqa 通常用于屏蔽 linter 而非类型检查。

### single_choice · None



- [A] 总是把列表元素推断为 Any，因为推导式无法静态分析
- [B] 会尝试从推导式的表达式与迭代源推断出列表的元素类型
- [C] 把整个列表推断为 tuple
- [D] 必须显式写 List[Any] 注解，否则一定报错

**参考答案**：1

**解析**：Pyright 会结合推导式中的产出表达式和迭代对象来推断容器元素类型，而不是一律退化成 Any 或 tuple；在能推断时不会强制要求显式注解。

### single_choice · None



- [A] 把整个项目配置改成关闭类型检查
- [B] 把该文件扩展名改成 .txt
- [C] 在该行加 # type: ignore 或对该表达式使用 cast
- [D] 删除该行代码中所有的变量名

**参考答案**：2

**解析**：局部问题应当局部处理：`# type: ignore` 可压制单行报错，`typing.cast` 可向检查器声明你确信的类型，二者都是最小干预。关闭整个项目的检查会掩盖其它真实问题，改扩展名或删变量名则会破坏代码。

### multi_choice · None



- [A] 先按目录或文件范围收紧，待修复后再扩大范围
- [B] 利用 Pyright 报出的错误清单逐类修复，而不是一次性全项目开启最严模式
- [C] 把所有变量注解统一写成 Any 以消除所有报错
- [D] 对确实无法静态化的少数位置局部使用忽略或 cast，并留下注释说明原因

**参考答案**：[0, 1, 3]

**解析**：渐进式收紧、分批修复、局部有理由的压制，都是让严格检查落地的常规策略。把变量一律标成 Any 相当于放弃类型信息，会掩盖问题而非解决，因此不正确。

### multi_choice · None



- [A] 向声明为 int 的参数传入 str
- [B] 访问一个在类中并未定义的属性
- [C] 程序在特定输入下产生的业务逻辑错误
- [D] 返回值类型与函数注解声明不一致

**参考答案**：[0, 1, 3]

**解析**：Pyright 关注类型与结构一致性：参数/返回值不匹配、访问未声明属性等都能识别。业务逻辑层面的错误（例如打折算错）超出静态类型检查的范围，需要测试来覆盖。

### multi_choice · None



- [A] 变量被注解为 Optional[int] 且尚未经过非 None 的收窄判断
- [B] 变量是通过一个可能返回 None 的调用得到的，且调用结果未做判断
- [C] 变量在该函数内被无条件地赋为具体的 int 值后就立即使用
- [D] 变量来自函数参数且调用方可能传入 None，而函数内未做检查

**参考答案**：[0, 1, 3]

**解析**：Optional 注解、可能返回 None 的调用结果、未校验的可空参数，都会让 Pyright 在使用点提示可能为 None。若变量在使用前被无条件赋为确定值，控制流分析会认定其非 None，因此第 3 项不会触发该提示。

### single_choice · None



- [A] 第 1 行，因为 list[int] 写法不被支持
- [B] 第 2 行，因为返回类型声明为 int，但分支可能返回 None
- [C] 不会提示，因为 if items 已经排除了空列表
- [D] 第 2 行，因为 items[0] 索引可能越界

**参考答案**：1

**解析**：当 items 为空时会返回 None，而函数返回注解是 int，二者不兼容，因此 Pyright 会对返回值行报「可能为 None」类型的错误。`if items` 排除的是空列表分支，但 else 分支返回 None 的现象依然存在。
