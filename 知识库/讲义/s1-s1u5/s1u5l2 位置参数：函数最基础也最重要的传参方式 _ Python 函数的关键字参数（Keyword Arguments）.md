# s1u5l2 位置参数：函数最基础也最重要的传参方式 / Python 函数的关键字参数（Keyword Arguments）

> 来源 `content/lessons/s1u5l2.json`

## py.func.args_positional

# 位置参数：函数最基础也最重要的传参方式

## 一句话直觉

**位置参数（positional arguments）** 是函数调用时按“顺序”一一对应传进去的实参——就像排队买奶茶，柜台只认“第 1 个、第 2 个……”，不看名字。

它是 Python 函数调用的起点：不理解位置参数，就理解不了默认值、`*args`、关键字参数、甚至装饰器。

---

## 1. 什么是位置参数？

定义函数时，写在括号里的参数叫 **形参（parameter）**；调用时传进去的值叫 **实参（argument）**。

当调用时只按顺序写值，Python 就按定义时的顺序依次绑定——这就是位置参数。

```python
def greet(name, city):          # name, city 是形参
    return f"你好，{name}！欢迎来到{city}。"

print(greet("小明", "北京"))    # "小明" → name, "北京" → city
# 输出: 你好，小明！欢迎来到北京。
```

**关键结论**：位置参数是“按顺序绑定”，顺序错了，结果就错了。

```python
print(greet("北京", "小明"))
# 输出: 你好，北京！欢迎来到小明。   ← 语义完全反了
```

> 工程级提示：位置参数数量必须与定义完全一致，多了少了都会 `TypeError`。

---

## 2. 数量必须匹配（这是最容易踩的坑）

```python
def add(a, b):
    return a + b

print(add(1, 2))    # 3
# add(1)            # TypeError: missing 1 required positional argument: 'b'
# add(1, 2, 3)      # TypeError: takes 2 positional arguments but 3 were given
```

**关键结论**：位置参数是“必填”的，除非给它一个默认值（下一节讲）。

---

## 3. 位置参数 + 默认值

给形参赋默认值后，它变成 **可选位置参数（optional positional argument）**，调用时可以省略。

```python
def greet(name, city="北京"):     # city 有默认值
    return f"你好，{name}！欢迎来到{city}。"

print(greet("小明"))              # 你好，小明！欢迎来到北京。
print(greet("小明", "上海"))      # 你好，小明！欢迎来到上海。
# print(greet("小明", "上海", "额外"))  # TypeError: too many
```

**语法规则**：默认值参数必须排在非默认值参数后面。

```python
def bad(a=1, b):   # SyntaxError: non-default argument follows default argument
    ...
```

**关键结论**：默认值只是“可省略”，一旦传入仍按位置绑定。

---

## 4. 关键字参数：位置参数的“名字版”

调用时用 `名字=值` 的形式，叫 **关键字参数（keyword arguments）**。它和位置参数可以混用，但位置参数必须在前。

```python
def greet(name, city):
    return f"你好，{name}！欢迎来到{city}。"

print(greet("小明", city="上海"))   # OK
print(greet(name="小明", city="上海"))  # OK，全关键字
# greet(city="上海", "小明")        # SyntaxError: positional argument follows keyword argument
```

**关键结论**：位置参数解决“顺序调用”，关键字参数解决“可读性”和“跳过默认值”。两者配合才是完整图景。

---

## 5. 运行时真正发生了什么（工程级视角）

Python 的函数对象有 `__code__.co_varnames` 记录形参顺序，调用时解释器按顺序把实参塞进去。理解这一点，就能理解后面 `*args`、`**kwargs`、`functools.partial` 为什么那样设计。

```python
def f(a, b, c):
    return a, b, c

print(f.__code__.co_varnames)   # ('a', 'b', 'c')
```

常见错误（提前预览）：
- 忘记传参 → `TypeError: missing ...`
- 顺序写反 → 程序不报错但结果错，这是最危险的
- 默认值写成可变对象（如 `[]`）→ 多次调用共享同一个对象

```python
def append_bad(item, box=[]):   # 危险！
    box.append(item)
    return box

print(append_bad(1))   # [1]
print(append_bad(2))   # [1, 2]  ← 不是 [2]
```

正确写法：

```python
def append_good(item, box=None):
    if box is None:
        box = []
    box.append(item)
    return box

print(append_good(1))  # [1]
print(append_good(2))  # [2]
```

**关键结论**：位置参数是最底层、最常用的传参机制；默认值参数要小心可变对象。

---

## 动手练习

写一个函数 `format_student(name, age, city="未知")`，返回字符串：

> `姓名：<name>，年龄：<age>，城市：<city>`

要求：

1. 只用位置参数调用一次：`format_student("小明", 18, "北京")`
2. 用“位置 + 关键字”混合调用一次：`format_student("小红", age=20)`
3. 故意传错顺序，观察输出，并思考：为什么 Python 不报错？
4. 写一个小脚本，循环调用 5 次，每次传不同参数，打印结果。

预期输出示例：

```
姓名：小明，年龄：18，城市：北京
姓名：小红，年龄：20，城市：未知
姓名：18，年龄：小明，城市：北京   ← 顺序反了，但不报错
```

完成后问自己：如果把 `format_student` 的第三个参数改成必填，调用方要改几处？这就是为什么工程上推荐“关键字参数优先”来提升可维护性。

```python
def greet(name, city="北京"):
    """位置参数 name 必填；city 是带默认值的位置参数。"""
    return f"你好，{name}！欢迎来到{city}。"

if __name__ == "__main__":
    # 1) 纯位置参数
    print(greet("小明", "上海"))

    # 2) 省略默认值
    print(greet("小红"))

    # 3) 位置 + 关键字混用
    print(greet("小刚", city="广州"))

    # 4) 查看形参顺序
    print(greet.__code__.co_varnames)  # ('name', 'city')
```

## py.func.args_keyword

# Python 函数的关键字参数（Keyword Arguments）

> **一句话直觉**：当你调用函数时，如果能用“参数名=值”的方式传参，代码不仅一眼看懂每个值代表什么，还能忽略顺序、给默认值、只在需要时覆盖——这就是关键字参数（keyword arguments）存在的意义。

本讲从“什么是关键字参数”讲到“工程级 API 设计”，共 5 小节。所有示例都可直接复制运行。

---

## 1. 从位置参数（positional arguments）说起

调用函数时最原始的方式是按位置传参：

```python
def greet(name, age):
    return f"{name} 今年 {age} 岁"

greet("小明", 18)   # '小明' 给 name，18 给 age
```

只要顺序错了，语义就全乱。当参数有 3、4 个以上时，读代码的人必须去翻函数定义才知道 `True` 到底是“是否激活”还是“是否删除”。

**关键字参数**就是你主动把参数名写出来：

```python
greet(age=18, name="小明")   # 顺序随便换，结果一致
```

规则只有一条：**参数名必须和函数定义里的一致**（这里的 `name`、`age`）。

---

## 2. 混用规则：位置参数必须在前

Python 允许两种写法混用，但有顺序要求：**位置参数在前，关键字参数在后**。

```python
greet("小明", age=18)   # ✅ 合法
greet(name="小明", 18)  # ❌ SyntaxError: positional argument follows keyword argument
```

一旦你开始用关键字参数，后面的所有实参（arguments）都必须也带名字：

```python
def profile(name, age, city):
    return f"{name}/{age}/{city}"

profile("小明", age=18, city="上海")  # ✅
profile("小明", city="上海", age=18)  # ✅ 顺序无关，只要名字对
```

**工程直觉**：参数少时位置传参够用；一旦参数 ≥3 个或某个参数是布尔/None，就强烈建议用关键字传参提升可读性。

---

## 3. 默认值（default values）：关键字参数的天然搭档

函数定义时给参数提供默认值，调用时就可以不传：

```python
def connect(host, port=3306, timeout=5):
    return f"连接 {host}:{port}, 超时 {timeout}s"

connect("db.local")                       # 用默认 port 和 timeout
connect("db.local", timeout=30)           # 只覆盖 timeout，必须用关键字
connect("db.local", 5432, timeout=30)     # port 也可以位置传
```

**关键规则**：带默认值的参数必须排在无默认值参数之后，否则 SyntaxError。

```python
def bad(a=1, b):   # ❌ SyntaxError: non-default argument follows default argument
    ...
```

> 默认值在函数**定义时**只求值一次，因此千万不要用可变对象（mutable）当默认值——见第 5 节常见误区。

---

## 4. 强制关键字参数（keyword-only arguments）：用 `*` 划清边界

在参数列表中写一个 `*`，它**右边**的参数就变成只能通过关键字传入：

```python
def transfer(from_account, to_account, *, amount, currency="CNY"):
    return f"从 {from_account} 转 {amount} {currency} 到 {to_account}"

transfer("A", "B", amount=100)              # ✅
transfer("A", "B", 100)                     # ❌ TypeError: takes 2 positional arguments but 3 were given
transfer("A", "B", amount=100, currency="USD")  # ✅
```

**为什么工程上需要它？**

- 让调用点“自解释”，杜绝 `f(True, False, 1)` 这种难读的调用。
- 当参数带 `*` 后，未来新增参数可以安全地插入而不破坏已有调用（只要新参数也有默认值）。
- 这是现代 Python 库（requests、pandas、pydantic）的常见 API 风格。

对称的还有 `/` 用来标记“只能位置传”的参数（Python 3.8+），例如 `def f(a, /, b)` 中 `a` 不能用关键字传。

---

## 5. 参数解包（unpacking）：`*args` 与 `**kwargs` 的关键字侧

`**kwargs` 让函数接收任意数量的关键字参数，在函数内部变成一个 `dict`：

```python
def build_config(**kwargs):
    return kwargs

build_config(host="db", port=3306)   # {'host': 'db', 'port': 3306}
```

调用时也可以用 `**` 把字典“拆开”传入：

```python
opts = {"host": "db", "port": 3306}
connect(**opts)   # 等价于 connect(host="db", port=3306)
```

**典型工程模式**：装饰器（decorator）和包装器（wrapper）里用 `*args, **kwargs` 透传所有参数，不关心具体签名。

```python
def log_calls(fn):
    def wrapper(*args, **kwargs):
        print(f"调用 {fn.__name__} args={args} kwargs={kwargs}")
        return fn(*args, **kwargs)
    return wrapper

@log_calls
def add(a, b, c=0):
    return a + b + c

add(1, 2, c=3)   # 打印 kwargs={'c': 3}，返回 6
```

---

## 结尾 · 动手练习

**任务**：写一个 `make_request` 函数，模拟 HTTP 请求配置构造。

要求：
1. 签名：`make_request(url, *, method="GET", timeout=5, headers=None, **extra)`
2. `method`、`timeout`、`headers` 必须是强制关键字参数（用 `*` 隔开）。
3. `headers` 默认值为 `None`，函数体内部若为 `None` 就替换为 `{"User-Agent": "my-client"}`（不要直接在默认值里写可变字典）。
4. `**extra` 把额外关键字参数合并进返回的字典中输出。
5. 返回一个 `dict`，结构：`{"url":..., "method":..., "timeout":..., "headers":..., **extra}`。

验证：

```python
make_request("https://example.com")
# {'url':'https://example.com','method':'GET','timeout':5,'headers':{'User-Agent':'my-client'}}

make_request("https://example.com", method="POST", retries=3, cache=False)
# 含 'method':'POST'、'retries':3、'cache':False

make_request("https://example.com", "POST")  # ❌ 应抛 TypeError
```

**进阶要求**：再加一个装饰器 `@log_calls`，打印每次调用收到的 `kwargs`，并用它装饰 `make_request` 验证。

```python
# 演示：关键字参数、默认值、强制关键字参数、**kwargs

def make_request(url, *, method="GET", timeout=5, headers=None, **extra):
    # 注意：绝不能在默认值里写 {}，否则所有调用共享同一个 dict
    if headers is None:
        headers = {"User-Agent": "my-client"}
    return {"url": url, "method": method, "timeout": timeout,
            "headers": headers, **extra}


if __name__ == "__main__":
    # 1) 全省略可选参数
    print(make_request("https://example.com"))

    # 2) 只覆盖 method 并追加额外字段
    print(make_request("https://example.com", method="POST", retries=3, cache=False))

    # 3) 位置传 method 会报错（method 是 keyword-only）
    try:
        make_request("https://example.com", "POST")
    except TypeError as e:
        print("预期报错:", e)

    # 4) 字典解包：**opts 等价于逐个关键字传参
    opts = {"method": "PUT", "timeout": 30}
    print(make_request("https://example.com", **opts))
```


---

## 本课题目

### single_choice · None



- [A] Hello, Alice
- [B] Alice, Hello
- [C] HelloAlice
- [D] 报错，因为参数顺序错误

**参考答案**：0

**解析**：调用时按位置依次把 'Alice' 绑定到 name，把 'Hello' 绑定到 greeting，因此返回 'Hello, Alice'。位置参数按书写顺序一一对应，顺序不同结果不同。

### single_choice · None



- [A] power(3, 2)
- [B] power(2, 3)
- [C] power(base=2, exp=3)
- [D] power(exp=2, base=3) 会报错

**参考答案**：0

**解析**：位置参数第一个传给 base，第二个传给 exp，所以 power(3, 2) 得到 3 的 2 次方。原题 power(2, 3) 是 2 的 3 次方，不符合需求。

### single_choice · None



- [A] (2, 1)
- [B] (1, 2)
- [C] 报错
- [D] (1, 1)

**参考答案**：0

**解析**：位置参数按顺序绑定，f(2, 1) 中 x=2, y=1，返回元组 (2, 1)。与 f(1, 2) 返回值不同。

### single_choice · None



- [A] Hi Bob
- [B] Bob Hi
- [C] Hi
- [D] 报错，缺少 msg 参数

**参考答案**：0

**解析**：name 是必需的位置参数，msg 有默认值。调用 greet('Bob') 时只传一个位置参数，name='Bob'，msg 使用默认 'Hi'，输出 'Hi Bob'。

### single_choice · None



- [A] 6
- [B] 13
- [C] 23
- [D] 33

**参考答案**：0

**解析**：三个位置实参依次绑定 a=1, b=2, c=3，覆盖默认值，结果 1+2+3=6。位置参数可以覆盖有默认值的形参。

### single_choice · None



- [A] 有 SyntaxError：非默认参数不能跟在默认参数之后
- [B] 没有错误，可以正常调用
- [C] 有 TypeError，只在调用时报错
- [D] 有错误，但可以通过 f(1, 2) 绕过

**参考答案**：0

**解析**：Python 规定：定义函数时，带默认值的形参不能出现在不带默认值的形参之前。因此 def f(a=1, b) 是 SyntaxError，在定义时就会报错。

### single_choice · None



- [A] 输出 1 2 3
- [B] 报错，因为位置参数不能与关键字参数混用
- [C] 输出 1 3 2
- [D] 报错，因为 c 必须在 b 之后

**参考答案**：0

**解析**：位置参数 1 绑定 a，随后关键字参数 c=3、b=2 分别绑定。Python 允许位置参数与关键字参数混合使用，只要不重复绑定同一个形参。输出 1 2 3。

### single_choice · None



- [A] 7
- [B] -7
- [C] 13
- [D] 报错，位置参数必须按顺序

**参考答案**：0

**解析**：使用关键字参数时，绑定按名字而非位置，a=10, b=3，结果 10-3=7。这与位置参数调用 f(10, 3) 结果相同。

### single_choice · None



- [A] 位置参数在调用时必须严格按照形参顺序传值，不能使用关键字
- [B] 位置参数按从左到右顺序绑定
- [C] 实参个数必须与形参个数匹配（除非有默认值或可变参数）
- [D] 位置参数与关键字参数可以在同一次调用中混用

**参考答案**：0

**解析**：位置参数在调用时也可以使用关键字方式传递，只要绑定结果唯一即可。'不能使用关键字' 是错误的说法。其他三项均为正确描述。

### single_choice · None



- [A] f(3, 2)
- [B] f(2, 3)
- [C] f(b=2, a=3)
- [D] f(2, b=3)

**参考答案**：0

**解析**：f(3, 2) 绑定 a=3, b=2，计算 3*10+2=32。选项三 f(b=2, a=3) 也会得到 32，但本题为单选，最直接的位置调用是 f(3, 2)。原式 f(2, 3) 得到 23。

### single_choice · None



- [A] (1, 2, 3)
- [B] (3, 1, 2)
- [C] (1, 3, 2)
- [D] 报错，位置参数顺序被打乱

**参考答案**：0

**解析**：关键字参数按名字绑定，x=1, y=2, z=3，返回 (1, 2, 3)。与位置调用 f(1, 2, 3) 结果相同。位置参数与关键字参数在绑定结果上可以等价。

### single_choice · None



- [A] 3
- [B] 报错，因为第一个参数必须用关键字
- [C] 报错，因为位置参数不能与关键字参数混用
- [D] None

**参考答案**：0

**解析**：第一个实参 1 按位置绑定 a，第二个实参 b=2 按关键字绑定 b，合法调用，返回 3。位置参数可以出现在关键字参数之前。

### single_choice · None



- [A] 5
- [B] 9
- [C] 11
- [D] -5

**参考答案**：0

**解析**：按位置绑定 a=10, b=3, c=2，计算 10-3-2=5。位置参数依次赋值，顺序不能随意调换。

### single_choice · None



- [A] TypeError: add() missing 1 required positional argument: 'y'
- [B] 返回 1，y 默认为 0
- [C] 返回 None
- [D] SyntaxError

**参考答案**：0

**解析**：位置参数个数少于必需形参个数时，Python 抛出 TypeError，指出缺少一个必需的位置参数。不会有隐式默认值。

### single_choice · None



- [A] TypeError: show() takes 2 positional arguments but 3 were given
- [B] 打印 1 2，多余参数被忽略
- [C] 打印 1 2 3
- [D] 把 3 赋给可变参数

**参考答案**：0

**解析**：函数只接受两个位置参数，传入三个会触发 TypeError，提示给了 3 个位置参数但只接受 2 个。Python 不会自动忽略多余参数。

### single_choice · None



- [A] func(1, 2, 3)
- [B] func(a=1, b=2, c=3)
- [C] func(1, c=3, b=2)
- [D] func(1, 2, c=3)

**参考答案**：0

**解析**：func(1, 2, 3) 全部按位置传参，是最纯粹的位置参数调用。其他选项使用了关键字参数，不属于纯位置调用。

### single_choice · None



- [A] 实参按从左到右的顺序依次绑定到形参
- [B] 实参可以任意顺序，Python 会自动匹配类型
- [C] 位置参数必须全部使用关键字方式传递
- [D] 位置参数在定义时不需要写形参名

**参考答案**：0

**解析**：位置参数的核心规则是按顺序一一绑定。Python 不会按类型或名字自动匹配，定义时也必须写形参名。

### single_choice · None



- [A] width = 5, height = 3
- [B] width = 3, height = 5
- [C] width = 5, height = 5
- [D] width = 3, height = 3

**参考答案**：0

**解析**：第一个位置实参 5 绑定到第一个形参 width，第二个位置实参 3 绑定到 height，所以 width=5, height=3。

### single_choice · None



- [A] 从 5.0 变成 0.2
- [B] 仍然是 5.0，因为除法交换律
- [C] 抛出 ZeroDivisionError
- [D] 从 5.0 变成 20.0

**参考答案**：0

**解析**：位置参数顺序不同，a 和 b 的绑定值互换，10/2=5.0 变成 2/10=0.2。这体现位置参数顺序对结果的直接影响。

### single_choice · None



- [A] 'ababab'
- [B] '333'
- [C] 报错，因为参数类型不匹配预期
- [D] 'ab' 重复 3 次但返回列表

**参考答案**：0

**解析**：按位置绑定 text=3, times='ab'，表达式 3 * 'ab' 等价于 'ab' * 3，结果 'ababab'。Python 的 * 对整数和字符串都支持重复。

### single_choice · None



- [A] a=1, b=2, c=3
- [B] a=1, b=10, c=20
- [C] a=1, b=3, c=2
- [D] 抛出 TypeError

**参考答案**：0

**解析**：位置实参按从左到右的顺序依次绑定到位置形参 a、b、c，默认值 b=10、c=20 在此被 2、3 覆盖。

### single_choice · None



- [A] f(a=5, b=2)
- [B] f(5, a=2)
- [C] f(b=2, 5)
- [D] f(5, b=2, 3)

**参考答案**：0

**解析**：关键字实参可单独使用；但一旦使用了关键字实参，后面不能再出现位置实参，因此 f(5, a=2) 中 a 重复；f(b=2, 5) 语法非法；f(5, b=2, 3) 位置实参在关键字实参之后非法。

### multi_choice · None



- [A] 关键字实参按形参名匹配，与传入顺序无关
- [B] 关键字实参可以传给 *args 收集的位置参数
- [C] 调用时位置实参必须出现在关键字实参之前
- [D] 关键字实参可以重复传入同一形参（后者覆盖前者的值）
- [E] 使用关键字传参可以提高调用可读性，尤其是参数较多的函数

**参考答案**：[0, 2, 4]

**解析**：*args 收集的是位置实参，关键字实参无法落入 *args（会进入 **kwargs 或引发错误）；重复传入同一形参会引发 TypeError，不会覆盖。因此只有 0、2、4 正确。

### multi_choice · None



- [A] 使用单独的 * 可以界定其后形参为仅限关键字
- [B] 仅限关键字形参必须提供默认值，否则调用必须显式传入
- [C] 在已有 *args 的情况下，其后的形参默认也是仅限关键字形参
- [D] 仅限关键字形参可以用位置方式传递，只要顺序正确
- [E] 函数内的 **kwargs 也可以接收仅限关键字形参

**参考答案**：[0, 1, 2]

**解析**：仅限关键字形参不能以位置方式传入（D 错）；**kwargs 收集的是「未匹配任何形参」的关键字实参，已匹配到仅限关键字形参的不在其内（E 错）。A、B、C 均符合 Python 语义。

### multi_choice · None



- [A] f(1)
- [B] f(1, 2, 3, 4)
- [C] f(1, b=2)
- [D] f(1, a=2, b=3)

**参考答案**：[0, 1, 3]

**解析**：f(1) 缺少 b；f(1,2,3,4) 多传了位置实参；f(1, a=2, b=3) 中 a 既被位置传入又被关键字传入，属于重复赋值。f(1, b=2) 合法，c 用默认值。

### multi_choice · None



- [A] 使用 None 作为默认值，在函数体内判断后再创建新对象
- [B] 将可变默认参数改为不可变对象（如元组）
- [C] 在函数内部对参数重新赋值为新对象而不是原地修改
- [D] 把默认值改成类级别的可变属性，让所有调用共享
- [E] 在函数体内使用 default.copy() 后再修改副本

**参考答案**：[0, 1, 2, 4]

**解析**：D 会让多个调用共享同一对象，问题更严重。A、B、C、E 都能避免默认参数被跨调用共享修改。

### fill_blank · None



**参考答案**：["*", "* ,", "*,", "*,"]

**解析**：在位置形参之后使用单独的 *，其后的形参即成为仅限关键字形参，必须以关键字方式传入。

### fill_blank · None



**参考答案**：["前面", "之前", "左边"]

**解析**：位置实参必须出现在关键字实参之前，例如 f(1, b=2) 合法，f(b=2, 1) 语法错误。

### code_reading · None



**参考答案**：10

**解析**：a=1、b=2 由位置传入；c 是仅限关键字形参，显式传入 3；d 使用默认值 4。结果为 1+2+3+4=10。

### code_reading · None



**参考答案**：1 (2, 3) {'y': 4, 'z': 5}

**解析**：1 绑定到 x；多余的位置实参 2、3 被 *args 收集成元组 (2, 3)；关键字实参 y=4、z=5 被 **kwargs 收集成字典。

### code_reading · None



**参考答案**：(1, 3, (5, 7), 9, {'d': 11})

**解析**：a=1、b=3 由前两个位置实参绑定；剩余位置实参 5、7 被 *args 收集为 (5, 7)；c=9 是仅限关键字形参；d=11 进入 **kwargs。常见错误是把 5 当成 b 或把 c=9 当成 kwargs 的一部分。

### scenario · None



**解析**：将签名改为 download(url, *, timeout, retries)，其中 * 之后的形参仅限关键字，任何传入位置实参的旧调用都会抛出 TypeError，因此需要在发布前同步更新所有调用方或提供过渡期兼容层。

### single_choice · None



- [A] (1, (2, 3), 4, {'x': 5})
- [B] (1, (2, 3, 4), 0, {'x': 5})
- [C] (1, (2, 3), 0, {'b': 4, 'x': 5})
- [D] 抛出 TypeError

**参考答案**：0

**解析**：1 绑定到 a；额外的位置实参 2、3 被 *args 收集为元组；b=4 是仅限关键字形参（在 *args 之后），因此 b 绑定到 4；x=5 落入 **kwargs。

### scenario · None



**解析**：默认值 cart=[] 只在函数定义时求值一次，因此所有未传 cart 的调用共享同一个列表。修复方式是把默认值改为 None，并在函数体内 cart = cart if cart is not None else []，或使用其他不可变默认值。

### single_choice · None



- [A] f(1, b=2)
- [B] f(1, 2)
- [C] f(a=1, b=2)
- [D] f(b=2, a=1)

**参考答案**：1

**解析**：形参 b 位于 * 之后，是仅限关键字形参，必须用关键字传递。f(1, 2) 试图用位置实参传给 b，因此 TypeError。其余三种写法都合法。

### single_choice · None



- [A] 1 2 3
- [B] 1 3 2
- [C] 抛出 TypeError
- [D] 1 2 z

**参考答案**：0

**解析**：关键字实参之间可以任意顺序，绑定时按名字匹配：z=3 绑定到形参 z，y=2 绑定到形参 y。打印顺序按形参顺序为 1 2 3。

### single_choice · None



- [A] 位置实参必须出现在关键字实参之前
- [B] 关键字实参必须出现在位置实参之前
- [C] 两者顺序任意
- [D] 两者不能混用

**参考答案**：0

**解析**：Python 规定调用时位置实参必须在关键字实参前，例如 f(1, b=2) 合法，而 f(a=1, 2) 语法非法。

### single_choice · None



- [A] * 之后的所有形参都只能通过关键字传递
- [B] * 之后的所有形参只能通过位置传递
- [C] * 仅用于声明可变位置参数
- [D] * 之后只能出现默认参数

**参考答案**：0

**解析**：在函数定义中单独的 * 用于分隔位置形参与仅限关键字形参，其后形参必须以关键字方式传入（如 f(a, *, b)）。

### single_choice · None



- [A] [1]
  [2]
- [B] [1]
  [1, 2]
- [C] [1, 2]
  [1, 2]
- [D] 抛出 TypeError

**参考答案**：1

**解析**：默认参数 b=[] 只在函数定义时求值一次，因此两次调用共用同一个列表：第一次 append(1) 得 [1]，第二次 append(2) 得 [1, 2]。这是可变默认参数的经典陷阱。

### single_choice · None



- [A] def f(a, *, b): ...
- [B] def f(a, b, *, ): ...
- [C] def f(*, a, b): ... 中 b 只能是关键字
- [D] 两者都是合法写法，但只有第一种 b 是仅限关键字

**参考答案**：0

**解析**：语法上 def f(a, *, b) 中的 b 是仅限关键字形参；而 def f(*, a, b) 一样合法，两者 b 都是仅限关键字形参。第一项的写法更直观地展示了 a 可位置可关键字。注意这题的答案只选 A，其他选项的表述并不准确（B 语法非法）。

### single_choice · None



- [A] f(1, 2, 3)
- [B] f(a=1, b=2)
- [C] f('x')
- [D] f(*[1, 2])

**参考答案**：1

**解析**：**kwargs 只能收集额外的关键字实参，因此必须用关键字方式传入。f(1,2,3) 与 f(*[...]) 都是位置实参，会引发 TypeError。
