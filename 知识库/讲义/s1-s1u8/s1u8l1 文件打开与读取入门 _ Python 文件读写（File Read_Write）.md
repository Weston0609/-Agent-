# s1u8l1 文件打开与读取入门 / Python 文件读写（File Read/Write）

> 来源 `content/lessons/s1u8l1.json`

## py.io.file_open

# py.io.file_open：文件打开与读取入门

> **一句话直觉**：程序运行时的数据一旦断电就消失，`open()` 让我们能把数据写到磁盘上的文件里、也能从磁盘文件里读回来——这是任何程序与“外部世界”交换数据的起点。

---

## 1. 为什么需要打开文件？

变量（variable）保存在内存（memory）中，程序一结束就消失。文件（file）保存在磁盘（disk）上，可以长期保留。Python 提供内置函数（built-in function）`open()` 来在程序与磁盘文件之间建立一条数据通道，这个通道叫做**文件对象**（file object，也叫文件句柄 file handle）。

```python
# 最简用法：打开一个文件进行写入
f = open("hello.txt", "w")   # "w" 表示 write 模式
f.write("你好，世界\n")        # 写入字符串
f.close()                     # 必须关闭，释放资源
```

**关键结论**：`open()` 返回一个文件对象；用完必须 `close()`，否则数据可能没写盘、文件句柄会泄漏。

---

## 2. 四种常用打开模式

| 模式 | 含义 | 文件不存在时 | 是否清空原内容 |
|------|------|--------------|----------------|
| `"r"` | 只读 read（默认） | 报错 `FileNotFoundError` | — |
| `"w"` | 只写 write | 新建 | 是 |
| `"a"` | 追加 append | 新建 | 否（在末尾追加） |
| `"x"` | 独占创建 exclusive | 报错 | — |

再加后缀 `b` 表示二进制（binary）模式，例如 `"rb"`、`"wb"`。

```python
# 追加模式：不覆盖原内容
with open("log.txt", "a", encoding="utf-8") as f:
    f.write("新的一行日志\n")
```

**关键结论**：默认模式是 `"r"` 文本模式；写文件时 `"w"` 会清空，`"a"` 会追加，要谨慎选择。

---

## 3. 用 `with` 自动关文件（推荐写法）

手动 `close()` 容易漏写。`with` 语句（context manager，上下文管理器）会在代码块结束时**自动关闭**文件，即使中途抛异常也会关。

```python
# 推荐写法：with 自动调用 close()
with open("hello.txt", "w", encoding="utf-8") as f:
    f.write("hello\n")
# 走出了 with 块，f 已经自动关闭
print(f.closed)   # True
```

**关键结论**：工程代码一律用 `with open(...) as f:`，不要手动 `close()`。

---

## 4. 读取内容的三种方式

- `f.read()`：一次性读全部（小文件可以，大文件会吃满内存）
- `f.readline()`：读一行
- `for line in f:`：逐行迭代，最省内存（推荐）

```python
# 逐行读取：内存友好，工程首选
with open("hello.txt", "r", encoding="utf-8") as f:
    for line in f:
        print(line.rstrip("\n"))   # rstrip 去掉行尾换行符
```

**关键结论**：处理大文件用 `for line in f`，而不是 `f.read()`。

---

## 5. 编码与二进制：不要忽略 `encoding`

文本模式（text mode）下，Python 需要在字节与字符间转换，这个规则叫**编码**（encoding）。跨平台时默认编码不同（Windows 常见 `gbk`，Linux/macOS 常见 `utf-8`），容易踩坑，所以**永远显式写出 `encoding="utf-8"`**。

如果需要读写图片、音频、压缩包等非文本数据，用二进制模式（binary mode），此时不需要 `encoding`。

```python
# 文本模式：显式指定编码
with open("data.txt", "w", encoding="utf-8") as f:
    f.write("中文不会乱码\n")

# 二进制模式：按字节读写，无 encoding 参数
with open("img.bin", "wb") as f:
    f.write(b"\x00\x01\x02")
```

**关键结论**：文本文件永远写 `encoding="utf-8"`；二进制数据用 `"rb"`/`"wb"`，不要传 `encoding`。

---

### 小结

1. `open(path, mode, encoding=...)` 建立文件对象；
2. 模式决定读/写/追加/二进制；
3. 用 `with` 自动关闭；
4. 读文件优先 `for line in f`；
5. 文本文件一定写 `encoding="utf-8"`。

掌握这五点，你就已经能安全地在本地读写绝大多数文件了。

```python
# demo_file_open.py
# 演示 open() 的写、读、追加与二进制基本用法

PATH = "demo.txt"

# 1) 写入（会清空已有内容）
with open(PATH, "w", encoding="utf-8") as f:
    f.write("第一行\n")
    f.write("第二行\n")

# 2) 追加（保留原内容，末尾加新行）
with open(PATH, "a", encoding="utf-8") as f:
    f.write("第三行\n")

# 3) 逐行读取（内存友好）
with open(PATH, "r", encoding="utf-8") as f:
    for line in f:
        print("读到:", line.rstrip("\n"))

# 4) 二进制写入与读取
with open("demo.bin", "wb") as f:
    f.write(bytes([0, 1, 2, 255]))

with open("demo.bin", "rb") as f:
    print("二进制:", f.read())

# 5) 检查文件是否已自动关闭
print("文件已关闭?", f.closed)  # True
```

## py.io.file_read_write

# Python 文件读写（File Read/Write）

> **一句话直觉**：程序运行时的数据存在内存里，一关机就没了；学会文件读写，你才能把数据“存下来、读回来”，这是所有数据持久化（persistence）、日志记录、配置加载和模型保存的基础。

---

## 第 1 节：为什么需要文件 I/O —— 内存 vs 磁盘

程序里的变量活在内存（RAM, Random Access Memory）中，进程一结束就消失。磁盘（disk）上的文件才是长期存储。

Python 用内置函数 `open()` 打开一个文件，得到一个**文件对象（file object）**，也叫**文件句柄（file handle）**。读写完成后必须关闭它，否则系统资源泄漏、数据可能没写入磁盘。

最推荐的写法是 `with` 语句，它会在代码块结束时自动关闭文件（即使中途抛异常也安全）：

```python
# with 会自动关闭文件，等价于 try/finally 里调用 f.close()
with open("demo.txt", "w", encoding="utf-8") as f:
    f.write("你好，文件！\n")
print("写入完成")
```

**关键结论**：永远优先用 `with open(...)`，不要在手动 `open()` 后忘记 `close()`。

---

## 第 2 节：打开模式（mode）与文本 vs 二进制

`open(path, mode)` 的 `mode` 决定行为：

| mode | 含义 |
|------|------|
| `'r'` | 只读（默认），文件必须存在 |
| `'w'` | 写入，**会清空**原内容，不存在则创建 |
| `'a'` | 追加，写到文件末尾 |
| `'x'` | 独占创建，文件已存在则报错 |
| `'r+'` / `'w+'` / `'a+'` | 读写混合 |
| `'rb'` / `'wb'` | 二进制模式（bytes） |

文本模式（text mode）下 Python 会做编码/解码；二进制模式（binary mode）读写的是 `bytes`，不做任何转换——适合图片、模型权重、压缩包。

```python
# 追加模式：不会覆盖旧内容
with open("demo.txt", "a", encoding="utf-8") as f:
    f.write("追加一行\n")

# 二进制写入：注意必须传 bytes，不能传 str
with open("demo.bin", "wb") as f:
    f.write(b"\x00\x01\x02")
```

**关键结论**：文本模式配 `encoding="utf-8"`；二进制模式不写 `encoding`，数据是 `bytes`。

---

## 第 3 节：读取文件的 4 种常用方式

```python
# 1) read()：一次读全部，适合小文件
with open("demo.txt", "r", encoding="utf-8") as f:
    content = f.read()

# 2) readline()：读一行
with open("demo.txt", "r", encoding="utf-8") as f:
    first_line = f.readline()

# 3) readlines()：读成行列表（会全部载入内存）
with open("demo.txt", "r", encoding="utf-8") as f:
    lines = f.readlines()

# 4) 直接迭代文件对象：最省内存，推荐处理大文件
with open("demo.txt", "r", encoding="utf-8") as f:
    for line in f:
        print(line.rstrip("\n"))
```

**关键结论**：小文件用 `read()`；大文件用 `for line in f` 逐行迭代，内存占用只与单行长度相关。

---

## 第 4 节：编码（encoding）——中文乱码的根源

文本在磁盘上其实是字节；从 `str` 到 `bytes` 叫编码（encode），反过程叫解码（decode）。如果不指定编码，Python 会用平台默认值（Windows 常见 GBK，Linux/macOS 多为 UTF-8），跨平台时就乱码。

```python
# 永远显式写出 encoding="utf-8"
s = "中文测试"
b = s.encode("utf-8")     # str -> bytes
print(b)                   # b'\xe4\xb8\xad\xe6\x96\x87...'
print(b.decode("utf-8"))   # bytes -> str
```

**关键结论**：读写文本文件时始终显式写 `encoding="utf-8"`，避免依赖平台默认值。

---

## 第 5 节：路径（path）与 `pathlib` 工程化写法

工程代码里别用字符串拼路径，用 `pathlib.Path`——跨平台、可读、能直接读写。

```python
from pathlib import Path

p = Path("data") / "notes.txt"   # 用 / 拼路径，跨平台安全
p.parent.mkdir(parents=True, exist_ok=True)  # 确保目录存在

p.write_text("hello\n", encoding="utf-8")   # 一步写入
text = p.read_text(encoding="utf-8")         # 一步读出
print(text)
print(p.exists(), p.suffix)                  # True '.txt'
```

**关键结论**：生产代码优先用 `pathlib.Path` 的 `read_text` / `write_text` / `open`，路径拼接用 `/` 运算符。

---

## 动手练习

**任务**：写一个 `notes_manager.py`，实现三个函数（用 `pathlib`）：

1. `append_note(path, note: str)`：向文件追加一行笔记（末尾加换行），文件不存在则创建。
2. `list_notes(path) -> list[str]`：读取所有笔记，返回去掉结尾换行的列表；文件不存在返回空列表。
3. `count_words(path) -> int`：统计文件中所有单词总数（按空白切分）。

要求：
- 全程显式使用 `encoding="utf-8"`；
- 用 `with` 或 `Path.read_text/write_text`，不要手动 `close()`；
- 自己写几行测试：追加 3 条含中文的笔记，然后打印 `list_notes` 与 `count_words` 结果。

**验收**：连续运行两次脚本，笔记应累积（不是被覆盖），且中文不乱码。

```python
from pathlib import Path

# 演示：文件读写基础 + pathlib 工程化写法
demo = Path("demo_io.txt")

# 1) 写入（覆盖）
with open(demo, "w", encoding="utf-8") as f:
    f.write("第一行\n")

# 2) 追加
with open(demo, "a", encoding="utf-8") as f:
    f.write("第二行 含中文\n")

# 3) 逐行读取（大文件友好）
with open(demo, "r", encoding="utf-8") as f:
    for line in f:
        print("读到:", line.rstrip("\n"))

# 4) pathlib 一行读写
backup = Path("demo_io_backup.txt")
backup.write_text(demo.read_text(encoding="utf-8"), encoding="utf-8")
print("备份存在?", backup.exists())

# 5) 二进制读写
bin_path = Path("demo_io.bin")
with open(bin_path, "wb") as f:
    f.write(b"\x00\x01\x02\xff")
with open(bin_path, "rb") as f:
    print("二进制前 4 字节:", f.read(4))

# 清理演示文件
for p in (demo, backup, bin_path):
    p.unlink(missing_ok=True)
```


---

## 本课题目

### single_choice · None



- [A] with 语句块执行完毕后，无论是否发生异常，文件都会被自动关闭
- [B] 只有在 with 语句块正常执行完毕时，文件才会被关闭；若抛出异常则文件保持打开
- [C] 文件会在 text = f.read() 执行后立即关闭
- [D] 文件一直保持打开，直到程序结束由解释器统一关闭

**参考答案**：0

**解析**：with 语句依赖上下文管理器协议，无论块内正常结束还是发生异常，都会调用文件对象的 __exit__ 来关闭文件，因此选项 A 正确。B 是常见误解，忽略了异常路径下的关闭行为；C 混淆了读取完成与文件关闭；D 忽略了上下文管理器的显式关闭作用。

### single_choice · None



- [A] 使用 with open(...) as f: 打开文件
- [B] 使用 f = open(...) 打开文件，并在 try/finally 中调用 f.close()
- [C] 使用 f = open(...) 打开文件后直接读取，不显式调用 f.close()
- [D] 使用 pathlib.Path(...).open() 配合 with 语句

**参考答案**：2

**解析**：直接调用 open 且不关闭文件，会依赖垃圾回收来释放资源，时机不确定，容易造成资源未及时释放。A、D 使用 with 自动关闭；B 使用 try/finally 保证关闭，都是更可靠的写法。

### single_choice · None



- [A] f = open('x.txt')
  return f.read()
- [B] try:
      f = open('x.txt')
      return f.read()
- [C] with open('x.txt') as f:
      return f.read()
- [D] f = open('x.txt')

**参考答案**：2

**解析**：with 语句在离开代码块时会自动关闭文件，即使发生异常或提前 return 也会触发关闭。A、D 没有关闭；B 没有 finally 或 with，异常时文件不会被关闭。

### single_choice · None



- [A] 'r+'
- [B] 'w+'
- [C] 'a+'
- [D] 'rw'

**参考答案**：0

**解析**：'r+' 以读写方式打开已存在文件，不会截断原内容。'w+' 会先截断文件；'a+' 以追加和读取方式打开，写入位置在末尾；'rw' 不是合法的模式组合字符串。

### single_choice · None



- [A] encoding 参数在二进制模式下也用于指定字节到字符的解码方式
- [B] encoding 参数只对文本模式有效，用于指定字符编码
- [C] encoding 参数默认值是 'ascii'，必须显式改为 'utf-8'
- [D] encoding 参数用于指定文件路径的编码方式

**参考答案**：1

**解析**：encoding 只对文本模式有意义，用来指定读写文本时使用的字符编码。二进制模式不涉及编码解码，若传入 encoding 会报错；默认编码通常与平台相关而非固定 ascii；encoding 与路径编码无关。

### single_choice · None



- [A] 123456
- [B] 456
- [C] 123
- [D] 123
  456

**参考答案**：0

**解析**：第一次以 'w' 写入 '123'；第二次以 'a' 追加 '456'，追加模式不会截断已有内容，因此最终为 '123456'。B 误以为追加会覆盖；C 忽略了第二次写入；D 误以为 append 会自动换行。

### single_choice · None



- [A] 写入的数据可能仍停留在缓冲区，尚未落盘
- [B] 文件描述符被占用，长期运行可能耗尽资源
- [C] Python 解释器会立即抛出 SyntaxError
- [D] 在 Windows 上可能因文件被占用而无法删除或重命名该文件

**参考答案**：2

**解析**：文件未关闭不会导致 SyntaxError，语法错误与文件资源管理无关。未关闭可能导致缓冲数据未刷新、文件描述符泄漏、以及 Windows 上文件被锁定等问题。

### single_choice · None



- [A] f 是一个字符串，表示文件内容
- [B] f 是文件对象，支持 read、write、close 等方法
- [C] f 是文件路径的 Path 对象
- [D] f 是 open 函数的返回值经 with 转换后的整数文件描述符

**参考答案**：1

**解析**：as f 将 open 返回的文件对象绑定给 f，文件对象提供 read、write、close 等方法。A 把对象与内容混淆；C 把文件对象与 pathlib.Path 混淆；D 错误，f 不是裸文件描述符整数。

### single_choice · None



- [A] f = open('a.txt')
  g = open('b.txt')
  # 若 g 打开失败，f 不会被关闭
- [B] try:
      f = open('a.txt')
      g = open('b.txt')
  except:
      pass
- [C] with open('a.txt') as f, open('b.txt') as g:
      pass
- [D] f = open('a.txt')
  with open('b.txt') as g:
      pass

**参考答案**：2

**解析**：在同一 with 中打开两个文件，任一环节出错时已成功打开的上下文管理器都会在退出时关闭对应文件，避免泄漏。A、D 中 f 没有受 with 或 finally 保护；B 的 except 中没有关闭 f，仍可能泄漏。

### single_choice · None



- [A] 每次调用 read() 都会从文件开头重新读取，不受之前读取影响
- [B] 连续调用 read() 会从当前文件位置继续向后读取
- [C] 文件指针只能通过 seek 显式移动，read 不会改变它
- [D] 文本模式下文件指针没有意义

**参考答案**：1

**解析**：文件对象维护当前位置，read 会从当前位置读取并推进指针，因此连续 read 会继续向后读取而不是重头开始。A 错误；C 错误，read 会改变位置；D 错误，文本模式下也有位置概念，只是 seek 有额外限制。

### single_choice · None



- [A] f = open('t.txt', 'w')
  f.write('x')
  # 没有关闭
- [B] with open('t.txt', 'w') as f:
      f.write('x')
- [C] f = open('t.txt', 'w')
  f.write('x')
  f.flush()
  # 没有关闭
- [D] f = open('t.txt', 'w')
  f.write('x')
  f.seek(0)
  # 没有关闭

**参考答案**：1

**解析**：with 块结束会关闭文件，释放操作系统层面的文件句柄，因此在 Windows 上文件通常可以立即被删除或重命名。A、C、D 都没有关闭文件，即使 flush 或 seek 也不等于关闭，文件可能仍被占用。

### single_choice · None



- [A] lines 是一个字符串，包含文件的全部内容
- [B] lines 是一个列表，每个元素是包含换行符的一行字符串
- [C] lines 是一个生成器，只能迭代一次
- [D] lines 是一个 bytes 对象，保存原始字节

**参考答案**：1

**解析**：readlines 返回列表，每行作为元素，通常保留行尾的换行符。A 描述的是 read()；C 描述的是迭代文件对象本身或生成器表达式；D 只有在二进制模式下读取才得到 bytes。

### single_choice · None



- [A] 抛出 FileExistsError，必须改用 'x' 模式
- [B] 文件原有内容保留，新写入的内容追加到末尾
- [C] 文件原有内容被截断为 0 字节，然后从头开始写入
- [D] 文件被打开为只读，原有内容不变

**参考答案**：2

**解析**：'w' 模式表示只写，若文件存在会先截断为空文件再写入，因此 C 正确。A 混淆了 'x' 独占创建模式；B 描述的是 'a' 追加模式；D 描述的是 'r' 只读模式。

### single_choice · None



- [A] 'r'
- [B] 'w'
- [C] 'a'
- [D] 'x'

**参考答案**：2

**解析**：'a' 模式表示追加写，写入位置在文件末尾，不会覆盖已有内容。'r' 只读；'w' 会截断原文件；'x' 在文件已存在时抛出 FileExistsError，都不适合追加日志。

### single_choice · None



- [A] 'w'
- [B] 'a'
- [C] 'x'
- [D] 'r+'

**参考答案**：2

**解析**：'x' 模式用于独占创建，文件已存在时会抛出 FileExistsError，符合“不覆盖已有文件”的需求。'w' 会截断并覆盖；'a' 会追加；'r+' 要求文件必须已存在，均不符合。

### single_choice · None



- [A] 使用 open(path, 'r', newline='') 打开
- [B] 使用 open(path, 'rb') 以二进制模式打开
- [C] 使用 open(path, 'r', encoding='utf-8') 打开
- [D] 使用 open(path, 'w') 打开

**参考答案**：1

**解析**：二进制模式 'rb' 不进行换行符翻译，也不涉及编码解码，可以按字节原样处理。A 中 newline='' 主要用于控制文本模式下的换行处理，但仍会解码；C 仍是文本模式；D 是写入模式。

### single_choice · None



- [A] 没有以二进制模式打开文件
- [B] 没有显式指定 encoding，导致使用平台默认编码而非文件实际编码
- [C] 没有使用 'rb' 模式，所以无法读取 Unicode
- [D] open 函数不能读取文本文件，只能用 readlines

**参考答案**：1

**解析**：文本模式若不指定 encoding，会使用平台相关的默认编码，可能与文件实际编码不一致，导致解码错误或乱码。A、C 方向反了，二进制模式并不会自动解决编码问题；D 明显错误，open 可以读取文本文件。

### single_choice · None



- [A] open('data.txt') 中的相对路径总是相对于 Python 安装目录解析
- [B] open('data.txt') 中的相对路径相对于当前工作目录解析
- [C] open('data.txt') 中的相对路径相对于脚本文件所在目录解析
- [D] open('data.txt') 只能接受绝对路径

**参考答案**：1

**解析**：相对路径默认相对于进程的当前工作目录（current working directory）解析，而不是 Python 安装目录或脚本所在目录。open 既可以接受相对路径也可以接受绝对路径。

### single_choice · None



- [A] ValueError
- [B] FileNotFoundError
- [C] OSError 的父类 Exception，具体无法确定
- [D] TypeError

**参考答案**：1

**解析**：以读模式打开不存在的文件会抛出 FileNotFoundError（它是 OSError 的子类）。ValueError、TypeError 与文件不存在无关；C 的说法不准确，实际会抛出更具体的 FileNotFoundError。

### single_choice · None



- [A] hello world（中间自动插入空格）
- [B] helloworld（两次写入直接拼接）
- [C] hello
  world（write 自动换行）
- [D] world（后一次写入覆盖前一次）

**参考答案**：1

**解析**：write 不会自动添加空格或换行，多次 write 会按顺序直接拼接，因此内容为 helloworld。A、C 是常见误解；D 错误，后续 write 是在当前位置继续写，不会覆盖前一次内容。

### single_choice · None



- [A] 第一行
  第二行
  追加
- [B] 第一行
  第二行追加
- [C] 第一行第二行追加
- [D] 追加第一行
  第二行

**参考答案**：1

**解析**：'a' 模式在原文件末尾追加，不自动添加换行；写入的字符串是 '第一行\n'、'第二行'、'追加'，因此结果中最后两个字符串之间没有换行，即 '第一行\n第二行追加'。

### single_choice · None



- [A] 'r+' 会清空文件再读写
- [B] 'w' 会清空原有内容，文件不存在则创建
- [C] 'a' 会把写入位置重置到文件开头
- [D] 'x' 与 'w' 完全相同

**参考答案**：1

**解析**：'w' 打开时截断文件（清空），不存在则创建。'r+' 不会清空；'a' 始终在末尾追加；'x' 在文件存在时报错，与 'w' 不同。

### multi_choice · None



- [A] 二进制模式 'rb' 读回的是 bytes 对象
- [B] 文本模式读取返回 str
- [C] 在二进制模式下指定 encoding 会报错
- [D] 文本模式下 write 可以直接写 bytes

**参考答案**：[0, 1, 2]

**解析**：二进制模式返回 bytes，不能指定 encoding；文本模式返回 str 且只能写 str，写 bytes 会抛 TypeError。

### multi_choice · None



- [A] with 语句在退出代码块时自动 close
- [B] 文件关闭后再调用 write 会抛 ValueError
- [C] 不关闭文件可能导致数据未写入磁盘
- [D] 垃圾回收保证文件一定被及时关闭，无需 with

**参考答案**：[0, 1, 2]

**解析**：with 自动关闭；关闭后操作文件对象抛 ValueError；未关闭可能数据留在缓冲区。依赖垃圾回收不可靠，可能延迟或不触发。

### multi_choice · None



- [A] open 时显式指定 encoding='utf-8'
- [B] 写入用 'w'，读取用 'r'
- [C] 读取时用 'rb' 然后手动 decode
- [D] 写入和读取使用不同的随机编码

**参考答案**：[0, 1, 2]

**解析**：显式指定编码最稳妥；'r'/'w' 是默认正确模式；二进制读后手动 decode 也可行。读写使用不同编码会导致乱码。

### multi_choice · None



- [A] 'a' 模式写入总是从文件末尾开始
- [B] 'w' 模式打开时截断已有内容
- [C] 'a' 模式在文件不存在时会创建文件
- [D] 'a' 模式可以用 seek 定位后在中间覆盖写入

**参考答案**：[0, 1, 2]

**解析**：'a' 追加写入并在不存在时创建，seek 对写入位置在多数平台上无效（写入仍到末尾）；'w' 截断文件。

### fill_blank · None



**参考答案**：["'r'", "\"r\"", "mode='r'", "'rt'", "\"rt\""]

**解析**：文本只读模式为 'r'（或显式 'rt'），配合 encoding 可正确读取文本。

### fill_blank · None



**参考答案**：["'\\n'", "\"\\n\"", "'\\\\n'"]

**解析**：换行符用 '\n' 表示（也可用 os.linesep，但通用写法是 '\n'）。

### fill_blank · None



**参考答案**：["'rb'", "\"rb\""]

**解析**：二进制只读模式是 'rb'，读取返回 bytes，不需要也不能指定 encoding。

### code_reading · None



**参考答案**：['a', 'b']

**解析**：文件内容为 'a\nb\n'，逐行迭代得到 'a\n'、'b\n'，strip 去掉首尾空白（含换行）后为 ['a', 'b']。

### code_reading · None



**参考答案**：second

**解析**：第二个 with 以 'w' 打开会截断文件，first 被清空，最终只剩 second。若想追加应使用 'a'。

### scenario · None



**解析**：readlines() 会把整个 2GB 文件一次性载入内存，容易 MemoryError。更合适的做法是直接 for line in f 逐行迭代，或分块读取，边读边统计，内存占用恒定。

### single_choice · None



- [A] f.read()
- [B] f.readlines()
- [C] for line in f: 逐行迭代
- [D] list(f)

**参考答案**：2

**解析**：逐行迭代文件对象每次只加载一行，内存占用小。read()、readlines()、list(f) 都会把全部内容载入内存。

### scenario · None



**解析**：open 未指定 encoding 时使用平台默认编码，不同机器默认编码不同（如 Windows 的 GBK 与 Linux 的 UTF-8），导致解码失败。修复：在 open 中显式指定 encoding='utf-8'（或配置文件声明并统一使用）。

### single_choice · None



- [A] 文件会自动加密
- [B] 读取速度更快
- [C] 即使发生异常也能正确关闭文件
- [D] 可以省略 mode 参数

**参考答案**：2

**解析**：with 语句利用上下文管理器，无论代码块正常结束还是抛异常，都会调用文件对象的 close()，防止资源泄漏。

### single_choice · None



- [A] hello
- [B] hello世
- [C] hello世界
- [D] hell

**参考答案**：1

**解析**：文本模式下 read(n) 读取 n 个字符而非字节，'hello' 是 5 个字符，但这里读 5 个字符得到 'hello'。需要注意：在文本模式下 read(5) 读的是 5 个字符，'hello' 正好 5 个字符，所以输出 'hello'。更正：read(5) 返回前 5 个字符即 'hello'，不含'世'。正确答案为下标 0。

### single_choice · None



- [A] 文本模式下 newline='' 表示把 
  、\r
   等都保留不转换
- [B] newline 只能用于二进制模式
- [C] newline 参数影响 encoding 的取值
- [D] newline=‘
  ’ 会禁止读取任何换行

**参考答案**：0

**解析**：文本模式下 newline 控制换行处理：newline=None（默认）统一转换为 '\n'；newline='' 不转换、保留原样；newline 为其他字符时按该字符切分。它不能用于二进制模式，也不影响编码。

### single_choice · None



- [A] write 不能写字符串
- [B] 没有指定 encoding，可能使用平台默认编码导致错误或乱码
- [C] mode 应为 'wb'
- [D] 文件名不能含中文

**参考答案**：1

**解析**：open 默认使用平台默认编码（Windows 常为 GBK），写入中文时若编码不匹配可能乱码。推荐显式指定 encoding='utf-8'。

### single_choice · None



- [A] 直接 open 并忽略异常
- [B] 用 try/except FileNotFoundError 或先 os.path.exists 判断
- [C] 将 mode 改为 'w' 强制创建
- [D] 使用 open 的 encoding=None

**参考答案**：1

**解析**：捕获 FileNotFoundError 或用 exists 判断可以优雅处理文件缺失；改成 'w' 会清空已有文件，属于破坏性操作。

### single_choice · None



- [A] 清空文件内容
- [B] 关闭文件
- [C] 将缓冲区数据强制写入磁盘
- [D] 切换为只读模式

**参考答案**：2

**解析**：flush() 把内存缓冲区中的数据立即写入底层文件，不关闭文件；close() 会先 flush 再关闭。

### single_choice · None



- [A] 文件对象只能顺序读取，无法改变位置
- [B] seek(0) 一定把位置移到文件末尾
- [C] tell() 返回当前读写位置的字节偏移（二进制模式）
- [D] 文本模式下 seek 任意值总是合法的

**参考答案**：2

**解析**：二进制模式下 tell()/seek() 以字节为偏移。文本模式下 seek 只允许移动到 tell() 返回过的位置或 0，不能任意偏移。
