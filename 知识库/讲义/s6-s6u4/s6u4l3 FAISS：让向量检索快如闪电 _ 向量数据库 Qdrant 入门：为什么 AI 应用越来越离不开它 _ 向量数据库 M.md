# s6u4l3 FAISS：让向量检索快如闪电 / 向量数据库 Qdrant 入门：为什么 AI 应用越来越离不开它 / 向量数据库 Milvus 入门：从零到工程级

> 来源 `content/lessons/s6u4l3.json`

## ai.vec.faiss

# FAISS：让向量检索快如闪电

## 一句话直觉

当你把 100 万条文本变成 100 万条向量后，用户搜一句话，你需要**在毫秒内**从 100 万条里找最相似的 10 条——**FAISS 就是干这件事的引擎**。

---

## 1. 为什么需要向量检索？

### 1.1 从关键词到语义

传统搜索靠**关键词匹配**（keyword matching）：搜“银行 利率”，只返回含这两个词的文档。但用户写“存钱能赚多少”，语义相同，词却不一样。

**向量检索**（vector retrieval）先把每条内容（文本、图片、音频）用 AI 模型编码（encode）成一个**高维向量**（embedding）。语义相近的内容，向量在空间中**距离近**。检索时，把查询也编码成向量，找**最近邻**（Nearest Neighbor, NN）。

```python
# 用一句话理解：向量就是语义坐标
# 假设 3 维向量（真实通常 384~1536 维）
v_dog   = [0.9, 0.1, 0.0]   # “狗”
v_puppy = [0.85, 0.15, 0.0] # “小狗” —— 与狗很近
v_stock = [0.0, 0.1, 0.95]  # “股票” —— 与狗很远
```

### 1.2 暴力搜索的代价

假设有 N 条向量，维度 d，每次查询要和每一条算距离：

- 距离计算量：N × d 次浮点乘加
- N = 1,000,000，d = 768 时，约 7.68 亿次运算 → 单次可能几百毫秒
- 在线上服务里，这是**不可接受的**（目标 < 10 ms）

FAISS 的核心价值：**把暴力 O(N) 降到近似 O(log N) 或 O(√N)**，同时保持高召回率（recall）。

---

## 2. FAISS 是什么？

**FAISS**（Facebook AI Similarity Search）是 Meta 开源的**向量相似度搜索库**（library），用 C++ 编写、提供 Python 接口，专门做**稠密向量**（dense vector）的高效检索。

它的定位：

| 维度 | 说明 |
|------|------|
| 不是数据库 | FAISS 是**库**，不是服务；没有 SQL、没有持久化事务 |
| 不是模型 | 只负责“存向量 + 找近邻”，不产生向量 |
| 强项 | 十亿级向量的毫秒级检索；支持 CPU / GPU |
| 弱项 | 不负责元数据过滤、分布式、动态增删（需自己封装） |

一句话：**FAISS 是向量检索的“发动机”，不是“整车”**。

---

## 3. 核心概念：索引（Index）

FAISS 里一切围绕 **Index** 对象。创建、添加、查询三步走：

### 3.1 最小可运行例子

```python
import numpy as np
import faiss

# 1. 准备数据：1000 条 64 维向量
d = 64
nb = 1000
rng = np.random.default_rng(42)
# float32 是 FAISS 要求的类型（不支持 float64）
xb = rng.random((nb, d), dtype=np.float32)

# 2. 建索引：最简单的暴力索引 IndexFlatL2
index = faiss.IndexFlatL2(d)   # L2 距离
print("是否已训练:", index.is_trained)  # Flat 无需训练
index.add(xb)                  # 把向量加入索引
print("已存向量数:", index.ntotal)

# 3. 查询：找最近的 5 个邻居
nq = 1
xq = rng.random((nq, d), dtype=np.float32)
k = 5
D, I = index.search(xq, k)     # D=距离, I=下标
print("距离:", D)
print("邻居 id:", I)
```

关键 API：

- `IndexFlatL2(d)`：维度 d 的**暴力精确**索引，最简单、最准、最慢。
- `index.add(x)`：加入 N×d 的 `float32` 数组。
- `index.search(xq, k)`：返回 `(距离, id)`，形状均为 `(nq, k)`。
- `index.ntotal`：索引中向量总数。

### 3.2 距离度量：L2 还是内积？

| 索引类 | 距离 | 用于 |
|--------|------|------|
| `IndexFlatL2` | 欧氏距离平方 | 通用 |
| `IndexFlatIP` | 内积（inner product） | 向量已归一化时等价于余弦相似度 |

```python
import faiss, numpy as np

# 归一化后，内积 = 余弦相似度
xb = np.random.rand(100, 32).astype(np.float32)
faiss.normalize_L2(xb)

index_ip = faiss.IndexFlatIP(32)
index_ip.add(xb)

xq = np.random.rand(1, 32).astype(np.float32)
faiss.normalize_L2(xq)
scores, ids = index_ip.search(xq, 3)
print(scores)  # 越大越相似
```

---

## 4. 进阶：让检索更快（近似索引）

`IndexFlatL2` 的复杂度是 O(N·d)。当 N 到百万、千万级时，需要**近似最近邻**（Approximate Nearest Neighbor, ANN）索引，牺牲一点点召回率换巨大速度。

### 4.1 IVF：先聚类再搜索

**IVF**（Inverted File，倒排文件）先用 k-means 把向量空间分成 `nlist` 个聚类，查询时只搜最近几个聚类（`nprobe` 个）。

```python
import faiss, numpy as np

d = 128
xb = np.random.rand(100_000, d).astype(np.float32)

nlist = 100      # 聚类数
quantizer = faiss.IndexFlatL2(d)                # 用于分配聚类
index = faiss.IndexIVFFlat(quantizer, d, nlist)

# IVF 必须先训练，才能 add
index.train(xb)
index.add(xb)

# nprobe 越大越准越慢
index.nprobe = 10
D, I = index.search(xb[:5], 5)
print(I)
```

经验法则：`nlist ≈ 4 * sqrt(N)`；`nprobe` 取 `nlist` 的 1%~10%。

### 4.2 PQ：压缩向量省内存

**PQ**（Product Quantization，乘积量化）把 d 维向量切段，每段用一个编号近似。能把内存压缩几十倍，代价是精度下降。

```python
import faiss, numpy as np

d = 128
xb = np.random.rand(200_000, d).astype(np.float32)

m = 16                     # 切成 16 段，每段 8 维
index = faiss.IndexIVFPQ(faiss.IndexFlatL2(d), d, nlist=100, M=m, nbits=8)
index.train(xb)
index.add(xb)
index.nprobe = 10
D, I = index.search(xb[:3], 5)
print(I.shape)
```

### 4.3 保存与加载索引

生产环境不能每次重建索引。`write_index` / `read_index` 即可持久化：

```python
import faiss
faiss.write_index(index, "my.index")
loaded = faiss.read_index("my.index")
print(loaded.ntotal)
```

---

## 5. 工程级使用要点

1. **数据类型**：向量必须 `np.float32` 且**连续内存**（`np.ascontiguousarray`）。否则 FAISS 会抛异常或悄悄复制。
2. **维度一致**：索引维度 = 建索引时传入的 d；后续 add/search 必须一致。
3. **归一化**：用余弦相似度时，先 `faiss.normalize_L2(x)` 再用 `IndexFlatIP`；或直接用 `IndexFlatIP` 并记录是否已归一化。
4. **ID 映射**：FAISS 返回的 id 是**添加顺序**的 0,1,2,…。要映射到业务 ID，用 `IndexIDMap`：

```python
import faiss, numpy as np
base = faiss.IndexFlatL2(64)
index = faiss.IndexIDMap(base)

xb = np.random.rand(5, 64).astype(np.float32)
ids = np.array([1001, 1002, 1003, 1004, 1005], dtype=np.int64)
index.add_with_ids(xb, ids)

D, I = index.search(xb[:1], 2)
print(I)  # 会返回业务 ID 而不是 0,1
```

5. **CPU / GPU**：`faiss.StandardGpuResources()` + `faiss.index_cpu_to_gpu(res, 0, index)` 可把索引搬到 GPU，适合离线批量或高并发在线。
6. **召回评估**：用 `IndexFlatL2` 的结果当“金标准”，比较近似索引的 recall@k。

```python
import faiss, numpy as np
d, N = 64, 10000
xb = np.random.rand(N, d).astype(np.float32)
flat = faiss.IndexFlatL2(d); flat.add(xb)
ivf_q = faiss.IndexFlatL2(d)
ivf = faiss.IndexIVFFlat(ivf_q, d, nlist=100)
ivf.train(xb); ivf.add(xb); ivf.nprobe = 10

xq = np.random.rand(50, d).astype(np.float32)
_, I_flat = flat.search(xq, 10)
_, I_ivf  = ivf.search(xq, 10)
recall = np.mean([len(set(a) & set(b)) / 10 for a, b in zip(I_flat, I_ivf)])
print("recall@10 =", recall)
```

---

## 小结

- FAISS 解决**高维向量的近邻搜索**，是 RAG、推荐、去重、以图搜图等场景的基础设施。
- 掌握三步：**建索引 → add → search**。
- 从 `IndexFlatL2` 起步，规模大了换 **IVF**、**IVFPQ**。
- 生产落地注意 **float32、归一化、ID 映射、索引持久化、召回评估**。

## ai.vec.qdrant

# 向量数据库 Qdrant 入门：为什么 AI 应用越来越离不开它

**一句话直觉**：当你有几十万条文本、图片或用户行为的"向量表示"，想知道"和这条最像的 Top-K 是谁"时，Qdrant 就是那个能在毫秒内回答你的专业引擎——它把"相似度搜索"做成了数据库级别的基础设施。

---

## 1. 从问题出发：为什么不直接用 NumPy 算余弦相似度？

向量（Vector）是一串浮点数，例如 `[0.12, -0.9, 0.33, ...]`，常常有 384、768、1536 维。给定一条查询向量（Query Vector），要找出库里与之最相似的 K 条，这叫 **最近邻搜索（Nearest Neighbor Search, 简称 NN）**。

Naïve 做法是把所有向量读进内存，逐个算**余弦相似度（Cosine Similarity）**或**内积（Inner Product，也叫点积 Dot Product）**，然后排序。

```python
# 朴素的暴力检索：O(N·D) 复杂度
import numpy as np

# 假设有 10000 条 128 维向量
db = np.random.rand(10000, 128).astype("float32")
query = np.random.rand(128).astype("float32")

# 归一化后，内积 == 余弦相似度
def l2norm(m):
    return m / np.linalg.norm(m, axis=-1, keepdims=True)

scores = l2norm(db) @ l2norm(query)          # 一次矩阵乘法算完
topk = np.argsort(-scores)[:5]               # 取相似度最高的 5 条
print("Top-5 索引:", topk)
```

这个方案在 1 万条时很快，但当数据涨到千万条会：占用几十 GB 内存、每次查询要几百毫秒、无法并发、重启后要重新加载、无法按元数据过滤。**向量数据库（Vector Database）**就是为解决这些问题而生的专用系统。

---

## 2. Qdrant 是什么：一个为向量而生的数据库

**Qdrant**（读作 "quadrant"，象限）是一个开源向量相似度搜索引擎，用 Rust 编写，对外提供 HTTP 与 gRPC 接口，官方 Python 客户端叫 `qdrant-client`。它的核心对象有三个：

- **Collection（集合）**：一组同维度、同距离度量的向量，类似关系库里的"表"。
- **Point（点）**：一条记录，由 `id`（整数或 UUID）+ `vector`（向量）+ 可选 `payload`（元数据字典）组成。
- **Distance（距离度量）**：常见三种——`Cosine`（余弦）、`Euclid`（欧氏）、`Dot`（内积）。

可以用一个类比理解：**Collection 是书架，Point 是书，vector 是书的"语义指纹"，payload 是书名/作者/年份这类可按字段筛选的标签**。

Qdrant 底层用 **HNSW（Hierarchical Navigable Small World）** 图索引做 **近似最近邻（Approximate Nearest Neighbor, ANN）** 检索——牺牲一点点召回率（Recall），换来百倍以上的速度提升。

---

## 3. 最小可用流程：建库 → 写入 → 检索

Qdrant 官方推荐用 Docker 一条命令起一个本地实例：

```bash
docker run -p 6333:6333 qdrant/qdrant
```

6333 是 HTTP/REST 端口（也是 Web UI），6334 是 gRPC 端口。然后用 Python 客户端操作：

```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

# 1) 连接本地实例（内存模式可把 :memory: 传给 location）
client = QdrantClient(url="http://localhost:6333")

# 2) 建集合：4 维、余弦距离
client.recreate_collection(
    collection_name="demo",
    vectors_config=VectorParams(size=4, distance=Distance.COSINE),
)

# 3) 写入若干点
points = [
    PointStruct(id=1, vector=[0.05, 0.61, 0.76, 0.74], payload={"tag": "cat"}),
    PointStruct(id=2, vector=[0.19, 0.81, 0.75, 0.11], payload={"tag": "dog"}),
    PointStruct(id=3, vector=[0.36, 0.55, 0.47, 0.94], payload={"tag": "cat"}),
]
client.upsert(collection_name="demo", points=points)

# 4) 检索：找出与查询向量最相似的 2 条
hits = client.search(
    collection_name="demo",
    query_vector=[0.2, 0.1, 0.9, 0.7],
    limit=2,
    with_payload=True,
)
for h in hits:
    print(f"id={h.id}  score={h.score:.3f}  payload={h.payload}")
```

**关键点**：
- 向量的维度必须和 Collection 声明时一致，否则会报错。
- `score` 的含义由 distance 决定：`Cosine`/`Dot` 越大越相似，`Euclid` 越小越相似。
- `id` 可自定义（整数或 UUID），重复 upsert 会覆盖。

---

## 4. 真正让 Qdrant 好用的两件事：过滤 + 多向量

### 4.1 Payload 过滤（Filtering）

真实业务里"最相似"往往还要加上"只在某个范围内"。比如只看 `year >= 2023` 且 `lang == 'zh'` 的文章。Qdrant 会把过滤条件**下推**到 ANN 搜索内部，避免先取 Top-100 再丢一半。

```python
from qdrant_client.models import Filter, FieldCondition, MatchValue, Range

hits = client.search(
    collection_name="demo",
    query_vector=[0.2, 0.1, 0.9, 0.7],
    query_filter=Filter(
        must=[FieldCondition(key="tag", match=MatchValue(value="cat"))],
    ),
    limit=5,
)
print([h.id for h in hits])
```

`must` 是 AND，`should` 是 OR，`must_not` 是 NOT，可以嵌套组合，形成布尔表达式。

### 4.2 命名向量（Named Vectors）与多模态

同一个 Point 可以存多个向量，比如"标题向量"和"正文向量"，分别对应不同编码器：

```python
client.recreate_collection(
    collection_name="multi",
    vectors_config={
        "title": VectorParams(size=384, distance=Distance.COSINE),
        "body":  VectorParams(size=768, distance=Distance.COSINE),
    },
)

client.upsert(
    collection_name="multi",
    points=[PointStruct(
        id=1,
        vector={"title": [0.1]*384, "body": [0.2]*768},
        payload={"doc": "hello"},
    )],
)

hits = client.search(
    collection_name="multi",
    query_vector=("body", [0.3]*768),   # 指定用哪个向量检索
    limit=3,
)
```

### 4.3 生产模式：`:memory:` vs Docker vs Qdrant Cloud

- `QdrantClient(":memory:")`：纯内存，方便单元测试和脚本演示，进程退出即丢弃。
- `QdrantClient(path="./qdrant_data")`：**本地持久化模式（Local Mode）**，无需服务端，适合笔记本/单机应用。
- `QdrantClient(url=...)`：连远程服务端，支持副本、分片、快照、分布式，是生产选择。
- Qdrant Cloud：官方托管服务，免运维。

---

## 5. 和 AI 应用的关系：RAG 的"记忆库"

大语言模型（LLM）自己不知道你公司文档的内容。**检索增强生成（Retrieval-Augmented Generation, RAG）** 的经典流水线是：

1. 用 embedding 模型（如 OpenAI `text-embedding-3-small`、`bge-m3`）把每段文档编码成向量；
2. 存入 Qdrant，payload 里放原文与元数据；
3. 用户提问时，把问题也编码成向量，从 Qdrant 取 Top-K 相似段落；
4. 把这些段落拼进 Prompt，交给 LLM 生成答案。

Qdrant 在这一层扮演的就是"语义记忆"角色。它的性能、过滤能力、混合检索（稠密 + 稀疏）能力，直接决定 RAG 回答的**上下文质量**。所以，学 Qdrant 不只是学一个工具，更是学**AI 应用的数据平面（Data Plane）**。

## ai.vec.milvus

# 向量数据库 Milvus 入门：从零到工程级

> 一句话直觉：当你需要“从成千上万条数据里，按含义找出最相似的前 K 条”时，传统数据库做不到，Milvus 就是为这件事而生的向量数据库（Vector Database）。

---

## 一、为什么需要 Milvus：从“精确匹配”到“语义相似”

传统关系型数据库（Relational Database）擅长精确查询：`WHERE name = 'Alice'`。但 AI 场景里，我们经常要问的是：

- 给我找出与这张图片最相似的 10 张图；
- 给我找出与这句话语义最接近的 5 段文档；
- 给我推荐与这个用户历史行为最相近的商品。

这些问题的共同点是：**对象被表示成向量（Vector）**，即一串浮点数 `[0.12, -0.98, 0.33, ...]`，而“相似”用**距离（Distance）**衡量，例如余弦相似度（Cosine Similarity）或欧氏距离（Euclidean Distance）。

Milvus 的核心职责：**高效存储海量向量，并做近似最近邻（Approximate Nearest Neighbor, ANN）检索**。

```python
# 直觉演示：向量之间用余弦相似度衡量“含义接近程度”
import numpy as np

def cosine(a, b):
    a, b = np.array(a), np.array(b)
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b)))

v_cat  = [0.9, 0.1, 0.0]   # 假设“猫”的向量
v_dog  = [0.8, 0.2, 0.0]   # 假设“狗”的向量
v_car  = [0.0, 0.1, 0.9]   # 假设“汽车”的向量

print(cosine(v_cat, v_dog))  # ~0.99，语义接近
print(cosine(v_cat, v_car))  # ~0.02，语义很远
```

---

## 二、Milvus 的核心概念：集合、字段、索引、检索

Milvus 用四个关键词就能概括：

| 概念 | 英文 | 说明 |
|---|---|---|
| 集合 | Collection | 类似关系库的“表”，存放同一类向量 |
| 字段 | Field | 每条记录的列，包含向量字段和标量字段 |
| 索引 | Index | 为了加速检索而建立的数据结构（如 IVF、HNSW） |
| 检索 | Search | 输入一个查询向量，返回 top-k 最相似的实体 |

其中**索引**是性能的关键。常用索引类型：

- **FLAT**：暴力精确检索，最准但最慢，适合小数据或验证。
- **IVF_FLAT**：倒排文件（Inverted File），先聚类再检索，速度快。
- **HNSW**：基于图（Hierarchical Navigable Small World），查询快、召回高，内存占用较大。

**度量方式（Metric Type）**必须与向量产生方式匹配：

- `L2`：欧氏距离，越小越相似；
- `IP`：内积（Inner Product），越大越相似；
- `COSINE`：余弦相似度，越大越相似（Milvus 内部按 IP 处理归一化向量）。

```python
# 用 pymilvus 声明一个 Collection 的 schema（结构）
from pymilvus import MilvusClient, DataType

client = MilvusClient("milvus_demo.db")  # 本地文件模式，无需 Docker，便于学习

schema = client.create_schema(auto_id=True, enable_dynamic_field=False)
schema.add_field(field_name="id",        datatype=DataType.INT64, is_primary=True)
schema.add_field(field_name="title",     datatype=DataType.VARCHAR, max_length=200)
schema.add_field(field_name="embedding", datatype=DataType.FLOAT_VECTOR, dim=4)
```

---

## 三、最小可运行流程：建库 → 插入 → 建索引 → 检索

Milvus 的典型生命周期（Lifecycle）是四步：

1. 创建 Collection；
2. 插入（Insert）向量数据；
3. 创建索引（Create Index）并加载（Load）；
4. 执行检索（Search）。

下面这段代码把它一次性跑通。它使用 Milvus 官方轻量模式 `milvus_demo.db`，**无需安装 Docker 或单独启动服务**，非常适合本地学习。

```python
from pymilvus import MilvusClient, DataType

# 1) 连接（本地文件模式，会自动创建 milvus_demo.db）
client = MilvusClient("milvus_demo.db")

# 2) 如果已经存在则删除，保证示例可重复运行
if client.has_collection("docs"):
    client.drop_collection("docs")

# 3) 定义 schema
schema = client.create_schema(auto_id=True, enable_dynamic_field=False)
schema.add_field(field_name="id",        datatype=DataType.INT64, is_primary=True)
schema.add_field(field_name="title",     datatype=DataType.VARCHAR, max_length=200)
schema.add_field(field_name="embedding", datatype=DataType.FLOAT_VECTOR, dim=4)

# 4) 索引参数（HNSW + 余弦相似度）
index_params = client.prepare_index_params()
index_params.add_index(
    field_name="embedding",
    index_type="HNSW",
    metric_type="COSINE",
    params={"M": 16, "efConstruction": 200},
)

# 5) 创建集合（同时应用索引）
client.create_collection(
    collection_name="docs",
    schema=schema,
    index_params=index_params,
)

# 6) 插入数据（这里的向量是假的，真实项目里来自嵌入模型）
data = [
    {"title": "猫的习性",   "embedding": [0.9, 0.1, 0.0, 0.0]},
    {"title": "狗的饲养",   "embedding": [0.8, 0.2, 0.0, 0.0]},
    {"title": "汽车维修",   "embedding": [0.0, 0.1, 0.9, 0.0]},
    {"title": "飞机驾驶",   "embedding": [0.0, 0.0, 0.8, 0.2]},
]
client.insert(collection_name="docs", data=data)

# 7) 检索：找与 [0.85, 0.15, 0, 0] 最相似的 top-2
results = client.search(
    collection_name="docs",
    data=[[0.85, 0.15, 0.0, 0.0]],
    limit=2,
    output_fields=["title"],
)

for hit in results[0]:
    print(hit["entity"]["title"], "->", round(hit["distance"], 4))
```

预期输出（相似度由高到低）：`猫的习性` → `狗的饲养`。

---

## 四、工程化关键点：索引、分区、标量过滤

做到能用之后，工程上还需要关心下面几点。

### 1. 索引与度量的一致性

索引创建时指定的 `metric_type` 必须与检索时一致，否则结果会出错甚至报错。检索时也可以传入 `search_params` 调整召回率：

```python
results = client.search(
    collection_name="docs",
    data=[[0.85, 0.15, 0.0, 0.0]],
    limit=2,
    output_fields=["title"],
    search_params={"metric_type": "COSINE", "params": {"ef": 64}},  # HNSW 的查询参数
)
```

`ef` 越大召回越高但越慢；`M`、`efConstruction` 影响建索引的成本与质量。

### 2. 标量过滤（Scalar Filtering）

真实场景常常是“**先过滤再检索**”，例如“只在 2024 年之后的文档里找相似段落”。Milvus 支持用布尔表达式过滤：

```python
# 假设 schema 里有一个 year 字段，则可以使用 expr 过滤
results = client.search(
    collection_name="docs",
    data=[[0.85, 0.15, 0.0, 0.0]],
    limit=2,
    filter="year >= 2024",        # 表达式必须在插入时该字段已存在
    output_fields=["title", "year"],
)
```

### 3. 分区（Partition）与并发

- **分区键（Partition Key）**：把一个 Collection 按某个标量字段（如 `tenant_id`）切分，减小单次检索扫描范围。
- **分批插入**：大量插入时用 `client.insert` 批量调用，不要一条一条写，否则网络往返开销巨大。

### 4. 数据的持久化与一致性

Milvus 是**最终一致性（Eventual Consistency）**系统。写入后立即可查通常没问题（本地模式更直接），但分布式部署时要了解 `consistency_level` 参数对搜索结果新鲜度的影响。

```python
# 强制等待数据可见（分布式部署时有用）
client.flush(collection_name="docs")
```

---

## 五、与 AI 应用如何衔接：RAG 中的 Milvus

最典型的工程用法是 **检索增强生成（Retrieval-Augmented Generation, RAG）**：

1. 用嵌入模型（Embedding Model，如 sentence-transformers、OpenAI Embeddings）把文本编码成向量；
2. 向量写入 Milvus；
3. 用户提问时，把问题也编码成向量，去 Milvus 检索最相关的文档片段；
4. 把检索到的片段拼进提示词（Prompt）交给大语言模型（LLM）。

```python
# 伪代码：RAG 中的 Milvus 角色
# from sentence_transformers import SentenceTransformer
# model = SentenceTransformer("all-MiniLM-L6-v2")
# query_vec = model.encode([user_question]).tolist()
#
# hits = client.search(
#     collection_name="knowledge_base",
#     data=query_vec,
#     limit=5,
#     output_fields=["text"],
# )
# context = "\n".join(h["entity"]["text"] for h in hits[0])
# prompt = f"请根据以下资料回答问题：\n{context}\n\n问题：{user_question}"
```

到这里，你就能把 Milvus 看成“**AI 应用的外部记忆**”：模型负责理解，Milvus 负责记忆和检索。

---

## 动手练习

**任务**：搭建一个个人知识片段检索器。

1. 本地 `pip install pymilvus`，按上面第 3 节的代码，创建名为 `my_notes` 的 Collection，维度设为 4（为了简化，用随机向量代替真实嵌入）。
2. 插入至少 8 条笔记，每条包含 `title` 和 `embedding`，其中至少 4 条是关于“编程”，4 条是关于“食物”。
3. 用一条“趋向编程类”的查询向量检索 top-3，观察返回结果是否都是编程类。
4. 进阶：给 schema 加一个 `category`（VARCHAR）字段，用 `filter="category == 'programming'"` 把检索限制在编程类笔记里，比较有无过滤时的差异。

**提交物**：一段完整可运行的 Python 脚本，以及一张截图或文本输出，展示检索结果与相似度分数。


---

## 本课题目

### single_choice · None



- [A] 直接使用 IndexFlatL2，因为它是精确检索，结果一定最好
- [B] 使用 IVF 类索引并调整 nlist 和 nprobe，在召回率与速度之间取得平衡
- [C] 使用 IndexIDMap 包装任意索引即可自动加速
- [D] 使用 IndexFlatIP 并把向量归一化后，检索速度会比 IndexFlatL2 快很多

**参考答案**：1

**解析**：大数据量下精确检索（Flat）内存与耗时都不可接受；IVF 通过倒排文件聚类先粗筛再精算，nlist 控制聚类数、nprobe 控制查询时访问的聚类数，是召回率与速度的权衡手段。IndexIDMap 只是建立外部 ID 到内部 ID 的映射，不改变搜索复杂度；IndexFlatIP 与 IndexFlatL2 都是暴力检索，归一化只影响度量含义，不会显著提速。

### single_choice · None



- [A] 查询时使用的 nprobe 太小，目标向量所在聚类没有被访问
- [B] 添加向量之前忘记对索引调用 train（对需要训练的索引类型）
- [C] 查询向量与库向量使用了不同的归一化方式
- [D] 把向量添加到了 IndexIDMap 中，因此原始向量被覆盖

**参考答案**：3

**解析**：IndexIDMap 只是把用户提供的 ID 映射到内部顺序 ID，不会覆盖或丢失向量。nprobe 过小、忘记 train（IVF/PQ 等需要训练）、归一化不一致都会造成召回缺失。

### single_choice · None



- [A] 它基于图结构进行近似最近邻搜索，通常查询速度快、召回率高，但内存占用较大
- [B] 它是精确检索，不会有任何误差
- [C] 它必须先对向量做乘积量化压缩后才能使用
- [D] 它只能用于 L2 距离，不能用于内积

**参考答案**：0

**解析**：HNSW 是分层可导航小世界图，属于近似最近邻方法，查询延迟低、召回高，但需要存储图边，内存较高。它不是精确检索；不强制 PQ 压缩；可以通过度量配置支持不同距离类型。

### single_choice · None



- [A] IndexFlatL2 本身支持自定义 ID
- [B] 在索引外层再包一层列表记录顺序
- [C] IndexIDMap 包装底层索引，用 add_with_ids 添加向量
- [D] 把自定义 ID 编码进向量最后一个维度

**参考答案**：2

**解析**：IndexIDMap（及 IndexIDMap2）用于把用户提供的 int64 ID 映射到内部顺序 ID，配合 add_with_ids 使用。普通 Flat 索引的 add 不接收外部 ID；外层列表无法在检索时直接返回 ID；把 ID 塞进向量维度会污染语义并改变度量。

### single_choice · None



- [A] 必须与最终添加的向量完全相同，且顺序一致
- [B] 应从待索引数据分布中采样，数量通常远多于 nlist
- [C] 只需要一条样本即可完成训练
- [D] 训练样本必须归一化，否则训练会失败

**参考答案**：1

**解析**：训练的目标是学习聚类中心或量化码本，因此训练样本应具有代表性，数量通常建议远大于 nlist（例如几十倍）。不必与最终向量完全一致，也不要求顺序对应；一条样本远不足以训练；归一化取决于度量设计而非训练硬性要求。

### single_choice · None



- [A] FAISS 自动把 512 维补零到 768 维
- [B] FAISS 自动截断到 512 维继续检索
- [C] 抛出维度不匹配的异常
- [D] 检索正常返回，只是结果不准

**参考答案**：2

**解析**：FAISS 索引在创建时固定维度 d，查询或添加时传入不同维度的向量会触发异常/断言失败，不会自动补零或截断。

### single_choice · None



- [A] 近似检索一定会返回错误的最近邻，因此生产环境不能用
- [B] 精确检索结果可保证与暴力搜索一致，但数据量大时速度与内存代价高
- [C] 近似检索只适合小规模数据，大规模数据必须用精确检索
- [D] 两者返回的结果完全相同，只是速度不同

**参考答案**：1

**解析**：精确检索（如 Flat）穷举比较，结果与暴力搜索一致，但规模大时开销高；近似检索通过聚类、量化、图结构等减少计算量，可能漏掉真实最近邻但可接受。近似检索反而在大规模场景更常用。两者结果不保证相同。

### single_choice · None



- [A] IVFFlat 只用倒排聚类，IVFPQ 在倒排基础上再用乘积量化压缩向量存储
- [B] IVFFlat 是精确检索，IVFPQ 不是近似检索
- [C] IVFFlat 不需要训练，IVFPQ 也不需要训练
- [D] IVFPQ 的检索结果总是比 IVFFlat 更准确

**参考答案**：0

**解析**：IVFFlat 在候选列表内保存完整向量并精确计算距离；IVFPQ 进一步用 PQ 压缩向量，显著降低内存但损失精度，两者都是近似检索且都需要训练。IVFPQ 因压缩通常精度低于 IVFFlat。

### single_choice · None



- [A] D 是距离/得分矩阵，I 是对应向量的 ID 矩阵，形状均为 (查询数, k)
- [B] D 是向量维度，I 是索引数量
- [C] D 是查询向量的原始数据，I 是结果 ID
- [D] D 和 I 都是长度为 k 的一维数组，与查询数无关

**参考答案**：0

**解析**：search(x, k) 返回 (D, I)，D 为每个查询的 k 个最近邻的距离/相似度，I 为对应的向量 ID，形状都是 (n_queries, k)。它们不是维度或原始向量数据。

### single_choice · None



- [A] 增加倒排列表数量以提升召回
- [B] 学习一个旋转矩阵，使各子空间方差更均衡，从而降低量化误差
- [C] 替代 nprobe，在查询时决定访问哪些聚类
- [D] 把内积转换为欧氏距离

**参考答案**：1

**解析**：OPQ 通过优化一个正交旋转矩阵，让向量各维度能量分布更均匀，减少 PQ 各子空间独立量化带来的误差。它与倒排列表数量、nprobe 查询策略、距离类型转换无关。

### single_choice · None



- [A] 训练时每个聚类中心样本过少，聚类质量差，检索召回下降
- [B] 索引会自动降级为 Flat 索引，结果精确
- [C] nprobe 会自动被设为 nlist，速度不受影响
- [D] 内存占用会显著低于数据量很小的情况

**参考答案**：0

**解析**：nlist 过大而训练样本相对不足时，聚类中心难以被充分学习，每个列表内样本极少，查询时即便访问少数列表也覆盖不到目标，召回下降。FAISS 不会自动降级为 Flat；nprobe 不会自动等于 nlist；内存不一定更低。

### single_choice · None



- [A] 可以保证 100% 召回率
- [B] 通过先聚类筛选候选集，显著减少每次查询需要比较的向量数量
- [C] 可以自动把向量维度降低到更低维度
- [D] 可以完全避免内存占用

**参考答案**：1

**解析**：IVF 的核心思想是把向量分到 nlist 个聚类中，查询时只在 nprobe 个最可能的聚类内做距离计算，从而减少比较次数。它不保证 100% 召回；不会自动降维（那是 PQ 等压缩手段）；仍需要内存保存索引数据。

### single_choice · None



- [A] 向量维度与索引声明的维度不一致
- [B] 使用的是需要训练的索引类型（如 IVF、PQ），但没有先调用 train
- [C] add 的向量数量太少，FAISS 要求至少 1000 条
- [D] 没有先调用 normalize_L2 对向量做归一化

**参考答案**：2

**解析**：需要训练的索引类型（含 IVF、PQ 等）必须先提供训练样本调用 train，再 add。add 向量数量没有统一的 1000 条下限要求；归一化不是所有索引的必需步骤；维度不一致会报另一种错误。

### single_choice · None



- [A] FAISS 返回的 ID 需要除以向量维度才是真实 ID
- [B] 没有使用 IndexIDMap 或未调用 add_with_ids，导致索引只保存内部顺序 ID
- [C] 查询向量的维度写错了
- [D] 需要把 nprobe 设置为 0 才能返回真实 ID

**参考答案**：1

**解析**：普通索引用 add 添加向量时内部以 0 起始的顺序编号作为 ID。要返回业务 ID，需要用 IndexIDMap 包装并使用 add_with_ids 传入 int64 ID。ID 与维度无关，nprobe 不影响 ID 含义。

### single_choice · None



- [A] IndexFlatL2 是精确检索，IndexIVFFlat 是近似检索，后者可能漏掉真正的最近邻
- [B] IndexIVFFlat 也是精确检索，只是速度更快
- [C] IndexFlatL2 需要训练，IndexIVFFlat 不需要训练
- [D] 两者都基于乘积量化，只是存储方式不同

**参考答案**：0

**解析**：Flat 索引对所有向量做穷举比较，结果精确；IVFFlat 先用粗聚类筛选候选再在候选集内精算，是近似检索，nprobe 不够时可能漏掉真实最近邻。训练需求与两者相反：Flat 不需要训练，IVFFlat 需要。

### single_choice · None



- [A] 倒排列表（聚类）的数量
- [B] 查询时访问的聚类数量
- [C] 把原始向量切分成的子向量段数，每段分别做量化
- [D] 索引中保存的向量总条数

**参考答案**：2

**解析**：在 PQ（乘积量化）中，M 是把 d 维向量切成 M 段子向量、每段独立量化的段数；倒排列表数量是 nlist，查询访问的聚类数是 nprobe。

### single_choice · None



- [A] 减小 nlist
- [B] 增大 nprobe
- [C] 减小 M
- [D] 减小向量维度

**参考答案**：1

**解析**：nprobe 控制查询时访问的倒排列表数量，增大可覆盖更多候选、提高召回，但耗时增加。减小 nlist 使每个列表更大，单列表精算变慢，对召回的影响不是直接可控的；M 是 PQ 子段数，影响压缩率与精度但并非查询期参数；减小维度会改变语义。

### single_choice · None



- [A] IndexFlatL2
- [B] IndexFlatIP
- [C] IndexIVFPQ
- [D] IndexHNSWFlat 只能使用 L2

**参考答案**：1

**解析**：IndexFlatIP 使用内积作为度量，得分越大越相似。IndexFlatL2 用欧氏距离，越小越相似。IndexIVFPQ 是量化索引，其度量取决于训练与配置，但名称本身不代表内积。HNSW 也可配合不同度量，说“只能 L2”不正确。

### single_choice · None



- [A] FAISS 索引文件损坏
- [B] 查询向量与库向量没有经过一致的预处理（如归一化或同一模型编码）
- [C] nprobe 设置得太小
- [D] 没有使用 GPU 版本的 FAISS

**参考答案**：1

**解析**：向量检索的有效性依赖查询向量与库向量处于同一表示空间与同一尺度。若一侧归一化或编码方式不同，距离/内积就失去可比性，导致结果无关。索引损坏通常直接报错；nprobe 过小只会漏召回而非全错；CPU/GPU 版本不影响语义正确性。

### single_choice · None



- [A] 用 write_index 保存索引后，用 read_index 加载即可继续 add 和 search
- [B] 索引必须序列化为 JSON 才能保存
- [C] 保存索引时必须同时保存原始向量文件，否则无法加载
- [D] 只有 Flat 索引可以保存，IVF 索引无法持久化

**参考答案**：0

**解析**：FAISS 提供 write_index / read_index 对索引做二进制序列化与反序列化，加载后可继续使用。索引不是 JSON 格式；FAISS 索引自身保存了向量数据，不需要额外原始文件；各类索引普遍支持保存。

### single_choice · None



- [A] 调用 index.to_gpu()，对任意 CPU 索引都可用
- [B] 使用 index_cpu_to_gpu 或 index_cpu_to_all_gpus 等辅助函数进行转换
- [C] 直接把索引文件后缀改为 .gpu 即可
- [D] GPU 版本不支持从 CPU 索引转换，必须从头在 GPU 上建立

**参考答案**：1

**解析**：FAISS 提供 index_cpu_to_gpu / index_cpu_to_all_gpus 等辅助函数，将 CPU 索引复制到 GPU 上并指定资源。并非所有索引都支持 to_gpu()；改后缀没有意义；GPU 版本可以直接从 CPU 索引转换，不必从头重建。

### single_choice · None



- [A] 向量和可选的负载（payload）
- [B] 只有向量
- [C] 只有负载
- [D] 向量、负载以及一个自动生成的关系表

**参考答案**：0

**解析**：Qdrant 中的 point 由向量和可选的 payload 组成，payload 用于存储与向量关联的元数据。它不需要关系表结构，也不是只能存向量或只能存负载。

### single_choice · None



- [A] 同一集合中不同向量可以使用不同的距离度量，互不影响
- [B] 距离度量在创建集合时指定，同一集合内所有向量共用该度量
- [C] 距离度量只能在查询时临时指定，创建集合时无法设置
- [D] Qdrant 不支持余弦距离

**参考答案**：1

**解析**：Qdrant 在创建集合时通过向量配置指定距离度量（如 Cosine、Euclidean、Dot），该集合内的所有向量共用同一度量，不能在查询时随意更换为不同类型，也不支持同一集合内混用多种度量。

### single_choice · None



- [A] 直接把新向量写入原集合，Qdrant 会自动适配
- [B] 新建一个维度匹配的集合并重新写入全部向量
- [C] 修改已有集合的维度配置即可
- [D] 降低查询时的 limit 以规避维度问题

**参考答案**：1

**解析**：集合维度在创建时固定，不能就地修改为不同维度。更换嵌入模型导致维度变化时，应新建匹配维度的集合并重新写入数据，否则写入会因维度不匹配而失败。

### multi_choice · None



- [A] 它是一款向量相似度搜索引擎/向量数据库
- [B] 它支持为 payload 字段建立索引以加速过滤
- [C] 它支持在搜索时结合向量相似度与 payload 过滤条件
- [D] 它要求所有向量必须是同一种固定的距离度量才能混用

**参考答案**：[0, 1, 2]

**解析**：Qdrant 是向量数据库，支持 payload 索引和带过滤的向量检索。选项 D 描述错误：同一集合使用统一距离度量，但不能在同一集合内任意混用不同度量。

### multi_choice · None



- [A] 为经常用于过滤的 payload 字段建立索引
- [B] 合理设计分片与副本
- [C] 把所有过滤都放到客户端做，减少服务端负担
- [D] 为集合选择合适的距离度量以匹配数据特性

**参考答案**：[0, 1, 3]

**解析**：建立 payload 索引、合理分片与副本、选择合适的距离度量都有助于性能与效果。把过滤全部放到客户端会拉取大量无用数据，通常更慢，不是推荐做法。

### multi_choice · None



- [A] payload 用于存储与向量关联的元数据
- [B] payload 可以参与过滤条件
- [C] payload 是可选的
- [D] payload 会被直接用于计算向量相似度

**参考答案**：[0, 1, 2]

**解析**：payload 存储元数据、可参与过滤且是可选的。相似度计算基于向量本身而非 payload，因此选项 D 错误。

### multi_choice · None



- [A] 所选嵌入模型的质量
- [B] 所选距离度量是否与数据特性匹配
- [C] 向量维度是否与集合配置一致
- [D] Qdrant 服务的安装目录路径

**参考答案**：[0, 1, 2]

**解析**：嵌入模型质量、距离度量匹配度、维度一致性都会影响检索效果与可用性。服务的安装目录路径与检索相关性无关。

### fill_blank · None



**参考答案**：["payload", "Payload", "payloads", "Payloads"]

**解析**：Qdrant 将向量关联的元数据称为 payload，它可选、可被过滤，并能在检索结果中一并返回。

### fill_blank · None



**参考答案**：["Cosine", "cosine", "Euclidean", "euclidean", "Dot", "dot"]

**解析**：创建集合时需要指定距离度量，常见取值有 Cosine、Euclidean、Dot，它们决定相似度如何计算。

### code_reading · None



**参考答案**：先创建一个名为 docs、向量维度为 768、使用余弦距离的集合；再插入一个 id 为 1、带 payload {"lang": "zh"} 的向量；最后用查询向量 q 在该集合中检索，limit=5 表示最多返回 5 个最近邻，filter 限制结果只包含 payload 中 lang 为 zh 的点，即服务端先按 payload 过滤再返回相似度最高的若干结果。

**解析**：该伪代码展示了集合创建、向量写入与带过滤的向量检索三个步骤。filter 让检索只在满足 payload 条件的点中进行，从而结合语义相似度与元数据约束。

### scenario · None



**解析**：应把文档的权限标识作为 payload 字段存储，并在检索请求中携带 filter 让 Qdrant 在服务端按权限过滤。相比先全量检索再在应用层过滤，服务端过滤能避免拉取大量无权限结果、降低延迟与泄露风险，并可结合 payload 索引提升性能。

### scenario · None



**解析**：集合维度创建时固定，直接写入 1024 维向量会因维度不匹配而报错。平滑切换的思路是新建一个 1024 维的集合，用新模型重新生成并写入全部向量，验证无误后再切换流量、下线旧集合，从而避免停机与数据不一致。

### single_choice · None



- [A] 把所有数据取回客户端后再在本地过滤
- [B] 在检索请求中附带 filter 条件，由 Qdrant 在服务端过滤
- [C] 必须为每个字段单独建立一个集合
- [D] 过滤功能在 Qdrant 中不存在

**参考答案**：1

**解析**：Qdrant 支持在搜索请求中携带 filter，服务端会结合向量相似度和 payload 条件进行过滤，避免把全部结果拉回客户端再处理，也能通过为字段建立索引来提升效率。

### single_choice · None



- [A] payload 索引是强制创建的，无法省略
- [B] 为常用过滤字段建立 payload 索引可以提升带条件检索的性能
- [C] payload 索引等同于向量索引，二者没有区别
- [D] 没有索引时任何过滤操作都会报错

**参考答案**：1

**解析**：payload 索引是可选的，为经常用于过滤的字段建立索引能显著提升带条件查询的速度；它不是强制的，没有索引时过滤仍可工作，只是可能更慢。payload 索引与向量索引是不同概念。

### single_choice · None



- [A] Qdrant 会自动截断或补齐向量到目标维度
- [B] Qdrant 会自动把该集合改造成适配新维度
- [C] 操作会失败并报维度不匹配的错误
- [D] Qdrant 会忽略维度问题并随机返回结果

**参考答案**：2

**解析**：集合在创建时确定了向量维度，写入或查询的向量必须与该维度一致，否则请求会报错。Qdrant 不会自动截断、补齐或修改集合维度。

### single_choice · None



- [A] 余弦距离关注向量方向，欧氏距离关注向量间的空间直线距离
- [B] 余弦距离和欧氏距离在任何情况下结果完全等价
- [C] 欧氏距离只适用于单位向量
- [D] 余弦距离会忽略向量的夹角信息

**参考答案**：0

**解析**：余弦距离衡量向量方向上的相似性，对整体缩放不敏感；欧氏距离衡量向量端点的直线距离，受向量长度影响。二者不等价，欧氏距离并非只适用于单位向量，余弦距离恰恰关注夹角。

### single_choice · None



- [A] limit
- [B] dimension
- [C] shard_number
- [D] replica

**参考答案**：0

**解析**：搜索请求中的 limit 决定返回的最近邻结果个数。dimension 是向量维度，shard_number 是分片数，replica 与副本相关，它们都不控制返回结果数量。

### single_choice · None



- [A] 必须先插入数据，Qdrant 会自动推断并创建集合
- [B] 创建集合时需指定向量维度与距离度量等参数
- [C] 集合创建后无法再添加任何字段的索引
- [D] 一个 Qdrant 实例只能存在一个集合

**参考答案**：1

**解析**：Qdrant 的集合通常需要显式创建，并在创建时指定向量维度、距离度量等配置。集合创建后仍可添加 payload 索引，一个实例也可包含多个集合，且不会因插入数据自动推断建集合。

### single_choice · None



- [A] 副本（replica）
- [B] payload 索引
- [C] 距离度量
- [D] 向量维度

**参考答案**：0

**解析**：副本机制通过在多个节点保存同一分片的拷贝来提升可用性和读吞吐。payload 索引用于过滤加速，距离度和向量维度是向量配置相关概念，均不提供冗余。

### single_choice · None



- [A] 两者完全等价，都会返回最近邻列表
- [B] 按 id 获取是精确查找指定点，向量搜索返回与查询向量最相似的点
- [C] 按 id 获取需要提供查询向量
- [D] 向量搜索不能返回 payload

**参考答案**：1

**解析**：按 id 获取是根据已知主键精确取回一个点，不需要查询向量；向量搜索是根据相似度返回最近邻。向量搜索默认可以返回 payload，二者并不等价。

### single_choice · None



- [A] 一个分区可以包含多个集合，集合是分区的逻辑子集
- [B] 一个集合可以包含多个分区，分区是集合内的数据子集划分
- [C] 集合和分区是同一层级的平行概念，可互相包含
- [D] 分区必须跨多个集合存在，用于全局数据切分

**参考答案**：1

**解析**：在 Milvus 的数据模型中，Collection 是顶层的数据组织单位（类似关系库中的表），Partition 是 Collection 内部的可选子划分，用于缩小搜索范围、提升查询效率。一个 Collection 可包含多个 Partition，而 Partition 不能跨 Collection 存在。

### single_choice · None



- [A] 向量字段只能存 128 维以内的向量，超出需拆分成多字段
- [B] Schema 在集合创建后可以随意增加任意类型的向量字段而无需重建索引
- [C] Schema 定义了集合的字段结构，其中必须包含一个主键字段和一个（或多个）向量字段
- [D] 主键字段的值允许为空，Milvus 会自动生成 UUID 填充

**参考答案**：2

**解析**：创建集合时需要定义 Schema，Schema 描述字段名、类型及约束；其中至少要有主键字段和向量字段。向量维度可以在 Schema 中指定（高维如 768 维很常见），主键通常不允许为空且需唯一。创建后随意修改向量字段结构并非无代价操作。

### single_choice · None



- [A] 删除集合后，其中的分区和索引仍然保留，可被其他集合复用
- [B] 删除集合会移除该集合及其分区和索引等关联结构
- [C] 只能删除单个实体，无法删除整个集合
- [D] 删除实体后向量占用的空间会被立即、同步地完全回收

**参考答案**：1

**解析**：删除集合会移除集合及其关联的分区、索引等结构。删除实体通常不一定立即同步回收全部存储空间（可能涉及后续的压缩整理）。因此选 B。

### multi_choice · None



- [A] 为向量字段选择合适的近似索引（如 IVF/HNSW 类）以平衡速度与召回
- [B] 把图片的类别、上传时间等标量信息作为字段存储，以便混合过滤检索
- [C] 将向量维度在集合创建时确定，并保证插入向量维度一致
- [D] 为追求绝对精确，强制关闭所有索引并全量暴力扫描，忽略性能开销
- [E] 把每张图片的原始二进制直接存进向量字段

**参考答案**：[0, 1, 2]

**解析**：合理做法包括：选择合适的 ANN 索引、存储标量元数据以支持混合过滤、在创建集合时确定向量维度并保持插入一致。暴力全量扫描虽精确但通常不适用于大规规则模生产；向量字段应存数值向量而非原始图片二进制。

### multi_choice · None



- [A] 不同索引类型在构建时间、内存占用和查询速度上各有取舍
- [B] 搜索时的参数（如候选范围大小）会影响召回率与延迟
- [C] 所有索引类型都能在不损失召回的前提下达到与暴力搜索完全相同的精度
- [D] 选择度量方式（L2/IP/COSINE）会影响相似度结果的排序含义
- [E] 索引只影响写入性能，与查询无关

**参考答案**：[0, 1, 3]

**解析**：不同索引有不同权衡；搜索参数影响召回率和延迟；度量方式决定相似度含义与排序。并非所有索引都能零损失达到暴力搜索精度，索引也不只是影响写入。因此正确项为 0、1、3。

### multi_choice · None



- [A] 按业务维度（如租户、时间）划分分区有助于缩小检索范围
- [B] 分区是集合内部的可选划分，分区内的数据仍属于该集合
- [C] 跨集合检索可以在一次搜索请求中自动完成，无需应用层聚合
- [D] 合理使用分区可以在部分场景下减少扫描的数据量
- [E] 一个分区可以同时属于多个集合

**参考答案**：[0, 1, 3]

**解析**：分区用于集合内划分，可按业务维度缩小检索范围、减少扫描量。跨集合检索通常需要应用层或多次请求处理，并非单次自动聚合；分区不能跨集合存在。正确项为 0、1、3。

### fill_blank · None



**参考答案**：["hybrid", "Hybrid", "hybrid search", "Hybrid Search"]

**解析**：在向量检索时结合标量字段过滤的表达，常被称为混合查询（hybrid search / hybrid query），即在向量相似度检索的基础上附加标量过滤表达式。

### fill_blank · None



**参考答案**：["COSINE", "cosine", "余弦相似度", "Cosine", "cosine similarity"]

**解析**：Milvus 常见度量方式包括 L2、IP 和 COSINE（余弦相似度）。题目已给出前两种，空缺处应填余弦相似度对应的名称。

### fill_blank · None



**参考答案**：["load", "Load", "加载", "load collection", "LoadCollection"]

**解析**：集合建好索引后需执行 load（加载）操作，将数据加载进查询节点内存，之后才能对外提供搜索/查询服务。

### code_reading · None



**参考答案**：创建索引的主要作用是为向量字段建立高效检索结构（通常是近似最近邻索引），从而在搜索时快速定位候选近邻，兼顾速度与内存。若省略索引直接搜索，可能因缺少检索结构导致搜索效率极低，或在未加载/未建索引时无法正常搜索，需要退化为低效的扫描或直接报错。

**解析**：索引是搜索性能的核心。Milvus 中向量字段通常先建索引再加载搜索；没有索引会导致搜索效率低下甚至不可用。该题考察对「索引—搜索」流程的理解，而不是记忆具体 API 名。

### code_reading · None



**参考答案**：该次插入最可能会失败（报错），因为向量字段在 Schema 中已声明为 768 维，插入的向量维度必须与声明维度一致，512 维与 768 维不匹配会被拒绝。

**解析**：向量字段的维度在创建集合时确定，插入数据的向量维度必须与之严格一致，否则插入会报错。考察维度一致性这一边界规则。

### scenario · None



**解析**：该场景需要：用集合存放商品向量并定义包含标量字段（类目、上架时间）的 Schema；查询时使用标量过滤表达式结合向量检索（混合查询）；为向量字段选择合适的近似索引以平衡延迟与召回率（召回率是重要取舍）；可按类目或时间做分区以缩小检索范围。关键词覆盖集合、标量字段、混合查询/过滤、索引、召回率。

### single_choice · None



- [A] 建立索引后，搜索时返回的结果一定是精确的最近邻，不会有近似误差
- [B] 近似最近邻索引（如 IVF、HNSW 类）用召回率换取查询速度，搜索参数会影响精度与性能的权衡
- [C] 索引一旦建立就与查询参数无关，nprobe、ef 等参数只影响写入速度
- [D] 向量集合必须建立索引后才能插入数据，否则插入会失败

**参考答案**：1

**解析**：Milvus 支持的多数向量索引属于近似最近邻（ANN）索引，会以一定召回率损失换取速度与内存优势。查询时的搜索参数（如探测的桶数、候选列表大小）会直接影响召回率与延迟的权衡。数据插入并不强制要求已有索引。

### single_choice · None



- [A] 欧氏距离（L2）
- [B] 内积（IP）
- [C] 余弦相似度（COSINE）
- [D] 编辑距离（Levenshtein）

**参考答案**：3

**解析**：Milvus 常见向量度量包括 L2 欧氏距离、IP 内积和 COSINE 余弦相似度。编辑距离用于字符串序列比较，不是向量相似度度量方式，因此不属于常见度量。

### single_choice · None



- [A] Milvus 只能做纯向量检索，无法结合标量字段条件过滤
- [B] 可以通过表达式（如对数值、字符串字段的比较）在向量检索时附加标量过滤条件
- [C] 标量过滤只能在插入数据时进行，查询时不能使用
- [D] 标量过滤必须对每个标量字段单独建向量索引才能生效

**参考答案**：1

**解析**：Milvus 支持混合查询，即在向量相似度检索时附带标量字段的过滤表达式（如 age > 30、category == "xxx"），从而缩小候选集。标量字段不需要建向量索引。

### single_choice · None



- [A] 数据一旦插入，立刻对所有查询完全可见，无需任何等待
- [B] 插入的数据需要经过持久化与加载等过程，查询可见性受一致性级别等配置影响
- [C] Milvus 不支持任何一致性级别配置，行为固定
- [D] 只有删除操作存在可见性延迟，插入操作没有

**参考答案**：1

**解析**：Milvus 中插入的数据需被写入并最终对查询可见，这受一致性级别（如 Strong、Bounded、Eventually 等）影响。不同级别在一致性与延迟之间存在权衡。

### single_choice · None



- [A] 只有在第一次搜索时确定即可
- [B] 在创建集合定义 Schema 时就需要确定，且同一向量字段内所有向量维度一致
- [C] 可以在每次插入数据时动态改变，Milvus 自动对齐维度
- [D] 维度由索引类型自动推断，无需用户指定

**参考答案**：1

**解析**：向量字段的维度需在定义 Schema（创建集合）时指定，且同一字段中所有向量维度必须一致，否则插入会报错。维度不能每次插入时动态改变。

### single_choice · None



- [A] Load 是把数据从磁盘直接拷贝到用户本地文件系统
- [B] Load 使集合（或分区）的数据被加载进内存以便提供搜索/查询服务
- [C] Load 是在创建集合前必须执行的步骤，用于初始化元数据
- [D] Load 只对索引有效，对原始向量数据无效

**参考答案**：1

**解析**：在 Milvus 中，集合创建并建索引后，需要执行加载操作，将数据加载进内存（查询节点），之后才能对外提供搜索和查询服务。这不是把数据拷到用户本地磁盘。

### single_choice · None



- [A] 向量维度设置为 768
- [B] 使用近似索引但搜索参数设置得过于激进（如探测范围过小）
- [C] 集合中数据量较小
- [D] 主键使用整数类型

**参考答案**：1

**解析**：近似最近邻索引在搜索时若参数设置过小（例如探测的候选范围过窄），会遗漏部分真实近邻，导致召回率下降。维度、数据量小、主键类型通常不是召回率偏低的直接原因。

### single_choice · None



- [A] 主键只能使用字符串类型
- [B] 主键用于唯一标识集合中的实体，常见可用整数或字符串类型
- [C] 主键可以重复，Milvus 会自动去重
- [D] 主键不能与向量字段同时存在于一个 Schema 中

**参考答案**：1

**解析**：主键用于唯一标识实体，Milvus 支持整数或字符串类型作为主键，不允许重复。它与向量字段可共存于同一 Schema。
