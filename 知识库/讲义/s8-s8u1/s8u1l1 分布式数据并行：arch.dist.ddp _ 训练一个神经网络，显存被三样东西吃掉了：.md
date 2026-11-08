# s8u1l1 分布式数据并行：arch.dist.ddp / 训练一个神经网络，显存被三样东西吃掉了：

> 来源 `content/lessons/s8u1l1.json`

## arch.dist.ddp

# 分布式数据并行：arch.dist.ddp

## 一句话直觉
**数据并行（Data Parallelism）** 的核心思想：把同一份模型复制到多张 GPU（图形处理器，Graphics Processing Unit）上，每张卡处理不同的一批数据，然后同步梯度，从而让训练速度近似线性提升。而 **分布式数据并行（Distributed Data Parallel, DDP）** 是 PyTorch 中实现这一思想的工程级方案，它通过 **all-reduce** 高效同步梯度，是当前大模型训练的基础设施。

---

## 1. 为什么需要 DDP？

单卡训练大模型会遇到两个瓶颈：
- **显存不足**：模型参数、激活值、优化器状态放不下。
- **训练太慢**：数据吞吐量受限于单卡算力。

数据并行解决的是“同一模型、多份数据”的问题。最朴素的实现是 **DataParallel（DP）**，但它在单进程内多线程调度，受 GIL（全局解释器锁，Global Interpreter Lock）影响，且主卡负载不均。**DDP** 采用多进程，每张卡一个进程，通信效率高，扩展性好。

**关键结论**：DDP 不是“模型并行”，它要求模型能完整放入单张 GPU；它解决的是吞吐量与显存（batch 维度）的问题。

---

## 2. DDP 的核心机制

DDP 在每张卡上：
1. 复制一份完整的模型副本（replica）。
2. 每个进程读取不同的数据分片（通过 DistributedSampler）。
3. 前向传播后各自计算梯度。
4. 反向传播时，通过 **all-reduce** 把所有卡上的梯度求平均并同步。
5. 每个进程用相同的同步梯度更新自己那份模型，保证参数始终一致。

**all-reduce** 是一种集合通信（collective communication）操作：所有进程贡献自己的梯度，最终每个进程都得到所有梯度之和（或平均）。PyTorch 的 DDP 会将梯度分桶（bucketing），与反向传播重叠通信，从而隐藏通信开销。

**关键结论**：DDP 的正确性依赖于“每个进程看到的初始参数相同、梯度同步后更新相同”。

---

## 3. 进程组与启动方式

DDP 需要一个 **进程组（process group）** 来管理通信。核心 API：
- `torch.distributed.init_process_group(backend='nccl')`：初始化通信后端，GPU 上常用 NCCL。
- `torch.distributed.get_rank()` / `get_world_size()`：获取当前进程编号与总进程数。
- `torch.nn.parallel.DistributedDataParallel(model, device_ids=[local_rank])`：包装模型。

启动方式推荐用 `torchrun`（PyTorch 官方启动器），它会自动设置 `RANK`、`WORLD_SIZE`、`LOCAL_RANK` 等环境变量。

**关键结论**：每张 GPU 对应一个进程；`LOCAL_RANK` 决定用哪张卡，`RANK` 决定全局编号。

---

## 4. 数据分片与梯度同步

`DistributedSampler` 负责把数据集切分给各个进程，保证每个 epoch 数据不重叠。注意：每个 epoch 开始前要调用 `sampler.set_epoch(epoch)`，否则 shuffle 顺序在每个 epoch 会相同，影响训练效果。

梯度同步由 DDP 自动完成，但要注意：
- 只有参与 `forward` 且 `requires_grad=True` 的参数才会同步。
- 若模型中有未使用参数，需设置 `find_unused_parameters=True`（但会降低性能）。
- 保存模型时，通常只在 `rank==0` 的进程保存，避免多进程写冲突。

**关键结论**：DDP 的通信发生在反向传播期间，不需要手动调用 all-reduce。

---

## 5. 工程级注意事项

- **随机种子**：每个进程设置相同种子，保证模型初始化一致。
- **日志与 checkpoint**：只在 rank 0 打印/保存。
- **BatchNorm**：DDP 下默认每卡独立统计，若需跨卡同步需使用 `SyncBatchNorm`。
- **评估**：验证时可用 `DistributedSampler` 并设置 `sampler.set_epoch(0)`，或只在 rank 0 评估。
- **混合精度**：配合 `torch.cuda.amp` 可进一步省显存、提速。

**关键结论**：DDP 是“数据并行”的工程标准；它简单、高效，但要求模型能放入单卡，且代码需适配多进程。

---

## 动手练习

**任务**：在本机（无 GPU 也可用 CPU 的 `gloo` 后端）跑通一个 2 进程的 DDP 训练脚本。

1. 写一个简单的线性回归模型 `nn.Linear(10, 1)`。
2. 用 `torchrun --nproc_per_node=2 train_ddp.py` 启动。
3. 在脚本中：
   - 初始化进程组（GPU 用 `nccl`，CPU 用 `gloo`）。
   - 用 `DistributedSampler` 包装一个随机数据集。
   - 用 `DistributedDataParallel` 包装模型。
   - 训练 5 个 epoch，只在 rank 0 打印 loss。
4. 观察两个进程是否都能正常完成，且 rank 0 的 loss 逐渐下降。

**进阶**：把 `--nproc_per_node` 改成 1 和 2，对比训练时间（CPU 上可能不明显，可换到 GPU 环境）。

## arch.dist.fsdp

## 一句话直觉

**FSDP（Fully Sharded Data Parallel，全分片数据并行）** 的核心思想是：把一个大模型的参数、梯度、优化器状态**全部切碎**分散到多张 GPU 上，每张卡只保存「一片」，需要计算时再临时拼回来，从而用有限的显存训练超大模型。

---

## 第 1 节：为什么需要 FSDP？

### 1.1 从显存瓶颈说起

训练一个神经网络，显存被三样东西吃掉了：

| 占用项 | 大小 |
|--------|------|
| 模型参数（parameters） | P |
| 梯度（gradients） | P |
| 优化器状态（optimizer states，如 Adam 的 m/v） | 2P~4P |

再加上**激活值（activations）**，总量约为 **16P 字节**（混合精度下）。

一个 7B（70 亿参数）模型：

```
7 × 10^9 × 16 ≈ 112 GB
```

单张 80GB 的 A100 根本放不下。

### 1.2 传统方案的局限

- **DDP（Distributed Data Parallel）**：每张卡存**完整**模型副本 → 显存浪费。
- **TP（Tensor Parallelism）**：按张量切分，但通信频繁，跨节点效率低。
- **PP（Pipeline Parallelism）**：按层切分，但存在气泡（bubble），利用率下降。

**FSDP 的定位**：在数据并行的框架下实现**参数分片（sharding）**，兼顾显存节省和通信效率。

### 1.3 关键权衡

```
显存 ↓↓↓   通信 ↑↑   实现复杂度 ↑
```

FSDP 的聪明之处在于：**通信只在需要时发生**（forward 前 all-gather，backward 后 reduce-scatter），不是时刻同步。

---

## 第 2 节：FSDP 的核心机制

### 2.1 三个关键操作

FSDP 在每个训练 step 中执行：

1. **All-Gather（全收集）**：forward 前，把各卡上的参数分片拼成完整参数。
2. **Forward / Backward**：正常计算。
3. **Reduce-Scatter（归约散射）**：backward 后，把梯度求和再切分，每卡只留自己负责的那片梯度。

```
        卡0        卡1        卡2        卡3
参数:  [P0]       [P1]       [P2]       [P3]     ← 初始分片
         │          │          │          │
         └──────────┴──────────┴──────────┘
                    All-Gather
                        ↓
        [P0 P1 P2 P3] [P0 P1 P2 P3] ...        ← forward 时短暂全量
                        ↓
                    Backward
                        ↓
         ┌──────────┬──────────┬──────────┐
         │          │          │          │
        [g0]       [g1]       [g2]       [g3]   ← Reduce-Scatter 后
```

### 2.2 为什么能省显存？

假设 N 张卡，模型参数量 P：

| 项目 | DDP | FSDP |
|------|-----|------|
| 参数 | P | P/N |
| 梯度 | P | P/N |
| 优化器状态 | 4P | 4P/N |
| **总计** | **6P** | **6P/N** |

N=8 时，FSDP 显存占用只有 DDP 的 **1/8**。

### 2.3 分片粒度（Sharding Strategy）

- **FULL_SHARD**：参数/梯度/优化器全部切分（最省显存，通信最多）
- **SHARD_GRAD_OP**：只切梯度+优化器状态（ZeRO-2 等价）
- **NO_SHARD**：等价 DDP
- **HYBRID_SHARD**：节点内 full-shard，节点间复制

---

## 第 3 节：PyTorch 中的 FSDP 使用

### 3.1 最小可用例子

FSDP 的核心 API 是 `torch.distributed.fsdp.FullyShardedDataParallel`，把模型「包一层」即可。

需要注意的关键点：
- **auto_wrap_policy**：因为 FSDP 是**按层包装**的，太大整体包装会一次性 all-gather 全部参数，失去分片意义。通常按 Transformer block 包装。
- **MixedPrecision**：配合混合精度训练。
- **device_id**：指定 GPU。

### 3.2 与 DDP 的代码对比

```python
# DDP：一行包裹，每卡全量
model = DDP(model, device_ids=[rank])

# FSDP：分层包装，每卡分片
model = FSDP(model, auto_wrap_policy=transformer_auto_wrap_policy, ...)
```

### 3.3 训练循环不变

FSDP 封装后的模型，**训练循环与普通模型完全一致**：

```python
output = model(input)
loss = criterion(output, target)
loss.backward()
optimizer.step()
```

梯度同步、参数分片、all-gather / reduce-scatter 都自动在 backward 和 forward 里发生。

---

## 第 4 节：完整可运行示例

下面这段代码展示了 FSDP 的最小骨架（需要多 GPU 环境，如 2 张卡）：

```python
# 见 example_code 字段
```

代码要点：
- 用 `torchrun --nproc_per_node=2 fsdp_demo.py` 启动
- `init_process_group` 初始化进程组
- `FullyShardedDataParallel` 包装模型
- 显存打印可看到分片效果

---

## 第 5 节：工程实践要点

### 5.1 何时用 FSDP？

| 场景 | 推荐 |
|------|------|
| 模型能塞进单卡 | DDP |
| 单卡放不下，多卡要训练 | **FSDP** |
| 模型巨大（>50B）跨节点 | FSDP + TP + PP |
| 推理/微调 | FSDP 或 LoRA/QLoRA |

### 5.2 调优参数

- **`sharding_strategy`**：默认 FULL_SHARD
- **`backward_prefetch`**：BACKWARD_PRE 可提升通信重叠
- **`forward_prefetch`**：提前 all-gather 提高吞吐
- **`limit_all_gathers`**：限制并发 all-gather，省显存
- **`cpu_offload`**：把参数/梯度卸载到 CPU，进一步省显存（训练变慢）

### 5.3 与 Checkpoint 的配合

FSDP 分片后的模型不能直接用 `torch.save(model.state_dict())`（每卡只有一片）。需要用：

```python
from torch.distributed.fsdp import FullyShardedDataParallel as FSDP
from torch.distributed.fsdp import StateDictType

with FSDP.state_dict_type(model, StateDictType.FULL_STATE_DICT):
    state = model.state_dict()
    if rank == 0:
        torch.save(state, "ckpt.pt")
```

---

## 常见误区（Pitfalls）

1. **以为 FSDP 会加速训练**
   错。FSDP 主要目的是**省显存**，因为通信开销，训练速度通常略慢于 DDP。但显存换速度，通常能训练更大模型，总体更划算。

2. **不加 auto_wrap_policy 就 wrap 整个模型**
   这样 all-gather 会一次性完成，失去分片的意义，而且 OOM 依旧。必须**按层包装**（如每层 Transformer block 一层 FSDP）。

3. **用 state_dict 直接存/加载**
   FSDP 分片后 state_dict 是分片的，直接 `torch.save` 会有问题，必须用 `StateDictType.FULL_STATE_DICT` 或 `SHARDED_STATE_DICT`。

4. **以为可以在 per-rank 做数据加载重复**
   用 `DistributedSampler` 保证每个 rank 拿到的数据不重复。

5. **在 forward 里随机数不设种子**
   Dropout 各 rank 不一致会破坏梯度同步语义（虽然一般无碍，但调试困难）。

6. **混用 device_id 和 cpu offload**
   组合不当会出错，需参考官方示例。

7. **忘记调 `torch.cuda.set_device(rank)`**
   会导致所有进程都跑在 GPU 0 上，OOM。

---

## 动手练习

**任务**：用 2 张 GPU 训练一个 3 层 MLP，对比 DDP 和 FSDP 的显存占用。

**步骤**：

1. 在本地/Colab（2×GPU）环境，创建 `fsdp_vs_ddp.py`。
2. 实现一个参数量约 1 亿（隐藏层 4096，3 层）的 MLP。
3. 分别用 DDP 和 FSDP（auto_wrap_policy 按 Linear 层包装）跑一次 forward+backward。
4. 用 `torch.cuda.max_memory_allocated()` 打印每卡峰值显存。
5. 记录结果：FSDP 的峰值显存应该显著低于 DDP。

**提示**：

```python
from torch.distributed.fsdp.wrap import size_based_auto_wrap_policy
import functools

my_policy = functools.partial(size_based_auto_wrap_policy, min_num_params=1e6)
model = FSDP(model, auto_wrap_policy=my_policy, device_id=rank)
```

**启动**：

```bash
torchrun --nproc_per_node=2 fsdp_vs_ddp.py
```

**进阶**：把 `sharding_strategy` 改成 `SHARD_GRAD_OP`，观察显存和速度的变化。


---

## 本课题目

### single_choice · None



- [A] 每个 epoch 的数据划分完全相同，模型收敛变慢或过拟合风险增加
- [B] 程序会直接报错，提示 sampler 未设置 epoch
- [C] 所有进程会读取完全相同的一批数据，导致梯度为零
- [D] DataLoader 会自动随机打乱数据，因此没有影响

**参考答案**：0

**解析**：DistributedSampler 默认使用当前 epoch 作为随机种子的一部分来打乱数据。若不调用 set_epoch，每个 epoch 的划分和顺序完全相同，削弱了数据打乱效果，通常导致收敛变慢或泛化变差。它不会直接报错，也不会让所有进程读同一批数据（各 rank 的索引仍不同），更不会自动打乱。

### single_choice · None



- [A] RANK 和 WORLD_SIZE
- [B] LOCAL_RANK 和 NODE_COUNT
- [C] PROCESS_ID 和 NUM_PROCESSES
- [D] RANK 和 LOCAL_WORLD_SIZE

**参考答案**：0

**解析**：torchrun 会设置 RANK（全局进程序号）和 WORLD_SIZE（总进程数），这是 DDP 初始化 process group 时最常用的两个环境变量。LOCAL_RANK 表示节点内序号，但与其搭配的是 WORLD_SIZE 而不是 NODE_COUNT；PROCESS_ID/NUM_PROCESSES 不是标准变量；LOCAL_WORLD_SIZE 是节点内进程数，不是全局总数。

### single_choice · None



- [A] 指定当前节点上要启动的进程数，通常等于本机使用的 GPU 数量
- [B] 指定总的 GPU 数量，跨节点累加
- [C] 指定每个进程使用的 CPU 线程数
- [D] 指定数据加载器的 worker 数量

**参考答案**：0

**解析**：--nproc_per_node 表示每个节点启动的进程数，单机多卡时通常设为该节点的 GPU 数。总进程数是各节点 nproc_per_node 之和，不是由它单独决定；它不控制 CPU 线程或 DataLoader worker 数量。

### single_choice · None



- [A] 模型很小、计算量极低，而每步的梯度通信开销相对固定，通信成为瓶颈
- [B] 模型很大，单卡放不下，必须用多卡
- [C] 使用 DistributedSampler 并正确调用 set_epoch
- [D] 设置了 find_unused_parameters=True 但模型确实有未使用参数

**参考答案**：0

**解析**：当单步计算量很小时，all-reduce 的通信时间占比会显著上升，多卡不仅不能加速，反而可能因通信开销而变慢。模型很大必须多卡是合理的扩展场景；正确使用 sampler 不是减速原因；确有未使用参数时设置 find_unused_parameters=True 是必要的，不是导致变慢的直接原因。

### single_choice · None



- [A] 允许反向传播时跳过本次未参与计算的分支参数，避免因未使用参数导致的报错或挂起
- [B] 自动找出模型中未被初始化的参数并随机初始化
- [C] 在多个进程间自动查找哪些参数没有同步
- [D] 让优化器忽略所有未使用的参数，不更新它们

**参考答案**：0

**解析**：当模型前向过程中有条件分支导致部分参数未参与计算时，DDP 默认会因为预期梯度缺失而报错。find_unused_parameters=True 会让 DDP 在反向传播时分析计算图，标记未使用参数，从而正确完成同步。它不是初始化参数、不是查找未同步参数，也不是让优化器忽略参数。

### single_choice · None



- [A] 初始化 process group 时需要指定后端（如 nccl、gloo），并让所有参与训练的进程使用相同的通信配置
- [B] 每个进程可以使用不同的后端，只要最终都调用 init_process_group 即可
- [C] process group 只需要在 rank 0 上初始化
- [D] 初始化 process group 时会自动读取 RANK 和 WORLD_SIZE，不需要显式传入

**参考答案**：0

**解析**：所有进程必须用相同的后端和一致的通信参数（如 init_method、world_size、rank）加入同一个 process group。各进程用不同后端无法通信；只在 rank 0 初始化会导致其他进程无法加入；虽然 torchrun 会设置环境变量，但 init_process_group 仍需要正确配置或显式传参。

### single_choice · None



- [A] 对数据进行补齐，使每个进程拿到的样本数相同，可能重复部分样本
- [B] 直接报错，要求数据集大小必须能被进程数整除
- [C] 让某些进程少拿一个 batch，DDP 会自动处理不均衡
- [D] 丢弃多余样本，保证各进程数量一致

**参考答案**：0

**解析**：DistributedSampler 在 drop_last=False 时会通过补齐使每个进程的样本数相同，可能重复少量样本；若 drop_last=True 则丢弃多余样本。它不会因为不能整除而直接报错，也不会让某些进程少拿 batch 后由 DDP 自动处理（各进程步数不一致会导致集合通信不匹配）。

### single_choice · None



- [A] 用 if rank == 0: 包住保存逻辑，并确保其他进程不会因此错过后续的集合通信
- [B] 所有进程都保存，覆盖同一个文件即可
- [C] 在保存前调用 torch.distributed.barrier()，然后所有进程都保存
- [D] 使用 torch.save 时传入 rank 参数，DDP 会自动只让主进程写盘

**参考答案**：0

**解析**：常见做法是用 rank 判断只让主进程写盘，同时注意保存不能引入集合通信不匹配，必要时配合 barrier 同步。所有进程写同一文件会竞争或损坏；barrier 后所有进程保存仍然会写多次；torch.save 没有 rank 参数，DDP 也不会自动限制写盘进程。

### single_choice · None



- [A] 先把模型移动到目标 GPU，再用 DDP 包装，并把该设备作为 device_ids 传入
- [B] 先用 DDP 包装，再把返回的模型移动到 GPU
- [C] 在 CPU 上用 DDP 包装，训练时再把输入数据放到 GPU，DDP 会自动迁移模型
- [D] 必须在 init_process_group 之前完成 DDP 包装

**参考答案**：0

**解析**：通常先把模型 .to(device)，再用 DDP(model, device_ids=[local_rank]) 包装；DDP 包装后再移动模型可能破坏其内部缓冲区和通信钩子。DDP 不会在训练时自动迁移模型，也必须在初始化 process group 之后才能包装。

### single_choice · None



- [A] 为每个进程设置不同的随机种子（如 base_seed + rank），以保证数据增强等随机操作的多样性
- [B] 所有进程设置完全相同的随机种子，保证每张卡看到的数据完全相同
- [C] 不需要设置随机种子，DDP 会自动为每个进程分配不同种子
- [D] 只在 rank 0 设置种子，其他进程继承主进程的随机状态

**参考答案**：0

**解析**：为了避免各进程的随机增强完全相同，通常用 base_seed + rank 给每个进程设置不同种子。所有进程同种子会使随机操作同步，降低多样性；DDP 不会自动设置种子；只在 rank 0 设置并不能让其他进程自动获得不同的随机状态。

### single_choice · None



- [A] 该参数仍会在反向传播中产生梯度并被 all-reduce，但由于优化器不更新它，各进程之间它保持一致
- [B] DDP 会报错，提示存在未加入优化器的参数
- [C] 该参数不会参与 all-reduce，各进程会逐渐不一致
- [D] 优化器会自动把遗漏的参数加入参数组

**参考答案**：0

**解析**：DDP 的梯度同步基于反向传播中产生梯度的参数，与是否加入优化器无关。遗漏的参数仍会被 all-reduce，但因优化器不更新它，各进程里该参数保持一致（初始相同且不更新）。DDP 不会因此报错，也不会自动加入优化器。

### single_choice · None



- [A] 通过 init_method 指定的通信方式（如 TCP 地址或共享文件系统）建立全局通信，后端常选用 nccl
- [B] 各节点直接读写同一个本地磁盘文件来交换梯度
- [C] 通过 Python 的 multiprocessing.Queue 跨节点传递梯度
- [D] 由 rank 0 节点轮询其他节点的 GPU 显存来同步参数

**参考答案**：0

**解析**：多机 DDP 通过 init_method（如 tcp:// 地址或共享文件）让各节点进程找到彼此并建立通信组，GPU 间通信后端通常用 nccl。本地磁盘文件、multiprocessing.Queue 都不能跨节点高效通信；轮询显存不是同步机制。

### single_choice · None



- [A] 梯度在反向传播过程中由 DDP 自动同步，各进程的 optimizer.step() 使用相同的梯度更新参数
- [B] 梯度只在第一次 optimizer.step() 时同步一次，之后各进程独立更新
- [C] 必须手动调用 all_reduce 同步梯度，DDP 本身不负责梯度同步
- [D] optimizer.step() 会自动触发梯度同步，因此 loss.backward() 中不需要通信

**参考答案**：0

**解析**：DDP 在反向传播期间通过注册的 autograd hook 自动进行梯度 all-reduce，因此各进程在 optimizer.step() 时看到的是相同的平均梯度，从而保持参数一致。它不是只同步一次；不需要手动 all_reduce（那是更底层的做法）；反向传播过程中就已经完成通信，而不是等到 step()。

### single_choice · None



- [A] 根据 LOCAL_RANK（或进程内序号）指定 cuda:LOCAL_RANK，每个进程使用一张不同的卡
- [B] 所有进程都使用 cuda:0，由 DDP 自动分发计算
- [C] 根据 RANK 对显卡数量取模后指定，以保证全局唯一
- [D] 不需要指定设备，DDP 会自动选择空闲显卡

**参考答案**：0

**解析**：单机多卡时通常用 LOCAL_RANK 作为当前节点内的 GPU 编号，让每个进程绑定到不同显卡；全局 RANK 包含跨节点信息，取模虽然有时也能用，但不是标准做法。所有进程都用 cuda:0 会导致显存竞争和错误。DDP 不会自动帮你选卡。

### single_choice · None



- [A] 在验证/日志代码外使用 if rank == 0 判断，并在训练结束时调用 destroy_process_group()
- [B] 在所有进程上都执行验证，只是不打印日志
- [C] 在验证前调用 torch.cuda.synchronize()
- [D] 把验证放到单独的 DataLoader 中并设置 num_workers=0

**参考答案**：0

**解析**：常见做法是用 rank 判断让只有主进程做验证和日志，同时训练结束时调用 destroy_process_group() 释放资源。只在部分进程执行验证本身可以，但若不销毁进程组或同步不当，可能出现挂起；其他选项并没有解决进程生命周期问题。

### single_choice · None



- [A] 其他进程会在集合通信处一直等待，训练挂起或超时
- [B] DDP 会自动跳过该进程，训练照常进行
- [C] 该进程的参数会变成随机值，但其他进程不受影响
- [D] 程序会立即抛出 RuntimeError 并提示 batch 为空

**参考答案**：0

**解析**：DDP 的梯度同步是集合通信，所有进程必须对同一组参数执行反向传播并到达通信点。某个进程跳过 backward 会使其他进程在 all-reduce 处等待，导致挂起或超时。DDP 不会自动跳过该进程，也不会只让该进程参数随机化。

### single_choice · None



- [A] DDP 使用多进程，每个进程有独立的 Python 解释器和优化器；DP 使用单进程多线程，受 GIL 限制且主卡负载不均
- [B] DDP 只能用于单机多卡，DP 可以跨节点训练
- [C] DDP 不需要设置随机种子，DP 需要为每个线程设置随机种子
- [D] DDP 的显存占用总是比 DP 高，因为它为每张卡复制了完整模型

**参考答案**：0

**解析**：DDP 采用多进程，每个进程独立运行，绕开 GIL，通信效率更高，负载也更均衡；DP 是单进程多线程，受 GIL 影响且主卡承担额外聚合负担。DDP 支持多机，DP 基本只适合单机；DDP 同样需要处理随机种子；显存方面两者都会复制模型，这不是 DDP 的缺点。

### single_choice · None



- [A] sampler
- [B] shuffle
- [C] batch_sampler
- [D] worker_init_fn

**参考答案**：0

**解析**：DistributedSampler 是 Sampler 的子类，应通过 DataLoader 的 sampler 参数传入。传入 sampler 后不能再设置 shuffle=True（二者互斥）；batch_sampler 用于控制每个 batch 的索引，不是这里要传的；worker_init_fn 用于初始化 worker 的随机种子，与数据划分无关。

### single_choice · None



- [A] 该进程的梯度变为 NaN，all-reduce 后其他进程的梯度也被污染为 NaN，整个训练崩溃
- [B] DDP 会自动把 NaN 替换为 0，训练继续
- [C] 只有该进程的参数变为 NaN，其他进程不受影响
- [D] DDP 会检测到 NaN 并自动回滚到上一个检查点

**参考答案**：0

**解析**：DDP 的梯度 all-reduce 是求和后取平均，只要有一个进程的梯度含 NaN，整个通信结果就会是 NaN，进而所有进程的参数都被污染。DDP 不会自动替换 NaN、不会隔离该进程，也不会自动回滚检查点。

### single_choice · None



- [A] 将 BatchNorm 替换为 SyncBatchNorm 或改用 GroupNorm/LayerNorm，以保证跨进程统计量一致
- [B] 保持普通 BatchNorm，DDP 会自动同步 BN 的均值和方差
- [C] 把 BatchNorm 的 momentum 设为 1，避免统计量不一致
- [D] 只在 rank 0 上更新 BatchNorm 的 running_mean 和 running_var

**参考答案**：0

**解析**：普通 BatchNorm 只在单个进程的 mini-batch 内统计，各进程统计量不同，会影响一致性。常用方案是使用 SyncBatchNorm 在进程间同步统计量，或改用对 batch 不敏感的归一化。DDP 不会自动同步普通 BN；把 momentum 设为 1 也不能解决；只在 rank 0 更新会导致其他进程统计量不同步。

### single_choice · None



- [A] 计算速度会随参数量线性下降
- [B] 每张卡都要存下全部参数、梯度和优化器状态，显存很快不够用
- [C] 数据并行的通信量会变成常数的两倍
- [D] 只有第一张卡能进行反向传播

**参考答案**：1

**解析**：数据并行要求每个副本都持有完整的参数、梯度和优化器状态，因此显存占用随模型规模增长，当模型大到单卡放不下时就会 OOM，这正是 FSDP 这类分片方案要解决的问题。

### single_choice · None



- [A] 把训练数据切成更小的 batch 分给不同卡
- [B] 把模型的参数、梯度和优化器状态切分（分片）到各张卡上，计算时再临时聚合所需分片
- [C] 把同一个模型复制多份以提高吞吐
- [D] 把优化器换成显存占用更小的算法

**参考答案**：1

**解析**：FSDP 属于分片数据并行，把参数、梯度、优化器状态按 rank 切分，需要某一层计算前通过 all-gather 临时还原该层参数，计算后再释放，从而降低单卡常驻显存。

### multi_choice · None



- [A] 它把参数、梯度和优化器状态分片存储，降低单卡常驻显存
- [B] 计算某层之前通常需要把该层参数聚合回来
- [C] 它完全不需要任何集合通信
- [D] 反向传播后梯度通常会做归约并重新分片
- [E] 它依靠每张卡都保存完整模型来实现扩展

**参考答案**：[0, 1, 3]

**解析**：FSDP 的核心是分片存储 + 用时聚合 + 梯度归约分片，这三点都依赖集合通信；「不需要通信」和「每卡保存完整模型」与分片思想相反，是常见误解。

### multi_choice · None



- [A] 模型参数量很大，单卡放不下完整的参数、梯度和优化器状态
- [B] 希望在不显著牺牲全局 batch 的情况下扩展到更多 GPU
- [C] 只想把数据切成更多份，不关心模型显存占用
- [D] 想降低单卡常驻的优化器状态显存占用

**参考答案**：[0, 1, 3]

**解析**：FSDP 解决的是单卡显存不足和扩展性问题，尤其是参数、梯度、优化器状态三者共同带来的显存压力；单纯「只想切数据、不关心显存」并不是 FSDP 的动机，那更接近普通数据并行的诉求。

### multi_choice · None



- [A] 分片组决定了参数被切分到哪些 rank 上
- [B] 分片组内的集合通信负责聚合分片参数
- [C] 分片组必须包含所有参与训练的 rank，否则无法训练
- [D] 可以让多个分片组共同承担全局数据并行的角色
- [E] 分片组越小，单卡保存的分片通常越大（在总模型不变时）

**参考答案**：[0, 1, 3, 4]

**解析**：分片组限定分片与通信范围，不必等于全部 rank；分片组越小，参与切分的 rank 越少，每个分片相对越大。选项 C 把分片组错误地限定为全体 rank。

### multi_choice · None



- [A] 用后立即释放 all-gather 出来的完整参数
- [B] 把模型拆成合适的 FSDP 单元，避免一次性聚合所有层参数
- [C] 把优化器状态也纳入分片，而不是每个 rank 各存一份
- [D] 在前向之前把所有层的完整参数都一次性 all-gather 并常驻

**参考答案**：[0, 1, 2]

**解析**：释放时机、封装粒度和优化器状态分片都是从不同角度降低常驻/峰值显存的手段；一次性聚合全部层参数反而会制造很大的峰值显存，与目标相反。

### fill_blank · None



**参考答案**：["all-gather", "allgather", "all gather", "AllGather", "all_gather"]

**解析**：all-gather 让每个 rank 拿到所有 rank 的分片，从而拼出该层完整参数；反向之后配合 reduce-scatter 把梯度重新变回分片。

### fill_blank · None



**参考答案**：["reduce-scatter", "reducescatter", "reduce scatter", "ReduceScatter", "reduce_scatter"]

**解析**：reduce-scatter 同时完成「对所有 rank 的梯度求和」和「把结果切成对应分片」两件事，是 FSDP 梯度处理的关键操作。

### code_reading · None



**参考答案**：这段代码体现的是「按层（或按模块）用时才聚合、用后立即释放」的策略。因为完整参数只在某一层前向期间短暂存在，峰值常驻显存大致只有单层完整参数加上各 rank 自己的分片，而不是整个模型所有层的完整参数之和，所以比一次性聚合全部参数更省显存。

**解析**：关键在于「临时聚合 + 用后释放」把峰值显存从整模型规模降到单层规模，代价是反向时可能需要再次 all-gather。

### code_reading · None



**参考答案**：应该使用 reduce-scatter。它一方面对所有 rank 的梯度进行归约（求和），另一方面把归约后的结果切分成与各 rank 对应的分片，使每个 rank 只长期保留自己那一份梯度，从而与参数分片保持一致。

**解析**：reduce-scatter 把 reduce 和 scatter 两步合一，正好满足「求和后再按 rank 分片」的梯度处理需求。

### scenario · None



**解析**：场景的关键约束是「单卡放不下完整模型」和「想保持大全局 batch」。FSDP 通过把参数、梯度、优化器状态分片到多个 rank 来解决显存问题；计算前用 all-gather 临时聚合所需分片，反向后用 reduce-scatter 归约并重新分片；分片组限定通信与切分范围，多个分片组还可以配合全局数据并行来扩展 batch。

### scenario · None



**解析**：把大模块拆成更细的 FSDP 单元，使得每次 all-gather 的完整参数规模更小；同时确保完整参数「用后立即释放」，并让下一单元的 all-gather 与当前单元计算重叠，从而压低峰值显存、减少通信等待，避免一次性聚合过大模块导致的 OOM。

### single_choice · None



- [A] 只需分片参数，梯度必须每个 rank 都保存完整副本
- [B] 只需分片梯度，参数必须每个 rank 都保存完整副本
- [C] 参数和梯度都按相同的分片方式切分，因此单卡常驻的梯度也只是一部分
- [D] 参数和梯度都不分片，只分片优化器状态

**参考答案**：2

**解析**：FSDP 对参数和梯度都做分片，各 rank 只长期保存自己那一份分片；进行反向前向计算时通过通信临时还原完整参数，反向后梯度再做 reduce-scatter 回到分片状态。

### single_choice · None



- [A] all-gather
- [B] reduce-scatter
- [C] broadcast
- [D] all-reduce

**参考答案**：0

**解析**：all-gather 把分散在各 rank 的参数分片收集成完整参数供本层计算；反向传播结束后还会用 reduce-scatter 把梯度归约并重新切成分片。

### single_choice · None



- [A] 永远保留到整个训练结束
- [B] 在本次前向计算使用完毕后，通常在前向完成后立即释放
- [C] 只在最后一步训练结束时释放
- [D] 只有发生了显存溢出时才释放

**参考答案**：1

**解析**：FSDP 采用「用后即释放」策略：某层前向用完全参数后即可释放该层的完整参数，反向传播时若需要再重新 all-gather，从而把峰值显存控制在接近单层而非整模型的规模。

### single_choice · None



- [A] 可以让不同分片组各自独立训练完全无关的模型
- [B] 可以用较小的分片组换取较小的通信域，同时还能配合更大的全局 batch
- [C] 可以避免使用任何集合通信
- [D] 可以让每张卡都保存完整参数

**参考答案**：1

**解析**：分片组（sharding group）限定分片和相应集合通信的范围，分片组越小，组内通信参与方越少；而全局数据并行可以跨分片组继续扩展，两者结合兼顾显存与扩展性。

### single_choice · None



- [A] 先对模型做量化，再交给 FSDP
- [B] 直接用普通的 DistributedDataParallel 包装即可
- [C] 用 FSDP 提供的方式包装模型（或在初始化后对模块进行分片封装），再启动训练
- [D] 必须先把模型参数全部转成半精度，否则无法分片

**参考答案**：2

**解析**：FSDP 需要把模型用其提供的包装/分片机制封装，从而知道模型的模块结构并据此切分参数；普通 DDP 只做梯度同步，不做参数分片。

### single_choice · None



- [A] all-gather
- [B] reduce-scatter
- [C] broadcast
- [D] gather

**参考答案**：1

**解析**：reduce-scatter 在一步中既对各 rank 的梯度求和（归约），又把结果切成与其 rank 对应的分片，正好符合 FSDP 梯度分片的需求。

### single_choice · None



- [A] 把所有层一次性 all-gather 完再开始前向
- [B] 按模块分层/分块封装，使得下一层参数可以在当前层计算时预取，实现通信与计算重叠
- [C] 关闭所有集合通信以提升速度
- [D] 只在最后一步做一次 all-gather

**参考答案**：1

**解析**：把模型拆成更小的 FSDP 单元，可以让某层的 all-gather 与另一层的计算重叠，减少通信等待；一次性聚合全部参数则会让峰值显存和通信尖峰都变差。

### single_choice · None



- [A] 两者都只复制模型，不做任何参数分片
- [B] DDP 每个 rank 保存完整模型，FSDP 把模型分片保存并临时聚合
- [C] FSDP 不需要任何集合通信，DDP 需要
- [D] DDP 只能用于单机，FSDP 只能用于多机

**参考答案**：1

**解析**：DDP 保持每份完整副本，仅同步梯度；FSDP 把参数、梯度、优化器状态分片，计算时临时聚合，因此更省显存但通信模式不同。
