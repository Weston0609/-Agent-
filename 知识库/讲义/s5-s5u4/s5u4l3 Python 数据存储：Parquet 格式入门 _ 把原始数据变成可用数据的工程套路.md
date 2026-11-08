# s5u4l3 Python 数据存储：Parquet 格式入门 / 把原始数据变成可用数据的工程套路

> 来源 `content/lessons/s5u4l3.json`

## py.data.parquet

# Python 数据存储：Parquet 格式入门

## 一句话直觉

当你的数据从几行变成几百万行时，CSV 会变得又慢又占空间；**Parquet**（一种列式存储格式，columnar storage）就是为大数据而生的高效文件格式——它让读取更快、文件更小、还能保留数据类型。

---

## 1. 为什么需要 Parquet？从 CSV 的痛点说起

CSV（Comma-Separated Values，逗号分隔值）是最常见的表格存储格式，但它有三个致命问题：

1. **没有数据类型**：读回来全是字符串，需要手动转换。
2. **按行存储**：如果只想读某一列，也得把整行读进来。
3. **没有压缩**：文本冗余大，文件体积膨胀。

Parquet 的设计目标就是解决这三点：它记录每列的**数据类型（schema，模式）**、按**列（column）**存储、支持**高效压缩（compression）**。

```python
# 先感受一下 CSV 的“无类型”问题
import csv

with open("sample.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["id", "price", "sold_at"])
    writer.writerow([1, 9.99, "2024-01-01"])

with open("sample.csv") as f:
    rows = list(csv.reader(f))
print(rows[1])          # ['1', '9.99', '2024-01-01'] —— 全变成了字符串
print(type(rows[1][0])) # <class 'str'>，不是 int
```

---

## 2. Parquet 的核心概念：列式存储与 Schema

Parquet 是 **列式存储（columnar storage）**：同一列的数据物理上挨在一起。这有两个好处：

- **只读需要的列**：分析时常常只用几列，列存可以跳过其他列。
- **同列数据类型一致，压缩率极高**：例如整数列用 RLE（Run-Length Encoding，游程编码）压缩。

每个 Parquet 文件头部带有 **schema**，明确记录每列的名字和类型（int64、float64、string、timestamp 等），读取时不需要猜测。

```python
# 用 pandas 写一个 Parquet 文件并查看它的 schema
import pandas as pd

df = pd.DataFrame({
    "id": [1, 2, 3],
    "price": [9.99, 19.5, 3.2],
    "sold_at": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
})
df.to_parquet("sample.parquet", engine="pyarrow", index=False)

import pyarrow.parquet as pq
schema = pq.read_schema("sample.parquet")
print(schema)
# id: int64
# price: double
# sold_at: timestamp[ns]
```

---

## 3. 用 pandas + pyarrow 读写 Parquet

实践中最常用的组合是 **pandas**（做数据处理）加上 **pyarrow**（提供 Parquet 引擎）。安装一行命令搞定：

```bash
pip install pandas pyarrow
```

读写代码几乎和 CSV 一样简单，但得到了类型保真和压缩。

```python
import pandas as pd

# 写：index=False 避免把 DataFrame 行号也存进去
df.to_parquet("data.parquet", engine="pyarrow", compression="snappy", index=False)

# 读：只读需要的列，速度更快、内存更省
subset = pd.read_parquet("data.parquet", columns=["id", "price"])
print(subset.head())
print(subset.dtypes)  # 类型被完整保留：int64 / float64
```

`compression` 可选：`snappy`（默认，速度快）、`gzip`（压缩率高）、`zstd`（平衡）、`none`（不压缩）。

---

## 4. 列选择、过滤与分片：工程级用法

数据量再大一点，Parquet 的优势才真正显现。三个关键能力：

- **列裁剪（column pruning）**：`columns=[...]` 只加载用到的列。
- **谓词下推（predicate pushdown）**：`filters=[...]` 让引擎在读取时先过滤，减少 IO。
- **分区数据集（partitioned dataset）**：按某列分目录存储（如 `year=2024/month=01/`），读取时可跳过无关分区。

```python
import pandas as pd
import pyarrow.dataset as ds

# 假设有一个按日期分区的数据集目录：dataset/year=2024/month=01/part-0.parquet
# 用 pyarrow.dataset 只扫描需要的列和行

dataset = ds.dataset("dataset", format="parquet", partitioning=["year", "month"])

# 只读 id, price 两列，且 price > 5
scanner = dataset.scanner(columns=["id", "price"], filter=ds.field("price") > 5)
result = scanner.to_table().to_pandas()
print(result)
```

对于本地小文件也可以直接用 pandas 的 `filters` 参数：

```python
small = pd.read_parquet("data.parquet", columns=["id", "price"],
                        filters=[("price", ">", 5)])
print(small)
```

---

## 5. 如何选格式？CSV、Parquet、JSON 对比

| 维度 | CSV | JSON | Parquet |
|------|-----|------|---------|
| 类型保真 | 无 | 部分 | 完整 |
| 列裁剪 | 不支持 | 不支持 | 支持 |
| 压缩率 | 低 | 低 | 高 |
| 人可读 | 是 | 是 | 否（二进制） |
| 适用场景 | 交换/小数据 | 嵌套/配置 | 分析/大数据 |

经验法则：**跨系统交换或数据很小 → CSV/JSON；做分析或数据规模大 → Parquet。**

```python
import os, pandas as pd

df = pd.DataFrame({"a": range(100_000), "b": [i * 0.5 for i in range(100_000)]})
df.to_csv("big.csv", index=False)
df.to_parquet("big.parquet", index=False)

print("csv   :", os.path.getsize("big.csv"), "bytes")
print("parquet:", os.path.getsize("big.parquet"), "bytes")  # 通常小几倍甚至十倍
```

---

## 动手练习

**目标**：亲手感受 Parquet 的“类型保真 + 体积小 + 列裁剪快”。

1. 用 `pandas` 生成一个 50 万行的 DataFrame，列包含：
   - `user_id`：整数，0 到 499999
   - `age`：18 到 70 的随机整数
   - `score`：0 到 100 的随机浮点数
   - `signup`：随机日期（用 `pd.date_range` 生成）
2. 分别用 `to_csv` 和 `to_parquet`（`engine="pyarrow", compression="snappy"`）保存到本地，打印两个文件的大小并比较。
3. 用 `pd.read_parquet(..., columns=["user_id", "score"])` 只读两列，记录耗时；再读全部列，记录耗时，比较差异。
4. 用 `pq.read_schema` 打印 Parquet 的 schema，确认每列类型是否符合预期。
5. **进阶**：用 `pd.read_parquet(..., filters=[("age", ">=", 60)])` 筛选出 60 岁及以上的用户，打印他们的人数。

完成后请思考：如果这份数据要跨部门共享，你会选哪个格式？为什么？

---

## 小结

- **Parquet 是列式、带 Schema、可压缩**的高效数据格式。
- Python 里的标准组合是 **pandas + pyarrow**，读写接口与 CSV 一样简单。
- 工程级要点：**列裁剪、谓词下推、分区数据集**，让大数据读取变快。
- 选型原则：**交换用小文本格式，分析用 Parquet**。

## py.data.etl_patterns

# py.data.etl_patterns：把原始数据变成可用数据的工程套路

> 一句话直觉：**ETL（Extract-Transform-Load，抽取-转换-加载）就是把“脏、散、乱”的原始数据，通过一套可复用、可测试、可扩展的代码流程，变成干净、结构化、能直接喂给模型或数据库的数据。** 不学它，你就只能写一堆一次性脚本；学了它，你才能写出真正能在工程里跑起来的数据管道（data pipeline）。

前置说明：本讲假设你会写最基础的 Python（变量、函数、for 循环、字典、列表）。如果还没写过，请先完成 Python 官方教程的 3~5 章。

---

## 1. ETL 的心智模型：三个动作 + 一条流水线

ETL 拆开来看只有三件事：

- **Extract（抽取）**：从文件、数据库、API、日志里把原始数据读进来。
- **Transform（转换）**：清洗、过滤、补全、聚合、改字段名、改类型。
- **Load（加载）**：写到目标位置，比如 CSV、数据库、数据仓库、模型训练集。

工程上最重要的不是三步本身，而是把每一步写成**独立、可组合的函数**。这样你才能测试、复用、替换。

```python
# etl_step1_model.py
# 核心思想：把 E、T、L 各写成一个纯函数，输入输出都是 Python 原生数据结构

from typing import Iterable

def extract(raw_records: Iterable[dict]) -> list[dict]:
    """模拟从某个数据源抽取：这里直接接收一批原始记录"""
    return [dict(r) for r in raw_records]  # 复制一份，避免污染入参

def transform(records: list[dict]) -> list[dict]:
    """转换：去掉空行、把 age 转成 int、去掉首尾空格"""
    cleaned = []
    for r in records:
        if not r.get("name"):          # 过滤掉没有名字的记录
            continue
        r["name"] = r["name"].strip()  # 清洗字符串
        r["age"] = int(r.get("age", 0))  # 类型转换，默认 0
        cleaned.append(r)
    return cleaned

def load(records: list[dict]) -> str:
    """加载：这里用字符串表示“写出去”的结果，工程里可换成写 CSV/DB"""
    return "\n".join(f"{r['name']},{r['age']}" for r in records)

raw = [
    {"name": "  Alice ", "age": "30"},
    {"name": "",        "age": "25"},   # 这条会被过滤
    {"name": "Bob",     "age": "41"},
]

records = extract(raw)
records = transform(records)
print(load(records))
# 输出：
# Alice,30
# Bob,41
```

**关键结论**：先定义“数据在每一步长什么样”，再写代码。函数的输入输出都应该是普通 Python 对象（dict/list），不要一上来就绑死到某个数据库或某个框架。

---

## 2. 抽取（Extract）：把“不确定的输入”变成“确定的迭代器”

真实数据源很杂：CSV 文件、JSON 文件、日志文件、API、数据库。工程上最稳的做法是：**用生成器（generator）逐行读取**，而不是一次性 read 到内存。

Python 官方教程在第 9.9 节专门讲了生成器（Generators）。它的价值是：

- 内存友好：只处理当前这一行。
- 可组合：生成器可以像列表一样被 for 循环消费。
- 可流式：适合日志、大文件。

```python
# etl_step2_extract.py
import csv, io, json
from collections.abc import Iterator

def extract_csv(text: str) -> Iterator[dict]:
    """从 CSV 文本中逐行抽取成 dict"""
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        yield dict(row)   # 生成器：一次只吐一行，不占内存

def extract_json_lines(text: str) -> Iterator[dict]:
    """从 JSON Lines（每行一个 JSON 对象）中逐行抽取"""
    for line in text.splitlines():
        line = line.strip()
        if line:
            yield json.loads(line)

csv_text = "name,age\nAlice,30\nBob,41\n"
jsonl_text = '{"name": "Carol", "age": "28"}\n{"name": "Dave", "age": "35"}\n'

print(list(extract_csv(csv_text)))
print(list(extract_json_lines(jsonl_text)))
# 输出：
# [{'name': 'Alice', 'age': '30'}, {'name': 'Bob', 'age': '41'}]
# [{'name': 'Carol', 'age': '28'}, {'name': 'Dave', 'age': '35'}]
```

**关键结论**：抽取层用 `Iterator[dict]` 做统一接口。无论底层是 CSV 还是 JSONL，上层只看到一个“会吐 dict 的东西”。这就是工程上的**接口抽象**。

---

## 3. 转换（Transform）：组合小函数，而不是写大泥球

转换是 ETL 里最容易写乱的一步。工程上推荐：**把每个清洗动作写成一个可复用函数，再用组合（compose）串起来**。

注意：Python 的列表推导（List Comprehension，官方教程 5.1.3）非常适合写“一行一个动作”的转换。

```python
# etl_step3_transform.py
from collections.abc import Iterable, Callable

def drop_empty(records: Iterable[dict]) -> Iterable[dict]:
    """过滤掉关键字段为空的记录"""
    return (r for r in records if r.get("name"))

def strip_strings(records: Iterable[dict]) -> Iterable[dict]:
    """清洗所有字符串字段的首尾空格"""
    def clean(r: dict) -> dict:
        return {k: (v.strip() if isinstance(v, str) else v) for k, v in r.items()}
    return (clean(r) for r in records)

def to_int(records: Iterable[dict], field: str) -> Iterable[dict]:
    """把某个字段转为 int，转换失败则记为 0"""
    def convert(r: dict) -> dict:
        try:
            r[field] = int(r.get(field, 0))
        except (ValueError, TypeError):
            r[field] = 0
        return r
    return (convert(r) for r in records)

def compose(*fns: Callable[[Iterable[dict]], Iterable[dict]]):
    """把多个转换函数从左到右串起来"""
    def pipeline(records: Iterable[dict]) -> Iterable[dict]:
        for fn in fns:
            records = fn(records)
        return records
    return pipeline

raw = [
    {"name": "  Alice ", "age": "30"},
    {"name": "",        "age": "oops"},  # 会被 drop_empty 干掉
    {"name": " Bob  ",  "age": "abc"},   # age 会被转成 0
]

pipeline = compose(drop_empty, strip_strings, lambda rs: to_int(rs, "age"))
print(list(pipeline(raw)))
# 输出：
# [{'name': 'Alice', 'age': 30}, {'name': 'Bob', 'age': 0}]
```

**关键结论**：转换函数不要修改入参（注意上面 `clean` 用了新 dict），否则流水线会“互相污染”。每个函数只做一件事，测试就很容易：给一个小列表，断言输出。

---

## 4. 加载（Load）：把结果写成可验证的产物

加载层的关键是**幂等**：同样的输入，跑两次，结果一致，不会重复追加。工程上常见的做法：

- 写文件：CSV、JSONL、Parquet。
- 写数据库：先建唯一键（unique key），用 upsert 或先删后插。
- 写训练集：记录版本号、字段 schema、行数。

```python
# etl_step4_load.py
import csv, io
from collections.abc import Iterable

def load_to_csv(records: Iterable[dict], fields: list[str]) -> str:
    """把记录写成 CSV 字符串；保证列顺序固定，便于 diff、测试"""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fields)
    writer.writeheader()
    for r in records:
        writer.writerow({k: r.get(k, "") for k in fields})
    return buf.getvalue()

records = [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 0}]
print(load_to_csv(records, ["name", "age"]))
# 输出：
# name,age
# Alice,30
# Bob,0
```

**关键结论**：加载层要显式声明 schema（字段列表、字段类型）。schema 是数据管道与下游消费者之间的“契约（contract）”。

---

## 5. 把三层串起来：一条最小可用的 ETL 管道

现在把前面所有东西组合起来。这就是一个完整的、可测试的、可扩展的 ETL 管道（pipeline）。

```python
# etl_step5_pipeline.py
def run_etl(raw_text: str) -> str:
    """一条最小可用 ETL 管道：CSV 文本 → 清洗 → CSV 文本"""
    records = extract_csv(raw_text)          # Extract
    records = drop_empty(records)            # Transform
    records = strip_strings(records)
    records = to_int(records, "age")
    return load_to_csv(records, ["name", "age"])  # Load

print(run_etl("name,age\n  Alice ,30\n,25\nBob,abc\n"))
# 输出：
# name,age
# Alice,30
# Bob,0
```

**关键结论**：管道（pipeline）本身也应该是一个函数。输入是原始数据，输出是最终产物。中间每一步都可以单独测试。

---

## 常见误区

- 把 E、T、L 揉在一个 200 行的脚本里 —— 无法测试、无法复用、无法定位错误。
- 在转换函数里**原地修改入参 dict** —— 上游数据被污染，下游拿到的是“被改过的历史”。
- 一次性 `read()` 整个文件到内存 —— 大数据量直接 OOM，抽取层应该用生成器。
- 不声明 schema —— 下游不知道字段名和类型，等于把问题推给别人。
- 不做幂等 —— 重跑一次就重复追加数据，生产环境非常危险。
- 不写异常处理 —— 一条脏数据直接让整个管道崩掉，工程上不可接受。

---

## 动手练习

请在本机新建 `etl_practice.py`，完成以下任务：

1. 有一个 JSON Lines 文本，每行形如 `{"name": "  Alice ", "age": "30", "city": "Beijing"}`。
2. 实现 `extract_jsonl(text: str) -> list[dict]`，逐行解析并返回列表。
3. 实现 `clean(records)`，要求：
   - 丢掉 `name` 为空或缺失的记录；
   - 所有字符串字段去除首尾空格；
   - `age` 转成 `int`，失败则记为 `0`；
   - `city` 缺失则填 `"Unknown"`。
4. 实现 `load(records) -> str`，输出固定列顺序 `name,age,city` 的 CSV 文本。
5. 写一个 `run(text) -> str` 把上面三步串起来，并用下面输入测试：

```
{"name": "  Alice ", "age": "30", "city": " Beijing "}
{"name": "", "age": "25", "city": "Shanghai"}
{"name": "Bob", "age": "abc", "city": ""}
{"name": "Carol", "age": "28"}
```

期望输出（顺序一致）：

```
name,age,city
Alice,30,Beijing
Bob,0,
Carol,28,Unknown
```

加分项：给 `run` 加一个 `try/except`，让某一行 JSON 解析失败时跳过该行而不是整条管道崩溃。

```python
import csv
import io
import json
from collections.abc import Iterable, Iterator


def extract_jsonl(text: str) -> Iterator[dict]:
    """逐行解析 JSON Lines，解析失败的行直接跳过"""
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            yield json.loads(line)
        except json.JSONDecodeError:
            continue


def clean(records: Iterable[dict]) -> list[dict]:
    """清洗：丢空 name、去空格、age 转 int、city 兜底"""
    result = []
    for raw in records:
        name = (raw.get("name") or "").strip()
        if not name:
            continue
        try:
            age = int(str(raw.get("age", 0)).strip())
        except (ValueError, TypeError):
            age = 0
        city = (raw.get("city") or "").strip() or "Unknown"
        result.append({"name": name, "age": age, "city": city})
    return result


def load(records: list[dict]) -> str:
    """按固定列顺序输出 CSV 文本"""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=["name", "age", "city"])
    writer.writeheader()
    for r in records:
        writer.writerow(r)
    return buf.getvalue()


def run(text: str) -> str:
    """完整 ETL 管道：Extract -> Transform -> Load"""
    return load(clean(extract_jsonl(text)))


if __name__ == "__main__":
    sample = "\n".join([
        '{"name": "  Alice ", "age": "30", "city": " Beijing "}',
        '{"name": "", "age": "25", "city": "Shanghai"}',
        '{"name": "Bob", "age": "abc", "city": ""}',
        '{"name": "Carol", "age": "28"}',
        'not-a-json-line',
    ])
    print(run(sample), end="")
```


---

## 本课题目

### single_choice · None



- [A] Parquet
- [B] CSV
- [C] JSON Lines
- [D] 纯文本日志文件

**参考答案**：0

**解析**：Parquet 是列式存储格式，自带 schema，支持嵌套类型（arrays、structs）以及列裁剪和谓词下推，非常适合分析型场景。CSV 不支持嵌套结构且无类型信息；JSON Lines 虽能表达嵌套但无列裁剪能力且解析开销大；纯文本日志更不具备 schema 与列裁剪特性。

### single_choice · None



- [A] row group 是 Parquet 文件内部按行划分的存储单元，读取时可以只加载部分 row group
- [B] row group 只能有一个，否则文件无法被读取
- [C] row group 是 Parquet 的行索引，用于保证行顺序不会改变
- [D] row group 表示每一列的最大值，用于统计信息

**参考答案**：0

**解析**：Parquet 文件由若干 row group 组成，每个 row group 内部按列存储数据。读取时可以只加载需要的 row group，从而实现并行读取和裁剪。一个文件允许多个 row group；行顺序是由写入顺序决定，与 row group 数量无必然关系；列统计信息（min/max）是 row group 的元数据之一，而不是 row group 本身。

### single_choice · None



- [A] Parquet 是内存中的列式数据表示，Arrow 是磁盘上的文件格式
- [B] Arrow 是一种磁盘文件格式，Parquet 是它的内存版本
- [C] Parquet 是磁盘上的列式文件格式，Arrow 是内存中的列式数据表示，二者常配合使用
- [D] Parquet 和 Arrow 是完全相同的格式，只是叫法不同

**参考答案**：2

**解析**：Parquet 是磁盘上的列式存储文件格式，Arrow 是内存中的列式数据表示（由不同语言共享）。PyArrow 同时提供两者，读取 Parquet 后通常以 Arrow Table 的形式在内存中处理。A、B 把两者角色对调，D 把两者混为一谈。

### single_choice · None



- [A] engine 参数只能使用默认值，不能更改
- [B] 不同的 engine 实现可能在支持的特性、性能和依赖上有差异，应按环境选择
- [C] 指定 engine='pyarrow' 后就不需要安装 pyarrow 了
- [D] engine 参数用于指定压缩算法

**参考答案**：1

**解析**：pandas 的 to_parquet/read_parquet 支持不同引擎（如 pyarrow、fastparquet），它们在依赖、特性支持、性能上可能有差异，需要根据环境选择。指定 engine='pyarrow' 仍然要求安装 pyarrow；engine 不是压缩参数，也不是只能使用默认值。

### single_choice · None



- [A] pandas.read_parquet 默认返回 Arrow Table，需要手动调用 .to_pandas()
- [B] pandas.read_parquet 默认返回 pandas DataFrame，可直接使用
- [C] pandas 无法读取 Parquet，必须先用 pyarrow 读取再转换
- [D] 必须调用 pyarrow.parquet.read_table 并设置 as_pandas=True 才能得到 DataFrame

**参考答案**：1

**解析**：pandas.read_parquet 直接返回 pandas DataFrame，这是它的默认行为；它内部可能借助 pyarrow 或 fastparquet 读取，但对外返回 DataFrame。A、C、D 都是对 pandas 读取行为的常见误解。

### single_choice · None



- [A] 行组越小越好，没有负面影响
- [B] 行组越小，读取时能跳过更多数据块，但元数据开销和文件碎片会增加
- [C] 行组大小只影响写入速度，不影响读取
- [D] 行组大小一旦写入就无法更改，所以必须设置为最大值

**参考答案**：1

**解析**：row group 越小，谓词下推时能跳过的粒度越细，但元数据（统计信息、footer）和文件碎片化开销也会增加；需要权衡。行组大小同时影响读写，不是只影响写入，也不是越小越好。

### single_choice · None



- [A] Parquet 文件不保存 schema，读取时必须由用户指定每一列的类型
- [B] Parquet 文件把 schema 保存在文件元数据中，读取时可以自动获得列名和类型
- [C] Parquet 的 schema 只能保存列名，不能保存类型
- [D] Parquet 的 schema 保存在单独的 .schema 文件中，必须一起分发

**参考答案**：1

**解析**：Parquet 文件自身在 footer 中保存 schema（列名、类型、嵌套结构等），读取时无需用户手动指定类型。它不需要单独的分发文件，也不只是列名。

### single_choice · None



- [A] 按行逐条读取并立即打印每一行
- [B] 只查询某几列并对某列做聚合统计
- [C] 用文本编辑器手动修改某个单元格的值
- [D] 把文件通过邮件附件发送给同事查看

**参考答案**：1

**解析**：Parquet 是列式存储，只查询部分列并做聚合时可以利用列裁剪和向量化执行，通常比 CSV 高效得多。逐行读取、手动编辑、邮件查看文本内容都不是 Parquet 的强项，CSV 更合适。

### single_choice · None



- [A] 一个 pandas DataFrame
- [B] 一个 pyarrow Table（列式内存表）
- [C] 一个 Python 字典，键是列名，值是列表
- [D] 一个 NumPy 二维数组

**参考答案**：1

**解析**：pyarrow.parquet.read_table 返回 pyarrow.Table，这是 Arrow 的列式内存表。如果需要 pandas DataFrame，可以进一步调用 .to_pandas()。它不会自动返回 DataFrame、字典或纯 NumPy 数组。

### single_choice · None



- [A] Spark 只能读取 CSV，不能读取 Parquet
- [B] Spark 可以读取 Parquet，并利用其列式特性和谓词下推加速查询
- [C] Spark 读取 Parquet 时必须先把整个文件加载到驱动节点内存
- [D] Spark 读取 Parquet 时无法并行，因为 Parquet 是二进制格式

**参考答案**：1

**解析**：Spark 原生支持 Parquet，并利用列裁剪、谓词下推、row group 切分等特性进行并行和加速查询。它不需要把整个文件加载到驱动节点，也能并行读取。读 Parquet 是 Spark 的常见用法。

### single_choice · None



- [A] 因为 Parquet 会丢弃一部分数据
- [B] 因为 Parquet 是列式存储，同一列的数据类型一致，便于使用编码和压缩，且可跳过重复值
- [C] 因为 Parquet 把字符串自动转换成整数
- [D] 因为 Parquet 不保存列名

**参考答案**：1

**解析**：Parquet 按列存储，同列数据同质，便于字典编码、RLE、位压缩等编码方式，再加上块级压缩，通常比行式 CSV 更省空间。它不会丢弃数据、不会自动把字符串转成整数、也必须保存列名。

### single_choice · None



- [A] pyarrow.parquet.write_table(table, path)
- [B] pyarrow.csv.write_csv(table, path)
- [C] pyarrow.parquet.read_table(path)
- [D] pyarrow.Table.to_csv(path)

**参考答案**：0

**解析**：pyarrow.parquet.write_table 用于把 Arrow Table 写入 Parquet 文件；read_table 是读取；write_csv 是写 CSV；Table 对象没有 to_csv 方法（pandas DataFrame 才有）。

### single_choice · None



- [A] pandas 不支持读取分区目录，必须先手动合并所有文件
- [B] 使用 read_parquet 并传入 filters=[('year', '==', 2023), ('month', '==', 1)]，由底层引擎利用分区信息裁剪
- [C] 把所有文件读入后再用 Python 的 filter 函数过滤，因为 read_parquet 不能按分区过滤
- [D] 只能读取单个文件，无法读取整个目录

**参考答案**：1

**解析**：现代 pandas 的 read_parquet 底层使用 pyarrow 或 fastparquet，支持直接读取分区目录（dataset）并可通过 filters 参数下推分区过滤条件，从而只读取相关分区。直接手动合并或全量读取后再过滤虽然结果正确但效率低下，且“pandas 不支持目录”是常见误解。

### single_choice · None



- [A] 谓词下推指在写入时对数据做预聚合，从而减少读取量
- [B] 谓词下推指查询引擎利用 Parquet 元数据（如 row group 的 min/max 统计）跳过不可能匹配的数据块
- [C] 谓词下推指把 SQL 中的 WHERE 子句转换成 Python 的 if 语句
- [D] 谓词下推只对 CSV 格式有效，Parquet 不支持

**参考答案**：1

**解析**：谓词下推（predicate pushdown）是指查询引擎在扫描 Parquet 时，利用文件/row group 级别的统计信息（最小值、最大值、空值计数等）来跳过不满足过滤条件的数据块，从而减少 I/O。它发生在读取阶段而不是写入阶段，也与把 SQL 转成 Python 无关；CSV 没有元数据统计，反而不支持这种优化。

### single_choice · None



- [A] 需要人类直接打开文件用肉眼查看每一行数据
- [B] 需要在 Excel 中直接双击打开并编辑
- [C] 需要对数十 GB 的分析型数据做列裁剪和压缩存储
- [D] 需要把数据追加到文件末尾，并保证任意程序都能读取

**参考答案**：2

**解析**：Parquet 是列式、压缩、带 schema 的二进制格式，特别适合大规模分析型数据的列裁剪和压缩存储。人类肉眼查看、Excel 直接编辑、以及需要追加且通用文本可读的场景，CSV 更合适。Parquet 不是为逐行编辑或简单追加设计的。

### single_choice · None



- [A] Parquet 文件一旦写入就不能直接修改某一行，通常需要重写文件或使用其他机制
- [B] Parquet 文件可以像数据库一样原地更新任意一行，且不需要额外结构
- [C] Parquet 文件只能追加，不能覆盖写入
- [D] Parquet 文件每次更新一行都会自动生成一个新版本文件

**参考答案**：0

**解析**：Parquet 是面向分析的一次写入、多次读取的格式，文件本身不可原地修改某一行；要更新数据通常需要重写整个文件或借助 Delta Lake、Iceberg 等表格式来管理版本与增量。选项 B、C、D 都是常见误解。

### single_choice · None



- [A] 压缩只能作用在整个文件上，不能按列选择
- [B] Snappy 通常压缩比高但速度慢，Zstd 压缩比低但速度快
- [C] 不同的压缩算法在压缩比和解压速度上有不同权衡，应按场景选择
- [D] Parquet 不支持任何压缩，压缩必须由外部工具完成

**参考答案**：2

**解析**：Parquet 支持多种压缩算法，不同算法在压缩比、写入速度、解压速度上各有取舍；Parquet 本身支持压缩。通常 Snappy 速度快、压缩比中等；Zstd 压缩比更高且解压也快；Gzip 压缩比高但较慢。压缩不是只能整文件进行，也不是外部工具才做的事。

### single_choice · None



- [A] 先读取全部列，再用 df[['a','b']] 选择需要的列
- [B] 在读取时通过 columns=['a','b'] 参数只加载需要的列
- [C] 先把 Parquet 转成 CSV，再用 CSV 读取器选择列
- [D] 必须读取所有列，因为 Parquet 不支持列裁剪

**参考答案**：1

**解析**：Parquet 是列式存储，读取时指定 columns 可以只加载需要的列，减少 I/O 和解码开销。先读全部列再切片已经付出了读取所有列的代价；转成 CSV 反而更慢且丢失类型；Parquet 正是支持列裁剪的格式。

### single_choice · None



- [A] 可以让 Parquet 文件变得更小，从而减少存储成本
- [B] 可以让查询引擎根据目录路径跳过不相关的分区，减少扫描的数据量
- [C] 可以保证每个分区的数据量完全相等
- [D] 可以让 Parquet 支持原地更新

**参考答案**：1

**解析**：Hive 风格分区把分区键编码在目录路径中，查询引擎可以根据过滤条件只读取相关目录，实现分区裁剪，减少扫描量。分区并不会自动让文件更小、也不会保证数据量均衡，更不能让 Parquet 支持原地更新。

### single_choice · None



- [A] 整数（int32/int64）
- [B] 浮点数（float/double）
- [C] 任意 Python 对象（如自定义类实例）
- [D] 字符串（byte_array/string）

**参考答案**：2

**解析**：Parquet 有明确的逻辑类型系统，支持整数、浮点、字符串、布尔、嵌套结构等，但不能直接存储任意 Python 对象（如自定义类实例）；这类数据需要先序列化成字节/字符串或拆成受支持的字段。

### single_choice · None



- [A] ETL 中提取阶段负责清洗数据，转换阶段负责从数据源收集数据
- [B] ETL 中提取阶段从数据源获取原始数据，转换阶段对数据做清洗、格式化和聚合等处理，加载阶段把结果写入目标存储
- [C] ETL 只适用于数据库之间的迁移，不能用于文件或 API 数据
- [D] ETL 的加载阶段必须在转换阶段之前完成，否则数据会丢失

**参考答案**：1

**解析**：ETL 的核心顺序是 Extract（从数据源获取原始数据）、Transform（清洗、标准化、聚合等）、Load（写入目标存储）。选项 A 把提取与转换的职责对调；选项 C 忽略了文件、API 等数据源；选项 D 颠倒了加载与转换的顺序。

### single_choice · None



- [A] 可以让代码运行速度自动变快，因为函数调用开销小
- [B] 可以让每个转换步骤单独测试和复用，便于定位问题和组合流程
- [C] 可以避免使用任何第三方库，从而减少依赖
- [D] 可以让数据自动去重，不需要额外编写逻辑

**参考答案**：1

**解析**：把转换拆成小函数是模块化设计：每个函数职责单一，便于单元测试、复用和排错，也方便按需组合成不同流程。它并不会自动提升运行速度、消除第三方依赖或自动去重。

### multi_choice · None



- [A] 对字段做类型转换和单位统一
- [B] 过滤掉不符合业务规则的记录
- [C] 从远程 API 拉取原始 JSON 数据
- [D] 按维度对数据做聚合或派生新字段
- [E] 将最终结果写入目标数据库

**参考答案**：[0, 1, 3]

**解析**：类型转换、过滤、聚合/派生字段都属于转换阶段。从远程 API 拉取原始数据属于提取阶段；写入目标数据库属于加载阶段。

### multi_choice · None



- [A] 让加载操作具备幂等性，例如按主键 upsert
- [B] 把处理过程拆分为可重试的多个步骤，并记录中间状态
- [C] 每次重跑前手动修改源数据以「对齐」结果
- [D] 对关键步骤记录日志和批次标识，便于定位与回滚
- [E] 让任务失败后不记录任何信息，靠记忆恢复

**参考答案**：[0, 1, 3]

**解析**：幂等写入、步骤拆分与状态记录、日志与批次标识，都是可安全重跑的关键。手动改源数据不可取；失败不留痕迹会让恢复变得困难且不可靠。

### multi_choice · None



- [A] 不同数据源的编码和分隔符可能不一致，需要分别处理
- [B] 源数据可能包含大量缺失或格式错误的记录
- [C] 提取阶段应尽量修改源数据，使其符合目标格式
- [D] 数据源可能不稳定或存在访问频率限制，需要考虑重试
- [E] 提取必须一次性完成，不能分批

**参考答案**：[0, 1, 3]

**解析**：编码/分隔符差异、脏数据、源不稳定或限流都是提取阶段的常见挑战，尤其需要重试机制。提取阶段不应随意修改源数据，格式统一应在转换阶段进行；提取可以分批进行。

### multi_choice · None



- [A] 把复杂转换拆成职责单一的小函数并配单元测试
- [B] 用清晰命名的中间变量或数据结构表示各处理阶段
- [C] 把所有逻辑写进一个超长函数以减少调用层级
- [D] 用配置文件或参数管理数据源、路径等易变信息
- [E] 在代码中硬编码所有文件路径和数据库连接信息

**参考答案**：[0, 1, 3]

**解析**：拆分函数、清晰命名、配置化管理都有利于维护与测试。把所有逻辑塞进一个超长函数会降低可读性；硬编码路径和连接信息会使环境迁移和修改变得脆弱。

### fill_blank · None



**参考答案**：["提取", "Extract", "extract", "抽取"]

**解析**：ETL 三个字母分别对应 Extract（提取）、Transform（转换）、Load（加载）。从数据源收集原始数据的阶段是提取阶段。

### fill_blank · None



**参考答案**：["转换", "Transform", "transform", "转化"]

**解析**：转换阶段负责对提取到的数据做清洗、格式化、聚合、派生等处理，使其满足目标存储与分析需求。

### fill_blank · None



**参考答案**：["加载", "Load", "load", "装载"]

**解析**：L 代表 Load（加载），即把转换后的数据写入目标存储（如数据仓库、数据库或文件）。

### code_reading · None



**参考答案**：遍历输入记录，跳过缺少 order_id 的记录；对 amount 缺失或为负的情况将其置为 0；最后只保留 order_id 与 amount 两个字段并返回新列表。

**解析**：该函数是转换阶段的典型示例：先做过滤（跳过缺少关键字段的记录），再做缺失/异常值处理（负数或 None 归零），最后做字段裁剪并输出结构化结果。

### code_reading · None



**参考答案**：最终只剩下最后一次传入的 records 中的数据，因为每次执行都会先清空 orders 表再插入，重复执行不会产生重复行，结果与只执行一次相同（具备幂等性）。

**解析**：该写入逻辑每次先 DELETE 整表再插入，因此重复执行不会累积重复数据，最终状态等于最后一次输入。这是一种通过「先清后写」实现幂等的方式（但会覆盖该表原有全部数据）。

### scenario · None



**解析**：重跑产生重复的根因是加载操作不幂等。应让写入以业务主键为准（如 upsert 或按批次先删后写），使同一批次重复执行的结果与执行一次一致；同时记录批次标识便于识别与回滚，从而安全重跑。

### single_choice · None



- [A] 用户点击按钮后立即在网页上看到自己的余额
- [B] 每天凌晨把多个业务库的订单数据汇总、清洗后写入分析仓库
- [C] 在游戏里实时响应玩家的移动指令
- [D] 在编辑器中实时高亮用户输入的代码语法

**参考答案**：1

**解析**：ETL 适合批量、周期性的数据集成与分析场景，例如把多源数据汇总清洗后写入分析仓库。实时交互场景（余额查询、游戏响应、语法高亮）对延迟敏感，通常不属于典型批量 ETL 的适用场景。

### scenario · None



**解析**：内存不足通常来自一次性加载全部数据。提取环节可改为分批或流式读取（如逐行迭代、按块读取、使用生成器惰性产出）；转换环节也可对每批数据独立处理，避免在内存中同时保留全部中间结果，从而把内存占用控制在可控范围。

### single_choice · None



- [A] 一次性把整个文件读入内存，无论文件多大都直接处理
- [B] 分批或按行迭代读取，避免把整个文件同时加载到内存中
- [C] 先修改源文件的内容再读取，以保证数据干净
- [D] 忽略文件编码，直接按默认方式读取，出错再说

**参考答案**：1

**解析**：提取阶段面对大文件时，流式或分批读取能显著降低内存占用，避免内存溢出。一次性读入大文件可能导致内存不足；修改源文件有风险且不符合提取阶段职责；忽略编码容易导致乱码或读取异常。

### single_choice · None



- [A] 用该列的均值填充缺失值而不考虑数据分布
- [B] 记录缺失值数量并单独分析缺失模式
- [C] 根据业务规则决定删除或填充
- [D] 对缺失值做标记以便后续追溯

**参考答案**：0

**解析**：不区分分布直接用均值填充可能扭曲数据分布、掩盖缺失模式，从而引入偏差。记录缺失、按业务规则处理、标记缺失都是更可追溯、更谨慎的做法。

### single_choice · None



- [A] 可以保证数据一定不会出错
- [B] 便于测试和推理，因为相同输入总得到相同输出
- [C] 可以跳过加载阶段直接得到结果
- [D] 可以自动处理并发写入冲突

**参考答案**：1

**解析**：纯函数的输出只由输入决定且无副作用，因此容易测试、推理和复用。它并不能保证数据本身正确、不能省去加载阶段，也不负责处理并发冲突。

### single_choice · None



- [A] 幂等意味着同一处理流程重复执行多次，对目标数据的结果与执行一次相同
- [B] 幂等意味着处理流程只能执行一次，重复执行会报错
- [C] 幂等意味着每次执行都会产生新的一份数据副本
- [D] 幂等意味着流程必须并行执行才能生效

**参考答案**：0

**解析**：幂等性指同一操作重复执行多次的效果与执行一次一致，这在重跑任务、故障恢复时非常重要。它不意味着只能执行一次、不意味着产生副本，也与并行执行无关。

### single_choice · None



- [A] 每次运行前清空整个数据库的所有表
- [B] 使用基于主键的 upsert（存在则更新、不存在则插入）或先删除本次批次再写入
- [C] 不做任何处理，反正重复数据可以后面手动删
- [D] 每次运行把数据写入随机命名的表，避免冲突

**参考答案**：1

**解析**：基于主键的 upsert 或按批次先删后写，能在重跑时保持结果一致，属于实现幂等的常见手段。清空整个库风险极大；放任重复增加清理成本；随机表名会让目标数据难以管理。

### single_choice · None



- [A] 提取
- [B] 转换
- [C] 加载
- [D] 存储引擎调优

**参考答案**：1

**解析**：把格式统一、类型转换、标准化等属于转换阶段的典型工作。提取是从源获取数据，加载是写入目标，存储引擎调优与 ETL 阶段划分无关。

### single_choice · None



- [A] ETL 只负责搬运数据，数据质量应在数据到达后再单独考虑
- [B] 转换阶段可以包含去重、校验、类型转换等步骤来提升数据质量
- [C] 只要提取阶段数据正确，转换和加载就不需要校验
- [D] 数据质量只与加载阶段的目标存储有关

**参考答案**：1

**解析**：转换阶段是提升数据质量的关键环节，可包含去重、校验、标准化、类型转换等。数据质量贯穿提取、转换、加载全过程，不能只在某个阶段或事后单独考虑。
