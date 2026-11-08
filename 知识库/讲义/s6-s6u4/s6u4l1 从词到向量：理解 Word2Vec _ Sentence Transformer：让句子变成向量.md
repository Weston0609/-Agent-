# s6u4l1 从词到向量：理解 Word2Vec / Sentence Transformer：让句子变成向量

> 来源 `content/lessons/s6u4l1.json`

## ai.embed.word2vec

# 从词到向量：理解 Word2Vec

## 一句话直觉

**Word2Vec（词向量）** 的目标，是把“词”变成一串数字（向量），并且让语义相近的词在向量空间里也靠得近——这样机器才能“理解”词与词之间的关系。

---

## 1. 为什么需要 Word2Vec？

传统做法把词当成离散符号（one-hot，独热编码）：

- “猫” = [1, 0, 0, ...]
- “狗” = [0, 1, 0, ...]
- “汽车” = [0, 0, 1, ...]

问题是：任意两个词的距离都一样，模型无法知道“猫”和“狗”比“猫”和“汽车”更接近。

Word2Vec 的核心思想：**一个词的含义，由它经常出现的上下文决定**（distributional hypothesis，分布式假设）。

```python
# 直观对比：one-hot 无法表达相似度
import numpy as np

cat = np.array([1, 0, 0])
dog = np.array([0, 1, 0])
car = np.array([0, 0, 1])

def cosine(a, b):
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b)))

print("猫 vs 狗:", cosine(cat, dog))   # 0.0
print("猫 vs 车:", cosine(cat, car))   # 0.0
# one-hot 下所有词都正交，无法体现语义关系
```

---

## 2. Word2Vec 的两种训练方式

Word2Vec 有两大经典架构：

### 2.1 CBOW（Continuous Bag-of-Words，连续词袋）

用**上下文词**预测**中心词**。

例如句子：“我 喜欢 吃 苹果”
- 输入：我、喜欢、苹果
- 目标：吃

### 2.2 Skip-gram（跳字模型）

用**中心词**预测**上下文词**。

- 输入：吃
- 目标：我、喜欢、苹果

> 工程经验：Skip-gram 对低频词效果更好，但训练更慢；CBOW 训练更快，适合大规模语料。

```python
# 用 gensim 训练一个最小 Word2Vec 模型
# 安装：pip install gensim
from gensim.models import Word2Vec

# 语料：每个句子是一个词列表
sentences = [
    ["我", "喜欢", "吃", "苹果"],
    ["我", "喜欢", "吃", "香蕉"],
    ["他", "喜欢", "吃", "苹果"],
    ["猫", "喜欢", "吃", "鱼"],
    ["狗", "喜欢", "吃", "肉"],
]

# sg=1 表示 Skip-gram；sg=0 表示 CBOW
model = Word2Vec(sentences, vector_size=20, window=2, min_count=1, sg=1, epochs=100)

# 查看“苹果”的向量
print(model.wv["苹果"])

# 找与“苹果”最相似的词
print(model.wv.most_similar("苹果", topn=3))
```

---

## 3. 词向量的几何意义

训练完成后，每个词是一个稠密向量（dense vector），比如 100 维、300 维。

我们可以做“词向量算术”：

> 国王 - 男人 + 女人 ≈ 女王

这体现了 Word2Vec 捕捉到的**线性语义关系**。

```python
# 假设已训练好较大语料模型
# 这里演示 API 用法（真实效果需要足够语料）
# model.wv.most_similar(positive=["国王", "女人"], negative=["男人"])

# 用余弦相似度衡量两个词
from numpy import dot
from numpy.linalg import norm

v1 = model.wv["苹果"]
v2 = model.wv["香蕉"]

cos_sim = dot(v1, v2) / (norm(v1) * norm(v2))
print("苹果 vs 香蕉 相似度:", cos_sim)
```

---

## 4. 训练参数与工程要点

常见参数：

| 参数 | 含义 | 建议 |
|---|---|---|
| `vector_size` | 向量维度 | 100~300 常用 |
| `window` | 上下文窗口大小 | 5 左右常用 |
| `min_count` | 忽略低频词 | 至少 1，通常 5 |
| `sg` | 0=CBOW，1=Skip-gram | 视任务而定 |
| `negative` | 负采样数量 | 5~20 |
| `epochs` | 训练轮数 | 5~20 |

**负采样（negative sampling）**：Word2Vec 不直接做 softmax（输出维度=词表大小），而是把问题变成二分类，随机抽一些“负样本”词，大幅加速训练。

```python
# 展示常用参数配置
model = Word2Vec(
    sentences,
    vector_size=100,   # 向量维度
    window=5,          # 上下文窗口
    min_count=5,       # 忽略出现次数少于5的词
    sg=1,              # Skip-gram
    negative=5,        # 负采样
    epochs=10,
    workers=4,         # 并行线程
)
```

---

## 5. Word2Vec 的局限与后续发展

局限：

1. **静态向量**：一个词只有一个向量，无法处理多义词（“苹果”公司 vs 水果）。
2. **依赖语料**：语料质量决定效果。
3. **无法处理未登录词（OOV，Out-of-Vocabulary）**：没见过的词没有向量。

后续发展：

- **GloVe（Global Vectors）**：基于全局共现矩阵。
- **FastText**：引入子词（subword），缓解 OOV。
- **ELMo / BERT**：上下文相关（contextualized）词向量，一个词在不同句子中向量不同。

```python
# FastText 可以处理未登录词（通过子词）
# from gensim.models import FastText
# ft = FastText(sentences, vector_size=20, min_count=1)
# print(ft.wv["苹果派"])   # 即使没出现过，也能得到向量
```

---

## 动手练习

**任务：用 Word2Vec 找“语义最近邻”**

1. 准备一个小语料：自己写 20~30 个中文句子，主题围绕“水果、动物、交通工具”。
2. 用 `gensim` 训练一个 Word2Vec 模型（`vector_size=50, window=3, min_count=1, sg=1`）。
3. 完成以下操作：
   - 输出“苹果”的向量前 5 维。
   - 找出与“苹果”最相似的 3 个词。
   - 计算“猫”和“狗”的余弦相似度，并与“猫”和“汽车”的相似度对比。
4. 思考：为什么在你的小语料上效果可能不理想？语料规模对 Word2Vec 有什么影响？

**提交形式**：一段可运行 Python 脚本 + 一段简短分析（200 字以内）。

## ai.embed.sentence_transformer

# Sentence Transformer：让句子变成向量

> 一句话直觉：计算机读不懂“你好”和“Hello”为什么意思相近，Sentence Transformer（句子转换器）就是把一句自然语言压成一串数字向量，让“意思相近的句子，向量也相近”，从而让机器能算相似度、做检索、做聚类、做推荐。

本讲义面向零基础到工程级，目标是在 40 分钟内让你理解它是什么、为什么有效、怎么用、怎么落地，并能自己写出一个小型语义检索 Demo。

---

## 1. 从“词向量”到“句向量”：为什么要专门学 Sentence Transformer

传统 NLP（Natural Language Processing，自然语言处理）里，词可以被表示成向量，例如 Word2Vec、GloVe。但工程中我们真正处理的是句子、段落、文档。

朴素做法是把句子中每个词的词向量求平均。问题是：

- “狗咬人”和“人咬狗”词一样，平均后几乎一样，但语义完全不同。
- “我不喜欢这部电影”和“我喜欢这部电影”也会被平均得非常接近。

所以我们需要一个模型，直接输入整句，输出一个固定长度的句向量（sentence embedding，句子嵌入）。Sentence Transformer 就是这类模型的代表。

它的核心思想是：用 Transformer（一种基于自注意力机制的神经网络架构）编码句子，再通过对比学习（contrastive learning）训练，让语义相近的句子在向量空间里靠近，语义不同的句子远离。

```python
# 先建立直觉：句子可以由模型编码成向量
# 这里只演示概念，不依赖联网下载模型
sentences = ["猫坐在垫子上", "一只猫在垫子上休息", "今天天气很好"]

# 假设我们已经有一个编码函数 encode(text) -> list[float]
# 真实模型会在后文使用 sentence-transformers 库加载
print("我们要把每句话变成一个固定长度向量")
print("然后比较向量之间的距离，距离越小，语义越相似")
```

---

## 2. 核心机制：Transformer 编码 + 池化 + 对比学习

Sentence Transformer 通常由三部分组成：

1. **Transformer 编码器（Transformer Encoder）**：把输入 token（词元）序列变成上下文相关的 token 向量。
2. **池化层（Pooling）**：把多个 token 向量压成一个句向量。常见有 CLS pooling、Mean pooling、Max pooling。
3. **训练目标（Training Objective）**：常用对比学习，让正样本对（语义相近）向量更近，负样本对更远。

你可以把它理解成：

```text
句子 -> 分词 -> Transformer -> 每个 token 一个向量 -> 池化 -> 一个句向量
```

工程上最常用的是 Mean pooling：对所有 token 向量取平均。

```python
import numpy as np

# 模拟 Transformer 输出：3 个 token，每个 token 是 4 维向量
token_embeddings = np.array([
    [0.1, 0.2, 0.3, 0.4],
    [0.2, 0.1, 0.4, 0.3],
    [0.3, 0.3, 0.2, 0.2],
])

# Mean pooling：按 token 维度求平均，得到一个句向量
sentence_embedding = token_embeddings.mean(axis=0)
print(sentence_embedding)  # [0.2 0.2 0.3 0.3]
```

关键结论：句向量不是简单词向量平均，而是经过上下文编码后的 Token 向量再做池化。

---

## 3. 最常用工具：sentence-transformers 库

实际开发中，我们很少从零训练，而是直接使用 `sentence-transformers` 库加载预训练模型。

安装：

```bash
pip install -U sentence-transformers
```

最小可用代码：

```python
from sentence_transformers import SentenceTransformer

# 加载一个轻量多语言模型，第一次运行会自动下载
model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

sentences = [
    "猫坐在垫子上",
    "一只猫在垫子上休息",
    "今天天气很好",
]

# 编码：输出形状为 (句子数, 向量维度)
embeddings = model.encode(sentences)
print(embeddings.shape)
print(embeddings[0][:5])
```

这里模型名 `paraphrase-multilingual-MiniLM-L12-v2` 的意思是：

- `paraphrase`：面向释义/相似句任务训练。
- `multilingual`：多语言。
- `MiniLM-L12`：较小的 Transformer 结构，适合工程部署。

关键结论：工程中优先选“任务匹配 + 语言匹配 + 体积可接受”的预训练模型。

---

## 4. 怎么用：相似度、检索、聚类

得到句向量后，最常用的操作是余弦相似度（cosine similarity）。

公式：

```text
cos(a, b) = a · b / (||a|| * ||b||)
```

范围通常在 -1 到 1，越接近 1 越相似。

```python
from sentence_transformers import SentenceTransformer, util

model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

sentences = [
    "猫坐在垫子上",
    "一只猫在垫子上休息",
    "今天天气很好",
]

embeddings = model.encode(sentences, convert_to_tensor=True)

# 计算第 0 句和第 1 句的余弦相似度
sim_01 = util.cos_sim(embeddings[0], embeddings[1])
# 计算第 0 句和第 2 句的余弦相似度
sim_02 = util.cos_sim(embeddings[0], embeddings[2])

print("0 和 1 相似度：", sim_01.item())
print("0 和 2 相似度：", sim_02.item())
```

工程级最小检索系统：

```python
from sentence_transformers import SentenceTransformer, util

model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

# 知识库文档
docs = [
    "Python 是一种编程语言",
    "猫科动物包括猫、狮子和老虎",
    "余弦相似度用于衡量向量方向接近程度",
    "北京是中国的首都",
]

doc_embeddings = model.encode(docs, convert_to_tensor=True)

query = "哪种动物属于猫科？"
query_embedding = model.encode(query, convert_to_tensor=True)

# 计算查询与所有文档的相似度
scores = util.cos_sim(query_embedding, doc_embeddings)[0]

# 取最相似的前 2 个
best = scores.topk(k=2)
for score, idx in zip(best.values, best.indices):
    print(f"相似度={score:.4f} 文档={docs[idx]}")
```

关键结论：句向量把“语义匹配”变成了“向量近邻搜索”。

---

## 5. 工程级注意点：归一化、批处理、模型选择与部署

当你从 Demo 走向生产，要关注这些点：

1. **归一化（Normalization）**：很多模型输出未归一化，做余弦相似度前最好 `normalize_embeddings=True`。
2. **批处理（Batching）**：`encode` 支持批量输入，显著提升吞吐。
3. **向量维度与存储**：句向量通常是 384、512、768 维，存入向量数据库（Vector Database）如 FAISS、Milvus、Chroma。
4. **模型选择**：
   - 多语言：`paraphrase-multilingual-*`
   - 英文检索：`all-MiniLM-L6-v2`、`multi-qa-MiniLM-L6-cos-v1`
   - 高精度：`BAAI/bge-*`、`intfloat/e5-*`
5. **版本与缓存**：模型首次下载后会缓存，生产环境要固定版本，避免行为漂移。

```python
from sentence_transformers import SentenceTransformer
import numpy as np

model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

sentences = ["句子一", "句子二", "句子三"]

# normalize_embeddings=True 让向量长度为 1，之后点积等于余弦相似度
embeddings = model.encode(
    sentences,
    batch_size=32,
    normalize_embeddings=True,
    show_progress_bar=False,
)

# 因为已归一化，点积就是余弦相似度
sim_matrix = np.dot(embeddings, embeddings.T)
print(sim_matrix)
```

关键结论：生产环境要固定模型、归一化向量、批量编码，并配合向量数据库做近邻搜索。

---

## 6. 常见对比：Sentence Transformer 与普通 Transformer

普通 BERT（Bidirectional Encoder Representations from Transformers）输出的是 token 级向量，直接拿 CLS 向量做句子相似度效果往往一般，因为没有专门为句子相似度训练。

Sentence Transformer 通过孪生网络（Siamese Network）或对比学习，把“句子对是否相似”作为训练目标，因此更适合：

- 语义搜索（Semantic Search）
- 文本聚类（Text Clustering）
- 去重（Deduplication）
- 推荐召回（Recommendation Retrieval）
- RAG（Retrieval-Augmented Generation，检索增强生成）中的召回阶段

```python
# 伪代码对比：普通 BERT 取 CLS 和 Sentence Transformer 的差异
# 普通 BERT：
# outputs = bert_model(input_ids)
# cls_vector = outputs.last_hidden_state[:, 0, :]
# 问题：CLS 向量未必适合余弦相似度

# Sentence Transformer：
# embedding = model.encode("句子")
# 优点：直接为句子相似度优化，开箱即用
print("做语义相似度任务，优先用 Sentence Transformer")
```

---

## 7. 动手练习

**任务：搭建一个本地“迷你语义搜索”脚本。**

要求：

1. 安装 `sentence-transformers`。
2. 准备至少 8 条中文短句作为知识库，主题可以是你喜欢的电影、书籍或技术概念。
3. 用 `paraphrase-multilingual-MiniLM-L12-v2` 编码知识库。
4. 输入一个查询句，输出相似度最高的前 3 条。
5. 把 `normalize_embeddings=True` 打开，并解释为什么余弦相似度仍然正确。
6. 额外挑战：把知识库向量保存为 `.npy` 文件，下次直接加载，不重复编码。

示例骨架：

```python
from sentence_transformers import SentenceTransformer, util
import numpy as np

model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

docs = [
    "替换成你的第 1 条知识",
    "替换成你的第 2 条知识",
    # ... 至少 8 条
]

doc_emb = model.encode(docs, normalize_embeddings=True, convert_to_tensor=True)
query = "输入你的查询句"
query_emb = model.encode(query, normalize_embeddings=True, convert_to_tensor=True)

scores = util.cos_sim(query_emb, doc_emb)[0]
top = scores.topk(k=3)
for s, i in zip(top.values, top.indices):
    print(f"{s:.4f}\t{docs[i]}")

# 保存与加载
np.save("doc_emb.npy", doc_emb.cpu().numpy())
loaded = np.load("doc_emb.npy")
print(loaded.shape)
```

完成后你应该能回答：

- 为什么句向量能表示语义？
- 为什么需要池化？
- 为什么余弦相似度适合句向量？
- 生产中如何选模型和存向量？

如果这四点都清晰，你已经掌握了 Sentence Transformer 的核心。


---

## 本课题目

### single_choice · None



- [A] 给定中心词，预测它周围的上下文词
- [B] 给定上下文词，预测中心词
- [C] 给定一个句子，预测整句的情感极性
- [D] 给定两个词，直接输出它们的余弦相似度

**参考答案**：0

**解析**：Skip-gram 的核心思想是用中心词预测上下文词；选项 B 是 CBOW 的目标，C、D 均不是 Word2Vec 的训练目标。

### single_choice · None



- [A] 每个中心词会关联到更远的上下文词，学到的共现关系范围更广
- [B] 词表大小会立即增大 5 倍
- [C] 模型会自动从 Skip-gram 切换为 CBOW
- [D] 训练得到的词向量维度会自动变为 10

**参考答案**：0

**解析**：窗口大小决定中心词与上下文词的最大距离；窗口越大，纳入的上下文越远，但不会改变词表、模型结构或向量维度。

### single_choice · None



- [A] Skip-gram
- [B] CBOW
- [C] 词袋模型
- [D] TF-IDF

**参考答案**：0

**解析**：Skip-gram 用中心词预测上下文，对低频词和词序信息通常表现更好；CBOW 更平滑、训练更快但低频词效果往往稍弱；词袋和 TF-IDF 不是 Word2Vec 的模型变体。

### single_choice · None



- [A] 使用负采样或层次 softmax 替代完整 softmax
- [B] 把向量维度设置为 1
- [C] 把窗口大小设置为 0
- [D] 删除所有高频词

**参考答案**：0

**解析**：负采样和层次 softmax 都是加速训练、近似完整 softmax 的常用方法；维度设为 1、窗口设为 0 或删除高频词会破坏训练效果或目标。

### single_choice · None



- [A] 词向量可以通过语义类比任务进行定性评估，例如“国王 - 男人 + 女人”接近“女王”
- [B] 词向量的每一维都严格对应一个语法标签
- [C] 词向量训练完成后不能再用于其他下游任务
- [D] 词向量只能用于英文，不能用于中文

**参考答案**：0

**解析**：词向量的语义类比是经典评估方式；每一维通常不可解释，词向量可迁移到多种下游任务，也不限语言。

### single_choice · None



- [A] 训练模型从 Skip-gram 切换为 CBOW
- [B] 训练模型从 CBOW 切换为 Skip-gram
- [C] 窗口大小自动变为 0
- [D] 负采样被自动关闭

**参考答案**：0

**解析**：在常见实现中，sg=1 表示 Skip-gram，sg=0 表示 CBOW；该参数不控制窗口大小或负采样。

### single_choice · None



- [A] 训练语料的领域与下游任务差异很大
- [B] 训练语料规模较大且覆盖面广
- [C] 根据任务调整了窗口大小
- [D] 对语料进行了分词和去噪

**参考答案**：0

**解析**：词向量会继承训练语料的领域分布，领域差异大时迁移效果可能差；其余选项通常是正面做法。

### single_choice · None



- [A] 对共现统计影响不大，词向量整体仍然可以正常训练
- [B] 词表大小会立即变为 0
- [C] Skip-gram 会自动变成 CBOW
- [D] 所有词向量都会变成零向量

**参考答案**：0

**解析**：Word2Vec 主要依赖局部窗口内的共现关系，句子整体顺序对训练影响有限；它不会改变词表、模型类型或使向量归零。

### single_choice · None



- [A] Word2Vec 学习低维稠密词向量，而词袋模型通常产生高维稀疏表示
- [B] Word2Vec 不能用于文本分类，词袋模型可以
- [C] Word2Vec 不需要语料，词袋模型需要语料
- [D] Word2Vec 只能处理英文，词袋模型只能处理中文

**参考答案**：0

**解析**：Word2Vec 的输出是低维稠密向量，词袋模型通常是高维稀疏计数或权重向量；两者都可以用于文本分类，也都需要语料，且不限语言。

### single_choice · None



- [A] 模型尚未充分学习共现统计，词向量质量可能较差
- [B] 词表大小会自动缩小
- [C] 窗口大小会自动变大
- [D] 负采样会自动关闭

**参考答案**：0

**解析**：迭代次数不足会导致模型欠拟合；它不会改变词表、窗口或负采样设置。

### single_choice · None



- [A] 对高频词进行下采样（subsampling）
- [B] 把向量维度设置为 1
- [C] 把窗口大小设置为整个语料长度
- [D] 删除所有低频词

**参考答案**：0

**解析**：下采样可以降低高频词在训练中的权重，缓解其主导问题；其余选项会破坏训练或与目标无关。

### single_choice · None



- [A] 它们在训练语料中经常出现在相似的上下文里
- [B] 它们的词向量维度完全相同
- [C] 它们的词频完全相同
- [D] 它们的词表下标相邻

**参考答案**：0

**解析**：Word2Vec 基于分布式假设，上下文相似会导致词向量相似；维度相同是普遍现象，词频和下标的接近并不决定语义相似度。

### single_choice · None



- [A] 输入是多个上下文词，输出是中心词
- [B] 输入是中心词，输出是多个上下文词
- [C] 输入是整篇文档，输出是文档主题
- [D] 输入是词向量，输出是词频统计

**参考答案**：0

**解析**：CBOW 使用上下文词预测中心词；选项 B 是 Skip-gram 的方向，C、D 与该模型无关。

### single_choice · None



- [A] 在大规模通用语料上训练的词向量可以作为下游任务的初始化或特征输入
- [B] 词向量一旦训练完成，只能用于训练时使用的那个任务
- [C] 词向量不能用于任何深度学习模型
- [D] 词向量必须与训练时的词表完全一致才能在任何任务中使用

**参考答案**：0

**解析**：预训练词向量常被迁移到下游任务作为初始化或特征；它不限于原任务，也可用于深度学习模型，词表可以按需裁剪或映射。

### single_choice · None



- [A] 每个中心词只能看到紧邻的一个或两个上下文词，学到的共现范围很局部
- [B] 模型会自动退化为 CBOW
- [C] 词表会只保留相邻词
- [D] 训练会立即报错，无法进行

**参考答案**：0

**解析**：窗口大小为 1 表示只考虑紧邻上下文，共现范围很局部；它不会自动切换模型、裁剪词表或导致训练必然失败。

### single_choice · None



- [A] 语义相近的词在向量空间中距离通常较近
- [B] 每个词向量的每一维都对应一个可解释的语义属性
- [C] 词向量的维度必须等于训练语料的词表大小
- [D] 词向量一经训练就与上下文完全无关，无法体现多义词

**参考答案**：0

**解析**：Word2Vec 的分布式假设使语义相近的词向量相近；每一维通常不可单独解释，维度不等于词表大小，且静态词向量确实难以处理多义词，但这不是“符合实际特性”的最佳正向描述。

### single_choice · None



- [A] 每个词向量的长度变为 300 个浮点数，模型参数量增加
- [B] 词表会被截断为 300 个词
- [C] 窗口大小会自动调整为 300
- [D] 训练目标会从 Skip-gram 变为 CBOW

**参考答案**：0

**解析**：向量维度决定每个词向量的长度和模型参数量；它不影响词表大小、窗口大小或训练目标。

### single_choice · None



- [A] 原始 Word2Vec 为每个词只学习一个固定向量，无法根据上下文区分多义词
- [B] 训练语料中没有出现“苹果”这个词
- [C] 窗口大小设置得太小，导致无法训练
- [D] 向量维度设置得太大，导致多义词被合并

**参考答案**：0

**解析**：原始 Word2Vec 的词向量是静态的，同一个词只有一个向量；语料中出现与否、窗口和维度都不是该现象的根本原因。

### single_choice · None



- [A] 使用规模很小且领域非常单一的语料进行训练
- [B] 使用较大的语料并保留足够的迭代次数
- [C] 根据任务调整窗口大小和向量维度
- [D] 对语料进行基本的清洗和分词

**参考答案**：0

**解析**：Word2Vec 依赖大量共现统计，语料过小或过于单一会导致词向量覆盖不足、质量差；其余选项通常是提升质量的常规做法。

### single_choice · None



- [A] 通过只更新少量负样本，降低每次训练的计算量
- [B] 把词表大小减少到原来的负样本数量
- [C] 把 Skip-gram 自动转换为 CBOW
- [D] 保证每个词向量都是单位向量

**参考答案**：0

**解析**：负采样通过随机抽取少量负样本近似原来的 softmax，从而降低计算开销；它不改变词表大小、模型方向，也不强制单位化。

### single_choice · None



- [A] 常用余弦相似度衡量两个词向量在方向上的接近程度
- [B] 必须使用欧氏距离，且值越大表示越相似
- [C] 相似度只能通过查词表下标差值得到
- [D] 相似度与训练语料无关，只由向量维度决定

**参考答案**：0

**解析**：余弦相似度是词向量相似度计算的常用方式；欧氏距离并非唯一选择，词表下标和维度都不能直接决定语义相似度。

### single_choice · None



- [A] 低频词会被丢弃，词表变小
- [B] 所有词都会被保留，但向量维度变大
- [C] 窗口大小会自动增大
- [D] 训练目标会改为预测句子顺序

**参考答案**：0

**解析**：min_count 用于过滤出现次数低于阈值的词，因此词表会变小；它不影响维度、窗口或训练目标。

### single_choice · None



- [A] 点积与余弦相似度完全相同，不会有任何问题
- [B] 点积会受向量模长影响，短向量或长向量会扭曲相似度排序
- [C] 点积只能用于二分类，不能用于相似度比较
- [D] 点积要求两个向量维度不同才能计算

**参考答案**：1

**解析**：余弦相似度会除以两个向量的模长，消除长度影响；而点积不归一化，当不同句子的向量模长差异较大时，点积值会被模长主导，从而扭曲相似度排序。若想用点积近似余弦相似度，通常需要先对向量做 L2 归一化。

### single_choice · None



- [A] 句向量模型可以无限接收任意长度的文本，不需要截断
- [B] 模型通常有最大序列长度限制，超长文本会被截断，可能导致语义信息丢失
- [C] 只要文本是中文，就不会有长度限制
- [D] 长度限制只影响训练，不影响推理

**参考答案**：1

**解析**：基于 Transformer 的句向量模型一般有最大序列长度（如 512 个 token）。超过该长度的输入会被截断，被截掉的部分信息不会参与编码，因此长文本的语义可能丢失。推理阶段同样受此限制，并非只影响训练。

### multi_choice · None



- [A] 对向量做 L2 归一化后使用内积/余弦相似度
- [B] 根据业务数据对模型进行微调
- [C] 使用适合该任务的池化方式（如平均池化或取 [CLS]）
- [D] 把所有句子都截断到 1 个字符以节省空间
- [E] 对 query 和 document 使用同一种编码模型与同一套预处理

**参考答案**：[0, 1, 2, 4]

**解析**：归一化、任务相关微调、合适的池化、以及 query/document 编码方式一致，都有助于让相似度更可靠。把句子截断到 1 个字符会丢失几乎全部语义，严重损害召回。

### multi_choice · None



- [A] 推理时通常关闭 dropout，保证输出确定性
- [B] 训练时可能会使用对比学习等目标来拉近正样本、推远负样本
- [C] 推理时不需要标签，只要把文本编码成向量
- [D] 推理时必须和训练一样进行反向传播

**参考答案**：[0, 1, 2]

**解析**：推理阶段关闭 dropout 以保证稳定输出，不需要标签，也不进行反向传播；训练阶段常用对比学习类目标优化向量空间。推理时做反向传播既无必要也浪费计算。

### multi_choice · None



- [A] 输入文本远超模型最大长度而被截断
- [B] query 与 document 使用了不同的编码模型
- [C] 向量未归一化却用内积比较
- [D] 把相似度阈值当成固定不变的通用常数
- [E] 对输入文本做了与模型训练时一致的预处理

**参考答案**：[0, 1, 2, 3]

**解析**：截断丢信息、编码模型不一致、未归一化用内积、把阈值当通用常数，都会让相似度判断失真。与训练一致的预处理是正确做法，不会导致不合理结果。

### multi_choice · None



- [A] 对向量建立近似最近邻索引以加速大规模检索
- [B] 对高频 query 的向量做缓存
- [C] 监控编码延迟与召回指标
- [D] 把模型输出向量维度随意改成任意值而不重新训练

**参考答案**：[0, 1, 2]

**解析**：ANN 索引、缓存、监控都是常见的生产优化手段。随意改变输出维度会破坏与已训练模型的一致性，除非使用专门的降维/投影方法，否则不可取。

### fill_blank · None



**参考答案**：["L2", "l2", "欧几里得", "二范数"]

**解析**：L2 归一化把向量缩放到单位长度，此时两向量内积等于余弦相似度。也有写「二范数归一化」「欧几里得归一化」的说法。

### fill_blank · None



**参考答案**：["池化", "pooling", "汇聚"]

**解析**：池化（pooling）是把变长的 token 序列表示聚合成固定维度句子向量的操作，常见形式有平均池化、最大池化和取 [CLS] 位置。

### code_reading · None



**参考答案**：未做 L2 归一化时，内积会受向量模长影响，不能等价于余弦相似度。若想与余弦相似度一致，应先对 emb 做 L2 归一化再计算内积。

**解析**：内积等于模长乘积乘以夹角余弦。未归一化时，模长差异会主导结果，使相似度排序被长度影响。归一化后内积才等于余弦相似度。

### code_reading · None



**参考答案**：逐条编码（batch_size=1）通常不改变单条句子的语义表示，但吞吐量低、耗时更长；增大 batch 能利用并行提升吞吐，在不超显存的前提下一般不改变单条语义。

**解析**：batch size 主要影响编码效率，对单条句子的向量表示通常没有本质影响（前提是推理模式且无随机性）。batch_size=1 会显著降低吞吐。

### scenario · None



**解析**：通用句向量模型在通用语料上训练，对领域内细粒度差异（如「手机壳」与「手机」）区分不足。可通过使用领域数据微调、构造困难负样本进行对比学习、调整相似度阈值、增加重排或关键词过滤等手段提高区分度。

### scenario · None



**解析**：延迟随库规模上升通常是因为线性扫描全部向量。可构建近似最近邻（ANN）向量索引、对高频查询做向量缓存、使用批处理与 GPU 加速编码、必要时降低向量维度或做量化。

### single_choice · None



- [A] 把向量维度降低到 1
- [B] 对每个向量做 L2 归一化后再计算内积
- [C] 把向量中所有负值置为 0
- [D] 对向量做标准化使均值为 0、方差为 1

**参考答案**：1

**解析**：当两个向量都做了 L2 归一化（模长为 1）后，内积就等于余弦相似度。因此归一化是让内积检索与余弦相似度一致的标准做法。降维、ReLU 截断或按特征做标准化都不能保证模长为 1。

### single_choice · None



- [A] 模型在推理时默认是确定性的，相同输入得到相同输出，这是正常现象
- [B] 模型出错了，应该每次都有随机性
- [C] 模型没有加载成功
- [D] 模型的向量维度设置错了

**参考答案**：0

**解析**：在推理/编码阶段，模型通常关闭 dropout 等随机机制，且不采样，因此相同输入会稳定地得到相同输出。这是可复现性的正常表现，不代表模型出错或没加载成功。

### single_choice · None



- [A] 把 batch size 设为 1，逐条编码
- [B] 使用较大的 batch 并行编码，并视情况使用 GPU
- [C] 把所有句子拼成一个超长字符串再编码
- [D] 对每条句子多次编码后取平均

**参考答案**：1

**解析**：批量编码能充分利用硬件并行能力，提升吞吐量；在显存允许范围内增大 batch 通常不改变单条句子的语义表示。逐条编码效率低；拼接会破坏句子边界；多次编码取平均既慢又不必要。

### single_choice · None



- [A] 直接使用，不需要考虑训练任务与使用场景是否匹配
- [B] 换用或微调一个更适合非对称检索（query-document）的句向量模型
- [C] 把问题和文档都截断到 10 个字符
- [D] 对文档向量做随机打乱

**参考答案**：1

**解析**：对称相似度任务（如 STS）与非对称检索任务（query 短、document 长）的分布不同。在对称任务上训练的模型直接用于非对称检索，召回质量可能明显下降。更合理的做法是选用专门为非对称检索训练/微调的模型。

### single_choice · None



- [A] 池化是为了把 token 级别的表示聚合成一个固定维度的句子向量
- [B] 池化是为了增加向量的维度
- [C] 池化是为了把句子翻译成另一种语言
- [D] 池化是为了随机丢弃一半的 token

**参考答案**：0

**解析**：Transformer 输出的是每个 token 的向量，需要经过池化（如取 [CLS]、平均池化、最大池化）聚合成一个固定维度的句子级向量，才能用于句子相似度等任务。池化不改变模型设计的目标维度语义，也不是翻译或随机丢弃。

### single_choice · None



- [A] 检索速度通常变快，存储变小，但语义区分能力可能有所下降
- [B] 检索速度一定变慢，因为维度更少计算更复杂
- [C] 语义区分能力一定提升，因为维度更低更紧凑
- [D] 模型会直接报错，无法运行

**参考答案**：0

**解析**：降低向量维度通常减少存储与计算开销、提升检索速度，但会损失部分语义信息，导致区分能力下降。维度降低并不会让计算更复杂，也不能保证区分能力提升。

### single_choice · None



- [A] 取值范围是 [0, 1]，不可能为负
- [B] 取值范围是 [-1, 1]，1 表示方向完全相同，-1 表示方向完全相反
- [C] 取值范围是 [0, 100]，用于表示百分比
- [D] 取值范围是 (-∞, +∞)，没有上界

**参考答案**：1

**解析**：余弦相似度是两个向量夹角的余弦，取值范围为 [-1, 1]。1 表示方向一致，0 表示正交，-1 表示方向相反。它不是 [0,1]、不是百分比，也不是无界量。

### single_choice · None



- [A] 中文和英文不能放在同一台机器上处理，应拆分服务器
- [B] 普通单语模型未必把中英文映射到可比的空间，应换用多语言/跨语言句向量模型
- [C] 应该把所有文本转成大写字母
- [D] 应该把向量长度统一改成 1

**参考答案**：1

**解析**：单语句向量模型通常只在单一语言语料上训练，跨语言时向量空间可能不可比。跨语言检索应使用多语言模型，使不同语言的语义相近内容映射到相近位置。拆分服务器或大小写转换都不解决问题。
