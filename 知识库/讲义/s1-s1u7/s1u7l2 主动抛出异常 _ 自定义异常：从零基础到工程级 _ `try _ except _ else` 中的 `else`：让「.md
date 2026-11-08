# s1u7l2 主动抛出异常 / 自定义异常：从零基础到工程级 / `try / except / else` 中的 `else`：让「成功路径」显式化

> 来源 `content/lessons/s1u7l2.json`

## py.exc.raise

# py.exc.raise：主动抛出异常

> 一句话直觉：**当程序发现自己处于“不可能、不允许、无法继续”的状态时，与其默默返回一个错误的值，不如用 `raise` 大声告诉调用者“出事了”，让错误在正确的层级被处理。**

前置：无。你只需要会写 Python 函数和 `if` 即可。

---

## 1. 为什么需要 raise：错误应该被“报告”，而不是被“吞掉”

很多初学者遇到非法输入时喜欢返回 `None` 或返回一个“魔法值”表示失败：

```python
def sqrt(x):
    if x < 0:
        return None   # 用 None 偷偷表示“失败”
    return x ** 0.5
```

这看起来很“温柔”，但会带来灾难：调用者必须**记住**每个函数的“失败约定”，一旦忘记检查，`None` 就会一路传播，最后在某处爆出一个跟真正原因完全无关的 `TypeError`。

更糟的是，`sqrt(0)` 返回 `0.0`，而 `sqrt(-1)` 返回 `None`——两个完全不同的语义被混在了一起。

`raise` 的思想是：**函数只负责它该做的事，遇到它无法处理的情况就抛出一个异常（exception），把“我处理不了”这件事明确地、机器可识别地告诉调用栈。**

```python
def sqrt(x):
    if x < 0:
        raise ValueError(f"sqrt 只接受非负数，收到 {x!r}")
    return x ** 0.5

sqrt(4)     # => 2.0
sqrt(-1)    # 抛出 ValueError: sqrt 只接受非负数，收到 -1
```

**关键结论**：`raise` 不是“崩溃”，而是一种**控制流机制**——它把执行权从当前函数直接交给最近一个能处理这种异常的 `except`。如果没人处理，才变成程序崩溃。

---

## 2. raise 的三种基本用法

### 2.1 抛出内置异常（最常见）

Python 内置了一批语义清晰的异常类，直接 `raise 类名(消息)` 即可：

```python
raise ValueError("值不合法")        # 值不对
raise TypeError("参数类型不对")     # 类型不对
raise KeyError("missing_key")       # 字典缺键
raise FileNotFoundError("a.txt")    # 文件不存在
raise RuntimeError("不该到这里")    # 兜底“不可能发生”
```

选异常的原则：**让看日志的人一眼知道“哪里错了”，而不是“出错了”。**

### 2.2 抛出异常类（不推荐）

```python
raise ValueError       # 合法，但抛出的实例没有消息
```

运行时 Python 会帮你实例化，但调用者只能看到空的 `ValueError()`，调试时几乎没用。**永远带上消息**。

### 2.3 重新抛出当前异常（bare raise）

在 `except` 块里，如果你想“记录一下，但继续往上抛”，用不带表达式的 `raise`：

```python
try:
    do_something()
except Exception:
    print("do_something 失败了，准备继续上抛")
    raise              # 保留原始 traceback，继续传播
```

如果写成 `raise e`（e 是异常对象），会丢掉原始 traceback 的“来源链”，可读性差。**裸 `raise` 是重抛的标准写法。**

---

## 3. 异常链：raise X from Y

当你把一个异常“翻译”成另一个更贴合上下文的异常时，原始异常默认会被挂到 `__context__` 上，打印 traceback 时会看到 “During handling of the above exception, another exception occurred”。

如果这是你有意为之的“因果替换”，用 `raise X from Y` 明确表达，traceback 会显示 “The above exception was the direct cause of the following exception”：

```python
import json

def load_config(text):
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        # 明确告诉调用者：出问题的是“配置解析”这一层，
        # 而不是让 JSONDecodeError 原样冒泡出去。
        raise ValueError("配置文件不是合法 JSON") from e
```

**结论**：`raise ... from e` = “我主动替换异常，但保留因果链”。
如果确实想**切断**因果链（少见），用 `raise X from None`。

---

## 4. 自定义异常：让错误“会说人话”

内置异常覆盖不了所有业务语义。这时应该派生子类。按惯例：

- 继承 `Exception`（不要继承 `BaseException`，那是给 `SystemExit`/`KeyboardInterrupt` 这类“抓了反而是错”的异常留的）。
- 类名以 `Error` 结尾。

```python
class InsufficientBalanceError(Exception):
    """余额不足。"""

def withdraw(account, amount):
    if amount <= 0:
        raise ValueError(f"取款金额必须为正，收到 {amount}")
    if amount > account["balance"]:
        raise InsufficientBalanceError(
            f"余额 {account['balance']}，无法取出 {amount}"
        )
    account["balance"] -= amount
```

这样调用方就能 `except InsufficientBalanceError` 精准处理，而不是 `except Exception` 一把抓。

---

## 5. 一个完整可运行的例子

下面把“参数校验 → 业务规则 → 外层捕获”串起来，运行一次就能看到每种分支的实际效果。

```python
class InsufficientBalanceError(Exception):
    """账户余额不足。"""


def withdraw(balance, amount):
    # 1) 参数层：非法输入直接 ValueError
    if not isinstance(amount, (int, float)):
        raise TypeError(f"amount 必须是数字，收到 {type(amount).__name__}")
    if amount <= 0:
        raise ValueError(f"金额必须为正，收到 {amount}")

    # 2) 业务层：规则违反用自定义异常
    if amount > balance:
        raise InsufficientBalanceError(
            f"余额 {balance} 不足以取出 {amount}"
        )
    return balance - amount


def safe_withdraw(balance, amount):
    try:
        new_balance = withdraw(balance, amount)
    except (TypeError, ValueError) as e:
        # 输入错误：一般不重试、不吞，向上报告
        print(f"[输入错误] {e}")
        raise
    except InsufficientBalanceError as e:
        # 业务错误：可以在这里决定降级/提示用户
        print(f"[业务拒绝] {e}")
        return balance
    else:
        print(f"[成功] 新余额 = {new_balance}")
        return new_balance


if __name__ == "__main__":
    safe_withdraw(100, 30)      # 成功，新余额 70
    safe_withdraw(100, -1)      # 输入错误，向上抛 ValueError
    safe_withdraw(100, 500)     # 业务拒绝，返回原余额 100
```

---

## 6. 常见误区（PEP 8 与实践）

1. **用返回值表示失败**：`return None` 或 `return -1` 这类“哨兵值”让调用者必须记住约定，一旦忘记就等着 `AttributeError` / `TypeError` 在最没相关的地方爆炸。**能 raise 就 raise。**
2. **裸 `except:`**：它会连 `SystemExit`、`KeyboardInterrupt` 一起吞掉，Ctrl+C 都打断不了。想抓“所有普通错误”请写 `except Exception:`。
3. **裸 `except` 后吞掉**：`except Exception: pass` 是调试噩梦——错误发生了，但什么都没说。要么处理，要么 `raise`。
4. **`try` 块范围过大**：把一堆不相干的代码塞进 `try`，会把别人的异常也一起捕获。`try` 里只放“真正可能抛该异常”的那一两行。
5. **在 `finally` 里 `return` / `break` / `continue`**：这会让正在传播的异常被静默取消，行为极其反直觉。要清理资源用 `with`。
6. **异常类不用 `Error` 后缀、不从 `Exception` 派生**：破坏可读性和库之间的兼容约定。
7. **重抛时写 `raise e`**：丢失原始 traceback；应使用裸 `raise`。

---

## 动手练习

**任务**：实现一个学生成绩登记函数 `record_score(name, score)`，要求：

1. `name` 必须是非空字符串，否则 `raise ValueError`，消息里包含实际收到的内容。
2. `score` 必须是 `int` 或 `float`，否则 `raise TypeError`。
3. `score` 必须在 `[0, 100]` 之间，否则 `raise ValueError`。
4. 定义一个自定义异常类 `ScoreTooLowError(Exception)`；当 `score < 60` 时抛它，消息里带上学生姓名和分数。
5. 在 `main` 里循环调用几个测试用例（正常的、类型错的、范围错的、不及格的），用**分别捕获**的方式打印不同提示，并在处理“类型/范围”错误后用裸 `raise` 重抛，观察 traceback。

**验收标准**：
- 每个异常分支能打印出可读的错误信息；
- 不及格时能被 `except ScoreTooLowError` 精确捕获（而不是被 `except ValueError` 抢先）；
- 通过 `raise ... from e` 至少演示一次异常链（例如把 `json` 解析错误包装成 `ValueError`）。

**提示**：把自定义异常放在内置异常的子类里要小心继承顺序——`except` 是按从上到下的顺序匹配的，子类要写在父类前面。

```python
class ScoreTooLowError(Exception):
    """分数低于及格线。"""


def record_score(name, score):
    if not isinstance(name, str) or not name:
        raise ValueError(f"name 必须是非空字符串，收到 {name!r}")
    if not isinstance(score, (int, float)) or isinstance(score, bool):
        raise TypeError(f"score 必须是数字，收到 {type(score).__name__}")
    if not 0 <= score <= 100:
        raise ValueError(f"score 必须在 [0, 100]，收到 {score}")
    if score < 60:
        raise ScoreTooLowError(f"{name} 的成绩 {score} 未及格")
    return {"name": name, "score": score, "passed": True}


def main():
    cases = [
        ("Alice", 88),
        ("Bob", 42),
        ("", 90),
        ("Cara", "ninety"),
        ("Dan", 120),
    ]
    for name, score in cases:
        try:
            result = record_score(name, score)
        except ScoreTooLowError as e:
            print(f"[不及格] {e}")
        except (ValueError, TypeError) as e:
            print(f"[输入错误] {e}")
             # 裸 raise 演示：把输入错误继续向上传播。
             # 生产代码里这里通常会用日志记录后再 raise。
            raise
        else:
            print(f"[登记成功] {result}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[顶层兜底] {type(e).__name__}: {e}")
```

## py.exc.custom

# 自定义异常：从零基础到工程级

## 一句话直觉

**当程序出错时，如果你只会 `raise Exception("出错了")`，调用方根本不知道发生了什么；自定义异常（custom exception）就是给你的错误起一个有意义的名字，让代码像读中文一样清晰。**

---

## 1. 为什么需要自定义异常

Python 内置了很多异常，比如 `ValueError`、`TypeError`、`KeyError`。它们描述的是“语言层面”的错误。但真实项目里，错误往往和业务有关：

- 用户余额不足
- 库存扣减失败
- 配置文件格式不对
- 模型训练时梯度爆炸

如果全部用 `ValueError`，调用方无法精确地区分和处理。自定义异常（custom exception）就是为你的领域（domain）定义专属的错误类型。

```python
# 不是好做法：所有错误都用一个 ValueError
raise ValueError("余额不足")
raise ValueError("库存不足")

# 好做法：让错误类型自己说话
class InsufficientBalanceError(Exception):
    pass

raise InsufficientBalanceError("余额不足")
```

> 关键结论：**异常类型本身就是一种“错误分类”，调用方可以 `except` 到具体类型，而不是靠字符串匹配。**

---

## 2. 定义自定义异常的最小写法

在 Python 中，异常就是一个类，必须继承自 `BaseException` 或其子类。日常工程中，我们几乎总是继承 `Exception`。

```python
# 最小自定义异常：只继承 Exception，不做任何事
class MyError(Exception):
    pass

# 抛出与捕获
try:
    raise MyError("something went wrong")
except MyError as e:
    print(f"捕获到自定义异常: {e}")
```

**为什么继承 `Exception` 而不是 `BaseException`？**

- `BaseException` 是给系统级异常用的，比如 `KeyboardInterrupt`、`SystemExit`。
- 如果你继承 `BaseException`，`except Exception` 就抓不到它，会破坏很多工具的行为。

> 关键结论：**自定义异常一律继承 `Exception`（或它的子类），不要直接继承 `BaseException`。**

---

## 3. 给异常加上结构化信息

只传一个字符串是不够的。工程里我们常把出错的上下文（context）附在异常上，方便日志和上层处理。

```python
class InsufficientBalanceError(Exception):
    """余额不足异常，携带账户和金额信息。"""
    def __init__(self, account: str, needed: float, current: float):
        self.account = account
        self.needed = needed
        self.current = current
        # 调用父类构造，让 str(e) 有一个可读消息
        super().__init__(
            f"账户 {account} 余额不足：需要 {needed}，当前 {current}"
        )

try:
    raise InsufficientBalanceError("A1001", needed=500, current=120)
except InsufficientBalanceError as e:
    print(e)
    print("账户:", e.account)
    print("差额:", e.needed - e.current)
```

> 关键结论：**自定义异常可以携带属性（attribute），让上层代码拿到结构化数据，而不是解析字符串。**

---

## 4. 建立异常层级（exception hierarchy）

一个项目通常有多个业务异常。做法是先定义一个基类，再分门别类。

```python
# 项目统一异常基类
class AppError(Exception):
    """所有业务异常的基类。"""
    pass

# 具体业务异常
class ValidationError(AppError):
    pass

class StorageError(AppError):
    pass

class NetworkError(AppError):
    pass

# 上层可以粗粒度捕获
try:
    raise ValidationError("字段 age 必须是整数")
except AppError as e:
    print("业务异常:", type(e).__name__, e)
```

这种结构的好处：

- 上层可以只 `except AppError`，统一记录日志。
- 底层可以抛具体子类，让关心细节的调用方精确处理。
- 未来新增异常，只要挂在 `AppError` 下，上层代码不用改。

> 关键结论：**先定义项目异常基类，再按业务维度派生子类，是一种可扩展的工程惯例。**

---

## 5. 工程级实践：链式异常与 `from`

当你在 `except` 里抛出新的异常时，Python 会自动记录“原始异常”作为上下文。推荐显式使用 `raise ... from ...` 表达因果链。

```python
class ConfigError(AppError):
    pass

def load_config(raw: str) -> dict:
    try:
        import json
        return json.loads(raw)
    except json.JSONDecodeError as e:
        # 把底层错误转成业务错误，并保留因果链
        raise ConfigError(f"配置文件不是合法 JSON: {raw!r}") from e

try:
    load_config("{not json}")
except ConfigError as e:
    print("捕获:", e)
    print("根因:", e.__cause__)
```

运行后会看到类似输出：

```
捕获: 配置文件不是合法 JSON: '{not json}'
根因: Expecting property name enclosed in double quotes: line 1 column 2 (char 1)
```

> 关键结论：**在异常转换时使用 `raise NewError(...) from original`，可以同时保留业务语义和根因（root cause），是调试和日志的关键。**

---

## 动手练习

**任务：为一个小型“图书馆借书”模块设计异常体系。**

1. 定义一个基类 `LibraryError(Exception)`。
2. 从基类派生三个子类：
   - `BookNotFoundError`：携带 `isbn` 属性。
   - `BookAlreadyBorrowedError`：携带 `isbn` 和 `borrower` 属性。
   - `BorrowLimitExceededError`：携带 `borrower` 和 `limit` 属性。
3. 实现函数 `borrow_book(isbn, borrower)`，规则如下：
   - 如果 `isbn` 不在库存中，抛 `BookNotFoundError`。
   - 如果书已被借出，抛 `BookAlreadyBorrowedError`。
   - 如果该借阅人已借满 3 本，抛 `BorrowLimitExceededError`。
   - 成功则返回一个字符串 `"borrow ok: <isbn>"`。
4. 写一段测试代码，分别触发三种异常并捕获，打印异常的属性。

**加分项**：在 `borrow_book` 内部捕获一个 `KeyError`，用 `raise ... from ...` 转成 `BookNotFoundError`，并打印 `__cause__`。

---

## 小结

- 自定义异常 = 给错误起名字。
- 继承 `Exception`，不要继承 `BaseException`。
- 用属性携带结构化信息，不要只传字符串。
- 用基类 + 子类构建异常层级。
- 用 `raise ... from ...` 保留因果链。

```python
import json


# 1. 项目异常基类
class AppError(Exception):
    """所有业务异常的基类。"""
    pass


# 2. 具体业务异常
class ConfigError(AppError):
    pass


class InsufficientBalanceError(AppError):
    """余额不足，携带账户和金额信息。"""
    def __init__(self, account: str, needed: float, current: float):
        self.account = account
        self.needed = needed
        self.current = current
        super().__init__(
            f"账户 {account} 余额不足：需要 {needed}，当前 {current}"
        )


# 3. 异常转换：保留因果链
def load_config(raw: str) -> dict:
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise ConfigError(f"配置文件不是合法 JSON: {raw!r}") from e


# 4. 演示
if __name__ == "__main__":
    # 场景一：余额不足
    try:
        raise InsufficientBalanceError("A1001", needed=500, current=120)
    except AppError as e:
        print("业务异常:", type(e).__name__, e)
        print("差额:", e.needed - e.current)

    # 场景二：异常转换 + 因果链
    try:
        load_config("{not json}")
    except ConfigError as e:
        print("捕获:", e)
        print("根因:", e.__cause__)
```

## py.exc.else

# `try / except / else` 中的 `else`：让「成功路径」显式化

> 一句话直觉：`else` 是给「try 块没抛异常时」准备的专属舞台，它让「正常成功后的收尾逻辑」和「兜底的异常处理逻辑」彻底分家，代码一眼就能看出「出事了走哪、没出事走哪」。

前置说明：本节假设你已经会写 `try / except`。如果还不会，请先花 5 分钟回看 `try/except` 的基本用法；本节聚焦的是「第三个关键字：`else`」。

---

## 1. 为什么需要 `else`？—— 从一段「看起来没问题」的代码说起

很多初学者会把「成功之后要执行的代码」直接塞进 `try` 里面，例如：

```python
# 反例：把所有逻辑都塞进 try
 try:
     data = open("config.json").read()   # 可能 FileNotFoundError
     parsed = json.loads(data)            # 可能 JSONDecodeError
     save_to_db(parsed)                   # 可能数据库异常
 except Exception as e:
     print("出错了：", e)
```

问题在哪？`save_to_db` 抛出的异常会被这个 `except Exception` 悄悄吞掉，你根本不知道到底是「读文件失败」「JSON 解析失败」还是「存数据库失败」。**`try` 块的边界太粗，异常类型无法精确定位**。

**结论 1**：`try` 块应该只包住「真正可能抛该异常的语句」。成功后的后续处理，放到 `else` 里。

```python
# 正例：try 只包住可能出错的读取，成功后再处理
 try:
     data = open("config.json").read()   # 只可能在这里抛 IO 错误
 except OSError as e:
     print("读文件失败：", e)
 else:
     # 只有 try 没抛异常才会走到这里
     parsed = json.loads(data)
     save_to_db(parsed)
```

现在 `except` 只负责「读文件失败」，`else` 里代码的异常会正常向上传播，不会被误吞。

---

## 2. `else` 的执行语义：三条规则

`try / except / else / finally` 是一个整体，执行顺序固定为：

1. 执行 `try` 块。
2. 若抛出异常 → 跳到匹配的 `except`；**`else` 被跳过**。
3. 若没抛异常 → 执行 `else` 块。
4. 无论是否异常 → 最后执行 `finally`（如果写了）。

**结论 2**：只要 `try` 块内**没有异常逃出**（包括内部 `return`、`break`、`continue` 也算「正常结束」），`else` 就会执行；否则 `else` 被跳过。

```python
# 演示：try 成功 vs 失败时 else 的差异
 def demo(flag: bool) -> None:
     try:
         print("A: try 开始")
         if flag:
             raise ValueError("boom")
         print("B: try 正常结束")
     except ValueError as e:
         print("C: 捕获到", e)
     else:
         print("D: else 执行（只有 try 无异常才走这里）")
     finally:
         print("E: finally 总会执行")

 demo(True)   # A -> C -> E      （else 被跳过）
 demo(False)  # A -> B -> D -> E （else 被走到）
```

---

## 3. `else` 和「写在 try 里」到底差在哪？—— 异常边界不同

很多人会问：「我把 `else` 里的代码放回 `try` 末尾，不也能跑吗？」——能跑，但语义完全不同。

**结论 3**：`else` 里的代码**不属于 try 的保护范围**，它抛的异常不会被同名 `except` 捕获，会向上冒泡。这正是我们想要的「精细边界」。

```python
# 对比：同样的逻辑，try 内 vs else 内，捕获到的异常范围不同
 def without_else():
     try:
         n = int("123")        # 不会失败
         print(10 / n)         # 可能抛 ZeroDivisionError
     except ZeroDivisionError:
         print("[without_else] 捕获到了 ZeroDivisionError")

 def with_else():
     try:
         n = int("123")
     except ValueError:
         print("[with_else] int() 转换失败")
     else:
         print(10 / n)          # ZeroDivisionError 会往上抛，不被 except 捕获

 without_else()                # 打印“捕获到了 ZeroDivisionError”
 try:
     with_else()               # ZeroDivisionError 冒泡到这里
 except ZeroDivisionError:
     print("[caller] 在调用方处理了 ZeroDivisionError")
```

这就是 `else` 的核心价值：**把「可能出错的步骤」和「出错后该怎么办」分离，让每个 `except` 只对一小段代码负责**。

---

## 4. `else` + `finally` + `continue/break/return` 的细节

在循环里搭配 `else` 时，有几条容易踩坑的规则，集中说清：

**结论 4**：
- `try` 里执行了 `return` / `break` / `continue`，也算「正常结束」，`else` 仍会执行（在 `finally` 之前）。
- 但 `break` / `continue` / `return` 会**直接结束整个 `try/else` 流程**，只是路径不同。
- `finally` 永远最后执行，且**若 `finally` 内部有 `return`，会覆盖 `try` / `else` 的返回值**——这是经典坑。

```python
# 演示：try 里 return 时，else 依然会执行（在 finally 之前）
 def f():
     try:
         print("try")
         return 1
     except Exception:
         print("except")
     else:
         print("else")          # 会被打印
     finally:
         print("finally")       # 最后打印

 print("返回值 =", f())
 # 输出顺序：try -> else -> finally -> 返回值 = 1
```

```python
# 演示：finally 里 return 会覆盖前面的返回值（应避免）
 def g():
     try:
         return "from try"
     finally:
         return "from finally"   # 覆盖，非常危险

 print(g())   # "from finally"
```

---

## 5. 工程级用法：重试、资源获取、给调用方清晰失败点

`else` 在工程代码中最常见的两个场景：

**场景 A：资源获取失败就放弃，成功才进入主逻辑**

```python
# 拿锁失败就跳过，成功才处理任务
 from threading import Lock

 lock = Lock()

 def do_job():
     acquired = lock.acquire(timeout=0.01)
     if not acquired:
         print("拿锁失败，跳过本次任务")
         return
     try:
         print("执行任务")
     finally:
         lock.release()
```

**场景 B：重试框架里区分「重试条件」和「成功后续」**

```python
# 只有异常才重试；一旦成功，统一在 else 分支里做统计
 import time

 def retry(n: int, fn, attempts: int = 3):
     last_exc = None
     for i in range(attempts):
         try:
             return fn()
         except Exception as e:
             last_exc = e
             time.sleep(0.1)
     raise last_exc
```

注意上面用 `return fn()` 直接返回，本质上等价于「成功即走」。若你想在成功后再做一些统一统计，可以改写为 `try/except/else` 结构：

```python
 def fetch_with_log(fn):
     try:
         result = fn()
     except Exception as e:
         print("抓取失败：", e)
         raise
     else:
         print("抓取成功，条数 =", len(result))
         return result
```

**结论 5**：在「先做一件可能失败的事，再基于结果做后续」的模式中，`else` 是最清晰的表达方式：**失败走 `except`，成功走 `else`，中间不做假设。**

---

## 小结（给零基础到工程级的记忆锚点）

| 关键字 | 何时执行 | 常放什么 |
|--------|----------|----------|
| `try` | 总是先执行 | 只放真正可能抛异常的最小语句集 |
| `except` | `try` 中抛异常时 | 针对具体异常类型的处理 |
| `else` | `try` 正常结束、`except` 未触发时 | 成功后的后续逻辑 |
| `finally` | 无论如何最后执行 | 资源释放、清理 |

一句话收尾：**`else` 存在的意义，不是多一个语法糖，而是让「成功路径」和「失败路径」在代码上可见、可读、可测。**

```python
import json

# ============================================================
# 场景：从字符串读取配置，解析成功才继续处理
# 用 try / except / else / finally 展示四个块的职责分离
# ============================================================

def load_config(raw: str) -> dict | None:
    fp = None  # 占位，模拟一个需要在 finally 释放的资源
    try:
        # 只把「可能失败」的最小语句放进 try
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        # 失败路径：只处理 JSON 解析错误
        print(f"[except] 配置解析失败：{e}")
        return None
    else:
        # 成功路径：try 没有异常时才会走到这里
        # 这里的异常（例如下面的 KeyError）不会被上面的 except 捕获
        if "version" not in parsed:
            raise KeyError("缺少 version 字段")
        print(f"[else] 解析成功，version = {parsed['version']}")
        return parsed
    finally:
        # 清理路径：无论成功失败都会执行
        print("[finally] 清理工作（例如关闭文件、释放连接）")


if __name__ == "__main__":
    good = '{"version": 3, "name": "demo"}'
    bad = '{not valid json}'

    print("--- 成功用例 ---")
    print("结果:", load_config(good))

    print("\n--- 失败用例（JSON 非法） ---")
    print("结果:", load_config(bad))

    print("\n--- 失败用例（缺字段，会从 else 里抛出） ---")
    try:
        load_config('{"name": "demo"}')
    except KeyError as e:
        print("[caller] 捕获到 else 里抛出的异常：", e)
```


---

## 本课题目

### single_choice · None



- [A] throw
- [B] raise
- [C] error
- [D] except

**参考答案**：1

**解析**：Python 使用 raise 语句主动引发异常；throw 是 Java 等语言的写法，error 不是 Python 的异常抛出关键字，except 用于捕获异常。

### single_choice · None



- [A] 程序正常结束，无输出
- [B] 输出 bad value 并正常结束
- [C] 抛出 ValueError 异常并显示 Traceback，程序中断
- [D] 输出 ValueError: bad value 并继续执行后续代码

**参考答案**：2

**解析**：raise 引发异常后如果没有被捕获，会终止当前执行流程并打印 Traceback。

### single_choice · None



- [A] 只显示 TypeError: outer
- [B] 显示 TypeError: outer，并带有直接原因 ValueError: inner 的异常链信息
- [C] 只显示 ValueError: inner
- [D] 显示 ValueError: inner 和 TypeError: outer，但两者无关联

**参考答案**：1

**解析**：from e 建立了异常链，Traceback 中会显示 The above exception was the direct cause of the following exception。

### single_choice · None



- [A] 必须重写 __str__ 方法
- [B] 必须重写 __init__ 方法并调用 super().__init__(message)
- [C] 必须继承自 BaseException 而不是 Exception
- [D] 必须实现 __raise__ 方法

**参考答案**：1

**解析**：自定义异常通常继承 Exception，并在 __init__ 中把消息传给父类，这样 str(e) 才能返回消息。

### single_choice · None



- [A] raise 只能在 except 块中使用
- [B] raise 可以在任何需要引发异常的地方使用
- [C] raise 只能引发内置异常，不能引发自定义异常
- [D] raise 后必须跟字符串作为异常消息

**参考答案**：1

**解析**：raise 是通用语句，可以在任何位置引发异常；自定义异常同样可以通过 raise 抛出。

### single_choice · None



- [A] 只抛出 Exception: a
- [B] 只抛出 Exception: b
- [C] Exception: b 被抛出，且 a 不会出现在异常链中
- [D] Exception: b 被抛出，且 a 会作为隐式上下文出现在异常链中

**参考答案**：3

**解析**：在 except 块中抛出新的异常时，原异常会作为 __context__ 隐式关联，Traceback 中会显示 During handling of the above exception。

### single_choice · None



- [A] raise NewError from None
- [B] raise NewError without context
- [C] raise NewError from False
- [D] raise NewError ignore_context

**参考答案**：0

**解析**：raise ... from None 会设置 __suppress_context__，从而在 Traceback 中隐藏原始异常上下文。

### single_choice · None



- [A] ValueError
- [B] TypeError
- [C] SystemExit
- [D] KeyError

**参考答案**：2

**解析**：SystemExit 通常由解释器在退出时使用；用户代码主动 raise SystemExit 虽然可行，但一般应使用 sys.exit()，且它继承自 BaseException。

### single_choice · None



- [A] e.args
- [B] e.message
- [C] e.msg
- [D] e.reason

**参考答案**：0

**解析**：Python 3 中异常消息存储在 args 元组中，通常使用 str(e) 获取可读消息；message 属性在 Python 3 已移除。

### single_choice · None



- [A] 输出 -1
- [B] 输出 None
- [C] 抛出 ValueError: negative，程序中断
- [D] 输出 negative 并返回 -1

**参考答案**：2

**解析**：check(-1) 在条件分支中 raise ValueError，未被捕获，因此程序中断并显示 Traceback。

### single_choice · None



- [A] raise 会跳过 finally 块
- [B] raise 会正常触发 finally 块的执行
- [C] raise 只能出现在 else 块中
- [D] raise 在 try 块中不会触发 except

**参考答案**：1

**解析**：无论 try 块中是否 raise，finally 块都会执行（除非进程被强制终止）。

### single_choice · None



- [A] 只执行 raise ValueError("one")
- [B] 先执行 raise ValueError("one")，再执行 raise KeyError("converted")
- [C] 只执行 raise KeyError("converted")
- [D] 两个 raise 都不会执行

**参考答案**：1

**解析**：当 n==1 时，先进入 raise ValueError，被 except 捕获后又执行 raise KeyError。

### single_choice · None



- [A] raise ValueError
- [B] raise ValueError()
- [C] raise ValueError("invalid")
- [D] 以上写法均合法

**参考答案**：3

**解析**：raise 可以引发异常类、异常实例，或带参数的异常实例。

### single_choice · None



- [A] try
- [B] except
- [C] finally
- [D] else

**参考答案**：1

**解析**：raise 通常出现在 except 块中，用于在捕获异常后重新抛出或抛出新的异常；finally 用于清理，不是重新抛出的必需关键字。

### single_choice · None



- [A] 只输出 caught
- [B] 输出 caught，然后重新抛出 TypeError，程序中断
- [C] 输出 caught，异常被忽略，程序正常结束
- [D] 直接抛出 TypeError，不输出 caught

**参考答案**：1

**解析**：except 块中先打印 caught，随后 raise 不带参数会重新引发当前正在处理的异常。

### single_choice · None



- [A] 抛出一个新的 RuntimeError
- [B] 重新抛出当前正在处理的异常
- [C] 忽略当前异常并继续执行
- [D] 结束当前函数并返回 None

**参考答案**：1

**解析**：裸 raise 会重新抛出当前 except 正在处理的异常，通常用于记录日志后继续向上传播。

### single_choice · None



- [A] 抛出 KeyError 类本身，不是实例
- [B] Python 自动实例化 KeyError 并抛出该实例
- [C] 语法错误，无法运行
- [D] 返回 KeyError 类对象，不抛异常

**参考答案**：1

**解析**：raise 后跟异常类时，Python 会自动调用该类的无参构造创建一个实例并抛出。

### single_choice · None



- [A] 类型为 RuntimeError，消息为 something failed
- [B] 类型为 Exception，消息为 RuntimeError
- [C] 类型为 RuntimeError，消息为空
- [D] 类型为 something failed，消息为 RuntimeError

**参考答案**：0

**解析**：raise 后跟异常实例时，异常类型为实例所属类，消息为构造时传入的参数。

### single_choice · None



- [A] raise 只能用于测试，assert 用于生产代码
- [B] assert 在优化模式下可能被移除，而 raise 不会
- [C] raise 不能抛出 AssertionError
- [D] assert 比 raise 更灵活，可以抛出任意异常类型

**参考答案**：1

**解析**：assert 语句在 Python 以 -O 优化模式运行时会被移除，而 raise 始终生效。

### single_choice · None



- [A] except ValueError:
      raise ValueError("new")
- [B] except ValueError as e:
      raise ValueError("new") from e
- [C] except ValueError:
      return ValueError("new")
- [D] except ValueError as e:
      print(e); raise

**参考答案**：1

**解析**：raise ... from ... 会显式设置 __cause__，保留原始异常上下文；直接 raise 新异常不会显式关联原因，选项 D 是重新抛出原异常。

### single_choice · None



- [A] 自定义异常类必须直接继承自 BaseException
- [B] 自定义异常类通常继承自 Exception 或其子类
- [C] 自定义异常类不能有自己的 __init__ 方法
- [D] 自定义异常类只能是空类，不能添加任何属性

**参考答案**：1

**解析**：自定义异常一般继承 Exception（或其子类），这样既能被常规的 except Exception 捕获，又不会误捕获 KeyboardInterrupt、SystemExit 等 BaseException 直接子类。自定义异常完全可以添加属性和自定义 __init__。

### single_choice · None



- [A] MyError 出错了
- [B] Exception 出错了
- [C] MyError
- [D] Exception

**参考答案**：0

**解析**：raise MyError('出错了') 抛出的是 MyError 实例，type(e).__name__ 得到类名 'MyError'，str(e) 得到传入的参数 '出错了'。MyError 继承自 Exception，所以能被 except Exception 捕获。

### multi_choice · None



- [A] Exception 的子类不会意外拦截 KeyboardInterrupt 和 SystemExit
- [B] except Exception 能捕获业务异常，语义更清晰
- [C] BaseException 子类不能被 raise
- [D] 继承 Exception 更符合 Python 异常层次的设计约定

**参考答案**：[0, 1, 3]

**解析**：KeyboardInterrupt 和 SystemExit 直接继承 BaseException 而非 Exception，因此业务代码很少会误捕获它们。继承 Exception 语义清晰且符合约定。BaseException 子类同样可以 raise，C 错误。

### fill_blank · None



**参考答案**：["Exception, super().__init__", "Exception, super().__init__", "Exception, super().__init__", "Exception,super().__init__"]

**解析**：继承 Exception 是自定义异常的常规做法，第一空填 Exception。第二空应调用父类初始化，即 super().__init__(msg)，这样 str(e) 才能正常返回消息。

### fill_blank · None



**参考答案**：["from", "from "]

**解析**：使用 raise ... from e 语法可以显式设置 __cause__，形成异常链。不加 from 时 Python 也会自动设置 __context__，但 __cause__ 是显式指定的。

### fill_blank · None



**参考答案**：["class MyError(Exception): pass", "class MyError(Exception):pass", "class MyError( Exception ): pass"]

**解析**：最简单的自定义异常只需继承 Exception 并提供空的类体。常见写法是 class MyError(Exception): pass。

### code_reading · None



**参考答案**：输出为 A DBError。

**解析**：except 从上到下匹配，DBError 是 AppError 的子类，第一个分支 except AppError 先匹配成功，因此打印 'A DBError'。第二个 except DBError 永远不会执行。这体现了「子类应排在父类之前」的原则。

### code_reading · None



**参考答案**：输出为：not found 404 ('not found',)。

**解析**：super().__init__(msg) 将 'not found' 存入 args，所以 str(e) 为 'not found'，e.args 为 ('not found',)。code 是自定义属性，值为 404。

### code_reading · None



**参考答案**：输出为：ValueError origin。

**解析**：raise Wrap('wrapped') from e 显式设置新异常的 __cause__ 为原始 ValueError 实例。外层捕获 Wrap 后，w.__cause__ 就是那个 ValueError，其类型名为 ValueError，字符串为 origin。

### scenario · None



**解析**：合理设计是定义一个基类（如 PaymentError 继承 Exception），再让三个具体错误作为其子类。调用方可以捕获基类统一处理，也可以捕获具体子类。底层网络异常在转换时使用 raise ... from e 保留 __cause__，便于排查根因。

### scenario · None



**解析**：因为 MyError 继承自 Exception，except Exception 分支会先匹配所有 Exception 子类，导致专门的 except MyError 永远不执行。修复方式是把更具体的子类异常（except MyError）放到前面，父类异常放到后面。

### single_choice · None



- [A] 子类异常必须先于父类异常被 except 捕获
- [B] 父类异常必须先于子类异常被 except 捕获
- [C] 捕获顺序不影响结果
- [D] 自定义异常不能被多层 except 捕获

**参考答案**：0

**解析**：except 从上到下匹配，先匹配到的分支生效。如果把父类异常写在前面，子类异常会被父类分支提前捕获，导致子类分支永远不执行，所以子类应排在父类前面。

### single_choice · None



- [A] 为每种可预见的业务错误定义专门的异常类，便于调用方精确捕获
- [B] 把所有错误都用 raise Exception('error') 抛出
- [C] 用自定义异常替代所有 if 判断
- [D] 把自定义异常当作普通数据容器返回值使用

**参考答案**：0

**解析**：自定义异常的价值在于表达领域特定的错误类型，让调用方可以针对性地捕获并处理。全部用 Exception 会丢失类型信息，无法精确区分；异常用于控制流替代 if 也不合适。

### single_choice · None



- [A] 让异常的 args 包含 msg，并保证 str(e) 正常返回该消息
- [B] 强制异常必须带两个参数
- [C] 让异常自动被打印到控制台
- [D] 使异常无法被捕获

**参考答案**：0

**解析**：Exception.__init__ 会把参数存入 self.args，str(e) 默认返回 args 的表示，因此调用 super().__init__(msg) 能保证消息正确保存和显示。code 通过自定义属性额外附加。

### single_choice · None



- [A] 改变 print(e) 或 str(e) 时显示的文本
- [B] 决定异常能否被捕获
- [C] 决定异常的继承层次
- [D] 决定异常是否终止程序

**参考答案**：0

**解析**：__str__ 控制对象的字符串表示，对异常来说就是 print(e) 或 str(e) 显示的内容，不影响捕获、继承或程序终止行为。

### single_choice · None



- [A] 它用于显式指定异常链的 __cause__，保留原始异常信息
- [B] 它会把两个异常合并成一个
- [C] 它只能用于内置异常
- [D] 它会阻止原始异常被记录

**参考答案**：0

**解析**：raise NewError(...) from e 会把 e 设为新异常的 __cause__，形成显式异常链，便于追踪根因。它不会合并异常，也不限于内置异常。

### single_choice · None



- [A] 能，因为 Exception 是 BaseException 的子类
- [B] 不能，必须直接继承 BaseException
- [C] 不能，除非重新注册
- [D] 只能被 finally 捕获

**参考答案**：0

**解析**：Exception 继承自 BaseException，所以 Exception 的任意子类（包括自定义异常）都能被 except BaseException 捕获。一般不推荐捕获 BaseException，因为它会吞掉 KeyboardInterrupt 和 SystemExit。

### multi_choice · None



- [A] 自定义异常应尽量继承 Exception 而非 BaseException
- [B] 可以通过自定义属性携带结构化错误信息，如错误码
- [C] 捕获时应把子类异常放在父类异常之前
- [D] 自定义异常必须实现 __str__ 才能抛出
- [E] raise NewError() from e 可以保留原始异常作为 __cause__

**参考答案**：[0, 1, 2, 4]

**解析**：A、B、C、E 都是自定义异常的常见正确做法。自定义异常不需要实现 __str__ 也能抛出，默认会使用 args 的表示，所以 D 错误。

### multi_choice · None



- [A] class MyError(Exception): pass
- [B] class MyError(ValueError): pass
- [C] class MyError(Exception):
      def __init__(self, msg, code):
          super().__init__(msg)
          self.code = code
- [D] class MyError: pass

**参考答案**：[0, 1, 2]

**解析**：A、B、C 都是合法且常见的自定义异常定义。D 定义的类不继承任何异常基类，抛出时 raise MyError() 会因不是 BaseException 子类而报 TypeError，因此不是有效的异常类定义。

### single_choice · None



- [A] try 块中一旦有任何语句执行，else 块就一定会执行
- [B] else 块只在 try 块没有抛出异常时执行
- [C] else 块在 try 块抛出异常时执行
- [D] else 块无论 try 块是否抛异常都会执行

**参考答案**：1

**解析**：else 子句仅在 try 块正常结束（没有异常传播出来）时执行；若 try 中抛出被捕获的异常，则执行 except 而跳过 else。finally 才是无论是否异常都执行。

### single_choice · None



- [A] A
  D
- [B] A
  C
  D
- [C] A
  B
  C
  D
- [D] A
  C

**参考答案**：1

**解析**：try 块正常执行打印 A，无异常所以执行 else 打印 C，最后 finally 打印 D。输出顺序为 A、C、D。

### multi_choice · None



- [A] 无论是否发生异常，finally 都会执行
- [B] else 只在 try 正常结束时执行
- [C] 发生异常时 else 与 finally 都不会执行
- [D] 当 try 中执行了 return、break 或 continue 时，finally 仍会执行

**参考答案**：[0, 1, 3]

**解析**：finally 在控制流离开 try 语句时总会被执行，包括 return/break/continue 的情形；发生异常时 else 跳过但 finally 仍会运行，所以第三项错误。

### fill_blank · None



**参考答案**：["else"]

**解析**：try 正常结束（无异常传播）时执行 else 子句；finally 无论是否异常都执行。

### fill_blank · None



**参考答案**：["except", "except 子句", "except子句"]

**解析**：Python 语法要求 else 必须与至少一个 except 搭配，单独出现 try...else 会触发 SyntaxError。

### fill_blank · None



**参考答案**：["finally", "finally 子句", "finally子句"]

**解析**：finally 用于释放资源等必须执行的清理工作，不受异常是否发生影响。

### code_reading · None



**参考答案**：value 10\ncleanup

**解析**：int('10') 合法返回 10，无异常，因此 except 跳过、执行 else 打印 'value 10'，最后 finally 打印 'cleanup'。

### scenario · None



**解析**：应缩小 try 的范围，只让转换操作处于 try 中并用 except ValueError 处理；把后续计算放入 else 子句，这样后续抛出的 KeyError 不会被本轮 except 捕获，从而暴露真实问题。

### scenario · None



**解析**：打开文件放在 try，异常处理放 except，数据处理放 else，日志/清理放 finally。数据处理放 try 内会被本次 except 覆盖到其可能抛出的异常，放在 else 可将其与「打开失败」区分开来。

### single_choice · None



- [A] caught
  no error
  done
- [B] caught
  done
- [C] no error
  done
- [D] caught
  no error

**参考答案**：1

**解析**：try 抛出 ValueError 被 except 捕获打印 caught，因为有异常所以 else 被跳过，finally 一定执行打印 done。

### single_choice · None



- [A] else 用来处理 try 中未捕获的异常
- [B] else 用来放置只在 try 块成功执行后才应运行的代码，以避免意外捕获其抛出的异常
- [C] else 等价于 finally，两者可互换
- [D] else 只能配合 except 使用，不能单独出现

**参考答案**：1

**解析**：把「成功后才执行」的逻辑放进 else，可以让其抛出的异常不被本次 except 捕获，从而与 try 中受保护的代码区分开，这是 else 的核心价值。

### single_choice · None



- [A] open failed
  end
- [B] open ok
  end
- [C] open ok，随后 OSError 传播，但 end 仍打印
- [D] open ok
  open failed
  end

**参考答案**：2

**解析**：open 成功所以进入 else 打印 open ok；else 中的 f.read() 抛出的 OSError 不会被本 try 的 except 捕获，会向外传播，但 finally 依然会执行打印 end。

### single_choice · None



- [A] 1
- [B] 2
- [C] None
- [D] 抛出 SyntaxError

**参考答案**：3

**解析**：else 子句必须至少有一个 except 子句与之配对，单独的 try...else 是语法错误，会在编译时被拒绝。

### single_choice · None



- [A] else 和 finally 都不执行
- [B] else 不执行，finally 执行，异常继续传播
- [C] else 执行，finally 执行
- [D] else 执行，finally 不执行

**参考答案**：1

**解析**：else 只在 try 无异常时执行，因此此处跳过；finally 无论如何都执行。未被捕获的异常在 finally 结束后继续向外传播。

### single_choice · None



- [A] finally 中的 return 会被忽略，以 try 或 except 的 return 为准
- [B] finally 中的 return 会覆盖 try 或 except 中已经确定的返回值
- [C] finally 中不允许出现 return，否则报 SyntaxError
- [D] 只有 try 中也有 return 时 finally 的 return 才生效

**参考答案**：1

**解析**：finally 块中若执行 return，会覆盖之前 try/except 中已计算的返回值，因为 finally 在返回前执行。这是常见的陷阱。

### multi_choice · None



- [A] else 子句只在 try 块未抛出异常时执行
- [B] finally 子句无论是否发生异常都会执行
- [C] else 中抛出的异常可以被同一个 try 的 except 捕获
- [D] else 必须与至少一个 except 搭配使用

**参考答案**：[0, 1, 3]

**解析**：else 只在无异常时执行且必须与 except 配对；finally 总是执行。else 中抛出的异常不会被本轮 except 捕获，因此该项错误。

### multi_choice · None



- [A] 把「成功后才会执行」的后续步骤放进 else，避免被 except 意外捕获
- [B] 把需要严格保护、可能抛出被捕获异常的语句放进 try
- [C] 把 except 中处理的异常重新放进 else 里执行
- [D] 让 try 块只包含最小范围的、真正可能失败的代码

**参考答案**：[0, 1, 3]

**解析**：else 的设计意图是隔离「成功路径」与「受保护操作」。缩小 try 范围、用 else 承载后续逻辑是推荐做法；把异常处理移入 else 没有意义。
