# s1u8l2 用上下文管理器优雅地管理 I/O 资源 / 路径的艺术：`pathlib` 让文件操作像说话一样自然 / py.io.os_path —— 让 Python 代码在任何操作系统上都能正确读写文件路径

> 来源 `content/lessons/s1u8l2.json`

## py.io.with

# py.io.with：用上下文管理器优雅地管理 I/O 资源

> **一句话直觉**：`with` 语句让你“用完自动收尾”——打开文件、数据库连接、锁等资源时，离开代码块会自动关闭或释放，即使中途抛异常也不例外。

---

## 1. 没有 `with` 的世界：资源泄漏的噩梦

假设你要读文件。最朴素的写法是：

```python
f = open("data.txt", "r", encoding="utf-8")
data = f.read()
f.close()
```

问题在于：**如果 `f.read()` 抛异常，`f.close()` 永远不会执行**，文件句柄（file handle）会泄漏。操作系统对每个进程能打开的文件数有限制，泄漏到一定程度程序就会崩。

有人会写 `try/finally` 来兜底：

```python
f = open("data.txt", "r", encoding="utf-8")
try:
    data = f.read()
finally:
    f.close()
```

这没错，但每个资源都这样写太啰嗦。Python 把这种模式抽象成了 **上下文管理器（context manager）**，`with` 就是它的语法糖。

---

## 2. `with` 的基本语法与执行顺序

```python
with open("data.txt", "r", encoding="utf-8") as f:
    data = f.read()
# 离开 with 块后，f 已经被自动关闭
```

等价于：

```python
f = open("data.txt", "r", encoding="utf-8")  # __enter__
try:
    data = f.read()
finally:
    f.close()                                # __exit__
```

**三个关键结论**：

1. `with EXPR as VAR` 中，`EXPR` 会调用它的 `__enter__()` 方法，返回值绑定到 `VAR`。
2. 离开代码块（正常结束或抛异常），一定调用 `__exit__()`。
3. `__exit__()` 接收异常信息 `(exc_type, exc, tb)`；返回真值可吞掉异常，返回 `None`/`False` 则异常继续向外传播。

```python
# 演示：__exit__ 一定会被调用
class Noisy:
    def __enter__(self):
        print("enter")
        return self
    def __exit__(self, exc_type, exc, tb):
        print("exit, exc =", exc_type)
        return False  # 不吞异常

try:
    with Noisy():
        print("inside")
        raise ValueError("boom")
except ValueError:
    print("caught outside")
# 输出：enter / inside / exit, exc = <class 'ValueError'> / caught outside
```

---

## 3. 一次管理多个资源

Python 3.10 起，`with` 支持括号和逗号，一次打开多个资源：

```python
with (
    open("in.txt", "r", encoding="utf-8") as fin,
    open("out.txt", "w", encoding="utf-8") as fout,
):
    for line in fin:
        fout.write(line.upper())
```

**退出顺序**：像栈一样，**后进先出（LIFO）**。上面例子里先关闭 `fout`，再关闭 `fin`。

---

## 4. 自己写一个上下文管理器

两种方式：

**方式 A：类 + `__enter__/__exit__`**（适合需要状态、复用的场景）

```python
import time

class Timer:
    def __enter__(self):
        self.start = time.perf_counter()
        return self
    def __exit__(self, exc_type, exc, tb):
        self.elapsed = time.perf_counter() - self.start
        print(f"elapsed: {self.elapsed:.4f}s")
        return False

with Timer():
    sum(range(1_000_000))
```

**方式 B：`contextlib.contextmanager`（装饰器）**（最简写法，用生成器代替两个方法）

```python
from contextlib import contextmanager

@contextmanager
def timer():
    start = time.perf_counter()
    try:
        yield                # yield 之前 = __enter__，之后 = __exit__
    finally:
        print(f"elapsed: {time.perf_counter() - start:.4f}s")

with timer():
    sum(range(1_000_000))
```

**关键约定**：`yield` 前的代码对应 `__enter__`；`yield` 抛出的值绑定给 `as`；`finally` 保证清理逻辑一定执行；若 `yield` 处捕获异常需要 `try/except`。

---

## 5. 一个实用例子：临时切换工作目录

把“进入—操作—还原”成对出现的操作封装成上下文管理器，是从“能写”到“写得好”的分水岭。

```python
import os
from contextlib import contextmanager

@contextmanager
def cd(path):
    old = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old)   # 无论出错与否都还原

with cd("/tmp"):
    print(os.getcwd())
print(os.getcwd())   # 回到原目录
```

同类的还有：`threading.Lock`、`open()`、`sqlite3.connect()`、`socket`、`tempfile.TemporaryDirectory`、`contextlib.suppress(...)` 等，Python 标准库里到处都是 `with`。

---

## 6. 与 I/O 类型的呼应

Python 的 `open()` 返回的文本流对应 `typing.TextIO`，二进制流对应 `typing.BinaryIO`，它们都实现了 `__enter__/__exit__`，所以都能安全地放进 `with`。当你写自己的 I/O 类时，**实现 `__enter__/__exit__` 是对用户的礼貌**——用户便能写成 `with MyStream(...) as s:`。

---

## 小结

| 概念 | 作用 |
|---|---|
| `with EXPR as VAR` | 自动调用 `__enter__` / `__exit__` |
| `__exit__` 返回值 | 真值吞异常，否则传播 |
| 多资源 | 用括号或逗号分隔，LIFO 退出 |
| `@contextmanager` | 用生成器快速自定义上下文管理器 |
| `finally` | 保证清理一定执行——**别把清理逻辑放在 `yield` 后面但不在 `finally` 里** |

---

## 动手练习

**任务**：实现一个上下文管理器 `atomic_write`，用于把数据安全地写入文件：先写到临时文件 `xxx.tmp`，全部写完成功后，用 `os.replace` 原子性地覆盖目标；若中途抛异常，则删除临时文件并保留原文件不变。

**要求**：
1. 使用 `contextlib.contextmanager` 实现。
2. 使用方式：
   ```python
   with atomic_write("out.txt") as f:
       f.write("hello\n")
       # f.write 抛异常时，原 out.txt 必须不变
   ```
3. 写一个测试：故意在 `with` 块里 `raise RuntimeError`，验证 `out.txt` 内容保持不变。
4. 加分：让 `atomic_write` 支持 `encoding` 参数。

**提示**：`tempfile.NamedTemporaryFile(delete=False)` 或 `tempfile.mkstemp()` 都能拿到临时路径；`os.replace(src, dst)` 在 POSIX/Windows 上都是原子替换。

```python
import os
import tempfile
from contextlib import contextmanager

@contextmanager
def atomic_write(path, encoding="utf-8"):
    """先写临时文件，成功后原子替换 path；失败则原文件不变。"""
    dir_ = os.path.dirname(os.path.abspath(path)) or "."
    fd, tmp_path = tempfile.mkstemp(dir=dir_, prefix=".tmp_", suffix=".swap")
    try:
        with os.fdopen(fd, "w", encoding=encoding) as f:
            yield f                 # 把临时文件句柄交给 with 块
        os.replace(tmp_path, path)  # 仅当 with 块正常结束时才替换
    except BaseException:
        try:
            os.unlink(tmp_path)     # 清理临时文件
        except FileNotFoundError:
            pass
        raise                       # 别吞异常

# --- 演示 ---
if __name__ == "__main__":
    target = "out.txt"
    with open(target, "w", encoding="utf-8") as f:
        f.write("ORIGINAL\n")

    # 1) 正常写入
    with atomic_write(target) as f:
        f.write("NEW CONTENT\n")
    print("after success:", open(target, encoding="utf-8").read().strip())

    # 2) 写入过程中抛异常，原文件必须不变
    try:
        with atomic_write(target) as f:
            f.write("SHOULD NOT PERSIST\n")
            raise RuntimeError("boom")
    except RuntimeError as e:
        print("caught:", e)
    print("after failure:", open(target, encoding="utf-8").read().strip())
```

## py.io.pathlib

# 路径的艺术：`pathlib` 让文件操作像说话一样自然

## 一句话直觉

在没有 `pathlib` 之前，我们只能用字符串拼接路径（例如 `"data" + "/" + "train.csv"`），既容易出错又不可读。`pathlib` 把路径变成**对象**（object），让你像操作普通数据一样调用方法，一次学会，走遍所有操作系统。

---

## 第 1 节：为什么要学 `pathlib`？

传统做法使用字符串来拼接路径（**path**），在 Windows 上分隔符是 `\`，在 Linux/macOS 上是 `/`。比如下面的写法在跨平台时就会出问题：

```python
# 传统方式：硬编码分隔符
path = "data\\train" + "/" + "file.txt"
print(path)
```

`pathlib.Path` 会自动根据当前操作系统选择正确的分隔符，你只需用 `/` 运算符即可：

```python
from pathlib import Path  # Path 是 pathlib 的核心类

p = Path("data") / "train" / "file.txt"  # 用 / 拼接路径
print(p)  # 在 Linux 上输出 data/train/file.txt，在 Windows 上输出 data\train\file.txt
```

**关键结论**：`Path` 对象比字符串更安全、更可读、更跨平台。

---

## 第 2 节：创建与解析路径

`Path` 可以从字符串、当前目录甚至用户主目录创建：

```python
from pathlib import Path

p1 = Path("data/train.csv")        # 相对路径（relative path）
p2 = Path("/etc/hosts")            # 绝对路径（absolute path）
p3 = Path.cwd()                    # 当前工作目录（current working directory）
p4 = Path.home()                   # 用户主目录

print(p1.name)      # train.csv        —— 文件名
print(p1.stem)      # train            —— 去后缀
print(p1.suffix)    # .csv             —— 后缀
print(p1.parent)    # data             —— 父目录
print(p3.is_absolute())  # True
```

**关键结论**：`Path` 把路径切成 `name`、`stem`、`suffix`、`parent` 等部分，避免手工切片字符串。

---

## 第 3 节：读写文件，一行搞定

`Path` 内置了 `read_text`、`write_text`、`read_bytes`、`write_bytes`，不必再写 `open()`/`close()`：

```python
from pathlib import Path

p = Path("demo.txt")
p.write_text("你好，pathlib！", encoding="utf-8")  # 写文件（自动关闭）
content = p.read_text(encoding="utf-8")            # 读文件
print(content)
```

二进制文件也同样简洁：

```python
p = Path("demo.bin")
p.write_bytes(b"\x00\x01\x02")
print(p.read_bytes())
```

**关键结论**：`Path` 把 `open` + `read` + `close` 合并成一次函数调用，减少样板代码（boilerplate）。

---

## 第 4 节：检查、遍历与创建

`Path` 自带存在性检查（existence check）、遍历目录（directory iteration）和创建目录（mkdir）功能：

```python
from pathlib import Path

p = Path("output")
print(p.exists())          # False（如果目录不存在）
p.mkdir(parents=True, exist_ok=True)  # 递归创建目录，已存在也不报错

# 遍历目录下的所有 .py 文件
for f in Path(".").glob("*.py"):
    print(f.name)

# 递归匹配所有子目录
for f in Path(".").rglob("*.txt"):
    print(f)

# 判断类型
p2 = Path("output")
print(p2.is_dir(), p2.is_file())
```

**关键结论**：`glob` 与 `rglob` 让你用模式匹配（pattern matching）方式遍历文件，替代 `os.walk`。

---

## 第 5 节：与 `os.path` 的互操作

旧代码可能还在使用 `os.path`，两者可以互相转换：

```python
import os
from pathlib import Path

p = Path("data/train.csv")
print(str(p))              # 转成字符串
print(p.as_posix())        # 强制使用 / 分隔（便于写入配置文件）

old_path = os.path.join("data", "train.csv")
p2 = Path(old_path)
print(p2.suffix)           # .csv
```

**关键结论**：`pathlib` 不排斥旧代码，可以平滑迁移，`str(p)` 或 `p.as_posix()` 都能拿到字符串形式。

---

## 动手练习

**任务**：在当前目录下创建 `exercise/` 文件夹，并在其中生成 `report.md`，内容为 3 行文本；随后遍历 `exercise/`，列出所有 `.md` 文件及其大小（字节数）。

```python
from pathlib import Path

base = Path("exercise")
base.mkdir(exist_ok=True)
(base / "report.md").write_text("line1\nline2\nline3\n", encoding="utf-8")

for f in base.glob("*.md"):
    print(f.name, f.stat().st_size)
```

**进阶**：把 `report.md` 读回，判断 `len(content.splitlines()) == 3` 是否成立，并打印布尔结果。

```python
from pathlib import Path

# 1. 创建目录并写文件
base = Path("exercise")
base.mkdir(parents=True, exist_ok=True)
f = base / "report.md"
f.write_text("line1\nline2\nline3\n", encoding="utf-8")

# 2. 读取并校验
content = f.read_text(encoding="utf-8")
print("lines =", len(content.splitlines()))

# 3. 遍历目录并打印文件信息
for p in base.glob("*.md"):
    print(p.name, p.stat().st_size, "bytes")
```

## py.io.os_path

# py.io.os_path —— 让 Python 代码在任何操作系统上都能正确读写文件路径

## 一句话直觉

你写的程序最终几乎都要和"文件"打交道：读配置、写日志、存数据。**`os.path` 就是 Python 内置的"路径工具箱"**，它帮你拼接、拆分、判断、归一化文件路径，并且自动适配 Windows（`C:\\Users\\...`）和 Linux/macOS（`/home/...`）两种风格，让你的代码**换一台电脑、换一个系统也能跑**。

学它，是为了避免手写 `"a" + "/" + "b"` 这种"看起来能用、换个平台就崩"的代码。

---

## 1. 路径的本质：字符串 + 规则

在 Python 里，路径不是一种特殊对象，它**首先是一个字符串（str）**。但字符串背后有"规则"：

- 分隔符（separator）：Windows 用 `\\`，Linux/macOS 用 `/`
- 当前目录（current directory）：`'.'`
- 上级目录（parent directory）：`'..'`
- 根目录（root）：Windows 是盘符 `C:\\`，类 Unix 是 `/`

`os.path` 提供了一整套函数，把这些规则**替你处理掉**。

```python
import os

# 拼接路径：自动使用当前操作系统的分隔符
path = os.path.join('data', 'images', 'cat.png')
print(path)  # Linux/macOS: data/images/cat.png
             # Windows:     data\\images\\cat.png
```

> 关键结论：**永远用 `os.path.join` 拼路径，不要手写 `'/'` 或 `'\\'`**。

---

## 2. 拆路径：把路径当"结构化数据"

一段路径其实由三块构成：**目录（dirname）+ 主干（basename）+ 扩展名（extension）**。`os.path` 把它们拆得很干净。

```python
import os

p = '/home/alice/project/report.pdf'

print(os.path.dirname(p))   # /home/alice/project    → 所在目录
print(os.path.basename(p))  # report.pdf             → 文件名
print(os.path.splitext(p))  # ('/home/alice/project/report', '.pdf')  → 拆扩展名
```

> 关键结论：**要"改扩展名"或"判断文件类型"时，先 `splitext` 再操作**，不要用字符串切片 `p[:-4]`。

---

## 3. 判断与查询：文件到底存不存在？

写文件、读文件之前，最常见的需求是"先问一句"。

```python
import os

p = 'demo.txt'

print(os.path.exists(p))  # 路径是否存在（文件或目录都算）
print(os.path.isfile(p))  # 是否是文件
print(os.path.isdir(p))   # 是否是目录
print(os.path.getsize(p)) # 如果存在，文件大小（字节）
```

注意 `os.path.getsize` 在文件不存在时会直接抛 `FileNotFoundError`——所以**先 `exists`，再 `getsize`**。

---

## 4. 归一化与绝对化：让路径"说话清楚"

路径里可能有 `..`、`.`、多余的斜杠，甚至相对当前工作目录。`os.path` 提供两个"整理函数"。

```python
import os

# normalize：把 a/./b/../c 压成 a/c
print(os.path.normpath('a/./b/../c'))     # a/c

# absolute / abspath：补全成绝对路径
print(os.path.abspath('demo.txt'))        # /当前工作目录/demo.txt
print(os.path.abspath('..'))              # 当前目录的上一级
```

> 关键结论：**日志、缓存、配置里的路径统一用 `os.path.abspath` 处理后再存**，否则换个目录运行程序就找不到文件。

---

## 5. 工程级套路：`__file__` + `os.path` 定位资源

真实项目里，脚本和它依赖的资源（模板、图片、CSV）通常放在一起。但 `'./templates/x.html'` 这种写法依赖"你在哪个目录启动脚本"，非常脆弱。**工程级写法**是用 `__file__` 锚定脚本自身位置：

```python
import os

# 当前 .py 文件所在目录
HERE = os.path.dirname(os.path.abspath(__file__))
# 相对它定位资源
CONFIG = os.path.join(HERE, 'config', 'settings.json')
```

这行 `os.path.dirname(os.path.abspath(__file__))` 几乎是每个 Python 工程师的肌肉记忆，**无论从哪个目录运行脚本，`CONFIG` 都指向正确位置**。

> 补充：Python 3.4+ 还提供了面向对象（object-oriented）的替代品 `pathlib.Path`，写起来更优雅。但 `os.path` 依然是标准库最底层、最通用的接口，读别人的老代码、写工具脚本时都离不开它。

---

## 动手练习

**任务**：写一个 Python 脚本 `project_info.py`，放在任意目录，要求：

1. 打印**脚本自身的绝对路径**；
2. 打印脚本所在目录下的一个虚构文件 `data/raw/input.csv` 的完整路径（用 `os.path.join` 拼出来）；
3. 打印该虚构文件的**文件名**和**扩展名**；
4. 判断该文件是否**真实存在**，并打印结果；
5. 在脚本同级目录下创建一个空的 `notes` 文件夹（用 `os.makedirs(..., exist_ok=True)`），再判断它是否是目录。

**验收标准**：从任意目录 `cd` 过去运行 `python project_info.py`，输出的第 2 行路径都指向 `project_info.py` 所在目录，而不是你启动命令的目录。

**提示**：核心就是这一行——
```python
HERE = os.path.dirname(os.path.abspath(__file__))
```


---

## 本课题目

### single_choice · None



- [A] False
- [B] True
- [C] None
- [D] 报错，因为 f 在 with 外不可访问

**参考答案**：1

**解析**：with 语句块结束时（无论是正常结束还是异常）都会调用上下文管理器的 __exit__，文件会被自动关闭。变量 f 在 with 外仍然可访问，只是文件已关闭，因此 f.closed 为 True。

### single_choice · None



- [A] 只有文件对象可以作为 with 的对象
- [B] with 块内发生异常时不会调用上下文管理器的退出方法
- [C] 实现 __enter__ 和 __exit__ 的对象都可以配合 with 使用
- [D] with 语句不能同时管理多个资源

**参考答案**：2

**解析**：with 依赖上下文管理协议：对象需实现 __enter__ 和 __exit__。文件只是常见的例子，任何实现了该协议的对象都可以用。即使块内发生异常，__exit__ 也会被调用。一个 with 也可以管理多个资源。

### single_choice · None



- [A] 可以自动捕获所有异常并忽略
- [B] 可以减少忘记释放资源导致的泄漏，代码更简洁清晰
- [C] 可以提升文件读写速度
- [D] 可以让资源在块内不被关闭

**参考答案**：1

**解析**：with 封装了 try/finally 的释放逻辑，降低遗漏释放资源（如忘记 close）造成的泄漏风险，同时让代码更简洁。with 并不负责吞掉异常，也不会提升 I/O 速度。

### single_choice · None



- [A] f.write 后内容不会写入磁盘，因为未调用 flush
- [B] with 退出时文件会关闭，关闭前会刷新缓冲区，内容已写入
- [C] with 退出不会关闭文件，还需要手动 close
- [D] 只有在 with 内调用 f.close() 才会关闭文件

**参考答案**：1

**解析**：文件对象在关闭时会刷新缓冲区并释放系统资源。with 退出触发 __exit__ 调用 close，因此内容会写入。with 的目的就是自动关闭，不需要手动 close。

### single_choice · None



- [A] KeyError 被抑制，__exit__ 内的异常作为新异常抛出
- [B] KeyError 继续传播，__exit__ 内的异常替换 KeyError 抛出
- [C] 两个异常同时抛出，程序捕获到元组
- [D] KeyError 被忽略，程序正常继续

**参考答案**：1

**解析**：当 __exit__ 自身抛出异常时，它会替换原先正在传播的异常（原异常会被链式保存在 __context__ 中）。返回 False 表示不抑制原异常，但 __exit__ 内部异常会中止退出流程，最终看到的是 __exit__ 抛出的异常。

### single_choice · None



- [A] __exit__ 仍会被调用一次
- [B] with 块不会执行，异常直接传播
- [C] 对象会被自动销毁，异常被忽略
- [D] __enter__ 的异常会被转换成 RuntimeError

**参考答案**：1

**解析**：只有 __enter__ 成功返回后才会执行 with 块，之后退出时才调用 __exit__。如果 __enter__ 自身抛出异常，块体和 __exit__ 都不会执行，异常直接向外传播。

### single_choice · None



- [A] enter
  body
  exit
- [B] body
  enter
  exit
- [C] enter
  exit
  body
- [D] body
  exit
  enter

**参考答案**：0

**解析**：执行顺序为先调用 __enter__（打印 enter），再执行块体（打印 body），最后调用 __exit__（打印 exit）。所以顺序是 enter、body、exit。

### single_choice · None



- [A] return 会跳过 __exit__，文件不会关闭
- [B] return 执行前会先触发 with 的退出，文件被关闭后再返回
- [C] return 后文件保持打开，需在函数外关闭
- [D] return 会导致 with 报错

**参考答案**：1

**解析**：无论块内是正常结束、return、break、continue 还是抛出异常，with 都会执行 __exit__ 进行清理。return 会先计算返回值表达式，再退出 with（关闭文件），最后返回。

### single_choice · None



- [A] 只要使用了 with，所有异常都会被抑制
- [B] 只有 IOError 会被抑制
- [C] 当 __exit__ 返回假值时，块内异常会传播到块外
- [D] 只有 SystemExit 会被抑制

**参考答案**：2

**解析**：是否抑制块内异常取决于 __exit__ 的返回值：返回真值则抑制，返回假值（None、False 等）则异常继续传播。with 本身并不自动吞掉异常。

### single_choice · None



- [A] 打开的文件对象
- [B] threading.Lock 实例
- [C] 普通整数 5
- [D] 自定义实现了 __enter__ 和 __exit__ 的实例

**参考答案**：2

**解析**：整数没有实现上下文管理器协议，不能直接用于 with。文件对象、Lock 以及自定义实现了协议的对象都可以。

### single_choice · None



- [A] 如果 f.read() 抛出异常，文件不会被关闭
- [B] 如果 f.read() 抛出异常，__exit__ 仍会被调用，文件会被关闭，异常继续传播
- [C] 如果 f.read() 抛出异常，with 会把它转换成 IOError
- [D] 如果 f.read() 抛出异常，必须手动调用 f.close()

**参考答案**：1

**解析**：with 保证无论块内是否发生异常，都会调用 __exit__ 来释放资源。文件对象的 __exit__ 会关闭文件且不抑制异常，因此异常在清理后继续向外传播。

### single_choice · None



- [A] with open('a.txt') as f
- [B] with open('a.txt') as f:
- [C] with (open('a.txt') as f):
- [D] with as open('a.txt') f:

**参考答案**：1

**解析**：with 语句必须以冒号结尾并带缩进块，正确形式为 with 表达式 as 变量:。选项 A 缺冒号；C 括号位置错误；D 顺序错误。

### single_choice · None



- [A] 在 print('inside') 之前
- [B] 在 print('inside') 执行之后、print('outside') 之前
- [C] 在 print('outside') 之后
- [D] 在程序退出时由垃圾回收统一关闭

**参考答案**：1

**解析**：with 语句块结束时自动调用 __exit__，文件随即关闭。因此关闭发生在块内语句之后、块外语句之前，而不是等程序结束或垃圾回收。

### single_choice · None



- [A] 只定义 __init__ 和 __del__
- [B] 定义 __enter__ 和 __exit__
- [C] 定义 open 和 close
- [D] 定义 __with__ 和 __end__

**参考答案**：1

**解析**：with 使用上下文管理器协议，要求类型实现 __enter__ 和 __exit__。__del__ 是析构相关，open/close 是文件对象的普通方法，__with__/__end__ 不存在。

### single_choice · None



- [A] ValueError 会继续向外传播，print('after') 不执行
- [B] ValueError 被抑制，print('after') 会执行
- [C] 无论返回什么，with 块内异常都会被抑制
- [D] 无论返回什么，with 块内异常都会继续传播

**参考答案**：1

**解析**：__exit__ 返回真值时表示异常已被处理，异常不会继续向外传播；返回假值（如 None/False）则异常继续抛出。因此返回 True 时 print('after') 会执行。

### single_choice · None



- [A] 进入 with 块，f 为 None，data 为 None
- [B] 不会进入 with 块，异常直接向外传播，__exit__ 不会被调用
- [C] 进入 with 块，读取时才报错
- [D] 异常被 with 自动忽略

**参考答案**：1

**解析**：with 先求值上下文表达式（这里是 open(...)）并调用 __enter__，只有成功后才执行块体。如果 open 本身失败，with 块不会执行，也不存在已获得的上下文管理器来调用 __exit__，异常直接传播。

### single_choice · None



- [A] 绑定的值一定是上下文管理器对象本身
- [B] 绑定的值是 __enter__ 方法的返回值
- [C] 绑定的值是 __exit__ 方法的返回值
- [D] as 子句只能绑定文件名

**参考答案**：1

**解析**：with ... as x 中，x 接收的是 __enter__ 的返回值，不一定是上下文管理器对象本身。对文件对象来说 __enter__ 返回自身，但对许多上下文管理器会返回别的对象。

### single_choice · None



- [A] 打印 Ctx 对象
- [B] 打印 42
- [C] 打印 None
- [D] 报错，因为 as 不能绑定整数

**参考答案**：1

**解析**：as 绑定的是 __enter__ 的返回值，这里返回 42，因此 v 为 42。as 可以绑定任意对象，不限于上下文管理器。

### single_choice · None



- [A] with open('a.txt') as f, open('b.txt') as g:
- [B] with open('a.txt') and open('b.txt') as f, g:
- [C] with open('a.txt'), open('b.txt') as f, g:
- [D] with open('a.txt') as f as g:

**参考答案**：0

**解析**：Python 支持在一个 with 语句中用逗号分隔多个上下文管理器：with A as a, B as b:。其余写法语法错误或语义错误。

### single_choice · None



- [A] 内层 with 的退出发生在外层 with 退出之后
- [B] 外层 with 先退出，然后内层 with 再退出
- [C] 内外层 with 同时退出
- [D] 嵌套 with 无法正确关闭资源

**参考答案**：0

**解析**：with 的进出遵循栈结构：外层先进入，内层后进入；退出时内层先退出（后进先出），外层后退出。这样能保证资源按相反顺序释放。

### single_choice · None



- [A] Path 对象把路径拆成若干字符串片段，使用时必须手动拼接，才可以传给 open 等函数
- [B] Path 对象是面向对象的路径表示，自带与路径相关的方法（如名称、父目录、拼接），并且可以直接被 open 等接受路径参数的函数使用
- [C] Path 对象是文件内容的容器，可以直接读取和写入文件内容，因此不再需要 open
- [D] Path 对象只能表示目录，不能表示文件，表示文件必须用字符串

**参考答案**：1

**解析**：pathlib.Path 是面向对象的路径表示，封装了路径的多种操作，同时它实现了 os.PathLike 协议，可直接传给 open 等接受路径的函数。它不负责文件内容管理（读写仍由 open 完成），也不仅限于目录。Option 1 把路径方法说成必须手动拼接字符串，忽略了 Path 的方法与运算符；Option 3 混淆了路径对象与文件对象；Option 4 错误地限制了 Path 的适用范围。

### single_choice · None



- [A] Path('data/report.txt')
- [B] Path.join('data', 'report.txt')
- [C] Path.new('data/report.txt')
- [D] Path.from_string('data/report.txt')

**参考答案**：0

**解析**：pathlib.Path 的推荐用法是直接调用构造器传入字符串或若干路径片段：Path('data/report.txt')，也支持 Path('data', 'report.txt')。Path.join、Path.new、Path.from_string 都不是 pathlib 的公开 API，属于虚构方法。

### single_choice · None



- [A] PurePath 只做纯路径计算、不做 I/O，Path 继承自 PurePath 并增加了 I/O 相关方法
- [B] PurePath 可以读写文件，Path 只能做纯路径计算
- [C] PurePath 与 Path 完全等价，只是名字不同
- [D] PurePath 仅用于 Windows 路径，Path 仅用于 POSIX 路径

**参考答案**：0

**解析**：PurePath 提供不依赖文件系统的路径操作（如拼接、取 name/suffix），不会执行 I/O；Path 继承自 PurePath，并增加了 exists、read_text、mkdir 等涉及文件系统 I/O 的方法。二者并非等价，也不是按平台划分。

### multi_choice · None



- [A] Path 对象可以在需要文件系统路径的参数里替代字符串使用，例如传给 open
- [B] Path 的 / 运算符可以用于拼接路径片段
- [C] Path 对象是不可变的，对其调用拼接或 resolve 等方法会返回新的 Path 对象，而不修改原对象
- [D] Path.resolve() 会返回解析后的绝对路径，并消除 . 与 .. 以及符号链接
- [E] Path 对象一旦创建就会锁定对应的文件内容，阻止其他进程修改

**参考答案**：[0, 1, 2, 3]

**解析**：Path 实现了 os.PathLike，可替代字符串传参；/ 运算符用于拼接；Path 对象不可变，相关方法返回新对象；resolve() 解析为绝对路径并处理 .、.. 和符号链接。Path 不锁定文件内容，那属于文件锁机制，与 Path 无关。

### multi_choice · None



- [A] 使用 Path('dir').rglob('*.txt') 得到匹配的 Path 对象
- [B] 使用 Path('dir').glob('**/*.txt') 也可以实现递归匹配
- [C] 使用 Path('dir').iterdir() 只能遍历直接子项，不能直接完成递归匹配
- [D] Path.glob 和 Path.rglob 的匹配模式遵循 fnmatch 风格的语法，* 不跨越目录分隔符，** 才跨越

**参考答案**：[0, 1, 2, 3]

**解析**：rglob('*.txt') 等价于在模式前加 '**/'；glob('**/*.txt') 也能递归匹配；iterdir() 只产出直接子项；glob 使用 fnmatch 风格，* 不跨目录、** 才跨目录。四种说法都正确。

### multi_choice · None



- [A] 可以给 write_text() 传入 encoding 参数来指定写入时使用的编码
- [B] read_text() 可以传入 encoding 参数来指定解码方式
- [C] 如果不显式指定 encoding，则使用平台相关的默认编码，可能导致跨平台读取不一致
- [D] write_text() 的 newline 参数可以控制换行符的转换方式

**参考答案**：[0, 1, 2, 3]

**解析**：Path.write_text() 和 read_text() 都接受 encoding；不指定时使用平台默认编码，跨平台时可能不一致；write_text() 也接受 newline 参数来影响换行处理。四项都成立。

### fill_blank · None



**参考答案**：["is_dir", "is_dir()"]

**解析**：Path.is_dir() 用来判断路径是否指向一个存在的目录，返回布尔值。is_file() 判断文件，exists() 只判断存在。

### fill_blank · None



**参考答案**：["rglob", "rglob()"]

**解析**：Path.rglob(pattern) 会递归地在子目录中匹配，等价于在模式前加 '**/'。若使用 glob('*.py') 则只匹配直接子项，不能递归。

### fill_blank · None



**参考答案**：["stem"]

**解析**：Path.stem 返回去掉最后一个后缀后的文件名，这里得到 'summary'。suffix 返回后缀 '.txt'，name 返回完整文件名。

### code_reading · None



**参考答案**：依次输出：c.txt、.txt、/a/b

**解析**：Path.name 返回路径最后一部分 'c.txt'；Path.suffix 返回最后一个后缀且含点 '.txt'；Path.parent 返回上一级目录的 Path，其字符串形式为 '/a/b'。

### code_reading · None



**参考答案**：输出依次为：/home/user/docs/a.txt、PosixPath（在 Windows 上为 WindowsPath）、('/', 'home', 'user', 'docs', 'a.txt')

**解析**：/ 运算符把 Path 与字符串拼接成新的 Path 对象；打印 Path 会得到其字符串形式；parts 返回各组成部分的元组，根目录 '/' 也是其中一部分。type 名称在 POSIX 平台上为 PosixPath，Windows 上为 WindowsPath。

### scenario · None



**解析**：推荐流程：用 Path(project_dir) 表示项目根目录；用 rglob('*.py') 递归获取所有 Python 文件的 Path 对象；对每个文件调用 read_text()（必要时指定 encoding）读取文本，判断是否包含 'TODO'，并计数。使用 rglob 可跨子目录匹配，Path/read_text 是跨平台且面向对象的路径与读取方式，避免手动拼接字符串。

### single_choice · None



- [A] 字符串 '/home/user/docs/file.txt'
- [B] 一个 Path 对象，其字符串形式为 '/home/user/docs/file.txt'
- [C] 一个包含三个元素的列表 ['/home/user', 'docs', 'file.txt']
- [D] 一个 Path 对象，但因为使用了 / 运算符而抛出 TypeError

**参考答案**：1

**解析**：Path 重载了 / 运算符用于拼接路径，因此结果是 Path 对象，其字符串表示为 '/home/user/docs/file.txt'。它不会自动转成字符串，也不会变成列表。当参与拼接的操作数之一是 Path 时，/ 运算符是被支持的，不会报错。

### scenario · None



**解析**：应使用 Path('output/2024/logs').mkdir(parents=True, exist_ok=True)。parents=True 会在父目录缺失时递归创建，避免因中间目录不存在而失败；exist_ok=True 使得目标目录已存在时不抛 FileExistsError。两者组合能同时应对父目录缺失与目录已存在两种情况。

### single_choice · None



- [A] parts 返回路径各组成部分的元组，name 返回最后一部分，suffix 返回最后一个后缀（含点）
- [B] parts 返回路径各组成部分的列表，name 返回最后一部分，suffix 返回最后一个后缀（不含点）
- [C] parts 返回路径各组成部分的元组，name 返回第一个部分，suffix 返回整个文件名
- [D] parts 返回路径各组成部分的集合，name 返回最后一个部分，suffix 返回所有后缀的列表

**参考答案**：0

**解析**：在 pathlib 中，Path.parts 返回路径各段的元组；Path.name 返回路径最后的组件名；Path.suffix 返回最后一个后缀，并且包含点号（如 '.txt'）。name 返回的是最后一部分而不是第一部分；suffix 不是整个文件名；parts 也不是集合。

### single_choice · None



- [A] os.path.join('a', 'b') 返回字符串，而 Path('a') / 'b' 返回 Path 对象，并且两者结果都表示同一路径 'a/b'
- [B] os.path.join 只能接受两个参数，因此无法拼接三段以上路径
- [C] Path('a') / 'b' 会修改原始 Path 对象，使之变成 'a/b'
- [D] os.path.join 会自动创建目录，而 Path 的拼接不会

**参考答案**：0

**解析**：os.path.join 以字符串形式返回拼接结果，Path 的 / 运算符返回 Path 对象，这是两者的典型区别，且二者都表示同一路径。os.path.join 可接受任意个参数；Path 的 / 运算符返回新对象，不会改动原对象；os.path.join 也不会创建目录。

### single_choice · None



- [A] Path.exists() 判断存在，Path.is_file() 判断文件，Path.is_dir() 判断目录
- [B] Path.check() 判断存在，Path.file() 判断文件，Path.directory() 判断目录
- [C] Path.exists 是布尔属性，Path.is_file 也是布尔属性，Path.is_dir 也是布尔属性
- [D] 判断文件只能用 os.path.isfile，pathlib 不提供判断文件类型的方法

**参考答案**：0

**解析**：pathlib 提供 exists()、is_file()、is_dir() 等方法来判断路径状态。它们是方法调用而不是属性，也不叫 check、file、directory。pathlib 本身就提供了判断文件类型的方法，不需要回退到 os.path。

### single_choice · None



- [A] parents=True 会递归创建缺失的父目录，exist_ok=True 使得目录已存在时不抛 FileExistsError
- [B] parents=True 会递归创建缺失的父目录，exist_ok=True 使得目录已存在时返回 False 而不抛异常
- [C] parents=True 会返回父目录的 Path 对象，exist_ok=True 会自动删除已存在的目录再重建
- [D] 两个参数都只对文件有效，用于创建文件而不是目录

**参考答案**：0

**解析**：Path.mkdir(parents=True, exist_ok=True) 是常见的组合：parents=True 递归创建父目录，exist_ok=True 让目录已存在时不抛 FileExistsError。exist_ok=True 并不改变返回值语义；parents 不返回父目录对象；这两个参数是用于目录创建的。

### single_choice · None



- [A] read_text() 返回字符串，write_text() 写入字符串并返回写入的字符数
- [B] read_text() 返回字节，write_text() 只能写入字节
- [C] read_text() 返回字符串，write_text() 返回写入的字符数，所以二者必须成对使用且不能与 open 混用
- [D] read_text() 与 write_text() 都会自动创建不存在的父目录

**参考答案**：0

**解析**：Path.read_text() 以文本模式读取整个文件并返回字符串；Path.write_text() 写入字符串，并返回写入的字符数。read_bytes()/write_bytes() 才处理字节。read_text/write_text 可以与 open 混用，它们只是便捷方法，不会自动创建父目录。

### single_choice · None



- [A] 返回一个生成器，逐个产出该目录下直接子项的 Path 对象；不能递归子目录
- [B] 返回一个列表，包含该目录下所有层级的 Path 对象；可以递归子目录
- [C] 返回一个字符串，列出目录内容；不能递归子目录
- [D] 返回一个生成器，产出的是文件名字符串；可以递归子目录

**参考答案**：0

**解析**：Path.iterdir() 返回一个生成器，逐个产出目录下直接子项的 Path 对象，不递归子目录。若要递归遍历，应使用 Path.rglob() 或 os.walk。选项把返回类型说成列表、字符串或产出字符串都是错误的。

### single_choice · None



- [A] 'c' 与 '.gz'
- [B] 'c.txt' 与 '.tar.gz'
- [C] 'c' 与 '.tar'
- [D] 'c' 与 '.gz'，且 stem 等于去掉所有后缀后的文件名

**参考答案**：0

**解析**：Path.stem 返回去掉最后一个后缀后的文件名，Path('a/b/c.txt').stem 为 'c'；Path.suffix 返回最后一个后缀且含点，Path('a/b/c.tar.gz').suffix 为 '.gz'。要获取全部后缀应使用 suffixes，要获取去掉全部后缀的名字可借助 name 与 suffixes 组合处理。

### single_choice · None



- [A] 它会自动检查路径是否存在，不存在则抛异常
- [B] 它会用当前操作系统的路径分隔符把多个字符串拼接成一个路径
- [C] 它只能接受两个参数
- [D] 它会把所有参数中的分隔符规范化为正斜杠 '/'

**参考答案**：1

**解析**：os.path.join 的职责是按当前平台的路径分隔符（如 Windows 用 '\\'，类 Unix 用 '/'）把片段拼接起来，它不做存在性检查，也不做分隔符规范化，且可接受任意多个参数。

### single_choice · None



- [A] a/b/c
- [B] a//b/c
- [C] /b/c
- [D] a/b/c 或 a\\b\\c，取决于平台

**参考答案**：2

**解析**：当 join 遇到以分隔符开头的绝对路径片段时，会丢弃它之前的所有片段，从该绝对片段重新开始，因此结果是 '/b/c'。

### multi_choice · None



- [A] os.path.exists('x')
- [B] os.path.join('a', 'b')
- [C] os.path.isfile('x')
- [D] os.path.splitext('a.txt')
- [E] os.path.getsize('x')

**参考答案**：[0, 2, 4]

**解析**：exists、isfile、getsize 都需要查询文件系统状态；join、splitext 只是字符串操作，不访问磁盘。

### multi_choice · None



- [A] 参数可以超过两个
- [B] 任意一个参数为 '' 不会影响结果
- [C] 遇到以分隔符开头的绝对路径片段会重置拼接
- [D] 它会自动创建不存在的目录
- [E] 它会检查每个片段是否存在

**参考答案**：[0, 1, 2]

**解析**：join 支持任意参数数量；空字符串不产生额外分隔符；绝对路径片段会重置。它既不创建目录也不做存在性检查。

### multi_choice · None



- [A] '/home/user'
- [B] './data'
- [C] '~/data'
- [D] '/tmp'

**参考答案**：[0, 3]

**解析**：'/home/user' 与 '/tmp' 以 '/' 开头属于绝对路径；'./data' 是相对路径；'~/data' 中的 '~' 由 shell 展开，os.path.isabs 不认它。

### multi_choice · None



- [A] 对 'a/b.txt' 返回 ('a/b', '.txt')
- [B] 对 '.bashrc' 返回 ('.bashrc', '')
- [C] 对 'a.tar.gz' 返回 ('a.tar', '.gz')
- [D] 对 'a' 返回 ('a', '')

**参考答案**：[0, 2, 3]

**解析**：splitext 只按最后一个点拆分。以点开头的隐藏文件 '.bashrc' 整体被视为文件名、扩展名为空（返回 ('.bashrc', '')），这是常见误区，所以选项 B 表述错误。

### fill_blank · None



**参考答案**：["usr/local/bin", "usr\\local\\bin"]

**解析**：join 使用当前平台分隔符拼接，类 Unix 下为 'usr/local/bin'，Windows 下为 'usr\\local\\bin'，两种写法均可接受。

### fill_blank · None



**参考答案**：["/a/b"]

**解析**：dirname 返回最后一个分隔符之前的目录部分 '/a/b'，不带尾部分隔符。

### fill_blank · None



**参考答案**：[".txt"]

**解析**：splitext 取文件名中最后一个点后的部分作为扩展名，结果为 '.txt'，与平台与盘符无关。

### code_reading · None



**参考答案**：第一行输出 'data/raw/input.csv'（Windows 上为 'data\\raw\\input.csv'），第二行输出 'input.csv'。

**解析**：join 拼接三个片段得到相对路径，basename 再取出最后的名字部分 'input.csv'。

### scenario · None



**解析**：应使用 os.path.join 而不是字符串相加：join 能自动适配不同平台的分隔符，并在遇到绝对路径片段时按规范重置前缀，避免 '+' 拼接导致的重复分隔符、跨平台不兼容以及绝对路径语义被破坏等问题。

### single_choice · None



- [A] C:\\Users/name
- [B] C:\\Users\
  ame
- [C] C:\\Usersname
- [D] name

**参考答案**：1

**解析**：Windows 上 join 使用 '\\' 作为分隔符，且第一个片段已是绝对路径，因此拼接为 'C:\\Users\\name'，不会混用正斜杠。

### single_choice · None



- [A] ('/home/user', 'data.txt')
- [B] ('/home/user/', 'data.txt')
- [C] ('/home', 'user/data.txt')
- [D] ('data.txt', '/home/user')

**参考答案**：0

**解析**：os.path.split 按最后一个路径分隔符拆成 (目录, 文件名) 二元组，目录部分不含尾部分隔符，因此是 ('/home/user', 'data.txt')。

### single_choice · None



- [A] '.tar.gz'
- [B] '.gz'
- [C] 'tar.gz'
- [D] ''

**参考答案**：1

**解析**：splitext 只按最后一个点拆分，返回 ('archive.tar', '.gz')，扩展名是 '.gz'。

### single_choice · None



- [A] os.path.exists(path)
- [B] os.path.isdir(path)
- [C] os.path.isfile(path)
- [D] os.path.islink(path)

**参考答案**：1

**解析**：os.path.isdir 专门判断路径是否为目录（且存在才算 True）；exists 只判断存在性，isfile 判断文件，islink 判断符号链接。

### single_choice · None



- [A] 原样返回 './data/../file.txt'
- [B] 返回以当前工作目录为基准的绝对路径，但不一定消除 '..'
- [C] 一定会消除 '..' 并返回 '/cwd/file.txt'
- [D] 抛出 FileNotFoundError

**参考答案**：1

**解析**：abspath 基于当前工作目录把相对路径转成绝对路径，但它只是字符串拼接加规范，不做文件系统访问，也不保证完全解析 '..' 语义；要彻底化简用 realpath。

### single_choice · None



- [A] 'bin'
- [B] ''
- [C] '/usr/local/bin'
- [D] 抛异常

**参考答案**：1

**解析**：当路径以分隔符结尾时，basename 返回空字符串，因为最后一个分隔符后没有名称部分。这是常见边界情况。

### single_choice · None



- [A] 两者完全相同
- [B] exists 对悬空符号链接返回 False，lexists 对悬空符号链接返回 True
- [C] exists 对悬空符号链接返回 True，lexists 返回 False
- [D] lexists 只用于 Windows

**参考答案**：1

**解析**：exists 会跟随符号链接，若链接指向的目标不存在则返回 False；lexists 不跟随链接，只看链接本身是否存在，故悬空链接返回 True。

### single_choice · None



- [A] 'a/b/../c'
- [B] 'a/c'
- [C] 'c'
- [D] 'a/b/c'

**参考答案**：1

**解析**：normpath 会折叠 '.' 与多余的 '..' 以及重复分隔符（在合理范围内），把 'a/b/../c' 规范化为 'a/c'。
