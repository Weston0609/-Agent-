# s2u7l3 让测试告诉你「哪些代码从没被跑过」 / 让测试自己去找 bug

> 来源 `content/lessons/s2u7l3.json`

## py.test.coverage

# py.test.coverage：让测试告诉你「哪些代码从没被跑过」

> **一句话直觉（Why）**：写完一堆单元测试，你其实不知道测试到底"盖"住了多少代码；`py.test.coverage`（即 pytest + coverage.py 集成）就是那把 X 光机——它跑一遍测试，然后精确地告诉你每一行代码是"被执行过"还是"从没被执行过"。

前置知识点：无。本文假设你会写最基础的 `def` 和 `assert`。

---

## 1. 什么是「测试覆盖率」（Test Coverage）

**覆盖率（coverage）** 衡量的是：你的测试执行时，源代码有多少比例被真正走过。最常见的粒度是**行覆盖率（line coverage）**：统计 `.py` 文件里每一条可执行语句是否被至少执行过一次。

为什么需要它？因为"测试通过"不代表"逻辑被验证"——一段从没被调用的 `if` 分支，测试永远是绿的，但它是 bug 的温床。

覆盖率工具的事实标准是 [`coverage.py`](https://coverage.readthedocs.io/)；`pytest`（也就是历史别名 `py.test`）通过插件 **`pytest-cov`** 与它无缝集成，命令统一为 `pytest --cov=...`。

```python
# demo_math.py —— 一段薄薄的被测代码
def add(a, b):
    return a + b

def classify(n):
    if n > 0:
        return "pos"      # 分支 1
    elif n < 0:
        return "neg"      # 分支 2
    else:
        return "zero"     # 分支 3
```

如果测试里只调用了 `add(1, 2)`，`classify` 的三个分支一个都没走——覆盖率会立刻把你"测试的空洞"亮出来。

---

## 2. 安装与最小可运行示例

只需要两条命令：

```bash
pip install pytest pytest-cov
```

然后写一个测试文件：

```python
# test_demo_math.py
def test_add():
    from demo_math import add
    assert add(1, 2) == 3
```

跑一次覆盖率：

```bash
pytest --cov=demo_math --cov-report=term-missing
```

其中：
- `--cov=demo_math`：指定要统计的"模块/包名"（不是文件名），可以是 `--cov=.` 或 `--cov=src`。
- `--cov-report=term-missing`：在终端表格里额外列出**未被覆盖的行号**。

输出形如：

```
Name           Stmts   Miss  Cover   Missing
--------------------------------------------
demo_math.py       6      3    50%   4-8
```

`4-8` 就是 `classify` 那一整段没被测到——问题一眼可见。

---

## 3. 生成可读性更强的报告：HTML、XML、Fail-under

终端输出适合快速检查，但要做工程化评审，通常需要：

| 报告形式 | 命令 | 用途 |
|---|---|---|
| HTML | `--cov-report=html` | 打开 `htmlcov/index.html`，逐行染色 |
| XML | `--cov-report=xml` | 给 CI（如 Jenkins、GitLab）或 SonarQube 用 |
| 阈值门禁 | `--cov-fail-under=85` | 低于 85% 直接失败，强制质量底线 |

一次拿到全套：

```bash
pytest --cov=src --cov-report=term-missing --cov-report=html --cov-fail-under=85
```

更工程化的做法是把这些选项固化到项目根目录的 `pyproject.toml`：

```toml
# pyproject.toml
[tool.pytest.ini_options]
addopts = "--cov=src --cov-report=term-missing --cov-fail-under=85"
```

这样开发者只需敲一个 `pytest`，覆盖率约束就被自动施加。

---

## 4. 理解"覆盖率"的几种口径

`coverage.py` 能报告多种口径，别把它们混为一谈：

- **语句覆盖率（statement / line coverage）**：默认口径，只看"行有没有被执行"。
- **分支覆盖率（branch coverage）**：额外要求 `if/while/for` 的每个分支都走到，加 `--cov-branch` 开启。
- **函数覆盖率 / 类覆盖率**：主要在大纲视图中展示。

一个容易踩的坑：**100% 行覆盖率 ≠ 测试充分**。例如下面这种断言为空的测试：

```python
def test_classify_pos():
    classify(1)      # 调了，但没断言
```

行覆盖率会认为 `classify` 的 `if n > 0` 分支"被覆盖"了，可实际什么都没验证。所以覆盖率是**发现遗漏**的工具，不是**证明正确**的工具——它必须和断言（assertion）配合使用。

---

## 5. 常用 CLI 速查

| 需求 | 命令 |
|---|---|
| 覆盖指定包 | `pytest --cov=my_pkg` |
| 覆盖整个项目 | `pytest --cov=.` |
| 显示缺失行号 | `--cov-report=term-missing` |
| 生成 HTML | `--cov-report=html` |
| 开启分支覆盖 | `--cov-branch` |
| 设置最低阈值 | `--cov-fail-under=90` |
| 合并多个 run | `coverage combine` + `coverage report` |

把 `--cov-fail-under` 放进 CI 是最常见的工程化落地方式：覆盖率"只能涨不能跌"，团队就有持续改进的方向感。

```python
# demo_math.py
"""被测模块：一个加法与一个三分类函数。"""


def add(a, b):
    return a + b


def classify(n):
    if n > 0:
        return "pos"
    elif n < 0:
        return "neg"
    else:
        return "zero"


# test_demo_math.py
"""最小 pytest + coverage 示例：

运行：
    pip install pytest pytest-cov
    pytest --cov=demo_math --cov-report=term-missing

预期输出会显示 classify 的第 9-14 行未被覆盖，
再把下面被注释的用例打开，覆盖率会明显上升。
"""


def test_add():
    assert add(1, 2) == 3


def test_classify_pos():
    assert classify(1) == "pos"


# 想进一步把覆盖率抬到 100%，请补上下面两个用例：
# def test_classify_neg():
#     assert classify(-1) == "neg"
#
# def test_classify_zero():
#     assert classify(0) == "zero"
```

## py.test.hypothesis

# py.test.hypothesis：让测试自己去找 bug

## 一句话直觉

**与其手写几条测试用例，不如让机器自动生成成百上千个「刁钻输入」来轰炸你的函数。** `hypothesis` 就是 Python 生态里做这件事最成熟的库，与 `pytest` 无缝集成——你只描述「什么样的输入是合法的」，它负责找出让代码崩溃的反例。

---

## 1. 从「举例测试」到「属性测试」

传统测试写法叫 **举例测试（example-based testing）**：你手动挑几个输入，断言输出。问题很明显——你能想到的输入，往往正是你写代码时已经考虑过的；真正让你半夜加班的边界情况（空字符串、负数、极大值、Unicode 尾部空格……）不会出现在你的例子里。

**属性测试（property-based testing）** 换了个思路：你不用举例子，而是声明「对所有合法输入，某个性质必须成立」。例如排序函数，无论输入什么列表，`sorted(xs)` 都应当满足：
- 长度不变
- 结果是有序的
- 结果与 `xs` 包含相同元素

`hypothesis` 会反复随机生成 `xs` 来尝试推翻这三条性质；一旦失败，它会把导致失败的最小输入**自动缩小（shrink）** 到最简形，然后报告给你。

```python
# demo1_basic.py
from hypothesis import given, strategies as st

# st.lists(st.integers()) 描述「整数列表」这种输入
@given(st.lists(st.integers()))
def test_sorted_is_ordered(xs):
    out = sorted(xs)
    # 属性 1：长度不变
    assert len(out) == len(xs)
    # 属性 2：非递减（用 zip 检查相邻对）
    assert all(a <= b for a, b in zip(out, out[1:]))
```

运行：`pytest demo1_basic.py`。它会默默跑 100 组随机样例（默认值），全部通过就绿。

---

## 2. 策略（strategy）：Hypothesis 的「输入语言」

`strategies` 模块是你和 Hypothesis 之间的「合同」。你声明输入空间的形状，它负责采样。常见策略：

| 策略 | 作用 |
|---|---|
| `st.integers(min_value=..., max_value=...)` | 整数 |
| `st.floats(allow_nan=False, allow_infinity=False)` | 浮点数（默认允许 NaN/Inf，常需要关掉） |
| `st.text()` | 任意字符串（含 Unicode） |
| `st.lists(elements, min_size=..., max_size=...)` | 列表 |
| `st.dictionaries(keys, values)` | 字典 |
| `st.one_of(s1, s2, ...)` | 联合类型 |
| `st.tuples(s1, s2)` / `st.sampled_from([...])` | 元组 / 枚举 |

所有策略都可以组合。写测试前，先在脑子里把「参数的类型与约束」翻译成策略——这一步做对了，测试就成功一半。

```python
def add(a: int, b: int) -> int:
    return a + b

@given(st.integers(), st.integers())
def test_add_commutative(a, b):
    # 加法交换律：这是一个绝佳的「属性」候选
    assert add(a, b) == add(b, a)
```

---

## 3. `.example()` 与可复现性：从随机到确定

每次跑测试都会换一批随机样例，这很好——但比赛/CI 里我们有时希望「固定住某个已知的反例」。两种手段：

1. **`@example(...)`**：显式钉一个输入。
2. **`@settings(database=...)`**：Hypothesis 会把失败样例写进本地数据库（默认在 `.hypothesis/`），下次运行自动重放。

```python
from hypothesis import given, example, settings, strategies as st

@given(st.text())
@example("")            # 空串是经典边界，钉住它
@example("\u0000")
@settings(max_examples=200)   # 加大试探次数

def test_encode_decode_roundtrip(s: str):
    # 属性：str -> bytes -> str 应当还原
    assert s.encode("utf-8").decode("utf-8") == s
```

`max_examples` 调大能提升找 bug 的概率，但 CI 里通常保持默认 100 就足够。

---

## 4. 复合策略：`@st.composite` 构造领域对象

真实项目里，输入往往不是基本类型，而是「一个合法的订单」「一个符合约束的用户名」。这时用 **`@st.composite`** 把基本策略拼装成领域策略。

```python
from hypothesis import strategies as st

@st.composite
def orders(draw):
    price = draw(st.floats(min_value=0.01, max_value=1e6, allow_nan=False))
    qty   = draw(st.integers(min_value=1, max_value=1000))
    # draw 是「从子策略里取一个样本」的方法
    return {"price": price, "qty": qty}

@given(orders())
def test_total_never_negative(o):
    total = o["price"] * o["qty"]
    assert total >= 0
```

这样做的好处：**约束写在生成器里一次，所有测试复用**；而当测试失败时，Hypothesis 依然能把失败缩到最小 `{price, qty}` 组合，便于定位。

---

## 5. 边界与陷阱：如何让 Hypothesis 真正帮到你

- **不要 `try/except` 吞掉断言**：`hypothesis` 依靠异常判定失败，捕获异常会让它误判为通过。
- **不要包 `random`**：如果你自己在测试体里再随机，会让 shrink 失效。所有随机性应来自参数。
- **`st.floats()` 默认含 NaN**：`float('nan') != float('nan')`，会让很多「相等性」属性莫名失败——常需 `allow_nan=False`。
- **慢**：如果被测试函数很重，调小 `max_examples` 或加 `deadline=None`（`@settings(deadline=None)`）避免每个样例被超时判负。
- **配合 Type Hints 使用**：`hypothesis` 有 `hypothesis-jsonschema`、`hypothesis.strategies.from_type(int)` 等工具，可从类型注解自动推导策略，对大型代码库尤其香。

一句话总结：**你负责写「性质」，Hypothesis 负责找「反例」；它替你穷举那些你绝不会手写的边界输入。**


---

## 本课题目

### single_choice · None



- [A] pytest 的覆盖率插件默认只统计行（语句）覆盖率，不统计分支覆盖率，除非显式开启分支统计
- [B] pytest 会自动把所有被 import 的模块标记为 100% 覆盖
- [C] 命令行加了 --cov 后，pytest 会跳过断言失败的分支
- [D] 覆盖率报告只统计测试文件中出现的代码行，不统计被测模块

**参考答案**：0

**解析**：语句覆盖率只关心某行是否被执行过，if 语句所在行被执行即算覆盖，即使某个分支从未进入。要发现未走到的分支需要开启分支覆盖统计（如 --cov-branch）。B、C、D 均是对覆盖率统计机制的常见误解。

### single_choice · None



- [A] 行覆盖率为 100% 一定意味着分支覆盖率也是 100%
- [B] 分支覆盖率 100% 一定意味着行覆盖率也是 100%
- [C] 两个指标互相独立，无法从一个是 100% 推断另一个也一定是 100%
- [D] 分支覆盖率只统计 if/else，不统计循环中的分支

**参考答案**：2

**解析**：行覆盖与分支覆盖是不同维度的度量。行覆盖 100% 仍可能有未进入的分支；分支覆盖 100% 意味着所有分支都被走到，通常也覆盖了对应行，但把两者当作可互相推导的等价指标是错误的。二者不能互相替代。

### single_choice · None



- [A] 部分覆盖指该行的一部分字符被执行，另一部分被跳过
- [B] 部分覆盖通常指某行的某些分支被走到而另一些分支未走到，常在开启分支统计后出现
- [C] 部分覆盖表示该行在测试中被执行了两次以上
- [D] 部分覆盖只在函数级统计中存在，行级统计不会出现

**参考答案**：1

**解析**：在分支统计开启后，某行如果对应多个分支而只有一部分被执行，会被标记为部分覆盖。它不是字符级统计，也和执行次数无关。

### single_choice · None



- [A] 把所有第三方库复制进业务目录一起统计
- [B] 在覆盖率配置中通过 source / include / omit 等选项限定统计范围，或在命令行 --cov 后指定目标包
- [C] 删除第三方库的安装以使其不出现
- [D] 将测试目录中的文件改名为 .txt 以避开统计

**参考答案**：1

**解析**：覆盖率工具支持把统计范围限定到指定包或排除某些模式，避免报告被第三方库和测试文件干扰。删除依赖、改名等做法既不可靠也不合理。

### single_choice · None



- [A] 总体覆盖率下降必然说明旧代码的测试被删除了
- [B] 新增未测试代码会稀释分母，使总体覆盖率下降，即使旧代码的测试完全没变
- [C] 覆盖率下降意味着测试全部失败
- [D] 只要测试用例总数不变，覆盖率就不会变化

**参考答案**：1

**解析**：覆盖率是「被执行的代码 / 总可执行代码」。新增未覆盖代码会增大分母，导致总体覆盖率下降，而不是旧测试被删除或测试失败导致的。

### single_choice · None



- [A] 总体覆盖率是各文件覆盖率的算术平均值，与代码量无关
- [B] 总体覆盖率通常按可执行行（或语句）加权计算，长文件对总体值的影响更大
- [C] 只要有一个文件达到 100%，总体覆盖率就一定是 100%
- [D] 单文件覆盖率没有意义，只有总体覆盖率有用

**参考答案**：1

**解析**：总体覆盖率一般以可执行行数加权汇总，代码量大的文件影响更大，而不是各文件百分比的简单平均。单个文件 100% 不能保证总体 100%。

### single_choice · None



- [A] 这是不可能的，100% 覆盖必然意味着异常分支也被执行
- [B] 行覆盖率只统计普通执行路径；异常处理分支若未被触发，可能体现在分支级统计中，行覆盖仍可能为 100%
- [C] 覆盖率工具会把 except 分支自动算作已覆盖，因为异常总会发生
- [D] 只要文件中出现 try/except 关键字，覆盖率工具就忽略该文件

**参考答案**：1

**解析**：行覆盖率可能只反映异常处理块所在行被跳过或执行，而分支统计能揭示哪些异常路径未被触发。覆盖率工具不会因为出现 try/except 就忽略文件或自动视为已覆盖。

### single_choice · None



- [A] 把整体阈值从 90% 调到 90%，只靠人工评审
- [B] 结合整体阈值与「新代码覆盖率」或按变更文件的覆盖率要求，并允许合理排除难以测试的代码
- [C] 只要不下降就允许合并，从不检查具体覆盖了哪些代码
- [D] 把阈值设为 0%，让覆盖率报告仅供展示

**参考答案**：1

**解析**：整体阈值配合新代码/变更文件覆盖率能避免「历史债务稀释」的问题，同时通过合理的排除和 # pragma: no cover 处理难以测试的代码，兼顾质量与可执行性。其余做法要么形同虚设，要么忽视实际覆盖内容。

### single_choice · None



- [A] 该模块会被自动标记为已覆盖，因为 import 尝试过
- [B] 该模块可能根本不出现在报告中，或出现但覆盖率极低，容易掩盖未被测试的情况
- [C] 覆盖率工具会自动修复 import 错误并继续统计
- [D] import 错误只会影响测试结果，不会影响覆盖率统计范围

**参考答案**：1

**解析**：覆盖率统计依赖模块实际被导入/执行。若因 import 错误导致模块未被加载，它可能不出现在报告中（若统计范围由实际导入决定）或显示极低覆盖，从而掩盖问题。工具不会自动修复错误或强制标记已覆盖。

### single_choice · None



- [A] 覆盖率只能输出到终端，无法生成其他格式的报告
- [B] 覆盖率工具通常支持多种输出格式（如终端、HTML、XML 等），便于与 CI 或代码评审平台集成
- [C] 只有生成 XML 格式的报告才能被持续集成系统读取
- [D] HTML 报告比终端报告统计的代码行更多，因此覆盖率更高

**参考答案**：1

**解析**：覆盖率工具普遍支持终端表格、HTML、XML（如 Cobertura）等多种报告格式，便于本地查看和 CI 集成。报告格式不影响统计口径，因此不会改变覆盖率数值。

### single_choice · None



- [A] 行覆盖率与分支覆盖率都必然是 100%
- [B] 行覆盖率小于 100%，但分支覆盖率必然为 100%
- [C] 行覆盖率与分支覆盖率都小于 100%（假设 else 分支的代码未被其他测试执行）
- [D] 只要函数被调用过，该函数就被视为 100% 覆盖

**参考答案**：2

**解析**：仅测试 if 分支时，else 分支中的代码未被执行，因此行覆盖率不足 100%；分支维度上 else 分支未走到，分支覆盖率也不足 100%。函数被调用不等于所有行/分支都被覆盖。

### single_choice · None



- [A] 合理，因为覆盖率越高测试质量一定越好
- [B] 不合理，覆盖率只反映代码执行情况，不能衡量断言强度、边界条件和缺陷发现能力
- [C] 合理，只要覆盖率达标，代码就不可能有 bug
- [D] 不合理，因为覆盖率工具本身计算经常出错

**参考答案**：1

**解析**：覆盖率是必要而非充分的指标。它无法反映断言是否充分、是否覆盖边界与异常场景。将其作为唯一指标会鼓励「为了覆盖率而写无意义测试」。

### single_choice · None



- [A] 在测试文件里把该目录的模块全部 skip 掉
- [B] 使用覆盖率配置文件（如 .coveragerc）中的 omit 选项指定要排除的文件或目录模式
- [C] 给该目录下的每个函数加上 # pragma: no test 注释
- [D] 在命令行中删除该目录后再运行 pytest --cov

**参考答案**：1

**解析**：覆盖率工具通常通过配置文件或命令行参数指定 omit / exclude 规则来排除文件，或在源码中用 # pragma: no cover 标记特定行。skip 测试、注释 no test、删除目录都不是标准做法。

### single_choice · None



- [A] 覆盖率工具会累积历史数据，不删除旧数据会导致结果被合并
- [B] 覆盖率结果与数据文件无关，两次结果必然完全相同
- [C] 覆盖率数据文件只保存测试日志，不影响统计
- [D] 删除数据文件会使覆盖率工具切换到不同的统计算法

**参考答案**：0

**解析**：覆盖率工具通常把本次运行数据写入数据文件，默认行为可能与历史数据合并。若不清理，累积数据会影响报告结果。删除数据文件后重新运行，得到的是本次运行的干净结果。

### single_choice · None



- [A] 覆盖率统计会验证断言是否正确，因此断言一定有效
- [B] 覆盖率只反映代码是否被执行，不保证执行结果被正确断言，所以高覆盖率不等于高质量测试
- [C] 覆盖率工具只统计 pass 的测试，因此报告偏高
- [D] 断言数量越多覆盖率越高，与断言内容无关

**参考答案**：1

**解析**：覆盖率衡量的是代码被执行到的比例，而不是断言是否充分。即使所有行都执行过，如果断言缺失或很弱，测试依然可能放过缺陷。这是覆盖率的经典局限。

### single_choice · None



- [A] 测试文件中缺失的测试函数数量
- [B] 该文件中未被任何测试执行到的行号或行号区间
- [C] 因异常而中断的测试数量
- [D] 被标记为 skip 的代码行

**参考答案**：1

**解析**：在覆盖率报告的表格中，Missing 列列出的是该文件里没有被测试执行到的行号或区间，便于定位尚未覆盖的代码。它不是测试数量、异常数或 skip 数。

### single_choice · None



- [A] pytest 默认在覆盖率低于 100% 时就会让整个测试会话失败
- [B] 可以通过覆盖率工具提供的选项（如 fail-under 或配置项）设定最低覆盖率阈值，低于该值则命令返回失败
- [C] 只有把阈值设在 100%，覆盖率报告才会生成
- [D] 覆盖率阈值只能对单个文件设置，不能对整体设置

**参考答案**：1

**解析**：许多覆盖率工具支持通过 --cov-fail-under 或配置文件设置最低覆盖率，低于该阈值时返回非零退出码，便于 CI 卡控。默认不会强制 100%，阈值既可对整体也可对某些文件设置。

### single_choice · None



- [A] CI 环境中某些测试因缺少依赖而被 skip 了
- [B] 两次运行的覆盖率统计范围（包含/排除的目录）不同
- [C] 覆盖率算法会随机变化，同一代码每次结果都不同
- [D] CI 中使用了不同的覆盖率配置或命令行参数

**参考答案**：2

**解析**：覆盖率统计是确定性的：在相同代码、相同测试集合和相同统计范围下结果应一致。差异通常来自测试被跳过、统计范围不同或配置参数不同，而不是算法随机。

### single_choice · None



- [A] 语句覆盖率衡量执行过的语句比例；路径覆盖率衡量执行过的不同执行路径比例，后者更严格
- [B] 路径覆盖率就是语句覆盖率的另一种叫法
- [C] 语句覆盖率为 100% 时路径覆盖率也必然为 100%
- [D] 路径覆盖率只统计函数是否被调用过

**参考答案**：0

**解析**：语句覆盖率是执行语句的比例；路径覆盖率关注代码中不同控制流路径的组合是否都被执行到，通常比语句覆盖严格得多，语句全覆盖不代表所有路径组合都走到。

### single_choice · None



- [A] # coverage: skip
- [B] # pragma: no cover
- [C] # pytest: ignore
- [D] # no coverage: true

**参考答案**：1

**解析**：覆盖率工具通常支持 # pragma: no cover 注释，将被标记的行或块排除在覆盖率统计之外。其余写法并非标准约定，属于常见误记。

### single_choice · None



- [A] pytest 内置自动记录覆盖率，无需任何插件或参数
- [B] 通常需要安装并启用覆盖率插件（如 pytest-cov），再通过 --cov 等参数指定被测范围
- [C] 只要使用 assert 语句就会自动生成覆盖率报告
- [D] 必须把测试改写成 unittest 风格才能统计覆盖率

**参考答案**：1

**解析**：pytest 本身不内置覆盖率统计，通常需借助覆盖率插件（如 pytest-cov）并通过 --cov 参数指定统计目标。覆盖率与断言风格、测试框架风格无关。

### single_choice · None



- [A] 自动为测试函数生成随机输入并多次运行
- [B] 把测试函数标记为跳过执行
- [C] 将测试函数的异常转换为断言失败
- [D] 为测试函数提供数据库连接

**参考答案**：0

**解析**：@given 是 Hypothesis 的核心装饰器，它根据传入的策略（strategy）生成各种输入，并用这些输入反复调用被装饰的测试函数，从而覆盖更多边界情况。其他选项与 @given 无关。

### single_choice · None



- [A] 一个整数列表
- [B] 一个用于生成整数的策略对象
- [C] 一个随机整数
- [D] 一个断言函数

**参考答案**：1

**解析**：st.integers() 返回的是策略（SearchStrategy）对象，描述如何生成整数；要得到具体值需要 @given 等机制来驱动。它不是列表、也不是具体整数，更不是断言。

### multi_choice · None



- [A] 健康检查用于提醒可能导致测试不稳定或过慢的问题
- [B] 可以通过 @settings(suppress_health_check=...) 关闭部分检查
- [C] 健康检查失败一定会导致测试失败，不能关闭
- [D] 常见的健康检查包括数据生成过慢、过滤掉太多数据等
- [E] 健康检查会自动修改被测代码

**参考答案**：[0, 1, 3]

**解析**：健康检查会提示潜在问题（如生成过慢、过滤过多等），可以通过 suppress_health_check 关闭部分检查。它不是不可关闭的，也不会自动修改被测代码。

### fill_blank · None



**参考答案**：["lists", "st.lists", "hypothesis.strategies.lists"]

**解析**：st.lists() 用于生成列表策略，常与元素策略配合使用，如 st.lists(st.integers())。

### fill_blank · None



**参考答案**：["assume", "hypothesis.assume"]

**解析**：assume(condition) 会在条件不满足时丢弃当前示例，让 Hypothesis 重新生成输入，常用于表达前置条件。

### fill_blank · None



**参考答案**：["example", "given.example"]

**解析**：@example 可以给测试函数提供固定的输入样例，通常与 @given 一起使用，用于回归或强调特定情况。

### code_reading · None



**参考答案**：验证整数与 0 相加等于其本身这一属性（加法单位元性质）对任意整数都成立。

**解析**：该测试使用 @given(st.integers()) 生成任意整数，断言 x + 0 == x，属于属性测试：不是枚举具体值，而是验证一个对所有整数都应成立的性质。

### code_reading · None



**参考答案**：对任意整数列表，反转两次应当得到与原列表相同的列表。

**解析**：该测试通过生成任意整数列表，验证“反转两次等于原列表”这一不变量。它体现属性测试的思路：对一类输入验证一个普遍成立的性质。

### code_reading · None



**参考答案**：整数加法的交换律：对任意两个整数 a 和 b，a + b 等于 b + a。

**解析**：@given 接收两个整数策略，分别对应参数 a 和 b，断言 a + b == b + a，验证加法交换律对任意整数对都成立。

### scenario · None



**解析**：可以通过 @settings 调整参数：用 max_examples 控制生成示例数量，用 deadline 限制单个示例的超时时间。这样既保留属性测试，又避免单个示例过慢导致测试不稳定。

### scenario · None



**解析**：可以在测试函数内部使用 assume 表达前置条件，例如 assume(len(xs) > 0)，这样当生成为空列表时当前示例会被丢弃，Hypothesis 会重新生成，从而只测试非空列表。

### scenario · None



**解析**：可以使用 @example 装饰器把这个具体输入固定下来，它与 @given 一起使用，会作为固定示例执行，从而起到回归测试的作用，避免同类问题再次出现。

### single_choice · None



- [A] 它只能用于没有使用 @given 的测试函数
- [B] 它会在每次运行测试时强制使用指定输入作为示例
- [C] 它会替代所有随机生成的输入
- [D] 它只能接受字符串参数

**参考答案**：1

**解析**：@example 用来显式提供一个或多个固定的输入样例，这些样例会与 @given 生成的随机输入一起被执行，而不是取代随机输入；它也可以与 @given 一起使用。

### scenario · None



**解析**：这个问题通常是因为 @given 中传入的策略数量与测试函数参数数量不一致，或者参数名不匹配。排查时应检查函数签名，确保每个策略都有对应的参数，数量与顺序一致。

### single_choice · None



- [A] Hypothesis 会自动把参数注入到全局变量中
- [B] 测试会直接跳过
- [C] 运行时会报错，提示缺少与 @given 参数对应的函数参数
- [D] Hypothesis 会忽略该策略

**参考答案**：2

**解析**：@given 的参数（策略）必须与测试函数的参数一一对应。如果数量或名称不匹配，Hypothesis 在运行时会抛出错误，而不是静默跳过或注入全局变量。

### single_choice · None



- [A] 测试函数最多只能被调用 5 次
- [B] 最多生成 5 个不同的随机输入来执行测试
- [C] 测试超时时间为 5 秒
- [D] 只允许 5 个断言失败

**参考答案**：1

**解析**：max_examples 控制 Hypothesis 为一次测试最多生成多少个不同的示例输入。它不是限制调用次数到某个绝对值（因为加上 @example 等可能更多），也不是超时或断言失败数。

### single_choice · None



- [A] 忽略该失败并继续
- [B] 尝试把输入缩小（shrink）到更简单的形式，以便定位问题
- [C] 删除整个测试文件
- [D] 把输入写入数据库并停止所有测试

**参考答案**：1

**解析**：Hypothesis 内置 shrink 机制，一旦发现失败示例，会尝试把它简化成更小、更易读的反例，帮助定位问题。它不会忽略失败、删除文件或停止整个测试会话。

### single_choice · None



- [A] 失败的测试无法复现
- [B] Hypothesis 会保存导致失败的示例，并在下次运行时优先尝试复现
- [C] 必须手动把随机种子写死在测试文件里才能复现
- [D] 复现机制只在 Linux 上可用

**参考答案**：1

**解析**：Hypothesis 会把失败示例保存在数据库中（默认 .hypothesis 目录），下次运行该测试时会优先尝试这些示例，保证可复现。并不需要手动写死种子，且该机制跨平台。

### multi_choice · None



- [A] st.integers()
- [B] st.text()
- [C] st.lists()
- [D] st.assert_equal()
- [E] st.booleans()

**参考答案**：[0, 1, 2, 4]

**解析**：st.integers、st.text、st.lists、st.booleans 都是 Hypothesis 的策略构造器。st.assert_equal 不是策略，而是一个与断言相关的辅助（且并非用于生成数据），因此不属于常用策略。

### multi_choice · None



- [A] 用 @given 配合策略生成输入并验证不变量
- [B] 对已经发现的失败用例使用 @example 固定下来作为回归测试
- [C] 用 assume 过滤掉不满足前置条件的输入
- [D] 把所有断言都改成 print，避免失败
- [E] 用 @settings 调整最大示例数或 deadline

**参考答案**：[0, 1, 2, 4]

**解析**：属性测试的常见实践包括：用 @given 生成输入、用 @example 固化回归用例、用 assume 过滤不合法前置条件、用 @settings 调整行为。把断言改成 print 会掩盖失败，不是合理做法。

### multi_choice · None



- [A] 可以设置 max_examples 来限制生成示例数量
- [B] 可以设置 deadline 来控制单个示例的超时
- [C] 可以设置 suppress_health_check 来关闭某些健康检查
- [D] 它可以替代 @given 使用
- [E] 它会自动修复测试中的逻辑错误

**参考答案**：[0, 1, 2]

**解析**：@settings 用于调整测试运行参数，例如 max_examples、deadline、suppress_health_check 等。它不能替代 @given，也不会自动修复测试逻辑错误。
