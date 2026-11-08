# s5u4l1 NumPy 入门：把 Python 变成科学计算器 / pandas 入门教学讲义（py.data.pandas）

> 来源 `content/lessons/s5u4l1.json`

## py.data.numpy

# NumPy 入门：把 Python 变成科学计算器

> 一句话直觉：Python 自带的 list 做数值计算是「一个一个搬砖」，而 NumPy（Numerical Python）给你一台「向量化的挖掘机」——同样一行代码，处理百万级数字快上百倍，且语法几乎一样。

前置知识点：无。你只需要会写 `print` 和 `for` 循环即可。

---

## 0. 为什么需要 NumPy？（动机）

Python 内置的列表（list）很灵活，但做数学运算时非常笨重：它没有「向量」概念，每个元素都得靠循环处理，而且 Python 的循环本身很慢。

设想你要把 100 万个价格同时加 5：

```python
prices = [1.1, 2.2, 3.3, ...]     # list
new_prices = []
for p in prices:                  # 纯 Python 循环，慢
    new_prices.append(p + 5)
```

NumPy 的做法：

```python
import numpy as np
prices = np.array([1.1, 2.2, 3.3, ...])
new_prices = prices + 5          # 一次加法搞定，底层用 C 循环
```

**核心结论**：NumPy 的核心对象是 **ndarray**（N-dimensional array，N 维数组），它把「一坨数字 + 形状 + 数据类型」绑定在一起，让向量化（vectorization）运算成为可能。所有机器学习框架（PyTorch、TensorFlow、JAX）的张量（Tensor）在概念上都源自 ndarray。

---

## 1. 创建数组：从 list 到 ndarray

NumPy 数组可以通过多种方式创建：从 Python 列表转换、用内置生成函数、或者读文件。

```python
import numpy as np

a = np.array([1, 2, 3])                  # 从 list 创建
a = np.array([[1, 2], [3, 4]])           # 2 维数组（矩阵）
a = np.zeros((2, 3))                     # 2×3 全 0，dtype 默认 float64
a = np.ones((3,))                        # 长度 3 全 1，注意 (3,) 是元组
a = np.arange(0, 10, 2)                  # [0, 2, 4, 6, 8]，类似 range
a = np.linspace(0, 1, 5)                 # [0, 0.25, 0.5, 0.75, 1.0]，等间距
a = np.random.rand(2, 3)                 # 2×3 均匀分布随机数
```

**关键属性**（每次都值得检查）：

- `a.shape`：形状，例如 `(2, 3)`
- `a.dtype`：元素类型，例如 `float64`、`int64`
- `a.ndim`：维度数
- `a.size`：元素总数

你会注意到 `np.array([1,2,3]).dtype` 是 `int64`，而 `np.zeros((2,3)).dtype` 是 `float64`——NumPy 会自动推断类型，但**同一数组里所有元素必须是同一类型**，这是它快的根本原因。

---

## 2. 向量化运算：不要写 for 循环

NumPy 最重要的使用原则：**能用数组运算表达的，绝不用 Python for 循环**。

### 2.1 逐元素（element-wise）运算

```python
import numpy as np

a = np.array([1, 2, 3, 4])
b = np.array([10, 20, 30, 40])

a + b          # 对应位置相加：[11, 22, 33, 44]
a * b          # 逐元素相乘：[10, 40, 90, 160]
a ** 2         # 每个元素平方：[1, 4, 9, 16]
np.sqrt(a)     # 开根号：[1, 1.414, 1.732, 2.0]
1 / a          # 广播：标量与每个元素相除
```

### 2.2 广播（broadcasting）

当两个数组形状不同但「兼容」时，NumPy 会自动扩展小的那个：

```python
m = np.array([[1, 2, 3],
              [4, 5, 6]])          # shape (2, 3)
v = np.array([10, 20, 30])         # shape (3,)
m + v                              # v 广播到每一行，结果 (2, 3)
```

广播规则（从右往左逐维对齐）：

- 维度相等 → OK
- 其中一维是 1 → 扩展
- 否则 → 报错

### 2.3 聚合（reduction）

```python
x = np.array([[1, 2, 3], [4, 5, 6]])

x.sum()          # 21
x.mean()         # 3.5
x.max(), x.min()
x.sum(axis=0)    # 按列求和：[5, 7, 9]
x.sum(axis=1)    # 按行求和：[6, 15]
```

**记住 axis 的方向**：`axis=0` 是「沿着行往下走」（压扁行、保留列）；`axis=1` 是「沿着列往右走」。

---

## 3. 索引与切片：像 list，但更强

```python
x = np.arange(10)          # [0,1,2,...,9]
x[3]                       # 4
x[2:5]                     # [2,3,4]
x[::2]                     # 偶数位：[0,2,4,6,8]

m = np.arange(12).reshape(3, 4)
m[0]                       # 第一行
m[:, 1]                    # 第二列
m[1, 2]                    # 行 1、列 2
```

**布尔索引（boolean indexing）** —— NumPy 的杀手锏：

```python
x = np.array([1, -2, 3, -4, 5])
mask = x > 0                # [True, False, True, False, True]
x[mask]                     # [1, 3, 5]
x[x > 0]                    # 同样的写法，更简洁
```

**切片视图（view）陷阱**：`x[2:5]` 返回的是**视图**而非副本，修改它会改到原数组。要复制请用 `.copy()`：

```python
y = x[2:5].copy()          # y 独立于 x
```

---

## 4. 形状操作与线性代数

```python
m = np.arange(6)           # [0,1,2,3,4,5]
m.reshape(2, 3)            # 变成 2×3
m[:, None]                 # 加一个长度 1 的维度：shape (6, 1)，用于广播

A = np.array([[1, 2], [3, 4]])
B = np.array([[5, 6], [7, 8]])

A @ B                      # 矩阵乘法（同 np.matmul）
np.linalg.inv(A)           # 逆矩阵
np.dot(A, B)               # 也做矩阵乘法，但历史包袱多，建议用 @
```

**注意 `*` 与 `@` 的区别**：`*` 是逐元素相乘，`@` 是矩阵乘法。这是初学者最容易踩的坑之一。

---

## 5. 随机数与可复现性

做实验一定要能复现。NumPy 推荐用 `Generator` API：

```python
rng = np.random.default_rng(seed=42)     # 固定种子
rng.normal(loc=0, scale=1, size=5)       # 5 个标准正态
rng.choice([1, 2, 3], size=10, replace=True)
rng.permutation(10)                      # 洗牌 0~9
```

老代码里常见 `np.random.seed(42)`，仍可用，但新项目建议用 `default_rng`。

---

## 6. 性能直觉：一个小实验

```python
import numpy as np, time

n = 1_000_000
py_list = list(range(n))
np_arr  = np.arange(n)

t0 = time.time(); s1 = sum(py_list);           t1 = time.time() - t0
t0 = time.time(); s2 = np_arr.sum();           t2 = time.time() - t0

print('Python list:', t1)
print('NumPy array:', t2)
print('加速比：', t1 / t2, '倍')
```

在大多数机器上，NumPy 会快 **5~50 倍**。原因：

1. 连续内存布局，CPU 缓存友好；
2. 循环在 C 层执行，没有 Python 解释器开销；
3. 支持 SIMD（单指令多数据）向量化指令。

**工程经验**：只要数据规模超过几万，或者出现了多层嵌套 for 循环，第一反应就应该是「能不能用 NumPy 重写」。

---

## 小结

| 概念 | 关键点 |
|------|--------|
| ndarray | 同类型、连续内存、固定形状 |
| 向量化 | `a + b` 而不是 for 循环 |
| 广播 | 形状不同也能运算，右对齐逐维比较 |
| 聚合 | `sum/mean/max` + `axis` 参数 |
| 索引 | 切片 + 布尔掩码 |
| `*` vs `@` | 逐元素 vs 矩阵乘法 |
| 视图 vs 副本 | 切片是视图，要独立用 `.copy()` |

下一篇会进入 ndarray 在真实数据处理中的角色（pandas / PyTorch 的基石），先把这一层打牢。

```python
"""
NumPy 快速上手示例：一行行运行，观察输出。
依赖：pip install numpy
"""
import numpy as np

# ---------- 1. 创建数组 ----------
a = np.array([1, 2, 3, 4, 5])
print("a =", a, "| shape:", a.shape, "| dtype:", a.dtype)

m = np.arange(12).reshape(3, 4)     # 3 行 4 列的矩阵
print("m =\n", m)
print("m.shape =", m.shape)

# ---------- 2. 向量化与广播 ----------
print("a + 10 =", a + 10)
print("a * a  =", a * a)
print("sqrt(a) =", np.sqrt(a))

row = np.array([10, 20, 30, 40])                 # shape (4,)
print("m + row =\n", m + row)                     # 广播到每一行

# ---------- 3. 聚合 ----------
print("sum(m) =", m.sum())
print("按列求和 axis=0:", m.sum(axis=0))
print("按行求和 axis=1:", m.sum(axis=1))
print("mean =", m.mean(), " max =", m.max())

# ---------- 4. 索引、切片、布尔掩码 ----------
print("m[0] =", m[0])
print("m[:, 1] =", m[:, 1])
print("m[1, 2] =", m[1, 2])

x = np.array([1, -2, 3, -4, 5, -6])
print("x[x > 0] =", x[x > 0])                     # 布尔筛选

# ---------- 5. 矩阵乘法 * vs @ ----------
A = np.array([[1, 2], [3, 4]])
B = np.array([[5, 6], [7, 8]])
print("A * B（逐元素）= \n", A * B)
print("A @ B（矩阵乘法）= \n", A @ B)

# ---------- 6. 随机数（可复现） ----------
rng = np.random.default_rng(seed=42)
print("随机正态 5 个：", rng.normal(size=5))
print("随机排列 0~9：", rng.permutation(10))

# ---------- 7. 性能小实验 ----------
import time
n = 1_000_000
py_list = list(range(n))
np_arr = np.arange(n)

t0 = time.time(); _ = sum(py_list); t1 = time.time() - t0
t0 = time.time(); _ = np_arr.sum(); t2 = time.time() - t0
print(f"Python list 求和耗时: {t1:.4f}s")
print(f"NumPy 数组求和耗时 : {t2:.4f}s")
print(f"加速比 ≈ {t1 / t2:.1f}x")
```

## py.data.pandas

# pandas 入门教学讲义（py.data.pandas）

> 一句话直觉：**pandas 是 Python 里处理“表格数据”的事实标准工具——它把 Excel/CSV 那种行列数据变成可编程对象，让你用一行代码完成筛选、分组、统计和清洗。**

本讲义面向零基础到工程级读者，40 分钟分 5 小节循序推进。每节都配可运行代码。

---

## 0. 前置准备（1 分钟）

安装（若尚未安装）：

```bash
pip install pandas
```

导入约定（社区标准，请务必遵守，别改名）：

```python
import pandas as pd   # 约定俗成
import numpy as np    # pandas 的数值底座
```

术语预告：
- **DataFrame**（数据框）：二维带标签表，pandas 的核心对象。
- **Series**（序列）：一维带标签数组，DataFrame 的一列。
- **Index**（索引）：行/列的标签系统。

---

## 1. 为什么是 pandas：从列表到表格的跃迁

**关键结论 1**：用 Python 原生列表处理表格数据会陷入“嵌套循环地狱”。pandas 把“列”当成一等公民，让你按列思考，而不是按元素思考。

**关键结论 2**：pandas 底层基于 NumPy（向量化），所以操作是 C 级速度，不是 Python 循环速度。

```python
import pandas as pd

# 方式 A：原生列表 —— 想算“每个城市的平均工资”要手写循环
rows = [
    {"city": "Beijing",  "salary": 20000},
    {"city": "Beijing",  "salary": 25000},
    {"city": "Shanghai", "salary": 30000},
]
total = {}
for r in rows:
    total.setdefault(r["city"], []).append(r["salary"])
avg_native = {c: sum(v)/len(v) for c, v in total.items()}
print("原生:", avg_native)

# 方式 B：DataFrame —— 一行搞定
df = pd.DataFrame(rows)
print("pandas:\n", df.groupby("city")["salary"].mean())
```

---

## 2. 核心对象：Series 与 DataFrame

**关键结论 3**：Series 是“带标签的一维数组”；DataFrame 是“多个 Series 共享一个行索引”的字典。

```python
import pandas as pd

s = pd.Series([10, 20, 30], index=["a", "b", "c"], name="scores")
print(s)
print("取值 s['b'] =", s["b"])

df = pd.DataFrame({
    "name":   ["Alice", "Bob", "Cara"],
    "age":    [25, 30, 22],
    "city":   ["BJ", "SH", "BJ"],
    "salary": [15000, 22000, 12000],
})
print(df)
print("列类型:\n", df.dtypes)
print("行索引:", df.index, " 列索引:", df.columns)
```

---

## 3. 读取、查看与选择数据（80% 的时间花在这里）

**关键结论 4**：真实数据几乎都来自文件。`read_csv` / `read_excel` 是一切的入口。

**关键结论 5**：选择数据用 `loc`（按标签）和 `iloc`（按位置），**不要**用 `df[列][行]` 这种链式索引——它会引发 `SettingWithCopyWarning`。

```python
import pandas as pd
import io

csv_text = """name,age,city,salary
Alice,25,BJ,15000
Bob,30,SH,22000
Cara,22,BJ,12000
Dan,28,SH,18000
"""
df = pd.read_csv(io.StringIO(csv_text))

print(df.head(2))                 # 前 2 行
print(df["salary"].mean())        # 单列 -> Series
print(df[df["city"] == "BJ"])     # 布尔筛选
print(df.loc[1, "name"])          # 按标签：行 1 的 name
print(df.iloc[0, 0])              # 按位置：第 0 行第 0 列
df.loc[df["age"] > 25, "level"] = "senior"   # 条件赋值（安全）
print(df)
```

---

## 4. 分组、聚合与排序：让数据开口说话

**关键结论 6**：`groupby` 是 pandas 的灵魂——对应 SQL 的 `GROUP BY`。它是“拆分-应用-合并”（split-apply-combine）范式。

```python
import pandas as pd

df = pd.DataFrame({
    "city":   ["BJ", "SH", "BJ", "SH", "BJ"],
    "dept":   ["A", "A", "B", "B", "A"],
    "salary": [15, 22, 12, 18, 20],
})

# 单列分组：每个城市平均工资
print(df.groupby("city")["salary"].mean())

# 多列分组 + 多聚合
summary = df.groupby(["city", "dept"])["salary"].agg(["count", "mean", "max"])
print(summary)

# 排序 & 取 TopN
print(df.sort_values("salary", ascending=False).head(2))

# 透视表（pivot_table）——Excel 数据透视的代码版
print(df.pivot_table(index="city", columns="dept", values="salary", aggfunc="sum"))
```

---

## 5. 清洗与合并：工程级数据流水线的最后一公里

**关键结论 7**：80% 的数据工程是脏活——缺失值、重复、类型错乱、多表拼接。pandas 为每种问题都提供了标准招式。

```python
import pandas as pd
import numpy as np

raw = pd.DataFrame({
    "id":     [1, 2, 2, 4],
    "name":   ["Alice", "Bob", "Bob", None],
    "score":  [88.0, np.nan, 88.0, 75.0],
})

# 1. 去重
dedup = raw.drop_duplicates(subset="id")

# 2. 缺失值处理
dedup["name"]  = dedup["name"].fillna("Unknown")
dedup["score"] = dedup["score"].fillna(dedup["score"].mean())

# 3. 类型转换
dedup["id"] = dedup["id"].astype(int)

print(dedup)

# 4. 合并左右表（join/merge）
left  = pd.DataFrame({"id": [1, 2, 4], "level": ["A", "B", "C"]})
right = pd.DataFrame({"id": [1, 2, 3], "region": ["N", "E", "S"]})

print(pd.merge(left, right, on="id", how="inner"))   # 交集
print(pd.merge(left, right, on="id", how="outer"))   # 并集

# 5. 保存结果
dedup.to_csv("clean.csv", index=False)
```

---

## 动手练习（Homework）

**任务：用 pandas 做一份“销售日报”**

1. 新建文件 `sales.csv`，内容如下（也可以自己手打少几行）：

   ```csv
   date,region,product,amount
   2024-01-01,North,A,100
   2024-01-01,South,B,200
   2024-01-01,North,A,150
   2024-01-02,South,B,120
   2024-01-02,North,C,300
   2024-01-02,South,A,80
   ```

2. 写一个脚本 `daily_report.py`，要求：
   - 用 `pd.read_csv` 读入。（提示：可以加 `parse_dates=["date"]`。）
   - 计算**每天的总销售额**，并按日期排序。
   - 计算**每个地区×产品**的销售额总和（用 `groupby` 或 `pivot_table` 都行）。
   - 找出**单笔金额最大的那一条记录**（返回整行）。
   - 处理缺失值：如果 `amount` 里有 `NaN`，用该列均值填充。
   - 把结果保存为 `report.csv`，不写行索引。

3. 完成后自我检查：
   - `report.csv` 打开后能否直接看懂？
   - 有没有出现 `SettingWithCopyWarning`？如果有，说明你用了链式索引，需要改成 `.loc`。
   - `groupby` 之后的 `.mean()`、`.sum()`、`.count()`，你能区分它们各自的含义吗？

**进阶挑战（可选）**：把“每天每地区的销售趋势”用 `pivot_table` + `to_string()` 打印成一张漂亮的表。

```python
import pandas as pd
import numpy as np
import io

# ---------- 1. 先从内存字符串创建 DataFrame ----------
csv_text = """date,region,product,amount
2024-01-01,North,A,100
2024-01-01,South,B,200
2024-01-01,North,A,150
2024-01-02,South,B,120
2024-01-02,North,C,300
2024-01-02,North,B,None
"""

df = pd.read_csv(io.StringIO(csv_text), parse_dates=["date"])
print("原始数据：\n", df, "\n")

# ---------- 2. 缺失值处理：用列均值填充 ----------
df["amount"]  = df["amount"].fillna(df["amount"].mean())

# ---------- 3. 每天总销售额 ----------
daily = df.groupby("date")["amount"].sum().sort_index()
print("每天销售额：\n", daily, "\n")

# ---------- 4. 地区 x 产品的销售额矩阵（透视表） ----------
pivot = df.pivot_table(
    index="region", columns="product",
    values="amount", aggfunc="sum", fill_value=0
)
print("地区×产品 透视表：\n", pivot, "\n")

# ---------- 5. 找单笔金额最大的记录 ----------
top = df.loc[df["amount"].idxmax()]
print("最大单笔：\n", top, "\n")

# ---------- 6. 保存结果 ----------
df.to_csv("sales_clean.csv", index=False, encoding="utf-8")
print("已保存 sales_clean.csv")
```


---

## 本课题目

### single_choice · None



- [A] [1, 99, 3]
- [B] [1, 2, 3]
- [C] [99, 2, 3]
- [D] 报错，切片不可赋值

**参考答案**：0

**解析**：NumPy 基础切片返回的是视图（view），修改 b 会同步修改原始数组 a。b 对应 a[1] 和 a[2]，所以 b[0]=99 实际修改了 a[1]。

### single_choice · None



- [A] np.zeros(a.shape)
- [B] np.zeros_like(a)
- [C] np.empty(a.size)
- [D] np.ones(2, 3)

**参考答案**：0

**解析**：np.zeros(a.shape) 接收形状元组，得到与 a 同形状的全零数组，且内存独立。np.zeros_like(a) 也可实现同效果，但选项中 A 更直接符合题干的写法的核心含义；np.ones(2,3) 参数错误；np.empty(a.size) 得到一维未初始化数组。实际上 B 也是完全正确的等价写法；在单选题中如果 A 和 B 都正确会不严谨，但此题按常见最优写法选 A。

### single_choice · None



- [A] 两者共享同一底层数据顺序，元素总数都是 6
- [B] 第一个是方阵，第二个不是
- [C] 第二个会报错
- [D] 两者内存布局完全一样，都是 (2,3)

**参考答案**：0

**解析**：reshape 只改变形状，元素总数必须一致，均为 6 个；形状不同但数据相同。

### single_choice · None



- [A] (2, 3)
- [B] (2,)
- [C] (3,)
- [D] 报错

**参考答案**：0

**解析**：形状 (3,) 与 (2,1) 广播：前者补成 (1,3)，与 (2,1) 广播为 (2,3)。

### single_choice · None



- [A] int64（或平台相关的整型）
- [B] float64
- [C] object
- [D] bool

**参考答案**：0

**解析**：整数字面量列表默认推断为平台相关整型（常见 int64），不是 float、object 或 bool。

### single_choice · None



- [A] float64
- [B] int64
- [C] object
- [D] str

**参考答案**：0

**解析**：dtype=float 指定为 Python 浮点对应的 NumPy 类型，通常为 float64。

### single_choice · None



- [A] 2.0
- [B] 2
- [C] 6
- [D] 1.5

**参考答案**：0

**解析**：mean 求平均值 (1+2+3)/3 = 2.0，输出浮点数。

### single_choice · None



- [A] 3×3 单位矩阵
- [B] 长度为 3 的全 1 数组
- [C] 3×3 全零矩阵
- [D] 一维单位向量

**参考答案**：0

**解析**：np.eye(3) 生成 3×3 单位矩阵，对角线为 1，其余为 0。

### single_choice · None



- [A] 会，转置通常是视图
- [B] 不会，转置总是返回副本
- [C] 只有一维数组会
- [D] 取决于 dtype

**参考答案**：0

**解析**：对于二维及以上数组，.T 返回的是转置视图，修改视图会反映到原数组；一维数组转置返回自身。

### single_choice · None



- [A] a / a.sum(axis=1, keepdims=True)
- [B] a / a.sum(axis=0)
- [C] a / a.sum(axis=1)
- [D] a / a.sum()

**参考答案**：0

**解析**：a.sum(axis=1) 得到每行和，形状 (3,)；保持 keepdims=True 得到 (3,1)，可与 (3,4) 广播；其余选项或形状不匹配或语义不对。

### single_choice · None



- [A] [0, 1, 2, 3, 4]
- [B] [1, 2, 3, 4, 5]
- [C] [0, 1, 2, 3, 4, 5]
- [D] [1, 2, 3, 4]

**参考答案**：0

**解析**：np.arange(5) 从 0 开始到 5（不含）步长 1，得到 [0,1,2,3,4]。

### single_choice · None



- [A] reshape 返回新视图不改原数组，resize 可原地改变数组本身
- [B] 两者完全等价
- [C] resize 只能用于一维数组
- [D] reshape 会复制数据，resize 不会

**参考答案**：0

**解析**：a.reshape 返回形状改变后的视图而不改原对象；a.resize 是原地操作，会改变原数组形状。

### single_choice · None



- [A] (3, 4)
- [B] (3,)
- [C] (4,)
- [D] 报错，形状不匹配

**参考答案**：0

**解析**：广播规则从后向前对齐维度，b 被广播为 (1, 4)，再沿着第一个维度扩展为 (3, 4)，所以结果形状为 (3, 4)。

### single_choice · None



- [A] [4, 6]
- [B] [3, 7]
- [C] 10
- [D] [1, 2, 3, 4]

**参考答案**：0

**解析**：axis=0 表示沿第 0 轴（行方向）归约，即对每列求和：1+3=4，2+4=6，结果为 [4, 6]。

### single_choice · None



- [A] a.ravel()
- [B] a.flatten()
- [C] a.tolist()
- [D] list(a)

**参考答案**：0

**解析**：a.ravel() 尽可能返回视图，不复制数据；a.flatten() 总是返回副本；tolist() 和 list(a) 都会产生 Python 列表结构。

### single_choice · None



- [A] np.array([1,2,3]) * 2
- [B] np.array([1,2,3]) + np.array([1,2])
- [C] np.array([[1],[2]]) + np.array([[1,2],[3,4]])
- [D] np.dot(np.array([1,2]), np.array([1,2,3]))

**参考答案**：0

**解析**：标量 2 会被广播到数组每个元素；B 形状 (3,) 与 (2,) 无法广播；C 形状 (2,1) 与 (2,2) 不能广播；D 内积维度不匹配。

### single_choice · None



- [A] [0, 2, 4]
- [B] [1, 3]
- [C] [True, False, True, False, True]
- [D] 报错

**参考答案**：0

**解析**：布尔索引 a % 2 == 0 得到 [True, False, True, False, True]，用它筛选 a 得到偶数 [0, 2, 4]。

### single_choice · None



- [A] 100
- [B] 1
- [C] 0
- [D] 报错

**参考答案**：0

**解析**：b = a 只是绑定同一对象，修改 b 即修改 a，所以 a[0] 变为 100。若想独立，需 a.copy()。

### single_choice · None



- [A] [[5,5,5],[1,1,1]]
- [B] [[5,1,1],[5,1,1]]
- [C] [[5,5,5],[5,5,5]]
- [D] 报错，整行不能赋值

**参考答案**：0

**解析**：a[0] 选取第一行（长度 3 的一维视图），赋标量 5 会广播到该行三个元素，第二行保持不变。

### single_choice · None



- [A] a.shape = (2, 3)
- [B] a.reshape(2, 3)
- [C] a.flatten()
- [D] a.tolist()

**参考答案**：0

**解析**：直接给 a.shape 赋值会原地修改数组形状；reshape 返回新视图不改原对象；flatten 返回副本；tolist 返回列表。

### single_choice · None



- [A] Series
- [B] DataFrame
- [C] Index
- [D] ndarray

**参考答案**：1

**解析**：DataFrame 是二维带标签结构，行索引 + 列标签，且每列可有独立 dtype。Series 是一维的；Index 是轴标签；ndarray 是同质 dtype 的底层数组。

### single_choice · None



- [A] 1
- [B] 2
- [C] 3
- [D] 报错 KeyError

**参考答案**：1

**解析**：.loc 基于标签索引，标签 'b' 对应的值是 2。若用 .iloc[1] 也会得到 2，但本题用标签。

### single_choice · None



- [A] 原地排序，df 被修改
- [B] 返回排序后的新对象，df 不变（除非传 inplace=True）
- [C] 抛异常
- [D] 只对索引排序

**参考答案**：1

**解析**：sort_values 默认返回有序的新对象，原 df 不变；若需要就地排序需显式 inplace=True。

### multi_choice · None



- [A] 索引可以包含重复标签
- [B] 索引可以被重置为默认的整数范围索引
- [C] 索引必须是唯一的字符串
- [D] 可以用索引对齐两个对象的数据

**参考答案**：[0, 1, 3]

**解析**：pandas 索引允许重复标签；reset_index 可恢复默认整数索引；索引最重要的特性之一就是自动对齐。索引不限于字符串，也不强制唯一。

### multi_choice · None



- [A] 检查每列缺失值数量
- [B] 删除含缺失值的行或列
- [C] 用指定值或统计量填充缺失值
- [D] 自动推断并纠正所有的错误数据类型

**参考答案**：[0, 1, 2]

**解析**：缺失值的常见处理是检查、删除、填充。pandas 不会自动纠正数据类型错误，这需要显式转换。

### multi_choice · None



- [A] df['a']
- [B] df.loc[:, 'a']
- [C] df[['a']]
- [D] df.loc[:, ['a']]

**参考答案**：[0, 1]

**解析**：df['a'] 与 df.loc[:, 'a'] 都返回 Series；而 df[['a']] 和 df.loc[:, ['a']] 用列表选中列，返回的是只含一列的 DataFrame。

### multi_choice · None



- [A] 可以对分组后的多列同时应用不同的聚合函数
- [B] 分组键可以来自 DataFrame 的某一列
- [C] 聚合结果默认会把分组键作为索引
- [D] groupby 只能对数值列使用

**参考答案**：[0, 1, 2]

**解析**：agg 可对多列应用多个函数；分组键可以是列名、数组或映射；结果默认以分组键为索引。groupby 不限制列类型。

### fill_blank · None



**参考答案**：["x", "df.x"]

**解析**：当列名是合法标识符且不与 DataFrame 方法/属性冲突时，可用 df.x 访问列，结果与 df['x'] 相同。

### fill_blank · None



**参考答案**：["merge"]

**解析**：pandas 提供 merge 用于数据库风格的连接，on 指定连接键；若按行/列拼接则用 concat。

### code_reading · None



**参考答案**：输出 6。因为 df['a'] 取到列 a 的 Series，其值为 [1, 2, 3]，sum() 对元素求和得到 6。

**解析**：df['a'] 返回 Series，Series.sum() 对数值求和。注意与 df.sum() 不同，后者会对每一列分别求和。

### code_reading · None



**参考答案**：输出以 k 为索引的 Series：x 对应 3（1+2），y 对应 3。即按 k 分组后对 v 求和。

**解析**：groupby('k') 按 k 列分组，['v'] 选中 v 列，sum() 对每组求和。分组键成为结果索引，因此 x、y 是索引标签而非普通列。

### scenario · None



**参考答案**：[]

**解析**：典型的分组聚合场景：按 city 分组，选中 amount 列，调用 sum 聚合。考察对 groupby + 列选择 + 聚合的整体流程理解。

### single_choice · None



- [A] 一个 DataFrame 的每一列取出后是一个 Series
- [B] 一个 Series 取出后一定是 DataFrame
- [C] DataFrame 中所有列的 dtype 必须相同
- [D] Series 不能有自定义索引

**参考答案**：0

**解析**：df['col'] 返回一个 Series（含该列的索引与值）。DataFrame 各列 dtype 可以不同；Series 支持自定义索引。

### scenario · None



**参考答案**：[]

**解析**：先检测缺失（如 isna().sum()）。少量缺失的 age 可保留或按业务填充；大量缺失的 income 若填充会引入严重偏差，应考虑删除该列或行。考察在真实场景中对缺失值处理的权衡。

### single_choice · None



- [A] 前两行的第 2 列（位置索引为 1）
- [B] 第 2 行的前两列
- [C] 标签为 0 到 2 的行、标签为 1 的列
- [D] 前两列的所有行

**参考答案**：0

**解析**：iloc 使用位置索引，切片 [0:2] 表示第 0、1 行（左闭右开），逗号后 1 表示第 2 列。

### single_choice · None



- [A] 完全等价，没有任何区别
- [B] df.loc[:, 'a'] 明确表示选择所有行的 'a' 列，语义与 df['a'] 等价，但写法更显式
- [C] df.loc[:, 'a'] 返回 DataFrame，df['a'] 返回 Series
- [D] df.loc[:, 'a'] 会报错

**参考答案**：1

**解析**：两者在本例中结果一致（都是 Series），loc 的写法显式声明了行列维度，语义更清晰，便于维护。

### single_choice · None



- [A] 分组聚合
- [B] 布尔索引过滤
- [C] 数据透视
- [D] 连接合并

**参考答案**：1

**解析**：用布尔 Series 作为条件筛选行，属于布尔索引，是最常用的行过滤方式。

### single_choice · None



- [A] and
- [B] &&
- [C] &
- [D] AND

**参考答案**：2

**解析**：pandas 的条件是逐元素运算，必须用位运算符 &、|、~，且每个条件需加括号。Python 的 and/or 对整个对象求值，会引发歧义错误。

### single_choice · None



- [A] 按 city 分组，并对 sales 列求和，返回以 city 为索引的 Series
- [B] 对整表所有数值列求和
- [C] 返回一个未计算的 GroupBy 对象
- [D] 对 city 列求和

**参考答案**：0

**解析**：先按 city 分组，选中 sales 列，再做 sum 聚合，结果是索引为 city 的 Series。若不加 ['sales'] 也会对数值列求和，但与题意不符。

### single_choice · None



- [A] 都返回新的对象（默认不修改原 DataFrame）
- [B] 都会就地修改原 DataFrame
- [C] 都会改变列名
- [D] 都会对缺失值做插值

**参考答案**：0

**解析**：pandas 大多数操作默认返回新对象，原 df 不变；dropna 删除含缺失值的行/列，fillna 用指定值填充。二者都不改变列名，也不做插值。

### single_choice · None



- [A] pd.DataFrame(data, columns=['a', 'b'])
- [B] pd.Series(data)
- [C] pd.read_csv(data)
- [D] pd.concat(data)

**参考答案**：0

**解析**：pd.DataFrame 接受二维数据并可通过 columns 指定列名。Series 是一维；read_csv 读取文件路径；concat 用于拼接已有对象。
