# s2u7l1 一、一句话直觉：为什么学 pytest？ / 让测试的“准备工作”不再重复

> 来源 `content/lessons/s2u7l1.json`

## py.test.pytest_basic

# 一、一句话直觉：为什么学 pytest？

写代码时你需要不断确认“它到底还能不能跑”——`pytest` 就是把这件事自动化的工具：**你写几条断言（assert），它帮你跑一遍并清楚地告诉你哪条挂了**。

---

## 二、最小可用：一个测试文件就能跑

pytest 的约定非常简单：

- 文件名以 `test_` 开头，或 `_test.py` 结尾；
- 函数名以 `test_` 开头；
- 函数里用 Python 原生的 `assert` 做断言。

```python
# test_sample.py
def add(a, b):
    return a + b

def test_add_positive():
    assert add(1, 2) == 3

def test_add_negative():
    assert add(-1, -2) == -3
```

在终端运行：

```bash
pytest -q
```

`-q`（quiet）会让输出只保留结果摘要，方便快速浏览。

---

## 三、断言失败时，pytest 会“告诉你哪里不一样”

pytest 的杀手锏之一是 **断言重写（assertion rewriting）**：它会把 `assert` 语句拆开，失败时展示两边变量的实际值，而不像原生 `assert` 只抛一个 `AssertionError`。

```python
def test_list_equal():
    actual = [1, 2, 3, 4]
    expected = [1, 2, 3, 5]
    assert actual == expected
```

失败输出会明确标出第 4 个元素不同，而不是让你自己去“瞪眼看”。在同一条 `assert` 里比较两个数据结构时，pytest 还会做结构化的 diff 展示。

---

## 四、用 `pytest.raises` 测“该报错的地方”

很多情况下，正确的行为是“抛异常”。pytest 提供 `pytest.raises` 作为上下文管理器：

```python
import pytest

def divide(a, b):
    return a / b

def test_divide_by_zero():
    with pytest.raises(ZeroDivisionError):
        divide(1, 0)
```

还可以顺便检查异常信息：

```python
with pytest.raises(ValueError, match="must be positive"):
    raise ValueError("n must be positive")
```

`match` 接受正则表达式，用来确认错误消息符合预期。

---

## 五、参数化：一份逻辑测多组输入

写 `test_add_1`、`test_add_2`、`test_add_3` 很啰嗦。用 `@pytest.mark.parametrize` 可以把多组输入/期望值写成表格：

```python
import pytest

def add(a, b):
    return a + b

@pytest.mark.parametrize("a, b, expected", [
    (1, 2, 3),
    (0, 0, 0),
    (-1, 1, 0),
    (2**30, 2**30, 2**31),
])
def test_add(a, b, expected):
    assert add(a, b) == expected
```

每个元组会变成一条独立的测试用例（test case），失败时能精确知道是哪一组参数挂了。

---

## 六、fixture：把“准备/清理”抽出来复用

当多个测试都需要同一个对象（数据库连接、临时文件、配置等）时，用 **fixture** 抽取。测试函数通过同名参数“请求”它：

```python
import pytest

@pytest.fixture
def sample_list():
    return [1, 2, 3]

def test_len(sample_list):
    assert len(sample_list) == 3

def test_sum(sample_list):
    assert sum(sample_list) == 6
```

如果 fixture 里 `yield` 而不是 `return`，`yield` 后面的代码就变成“清理阶段”，无论测试通过还是失败都会执行：

```python
@pytest.fixture
def resource():
    r = {"open": True}
    yield r
    r["open"] = False  # teardown
```

---

## 七、小结

| 概念 | 用途 |
| --- | --- |
| `test_*.py` / `test_*` | pytest 识别测试的命名约定 |
| `assert` | 用 Python 原生断言，pytest 会给出更清晰的失败信息 |
| `pytest.raises` | 断言某段代码应抛指定异常 |
| `@pytest.mark.parametrize` | 一份逻辑跑多组数据 |
| `@pytest.fixture` | 复用测试准备/清理逻辑 |

学完这六小节，你就已经能写出可维护的测试集了。接下来多写、多跑 `pytest -q`，让“绿条”成为你的日常。

## py.test.fixture

# py.test.fixture：让测试的“准备工作”不再重复

## 一句话直觉

写测试时，你经常要在每个测试函数里重复“造数据、连数据库、启服务”这类准备工作；`pytest` 的 **fixture（夹具）** 让你把这些准备工作抽出来，声明一次，谁需要谁就用，测试代码因此变得干净、可复用、可组合。

---

## 1. 为什么需要 fixture：从重复准备说起

假设你要测试一个“购物车结算”函数。每个测试都要先造一个购物车、放两件商品、算好预期总价。如果每个测试函数都手写一遍，会出现三个问题：

1. **重复**：同样的准备代码抄 N 遍。
2. **脆弱**：商品价格一改，所有测试都要改。
3. **难组合**：有的测试需要空购物车，有的需要打折购物车，靠复制粘贴很难管理。

`pytest` 的 fixture 就是来解决这个问题的。

先看一个不用 fixture 的写法（痛点版）：

```python
# test_cart_no_fixture.py
def test_total_two_items():
    cart = {"apple": 3, "banana": 5}
    assert sum(cart.values()) == 8

def test_total_empty():
    cart = {}
    assert sum(cart.values()) == 0
```

两个测试都在自己造 `cart`，虽然这里简单，但真实项目里“造 cart”可能是十行代码。

---

## 2. 第一个 fixture：用 `@pytest.fixture` 声明准备逻辑

一个 **fixture** 就是一个被 `@pytest.fixture` 装饰的函数。测试函数只要把 fixture 的名字写进参数列表，`pytest` 就会自动调用它，并把返回值注入进来。

```python
# test_cart_fixture.py
import pytest

@pytest.fixture
def cart():
    # 准备阶段：返回一个购物车（字典）
    return {"apple": 3, "banana": 5}

def test_total(cart):          # 参数名 = fixture 名
    assert sum(cart.values()) == 8

def test_has_apple(cart):
    assert "apple" in cart
```

关键点：

- fixture 名 `cart` 就是“依赖声明”，测试函数不需要自己调用它。
- 同一个 fixture 在同一个测试里只会被调用一次（默认作用域内缓存）。
- fixture 可以返回任意对象：字典、对象实例、数据库连接、临时目录路径等。

---

## 3. 进阶：作用域（scope）、yield 清理、自动使用

### 3.1 scope：控制 fixture 的生命周期

默认 `scope="function"`，每个测试函数都重新执行一次 fixture。对“启动一次数据库、所有测试共用”的场景，可以用 `scope="session"` 或 `scope="module"`。

```python
import pytest

# 整个测试会话只执行一次
@pytest.fixture(scope="session")
def db_connection():
    print("\n[setup] 连接数据库（只执行一次）")
    conn = {"connected": True}
    yield conn
    print("[teardown] 关闭数据库连接")

def test_a(db_connection):
    assert db_connection["connected"]

def test_b(db_connection):
    assert db_connection["connected"]
```

运行 `pytest -s` 会看到 `[setup]` 只打印一次，`[teardown]` 在会话结束时打印一次。

### 3.2 yield：setup 和 teardown 写在一起

把 `return` 换成 `yield`，`yield` 之前是准备，之后是清理。即使测试失败，清理代码也会执行。

```python
import pytest

@pytest.fixture
def temp_file(tmp_path):    # tmp_path 是 pytest 内置 fixture，提供临时目录
    f = tmp_path / "data.txt"
    f.write_text("hello")
    yield f                 # 测试拿到 f
    # 清理：删除临时文件（tmp_path 本身会被 pytest 自动清理）
    f.unlink()

def test_read(temp_file):
    assert temp_file.read_text() == "hello"
```

### 3.3 autouse：自动应用

如果某个 fixture 不需要测试显式声明、但每次都要执行（比如“每个测试前重置日志”），用 `autouse=True`。

```python
import pytest

@pytest.fixture(autouse=True)
def reset_counter():
    global counter
    counter = 0
    yield
    counter = 0

def test_counter_increments():
    global counter
    counter += 1
    assert counter == 1
```

---

## 4. 组合：fixture 可以依赖别的 fixture

这是 fixture 最强大的地方。你可以像搭积木一样组合准备逻辑：

```python
import pytest

@pytest.fixture
def user():
    return {"id": 1, "name": "alice"}

@pytest.fixture
def cart_with_user(user):
    # 依赖 user fixture，pytest 会先准备好 user
    return {"user": user, "items": ["apple", "banana"]}

def test_cart_belongs_to_user(cart_with_user):
    assert cart_with_user["user"]["name"] == "alice"
    assert len(cart_with_user["items"]) == 2
```

`pytest` 会自动解析依赖顺序，不需要你手动调用 `user()`。

---

## 5. fixture 与参数化：一个 fixture，多种数据

配合 `@pytest.fixture(params=[...])`，可以让 fixture 对多组数据各跑一遍，测试函数自动被参数化：

```python
import pytest

@pytest.fixture(params=[0, 1, 3])
def number(request):     # request 是 pytest 内置对象，能拿到当前参数
    return request.param

def test_square_non_negative(number):
    assert number ** 2 >= 0
```

运行后会看到 `test_square_non_negative[0]`、`[1]`、`[3]` 三个测试。

---

## 动手练习

**任务**：用 fixture 重构一个“待办事项（Todo）列表”的测试。

1. 新建 `test_todo.py`。
2. 写一个 `todo_list` fixture，返回一个空列表 `[]`。
3. 写一个 `filled_todo` fixture，依赖 `todo_list`，往里面加三条待办，返回这个列表。
4. 写两个测试：
   - `test_empty(todo_list)`：断言列表为空。
   - `test_filled(filled_todo)`：断言长度为 3，且包含 `"写代码"`。
5. 再写一个 `scope="session"` 的 fixture `app_config`，返回 `{"debug": True}`，写一个测试断言 `debug` 为 `True`。
6. 运行 `pytest -v test_todo.py`，观察每个测试的 fixture 依赖是否如预期。

**加分**：把 `todo_list` 的 `return` 改成 `yield`，在 `yield` 后打印 `"清理 todo"`，观察测试输出。

---

## 小结

| 概念 | 作用 |
|---|---|
| `@pytest.fixture` | 声明一个可复用的准备函数 |
| 测试参数名 | 声明“我需要这个 fixture” |
| `scope` | 控制 fixture 执行频率（function/module/session） |
| `yield` | 同时写 setup 和 teardown |
| `autouse=True` | 自动应用，无需显式声明 |
| fixture 嵌套 | fixture 可以依赖 fixture，自动解析顺序 |
| `params` | 一个 fixture 多组数据，自动参数化 |

记住一句话：**fixture 让测试的“准备”和“清理”变成可声明、可组合、可复用的零件，而不是散落在每个测试函数里的复制粘贴。**


---

## 本课题目

### single_choice · None



- [A] test_calc.py
- [B] calc_test.py
- [C] testing_calc.py
- [D] calc.test.py

**参考答案**：0

**解析**：pytest 默认按文件名模式 test_*.py 或 *_test.py 收集测试，calc_test.py 也符合 *_test.py 模式，但测试函数命名同样需要匹配；这里最典型、最常见的约定是 test_calc.py。选项 C、D 不符合默认命名规则。

### single_choice · None



- [A] test_add 和 check_add 都会执行
- [B] 只有 test_add 会执行
- [C] 只有 check_add 会执行
- [D] 两个都不会执行

**参考答案**：1

**解析**：pytest 默认只收集以 test_ 开头的函数作为测试函数，check_add 不满足命名规则，不会被自动收集。

### single_choice · None



- [A] 1 个
- [B] 2 个
- [C] 3 个
- [D] 4 个

**参考答案**：1

**解析**：参数列表中给出了两组数据 (1,2) 和 (3,4)，pytest 会为每组数据生成一个独立测试用例，共 2 个。

### single_choice · None



- [A] pytest -k add
- [B] pytest -x add
- [C] pytest -m add
- [D] pytest -q add

**参考答案**：0

**解析**：-k 用于按名称关键字筛选测试；-x 是遇到失败即停止，-m 是按标记筛选，-q 是安静模式减少输出。

### single_choice · None



- [A] pytest -k
- [B] pytest -x
- [C] pytest -m
- [D] pytest -s

**参考答案**：1

**解析**：-x 表示遇到第一个失败就退出；-k 是名称筛选，-m 是标记筛选，-s 是显示打印输出。

### single_choice · None



- [A] pytest -q
- [B] pytest -x
- [C] pytest -s
- [D] pytest -v

**参考答案**：2

**解析**：-s 会关闭输出捕获，使 print 等内容直接显示；-q 是安静模式，-x 遇失败停止，-v 是详细模式。

### single_choice · None



- [A] 只有显式在命令行中指定的函数才会被执行
- [B] 必须写 __init__.py 才能被发现
- [C] 默认会递归查找匹配命名规则的文件并执行其中匹配命名规则的测试
- [D] pytest 只能发现与测试文件同名的目录中的测试

**参考答案**：2

**解析**：pytest 默认从当前目录递归收集符合 test_*.py 或 *_test.py 命名的文件，以及其中符合命名规则的测试函数/方法；不要求显式指定，也不强制要求 __init__.py。

### single_choice · None



- [A] test_add 和 helper
- [B] 只有 test_add
- [C] 只有 helper
- [D] 两个都不执行

**参考答案**：1

**解析**：pytest 会收集以 Test 开头的类，类中方法名以 test_ 开头的才会被当作测试；helper 不匹配命名规则。

### single_choice · None



- [A] 只能写在名为 teardown 的函数里
- [B] 可以让 fixture 在 return 之后通过 yield 提供清理逻辑
- [C] teardown 必须与 fixture 同名并加 _teardown 后缀
- [D] fixture 不支持任何清理操作

**参考答案**：1

**解析**：使用 yield 的 fixture 可以在 yield 之前做 setup、之后做 teardown，yield 之后的代码在测试结束后执行；不需要特殊命名的 teardown 函数。

### single_choice · None



- [A] 一个列表，列出测试函数名
- [B] 一个字符串，包含以逗号分隔的参数名
- [C] 一个字典，映射参数到值
- [D] 一个整数，表示参数个数

**参考答案**：1

**解析**：第一个参数是字符串形式的参数名列表（以逗号分隔），也可以是字符串序列；第二个参数是对应的数据集合。

### single_choice · None



- [A] 通过
- [B] 失败，并可能展示断言表达式两侧的值
- [C] 跳过
- [D] 预期失败

**参考答案**：1

**解析**：assert False 会触发断言失败，pytest 将测试标记为失败，并利用断言重写机制展示相关表达式的中间值，便于定位问题。

### single_choice · None



- [A] pytest 可以运行用 unittest 风格编写的测试
- [B] pytest 完全不能识别 unittest.TestCase 子类
- [C] 必须把所有测试改写成 pytest 风格才能在 pytest 中运行
- [D] pytest 只能运行 pytest 专属的测试函数

**参考答案**：0

**解析**：pytest 兼容 unittest 风格，可以直接收集并运行 unittest.TestCase 子类中的测试方法；同时它也能运行 pytest 风格的函数。

### single_choice · None



- [A] assert 3 * 4 = 12
- [B] assert (3 * 4 == 12)
- [C] assert 3 * 4 == 12
- [D] assert 3 * 4 === 12

**参考答案**：2

**解析**：Python 的 assert 语句语法为 assert 表达式，等值比较使用 ==；= 是赋值，=== 不是 Python 运算符。

### single_choice · None



- [A] 必须使用 assertEqual 等专用断言方法
- [B] 只能使用 assertTrue 和 assertFalse
- [C] 可以直接使用 Python 原生的 assert 语句
- [D] 必须导入 pytest.assert 才能使用断言

**参考答案**：2

**解析**：pytest 直接复用 Python 原生的 assert 语句，无需专用的断言方法；assertEqual 等属于 unittest 风格。

### single_choice · None



- [A] @pytest.mark.xfail
- [B] @pytest.mark.skip
- [C] @pytest.mark.fail
- [D] @pytest.mark.error

**参考答案**：0

**解析**：pytest 使用 @pytest.mark.xfail 标记预期失败的测试；@pytest.mark.skip 是跳过测试，fail 和 error 不是内置标记。

### single_choice · None



- [A] @pytest.mark.xfail
- [B] @pytest.mark.skip
- [C] @pytest.mark.ignore
- [D] @pytest.mark.pass

**参考答案**：1

**解析**：@pytest.mark.skip 用于无条件跳过测试；xfail 是预期失败；ignore 和 pass 不是内置标记。

### single_choice · None



- [A] scope="session"
- [B] scope="module"
- [C] scope="class"
- [D] scope="function"

**参考答案**：3

**解析**：fixture 的 scope 默认为 function，表示每个测试函数调用一次；session 是整个测试会话一次，module 是每个模块一次，class 是每个类一次。

### single_choice · None



- [A] @pytest.fixture
  def resource():
      return object()
- [B] @pytest.setup
  def resource():
      return object()
- [C] def fixture_resource():
      return object()
- [D] @fixture
  def resource():
      return object()

**参考答案**：0

**解析**：pytest 中使用 @pytest.fixture 装饰器定义 fixture；@pytest.setup 和自造 @fixture 都不存在，单纯以 fixture_ 命名不会被识别为 fixture。

### single_choice · None



- [A] def test_query(db):
- [B] def test_query(fixture_db):
- [C] def test_query(db=fixture):
- [D] def test_query(*db):

**参考答案**：0

**解析**：pytest 通过测试函数参数名匹配同名 fixture 并自动注入；不需要特殊前缀，也不能用默认值或其他形式替代。

### single_choice · None



- [A] 使用 @pytest.mark.parametrize 可以为同一测试函数提供多组输入
- [B] 参数化必须配合 unittest.TestCase 子类使用
- [C] 只有 fixture 支持参数化，测试函数不支持
- [D] 参数化后每组数据只能包含一个参数

**参考答案**：0

**解析**：@pytest.mark.parametrize 用于为测试函数提供多组参数，每组数据可以有多个参数；无需继承 unittest.TestCase；fixture 参数化和测试函数参数化是两种不同能力。

### single_choice · None



- [A] fixture 只能用来创建数据库连接，不能做其他事情
- [B] fixture 用于为测试函数提供可复用的准备数据和资源，并可选择在测试后做清理
- [C] fixture 是一个断言工具，用来替代 assert 语句
- [D] fixture 只能定义在 conftest.py 中，不能在测试文件中定义

**参考答案**：1

**解析**：fixture 的核心作用是提供测试所需的资源或前置状态，并通过 yield 或 finalizer 支持清理；它既可用于数据库，也可用于临时文件、配置对象等，且可定义在测试文件或 conftest.py 中。

### single_choice · None



- [A] resource 必须用 @pytest.mark.usefixtures 声明后 test_demo 才能使用
- [B] test_demo 通过参数名 resource 请求 fixture，pytest 会自动注入其返回值
- [C] test_demo 中 resource 得到的是函数对象本身，而不是返回值
- [D] resource fixture 只能被名为 resource 的测试文件使用

**参考答案**：1

**解析**：pytest 通过测试函数的参数名与 fixture 名称匹配来解析并注入 fixture 的返回值，无需额外声明；参数拿到的是 fixture 的返回值而非函数对象。

### multi_choice · None



- [A] fixture 可以返回一个值，也可以只做副作用而不返回值
- [B] fixture 可以被多个测试函数复用
- [C] fixture 的名称必须与测试函数参数名一致才能被注入
- [D] fixture 只能定义在 conftest.py 中
- [E] fixture 可以依赖其他 fixture

**参考答案**：[0, 1, 2, 4]

**解析**：fixture 可返回值或仅做副作用，可复用，可通过参数名匹配注入，可相互依赖；它并非只能定义在 conftest.py，也可定义在测试模块或类中。

### multi_choice · None



- [A] function
- [B] class
- [C] module
- [D] package
- [E] process

**参考答案**：[0, 1, 2, 3]

**解析**：pytest 支持的 scope 包括 function、class、module、package、session；process 不是有效的 scope 取值。

### multi_choice · None



- [A] 每个测试前都需要重置某个全局计数器
- [B] 需要为每个测试自动准备并清理临时目录
- [C] 只想让部分测试使用的数据库连接对象
- [D] 需要在每个测试前后打印日志分隔线以方便排查
- [E] 希望某个 fixture 的返回值自动成为所有测试的参数

**参考答案**：[0, 1, 3]

**解析**：autouse 适合对所有（或某作用域内）测试统一生效的副作用，如状态重置、临时资源准备/清理、日志分隔；它不会自动注入返回值，也不适合只给部分测试使用的资源。

### multi_choice · None



- [A] yield 之后的代码在测试函数执行完毕后运行
- [B] 如果测试失败，yield 之后的清理代码默认仍会执行
- [C] yield 之后的代码可以使用 try/finally 保证清理一定会执行
- [D] 如果 fixture 中有多个 yield，pytest 会依次执行所有 yield 之后的代码
- [E] yield 之后不能访问 yield 之前定义的局部变量

**参考答案**：[0, 1, 2]

**解析**：yield 后代码是 teardown，测试失败时也会执行；可用 try/finally 保证清理；一个 fixture 中通常只有一个 yield，yield 后可访问之前定义的局部变量。

### multi_choice · None



- [A] 使用 params 后，依赖该 fixture 的测试会对每个参数值各运行一次
- [B] params 中的值可以通过 request.param 在 fixture 内部访问
- [C] params 只能用于 function 作用域的 fixture
- [D] 使用 params 时通常需要配合 request fixture 来获取当前参数值
- [E] params 与 ids 参数可以一起使用，为每个参数值指定可读的测试 ID

**参考答案**：[0, 1, 3, 4]

**解析**：fixture 参数化会让依赖它的测试对每个参数各执行一次，参数值通过 request.param 获取，ids 可自定义显示 ID；params 可用于多种作用域，不限于 function。

### fill_blank · None



**参考答案**：["yield"]

**解析**：yield 风格 fixture 中，yield 之前的代码用于 setup，yield 之后的代码用于 teardown，因此清理代码应写在 yield 之后。

### fill_blank · None



**参考答案**：["autouse"]

**解析**：autouse=True 会让 fixture 自动应用到其作用域内的测试，无需测试函数通过参数请求。

### code_reading · None



**参考答案**：setup\ntest_a\nteardown\nsetup\ntest_b\nteardown

**解析**：setup 作用域为 function，因此每个测试函数都会重新执行一次：先打印 setup，再执行测试打印 test_a，测试结束后执行 teardown；test_b 同理。

### code_reading · None



**参考答案**：正常运行通过：session 作用域的 a 先被创建并返回 1，function 作用域的 b 依赖 a，得到 2，test_ok 断言通过。

**解析**：这是合法的依赖方向：生命周期较短的 function 作用域 fixture b 依赖生命周期较长的 session 作用域 fixture a，pytest 能够正确解析，不会报作用域错误。

### scenario · None



**解析**：常见方案是用 session 作用域的 fixture 建立并复用昂贵连接，在会话结束时关闭；再用一个 function 作用域的 fixture（依赖 session fixture）在每个测试前后清理数据。这样兼顾连接复用与测试隔离；清理逻辑通常放在 yield 之后。

### single_choice · None



- [A] scope="function" 的 fixture 在整个测试会话中只执行一次
- [B] scope="session" 的 fixture 在整个测试会话中只执行一次，适合昂贵资源
- [C] scope 只能取 function 和 session 两个值
- [D] scope="module" 表示该 fixture 对每个测试类只执行一次

**参考答案**：1

**解析**：session 作用域的 fixture 在一个完整测试会话中只创建一次；function 是每个测试函数一次；module 是每个模块一次；scope 还可取 class、package 等。

### single_choice · None



- [A] yield 之前的代码在测试前执行，yield 之后（finally 等清理）的代码在测试结束后执行
- [B] yield 只能返回 None，所以不能用于提供资源
- [C] yield 之后的代码永远不会执行
- [D] 使用 yield 的 fixture 无法再被其他 fixture 依赖

**参考答案**：0

**解析**：带 yield 的 fixture 将 setup 放在 yield 前，teardown 放在 yield 后，能天然支持资源的建立与释放，且仍可被其他 fixture 依赖。

### single_choice · None



- [A] conftest.py 中的 fixture 只对同目录下的测试文件及其子目录生效
- [B] conftest.py 必须显式 import 到测试文件中，fixture 才会生效
- [C] conftest.py 只能存放 fixture，不能存放 hook 函数
- [D] conftest.py 中的 fixture 无法被其他 conftest.py 使用

**参考答案**：0

**解析**：conftest.py 无需导入，其 fixture 自动对所在目录及子目录生效；它也可以包含 pytest hook 函数；子目录的 conftest 可复用上层 conftest 的 fixture。

### single_choice · None



- [A] fixture 之间不能相互依赖，这段代码会报错
- [B] user fixture 通过参数 db 依赖另一个 fixture，pytest 会先构造 db 再构造 user
- [C] user fixture 必须显式调用 db() 函数才能拿到连接
- [D] test_user 必须同时声明 db 和 user 两个参数

**参考答案**：1

**解析**：fixture 可以通过声明其他 fixture 名作为参数形成依赖链，pytest 会按依赖顺序解析；测试函数只需声明直接需要的 fixture。

### single_choice · None



- [A] autouse=True 的 fixture 会自动应用到作用域内的所有测试，无需在参数中声明
- [B] autouse=True 的 fixture 会替代测试函数中的 assert
- [C] autouse=True 只能与 scope="session" 搭配使用
- [D] autouse=True 会让 fixture 的返回值自动注入到测试函数参数中

**参考答案**：0

**解析**：autouse=True 使 fixture 在作用域内自动生效，无需测试函数显式请求；它的返回值不会自动成为测试参数，除非测试函数声明该参数名。

### single_choice · None



- [A] finalizer 只在测试通过时执行，测试失败时不执行
- [B] finalizer 应在测试结束后执行清理工作，无论测试是否通过都应被执行
- [C] finalizer 只能使用一次，不能注册多个
- [D] finalizer 与 yield 不能同时使用

**参考答案**：1

**解析**：finalizer 用于测试后的清理，即使测试失败也会执行；可以通过 request.addfinalizer 注册多个，也可以与 yield 搭配。

### single_choice · None



- [A] 一个 function 作用域的 fixture 可以安全地依赖一个 session 作用域的 fixture
- [B] 一个 session 作用域的 fixture 可以依赖一个 function 作用域的 fixture，且不会有任何问题
- [C] fixture 之间不能跨作用域依赖
- [D] session 作用域的 fixture 只能依赖 session 作用域的 fixture，否则 pytest 会报错

**参考答案**：0

**解析**：作用域较窄（生命周期短）的 fixture 依赖作用域较宽（生命周期长）的 fixture 是安全的；反过来会导致 pytest 报 ScopeMismatch 错误。

### single_choice · None



- [A] 在测试函数里用 if 判断环境变量，手动调用不同函数
- [B] 使用 fixture 的 params 参数进行参数化，或使用 override（在子目录 conftest 中重定义同名 fixture）
- [C] 把两个实现写在一个 fixture 中，用 random 随机选择
- [D] pytest 不支持同一 fixture 的多种实现

**参考答案**：1

**解析**：pytest 支持通过 fixture 的 params 参数化，也支持在更靠近测试的 conftest 或模块中重定义同名 fixture 来覆盖（override），从而切换实现。
