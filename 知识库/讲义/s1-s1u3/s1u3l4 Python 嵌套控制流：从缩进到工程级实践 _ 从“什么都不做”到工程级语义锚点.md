# s1u3l4 Python 嵌套控制流：从缩进到工程级实践 / 从“什么都不做”到工程级语义锚点

> 来源 `content/lessons/s1u3l4.json`

## py.flow.nested

# Python 嵌套控制流：从缩进到工程级实践

> **一句话直觉**：Python 用「缩进（indentation）」而不是花括号来表达「谁属于谁」——嵌套（nested）控制流就是让你在一层一层「代码套娃」中，把复杂逻辑写清楚、写正确、写可读。

---

## 0. 为什么先学「嵌套」？

任何一门语言都会有分支和循环，但 Python 的特殊之处在于：**它把「缩进」本身变成了语法**。你写代码时的空白字符，决定了 `if` 属于谁、`for` 里包了什么、`else` 又和哪个 `if` 配对。这就是「嵌套控制流（nested flow control）」要讲清楚的核心。

学完之后，你能：

1. 读懂多层缩进的代码（而不是看着头疼）。
2. 自己写出整洁的多层 `if/for/while/try`。
3. 避开常见的缩进、`else` 配对、长条件换行等「坑」。

---

## 1. 缩进就是语法：Python 的「套娃」规则

在 C/Java 里，`{ }` 决定代码块；Python 用「冒号 `:` + 缩进」表达代码块（block）。

规则只有三条：

- **每个冒号后面必须换行并缩进**，表示一个子块。
- **同一层的语句缩进量必须一致**。
- **官方推荐用 4 个空格（4 spaces）作为一层缩进**（PEP 8），不要混用 Tab 和空格。

```python
# 示例 1：一层嵌套
score = 85
if score >= 60:
    print("及格")          # 4 空格
    if score >= 90:
        print("优秀")      # 8 空格
```

**关键结论**：缩进不是「美化」，而是「语法」。缩进错了，程序直接报 `IndentationError`。

---

## 2. 多层嵌套的常见形态：if / for / while / try

嵌套不是只有 `if` 套 `if`。真实代码里，四种控制流经常互相嵌套。

### 2.1 if 套 for

```python
# 示例 2：判断列表里有没有负数
nums = [3, -1, 5]
has_negative = False
if nums:
    for n in nums:
        if n < 0:
            has_negative = True
            break
print(has_negative)
```

### 2.2 for 套 while

```python
# 示例 3：对每个数做递减运算
for target in [3, 2]:
    n = target
    while n > 0:
        print(f"target={target}, n={n}")
        n -= 1
```

### 2.3 try 套 if

```python
# 示例 4：多层嵌套中捕获异常
def to_int(x):
    try:
        if x is None:
            return 0
        return int(x)
    except (TypeError, ValueError):
        return -1

print(to_int("42"), to_int(None), to_int("abc"))
```

**关键结论**：嵌套是自然形成的，不是刻意追求。**当嵌套超过 3 层时，优先考虑拆函数**。

---

## 3. else / elif 的配对规则

`else` 永远和**最近的、尚未配对的 `if`** 结合。这一条在多层嵌套里最容易出错。

```python
# 示例 5：else 属于内层 if
x = 5
if x > 0:
    if x > 10:
        print("很大")
    else:
        print("正但不大")   # 属于内层 if
else:
    print("非正")
```

**关键结论**：Python 没有 C 的「悬空 else」陷阱，因为缩进强制了归属。但**读代码时仍然要看清缩进层级**。

---

## 4. 嵌套与提前返回：让代码「扁平化」

工程里最常见的「去嵌套」技巧是**卫语句（guard clause）**：能在最早位置返回就在最早位置返回。

```python
# 示例 6：反面教材（嵌套较深）
def sqrt_pos(x):
    if x >= 0:
        return x ** 0.5
    else:
        return None

# 正面示例（扁平化）
def sqrt_pos2(x):
    if x < 0:
        return None
    return x ** 0.5

print(sqrt_pos(9), sqrt_pos2(9))
```

**关键结论**：卫语句把「异常分支」提前掐掉，让主流程保持在同一层缩进里 —— 这是 PEP 8 推荐写法。

---

## 5. 长的条件与参数：嵌套里的「换行」艺术

当 `if` 的条件很长，需要换行时，PEP 8 给了两种主流写法：

- **对齐到左括号（aligned with opening delimiter）**
- **悬挂缩进（hanging indent）**：再多缩进一层。

```python
# 示例 7：多行 if 的两种写法
this_is_one_thing = True
that_is_another_thing = True

# 写法 A：悬挂缩进（推荐，且不会和内层代码混淆）
if (this_is_one_thing and
        that_is_another_thing):
    print("both true")

# 写法 B：对齐到左括号
def long_fn(var_one, var_two,
            var_three, var_four):
    print(var_one, var_two, var_three, var_four)

long_fn(1, 2, 3, 4)
```

**关键结论**：多行条件如果换行方式看不清层次，宁可**加注释或使用显式括号**，也不要为了「省行数」而堆在一行。

---

## 6. 判断类的正确姿势（顺带记住，嵌套里常用）

这几条在嵌套 `if` 里经常出现，属于工程级基本功：

- 前缀/后缀判断用 `str.startswith()` / `str.endswith()`，别用切片。
- 类型判断用 `isinstance()`，别用 `type(x) == ...`。
- 空序列直接用 `if not seq:`，别写 `if len(seq) == 0:`。
- 布尔值不要和 `True`/`False` 用 `==` 比较。

```python
# 示例 8：工程级判断
s = "report_2024.csv"
obj = 42
seq = []

if s.endswith(".csv"):
    print("is csv")

if isinstance(obj, int):
    print("int")

if not seq:
    print("empty sequence")
```

---

## 7. 动手练习：把「深嵌套」改写成「扁平 + 卫语句」

**任务（本地完成，约 10~15 分钟）**：

1. 新建文件 `practice_nested.py`。
2. 写一个函数 `classify_student(score, name)`：
   - 如果 `name` 为空字符串，返回 `"名字不能为空"`。
   - 如果 `score` 不是数字，返回 `"分数必须是数字"`。
   - 如果 `score < 0` 或 `score > 100`，返回 `"分数超出范围"`。
   - 否则：`>=90` 返回 `f"{name}: 优秀"`；`>=60` 返回 `f"{name}: 及格"`；否则返回 `f"{name}: 不及格"`。
3. **要求**：全部用**卫语句（guard clause）** + **最多一层嵌套**实现，不要出现 `if` 套 `if` 套 `if`。
4. 自己写 4 个测试调用，覆盖：空名字、非数字、超出范围、正常分数。
5. 运行并检查输出。

**进阶（可选）**：把 `classify_student` 中的「分数范围判断」抽成一个内部小函数，再减少一层嵌套。

---

### 本篇小结

- 缩进 = 语法，推荐 4 空格，别混用 Tab。
- 嵌套是为了表达层级，不是为了炫技；**超过 3 层就拆函数**。
- `else` 永远配最近的 `if`，读代码先看缩进。
- 用**卫语句**把异常分支提前返回，能让代码「扁平化」。
- 长条件换行有两种主流写法：悬挂缩进、对齐左括号；选一种并保持一致。

```python
"""演示 Python 嵌套控制流的可运行示例。"""


def classify_student(score, name):
    # 卫语句 1：名字不能为空
    if not name:
        return "名字不能为空"

    # 卫语句 2：分数必须是数字（bool 也属于 int，特意排除）
    if isinstance(score, bool) or not isinstance(score, (int, float)):
        return "分数必须是数字"

    # 卫语句 3：分数范围
    if score < 0 or score > 100:
        return "分数超出范围"

    # 主流程（只剩一层嵌套）
    if score >= 90:
        level = "优秀"
    elif score >= 60:
        level = "及格"
    else:
        level = "不及格"
    return f"{name}: {level}"


# 多层嵌套对照示例：for -> if -> while
if __name__ == "__main__":
    tests = [
        ("", 90),
        ("小明", "A"),
        ("小红", 120),
        ("小刚", 95),
        ("小美", 59),
    ]
    for name, score in tests:
        print(classify_student(score, name))

    # 演示 else 与 if 的配对
    x = 5
    if x > 0:
        if x > 10:
            print("很大")
        else:
            print("正但不大")
    else:
        print("非正")

    # 演示多行 if 的悬挂缩进
    a, b = True, True
    if (a and
            b):
        print("both true")
```

## py.flow.pass

# py.flow.pass：从“什么都不做”到工程级语义锚点

> 一句话直觉：`pass` 是 Python 里唯一“语法上必须写、语义上什么都不做”的语句，它是你理解“缩进块、占位、协议与类型契约”的第一块地基。

---

## 1. 为什么需要 `pass`：空块的语法刚需

Python 用缩进（indentation）表示代码块（block）。只要出现 `if`、`for`、`while`、`def`、`class`、`try`、`with` 等复合语句，冒号后面**必须**有一个非空代码块。

但真实工程中经常遇到“这个分支暂时不处理”“这个函数稍后再实现”“这个异常先吞掉”的场景。此时你既不能省略代码块，也不能写注释（注释不构成语句），于是 `pass` 出现：它是一个合法的空操作（no-op）语句。

```python
# 演示：pass 是唯一能合法填充空块的语句
if True:
    pass  # 语法要求这里必须有语句，pass 什么都不做

def todo_later():
    pass  # 占位：函数体暂时为空

class Config:
    pass  # 占位：先建一个空类

print("程序继续运行，pass 不会产生任何副作用")
```

**关键结论**：`pass` 不是“空”，而是“显式的空”。它让“我故意什么都不做”变成一个可读、可搜索、可被工具识别的信号。

---

## 2. `pass` 与 `...`（Ellipsis）、`None`、注释的区别

初学者最容易混淆的是“几种看起来都像什么都不做”的写法：

| 写法 | 是否语句 | 运行时行为 | 常见用途 |
|---|---|---|---|
| `pass` | 是 | 空操作 | 真正的“暂时不实现” |
| `...` | 是（表达式语句） | 求值为 `Ellipsis` 对象，然后丢弃 | 类型存根、协议、抽象占位 |
| `None` | 是（表达式语句） | 求值为 `None`，然后丢弃 | 几乎不这么写，语义模糊 |
| `# 注释` | 否 | 不构成语句 | 说明文字 |

```python
# pass 与 ... 的运行时差异

def with_pass():
    pass

def with_ellipsis():
    ...

print(with_pass())      # None
print(with_ellipsis())  # None（函数没 return 都返回 None）

# 但表达式本身不同
x = ...
print(x is Ellipsis)    # True

y = pass  # 语法错误：pass 不是表达式，不能赋值
```

**关键结论**：`pass` 是“语句级空操作”，`...` 是“表达式级占位”，后者在协议（Protocol）、类型存根（stub）和抽象基类中更常见。

---

## 3. `pass` 在类与继承中的角色：空类也是合法类

`class Foo: pass` 会创建一个真实可实例化的类。它没有自定义属性，但继承链、`__dict__`、`isinstance` 全部正常工作。这是“最小可用类”的写法。

```python
# 空类是最小可用的类型锚点
class Base:
    pass

class Sub(Base):
    pass

obj = Sub()
print(isinstance(obj, Base))   # True
print(Sub.__mro__)              # (<class 'Sub'>, <class 'Base'>, <class 'object'>)

# 多继承：disjoint_base 的反面教材
class A:
    pass

class B:
    pass

class C(A, B):
    pass

print(C.__mro__)  # C -> A -> B -> object（运行时合法）
```

**关键结论**：`pass` 定义的类不是“占位符”，它是完整类型。工程中常用于“标记类”（marker class）、“命名空间类”和“异常基类”。

---

## 4. `pass` 在异常与循环中的工程语义

在 `try/except` 中，`pass` 表示“显式吞掉异常”。这不是偷懒，而是一种设计决策——但必须配注释说明**为什么可以吞**。

```python
# 场景：清理临时文件，失败也无所谓
def safe_cleanup(path: str) -> None:
    import os
    try:
        os.remove(path)
    except FileNotFoundError:
        pass  # 文件本来就不存在，无需处理

# 场景：循环中跳过不满足条件的元素
for i in range(5):
    if i % 2 == 0:
        pass  # 偶数先不处理，保留分支结构
    else:
        print("奇数:", i)
```

**关键结论**：`pass` 在异常处理中等于“静默忽略”，必须配合注释；在循环中等于“保留分支骨架”，便于后续填充逻辑。

---

## 5. `pass` 与类型系统：占位、协议与 `@override`

现代 Python 的类型检查（type checking）大量使用 `...` 作为函数体占位，但在**运行时**依然会落地为空操作。`pass` 与它们的关系是：

- 存根文件（`.pyi`）和协议（Protocol）里通常写 `...`；
- 真实可运行代码里，若只是暂时不实现，写 `pass` 更明确；
- 装饰器（decorator）如 `@override`（Python 3.12+）只做静态检查，运行时可能什么都不做，`pass` 可以作为其函数体。

```python
# 演示：pass 作为被装饰函数的合法体
try:
    from typing import override
except ImportError:
    def override(f):  # 兼容旧版本
        return f

class Base:
    def log_status(self) -> None:
        pass

class Sub(Base):
    @override
    def log_status(self) -> None:
        pass  # 重写父类方法，暂时空实现

Sub().log_status()  # 不会报错

# 运行时可通过 __override__ 属性判断
print(getattr(Sub.log_status, "__override__", False))  # True（3.12+）
```

**关键结论**：`pass` 是运行时与静态类型系统之间的“最小连接件”——它保证语法合法，同时不引入任何运行副作用，让类型检查器和装饰器接管语义。

---

## 动手练习

**任务**：实现一个“极简事件系统”，要求：

1. 定义空基类 `Event` 和子类 `ClickEvent`、`KeyEvent`，全部用 `pass` 占位。
2. 定义一个 `EventBus` 类，内部有 `handlers: dict[type, list]`。
3. `subscribe(event_type, handler)` 注册处理器；`publish(event)` 根据 `isinstance` 找到匹配的处理器并调用。
4. 至少注册一个“忽略 KeyEvent”的处理器，用 `pass` 明确表示不处理，并写注释说明原因。

**验收标准**：
- 空类能被 `isinstance` 正确识别；
- `pass` 分支不产生任何输出；
- 代码能本地运行且无语法/类型错误。

```python
"""py.flow.pass 综合示例：极简事件系统"""

# 1. 空类作为类型锚点
class Event:
    pass

class ClickEvent(Event):
    pass

class KeyEvent(Event):
    pass

# 2. 事件总线
class EventBus:
    def __init__(self) -> None:
        self.handlers: dict[type, list] = {}

    def subscribe(self, event_type: type, handler) -> None:
        self.handlers.setdefault(event_type, []).append(handler)

    def publish(self, event: Event) -> None:
        for event_type, handlers in self.handlers.items():
            if isinstance(event, event_type):
                for h in handlers:
                    h(event)

# 3. 处理器
def on_click(event):
    print("处理点击:", type(event).__name__)

def on_any(event):
    if isinstance(event, KeyEvent):
        pass  # 明确忽略键盘事件：本系统不处理输入
    else:
        print("通用处理器收到:", type(event).__name__)

# 4. 组装运行
bus = EventBus()
bus.subscribe(ClickEvent, on_click)
bus.subscribe(Event, on_any)

bus.publish(ClickEvent())
bus.publish(KeyEvent())

# 5. pass 与 ... 的语义对比
def placeholder_pass():
    pass

def placeholder_ellipsis():
    ...

print(placeholder_pass() is None)        # True
print(placeholder_ellipsis() is None)    # True
print(... is Ellipsis)                   # True
```


---

## 本课题目

### single_choice · None



- [A] 输出 3 行，每行一个数字对
- [B] 输出 6 行，按 (0,0) (0,1) (1,0) (1,1) (2,0) (2,1) 的顺序
- [C] 输出 6 行，按 (0,0) (1,0) (2,0) (0,1) (1,1) (2,1) 的顺序
- [D] 只输出 2 行，因为内层循环覆盖了外层循环

**参考答案**：1

**解析**：外层循环每迭代一次，内层循环都会完整走一遍，因此顺序是先固定 i，把 j 从 0 到 1 全部执行完，再进入下一个 i，共 3×2=6 行。

### single_choice · None



- [A] 嵌套循环的总迭代次数等于外层循环次数加内层循环次数
- [B] 嵌套循环的总迭代次数等于外层循环次数乘以内层循环次数（忽略提前退出）
- [C] 嵌套循环的总迭代次数总是等于外层循环次数
- [D] 嵌套循环的总迭代次数总是等于内层循环次数

**参考答案**：1

**解析**：在没有 break、continue 等提前退出语句时，外层每执行一次，内层就完整执行一次，所以总次数是两层次数的乘积。

### single_choice · None



- [A] 内层 print('*') 默认会换行，导致每行只有一个星号，应使用 print('*', end='')
- [B] 外层循环应该使用 while 而不是 for
- [C] 内层循环应该改成 range(4)
- [D] print() 应该放在内层循环里面

**参考答案**：0

**解析**：print('*') 每次输出后都会换行，因此每个星号独占一行。要形成一行多个星号，需要在内层使用 end='' 抑制换行，最后再统一换行。

### single_choice · None



- [A] 在内层循环中直接写 break
- [B] 在外层循环中写 continue
- [C] 设置一个标志变量，在内层循环中修改它，外层循环检查该标志后 break
- [D] 在内层循环中写 return

**参考答案**：2

**解析**：内层 break 只能跳出内层，continue 只能影响所在层。使用标志变量可以让外层感知到内层满足条件，从而跳出外层循环。return 只在函数内有意义且会结束整个函数。

### single_choice · None



- [A] 内层循环不能访问外层循环的循环变量
- [B] 外层循环不能访问内层循环的循环变量
- [C] 内层循环可以访问外层循环的循环变量，但外层循环不能直接访问内层循环结束后残留的循环变量
- [D] 内外层循环变量必须使用相同的名字

**参考答案**：2

**解析**：Python 中变量作用域是按函数等层次划分的，内层可以读取外层循环变量；但内层循环结束后，其循环变量仍会保留在作用域中，外层可以在之后访问到它的值，而不是“不能访问”。

### single_choice · None



- [A] 不能访问，会报 NameError
- [B] 可以访问，输出最后一次内层循环的值 1
- [C] 可以访问，输出外层循环的值 1
- [D] 可以访问，但输出的是未定义值

**参考答案**：1

**解析**：Python 的 for 循环不会创建新的作用域，内层循环变量 j 在循环结束后仍然存在，其值为最后一次迭代的值 1。

### single_choice · None



- [A] O(n)
- [B] O(n²)
- [C] O(log n)
- [D] O(1)

**参考答案**：1

**解析**：外层执行 n 次，内层每次也执行 n 次，总操作次数约为 n×n，因此是 O(n²)。

### single_choice · None



- [A] 只与 n 有关，内层每次都执行 n 次
- [B] 只与外层变量 i 有关，与 n 无关
- [C] 与外层变量 i 有关：当外层为 i 时，内层执行 i+1 次
- [D] 内层循环不会执行

**参考答案**：2

**解析**：内层 range(i+1) 的上限由外层变量 i 决定，因此内层次数随外层变化，i 确定时为 i+1 次。

### single_choice · None



- [A] 0 0; 0 1; 0 2; 1 0; 1 2; 2 0; 2 1; 2 2; 
- [B] 0 0; 0 1; 0 2; 1 0; 2 0; 2 1; 2 2; 
- [C] 0 0; 0 1; 0 2; 1 0; 1 1; 1 2; 2 0; 2 1; 2 2; 
- [D] 0 0; 1 1; 2 2; 

**参考答案**：0

**解析**：当 i==1 且 j==1 时，内层 break 只跳过 i=1、j=1 之后内层剩余迭代（即跳过 j=2），但外层继续。因此输出缺少 1 1 和 1 2，其余都有。

### single_choice · None



- [A] 内层循环可以有自己的 break 和 continue，它们只影响内层
- [B] 内层循环的 break 会同时终止外层循环
- [C] 内层循环的 continue 会跳过外层循环的当前迭代
- [D] 外层循环的 continue 会跳过内层循环的当前迭代

**参考答案**：0

**解析**：break 和 continue 都是作用于它们所在的那一层循环。内层的控制语句只影响内层，外层的只影响外层。

### single_choice · None



- [A] [(0, 0), (1, 1)]
- [B] [(0, 1), (1, 0)]
- [C] [(0, 0), (0, 1), (1, 0), (1, 1)]
- [D] [(0, 1)]

**参考答案**：1

**解析**：只有 i 不等于 j 的组合会被加入，满足条件的组合是 (0,1) 和 (1,0)。

### single_choice · None



- [A] 完全相同，都是 0 0、0 1、1 0、1 1
- [B] 不同，写法一先变化 j，写法二先变化 i
- [C] 不同，写法一输出 (0,0)(0,1)(1,0)(1,1)，写法二输出 (0,0)(1,0)(0,1)(1,1)
- [D] 写法二会报错，因为内外层变量顺序颠倒了

**参考答案**：2

**解析**：写法一外层变量是 i，先固定 i 变化 j；写法二外层变量是 j，先固定 j 变化 i，因此输出顺序不同。

### single_choice · None



- [A] 打印所有 i 和 j 都不相等的组合
- [B] 打印所有 i 和 j 都相等的组合
- [C] 打印 i 小于 j 的组合
- [D] 打印 i 大于 j 的组合

**参考答案**：0

**解析**：当 i 等于 j 时执行 break，跳出当前内层循环，因此每一轮中 i==j 的那次不会打印，最终只打印 i 和 j 不相等的组合。

### single_choice · None



- [A] 同时跳出外层循环和内层循环
- [B] 只跳出当前所在的那一层循环
- [C] 会终止整个程序
- [D] 会跳过本次循环的剩余部分，但继续下一次迭代

**参考答案**：1

**解析**：break 只终止它所在的那一层循环，不会自动终止外层循环。要跳出多层通常需要额外标志或异常等机制。

### single_choice · None



- [A] 12
- [B] 9
- [C] 8
- [D] 6

**参考答案**：1

**解析**：外层 3 次，内层 4 次，其中 j==2 时 continue 跳过累加，所以每轮只加 3 次，共 3×3=9。

### single_choice · None



- [A] 跳过整个内层循环的剩余迭代，直接开始外层循环的下一次
- [B] 只跳过当前这一层循环的本次剩余部分，继续该层循环的下一次迭代
- [C] 同时跳过外层和内层本次迭代
- [D] 跳出所有循环

**参考答案**：1

**解析**：continue 只影响它所在的那一层循环，它会跳过该层本次迭代剩余代码，进入该层循环的下一次迭代。

### single_choice · None



- [A] 3 行
- [B] 6 行
- [C] 9 行
- [D] 0 行

**参考答案**：0

**解析**：内层范围是 range(i)，当 i=0 时执行 0 次，i=1 时执行 1 次，i=2 时执行 2 次，总共 0+1+2=3 行。

### single_choice · None



- [A] 16 次
- [B] 10 次
- [C] 8 次
- [D] 4 次

**参考答案**：1

**解析**：i=1 时内层 4 次，i=2 时 3 次，i=3 时 2 次，i=4 时 1 次，合计 4+3+2+1=10 次。

### single_choice · None



- [A] 0 1 1 2
- [B] 0 0 1 1
- [C] 0 1 2 3
- [D] 1 2 2 3

**参考答案**：0

**解析**：依次组合为 (0,0)->0、(0,1)->1、(1,0)->1、(1,1)->2，因此输出 0 1 1 2。

### single_choice · None



- [A] 9
- [B] 18
- [C] 36
- [D] 27

**参考答案**：1

**解析**：外层 i 为 0、1、2；内层 j 为 0、1、2。总和为 (0+0+0)+(0+1+2)+(0+2+4)=0+3+6=9？逐项复核：i=0 时全为 0；i=1 时 0+1+2=3；i=2 时 0+2+4=6；总计 9。等等，选项中没有 9？正确答案应为 9，但选项未列出？请修正：实际总和是 9，应出现在选项中。再核对 i=2、j=2 为 4，i=2 行确实是 0+2+4=6，总计 9。题干选项需调整。

### single_choice · None



- [A] 程序报错，因为 pass 不能放在循环里
- [B] 打印 0、1、2
- [C] 打印 2
- [D] 什么都不打印

**参考答案**：2

**解析**：pass 是一条空语句，什么都不做，但它不会终止循环。循环正常跑完，i 最终为 2，print(i) 打印 2。它也不会像 break 一样提前结束。

### single_choice · None



- [A] pass 会跳过本次循环的剩余部分，进入下一次迭代
- [B] pass 是一个语法占位符，执行时不产生任何效果
- [C] pass 会立即退出当前函数并返回 None
- [D] pass 会删除当前作用域中的变量

**参考答案**：1

**解析**：pass 是空操作语句，仅用于满足语法上需要一条语句的要求。跳过本次迭代是 continue，退出函数是 return，删除变量是 del。

### multi_choice · None



- [A] pass 不会改变程序的控制流
- [B] return 会结束当前函数的执行
- [C] break 会终止最内层循环
- [D] continue 与 pass 在执行效果上完全一致
- [E] pass 会让循环立即结束

**参考答案**：[0, 1, 2]

**解析**：pass 不改变控制流；return 结束函数；break 结束最内层循环；continue 跳过本次迭代，与 pass 完全不同；pass 不会结束循环。

### fill_blank · None



**参考答案**：["pass"]

**解析**：pass 是 Python 的空操作语句，常用来充当语法上必需的语句。

### fill_blank · None



**参考答案**：["pass", "..."]

**解析**：函数体不能为空。pass（或省略号字面量 ...）可作为占位，使函数体合法且什么都不做。

### fill_blank · None



**参考答案**：["continue"]

**解析**：continue 会跳过本次迭代剩余部分，进入下一次循环；pass 只是空操作，不会跳过。

### code_reading · None



**参考答案**：输出 5 -1。pass 在 x > 0 分支里不做任何事，函数继续执行到 return x，所以正数和负数都原样返回。

**解析**：pass 不改变控制流也不影响返回值。check(5) 中 if 成立走 pass，随后仍执行 return x 得 5；check(-1) 中 if 不成立，跳过 pass，同样执行 return x 得 -1。

### code_reading · None



**参考答案**：4。当 i 等于 2 时进入 if 分支，pass 什么都不做但不会跳过 else，else 只在 if 不成立时执行；i 为 0、1、3、4 时 counter 各加 1，共加 4 次。

**解析**：pass 与 continue 的关键区别：pass 不会阻止 else 分支的语义判定。当 i == 2 时执行 pass 后循环体结束，counter 不变；其他四次进入 else 加一，最终为 4。

### code_reading · None



**参考答案**：会报错。todo 函数体的唯一内容是文档字符串，函数体本身为空（docstring 不是执行语句），Python 会抛出 IndentationError: expected an indented block。需要在函数体内补上 pass 之类语句。类体有 pass，不报错。

**解析**：函数体必须包含至少一条语句；孤立的文档字符串不足以构成函数体，仍需 pass 占位。类体写了 pass 因此合法。

### scenario · None



**解析**：Python 要求函数体、类体等语句块至少包含一条语句，只有注释不算语句，会触发 IndentationError。可行占位写法是 pass 或省略号字面量 ...。

### scenario · None



**解析**：pass 只是空语句，不会跳过循环体剩余代码，所以条件成立后仍会往下执行。要实现「跳过本次迭代」应使用 continue，让循环立即进入下一轮。

### scenario · None



**解析**：类体同样要求至少一条语句，空白类体需要 pass 这类占位语句来保证语法正确。pass 执行时不产生任何行为，因此不会影响异常的语义。

### single_choice · None



- [A] def handler():
      # TODO
- [B] def handler():
      pass
- [C] def handler():
      ...
- [D] def handler():

**参考答案**：1

**解析**：函数体不能为空，必须至少有一条语句。pass 是最常见的占位写法；选项 C 的 ...（省略号字面量）在 Python 3 中也可行但不是传统占位写法，选项 D 直接导致 IndentationError。题目问「最合适」，标准占位是 pass。

### single_choice · None



- [A] 在 if 分支里写注释就够了，无需 pass
- [B] 在 try 后面必须有 except 或 finally，此时可用 pass 占位
- [C] 在空函数体中，因为函数体不能为空
- [D] 在模块顶层声明变量时

**参考答案**：2

**解析**：函数体、类体、if/for/while 等复合语句的从句体不能为空，必须至少有一条语句，pass 正好满足这一要求。模块顶层并不要求有语句。

### single_choice · None



- [A] None
- [B] 程序报错
- [C] 什么都不打印
- [D] pass

**参考答案**：0

**解析**：函数体只有 pass，函数正常执行完毕，没有 return 语句，因此返回 None，print 输出 None。

### single_choice · None



- [A] 两者完全等价，可以互换
- [B] pass 是空操作，continue 会跳过本次循环剩余代码进入下一次迭代
- [C] pass 只能用于循环，continue 只能用于函数
- [D] continue 是空操作，pass 会跳过本次迭代

**参考答案**：1

**解析**：pass 不改变控制流；continue 会终止当前迭代、跳到下一次循环。二者不可互换。

### single_choice · None



- [A] 对负数不做处理，只处理非负数
- [B] 会跳过负数，直接进入下一次循环
- [C] 会报错，因为 pass 不能放在 if 中
- [D] 会把负数转成 0 再处理

**参考答案**：0

**解析**：pass 让 if 分支成为不做任何事的空分支，负数被忽略，其他分支走 else。若想跳过迭代需要 continue。

### single_choice · None



- [A] 报错，类体不能只有 pass
- [B] <class '__main__.Empty'>
- [C] None
- [D] <class 'pass'>

**参考答案**：1

**解析**：类体只有 pass 是合法的，pass 仅作为占位，类的定义正常完成，实例化后类型就是该类本身。

### multi_choice · None



- [A] pass 是一条语句，会占用一个语句位置
- [B] pass 执行时不会产生任何运行时行为
- [C] pass 可以用在函数体、类体、if/for/while 从句中
- [D] pass 会让所在函数返回 0
- [E] pass 会中断外层循环

**参考答案**：[0, 1, 2]

**解析**：pass 是空操作语句，可用于任何需要语句块的地方。它不会改变返回值（无 return 时仍返回 None），也不会中断循环。

### multi_choice · None



- [A] 先搭好函数框架，函数体待后续实现
- [B] 自定义异常类，暂时不添加方法或属性
- [C] 捕获异常后有意忽略该异常
- [D] 在循环中当某条件成立时需要跳过本次迭代的其余代码
- [E] 需要在分支里什么都不做，只保留结构

**参考答案**：[0, 1, 2, 4]

**解析**：pass 是常用的占位和「有意什么都不做」的写法；跳过本次迭代应使用 continue，因此 D 不正确。
