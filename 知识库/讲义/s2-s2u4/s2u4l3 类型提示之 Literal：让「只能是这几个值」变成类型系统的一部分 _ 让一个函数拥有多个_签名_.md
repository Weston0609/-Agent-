# s2u4l3 类型提示之 Literal：让「只能是这几个值」变成类型系统的一部分 / 让一个函数拥有多个"签名"

> 来源 `content/lessons/s2u4l3.json`

## py.typehint.literal

# 类型提示之 Literal：让「只能是这几个值」变成类型系统的一部分

> 一句话直觉：`Literal` 把「这个参数只能是 `'r'`、`'w'` 这几个固定值之一」这种口头约定，写进类型注解里，让类型检查器在编码阶段就替你拦下拼写错误、非法取值。

---

## 一、为什么需要 Literal？从「字符串常量」的痛点说起

在 Python 里，我们经常写这样的函数：

```python
def open_helper(file: str, mode: str) -> str:
    ...
```

调用方可以传 `'r'`、`'w'`、`'rb'`……但也可以随手传 `'typo'`、`'READ'`、`''`，函数内部才发现问题——**错误被推迟到运行时**。

即便你用最朴素的类型注解 `mode: str`，类型检查器（type checker，如 mypy、pyright）也只会告诉你「你传了一个字符串，没问题」，它**无法知道**你只允许某几个特定的字符串。

`typing.Literal` 就是为解决这个问题而设计的：它让「字面量值本身」成为一种类型（literal type，字面量类型）。

---

## 二、基本语法：Literal[...] 怎么用

`Literal` 是 `typing` 模块中的一个特殊类型构造器（special typing form）。写法如下（Python 3.8 起可用）：

```python
from typing import Literal

# Mode 只能取 'r'、'rb'、'w'、'wb' 四个值之一
type Mode = Literal['r', 'rb', 'w', 'wb']

def open_helper(file: str, mode: Mode) -> str:
    return f"open {file} with {mode}"

open_helper('/some/path', 'r')   # OK，通过类型检查
open_helper('/other/path', 'typo')  # 类型检查器报错
```

要点：

1. `Literal[...]` 至少要有一个参数，参数必须是**字面量值**（literal value，如字符串、整数、布尔值、`None`、枚举值等）。
2. `Literal` 不能被继承，也不能被实例化。
3. 运行时不做任何检查，它只是给类型检查器看的。

一个经典的例子是「函数返回值是某个固定的字面量」：

```python
from typing import Any, Literal

def validate_simple(data: Any) -> Literal[True]:
    # 这个函数永远返回 True
    return True
```

---

## 三、进阶细节：去重、顺序与嵌套

`Literal` 对象在比较时有一些有意思的规定（Python 3.9.1 起）：

```python
from typing import Literal

# 冗余参数会被自动跳过
assert Literal[1, 2, 1] == Literal[1, 2]

# 比较时不关心参数顺序
assert Literal[1, 2] == Literal[2, 1]

# 嵌套的 Literal 会被展开（flatten）
assert Literal[Literal[1, 2], 3] == Literal[1, 2, 3]

# 但通过 type alias 引用的 Literal 不会被展开
# type A = Literal[1, 2]
# assert Literal[A, 3] != Literal[1, 2, 3]
```

还有一个容易踩的坑：`Literal` 在运行时做相等比较时，若某个参数**不可哈希**（unhashable），会抛出 `TypeError`。例如不能在 `Literal` 里放 list。

---

## 四、Literal 与枚举、与字符串常量的关系

你可能会问：那我直接定义一个 `Enum`，或者用字符串常量不就行了？

- **字符串常量**：没有类型约束，仍能被传入任意字符串。
- **Enum**：可以，但对「简单的一组字符串/整数」有点重；类型检查器对 `Literal` 的推断通常更直接。
- **Literal**：轻量，适合「工具函数的选择参数」「API 的固定取值」「配置中的模式开关」等场景。

例如一个「返回一个固定 SQL 模板」的函数：

```python
from typing import Literal

type SqlTemplate = Literal['select_all', 'select_by_id', 'count']

def build_sql(template: SqlTemplate) -> str:
    if template == 'select_all':
        return 'SELECT * FROM t'
    if template == 'select_by_id':
        return 'SELECT * FROM t WHERE id = ?'
    return 'SELECT COUNT(*) FROM t'
```

类型检查器还能做**穷尽性检查**（exhaustiveness）：如果你用 `match` 处理 `int | str` 这样的联合类型，遇到底部类型 `Never`（在旧版本中对应 `NoReturn`）时会知道已经覆盖所有情况。`Literal` 配合联合类型，也能让这种检查更精确。

---

## 五、和 Final、ClassVar 的区别（避免混淆）

这三个常常被一起提及，但目标不同：

| 构造器 | 作用 |
| --- | --- |
| `Literal[...]` | 值是**某几个固定字面量**之一 |
| `Final` | 名字**不可被重新赋值** |
| `ClassVar` | 标注为**类变量**，不应在实例上赋值 |

例如：

```python
from typing import Final, Literal

MAX_SIZE: Final = 9000
# MAX_SIZE += 1  # 类型检查器报错

Level = Literal['debug', 'info', 'warning', 'error']
```

`Literal` 描述「能取哪些值」，`Final` 描述「能不能改」。二者可以叠加使用。

---

## 六、运行时行为：Literal 不做检查

最常见误解：以为 `Literal['r']` 会在运行时抛异常。**不会**。Python 运行时只把它当作一个普通的泛型（generic）对象，不做值校验。它的价值 100% 来源于类型检查器。

```python
from typing import Literal

mode: Literal['r'] = 'typo'  # 运行时不报错，但类型检查器会报错
```

所以在生产代码里，若要真正做运行时校验，还是要另外写 `if mode not in {'r', 'w'}` 之类的判断。

```python
from typing import Literal

type Mode = Literal['r', 'rb', 'w', 'wb']

def open_helper(file: str, mode: Mode) -> str:
    """根据文件路径和模式返回一句描述。"""
    return f"open {file!r} with mode {mode!r}"

# 合法的调用
print(open_helper('/tmp/a.txt', 'r'))
print(open_helper('/tmp/a.txt', 'rb'))

# 下面这行如果被类型检查器（mypy/pyright）扫描，会报类型错误：
# open_helper('/tmp/a.txt', 'typo')

# 演示 Literal 的去重与顺序无关
from typing import Literal as L
assert L[1, 2, 1] == L[1, 2]
assert L['a', 'b'] == L['b', 'a']
assert L[L[1, 2], 3] == L[1, 2, 3]
print('Literal 等价性演示通过')
```

## py.typehint.overload

# py.typehint.overload：让一个函数拥有多个"签名"

> **一句话直觉**：当一个函数根据参数类型的不同返回不同类型时，`@overload`（重载）让类型检查器（type checker）也能"看懂"这些分支，从而给调用者精确的类型提示——而不是一个含糊的 `Union`。

前置知识：本讲假设你会写基础的 Python 函数和类型注解（type hint），例如 `def f(x: int) -> str:`。这是本课的起点。

---

## 1. 为什么需要 overload：一个真实的困惑

考虑这样一个函数：它既可以接受整数返回整数，也可以接受字符串返回字符串。

```python
def double(x):
    return x + x
```

如果只写 `def double(x: int | str) -> int | str:`，类型检查器只知道"输入 int 或 str，输出 int 或 str"，但**不知道对应关系**。调用 `double(3)` 得到的结果类型是 `int | str`，你还得再判断一次。

`@overload` 解决的就是这个"输入-输出对应关系"的表达问题。它本身**不改变运行时行为**，只是在类型层面告诉检查器（如 mypy、pyright、IDE 的 Pylance）："这个函数有这些签名，请根据调用时实参类型选择对应的返回类型。"

> 关键事实：Python 运行时（runtime）**不强制**类型注解。`@overload` 装饰的函数体在运行时永远不会被调用，它只是给静态工具看的"声明"。

---

## 2. overload 的基本写法：三段式结构

使用 `@overload` 有一个严格的三段式规则：

1. 写若干个用 `@overload` 装饰的**存根（stub）**——只有签名和 `...`，没有函数体逻辑。
2. 最后写一个**真正的实现（implementation）**——不带 `@overload`，包含实际逻辑。
3. 实现体的签名要"兼容"所有存根（通常用最宽的类型或 `Any`）。

```python
from typing import overload

@overload
def double(x: int) -> int: ...

@overload
def double(x: str) -> str: ...

def double(x: int | str) -> int | str:  # 真正的实现
    return x + x
```

运行结果：`double(3)` 的类型是 `int`，`double("ab")` 的类型是 `str`。运行时行为完全不变——就是 `x + x`。

**注意**：实现函数**必须**紧跟在所有 `@overload` 存根之后，中间不能插入其它代码，否则类型检查器会报错。

---

## 3. 用 `@overload` 表达"按字面量分发"

`@overload` 最实用的场景之一，是根据**字面量参数（Literal）**返回不同类型。比如一个 API 客户端：

```python
from typing import overload, Literal

@overload
def fetch(url: str, *, as_json: Literal[True]) -> dict: ...

@overload
def fetch(url: str, *, as_json: Literal[False] = False) -> str: ...

def fetch(url: str, *, as_json: bool = False) -> dict | str:
    return {"ok": True} if as_json else "raw text"
```

调用 `fetch("x", as_json=True)` 被推断为 `dict`；`fetch("x")` 被推断为 `str`。这样调用者不必写 `isinstance` 判断，IDE 补全也能精确工作。

**要点**：`Literal[True]` 与 `Literal[False]` 让重载在"布尔开关"这类 API 上非常好用。

---

## 4. 类内部的重载：`__init__` 与方法

`@overload` 也可以用在类里，典型场景是构造函数根据参数不同而返回不同形态的对象。例如一个 `Vector`：

```python
from typing import overload

class Point:
    @overload
    def __init__(self, x: int, y: int) -> None: ...
    @overload
    def __init__(self, pair: tuple[int, int]) -> None: ...
    def __init__(self, *args) -> None:
        if len(args) == 2:
            self.x, self.y = args
        else:
            self.x, self.y = args[0]
```

**重要限制**：`@overload` 只能用于**方法/函数**，不能用于普通属性。类属性类型分发要用 `TypeVar` 或 `Generic`。

另外注意：`@overload` 装饰的方法**不能在运行时被 `getattr` 找到**——它被装饰器替换成了占位对象（`typing.overload` 返回一个 `_overload_dummy`），所以不要试图在运行时反射它。

---

## 5. 工程实践：什么时候用、什么时候别用

**该用 `@overload` 的场景**

- 函数根据参数类型/字面量返回不同类型，且这个对应关系对调用者很重要。
- 你正在为一个库（library）写公共 API，想让用户获得精确的类型提示。
- 你在包装 C 扩展、数据库驱动、或 `Path` 这类"多态输入"的接口。

**不要滥用的场景**

- 只是想让签名"看起来完善"——如果所有分支返回同一类型，直接写一个注解即可。
- 只在函数内部使用、没有外部调用者的私有工具函数——收益很低。
- 如果分支逻辑非常复杂，重载会变成"类型魔法"，可读性下降。此时考虑把函数拆成多个小函数。

**调试小贴士**：用 mypy 验证你的重载是否被正确识别：

```bash
pip install mypy
mypy your_file.py
```

如果实现体签名与存根不兼容，mypy 会报 `Overloaded function signatures 1 and 2 overlap with incompatible return types`。

**最后一个容易忽略的点**：`@overload` 函数在运行时如果被直接调用，会抛 `NotImplementedError`。所以真实实现必须是**不带 `@overload`** 的那个。也就是说，"三段式"里最后一段**必须存在**，并且被真正调用。

---

## 动手练习

写一个 `parse_value` 函数，满足以下要求：

1. 当参数是 `int` 时，返回 `int`。
2. 当参数是 `str` 且形如数字时，返回 `float`。
3. 当参数是 `list[int]` 时，返回 `int`（求和）。
4. 当参数是 `list[str]` 时，返回 `str`（拼接）。

用三个 `@overload` 存根 + 一个真实实现完成。然后：

- 用 `mypy file.py` 检查通过。
- 在 IDE（VS Code + Pylance，或 PyCharm）中把鼠标悬停在 `parse_value(3)` 上，确认显示返回类型是 `int`。
- 在悬停 `parse_value(["a", "b"])` 时确认显示 `str`。

**加分题**：如果参数是 `bool` 呢？提示——`bool` 是 `int` 的子类，思考 `@overload` 的匹配顺序（从上到下，先匹配先赢）。

```python
"""
py.typehint.overload 最小可运行示例。
注意：类型信息由 mypy / pyright / IDE 静态读取；
运行时行为与不带 @overload 的普通函数完全一致。
"""
from typing import overload, Literal


# ---------- 示例 1：按参数类型分发 ----------
@overload
def double(x: int) -> int: ...

@overload
def double(x: str) -> str: ...

def double(x: int | str) -> int | str:
    # 这是真正被调用的实现体（不带 @overload）
    return x + x


# ---------- 示例 2：按字面量开关分发 ----------
@overload
def fetch(url: str, *, as_json: Literal[True]) -> dict: ...

@overload
def fetch(url: str, *, as_json: Literal[False] = False) -> str: ...

def fetch(url: str, *, as_json: bool = False) -> dict | str:
    return {"ok": True, "url": url} if as_json else f"raw text from {url}"


if __name__ == "__main__":
    print(double(3))            # 运行时 -> 6
    print(double("ab"))         # 运行时 -> abab
    print(fetch("https://x"))   # 运行时 -> raw text from https://x
    print(fetch("https://x", as_json=True))  # 运行时 -> {'ok': True, 'url': 'https://x'}
```


---

## 本课题目

### single_choice · None



- [A] 限定变量只能取某几个具体的字面量值
- [B] 限定变量必须是字符串类型
- [C] 声明变量是运行时不可修改的常量
- [D] 把一个类型转换成它的字面量表示形式

**参考答案**：0

**解析**：Literal 用来把类型收窄为具体的字面量取值集合，而不是改变可变性或做类型转换。

### single_choice · None



- [A] mode: str
- [B] mode: Literal["r", "w", "a"]
- [C] mode: list["r", "w", "a"]
- [D] mode: Union["r", "w", "a"]

**参考答案**：1

**解析**：Literal 接受一组字面量作为合法取值；Union 里的字符串是类型而非取值集合，list[...] 表示列表类型。

### single_choice · None



- [A] list[Literal["x", "y"]]
- [B] Literal[list["x", "y"]]
- [C] list[str]
- [D] Literal["x", "y"]

**参考答案**：0

**解析**：把 Literal 放在元素位置可以约束每个元素的取值；Literal[list[...]] 则非法。

### single_choice · None



- [A] "on"、"off" 或 None
- [B] 只有 "on" 和 "off"
- [C] 任意字符串或 None
- [D] 任意类型

**参考答案**：0

**解析**：Optional 表示再额外允许 None，因此合法取值为 "on"、"off" 和 None。

### single_choice · None



- [A] x: Literal[1, 2] = 1
- [B] x: Literal[1, 2] = 2
- [C] x: Literal[1, 2] = 3
- [D] x: int = 1

**参考答案**：2

**解析**：3 不在 Literal[1, 2] 的取值集合中，因此该赋值不符合类型注解。

### single_choice · None



- [A] 两者完全等价，可以互相替代
- [B] Literal 用字面量值表达固定取值集合，Enum 用枚举成员表达，且枚举是运行时对象
- [C] Enum 只能用于类型注解，Literal 只能在运行时使用
- [D] Literal 的成员在运行时是枚举实例

**参考答案**：1

**解析**：Literal 是纯类型层面的取值集合，Enum 会创建真实的运行时枚举对象，二者用途和形态不同。

### single_choice · None



- [A] 前者同时接受整数 1 和字符串 "1"
- [B] 前者会把 "1" 转成 1，因此与后者等价
- [C] 前者非法，因为 Literal 不允许混合类型
- [D] 前者等价于 Union[int, str]

**参考答案**：0

**解析**：Literal 可以混合多种字面量类型；每个取值单独匹配，不会做类型转换。

### single_choice · None



- [A] dict[Literal["a", "b"], int]
- [B] Literal[dict["a", "b"], int]
- [C] dict[str, Literal["a", "b"]]
- [D] Literal[dict[str, int]]

**参考答案**：0

**解析**：字面量约束放在键的位置即可；放到值位置或外面都不能表达键的取值范围。

### single_choice · None



- [A] Literal[1] 是 Literal[1, 2] 的子类型
- [B] Literal[1, 2] 是 Literal[1] 的子类型
- [C] 两者相等
- [D] 两者没有子类型关系

**参考答案**：0

**解析**：取值范围更小的字面量类型是范围更大的字面量类型的子类型。

### single_choice · None



- [A] method = "GET"
- [B] method = "PUT"
- [C] method = "get"
- [D] method = ""

**参考答案**：0

**解析**：只有精确匹配 "GET" 或 "POST" 的字面量才符合注解，大小写和拼写都敏感。

### single_choice · None



- [A] 两者可以互换使用
- [B] 类型层面它们不相等，因为 True 和 1 是不同类型的字面量
- [C] 运行时 True 会被当作 1 从而等价
- [D] Literal[True] 会自动转换为 Literal[1]

**参考答案**：1

**解析**：虽然有 True == 1 的运行时相等性，但类型检查中 True 与 1 属于不同的字面量类型。

### single_choice · None



- [A] 可以，直接写成 Literal[None]
- [B] 不可以，必须用 Optional
- [C] 不可以，None 不是合法注解
- [D] 可以，但只能在 Python 3.10 之后

**参考答案**：0

**解析**：None 也是字面量，可写入 Literal；在需要允许 None 时也可与 Optional 组合使用。

### single_choice · None



- [A] 不会报错，因为 3 也是 int
- [B] 会报错，因为 3 不在字面量取值集合中
- [C] 只有运行时才报错
- [D] 会报错，因为 Literal 不能用于函数参数

**参考答案**：1

**解析**：Literal[1, 2] 只接受 1 和 2；3 虽然同属 int，但不在允许的字面量集合内。

### single_choice · None



- [A] 两者完全等价
- [B] Literal[True] 是 bool 的子类型，仅接受 True
- [C] Literal[True] 等价于 Literal[1]
- [D] Literal[True] 在运行时会把值强制转为 True

**参考答案**：1

**解析**：Literal[True] 是 bool 的收窄子类型，只允许 True；类型层面 True 与 1 不等价。

### single_choice · None



- [A] Literal["a"] 是 str 的子类型
- [B] str 是 Literal["a"] 的子类型
- [C] 两者互不相干
- [D] Literal["a"] 会在运行时变成 str 的子类

**参考答案**：0

**解析**：字面量类型是它对应基础类型的子类型，因此 Literal["a"] 可赋给 str，反之不行。

### single_choice · None



- [A] Literal[1, "a", True, None]
- [B] Literal[int]
- [C] Literal[list[int]]
- [D] Literal[1 + 1]

**参考答案**：0

**解析**：Literal 的参数必须是字面量值；不能使用类型、容器类型或表达式。

### single_choice · None



- [A] import Literal
- [B] from typing import Literal
- [C] from collections.abc import Literal
- [D] from typing_extensions import Literal 是唯一方式

**参考答案**：1

**解析**：自 Python 3.8 起 Literal 位于标准库 typing 中。

### single_choice · None



- [A] 合法，因为 "rb" 是 str
- [B] 不合法，因为 "rb" 不在允许的字面量中
- [C] 合法，因为 Literal 只在运行时生效
- [D] 不合法，因为 Literal 不接受字符串

**参考答案**：1

**解析**：Literal 限制的是取值集合，"rb" 不在其中，因此类型检查会报告错误。

### single_choice · None



- [A] bool 同时允许 True 和 False，Literal[True] 只允许 True
- [B] bool 只允许 True，Literal[True] 允许 True 和 False
- [C] 两者都只允许 True
- [D] 两者都允许 True 和 False

**参考答案**：0

**解析**：基础类型 bool 覆盖两个取值；字面量类型 Literal[True] 把范围收窄为单个取值。

### single_choice · None



- [A] Literal["a", "b"] 在运行时会创建一个枚举类
- [B] Literal["a", "b"] 在运行时不会强制校验传入值
- [C] Literal 会在运行时对实参自动转换类型
- [D] Literal 要求所有取值必须可哈希，否则运行时抛异常

**参考答案**：1

**解析**：类型注解默认不影响运行时行为，Literal 主要供静态检查器使用，不会自动校验或转换。

### single_choice · None



- [A] 使用 @overload 装饰器声明多个重载签名，再编写一个实际实现
- [B] 在函数内部使用 isinstance 判断后直接 return，无需额外声明
- [C] 使用 @staticmethod 装饰器
- [D] 使用 @property 装饰器

**参考答案**：0

**解析**：@overload 用于为同一个函数声明多个类型签名，帮助类型检查器（如 mypy）根据实参类型推导返回类型；仅有 isinstance 分支无法让静态检查器推导出精确的返回类型。

### single_choice · None



- [A] @overload 装饰的函数可以有完整函数体，且会被优先调用
- [B] @overload 装饰的签名函数体通常用 ... 或 pass 占位，真正被调用的是最后一个不带 @overload 的实现
- [C] 所有用 @overload 声明的签名都必须有相同的参数个数
- [D] @overload 只能用于类方法，不能用于模块级函数

**参考答案**：1

**解析**：被 @overload 装饰的函数只是类型签名，运行时会被后面的实现覆盖，因此其函数体通常写 ... 或 pass；真正被调用的是最后一个未加 @overload 的实现。

### single_choice · None



- [A] 重载签名中必须为所有参数都提供默认值
- [B] 重载签名中不应给参数提供默认值，默认值只应出现在实现函数中
- [C] 实现函数不能有默认参数
- [D] 默认参数会自动被类型检查器忽略

**参考答案**：1

**解析**：@overload 签名表示的是调用约定，不应写默认值（默认值属于实现细节）；实现函数才提供实际默认值。

### single_choice · None



- [A] @classmethod
- [B] @staticmethod
- [C] 无需额外装饰器，普通实例方法即可
- [D] @property

**参考答案**：2

**解析**：实例方法直接定义即可，@overload 叠加在方法上；若为类方法/静态方法，则应相应配合 @classmethod / @staticmethod，但本题问的是普通实例方法，故选无需额外装饰器。

### multi_choice · None



- [A] @overload 只对静态类型检查器有意义，运行时不做分派
- [B] 被 @overload 装饰的函数体通常写成 ... 或 pass
- [C] 最后一个不带 @overload 的实现会在运行时生效
- [D] 重载签名可以任意定义，不要求与实现兼容
- [E] 类型检查器按声明顺序选择匹配的签名

**参考答案**：[0, 1, 2, 4]

**解析**：选项 D 错误：重载签名必须与实现兼容；其余说法均符合 @overload 的规则。

### multi_choice · None



- [A] 函数接受 int 或 str，返回相应类型
- [B] 函数在传入 None 时返回 None，传入 int 时返回 int
- [C] 函数根据传入布尔值 True/False 返回完全相同的类型
- [D] 函数在传入 list 时返回 list，传入 tuple 时返回 tuple
- [E] 函数根据运行时的随机数决定返回值类型

**参考答案**：[0, 1, 3]

**解析**：A、B、D 都是类型与返回类型联动的典型重载场景；C 无需重载；E 依赖运行时随机值，静态类型无法表达。

### multi_choice · None



- [A] 只写了 @overload 签名，没有写不带 @overload 的实现
- [B] 把更宽泛的签名写在更具体的签名之前
- [C] 在重载签名中给参数提供了默认值
- [D] 在实现函数中使用了与签名一致的参数名
- [E] 在重载签名中使用与实现不兼容的参数种类（如仅关键字与位置参数冲突）

**参考答案**：[0, 1, 2, 4]

**解析**：A 缺少实现；B 顺序问题；C 签名中不应有默认值；E 参数种类不兼容会报错。D 是正确做法。

### fill_blank · None



**参考答案**：["...", "Ellipsis", "pass"]

**解析**：被 @overload 装饰的函数体只需占位，常见写法是 ... 或 pass。

### fill_blank · None



**参考答案**：["int, str", "int,str"]

**解析**：TypeVar 可以接受约束类型列表，例如 TypeVar('T', int, str)，表示 T 只能是 int 或 str。

### code_reading · None



**参考答案**：输出为 `1 a`。因为只有最后一个不带 @overload 的实现函数会在运行时生效，前面的 @overload 签名仅对静态类型检查器可见，运行时被覆盖，因此调用的是 return x 的实现。

**解析**：@overload 不参与运行时逻辑，运行时只保留最后的实现函数，故输出原始参数。

### code_reading · None



**参考答案**：类型检查器很可能匹配到第一个签名 g(x: object) -> object，因此推断 g(1) 返回 object，而不是 int。因为签名按声明顺序匹配，宽泛签名在前会「截胡」后面的具体签名，使得 g(x: int) -> int 形同虚设。

**解析**：类型检查器自上而下匹配签名，宽泛签名应放在更具体签名之后，否则具体重载不会被选用。

### scenario · None



**解析**：通过为 parse 添加多个 @overload 签名，并保留一个不带 @overload 的实现函数，类型检查器就能根据实参类型匹配对应签名，从而推断精确的返回类型。

### single_choice · None



- [A] 各重载签名可以任意定义，不必与实际实现兼容
- [B] 各重载签名应当与实现的参数名和参数种类保持兼容，否则类型检查器会报错
- [C] 只要返回值类型一致，参数可以完全不同
- [D] 实现函数必须使用与所有重载签名完全相同的参数名，否则运行时会崩溃

**参考答案**：1

**解析**：重载签名需要与实现的参数结构兼容（参数名、位置/关键字种类等），否则 mypy 等检查器会报错；但实现本身是运行时唯一执行体，参数名不一致并不导致运行时崩溃。

### scenario · None



**解析**：所有 @overload 装饰的函数体都是占位符，运行时没有真正的实现体，因此调用不会得到预期结果。修复方法是补上最后一个不带 @overload 的实现函数，并保证其参数与各重载签名兼容。

### single_choice · None



- [A] 使用 TypeVar 约束返回类型与参数类型一致，例如 T = TypeVar('T', int, str)
- [B] 把所有重载签名写成返回 Any
- [C] 使用 @overload 并让每个签名都返回 object
- [D] 使用 Optional 包裹返回值

**参考答案**：0

**解析**：这种「输入类型与输出类型联动」的场景用 TypeVar（受限类型变量）最合适；@overload 也常用于此类场景，但选项中首选用 TypeVar 表达类型一致性，是更贴合题意的答案。

### single_choice · None



- [A] 实现函数写在最前面，@overload 签名写在后面
- [B] @overload 签名写在前面，最后一个不带 @overload 的实现写在最后
- [C] @overload 签名和实现函数必须写在两个不同的模块中
- [D] @overload 签名必须全部写在文件末尾

**参考答案**：1

**解析**：运行时只有最后一个非 @overload 的实现会被保留，所以必须先写重载签名再写实现。

### single_choice · None



- [A] @overload 会在运行时检查参数类型并自动分派到对应签名
- [B] @overload 在运行时不做任何类型分派，它只是给静态类型检查器的信息
- [C] @overload 会在运行时抛出 TypeError
- [D] @overload 会修改函数的字节码以实现重载

**参考答案**：1

**解析**：@overload 只对静态类型检查器有意义，运行时被装饰的签名会被后续实现覆盖，语言本身不做运行时类型分派。

### single_choice · None



- [A] 程序会在导入时报 SyntaxError
- [B] 所有带 @overload 的函数体都是占位符，运行时调用可能不会得到预期结果或报错
- [C] 类型检查器会自动补上实现
- [D] 程序正常运行，类型检查器自动选择最后一个签名作为实现

**参考答案**：1

**解析**：若实现也被 @overload 装饰，运行时就没有真正执行的函数体，调用时会得到占位实现的结果或报错，且类型检查器可能报「缺少实现」之类的错误。

### single_choice · None



- [A] 函数根据第一个参数是 int 还是 str 返回不同类型
- [B] 函数在不同参数个数下行为不同（如一个参数或两个参数）
- [C] 函数需要根据参数值（如值为 0 或 1）返回类型不同的结果，且值不是字面量类型
- [D] 函数在传入 bytes 时返回 bytes，传入 bytearray 时返回 bytearray

**参考答案**：2

**解析**：@overload 基于类型而非运行时的值分派；若区分依据是具体数值（且不是 Literal 字面量类型），静态重载无法表达。

### single_choice · None



- [A] 随机选择一个签名
- [B] 按声明顺序，从上到下找到第一个与实参类型兼容的签名
- [C] 总是选择参数最多的签名
- [D] 总是选择返回值类型最宽泛的签名

**参考答案**：1

**解析**：类型检查器按声明顺序匹配签名，因此更具体、更特化的签名应放在前面。

### single_choice · None



- [A] 程序运行时崩溃
- [B] 类型检查器可能总是匹配到宽泛签名，导致具体签名永远不被选用
- [C] Python 解释器会拒绝导入
- [D] @overload 会自动重排签名顺序

**参考答案**：1

**解析**：按顺序匹配的机制下，宽泛签名若在前，会「截胡」所有调用，导致更具体的重载形同虚设。
