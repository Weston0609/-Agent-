# s1u7l1 异常处理：try / except 入门到工程实践 / 多个异常的处理（Multiple Exceptions） / `try/finally`：让清理代码一定执行

> 来源 `content/lessons/s1u7l1.json`

## py.exc.try_except

# 异常处理：try / except 入门到工程实践

> 一句话直觉：程序总会遇到“意外”（除零、文件不存在、网络超时），**try/except** 让你优雅地接住这些意外，而不是让程序直接崩溃。

---

## 1. 为什么需要 try/except

写代码时我们总假设“输入是对的、文件是存在的”。但真实世界并非如此。

看下面这段代码：

```python
import math

print(math.sqrt(-1))
```

运行它会得到：

```
ValueError: math.sqrt(x): x must be non-negative
```

程序**直接崩溃（crash）**，后面所有代码都不再执行。

再比如 `int("abc")` 会抛 `ValueError`，`1/0` 会抛 `ZeroDivisionError`，`open("不存在.txt")` 会抛 `FileNotFoundError`。

这些“抛出”的东西叫 **异常（Exception）**：它是 Python 用来表示“我遇到问题了，处理不了”的机制。

如果不想让程序因为一次小问题就挂掉，就需要用 **try / except** 主动接住它。

---

## 2. 基本语法：try / except

语法结构：

```python
try:
    # 可能出错的代码
except 异常类型:
    # 出错时怎么办
```

Python 会先执行 `try` 里的代码；如果没有出错，`except` 块被跳过；一旦抛异常，程序**立刻跳到**匹配的 `except` 块，而不是崩溃。

### 示例 1：安全求平方根

```python
import math

def safe_sqrt(x):
    try:
        return math.sqrt(x)      # 负数会抛 ValueError
    except ValueError:
        print(f"输入 {x} 无法开平方")
        return None

print(safe_sqrt(16))    # 4.0
print(safe_sqrt(-1))    # 打印提示，返回 None
```

对比一下原始材料里的 `foo` 和 `bar`：它们用 `if x >= 0` 提前防御。那种写法不算错，但**只能覆盖你想到的情况**；而 try/except 能兜住“运行期真实发生的错误”，更贴近工程实践。

---

## 3. 捕获多种异常与 as 取异常对象

现实中的函数可能抛出**不同类型**的异常，需要分别处理。

```python
def to_int(s):
    try:
        return int(s)
    except (ValueError, TypeError) as e:
        # 一个 except 可以接多个异常类型（元组）
        # as e 把异常对象捕获，方便打印诊断信息
        print(f"转换失败：{type(e).__name__} -> {e}")
        return None

print(to_int("42"))     # 42
print(to_int("abc"))    # ValueError
print(to_int(None))     # TypeError
```

关键结论：

- `except A, B` 用元组形式一次捕获多个类型。
- `as e` 让你拿到异常对象，可以读 `e.args`、`str(e)` 等。
- `type(e).__name__` 是打印异常类名的常用技巧。

---

## 4. else、finally：完整结构

try/except 还可以配 `else` 和 `finally`：

| 子句 | 何时执行 |
|------|---------|
| `try` | 总是先执行 |
| `except` | try 中抛出匹配异常时 |
| `else` | try 中**没有**抛异常时 |
| `finally` | **无论如何**都执行 |

```python
def read_first_line(path):
    f = None
    try:
        f = open(path, "r", encoding="utf-8")
        data = f.readline()
    except FileNotFoundError:
        print(f"文件不存在：{path}")
        return None
    except OSError as e:
        print(f"读取文件出错：{e}")
        return None
    else:
        print("读取成功")
        return data.strip()
    finally:
        # 不管成功失败，都关掉文件句柄，防止资源泄漏
        if f is not None:
            f.close()

print(read_first_line("some.txt"))
```

工程意义：`finally` 是**资源释放（cleanup）**的标准位置，例如关闭文件、释放锁、断开连接。

更 Pythonic 的写法是用 `with` 上下文管理器，但理解 `finally` 的语义是基础。

---

## 5. 工程级实践：精细捕获 + 按需兜底

### 5.1 不要裸捕 `except:`

```python
# ❌ 不推荐：会吞掉 KeyboardInterrupt、SystemExit 等
try:
    do_something()
except:
    pass
```

裸 `except:` 会连用户按 Ctrl+C 都一并吞掉，非常危险。至少要写 `except Exception:`，更好的是**精确列出**你期望的异常。

### 5.2 不要用异常控制正常流程

原始材料中的 `foo / bar` 演示了：**用返回值 None 表达“不合法输入”** 是一种风格。工程上推荐：

- 你能提前判断的错误：用 `if` 提前校验（更清晰、更快）。
- 你**无法提前判断**、或来自外部（文件、网络、第三方库）的错误：用 try/except。

### 5.3 re-raise：记录后继续向上抛

```python
import logging
log = logging.getLogger(__name__)

def parse_config(raw):
    try:
        return dict(line.split("=", 1) for line in raw.splitlines())
    except ValueError as e:
        log.warning("配置解析失败：%s", e)
        raise       # 关键：重新抛出，让上层决定怎么处理
```

`raise` 单用可以**重新抛出当前异常**，同时保留原始 traceback。这样既记录了日志，又不掩盖问题。

### 5.4 `try/except/else/finally` 与 finally 中的 return

原始 PEP 8 里强调：

> 不要在 `try...finally` 的 `finally` 里写 `return / break / continue`，因为它会**悄悄吞掉正在传播的异常**。

```python
def foo():
    try:
        1 / 0
    finally:
        return 42          # ❌ ZeroDivisionError 被吞，函数却返回 42

print(foo())   # 42 —— 你根本不知道发生了除零
```

正确做法是让 `finally` 只负责清理，不改变控制流：

```python
def foo():
    try:
        return 1 / 0
    except ZeroDivisionError as e:
        print("出错了：", e)
        return None
```

---

## 6. 小结（判断用 if 还是 try）

| 场景 | 推荐 |
|------|------|
| 已知的、可提前判断的非法输入（`x < 0`） | `if` 提前校验 |
| 外部来源的失败（文件/网络/数据库） | `try / except` |
| 需要释放资源 | `try / finally` 或 `with` |
| 记录日志后继续向上传播 | `try / except ... raise` |
| 想“什么都接住然后忽略” | ⚠️ 不要这么做 |

学会 try/except，你的程序就从“脆弱脚本”迈向“靠谱工程”。

```python
import math
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)


def safe_sqrt(x):
    """安全求平方根：非数字或负数都返回 None 并记录原因。"""
    try:
        return math.sqrt(x)             # 可能抛 TypeError / ValueError
    except (TypeError, ValueError) as e:
        log.warning("sqrt(%r) 失败：%s", x, e)
        return None


def parse_int(s):
    """把字符串转 int；失败返回 None，并演示 else/finally。"""
    try:
        value = int(s)                  # 可能抛 ValueError
    except ValueError as e:
        print(f"  [parse_int] 无法解析 {s!r}: {e}")
        return None
    else:
        print(f"  [parse_int] 解析成功 -> {value}")
        return value
    finally:
        # 无论如何都会执行，这里只是打个日志（真实场景常用于释放资源）
        print(f"  [parse_int] 处理结束：input={s!r}")


if __name__ == "__main__":
    print("== safe_sqrt ==")
    print(safe_sqrt(16))    # 4.0
    print(safe_sqrt(-1))    # None（并记录 warning）
    print(safe_sqrt("abc")) # None（TypeError）

    print("\n== parse_int ==")
    print(parse_int("42"))
    print(parse_int("abc"))
```

## py.exc.multiple

# 多个异常的处理（Multiple Exceptions）

> 一句话直觉：现实中的代码出错往往不止一种原因，学会「一次捕获多种异常」才能让程序既健壮又优雅。

---

## 一、为什么需要「多个异常」？

假设你在写一个读取配置文件的函数：文件可能不存在（`FileNotFoundError`），也可能是 JSON 格式错误（`json.JSONDecodeError`），还有可能是权限问题（`PermissionError`）。

如果每种异常都写一个 `except`，代码会变得冗长：

```python
try:
    do_something()
except FileNotFoundError:
    handle_missing()
except json.JSONDecodeError:
    handle_bad_format()
except PermissionError:
    handle_permission()
```

Python 允许我们把「处理方式相同」的异常合并到一条语句里，这就是**多个异常（multiple exceptions）**。

---

## 二、基础语法：`except (A, B, C)`

多个异常要用**元组（tuple）**包裹，不能写 `except A, B`。

```python
# 把「文件不存在」和「没有权限」都当成同一种情况处理
try:
    with open("cfg.json") as f:
        data = f.read()
except (FileNotFoundError, PermissionError) as e:
    print(f"无法读取配置文件：{e}")
```

关键点：
- 括号是元组，不是分组表达式。
- `as e` 绑定的是**实际触发的那个异常实例**。
- 匹配顺序仍然从上到下，先匹配到的分支生效。

---

## 三、在一条语句里混合「单异常」和「多异常」

可以按处理逻辑分组：

```python
try:
    result = risky_operation()
except (ValueError, TypeError) as e:
    print(f"输入有问题：{e}")
except OSError as e:
    print(f"系统调用失败：{e}")
except Exception as e:  # 兜底
    print(f"未预期错误：{type(e).__name__}: {e}")
```

注意：更宽泛的异常要放在后面，否则前面的分支永远走不到。

---

## 四、异常元组可以传变量、可以动态构造

`except` 后面的表达式在运行时求值，因此可以复用变量：

```python
NETWORK_ERRORS = (ConnectionError, TimeoutError)

try:
    fetch()
except NETWORK_ERRORS as e:
    retry(e)
```

这在「库作者希望把一批异常暴露成公共名字」时非常常用。

---

## 五、从「捕获」到「分类处理」：`type(e)` 与 `isinstance`

当多种异常要区分为不同处理时，捕获后可以用 `isinstance` 分发：

```python
try:
    parse(data)
except (ValueError, TypeError, KeyError) as e:
    if isinstance(e, KeyError):
        print(f"缺少字段：{e.args[0]}")
    elif isinstance(e, TypeError):
        print("类型不匹配")
    else:
        print("值不合法")
```

对于自定义异常层次结构，`except` 本身就会按 MRO 匹配父类，无需手动 `isinstance`。

---

## 六、工程级建议

1. **不要用 `except Exception` 吞掉一切**——除非你确实要做顶层兜底并重新抛出。
2. **保持元组内异常语义相近**：把「都能用同一句话解释」的异常放在一起。
3. **捕获后要记日志**：`logging.exception(...)` 会带上 traceback。
4. **别把异常当控制流**：能用 `if` 判断的先判断，异常留给真正的意外。
5. **自定义异常可继承同一基类**，让调用方只写一条 `except` 就能覆盖一组：

```python
class AppError(Exception): ...
class ConfigError(AppError): ...
class NetworkError(AppError): ...

try:
    run()
except AppError as e:   # 一次覆盖子类
    log(e)
```

---

## 七、动手练习

写一个 `safe_read_number(path: str) -> float | None` 函数：

- 读取文件内容并转成 `float`。
- 用**一条 `except`** 同时捕获 `FileNotFoundError`、`PermissionError`（返回 `None` 并打印「文件不可读」）。
- 用**另一条 `except`** 同时捕获 `ValueError`、`TypeError`（返回 `None` 并打印「内容不是合法数字」）。
- 其它异常不捕获，让它自然抛出。

测试用例：文件不存在、内容为 `"abc"`、内容为 `"3.14"`。

完成后思考：如果把两个 `except` 合并成一条，可读性会变好还是变差？为什么？

```python
import json
import logging

logging.basicConfig(level=logging.INFO)


def safe_read_number(path: str):
    """读取文件并解析为 float；失败时返回 None。"""
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read().strip()
        return float(text)
    except (FileNotFoundError, PermissionError) as e:
        # 一组「文件层面」的错误，统一处理
        print(f"文件不可读：{e}")
        return None
    except (ValueError, TypeError) as e:
        # 一组「内容层面」的错误，统一处理
        print(f"内容不是合法数字：{e}")
        return None


if __name__ == "__main__":
    print(safe_read_number("missing.txt"))   # 文件不存在

    # 临时造两个测试文件
    with open("num.txt", "w") as f:
        f.write("3.14")
    with open("bad.txt", "w") as f:
        f.write("abc")

    print(safe_read_number("num.txt"))       # 3.14
    print(safe_read_number("bad.txt"))       # None
```

## py.exc.finally

# `try/finally`：让清理代码一定执行

> **一句话直觉**：无论 `try` 里面的代码是正常结束、抛出异常、还是提前 `return`，`finally` 里的清理动作都一定会被执行——它是 Python 中"善后"的可靠保证。

---

## 一、为什么需要 `finally`？

程序里有一类操作是"成对出现"的：打开文件要关闭、加锁要解锁、连接要断开、临时状态要恢复。

但如果中间出错、或者提前 `return`，后面的清理代码就可能被跳过。`finally` 的作用就是：**把清理逻辑放进一个永远不会被跳过的代码块里**。

语法结构：

```python
try:
    ...  # 可能出错的代码
finally:
    ...  # 无论如何都会执行的清理代码
```

关键点：`finally` 不需要 `except` 也能单独和 `try` 搭配使用。

---

## 二、`finally` 的三种触发场景

`try` 块有三种"离开方式"，`finally` 都会执行：

1. **正常结束**：`try` 块跑完，没有异常。
2. **发生异常**：异常向上抛出前，先执行 `finally`。
3. **遇到控制流语句**：`return`、`break`、`continue` 触发离开时，先执行 `finally`。

```python
def demo(flag):
    try:
        print("try: 开始")
        if flag:
            return "提前返回"        # 有 return 也不会跳过 finally
        raise ValueError("出错了")   # 抛异常也不会跳过 finally
    finally:
        print("finally: 清理完毕")

print(demo(True))
# try: 开始
# finally: 清理完毕
# 提前返回
```

注意：`return` 的值会**先计算、暂存**，然后执行 `finally`，最后才真正返回。如果 `finally` 里也有 `return`，会覆盖前面的返回值（这是坑，见"常见误区"）。

---

## 三、异常传播：`finally` 不"吃掉"异常

`finally` 和 `except` 最大的区别是：**`finally` 不捕获异常**。异常在执行完 `finally` 之后，依然会向上传播。

```python
try:
    raise RuntimeError("boom")
finally:
    print("先做清理")
# 输出: 先做清理
# 然后仍然抛出 RuntimeError 给上层
```

如果你希望既做清理、又要捕获异常，就写成 `try/except/finally`：

```python
try:
    1 / 0
except ZeroDivisionError:
    print("捕获到除零错误")
finally:
    print("无论如何都清理")
```

**工程师心法**：能用 `finally` 就说明这不是"错误处理"，而是"资源保证"。区分这两件事，代码会更清晰。

---

## 四、`finally` 的真实用途：资源生命周期

`finally` 最常见的场景就是"谁开谁关"。下面是一个文件读写的最小闭环：

```python
def read_first_line(path):
    f = open(path, "r", encoding="utf-8")
    try:
        return f.readline()
    finally:
        f.close()          # 即使 readline 抛错，文件也会被关闭
```

`with` 语句（上下文管理器）本身就是基于 `try/finally` 实现的，能替代大部分显式 `finally`。但如果某个资源没有上下文管理器（例如某些底层句柄），`try/finally` 就是必备工具。

---

## 五、一个更完整的模板

工业级代码里常见的形态是"锁 + 事务 + finally"：

```python
lock.acquire()
try:
    do_critical_work()
finally:
    lock.release()   # 死锁就出在这里被避免
```

请记住三件事：

- `finally` **一定执行**（除非进程被杀掉、`os._exit()`、或解释器崩溃）。
- `finally` **不吞异常**，只在离开时插播一段清理。
- `finally` **不要写 `return`**，会静默覆盖原返回值，是调试噩梦。

---

## 动手练习

**任务：写一个"安全的整数除法 + 资源清理"函数**

要求：
1. 函数签名 `safe_divide(a, b, log_path)`。
2. 在函数内部用 `open(log_path, "a", encoding="utf-8")` 打开一个日志文件。
3. 用 `try/finally` 保证无论如何日志文件都被关闭。
4. 在 `try` 里做 `a / b`，并把结果写入日志（形如 `"a/b = result"` 或 `"error: ..."`）。
5. 遇到 `ZeroDivisionError` 时，记录日志后返回 `None`，但**不要**用 `finally` 吞掉其他异常。

**自测用例**：

```python
print(safe_divide(10, 2, "log.txt"))   # 5.0
print(safe_divide(1, 0, "log.txt"))    # None
```

**进阶**：把 `try/finally` 改成 `with open(...) as f`，对比一下代码量，想想为什么 `with` 更推荐。

---

## 小结

| 结构 | 作用 |
| --- | --- |
| `try/except` | 处理异常 |
| `try/finally` | 保证清理 |
| `try/except/finally` | 既处理又清理 |
| `with` | `try/finally` 的语法糖（针对上下文管理器） |

记住这条工程准则：**只要资源需要成对操作，就用 `try/finally` 或 `with`，绝不要靠"代码顺序"赌它会被执行。**

```python
"""演示 py.exc.finally 的核心行为：三种离开 try 的路径都会执行 finally。"""
import os


def demo_normal():
    try:
        print("[normal] try 块执行")
    finally:
        print("[normal] finally 清理")


def demo_return():
    try:
        print("[return] 准备 return")
        return "from try"
    finally:
        print("[return] finally 仍然执行")


def demo_exception():
    try:
        print("[except] 抛出异常")
        raise ValueError("boom")
    except ValueError as e:
        print(f"[except] 捕获: {e}")
        return "handled"
    finally:
        print("[except] finally 仍然执行")


def safe_read_first_line(path: str) -> str | None:
    """用 try/finally 保证文件对象一定被关闭。"""
    if not os.path.exists(path):
        return None
    f = open(path, "r", encoding="utf-8")
    try:
        return f.readline()
    finally:
        f.close()
        print(f"[file] {path} 已关闭: {f.closed}")


if __name__ == "__main__":
    demo_normal()
    print(demo_return())
    print(demo_exception())

    # 写一个临时文件做读取测试
    tmp = "_finally_demo.txt"
    with open(tmp, "w", encoding="utf-8") as fp:
        fp.write("hello finally\n")
    print("first line:", safe_read_first_line(tmp))
    print("missing file:", safe_read_first_line("__no_such_file__"))
```


---

## 本课题目

### single_choice · None



- [A] A
  B
  C
- [B] A
  C
- [C] A
  B
- [D] B
  C

**参考答案**：0

**解析**：try 块中 print("A") 先执行，随后抛出 ValueError 被 except ValueError 捕获，打印 B；捕获处理完后继续执行后续语句打印 C。因此输出为 A、B、C 三行。

### single_choice · None



- [A] 只打印 捕获
- [B] 只打印 正常
- [C] 先打印 捕获 再打印 正常
- [D] 程序崩溃，不打印任何内容

**参考答案**：0

**解析**：发生 ZeroDivisionError 被 except 捕获，执行 except 块打印“捕获”。else 子句只在 try 块未发生异常时才执行，因此不会打印“正常”。

### single_choice · None



- [A] int("abc") 抛出 ValueError，而 except 只捕获 TypeError，因此异常未被处理
- [B] int("abc") 不抛异常，输出类型错误
- [C] except TypeError 会捕获 ValueError，输出类型错误
- [D] 把字符串转成整数不会抛出任何异常

**参考答案**：0

**解析**：int("abc") 抛出 ValueError，而 except TypeError 仅捕获 TypeError，类型不匹配导致异常未被捕获。

### single_choice · None



- [A] except (ValueError, TypeError):
- [B] except ValueError, TypeError:
- [C] except ValueError or TypeError:
- [D] except [ValueError, TypeError]:

**参考答案**：0

**解析**：Python 3 中用元组 (ValueError, TypeError) 表示捕获多种异常。except ValueError, TypeError: 是 Python 2 语法，在 Python 3 中会因语法错误无法运行。

### single_choice · None



- [A] except 块中新抛出的异常
- [B] 原来的 ValueError
- [C] 两个异常都会传播
- [D] 不会有异常传播

**参考答案**：0

**解析**：except 块中新抛出的异常会取代原异常继续向外传播（原异常作为其 __context__ 记录），最终传播的是新异常。

### single_choice · None



- [A] 打印 handled，然后重新抛出同一个 ValueError
- [B] 打印 handled，程序正常结束
- [C] 直接重新抛出 ValueError，不打印 handled
- [D] 抛出 RuntimeError

**参考答案**：0

**解析**：except 中裸 raise 会重新抛出当前正在处理的异常，即原来的 ValueError；在此之前已先打印 handled。

### single_choice · None



- [A] 1
  2
  3
- [B] 1
  2
- [C] 1
  3
- [D] 2
  3

**参考答案**：0

**解析**：先打印 1，抛出 ValueError 被 except 捕获打印 2，最后 finally 打印 3。

### single_choice · None



- [A] 第二个 except 永远不会被匹配到，因为 ValueError 是 Exception 的子类
- [B] 代码无法运行，会抛出语法错误
- [C] 两个 except 会依次都执行
- [D] ValueError 会优先匹配第二个 except

**参考答案**：0

**解析**：except 按从上到下顺序匹配，ValueError 继承自 Exception，因此会先匹配 Exception，后面的 except ValueError 永远不会被命中。

### single_choice · None



- [A] NameError，因为 except 块结束后 e 被自动删除
- [B] ValueError 的字符串表示
- [C] 空字符串
- [D] None

**参考答案**：0

**解析**：Python 3 中 except ... as e 的绑定变量在 except 块结束后会被自动删除，因此在块外访问 e 会触发 NameError。

### single_choice · None



- [A] finally
  caught
- [B] caught
  finally
- [C] finally
- [D] caught

**参考答案**：0

**解析**：先执行 except 中的 return "caught"，在函数真正返回前执行 finally 里的 print("finally")，最后返回字符串，因此先打印 finally 再打印 caught。

### single_choice · None



- [A] except ValueError as e: print(e)
- [B] except ValueError: print(ValueError)
- [C] except ValueError e: print(e)
- [D] except as ValueError: print(e)

**参考答案**：0

**解析**：except ValueError as e: print(e) 是正确语法，print(e) 会打印异常对象的描述。其他写法要么打印类本身，要么语法错误。

### single_choice · None



- [A] inner handled
  outer handled
- [B] inner handled
- [C] outer handled
- [D] 程序崩溃，无输出

**参考答案**：0

**解析**：内层 except 捕获 ValueError 并打印，随后裸 raise 重新抛出，被外层 except 捕获并打印 outer handled。

### single_choice · None



- [A] 只有当 try 块中没有发生异常时才会执行 else 块
- [B] 无论 try 块是否发生异常，else 块都会执行
- [C] 只有当 try 块发生异常时才会执行 else 块
- [D] else 块在 except 块之前执行

**参考答案**：0

**解析**：else 子句只有在 try 块顺利执行完、没有异常时才执行；若 try 里发生异常，则进入 except，else 不执行。

### single_choice · None



- [A] F
- [B] V
  F
- [C] V
- [D] 程序崩溃，无输出

**参考答案**：3

**解析**：抛出的 KeyError 与 except 的 ValueError 不匹配，异常未被处理；但 finally 仍会执行后异常继续向外传播，最终程序因未捕获的 KeyError 而终止。因此不会输出 F 或 V，最终表现为程序崩溃。

### single_choice · None



- [A] 仍然会执行
- [B] 不会执行
- [C] 只在异常未被捕获时执行
- [D] 只在 try 块无异常时执行

**参考答案**：0

**解析**：finally 块无论是否发生异常、异常是否被捕获，都会执行，常用于释放资源。

### single_choice · None



- [A] cleanup
  1
- [B] 1
  cleanup
- [C] 1
- [D] cleanup

**参考答案**：0

**解析**：return 1 会先记录下来，在真正返回前执行 finally 中的 print("cleanup")，因此先打印 cleanup，再打印函数返回值 1。

### single_choice · None



- [A] Exception
- [B] a
- [C] e
- [D] None

**参考答案**：0

**解析**：异常对象 e 的类型名通过 type(e).__name__ 获取，为 Exception。异常消息 "a" 是 e.args[0] 或 str(e)，不是类型名。

### single_choice · None



- [A] except Exception:
- [B] except:
- [C] except BaseException:
- [D] except StandardError:

**参考答案**：0

**解析**：except Exception 捕获大多数普通异常，但不会捕获 SystemExit、KeyboardInterrupt 等 BaseException 子类。裸 except 会捕获包括它们在内的所有异常；BaseException 也会捕获系统退出类异常。

### single_choice · None



- [A] 输出 try、else、finally
- [B] 输出 try、except、finally
- [C] 输出 try、except、else、finally
- [D] 输出 try、finally

**参考答案**：0

**解析**：try 块没有异常，因此不执行 except，执行 else，最后执行 finally。正确顺序为 try、else、finally。

### single_choice · None



- [A] 会，因为 finally 总会执行 close
- [B] 不会，因为异常未被 except 捕获
- [C] 不会，因为 f.close() 必须放在 except 中
- [D] 只有读取成功时才会关闭

**参考答案**：0

**解析**：无论 read() 是否抛出异常，finally 块都会执行 f.close()，从而保证文件被关闭；异常随后继续向外传播。

### single_choice · None



- [A] 一个 except 子句只能列一个异常类型，不能写成元组
- [B] except (ValueError, TypeError): 可以同时捕获这两种异常
- [C] except ValueError, TypeError: 是 Python 3 的推荐写法
- [D] 捕获多种异常必须写多个 try 语句

**参考答案**：1

**解析**：Python 3 中在一个 except 后使用异常类型元组可以捕获多种异常；逗号分隔的旧写法在 Python 3 中语法错误（那是 Python 2 写法）。多个 try 并非必需。

### single_choice · None



- [A] caught ValueError
- [B] caught TypeError
- [C] 程序崩溃并打印 traceback
- [D] 什么都不输出

**参考答案**：0

**解析**：抛出的是 ValueError，元组中匹配到 ValueError，因此捕获并输出 caught ValueError。

### multi_choice · None



- [A] 合并写法可减少重复的处理代码
- [B] 合并写法无法针对不同异常给出不同处理
- [C] 拆分写法能让每种异常的处理逻辑更清晰
- [D] 合并写法一定比拆分写法性能更好

**参考答案**：[0, 1, 2]

**解析**：合并减少重复但牺牲差异化处理，拆分更灵活可读。性能差异在绝大多数场景可忽略，选项 4“一定更好”说法不成立。

### multi_choice · None



- [A] 多种异常的处理逻辑完全一致（如都记日志并返回默认值）
- [B] 需要针对每种异常给出完全不同的用户提示
- [C] 多个异常类型都是同一业务失败的变体
- [D] 其中一个异常是 KeyboardInterrupt

**参考答案**：[0, 2]

**解析**：处理逻辑一致或同一业务变体适合合并；需要差异化处理时应拆分；KeyboardInterrupt 属 BaseException，不应与普通业务异常一起捕获。

### fill_blank · None



**参考答案**：["except", "except "]

**解析**：捕获多种异常的子句关键字是 except，后面跟异常类元组。

### fill_blank · None



**参考答案**：["(ValueError, TypeError)", "ValueError, TypeError"]

**解析**：int(None) 抛 TypeError，int('abc') 抛 ValueError，两者都需要捕获，元组写法能一次覆盖。

### fill_blank · None



**参考答案**：["KeyError"]

**解析**：两个独立 except 分别匹配不同异常，按类型一一对应，顺序上把较具体的放在前更安全。

### code_reading · None



**参考答案**：1 TypeError
3

**解析**：TypeError 匹配第一个元组子句，输出 1 TypeError；之后执行 finally，输出 3。注意第二个 except 不会执行。

### code_reading · None



**参考答案**：KeyError

**解析**：KeyError 在元组中，被捕获并返回异常类型名 KeyError。

### scenario · None



**解析**：应把预期的几种异常用元组形式在 except 中列出（如 FileNotFoundError、UnicodeDecodeError、ValueError 等），避免用 Exception 一刀切；对未预期的异常不要捕获，让其自然传播以便暴露 Bug 和保留追踪信息。

### scenario · None



**解析**：KeyboardInterrupt 和 SystemExit 继承自 BaseException 而非 Exception，把它们写进 except 元组会吞掉用户的终止信号和程序退出请求。应只在 except 中列出 Exception 或其子类（如具体的业务异常），不要捕获 BaseException 体系中的退出类异常。

### single_choice · None



- [A] Python 会自动选择最精确的异常类型，与书写顺序无关
- [B] 按书写顺序从上到下匹配，第一个匹配的子句生效
- [C] 最后一个匹配的子句生效
- [D] 必须把父类异常写在子类异常之前

**参考答案**：1

**解析**：except 子句按书写顺序依次匹配，命中第一个就执行，因此把范围大的父类异常写在前面会“吃掉”后面的子类异常。

### single_choice · None



- [A] A
- [B] B
- [C] C
- [D] 程序崩溃

**参考答案**：1

**解析**：KeyError 不匹配第一个元组，但匹配 Exception，因此输出 B。后面的 except KeyError 永远不会被到达——这正是把宽泛异常写在前面的陷阱。

### single_choice · None



- [A] 用字符串比较 str(e) 的内容
- [B] 用 isinstance(e, ValueError) 判断，或分多个 except 子句处理
- [C] 题目无法判断，只能重新抛出
- [D] 用 e.type 属性读取异常类型

**参考答案**：1

**解析**：异常对象没有 e.type 属性；判断类型应用 isinstance 或按类型拆分 except 子句。字符串比较脆弱不可靠。

### single_choice · None



- [A] SystemExit 和 KeyboardInterrupt
- [B] ValueError 和 UnicodeDecodeError
- [C] FileNotFoundError 和 PermissionError
- [D] GeneratorExit 和 Exception

**参考答案**：2

**解析**：FileNotFoundError 和 PermissionError 都是正常的业务异常，合并捕获等价。KeyboardInterrupt/SystemExit/GeneratorExit 属于 BaseException 体系，捕获它们会干扰程序正常退出，通常不应与普通异常合并捕获。

### single_choice · None



- [A] raise e
- [B] raise
- [C] raise e from None
- [D] sys.exit(1)

**参考答案**：1

**解析**：裸 raise 会保留原始 traceback；raise e 会重置 traceback 起点。raise e from None 会抑制上下文但仍是新抛出。

### single_choice · None



- [A] 输出 no
- [B] 输出 outer
- [C] 抛出 ValueError 给上层
- [D] 抛出 TypeError 给上层

**参考答案**：1

**解析**：内层 except TypeError 不匹配 ValueError，异常向外传播到外层 except ValueError，输出 outer。

### multi_choice · None



- [A] 异常类型需写成元组，如 except (A, B):
- [B] 元组中元素必须按字母顺序排列
- [C] 捕获后可用 as 绑定一个异常对象变量
- [D] 该变量在 except 块结束后会被自动删除
- [E] 元组里可以包含自定义异常类

**参考答案**：[0, 2, 3, 4]

**解析**：元组顺序无关，且不需要排序。as 绑定变量在块外被删除（Python 3 的行为），元组可包含任意异常类包括自定义类。

### multi_choice · None



- [A] except (ValueError, TypeError):
- [B] except ValueError or TypeError:
- [C] except [ValueError, TypeError]:
- [D] except (ValueError, TypeError) as e:

**参考答案**：[0, 3]

**解析**：except 后接受异常类或异常类元组。`ValueError or TypeError` 会先求真值，结果只等价于 ValueError；列表 [ValueError, TypeError] 不是合法类型，会引发 TypeError。

### single_choice · None



- [A] 无论 try 块是否抛出异常，finally 块都会执行
- [B] 只有 try 块正常结束，finally 块才执行
- [C] 只有 try 块抛出异常，finally 块才执行
- [D] finally 块只在捕获到异常时才执行

**参考答案**：0

**解析**：finally 的设计目的就是无论 try 块是正常结束、抛出异常还是被 return/break 中断，都会执行清理逻辑。其他选项都错误地把 finally 的执行与异常是否发生绑定。

### single_choice · None



- [A] A B C
- [B] A C B
- [C] A B
- [D] A C

**参考答案**：0

**解析**：先执行 try 中 print('A')，抛异常后匹配 except 打印 'B'，之后无论是否异常 finally 都会打印 'C'，所以顺序为 A B C。

### single_choice · None



- [A] 无论 process 是否抛异常，文件都会关闭
- [B] 只有 process 正常返回时文件才关闭
- [C] 只有 process 抛异常时文件才关闭
- [D] 文件不会关闭，程序退出才会释放

**参考答案**：0

**解析**：finally 保证无论 process 是否抛出异常，f.close() 都会被执行。这是经典的资源清理模式，也是 with 语句所封装的语义。

### multi_choice · None



- [A] finally 会在 try 块正常结束时执行
- [B] finally 会在 try 块抛出未捕获异常时执行
- [C] finally 会在 try 块中执行 return 或 break 时执行
- [D] finally 只在有 except 子句时才允许出现
- [E] finally 中可以使用 return，但会覆盖之前的返回值

**参考答案**：[0, 1, 2, 4]

**解析**：finally 在正常结束、异常、return/break 等情况下都会执行；它不要求必须有 except；finally 中的 return 会覆盖之前返回值。因此 D 错误。

### multi_choice · None



- [A] finally 中的 return 会丢弃正在传播的异常
- [B] finally 中的 raise 会替换掉正在传播的原异常
- [C] finally 中的 return 会覆盖 try 中的返回值
- [D] finally 中的 return 只是装饰，不影响返回值

**参考答案**：[0, 1, 2]

**解析**：finally 中的控制流语句（return/raise）会接管出口，覆盖或丢弃之前 try/except 中的返回值或异常。D 的说法错误。

### multi_choice · None



- [A] try 块中正常执行完毕
- [B] try 块中抛出异常并被 except 捕获
- [C] try 块中抛出异常且未被任何 except 捕获
- [D] try 块中执行 os._exit(0) 直接终止进程

**参考答案**：[0, 1, 2]

**解析**：正常、捕获异常、未捕获异常三种情况 finally 都会执行；但 os._exit 直接终止进程，绕过一切清理，finally 不会运行。

### fill_blank · None



**参考答案**：["body", "'body'", "\"body\""]

**解析**：先执行 try 块中的 print('body')，然后 finally 执行 print('end')，因此首先打印 body。

### fill_blank · None



**参考答案**：["20", "'20'"]

**解析**：finally 中的 return 20 会覆盖 try 中的 return 10，因此函数最终返回 20。

### code_reading · None



**参考答案**：T
F
R

**解析**：先打印 T，return 表达式求值得 'R' 并暂存，接着 finally 打印 F，最后打印返回值 R。输出为三行：T、F、R。

### code_reading · None



**参考答案**：inner
caught

**解析**：内层 try 抛 KeyError，内层 finally 先打印 inner，然后异常冒泡到外层 except 捕获并打印 caught。

### scenario · None



**解析**：经典做法是把 open 放在 try 外或 try 内，用 finally 保证 close 一定执行，无论是否抛异常。更优雅的替代是使用 with 语句（上下文管理器），它内部等价于 try/finally 的清理语义。

### scenario · None



**解析**：finally 中的 return 会覆盖 try 中的返回值，并且可能吞掉正在传播的异常，导致返回值不正确。正确做法是不要在 finally 中写 return，日志等清理逻辑只写副作用，返回留给 try/except 处理。

### single_choice · None



- [A] 1
- [B] 2
- [C] None
- [D] 抛出异常

**参考答案**：1

**解析**：finally 块中的 return 会覆盖 try 块中尚未真正返回的值，因此最终返回 2。这是一个容易被忽视的陷阱。

### single_choice · None



- [A] cleanup
  try
- [B] try
  cleanup
- [C] try
- [D] cleanup

**参考答案**：0

**解析**：return 的表达式先求值保存，finally 在真正返回前执行，因此打印顺序是 cleanup，再打印返回值 try。

### single_choice · None



- [A] 打印 done 后，ValueError 继续向外传播
- [B] 打印 done，异常被静默吞掉
- [C] 不打印 done，直接抛出 ValueError
- [D] 打印 done 后抛出 RuntimeError

**参考答案**：0

**解析**：没有 except 捕获时，finally 仍然会执行，但异常不会被吞掉，会继续向上传播。finally 只做清理，并不处理异常。

### single_choice · None



- [A] 1
- [B] 2
- [C] 3
- [D] 0

**参考答案**：2

**解析**：except 中 x 被赋为 2，finally 在 return 之前执行并把 x 改为 3，因此最终返回 3。

### single_choice · None



- [A] finally 中使用 return 会覆盖之前 try 或 except 的返回值或异常
- [B] finally 中 return 会立即报语法错误
- [C] finally 中的代码在 try 返回后不会再执行
- [D] finally 中抛出的异常会被自动忽略

**参考答案**：0

**解析**：finally 中的 return 会丢弃正在传播的异常或覆盖原返回值；同理 finally 中抛出的新异常会替换原异常。因此一般不建议在 finally 里写 return。

### single_choice · None



- [A] 1 次
- [B] 2 次
- [C] 3 次
- [D] 0 次

**参考答案**：2

**解析**：每次循环迭代结束时 finally 都会执行，包括 continue 触发的那次，因此 3 次迭代各打印一次 cleanup。

### single_choice · None



- [A] 打印一次 bye，然后退出循环
- [B] 不打印 bye，直接退出循环
- [C] 一直循环打印 bye
- [D] 抛出异常

**参考答案**：0

**解析**：break 会触发离开 try 块，finally 在真正跳出循环前执行一次，打印 bye 后循环结束。

### single_choice · None



- [A] return 表达式在到达该语句时求值，finally 在其后、真正返回前执行
- [B] return 表达式在 finally 执行之后才求值
- [C] finally 永远在 return 表达式求值之前执行
- [D] finally 中的语句会被编译器忽略

**参考答案**：0

**解析**：return 后的表达式会先求值并保存，然后执行 finally，最后才真正返回保存的值。理解这一点有助于避免 finally 修改对象造成的困惑。
