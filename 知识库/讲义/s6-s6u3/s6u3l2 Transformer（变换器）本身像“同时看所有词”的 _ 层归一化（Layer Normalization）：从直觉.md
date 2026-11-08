# s6u3l2 Transformer（变换器）本身像“同时看所有词”的 / 层归一化（Layer Normalization）：从直觉到工程实现

> 来源 `content/lessons/s6u3l2.json`

## ai.llm.position_encoding

## 一句话直觉

Transformer（变换器）本身像“同时看所有词”的机器，**没有顺序感**；位置编码（Position Encoding）就是把“第几个词”这件事写进向量里，让模型知道“我爱你”和“你爱我”不是一回事。

---

## 1. 为什么需要位置编码

在循环神经网络（RNN, Recurrent Neural Network）里，词是一个一个按顺序喂进去的，顺序天然存在。但 Transformer 的核心是自注意力（Self-Attention）：每个词同时和所有词计算相关性。如果你把句子打乱，自注意力算出来的结果会完全一样（只是输出顺序跟着变），模型无法区分“猫追老鼠”和“老鼠追猫”。

所以必须在输入里显式加入位置信息。

```python
# 没有位置编码时，自注意力对顺序不敏感
import torch

def attention_scores(x):
    # x: [seq_len, dim]，简化版：用点积表示两两相关性
    return x @ x.T

x = torch.tensor([[1., 0.], [0., 1.], [1., 1.]])  # 3 个词向量
print(attention_scores(x))
print(attention_scores(x.flip(0)))  # 顺序反过来，分数矩阵只是行列调换，不是“不同句子”
```

**结论**：Transformer 的输入需要额外注入位置信息。

---

## 2. 位置编码的基本形式

位置编码（Position Encoding, PE）是一个和词嵌入（Token Embedding）同维度的向量。对第 `pos` 个位置、第 `i` 维，Transformer 原论文使用正弦/余弦函数：

- 偶数维：`PE(pos, 2i) = sin(pos / 10000^(2i/d_model))`
- 奇数维：`PE(pos, 2i+1) = cos(pos / 10000^(2i/d_model))`

其中 `d_model` 是模型隐藏维度。它的好处是：不同位置有唯一模式；相对位置可以通过线性变换表示；可以外推到比训练时更长的序列。

```python
import torch
import math

def sinusoidal_position_encoding(seq_len, d_model):
    pe = torch.zeros(seq_len, d_model)
    position = torch.arange(0, seq_len, dtype=torch.float).unsqueeze(1)
    div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
    pe[:, 0::2] = torch.sin(position * div_term)
    pe[:, 1::2] = torch.cos(position * div_term)
    return pe

pe = sinusoidal_position_encoding(5, 8)
print(pe.shape)  # [5, 8]
print(pe[0])     # 第 0 个位置的编码
```

**结论**：正弦位置编码是固定、无需训练的，直接加到词嵌入上。

---

## 3. 怎么把位置编码加进模型

最常见的做法是：`最终输入 = 词嵌入 + 位置编码`。两者维度相同，逐元素相加。位置编码不改变词义，只是给每个位置打上“坐标”。

```python
import torch
import torch.nn as nn

class ToyTransformerInput(nn.Module):
    def __init__(self, vocab_size, d_model, max_len=100):
        super().__init__()
        self.token_emb = nn.Embedding(vocab_size, d_model)
        self.register_buffer('pos_emb', sinusoidal_position_encoding(max_len, d_model))
        self.d_model = d_model

    def forward(self, token_ids):
        # token_ids: [batch, seq_len]
        seq_len = token_ids.size(1)
        x = self.token_emb(token_ids) * math.sqrt(self.d_model)  # 缩放词嵌入
        x = x + self.pos_emb[:seq_len].unsqueeze(0)              # 加位置编码
        return x

model = ToyTransformerInput(vocab_size=100, d_model=16)
out = model(torch.tensor([[1, 2, 3, 4]]))
print(out.shape)  # [1, 4, 16]
```

**结论**：位置编码与词嵌入相加，是 Transformer 输入层的标准步骤。

---

## 4. 可学习位置编码与相对位置

除了固定的正弦编码，还有两类常见方案：

1. **可学习位置编码（Learned Position Embedding）**：给每个位置一个可训练向量，如 BERT 使用。实现简单，但外推能力弱。
2. **相对位置编码（Relative Position Encoding）**：关注词与词之间的相对距离，如 T5 的相对位置偏置、RoPE（旋转位置编码）。现代大语言模型常用 RoPE，因为它对长上下文更友好。

```python
# 可学习位置编码示例
learned_pos = nn.Embedding(100, 16)
pos_ids = torch.arange(4)
print(learned_pos(pos_ids).shape)  # [4, 16]

# 简化版相对位置偏置：给注意力分数加一个与距离有关的偏置
def relative_bias(seq_len, num_heads):
    # 距离越远，偏置越小（这里只是示意）
    distance = torch.arange(seq_len).unsqueeze(1) - torch.arange(seq_len).unsqueeze(0)
    bias = -torch.abs(distance).float()
    return bias.unsqueeze(0).expand(num_heads, -1, -1)

print(relative_bias(4, 2).shape)  # [2, 4, 4]
```

**结论**：绝对位置编码解决“第几个”，相对位置编码解决“隔多远”，RoPE 是当前大模型主流。

---

## 5. 工程中要注意什么

- **维度必须匹配**：位置编码维度 = 词嵌入维度 = `d_model`。
- **最大长度限制**：固定或可学习位置编码通常有 `max_len`，超过会越界；RoPE 和 ALiBi 等方法更适合长文本。
- **不要重复加**：位置编码只在输入层加一次，不要在每层 Transformer 后重复加。
- **批处理对齐**：`pos_emb[:seq_len]` 要能广播到 `[batch, seq_len, d_model]`。

```python
# 检查位置编码是否能广播到 batch
batch, seq_len, d_model = 2, 5, 8
x = torch.randn(batch, seq_len, d_model)
pe = sinusoidal_position_encoding(seq_len, d_model)
print((x + pe.unsqueeze(0)).shape)  # [2, 5, 8]
```

**结论**：位置编码虽小，但维度、长度和加法位置都容易出错，工程实现要仔细核对。

---

## 动手练习

实现一个 `PositionalEncoding` 类，要求：

1. 使用正弦/余弦公式生成位置编码；
2. 支持 `max_len=50`、`d_model=32`；
3. `forward(x)` 接收 `[batch, seq_len, d_model]` 的词嵌入，返回加上位置编码后的结果；
4. 打印第 0 个位置和第 1 个位置的前 4 维，观察它们不同；
5. 把 `seq_len` 改成 60，观察是否越界，并思考如何修改才能支持更长序列。

完成后，你会对“Transformer 如何知道词序”有完整直觉。

## ai.llm.layer_norm

# 层归一化（Layer Normalization）：从直觉到工程实现

> **一句话直觉**：层归一化让每个样本的特征分布保持稳定，是让深层神经网络和 Transformer 能稳定、快速训练的关键“稳压器”。

---

## 0. 先修知识：为什么需要归一化？

在神经网络中，每一层的输入分布会随着前面层参数更新而不断变化（称为 **内部协变量偏移 internal covariate shift**）。这会让训练变得不稳定、学习率必须很小。

**做法**：对每一层的输入进行重新标准化，使其均值接近 0、方差接近 1。

常见的归一化有：

| 名称 | 英文 | 归一化维度 |
|---|---|---|
| 批归一化 | Batch Normalization, BN | 对一个 batch 内同一特征跨样本归一化 |
| 层归一化 | Layer Normalization, LN | 对单个样本的所有特征归一化 |
| 实例归一化 | Instance Normalization | 对单个样本单通道空间归一化 |

---

## 1. 层归一化到底在做什么？

给定一个样本的特征向量 $x \in \mathbb{R}^d$：

$$
\mu = \frac{1}{d}\sum_{i=1}^{d} x_i,\quad
\sigma^2 = \frac{1}{d}\sum_{i=1}^{d}(x_i-\mu)^2
$$

$$
\hat{x}_i = \frac{x_i-\mu}{\sqrt{\sigma^2+\epsilon}},\quad
y_i = \gamma_i \hat{x}_i + \beta_i
$$

- $\epsilon$：防止除零的小常数（如 `1e-5`）。
- $\gamma, \beta$：可学习参数，让网络可以恢复原始表达能力。
- **关键点**：均值和方差**只在一个样本内部计算**，与 batch 大小无关。


### 为什么 LLM 爱用 LayerNorm？
- 不依赖 batch 大小；
- 训练和推理行为一致；
- 序列变长时仍然稳定；
- 对 Transformer 的残差流特别友好。

---

## 2. 手写 LayerNorm：从公式到代码

我们先用 PyTorch 从零实现一层 LayerNorm，并和官方结果对比。

```python
import torch
import torch.nn as nn

torch.manual_seed(0)

class MyLayerNorm(nn.Module):
    def __init__(self, normalized_shape, eps=1e-5):
        super().__init__()
        self.eps = eps
        self.gamma = nn.Parameter(torch.ones(normalized_shape))
        self.beta  = nn.Parameter(torch.zeros(normalized_shape))

    def forward(self, x):
        mean = x.mean(dim=-1, keepdim=True)
        var  = x.var(dim=-1, unbiased=False, keepdim=True)
        x_hat = (x - mean) / torch.sqrt(var + self.eps)
        return self.gamma * x_hat + self.beta
```

对最后一维做归一化是最常见的用法（例如 Transformer 中每个 token 的 hidden 向量）。

---

## 3. Pre-LN 与 Post-LN：Transformer 里的位置差异

在 Transformer block 中，LayerNorm 放的位置不同，训练稳定性差别很大：

- **Post-LN**（原版 Transformer）：`x = LN(x + Sublayer(x))`，训练对学习率敏感。
- **Pre-LN**：`x = x + Sublayer(LN(x))`，梯度更平稳，是现代 LLM 的主流。

**结论**：当模型很深时，优先使用 Pre-LN。

---

## 4. RMSNorm：LLM 中常见的简化版

**RMSNorm（Root Mean Square Normalization）** 去掉均值中心化，只按均方根缩放：

$$
y_i = \frac{x_i}{\sqrt{\frac{1}{d}\sum_j x_j^2+\epsilon}}\cdot \gamma_i
$$

好处：更快、参数更少，在 LLaMA 等大模型中广泛使用。

---

## 5. 工程级注意点

1. **归一化维度**必须和 `normalized_shape` 一致，否则 PyTorch 会报错。
2. **`var` 的 `unbiased`**：LN 使用有偏方差（除以 d，而不是 d-1），所以要设置 `unbiased=False`。
3. **`eps` 默认值**：PyTorch `nn.LayerNorm` 默认 `1e-5`；RMSNorm 常取 `1e-6` 或 `1e-8`。
4. **dtype**：混合精度训练时，LayerNorm 内部建议用 `float32` 累加，避免数值溢出。
5. **不要在 batch 维度做归一化**：那是 BatchNorm 的活，在变长序列和小 batch 下会翻车。

---

## 6. 一个最小可运行演示

下面代码把自定义 LayerNorm 和 PyTorch 官方实现对比，验证正确性。

```python
import torch
import torch.nn as nn

torch.manual_seed(42)

x = torch.randn(2, 3, 8)  # (batch, seq, hidden)

ln_official = nn.LayerNorm(8)
ln_mine     = MyLayerNorm(8)

# 同步参数，确保可比
with torch.no_grad():
    ln_mine.gamma.copy_(ln_official.weight)
    ln_mine.beta.copy_(ln_official.bias)

y_ref = ln_official(x)
y_my  = ln_mine(x)

print('max diff =', (y_ref - y_my).abs().max().item())
assert torch.allclose(y_ref, y_my, atol=1e-6)
print('LayerNorm 实现一致 ✅')
```

运行后会输出极小的差异（约 1e-7 量级），说明手写版本与官方实现等价。

---

## 7. 动手练习

**任务**：实现一个 `RMSNorm` 并验证它和 LayerNorm 的区别。

要求：
1. 继承 `nn.Module`，参数只有 `gamma`（没有 `beta`）。
2. 使用 `x.pow(2).mean(-1, keepdim=True)` 计算均方值。
3. 对形状 `(2, 4, 16)` 的随机张量做前向，检查输出每个 token 的均方根是否接近 1（乘以 gamma 前）。
4. 可选：和 `torch.nn.RMSNorm`（PyTorch 2.4+）对比结果。

提示：验证时可以临时把 `gamma` 设成全 1，然后打印 `y.pow(2).mean(-1)`。


---

## 本课题目

### single_choice · None



- [A] 无法区分输入序列中不同位置的相同词元，输出对词序不敏感
- [B] 注意力权重会变成全零，模型无法训练
- [C] 模型会自动从词嵌入中推断出绝对位置信息
- [D] 模型只能处理长度为 1 的序列

**参考答案**：0

**解析**：自注意力本身是置换等变的，去掉位置编码后，打乱输入顺序不会改变注意力输出（对相同词元而言），因此模型丢失词序信息。注意力权重不会变成全零，词嵌入也不含绝对位置信息，序列长度也不受此限制。

### single_choice · None



- [A] 它使用可学习的参数，通过训练更新每个位置的编码向量
- [B] 它由不同频率的正弦和余弦函数生成，不同维度对应不同波长
- [C] 它只能表示绝对位置，完全无法体现相对位置关系
- [D] 它的编码向量长度必须等于词表大小

**参考答案**：1

**解析**：正弦位置编码用不同频率的 sin/cos 生成，不同维度对应不同波长，且具有可推导相对位置的性质。它不是可学习参数，也不要求长度等于词表大小；它虽为绝对编码，但因三角恒等式可体现相对位移。

### single_choice · None



- [A] 基本保持不变，因为只依赖相对距离
- [B] 完全变为零
- [C] 变为原来的平方
- [D] 随机变化，无法预测

**参考答案**：0

**解析**：相对位置编码只关心两词元之间的距离，整体平移不改变任意两位置的相对距离，因此分数基本不变。绝对位置编码则可能改变。

### single_choice · None



- [A] 位置索引乘以一个与维度相关的频率常数
- [B] 位置索引的平方根
- [C] 位置索引的对数
- [D] 与位置索引无关的随机值

**参考答案**：0

**解析**：RoPE 对第 i 个位置、第 j 对维度使用角度 i·θ_j，其中 θ_j 是与维度相关的频率常数。它不采用平方根、对数或随机值。

### single_choice · None



- [A] 让不同头关注不同距离范围，增强表示多样性
- [B] 减少模型参数量
- [C] 强制所有头关注同一距离
- [D] 替代词嵌入层

**参考答案**：0

**解析**：ALiBi 为不同头设置不同斜率，使各头偏好不同距离尺度，增加多样性。它不减少参数量，也不替代词嵌入，更不是强制同距离。

### single_choice · None



- [A] 为模型提供词元在序列中的顺序信息，因为自注意力本身对顺序不敏感
- [B] 替代注意力机制进行序列建模
- [C] 压缩序列长度以减少计算量
- [D] 生成词表外的词元

**参考答案**：0

**解析**：自注意力对位置置换等变，需要位置编码注入顺序信息。它不替代注意力、不压缩长度、也不生成词表外词元。

### single_choice · None



- [A] 位置信息无法在注意力计算中影响词元之间的交互
- [B] 位置编码维度会与输出维度不匹配而报错
- [C] 模型会完全无法训练
- [D] 位置编码会覆盖词嵌入信息

**参考答案**：0

**解析**：位置编码需在注意力计算前注入，才能影响 Q/K 的匹配。加在注意力输出之后，词元交互阶段已看不到位置信息。维度不匹配并非必然，也不一定完全无法训练或覆盖词嵌入。

### single_choice · None



- [A] 其维度通常与词嵌入维度相同，以便逐元素相加
- [B] 其维度必须等于序列长度
- [C] 其维度必须等于注意力头数
- [D] 其维度必须等于词表大小

**参考答案**：0

**解析**：为与词嵌入相加，位置编码维度通常等于词嵌入维度。它不要求等于序列长度、头数或词表大小。

### single_choice · None



- [A] 正弦位置编码或相对位置编码等可解析外推的方案
- [B] 固定长度的可学习位置嵌入
- [C] 不使用任何位置编码
- [D] 把位置编码维度设为序列长度

**参考答案**：0

**解析**：正弦编码与相对位置编码（含 RoPE/ALiBi）对外推更友好；固定可学习嵌入受训练长度限制；不用位置编码会丢失顺序；维度设为序列长度不现实。

### single_choice · None



- [A] RoPE（旋转位置编码）
- [B] 正弦绝对位置编码
- [C] 可学习位置嵌入
- [D] ALiBi

**参考答案**：0

**解析**：对 Q、K 施加位置相关旋转矩阵是 RoPE 的典型实现。正弦编码是加到嵌入上，可学习嵌入是查表相加，ALiBi 是加线性偏置。

### single_choice · None



- [A] 打乱输入序列顺序，输出会以相同方式被打乱，模型未利用顺序信息
- [B] 打乱输入序列顺序，输出保持不变，模型利用了顺序信息
- [C] 注意力权重与输入顺序无关，因此自动编码了位置
- [D] 置换等变意味着模型只能处理无序集合

**参考答案**：0

**解析**：置换等变指输入置换会导致输出同样置换，说明注意力未内建顺序偏好，需要位置编码。它与置换不变不同，也不意味着不能处理序列。

### single_choice · None



- [A] 采用外推友好的位置编码方案，或对超出部分进行插值/截断等特殊处理
- [B] 直接查表，因为嵌入表会自动扩展
- [C] 把序列长度强制改为 512 而不做任何处理
- [D] 忽略位置编码，让模型自行推断

**参考答案**：0

**解析**：可学习位置嵌入表大小固定，超长时需改用外推方案或做插值/截断等处理。表不会自动扩展，强制改长度会丢信息，忽略位置编码会丢失顺序。

### single_choice · None



- [A] 位置嵌入表没有对应新位置的向量，无法直接查表获得编码
- [B] 注意力计算会因位置嵌入缺失而报除零错误
- [C] 模型会自动把新位置截断到训练最大长度，无需处理
- [D] 位置嵌入的维度会自动扩展以适配新长度

**参考答案**：0

**解析**：可学习位置嵌入是一张固定大小的参数表，超出训练长度就没有对应行，无法直接查表。维度不会自动扩展，截断会导致信息丢失，也不会出现除零错误。

### single_choice · None



- [A] 让模型在计算注意力时显式建模两个词元之间的距离或方向
- [B] 把位置信息从词嵌入中彻底删除以节省显存
- [C] 强制所有注意力头使用完全相同的位置偏移
- [D] 使模型只能处理固定长度序列

**参考答案**：0

**解析**：相对位置编码的核心是把两词元之间的相对距离/方向纳入注意力计算，更适合序列长度外推。它并不删除位置信息，也不强制各头一致，更不是限制序列长度。

### single_choice · None



- [A] 旋转后的点积只依赖两个词元的相对位置差
- [B] 旋转会改变向量的模长，从而放大远距离注意力
- [C] 旋转只在训练时应用，推理时不应用
- [D] 旋转编码只能用于编码器，不能用于解码器

**参考答案**：0

**解析**：RoPE 对 Q、K 施加与位置相关的旋转，使内积结果只依赖相对位置差，同时保持向量模长不变。它在训练和推理都应用，编解码器均可用。

### single_choice · None



- [A] 不添加位置嵌入，而是直接在注意力分数上施加线性距离惩罚
- [B] 在词嵌入层加入可学习的位置向量
- [C] 使用正弦函数生成位置编码并加到输入上
- [D] 通过旋转查询和键向量来编码位置

**参考答案**：0

**解析**：ALiBi 不加位置嵌入，而是在注意力 logits 上加一个与距离成比例的负偏置（不同头斜率不同）。其余选项分别描述可学习位置嵌入、正弦编码和 RoPE。

### single_choice · None



- [A] 逐元素相加后送入后续层
- [B] 拼接后通过线性层投影回原维度
- [C] 作为额外的注意力头单独计算
- [D] 只加到解码器输出上，编码器不加

**参考答案**：0

**解析**：经典 Transformer 将位置编码与词嵌入逐元素相加。拼接再投影是另一种设计但非标准做法；它不是独立注意力头，也不只用于解码器输出。

### single_choice · None



- [A] 因为正弦函数对任意位置都有定义，编码可解析地计算到更长位置
- [B] 因为正弦编码的参数表会随序列长度自动增长
- [C] 因为正弦编码在训练时会记住所有可能的位置
- [D] 因为外推依赖词嵌入维度而非位置编码

**参考答案**：0

**解析**：正弦编码是位置的解析函数，任意位置都能计算，因而具备一定外推能力。它没有可增长参数表，也不会记住所有位置；外推与位置编码直接相关。

### single_choice · None



- [A] 位置编码是独立于词嵌入、用于注入词序信息的机制，可以是固定的或可学习的
- [B] 位置编码确实属于词嵌入，但只在解码器中存在
- [C] 位置编码只在推理时添加，训练时不添加
- [D] 位置编码必须与词嵌入维度不同才能生效

**参考答案**：0

**解析**：位置编码是独立机制，固定（如正弦）或可学习均可，目的是注入位置信息。它并非词嵌入的固有部分，也不只在解码器或只在推理时使用。

### single_choice · None



- [A] 可学习嵌入更灵活但受训练长度限制，外推能力较弱
- [B] 可学习嵌入外推能力更强，但训练更慢
- [C] 正弦编码可学习，因此比可学习嵌入更灵活
- [D] 两者完全相同，只是实现语言不同

**参考答案**：0

**解析**：可学习位置嵌入由数据驱动、更灵活，但参数量固定，超出训练长度难以外推；正弦编码固定且可解析外推，但灵活性较低。

### single_choice · None



- [A] 对 batch 维和序列维一起做归一化，不依赖特征维
- [B] 在最后一个维度（特征维/隐藏维）上做归一化，与 batch 大小无关
- [C] 只对 batch 维做归一化，因此对 batch size 敏感
- [D] 对序列长度维做归一化，因此推理时可以任意改变生成长度

**参考答案**：1

**解析**：LayerNorm 在每个样本内部对特征维（最后一维）计算均值与方差，因此不依赖 batch 中其他样本，batch=1 也能正常工作；这与 BatchNorm 依赖 batch 维形成对比。

### single_choice · None



- [A] 每个样本、每个位置的 4 个隐藏单元
- [B] 整个张量 24 个元素的全局统计量
- [C] 每个隐藏单元跨 2×3=6 个位置的统计量
- [D] 每个 batch 内 3×4=12 个元素的统计量

**参考答案**：0

**解析**：Last-dim LayerNorm 会对每个样本的每个 token 位置独立计算均值和方差，即对 hidden=4 这一维度归一化，因此共有 2×3=6 组统计量，每组覆盖 4 个值。

### multi_choice · None



- [A] 归一化在特征维上进行，与 batch 维无关
- [B] 含有可学习的缩放 γ 和平移 β 参数
- [C] 训练时维护 running mean/var 供推理使用
- [D] 除以 sqrt(σ² + ε) 以提升数值稳定性
- [E] 必须要求 batch size 大于 1 才能计算

**参考答案**：[0, 1, 3]

**解析**：LayerNorm 逐样本在特征维归一化，有 γ/β 可训练参数，并用 ε 保证数值稳定；它不维护 running statistics，也不要求 batch>1。

### multi_choice · None



- [A] Pre-LN 在进入子层前归一化，残差路径保持恒等
- [B] Post-LN 在残差相加后再归一化
- [C] Post-LN 通常需要更谨慎的学习率 warmup 才能稳定训练
- [D] Pre-LN 与 Post-LN 在数学上完全等价，只是写法不同
- [E] Pre-LN 时残差连接被 LayerNorm 破坏，无法训练深层网络

**参考答案**：[0, 1, 2]

**解析**：Pre-LN 先归一化再进子层、残差直通；Post-LN 先子层再加残差再归一化；Post-LN 通常对 warmup 更敏感。二者并不等价，Pre-LN 反而更利于深层稳定训练。

### multi_choice · None



- [A] 适当增大 ε，避免分母接近 0
- [B] 在计算统计量时使用更高精度（如 fp32 累积）
- [C] 改用更小的 ε（如 0）来降低误差
- [D] 在混合精度训练中让归一化部分保持在 fp32 计算

**参考答案**：[0, 1, 3]

**解析**：增大 ε、提升累积精度、在混合精度中保持归一化用 fp32，都是常见且合理的稳定化手段；把 ε 设为 0 会加大除零风险，不正确。

### multi_choice · None



- [A] 对 (B, S, H) 输入，默认通常对 H 维归一化
- [B] 对 (B, S, H) 输入，也可以对 (S, H) 维一起归一化，但这是不同实现选择
- [C] 归一化维度的选择会影响模型的表达能力和计算量
- [D] LayerNorm 只能对 H 维归一化，不允许其他选择

**参考答案**：[0, 1, 2]

**解析**：通过对最后一维归一化是 Transformer 的常见选择；也有一些实现选择对 (S,H) 整体归一化。不同归一化维度会改变行为，并非只允许 H 维。

### fill_blank · None



**参考答案**：["ε", "eps", "epsilon", "ε（epsilon）"]

**解析**：这个小常数通常记作 ε（epsilon），习惯写作 sqrt(σ² + ε)，用于保证数值稳定性。

### fill_blank · None



**参考答案**：["仿射", "affine", "仿射变换", "affine transform", "线性"]

**解析**：这步变换称为仿射变换（affine），它是 LayerNorm 恢复表示能力的关键，γ 和 β 分别控制缩放和平移。

### code_reading · None



**参考答案**：out 的形状仍为 (4, 10, 8)；LayerNorm(8) 对最后一维 hidden=8 做归一化，对 4×10=40 个 token 位置各自独立计算均值与方差。

**解析**：LayerNorm 不改变张量形状。传入 normalized_shape=8 表示对最后一维做归一化，因此每个 (batch, seq) 位置独立计算 8 个值的均值方差。

### code_reading · None



**参考答案**：相等。LayerNorm 没有 running statistics，eval 模式与 train 模式都基于当前输入实时计算均值方差；输入相同则输出相同。

**解析**：与 BatchNorm 不同，LayerNorm 不使用训练期累积统计量，因此 eval 模式不会改变前向计算，相同输入得到相同输出。

### scenario · None



**解析**：典型答案是改成 Pre-LN：把 LayerNorm 放到子层之前，使残差路径成为恒等映射，梯度回传更顺畅，深层网络更稳定；同时可保留或减弱学习率 warmup；如仍出现数值问题，可适当增大 ε 或在混合精度中让归一化用 fp32 计算。关键词覆盖 Pre-LN、残差、warmup、LayerNorm、eps、稳定性即可。

### single_choice · None



- [A] 它们只在前向推理时使用，训练中不更新
- [B] γ 初始化为 1、β 初始化为 0，二者都是可训练参数
- [C] 只有 γ 可训练，β 是固定的常量
- [D] 它们是被归一化数据的实时均值与方差，不是参数

**参考答案**：1

**解析**：LayerNorm 在归一化后再做 γ·x̂ + β 的仿射变换，γ 和 β 是本层可训练参数，通常分别初始化为全 1 和全 0，用于恢复网络的表示能力。

### single_choice · None



- [A] 控制归一化后输出的最大幅度
- [B] 防止方差为 0 时出现除零或数值溢出，保证数值稳定
- [C] 作为学习率缩放系数影响收敛速度
- [D] 计算均值时排除异常值

**参考答案**：1

**解析**：ε 是一个很小的常数，加在方差上避免分母为 0，从而提升数值稳定性，尤其在 fp16 等低精度场景下很关键。

### single_choice · None



- [A] 需要，训练时累积统计量，推理时用累积值
- [B] 不需要，统计量在每次前向时由当前样本实时计算
- [C] 需要，因为 LayerNorm 本质上与 BatchNorm 统计逻辑相同
- [D] 只在 batch size 大于 1 时需要累积

**参考答案**：1

**解析**：LayerNorm 是逐样本实时计算均值方差，不存在 running statistics，训练与推理行为一致，因此不依赖 batch。running mean/var 是 BatchNorm 的机制。

### single_choice · None



- [A] LayerNorm 使用的是 γ 还是 β
- [B] LayerNorm 放在子层（如注意力/FFN）之前还是残差相加之后
- [C] LayerNorm 的 ε 取值大小
- [D] LayerNorm 归一化的维度是 hidden 还是 seq

**参考答案**：1

**解析**：Pre-LN 指在进入子层之前先做归一化（残差直通），Post-LN 指在子层输出与残差相加之后再归一化。二者影响训练稳定性与是否需 warmup。

### single_choice · None



- [A] Pre-LN 参数量更少，更容易优化
- [B] 残差路径上保持了近似恒等映射，梯度可以更直接地回传
- [C] Pre-LN 会把所有激活值置为相同分布，从而消除梯度
- [D] Pre-LN 不用计算均值方差，节省算力

**参考答案**：1

**解析**：Pre-LN 时残差连接直接从输入连到输出，主干近似恒等映射，梯度沿残差路径回传不易衰减，因此训练更稳定，通常可减弱对学习率 warmup 的依赖。

### single_choice · None



- [A] 二者是同一件事，缩放点积就是 LayerNorm
- [B] 缩放点积属于对注意力 logits 的尺度控制，与 LayerNorm 在子层前后的归一化是不同机制
- [C] 缩放点积是为了让 LayerNorm 的 ε 失效
- [D] 缩放点积只在 Pre-LN 中存在，Post-LN 不需要

**参考答案**：1

**解析**：除以 sqrt(d_k) 是防止点积随维度增大而数值过大导致 softmax 饱和的尺度缩放；LayerNorm 是对特征维的归一化。两者作用不同，不要混为一谈。

### single_choice · None



- [A] 因为 batch 变大，统计量会随之变化
- [B] 每个样本的统计量仍只由自身决定，逐样本结果不变
- [C] 统计量会取跨 batch 的平均，从而改变输出
- [D] 会报错，因为 LayerNorm 要求 batch 固定

**参考答案**：1

**解析**：LayerNorm 逐样本计算统计量，与 batch 中其他样本无关，所以改变 batch size 不会改变单个样本的归一化结果（数值误差除外）。

### single_choice · None



- [A] LayerNorm 推理时冻结参数，BatchNorm 推理时更新参数
- [B] LayerNorm 推理时行为与训练一致，BatchNorm 推理通常使用训练期累积的统计量
- [C] 两者推理时都必须使用 running statistics
- [D] LayerNorm 不能在推理阶段使用

**参考答案**：1

**解析**：BatchNorm 训练时用 batch 统计量、推理时用 running mean/var，存在训练-推理不一致；LayerNorm 没有 running statistics，训练与推理行为一致。
