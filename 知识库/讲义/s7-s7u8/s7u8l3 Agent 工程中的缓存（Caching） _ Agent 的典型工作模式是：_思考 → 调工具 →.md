# s7u8l3 Agent 工程中的缓存（Caching） / Agent 的典型工作模式是：**思考 → 调工具 →

> 来源 `content/lessons/s7u8l3.json`

## agent.eng.caching

# Agent 工程中的缓存（Caching）

## 一句话直觉

> Agent（智能体）每一次调用大模型都很贵、很慢，而很多请求其实是重复的——**缓存就是让同样的活儿只干一次的工程手段。**

学它的理由很朴素：一个 Agent 应用能省 80% 的 token 成本和一半的延迟，通常不是靠换更小的模型，而是靠**命中率高的缓存层**。

---

## 第 1 节：什么是缓存，为什么 Agent 特别需要它

**缓存（Cache）** 是一种用「空间换时间」的策略：把一次昂贵计算的输入和输出存起来，下次遇到相同输入直接返回输出。

Agent 场景下，“昂贵计算”通常是：

- 一次 LLM 调用（几十毫秒到几十秒，按 token 计费）；
- 一次工具（Tool）调用（如搜索 API、数据库查询、代码执行）；
- 一次嵌入（Embedding）计算。

Agent 请求有个特点：**输入空间重复度极高**。用户会反复问相似的问题；同一段文档会被多个请求当作上下文；同一个工具会被不同子任务调用。这正好是缓存的甜点区。

```python
# 最朴素的缓存：用 dict 把「输入 -> 输出」记下来
import time

_cache = {}

def slow_llm_call(prompt: str) -> str:
    """模拟一次昂贵的 LLM 调用"""
    if prompt in _cache:              # 命中缓存，直接返回
        return _cache[prompt]
    time.sleep(1.0)                   # 模拟 1 秒的网络+推理耗时
    answer = f"回答：{prompt.upper()}"
    _cache[prompt] = answer           # 写回缓存
    return answer

print(slow_llm_call("你好"))          # 约 1 秒
print(slow_llm_call("你好"))          # 几乎瞬时
```

**关键结论**：缓存的第一性原理是「输入决定输出」——只有当同样的输入必然得到同样的输出时，缓存才安全。

---

## 第 2 节：缓存的键（Cache Key）——经常被低估的坑

缓存的核心不是存，而是**如何定义一个「相同」的请求**。这个东西叫缓存键（cache key）。

在 Agent 里，一个请求通常包含：prompt、模型名、温度（temperature）、系统提示词（system prompt）、工具列表、历史对话。任何一个不同，结果就可能不同。所以 key 必须是**这些字段的确定性（deterministic）编码**。

常见做法是把它们序列化成 JSON，再哈希。

```python
import hashlib, json

def make_cache_key(prompt, model, temperature, system_prompt=""):
    """把请求参数规范化后哈希成一个短 key"""
    payload = {
        "prompt": prompt,
        "model": model,
        "temperature": temperature,
        "system": system_prompt,
    }
    # sort_keys 保证同样的字段顺序得到同样的字符串
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()

k1 = make_cache_key("你好", "gpt-4o", 0.0)
k2 = make_cache_key("你好", "gpt-4o", 0.0)
k3 = make_cache_key("你好", "gpt-4o", 0.7)   # 温度不同
print(k1 == k2)   # True
print(k1 == k3)   # False
```

**关键结论**：key 的粒度决定了缓存的正确性与命中率。太粗会返回错的答案，太细则几乎命不中。

> 小技巧：`temperature > 0` 时模型输出带有随机性，严格来说不可缓存。工程上常见的折中是：只对 `temperature == 0` 的调用做语义缓存，其余做「概率性缓存」或直接跳过。

---

## 第 3 节：缓存的失效（Eviction）与容量控制

缓存不能无限增长，否则内存迟早爆掉。所以必须有一套**淘汰策略（eviction policy）**。最常用的三种：

| 策略 | 含义 | 适用场景 |
|---|---|---|
| LRU（Least Recently Used） | 淘汰最久未使用的 | 通用、请求有热度聚集 |
| TTL（Time To Live） | 超过一定时间就失效 | 数据会过期，如搜索结果 |
| LFU（Least Frequently Used） | 淘汰访问次数最少的 | 访问频率差异大 |

Python 自带的 `functools.lru_cache` 就是 LRU，但它是进程内的、容量固定的（不能按时间过期）。Agent 服务里更常用「TTL + LRU」的混合体。

```python
from functools import lru_cache
import time

# 最多缓存 128 个条目，超出后淘汰最久未用的
@lru_cache(maxsize=128)
def embed(text: str) -> tuple:
    """模拟一次 embedding 调用，返回 tuple（因为 lru_cache 要求可哈希）"""
    time.sleep(0.5)
    return tuple(ord(c) % 100 for c in text[:8])

print(embed("agent"))
print(embed("agent"))            # 命中，不再 sleep
print(embed.cache_info())        # 查看命中率：hits / misses / maxsize
```

**关键结论**：有缓存就一定要有过期/淘汰，否则就是内存泄漏；`cache_info()` 是你诊断命中率的第一手工具。

---

## 第 4 节：分层缓存——Agent 工程的真实战场

单层缓存远远不够。生产级 Agent 通常有**多级缓存（multi-tier cache）**：

1. **精确缓存（Exact Cache）**：key = 完整请求哈希。命中即秒回。
2. **语义缓存（Semantic Cache）**：把 prompt 做 embedding，如果和某个历史 prompt 的余弦相似度超过阈值（如 0.95），就复用答案。能命中「换了个说法但意思一样」的请求。
3. **前缀缓存（Prefix Cache）**：很多 LLM 提供商（如 OpenAI、Anthropic）对相同前缀的 prompt 有 KV 缓存折扣。把 system prompt 放前面、变化的内容放后面，成本能降一大截。
4. **分布式缓存（Distributed Cache）**：跨进程、跨机器共享，常用 Redis。单机 `dict` 在多副本部署下命中率极低。

```python
# 语义缓存的极简演示（不依赖外部库，只用余弦相似度）
import math

def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb + 1e-9)

class SemanticCache:
    def __init__(self, threshold=0.95):
        self.threshold = threshold
        self.entries = []  # [(vector, value), ...]

    def get(self, vec):
        best, best_sim = None, 0.0
        for v, val in self.entries:
            s = cosine(vec, v)
            if s > best_sim:
                best, best_sim = val, s
        return best if best_sim >= self.threshold else None

    def put(self, vec, value):
        self.entries.append((vec, value))

cache = SemanticCache()
cache.put([1.0, 0.0, 0.0], "你好！")
# 一个「很像」的向量，应该命中
print(cache.get([0.99, 0.01, 0.0]))   # 你好！
# 一个「不太像」的向量，不应命中
print(cache.get([0.0, 1.0, 0.0]))     # None
```

**关键结论**：精确缓存保底，语义缓存提命中率，前缀缓存省成本，分布式缓存保多副本一致——四个各管一段，组合起来才有效。

---

## 第 5 节：从「正确」到「工程级」——一致性、可观测、可关闭

到这一步，你需要考虑三件工程事：

1. **一致性（Consistency）**：缓存返回的可能是旧数据。对于会变的工具结果（如股票价格），必须用短 TTL 或加版本号。
2. **可观测（Observability）**：记录命中率、命中延迟、缓存大小。一个命中率 5% 的缓存就是白费内存。
3. **可关闭（Kill Switch）**：要有开关，能在出现脏数据时一键关闭，而不是改代码重新发版。

```python
import os
import time

class TTLCache:
    """带 TTL 和开关的缓存——生产最小可用形态"""
    def __init__(self, ttl_seconds=60, enabled=True):
        self.ttl = ttl_seconds
        self.enabled = enabled
        self.store = {}          # key -> (value, expire_at)
        self.hits = self.misses = 0

    def get(self, key):
        if not self.enabled:
            self.misses += 1
            return None
        item = self.store.get(key)
        if item and item[1] > time.time():
            self.hits += 1
            return item[0]
        self.misses += 1
        return None

    def put(self, key, value):
        if not self.enabled:
            return
        self.store[key] = (value, time.time() + self.ttl)

    def stats(self):
        total = self.hits + self.misses
        rate = self.hits / total if total else 0.0
        return {"hits": self.hits, "misses": self.misses, "hit_rate": round(rate, 3)}

# 演示
c = TTLCache(ttl_seconds=1)
c.put("q", "answer")
print(c.get("q"))         # answer
print(c.stats())           # {'hits': 1, 'misses': 0, 'hit_rate': 1.0}
time.sleep(1.2)
print(c.get("q"))          # None（已过期）
c.enabled = False          # 一键关闭
print(c.stats())
```

**关键结论**：一个「工程级」缓存 = 正确的 key + 合理的淘汰 + 分层策略 + 可观测指标 + 开关。前三条让它能工作，后两条让它能被维护。

---

## 动手练习（本地可完成）

**任务：给一个假装的 Agent 加上两级缓存，并验证命中率提升。**

1. 写一个函数 `fake_agent(question: str) -> str`，模拟 0.3 秒延迟，返回对问题的「回答」（可以是任何字符串，但要包含 question）。
2. 用第 2 节的 `make_cache_key` 思路，为它加一层**精确缓存**（key = question 的哈希）。
3. 再包一层**语义缓存**：把 question 转成简单向量（例如 `[len(question), question.count(' '), sum(map(ord, question)) % 100]`），相似度阈值 0.95。
4. 用下面 5 个问题依次调用你的封装函数（第一次全部预期 miss，第二次预期大部分 hit）：
   - `"今天天气怎么样"`
   - `"今天天气怎么样"` （完全相同，精确命中）
   - `"今天 天气 怎么样"`（只差空格，语义可能命中）
   - `"明天天气怎么样"`（差一个字，语义可能不命中）
   - `"今天天气怎么样"`（再次精确命中）
5. 打印 `stats()`：命中数、未命中数、命中率。

**提交标准**：
- 能跑，无报错；
- 打印出的命中率 > 0；
- 在注释里用一句话说明你为什么这么设相似度阈值。

**进阶（可选）**：把 TTL 设为 2 秒，观察 3 秒后再调用时，是否所有请求都 miss。

```python
import time
import hashlib
import json
import math

# ---------- 1. 伪 Agent：模拟昂贵调用 ----------
def fake_agent(question: str) -> str:
    time.sleep(0.3)  # 模拟 LLM 延迟
    return f"关于「{question}」的回答"

# ---------- 2. 精确缓存 ----------
class ExactCache:
    def __init__(self):
        self.store = {}
        self.hits = self.misses = 0

    @staticmethod
    def key(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def get(self, text):
        k = self.key(text)
        if k in self.store:
            self.hits += 1
            return self.store[k]
        self.misses += 1
        return None

    def put(self, text, value):
        self.store[self.key(text)] = value

# ---------- 3. 语义缓存 ----------
def to_vec(text: str):
    # 一个极简的“伪 embedding”
    return [len(text), text.count(" "), sum(map(ord, text)) % 100]

def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1e-9
    nb = math.sqrt(sum(y * y for y in b)) or 1e-9
    return dot / (na * nb)

class SemanticCache:
    def __init__(self, threshold=0.95):
        self.threshold = threshold
        self.entries = []  # (vec, value)
        self.hits = self.misses = 0

    def get(self, text):
        v = to_vec(text)
        best, best_sim = None, 0.0
        for ev, val in self.entries:
            s = cosine(v, ev)
            if s > best_sim:
                best, best_sim = val, s
        if best is not None and best_sim >= self.threshold:
            self.hits += 1
            return best
        self.misses += 1
        return None

    def put(self, text, value):
        self.entries.append((to_vec(text), value))

# ---------- 4. 两级缓存封装 ----------
exact = ExactCache()
semantic = SemanticCache(threshold=0.95)

def cached_agent(question: str) -> str:
    hit = exact.get(question)
    if hit is not None:
        return "[EXACT] " + hit
    hit = semantic.get(question)
    if hit is not None:
        return "[SEMANTIC] " + hit
    ans = fake_agent(question)
    exact.put(question, ans)
    semantic.put(question, ans)
    return "[MISS] " + ans

# ---------- 5. 测试 ----------
if __name__ == "__main__":
    questions = [
        "今天天气怎么样",
        "今天天气怎么样",   # 精确命中
        "今天 天气 怎么样", # 语义可能命中
        "明天天气怎么样",   # 大概率 miss
        "今天天气怎么样",   # 精确命中
    ]
    for q in questions:
        print(f"{q!r} -> {cached_agent(q)}")

    print("Exact stats   :", {"hits": exact.hits, "misses": exact.misses})
    print("Semantic stats:", {"hits": semantic.hits, "misses": semantic.misses})
```

## agent.eng.rate_limit

## 一句话直觉
**限流（Rate Limiting）** 就是给 Agent（智能体）装一个“请求节流阀”：无论外部 API 多慢、下游多脆弱，你的 Agent 都必须按既定节奏调用，否则就会触发 429 限流错误、账单爆炸或服务雪崩。

---

## 1. 为什么 Agent 必须懂限流？

Agent 的典型工作模式是：**思考 → 调工具 → 观察 → 再思考**。一次任务可能触发几十次 LLM（大语言模型）调用或外部 API 调用。如果 Agent 无节制地并发请求：

- 第三方服务会直接返回 **HTTP 429 Too Many Requests**；
- 你的 Token 消耗会在几秒内烧掉预算；
- 下游数据库被打挂，整个 Agent 任务失败。

所以限流不是“优化”，而是 Agent 工程化的**第一道防线**。

```python
import time

# 反例：没有限流，短时间疯狂请求
# for i in range(1000):
#     call_llm_api()  # 很快就会被 429 阻断
```

---

## 2. 三种最常用的限流算法

### 2.1 固定窗口（Fixed Window）

把时间切成固定区间（比如每 60 秒），区间内计数不超过 N 次。实现最简单，但**临界问题**明显：两个窗口交界处可能瞬间放过 2N 次请求。

```python
import time

class FixedWindowLimiter:
    def __init__(self, max_calls: int, window: float = 60.0):
        self.max_calls = max_calls
        self.window = window
        self.start = time.time()
        self.count = 0

    def allow(self) -> bool:
        now = time.time()
        if now - self.start >= self.window:
            # 进入新窗口，重置计数
            self.start = now
            self.count = 0
        if self.count < self.max_calls:
            self.count += 1
            return True
        return False
```

### 2.2 滑动窗口（Sliding Window）

记录每个请求的时间戳，只保留最近 `window` 秒内的记录。精度更高，代价是内存随 QPS（每秒查询数）增长。

```python
import time
from collections import deque

class SlidingWindowLimiter:
    def __init__(self, max_calls: int, window: float = 60.0):
        self.max_calls = max_calls
        self.window = window
        self.timestamps = deque()

    def allow(self) -> bool:
        now = time.time()
        # 剔除窗口外的旧记录
        while self.timestamps and now - self.timestamps[0] > self.window:
            self.timestamps.popleft()
        if len(self.timestamps) < self.max_calls:
            self.timestamps.append(now)
            return True
        return False
```

### 2.3 令牌桶（Token Bucket）

以恒定速率向桶中放令牌，请求需要消耗令牌。既能限制**平均速率**，又允许**突发流量**（burst），是工程上最常用的方案，也是各大云厂商 API 限流的标准模型。

```python
import time

class TokenBucket:
    def __init__(self, rate: float, capacity: int):
        self.rate = rate            # 每秒补充的令牌数
        self.capacity = capacity    # 桶容量（最大突发量）
        self.tokens = capacity
        self.last = time.time()

    def allow(self, n: int = 1) -> bool:
        now = time.time()
        # 按经过的时间补充令牌，上限为容量
        self.tokens = min(self.capacity, self.tokens + (now - self.last) * self.rate)
        self.last = now
        if self.tokens >= n:
            self.tokens -= n
            return True
        return False
```

---

## 3. 在 Agent 中如何接入限流？

真实 Agent 通常会对每一个工具（Tool）或每一个 Provider 挂一个限流器，并配合**重试 + 退避（backoff）**：

```python
import time, random

def call_with_retry(fn, limiter, max_retries: int = 5):
    for attempt in range(max_retries):
        if limiter.allow():
            return fn()
        # 指数退避 + 抖动，避免惊群
        sleep = min(2 ** attempt + random.random(), 30)
        time.sleep(sleep)
    raise RuntimeError("rate limit exceeded after retries")
```

关键点：

1. **限流器是共享状态**：同一 API Key 下所有协程/线程要共用一个 limiter，否则形同虚设。
2. **退避要带抖动（jitter）**：纯指数退避会让多个 Agent 同时重试，再次撞墙。
3. **区分硬限与软限**：硬限（每秒 N 次）直接阻断；软限（预算）可以降级。

---

## 4. 分布式场景的下沉：集中式限流

单机 limiter 在多副本 Agent 下会失效（每个进程各算一份）。工程上通常把令牌桶下沉到 **Redis**，用 Lua 脚本保证原子性：

```python
# 伪代码示意（需 redis-py）
# LUA = '''
# local tokens = tonumber(redis.call('get', KEYS[1]) or ARGV[2])
# local rate = tonumber(ARGV[1])
# local cap = tonumber(ARGV[2])
# local now = tonumber(ARGV[3])
# ... 计算补充令牌并写回 ...
# '''
```

这一步是 Agent 从“玩具”走向“生产”的分水岭。

---

## 5. 工程落地清单

- 为每个外部依赖（LLM、搜索、DB）单独配置限流；
- limiter 参数从配置中心下发，可动态调整；
- 打点监控 `allow / deny` 比例，观察是否过紧或过松；
- 与预算（budget）系统联动，超预算直接熔断；
- 永远要假设**下游会 429**，重试逻辑必须写好。

> 一句话总结：**限流是 Agent 与外部世界之间的“节流阀 + 缓冲器”，它决定了你的 Agent 能不能在真实流量下活着。**

```python
import time
import random
from collections import deque

class TokenBucket:
    """令牌桶限流器：平均速率 rate，突发容量 capacity。"""
    def __init__(self, rate: float, capacity: int):
        self.rate = rate
        self.capacity = capacity
        self.tokens = float(capacity)
        self.last = time.time()

    def allow(self, n: int = 1) -> bool:
        now = time.time()
        self.tokens = min(self.capacity, self.tokens + (now - self.last) * self.rate)
        self.last = now
        if self.tokens >= n:
            self.tokens -= n
            return True
        return False

class SlidingWindowLimiter:
    """滑动窗口限流器：window 秒内最多 max_calls 次。"""
    def __init__(self, max_calls: int, window: float = 60.0):
        self.max_calls = max_calls
        self.window = window
        self.timestamps = deque()

    def allow(self) -> bool:
        now = time.time()
        while self.timestamps and now - self.timestamps[0] > self.window:
            self.timestamps.popleft()
        if len(self.timestamps) < self.max_calls:
            self.timestamps.append(now)
            return True
        return False

def call_with_retry(fn, limiter, max_retries: int = 5):
    """限流 + 指数退避重试，避免 429 后疯狂重试。"""
    for attempt in range(max_retries):
        if limiter.allow():
            return fn()
        sleep = min(2 ** attempt + random.random(), 30)
        print(f"[限流] 第 {attempt + 1} 次被拒，等待 {sleep:.2f}s")
        time.sleep(sleep)
    raise RuntimeError("rate limit exceeded after retries")

if __name__ == "__main__":
    # 演示 1：令牌桶，2 次/秒，突发 3
    bucket = TokenBucket(rate=2.0, capacity=3)
    ok = sum(1 for _ in range(10) if bucket.allow())
    print(f"令牌桶瞬时通过: {ok}/10（容量 3，符合预期）")

    # 演示 2：滑动窗口，1 秒内最多 3 次
    sw = SlidingWindowLimiter(max_calls=3, window=1.0)
    passed = [sw.allow() for _ in range(5)]
    print(f"滑动窗口通过情况: {passed}")

    # 演示 3：带限流的调用
    counter = {"n": 0}
    def fake_llm():
        counter["n"] += 1
        return f"llm-response-{counter['n']}"

    limiter = TokenBucket(rate=5.0, capacity=2)
    for i in range(4):
        try:
            print(call_with_retry(fake_llm, limiter))
        except RuntimeError as e:
            print("超出重试:", e)
```


---

## 本课题目

### single_choice · None



- [A] 把查询语句改写得更短，减少接口返回的数据量
- [B] 对相同输入的查询结果进行缓存，命中时直接复用
- [C] 增加并发线程数，让每次调用都重新发起请求
- [D] 将搜索接口换成延迟更低的接口，但不做任何结果复用

**参考答案**：1

**解析**：缓存的核心思想就是复用相同输入对应的结果，命中时无需重新计算或请求，从而降低延迟且不改变结果。改写查询会改变语义；增加并发不减少重复请求；更换接口只是降低单次延迟，未解决重复计算问题。

### single_choice · None



- [A] 缓存仍然命中，因为集合相同
- [B] 缓存无法命中，产生本可避免的重复计算
- [C] 缓存命中但返回错误结果
- [D] 缓存键冲突，覆盖掉其他用户的缓存

**参考答案**：1

**解析**：顺序不同会使拼接后的键字符串不同，导致缓存未命中，形成重复计算。内容相同的集合应做规范化（如排序）再作为键的一部分。

### single_choice · None



- [A] 并发写入导致存储介质磨损
- [B] 并发读写可能产生数据竞争或覆盖不一致的结果
- [C] 并发会使缓存键自动改变
- [D] 并发写入一定会让缓存完全失效

**参考答案**：1

**解析**：并发读写下若缺乏同步机制，可能出现数据竞争，导致读到中间状态或被错误覆盖。并发不会自动改变键，也不会必然导致缓存完全失效。

### single_choice · None



- [A] 关闭缓存，让所有请求都直接回源
- [B] 对同一键的回源请求做合并或加锁，只让少量请求真正计算
- [C] 把所有缓存条目的过期时间设为同一时刻
- [D] 缩短缓存的过期时间以加快更新

**参考答案**：1

**解析**：合并或加锁可以避免同一键在未命中时被大量重复回源。关闭缓存会加剧回源；集中过期时间会引发同时失效；缩短过期时间会增加回源频率。

### single_choice · None



- [A] 缓存命中率提高，因为多了字段
- [B] 缓存结果仍可复用于相同输入，但请求 ID 会造成误导
- [C] 缓存键会自动忽略该字段
- [D] 请求 ID 会让缓存永久失效

**参考答案**：1

**解析**：请求 ID 不影响主要结果的可复用性，但会随每次调用变化，若出现在结果中会造成混淆甚至误导。它不会自动被忽略，也不应导致永久失效。

### single_choice · None



- [A] 大量请求查询不存在的数据，导致每次都绕过缓存去回源
- [B] 缓存条目同时过期导致回源激增
- [C] 缓存键冲突导致结果被覆盖
- [D] 缓存容量不足触发大量淘汰

**参考答案**：0

**解析**：缓存穿透指请求的数据不存在，缓存无条目可命中，每次都回源。集中过期属于雪崩，键冲突属于键设计问题，容量不足属于淘汰问题。

### single_choice · None



- [A] 对同一段静态提示词的向量化结果
- [B] 对同一知识库文档的嵌入向量
- [C] 每次都需要唯一且不可重复的交易流水号
- [D] 对同一工具 schema 的校验结果

**参考答案**：2

**解析**：唯一且不可重复的交易流水号必须每次生成新值，不能复用缓存。静态提示词向量、文档嵌入和监督 schema 校验结果都属于可复用的确定性结果。

### single_choice · None



- [A] 放弃缓存整个响应
- [B] 将易变字段从缓存内容中剥离或仅在展示时注入
- [C] 每次命中后重新调用模型刷新时间字段
- [D] 把时间字段加入缓存键

**参考答案**：1

**解析**：将易变字段与稳定内容分离，可以让稳定部分继续复用，同时避免陈旧时间。放弃缓存过于极端；命中后重新调用模型失去缓存意义；把时间加入键会导致永远不命中。

### single_choice · None



- [A] 缓存命中率立刻降为 0
- [B] 内存或存储持续增长，最终耗尽资源
- [C] 所有缓存条目立即过期
- [D] 缓存键自动失效

**参考答案**：1

**解析**：无限容量意味着条目只增不减，资源会持续增长并最终耗尽。它与命中率、过期时间和键的有效性没有直接必然关系。

### single_choice · None



- [A] 缓存与数据源之间天然强一致，无需额外处理
- [B] 缓存通常追求最终一致，需要在数据变更时主动失效或更新
- [C] 只要读取速度够快，就不需要考虑一致性
- [D] 一致性只与写入频率有关，与读取无关

**参考答案**：1

**解析**：缓存通常是数据源的副本，难以天然强一致，常见做法是接受最终一致并在变更时主动失效或更新。读取速度与一致性是两回事。

### single_choice · None



- [A] 使用对象的默认字符串表示直接作为键
- [B] 对输入做规范化后计算稳定哈希作为键
- [C] 每次请求都生成新的随机键
- [D] 只用输入长度作为键

**参考答案**：1

**解析**：规范化后计算稳定哈希，可以让语义相同的输入映射到同一键。默认字符串表示可能包含内存地址等不稳定内容；随机键无法命中；只用长度会严重冲突。

### single_choice · None



- [A] 缓存键字符数
- [B] 回源计算节省的时间与缓存读写开销的对比
- [C] 缓存服务器的外观颜色
- [D] 缓存条目的创建顺序

**参考答案**：1

**解析**：缓存收益取决于节省的回源计算时间是否大于缓存读写的额外开销。命中率只是其中一环，键字符数、外观和创建顺序都不是核心指标。

### single_choice · None



- [A] 每次调用都依赖当前精确到毫秒的时间戳生成结果
- [B] 对同一篇固定文档反复进行相同的摘要抽取
- [C] 需要根据用户最新输入实时生成个性化回复
- [D] 涉及随机数种子每次都不同的采样过程

**参考答案**：1

**解析**：固定文档上的相同抽取操作输入稳定、结果可复用，适合缓存。依赖毫秒时间戳、实时个性化输入或随机采样每次都不同，缓存命中率极低甚至结果不可复用。

### single_choice · None



- [A] 只要设置了过期时间，就永远不会返回过期数据
- [B] 当底层数据发生变化时，应使相关缓存条目失效或更新
- [C] 缓存一旦写入就不应再被删除，以保证命中率
- [D] 失效策略只影响性能，不影响结果正确性

**参考答案**：1

**解析**：底层数据变更后若继续使用旧缓存，会返回过期结果，因此需要失效或更新。过期时间只是降低过期概率；不删除会放大陈旧数据问题；失效策略不当会直接导致结果错误，而不只是性能问题。

### single_choice · None



- [A] 缓存永远不会命中
- [B] 可能返回最多 24 小时前的陈旧汇率
- [C] 接口调用次数反而增加
- [D] 缓存键会自动更新为新的汇率

**参考答案**：1

**解析**：过期时间远大于数据更新频率时，缓存会在数据已更新后继续返回旧值，导致陈旧数据。过期时间应参考数据变化频率来设定。

### single_choice · None



- [A] 影响输出结果的输入参数
- [B] 请求发生时的随机唯一追踪号
- [C] 使用的模型或工具版本标识
- [D] 影响结果的配置项

**参考答案**：1

**解析**：随机唯一追踪号每次请求都不同，会导致缓存永远无法命中，属于把不影响结果的信息纳入键的典型错误。影响输出的参数、版本和配置都应纳入键以保证正确性。

### single_choice · None



- [A] 缓存过期时间太短
- [B] 缓存键未包含用户或权限等隔离维度
- [C] 缓存容量太小导致频繁淘汰
- [D] 缓存写入速度太慢

**参考答案**：1

**解析**：当结果包含用户私有数据时，缓存键必须包含用户或权限等隔离维度，否则会跨用户串数据。过期时间、容量和写入速度不影响隔离性。

### single_choice · None



- [A] 命中率越高一定代表系统正确性越好
- [B] 在结果可复用的前提下，提高命中率通常能减少重复计算与延迟
- [C] 命中率只与缓存容量有关，与请求分布无关
- [D] 命中率为 100% 意味着不需要任何失效策略

**参考答案**：1

**解析**：在结果可复用的前提下，高命中率减少重复计算、降低延迟。但命中率不直接等于正确性；命中率受请求分布和键设计影响；即使命中率 100%，底层数据变更时仍需失效。

### single_choice · None



- [A] 永不淘汰任何条目，直到存储写满报错
- [B] 采用淘汰策略，优先淘汰最近最少使用的条目
- [C] 只缓存最短的结果，忽略较长结果
- [D] 把所有条目都复制多份以提高读取速度

**参考答案**：1

**解析**：空间有限时需要淘汰策略，LRU 等策略能保留更可能被再次访问的条目。永不淘汰会导致写满；只按长度筛选会忽略访问模式；复制多份浪费空间。

### single_choice · None



- [A] 对一个固定知识库的相同查询
- [B] 对同一段文本的相同格式转换
- [C] 结果依赖实时外部状态且该状态随时可能变化
- [D] 对同一组参数的确定性计算

**参考答案**：2

**解析**：当结果依赖实时变化的外部状态时，相同输入在不同时刻应得到不同结果，缓存会返回过期数据。前三类中固定知识库、格式转换和确定性计算都适合缓存。

### single_choice · None



- [A] 该状态码表示请求参数不合法，应立即修改 prompt 后重试
- [B] 该状态码通常表示请求速率超过配额，应在等待一段时间后重试
- [C] 该状态码表示认证失败，应检查 API Key 是否正确
- [D] 该状态码表示服务器内部错误，应无限立即重试直到成功

**参考答案**：1

**解析**：HTTP 429 是 Too Many Requests，表示客户端在单位时间内发送请求过多，通常配合 Retry-After 头，正确做法是退避等待后重试。400 才是参数错误，401 是认证失败，5xx 是服务端错误。

### single_choice · None



- [A] 实现起来更复杂，容易出错
- [B] 多个客户端会同时重试造成同步冲击，加剧限流
- [C] 固定间隔会消耗更多内存
- [D] 固定间隔无法配合任何 HTTP 状态码使用

**参考答案**：1

**解析**：固定间隔重试会让大量客户端在同一时刻再次发起请求，形成同步的流量峰值，使限流雪上加霜。指数退避并加入随机抖动可以错开重试时刻，降低碰撞概率。

### multi_choice · None



- [A] 指数退避加随机抖动重试
- [B] 在客户端或网关侧做请求速率限制
- [C] 使用共享存储实现多实例的统一限流
- [D] 把失败请求无限次立即重发

**参考答案**：[0, 1, 2]

**解析**：退避重试、客户端/网关限流、共享存储统一限流都是标准手段。无限次立即重发会加剧限流，是反模式。

### multi_choice · None



- [A] 固定窗口在窗口边界可能出现瞬时双倍流量
- [B] 滑动窗口比固定窗口能更平滑地反映真实速率
- [C] 令牌桶允许一定程度的突发流量
- [D] 漏桶强制以恒定速率流出，通常不允许突发

**参考答案**：[0, 1, 2, 3]

**解析**：固定窗口边界问题确实存在瞬时翻倍；滑动窗口统计更平滑；令牌桶允许突发；漏桶以恒定速率处理更强调平滑输出。四项均正确。

### multi_choice · None



- [A] 服务端返回 429 限流
- [B] 网络连接超时等瞬时错误
- [C] 服务端返回 5xx 且属于可恢复的瞬时故障
- [D] 请求参数错误返回 400
- [E] 认证失败返回 401

**参考答案**：[0, 1, 2]

**解析**：429、超时和瞬时 5xx 通常可重试。400/401 属于请求本身有问题（参数错、认证错），重试不会成功，应先修正而不是重试。

### multi_choice · None



- [A] 每单位时间允许的最大请求数
- [B] 单次请求允许消耗的 token 上限
- [C] 最大重试次数与退避上限
- [D] 网络延迟造成的并发在途请求数

**参考答案**：[0, 1, 2, 3]

**解析**：限流可能同时按请求数和 token 数计费/配额，重试上限和退避上限决定失败时行为，并发在途数影响资源占用。四者都需纳入设计。

### fill_blank · None



**参考答案**：["jitter", "随机抖动", "抖动", "random jitter"]

**解析**：该技术即 jitter（抖动），把各客户端的重试时刻打散，避免同步冲击。

### fill_blank · None



**参考答案**：["429", "429 Too Many Requests", "Too Many Requests"]

**解析**：429 是标准的限流/过多请求状态码，常配合 Retry-After 使用。

### code_reading · None



**参考答案**：等待时间分别为 1、2、4 秒（2 的 0、1、2 次方）。这属于指数退避；代码优先使用服务端给的 retry_after，缺失时退化为指数退避。

**解析**：2**i 在 i=0,1,2 时为 1,2,4，呈指数增长，即指数退避。真实工程中通常还会加入随机抖动。

### code_reading · None



**参考答案**：在途请求数上限从 5 提高到 40，几乎等于全部并发发起，触发服务端限流的可能性显著增大；并发控制实际失去了限流作用。

**解析**：信号量限制的是同时在途请求数。值设得过大会让并发数逼近任务总数，无法有效削峰，从而更容易触发限流。

### scenario · None



**解析**：改进方向包括：采用指数退避并加入随机抖动以错开重试时刻；尊重 Retry-After；设置最大重试次数和退避上限；在客户端/网关做速率限制或排队削峰，避免同步冲击。

### single_choice · None



- [A] 令牌桶不允许任何突发流量，只能按固定速率放行
- [B] 令牌桶以固定速率补充令牌，桶满时多余的令牌被丢弃，请求需要消耗令牌
- [C] 令牌桶的桶容量越小，允许的突发流量越大
- [D] 令牌桶只能在服务端使用，客户端无法实现

**参考答案**：1

**解析**：令牌桶按固定速率生成令牌并存入容量有限的桶，请求到来时取走令牌，取不到则被限流或被排队。桶容量决定了可容忍的突发量，容量越大突发能力越强。客户端也可实现该算法做自我保护。

### single_choice · None



- [A] 两者完全等价，选择哪个都一样
- [B] 限流约束的是单位时间内的请求数量，并发控制约束的是同一时刻在途的请求数量
- [C] 并发控制只能限制每秒请求数，无法限制在途数
- [D] 限流只作用于客户端，并发控制只作用于服务端

**参考答案**：1

**解析**：限流关注时间窗口内的速率（例如每秒 N 个请求），并发控制关注同时未完成请求的数量（例如最多 5 个在途）。两者互补，常常同时使用。

### single_choice · None



- [A] 忽略该头，立即重试
- [B] 优先按 Retry-After 指示的时间等待后再重试，而不是用自己估算的时间
- [C] 直接把请求丢弃，永不重试
- [D] 把 Retry-After 的值当作已重试次数累计

**参考答案**：1

**解析**：Retry-After 是服务端明确告知客户端应等待多久的机制，尊重它可以避免无效重试造成的额外限流，通常比客户端自行估算更准确。

### single_choice · None



- [A] 为了让等待时间看起来更随机，方便调试
- [B] 为了避免大量客户端在相同的退避时刻同时重试，造成新的流量高峰
- [C] 随机抖动可以减少网络延迟
- [D] 随机抖动可以增加 API Key 的有效期限

**参考答案**：1

**解析**：如果所有客户端都使用纯指数退避，退避时间可能相同，导致它们再次同时发起请求。加入随机抖动把这些时刻打散，平滑整体流量。

### single_choice · None



- [A] 重试次数应设置为无限，直到成功为止
- [B] 应设置最大重试次数，避免在持续故障或长期限流时无限占用资源
- [C] 重试次数越多越好，越多越能保证最终成功
- [D] 只要使用了退避，就不需要设置上限

**参考答案**：1

**解析**：无限重试会在服务长期不可用或持续限流时耗尽线程、连接和配额。设置上限并配合退避和熔断是更稳妥的做法。

### single_choice · None



- [A] 一次性并发发起全部请求，靠重试兜底
- [B] 把请求分散到时间上（如控制发送速率或使用队列），并配合退避重试
- [C] 缩小每次请求的 prompt 长度，这样就不会被限流
- [D] 更换网络环境即可绕过限流

**参考答案**：1

**解析**：限流基于请求数量/速率，分散发送（速率控制、队列）能从源头降低触发概率。缩小 prompt 主要影响 token 配额而非请求数限流，更换网络环境不属于合理工程手段。

### single_choice · None



- [A] 本地计数器无法统计请求数量
- [B] 每个实例独立计数，整体实际放行量会超过预期，限流不准
- [C] 本地内存计数器会使 API 返回 500
- [D] 本地计数器只能统计 GET 请求

**参考答案**：1

**解析**：本地计数只约束单个实例，多实例叠加后总量会突破全局限额。要用全局视角限流通常需要共享存储（如 Redis）或集中式限流服务。

### single_choice · None



- [A] 限流后立刻返回错误，让上游无限制地继续快速重发
- [B] 限流后进入队列排队、返回友好提示或使用降级结果，避免请求雪崩
- [C] 限流后把请求全部丢弃且不记录任何日志
- [D] 限流后修改 API 地址以绕过限制

**参考答案**：1

**解析**：合理的降级包括排队、快速失败并提示、返回缓存/降级内容，同时记录日志便于观测。无限制快速重发或丢弃不记录都不利于稳定性和可观测性。
