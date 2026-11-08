# s1u5l5 闭包 (Closure)：让函数带着它的记忆一起走 / Python 函数作用域与 LEGB 规则

> 来源 `content/lessons/s1u5l5.json`

## py.func.closure

# 闭包 (Closure)：让函数带着它的记忆一起走

**一句话直觉**：闭包就是一个函数“记住”了它出生时周围环境里的变量，即使离开了那个环境，也能继续访问这些变量。它是装饰器、回调、工厂函数等大量 Python 高级技巧的底层基石。

---

## 1. 从“函数内部嵌套函数”说起

在 Python 里，函数可以定义在另一个函数内部。内部函数可以访问外部函数的局部变量，这就是闭包的起点。

```python
def outer():
    msg = "hello"
    def inner():
        print(msg)   # inner 读取了 outer 的局部变量 msg
    inner()

outer()   # 输出：hello
```

但此时 `inner` 只是在 `outer` 内被调用了，还不算真正的闭包“逃逸”。

---

## 2. 闭包的核心：函数“带走”自由变量 (free variable)

当外部函数**返回**内部函数时，内部函数依然记得外部函数作用域中的变量——这就是闭包。

```python
def make_greeter(greeting):
    def greet(name):
        return f"{greeting}, {name}!"   # greeting 是自由变量
    return greet                       # 返回内部函数，不调用它

hi = make_greeter("Hi")
hey = make_greeter("Hey")

print(hi("Alice"))   # Hi, Alice!
print(hey("Bob"))     # Hey, Bob!
```

注意：`make_greeter` 已经执行结束，但 `hi` 和 `hey` 依然各自“记得”自己的 `greeting`。这份被记住的绑定关系由函数的 `__closure__` 属性承载。

```python
print(hi.__closure__)              # (<cell at ...>,)
print(hi.__closure__[0].cell_contents)   # Hi
```

---

## 3. 闭包 vs 普通函数：三个判定条件

一个内部函数要成为闭包，需要同时满足：

1. 定义在另一个函数内部（嵌套）；
2. 内部函数引用了外部函数的变量（自由变量）；
3. 外部函数返回了内部函数（或者内部函数被传递出去）。

```python
def counter_factory(start):
    count = start
    def step(inc=1):
        nonlocal count     # 声明我们要修改外层的变量
        count += inc
        return count
    return step

c1 = counter_factory(0)
c2 = counter_factory(100)
print(c1(), c1(), c1())    # 1 2 3
print(c2())                # 101   各自独立，互不影响
```

关键点：`nonlocal` 告诉 Python “我改的不是本地新变量，而是外层自由变量”。两个计数器各自持有独立的 `count`，这就体现了闭包“每次调用外部函数都会创建一份新的绑定”的特性。

---

## 4. 实用场景：工厂函数、装饰器、回调

闭包最常见的三类工程用途：

**（1）工厂函数**：批量生产相似行为但参数不同的函数（上面 `counter_factory` 就是）。

**（2）装饰器 (decorator)**：装饰器本质上就是一个接受函数并返回闭包的函数。

```python
import time

def timed(func):
    def wrapper(*args, **kwargs):
        t0 = time.perf_counter()
        result = func(*args, **kwargs)
        print(f"{func.__name__} took {time.perf_counter()-t0:.4f}s")
        return result
    return wrapper    # wrapper 记住 func

@timed
def add(a, b):
    return a + b

add(1, 2)
```

**（3）回调 (callback)**：把带参数的函数注册到某处稍后执行。

```python
def on_event(prefix):
    def handler(payload):
        print(f"[{prefix}] {payload}")
    return handler

click = on_event("click")
load  = on_event("load")
click("button#submit")
load("home page")
```

---

## 5. 常见陷阱预览（详见 pitfalls）

- 循环中创建闭包会共享同一个变量；
- 只能读取、不能直接赋值外层变量（需要 `nonlocal`）；
- 不要和默认参数、可变对象混用造成“意外记忆”。

---

## 动手练习

**任务：实现一个 `make_multiplier(k)`，返回一个函数 `f(x) = k * x`；并实现一个 `make_acc()`，返回一个累加器：每次调用传入一个数就累加，无参调用则返回当前总和。**

```python
def make_multiplier(k):
    def mul(x):
        return k * x
    return mul

def make_acc():
    total = 0
    def acc(n=None):
        nonlocal total
        if n is not None:
            total += n
        return total
    return acc

# 预期行为
triple = make_multiplier(3)
assert triple(4) == 12
assert triple(-1) == -3

a = make_acc()
a(10); a(5)
assert a() == 15
assert a(7) == 22
```

**进阶**：把 `make_acc` 改造成支持初始值的 `make_acc(start)`；再用 `make_multiplier` 组合出一个 `f(x) = 3 * (x + 1)` 的新闭包。

```python
def make_counter(start=0, step=1):
    """返回一个带独立状态的计数器闭包。"""
    count = start
    def step_once():
        nonlocal count
        count += step
        return count
    return step_once


def make_multiplier(k):
    def mul(x):
        return k * x
    return mul


if __name__ == "__main__":
    # 每个计数器有自己独立的 count，互不影响
    c1 = make_counter()
    c2 = make_counter(start=100, step=10)
    print(c1(), c1(), c1())    # 1 2 3
    print(c2(), c2())          # 110 120

    # 闭包能访问到创建时的自由变量
    triple = make_multiplier(3)
    print(triple(4), triple(-1))   # 12 -3

    # 查看内部记录的闭包内容
    print([c.cell_contents for c in c1.__closure__])   # [3, 1]
```

## py.func.legb

# Python 函数作用域与 LEGB 规则

## 一句话直觉

**你写的每一个变量名，Python 都要回答一个问题：这个 `x` 到底指的是哪个 `x`？** LEGB 规则就是 Python 查找变量名的固定顺序——**Local（局部）→ Enclosing（外层函数）→ Global（全局）→ Built-in（内置）**，理解它，你才能预测代码里每个名字真正绑定到谁。

---

## 1. 什么是作用域（Scope）？

**作用域（Scope）** 是变量名可以被“看见”的范围。Python 中一切名字（name）本质上是绑定到对象的引用，而作用域决定了**在某个位置能不能找到这个名字**。

Python 有四种作用域，按从近到远排列：

| 层级 | 英文 | 中文 | 出现位置 |
|------|------|------|----------|
| L | Local | 局部 | 当前函数内部 |
| E | Enclosing | 闭包外层 | 外层嵌套函数 |
| G | Global | 全局 | 模块顶层 |
| B | Built-in | 内置 | `len`、`print` 等 |

```python
x = "global"          # G：全局

def outer():
    x = "enclosing"   # E：外层函数作用域
    def inner():
        x = "local"   # L：当前函数局部
        print(x)      # 先找 L，找到 "local" 就停
    inner()

outer()               # 输出: local
```

**结论**：查找是“就近命中”，一旦在某一层找到名字就停止，不会继续往上找。

---

## 2. 逐层拆解 LEGB

### 2.1 Local（局部作用域）

函数**内部**通过赋值、`def`、`import`、`for` 等创建的名字都进入 Local。

```python
def f():
    a = 1             # 局部名 a
    b = a + 1         # 局部名 b
    return b

print(f())            # 2
# print(a)            # NameError: a 只活在 f 内部
```

### 2.2 Enclosing（闭包外层作用域）

当你在函数里再定义函数，**外层函数的局部变量**对内层函数来说就是 Enclosing。

```python
def counter():
    n = 0                    # 外层局部，对内层是 Enclosing
    def inc():
        return n             # 只读引用，OK
    return inc

c = counter()
print(c())                   # 0
```

注意：内层**只读**没问题，一旦想**改写**外层变量，就需要 `nonlocal`（见第 4 节）。

### 2.3 Global（全局作用域）

模块顶层（一个 `.py` 文件里没缩进的部分）定义的名字属于 Global。函数里读全局变量是允许的：

```python
PI = 3.14159

def area(r):
    return PI * r * r       # 读全局，OK

print(area(2))              # 12.56636
```

但**在函数里赋值**同名变量会创建一个新的局部变量，而不是修改全局：

```python
count = 0

def bad():
    count = 10              # 这是新局部变量，与全局 count 无关

bad()
print(count)                # 0，全局没变
```

### 2.4 Built-in（内置作用域）

最后才去找 `len`、`print`、`ValueError` 这些内置名字。它们自动存在于 `builtins` 模块中。

```python
print(len("hello"))         # len 来自 Built-in

# 危险：覆盖内置名
def f():
    list = [1, 2, 3]        # 局部把内置 list 遮住了
    return list

print(f())                  # [1, 2, 3]
# 出了函数，list 又恢复为内置类型
print(list("ab"))           # ['a', 'b']
```

---

## 3. 一个综合示例：名字究竟被谁接管？

```python
x = "G"

def outer():
    x = "E"
    def inner():
        print("inner 里看到的 x:", x)   # L? 无 → E 命中 "E"
    inner()
    print("outer 里看到的 x:", x)       # L 命中 "E"

outer()
print("模块里看到的 x:", x)             # G 命中 "G"
```

输出：
```
inner 里看到的 x: E
outer 里看到的 x: E
模块里看到的 x: G
```

只看函数的“定义位置”决定 Enclosing，与“调用位置”无关，这就是 **词法作用域（Lexical Scoping）**。

---

## 4. 修改外层变量：`global` 与 `nonlocal`

默认情况下，函数体里出现赋值语句 `name = ...`，Python 就会把 `name` 视为**局部名**——即使周围有其他同名变量。要打破这条规则，用显式声明：

```python
count = 0

def bump():
    global count        # 声明“我要改模块级的 count”
    count += 1

bump(); bump()
print(count)            # 2
```

```python
def counter():
    n = 0
    def inc():
        nonlocal n      # 声明“我要改外层的 n”
        n += 1
        return n
    return inc

c = counter()
print(c(), c(), c())    # 1 2 3
```

**记忆口诀**：读不需要声明，写非局部才需要 `global`/`nonlocal`。

---

## 5. 为什么要懂 LEGB？（工程意义）

1. **调试定位**：`UnboundLocalError`、`NameError` 几乎都是 LEGB 顺序引起的。
2. **闭包（Closure）**：装饰器、回调、`functools.partial` 都依赖 Enclosing 层。
3. **避免 shadowing**：不要用 `list`、`id`、`str` 做变量名，否则局部覆盖内置。
4. **接口设计**：全局状态越多，函数越是“看不着边界”，LEGB 让你清楚该往哪里传参。

---

## 动手练习

写一个 `make_multiplier(factor)`，返回一个新函数，新函数接受 `x` 返回 `factor * x`。再写一个 `make_counter()`，每次调用返回的计数器都比上次多 1（提示：用 `nonlocal`）。最后用 `print` 验证：

```python
triple = make_multiplier(3)
print(triple(10))   # 期望 30

c = make_counter()
print(c(), c(), c())  # 期望 1 2 3
```

**额外挑战**：如果 `make_multiplier` 里用 `global factor` 而不是闭包，会出现什么问题？动手改一下看看。

```python
# demo_legb.py —— 可直接运行，观察 LEGB 各级命中情况

x = "GLOBAL"                     # Global 层


def outer():
    x = "ENCLOSING"              # Enclosing 层

    def inner():
        # 尝试四个层级：
        x_local = "LOCAL"        # Local 层
        print("1) L 命中:", x_local)
        print("2) E 命中:", x)    # 没有 L 的 x，向上找到 E

        # Built-in 层
        print("3) B 命中 len:", len("abc"))

    inner()


outer()

# G 层：模块顶层
print("4) G 命中:", x)


# 闭包修改外层：nonlocal
def make_counter():
    n = 0
    def inc():
        nonlocal n               # 声明修改 Enclosing 的 n
        n += 1
        return n
    return inc


c = make_counter()
print("5) 闭包计数:", c(), c(), c())


# global 修改模块级变量
total = 0

def bump():
    global total
    total += 1


bump(); bump()
print("6) global 累计:", total)
```


---

## 本课题目

### single_choice · None



- [A] 1
- [B] 0
- [C] 抛出 UnboundLocalError
- [D] 抛出 NameError

**参考答案**：2

**解析**：inner 中对 count 使用了 count += 1，相当于赋值操作，Python 会把 count 视为 inner 的局部变量，但它在读取前未被赋值，因此抛出 UnboundLocalError。若要修改外层变量，需使用 nonlocal 声明。

### single_choice · None



- [A] 1 1 1
- [B] 1 2 3
- [C] 1 2 1
- [D] 2 2 2

**参考答案**：2

**解析**：每次调用 outer() 都会创建一个新的局部环境，因此 f 和 g 各自绑定独立的 count 变量。f() 连续调用会累加到 1、2，而 g() 是另一个闭包，它的 count 从 0 开始变为 1。

### single_choice · None



- [A] 自由变量在外层函数返回后立即被销毁
- [B] 自由变量只有在闭包被调用时才会被创建
- [C] 自由变量会随闭包一起存活，即使外层函数已经返回
- [D] 自由变量会被自动复制到全局作用域

**参考答案**：2

**解析**：闭包会持有对外层作用域中自由变量的引用，使得这些变量在外层函数返回后仍然存活，不会被垃圾回收。它们不会自动进入全局作用域，也不是在闭包调用时才创建。

### single_choice · None



- [A] [0, 1, 2]
- [B] [2, 2, 2]
- [C] [0, 0, 0]
- [D] 抛出异常

**参考答案**：0

**解析**：使用默认参数 i=i 时，默认值在函数定义时求值并绑定到该 lambda 的局部参数上，因此每个 lambda 捕获的是当前循环变量 i 的值，输出 [0, 1, 2]。这常用于解决循环闭包的延迟绑定问题。

### single_choice · None



- [A] count 是全局变量，不能在任何函数中修改
- [B] 函数内对 count 赋值使其成为局部变量，应使用 global 声明
- [C] 函数内应使用 nonlocal 声明 count
- [D] count 必须定义为列表才能修改

**参考答案**：1

**解析**：由于函数中对 count 进行了赋值，Python 将其视为局部变量，但赋值前读取会引发 UnboundLocalError。要修改全局变量，应在函数内使用 global count。nonlocal 用于外层函数变量，不适用于全局变量。

### single_choice · None



- [A] 5
- [B] 抛出 NameError
- [C] 抛出 UnboundLocalError
- [D] None

**参考答案**：0

**解析**：inner 是最内层函数，它引用的 x 来自最外层 outer 的局部作用域。闭包可以跨越中间层，因此 inner 仍然能够访问 x 并返回 5。

### single_choice · None



- [A] 闭包无法保存状态，函数对象可以
- [B] 闭包可以保存状态，并且多个闭包实例之间的状态通常相互独立
- [C] 同一个外层函数返回的所有闭包必然共享同一份状态
- [D] 闭包保存的状态只能通过全局变量访问

**参考答案**：1

**解析**：闭包可以保存外层作用域中的变量作为状态，每次调用外层函数都会创建新的作用域，因此不同实例的状态通常相互独立。只有同一实例内创建的多个闭包才会共享该实例的状态。

### single_choice · None



- [A] 1 2
- [B] 2 3
- [C] 2 2
- [D] 抛出 UnboundLocalError

**参考答案**：1

**解析**：nonlocal x 允许 inner 修改外层变量 x。第一次调用时 x 从 1 变为 2 并返回 2；第二次调用时 x 从 2 变为 3 并返回 3。由于闭包共享同一个 x，状态得以保持。

### single_choice · None



- [A] 需要在函数内使用循环时
- [B] 需要创建记住某些配置参数、并在多次调用间保持状态的函数时
- [C] 需要调用第三方库时
- [D] 需要将函数定义为递归时

**参考答案**：1

**解析**：闭包的典型用途是创建带有私有状态或预设参数的函数工厂，例如计数器、装饰器、带配置的回调。循环、递归或调用第三方库并不一定需要闭包。

### single_choice · None



- [A] [1, 2] [1, 2]
- [B] [1, 2] [1, 2, 2]
- [C] [1] [1]
- [D] 抛出 UnboundLocalError

**参考答案**：1

**解析**：inner 中对 x 调用了 append 方法，但没有对 x 本身重新赋值，因此不构成对 x 的局部绑定。x 仍指向外层的列表，修改会持续累积，所以第一次返回 [1, 2]，第二次返回 [1, 2, 2]。

### single_choice · None



- [A] 局部作用域 → 全局作用域 → 外层函数作用域 → 内置作用域
- [B] 局部作用域 → 外层函数作用域 → 全局作用域 → 内置作用域
- [C] 全局作用域 → 局部作用域 → 外层函数作用域 → 内置作用域
- [D] 外层函数作用域 → 局部作用域 → 全局作用域 → 内置作用域

**参考答案**：1

**解析**：Python 使用 LEGB 规则查找变量：Local（局部）→ Enclosing（外层函数）→ Global（全局）→ Built-in（内置）。闭包中的自由变量正是在 Enclosing 这一层被找到的。

### single_choice · None



- [A] 10
- [B] 30
- [C] None
- [D] 抛出 NameError

**参考答案**：1

**解析**：闭包捕获变量绑定本身而不是定义时的快照。调用 f() 时读取的是外层 x 的最终值 30，而不是 inner 定义时的 10。

### single_choice · None



- [A] [10, 11, 12]
- [B] [12, 12, 12]
- [C] [13, 13, 13]
- [D] [10, 10, 10]

**参考答案**：1

**解析**：列表推导中的 lambda 闭包捕获的是同一个变量 i，而不是每个 i 的当前值。当推导结束后 i 为 2，三个 lambda 都引用它，因此结果都是 12。要得到 [10, 11, 12]，需用默认参数或工厂函数固定 i。

### single_choice · None



- [A] 0
- [B] 1
- [C] 2
- [D] 抛出异常

**参考答案**：2

**解析**：inc 和 get 是同一外层作用域中创建的两个闭包，它们共享同一个 x。两次调用 f() 后 x 变为 2，因此 g() 返回 2。

### single_choice · None



- [A] 闭包必须定义在类的方法中
- [B] 闭包是能访问其定义所在词法作用域中变量的嵌套函数，即使外层函数已经返回
- [C] 闭包只能捕获全局变量，不能捕获外层函数的局部变量
- [D] 闭包中的变量在每次调用时都会被重新初始化为定义时的值

**参考答案**：1

**解析**：闭包指嵌套函数记住了其定义时的词法作用域中的自由变量，即使外层函数已经返回，这些变量依然可以被访问。闭包与类方法无关，也可以捕获外层局部变量；每次调用不会重置状态，而是共享同一份绑定。

### single_choice · None



- [A] 10
- [B] 20
- [C] None
- [D] 抛出异常

**参考答案**：1

**解析**：闭包捕获的是变量本身，而不是定义函数时的值。bar 返回时读取的是外层函数中 x 的最新值，此时 x 已被赋值为 20，因此输出 20。

### single_choice · None



- [A] nonlocal 用于声明变量属于全局作用域
- [B] nonlocal 只能用于最外层函数中
- [C] nonlocal 使内层函数可以重新绑定外层函数中的变量
- [D] nonlocal 声明的变量必须已经存在于全局命名空间中

**参考答案**：2

**解析**：nonlocal 用于在内层函数中声明变量来自外层（非全局）作用域，从而可以对其重新赋值。它不用于全局作用域，也不要求最外层函数，更不会去全局命名空间查找。

### single_choice · None



- [A] outer
- [B] inner
- [C] 抛出 UnboundLocalError
- [D] 抛出 NameError

**参考答案**：2

**解析**：inner 中存在对 x 的赋值语句，因此 x 在 inner 的整个作用域内被视为局部变量。print(x) 在赋值之前执行，读取了尚未绑定的局部变量，从而抛出 UnboundLocalError。若想打印外层的 x，需要先声明 nonlocal x。

### single_choice · None



- [A] def counter():
      count = 0
      return lambda: count + 1
- [B] def counter():
      count = 0
      def inc():
          nonlocal count
          count += 1
          return count
      return inc
- [C] def counter():
      def inc():
          count += 1
          return count
      return inc
- [D] def counter():
      return lambda: count += 1

**参考答案**：1

**解析**：要在内层函数中修改外层变量，必须使用 nonlocal 声明；选项 B 正确地声明了 nonlocal count 并返回 inc。选项 A 的 lambda 每次只返回 count+1，并不改变 count。选项 C 缺少 nonlocal 会报 UnboundLocalError。选项 D 语法错误，lambda 不能包含赋值语句。

### single_choice · None



- [A] 不是，因为 x 是全局变量
- [B] 不是，因为 inner 没有使用 nonlocal
- [C] 是，因为 inner 引用了外层函数 outer 的局部变量 x
- [D] 是，但仅当 x 被声明为 nonlocal 时

**参考答案**：2

**解析**：闭包只要求嵌套函数引用其外层词法作用域中的变量，并不要求使用 nonlocal。inner 读取 outer 的局部变量 x，因此构成闭包。x 不是全局变量，nonlocal 仅在需要改写外层变量时才需要。

### single_choice · None



- [A] 0 1 2
- [B] 2 2 2
- [C] 0 0 0
- [D] 1 2 3

**参考答案**：1

**解析**：所有 f 都捕获了同一个变量 i。循环结束后 i 的值为 2，因此每个函数都返回 2。这是经典的延迟绑定问题。若想输出 0 1 2，可以将 i 作为默认参数传入，例如 def f(i=i): return i。

### single_choice · None



- [A] 查找顺序为 Local → Enclosing → Global → Built-in
- [B] 查找顺序为 Local → Global → Enclosing → Built-in
- [C] 查找顺序为 Built-in → Global → Enclosing → Local
- [D] 查找顺序为 Enclosing → Local → Global → Built-in

**参考答案**：0

**解析**：LEGB 分别代表 Local（局部）、Enclosing（嵌套外层函数）、Global（模块全局）、Built-in（内置命名空间），Python 按此顺序依次查找名称。

### single_choice · None



- [A] global
- [B] enclosing
- [C] 报 NameError
- [D] 报 UnboundLocalError

**参考答案**：1

**解析**：inner 内没有对 x 赋值，因此不产生局部变量。查找时先找 Local（没有），再找 Enclosing，outer 中的局部变量 x='enclosing' 被找到。

### multi_choice · None



- [A] Local 指的是当前函数内部绑定的名称
- [B] Enclosing 指的是任意层嵌套的外层函数作用域，由内向外逐层查找
- [C] Global 指的是当前模块顶层绑定的名称
- [D] Built-in 指的是 Python 内置的名称，查找优先级最高
- [E] 如果在 Local 找到，就不会去 Enclosing 或 Global 查找同一名称

**参考答案**：[0, 1, 2, 4]

**解析**：Built-in 位于查找链末端，优先级最低，所以选项 4 错误；选项 0、1、2、4 都符合 LEGB 的定义。

### multi_choice · None



- [A] 函数体内对同名变量做赋值
- [B] 函数体内对同名变量使用 += 复合赋值
- [C] 函数体内对同名变量使用 for 循环变量复用
- [D] 函数体内只是读取该变量并打印
- [E] 函数体内用 del 删除该名称

**参考答案**：[0, 1, 2, 4]

**解析**：赋值、复合赋值、作为循环目标、作为 with/except 目标、del 都会让名称在函数内被绑定为局部；单纯读取不会。因此选 0、1、2、4。

### multi_choice · None



- [A] global 让函数内赋值作用于模块全局命名空间
- [B] nonlocal 让函数内赋值作用于最近的外层函数局部变量
- [C] nonlocal 可以用于模块顶层代码
- [D] 使用 nonlocal 时，外层必须存在该名称的绑定，否则报 SyntaxError
- [E] global 和 nonlocal 都必须在函数体内使用

**参考答案**：[0, 1, 3, 4]

**解析**：nonlocal 只能用在嵌套函数内部，不能在模块顶层使用，选项 2 错误。其余说法正确。

### fill_blank · None



**参考答案**：["Local Enclosing Global Built-in", "Local,Enclosing,Global,Built-in", "local enclosing global built-in"]

**解析**：LEGB 依次是 Local（函数局部）、Enclosing（外层函数）、Global（模块全局）、Built-in（内置），Python 按此顺序查找名称。

### fill_blank · None



**参考答案**：["nonlocal global", "nonlocal,global", "nonlocal; global"]

**解析**：nonlocal 定位到最近的外层函数作用域；global 定位到模块全局作用域，二者不可互换使用。

### code_reading · None



**参考答案**：g

**解析**：inner 的 Local 与 Enclosing 都没有 x，查找进入 Global，找到模块级 x='g'，因此输出 g。

### code_reading · None



**参考答案**：1

**解析**：inner 的 Local 无 x，Enclosing 会从最近的外层 mid 开始逐层向外查找，mid 没有 x，继续到 outer，找到 x=1，所以输出 1。

### code_reading · None



**参考答案**：UnboundLocalError

**解析**：函数内的 x += 1 让 x 在编译期被视为局部变量，但读取它时还未赋值，所以抛出 UnboundLocalError，而不是修改全局 x。

### scenario · None



**解析**：函数内出现对 count 的赋值/复合赋值，编译期就把 count 定为局部变量，而读取发生在赋值之前，因此报 UnboundLocalError。修复方案一：在函数首行加 global count；方案二：把计数保存在可变容器（如列表或字典）中，通过修改容器元素来绕过重新绑定。

### scenario · None



**解析**：闭包按名称在 Enclosing 作用域查找变量，捕获的是变量本身而不是创建时的值；所有闭包共享同一个循环变量，循环结束后该变量定格为末值，因此返回同一结果。修复思路：把循环变量的当前值通过默认参数绑定（如 lambda i=i: i），或改用工厂函数 / functools.partial 固定每次的取值。

### single_choice · None



- [A] 10
- [B] 20
- [C] None
- [D] 抛出 UnboundLocalError

**参考答案**：3

**解析**：函数体内只要出现对 x 的赋值，编译期就把 x 视为局部变量；print(x) 在赋值之前执行，局部变量尚未绑定，因此抛出 UnboundLocalError。

### single_choice · None



- [A] nonlocal
- [B] global
- [C] static
- [D] extern

**参考答案**：1

**解析**：global 声明使函数内的赋值作用于模块全局命名空间；nonlocal 用于嵌套函数中修改外层函数的局部变量，不能修改模块全局。

### single_choice · None



- [A] 1
- [B] 2
- [C] 报 SyntaxError
- [D] 报 NameError

**参考答案**：1

**解析**：nonlocal 声明 x 指向外层函数 outer 的局部变量，inner 中的赋值修改的就是它，因此 outer 打印 2。

### single_choice · None



- [A] 5
- [B] 6
- [C] None
- [D] 报 UnboundLocalError

**参考答案**：1

**解析**：global 声明 x 指向模块全局变量，f() 中的赋值修改全局 x 为 6，之后 print(x) 输出 6。

### single_choice · None



- [A] 它是查找的第一站，优先级最高
- [B] 它只在内置模块被导入后才参与查找
- [C] 它是查找的最后一站，Local/Enclosing/Global 都找不到时才查它
- [D] 它和外层函数命名空间优先级相同

**参考答案**：2

**解析**：内置命名空间位于 LEGB 链条末端，只有当局部、外层函数、全局都找不到该名称时才会去内置命名空间查找，例如 len、print。

### single_choice · None



- [A] 3
- [B] 5
- [C] 报 TypeError
- [D] 报 NameError

**参考答案**：2

**解析**：模块全局把 len 绑定为整数 5，函数内在 Global 层就找到了 len，因此不会继续查找内置的 len 函数，5('abc') 触发 TypeError。

### single_choice · None



- [A] [0, 1, 2]
- [B] [2, 2, 2]
- [C] [3, 3, 3]
- [D] [0, 0, 0]

**参考答案**：1

**解析**：lambda 捕获的是变量 i 本身（闭包按名称查找），循环结束后 i 的值为 2，三个闭包查到的都是同一个 i，所以都返回 2。

### single_choice · None



- [A] outer
- [B] changed
- [C] None
- [D] 报 NameError

**参考答案**：1

**解析**：闭包捕获的是变量本身而非调用时的值。返回 inner 后调用时，Enclosing 中的 x 已经是 'changed'，因此输出 changed。
