# s6u3l4 LLM 训练三阶段：预训练、SFT 与 RLHF / 从 LoRA 到 QLoRA：大模型微调的“够用就行”指南

> 来源 `content/lessons/s6u3l4.json`

## ai.llm.pretrain_sft_rlhf

# LLM 训练三阶段：预训练、SFT 与 RLHF

> **一句话直觉**：想让一个“只会接话”的模型变成“听话、安全、有用”的助手，需要先让它读书（预训练），再教它答题（SFT），最后按人类偏好调教它（RLHF）——这就是 ChatGPT 类模型的诞生流水线。

---

## 一、为什么需要三个阶段？

大语言模型（Large Language Model, LLM）不是一步训练出来的。原始互联网文本只告诉模型“下一个词是什么”，但用户想要的是“帮我写邮件/写代码/拒绝有害请求”。于是业界形成了三段式范式：

| 阶段 | 目标 | 数据形态 | 成本 |
|---|---|---|---|
| 预训练（Pretrain） | 学会语言与世界知识 | 海量无标注文本 | 极高 |
| 监督微调（SFT） | 学会“听懂指令” | 指令-回答对 | 中 |
| 人类反馈强化学习（RLHF） | 学会“符合人类偏好” | 人类排序 + 奖励模型 | 高 |

下面的代码用一个极简的手写小模型（n-gram 风格）来演示三个阶段的数据形态和损失计算思路，方便零基础理解。

---

## 二、预训练（Pretrain）：自监督的“下一个词预测”

**核心目标**：给定前文，预测下一个 token。没有标签，文本自己就是标签，这叫自监督（self-supervised）。

```python
# 预训练直觉：给定前 N 个词，模型要预测第 N+1 个词
corpus = "the cat sat on the mat the cat ate the fish".split()

# 用 2-gram 计数模拟“模型参数”
from collections import defaultdict, Counter
bigram = defaultdict(Counter)
for a, b in zip(corpus, corpus[1:]):
    bigram[a][b] += 1

# 预测下一个词
print(bigram["the"])  # Counter({'cat': 2, 'mat': 1, 'fish': 1})
```

> 真实 GPT 只是把 2-gram 换成几十层 Transformer，把词表扩大到几万 token，把语料换成 TB 级文本。**目标函数完全一样**：最大化下一 token 的对数似然。

**关键特征**：
- 数据：Common Crawl、书籍、代码，几十 TB。
- 产物：Base Model（只会续写，不会对话）。
- 代价：一次训练动辄几百万美元。

---

## 三、SFT：用“指令-回答”对教它对话

**核心目标**：让 Base Model 学会“见到指令就输出答案”的格式。做法依然是下一 token 预测，但只对答案部分算损失。

```python
# SFT 数据长这样：prompt + response
sft_sample = {
    "prompt": "用户：把下面翻译成英文：你好\n助手：",
    "response": "Hello"
}

# 关键：损失只算在 response 上（prompt 部分 mask 掉）
tokens = list(sft_sample["prompt"]) + list(sft_sample["response"])
loss_mask = [0] * len(sft_sample["prompt"]) + [1] * len(sft_sample["response"])
print(list(zip(tokens, loss_mask)))
```

> 注意最后几组 `('H',1), ('e',1), ('l',1), ('l',1), ('o',1)`——只有这些位置的预测误差会回传梯度。这是 SFT 与预训练在实现上最重要的一点差别。

**关键特征**：
- 数据量：几千到几十万条人工写的高质量对话。
- 产物：Instruction-tuned Model（会对话了，但仍可能跑偏/有害）。
- 训练 1~3 epochs 即可，过多会过拟合。

---

## 四、RLHF：用人类偏好排序做奖励

SFT 后模型“会答”，但答案好坏参半。RLHF 分两步：

**Step 1：训练奖励模型（Reward Model, RM）**
人类对同一 prompt 的多个回答排序：A > B > C。RM 学习给 A 高分、C 低分。

**Step 2：用强化学习（PPO）优化策略模型**
让模型生成答案 → RM 打分 → 用 PPO 更新参数，同时加 KL 惩罚防止它偏离 SFT 模型太远。

```python
# 用极小例子模拟 RLHF 的奖励与 KL 惩罚思想
import math

sft_logprob = math.log(0.5)   # 原 SFT 模型对答案的概率
tuned_logprob = math.log(0.8) # 新模型对同一答案的概率
reward = 1.0                  # 奖励模型给的分
beta = 0.1                    # KL 系数

# PPO 目标（简化版）：reward - beta * KL
kl = math.exp(sft_logprob) * (sft_logprob - tuned_logprob)  # 简化 KL
objective = reward - beta * kl
print("训练目标：", objective)
```

> KL 惩罚 (Kullback-Leibler divergence) 是 RLHF 稳定的关键：它约束新模型不要为了骗高分而输出乱七八糟的东西（reward hacking）。

**关键特征**：
- 数据：人类排序对，几千到几万条。
- 产物：Align Model（GPT-3.5 / ChatGPT 级别）。
- 后续进化：DPO（Direct Preference Optimization）省去 RM，直接偏好优化；RLAIF 用 AI 反馈代替人类。

---

## 五、三阶段串联与工程实践

```
Pretrain  ->  Base LLM  --SFT-->  SFT LLM  --RLHF/DPO-->  Aligned LLM
   TB 级文本       指令对             人类偏好对
   数百万美元       数千美元            数万美元
```

**落地建议**：
1. 个人/小团队通常只做 SFT 或 DPO，预训练用开源模型（Llama、Qwen、Mistral）。
2. SFT 数据质量 > 数量，1000 条精标数据常胜过 10 万条脏数据。
3. RLHF 计算成本高、调参难，2024 年后更推荐先试 DPO。

---

## 六、动手练习

**任务**：用 Python 手写一个迷你三阶段流水线（不需要 GPU）。

1. 准备一段英文句子作为“预训练语料”，用字典构建 2-gram 计数模型。
2. 构造 3 条 SFT 数据：`{"prompt": ..., "response": ...}`，并生成对应的 loss mask。
3. 模拟 RLHF：给两个候选回答打分（自己指定分数），计算 `reward - 0.1 * KL` 形式的训练目标。
4. 输出：三个阶段各自的数据格式与一行说明。

**提交标准**：代码可运行，能打印出三阶段的数据结构与目标值。

---

**术语速查**：Pretrain（预训练）、SFT（Supervised Fine-Tuning，监督微调）、RLHF（Reinforcement Learning from Human Feedback，基于人类反馈的强化学习）、PPO（Proximal Policy Optimization，近端策略优化）、KL（Kullback-Leibler divergence，KL 散度）、DPO（Direct Preference Optimization，直接偏好优化）。

```python
# mini_pipeline.py —— 三阶段迷你流水线（纯 Python，无依赖）
import math
from collections import defaultdict, Counter

# ============ 阶段 1：预训练（2-gram 语言模型） ============
corpus = "the cat sat on the mat the cat ate the fish".split()
bigram = defaultdict(Counter)
for a, b in zip(corpus, corpus[1:]):
    bigram[a][b] += 1
print("[Pretrain] 给定 'the'，下一词分布：", bigram["the"])

# ============ 阶段 2：SFT（指令-回答对 + loss mask） ============
sft_data = [
    {"prompt": "Q: 1+1=? A:", "response": "2"},
    {"prompt": "Q: 首都是? A:", "response": "北京"},
    {"prompt": "Q: say hi A:", "response": "hi"},
]
for d in sft_data:
    tokens = list(d["prompt"]) + list(d["response"])
    mask = [0] * len(d["prompt"]) + [1] * len(d["response"])
    print("[SFT] tokens:", tokens, "| loss_mask:", mask)

# ============ 阶段 3：RLHF（奖励 + KL 惩罚） ============
reward = 1.2                      # 奖励模型对当前回答的打分
beta = 0.1                        # KL 惩罚系数
p_sft = 0.5                       # 原 SFT 模型生成该答案的概率
p_new = 0.8                       # 新模型生成该答案的概率
kl = p_sft * (math.log(p_sft) - math.log(p_new))   # 简易 KL 估计
objective = reward - beta * kl
print(f"[RLHF] reward={reward}, KL={kl:.4f}, objective={objective:.4f}")
```

## ai.llm.lora_qlora

# 从 LoRA 到 QLoRA：大模型微调的“够用就行”指南

> **一句话直觉**：大模型全量微调太贵，LoRA 用“打补丁”的方式只训练一小撮参数，QLoRA 再把底座压缩到 4-bit（比特），让你用一张普通显卡也能微调上百亿参数（billion-parameter）的模型。

本节面向零基础到工程级，共 5 小节，每节都配一段可运行的 Python（Programming Language，程序设计语言）代码。建议你在本地创建一个 `lora_qlora.ipynb` 或 `demo.py` 跟着敲。

---

## 1. 为什么需要 LoRA？

### 1.1 全量微调的痛点

微调（fine-tuning，微调）一个大语言模型（LLM，Large Language Model）意味着：

- 参数量：例如 7B（70 亿参数）模型，用 float32（32 位浮点）保存需要 28 GB 显存；
- 优化器（optimizer，优化器）状态：Adam（自适应矩估计，Adaptive Moment Estimation）还要再存 2 份梯度/动量，总显存 ~ 4 倍参数量；
- 结果：单卡 24 GB 显存连 7B 全量微调都跑不起来。

### 1.2 LoRA 的核心思想

LoRA（Low-Rank Adaptation，低秩适配）把原来的权重矩阵 $W \in \mathbb{R}^{d \times k}$ 冻结，只在旁边加一个可训练的低秩分解：

$$\Delta W = B A, \quad B \in \mathbb{R}^{d \times r},\ A \in \mathbb{R}^{r \times k},\ r \ll \min(d,k)$$

训练时只更新 $A$ 和 $B$，原模型不动。这样：

- 可训练参数从 $d \times k$ 降到 $r\,(d+k)$，通常减少 **100~1000 倍**；
- 推理（inference，推理）时可以把 $BA$ 合并回 $W$，**不增加推理延迟**；
- 每个任务存一个几 MB 的 LoRA 权重即可，方便切换。

### 1.3 代码：用纯 NumPy 理解 LoRA 的“打补丁”

下面这段不依赖任何深度学习框架，只用 NumPy（Numerical Python，数值计算库）演示 LoRA 的数学本质。

```python
import numpy as np

# 假设原始权重 W: d=1024, k=1024
W = np.random.randn(1024, 1024).astype(np.float32)
# LoRA 秩 r 远小于 d,k
r = 8
A = np.random.randn(r, 1024).astype(np.float32) * 0.01
B = np.zeros((1024, r), dtype=np.float32)   # B 初始化为 0 -> 初始 ΔW=0

x = np.random.randn(1024).astype(np.float32)

# 前向：y = (W + BA) x = Wx + B(Ax)
y_full = (W + B @ A) @ x            # 合并后推理

# 等价的高效写法：不算 BA，先算 Ax 再算 B(Ax)
y_lora = W @ x + B @ (A @ x)

print('可训练参数量:', A.size + B.size)          # 16*1024 = 16384
print('原始参数量  :', W.size)                    # 1048576
print('两种前向是否等价:', np.allclose(y_full, y_lora, atol=1e-5))
```

**关键结论**：LoRA 不是“改模型”，而是在原权重上叠加一个低秩增量；初始时 $B=0$，所以训练开始时模型输出与原模型完全一致。

---

## 2. LoRA 的关键超参数

工程上你主要调 3 个参数：

| 参数 | 含义 | 常用取值 | 影响 |
|------|------|----------|------|
| `r`（秩，rank） | 低秩矩阵的秩 | 4 / 8 / 16 / 32 | 越大容量越强，参数越多 |
| `lora_alpha` | 缩放因子 $\alpha$ | 通常等于 r 或 2r | 与 $\tfrac{\alpha}{r}$ 一起决定更新强度 |
| `lora_dropout` | 丢弃率 | 0 ~ 0.1 | 防止过拟合（overfitting，过拟合） |

LoRA 的实际更新是：

$$h = W x + \frac{\alpha}{r} B A x$$

### 2.1 代码：手动实现一次 LoRA 前向 + 反向

```python
import numpy as np

np.random.seed(0)
d, k, r = 64, 64, 4
alpha = 8.0

# 冻结的原权重
W = np.random.randn(d, k).astype(np.float32)
# 可训练参数
A = (np.random.randn(r, k) * 0.01).astype(np.float32)
B = np.zeros((d, r), dtype=np.float32)

x = np.random.randn(k).astype(np.float32)
scale = alpha / r

def forward(W, A, B, x, scale):
    return W @ x + scale * (B @ (A @ x))

# 假设目标 y 就是原模型输出（模拟拟合）
y = W @ x
lr = 1e-2

for step in range(200):
    # 前向
    Ax = A @ x
    Bx = B @ Ax
    out = W @ x + scale * Bx
    loss = 0.5 * np.sum((out - y) ** 2)
    # 反向（只更新 A, B）
    grad_out = (out - y)                        # d
    grad_B = scale * np.outer(grad_out, Ax)     # d x r
    grad_A = scale * np.outer(B.T @ grad_out, x[None, :])  # r x k
    B -= lr * grad_B
    A -= lr * grad_A
    if step % 50 == 0:
        print(f'step={step}, loss={loss:.6f}')

print('最终 loss:', loss)
```

**关键结论**：LoRA 反向传播的梯度只流经 `A`、`B`，`W` 始终不变，这就是它能省显存的根本原因。

---

## 3. QLoRA：把底座“压”到 4-bit

### 3.1 量化（quantization，量化）基础

量化就是用更少的比特表示参数。QLoRA（Quantized LoRA，量化 LoRA）的核心是 **4-bit NormalFloat（NF4）**：

- 把权重按分位数映射到 4-bit 的 16 个值；
- 再配合 **双重量化（double quantization）** 量化缩放因子，进一步省内存；
- 用 **分页优化器（paged optimizer）** 把优化器状态换出到 CPU（中央处理器，Central Processing Unit）内存，避免显存峰值崩溃。

结果：7B 模型底座只需 ~4 GB 显存，配合 LoRA 就能在 8 GB 显存的消费级显卡上微调。

### 3.2 代码：模拟 4-bit 分块量化

```python
import numpy as np

def quantize_4bit(tensor, block_size=64):
    """把 float32 张量按块量化到 4-bit（16 个等级）。"""
    flat = tensor.flatten()
    n = flat.size
    pad = (-n) % block_size
    if pad:
        flat = np.concatenate([flat, np.zeros(pad, dtype=flat.dtype)])
    blocks = flat.reshape(-1, block_size)
    # 每个 block 存一个 scale（实际 QLoRA 会再做一次量化）
    scales = np.abs(blocks).max(axis=1, keepdims=True) / 7.0  # [-8,7] 共 16 级
    scales[scales == 0] = 1e-8
    q = np.round(blocks / scales).clip(-8, 7).astype(np.int8)
    return q, scales, pad

def dequantize_4bit(q, scales, pad):
    out = (q.astype(np.float32) * scales).flatten()
    if pad:
        out = out[:-pad]
    return out

W = np.random.randn(256, 256).astype(np.float32)
q, scales, pad = quantize_4bit(W)
W_hat = dequantize_4bit(q, scales, pad)

print('原始大小 (float32):', W.nbytes, 'bytes')
print('量化后存储 (4-bit):', q.nbytes, 'bytes (约 1/8)')
print('误差 MAE:', np.abs(W.flatten() - W_hat).mean())
```

**关键结论**：4-bit 量化让底座内存降到 1/8 左右，代价是可接受的精度损失（通常下游任务只掉 1~2 个点）。

---

## 4. 工程实战：用 PEFT + bitsandbytes 跑 QLoRA

真实项目里我们不用手写这些，直接用 Hugging Face 生态：

- `bitsandbytes`：提供 4-bit / 8-bit 量化算子；
- `peft`（Parameter-Efficient Fine-Tuning，参数高效微调库）：提供 `LoraConfig` 和 `get_peft_model`；
- `transformers`：加载模型与分词器。

### 4.1 代码：QLoRA 最小可运行模板

```python
# pip install transformers peft bitsandbytes accelerate datasets
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

model_id = "Qwen/Qwen2.5-0.5B"   # 用最小的模型演示，换成 7B 同理

# 1) 4-bit 量化配置
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",            # NormalFloat4
    bnb_4bit_use_double_quant=True,       # 双重量化省内存
    bnb_4bit_compute_dtype=torch.float16, # 计算时用 fp16
)

# 2) 加载量化底座
tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(
    model_id,
    quantization_config=bnb_config,
    device_map="auto",
    trust_remote_code=True,
)

# 3) 准备 k-bit 训练（让 layer norm、lm_head 用 fp32/混合精度）
model = prepare_model_for_kbit_training(model)

# 4) LoRA 配置
lora_config = LoraConfig(
    r=8,
    lora_alpha=16,
    lora_dropout=0.05,
    bias="none",
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],  # 只加在注意力投影上
    task_type="CAUSAL_LM",
)

# 5) 注入 LoRA
model = get_peft_model(model, lora_config)
model.print_trainable_parameters()

# ---- 极简训练循环（真实项目建议用 Trainer 或 trl）----
texts = [
    "LoRA 是一种低秩适配方法。",
    "QLoRA 用量化降低显存占用。",
    "参数高效微调让大模型更亲民。",
]
enc = tokenizer(texts, return_tensors="pt", padding=True, truncation=True, max_length=64)
enc = {k: v.to(model.device) for k, v in enc.items()}
enc["labels"] = enc["input_ids"].clone()

model.train()
opt = torch.optim.AdamW(filter(lambda p: p.requires_grad, model.parameters()), lr=1e-4)

for step in range(5):
    out = model(**enc)
    loss = out.loss
    loss.backward()
    opt.step()
    opt.zero_grad()
    print(f"step={step}, loss={loss.item():.4f}")
```

**关键结论**：工程上 QLoRA = `BitsAndBytesConfig(load_in_4bit=True)` + `LoraConfig(...)` + `prepare_model_for_kbit_training`。三行核心配置，就能把 7B 微调塞进单张消费级显卡。

---

## 5. 什么时候用 LoRA / QLoRA？

- **数据量小（< 10 万条）、任务单一**：LoRA 足够，`r=8~16`；
- **显存紧张（≤ 16 GB）**：上 QLoRA，注意 `bnb_4bit_compute_dtype` 要用 fp16/bf16；
- **需要多任务切换**：每个任务保存一个 LoRA adapter，几 MB，热插拔；
- **追求极致质量、预算充足**：全量微调仍然可能更优，但成本高一个数量级。

选型口诀：**“小数据用 LoRA，小显存用 QLoRA，多任务用 Adapter 切换，不缺钱才全量微调。”**

---

## 6. 动手练习（本地完成）

**任务**：用 QLoRA 微调一个 0.5B 的中文小模型，让它学会“把输入句子改写成疑问句”。

具体要求：

1. 准备 100 条“陈述句 → 疑问句”的配对数据，存成 JSONL（JSON Lines，行式 JSON）格式，例如：
   ```json
   {"input":"今天天气很好。","output":"今天天气好吗？"}
   ```
2. 用 `Qwen/Qwen2.5-0.5B` 作为底座，按照第 4 节的模板加 4-bit + LoRA；
3. 训练 1~3 个 epoch（轮次），观察 loss 是否下降；
4. 训练结束后用 `model.save_pretrained("my_lora")` 保存 adapter，比较保存前后的文件大小（应该只有几 MB）；
5. 用 `PeftModel.from_pretrained(base_model, "my_lora")` 加载，测试 3 条新句子，看是否变成疑问句。

**提交物**：一份 `train.py` + 一段 3 条推理结果的截图 + 一段 100 字总结（说明你的 `r`、`alpha`、学习率是怎么选的）。


---

## 本课题目

### single_choice · None



- [A] 预训练、监督微调、基于人类反馈的强化学习
- [B] 监督微调、预训练、基于人类反馈的强化学习
- [C] 预训练、基于人类反馈的强化学习、监督微调
- [D] 基于人类反馈的强化学习、监督微调、预训练

**参考答案**：0

**解析**：先在无标注文本上做下一个词预测属于预训练；在标注的「问题-答案」上微调属于监督微调；利用人工偏好排序优化属于基于人类反馈的强化学习。顺序颠倒即错。

### single_choice · None



- [A] 预训练目标只是预测下一个词，模型没有被专门训练成遵循指令
- [B] 模型参数量太小，无法理解任何指令
- [C] 预训练数据中完全没有出现过「过拟合」这个词
- [D] 模型在预训练时已经发生了严重的灾难性遗忘

**参考答案**：0

**解析**：纯预训练模型学习的是续写分布，缺少「按指令作答」的对齐训练，因此容易续写而非回答。参数量、词是否出现、灾难性遗忘都不是最直接原因。

### single_choice · None



- [A] 监督微调直接模仿给定的标准答案；RLHF 用奖励信号引导模型向更受偏好的方向优化
- [B] 监督微调使用无标注数据；RLHF 只使用无标注数据
- [C] 监督微调不更新任何参数；RLHF 才更新参数
- [D] 两者完全等价，只是名称不同

**参考答案**：0

**解析**：监督微调是模仿学习，目标是复现示范输出；RLHF 通过奖励模型间接优化偏好。两者都更新参数，也都可能用到不同形式的数据，并非等价。

### single_choice · None



- [A] 模型可能还不具备基本的指令遵循能力，探索空间过大，强化学习很难稳定起步
- [B] 预训练模型无法计算任何损失
- [C] 奖励模型无法被训练
- [D] 人类无法对回答进行偏好比较

**参考答案**：0

**解析**：监督微调常为 RLHF 提供较好的初始策略，使模型至少能按指令生成合理回答。完全跳过时，策略起点太差，强化学习探索困难。损失计算、奖励模型训练、人类比较本身并不因此失效。

### single_choice · None



- [A] 让模型学会针对具体问题给出简洁答案
- [B] 让模型从大规模文本中学习通用的语言规律和世界知识
- [C] 让模型学会完全按照人类偏好排序
- [D] 让模型只记住训练集中的每一句话

**参考答案**：1

**解析**：预训练通过大规模文本上的自监督目标学习通用表示与知识。针对问题作答主要靠后续微调；偏好排序属于 RLHF；逐句记忆不是目标且会带来过拟合。

### single_choice · None



- [A] 单个回答及其绝对质量分
- [B] 同一个提示下的多个回答及人类对它们的偏好排序
- [C] 只有无标注的网页文本
- [D] 模型内部的梯度向量

**参考答案**：1

**解析**：奖励模型通常从同一提示下多个回答的偏好比较中学习打分。绝对分、无标注文本、梯度向量都不是该阶段的标准训练数据形式。

### single_choice · None



- [A] 可以利用人类对「哪个回答更好」的细粒度比较，优化那些难以用单一标准答案表达的目标
- [B] 可以完全不需要任何训练数据
- [C] 可以保证模型永远不会犯错
- [D] 可以让预训练阶段自动完成

**参考答案**：0

**解析**：RLHF 擅长优化难以用监督信号直接表达的主观或复杂目标，如帮助性与安全性的权衡。它仍需数据，无法保证零错误，也不会自动完成预训练。

### single_choice · None



- [A] 模型在微调数据上表现变差，甚至遗忘预训练阶段学到的能力
- [B] 预训练数据会自动增加
- [C] 奖励模型会自动生成
- [D] 模型参数量会减少

**参考答案**：0

**解析**：学习率过大可能导致微调不稳定、过拟合或灾难性遗忘，损害原有能力。数据、奖励模型、参数量都不会因此自动变化。

### single_choice · None



- [A] RLHF 只优化人类偏好，可能在偏好与事实正确性不完全一致时产生偏差
- [B] RLHF 会删除模型中的所有知识
- [C] 监督微调数据全部是错误答案
- [D] 预训练从未学习过任何事实

**参考答案**：0

**解析**：偏好信号与客观正确性并不总是一致，过度优化偏好可能导致事实性下降，即对齐税的一种表现。删除全部知识、SFT 全错、预训练零事实都过于绝对。

### single_choice · None



- [A] 预训练像广泛阅读积累知识，监督微调像跟着范例学习答题格式，RLHF 像根据用户反馈调整回答风格
- [B] 预训练像考试，监督微调像玩耍，RLHF 像睡觉
- [C] 三者互相独立，没有任何先后依赖
- [D] RLHF 必须在预训练之前完成

**参考答案**：0

**解析**：该比喻对应三阶段的功能：积累、模仿示范、基于偏好调整。三者有典型先后顺序，并非完全独立，RLHF 也不是在预训练之前。

### single_choice · None



- [A] 奖励模型过拟合了偏好数据，泛化到新回答的能力不足
- [B] 策略模型没有参数
- [C] 预训练数据太少
- [D] 人类偏好比较数据完全无效

**参考答案**：0

**解析**：奖励模型在偏好训练集上表现好但在新样本上差，是过拟合与分布外泛化不足的典型表现。策略模型无参数或偏好数据完全无效都不符合事实。

### single_choice · None



- [A] 模型会放大自身已有的错误，缺乏外部正确示范的纠正
- [B] 模型会自动获得人类偏好
- [C] 预训练阶段会被自动跳过
- [D] 奖励模型会变得不必要

**参考答案**：0

**解析**：只用模型自生成数据做模仿，容易固化甚至放大已有错误，缺少人类示范的纠偏。它不会自动获得偏好，也不会跳过预训练或让奖励模型消失。

### single_choice · None



- [A] 大量无标注的网页文本
- [B] 人工编写的「输入-期望输出」配对样本
- [C] 只包含人类对两个回答的偏好排序
- [D] 随机生成的噪声向量

**参考答案**：1

**解析**：监督微调使用带标签的输入-输出对，让模型学会按期望方式回应。无标注文本属于预训练；偏好排序属于 RLHF 的奖励建模阶段；噪声向量与该阶段无关。

### single_choice · None



- [A] 它指用人类提供的偏好信号来训练奖励模型，再用强化学习优化语言模型
- [B] 它指人类直接手动修改模型的每一层权重
- [C] 它指完全不需要强化学习的监督训练
- [D] 它指只使用人类写的文章做预训练

**参考答案**：0

**解析**：RLHF 的核心是人类反馈构建奖励信号，并通过强化学习更新策略。手动改权重、无强化学习、仅人类文章预训练都不符合其含义。

### single_choice · None



- [A] 需要的数据量通常小得多，但数据质量要求高
- [B] 必须使用比预训练更大的数据集
- [C] 完全不需要任何标注
- [D] 只能训练模型最后一层，其他层必须冻结

**参考答案**：0

**解析**：监督微调一般用远少于预训练的数据，但样本需精心标注。它并非必须更大数据，也不是无标注，参数也并非只能训练最后一层。

### single_choice · None



- [A] 直接生成最终回答
- [B] 把人类偏好排序中学到的偏好转化为可自动计算的奖励信号
- [C] 替代预训练过程重新训练语言模型
- [D] 删除训练数据中的重复样本

**参考答案**：1

**解析**：奖励模型从人类偏好比较中学习，为策略模型生成的回答打分，从而在强化学习中充当自动奖励。它不直接生成回答，也不替代预训练或做数据清洗。

### single_choice · None



- [A] 最小化预训练损失
- [B] 最大化奖励模型给出的分数（通常还带一个与初始模型的偏离约束）
- [C] 最大化训练集的准确率
- [D] 最小化模型参数量

**参考答案**：1

**解析**：强化学习阶段让策略模型生成更受奖励模型偏好的回答，同时常用 KL 等约束防止偏离初始模型太远。预训练损失、分类准确率、参数量都不是该阶段的直接优化目标。

### single_choice · None



- [A] 模型只会输出单一重复的词
- [B] 模型会钻奖励模型的空子，生成在奖励模型上得分高但实际质量差的回答
- [C] 预训练阶段会失败
- [D] 监督微调数据会自动增加

**参考答案**：1

**解析**：缺少偏离约束时，策略可能过度优化奖励模型的缺陷，出现奖励黑客现象。单一重复词、预训练失败、数据自动增加都不是该约束缺失的直接后果。

### single_choice · None



- [A] 三个阶段都必须使用人工标注数据
- [B] 预训练阶段通常使用无标注数据，后两个阶段需要不同程度的人工参与
- [C] 监督微调阶段完全不使用人工数据
- [D] 基于人类反馈的强化学习阶段不需要任何模型训练

**参考答案**：1

**解析**：预训练一般无需标注；监督微调需要人工编写或筛选的示范；RLHF 需要人类偏好比较。因此后两阶段有人工参与，但不等于三阶段都全量人工标注。

### single_choice · None



- [A] 收集人类对模型多个回答的偏好比较数据
- [B] 重新用网页文本做下一个词预测
- [C] 直接把模型参数量翻倍
- [D] 删除监督微调数据

**参考答案**：0

**解析**：RLHF 通常先收集人类对成对或多个回答的偏好比较，再训练奖励模型并用强化学习优化策略。重做预训练、扩参、删数据都不属于该流程。

### single_choice · None



- [A] 因为绝对分数在数学上无法定义
- [B] 因为比较判断通常比给出一致的绝对分数更容易、更可靠
- [C] 因为比较数据不需要任何人工成本
- [D] 因为只有比较数据才能用于监督学习

**参考答案**：1

**解析**：人类对「哪个更好」的判断往往比稳定的绝对打分更容易达成一致，因此偏好比较常被用来训练奖励模型。绝对分数并非无法定义，比较同样有人工成本，也不是唯一可用于监督学习的形式。

### single_choice · None



- [A] LoRA 会更新原始权重矩阵 W 的全部参数
- [B] LoRA 冻结原始权重 W，只训练新增的低秩矩阵 A 和 B
- [C] LoRA 会删除原始权重矩阵 W，仅保留低秩矩阵
- [D] LoRA 只训练偏置项 bias，不训练权重矩阵

**参考答案**：1

**解析**：LoRA 的核心思想是冻结预训练权重 W，在其旁路注入两个低秩矩阵 A 和 B，只训练这两个小矩阵，从而大幅减少可训练参数量。

### single_choice · None



- [A] r 必须等于 d 才能保证效果
- [B] r 通常远小于 min(d, k)，以降低参数量和计算开销
- [C] r 必须大于 k，否则无法训练
- [D] r 越大参数越少，所以应取尽量大的值

**参考答案**：1

**解析**：LoRA 的秩 r 是超参数，通常取 4、8、16 等远小于原始维度的值，这样新增参数量为 r*(d+k)，远低于 d*k，从而高效微调。

### multi_choice · None



- [A] 显著减少可训练参数量，降低显存和存储需求
- [B] 不同任务的适配器可以分别保存，便于在同一基础模型上切换
- [C] 推理时可合并权重，不引入额外延迟
- [D] LoRA 一定比全量微调效果更好，任何任务都适用

**参考答案**：[0, 1, 2]

**解析**：LoRA 的优势包括参数高效、便于多任务切换、可合并推理；但它并不保证在所有任务上都优于全量微调，效果依赖数据和超参。

### multi_choice · None



- [A] QLoRA 的基础模型以 4-bit 量化存储，LoRA 的基础模型通常保持较高精度
- [B] 两者都只训练低秩适配器，不更新基础权重
- [C] QLoRA 通过量化进一步降低了基础模型的显存占用
- [D] QLoRA 的适配器也必须以 4-bit 训练才能工作
- [E] QLoRA 不需要 LoRA 适配器即可微调

**参考答案**：[0, 1, 2]

**解析**：QLoRA 的关键是 4-bit 量化基础模型 + 高精度 LoRA 适配器训练；适配器仍以较高精度训练，量化的是基础权重；QLoRA 依然依赖 LoRA 适配器。

### multi_choice · None



- [A] 秩 r
- [B] 缩放参数 α
- [C] dropout 比例（LoRA dropout）
- [D] 目标模块 target_modules
- [E] 随机种子必须固定为 42

**参考答案**：[0, 1, 2, 3]

**解析**：r、α、dropout、target_modules 都是 LoRA 常见的配置项；随机种子虽可设置，但固定为 42 并非必要或规定要求。

### multi_choice · None



- [A] 多个不同任务的 LoRA 适配器可以共享同一个基础模型
- [B] 适配器是较小的权重增量，存储和分发成本低于完整模型
- [C] 训练时基础模型权重可以保持冻结
- [D] 适配器必须和基础模型参数量相同才能加载

**参考答案**：[0, 1, 2]

**解析**：LoRA 适配器参数量远小于基础模型，可多任务共享基础模型并独立保存；训练时基础权重冻结；加载时并不要求参数量相同。

### fill_blank · None



**参考答案**：["秩", "rank", "r 值"]

**解析**：r 是 LoRA 的低秩维度，即分解矩阵的秩，直接决定新增参数量与适配能力，是核心超参数。

### fill_blank · None



**参考答案**：["NF4", "nf4", "4-bit NormalFloat"]

**解析**：NF4 即 4-bit NormalFloat，是 QLoRA 使用的量化数据类型，基于分位数量化，在正态分布权重上信息损失较小。

### fill_blank · None



**参考答案**：["α", "alpha", "lora_alpha"]

**解析**：α（常写作 lora_alpha）是缩放参数，与 r 共同决定缩放因子 α/r，用于控制低秩更新的幅度。

### code_reading · None



**参考答案**：输出与原始预训练模型完全相同（或几乎相同）。因为 B 被初始化为零矩阵，所以 (alpha/r)*(B@(A@x)) = 0，旁路项不产生任何贡献，模型表现与原始 W 一致。

**解析**：B 零初始化保证训练起点不破坏预训练模型的行为，随训练推进 B 才逐渐学出非零增量，这是 LoRA 稳定训练的关键设计。

### code_reading · None



**参考答案**：合并后模型结构与原基础模型完全一致，只需一次矩阵乘法，不增加额外计算分支和推理延迟，同时省去了维护单独适配器分支的开销。

**解析**：LoRA 的可合并性使其在部署时无额外推理成本，这是相对其他某些参数高效方法的重要优势。

### scenario · None



**解析**：在显存非常受限时 QLoRA 更合适：它把基础模型量化到 4-bit 存储以大幅降低显存占用，同时仍以较高精度训练 LoRA 适配器；相比标准 LoRA 进一步降低基础权重显存开销。若显存充裕，标准 LoRA 也可行。

### single_choice · None



- [A] QLoRA 将基础模型权重量化到 4-bit，并在此基础上附加 LoRA 适配器进行训练
- [B] QLoRA 将 LoRA 适配器也量化到 4-bit，基础模型保持 fp16
- [C] QLoRA 完全不需要训练任何参数，只做推理
- [D] QLoRA 把模型权重从 4-bit 反量化回 fp32 后全量微调

**参考答案**：0

**解析**：QLoRA 将预训练基础模型量化到 4-bit（如 NF4）存储，前向计算时反量化，LoRA 适配器仍以较高精度训练，从而极大降低显存占用。

### scenario · None



**解析**：LoRA 适配器参数量小且独立于基础模型，多个业务可共享同一份基础模型权重，只需在推理时加载对应的适配器；也可以按需把适配器合并进基础权重或动态挂载，从而实现低成本多任务切换。

### single_choice · None



- [A] 控制低秩更新的幅度，使不同秩 r 下的适配器行为更一致
- [B] 把结果强制归一化到 0 到 1 之间
- [C] 表示学习率的大小
- [D] 用于把 4-bit 权重反量化

**参考答案**：0

**解析**：α 是缩放超参数，缩放因子 α/r 用于调节 LoRA 更新项的相对幅度。当改变 r 时，通过调整 α 可以保持更新强度大致稳定，减少重新调参的成本。

### single_choice · None



- [A] 推理时必须保留单独的 LoRA 分支，不能与基础权重合并
- [B] 可以将 BA 乘上缩放因子后加到 W 上，合并为单一权重，从而不增加推理延迟
- [C] 合并后必须重新量化才能推理
- [D] LoRA 适配器只能用于训练，推理完全无效

**参考答案**：1

**解析**：LoRA 的一个重要优势是推理时可将 B·A 的缩放结果直接加回 W，得到 W' = W + (α/r)BA，合并后结构与原模型一致，不引入额外推理延迟。

### single_choice · None



- [A] A 和 B 都用零矩阵初始化
- [B] A 用随机高斯初始化，B 用零初始化，使训练开始时更新量为零
- [C] A 和 B 都从预训练权重复制
- [D] A 用零初始化，B 用随机初始化

**参考答案**：1

**解析**：常见做法是对 A 使用随机（如 Kaiming/高斯）初始化，对 B 使用零初始化，这样训练起始时 BA=0，模型行为与原始预训练模型完全一致，避免初始扰动。

### single_choice · None



- [A] NF4 是一种均匀量化，将权重等间隔地映射到 16 个值
- [B] NF4 是一种针对近似正态分布权重设计的信息论最优量化，在相同位宽下通常比均匀量化保留更多信息
- [C] NF4 只能用于激活值，不能用于权重
- [D] NF4 会把所有权重变为整数，推理时无法反量化

**参考答案**：1

**解析**：NF4 针对预训练权重近似零均值正态分布的特点设计，使量化分位点等概率分布，在 4-bit 下相比均匀量化保留更多信息。它是 QLoRA 的重要组成部分。

### single_choice · None



- [A] 进一步压缩量化常数（量化缩放因子）占用的显存
- [B] 把 LoRA 适配器的秩减半
- [C] 提高基础模型的推理速度到两倍
- [D] 把 4-bit 权重变成 2-bit 权重

**参考答案**：0

**解析**：双重量化对第一层量化的缩放常数再次量化，进一步降低这些常数占用的显存。虽然节省的显存相对模型权重不多，但在大模型上累积效应可观。

### single_choice · None



- [A] 训练时优化器状态显存峰值过高导致 OOM（显存不足）
- [B] 模型权重无法合并到基础模型
- [C] LoRA 适配器无法学习
- [D] 量化误差过大导致模型崩溃

**参考答案**：0

**解析**：Paged Optimizers 利用统一内存，在显存紧张时把优化器状态换出到 CPU 内存，从而缓解长序列或大批量训练时的显存峰值，避免 OOM。

### single_choice · None



- [A] 只在词嵌入层添加
- [B] 只在最后一层添加
- [C] 在注意力模块的 Q、K、V、O 投影以及 MLP 层等多个线性层添加
- [D] 只在输出层添加

**参考答案**：2

**解析**：实践表明，将 LoRA 适配器应用到注意力模块的多个投影矩阵以及 MLP 层，通常比只加在少数层上效果更好，是常见配置。
