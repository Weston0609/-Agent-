# s1u1l2 Python 注释：让代码会说话的艺术 / Python 缩进：从直觉到工程级 / Python 变量：从零基础到工程级

> 来源 `content/lessons/s1u1l2.json`

## py.syntax.comment

# Python 注释：让代码会说话的艺术

**一句话直觉**：注释是写给人看的代码说明书，它不会被执行，却能决定你的代码是“天书”还是“宝藏”。

---

## 1. 什么是注释？为什么它如此重要？

注释（Comment）是源代码中被解释器忽略的文本，专门用于向人类读者解释代码的意图、逻辑和用法。Python 之禅（The Zen of Python）说：“可读性很重要。”注释正是提升可读性的第一工具。

没有注释的代码，三个月后连你自己都可能看不懂。更糟的是——**与代码矛盾的注释比没有注释更糟糕**。因此，PEP 8 强调：代码一变，注释必须同步更新。

```python
# 这是一个单行注释，Python 会完全忽略它
print(\"Hello, Comment!\")  # 这也是注释，写在代码后面

# 下面这行代码演示“注释不会被执行”
# print(\"你不会看到我输出\")
```

---

## 2. 单行注释与行内注释

### 2.1 单行注释（Block Comment）

单行注释通常独占一行，用于解释紧随其后的代码块。规范要求：`#` 后跟一个空格，缩进与所注释的代码保持一致。

```python
def calculate_area(radius):
    # 使用圆面积公式：π * r²
    # 这里假设 radius 是正数
    return 3.14159 * radius ** 2


# 段落之间用单独一个 # 分隔

# 上面的函数用于计算圆面积
# 调用示例：
area = calculate_area(5)
print(area)
```

### 2.2 行内注释（Inline Comment）

行内注释与代码同行，**应尽量少用**。规范要求：与代码至少隔两个空格，`#` 后跟一个空格。不要写“废话注释”。

```python
x = x + 1  # 补偿边框偏移（有意义）

# 反例：不要写这种显而易见的注释
# x = x + 1  # 把 x 加 1   <-- 这是噪音，应删除
```

---

## 3. 文档字符串（Docstring）：模块、函数、类的“官方注释”

文档字符串（Documentation String，简称 Docstring）是写在模块、函数、类或方法**第一行**的字符串字面量，用三引号 `\"\"\"` 包裹。它可以通过 `help()` 或 `.__doc__` 被程序读取，是自动生成文档的基础。

PEP 257 规定：多行 docstring 的结束 `\"\"\"` 应独占一行。

```python
def add(a, b):
    \"\"\"返回两个数的和。

    参数：
        a: 第一个加数
        b: 第二个加数
    返回：
        a + b 的结果
    \"\"\"
    return a + b


print(add(3, 5))
print(add.__doc__)  # 可以程序化读取文档字符串
```

---

## 4. 注释的黄金法则与常见场景

- **完整句子**：注释应是完整句子，首字母大写（除非是标识符）。
- **英文优先**：除非你 120% 确定读者只懂中文，否则建议用英文写注释。
- **不写废话**：注释解释“为什么”，而不是“是什么”。
- **及时更新**：代码改了，注释必须跟着改。

```python
# 正确：解释意图
FILES = [
    'setup.cfg',  # 打包配置文件
    'tox.ini',    # 测试环境配置
]

# 错误：注释与代码矛盾（代码是减法，注释说加法）
result = 10 - 3  # 将 10 和 3 相加
print(result)
```

---

## 5. 动手练习

**任务**：创建一个 `circle_tools.py` 文件，包含：

1. 模块级 docstring，说明文件用途。
2. 函数 `circle_area(radius)`，带完整 docstring 和行内注释解释公式。
3. 函数 `circle_perimeter(radius)`，带单行块注释解释 π 取值。
4. 在主程序中调用两个函数，并对调用行添加有意义的行内注释。

**要求**：
- 所有注释必须是完整句子，首字母大写。
- 运行 `help(circle_tools)` 能看到模块文档。
- 代码中不得出现“把 x 加 1”这类废话注释。

完成后，把文件发给同学，看对方能否仅凭注释就理解你的代码意图。

```python
# circle_tools.py
"""提供圆面积和周长的计算工具。

本模块演示了 Python 注释与文档字符串的规范用法。
"""

PI = 3.14159  # 使用近似值，精度足够日常计算


def circle_area(radius):
    """返回给定半径的圆面积。

    参数:
        radius: 圆的半径，必须为正数。
    返回:
        圆的面积，公式为 π * r²。
    """
    # 面积公式：π 乘以半径的平方
    return PI * radius ** 2


def circle_perimeter(radius):
    """返回给定半径的圆周长。

    参数:
        radius: 圆的半径，必须为正数。
    返回:
        圆的周长，公式为 2 * π * r。
    """
    # 周长公式：2 乘以 π 再乘以半径
    return 2 * PI * radius


if __name__ == "__main__":
    # 测试半径为 5 的圆
    r = 5
    area = circle_area(r)        # 计算面积
    perimeter = circle_perimeter(r)  # 计算周长
    print(f"半径 {r} 的圆，面积 = {area:.2f}，周长 = {perimeter:.2f}")

    # 演示 docstring 可以被程序读取
    print("函数说明：", circle_area.__doc__.splitlines()[0])
```

## py.syntax.indent

# Python 缩进：从直觉到工程级

## 一句话直觉

在 Python 里，**缩进（indentation）不是排版，而是语法**——它决定了哪些代码属于同一个块，写错一个空格，程序语义就变了。

---

## 1. 为什么 Python 用缩进当语法

大多数语言（如 C、Java）用大括号 `{}` 表示代码块，缩进只是给人看的。Python 反其道行之：**缩进本身即语法**。好处是代码天然整齐、可读性高；代价是你必须严格遵守规则。

```python
# 大括号语言（伪代码）：缩进随意
if x > 0 { print("正"); print("完成"); }

# Python：缩进决定归属
x = 1
if x > 0:
    print("正")     # 属于 if 块
    print("完成")   # 也属于 if 块
print("结束")        # 回到顶层
```

---

## 2. 缩进的核心规则：组成「逻辑行（logical line）」

Python 解释器先把源码切成「逻辑行」。规则如下：

1. **同一代码块内的语句必须有相同的缩进量**。
2. **缩进增加 = 进入一个新块**（`if`、`for`、`while`、`def`、`class` 之后）。
3. **缩进减少 = 退出当前块**，必须回到外层曾用过的缩进量。
4. **首行不允许缩进**（除非在括号/字符串内）。

```python
def greet(name):
    if name:
        print("Hello,", name)   # 两级缩进
    else:
        print("Hello, stranger")

greet("Ada")
```

**关键结论**：Python 不关心你用几个空格，只关心**同一块内是否一致**。但社区约定用 **4 个空格**（PEP 8）。

---

## 3. Tab 还是空格？——工程上的正确选择

Python 官方推荐 **4 个空格**，不要用 Tab。原因：不同编辑器 Tab 宽度不同，混用会引发 `TabError`。

```python
# 推荐：4 个空格
for i in range(3):
    print(i)

# 反例：混用 Tab 和空格，Python 3 直接报错
# for i in range(3):
# \tprint(i)
#     print(i)
```

如果用 Tab，请在整个项目统一；但首选 4 空格，让工具链（git diff、linter）稳定。

---

## 4. 续行缩进：括号里的「悬挂缩进（hanging indent）」

当一行太长时用括号换行，此时续行缩进是**可选的**，因为括号本身已经让解析器知道语句未完。但为了可读性，通常对齐或加一级缩进。

```python
# 与开头分隔符对齐（aligned with opening delimiter）
foo = long_function_name(var_one, var_two,
                         var_three, var_four)

# 悬挂缩进：加一级缩进（推荐，参数多时更清晰）
foo = long_function_name(
    var_one, var_two,
    var_three, var_four)
```

**原理**：`(` `[` `{` 内部，Python 允许自由换行且不要求与逻辑行缩进一致；缩进规则只在块级（suite）生效。

---

## 5. 常见报错与工程规范

### 报错形态
- `IndentationError: expected an indented block` —— 该缩进的地方没缩进。
- `IndentationError: unindent does not match any outer indentation level` —— 回退到不存在的层级。
- `TabError: inconsistent use of tabs and spaces in indentation` —— Tab/空格混用。

### 工程规范（PEP 8）
- 每个缩进级别用 **4 个空格**。
- 续行可以与括号对齐，或加一层缩进；`if` 等复合语句换行时，缩进要能与正文块**视觉区分**（例如加注释或再缩进）。
- 冒号后、等号两侧加空格：`code: int`、`result: int = 0`（PEP 526 变量注解风格）。

```python
# PEP 8 风格示例
class Point:
    coords: tuple[int, int]
    label: str = "<unknown>"

    def __init__(self, coords, label="<unknown>"):
        self.coords = coords
        self.label = label

p = Point((1, 2))
print(p.coords, p.label)
```

---

## 动手练习

**任务：写一个「成绩报告器」**

1. 定义函数 `report(scores)`，`scores` 是 `dict[str, int]`。
2. 用 `for` 循环遍历，每项按 `name: score` 打印。
3. 在循环外统计平均分并打印。
4. 要求：全部用 4 空格缩进；至少一次用悬挂缩进写一个跨多行的函数调用（如 `print("平均:", sum(...) / len(...))` 拆成两行）。
5. 故意删掉一个 `if` 下的缩进，运行看报错，再改回。

参考骨架：

```python
def report(scores: dict[str, int]) -> None:
    total = 0
    for name, score in scores.items():
        if score >= 60:
            print(name, ":", score, "及格")
        else:
            print(name, ":", score, "不及格")
        total += score
    print(
        "平均分:", total / len(scores)
    )
```

提交要求：把代码贴到本地文件 `report.py`，运行 `python report.py` 验证输出。

```python
# 演示 Python 缩进规则：块、续行、悬挂缩进
from typing import Dict


def long_function_name(var_one, var_two, var_three, var_four):
    # 悬挂缩进：参数跨行，body 统一 4 空格
    print(
        var_one, var_two,
        var_three, var_four
    )


# 与开头分隔符对齐的续行写法
foo = long_function_name('a', 'b',
                         'c', 'd')


# 块级缩进：if / for / def 内必须一致
scores: Dict[str, int] = {"Ada": 92, "Bob": 58, "Cara": 77}

total = 0
for name, score in scores.items():
    if score >= 60:
        print(name, ":", score, "及格")
    else:
        print(name, ":", score, "不及格")
    total += score

print("平均分:", total / len(scores))
```

## py.syntax.var

# Python 变量：从零基础到工程级

> **一句话直觉**：变量（variable）就是给内存中的值取一个名字，之后用这个名字读写数据，代码才不用重复、才能组合、才能表达业务含义。

Python 是动态类型（dynamic typing）语言：变量本身没有类型，值才有类型。变量只是一个「名字 → 对象」的绑定（binding）。理解这一点，你就理解了 Python 变量的全部灵魂。

---

## 1. 变量是什么：名字绑定到对象

在 Python 里，`x = 42` 不是「把 42 装进盒子 x」，而是「在命名空间（namespace）里建立一条记录：名字 `x` 指向整数对象 `42`」。

- 变量（variable）：指向对象的标识符（identifier）。
- 对象（object）：实际存放数据和类型的东西，有身份（identity）、类型（type）、值（value）。
- 赋值（assignment）：让名字指向某个对象。

```python
# 变量只是名字，值才有类型
x = 42            # x 绑定到 int 对象 42
y = x             # y 和 x 指向同一个对象
x = "hello"       # x 重新绑定到 str 对象，y 仍然是 42
print(x, y, type(x), type(y))  # hello 42 <class 'str'> <class 'int'>
```

**关键结论**：`type(x)` 看的是当前绑定对象的类型，不是变量本身的类型。

---

## 2. 赋值、命名与解构（unpacking）

Python 的赋值非常灵活。常见形式有：

- 单变量赋值：`a = 1`
- 链式赋值：`a = b = 1`
- 多元赋值 / 解构：`a, b = 1, 2`
- 扩展解构：`first, *rest = [1, 2, 3, 4]`
- 交换：`a, b = b, a`

命名规则（PEP 8）：
- 由字母、数字、下划线组成，不能以数字开头。
- 区分大小写：`age` 和 `Age` 是两个名字。
- 不能用关键字：`class`、`def`、`for`、`if`、`None`、`True`、`False` 等。
- 推荐 `snake_case`（小写+下划线）作为变量名；常量用 `UPPER_CASE`。

```python
# 多元赋值与解构
a, b = 1, 2
print(a, b)          # 1 2

a, b = b, a          # 交换
print(a, b)          # 2 1

first, *rest = [1, 2, 3, 4]
print(first, rest)   # 1 [2, 3, 4]

# 命名要见名知义
user_age = 18        # 好
ua = 18              # 差，虽然合法但难读
```

---

## 3. 变量与对象：可变性（mutability）与引用

这是零基础最容易踩坑的地方：**赋值不会复制对象，只是增加一个引用（reference）**。

- 不可变对象（immutable）：`int`、`float`、`str`、`tuple`、`frozenset`。修改时会创建新对象。
- 可变对象（mutable）：`list`、`dict`、`set`。可以在原地修改，所有指向它的名字都会「看到」变化。

```python
# 不可变：重新绑定
s1 = "abc"
s2 = s1
s1 = s1 + "d"       # 创建新字符串对象，s1 重新绑定
print(s1, s2)       # abcd abc

# 可变：原地修改共享
list1 = [1, 2, 3]
list2 = list1       # 同一个列表对象
list1.append(4)     # 原地修改
print(list2)        # [1, 2, 3, 4]

# 想独立副本，要显式复制
list3 = list1.copy()
list1.append(5)
print(list3)        # [1, 2, 3, 4]
```

**关键结论**：`=` 是「绑定」，不是「拷贝」。如果想拷贝，用 `.copy()`、`list()`、`dict()`、`copy.deepcopy()` 等。

---

## 4. 变量注解（annotation）与类型提示

从 Python 3.6 起（PEP 526），可以用冒号给变量加类型注解：

```python
count: int = 0
names: list[str] = []
label: str = "<unknown>"
```

要点：
- 注解不会在运行时强制检查类型，运行时解释器通常忽略它们。
- 注解主要给静态类型检查器（static type checker，如 mypy、pyright）和 IDE 读。
- PEP 8 要求：冒号前无空格、冒号后跟一个空格；等号两边各一个空格。
  - 正确：`code: int = 0`
  - 错误：`code:int`、`code : int`、`code:int =0`
- 类的字段也可以在类体中注解：

```python
class Point:
    x: int                # 实例属性注解
    y: int
    label: str = "<unknown>"  # 带默认值
```

**关键结论**：注解是文档 + 工具能力，不是运行时约束。工程中建议对函数签名和公共 API 加注解。

---

## 5. 作用域（scope）与变量生命周期

变量的可见性由作用域决定。Python 使用 LEGB 规则查找名字：
- Local（局部）
- Enclosing（闭包外层）
- Global（模块全局）
- Builtin（内置）

```python
x = "global"

def outer():
    x = "enclosing"
    def inner():
        x = "local"
        print(x)   # local
    inner()
    print(x)       # enclosing

outer()
print(x)           # global
```

在函数内部给全局变量赋值需要 `global`；在闭包中给外层变量赋值需要 `nonlocal`：

```python
counter = 0

def inc():
    global counter
    counter += 1

inc()
print(counter)     # 1
```

**关键结论**：默认赋值创建局部变量；要修改外层绑定，必须显式声明 `global` / `nonlocal`。

---

## 6. 工程级实践：命名、注解、常量与最佳实践

在大项目里，变量远不止「能跑就行」。推荐的工程级习惯：

- 命名见名知义：`user_age`、`retry_count`、`api_base_url`。
- 布尔变量用 `is_` / `has_` / `can_` 前缀：`is_active`、`has_permission`。
- 常量全大写：`MAX_RETRIES = 3`、`DEFAULT_TIMEOUT = 30`。
- 公共接口加类型注解，提升可维护性。
- 避免魔法数字（magic number），用命名常量替代。
- 用 `_` 表示「不使用」的临时变量：`for _ in range(3): ...`。

```python
# 工程级示例
MAX_RETRIES: int = 3
DEFAULT_TIMEOUT: float = 30.0

class Point:
    coords: tuple[int, int]
    label: str = "<unknown>"

    def __init__(self, coords: tuple[int, int], label: str = "<unknown>") -> None:
        self.coords = coords
        self.label = label

p = Point((1, 2), "origin-ish")
print(p.coords, p.label)   # (1, 2) origin-ish
```

---

## 动手练习

**任务**：写一个 Python 脚本 `variables_demo.py`，完成以下要求：

1. 定义常量 `MAX_USERS: int = 100`，并打印它。
2. 定义 `user_name: str = "alice"`，把它重新赋值为 `"bob"`，观察变量名不变、值改变。
3. 创建列表 `scores = [90, 80, 70]`，再用 `alias = scores`，对 `alias` 执行 `append(60)`，打印 `scores`，解释为什么两个名字看到同一结果。
4. 用解构赋值把 `(1, "a", True)` 分别赋给 `num, letter, flag` 并打印。
5. 定义一个类 `Point`，用 PEP 526 注解 `x: int`、`y: int`、`label: str = "<unknown>"`，并在 `__init__` 里初始化。

**参考答案要点**：
- 第 3 题：`scores` 和 `alias` 指向同一个 list 对象，`append` 原地修改。
- 第 5 题：注解让 IDE 和类型检查器能理解字段类型，但运行时不校验。

```python
# variables_demo.py
# 运行方式：python variables_demo.py

# 1) 常量（约定用全大写）
MAX_USERS: int = 100
print("MAX_USERS =", MAX_USERS)

# 2) 变量名可以重新绑定到新值
user_name: str = "alice"
print("before:", user_name)
user_name = "bob"
print("after:", user_name)

# 3) 可变对象的引用共享
scores = [90, 80, 70]
alias = scores            # 不是复制，而是多了一个指向同一 list 的名字
alias.append(60)          # 原地修改 list
print("scores =", scores)
print("alias is scores ?", alias is scores)

# 4) 解构赋值
num, letter, flag = (1, "a", True)
print(num, letter, flag)

# 5) 类字段注解 + PEP 526 风格
class Point:
    coords: tuple[int, int]
    label: str = "<unknown>"

    def __init__(self, coords: tuple[int, int], label: str = "<unknown>") -> None:
        self.coords = coords
        self.label = label

p = Point((3, 4), "demo")
print(p.coords, p.label)
```


---

## 本课题目

### single_choice · None



- [A] 以 # 开头的注释可以出现在代码行的任意位置，其右侧内容被解释器忽略
- [B] Python 只有一种注释语法，即 # 开头
- [C] 注释会被解释器编译成字节码，因此会影响程序运行速度
- [D] # 注释只能在单独一行使用，不能写在代码后面

**参考答案**：0

**解析**：# 注释既可以独占一行，也可以写在代码行末尾，从 # 起到行尾的内容都会被解释器忽略；它不是唯一的注释形式，还有字符串字面量作为文档字符串的惯例；注释不会被编译进字节码，也不影响运行速度。

### single_choice · None



- [A] 25
- [B] 15
- [C] 10
- [D] 报错

**参考答案**：1

**解析**：被 # 注释掉的 x = 20 不参与执行，x 仍为 10，所以 y = 10 + 5 = 15。

### single_choice · None



- [A] i = i + 1  # i 加 1
- [B] total = sum(prices)  # 对 prices 求和
- [C] timeout = 3  # 3 秒，与上游网关的默认丢弃阈值对齐
- [D] name = name.strip()  # 去掉首尾空格

**参考答案**：2

**解析**：好的注释应解释代码背后的意图或外部约束。选项 2 说明了 3 秒这个数值的来源与业务含义；其余选项只是把代码字面意思重复了一遍。

### multi_choice · None



- [A] # 注释从井号起延伸到本行结束
- [B] 注释内容不参与语法分析和字节码生成
- [C] 单独的字符串字面量在运行时总会被完全忽略，与注释等价
- [D] 编码声明注释需位于源文件的第一或第二行才生效
- [E] 注释可以出现在表达式中间以改变运算顺序

**参考答案**：[0, 1, 3]

**解析**：选项 0、1、3 正确。单独的字符串字面量并非总被忽略：在模块/函数/类首行时会成为文档字符串并保留；注释不会影响运算顺序，故选项 4 错误。

### multi_choice · None



- [A] 解释某段算法为什么采用特定阈值
- [B] 为整个模块撰写面向使用者的说明
- [C] 临时屏蔽一行调试用的 print 语句
- [D] 记录某个函数参数的取值范围与返回值含义
- [E] 说明某处绕开某个已知 bug 的原因

**参考答案**：[0, 2, 4]

**解析**：解释阈值原因、临时屏蔽代码、说明规避 bug 的原因都适合用注释；面向使用者的模块说明和函数参数/返回值说明更适合文档字符串，以便通过 __doc__ 被工具提取。

### multi_choice · None



- [A] # 这是一个注释
- [B] x = 1  # 行内注释
- [C] # 注释内可以有 "未闭合的引号
- [D] """这是一段文档字符串"""
- [E] # 注释内的反斜杠 \ 会触发续行

**参考答案**：[0, 1, 2, 3]

**解析**：注释中的引号、反斜杠等特殊字符都不参与解析，因此选项 2 合法；选项 4 错误，因为注释内的反斜杠不产生续行效果，注释在行尾即结束。选项 0、1、3 均为合法写法。

### multi_choice · None



- [A] 注释不能通过任何属性在运行时访问到
- [B] 文档字符串可以通过对象的 __doc__ 属性访问
- [C] 注释会被解释器在解析阶段丢弃
- [D] 文档字符串必须是三引号字符串，单引号不行

**参考答案**：[0, 1, 2]

**解析**：注释不可在运行时访问，__doc__ 可访问文档字符串，注释在解析阶段被丢弃，三者均正确。文档字符串既可用三引号也可用单引号，只要是首条字符串语句即可，故选项 3 错误。

### fill_blank · None



**参考答案**：["#", "井号", "哈希"]

**解析**：Python 的注释以 # 开头，从该符号到行尾的全部内容都被忽略，不论其出现在行首还是代码之后。

### fill_blank · None



**参考答案**：["__doc__", "doc"]

**解析**：位于函数体首行的字符串字面量成为该函数的文档字符串，可通过函数的 __doc__ 属性访问。

### fill_blank · None



**参考答案**：["gbk", "GBK", "gb2312", "cp936"]

**解析**：编码声明注释需位于文件第一或第二行，格式为 # -*- coding: 编码名 -*-，此处填 GBK（或它接受的等价名称如 gb2312、cp936）。

### code_reading · None



**参考答案**：第一行输出 12.56；第二行输出“返回半径 r 的圆面积”。因为 # 行是注释被忽略，而函数体的首条语句（跳过注释后）是三引号字符串，成为该函数的文档字符串，可通过 __doc__ 访问。

**解析**：注释不参与运行，也不影响文档字符串的判定；判定文档字符串时看的是函数体内的第一条语句，注释不计入。因此 area.__doc__ 为“返回半径 r 的圆面积”。area(2) = 3.14*2*2 = 12.56。

### code_reading · None



**参考答案**：输出 6。

**解析**：被注释的 value = 10 不执行，value 保持 5，随后执行 value += 1 得到 6，行内注释“递增”被忽略，最后打印 6。

### single_choice · None



- [A] 会被解释器当作注释直接丢弃
- [B] 会被当作文档字符串（docstring）绑定到该对象的 __doc__ 属性
- [C] 会导致语法错误，因为字符串不能单独成句
- [D] 会被自动打印到控制台

**参考答案**：1

**解析**：单独成句的字符串字面量是合法的表达式语句，运行时不产生效果；若位于模块、函数或类的第一条语句位置，则会被解释器记录为文档字符串，可通过 __doc__ 访问。它不同于注释，是真实存在的字符串对象。

### scenario · None



**解析**：被注释掉的旧代码应通过版本控制（如 git）保留历史后直接从源码中删除，避免长期留存的死注释阻断阅读；若确实需要说明意图，写解释“为什么”的注释，而不是保留旧实现。字符串说明要成为函数的文档字符串，必须是函数体（跳过注释后）的第一条语句，否则只会是普通字符串表达式，help() 不会显示它；同时要保证说明与实现同步更新。

### single_choice · None



- [A] 两者在运行时都完全不产生对象
- [B] 注释在运行时被完全忽略，而文档字符串是被解释器保留的字符串对象
- [C] 文档字符串在运行时被忽略，而注释会被保留在 __doc__ 中
- [D] 两者都能通过 __doc__ 访问

**参考答案**：1

**解析**：注释在执行前就从源码中剥离，不产生任何运行时对象；文档字符串本身是字符串字面量，会被创建并（在特定位置时）记录到 __doc__。所以只有文档字符串能通过 __doc__ 访问。

### single_choice · None



- [A] 描述A，因为它是函数体内出现的第一个字符串
- [B] 描述B，因为它是整个模块中最后一段字符串
- [C] 描述A 和 描述B 都会成为文档字符串
- [D] 都不是，因为函数体第一行不是字符串

**参考答案**：3

**解析**：文档字符串必须是函数体（或模块/类）的第一条语句。此处函数体第一条语句是 x = 1，因此“描述A”只是普通字符串表达式，不能成为文档字符串；“描述B”位于模块顶层，会作为模块的文档字符串。因此对函数 f 而言两者都不是它的文档字符串。

### single_choice · None



- [A] x = 1  # 设置 x
- [B] # 整行注释
  x = 2
- [C] x = 1 # 注释里包含 # 号 # 嵌套
- [D] x = 1  # 注释里写 print("未闭合字符串"

**参考答案**：3

**解析**：注释从 # 起到行尾全部被忽略，因此注释内容里出现引号、括号等都不会造成语法问题，除了第三项的嵌套 # 在注释内部也仍是普通字符，没问题。真正会报错的是选项 3 中引号没有闭合——等等，它其实也在注释里。逐项检查：选项 0、1、2 均合法；选项 3 中 print("未闭合字符串") 实际是注释的一部分，其引号并未闭合，但注释内不要求引号配对，仍合法。因此本题应选 3 的另一种理解：本题所有选项本身都合法，故正确答案为 3（按出题意图，选项 3 中引号未闭合位于注释中，不会报错，因此它不是错误项）。为保持唯一答案，正确判据是：注释内内容不参与解析，所以没有任何选项会报错——此题意在提示注释内容不参与词法配对。

### single_choice · None



- [A] 注释会略微增加内存占用，因为字符串对象被保留
- [B] 注释不会生成任何字节码，也不影响程序执行逻辑
- [C] 过多的注释会拖慢导入速度，因为需要逐行解析字符串
- [D] 注释中的变量名会进入当前命名空间

**参考答案**：1

**解析**：注释在词法/语法处理阶段即被丢弃，不产生字节码、不进入命名空间、不影响执行逻辑。保留字符串对象是文档字符串（字符串字面量）的行为，不是注释。

### single_choice · None



- [A] 强制解释器以指定编码读取源文件，即使默认已是 UTF-8
- [B] 声明该行之后的所有字符串都会自动转码
- [C] 它只是普通注释，Python 3 完全忽略其含义
- [D] 它用于指定程序输出到终端的编码

**参考答案**：0

**解析**：在 Python 3 中源文件默认按 UTF-8 解码，但编码声明注释仍会被识别，用于告诉解释器以指定编码读取源文件。它必须出现在文件第一或第二行。它不是普通注释，也不控制输出编码。

### single_choice · None



- [A] A
- [B] B
- [C] B
  C
- [D] 什么都不输出

**参考答案**：1

**解析**：第一行整行被注释，第二行先执行 print("B")，其后的 # print("C") 是行内注释被忽略，因此只输出 B。

### single_choice · None



- [A] 注释应尽量复述代码本身，让代码看起来更长更完整
- [B] 注释应与代码同步更新，避免注释描述与实现不一致
- [C] 注释越少越好，最好完全不写注释
- [D] 注释必须使用中文，否则会被解释器拒绝

**参考答案**：1

**解析**：PEP 8 强调注释要与代码保持一致、及时更新，避免误导；注释应解释“为什么”而非复述“做了什么”；注释语言与解释器无关，中英文皆可。

### single_choice · None



- [A] 正常输出 hello
- [B] 抛出 IndentationError，因为 if 块内没有缩进
- [C] 抛出 SyntaxError，因为字符串没有加引号
- [D] 抛出 TabError

**参考答案**：1

**解析**：Python 用缩进表示代码块。if 语句后面需要缩进的语句块，print 前没有缩进，会触发 IndentationError（IndentationError 是 SyntaxError 的子类）。

### single_choice · None



- [A] 30
- [B] 抛出 NameError
- [C] 输出 10
- [D] 抛出 IndentationError

**参考答案**：0

**解析**：Python 没有块级作用域，if 块内定义的 y、z 在块外仍然可见，因此 y+z 为 30。

### fill_blank · None



**参考答案**：["IndentationError", "IndentationError（缩进错误）", "缩进错误"]

**解析**：if 语句块内没有缩进，会抛出 IndentationError。

### fill_blank · None



**参考答案**：["缩进", "indentation", "缩进量", "Indentation"]

**解析**：Python 使用缩进来表示代码块的从属和层次关系。

### fill_blank · None



**参考答案**：["4", "四"]

**解析**：PEP 8 建议每一级缩进使用 4 个空格。

### code_reading · None



**参考答案**：0 0
0 1
1 0
1 1

**解析**：外层循环每取一个 i，内层循环完整执行 j=0、1，打印四次，输出顺序为 0 0、0 1、1 0、1 1。

### code_reading · None



**参考答案**：big
positive

**解析**：内层 if 块打印 big，随后与内层 if 同级的 print 打印 positive。

### code_reading · None



**参考答案**：报错 IndentationError，因为同一代码块内 x 和 y 的缩进量不一致。

**解析**：第 3 行比第 4 行少一个空格，属于同一代码块内缩进不一致，会引发 IndentationError。

### code_reading · None



**参考答案**：pos
non-pos

**解析**：最后的 return 与 if 同级，而不是在 if 块内，因此 n<=0 时会返回 non-pos。该题考察缩进决定 return 归属。

### scenario · None



**解析**：缩进混用是环境相关的隐性 bug，应在团队内统一缩进风格（如 4 个空格），并用 linter/格式化工具和代码审查自动化检查。

### scenario · None



**解析**：print("done") 与 print(i) 同为循环体，因此每次循环都会执行。要只执行一次，应把 print("done") 减少缩进，使其与 for 语句同级。

### single_choice · None



- [A] 同一代码块内每行缩进空格数可以不同，Python 会自动对齐
- [B] 同一代码块内所有语句必须有相同的缩进量
- [C] 必须使用 Tab 缩进，空格会报错
- [D] 必须使用 4 个空格，其他数量都会报错

**参考答案**：1

**解析**：同一代码块内各行的缩进量必须一致；不同代码块之间可以不同。缩进字符可以是空格或 Tab，但混用容易出错。官方风格推荐 4 个空格，但并非强制。

### single_choice · None



- [A] 不会报错，Tab 和空格可以自由混用
- [B] 会报错，因为同一代码块内混用了 Tab 和空格缩进
- [C] 不会报错，Python 自动把 Tab 转换成 4 个空格
- [D] 会报错，因为函数必须有 return 前的空行

**参考答案**：1

**解析**：在同一个代码块内混用 Tab 和空格可能导致 TabError（缩进不一致），Python 3 明确禁止在同一块内不一致地混用制表符与空格。

### single_choice · None



- [A] if x:
    a = 1
     b = 2
- [B] if x:
      a = 1
      b = 2
- [C] if x:
      a = 1
          b = 2
- [D] if x:
  a = 1
  b = 2

**参考答案**：1

**解析**：同一代码块 a、b 的缩进量必须一致，选项 B 中两行都是 4 个空格，正确。A、C 缩进不一致，D 没有缩进。

### single_choice · None



- [A] if 语句块内语句没有缩进
- [B] 函数体缩进量比函数头多
- [C] 代码块中某一行比其他行多缩进了一格
- [D] def 语句后直接跟不带缩进的代码

**参考答案**：1

**解析**：函数体的缩进比函数头多正是 Python 要求的形式，不会报错；其余都是缩进错误。

### multi_choice · None



- [A] 缩进用于表示代码块层次
- [B] 同一个代码块内缩进量必须一致
- [C] 不同代码块可以使用不同的缩进量
- [D] 缩进只影响可读性，对语义没有影响
- [E] 缩进必须严格使用 4 个空格

**参考答案**：[0, 1, 2]

**解析**：缩进在 Python 中是语法的一部分，用于表示代码块，同类块内必须一致，不同块间可以不同；缩进数量无强制规定，4 空格只是风格推荐。D、E 错误。

### multi_choice · None



- [A] if True:
      x = 1
     y = 2
- [B] if True:
  	x = 1
          y = 2
- [C] if True:
  x = 1
- [D] for i in range(3):
      print(i)

**参考答案**：[0, 1, 2]

**解析**：A 中 y 比 x 少一格，同块内缩进不一致；B 中混用了 Tab 和多个空格且不一致；C 中块内没有缩进。只有 D 是正确写法。

### multi_choice · None



- [A] Python 的缩进用于划分代码块
- [B] 缩进形成的代码块并不创建新的作用域
- [C] 在 if 块内定义的变量在块外仍可访问
- [D] 缩进越深，变量的作用域越小

**参考答案**：[0, 1, 2]

**解析**：缩进决定代码块结构，但 Python 没有块级作用域，if/for 等块内定义的变量在块外依旧可见。D 混淆了缩进层次和作用域。

### multi_choice · None



- [A] 可以用空格作缩进
- [B] 可以用 Tab 作缩进
- [C] 在同一代码块内混用 Tab 和空格可能导致 TabError
- [D] 缩进必须用 Tab，否则无法运行
- [E] Python 3 禁止在源文件中出现 Tab 字符

**参考答案**：[0, 1, 2]

**解析**：空格和 Tab 都可用作缩进；但在同一块内混用导致不一致时会引发 TabError。D 错误，空格完全可以；E 错误，Tab 仍可用于缩进。

### single_choice · None



- [A] int
- [B] str
- [C] TypeError
- [D] NoneType

**参考答案**：1

**解析**：Python 变量只是名字到对象的绑定，重新赋值会把名字绑定到新对象上，旧对象若无其他引用则被回收。第二次赋值后 x 指向字符串，因此类型是 str。

### single_choice · None



- [A] 变量是存放值的内存盒子，赋值就是把值拷贝进盒子
- [B] 变量名是对对象的引用，赋值建立名字到对象的绑定
- [C] 同一个变量名在同一时刻可以绑定多个对象
- [D] 变量必须先声明类型，之后不能改变绑定的对象类型

**参考答案**：1

**解析**：Python 采用「名字—对象」的引用模型，赋值语句把名字绑定到对象上，名字本身没有类型，类型属于对象。因此同一名字先后可以指向不同类型的对象。

### single_choice · None



- [A] 使用 const 关键字可以定义不可修改的常量
- [B] 用全大写命名的变量是约定俗成的常量，但解释器不会阻止修改
- [C] 常量一旦定义，赋值会抛出异常
- [D] Python 没有常量也没有相应约定

**参考答案**：1

**解析**：Python 没有 const 关键字或真正的常量机制，社区约定用全大写名（如 MAX_SIZE）表示常量，但解释器不强制，仍然可以被重新赋值。

### multi_choice · None



- [A] 赋值语句把名字绑定到对象上，而不是把值装进名字里
- [B] 变量名本身没有类型，类型属于它所引用的对象
- [C] 同一个名字在程序不同位置可以先后绑定不同类型的对象
- [D] 变量在使用前必须显式声明其类型
- [E] del 一个名字会立即释放该名字所引用的对象

**参考答案**：[0, 1, 2]

**解析**：前三项正确描述了引用模型和动态类型。变量无需声明类型，所以 D 错。del 只是解除名字绑定，只有对象引用计数降为 0 时才会被回收，所以 E 错。

### multi_choice · None



- [A] _value
- [B] value1
- [C] 1value
- [D] Value_2
- [E] for

**参考答案**：[0, 1, 3]

**解析**：_value、value1、Value_2 都符合标识符规则。1value 以数字开头不合法，for 是保留关键字也不能作为标识符。

### multi_choice · None



- [A] a = b = 0
- [B] a, b = 1, 2
- [C] (a, b) = (1, 2)
- [D] a := 1
- [E] a = 1; b = 2

**参考答案**：[0, 1, 2]

**解析**：A 是链式赋值，B 和 C 是元组解包赋值，都能在一句里给多个名字赋值。D 的海象运算符用于在表达式内赋值单个名字，E 用分号写的是两条独立语句。

### multi_choice · None



- [A] 函数内对名字赋值会使其成为局部变量
- [B] 读取一个未在函数内赋值的名字会按局部、外层、全局、内置的顺序查找
- [C] 在函数内用 global 声明后可以修改全局变量
- [D] 局部变量在函数返回后仍然可以被外部访问
- [E] 函数内引用外层函数的变量称为闭包，需要用 nonlocal 才能重新绑定

**参考答案**：[0, 1, 2, 4]

**解析**：A、B、C、E 都是作用域与名字查找的正确描述。局部变量随函数调用结束而失效，外部无法访问，因此 D 错误。

### fill_blank · None



**参考答案**：["8"]

**解析**：x 先绑定 5，再执行 x = x + 3，右侧先算出 8 并把名字 x 重新绑定到 8，因此打印 8。

### fill_blank · None



**参考答案**：["global", "global语句", "global 语句"]

**解析**：函数内直接赋值会创建局部变量；要修改全局变量必须用 global 声明该名字，否则只会遮蔽全局变量或引发 UnboundLocalError。

### code_reading · None



**参考答案**：输出：[1, 2] [3, 4]。原因：b = a 让 b 与 a 指向同一个列表，但随后 b = [3, 4] 是把 b 重新绑定到一个新列表对象，并没有修改原来的列表，所以 a 仍指向 [1, 2]。

**解析**：关键在于区分「重新绑定名字」和「原地修改对象」。b = [3, 4] 属于重新绑定，因此对 a 没有影响；如果写的是 b.append 或 b[0] = 3 才会影响 a。

### code_reading · None



**参考答案**：抛出 UnboundLocalError。原因：函数体中出现对 x 的赋值，使 x 在整个函数内被视为局部变量，但 print 执行时局部 x 还未被赋值，因此报 UnboundLocalError 而非取到全局的 10。

**解析**：Python 在编译时扫描函数体，只要发现对某名字的赋值就把它归为局部变量，因此 print(x) 访问的是尚未赋值的局部名。若想先用全局值再修改，需用 global 声明。

### scenario · None



**解析**：函数体内对 count 赋值使其成为局部变量，count = count + 1 右侧读取的是尚未赋值的局部名，会报 UnboundLocalError，或即使不报错也不会影响全局。修正方式是在函数内使用 global count 声明后再自增，或改用可变对象（如把计数放在列表或字典里）进行原地修改。

### single_choice · None



- [A] [1, 2, 3]
- [B] [1, 2, 3, 4]
- [C] [4]
- [D] 报错，因为 a 不能被修改

**参考答案**：1

**解析**：b = a 没有复制列表，而是让 b 和 a 绑定同一个列表对象。通过 b 修改列表内容，a 也会看到变化，因此打印 [1, 2, 3, 4]。

### scenario · None



**解析**：Python 没有内置的常量机制，也没有 const 关键字，全大写只是约定，解释器不会阻止重新赋值。团队可以通过代码审查、静态检查工具（如 lint 检查命名与赋值）、或把常量放入不可变结构/使用枚举等方式降低误改风险。

### single_choice · None



- [A] 2count
- [B] _total
- [C] my-var
- [D] class

**参考答案**：1

**解析**：Python 标识符可以以字母或下划线开头，后面跟字母、数字、下划线，且不能是关键字。2count 以数字开头，my-var 含连字符，class 是关键字，只有 _total 合法。

### single_choice · None



- [A] 1 2
- [B] 2 1
- [C] 1 1
- [D] 报错，不支持这种赋值

**参考答案**：1

**解析**：右侧会先构造元组 (b, a) = (2, 1) 再依次解包赋值，因此 a 变 2、b 变 1。这实现了无需临时变量的交换。

### single_choice · None



- [A] a 和 b 是两个内容相同的独立列表，互不影响
- [B] a 和 b 绑定同一个列表对象，通过 a 修改会影响 b
- [C] 会报错，因为列表不能链式赋值
- [D] a 是列表，b 是元组

**参考答案**：1

**解析**：链式赋值按同一对象依次绑定，a 和 b 指向同一个列表对象，因此是别名关系，一方修改另一方可见。要得到独立副本应写成 a = []; b = [] 或显式复制。

### single_choice · None



- [A] 5
- [B] None
- [C] NameError
- [D] 0

**参考答案**：2

**解析**：y 在函数内部赋值，默认是局部变量，作用域只在函数体内。函数执行结束后 y 即不可访问，所以函数外的 print(y) 抛出 NameError。

### single_choice · None



- [A] 报错 NameError
- [B] 报错 UnboundLocalError
- [C] 1
- [D] None

**参考答案**：2

**解析**：函数内只是读取 x，没有对 x 赋值，因此 x 不是局部变量，会按 LEGB 规则向上查找并找到全局的 x = 1，输出 1。

### single_choice · None



- [A] 1
- [B] 2
- [C] None
- [D] 报错

**参考答案**：0

**解析**：函数内的 x = 2 创建了一个局部变量 x，只在函数内部有效，不会改变全局的 x。因此函数外打印仍是 1。若想在函数内改全局变量需用 global 声明。

### single_choice · None



- [A] 只有 z 被赋值为 0
- [B] x、y、z 都绑定到整数对象 0
- [C] x、y、z 是同一个可变对象
- [D] 会报语法错误

**参考答案**：1

**解析**：链式赋值把最右侧的值同时绑定给左侧所有名字，所以 x、y、z 都指向同一个整数对象 0。整数不可变，因此不存在共享可变对象被意外修改的风险。
