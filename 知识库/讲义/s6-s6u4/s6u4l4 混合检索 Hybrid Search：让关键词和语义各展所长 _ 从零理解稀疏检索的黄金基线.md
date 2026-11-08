# s6u4l4 混合检索 Hybrid Search：让关键词和语义各展所长 / 从零理解稀疏检索的黄金基线

> 来源 `content/lessons/s6u4l4.json`

## ai.vec.hybrid_search

# 混合检索 Hybrid Search：让关键词和语义各展所长

> **一句话直觉**：只用关键词搜（如 BM25）会漏掉“意思相近但用词不同”的结果，只用向量搜（语义检索）又容易对精确术语、数字、专有名词不敏感；**混合检索就是把两路结果融合起来，取长补短**。

---

## 0. 为什么需要混合检索？

假设你有一堆商品描述。用户查询是：**“iPhone 15 电池续航”**。

- **关键词检索**（Keyword Search / Sparse Retrieval）：按词匹配。文档里出现了 `iPhone`、`15`、`电池`、`续航` 就得分高。优点：精确、可解释、对专有名词和数字强。缺点：“苹果手机能用多久”这种同义改写就搜不到。
- **向量检索**（Vector Search / Dense Retrieval）：把查询和文档都编码成向量，比较语义相似度。优点：能理解同义、近义改写。缺点：对 `iPhone 15` 和 `iPhone 14` 这种细节差异不够敏感，也常把无关但语义泛化的文档拉进来。

工业界（Elasticsearch、Vespa、Weaviate、Pinecone 等）的共识是：**两路召回 + 融合排序**，效果通常显著优于任何单一路径。

本节课我们从零开始，用纯 Python + NumPy 实现一个最小可用的混合检索系统。

---

## 1. 第一块积木：稀疏检索（BM25 简化版）

**稀疏检索（Sparse Retrieval）**：把文档表示成“词 → 权重”的稀疏向量，只对出现过的词给非零值。最经典的算法是 **BM25（Best Matching 25）**。

BM25 的核心思想：
1. **词频饱和**：一个词出现 10 次并不比出现 5 次重要 2 倍。
2. **逆文档频率（IDF, Inverse Document Frequency）**：越罕见的词越有区分度。
3. **文档长度归一化**：长文档天然容易命中更多词，需要抑制。

公式（单查询词 q 对文档 d 的贡献）：

```
score(q, d) = IDF(q) * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * |d| / avgdl))
```

下面实现一个可直接跑的版本：

```python
import math
from collections import Counter


def tokenize(text: str) -> list[str]:
    """最简单的分词：按空格切分并转小写。生产环境请换 jieba / BPE 等。"""
    return text.lower().split()


class BM25:
    def __init__(self, corpus: list[str], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.docs = [tokenize(d) for d in corpus]
        self.doc_len = [len(d) for d in self.docs]
        self.avgdl = sum(self.doc_len) / max(len(self.docs), 1)

        # 统计 DF（文档频率）
        df = Counter()
        for d in self.docs:
            for w in set(d):
                df[w] += 1
        N = len(self.docs)
        # IDF：加 1 平滑，避免负值
        self.idf = {w: math.log(1 + (N - c + 0.5) / (c + 0.5)) for w, c in df.items()}

        # 预计算每篇文档的词频
        self.tf = [Counter(d) for d in self.docs]

    def score(self, query: str, doc_id: int) -> float:
        s = 0.0
        dl = self.doc_len[doc_id]
        for w in tokenize(query):
            if w not in self.idf or w not in self.tf[doc_id]:
                continue
            tf = self.tf[doc_id][w]
            idf = self.idf[w]
            s += idf * (tf * (self.k1 + 1)) / (tf + self.k1 * (1 - self.b + self.b * dl / self.avgdl))
        return s

    def search(self, query: str, top_k: int = 5) -> list[tuple[int, float]]:
        scores = [(i, self.score(query, i)) for i in range(len(self.docs))]
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]
```

---

## 2. 第二块积木：向量检索（余弦相似度）

**向量检索（Dense Retrieval）**：用嵌入模型（Embedding Model）把文本编码为稠密向量，再算相似度。

常见相似度：
- **余弦相似度（Cosine Similarity）**：只看方向，不看长度。文本检索首选。
- **点积（Dot Product）**：向量已归一化时等价于余弦。
- **欧氏距离（L2）**：图像、聚类常用。

```python
import numpy as np


def cosine_sim_matrix(query_vec: np.ndarray, doc_vecs: np.ndarray) -> np.ndarray:
    """query_vec: (D,), doc_vecs: (N, D) -> (N,)"""
    q = query_vec / (np.linalg.norm(query_vec) + 1e-12)
    d = doc_vecs / (np.linalg.norm(doc_vecs, axis=1, keepdims=True) + 1e-12)
    return d @ q  # 归一化后点积 == 余弦
```

**教学用假嵌入器**（无需下载模型，可离线跑）：用哈希把每个词映射到一个固定维度，再按词平均。真实项目里把 `FakeEmbedder` 换成 `sentence-transformers` 或 OpenAI/Cohere 的 embedding API 即可，接口不变：

```python
class FakeEmbedder:
    """极简“嵌入器”：词哈希到固定维度后取平均。仅用于教学演示。"""
    def __init__(self, dim: int = 64):
        self.dim = dim

    def _embed_one(self, text: str) -> np.ndarray:
        v = np.zeros(self.dim, dtype=np.float32)
        words = tokenize(text)
        if not words:
            return v
        for w in words:
            idx = hash(w) % self.dim
            v[idx] += 1.0
        return v / len(words)

    def encode(self, texts: list[str]) -> np.ndarray:
        return np.stack([self._embed_one(t) for t in texts])
```

---

## 3. 核心：融合两路结果（Hybrid Fusion）

拿到两路分数后，如何合并？主流有两种做法：

### 3.1 倒数排名融合（RRF, Reciprocal Rank Fusion）

**不需要两路分数同尺度**，只看排名。这是工程上最稳、最常用的方法：

```
RRF_score(d) = Σ  1 / (k + rank_i(d))
```

- `rank_i(d)`：文档 d 在第 i 路结果中的排名（从 1 开始）
- `k`：常数（经验值 60），用来压平头部
- 优点：鲁棒、无需调权重、只需排名

### 3.2 加权线性融合

先各自 min-max 归一化，然后 `score = α * norm_sparse + (1 - α) * norm_dense`。需要调 α。

下面给出包含两种融合方式的完整实现：

```python
import numpy as np


def minmax(x: np.ndarray) -> np.ndarray:
    if x.max() - x.min() < 1e-12:
        return np.zeros_like(x)
    return (x - x.min()) / (x.max() - x.min())


class HybridSearcher:
    def __init__(self, corpus: list[str], embedder: FakeEmbedder,
                 alpha: float = 0.5, rrf_k: int = 60):
        self.corpus = corpus
        self.embedder = embedder
        self.alpha = alpha        # 加权融合中稀疏路的权重
        self.rrf_k = rrf_k

        self.bm25 = BM25(corpus)
        self.doc_vecs = embedder.encode(corpus)

    def _sparse_scores(self, query: str) -> np.ndarray:
        return np.array([self.bm25.score(query, i) for i in range(len(self.corpus))])

    def _dense_scores(self, query: str) -> np.ndarray:
        qv = self.embedder.encode([query])[0]
        return cosine_sim_matrix(qv, self.doc_vecs)

    def search_rrf(self, query: str, top_k: int = 5) -> list[tuple[int, float]]:
        sp = self._sparse_scores(query)
        de = self._dense_scores(query)

        # 各自排序，得到 (doc_id, rank)
        sp_rank = {i: r + 1 for r, i in enumerate(np.argsort(-sp))}
        de_rank = {i: r + 1 for r, i in enumerate(np.argsort(-de))}

        rrf = {i: 1.0 / (self.rrf_k + sp_rank[i]) + 1.0 / (self.rrf_k + de_rank[i])
               for i in range(len(self.corpus))}
        return sorted(rrf.items(), key=lambda x: x[1], reverse=True)[:top_k]

    def search_weighted(self, query: str, top_k: int = 5) -> list[tuple[int, float]]:
        sp = minmax(self._sparse_scores(query))
        de = minmax(self._dense_scores(query))
        fused = self.alpha * sp + (1 - self.alpha) * de
        return sorted(enumerate(fused), key=lambda x: x[1], reverse=True)[:top_k]
```

---

## 4. 把它们拼起来跑一遍

```python
corpus = [
    "iPhone 15 电池续航 提升 明显",
    "苹果手机 新款 电池 使用时长 评测",
    "Android 旗舰 快充 技术 对比",
    "iPhone 14 电池 表现 一般",
    "笔记本电脑 续航 排行",
]

embedder = FakeEmbedder(dim=64)
searcher = HybridSearcher(corpus, embedder, alpha=0.5)

query = "iPhone 15 电池续航"
print("稀疏 top3:", searcher.bm25.search(query, 3))
print("稠密 top3:", sorted(enumerate(searcher._dense_scores(query)),
                          key=lambda x: x[1], reverse=True)[:3])
print("RRF  top3:", searcher.search_rrf(query, 3))
print("加权 top3:", searcher.search_weighted(query, 3))
```

你会观察到：
- 稀疏结果偏向字面命中 `iPhone 15` 的文档。
- 稠密结果（因为假嵌入器很弱，效果有限）会偏向含相似词的文档。
- **融合结果**同时兼顾两者——这正是混合检索的意义。

---

## 5. 工程落地要点

1. **真实嵌入模型**：把 `FakeEmbedder` 换成 `sentence-transformers`（如 `BAAI/bge-small-zh-v1.5`）或 API embedding，接口签名保持一致。
2. **向量库**：小规模用 NumPy 直接点积；大规模换 FAISS / HNSW / pgvector / Milvus / Qdrant。
3. **稀疏检索**：生产建议用 Elasticsearch / OpenSearch 的 BM25，或 SPLADE 等学习型稀疏（Learned Sparse）方案。
4. **融合策略**：默认先用 **RRF**（无需调参、稳健）；性能不够再尝试加权融合 + 网格搜 α。
5. **重排序（Rerank）**：拿到 top-50 融合结果后，再用 Cross-Encoder 做精排，是当前 RAG（Retrieval-Augmented Generation）的标准三段式：召回 → 融合 → 重排。

```python
import math
import numpy as np
from collections import Counter


def tokenize(text: str) -> list[str]:
    return text.lower().split()


class BM25:
    def __init__(self, corpus, k1=1.5, b=0.75):
        self.k1, self.b = k1, b
        self.docs = [tokenize(d) for d in corpus]
        self.doc_len = [len(d) for d in self.docs]
        self.avgdl = sum(self.doc_len) / max(len(self.docs), 1)
        df = Counter()
        for d in self.docs:
            for w in set(d):
                df[w] += 1
        N = len(self.docs)
        self.idf = {w: math.log(1 + (N - c + 0.5) / (c + 0.5)) for w, c in df.items()}
        self.tf = [Counter(d) for d in self.docs]

    def score(self, query, doc_id):
        s, dl = 0.0, self.doc_len[doc_id]
        for w in tokenize(query):
            if w not in self.idf or w not in self.tf[doc_id]:
                continue
            tf = self.tf[doc_id][w]
            s += self.idf[w] * (tf * (self.k1 + 1)) / (
                tf + self.k1 * (1 - self.b + self.b * dl / self.avgdl))
        return s

    def search(self, query, top_k=5):
        scores = [(i, self.score(query, i)) for i in range(len(self.docs))]
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]


class FakeEmbedder:
    def __init__(self, dim=64):
        self.dim = dim

    def _embed_one(self, text):
        v = np.zeros(self.dim, dtype=np.float32)
        words = tokenize(text)
        if not words:
            return v
        for w in words:
            v[hash(w) % self.dim] += 1.0
        return v / len(words)

    def encode(self, texts):
        return np.stack([self._embed_one(t) for t in texts])


def cosine_sim_matrix(query_vec, doc_vecs):
    q = query_vec / (np.linalg.norm(query_vec) + 1e-12)
    d = doc_vecs / (np.linalg.norm(doc_vecs, axis=1, keepdims=True) + 1e-12)
    return d @ q


def minmax(x):
    if x.max() - x.min() < 1e-12:
        return np.zeros_like(x)
    return (x - x.min()) / (x.max() - x.min())


class HybridSearcher:
    def __init__(self, corpus, embedder, alpha=0.5, rrf_k=60):
        self.corpus = corpus
        self.embedder = embedder
        self.alpha = alpha
        self.rrf_k = rrf_k
        self.bm25 = BM25(corpus)
        self.doc_vecs = embedder.encode(corpus)

    def _sparse_scores(self, query):
        return np.array([self.bm25.score(query, i) for i in range(len(self.corpus))])

    def _dense_scores(self, query):
        qv = self.embedder.encode([query])[0]
        return cosine_sim_matrix(qv, self.doc_vecs)

    def search_rrf(self, query, top_k=5):
        sp, de = self._sparse_scores(query), self._dense_scores(query)
        sp_rank = {i: r + 1 for r, i in enumerate(np.argsort(-sp))}
        de_rank = {i: r + 1 for r, i in enumerate(np.argsort(-de))}
        rrf = {i: 1.0 / (self.rrf_k + sp_rank[i]) + 1.0 / (self.rrf_k + de_rank[i])
               for i in range(len(self.corpus))}
        return sorted(rrf.items(), key=lambda x: x[1], reverse=True)[:top_k]

    def search_weighted(self, query, top_k=5):
        sp = minmax(self._sparse_scores(query))
        de = minmax(self._dense_scores(query))
        fused = self.alpha * sp + (1 - self.alpha) * de
        return sorted(enumerate(fused), key=lambda x: x[1], reverse=True)[:top_k]


if __name__ == "__main__":
    corpus = [
        "iPhone 15 电池续航 提升 明显",
        "苹果手机 新款 电池 使用时长 评测",
        "Android 旗舰 快充 技术 对比",
        "iPhone 14 电池 表现 一般",
        "笔记本电脑 续航 排行",
    ]
    embedder = FakeEmbedder(dim=64)
    searcher = HybridSearcher(corpus, embedder, alpha=0.5)

    query = "iPhone 15 电池续航"
    print("稀疏 top3:", searcher.bm25.search(query, 3))
    print("稠密 top3:", sorted(enumerate(searcher._dense_scores(query)),
                              key=lambda x: x[1], reverse=True)[:3])
    print("RRF  top3:", searcher.search_rrf(query, 3))
    print("加权 top3:", searcher.search_weighted(query, 3))
```

## ai.vec.bm25

# ai.vec.bm25：从零理解稀疏检索的黄金基线

## 一句话直觉

BM25（Best Matching 25）是信息检索里最经典的"打分公式"——它回答一个问题：**给定一个查询词，一篇文档到底有多相关？** 你搜 Google、用 Elasticsearch、做 RAG 检索，底层都可能跑着 BM25。它是稀疏向量（sparse vector）检索的代表，也是所有向量检索系统的"对照组"。

---

## 1. 从 TF-IDF 出发：为什么需要打分？

检索的最小单元是"词"（term）。给定查询 `q` 和文档 `d`，最朴素的想法是数词频（Term Frequency, TF）。但常识告诉我们：

- 一个词在文档里出现 10 次，不代表比出现 5 次相关 2 倍。
- "的"、"是"这类词到处出现，区分度极低。

于是 IDF（Inverse Document Frequency，逆文档频率）登场：**越稀有的词，权重越高**。

```python
import math

# 假设有 1000 篇文档，其中 "bm25" 只在 10 篇里出现
N = 1000
df = 10
idf = math.log((N - df + 0.5) / (df + 0.5) + 1)
print(f"IDF(bm25) = {idf:.3f}")  # 越稀有越大

# 对比一个常见词 "the"，假设出现在 900 篇里
df_common = 900
idf_common = math.log((N - df_common + 0.5) / (df_common + 0.5) + 1)
print(f"IDF(the)  = {idf_common:.3f}")  # 接近 0
```

**关键结论**：TF 负责"这个词在这篇文档里重要吗"，IDF 负责"这个词在整个语料里稀有吗"，两者相乘就是经典的 TF-IDF。

---

## 2. BM25 的三大改进

BM25 在 TF-IDF 上做了三处修正，让打分更符合直觉：

1. **TF 饱和（saturation）**：词频再高，分数也有上界。参数 `k1` 控制饱和速度。
2. **文档长度归一化**：长文档天然词频更高，需要惩罚。参数 `b` 控制惩罚强度（0=不归一，1=完全归一）。
3. **IDF 平滑**：避免出现负数 IDF。

公式（单词项）：

```
score(q, d) = IDF(t) * ( tf * (k1 + 1) ) / ( tf + k1 * (1 - b + b * |d| / avgdl) )
```

多词查询就是把每个词的分数**求和**。

---

## 3. 手写一个 BM25

下面是一个可以真正跑起来的最小实现，包含分词、IDF、长度归一化和打分。

```python
import math
from collections import Counter

def tokenize(text):
    # 极简分词：小写 + 按空白切分。工程里应换成 jieba / spaCy 等
    return text.lower().split()

class BM25:
    def __init__(self, corpus, k1=1.5, b=0.75):
        self.k1 = k1
        self.b = b
        self.docs = [tokenize(d) for d in corpus]
        self.N = len(self.docs)
        self.avgdl = sum(len(d) for d in self.docs) / self.N
        self.tfs = [Counter(d) for d in self.docs]
        # 每个词的文档频率 df
        self.df = Counter()
        for d in self.docs:
            for w in set(d):
                self.df[w] += 1
        # 预计算 IDF
        self.idf = {
            w: math.log((self.N - df + 0.5) / (df + 0.5) + 1)
            for w, df in self.df.items()
        }

    def score(self, query, idx):
        q = tokenize(query)
        doc = self.docs[idx]
        dl = len(doc)
        tf = self.tfs[idx]
        s = 0.0
        for w in q:
            if w not in self.idf or tf[w] == 0:
                continue
            f = tf[w]
            denom = f + self.k1 * (1 - self.b + self.b * dl / self.avgdl)
            s += self.idf[w] * f * (self.k1 + 1) / denom
        return s

    def search(self, query, topk=3):
        scored = [(self.score(query, i), i) for i in range(self.N)]
        scored.sort(reverse=True)
        return scored[:topk]

# —— 演示 ——
corpus = [
    "BM25 is a ranking function used in information retrieval",
    "Vector search uses dense embeddings for semantic retrieval",
    "BM25 combines term frequency and inverse document frequency",
    "Information retrieval systems often use BM25 as a baseline",
]
bm = BM25(corpus)
for s, i in bm.search("BM25 retrieval"):
    print(f"score={s:.4f}  doc{i}: {corpus[i]}")
```

**关键结论**：BM25 的输出是**稀疏向量内积**——每个查询词只激活文档中出现的少数几个维度。这也是它和稠密向量检索（如 embedding）最本质的区别：BM25 的"向量"维度是整个词表，绝大多数位置是 0。

---

## 4. 为什么 BM25 至今仍是"黄金基线"

- **零训练**：无需 GPU、无需 embedding 模型，给定语料即可工作。
- **可解释**：能直接告诉你哪个词贡献了多少分。
- **强基线**：在 RAG、搜索引擎评测里，BM25 经常能打赢未经精调的稠密检索。
- **互补性**：BM25 擅长精确匹配（专有名词、代码、ID），稠密检索擅长语义泛化。工业界常用 **混合检索（hybrid retrieval）**：BM25 + dense，再融合排序。

```python
# 混合检索的最小骨架示意（加权融合）
def hybrid_search(bm25_scores, dense_scores, alpha=0.5):
    # 归一化后加权求和
    def norm(arr):
        lo, hi = min(arr), max(arr)
        return [(x - lo) / (hi - lo + 1e-9) for x in arr]
    b = norm(bm25_scores)
    d = norm(dense_scores)
    return [alpha * bi + (1 - alpha) * di for bi, di in zip(b, d)]

# 例如 BM25 分数 [3.2, 1.1, 0.5]，稠密分数 [0.8, 0.9, 0.3]
print(hybrid_search([3.2, 1.1, 0.5], [0.8, 0.9, 0.3]))
```

---

## 5. 工程实践中的调参与陷阱

- **k1 ∈ [1.2, 2.0]**：控制词频饱和。太大则词频高的文档被打得过高。
- **b ∈ [0.5, 0.8]**：控制长度归一。短查询、短文档场景可调小 b。
- **分词（tokenization）**：中文必须引入分词器；英文要处理词干（stemming）或词形还原（lemmatization）。
- **停用词（stopwords）**：BM25 的 IDF 已能自动压低常见词，但显式去除停用词仍常有收益。
- **索引（inverted index，倒排索引）**：生产环境用倒排索引把 `score` 从 O(N) 降到 O(命中文档数)，Elasticsearch / Lucene / rank_bm25 都是如此。

**关键结论**：BM25 不是"过时技术"，而是检索系统的"地基"——理解它，才能真正理解向量检索为什么需要它、又在哪里超越了它。

---

## 动手练习

**任务**：在本地实现一个 mini BM25 搜索引擎，并完成一次对比实验。

1. 准备 10 篇中文短文（可以是你喜欢的电影简介、新闻摘要），保存为 `docs.txt`，每行一篇。
2. 用 `jieba` 分词（`pip install jieba`），替换上面代码里的 `tokenize`。
3. 实现 `BM25` 类，支持 `search(query, topk=3)`。
4. 用查询 `"人工智能"` 和 `"电影推荐"` 分别检索，打印 top-3 结果及分数。
5. **对比实验**：把 `k1` 分别设为 `0.5` 和 `2.0`，`b` 分别设为 `0.0` 和 `1.0`，观察排序变化，并在注释里写下你的结论。

**进阶（可选）**：用 `rank_bm25` 库（`pip install rank_bm25`）跑同样语料，对比你手写实现的分数是否一致，并思考差异来源。

```python
import math
from collections import Counter

def tokenize(text):
    return text.lower().split()

class BM25:
    def __init__(self, corpus, k1=1.5, b=0.75):
        self.k1, self.b = k1, b
        self.docs = [tokenize(d) for d in corpus]
        self.N = len(self.docs)
        self.avgdl = sum(len(d) for d in self.docs) / self.N
        self.tfs = [Counter(d) for d in self.docs]
        self.df = Counter()
        for d in self.docs:
            for w in set(d):
                self.df[w] += 1
        self.idf = {w: math.log((self.N - df + 0.5) / (df + 0.5) + 1)
                    for w, df in self.df.items()}

    def score(self, query, idx):
        q = tokenize(query)
        dl = len(self.docs[idx])
        tf = self.tfs[idx]
        s = 0.0
        for w in q:
            if w not in self.idf or tf[w] == 0:
                continue
            f = tf[w]
            denom = f + self.k1 * (1 - self.b + self.b * dl / self.avgdl)
            s += self.idf[w] * f * (self.k1 + 1) / denom
        return s

    def search(self, query, topk=3):
        scored = [(self.score(query, i), i) for i in range(self.N)]
        scored.sort(reverse=True)
        return scored[:topk]

corpus = [
    "BM25 is a ranking function used in information retrieval",
    "Vector search uses dense embeddings for semantic retrieval",
    "BM25 combines term frequency and inverse document frequency",
    "Information retrieval systems often use BM25 as a baseline",
]
bm = BM25(corpus)
for s, i in bm.search("BM25 retrieval"):
    print(f"score={s:.4f}  doc{i}: {corpus[i]}")
```


---

## 本课题目

### single_choice · None



- [A] 只使用关键词倒排索引，按词频排序返回结果
- [B] 只使用向量相似度检索，忽略关键词匹配
- [C] 同时执行关键词检索和向量检索，并将两路结果融合排序
- [D] 先随机抽取一部分文档，再对这部分文档做向量检索

**参考答案**：2

**解析**：混合检索的核心是结合稀疏检索（关键词/倒排索引）与稠密检索（向量语义）两条召回路径，再通过融合策略（如加权求和、RRF）合并排序。A、B 只覆盖单一路径；D 属于随机采样，与混合检索无关。

### single_choice · None



- [A] 召回阶段必须使用向量检索，重排阶段必须使用关键词匹配
- [B] 召回阶段可以并行执行关键词检索和向量检索，重排阶段对合并后的候选集统一打分
- [C] 召回阶段只能返回一个结果，重排阶段再扩充结果
- [D] 重排阶段的作用是替换召回阶段，因此可以跳过召回直接重排

**参考答案**：1

**解析**：混合检索通常在召回阶段并行跑稀疏和稠密两路检索，得到候选集后再在重排阶段统一打分融合。A 把两阶段职责说反；C 召回通常返回多个候选；D 重排依赖召回提供的候选，不能跳过召回。

### single_choice · None



- [A] 关键词检索没有生效，需要关闭关键词路径
- [B] 关键词精确匹配会引入词汇歧义，需要向量语义或重排来纠正
- [C] 向量检索一定也会把“Python 蛇”排在前面
- [D] CSV 文件无法被任何检索器处理

**参考答案**：1

**解析**：关键词匹配只看到“Python”字面，无法区分编程语言和蛇，容易产生歧义。混合检索中向量语义或统一重排可以缓解这种问题。A 因噎废食；C 没有必然性；D 与题意无关。

### single_choice · None



- [A] 把多个检索器返回的候选文档合并成一个统一排序的列表
- [B] 把多个文档拼接成一个更长的文档
- [C] 把查询扩展成多个同义词查询
- [D] 把向量维度从高维降到低维

**参考答案**：0

**解析**：融合步骤的目标是整合多路召回结果，形成一个统一的排序列表。B 是文档拼接，C 是查询扩展，D 是降维，都不是融合步骤的核心任务。

### single_choice · None



- [A] 每路检索只召回 1 个结果，保证速度最快
- [B] 每路检索召回适量候选，例如各取前几十到几百条，再统一重排
- [C] 每路检索召回全部文档，确保不遗漏
- [D] 候选集大小对最终效果没有任何影响

**参考答案**：1

**解析**：每路召回适量候选可以在效果和效率之间取得平衡，再通过重排精筛。A 召回太少容易漏掉相关文档；C 代价过高；D 候选集大小会影响召回率和延迟。

### single_choice · None



- [A] 只用关键词检索，因为关键词能处理同义词
- [B] 只用向量检索，因为向量能精确匹配型号
- [C] 关键词检索负责精确匹配型号，向量检索负责语义泛化，再融合两路结果
- [D] 随机选择关键词或向量其中一路返回结果

**参考答案**：2

**解析**：关键词检索擅长精确匹配型号、编号；向量检索擅长语义泛化、同义词。两者融合可同时满足两类需求。A、B 把能力说反；D 随机选择不能稳定兼顾。

### single_choice · None



- [A] Precision@K 或 Recall@K 等排序指标
- [B] 训练时的学习率
- [C] 嵌入向量的维度
- [D] 索引构建的耗时

**参考答案**：0

**解析**：混合检索最终输出排序列表，常用 Precision@K、Recall@K、MRR、NDCG 等排序指标评测。B、C、D 是训练或工程参数，不是排序质量指标。

### single_choice · None



- [A] 提高向量检索的权重并检查/改进分词或查询预处理
- [B] 降低向量检索的权重
- [C] 关闭向量检索路径
- [D] 增加文档数量

**参考答案**：0

**解析**：关键词路召回差往往与分词或查询预处理有关，应检查并改进；同时可适当提高向量权重以缓解。B、C 会进一步削弱语义路；D 不直接解决分词问题。

### single_choice · None



- [A] 并行召回是两路检索同时执行，串行召回是一路的结果作为另一路的输入或过滤条件
- [B] 并行召回一定比串行召回效果差
- [C] 串行召回不需要任何索引
- [D] 并行召回只能用于图像检索，不能用于文本检索

**参考答案**：0

**解析**：并行召回是两路独立同时执行再融合；串行召回可以先用一路缩小范围，再用另一路精排。B 效果取决于场景；C 串行也需要索引；D 明显错误。

### single_choice · None



- [A] 交叉编码器让查询和文档一起输入模型，能建模更细粒度的交互，但计算开销更大
- [B] 交叉编码器只能处理关键词，不能处理向量
- [C] 双编码器不能用于文本检索
- [D] 交叉编码器不需要候选集，可以直接生成文档

**参考答案**：0

**解析**：交叉编码器将查询和文档拼接后共同编码，交互更充分、精度通常更高，但逐对计算开销大，常用于重排阶段。B、C 说法错误；D 重排仍需要候选集。

### single_choice · None



- [A] 召回率指标不能反映排序质量，且融合时关键词路径可能被弱化
- [B] 召回率高就一定意味着所有场景都好
- [C] 向量检索无法处理任何查询
- [D] 编号类查询不需要精确匹配

**参考答案**：0

**解析**：召回率高说明相关文档在前 K 个候选里，但编号类查询需要精确匹配并排在前面，若融合权重偏向向量，关键词命中的编号可能被压后。B 过于绝对；C、D 不成立。

### single_choice · None



- [A] 对查询同时执行关键词检索和向量检索，并在融合时保留两路的高分候选
- [B] 只保留关键词检索结果，删除向量检索结果
- [C] 只保留向量检索结果，删除关键词检索结果
- [D] 将查询拆成单字后只做关键词匹配

**参考答案**：0

**解析**：混合查询中既有专有名词（适合关键词）又有语义描述（适合向量），同时保留两路高分候选并融合最合理。B、C 丢失一路信息；D 拆成单字会破坏语义和精确匹配。

### single_choice · None



- [A] 向量检索的得分范围太小，直接相加会被关键词得分主导
- [B] 向量检索的得分范围太大，直接相加会压过关键词得分
- [C] 余弦相似度不能用于文本检索
- [D] 关键词检索的得分不应该参与排序

**参考答案**：0

**解析**：不同检索器的分数尺度不同，直接相加会让量级大的那一路主导结果。关键词得分 0~10 远大于向量得分 0~1，因此向量路几乎被淹没。B 与事实相反；C、D 说法不成立。

### single_choice · None



- [A] 每个文档在两路结果中的原始得分绝对值
- [B] 每个文档在两路结果中的排名位置
- [C] 每个文档的文本长度
- [D] 每个文档被检索到的次数除以文档总数

**参考答案**：1

**解析**：RRF 的核心思想是根据文档在各路结果中的排名（rank）计算融合分数，通常形式为 1/(k+rank) 求和，不依赖原始得分的绝对尺度。A 是直接分数融合的思路；C、D 与 RRF 无关。

### single_choice · None



- [A] 可以完全不需要建立任何索引
- [B] 能同时利用关键词精确匹配能力和向量语义泛化能力
- [C] 可以保证返回结果一定比纯向量检索少
- [D] 可以避免对查询文本做任何预处理

**参考答案**：1

**解析**：混合检索结合稀疏检索（精确词汇匹配）和稠密检索（语义泛化）的优点，既能命中专有名词、编号等，又能召回语义相近但用词不同的内容。A、D 不成立；C 与优势无关且通常不保证。

### single_choice · None



- [A] 查询“如何缓解工作压力”，希望找到语义相近但用词不同的文章
- [B] 查询“错误码 E5021”，需要精确匹配这个编号
- [C] 查询“推荐一些好看的电影”，希望按语义相关性排序
- [D] 查询“介绍人工智能的发展历史”，希望覆盖不同表述的段落

**参考答案**：1

**解析**：错误码、产品型号、专有名词等需要精确匹配，关键词/倒排检索路径更擅长。A、C、D 更依赖语义泛化，是向量检索的强项，不能体现关键词路径的独特价值。

### single_choice · None



- [A] 关键词精确匹配的文档排名被削弱，语义相近但用词不同的文档更容易排前
- [B] 所有结果都会变成关键词精确匹配的文档
- [C] 向量检索的得分范围会自动缩小
- [D] 关键词检索会自动停止工作

**参考答案**：0

**解析**：加权融合中权重决定某一路对最终排序的影响。向量权重过高会稀释关键词路的作用，使语义相似文档占优，精确匹配的文档可能被压后。B 与题意相反；C、D 不会因权重变化自动发生。

### single_choice · None



- [A] 稀疏向量通常维度极高但每篇文档只有少量非零分量，稠密向量通常维度较低且分量大多非零
- [B] 稀疏向量一定比稠密向量维度低
- [C] 稠密向量只能表示关键词是否出现，不能表示语义
- [D] 稀疏向量和稠密向量都不能用于文本检索

**参考答案**：0

**解析**：稀疏向量（如 TF-IDF、BM25 的词项向量）维度高、非零项少；稠密向量（如神经嵌入）维度较低、分量稠密，能编码语义。B 与事实相反；C 把两者能力说反；D 明显错误。

### single_choice · None



- [A] 两路检索都返回了较多候选文档
- [B] 两路检索的候选文档集合完全不重叠
- [C] 两路检索的得分没有做归一化就直接加权相加
- [D] 检索时使用了相同的查询文本

**参考答案**：2

**解析**：BM25 得分和嵌入相似度得分尺度不同，未归一化直接加权相加会让量级大的一路主导融合。A、B、D 本身不一定导致效果差；候选不重叠也可以通过融合策略整合。

### single_choice · None



- [A] 只使用一个检索器，因此实现更简单
- [B] 保留多路检索各自的优势，再由重排模型综合判断相关性
- [C] 不需要任何候选集，直接输出最终结果
- [D] 重排阶段只能使用关键词匹配，不能使用向量

**参考答案**：1

**解析**：混合检索的典型流程是多路召回保留各自长处，再由重排模型统一打分。A 描述的是单检索器方案；C 重排必须有候选集；D 重排模型可以任意设计，不限于关键词。

### single_choice · None



- [A] BM25 使用词频饱和函数，避免词频线性增长带来的过度加权
- [B] BM25 完全抛弃了 IDF 成分
- [C] BM25 不进行文档长度归一化
- [D] BM25 只能用于二值词袋，无法处理词频

**参考答案**：0

**解析**：BM25 在 TF-IDF 基础上引入了词频饱和（k1 参数）和文档长度归一化（b 参数），词频贡献随出现次数增加逐渐饱和而非线性增长。IDF 成分依然保留，长度归一化也是其核心特征之一，且它处理的是带权词频。

### single_choice · None



- [A] 完全不进行文档长度归一化
- [B] 完全按文档长度归一化
- [C] 只考虑查询词长度
- [D] 关闭词频饱和

**参考答案**：0

**解析**：b 控制文档长度归一化的强度。b=0 时长度归一化因子为 1，即不考虑文档长度差异；b=1 时完全按文档长度相对平均长度归一化。

### multi_choice · None



- [A] 先对文本进行分词，再统计词频与文档频率
- [B] 对停用词进行过滤以减少噪声
- [C] 统计每篇文档长度和语料平均长度
- [D] 把整段文本当作一个词直接计算词频
- [E] 忽略文档频率统计直接给所有词相同 IDF

**参考答案**：[0, 1, 2]

**解析**：BM25 依赖词项级别的词频、文档频率和文档长度统计，因此必须先分词并统计长度；停用词过滤有助于减少噪声。整段文本当一词或忽略 DF 都会破坏 BM25 的核心假设。

### multi_choice · None



- [A] IDF 由文档频率和文档总数共同决定
- [B] 文档频率越高的词 IDF 一般越低
- [C] 词频越高，BM25 中该词的贡献单调增加但有上界
- [D] 文档长度越短，在 b>0 时长度归一化因子越小
- [E] avgdl 越小，长文档受到的惩罚越小

**参考答案**：[0, 1, 2, 3]

**解析**：IDF 依赖 DF 与 N；DF 高的词 IDF 低；TF 贡献单调但饱和；短文档 dl/avgdl 小使归一化因子小（<1）。avgdl 越小，同样长度的文档 dl/avgdl 越大，长文档惩罚反而越大，故最后一项错误。

### fill_blank · None



**参考答案**：["k1, b", "k1,b", "k1, b ", "k1，b"]

**解析**：k1 控制词频饱和速度，b 控制文档长度归一化强度，二者是 BM25 最核心的两个可调参数。

### fill_blank · None



**参考答案**：["avgdl", "平均文档长度"]

**解析**：长度归一化以平均文档长度 avgdl 为基准，dl/avgdl 反映当前文档相对平均长度的比例。

### fill_blank · None



**参考答案**：["0", "接近0", "接近于0", "零", "接近零", "近似0"]

**解析**：在平滑 IDF 公式 log((N-n+0.5)/(n+0.5)+1) 中，当 n 接近 N 时括号内趋近 1，log 趋近 0，即高频词权重接近零。

### code_reading · None



**参考答案**：score 随 t 增加单调递增，但增长逐渐放缓并趋近上界 (k1+1)=2.2；t=1 时 score≈1.0，t=100 时 score≈2.17。这体现了词频饱和：从 1 增到 2 收益大，从 100 增到 101 收益极小。

**解析**：该式是 BM25 词频饱和项在 dl=avgdl、b 不生效或长度相同时的简化形式。分母 t+k1 使增长呈饱和曲线，上限为 k1+1。

### code_reading · None



**参考答案**：idf_smooth 会略小于 idf_classic。n=1 时平滑式 = log((99.5)/(1.5)+1)=log(67.33)≈4.21，经典式 = log(100/1)=log(100)≈4.605。两者都随词越稀有越大，但平滑式通过 +0.5 与 +1 压低极稀词的权重并避免负值。

**解析**：平滑 IDF 在稀有词上给出有限上界，避免单个罕见词被过度放大，同时在高频词上保持非负，这是 BM25 数值稳健性的来源。

### code_reading · None



**参考答案**：文档 A 的贡献更大。norm_A = 1-0.75+0.75*0.5 = 0.625，norm_B = 1-0.75+0.75*5 = 4.0。长度归一化因子作为分母，norm 越小则词频贡献被衰减得越少，而 A 的因子小于 1，B 大于 1，故 A 在相同词频下得到更大贡献。

**解析**：长度归一化因子 (1-b+b*dl/avgdl) 位于词频项分母，短于平均长度的文档因子<1（增益），长于平均长度的文档因子>1（惩罚），从而实现按长度调节。

### scenario · None



**解析**：问题根源是长度归一化不足或 b 偏小。增大 b（向 1 靠近）会加强按平均文档长度归一化的力度，使 dl/avgdl 较大的长标题在分母中受到更大惩罚，从而抑制长标题堆砌词的优势。同时应检查 dl 与 avgdl 的统计口径是否一致。

### scenario · None



**解析**：BM25 的 IDF 由文档频率决定：出现于大量文档的常见虚词 DF 高、IDF 接近 0，本应贡献很小，理论上不会导致异常靠前。若出现异常，往往是停用词未过滤导致其与其他高频词组合或分词误差放大了作用。改善方案包括过滤停用词、检查分词质量、核对 IDF 平滑形式与统计口径，必要时对停用词直接赋予零权重。

### single_choice · None



- [A] 词频贡献的饱和速度
- [B] 文档长度归一化强度
- [C] IDF 的平滑程度
- [D] 查询词的权重上限

**参考答案**：0

**解析**：k1 决定词频增加时得分增长的饱和速度，k1 越大饱和越慢，k1 越小越快达到上限；b 才控制长度归一化。

### single_choice · None



- [A] 避免高频词（出现于多数文档）得到负分，使权重非负且更稳定
- [B] 使 IDF 与词频完全无关
- [C] 使所有词的 IDF 相等
- [D] 消除对文档总数 N 的依赖

**参考答案**：0

**解析**：经典 IDF 在词出现于超过一半文档时可能为负，BM25 常用的平滑形式通过加 0.5 与加 1 保证非负，避免高频词对结果产生不合理的负贡献。

### single_choice · None



- [A] 约 0.22
- [B] 约 -1.6
- [C] 约 1.6
- [D] 约 0.5

**参考答案**：0

**解析**：log((1000-800+0.5)/(800+0.5)+1)=log(200.5/800.5+1)=log(1.2504)≈0.223。经典 IDF log(1000/800)≈0.223 也接近，但关键是使用平滑形式时该高频词权重很小而非负值。

### single_choice · None



- [A] 语料库中所有文档的平均长度
- [B] 查询的平均长度
- [C] 一篇文档中最长字段的长度
- [D] 出现该查询词的文档平均长度

**参考答案**：0

**解析**：avgdl 是语料库整体的平均文档长度，用于在长度归一化因子中作为参照基准。

### single_choice · None



- [A] 被除以一个大于 1 的因子而衰减
- [B] 被乘以一个大于 1 的因子而放大
- [C] 完全不受影响
- [D] 直接置零

**参考答案**：0

**解析**：长度归一化因子为 (1 - b + b * dl/avgdl)。当 dl>avgdl 且 b>0 时该因子大于 1，作为分母使词频贡献衰减，抑制长文档通过堆砌词获得高分。

### single_choice · None



- [A] 两者都可以看作对词权重的加权求和，但 BM25 的词频饱和与长度归一化设计更契合检索排序经验
- [B] BM25 不需要任何词权重，只做布尔匹配
- [C] 余弦相似度无法处理词频
- [D] BM25 的输出是固定归一化到 [0,1] 的相似度

**参考答案**：0

**解析**：BM25 可视为一种带饱和与非对称归一化的加权词匹配打分，与 VSM/余弦相似度同属词袋检索家族，但在 TF 饱和、长度归一化和 IDF 形式上针对检索排序做了经验性优化；其得分并非 [0,1] 归一化。

### multi_choice · None



- [A] 词频饱和项
- [B] 文档长度归一化项
- [C] 文档频率相关的 IDF 项
- [D] 对查询词进行同义词扩展
- [E] 对高词频进行线性无上限放大

**参考答案**：[0, 1, 2]

**解析**：BM25 由 IDF、含饱和的词频项以及文档长度归一化项组成；同义词扩展属于查询改写，不属 BM25 公式；BM25 恰恰对词频做饱和处理而非无上限线性放大。

### multi_choice · None



- [A] b 取 0 会忽略文档长度差异
- [B] b 取 1 会完全按文档长度相对平均值归一化
- [C] k1 越大，词频达到饱和所需的出现次数越多
- [D] k1 和 b 在绝大多数场景下必须相等
- [E] 增大 k1 会关闭 IDF

**参考答案**：[0, 1, 2]

**解析**：b 控制长度归一化力度，0 表示不归一化，1 表示完全归一化；k1 控制饱和速度，值越大饱和越慢。k1 与 b 相互独立，调大 k1 不影响 IDF。
