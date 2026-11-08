# s1u8l3 把 Python 对象变成 JSON 文本，再把文本变回对象 / 把表格数据读进 Python 的第一把钥匙

> 来源 `content/lessons/s1u8l3.json`

## py.io.json

# py.io.json：把 Python 对象变成 JSON 文本，再把文本变回对象

> 一句话直觉：JSON（JavaScript Object Notation）是程序之间交换数据的“普通话”——不管你用 Python、JavaScript 还是 Go，大家都能读懂同一段 JSON 文本。学会 `json` 模块，你的程序就能把内存里的字典、列表保存到文件，或通过 HTTP 接口发给别人。

本讲假设你**零基础**，但目标是让你能写出**工程级**的 JSON 读写代码。全程只需要 Python 标准库，不需要安装任何东西。

---

## 1. JSON 是什么？为什么 Python 程序离不开它

JSON 是一种**文本格式**，用来表示结构化数据。它只有两种“复合结构”：

- **对象（object）**：用 `{}` 包裹的键值对，键必须是**双引号字符串**。
- **数组（array）**：用 `[]` 包裹的有序值列表。

以及四种基本值：字符串、数字、布尔值（`true`/`false`）、`null`。

```json
{
  "name": "Ada",
  "age": 36,
  "skills": ["math", "programming"],
  "active": true,
  "address": null
}
```

Python 标准库里的 `json` 模块负责两件事：

| 方向 | Python 对象 → JSON 文本 | JSON 文本 → Python 对象 |
|------|------------------------|------------------------|
| 字符串 | `json.dumps()` | `json.loads()` |
| 文件 | `json.dump()` | `json.load()` |

记忆口诀：**带 `s` 的跟字符串（string）打交道，不带 `s` 的跟文件（stream）打交道。**

关键类型映射（记不住没关系，工程里靠 `dumps`/`loads` 自动转换）：

| Python | JSON |
|--------|------|
| `dict` | object |
| `list` / `tuple` | array |
| `str` | string |
| `int` / `float` | number |
| `True` / `False` | true / false |
| `None` | null |

**结论 1**：JSON 只认这 6 类 Python 类型，其他类型（如 `datetime`、`set`、自定义对象）默认无法直接序列化，需要额外处理——这是后面第 4 节的重点。

---

## 2. 最小可用：`dumps` / `loads` 与 `dump` / `load`

先看最核心的四个函数，配合 `ensure_ascii=False`（保留中文）和 `indent=2`（美化输出）。

```python
import json

# Python 对象 -> JSON 字符串
data = {"name": "小明", "age": 18, "tags": ["Python", "JSON"]}
text = json.dumps(data, ensure_ascii=False, indent=2)
print(text)
# {
#   "name": "小明",
#   "age": 18,
#   "tags": [
#     "Python",
#     "JSON"
#   ]
# }

# JSON 字符串 -> Python 对象
back = json.loads(text)
print(back["name"], back["tags"][0])  # 小明 Python
print(type(back))                     # <class 'dict'>
```

文件读写也遵循同样的对称性：

```python
import json

# 写入文件：注意 encoding="utf-8"
with open("config.json", "w", encoding="utf-8") as f:
    json.dump({"theme": "dark", "font_size": 14}, f, ensure_ascii=False, indent=2)

# 读取文件
with open("config.json", "r", encoding="utf-8") as f:
    cfg = json.load(f)
print(cfg["theme"])  # dark
```

**结论 2**：`ensure_ascii=False` + `encoding="utf-8"` 是处理中文的黄金组合。默认 `ensure_ascii=True` 会把中文转成 `\uXXXX`，虽然仍是合法 JSON，但人不可读、体积也更大。

---

## 3. 反序列化安全：`loads` 只认 JSON，不执行代码

一个常见误区：以为 JSON 像 Python 的 `eval` 一样能执行任意表达式。**不是的。** JSON 是纯数据格式，解析器只认识 JSON 语法。

```python
import json

# 合法 JSON 才能被解析
print(json.loads('{"a": 1}'))       # {'a': 1}
print(json.loads('[1, 2, 3]'))       # [1, 2, 3]

# 下面的都会抛 json.JSONDecodeError：
for bad in ["{'a': 1}", "{a: 1}", "{'a': 1,}", "NaN"]:
    try:
        json.loads(bad)
    except json.JSONDecodeError as e:
        print(f"解析失败: {bad!r} -> {e.msg}")
```

注意第一行 `{'a': 1}`：这是 **Python 字典字面量**，但不是合法 JSON（JSON 的键必须用双引号）。很多人从 Python 源码里复制字典去调 `loads` 会失败，原因就在这。

**结论 3**：`json.loads` 只接受严格 JSON。这种严格性正是它的安全优势——它不会像 `eval` 那样执行任何代码，所以**可以安全地解析来自网络、来自用户的字符串**。

---

## 4. 处理“非标准”类型：`default`、`object_hook` 与 `JSONEncoder`

工程中你迟早会想把 `datetime`、`Decimal`、`UUID`、自定义对象塞进 JSON。`json` 模块默认会抛 `TypeError`。两种主流做法：

### 4.1 序列化：用 `default` 回调

```python
import json
from datetime import datetime, date
from decimal import Decimal

def default_handler(obj):
    """告诉 json 模块：遇到不认识的类型时怎么转。"""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()           # 转成 ISO 8601 字符串
    if isinstance(obj, Decimal):
        return str(obj)                  # 用字符串保存，避免 float 精度损失
    raise TypeError(f"无法序列化: {type(obj).__name__}")

payload = {
    "created_at": datetime(2024, 5, 1, 12, 0, 0),
    "price": Decimal("19.99"),
}
print(json.dumps(payload, default=default_handler, ensure_ascii=False))
# {"created_at": "2024-05-01T12:00:00", "price": "19.99"}
```

### 4.2 反序列化：用 `object_hook` 把字典“升级”回对象

```python
import json
from datetime import datetime

def object_hook(d):
    """每个 JSON object 解析后会被传入这里，可以做类型恢复。"""
    if "created_at" in d and isinstance(d["created_at"], str):
        d["created_at"] = datetime.fromisoformat(d["created_at"])
    return d

text = '{"created_at": "2024-05-01T12:00:00", "price": "19.99"}'
obj = json.loads(text, object_hook=object_hook)
print(obj["created_at"], type(obj["created_at"]))
# 2024-05-01 12:00:00 <class 'datetime.datetime'>
```

**结论 4**：`default` 负责“出”，`object_hook` 负责“回”。两者成对使用，才能实现自定义类型的无损往返。生产代码里更推荐把它们封装成 `JSONEncoder` / `JSONDecoder` 子类，方便复用。

---

## 5. 工程实践：原子写入、异常处理与流式处理

把 JSON 写配置、写缓存时，最怕程序中途崩溃导致文件半截损坏。稳妥做法是**先写临时文件，再原子替换**：

```python
import json, os, tempfile

def atomic_write_json(path: str, data) -> None:
    """原子地写 JSON：写入临时文件 -> fsync -> os.replace。"""
    directory = os.path.dirname(os.path.abspath(path)) or "."
    fd, tmp_path = tempfile.mkstemp(dir=directory, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())        # 确保数据真正落盘
        os.replace(tmp_path, path)      # 原子替换（POSIX / Windows 均支持）
    except BaseException:
        os.unlink(tmp_path)             # 出错清理临时文件
        raise

atomic_write_json("data.json", {"version": 1, "items": [1, 2, 3]})
print(open("data.json", encoding="utf-8").read())
```

读取时永远不要假设文件一定合法，要把 `JSONDecodeError` 和 `OSError` 分开捕获：

```python
import json

def load_json(path: str, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default                    # 文件不存在：返回默认值
    except json.JSONDecodeError as e:
        raise RuntimeError(f"{path} 不是合法 JSON：第 {e.lineno} 行") from e

print(load_json("missing.json", default={}))  # {}
```

**结论 5**：工程级 JSON 读写要关注三件事——**编码（UTF-8）**、**原子性（避免半截文件）**、**错误分类（缺文件 vs 格式错误）**。这三点决定了你的程序在生产环境里是否可靠。

---

## 6. 动手练习：写一个"配置读写小工具"

**任务**：实现一个模块 `config_store.py`，提供 `save_config(path, config)` 和 `load_config(path)` 两个函数（可直接复用上面第 5 节的 `atomic_write_json` 与 `load_json`）。

**要求**：

1. `config` 是一个字典，可能包含 `datetime` 类型的值；保存时用 ISO 8601 字符串，读取时还原为 `datetime`。
2. 保存时 `ensure_ascii=False, indent=2`，文件编码 UTF-8，且必须是原子写入。
3. `load_config` 遇到文件不存在返回空字典 `{}`，遇到格式错误抛出带行号的 `RuntimeError`。
4. 写一段 `if __name__ == "__main__":` 的自测代码：构造一个配置、保存、再读回、断言 `datetime` 字段类型正确。

**验收标准**：运行脚本不报错，且 `python -c "import json; json.load(open('demo_config.json', encoding='utf-8'))"` 能正常解析生成的文件。

**挑战加餐**：给 `save_config` 增加 ``if_exists`` 参数，支持 `"overwrite"`（默认）和 `"skip"` 两种行为，并写单元测试覆盖这两种情况。

完成这个练习，你就已经掌握了从零基础到生产可用的 JSON 技能。

```python
import json
import os
import tempfile
from datetime import datetime


def _default(obj):
    """序列化钩子：把 datetime 转成 ISO 8601 字符串。"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"无法序列化: {type(obj).__name__}")


def _object_hook(d):
    """反序列化钩子：把形如 ISO 8601 的字符串恢复成 datetime。"""
    if "created_at" in d and isinstance(d["created_at"], str):
        try:
            d["created_at"] = datetime.fromisoformat(d["created_at"])
        except ValueError:
            pass
    return d


def save_config(path, config):
    """原子写入 JSON 配置：先写临时文件，再 os.replace。"""
    directory = os.path.dirname(os.path.abspath(path)) or "."
    fd, tmp = tempfile.mkstemp(dir=directory, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(config, f, default=_default, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        os.unlink(tmp)
        raise


def load_config(path):
    """读取 JSON 配置：缺文件返回 {}，格式错抛 RuntimeError。"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f, object_hook=_object_hook)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as e:
        raise RuntimeError(f"{path} 不是合法 JSON：第 {e.lineno} 行") from e


if __name__ == "__main__":
    path = "demo_config.json"
    cfg = {"version": 1, "created_at": datetime(2024, 5, 1, 12, 0, 0), "tags": ["json", "demo"]}
    save_config(path, cfg)
    loaded = load_config(path)
    assert isinstance(loaded["created_at"], datetime), loaded["created_at"]
    assert loaded["tags"] == ["json", "demo"]
    print("OK:", loaded)
```

## py.io.csv

# py.io.csv：把表格数据读进 Python 的第一把钥匙

> **一句话直觉**：现实中 80% 的数据都以「逗号分隔的表格」形式存在，`csv` 模块就是 Python 标准库里把这种表格变成列表/字典、再写回文件的官方桥梁（standard library 的意思是不用 pip 安装，直接 `import` 就能用）。

---

## 0. 为什么是 CSV？先建立场景感

CSV = **Comma-Separated Values**（逗号分隔值）。它长得像这样：

```
name,age,city
Alice,30,Beijing
Bob,25,Shanghai
```

第一行通常叫**表头**（header），后面每行叫一条**记录**（record）。
Excel、数据库导出、日志、Kaggle 数据集，几乎都会给你一个 `.csv` 文件。

学完这一节，你能做到：**读 CSV → 处理数据 → 写回 CSV**，这是数据工程流水线（data pipeline）的第一步。

---

## 1. 最小可用：用 `csv.reader` 读取

`csv` 是标准库模块，直接 `import csv` 即可。`csv.reader(file_obj)` 返回一个**迭代器**（iterator），每次产出一行，值是字符串组成的列表。

```python
import csv

# 准备一个小文件（实际项目里通常是别人给你的）
with open("people.csv", "w", newline="", encoding="utf-8") as f:
    f.write("name,age,city\nAlice,30,Beijing\nBob,25,Shanghai\n")

# 关键点 1：必须用 newline="" 打开文件
# 关键点 2：encoding 显式指定，避免 Windows 下中文乱码
with open("people.csv", newline="", encoding="utf-8") as f:
    reader = csv.reader(f)
    for row in reader:
        print(row)   # 每行是一个 list[str]
```

输出：

```
['name', 'age', 'city']
['Alice', '30', 'Beijing']
['Bob', '25', 'Shanghai']
```

**三个必须记住的结论**：
1. 打开文件一定要写 `newline=""`。否则 Windows 上会出现空行，跨平台行为不一致。
2. 所有字段读出来都是 **`str`**。`'30'` 不是 `30`，需要自己 `int()` 转换。
3. `csv.reader` 是**惰性**的：不一次性把文件读进内存，所以千万行的 CSV 也能流式处理。

---

## 2. 更常用：用 `csv.DictReader` 按列名取值

`csv.reader` 的问题是：`row[0]`、`row[1]` 到底是哪一列？代码可读性差、易错。

`csv.DictReader`（字典读取器）会把**表头自动作为键**，每行变成一个 `dict`：

```python
import csv

with open("people.csv", newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)           # 默认把第一行当表头
    for row in reader:
        print(row["name"], int(row["age"]))  # 按列名取值，可读性飞升
```

输出：

```
Alice 30
Bob 25
```

> **工程建议**：只要文件有表头（99% 的情况），优先用 `DictReader`。列顺序变化时你的代码不用改。

---

## 3. 写回去：`csv.writer` 与 `csv.DictWriter`

读进来不是目的，处理完要**写出去**。

```python
import csv

# 方式 A：list 写出去
rows = [
    ["name", "age", "city"],
    ["Carol", 28, "Shenzhen"],
]
with open("out_list.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerows(rows)   # 一次写多行

# 方式 B：dict 写出去（推荐，配合 DictReader 使用最自然）
dict_rows = [
    {"name": "Carol", "age": 28, "city": "Shenzhen"},
    {"name": "Dave",  "age": 41, "city": "Hangzhou"},
]
with open("out_dict.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["name", "age", "city"])
    writer.writeheader()          # 显式写表头
    writer.writerows(dict_rows)
```

写完 `cat out_dict.csv` 你会看到：

```
name,age,city
Carol,28,Shenzhen
Dave,41,Hangzhou
```

---

## 4. 无痛处理「逗号、引号、换行」的坑：方言与转义

CSV 名字叫「逗号分隔」，但字段里**本身含逗号或换行**怎么办？标准做法是**用双引号包裹**该字段，内部的 `"` 用 `""` 转义。好消息是：`csv` 模块自动帮你处理，**你不需要手写正则**。

```python
import csv, io

# 构造一个含有逗号、双引号、换行的「脏」数据
raw = 'name,note\nAlice,"Hello, world"\nBob,"He said ""hi"""\n'
f = io.StringIO(raw)                   # 用内存字符串当文件，便于演示
for row in csv.reader(f):
    print(row)
```

输出：

```
['name', 'note']
['Alice', 'Hello, world']
['Bob', 'He said "hi"']
```

**结论**：不要把 CSV 当普通字符串用 `split(',')` 切——那会在含逗号的字段上直接爆炸。**永远用 `csv` 模块**。

如果你遇到区域差异（比如欧洲用 `;` 作分隔符），可以指定 `delimiter`：

```python
csv.reader(f, delimiter=";")          # 分号分隔
csv.reader(f, quoting=csv.QUOTE_ALL)   # 所有字段都加引号
```

---

## 5. 从脚本到工程：三个纪律

1. **上下文管理器**（context manager）：`with open(...)` 保证文件必被关闭，即使中途抛异常。
2. **显式编码**：`encoding="utf-8"` 是硬性要求。默认编码随操作系统变化，是要人命的 bug 源。
3. **类型转换显式化**：读出来全是 `str`，处理前必须转 `int`/`float`/`datetime`，且要考虑**空字段**的情况（用 `try/except` 或给默认值）。

```python
def safe_int(s, default=0):
    try:
        return int(s)
    except (ValueError, TypeError):
        return default

import csv
with open("people.csv", newline="", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        age = safe_int(row["age"])
        print(row["name"], age)
```

---

## 小结

| 需求 | 用法 |
|------|------|
| 按行列读 | `csv.reader(f)` → `list[str]` |
| 按列名读 | `csv.DictReader(f)` → `dict[str, str]` |
| 按行列写 | `csv.writer(f).writerows(rows)` |
| 按列名写 | `csv.DictWriter(f, fieldnames=...).writerows(...)` |
| 必写参数 | `open(..., newline="", encoding="utf-8")` |

---

## 动手练习

在你本地创建一个 `scores.csv`，内容如下（注意第 3 行 Alice 的 `score` 有引号，且 comments 里带逗号）：

```
name,score,comment
Alice,90,"Good, but late"
Bob,,absent
Carol,78,"Well done"
```

写一个脚本 `clean_scores.py`，完成：

1. 用 `csv.DictReader` 读入 `scores.csv`；
2. 把 `score` 字段里**空字符串视为 0**，其余转成 `int`；
3. 过滤掉 `comment` 中包含 `"absent"`（不区分大小写）的行；
4. 用 `csv.DictWriter` 写出到 `scores_clean.csv`，字段顺序保持 `name,score,comment`；
5. 打开输出文件，确认 `Alice` 的 `comment` 仍是 `Good, but late`（引号与逗号都被正确保留）。

**验收标准**：`scores_clean.csv` 中包含两行数据，字段值原样保留，`score` 是纯整数，没有空行、没有乱码。

**进阶挑战**：把练习改成「从命令行接收输入/输出文件路径」，用 `argparse` 或 `sys.argv` 传入。

```python
import csv
import io

# ---------- 1. 用内存字符串模拟一个 CSV 文件 ----------
raw = (
    'name,score,comment\n'
    'Alice,90,"Good, but late"\n'
    'Bob,,absent\n'
    'Carol,78,"Well done"\n'
)

# ---------- 2. 读取：DictReader 按列名访问 ----------
def safe_int(s, default=0):
    """把字符串安全地转成 int，空串/脏数据返回默认值。"""
    try:
        return int(s)
    except (ValueError, TypeError):
        return default

cleaned = []
reader = csv.DictReader(io.StringIO(raw))
for row in reader:
    row['score'] = safe_int(row['score'])
    # 过滤掉 comment 中包含 absent 的行（不区分大小写）
    if 'absent' in (row['comment'] or '').lower():
        continue
    cleaned.append(row)

print('清洗后:', cleaned)

# ---------- 3. 写入：DictWriter 按指定列顺序输出 ----------
buf = io.StringIO()
writer = csv.DictWriter(buf, fieldnames=['name', 'score', 'comment'])
writer.writeheader()
writer.writerows(cleaned)

print('---- 写回结果 ----')
print(buf.getvalue())

# ---------- 4. 真实文件读写示例 ----------
with open('demo_out.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=['name', 'score', 'comment'])
    w.writeheader()
    w.writerows(cleaned)

with open('demo_out.csv', newline='', encoding='utf-8') as f:
    for row in csv.reader(f):
        print('读回:', row)
```


---

## 本课题目

### single_choice · None



- [A] dumps 把 Python 对象序列化为 JSON 字符串，loads 把 JSON 字符串解析为 Python 对象
- [B] dumps 把 JSON 字符串解析为 Python 对象，loads 把 Python 对象序列化为 JSON 字符串
- [C] 两者都用于读写文件，dumps 写文件，loads 读文件
- [D] 两者都返回字典，只是输入类型不同

**参考答案**：0

**解析**：dumps 中 d 代表 dump to string，将 Python 对象转成 JSON 格式字符串；loads 中 l 代表 load from string，将 JSON 字符串解析回 Python 对象。文件和字符串版本要区分开。

### single_choice · None



- [A] {'a': 1, 'b': [True, None]}
- [B] {"a": 1, "b": [true, null]}
- [C] {"a": 1, "b": [True, None]}
- [D] 会抛出 TypeError

**参考答案**：1

**解析**：JSON 使用双引号作为字符串定界符，布尔真写作 true，空写作 null。dumps 会把 Python 的 True/None 分别转换成 true/null。

### single_choice · None



- [A] ValueError 的普通实例
- [B] json.JSONDecodeError（JSONDecodeError 是 ValueError 的子类）
- [C] TypeError
- [D] KeyError

**参考答案**：1

**解析**：json.loads 解析失败会抛 json.JSONDecodeError，它是 ValueError 的子类。所以捕获 ValueError 也能兜住，但精确类型是 JSONDecodeError。

### multi_choice · None



- [A] None
- [B] True
- [C] 字符串 'x'
- [D] 集合 {1, 2}
- [E] 元组 (1, 2)

**参考答案**：[0, 1, 2, 4]

**解析**：None、布尔、字符串可直接序列化。元组会被当作 JSON 数组处理，也可序列化。集合 set 不是 JSON 支持的类型，会抛 TypeError。

### multi_choice · None



- [A] dump 将对象写入文件类对象
- [B] dumps 返回一个字符串
- [C] 两者都接受 ensure_ascii 参数
- [D] dump 会直接把结果返回为字符串
- [E] dumps 必须传入文件对象

**参考答案**：[0, 1, 2]

**解析**：dump 写入文件对象，返回 None；dumps 返回字符串。两者共享 ensure_ascii、sort_keys、indent 等参数。dump 不返回字符串，dumps 也不需要文件对象。

### multi_choice · None



- [A] indent
- [B] sort_keys
- [C] ensure_ascii
- [D] default
- [E] encoding

**参考答案**：[0, 1, 2, 3]

**解析**：json.dumps 支持 indent、sort_keys、ensure_ascii、default、separators 等。encoding 是 json.dump/load 在处理文件时才涉及的概念，不是 dumps 的参数。

### multi_choice · None



- [A] JSON 的 object 对应 Python 的 dict
- [B] JSON 的 array 对应 Python 的 list
- [C] JSON 的 null 对应 Python 的 None
- [D] JSON 的 number 一定对应 Python 的 int
- [E] JSON 的 true/false 对应 Python 的 True/False

**参考答案**：[0, 1, 2, 4]

**解析**：object→dict，array→list，null→None，true/false→True/False 都正确。number 没有整型和浮点区分，可能解析为 int 或 float，带小数点的一定是 float，所以第四项错误。

### fill_blank · None



**参考答案**：["dumps", "json.dumps"]

**解析**：把 Python 对象序列化为字符串使用 json.dumps；如果写入文件对象才是 json.dump。

### fill_blank · None



**参考答案**：["load", "json.load"]

**解析**：从文件对象读取使用 json.load；从字符串读取才用 json.loads。

### code_reading · None



**参考答案**：[1, "a", null, true]

**解析**：json.dumps 默认不加空格，None 转成 null，True 转成 true，字符串用双引号，数字原样输出。得到 [1, "a", null, true]。

### code_reading · None



**参考答案**：输出 4，v 是 int 类型 3，加 1 得到 4

**解析**：JSON 中不带小数点的数字会被解析为 Python 的 int，所以 v 是 3（int），v + 1 得 4。若写成 3.0 则会解析为 float。

### scenario · None



**解析**：中文变转义是因为 ensure_ascii 默认为 True，设为 False 可保留原始中文字符；文件挤成一行是因为未设置缩进，设置 indent（如 2）可让输出带换行和缩进，便于人工阅读。写出到文件用 json.dump。

### single_choice · None



- [A] 一个列表 [1, 2, 3]
- [B] 一个字典 {'x': 1}
- [C] 一个集合 {1, 2, 3}
- [D] 一个字符串 'hello'

**参考答案**：2

**解析**：JSON 没有集合类型，json.dumps 遇到 set 会抛 TypeError: Object of type set is not JSON serializable。列表、字典、字符串都是可序列化类型。

### single_choice · None



- [A] int
- [B] float
- [C] str
- [D] Decimal

**参考答案**：1

**解析**：JSON 中没有独立的整型/浮点区分，数字带小数点会被解析为 Python 的 float。1.0 会被解析为 1.0（float），而不是 int。

### single_choice · None



- [A] load 接收文件对象，loads 接收字符串
- [B] load 接收字符串，loads 接收文件对象
- [C] 两者都可以接收文件对象，没有区别
- [D] load 只能解析列表，loads 只能解析字典

**参考答案**：0

**解析**：load（无 s）从文件类对象读取并解析；loads（有 s）从字符串解析。同理 dump 写文件对象，dumps 返回字符串。

### single_choice · None



- [A] ensure_ascii=False
- [B] indent=None
- [C] sort_keys=False
- [D] encoding='utf-8'

**参考答案**：0

**解析**：json.dumps 默认 ensure_ascii=True，把非 ASCII 字符转义。设置 ensure_ascii=False 可保留原始字符。encoding 不是 dumps 的参数。

### single_choice · None



- [A] {"b": 1, "a": 2}
- [B] {"a": 2, "b": 1}
- [C] {"a": 1, "b": 2}
- [D] 会抛出异常

**参考答案**：1

**解析**：sort_keys=True 会按键的字典序重新排列输出，所以 a 在 b 前面，值保持对应。注意不是按值排序，也不改变键值配对。

### single_choice · None



- [A] 指定输出 JSON 的默认缩进
- [B] 为无法直接序列化的对象提供一个转换函数
- [C] 设置解析 JSON 时的默认编码
- [D] 指定字典排序的默认规则

**参考答案**：1

**解析**：default 是一个函数，当遇到不能被默认序列化的对象时会被调用，返回可序列化的替代值，常用于处理 datetime、自定义类等。

### single_choice · None



- [A] list
- [B] tuple
- [C] dict
- [D] str

**参考答案**：0

**解析**：json.loads 遇到 JSON 数组会解析为 Python 的 list，而不是 tuple。JSON 没有元组概念。

### single_choice · None



- [A] 抛出 JSONDecodeError
- [B] 返回 {'a': 2}，后面的值覆盖前面的
- [C] 返回 {'a': 1}，前面的值优先
- [D] 返回 {'a': [1, 2]}

**参考答案**：1

**解析**：虽然标准 JSON 不建议出现重复键，但 Python 的 json 解析器默认不报错，后出现的同名键会覆盖前面的值，结果为 {'a': 2}。

### single_choice · None



- [A] open('data.csv', 'r')
- [B] open('data.csv', 'r', newline='')
- [C] open('data.csv', 'rb')
- [D] open('data.csv', 'r', encoding=None)

**参考答案**：1

**解析**：csv 模块文档建议以 newline='' 打开文件，这样才能正确处理嵌入的换行符，避免在 Windows 上出现多余空行。二进制模式返回 bytes，csv.reader 无法直接处理。

### single_choice · None



- [A] ['a', 'b', 'c'] 然后 ['1', '2', '3']
- [B] ['a,b,c'] 然后 ['1,2,3']
- [C] a b c 然后 1 2 3
- [D] ['a', 'b', 'c', '1', '2', '3']

**参考答案**：0

**解析**：csv.reader 逐行迭代，每行返回一个字符串列表，按逗号切分。因此会依次打印两个列表。

### multi_choice · None



- [A] reader 每行返回列表，DictReader 每行返回字典
- [B] 两者都把所有字段读成字符串
- [C] DictReader 会自动把首行当作表头，可用 fieldnames 参数覆盖
- [D] reader 支持通过 fieldnames 参数按列名取值

**参考答案**：[0, 1, 2]

**解析**：reader 返回列表，DictReader 返回字典且默认首行为表头；两者都不做类型转换。reader 没有 fieldnames 参数，这是 DictReader 的概念。

### multi_choice · None



- [A] 含有分隔符逗号的字段，如 'a,b'
- [B] 含有换行符的字段
- [C] 含有双引号的字段，如 'say "hi"'
- [D] 只含字母数字的普通字段，如 'abc'

**参考答案**：[0, 1, 2]

**解析**：默认 QUOTE_MINIMAL 策略下，含分隔符、引号或换行符的字段会被加引号；普通字段不加引号。

### multi_choice · None



- [A] 传入可写文件对象，且文件以 newline='' 打开
- [B] 用 writerow 写单行，用 writerows 写多行
- [C] 写入的每个元素应尽量是字符串，非字符串会按 str 转换后写出
- [D] writerow 会返回写入的字节数用于校验

**参考答案**：[0, 1, 2]

**解析**：writer 接受可写对象，建议 newline='' 打开；writerow/writerows 分别写单行和多行；非字符串会被 str 化。writerow 返回的是 writer 的返回值，通常为 None，不是字节数。

### multi_choice · None



- [A] 默认 quotechar 是双引号 "
- [B] 被引号包裹的字段内部可以包含分隔符
- [C] 两个连续的双引号表示一个转义的双引号
- [D] 字段一旦被引号包裹，读取结果一定是 bytes 类型

**参考答案**：[0, 1, 2]

**解析**：默认 quotechar 为双引号，引号内可含分隔符和换行符；内部的双引号通过重复双引号转义。读取结果依然是 str，不是 bytes。

### fill_blank · None



**参考答案**：["len", "len()"]

**解析**：len() 是内置函数，用来获取列表等容器的长度，常用来校验每行字段数。

### fill_blank · None



**参考答案**：["None", "none"]

**解析**：DictReader 对缺失字段默认填充 None，可通过 restval 参数修改默认值。

### code_reading · None



**参考答案**：Alice 90\nBob 85

**解析**：DictReader 以首行 name,score 作为键，逐行返回字典；打印 name 与 score 两列，字段值均为字符串。

### code_reading · None



**参考答案**：['a,b', 'c']

**解析**：第一个字段被双引号包裹，其中的逗号属于字段内容，不算分隔符，因此解析为 'a,b'，第二字段为 'c'。

### code_reading · None



**参考答案**：输出为 'x,y\r\n1,2\r\n'（默认行终止符是 \r\n，可能因平台略有差异）

**解析**：writer 默认使用 \r\n 作为行终止符，writerow 会把列表按逗号连接并追加终止符，因此缓冲区内容为两行加终止符。

### scenario · None



**解析**：应使用 csv 模块并以 newline='' 打开文件；可能的分隔符差异可用 csv.Sniffer 探测或允许配置 delimiter；首行为表头时用 DictReader（配合 quotechar 处理引用字段）；对列数不一致的脏行进行检查并跳过或记录，避免后续断言失败。

### single_choice · None



- [A] 所有字段都会被自动转换为对应的数值类型
- [B] 所有字段都是字符串，需要时须手动转换类型
- [C] 只有当字段含小数点时才转成 float
- [D] 空字段会被自动省略

**参考答案**：1

**解析**：csv.reader 不做任何类型推断，所有字段均为 str；数值转换需由使用者自行处理。空字段会保留为空字符串，不会省略。

### single_choice · None



- [A] 直接输出 a,b,c,d，逗号被当作分隔符
- [B] 自动为含逗号的字段加上双引号：a,"b,c",d
- [C] 抛出异常，字段中不允许出现分隔符
- [D] 把逗号替换成空格

**参考答案**：1

**解析**：csv.writer 默认 dialect 为 excel，遇到含分隔符、引号或换行符的字段会自动加引号转义，保证可被正确解析。

### single_choice · None



- [A] 用 csv.reader 后手动记录第一行作为索引
- [B] 使用 csv.DictReader，它把每行转为以表头为键的字典
- [C] 使用 csv.writer 并设置 fieldnames
- [D] 使用 csv.Sniffer 自动识别类型

**参考答案**：1

**解析**：csv.DictReader 会自动读取首行作为字段名，之后每行返回一个 dict，按列名取值更清晰。

### single_choice · None



- [A] [['1', '2'], ['3']]
- [B] [['1', '2'], ['3', '']]
- [C] [['1', '2', '3']]
- [D] 抛出异常，因为列数不一致

**参考答案**：0

**解析**：csv.reader 不要求各行字段数相同，第二行只有一个字段就返回单元素列表，不会补空字符串，也不报错。

### single_choice · None



- [A] writer.header()
- [B] writer.writeheader()
- [C] writer.write_header()
- [D] writer.start()

**参考答案**：1

**解析**：DictWriter 提供 writeheader() 方法，按 fieldnames 顺序写出表头行。

### single_choice · None



- [A] dialect 只能使用内置的 'excel'，无法自定义
- [B] 可以在调用 reader/writer 时通过关键字参数覆盖该 dialect 的部分格式，如 delimiter
- [C] fmtparams 只对 writer 生效，对 reader 无效
- [D] 自定义 dialect 必须继承 csv.Dialect 且不能注册

**参考答案**：1

**解析**：reader/writer 接受 fmtparams（如 delimiter、quotechar），会覆盖所选 dialect 中的对应设置；自定义 dialect 可继承 csv.Dialect 并注册使用。

### single_choice · None



- [A] csv.reader(f, delimiter=';')
- [B] csv.reader(f).set_delimiter(';')
- [C] csv.reader(f, sep=';')
- [D] csv.reader(f, quotechar=';')

**参考答案**：0

**解析**：分隔符通过 delimiter 关键字参数指定。sep 是 pandas 的参数，quotechar 用于引用符，都不正确。

### single_choice · None



- [A] 必须手动在每行末尾加 
  
- [B] writerow 会自动添加行终止符（默认 \r
  ），不需要手动加换行
- [C] writerow 不会添加任何终止符，需配合 print 使用
- [D] 必须使用 newline='
  ' 打开文件才正确

**参考答案**：1

**解析**：writer 会按 dialect 的 lineterminator 自动在每行结尾添加终止符，默认是 \r\n，所以打开文件时应使用 newline='' 以避免重复换行。
