# s1u3l1 Python 条件语句 `if`：从直觉到工程实践 / 条件分支：`if` / `elif` / `else`

> 来源 `content/lessons/s1u3l1.json`

## py.flow.if

# Python 条件语句 `if`：从直觉到工程实践

## 一句话直觉

**程序不是只会从上到下执行，`if` 让代码学会「看情况做决定」——这是所有逻辑分支的起点。**

---

## 1. 为什么需要 `if`：程序的「十字路口」

计算机默认按顺序执行代码。但现实中我们经常需要：**满足条件才做某事，否则做另一件事**。比如登录时检查密码、除零时避免崩溃。`if` 就是 Python 提供的最基础流程控制语句（flow control statement）。

```python
# 无 if 的世界：只能一条路走到黑
x = -5
# print(x ** 0.5)  # 这里会报错，因为没有判断

# 有 if 的世界：程序会「看情况」
import math
x = -5
if x >= 0:
    print(math.sqrt(x))
else:
    print("负数不能开平方")
```

**关键结论**：`if` 让程序具备「分支」能力，是后续 `for`、`while`、函数、异常处理的基础。

---

## 2. 基本语法：`if` / `elif` / `else`

Python 用**缩进（indentation）**表示代码块，而不是花括号。冒号 `:` 后换行缩进（通常 4 个空格）就是「条件成立时执行的代码」。

```python
score = 85

if score >= 90:
    grade = "A"
elif score >= 80:      # elif = else if，当前面条件不满足时继续判断
    grade = "B"
elif score >= 70:
    grade = "C"
else:                  # 所有条件都不满足时执行
    grade = "D"

print(grade)  # 输出 B
```

**关键结论**：
- `if` 可单独使用；`elif` 和 `else` 必须跟在 `if` 后面。
- 判断是**从上到下**的，一旦某个条件为真，后面的分支不再判断。

---

## 3. 真值判断：什么算「真」？

Python 中几乎所有对象都能被判断真假（truthiness）：

| 为假（False）的值 | 为真的值 |
|---|---|
| `False`、`0`、`0.0` | 非零数字 |
| `""`（空字符串） | 非空字符串 |
| `[]`、`()`、`{}`、`set()` | 非空容器 |
| `None` | 绝大多数对象 |

```python
name = ""
if name:                # 等价于 if len(name) > 0，但更 Pythonic
    print("你好，" + name)
else:
    print("名字不能为空")

items = [1, 2, 3]
if items:               # 推荐：直接判断序列真假
    print(f"有 {len(items)} 个元素")
```

**关键结论**（来自 PEP 8 风格指南）：
- 判断空序列用 `if not seq:` / `if seq:`，**不要**用 `if len(seq):`。
- 判断布尔值用 `if greeting:`，**不要**写 `if greeting == True:`，更不要写 `if greeting is True:`。

---

## 4. 条件表达式：三元运算符

当只想根据条件选一个值时，可以用**条件表达式（conditional expression）**一行写完：

```python
x = 10
label = "正数" if x > 0 else "非正数"
print(label)  # 正数

# 等价于：
if x > 0:
    label = "正数"
else:
    label = "非正数"
```

**关键结论**：条件表达式适合简单赋值，逻辑复杂时仍用 `if/else` 块更清晰。

---

## 5. 工程级建议：写出可维护的 `if`

### 5.1 避免用切片判断前缀/后缀

```python
foo = "bar_baz"

# 正确：用 startswith / endswith
if foo.startswith("bar"):
    print("以 bar 开头")

# 错误：切片容易出错且不清晰
if foo[:3] == "bar":
    print("以 bar 开头")
```

### 5.2 类型判断用 `isinstance()`

```python
obj = 42

# 正确
if isinstance(obj, int):
    print("是整数")

# 错误：不推荐直接比较 type
if type(obj) is type(1):
    print("是整数")
```

### 5.3 函数中提前返回，减少嵌套

```python
import math

def sqrt_or_none(x):
    """负数和 None 直接返回，避免深层 if 嵌套。"""
    if x is None or x < 0:
        return None
    return math.sqrt(x)

print(sqrt_or_none(9))   # 3.0
print(sqrt_or_none(-1))  # None
```

**关键结论**：把「边界情况」提前 `return`，主逻辑保持平坦，可读性显著提升。

---

## 6. 多行条件：PEP 8 推荐写法

当 `if` 条件很长时，用括号换行：

```python
this_is_one_thing = True
that_is_another_thing = True

# 推荐：括号内换行
if (this_is_one_thing and
        that_is_another_thing):
    print("两个条件都成立")
```

**关键结论**：括号内换行时，续行缩进不是强制的 4 空格，但应与代码块有视觉区分。

---

## 动手练习

**任务：写一个成绩等级判定函数**

要求：
1. 定义函数 `grade(score)`，输入一个 0~100 的分数。
2. 如果分数不在 0~100 范围内，返回 `"无效分数"`。
3. 90 及以上返回 `"A"`；80~89 返回 `"B"`；70~79 返回 `"C"`；60~69 返回 `"D"`；60 以下返回 `"F"`。
4. 用**提前返回**的方式写，避免多层嵌套。
5. 测试：`grade(95)` 返回 `"A"`，`grade(101)` 返回 `"无效分数"`，`grade(-5)` 返回 `"无效分数"`。

参考骨架（请补全逻辑）：

```python
def grade(score):
    if not isinstance(score, (int, float)):
        return "无效分数"
    # 在此继续写...

print(grade(95))   # A
print(grade(101))  # 无效分数
print(grade(-5))   # 无效分数
print(grade(75))   # C
```

完成后思考：如果不用提前返回，代码会嵌套几层？哪种更好读？

```python
# 综合示例：用 if 实现安全的平方根计算器
import math

def safe_sqrt(x):
    """返回 x 的平方根；若 x 为负数或 None，返回 None。"""
    if x is None:
        return None
    if x < 0:
        return None
    return math.sqrt(x)

def grade(score):
    """根据分数返回等级，提前返回避免嵌套。"""
    if not isinstance(score, (int, float)):
        return "无效分数"
    if score < 0 or score > 100:
        return "无效分数"
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"

# 测试
print(safe_sqrt(16))    # 4.0
print(safe_sqrt(-4))    # None
print(safe_sqrt(None))  # None

print(grade(95))        # A
print(grade(85))        # B
print(grade(75))        # C
print(grade(65))        # D
print(grade(55))        # F
print(grade(101))       # 无效分数
print(grade(-5))        # 无效分数

# Pythonic 真值判断
name = ""
if name:
    print("你好，" + name)
else:
    print("名字为空")

# 三元表达式
x = 10
label = "正数" if x > 0 else "非正数"
print(label)            # 正数

# startswith / endswith 而不是切片
foo = "bar_baz"
if foo.startswith("bar"):
    print("以 bar 开头")

# isinstance 而不是 type 比较
obj = 42
if isinstance(obj, int):
    print("obj 是整数")
```

## py.flow.elif_else

# 条件分支：`if` / `elif` / `else`

> **一句话直觉**：程序不是只会从上往下一条道走到黑，`if / elif / else` 让代码能根据不同情况走不同的路——这是所有 AI 工程里“判断、分支、决策”的最小基石。

---

## 1. 为什么需要条件分支

你写程序时，几乎每时每刻都在做判断：

- 如果 loss 比上次小，就保存模型；
- 如果用户输入是数字，就继续计算；否则提示格式错误；
- 如果 GPU 可用，就放到 GPU 上；否则用 CPU。

这些“如果……就……否则……”在 Python 里用 `if / elif / else` 表达。

最基本的写法是：

```python
x = 10
if x > 0:
    print("正数")
```

注意冒号 `:` 和缩进（indentation）。Python 用缩进来表示“这些代码属于上面那个条件”。

---

## 2. `if` 加 `else`：二选一

`else` 表示“前面条件都不成立时怎么办”。

```python
temperature = 30

if temperature >= 25:
    print("开空调")
else:
    print("不开空调")
```

`if` 和 `else` 只会有一个分支被执行，不可能两个都执行。

---

## 3. `elif`：多个条件依次判断

现实情况往往不止两种。`elif`（else if 的缩写）可以串起多个条件，**从上到下依次检查，遇到第一个为真就执行对应分支，然后直接跳过后面所有分支**。

```python
score = 76

if score >= 90:
    grade = "A"
elif score >= 80:
    grade = "B"
elif score >= 70:
    grade = "C"
elif score >= 60:
    grade = "D"
else:
    grade = "F"

print(grade)
```

**顺序很重要**：如果把 `score >= 70` 放在 `score >= 90` 前面，那么 95 分也会被判成 C。`elif` 是“短路”的——第一个为真后，后面全部不再判断。

---

## 4. 条件本身是“真值”而不是必须 `True`

Python 中任何对象都能当条件用。以下这些被视为 **假值（falsy）**：

- `False`、`None`
- 数字 `0`、`0.0`
- 空字符串 `""`
- 空列表 `[]`、空元组 `()`、空字典 `{}`、空集合 `set()`

其它都被视为 **真值（truthy）**。所以你可以写：

```python
data = []

if data:
    print("有数据")
else:
    print("没有数据")
```

但注意：判断 `None` 时要用 `is None` / `is not None`，不要用 `== None`。

```python
value = None
if value is None:
    print("未设置")
```

---

## 5. 工程级写法：可读性、提前返回、避免深嵌套

初学者常写出“金字塔式”的多层嵌套；工程中更推荐**提前返回（early return）**或用 `elif` 把逻辑拍平。

```python
def classify(value):
    if value is None:
        return "缺失"
    if value < 0:
        return "负数"
    if value == 0:
        return "零"
    return "正数"
```

另外，`if / elif / else` 是可以嵌套在另一个分支里的，但嵌套超过两层就要怀疑是否需要重构。

---

## 6. 与 AI 工程的一点联系

你在训练/推理脚本里天天会碰到这种结构：

```python
if device == "cuda" and torch.cuda.is_available():
    device = "cuda"
elif device == "mps" and torch.backends.mps.is_available():
    device = "mps"
else:
    device = "cpu"
```

`and` 是逻辑与，可以组合多个条件；`or` 是逻辑或；`not` 取反。它们是条件分支的好搭档。

---

## 7. 小结

| 结构 | 含义 |
|---|---|
| `if cond:` | 条件为真时执行 |
| `if cond: ... else: ...` | 二选一 |
| `if / elif / else` | 多路分支，自上而下短路判断 |
| `and` / `or` / `not` | 组合条件 |
| 缩进 | 决定代码块归属，Python 强制要求 |

记住三个关键词：**条件、缩进、短路**。

```python
# 学生成绩分级 —— 演示 if / elif / else 的完整用法


def grade_of(score):
    """根据分数返回等级字符串。"""
    if score is None or not isinstance(score, (int, float)):
        return "输入无效"
    if not 0 <= score <= 100:
        return "超出范围"
    if score >= 90:
        return "A"
    elif score >= 80:
        return "B"
    elif score >= 70:
        return "C"
    elif score >= 60:
        return "D"
    else:
        return "F"


# 批量测试
samples = [95, 83, 76, 60, 42, None, 120, -1, "abc"]
for s in samples:
    print(f"{s!r:>6} -> {grade_of(s)}")

# 真值判断示例
history = []
if not history:
    print("还没有训练历史")
else:
    print(f"最新 loss = {history[-1]}")
```


---

## 本课题目

### single_choice · None



- [A] if 语句块必须用花括号 {} 包裹
- [B] if 语句块通过缩进表示，同一块内缩进必须一致
- [C] if 语句块必须恰好缩进一个空格
- [D] if 语句块必须用 end 关键字结束

**参考答案**：1

**解析**：Python 用缩进表示代码块，不用花括号。同一代码块内缩进必须一致，但具体几个空格（通常 4 个）不是语法强制，只要块内一致即可。

### single_choice · None



- [A] 真
- [B] 假
- [C] 报错
- [D] 什么都不输出

**参考答案**：1

**解析**：整数 0 的布尔值为 False，因此条件不成立，执行 else 分支，输出“假”。

### multi_choice · None



- [A] None
- [B] 0
- [C] 空列表 []
- [D] "False"
- [E] [0, 0]

**参考答案**：[0, 1, 2]

**解析**：None、0、空容器（如空列表）都是假值。字符串 "False" 非空为真；[0, 0] 是非空列表，也为真。

### multi_choice · None



- [A] elif 可以有多个
- [B] else 最多一个
- [C] 各分支按从上到下的顺序判断，命中一个后其余分支不再执行
- [D] elif 可以单独使用而不需要 if

**参考答案**：[0, 1, 2]

**解析**：elif 可以有任意多个，else 最多一个，判断自上而下，命中即结束。elif 不能脱离 if 单独存在，因此选项 3 错误。

### multi_choice · None



- [A] if a and b:
- [B] if not flag:
- [C] if x > 0 or y > 0:
- [D] if a = b:

**参考答案**：[0, 1, 2]

**解析**：and、not、or 都是合法的布尔运算符组合。而 a = b 是赋值语句，不能作为条件，会引发语法错误。

### multi_choice · None



- [A] 形式为 值1 if 条件 else 值2
- [B] 条件为真时取 值1
- [C] 条件为假时取 值2
- [D] 它必须配合 print 才能使用

**参考答案**：[0, 1, 2]

**解析**：条件表达式形式为 值1 if 条件 else 值2，真取前、假取后，可用于任何需要表达式的地方，不限于 print。

### fill_blank · None



**参考答案**：["elif", "elif "]

**解析**：多分支判断中，第二个条件使用 elif，它只在前面条件不成立时才会继续判断。

### fill_blank · None



**参考答案**：["in"]

**解析**：in 用于判断子串是否存在于字符串中，"app" 是 "apple" 的子串，因此条件成立。

### code_reading · None



**参考答案**：中

**解析**：x=5 不满足 >10，满足 >3，命中第一个 elif 后即结束，不再判断后续分支，输出“中”。

### code_reading · None



**参考答案**：D

**解析**：0、空字符串和 None 都是假值，三个条件均不成立，因此执行 else 分支，输出 D。

### code_reading · None



**参考答案**：奇

**解析**：n % 2 为 1，条件 n % 2 == 0 不成立，因此条件表达式取 else 后的值，输出“奇”。

### scenario · None



**解析**：username 为 None 时，== "" 判断为 False，无法识别出空的情况；而依赖真值判断（如 if not username）可以同时覆盖 None、空字符串等假值。因此推荐用真值判断而非与空字符串比较。

### single_choice · None



- [A] 字符串 "0"
- [B] 列表 [0]
- [C] 空字符串 ""
- [D] 整数 -1

**参考答案**：2

**解析**：空字符串是假值。字符串 "0" 非空为真；列表 [0] 非空为真；-1 非零为真。

### scenario · None



**解析**：多分支从上到下依次判断且互斥，先判断 >=60 会把 90 分以上的也截获。应把更严格的 >=90 放在前面，或将条件按从高到低排列。

### single_choice · None



- [A] A
- [B] B
- [C] C
- [D] B 和 C

**参考答案**：1

**解析**：score 为 75，不满足 >=90，满足 >=60，因此进入第一个 elif 分支输出 B。elif 是互斥的，只会执行一个分支。

### single_choice · None



- [A] 1
- [B] 1 换行 2
- [C] 1 换行 2 换行 3
- [D] 1 换行 3

**参考答案**：2

**解析**：print(1) 和 print(2) 都在 if 块内（有缩进），都会执行；print(3) 没有缩进，位于 if 块外，无条件执行。

### single_choice · None



- [A] in 只能用于字符串
- [B] in 可用于检查元素是否属于序列或集合等容器
- [C] in 只能用于列表
- [D] in 在 if 中出现会导致语法错误

**参考答案**：1

**解析**：in 是成员运算符，可用于字符串、列表、元组、集合、字典（检查键）等容器，在 if 条件中很常见。

### single_choice · None



- [A] 成年
- [B] 刚成年
- [C] 未成年
- [D] 什么都不输出

**参考答案**：1

**解析**：age 等于 18，不满足 >18，满足 ==18，因此输出“刚成年”。

### single_choice · None



- [A] 能运行，输出 ok
- [B] 报语法错误，因为条件中应使用 == 而不是 =
- [C] 能运行，但不输出任何内容
- [D] 报运行时错误，因为 x 未定义

**参考答案**：1

**解析**：在条件表达式中 = 是赋值语句而非比较，会导致语法错误（SyntaxError），比较应使用 ==。

### single_choice · None



- [A] if 语句不能嵌套
- [B] if 语句可以嵌套，内层 if 的缩进要比外层更深
- [C] if 语句可以嵌套，但内层缩进必须和外层一样
- [D] 嵌套 if 时必须使用 elif

**参考答案**：1

**解析**：if 可以嵌套，内层代码块相对外层需要更深的缩进，以体现层级关系。

### single_choice · None



- [A] 非空
- [B] 空
- [C] 报错
- [D] 输出列表内容

**参考答案**：0

**解析**：非空列表的布尔值为 True，因此输出“非空”。

### single_choice · None



- [A] A
- [B] B
- [C] C
- [D] D

**参考答案**：1

**解析**：x=7 不满足 x>10，满足 x>5，因此执行第一个 elif 分支并输出 B。elif 链一旦匹配就跳过后续所有分支，所以即使 x>0 也成立，也不会再执行输出 C 的分支。

### single_choice · None



- [A] 1
- [B] 2
- [C] 3
- [D] 4

**参考答案**：2

**解析**：num=4 不满足 num>10 和 num>8，满足 num>2，所以执行 num=3。之后 elif 链结束，不再检查 else，num 为 3。

### single_choice · None



- [A] elif 不能出现在 else 之后，会触发 SyntaxError
- [B] elif 条件写反了
- [C] print 应改为 return
- [D] 没有问题

**参考答案**：0

**解析**：if/elif/else 结构中，else 必须是最后一个分支。把 elif 放在 else 之后属于语法错误，Python 会抛 SyntaxError。正确顺序应为 if → elif → else。

### single_choice · None



- [A] 一
- [B] 二
- [C] 三
- [D] 什么都不输出

**参考答案**：3

**解析**：x=5 不满足任何一个 if/elif 条件，且该结构没有 else 兜底，因此所有分支都被跳过，程序不产生任何输出，也不会报错。缺少 else 时可能无输出是常见陷阱。

### multi_choice · None



- [A] elif 可以有多个，按书写顺序从上到下依次判断
- [B] else 最多出现一次，且必须位于所有 elif 之后
- [C] 每个 elif 都必须带一个条件表达式
- [D] 当某个 elif 条件为真时，会先执行该分支，再继续检查后面的 elif

**参考答案**：[0, 1, 2]

**解析**：elif 可以有任意多个，按顺序判断；else 最多一次且在最末；每个 elif 必须有条件表达式。选项 D 错误，因为第一个为真的分支执行后，整个结构即结束，不再检查后面的分支。

### multi_choice · None



- [A] 所有 if 和 elif 的条件都为假
- [B] 第一个 if 条件为真
- [C] 最后一个 elif 条件为真
- [D] 使用了 if 但条件表达式为 0

**参考答案**：[0, 3]

**解析**：当所有条件都为假且没有 else 时，没有任何分支执行，程序无输出；条件表达式为 0 等价于假，同理可能无输出。第一个 if 为真、或某个 elif 为真都会产生输出。

### multi_choice · None



- [A] if a: pass
  elif b: pass
  else: pass
- [B] if a: pass
  else: pass
  elif b: pass
- [C] if a: pass
  if b: pass
- [D] elif a: pass

**参考答案**：[0, 2]

**解析**：if 可以单独使用，也可以带 elif/else；两个独立 if 也是合法的。但在 else 之后再写 elif 属于语法错误；直接以 elif 开头（前面没有 if）也是语法错误。

### multi_choice · None



- [A] 用 elif 时，成功匹配的分支之后的判断会被跳过
- [B] 用多个独立 if 时，所有条件为真的分支都会执行
- [C] elif 和 if 在语义上完全等价，可以随意替换
- [D] 当多个条件可能同时为真时，elif 只会执行其中一个分支

**参考答案**：[0, 1, 3]

**解析**：elif 是互斥的：第一个为真即结束，后续跳过的判断不会再执行；多个独立 if 会各自判断、可能全部执行。两者语义不同，不能随意替换，因此在“条件可能同时为真但只需执行一个分支”时应使用 elif。

### fill_blank · None



**参考答案**：["elif", "elif "]

**解析**：要在第一个条件之后再补一个互斥条件，应该使用 elif。若填 if，当 score>=90 和 score>=80 同时成立时会输出两行，破坏互斥性。

### fill_blank · None



**参考答案**：["假", "false", "False", "为假", "假值"]

**解析**：else 是兜底分支，仅在所有 if 和 elif 条件都为假（False）时执行。这也是它被称为“默认分支”的原因。

### code_reading · None



**参考答案**：x=7 时，第一个条件 x>10 为假，第二个条件 x>5 为真，进入该 elif 分支并执行 print("B")。由于 if/elif 是互斥结构，一旦某个分支的条件为真并执行完，后续所有 elif 分支都会被跳过，因此尽管 x>0 也为真，输出 "C" 的分支不会再执行，最终只输出 B。

**解析**：本题考查 elif 链的“首个为真即结束”规则。关键是理解：后续 elif 虽然条件也可能为真，但由于前面已有分支命中，它们不会被检查。

### scenario · None



**解析**：原来的三个分支使用了两个独立 if，第一个 if 与第二个 if 是各自判断的，导致 amount=600 时先被赋为 0.8，随后又进入第二个 if 被覆盖为 0.9。修正方式是改用 if/elif/else 形成互斥多分支：条件从上到下判断，第一个满足的分支执行后即结束，不会覆盖。修正后 amount>=500 时只执行 0.8 分支。

### single_choice · None



- [A] A
- [B] B
- [C] C
- [D] 报错：grade 未定义（在满足 70≤score<80 时才会这样）

**参考答案**：1

**解析**：score=85 满足 score>=80，执行 grade="B"，输出 B。elif 是顺序判断，第一个满足条件的分支被执行后其余分支被跳过。选项 D 描述的是当条件落在未覆盖区间时的潜在问题，但本题 score=85 已被覆盖，因此不报错。

### single_choice · None



- [A] 所有满足条件的 elif 分支都会被执行
- [B] elif 分支可以不写条件表达式
- [C] 一旦某个分支的条件为真，执行该分支后整个 if/elif/else 结构结束
- [D] else 必须与每个 elif 配对出现

**参考答案**：2

**解析**：if/elif/else 是互斥的多分支结构：从上到下检查，第一个为真的分支执行后，整个结构就结束，后面的分支不再检查。elif 必须有条件表达式；else 是可选的且最多出现一次，不需要与每个 elif 配对。

### single_choice · None



- [A] 相同，都输出两行
- [B] 不相同：代码一输出两行，代码二只输出一行
- [C] 不相同：代码一输出一行，代码二输出两行
- [D] 相同，都只输出一行

**参考答案**：1

**解析**：代码一用两个独立的 if，两个条件互不影响，都会检查并执行，输出“正”和“大”两行。代码二用 if/elif，x>0 已为真，elif 被跳过，只输出“正”一行。这就是用 elif 替代连续 if 时的关键区别。

### single_choice · None



- [A] 真
- [B] 零
- [C] 假
- [D] 什么都不输出

**参考答案**：1

**解析**：value=0 在布尔语境下为假，所以 if value 不成立。接着检查 elif value == 0，该表达式为 True，输出“零”。注意区分“真值判断”（if value）与“相等判断”（value == 0）。

### single_choice · None



- [A] if a > 0: 这一行
- [B] print("A") 这一行
- [C] elif: 这一行，elif 缺少条件表达式
- [D] 整体没有错误

**参考答案**：2

**解析**：elif 必须跟一个条件表达式，写成裸的 elif: 会触发 SyntaxError。只有 else 才是不带条件的，elif 不能省略条件。

### single_choice · None



- [A] 正数
- [B] 负数
- [C] 零
- [D] 报错

**参考答案**：1

**解析**：n=-3 不满足 n>0，满足 n<0，因此执行 elif 分支输出“负数”。这是典型的三分支互斥结构。

### single_choice · None



- [A] 当且仅当所有 if 和 elif 条件都为假时执行
- [B] 当任意一个 elif 条件为假时执行
- [C] 无论条件真假都会执行
- [D] 必须与每个 elif 一一对应

**参考答案**：0

**解析**：else 是兜底分支，只有当上面所有的 if 和 elif 条件都不成立时才执行。它不是对单个 elif 的补充，而是整个链的默认出口，最多出现一次。

### single_choice · None



- [A] if
- [B] elif
- [C] else
- [D] while

**参考答案**：1

**解析**：要实现互斥的三分支判断，第一个条件之后应使用 elif，这样当 x>50 成立时就不会再检查 x>5。若用 if 会变成独立判断，可能导致多个分支同时执行。while 是循环，不适用。
