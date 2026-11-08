# s7u2l2 向量嵌入选择：Agent 的 RAG 起点 / agent.rag.rerank 教学讲义

> 来源 `content/lessons/s7u2l2.json`

## agent.rag.embedding_choice

# 向量嵌入选择：Agent 的 RAG 起点

## 一句话直觉

在 RAG（Retrieval-Augmented Generation，检索增强生成）里，**嵌入模型（Embedding Model）决定了“找得准不准”**——如果嵌入模型把你的问题映射到错误的语义区域，后面的大模型再强也救不回来。

因此 `embedding_choice` 要解决的核心问题是：**面对一个具体 Agent 场景，如何从众多嵌入模型里选出一个，既语义匹配业务，又能在延迟、成本、部署条件上落地。**

下面用 5 个小节循序渐进。

---

## 1. 嵌入模型到底在干什么？

嵌入模型把文本（一段话、一个句子、一个词）映射成一个**高维稠密向量**（dense vector），比如 384、768、1024、1536 维。语义相近的文本，向量夹角小；语义不相关的，夹角大。

**关键结论：嵌入模型不是“理解”文本，它只是把文本放在一个几何空间里，距离约等于语义相似度。**

```python
# 用一个最简单的句子向量示例，说明“语义近 = 向量近”
from sentence_transformers import SentenceTransformer
import numpy as np

model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

sentences = [
    "如何申请退款",
    "退款流程是什么",
    "今天天气真好",
]

# 把三句话转成 384 维向量
embeddings = model.encode(sentences, normalize_embeddings=True)

# 计算余弦相似度（cosine similarity），越接近 1 越相似
sim_01 = float(np.dot(embeddings[0], embeddings[1]))
sim_02 = float(np.dot(embeddings[0], embeddings[2]))

print(f"退款 vs 退款流程: {sim_01:.4f}")  # 应该明显更高
print(f"退款 vs 天气:     {sim_02:.4f}")
```

运行后你会看到第一组相似度接近 0.7~0.9，第二组接近 0~0.2。这就是嵌入模型的基本价值。

---

## 2. 选择嵌入模型时要看的 6 个维度

工程上选型不是“谁榜单分高就用谁”，而是要看下面 6 个维度：

| 维度 | 英文 | 说明 |
|---|---|---|
| 语义质量 | Semantic Quality | MTEB、BEIR 等榜单，业务数据上的召回率 |
| 向量维度 | Dimension | 维度越高，通常表达力强，但存储和检索成本上升 |
| 最大输入长度 | Max Sequence Length | 常见 128、256、512、8192 tokens，决定能否直接嵌入长文档 |
| 多语言能力 | Multilingual | 是否支持中英混合、跨语言检索 |
| 部署方式 | Deployment | API（Application Programming Interface）调用还是本地推理 |
| 成本与延迟 | Cost & Latency | 每百万 token 价格、P99 响应时间、GPU 占用 |

**关键结论：没有“最好”的嵌入模型，只有“在这个业务 + 这个部署条件下最合适”的嵌入模型。**

```python
# 用一句话说明“长文本截断”问题：模型只保留前 N 个 token
from transformers import AutoTokenizer

tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")

text = "这是一段很长的文档。" * 200  # 模拟长文档
tokens = tokenizer(text, truncation=True, max_length=256, return_tensors="pt")

print("原始 token 数:", len(tokenizer(text)["input_ids"]))
print("截断后 token 数:", tokens["input_ids"].shape[1])
# 如果原始长度 > 256，模型只看前 256 个 token，后面的信息直接丢失
```

如果你的文档很长，而模型 max length 只有 256，就必须先做**分块（chunking）**，否则后面的内容根本不会被检索到。

---

## 3. 主流嵌入模型分类与代表

当前工程上常见三类：

1. **API 类**：OpenAI `text-embedding-3-small/large`、Cohere `embed-v3`、Voyage `voyage-3`。优点是开箱即用、质量稳定；缺点是要联网、按量付费、数据出域。
2. **开源本地类**：`BAAI/bge-m3`、`intfloat/multilingual-e5-large`、`sentence-transformers/all-MiniLM-L6-v2`、`nomic-embed-text`。优点是免费、可私有化；缺点是要自己维护推理服务。
3. **领域微调类**：在通用模型基础上，用你的业务数据（query-doc pair）做对比学习微调。优点是最贴合业务；缺点是需要标注数据和训练成本。

**关键结论：先用 API 或强开源模型快速跑通，等到业务数据积累到一定量，再考虑领域微调。**

```python
# 用同一段文本对比两种模型输出的维度差异
from sentence_transformers import SentenceTransformer

models = [
    "sentence-transformers/all-MiniLM-L6-v2",  # 轻量，384 维，英文强
    "BAAI/bge-small-zh-v1.5",                   # 中文场景常用，512 维
]

text = "RAG 系统的检索质量很大程度取决于嵌入模型"

for name in models:
    m = SentenceTransformer(name)
    vec = m.encode([text])
    print(f"{name} -> shape={vec.shape}, dtype={vec.dtype}")
```

你会看到不同模型输出的维度不同。**一旦选定模型，向量数据库里的维度就固定了，换模型通常要重建索引。**

---

## 4. 如何做一次可解释的选型评估

不要凭感觉选。最小可行评估流程如下：

1. 准备 **20~100 条** 业务 query 和对应正确答案（query -> relevant doc id）。
2. 对每个候选模型，把文档库全部嵌入，建临时索引。
3. 对每个 query 做 top-k 检索。
4. 计算 **Recall@k**、**MRR（Mean Reciprocal Rank）**、**nDCG（Normalized Discounted Cumulative Gain）**。
5. 同时记录平均延迟和费用。

**关键结论：用业务数据上的召回指标 + 延迟 + 成本三者共同决策，而不是只看 MTEB 榜单。**

```python
# 一个极简的嵌入模型评估骨架：计算 Recall@k
import numpy as np
from sentence_transformers import SentenceTransformer

# 模拟业务数据
docs = [
    "退款需要 3-5 个工作日到账",
    "如何修改绑定手机号",
    "订单取消后优惠券会退回",
    "发票申请入口在订单详情页",
]
queries = ["退款多久到账", "手机号怎么改"]
ground_truth = [0, 1]  # 每个 query 对应正确文档的下标

model = SentenceTransformer("BAAI/bge-small-zh-v1.5")
doc_vecs = model.encode(docs, normalize_embeddings=True)
query_vecs = model.encode(queries, normalize_embeddings=True)

k = 2
for i, qv in enumerate(query_vecs):
    scores = doc_vecs @ qv                 # 余弦相似度（已归一化）
    topk = np.argsort(-scores)[:k]         # 取分数最高的 k 个
    hit = ground_truth[i] in topk
    print(f"Query: {queries[i]} | Top-{k}: {topk.tolist()} | 命中: {hit}")
```

把 `model` 换成不同候选，跑同一份数据，就能横向对比。

---

## 5. 在 Agent 里的落地建议

Agent 场景和普通问答不同：

- **多轮对话**：query 往往很短、有指代，需要先做 query rewrite 或拼接上下文再嵌入。
- **工具调用**：Agent 可能用嵌入做“工具选择”，此时嵌入的是工具描述，要保证工具描述清晰且彼此可区分。
- **混合检索**：单靠稠密向量对专有名词、ID、代码不敏感，常用 **混合检索（Hybrid Retrieval）** = 稠密向量 + BM25 稀疏检索。
- **重排序**：先嵌入召回 top-50，再用 **交叉编码器（Cross-Encoder，reranker）** 精排 top-5，质量通常显著提升。

**关键结论：嵌入模型只是检索链路的第一环，Agent 工程中要把它和分块、混合检索、重排序一起设计。**

```python
# 用句子长度分布判断 chunk 大小是否和模型 max length 匹配
import numpy as np
from transformers import AutoTokenizer

tokenizer = AutoTokenizer.from_pretrained("BAAI/bge-small-zh-v1.5")
chunks = ["这是第一个分块的内容。" * 3, "这是第二个分块。" * 20, "短分块"]

lengths = [len(tokenizer(c)["input_ids"]) for c in chunks]
print("各分块 token 长度:", lengths)
print("最大长度:", max(lengths), "| 模型上限通常 512")
# 若最大长度接近或超过模型上限，需要缩小 chunk size 或换长文本模型
```

---

## 动手练习

**任务：为你的业务场景做一次嵌入模型小型对比实验。**

1. 准备 10 条中文 query，每条对应 1 个正确答案，另外准备 30 条无关干扰文档，组成 40 条文档库。
2. 选 2 个候选模型：
   - `BAAI/bge-small-zh-v1.5`（本地开源）
   - 任意一个 API 嵌入模型（如 OpenAI `text-embedding-3-small`）
3. 分别嵌入文档库，对 10 条 query 做 top-3 检索。
4. 输出一张表：模型名 | Recall@3 | 平均延迟(ms) | 预估成本。
5. 写 3 句话结论：哪个更合适你的场景，为什么。

**提交物**：`eval_embedding.py` + 一张结果表 + 结论。

完成这个练习，你就掌握了 `embedding_choice` 的完整工程闭环。

## agent.rag.rerank

# agent.rag.rerank 教学讲义

> **一句话直觉**：在 RAG（Retrieval-Augmented Generation，检索增强生成）里，第一轮检索为了“快”会召回一堆候选，但顺序往往不够准；rerank（重排序）就是用一个更聪明、更慢的模型，把这堆候选重新排好，让真正有用的资料排到最前面，喂给大模型。

---

## 0. 为什么要学 rerank？

RAG 的基本流程是：

1. 用户提问 → 2. 从知识库检索相关文档 → 3. 把文档塞进大模型上下文 → 4. 生成答案。

问题在于第 2 步：

- 向量检索（vector search）基于 embedding（嵌入向量）相似度，速度快，但它是“粗筛”。
- 它可能把语义相近但实际没用的内容排前面。
- 也可能把真正关键的证据排在 8、9、10 名，被后续截断丢掉。

**rerank 的价值**：用 cross-encoder（交叉编码器）或更强的排序模型，对“问题 + 每个候选文档”成对打分，重新排序。它比向量相似度更准，但更慢，所以只对少量候选做。

一句话：**先召回 50 个，再 rerank 出 5 个，效果通常远好于直接召回 5 个。**

---

## 1. 第一层：RAG 检索为什么需要两阶段？

RAG 检索通常分两阶段：

- **召回阶段（retrieval）**：从百万文档中快速找出 Top-K 候选。常用向量检索、BM25。
- **重排阶段（rerank）**：对 Top-K 候选精细排序，选出 Top-N 给大模型。

为什么不能一步到位？

- 向量检索是双编码器（bi-encoder）：问题和文档分别编码，再算余弦相似度。快，但交互不充分。
- Cross-encoder 把问题和文档拼在一起送进模型，能捕捉细粒度交互，准，但无法预先建索引，必须逐个候选计算。

所以工程上采用“粗召回 + 精排序”。

```python
# 模拟两阶段检索的直观对比
# 假设有 5 个候选文档，向量分数和 rerank 分数不同

candidates = [
    {"id": "doc1", "text": "Python 是一种编程语言", "vector_score": 0.91},
    {"id": "doc2", "text": "Python 蛇的习性介绍", "vector_score": 0.89},
    {"id": "doc3", "text": "如何安装 Python 解释器", "vector_score": 0.85},
    {"id": "doc4", "text": "Python 在数据科学中的应用", "vector_score": 0.84},
    {"id": "doc5", "text": "Python 编程入门教程", "vector_score": 0.83},
]

query = "我想学 Python 编程，应该怎么开始？"

# 假设 rerank 模型给出的相关性分数
rerank_scores = {
    "doc1": 0.55,
    "doc2": 0.10,
    "doc3": 0.78,
    "doc4": 0.70,
    "doc5": 0.95,
}

# 按向量分数排序
vector_ranked = sorted(candidates, key=lambda x: x["vector_score"], reverse=True)
print("向量排序:", [d["id"] for d in vector_ranked])

# 按 rerank 分数排序
rerank_ranked = sorted(candidates, key=lambda x: rerank_scores[x["id"]], reverse=True)
print("Rerank 排序:", [d["id"] for d in rerank_ranked])
```

你会看到：向量排序把“Python 蛇”排得很高，但 rerank 能把“入门教程”顶上来。

---

## 2. 第二层：Rerank 的核心原理——Cross-Encoder

Rerank 最常用的模型是 cross-encoder（交叉编码器）。

它的输入是：

```
[CLS] query [SEP] document [SEP]
```

输出一个相关性分数。

和 bi-encoder 的区别：

| 类型 | 编码方式 | 优点 | 缺点 |
|---|---|---|---|
| Bi-encoder | query 和 doc 分开编码 | 可预计算，快 | 交互弱 |
| Cross-encoder | query 和 doc 拼接后编码 | 精度高 | 无法预计算，慢 |

因此 rerank 只对少量候选做，通常 K=20~100，输出 N=3~10。

```python
# 用 sentence-transformers 的 CrossEncoder 做 rerank
# 先安装: pip install sentence-transformers

from sentence_transformers import CrossEncoder

# 加载一个轻量 rerank 模型
model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

query = "我想学 Python 编程，应该怎么开始？"
docs = [
    "Python 是一种编程语言",
    "Python 蛇的习性介绍",
    "如何安装 Python 解释器",
    "Python 在数据科学中的应用",
    "Python 编程入门教程",
]

# 构造 query-doc 对
pairs = [[query, d] for d in docs]

# 打分
scores = model.predict(pairs)

# 排序
ranked = sorted(zip(docs, scores), key=lambda x: x[1], reverse=True)
for doc, score in ranked:
    print(f"{score:.4f}  {doc}")
```

这段代码可以直接运行。你会看到“Python 编程入门教程”通常排最前。

---

## 3. 第三层：工程里怎么接入 RAG？

真实 RAG 系统里，rerank 一般放在检索之后、生成之前。

流程如下：

```
用户问题
  ↓
召回器（向量/BM25）→ Top-50
  ↓
Reranker → Top-5
  ↓
拼进 Prompt
  ↓
LLM 生成
```

关键工程点：

- 召回数量要大一些，比如 20~100。
- rerank 数量要小一些，比如 3~10。
- rerank 模型可以用开源 cross-encoder，也可以用 Cohere Rerank、BGE Reranker 等 API。
- 要注意延迟：cross-encoder 逐个打分，候选越多越慢。

```python
# 模拟完整 RAG 检索 + rerank 流程

# 1. 模拟向量检索召回
retrieved = [
    {"id": 1, "text": "Python 是一种编程语言", "score": 0.91},
    {"id": 2, "text": "Python 蛇的习性介绍", "score": 0.89},
    {"id": 3, "text": "如何安装 Python 解释器", "score": 0.85},
    {"id": 4, "text": "Python 在数据科学中的应用", "score": 0.84},
    {"id": 5, "text": "Python 编程入门教程", "score": 0.83},
]

query = "我想学 Python 编程，应该怎么开始？"

# 2. 用简单的关键词重合模拟 rerank 分数
# 真实场景请换成 CrossEncoder
def fake_rerank_score(query, doc):
    keywords = ["Python", "编程", "入门", "教程", "开始"]
    return sum(1 for k in keywords if k in query and k in doc) / len(keywords)

# 3. 重排
for item in retrieved:
    item["rerank_score"] = fake_rerank_score(query, item["text"])

reranked = sorted(retrieved, key=lambda x: x["rerank_score"], reverse=True)

# 4. 取 Top-3 给 LLM
top_n = reranked[:3]
print("最终送给 LLM 的文档:")
for item in top_n:
    print(f"  {item['text']}  (rerank={item['rerank_score']:.2f})")
```

---

## 4. 第四层：常见 rerank 方案与选型

常见方案：

1. **Cross-Encoder 开源模型**
   - 例如 `cross-encoder/ms-marco-MiniLM-L-6-v2`
   - 本地运行，免费，适合中小规模。

2. **BGE Reranker**
   - 例如 `BAAI/bge-reranker-base`
   - 中文效果较好。

3. **Cohere Rerank API**
   - 托管服务，效果好，按量收费。

4. **LLM-as-a-reranker**
   - 用大模型给候选打分。
   - 灵活但慢、贵。

选型建议：

- 中文场景优先 BGE Reranker。
- 英文场景可用 MS MARCO cross-encoder。
- 追求效果且能付费，用 Cohere Rerank。
- 候选少、延迟敏感，可用轻量模型。

```python
# 中文场景：使用 BGE Reranker
# pip install FlagEmbedding

from FlagEmbedding import FlagReranker

reranker = FlagReranker("BAAI/bge-reranker-base", use_fp16=True)

query = "我想学 Python 编程，应该怎么开始？"
docs = [
    "Python 是一种编程语言",
    "Python 蛇的习性介绍",
    "如何安装 Python 解释器",
    "Python 在数据科学中的应用",
    "Python 编程入门教程",
]

pairs = [[query, d] for d in docs]
scores = reranker.compute_score(pairs)

ranked = sorted(zip(docs, scores), key=lambda x: x[1], reverse=True)
for doc, score in ranked:
    print(f"{score:.4f}  {doc}")
```

---

## 5. 第五层：评估 rerank 是否有效

不能只看“感觉更好”。要量化。

常用指标：

- **Recall@K**：前 K 个里是否包含正确答案。
- **MRR（Mean Reciprocal Rank，平均倒数排名）**：正确答案排得越前，分数越高。
- **NDCG（Normalized Discounted Cumulative Gain，归一化折损累计增益）**：考虑排序位置和相关性等级。

工程做法：

1. 准备一批“问题 + 正确文档 ID”。
2. 分别跑“只召回”和“召回 + rerank”。
3. 对比 MRR 或 NDCG。

```python
# 简单评估：对比 rerank 前后的 MRR

def mrr(ranked_ids, correct_id):
    for i, doc_id in enumerate(ranked_ids, start=1):
        if doc_id == correct_id:
            return 1 / i
    return 0

# 假设正确文档是 doc5
correct = "doc5"

vector_ranked_ids = ["doc1", "doc2", "doc3", "doc4", "doc5"]
rerank_ranked_ids = ["doc5", "doc3", "doc4", "doc1", "doc2"]

print("向量检索 MRR:", mrr(vector_ranked_ids, correct))
print("Rerank 后 MRR:", mrr(rerank_ranked_ids, correct))
```

如果 rerank 后 MRR 明显提升，说明 rerank 有效。

---

## 总结

- rerank 是 RAG 的“精排”阶段，用 cross-encoder 对候选重新打分。
- 它比向量相似度更准，但更慢，所以只对少量候选做。
- 工程流程：召回 Top-50 → rerank → 取 Top-5 → 喂给 LLM。
- 常用方案：BGE Reranker、MS MARCO Cross-Encoder、Cohere Rerank。
- 要用 MRR、NDCG 等指标验证效果。

---

## 动手练习

**任务**：搭一个最小 rerank 实验，对比“只召回”和“召回 + rerank”的效果。

步骤：

1. 准备 10 条中文文档，主题自定，例如“Python 入门”“机器学习”“做饭”。
2. 准备 5 个问题，每个问题标注 1 个正确文档 ID。
3. 用 `sentence-transformers` 做向量召回，取 Top-5。
4. 用 `BAAI/bge-reranker-base` 对 Top-5 重排。
5. 计算并打印：
   - 只召回时的 MRR
   - rerank 后的 MRR

**提交物**：一段可运行的 Python 脚本 + 终端输出截图。

**提示**：

- 如果没有 GPU，BGE Reranker 也能在 CPU 跑，只是慢一点。
- 可以先用 5 条文档、2 个问题跑通，再扩展。
- 重点不是模型多强，而是理解“两阶段检索”的工程结构。


---

## 本课题目

### single_choice · None



- [A] 改用基于关键词精确匹配的 BM25 检索
- [B] 对文档和查询都使用支持中文的语义向量模型进行嵌入后做相似度检索
- [C] 增大文档分块大小以保留更多上下文
- [D] 在查询时对用户输入做同义词扩展后仍用 TF-IDF 检索

**参考答案**：1

**解析**：语义相近但用词不同的问题本质是词汇鸿沟，语义嵌入模型能把不同措辞映射到相近向量空间；BM25 和 TF-IDF 仍依赖词面匹配，同义词扩展只能有限缓解，且分块大小与语义匹配无关。

### single_choice · None



- [A] 模型是否支持多语言，能在同一向量空间中表示不同语言的语义
- [B] 模型的向量维度是否越小越好，以便节省存储
- [C] 模型是否只能处理英文，因为英文语料最多
- [D] 模型是否附带分词器，以便手动分词后再输入

**参考答案**：0

**解析**：多语言场景要求模型能在同一向量空间中对齐不同语言的语义，否则跨语言检索会失效；维度大小是次要权衡，不能只处理英文，手动分词也不是使用现代嵌入模型的必要前提。

### single_choice · None



- [A] 只选延迟最低的模型，质量可以通过增加文档数量弥补
- [B] 只在离线评估中比较质量，忽略延迟
- [C] 在离线评估中同时测量检索质量和推理延迟，选择满足延迟约束下质量最好的模型
- [D] 随机选择一个模型，上线后再看效果

**参考答案**：2

**解析**：嵌入模型选择是多目标权衡，离线评估应同时测量质量和延迟，在满足延迟约束下选质量最优者；只看延迟或只看质量都会带来风险，随机选择不可取。

### single_choice · None



- [A] 只针对等长文本训练的对称嵌入模型
- [B] 专为短查询检索长文档设计的非对称嵌入模型
- [C] 只能处理单个词的词嵌入模型
- [D] 只输出一个标量分数的分类模型

**参考答案**：1

**解析**：短查询检索长文档是非对称检索的典型场景，非对称嵌入模型更合适；对称模型针对等长文本，词嵌入模型不产生句子级向量，分类模型不用于检索。

### single_choice · None



- [A] 只需替换查询时的模型，索引不用重建
- [B] 必须用新模型重新编码所有文档并重建索引，因为新旧向量空间不一致
- [C] 只需把索引的向量维度手动改成新模型的维度即可
- [D] 只需在检索时对新旧向量做平均即可

**参考答案**：1

**解析**：不同嵌入模型的向量空间不同，换模型后查询向量与旧文档向量不可比，必须用新模型重新编码文档并重建索引；改维度、平均向量、只换查询侧都不能解决空间不一致问题。

### single_choice · None



- [A] 生成最终答案的自然语言文本
- [B] 把查询和文档映射到同一向量空间，以便按语义相似度检索
- [C] 对文档进行语法纠错
- [D] 对用户查询进行拼写检查

**参考答案**：1

**解析**：嵌入模型负责把查询和文档编码为向量，使语义相似度可计算，从而支持检索；生成答案由生成模型完成，纠错和拼写检查不是嵌入模型的核心职责。

### single_choice · None



- [A] 对向量做归一化，使相似度只反映方向差异
- [B] 把所有向量截断为前 10 维
- [C] 把向量维度统一改为 1
- [D] 把余弦相似度换成点积但不做任何处理

**参考答案**：0

**解析**：归一化后向量长度为 1，余弦相似度与点积等价，分数只反映方向差异，从而更稳定；截断维度、改为 1 维会丢失信息，未归一化的点积仍受长度影响。

### single_choice · None



- [A] 模型在目标领域数据上的检索召回率
- [B] 模型的推理延迟和成本
- [C] 模型在社交媒体上的讨论热度
- [D] 模型是否支持目标语言

**参考答案**：2

**解析**：模型选择应基于领域效果、延迟成本、语言支持等可量化指标；社交热度可能受营销影响，不能作为主要决策依据。

### single_choice · None



- [A] 忽略截断，因为嵌入模型总能保留全部语义
- [B] 调整分块策略，使每个块不超过模型最大长度，并保留必要的上下文重叠
- [C] 把模型最大长度改得更大，但模型本身不支持
- [D] 把查询也截断到同样长度以保持一致

**参考答案**：1

**解析**：嵌入模型有最大输入长度限制，超出部分会被截断，因此应调整分块策略使块在限制内并保留重叠；模型能力不能随意扩大，截断查询会进一步损失信息。

### single_choice · None



- [A] 嵌入检索只能处理英文，关键词检索只能处理中文
- [B] 嵌入检索擅长语义匹配，关键词检索擅长精确匹配，两者可以互补
- [C] 嵌入检索完全取代关键词检索，关键词检索已无用处
- [D] 关键词检索的召回率一定高于嵌入检索

**参考答案**：1

**解析**：嵌入检索基于语义相似度，关键词检索基于词面精确匹配，两者各有优势，实际系统中常结合使用；语言限制、完全取代、召回率绝对高低都不成立。

### single_choice · None



- [A] 整本手册的向量会包含太多主题，检索时难以定位到具体相关段落
- [B] 嵌入模型无法处理超过 10 页的文本
- [C] 整本手册的向量维度会变成 200 维
- [D] 检索时会自动按页码排序，与语义无关

**参考答案**：0

**解析**：整本手册的单一向量会混合多个主题，语义被平均化，难以精确定位相关段落，因此需要分块；嵌入模型并非只能处理 10 页，向量维度与页数无关，也不会按页码排序。

### single_choice · None



- [A] 无条件选择模型 A，因为召回率最重要
- [B] 无条件选择模型 B，因为延迟最重要
- [C] 结合线上延迟要求与召回率收益，若延迟可接受则选 A，否则选 B 或做进一步优化
- [D] 两个都不用，改用随机检索

**参考答案**：2

**解析**：模型选择是效果与延迟的权衡，应结合线上延迟约束和召回率收益综合决策；无条件偏向任一指标都不合理，随机检索更不可取。

### single_choice · None



- [A] 检索仍然正常工作，因为相似度计算会自动对齐维度
- [B] 检索会报错或得到无意义结果，因为已有向量与新查询向量维度不一致，无法计算相似度
- [C] 索引会自动降维到 768 维，性能不受影响
- [D] 查询向量会被截断为前 768 维，检索质量略有下降

**参考答案**：1

**解析**：相似度计算要求向量维度一致，已有索引是用旧模型生成的 768 维向量，新查询是 1536 维，维度不匹配会导致计算失败或结果无意义；系统不会自动对齐或截断。

### single_choice · None



- [A] 只在英文语料上训练的单语模型
- [B] 只在中文语料上训练的单语模型
- [C] 在多语言语料上训练、能把中英文映射到同一向量空间的多语言模型
- [D] 只能输出词频统计的模型

**参考答案**：2

**解析**：跨中英文检索要求模型在多语言语料上训练，使不同语言映射到同一向量空间；单语模型无法对齐另一种语言，词频统计模型不产生语义向量。

### single_choice · None



- [A] 只对文档正文做嵌入，标题不参与嵌入
- [B] 只对用户查询做嵌入，文档用关键词索引
- [C] 对文档的标题和正文分别或拼接后做嵌入，使查询与标题更易匹配
- [D] 把所有文档标题拼接成一个长文本后做一次嵌入

**参考答案**：2

**解析**：标题通常高度概括主题，将标题纳入嵌入（单独或与正文拼接）能提高查询与文档的语义匹配；只用正文可能丢失标题信息，只用关键词索引无法解决语义问题，把全部标题拼成一条向量则丧失区分度。

### single_choice · None



- [A] 只比较两个模型在通用语义相似度基准上的分数，因为基准分数高就一定好
- [B] 在标注集上分别用两个模型建索引并检索，比较 top-k 召回率
- [C] 只比较两个模型的推理速度，速度快的更适合
- [D] 只比较两个模型的向量维度，维度高的必然更准

**参考答案**：1

**解析**：实际 RAG 关注的是给定查询能否召回相关文档，因此在标注集上建索引并比较 top-k 召回率最贴近真实效果；通用基准分数、推理速度和维度都不能单独决定领域检索质量。

### single_choice · None



- [A] 医学文献太长，嵌入模型无法处理长文本
- [B] 通用模型的向量维度不适合医学领域
- [C] 领域术语的语义在通用模型中没有得到充分训练，导致向量表示不佳
- [D] 医学文献必须使用关键词检索，不能用向量检索

**参考答案**：2

**解析**：通用嵌入模型对专业术语的语义覆盖不足，导致领域内向量区分度差；长文本可通过分块解决，维度并非领域适配的关键，向量检索也适用于医学领域。

### single_choice · None



- [A] 对称检索指查询和文档长度相同，非对称检索指长度不同
- [B] 非对称检索模型适合短查询检索长文档，对称检索模型适合查询和文档形式相近的场景
- [C] 对称检索只能用于图像，非对称检索只能用于文本
- [D] 非对称检索模型不能用于 RAG，因为 RAG 查询和文档总是等长的

**参考答案**：1

**解析**：对称与非对称区分的核心是查询与文档在长度和形式上是否相似；非对称模型专为短查询对长文档设计，RAG 常见这种场景，因此选项 B 正确，其余选项混淆了概念或场景。

### single_choice · None



- [A] 小模型一定比大模型差，应无条件换最大模型
- [B] 在延迟和成本可接受的前提下，换用在该领域数据上表现更好的更大或更专用的嵌入模型
- [C] 继续使用小模型，但把 top-k 从 5 提高到 100，以数量弥补质量
- [D] 放弃向量检索，改用人工规则匹配

**参考答案**：1

**解析**：模型选择需要在效果、延迟和成本之间权衡，应基于领域表现选择更合适的模型；小模型不一定绝对差，盲目增大 top-k 会引入噪声，放弃向量检索则倒退。

### single_choice · None



- [A] 嵌入模型无法处理短文本
- [B] 相似度高只代表语义接近，不代表该块对回答有用，需要结合重排或过滤策略
- [C] 相似度计算方式选错了，应改用欧氏距离
- [D] 该块不应被嵌入，所有过渡文字都应删除

**参考答案**：1

**解析**：向量相似度衡量的是语义接近程度，过渡文字可能与查询语义接近但不含答案，因此需要重排或过滤；嵌入模型可处理短文本，换距离度量不解决内容无用问题，删除所有过渡文字也不现实。

### single_choice · None



- [A] 文档和查询都使用同一个嵌入模型进行编码
- [B] 文档使用模型 A 编码，查询时使用模型 B 编码
- [C] 文档和查询都在同一台机器上编码
- [D] 文档和查询都使用相同的归一化方式

**参考答案**：1

**解析**：查询和文档必须用同一个嵌入模型（或至少同一向量空间）编码，否则向量不可比；同一模型、同一归一化方式是正确做法，机器是否相同不影响向量语义。

### single_choice · None



- [A] 对候选文档按与查询的相关性重新打分并重排，使最相关的排到前面
- [B] 把 100 个候选全部压缩成 10 个短摘要
- [C] 生成最终答案，替代大语言模型的输出
- [D] 把查询改写为更具体的子查询

**参考答案**：0

**解析**：重排序的本质是对第一阶段召回（recall）得到的候选集，使用更精细（通常更昂贵）的相关性模型重新打分并排序，从而让真正相关的少量文档进入后续上下文。压缩、生成答案、查询改写都不是 rerank 的职责。

### single_choice · None



- [A] 因为重排序模型不能处理超过 10 个文档
- [B] 因为重排序模型通常更慢/更贵，先召回缩小候选集可以在质量和成本间取得平衡
- [C] 因为召回模型比重排序模型准确率更高
- [D] 因为向量数据库不支持打分排序

**参考答案**：1

**解析**：重排序模型（如交叉编码器）精度高但计算代价大，无法对整个语料库实时计算。先用轻量的向量检索或关键词检索把范围缩到几十到几百条，再用重排序精排，是典型的效率-质量权衡。

### multi_choice · None



- [A] 召回决定候选集的上限，重排序只能在候选集内精排
- [B] 更高的召回率通常给重排序更大的发挥空间
- [C] 召回阶段的相关文档若缺失，重排序无法弥补
- [D] 重排序可以完全替代召回，不需要召回阶段
- [E] 召回和重排序使用完全相同的模型和分数

**参考答案**：[0, 1, 2]

**解析**：重排序在候选集内部工作，受召回上限约束；召回越全，重排序越能把相关文档选出来。重排序不能替代召回（否则就要对全库计算，代价不可接受），两者模型与分数通常也不同。

### multi_choice · None



- [A] 把不同来源的分数未归一化就直接相加融合
- [B] 重排序候选集过大导致延迟飙升，超出线上服务预算
- [C] 只关注 Top-1 命中，忽略整体排序质量指标
- [D] 在召回阶段就使用交叉编码器对全语料打分
- [E] 对每条 query 都重新训练重排序模型

**参考答案**：[0, 1, 2, 3]

**解析**：分数未归一化融合会让某一路主导；候选集过大会拖慢响应；只看 Top-1 会掩盖排序退化；对全语料用交叉编码器计算量不可接受。对每条 query 重新训练模型既不可行也无必要，不是常见做法。

### fill_blank · None



**参考答案**：["rerank", "re-rank", "重排序", "重排", "re-ranking"]

**解析**：该过程称为 rerank（重排序），其模型称为 reranker/交叉编码器。它在召回之后对候选集做精排，提升送入大模型上下文的相关性。

### fill_blank · None



**参考答案**：["召回", "recall", "检索", "retrieval", "初排", "粗排"]

**解析**：第一阶段通常称为召回/检索（recall/retrieval），负责从全库快速缩小范围；第二阶段是重排序（rerank），用计算量更大的模型精排候选集。

### fill_blank · None



**参考答案**：["cross", "cross-encoder", "交叉", "交叉编码器", "cross encoder"]

**解析**：交叉编码器（cross-encoder）将 query 和 document 联合编码，能建模细粒度交互，效果好但无法预计算文档表示；双编码器（bi-encoder）分别编码，可离线建索引、速度快。

### code_reading · None



**参考答案**：该段代码先召回 n 条候选，用重排序模型对每条候选打分，然后按分数降序取前 k 条作为最终结果。先召回较多候选（n>k）是为了给重排序更大的选择空间：召回模型精度有限，相关文档可能排在 n 条中的靠后位置，重排序可以用更精细的模型把它重新排到前面。如果只召回 k 条，重排序只能在很小的集合内排序，容易因为召回遗漏而丢失相关文档。

**解析**：核心是『召回扩大候选集 + 重排序精排取 Top-k』的两阶段权衡：n 提供召回覆盖率，k 控制进入上下文的规模。

### code_reading · None



**参考答案**：问题在于两路分数的量纲和分布差异很大：向量相似度在约 0~1，重排序分数是 logits 约 -10~10，直接按 0.5/0.5 相加会让重排序分数在数值上主导最终排序，权重 0.5 实际上并不等价。改进方法：先对各路分数做归一化（如 min-max 或 z-score），或在同一候选集内按排名做融合（如倒数排名融合 RRF），再按业务需求设权重。

**解析**：分数融合的前提是量纲可比。未归一化时，数值范围大的一路会主导排序结果，权重失去意义。归一化或基于排名的融合是常见修正。

### scenario · None



**解析**：正确文档已被召回但未进入最终上下文，说明瓶颈在召回之后的精排/截断环节。应检查重排序模型的相关性打分、候选集大小 N、最终保留的 Top-k，以及融合/截断策略，而不是去优化召回或生成。

### scenario · None



**解析**：重排序是延迟大头，可从三方面入手：缩小候选集 N（如 200 → 50）、对候选分批并行/批处理以便用上 GPU 吞吐、换更小或量化/蒸馏的重排序模型；同时保证召回率不下降太多，避免因缩减候选集而漏掉相关文档。需要在延迟与质量间做权衡并做 A/B 验证。

### scenario · None



**解析**：应先构建带标注的领域评测集，用 NDCG/MRR/MAP 等排序指标做离线对比；同时检查召回阶段指标避免被掩盖；上线采用小流量 A/B 测试，结合人工评估与业务指标（点击、采纳率、答案正确率）观察，逐步放量，保留回滚开关。

### single_choice · None



- [A] 交叉编码器把查询和文档拼接后一起编码，能建模更细粒度的交互，但无法预计算文档向量
- [B] 交叉编码器可以像双编码器一样提前把文档编码好存入向量库
- [C] 双编码器必须成对输入查询和文档才能工作
- [D] 两者得到的相似度分数含义完全相同，可直接数值比较

**参考答案**：0

**解析**：交叉编码器将 query 和 document 一起送入模型，能捕捉词级交互，效果好但每条 query-document 对都要前向计算，不能预先缓存文档表示。双编码器则分别编码，可离线建索引，速度快但交互弱。两者分数标定不同，不宜直接比较。

### scenario · None



**解析**：把大量低相关文档塞入上下文会引入噪声、稀释关键信息，还可能触发『lost in the middle』效应，让模型忽略中段内容；同时 token 变多导致成本与延迟上升。改进方向是保持较小的 Top-k、提高重排序精度、对上下文做去重/压缩/重排，确保高相关文档位于显著位置。

### single_choice · None



- [A] 两者量纲和分布不同，直接相加可能导致某一方主导，通常需要归一化或加权后再融合
- [B] 两者数值范围完全一致，可直接相加
- [C] 重排序分数必须乘以 -1 才能与余弦相似度相加
- [D] 余弦相似度必须转成角度制才能与重排序分数相加

**参考答案**：0

**解析**：不同模型输出的分数尺度、分布不同（如 logits、概率、余弦值），直接线性组合会让量纲大的那一路主导排序结果。常见做法是归一化（如 min-max、z-score）或对两路分数做加权/倒数排名融合。

### single_choice · None



- [A] 召回阶段没有把真正相关的文档召回到候选集中，重排序再强也无法补救
- [B] 重排序模型参数量太大
- [C] 重排序用了 GPU 而召回用了 CPU
- [D] 重排序返回了浮点数分数

**参考答案**：0

**解析**：重排序是在召回候选集内部做精排，其上限由召回决定。如果相关文档根本没被召回（召回率不足），重排序无法凭空生成。这是典型的『召回是瓶颈』问题。

### single_choice · None



- [A] 重排序通常位于召回之后、把结果拼进大模型上下文之前
- [B] 重排序通常位于大模型生成答案之后，用于修正输出
- [C] 重排序必须放在查询改写之前
- [D] 重排序应放在最终答案生成的最开始，早于任何检索

**参考答案**：0

**解析**：标准 RAG 流水线是：查询处理/改写 → 召回 → 重排序 → 上下文组装 → 大模型生成。重排序在召回之后、生成之前，用于筛选和排序要送入模型的文档。

### single_choice · None



- [A] 上下文变长、成本上升，且可能引入噪声文档干扰生成
- [B] 召回率立刻变成 100%
- [C] 重排序模型会自动变快
- [D] 大模型一定给出更准确的答案

**参考答案**：0

**解析**：保留更多文档会增加 token 消耗和延迟，同时把相关性较低的文档一起喂给模型，可能造成上下文噪声、稀释关键信息（lost in the middle），并不必然提升答案质量。

### single_choice · None



- [A] NDCG（归一化折损累计增益）
- [B] 文档总数
- [C] 平均文档长度
- [D] 模型参数量

**参考答案**：0

**解析**：NDCG 衡量排序结果中相关项的位置加权质量，对排在靠前的相关文档给予更高权重，是排序/重排序的常用指标。MRR、MAP 也常用。文档总数、长度、参数量与排序质量无直接关系。

### single_choice · None



- [A] 可以把 query 与每个候选文档组成多个 (query, doc) 对，批量送入模型以提升吞吐
- [B] 重排序必须一次只处理一个 (query, doc) 对，无法批处理
- [C] 批处理会改变每个文档的相关性分数排序
- [D] 批处理只对双编码器有效，对交叉编码器无效

**参考答案**：0

**解析**：交叉编码器虽然不能预计算文档表示，但可以把同一 query 与多个候选文档组成多条输入，批量前向计算，提高 GPU 利用率。批处理不改变每条样本的独立打分结果。

### multi_choice · None



- [A] 选择与业务语料领域更匹配的重排序模型或做领域微调
- [B] 适当扩大召回候选集 N，给重排序更多可挑选的文档
- [C] 对输入重排序的查询做改写或扩展，提升语义匹配
- [D] 直接把重排序分数当作最终答案返回给用户
- [E] 把重排序模型替换成随机打乱顺序

**参考答案**：[0, 1, 2]

**解析**：领域适配的模型、更大的候选集、更好的查询表示都能提升重排序上限。重排序只负责排序，不生成答案；随机打乱会破坏排序，显然是错误的。
