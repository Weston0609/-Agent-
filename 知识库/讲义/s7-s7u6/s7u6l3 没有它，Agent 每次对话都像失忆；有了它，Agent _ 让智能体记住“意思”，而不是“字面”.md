# s7u6l3 没有它，Agent 每次对话都像失忆；有了它，Agent / 让智能体记住“意思”，而不是“字面”

> 来源 `content/lessons/s7u6l3.json`

## agent.mem.episodic

## 一句话直觉

**情景记忆（Episodic Memory）** 就是让 AI Agent（智能体）像人一样，记住“**什么时候、在哪里、发生了什么**”，并在之后需要时把这段经历**原样或摘要地取出来**用。  
没有它，Agent 每次对话都像失忆；有了它，Agent 才能“吃一堑长一智”。

---

## 1. 什么是情景记忆：从“失忆助手”说起

普通 LLM（大语言模型）的上下文窗口（Context Window）是临时的：关掉会话，一切归零。  
**情景记忆**要解决的就是：把每一次交互事件（Event）持久化下来，形成一个可按时间、按语义检索的“经历库”。

它和另外两种记忆的区别：

| 类型 | 英文 | 内容 | 例子 |
|---|---|---|---|
| 语义记忆 | Semantic Memory | 事实、概念 | “北京是中国首都” |
| 程序记忆 | Procedural Memory | 技能、步骤 | “怎么调用天气 API” |
| **情景记忆** | **Episodic Memory** | **具体经历事件** | “2024-05-01 用户让我订了去上海的票” |

> 关键结论：情景记忆 = **事件 + 时间戳 + 参与者 + 可检索**。

```python
# 一条最小的情景记忆记录：就是结构化的事件
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class Episode:
    timestamp: str          # 事件发生时间（ISO 格式）
    role: str               # 谁说的：user / agent / tool
    content: str            # 事件内容
    metadata: dict = field(default_factory=dict)  # 标签、session_id 等

# 造一条情景记忆
ep = Episode(
    timestamp=datetime.now().isoformat(),
    role="user",
    content="帮我订一张明天去上海的火车票",
    metadata={"session_id": "s001", "intent": "book_train"},
)
print(ep)
```

---

## 2. 存储：情景记忆怎么写进去

工程上，情景记忆通常存到**向量数据库（Vector Database）** 或**关系库 + 向量索引**。  
原因：检索时既要“按时间”，也要“按语义相似”。

核心流程：  
1. 事件发生 → 2. 生成文本 → 3. 调用 Embedding（嵌入）模型 → 4. 存入带向量的表。

```python
# 用内存版 FAISS 模拟向量库：把情景记忆写进去
import numpy as np

class SimpleEpisodicStore:
    def __init__(self, dim=4):
        self.dim = dim
        self.vectors = []   # 向量
        self.episodes = []  # 对应的情景

    def _embed(self, text: str):
        """真实项目请换成 OpenAI / BGE / Sentence-Transformers 的 embedding 模型。
        这里用哈希做一个可复现的玩具向量，仅用于教学。"""
        rng = np.random.default_rng(abs(hash(text)) % (2**32))
        return rng.random(self.dim)

    def add(self, episode):
        vec = self._embed(episode.content)
        self.vectors.append(vec)
        self.episodes.append(episode)

    def search(self, query: str, top_k: int = 2):
        if not self.vectors:
            return []
        q = self._embed(query)
        mat = np.stack(self.vectors)
        sims = mat @ q / (np.linalg.norm(mat, axis=1) * np.linalg.norm(q) + 1e-9)
        idx = np.argsort(-sims)[:top_k]
        return [(self.episodes[i], float(sims[i])) for i in idx]

store = SimpleEpisodicStore()
store.add(Episode("2024-05-01T10:00", "user", "我明天要从北京去上海"))
store.add(Episode("2024-05-01T10:01", "agent", "已为您查询到 G1 次列车"))
store.add(Episode("2024-05-02T09:00", "user", "上次那趟车几点发车？"))

for ep, score in store.search("去上海的火车", top_k=2):
    print(f"[{score:.3f}] {ep.timestamp} {ep.role}: {ep.content}")
```

---

## 3. 检索：情景记忆怎么被“想起来”

检索策略有三种常见组合：

1. **语义检索（Semantic Retrieval）**：按内容相似度。  
2. **时间检索（Temporal Retrieval）**：最近 N 条 / 某时间段。  
3. **混合检索（Hybrid Retrieval）**：两者加权，再加关键词过滤。

真实的 Agent 会把检索结果拼进 Prompt（提示词）里，形成“回忆上下文”。

```python
# 混合检索：语义相似度 + 时间新鲜度
def hybrid_search(store, query, top_k=2, alpha=0.7):
    results = store.search(query, top_k=len(store.episodes))
    # 按时间排序后归一化新鲜度
    episodes = [ep for ep, _ in results]
    times = sorted(range(len(episodes)), key=lambda i: episodes[i].timestamp)
    freshness = {i: rank / max(len(episodes) - 1, 1) for rank, i in enumerate(times)}
    scored = [
        (ep, alpha * sim + (1 - alpha) * freshness[i])
        for i, (ep, sim) in enumerate(results)
    ]
    scored.sort(key=lambda x: -x[1])
    return scored[:top_k]

for ep, score in hybrid_search(store, "订票经历"):
    print(f"[{score:.3f}] {ep.timestamp} {ep.content}")
```

---

## 4. 注入：把回忆放进 Agent 的决策循环

记忆只有进入 Prompt，才会影响 Agent 行为。典型做法：  
**系统提示（System Prompt）+ 检索到的情景 + 当前用户输入**。

```python
def build_prompt(user_input: str, store) -> str:
    recalled = store.search(user_input, top_k=3)
    memory_block = "\n".join(
        f"- ({ep.timestamp}) {ep.role}: {ep.content}" for ep, _ in recalled
    )
    return f"""你是一个有记忆的助手。以下是你与用户的历史经历：
{memory_block}

用户现在说：{user_input}
请结合历史经历回答。"""

print(build_prompt("上次那趟车几点发车？", store))
```

> 关键结论：情景记忆的价值 = **存得下 · 检得准 · 用得上**。三者缺一，Agent 依然“失忆”。

---

## 5. 生命周期：写入、摘要、遗忘

长期跑下去，记忆会膨胀。工程上必须处理：  
- **写入策略**：每轮都写？还是只写重要事件？  
- **摘要（Summarization）**：把多轮压缩成一条。  
- **遗忘（Forgetting）**：按时间衰减、按容量淘汰。

```python
# 简易遗忘：只保留最近 100 条
MAX_SIZE = 100

def add_with_forgetting(store, episode):
    store.add(episode)
    if len(store.episodes) > MAX_SIZE:
        store.episodes = store.episodes[-MAX_SIZE:]
        store.vectors  = store.vectors[-MAX_SIZE:]

add_with_forgetting(store, Episode("2024-05-03T12:00", "user", "谢谢") )
print("当前记忆条数:", len(store.episodes))
```

## agent.mem.semantic

# agent.mem.semantic：让智能体记住“意思”，而不是“字面”

> **一句话直觉**：如果 Agent（智能体）只按原文逐字搜索记忆，那么用户换一种说法它就“失忆”；语义记忆（semantic memory）让它按“含义”找回相关信息。

---

## 1. 为什么需要“语义记忆”？

传统程序里，记忆通常是一个字典（dict）或数据库：你存什么，就按什么键查。  
但对话型 Agent 面对的是自然语言（natural language），同一个意思可以有无数种说法：

- “我明天要去北京出差”
- “下周一我得飞一趟帝都”
- “计划去北京办点事”

如果 Agent 的记忆只存第一句，用户后面说“帮我查下帝都的天气”，字面匹配（literal matching）就找不到“北京”。  
**语义记忆（semantic memory）** 的目标是：把文本映射成向量（vector），让“意思相近”的文本在向量空间里距离也相近，从而用相似度（similarity）检索。

这一节你只需要记住一个核心结论：

> **语义记忆 = 文本嵌入（embedding）+ 向量相似度检索（vector similarity search）**

---

## 2. 从文本到向量：嵌入（Embedding）

**嵌入（embedding）** 是把一段文本变成一个固定长度的数字列表，例如 384 维或 1536 维。  
理想情况下：

- “北京”和“帝都”向量夹角很小；
- “北京”和“香蕉”向量夹角很大。

零基础阶段，我们可以先用一个轻量、离线可跑的库 `sentence-transformers`。  
下面代码会把三句话变成向量，并计算余弦相似度（cosine similarity）。

```python
# pip install sentence-transformers
from sentence_transformers import SentenceTransformer, util

# 1) 加载一个轻量嵌入模型（首次运行会自动下载）
model = SentenceTransformer("all-MiniLM-L6-v2")

# 2) 准备文本
sentences = [
    "我明天要去北京出差",
    "下周一我得飞一趟帝都",
    "我想买一根香蕉",
]

# 3) 编码为向量
embeddings = model.encode(sentences, convert_to_tensor=True)

# 4) 计算两两余弦相似度
sim_matrix = util.cos_sim(embeddings, embeddings)
print(sim_matrix)
# 你会看到第 0 句和第 1 句相似度明显高于第 0 句和第 2 句
```

**关键结论**：嵌入模型不是“关键词匹配”，而是把语义压缩进向量。  
选模型时，维度、速度、语言支持都要权衡；但教学阶段先用小模型即可。

---

## 3. 把记忆存起来：向量库（Vector Store）

有了向量，还需要一个地方存：**向量库（vector store）** 或 **向量数据库（vector database）**。  
最小实现可以用 NumPy 数组；工程级会用 FAISS、Chroma、Qdrant、Milvus 等。

语义记忆通常存两类东西：

- **原始文本**：给 LLM（大语言模型）读；
- **向量**：给检索用。

下面用 NumPy 做一个“最小语义记忆”。

```python
# pip install numpy sentence-transformers
import numpy as np
from sentence_transformers import SentenceTransformer

class SimpleSemanticMemory:
    def __init__(self, model_name="all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
        self.texts = []          # 原始记忆
        self.vectors = None      # 向量矩阵

    def add(self, text: str):
        """写入一条记忆"""
        vec = self.model.encode([text], convert_to_numpy=True)[0]
        self.texts.append(text)
        if self.vectors is None:
            self.vectors = vec.reshape(1, -1)
        else:
            self.vectors = np.vstack([self.vectors, vec])

    def search(self, query: str, top_k: int = 2):
        """按语义相似度检索"""
        q = self.model.encode([query], convert_to_numpy=True)[0]
        # 余弦相似度 = 点积 / 模长乘积
        q_norm = q / np.linalg.norm(q)
        v_norm = self.vectors / np.linalg.norm(self.vectors, axis=1, keepdims=True)
        sims = v_norm @ q_norm
        idx = np.argsort(-sims)[:top_k]
        return [(self.texts[i], float(sims[i])) for i in idx]

# 使用
mem = SimpleSemanticMemory()
mem.add("我明天要去北京出差")
mem.add("我喜欢吃香蕉")
mem.add("下周一我得飞一趟帝都")

print(mem.search("帮我查下帝都的天气"))
# 会优先命中“下周一我得飞一趟帝都”或“我明天要去北京出差”
```

**关键结论**：语义记忆的最小闭环是 `add()` 和 `search()`。  
工程上，向量库负责索引与近似最近邻（ANN, Approximate Nearest Neighbor）加速。

---

## 4. 让 Agent 用上语义记忆：写入与召回

Agent 的语义记忆一般分两步：

1. **写入（write）**：从对话中抽取值得长期记住的事实，例如“用户要去北京”。
2. **召回（recall）**：每轮对话前，用当前用户输入去检索 Top-K 相关记忆，拼进提示词（prompt）。

伪代码：

```python
# 假设 memory 是上面的 SimpleSemanticMemory

def agent_step(user_input, memory, llm):
    # 1) 召回相关记忆
    recalled = memory.search(user_input, top_k=3)
    context = "\n".join([f"- {t}" for t, _ in recalled])

    # 2) 拼 prompt
    prompt = f"""已知用户信息：
{context}

用户说：{user_input}
请回答："""

    # 3) 调 LLM（这里用假函数示意）
    answer = llm(prompt)

    # 4) 可选：把新事实写回记忆
    # memory.add(extract_fact(user_input))
    return answer
```

**关键结论**：语义记忆不是“全量塞给 LLM”，而是**按需召回**，这样既省 token（词元）又更准。

---

## 5. 工程级要注意什么？

1. **分块（chunking）**：长文本要切成合适大小的块再嵌入。
2. **元数据（metadata）**：时间、来源、用户 ID 要一起存，方便过滤。
3. **去重与更新**：用户改口时，旧记忆要能失效或覆盖。
4. **混合检索（hybrid search）**：向量 + 关键词（BM25）往往比纯向量更稳。
5. **评估（evaluation）**：用 Recall@K、MRR 等指标衡量召回质量。

**关键结论**：语义记忆是 RAG（Retrieval-Augmented Generation，检索增强生成）和长期记忆系统的基础组件。

---

## 动手练习

**任务**：实现一个“个人语义备忘录”命令行程序。

要求：

1. 用 `sentence-transformers` 的 `all-MiniLM-L6-v2` 做嵌入。
2. 支持三个命令：
   - `add <文本>`：写入记忆；
   - `search <查询>`：返回 Top-3 相似记忆及相似度；
   - `quit`：退出。
3. 额外挑战：把记忆持久化到 `memory.json`，重启后还能加载。

参考代码骨架：

```python
# memo.py
import json
import numpy as np
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")

class Memo:
    def __init__(self, path="memory.json"):
        self.path = path
        self.texts = []
        self.vectors = []
        self.load()

    def load(self):
        try:
            data = json.load(open(self.path, "r", encoding="utf-8"))
            self.texts = [d["text"] for d in data]
            self.vectors = [np.array(d["vector"]) for d in data]
        except FileNotFoundError:
            pass

    def save(self):
        data = [{"text": t, "vector": v.tolist()} for t, v in zip(self.texts, self.vectors)]
        json.dump(data, open(self.path, "w", encoding="utf-8"), ensure_ascii=False)

    def add(self, text):
        v = model.encode([text], convert_to_numpy=True)[0]
        self.texts.append(text)
        self.vectors.append(v)
        self.save()

    def search(self, query, top_k=3):
        if not self.vectors:
            return []
        q = model.encode([query], convert_to_numpy=True)[0]
        q = q / np.linalg.norm(q)
        M = np.vstack(self.vectors)
        M = M / np.linalg.norm(M, axis=1, keepdims=True)
        sims = M @ q
        idx = np.argsort(-sims)[:top_k]
        return [(self.texts[i], float(sims[i])) for i in idx]

if __name__ == "__main__":
    memo = Memo()
    while True:
        cmd = input("> ").strip()
        if cmd == "quit":
            break
        if cmd.startswith("add "):
            memo.add(cmd[4:])
            print("已记住")
        elif cmd.startswith("search "):
            for text, score in memo.search(cmd[7:]):
                print(f"{score:.3f}  {text}")
```

完成后你会得到一个可复用的语义记忆模块，后续可以接入任何 LLM 做长期记忆。


---

## 本课题目

### single_choice · None



- [A] 两者都属于情景记忆，因为它们都来自真实发生过的交互事件
- [B] 订单号属于会话上下文，退款反馈属于情景记忆，二者在时间跨度和检索方式上并不相同
- [C] 两者都属于语义记忆，因为它们都是可以被检索的事实
- [D] 只有订单号属于记忆，退款反馈不属于任何记忆类型

**参考答案**：1

**解析**：情景记忆强调对过去具体经历事件的存储与按情境/时间线索的回溯式检索。本次会话内的订单号更多是工作性的会话上下文，而跨会话的「上周退款经历」才是典型的情景记忆。把它们笼统归为同一类会混淆检索时机与生命周期，故 B 最准确。

### single_choice · None



- [A] 它存储的是与具体时间、地点、参与者绑定的经历事件，可按情景线索被重新唤起
- [B] 它存储的是通用的世界知识和概念定义，与何时习得无关
- [C] 它等同于模型权重中固化的知识，训练后不再改变
- [D] 它只能存储结构化的数值，不能存储自然语言描述

**参考答案**：0

**解析**：情景记忆的核心是「关于具体经历的事件」并带有情境线索（时间、场合、参与者）。语义记忆才是通用概念与事实；权重知识是参数化记忆，与情景记忆不同；情景记忆当然可以用自然语言存储。故 A 正确。

### multi_choice · None



- [A] 为每条经历记录时间戳与会话来源等情境线索
- [B] 设计写入策略，决定何时把交互摘要为一条事件
- [C] 设计检索策略，结合相关性与时间新鲜度排序
- [D] 考虑时效性，对过时或冲突的记忆降权或更新
- [E] 确保每条记忆都直接修改模型权重

**参考答案**：[0, 1, 2, 3]

**解析**：情景记忆模块的关键要素包括情境线索、写入策略、检索策略与时效/冲突处理。而「直接修改模型权重」不属于情景记忆的做法，情景记忆通常存于外部可检索存储，故前四项正确。

### multi_choice · None



- [A] 情景记忆绑定具体经历的时间与情境，语义记忆更关注一般性知识
- [B] 情景记忆通常按经历事件检索，语义记忆通常按概念与事实检索
- [C] 情景记忆可以随新经历不断积累，语义记忆相对更稳定
- [D] 情景记忆只能由程序硬编码，语义记忆只能由模型生成
- [E] 把情景记忆中的规律提炼出来，可以形成语义记忆

**参考答案**：[0, 1, 2, 4]

**解析**：A、B、C、E 都正确描述了二者的差异与联系：情境绑定、检索方式、稳定性、以及从经历提炼知识。D 把两者限定为「硬编码/模型生成」，是错误二分，故不选。

### multi_choice · None



- [A] 在检索打分中加入时间新鲜度，让近期经历更容易被召回
- [B] 对重要偏好做显式标记，使其在检索时获得更高权重
- [C] 把检索范围限制为仅最近一条记录
- [D] 基于会话情境（如同一会话）做过滤与提升
- [E] 彻底删除所有历史记忆以避免干扰

**参考答案**：[0, 1, 3]

**解析**：改进方向包括引入时间新鲜度、对重要内容加权、按会话情境过滤提升，这些都是情景记忆检索的合理增强。仅取最近一条会丢失信息，删除全部历史同样不合理，故 A、B、D 正确。

### multi_choice · None



- [A] 对新写入的经历设置时间戳，便于后续按新鲜度排序
- [B] 对长期未被访问的旧记忆做归档或清理
- [C] 当新旧经历冲突时，保留两者并标记冲突供后续判断
- [D] 写入后永不核对，认为情景记忆不可能出错
- [E] 对记忆做摘要以控制存储规模

**参考答案**：[0, 1, 2, 4]

**解析**：生命周期管理包括时间戳、归档清理、冲突标记与摘要压缩，以控制规模和保持可用性。认为记忆永不需核对是错误假设，故排除 D。

### fill_blank · None



**参考答案**：["情境", "情境化", "上下文", "语境"]

**解析**：情景记忆的关键在于它与具体情境（时间、场合、参与者等）绑定，这些情境线索是唤起回忆的依据。故填「情境」（或等价的「情境化/上下文」）。

### fill_blank · None



**参考答案**：["语义", "语义记忆", "semantic"]

**解析**：语义记忆存储一般性的概念、事实与知识，与情景记忆相对。题干描述正是语义记忆，故填「语义」（或「语义记忆」）。

### fill_blank · None



**参考答案**：["时间新鲜度", "新鲜度", "时间衰减", "时效性"]

**解析**：情景记忆检索常加入时间新鲜度（或时间衰减）这一情境因素，让近期经历获得更高排序。故填「时间新鲜度」或其等价说法。

### code_reading · None



**参考答案**：同时考虑了内容相关性（由 sim = similarity(query, m.text) 体现）和时间新鲜度（由 recency = 1.0 / (1.0 + (now - m.timestamp)) 体现），并用 alpha 对两者加权求和。

**解析**：sim 反映语义相关性，recency 反映时间新鲜度，二者由 alpha 组合成最终打分。这正体现了情景记忆检索中「相关性 + 情境线索」的综合排序思路。

### code_reading · None



**参考答案**：因为情景记忆以有意义的事件为单位，会话结束时写入可对整段交互做摘要，保留时间、会话来源、参与者等情境线索，同时避免逐条写入带来的噪声与存储膨胀。

**解析**：情景记忆的写入粒度是事件，会话结束是自然的边界，可产出结构化摘要并附带情境线索。逐条写入会产生大量碎片与噪声，故在会话结束时写入更合理。

### scenario · None



**解析**：应把历史交互按事件粒度做摘要并附加时间等情境线索，存入可检索的情景记忆存储；回答时按内容相关性与时间新鲜度综合检索相关事件，而非拼接全部原文；同时对过时或冲突的记忆做降权或更新。这样既能让 Agent 回溯具体经历，又能控制上下文长度。

### single_choice · None



- [A] 该品牌的词向量相似度，且必须全局扫描所有历史
- [B] 发生时间与对话情境，使这次偏好陈述能被按近期经历重新唤起
- [C] 模型的参数规模，规模越大记忆越准
- [D] 用户的账户等级，等级越高越优先

**参考答案**：1

**解析**：情景记忆依赖情境线索（尤其是时间、会话上下文）来检索具体经历。类似「三分钟前说过」这种近期经历，需要按时间/情境线索唤起，而非单纯按词向量全局扫描。参数规模和账户等级与情景记忆检索机制无关。

### scenario · None



**解析**：问题在于检索只依赖语义相似度，忽略了情景记忆赖以唤起的时间线索，导致近期经历被久远但语义相近的旧经历压制。改进可在检索打分中引入时间新鲜度并做加权综合排序，同时优先在同一会话情境内过滤/提升近期经历，从而让「刚说过的话」更容易被召回。

### single_choice · None



- [A] 两者完全对立，一个系统只能选其一实现
- [B] 情景记忆中的具体经历经过抽象和提炼后，可以逐渐沉淀为语义记忆
- [C] 语义记忆必须先于情景记忆存在，否则无法记住任何事件
- [D] 情景记忆只能存错误的经历，语义记忆只能存正确的知识

**参考答案**：1

**解析**：认知科学中一个常见观点是：反复出现的具体经历可被抽象、去情境化，逐步形成语义记忆（一般性知识）。二者并非对立，也不是以对错划分。因此 B 正确，其余选项为常见误解。

### single_choice · None



- [A] 拼接会使模型无法生成任何回复
- [B] 随会话增长上下文会超长，且缺乏按情景检索的能力，难以稳定回溯久远经历
- [C] 拼接会导致语法错误，程序无法运行
- [D] 这种做法会改变模型的权重，破坏模型

**参考答案**：1

**解析**：把全部历史原文塞进提示词会受上下文窗口限制，且没有对经历做结构化存储与检索，无法可靠地回答「上次说过什么」。它不会导致无法生成、语法错误或改变权重，故 B 正确。

### single_choice · None



- [A] 每收到一个 token 就写入一条永久记忆
- [B] 在完成一次有意义的交互事件后（如任务结束、用户表达重要偏好）进行摘要并写入
- [C] 只在程序启动时写入一次，之后不再更新
- [D] 只有当模型参数更新时才写入

**参考答案**：1

**解析**：情景记忆以「事件」为粒度，通常在完成一段有意义的交互后做摘要/结构化写入，兼顾信息量与存储成本。逐 token 写入会造成噪声与膨胀；一次性或仅随参数更新写入都不符合情景记忆的动态积累特性。

### single_choice · None



- [A] 只按时间倒序返回最近 N 条，不看相关性
- [B] 只按语义相似度检索，完全忽略时间因素
- [C] 结合语义相关性与时间新鲜度等情境线索进行综合排序
- [D] 随机抽取历史记录，以保证多样性

**参考答案**：2

**解析**：情景记忆检索常同时考虑内容相关性（语义）与情境线索（如时间新鲜度、会话来源），做综合排序。仅按时间、仅按相似度或随机抽取都各有明显缺陷，故 C 最合理。

### single_choice · None



- [A] 情景记忆应当只读，永远不能更新
- [B] 情景记忆需要处理时效性与冲突，过时经历应被降权或覆盖
- [C] 情景记忆必须加密，否则不能使用
- [D] 情景记忆和地址无关，不应存储地址

**参考答案**：1

**解析**：情景记忆会过时，系统需处理时效性与新旧冲突（如地址变更），对过时条目降权、标记或覆盖。情景记忆并非只读，也不因加密或存储类型而被禁止。故 B 正确。

### single_choice · None



- [A] 「2024-05-01 用户咨询了退货流程并最终选择换货」
- [B] 「用户在本会话中表现出对物流延迟的不满」
- [C] 「所有用户共享的物理常数与数学公理」
- [D] 「用户上周三提到他的会员将于下月到期」

**参考答案**：2

**解析**：情景记忆存储与具体时间/情境绑定的经历事件。物理常数、数学公理这类与情境无关的通用知识属于语义记忆，不适合放进情景记忆，故 C 正确。

### single_choice · None



- [A] 每条记忆都保留原始逐字对话，不做任何压缩
- [B] 把一整天的交互合并成一条无结构的超长文本
- [C] 以有意义的事件为单位，做适度摘要并保留关键线索（时间、参与者、结果）
- [D] 只存储单个关键词，丢弃所有上下文

**参考答案**：2

**解析**：情景记忆以事件为粒度、适度摘要并保留关键情境线索，兼顾可检索性与存储效率。逐字保留会膨胀且噪声大；无结构超长文本难以检索；只存关键词则丢失情境，均不合理。

### single_choice · None



- [A] 工作记忆（当前上下文窗口内的临时信息）
- [B] 情节记忆（某次具体交互发生的时间与经过）
- [C] 语义记忆（与具体会话无关的稳定事实与概念）
- [D] 程序记忆（如何执行某个技能或流程）

**参考答案**：2

**解析**：“用户对花生过敏”是与具体会话、时间无关的稳定事实，属于语义记忆。工作记忆随会话结束而消失；情节记忆记录的是“什么时候发生过什么”；程序记忆是技能性知识。

### single_choice · None



- [A] “昨天上午用户让我把报表导出成 CSV。”
- [B] “上周三的对话里用户情绪很差。”
- [C] “公司产品支持邮箱登录和企业 SSO 两种方式。”
- [D] “这次会话中用户先问了退款再问了物流。”

**参考答案**：2

**解析**：“产品支持哪些登录方式”是可复用的稳定事实，与具体某次交互无关，属于语义记忆。其余三项都绑定了具体时间或某次会话经历，属情节记忆。

### single_choice · None



- [A] 语义记忆必须依赖 RAG，二者是同一个东西
- [B] 语义记忆可以借助向量检索等技术来存取，但它是关于“记住用户/领域稳定事实”的机制，与一般文档问答的 RAG 目标不同
- [C] RAG 只能检索文档，不能用于记忆
- [D] 有了 RAG 就不需要任何记忆管理

**参考答案**：1

**解析**：二者可共享向量检索等技术，但语义记忆强调对稳定事实的抽取、更新与个性化，文档问答 RAG 侧重从知识库检索资料，目标与生命周期管理不同。

### multi_choice · None



- [A] 用户的长期饮食禁忌
- [B] 用户所在时区
- [C] 某次会话中用户随口说的“今天好累”
- [D] 产品对某项功能的稳定计费规则

**参考答案**：[0, 1, 3]

**解析**：长期禁忌、时区、稳定计费规则都是可复用的稳定事实。而“今天好累”是绑定当时情境的临时状态，属于情节性/瞬时信息，不适合长期写入语义记忆。

### multi_choice · None



- [A] 只抽取可复用、相对稳定的事实，而非逐句转存
- [B] 对同一主体的事实做冲突检测与更新
- [C] 为每条记忆保留来源与时间，便于溯源
- [D] 为了提高召回率，把所有原始对话完整无差别地塞进语义库

**参考答案**：[0, 1, 2]

**解析**：抽取稳定事实、处理冲突、保留元数据都是良好实践。无差别全量转存会带来大量冗余与噪声，反而降低检索质量，是不合理的。

### multi_choice · None



- [A] 检索结果与当前问题的语义相关性
- [B] 记忆的新鲜度/时效
- [C] 记忆之间是否相互矛盾
- [D] 把检索到的全部内容不筛选地拼进提示词

**参考答案**：[0, 1, 2]

**解析**：相关性、时效与一致性都会影响记忆可用性，需要评估。而不筛选地全量拼接会污染上下文，是应避免的反模式。

### multi_choice · None



- [A] 语义记忆侧重“是什么”的稳定事实，情节记忆侧重“何时发生过什么”的具体经历
- [B] 语义记忆通常不绑定某次具体会话，情节记忆往往绑定具体时间与事件
- [C] 语义记忆中的一条事实可能由多条情节记忆归纳而来
- [D] 情节记忆只能由人类产生，智能体无法拥有情节记忆

**参考答案**：[0, 1, 2]

**解析**：前三条准确刻画了两类记忆的差异与联系：语义记忆可由情节记忆抽象归纳而来。智能体同样可以实现情节记忆，故最后一条错误。

### fill_blank · None



**参考答案**：["语义", "含义", "语义/含义", "意思"]

**解析**：向量表示的核心在于捕捉语义；相似度衡量的是语义接近程度，因此应填“语义”（含义/意思等近义表达亦可）。

### fill_blank · None



**参考答案**：["更新", "覆盖", "替换", "update", "overwrite"]

**解析**：冲突时应以新事实更新或覆盖旧事实，并保留必要的溯源信息，避免检索到过期结论。

### code_reading · None



**参考答案**：只展示“用户喜欢用 Markdown 写周报”。因为 is_fresh 过滤掉了 2023 年的“现居北京”，而 is_relevant 认为“现居上海”与“生成周报”不相关；剩下的相关且新鲜记忆只有 Markdown 偏好这一条。

**解析**：该流程先用新鲜度筛选，再用相关性筛选，最后对冲突去重。旧地址被时效过滤，现居地虽新但与周报话题不相关，故最终只剩 Markdown 偏好。

### code_reading · None



**参考答案**：会把大量与稳定事实无关的寒暄和临时内容写入语义记忆，造成噪声与冗余，降低后续检索的相关性和准确性；真正有价值的“花生过敏”反而可能被淹没。

**解析**：语义记忆应存稳定、可复用的事实。逐条无差别转存会把“早上好”“今天天气不错”等瞬时/寒暄内容当作记忆，污染检索结果。

### single_choice · None



- [A] 压缩存储空间，降低磁盘占用
- [B] 让语义相近的内容在向量空间中距离更近，从而支持按含义检索
- [C] 对内容做加密，防止泄露
- [D] 把自然语言翻译成另一种语言

**参考答案**：1

**解析**：向量化的核心价值是语义相似度可计算：含义相近的文本向量距离近，于是可以按“意思”而不是关键词精确匹配来检索。空间压缩、加密、翻译都不是主要目的。

### single_choice · None



- [A] 每收到一条用户消息就立即无条件写入，越多越好
- [B] 只在会话结束时把整段对话原文一次性写入
- [C] 从交互中抽取稳定、可复用的事实，并附带来源与时间，必要时做去重与更新
- [D] 只要模型参数量足够大，就不需要单独的语义记忆

**参考答案**：2

**解析**：语义记忆的关键是“抽取稳定事实 + 可追溯 + 可更新”。无条件全写会引入噪声和矛盾；只存原文难以复用且冗余；模型参数无法动态、精确地记住单个用户的最新事实。

### single_choice · None



- [A] 保留两条，检索时随机返回其中一条
- [B] 用新事实更新旧事实（或将其标记为已失效），使检索只返回“现居上海”
- [C] 两条都删除，因为出现冲突
- [D] 把两条合并成“我住在北京和上海”

**参考答案**：1

**解析**：语义记忆需要处理事实更新：新信息覆盖/失效旧信息，避免检索到过期事实。随机返回、全删或强行合并都会产生错误或矛盾的知识。

### single_choice · None



- [A] 检索到的记忆应原样拼接进提示，无需任何筛选
- [B] 检索结果可能不相关或已过期，需要相关性过滤与新鲜度判断后再使用
- [C] 只要建立了语义记忆，模型就不需要系统提示了
- [D] 语义记忆只能用于问答，不能用于个性化推荐

**参考答案**：1

**解析**：检索是近似的，可能召回不相关或过时内容，因此需要过滤、打分与新鲜度判断。不筛选地拼接会污染上下文；语义记忆并不取代系统提示，其用途也远不止问答。

### single_choice · None



- [A] 替代模型推理能力
- [B] 提供跨会话的个性化事实，减少重复询问
- [C] 记录本次会话的临时状态
- [D] 对模型输出做安全审查

**参考答案**：1

**解析**：语义记忆承载用户偏好等稳定事实，使得跨会话可直接复用，减少重复澄清。它不替代推理、不是临时状态，也不承担安全审查职责。

### single_choice · None



- [A] 经确认的、稳定的用户偏好
- [B] 从寒暄和玩笑中抽取出的、被误当作事实的内容
- [C] 产品的稳定功能说明
- [D] 用户明确声明的长期约束条件

**参考答案**：1

**解析**：把寒暄、玩笑、假设语气误抽为事实，会产生错误知识并污染检索结果，是典型的记忆噪声。其余三项都是应被保留的稳定信息。

### single_choice · None



- [A] 让向量维度更高，检索更准
- [B] 支持溯源与时效判断，便于冲突时决定采信哪条、以及清理过期内容
- [C] 减少模型调用次数
- [D] 让事实自动变成情节记忆

**参考答案**：1

**解析**：来源与时间元数据用于溯源、判断新鲜度和解决冲突，是维护语义记忆一致性的关键。它不改变向量维度，也不自动转化记忆类型。

### single_choice · None



- [A] 直接回答“您之前问过，仍未解决”，无需再查
- [B] 把该条作为参考但不直接复述，优先依据最新产品政策回答，并在必要时确认上下文
- [C] 忽略该条，因为时间太久
- [D] 把该条更新为“用户已解决发票问题”

**参考答案**：1

**解析**：旧记忆可作为背景但不应直接当作答案；应结合最新政策，必要时向用户确认。直接复述旧状态可能误导；无依据地改写为“已解决”属于臆造。
