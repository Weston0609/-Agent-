# s2u6l4 Python `subprocess` 标准库：让你的程序会「调用」别的程序 / 文件与目录操作的标准工具箱

> 来源 `content/lessons/s2u6l4.json`

## py.stdlib.subprocess

# Python `subprocess` 标准库：让你的程序会「调用」别的程序

> 一句话直觉：**Python 自己的代码解决不了的活儿（比如让 `ffmpeg` 转个视频、让 `git` 拉个代码、让 `pip` 装个包），都可以通过 `subprocess` 启动一个外部进程（external process）来完成，并拿到它的输出结果。**

---

## 1. 为什么需要 `subprocess`？——从系统调用说起

操作系统（Operating System）本身提供了创建进程（process）的能力。在 Python 里我们不会直接写系统调用，而是用标准库 `subprocess` 作为「遥控器」：

- 它可以启动一个新程序（比如 `ping`、`ls`、`python`）。
- 可以给这个程序传参数（命令行参数，command-line arguments）。
- 可以捕获它的标准输出（stdout）和标准错误（stderr）。
- 可以等待它结束并读取退出码（exit code），判断成功或失败。

最基础的入口是 `subprocess.run()`，它是官方推荐的「现代写法」。

```python
import subprocess  # 导入标准库

# 运行一个最简单的命令：让系统打印当前工作目录
result = subprocess.run(["pwd"], capture_output=True, text=True)

print("退出码：", result.returncode)   # 0 表示成功
print("标准输出：", result.stdout)     # 命令打印在屏幕上的内容
```

**关键结论**：

- 命令和参数要用**列表**写（第 1 个元素是程序名，其余是参数），这样能避免空格被 shell 错误拆分。
- `capture_output=True` 表示把 stdout/stderr 收进 Python 变量里，而不是直接打印到终端。
- `text=True` 表示以字符串（`str`）而非字节（`bytes`）返回结果，方便中文处理。

---

## 2. 返回值 `CompletedProcess`：退出码、stdout 与 stderr

`subprocess.run()` 返回一个 `CompletedProcess` 对象，它是我们与子进程（child process）的「沟通结果」。

```python
import subprocess

# 故意运行一个不存在的命令，看看会发生什么
result = subprocess.run(
    ["ls", "/root/does_not_exist"],   # 访问不存在的目录
    capture_output=True,
    text=True,
)

print("returncode =", result.returncode)   # 通常是 2（非零 = 失败）
print("stdout     =", repr(result.stdout)) # 空字符串
print("stderr     =", result.stderr)       # 错误信息在这里
```

**关键结论**：

- `returncode == 0`：命令成功执行。
- `returncode != 0`：命令失败，原因通常在 `stderr` 里。
- **`capture_output=True` 一定要配合 `text=True`** 才方便阅读中文；否则拿到的是 `bytes`，需要 `.decode("utf-8")`。
- `subprocess.run()` 默认不会在非零退出码时抛异常，需要的话显式加 `check=True`。

---

## 3. 异常处理：`check=True`、`FileNotFoundError` 与 `TimeoutExpired`

工程代码里，失败是常态，所以我们必须会「接住」错误。

```python
import subprocess

# 情形 A：命令返回非零 → check=True 会抛 CalledProcessError
 try:
    subprocess.run(["ls", "/no/such/dir"], check=True, capture_output=True, text=True)
except subprocess.CalledProcessError as e:
    print("命令失败，退出码 =", e.returncode)
    print("错误输出 =", e.stderr)

# 情形 B：程序本身不存在 → FileNotFoundError
try:
    subprocess.run(["this_program_does_not_exist"], check=True)
except FileNotFoundError as e:
    print("找不到这个可执行程序：", e.filename)

# 情形 C：命令跑太久 → TimeoutExpired
try:
    subprocess.run(["sleep", "10"], timeout=1)
except subprocess.TimeoutExpired:
    print("超时了，已终止子进程")
```

**关键结论**：

- `check=True`：命令返回非零时抛出 `CalledProcessError`，比自己判断 `returncode` 更工程化。
- 常见异常三类：`CalledProcessError`（命令失败）、`FileNotFoundError`（命令不存在）、`TimeoutExpired`（超时）。
- 生产脚本永远要写 `timeout=`，否则一个卡住的命令会拖死整个服务。

---

## 4. 进阶：`Popen` 与「流式」读取

`subprocess.run()` 是「一次执行、一次拿结果」。如果命令会**持续输出**（比如日志、训练进度），就需要 `Popen`（process open 的缩写）。

```python
import subprocess

# 逐行读取子进程输出（实时看到 progress）
proc = subprocess.Popen(
    ["python", "-c", "for i in range(3): print('step', i)"],
    stdout=subprocess.PIPE,
    text=True,
)

for line in proc.stdout:   # 边输出边读
    print("子进程说：", line.rstrip())

proc.wait()                # 等它结束
print("退出码：", proc.returncode)
```

**关键结论**：

- `Popen` 让你**在命令运行期间**就能处理输出，适合长任务。
- `stdout=subprocess.PIPE` 表示把 stdout 接到管道（pipe），由 Python 读取。
- 记住最后调用 `.wait()`，否则会留下僵尸进程（zombie process）。
- 简单任务用 `run()`，需要流式/交互才用 `Popen`。

---

## 5. 安全底线：`shell=True` 与命令注入

`shell=True` 会让命令交给系统的 shell 解析，虽然写起来「像在终端里打字」，但带来严重风险（命令注入，command injection）。

```python
import subprocess

# ❌ 危险示例：文件名来自用户输入
user_file = "data.txt; rm -rf ~"   # 恶意输入
# subprocess.run(f"cat {user_file}", shell=True)  # 千万不要这样写！

# ✅ 安全写法：用列表，不经过 shell
user_file = "data.txt"
subprocess.run(["cat", user_file], check=True)
```

**关键结论**：

- **默认不要用 `shell=True`**。除非你确实需要 shell 特性（通配符、管道、环境变量展开），并且输入完全可信。
- 用**列表传参**是防注入的第一道防线。
- 需要用到 shell 能力时，优先在 Python 里组合（比如用 `|` 的场景，可拆成两次 `run()` 或用 Python 处理）。

---

## 小结

| 场景 | 推荐 API |
|------|----------|
| 一次性执行 + 拿结果 | `subprocess.run()` |
| 需要流式 / 交互式输出 | `subprocess.Popen` |
| 出错就抛异常 | `check=True` |
| 防止卡死 | `timeout=` |
| 安全传参 | 用列表，不用 `shell=True` |

```python
import subprocess


def run_safely(cmd: list[str], timeout: float = 5.0) -> dict:
    """运行外部命令并返回结构化结果（不抛异常）。

    Args:
        cmd: 命令 + 参数组成的列表，例如 ["ls", "-l"]。
        timeout: 最长等待秒数，避免卡死。
    Returns:
        dict，包含 ok / returncode / stdout / stderr。
    """
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,   # 收 stdout / stderr
            text=True,             # 返回 str 而非 bytes
            timeout=timeout,       # 防卡死
        )
        return {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }
    except FileNotFoundError as e:
        # 命令本身不存在
        return {"ok": False, "returncode": None, "stdout": "", "stderr": f"命令不存在: {e.filename}"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "returncode": None, "stdout": "", "stderr": "超时"}


if __name__ == "__main__":
    # 正常情况：列出当前目录
    r = run_safely(["ls", "-1"])
    print("ok =", r["ok"], "| stdout 前 3 行：")
    print("\n".join(r["stdout"].splitlines()[:3]))

    # 失败情况：访问不存在的目录
    r = run_safely(["ls", "/no/such/dir"])
    print("ok =", r["ok"], "| stderr =", r["stderr"].strip())

    # 超时情况
    r = run_safely(["sleep", "2"], timeout=0.3)
    print("ok =", r["ok"], "| stderr =", r["stderr"])
```

## py.stdlib.shutil

# py.stdlib.shutil：文件与目录操作的标准工具箱

## 一句话直觉

> 你每天都在做「复制文件、移动目录、删除整个文件夹、打包备份」这些事——`shutil`（**sh**ell **util**ities，外壳工具集）就是 Python 标准库里专门干这些脏活累活的模块，用它一行顶十行，而且跨平台安全。

`shutil` 是 Python 标准库（Standard Library）的一部分，无需 `pip install`，直接 `import shutil` 即可。它建立在更底层的 `os` 模块之上，把文件系统（File System）操作封装成高层、易读、跨平台（cross-platform）的 API。

---

## 第 1 节：为什么要用 shutil，而不是手写 os 循环？

如果不用 `shutil`，你想「复制一个文件夹」得自己递归（recursion）遍历、判断是文件还是目录、创建目标目录、再逐个复制——代码长、易漏边界、还可能踩到符号链接（symbolic link）的坑。

`shutil` 提供的核心价值：

- **高层抽象**：`copy`、`copytree`、`move`、`rmtree` 一行搞定。
- **跨平台**：自动处理 Windows / macOS / Linux 的路径分隔符（path separator）差异。
- **元数据（metadata）保留**：可选保留权限、时间戳。
- **安全删除**：`rmtree` 有防护机制，避免误删关键目录。

```python
import shutil
import os

# 复制单个文件（目标可以是文件路径或目录）
shutil.copy("source.txt", "backup.txt")          # 复制内容 + 权限
shutil.copy2("source.txt", "backup2.txt")        # copy2 = copy + 元数据(时间戳)

# 复制整个目录树（directory tree）
shutil.copytree("my_project", "my_project_backup")

# 移动文件或目录（跨磁盘也能用）
shutil.move("old_name.txt", "new_folder/new_name.txt")

# 删除整个目录树（相当于 rm -rf，但更安全）
shutil.rmtree("temp_dir")
```

> 记忆口诀：**copy 管文件，copytree 管目录，move 管搬家，rmtree 管清场。**

---

## 第 2 节：copy 家族——copy / copy2 / copyfile 的区别

`shutil` 里名字带 `copy` 的函数有好几个，初学者最容易混。看下面这张对照表：

| 函数 | 复制内容 | 复制权限 | 复制时间戳 | 目标可以是目录 |
|------|----------|----------|------------|----------------|
| `copyfile(src, dst)` | ✅ | ❌ | ❌ | ❌ |
| `copy(src, dst)` | ✅ | ✅ | ❌ | ✅ |
| `copy2(src, dst)` | ✅ | ✅ | ✅ | ✅ |
| `copymode(src, dst)` | ❌ | ✅ | ❌ | — |
| `copystat(src, dst)` | ❌ | ✅ | ✅ | — |

**工程建议**：默认用 `copy2`，因为它保留最多信息；只有明确不想要元数据时才用 `copy`。

```python
import shutil
import os
import time

# 准备一个源文件
with open("demo.txt", "w") as f:
    f.write("hello shutil")

time.sleep(1)  # 让时间戳有差异，方便观察

# copy2 会保留修改时间
shutil.copy2("demo.txt", "demo_copy2.txt")

print("源文件 mtime:", os.path.getmtime("demo.txt"))
print("copy2 mtime:", os.path.getmtime("demo_copy2.txt"))  # 两者几乎一致
```

关键点：`copyfile` 要求 `dst` 是**完整文件路径**，不能是目录；而 `copy` / `copy2` 允许 `dst` 是目录，此时同名文件会被放进该目录。

---

## 第 3 节：目录级操作——copytree 与 rmtree

`copytree` 递归复制整个目录，`rmtree` 递归删除整个目录。这两个是最常用、也最容易出事的函数。

```python
import shutil
import os

# 建立测试目录结构
os.makedirs("project/src", exist_ok=True)
os.makedirs("project/data", exist_ok=True)
with open("project/src/main.py", "w") as f:
    f.write("print('hi')")
with open("project/data/info.txt", "w") as f:
    f.write("data")

# 递归复制
shutil.copytree("project", "project_backup")
print(os.listdir("project_backup"))  # ['src', 'data']

# 递归删除
shutil.rmtree("project_backup")
print(os.path.exists("project_backup"))  # False
```

**重要安全特性**：从 Python 3.12 开始，`rmtree` 默认不会删除符号链接指向的目录，也不会删除文件系统根目录（`/`）——这是防止误操作的护栏。

如果目标目录已存在，`copytree` 默认会报错。这时用 `dirs_exist_ok=True`（Python 3.8+）：

```python
shutil.copytree("project", "project_backup", dirs_exist_ok=True)
```

---

## 第 4 节：磁盘空间、归档与查找

除了复制/删除，`shutil` 还提供了一些「顺手小工具」：

```python
import shutil

# 1) 查询磁盘空间（单位：字节）
total, used, free = shutil.disk_usage("/")
print(f"总: {total/1e9:.1f} GB, 已用: {used/1e9:.1f} GB, 可用: {free/1e9:.1f} GB")

# 2) 查找可执行文件（类似 which 命令）
print(shutil.which("python"))   # 例如 /usr/bin/python
print(shutil.which("git"))      # 例如 /usr/bin/git

# 3) 打包成 zip 归档（archive）
shutil.make_archive("backup", "zip", root_dir="project")

# 4) 解包
shutil.unpack_archive("backup.zip", "restored")
```

`make_archive` 和 `unpack_archive` 支持 `zip`、`tar`、`gztar` 等格式，是写「一键备份脚本」的利器。

> 工程级提示：归档路径若来自用户输入，务必做路径校验，防止目录穿越（directory traversal）攻击。

---

## 第 5 节：工程实践——一个安全的备份工具

把前面知识串起来，写一个真实场景会用到的「带时间戳的备份函数」：

```python
import shutil
import os
from datetime import datetime

def backup(source_dir: str, backup_root: str = "backups") -> str:
    """把 source_dir 备份到 backup_root 下，目录名带时间戳。"""
    if not os.path.isdir(source_dir):
        raise FileNotFoundError(f"源目录不存在: {source_dir}")

    os.makedirs(backup_root, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = os.path.join(backup_root, f"{os.path.basename(source_dir)}_{stamp}")

    # 使用 copytree 并允许目标已存在（避免重复运行时崩溃）
    shutil.copytree(source_dir, target, dirs_exist_ok=True)
    return target

print(backup("project"))
```

这段代码覆盖了 `shutil` 的核心用法（`copytree`），并体现了工程思维：**输入校验、目录创建、时间戳命名、可重复执行**。

---

## 动手练习

**任务：写一个「项目目录快照 + 自动清理」脚本 `snapshot.py`**

要求：

1. 接收两个命令行参数：`source`（源目录）和 `keep`（保留的最新快照数量，整数）。
2. 每次运行时，在 `snapshots/` 目录下创建一个名为 `快照名_YYYYMMDD_HHMMSS` 的快照目录，内容是 `source` 的完整副本（用 `copytree`）。
3. 如果 `snapshots/` 下的快照数量超过 `keep`，删除最旧的快照（用 `rmtree`）。
4. 如果源目录是文件而不是目录，改为复制该文件（用 `copy2`）。
5. 运行结束后，用 `shutil.disk_usage` 打印当前磁盘剩余空间。

**验收标准**：
- 连续运行 3 次，`keep=2`，最终 `snapshots/` 下只剩 2 个快照。
- 传入不存在的路径时，脚本给出友好报错而不是崩溃。
- 用 `shutil.which` 提示用户当前 Python 解释器路径。

**提示**：使用 `sys.argv` 读取参数；用 `datetime` 生成时间戳；用 `os.listdir` + `sorted` 找出最旧目录。

```python
import shutil
import os
from datetime import datetime


def snapshot(source: str, keep: int = 3, root: str = "snapshots") -> str:
    """对 source 创建一次带时间戳的快照，并只保留最新 keep 份。"""
    if not os.path.exists(source):
        raise FileNotFoundError(f"源路径不存在: {source}")

    os.makedirs(root, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    name = f"{os.path.basename(source.rstrip(os.sep))}_{stamp}"
    target = os.path.join(root, name)

    if os.path.isdir(source):
        shutil.copytree(source, target)          # 目录 -> 递归复制
    else:
        os.makedirs(target, exist_ok=True)
        shutil.copy2(source, target)             # 文件 -> 复制 + 元数据

    # 清理旧快照
    snaps = sorted(os.path.join(root, d) for d in os.listdir(root))
    while len(snaps) > keep:
        shutil.rmtree(snaps.pop(0))              # 删除最旧的

    return target


if __name__ == "__main__":
    # 构造一个测试目录
    os.makedirs("demo_proj/src", exist_ok=True)
    with open("demo_proj/src/app.py", "w") as f:
        f.write("print('hello')")

    for i in range(3):
        path = snapshot("demo_proj", keep=2)
        print(f"第 {i+1} 次快照: {path}")

    print("剩余快照:", sorted(os.listdir("snapshots")))

    total, used, free = shutil.disk_usage("/")
    print(f"磁盘可用: {free / 1e9:.2f} GB")
    print("当前 Python:", shutil.which("python") or shutil.which("python3"))
```


---

## 本课题目

### single_choice · None



- [A] 使用 os.system() 并捕获返回值
- [B] 使用 subprocess.run() 并设置 capture_output=True
- [C] 使用 subprocess.Popen() 且不调用 communicate()
- [D] 使用 sys.execv() 直接替换当前进程

**参考答案**：1

**解析**：subprocess.run() 配合 capture_output=True 能直接获取标准输出和标准错误，是最常用的方式。os.system() 只能获得退出码，无法获取输出；Popen() 需要额外调用 communicate()；sys.execv() 会替换当前进程。

### single_choice · None



- [A] shell=True
- [B] check=True
- [C] capture_output=True
- [D] text=True

**参考答案**：1

**解析**：check=True 会在命令返回非零退出码时抛出 CalledProcessError。shell=True 是控制是否通过 shell 执行；capture_output 和 text 分别控制输出捕获与文本模式。

### single_choice · None



- [A] subprocess.run(['ls | grep py'])
- [B] subprocess.run('ls | grep py', shell=True)
- [C] subprocess.run(['ls', '|', 'grep', 'py'])
- [D] subprocess.run('ls | grep py', shell=False)

**参考答案**：1

**解析**：shell=True 且命令作为字符串传入时，会交给系统 shell 解释，从而支持管道。传列表且 shell=False 时管道符不会被解释；传列表且 shell=True 时第一个元素被当作 shell 命令，其余作为参数。

### single_choice · None



- [A] 0
- [B] 1
- [C] None
- [D] 抛出异常

**参考答案**：1

**解析**：子进程中的 Python 因 ZeroDivisionError 异常退出，返回非零退出码（通常为 1）。因为没有设置 check=True，不会抛出异常，r.returncode 为 1。

### single_choice · None



- [A] call() 返回 CompletedProcess 对象，run() 返回退出码
- [B] run() 返回 CompletedProcess 对象，call() 返回退出码
- [C] 两者完全等价，只是名称不同
- [D] call() 不支持 shell=True

**参考答案**：1

**解析**：subprocess.run() 返回 CompletedProcess 实例，便于获取输出和退出码；subprocess.call() 是旧接口，直接返回退出码。

### single_choice · None



- [A] 子进程会自动被杀死，没有任何问题
- [B] 子进程可能变成孤儿进程继续运行，且管道缓冲区可能填满导致死锁
- [C] Python 会抛出 RuntimeError
- [D] 子进程的退出码无法获取，但进程一定结束

**参考答案**：1

**解析**：Popen 不会自动等待子进程。若父进程退出，子进程可能成为孤儿；若使用了管道且不读取输出，缓冲区填满后子进程会阻塞，造成死锁。

### single_choice · None



- [A] cwd
- [B] chdir
- [C] workdir
- [D] path

**参考答案**：0

**解析**：subprocess 的 cwd 参数用于设置子进程的当前工作目录。chdir 不是 subprocess 参数；workdir 和 path 也不是。

### single_choice · None



- [A] env 参数，传入包含所有环境变量的字典
- [B] environment 参数，传入要添加的键值对
- [C] setenv 参数，传入要设置的变量名
- [D] inherit_env 参数，设为 True

**参考答案**：0

**解析**：env 参数用于指定子进程的环境变量字典。若希望继承当前环境，通常先复制 os.environ 再修改。其他参数名不存在。

### single_choice · None



- [A] 它用于将子进程的输出重定向到空设备，丢弃输出
- [B] 它表示子进程的输入为空，不能读取
- [C] 它等价于 subprocess.PIPE
- [D] 它只能用于 stderr，不能用于 stdout

**参考答案**：0

**解析**：subprocess.DEVNULL 是一个特殊值，可传给 stdin/stdout/stderr，表示重定向到空设备（丢弃输出或提供空输入）。它不等价于 PIPE。

### single_choice · None



- [A] 命令名带 .exe 后缀且存在于 PATH 中
- [B] 命令是 shell 内置命令（如 dir）且未指定 shell=True
- [C] 使用绝对路径指定可执行文件
- [D] 使用 sys.executable 作为命令

**参考答案**：1

**解析**：未指定 shell=True 时，subprocess 直接查找可执行文件。dir 等是 shell 内置命令，没有对应的可执行文件，因此会抛出 FileNotFoundError。

### single_choice · None



- [A] 输出会直接打印到终端，因为未保存返回值
- [B] 输出被捕获到 CompletedProcess 对象中，但未保存返回值所以无法访问
- [C] 会抛出 ValueError
- [D] stdout=PIPE 在 text=True 时无效

**参考答案**：1

**解析**：stdout=PIPE 会捕获输出，不打印到终端。由于没有保存 run() 的返回值，CompletedProcess 对象被丢弃，无法再访问输出。

### single_choice · None



- [A] timeout 参数只对 Popen 有效，run() 不支持
- [B] timeout 超时后会杀死子进程并抛出 TimeoutExpired
- [C] timeout 超时后子进程会继续运行，只是调用返回
- [D] timeout 参数单位是毫秒

**参考答案**：1

**解析**：subprocess.run() 和 Popen.communicate() 都支持 timeout。超时后会杀死子进程并抛出 subprocess.TimeoutExpired。单位是秒。

### single_choice · None



- [A] result.stdout
- [B] result.output
- [C] result.stderr
- [D] result.returncode

**参考答案**：0

**解析**：CompletedProcess 对象的 stdout 属性保存标准输出；stderr 保存标准错误；returncode 是退出码；output 不是该对象的属性。

### single_choice · None



- [A] 它会把命令的输出编码为 UTF-8 字节串
- [B] 它会把 stdin/stdout/stderr 以文本字符串形式处理
- [C] 它等同于 shell=True
- [D] 它会把命令的返回值自动转换为字符串

**参考答案**：1

**解析**：text=True（或 universal_newlines=True）让子进程的输入输出以文本模式（str）处理，而不是默认的字节串。它不影响 shell 行为，也不会改变返回码类型。

### single_choice · None



- [A] 通过系统 shell 解释并执行 echo hello
- [B] 直接执行名为 echo 的可执行文件，不经过 shell
- [C] 因为 echo 是 shell 内置命令而报错
- [D] 等价于 subprocess.run('echo hello', shell=True)

**参考答案**：1

**解析**：不指定 shell=True 时，第一个参数是命令列表，subprocess 会直接执行该可执行文件而不会经过 shell。因此 echo 需要是系统上真实存在的可执行文件。

### single_choice · None



- [A] stdin
- [B] input
- [C] stdout
- [D] args

**参考答案**：1

**解析**：subprocess.run() 的 input 参数用于向子进程的标准输入传递数据，会自动设置 stdin=PIPE。stdin 参数用于重定向，stdout 用于输出重定向，args 是命令本身。

### single_choice · None



- [A] p.start()
- [B] p.wait()
- [C] p.poll()
- [D] p.terminate()

**参考答案**：1

**解析**：wait() 会阻塞直到子进程结束并返回退出码。poll() 是非阻塞检查，可能返回 None；terminate() 是发送终止信号；start() 不是 Popen 的方法。

### single_choice · None



- [A] 它只能用于读取标准输出，不能发送输入
- [B] 它会等待子进程结束，并可选地发送输入、读取输出
- [C] 它等同于调用 wait() 但不读取输出
- [D] 它只能在没有使用管道时调用

**参考答案**：1

**解析**：communicate() 会与子进程交互：发送 input 数据（如果提供），读取 stdout/stderr 直到结束，并等待进程终止。这是避免管道死锁的推荐方式。

### single_choice · None



- [A] e.output
- [B] e.stderr
- [C] e.stdout
- [D] e.returncode

**参考答案**：1

**解析**：CalledProcessError 对象有 stderr 属性保存标准错误；output 是旧式别名（在某些版本中指向 stdout）；stdout 属性保存标准输出；returncode 是退出码。

### single_choice · None



- [A] 两者等效，可以同时使用
- [B] 会引发 ValueError，因为两者不能同时指定
- [C] capture_output 会覆盖 stdout 的设置
- [D] stdout 会被忽略，只捕获标准错误

**参考答案**：1

**解析**：capture_output=True 已经隐含了 stdout=PIPE 和 stderr=PIPE，如果同时显式指定 stdout 或 stderr，会引发 ValueError。

### single_choice · None



- [A] 源文件与目标文件是同一个文件
- [B] 目标文件已存在且为普通文件
- [C] 源文件是普通文本文件
- [D] 目标路径所在磁盘剩余空间充足

**参考答案**：0

**解析**：shutil.copyfile() 明确禁止源和目标为同一文件，会抛出 SameFileError。目标已存在、源是普通文件、磁盘空间充足都不会导致异常。

### single_choice · None



- [A] copy 会复制权限位，copyfile 不会
- [B] copy 会复制文件内容，copyfile 只复制元数据
- [C] copy 只能复制目录，copyfile 只能复制文件
- [D] 两者完全等价，只是名字不同

**参考答案**：0

**解析**：shutil.copy() 在复制内容的同时会复制权限位（mode），而 copyfile() 只复制文件内容。两者都不能复制目录。

### single_choice · None



- [A] 修改文件的所有者和所属组（依赖底层操作系统的支持）
- [B] 修改文件的权限位（如 644、755）
- [C] 修改文件的访问时间
- [D] 修改文件的扩展名

**参考答案**：0

**解析**：shutil.chown() 用于更改文件属主和属组，它是对 os.chown() 的封装，可接受用户名/组名。修改权限位应使用 os.chmod()。

### single_choice · None



- [A] shutil.get_terminal_size()
- [B] shutil.disk_usage('/')
- [C] shutil.which('tty')
- [D] shutil.copyfileobj()

**参考答案**：0

**解析**：shutil.get_terminal_size() 返回终端大小（columns, lines）。若无终端，则回退到环境变量或默认值。其他选项与该需求无关。

### multi_choice · None



- [A] 它从 fsrc 读取数据并写入 fdst，直到 fsrc 到达 EOF
- [B] 它接收的是文件对象，而不是文件路径
- [C] 可以通过 length 参数限制复制的字节数
- [D] 它只能复制文本文件，不能复制二进制文件
- [E] 它会自动关闭 fsrc 和 fdst

**参考答案**：[0, 1, 2]

**解析**：copyfileobj() 接收文件对象，从 fsrc 读取并写入 fdst 直到 EOF，可用 length 限制字节数。它不区分文本/二进制，也不会自动关闭文件。

### multi_choice · None



- [A] shutil.copy
- [B] shutil.copy2
- [C] shutil.copystat
- [D] shutil.copyfile
- [E] shutil.rmtree

**参考答案**：[0, 1, 2]

**解析**：copy 保留权限位；copy2 保留更多元数据；copystat 专门复制状态信息。copyfile 只复制内容，rmtree 是删除操作，均不保留元数据。

### multi_choice · None



- [A] ignore 参数可以接受一个可调用对象，用于过滤要忽略的文件/目录
- [B] dirs_exist_ok=True 时，允许目标目录已存在并合并内容
- [C] symlinks=True 时会复制符号链接本身而非其指向的文件
- [D] copytree 不能复制符号链接，永远跟随链接

**参考答案**：[0, 1, 2]

**解析**：copytree 支持 ignore 回调、dirs_exist_ok 合并、symlinks 控制链接处理方式。默认情况下会跟随符号链接，但可通过 symlinks=True 复制链接本身，因此 D 错误。

### fill_blank · None



**参考答案**：["rmtree", "shutil.rmtree", "shutil.rmtree()"]

**解析**：shutil.rmtree(path) 专门用于递归删除目录树，删除空目录可以用 os.rmdir，但非空目录必须用 rmtree。

### fill_blank · None



**参考答案**：["SameFileError", "shutil.SameFileError"]

**解析**：shutil 定义了 SameFileError 异常，当源和目标为同一文件时抛出，用于防止意外清空源文件。

### code_reading · None



**参考答案**：第二次调用会抛出 FileExistsError，因为 copytree 默认要求目标目录不存在。如需合并，应传入 dirs_exist_ok=True。

**解析**：copytree() 在目标已存在且未指定 dirs_exist_ok=True 时，会抛出 FileExistsError，以防止误覆盖已有目录内容。

### code_reading · None



**参考答案**：b.txt 的内容是 'hello'（5 个字节）。因为 copyfileobj 会从源文件对象读取数据并原样写入目标文件对象，直到读取到 EOF。

**解析**：copyfileobj 不解析文件内容，只做字节流式的读写，直到 fsrc 读到 EOF。因此 b.txt 与 a.txt 内容一致。

### scenario · None



**解析**：直接 copytree 会因目标目录已存在而抛出 FileExistsError，无法覆盖发布；应使用 dirs_exist_ok=True 进行合并式复制，把新构建内容合并进现有目录，从而保留旧日志等文件。

### single_choice · None



- [A] 会尝试保留更多元数据（如修改时间、访问时间）
- [B] 会递归复制整个目录树
- [C] 会自动覆盖只读文件
- [D] 会校验复制内容的哈希值

**参考答案**：0

**解析**：copy2() 在 copy() 的基础上还会通过 copystat() 复制文件元数据（如 mtime、atime）。它不递归复制目录，也不做哈希校验。

### single_choice · None



- [A] 抛出 FileExistsError
- [B] 合并到已有目录中
- [C] 先删除 dst 再复制
- [D] 静默跳过

**参考答案**：0

**解析**：copytree() 默认要求目标目录不存在，否则抛出 FileExistsError。要合并或覆盖需使用 dirs_exist_ok=True 参数。

### single_choice · None



- [A] 它递归删除目录及其所有内容，包括非空目录
- [B] 它只能删除空目录
- [C] 它会把目录移动到回收站
- [D] 它默认会先询问用户确认

**参考答案**：0

**解析**：shutil.rmtree() 用于递归删除目录树，包括其中的所有文件和子目录。它不能删除单个文件（那是 os.remove 的职责），也不会移动到回收站或询问确认。

### single_choice · None



- [A] 当 src 和 dst 跨文件系统时，move 会先复制再删除，而 rename 可能失败
- [B] move 只能移动目录，rename 只能移动文件
- [C] move 会自动进行文件内容校验
- [D] move 不需要目标路径存在

**参考答案**：0

**解析**：os.rename() 在同一文件系统内重命名/移动很快，但跨文件系统时可能失效；shutil.move() 会检测到跨文件系统并执行“复制+删除”的降级策略。

### single_choice · None



- [A] total、used、free
- [B] size、count、name
- [C] read、write、exec
- [D] inode、block、mount

**参考答案**：0

**解析**：disk_usage() 返回一个具名元组，包含 total（总空间）、used（已用空间）、free（可用空间），单位是字节。

### single_choice · None



- [A] 在 PATH 环境变量中查找可执行文件并返回其路径（找不到返回 None）
- [B] 返回当前 Python 解释器的版本号
- [C] 检查 python3 是否为内置模块
- [D] 启动一个 python3 子进程

**参考答案**：0

**解析**：shutil.which() 模拟 shell 的 which 命令，在 PATH 中搜索指定命令，返回可执行文件的绝对路径；未找到返回 None。它不会启动子进程或查询版本。

### single_choice · None



- [A] base_name 是不含扩展名的归档路径，format 决定压缩格式，root_dir 是要打包的源目录
- [B] base_name 是源目录名，root_dir 是输出路径
- [C] format 只能是 'zip'，其他格式不支持
- [D] root_dir 必须是空目录

**参考答案**：0

**解析**：make_archive(base_name, format, root_dir=...) 中 base_name 是不含扩展名的输出路径，format 决定格式（如 zip、tar、gztar 等），root_dir 是要归档的目录。

### single_choice · None



- [A] 根据归档文件扩展名自动选择格式并解压到指定目录
- [B] 把目录压缩成归档文件
- [C] 校验归档文件是否损坏
- [D] 列出归档文件中的内容清单

**参考答案**：0

**解析**：unpack_archive() 是 make_archive() 的逆操作，会根据 filename 的扩展名（如 .zip、.tar.gz）自动选择解压格式并解压到 extract_dir。
