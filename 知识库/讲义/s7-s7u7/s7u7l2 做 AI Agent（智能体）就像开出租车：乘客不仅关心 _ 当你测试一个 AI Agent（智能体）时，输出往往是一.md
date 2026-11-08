# s7u7l2 做 AI Agent（智能体）就像开出租车：乘客不仅关心 / 当你测试一个 AI Agent（智能体）时，输出往往是一

> 来源 `content/lessons/s7u7l2.json`

## agent.eval.cost_latency

## 一句话直觉
做 AI Agent（智能体）就像开出租车：乘客不仅关心你能不能送到（效果），还关心你烧了多少油（成本 cost）和花了多长时间（延迟 latency）。**agent.eval.cost_latency** 就是教你如何量化、对比和优化这两项指标。

---

## 1. 为什么成本和延迟是 Agent 的“硬约束”

Agent 通常要调用多次 LLM（大语言模型 Large Language Model）、工具（tool）、检索（retrieval）。每一步都会产生 token（词元）消耗和网络往返时间。

- **成本**：按 token 计费，输入 + 输出都收费。
- **延迟**：用户等待时间，直接影响体验。
- **评估（evaluation）**：不能只看“答得对不对”，还要看“花了多少钱、等了多少秒”。

> 关键结论：一个 Agent 的评估向量至少是三维的：质量、成本、延迟。

```python
# 用一个简单字典模拟一次 Agent 调用的“账单”
call_record = {
    "input_tokens": 1200,   # 输入词元数
    "output_tokens": 300,   # 输出词元数
    "price_in": 0.000003,   # 每输入 token 单价（美元）
    "price_out": 0.000015,  # 每输出 token 单价（美元）
    "latency_ms": 2400      # 本次调用耗时（毫秒）
}

cost = call_record["input_tokens"] * call_record["price_in"] + \
       call_record["output_tokens"] * call_record["price_out"]
print(f"本次成本: ${cost:.6f}, 延迟: {call_record['latency_ms']} ms")
```

---

## 2. 成本怎么算：token 是货币

LLM 的计费单位是 token。不同模型价格不同，输入和输出价格也不同。

- **输入 token**：你发给模型的提示（prompt）、上下文、工具返回结果。
- **输出 token**：模型生成的内容。
- **总成本 = 输入 token × 输入单价 + 输出 token × 输出单价**。

> 关键结论：优化成本的第一手段是减少不必要的上下文和输出长度。

```python
# 计算多个模型完成同一任务的成本对比
models = {
    "gpt-4o":      {"in": 0.0000025, "out": 0.000010},
    "gpt-4o-mini": {"in": 0.00000015, "out": 0.0000006},
}
input_tokens, output_tokens = 2000, 500

for name, p in models.items():
    cost = input_tokens * p["in"] + output_tokens * p["out"]
    print(f"{name}: ${cost:.6f}")
```

---

## 3. 延迟怎么量：从单步到端到端

延迟（latency）通常用毫秒（ms）或秒（s）表示。Agent 的延迟不是单次 LLM 调用，而是所有步骤之和。

- **单步延迟**：一次 LLM 调用或一次工具调用。
- **端到端延迟（end-to-end latency）**：用户从提问到收到最终答案的总时间。
- **首 token 延迟（time to first token, TTFT）**：流式输出时用户看到第一个字的时间。

> 关键结论：Agent 的延迟 ≈ 各步骤延迟之和 + 调度开销。并行化是降低延迟的关键。

```python
import time

def fake_llm_call(ms):
    """模拟一次耗时 ms 毫秒的 LLM 调用"""
    time.sleep(ms / 1000)
    return f"done in {ms}ms"

start = time.perf_counter()
# 模拟 Agent 的三个串行步骤
fake_llm_call(500)   # 规划
fake_llm_call(800)   # 工具调用
fake_llm_call(600)   # 总结
end = time.perf_counter()
print(f"端到端延迟: {(end - start) * 1000:.0f} ms")
```

---

## 4. 把成本和延迟写进评估函数

评估（evaluation）要可重复、可比较。我们定义一个函数，输入是 Agent 运行记录，输出是质量、成本、延迟三元组。

> 关键结论：评估指标必须和业务目标对齐，比如“成本 < $0.01 且延迟 < 3s 且准确率 > 90%”。

```python
def evaluate_agent(record, quality_score):
    """record: 包含 token 和延迟的字典; quality_score: 0~1 的质量分"""
    cost = record["input_tokens"] * record["price_in"] + \
           record["output_tokens"] * record["price_out"]
    latency_s = record["latency_ms"] / 1000
    return {"quality": quality_score, "cost_usd": round(cost, 6), "latency_s": round(latency_s, 3)}

result = evaluate_agent({
    "input_tokens": 1500, "output_tokens": 400,
    "price_in": 0.0000025, "price_out": 0.000010,
    "latency_ms": 2200
}, quality_score=0.92)
print(result)
```

---

## 5. 优化策略：又快又省的常见手段

- **缓存（cache）**：相同问题不重复调用。
- **模型路由（model routing）**：简单任务用小模型，复杂任务用大模型。
- **并行工具调用**：多个独立工具同时执行。
- **提示压缩（prompt compression）**：减少输入 token。
- **流式输出（streaming）**：降低用户感知延迟。

> 关键结论：成本和延迟往往需要权衡（trade-off），没有免费的午餐。

```python
# 用缓存模拟：同一个问题第二次调用成本为 0
cache = {}
def cached_agent(question, answer_fn):
    if question in cache:
        return cache[question], 0.0  # 缓存命中，成本 0
    answer = answer_fn(question)
    cache[question] = answer
    return answer, 0.001  # 模拟一次调用成本

ans, c1 = cached_agent("什么是 Agent?", lambda q: "智能体")
ans2, c2 = cached_agent("什么是 Agent?", lambda q: "智能体")
print(f"第一次成本: ${c1}, 第二次成本: ${c2}")
```

---

## 动手练习

**任务**：写一个 Python 脚本 `agent_eval.py`，完成以下功能：

1. 定义一个列表 `runs`，包含 5 次 Agent 运行记录，每条记录有 `input_tokens`、`output_tokens`、`price_in`、`price_out`、`latency_ms`、`quality`。
2. 写一个函数 `evaluate(runs)`，返回：
   - 平均成本（美元）
   - 平均延迟（秒）
   - 平均质量分
   - 成本最低的那次运行的索引
3. 打印结果，并判断是否满足：平均成本 < $0.005、平均延迟 < 2.0s、平均质量 > 0.85。

**提示**：可以用 `sum()` 和列表推导式。完成后，试着把其中一次运行的 `input_tokens` 减半，观察成本变化。

```python
import time

# 模拟一次 Agent 调用的评估
record = {
    "input_tokens": 1500,
    "output_tokens": 400,
    "price_in": 0.0000025,   # 每输入 token 单价（美元）
    "price_out": 0.000010,   # 每输出 token 单价（美元）
    "latency_ms": 2200,
    "quality": 0.92
}

def evaluate(r):
    cost = r["input_tokens"] * r["price_in"] + r["output_tokens"] * r["price_out"]
    latency_s = r["latency_ms"] / 1000
    return {"quality": r["quality"], "cost_usd": round(cost, 6), "latency_s": round(latency_s, 3)}

print(evaluate(record))

# 模拟串行 Agent 步骤的端到端延迟
def fake_llm_call(ms):
    time.sleep(ms / 1000)
    return f"done in {ms}ms"

start = time.perf_counter()
fake_llm_call(300)
fake_llm_call(500)
fake_llm_call(400)
end = time.perf_counter()
print(f"端到端延迟: {(end - start) * 1000:.0f} ms")

# 缓存降低重复成本
cache = {}
def cached_agent(question, answer_fn):
    if question in cache:
        return cache[question], 0.0
    answer = answer_fn(question)
    cache[question] = answer
    return answer, 0.001

_, c1 = cached_agent("什么是 Agent?", lambda q: "智能体")
_, c2 = cached_agent("什么是 Agent?", lambda q: "智能体")
print(f"第一次成本: ${c1}, 第二次成本: ${c2}")
```

## agent.eval.llm_as_judge

## 一句话直觉
当你测试一个 AI Agent（智能体）时，输出往往是一段自然语言、一份推理过程，而不是一个简单的对/错标签。**LLM-as-Judge**（大语言模型作为裁判）就是让另一个大模型来给这些开放性输出打分、排序或挑错，从而把“主观质量”变成可批量复现的评测信号。

---

## 1. 为什么需要 LLM-as-Judge

传统评测像 `assert output == "2"` 只适合闭式答案。Agent 的输出常包含：
- 多步推理是否自洽；
- 工具调用顺序是否合理；
- 最终回答是否满足用户意图。

人工逐条打分成本高，规则匹配覆盖不全，因此用 LLM 当裁判成为工程上的折中：**比人工便宜，比字符串匹配灵活**。

```python
# 先看一个最小对比：规则评测 vs LLM 裁判
rule_score = int("北京是中国的首都" in "中国的首都是北京")
print(rule_score)  # 0，规则太死

# LLM 裁判会判断“语义是否一致”，而不是只做子串匹配
```

---

## 2. 最小可运行架构：输入、裁判、输出

一个 LLM-as-Judge 评测器通常包含三部分：
1. **待评样本**：问题、Agent 输出、参考答案或评分标准；
2. **裁判提示词**：告诉裁判模型按什么维度打分；
3. **结构化输出**：让裁判返回 JSON，便于程序解析和统计。

```python
import json

def build_judge_prompt(question, agent_answer, reference):
    return f"""你是严格的评测裁判。请根据参考答案判断 Agent 回答是否正确。
只输出 JSON，格式为 {{"score": 0 或 1, "reason": "一句话理由"}}。

问题：{question}
Agent 回答：{agent_answer}
参考答案：{reference}
"""
```

关键点：**强迫裁判输出 JSON**，否则后续无法稳定聚合。

---

## 3. 三种常见评测模式

工程里最常用的 LLM-as-Judge 模式有三类：
- **打分（Scoring）**：给 1~5 分或 0/1；
- **成对比较（Pairwise Comparison）**：给两个回答选更好的；
- **清单检查（Checklist / Rubric）**：按多个维度逐项判断。

```python
RUBRIC = [
    "是否直接回答了用户问题",
    "是否没有编造不存在的事实",
    "表达是否清晰、无多余重复",
]

def build_rubric_prompt(question, answer):
    items = "\n".join(f"{i+1}. {r}" for i, r in enumerate(RUBRIC))
    return f"""请按以下清单评估回答，每项输出 pass 或 fail，并给整体 score(0-1)。
只输出 JSON：{{"items": ["pass/fail", ...], "score": 0.x, "reason": "..."}}

问题：{question}
回答：{answer}
清单：
{items}
"""
```

这种模式比单一总分更可解释，适合迭代 Agent 提示词。

---

## 4. 用代码跑一次 LLM-as-Judge

下面示例不依赖真实 API，用一个假的裁判函数模拟模型返回，重点展示**评测流水线**：批量样本 -> 裁判 -> 解析 -> 汇总。

```python
import json

def fake_judge(prompt: str) -> str:
    # 模拟裁判模型：真实场景可替换为 openai.chat.completions.create
    if "北京" in prompt and "中国首都" in prompt:
        return json.dumps({"score": 1, "reason": "语义一致"}, ensure_ascii=False)
    return json.dumps({"score": 0, "reason": "与参考答案不一致"}, ensure_ascii=False)

def evaluate(samples):
    results = []
    for s in samples:
        prompt = build_judge_prompt(s["q"], s["a"], s["ref"])
        raw = fake_judge(prompt)
        parsed = json.loads(raw)
        results.append({**s, **parsed})
    return results

samples = [
    {"q": "中国首都是哪里？", "a": "北京", "ref": "北京"},
    {"q": "中国首都是哪里？", "a": "上海", "ref": "北京"},
]
for r in evaluate(samples):
    print(r["a"], r["score"], r["reason"])
```

---

## 5. 工程级注意事项

要把 LLM-as-Judge 用到生产评测，至少要处理四件事：
- **裁判偏差**：位置偏差、长度偏好、自我偏好，需要用交换顺序、多次投票缓解；
- **校准**：用人工标注的小样本验证裁判与人类一致性；
- **成本与缓存**：相同 prompt 缓存结果，批量并发；
- **可复现**：固定模型版本、temperature=0、记录完整 prompt。

```python
# 位置偏差缓解：交换 A/B 顺序各评一次

def pairwise_judge(a, b, judge_fn):
    r1 = judge_fn(a, b)  # 返回 'A' 或 'B'
    r2 = judge_fn(b, a)  # 交换顺序
    # 只有两次都不偏袒同一位置，才认为结果稳定
    return r1, r2
```

记住：**LLM-as-Judge 不是真理，它是一个需要被评测的评测器**。

```python
import json

# 一个可运行的 LLM-as-Judge 最小示例（用假裁判模拟模型输出）
RUBRIC = [
    "是否直接回答了用户问题",
    "是否没有编造不存在的事实",
    "表达是否清晰、无多余重复",
]

def build_rubric_prompt(question, answer):
    items = "\n".join(f"{i+1}. {r}" for i, r in enumerate(RUBRIC))
    return f"""请按以下清单评估回答，每项输出 pass 或 fail，并给整体 score(0-1)。
只输出 JSON：{{"items": ["pass/fail", ...], "score": 0.x, "reason": "..."}}

问题：{question}
回答：{answer}
清单：
{items}
"""

def fake_judge(prompt: str) -> str:
    # 模拟裁判模型：真实场景替换为真实 LLM API 调用
    if "北京" in prompt:
        return json.dumps({
            "items": ["pass", "pass", "pass"],
            "score": 1.0,
            "reason": "回答正确且简洁"
        }, ensure_ascii=False)
    return json.dumps({
        "items": ["pass", "fail", "pass"],
        "score": 0.3,
        "reason": "事实错误"
    }, ensure_ascii=False)

def evaluate(samples):
    results = []
    for s in samples:
        prompt = build_rubric_prompt(s["q"], s["a"])
        raw = fake_judge(prompt)
        parsed = json.loads(raw)
        results.append({**s, **parsed})
    return results

if __name__ == "__main__":
    samples = [
        {"q": "中国首都是哪里？", "a": "北京"},
        {"q": "中国首都是哪里？", "a": "上海"},
    ]
    for r in evaluate(samples):
        print(r["a"], r["score"], r["reason"])
```


---

## 本课题目

### single_choice · None



- [A] 只统计每次请求消耗的 token 数量，不考虑响应时间
- [B] 只测量平均响应时间，不记录 token 消耗或调用次数
- [C] 在记录每次任务成功率的同时，分别统计 token 消耗、API 调用次数和端到端响应时间
- [D] 只关注模型参数量，因为参数量同时决定了成本和延迟

**参考答案**：2

**解析**：成本和延迟是多维指标，评估时应同时记录资源消耗（如 token、调用次数）和时间指标（端到端延迟），并可与任务质量指标一起分析。A、B 都只覆盖单一维度；D 把参数量当作唯一决定因素，忽略了推理框架、批处理、缓存等因素。

### single_choice · None



- [A] 平均延迟低说明系统稳定，P99 高可以忽略
- [B] 少数请求可能触发了长尾路径（如多次工具调用、重试或大模型长输出），拉高了尾部延迟
- [C] P99 延迟高一定是网络问题，与智能体逻辑无关
- [D] 平均延迟和 P99 延迟不可能同时出现这种组合

**参考答案**：1

**解析**：平均值容易被大量快请求拉低，而 P99 反映最慢的 1% 请求。智能体中长尾可能来自工具调用链变长、重试、上下文膨胀等。A 忽略了用户体验；C 过于绝对；D 与事实不符。

### single_choice · None



- [A] 测量从请求发出到收到第一个 token 的时间，并把它当作完整响应时间
- [B] 测量端到端完整响应时间
- [C] 在多种网络条件下测量延迟
- [D] 记录 P50、P95、P99 等多个分位数

**参考答案**：0

**解析**：首 token 时间只反映开始响应的时间，不代表完整回答生成完毕。若把它当作完整延迟，会低估用户实际等待时间。B、C、D 都是更全面的做法。

### single_choice · None



- [A] 这两个指标可以互相替代
- [B] 它们分别反映资源效率和时间效率，需要结合业务场景一起看
- [C] 只要成本低，延迟再高也可以接受
- [D] 只要延迟低，成本再高也可以接受

**参考答案**：1

**解析**：成本和延迟是不同维度，不能互相替代。业务场景决定哪个更重要，通常需要综合权衡，而不是只看其中一个。

### single_choice · None



- [A] 减少提示词长度
- [B] 增加不必要的工具调用和重试次数
- [C] 启用结果缓存
- [D] 降低输出最大 token 数

**参考答案**：1

**解析**：不必要的工具调用和重试既消耗额外资源，也增加等待时间。A、C、D 通常有助于降低成本或延迟。

### single_choice · None



- [A] 合并后无法再分析延迟瓶颈，但总延迟仍有参考价值
- [B] 合并后总延迟一定不准确
- [C] 工具调用时间不属于延迟
- [D] 模型推理时间不属于延迟

**参考答案**：0

**解析**：总延迟有整体参考价值，但若不分段记录，就难以定位瓶颈（是模型慢还是工具慢）。B 过于绝对；C、D 都错误，两者都属于端到端延迟的组成部分。

### single_choice · None



- [A] 离线批处理任务，用户对完成时间不敏感
- [B] 实时客服场景，用户等待时间要求严格，且预算允许
- [C] 内部测试环境，没有任何用户
- [D] 模型训练阶段，不涉及推理

**参考答案**：1

**解析**：用更高成本换取更低延迟，通常在延迟敏感且预算允许的场景下合理。A、C、D 对延迟不敏感或不涉及在线推理，通常不适用。

### single_choice · None



- [A] 优化最常见路径的提示词
- [B] 为长尾请求设置超时、限制重试次数并优化慢工具
- [C] 降低所有请求的输出长度
- [D] 增加平均响应时间

**参考答案**：1

**解析**：P99 反映长尾，改进方向应针对导致长尾的因素，如超时、重试、慢工具。A 主要影响常见路径；C 可能影响整体但不针对长尾；D 与目标相反。

### single_choice · None



- [A] 每秒处理请求数
- [B] 完成每个任务的平均费用
- [C] 首次响应时间
- [D] 模型准确率

**参考答案**：1

**解析**：成本效率关注单位任务的花费，平均每任务费用最直接。A 是吞吐，C 是延迟，D 是质量指标。

### single_choice · None



- [A] 缓存对延迟没有影响
- [B] 即使命中率低，命中的那些请求也可能恰好是高延迟请求，从而拉低平均延迟
- [C] 缓存命中率低说明延迟一定上升
- [D] 缓存只能降低成本，不能降低延迟

**参考答案**：1

**解析**：缓存命中可以跳过昂贵计算，即使命中率不高，若命中的是慢请求，也可能明显改善平均或尾部延迟。A、C、D 都过于绝对或错误。

### single_choice · None



- [A] 只记录全局总成本
- [B] 按任务类型或意图分组统计平均成本和延迟
- [C] 只记录成功任务的总数
- [D] 只记录模型的版本号

**参考答案**：1

**解析**：按任务类型分组可以定位哪类任务消耗异常。只记录全局总成本或成功数无法细分问题来源，模型版本号与成本异常无直接关系。

### single_choice · None



- [A] 成本和延迟是唯一影响满意度的因素
- [B] 回答质量、准确性或交互体验可能存在问题
- [C] 只要成本和延迟达标，满意度必然高
- [D] 用户满意度与智能体无关

**参考答案**：1

**解析**：成本和延迟只是效率指标，用户满意度还受回答质量、准确性、语气、交互流畅度等影响。A、C、D 都忽略了质量维度。

### single_choice · None



- [A] 模型文件在磁盘上的大小
- [B] 完成一次任务所消耗的 token 总数与外部 API 调用次数
- [C] 模型训练时使用的 GPU 数量
- [D] 开发人员编写提示词所花的时间

**参考答案**：1

**解析**：单次任务成本通常由 token 消耗、外部调用次数、工具执行费用等构成。A 是部署占用，C 是训练成本，D 是人力成本，都不直接等于单次任务运行成本。

### single_choice · None



- [A] 只给出一个综合分数，不展示分项
- [B] 同时展示成本、延迟和质量指标，并标注不同方案在权衡曲线上的位置
- [C] 只展示成本最低的方案
- [D] 只展示延迟最低的方案

**参考答案**：1

**解析**：决策者需要看到多维度指标及取舍关系，才能根据业务目标选择方案。只给综合分或单一最优指标会丢失权衡信息。

### single_choice · None



- [A] 增加提示词长度，让模型更详细地思考
- [B] 对常见问题使用缓存，并精简系统提示与上下文
- [C] 把所有请求都改成串行执行
- [D] 提高温度参数，让输出更长

**参考答案**：1

**解析**：缓存可避免重复计算，精简提示和上下文可减少输入 token 与推理时间，因此可能同时降低成本与延迟。A、D 会增加 token 和延迟；C 串行化通常增加延迟。

### single_choice · None



- [A] 离线批量生成年度报告
- [B] 实时语音助手需要即时回应用户
- [C] 夜间定时数据清洗任务
- [D] 模型微调训练过程

**参考答案**：1

**解析**：实时交互场景对响应时间敏感，延迟直接影响用户体验。离线批处理、定时任务和训练过程通常更关注吞吐或成本，对单次延迟要求较低。

### single_choice · None



- [A] 无法计算单次请求的平均成本，难以比较不同方案的效率
- [B] 总成本会变得不准确
- [C] 请求数量对成本没有影响
- [D] 无法测量延迟

**参考答案**：0

**解析**：只有总量而没有请求数，就无法得到单位成本（如每次请求成本），不同规模或不同调用量的方案之间难以公平比较。总成本本身仍可记录，只是缺少归一化信息。

### single_choice · None



- [A] 一个方案用简单任务测试，另一个用复杂任务测试
- [B] 使用相同的一组任务、相同的硬件环境和相同的并发条件进行测试
- [C] 只测试延迟，不测试成本
- [D] 只测试成本，不测试延迟

**参考答案**：1

**解析**：公平比较要求控制变量：任务集、硬件、并发、网络等条件应一致。A 引入任务难度差异；C、D 都只覆盖单一维度。

### single_choice · None



- [A] 延迟降低，成本可能上升
- [B] 延迟和成本都必然降低
- [C] 延迟上升，成本必然下降
- [D] 延迟和成本都不受影响

**参考答案**：0

**解析**：并行化可以缩短等待时间，但更多外部调用通常增加费用或资源消耗。因此常见权衡是延迟下降、成本上升，而不是两者必然同降。

### single_choice · None



- [A] 每次任务消耗的 token 数
- [B] 从收到用户请求到返回完整回答所经过的时间
- [C] 模型文件占用的磁盘空间
- [D] 每千次调用的费用

**参考答案**：1

**解析**：延迟衡量时间，端到端响应时间属于延迟指标。A、D 属于成本相关指标，C 属于存储占用，不是延迟。

### single_choice · None



- [A] 成本与对话轮数无关，一定是统计错误
- [B] 随着对话轮数增加，上下文变长，每次请求需要处理的 token 增多，导致成本上升
- [C] 对话轮数增加会降低 token 消耗
- [D] 只要模型不变，成本就不会变化

**参考答案**：1

**解析**：多轮对话中，历史消息通常会作为上下文重复发送，导致每轮输入 token 增长，累计成本上升。A、C、D 都与常见现象不符。

### single_choice · None



- [A] 用人工标注员逐条打分，再训练一个分类器替代人工
- [B] 让另一个大语言模型根据给定标准对智能体的输出进行评分或判定
- [C] 用精确字符串匹配来判断智能体输出是否正确
- [D] 统计智能体输出的 token 数量作为质量指标

**参考答案**：1

**解析**：LLM as Judge 的本质是用一个大语言模型充当评委，依据评分标准（rubric）对输出做质量判定。字符串匹配、token 统计都不属于 LLM 评判；训练分类器替代人工属于另一类做法。

### single_choice · None



- [A] 减少评委模型需要生成的 token 数量以节省成本
- [B] 让评委模型的输出更随机，从而覆盖更多情况
- [C] 让评分维度明确、可复现，减少评委的主观随意性
- [D] 强迫评委模型只能输出单个字符

**参考答案**：2

**解析**：提供明确的评分标准能让评判维度清晰、标准统一，提高评分的一致性与可复现性，而不是为了省 token 或增加随机性。

### multi_choice · None



- [A] 位置偏差：评分受候选项排列顺序影响
- [B] 长度偏差：偏好更冗长的回答
- [C] 自我偏好：评委偏爱与自己风格相似的输出
- [D] 评委模型完全没有随机性，评分绝对客观

**参考答案**：[0, 1, 2]

**解析**：位置偏差、长度偏差、自我偏好（self-preference）都是已知的评委偏差。评委模型并非绝对客观，其输出会受提示、顺序、风格等影响。

### multi_choice · None



- [A] 明确列出评分维度和各分档的描述
- [B] 要求评委先给出理由再给出分数
- [C] 要求评委以结构化格式（如 JSON）输出结果
- [D] 在提示词中给评委施加压力，说「答错就惩罚你」

**参考答案**：[0, 1, 2]

**解析**：清晰维度、先理由后分数（chain-of-thought 式）、结构化输出都能提高一致性与可解析性。施压式措辞不会提升可靠性，反而可能引入噪声。

### multi_choice · None



- [A] LLM 评委可以大规模、低成本地替代部分人工评估工作
- [B] LLM 评委的结果应当通过抽样人工复核来验证其一致性
- [C] LLM 评委完全可以取代人工评估，无需任何验证
- [D] 人工评估可以作为校准 LLM 评委的参考标准

**参考答案**：[0, 1, 3]

**解析**：LLM 评委适合规模化评估，但需人工抽样验证一致性，人工评估常作为校准参考。说其可完全取代人工且无需验证是不成立的。

### multi_choice · None



- [A] 交换 A、B 顺序分别评估，检查结论是否一致
- [B] 在提示词中给出明确的评判维度（如正确性、相关性）
- [C] 只评估顺序为 A、B 的那一次，忽略反向结果
- [D] 对不一致的样本进行人工复核或标记为存疑

**参考答案**：[0, 1, 3]

**解析**：交换顺序、明确维度、对不一致样本复核都是降低偏差、提升结论可靠性的合理策略。只评估单次顺序会放大位置偏差。

### fill_blank · None



**参考答案**：["rubric", "评分标准", "评分细则"]

**解析**：评分标准/评分细则在英文中常称为 rubric，它定义了评判维度与分档描述，是 LLM 评委提示词的核心组成部分。

### fill_blank · None



**参考答案**：["位置", "position", "位置偏差", "position bias"]

**解析**：评分受候选项排列顺序影响称为位置偏差（position bias），常通过交换顺序评估来缓解。

### code_reading · None



**参考答案**：它做的是成对比较的 LLM 评判：先用 A、B 顺序让评委判断，再交换为 B、A 顺序再判一次；若两次结论一致则采用，否则标记为不一致。这样设计的目的是缓解位置偏差，并通过一致性检查提高评估可靠性。

**解析**：两次交换顺序评估是缓解位置偏差的经典做法；不一致时标记，避免直接采信单次可能受顺序影响的结论。

### code_reading · None



**参考答案**：要求先写理由再给分数，是让模型进行分步推理（类似 chain-of-thought），有助于得到更有依据的评分；把 temperature 调低是为了减少输出的随机性，让同一输入的评分更稳定、可复现。

**解析**：先理由后分数提升评分质量与可解释性；低温度降低采样随机性，提升一致性与可复现性。

### scenario · None



**解析**：分数波动大通常源于采样温度过高、评分标准模糊、输出格式不规范。可通过降低温度、细化评分标准与分档、要求结构化输出、对多次评估取一致性或多数投票、抽样人工复核来提升稳定性。

### scenario · None



**解析**：担心是合理的，因为先 A 后 B 的单次成对评估可能受位置偏差影响。更可信的方案是交换顺序各评一次（或多次重复），检查结论一致性；对不一致样本做人工复核或抽样验证，必要时对不同顺序的结果做综合统计。

### single_choice · None



- [A] 评委模型倾向于给排在前面（或后面）的候选答案更高的分数，与内容质量无关
- [B] 评委模型对包含数字的答案一律给低分
- [C] 评委模型只输出英文而不输出中文
- [D] 评委模型无法处理超过 100 字的输入

**参考答案**：0

**解析**：位置偏差指评委的评分受候选呈现顺序影响，而非内容本身。常见缓解方法是交换顺序做两次评估并取平均/一致性判断。

### single_choice · None



- [A] 位置偏差
- [B] 长度偏差（verbosity bias）
- [C] 采样温度偏差
- [D] 分词偏差

**参考答案**：1

**解析**：长度偏差指评委偏好更冗长的回答。缓解方式包括在评分标准中明确「简洁且正确」优先，或对答案长度做控制。

### single_choice · None



- [A] 把采样温度调到很高的值
- [B] 让评委模型自由发挥，不给出任何输出格式要求
- [C] 使用较低的温度并要求结构化的评分输出（如分数加理由）
- [D] 每次都更换不同的评委模型

**参考答案**：2

**解析**：较低温度可降低随机性，结构化输出便于解析和一致性校验。高温度、更换模型、无格式要求都会降低可复现性。

### single_choice · None



- [A] 成对比较要求评委同时输出两个绝对分数才能对比
- [B] 单点打分天然比成对比较更适合判断两个答案谁更好
- [C] 成对比较是让评委在两个候选之间选更优者，通常更贴近相对质量判断
- [D] 两者完全等价，没有任何区别

**参考答案**：2

**解析**：成对比较让评委在 A、B 间做相对选择，常用于 A/B 评估；单点打分给绝对分数。两者适用场景不同，并非等价，成对比较在判断相对优劣时往往更稳定。

### single_choice · None



- [A] 只评估一次，因为一次就够了
- [B] 交换 A、B 顺序各评一次，再综合两次结果
- [C] 只在提示词中写「忽略顺序」即可，无需实际交换
- [D] 只让评委看 A，不看 B

**参考答案**：1

**解析**：实际交换候选顺序各评一次，再根据两次结果是否一致来做判断，是缓解位置偏差的常用手段。仅在提示词里声明忽略顺序往往效果有限。

### single_choice · None



- [A] 评委模型的上下文窗口太小
- [B] 评分标准没有强调事实正确性，评委更关注语言流畅度
- [C] 评委模型的温度设置过低
- [D] 智能体输出过短

**参考答案**：1

**解析**：评委按评分标准行事，若标准未明确要求核查事实正确性，模型容易依据表面流畅度给分。应在 rubric 中显式加入事实准确性维度。

### single_choice · None



- [A] 参考基准评判不需要任何参考答案，完全凭评委主观判断
- [B] 参考基准评判会提供给评委一个标准参考答案，让评委据此判断候选答案的正确性
- [C] 参考基准评判只能用字符串精确匹配实现
- [D] 参考基准评判无法处理开放式问题

**参考答案**：1

**解析**：reference-based 评判把参考答案提供给评委作为比对依据，有助于提升事实判断的准确性，尤其适合有唯一或近似正确答案的任务。

### single_choice · None



- [A] 完全信任评委模型的每一次输出，不做任何校验
- [B] 对一部分样本进行人工复核，并与评委结果比对以估计一致性
- [C] 只评估一个样本就下结论
- [D] 把评分标准隐藏起来，避免评委受干扰

**参考答案**：1

**解析**：人工复核抽样并与评委结果比对，可估计评委与人类判断的一致性（如一致率、相关性），从而评估评委可信度。全信任、单样本、隐藏标准都不利于可信度。
