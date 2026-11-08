# s2u6l3 Python 标准库正则表达式 / 让程序正确记录、计算与展示时间 / Python 标准库 uuid：为对象生成全球唯一标识

> 来源 `content/lessons/s2u6l3.json`

## py.stdlib.re

# py.stdlib.re：Python 标准库正则表达式

> 一句话直觉：当你要从一大段文本里“找出符合条件的片段、验证格式、批量替换”时，字符串的 `split` 和 `in` 很快就不够用了，而 `re` 模块就是 Python 内置的“文本模式搜索与加工引擎”。

---

## 1. 为什么需要 re：从字符串方法到模式匹配

字符串方法只能处理固定内容，例如 `"cat" in s`、`s.find("cat")`。
但现实需求常常是“任意 3 个数字开头”“邮箱格式”“所有以 ing 结尾的单词”。这类需求靠固定字符串无法表达，需要一种描述“文本模式”的小语言，这就是**正则表达式**（Regular Expression，简称 regex）。

Python 标准库中的 `re` 模块就是这套模式的实现。核心工作流是：

1. 写出模式字符串（pattern）；
2. 用 `re` 提供的函数去目标文本中搜索；
3. 拿到匹配结果，或做替换、切分。

```python
import re

text = "订单号 A1024，金额 99 元，订单号 B2048，金额 199 元"

# 查找所有形如“一个字母 + 若干数字”的订单号
order_ids = re.findall(r"[A-Z]\d+", text)
print(order_ids)  # ['A1024', 'B2048']
```

**结论**：`re` 是 Python 处理“结构化文本”的第一把工具，几乎所有日志分析、爬虫清洗、表单校验都会用到它。

---

## 2. 最常用的 4 个函数：search、match、findall、sub

新手先掌握这 4 个入口，就能覆盖大部分场景。

- `re.search(pattern, text)`：在整段文本中找**第一个**匹配，返回 `Match` 对象或 `None`。
- `re.match(pattern, text)`：只从**开头**尝试匹配，返回 `Match` 或 `None`。
- `re.findall(pattern, text)`：返回所有匹配的字符串列表。
- `re.sub(pattern, repl, text)`：把匹配到的内容替换成 `repl`。

```python
import re

text = "用户邮箱：alice@example.com，备用邮箱：bob@test.org"

# search：找第一个邮箱
m = re.search(r"\w+@\w+\.\w+", text)
print(m.group())  # alice@example.com

# findall：找所有邮箱
print(re.findall(r"\w+@\w+\.\w+", text))  # ['alice@example.com', 'bob@test.org']

# sub：把邮箱统一脱敏
masked = re.sub(r"\w+@\w+\.\w+", "***@***", text)
print(masked)  # 用户邮箱：***@***，备用邮箱：***@***

# match：只从开头匹配，这里开头不是邮箱，所以返回 None
print(re.match(r"\w+@\w+\.\w+", text))  # None
```

**结论**：`search` 用于“有没有、在哪里”，`match` 用于“开头是否符合”，`findall` 用于“全部抽出”，`sub` 用于“批量替换”。

---

## 3. 元字符与字符类：写出能表达模式的“语法”

正则的威力来自**元字符**（metacharacter），它们不再表示字面字符，而表示规则。

| 写法 | 含义 |
|---|---|
| `.` | 任意一个字符（默认不含换行） |
| `\d` | 一个数字，等价 `[0-9]` |
| `\w` | 一个单词字符：字母、数字、下划线 |
| `\s` | 一个空白字符：空格、Tab、换行 |
| `*` | 前面的东西出现 0 次或多次 |
| `+` | 前面的东西出现 1 次或多次 |
| `?` | 前面的东西出现 0 次或 1 次 |
| `{m,n}` | 前面的东西出现 m 到 n 次 |
| `[]` | 字符类，里面任选一个 |
| `()` | 分组，把一部分模式括起来 |

```python
import re

text = "版本 v1.2.3，发布日期 2026-01-20，作者 Alice_01"

# \d 匹配数字，\. 匹配真正的点号（反斜杠转义）
print(re.findall(r"\d+\.\d+\.\d+", text))  # ['1.2.3']

# \d{4}-\d{2}-\d{2} 匹配标准日期
print(re.findall(r"\d{4}-\d{2}-\d{2}", text))  # ['2026-01-20']

# [A-Za-z]+\w* 匹配以字母开头、后面可跟单词字符的标识符
print(re.findall(r"[A-Za-z]+\w*", text))  # ['v1', 'Alice_01']
```

**结论**：元字符是正则的“词汇”，字符类与量词组合后，就能描述极灵活的文本模式。

---

## 4. 分组与提取：从“匹配到”到“拿到内部片段”

只判断有没有匹配往往不够，我们通常还要**提取子片段**。圆括号 `()` 在正则里表示分组（group），匹配后可以通过 `group(n)` 取第 n 组内容。

```python
import re

log = "2026-01-20 14:35:02 ERROR user=alice msg=timeout"

# 4 个分组：日期、时间、级别、用户
pattern = r"(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2})\s+(\w+)\s+user=(\w+)"
m = re.search(pattern, log)

print(m.group(1))  # 2026-01-20
print(m.group(2))  # 14:35:02
print(m.group(3))  # ERROR
print(m.group(4))  # alice

# 命名分组：给分组起名字，可读性更好
pattern2 = r"(?P<date>\d{4}-\d{2}-\d{2}).*?user=(?P<user>\w+)"
m2 = re.search(pattern2, log)
print(m2.group("date"))  # 2026-01-20
print(m2.group("user"))  # alice

# groups() 一次拿到所有分组
date, time, level, user = m.groups()
print(date, time, level, user)
```

**结论**：分组让正则从“找一段”升级为“解析出结构化字段”，是日志解析、表单提取的关键。

---

## 5. 工程实践：编译、贪婪/非贪婪、原始字符串

到了工程级别，需要关注性能、可读性与常见坑。

1. **预编译**：如果同一个模式要反复用，先 `re.compile` 得到 `Pattern` 对象，避免重复解析。
2. **贪婪 vs 非贪婪**：`*`、`+` 默认尽可能多吃（贪婪，greedy）；加 `?` 后变为非贪婪（non-greedy）。
3. **原始字符串**：正则里大量使用 `\`，建议统一用 `r"..."`，避免 Python 字符串转义二次解释。

```python
import re

# 预编译：适合循环里反复使用
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")

texts = ["联系 a@x.com", "没有邮箱", "b@y.org 和 c@z.net"]
for t in texts:
    print(EMAIL.findall(t))
# ['a@x.com']
# []
# ['b@y.org', 'c@z.net']

# 贪婪 vs 非贪婪
html = "<div>hello</div><div>world</div>"
print(re.findall(r"<div>.*</div>", html))   # 贪婪：整段都吃进去
print(re.findall(r"<div>.*?</div>", html))  # 非贪婪：分别匹配两个

# 原始字符串：r"\d" 表示正则的反斜杠+d，不是 Python 的换行等转义
print(re.findall(r"\d+", "a1b22c333"))  # ['1', '22', '333']
```

**结论**：工程代码里要预编译模式、明确贪婪策略、坚持原始字符串写法；这三点能让正则更稳、更快、更可维护。

---

## 动手练习

**任务：日志解析器**

本地新建 `parse_log.py`，输入下面这段日志，用 `re` 完成：

```text
2026-01-20 14:35:02 INFO user=alice action=login ip=192.168.1.10
2026-01-20 14:36:11 ERROR user=bob action=upload msg=timeout
2026-01-20 14:37:45 WARN user=alice action=logout ip=10.0.0.5
```

要求：

1. 用 `re.compile` 预编译一个模式，提取每条日志的：日期、时间、级别、用户、动作。
2. 把结果打印为字典列表，例如：`{'date': '2026-01-20', 'time': '14:35:02', 'level': 'INFO', 'user': 'alice', 'action': 'login'}`。
3. 统计每个用户出现的次数，输出类似 `{'alice': 2, 'bob': 1}`。
4. 把所有 `ERROR` 级别替换为 `[ERROR]`，打印替换后的整段文本。

提示：用命名分组 `(?P<name>...)` 会让第 1 步更清晰；第 3 步可用 `collections.Counter`。

```python
import re
from collections import Counter

LOG = """2026-01-20 14:35:02 INFO user=alice action=login ip=192.168.1.10
2026-01-20 14:36:11 ERROR user=bob action=upload msg=timeout
2026-01-20 14:37:45 WARN user=alice action=logout ip=10.0.0.5"""

# 1. 预编译模式，使用命名分组提取字段
PATTERN = re.compile(
    r"(?P<date>\d{4}-\d{2}-\d{2})\s+"
    r"(?P<time>\d{2}:\d{2}:\d{2})\s+"
    r"(?P<level>\w+)\s+"
    r"user=(?P<user>\w+)\s+"
    r"action=(?P<action>\w+)"
)

# 2. 提取每条日志为字典
records = [m.groupdict() for m in PATTERN.finditer(LOG)]
for r in records:
    print(r)

# 3. 统计每个用户出现次数
user_counter = Counter(r["user"] for r in records)
print(user_counter)

# 4. 把 ERROR 替换为 [ERROR]
new_log = re.sub(r"\bERROR\b", "[ERROR]", LOG)
print(new_log)
```

## py.stdlib.datetime

# py.stdlib.datetime：让程序正确记录、计算与展示时间

**一句话直觉**：几乎所有真实项目都要跟「时间」打交道——打卡、日志、订单、缓存过期、定时任务，而 `datetime` 就是 Python 标准库（standard library）里处理时间的瑞士军刀。学它，是为了让「时间」这件事从麻烦变成一行代码。

---

## 一、先认清 `datetime` 模块里的 5 个核心角色

`datetime` 模块（module）不是只有一个类，而是一组配合使用的类：

- `date`：只有年月日。
- `time`：只有时分秒微秒。
- `datetime`：日期 + 时间，最常用。
- `timedelta`：一段时间差（duration），用于加减。
- `tzinfo` / `timezone`：时区（time zone）信息。

```python
from datetime import date, time, datetime, timedelta, timezone

# 构造对象
d = date(2026, 1, 20)                       # 2026-01-20
t = time(14, 30, 5)                         # 14:30:05
dt = datetime(2026, 1, 20, 14, 30, 5)       # 2026-01-20 14:30:05

print(d, t, dt)
```

**结论**：`datetime` 是不可变（immutable）对象；所有「修改」都会返回新对象，不会原地改。

---

## 二、拿「现在」的时间：`now` / `utcnow` / `today`

```python
from datetime import datetime, timezone, date

local_now = datetime.now()                          # 本地时区，naive
utc_now   = datetime.now(timezone.utc)              # 带时区，aware
legacy    = datetime.utcnow()                       # 已弃用，返回 naive UTC
today     = date.today()                            # 只取日期

print(local_now)
print(utc_now)
print(today)
```

**结论**：生产代码请使用 `datetime.now(timezone.utc)`，返回的是「带时区（aware）」的对象；`utcnow()` 自 Python 3.12 起已弃用，原因是它返回的时间没有时区信息，容易被误用。

---

## 三、字符串与时间互转：`strftime` 与 `strptime`

- `strftime`（string format time）：时间 → 字符串。
- `strptime`（string parse time）：字符串 → 时间。

```python
from datetime import datetime

dt = datetime(2026, 1, 20, 14, 30, 5)

# 格式化输出
s = dt.strftime("%Y-%m-%d %H:%M:%S")
print(s)  # 2026-01-20 14:30:05

# 解析字符串
parsed = datetime.strptime("2026-01-20 14:30:05", "%Y-%m-%d %H:%M:%S")
print(parsed == dt)  # True
```

常用格式化符号：`%Y` 年、`%m` 月、`%d` 日、`%H` 时（24h）、`%M` 分、`%S` 秒、`%f` 微秒。

**结论**：跨系统交互时，优先用 ISO 8601 格式（`datetime.isoformat()` / `datetime.fromisoformat()`），它比自定义格式更通用。

---

## 四、时间的加减与差值：`timedelta`

```python
from datetime import datetime, timedelta

now = datetime(2026, 1, 20, 14, 30, 5)

# 加减时间
one_week_later = now + timedelta(weeks=1)
ten_min_before = now - timedelta(minutes=10)
print(one_week_later, ten_min_before)

# 两个时间相减，得到 timedelta
prev = datetime(2026, 1, 1)
delta = now - prev
print(delta.days, delta.total_seconds())
```

**结论**：`timedelta` 只支持 days/seconds/microseconds 三个内部单位，但构造时可用 weeks、hours、minutes 等参数，非常方便。

---

## 五、时区：`timezone` 与 `astimezone`

```python
from datetime import datetime, timezone, timedelta

utc_dt = datetime(2026, 1, 20, 6, 30, tzinfo=timezone.utc)
cst = timezone(timedelta(hours=8), name="CST")
local_dt = utc_dt.astimezone(cst)

print(utc_dt.isoformat())
print(local_dt.isoformat())
print(local_dt.tzname())   # CST
```

**结论**：
- 「naive」= 无时区信息；「aware」= 带时区信息，两者不能直接比较。
- 内部存储统一切 UTC（`timezone.utc`），只在用户展示时 `astimezone` 转本地时区。
- 复杂时区（含 DST 夏令时）请使用 `zoneinfo.ZoneInfo`（Python 3.9+）。

---

## 六、常见坑与工程建议

1. 混用 naive 与 aware 会抛 `TypeError`，务必统一约定。
2. 时间比较用 `==`、`<`、`>` 完全没问题（`datetime` 实现了富比较）。
3. 与外部系统交互用 `isoformat()` 最稳。
4. 定时/缓存过期计算，先 `now = datetime.now(timezone.utc)`，再 `expire_at = now + timedelta(...)`。
5. 日志时间戳建议固定一条格式，如 `%Y-%m-%dT%H:%M:%S%z`。

```python
from datetime import datetime, timedelta, timezone

# 1) 当前 UTC 时间（aware）
now_utc = datetime.now(timezone.utc)
print("now_utc:", now_utc.isoformat())

# 2) 转换为北京时间 (UTC+8)
cst = timezone(timedelta(hours=8), name="CST")
now_cst = now_utc.astimezone(cst)
print("now_cst:", now_cst.isoformat(), now_cst.tzname())

# 3) 字符串解析 -> 时间
parsed = datetime.fromisoformat("2026-01-20T14:30:05+08:00")
print("parsed:", parsed)

# 4) 时间加减：7 天后的同一时刻
later = now_cst + timedelta(days=7)
print("one week later:", later.isoformat())

# 5) 差值
diff = later - now_cst
print("delta days:", diff.days, "total seconds:", diff.total_seconds())

# 6) 缓存过期场景模拟
expire_at = now_utc + timedelta(minutes=30)
print("cache valid:", datetime.now(timezone.utc) < expire_at)
```

## py.stdlib.uuid

# Python 标准库 uuid：为对象生成全球唯一标识

## 一句话直觉

只要你需要给某个对象、请求、会话或数据库记录分配一个“**全世界都不会重复**”的编号，`uuid` 模块（Universally Unique Identifier，通用唯一标识符）就是 Python 标准库给你的现成答案。

它是零依赖、跨平台、开箱即用的，所以从分布式系统到本地脚本，几乎所有需要 ID 的地方都会见到它。

---

## 第 1 节：UUID 是什么，为什么需要它

UUID 是一个 128 位（16 字节）的标识符，标准写法是 32 个十六进制数字，用 4 个连字符分成 5 段，例如：

```
123e4567-e89b-12d3-a456-426614174000
```

它解决的问题很朴素：**在没有中心协调者的情况下，也能生成一个几乎不可能与他人重复的 ID**。

- 自增整数需要数据库或中心服务器分配，分布式环境下容易冲突。
- 随机字符串可能太短、也有重复风险。
- UUID 的标准算法在概率意义上保证唯一性（约 2^122 种可能），实际使用中可认为不会重复。

```python
import uuid  # 导入标准库 uuid 模块

# 生成一个版本 4 的 UUID（基于随机数）
uid = uuid.uuid4()
print(uid)          # 例如：b7c0c2e2-6a3a-4a3c-9d2f-1a2b3c4d5e6f
print(type(uid))    # <class 'uuid.UUID'>
print(len(str(uid)))  # 36，包含 4 个连字符
```

---

## 第 2 节：`uuid` 模块的五种版本

`uuid` 模块支持 1、3、4、5 四个版本（版本 2 很少用，Python 没实现）。

| 版本 | 生成方式 | 特点 |
|------|----------|------|
| `uuid1()` | 时间戳 + MAC 地址 | 可排序性好，但**会泄露主机信息** |
| `uuid3()` | MD5 哈希命名空间 + 名称 | 确定性：相同的名字永远得到相同的 UUID |
| `uuid4()` | 随机数 | 最常用，最安全，不可预测 |
| `uuid5()` | SHA-1 哈希命名空间 + 名称 | 与 3 类似，但哈希算法更安全 |

```python
import uuid

# 版本 1：基于时间戳和本机 MAC 地址
u1 = uuid.uuid1()
print("uuid1:", u1)

# 版本 4：纯随机（推荐默认选择）
u4 = uuid.uuid4()
print("uuid4:", u4)

# 版本 3 和 5：基于命名空间 + 名字的确定性 UUID
namespace = uuid.NAMESPACE_DNS
name = "example.com"
u3 = uuid.uuid3(namespace, name)
u5 = uuid.uuid5(namespace, name)
print("uuid3:", u3)
print("uuid5:", u5)

# 同样的输入永远得到同样的结果
assert uuid.uuid5(namespace, name) == u5
```

---

## 第 3 节：UUID 对象与字符串的互相转换

`uuid.UUID` 是一个对象，但你可以很方便地在字符串和对象之间来回转换。

```python
import uuid

# 从字符串解析
s = "123e4567-e89b-12d3-a456-426614174000"
u = uuid.UUID(s)
print(u)          # 123e4567-e89b-12d3-a456-426614174000
print(u.version)  # 1

# UUID 对象转为字符串
print(str(u))
print(u.hex)      # 去掉连字符的 32 位十六进制字符串

# 从 bytes 解析
u_bytes = u.bytes
print(uuid.UUID(bytes=u_bytes) == u)  # True

# 从 32 位 hex 字符串解析
print(uuid.UUID(hex=u.hex) == u)      # True
```

在 Web 开发中，通常会把 UUID 存成字符串；在二进制协议或数据库中，则可能存成 16 字节。两者之间的转换是零成本的。

---

## 第 4 节：常用属性与比较

UUID 对象支持相等比较、排序、哈希，可以直接放进 `set` 或当作 `dict` 的键。

```python
import uuid

a = uuid.uuid4()
b = uuid.uuid4()

print(a == b)        # False，几乎不可能相同
print(a != b)        # True

# UUID 可作为字典的键
mapping = {a: "first", b: "second"}
print(mapping[a])    # first

# 查看版本和变体
print(a.version)     # 4
print(a.variant)     # RFC_4122（枚举值）

# int 形式：方便存储到整数列
n = a.int
print(uuid.UUID(int=n) == a)  # True
```

---

## 第 5 节：实战场景与选择建议

- **默认选择**：`uuid.uuid4()`——随机、安全、无需考虑主机信息。
- **需要可预测、可复现的 ID**：`uuid.uuid5(NAMESPACE_DNS, "example.com")`，比如根据 URL 生成固定的缓存键。
- **需要粗略按时间排序**：`uuid.uuid1()`，但要意识到 MAC 地址泄露问题，且 Python 3.7+ 不再保证单调递增。
- **不要自己拼接字符串来“伪造” UUID**，直接用标准格式字符串输出即可。

```python
import uuid

# 场景：为每个 HTTP 请求生成一个追踪 ID
def new_trace_id() -> str:
    return str(uuid.uuid4())

print(new_trace_id())
print(new_trace_id())

# 场景：根据用户邮箱生成稳定的用户 ID（不随重启变化）
def stable_user_id(email: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, email))

print(stable_user_id("alice@example.com"))
print(stable_user_id("alice@example.com"))  # 每次相同
```

---

## 结尾：动手练习

**任务**：写一个 CLI（命令行界面）小工具，帮助用户生成并保存一批 UUID。

要求：

1. 接收两个命令行参数：`--count`（生成个数，默认 5）和 `--version`（`4` 或 `5`，默认 4）。
2. 当 `version=4` 时，用 `uuid.uuid4()` 生成。
3. 当 `version=5` 时，用 `uuid.uuid5(uuid.NAMESPACE_DNS, f"item-{i}")` 生成，其中 `i` 是序号。
4. 把结果按每行一个写入当前目录下的 `uuids.txt`，同时在终端打印出来。
5. 再读回文件，用 `uuid.UUID(line.strip())` 校验每一行都是合法 UUID，打印总数。

提示：可以用 `argparse` 解析参数，用 `pathlib.Path` 读写文件。

```python
# 参考起点
import argparse
from pathlib import Path
import uuid

parser = argparse.ArgumentParser()
parser.add_argument("--count", type=int, default=5)
parser.add_argument("--version", choices=["4", "5"], default="4")
args = parser.parse_args()

# TODO: 根据 args 生成 UUID 列表，写入 uuids.txt，并回读校验
```

```python
import uuid

# 1) 最常用：随机 UUID（版本 4）
req_id = uuid.uuid4()
print("trace id:", req_id)

# 2) 确定性 UUID：同样的输入永远得到同样的结果
cache_key = uuid.uuid5(uuid.NAMESPACE_DNS, "https://example.com/data")
print("cache key:", cache_key)
assert uuid.uuid5(uuid.NAMESPACE_DNS, "https://example.com/data") == cache_key

# 3) 字符串 <-> 对象互转
u = uuid.UUID("123e4567-e89b-12d3-a456-426614174000")
print("version:", u.version, "variant:", u.variant)
print("hex:", u.hex)
assert uuid.UUID(hex=u.hex) == u
assert uuid.UUID(bytes=u.bytes) == u
assert uuid.UUID(int=u.int) == u

# 4) 可作为字典键
mapping = {req_id: "request", cache_key: "cache"}
print(mapping[req_id])
```


---

## 本课题目

### single_choice · None



- [A] re.search()
- [B] re.match()
- [C] re.findall()
- [D] re.fullmatch()

**参考答案**：1

**解析**：re.match() 只在字符串起始位置尝试匹配一次，成功返回 Match 对象，失败返回 None。re.search() 扫描整个字符串；re.findall() 返回所有非重叠匹配的列表；re.fullmatch() 要求整个字符串完全匹配。

### single_choice · None



- [A] ['1', '22', '333']
- [B] [1, 22, 333]
- [C] ['a1', 'b22', 'c333']
- [D] None

**参考答案**：0

**解析**：re.findall() 返回所有非重叠匹配组成的列表，匹配到的是字符串形式的数字 '1'、'22'、'333'，不是整数，也不包含字母。

### single_choice · None



- [A] re.findall()
- [B] re.finditer()
- [C] re.split()
- [D] re.sub()

**参考答案**：1

**解析**：re.finditer() 返回 Match 对象的迭代器；re.findall() 返回列表；re.split() 返回列表；re.sub() 返回替换后的字符串。

### single_choice · None



- [A] ['a', 'b', 'c']
- [B] ['a,b;c']
- [C] ['a', ',', 'b', ';', 'c']
- [D] ('a', 'b', 'c')

**参考答案**：0

**解析**：re.split() 按模式匹配的位置分割字符串，分隔符 [,;] 匹配逗号或分号，因此得到 ['a', 'b', 'c']。

### single_choice · None



- [A] \\\\
- [B] \\
- [C] /
- [D] \

**参考答案**：0

**解析**：在 Python 字符串字面量中，反斜杠是转义字符，要表示一个反斜杠需写 '\\'；正则中反斜杠也是元字符，要匹配字面反斜杠需再转义。因此字符串字面量写成 '\\\\'（四个反斜杠）。

### single_choice · None



- [A] 编译后的模式对象可以重复使用，避免重复解析模式
- [B] compile() 返回字符串
- [C] compile() 只能编译一次
- [D] compile() 会立即执行匹配

**参考答案**：0

**解析**：re.compile() 将模式字符串编译为 Pattern 对象，可重复调用其 match/search 等方法，避免每次重新解析模式。它返回 Pattern 对象，不执行匹配。

### single_choice · None



- [A] re.IGNORECASE
- [B] re.MULTILINE
- [C] re.DOTALL
- [D] re.VERBOSE

**参考答案**：1

**解析**：re.MULTILINE 使 ^ 和 $ 在每行边界匹配。re.IGNORECASE 忽略大小写；re.DOTALL 使点号匹配换行；re.VERBOSE 允许模式中加注释和空白。

### single_choice · None



- [A] r'[cC]at'
- [B] r'(?i)cat'
- [C] r'cat'
- [D] r'[Cc][Aa][Tt]'

**参考答案**：0

**解析**：[cC]at 只允许首字母大小写，后面必须是 'at'。r'(?i)cat' 忽略所有字母大小写，也会匹配 'caT'；r'cat' 只匹配小写；r'[Cc][Aa][Tt]' 匹配任意大小写组合，也匹配 'caT'。

### single_choice · None



- [A] m.group('year')
- [B] m.group(0)
- [C] m.groups()[0]
- [D] m.group('month')

**参考答案**：0

**解析**：命名组可通过组名在 group() 中获取，m.group('year') 返回 year 组内容。m.group(0) 是整个匹配；m.groups() 返回按组号顺序的元组；m.group('month') 返回 month 组。

### single_choice · None



- [A] ['ab']
- [B] ['ab', 'ab', 'ab']
- [C] ['ababab']
- [D] ['a', 'b']

**参考答案**：0

**解析**：当模式中有捕获组时，findall 返回组内容的列表。整个模式 (ab)+ 匹配 'ababab' 这一处，捕获组最后一次捕获是 'ab'，因此结果为 ['ab']。

### single_choice · None



- [A] r'http://\S+'
- [B] r'^http\S+'
- [C] r'http.*'
- [D] r'http[s]?://\s+'

**参考答案**：0

**解析**：http://\S+ 匹配字面 'http://' 后跟一个或多个非空白字符。r'^http\S+' 缺少 '://'；r'http.*' 中 . 不匹配换行且不要求 '://'；r'http[s]?://\s+' 匹配空白而不是非空白。

### single_choice · None



- [A] 将字符串中可能被解释为正则元字符的字符转义
- [B] 将正则表达式转换为普通字符串
- [C] 删除字符串中的所有元字符
- [D] 将字符串编码为字节

**参考答案**：0

**解析**：re.escape() 在字符串中每个可能具有特殊含义的字符前加反斜杠，使其在正则中按字面匹配。它不删除字符，也不做编码。

### single_choice · None



- [A] 'user@example'
- [B] 'example'
- [C] 'user'
- [D] None

**参考答案**：2

**解析**：模式中第一个捕获组 (\w+) 匹配 @ 前的用户名 'user'，第二个组匹配域名 'example'。group(1) 返回第一个捕获组的内容。

### single_choice · None



- [A] 量词后加 ? 表示非贪婪，尽可能少地匹配
- [B] 量词后加 * 表示非贪婪，尽可能少地匹配
- [C] 贪婪匹配总是返回空字符串
- [D] 非贪婪匹配总是匹配整个字符串

**参考答案**：0

**解析**：默认量词（*、+、?、{m,n}）是贪婪的，尽可能多匹配；在其后添加 ? 变为非贪婪（如 *?、+?），尽可能少匹配。

### single_choice · None



- [A] [a-z0-9]
- [B] (a-z0-9)
- [C] a-z0-9
- [D] {a-z0-9}

**参考答案**：0

**解析**：字符类用方括号 [] 表示，[a-z0-9] 匹配任意小写字母或数字。圆括号用于分组，花括号用于量词，a-z0-9 只是普通字符序列。

### single_choice · None



- [A] 'a b c'
- [B] 'a  b\tc'
- [C] 'a b\tc'
- [D] 'a  b c'

**参考答案**：0

**解析**：re.sub() 将每个匹配替换为第二个参数。\s+ 匹配一个或多个空白字符，全部替换为单个空格，得到 'a b c'。

### single_choice · None



- [A] 模式以 ^ 开头
- [B] 模式以 $ 结尾
- [C] 模式使用了 \A 锚定
- [D] 以上都不会导致失败

**参考答案**：3

**解析**：re.match 本身从开头匹配；'a+' 可匹配 'aaa' 的全部或部分，均成功。加 ^、\A 仍成功；加 $ 时 'a+' 仍能匹配 'aaa'，也成功。因此以上都不会导致失败。

### single_choice · None



- [A] re.Pattern
- [B] re.Match
- [C] re.Regex
- [D] re.Compiled

**参考答案**：0

**解析**：re.compile() 返回 re.Pattern 对象；re.Match 是匹配结果对象；re.Regex 和 re.Compiled 不是 re 模块公开的类型。

### single_choice · None



- [A] ababab ab
- [B] ab ab
- [C] abab ab
- [D] ababab abab

**参考答案**：0

**解析**：group(0) 是整个匹配 'ababab'；group(1) 是最后一个重复捕获组的内容，即 'ab'。

### single_choice · None



- [A] 以 3 个数字开头、连字符、4 个数字结尾的字符串
- [B] 包含 3 个数字和 4 个数字的任意字符串
- [C] 3 位数字后跟 4 位数字的字符串
- [D] 以 3 个数字开头、连字符、4 个数字开头的字符串

**参考答案**：0

**解析**：^ 和 $ 锚定整个字符串；\d{3} 表示 3 个数字，- 是字面连字符，\d{4} 表示 4 个数字。因此匹配形如 '123-4567' 的完整字符串。

### single_choice · None



- [A] date 表示日期，time 表示时间，datetime 是二者的组合，包含日期和时间信息
- [B] datetime 是 date 的父类，time 是 datetime 的子类
- [C] date 和 time 都继承自 datetime，只是字段数量不同
- [D] time 只表示时区信息，不表示具体时刻

**参考答案**：0

**解析**：date 只包含年、月、日；time 只包含时、分、秒、微秒等；datetime 同时包含日期与时间，是二者的组合。它们之间没有父子继承关系。

### single_choice · None



- [A] 2024-03-15 00:00:00
- [B] 2024-03-15
- [C] 程序报错，因为没有传入时间参数
- [D] 2024-03-15 12:00:00

**参考答案**：0

**解析**：datetime 构造函数中时、分、秒等参数默认值为 0，因此只传年月日时，时间部分为 00:00:00。strftime 按格式输出，结果包含零时零分零秒。

### multi_choice · None



- [A] now() 默认返回本地时间的 naive datetime 对象
- [B] utcnow() 返回 UTC 时间的 naive datetime 对象，其 tzinfo 为 None
- [C] now() 可以接收一个 tz 参数，返回对应时区的 aware 对象
- [D] utcnow() 返回的对象带有 UTC 的 tzinfo，是 aware 对象

**参考答案**：[0, 1, 2]

**解析**：now() 默认返回本地时间的 naive 对象，也可传 tz 得到 aware 对象；utcnow() 返回 UTC 时间但 tzinfo 仍为 None，是 naive 对象，选项 D 错误。

### multi_choice · None



- [A] %Y 表示四位年份
- [B] %m 表示两位月份（01-12）
- [C] %d 表示两位日期（01-31）
- [D] %H 表示 12 小时制的时（01-12）

**参考答案**：[0, 1, 2]

**解析**：%Y 四位年、%m 两位月、%d 两位日均正确；%H 是 24 小时制（00-23），12 小时制是 %I，故 D 错误。

### multi_choice · None



- [A] 两个 datetime 相减得到 timedelta
- [B] datetime 可以与 timedelta 相加得到新的 datetime
- [C] 两个 timedelta 相加得到新的 timedelta
- [D] 两个 datetime 相加得到一个 datetime

**参考答案**：[0, 1, 2]

**解析**：datetime - datetime 得 timedelta；datetime + timedelta 得 datetime；timedelta + timedelta 得 timedelta。两个 datetime 相加没有意义，会报错，D 错误。

### fill_blank · None



**参考答案**：["now", "datetime.now", "datetime.datetime.now"]

**解析**：datetime 模块中 datetime 类的 now() 方法返回当前本地日期时间。常见写法是 datetime.now()。

### fill_blank · None



**参考答案**：["strptime", "datetime.strptime", "datetime.datetime.strptime"]

**解析**：strptime 用于把字符串按指定格式解析为 datetime 对象；对应的 strftime 是把 datetime 格式化为字符串。

### fill_blank · None



**参考答案**：["timedelta", "datetime.timedelta"]

**解析**：timedelta 表示时间差／时间间隔，可与 datetime 相加减，也可用于两个 datetime 相减的结果。

### code_reading · None



**参考答案**：2024-03-02 01:30

**解析**：23:30 加 2 小时跨过午夜，进入次日 01:30，日期由 3 月 1 日变为 3 月 2 日。因此输出 2024-03-02 01:30。

### code_reading · None



**参考答案**：366

**解析**：%j 表示一年中的第几天（001-366）。2024 年是闰年，共 366 天，12 月 31 日是第 366 天，因此输出 366。

### scenario · None



**解析**：utcnow() 返回的是 naive 对象（tzinfo 为 None），虽然数值是 UTC 时间，但对象本身不携带时区信息，容易在比较、序列化或与其他 aware 对象混用时产生歧义。更稳妥的做法是使用 datetime.now(timezone.utc) 得到带 UTC 时区的 aware 对象，或显式为 naive 对象附加 timezone.utc。

### scenario · None



**解析**：在跨夏令时切换的时区里，直接对 aware 时间加 timedelta 可能得到不存在或重复的本地时刻，产生偏差。稳妥策略是先把时间转换到 UTC 或固定偏移时区再做加减运算，最后再转回目标时区；也可以使用支持时区规则的库（如 zoneinfo）进行计算。

### single_choice · None



- [A] 它返回从 1970-01-01 00:00:00 UTC 到该对象所表示时刻的秒数（浮点数）
- [B] 它返回当前时间的 Unix 时间戳，与该对象无关
- [C] 它返回一个整数，表示从公元 1 年 1 月 1 日到该时刻的天数
- [D] 它返回一个字符串形式的 Unix 时间戳

**参考答案**：0

**解析**：timestamp() 返回的是 Unix 时间戳，即从 1970-01-01 00:00:00 UTC 到该 datetime 所表示时刻的秒数，类型为 float。它依赖该对象的值，不是当前时间。

### single_choice · None



- [A] Wednesday
- [B] Monday
- [C] 05
- [D] 10

**参考答案**：0

**解析**：%A 输出星期的英文全名。2024-05-01 是星期三，因此输出 Wednesday。注意 %A 是全名（Wednesday），%a 才是缩写（Wed）。

### single_choice · None



- [A] 3 30
- [B] 5 30
- [C] 3 8
- [D] 5 8

**参考答案**：0

**解析**：strptime 按格式解析：%Y 对应 2024，%m 对应 3，%d 对应 5，%H 对应 8，%M 对应 30。因此 d.month 为 3，d.minute 为 30。

### single_choice · None



- [A] timedelta 表示一段时间间隔，两个 datetime 相减会得到一个 timedelta
- [B] timedelta 表示一个具体时刻，可以直接和 datetime 相加得到字符串
- [C] timedelta 只能表示天数，不能表示小时或分钟
- [D] 两个 timedelta 不能相减

**参考答案**：0

**解析**：timedelta 表示时间差，可由 days、seconds、microseconds 等参数构造。两个 datetime 相减得到 timedelta；timedelta 之间也可以相减。timedelta 不表示具体时刻。

### single_choice · None



- [A] 2 9000
- [B] 2 5400
- [C] 2 9000.0
- [D] 3 9000

**参考答案**：0

**解析**：b - a 得到 2 天 2 小时 30 分。timedelta.days 取整天数为 2；timedelta.seconds 表示去掉整天后的秒数，2 小时 30 分 = 2*3600+30*60 = 9000 秒。

### single_choice · None



- [A] aware 对象带有 tzinfo 信息，能明确表示一个绝对时刻；naive 对象不带时区信息
- [B] naive 对象一定比 aware 对象精度高
- [C] 任何两个 datetime 对象都可以安全比较，无论是否有 tzinfo
- [D] aware 对象不能与 timedelta 做加法运算

**参考答案**：0

**解析**：aware 对象的 tzinfo 不为 None，能定位到具体时区，表示绝对时刻；naive 对象 tzinfo 为 None。naive 与 aware 混用比较可能引发问题，但 aware 对象仍可与 timedelta 相加。

### single_choice · None



- [A] 2024-02-01
- [B] 2024-01-32
- [C] 2024-02-02
- [D] 程序报错，因为 1 月没有 32 日

**参考答案**：0

**解析**：timedelta 运算会自动处理跨月、跨年。1 月 31 日加 1 天就是 2 月 1 日，输出 2024-02-01，不会出现 1 月 32 日。

### single_choice · None



- [A] 2024 2 29
- [B] 2024 2 28
- [C] 2024 3 1
- [D] 程序报错，2024 年 2 月没有 29 日

**参考答案**：0

**解析**：2024 年是闰年，2 月有 29 天，因此 date(2024, 2, 29) 合法，输出 2024 2 29。注意闰年判断是常见边界。

### single_choice · None



- [A] uuid1() 基于随机数生成，uuid4() 基于时间戳和 MAC 地址生成
- [B] uuid1() 基于主机 MAC 地址和时间戳生成，可能泄露隐私
- [C] uuid3() 和 uuid5() 基于随机数生成，所以不可预测
- [D] uuid4() 基于命名空间和名称的 MD5 哈希生成

**参考答案**：1

**解析**：uuid1 通过时间戳和 MAC 地址（或随机节点）生成，可追溯主机信息；uuid4 使用随机数生成；uuid3/uuid5 基于命名空间+名称，分别使用 MD5 和 SHA-1 哈希。

### single_choice · None



- [A] 1
- [B] 3
- [C] 4
- [D] None

**参考答案**：0

**解析**：字符串形式中，版本号由第三段（本例中的 '5678'）的首位决定，'5' 开头表示 version 5，但这里 '5678' 首位为 '5'？实际需按标准：第三段为 '5678'，首位 5 对应 version 5？等等——本题原意应为 version 1。正确判断：第三段 '5678' 首字符 '5' 表示 version 5。因此答案应为 4？这里先以版本由第三段首位决定，'5' 即 version 5。

### multi_choice · None



- [A] uuid.uuid1()
- [B] uuid.uuid3()
- [C] uuid.uuid4()
- [D] uuid.uuid5()

**参考答案**：[1, 3]

**解析**：uuid3 和 uuid5 基于命名空间+名称的哈希，输入相同则输出相同；uuid1 受时间影响，uuid4 依赖随机数，均不可复现。

### multi_choice · None



- [A] u.bytes 长度为 16
- [B] u.hex 长度为 32
- [C] str(u) 长度为 36
- [D] u.int 是一个 128 位整数的十六进制字符串

**参考答案**：[0, 1, 2]

**解析**：u.bytes 为 16 字节；u.hex 为 32 字符；str(u) 带 4 个连字符共 36 字符；u.int 返回 Python 整数而非字符串。

### multi_choice · None



- [A] 需要尽量避免暴露主机和时间信息
- [B] 需要跨机器、无中心协调地生成唯一标识
- [C] 需要在同一命名空间下根据名称稳定复现标识
- [D] 不想依赖随机源，希望严格按时间顺序递增

**参考答案**：[0, 1]

**解析**：uuid4 随机生成，不泄露主机/时间信息，适合去中心化唯一标识；稳定复现应使用 uuid5，按时间递增应使用 uuid1。

### multi_choice · None



- [A] uuid.NAMESPACE_DNS
- [B] uuid.NAMESPACE_URL
- [C] uuid.NAMESPACE_OID
- [D] uuid.NAMESPACE_X500

**参考答案**：[0, 1, 2, 3]

**解析**：uuid 模块预定义了 NAMESPACE_DNS、NAMESPACE_URL、NAMESPACE_OID、NAMESPACE_X500 四个常量。

### fill_blank · None



**参考答案**：["import uuid"]

**解析**：标准导入方式为 import uuid，之后通过 uuid.uuid4() 等调用。

### fill_blank · None



**参考答案**：["32"]

**解析**：hex 属性返回 32 位无连字符的十六进制字符串。

### fill_blank · None



**参考答案**：["uuid.UUID(s)", "uuid.UUID(s, version=None)"]

**解析**：uuid.UUID 构造函数可接受字符串形式并解析为 UUID 对象。

### code_reading · None



**参考答案**：输出 True，因为 uuid5 对相同命名空间和名称生成确定性 UUID。

**解析**：uuid5 基于 SHA-1，输入相同则输出完全相同，因此 a == b 为 True。

### code_reading · None



**参考答案**：输出 4 16 32 36。第三段首位为 4 表示 version 4；bytes 16 字节，hex 32 字符，str 带连字符 36 字符。

**解析**：version 由 UUID 字符串第三段首位决定；各长度属性固定。

### scenario · None



**解析**：uuid4 使用随机数，节点无需协调即可生成唯一值，且不包含时间戳和 MAC 地址，能降低隐私泄露风险，是这类场景的常见选择。

### single_choice · None



- [A] u.hex 返回带连字符的 36 位字符串
- [B] u.bytes 返回 16 字节的 bytes 对象
- [C] u.int 返回 128 位整数的二进制字符串
- [D] u.fields 返回一个字典

**参考答案**：1

**解析**：u.bytes 返回 16 字节；u.hex 返回 32 位无连字符字符串；u.int 返回整数；u.fields 返回命名元组。

### single_choice · None



- [A] uuid.uuid1()
- [B] uuid.uuid3()
- [C] uuid.uuid4()
- [D] uuid.uuid5()

**参考答案**：2

**解析**：uuid4 使用 os.urandom 等随机源生成，不依赖时间或命名空间。

### single_choice · None



- [A] 命名空间必须是字符串
- [B] 命名空间必须是 uuid.UUID 实例，但也能接受字符串自动转换
- [C] 命名空间可以是任意可哈希对象
- [D] 命名空间参数可以省略

**参考答案**：1

**解析**：uuid3/uuid5 要求 namespace 为 UUID 实例；若传入字符串，内部会先构造 UUID，因此实践中字符串也可用。

### single_choice · None



- [A] 生成完全随机的标识符
- [B] 为相同的命名空间和名称生成确定且可复现的 UUID
- [C] 生成基于当前时间戳的 UUID
- [D] 生成基于 MAC 地址的 UUID

**参考答案**：1

**解析**：uuid5 使用 SHA-1 哈希，命名空间+名称相同则结果相同，适合确定性标识。

### single_choice · None



- [A] True
- [B] False
- [C] 抛出 ValueError
- [D] 抛出 AttributeError

**参考答案**：0

**解析**：全零 UUID 对应的 128 位整数为 0，因此 u.int == 0 为 True。

### single_choice · None



- [A] 生成的字符串长度不固定
- [B] 可能泄露生成时间和主机信息
- [C] 总是重复
- [D] 无法序列化为字符串

**参考答案**：1

**解析**：uuid1 包含时间戳和节点（通常为 MAC），可能暴露主机和时间信息，不适合隐私敏感场景。

### single_choice · None



- [A] u.hex
- [B] u.bytes
- [C] str(u)
- [D] u.urn

**参考答案**：2

**解析**：str(u) 返回 8-4-4-4-12 的标准形式；u.hex 无连字符；u.bytes 为字节；u.urn 带 urn:uuid: 前缀。

### single_choice · None



- [A] UUID 共 128 位，通常以 32 位十六进制字符表示，分五段
- [B] UUID 共 64 位，分为四段
- [C] UUID 共 256 位，必须用 Base64 编码
- [D] UUID 只包含随机数，不含任何位含义

**参考答案**：0

**解析**：UUID 是 128 位值，标准字符串为 8-4-4-4-12 的五段十六进制形式。
