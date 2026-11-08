# s7u2l3 40 分钟教学讲义：agent.rag.query_rewrite / 在检索增强生成（Retrieval-Augmented

> 来源 `content/lessons/s7u2l3.json`

## agent.rag.query_rewrite

# 40 分钟教学讲义：agent.rag.query_rewrite

## 一句话直觉

用户问得很短、很口语、有歧义，而知识库（Knowledge Base）里的文档写得很规范；**查询重写（Query Rewrite）** 就是在检索（Retrieval）之前，先把用户问题改写成“更容易被搜到”的查询表达，从而显著提升 RAG（Retrieval-Augmented Generation，检索增强生成）的召回与答案质量。

---

## 0. 学习地图（本节你将掌握）

1. 为什么需要 Query Rewrite：RAG 链路里“检索”是最脆弱的一环。
2. Query Rewrite 的 4 种主流策略：扩展、改写、分解、结构化过滤。
3. 如何用 Python + LLM 做最小可用实现（MVP）。
4. 如何评估 Query Rewrite 是否真的变好（别凭感觉）。
5. 工程化落地：缓存、并行、降级、可观测性。

---

## 1. 背景：RAG 里“检索错了，后面全错”

RAG 的典型流程是：

- 用户问题（Query）
- → 检索（Retrieve）相关文档片段（Chunks）
- → 拼接上下文（Context）
- → 大语言模型（LLM，Large Language Model）生成答案

关键结论：**检索阶段决定了 LLM 能看到什么**。如果查询词与文档词不匹配，向量检索（Vector Search）和关键词检索（BM25）都会漏召。

常见“坏查询”长这样：

- 太短：“报销？”
- 口语化：“出差吃饭的钱咋弄？”
- 指代不明：“它怎么申请？”
- 多意图：“年假和病假的区别，以及怎么请？”

Query Rewrite 的目标：把“坏查询”变成“检索友好查询”。

```python
# 演示：同一个问题，不同查询表达对检索结果的影响（用 TF-IDF 模拟）
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# 知识库文档（模拟企业制度文档，措辞规范）
docs = [
    "员工出差期间产生的餐饮费用，可按公司差旅报销制度申请报销。",
    "年假申请需提前三个工作日在人事系统提交。",
    "病假需提供二级以上医院证明。",
]

# 两种查询：原始 vs 重写后
raw_query = "出差吃饭的钱咋弄？"
rewritten_query = "出差 餐饮费用 报销 申请 流程"

vec = TfidfVectorizer().fit(docs + [raw_query, rewritten_query])
X = vec.transform(docs + [raw_query, rewritten_query])

# 计算与每个文档的相似度
sim_raw = cosine_similarity(X[-2], X[:3]).flatten()
sim_new = cosine_similarity(X[-1], X[:3]).flatten()

print("原始查询相似度:", sim_raw, "-> 最相关文档:", sim_raw.argmax())
print("重写查询相似度:", sim_new, "-> 最相关文档:", sim_new.argmax())
```

预期你会看到：重写后与“差旅报销”文档的相似度更高、排序更靠前。

---

## 2. 四种主流 Query Rewrite 策略

### 2.1 查询扩展（Query Expansion）

给原查询补同义词、上位词、英文术语。

- “报销” → “报销 费用 结算 reimbursement”
- 适合：关键词检索、稀疏向量（Sparse Vector）

### 2.2 查询改写（Query Reformulation）

用 LLM 把口语化问题改成规范表达。

- “出差吃饭的钱咋弄？” → “员工出差餐饮费用如何申请报销？”
- 适合：向量检索（Dense Retrieval）

### 2.3 查询分解（Query Decomposition）

把多意图问题拆成多个子查询，分别检索再合并。

- “年假和病假的区别，以及怎么请？” → [“年假和病假的区别”, “年假申请流程”, “病假申请流程”]
- 适合：多跳（Multi-hop）问答、对比类问题

### 2.4 结构化过滤（Metadata Filtering）

从查询里抽取过滤条件，例如部门、时间、文档类型。

- “2024 年财务部的报销制度” → query=“报销制度”, filter={"dept":"财务", "year":2024}
- 适合：有元数据（Metadata）的知识库

```python
# 演示：用规则 + 简单模板实现 4 种策略的雏形（无需 LLM 也能跑）
import re

def rewrite_expand(q: str) -> str:
    synonyms = {"报销": ["费用", "结算"], "年假": ["annual leave"], "病假": ["sick leave"]}
    extra = []
    for k, vs in synonyms.items():
        if k in q:
            extra.extend(vs)
    return q + " " + " ".join(extra) if extra else q

def rewrite_reformulate(q: str) -> str:
    # 实际项目这里调用 LLM；此处用模板演示
    q = q.replace("咋弄", "如何申请").replace("啥", "什么")
    return q

def rewrite_decompose(q: str) -> list:
    # 简单按“和/以及/、”切分
    parts = re.split(r"[和以及、]", q)
    return [p.strip() for p in parts if p.strip()]

def rewrite_filter(q: str) -> dict:
    m = re.search(r"(\d{4})年(.+?)的(.+)", q)
    if m:
        return {"query": m.group(3), "filter": {"year": int(m.group(1)), "dept": m.group(2)}}
    return {"query": q, "filter": {}}

print(rewrite_expand("报销流程"))
print(rewrite_reformulate("出差吃饭的钱咋弄？"))
print(rewrite_decompose("年假和病假的区别，以及怎么请？"))
print(rewrite_filter("2024年财务部的报销制度"))
```

---

## 3. 用 LLM 做 Query Rewrite 的最小实现

思路：用提示词（Prompt）让 LLM 输出结构化 JSON，包含：

- rewritten_query：改写后的主查询
- sub_queries：子查询列表
- filters：元数据过滤

关键结论：**一定要约束输出格式**，否则下游解析会崩。

```python
# 演示：LLM Query Rewrite 的接口设计（用 mock 模拟 LLM，真实项目替换为 OpenAI/Claude/本地模型）
import json

def llm_call(prompt: str) -> str:
    # mock 返回，真实场景调用 LLM API
    return json.dumps({
        "rewritten_query": "员工出差餐饮费用如何申请报销",
        "sub_queries": ["出差餐饮费用报销条件", "出差餐饮费用报销流程"],
        "filters": {"doc_type": "制度"}
    }, ensure_ascii=False)

PROMPT = """你是查询重写器。请把用户问题改写为检索友好查询。
只输出 JSON，字段：rewritten_query(str), sub_queries(list[str]), filters(dict)。
用户问题：{q}
"""

def rewrite_query(q: str) -> dict:
    raw = llm_call(PROMPT.format(q=q))
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # 降级：解析失败就用原查询
        data = {"rewritten_query": q, "sub_queries": [], "filters": {}}
    return data

result = rewrite_query("出差吃饭的钱咋弄？")
print(json.dumps(result, ensure_ascii=False, indent=2))
```

工程要点：

- 加超时（Timeout）与重试（Retry）。
- 解析失败要降级（Fallback）为原查询。
- 对高频查询做缓存（Cache）。

---

## 4. 评估：怎么知道 Query Rewrite 真的有用？

不要凭感觉。至少看三类指标：

- 召回率（Recall@k）：相关文档是否进入前 k。
- 命中率（Hit Rate）：前 k 里是否至少有一个相关文档。
- 平均倒数排名（MRR，Mean Reciprocal Rank）：相关文档排得越靠前越好。

```python
# 演示：对比原始查询与重写查询的 Recall@k

def recall_at_k(retrieved: list, relevant: set, k: int = 3) -> float:
    topk = set(retrieved[:k])
    if not relevant:
        return 0.0
    return len(topk & relevant) / len(relevant)

# 假设文档 id
retrieved_raw = ["doc_2", "doc_5", "doc_1", "doc_9"]
retrieved_new = ["doc_1", "doc_2", "doc_7", "doc_5"]
relevant = {"doc_1", "doc_2"}

print("原始 Recall@3:", recall_at_k(retrieved_raw, relevant, 3))
print("重写 Recall@3:", recall_at_k(retrieved_new, relevant, 3))
```

关键结论：**Query Rewrite 是手段，不是目的**；要用评估集（Eval Set）驱动决策。

---

## 5. 工程化落地清单

- 缓存：对 (query, 策略) 做键，减少 LLM 调用。
- 并行：sub_queries 并行检索，再合并去重（如 RRF，Reciprocal Rank Fusion）。
- 降级：LLM 超时/解析失败 → 用原查询。
- 可观测：记录原始查询、重写查询、检索结果、命中情况。
- 安全：防止提示词注入（Prompt Injection）改变重写逻辑。

```python
# 演示：并行检索 + RRF 融合（简化版）
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict

def search(q: str) -> list:
    # mock 检索
    return [f"{q}_doc1", f"{q}_doc2", f"{q}_doc3"]

def rrf(rank_lists: list, k: int = 60) -> list:
    score = defaultdict(float)
    for lst in rank_lists:
        for rank, doc in enumerate(lst, start=1):
            score[doc] += 1.0 / (k + rank)
    return [d for d, _ in sorted(score.items(), key=lambda x: -x[1])]

sub_queries = ["出差餐饮报销条件", "出差餐饮报销流程"]
with ThreadPoolExecutor(max_workers=4) as ex:
    results = list(ex.map(search, sub_queries))

fused = rrf(results)
print("融合后排序:", fused)
```

---

## 动手练习（本地可完成）

任务：实现一个 Query Rewrite 模块，并对比效果。

1. 准备 5 篇模拟制度文档（差旅、年假、病假、报销、考勤）。
2. 写 5 个“坏查询”（口语化/多意图/带过滤条件）。
3. 实现两条链路：
   - 基线：直接用原查询做 TF-IDF 检索，输出 Top-3。
   - 改进：先用规则或 LLM 做 Query Rewrite（改写+分解），再检索并合并结果。
4. 为每个查询标注相关文档 id，计算 Recall@3 对比。
5. 输出一张表：查询 | 基线 Recall@3 | 重写 Recall@3。

加分项：

- 用缓存避免重复重写。
- 用 ThreadPoolExecutor 并行检索子查询。
- 加降级：LLM 输出非 JSON 时回退到原查询。

---

## 小结

- Query Rewrite 是 RAG 检索前的“翻译器”，把用户语言翻译成检索语言。
- 四大策略：扩展、改写、分解、结构化过滤。
- 工程上要抓：结构化输出、降级、缓存、并行、评估。

## agent.rag.hyde

## 一句话直觉

在检索增强生成（Retrieval-Augmented Generation, RAG）里，**HyDE（Hypothetical Document Embeddings，假设文档嵌入）** 的核心直觉是：用户的问题很短、很口语，而知识库里的文档很长、很正式；与其直接拿问题去检索，不如先让大语言模型（Large Language Model, LLM）**编一段“假想答案”**，再用这段假想答案去检索真实文档。

---

## 1. 为什么需要 HyDE：问题与文档的“语义鸿沟”

传统 RAG 的流程是：

```
用户问题 -> 嵌入向量 -> 向量数据库检索 -> 取回文档 -> 交给 LLM 回答
```

问题在于：用户问“怎么让 Python 脚本跑得更快？”和知识库里的文档“使用 cProfile 定位性能瓶颈”在字面和语义分布上并不完全一致。

HyDE 的做法是：

```
用户问题 -> LLM 生成假想答案 -> 假想答案嵌入 -> 向量数据库检索 -> 取回真实文档 -> 交给 LLM 回答
```

这里的“假想答案”不需要真实正确，它只需要**在语义空间里接近真实文档**，从而充当一座“语义桥梁”。

---

## 2. HyDE 的最小可运行结构

一个最小 HyDE 检索器包含四步：

1. 用 LLM 根据问题生成假想文档；
2. 用嵌入模型（Embedding Model）把假想文档编码成向量；
3. 在向量库中做相似度检索；
4. 返回真实文档。

下面代码用“伪 LLM”和“伪向量库”演示流程，但接口与真实工程一致。

```python
# 文件：hyde_minimal.py
# 运行前：无需安装任何第三方库，直接 python hyde_minimal.py 即可

import math
from typing import List, Dict

# ---------- 1. 伪 LLM：真实场景替换为 OpenAI / 本地模型调用 ----------
def fake_llm_generate_hypothetical_doc(question: str) -> str:
    """模拟 LLM 根据问题生成一段假想答案。
    真实工程中这里会调用 chat/completions 接口。
    """
    templates = {
        "python 性能": "Python 脚本性能优化通常包括使用 cProfile 定位热点、"
                        "用 NumPy 向量化替代循环、减少全局变量查找、"
                        "使用多进程 multiprocessing 绕过 GIL。",
        "向量检索": "向量检索依赖嵌入模型将文本映射到高维空间，"
                    "再通过余弦相似度或内积进行最近邻搜索，"
                    "常用工具有 FAISS、Milvus、Chroma。",
    }
    for key, doc in templates.items():
        if key in question:
            return doc
    return "这是一段关于该问题的通用假设性回答，用于桥接问题与文档的语义鸿沟。"

# ---------- 2. 伪嵌入模型：真实场景替换为 text-embedding-3-small 等 ----------
def fake_embed(text: str, dim: int = 8) -> List[float]:
    """用字符哈希构造一个确定性的伪向量，仅用于演示。"""
    vec = [0.0] * dim
    for i, ch in enumerate(text):
        vec[i % dim] += (ord(ch) % 97) / 97.0
    # 归一化
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]

def cosine(a: List[float], b: List[float]) -> float:
    return sum(x * y for x, y in zip(a, b))

# ---------- 3. 伪向量库 ----------
KNOWLEDGE_BASE: List[Dict[str, str]] = [
    {"id": "doc1", "text": "使用 cProfile 和 line_profiler 可以定位 Python 性能瓶颈。"},
    {"id": "doc2", "text": "NumPy 向量化能显著减少 Python 循环开销。"},
    {"id": "doc3", "text": "FAISS 是 Facebook 开源的向量最近邻搜索库。"},
    {"id": "doc4", "text": "Chroma 是轻量级向量数据库，适合本地 RAG 原型。"},
]

# ---------- 4. HyDE 检索 ----------
def hyde_retrieve(question: str, top_k: int = 2) -> List[Dict[str, str]]:
    # 步骤 1：生成假想文档
    hypo_doc = fake_llm_generate_hypothetical_doc(question)
    print(f"[HyDE] 假想文档：{hypo_doc}\n")

    # 步骤 2：编码假想文档
    query_vec = fake_embed(hypo_doc)

    # 步骤 3：对知识库中每篇文档打分
    scored = []
    for doc in KNOWLEDGE_BASE:
        doc_vec = fake_embed(doc["text"])
        score = cosine(query_vec, doc_vec)
        scored.append((score, doc))

    # 步骤 4：返回 top-k
    scored.sort(key=lambda x: x[0], reverse=True)
    return [doc for _, doc in scored[:top_k]]

if __name__ == "__main__":
    q = "python 性能怎么优化？"
    results = hyde_retrieve(q, top_k=2)
    print("检索结果：")
    for r in results:
        print(f"- {r['id']}: {r['text']}")
```

运行后你会看到：即使问题里没有出现“cProfile”“NumPy”，HyDE 也能把相关文档排到前面。

---

## 3. 关键结论：HyDE 不是“生成答案”，而是“生成检索钥匙”

很多初学者误以为 HyDE 生成的内容要直接回答用户。实际上：

- 假想文档是**给检索器看的**，不是给用户看的；
- 它可以包含事实错误，只要语义方向对；
- 真正回答用户的是最后一步 LLM，它看到的是**真实文档**。

下面代码展示“假想文档可以错，但检索仍然有效”的对比实验。

```python
# 文件：hyde_wrong_but_useful.py
from hyde_minimal import fake_embed, cosine, KNOWLEDGE_BASE

# 一段“事实错误但语义相关”的假想文档
wrong_hypo = "Python 性能优化就是多用 for 循环和全局变量，cProfile 完全没用。"

query_vec = fake_embed(wrong_hypo)
scores = [(cosine(query_vec, fake_embed(d["text"])), d["id"]) for d in KNOWLEDGE_BASE]
scores.sort(reverse=True)
print("即使假想文档事实错误，检索排名仍然：", scores)
```

结论：HyDE 利用的是**语义分布对齐**，而不是事实正确性。

---

## 4. 工程落地：把 HyDE 接进真实 RAG

真实工程中，你只需要替换两个组件：

| 组件 | 演示版 | 真实版 |
|---|---|---|
| LLM | `fake_llm_generate_hypothetical_doc` | OpenAI `gpt-4o-mini` / 本地 Qwen |
| Embedding | `fake_embed` | `text-embedding-3-small` / BGE |

一个真实调用示例（伪代码级，保留接口形状）：

```python
# 文件：hyde_real_shape.py
# 仅展示真实工程接口形状，不依赖具体 SDK

def generate_hypothetical_doc(question: str, client, model: str = "gpt-4o-mini") -> str:
    prompt = f"请写一段可能出现在技术文档中的段落，用来回答：{question}"
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,  # 适度随机，生成多样假想文档
    )
    return resp.choices[0].message.content

def embed(text: str, embed_client, model: str = "text-embedding-3-small"):
    return embed_client.embeddings.create(model=model, input=text).data[0].embedding
```

工程建议：

- 假想文档数量可以是 1~4 篇，做多向量平均或最大池化；
- 温度（temperature）建议 0.5~0.8，太低会退化成“复述问题”；
- 可与原始问题向量做**混合检索**，兼顾精确匹配与语义扩展。

---

## 5. 何时不要用 HyDE

HyDE 不是银弹。以下场景收益低：

- 问题是精确查询（如订单号、错误码），需要字面匹配；
- 知识库文档本身就是问答对，问题与文档已对齐；
- 延迟敏感场景，因为多了一次 LLM 调用。

一个简单的决策规则：

```
如果问题短、口语化、文档长且正式 -> 用 HyDE
如果问题是关键词/ID/代码符号 -> 用 BM25 或混合检索
```

---

## 动手练习

**任务**：在本地实现一个 HyDE 检索小实验。

1. 复制第 2 节代码到 `hyde_minimal.py`；
2. 向 `KNOWLEDGE_BASE` 增加 5 篇你自己领域的文档（如“机器学习”“ cooking”均可）；
3. 修改 `fake_llm_generate_hypothetical_doc`，让它在没有匹配模板时返回更通用的假想文档；
4. 设计 3 个口语化问题，分别比较：
   - 直接用问题嵌入检索；
   - 用 HyDE 假想文档嵌入检索；
   记录 top-2 结果差异；
5. 写一段 100 字结论：HyDE 在哪些问题上更优，在哪些问题上更差。

**提交物**：`hyde_minimal.py` + 一段对比结果说明。


---

## 本课题目

### single_choice · None



- [A] 向量数据库索引类型选择错误
- [B] 查询中缺少指代消解所需的上文信息，导致检索到的文档与真实意图不匹配
- [C] 嵌入模型维度太低
- [D] 文档切分块太小

**参考答案**：1

**解析**：该问题含有代词「它」，属于依赖对话上下文的查询。直接拿原句去检索会丢失指代对象，检索语义漂移。查询改写（query rewrite）的一项核心任务就是结合历史对话把指代补全为自包含的查询。

### single_choice · None



- [A] 检索器会结合会话历史自动补全「它」的指代，结果准确
- [B] 检索器会把「它」当成一个普通词项，召回大量与注意力机制无关的文档
- [C] 检索器会报错，因为查询中不允许出现代词
- [D] 检索器会优先返回最新上传的文档

**参考答案**：1

**解析**：检索器通常只看到当前查询字符串，无法自动感知上文，「它」会被当作无信息量的词项，导致召回的文档偏离真实主题。这正是需要查询改写来补全指代的原因。

### single_choice · None



- [A] 查询会变得更短
- [B] 改写可能偏离原意，或对本来清晰的查询造成语义漂移，并增加延迟
- [C] 向量维度会发生改变
- [D] 检索器会拒绝执行查询

**参考答案**：1

**解析**：改写不是免费的午餐：LLM 可能误解用户意图、丢词或加词，导致语义漂移；同时增加一次模型调用。因此实际系统常按需改写或做改写校验。

### single_choice · None



- [A] 查询字符串的长度是否大于 20 个字符
- [B] 查询中是否含有代词、省略、多个并列子句或与知识库用语风格差异大的表达
- [C] 用户是否使用了标点符号
- [D] 查询是否以问号结尾

**参考答案**：1

**解析**：改写的触发应基于语义信号：指代、省略、多意图、风格差异等；而长度、标点、问号等形式特征与是否需要改写没有必然关系。

### single_choice · None



- [A] 在文档切分之前
- [B] 在嵌入与检索之前，即拿到用户查询后、送入检索器前
- [C] 在检索完成之后、生成答案之前
- [D] 在生成答案之后

**参考答案**：1

**解析**：查询改写目的是影响检索，因此必须发生在嵌入/检索之前；放在检索后或生成后无法改变检索到的文档集合。

### single_choice · None



- [A] 改写成「Python CSV 读取方法」
- [B] 改写成「Python 使用 csv 模块解析逗号分隔文件」
- [C] 改写成「csv 是什么」
- [D] 不做改写，直接检索

**参考答案**：1

**解析**：改写的目标是对齐知识库的表述风格与术语。B 选项引入了「csv 模块」「逗号分隔文件」「解析」等文档用语，更贴近文档标题，检索匹配度最高。

### single_choice · None



- [A] 两者都在检索前执行
- [B] 查询改写作用于查询侧以改变召回集合；重排序作用于检索结果侧，对已召回的候选重新打分排序
- [C] 两者都只能使用 LLM 完成
- [D] 重排序会改变查询的含义

**参考答案**：1

**解析**：改写改变「查什么」，发生在检索前，影响召回；重排序不改变查询，只对召回结果重新排序。二者阶段与作用对象不同。

### single_choice · None



- [A] BM25 不支持中文
- [B] 改写输出多为语义化、同义化的自然语言表述，向量检索能受益，而 BM25 依赖精确词项匹配，收益有限
- [C] 向量检索不需要查询改写
- [D] LLM 的改写一定有问题

**参考答案**：1

**解析**：向量检索关注语义相似，语义化改写能拉近查询与文档的向量距离；BM25 基于词项统计，改写若未引入文档中实际存在的词项，收益就不明显。

### single_choice · None



- [A] 假装知道并编造一个库名
- [B] 合理解析出信息缺失，向用户反问是哪个库，或先检索「库安装方式」再确认
- [C] 直接把整句当成关键词检索
- [D] 把「那个」替换为「这个」

**参考答案**：1

**解析**：查询改写不应凭空捏造实体。在缺少关键指代对象时，应通过澄清或保守改写来处理，避免引入错误假设导致下游幻觉。

### single_choice · None



- [A] 查询中的指代依赖上文
- [B] 查询包含多个需要分别检索的子问题
- [C] 查询的表述风格与知识库文档差异大
- [D] 向量数据库中的文档数量太多

**参考答案**：3

**解析**：查询改写面向查询本身的表达问题（指代、多意图、风格差异等）；文档数量属于语料规模问题，与查询如何改写无关。

### single_choice · None



- [A] 让模型自由发挥，改写结果越长越好
- [B] 限定改写规则（如只允许指代补全与术语对齐），或对改写前后做一致性校验、保留原始查询作为兜底
- [C] 只保留改写后的查询，丢弃原始查询
- [D] 对改写结果不做任何检查直接使用

**参考答案**：1

**解析**：通过约束改写范围、做一致性检查、保留原查询用于回退或混合检索，可以在享受改写收益的同时降低语义漂移风险。

### single_choice · None



- [A] 「那 GPT 呢」
- [B] 「GPT 的预训练任务是什么」
- [C] 「BERT 和 GPT 是什么」
- [D] 「预训练任务」

**参考答案**：1

**解析**：「那 GPT 呢」省略了被问的属性，需结合上文补全为「GPT 的预训练任务是什么」，才能作为自包含查询送入检索器。其他选项要么保留省略，要么改变了问题意图。

### single_choice · None



- [A] 把用户问题翻译成英文后再检索
- [B] 把口语化、含指代或多意图的问题转写成适合检索的自包含查询
- [C] 对知识库文档重新做一遍 embedding
- [D] 在生成答案时对模型输出做后处理

**参考答案**：1

**解析**：查询改写作用在「检索前」的查询侧，目的是让查询更清晰、自包含、易于匹配文档；翻译、重建索引、生成后处理都不属于查询改写。

### single_choice · None



- [A] 对查询做同义词扩展，加入「故障」「异常」等词
- [B] 先向用户澄清缺失的关键信息（如报错文本），再进行检索
- [C] 把查询拆成多个子查询并行检索
- [D] 提高检索返回的 top-k

**参考答案**：1

**解析**：查询本身缺失关键实体（报错内容），任何改写都无法凭空补全。此时最优策略是澄清式改写或反问用户；同义词扩展、拆分、调大 top-k 都不能弥补信息缺失。

### single_choice · None



- [A] 把整个问题压缩成一个短关键词
- [B] 将问题分解为多个子查询（分别针对两个框架），再合并检索结果
- [C] 只保留问题中的第一个实体
- [D] 把问题改写成陈述句

**参考答案**：1

**解析**：对比型问题包含多个独立信息需求，单一查询的向量容易被某一实体主导。查询分解（decomposition）能把每个子需求分别检索，提升召回覆盖。

### single_choice · None



- [A] 用一个更短的查询替换原查询
- [B] 先让 LLM 生成一段假设性的答案文档，再用该文档的向量去检索
- [C] 对原查询的向量加入随机噪声以提升多样性
- [D] 把查询同时发给多个检索器投票

**参考答案**：1

**解析**：HyDE 让生成模型先产出「假设答案」，用假设答案的嵌入去检索，使其在向量空间中更接近真实文档。它不是缩短查询、加噪或集成投票。

### single_choice · None



- [A] 检索结果的多样性会下降
- [B] 增加检索与生成的调用次数，带来额外延迟和成本
- [C] 向量数据库的维度会增加
- [D] 文档切分粒度会变粗

**参考答案**：1

**解析**：多查询改写（multi-query）通过增加查询数量提升召回，但每个查询都需要一次嵌入与检索，且改写本身调用 LLM，因此主要代价是延迟和费用上升。

### single_choice · None



- [A] 保留原句但加上引号
- [B] 改写成贴近知识库表述的直白说法，如「大任务的分步骤拆解与分阶段处理」
- [C] 把「大象」「冰箱」替换为同义词
- [D] 把句子翻译成英文再检索

**参考答案**：1

**解析**：隐喻或口语表达与知识库的书面表述存在词汇鸿沟。查询改写的目标之一是弥合这种表达差异，将意图转写为接近文档用语的查询。

### single_choice · None



- [A] 两者完全等价，只是叫法不同
- [B] 查询扩展通常指向查询中增加同义或相关词项；查询改写范围更广，还包括指代消解、分解、重写等
- [C] 查询扩展只能用于关键词检索，不能用于向量检索
- [D] 查询改写只能用于向量检索，不能用于关键词检索

**参考答案**：1

**解析**：查询扩展是查询改写的一种常见手段（增词、同义扩展），但查询改写还包括结构化的操作，如指代补全、多意图分解、风格转写等，适用范围也更广。

### single_choice · None



- [A] 只看当前用户问题
- [B] 看当前问题与最近若干轮对话，再生成自包含查询
- [C] 看全部历史对话以及知识库全文
- [D] 只看知识库摘要

**参考答案**：1

**解析**：指代消解需要上文，但把全部历史或知识库全文塞入反而引入噪声并增加成本。常见做法是结合最近若干轮对话来改写，兼顾信息完整与效率。

### single_choice · None



- [A] 让大模型先根据问题生成一个假设性答案文档，再用该文档的向量去检索
- [B] 对用户的原始问题做同义词扩展后直接检索
- [C] 把检索到的文档全部拼接后交给大模型生成答案
- [D] 训练一个专门的检索模型来匹配问题和文档

**参考答案**：0

**解析**：HyDE 的关键是先让 LLM 生成一个『假设文档』（假想答案），对该文档做向量化后再去检索，从而缩小问题与文档之间的语义鸿沟，而不是直接对原问题检索或训练新检索模型。

### single_choice · None



- [A] 假设文档与真实文档在语料风格和用词上更接近，向量空间更接近目标文档
- [B] 假设文档包含真实答案，可以直接返回给用户
- [C] 假设文档更短，检索速度更快
- [D] HyDE 减少了向量维度，降低了计算成本

**参考答案**：0

**解析**：问题和答案/文档在表述风格上往往差异很大，向量相似度不高。假设文档模仿了文档的写作风格，因此其向量更接近真实相关文档，从而提升召回质量。

### single_choice · None



- [A] 两者都是在检索前改善查询文本，但 HyDE 生成的是文档式内容，查询改写通常仍是问题式内容
- [B] 两者完全等价
- [C] HyDE 属于查询改写的一种特例，且只能改写为问题
- [D] 查询改写只能在 HyDE 之后进行

**参考答案**：0

**解析**：HyDE 与查询改写都属于『检索前查询优化』，但 HyDE 生成的是仿文档内容，查询改写一般保持问题/关键词形态，二者思路不同但可结合。

### single_choice · None



- [A] 检索结果可能波动，可通过降低生成温度或多次生成后融合向量来缓解
- [B] 系统会崩溃
- [C] 向量维度会发生变化
- [D] 嵌入模型会被重新训练

**参考答案**：0

**解析**：LLM 采样具有随机性，导致假设文档和查询向量波动，进而影响召回稳定性；常通过降低温度、多次生成取平均向量等方式缓解。

### single_choice · None



- [A] HyDE 要求用户问题必须是自然语言，否则无法使用
- [B] HyDE 适合问答式检索场景
- [C] HyDE 可以与其他检索增强手段结合
- [D] HyDE 适用于短问题、稀疏语义的问题

**参考答案**：0

**解析**：HyDE 对问题形式并不强依赖，关键词式、短语式查询同样可以由 LLM 生成假设文档；其余选项均为 HyDE 的合理特性。

### multi_choice · None



- [A] 它在检索前增加了一次 LLM 生成步骤
- [B] 它用生成的假设文档代替原始问题去做向量检索
- [C] 它最终返回的是假设文档本身
- [D] 它可以与向量数据库正常配合使用

**参考答案**：[0, 1, 3]

**解析**：HyDE 的确增加一次生成并用假设文档作为查询，且可与向量数据库配合；但它最终返回的是检索到的真实文档，而非假设文档，故 C 错误。

### multi_choice · None



- [A] 用于生成假设文档的 LLM 质量
- [B] 嵌入模型对假设文档和目标语料的表征能力
- [C] 生成假设文档时的提示词设计
- [D] 操作系统版本

**参考答案**：[0, 1, 2]

**解析**：LLM 质量、嵌入模型表征能力、提示词设计都会直接影响假设文档的质量及向量表征效果；操作系统版本与 HyDE 效果无关。

### multi_choice · None



- [A] HyDE 增加了生成开销
- [B] HyDE 在问题与文档用词差异大时通常更有优势
- [C] HyDE 一定比直接检索快
- [D] 两者都可以使用相同的向量数据库

**参考答案**：[0, 1, 3]

**解析**：HyDE 增加生成步骤因此通常不更快，C 错误；其余三项均正确：它增加开销、在语义鸿沟大时更有优势、且与直接检索共用同一向量检索底座。

### fill_blank · None



**参考答案**：["假设", "假设性", "假想", "hypothetical"]

**解析**：HyDE 全称 Hypothetical Document Embeddings，核心即生成『假设（性）文档』并对其做嵌入用于检索。

### fill_blank · None



**参考答案**：["检索", "召回", "retrieval"]

**解析**：HyDE 的作用发生在检索阶段，它通过改写查询表征来提升召回质量，而非直接改进生成模型本身。

### code_reading · None



**参考答案**：docs 来自向量索引 index 中检索到的真实文档，而非 hypo。设计目的是用 LLM 生成的假设文档作为查询向量，使查询更接近真实文档的语义风格，从而提升召回质量；假设文档本身不作为结果返回。

**解析**：代码中 hs 只用来生成向量，index.search 返回的是索引内的真实文档，这正是 HyDE『生成假设文档用于检索、返回真实文档』的核心流程。

### scenario · None



**解析**：场景题考察把 HyDE 落到工程上：先由 LLM 把短问题扩展为假设文档，对该文档做嵌入后检索，最终仍返回真实文档作为上下文；同时要关注额外 LLM 调用带来的延迟/成本开销，以及假设文档错误可能误导检索的风险。

### single_choice · None



- [A] 问题 → 生成假设文档 → 向量化假设文档 → 向量检索 → 返回真实文档
- [B] 问题 → 向量化问题 → 生成假设文档 → 返回假设文档
- [C] 问题 → 检索真实文档 → 生成假设文档 → 重新排序
- [D] 问题 → 生成假设文档 → 直接作为最终答案返回

**参考答案**：0

**解析**：HyDE 的顺序是先由 LLM 根据问题生成假设文档，再对该假设文档做嵌入并检索，最终仍返回真实语料中的文档，而非假设文档本身。

### single_choice · None



- [A] 语料库中被检索到的真实文档
- [B] LLM 生成的假设文档
- [C] 假设文档与真实文档混合的原始假设文本
- [D] 用户问题本身

**参考答案**：0

**解析**：HyDE 只是用假设文档来改善检索，真正作为上下文交给下游的是检索命中的真实文档，假设文档仅用作检索查询的替身。

### single_choice · None



- [A] 依赖 LLM 生成假设文档，增加了一次额外的推理开销，且假设内容可能有误导致检索方向偏移
- [B] 必须重新训练嵌入模型
- [C] 无法与向量数据库一起使用
- [D] 只能用于英文语料

**参考答案**：0

**解析**：HyDE 需要在检索前额外调用一次 LLM 生成假设文档，带来延迟与成本，同时假设文档若偏离事实可能误导检索方向，这是其主要局限。

### single_choice · None



- [A] 通过生成较完整的假设文档补足语义信息，使检索向量更具区分度
- [B] 缩短检索返回的文档数量
- [C] 避免使用嵌入模型
- [D] 替代关键词检索的全部功能

**参考答案**：0

**解析**：短问题信息量少，向量往往不够『有内容』。HyDE 用假设文档把隐含语义展开，让检索向量携带更多上下文，从而提升召回质量。

### single_choice · None



- [A] 两者底层仍使用同一套嵌入模型和向量检索机制，区别在于用什么文本去生成查询向量
- [B] HyDE 不使用嵌入模型
- [C] 普通问题检索一定优于 HyDE
- [D] HyDE 只能配合 BM25 使用

**参考答案**：0

**解析**：HyDE 并没有更换检索机制，它只是把『查询文本』从原问题换成假设文档，底层嵌入模型与向量检索流程保持不变。

### single_choice · None



- [A] 领域非常专业、LLM 容易生成看似合理但事实错误的假设文档时
- [B] 用户问题很长、信息非常充分时
- [C] 语料库文档数量很少时
- [D] 使用了较新的嵌入模型时

**参考答案**：0

**解析**：在专业领域，LLM 生成的假设文档可能包含错误事实或偏离真实用词，导致查询向量被误导，检索质量下降；问题信息本就充分时一般不会因此变差。

### single_choice · None



- [A] 它是一个用于检索的『语义探针』，不要求事实正确，只要求风格和语义接近目标文档
- [B] 它必须是事实正确的答案
- [C] 它会被直接写回语料库
- [D] 它必须与问题原文逐字匹配

**参考答案**：0

**解析**：HyDE 中的假设文档不要求事实正确，其作用是在向量空间中『指向』相关文档区域，因此更像语义探针，而非可信答案。

### single_choice · None



- [A] 先用假设文档做向量召回，再用重排序模型对召回的候选文档精排
- [B] 先用重排序，再用假设文档替换候选文档
- [C] 假设文档直接参与重排序成为最终结果
- [D] 两者不能同时使用

**参考答案**：0

**解析**：HyDE 提升的是召回阶段的查询质量，重排序作用在召回后对候选精排，两者是『召回—精排』流水线上的互补环节。
