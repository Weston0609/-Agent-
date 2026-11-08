# s6u3l3 GPT 架构（Generative Pre-traine / 计算机只认识数字，而 LLM 的输入必须是**整数 ID

> 来源 `content/lessons/s6u3l3.json`

## ai.llm.gpt_arch

## 一句话直觉

GPT 架构（Generative Pre-trained Transformer）就是让机器学会“看前文、猜下一个词”的神经网络结构，像你手机输入法那样，只不过它读过的书和文章多到能写出通顺的段落、代码甚至诗歌。

## 1. 从“预测下一个词”开始

GPT 的核心任务只有一个：给定前面的一串词（token），预测下一个词最可能是什么。比如输入“今天天气真”，模型应该输出“好”或“不错”的概率最高。这个任务叫做**自回归语言建模**（Autoregressive Language Modeling）。

为什么这么简单的事能造就 ChatGPT？因为要准确预测下一个词，模型必须隐式学会语法、事实、推理甚至代码逻辑。

```python
# 模拟一个极简的“下一个词预测”
# 注意：这不是真正的 GPT，只是帮助理解任务形式
from collections import defaultdict

# 训练语料：每行是一个句子，拆成词
corpus = [
    "今天 天气 真 好",
    "今天 天气 真 不错",
    "明天 天气 可能 会 下雨",
]

# 统计每个“前文词”后面跟什么词
bigram = defaultdict(list)
for sentence in corpus:
    words = sentence.split()
    for i in range(len(words) - 1):
        bigram[words[i]].append(words[i + 1])

# 预测“今天”后面最可能是什么
print(bigram["今天"])  # ['天气', '天气']
```

**关键结论**：GPT 的输入是一段文本，输出是词表上所有词的概率分布。训练目标就是让正确下一个词的概率尽量大。

## 2. Transformer 是它的骨架

GPT 用的是 **Transformer**（一种基于自注意力机制的神经网络）的**解码器**（Decoder）部分。解码器的特点是：每个位置只能看到自己左边的词，不能偷看右边的词，这叫**因果掩码**（Causal Mask）。

自注意力（Self-Attention）让每个词都能“关注”前面所有词，并加权组合它们的信息。公式简化成：

```
Attention(Q, K, V) = softmax(QK^T / sqrt(d)) V
```

其中 Q、K、V 都是输入经过线性变换得到的。掩码把右上角（未来位置）设为负无穷，softmax 后权重为 0。

```python
import torch
import torch.nn.functional as F

# 模拟 3 个词，每个词用 4 维向量表示
x = torch.randn(3, 4)

# 简单自注意力：Q=K=V=x（实际中会分别做线性变换）
Q, K, V = x, x, x

scores = Q @ K.T / (4 ** 0.5)  # 3x3 注意力分数

# 因果掩码：只能看左边，不能看右边
mask = torch.triu(torch.ones(3, 3), diagonal=1).bool()
scores = scores.masked_fill(mask, float('-inf'))

weights = F.softmax(scores, dim=-1)
out = weights @ V
print(out.shape)  # torch.Size([3, 4])
```

**关键结论**：GPT 的每个词只能看到它左边的词，这保证了生成时不会“作弊”。

## 3. GPT 的堆叠结构

一个 GPT 模型由很多层相同的 **Transformer 块**（Block）堆叠而成。每一块包含：

1. **层归一化**（LayerNorm）
2. **多头自注意力**（Multi-Head Self-Attention）
3. **残差连接**（Residual Connection）
4. **前馈网络**（Feed-Forward Network，FFN）

GPT-2 有 12 到 48 层，GPT-3 有 96 层，GPT-4 更多。层数越多、维度越大，模型能力越强，但计算量也越大。

```python
import torch.nn as nn

class GPTBlock(nn.Module):
    def __init__(self, d_model=64, nhead=4):
        super().__init__()
        self.ln1 = nn.LayerNorm(d_model)
        self.attn = nn.MultiheadAttention(d_model, nhead, batch_first=True)
        self.ln2 = nn.LayerNorm(d_model)
        self.ffn = nn.Sequential(
            nn.Linear(d_model, 4 * d_model),
            nn.GELU(),
            nn.Linear(4 * d_model, d_model),
        )

    def forward(self, x):
        # 自注意力 + 残差
        h = self.ln1(x)
        # 因果掩码：上三角为 True
        L = x.size(1)
        mask = torch.triu(torch.ones(L, L), diagonal=1).bool()
        attn_out, _ = self.attn(h, h, h, attn_mask=mask)
        x = x + attn_out
        # 前馈 + 残差
        x = x + self.ffn(self.ln2(x))
        return x

block = GPTBlock()
dummy = torch.randn(1, 5, 64)  # batch=1, 序列长度=5, 维度=64
print(block(dummy).shape)  # torch.Size([1, 5, 64])
```

**关键结论**：GPT 就是很多个这样的块叠起来，每个块都在做“看前文、更新表示”的操作。

## 4. 从模型到生成：采样策略

训练好的 GPT 只给出下一个词的概率分布，真正生成文本还需要**采样策略**：

- **贪心搜索**（Greedy Search）：每次选概率最大的词，容易重复。
- **温度采样**（Temperature Sampling）：用温度 T 调整分布平滑度，T 越大越随机。
- **Top-k 采样**：只从概率最高的 k 个词里采样。
- **Top-p 采样**（Nucleus Sampling）：从累积概率达到 p 的最小词集合里采样。

```python
import torch
import torch.nn.functional as F

logits = torch.tensor([2.0, 1.0, 0.5, 0.1])  # 4 个候选词的原始分数
probs = F.softmax(logits, dim=-1)
print("原始概率:", probs)

# 温度采样：T=0.5 让分布更尖锐
temp = 0.5
temp_probs = F.softmax(logits / temp, dim=-1)
print("温度0.5概率:", temp_probs)

# Top-k 采样：只保留前2个
values, indices = torch.topk(probs, 2)
print("Top-2 词索引:", indices, "概率:", values)
```

**关键结论**：GPT 生成文本时，采样策略决定了输出的多样性和质量。

## 5. 为什么 GPT 能“涌现”能力

当模型参数和数据量增加到一定程度，GPT 会表现出训练目标之外的能力，比如翻译、算术、写代码。这被称为**涌现能力**（Emergent Abilities）。原因目前还在研究中，但普遍认为与大规模自注意力捕捉长距离依赖、以及海量数据中的统计规律有关。

```python
# 用参数数量粗略感受规模差异
# 这里只是示意，不是真实计算
def rough_params(layers, d_model):
    # 每层约 12 * d_model^2（注意力+FFN）
    return layers * 12 * d_model * d_model

print("GPT-2 Small:", rough_params(12, 768))
print("GPT-3 175B 级别:", rough_params(96, 12288))
```

**关键结论**：GPT 的能力随规模增长而提升，但具体机制仍是开放问题。

## 动手练习

在本地完成以下任务：

1. 安装 PyTorch：`pip install torch`
2. 复制上面的 `GPTBlock` 代码，创建一个 2 层的迷你 GPT。
3. 输入一个形状为 `(1, 10, 64)` 的随机张量，让它前向传播，打印输出形状。
4. 修改代码：去掉因果掩码，观察输出形状是否变化，并思考为什么生成任务必须用掩码。
5. 选做：把 `d_model` 改成 128，层数改成 4，再运行一次，感受参数量变化。

## ai.llm.tokenizer

## 一句话直觉

**Tokenizer（分词器）** 是连接人类语言和 LLM（大语言模型）的“翻译官”——它把文本转换成模型能处理的整数序列，也决定了模型眼里的“最小单位”是什么。

---

## 1. 为什么需要 Tokenizer？

计算机只认识数字，而 LLM 的输入必须是**整数 ID 序列**。Tokenizer 负责：

- **编码（encode）**：文本 → token 序列 → 整数 ID 序列
- **解码（decode）**：整数 ID 序列 → token 序列 → 文本

Token 不一定等于“字”或“词”。现代 LLM 常用 **子词（subword）** 切分，例如 `"unhappiness"` 可能被切成 `un + happi + ness`。

> 关键结论：**同一段文本，不同 tokenizer 得到的 token 数和 ID 完全不同**；模型只能认识自己 tokenizer 产生的 ID。

```python
# 用字符级 tokenizer 直观感受“编码/解码”
text = "你好 LLM"
chars = list(text)                # 最朴素的分词：每个字符一个 token
vocab = {c: i for i, c in enumerate(sorted(set(chars)))}
ids = [vocab[c] for c in chars]
print("tokens:", chars)
print("ids:", ids)
print("decoded:", "".join(chars[i] for i in ids))
```

---

## 2. 常见分词粒度

| 粒度 | 例子 | 优点 | 缺点 |
|---|---|---|---|
| 字符级（char） | `你/好` | 词表小 | 序列太长 |
| 词级（word） | `你好/世界` | 语义直观 | 词表爆炸、OOV |
| 子词（subword） | `un/happi/ness` | 平衡词表与长度 | 需要训练算法 |

主流子词算法：**BPE（Byte Pair Encoding）**、**WordPiece**、**Unigram**、**SentencePiece**。

> 关键结论：子词分词能在“词表大小”和“序列长度”之间取得工程最优。

```python
# 极简 BPE 思想演示：反复合并出现频率最高的相邻符号对
from collections import Counter

def get_pairs(tokens_list):
    pairs = Counter()
    for tokens in tokens_list:
        for i in range(len(tokens) - 1):
            pairs[(tokens[i], tokens[i+1])] += 1
    return pairs

def merge(tokens, pair, new_token):
    out, i = [], 0
    while i < len(tokens):
        if i < len(tokens) - 1 and (tokens[i], tokens[i+1]) == pair:
            out.append(new_token); i += 2
        else:
            out.append(tokens[i]); i += 1
    return out

corpus = [list("low"), list("lower"), list("lowest")]
for step in range(3):
    pair, _ = get_pairs(corpus).most_common(1)[0]
    new_token = "".join(pair)
    corpus = [merge(t, pair, new_token) for t in corpus]
    print(f"step {step}: merge {pair} -> {new_token}", corpus)
```

---

## 3. 词表、特殊 token 与注意力掩码

- **词表（vocabulary）**：token ↔ ID 的映射表，大小通常 30k~150k。
- **特殊 token（special tokens）**：`[CLS]`、`[SEP]`、`[PAD]`、`[UNK]`、`<|endoftext|>` 等，控制模型行为。
- **attention mask（注意力掩码）**：区分真实 token 与 padding，避免 attention 关注补齐位置。

> 关键结论：padding 与 attention mask 是 batch 推理正确性的前提。

```python
# 模拟 batch 编码：padding + attention mask
def batch_encode(texts, vocab, max_len=6, pad_id=0):
    ids_batch, mask_batch = [], []
    for t in texts:
        ids = [vocab.get(c, vocab.get("<UNK>", -1)) for c in t][:max_len]
        mask = [1] * len(ids)
        ids += [pad_id] * (max_len - len(ids))
        mask += [0] * (max_len - len(mask))
        ids_batch.append(ids); mask_batch.append(mask)
    return ids_batch, mask_batch

vocab = {"<PAD>":0, "<UNK>":1, "你":2, "好":3, "L":4, "M":5}
ids, mask = batch_encode(["你好", "LLM"], vocab)
print("ids:", ids)
print("mask:", mask)
```

---

## 4. 实战：用 Hugging Face Tokenizer

工程中几乎不自己写 tokenizer，而是加载预训练 tokenizer，必须与模型**严格配套**。

> 关键结论：**tokenizer 和 model 必须来自同一预训练版本**，否则 ID 语义错位，结果灾难性错误。

```python
# 安装: pip install transformers
from transformers import AutoTokenizer

tok = AutoTokenizer.from_pretrained("bert-base-chinese")
enc = tok("我喜欢自然语言处理", return_tensors="pt", padding=True, truncation=True)
print("input_ids:", enc["input_ids"])
print("attention_mask:", enc["attention_mask"])
print("decode:", tok.decode(enc["input_ids"][0], skip_special_tokens=True))
```

---

## 5. 工程关注点

- **序列长度与成本**：token 数直接决定计算量、显存和 API 计费。中文常 1 字≈1~2 token。
- **OOV（Out-of-Vocabulary）**：子词和 byte-level fallback 已基本消除。
- **多语言/代码场景**：优先选择 byte-level BPE（如 GPT 系列、Llama 系列）。
- **缓存 tokenizer**：本地缓存避免重复下载。

> 关键结论：优化 prompt 时，先量化 token 数，再谈压缩策略。

```python
# 估算 token 数，用于成本评估
samples = ["Hello world", "你好，世界", "def f(x): return x + 1"]
for s in samples:
    n = len(tok.encode(s))
    print(f"{n:>3} tokens | {s}")
```

---

## 动手练习

1. 本地安装 `transformers`，分别加载 `bert-base-chinese` 与 `gpt2` 两个 tokenizer。
2. 对下面三段文本分别计算 token 数并打印 ID：
   - `"人工智能正在改变世界"`
   - `"Artificial Intelligence is changing the world"`
   - `"def add(a, b): return a + b"`
3. 对比两个 tokenizer 在同一文本上的 token 数量差异，写出 3 条观察结论。
4. 进阶：自己实现一个最简 BPE，在 100 行英文小语料上训练词表并编码一句话。


---

## 本课题目

### single_choice · None



- [A] 它让模型在预测第 t 个位置时只能看到前 t 个位置，避免信息泄露
- [B] 它让模型在前向传播时只能使用后 t 个位置的信息
- [C] 它只用于训练阶段，推理阶段必须移除，否则输出会出错
- [D] 它会把注意力权重强制归一化为均匀分布

**参考答案**：0

**解析**：因果掩码把未来位置的注意力权重置为负无穷，使每个位置只能关注自身及之前的位置，从而支持自回归语言建模并防止训练时看到答案。

### single_choice · None



- [A] 一次性并行输出整个序列的所有 token，再用后处理去重
- [B] 每一步根据已生成的前缀预测下一个 token，再把它拼回输入继续预测
- [C] 先从序列末尾开始反向生成，最后再整体翻转
- [D] 随机采样若干 token 后按词典序排序输出

**参考答案**：1

**解析**：自回归生成是逐 token 进行：用当前前缀预测下一个 token，将新 token 加入前缀，重复直到结束符或长度上限。

### single_choice · None



- [A] 它直接改变模型权重，使模型更聪明
- [B] 它缩放 logits，温度越高分布越平坦、采样越随机；温度越低分布越尖锐
- [C] 它决定生成的最大长度
- [D] 它控制注意力头数

**参考答案**：1

**解析**：温度通过除以 logits 来调节 softmax 分布的平滑程度：高温更随机，低温更确定。

### single_choice · None



- [A] 自注意力本身对输入顺序不敏感，需要显式注入位置信息
- [B] 词嵌入维度过大，需要降维
- [C] 训练时梯度爆炸，需要归一化
- [D] 输出层词汇表太大，需要压缩

**参考答案**：0

**解析**：纯自注意力是置换等变的，没有顺序概念，因此需要位置编码来提供序列位置信息。

### single_choice · None



- [A] 它把子层输出与子层输入相加，有助于梯度传播和训练深层网络
- [B] 它把子层输出与子层输入相减，用于去除噪声
- [C] 它只在最后一层使用，其他层不需要
- [D] 它会完全替代层归一化

**参考答案**：0

**解析**：残差连接将输入加到子层输出上，缓解梯度消失，便于训练很深的 Transformer。

### single_choice · None



- [A] LayerNorm 在特征维度上归一化，不依赖 batch 大小；BatchNorm 依赖 batch 统计
- [B] LayerNorm 只能用于卷积网络，BatchNorm 只能用于 Transformer
- [C] LayerNorm 会改变序列长度，BatchNorm 不会
- [D] 两者完全等价，只是名字不同

**参考答案**：0

**解析**：LayerNorm 对每个样本在特征维度上做归一化，适合变长序列和小 batch；BatchNorm 依赖 batch 内统计量。

### single_choice · None



- [A] 把隐藏状态映射到词表大小的分布，得到下一个 token 的概率
- [B] 把词表压缩成固定长度向量
- [C] 计算注意力权重
- [D] 生成位置编码

**参考答案**：0

**解析**：输出线性层把隐藏状态投影到词表维度，softmax 后得到下一个 token 的概率分布。

### single_choice · None



- [A] 交叉熵损失，对每个位置的下一 token 预测计算
- [B] 均方误差损失，对所有 token 嵌入回归
- [C] 对比损失，只拉近正样本对
- [D] Hinge 损失，用于最大间隔分类

**参考答案**：0

**解析**：语言建模通常用交叉熵（负对数似然）衡量预测分布与真实下一 token 的差异。

### single_choice · None



- [A] 它只使用 Transformer 解码器堆叠，不使用编码器
- [B] 它只做解码任务，不做任何训练
- [C] 它只能处理图像，不能处理文本
- [D] 它没有注意力机制，只有前馈网络

**参考答案**：0

**解析**：GPT 仅堆叠 Transformer 解码器层，没有独立的编码器部分，因此称为 decoder-only。

### single_choice · None



- [A] 它指模型一次能处理的最大 token 数，超出部分需要截断或分块
- [B] 它指模型可以同时训练的 batch 大小
- [C] 它指模型参数的总数量
- [D] 它指生成时允许的最大温度值

**参考答案**：0

**解析**：上下文窗口是模型单次前向能接受的最大序列长度，由位置编码和注意力计算限制。

### single_choice · None



- [A] 为了防止点积结果过大导致 softmax 梯度极小，稳定训练
- [B] 为了让注意力权重变成整数
- [C] 为了减少参数数量
- [D] 为了让 Q、K 维度必须相等

**参考答案**：0

**解析**：点积随维度增大而增大，除以 sqrt(d_k) 可以控制方差，避免 softmax 进入饱和区导致梯度消失。

### single_choice · None



- [A] 可以在预训练模型基础上，用下游任务数据继续训练，使输出更适配任务
- [B] 微调会完全丢弃预训练权重，从随机初始化开始
- [C] 微调只能改变词表大小，不能改变其他参数
- [D] 微调只适用于图像任务，不适用于文本

**参考答案**：0

**解析**：微调是在预训练权重基础上用任务数据继续优化，通常比从头训练更高效、效果更好。

### single_choice · None



- [A] 为了减少参数量，让模型更容易训练
- [B] 为了让每个位置只能看到前面的 token，与语言模型预测下一个词的目标一致
- [C] 为了避免使用位置编码
- [D] 为了让注意力计算从平方复杂度降为线性复杂度

**参考答案**：1

**解析**：语言模型的目标是用前面的上下文预测下一个词，因此需要因果掩码来阻止模型看到未来 token。

### single_choice · None



- [A] 拼接会导致维度爆炸，而相加可以保持隐藏维度不变并让模型在每层统一处理
- [B] 相加后位置信息会被完全丢弃，从而增强语义
- [C] 拼接会破坏 token 的离散性，模型无法训练
- [D] 相加可以自动实现权重共享

**参考答案**：0

**解析**：把同维度的 token 嵌入和位置嵌入相加，可以在不增加隐藏维度的前提下注入位置信息，是常见做法。

### single_choice · None



- [A] 多个头共享同一组 Q、K、V 投影矩阵，只是重复计算多次
- [B] 多个头各自有独立的 Q、K、V 投影，能关注不同子空间的信息
- [C] 多头只是为了增加参数量，对表达能力没有帮助
- [D] 每个头都必须输出相同维度的结果，最后直接相加不做拼接

**参考答案**：1

**解析**：多头注意力让每个头学习不同的投影子空间，从而捕捉多样化的依赖关系；各头结果拼接后再做一次线性变换。

### single_choice · None



- [A] 卷积层 + 池化层 + 全连接层
- [B] 掩码多头自注意力 + 前馈网络 + 残差连接和层归一化
- [C] 双向自注意力 + 交叉注意力 + 循环单元
- [D] 嵌入层 + softmax + 词袋模型

**参考答案**：1

**解析**：GPT 的每个 block 主要由掩码多头自注意力和逐位置前馈网络组成，并配有残差连接与层归一化。

### single_choice · None



- [A] 它负责把 token 序列的位置信息编码进去
- [B] 它对每个位置独立地进行非线性变换，增强模型的表达能力
- [C] 它用来替代注意力机制，减少计算量
- [D] 它只在训练时使用，推理时可以省略

**参考答案**：1

**解析**：FFN 对每个位置独立应用两层线性变换和激活函数，提供非线性并增大模型容量。

### single_choice · None



- [A] 掩码语言建模（masked language modeling），随机遮盖部分 token 并还原
- [B] 自回归语言建模，根据前文预测下一个 token
- [C] 句子对分类，判断两句话是否相邻
- [D] 图像分类，把文本映射到类别标签

**参考答案**：1

**解析**：GPT 预训练使用自回归语言建模目标：最大化给定前文条件下下一个 token 的似然。

### single_choice · None



- [A] BERT 使用自回归目标，GPT 使用掩码目标
- [B] BERT 使用掩码/双向目标，GPT 使用自回归目标
- [C] 两者都使用自回归目标，只是模型大小不同
- [D] 两者都使用掩码目标，只是掩码比例不同

**参考答案**：1

**解析**：BERT 通过掩码语言建模利用双向上下文；GPT 通过自回归语言建模只能利用左侧上下文。

### single_choice · None



- [A] 贪心解码（greedy decoding）
- [B] 束搜索（beam search）
- [C] 温度采样（temperature sampling）
- [D] Top-k 采样

**参考答案**：0

**解析**：每步取 argmax 概率的 token 即贪心解码，简单但容易重复、缺乏多样性。

### single_choice · None



- [A] 将文本切分为模型可处理的 token 序列，并映射为整数 ID
- [B] 对模型输出的概率分布进行排序
- [C] 把模型的权重从浮点数量化为整数
- [D] 在训练时计算损失函数的梯度

**参考答案**：0

**解析**：分词器负责把原始文本切分成子词/token，并映射到词表中的整数 ID，作为模型输入；概率排序、量化、梯度计算都不是分词器的职责。

### single_choice · None



- [A] 不同模型的参数量不同
- [B] 不同模型使用不同的词表和分词算法（如 BPE、WordPiece、Unigram）
- [C] 不同模型的上下文窗口一定相同
- [D] 不同模型的浮点精度不同

**参考答案**：1

**解析**：token 数量取决于词表大小与分词算法，与参数量、精度无直接关系；上下文窗口是模型能接受的最大 token 数，不影响切分粒度。

### multi_choice · None



- [A] 词表大小与嵌入层参数量、显存占用的平衡
- [B] 序列长度与推理成本／上下文利用率的平衡
- [C] 对多语言和目标领域词汇的覆盖程度
- [D] 把分词器设计成能直接输出模型最终答案
- [E] 与预训练模型保持一致，避免推理时错配

**参考答案**：[0, 1, 2, 4]

**解析**：分词器设计需权衡词表规模、序列长度、语言覆盖，并须与预训练模型匹配；分词器只做文本与 token 的映射，不负责生成答案。

### fill_blank · None



**参考答案**：["BPE", "bpe", "Byte Pair Encoding", "byte pair encoding"]

**解析**：BPE（Byte Pair Encoding，字节对编码）通过迭代合并高频相邻符号对来构建子词词表，是常见的子词分词算法之一。

### fill_blank · None



**参考答案**：["token ids", "token id", "tokens", "input_ids", "标记 ID", "token 序列", "token序列"]

**解析**：编码结果通常以整数 ID 序列（token ids / input_ids）表示，作为模型输入；它是文本到模型可处理形式的映射结果。

### code_reading · None



**参考答案**：不一定相等。"hello world" 与 "helloworld" 是不同字符串，分词器对空白的处理与子词切分不同，切分出的 token 数可能不同；即使本例中恰好相同，也不能断言任意两串文本长度相同。最终 token 数还受是否添加特殊 token 影响。

**解析**：token 数取决于分词器实际的切分结果，而不是字符串长度或直觉；不同文本即使看起来相近，也可能切分不同，因此不能保证相等。

### code_reading · None



**参考答案**：不可靠。原因有二：(1) 词表对中文覆盖不足时，一个汉字可能被拆成多个字节级子词，token 数会多于或不同于字符数；(2) 分词器自动添加的特殊 token 也计入长度。因此 len(ids) 不能直接反映原始字符数。

**解析**：token 数与字符数并非一一对应，尤其在多语言覆盖不足和多加特殊 token 的情况下，长度判断会失真。

### code_reading · None



**参考答案**：不保证。解码通常在文本层面接近原文，但分词过程可能对空白、大小写或特殊字符做规范化，且特殊 token 的处理方式不同，因此可能丢失或改变少量格式细节，不能保证逐字符一致。

**解析**：编解码近似可逆而非严格可逆，规范化与特殊 token 处理会造成差异。

### scenario · None



**解析**：应按 token 而非字符数衡量长度：先确认该模型使用的分词器，把文本编码后统计 token 数；中文可能被拆成多个子词导致 token 数远超预期；再根据上下文上限做截断或分段，并预留输出 token 的空间。

### scenario · None



**解析**：需结合语料规模与领域/语言分布选择词表大小与子词算法：词表大则序列短但嵌入参数多，词表小则序列长但参数少；要保证对目标语言与领域词汇的覆盖，并注意与后续使用保持一致性。

### single_choice · None



- [A] 它采用的是字符级分词，每个字符一个 token
- [B] 它采用的是子词（subword）分词，可组合词根与词缀
- [C] 它采用的是整词分词，词表中只存完整单词
- [D] 它会把所有单词都切分成单个字母

**参考答案**：1

**解析**：把单词拆成词根与词缀是子词分词（如 BPE/WordPiece）的典型行为；字符级会把每个字母分开，整词分词不会拆出 "play"+"ing"。

### single_choice · None



- [A] 词表越大，一般不常见词被切成更多子词，序列可能更短，但嵌入参数量更大
- [B] 词表越大，同一文本的 token 数一定越多
- [C] 词表大小与嵌入参数量无关
- [D] 词表越小，模型一定越难处理未登录词

**参考答案**：0

**解析**：词表越大，越容易用单个 token 覆盖更多词，序列变短，但嵌入矩阵规模随之增大；词表小则更依赖子词拆分，序列往往更长。

### single_choice · None



- [A] 按输入和输出文本的字符数
- [B] 按输入和输出 token 的数量
- [C] 按请求次数固定收费
- [D] 按模型的磁盘占用大小

**参考答案**：1

**解析**：主流大模型 API 按 token 数量计费，输入与输出通常分别计价；字符数、请求次数、磁盘占用都不是通用计量方式。

### single_choice · None



- [A] 它们由用户在每次调用时手动拼接到文本中
- [B] 它们由分词器在编码时按规则自动添加，用于标记序列结构
- [C] 它们与普通 token 完全相同，没有特殊含义
- [D] 它们只存在于训练阶段，推理时会被删除

**参考答案**：1

**解析**：特殊 token 由分词器根据配置（如是否添加起止标记、是否填充）自动处理，用于标识序列结构；并非用户手工拼接，也不等同于普通 token。

### single_choice · None



- [A] 解码结果与原文完全逐字符一致，包括空格和大小写
- [B] 解码结果通常在语义/文本上接近原文，但个别空白或格式可能有差异
- [C] 解码结果一定变成乱码
- [D] 解码结果一定是原文的两倍长度

**参考答案**：1

**解析**：编解码一般近似可逆，但某些分词方案会规范化空白或特殊字符，因此可能丢失或改变少量格式细节，不会完全逐字符一致。

### single_choice · None



- [A] 一个汉字通常对应一个 token，与英文单词 token 数可比
- [B] 由于词表覆盖不足，一个汉字可能被拆成多个字节级 token，导致 token 数偏多
- [C] 非英语文本无法被分词
- [D] 非英语文本的 token 数一定少于英语

**参考答案**：1

**解析**：若词表对某些语言覆盖不足，字节级回退会把一个字符拆成多个 token，导致 token 数偏多；具体取决于词表设计，不能一概而论。

### multi_choice · None



- [A] 所使用的分词器及其词表大小
- [B] 文本本身的长度和内容（如是否含大量罕见词或生僻字符）
- [C] 文本的语言种类
- [D] 模型的上下文窗口上限
- [E] 调用时的 temperature 参数

**参考答案**：[0, 1, 2]

**解析**：token 数由分词器/词表、文本内容与语言决定；上下文窗口是能容纳的最大 token 数，不改变切分结果；temperature 只影响采样，不影响编码。

### multi_choice · None



- [A] 它能在一定程度上缓解未登录词（OOV）问题
- [B] 它通过组合常见词根/词缀来表示罕见词
- [C] 它需要在训练语料上统计并构建词表
- [D] 它保证每个单词都恰好对应一个 token
- [E] 它的常见算法包括 BPE、WordPiece 等

**参考答案**：[0, 1, 2, 4]

**解析**：子词分词通过拆分与组合缓解 OOV，需要基于语料构建词表，常见算法有 BPE、WordPiece 等；它并不保证单词与 token 一一对应。
