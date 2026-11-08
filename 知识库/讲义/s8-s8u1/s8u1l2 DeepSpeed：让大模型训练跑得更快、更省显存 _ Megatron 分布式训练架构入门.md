# s8u1l2 DeepSpeed：让大模型训练跑得更快、更省显存 / Megatron 分布式训练架构入门

> 来源 `content/lessons/s8u1l2.json`

## arch.dist.deepspeed

# DeepSpeed：让大模型训练跑得更快、更省显存

## 一句话直觉

当你训练的模型大到单张 GPU 装不下、或者慢得离谱时，DeepSpeed 就是那把“把模型切碎、把显存省下来、把速度提上去”的瑞士军刀。

---

## 1. 为什么需要 DeepSpeed？

大模型（Large Language Model, LLM）训练有两个核心痛点：

1. **显存不够**：模型参数、梯度、优化器状态（optimizer states）加在一起，动辄是参数量的 16 倍以上。
2. **训练太慢**：单卡算力有限，数据并行（Data Parallelism, DP）通信开销大。

DeepSpeed 是微软开源的一个深度学习优化库，核心目标是：**用更少的显存、更少的通信、更少的代码改动，训练更大的模型**。

它最著名的技术是 **ZeRO（Zero Redundancy Optimizer）**，通过把优化器状态、梯度、参数分片（shard）到多张 GPU 上，消除数据并行中的内存冗余。

```python
# 直觉演示：一个 1.5B 参数的模型，传统数据并行下每张卡要存多少？
# 假设用 Adam，混合精度训练
params = 1.5e9
bytes_per_param_fp16 = 2  # 模型参数 + 梯度
bytes_per_param_adam = 12  # Adam: fp32 参数副本 + m + v

per_gpu_gb = params * (bytes_per_param_fp16 + bytes_per_param_adam) / (1024**3)
print(f"传统 DP 每张卡至少需要: {per_gpu_gb:.1f} GB 显存")
# 输出约 19.6 GB，还没算激活值（activation）
```

---

## 2. ZeRO 的三个阶段：从“人人有份”到“按需分配”

ZeRO 把训练状态分成三块：**优化器状态（Optimizer States）**、**梯度（Gradients）**、**参数（Parameters）**。

| 阶段 | 分片对象 | 显存节省 | 通信量 |
|------|----------|----------|--------|
| ZeRO-1 | 优化器状态 | ~4x | 低 |
| ZeRO-2 | + 梯度 | ~8x | 中 |
| ZeRO-3 | + 参数 | 线性于 GPU 数 | 高 |

```python
# 用一个简单的比喻理解 ZeRO 分片
# 假设 4 张 GPU，每张卡原本都要存完整的 100 份状态
full_states = 100
gpus = 4

zero1 = full_states / gpus + full_states + full_states  # 只分片优化器状态
zero2 = full_states / gpus * 2 + full_states            # 分片优化器状态+梯度
zero3 = full_states / gpus * 3                          # 三者都分片

print(f"ZeRO-1 每卡: {zero1:.0f}, ZeRO-2 每卡: {zero2:.0f}, ZeRO-3 每卡: {zero3:.0f}")
# ZeRO-1 每卡: 225, ZeRO-2 每卡: 150, ZeRO-3 每卡: 75
```

**关键结论**：ZeRO 阶段越高，显存越省，但通信越多。工程上常从 ZeRO-2 起步，显存实在不够再上 ZeRO-3。

---

## 3. 最小可运行示例：用 DeepSpeed 训练一个玩具模型

DeepSpeed 的使用流程和 PyTorch 几乎一样，只是多了一个 `deepspeed.initialize()` 和配置文件（JSON）。

```python
# train_deepspeed.py
import torch
import torch.nn as nn
import deepspeed

# 1. 定义模型
def make_model():
    return nn.Sequential(
        nn.Linear(128, 256),
        nn.ReLU(),
        nn.Linear(256, 10),
    )

# 2. DeepSpeed 配置：这里用 ZeRO-2 + 混合精度
ds_config = {
    "train_batch_size": 64,
    "optimizer": {"type": "Adam", "params": {"lr": 1e-3}},
    "fp16": {"enabled": True},
    "zero_optimization": {"stage": 2},
}

# 3. 初始化 DeepSpeed 引擎
model = make_model()
engine, optimizer, _, _ = deepspeed.initialize(
    model=model,
    model_parameters=model.parameters(),
    config=ds_config,
)

# 4. 正常训练循环
device = engine.device
for step in range(10):
    x = torch.randn(64, 128).to(device)
    y = torch.randint(0, 10, (64,)).to(device)
    loss = nn.CrossEntropyLoss()(engine(x), y)
    engine.backward(loss)
    engine.step()
    if step % 5 == 0:
        print(f"step {step}, loss={loss.item():.4f}")
```

启动方式（单机多卡）：

```bash
deepspeed --num_gpus=2 train_deepspeed.py
```

---

## 4. 工程级要点：配置、通信与检查点

### 4.1 配置文件是核心

DeepSpeed 的 JSON 配置决定了性能表现，常见字段：

- `train_batch_size` / `train_micro_batch_size_per_gpu`：全局与单卡 batch。
- `gradient_accumulation_steps`：梯度累积。
- `zero_optimization.stage`：ZeRO 阶段。
- `fp16` 或 `bf16`：混合精度。
- `offload_optimizer` / `offload_param`：把状态卸载到 CPU/NVMe，用时间换显存。

```python
# 一个更工程化的 ZeRO-3 配置片段
zero3_config = {
    "train_batch_size": 128,
    "train_micro_batch_size_per_gpu": 4,
    "gradient_accumulation_steps": 4,
    "bf16": {"enabled": True},
    "zero_optimization": {
        "stage": 3,
        "offload_optimizer": {"device": "cpu"},
        "offload_param": {"device": "cpu"},
    },
}
# 注意：offload 会显著降低速度，只在显存极度紧张时使用
```

### 4.2 检查点（Checkpoint）

DeepSpeed 提供 `engine.save_checkpoint()` 和 `engine.load_checkpoint()`，能正确处理分片状态。

```python
# 保存与加载
engine.save_checkpoint("./ckpt", tag="step_100")
# engine.load_checkpoint("./ckpt", tag="step_100")
```

### 4.3 与 Hugging Face 集成

实际项目里常用 `transformers` + `accelerate` + DeepSpeed：

```python
# 伪代码示意
from transformers import Trainer, TrainingArguments

args = TrainingArguments(
    output_dir="./out",
    deepspeed="ds_config.json",  # 直接指定 DeepSpeed 配置
    per_device_train_batch_size=4,
)
trainer = Trainer(model=model, args=args, train_dataset=dataset)
trainer.train()
```

---

## 5. 什么时候用、怎么选？

- **模型 < 1B**：普通 DDP（Distributed Data Parallel）通常够用。
- **1B ~ 10B**：ZeRO-2 + 混合精度，性价比最高。
- **> 10B 或单卡装不下**：ZeRO-3，必要时加 CPU offload。
- **超大模型 + 多机**：ZeRO-3 + 张量并行（Tensor Parallelism）/流水线并行（Pipeline Parallelism）。

**核心权衡**：显存 ↔ 通信 ↔ 速度。DeepSpeed 给你旋钮，工程上要按硬件和模型规模调。

---

## 动手练习

**任务**：在本机（或 Colab 单卡）上，用 DeepSpeed 训练一个两层 MLP 做 MNIST 分类。

要求：
1. 写一份 `ds_config.json`，启用 ZeRO-2 和 fp16。
2. 用 `deepspeed.initialize()` 包装模型和优化器。
3. 训练 1 个 epoch，打印每 100 步的 loss。
4. 对比：把 `zero_optimization.stage` 改成 0（即关闭 ZeRO），观察 `torch.cuda.max_memory_allocated()` 的变化。

提示：单卡也能跑 DeepSpeed，只是分片效果不明显；重点是跑通流程、理解配置。

---

## 常见误区

1. **以为 DeepSpeed 只支持多卡**：单卡也能用，只是 ZeRO 分片收益小。
2. **无脑上 ZeRO-3**：通信开销大，小模型反而更慢。
3. **忘记设置 `train_batch_size`**：DeepSpeed 会报错或行为异常。
4. **offload 当默认选项**：CPU/NVMe offload 会显著拖慢训练，只在显存不够时用。
5. **直接 `torch.save` 保存 DeepSpeed 模型**：分片状态会丢，必须用 `engine.save_checkpoint()`。

## arch.dist.megatron

# Megatron 分布式训练架构入门

> **一句话直觉**：当模型大到一张 GPU 装不下时，Megatron 告诉你如何把模型“切”到多张 GPU 上，让它们协同训练，同时尽量不浪费算力。

Megatron（全称 Megatron-LM，最初由 NVIDIA 提出）是一套用于**大规模语言模型分布式训练**（distributed training）的架构与工程实践集合。它要解决的核心问题是：模型参数量、激活值（activation）和优化器状态（optimizer state）会远超单卡显存，必须把训练任务拆分到多张 GPU 上。

本讲义用 5 个小节带你从“为什么要并行”走到“Megatron 的三种并行怎么配合”。

---

## 1. 为什么需要分布式训练？

训练一个神经网络需要三类显存：

- **参数**（parameters）：模型权重。
- **梯度**（gradients）：反向传播算出的每个参数的导数。
- **优化器状态**（optimizer state）：如 Adam 的动量和方差，通常每个参数还要多占 2 份。

粗略估算，用 Adam 训练一个 `P` 参数的模型，单卡显存需求约为 `16P` 字节（fp16 参数 2 + fp16 梯度 2 + fp32 主权重 4 + 优化器状态 8）。一个 100 亿参数模型仅状态就要约 160 GB，远超单张 GPU。

因此必须并行（parallelism）。Megatron 把并行分成两大类：

- **数据并行**（Data Parallelism, DP）：每张卡有完整模型，但喂不同的数据。
- **模型并行**（Model Parallelism, MP）：把模型本身切开，包括**张量并行**（Tensor Parallelism, TP）和**流水线并行**（Pipeline Parallelism, PP）。

---

## 2. 数据并行（DP）与它的瓶颈

数据并行的做法是：复制模型到 N 张卡，每张卡处理一个 mini-batch 的分片，反向传播后通过 **All-Reduce**（全归约）同步梯度。

```python
# 概念演示：数据并行中的梯度平均（用 PyTorch DDP 的伪代码结构）
import torch
import torch.distributed as dist

# 假设已初始化进程组：dist.init_process_group("nccl")
# 每个 rank 持有一份完整模型和不同数据分片
model = torch.nn.Linear(1024, 1024).cuda()
optimizer = torch.optim.SGD(model.parameters(), lr=0.01)

# 前向 + 反向
loss = model(torch.randn(8, 1024).cuda()).sum()
loss.backward()

# 关键步骤：对每个参数的梯度做 All-Reduce，得到全局平均梯度
for p in model.parameters():
    dist.all_reduce(p.grad, op=dist.ReduceOp.SUM)
    p.grad /= dist.get_world_size()

optimizer.step()
```

**瓶颈**：每张卡仍要存完整模型、梯度和优化器状态。当模型本身超过单卡容量时，DP 就失效了，需要模型并行。

---

## 3. 张量并行（TP）：把矩阵乘法切开

张量并行是 Megatron 的招牌技术。以 Transformer 里的线性层 `Y = XA` 为例，可以按两种方式切：

- **列并行**（Column Parallel）：把权重 `A` 按列切成 `[A1, A2]`，每张卡算一部分输出列，然后拼接。
- **行并行**（Row Parallel）：把 `A` 按行切，每张卡得到部分和，最后 All-Reduce 求和。

Megatron 在 Transformer 的 MLP 和 Attention 中精心安排“列并行 → 行并行”的配对，使得中间只需少量通信。

```python
import torch
import torch.distributed as dist

# 模拟列并行线性层：权重按输出维度切成 2 份，分给 2 个 rank
class ColumnParallelLinear(torch.nn.Module):
    def __init__(self, in_features, out_features, world_size, rank):
        super().__init__()
        self.out_per_rank = out_features // world_size
        # 每张卡只保存自己那部分权重
        self.weight = torch.nn.Parameter(torch.randn(self.out_per_rank, in_features))
        self.rank = rank

    def forward(self, x):
        # 每张卡计算自己的输出列
        local_out = x @ self.weight.t()
        # 收集所有卡的结果并拼接（实际用 all_gather / 或后续行并行直接对接）
        gathered = [torch.zeros_like(local_out) for _ in range(dist.get_world_size())]
        dist.all_gather(gathered, local_out)
        return torch.cat(gathered, dim=-1)
```

**直觉**：张量并行把一层内的计算切细，通信发生在层内，适合单机多卡（NVLink 带宽高）。

---

## 4. 流水线并行（PP）：按层切开

流水线并行把模型按层切成多个阶段（stage），每个阶段放到不同 GPU。数据被切成多个 micro-batch，像工厂流水线一样依次经过各阶段。

关键概念是 **气泡**（bubble）：流水线启动和排空阶段会有 GPU 空闲。常用优化是 **1F1B**（One Forward One Backward）调度，让前向和反向交错，减少气泡。

```python
# 概念演示：流水线并行的 micro-batch 调度思路
num_micro_batches = 4
num_stages = 3  # 3 个流水线阶段

# 简化模拟：每个阶段处理一个 micro-batch 需要 1 个时间单位
schedule = []
for t in range(num_micro_batches + num_stages - 1):
    for stage in range(num_stages):
        mb = t - stage
        if 0 <= mb < num_micro_batches:
            schedule.append((t, stage, mb))

for t, stage, mb in schedule:
    print(f"时间 {t}: 阶段 {stage} 处理 micro-batch {mb}")
```

**直觉**：流水线并行通信量小（只在阶段边界传激活），适合跨机扩展；但会引入气泡，需要足够多的 micro-batch 来掩盖。

---

## 5. Megatron 的三维并行：TP × PP × DP

真实的大模型训练会同时使用三种并行，称为 **3D 并行**（3D Parallelism）：

- **TP** 在节点内切层，利用高带宽 NVLink。
- **PP** 跨节点切层，通信量小。
- **DP** 复制剩余部分，扩大全局 batch size。

总 GPU 数 = `TP_size × PP_size × DP_size`。

Megatron 的工程价值在于：它把这三者的通信组（process group）管理、调度顺序、显存优化（如激活重计算 activation recomputation）都封装好，并提供高效实现。

```python
# 概念演示：计算 3D 并行下每个 rank 的身份
TP, PP, DP = 8, 4, 2
world_size = TP * PP * DP
print(f"总 GPU 数: {world_size}")

# 给定全局 rank，解析出它在 TP/PP/DP 中的坐标
rank = 33
tp_rank = rank % TP
pp_rank = (rank // TP) % PP
dp_rank = rank // (TP * PP)
print(f"rank {rank}: tp={tp_rank}, pp={pp_rank}, dp={dp_rank}")
```

**记忆口诀**：TP 切“宽”，PP 切“深”，DP 切“数据”。

---

## 动手练习

**任务**：用纯 Python（不依赖 GPU）模拟一个 3D 并行配置。

1. 定义 `TP=2, PP=3, DP=2`。
2. 编写函数 `parse_rank(global_rank, TP, PP, DP)`，返回 `(tp_rank, pp_rank, dp_rank)`。
3. 遍历所有全局 rank，打印每个 rank 的三维坐标。
4. 额外计算：同一个 `dp_rank` 且同一个 `tp_rank`、不同 `pp_rank` 的 rank 是否属于同一个流水线组？用代码验证你的答案。

完成后你就能理解 Megatron 中 `mpu`（model parallel unit）如何根据全局 rank 推导出各种通信组。

---

## 小结

- Megatron 解决的是“模型大到单卡放不下”的问题。
- 三种并行：TP 切层内矩阵、PP 切层间、DP 切数据。
- 3D 并行组合起来，才能训练千亿级模型。
- 核心权衡：显存节省 vs 通信开销 vs GPU 利用率（气泡）。


---

## 本课题目

### single_choice · None



- [A] 整个训练过程中所有 GPU 上的总批大小
- [B] 单个 GPU 上的批大小
- [C] 每个数据并行组的批大小
- [D] 模型一次前向传播处理的样本数上限

**参考答案**：0

**解析**：DeepSpeed 的 train_batch_size 是全局批大小，等于单卡批大小乘以数据并行度（GPU 数量）。这是分布式训练中常用的约定，便于统一配置不同规模下的训练。

### single_choice · None



- [A] ZeRO-1 分片优化器状态，ZeRO-2 额外分片梯度，ZeRO-3 额外分片模型参数
- [B] ZeRO-1 分片模型参数，ZeRO-2 分片梯度，ZeRO-3 分片优化器状态
- [C] ZeRO-1 同时分片优化器状态和梯度，ZeRO-2 再加入模型参数分片
- [D] ZeRO 只能分片优化器状态，梯度与参数始终在各卡上完整保留

**参考答案**：0

**解析**：ZeRO 的三个阶段依次增加分片对象：Stage 1 分片优化器状态，Stage 2 在此基础上分片梯度，Stage 3 再分片模型参数。这是 ZeRO 最核心的分级设计。

### single_choice · None



- [A] 仅保存参数的一个分片，前向/反向时按需 all-gather 完整参数
- [B] 保存完整参数，但与优化器状态分片
- [C] 不保存任何参数，全部放在 CPU
- [D] 只保存参数副本用于梯度同步

**参考答案**：0

**解析**：ZeRO-3 将参数划分为分片，每卡只持有一部分，计算时通过 all-gather 临时重建完整参数，用完即释放，从而大幅降低单卡参数显存。

### single_choice · None



- [A] 禁用 ZeRO 分片，相当于普通数据并行
- [B] 启用 ZeRO-1
- [C] 启用 ZeRO-2
- [D] 启用 ZeRO-3

**参考答案**：0

**解析**：stage 0 表示不启用 ZeRO 分片，此时 DeepSpeed 行为接近标准数据并行；stage 1/2/3 分别对应逐级增加的分片策略。

### single_choice · None



- [A] 梯度累积步数设置得太大
- [B] 学习率过高导致发散
- [C] FP16 动态 loss scaling 失效导致梯度下溢
- [D] 数据中存在异常值

**参考答案**：0

**解析**：梯度累积步数大本身不会直接导致 NaN；学习率过高、loss scaling 失效、数据异常都是常见诱因，梯度累积只会改变有效批大小。

### single_choice · None



- [A] 按分片保存，需要合并后才能得到完整权重
- [B] 始终保存合并后的完整权重
- [C] 只保存优化器状态，不保存权重
- [D] 只保存配置文件

**参考答案**：0

**解析**：ZeRO-3 下各卡只持有参数分片，直接保存的是分片权重，加载到单卡推理前通常需要合并；也可以通过配置保存合并后的权重。

### single_choice · None



- [A] 通过 ZeRO 等技术对优化器状态、梯度和参数进行分片以降低单卡显存
- [B] 自动提升模型准确率
- [C] 完全取代反向传播
- [D] 不再需要任何通信

**参考答案**：0

**解析**：DDP 只做梯度同步，而 DeepSpeed 在此之上提供 ZeRO 分片、混合精度、offload 等显存优化机制，使其能训练更大模型，但通信仍然存在，精度也不会自动提升。

### single_choice · None



- [A] 64
- [B] 16
- [C] 8
- [D] 32

**参考答案**：0

**解析**：全局批大小 = micro_batch_size_per_gpu × gradient_accumulation_steps × GPU 数量 = 2 × 8 × 4 = 64。

### single_choice · None



- [A] 用额外的前向计算换取激活显存的降低
- [B] 减少模型参数量
- [C] 加快数据加载速度
- [D] 避免使用优化器

**参考答案**：0

**解析**：梯度检查点不保存全部中间激活，反向时重新计算，从而显著降低激活显存，代价是增加计算量；它不改变参数量，也与数据加载和优化器无关。

### single_choice · None



- [A] 它把模型按层切分到不同设备上，micro-batch 在设备间流水执行
- [B] 它把同一层的计算复制到所有设备
- [C] 它只能用于单卡训练
- [D] 它通过缩小模型来加速训练

**参考答案**：0

**解析**：流水线并行把模型的不同层分配到不同设备，并通过 micro-batch 调度形成流水线以提高利用率；它不是复制计算，也不缩小模型，且需要多设备。

### single_choice · None



- [A] 降低 ZeRO stage 或增大 bucket size 以减少通信次数
- [B] 增大 offload 到 NVMe 的比例
- [C] 把 fp16 改为 fp32 以提升精度
- [D] 增加 gradient_accumulation_steps

**参考答案**：0

**解析**：显存充足时，过高的 ZeRO 分片或 offload 会带来额外通信/传输开销拖慢速度，降低 stage 或增大桶大小可减少通信；增大累积步数不会直接提速，改成 fp32 通常更慢。

### single_choice · None



- [A] 控制每隔多少训练步打印一次日志
- [B] 控制每步使用的 GPU 数量
- [C] 设置学习率的步长
- [D] 设置梯度裁剪的阈值

**参考答案**：0

**解析**：steps_per_print 决定日志打印频率，属于监控配置，与 GPU 数量、学习率步长、梯度裁剪阈值均无关。

### single_choice · None



- [A] 可以在单卡显存有限时训练更大参数量的模型
- [B] 训练速度一定比 Stage 2 更快
- [C] 不再需要数据并行
- [D] 可以完全避免通信开销

**参考答案**：0

**解析**：ZeRO-3 在分片优化器状态和梯度的基础上进一步分片模型参数，使单卡参数显存大幅下降，从而支持更大模型；但通信量增加，速度不一定更快，数据并行仍然需要，通信也无法完全避免。

### single_choice · None



- [A] 让模型参数、梯度和激活以半精度存储与计算，并通常配合动态 loss scaling
- [B] 只把优化器状态转成半精度，模型参数仍为单精度
- [C] 只在推理时使用半精度，训练时仍用单精度
- [D] 自动把 batch size 减半以避免溢出

**参考答案**：0

**解析**：DeepSpeed 的 fp16 配置启用混合精度训练，模型与计算以 FP16 为主，并通过 loss scaling 避免梯度下溢。优化器状态通常保留 FP32 以保证数值稳定。

### single_choice · None



- [A] 8
- [B] 4
- [C] 32
- [D] 128

**参考答案**：0

**解析**：micro batch size = train_batch_size / gradient_accumulation_steps = 32 / 4 = 8。梯度累积通过在多个 micro step 上累加梯度来模拟更大的全局批大小。

### single_choice · None



- [A] 可以把优化器状态或参数卸载到 CPU 内存甚至 NVMe，以显存换速度
- [B] 卸载后模型精度会自动提升
- [C] 卸载只能用于推理，不能用于训练
- [D] 卸载后训练速度必然提升

**参考答案**：0

**解析**：offload 将优化器状态、参数等转移到 CPU 内存或 NVMe，缓解显存压力，但会增加数据传输开销，通常以速度换显存，精度不受影响，训练和推理均可使用。

### single_choice · None



- [A] 在数据并行卡之间高效地聚合和分发梯度或参数分片
- [B] 在单卡内部复制张量以加速计算
- [C] 压缩模型参数以减少存储
- [D] 替代优化器进行参数更新

**参考答案**：0

**解析**：all-gather 收集各卡分片拼成完整张量，reduce-scatter 在归约的同时把结果分片回各卡，二者是 ZeRO 等分片策略中通信的核心原语。

### single_choice · None



- [A] 优化器状态及其计算
- [B] 模型的前向激活
- [C] 数据加载器
- [D] 学习率调度器

**参考答案**：0

**解析**：ZeRO-Offload 把优化器状态和优化器计算卸载到 CPU，从而在单卡上支持更大模型；激活值通常不在卸载范围内，数据加载器和调度器与 offload 无关。

### single_choice · None



- [A] 先用 deepspeed.initialize 包装模型和优化器，再用返回的引擎进行反向与步进
- [B] 直接调用 torch.distributed.init_process_group 即可获得 DeepSpeed 全部特性
- [C] 手动把模型参数除以 GPU 数量
- [D] 必须把模型转换为单精度才能启动

**参考答案**：0

**解析**：DeepSpeed 需要通过 deepspeed.initialize 返回引擎对象，由引擎接管前向、反向和优化器步进，从而启用 ZeRO、混合精度、offload 等特性。

### single_choice · None



- [A] 它控制梯度归约时桶的大小，影响通信与显存的权衡
- [B] 它控制模型隐藏层维度
- [C] 它决定数据加载的线程数
- [D] 它设置学习率的衰减系数

**参考答案**：0

**解析**：reduce_bucket_size 指定梯度归约时使用的桶大小，较大的桶可提高带宽利用率但增加显存占用，是通信与显存之间的权衡参数。

### single_choice · None



- [A] 数据并行将模型参数拆分到不同设备，模型并行将数据拆分到不同设备
- [B] 数据并行将数据拆分到不同设备而模型副本相同，模型并行将模型参数拆分到不同设备
- [C] 两者完全相同，只是命名不同
- [D] 数据并行只用于推理，模型并行只用于训练

**参考答案**：1

**解析**：数据并行是每个设备持有完整模型副本但处理不同数据批次；模型并行是把模型参数（层或张量）拆分到不同设备上。两者常结合使用。

### single_choice · None



- [A] 流水线并行不需要通信
- [B] 流水线并行将不同层分配到不同设备，通信量较小，但需要处理流水线气泡
- [C] 张量并行不能用于 Transformer
- [D] 流水线并行只能用于推理阶段

**参考答案**：1

**解析**：流水线并行按层切分模型到不同设备，层间通信量远小于张量并行中每层内的 all-reduce 通信，但会引入流水线气泡（bubble）导致设备空闲。

### multi_choice · None



- [A] 数据并行
- [B] 张量并行
- [C] 流水线并行
- [D] 序列并行
- [E] 随机并行

**参考答案**：[0, 1, 2, 3]

**解析**：数据并行、张量并行、流水线并行和序列并行（Sequence Parallelism）都是常见的分布式训练策略。“随机并行”不是一种标准并行策略。

### multi_choice · None



- [A] ZeRO-1 分片优化器状态
- [B] ZeRO-2 分片梯度和优化器状态
- [C] ZeRO-3 分片参数、梯度和优化器状态
- [D] ZeRO 可以减少单卡显存占用
- [E] ZeRO 会增加通信量

**参考答案**：[0, 1, 2, 3, 4]

**解析**：ZeRO-1/2/3 分别分片优化器状态、梯度和参数，均能减少单卡显存占用，但分片带来的通信开销会增加（尤其是 ZeRO-3 需要参数 all-gather）。

### multi_choice · None



- [A] 流水线阶段数（pipeline stages）
- [B] micro-batch 数量
- [C] 梯度累积步数
- [D] 节点间网络带宽

**参考答案**：[0, 1]

**解析**：气泡大小主要取决于流水线阶段数和 micro-batch 数量。micro-batch 越多，气泡占比越小。梯度累积步数和网络带宽影响吞吐但不直接决定气泡比例。

### multi_choice · None



- [A] 权重按输入维度（行）切分
- [B] 每个设备接收部分输入并计算部分结果
- [C] 输出需要跨设备求和（all-reduce）
- [D] 输入需要完整的权重才能计算

**参考答案**：[0, 1, 2]

**解析**：行并行将权重按输入维度切分，每个设备接收部分输入并计算部分输出，最终需要 all-reduce 求和得到完整输出。输入不需要完整权重。

### multi_choice · None



- [A] 数据并行的梯度 all-reduce
- [B] 张量并行的 all-gather 和 reduce-scatter
- [C] 流水线并行的点对点 send/recv
- [D] 序列并行的 all-gather 用于 LayerNorm 等操作

**参考答案**：[0, 1, 2, 3]

**解析**：数据并行用 all-reduce 同步梯度；张量并行用 all-gather/reduce-scatter 组合行/列并行；流水线并行用点对点通信；序列并行在特定操作（如 LayerNorm）前后需要 all-gather。

### fill_blank · None



**参考答案**：["模型参数", "参数", "parameters", "模型参数(parameters)"]

**解析**：ZeRO-3 在 ZeRO-1 和 ZeRO-2 的基础上，进一步对模型参数进行分片，使得每张卡只保存部分参数，从而大幅降低单卡显存需求。

### fill_blank · None



**参考答案**：["micro-batch", "micro batch", "微批次", "microbatches", "micro-batches"]

**解析**：micro-batch 是流水线并行中的关键概念，将 batch 拆分后可以让各阶段并行工作，填充流水线，减少气泡比例。

### code_reading · None



**参考答案**：全局 batch size = micro-batch size × 数据并行度 × 梯度累积步数 = 8 × 4 × 2 = 64。张量并行度不影响全局 batch size 的计算。

**解析**：全局 batch size 只与 micro-batch size、数据并行度和梯度累积步数有关。张量并行只是将模型参数拆分到多卡，不增加有效数据并行副本数。

### code_reading · None



**参考答案**：气泡比例为 (p-1)/(m+p-1) = (4-1)/(16+4-1) = 3/19 ≈ 15.8%。其中 p 为流水线阶段数，m 为 micro-batch 数量。

**解析**：流水线气泡的经典公式为 (p-1)/(m+p-1)，p 为流水线阶段数，m 为 micro-batch 数。micro-batch 越多，气泡占比越小。

### scenario · None



**解析**：合理的方案是：在节点内使用张量并行（利用高带宽 NVLink），跨节点使用流水线并行（减少跨节点通信频率），最外层使用数据并行（进一步扩展吞吐）。这样可以把高通信量的张量并行限制在节点内，降低对跨节点低带宽网络的依赖。

### single_choice · None



- [A] 将每个注意力头的维度进一步拆分为两半
- [B] 按注意力头（head）维度切分，每个设备负责一部分头
- [C] 只在 batch 维度上切分
- [D] 只在序列长度维度上切分

**参考答案**：1

**解析**：多头注意力天然适合按头维度切分，每个设备计算一部分注意力头，之后通过列并行/行并行线性层组合结果，这是 Megatron-LM 中的经典做法。

### scenario · None



**解析**：推荐使用 ZeRO 优化器（特别是 ZeRO-1 或 ZeRO-2），它通过将优化器状态（乃至梯度）分片到各数据并行设备上，减少单卡显存占用。副作用是分片带来的额外通信开销，可能降低训练吞吐。

### single_choice · None



- [A] 等于单卡 micro-batch size
- [B] 等于 micro-batch size × 数据并行度 × 梯度累积步数
- [C] 等于 micro-batch size × 张量并行度
- [D] 等于 micro-batch size × 流水线并行度

**参考答案**：1

**解析**：全局 batch size = micro-batch size × 数据并行度 × 梯度累积步数。张量并行和流水线并行不增加有效数据并行副本数（流水线并行需考虑 micro-batch 数量）。

### single_choice · None



- [A] 减少张量并行的通信量
- [B] 减少流水线气泡，提高设备利用率
- [C] 增加每个设备的内存占用
- [D] 降低模型参数量

**参考答案**：1

**解析**：1F1B 调度让每个设备在完成一次前向传播后立即开始反向传播，交错进行，从而减小流水线气泡，提高设备利用率，同时减少峰值激活内存。

### single_choice · None



- [A] ZeRO-1 仅对优化器状态进行分片
- [B] ZeRO-1 对优化器状态、梯度和参数都进行分片
- [C] ZeRO-3 仅对梯度进行分片
- [D] ZeRO 与模型并行互斥，不能同时使用

**参考答案**：0

**解析**：ZeRO 分为三个阶段：ZeRO-1 分片优化器状态，ZeRO-2 额外分片梯度，ZeRO-3 再额外分片模型参数。ZeRO 是数据并行的内存优化技术，可与模型并行结合使用。

### single_choice · None



- [A] 输入 X 的特征维度
- [B] 权重 W 的输出维度（列）
- [C] 权重 W 的输入维度（行）
- [D] batch 维度

**参考答案**：1

**解析**：列并行（Column Parallel）将权重 W 按输出维度（列）切分，每个设备计算输出的一部分，输入 X 是完整的，输出需要拼接或后续处理。

### single_choice · None



- [A] 减小模型参数量
- [B] 将全局 batch 拆分为更小的批次以填充流水线，减少气泡
- [C] 替代梯度累积
- [D] 减少张量并行通信

**参考答案**：1

**解析**：micro-batch 是将一个 batch 进一步拆分成的小批次，让不同流水线阶段可以并行处理不同 micro-batch，从而填充流水线、减少气泡，提高设备利用率。

### single_choice · None



- [A] 张量并行
- [B] 数据并行
- [C] 流水线并行
- [D] 以上都不需要

**参考答案**：1

**解析**：数据并行中每个设备计算不同数据上的梯度，需要通过 all-reduce 同步梯度以保持模型副本一致。张量并行使用 all-gather/reduce-scatter，流水线并行使用点对点通信。

### single_choice · None



- [A] 优先使用最高程度的张量并行
- [B] 根据模型大小、集群拓扑（节点内/节点间带宽）和内存限制综合选择
- [C] 只使用数据并行即可
- [D] 仅根据 batch size 决定

**参考答案**：1

**解析**：并行策略选择需要综合考虑模型参数量、单卡显存、节点内 NVLink 带宽、节点间网络带宽等因素。通常节点内用张量并行，节点间用流水线并行或数据并行。
