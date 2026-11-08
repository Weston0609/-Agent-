# s1u1l3 Python 的输入（input）：从键盘读取数据的第一步 / `py.io.print_format`：把数据“好看地”送进输出流 / Python f-string：让字符串拼接变得又快又优雅

> 来源 `content/lessons/s1u1l3.json`

## py.io.input

# Python 的输入（input）：从键盘读取数据的第一步

## 一句话直觉

程序需要从外部拿数据才能“活”起来，而最简单的入口就是**让用户用键盘输入**——`input()` 就是 Python 给我们的那个“耳朵”。

---

## 1. 什么是输入（Input）？

**输入（input）** 指的是程序从外部世界获取数据的过程。外部世界可以是：

- 键盘（最常用，也是本篇重点）
- 文件
- 网络
- 另一个程序

在 Python 中，从键盘读取一行文本最简单的方式就是调用内置函数 `input()`。

它的核心行为只有两点：

1. **暂停程序运行**，等待用户在终端敲入内容并按下回车。
2. **返回一个字符串**（str），内容是用户敲入的那一行（不包含结尾的换行符）。

```python
# 最简单的输入示例：等待用户输入，然后把内容原样打印出来
name = input("请输入你的名字：")  # 括号里的字符串是提示信息（prompt），会显示在终端上
print("你好，" + name + "！")     # name 一定是一个 str 类型
```

运行效果（终端中）：

```text
请输入你的名字：小明
你好，小明！
```

> 关键结论：**无论用户输入什么，`input()` 返回的永远是字符串。**

---

## 2. 为什么 `input()` 返回的总是字符串？

因为键盘敲进来的本来就是**字符序列**，Python 不做任何“猜测”。即使你输入 `123`，它也只是三个字符 `'1'`、`'2'`、`'3'` 组成的字符串 `"123"`，而不是整数 `123`。

如果你需要数字，必须自己做**类型转换（type conversion / casting）**：

```python
# 想要整数？用 int() 转换
age_text = input("请输入你的年龄：")  # 例如用户输入 18
age = int(age_text)                  # 把字符串 "18" 转成整数 18
print("明年你", age + 1, "岁")        # 现在可以做数学运算
```

如果用户输入的不是数字（比如 `abc`），`int()` 会抛出 `ValueError`。所以真实程序里通常要配合异常处理：

```python
# 更健壮的写法：用 try/except 处理非法输入
try:
    age = int(input("请输入你的年龄："))
    print("明年你", age + 1, "岁")
except ValueError:
    print("你输入的不是一个整数，请重新运行程序。")
```

这是工程中非常常见的模式：**输入 → 校验 → 转换 → 使用**。

---

## 3. `input()` 与其他输入源的对比

`input()` 只是 Python 输入体系的“入门款”。理解它在整个体系中的位置，有助于你后面学文件、网络、异步 IO。

| 输入源 | 典型方式 | 返回类型 | 是否需要等待 |
| --- | --- | --- | --- |
| 键盘 | `input()` | `str` | 是（阻塞） |
| 文件 | `open().read()` | `str` 或 `bytes` | 是 |
| 命令行参数 | `sys.argv` | `list[str]` | 否 |
| 标准输入流 | `sys.stdin.readline()` | `str` | 是 |

从类型系统的角度看，Python 标准库用 `typing.IO`、`typing.TextIO`、`typing.BinaryIO` 来描述“输入输出流”的类型；而 `io.Reader` 这类**协议（Protocol）** 则只要求实现一个 `read()` 方法，适合写更通用的函数签名：

```python
from typing import Iterable

# 接收任何“可迭代的字符串流”（文件、sys.stdin、字符串列表都可以）
def read_config(stream: Iterable[str]) -> None:
    for line in stream:
        print(line.rstrip())

read_config(["host=localhost", "port=8080"])
```

对于初学者，你只需要记住：**`input()` 是文本输入流的一种便捷封装**，底层同样是在读“流”。

---

## 4. 常见的输入处理模式

实际工程里，`input()` 通常被包在各种模式中。掌握下面三种，就覆盖了绝大部分日常场景。

### 4.1 读取一行并转换

```python
# 读取一个整数
n = int(input("请输入一个整数："))
print("它的平方是", n * n)
```

### 4.2 读取一行中的多个值（用 split 切分）

```python
# 输入形如 "3 5"，得到两个整数
a, b = input("请输入两个整数，用空格分隔：").split()
a, b = int(a), int(b)
print("它们的和是", a + b)
```

### 4.3 循环读取直到结束

```python
# 持续读取，直到用户输入空行
lines = []
while True:
    line = input("输入内容（直接回车结束）：")
    if line == "":
        break
    lines.append(line)
print("你一共输入了", len(lines), "行")
```

---

## 5. 工程级视角：输入为什么容易出错？

因为输入来自**不受你控制的外部世界**。用户可能：

- 输入空字符串
- 输入中文、emoji、控制字符
- 输入超长文本
- 直接关闭终端（触发 `EOFError`）

因此工程代码中，输入处理通常要遵循三条原则：

1. **永远先当作字符串处理，再做转换。**
2. **转换必须捕获异常（`ValueError`、`EOFError`）。**
3. **对输入长度、取值范围做校验，而不是直接信任。**

```python
# 一个简单的工程级输入函数：循环直到拿到合法整数
def read_int(prompt: str) -> int:
    while True:
        try:
            return int(input(prompt))
        except ValueError:
            print("输入无效，请输入一个整数。")
        except EOFError:
            print("\n检测到输入结束，程序退出。")
            raise SystemExit(1)

n = read_int("请输入一个整数：")
print("你输入的是", n)
```

这就是从“会用 `input()`”到“工程级输入处理”的差距：**健壮性来自对异常和边界的处理，而不是来自函数本身。**

---

## 动手练习

**任务：写一个“简易成绩统计器”**

要求：

1. 用 `input()` 提示用户输入若干学生的成绩，每行一个。
2. 输入空行表示结束。
3. 把每一行转换成 `float`，如果某行不是合法数字，打印提示并跳过这一行。
4. 最后输出：
   - 有效成绩的个数
   - 平均分（保留两位小数）
   - 最高分和最低分
5. 如果一条有效成绩都没有，输出“没有有效成绩”。

示例运行：

```text
请输入成绩（直接回车结束）：90
请输入成绩（直接回车结束）：85.5
请输入成绩（直接回车结束）：abc
输入无效，已跳过：abc
请输入成绩（直接回车结束）：
有效成绩个数：2
平均分：87.75
最高分：90.0
最低分：85.5
```

提示：数字格式可以用 `f"{value:.2f}"` 保留两位小数。

## py.io.print_format

# `py.io.print_format`：把数据“好看地”送进输出流

## 一句话直觉

你写程序，最终总要**把结果给别人看**——可能是终端里的一行日志、文件里的一张表格、网页上的一段 JSON。`print` 和**格式化**（formatting，即把数据按指定样式转成字符串）就是 Python 与外界对话的“嘴”。学不好它，数据再对，输出也一塌糊涂；学好了它，调试、日志、报告都事半功倍。

> 本讲知识点 ID 为 `py.io.print_format`，属于 s1u1l3。前置知识为无，因此从最基础的 `print` 讲起，逐步过渡到工程级格式化方案。

---

## 1. `print` 的本质：它只是往标准输出写字符串

`print` 的签名大致是：

```python
print(*objects, sep=' ', end='\n', file=sys.stdout, flush=False)
```

关键理解三点：

- 它把每个对象用 `str()` 转成字符串；
- 用 `sep` 连接，末尾加 `end`；
- 写到 `file` 指定的**流**（stream，即可写入的对象，如 `sys.stdout`、文件对象）。

```python
# 基础 print 行为
print("a", "b", "c")                 # a b c
print("a", "b", "c", sep="-")         # a-b-c
print("no newline", end="")           # 不换行
print(" -> continue")                 # no newline -> continue
```

结论：`print` 不是“打印机”，而是“往流里写字符串”的快捷方式。

---

## 2. 三种格式化方式：`%`、`str.format`、f-string

Python 历史上有三代格式化方案，今天都还会见到。

### 2.1 `%` 风格（最古老，仍常见于日志）

```python
name = "Alice"
age = 30
# %s 表示按 str 插入，%d 表示按整数插入
print("Name: %s, Age: %d" % (name, age))
```

### 2.2 `str.format`（Python 2.6+，灵活）

```python
# {} 占位，按位置或按名字填入
print("Name: {}, Age: {}".format(name, age))
print("Name: {n}, Age: {a}".format(n=name, a=age))
```

### 2.3 f-string（Python 3.6+，推荐）

```python
# 在字符串前加 f，{} 内可直接写表达式
print(f"Name: {name}, Age: {age}")
print(f"Next year: {age + 1}")  # 可内嵌表达式
```

工程建议：**新代码优先 f-string**，可读性最好、性能也最好。

---

## 3. 格式规格（format spec）：控制宽度、精度、对齐、类型

格式化的核心威力在“**格式规格**”（format spec），写在 `:` 后面。

```python
pi = 3.14159265
print(f"{pi:.2f}")        # 保留 2 位小数：3.14
print(f"{pi:10.3f}")      # 总宽 10，右对齐，保留 3 位：     3.142
print(f"{pi:<10.3f}|")    # 左对齐
print(f"{pi:^10.3f}|")    # 居中
print(f"{42:05d}")        # 补零到 5 位：00042
print(f"{255:x}")         # 十六进制：ff
print(f"{255:b}")         # 二进制：11111111
print(f"{0.25:.1%}")      # 百分比：25.0%
```

记忆口诀：`[[填充]对齐][符号][#][0][宽度][,][.精度][类型]`。

---

## 4. 写文件与重定向：`print(file=...)` 与 `open`

`print` 可以写到任何“文件样对象”（file-like object）。

```python
with open("out.txt", "w", encoding="utf-8") as f:
    print("Hello, file", file=f)
    print("second line", file=f)

# 标准错误（stderr）常用于日志
import sys
print("warning!", file=sys.stderr)
```

注意：`open` 时显式写 `encoding="utf-8"` 是工程习惯，避免跨平台乱码。

---

## 5. 工程级：`logging` 与格式化的分工

真正上生产时，**不要用 `print` 打日志**。用 `logging`：

```python
import logging
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
logging.info("user %s logged in", "alice")  # 推荐：延迟格式化
```

要点：

- `logging` 的 `"%s" % arg` 风格是**延迟格式化**（lazy formatting），只有日志真的被输出时才拼接，性能友好。
- 输出目标（终端/文件/网络）由 **handler** 决定，格式化只负责“长什么样”。
- 这与 `print` 的格式化是同一套底层逻辑：把对象转文本，但分发与级别管理更专业。

---

## 6. 对象如何被格式化：`__str__` 与 `__format__`

当 f-string 里写 `{obj}` 时，Python 调用对象的 `__format__` 方法；若没自定义，则回退到 `str(obj)`（即 `__str__`）。默认情况下 `object.__format__` 只接受空 spec。

```python
class Money:
    def __init__(self, amount):
        self.amount = amount
    def __format__(self, spec):
        # 支持 {m:.2f} 这样的规格
        return format(self.amount, spec) if spec else str(self.amount)

m = Money(3.14159)
print(f"{m:.2f}")  # 3.14
```

这解释了一个常见现象：**自定义类如果没实现 `__format__`，`f"{obj:>10}"` 可能会报错**。

---

## 小结

| 层次 | 工具 | 用途 |
|---|---|---|
| 基础 | `print` | 快速输出到终端 |
| 格式化 | f-string / `format` / `%` | 控制文本长相 |
| IO | `print(file=...)`、`open` | 写到文件/流 |
| 工程 | `logging` | 分级、分发、延迟格式化 |
| 扩展 | `__format__` / `__str__` | 自定义对象如何被格式化 |

掌握这五步，你就从“能打印”走到了“会输出”。

```python
# py.io.print_format 综合示例
import sys
import logging

# 1) print 的基本参数
print("A", "B", "C", sep="|", end="  <-- end\n")

# 2) 三种格式化方式对比
name, score = "Alice", 93.45678
print("%%  : Name: %s, Score: %.2f" % (name, score))
print("fmt: Name: {}, Score: {:.2f}".format(name, score))
print(f"fstr: Name: {name}, Score: {score:.2f}")

# 3) 格式规格：宽度、对齐、进制、百分比
print(f"|{name:>10}|{score:<8.3f}|")
print(f"hex={255:#x}, bin={255:b}, pct={0.256:.1%}")

# 4) 写文件 + 标准错误
with open("demo_out.txt", "w", encoding="utf-8") as f:
    print("written to file", file=f)
print("this goes to stderr", file=sys.stderr)

# 5) logging 的延迟格式化
logging.basicConfig(level=logging.INFO,
                    format="%(levelname)s:%(message)s")
logging.info("user %s scored %.2f", name, score)

# 6) 自定义 __format__
class Money:
    def __init__(self, amount):
        self.amount = amount
    def __format__(self, spec):
        return format(self.amount, spec) if spec else str(self.amount)

m = Money(3.14159)
print(f"Money: {m:.2f}")
```

## py.io.fstring

# Python f-string：让字符串拼接变得又快又优雅

## 一句话直觉

`f-string`（formatted string literal，格式化字符串字面量）让你把变量、表达式直接"嵌"进字符串里，写起来像填表格，读起来像自然语言。

---

## 1. 为什么需要 f-string？

在 Python 里，把变量的值放进字符串是一件非常常见的事。早期的写法是：

```python
name = "Alice"
age = 30
text = "My name is " + name + " and I am " + str(age) + " years old."
print(text)
```

问题很明显：需要手动转换类型（`str(age)`）、需要拼接大量 `+` 号、引号容易数错。

Python 3.6 引入了 **f-string**，把这件事变成：

```python
name = "Alice"
age = 30
text = f"My name is {name} and I am {age} years old."
print(text)
```

**核心结论**：在字符串前面加一个字母 `f`，字符串里的 `{}` 就会被当作 Python 表达式求值后插入。

---

## 2. 基本语法：`{}` 里可以放什么？

`{}` 里可以放任何合法的 Python 表达式，不限于变量名。

```python
x = 6
print(f"{x} 的平方是 {x ** 2}")          # 6 的平方是 36
print(f"1 + 2 = {1 + 2}")                  # 1 + 2 = 3
print(f"当前时间戳：{__import__('time').time():.2f}")
```

**核心结论**：`{}` 内是"表达式"而不是"变量名"，可以做运算、调用函数、访问属性。

---

## 3. 格式化：冒号后面的"小语言"

`{}` 里除了表达式，还可以用 `:` 指定**格式规格**（format spec），控制数字、对齐、精度等。

```python
pi = 3.1415926
print(f"{pi:.2f}")        # 保留两位小数：3.14
print(f"{pi:10.3f}")      # 宽度 10，右对齐，3 位小数：     3.142
print(f"{pi:<10.3f}END")  # 左对齐
print(f"{pi:^10.3f}END")  # 居中对齐

percent = 0.856
print(f"{percent:.1%}")    # 百分比：85.6%

num = 255
print(f"{num:#x}")        # 十六进制带前缀：0xff
print(f"{num:08b}")       # 二进制补零：11111111
```

**核心结论**：`{表达式:格式}` 是 f-string 最强大的部分，能直接完成过去 `format()` 才能做的事。

---

## 4. 进阶：自记录表达式与嵌套

Python 3.8 起，`f"{x=}"` 会打印 `x=值` 的调试形式；f-string 还支持嵌套表达式。

```python
user = "Bob"
score = 95.6789

# 自记录表达式（self-documenting expression）
print(f"{user=}, {score=:.2f}")
# 输出：user='Bob', score=95.68

# 嵌套：用变量控制宽度
width = 12
print(f"{user:>{width}}")   # 右对齐到 12 宽

# 多行 f-string
name = "Carol"
msg = (
    f"Hello, {name}!\n"
    f"Welcome to the f-string tutorial."
)
print(msg)
```

**核心结论**：`=` 后缀是调试利器，嵌套让格式规格也能动态化。

---

## 5. 性能与可读性：为什么工程里首选 f-string

f-string 在编译期就被优化为字节码拼接，通常比 `%`、`str.format()`、甚至 `+` 拼接更快。同时写法更短，减少了"模板与参数分离"导致的错位 bug。

```python
import timeit

value = 42

fstr = timeit.timeit(
    lambda: f"value is {value}", number=100_000
)
format_str = timeit.timeit(
    lambda: "value is {}".format(value), number=100_000
)
percent = timeit.timeit(
    lambda: "value is %d" % value, number=100_000
)

print(f"f-string:  {fstr:.4f}s")
print(f"format():  {format_str:.4f}s")
print(f"% 运算符:  {percent:.4f}s")
```

**核心结论**：在同样可读的情况下，f-string 通常是最快、最简洁的选择。

---

## 动手练习

**任务**：编写一个 `receipt.py`，使用 f-string 打印一张小票。要求：

1. 定义 3 个商品：名称、单价、数量。
2. 用 f-string 输出表格格式：商品名左对齐宽度 10，单价右对齐宽度 8 保留两位小数，数量居中宽度 5，小计右对齐宽度 10 保留两位小数。
3. 最后输出总价，保留两位小数，前面带 `¥`。
4. 附加：用 `{变量=}` 调试输出原始数据一次。

**参考输入数据**：

```python
items = [
    ("apple", 3.5, 2),
    ("banana", 1.2, 5),
    ("coffee", 18.0, 1),
]
```

**期望输出示意**：

```
apple        3.50  2     7.00
banana       1.20  5     6.00
coffee      18.00  1    18.00
----------------------------
TOTAL: ¥31.00
```

完成后可以尝试：用同一个 f-string 表达式，把单价改成 `:.2%`，看看输出如何变化。

```python
# -*- coding: utf-8 -*-
"""
f-string 综合示例：小票打印
运行：python receipt.py
"""

items = [
    ("apple", 3.5, 2),
    ("banana", 1.2, 5),
    ("coffee", 18.0, 1),
]

total = 0.0
print(f"{'Item':<10}{'Price':>8}{'Qty':^5}{'Subtotal':>10}")
print("-" * 28)

for name, price, qty in items:
    subtotal = price * qty
    total += subtotal
    # 左对齐/右对齐/居中，浮点保留两位小数
    print(f"{name:<10}{price:>8.2f}{qty:^5d}{subtotal:>10.2f}")

print("-" * 28)
print(f"TOTAL: ¥{total:.2f}")

# 自记录表达式，方便调试
first_name = items[0][0]
print(f"{first_name=} {total=:.2f}")
```


---

## 本课题目

### single_choice · None



- [A] int
- [B] str
- [C] 由输入内容自动推断的类型
- [D] bytes

**参考答案**：1

**解析**：input() 无论用户输入数字还是文字，都返回字符串 str。若要得到数字需自行用 int()/float() 转换，Python 不会自动推断类型。

### single_choice · None



- [A] 整数 42
- [B] 字符串 "42"
- [C] 浮点数 42.0
- [D] 报错 TypeError

**参考答案**：1

**解析**：input() 返回字符串，因此 x 是字符串 "42"，而不是数字。常见误解是以为它会根据内容自动转成 int。

### multi_choice · None



- [A] 它返回的总是字符串
- [B] 可以传入一个提示字符串作为参数
- [C] 它会自动把输入内容转换成数字或列表
- [D] 到达输入流末尾时会抛 EOFError
- [E] 它返回的字符串包含行尾换行符

**参考答案**：[0, 1, 3]

**解析**：input() 返回 str、支持提示参数、EOF 时抛 EOFError 均正确。它不会自动转换类型（需手动 int()/split()），也不包含行尾换行符。

### multi_choice · None



- [A] int(input())
- [B] input().split()
- [C] list(map(int, input().split()))
- [D] input().to_integer()
- [E] float(input())

**参考答案**：[0, 1, 2, 4]

**解析**：int/float 转换、split 切分、map 批量转 int 都是真实存在的方式。input() 没有 to_integer() 方法，属于臆造 API。

### multi_choice · None



- [A] 输入内容默认是字符串，参与数值运算前常常需要转换
- [B] 数据被重定向读完后继续读取会抛 EOFError
- [C] 每调用一次 input() 通常消耗一整行输入
- [D] input() 会自动跳过空行读取下一非空行
- [E] 输入可能包含多余空白，切分时可依赖不带参数的 split()

**参考答案**：[0, 1, 2, 4]

**解析**：input() 不会自动跳过空行，空行会返回空字符串，因此选项 D 错误。其余都符合 input() 的读取与转换行为。

### multi_choice · None



- [A] nums = list(map(int, input().split()))
- [B] nums = [int(x) for x in input().split()]
- [C] nums = int(input().split())
- [D] nums = input().split() 并通过 int() 逐个转换后再收集

**参考答案**：[0, 1, 3]

**解析**：选项 A、B 是直接得到整数列表的常见写法；选项 D 先切分再逐个转换也正确；选项 C 把列表直接传给 int() 会报 TypeError。

### fill_blank · None



**参考答案**：["int", "int "]

**解析**：input() 返回字符串，转整数需用内置类型 int()。float() 得到浮点数，不符合本题要求的整数。

### fill_blank · None



**参考答案**：["split", "split ", "split()"]

**解析**：str.split() 不带参数时按任意空白切分，是读取一行多值的标准做法。

### fill_blank · None



**参考答案**：["input", "input "]

**解析**：input() 是读取一行标准输入的机制。注意不要与 sys.stdin.readline() 混淆，后者保留行尾换行符。

### code_reading · None



**参考答案**：7

**解析**：input() 得到字符串 "3 4"，split() 切成 ["3", "4"]，map(int, ...) 转成 3 和 4，解包给 a、b，相加得 7 并打印。若忘记 int 转换会变成字符串拼接得到 "34"。

### code_reading · None



**参考答案**：55

**解析**：input() 返回字符串 "5"，字符串与整数相乘表示重复拼接，因此得到 "55" 而不是 10。要得到 10 需先写 int(input())。

### scenario · None



**解析**：到达输入流末尾时 input() 抛 EOFError，工程上通常用 try/except EOFError 捕获，在 except 分支中打印提示并退出（如 break、return 或 sys.exit()），避免程序因未处理异常直接崩溃。

### single_choice · None



- [A] [1, 2, 3]
- [B] ["1", "2", "3"]
- [C] "123"
- [D] 报错，因为 split() 不作用于字符串

**参考答案**：0

**解析**：input() 得到 "1 2 3"，split() 按空白切分成字符串列表，再用 int 逐个转换得到整数列表 [1, 2, 3]。

### single_choice · None



- [A] 参数是必须提供的输入值
- [B] 参数是可选的提示字符串，会打印到标准输出且不带换行
- [C] 参数会被自动转换为数字
- [D] 参数会被当作分隔符切分输入

**参考答案**：1

**解析**：input(prompt) 中的 prompt 是可选提示串，会先写到标准输出（通常是屏幕）且不自动换行，然后等待用户输入。它只是提示，不参与解析。

### single_choice · None



- [A] 5
- [B] 11
- [C] 12
- [D] 报错

**参考答案**：1

**解析**："hello world" 长度为 11（含中间一个空格）。input() 不含行尾换行符，因此不是 12。提示串 '请输入: ' 不算入 s。

### single_choice · None



- [A] None
- [B] 空字符串 ""
- [C] 换行符 "
  "
- [D] 抛出 EOFError

**参考答案**：1

**解析**：回车表示输入了一个空行，input() 返回空字符串 ""，而不是 None，也不包含换行符。只有在输入流到达文件末尾时才会抛 EOFError。

### single_choice · None



- [A] a, b = input()
- [B] a = int(input()); b = int(input())
- [C] a, b = map(int, input().split())
- [D] a, b = input().split(int)

**参考答案**：2

**解析**：input().split() 得到两个字符串，再用 map(int, ...) 批量转换为整数并解包。选项 A 会按字符逐个解包字符串；选项 B 需要两行输入；选项 D 语法无效。

### single_choice · None



- [A] 用户输入空行时
- [B] 用户输入非数字字符时
- [C] 输入流已到达末尾（如重定向文件读完）时
- [D] 从标准输入读取时永远不会抛 EOFError

**参考答案**：2

**解析**：input() 在遇到文件末尾（EOF）而无更多数据可读时抛 EOFError。交互式终端下通常不出现，但管道、重定向或在线判题环境中很常见。

### single_choice · None



- [A] 返回的字符串会保留行尾的换行符
- [B] 返回的字符串会去掉行尾的换行符
- [C] 会读取多个以空格分隔的token并组成列表
- [D] 会自动去除首尾空格

**参考答案**：1

**解析**：input() 读取一行并去除行尾的换行符，但不会自动去除其它空白（首尾空格仍保留）。这与 sys.stdin.readline() 保留换行符不同。

### single_choice · None



- [A] a 的值为 0
- [B] a 的值为字符串 "abc"
- [C] 抛出 ValueError
- [D] 抛出 EOFError

**参考答案**：2

**解析**："abc" 不是合法整数表示，int() 转换失败会抛 ValueError。这是读取数字时常见的运行时错误，需要通过校验或异常处理避免。

### single_choice · None



- [A] a-b
- [B] a b
- [C] ab
- [D] a, b

**参考答案**：0

**解析**：print 的 sep 参数指定多个对象之间的分隔符，默认是空格，这里设为 '-'，所以输出 a-b。

### single_choice · None



- [A] hello world
- [B] helloworld
- [C] hello
  world
- [D] hello, world

**参考答案**：1

**解析**：end 参数指定 print 结束时的字符，默认是换行符。第一个 print 用 end='' 取消换行，因此两段输出连在一起为 helloworld。

### single_choice · None



- [A] Result: 3.14159
- [B] Result: {}
- [C] Result: 3.14
- [D] 报错：缺少格式说明

**参考答案**：0

**解析**：format 中的 {} 会按顺序替换为传入的参数，未指定格式说明符时使用默认的字符串表示，即 3.14159。

### single_choice · None



- [A] 12.34%
- [B] 0.12%
- [C] 12%
- [D] 1.23%

**参考答案**：0

**解析**：格式说明符 .2% 表示以百分数形式显示并保留两位小数：0.1234 → 12.34%。

### multi_choice · None



- [A] sep 用于指定多个输出对象之间的分隔符
- [B] end 用于指定输出结束时的字符，默认是换行
- [C] file 用于指定输出目标，默认是 sys.stdout
- [D] flush 用于强制刷新输出缓冲区
- [E] sep 和 end 必须同时指定

**参考答案**：[0, 1, 2, 3]

**解析**：sep、end、file、flush 都是 print 的合法关键字参数，各有明确含义；sep 和 end 都有默认值，无需同时指定，E 错误。

### multi_choice · None



- [A] f'{3.14159:.2f}'
- [B] '{:.2f}'.format(3.14159)
- [C] '%.2f' % 3.14159
- [D] str(round(3.14159, 2))
- [E] f'{3.14159:.3f}'

**参考答案**：[0, 1, 2]

**解析**：A、B、C 都能保留两位小数得到 '3.14'。D 中 round(3.14159, 2) 返回 3.14，但 str(3.14) 是 '3.14' 也正确——不过 round 可能引入二进制表示问题，某些数值下会不精确；在本题 3.14159 情形下 str(round(...)) 为 '3.14'，但作为格式化手段不如前三种可靠，标准答案是 A、B、C。E 保留三位小数得到 '3.142'。

### multi_choice · None



- [A] f-string 需要在字符串前加 f 或 F 前缀
- [B] f-string 的花括号内可以写表达式
- [C] f-string 中可以指定格式说明符，如 {x:.2f}
- [D] f-string 中的花括号需要用 {{ 和 }} 转义输出字面花括号
- [E] f-string 只能用于 print 函数

**参考答案**：[0, 1, 2, 3]

**解析**：A-D 都是 f-string 的正确特性。f-string 是通用的字符串字面量语法，可用于任何需要字符串的地方，不限于 print，故 E 错误。

### fill_blank · None



**参考答案**：["sep", "sep=", "sep ="]

**解析**：要让多个对象之间用 '|' 分隔，应使用 print 的 sep 参数，即 sep='|'。

### fill_blank · None



**参考答案**：[".2f", "0.2f", ".2F"]

**解析**：保留两位小数的定点格式说明符是 .2f，也可写作 .2F（输出大写不影响数字）。

### code_reading · None



**参考答案**：xy!z

**解析**：第一个 print 用 sep='' 拼接 'x' 和 'y' 得到 'xy'，再用 end='!' 使结尾为感叹号不换行；第二个 print 输出 'z' 后换行。整体显示为 xy!z。

### code_reading · None



**参考答案**：a
bc

**解析**：第一个 print 输出 'a' 并换行；第二个 print 输出 'b' 且 end='' 不换行；第三个 print 紧接着输出 'c' 再换行，因此第二行为 'bc'。

### scenario · None



**解析**：应使用 print 的 file 参数指定目标文件对象（需以写入模式打开，具有 write 方法），用 end='' 避免自动换行，用 flush=True 强制刷新缓冲区以便实时写入。file 参数接收的是文件类对象而不是路径字符串。

### single_choice · None



- [A] 1, 2, 3.
  （换行）
- [B] 1 2 3.
  （换行）
- [C] 1,2,3.（换行）
- [D] 1, 2, 3.（不换行）

**参考答案**：0

**解析**：sep=', ' 使各个对象之间用逗号加空格分隔，end='.\n' 使结束符为句点加换行，因此输出为 '1, 2, 3.' 后换行。

### scenario · None



**解析**：推荐使用 f-string。姓名用 {name:<10} 表示左对齐、宽度 10；分数用 {score:>8.2f} 表示右对齐、总宽度 8、保留两位小数。也可用 str.format 达到同样效果。<> 分别控制左右对齐方向，宽度数字控制占位，.2f 控制小数位数。

### single_choice · None



- [A] print(f'Pi is {3.14159:.2f}')
- [B] print('Pi is {3.14159:.2f}')
- [C] print(f'Pi is {3.14159:2f}')
- [D] print(f'Pi is {3.14159:.2}')

**参考答案**：0

**解析**：f-string 中使用 {value:.2f} 表示保留两位小数的定点格式。选项 B 缺少 f 前缀不会插值；C 的格式说明不完整；D 中 .2 对 float 不合法。

### single_choice · None



- [A] Hello, Tom!
- [B] Hello, %s!
- [C] Hello, name!
- [D] 报错：缺少参数

**参考答案**：0

**解析**：百分号格式化中 %s 会用后面的 name 值替换，得到 'Hello, Tom!'。

### single_choice · None



- [A] a-b-a
- [B] a-b-b
- [C] 0-1-0
- [D] 报错：索引超出范围

**参考答案**：0

**解析**：str.format 中 {0} 表示第一个位置参数，可以重复引用，因此 'a' 被使用两次，输出 a-b-a。

### single_choice · None



- [A] 0.3
- [B] 0.30000000000000004
- [C] 0.30
- [D] 0.3000000000000000

**参考答案**：1

**解析**：0.1 和 0.2 的二进制浮点表示存在误差，相加得到 0.30000000000000004。直接 print 会输出该完整结果，如需显示 0.3 应使用格式化。

### single_choice · None



- [A] abc
- [B] a bc
- [C] ab
  c
- [D] a, b, c

**参考答案**：0

**解析**：第一个 print 使用 sep='' 使 'a' 和 'b' 无分隔并拼接为 'ab'，end='' 使其不换行；第二个 print 输出 'c' 后换行。最终显示 abc（换行）。

### single_choice · None



- [A] sep 参数只在传入多个位置参数时起作用
- [B] sep 参数可以设置为 None
- [C] end 参数不能为空字符串
- [D] file 参数必须是字符串文件路径

**参考答案**：0

**解析**：sep 只在有多个要打印的对象时插入到它们之间；只打印一个对象时 sep 不产生可见影响。sep 不能为 None（否则 TypeError）；end 可以为空字符串；file 必须是具有 write 方法的文件类对象而非路径字符串。

### single_choice · None



- [A] 10
- [B] 00010
- [C] 10000
- [D] 10.000

**参考答案**：1

**解析**：{10:05d} 中的 0 表示用零填充，5 表示总宽度为 5，d 表示十进制整数，因此输出 00010。

### single_choice · None



- [A] f-string 是 Python 2.6 引入的字符串格式化方式
- [B] f-string 中的表达式在字符串创建时就会被求值
- [C] f-string 只能嵌入变量名，不能嵌入任意表达式
- [D] f-string 必须写成 f('...') 这种函数调用的形式

**参考答案**：1

**解析**：f-string 是 Python 3.6 引入的，且在字符串被创建时即对花括号内的表达式求值；它可以嵌入任意合法表达式，且书写形式是 f'...' 或 F'...'，不是函数调用。

### single_choice · None



- [A] Hello, {name}!
- [B] Hello, Ada!
- [C] Hello, name!
- [D] 报错：name 未定义

**参考答案**：1

**解析**：f-string 会把花括号中的 name 当作表达式求值，得到变量值 Ada，因此输出 Hello, Ada!。

### single_choice · None



- [A] f-string 会调用 repr 而不是 str
- [B] f-string 允许在占位符内写任意表达式，包括方法调用
- [C] f-string 中的表达式只能是数字
- [D] f-string 会在运行时重新解析字符串内容

**参考答案**：1

**解析**：f-string 的花括号内可以是任意合法表达式，包括属性访问、方法调用、函数调用等；它默认使用 str 转换；表达式在编译期被解析而非运行时重新解析。

### multi_choice · None



- [A] f-string 由 Python 3.6 引入
- [B] f-string 的花括号中可以调用函数
- [C] f-string 支持在冒号后指定格式说明符
- [D] f-string 中的表达式会在每次字符串被读取时重新求值
- [E] f-string 只能用于 print

**参考答案**：[0, 1, 2]

**解析**：f-string 3.6 引入、可嵌表达式（含函数调用）、支持格式说明符。表达式在字面量求值时一次性计算并固化，不会每次读取重新求值；f-string 是普通字符串字面量，可用于任何需要字符串的地方，不限于 print。

### multi_choice · None



- [A] f"{a + b}"
- [B] f"{name!r}"
- [C] f"{value:>10.3f}"
- [D] f"{a if a > b else b}"
- [E] f"{"

**参考答案**：[0, 1, 2, 3]

**解析**：f-string 支持表达式、!r 之类的转换符、格式说明符以及条件表达式。单个未配对的花括号会产生语法错误，必须写成 {{ 才能输出字面量大括号。

### multi_choice · None



- [A] 格式说明符写在冒号 : 之后
- [B] :>10 表示右对齐、总宽度至少 10
- [C] :.3f 表示保留三位小数的定点数
- [D] :, 表示使用千位分隔符
- [E] 格式说明符中不能引用变量

**参考答案**：[0, 1, 2, 3]

**解析**：格式说明符跟随冒号；> 对齐、数字为宽度；.3f 定点小数；逗号用于千位分隔。格式说明符中允许用嵌套花括号引用变量作为宽度/精度，所以「不能引用变量」错误。

### fill_blank · None



**参考答案**：[".2f", ":.2f", ".02f"]

**解析**：要在 f-string 中把整数输出为保留两位小数的定点数，应在冒号后使用 .2f。填写时冒号可能已给出，所以接受 .2f 等形式。

### fill_blank · None



**参考答案**：["!r", "！r"]

**解析**：!r 是转换符，表示对表达式结果调用 repr，因此字符串会带上引号输出。

### fill_blank · None



**参考答案**：["{{", "{{}}", "{{ }}"]

**解析**：f-string 中用两个连续大括号 {{ 表示一个字面量 {，}} 表示 }。只写一个 { 会被解析为表达式开始，导致语法错误。

### code_reading · None



**参考答案**：a at 0
b at 1

**解析**：每条 print 执行时，f-string 会立即对表达式求值。第一条 i 为 0，输出 a at 0；随后 i 变为 1，第二条输出 b at 1。说明求值发生在字面量被执行的时刻，而不是之后。

### code_reading · None



**参考答案**：0005

**解析**：f-string 在 s 被赋值时就完成了求值与格式化，结果 0005 已固化到字符串 s 中。之后修改 v 不会影响已生成的字符串，因此打印 0005 而非 0099。

### scenario · None



**解析**：f-string 中的 { } 具有特殊含义，会被当成表达式占位符。若用户文本中包含大括号，直接放入 f-string 会导致语法或逻辑问题。应当把用户数据作为变量传入占位符（例如 f"{user_input}"），而不是把用户内容直接作为 f-string 字面量的一部分；如确需在字面量中显示大括号，须写成 {{ 和 }}。也可以选择拼接或 format 来避免字面量大括号问题。

### single_choice · None



- [A] {x} + {y} = {x + y}
- [B] 3 + 4 = {x + y}
- [C] 3 + 4 = 7
- [D] 报错：f-string 中不能有算术运算

**参考答案**：2

**解析**：f-string 的花括号中可以嵌入任意表达式，包括算术运算，因此会先计算 x + y 得到 7，再拼接到字符串中。

### scenario · None



**解析**：他的理解不正确。f-string 是在该字面量被执行到时求值一次，结果即成为普通字符串，不会在后续被读取或使用时重新计算表达式。若循环体本身迭代多次，每次迭代都会重新执行该字面量，从而各自求值一次；但这不是「反复对同一字符串重算」。性能问题应关注循环内是否重复做了本可提出循环的无关计算。

### single_choice · None



- [A] f"{"
- [B] f"{{"
- [C] f"\{"
- [D] f"[["

**参考答案**：1

**解析**：f-string 中需要写两个连续的大括号 {{ 来表示一个字面量左大括号，}} 表示右大括号。反斜杠转义在 f-string 的表达式部分不受支持，单个 { 会被当作表达式开始。

### single_choice · None



- [A] 3.14159
- [B] 3.14
- [C] 3.1
- [D] 报错：.2f 不是合法格式说明符

**参考答案**：1

**解析**：冒号后的 .2f 是格式说明符，表示保留两位小数的定点表示，因此输出 3.14。

### single_choice · None



- [A] value =
- [B] value = 42
- [C] 42
- [D] 报错：= 不能出现在 f-string 中

**参考答案**：1

**解析**：Python 3.8 引入的调试语法在表达式后加 =，会同时输出表达式文本和其求值结果，因此输出 value = 42。注意等号与表达式之间、等号与结果之间的空格是默认行为。

### single_choice · None



- [A] |hi      |
- [B] |      hi|
- [C] |hi{width}|
- [D] 报错：width 不能嵌套在格式说明符中

**参考答案**：1

**解析**：格式说明符中可以用嵌套花括号引用变量作为宽度，> 表示右对齐，因此 hi 在宽度 8 的字段中右对齐，前面补 6 个空格。

### single_choice · None



- [A] v
- [B] k
- [C] 报错：f-string 中不能使用双引号索引
- [D] {'k': 'v'}

**参考答案**：0

**解析**：Python 3.12 起 f-string 支持在花括号表达式内使用与外部字符串相同类型的引号（PEP 701）。在更早版本中这段代码会因引号冲突而报语法错误。题目描述以 3.12 为环境，输出为 v。

### single_choice · None



- [A] 延迟求值，只有在字符串被打印时才计算
- [B] 在字符串字面量被求值时立即计算，结果被固化到字符串中
- [C] 每次访问该字符串对象都重新计算一次
- [D] 只对变量名求值，函数调用会抛出异常

**参考答案**：1

**解析**：f-string 在字面量被求值（即代码执行到该处）时立即计算花括号内表达式，结果直接拼接进生成的字符串对象，之后不再重新计算。

### single_choice · None



- [A] ff
- [B] FF
- [C] 0xff
- [D] 255

**参考答案**：0

**解析**：格式说明符 x 表示小写十六进制，X 表示大写，不带 # 时不加 0x 前缀，因此 255 输出 ff。
