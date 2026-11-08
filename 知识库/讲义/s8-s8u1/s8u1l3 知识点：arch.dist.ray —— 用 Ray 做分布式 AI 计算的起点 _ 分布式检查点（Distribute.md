# s8u1l3 知识点：arch.dist.ray —— 用 Ray 做分布式 AI 计算的起点 / 分布式检查点（Distributed Checkpoint）：从零到工程实践

> 来源 `content/lessons/s8u1l3.json`

## arch.dist.ray

# 知识点：arch.dist.ray —— 用 Ray 做分布式 AI 计算的起点

> **一句话直觉**：当你的一台机器已经喂不饱模型训练或数据处理时，Ray 让你用几乎不改代码的方式，把同样的 Python 函数分布到多台机器上跑。

---

## 1. 为什么需要 Ray？从单机瓶颈说起

在 AI 工程里，我们经常会遇到三类瓶颈：

1. **算力瓶颈**：一个模型训练要跑 20 小时，单机 GPU 不够。
2. **吞吐瓶颈**：要处理 1 亿张图片，单进程 `for` 循环太慢。
3. **资源异构**：有的任务要 GPU，有的只要 CPU，有的要大量内存。

最原始的分布式（distributed）做法是写 `multiprocessing` 或手动起多台机器跑脚本，但很快就会遇到：任务调度、失败重试、跨机通信、资源分配这些重复造轮子的问题。

**Ray** 是一个通用的分布式计算框架（distributed computing framework），它把这些基础设施封装好，让你继续用 Python 函数和类来写分布式程序。

核心心智模型只有两个：

- **Task（任务）**：把一个普通函数变成可以远程执行的函数。
- **Actor（演员/有状态进程）**：把一个普通类变成可以远程调用的、带状态的进程。

---

## 2. 最小可运行示例：把函数变成远程任务

Ray 的基本用法是：用 `@ray.remote` 装饰一个函数，调用时用 `.remote()`，取结果用 `ray.get()`。

```python
import ray

# 初始化 Ray；本地单机也会启动一个本地集群（local cluster）
ray.init()

@ray.remote
def square(x):
    # 这个函数会在 Ray 的 worker 进程里执行，而不是当前进程
    return x * x

# 提交任务：立即返回一个 ObjectRef（对象引用），不阻塞
futures = [square.remote(i) for i in range(5)]

# 阻塞等待所有结果
results = ray.get(futures)
print(results)  # [0, 1, 4, 9, 16]

ray.shutdown()
```

关键结论：

- `@ray.remote` 把函数注册成远程任务。
- `.remote()` 是异步提交，返回 `ObjectRef`，不是结果本身。
- `ray.get()` 才会真正取值，并把结果从对象存储（object store）拉回本地。

---

## 3. 从任务到 Actor：需要状态时怎么办？

如果每个任务都无状态，那用 Task 就够了。但很多 AI 场景需要**有状态**：比如一个参数服务器（parameter server）、一个环境模拟器、一个加载了大模型的推理服务。

这时用 Actor：`@ray.remote` 装饰一个类，实例化后就是一个常驻的远程进程。

```python
import ray

ray.init()

@ray.remote
class Counter:
    def __init__(self):
        self.value = 0

    def inc(self):
        self.value += 1
        return self.value

# 创建 Actor 实例：会在某个 worker 进程里常驻
c = Counter.remote()

# 连续调用，状态会保留
print(ray.get(c.inc.remote()))  # 1
print(ray.get(c.inc.remote()))  # 2

ray.shutdown()
```

关键结论：

- Actor 方法默认是**串行**执行的，适合维护状态一致性。
- Actor 可以指定资源，例如 `Counter.options(num_gpus=1).remote()`。
- Actor 的生命周期由 Ray 管理，可以通过 `ray.kill()` 或让它被垃圾回收。

---

## 4. 资源与调度：让任务跑到该去的地方

Ray 的调度器（scheduler）会根据资源声明把任务分配到合适的节点。你可以声明任务需要多少 CPU、GPU、内存。

```python
import ray

ray.init()

@ray.remote(num_gpus=1)
def train_step(data):
    # 这里假设内部会用到 GPU
    return sum(data)

# 提交时 Ray 会找一个有空闲 GPU 的节点
futures = [train_step.remote(list(range(10))) for _ in range(4)]
print(ray.get(futures))

ray.shutdown()
```

关键结论：

- `num_gpus=1` 是**逻辑资源**，Ray 会按节点实际 GPU 数量调度。
- 资源不足时任务会排队，而不是直接失败。
- 可以用 `ray.nodes()` 查看集群节点和资源状态。

---

## 5. 从单机到集群：Ray 的扩展路径

本地跑通后，扩展到集群通常只需要改 `ray.init()` 的地址：

```python
# 本地
# ray.init()

# 连接到已有集群（head 节点地址）
# ray.init(address=\"ray://<head-node-ip>:10001\")
```

Ray 集群一般由一个 **head node（头节点）** 和多个 **worker node（工作节点）** 组成。head 负责调度和元数据，worker 负责实际计算。

关键结论：

- 同一份代码，本地和集群可以复用。
- 生产环境常用 Ray Cluster Launcher 或 KubeRay 在 Kubernetes 上部署。
- Ray 生态里还有 Ray Train、Ray Tune、Ray Serve、Ray Data，分别解决训练、调参、推理服务、数据处理。

---

## 6. 一句话总结

Ray 用 `@ray.remote` 把普通 Python 函数和类变成分布式任务与 Actor，让你在单机和集群之间平滑迁移，是分布式 AI 工程的起点。

---

## 动手练习

**任务**：在本机安装 Ray，写一个脚本，完成以下要求：

1. 用 `@ray.remote` 定义一个函数 `fib(n)`，返回第 n 个斐波那契数。
2. 并发提交 `fib(30)`、`fib(31)`、`fib(32)` 三个任务。
3. 用 `ray.get()` 收集结果并打印。
4. 再用 `@ray.remote` 定义一个 Actor `Accumulator`，提供 `add(x)` 方法累加值，并打印连续三次调用后的累计结果。

**提交物**：一个 `.py` 文件 + 运行输出截图或文本。

**提示**：如果本机没有 GPU，练习中不需要声明 `num_gpus`。


## arch.dist.checkpoint

# 分布式检查点（Distributed Checkpoint）：从零到工程实践

## 一句话直觉

在分布式训练（Distributed Training）中，模型和数据被拆到多张 GPU 上；**分布式检查点（Distributed Checkpoint）** 就是：在训练过程中，把“分散在各卡上的状态”安全、完整、可恢复地保存下来——像给整个训练过程拍一张“全局快照”。

为什么必须学它？因为真实训练中停电、抢占、OOM（Out of Memory）、机器故障都会发生。没有可靠的 checkpoint，你可能会丢掉几天甚至几周的算力。

---

## 1. 什么是检查点（Checkpoint）？

**检查点（Checkpoint）** 是训练过程中的“存档点”：把当前模型参数、优化器状态、学习率调度器状态、训练步数等信息保存到磁盘，以便之后恢复（Resume）。

在单卡训练里，这很简单：

```python
# 单卡：保存和恢复非常简单
import torch

model = torch.nn.Linear(10, 2)
optimizer = torch.optim.SGD(model.parameters(), lr=0.1)

# 保存
ckpt = {
    "model": model.state_dict(),
    "optimizer": optimizer.state_dict(),
    "step": 100,
}
torch.save(ckpt, "single.pt")

# 恢复
ckpt = torch.load("single.pt")
model.load_state_dict(ckpt["model"])
optimizer.load_state_dict(ckpt["optimizer"])
start_step = ckpt["step"]
```

> 关键结论：Checkpoint 不只是“模型权重”，还包括**优化器状态**和**训练进度**。少了任何一项，恢复后训练行为都会变。

---

## 2. 分布式训练为什么让 Checkpoint 变难？

分布式训练常见三种并行：

- **数据并行（Data Parallel, DP）**：每张卡有一份完整模型副本，但梯度不同。
- **张量并行（Tensor Parallel, TP）**：同一层的权重被切到不同卡上。
- **流水线并行（Pipeline Parallel, PP）**：不同层放在不同卡上。

当使用 TP/PP 时，**每张卡只持有模型的一部分**。如果只保存 rank0 的状态，恢复时模型就不完整。

用一个最小例子感受“分片（Sharding）”：

```python
# 模拟：一个权重矩阵被切到 2 张卡上
import torch

full = torch.arange(12).reshape(4, 3)
# 按行切分到 2 个 rank
rank0 = full[:2]
rank1 = full[2:]

print("rank0:", rank0.tolist())
print("rank1:", rank1.tolist())

# 恢复时必须把两个 rank 的分片拼回去
restored = torch.cat([rank0, rank1], dim=0)
assert torch.equal(restored, full)
```

> 关键结论：分布式 Checkpoint 的核心问题是 **分片状态如何被正确收集、命名、写入和重组**。

---

## 3. 两种主流策略：汇总保存 vs 分片保存

### 3.1 汇总保存（Gather then Save）

所有 rank 把张量发给 rank0，由 rank0 写一个完整文件。

**优点**：格式简单，恢复容易。  
**缺点**：rank0 内存/带宽成为瓶颈，大规模下容易 OOM。

```python
# 用 torch.distributed 模拟：把各 rank 的分片汇总到 rank0
import os
import torch
import torch.distributed as dist

# 说明：需用 torchrun 启动，例如
# torchrun --nproc_per_node=2 gather_save.py
dist.init_process_group("gloo")
rank = dist.get_rank()
world_size = dist.get_world_size()

# 每个 rank 本地有一个分片
local_shard = torch.full((2, 3), float(rank))

# 收集所有 rank 的分片
if rank == 0:
    gathered = [torch.empty_like(local_shard) for _ in range(world_size)]
else:
    gathered = None

dist.gather(local_shard, gather_list=gathered, dst=0)

if rank == 0:
    full = torch.cat(gathered, dim=0)
    torch.save({"weight": full}, "gathered.pt")
    print("saved on rank0:", full.tolist())

dist.destroy_process_group()
```

### 3.2 分片保存（Sharded Save）

每个 rank 只写自己的分片，并附一个元数据（Metadata）文件描述如何重组。

**优点**：可扩展，避免单点瓶颈。  
**缺点**：恢复时要按元数据加载并拼接。

```python
# 分片保存：每个 rank 写自己的文件 + 一个 metadata
import os
import torch
import torch.distributed as dist

dist.init_process_group("gloo")
rank = dist.get_rank()
world_size = dist.get_world_size()

local_shard = torch.full((2, 3), float(rank))
os.makedirs("sharded_ckpt", exist_ok=True)

torch.save(local_shard, f"sharded_ckpt/rank{rank}.pt")

if rank == 0:
    meta = {"world_size": world_size, "shape": [2 * world_size, 3], "dtype": "float32"}
    torch.save(meta, "sharded_ckpt/meta.pt")

dist.barrier()

# 恢复：每个 rank 读取自己的分片
loaded = torch.load(f"sharded_ckpt/rank{rank}.pt")
print(f"rank{rank} loaded:", loaded.tolist())

dist.destroy_process_group()
```

> 关键结论：**大规模训练优先用分片保存**；小规模或调试阶段可以用汇总保存。

---

## 4. 工程中最常用的方案：PyTorch DCP

PyTorch 提供了 **分布式检查点（Distributed Checkpoint, DCP）**，即 `torch.distributed.checkpoint`，专门解决分片保存与恢复。

核心 API：

- `save(state_dict, checkpoint_id)`：保存
- `load(state_dict, checkpoint_id)`：恢复
- `StateDictOptions`：控制是否展平、是否只 rank0 加载等

```python
# PyTorch DCP 最小示例（需分布式环境，如 torchrun --nproc_per_node=2 dcp_demo.py）
import torch
import torch.distributed as dist
import torch.distributed.checkpoint as dcp
from torch.distributed.checkpoint.state_dict import get_state_dict, set_state_dict

model = torch.nn.Linear(4, 2)
optim = torch.optim.Adam(model.parameters())

dist.init_process_group("gloo")

# 1) 收集模型和优化器的 state_dict（DCP 友好）
model_sd, optim_sd = get_state_dict(model, optim)
state = {"model": model_sd, "optim": optim_sd}

# 2) 保存到目录（每个 rank 写自己的分片）
dcp.save(state, checkpoint_id="dcp_ckpt")

# 3) 恢复：先构造同样结构的空 state_dict
model_sd2, optim_sd2 = get_state_dict(model, optim)
state2 = {"model": model_sd2, "optim": optim_sd2}
dcp.load(state2, checkpoint_id="dcp_ckpt")

# 4) 把加载后的 state 写回模型和优化器
set_state_dict(model, optim, model_sd2, optim_sd2)
print(f"rank{dist.get_rank()} loaded ok")

dist.destroy_process_group()
```

> 关键结论：DCP 把“分片、元数据、重组”都封装好了，是当前 PyTorch 工程中的首选。

---

## 5. 工程级注意事项

1. **异步保存（Async Save）**：保存大模型可能阻塞训练。可以用后台线程或 DCP 的异步能力。
2. **原子性（Atomicity）**：先写临时目录，再重命名，避免半写状态被当成有效 checkpoint。
3. **版本兼容**：记录 PyTorch 版本、并行策略、词表大小等元数据。
4. **保留策略**：只保留最近 N 个 + 最佳 N 个，避免磁盘爆满。
5. **恢复一致性**：数据加载器的随机种子、采样进度也要一起保存。

> 关键结论：Checkpoint 的目标不是“存下来”，而是“**任何时刻都能正确恢复并继续训练**”。

---

## 动手练习

**任务**：用 `torchrun` 在 2 个进程上模拟一个分布式训练的分片保存与恢复。

要求：

1. 每个 rank 创建一个形状为 `(2, 3)` 的张量，内容为 `rank` 的值。
2. 用“分片保存”写到 `./my_ckpt/rank{N}.pt`，并在 rank0 写 `meta.pt`。
3. 再写一个 `load` 脚本，读取各 rank 分片并 `torch.cat` 成完整张量。
4. 验证完整张量等于逐行拼接的期望结果。

运行命令示例：

```bash
torchrun --nproc_per_node=2 save_shards.py
torchrun --nproc_per_node=2 load_shards.py
```

进阶：把上面的例子改写成 `torch.distributed.checkpoint` 版本，对比代码量与可扩展性。


---

## 本课题目

### single_choice · None



- [A] 直接调用该函数，Ray 会自动将其分发到集群节点
- [B] 用 @ray.remote 装饰该函数，然后通过 .remote() 调用
- [C] 将函数放入 multiprocessing.Pool 中执行
- [D] 使用 threading.Thread 启动该函数

**参考答案**：1

**解析**：Ray 通过 @ray.remote 装饰器将普通函数转换为远程函数，调用时使用 .remote() 提交任务，由 Ray 调度到集群节点执行。直接调用不会分发；multiprocessing 和 threading 是单机并发方案，不涉及 Ray 的分布式调度。

### single_choice · None



- [A] 整数 3
- [B] 一个 ObjectRef 对象，需要通过 ray.get() 获取实际结果
- [C] None
- [D] 一个 Future 对象，可以直接用 await 获取结果

**参考答案**：1

**解析**：调用 .remote() 会立即返回一个 ObjectRef（对象引用），任务在后台异步执行。要获得实际返回值，必须使用 ray.get(result)。直接 print 只会显示 ObjectRef 的表示。

### single_choice · None



- [A] @ray.remote(num_cpus=2, num_gpus=1)
- [B] @ray.remote(cpus=2, gpus=1)
- [C] @ray.resource(cpu=2, gpu=1)
- [D] 在函数内调用 ray.request(cpu=2, gpu=1)

**参考答案**：0

**解析**：Ray 使用 @ray.remote(num_cpus=..., num_gpus=...) 来声明资源需求。参数名是 num_cpus 和 num_gpus，不是 cpus/gpus，也没有 ray.request 这样的函数。

### single_choice · None



- [A] [0, 1, 4, 9]
- [B] [1, 4, 9, 16]
- [C] [0, 1, 2, 3]
- [D] [0, 2, 4, 6]

**参考答案**：0

**解析**：square(i) 计算 i 的平方，i 从 0 到 3，结果为 [0,1,4,9]。ray.get 接受一个 ObjectRef 列表，按顺序返回结果列表。

### single_choice · None



- [A] ray.get() 是非阻塞的，立即返回
- [B] ray.get() 会阻塞直到所有请求的对象就绪，然后返回
- [C] ray.get() 会阻塞直到超时，超时后返回 None
- [D] ray.get() 只能获取一个对象，不能传入列表

**参考答案**：1

**解析**：ray.get 是阻塞调用，会等待直到传入的所有 ObjectRef 对应的对象都就绪，然后返回结果（单个值或列表）。它会一直等待，除非指定 timeout 参数。它也可以接受 ObjectRef 列表。

### single_choice · None



- [A] 将 ObjectRef 作为参数传递给另一个远程函数
- [B] 在远程函数内部对传入的 ObjectRef 再次调用 ray.get
- [C] 使用 ray.get 获取最终结果
- [D] 将多个 ObjectRef 放入列表一次性 ray.get

**参考答案**：1

**解析**：在远程函数内部对传入的 ObjectRef 再次调用 ray.get 通常不必要，而且可能因为对象不在本地而阻塞或引发问题。Ray 会自动解析作为参数传入的 ObjectRef。其他选项都是推荐做法。

### single_choice · None



- [A] 放置组用于将多个任务或 actor 按指定策略（如打包或分散）调度到同一组节点上
- [B] 放置组用于对任务结果进行分组排序
- [C] 放置组只能包含 actor，不能包含任务
- [D] 放置组是一种序列化机制

**参考答案**：0

**解析**：放置组是 Ray 中用于原子性预留资源并按照指定策略（PACK、SPREAD、STRICT_PACK 等）调度任务和 actor 的机制，常用于需要协同调度的场景。它不负责结果排序或序列化，且可以包含任务和 actor。

### single_choice · None



- [A] 输出 3
- [B] 输出 0
- [C] 抛出 TypeError，因为 ObjectRef 不支持 len()
- [D] 输出 ObjectRef 的长度

**参考答案**：2

**解析**：ObjectRef 不是实际的列表，不支持 len() 操作。要获取列表长度，需要先 ray.get(ref) 得到实际列表。直接调用 len 会抛出 TypeError。

### single_choice · None



- [A] 调用 ray.shutdown()
- [B] 调用 ray.stop()
- [C] 直接退出 Python 解释器即可，无需任何操作
- [D] 调用 ray.disconnect()

**参考答案**：0

**解析**：ray.shutdown() 用于断开当前进程与 Ray 集群的连接并释放相关资源。ray.stop() 和 ray.disconnect() 不是标准 API。虽然进程退出通常也会清理，但显式 shutdown 是推荐做法。

### single_choice · None



- [A] 同一个 actor 的方法调用默认按提交顺序串行执行
- [B] 同一个 actor 的方法调用默认并行执行
- [C] 必须显式加锁才能保证顺序
- [D] actor 方法调用没有顺序保证

**参考答案**：0

**解析**：Ray actor 的每个方法调用默认在同一个 actor 进程内按提交顺序串行执行，这保证了状态一致性。如果需要并发，可以使用 async actor 或 max_concurrency 参数。

### single_choice · None



- [A] 分布式模型训练
- [B] 大规模数据预处理
- [C] 强化学习中的并行环境采样
- [D] 替代 Python 的 GIL 实现单线程加速

**参考答案**：3

**解析**：Ray 用于分布式计算，可以跨进程和节点并行，但它不是用来替代 GIL 或实现单线程加速的工具。分布式训练、数据预处理、强化学习采样都是 Ray 的典型场景。

### single_choice · None



- [A] 等待所有 ObjectRef 就绪后返回
- [B] 等待部分 ObjectRef 就绪后返回，可指定 num_returns
- [C] 等待集群启动
- [D] 等待网络连接

**参考答案**：1

**解析**：ray.wait(refs, num_returns=n) 会等待直到有 n 个对象就绪，然后返回 (ready_refs, remaining_refs)。它允许部分等待，适合流式处理。ray.get 则是等待所有。

### single_choice · None



- [A] result.value()
- [B] result.get()
- [C] ray.get(result)
- [D] result.await()

**参考答案**：2

**解析**：Ray 使用 ray.get(object_ref) 来获取远程任务的结果。ObjectRef 本身没有 .value()、.get() 或 .await() 方法用于获取值（虽然某些版本可能有兼容接口，但标准方式是 ray.get）。

### single_choice · None



- [A] Actor 是用 @ray.remote 装饰的类，其实例在集群中作为有状态的进程运行
- [B] Actor 只能用于无状态计算，不能保存成员变量
- [C] Actor 的每个方法调用都会创建一个新的进程
- [D] Actor 不能跨节点调度，只能在本地运行

**参考答案**：0

**解析**：Ray actor 是通过 @ray.remote 装饰的类，实例化后会在集群中某个节点上启动一个长期运行的进程，可以维护内部状态。方法调用通过 .remote() 提交，按顺序执行。Actor 可以有状态，也可以跨节点调度。

### single_choice · None



- [A] 0 0
- [B] 1 1
- [C] 1 2
- [D] 2 1

**参考答案**：2

**解析**：Actor 方法调用在同一个 actor 实例上按提交顺序串行执行，且共享状态。第一次 inc 后 n 变为 1，第二次变为 2，因此输出 1 2。每个调用不会重新初始化。

### single_choice · None



- [A] 启动本地 Ray 运行时并连接到集群（或创建本地集群）
- [B] 初始化一个 Python 虚拟环境
- [C] 安装 Ray 的依赖包
- [D] 编译 Ray 的 C++ 核心

**参考答案**：0

**解析**：ray.init() 用于启动 Ray 运行时。如果不指定地址，会在本地启动一个 Ray 集群；如果指定 address，则连接到已有集群。它不负责安装依赖、创建虚拟环境或编译代码。

### single_choice · None



- [A] 对一批图片进行无状态的预处理
- [B] 训练一个需要维护优化器状态的模型，并在多轮迭代中更新参数
- [C] 计算两个数的和
- [D] 读取一个静态配置文件

**参考答案**：1

**解析**：Actor 适合需要维护内部状态、跨多次调用累积或更新状态的场景，例如参数服务器、模型训练中的优化器状态。无状态的一次性计算更适合普通远程函数。

### single_choice · None



- [A] 一个指向远程对象存储中对象的引用，可用于获取结果或作为参数传递
- [B] 一个 Python 原生对象，可以直接修改其值
- [C] 一个线程锁对象
- [D] 一个文件描述符

**参考答案**：0

**解析**：ObjectRef 是 Ray 中指向分布式对象存储中对象的引用。它不能直接当作普通值使用，必须通过 ray.get 获取实际对象，但可以作为参数传递给其他远程任务，Ray 会自动解析依赖。

### single_choice · None



- [A] 报错，远程函数不能接受 ObjectRef 参数
- [B] 自动将 ObjectRef 解析为实际值后再执行
- [C] 将 ObjectRef 原样传入，函数内部需要手动调用 ray.get
- [D] 忽略该参数

**参考答案**：1

**解析**：Ray 会自动解析作为参数传入的 ObjectRef，远程函数接收到的是实际值。这使得任务依赖可以自动构建 DAG，无需手动 ray.get。手动 ray.get 会阻塞，不推荐在远程函数内对参数使用。

### single_choice · None



- [A] Ray 总是将任务调度到提交任务的本地节点
- [B] Ray 根据资源需求和集群状态将任务调度到合适的节点
- [C] Ray 只能调度到有 GPU 的节点
- [D] Ray 不支持异构集群

**参考答案**：1

**解析**：Ray 的调度器会根据任务声明的资源需求（CPU、GPU、内存等）和集群各节点的可用资源，将任务调度到合适的节点。它支持异构集群和本地节点优先等策略，并非只能在本地或 GPU 节点运行。

### single_choice · None



- [A] 检查点用于记录模型每一层的计算公式，便于调试前向传播
- [B] 检查点把运行中的状态定期持久化到可靠存储，故障后可从最近状态恢复，避免从头重算
- [C] 检查点只能保存模型的超参数，不能保存权重
- [D] 检查点是为了在训练时加速反向传播而设计的缓存机制

**参考答案**：1

**解析**：检查点的本质是把易失的运行状态（如模型参数、优化器状态、当前步数等）周期性写入持久存储，使任务在中断后能从最近一次保存点续跑。它不记录公式、不只是超参数、也不等同于反向传播的激活缓存。

### single_choice · None



- [A] 保存间隔太短，导致文件太多
- [B] 保存没有采用「先写临时文件再原子替换」的方式，中断后留下的是不完整的半成品文件
- [C] 检查点文件必须保存在本地磁盘，不能放共享存储
- [D] 加载时需要同时加载所有历史检查点

**参考答案**：1

**解析**：如果在写入目标文件的过程中被中断，目标文件会处于截断或未写完的状态。常见做法是写入临时文件并 fsync，再原子地 rename 到最终路径，从而保证检查点要么完整要么不存在。保存间隔与文件数量、加载全部历史检查点都不是这里的根因。

### multi_choice · None



- [A] 模型参数（权重与偏置）
- [B] 优化器状态（如动量等）
- [C] 当前训练进度（步数 / epoch）
- [D] 数据集的原始文件本身
- [E] 学习率调度器的状态

**参考答案**：[0, 1, 2, 4]

**解析**：完整续训通常需要模型参数、优化器状态、训练进度以及学习率调度器状态。数据集原始文件不属于运行状态，不会被打包进检查点。

### multi_choice · None



- [A] 保存间隔要权衡「重算损失」与「保存开销」
- [B] 采用原子写入（先写临时文件再替换）以避免半成品文件
- [C] 把检查点写到多个副本或可靠存储以提高可用性
- [D] 保存间隔越短越好，完全不考虑 I/O 开销
- [E] 保留一定数量的历史检查点以便回退

**参考答案**：[0, 1, 2, 4]

**解析**：合理的策略要平衡重算与保存开销、保证写入原子性、提高存储可靠性并保留历史点。间隔越短越好的说法忽略了频繁写带来的 I/O 和存储压力，可能反而拖慢训练。

### multi_choice · None



- [A] 应确保所有进程加载到的是同一次保存的状态版本
- [B] 如果部分进程加载旧版本、部分加载新版本，训练可能不正确
- [C] 加载后通常需要一次同步，确保所有进程就绪后再继续
- [D] 各进程可以随意加载不同的检查点文件而不影响结果

**参考答案**：[0, 1, 2]

**解析**：分布式训练要求各进程基于同一份一致的全局状态继续，否则会出现参数/进度不一致。加载后同步可确保所有进程就绪。允许各进程加载不同检查点会破坏一致性。

### fill_blank · None



**参考答案**：["临时", "temp", "临时文件", "temporary"]

**解析**：先写临时文件、再原子 rename，可保证目标路径上的检查点要么是旧的完整版本，要么是新的完整版本，不会出现半写状态。

### fill_blank · None



**参考答案**：["主", "rank 0", "rank0", "0", "主进程", "zero"]

**解析**：常见模式是 rank 0（主进程）统一写出，其他进程等待并在写完后同步，从而避免并发写冲突。

### fill_blank · None



**参考答案**：["优化器", "optimizer", "优化器状态"]

**解析**：优化器为每个参数维护动量等状态，若不同时保存，恢复后更新规则会与原来不同，导致轨迹不连续。

### code_reading · None



**参考答案**：通过先写临时文件再原子 rename，保证 final_path 上要么是旧的完整检查点、要么是新的完整检查点，不会因中断而留下被截断的半成品文件；直接写 final_path 在中断时会留下不完整文件。

**解析**：rename 在同一文件系统内通常是原子的，因此能提供「全有或全无」的语义，这是检查点健壮性的关键。

### code_reading · None



**参考答案**：最近保存发生在第 200 步；恢复后通常从第 200 步（或其后一步）继续，第 201~250 步的工作需要重算。

**解析**：在 step 为 100 的整数倍时保存，因此崩溃前最后保存点是 200。250 与 200 之间的进度未持久化，恢复时需重算这段。

### scenario · None



**解析**：要点包括：按合适间隔定期保存检查点，使故障后从最近点恢复、只重算少量进度；采用原子写入避免半成品文件；保存到可靠存储；保留若干历史点以便回退。这些做法共同把「故障损失」限制在一个保存间隔内。

### scenario · None



**解析**：只恢复权重会丢失优化器动量、学习率调度进度、已完成步数以及随机数生成器状态，导致更新规则与数据顺序改变，从而出现不连续。应将优化器状态、调度器状态、训练进度和相关 RNG 状态一并纳入检查点，并确保各进程加载一致版本。

### single_choice · None



- [A] 应该由各进程同时写同一个文件，写入更快
- [B] 通常只需由一个进程（如 rank 0）负责写出完整检查点，再通过同步机制让其他进程等待，避免写冲突和内容交错
- [C] 每个进程必须写自己的文件，且加载时必须手动拼接
- [D] 多进程写入同一文件时操作系统会自动加锁，无需任何协调

**参考答案**：1

**解析**：并发写同一文件会导致内容交错或损坏。分布式训练的常见模式是由主进程统一汇总/写出检查点，其他进程在写完后同步。多进程写同一文件并不会自动获得正确性保证。

### single_choice · None



- [A] 从零重训一定比从检查点恢复更快
- [B] 从检查点恢复能利用已持久化的状态，通常显著快于从零重训，但前提是检查点完整且可用
- [C] 检查点恢复与从零重训耗时完全相同
- [D] 只要保存了检查点就一定能恢复到崩溃时的精确状态，没有任何重算

**参考答案**：1

**解析**：恢复比从零重训快，是因为它跳过了已持久化的进度。但并不保证精确到崩溃瞬间，通常要重算最近一个保存间隔内的工作。因此「完整且可用」是前提，且会有少量重算。

### single_choice · None



- [A] 只需要保存模型权重即可完全恢复
- [B] 优化器状态（如动量）以及当前已完成的步数 / epoch
- [C] 只需要保存当前 epoch 数
- [D] 只需要保存学习率的值

**参考答案**：1

**解析**：只恢复模型权重会造成优化器动量、学习率调度进度、已完成步数等丢失，导致轨迹不连续。要精确续跑，需要一并保存优化器状态和训练进度信息。仅保存权重并非「完全恢复」。

### single_choice · None



- [A] 检查点文件永远只包含模型权重，因此大小固定
- [B] 若检查点同时包含模型权重和优化器状态，通常其大小会明显大于仅含权重的检查点
- [C] 检查点大小与优化器类型无关
- [D] 检查点大小只取决于数据集大小

**参考答案**：1

**解析**：优化器状态（例如带一阶/二阶动量的优化器）通常为每个参数额外保存若干份张量，因此含优化器状态的检查点往往比只含权重的检查点大几倍。检查点大小与数据集大小无直接关系。

### single_choice · None



- [A] 系统会自动从头开始训练，没有任何损失
- [B] 由于没有更早的可用检查点，任务可能不得不从头重算，损失大量已完成的工作
- [C] 损坏的检查点会被自动修复
- [D] 训练框架会忽略损坏并继续使用部分状态

**参考答案**：1

**解析**：仅保留单个检查点意味着没有回退选项，一旦它损坏就只能从头开始。通常会保留若干个历史检查点（滚动或定期归档），以便在最近一个不可用时回退到更早的可用点。

### single_choice · None



- [A] 把检查点间隔设得越长越好
- [B] 把检查点保存到读写延迟低的可靠存储，并合理设置较短但不过于频繁的保存间隔
- [C] 只在训练全部结束后保存一次
- [D] 把检查点保存在每个节点的本地内存中

**参考答案**：1

**解析**：恢复时间 = 加载最近检查点的时间 + 从该点到故障点的重算时间。保存到快速可靠存储可缩短加载时间，合适的间隔可减少重算量。保存过稀会增加重算量，只在结束时保存则等于没有检查点，保存在内存中在进程崩溃后会丢失。

### single_choice · None



- [A] 保存和加载都必须由所有 rank 各写各的完整副本，互不通信
- [B] 常见做法是保存时由主 rank 写出，加载时由主 rank 读取后再分发给其他 rank，配合集合通信同步
- [C] 加载只能由最后一个 rank 执行
- [D] 保存与加载都不需要任何同步

**参考答案**：1

**解析**：为避免写冲突并保证一致性，通常由主 rank 负责持久化与读取，之后通过广播等集合通信把状态分发给其余进程。各 rank 独立写完整副本会造成写冲突且浪费空间，也不需要特定「最后一个 rank」来加载。

### single_choice · None



- [A] 可以完全不做任何同步
- [B] 把写文件的压力分散到多个进程/存储目标，减少单点写瓶颈，但加载时需要正确地把分片重新组装
- [C] 使检查点文件不再需要版本管理
- [D] 可以省略优化器状态

**参考答案**：1

**解析**：分片保存把大检查点的写入负载分摊到多个进程和/或多个文件，缓解单点写入瓶颈。代价是加载时需按元数据把各分片正确重组，仍然需要同步与一致性保障，且不改变是否需要保存优化器状态。

### single_choice · None



- [A] 随机种子无需保存，因为每次运行结果都一样
- [B] 如果希望恢复后数据打乱、dropout 等随机行为与原来一致，通常应把相关随机数生成器的状态一并纳入检查点
- [C] 只要保存模型权重，随机性就一定可复现
- [D] 随机种子只在推理时需要保存

**参考答案**：1

**解析**：训练中存在数据打乱、dropout 等随机过程。若只恢复权重而不恢复随机数生成器状态，后续的随机序列会不同，导致难以精确复现。因此常把相关 RNG 状态纳入检查点。
