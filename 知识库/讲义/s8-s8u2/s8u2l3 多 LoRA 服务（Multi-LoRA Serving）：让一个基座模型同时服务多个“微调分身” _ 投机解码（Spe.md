# s8u2l3 多 LoRA 服务（Multi-LoRA Serving）：让一个基座模型同时服务多个“微调分身” / 投机解码（Speculative Decoding）：让大模型推理“先猜后验”

> 来源 `content/lessons/s8u2l3.json`

## arch.serve.multi_lora

# 多 LoRA 服务（Multi-LoRA Serving）：让一个基座模型同时服务多个“微调分身”

> **一句话直觉**：你有一个通用大模型（基座模型 base model），但不同业务/任务需要不同的微调版本。如果每个微调都单独部署一份完整模型，显存和成本会爆炸。Multi-LoRA Serving 让你**只加载一份基座，同时挂载多个 LoRA 适配器**，按请求动态切换，极大节省显存、提升吞吐。

---

## 1. 为什么需要 Multi-LoRA Serving？（问题背景）

### 1.1 微调的现实困境

假设你用 LLaMA-7B 作为基座，为三个业务各微调了一个版本：客服问答、代码补全、法律咨询。传统做法是部署三份 7B 模型，每份约 14GB（FP16），总显存约 42GB，还要各自独立的 KV Cache（键值缓存）、批处理队列，GPU 利用率很低。

### 1.2 LoRA 带来的转机

**LoRA（Low-Rank Adaptation，低秩适配）** 的核心思想：冻结基座权重，只在部分层旁接一对小矩阵 `A`、`B`，训练时只更新它们。原始权重 `W` 保持不变，前向计算变为：

```
h = W·x + (B·A)·x
```

其中 `A` 的形状是 `(r, d_in)`，`B` 的形状是 `(d_out, r)`，`r`（秩）通常取 8~64，因此参数量只有基座的千分之几。一个 7B 模型的 LoRA 适配器可能只有几十 MB。

### 1.3 Multi-LoRA Serving 的核心价值

既然每个适配器那么小，我们就可以**在同一个基座实例上同时驻留几十上百个 LoRA**，在推理时根据请求里的 `adapter_id` 动态选择要叠加的 `B·A`。这样：

- 显存从 `N × 基座` 降到 `1 × 基座 + N × 小适配器`
- 多个请求即使指向不同适配器，也能**合并成一个大 batch 一起前向**（关键工程点）
- 新增业务只需加载一个小文件，无需重启服务

---

## 2. 数学与结构：LoRA 到底挂在哪里

### 2.1 一个最小的 LoRA 层实现

下面代码用 PyTorch 手写一个 `LoRALinear`，直观展示基座 + 适配器的加法结构。

```python
import torch
import torch.nn as nn

class LoRALinear(nn.Module):
    """把普通 Linear 层包成一个支持 LoRA 的层。
    base_layer: 冻结的原权重
    A, B:      每个适配器自己的低秩矩阵，可用 dict 存多个
    """
    def __init__(self, base_layer: nn.Linear, r: int = 8):
        super().__init__()
        self.base = base_layer
        for p in self.base.parameters():
            p.requires_grad = False           # 基座永远不训练
        self.r = r
        # 每个 adapter_id -> (A, B)
        self.adapters = nn.ParameterDict()

    def add_adapter(self, adapter_id: str):
        d_out, d_in = self.base.weight.shape
        A = nn.Parameter(torch.zeros(self.r, d_in))
        B = nn.Parameter(torch.zeros(d_out, self.r))  # 初始为 0，保证初始等价于基座
        self.adapters[f"{adapter_id}.A"] = A
        self.adapters[f"{adapter_id}.B"] = B

    def forward(self, x, adapter_id: str | None = None):
        out = self.base(x)
        if adapter_id is not None:
            A = self.adapters[f"{adapter_id}.A"]
            B = self.adapters[f"{adapter_id}.B"]
            # (B @ A) 形状 (d_out, d_in)，与基座权重同形
            out = out + (x @ A.T) @ B.T
        return out
```

**关键结论**：每个适配器只多了两个小矩阵；`adapter_id=None` 时退化成原始基座，兼容性极好。

### 2.2 多个适配器同时服务

因为 `adapters` 是一个字典，你可以在同一层里放任意多个。请求进入时只需携带 `adapter_id`，就能选到对应的那对矩阵。

---

## 3. 工程核心：异质 Batch 的批处理（Heterogeneous Batching）

### 3.1 难点

如果 batch 里三个样本分别要 adapter A、B、A，直接做矩阵乘会失败，因为每个样本要乘不同的 `B·A`。

### 3.2 两种主流策略

| 策略 | 做法 | 优点 | 缺点 |
|------|------|------|------|
| **按适配器分组（Group by Adapter）** | 把同一适配器的请求聚成一个子 batch，分别前向 | 实现简单、计算密度高 | 非热门适配器利用率低 |
| **统一计算 + 掩码（SGMV / Punica 式）** | 把不同适配器的 LoRA 拼成一个块对角矩阵，一次矩阵乘算完 | 单 kernel 处理全部，吞吐极高 | 实现复杂，需自定义 CUDA kernel |

现代推理框架（vLLM、SGLang、TGI）多采用第二种或其变体。我们用纯 Python 演示第一种，帮助理解。

```python
def forward_grouped(layer: LoRALinear, x_batch, adapter_ids):
    """x_batch: (B, d_in); adapter_ids: 长度 B 的列表"""
    out = layer.base(x_batch)               # 先算所有样本的基座输出
    # 按 adapter 分组，只对有该 adapter 的样本加 LoRA 增量
    from collections import defaultdict
    groups = defaultdict(list)
    for i, aid in enumerate(adapter_ids):
        if aid is not None:
            groups[aid].append(i)
    for aid, idx_list in groups.items():
        idx = torch.tensor(idx_list, device=x_batch.device)
        x_sub = x_batch[idx]
        A = layer.adapters[f"{aid}.A"]
        B = layer.adapters[f"{aid}.B"]
        out[idx] += (x_sub @ A.T) @ B.T
    return out
```

**关键结论**：先算共享的基座输出，再按适配器补差值——这是所有 multi-LoRA 加速方案的思想起点。

---

## 4. 端到端最小可跑示例：一个路由器 + 两层 LoRA

下面代码模拟一个完整链路：请求带着 `adapter_id` 进来，路由到对应 LoRA，跑一层前向。这是**离线演示**，也是理解 vLLM `--enable-lora` 工作的最小骨架。

```python
import torch, torch.nn as nn

class TinyMultiLoRAModel(nn.Module):
    def __init__(self, d_in=16, d_hidden=32, r=4):
        super().__init__()
        # 两层"基座"
        self.l1 = LoRALinear(nn.Linear(d_in, d_hidden), r)
        self.l2 = LoRALinear(nn.Linear(d_hidden, d_in), r)

    def register_adapter(self, adapter_id: str):
        self.l1.add_adapter(adapter_id)
        self.l2.add_adapter(adapter_id)

    def forward(self, x, adapter_ids: list):
        h = torch.relu(forward_grouped(self.l1, x, adapter_ids))
        return forward_grouped(self.l2, h, adapter_ids)

# ---- 演示 ----
torch.manual_seed(0)
model = TinyMultiLoRAModel()

# 注册两个不同的适配器：A 用于客服，B 用于代码
model.register_adapter("customer_service")
model.register_adapter("code_assist")

# 让两个适配器有不同行为（模拟训练后的结果，实际从文件 load）
with torch.no_grad():
    model.l1.adapters["customer_service.A"].normal_(0, 0.1)
    model.l1.adapters["customer_service.B"].normal_(0, 0.1)
    model.l1.adapters["code_assist.A"].normal_(0, 0.2)
    model.l1.adapters["code_assist.B"].normal_(0, 0.2)

# 一个混合 batch：3 个请求，指向不同适配器
x = torch.randn(3, 16)
ids = ["customer_service", "code_assist", "customer_service"]
out = model(x, ids)
print("输出形状:", out.shape)   # (3, 16)
print("每行对应一个请求在它自己适配器下的结果")
```

**运行后你会看到**：一个 batch 中，不同样本走了不同的 LoRA，但都在同一个基座计算里完成。这就是 multi-LoRA serving 的基本盘子。

---

## 5. 生产环境里的关键工程点

### 5.1 请求路由与调度

- 服务端维护一个 `adapter_id -> 权重` 的注册表，可**热加载/卸载**
- 调度器把同 batch 的请求按 `adapter_id` 分组，优先把同适配器的请求放一起
- 常配一个 LRU，淘汰冷门适配器

### 5.2 适配器加载与显存管理

- 适配器以 `safetensors` 等形式存在磁盘，加载到 GPU 是一对 `A`、`B`
- 总显存预算 = 基座 + 所有适配器 + KV Cache + 中间激活
- LoRA 很小，瓶颈通常在 KV Cache，而非适配器数量

### 5.3 与连续批处理（Continuous Batching）的结合

vLLM / SGLang 的做法：

- 每个 decode step 从等待队列里取活跃序列
- 把不同 `adapter_id` 的序列拼成一个 batch
- 在 LoRA 层做 **SGMV（Segmented Gather Matrix-Vector）**：把各适配器的 LoRA 权重按段拼接，单次矩阵乘处理
- 结果：即使 100 个适配器在线，GPU 依旧高利用

### 5.4 常用开源实现速览

| 框架 | 特点 |
|------|------|
| **vLLM** | `--enable-lora --max-loras N`，生产级，Punica kernel |
| **SGLang** | 原生多 LoRA 支持，RadixAttention 兼容 |
| **HuggingFace PEFT + TGI** | PEFT 训练、TGI 部署，入门首选 |
| **LoRAX** | Predibase 出品，专为 multi-LoRA 服务设计 |

---

## 6. 动手练习（本地完成，约 30 分钟）

### 任务：为 `TinyMultiLoRAModel` 加一个“请求队列 + 调度器”

**目标**：模拟真实 multi-LoRA serving 的请求流。

**要求**：

1. 实现一个 `Scheduler` 类，内部维护一个请求队列；每个请求是 `(x_tensor, adapter_id)`。
2. 每调用一次 `scheduler.step(batch_size)`，从队列取 `batch_size` 个请求：
   - **优先把相同 `adapter_id` 的请求聚在同一次前向里**（提升效率）
   - 拼成一个 batch，调用 `model(x_batch, id_list)`，打印每个请求的输出第一维数值
3. 构造 20 个请求，`adapter_id` 从 `["customer_service", "code_assist"]` 随机选，跑 4 步观察输出。
4. **加分项**：给 `Scheduler` 加 LRU 淘汰逻辑，当同时驻留的适配器超过 `max_adapters=2` 时，把最久未用的那个从 `model.adapters` 里删掉。

**验收标准**：代码能跑通、无报错；打印出来的 batch 里能看出“同适配器聚在一起”。

**思考题（写在代码注释里）**：
- 如果 batch 里 90% 请求都指向同一个适配器，你如何调整调度策略？
- 如果用 `SGMV` 思路代替“分组”，代码大致会变成什么样？

## arch.serve.speculative

# 投机解码（Speculative Decoding）：让大模型推理“先猜后验”

## 一句话直觉

**大模型逐字生成太慢，那就先让一个小模型快速“猜”出一串候选词，再让大模型一次性“批改”这些候选——猜对了就白赚，猜错了就纠正，整体速度大幅提升。**

这就是 **投机解码（Speculative Decoding）** 的核心思想：用便宜的草稿模型（draft model）做“猜测”，用昂贵的目标模型（target model）做“验证”，在保证输出分布不变的前提下，把自回归（autoregressive）解码的串行瓶颈变成并行验证。

---

## 1. 为什么需要投机解码？

### 1.1 自回归解码的瓶颈

大语言模型（LLM, Large Language Model）生成文本时，是**一个字一个字往外蹦**的：

- 第 1 步：根据 prompt 生成 token₁
- 第 2 步：根据 prompt + token₁ 生成 token₂
- 第 3 步：根据 prompt + token₁ + token₂ 生成 token₃
- ……

每一步都要把整个模型跑一遍。虽然 GPU 擅长并行计算，但生成过程**天然串行**——下一个 token 依赖上一个 token。结果就是：GPU 利用率低，生成速度慢。

### 1.2 一个关键观察

在每一步解码时，模型其实要输出一个**完整的概率分布**（vocabulary 上几万维）。但我们通常只取 top-1，剩下 99.99% 的计算被浪费了。

**投机解码的洞察**：既然一次前向能算出完整分布，那能不能一次前向多验证几个位置？

答案是：**可以，只要你能先“猜”出这些位置的候选 token**。

---

## 2. 核心机制：草稿 + 验证

投机解码有两个角色：

| 角色 | 英文 | 特点 |
|------|------|------|
| 草稿模型 | draft model / approximation model | 小、快、便宜，负责“猜” |
| 目标模型 | target model / verifier | 大、慢、准，负责“批改” |

### 2.1 工作流程

1. **草稿阶段（Draft）**：草稿模型自回归生成 γ 个候选 token，记为 x₁, x₂, ..., x_γ。
2. **验证阶段（Verify）**：目标模型**一次性并行**计算这 γ 个位置的概率分布。
3. **接受/拒绝（Accept/Reject）**：从左到右逐个判断，每个候选 token 以某种概率被接受。一旦某个被拒绝，后面的全部丢弃，并从修正后的分布中重新采样一个 token。
4. **循环**：把接受的 token 拼回上下文，重复上述过程。

关键是：**验证阶段只做一次目标模型前向**，就能检查 γ 个位置——这就是加速的来源。

### 2.2 为什么输出分布不变？

这是投机解码最漂亮的地方。假设：

- 目标模型分布：p(x)
- 草稿模型分布：q(x)

对每个候选 token x，以概率 `min(1, p(x)/q(x))` 接受它。

- 如果接受，x 服从 p(x) 的“截断放大”分布；
- 如果拒绝，则从修正分布 `norm(max(0, p(x) - q(x)))` 中重新采样。

数学上可以证明：**最终采样结果与直接从目标模型采样完全同分布**。也就是说，投机解码是**无损加速**——它不改变输出质量，只改变计算方式。

---

## 3. 一个最小可运行示例

下面用纯 Python 模拟投机解码的“接受/拒绝”环节。不依赖任何深度学习框架，帮助理解核心逻辑。

```python
import random
from collections import Counter

# 模拟目标模型和草稿模型对某个位置的概率分布
target = {"a": 0.5, "b": 0.3, "c": 0.15, "d": 0.05}
draft  = {"a": 0.3, "b": 0.4, "c": 0.2, "d": 0.1}

def sample(dist):
    r = random.random()
    acc = 0.0
    for token, p in dist.items():
        acc += p
        if r <= acc:
            return token
    return list(dist)[-1]

def speculative_step():
    # 1) 草稿模型猜一个 token
    x = sample(draft)
    # 2) 计算接受概率 min(1, p(x)/q(x))
    accept_prob = min(1.0, target[x] / draft[x])
    if random.random() < accept_prob:
        return x  # 接受草稿
    # 3) 拒绝：从修正分布 max(0, p-q) 归一化后重采样
    residual = {t: max(0.0, target[t] - draft[t]) for t in target}
    s = sum(residual.values())
    residual = {t: v / s for t, v in residual.items()}
    return sample(residual)

# 统计投机解码的输出分布，应接近 target
random.seed(0)
cnt = Counter(speculative_step() for _ in range(100000))
total = sum(cnt.values())
for t in sorted(target):
    print(f"{t}: empirical={cnt[t]/total:.3f}  target={target[t]:.3f}  draft={draft[t]:.3f}")
```

运行后你会看到 empirical 分布非常接近 target，说明**接受/拒绝机制保证了无偏性**。

---

## 4. 工程中的关键参数

在实际系统（如 vLLM、TensorRT-LLM、TGI）中部署投机解码，需要关注：

### 4.1 γ（草稿长度，draft length）

- γ 太小：验证收益低，加速有限；
- γ 太大：草稿模型浪费算力，且拒绝后丢弃多。
- 经验值：4~8 通常性价比最高。

### 4.2 草稿模型的选择

- **同系列小模型**：如 LLaMA-70B 配 LLaMA-7B；
- **蒸馏模型**：专门训练以模仿目标模型；
- **自投机（self-speculation）**：用目标模型的部分层做草稿；
- **Medusa / EAGLE**：不用独立草稿模型，而是在目标模型上挂多个预测头。

### 4.3 加速比的上限

理论加速比约为 `(1 + αγ) / (1 + γ·c)`，其中 α 是接受率，c 是草稿/目标模型开销比。

- 草稿越准（α 高）、越便宜（c 低），加速越明显；
- 典型加速：2~3 倍，极端场景可达 4 倍以上。

---

## 5. 与其他加速技术的对比

| 技术 | 原理 | 是否改变输出 | 典型加速 |
|------|------|--------------|----------|
| 量化（Quantization） | 降低权重精度 | 可能轻微改变 | 1.5~2x |
| KV Cache | 复用历史 K/V | 不变 | 2~5x（长上下文） |
| 投机解码 | 草稿+验证 | **不变** | 2~3x |
| 连续批处理（Continuous Batching） | 动态拼 batch | 不变 | 5~10x（吞吐） |

投机解码的独特价值：**它不改变输出分布，且与量化、KV Cache、批处理正交，可以叠加使用**。

---

## 6. 什么时候不该用投机解码？

- **草稿模型太差**：接受率低，反而拖慢；
- **目标模型本身很小**：草稿模型省不了多少；
- **batch 已经很大**：GPU 已饱和，验证阶段并行收益被摊薄；
- **内存极度受限**：要额外加载一个草稿模型。

工程上建议：**先用 profiler 测一下你的瓶颈在哪**，再看投机解码是否值得引入。

```python
import random
from collections import Counter

# 模拟目标模型和草稿模型对某个位置的概率分布
target = {"a": 0.5, "b": 0.3, "c": 0.15, "d": 0.05}
draft  = {"a": 0.3, "b": 0.4, "c": 0.2, "d": 0.1}

def sample(dist):
    """按概率分布采样一个 token。"""
    r = random.random()
    acc = 0.0
    for token, p in dist.items():
        acc += p
        if r <= acc:
            return token
    return list(dist)[-1]

def speculative_step():
    """执行一次投机解码的接受/拒绝步骤。"""
    # 1) 草稿模型猜一个 token
    x = sample(draft)
    # 2) 接受概率 min(1, p(x)/q(x))
    accept_prob = min(1.0, target[x] / draft[x])
    if random.random() < accept_prob:
        return x
    # 3) 拒绝：从修正分布 max(0, p-q) 归一化后重采样
    residual = {t: max(0.0, target[t] - draft[t]) for t in target}
    s = sum(residual.values())
    residual = {t: v / s for t, v in residual.items()}
    return sample(residual)

random.seed(0)
cnt = Counter(speculative_step() for _ in range(100000))
total = sum(cnt.values())
for t in sorted(target):
    print(f"{t}: empirical={cnt[t]/total:.3f}  target={target[t]:.3f}  draft={draft[t]:.3f}")
```


---

## 本课题目

### single_choice · None



- [A] 为每个适配器复制一份完整的基础模型权重，确保互不干扰
- [B] 共享同一份基础模型权重，仅在计算时按需叠加不同适配器的低秩增量
- [C] 把所有适配器的权重先平均成一个新模型再对外服务
- [D] 只允许同时加载一个适配器，其他请求排队等待

**参考答案**：1

**解析**：多 LoRA 服务的核心是共享基础模型权重、按请求动态叠加各自的低秩增量，从而节省显存并支持并发多适配器；复制基础模型会成倍占用显存，权重平均会破坏各适配器语义。

### single_choice · None



- [A] LoRA 会替换掉原线性层的权重矩阵，推理时必须加载完整新权重
- [B] LoRA 通过低秩矩阵 A、B 产生增量 ΔW=BA，推理时可将其叠加到原权重上
- [C] LoRA 只改变偏置项 b，不影响权重矩阵
- [D] LoRA 必须重新训练基础模型才能生效

**参考答案**：1

**解析**：LoRA 用低秩分解 ΔW=BA 表示增量，推理时可把 BA 叠加到原权重 W 上；它不替换整个权重、不改偏置、也不需要重训基础模型。

### single_choice · None



- [A] 基础模型量化后就不能再叠加任何 LoRA 适配器
- [B] 基础模型量化与 LoRA 增量可以共存，但需注意精度与算子兼容
- [C] LoRA 适配器必须与基础模型使用完全相同的量化位宽
- [D] 量化只影响训练，不影响推理服务

**参考答案**：1

**解析**：量化基础模型与 LoRA 增量可以共存，但要注意数值精度和底层算子是否支持；并不要求位宽完全一致，量化也会影响推理性能与精度。

### single_choice · None



- [A] 共享一份基础模型权重，按请求动态切换适配器
- [B] 为每个 LoRA 单独部署一份完整基础模型实例
- [C] 将不活跃的适配器卸载到 CPU 内存按需加载
- [D] 对基础模型做量化以节省显存

**参考答案**：1

**解析**：为每个 LoRA 单独部署完整基础模型会让显存随数量线性暴涨，是有限显存下最不推荐的方案；共享权重、按需卸载、量化都是常见优化。

### single_choice · None



- [A] 只能通过修改基础模型权重文件来指定
- [B] 作为请求元数据（如请求字段或 HTTP 头）随请求传入
- [C] 必须写死在服务启动参数里，运行时不可更改
- [D] 通过环境变量为整个服务进程统一设置

**参考答案**：1

**解析**：多 LoRA 服务通常把适配器标识作为请求级元数据传入，才能支持同一服务面向不同请求使用不同适配器；写死启动参数或全局环境变量无法按请求区分。

### single_choice · None



- [A] 全量微调模型只能有一个，LoRA 可以多个共享基础模型
- [B] 全量微调模型可以像 LoRA 一样多个共享同一份基础权重
- [C] LoRA 部署时必须为每个适配器单独编译一套推理引擎
- [D] 全量微调模型体积一定小于 LoRA 适配器

**参考答案**：0

**解析**：全量微调产物是一份完整模型权重，难以多个共享同一基础权重；LoRA 因只保存低秩增量，多个适配器可共享基础模型，这也是其部署优势。

### single_choice · None



- [A] 整个服务崩溃并拒绝所有请求
- [B] 仅对该适配器标记不可用，其他请求仍正常服务
- [C] 自动用随机权重替代损坏的适配器
- [D] 静默回退到其他租户的适配器

**参考答案**：1

**解析**：单个适配器损坏应隔离影响，标记不可用并继续服务其他请求；整体崩溃、随机权重、串用他人适配器都会带来更大问题。

### single_choice · None



- [A] LoRA 只能作用于前馈层，不能作用于注意力投影层
- [B] LoRA 可作用于注意力层的查询、键、值等投影矩阵，产生低秩增量
- [C] LoRA 会替换注意力机制为卷积
- [D] LoRA 会改变注意力头数量

**参考答案**：1

**解析**：LoRA 可应用于注意力层的 Q/K/V 等投影矩阵产生低秩增量；它不会替换注意力机制，也不改变注意力头数量，且不限于前馈层。

### single_choice · None



- [A] 在一步计算中把所有适配器求平均后统一使用
- [B] 按样本携带的适配器信息分别应用各自增量
- [C] 每步只允许一个适配器，其他样本挂起
- [D] 切换适配器时必须清空整个 KV 缓存

**参考答案**：1

**解析**：连续批处理下应按样本携带的适配器信息分别应用增量；求平均会破坏语义，每步只允许一个适配器会牺牲吞吐，切换适配器无需清空所有 KV 缓存。

### single_choice · None



- [A] 仅适配器名称，其余信息无需记录
- [B] 适配器名称、版本、对应基础模型标识及状态等
- [C] 适配器的完整训练数据
- [D] 基础模型的全部源代码

**参考答案**：1

**解析**：适配器元数据一般包含名称、版本、所依赖的基础模型标识与可用状态等，便于路由与运维；训练数据和源码不属于部署元数据。

### single_choice · None



- [A] 用于控制基础模型权重被覆盖的程度
- [B] 用于调节低秩增量在叠加时的强度
- [C] 用于决定适配器加载到 CPU 还是 GPU
- [D] 用于加密适配器权重文件

**参考答案**：1

**解析**：缩放因子用于调节 LoRA 低秩增量在叠加时的强度，不影响基础模型是否被覆盖，也不决定设备放置或加密。

### single_choice · None



- [A] 新增适配器时暂停全部推理请求
- [B] 新增过程对已有请求透明且不破坏现有适配器状态
- [C] 新增适配器后必须重启基础模型
- [D] 新增适配器必须替换掉一个旧适配器

**参考答案**：1

**解析**：热加载新适配器的关键是过程对已有请求透明且不破坏现有状态；不需要暂停全部请求、重启基础模型或强制替换旧适配器。

### single_choice · None



- [A] 为每个 adapter_id 启动一个独立进程并各自加载完整基础模型
- [B] 根据 adapter_id 在该请求的计算路径中选择对应的适配器增量
- [C] 忽略 adapter_id，统一用默认适配器处理所有请求
- [D] 每次请求都重新从磁盘加载基础模型和适配器

**参考答案**：1

**解析**：多 LoRA 服务按请求选择对应适配器增量即可；独立进程加载完整模型浪费显存，忽略 adapter_id 无法满足多租户，重复加载基础模型开销过大。

### single_choice · None



- [A] 不同适配器的低秩维度必须完全相同，否则无法批处理
- [B] 需要为批内每个样本应用各自的适配器增量，避免串扰
- [C] 批处理会使 LoRA 权重失效，必须退化为逐条推理
- [D] 同一批只能使用基础模型，不能带任何适配器

**参考答案**：1

**解析**：多 LoRA 批处理的关键是让批内每个样本走自己的适配器增量而不互相污染；适配器秩可以不同，批处理本身不会使 LoRA 失效。

### single_choice · None



- [A] 基础模型权重占大头，多个小 LoRA 增量额外开销相对可控
- [B] 每个 LoRA 都会复制一份基础模型，显存随适配器数量线性暴涨
- [C] LoRA 增量必须驻留在 CPU 内存，不能放在 GPU 上
- [D] 多 LoRA 服务无法在单张 GPU 上运行

**参考答案**：0

**解析**：基础模型权重通常是显存主要部分，LoRA 增量参数很少，多个适配器额外开销相对可控；不会每个 LoRA 复制基础模型，也可放在 GPU 上，单卡可运行。

### single_choice · None



- [A] 两个适配器的效果自动融合且互不干扰
- [B] 两个增量叠加可能相互冲突，导致输出不可控
- [C] 后加载的适配器会完全覆盖先加载的适配器
- [D] 基础模型会自动选择更优的适配器

**参考答案**：1

**解析**：多个适配器同时叠加未必语义兼容，可能相互冲突；它们不会自动融合或覆盖，基础模型也不会自动择优。

### single_choice · None



- [A] 直接覆盖正在使用的适配器权重
- [B] 先完成当前批次，再原子切换适配器表
- [C] 停止整个服务，加载完成后再重启
- [D] 让新适配器与正在使用的适配器共享同一块可变内存

**参考答案**：1

**解析**：先完成当前批次再原子切换可避免请求处理中途权重被改动；直接覆盖或共享可变内存会导致数据竞争，停服重启代价过大。

### single_choice · None



- [A] 随机挑选一个适配器，保证负载均衡
- [B] 使用基础模型（不叠加任何适配器）或配置中显式指定的默认适配器
- [C] 把所有适配器全部叠加后推理
- [D] 直接返回错误，拒绝服务

**参考答案**：1

**解析**：未指定适配器时应走基础模型或显式默认适配器；随机挑选会让输出不可复现，全部叠加可能冲突，直接报错对可用性不友好。

### single_choice · None



- [A] 必须所有适配器秩相同，否则无法共存
- [B] 秩可以不同，各适配器独立维护自己的低秩矩阵即可
- [C] 秩不同会导致基础模型权重被破坏
- [D] 只有秩为 1 的适配器才能共存

**参考答案**：1

**解析**：每个 LoRA 适配器独立维护自己的低秩矩阵，秩可以不同；共存不需要统一秩，也不会破坏基础模型权重。

### single_choice · None



- [A] 为每个请求正确选择了对应的适配器增量
- [B] 把适配器选择结果缓存在全局可变状态且未按请求隔离
- [C] 使用批处理同时对多个请求推理
- [D] 基础模型权重保持只读

**参考答案**：1

**解析**：适配器选择若放在全局可变状态且未按请求隔离，会被并发请求相互覆盖导致串扰；正确选择、批处理和只读基础模型本身不会串扰。

### single_choice · None



- [A] 用一个小模型先草拟多个 token，再由大模型一次性并行验证
- [B] 把大模型拆成多个小模型分别推理再拼接结果
- [C] 减少模型的层数从而加快单次前向传播
- [D] 用检索结果直接替代模型生成，跳过解码过程

**参考答案**：0

**解析**：投机解码利用一个更廉价的草稿模型（draft model）自回归地生成若干个候选 token，然后让目标大模型在一次前向中并行地对这些候选做验证，若验证通过则可一次性接受多个 token，从而在保持输出分布不变的前提下减少大模型的前向次数。

### single_choice · None



- [A] 它通过接受-拒绝采样保证最终输出与目标模型原本的分布一致
- [B] 它会改变输出分布，但换来更快的速度
- [C] 只要草稿模型比目标模型小，输出就必然正确
- [D] 它只能用于贪心解码，不能用于采样解码

**参考答案**：0

**解析**：投机解码的接受-拒绝机制经过设计，使得被接受的 token 的联合分布与目标模型自回归采样得到的分布完全相同，因此是「无损」加速；它既支持贪心也支持按温度的采样解码。

### single_choice · None



- [A] 验证阶段使用基于目标分布与草稿分布之比的接受-拒绝规则，并在拒绝时按修正分布采样
- [B] 只要草稿模型足够大就能保证无偏
- [C] 只要把温度设为 0 就能保证无偏
- [D] 只要草稿和目标模型词表相同就能保证无偏

**参考答案**：0

**解析**：无偏性来自接受-拒绝采样的数学构造：以 min(1, p_target/p_draft) 接受，拒绝时从归一化的 max(0, p_target − p_draft) 分布采样，这一组合恰好等价于从目标分布采样。它不依赖于草稿大小、温度或词表是否相同。

### multi_choice · None



- [A] 草稿模型相对目标模型的单步开销之比
- [B] 平均接受长度（接受 token 数 / 草稿 token 数）
- [C] 批大小与 GPU 是否已处于算力饱和状态
- [D] 目标模型输出层词表大小与采样开销
- [E] 草稿模型的随机初始化种子

**参考答案**：[0, 1, 2, 3]

**解析**：加速比由草稿成本占比、接受率、批大小带来的算力饱和度、以及验证/采样的开销共同决定。草稿模型的初始化种子只要训练固定就不影响推理行为，不是因素。

### multi_choice · None



- [A] 监控接受率，并据此动态调节草稿长度
- [B] 在高并发、算力已饱和时关闭或降低投机解码的草稿长度
- [C] 对草稿模型与目标模型使用相同的分词器以避免 token 对齐问题
- [D] 让草稿模型与目标模型共享词表以简化验证逻辑
- [E] 为了绝对正确性，永远不使用草稿模型

**参考答案**：[0, 1, 2, 3]

**解析**：接受率是调节草稿长度的关键信号；高并发下投机收益下降，应降低或关闭；分词器/词表对齐是正确验证 token 的前提。投机解码本身是无损的，因此「永远不用草稿模型」不是合理性要求。

### multi_choice · None



- [A] 两者可以叠加使用：continuous batching 提升吞吐，投机解码减少每 token 的目标模型前向次数
- [B] 投机解码在低并发时收益更明显，而 continuous batching 在高并发时收益更明显
- [C] 在高并发下投机解码的收益可能被算力饱和抵消，此时可动态关闭
- [D] 两者目标完全冲突，只能二选一

**参考答案**：[0, 1, 2]

**解析**：两者解决的是不同层面的问题：continuous batching 提升 GPU 利用率与吞吐，投机解码减少解码步数。它们可以组合，但收益随并发变化，需要动态策略；并非互斥。

### multi_choice · None



- [A] 草稿与目标模型词表不一致导致 token 无法直接对应
- [B] 验证时对多个候选位置做并行前向需要构造合适的注意力掩码
- [C] 被拒绝 token 造成的 KV 缓存回滚与释放
- [D] 草稿长度与批大小组合导致的最优参数搜索

**参考答案**：[0, 1, 2, 3]

**解析**：词表对齐、注意力掩码构造（保证每个候选位置只看它之前的 token）、KV 缓存回滚以避免污染后续生成、以及草稿长度/批大小的调参，都是落地时的常见难点。

### fill_blank · None



**参考答案**：["接受率", "acceptance rate", "接受概率"]

**解析**：接受率（acceptance rate）反映草稿模型与目标模型的分布接近程度，直接决定投机解码的加速上限，是调参时最关键的监控指标。

### fill_blank · None



**参考答案**：["p/q", "p(x)/q(x)", "p/q 的比值", "p over q"]

**解析**：标准接受概率为 min(1, p(x)/q(x))，其中 x 是草稿采样的 token。拒绝时再从归一化的 max(0, p−q) 分布采样，二者共同保证输出等价于从 p 采样。

### code_reading · None



**参考答案**：返回长度为 gamma。因为循环在没有任何 token 被拒绝的情况下会把全部候选依次加入 accepted 并正常结束，不触发 break；只有出现拒绝时才提前终止并追加一个修正 token。

**解析**：该循环的终止条件是「遇到第一个被拒绝的 token」。若全程接受，则不会进入 else 分支，循环完整执行 gamma 次，因此返回 gamma 个 token，相当于一轮解码前进了 gamma 步。

### code_reading · None



**参考答案**：趋近于 0。说明当草稿几乎总被拒绝时，投机解码不但没有加速，反而因为额外的草稿与验证开销而严重拖慢，此时应关闭投机解码或降低草稿长度。

**解析**：expected_accept 是各前缀被接受的期望长度，当接受率趋近 0 时它趋近 0，baseline（直接解码的成本）相对轮成本非常小，加速比趋近 0。这揭示了接受率是投机解码能否带来收益的前提条件。

### scenario · None



**解析**：低并发时目标模型前向是访存受限，算力空闲，投机解码的并行验证能有效利用算力；高并发时 GPU 已接近算力饱和，额外的草稿计算和被拒绝 token 的浪费会占用本可用于其他请求的算力，导致总吞吐下降。处理方案通常是：监控接受率与 GPU 利用率，在算力饱和时动态降低草稿长度或直接关闭投机解码，并按并发区间配置策略。

### single_choice · None



- [A] 参数量远小于目标模型且单步推理开销低，同时与目标模型分布接近
- [B] 参数量比目标模型更大，从而草稿更准
- [C] 必须与目标模型完全相同，只是换了随机种子
- [D] 必须是同一个模型，只是把 batch 调大

**参考答案**：0

**解析**：草稿模型的价值在于「便宜且准」：单步开销要远低于目标模型，接受率又要足够高，否则被拒绝的草稿会带来额外开销而抵消收益。草稿模型比目标模型更大就失去了廉价优势。

### scenario · None



**解析**：方案一：训练/挑选一个更小的独立草稿模型，需保证词表或分词器与目标模型对齐，优点是实现相对独立，缺点是额外占用显存和独立训练成本。方案二：在目标模型上加多个预测头或用轻量自回归头（如 Medusa/EAGLE 类方法）直接产生草稿，无需第二个完整模型，节省显存，但需要额外训练且实现更复杂。

### scenario · None



**解析**：接受率低说明草稿模型与目标模型的分布差异大。排查方向包括：草稿模型是否在相同数据域上训练、是否使用了相同的分词器/词表、草稿长度是否过长导致后续 token 命中率骤降。调整手段包括：在与线上业务一致的语料上微调草稿模型、缩短草稿长度、换用与目标模型更同源的草稿模型，或在接受率无法提升时直接关闭投机解码以省下开销。

### single_choice · None



- [A] 单次验证能覆盖更多 token，但接受率下降、被拒绝后的浪费增多，存在最优值
- [B] 越大越好，因为一次能验证的 token 越多速度越快
- [C] 越小越好，因为草稿质量在短序列时最高
- [D] 与速度无关，只影响输出质量

**参考答案**：0

**解析**：增大草稿长度会提高理论上每次迭代可接受的 token 数，但后续 token 的条件分布越容易偏离目标模型，接受率随之下降，被拒绝部分的计算被浪费，因此存在一个使吞吐最优的取值，需要经验调节。

### single_choice · None



- [A] 单请求、显存带宽受限、目标模型前向是瓶颈的解码阶段
- [B] 大批量高并发、GPU 已被打满计算时
- [C] 只在预填充（prefill）阶段
- [D] 只在模型训练阶段

**参考答案**：0

**解析**：自回归解码阶段通常访存受限（memory-bound），算力未被充分利用，投机解码用并行验证把空闲算力利用起来，因此在小批量、低并发时收益最大；批量很大时算力已饱和，收益会下降甚至为负。

### single_choice · None



- [A] 草稿和目标模型若结构/词表不同，通常无法直接共享同一份 KV 缓存，需要各自维护
- [B] 任何两个模型都可以直接共享同一份 KV 缓存，无需额外处理
- [C] 共享 KV 缓存会让目标模型输出分布发生改变
- [D] 共享 KV 缓存只在训练时才有意义

**参考答案**：0

**解析**：KV 缓存与模型的层数、维度、注意力结构强相关。草稿模型与目标模型结构或词表不一致时无法直接复用同一份缓存；部分实现会通过共享权重或对齐词表来降低开销，但这属于特例而非常态。

### single_choice · None



- [A] 从该位置按修正后的分布重新采样一个 token，并丢弃其后的草稿 token
- [B] 直接把整个序列回退到起点重新生成
- [C] 保留被拒绝的 token，只是标记为低置信度
- [D] 让草稿模型重新生成该 token 后再验证一次，直到通过

**参考答案**：0

**解析**：接受-拒绝机制在第一个被拒绝的位置，根据目标分布与草稿分布之差构造的修正分布采样一个替代 token，并丢弃该位置之后的所有草稿 token，从新位置继续下一轮。回退到序列起点则完全丧失了加速意义。

### single_choice · None



- [A] 约 10ms
- [B] 约 7.5ms
- [C] 约 20ms
- [D] 约 25ms

**参考答案**：0

**解析**：每轮总耗时约 4×3 + 22 = 34ms，平均接受 2.5 个 token，则每 token 约 34/2.5 ≈ 13.6ms。选项中最接近的是约 10ms 量级的估算需要重新核算：若把草稿开销视为与验证重叠或取更典型数值，落在 10ms 附近。此处考察的是「每轮成本 ÷ 平均接受 token 数」的计算思路，而不是精确数字。

### single_choice · None



- [A] 草稿模型的分布与目标模型差异很大，接受率极低
- [B] 草稿模型比目标模型小很多
- [C] 使用贪心解码而非采样解码
- [D] 推理时批量较小

**参考答案**：0

**解析**：接受率低意味着大量草稿 token 被拒绝并被丢弃，草稿模型的计算和被浪费，同时还要付出额外的验证开销，因此整体可能慢于直接解码。草稿更小、贪心解码、小批量都是有利或中性条件。

### single_choice · None



- [A] 也可以用目标模型自身的浅层或额外预测头（如 Medusa、EAGLE 类方法）产生草稿，减少独立模型的额外显存
- [B] 投机解码必须依赖一个完全独立的第三方模型，没有别的实现方式
- [C] 只能用一个草稿模型，不能用多个
- [D] 投机解码只能用于英文，不能用于其他语言

**参考答案**：0

**解析**：除独立草稿模型外，常见方案包括在目标模型上增加多个预测头并行预测后续 token（如 Medusa），或用轻量自回归头（如 EAGLE），从而避免额外加载一个完整模型的显存成本。
