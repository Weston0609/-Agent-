# s2u7l2 py.test.mock 教学讲义 / pytest.parametrize：一次写测试，多次跑数据

> 来源 `content/lessons/s2u7l2.json`

## py.test.mock

# py.test.mock 教学讲义

## 一句话直觉

**学 `py.test.mock`（即 `unittest.mock` 在 pytest 下的用法），是为了在不启动数据库、不发真实网络请求、不依赖外部服务的前提下，依然能对代码的行为做完整、可重复、快速的自动化测试。**

简单说：它让你"假装"某个对象已经存在、已经返回了某个结果，从而把测试聚焦在你真正要验证的逻辑上。

---

## 第 1 节：为什么需要 Mock（模拟对象）？

在真实项目里，函数往往依赖：

- 数据库连接
- HTTP API
- 时间（`datetime.now()`）
- 随机数
- 文件系统
- 第三方 SDK

如果测试真的去调用它们，就会出现：慢、不稳定、有副作用、需要凭证。  
**Mock（模拟对象）** 就是替身：它长得像真对象，行为可被人为指定，还能记录"有没有被调用、调用了几次、参数是什么"。

`unittest.mock` 是 Python 标准库自带的 mock 框架，pytest 直接兼容它；社区还有 `pytest-mock` 插件，提供更简洁的 `mocker` fixture（夹具）。本讲义使用标准库 `unittest.mock`，无需额外安装。

```python
# demo1.py
from unittest.mock import Mock

# 创建一个 Mock 对象
m = Mock()

# 默认情况下，Mock 调用会返回一个新的 Mock
result = m(1, 2, 3)
print("返回值是 Mock 吗？", isinstance(result, Mock))  # True

# 它可以记录调用信息
m.assert_called_once_with(1, 2, 3)
print("调用次数:", m.call_count)          # 1
print("最后一次调用参数:", m.call_args)   # call(1, 2, 3)
```

**结论：** Mock 是"万能替身"，默认什么都能调，返回值还是 Mock，同时悄悄记录每次调用。

---

## 第 2 节：`return_value` 与 `side_effect`——控制 Mock 的行为

Mock 默认返回另一个 Mock，但测试通常需要它返回**具体的值**或**抛出异常**。

- `return_value`：调用时返回什么
- `side_effect`：调用时执行什么（函数、异常、可迭代对象）

```python
# demo2.py
from unittest.mock import Mock

# 1) return_value：固定返回值
fake_db = Mock()
fake_db.get_user.return_value = {"id": 1, "name": "Alice"}
print(fake_db.get_user(1))  # {'id': 1, 'name': 'Alice'}

# 2) side_effect 为函数：可以动态返回
fake_db.get_age.side_effect = lambda uid: uid * 10
print(fake_db.get_age(3))   # 30

# 3) side_effect 为异常：模拟失败
def boom(*args, **kwargs):
    raise ConnectionError("数据库连不上")

fake_db.query.side_effect = boom
try:
    fake_db.query("SELECT 1")
except ConnectionError as e:
    print("捕获异常:", e)

# 4) side_effect 为可迭代对象：每次调用返回下一个值
fake_db.next_id.side_effect = [101, 102, 103]
print(fake_db.next_id(), fake_db.next_id(), fake_db.next_id())  # 101 102 103
```

**结论：** `return_value` 管"返回什么"，`side_effect` 管"发生什么"——异常、动态逻辑、序列轮询都靠它。

---

## 第 3 节：`patch`——把真实依赖临时替换成 Mock

光创建 Mock 不够，关键是让**被测代码真正用上它**。做法是用 `unittest.mock.patch` **打补丁（patch）**，它会在 `with` 块或装饰器范围内临时替换某个名字，结束后自动还原。

**重要规则：patch 的是"被测模块里引用的名字"，不是"定义的地方"。**

```python
# app.py
import requests

def fetch_status(url: str) -> int:
    resp = requests.get(url)
    return resp.status_code
```

```python
# demo3.py
from unittest.mock import patch
import app

# 关键：patch 的是 app 模块里的 requests，而不是 requests 库本身
with patch("app.requests.get") as fake_get:
    fake_get.return_value.status_code = 200
    print(app.fetch_status("https://example.com"))  # 200
    fake_get.assert_called_once_with("https://example.com")

# 出了 with，requests.get 自动还原
```

也可以写成装饰器：

```python
# demo3b.py
from unittest.mock import patch
import app

@patch("app.requests.get")
def test_fetch_status(fake_get):
    fake_get.return_value.status_code = 404
    assert app.fetch_status("https://x") == 404
```

**结论：** `patch` 是 mock 的"接线员"——把 Mock 接到被测代码真正调用的那个名字上，用完自动还原。

---

## 第 4 节：pytest 里更舒服的写法——`pytest-mock` 与 `mocker`

如果你的项目允许安装插件，`pytest-mock` 提供 `mocker` fixture，写法更短，且自动清理，不需要 `with`：

```python
# test_app_with_mocker.py
# 需先安装: pip install pytest-mock
import app

def test_fetch_status(mocker):
    fake_get = mocker.patch("app.requests.get")
    fake_get.return_value.status_code = 200
    assert app.fetch_status("https://example.com") == 200
    fake_get.assert_called_once()
```

`mocker` 相比原生 `patch` 的好处：

- 不用 `with`，代码更平
- 自动在测试结束后还原
- 还能 `mocker.spy(obj, "method")` 只记录调用、不改变原行为

**没有插件也没关系**：`unittest.mock` 已经够用，pytest 会原样识别 `assert` 和异常，测试依然好写。

**结论：** 原生 `patch` 是底座；`pytest-mock` 的 `mocker` 是便捷外壳，两者语义一致，按项目依赖选择即可。

---

## 第 5 节：断言调用——Mock 的另一半价值

Mock 不只"返回东西"，它还能证明"你的代码确实按预期调用了依赖"。常用断言方法：

| 方法 | 含义 |
|---|---|
| `assert_called()` | 至少被调用过一次 |
| `assert_called_once()` | 恰好一次 |
| `assert_called_with(*a, **kw)` | 最后一次调用参数匹配 |
| `assert_called_once_with(*a, **kw)` | 恰好一次且参数匹配 |
| `assert_any_call(*a, **kw)` | 曾经以某参数调用过 |
| `assert_not_called()` | 从未调用 |
| `.call_args_list` | 所有调用记录 |

```python
# demo5.py
from unittest.mock import Mock

notifier = Mock()
notifier.send("a@x.com", "欢迎")
notifier.send("b@x.com", "欢迎")

notifier.assert_called()                          # 至少一次
assert notifier.call_count == 2                   # 两次
notifier.assert_any_call("a@x.com", "欢迎")        # 曾用过这组参数
assert notifier.call_args_list[1].args == ("b@x.com", "欢迎")
```

**结论：** 断言调用让你能验证"协作关系"，这是纯返回值断言无法覆盖的。

---

## 小结

1. Mock 是依赖替身，让测试快、稳、可重复。
2. `return_value` 决定返回什么，`side_effect` 决定发生什么。
3. `patch` 负责把 Mock 接到被测代码实际引用的名字上。
4. `pytest-mock` 的 `mocker` 是更顺手的封装，语义不变。
5. 断言调用能验证代码与依赖的交互行为。

```python
# full_example.py
# 运行: python full_example.py
# 依赖: 仅标准库 unittest.mock

from unittest.mock import patch, Mock

# ---------- 被测代码 ----------
class WeatherClient:
    def get_temp(self, city: str) -> int:
        raise NotImplementedError("真实环境中会发 HTTP 请求")


def is_hot(city: str, client: WeatherClient, threshold: int = 30) -> bool:
    """判断城市是否炎热：温度 > 阈值。"""
    return client.get_temp(city) > threshold


# ---------- 测试 ----------

def test_is_hot_true():
    fake = Mock(spec=WeatherClient)          # spec 限制为 WeatherClient 的接口
    fake.get_temp.return_value = 35
    assert is_hot("Beijing", fake) is True
    fake.get_temp.assert_called_once_with("Beijing")


def test_is_hot_false():
    fake = Mock(spec=WeatherClient)
    fake.get_temp.return_value = 20
    assert is_hot("Beijing", fake) is False


def test_api_failure_bubbles_up():
    fake = Mock(spec=WeatherClient)
    fake.get_temp.side_effect = ConnectionError("网络不通")
    try:
        is_hot("Beijing", fake)
    except ConnectionError as e:
        assert "网络不通" in str(e)
    else:
        raise AssertionError("应当抛出 ConnectionError")


def test_patch_module_reference():
    """演示 patch 替换"定义处的引用"。"""
    with patch("__main__.is_hot", return_value=True) as fake_is_hot:
        assert is_hot("Anywhere", Mock()) is True
        fake_is_hot.assert_called_once()


if __name__ == "__main__":
    test_is_hot_true()
    test_is_hot_false()
    test_api_failure_bubbles_up()
    test_patch_module_reference()
    print("全部测试通过 ✅")
```

## py.test.parametrize

# pytest.parametrize：一次写测试，多次跑数据

> 一句话直觉：**当同一个测试逻辑需要对很多组输入验证时，`@pytest.mark.parametrize` 让你只写一个测试函数，就能自动跑出 N 条独立测试用例，失败时还能精确告诉你"是哪组数据挂了"。**

---

## 0. 为什么需要它（Why）

假设你要测试一个加法函数 `add(a, b)`，想验证：

- `1 + 1 == 2`
- `2 + 3 == 5`
- `0 + 0 == 0`
- `-1 + 1 == 0`

最朴素的写法是写四个测试函数，或者在一个函数里写四个 `assert`。前者重复、啰嗦；后者一旦第一个 `assert` 失败，后面就不再执行，你只能一次次修复再重跑。

`pytest.parametrize`（参数化）解决的正是这个问题：**把"测试数据"从"测试逻辑"中剥离出来**。逻辑写一遍，数据用列表给一串，pytest 自动为每一组数据生成一条独立的测试记录。

这是 pytest（Python 生态最流行的测试框架）最常用、也最能提升代码质量的功能之一。

---

## 1. 最小可用示例：看懂基本写法

`parametrize` 是一个装饰器（decorator），通过 `pytest.mark.parametrize` 使用。它的签名核心是：

```python
@pytest.mark.parametrize("参数名", [值1, 值2, ...])
```

- 第一个参数是字符串，表示要注入的**参数名**（可以多个，用逗号分隔）。
- 第二个参数是一个**可迭代对象**（iterable），每个元素对应一条测试用例。

```python
# test_add.py
import pytest

def add(a, b):
    return a + b

@pytest.mark.parametrize("a, b, expected", [
    (1, 1, 2),
    (2, 3, 5),
    (0, 0, 0),
    (-1, 1, 0),
])
def test_add(a, b, expected):
    # pytest 会依次把每一行元组填进 a / b / expected
    assert add(a, b) == expected
```

在终端运行 `pytest -v test_add.py`，你会看到类似输出：

```
test_add.py::test_add[1-1-2] PASSED
test_add.py::test_add[2-3-5] PASSED
test_add.py::test_add[0-0-0] PASSED
test_add.py::test_add[-1-1-0] PASSED
```

方括号里 `[1-1-2]` 就是 pytest 自动生成的**用例 ID**（test case ID）。四条数据 → 四个独立的测试条目，某一条挂了不影响其它条继续跑。

> **关键点**：参数名中逗号周围的空格会被 pytest 忽略，`"a, b, expected"` 和 `"a,b,expected"` 等价。

---

## 2. 进阶：三层参数化能力

### 2.1 多参数 vs 单参数

有时你只想参数化一个参数：

```python
import pytest

def is_even(n):
    return n % 2 == 0

@pytest.mark.parametrize("n", [2, 4, 6, 8])
def test_is_even(n):
    assert is_even(n)
```

此时每条数据是一个标量，pytest 也能正确处理。

### 2.2 参数化叠加（stacking）

多个 `parametrize` 装饰器叠加会做**笛卡尔积**（Cartesian product）：

```python
import pytest

def mul(a, b):
    return a * b

@pytest.mark.parametrize("a", [1, 2])
@pytest.mark.parametrize("b", [10, 100])
def test_mul(a, b):
    # 会生成 2 × 2 = 4 条用例：
    # (a=1,b=10), (a=1,b=100), (a=2,b=10), (a=2,b=100)
    assert mul(a, b) == a * b
```

这让「相同的逻辑 × 不同的输入维度」组合变得极其简洁。

### 2.3 给用例起可读的名字：`ids`

默认的 ID 是把参数值拼起来，可读性常常很差（比如对象会显示成内存地址）。用 `ids` 参数自定义：

```python
import pytest

def login(username, password):
    return username == "admin" and password == "123456"

@pytest.mark.parametrize(
    "username, password, ok",
    [
        ("admin", "123456", True),
        ("admin", "wrong",  False),
        ("guest", "123456", False),
    ],
    ids=["correct-creds", "wrong-password", "wrong-user"],
)
def test_login(username, password, ok):
    assert login(username, password) is ok
```

失败时输出会写成 `test_login[wrong-password]` 而不是一串原始值，排查问题轻松得多。

### 2.4 在数据里加标记：`pytest.param`

当某条数据你希望带上额外信息（如 `xfail` 预期失败、自定义 id）时，用 `pytest.param(...)` 包裹：

```python
import pytest

def parse_int(s):
    return int(s)

@pytest.mark.parametrize("s, expected", [
    ("1", 1),
    pytest.param("abc", None, marks=pytest.mark.xfail(reason="非法输入")),
])
def test_parse_int(s, expected):
    # 第二条预期会抛异常，pytest 会记为 xfail 而不是 failure
    assert parse_int(s) == expected
```

---

## 3. 内部机制：pytest 到底做了什么

理解机制能避免很多困惑。

当你写：

```python
@pytest.mark.parametrize("x", [1, 2, 3])
def test_f(x): ...
```

pytest 在**收集阶段（collection）**会做三件事：

1. 把 `parametrize` 存下来的数据展开成一个"用例列表"。
2. 对每一组数据，复制测试函数的一份"虚拟副本"，并绑定好该组参数。
3. 给每条用例生成一个唯一 ID（默认 = 把参数值用 `-` 串起来），用于报告和 `-k` 过滤。

所以在 `pytest -v` 里你看到的是 N 条独立的用例，而不是同一个函数被运行 N 次。

这带来几个直接好处：

- **隔离性**：任何一条用例崩了不影响其它用例的执行与汇报。
- **可选择性**：`pytest -k "1-1-2"` 只跑你想跑的用例。
- **报告清晰**：失败时会直接指出是哪一组数据挂了。

---

## 4. 工程实践建议

- **数据外置**：数据规模大时，把列表放进模块级常量或单独的数据文件（JSON/YAML/CSV），测试函数只负责逻辑，保持可读。
- **用 `ids` 代替猜 ID**：数据是复杂对象时一定加 `ids`，否则报告里的用例名会难以阅读。
- **参数名用英文标识符**：参数名本质是 Python 参数，用 `a, b, expected`、`input_, want_err` 这类清晰命名，别用中文。
- **断言写清楚**：宁可 `assert result == expected, f"{x} 处理结果不对"`，让失败信息自带上下文。
- **和 fixture 配合**：`parametrize` 常和 fixture（如数据库连接、临时目录）一起用，数据驱动 + 环境准备是 pytest 的两大支柱。
- **别滥用叠加**：多层叠加会让用例数指数级增长，注意总数量保持在可接受的运行时长内。

---

## 5. 小结

| 概念 | 作用 |
| --- | --- |
| `@pytest.mark.parametrize` | 把测试数据和测试逻辑分离 |
| 参数名 | 字符串，逗号分隔多个名字 |
| 数据列表 | 每个元素是一条用例的参数 |
| 叠加多个装饰器 | 生成笛卡尔积 |
| `ids=` | 自定义可读的用例名 |
| `pytest.param` | 单条数据附加 marks / id |

记住一句话：**`parametrize` = 循环 + 独立测试报告，且写起来是一个装饰器。**

---

## 动手练习

**任务**：为一个字符串处理函数写参数化测试。

在本地新建文件 `test_slugify.py`，实现并测试一个 `slugify(text)` 函数：把字符串转成 URL 友好的 slug（小写、空格换成连字符、去掉首尾空白），然后用 `pytest.mark.parametrize` 至少覆盖以下 5 组数据：

| 输入 | 期望输出 |
| --- | --- |
| `"Hello World"` | `"hello-world"` |
| `"  Python Rocks  "` | `"python-rocks"` |
| `"already-slug"` | `"already-slug"` |
| `"A B C"` | `"a-b-c"` |
| `""` | `""` |

**要求**：

1. 使用 `@pytest.mark.parametrize` 一次写全 5 组数据，不要写 5 个测试函数。
2. 用 `ids=[...]` 给每条用例起一个可读的名字。
3. 运行 `pytest -v test_slugify.py`，确认 5 条都 PASSED。
4. **进阶**：再故意加一条错误数据（例如把 `"Hello World"` 期望值写成 `"hello_world"`），观察失败时 pytest 报告里显示的用例 ID，理解 ID 的生成方式。

提示：实现 `slugify` 只需要 `text.strip().lower().replace(" ", "-")`。


---

## 本课题目

### single_choice · None



- [A] 访问 mock 对象上任意未定义的属性都会抛 AttributeError
- [B] 访问 mock 对象上任意未定义的属性都会自动创建一个新的 Mock
- [C] mock 对象只能访问预先通过 configure_mock 设置的属性
- [D] mock 对象上未定义的属性会返回 None

**参考答案**：1

**解析**：Mock 的特点是惰性创建子属性：访问不存在的属性时会自动生成新的 Mock 并记录在 mock_calls 相关结构中，而不是报错或返回 None。

### single_choice · None



- [A] True
- [B] False
- [C] None
- [D] 抛出异常

**参考答案**：0

**解析**：调用 mock 对象后，其 called 属性会变为 True。

### single_choice · None



- [A] 返回一个新的 Mock
- [B] 抛出 AttributeError
- [C] 返回 None
- [D] 自动将该属性加入 spec

**参考答案**：1

**解析**：spec 会限制 mock 可用的属性集合，访问未在 spec 中定义的属性会抛 AttributeError。

### single_choice · None



- [A] 会自动重置 mock 的调用记录
- [B] 会生成签名与被替换对象一致的 mock，参数不匹配时会报错
- [C] 会强制 patch 目标必须存在
- [D] 会自动把 mock 的返回值转换成真实类型

**参考答案**：1

**解析**：autospec 根据目标对象的签名生成 mock，可校验调用参数，避免因接口不匹配造成的假阳性测试。

### single_choice · None



- [A] ((1, 2), {'k': 3})
- [B] call(1, 2, k=3)
- [C] (1, 2, {'k': 3})
- [D] ['call', 1, 2, {'k': 3}]

**参考答案**：0

**解析**：call_args 返回一个 call 对象（本质是二元组），第一个元素是位置参数元组，第二个元素是关键字参数字典。

### single_choice · None



- [A] reset_mock() 会清空 return_value 和 side_effect
- [B] reset_mock() 默认只重置调用记录，不清空 return_value 与 side_effect
- [C] reset_mock() 会删除 mock 上所有子属性
- [D] reset_mock() 无法被再次调用

**参考答案**：1

**解析**：reset_mock() 默认重置调用相关信息，return_value 与 side_effect 可通过参数选择是否重置；子 mock 默认也会被递归重置，但不会删除。

### single_choice · None



- [A] patch.object 只能用于类属性，patch 只能用于模块属性
- [B] patch.object 直接引用目标对象，patch 通过字符串解析路径
- [C] 两者完全等价，可以互相替换
- [D] patch.object 不支持 new 参数

**参考答案**：1

**解析**：patch.object 接收目标对象和属性名，patch 接收点分字符串并逐级解析；前者可避免拼写路径错误，后者更灵活。

### single_choice · None



- [A] m.method.return_value = [A, B]
- [B] m.method.side_effect = [A, B]
- [C] m.method.return_value = A 再设置 B
- [D] m.method.assert_called_with(A, B)

**参考答案**：1

**解析**：side_effect 设置为列表时，每次调用按顺序取出一个元素作为返回值；return_value 设置为列表只会整体返回该列表。

### single_choice · None



- [A] assert_called_with
- [B] assert_called_once
- [C] assert_any_call
- [D] assert_called

**参考答案**：0

**解析**：assert_called_with 校验最近一次调用是否匹配给定参数（位置或关键字），其他选项只校验调用次数或是否被调用过。

### single_choice · None



- [A] 用于替换普通方法，返回值固定
- [B] 用于在 mock 对象上模拟属性，可设置其返回值
- [C] 只能用于 patch 装饰器，不能用作上下文管理器
- [D] 不能与 spec 一起使用

**参考答案**：1

**解析**：PropertyMock 模拟属性访问，常通过 patch 将该属性替换为 PropertyMock 并设置 return_value。

### single_choice · None



- [A] patch 该实例方法的引用为 Mock，并在调用后使用 assert_called_once_with 校验
- [B] 直接修改实例的 __dict__ 而不使用 patch
- [C] 使用 assert_called_with 来检查 mock 的返回值
- [D] 用 MagicMock 替换整个类并忽略实例化

**参考答案**：0

**解析**：patch 替换目标方法后可通过 mock 的 assert_called_once_with 等断言校验调用；assert_called_with 校验的是调用参数而非返回值。

### single_choice · None



- [A] create=True 时，如果属性原本不存在，patch 也会创建它
- [B] create=True 时会自动断言属性必须不存在
- [C] create 参数默认值为 True
- [D] create 参数用于控制是否创建新的 Mock 类型

**参考答案**：0

**解析**：默认 patch 要求属性存在；设置 create=True 后即使属性不存在也会被创建，方便替换不存在的目标。

### single_choice · None



- [A] return_value 必须是可调用对象
- [B] 设置 return_value 后调用 mock 返回该值
- [C] return_value 只能设置一次，再次调用会抛异常
- [D] return_value 与 side_effect 不能同时使用

**参考答案**：1

**解析**：Mock(return_value=x)() 返回 x，它可以是任意对象；side_effect 与 return_value 可以同时设置，side_effect 优先。

### single_choice · None



- [A] 第一次返回 3，第二次抛出 ValueError
- [B] 第一次抛出 ValueError，第二次返回 3
- [C] 两次都抛出 ValueError
- [D] 两次都返回 3

**参考答案**：1

**解析**：side_effect 为可迭代对象时，每次调用依次取出一个元素：异常类会被抛出，非异常值会作为返回值。

### single_choice · None



- [A] 只能是模块路径字符串
- [B] 只能是被替换的对象引用
- [C] 既可以是字符串（形如 'module.attr'）也可以是对象引用
- [D] 必须同时提供 new 参数

**参考答案**：2

**解析**：patch 的目标既可以用 '模块.属性' 字符串指定，也可以直接传入对象引用；new 参数可选，默认为 MagicMock。

### single_choice · None



- [A] new 参数必须是 Mock 实例
- [B] new 参数可以是任意对象，用于替换目标属性
- [C] new 参数只能是函数
- [D] 不指定 new 时会抛 TypeError

**参考答案**：1

**解析**：new 用于指定替换后的对象，可以是任意对象（函数、类、Mock、常量等）；不指定时默认使用 MagicMock。

### single_choice · None



- [A] patch 原定义处 'a.b'
- [B] patch 使用处所在模块中的 'b'
- [C] patch 原定义处与使用处都必须 patch
- [D] patch 任何一处效果都一样

**参考答案**：1

**解析**：from ... import 会在使用模块中绑定名字，所以必须 patch 使用方模块中持有的那个引用。

### single_choice · None



- [A] MagicMock 不能设置 return_value
- [B] MagicMock 默认支持魔术方法（如 __len__、__enter__）
- [C] MagicMock 只能用于类，不能用于函数
- [D] Mock 支持魔术方法而 MagicMock 不支持

**参考答案**：1

**解析**：MagicMock 预配置了常见魔术方法，因此可支持 len()、with、迭代等协议；两者都支持 return_value。

### single_choice · None



- [A] 断言通过并返回 True
- [B] 抛出 AssertionError
- [C] 抛出 TypeError
- [D] 断言失败但不抛异常，只返回 False

**参考答案**：1

**解析**：assert_called_once_with 要求恰好调用一次且参数匹配，否则抛出 AssertionError。

### single_choice · None



- [A] call_args 记录所有调用，mock_calls 只记录最后一次调用
- [B] mock_calls 记录对 mock 及其子 mock 的所有调用，call_args 是最后一次调用参数
- [C] method_calls 仅记录对 mock 本身直接调用，不包含子属性
- [D] 三者完全等价，只是命名不同

**参考答案**：1

**解析**：mock_calls 聚合所有调用（包括子 mock），call_args 表示最近一次调用的参数，method_calls 记录对方法和属性的调用。

### single_choice · None



- [A] @pytest.mark.parametrize('x', [1, 2, 3])
- [B] @pytest.mark.parametrize('x, y', [(1, 10), (2, 20), (3, 30)])
- [C] def test_add(x=1, y=10): ...
- [D] @pytest.mark.parametrize('x, y', [1, 10, 2, 20, 3, 30])

**参考答案**：1

**解析**：@pytest.mark.parametrize 第一个参数是逗号分隔的形参名字符串，第二个参数是一个可迭代对象，其每个元素对应一次调用。写成元组列表 [(1,10),(2,20),(3,30)] 才会生成三次用例；选项 0 只参数化了一个名称，选项 3 的扁平列表无法解包成 (x, y) 而会报参数数量不匹配的错误。

### single_choice · None



- [A] 5 条
- [B] 2 条
- [C] 3 条
- [D] 6 条

**参考答案**：3

**解析**：多个 parametrize 装饰器叠加时，参数是笛卡尔积关系，用例数等于各层列表长度之积：2 × 3 = 6。常见误解是相加得到 5，或者只取最内层列表长度。

### single_choice · None



- [A] 该组数据被视为通过，不影响最终退出码
- [B] 该组数据若断言失败则报告为 xfailed（预期失败）
- [C] 整个测试函数的其他参数集也被一并标记为预期失败
- [D] xfail 不能用于单个参数集，只能标记整个函数

**参考答案**：1

**解析**：通过 pytest.param(..., marks=pytest.mark.xfail) 可以只对某一组数据声明预期失败，不影响同函数其他参数集。这是参数化与标记结合的典型用法。

### multi_choice · None



- [A] 第二个参数可以是任意可迭代对象，包括生成器、列表、元组
- [B] 参数名与被测函数的形参名之间必须一致
- [C] 同一个测试函数上叠加多个 parametrize 会得到笛卡尔积
- [D] 参数化只能用于模块级函数，不能用于类方法
- [E] parametrize 的参数名可以引用 fixture，从而对 fixture 做参数化

**参考答案**：[0, 1, 2, 4]

**解析**：parametrize 接受任意可迭代对象；参数名需与函数签名匹配；多层叠加是笛卡尔积；参数名若与 fixture 同名，可以对 fixture 参数化（fixture 可直接使用该参数）。类方法同样可以参数化，所以「只能用于模块级函数」是错误的。

### multi_choice · None



- [A] ids 参数作用于整个 parametrize 的所有参数集
- [B] pytest.param(id=...) 作用于单个参数集，优先级高于同级参数化的 ids 列表
- [C] 如果同时给了 ids 列表和 pytest.param(id=...)，可能出现数量不匹配报错
- [D] id 里包含空格或方括号一定会导致收集失败
- [E] ids 只能是字符串列表，不能是函数

**参考答案**：[0, 1, 2]

**解析**：ids 是逐个参数集命名的列表/可调用对象，作用于该层参数化的全部参数集；pytest.param 的 id 只作用于某个具体参数集，优先级更高。当层内同时提供 ids 列表与部分 param 已带 id 时，长度/覆盖关系可能引发冲突。id 中含空格会触发 pytest 的非致命告警但不一定失败；ids 也可以是可调用对象。

### multi_choice · None



- [A] 每份数据都作为独立用例出现在报告中，失败定位更清晰
- [B] 便于对某一组数据单独指定 skip/xfail 标记
- [C] 可以减少重复样板代码，让测试更易维护
- [D] 能保证所有参数集的断言一定全部正确
- [E] 会显著加快测试执行速度

**参考答案**：[0, 1, 2]

**解析**：参数化的核心价值是「数据驱动 + 独立用例 + 可单独加标记」，能减少样板。它本身不保证断言的正确性，也不会自动提速（用例总数通常不变，甚至因为笛卡尔积而增加）。

### multi_choice · None



- [A] 当 parametrize 的参数名与某个 fixture 同名时，该 fixture 会针对每组参数被调用
- [B] fixture 内部可以通过 request.param 拿到当前参数值
- [C] 参数化 fixture 时，间接参数化可通过 indirect=True 让参数传递给 fixture 而非直接给测试函数
- [D] fixture 参数化不能和测试函数参数化共存
- [E] parametrize 只能参数化测试函数，不能影响 fixture

**参考答案**：[0, 1, 2]

**解析**：参数名与 fixture 同名即可参数化该 fixture；fixture 里用 request.param 取值；indirect=True 可让参数走 fixture 路径。fixture 参数化与函数参数化可以共存，所以最后两项错误。

### fill_blank · None



**参考答案**：["expected"]

**解析**：参数化的第三列 expected 就是本组期望值，断言应与它比较：assert a + b == expected。

### fill_blank · None



**参考答案**：["['add-positive', 'add-negative']", "[\"add-positive\", \"add-negative\"]"]

**解析**：ids 接受与参数集一一对应的字符串列表（或可调用对象），因此传入 ['add-positive', 'add-negative'] 就能在节点 ID 中显示自定义名称。

### code_reading · None



**参考答案**：共 6 条。两层 parametrize 叠加是笛卡尔积：3 个 x 与 2 个 y 组合成 3×2=6 条用例。

**解析**：多个 parametrize 装饰器的参数相互独立并做乘积组合，因此收集到的用例数是各层数据个数之积。注意最简单的（错误的）答案是 5（把个数相加），或 2/3（只取某一层个数）。

### code_reading · None



**参考答案**：在收集阶段就报错，提示参数数量不匹配：'x, y' 需要 2 个参数，但提供的元组有 3 个元素。

**解析**：parametrize 要求每组数据的元素个数与参数名个数一致，否则 pytest 在收集阶段就会报错，不会进入测试执行。

### scenario · None



**参考答案**：把四组输入与期望值集中在一个数据列表（模块常量或外部数据文件）里，用 @pytest.mark.parametrize 装饰单个测试函数；为每组数据用 ids 或 pytest.param(id=...) 起可读的名字（如 normal、discount、member、negative），这样节点 ID 与报告中会显示对应名称，失败时可直接定位；必要时对负价这类边界情况用 pytest.param(..., marks=pytest.mark.xfail) 或单独的标记区分。

**解析**：场景考察的是把重复的非参数化测试迁移为数据驱动参数化的做法。要点是：集中数据、用 parametrize 引用、给参数集起可读 id 以便定位失败，并可用 pytest.param 对个别数据附加标记。

### single_choice · None



- [A] ids 用于给形参赋默认值
- [B] ids 用来自定义每个参数集在测试报告和用例节点 ID 中显示的后缀名称
- [C] ids 必须与参数名列表一一对应，否则测试无法收集
- [D] ids 用于控制用例的执行顺序

**参考答案**：1

**解析**：ids 提供的是每个参数集的标识名，方便在 -k 选择或报告中分辨是哪一组数据。它不是默认值机制（那是函数签名的事），不控制执行顺序，也不是必需的。

### scenario · None



**参考答案**：使用 @pytest.mark.parametrize 的 ids 参数为每组数据指定可读名称，或者把每组数据写成 pytest.param(value, id='可读名') 的形式；这两种方式都会把可读名写入节点 ID 的方括号中，便于定位。对需要条件性地跳过/预期失败的个别数据，可以写成 pytest.param(..., marks=pytest.mark.skipif(...)) 或 pytest.mark.xfail，从而只影响对应参数集。

**解析**：场景的核心是以可读 id 替换默认的数值后缀，并可对个别参数集附加 skip/xfail 标记。关键在于把命名与标记收敛在参数化定义处。

### single_choice · None



- [A] 遇到第一个失败就停止整个测试函数的后续参数集
- [B] 把该参数集作为一次独立的失败报告，其他参数集继续执行
- [C] 把整个测试函数标记为 error 而不是 failed
- [D] 直接中断整个测试会话

**参考答案**：1

**解析**：参数化的每一组数据被视为一个独立的测试项，失败不会连累同函数的其他参数集，除非使用了 -x 之类的中断选项。

### single_choice · None



- [A] pytest.param 只能给值，不能传 marks 或 id
- [B] pytest.param 可以携带值、id 和 marks 等元信息，用于给特定参数集打标记
- [C] pytest.param 会把整个对象原样传给被测函数，不会解包
- [D] pytest.param 已被弃用，应该改用元组

**参考答案**：1

**解析**：pytest.param(value, id=..., marks=...) 允许为单个参数集附加 id 和标记（如 pytest.mark.skip、xfail），是给个别数据加元信息的标准做法。

### single_choice · None



- [A] 甲和乙等价，两种写法都合法
- [B] 只有甲合法，乙会报错
- [C] 只有乙合法，甲会报错
- [D] 两者都不合法，必须写成 'x y'

**参考答案**：0

**解析**：第一个参数可以是逗号分隔的字符串，也可以是字符串列表/元组；pytest 会做等价解析。写成 'x y'（空格分隔）在部分版本中也可接受，但用逗号或序列更稳妥。

### single_choice · None



- [A] pytest 自动补齐缺失的值为 None
- [B] pytest 自动截断多余的值
- [C] 该用例在收集阶段报错，提示参数数量不匹配
- [D] pytest 忽略该组数据继续运行其他组

**参考答案**：2

**解析**：参数数量必须与形参名数量一致，否则在收集阶段就会报错。pytest 不会自动补 None 也不会静默截断。

### single_choice · None



- [A] pytest test_div.py -k 'test_div[1-2]'
- [B] pytest test_div.py::test_div[1-2]
- [C] pytest test_div.py -m 'test_div[1-2]'
- [D] pytest test_div.py --param 1 2

**参考答案**：1

**解析**：带方括号的节点 ID 可以直接用 :: 定位到具体参数集。-k 虽然也可做子串匹配，但方括号内的字符在表达式中有特殊语义，容易误匹配；-m 是标记选择；--param 不是 pytest 选项。

### single_choice · None



- [A] 为每组数据复制粘贴一份测试函数
- [B] 在测试函数体内用 for 循环遍历所有数据并 assert
- [C] 把数据放在模块级列表或外部文件，用 parametrize 引用它
- [D] 只用一组数据，靠人工修改代码来换用例

**参考答案**：2

**解析**：parametrize 让每份数据成为独立用例，便于定位失败，且数据可与代码分离（模块常量、fixture、文件加载）。for 循环断言会导致一处失败就中断后面的检查，且报告里只有一条用例。

### single_choice · None



- [A] 只出现在 HTML 报告里，终端看不到
- [B] 出现在用例的节点 ID（方括号内）和测试报告标题中
- [C] 只出现在 assert 失败信息的附加说明里
- [D] 不会出现在任何地方，id 仅用于内部排序

**参考答案**：1

**解析**：自定义 id 会替换默认的数值后缀，出现在节点 ID 的方括号中，也会显示在 -v 输出和报告中，方便快速辨认失败的是哪组数据。
