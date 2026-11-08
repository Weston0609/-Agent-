# s5u4l2 Polars：为大数据而生的 DataFrame 库 / py.data.arrow —— 用 Arrow 做跨语言、零拷贝的列式数据交换

> 来源 `content/lessons/s5u4l2.json`

## py.data.polars

# Polars：为大数据而生的 DataFrame 库

> 一句话直觉：当你用 pandas 处理几十万行以上的数据开始卡顿时，Polars 用 Rust 写的多线程引擎，能在同样的机器上快几倍到几十倍，而且内存占用更低。

---

## 一、为什么需要 Polars（DataFrame 是什么）

**DataFrame（数据框）** 是一种带行名和列名的二维表格结构，类似 Excel 里的工作表，但可以用代码批量运算。Python 里最知名的是 **pandas**，但它有两个长期痛点：

1. **单线程（single-threaded）**：只用一个 CPU 核心，机器再多核也用不上。
2. **内存膨胀**：很多操作会悄悄复制整份数据，几十万行就会吃掉好几个 GB。

**Polars** 是一个用 **Rust** 编写、以 **Arrow**（Apache Arrow，一种列式内存格式）为底层的数据框库，天然具备三个优势：

- **多线程并行**：自动利用所有 CPU 核。
- **惰性求值（lazy evaluation）**：先构建查询计划，再整体优化执行，避免中间结果。
- **低内存**：列式存储 + 零拷贝（zero-copy）切片。

一句话：**Polars 是 pandas 的“高性能替代品”，在中等以上数据规模时优势显著。**

---

## 二、安装与最小示例

安装：

```bash
pip install polars
```

最小可运行示例：

```python
import polars as pl

# 用字典创建 DataFrame，和 pandas 类似但更严格
df = pl.DataFrame({
    "name": ["Alice", "Bob", "Carol"],
    "age":  [30, 25, 35],
})
print(df)
```

输出：

```
shape: (3, 2)
┌───────┬─────┐
│ name  ┆ age │
│ ---   ┆ --- │
│ str   ┆ i64 │
╞═══════╪═════╡
│ Alice ┆ 30  │
│ Bob   ┆ 25  │
│ Carol ┆ 35  │
└───────┴─────┘
```

注意 Polars 的打印会**显示每列的数据类型**（`str`、`i64`），这是它的风格：**类型先行**。

---

## 三、表达式（Expression）：Polars 的灵魂 API

Polars 的核心抽象是 **表达式（expression）**，用 `pl.col("列名")` 开始。表达式不是“立刻算出来的值”，而是“对某列的运算描述”。它可以在 `select`、`with_columns`、`filter`、`group_by` 等语境中复用。

```python
import polars as pl

df = pl.DataFrame({
    "name": ["Alice", "Bob", "Carol", "Dave"],
    "age":  [30, 25, 35, 28],
    "city": ["BJ", "SH", "BJ", "SH"],
})

# 表达式：对 age 列 ×2，再命名新列
result = df.with_columns(
    (pl.col("age") * 2).alias("age_double")
)
print(result)
```

**关键点**：

- `pl.col("age")` 返回一个表达式；`* 2` 会广播到整列；`.alias("新名")` 给结果列取名。
- `with_columns` 不会修改原 `df`（不可变风格，**immutable**），而是返回新对象。

---

## 四、筛选、排序、分组：三大常用操作

### 1. 筛选（filter）

```python
# 选出 age > 28 且 city == 'BJ' 的行
df2 = df.filter(
    (pl.col("age") > 28) & (pl.col("city") == "BJ")
)
print(df2)
```

注意：条件之间必须用 `&`、`|`、`~`（按位运算符），**不能**用 `and`/`or`/`not`，因为它们不支持逐元素运算。每个条件都要用括号包起来。

### 2. 排序（sort）

```python
df3 = df.sort("age", descending=True)
print(df3)
```

### 3. 分组聚合（group_by + agg）

```python
# 按城市分组，求年龄平均值和人数
df4 = df.group_by("city").agg([
    pl.col("age").mean().alias("avg_age"),
    pl.len().alias("cnt"),
])
print(df4)
```

`agg` 里传的是**一列表达式**；`pl.len()` 是内置的行计数表达式。这里的写法与 SQL 的 `GROUP BY` 非常接近。

---

## 五、惰性模式（Lazy）：让 Polars 自己优化

当数据量大时，推荐用 **`pl.scan_*`** 或 **`.lazy()`** 进入**惰性模式（LazyFrame）**。此时 Polars 不会立刻执行，而是记录一张“执行计划”，等你调用 `.collect()` 时再一次性优化并并行执行。

```python
import polars as pl

# 惰性：先构建计划，再一次性执行
lazy: pl.LazyFrame = (
    df.lazy()
      .filter(pl.col("age") > 26)
      .group_by("city")
      .agg(pl.col("age").mean().alias("avg_age"))
      .sort("avg_age", descending=True)
)

print(lazy.explain())   # 查看优化后的执行计划
result = lazy.collect() # 这时才真正算
print(result)
```

**为什么要惰性？** 因为 Polars 可以做**谓词下推（predicate pushdown）**、**投影下推（projection pushdown）**：你写的 `filter` 会被推到读取阶段之前，只读需要的列和行；多步运算可以合并成一次流式处理，数十倍速度差距常来自这里。

---

## 六、读取文件：CSV 与 Parquet

```python
# 直接读 CSV（惰性，推荐）
lf = pl.scan_csv("data.csv")

# Parquet 是列式压缩格式，读取更快，推荐
lf = pl.scan_parquet("data.parquet")

# 写文件
df.write_parquet("out.parquet")
df.write_csv("out.csv")
```

**Parquet** 是数据工程的通行格式：列存、压缩、保类型，远比 CSV 小且快。能用 Parquet 就用 Parquet。

---

## 七、和 pandas 怎么选？

| 场景 | 推荐 |
|------|------|
| 数据 < 10 万行、依赖生态（如 scikit-learn 直接吃 pandas） | pandas |
| 数据 10 万 ~ 上亿行、跑批处理、需要并行 | **Polars** |
| 需要惰性优化、流式处理大文件 | **Polars** |
| 老项目大量 pandas 代码 | 保留 pandas，新增模块用 Polars |

Polars 与 pandas 之间可以互转：`df.to_pandas()`、`pl.from_pandas(pdf)`。

---

## 小结表

| 概念 | Polars 对应 |
|------|-------------|
| 数据框 | `pl.DataFrame` |
| 惰性数据框 | `pl.LazyFrame` |
| 列引用 | `pl.col("x")` |
| 新增/修改列 | `with_columns` |
| 过滤 | `filter` |
| 排序 | `sort` |
| 分组聚合 | `group_by(...).agg(...)` |
| 触发执行 | `.collect()` |
| 读文件 | `pl.scan_csv` / `pl.scan_parquet` |

## py.data.arrow

# py.data.arrow —— 用 Arrow 做跨语言、零拷贝的列式数据交换

> **一句话直觉**：当你用 Python 处理表格数据、又想和 pandas / Polars / DuckDB / Spark / R 甚至 C++ 高效互通时，**Apache Arrow** 就是它们之间“通用的数据快递盒”——列式内存布局 + 零拷贝(Zero-Copy)，让数据交换从“搬砖”变成“递名片”。

本讲义面向零基础到工程级读者，40 分钟带你从“为什么需要 Arrow”一路走到“用 PyArrow（Python 的 Arrow 实现）做真实的表格分析与 IPC（Inter-Process Communication，进程间通信）”。

---

## 0. 前置准备：安装

```bash
pip install pyarrow pandas
```

我们全程使用 **PyArrow**，它是 Apache Arrow 的官方 Python 绑定。

---

## 1. 为什么需要 Arrow：从 pandas 的内存痛点说起

pandas 的 DataFrame 每个列是一个 NumPy 数组，但**字符串列**默认是 Python 对象数组（`object` dtype），每个字符串是一个独立 Python 对象——内存开销大、跨进程共享难、跨语言更是要序列化。

Apache Arrow 提供：

- **列式内存格式（Columnar Memory Format）**：同一列数据连续存储，利于 CPU cache、SIMD、向量化扫描。
- **零拷贝（Zero-Copy）**：语言之间通过共享内存缓冲区传递，不复制字节。
- **多语言一致规范**：C++、Python、R、Java、Rust、Go 都实现同一份内存规范。
- **丰富的类型系统**：`int64`、`string`、`timestamp`、`decimal`、`list`、`struct`、`map`、`dictionary` 等。

**关键结论**：Arrow 不是“又一个 DataFrame”，它是一份**内存规范 + 一组库**，DataFrame 只是它上面的一层。

```python
# 01_why_arrow.py
import pyarrow as pa
import numpy as np

# 一个 Arrow Array：不可变、类型明确、内存连续
arr = pa.array([1, 2, 3, 4], type=pa.int64())
print(arr.type)          # int64
print(arr.nbytes)        # 32 (4 * 8 bytes)，纯粹数据，无 Python 对象开销
print(arr.null_count)    # 0

# 零拷贝转换：NumPy -> Arrow
np_arr = np.arange(5, dtype=np.int64)
arrow_arr = pa.array(np_arr, from_pandas=False, zero_copy_only=True)
print(arrow_arr)         # [0,1,2,3,4]
```

---

## 2. 核心三件套：Array、ChunkedArray、Table

Arrow 的 Python 层三个最常用对象：

| 对象 | 含义 | 类比 pandas |
|---|---|---|
| `Array` | 一段不可变、单块内存的列 | 一列 |
| `ChunkedArray` | 多个 `Array` 组成的逻辑列 | 一列（分块） |
| `Table` | 若干 `ChunkedArray` 组成的二维表 | DataFrame |

为什么要有 ChunkedArray？因为数据经常是**分批（batch）**到达的（如流式读 Parquet、分布式聚合），合并成大数组代价高。

**关键结论**：`Table` 是**逻辑**二维表，列可以是多段内存，物理上碎片化不影响逻辑上的整体性。

```python
# 02_table.py
import pyarrow as pa

# 构造一个 Table：用 schema 明确定义列类型
schema = pa.schema([
    ("name",  pa.string()),
    ("age",   pa.int32()),
    ("score", pa.float64()),
])

table = pa.table(
    {
        "name":  ["Alice", "Bob", "Carol"],
        "age":   [23, 30, 27],
        "score": [88.5, 92.0, 79.3],
    },
    schema=schema,
)

print(table.schema)
print(table.num_rows, table.num_columns)

# 取列 -> ChunkedArray；to_pylist 方便小数据查看
print(table.column("age").to_pylist())

# 按条件过滤：filter 返回新 Table（零拷贝切片）
filtered = table.filter(pa.compute.greater(table["score"], 80.0))
print(filtered)
```

---

## 3. 计算内核：pyarrow.compute（简称 pc）

Arrow 不仅存数据，还带一套**向量化计算函数**，在列上批量执行，性能接近 C++。

**关键结论**：优先用 `pyarrow.compute` 而不是 Python `for` 循环——这是“列式思维”的第一步。

```python
# 03_compute.py
import pyarrow as pa
import pyarrow.compute as pc

t = pa.table({"x": [1, 2, 3, 4, 5], "y": [10, 20, 30, 40, 50]})

# 逐元素运算，返回 Array
s = pc.add(t["x"], t["y"])
print(s)  # [11,22,33,44,55]

# 聚合
print(pc.sum(t["y"]).as_py())         # 150
print(pc.mean(t["y"]).as_py())        # 30.0

# group_by：按 x 的奇偶分组求 y 之和
key = pc.if_else(pc.equal(pc.bit_wise_and(t["x"], 1), 0), "even", "odd")
grouped = pa.table({"k": key, "y": t["y"]}).group_by("k").aggregate([("y", "sum")])
print(grouped)
```

---

## 4. 与其他生态无缝互通：pandas / NumPy / Polars / DuckDB

Arrow 真正的价值在**边界**上体现：

- **pandas** ⇄ Arrow：`table.to_pandas()` / `pa.Table.from_pandas(df)`，底层通过 `__arrow_array__` 协议尽量减少拷贝。
- **Polars** 生来就是 Arrow-native。
- **DuckDB** 可以直接对 Arrow Table 执行 SQL（零拷贝）。
- **Parquet / Flight / IPC**：列式存储与传输的天然格式。

**关键结论**：**能让数据留在 Arrow 里，就别着急转成 pandas**；跨工具只在最后一步落地。

```python
# 04_interop.py
import pyarrow as pa
import pandas as pd

df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})

tbl = pa.Table.from_pandas(df, preserve_index=False)
print(tbl.schema)

# Arrow -> pandas（可能零拷贝，取决于类型）
back = tbl.to_pandas()
print(back.dtypes)

# 保存为 IPC 文件（内存映射友好），再读回来
import pyarrow.feather as feather
feather.write_feather(tbl, "/tmp/demo.arrow")
tbl2 = feather.read_table("/tmp/demo.arrow")
assert tbl2.equals(tbl)
print("round-trip OK")
```

---

## 5. 工程实践：用 RecordBatch 做流式处理

真实数据往往很大。Arrow 提供 **RecordBatch**：一批行、共享同一个 Schema，是流式（streaming）处理的最小单元。

**关键结论**：大文件不要一次性读成 `Table`，用 `RecordBatchReader` 边读边算。

```python
# 05_batch.py
import pyarrow as pa
import pyarrow.ipc as ipc

schema = pa.schema([("id", pa.int64()), ("v", pa.float64())])

# 写两批
with ipc.new_file("/tmp/batches.arrow", schema) as w:
    w.write_batch(pa.record_batch([[1, 2], [0.5, 1.5]], schema=schema))
    w.write_batch(pa.record_batch([[3, 4], [2.5, 3.5]], schema=schema))

# 流式读并逐批聚合
total = 0.0
with ipc.open_file("/tmp/batches.arrow") as r:
    for batch in r.iter_batches(batch_size=2):
        total += pa.compute.sum(batch.column("v")).as_py()
print("sum =", total)  # 8.0
```

---

## 小结对照表

| 层级 | 对象 | 用途 |
|---|---|---|
| 列 | `Array` / `ChunkedArray` | 紧凑、类型化的列数据 |
| 表 | `Table` | 逻辑二维表，跨工具交换 |
| 批 | `RecordBatch` | 流式/分片处理的最小单位 |
| 计算 | `pyarrow.compute` | 向量化运算 |
| 传输 | IPC / Feather / Flight / Parquet | 序列化与跨进程通信 |

---

## 动手练习

**任务**：在本地写一个脚本 `arrow_practice.py`，完成下面全部动作：

1. 生成一份 100 万行的模拟订单数据，列：`order_id(int64)`、`user(str)`、`amount(float64)`、`ts(timestamp[us])`。用 `pa.table(...)` 构造。
2. 用 `pyarrow.compute` 完成：(a) 过滤 `amount > 100`；(b) 按 `user` 分组求 `amount` 之和；(c) 找出金额最大的 `user`。
3. 把过滤后的结果用 `pyarrow.feather.write_feather` 写到 `orders.arrow`，再从文件读回并断言 `equals`。
4. 用 `ipc.new_file` + `iter_batches(batch_size=10000)` 流式读回文件，逐批累加 `amount` 总和，并和一次性求和对比。
5. 把结果 `to_pandas()` 打印 `head()`，观察内存占用（`df.memory_usage(deep=True).sum()`）。

**进阶**：把 1~3 步改为从 Parquet（`pyarrow.parquet`）读写，对比文件大小。

提交物：脚本 + 一段简短说明（≤200 字），解释为什么第 4 步“流式求和”和“一次性求和”结果一致，但在内存占用上有何不同。


---

## 本课题目

### single_choice · None



- [A] DataFrame 是惰性求值的，LazyFrame 是立即求值的
- [B] DataFrame 是立即求值的，LazyFrame 是惰性求值的，可以通过 collect() 触发计算
- [C] 两者都是立即求值，只是列名表示方式不同
- [D] 两者都不能进行聚合操作

**参考答案**：1

**解析**：Polars 中 DataFrame 立即执行，LazyFrame 构建查询计划后由 collect() 触发执行并可能进行优化。

### single_choice · None



- [A] df.group_by('team').agg(pl.col('score').mean())
- [B] df.groupby('team').avg('score')
- [C] df.group_by('team').mean()
- [D] df.agg('team').mean('score')

**参考答案**：0

**解析**：Polars 使用 group_by(...).agg(...) 组合，列表达式用 pl.col(...) 指定。

### single_choice · None



- [A] df.fill_null(0)
- [B] df.fillna(0)
- [C] df.dropna()
- [D] df.replace_null(0)

**参考答案**：0

**解析**：Polars 使用 fill_null 填充空值；fillna 是 pandas 风格。

### single_choice · None



- [A] df.select(pl.col('a').alias('x'), pl.col('b').alias('y'))
- [B] df.rename(columns={'a':'x','b':'y'})
- [C] df.columns = ['x','y']
- [D] df.select(['a','b']).rename(['x','y'])

**参考答案**：0

**解析**：select 支持表达式和 alias 来实现选择与重命名的一步操作。

### single_choice · None



- [A] df.group_by('team').agg(pl.len())
- [B] df.group_by('team').count()
- [C] df.group_by('team').size()
- [D] df.count('team')

**参考答案**：0

**解析**：Polars 在 agg 中使用 pl.len() 统计行数；count 方法行为不同，size 不是分组方法。

### single_choice · None



- [A] df.filter(pl.col('name').str.contains('A'))
- [B] df.filter(pl.col('name').contains('A'))
- [C] df.filter(df['name'].str.contains('A'))
- [D] df.filter('name'.contains('A'))

**参考答案**：0

**解析**：Polars 字符串操作通过 str 命名空间，contains 返回布尔表达式。

### single_choice · None



- [A] df.select(pl.col(['a','b']).mean())
- [B] df.select(pl.col('a','b').mean())
- [C] df.select(pl.all().mean())
- [D] df.select(pl.mean('a','b'))

**参考答案**：0

**解析**：pl.col 可以接收列名列表，对列表中的多列应用同一表达式。

### single_choice · None



- [A] df.unique(subset=['id'])
- [B] df.drop_duplicates('id')
- [C] df.distinct('id')
- [D] df.unique('id')

**参考答案**：0

**解析**：Polars 使用 unique 方法，通过 subset 指定去重依据的列。

### single_choice · None



- [A] df.with_columns(pl.col('date').str.to_date())
- [B] df.with_columns(pl.col('date').cast(pl.Date))
- [C] df.with_columns(pl.col('date').to_datetime())
- [D] df.with_columns(pl.col('date').astype('date'))

**参考答案**：0

**解析**：Polars 提供 str.to_date 将字符串解析为日期；cast 不负责字符串解析。

### single_choice · None



- [A] df.group_by('team').head(2)
- [B] df.group_by('team').agg(pl.col('score').head(2))
- [C] df.group_by('team').first(2)
- [D] df.group_by('team').take(2)

**参考答案**：1

**解析**：在 agg 中使用表达式 head(2) 可返回每组的前两行值；group_by 本身没有 head(2) 的语义。

### single_choice · None



- [A] df1.join(df2, on='id', how='left')
- [B] df1.merge(df2, on='id', how='left')
- [C] df1.left_join(df2, on='id')
- [D] df1.join(df2, left_on='id')

**参考答案**：0

**解析**：Polars 使用 join 方法，通过 how 参数指定连接类型，on 指定连接键。

### single_choice · None



- [A] 可以构建查询计划并在 collect 时进行优化，减少不必要计算
- [B] 可以自动把结果写入数据库
- [C] 可以绕过类型检查，避免类型转换错误
- [D] 可以同时使用多个线程但没有额外开销

**参考答案**：0

**解析**：LazyFrame 的核心优势是惰性求值与查询优化，能在执行时减少计算和内存开销。

### single_choice · None



- [A] pl.col('x') + 1
- [B] df['x'] + 1
- [C] pl.column('x').add(1)
- [D] col('x').plus(1)

**参考答案**：0

**解析**：Polars 表达式使用 pl.col('x') 并支持算术运算创建新表达式。

### single_choice · None



- [A] df.filter(pl.col('score') > 60)
- [B] df.where('score > 60')
- [C] df[df.score > 60]
- [D] df.filter(score > 60)

**参考答案**：0

**解析**：Polars 使用 filter 搭配布尔表达式；布尔表达式需用 pl.col 构建。

### single_choice · None



- [A] df.with_columns((pl.col('price') * pl.col('qty')).alias('total'))
- [B] df['total'] = df['price'] * df['qty']
- [C] df.assign(total=df['price'] * df['qty'])
- [D] df.add_column('total', df['price'] * df['qty'])

**参考答案**：0

**解析**：Polars 推荐用 with_columns 搭配表达式和 alias 来生成新列。

### single_choice · None



- [A] pl.read_csv('data.csv', lazy=True)
- [B] pl.scan_csv('data.csv')
- [C] pl.load_csv('data.csv')
- [D] pl.read_csv_lazy('data.csv')

**参考答案**：1

**解析**：scan_csv 返回 LazyFrame，便于后续惰性计算与优化；read_csv 返回 DataFrame。

### single_choice · None



- [A] df.with_columns(pl.col('age').cast(pl.Int64))
- [B] df.with_columns(pl.col('age').to_int())
- [C] df.astype({'age': 'int'})
- [D] df.cast('age', int)

**参考答案**：0

**解析**：Polars 使用 cast 方法进行类型转换，目标类型用 Polars 的 dtype 表示。

### single_choice · None



- [A] collect()
- [B] execute()
- [C] run()
- [D] to_pandas()

**参考答案**：0

**解析**：LazyFrame 的查询计划需要通过 collect() 才会执行并返回 DataFrame。

### single_choice · None



- [A] df.sort('score', descending=True).head(10)
- [B] df.order_by('score').limit(10)
- [C] df.sort_values('score', ascending=False)[:10]
- [D] df.top_k(10, 'score')

**参考答案**：0

**解析**：Polars 使用 sort 并设置 descending，再用 head 取前若干行。

### single_choice · None



- [A] pl.concat([df1, df2])
- [B] df1.append(df2)
- [C] df1.union(df2)
- [D] pd.concat([df1, df2])

**参考答案**：0

**解析**：Polars 提供 pl.concat 进行按行或按列的拼接。

### single_choice · None



- [A] Arrow 使用按行存储，因此随机读取一整行比按列读取更快
- [B] Arrow 使用列式存储，且数据以连续内存块保存，便于零拷贝与向量化计算
- [C] Arrow 把每个值都封装成 Python 对象，因此与 list 内存布局一致
- [D] Arrow 只能存字符串，数值类型需要先转成字符串再存储

**参考答案**：1

**解析**：Arrow 的核心设计是列式内存格式，同列数据连续存放，配合定义好的缓冲区布局，可以做到零拷贝共享与向量化运算。A 错在描述成行式；C 错在 Arrow 是紧凑的原始缓冲区，不是 Python 对象数组；D 与事实相反。

### single_choice · None



- [A] Pandas 内部就是用 Arrow 的列式缓冲区实现的
- [B] Arrow Table 与 Pandas DataFrame 可以互相转换，但转换不一定零拷贝
- [C] Arrow Table 本质上就是 Pandas DataFrame 的别名
- [D] Pandas 无法读取 Arrow Table 的数据

**参考答案**：1

**解析**：两者可以互转（例如通过 to_pandas / from_pandas 之类的接口），但只有当类型、空值表示等都兼容时才可能零拷贝，否则会发生数据复制或类型转换。A 错在 Pandas 主要是基于 NumPy 的块状存储；C 混淆了两者；D 明显不成立。

### multi_choice · None



- [A] 在类型和内存布局兼容的情况下，Arrow 数据可以在不同进程/语言间共享而无需复制
- [B] 零拷贝意味着完全不占用额外内存，包括元数据和 schema
- [C] 从 Arrow 转换成 Pandas DataFrame 时，如果类型不兼容，可能会发生复制或转换
- [D] Arrow 的列式缓冲区允许在不复制的前提下对原始数据做切片等操作

**参考答案**：[0, 2, 3]

**解析**：A、C、D 都符合 Arrow 的实际行为：兼容时可共享内存；不兼容转换会产生复制；切片等操作可在原缓冲区上完成。B 错在「完全不占额外内存」——schema、元数据、对象包装等仍需要少量内存。

### multi_choice · None



- [A] 使用列式文件格式（如 Parquet）落盘，并用 Arrow 作为内存中的交换格式
- [B] 让每种语言各自定义一套私有二进制格式，互不兼容
- [C] 尽量使用标准且类型明确的列式 schema，避免把数值都塞进字符串
- [D] 利用 Arrow 的内存布局让同一份数据在不同语言间共享，减少序列化

**参考答案**：[0, 2, 3]

**解析**：Arrow 被设计为跨语言的列式内存标准，配合 Parquet 等列式文件格式非常合适；类型清晰的 schema 也有助于减少转换开销。B 与跨语言互操作的目标相冲突。

### multi_choice · None



- [A] validity 位图让 Arrow 能区分 null 与数值 0
- [B] 对字符串列来说，空字符串和 null 是两种不同的值
- [C] 只要某列存在空值，该列所有值都必须复制成 Python 的 None 对象
- [D] 在计算是否为空时，可以借助位图快速判断而不必逐值扫描数据缓冲区

**参考答案**：[0, 1, 3]

**解析**：A、B、D 都与 Arrow 的空值位图设计一致。C 是常见误解：Arrow 用位图表示空值，并不会把数据整体转成 Python 对象，只有在显式转换时才会产生对象。

### multi_choice · None



- [A] 需要对大表按列做向量化聚合运算
- [B] 数据需要在 Python 和另一种语言编写的服务之间高速传递
- [C] 只需要在 Python 内部保存少量配置键值对
- [D] 数据要从多个 Parquet 文件读取后按列拼接成一张表

**参考答案**：[0, 1, 3]

**解析**：A 利用列式向量化优势，B 利用跨语言零拷贝，D 是 Arrow Table 拼接的典型场景。C 属于小规模配置数据，用字典更自然，Arrow 并不划算。

### fill_blank · None



**参考答案**：["validity", "validity bitmap", "有效位", "有效性", "有效性位图"]

**解析**：Arrow 用 validity 位图（有效性位图）单独记录空值，从而不占用数据本身的取值范围。

### fill_blank · None



**参考答案**：["ChunkedArray", "chunked array", "分块数组", "Chunked Array"]

**解析**：ChunkedArray 是多个 Array 的分块组合，逻辑上仍表现为一列，便于流式或分段产生数据。

### code_reading · None



**参考答案**：切片从下标 1 开始、长度为 2，因此 b 包含下标 1、2 两个元素（值 2 和 None）；长度为 2，空值数量为 1，所以输出为「2 1」。切片通常是在原缓冲区上按偏移量进行的视图操作，不一定发生复制。

**解析**：考察对切片语义与空值计数的理解：长度是切片长度，null_count 统计该切片内的空值数量。

### code_reading · None



**参考答案**：该 ChunkedArray 由两个 chunk 组成，因此 num_chunks 为 2；总长度为 2 + 3 = 5，所以 len(col) 为 5，输出为「2 5」。ChunkedArray 的长度是其所有 chunk 长度之和。

**解析**：考察对 ChunkedArray 分块结构与长度语义的理解。

### scenario · None



**解析**：参考回答：把数据转换成列式内存布局（如 Arrow Table），并约定统一的 schema；在支持的情况下让两个进程/语言共享同一块内存而不做逐行序列化，从而减少 JSON 编码解码与对象创建的开销。关键词覆盖列式、零拷贝、共享内存、序列化、schema、类型即可。

### scenario · None



**解析**：参考回答：利用列式格式的投影下推能力，只读取所需的三个列而不是整行所有列，减少 I/O；在内存中用 Arrow 的列式结构承载这些列，按列进行向量化聚合，降低对象开销与内存占用。关键词覆盖列裁剪/投影、只读需要的列、列式、Arrow、内存等即可。

### single_choice · None



- [A] 只有一段数据缓冲区
- [B] 数据类型、长度，以及可选的空值位图和多段数据缓冲区
- [C] 一个 Python 字典和若干键值对
- [D] 一个 SQLite 表名及其索引

**参考答案**：1

**解析**：Arrow 列式数组一般包含数据类型（含嵌套结构）、长度，以及 validity（空值）位图和实际数据缓冲区等。A 漏掉类型与空值信息；C、D 与 Arrow 的底层二进制模型无关。

### scenario · None



**解析**：参考回答：零拷贝是有条件的，只有当双方的内存布局、类型与空值表示等都兼容时才可能真正共享内存；如果类型不匹配（例如把 Arrow 的 decimal 转成 Python 对象或 Pandas 的某些类型），或者双方使用不同的进程边界且无法共享内存，就会发生复制或转换。所以「一定零拷贝、绝不复制」是错误的。

### single_choice · None



- [A] ChunkedArray 是分块的、由多个 Array 组成，而 Array 是单个连续数组
- [B] ChunkedArray 只能存字符串，Array 只能存数值
- [C] Array 是压缩过的，ChunkedArray 未压缩
- [D] 两者完全相同，只是名字不同

**参考答案**：0

**解析**：ChunkedArray 由多个 chunk（若干 Array）拼接而成，适合流式读取或分段产生数据；Array 是单一连续数组。B、C、D 的描述都不成立。

### single_choice · None



- [A] 因为列式格式是标准化的二进制布局，不同语言/进程可以直接共享同一块内存而无需序列化
- [B] Arrow 必须先把数据转成 JSON 才能被其他语言读取
- [C] Arrow 只支持 Python，其他语言无法访问
- [D] 共享数据时必须先把所有数据复制到磁盘文件

**参考答案**：0

**解析**：Arrow 规定了内存中列式数据的标准化二进制布局，因此不同语言或进程可以共享同一内存区域，避免序列化/反序列化开销。B、C、D 与 Arrow 的设计目标相悖。

### single_choice · None



- [A] 把所有字符串拼接成一个大字符串，另用偏移量数组记录每个字符串的起止位置
- [B] 每个字符单独存成一个整数数组
- [C] 把字符串转成定长字节，长度不足就截断
- [D] 字符串只能存放在 Python 的 list 对象里

**参考答案**：0

**解析**：Arrow 的字符串通常采用 offsets + data 两个缓冲区的变长布局，避免了在每个值上额外分配对象。B 浪费空间；C 会破坏数据；D 与 Arrow 的列式缓冲区设计无关。

### single_choice · None



- [A] Arrow 用一个独立的 validity 位图来标记哪些位置是空值
- [B] Arrow 用 0 表示空值，因此无法区分 0 和 null
- [C] Arrow 不允许存在空值
- [D] Arrow 把空值统一转换成空字符串

**参考答案**：0

**解析**：Arrow 用有效性位图（validity bitmap）单独记录空值，而不是占用数据缓冲区的特殊值，因此可以区分 0、空字符串与真正的 null。B、C、D 都不正确。

### single_choice · None



- [A] decimal 类型以及定长/变长的二进制类型
- [B] 只能使用 float64，其他都不支持
- [C] 统一转成字符串存储
- [D] 必须手动拆成多个 int32 数组

**参考答案**：0

**解析**：Arrow 为数值提供了 decimal 类型（含精度和小数位设置）以及各种整数宽度；需要二进制原始数据时也有定长或变长二进制类型。B、C、D 都不是必要或正确的做法。

### single_choice · None



- [A] RecordBatch 是带 schema 的一批列式数据，Table 可以由多个 RecordBatch 组成
- [B] RecordBatch 只能包含一列
- [C] Table 不能包含 schema
- [D] RecordBatch 与 Table 都只能存储行式数据

**参考答案**：0

**解析**：RecordBatch 是一组列式数组的集合，带有 schema；Table 通常由多个 RecordBatch 组成，也带有 schema。B、C、D 都与其结构不符。

### single_choice · None



- [A] 按需要的列选择性读取，而不是读取所有列后再丢弃不需要的
- [B] 必须先把所有列读进内存，再转换成 Python 列表
- [C] 只能逐行读取，不能按列读取
- [D] 必须先把所有文件合并成一个巨大的 JSON 文件

**参考答案**：0

**解析**：列式格式和 Arrow 的一大优势是按列裁剪（projection pushdown）读取，只加载需要的列即可显著降低 I/O 和内存。其他选项要么低效，要么与列式的优势背道而驰。
