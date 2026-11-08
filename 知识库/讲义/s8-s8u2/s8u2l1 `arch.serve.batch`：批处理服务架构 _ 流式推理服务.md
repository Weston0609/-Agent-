# s8u2l1 `arch.serve.batch`：批处理服务架构 / 流式推理服务

> 来源 `content/lessons/s8u2l1.json`

## arch.serve.batch

# `arch.serve.batch`：批处理服务架构

## 一句话直觉

当你要让 AI 模型对外提供服务时，一次性只处理一个请求会浪费 GPU、吞吐量低、成本高；**批处理（batching）** 就是把多个请求攒在一起送给模型，用一次前向计算服务多个用户。

---

## 第 1 节：为什么需要批处理？

假设你有一个深度神经网络（Deep Neural Network, DNN），每次只处理一张图片。GPU 计算单元大部分时间在等待数据搬运，利用率极低。

如果把 32 张图片堆成一个张量（Tensor）— 形状 `(32, 3, 224, 224)` — 送进模型，GPU 可以在同一时间做并行运算，吞吐量（throughput）能提升几十倍，而单次延迟（latency）增加有限。

这就是服务端批处理的核心动机：**用延迟换吞吐**，但延迟增加远小于批量大小的增长。

```python
import torch
import time

model = torch.nn.Sequential(
    torch.nn.Linear(512, 512),
    torch.nn.ReLU(),
    torch.nn.Linear(512, 10),
).cuda().eval()

# 逐个推理 vs 批量推理
x_single = torch.randn(1, 512).cuda()
x_batch = torch.randn(64, 512).cuda()

with torch.no_grad():
    # 单条推理 100 次
    t0 = time.time()
    for _ in range(100):
        model(x_single)
    t_single = time.time() - t0

    # 批量推理一次
    t0 = time.time()
    model(x_batch)
    t_batch = time.time() - t0

print(f"100 次单条: {t_single:.4f}s, 单条平均 {t_single/100*1000:.2f}ms")
print(f"1 次批量 64: {t_batch:.4f}s, 单条平均 {t_batch/64*1000:.2f}ms")
```

> 关键结论：批量推理在 GPU 上通常能把单条平均耗时降低一个数量级。

---

## 第 2 节：静态批处理 vs 动态批处理

**静态批处理（static batching）**：训练时预先确定 batch size，比如固定 32。简单，但服务线上请求到达时间不均匀时，会造成等待或空转。

**动态批处理（dynamic batching）**：服务端把短时间窗口内到达的请求攒起来，达到 `max_batch_size` 或超时 `max_wait_ms` 就立刻推理。这是 Triton、TorchServe、vLLM 等推理框架的默认策略。

核心参数：
- `max_batch_size`：单批最多几条
- `max_wait_ms`：最多等多久，避免小流量时延迟爆炸
- `timeout`：整体请求超时

```python
import asyncio
import torch

class DynamicBatcher:
    """极简动态批处理：攒到 max_batch_size 或超过 max_wait_ms 就推理"""
    def __init__(self, model, max_batch_size=8, max_wait_ms=50):
        self.model = model
        self.max_batch_size = max_batch_size
        self.max_wait_ms = max_wait_ms
        self.queue: list[tuple[torch.Tensor, asyncio.Future]] = []
        self.lock = asyncio.Lock()

    async def infer(self, x: torch.Tensor):
        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        async with self.lock:
            self.queue.append((x, fut))
            if len(self.queue) >= self.max_batch_size:
                await self._flush()
            else:
                # 启动一个超时任务，避免无限等待
                loop.call_later(self.max_wait_ms / 1000, lambda: asyncio.create_task(self._maybe_flush()))
        return await fut

    async def _maybe_flush(self):
        async with self.lock:
            if self.queue:
                await self._flush()

    async def _flush(self):
        batch = self.queue
        self.queue = []
        x = torch.cat([b[0] for b in batch], dim=0)
        with torch.no_grad():
            y = self.model(x)
        for i, (_, fut) in enumerate(batch):
            fut.set_result(y[i:i+1])
```

> 关键结论：动态批处理的关键是「要么攒满、要么等超时」，两个阈值共同决定延迟与吞吐的平衡。

---

## 第 3 节：连续批处理（Continuous Batching）

对于大语言模型（LLM）这种每条请求生成长度不一的场景，静态 batch 会导致「短请求等长请求」的浪费。

**连续批处理（continuous batching）**：不再等整批都做完，而是每一轮 decode step 完成后，把已经结束的序列踢出，把排队中的新序列插进来。GPU 每步都跑满。

这是 vLLM、TensorRT-LLM、SGLang 的核心优化之一。

```python
# 伪代码：连续批处理的调度思想
# 每一轮 decode step：
#   1. 移除已生成 <EOS> 的序列
#   2. 从等待队列补充新序列填满 max_batch_size
#   3. 对当前活跃序列做一次 forward
active = []          # 正在生成的序列
waiting = [...]      # 排队中的请求

while active or waiting:
    active = [s for s in active if not s.finished]      # 踢掉完成的
    while len(active) < max_batch_size and waiting:
        active.append(waiting.pop(0))                    # 补新的
    outputs = model.decode_step(active)                  # 一次 forward
    for s, o in zip(active, outputs):
        s.append_token(o)
```

> 关键结论：连续批处理让「已完成的请求立刻让位」，显著提高 GPU 占用率并降低平均延迟。

---

## 第 4 节：工程化落地要点

真实服务里，批处理不只是 `torch.cat`，还需要考虑：

1. **不同输入形状**：文本长度不一，需 padding（填充）到同一长度，配合 attention mask。
2. **优先级**：高优请求可以抢占，或进入小 batch 快速返回。
3. **背压（backpressure）**：队列过长时拒绝新请求（返回 429），避免雪崩。
4. **超时**：每个请求单独计时，超时就返回错误。
5. **可观测性**：记录 batch size 分布、排队时延、推理时延。

```python
import asyncio
from collections import deque

class BatchingServer:
    def __init__(self, model, max_batch=16, max_wait=0.05, max_queue=256):
        self.model = model
        self.max_batch = max_batch
        self.max_wait = max_wait
        self.max_queue = max_queue
        self.q = deque()

    async def handle(self, x):
        if len(self.q) >= self.max_queue:          # 背压
            raise RuntimeError("server overloaded (429)")
        fut = asyncio.get_running_loop().create_future()
        self.q.append((x, fut))
        asyncio.create_task(self._drain())
        return await asyncio.wait_for(fut, timeout=10.0)   # 整体超时

    async def _drain(self):
        await asyncio.sleep(self.max_wait)         # 攒一小会儿
        batch = []
        while self.q and len(batch) < self.max_batch:
            batch.append(self.q.popleft())
        if not batch:
            return
        xs = torch.cat([b[0] for b in batch], dim=0)
        with torch.no_grad():
            ys = self.model(xs)
        for i, (_, fut) in enumerate(batch):
            if not fut.done():
                fut.set_result(ys[i:i+1])
```

> 关键结论：批处理服务的鲁棒性来自「队列 + 批大小 + 超时 + 背压」四件套。

---

## 第 5 节：什么时候不该批处理

- **极致低延迟场景**：如实时语音唤醒、高频交易，宁可单条也不等。
- **超大批次会 OOM**：需动态调整 max_batch_size，或做 micro-batching（微批）。
- **输入不可张量化**：如需要复杂的自定义 Python 逻辑，难以批量。

**微批（micro-batching）**：把一个大 batch 拆成多个小 batch 依次跑，用时间换取显存，是显存受限时的常用手段。

```python
# 微批：大 batch 拆小，缓解显存
BIG = 256
MICRO = 32
x = torch.randn(BIG, 512).cuda()
outs = []
with torch.no_grad():
    for i in range(0, BIG, MICRO):
        outs.append(model(x[i:i+MICRO]))
result = torch.cat(outs, dim=0)
```

---

## 动手练习

写一个本地可运行的小服务，模拟动态批处理：

1. 用 `torch.nn.Linear(128, 10)` 造一个假模型。
2. 写一个 `DynamicBatcher`，参数 `max_batch_size=8, max_wait_ms=30`。
3. 用 `asyncio` 并发发起 100 个请求，每个请求是 `torch.randn(1, 128)`。
4. 统计：(a) 总共发生多少次 forward；(b) 每批的平均 batch size；(c) 端到端 P50/P99 延迟。
5. 改变 `max_wait_ms`（10/30/100），画出「平均延迟 vs 吞吐量」曲线，观察 trade-off。

预期结果：`max_wait_ms` 越大，batch size 越大、吞吐越高，但单请求延迟也越高。

## arch.serve.streaming

# arch.serve.streaming：流式推理服务

> 一句话直觉：用户等大模型回答时，希望**第一个字尽快出来**，而不是等整段话生成完才一次性显示。**流式（streaming）**就是让服务端一边生成、一边把结果推给客户端，把"等 10 秒"变成"0.3 秒看到第一个字"。

---

## 一、为什么需要流式？从"批"到"流"

传统 HTTP 接口的模型是**请求-响应（request-response）**：客户端发一个请求，服务端算完，把完整结果塞进一个 `Response` 返回。对大模型（LLM）来说这很糟：生成 500 个字可能要 10 秒，用户盯着白屏 10 秒才看到字。

**流式（streaming）**把一次响应拆成**多个数据块（chunk）**，服务端算出一小块就立刻发一块。用户看到的体验是"打字机效果"，首字节时间（TTFB, Time To First Byte）从秒级降到几百毫秒。

关键术语：
- **SSE（Server-Sent Events）**：HTTP 上的一种单向"服务端推流"协议，浏览器用 `EventSource` 或 `fetch` 读取。LLM 行业最常用。
- **chunk**：一次推送的最小数据单位，通常是一段文字或一个 token。
- **TTFB（Time To First Byte）**：从发请求到收到第一个字节的时间，流式服务的核心指标。

```python
# 对比：非流式 vs 流式
# 非流式：等全部生成完才返回
response = model.generate("讲个笑话")   # 阻塞 10 秒
print(response)                          # 10 秒后一次性看到结果

# 流式：边生成边返回
for chunk in model.stream("讲个笑话"):
    print(chunk, end="", flush=True)     # 0.3 秒就看到第一个字
```

---

## 二、最小可用流式服务：生成器 + SSE

Python 做流式最自然的工具是**生成器（generator）**——用 `yield` 一次吐一块。配合 Web 框架（下面用 FastAPI）就能变成 SSE 接口。

```python
# 一个极简的流式接口
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

app = FastAPI()

def fake_llm_stream(prompt: str):
    """模拟 LLM 逐字输出"""
    text = f"你说的是：{prompt}，我来回答……"
    for ch in text:
        yield ch            # 每次产出 1 个字符

@app.get("/chat")
def chat(q: str):
    def event_stream():
        for ch in fake_llm_stream(q):
            # SSE 格式：data: <内容>\n\n
            yield f"data: {ch}\n\n"
    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

要点：
1. 生成器**惰性求值**，服务端只在客户端还在读时才继续算。
2. `media_type="text/event-stream"` 告诉浏览器/客户端这是 SSE。
3. 每条消息以 `

` 结束，客户端按这个分帧。

---

## 三、客户端如何消费流？

流式客户端要**增量解析**，不能等响应结束。Python 用 `httpx.stream` 或 `requests` 的 `iter_lines`。

```python
import httpx

# 客户端流式读取
with httpx.stream("GET", "http://localhost:8000/chat", params={"q": "你好"}) as r:
    for line in r.iter_lines():
        if line.startswith("data: "):
            chunk = line[len("data: "):]
            print(chunk, end="", flush=True)  # 立即打印
```

注意：`iter_lines` 是**行级**迭代，SSE 的 `

` 分帧需要我们再做一次"空行触发一次 emit"的状态机；生产代码里通常用 `sse-starlette` 或 `httpx-sse` 库。

---

## 四、工程化要点

真实服务不止"能流"，还要**稳、快、可观测**：

1. **背压（backpressure）**：客户端读得慢时，服务端不能无限缓存。SSE 靠 TCP 窗口天然限速；用 `asyncio.Queue` 时要注意设置 `maxsize`。
2. **断线重连**：SSE 支持 `id:` 字段 + `Last-Event-ID` 头，客户端断线后可从上次位置继续。
3. **取消（cancellation）**：客户端关闭连接时，服务端要能停下生成，释放 GPU/调用。FastAPI 里检查 `await request.is_disconnected()`。
4. **缓冲（buffering）**：Nginx 默认会缓冲响应，必须加 `X-Accel-Buffering: no` 或 `proxy_buffering off`，否则"流"变"批"。
5. **心跳（heartbeat）**：长时间没 chunk 时定期发注释行 `: ping

`，防止中间层掐连接。

```python
import asyncio, json
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse

app = FastAPI()

async def sse_format(request: Request):
    """带心跳、可取消的 SSE 生成器"""
    for i in range(100):
        if await request.is_disconnected():
            break                              # 客户端走了，停
        payload = json.dumps({"i": i})
        yield f"id: {i}\ndata: {payload}\n\n"     # 带 id，便于断线续传
        await asyncio.sleep(0.1)

@app.get("/tick")
async def tick(request: Request):
    return StreamingResponse(
        sse_format(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",           # 关掉 Nginx 缓冲
        },
    )
```

---

## 五、与类型系统的关系：`Self`、`TypeVar`、`TypeAlias`

流式 SDK 常要写**链式风格**的客户端（如 `client.chat(...).on("chunk", cb)`），链式方法要返回 `self` 以保持类型。Python 3.11 引入的 `typing.Self` 正是为此：

- 方法返回 `Self` 时，子类调用仍推断为子类类型，而不是父类。
- 备选构造器 `@classmethod` 应返回 `Self`（或 `cls` 的类型），保证子类工厂返回子类实例。
- `TypeVar` 让泛型容器（如 `Stream[T]`）保留元素类型；`TypeAlias` 给复杂类型起名。

```python
from typing import Self, TypeVar, TypeAlias, Generic

T = TypeVar("T")

class Stream(Generic[T]):
    """泛型流，链式 API 用 Self 保持类型"""
    def __init__(self): self._items: list[T] = []
    def add(self, item: T) -> Self:      # 返回 Self，子类链式调用类型不丢
        self._items.append(item)
        return self
    def collect(self) -> list[T]:
        return list(self._items)

# 复杂类型起别名
ChunkHandler: TypeAlias = "Callable[[str], None]"
```

> 注意：如果方法**不保证**返回子类实例（比如总返回固定的 `Eggs()`），就不能用 `Self`，应写具体类名。

---

## 小结

| 概念 | 作用 |
|---|---|
| Streaming | 边生成边推送，降低 TTFB |
| SSE | HTTP 上最常用的流式协议 |
| Generator | Python 实现流的天然工具 |
| Backpressure/Cancel/Heartbeat | 工程上必须处理的三件事 |
| `Self` / `TypeVar` / `TypeAlias` | 流式 SDK 的类型友好写法 |


---

## 本课题目

### single_choice · None



- [A] 把每个请求单独提交给模型，减少排队延迟
- [B] 把多个请求聚合成一个批次一起送入模型计算
- [C] 增加更多的 HTTP 工作线程
- [D] 把模型的权重从 FP32 转换为 FP16

**参考答案**：1

**解析**：小请求单独执行时 GPU 利用率低，主要是启动开销和并行度不足。批处理能把多次前向合并成一次大矩阵运算，显著提升吞吐。增加 HTTP 线程只解决 CPU 侧的并发，不改变 GPU 利用率；FP16 能加速但通常不如批处理影响大。

### single_choice · None



- [A] 模型会报错，因为无法处理不等长输入
- [B] 权重会被错误更新
- [C] 大量无效填充计算，浪费显存和算力
- [D] 批处理的延迟一定低于单条处理

**参考答案**：2

**解析**：补齐到最长序列是常见做法，但会产生大量填充 token，造成无谓计算。模型本身可以处理不等长输入（通过 mask），但补齐会引入 wasted computation。

### single_choice · None



- [A] 微批是指把一个大批次拆成多个小批次依次执行，常用于流水线并行
- [B] 微批意味着必须放弃批处理
- [C] 微批只能用于训练，不能用于推理
- [D] 微批的批次大小必须为 1

**参考答案**：0

**解析**：微批是把大批次切分成若干小块，在流水线并行中让不同阶段重叠执行，减少气泡。它仍是批处理的一种形式，推理中也可使用。

### single_choice · None



- [A] 批次大小设置得过小
- [B] 请求到达速率太低，队列长期为空
- [C] CPU 预处理成为瓶颈，GPU 经常等待数据
- [D] 模型使用了 FP16 权重

**参考答案**：3

**解析**：FP16 通常能提升计算速度和利用率，不会导致 GPU 利用率低。批次小、请求稀疏、CPU 瓶颈都会让 GPU 空闲。

### single_choice · None



- [A] 吞吐量一定下降
- [B] 请求的平均排队延迟增加
- [C] 模型精度下降
- [D] 显存占用一定减少

**参考答案**：1

**解析**：等待窗口越长，请求在队列中停留越久，平均延迟上升。吞吐可能因批次更大而提升，所以「一定下降」不成立。

### single_choice · None



- [A] 避免重复计算历史 token 的注意力键值
- [B] 减少模型参数数量
- [C] 提高 tokenizer 的速度
- [D] 让批次大小自动增大

**参考答案**：0

**解析**：KV Cache 缓存历史 token 的键值，多轮对话中可复用，避免重复前向计算历史部分，从而降低延迟和算力消耗。

### single_choice · None



- [A] 只要实现正确，批处理不应改变每个样本的推理结果
- [B] 批处理会降低模型精度，所以结果一定不同
- [C] 批处理会让所有样本输出相同结果
- [D] 批处理只影响速度，不影响数值

**参考答案**：0

**解析**：正确的批处理实现中，每个样本独立计算，结果与单条推理应一致（浮点误差除外）。批处理不会改变模型语义。

### single_choice · None



- [A] 因为模型只能处理固定数量的输入
- [B] 为了防止单个大批次导致显存溢出或延迟过高
- [C] 因为批处理框架不支持更大的批次
- [D] 为了减少网络请求数量

**参考答案**：1

**解析**：批次过大会导致显存不足或单步耗时过长，影响稳定性和尾延迟。设置上限是保护服务的手段，而非模型本身的硬限制。

### single_choice · None



- [A] GPU 已经接近计算饱和，继续增大批次收益递减
- [B] 模型在批次大于 32 时精度下降
- [C] 网络带宽成为瓶颈
- [D] 请求数量不够

**参考答案**：0

**解析**：批次增大到一定程度后，GPU 计算单元接近饱和，额外批次带来的并行收益递减，甚至被显存和调度开销抵消。

### single_choice · None



- [A] 注意力掩码（attention mask）
- [B] 梯度裁剪
- [C] 学习率预热
- [D] 权重衰减

**参考答案**：0

**解析**：padding 位置是无效 token，必须通过 attention mask 让模型忽略它们，否则会污染注意力计算。梯度裁剪、学习率等是训练概念。

### single_choice · None



- [A] 把所有请求混在同一个批次里，统一补齐到最长
- [B] 按任务和长度分别组批，避免长短混批
- [C] 只对短文本启用批处理
- [D] 禁用批处理以保证公平

**参考答案**：1

**解析**：不同任务的计算图和长度差异大，混批会导致严重 padding 和资源浪费。按任务/长度分桶组批能兼顾效率和延迟。

### single_choice · None



- [A] 批处理是把多个样本合并成一次前向，利用 GPU 并行能力
- [B] 批处理等同于多线程 CPU 并行
- [C] 批处理必须使用多张 GPU
- [D] 批处理会降低 GPU 并行度

**参考答案**：0

**解析**：批处理把多个样本的矩阵运算合并，形成更大的矩阵乘法，从而更充分地利用 GPU 的并行计算单元。它不要求多 GPU，也不是 CPU 多线程。

### single_choice · None



- [A] 静态批处理必须等到凑满固定数量才能开始计算，可能增加等待时间
- [B] 动态批处理要求所有请求的长度完全一致
- [C] 静态批处理的平均延迟一定低于动态批处理
- [D] 动态批处理不能和连续批处理结合

**参考答案**：0

**解析**：静态批处理按固定批次大小组批，可能需要等待或填充；动态批处理根据当前队列在短时间内组批，更灵活。长度一致并非动态批处理的要求。

### single_choice · None



- [A] 继续等待直到凑满 32 个请求
- [B] 直接丢弃这 3 个请求
- [C] 立即用这 3 个请求组批执行
- [D] 把批次大小上限临时改为 3

**参考答案**：2

**解析**：动态批处理通常以「凑满批次或达到最大等待时间」中先满足者触发。已超过 10ms 等待上限，应立即组批执行，避免延迟继续增大。

### single_choice · None



- [A] 必须等整个批次所有序列都结束才能开始新请求
- [B] 可以把空出的位置立即分配给队列中的新请求
- [C] 必须清空 KV Cache 并重新开始整个批次
- [D] 新请求必须等到下一个批次周期

**参考答案**：1

**解析**：连续批处理的核心是逐 token 调度，序列结束后释放的槽位可立即被新请求复用，从而减少空闲等待，提升 GPU 利用率。

### single_choice · None



- [A] 无限增大批次大小，吞吐优先
- [B] 完全禁用批处理，只做单条推理
- [C] 设置较小的最大批次和较短的等待窗口
- [D] 只在夜间低峰期启用批处理

**参考答案**：2

**解析**：首 token 延迟对等待窗口敏感，窗口越长延迟越高；批次越大单步耗时也越高。折中方案是小批次加短等待窗口，在延迟和吞吐之间取得平衡。

### single_choice · None



- [A] 批处理不会增加显存占用，因为权重是共享的
- [B] 批次越大，激活值和 KV Cache 等中间张量的显存占用通常越高
- [C] 只要模型权重能放进显存，批次就可以无限增大
- [D] 显存占用只和输入文本长度有关，和批次大小无关

**参考答案**：1

**解析**：虽然权重在批次内共享，但每个样本的激活值、注意力中间结果、KV Cache 等都会随批次增大而增大，因此显存会成为批次大小的约束。

### single_choice · None



- [A] 降低模型权重的显存占用
- [B] 减少因补齐到最长序列造成的无效计算
- [C] 让所有请求的延迟完全一致
- [D] 避免使用动态批处理

**参考答案**：1

**解析**：把长度相近的请求放在同一批次，能显著减少 padding 比例，从而提高有效计算占比。它不改变权重占用，也不能保证延迟完全一致。

### single_choice · None



- [A] 批次越大，单个批次的计算时间越长，排在后面的请求等待更久
- [B] 批次越大，模型精度越低
- [C] 批次越大，网络带宽消耗越大
- [D] 批次越大，CPU 预处理越慢

**参考答案**：0

**解析**：批次增大通常提升吞吐，但单次前向耗时也增加，队列中的请求要等更久，导致尾延迟恶化。精度和带宽通常不是主因。

### single_choice · None



- [A] 减少模型参数量
- [B] 让 GPU 专注于矩阵运算，减少空闲等待
- [C] 提高模型准确率
- [D] 避免使用批处理

**参考答案**：1

**解析**：CPU 侧的预处理/后处理如果串行阻塞 GPU，会造成气泡。异步或并行执行可以让 GPU 持续工作，提升整体利用率。

### single_choice · None



- [A] 响应内容会被浏览器缓存
- [B] 内存占用随文件大小增长，可能触发 OOM 并拖垮并发能力
- [C] HTTP 状态码会变成 206
- [D] Content-Length 无法被设置

**参考答案**：1

**解析**：一次性读入内存会让服务进程的内存随单个响应体大小线性增长，大文件或高并发时容易内存耗尽，而流式响应通过分块读取与发送把内存占用控制在较小常量级。

### single_choice · None



- [A] 服务器必须先知道完整响应体的长度才能发送
- [B] 响应体被拆成多个块依次发送，客户端可以边接收边处理
- [C] 流式响应只适用于 WebSocket，普通 HTTP 不支持
- [D] 流式响应必须使用 POST 方法

**参考答案**：1

**解析**：流式响应的核心是把响应体分批（chunk）发送，客户端可以在收到部分数据后就开始处理，从而降低首字节延迟；它并不绑定 WebSocket 或特定请求方法。

### single_choice · None



- [A] 每写一块就 flush
- [B] 数据被中间反向代理缓冲，且未配置禁用缓冲
- [C] 使用 chunked 传输编码
- [D] 响应头设置了正确的 Content-Type

**参考答案**：1

**解析**：反向代理（如 Nginx）默认会缓冲上游响应，导致小块数据被攒着不转发；需要针对该路由关闭代理缓冲才能保证实时下发。

### multi_choice · None



- [A] 响应体很大，无法或不宜整体放入内存
- [B] 数据是逐步产生、长度事先不确定的
- [C] 希望降低首字节延迟、提升感知性能
- [D] 希望减少服务端代码的单元测试数量

**参考答案**：[0, 1, 2]

**解析**：流式适用于大响应、增量产生、低延迟等场景；它与测试数量没有因果关系，属于干扰项。

### multi_choice · None



- [A] 响应头一旦发出，就无法再更改状态码
- [B] 生成器/迭代器可以作为惰性数据源
- [C] 为保证实时性通常需要及时 flush
- [D] 流式响应必须把整个响应体一次性计算完成后再发送
- [E] 客户端断开后服务端应当停止无谓的生成

**参考答案**：[0, 1, 2, 4]

**解析**：前三项与最后一项都是流式实现的关键要点；『先算完再发送』恰恰与流式的增量思想相悖，是错误选项。

### multi_choice · None



- [A] 在发送响应头之前发生的错误，通常仍可返回普通错误状态码
- [B] 在已发送部分数据后，无法再把状态码改成 500
- [C] 可以在流内以约定格式发送错误信息供客户端识别
- [D] 只要捕获异常，客户端就一定能自动感知错误
- [E] 错误处理可以完全省略，让连接超时即可

**参考答案**：[0, 1, 2]

**解析**：头部发送前可正常报错，之后只能靠流内约定；捕获异常不等于客户端能自动感知，省略错误处理会导致客户端一直等待或拿到不完整数据。

### multi_choice · None



- [A] 每次写出一块数据后主动 flush
- [B] 为该路由关闭反向代理的响应缓冲
- [C] 避免使用会积攒数据才输出的压缩方式
- [D] 把所有数据先累积到列表里，最后统一发送
- [E] 让写入操作在需要时立即下发而非等多块攒满

**参考答案**：[0, 1, 2, 4]

**解析**：及时 flush、关闭代理缓冲、避免缓冲型压缩、及时下发都是保持实时性的手段；先全部累积再发送等于放弃了流式，是错误选项。

### fill_blank · None



**参考答案**：["yield", "yield 关键字", "yield语句"]

**解析**：yield 使函数成为生成器，每次迭代执行到 yield 处产出值并暂停，从而支持惰性、逐步产生数据。

### fill_blank · None



**参考答案**：["chunked", "chunked 编码", "分块传输编码", "chunked transfer encoding"]

**解析**：chunked 传输编码把响应体分成若干块并发送，以终止块结束，使未知长度的流式响应成为可能。

### code_reading · None



**参考答案**：created\nstart\nmid\nend

**解析**：调用生成器函数 gen() 不会执行函数体，只返回生成器对象，所以先打印 created；第一次 next 执行到第一个 yield，打印 start 并产出 1；第二次 next 从挂起点继续，打印 mid 并产出 2；end 只有在第三次 next（或迭代结束）时才会打印，因此不含 end 的第二次 next 之后尚未打印 end。

### code_reading · None



**参考答案**：[0, 1, 2, 0, 1, 2]

**解析**：每次调用 counter(3) 都返回一个全新的生成器，各自独立地从 0 迭代到 2，因此两次 list() 结果拼接为 [0,1,2,0,1,2]。

### scenario · None



**解析**：典型原因是反向代理对上游响应做了缓冲，把小块数据攒着，破坏实时性；也有可能是应用未及时 flush 或压缩层引入缓冲。排查时可对比直连与经代理的表现，检查代理缓冲配置；修复方向是针对该路由关闭代理缓冲、在应用中及时 flush，并避免缓冲型压缩。

### single_choice · None



- [A] identity
- [B] chunked
- [C] gzip
- [D] multipart

**参考答案**：1

**解析**：chunked 传输编码允许服务器在不知道总长度时逐块发送响应体并以终止块结束；identity 表示不编码，gzip 是内容压缩而非分块机制。

### scenario · None



**解析**：先把全部结果算好再返回并不具备流式的核心特征——增量产出与低首字节延迟，还会让内存随时长/规模增长。改造方向是用生成器或迭代器惰性产生数据、边产生边发送，并及时 flush，从而降低内存占用与首字节延迟。

### single_choice · None



- [A] 返回一个 20 字节的 JSON 状态对象
- [B] 向客户端持续推送大模型逐词生成的文本
- [C] 返回 302 重定向
- [D] 返回 204 No Content

**参考答案**：1

**解析**：逐词生成属于内容持续产生、总体长度事先不确定的场景，适合边生成边推送；而小对象、重定向、无内容响应都不需要流式。

### single_choice · None



- [A] 总传输字节数显著减少
- [B] 首字节时间（TTFB）更早，用户更早看到内容
- [C] 服务端 CPU 使用率必然下降
- [D] 可以完全省略 TLS 握手

**参考答案**：1

**解析**：流式的最直接收益是提早返回首批数据，降低首字节延迟、改善感知性能；总字节数一般不变，CPU 也不一定下降，TLS 握手与是否流式无关。

### single_choice · None



- [A] 立即完整执行到 return
- [B] 立即执行到第一个 yield 后暂停
- [C] 不会立即执行，只返回一个生成器对象，迭代时才执行
- [D] 会在线程中异步执行

**参考答案**：2

**解析**：调用生成器函数只返回生成器对象，函数体在第一次迭代（如 next()）时才执行到首个 yield 并挂起，这正是可以用于惰性、流式产出数据的原因。

### single_choice · None



- [A] 直接让连接异常断开即可，无需任何处理
- [B] 由于已经发送了响应头，无法再改成 500，应以某种约定格式在流中告知客户端错误并安全结束
- [C] 重新从头发送一个 500 响应
- [D] 忽略异常继续发送剩余数据

**参考答案**：1

**解析**：一旦响应头已发出，HTTP 状态码无法再变更；常见做法是在流内发送一个约定好的错误标记/事件，并妥善关闭流，让客户端识别并处理。

### single_choice · None



- [A] 服务端会立即收到通知并应停止继续生成，避免无谓的资源消耗
- [B] 客户端断开后服务端仍会完整生成所有数据直到结束
- [C] 客户端断开会导致服务进程崩溃
- [D] 客户端断开后服务端无法感知，只能等超时

**参考答案**：0

**解析**：大多数框架能感知连接断开（如捕获写失败或断开事件），此时应停止生成、释放资源；否则会做无用功、浪费 CPU 和上游调用配额。

### single_choice · None



- [A] 压缩会使响应无法分块
- [B] 压缩可能引入缓冲，导致数据不能及时刷出，削弱流式的实时性
- [C] 压缩会改变 HTTP 状态码
- [D] 压缩只能用于 200 响应

**参考答案**：1

**解析**：压缩实现通常需要攒够一定数据量才输出，从而引入缓冲、延迟刷出，抵消流式的低延迟优势；实时场景常禁用压缩或使用流式友好的压缩配置。

### single_choice · None



- [A] 手动把每次写出的数据立即 flush/刷出，避免中间层缓冲
- [B] 把所有数据写完后一次性 flush
- [C] 禁用 Nagle 算法即可，无需 flush
- [D] 增加响应体长度

**参考答案**：0

**解析**：中间件、代理和底层 socket 都可能缓冲数据，若不主动 flush，小块数据会被攒着，导致客户端迟迟收不到，实时性丧失。
