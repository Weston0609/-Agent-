# s1u9l2 把 print 升级为可运维的日志系统 / Python 错误处理 (Error Handling) 入门到工程化

> 来源 `content/lessons/s1u9l2.json`

## py.proj.logging

# py.proj.logging：把 print 升级为可运维的日志系统

> **一句话直觉**：`print` 只能让你「看见」，`logging` 才能让你「查得到、查得清、查得动」——它是项目从脚本走向工程的第一道门槛。

前置知识：无。你只需要会写 Python 函数即可。

---

## 1. 为什么要用 logging，而不是 print

零基础时，`print("x =", x)` 就能调试。但一旦代码上了服务器：

- 你无法按「级别」过滤：调试信息、警告、报错混在一堆。
- 你无法把日志分别写到文件、控制台、甚至远程。
- 你无法知道「什么时候、哪个模块、第几行」打印的。
- 上线前你想删掉所有 print，但调试时又想加回来——反复修改代码非常糟。

`logging`（日志）是 Python 标准库自带的**日志框架**，核心思想：

1. **日志级别（level）**：按严重程度分类，运行时统一开关。
2. **日志记录器（Logger）**：你在代码里调用的对象。
3. **处理器（Handler）**：决定日志输出到哪里（控制台、文件、网络…）。
4. **格式器（Formatter）**：决定每条日志长什么样。

记住一句话：**Logger 负责“产生”，Handler 负责“送往哪里”，Formatter 负责“长什么样”**。

```python
# 最简使用：一行就能跑
import logging

logging.basicConfig(level=logging.INFO)   # 设置全局最低级别为 INFO
logging.info("服务启动")                 # INFO 级别，会输出
logging.debug("这条是调试信息")           # DEBUG 低于 INFO，默认不输出
```

---

## 2. 五个日志级别（Level）

Python 的 `logging` 定义了 5 个标准级别，从低到高：

| 级别 | 数值 | 用途 |
|------|------|------|
| DEBUG | 10 | 细粒度调试信息 |
| INFO | 20 | 正常事件（启动、请求完成） |
| WARNING | 30 | 潜在问题，但程序仍能跑 |
| ERROR | 40 | 出现错误，某个功能失败 |
| CRITICAL | 50 | 严重错误，程序可能即将崩溃 |

规则：**设置级别为 X，则低于 X 的日志被丢弃**。

```python
import logging
logging.basicConfig(level=logging.WARNING)   # 只显示 WARNING 及以上

logging.debug("看不见")      # 被过滤
logging.info("也看不见")     # 被过滤
logging.warning("磁盘空间低") # 输出
logging.error("连接失败")     # 输出
logging.critical("数据库崩溃")# 输出
```

**工程习惯**：开发环境用 `DEBUG`，生产环境用 `INFO` 或 `WARNING`，通过**环境变量或配置文件**切换，而不是改代码。

---

## 3. 用 Logger 对象，而不是 root logger

直接 `logging.info(...)` 用的是**根记录器（root logger）**。在稍大的项目里，正确做法是：**每个模块创建自己的 Logger**。

约定：`logger = logging.getLogger(__name__)`，`__name__` 会自动变成模块名（如 `myapp.db`）。

```python
# myapp/db.py
import logging

logger = logging.getLogger(__name__)   # 名字就是 "myapp.db"

def connect(host: str) -> None:
    logger.info("尝试连接 %s", host)   # 用 %s 占位，不要用 f-string（延迟格式化）
    logger.warning("重试中")
```

**为什么不用 f-string？**
`logger.info("连接 %s", host)` 只有在日志真的要被输出时才做字符串拼接，性能更好；`logger.info(f"连接 {host}")` 哪怕日志被过滤也会先拼字符串。

有了名字后，你可以在日志里一眼看出「哪一行、哪个模块」打印的。

---

## 4. Handler + Formatter：控制输出目的地和格式

想让日志同时**写控制台 + 写文件**？加两个 Handler 即可。想让日志带上时间、模块名、行号？用 Formatter。

```python
import logging

logger = logging.getLogger("demo")
logger.setLevel(logging.DEBUG)

# Handler 1：控制台
console = logging.StreamHandler()
console.setLevel(logging.INFO)         # 控制台只看到 INFO 及以上

# Handler 2：文件
file_handler = logging.FileHandler("app.log", encoding="utf-8")
file_handler.setLevel(logging.DEBUG)   # 文件里保留所有 DEBUG

# Formatter：时间 - 级别 - 模块名 - 行号 - 消息
fmt = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s"
)
console.setFormatter(fmt)
file_handler.setFormatter(fmt)

logger.addHandler(console)
logger.addHandler(file_handler)

logger.debug("只写到文件")
logger.info("控制台和文件都有")
```

常用字段速记：

- `%(asctime)s` 时间
- `%(levelname)s` 级别名
- `%(name)s` Logger 名字（模块名）
- `%(lineno)d` 行号
- `%(message)s` 日志内容

**工程习惯**：库代码（被 import 的模块）只 `getLogger`，**不要**在里面调 `basicConfig` 或加 Handler——把配置权交给使用者。只有「应用入口」（`main.py`、`app.py`）才配置 Handler。

---

## 5. 异常日志：`logger.exception` 是必备技能

捕获到异常时，只 `logger.error("出错")` 会丢掉**堆栈（traceback）**，排查问题会非常痛苦。

```python
import logging
logger = logging.getLogger(__name__)

try:
    1 / 0
except ZeroDivisionError:
    logger.exception("计算失败")   # 等价于 error(..., exc_info=True)，会自动附上堆栈
```

输出会包含 `Traceback (most recent call last): ...`，这是线上排查 bug 的关键。

最后一条工程习惯：**配置只做一次**（应用入口），**库代码只用 Logger**。这条规则能避免「日志重复输出」「某个模块日志莫名消失」等 90% 的坑。

```python
"""演示：一个可运行的最小 logging 工程范例。

运行方式：python demo.py
效果：控制台看到 INFO 及以上，同时 app.log 文件里保留 DEBUG 及以上。
"""

import logging


def setup_logging() -> logging.Logger:
    """在应用入口调一次，配置好 Logger、Handler、Formatter。"""
    logger = logging.getLogger("demo")
    logger.setLevel(logging.DEBUG)          # Logger 本身允许所有级别通过

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s"
    )

    console = logging.StreamHandler()       # 输出到控制台
    console.setLevel(logging.INFO)          # 控制台只显示 INFO 及以上
    console.setFormatter(fmt)

    file_handler = logging.FileHandler("app.log", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)    # 文件里保留 DEBUG
    file_handler.setFormatter(fmt)

    # 避免重复加 Handler（比如函数被调用多次）
    if not logger.handlers:
        logger.addHandler(console)
        logger.addHandler(file_handler)

    return logger


logger = setup_logging()


def divide(a: float, b: float) -> float:
    logger.debug("divide called: a=%s b=%s", a, b)   # 用 %s 延迟格式化
    return a / b


if __name__ == "__main__":
    logger.info("程序启动")
    print("3 / 2 =", divide(3, 2))

    try:
        divide(1, 0)
    except ZeroDivisionError:
        logger.exception("除零错误")   # 自动带上 traceback

    logger.warning("磁盘空间偏低")
```

## py.proj.error_handling

# Python 错误处理 (Error Handling) 入门到工程化

## 一句话直觉

程序总会在你意想不到的地方崩溃——网络断了、文件没了、用户输入乱填。**错误处理 (Error Handling)** 就是让程序在遇到这些情况时，不是直接死掉，而是优雅地说“这里出问题了，我换个方式继续”或者“我告诉你到底哪里错了”，而不是给你一个晦涩的 Traceback。

---

## 1. 为什么需要错误处理？

在真实项目中，任何一次 I/O（文件、网络、数据库）、任何一次用户输入、任何一次第三方 API 调用，都可能失败。如果代码只有“正常路径”，那它就是一个随时会爆炸的定时炸弹。

```python
# 没有错误处理的代码
num = int(input("请输入一个整数: "))   # 用户输入 'abc' -> ValueError，程序直接崩溃
print(10 / num)                        # num 为 0 -> ZeroDivisionError
```

错误处理的目标有三个层次：
1. **不让程序崩溃**（对用户友好）。
2. **知道错在哪里**（方便调试）。
3. **知道怎么补救**（比如重试、回退、记录日志）。

---

## 2. 基础语法：try / except / else / finally

Python 用 `try` 包裹可能出错的代码，用 `except` 捕获指定类型的异常。

```python
try:
    num = int(input("请输入一个整数: "))
except ValueError:
    # 只有 ValueError 才会进入这里
    print("输入的不是合法整数！")
else:
    # 没有异常时才执行（工程上建议把“成功路径”放这里）
    print(f"你输入的是 {num}")
finally:
    # 无论成功失败都会执行，常用于释放资源
    print("程序结束。")
```

要点：
- `except` 后面尽量写**具体的异常类型**，不要用裸 `except:`（它会连 `KeyboardInterrupt` 都吞掉，让你按 Ctrl+C 都停不下来）。
- `else` 块是工程习惯：把可能报错的代码放在 `try` 里，把“确认成功后才做的事”放在 `else`，避免误捕。
- `finally` 一定执行，适合关闭文件、释放连接。

---

## 3. 异常的传播与自定义异常

异常会沿着调用栈向上“冒泡”，直到被某个 `except` 接住，或者到达顶层导致程序终止。工程中我们会：
- 在能处理的地方处理；
- 不能处理时，包装成更清晰的异常再向外抛；
- 定义自己的异常类表达业务错误。

```python
class InsufficientBalanceError(Exception):
    """自定义异常：余额不足。"""
    def __init__(self, balance, amount):
        super().__init__(f"余额 {balance} 不足以支付 {amount}")
        self.balance = balance
        self.amount = amount


def withdraw(balance, amount):
    if amount > balance:
        raise InsufficientBalanceError(balance, amount)
    return balance - amount


try:
    withdraw(100, 200)
except InsufficientBalanceError as e:
    print("业务异常:", e)
    print("差额:", e.amount - e.balance)
```

要点：
- 自定义异常继承 `Exception`，不要继承 `BaseException`。
- 异常类名推荐以 `Error` 结尾（PEP 8）。
- 用 `raise X from Y` 保留原始异常链，方便排查根因。

---

## 4. 资源管理：with 语句与上下文管理器 (Context Manager)

打开文件、连数据库、开锁——这类资源必须在结束时释放。`with` 语句会自动帮你做“收尾”，即使中途抛异常也保证释放。

```python
# 推荐写法：会自动关闭文件
with open("data.txt", "w", encoding="utf-8") as f:
    f.write("hello\n")

# 等价于：
f = open("data.txt", "w", encoding="utf-8")
try:
    f.write("hello\n")
finally:
    f.close()
```

`with` 背后是**上下文管理器协议 (Context Manager Protocol)**：`__enter__` 和 `__exit__` 方法。你可以自己写一个：

```python
class Timer:
    import time
    def __enter__(self):
        self.start = self.time.perf_counter()
        return self
    def __exit__(self, exc_type, exc, tb):
        self.end = self.time.perf_counter()
        print(f"耗时 {self.end - self.start:.4f}s")
        # 返回 False 表示不吞掉异常
        return False

with Timer():
    sum(range(1_000_000))
```

---

## 5. 工程化建议（给资深工程师的部分）

- **窄化 try 块**：`try` 里只放最可能出错的那一行，避免误捕别的异常。
- **精确捕获**：`except ValueError` 比 `except Exception` 好，后者会掩盖 bug。
- **永远不要静默失败**：接了异常就至少 `logging.exception(...)`，否则线上问题没人能查。
- **保持异常链**：`raise NewError(...) from e`，让 traceback 完整。
- **异常是 API 的一部分**：给你的库设计一套清晰的异常层级，比如 `MyLibError` 作为基类，下面再分 `ConfigError` / `NetworkError`。
- **不要用异常做正常控制流**：可以用，但读起来往往不如 `if` 清楚。
- **记录结构化上下文**：日志里带上请求 ID、用户 ID、参数，出了事能定位。

```python
import logging

logging.basicConfig(level=logging.INFO)

def parse_age(text):
    try:
        age = int(text)
    except ValueError as e:
        # 记日志 + 抛出自定义异常，保留链
        logging.exception("解析年龄失败: %r", text)
        raise ValueError(f"年龄必须是整数，得到 {text!r}") from e
    if not 0 <= age <= 150:
        raise ValueError(f"年龄超出合理范围: {age}")
    return age

try:
    parse_age("abc")
except ValueError as e:
    print("捕捉到:", e)
```

到这里，你已经从“语法怎么写”走到“设计怎么想”了。

```python
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


class InsufficientBalanceError(Exception):
    """业务异常：余额不足。"""
    def __init__(self, balance: float, amount: float):
        super().__init__(f"余额 {balance} 不足以支付 {amount}")
        self.balance = balance
        self.amount = amount


def withdraw(balance: float, amount: float) -> float:
    if amount <= 0:
        raise ValueError(f"取款金额必须为正，收到 {amount}")
    if amount > balance:
        raise InsufficientBalanceError(balance, amount)
    return balance - amount


def safe_withdraw(balance: float, amount: float) -> float | None:
    """在边界处统一处理异常，返回新余额或 None。"""
    try:
        new_balance = withdraw(balance, amount)
    except ValueError as e:
        logging.exception("参数错误: %s", e)
        return None
    except InsufficientBalanceError as e:
        logging.warning("业务规则拒绝: %s (缺口 %.2f)", e, e.amount - e.balance)
        return None
    else:
        logging.info("取款成功，新余额 = %.2f", new_balance)
        return new_balance
    finally:
        # 这里演示 finally：无论成功失败都会记录一行
        logging.debug("safe_withdraw 调用结束")


if __name__ == "__main__":
    print(safe_withdraw(100, 30))    # 成功 -> 70
    print(safe_withdraw(100, 300))   # 余额不足 -> None
    print(safe_withdraw(100, -5))    # ValueError -> None
```


---

## 本课题目

### single_choice · None



- [A] 在业务代码各处直接写 print() 输出调试信息，上线前再逐个删除
- [B] 定义模块级 logger = logging.getLogger(__name__)，用 logger.info() 等方法记录
- [C] 把文件名硬编码进 logging.basicConfig(filename='app.log') 后随处重新配置
- [D] 用 sys.stdout.write() 替代 print()，因为这样性能更好

**参考答案**：1

**解析**：最佳实践是每个模块用 logging.getLogger(__name__) 获取带层级名称的 logger，这样可以通过 root 或父 logger 统一控制级别和输出，避免 print 无法分级、无法过滤、无法统一关闭的问题。A 难以维护；C 在库代码中反复调用 basicConfig 会污染全局配置；D 只是换了个输出函数，没有日志级别能力。

### single_choice · None



- [A] debug() 的参数必须写成关键字形式，位置参数会被忽略
- [B] logger 对象没有调用 setLevel，因此消息被丢弃
- [C] logging 默认的有效级别是 WARNING，DEBUG 低于该级别被过滤
- [D] 字符串里用了 %s 占位符，logging 无法识别，于是静默丢弃

**参考答案**：2

**解析**：logging 的 root logger 默认级别为 WARNING，未显式配置时 DEBUG/INFO 消息不会输出。A 错误，位置参数正是推荐写法；B 描述不准确，logger 有自己的级别但默认有效级别由层级链和 root 决定；D 错误，logging 支持 % 风格惰性格式化。

### single_choice · None



- [A] 它只能在 except 块之外调用，否则会抛异常
- [B] 它以 ERROR 级别记录消息，并自动附带当前异常的堆栈信息
- [C] 它与 logger.error() 完全等价，不包含任何堆栈信息
- [D] 它会把程序异常重新抛出，因此必须配合 try/finally 使用

**参考答案**：1

**解析**：logging.exception() 等价于在 ERROR 级别调用并传入 exc_info=True，适合在 except 块中使用。A 错误，它通常就是在 except 块中调用；C 错误，它额外携带堆栈；D 错误，它不会重新抛出异常。

### single_choice · None



- [A] 在 loggers 段的 'app' 下用 handlers: ['console'] 指定
- [B] 在 handlers 段的 'console' 下用 loggers: ['app'] 指定
- [C] 在 root 段写 'app': 'console'
- [D] dictConfig 不支持这种关联，只能靠代码手动 addHandler

**参考答案**：0

**解析**：dictConfig 的 loggers 段中，每个 logger 条目通过 handlers 列表引用 handlers 段中定义的 handler 名称。B 方向反了；C 中 root 段的键是 level、handlers 等，不是 logger 名到 handler 名的映射；D 错误，dictConfig 正是为声明式配置而设计。

### single_choice · None



- [A] 所有模块共用一个 root logger，通过修改全局级别来区分
- [B] 为每个模块获取自己的命名 logger，并分别附加指向不同文件的 FileHandler
- [C] 在每个模块里都调用一次 logging.basicConfig(filename=...)
- [D] 在每个模块里直接打开文件并使用 file.write() 写日志

**参考答案**：1

**解析**：按名称获取 logger 并各自附加不同 handler，可以按模块分流且互不干扰。A 无法按模块分流；C 中 basicConfig 只对 root 生效，且重复调用不会按预期重配；D 绕过了 logging 的级别、格式与并发处理机制。

### single_choice · None



- [A] DEBUG < INFO < WARNING < ERROR < CRITICAL
- [B] INFO < DEBUG < WARNING < ERROR < CRITICAL
- [C] DEBUG < WARNING < INFO < ERROR < CRITICAL
- [D] CRITICAL < ERROR < WARNING < INFO < DEBUG

**参考答案**：0

**解析**：logging 预定义级别的数值依次为 DEBUG=10、INFO=20、WARNING=30、ERROR=40、CRITICAL=50，数值越大越严重。B、C 顺序错误；D 是倒序。

### single_choice · None



- [A] 让日志同时输出到控制台和文件
- [B] 当日志文件达到指定大小时自动轮转，避免单个文件无限增长
- [C] 按时间间隔自动把日志上传到远程服务器
- [D] 把日志记录压缩加密后再写入磁盘

**参考答案**：1

**解析**：RotatingFileHandler 基于文件大小进行轮转，超出 maxBytes 后重命名并新建文件，可配合 backupCount 限制保留数量。A 是同时挂多个 handler 的效果；C 属于 TimedRotatingFileHandler 按时间轮转，且都不负责上传；D 不是其职责。

### single_choice · None



- [A] 把所有进程的日志级别都提高到 CRITICAL，减少写入量
- [B] 让各进程统一通过一个负责写文件的进程或日志收集服务来落盘
- [C] 改用 print() 输出，因为 print 自带跨进程锁
- [D] 在每条日志后手动调用 flush()，即可保证内容不会交错

**参考答案**：1

**解析**：FileHandler 的锁只在单进程内有效，多进程直接写同一文件会出现交错。常见方案是集中到一个写入者（如专门的日志进程、队列或日志收集服务）。A 只是减少频率并未解决并发问题；C 错误，print 没有跨进程锁；D 中 flush 只保证缓冲写入，不保证多进程间的原子性。

### single_choice · None



- [A] logger.info('%s', obj)，其中 obj 是任意对象
- [B] logger.info('%d', '123')，把一个字符串传给 %d
- [C] logger.info('%s %s', a, b)，传入两个参数
- [D] logger.info('no placeholder')，不传额外参数

**参考答案**：1

**解析**：logging 的格式化最终走 % 风格，%d 要求整数，传入字符串会抛 TypeError。A 中 %s 接受任意对象；C 参数个数匹配；D 没有占位符时不传参数是合法的。

### single_choice · None



- [A] 在每个业务模块里分别写一套 handler 和格式配置
- [B] 在应用启动时集中配置一次（如 dictConfig 或 basicConfig），业务模块只调用 getLogger 记录
- [C] 在业务模块里调用 getLogger 后，逐个手动设置 formatter 与 level
- [D] 只在出现问题时临时修改源码加 print，排查完删除

**参考答案**：1

**解析**：日志配置应集中在应用入口完成，业务代码只负责产生日志。A、C 会造成配置分散、重复和冲突；D 不可持续且缺乏级别控制。

### single_choice · None



- [A] 程序因无法连接数据库而中断启动流程
- [B] 磁盘剩余空间低于阈值，但程序仍可继续运行
- [C] 用户输入了错误格式的邮箱，导致注册失败并返回错误页
- [D] 某个内部断言失败，数据已处于不一致状态

**参考答案**：1

**解析**：WARNING 表示「有问题但程序仍能继续运行」。A 通常是 ERROR 或 CRITICAL；C 属于可预期的业务校验失败，常用 INFO 或 WARNING，但相较之下 B 更符合「资源将耗尽但尚可运行」的典型 WARNING 场景；D 是严重错误，应为 ERROR 或 CRITICAL。

### single_choice · None



- [A] 每个模块用 logging.getLogger(__name__) 获取自己的 logger，由层级关系统一控制
- [B] 必须把 logger 作为全局单例放在一个模块中，其他模块导入该对象
- [C] 每个模块都新建一个 Logger 实例，绕过 getLogger 的管理
- [D] 直接把 root logger 传给所有模块使用

**参考答案**：0

**解析**：getLogger 对相同名字返回同一实例，配合 __name__ 可自然形成层级，便于按模块精细控制级别，无需手工传递。B 不是必须的，层级机制已能统一管理；C 绕过 getLogger 会破坏层级与命名约定；D 使用 root 会丢失模块粒度。

### single_choice · None



- [A] logger.info('user=%s, count=%d' % (user, count))
- [B] logger.info(f'user={user}, count={count}')
- [C] logger.info('user=%s, count=%d', user, count)
- [D] logger.info('user=' + user + ', count=' + str(count))

**参考答案**：2

**解析**：把参数作为 logging 调用的额外参数传入，只有在该条日志真正会被输出时才会执行格式化，避免不必要的字符串拼接开销。A、B、D 都会在调用前立即完成字符串拼接，即使日志被过滤也白做。

### single_choice · None



- [A] basicConfig 只能被调用一次，第二次会抛 ValueError 使程序崩溃
- [B] 它会修改全局 root logger 的 handler 配置，可能覆盖使用方应用自己的日志设置
- [C] 它只会影响当前模块的 logger，对其他模块没有任何作用，因此完全无害
- [D] 它会把日志级别强制设为 DEBUG，导致大量低级别日志输出

**参考答案**：1

**解析**：basicConfig 配置的是 root logger。库代码调用它会干扰宿主应用的日志配置，因此库中应只获取 logger 并记录，把配置权留给应用入口。A 错误，basicConfig 重复调用在已有 handler 时通常直接返回而不报错；C 错误，root 配置会影响所有未单独配置的 logger；D 错误，级别由传入参数决定。

### single_choice · None



- [A] getLogger('a.b') 返回的对象与 getLogger('a') 完全独立，不共享任何配置
- [B] getLogger('a.b') 是 getLogger('a') 的子 logger，未单独设置级别时会沿层级向上查找有效级别
- [C] getLogger(__name__) 中的点号会被替换成下划线，因此模块名 a.b 与 a_b 是同一个 logger
- [D] 只有以 root 开头的名字才能构成层级，其他名字都是平级的

**参考答案**：1

**解析**：logging 使用点号分隔的层级命名，子 logger 未显式设置级别时，其有效级别沿父级向上查找，最终落到 root。A 错误，它们存在父子关系；C 错误，点号就是层级分隔符，不会替换；D 错误，任意点号分隔名都构成层级。

### single_choice · None



- [A] 把该 logger 的 level 设置为 NOTSET
- [B] 把该 logger 的 propagate 属性设为 False
- [C] 调用 logging.disable(logging.CRITICAL)
- [D] 为该 logger 设置 disable_existing_loggers=True

**参考答案**：1

**解析**：logger 默认 propagate=True，记录会沿层级上传给祖先的 handler。若自己已有 handler，又不想让祖先再处理，可设 propagate=False。A 会让级别回退到父级，不解决重复；C 会全局关闭日志；D 是 dictConfig 中的参数，与传播无关。

### single_choice · None



- [A] logger 对象的名称，即传入 getLogger 的字符串
- [B] 日志记录所对应的级别名称，如 DEBUG、INFO、WARNING
- [C] 触发日志的源文件名与行号
- [D] 日志记录创建时的时间戳数值

**参考答案**：1

**解析**：levelname 是 LogRecord 的属性，表示级别名称。A 对应 %(name)s；C 对应 %(filename)s 与 %(lineno)d；D 对应 %(created)f，而 %(asctime)s 是格式化后的时间字符串。

### single_choice · None



- [A] logger = logging.getLogger('myapp'); logger.addHandler(logging.FileHandler('app.log'))
- [B] logger = logging.getLogger('myapp'); logger.setHandler(logging.FileHandler('app.log'))
- [C] logger = logging.getLogger('myapp'); logger.file = 'app.log'
- [D] logger = logging.getLogger('myapp'); logging.FileHandler('app.log').attach(logger)

**参考答案**：0

**解析**：标准做法是用 addHandler 把 FileHandler 附加到 logger 上。B 中 setHandler 不存在；C 中给 logger 随意赋属性不会生效；D 中 Handler 没有 attach 方法。

### single_choice · None



- [A] handler 没有级别概念，只有 logger 才有级别
- [B] logger 的级别决定消息是否被创建，handler 的级别决定该 handler 是否处理已创建的记录，两者需同时通过
- [C] handler 的级别会覆盖 logger 的级别，logger 的级别完全不起作用
- [D] 只要 logger 级别允许，所有 handler 无论自身级别如何都会输出该记录

**参考答案**：1

**解析**：一条日志要真正到达某个输出端，需要先通过 logger 的有效级别判断被创建，再经过该 handler 自身的级别判断被处理。A 错误，Handler 也有 setLevel；C 错误，handler 级别不会改变 logger 的级别；D 错误，不符合 handler 级别的记录会被该 handler 过滤。

### single_choice · None



- [A] logger.error('处理失败')
- [B] logger.error('处理失败', exc_info=True)
- [C] logger.error('处理失败', stack_info=True)
- [D] logger.error('处理失败', traceback=True)

**参考答案**：1

**解析**：exc_info=True 会让 logging 把当前异常的堆栈信息附到记录中。不带该参数只输出消息文本；stack_info 输出的是调用栈而非异常堆栈；traceback 不是 logging 支持的参数名。

### single_choice · None



- [A] f = open('data.txt'); process(f); f.close()
- [B] f = open('data.txt')
  try:
      process(f)
  finally:
      f.close()
- [C] f = open('data.txt')
  process(f)
  except: pass
- [D] with open('data.txt') as f:
      f.close()
      process(f)

**参考答案**：1

**解析**：使用 try/finally 可以保证即使 process 抛出异常，close 仍会被执行。选项 A 在异常时会跳过 close；选项 C 语法错误且没有关闭资源；选项 D 在 with 块内手动 close 后还继续使用 f，逻辑错误且资源已被提前释放。

### single_choice · None



- [A] A 后跟 D
- [B] B 后跟 D
- [C] A 后跟 C 后跟 D
- [D] 只有 D

**参考答案**：0

**解析**：'abc' 无法转换为整数，抛出 ValueError，先匹配到第一个 except 打印 A。因为异常已处理，else 分支不执行；finally 始终执行打印 D。所以输出 A 和 D。

### single_choice · None



- [A] inner 然后 outer
- [B] 只有 inner
- [C] 只有 outer
- [D] 报错中断

**参考答案**：0

**解析**：内层 try 抛出 KeyError，finally 先执行打印 inner，异常继续向外传播到外层 except 被捕获，打印 outer。finally 不会吞掉异常（除非其中有 return 或再次抛异常）。

### multi_choice · None



- [A] `except Exception` 会捕获绝大多数常规异常，但不会捕获 KeyboardInterrupt 和 SystemExit
- [B] `finally` 块无论是否发生异常都会执行
- [C] `else` 块在没有异常发生时执行
- [D] 可以在 `except` 块中重新抛出异常供上层处理
- [E] 捕获异常后必须显式调用 `sys.exit()` 才能继续

**参考答案**：[0, 1, 2, 3]

**解析**：Exception 是大多数异常的基类，KeyboardInterrupt 和 SystemExit 直接继承 BaseException，不会被普通 except Exception 捕获。finally 始终执行，else 在无异常时执行，except 中可以 `raise` 重抛。异常处理与 sys.exit 无关。

### multi_choice · None



- [A] 掩盖真正的 bug，导致调试困难
- [B] 可能让程序在错误状态下继续运行
- [C] 会让程序运行速度显著变慢
- [D] 使得错误失去堆栈信息，难以定位根因
- [E] 会自动修复错误

**参考答案**：[0, 1, 3]

**解析**：吞掉异常会隐藏 bug、使程序带病运行、丢失 traceback 信息。它不会显著拖慢程序，也不会自动修复错误。生产代码应至少记录日志或在无法处理时重新抛出。

### multi_choice · None



- [A] 为不同业务模块定义异常基类，便于上层统一捕获
- [B] 自定义异常类应继承 Exception 而不是 BaseException
- [C] 在异常消息中包含关键上下文（如 ID、参数值）
- [D] 为了图方便，用同一个异常类表示所有错误
- [E] 可以给自定义异常添加额外属性，如错误码

**参考答案**：[0, 1, 2, 4]

**解析**：合理的异常设计包括分层基类、继承 Exception、携带上下文信息、附加错误码等。用一个异常类表示所有错误会降低可辨识性，是不推荐的做法。

### fill_blank · None



**参考答案**：["else", "else:", "else 块", "else分支"]

**解析**：try/except/else/finally 结构中，else 分支只在 try 块未抛出异常时执行，适合放置那些'只有成功时才做'的操作，从而避免被本块的 except 误捕获。

### fill_blank · None



**参考答案**：["raise", "raise 语句", "裸 raise", "raise（不带参数）"]

**解析**：裸 `raise` 在 except 块中会重新抛出当前异常，并保留原始 traceback，比 `raise e` 更好，因为后者会把当前帧作为新的 traceback 起点。

### fill_blank · None



**参考答案**：["as", "as 关键字"]

**解析**：Python 3 使用 `except ExceptionType as e:` 绑定异常对象，Python 2 的逗号写法已被移除。注意 e 在 except 块结束后会被自动删除。

### code_reading · None



**参考答案**：done\n3.0\ndone\ninf

**解析**：第一次调用 6/2 正常返回 3.0，但 finally 在 return 之前先执行，打印 done，所以先输出 done 再输出 3.0。第二次调用 1/0 触发 ZeroDivisionError，被捕获返回 'inf'，finally 同样先打印 done。因此输出顺序为 done、3.0、done、inf。

### code_reading · None



**参考答案**：NameError，因为 Python 3 在 except 块结束后自动删除异常变量 err

**解析**：Python 3 为了防止异常对象与其 traceback 之间形成引用循环导致内存无法回收，会在 except 块结束时自动执行 `del err`。因此在块外访问 err 会触发 NameError。若需要在块外使用，应提前把信息保存到另一个变量（如 msg）。

### code_reading · None



**参考答案**：A\nC\nD

**解析**：先执行 try 块打印 A，然后抛出 ValueError。TypeError 分支不匹配，跳到 ValueError 分支打印 C，最后 finally 打印 D。异常被处理，不会向上传播。

### single_choice · None



- [A] Python 会执行所有匹配的 except 子句
- [B] Python 只执行第一个匹配的 except 子句，其余跳过
- [C] 父类异常写在子类异常前面不影响匹配
- [D] 多个 except 必须按字母顺序排列

**参考答案**：1

**解析**：Python 从上到下依次匹配 except 子句，命中第一个后执行其代码块，其余不再执行。因此若把父类异常（如 Exception）写在子类异常（如 ValueError）前面，子类分支将永远不会被命中，这是常见错误。

### scenario · None



**解析**：合理答案应包含：用 try/except 捕获具体的第三方超时/连接类异常（如 requests 的超时异常），不要裸捕获 Exception；在 except 内实现有限次数的重试或使用 tenacity/backoff 等库；重试耗尽后用 logging 记录完整信息（含堆栈）；再抛出封装后的自定义异常（如 UpstreamError）或转换为业务错误，让上层统一处理并返回友好响应。关键是区分可重试与不可重试异常、区分日志记录与异常传播层次。

### single_choice · None



- [A] 直接继承 BaseException
- [B] 继承 Exception 并添加业务相关的属性或信息
- [C] 使用字符串作为异常抛出
- [D] 每遇到错误就抛出 SystemExit

**参考答案**：1

**解析**：自定义异常应继承 Exception，避免继承 BaseException（后者会捕获 KeyboardInterrupt 等系统退出信号，破坏正常中断机制）。抛出字符串在 Python 3 中不合法。SystemExit 用于程序退出，不是业务错误的合适载体。

### single_choice · None



- [A] e 在 except 块外仍可访问，因为 Python 没有块级作用域
- [B] e 在 except 块结束后被自动删除，最后一行会抛出 NameError
- [C] e 在函数内始终有效
- [D] e 会变成全局变量

**参考答案**：1

**解析**：Python 3 在 except 块结束时自动删除异常变量 e（等价于 del e），以防止异常对象和 traceback 形成引用循环导致内存泄漏。因此最后一行 print(e) 会抛出 NameError。

### single_choice · None



- [A] 没有区别，完全等价
- [B] `raise` 重新抛出当前异常并保留原始 traceback，`raise e` 可能重写 traceback 起点
- [C] `raise` 只能用于 except 外
- [D] `raise e` 会改变异常类型

**参考答案**：1

**解析**：在 except 块内使用裸 `raise` 会重新抛出当前异常，并保留原始 traceback 信息；而 `raise e` 会把当前帧作为 traceback 的新起点，可能丢失原始抛出位置，不利于调试。

### single_choice · None



- [A] 1
- [B] 2
- [C] 报错
- [D] None

**参考答案**：1

**解析**：finally 块中的 return 会覆盖 try 块中的 return，因此函数返回 2。这是使用 finally 时的一个陷阱，通常不建议在 finally 中写 return，因为它会吞掉异常或覆盖返回值。

### single_choice · None



- [A] 检查一个变量是否等于 5
- [B] 判断列表长度是否大于 0
- [C] 从字典中读取可能不存在的键
- [D] 比较两个字符串是否相等

**参考答案**：2

**解析**：对于字典取键，Python 提供了 dict.get() 和 try/except KeyError 两种惯用写法，其中在键大概率不存在时用 try/except 更高效或更直接。其他选项用简单条件判断即可，无需异常处理。

### single_choice · None



- [A] 只捕获 ValueError，忽略 TypeError
- [B] 捕获 ValueError 和 TypeError 两种异常
- [C] 语法错误，元组不能用于 except
- [D] 捕获所有异常

**参考答案**：1

**解析**：except 后面可以跟异常类的元组，表示捕获其中任意一种异常。若想捕获所有异常应写 except Exception，但要谨慎使用以免掩盖 bug。

### single_choice · None



- [A] `raise NewError('x') from e` 会把 e 记录为 __cause__，保留原始异常上下文
- [B] `from` 关键字只能用于 import 语句
- [C] 使用 `from e` 会丢弃原始异常
- [D] `raise NewError('x') from e` 会抛出 e 而不是 NewError

**参考答案**：0

**解析**：`raise ... from ...` 用于显式建立异常链，将原异常存于 __cause__ 属性，新异常存于 __context__。这样在诊断时能同时看到两层异常信息，便于定位根因。
