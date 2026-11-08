# s1u5l1 Python 函数定义 `def`：从直觉到工程 / `return` 是函数把计算结果**交还给调用者**的 / Python 函数作用域（Function Scope）

> 来源 `content/lessons/s1u5l1.json`

## py.func.def

# Python 函数定义 `def`：从直觉到工程

## 一句话直觉

**`def` 是你给一段逻辑「起名字、定输入、说输出」的工具**——有了它，你才能把代码从「一次性脚本」升级为「可复用、可测试、可组合」的工程模块。

---

## 第 1 节：为什么需要函数？——从重复到抽象

假设你要计算三个不同半径圆的面积：

```python
r1, r2, r3 = 1.0, 2.0, 3.0
area1 = 3.14159 * r1 ** 2
area2 = 3.14159 * r2 ** 2
area3 = 3.14159 * r3 ** 2
```

问题很明显：公式重复、π 硬编码、改一处要改三处。函数（function）让我们把「一段逻辑」打包并命名：

```python
def circle_area(radius):
    """返回给定半径的圆面积。"""
    return 3.14159 * radius ** 2

print(circle_area(1.0))
print(circle_area(2.0))
```

**关键结论**：函数 = 名字 + 参数（parameter） + 函数体（body） + 返回值（return value）。

---

## 第 2 节：`def` 的语法解剖

一个完整的函数定义包括五个部分：

```python
def 函数名(形参1, 形参2=默认值, *args, **kwargs) -> 返回类型标注:
    """文档字符串（docstring）。"""
    函数体
    return 结果
```

逐项说明：

- **`def`**：关键字，宣告「接下来是函数定义」。
- **函数名**：遵循 `snake_case`，动词开头（`compute_total`、`parse_json`）。
- **形参**（parameter）：函数内部使用的占位符。调用时传入的实际值叫实参（argument）。
- **`return`**：结束函数并把结果交回调用方；没有 `return` 时默认返回 `None`。
- **类型标注**（type annotation）：`-> int` 只是给人类和类型检查器（type checker）看的，运行时不强制。

```python
def greet(name: str, punct: str = "!") -> str:
    """生成问候语。punct 有默认值，可不传。"""
    return f"Hello, {name}{punct}"

print(greet("Ada"))          # Hello, Ada!
print(greet("Ada", "?"))    # Hello, Ada?
```

---

## 第 3 节：参数的四种形态

Python 的参数系统非常灵活，工程里最常用四种：

1. **位置参数**（positional）：按顺序传入。
2. **关键字参数**（keyword）：按名字传入，顺序无关。
3. **默认参数**（default）：不传时用默认值。
4. **可变参数**（`*args` / `**kwargs`）：接收任意数量的位置/关键字参数。

```python
def log(level, msg, *tags, sep=" | ", **extra):
    """level 和 msg 必填；tags 收集多余位置参数；extra 收集多余关键字参数。"""
    tag_str = sep.join(tags) if tags else "-"
    extra_str = ", ".join(f"{k}={v}" for k, v in extra.items())
    print(f"[{level}] {msg} (tags: {tag_str}) {extra_str}")

log("INFO", "started")
log("WARN", "slow", "db", "api", user="alice", retry=3)
```

**经验法则**：参数顺序应是「必填 → 有默认 → `*args` → `**kwargs`」；调用方尽量用关键字传参提高可读性。

---

## 第 4 节：作用域、返回值、`None` 与及早返回

函数内部定义的变量属于**局部作用域**（local scope），函数外看不到；函数能读全局变量但不该改写（否则易出 bug）。

`return` 不止能带回值，还能提前退出，避免深层嵌套——这叫「及早返回」（early return）：

```python
def grade(score: int) -> str:
    """根据分数返回等级；先处理异常情况，再走主逻辑。"""
    if not isinstance(score, int):
        return "invalid"
    if score < 0 or score > 100:
        return "invalid"
    if score >= 90:
        return "A"
    if score >= 60:
        return "B"
    return "C"

print(grade(95), grade(72), grade(-1))
```

**关键结论**：没有 `return` 的函数返回 `None`，这是 Python 的既定约定，别把它当成「没有返回值」。

---

## 第 5 节：函数是「一等公民」

在 Python 里函数本身也是对象：可以赋给变量、作为参数传入、从函数里返回。这是装饰器（decorator）、回调（callback）、高阶函数（higher-order function）的基础。

```python
def apply_twice(fn, x):
    """把 fn 连续应用两次：fn(fn(x))。"""
    return fn(fn(x))

def inc(n):
    return n + 1

print(apply_twice(inc, 10))  # 12
print(apply_twice(lambda s: s * 2, "ab"))  # abababab
```

到这里你已经能写出工业级别的函数：命名清晰、类型标注齐全、参数灵活、能作为参数传递。

---

## 动手练习

**任务：写一个 `analyze_scores` 函数，报告一组成绩的统计信息。**

要求：

1. 函数签名：`def analyze_scores(*scores: int, pass_line: int = 60) -> dict:`
2. 返回一个字典，包含以下键：
   - `count`：成绩个数
   - `pass_count`：及格数量（`>= pass_line`）
   - `average`：平均分（保留两位小数）
   - `highest` / `lowest`：最高/最低分
3. 若 `scores` 为空，返回 `{"error": "no scores"}`。
4. 在文件底部写 3 个测试调用（含空参数、正常参数、自定义 `pass_line`），并把结果 `print` 出来。

参考自测点：

- `analyze_scores()` 是否返回 `{"error": "no scores"}`？
- `analyze_scores(90, 80, 55, 70)` 的 `average` 是否为 `73.75`？
- `analyze_scores(90, 80, pass_line=85)` 的 `pass_count` 是否为 `1`？

完成后，试着给每个函数都加上 `"""docstring"""` 并对 `pass_line` 做合法性检查（例如必须为 0~100 的整数）。这就是从「会写函数」到「工程级函数」的最后一步。

```python
def analyze_scores(*scores: int, pass_line: int = 60) -> dict:
    """汇总成绩统计。scores 为空时返回错误字典。"""
    if not scores:
        return {"error": "no scores"}
    count = len(scores)
    pass_count = sum(1 for s in scores if s >= pass_line)
    average = round(sum(scores) / count, 2)
    return {
        "count": count,
        "pass_count": pass_count,
        "average": average,
        "highest": max(scores),
        "lowest": min(scores),
    }

print(analyze_scores())
print(analyze_scores(90, 80, 55, 70))
print(analyze_scores(90, 80, pass_line=85))
```

## py.func.return

## 一句话直觉

`return` 是函数把计算结果**交还给调用者**的唯一出口——没有它，函数做完事就“人间蒸发”，有了它，函数才能像积木一样拼接成程序。

---

## 1. 最小模型：函数是一台“投币机”

把函数想象成一台投币机：你投入参数（硬币），它内部运转（执行语句），最后掉出一个结果——那个掉出来的东西就是 `return` 送出的值。

```python
def add(a, b):
    return a + b          # 把 a+b 的结果交还出去

result = add(3, 5)        # result 接住返回值
print(result)             # 8
```

关键结论：
- `return` 后面可以跟任意表达式，Python 先求值再返回。
- 函数体执行到 `return` 就**立即结束**，后面的语句不会再执行。

```python
def check(x):
    if x > 0:
        return "正数"     # 一旦满足，函数到此结束
    return "非正数"       # 只有上面没返回才会走到这里
```

---

## 2. 没有 return 会怎样？——返回 None

如果函数执行完毕都没有遇到 `return`，Python 自动返回 `None`（空值）。`None` 不是“没有”，而是一个真实存在的对象，表示“没有有意义的值”。

```python
def say_hello(name):
    print(f"Hello, {name}")   # 只打印，没有 return

value = say_hello("Alice")    # 打印 Hello, Alice
print(value)                  # None —— 函数默认的返回值
```

关键结论：
- 只做副作用（打印、写文件）的函数可以不写 `return`，但调用者拿到的是 `None`。
- 不返回值的函数常用于“执行动作”，返回值不为 `None` 的函数常用于“产出数据”。

---

## 3. 一次返回多个值？——其实是元组

Python 允许 `return a, b`，看起来像返回多个值，本质上是返回一个**元组（tuple）**，调用者可以用解包接收。

```python
def min_max(nums):
    return min(nums), max(nums)   # 等价于 return (min(nums), max(nums))

low, high = min_max([4, 1, 9, 3])  # 解包
print(low, high)                   # 1 9

pair = min_max([4, 1, 9, 3])
print(pair, type(pair))            # (1, 9) <class 'tuple'>
```

关键结论：
- `return a, b` 返回的是元组，不是两个独立对象。
- 调用方可以选择解包，也可以整体接收。

---

## 4. return 终止函数：提前退出的工程价值

`return` 可以出现在函数任意位置，用于**提前退出**（early return），减少嵌套、提升可读性。这是工程代码里最常见的模式之一。

```python
def safe_divide(a, b):
    if b == 0:
        return None        # 提前退出，避免后面除零
    return a / b

print(safe_divide(10, 2))  # 5.0
print(safe_divide(10, 0))  # None
```

关键结论：
- 用 `return` 做“守卫条件”（guard clause）可以让主逻辑保持平坦。
- 提前返回不会执行后续代码，因此可以安全地跳过不合法路径。

---

## 5. 返回 self：链式调用与类型注解的工程细节

在面向对象中，方法可以返回 `self`，从而实现**链式调用（method chaining）**。当你要为这种返回值写类型注解时，Python 3.11 引入了 `typing.Self`，表示“返回当前类的实例（子类也适用）”。

```python
from typing import Self

class Builder:
    def __init__(self):
        self.parts = []

    def add(self, part: str) -> Self:   # 返回自身，子类也适用
        self.parts.append(part)
        return self

    def build(self) -> str:
        return "-".join(self.parts)

result = Builder().add("a").add("b").add("c").build()
print(result)   # a-b-c
```

为什么不用类名 `Builder` 而用 `Self`？
- 如果写 `-> "Builder"`，子类调用时类型检查器会认为返回的是 `Builder`，丢掉子类信息。
- 用 `Self` 则能保留“当前实际类型”，对子类也正确。

但注意：如果方法**永远返回固定类的实例**（不随子类变化），就不该用 `Self`。例如：

```python
class Eggs:
    def returns_eggs(self) -> "Eggs":   # 总是 Eggs，不能用 Self
        return Eggs()
```

关键结论：
- 返回 `self` 时，注解用 `Self` 更准确。
- 返回固定类型实例时，不要用 `Self`。
- `Self` 在 Python 3.11+ 可用，来自 PEP 673。

---

## 6. 返回值的类型注解与工具函数

给返回值写类型注解（type hint）能帮助编辑器、类型检查器（如 mypy）理解代码。常见写法：

```python
def greet(name: str) -> str:
    return f"Hi, {name}"

def find(nums: list[int], target: int) -> int | None:
    for i, n in enumerate(nums):
        if n == target:
            return i
    return None
```

如果你需要在运行时**检查**某个函数的返回值注解，可以用 `typing.get_type_hints()`：

```python
from typing import get_type_hints

def f(x: int) -> str:
    return str(x)

print(get_type_hints(f))   # {'x': <class 'int'>, 'return': <class 'str'>}
```

关键结论：
- 返回值注解是文档+工具支持，不影响运行时行为。
- `get_type_hints` 可以把字符串形式的注解解析成真正的类型对象。

---

## 7. 动手练习

**任务：实现一个“安全整数除法器”，并练习 return 的多种用法。**

在本地新建 `practice_return.py`，完成：

1. 写函数 `safe_div(a: int, b: int) -> float | None`：
   - 若 `b == 0`，返回 `None`。
   - 否则返回 `a / b`。
2. 写函数 `divmod_safe(a: int, b: int) -> tuple[int, int] | None`：
   - 若 `b == 0`，返回 `None`。
   - 否则返回 `(a // b, a % b)`（一次 return 返回两个值）。
3. 写一个类 `Calc`，包含方法 `add(self, x: int) -> Self`，把 x 累加到 `self.total` 并返回 `self`，实现链式调用：
   - `Calc().add(1).add(2).add(3).total` 应得到 `6`。
4. 用 `get_type_hints` 打印 `safe_div` 的返回值注解。

示例骨架：

```python
from typing import Self, get_type_hints

def safe_div(a: int, b: int) -> float | None:
    ...

def divmod_safe(a: int, b: int) -> tuple[int, int] | None:
    ...

class Calc:
    def __init__(self):
        self.total = 0
    def add(self, x: int) -> Self:
        ...

if __name__ == "__main__":
    print(safe_div(10, 2))
    print(safe_div(10, 0))
    print(divmod_safe(10, 3))
    print(Calc().add(1).add(2).add(3).total)
    print(get_type_hints(safe_div))
```

完成后运行 `python practice_return.py`，确认输出与预期一致。

```python
from typing import Self, get_type_hints

# 1. 基本 return：把结果交还给调用者
def add(a, b):
    return a + b

print(add(3, 5))  # 8

# 2. 没有 return 默认返回 None
def say_hello(name):
    print(f"Hello, {name}")

value = say_hello("Alice")
print(value)  # None

# 3. return 多个值：本质是元组
def min_max(nums):
    return min(nums), max(nums)

low, high = min_max([4, 1, 9, 3])
print(low, high)  # 1 9

# 4. 提前 return 做守卫条件
def safe_div(a: int, b: int) -> float | None:
    if b == 0:
        return None
    return a / b

print(safe_div(10, 2))  # 5.0
print(safe_div(10, 0))  # None

# 5. 返回 self 实现链式调用，注解用 Self
class Builder:
    def __init__(self):
        self.parts = []

    def add(self, part: str) -> Self:
        self.parts.append(part)
        return self

    def build(self) -> str:
        return "-".join(self.parts)

print(Builder().add("a").add("b").add("c").build())  # a-b-c

# 6. 查看返回值类型注解
print(get_type_hints(safe_div))  # {'a': <class 'int'>, 'b': <class 'int'>, 'return': float | None}
```

## py.func.scope

# Python 函数作用域（Function Scope）

## 一句话直觉

**函数作用域（function scope）** 就是函数内部那块“私有领地”：名字在哪定义，决定了它在哪能被看见、被修改，写错一步就会 出现 `UnboundLocalError` 或“改了变量但外面没变”的诡异现象。理解作用域，是写出可维护代码、避免 Python 中最常见 bug 的起点。

---

## 一、为什么要有作用域

如果所有变量都共享同一片内存空间，那么任意两个函数使用同一个变量名（例如 `i`、`data`、`result`）就会相互污染。作用域（scope）给每个名字划出可见范围，Python 通过 **LEGB 规则** 决定一个名字到底指向谁：

- **L**ocal：当前函数内部
- **E**nclosing：外层函数（闭包，closure）
- **G**lobal：模块全局
- **B**uilt-in：内置命名空间（如 `print`、`len`）

查找顺序是 L → E → G → B，找到就停。

```python
# 演示 LEGB：同一个名字在四个层级的查找顺序
value = "global"          # G

def outer():
    value = "enclosing"   # E

    def inner():
        value = "local"   # L
        print(value)      # 输出 local

    inner()
    print(value)          # 输出 enclosing

outer()
print(value)              # 输出 global
print(len("abc"))         # len 来自 B（built-in）
```

> 结论：**变量名在哪一层被赋值，就在哪一层被创建**。函数内的赋值不会自动影响外层。

---

## 二、局部变量与 `global` / `nonlocal`

默认情况下，函数里对一个名字“赋值”会把它登记为**局部变量（local variable）**——即使外部已经有同名变量。这就是最经典的坑：

```python
# 错误示范：函数内赋值会让 count 变成局部变量，读取时先于赋值 → 报错
def bad_counter():
    print(count)   # UnboundLocalError: 因为下面有 count = ...
    count = 1

count = 10
# bad_counter()  # 取消注释即可复现
```

要让函数真正修改全局或外层变量，需要显式声明：

```python
# global：声明操作的是模块级变量
total = 0

def add_to_total(n):
    global total          # 告诉 Python：total 是全局的
    total += n

add_to_total(3)
add_to_total(5)
print(total)              # 8

# nonlocal：声明操作的是外层函数的变量
def make_counter():
    count = 0
    def step():
        nonlocal count    # 指向 make_counter 里的 count
        count += 1
        return count
    return step

c = make_counter()
print(c(), c(), c())      # 1 2 3
```

> 关键区别：`global` 向上找模块级，`nonlocal` 向上找最近的**外层函数**级。两者都不能跨越模块边界。

---

## 三、闭包（Closure）与延迟绑定

当一个内层函数引用了外层函数的变量，并作为对象返回时，外层变量不会随外层函数结束而消失——它被内层函数“记住”了，这就是闭包。

```python
# 闭包：inner 记住了 factor
def make_multiplier(factor):
    def multiply(x):
        return x * factor
    return multiply

double = make_multiplier(2)
triple = make_multiplier(3)
print(double(10), triple(10))   # 20 30
print(double.__closure__[0].cell_contents)  # 2

def make_multiplier_safe(self, factor: int) -> int:
    return factor * self.value
```

**延迟绑定（late binding）** 是闭包的经典陷阱：循环里创建的多个函数共享同一个变量，循环结束后它们都看到同一个“最后值”。

```python
# 陷阱：所有函数都返回 3
funcs = [lambda: i for i in range(3)]
print([f() for f in funcs])   # [2, 2, 2]

# 修复 1：用默认参数“冻结”当前值
funcs = [lambda i=i: i for i in range(3)]
print([f() for f in funcs])   # [0, 1, 2]

# 修复 2：用工厂函数制造独立作用域
def make_fn(i):
    return lambda: i
funcs = [make_fn(i) for i in range(3)]
print([f() for f in funcs])   # [0, 1, 2]
```

> 结论：闭包捕获的是**变量本身**，不是变量的值；要捕获“当下的值”，就用默认参数或额外一层函数。

---

## 四、默认参数的求值时机（作用域相关工程陷阱）

默认参数在**函数定义时**求值一次，而不是每次调用时。这意味着可变默认值会在多次调用之间被“共享”：

```python
# 陷阱：默认列表只创建一次
def append_bad(x, bucket=[]):
    bucket.append(x)
    return bucket

print(append_bad(1))   # [1]
print(append_bad(2))   # [1, 2]  ← 不是预期的 [2]

# 正确写法：默认用 None，调用时再创建
def append_ok(x, bucket=None):
    if bucket is None:
        bucket = []
    bucket.append(x)
    return bucket

print(append_ok(1))    # [1]
print(append_ok(2))    # [2]
```

这看起来像“默认值”问题，本质是**函数定义时的作用域快照**——默认值表达式在定义那一刻、在外层作用域里只求值一次。

---

## 五、`globals()`、`locals()` 与调试视角

想知道运行时作用域里到底有什么，可以用两个内置函数观察：

```python
GLOBAL_FLAG = "g"

def inspect_scope():
    local_x = 1
    print("locals:", locals())
    print("global GLOBAL_FLAG:", globals()["GLOBAL_FLAG"])

inspect_scope()
# locals: {'local_x': 1}
# global GLOBAL_FLAG: g
```

工程实践中，遇到 `UnboundLocalError`、`NameError`，先用 `locals()` / `globals()` 打印当下名字表，几乎立刻能定位问题。

---

## 结尾：动手练习

**任务：写一个 `make_account(initial)` 函数**，返回一个“账户”对象（用函数模拟即可），要求：

1. 内部用 `nonlocal balance` 维护余额；
2. 返回一个字典，包含 `deposit`、`withdraw`、`balance` 三个函数；
3. `deposit(n)` 加钱并返回新余额；`withdraw(n)` 若余额不足返回 `None`，否则扣钱并返回新余额；`balance()` 返回当前余额；
4. 创建两个独立账户，验证它们互不影响；
5. 思考：如果把 `nonlocal balance` 换成 `global balance`，行为会怎样变？

参考骨架（请自行补全）：

```python
def make_account(initial):
    balance = initial
    def deposit(n):
        ...
    def withdraw(n):
        ...
    def get_balance():
        ...
    return {"deposit": deposit, "withdraw": withdraw, "balance": get_balance}
```

```python
def make_account(initial):
    """用闭包模拟一个独立账户。"""
    balance = initial

    def deposit(n):
        nonlocal balance          # 修改外层函数的 balance
        balance += n
        return balance

    def withdraw(n):
        nonlocal balance
        if n > balance:
            return None           # 余额不足
        balance -= n
        return balance

    def get_balance():
        return balance            # 只读，无需 nonlocal

    return {"deposit": deposit, "withdraw": withdraw, "balance": get_balance}


a = make_account(100)
b = make_account(0)

print(a["deposit"](50))     # 150
print(a["withdraw"](30))    # 120
print(a["balance"]())       # 120
print(b["balance"]())       # 0    ← 与 a 完全隔离
print(a["withdraw"](999))   # None ← 余额不足

# 演示 global vs nonlocal 的区别
flag = "outer"
def demo_nonlocal():
    flag = "inner"
    def change():
        nonlocal flag
        flag = "changed-by-nonlocal"
    change()
    return flag

print(demo_nonlocal())       # changed-by-nonlocal
print(flag)                  # outer（全局未变）
```


---

## 本课题目

### single_choice · None



- [A] 输出 hi
- [B] 报错，因为 greet 必须先加括号再赋值
- [C] 输出 <function greet at ...>
- [D] 什么都不输出，因为没有调用 greet()

**参考答案**：0

**解析**：函数名本身是一个函数对象，x = greet 只是给同一个函数对象绑定了另一个名字，x() 等价于调用 greet()，因此输出 hi。

### single_choice · None



- [A] 形参在调用时提供，实参在定义时声明
- [B] 形参在定义时声明，实参在调用时提供
- [C] 两者完全同义，可以互换使用
- [D] 形参一定是关键字参数，实参一定是位置参数

**参考答案**：1

**解析**：形参（parameter）出现在 def 语句的括号里，是定义时的占位名；实参（argument）是调用时真正传入的值。

### single_choice · None



- [A] 1
  unreachable
- [B] unreachable
  1
- [C] 1
- [D] 报错

**参考答案**：2

**解析**：return 之后的语句不会被执行，函数返回 1。

### single_choice · None



- [A] 函数名必须唯一
- [B] 函数可以赋值给变量、作为参数传递、作为返回值返回
- [C] 函数只能定义在模块顶层
- [D] 函数不能被删除

**参考答案**：1

**解析**：一等对象意味着函数可以像普通值一样被赋值、传递和返回。

### single_choice · None



- [A] 5
- [B] 10
- [C] 15
- [D] 报错，add 在外部不可见

**参考答案**：2

**解析**：make 返回内部函数 add，通过闭包捕获 n=10，调用 g(5) 得 15。

### single_choice · None



- [A] 直接赋值 total = 0 即可
- [B] 在函数内使用 global total 声明后再赋值
- [C] 在函数内使用 nonlocal total 声明后再赋值
- [D] 无法修改，只能通过返回值

**参考答案**：1

**解析**：修改模块级变量需用 global 声明；nonlocal 只用于外层函数作用域的变量。

### single_choice · None



- [A] 0 0
- [B] 1 2
- [C] 1 1
- [D] 报错

**参考答案**：1

**解析**：nonlocal 使 inner 修改 outer 的局部变量 x，闭包保留状态，因此依次得到 1 和 2。

### single_choice · None



- [A] 每次调用函数时都会重新求值
- [B] 在 def 语句执行时求值一次，并作为函数对象的一部分保存
- [C] 在模块导入完成后统一求值
- [D] 在第一次调用时才求值

**参考答案**：1

**解析**：默认参数值在 def 执行时求值一次，因此使用可变对象作为默认值可能产生共享副作用。

### single_choice · None



- [A] f(1, 2)
- [B] f(a=1, b=2)
- [C] f(*[1, 2])
- [D] f(1, b=2)

**参考答案**：1

**解析**：/ 前的参数只能按位置传递，f(a=1, b=2) 试图用关键字传入位置限定参数，会报错。

### single_choice · None



- [A] b 只能按位置传递
- [B] b 是仅关键字参数，调用时必须写成 b=...
- [C] args 可以接收关键字参数
- [D] kw 会覆盖 b 的值

**参考答案**：1

**解析**：在 *args 之后定义的参数是仅关键字参数，只能通过关键字传入；args 只收集位置实参。

### single_choice · None



- [A] 必须用 # 开头
- [B] 函数体第一条语句若为字符串字面量，则成为 __doc__
- [C] 只能写在函数外部
- [D] 会被编译器完全忽略，无法访问

**参考答案**：1

**解析**：函数体首条字符串语句会作为 __doc__ 属性保存，可通过 help() 等查看。

### single_choice · None



- [A] 语法错误
- [B] 函数作为实参传递，输出 5
- [C] 输出 5，因为 len 是关键字
- [D] 运行时报错，len 不能被传递

**参考答案**：1

**解析**：函数是对象，可以像普通值一样作为实参传入；len("hello") 返回 5。

### single_choice · None



- [A] -7
- [B] 7
- [C] TypeError
- [D] 13

**参考答案**：1

**解析**：关键字实参按名字绑定，a=10、b=3，return a - b 得 7，与书写顺序无关。

### single_choice · None



- [A] 每次调用 f() 时，函数体都会重新被 Python 解析一次
- [B] 定义 f 时只创建函数对象，函数体内的代码在调用时才执行
- [C] 函数体在定义时立即执行一次，之后不再执行
- [D] 函数体在编译阶段执行

**参考答案**：1

**解析**：def 语句执行时创建函数对象并把函数体编译为代码对象，函数体只在调用时才执行。

### single_choice · None



- [A] 3 7
- [B] 2 5
- [C] 3 3
- [D] TypeError

**参考答案**：0

**解析**：b 有默认值 1，add(2) 使用默认值得 3；add(2, 5) 用 5 覆盖默认值得 7。

### single_choice · None



- [A] 正常运行
- [B] 报 SyntaxError，因为带默认值的参数后面出现无默认值参数
- [C] 运行时报 TypeError
- [D] c 会自动获得默认值 0

**参考答案**：1

**解析**：Python 要求有默认值的参数必须位于无默认值参数之后，否则是语法错误。

### single_choice · None



- [A] (1, (2, 3))
- [B] ((1, 2, 3), ())
- [C] (1, [2, 3])
- [D] TypeError

**参考答案**：0

**解析**：*args 把多余的位置实参收集成元组，所以 x=1，args=(2, 3)。

### single_choice · None



- [A] {'a': 1, 'b': 2}
- [B] [( 'a', 1), ('b', 2)]
- [C] ('a', 'b')
- [D] TypeError

**参考答案**：0

**解析**：**kw 把多余的关键字实参收集成字典。

### single_choice · None



- [A] 把 nums 作为单个参数传入
- [B] 把 nums 中的元素依次展开为位置实参传入
- [C] 把 nums 展开为关键字实参
- [D] 等价于 f(nums)

**参考答案**：1

**解析**：调用处的 * 用于把可迭代对象拆包成多个位置实参。

### single_choice · None



- [A] 没有 return 语句的函数返回 None
- [B] 没有 return 语句的函数返回 0
- [C] 没有 return 语句的函数不能有 print
- [D] return 只能返回一个值

**参考答案**：0

**解析**：无 return 或执行到函数末尾时，隐式返回 None；return 可以通过逗号返回元组。

### single_choice · None



- [A] 正
- [B] 非正
- [C] None
- [D] 报错

**参考答案**：1

**解析**：x=0 不满足 x>0，跳过第一个 return，执行最后的 return "非正"，因此输出“非正”。一个函数遇到 return 就立即结束并返回该值。

### single_choice · None



- [A] 3
- [B] 6
- [C] None
- [D] 0

**参考答案**：2

**解析**：函数体执行完但没有遇到 return，Python 隐式返回 None。range(3) 累加 0+1+2=6，但这个值没有被返回，所以 r 是 None。

### multi_choice · None



- [A] 函数体为空（只有 pass）
- [B] 函数执行到末尾也没有 return
- [C] 使用不带值的 bare return
- [D] 函数末尾写了 return None
- [E] 函数中途触发异常且未被捕获

**参考答案**：[0, 1, 2, 3]

**解析**：前四种都会返回 None：pass 函数、执行到末尾、bare return、显式 return None。E 不会返回 None，异常若未被捕获会向上传播而不是返回 None。

### multi_choice · None



- [A] return a, b 返回的是一个元组，可用 a, b = f() 解包
- [B] return 可以返回列表、字典等可变对象
- [C] 调用方可以用变量接收返回值，也可以忽略返回值
- [D] return 语句会改变全局变量的值

**参考答案**：[0, 1, 2]

**解析**：return a, b 返回元组且支持解包；返回任意类型都行；接收返回值可选。D 错：return 只用于返回，不负责改变全局变量（除非函数内部本来就修改了全局变量）。

### fill_blank · None



**参考答案**：["return", "return "]

**解析**：函数要把累加结果交给调用方，必须用 return s 返回，否则调用结果为 None。

### fill_blank · None



**参考答案**：["1", "1 "]

**解析**：x=7 满足 else 分支，返回 1。三个分支覆盖了所有情况，每次调用必然会返回一个值。

### fill_blank · None



**参考答案**：["True", "true", " True"]

**解析**：空函数体（pass）执行到末尾也没有 return，隐式返回 None，因此 f() is None 为 True。

### code_reading · None



**参考答案**：第一行输出 even；第二行输出 None（因为 classify(5) 不满足 n%2==0，函数没有其它 return，隐式返回 None）。

**解析**：classify(4) 满足偶数条件返回 "even"；classify(5) 为奇数，if 不成立，函数执行到末尾没有 return，返回 None，所以第二行打印 None。

### code_reading · None



**参考答案**：输出 1。第一条 return 执行后函数立即结束并返回 1，其后的 return 2 是永远不会执行到的死代码。

**解析**：return 具有立即终止函数的语义，函数内后续语句不再执行，因此只返回 1。

### code_reading · None



**参考答案**：输出 2 1。函数 return b, a 返回元组 (2, 1)，调用方用 x, y 解包，因此 x=2、y=1。

**解析**：return b, a 等价于返回元组 (b, a)，即 (2, 1)；解包赋值后 x 得 2，y 得 1。

### scenario · None



**解析**：当 name 长度不足 3 时，if 不成立且函数没有其它 return，函数隐式返回 None。判断 if result 时，None 是假值（falsy），所以会走 else 打印“不通过”。但函数设计上应显式返回布尔值，应补上 return False，让返回类型一致，避免调用方后续对 None 做其它操作出错。

### scenario · None



**解析**：当循环结束都没找到匹配项时，函数没有 return，隐式返回 None。调用方执行 None >= 0 就会抛 TypeError。应该按约定在循环后补上 return -1，明确表示“找不到”的特殊值，保持返回类型一致。

### single_choice · None



- [A] int 1
- [B] tuple (1, 2)
- [C] list [1, 2]
- [D] 报错，函数只能返回一个值

**参考答案**：1

**解析**：return 1, 2 用逗号分隔多个值，实际返回的是一个元组 (1, 2)。Python 并没有真正的多返回值，只是返回元组后可以解包。

### single_choice · None



- [A] 大
- [B] 中
- [C] 小
- [D] None

**参考答案**：1

**解析**：x=5 不满足 x>10，进入第二个 if，满足 x>3，返回“中”并立即结束函数，不会继续执行下面的 return。

### single_choice · None



- [A] 返回 -1，因为循环结束后才返回
- [B] 返回 3，return 立即终止循环和函数
- [C] 输出 0 1 2 3
- [D] 报错，return 不能在循环中使用

**参考答案**：1

**解析**：当 i 等于 3 时执行 return i，函数立即结束，返回 3，既终止了循环也终止了函数，后面的 return -1 不会执行。

### single_choice · None



- [A] hello
- [B] None
- [C] hello
  None
- [D] 报错

**参考答案**：1

**解析**：bare return（无值的 return）会返回 None 并立即结束函数，其后的 print("hello") 是死代码不会执行，所以 print(f()) 输出 None。

### single_choice · None



- [A] 3
- [B] 2
- [C] -1
- [D] None

**参考答案**：1

**解析**：enumerate 给出下标，target=3 在列表中的下标是 2（元素 3 位于第 3 位，下标从 0 开始），命中时返回下标 2。

### single_choice · None



- [A] return 可以返回任意类型的对象
- [B] 函数没有 return 时默认返回 None
- [C] 一个 return 语句可以同时返回多个用逗号分隔的值
- [D] 函数一旦有 return，就一定会执行到它并返回对应值

**参考答案**：3

**解析**：return 只有在被执行到时才起作用。如果它位于条件分支或循环中而条件不满足，可能根本执行不到，此时函数返回 None 或其他分支的返回值。所以“一定会执行到”是错误的。

### single_choice · None



- [A] 10
- [B] 20
- [C] None
- [D] 报错

**参考答案**：0

**解析**：return x 执行后函数立即返回 10，后面的 x = 20 永远不会执行（死代码）。返回值在 return 那一刻就确定了。

### multi_choice · None



- [A] return 执行后函数立即结束，其后的语句不再执行
- [B] 函数没有 return 语句时，调用结果为 None
- [C] return 后面可以跟一个表达式，函数返回该表达式的值
- [D] 一个函数中最多只能出现一条 return 语句
- [E] return 只能返回数字类型

**参考答案**：[0, 1, 2]

**解析**：A、B、C 都正确。D 错：一个函数可以有多条 return（例如不同分支各自返回），只是每次调用只有一个会被执行。E 错：return 可返回任意类型。

### single_choice · None



- [A] 10
- [B] 报错 NameError
- [C] None
- [D] 0

**参考答案**：0

**解析**：函数体内部没有对 x 赋值，因此 x 不是局部变量，Python 会沿 LEGB 规则到外层（全局）作用域查找，找到全局 x = 10，所以打印 10。

### single_choice · None



- [A] 打印 10
- [B] 打印 20
- [C] 抛出 UnboundLocalError
- [D] 抛出 NameError

**参考答案**：2

**解析**：函数体内存在对 x 的赋值语句，编译时就把 x 判定为局部变量，整 个函数范围内 x 都是局部名。print(x) 在赋值之前执行，此时局部 x 尚未绑定，因此抛出 UnboundLocalError。

### multi_choice · None



- [A] 函数内部直接给某名字赋值会使其成为局部变量
- [B] global 声明可以让函数内部的赋值作用于全局变量
- [C] nonlocal 可以指向模块级（全局）变量
- [D] 读取全局变量不需要 global 声明
- [E] 闭包捕获的是变量本身而不是定义时的值

**参考答案**：[0, 1, 3, 4]

**解析**：A、B、D、E 均正确。C 错误：nonlocal 只能指向外层函数作用域，不能指向模块级全局变量，那需要用 global。

### multi_choice · None



- [A] 函数体内先读取某名字，之后再对该名字赋值
- [B] 函数体内只读取全局变量而不赋值
- [C] 函数体内对某名字赋值但未加 global，而全局存在同名变量
- [D] 函数体内使用 global 声明并赋值
- [E] 函数体内在 if 分支中赋值，运行时该分支未走到却读取该名字

**参考答案**：[0, 2, 4]

**解析**：只要函数体内某名字被赋值且未声明 global/nonlocal，它就是局部名。先读后写（A）或在未执行赋值分支前读取（E）都会触发 UnboundLocalError。C 中局部变量遮蔽了全局变量，若在赋值前读取也会触发。B、D 不会。

### multi_choice · None



- [A] 闭包可以访问定义它的外层函数的变量
- [B] 闭包捕获的是变量的当前值快照
- [C] 可通过 nonlocal 在闭包内修改外层函数变量
- [D] 循环中创建闭包常因共享变量而产生意外结果
- [E] 闭包只能访问全局变量

**参考答案**：[0, 2, 3]

**解析**：A、C、D 正确。B 错误：闭包按名字引用变量而非值快照；E 错误：闭包正是能访问外层函数变量才叫闭包。

### fill_blank · None



**参考答案**：["nonlocal"]

**解析**：nonlocal 用于声明名字绑定到最近的外层函数作用域，从而可在内层函数中修改外层函数变量。

### fill_blank · None



**参考答案**：["global"]

**解析**：global 声明告诉解释器该名字指向模块级全局变量，函数内的赋值会作用到全局名字上。

### fill_blank · None



**参考答案**：["Local, Enclosing, Global, Builtins", "local enclosing global builtins", "Local Enclosing Global Builtins"]

**解析**：LEGB 分别代表 Local（局部）、Enclosing（外层函数）、Global（全局）、Builtins（内置），查找按此顺序进行。

### code_reading · None



**参考答案**：第一行输出 changed，第二行输出 global

**解析**：g 中的 nonlocal x 指向 f 的局部变量 x，把它改为 'changed'，因此 f 返回 'changed'。全局 x 未受影响，仍是 'global'。

### code_reading · None



**参考答案**：[0, 1, 2]

**解析**：这里是在每次循环中立即调用 inner() 并把返回值追加到列表，而不是保存函数对象，因此取到的是当时的 i 值，输出 [0, 1, 2]。与保存 lambda 对象的延迟调用不同。

### scenario · None



**解析**：函数体内对 config 进行了赋值（config[key] = value 实际上是 config 的方法调用，但对 config 名本身没有重新绑定……此处真正的问题常见于写成 config = {...} 之类导致 config 变局部）。标准处理是：若函数内对 config 名做了重新绑定赋值，需用 global config 声明，使赋值作用于全局变量；若只是对全局对象做原地修改（如下标赋值）则无需 global。答案需指出赋值使名字变局部，需要 global 声明来指向全局。

### scenario · None



**解析**：原因是闭包按名字捕获循环变量而非其值，循环结束后所有 lambda 看到的是同一个变量的最终值。修复一：用默认参数绑定当前值，如 lambda i=i: i；修复二：用工厂函数接收当前值作为参数，每次调用生成一个新的闭包，从而各 lambda 捕获不同的局部变量。

### single_choice · None



- [A] 读取全局变量必须先声明 global，否则报错
- [B] 读取全局变量无需声明，直接按名字查找即可
- [C] 读取全局变量必须用 globals() 显式取出
- [D] 函数无法读取全局变量

**参考答案**：1

**解析**：global 声明只在需要在函数内部对全局名重新绑定（赋值）时才需要。仅读取全局变量时，LEGB 查找会自动找到它。

### single_choice · None



- [A] 0
- [B] 1
- [C] 2
- [D] 报错

**参考答案**：2

**解析**：global count 使 count += 1 直接修改全局变量，调用两次后全局 count 变为 2。

### single_choice · None



- [A] 1
- [B] 2
- [C] 报错 NameError
- [D] None

**参考答案**：1

**解析**：nonlocal n 让 inner 绑定到外层函数 outer 的局部变量 n，而不是创建新的局部变量，因此 n 自增为 2。

### single_choice · None



- [A] 任意层级的全局作用域
- [B] 最近的外层函数作用域中的同名变量
- [C] 内置作用域
- [D] 必须指向模块级变量

**参考答案**：1

**解析**：nonlocal 用于把名字绑定到最近的外层函数作用域（不含全局和内置），不能绑定全局名。

### single_choice · None



- [A] [0, 1, 2]
- [B] [2, 2, 2]
- [C] [3, 3, 3]
- [D] [0, 0, 0]

**参考答案**：1

**解析**：闭包捕获的是变量 i 本身而非其当时的值，循环结束后 i 为 2，三个 lambda 都读取同一个 i，因此输出 [2, 2, 2]。

### single_choice · None



- [A] [0, 1, 2]
- [B] [2, 2, 2]
- [C] [3, 3, 3]
- [D] [报错]

**参考答案**：0

**解析**：通过默认参数 i=i 在每次循环时把当前值绑定到该 lambda 的局部默认参数上，从而打破对循环变量的共享引用，输出 [0, 1, 2]。

### single_choice · None



- [A] 最先查找，优先级最高
- [B] 最后查找，优先级最低
- [C] 与全局作用域同级，随机选择
- [D] 不参与名字查找

**参考答案**：1

**解析**：LEGB 中 B 指 builtins，查找顺序为 Local -> Enclosing -> Global -> Builtins，内置名字优先级最低。

### single_choice · None



- [A] [1] 然后 [2]
- [B] [1] 然后 [1, 2]
- [C] [1, 2] 然后 [1, 2]
- [D] 报错

**参考答案**：1

**解析**：默认参数在函数定义时只求值一次，lst 指向同一个可变列表对象，第二次调用会继续在同一个列表上追加，因此输出 [1] 和 [1, 2]。
