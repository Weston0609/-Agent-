# s2u4l1 在 AI 工程里，一个训练脚本动辄几百行，`loss`、 / Python 是动态类型语言，运行时并不强制检查你写下的

> 来源 `content/lessons/s2u4l1.json`

## py.typehint.basic

## 一句话直觉

**类型注解（Type Hint）** 就像给代码贴上「标签」：它不会改变程序运行结果，但能让编辑器、静态检查器（如 mypy、pyright）和同事一眼看懂「这个变量/函数应该是什么类型」，从而在运行前就发现低级错误。

在 AI 工程里，一个训练脚本动辄几百行，`loss`、`logits`、`batch` 满天飞。类型注解是让你半年后还能读懂自己代码的最低成本手段。

---

## 1. 为什么需要类型注解

Python 是**动态类型（dynamic typing）** 语言：变量本身没有类型，类型属于运行时的对象。好处是灵活，坏处是 IDE 无法在你写 `x + 1` 时判断 `x` 是不是数字。

类型注解让你显式声明意图，而不影响运行时。下面这段代码不写注解也能跑，但写注解后编辑器会立刻报错：

```python
# 没有注解：编辑器不知道 name 是 str 还是 int
name = "Alice"
# name + 1  # 编辑器不会提示；运行时才 TypeError

# 有注解：编辑器会直接划红线
name: str = "Alice"
# name + 1  # 编辑器提示：str 不支持 + int
```

关键结论：**注解是给「工具」看的元数据，不是给「解释器」用的强制约束**。

---

## 2. 变量注解与函数注解

最基本的两种位置：变量和函数参数/返回值。

```python
def add(a: int, b: int) -> int:
    return a + b

score: float = 95.5
names: list[str] = ["Alice", "Bob"]
config: dict[str, int] = {"epochs": 10}
```

点几个要点：

- `list[str]`、`dict[str, int]` 是 Python 3.9+ 的内置泛型写法，不需要 `from typing import List`。
- 函数注解不会在调用时被检查，`add("a", "b")` 依然会返回 `"ab"`。
- 返回 `None` 时要写 `-> None`，别省略。

---

## 3. 特殊类型：`Optional`、`Union`、`Any`

真实代码里最常见的三种「不纯」类型：

```python
from typing import Optional, Union, Any

def find_user(uid: int) -> Optional[str]:
    # Optional[str] 等价于 str | None
    return None if uid < 0 else "Alice"

def parse(x: Union[int, str]) -> int:
    # 3.10+ 可以写成 x: int | str
    return int(x)

def debug(obj: Any) -> None:
    # Any 表示放弃检查；能不用就不用
    print(obj)
```

关键结论：

- `Optional[X]` = `X | None`，不是「可选参数」的意思。
- `Union[A, B]` 用 `|` 写更短，3.10+ 推荐。
- `Any` 是逃生舱，滥用会让类型检查形同虚设。

---

## 4. 复合类型：`Callable`、`Iterable`、泛型

AI 代码里函数经常接收函数、迭代器，需要表达「容器里装的是什么」。

```python
from collections.abc import Callable, Iterable

def apply(fn: Callable[[int], int], xs: Iterable[int]) -> list[int]:
    # Callable[[参数类型], 返回类型]
    return [fn(x) for x in xs]

def first[T](xs: list[T]) -> T:
    # 3.12+ 泛型函数语法；旧版用 TypeVar
    return xs[0]
```

关键结论：

- `Callable[[int], int]` 表示「接收 int、返回 int 的函数」。
- `Iterable[int]` 比 `list[int]` 更宽，能接受生成器、tuple 等。
- 泛型让「输入什么类型，输出什么类型」的关系被工具理解。

---

## 5. 运行时校验：`typing.get_type_hints` 与 `pydantic`

注解默认不检查，但可以主动读出来做校验。这在配置解析、API 入参场景非常常见。

```python
from typing import get_type_hints

def greet(name: str, age: int) -> str:
    return f"{name} ({age})"

hints = get_type_hints(greet)
print(hints)  # {'name': <class 'str'>, 'age': <class 'int'>, 'return': <class 'str'>}
```

如果要自动校验，用 `pydantic` 这类库（AI 工程里几乎是标配）：

```python
# pip install pydantic
from pydantic import BaseModel

class TrainConfig(BaseModel):
    epochs: int
    lr: float = 1e-3
    model_name: str = "resnet18"

cfg = TrainConfig(epochs="10")  # 字符串会被强制转成 int
print(cfg.epochs, type(cfg.epochs))  # 10 <class 'int'>
```

关键结论：注解本身只是数据，`get_type_hints` 和 `pydantic` 把这份数据变成了运行时可执行的校验规则。

---

## 6. 与其他工具链对接

- **mypy**：`mypy train.py` 静态检查，不运行代码。
- **pyright / Pylance**：VS Code 内置，实时提示。
- **FastAPI**：直接用类型注解生成 API 文档和请求校验。
- **dataclasses**：`@dataclass` + 注解即可生成 `__init__`。

```python
from dataclasses import dataclass

@dataclass
class Batch:
    x: list[float]
    y: list[float]
```

---

## 动手练习

写一个 `train.py`，包含：

1. 一个函数 `normalize(values: list[float]) -> list[float]`，返回把每个元素除以最大值的列表；若列表为空返回 `[]`。
2. 一个 `@dataclass` 叫 `Config`，字段：`epochs: int`、`lr: float = 1e-3`、`name: str = "baseline"`。
3. 在文件末尾用 `get_type_hints` 打印 `normalize` 的类型注解，并调用 `normalize([2.0, 4.0, 8.0])`。
4. 本地安装 `mypy`（`pip install mypy`），执行 `mypy train.py`，确保 0 error。

提交内容：`train.py` 文件 + mypy 成功输出的截图或粘贴文本。

```python
from typing import Optional, get_type_hints
from dataclasses import dataclass


def normalize(values: list[float]) -> list[float]:
    """把列表每个元素除以最大值；空列表返回空列表。"""
    if not values:
        return []
    m = max(values)
    return [v / m for v in values]


@dataclass
class Config:
    epochs: int
    lr: float = 1e-3
    name: str = "baseline"


if __name__ == "__main__":
    # 打印函数类型注解，直观看到 str -> class 的映射
    print(get_type_hints(normalize))

    # 正常调用
    print(normalize([2.0, 4.0, 8.0]))

    # 空列表边界
    print(normalize([]))

    # dataclass 自动生成的 __init__
    cfg = Config(epochs=10)
    print(cfg)
```

## py.typehint.optional_union

## 一句话直觉

**类型注解（type hint）是写给“人”和“工具”看的说明书，而 `Optional`（可选）和 `Union`（联合）是用来描述“一个值可能是 A，也可能是 B，或者可能是 `None`”这件事的基本语法。**

Python 是动态类型语言，运行时并不强制检查你写下的类型注解；但当你把代码交给 IDE、`mypy`、`pyright`、CI 流水线时，这些注解就会变成提前抓住 bug 的第一道防线。学会 `Optional` 与 `Union`，你就能第一次准确地表达“这个函数可能返回 `None`”这样的真实业务语义——这是工程级 Python 代码的起点。

---

### 1. 从最简单的类型注解开始

在 Python 3.5+ 中，我们可以在变量、函数参数、返回值上写类型标注：

```python
def surface_area_of_cube(edge_length: float) -> str:
    return f"边长为 {edge_length} 的正方体表面积是 {6 * edge_length ** 2}"
```

- `edge_length: float` 表示参数期望是 `float`；
- `-> str` 表示返回值期望是 `str`。

注意：Python **运行时不会强制检查**这些注解。如果你传一个字符串进去，函数照样跑（然后在 `** 2` 处报错）。注解的真正用途是交给类型检查器（type checker）、IDE 补全和静态分析工具。

---

### 2. 什么时候需要 Union：一个值可能是多种类型

假设我们写一个函数，参数既可以是 `int`，也可以是 `str`（比如把它格式化后输出）：

```python
from typing import Union

def stringify(value: Union[int, str]) -> str:
    return str(value)
```

`Union[int, str]` 读作“`int` 或 `str`”。在 **Python 3.10+** 可以写成更简洁的 `int | str`：

```python
def stringify(value: int | str) -> str:
    return str(value)
```

`Union` 的价值：让静态检查器知道**所有合法的输入类型**，从而在你漏写分支时给出警告。例如：

```python
from typing import Union

def double(x: Union[int, float]) -> Union[int, float]:
    return x * 2   # 类型检查器接受；但如果你调用 double("a")，mypy 会报错
```

---

### 3. 什么是 Optional：语法糖，等价于 `Union[X, None]`

Python 中函数返回“找不到”的时候，惯例是返回 `None`。类型上要表达“可能是 `X`，也可能是 `None`”，就用 `Optional`：

```python
from typing import Optional

def find_user(user_id: int) -> Optional[str]:
    # 模拟查询：找不到返回 None
    if user_id == 1:
        return "Alice"
    return None
```

**关键事实**：`Optional[str]` 不是“可选参数”，而是 **`Union[str, None]` 的等价写法**。等价写法：

```python
from typing import Union

def find_user(user_id: int) -> Union[str, None]:
    ...
```

Python 3.10+ 可直接写 `str | None`。

---

### 4. 处理 Optional 时的正确姿势：显式判空

由于返回值可能是 `None`，调用方必须先判定再使用，否则类型检查器（以及未来的你）都会骂人：

```python
from typing import Optional

def get_length(s: Optional[str]) -> int:
    if s is None:
        return 0
    return len(s)   # 到这里类型检查器知道 s 是 str
```

对比一下反例——虽然能跑，但类型检查器会报“`s` 可能是 `None`”：

```python
from typing import Optional

def bad_length(s: Optional[str]) -> int:
    return len(s)   # ❌ mypy: Argument 1 to "len" has incompatible type "Optional[str]"
```

---

### 5. 工程级写法：Optional 与 Union 的常见组合模式

真实工程里常见三种写法：

```python
from typing import Optional, Union, List, Dict

# ① 默认参数为 None（常见于“未传时用默认值”的语义）
def connect(host: str, port: Optional[int] = None) -> None:
    port = port or 8080
    print(f"连接 {host}:{port}")

# ② 返回多种“成功类型”，或失败时返回 None
def parse_int(s: str) -> Optional[int]:
    try:
        return int(s)
    except ValueError:
        return None

# ③ 字段可能为空（配置、JSON 反序列化场景）
Config = Dict[str, Union[str, int, None]]
config: Config = {"name": "svc", "port": 8080, "desc": None}
```

**风格建议**：一个新式项目（Python 3.10+）可以统一用 `X | None`；为兼容旧版本或强调可读性时，`Optional[X]` 也完全没问题。二者在语义上等价。

---

### 一句话总结

- `Union[A, B]` / `A | B`：**“可能是 A 或 B”**；
- `Optional[X]` / `X | None`：**`Union[X, None]` 的简写**；
- 使用时记得**显式判空**，让类型检查器帮你把 `None` 相关 bug 提前打死。

```python
from typing import Optional, Union

# 演示 Union：参数可以是 int 或 str
def stringify(value: Union[int, str]) -> str:
    return str(value)

# 演示 Optional：找不到时返回 None
def find_user(user_id: int) -> Optional[str]:
    if user_id == 1:
        return "Alice"
    return None

# 演示 Optional 参数的正确判空
def greet(name: Optional[str]) -> str:
    if name is None:
        return "Hello, guest!"
    return f"Hello, {name}!"

if __name__ == "__main__":
    print(stringify(42))          # 42
    print(stringify("hi"))        # hi
    print(find_user(1))           # Alice
    print(find_user(2))           # None
    print(greet(None))            # Hello, guest!
    print(greet("Bob"))           # Hello, Bob!
```


---

## 本课题目

### single_choice · None



- [A] 运行时强制校验 name 必须是 str，否则抛出 TypeError
- [B] 为参数和返回值提供类型注解，供人和静态检查工具参考，运行时不强制
- [C] 把 name 自动转换为 str 类型后再传入函数体
- [D] 声明该函数只能被 str 类型的调用者使用

**参考答案**：1

**解析**：类型注解在运行时默认不做任何强制校验，它只是元数据，供阅读者和类型检查工具（如 mypy）使用。传入其他类型对象不会因注解本身报错。

### single_choice · None



- [A] 抛出 TypeError，因为 'hello' 不是 int
- [B] 打印 hello
- [C] 打印 0
- [D] 返回 None

**参考答案**：1

**解析**：类型注解不会在运行时检查或转换类型，f('hello') 正常返回字符串 'hello' 并被打印。

### single_choice · None



- [A] 表示函数没有返回值（返回 None），主要用于可读性和静态检查
- [B] 强制函数必须显式 return None
- [C] 运行时会检查函数是否真的返回 None
- [D] 表示该函数不能有 return 语句

**参考答案**：0

**解析**：-> None 只是表达设计意图，运行时不强制；函数仍可以直接 return 而不写值。

### single_choice · None



- [A] tuple[int, int]
- [B] tuple[int, ...]
- [C] Tuple[int]
- [D] List[int]

**参考答案**：0

**解析**：tuple[int, int] 表示恰好两个 int 的元组；tuple[int, ...] 表示任意长度的 int 元组；List[int] 是列表。

### single_choice · None



- [A] tuple[int, ...]
- [B] tuple[int, int]
- [C] tuple[int]
- [D] tuple[...]

**参考答案**：0

**解析**：省略号 ... 表示可变长度；tuple[int] 表示只有一个 int 的元组。

### single_choice · None



- [A] 在方法上用 @abstractmethod，并注解 `def speak(self) -> str: ...`
- [B] 把 speak 注解为 `speak: str`
- [C] 在类上写 `class Animal(Protocol[str])`
- [D] 把返回值注解为 `-> abstract str`

**参考答案**：0

**解析**：抽象方法用 @abstractmethod 标记，返回注解使用常规类型；Protocol 用于结构化子类型，不能这样带参数写。

### single_choice · None



- [A] Any 表示『任意类型』，任何值都可以赋给 Any，Any 也可以赋给任何类型
- [B] Any 等价于 object
- [C] Any 表示该变量必须是动态类型
- [D] Any 表示该值是 None

**参考答案**：0

**解析**：Any 会关闭该处的类型检查，双向兼容；object 表示所有类型的父类但不允许反向赋值；None 对应 NoneType。

### single_choice · None



- [A] Iterable[int]
- [B] List[int]
- [C] Sequence[int] 与 List[int] 都不等价于 Iterable[int]
- [D] Iterator[str]

**参考答案**：0

**解析**：typing.Iterable[int] 表示任何可被迭代、元素为 int 的对象；List 与 Sequence 是更具体的类型。

### single_choice · None



- [A] 使用类型注释（type comment）声明 x 是 int 列表，主要用于旧代码或需要避开注解语法歧义的场景
- [B] 把 x 强制转换成 List[int] 实例
- [C] 这是 Python 2 专用语法，Python 3 完全忽略
- [D] 它会导入 typing.List

**参考答案**：0

**解析**：type comment 是 PEP 484 中与变量注解并行的写法，工具会解析它，运行时同样不做强制。

### single_choice · None



- [A] 打印 {'a': <class 'int'>, 'b': <class 'str'>, 'return': <class 'bool'>}
- [B] 抛出 NameError，因为 'str' 是字符串
- [C] 打印空字典 {}
- [D] 打印 {'a': int, 'b': 'str', 'return': bool}

**参考答案**：0

**解析**：get_type_hints 会解析字符串形式的前向引用（如 'str'），把注解解析为真正的类型对象。

### single_choice · None



- [A] 使用字符串前向引用，例如 `'Node'`，必要时配合 `from __future__ import annotations`
- [B] 直接写 `Node`，Python 会自动延迟解析
- [C] 写 `self.__class__` 作为注解
- [D] 写 `type(self)` 作为注解

**参考答案**：0

**解析**：直接写尚未定义的类名会因名称未绑定而报错；使用字符串或 `from __future__ import annotations` 可以把注解延迟解析。

### single_choice · None



- [A] 它让所有注解在运行时以字符串形式保存，从而支持更自由的前向引用和延迟求值
- [B] 它启用运行时类型检查
- [C] 它把注解转换为 typing 模块中的对象
- [D] 它使注解在运行时被完全忽略，连 __annotations__ 都不再存在

**参考答案**：0

**解析**：该 future 导入让注解以字符串形式存储（PEP 563），便于前向引用，仍需工具解析；它不会启用运行时检查，__annotations__ 仍然存在。

### single_choice · None



- [A] count 会被自动转换成 int 类型
- [B] 该注解会被存入模块的 __annotations__ 中（作为元数据）
- [C] 如果之后写 count = 'abc' 会立即报错
- [D] 变量注解只能用于函数内部

**参考答案**：1

**解析**：模块级和类级变量注解会记录在 __annotations__ 中；运行时赋值不会被拦截，也不会自动转换类型。

### single_choice · None



- [A] list[int]
- [B] list(int)
- [C] [int]
- [D] List<int>

**参考答案**：0

**解析**：list[int] 是 PEP 585 引入的内置泛型写法；list(int) 是调用语法，[int] 只是含一个元素的列表，List<int> 不是合法语法。

### single_choice · None



- [A] dict[str, int]
- [B] dict(str, int)
- [C] dict<str, int>
- [D] dict[str -> int]

**参考答案**：0

**解析**：dict[str, int] 是标准写法；dict(str, int) 是调用 dict 构造函数的语法，另外两种都不是合法注解。

### single_choice · None



- [A] int | None
- [B] int & None
- [C] int or None
- [D] int and None

**参考答案**：0

**解析**：联合类型用 | 表示（PEP 604）；& 是位运算，or/and 是布尔运算，都不是类型联合语法。

### single_choice · None



- [A] Optional[int]（来自 typing）
- [B] Nullable[int]（来自 typing）
- [C] Maybe[int]（来自 typing）
- [D] Union[int]（不写 None）

**参考答案**：0

**解析**：typing.Optional[int] 等价于 Union[int, None]；typing 中没有 Nullable 或 Maybe。

### single_choice · None



- [A] Union[int, str]
- [B] Intersection[int, str]
- [C] Both[int, str]
- [D] Tuple[int, str]

**参考答案**：0

**解析**：Union 表示任选其一；Tuple[int, str] 表示一个两元素的元组类型；Intersection 不是 typing 中的类型。

### single_choice · None



- [A] Callable[[int], str]
- [B] Function[int, str]
- [C] Callable[int, str]
- [D] Func[[int], str]

**参考答案**：0

**解析**：typing.Callable[[参数类型列表], 返回类型] 是标准写法；括号不能省略，也没有 Function/Func 这样的类型。

### single_choice · None



- [A] args: int，kwargs: str
- [B] args 注解的是每个参数的类型（如 int），kwargs 注解的是每个值的类型（如 str）
- [C] args 注解整个元组类型，kwargs 注解整个字典类型
- [D] 两者都必须用 Any

**参考答案**：1

**解析**：*args 的注解表示每个位置参数的类型；**kwargs 的注解表示每个关键字参数值的类型，而不是整个容器类型。

### single_choice · None



- [A] 只能是 int 类型
- [B] 可以是 int 类型，也可以是 None
- [C] 可以是任意类型
- [D] 必须是 None

**参考答案**：1

**解析**：Optional[X] 等价于 Union[X, None]，表示该值要么是 X 类型，要么是 None；它并没有放宽到任意类型，也不是只能为 None。

### single_choice · None



- [A] Union[str, int]
- [B] Optional[Union[int, str]]
- [C] Union[int, str, None]
- [D] int | str 之外的写法都不等价

**参考答案**：0

**解析**：Union 中的类型顺序不影响语义，Union[int, str] 与 Union[str, int] 等价。Optional[Union[int, str]] 和 Union[int, str, None] 都额外允许了 None，不等价。

### multi_choice · None



- [A] Union[float, None]
- [B] float | None（Python 3.10+）
- [C] Union[float, int]
- [D] Optional[Union[float]]

**参考答案**：[0, 1, 3]

**解析**：Optional[float] 即 Union[float, None]。float | None 是 3.10+ 的等价写法；Optional[Union[float]] 等价于 Optional[float]。Union[float, int] 不含 None，不等价。

### multi_choice · None



- [A] Optional[X] 是 Union[X, None] 的简写
- [B] Union 中多个类型只要匹配其一即可
- [C] Optional 只能用于返回值，不能用于参数注解
- [D] Union 允许把 None 作为一个成员类型

**参考答案**：[0, 1, 3]

**解析**：Optional 是 Union[X, None] 的简写；Union 表示“之一”；None 可作为 Union 成员。Optional 可用于参数、返回值、变量等各种注解位置，故第三项错误。

### multi_choice · None



- [A] 查找函数在未找到时返回 None
- [B] 可选的配置项，未设置时为 None
- [C] 函数保证一定返回非空字符串时的返回值
- [D] 字典 .get(key) 的返回值

**参考答案**：[0, 1, 3]

**解析**：查找可能未命中、可选配置未提供、dict.get 未命中时都会得到 None，适合标注可选类型。函数保证返回非空字符串时不应包含 None。

### multi_choice · None



- [A] Optional[int] 表示“这个 int 是可选的，可以不用传”
- [B] Optional 会让运行时自动接受 None 并做类型转换
- [C] Optional[X] 在类型层面允许 None
- [D] 有了 Optional 注解，运行时就不再需要判空

**参考答案**：[0, 1, 3]

**解析**：Optional 描述的是“类型上可为 None”，与参数是否可省略无关，也不会做运行时转换或自动判空；第三项才是对 Optional 的正确描述。

### fill_blank · None



**参考答案**：["None", "NoneType", "type(None)"]

**解析**：Optional[X] 就是 Union[X, None] 的简写，缺失的成员是表示空值的 None（其类型可写作 NoneType）。

### fill_blank · None



**参考答案**：["int | None", "None | int"]

**解析**：在 3.10+ 中，int | None（顺序可交换）即可表达 Optional[int]，无需再导入 typing。

### fill_blank · None



**参考答案**：["int 或 str", "int或str", "int 或 None（错误理解）", "int or str", "整数或字符串"]

**解析**：Union[int, str] 表示返回值要么是 int，要么是 str；注意它并不包含 None。

### code_reading · None



**参考答案**：会警告 `print(idx + 1)` 这一行。因为 find 的返回类型是 Optional[int]，在未命中时会返回 None，而 None 不能参与整数加法。应先判断 idx is not None 再使用。

**解析**：Optional[int] 意味着返回值可能是 None；直接对可能为 None 的值做算术运算属于类型与运行时的双重风险，需先判空。

### code_reading · None



**参考答案**：输出为：第一行 empty，第二行 0。因为调用 f() 时 x 取默认值 None，返回 "empty"；调用 f(0) 时 x 为 0，0 不是 None，返回 str(0) 即 "0"。注意 0 与 None 不同。

**解析**：判断依据是 is None 而非真假值；0 为假值但不是 None，因此仍走非空分支，体现了 None 判断与布尔判断的区别。

### scenario · None



**解析**：返回值在未命中时为 None，因此返回类型应写成 Optional[str]（或 str | None，Python 3.10+），表示可能为 None。调用方在使用前应先做 None 判断，避免类型检查器报错及运行时空指针式错误（如对它做字符串操作）。

### single_choice · None



- [A] 两者含义相同，Optional[int] 就是 Union[int, None] 的简写
- [B] Optional[int] 允许 None，Union[int, None] 不允许
- [C] Union[int, None] 是语法错误
- [D] 两者含义不同，Optional 会额外允许空字符串

**参考答案**：0

**解析**：在 typing 中，Optional[X] 是 Union[X, None] 的等价写法，二者完全一致，只是书写风格不同。

### scenario · None



**解析**：在 Python 3.10+ 中 Optional[int] 与 int | None 语义等价，可以替换。但要注意：若项目还需支持 3.9 及更低版本，则不能直接用 | 写法；另外在运行时把复杂类型用到 isinstance 等场景时行为不同，需通过类型检查器与测试验证。

### single_choice · None



- [A] Python 3.6
- [B] Python 3.8
- [C] Python 3.10
- [D] Python 3.12

**参考答案**：2

**解析**：用 | 运算符组合类型（PEP 604）从 Python 3.10 起才在注解中受支持，3.10 之前需要用 typing.Union 或 typing.Optional。

### single_choice · None



- [A] 没有任何问题，name 一定是 str
- [B] name 可能是 None，直接调用 .upper() 存在风险
- [C] get_name 的返回类型写错了
- [D] Optional[str] 不是合法返回类型

**参考答案**：1

**解析**：返回值声明为 Optional[str]，说明可能为 None；直接对可能为 None 的值调用 .upper() 是不安全的，类型检查器会提示需要先判空。

### single_choice · None



- [A] 调用者必须传入 int，不能省略
- [B] 调用者可以不传该参数，也可以传 int 或显式传 None
- [C] 调用者只能传 None
- [D] 该参数不能有默认值

**参考答案**：1

**解析**：Optional 只描述类型允许 None，而默认值 None 使得参数可省略。两者结合意味着既可省略，也可传 int 或 None。

### single_choice · None



- [A] 会在运行时强制把值转换成 int 或 str
- [B] 会在传入其他类型时抛异常
- [C] 运行时不做类型校验，只对静态类型检查器有意义
- [D] 会自动把 int 转成 str

**参考答案**：2

**解析**：Python 的类型注解默认不参与运行时强制或校验，Union 只是给静态检查器的信息，不会在运行时阻止传入其他类型。

### single_choice · None



- [A] 直接 `len(x)`
- [B] 先 `if x is not None:` 再使用 x
- [C] 直接 `x + 'abc'`
- [D] 直接用 `x.strip()`，无需判断

**参考答案**：1

**解析**：因为 x 可能为 None，先做 None 判断再使用，能让类型检查器收窄类型为 str，是类型安全的标准做法。

### single_choice · None



- [A] 只要参数有默认值，就必须写成 Optional
- [B] 参数为 Optional 只说明类型上可为 None，并不代表一定有默认值
- [C] Optional 参数一定有默认值 None
- [D] 默认值为 None 的参数不能标注 Optional

**参考答案**：1

**解析**：Optional 描述的是类型是否包含 None，与是否有默认值是两件独立的事。一个 Optional 参数可以没有默认值（调用时必须显式传参，包括传 None）。

### single_choice · None



- [A] int | None
- [B] Union[int, None]
- [C] typing.Optional[int]
- [D] Union[None, int, str]

**参考答案**：3

**解析**：Union[None, int, str] 额外包含了 str，范围比 Optional[int] 更宽，因此不等价；其余三种都只表示 int 或 None。
