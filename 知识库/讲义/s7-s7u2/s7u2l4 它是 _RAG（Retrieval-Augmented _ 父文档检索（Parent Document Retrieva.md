# s7u2l4 它是 **RAG（Retrieval-Augmented / 父文档检索（Parent Document Retrieval）

> 来源 `content/lessons/s7u2l4.json`

## agent.rag.hybrid

## 一句话直觉

**混合检索（Hybrid Retrieval）**就是：当你要让 AI 从自己的资料库里找答案时，不要只靠一种找法，而是**同时用「关键词匹配」和「语义相似」两条路去找，再把结果融合排序**，这样既不会漏掉精确术语，也不会因为换个说法就搜不到。

它是 **RAG（Retrieval-Augmented Generation，检索增强生成）** 里最关键的检索环节。

---

## 1. 为什么单一检索不够？

RAG 的第一步是「检索（Retrieval）」：用户提问后，系统要从知识库里找出最相关的文档片段，再交给大模型生成答案。

常见的两种检索方式：

| 方式 | 原理 | 优点 | 缺点 |
|---|---|---|---|
| **稀疏检索（Sparse Retrieval）** | 基于关键词/词频，如 BM25 | 精确匹配术语、编号、人名 | 换个说法就搜不到 |
| **稠密检索（Dense Retrieval）** | 把文本变成向量，比语义相似度 | 理解同义、近义表达 | 对精确术语、罕见词不敏感 |

举个例子：

- 查询：「Python 怎么读文件？」
- 文档：「使用 open() 函数打开文本文件」

**BM25** 可能因为“读”“文件”匹配到；但如果查询是「Python 如何加载本地文本」，BM25 就可能漏掉，而**向量检索**能靠语义找到。

反过来，查询「错误码 E1024」时，向量检索可能把语义相近但编号不同的文档排前面，而 BM25 能精确命中。

所以：**两者互补，混合检索就是把它们的优势合起来。**

---

## 2. 混合检索的核心流程

一个标准的混合检索管道（pipeline）分四步：

1. **并行检索**：同一查询分别送给 BM25 和向量检索，各取 Top-K 结果。
2. **分数归一化**：两种检索的分数尺度不同，需要归一化到同一区间。
3. **融合排序**：用加权求和或 RRF（Reciprocal Rank Fusion，倒数排名融合）合并。
4. **返回 Top-N**：把融合后的前 N 个片段交给大模型。

最常用的融合算法是 **RRF**，它只看排名不看分数，简单又稳：

```
RRF_score(d) = Σ  1 / (k + rank_i(d))
```

其中 `k` 通常取 60，`rank_i(d)` 是文档 d 在第 i 路检索中的排名。

---

## 3. 用 Python 实现一个最小混合检索

下面代码不依赖任何外部模型，用纯 Python 演示 BM25 思路 + 余弦相似度 + RRF 融合。

```python
import math
from collections import Counter

# 模拟知识库
docs = [
    "Python 使用 open() 函数打开文本文件",
    "如何用 pandas 读取 CSV 数据",
    "错误码 E1024 表示文件权限不足",
    "Python 加载本地文本文件的几种方式",
]

# ---------- 1. 稀疏检索：简化的 BM25 ----------
def bm25_scores(query, docs):
    query_terms = query.lower().split()
    scores = []
    for doc in docs:
        terms = doc.lower().split()
        score = sum(terms.count(q) for q in query_terms)
        scores.append(score)
    return scores

# ---------- 2. 稠密检索：字符级余弦相似度（演示用） ----------
def cosine_scores(query, docs):
    def vec(text):
        c = Counter(text)
        return c
    qv = vec(query)
    scores = []
    for doc in docs:
        dv = vec(doc)
        common = set(qv) & set(dv)
        dot = sum(qv[k] * dv[k] for k in common)
        norm_q = math.sqrt(sum(v*v for v in qv.values()))
        norm_d = math.sqrt(sum(v*v for v in dv.values()))
        scores.append(dot / (norm_q * norm_d + 1e-9))
    return scores

# ---------- 3. RRF 融合 ----------
def rrf_fusion(rank_lists, k=60):
    scores = {}
    for ranks in rank_lists:
        for rank, doc_id in enumerate(ranks, start=1):
            scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank)
    return sorted(scores.items(), key=lambda x: -x[1])

# ---------- 4. 执行混合检索 ----------
query = "Python 读取文本文件"

bm25 = bm25_scores(query, docs)
dense = cosine_scores(query, docs)

bm25_rank = sorted(range(len(docs)), key=lambda i: -bm25[i])
dense_rank = sorted(range(len(docs)), key=lambda i: -dense[i])

fused = rrf_fusion([bm25_rank, dense_rank])

print("BM25 排名:", [docs[i] for i in bm25_rank])
print("向量排名:", [docs[i] for i in dense_rank])
print("融合结果:")
for doc_id, score in fused:
    print(f"  {score:.4f}  {docs[doc_id]}")
```

运行后你会看到：融合结果把「open() 打开文件」和「加载本地文本文件」都排到了前面，兼顾了关键词和语义。

---

## 4. 工程级要点

真实项目里，混合检索通常这样落地：

- **稀疏侧**：Elasticsearch / OpenSearch 的 BM25，或 `rank_bm25` 库。
- **稠密侧**：Sentence-Transformers、OpenAI Embeddings、BGE、E5 等模型 + FAISS / Milvus / Chroma。
- **融合**：RRF 或加权分数融合（weighted sum），权重可用验证集调优。
- **重排（Rerank）**：融合后常再加一个 Cross-Encoder 重排，进一步提升精度。

一个典型的生产链路：

```
Query
  ├─ BM25 检索 Top-50
  └─ 向量检索 Top-50
        ↓
      RRF 融合 Top-20
        ↓
   Cross-Encoder 重排 Top-5
        ↓
      LLM 生成答案
```

---

## 5. 什么时候必须用混合检索？

- 知识库里有**专业术语、编号、代码符号**（如 API 名、错误码）。
- 用户提问**口语化、同义表达多**。
- 单一检索的召回率（Recall）不达标。
- 对**精确率和召回率都要求高**的企业级 RAG。

简单说：**只要单一检索有短板，混合检索就是默认升级方案。**

---

## 动手练习

**任务**：把上面的示例代码改成一个可交互脚本。

要求：
1. 知识库换成 5 条你自己写的短句（比如你熟悉的领域知识）。
2. 支持命令行输入查询，循环检索。
3. 分别打印 BM25 排名、向量排名、RRF 融合排名。
4. 额外实验：把 RRF 里的 `k` 改成 1、10、60、100，观察融合结果变化，并写 3 句话总结。

提交：一段可运行的 `.py` 文件 + 你的观察结论。

```python
import math
from collections import Counter

docs = [
    "Python 使用 open() 函数打开文本文件",
    "如何用 pandas 读取 CSV 数据",
    "错误码 E1024 表示文件权限不足",
    "Python 加载本地文本文件的几种方式",
]

def bm25_scores(query, docs):
    query_terms = query.lower().split()
    return [sum(doc.lower().split().count(q) for q in query_terms) for doc in docs]

def cosine_scores(query, docs):
    def vec(text):
        return Counter(text)
    qv = vec(query)
    out = []
    for doc in docs:
        dv = vec(doc)
        common = set(qv) & set(dv)
        dot = sum(qv[k] * dv[k] for k in common)
        nq = math.sqrt(sum(v * v for v in qv.values()))
        nd = math.sqrt(sum(v * v for v in dv.values()))
        out.append(dot / (nq * nd + 1e-9))
    return out

def rrf_fusion(rank_lists, k=60):
    scores = {}
    for ranks in rank_lists:
        for rank, doc_id in enumerate(ranks, start=1):
            scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank)
    return sorted(scores.items(), key=lambda x: -x[1])

query = "Python 读取文本文件"
bm25 = bm25_scores(query, docs)
dense = cosine_scores(query, docs)
bm25_rank = sorted(range(len(docs)), key=lambda i: -bm25[i])
dense_rank = sorted(range(len(docs)), key=lambda i: -dense[i])
fused = rrf_fusion([bm25_rank, dense_rank])

print("BM25 排名:", [docs[i] for i in bm25_rank])
print("向量排名:", [docs[i] for i in dense_rank])
print("融合结果:")
for doc_id, score in fused:
    print(f"  {score:.4f}  {docs[doc_id]}")
```

## agent.rag.parent_doc

# 父文档检索（Parent Document Retrieval）

> **一句话直觉**：与其把长文档切碎后只把“碎片”喂给模型，不如**用小块做检索、用大块做回答**——小块负责精准命中，大块负责提供完整上下文。

这是 RAG（Retrieval-Augmented Generation，检索增强生成）里非常实用的一种策略。它解决一个核心矛盾：**切得小，检索准但上下文残缺；切得大，上下文全但检索糊**。父文档检索用一个“双层结构”同时拿到两边的好处。

---

## 1. 为什么需要它：RAG 的“切块困境”

RAG 的基本流程是：把文档切成块（chunk）→ 向量化存入向量库 → 用户提问时检索最相似的块 → 把块塞进提示词让大模型回答。

问题出在“切块”这一步：

- **块太小**（如 100 字）：语义集中，向量检索（vector search）很准，但可能只截到半句话，模型看不懂。
- **块太大**（如 2000 字）：上下文完整，但向量是把整块压成一个点，主题被稀释，检索变得模糊，容易“找错”。

**父文档检索的思路**：把文档切成**小片（child chunk）**用于检索，同时记录每个小片属于哪个**大块（parent chunk）**。检索时命中小片，但返回给模型的是它所属的大块。

```python
# 直觉演示：小块检索准，大块上下文全
child_chunks = ["退换货政策规定：", "自签收之日起 7 天内"]   # 小块，检索精准
parent_chunk = "退换货政策规定：自签收之日起 7 天内可无理由退货，需保留吊牌。"  # 大块，语义完整

# 用户问"几天内可以退货"，命中的是小块 "自签收之日起 7 天内"
# 但真正喂给模型的是 parent_chunk，信息完整
print("命中块:", child_chunks[1])
print("返回给模型:", parent_chunk)
```

---

## 2. 双层结构：子块（Child）与父块（Parent）

核心就是维护一个**映射关系**：每个子块知道自己属于哪个父块。

常见做法是“**父子同时切**”：

1. 先按较大粒度切出**父块**（比如按段落，每段 1000 字）。
2. 每个父块内部再按较小粒度切出**子块**（比如每句或每 200 字）。
3. 子块向量化入库，元数据（metadata）里存 `parent_id`。
4. 父块按 `parent_id` 存到字典或数据库里。

```python
# 最小可用实现：手动构建父子两层结构

document = (
    "公司报销制度：员工出差产生的交通费可报销。"
    "报销需在返回后 30 天内提交发票。"
    "住宿费标准为每晚不超过 500 元，超标部分自理。"
)

# 父块：按段落/主题切（这里简化为一整段）
parent_id = "p1"
parent_store = {parent_id: document}

# 子块：细粒度切分，并记录 parent_id
child_chunks = [
    {"id": "c1", "text": "员工出差产生的交通费可报销", "parent_id": parent_id},
    {"id": "c2", "text": "报销需在返回后 30 天内提交发票", "parent_id": parent_id},
    {"id": "c3", "text": "住宿费每晚不超过 500 元", "parent_id": parent_id},
]

print("子块数:", len(child_chunks))
print("父块存储:", parent_store)
```

> **关键结论**：子块是“检索的钩子”，父块是“回答的燃料”。两者用 `parent_id` 绑定。

---

## 3. 检索流程：命中子块，返回父块

一次完整的父文档检索有三个角色：

- **向量库**：只存子块的向量和文本，附带 `parent_id`。
- **父块存储（parent store）**：`parent_id -> 完整父块文本`，可以是 dict、SQLite 或专门的 Document Store。
- **检索器（retriever）**：先按向量相似度找子块，再用 `parent_id` 查出父块，去重后返回。

```python
# 用一个假的“向量相似度”演示检索流程
import math

def fake_embed(text):
    """伪向量：用字符编码和长度拼一个长度3的向量，仅供教学演示。"""
    return [len(text), sum(map(ord, text)) % 97, text.count("报")]

def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb + 1e-9)

# 建库：只存子块
child_chunks_with_vec = [(c, fake_embed(c["text"])) for c in child_chunks]

# 查询
query = "出差回来多久内要交发票"
q_vec = fake_embed(query)

# 1) 找最相似的子块
scored = sorted(
    child_chunks_with_vec,
    key=lambda item: cosine(q_vec, item[1]),
    reverse=True,
)
best_child = scored[0][0]
print("命中的子块:", best_child["text"])

# 2) 用 parent_id 取回父块
final_context = parent_store[best_child["parent_id"]]
print("最终喂给模型的上下文:", final_context)
```

> **关键结论**：检索只在子块层进行，返回给 LLM 的是父块，父块可以包含多个子块的信息。

---

## 4. 去重与顺序：同一父块只返回一次

一次查询可能命中同一父块的多个子块。如果不去重，你会把同一个父块重复塞进上下文，浪费 token 甚至让模型困惑。

正确处理：**按 `parent_id` 去重，保留得分最高的那个子块的排序位置**。

```python
# 查询命中了 p1 下的多个子块，需要去重
fake_results = [
    {"child": "c2", "parent_id": "p1", "score": 0.9},
    {"child": "c3", "parent_id": "p1", "score": 0.8},
    {"child": "c1", "parent_id": "p1", "score": 0.7},
]

seen = set()
deduped = []
for r in fake_results:  # 已按 score 从高到低排好
    if r["parent_id"] not in seen:
        seen.add(r["parent_id"])
        deduped.append(r)

print("去重后结果:", deduped)
# 只保留 p1 一条，避免重复上下文
```

> **关键结论**：父文档检索的“返回单位”是父块，不是子块。去重是必做步骤。

---

## 5. 工程落地：用 LangChain 的 ParentDocumentRetriever

实际工程里不需要从零写，LangChain 提供了开箱即用的 `ParentDocumentRetriever`（父文档检索器）。它内部帮你管理“子块向量库 + 父块存储”两层。

```python
# 需要安装: pip install langchain langchain-community langchain-openai chromadb
# 本示例展示标准用法，运行需配置 OPENAI_API_KEY

from langchain.retrievers import ParentDocumentRetriever
from langchain.storage import InMemoryStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings

# 父块切分器：大粒度
parent_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
# 子块切分器：小粒度
child_splitter = RecursiveCharacterTextSplitter(chunk_size=200, chunk_overlap=20)

# 向量库存子块，InMemoryStore 存父块
vectorstore = Chroma(collection_name="children", embedding_function=OpenAIEmbeddings())
store = InMemoryStore()

retriever = ParentDocumentRetriever(
    vectorstore=vectorstore,
    docstore=store,
    child_splitter=child_splitter,
    parent_splitter=parent_splitter,
)

# 索引文档
texts = ["这里放你的长文档内容……" * 50]
retriever.add_documents([__import__("langchain_core.documents", fromlist=["Document"]).Document(page_content=t) for t in texts])

# 检索：输入问题，返回父块
query = "你的问题"
docs = retriever.invoke(query)
print("返回的父块数量:", len(docs))
print("第一个父块内容长度:", len(docs[0].page_content))
```

> **关键结论**：生产环境用 `ParentDocumentRetriever`，你只需提供两个切分器和两个存储，剩下交给框架。

---

## 动手练习

**任务**：在本地实现一个“迷你父文档检索器”，不使用任何框架。

要求：
1. 准备一段至少 300 字的中文文档（可以用你熟悉的产品说明或课程笔记）。
2. 把文档按句号切成**父块**（每段一个父块），再把每个父块按逗号切成**子块**。
3. 用 `sentence-transformers` 的 `all-MiniLM-L6-v2` 或任意 embedding 模型，把子块向量化并存入一个简单的列表。
4. 实现 `search(query)`：计算 query 向量与所有子块的余弦相似度，找到最相似的子块，返回其 `parent_id` 对应的父块。
5. 打印：命中子块、返回的父块、以及去重后返回的父块列表。

**验收标准**：
- 问一个只出现在某个子块里的细节问题，能返回包含完整上下文的父块。
- 如果多个子块命中同一父块，最终只返回一次。

**提示**：可以用 `numpy` 做向量运算，`sklearn.metrics.pairwise.cosine_similarity` 计算相似度。


---

## 本课题目

### single_choice · None



- [A] 候选文档数量过多且排序无法统一，需要额外的融合策略
- [B] BM25 结果会被向量结果覆盖，导致关键词信息丢失
- [C] 向量检索无法处理数值型查询，会返回空结果
- [D] 并集操作会触发维度不匹配异常

**参考答案**：0

**解析**：Hybrid 检索的核心难点之一就是两路召回结果需要融合（如 RRF、加权求和）来统一排序；简单并集会导致候选膨胀且缺乏统一打分。

### single_choice · None



- [A] 稀疏检索擅长精确关键词匹配，稠密检索擅长语义相似，二者结合可提升召回覆盖面
- [B] 稠密检索一定优于稀疏检索，混合使用只是历史遗留
- [C] 稀疏检索只能处理短查询，稠密检索只能处理长文档
- [D] 二者使用相同的向量空间，所以结果必然一致

**参考答案**：0

**解析**：稀疏检索（如 BM25、TF-IDF）对精确词项匹配敏感，稠密检索（如嵌入向量）对语义泛化更强，二者互补是 Hybrid 检索的动机。

### single_choice · None



- [A] Hybrid 负责扩大召回，rerank 可对融合后的候选做更精细的排序
- [B] rerank 会替代 Hybrid，使混合检索变得多余
- [C] Hybrid 和 rerank 必须使用同一个模型
- [D] rerank 只能用于向量检索结果

**参考答案**：0

**解析**：Hybrid 提升召回覆盖面，rerank（如交叉编码器）在候选集上做精细打分，二者常配合使用；rerank 并不排斥 Hybrid。

### single_choice · None



- [A] 融合时向量路的权重或分数尺度占了主导
- [B] BM25 索引未构建成功，完全没有结果
- [C] 向量检索返回了空列表
- [D] 文档被去重时误删了 BM25 的结果

**参考答案**：0

**解析**：若向量路权重过大或分数量级更大，融合后向量结果会排到前面；需要检查权重、归一化或改用 RRF。

### single_choice · None



- [A] 两路贡献相加，通常比只在单路出现的文档得分更高
- [B] 只取向量一路的得分，忽略 BM25 的贡献
- [C] 只取 BM25 一路的得分，忽略向量的贡献
- [D] 因重复出现而被判为无效文档

**参考答案**：0

**解析**：RRF 对同一文档在两路中的贡献求和，因此被两路同时命中的文档往往获得更高融合分，这是 Hybrid 的常见优势。

### single_choice · None



- [A] BM25 + 向量检索
- [B] 稀疏向量 + 稠密向量
- [C] 关键词检索 + 语义检索
- [D] 监督微调 + 强化学习

**参考答案**：3

**解析**：Hybrid 检索指稀疏/关键词类检索与稠密/语义类检索的组合；监督微调与强化学习属于模型训练范式，不是检索融合方式。

### single_choice · None



- [A] 稀疏检索能精确匹配该型号词项，避免被语义近邻淹没
- [B] 向量检索无法编码任何字符
- [C] 稀疏检索能理解型号的语义含义
- [D] Hybrid 检索会自动忽略专有名词

**参考答案**：0

**解析**：专有名词、型号、代码等 OOV 或低频词项在稀疏检索中可精确匹配，弥补稠密向量对罕见词表征不足的问题。

### single_choice · None



- [A] 归一化依赖当前结果集的最小/最大值，不同查询间分数不可直接比较
- [B] 归一化后所有分数都会变成 0
- [C] min-max 只能用于 BM25，不能用于向量分数
- [D] 归一化会改变文档的排序，因此不能用于融合

**参考答案**：0

**解析**：min-max 归一化是查询内相对的，其最小/最大值随结果集变化，因此不同查询的归一化分数不可直接横向比较，但在同一查询内融合是可行的。

### single_choice · None



- [A] 检查召回文档是否被正确截断、去重并传入生成上下文
- [B] Hybrid 检索一定降低了精确率，应立刻移除
- [C] 生成模型无法处理多路召回结果
- [D] 向量索引与 BM25 索引不能共存

**参考答案**：0

**解析**：召回率提升不等于答案质量提升；可能问题在候选截断、去重、上下文拼接或生成阶段，需逐段排查，而不是直接否定 Hybrid。

### single_choice · None



- [A] 应基于验证集评估不同 α 下的检索指标，而非凭直觉固定
- [B] α 越大越好，因为关键词匹配最可靠
- [C] α 只能取 0 或 1
- [D] α 与检索效果无关，可随意设置

**参考答案**：0

**解析**：权重应按数据与任务在验证集上调优；固定偏好某一端或认为权重无关都不合理。

### single_choice · None



- [A] 精确匹配错误码「E-1042」
- [B] 理解「我想取消订阅」与「如何退订」的同义关系
- [C] 跨语言语义检索
- [D] 识别图像中的文字

**参考答案**：0

**解析**：错误码、型号、ID 等精确词项适合稀疏检索；同义改写、跨语言语义更适合稠密检索；图像文字属于 OCR 范畴。

### single_choice · None



- [A] 没有利用文档在两路中的排名深度与重复命中信息，排序可能次优
- [B] 交替合并会导致内存溢出
- [C] BM25 与向量检索不能同时使用
- [D] 交替合并只适用于同一种检索器

**参考答案**：0

**解析**：简单交替忽略了两路排名的相对可信度以及同一文档在双路重复出现带来的增益，RRF 等融合方法能更合理地综合这些信号。

### single_choice · None



- [A] 各文档在两路结果中的排名位置
- [B] 各文档的原始相似度分数绝对值
- [C] 各文档的长度
- [D] 各文档被检索到的先后顺序（时间戳）

**参考答案**：0

**解析**：RRF 使用 1/(k + rank) 形式的公式，只依赖排名而不依赖原始分数的量纲，因此能规避不同检索器分数量纲不一致的问题。

### single_choice · None



- [A] 系统更偏向关键词匹配，对同义改写的查询召回下降
- [B] 系统完全退化为纯向量检索
- [C] 归一化会失效导致数值溢出
- [D] 两路结果无法合并而报错

**参考答案**：0

**解析**：α 越大，BM25 权重越高，系统更依赖精确词项匹配，对语义改写、同义表达的鲁棒性下降；α 过小则相反。

### single_choice · None



- [A] BM25 分数因数值量级大而主导最终排序
- [B] 向量分数会覆盖 BM25 分数
- [C] 相加后分数会变成负数
- [D] 两路结果会因类型不同抛出异常

**参考答案**：0

**解析**：不同检索器的分数尺度和分布不同，直接相加会让数值范围大的那一路主导，因此通常需要归一化或用 RRF 这类基于排名的融合。

### single_choice · None



- [A] 同一文档可能被两路检索同时召回，需要合并为一条并合理处理其分数
- [B] 去重只能删除 BM25 的结果，保留向量结果
- [C] 两路检索结果天然不会重复，无需去重
- [D] 去重会破坏向量索引，应避免使用

**参考答案**：0

**解析**：Hybrid 检索中同一文档常被两路同时命中，需要在融合阶段按文档 ID 合并，并决定是取最大分、求和还是用 RRF 等方式综合。

### single_choice · None



- [A] 在生成答案之前，作为召回阶段的一部分
- [B] 在生成答案之后，用于校验答案
- [C] 在用户输入之前，用于预处理查询
- [D] 在模型训练阶段，用于构造损失函数

**参考答案**：0

**解析**：Hybrid 检索属于 RAG 的召回阶段，位于生成之前；其输出作为上下文交给生成模型。

### single_choice · None



- [A] 同时覆盖精确词项与语义改写，提升召回率
- [B] 保证返回结果一定与查询完全相关
- [C] 完全消除生成模型产生幻觉的可能
- [D] 减少索引构建时间

**参考答案**：0

**解析**：Hybrid 的价值在于召回阶段兼顾关键词精确匹配和语义泛化，提高相关文档被召回的几率；但并不能保证绝对相关，也不能消除幻觉。

### single_choice · None



- [A] 平滑排名靠前文档与靠后文档的分数差距
- [B] 控制返回文档的总数
- [C] 决定使用 BM25 还是向量检索
- [D] 设置向量维度

**参考答案**：0

**解析**：RRF 中 k 用于平滑，k 越大排名差异带来的分数差异越小；它不控制返回数量，也不决定检索器类型或向量维度。

### single_choice · None



- [A] 融合结果仍然偏向向量分数，因为两路尺度未对齐
- [B] 融合结果完全等于 BM25 结果
- [C] 向量检索会抛异常
- [D] 归一化会改变文档内容

**参考答案**：0

**解析**：融合要求两路分数尺度可比；只归一化一路，另一路仍可能主导，因此通常需要对两路都做归一化或改用基于排名的融合。

### single_choice · None



- [A] 只对父文档做向量化，子块仅用于展示
- [B] 先用小块（子块）做精准检索，再返回该子块所属的更大父文档（或父块）作为上下文
- [C] 把父文档和子块拼接成同一个向量放入索引
- [D] 检索时把整篇原始文档直接送入大模型，不做任何切分

**参考答案**：1

**解析**：父文档检索的经典做法是"小块检索、大块返回"：用粒度小的子块提高检索命中精度，再把子块对应的父块/父文档作为上下文返回，让模型获得更完整的语义背景。A 颠倒了子父关系；C 混淆了向量化对象；D 没有利用子块的精准检索优势。

### single_choice · None



- [A] 子块向量的 L2 范数值
- [B] 子块的字符长度与创建时间
- [C] 子块到其所属父块（或父文档）的标识符映射
- [D] 子块在大模型中的注意力权重

**参考答案**：2

**解析**：检索命中的是子块，而返回的是父块，因此必须建立"子块 -> 父块标识"的映射（如父块 ID 或文档 ID + 位置）。向量范数、长度、时间都不足以定位父块；注意力权重是模型内部量，与检索映射无关。

### single_choice · None



- [A] 索引时只需存子块，内存开销比普通检索更小
- [B] 检索时返回更大块，通常会增大送入大模型的上下文长度，从而增加推理开销
- [C] 父文档检索完全消除了向量相似度计算的开销
- [D] 它不会增加任何存储，因为父块就是原始文件

**参考答案**：1

**解析**：父文档检索以更大的父块作为上下文，token 数增加，推理成本随之上升；同时映射关系和父块内容会带来额外存储。A、D 低估开销，C 否认了检索阶段的向量计算。

### multi_choice · None



- [A] 需要建立子块到父块的映射关系，检索到子块后据此取回父块
- [B] 子块用于提高检索精度，父块用于为模型提供更完整的上下文
- [C] 可以用同一嵌入模型对子块向量化，也可以对父块单独向量化
- [D] 父块必须和子块使用完全相同的文本内容和长度
- [E] 父文档检索必须在检索阶段改用关键词匹配而非向量检索

**参考答案**：[0, 1, 2]

**解析**：A 是映射机制，B 是核心分工，C 描述了允许的实现方式（对子块索引、父块仅作返回是常见做法，也可对父块另行向量化）。D 错误，父子内容与长度本就不同；E 错误，向量检索仍是主要手段之一，并非必须改关键词。

### multi_choice · None



- [A] 回答常因缺少前后文而出现指代不清（如"它""该方法"指代对象丢失）
- [B] 答案需要综合同一章节多处信息，但每次只检索到零散片段
- [C] 检索到的句子本身正确，但拼接后语义不连贯
- [D] 向量数据库中没有任何子块被检索到
- [E] 嵌入模型无法处理中文文本

**参考答案**：[0, 1, 2]

**解析**：A、B、C 都是上下文被小块切碎导致的典型症状，返回父块可改善。D 是完全检索失败，与父子块设计无关；E 属于模型能力问题，父文档检索不能解决。

### multi_choice · None



- [A] 切分策略或分块参数变更时，重建子块与父块索引及映射
- [B] 为每个父块分配稳定且唯一的标识符
- [C] 在父块内容更新后，同步更新或重建其子块向量
- [D] 把父块 ID 用随机数生成，每次查询时重新分配
- [E] 只在首次建库时写入映射，之后不再更新

**参考答案**：[0, 1, 2]

**解析**：切分变更需重建、父块需稳定唯一 ID、父块更新要同步子块向量，这三者保证映射可靠。随机且每次重分配的 ID 会破坏一致性；只建一次不更新会在数据变更后失效。

### multi_choice · None



- [A] 两者都体现"小块精准检索、扩大返回上下文"的思想
- [B] 句子窗口检索返回命中句前后固定窗口，父文档检索返回所属父块，粒度来源不同
- [C] 父文档检索的上下文单元由预先的分块结构决定，而非命中位置动态决定
- [D] 两者都完全不需要向量检索
- [E] 父文档检索一定比句子窗口检索效果更好，无需比较

**参考答案**：[0, 1, 2]

**解析**：它们共享"小检大返"思路，但上下文单元来源不同：句子窗口按命中位置动态取窗口，父文档检索按预设分块取整块。D 否认了向量检索，错误；E 过于绝对，效果需按数据实测。

### fill_blank · None



**参考答案**：["精度/准确率/命中率, 父块/父文档", "精度 父块", "准确率 父文档"]

**解析**：前半句强调小块带来的检索精度（准确率、命中率），后半句是返回更大的父块/父文档提供上下文。这是父文档检索的核心机制表述。

### fill_blank · None



**参考答案**：["映射", "标识符映射", "ID映射", "映射关系"]

**解析**：子块与父块之间需要映射关系（如父块 ID），否则无法由命中的子块定位回父块。这是父文档检索的关键数据设计。

### code_reading · None



**参考答案**：它把检索命中的子块 ID 通过 child_to_parent 映射转换为父块 ID，并对父块去重，最后从 parent_store 取出父块内容返回；核心是"子块命中 -> 父块返回"的转换与去重。

**解析**：这段伪代码体现了父文档检索的关键步骤：用映射把子块命中转换为父块标识，去重后从父块存储取回内容供大模型使用。识别出映射转换与去重两点即可。

### code_reading · None



**参考答案**：意图是把命中的子块替换为其所属父块并去重，以获得更完整上下文；代价是返回的上下文变长，token 与推理开销增加，且可能引入父块中不相关的部分。

**解析**：代码显示了"子块命中 -> 按 parent_id 取父块 -> 去重"的父文档检索返回逻辑，同时要指出父块更大带来的上下文膨胀与无关内容风险，这是权衡的另一面。

### scenario · None



**参考答案**：思路：用较小的子块（如句子或小段落）建立向量索引以保证检索精度，同时按更粗的粒度（如小节/章节）生成父块；为每个子块保存其父块 ID，检索命中后经映射取回父块并去重，作为上下文交给模型。关键点包括：父子结构要稳定（父子 ID 唯一、可重建）、注意返回父块后上下文变长带来的 token 与推理开销、父块可能含无关内容需做筛选或截断、文档更新或切分参数变化时要同步重建映射与向量。

**解析**：场景聚焦于小块导致上下文丢失，需要"小块检索 + 返回父块"；同时要覆盖映射一致性、文档更新后重建、以及返回父块带来的上下文长度与成本等工程注意点。

### single_choice · None



- [A] 显著减少向量数据库的存储占用
- [B] 提高检索阶段向量相似度计算的精度
- [C] 让回答获得更完整连贯的上下文，降低因上下文被截断而答偏的概率
- [D] 减少需要送入大模型的 token 数量

**参考答案**：2

**解析**：父文档检索的收益在于上下文完整性。小块检索精准但上下文可能被切断，返回父块能补全语义，让模型基于连贯上下文作答。它通常会增加送入模型的 token 和存储，因此 A、D 方向相反；检索相似度计算本身仍基于子块，B 不成立。

### scenario · None



**参考答案**：排查方向：确认返回的父块是否过大（可统计返回上下文的 token 分布）、是否因多个子块命中同一父块而重复返回、是否存在父块粒度粗导致大量无关内容混入。优化建议：适当缩小父块粒度或对父块做相关性裁剪/截断；对命中父块去重；控制返回父块数量并做排序；在返回父块时标注命中子块位置以引导模型聚焦。理由是父块越大上下文越完整但噪声与开销越高，需要在完整性和成本之间权衡。

**解析**：题目考察对父文档检索代价的工程权衡：延迟与费用上升通常来自上下文膨胀和重复，无关内容来自父块过粗。应围绕父块粒度、去重、截断、排序与高亮给出可操作建议。

### single_choice · None



- [A] 子块应尽可能小（例如几个词），这样检索最准，父块大小无关紧要
- [B] 子块应和父块完全相同，这样实现最简单
- [C] 子块切分需要在检索精度与查找定位能力之间权衡，父块则用于提供上下文
- [D] 子块大小必须固定为 512 个 token，否则父块无法映射

**参考答案**：2

**解析**：子块越小，语义越集中、越易命中具体信息点，但过小会丢失定位所需语境；父块提供上下文。因此是精度与语义完整性的权衡。A、B 都走极端，D 编造了固定值约束。

### single_choice · None



- [A] 文档极短，每篇只有一两句话
- [B] 查询需要唯一定位到某个具体句子，且答案只在该句内
- [C] 问题需要跨段落、跨章节整合多处信息，单一块会丢失前后文
- [D] 向量数据库无法存储任何元数据

**参考答案**：2

**解析**：当问题需要跨块整合、依赖前后文时，小块容易丢失语境，父文档检索能返回更完整的上下文。A、B 场景下小块已足够，收益不大；D 与是否用父文档检索无关，且父文档映射本身依赖元数据。

### single_choice · None



- [A] 一个父块只能对应一个子块，二者一一对应
- [B] 一个父块可以包含多个子块，多个子块共享同一个父块标识
- [C] 子块必须先于父块创建，且父块内容完全由子块拼接而成
- [D] 父块和子块必须使用不同的向量模型

**参考答案**：1

**解析**：父块是比子块更大的整体，通常包含多个子块，这些子块共享同一父块 ID。A 忽略了一对多本质；C 的先后顺序不是关键，父子是逻辑嵌套；D 编造了模型约束，系统通常用同一嵌入模型。

### single_choice · None



- [A] 把同一个父块重复返回多次，增强权重
- [B] 对命中的父块做去重，只返回一份，避免上下文冗余
- [C] 丢弃所有命中子块，改为随机返回一个父块
- [D] 只返回首个命中的子块原文，不返回父块

**参考答案**：1

**解析**：多个子块命中同一父块时，父块内容会高度重复，去重可避免上下文冗余、浪费 token 并干扰模型。重复返回不会"加权"，反而造成噪声；C、D 都不符合父文档检索的设计意图。

### single_choice · None



- [A] 嵌入模型维度不匹配
- [B] 父子映射与实际分块数据不一致，属于数据一致性维护问题
- [C] 大模型温度参数设置过高
- [D] 向量数据库索引类型选择错误

**参考答案**：1

**解析**：重新切分后子块与父块的对应关系会变化，若映射未同步重建，就会指向错误内容，本质是父子映射的数据一致性问题。A、C、D 与该现象无关，属于误判根因。

### single_choice · None



- [A] 完全不需要向量数据库
- [B] 在提供足够上下文的同时，避免无关内容大量占用上下文窗口
- [C] 可以跳过嵌入计算，提升索引速度
- [D] 保证大模型不会产生幻觉

**参考答案**：1

**解析**：父块是按内容切分的较大单元，既保留相关上下文又比整篇文档更聚焦，能减少无关内容占用窗口。它仍然依赖向量库与嵌入；返回父块也不能保证零幻觉，只是改善依据质量。

### single_choice · None



- [A] 只能返回父块，绝不能同时返回命中的子块
- [B] 返回父块的同时，可附带命中的子块位置或高亮信息，帮助模型聚焦相关内容
- [C] 必须返回父块的所有子块且都排在上下文最前面
- [D] 返回内容与普通检索完全相同，父文档检索只影响索引阶段

**参考答案**：1

**解析**：常见增强做法是在返回父块时标注或高亮命中的子块位置，让模型既看到完整上下文又聚焦关键处。A 过于绝对；C 会导致冗余与排序问题；D 混淆了索引与检索返回两阶段的差异。
