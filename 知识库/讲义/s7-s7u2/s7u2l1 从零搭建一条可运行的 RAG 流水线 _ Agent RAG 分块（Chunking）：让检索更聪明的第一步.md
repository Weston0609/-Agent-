# s7u2l1 从零搭建一条可运行的 RAG 流水线 / Agent RAG 分块（Chunking）：让检索更聪明的第一步

> 来源 `content/lessons/s7u2l1.json`

## agent.rag.pipeline

# agent.rag.pipeline：从零搭建一条可运行的 RAG 流水线

> 一句话直觉：RAG（Retrieval-Augmented Generation，检索增强生成）就是让大模型在回答前先“查资料”，而 pipeline（流水线）就是把“查资料 → 喂给模型 → 得到答案”拆成标准步骤，让 Agent 能稳定、可替换、可调试地完成问答。

---

## 1. 为什么需要 RAG？先理解“模型不知道你的私有知识”

大语言模型（LLM, Large Language Model）的知识来自训练语料，它不知道你公司内部文档、最新政策、私人笔记。

两种常见补知识方式：

- 微调（Fine-tuning）：把知识写进模型参数，成本高、更新慢。
- RAG：把知识放在外部知识库，回答时先检索再生成，更新快、可溯源、成本低。

RAG 的核心公式可以写成：

```
用户问题 → 检索相关文档 → 把文档作为上下文 → LLM 生成答案
```

这就是一条最简 pipeline。

```python
# 一个最小 RAG 直觉示例：先检索，再拼接上下文，最后“生成”
# 注意：这里用规则函数模拟 LLM，真实场景替换为 OpenAI / 本地模型调用

knowledge_base = [
    "RAG 是检索增强生成，先检索文档再让模型回答。",
    "pipeline 是把多个处理步骤按顺序连接起来。",
    "Agent 是可以调用工具、做决策的智能体。",
]

question = "RAG 是什么？"

# 1) 检索：用最简单关键词匹配模拟
retrieved = [doc for doc in knowledge_base if "RAG" in doc]

# 2) 增强：把检索结果拼成上下文
context = "\n".join(retrieved)

# 3) 生成：真实场景应调用 LLM
answer = f"根据资料：{context}"

print(answer)
```

**关键结论**：RAG 不是“模型变聪明”，而是“模型开卷考试”。pipeline 的价值是把开卷考试的每一步标准化。

---

## 2. RAG pipeline 的五个标准阶段

工程级 RAG pipeline 通常包含：

1. **加载（Load）**：读取 PDF、Markdown、网页、数据库等原始资料。
2. **切分（Split / Chunk）**：把长文档切成小块，便于检索。
3. **嵌入（Embedding）**：把文本块转成向量（vector），让语义相近的文本在向量空间接近。
4. **检索（Retrieve）**：用用户问题向量去向量库找最相似的 top-k 文本块。
5. **生成（Generate）**：把检索结果和问题一起交给 LLM，生成最终答案。

可以把它想成一条工厂流水线：

```
原始文档 → 切分 → 向量化 → 存入向量库
用户问题 → 向量化 → 检索 top-k → 拼接 prompt → LLM → 答案
```

```python
# 用纯 Python 模拟 RAG pipeline 的五个阶段，不依赖第三方库
# 真实工程中 embedding 和向量库会换成 sentence-transformers / FAISS / Chroma 等

import math
from collections import Counter

# ---------- 阶段 1：加载 ----------
documents = [
    "RAG 是检索增强生成，它先检索相关文档，再让大模型生成答案。",
    "向量数据库用于存储文本向量，并支持相似度检索。",
    "Agent 可以调用工具，根据环境反馈做决策。",
    "pipeline 把多个处理步骤串联起来，形成可复用的工作流。",
]

# ---------- 阶段 2：切分 ----------
# 这里每句话已经很短，直接作为 chunk；真实场景按字符数或语义切分
chunks = documents

# ---------- 阶段 3：嵌入 ----------
# 用词频向量模拟 embedding，仅用于教学
def embed(text: str) -> Counter:
    # 中文按字符切分，英文按空格切分，简化处理
    tokens = text.replace("，", " ").replace("。", " ").split()
    return Counter(tokens)

chunk_vectors = [embed(c) for c in chunks]

# ---------- 阶段 4：检索 ----------
def cosine_sim(a: Counter, b: Counter) -> float:
    # 计算两个稀疏向量的余弦相似度
    common = set(a) & set(b)
    dot = sum(a[t] * b[t] for t in common)
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    return dot / (norm_a * norm_b + 1e-8)

def retrieve(query: str, top_k: int = 2):
    q_vec = embed(query)
    scored = [(cosine_sim(q_vec, c_vec), c) for c_vec, c in zip(chunk_vectors, chunks)]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:top_k]]

question = "RAG 是怎么工作的？"
top_chunks = retrieve(question)
print("检索结果：", top_chunks)

# ---------- 阶段 5：生成 ----------
# 真实场景把 prompt 发给 LLM；这里用模板模拟
prompt = f"""请根据以下资料回答问题。
资料：
{chr(10).join(top_chunks)}
问题：{question}
答案："""

print("\n构造的 Prompt：\n", prompt)
```

**关键结论**：pipeline 的每个阶段都应可单独测试、替换和观测。工程上最怕“黑盒一把梭”。

---

## 3. 切分策略：chunk 大小决定检索质量

切分（chunking）是 RAG 最容易被忽视、却最影响效果的一步。

- chunk 太小：语义不完整，检索到碎片。
- chunk 太大：噪声多，LLM 上下文浪费。
- 常见做法：按 300~800 字符切分，保留 10%~20% 重叠（overlap），避免边界语义断裂。

```python
# 一个简单的滑动窗口切分器
def split_text(text: str, chunk_size: int = 20, overlap: int = 5):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap  # 保留重叠，避免语义断裂
    return chunks

doc = "RAG 是检索增强生成。它先检索相关文档，再让大模型生成答案。pipeline 把步骤串联起来。"
for i, c in enumerate(split_text(doc)):
    print(f"chunk {i}: {c}")
```

**关键结论**：chunk 策略不是拍脑袋，要用真实问题集评估召回率（recall）和答案质量。

---

## 4. 检索：从关键词到向量，再到混合检索

检索阶段决定“能不能找到正确资料”。

- 关键词检索（BM25）：擅长精确匹配，比如专有名词、编号。
- 向量检索（dense retrieval）：擅长语义相似，比如“怎么退款”和“如何申请退钱”。
- 混合检索（hybrid retrieval）：两者结合，工程中常用。
- 重排（rerank）：先召回 top-20，再用交叉编码器（cross-encoder）精排 top-5。

```python
# 演示：关键词检索 vs 向量检索的差异
# 关键词检索命中“退款”字面；向量检索更可能命中“退钱”语义

# 简化：用字符集合重合度模拟向量语义相似度
def vec_sim(a: str, b: str) -> float:
    return len(set(a) & set(b)) / (len(set(a) | set(b)) + 1e-8)

docs = [
    "如何申请退款？",
    "怎么退钱？",
    "RAG 的 pipeline 包含检索和生成。",
]
query = "退款流程"

# 关键词：看是否包含“退款”
keyword_hits = [d for d in docs if "退款" in d]
# 向量：看字符重合度
vector_hits = sorted(docs, key=lambda d: vec_sim(query, d), reverse=True)

print("关键词检索：", keyword_hits)
print("向量检索 top-2：", vector_hits[:2])
```

**关键结论**：检索不是“越向量越好”。生产环境常做 hybrid + rerank，并记录每次检索的命中情况。

---

## 5. 生成与 Agent 化：把 pipeline 变成可调用工具

最后一步是把检索结果塞进 prompt，让 LLM 生成答案。工程要点：

- 明确指令：只根据资料回答，不知道就说不知道。
- 引用来源：让答案可追溯。
- 控制上下文长度：top-k 不是越大越好。
- Agent 化：把 RAG pipeline 封装成工具（tool），Agent 可在需要时调用。

```python
# 把 RAG pipeline 封装成一个函数，模拟 Agent 调用工具
def rag_answer(question: str, knowledge: list[str]) -> dict:
    # 简化检索：返回包含问题关键词的文档
    retrieved = [d for d in knowledge if any(ch in d for ch in question)]
    context = "\n".join(retrieved) if retrieved else "无相关资料"
    prompt = f"只根据资料回答，不知道就说不知道。\n资料：{context}\n问题：{question}"
    # 真实场景调用 LLM；这里模拟
    answer = f"（模拟 LLM）根据资料，答案是：{context}"
    return {"answer": answer, "sources": retrieved}

result = rag_answer("RAG 是什么？", documents)
print(result["answer"])
print("来源：", result["sources"])
```

**关键结论**：Agent 不直接“记住”知识，而是通过 RAG pipeline 动态获取知识。pipeline 是 Agent 的知识接口。

---

## 动手练习

**任务**：在本地实现一条最小可运行 RAG pipeline。

1. 准备 5 条你感兴趣领域的文本（比如：电影、菜谱、编程笔记）。
2. 实现 `split_text`、`embed`、`retrieve`、`generate` 四个函数。
3. 用 3 个问题测试，打印：
   - 检索到的 top-2 chunk
   - 最终 prompt
   - 模拟答案
4. 进阶：把 `embed` 换成 `sentence-transformers` 的 `all-MiniLM-L6-v2`，观察检索结果变化。

**提交物**：一个 `.py` 文件 + 一段 100 字总结：切分大小如何影响检索结果。

---

## 常见误区

- 以为 RAG 等于“把文档全塞进 prompt”：上下文有限，噪声大，成本高。
- 只关注 LLM，不关注切分和检索：检索错了，生成再强也没用。
- top-k 越大越好：错误信息会干扰 LLM。
- 没有评估：没有测试集，无法判断 pipeline 是否变好。

---

## 小结

RAG pipeline = 加载 → 切分 → 嵌入 → 检索 → 生成。

Agent 通过这条 pipeline 获得外部知识。

工程级关键在于：每一步可测试、可替换、可观测。

```python
import math
from collections import Counter

# ============================================================
# 最小可运行 RAG pipeline 示例
# 说明：用词频向量模拟 embedding，用余弦相似度模拟向量检索
# 真实工程请替换为 sentence-transformers / FAISS / Chroma + LLM API
# ============================================================

# ---------- 1. 加载 ----------
documents = [
    "RAG 是检索增强生成，它先检索相关文档，再让大模型生成答案。",
    "向量数据库用于存储文本向量，并支持相似度检索。",
    "Agent 可以调用工具，根据环境反馈做决策。",
    "pipeline 把多个处理步骤串联起来，形成可复用的工作流。",
    "切分 chunk 时保留重叠，可以避免语义在边界处断裂。",
]

# ---------- 2. 切分 ----------
def split_text(text: str, chunk_size: int = 20, overlap: int = 5):
    """滑动窗口切分，保留重叠"""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks

# 这里文档较短，直接把每句话作为一个 chunk
chunks = documents

# ---------- 3. 嵌入 ----------
def embed(text: str) -> Counter:
    """用词频向量模拟 embedding"""
    tokens = text.replace("，", " ").replace("。", " ").split()
    return Counter(tokens)

chunk_vectors = [embed(c) for c in chunks]

# ---------- 4. 检索 ----------
def cosine_sim(a: Counter, b: Counter) -> float:
    common = set(a) & set(b)
    dot = sum(a[t] * b[t] for t in common)
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    return dot / (norm_a * norm_b + 1e-8)

def retrieve(query: str, top_k: int = 2):
    q_vec = embed(query)
    scored = [(cosine_sim(q_vec, c_vec), c) for c_vec, c in zip(chunk_vectors, chunks)]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:top_k]]

# ---------- 5. 生成 ----------
def generate(question: str, top_chunks: list) -> str:
    context = "\n".join(top_chunks)
    prompt = f"请只根据资料回答问题。\n资料：\n{context}\n问题：{question}\n答案："
    # 真实场景：response = llm.invoke(prompt)
    return f"（模拟 LLM 输出）根据资料：{context}"

# ---------- 运行 ----------
if __name__ == "__main__":
    question = "RAG 是怎么工作的？"
    top_chunks = retrieve(question, top_k=2)
    answer = generate(question, top_chunks)

    print("问题：", question)
    print("\n检索到的 top-2 chunk：")
    for i, c in enumerate(top_chunks, 1):
        print(f"  {i}. {c}")
    print("\n最终答案：")
    print(answer)
```

## agent.rag.chunking

# Agent RAG 分块（Chunking）：让检索更聪明的第一步

**一句话直觉**：在 RAG（Retrieval-Augmented Generation，检索增强生成）中，分块就是把长文档切成小段，这样才能在用户提问时，精准找到“最相关”的那一小块，而不是把整本书塞给模型。

---

## 1. 为什么需要分块？（Why Chunking）

想象你在一个巨大的图书馆找一句话。如果所有书都粘成一本 10 万页的巨著，你根本没法快速定位。RAG 也一样：

- 大语言模型（LLM，Large Language Model）有上下文窗口（context window）限制，比如 8K、32K、128K token，不能塞下整本书。
- 把所有内容都塞进去，不仅贵、慢，还会让模型“注意力分散”，回答质量下降。
- 检索系统（retriever）需要把文档表示成向量（embedding），粒度太粗会导致语义模糊。

所以，**分块是 RAG 的第一道工序**：把文档切成语义相对完整的小段（chunk），再为每段生成向量，存入向量数据库（vector database）。

**关键结论**：分块质量直接决定检索质量，检索质量决定最终回答质量。

```python
# 演示：不分块 vs 分块 的检索直觉
# 假设用户问：“Python 的 GIL 是什么？”
# 不分块：整篇 100 页文档 -> 一个向量，语义太泛，可能检索不到。
# 分块后：包含“GIL 是全局解释器锁”的那一小段 -> 向量更聚焦，更容易命中。
print("分块 = 把大文档变成可检索的语义单元")
```

---

## 2. 分块的基本单位：从字符到 token

分块不是随便切。常见单位有三种：

1. **字符（character）**：最简单，`len(text)` 就是字符数。
2. **词（word）**：按空格切分，适合英文。
3. **token**：LLM 实际处理的最小单位。英文约 1 token ≈ 0.75 个单词，中文约 1 token ≈ 1~2 个汉字。

工程上，我们常用 **token 数** 来控制块大小，因为模型的上下文窗口是以 token 计的。但 tokenizer（分词器）有开销，所以原型阶段也常用字符数近似。

**关键结论**：块大小用 token 最准，但字符数在快速实验中足够用。

```python
# 示例：按字符数简单分块
text = "RAG 是检索增强生成。它先检索，再生成。分块是第一步。"
chunk_size = 10  # 每块最多 10 个字符
chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
print(chunks)
# 输出：['RAG 是检索增强', '生成。它先检索，再', '生成。分块是第一步', '。']
```

---

## 3. 三种经典分块策略

### 3.1 固定大小分块（Fixed-size Chunking）

最简单：每块固定长度，块之间可以重叠（overlap），避免边界切断语义。

- 优点：实现快、可控。
- 缺点：可能在句子中间切断，语义不完整。

```python
# 固定大小 + 重叠分块
def fixed_size_chunks(text, size=20, overlap=5):
    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        start = end - overlap  # 回退 overlap 个字符
        if start >= len(text):
            break
    return chunks

text = "RAG 是检索增强生成。它先检索，再生成。分块是第一步，决定检索质量。"
for i, c in enumerate(fixed_size_chunks(text, 15, 5)):
    print(f"块{i}: {c}")
```

### 3.2 递归字符分块（Recursive Character Chunking）

LangChain 的默认策略：按优先级尝试分隔符 `["

", "
", "。", ".", " ", ""]`，先按段落切，再按句子，最后按字符。这样尽量保持语义完整。

- 优点：语义边界更自然。
- 缺点：块大小不完全均匀。

```python
# 简化版递归分块：按句号、换行、空格依次尝试
def recursive_chunks(text, size=20):
    separators = ["\n\n", "\n", "。", " ", ""]
    def split(t, sep_idx):
        if len(t) <= size or sep_idx >= len(separators):
            return [t]
        sep = separators[sep_idx]
        parts = t.split(sep) if sep else list(t)
        result = []
        for p in parts:
            if len(p) <= size:
                result.append(p)
            else:
                result.extend(split(p, sep_idx + 1))
        return result
    return [c for c in split(text, 0) if c.strip()]

text = "RAG 是检索增强生成。\n它先检索，再生成。\n分块是第一步，决定检索质量。"
print(recursive_chunks(text, 15))
```

### 3.3 语义分块（Semantic Chunking）

用 embedding 计算相邻句子的相似度，相似度骤降处就是语义边界。

- 优点：最贴近“语义完整”。
- 缺点：计算贵、实现复杂，通常用于高质量场景。

```python
# 伪代码示意：真实使用需 embedding 模型
# 1. 把文档切成句子
# 2. 计算相邻句子 embedding 的余弦相似度
# 3. 相似度低于阈值处切分
print("语义分块：按语义相似度动态切分，效果最好但最贵")
```

**关键结论**：入门先用递归分块，追求质量再上语义分块。

---

## 4. 工程参数：块大小、重叠与元数据

实际项目中，分块不是孤立的，要配合这些参数：

| 参数 | 典型值 | 作用 |
|------|--------|------|
| chunk_size | 256~1024 token | 每块大小 |
| chunk_overlap | 10%~20% | 块间重叠，防边界丢失 |
| metadata | 来源、页码、标题 | 检索后可溯源 |

**元数据（metadata）** 非常重要：检索到块后，你可以告诉用户“这段话来自第 3 页”，提升可信度。

```python
# 带元数据的分块
chunks = fixed_size_chunks("RAG 分块示例。" * 10, size=20, overlap=5)
chunk_records = [
    {"text": c, "source": "demo.txt", "chunk_id": i}
    for i, c in enumerate(chunks)
]
print(chunk_records[0])
# {'text': 'RAG 分块示例。RAG 分块', 'source': 'demo.txt', 'chunk_id': 0}
```

---

## 5. 端到端小流程：从文档到可检索块

把上面串起来：读取文档 -> 分块 -> 加元数据 -> 生成 embedding（示意）-> 存入向量库（示意）。

```python
# 端到端示意（embedding 和向量库用占位函数）
def fake_embed(text):
    return [len(text) % 7, len(text) % 5]  # 仅演示

def build_index(text, source):
    chunks = recursive_chunks(text, size=30)
    index = []
    for i, c in enumerate(chunks):
        index.append({
            "text": c,
            "vector": fake_embed(c),
            "metadata": {"source": source, "chunk_id": i}
        })
    return index

doc = "RAG 是检索增强生成。\n分块是第一步。\n好的分块提升检索质量。"
index = build_index(doc, "demo.txt")
for item in index:
    print(item["metadata"], item["text"])
```

**关键结论**：分块是 RAG 流水线的起点，块的质量和元数据决定了后续检索与生成的上限。

---

## 动手练习

**任务**：本地实现一个 `chunk_text` 函数，满足：
1. 输入一段中文文本和 `chunk_size`（字符数）。
2. 使用递归分块策略，优先按 `

`、`
`、`。`、` ` 切分。
3. 每个块附带 `chunk_id` 和 `start_index` 元数据。
4. 打印每个块的长度和内容。

**进阶**：加入 `chunk_overlap` 参数，让相邻块有 20% 重叠。

**提交**：把你的代码和一段测试文本的运行结果贴出来。

```python
def recursive_chunks(text, size=20):
    """递归字符分块：按语义分隔符优先级切分。"""
    separators = ["\n\n", "\n", "。", " ", ""]

    def split(t, sep_idx):
        if len(t) <= size or sep_idx >= len(separators):
            return [t]
        sep = separators[sep_idx]
        parts = t.split(sep) if sep else list(t)
        result = []
        for p in parts:
            if len(p) <= size:
                result.append(p)
            else:
                result.extend(split(p, sep_idx + 1))
        return result

    return [c for c in split(text, 0) if c.strip()]


def build_index(text, source, size=30):
    """把文档分块并附上元数据，模拟向量索引结构。"""
    chunks = recursive_chunks(text, size=size)
    index = []
    for i, c in enumerate(chunks):
        index.append({
            "text": c,
            "metadata": {"source": source, "chunk_id": i}
        })
    return index


if __name__ == "__main__":
    doc = (
        "RAG 是检索增强生成。\n"
        "它先检索相关文档，再让大模型生成回答。\n"
        "分块是 RAG 的第一步，决定检索质量。\n"
        "好的分块让语义更聚焦，坏的分块会切断语义。"
    )
    index = build_index(doc, "demo.txt", size=25)
    for item in index:
        print(item["metadata"], "->", item["text"])
```


---

## 本课题目

### single_choice · None



- [A] 将用户问题直接输入大语言模型生成答案
- [B] 将用户问题转换为向量后到向量库中检索相关文档片段
- [C] 先对用户问题做关键词抽取，再去数据库做精确匹配
- [D] 把用户问题扩充为多个子问题后直接拼接成最终答案

**参考答案**：1

**解析**：RAG 管道的推理阶段，通常先把用户问题嵌入成向量，再与向量库中的文档向量做相似度检索，得到相关片段后交给大语言模型生成答案。直接输入模型无法利用外部知识；纯关键词匹配不是向量检索管道的典型第一步；问题扩充可能在多路召回中使用，但不是通用第一步。

### single_choice · None



- [A] 增大生成模型的温度参数，让答案更灵活
- [B] 在检索后增加重排序步骤，只保留与问题最相关的少量片段
- [C] 把所有检索到的片段全部拼接后交给模型，让模型自行忽略无关内容
- [D] 将向量库中的文档全部重新嵌入一次

**参考答案**：1

**解析**：检索后重排序可以基于更精细的相关性打分筛选片段，减少无关内容对生成的干扰。提高温度会增加随机性，不会提升事实相关性；全部拼接会加剧上下文噪声；重新嵌入不会自动改变片段粒度或排序质量。

### single_choice · None



- [A] 向量数据库会自动把两者对齐，检索不受影响
- [B] 文档向量和查询向量不在同一语义空间，相似度计算失去意义
- [C] 生成模型会自动纠正嵌入不一致的问题
- [D] 文档会被自动重新切分

**参考答案**：1

**解析**：不同嵌入模型产生的向量空间通常不一致，混用会导致相似度不可比，检索质量严重下降。向量数据库、生成模型和切分流程都不会自动修复该问题。

### single_choice · None



- [A] 检查提示词是否明确要求模型基于检索内容回答，以及检索片段是否真的包含答案
- [B] 直接认定向量数据库损坏，并重建整个索引
- [C] 把嵌入模型换成参数量更大的模型，不需要其他排查
- [D] 关闭检索阶段，让模型自己回答

**参考答案**：0

**解析**：检索到相关片段但答案仍错，常见原因包括提示词没有约束模型依据上下文回答、片段中实际缺少关键信息、或模型忽略上下文。应先检查这些环节，而不是直接重建索引或更换模型。

### single_choice · None



- [A] 同时使用多种检索方式（如向量检索和关键词检索）获取候选片段，再合并结果
- [B] 让多个大语言模型同时生成答案，再投票选一个
- [C] 把同一个文档重复存储多份
- [D] 让用户多次输入同一个问题以提高准确率

**参考答案**：0

**解析**：多路召回指用不同检索策略并行获取候选集并融合，以提升召回率和覆盖面。多模型投票、重复存储和重复提问都不是多路召回的含义。

### single_choice · None



- [A] 文档无法被嵌入模型处理
- [B] 片段可能在句子中间被截断，语义不完整，影响检索和生成质量
- [C] 向量数据库无法存储这些片段
- [D] 大语言模型会拒绝读取这些片段

**参考答案**：1

**解析**：固定长度切分可能切断句子或段落，破坏语义完整性，进而影响检索相关性和生成答案的质量。嵌入模型和向量库通常仍能处理，问题在于语义边界。

### single_choice · None



- [A] 召回不足
- [B] 检索结果与答案需求不匹配，属于相关性误判
- [C] 嵌入维度设置错误
- [D] 生成模型温度过高

**参考答案**：1

**解析**：语义相似不等于包含正确答案，这类情况属于检索相关性误判或答案覆盖不足。召回不足指没有检索到相关片段；嵌入维度和温度不是直接原因。

### single_choice · None



- [A] 在向量检索时结合元数据过滤，只返回满足条件的片段
- [B] 把所有文档合并成一个大文档后再检索
- [C] 让大语言模型在生成答案时自行忽略不满足条件的片段
- [D] 提高嵌入模型的维度

**参考答案**：0

**解析**：元数据过滤可以在检索阶段按来源、时间等条件缩小候选范围，是最直接有效的做法。合并文档、依赖模型忽略和高维嵌入都不能可靠实现条件筛选。

### single_choice · None



- [A] 在文档切分之前，对原始文档排序
- [B] 在向量检索返回候选片段之后、交给大语言模型生成之前
- [C] 在大语言模型生成答案之后，对答案进行排序
- [D] 在嵌入模型训练之前，对训练数据排序

**参考答案**：1

**解析**：重排序通常位于初步检索之后、生成之前，用更精细的模型对候选片段重新打分排序。切分前、生成后和嵌入训练前都不是典型位置。

### single_choice · None



- [A] 直接返回默认答案，不做检索
- [B] 结合对话历史或上下文对问题做补全和改写，再进行检索
- [C] 把问题重复多次后拼接成一个长查询
- [D] 降低向量数据库的相似度阈值到零

**参考答案**：1

**解析**：简短问题往往缺少指代和背景，结合对话历史补全或改写能显著提升检索质量。直接返回默认答案、重复拼接或把阈值降到零都不能解决语义缺失问题。

### single_choice · None



- [A] 模型回答时语气不够礼貌
- [B] 检索返回的片段中不包含回答问题所需的事实
- [C] 模型输出的格式不符合预期
- [D] 模型生成的内容过长

**参考答案**：1

**解析**：检索片段缺少所需事实属于检索阶段的问题，即没有召回正确内容。语气、格式和长度通常属于生成阶段的控制问题。

### single_choice · None



- [A] 只在系统上线时构建一次索引，之后不再更新
- [B] 建立文档更新到索引重建或增量更新的流程，使新文档能进入检索范围
- [C] 让大语言模型记住所有新文档内容
- [D] 每次用户提问时都重新训练嵌入模型

**参考答案**：1

**解析**：知识库频繁更新时，需要建立索引更新或增量更新机制，保证新文档可被检索。一次性索引会过期；模型记忆不可靠；每次请求重新训练嵌入模型不现实。

### single_choice · None



- [A] 嵌入模型无法处理任何输入
- [B] 检索到的片段可能缺失完整语境，生成答案时信息不完整
- [C] 向量数据库会拒绝存储这些片段
- [D] 大语言模型会完全无法读取检索结果

**参考答案**：1

**解析**：片段过小容易破坏语义完整性，检索出的内容可能只是局部信息，缺少回答所需上下文。嵌入模型和向量数据库通常都能处理小片段；模型也可以读取短文本，问题在于信息不完整。

### single_choice · None



- [A] 降低生成模型的最大输出长度
- [B] 增加检索返回的片段数量，即提高 top-k
- [C] 把用户问题改写成更短的句子
- [D] 关闭向量相似度计算，改为随机返回片段

**参考答案**：1

**解析**：提高 top-k 可以让检索阶段返回更多相关片段，为需要综合多文档信息的问题提供更全面的上下文。降低输出长度、缩短问题或随机返回都不能解决召回不足的问题。

### single_choice · None



- [A] 让问题变得更长，从而占用更多上下文窗口
- [B] 把口语化或含糊的问题改写成更适合检索的形式，提高召回质量
- [C] 替代向量检索，直接生成最终答案
- [D] 把问题翻译成英文，因为嵌入模型只支持英文

**参考答案**：1

**解析**：查询改写旨在弥合用户表达与文档表述之间的差距，使检索更容易命中相关内容。它不是为了占上下文、不能替代检索，也不一定要求翻译成英文。

### single_choice · None



- [A] 模型会自动忽略超出的部分并保证答案完整
- [B] 提示词会被截断或调用失败，导致部分检索信息丢失
- [C] 向量数据库会自动扩容以容纳更多片段
- [D] 嵌入模型会重新生成更短的片段

**参考答案**：1

**解析**：大语言模型有上下文窗口限制，超过后通常会被截断或直接报错，检索到的部分信息无法进入模型。模型不会自动保证完整；向量库和嵌入模型也不会因此动态调整。

### single_choice · None



- [A] 存储文档原文并支持全文检索，不涉及向量
- [B] 存储文档片段的向量表示，并支持按相似度快速检索
- [C] 负责把用户问题翻译成多种语言
- [D] 负责对大语言模型进行微调

**参考答案**：1

**解析**：向量数据库用于存储嵌入向量并支持近似最近邻搜索，是 RAG 检索阶段的核心组件。它通常不负责全文检索、翻译或模型微调。

### single_choice · None



- [A] 在检索后增加重排序，并按固定规则组织提示词中的片段顺序
- [B] 每次请求都随机打乱检索结果，以增加多样性
- [C] 关闭检索阶段，只依赖模型自身知识
- [D] 把生成模型的温度调到最高

**参考答案**：1

**解析**：重排序和固定片段组织顺序可以减少输入提示词的波动，从而提高生成答案的稳定性。随机打乱、关闭检索或提高温度都会增加不确定性。

### single_choice · None



- [A] 把文本转换为高维向量，使语义相近的文本在向量空间中距离较近
- [B] 直接生成最终的自然语言答案
- [C] 对文档进行语法纠错和拼写检查
- [D] 负责压缩向量数据库的存储空间

**参考答案**：0

**解析**：嵌入模型将文本映射为向量，用于相似度计算和检索。它不直接生成答案、不做语法纠错，也不负责存储压缩。

### single_choice · None



- [A] 在检索时加入时间过滤或时效性排序，优先返回最新文档
- [B] 提高生成模型的最大输出长度
- [C] 把用户问题翻译成英文再检索
- [D] 减少向量数据库中的文档数量

**参考答案**：1

**解析**：加入时间过滤或时效性排序可以让检索结果优先命中最新制度，直接解决旧文档干扰问题。输出长度、翻译和减少文档数量都不能针对时效性。

### single_choice · None



- [A] 减少文档的总字符数，以节省存储空间
- [B] 使每个文本片段的语义相对完整，便于检索时精准匹配相关内容
- [C] 将非结构化文本转换为结构化表格数据
- [D] 提高模型的训练速度，减少训练所需的 GPU 内存

**参考答案**：1

**解析**：分块是为了让检索粒度与语义单元对齐，使向量表示更聚焦、检索更精准，而不是单纯压缩存储或做结构化转换；分块也不涉及模型训练过程。

### single_choice · None



- [A] 文档的向量维度会发生变化，导致无法检索
- [B] 被截断的片段语义不完整，检索到后提供给模型的信息有缺失
- [C] 文件编码会出错，读取时抛出 UnicodeDecodeError
- [D] 分块数量减少，检索速度变慢

**参考答案**：1

**解析**：固定长度切分容易在语义边界之外断开，导致片段语义残缺，影响检索命中和生成质量；向量维度和编码与切分长度无关。

### multi_choice · None



- [A] 块太大时，嵌入向量会混合多个主题，检索精度可能下降
- [B] 块太小时，单个块可能缺乏足够上下文，生成答案可能不完整
- [C] 块大小不存在任何权衡，越小越好
- [D] 实际工程中常通过实验对比不同块大小来选择较优方案

**参考答案**：[0, 1, 3]

**解析**：块大小存在精度与上下文的权衡，需实验调优；「越小越好」忽略了上下文缺失的问题。

### multi_choice · None



- [A] 固定长度分块（按字符或 token）
- [B] 递归/层次化分块（先按大结构，再按小结构细分）
- [C] 基于语义相似度的分块（在语义变化处切分）
- [D] 按文件修改时间分块
- [E] 基于文档结构（标题、代码块、表格）分块

**参考答案**：[0, 1, 2, 4]

**解析**：固定长度、递归/层次、语义、结构感知都是常见策略；修改时间不是文本语义边界，不能作为分块依据。

### fill_blank · None



**参考答案**：["重叠", "overlap", "重叠区", "重叠部分"]

**解析**：重叠（overlap）让相邻块共享一部分内容，从而缓解边界处语义被截断的问题。

### fill_blank · None



**参考答案**：["字符", "字符数", "固定长度", "单词", "词"]

**解析**：递归分块逐级使用更细的分隔符，最后的兜底通常是按字符或固定长度切分。

### code_reading · None



**参考答案**：该函数按固定长度切分文本，每次取 chunk_size 个字符，然后向前移动 chunk_size - overlap 个字符，从而实现块间重叠。若 overlap 大于或等于 chunk_size，start 将不再前进甚至后退，导致死循环或产生无限重复的块。

**解析**：步长为 chunk_size - overlap，必须为正数才能保证循环推进；overlap >= chunk_size 会使步长 <= 0，导致死循环。

### code_reading · None



**参考答案**：输出近似为 ['ABCD', 'DEFG', 'GHIJ']。因为每块长度 4、重叠 1，步长为 3，依次从下标 0、3、6 开始取，最后一块被 min 截断到文本末尾。

**解析**：步长 = chunk_size - overlap = 3，起始下标为 0、3、6，分别得到 ABCD、DEFG、GHIJ（最后一块不足 4 时截断）。

### code_reading · None



**参考答案**：记录 doc_id 和块序号便于在检索到某个块后回溯其来源文档、定位原文位置，并支持按文档聚合、去重、按顺序拼接相邻块或在需要时返回父块上下文，从而提升生成答案的可解释性与完整性。

**解析**：元数据用于溯源与后处理；仅存向量和文本无法高效关联同一文档的其他块或展示引用来源。

### scenario · None



**解析**：不同文档类型适合不同粒度与结构策略：FAQ 应保持单条为块或小块，手册应结合标题层级并按结构保留表格完整，必要时对表格单独处理并配合重叠，从而提升检索精度与答案完整性。

### scenario · None



**解析**：块过大且跨越多个主题时，嵌入向量被混合语义稀释，导致与单一问题的相似度失真。改进方向包括按语义/结构边界切分，或减小块大小并配合重叠与父子策略。

### scenario · None



**解析**：改变重叠会改变每个块的文本内容，原有向量对应的文本已不一致，因此必须重新分块并重新生成嵌入，同时更新或重建向量索引，否则检索结果与文本不匹配。

### single_choice · None



- [A] 按固定长度分块一定比按段落分块检索效果更好
- [B] 按段落分块通常能保留更完整的语义单元，但块长度可能差异较大
- [C] 按段落分块不需要计算嵌入向量，因此可以省去向量数据库
- [D] 按固定长度分块无法处理英文文本，只能处理中文

**参考答案**：1

**解析**：按段落/语义分块尽量保证语义完整，但各块长度不均衡；两种方式都需要嵌入和向量检索，且均支持多语言文本。

### single_choice · None



- [A] 增加向量数据库的存储容量上限
- [B] 让跨越边界的上下文信息在相邻块中都有保留，减少信息丢失
- [C] 强制所有块的长度完全一致
- [D] 把文档翻译成另一种语言后再分块

**参考答案**：1

**解析**：重叠可以缓解边界截断造成的信息丢失，使相邻块共享部分上下文，提高检索召回的完整性；它并不改变存储上限或统一块长。

### single_choice · None



- [A] 需要检索非常具体的事实性答案，如某个型号的额定电压
- [B] 需要对整本书做主题摘要
- [C] 需要保留长篇论述的完整逻辑链条
- [D] 需要把整篇论文作为一次检索单元

**参考答案**：0

**解析**：小块更聚焦、噪声更少，适合精确定位事实型答案；摘要和长逻辑链则更适合较大的块或分层策略。

### single_choice · None



- [A] 嵌入模型无法处理短文本，会直接抛出异常
- [B] 检索到的片段可能缺失关键上下文，生成答案时依据不足
- [C] 向量数据库会自动把小块合并，导致分块失效
- [D] 文档中的数字会被自动删除

**参考答案**：1

**解析**：小块无重叠时，跨块信息被割裂，检索到的片段可能缺少必要上下文；嵌入模型可以处理短文本，也不会自动合并。

### single_choice · None



- [A] 检索时用小块定位，再把其所属的较大父块提供给生成模型
- [B] 父块只用于存储，永远不会被检索到
- [C] 子块必须比父块更长
- [D] 该策略要求父子块使用完全相同的嵌入向量

**参考答案**：0

**解析**：父子策略用小块提高检索精度，同时回传更大的父块以补充上下文；父块并非只存储，子块通常更短。

### single_choice · None



- [A] 可以完全避免生成嵌入向量
- [B] 能利用文档原有的结构信息，使每个块在语义上更内聚
- [C] 会让所有块的长度严格相等
- [D] 可以自动纠正文档中的错别字

**参考答案**：1

**解析**：Markdown 标题本身就是作者给出的语义边界，按标题切分能让块更内聚；它不消除嵌入需求，也不保证等长或纠错。

### multi_choice · None



- [A] 块的大小（字符数或 token 数）
- [B] 块与块之间是否重叠及重叠比例
- [C] 文档自身的结构（段落、标题、列表等）
- [D] 生成模型的名称是否为 GPT
- [E] 检索时返回的块数量（top-k）与块的粒度是否匹配

**参考答案**：[0, 1, 2, 4]

**解析**：块大小、重叠、文档结构、top-k 与粒度的匹配都是分块设计要素；生成模型名称与分块策略无关。

### multi_choice · None



- [A] 设置块间重叠
- [B] 优先在句子或段落边界处切分
- [C] 把整篇文档作为唯一一个块，不做切分
- [D] 使用基于 token 的切分并配合标点感知的边界规则

**参考答案**：[0, 1, 3]

**解析**：重叠、按语义边界切分、标点感知的 token 切分都能缓解断裂；把整篇作为单块会牺牲检索精度，不是缓解语义断裂的合理方案。
