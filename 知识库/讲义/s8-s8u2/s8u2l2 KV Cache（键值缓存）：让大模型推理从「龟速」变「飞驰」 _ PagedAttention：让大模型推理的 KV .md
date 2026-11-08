# s8u2l2 KV Cache（键值缓存）：让大模型推理从「龟速」变「飞驰」 / PagedAttention：让大模型推理的 KV Cache 不再浪费显存

> 来源 `content/lessons/s8u2l2.json`

## arch.serve.kv_cache

# KV Cache（键值缓存）：让大模型推理从「龟速」变「飞驰」

---

## 一句话直觉

大模型生成文本时，每吐出一个新词都要把「前文所有词」重新算一遍注意力——**KV Cache 就是把这份重复计算的结果存下来，让每一步只算「新词」对「老词」的注意力，把生成速度提升几倍到几十倍**。

---

## 1. 为什么需要 KV Cache？先看「没有它会发生什么」

### 1.1 自回归生成（Autoregressive Generation）的本质

大语言模型（LLM, Large Language Model）是**自回归**的：给它一段提示词（prompt），它预测下一个 token（词元），然后把预测出的 token 拼回输入，再预测下一个……直到生成结束。

```python
# 伪代码：没有 KV Cache 的推理循环
input_ids = tokenize("今天天气")        # [今天, 天气]
for step in range(5):
    logits = model(input_ids)          # 每次都把全部历史重新送进模型
    next_token = argmax(logits[-1])
    input_ids = input_ids + [next_token]
```

问题在于：**第 t 步输入的序列长度是 t，模型要为这 t 个 token 都计算 Key 和 Value**。而第 t+1 步，前 t 个 token 的 Key/Value 其实和上一步完全一样——白白重算。

### 1.2 注意力中的 K 和 V 分别是什么

Transformer 的**自注意力（Self-Attention）**里，每个 token 会产生三个向量：

- **Query（Q，查询）**：当前 token「想找什么信息」
- **Key（K，键）**：每个 token「能提供什么信息」
- **Value（V，值）**：每个 token「实际携带的信息内容」

注意力计算：`softmax(Q · Kᵀ / √d) · V`。

关键洞察：**生成第 t+1 个 token 时，只有新 token 的 Q 是新的；所有历史 token 的 K、V 都没有变**。所以只要把历史 K、V 缓存起来，每步计算量从 O(t²) 降到 O(t)。

---

## 2. KV Cache 的核心机制：用「缓存」换「时间」

### 2.1 直观类比

想象你在写一封长信，每次加一句话都要把整封信从头读一遍才能接上下文。有了 KV Cache，就像你把前文合上做成「索引卡」，每写一句只翻索引卡 + 看新写的那句。

### 2.2 两种阶段：Prefill（预填充）和 Decode（解码）

| 阶段 | 干什么 | 是否用 KV Cache |
|------|--------|-----------------|
| **Prefill** | 一次性处理整段 prompt，写入所有 K/V 到缓存 | 缓存**被写入** |
| **Decode** | 一步步生成新 token，每步追加一组新 K/V | 缓存**被读取并追加** |

```python
import torch
import torch.nn.functional as F

class SimpleKVCacheAttention(torch.nn.Module):
    def __init__(self, d_model=64, n_heads=8):
        super().__init__()
        self.d_model = d_model
        self.n_heads = n_heads
        self.head_dim = d_model // n_heads
        # Q/K/V 投影
        self.q_proj = torch.nn.Linear(d_model, d_model)
        self.k_proj = torch.nn.Linear(d_model, d_model)
        self.v_proj = torch.nn.Linear(d_model, d_model)

    def forward(self, x, past_kv=None):
        # x: [batch, seq_len, d_model]
        B, T, _ = x.shape
        q = self.q_proj(x).view(B, T, self.n_heads, self.head_dim).transpose(1, 2)
        k = self.k_proj(x).view(B, T, self.n_heads, self.head_dim).transpose(1, 2)
        v = self.v_proj(x).view(B, T, self.n_heads, self.head_dim).transpose(1, 2)

        # 关键：如果有历史缓存，把新的 K、V 追加进去
        if past_kv is not None:
            past_k, past_v = past_kv
            k = torch.cat([past_k, k], dim=2)   # 沿序列维度拼接
            v = torch.cat([past_v, v], dim=2)

        # 注意力：Q 只用当前 step 的，K/V 用全部历史的
        scores = torch.matmul(q, k.transpose(-2, -1)) / (self.head_dim ** 0.5)
        attn = F.softmax(scores, dim=-1)
        out = torch.matmul(attn, v)
        out = out.transpose(1, 2).reshape(B, T, self.d_model)

        return out, (k, v)   # 返回新的缓存

# 演示：prefill 一次，之后每步只传 1 个 token
model = SimpleKVCacheAttention()
prompt = torch.randn(1, 5, 64)              # 5 个 token 的 prompt
_, cache = model(prompt)                     # Prefill：写入缓存
for _ in range(3):
    new_token = torch.randn(1, 1, 64)        # Decode：每次 1 个 token
    _, cache = model(new_token, past_kv=cache)
    print('cache K shape:', cache[0].shape)  # 序列长度逐步增长
```

运行上面的代码你会看到缓存 K 的序列长度从 5 → 6 → 7 → 8，而每步输入只有 1 个 token。

### 2.3 时间与显存的权衡

- **省时间**：Decode 阶段每步只算 1 个 token 的 Q，K/V 直接读缓存。
- **费显存**：缓存大小 = `2 × batch × n_layers × seq_len × n_heads × head_dim × dtype_bytes`。
  - 例如 LLaMA-7B（32 层、32 头、head_dim=128、fp16），seq_len=2048，batch=1：约 **2 × 32 × 2048 × 32 × 128 × 2 ≈ 1.07 GB**。
  - 序列越长、层数越多，KV Cache 越吃显存，所以才有 **MQA（Multi-Query Attention）**、**GQA（Grouped-Query Attention）**、**PagedAttention（vLLM 的核心）** 等优化。

---

## 3. 工程视角：在生产推理框架里长什么样

### 3.1 形状与布局

生产级 KV Cache 一般预分配一个大张量：

```
[ 2,               # K 和 V
  num_layers,
  batch_size,
  num_kv_heads,    # 注意：GQA 里 kv_heads < q_heads
  max_seq_len,     # 预分配的「最大长度」
  head_dim ]
```

每个 decode step 用 `cache_position` 写入到对应位置，无需 cat，避免内存碎片。

### 3.2 常见策略

- **静态分配**：预留 max_seq_len，简单但浪费显存。
- **动态分配 / PagedAttention**：像操作系统分页一样按块（block）管理 KV，显存利用率可达 90%+。
- **量化 KV Cache**：把 fp16 缓存放成 int8/int4，用少量精度换大幅显存节省。
- **Sliding Window（滑动窗口）**：只保留最近 N 个 token 的 KV（如 Mistral 的 SWA），适合长文但上下文有限。
- **Prefix Caching（前缀缓存）**：多个请求共享相同 system prompt 时复用 KV，极大提速。

---

## 4. 从零写一个最小可用的 KV Cache 推理器

上面小节已经看到 attention 层面的 KV Cache。下面用一个「玩具语言模型」把它串起来，演示完整推理循环中缓存的**生命周期**：

```python
import torch

class ToyLM(torch.nn.Module):
    """极简语言模型：embedding + 单层 attention + lm_head"""
    def __init__(self, vocab=100, d_model=64, n_heads=4):
        super().__init__()
        self.embed = torch.nn.Embedding(vocab, d_model)
        self.attn = SimpleKVCacheAttention(d_model, n_heads)
        self.lm_head = torch.nn.Linear(d_model, vocab)

    def forward(self, ids, past_kv=None):
        x = self.embed(ids)                     # [B, T, d]
        h, new_kv = self.attn(x, past_kv)       # 消费/产生缓存
        logits = self.lm_head(h)                # [B, T, vocab]
        return logits, new_kv

@torch.no_grad()
def generate(model, prompt_ids, max_new=8):
    # 1) Prefill：整段 prompt 一次送入，建立初始缓存
    logits, cache = model(prompt_ids)
    out = prompt_ids.tolist()[0]
    next_id = logits[:, -1, :].argmax(-1, keepdim=True)
    out.append(next_id.item())

    # 2) Decode：每步只喂 1 个 token，缓存持续增长
    for _ in range(max_new - 1):
        logits, cache = model(next_id, past_kv=cache)
        next_id = logits[:, -1, :].argmax(-1, keepdim=True)
        out.append(next_id.item())
    return out

# 试跑：prompt 长度 4，再生成 8 个 token
model = ToyLM()
prompt = torch.randint(0, 100, (1, 4))
result = generate(model, prompt, max_new=8)
print('生成的 token id 序列：', result)
print('总长度：', len(result))
```

观察重点：`generate` 里 Prefill 只调用一次模型，之后每步传入的是长度为 1 的 `next_id`，缓存自动增长。

---

## 5. 关键结论速查

1. **KV Cache 缓存的是每层注意力的 Key 和 Value**，不是 Query。
2. **Prefill 阶段写入缓存，Decode 阶段读取并追加**，把每步复杂度从 O(t²) 降到 O(t)。
3. **代价是显存**，随 `batch × layers × seq_len × kv_heads × head_dim` 线性增长。
4. **工业优化三件套**：GQA 减少 kv_heads、PagedAttention 按块分配、KV 量化省显存。
5. **判断是否需要 KV Cache 的准则**：只要是**自回归**生成（token 逐个出），就必须用；遇到并行编码任务（如 BERT 类）则不需要。

---

## 6. 动手练习

**任务：给下面的 mini attention 加一个「缓存命中率」打印，并对比开/关 KV Cache 的耗时差异。**

要求：
1. 修改 `SimpleKVCacheAttention.forward`，当 `past_kv is None` 时打印 `[prefill] cache miss, 建立缓存`；否则打印 `[decode] cache hit, 序列长度 = X`。
2. 构造一个 prompt 长度 128，连续 decode 32 步。
3. 用 `time.perf_counter()` 分别测量「带缓存」和「每步重跑整段序列（不带缓存）」的总耗时，输出对比。
4. 用 matplotlib 画一条柱状图，横轴是方案（with cache / without cache），纵轴是耗时（ms）。
5. 提交一份简短结论：在你的机器上，加速比大约是多少？

提示：不带缓存的实现方式——每步都把 `prompt + 已生成的所有 token` 作为输入喂给 `forward(x, past_kv=None)`，只取最后一个位置的输出。

完成后你就能直观感受到为什么所有主流推理框架（vLLM、TGI、TensorRT-LLM、SGLang）都把 KV Cache 当作头等大事。

## arch.serve.paged_attention

# PagedAttention：让大模型推理的 KV Cache 不再浪费显存

> **一句话直觉**：大模型（LLM, Large Language Model）推理时，每个 token 都要缓存 Key/Value 向量（KV Cache），传统方式按“最大长度”预分配连续显存，浪费高达 60%–80%；PagedAttention 借鉴操作系统虚拟内存分页（paging）思想，把 KV Cache 切成固定大小的“页”（block）按需分配、非连续存储，从而让显存利用率接近 100%，吞吐量提升 2–4 倍。

---

## 1. 为什么需要 PagedAttention：从 KV Cache 说起

自回归（autoregressive）生成时，每生成一个新 token，模型都要“看”之前所有 token 的 Key 和 Value。为了避免重复计算，推理引擎会把历史 K/V 缓存下来，这就是 **KV Cache**。

问题在于：**请求的长度事先未知**。传统做法是按 `max_seq_len`（比如 2048）一次性预留连续显存。可是实际很多请求只用了 100 个 token，剩下的 1948 个位置就白白空着——这部分叫 **内部碎片（internal fragmentation）**。还有**外部碎片（external fragmentation）**：不同请求大小不一，连续内存块难以复用。

一句话：**KV Cache 不是缺显存，而是显存被“预留但没用”的方式浪费掉了。**

---

## 2. 核心思想：把 KV Cache 当“虚拟内存”来管

PagedAttention 的灵感来自操作系统的虚拟内存分页机制：

1. 把每个序列的 KV Cache 切分为固定大小的 **块（block）**，例如每块存 16 个 token 的 K/V。
2. 显存被预先划分成许多物理块，块与块之间**不需要连续**。
3. 每个序列维护一张 **块表（block table）**，记录“逻辑块 i → 物理块 j”的映射。
4. 生成新 token 时，只在块表末尾追加；块用满才分配新物理块。

这样，**内部碎片最多只剩一个块**（≤16 token），显存浪费从 60%+ 降到 <4%。

---

## 3. 注意力计算如何跨块完成

注意力（attention）需要在序列维度上做 softmax(QKᵀ)V。既然 K/V 分散在多个非连续块里，计算就需要“按块表收集”：

- 对每个 query 位置，遍历它的块表；
- 逐块加载 K、V，计算局部的 QKᵀ；
- 用 online softmax 技巧合并多块的结果，得到最终输出。

这正是 PagedAttention **kernel** 做的事：它在 GPU 上把非连续的物理块“拼”成逻辑上连续的 KV，做分块注意力（block-wise attention）。对上层模型来说，看到的仍是一个完整序列。

---

## 4. 附赠红利：前缀共享与写时复制

分页带来的不止是省显存，还有两个“免费”的能力：

- **前缀共享（prefix sharing）**：多个请求如果有相同的 prompt 前缀（如系统提示、few-shot 示例），可以让它们的块表指向同一批物理块，显存只存一份。这在并行采样（n 选 1）、多轮对话中极其常见。
- **写时复制（Copy-on-Write, CoW）**：当某个序列要修改共享块时，才复制出一份私有块，其余共享块继续复用。

结果是：**显存节省越多，能同时并发的请求就越多，吞吐量自然上去。**

---

## 5. 工程视角：它在哪里、怎么用

PagedAttention 最早由 vLLM 提出（Kwon et al., SOSP 2023），现已成为主流推理引擎的标配：

- **vLLM**：`enable_prefix_caching=True` 开启前缀共享；`gpu_memory_utilization` 控制显存水位。
- **TensorRT-LLM**：`paged_kv_cache` 选项。
- **SGLang / LMDeploy**：同样内置分页 KV 管理。

调参时最常碰的两个旋钮：
- `block_size`：通常 8/16/32。太大→内部碎片回升；太小→块表管理开销上升。
- `max_num_seqs` / `max_num_batched_tokens`：决定并发上限，直接受分页效率影响。

---

## 小结

| 维度 | 传统连续 KV Cache | PagedAttention |
|---|---|---|
| 存储方式 | 按 max_len 连续预留 | 按需分配、非连续块 |
| 内部碎片 | 高（可达 60%–80%） | 低（<4%，至多一块） |
| 前缀共享 | 难 | 原生支持（块表指向） |
| 写时复制 | 无 | 支持 |
| 吞吐提升 | 基线 | 2–4× |

一句话记住它：**把 KV Cache 从“整块预订的酒店房间”改造成“按页分配的虚拟内存”，显存不再空置，吞吐自然起飞。**

```python
from dataclasses import dataclass, field

# ============================================================
# 用纯 Python 模拟 PagedAttention 的块分配与块表逻辑
# 无需 GPU，零基础也能跑起来看到核心机制
# ============================================================

BLOCK_SIZE = 4          # 每个物理块存 4 个 token 的 K/V
NUM_PHYSICAL_BLOCKS = 16  # 模拟显存中的物理块总数


@dataclass
class PhysicalBlock:
    """一个物理块：存放若干 token 的 KV 占位（这里用整数示意）。"""
    block_id: int
    slots: list = field(default_factory=list)  # 已写入的 token 数

    def is_full(self) -> bool:
        return len(self.slots) >= BLOCK_SIZE

    def append(self, token_id: int):
        self.slots.append(token_id)


class BlockAllocator:
    """负责物理块的分配 / 释放（模拟分页内存分配器）。"""
    def __init__(self, num_blocks: int):
        self.free_blocks = list(range(num_blocks))
        self.blocks = {i: PhysicalBlock(i) for i in range(num_blocks)}

    def allocate(self) -> PhysicalBlock:
        if not self.free_blocks:
            raise MemoryError("显存不足：没有空闲物理块")
        bid = self.free_blocks.pop(0)
        block = self.blocks[bid]
        block.slots.clear()
        return block

    def free(self, block_id: int):
        self.free_blocks.append(block_id)


class Sequence:
    """一个推理请求（序列）：维护逻辑块到物理块的映射（块表）。"""
    def __init__(self, seq_id: int, allocator: BlockAllocator):
        self.seq_id = seq_id
        self.allocator = allocator
        self.block_table: list[int] = []   # 逻辑块 i -> 物理块 id
        self.num_tokens = 0

    def append_token(self, token_id: int):
        """追加一个新 token：只在新逻辑块开始时申请物理块。"""
        # 当前是否要开一个新逻辑块？
        if self.num_tokens % BLOCK_SIZE == 0:
            phys = self.allocator.allocate()
            self.block_table.append(phys.block_id)
        # 定位到最后一个逻辑块对应的物理块
        phys_id = self.block_table[-1]
        self.allocator.blocks[phys_id].append(token_id)
        self.num_tokens += 1

    def free(self):
        """序列结束后释放所有物理块。"""
        for bid in self.block_table:
            self.allocator.free(bid)
        self.block_table.clear()
        self.num_tokens = 0

    def __repr__(self):
        return (f"Seq(id={self.seq_id}, tokens={self.num_tokens}, "
                f"block_table={self.block_table})")


# ============================ 演示 ============================
if __name__ == "__main__":
    alloc = BlockAllocator(NUM_PHYSICAL_BLOCKS)
    seq = Sequence(seq_id=1, allocator=alloc)

    # 生成 6 个 token：需要 2 个物理块（4 + 2）
    for t in range(6):
        seq.append_token(token_id=t)
        print(f"  写入 token {t} -> {seq}")

    print("\n序列实际的物理块占用情况：")
    for bid in seq.block_table:
        print(f"  physical block {bid}: {alloc.blocks[bid].slots}")

    # 剩余可用物理块（空闲显存）
    print(f"\n剩余空闲物理块数: {len(alloc.free_blocks)} / {NUM_PHYSICAL_BLOCKS}")

    # 释放序列
    seq.free()
    print(f"释放后空闲物理块数: {len(alloc.free_blocks)} / {NUM_PHYSICAL_BLOCKS}")
```


---

## 本课题目

### single_choice · None



- [A] 存储模型权重以减少显存占用
- [B] 缓存历史 token 的注意力键值，避免每步重复计算
- [C] 保存用户请求日志以便审计
- [D] 对输入做分词并缓存词表

**参考答案**：1

**解析**：自回归生成时每一步都要对全部历史位置计算注意力，缓存已算好的 key/value 可以避免重复前向计算，从而显著加速解码。权重存储、日志、分词缓存都是别的机制。

### single_choice · None



- [A] 与有缓存相同
- [B] 仅需要计算新增 token，与有缓存等价
- [C] 需要对全部 100 个历史位置重新计算注意力
- [D] 计算量减半，因为只算一半历史

**参考答案**：2

**解析**：无缓存时每一步都要对全部历史序列重新做注意力计算，复杂度随序列长度增长；有缓存时只增量计算新 token 的 key/value。

### single_choice · None



- [A] 请求结束后及时释放，避免长期占用显存
- [B] 永久保留以便下次任意请求复用
- [C] 只在进程退出时释放
- [D] 从不释放，靠操作系统交换

**参考答案**：0

**解析**：请求完成后其 KV 缓存通常不再需要（除非有明确的复用策略），应及时回收；否则并发一多就会挤占显存。

### single_choice · None



- [A] 新一轮输入的 token 前缀与之前完全一致
- [B] 模型参数被重新加载
- [C] batch 大小必须为 1
- [D] 必须关闭注意力机制

**参考答案**：0

**解析**：只有前缀 token 序列一致，历史 KV 才与新计算的前缀对应；若历史被改写或截断，缓存就不再有效。

### single_choice · None



- [A] 分页管理以减少显存碎片
- [B] 量化 KV 到更低精度
- [C] 跨请求共享公共前缀的 KV
- [D] 增大模型词表以压缩缓存

**参考答案**：3

**解析**：词表大小与 KV 缓存无关；分页、量化、前缀共享都是常见优化手段。

### single_choice · None



- [A] 50
- [B] 2000
- [C] 2050
- [D] 100

**参考答案**：2

**解析**：缓存需要覆盖输入 prompt 加上已生成的输出，因此最大约 2000+50=2050 个位置。

### single_choice · None



- [A] 有缓存后每步计算与历史长度无关
- [B] 有缓存后每步仍需与全部历史 key/value 做注意力，只是省去重算 key/value
- [C] 有缓存后注意力变成线性且与长度无关
- [D] 缓存只影响显存不影响计算

**参考答案**：1

**解析**：缓存省去了重复的 key/value 投影与部分计算，但当前 query 仍要与所有历史 key 做点积，单步注意力仍随历史长度增长。

### single_choice · None



- [A] KV 缓存使注意力计算随历史长度增长
- [B] 分词器越来越慢
- [C] 模型权重被修改
- [D] batch 大小自动变为 0

**参考答案**：0

**解析**：解码第 t 步需要与 t 个历史位置做注意力，随输出增长单步耗时上升；不过其增长速度远小于无缓存时的重算。

### single_choice · None



- [A] 缓存只有序列维度，没有 batch 维度
- [B] 每个 batch 中的请求各自拥有独立的 KV 缓存
- [C] 整个 batch 共享同一份 KV 缓存
- [D] batch 维度会被自动平均掉

**参考答案**：1

**解析**：每个序列有自己的历史，因此 KV 缓存按 batch/请求分别存储；不同请求的 KV 不能混用（除非共享前缀且做了专门复用）。

### single_choice · None



- [A] 生成结果会基于错误的历史上下文，质量严重下降
- [B] 完全没有影响，因为 KV 可通用
- [C] 只会影响速度
- [D] 模型会自动纠正

**参考答案**：0

**解析**：KV 与具体前缀强绑定，错配会让注意力看到不相关历史，导致输出错误；这不是速度问题。

### single_choice · None



- [A] 限制最大并发与最大序列长度，或对 KV 做量化/分页
- [B] 直接关闭注意力
- [C] 把 batch 设为极大值
- [D] 把 KV 缓存写入用户浏览器

**参考答案**：0

**解析**：显存受限时通常通过限制并发与长度、量化 KV、分页管理等手段在吞吐与显存间权衡；关闭注意力会破坏模型。

### single_choice · None



- [A] prefill 阶段为整个输入序列计算并写入 KV，decode 阶段逐 token 追加
- [B] prefill 阶段不写 KV，decode 阶段才写
- [C] 两阶段都不需要 KV
- [D] decode 阶段会重写全部历史 KV

**参考答案**：0

**解析**：prefill 一次性为输入 prompt 计算 key/value 并存入缓存；decode 每步只计算新 token 的 key/value 并追加，同时用其 query 读取全部历史。

### single_choice · None



- [A] 模型权重的参数量
- [B] 批大小、序列长度、层数、注意力头数与头维度
- [C] 输入文本的字符数
- [D] 输出 token 的数量

**参考答案**：1

**解析**：KV 缓存大小 ≈ 2 × 层数 × 头数 × 头维 × 序列长度 × 批大小 × 精度字节数。参数量影响的是权重显存，字符数不等于 token 数，输出 token 数只是序列长度的一部分来源。

### single_choice · None



- [A] 只缓存 query
- [B] 缓存 key 和 value，不缓存 query
- [C] 同时缓存 query、key、value
- [D] 只缓存 attention 的输出

**参考答案**：1

**解析**：生成新 token 时只需要新的 query 与历史 key/value 做注意力，历史 query 不再需要，所以只缓存 key 和 value。

### single_choice · None



- [A] 结果完全错误
- [B] 首 token 延迟随对话历史增长而显著增加
- [C] 显存占用降低
- [D] 模型输出会改变语义

**参考答案**：1

**解析**：重复计算历史前缀导致 prefill 阶段开销随对话轮次增长，首 token 延迟上升；结果本身不一定错，显存不会因此降低。

### single_choice · None



- [A] 降低模型精度以加速推理
- [B] 多个请求共享相同前缀时复用已算好的 KV，减少重复 prefill
- [C] 把模型权重放到磁盘
- [D] 对输出做采样加速

**参考答案**：1

**解析**：前缀缓存复用相同系统提示、few-shot 示例等公共前缀的 KV，避免重复 prefill；它不改变精度，也不涉及权重存放或采样。

### single_choice · None



- [A] 不同请求序列长度不同，缓存需要动态分配与回收
- [B] 无法并行计算
- [C] 必须把 batch 大小固定为 1
- [D] 缓存内容会变成只读

**参考答案**：0

**解析**：连续批处理下请求动态进出，序列长度差异大，需要按页或按块动态分配、碎片整理与回收 KV 缓存空间，这是 PagedAttention 等方案要解决的问题。

### single_choice · None



- [A] 显存占用下降，但可能带来一定精度损失
- [B] 显存占用上升
- [C] 序列长度上限自动翻倍且无任何副作用
- [D] 模型权重也会自动量化

**参考答案**：0

**解析**：量化 KV 缓存可减少显存带宽与容量压力，但引入量化误差，可能影响生成质量；权重量化是独立的事。

### single_choice · None



- [A] t 个
- [B] 1 个（当前步的新 token）
- [C] 0 个
- [D] 取决于 batch 大小且恒等于历史长度

**参考答案**：1

**解析**：解码阶段每次只处理一个新 token，因此 query 只有一个（忽略 batch 维度），而 key/value 来自历史缓存加上当前 token。

### single_choice · None



- [A] 并发请求数很小且序列很短
- [B] 长上下文请求且高并发同时进行
- [C] 使用较小的模型
- [D] 只做单条推理且长度固定

**参考答案**：1

**解析**：KV 缓存随序列长度和批大小线性增长，长上下文加高并发会迅速耗尽显存；小并发、短序列、小模型都会减轻压力。

### single_choice · None



- [A] 减少了注意力计算所需的浮点运算次数
- [B] 避免了因序列长度不定而造成的内存碎片与过度预留
- [C] 使模型权重可以被多个请求共享
- [D] 消除了对 GPU 显存的依赖

**参考答案**：1

**解析**：传统做法按最大可能长度预分配连续显存，短序列会浪费、长序列要重分配，产生碎片。分页把 KV 缓存切成固定大小的块并按需分配，显著降低内部/外部碎片和预留浪费。它不减少计算量，模型权重共享是另一回事，也无法摆脱对显存的需求。

### single_choice · None



- [A] 一张块表（block table），保存每个序列的逻辑块对应的物理块编号
- [B] 矩阵乘法得到的注意力分数
- [C] Transformer 的层归一化参数
- [D] 优化器的动量缓冲区

**参考答案**：0

**解析**：分页机制借用操作系统虚拟内存的思想，用块表记录某序列第 i 个逻辑块实际落在哪个物理块上，从而无需连续显存。注意力分数、归一化参数、优化器状态都与该映射无关。

### multi_choice · None



- [A] 显著减少显存碎片和预留浪费
- [B] 支持不同序列的相同前缀共享物理块
- [C] 使序列可以按需增长而不必事先预留最大长度
- [D] 降低注意力计算的浮点运算量
- [E] 完全不需要块表等额外元数据开销

**参考答案**：[0, 1, 2]

**解析**：分页的核心优势是省显存、可共享前缀、按需增长。它并不减少注意力计算量；同时引入了块表等元数据开销，所以「完全不需要元数据」是错的。

### multi_choice · None



- [A] 它把序列的逻辑块映射到物理块编号
- [B] 它允许逻辑上连续的块在物理上不连续
- [C] 它使多个序列可以共享同一物理块
- [D] 它存储了模型的权重参数
- [E] 它取代了注意力分数计算

**参考答案**：[0, 1, 2]

**解析**：块表负责逻辑到物理的映射，允许物理不连续并支持共享。它不存储模型权重，也不能替代注意力分数的计算。

### multi_choice · None



- [A] 块越大，块表条目越少，管理和查表开销越低
- [B] 块越大，序列末尾不满一块时的内部碎片越多
- [C] 块越小，碎片越少但映射开销相对更高
- [D] 块大小对显存和性能没有任何影响
- [E] 块大小必须等于注意力头数

**参考答案**：[0, 1, 2]

**解析**：块大小是性能与碎片的权衡：大块省管理开销但碎片多，小块碎片少但管理开销高。它与显存/性能当然有关，也不要求等于注意力头数。

### multi_choice · None



- [A] 多个用户使用内容相同、很长的系统提示词
- [B] 同一请求在一次对话中携带很长的历史上下文
- [C] 批量推理中大量请求共享相同的少样本示例前缀
- [D] 每个请求的提示词都完全不同且无公共前缀
- [E] 每个请求都只包含一个随机生成的 token

**参考答案**：[0, 1, 2]

**解析**：前缀共享在有公共前缀时获益明显，如共享系统提示词、长上下文复用、共享少样本示例。前缀完全不同的请求，或只有一个 token 的请求，无公共前缀可共享，收益有限。

### multi_choice · None



- [A] 每个序列的块表，指明逻辑块对应的物理块
- [B] 每个序列的有效长度，以确定读取哪些 token 位置
- [C] 块大小
- [D] 优化器的学习率
- [E] 训练数据集的路径

**参考答案**：[0, 1, 2]

**解析**：内核需要块表做间接寻址、需要有效长度来避免读取无效槽位、需要块大小来定位块内偏移。学习率和数据集路径属于训练侧，与推理内核无关。

### fill_blank · None



**参考答案**：["块", "block", "block table", "块表", "页表", "page table"]

**解析**：该结构把逻辑块映射到物理块，借用操作系统页表思想，因此常被称为（逻辑块/物理块）映射表，即块表或页表。

### fill_blank · None



**参考答案**：["写时复制", "copy-on-write", "Copy-on-Write", "cow", "COW"]

**解析**：写时复制（copy-on-write）会在修改前把共享块复制成私有副本，从而保证共享者的数据不被破坏，这是分页注意力实现前缀共享的关键机制。

### fill_blank · None



**参考答案**：["3,15", "3, 15", "3，15"]

**解析**：33 个 token 按每块 16 个切分：16+16+1，共需 3 个块。最后一块用了 1 个槽位，浪费 15 个，即内部碎片。

### code_reading · None



**参考答案**：num_blocks = 3（ceil(40/16)=3）；used_in_last = 8（40%16=8）；最后一块浪费 16-8=8 个槽位。

**解析**：40 个 token 分块：16+16+8，共 3 块，最后一块用了 8 个位置，因此浪费 8 个内部碎片槽位。这体现了分页中最后一块通常不满的特性。

### code_reading · None



**参考答案**：物理块 2 是 seq A 的块，直接写会破坏 seq A 的数据（两个序列本应在写入后分离）。正确做法是采用写时复制：为 seq B 的第 2 个逻辑块分配一个新的物理块，先复制原内容再写入，并把 block_table_B[2] 指向新块。

**解析**：seq A 与 seq B 共享物理块 5 和 9，但物理块 2 属于 seq A。如果 seq B 直接写物理块 2，会污染 seq A 的内容。写时复制保证修改前先私有化。

### single_choice · None



- [A] 块越大，映射开销越低，但内部碎片越多
- [B] 块越小，一定能在所有场景下获得最快速度
- [C] 块大小必须等于模型隐藏层维度
- [D] 块大小必须等于批大小

**参考答案**：0

**解析**：块大小是权衡：块越大，块表条目越少、调度和管理开销越低，但序列末尾不满一块时浪费的内部碎片越多；块越小碎片越少但管理开销上升。它与隐藏层维度、批大小没有强制相等关系。

### scenario · None



**解析**：分页把 KV 缓存切成固定大小的块，按需分配并利用块表做逻辑到物理的映射，避免按最大长度预分配导致的碎片和预留浪费，从而支持更高并发。代价是引入块表等元数据、查表与间接寻址的开销，调度与内存管理更复杂，块大小需要权衡。

### scenario · None



**解析**：正确做法是让不同请求的逻辑块指向同一物理块实现前缀共享，并在需要写入时用写时复制为请求分配私有块，避免互相污染。提议中提到「原地改」会导致一个请求的更新破坏其他请求的 KV，破坏隔离和输出正确性，是危险的。

### scenario · None



**解析**：拷贝成连续缓冲会引入大量额外显存带宽和时间开销，抵消分页节省显存的收益，并且需要额外缓冲区。更合适的做法是让内核通过块表对物理上不连续的块做间接寻址，逐块读取并结合每个序列的有效长度累积注意力结果。

### single_choice · None



- [A] 让两个请求的对应逻辑块指向同一个物理块（写时复制/共享前缀）
- [B] 把两个请求合并成一个序列
- [C] 对其中一个请求关闭注意力计算
- [D] 只缓存其中一个请求的 KV

**参考答案**：0

**解析**：块表允许不同序列的逻辑块映射到相同物理块，因此相同前缀可共享同一份 KV 存储，只在需要写入新内容时复制（写时复制）。合并序列、关闭计算、丢弃缓存都会破坏语义或输出正确性。

### single_choice · None



- [A] 先把所有 KV 拷贝回一段连续显存再计算
- [B] 让内核根据块表间接寻址，逐块读取 KV 并累积注意力结果
- [C] 把批大小固定为 1 逐个处理
- [D] 预先按最长序列长度填充到等长

**参考答案**：1

**解析**：分页注意力的关键就在于注意力内核能通过块表间接访问分散的物理块，边读边累积（如在线 softmax），无需先整理成连续内存。拷贝成连续会抵消分页的收益；固定批大小或等长填充属于另一种思路。

### single_choice · None



- [A] 注意力计算复杂度过高
- [B] 预分配策略导致大量显存被预留却未被真正使用
- [C] 模型参数量太大
- [D] 网络传输带宽不足

**参考答案**：1

**解析**：按最大长度预分配会让绝大部分空间长期闲置，造成严重浪费，这是分页注意力要解决的核心痛点。计算复杂度、参数量、带宽都与「预留却闲置」这一现象没有直接因果关系。

### single_choice · None



- [A] 它通过提高单请求的计算速度来提升吞吐
- [B] 它通过减少显存浪费、支持更多并发请求同时驻留来提升吞吐
- [C] 它通过降低模型精度来提升吞吐
- [D] 它对吞吐量没有任何影响

**参考答案**：1

**解析**：分页注意力的主要收益是显存利用率的提升，从而能同时容纳更多序列（更大的有效批），提高整体吞吐。它不直接加速单个请求的计算，也不改变精度。

### single_choice · None



- [A] 一组键和值向量，对应序列中连续的若干 token
- [B] 模型的某一层
- [C] 一个批次里的全部请求
- [D] 一次梯度更新的单位

**参考答案**：0

**解析**：块是 KV 缓存的分配与映射单位，包含若干连续 token 对应的 key/value 向量。它与网络层、请求批次、优化步无关。

### single_choice · None



- [A] 必须申请 5 个块
- [B] 申请 1 个块即可，最后 11 个位置是内部碎片
- [C] 无法存储，必须把块大小改为 5
- [D] 必须按 16 长度填充输入

**参考答案**：1

**解析**：长度 5 只需一个块即可容纳，块内未用的 11 个槽位是内部碎片。分页允许最后一个块不满，这正是它比按最大长度预分配更省显存的原因。填充输入并非必要。

### single_choice · None



- [A] 直接覆盖共享的物理块，影响其他请求
- [B] 为该请求分配新的物理块并把需要修改的部分复制过去
- [C] 拒绝该请求的写入
- [D] 清空所有请求的 KV 缓存

**参考答案**：1

**解析**：写时复制保证共享块在被修改前先私有化：为新内容分配新块并复制原内容，避免影响其他仍指向旧块的请求。直接覆盖会破坏共享者的数据。
