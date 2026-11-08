# s6u3l5 大语言模型量化（LLM Quantization）入门：从零基础到工程级 / 你训练了一个大语言模型（LLM，Large Langua

> 来源 `content/lessons/s6u3l5.json`

## ai.llm.quantization

# 大语言模型量化（LLM Quantization）入门：从零基础到工程级

> **一句话直觉**：量化就是把模型里原本用 16/32 位浮点数（float）存储和计算的权重、激活值，换成 8 位、4 位甚至更低位宽的整数或低精度浮点数，从而让同一个大模型（LLM, Large Language Model）占用更少显存、跑得更快，而效果尽量不掉太多。

---

## 1. 为什么需要量化：显存、带宽、成本

大语言模型（LLM）的参数量动辄 7B、13B、70B。模型推理时显存主要被两部分吃掉：

1. **权重（weights）**：模型参数本身。
2. **激活值（activations）**、**KV Cache（Key-Value Cache）**：推理过程中间结果。

如果权重用 FP16（16-bit 浮点）存储，一个 7B 模型仅权重就要约 14 GB 显存；用 INT8（8-bit 整数）约 7 GB；用 INT4 约 3.5 GB。

```python
# 估算不同精度下 7B 模型的权重大小
params = 7_000_000_000  # 70 亿参数

for name, bits in [("FP32", 32), ("FP16", 16), ("INT8", 8), ("INT4", 4)]:
    size_gb = params * bits / 8 / (1024**3)
    print(f"{name}: {size_gb:.2f} GB")
```

**结论**：位宽（bit-width）每减半，模型权重大小几乎减半。这就是量化最直接的收益。

---

## 2. 量化的基本数学：从浮点到整数

最常见的**仿射量化（affine quantization）**公式：

```
q = round(x / scale + zero_point)
x_hat = (q - zero_point) * scale
```

其中：
- `x`：原始浮点值
- `q`：量化后的整数值
- `scale`：缩放因子（float）
- `zero_point`：零点（整数），保证浮点 0 能精确表示

```python
import numpy as np

def quantize_affine(x, num_bits=8):
    """最朴素的对称/非对称仿射量化示例"""
    qmin, qmax = 0, 2**num_bits - 1
    xmin, xmax = x.min(), x.max()
    # 计算 scale 和 zero_point
    scale = (xmax - xmin) / (qmax - qmin)
    zero_point = round(qmin - xmin / scale)
    # 量化
    q = np.round(x / scale + zero_point).clip(qmin, qmax).astype(np.int32)
    # 反量化
    x_hat = (q - zero_point) * scale
    return q, x_hat, scale, zero_point

x = np.array([-1.5, -0.2, 0.0, 0.7, 2.3], dtype=np.float32)
q, x_hat, s, z = quantize_affine(x, num_bits=8)
print("原始:", x)
print("量化:", q)
print("反量化:", x_hat)
print("scale:", s, "zero_point:", z)
```

**结论**：量化的本质是“用有限个离散格子去逼近连续值”。格子越少（位宽越低），误差越大。

---

## 3. 量化的粒度：per-tensor、per-channel、per-group

同一个 scale 用在整层上叫 **per-tensor**；每个输出通道一个 scale 叫 **per-channel**；每 32/64/128 个权重一组一个 scale 叫 **per-group**（也叫 group-wise / block-wise）。粒度越细，精度越高，但元数据（scale/zero_point）也越多。

```python
import numpy as np

def quantize_per_group(w, group_size=4, num_bits=8):
    """按 group 做对称量化，展示粒度对误差的影响"""
    w = w.flatten()
    qmax = 2**(num_bits - 1) - 1
    out = np.zeros_like(w)
    scales = []
    for i in range(0, len(w), group_size):
        g = w[i:i+group_size]
        scale = np.abs(g).max() / qmax + 1e-8
        q = np.round(g / scale).clip(-qmax, qmax)
        out[i:i+group_size] = q * scale
        scales.append(scale)
    return out, scales

np.random.seed(0)
w = np.random.randn(16).astype(np.float32)
w_q, scales = quantize_per_group(w, group_size=4)
print("原始:", np.round(w, 3))
print("量化:", np.round(w_q, 3))
print("每个 group 的 scale:", np.round(scales, 4))
```

**结论**：工程中 LLM 常用 **group-wise INT4**（如 group_size=128），在精度与体积之间取得平衡。

---

## 4. 主流量化方法：PTQ、QAT、GPTQ、AWQ、SmoothQuant

- **PTQ（Post-Training Quantization，训练后量化）**：模型训练完后直接量化，最常用。
- **QAT（Quantization-Aware Training，量化感知训练）**：训练时模拟量化误差，精度最好但成本高。
- **GPTQ**：基于二阶信息的逐层 PTQ，适合 LLM 的 4-bit 权重量化。
- **AWQ（Activation-aware Weight Quantization）**：根据激活值分布保护重要权重通道。
- **SmoothQuant**：把激活的量化难度“迁移”到权重上，常用于 W8A8。

```python
# 伪代码：用 Hugging Face + bitsandbytes 做 4-bit 加载
# 实际运行需要安装: pip install transformers bitsandbytes accelerate
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,                 # 4-bit 量化加载
    bnb_4bit_quant_type="nf4",         # NormalFloat4，LLM 常用
    bnb_4bit_compute_dtype="float16",  # 计算时用 FP16
    bnb_4bit_use_double_quant=True,    # 双重量化，进一步省显存
)

model_name = "meta-llama/Llama-3.2-1B"  # 示例模型名
# model = AutoModelForCausalLM.from_pretrained(model_name, quantization_config=bnb_config)
# tokenizer = AutoTokenizer.from_pretrained(model_name)
print("配置完成：4-bit NF4 + 双重量化 + FP16 计算")
```

**结论**：工程落地最常见路径是 **PTQ + 4-bit**；追求极致精度再上 QAT 或 AWQ/GPTQ。

---

## 5. 量化的精度评估与常见工程权衡

量化不是免费午餐，必须评估：

- **困惑度（Perplexity, PPL）**：越低越好，量化后上升幅度要可控。
- **下游任务准确率**：分类、问答、代码生成等。
- **延迟与吞吐**：不是所有硬件都对 INT4 有加速。
- **显存 vs 精度 vs 速度**：三者互相牵制。

```python
import math

def perplexity(log_probs):
    """log_probs: 每个 token 的 log 概率列表"""
    avg_nll = -sum(log_probs) / len(log_probs)
    return math.exp(avg_nll)

# 假设 FP16 和 INT4 模型在同一段文本上的 log 概率
fp16_logp = [-0.5, -0.8, -1.2, -0.3, -0.9]
int4_logp = [-0.6, -0.9, -1.4, -0.4, -1.0]
print("FP16 PPL:", round(perplexity(fp16_logp), 3))
print("INT4 PPL:", round(perplexity(int4_logp), 3))
```

**结论**：量化后要同时看**精度指标**和**系统指标**，不能只盯显存。

---

## 动手练习

**任务**：在本机用 Python + NumPy 实现一个 **per-group 对称量化器**，并对比 group_size 对重建误差的影响。

要求：
1. 生成一个长度 1024、服从标准正态分布的权重向量。
2. 分别用 `group_size = 8, 32, 128, 1024` 做 4-bit 对称量化。
3. 计算每种设置的 **均方误差（MSE, Mean Squared Error）**。
4. 用 print 输出表格，观察 group_size 变小是否误差下降。
5. 进阶：把重建权重画成折线图（matplotlib），对比原始曲线。

提示：4-bit 对称量化的 qmax = 2^(4-1) - 1 = 7。

```python
import numpy as np

def quantize_symmetric_per_group(w, group_size=128, num_bits=4):
    """对称 per-group 量化：每个 group 一个 scale，zero_point 固定为 0"""
    w = w.flatten().astype(np.float32)
    qmax = 2 ** (num_bits - 1) - 1  # 4-bit -> 7
    out = np.zeros_like(w)
    for i in range(0, len(w), group_size):
        g = w[i:i + group_size]
        scale = np.abs(g).max() / qmax + 1e-8
        q = np.round(g / scale).clip(-qmax, qmax)
        out[i:i + group_size] = q * scale
    return out

np.random.seed(42)
w = np.random.randn(1024).astype(np.float32)

print(f"{'group_size':>10} | {'MSE':>12}")
print("-" * 26)
for gs in [8, 32, 128, 1024]:
    w_q = quantize_symmetric_per_group(w, group_size=gs, num_bits=4)
    mse = np.mean((w - w_q) ** 2)
    print(f"{gs:>10} | {mse:>12.6f}")

# 结论：group_size 越小，量化粒度越细，MSE 通常越低
```

## ai.llm.inference_opt

## 一句话直觉

**LLM 推理优化（LLM Inference Optimization）**：让大模型在生成回答时更快、更省显存、更便宜。

你训练了一个大语言模型（LLM，Large Language Model），但真正上线给用户用时，瓶颈通常不是训练，而是**推理（Inference）**：每个 token 都要反复做矩阵乘法，显存被 KV Cache 占满，吞吐量上不去。推理优化就是研究“怎么让模型在同样硬件上跑得更快、更稳、更便宜”。

---

### 第 1 节：推理为什么慢？先认识自回归生成与 KV Cache

LLM 生成文本是**自回归（Autoregressive）**的：一次生成一个 token，然后把新 token 拼回输入，再生成下一个。

如果每次都重新计算整个序列的 Key/Value，计算量会爆炸。于是有了 **KV Cache（键值缓存）**：把历史 token 的 Key 和 Value 存下来，下一步只计算新 token 的 Q，并复用缓存的 K、V。

```python
import torch
import torch.nn.functional as F

# 模拟一个注意力头：batch=1, seq_len=4, head_dim=8
B, T, D = 1, 4, 8
torch.manual_seed(0)
q = torch.randn(B, T, D)
k = torch.randn(B, T, D)
v = torch.randn(B, T, D)

# 完整注意力：一次算完所有位置
scores = q @ k.transpose(-2, -1) / (D ** 0.5)
attn = F.softmax(scores, dim=-1)
out_full = attn @ v
print('full attention shape:', out_full.shape)

# KV Cache 思路：只存历史 K/V，新 token 只算自己的 q
cache_k = k[:, :T-1, :]   # 历史 key
cache_v = v[:, :T-1, :]   # 历史 value
q_new = q[:, T-1:, :]     # 当前 token query

# 当前 token 与所有历史 key 做注意力
scores_new = q_new @ cache_k.transpose(-2, -1) / (D ** 0.5)
attn_new = F.softmax(scores_new, dim=-1)
out_new = attn_new @ cache_v
print('cached attention shape:', out_new.shape)
print('last step matches full attention:',
      torch.allclose(out_new, out_full[:, T-1:, :], atol=1e-5))
```

**结论**：KV Cache 把每步复杂度从 O(T²) 降到 O(T)，是推理优化的第一块基石。

---

### 第 2 节：显存瓶颈——KV Cache 与量化

KV Cache 会随着序列长度线性增长。对长上下文（Long Context）场景，显存很快被吃满。

常见做法：

1. **量化（Quantization）**：把 FP16 权重压成 INT8/INT4，显存降 2~4 倍，速度提升。
2. **KV Cache 量化**：把缓存也压成低精度。
3. **分页注意力（PagedAttention）**：像操作系统分页一样管理 KV Cache，减少碎片。

```python
import torch

# 模拟权重从 FP16 量化到 INT8
torch.manual_seed(0)
weight_fp16 = torch.randn(4096, 4096, dtype=torch.float16)

# 简单对称量化：scale = max(abs(w)) / 127
scale = weight_fp16.abs().max() / 127
weight_int8 = (weight_fp16 / scale).round().clamp(-128, 127).to(torch.int8)

# 反量化回来
weight_dequant = (weight_int8.float() * scale).to(torch.float16)
mse = torch.mean((weight_fp16.float() - weight_dequant.float()) ** 2)

print('FP16 bytes:', weight_fp16.numel() * 2)
print('INT8 bytes:', weight_int8.numel() * 1)
print('量化 MSE:', mse.item())
```

**结论**：量化用少量精度损失换显存和速度，是工程上最常用的手段之一。

---

### 第 3 节：吞吐与延迟——连续批处理

在线服务里，请求是陆续到达的，长度不一。如果等一整批凑齐再跑，短请求会被长请求拖死。

**连续批处理（Continuous Batching）**：每生成一步，就把已完成的请求踢出，把新请求加进来。这样 GPU 利用率高，吞吐量（Throughput）大幅提升。

```python
# 伪代码：连续批处理调度器思路
import time

class Request:
    def __init__(self, rid, max_new_tokens):
        self.rid = rid
        self.max_new_tokens = max_new_tokens
        self.generated = 0
        self.done = False

def continuous_batching(requests, step_time=0.1):
    active = []
    finished = []
    pending = list(requests)
    step = 0
    while pending or active:
        # 每步尽量填满 batch
        while pending and len(active) < 4:
            active.append(pending.pop(0))
        # 模拟一步生成
        for r in active:
            r.generated += 1
            if r.generated >= r.max_new_tokens:
                r.done = True
        finished.extend([r for r in active if r.done])
        active = [r for r in active if not r.done]
        step += 1
        time.sleep(0)  # 占位，真实场景是 GPU 计算
    return finished

reqs = [Request(i, max_new_tokens=(i % 3) + 1) for i in range(6)]
res = continuous_batching(reqs)
print('完成顺序:', [r.rid for r in res])
```

**结论**：连续批处理是 vLLM、TensorRT-LLM 等推理引擎的核心调度策略。

---

### 第 4 节：算法级优化——投机解码与并行

前面是系统层，算法层也有大招：

- **投机解码（Speculative Decoding）**：用小模型先草拟多个 token，大模型一次验证，接受率高的部分直接采纳，减少大模型调用次数。
- **张量并行（Tensor Parallelism）**：把一层矩阵拆到多张 GPU 上算。
- **流水线并行（Pipeline Parallelism）**：不同层放不同 GPU，像流水线一样跑。

```python
# 伪代码：投机解码的接受-拒绝逻辑
import random

def speculative_decode(draft_tokens, target_prob, draft_prob, gamma=0.8):
    accepted = []
    for tok in draft_tokens:
        p = target_prob.get(tok, 0.0)
        q = draft_prob.get(tok, 0.0)
        if q == 0:
            break
        # 接受概率 min(1, p/q)
        accept_prob = min(1.0, p / q)
        if random.random() < accept_prob:
            accepted.append(tok)
        else:
            break
    return accepted

# 示例：草稿模型给出 5 个 token
draft = ['A', 'B', 'C', 'D', 'E']
target_prob = {'A': 0.5, 'B': 0.4, 'C': 0.3, 'D': 0.2, 'E': 0.1}
draft_prob  = {'A': 0.6, 'B': 0.5, 'C': 0.4, 'D': 0.3, 'E': 0.2}
random.seed(42)
accepted = speculative_decode(draft, target_prob, draft_prob)
print('接受的 token:', accepted)
```

**结论**：投机解码在生成质量几乎不变的前提下，可带来 2~3 倍加速。

---

### 第 5 节：工程落地——选型与度量

实际项目里，你需要回答：

1. **延迟（Latency）** 还是 **吞吐（Throughput）** 优先？
2. 用现成引擎（vLLM、SGLang、TensorRT-LLM）还是自研？
3. 关键指标：TTFT（Time To First Token）、TPOT（Time Per Output Token）、QPS。

```python
# 简单度量示例
import time

def measure_latency(fn, n=5):
    times = []
    for _ in range(n):
        t0 = time.perf_counter()
        fn()
        times.append(time.perf_counter() - t0)
    return sum(times) / len(times), max(times)

def fake_infer():
    sum(i * i for i in range(100000))

avg, worst = measure_latency(fake_infer)
print(f'平均延迟: {avg:.4f}s, 最差延迟: {worst:.4f}s')
```

**结论**：推理优化是“系统 + 算法 + 度量”的组合拳，先量化指标，再选手段。

---

## 动手练习

**任务**：在本机实现一个“迷你 KV Cache”并对比两种生成方式的耗时。

1. 用 PyTorch 实现一个单头注意力函数 `attention(q, k, v)`。
2. 模拟生成 50 个 token：
   - 方式 A：每步重新计算整个序列的 K、V。
   - 方式 B：维护一个 KV Cache，每步只算新 token。
3. 用 `time.perf_counter()` 统计两种方式总耗时，输出加速比。
4. 把序列长度改成 100、200，观察加速比变化。

**提交要求**：一段可运行代码 + 一张耗时对比表（或打印结果），并解释为什么序列越长，KV Cache 优势越明显。


---

## 本课题目

### single_choice · None



- [A] 约 1/4
- [B] 约 1/2
- [C] 约 1/8
- [D] 约 2 倍

**参考答案**：1

**解析**：16 位到 8 位，每参数字节数减半，因此文件大小约为原来的一半。1/4、1/8 是把位宽误当成字节数或误以为位宽减半意味着二次方缩减；2 倍则方向相反。

### single_choice · None



- [A] 模型准确率一定提高
- [B] 显存占用和内存带宽需求降低
- [C] 训练所需的数据量减少
- [D] 模型参数量自动减少为原来的四分之一

**参考答案**：1

**解析**：低比特量化主要降低存储与访存开销，从而减少显存占用和带宽压力。参数量本身不变，准确率通常也不会必然提高，训练数据量更不会因此减少。

### single_choice · None



- [A] 反量化会把模型恢复到与原始浮点模型完全一致的数值
- [B] 反量化是用量化参数把整数近似还原为浮点值，通常会引入误差
- [C] 反量化只能在训练时进行
- [D] 反量化会增加模型的参数量

**参考答案**：1

**解析**：反量化是按 scale 和 zero point 将整数映射回浮点，属于近似还原，必然存在舍入误差。它不会完全恢复原始数值，也不限于训练时使用，更不会改变参数量。

### single_choice · None



- [A] 用一小批代表性数据统计激活值范围，以确定量化参数
- [B] 对模型进行完整的重新训练
- [C] 删除模型中不重要的注意力头
- [D] 把模型从一种架构转换成另一种架构

**参考答案**：0

**解析**：校准是用少量代表性样本前向推理，观察权重或激活的数值分布，从而确定合适的量化参数。它不等于完整重训练，也不负责删头或改架构。

### single_choice · None



- [A] 长文本会触发模型重新训练
- [B] 长序列中误差逐步累积，量化的舍入偏差被放大
- [C] 长文本的 token 数量超过了量化支持的上限
- [D] 量化只对短文本有效，对长文本无效

**参考答案**：1

**解析**：自回归生成中，早期误差会影响后续 token，长序列使这种累积效应更明显。量化本身不会因文本长度触发训练，也没有“长文本上限”这一通用限制，更不是只对短文本有效。

### single_choice · None



- [A] 量化降低每个参数的表示精度，剪枝移除部分参数或连接
- [B] 量化移除参数，剪枝降低参数精度
- [C] 两者都必然减少模型参数量
- [D] 两者都只能在训练后进行

**参考答案**：0

**解析**：量化改变参数的数值表示精度，剪枝则删除参数或结构。量化通常不减少参数量，剪枝才会；剪枝也有训练中进行的方案，因此不能一概而论。

### single_choice · None



- [A] 推理速度提升且显存/内存占用降低，但可能带来一定精度损失
- [B] 推理速度提升且精度完全无损
- [C] 模型参数量减少为原来的八分之一
- [D] 模型无法在 CPU 上运行

**参考答案**：0

**解析**：8 位整数运算在支持它的硬件上可加速推理并降低内存占用，但量化仍可能带来精度损失。参数量不变；精度不能保证完全无损；CPU 通常正是这类方案的常见目标平台之一。

### single_choice · None



- [A] 离群值会显著扩大数值范围，使大部分正常值被压缩到很少的量化级别上
- [B] 离群值会使模型参数量翻倍
- [C] 离群值只能出现在权重中，不会出现在激活中
- [D] 离群值会自动触发模型的重新训练

**参考答案**：0

**解析**：离群值会拉大整体动态范围，导致量化步长变大，正常数值的表示精度下降。它不会改变参数量，也可能出现在激活中，更不会触发训练。

### single_choice · None



- [A] 2 位量化在语言模型上通常过于激进，精度损失可能不可接受
- [B] 2 位量化一定比 4 位量化精度更高
- [C] 量化位数越低，精度越高
- [D] 2 位量化只能用于图像模型

**参考答案**：0

**解析**：位数越低，可表示的量化级别越少，精度损失通常越大，2 位对多数语言模型过于激进。量化位数与精度并非正相关；2 位也并非图像模型专属。

### single_choice · None



- [A] 把权重分成若干组，每组单独计算量化参数，以更好地适应组内分布
- [B] 把模型参数按组删除，从而减少参数量
- [C] 把训练数据按组划分，以加速训练
- [D] 把不同层的输出拼接到一起

**参考答案**：0

**解析**：分组量化在更细粒度上计算量化参数，能缓解组间分布差异带来的误差。它不删除参数、不划分训练数据，也不做层间拼接。

### single_choice · None



- [A] 提高输出数字相关层的量化精度，或对这些层保留更高精度
- [B] 把所有层都改为 1 位量化
- [C] 增加模型参数量而不改变量化方案
- [D] 关闭所有量化并重新训练

**参考答案**：0

**解析**：对数值敏感层采用更高精度或混合精度量化，可在整体压缩的同时保护关键能力。进一步降低位数会加剧误差；只增加参数量不解决量化误差；完全关闭量化则放弃压缩收益。

### single_choice · None



- [A] 只看模型文件大小，越小越好
- [B] 在目标任务上对比量化前后的精度、延迟和内存占用，综合权衡
- [C] 只看推理速度，精度不重要
- [D] 只要量化位数相同，不同方案的精度一定相同

**参考答案**：1

**解析**：量化是精度、速度、内存之间的权衡，应在目标任务上综合评估。只看文件大小或速度会忽略精度损失；相同位数下，量化粒度、校准方法等都会影响最终精度。

### single_choice · None



- [A] 量化后模型参数量变少，知识被删除
- [B] 低比特表示带来的舍入误差累积，损害了模型输出质量
- [C] 量化只能用于图像模型，不能用于语言模型
- [D] 4 位整数无法表示负数，导致计算溢出

**参考答案**：1

**解析**：低比特量化的核心代价是数值精度下降，舍入误差会在大模型中累积并影响生成质量。参数量不会因量化而减少；4 位整数可以表示负数（如有符号表示）；量化也并非仅限图像模型。

### single_choice · None



- [A] 把浮点数值映射到整数范围，并在反量化时恢复近似原值
- [B] 在训练时自动删除不重要的权重
- [C] 把模型参数量压缩为原来的四分之一
- [D] 决定使用 CPU 还是 GPU 进行推理

**参考答案**：0

**解析**：量化通过缩放因子和零点建立浮点与整数之间的线性映射，反量化时用它们近似还原浮点值。它们不负责删权重、不改变参数量，也与推理硬件选择无关。

### single_choice · None



- [A] PTQ 需要在训练中插入伪量化节点，QAT 不需要
- [B] QAT 通常在训练阶段模拟量化误差，往往比 PTQ 获得更好的精度
- [C] PTQ 只能用于 8 位，QAT 只能用于 4 位
- [D] 两者都会改变模型的参数量

**参考答案**：1

**解析**：QAT 在训练时模拟量化带来的误差，使模型适应低精度表示，通常精度优于直接训练后量化。PTQ 不需要重新训练；两者都不改变参数量；位数选择也不是由方法名固定决定的。

### single_choice · None



- [A] 对所有激活值统一使用同一组量化参数，不做调整
- [B] 采用动态量化，根据运行时统计为激活值计算量化参数
- [C] 放弃量化，改用更大显存的 GPU
- [D] 只量化权重，不量化激活值，问题就完全解决了

**参考答案**：1

**解析**：激活值动态范围变化大时，动态量化按运行时统计量计算缩放因子，能更好地适应分布变化。固定参数容易产生大误差；仅量化权重可缓解但未必完全解决激活误差。

### single_choice · None



- [A] 对称量化只能用于权重，非对称量化只能用于激活
- [B] 对称量化要求零点为 0，非对称量化允许零点不为 0 以更好覆盖非对称分布
- [C] 对称量化精度一定低于非对称量化
- [D] 对称量化不需要缩放因子

**参考答案**：1

**解析**：对称量化以 0 为中心映射，零点通常为 0；非对称量化允许零点偏移，能更好地表示偏斜分布。对称与非对称都可同时用于权重和激活，精度高低取决于数据分布，两者都需要缩放因子。

### single_choice · None



- [A] 整个权重张量共用一组 scale 和 zero point
- [B] 每个输出通道分别使用一组 scale 和 zero point，通常比按张量量化精度更高
- [C] 按通道量化只能用于 8 位，不能用于 4 位
- [D] 按通道量化会增加模型参数量，因此不实用

**参考答案**：1

**解析**：按通道量化为每个通道单独计算量化参数，能更好地拟合不同通道的数值分布，通常精度更高。它不是按张量共用参数；位数选择不固定；它不增加模型参数量，只是增加少量量化参数。

### single_choice · None



- [A] 量化只影响模型的记忆能力，不影响推理能力
- [B] 量化误差对需要精细数值和长链条推理的任务影响更大
- [C] 数学任务的数据在量化时被删除了
- [D] 量化会把模型的语言能力转化为数学能力

**参考答案**：1

**解析**：推理任务对中间数值精度和误差累积更敏感，量化误差可能被放大。量化不会删除某类数据，也不会把语言能力转化为数学能力，更不是只影响记忆。

### single_choice · None



- [A] 同时显著降低权重存储和激活计算的显存开销
- [B] 降低权重存储与读取开销，同时避免激活值低精度带来的较大误差
- [C] 完全避免量化误差
- [D] 使模型训练速度大幅提升

**参考答案**：1

**解析**：仅量化权重可以降低权重存储与带宽，同时保留激活的高精度，减少激活量化误差。它不能完全避免误差，也不一定显著提升训练速度，更不会同时降低激活显存。

### single_choice · None



- [A] 它缓存了模型权重，避免每次前向传播重新加载参数
- [B] 它缓存了已生成 token 的键和值张量，避免自回归解码时对历史 token 重复计算
- [C] 它缓存了用户输入的 embedding，使同一提示可以跳过 tokenization
- [D] 它缓存了注意力输出，使每次解码可以直接复用上一步的 logits

**参考答案**：1

**解析**：自回归解码时每一步都要对全部历史 token 计算注意力，KV Cache 保存历史 token 的 Key/Value，使每步只需计算新 token 的 K/V，从而避免重复计算。它不缓存权重（那是权重常驻显存/量化等话题），也不缓存 embedding 或 logits。

### single_choice · None



- [A] prefill 逐个 token 处理，decode 一次性处理整段提示
- [B] prefill 并行处理整个提示，通常计算密集；decode 每步只生成一个 token，通常受内存带宽限制
- [C] 两个阶段都是计算密集，区别仅在于 batch size 不同
- [D] decode 阶段不需要 KV Cache，只有 prefill 需要

**参考答案**：1

**解析**：prefill 对整段输入并行做前向，矩阵乘规模大，属于计算密集；decode 每步只处理一个新 token，算术强度低，主要瓶颈是读取权重和 KV Cache 的显存带宽。KV Cache 在 decode 阶段被持续读写。

### single_choice · None



- [A] 增大 batch 一定降低单请求延迟，因为 GPU 更忙
- [B] 增大 batch 通常提升整体吞吐，但可能增加单请求延迟，需要在两者间权衡
- [C] 增大 batch 对吞吐和延迟都没有影响
- [D] 增大 batch 只影响显存占用，不影响吞吐

**参考答案**：1

**解析**：更大 batch 提高硬件利用率和总吞吐，但单请求需要等待批次调度、且资源竞争加剧，首 token 延迟和每 token 延迟可能上升，因此要在吞吐和延迟之间做权衡。

### multi_choice · None



- [A] 把 KV Cache 分块存储并用块表管理（分页式）
- [B] 对 KV Cache 采用低比特量化存储
- [C] 使用滑动窗口/流式注意力，只保留最近一段 KV
- [D] 把注意力头数增加到原来的两倍
- [E] 把所有权重从 FP16 转成 FP32

**参考答案**：[0, 1, 2]

**解析**：分页式管理、KV 量化、滑动窗口都能降低 KV Cache 的显存压力。增加头数会增大 KV Cache 规模；权重升到 FP32 会增大显存占用，均与目标相反。

### multi_choice · None



- [A] continuous batching 以迭代为粒度，允许序列完成后立即退出、新请求立即加入
- [B] 静态批处理往往需要等整批中最长序列结束才释放资源，导致短序列空转
- [C] 把长度相近的请求分到同一批（分桶）可以减少填充浪费
- [D] 批处理越大越好，不需要考虑延迟指标

**参考答案**：[0, 1, 2]

**解析**：前三项描述了 continuous batching、静态批处理的缺陷以及分桶的好处。批大小并非越大越好，需要在吞吐与延迟之间权衡，因此第四项错误。

### multi_choice · None



- [A] 对权重使用低比特量化
- [B] 对 KV Cache 使用分页式管理与按需分配
- [C] 限制单次请求的最大输出长度和最大并发数
- [D] 把所有权重和激活统一提升为 FP64 以提升精度
- [E] 启用 CPU 卸载，把部分权重或 KV 放到主机内存

**参考答案**：[0, 1, 2, 4]

**解析**：量化、分页式 KV 管理、限制长度和并发、CPU 卸载都能缓解显存压力。提升为 FP64 会成倍增大占用，与目标相反。

### multi_choice · None



- [A] prefill 阶段矩阵乘规模大，通常是计算密集
- [B] decode 阶段每步计算量小但需读取大量权重和 KV，通常是访存/带宽受限
- [C] 算术强度（每字节访存对应的浮点运算量）越高越可能偏向计算受限
- [D] 只要 GPU 主频更高，访存受限就一定消失

**参考答案**：[0, 1, 2]

**解析**：prefill 计算密集、decode 访存受限是常识；算术强度越高越偏向计算受限。提高主频无法改变内存带宽上限，访存受限不会仅靠主频消除，故第四项错误。

### fill_blank · None



**参考答案**：["KV Cache", "KVCache", "kv cache", "键值缓存"]

**解析**：该缓存保存历史 token 的 Key 和 Value，使每步只需计算新 token 的 K/V，是自回归解码加速的关键机制。

### fill_blank · None



**参考答案**：["continuous", "Continuous", "连续", "连续批处理", "continuous batching"]

**解析**：continuous batching 以每个解码迭代为调度粒度，序列完成即释放、新请求即插入，显著提升硬件利用率和吞吐。

### fill_blank · None



**参考答案**：["arithmetic intensity", "Arithmetic Intensity", "arithmetic_intensity", "算术强度", "AI"]

**解析**：算术强度（arithmetic intensity）等于浮点运算量除以访存字节数，数值低说明每读一字节做的计算少，容易受内存带宽限制，decode 阶段通常很低。

### code_reading · None



**参考答案**：不需要。历史 token 的 Key/Value 已经保存在 kv_cache 中，每一步只需为新产生的 token 计算 Key/Value 并追加，然后与缓存中的历史 K/V 一起参与注意力计算，从而把每步代价从与序列长度相关的重复计算降为只计算新 token。

**解析**：这就是 KV Cache 的核心作用：缓存历史键值，避免在自回归解码过程中对同一历史 token 反复做前向计算，把复杂度大幅降低。

### scenario · None



**解析**：长提示短输出意味着时间主要花在 prefill 阶段；prefill 属于计算密集，但如果调度让大量 prefill 与 decode 混在一起、或批次填充浪费严重，就会出现 GPU 利用率不高且首 token 延迟高的现象。可行方向包括：对提示长度分桶以减少填充、启用 continuous batching 让调度更平滑、把长 prefill 切块（chunked prefill）与 decode 交错、对重复的系统提示使用前缀缓存复用 KV、以及适当限制单批 prefill 长度以降低首 token 排队。

### single_choice · None



- [A] 它把多个请求的提示拼接成一条超长序列，减少前向次数
- [B] 它允许在一个批次内某个序列生成结束后立即填入新请求，而不必等整批全部完成
- [C] 它把所有请求的 KV Cache 合并成一份共享缓存
- [D] 它通过降低采样温度来加快生成速度

**参考答案**：1

**解析**：静态批处理要等批次中最长的序列结束后整批才释放，短序列造成大量空转。continuous batching 以迭代为粒度调度，序列完成即退出、新请求即插入，提升吞吐。采样温度与批处理策略无关。

### single_choice · None



- [A] 它为每个序列预留一段连续的最大长度显存，避免碎片
- [B] 它把 KV Cache 按固定大小的块进行非连续存储，用块表映射，减少显存碎片和预留浪费
- [C] 它把 KV Cache 全部换出到 CPU 内存，只在需要时读回
- [D] 它通过丢弃较早的 KV 来保证序列使用的显存严格为常数

**参考答案**：1

**解析**：PagedAttention 借鉴操作系统分页思想，把 KV Cache 切成固定大小的 block，逻辑上连续、物理上可非连续，用块表索引，从而降低内部碎片和过量预留。丢弃较早 KV 属于 sliding window/流式注意力等另一类技术。

### single_choice · None



- [A] 收益是减少显存占用并可能提升带宽受限场景的吞吐；代价是可能引入精度损失
- [B] 收益是增大显存占用以换取更高精度；代价是吞吐下降
- [C] 收益是完全没有精度损失地提升吞吐；代价是必须重新训练模型
- [D] 收益是减少前向传播的层数；代价是无法再做批处理

**参考答案**：0

**解析**：低比特量化减小权重/激活的存储与读取量，缓解显存容量和带宽瓶颈，从而提升吞吐；但数值精度下降可能带来质量退化，需要校准或量化感知训练来缓解。它不改变层数，也不必然需要重训。

### single_choice · None



- [A] 用小模型直接替代大模型输出，从而绕过大模型计算
- [B] 用低成本方式一次提出多个候选 token，再由目标模型一次并行验证，接受的部分可一次前进多步
- [C] 把目标模型的 KV Cache 完全共享给草稿模型，使草稿模型零成本
- [D] 通过降低生成质量换取更少的采样步骤

**参考答案**：1

**解析**：投机解码用草稿模型（或其它廉价提议机制）生成若干候选，目标模型在一次前向中并行校验这些位置，被接受的前缀使单次前向推进多个 token。其输出分布可与目标模型保持一致，不是简单用小模型替代或牺牲质量。

### single_choice · None



- [A] KV Cache 占用与序列长度无关，只与批大小有关
- [B] KV Cache 占用与层数、批大小、序列长度、注意力头维度等成正比，通常随批大小和序列长度线性增长
- [C] KV Cache 占用只取决于模型参数量，与并发请求数无关
- [D] KV Cache 占用在 prefill 完成后即固定，不再随生成增长

**参考答案**：1

**解析**：每层每个 token 都保存 K 和 V，规模约为 2 × 层数 × 头数 × 头维度 × 序列长度 × 批大小 × 数据类型字节数，因此随批大小和序列长度线性增长。它随生成不断追加，并非固定。

### single_choice · None



- [A] 补零会改变注意力计算结果，使输出不正确，必须禁用掩码
- [B] 大量填充位置参与计算会浪费算力，并可能因注意力掩码处理不当影响结果
- [C] 补零会使 KV Cache 无法复用，必须每步重建
- [D] 补零会使模型权重被重新初始化

**参考答案**：1

**解析**：填充到统一长度会产生无效计算，降低有效吞吐；同时需要正确的注意力掩码把填充位置屏蔽掉，否则会影响结果。合理做法是分桶或变长处理，而非无条件补零。

### single_choice · None



- [A] 减少 kernel 启动次数和中间张量的显存往返，提升带宽受限场景的效率
- [B] 增加并行度以便把不同请求合并成一个 kernel
- [C] 降低模型参数精度从而减少显存
- [D] 改变模型数学定义以获得更高质量输出

**参考答案**：0

**解析**：逐元素/归一化等小算子受限于 kernel 启动和显存读写，融合后可减少启动开销和中间结果往返，对 decode 这类带宽受限阶段收益明显。融合不改变数学定义，也不等同于量化。

### single_choice · None



- [A] 模型参数量太小，无法利用 GPU
- [B] KV Cache 显存不足导致可并发序列数受限，或计算/带宽已达饱和
- [C] tokenization 太慢，与 GPU 无关
- [D] 采样温度太高，导致每步生成变慢

**参考答案**：1

**解析**：并发上升后吞吐不增常见于两类原因：显存容量限制并发（KV Cache 占满导致排队）或计算/带宽饱和。简单归因于参数量小、tokenization 或采样温度都缺乏依据。
