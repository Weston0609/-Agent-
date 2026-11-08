# s8u5l2 Agent 平台（Agent Platform）：从零到工程级 / 评估平台（Evaluation Platform）：从零到工程级

> 来源 `content/lessons/s8u5l2.json`

## arch.sys.agent_platform

# Agent 平台（Agent Platform）：从零到工程级

> **一句话直觉**：Agent 平台就是把“会思考的 LLM（大语言模型）+ 会动手的工具 + 会协作的流程”打包成一个可部署、可扩展、可观测的服务系统——它让 AI 从“聊天框”走进“真实业务”。

---

## 0. 学习地图

本节 40 分钟，按 5 个小节循序渐进：

1. **什么是 Agent（智能体）** —— 从“会说话”到“会做事”
2. **Agent 的解剖结构** —— LLM + 工具 + 记忆 + 规划
3. **单 Agent 最小可运行实现** —— 一个能查天气、做算术的 Agent
4. **从单 Agent 到 Agent 平台** —— 注册中心、运行时、可观测性
5. **工程化关键：类型、协议与安全边界** —— 让平台可维护、可防错

最后配一个本地可完成的动手练习。

---

## 1. 什么是 Agent？

**Agent（智能体）** 是一个能感知环境、做决策、并调用工具去改变环境的程序。和普通函数不同：

- 普通函数：输入 → 固定输出。
- Agent：输入 → **思考 → 选工具 → 执行 → 观察结果 → 再思考** → 输出。

这个循环叫 **Agent Loop（智能体循环）**，也叫 **ReAct（Reason + Act，推理+行动）**。

```python
# 01_agent_loop.py
# 用最朴素的方式演示 Agent Loop 的骨架（无需真实 LLM）

def fake_llm(prompt: str) -> str:
    """模拟一个 LLM：看到 'weather' 就决定用天气工具。"""
    if "weather" in prompt.lower():
        return "TOOL:get_weather(Beijing)"
    return "ANSWER: 我不知道。"

def get_weather(city: str) -> str:
    """一个普通工具（Tool）：查询天气。"""
    return f"{city} 今天晴，25°C"

TOOLS = {"get_weather": get_weather}

def run_agent(user_input: str) -> str:
    """Agent Loop：最多迭代 3 次。"""
    scratchpad = user_input
    for _ in range(3):
        decision = fake_llm(scratchpad)
        if decision.startswith("TOOL:"):
            call = decision[len("TOOL:"):]
            name = call.split("(")[0]
            arg = call.split("(")[1].rstrip(")")
            observation = TOOLS[name](arg)   # 执行工具
            scratchpad += f"\n观察：{observation}"
        else:
            return decision[len("ANSWER:"):].strip()
    return "达到最大迭代次数"

print(run_agent("Beijing weather?"))
```

**结论**：Agent 的本质就是“LLM 决策 + 工具执行 + 循环反馈”。

---

## 2. Agent 的四大解剖件

一个工程级 Agent 通常由四部分组成：

| 组件 | 英文 | 作用 |
|---|---|---|
| 大脑 | LLM | 决策、理解、生成 |
| 手脚 | Tool / Function | 真实世界里做事 |
| 记忆 | Memory | 短期（对话）、长期（向量库） |
| 规划 | Planner | 拆任务、定步骤 |

我们用一个带 **类型注解（type hint）** 的 `Tool` 数据类来统一描述“手脚”：

```python
# 02_tool_spec.py
from dataclasses import dataclass
from typing import Callable, Any

@dataclass
class ToolSpec:
    """描述一个工具：名字、说明、参数类型、实现函数。"""
    name: str
    description: str            # 给 LLM 看的自然语言说明
    input_schema: dict          # JSON Schema，约束参数
    func: Callable[..., Any]

    def invoke(self, **kwargs) -> Any:
        return self.func(**kwargs)

def add(a: float, b: float) -> float:
    return a + b

add_tool = ToolSpec(
    name="add",
    description="计算两个数之和",
    input_schema={
        "type": "object",
        "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
        "required": ["a", "b"],
    },
    func=add,
)

print(add_tool.invoke(a=1.5, b=2.5))   # 4.0
```

**结论**：工具的元信息（名字 + 说明 + Schema）是 Agent 平台能“自动选择工具”的基础。

---

## 3. 单 Agent 最小可运行实现

现在把前面两部分拼起来：一个能**查天气、做算术**的小 Agent。为了不依赖外部 API，我们用规则模拟 LLM 决策；理解后你可以换成真实 LLM。

```python
# 03_mini_agent.py
import re
from typing import Any

# ---------- 工具 ----------
def get_weather(city: str) -> str:
    return f"{city} 今天晴，25°C"

def add(a: float, b: float) -> float:
    return a + b

TOOLS = {"get_weather": get_weather, "add": add}

# ---------- 模拟 LLM ----------
def decide(query: str) -> str:
    """返回 'tool:<name>|<json-ish args>' 或 'final:<text>'。"""
    if "weather" in query.lower():
        city = re.search(r"in\s+(\w+)", query)
        return f"tool:get_weather|{city.group(1) if city else 'Beijing'}"
    m = re.search(r"(\d+)\s*\+\s*(\d+)", query)
    if m:
        return f"tool:add|{m.group(1)},{m.group(2)}"
    return "final:我可以帮你查天气或做加法。"

def execute(command: str) -> Any:
    if command.startswith("tool:"):
        name, args = command[len("tool:"):].split("|")
        if name == "get_weather":
            return TOOLS[name](args)
        if name == "add":
            a, b = args.split(",")
            return TOOLS[name](float(a), float(b))
    return None

def agent(query: str) -> str:
    scratchpad = query
    for _ in range(3):
        cmd = decide(scratchpad)
        if cmd.startswith("final:"):
            return cmd[len("final:"):]
        obs = execute(cmd)
        scratchpad += f"\n观察：{obs}"
    return "超时"

print(agent("weather in Shanghai"))   # Shanghai 今天晴，25°C
print(agent("3 + 4"))                 # 观察：7.0  → 最终会走 final?
```

**结论**：一个 Agent 最少只需要 **工具表 + 决策函数 + 循环**。

---

## 4. 从单 Agent 到 Agent 平台

单机脚本只能玩；要上生产，就要 **Agent Platform（智能体平台）**。平台化的核心是三件事：

1. **注册中心（Registry）**：统一登记所有 Agent 和 Tool。
2. **运行时（Runtime）**：执行 Agent Loop，管理超时、重试、并发。
3. **可观测性（Observability）**：记录每一步的输入输出，方便调试和审计。

下面是最小“平台”的样子：

```python
# 04_platform.py
from typing import Callable, Any
import time, logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

class AgentPlatform:
    """极简 Agent 平台：支持注册 Agent 并调用，附带日志。"""
    def __init__(self):
        self._agents: dict[str, Callable[[str], str]] = {}

    def register(self, name: str):
        def deco(fn: Callable[[str], str]):
            self._agents[name] = fn
            logging.info(f"注册 Agent: {name}")
            return fn
        return deco

    def run(self, name: str, query: str) -> str:
        if name not in self._agents:
            raise KeyError(f"Agent 不存在: {name}")
        start = time.time()
        try:
            result = self._agents[name](query)
            logging.info(f"Agent={name} 耗时={time.time()-start:.3f}s")
            return result
        except Exception as e:
            logging.error(f"Agent={name} 失败: {e}")
            raise

platform = AgentPlatform()

@platform.register("mini")
def mini_agent(query: str) -> str:
    return f"echo: {query}"

print(platform.run("mini", "hello platform"))
```

**结论**：平台的价值 = **统一注册 + 受控运行 + 可观测日志**。

---

## 5. 工程化关键：类型、协议与安全

上生产最容易出问题的三点：

- **参数类型对不上**：LLM 给工具的参数是字符串，工具却要 int。→ 用类型注解 + 校验。
- **调用越权**：LLM 编出工具名 `delete_all`。→ 只能在注册表中查找，白名单机制。
- **不返回**：函数报错、死循环。→ 用 `Never` / `NoReturn` 标注不可返回路径，并设置最大迭代次数。

```python
# 05_safe_tool.py
from typing import Callable, Never, Any

def _abort(msg: str) -> Never:
    """永远不返回；用于标注非法路径。"""
    raise ValueError(msg)

REGISTRY: dict[str, Callable[..., Any]] = {}

def register(name: str):
    def deco(fn):
        REGISTRY[name] = fn
        return fn
    return deco

@register("mul")
def mul(a: int, b: int) -> int:
    return a * b

def safe_invoke(name: str, **kwargs) -> Any:
    if name not in REGISTRY:
        _abort(f"工具未注册: {name}")   # 白名单
    fn = REGISTRY[name]
    # 简单类型校验
    for k, v in kwargs.items():
        expected = fn.__annotations__.get(k)
        if expected is int and not isinstance(v, int):
            _abort(f"参数 {k} 期望 int，得到 {type(v).__name__}")
    return fn(**kwargs)

print(safe_invoke("mul", a=2, b=3))          # 6
# safe_invoke("delete_all")                    # 抛 ValueError
# safe_invoke("mul", a="2", b=3)               # 抛 ValueError
```

**结论**：类型注解和 `Never` 让“非法路径”在运行前就能被静态检查器抓出来，平台更稳。

---

## 6. 动手练习

**任务**：实现一个名为 `calc_agent` 的 Agent，注册到 `AgentPlatform`，让它支持：

1. 工具 `add`、`mul`（已注册过，可复用）。
2. 用户输入形如 `"3 + 4"` 或 `"3 * 4"`，Agent 自动选择对应工具并返回数值结果。
3. 通过 `platform.run("calc", "3 * 4")` 调用，输出 `12`。
4. 要求：工具未注册、参数非法时抛出 `ValueError`，不要崩溃整个平台。

**提示**：
- 用正则 `re.findall(r"\d+", text)` 提取数字。
- 用运算符 `+` / `*` 决定调用哪个工具。
- 用第 5 节的 `safe_invoke` 做安全调用。

完成后，你可以再把 `decide` 换成真实的 LLM 调用（如 OpenAI/Claude/本地模型），这个 `calc_agent` 只改一个函数就能跑起来——这正是 Agent 平台的可扩展性。

## arch.sys.eval_platform

# 评估平台（Evaluation Platform）：从零到工程级

> **一句话直觉**：评估平台就是给 AI 系统当"裁判"的自动化流水线——它用统一的规则、可复现的流程，对模型、提示词、检索策略等任何会变化的部件打分，让你能从"我觉得好像变好了"进化到"数据证明变好了 3.2%"。

---

## 0. 为什么零基础也要先学评估平台？

AI 工程和普通软件工程最大的差别是：**输出是概率性的**。同一段提示词（prompt）跑两次结果可能不同。如果没有评估平台（evaluation platform），团队会陷入三种常见困境：

1. **回归无感知**：改了一行系统提示（system prompt），线上效果悄悄变差。
2. **优化靠玄学**：A/B 两个方案选哪个，全凭"感觉"。
3. **无法协作**：每个人用自己的小脚本跑几个例子，结论互不可比。

评估平台把这些零散动作**标准化、自动化、可追踪**。本节课按四个层次递进：数据 → 指标 → 平台 → 工程化。

---

## 1. 第一层：数据集（Dataset）是最小可复用的评估单元

评估平台的地基不是模型，而是**数据**。一条评估样本（sample / case）通常包含：

- `input`：喂给系统的输入（提示词、用户问题等）
- `expected`：期望输出（参考答案、期望标签）
- `metadata`：可选标签（难度、领域、来源），方便切片分析

关键结论：**评估数据集必须是版本化的、不可变的**，否则你今天的分数和昨天的分数无法比较。

```python
# eval_dataset.py —— 用最朴素的结构定义一份版本化数据集
from dataclasses import dataclass, field
from typing import Any

@dataclass(frozen=True)  # frozen=True 保证样本不可变
class EvalSample:
    id: str                 # 样本唯一标识，回归分析时按 id 对比
    input: str              # 系统输入
    expected: Any           # 期望输出（字符串、标签、JSON 都行）
    metadata: dict = field(default_factory=dict)  # 领域/难度等切片维度

# 一份最小数据集，附带版本号
DATASET_VERSION = "2024-06-01.v1"

dataset = [
    EvalSample("q1", "法国的首都是？", "巴黎", {"domain": "geo"}),
    EvalSample("q2", "2+2 等于几？", "4", {"domain": "math"}),
    EvalSample("q3", "水的化学式？", "H2O", {"domain": "chem"}),
]

# 关键工程习惯：数据集一旦发布就不能就地修改，只增新版本
print(f"dataset {DATASET_VERSION}: {len(dataset)} cases")
```

---

## 2. 第二层：指标（Metric）是可插拔的打分器

指标就是"给一条样本打多少分"的函数。工程上务必把指标抽象成**统一接口**，这样平台才能用同一套流水线跑不同指标。

常见指标分三类：

| 类型 | 例子 | 适用场景 |
|---|---|---|
| 精确/规则型 | 完全匹配、包含匹配 | 有标准答案 |
| 语义型 | BLEU、ROUGE、Embedding 相似度 | 文本生成 |
| 评判型 | 模型打分（LLM-as-a-Judge）| 主观质量、复杂任务 |

关键结论：**指标必须返回结构化结果，而不是布尔值**，因为后续要做聚合、切片、对比。

```python
# metrics.py —— 把指标抽象成可插拔的 Callable
from typing import Callable, Protocol
from dataclasses import dataclass

@dataclass
class MetricResult:
    score: float        # 归一化到 [0, 1]，方便跨指标聚合
    passed: bool        # 是否达标，便于统计通过率
    reason: str = ""    # 失败原因，便于人工复核

class Metric(Protocol):
    name: str
    def __call__(self, sample_input: str, prediction: str, expected) -> MetricResult: ...

# 指标 1：精确匹配
def exact_match(_, prediction: str, expected) -> MetricResult:
    ok = prediction.strip() == str(expected).strip()
    return MetricResult(score=1.0 if ok else 0.0, passed=ok,
                        reason="" if ok else f"got={prediction!r} want={expected!r}")

# 指标 2：关键词包含（对生成式回答更宽容）
def contains_keyword(_, prediction: str, expected) -> MetricResult:
    ok = str(expected).strip() in prediction
    return MetricResult(score=1.0 if ok else 0.0, passed=ok,
                        reason="" if ok else "keyword missing")

# 指标 3：长度惩罚（示例：不要冗长）
def not_too_long(_, prediction: str, expected) -> MetricResult:
    ok = len(prediction) <= 100
    return MetricResult(score=1.0 if ok else 0.0, passed=ok,
                        reason="" if ok else "too long")

METRICS = [exact_match, contains_keyword, not_too_long]
```

---

## 3. 第三层：Runner（运行器）——把数据 × 指标 × 被测系统组装起来

这是评估平台的核心：**驱动被测系统（System Under Test, SUT）跑完整个数据集，收集每条样本 × 每个指标的得分**。

关键结论：**Runner 必须可复现**。要做到这点：
- 固定随机种子（seed）
- 记录被测系统的版本、数据集版本、指标版本
- 失败样本要被保存下来，便于排查

```python
# runner.py —— 一个最小可用的评估 Runner
from dataclasses import asdict
import json


def run_eval(dataset, sut_fn, metrics, run_meta):
    """sut_fn: 被测系统函数，输入 str 输出 str
       metrics: 指标列表
       run_meta: 记录本次评估的上下文（模型名、版本等）
    """
    records = []
    for sample in dataset:
        prediction = sut_fn(sample.input)
        for metric in metrics:
            result = metric(sample.input, prediction, sample.expected)
            records.append({
                "sample_id": sample.id,
                "metric": metric.__name__,
                "score": result.score,
                "passed": result.passed,
                "reason": result.reason,
                "prediction": prediction,
                "expected": sample.expected,
                **run_meta,
            })
    return records


# 被测系统：先用一个假模型做演示
 def fake_model(prompt: str) -> str:
     answers = {
         "法国的首都是？": "巴黎是法国的首都",
         "2+2 等于几？": "4",
         "水的化学式？": "不知道",
     }
     return answers.get(prompt, "")


if __name__ == "__main__":
    records = run_eval(
        dataset,
        sut_fn=fake_model,
        metrics=METRICS,
        run_meta={"model": "fake-1.0", "dataset_version": DATASET_VERSION},
    )
    print(json.dumps(records[:3], ensure_ascii=False, indent=2))
```

---

## 4. 第四层：聚合与回归对比——平台的"回答能力"

收集到原始记录后，评估平台要回答两个问题：

1. **本次跑分怎样？** → 按指标聚合，按 metadata 切片。
2. **这次改动有没有让结果变差？** → 与基线（baseline）逐样本对比，找出**回归样本（regressions）**。

关键结论：**只看平均分是不够的**。平均分可能掩盖某类样本的严重退化。工程上一定要输出：
- 总体均分
- 每个指标的通过率
- 每个切片（domain / difficulty）的通过率
- 每条样本相对基线的分数变化

```python
# aggregate.py —— 聚合 + 相对基线找回归
from collections import defaultdict


def aggregate(records):
    """按指标聚合总分和通过率。"""
    by_metric = defaultdict(lambda: {"n": 0, "sum": 0.0, "pass": 0})
    for r in records:
        m = by_metric[r["metric"]]
        m["n"] += 1
        m["sum"] += r["score"]
        m["pass"] += int(r["passed"])
    return {
        name: {
            "avg_score": v["sum"] / v["n"],
            "pass_rate": v["pass"] / v["n"],
        }
        for name, v in by_metric.items()
    }


def diff_against_baseline(current, baseline):
    """逐样本对比，输出回归列表（current < baseline 的样本）。"""
    base_map = {(r["sample_id"], r["metric"]): r["score"] for r in baseline}
    regressions = []
    for r in current:
        key = (r["sample_id"], r["metric"])
        delta = r["score"] - base_map.get(key, 0.0)
        if delta < 0:
            regressions.append({"sample_id": r["sample_id"],
                                "metric": r["metric"],
                                "delta": delta,
                                "reason": r["reason"]})
    return regressions


if __name__ == "__main__":
    # 假设 baselines 和 current 已由 run_eval 生成
    pass
```

---

## 5. 工程级形态：评估平台该长什么样

把上面的四层放到一起，一个生产级评估平台通常具有这些特征（本节只讲架构，不展开实现）：

| 维度 | 零级脚本 | 工程级平台 |
|---|---|---|
| 数据集 | 硬编码在 .py | 版本化存储（DB / 对象存储）+ schema 校验 |
| 指标 | 内联函数 | 注册中心，可按名引用与组合 |
| 运行 | 本地 `python eval.py` | 异步任务队列，支持并发、重试、超时 |
| 存储 | print 到屏幕 | 结构化写入（数据库 / 数据仓库） |
| 对比 | 手动 diff | 自动与基线对比，生成可视化报告 |
| 复现 | 靠记忆 | 每次运行记录 model / dataset / metric / code commit |
| 触发 | 手动 | CI 钩子（回归即阻断合并） |

**判断一个评估平台是否合格的三条线**：
1. 任意一次历史的评估结果，都能**一键复现**。
2. 任意一次代码/模型变更，都能在**几分钟内**得到回归报告。
3. 任意一条失败样本，都能**追溯到**它的输入、输出、期望、命中的指标与原因。

做到这三点，评估平台才算从"脚本"晋升为"平台"。

---

## 6. 常见误区速查（详见 pitfalls 字段）

- 把训练集和评估集混用
- 只看平均分，不看切片和单样本回归
- 指标不可复现（比如用了非固定随机种子）
- 数据集改了却复用旧版本号
- 只评估"成功案例"，忽略失败样本

---

## 7. 动手练习

**任务**：在一个本地目录下，把上面三份代码整合成一个可运行的最小评估平台，并完成一次回归对比。

具体要求：

1. 新建 `my_eval/` 目录，包含 `dataset.py`、`metrics.py`、`runner.py`、`aggregate.py`。
2. 数据集包含至少 5 条样本，覆盖 2 个领域（例如 `math` 和 `geo`）。
3. 实现两个指标：`exact_match` 与 `contains_keyword`。
4. 写一个 `main.py`，运行两次评估：
   - **基线（baseline）**：用 `fake_model`（故意答错其中一条）
   - **当前（current）**：用一个稍好的 `fake_model_v2`（把那条改对）
5. 调用 `diff_against_baseline`，输出：
   - 每个指标的 `avg_score`、`pass_rate`
   - 所有回归样本（`delta < 0`）
6. 把两次运行的 `run_meta` 打印出来，验证 `model` 字段不同、`dataset_version` 相同。

**验收标准**：`python main.py` 能输出对比报告，且报告里能看出"当前版本在某条样本上优于基线，无回归"。

**进阶挑战**：把 `dataset_version` 换成两个不同值，观察 `diff_against_baseline` 会给出什么信号，并思考为什么平台层强制要求数据集版本对齐。

```python
import json
from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Protocol
from collections import defaultdict

# ---------- 1. 数据集 ----------
DATASET_VERSION = "2024-06-01.v1"

@dataclass(frozen=True)
class EvalSample:
    id: str
    input: str
    expected: Any
    metadata: dict = field(default_factory=dict)

dataset = [
    EvalSample("q1", "法国的首都是？", "巴黎", {"domain": "geo"}),
    EvalSample("q2", "2+2 等于几？", "4", {"domain": "math"}),
    EvalSample("q3", "水的化学式？", "H2O", {"domain": "chem"}),
    EvalSample("q4", "3-1 等于几？", "2", {"domain": "math"}),
    EvalSample("q5", "日本的首都是？", "东京", {"domain": "geo"}),
]

# ---------- 2. 指标 ----------
@dataclass
class MetricResult:
    score: float
    passed: bool
    reason: str = ""

class Metric(Protocol):
    name: str
    def __call__(self, sample_input: str, prediction: str, expected) -> MetricResult: ...

def exact_match(_, prediction: str, expected) -> MetricResult:
    ok = prediction.strip() == str(expected).strip()
    return MetricResult(1.0 if ok else 0.0, ok, "" if ok else f"got={prediction!r}")

def contains_keyword(_, prediction: str, expected) -> MetricResult:
    ok = str(expected).strip() in prediction
    return MetricResult(1.0 if ok else 0.0, ok, "" if ok else "keyword missing")

METRICS = [exact_match, contains_keyword]

# ---------- 3. Runner ----------
def run_eval(dataset, sut_fn, metrics, run_meta):
    records = []
    for sample in dataset:
        prediction = sut_fn(sample.input)
        for metric in metrics:
            r = metric(sample.input, prediction, sample.expected)
            records.append({
                "sample_id": sample.id,
                "domain": sample.metadata.get("domain"),
                "metric": metric.__name__,
                "score": r.score,
                "passed": r.passed,
                "reason": r.reason,
                "prediction": prediction,
                "expected": sample.expected,
                **run_meta,
            })
    return records

# ---------- 4. 聚合 & 对比 ----------
def aggregate(records):
    by_metric = defaultdict(lambda: {"n": 0, "sum": 0.0, "pass": 0})
    for r in records:
        m = by_metric[r["metric"]]
        m["n"] += 1
        m["sum"] += r["score"]
        m["pass"] += int(r["passed"])
    return {k: {"avg_score": v["sum"]/v["n"], "pass_rate": v["pass"]/v["n"]}
            for k, v in by_metric.items()}

def diff_against_baseline(current, baseline):
    base_map = {(r["sample_id"], r["metric"]): r["score"] for r in baseline}
    regressions = []
    for r in current:
        k = (r["sample_id"], r["metric"])
        delta = r["score"] - base_map.get(k, 0.0)
        if delta < 0:
            regressions.append({"sample_id": r["sample_id"], "metric": r["metric"], "delta": delta, "reason": r["reason"]})
    return regressions

# ---------- 5. 两个版本的被测系统 ----------
def model_v1(prompt):
    return {"法国的首都是？": "巴黎", "2+2 等于几？": "4", "水的化学式？": "不知道",
            "3-1 等于几？": "2", "日本的首都是？": "东京"}.get(prompt, "")

def model_v2(prompt):
    return {"法国的首都是？": "巴黎", "2+2 等于几？": "4", "水的化学式？": "H2O",
            "3-1 等于几？": "2", "日本的首都是？": "东京"}.get(prompt, "")

if __name__ == "__main__":
    base_meta = {"model": "v1", "dataset_version": DATASET_VERSION}
    cur_meta  = {"model": "v2", "dataset_version": DATASET_VERSION}
    base = run_eval(dataset, model_v1, METRICS, base_meta)
    cur  = run_eval(dataset, model_v2, METRICS, cur_meta)

    print("== baseline aggregate ==")
    print(json.dumps(aggregate(base), ensure_ascii=False, indent=2))
    print("== current aggregate ==")
    print(json.dumps(aggregate(cur), ensure_ascii=False, indent=2))
    print("== regressions ==")
    print(json.dumps(diff_against_baseline(cur, base), ensure_ascii=False, indent=2))
```


---

## 本课题目

### single_choice · None



- [A] 为每个用户启动独立操作系统虚拟机
- [B] 使用 Python 的 subprocess 为每个用户启动独立解释器进程
- [C] 在单个解释器中为每个用户创建独立线程并共享全局变量
- [D] 使用模块级全局字典按用户 ID 存储所有状态

**参考答案**：1

**解析**：子进程可提供进程级隔离且启动成本低于虚拟机；线程共享全局状态无法隔离；模块级全局字典完全不隔离；虚拟机开销最大。

### single_choice · None



- [A] 让工具函数在后台线程中运行并忽略取消信号
- [B] 使用 async/await 配合可取消的 asyncio.Task 与 try/finally 清理
- [C] 把所有工具调用包装成同步阻塞调用
- [D] 将取消请求写入日志文件供事后分析

**参考答案**：1

**解析**：异步任务可被取消，try/finally 能保证资源释放；同步阻塞无法及时取消；忽略信号或仅记日志都不满足释放资源的要求。

### single_choice · None



- [A] 所有工具使用相同的全局命名空间
- [B] 按插件来源或命名空间前缀注册工具名
- [C] 要求所有工具名必须为单字符
- [D] 禁止插件注册工具

**参考答案**：1

**解析**：命名空间前缀可避免冲突；全局命名空间易冲突；单字符限制不现实；禁止注册失去扩展性。

### single_choice · None



- [A] 按字符数除以 2 粗略估算并直接发送
- [B] 使用与目标模型对应的 tokenizer 进行精确计数
- [C] 不估算，等模型返回错误再处理
- [D] 把提示词截断到固定 100 字符

**参考答案**：1

**解析**：不同模型 tokenizer 不同，精确计数最可靠；粗略估算和事后处理都可能导致失败；固定截断会丢失信息。

### single_choice · None



- [A] 在工具执行前插入审批检查点，暂停并等待外部审批结果
- [B] 让智能体自行决定是否跳过审核
- [C] 把审核逻辑写死在每个工具内部
- [D] 仅在日志中记录敏感操作

**参考答案**：0

**解析**：执行前检查点可强制暂停等待审批；自行决定或仅记日志无法阻止操作；写死在每个工具内部难以维护。

### single_choice · None



- [A] 只统计总调用次数
- [B] 分别统计成功次数与失败次数并计算成功率
- [C] 只统计平均耗时
- [D] 只统计最大耗时

**参考答案**：1

**解析**：成功率需要成功与失败两个计数；总次数或耗时指标无法直接反映成功率。

### single_choice · None



- [A] 立即无限重试直到成功
- [B] 使用指数退避并设置最大重试次数
- [C] 每次重试间隔固定 1 毫秒
- [D] 超时后直接丢弃请求不重试

**参考答案**：1

**解析**：指数退避+最大次数可平衡可靠性与资源消耗；无限重试、过短间隔或完全不重试都不合适。

### single_choice · None



- [A] 在每个提示词中重新询问用户偏好
- [B] 将偏好提取为结构化记忆并注入后续提示词
- [C] 忽略偏好，每次重新开始
- [D] 把偏好写在服务器环境变量中

**参考答案**：1

**解析**：结构化记忆可在多步任务中复用；重复询问体验差；忽略偏好不满足需求；环境变量不适合存用户偏好。

### single_choice · None



- [A] 在业务代码中到处写 if provider == 'A' 的分支
- [B] 定义统一的模型接口，各供应商实现适配器
- [C] 只支持一家供应商
- [D] 把供应商参数硬编码在提示词中

**参考答案**：1

**解析**：统一接口+适配器符合开闭原则；到处分支难以维护；单一供应商不满足需求；硬编码提示词不可扩展。

### single_choice · None



- [A] 在输出返回给用户前进行敏感信息过滤与脱敏
- [B] 要求模型不要泄露
- [C] 把系统提示词写得更长
- [D] 禁止智能体调用任何工具

**参考答案**：0

**解析**：输出侧过滤可实际拦截泄露；仅靠模型自觉不可靠；加长提示词或禁用工具都不解决泄露问题。

### single_choice · None



- [A] 使用全局递增整数但多进程下可能重复
- [B] 使用 UUID 作为运行标识并贯穿日志与调用
- [C] 使用时间戳到秒级作为唯一标识
- [D] 使用随机 0-9 的一位数

**参考答案**：1

**解析**：UUID 在分布式下碰撞概率极低；全局递增在并发下易重复；秒级时间戳会冲突；一位数随机空间太小。

### single_choice · None



- [A] 每次失败都重新初始化全部状态
- [B] 将中间状态持久化为检查点，并从最近检查点恢复
- [C] 只在内存中保存当前步骤编号
- [D] 失败后直接返回错误给用户

**参考答案**：1

**解析**：检查点持久化可支持断点续跑；重新初始化或仅内存保存无法恢复；直接返回错误不满足需求。

### single_choice · None



- [A] 在每个工具函数内部手动编写日志代码
- [B] 通过装饰器统一包装工具调用并记录元数据
- [C] 仅在平台入口处记录一次整体请求
- [D] 要求工具开发者自行保证日志格式一致

**参考答案**：1

**解析**：装饰器可集中处理横切关注点，避免重复代码；入口级记录粒度不足；手工或依赖开发者自觉难以保证一致性。

### single_choice · None



- [A] 要求所有工具返回字符串而不抛异常
- [B] 在调度层用 try/except 捕获工具异常并转为错误结果返回给智能体
- [C] 为每个工具单独部署一个物理服务器
- [D] 禁止第三方注册工具

**参考答案**：1

**解析**：在调用边界捕获异常可防止单个工具失败扩散；禁止注册或要求返回字符串限制了能力；物理隔离成本过高且不解决异常传播。

### single_choice · None



- [A] 无限保留全部历史消息
- [B] 对历史消息做摘要压缩并保留最近若干轮原文
- [C] 每轮随机丢弃一半历史消息
- [D] 将历史消息存入数据库但从不读取

**参考答案**：1

**解析**：摘要+最近窗口是常见上下文管理策略；无限保留浪费 token；随机丢弃会丢失关键信息；只存不读没有意义。

### single_choice · None



- [A] 直接崩溃并终止整个平台
- [B] 忽略该轮响应继续下一轮
- [C] 解析失败时回退到文本解析或向模型发送纠错提示
- [D] 把非法 JSON 当作合法动作执行

**参考答案**：2

**解析**：回退解析或纠错提示可提高鲁棒性；崩溃、忽略或强行执行都会导致错误行为。

### single_choice · None



- [A] 在工具函数内部用 time.sleep 随机延迟
- [B] 使用令牌桶或滑动窗口计数器进行限流
- [C] 在文档中建议用户不要频繁调用
- [D] 每次调用前询问用户是否继续

**参考答案**：1

**解析**：令牌桶/滑动窗口是标准限流算法；随机延迟不能保证上限；文档建议和询问用户都不是技术强制手段。

### single_choice · None



- [A] 增加服务器内存
- [B] 为调用链设置最大深度并检测循环调用
- [C] 要求工具作者自行避免递归
- [D] 把所有工具改为同步执行

**参考答案**：1

**解析**：深度限制+循环检测可直接防止无限递归；内存、作者自觉、同步执行都不能从根本上阻止递归。

### single_choice · None



- [A] 为每个智能体创建一个新的数据库连接池
- [B] 使用 asyncio 信号量控制并发获取连接的数量
- [C] 禁用并发，改为串行处理
- [D] 让智能体直接操作数据库文件

**参考答案**：1

**解析**：信号量可限制并发访问共享资源；每个智能体独立连接池会耗尽数据库连接；串行降低吞吐；直接操作文件破坏一致性。

### single_choice · None



- [A] 仅保存在内存中的全局字典
- [B] 序列化到 JSON 文件或数据库中并附带版本号
- [C] 打印到标准输出由运维手动抄写
- [D] 保存在线程局部变量中

**参考答案**：1

**解析**：序列化持久化可跨进程恢复；内存、线程局部变量随进程消失；标准输出不是可靠的持久化机制。

### single_choice · None



- [A] 评测平台主要负责编译源代码，编译成功后即视为评测通过
- [B] 评测平台负责调度评测任务、运行被测对象、采集结果并判定得分
- [C] 评测平台只负责存储评测结果，运行与调度由人工完成
- [D] 评测平台的核心是生成测试数据，运行与判定由被测系统自行完成

**参考答案**：1

**解析**：评测平台的核心职责包括任务调度、运行隔离、结果采集与判定。编译只是其中一个可选环节，存储和测试数据生成都不是平台的全部职责，因此B最准确。

### single_choice · None



- [A] 为了让代码运行得更快
- [B] 为了防止单个任务耗尽资源、影响其他任务或平台稳定性
- [C] 为了减少代码的行数
- [D] 为了强制用户使用指定的编程语言

**参考答案**：1

**解析**：资源限制是隔离性的手段，目的是防止某个任务占用过多 CPU 或内存从而拖垮整个平台或影响其他任务。它与运行速度、代码行数、语言选择无关。

### multi_choice · None



- [A] 限制可用的系统调用或网络访问
- [B] 为每个任务分配独立的工作目录
- [C] 让被测代码以宿主机的最高权限运行
- [D] 设置最大运行时间并支持超时终止

**参考答案**：[0, 1, 3]

**解析**：限制系统调用/网络、独立工作目录、超时终止都是常见的隔离与保护手段。让不可信代码以最高权限运行会放大风险，是错误的。

### multi_choice · None



- [A] 任务之间共享可变的全局状态
- [B] 运行时环境（如依赖版本）在不同机器上不一致
- [C] 为每个任务分配独立的隔离环境
- [D] 评测过程中依赖未固定的外部网络资源

**参考答案**：[0, 1, 3]

**解析**：共享可变状态、环境不一致、依赖未固定的外部网络都会导致结果不可复现。为每个任务分配独立隔离环境恰恰有助于可复现性，不选。

### fill_blank · None



**参考答案**：["沙箱", "sandbox", "sandboxing"]

**解析**：沙箱（sandbox）通过限制资源访问与系统调用来隔离不可信代码，是评测平台常用的安全机制。

### fill_blank · None



**参考答案**：["运行环境", "环境", "执行环境", "隔离环境"]

**解析**：为每个任务分配独立的运行环境（隔离环境）是保证任务互不干扰、结果可复现的常见做法。

### fill_blank · None



**参考答案**：["超时", "运行超时", "timeout", "TLE"]

**解析**：超过时间上限被终止的结果通常称为超时（timeout / TLE）。

### code_reading · None



**参考答案**：会判为 WA（答案错误）。因为判定使用字符串完全相等比较，把末尾换行也纳入了比较，语义正确但格式略有差异的输出会被误判。实际评测平台通常需要对尾部空白/换行做规范化或使用更宽松的判定规则。

**解析**：该判定逻辑基于字符串完全相等，属于过严的判定方式。语义正确但末尾缺少换行的输出会被判为 WA，说明判定规则需要考虑格式容差。

### code_reading · None



**参考答案**：time_limit 限制最大运行时间，memory_limit 限制内存使用，workdir 提供独立隔离的工作目录，network 控制是否允许网络访问。它们共同服务于「隔离和保护」这一目标：防止单个任务耗尽资源、干扰其他任务或影响宿主环境。

**解析**：这些参数分别从时间、内存、文件系统、网络四个维度对不可信代码进行限制，共同构成沙箱式的资源隔离与保护。

### code_reading · None



**参考答案**：体现了调度层负责判断平台是否有空闲执行资源、再决定是否派发任务的分层关系。去掉空闲判断会导致任务被无限制地并发派发，可能耗尽资源、拖垮平台或使任务相互干扰。

**解析**：调度与执行分层，调度层通过空闲判断控制并发度。去掉该判断会失去限流，导致资源耗尽和干扰。

### scenario · None



**参考答案**：应在隔离环境中运行不可信代码，并施加资源限制。具体措施包括：使用沙箱限制文件系统、网络和系统调用；为每个任务分配独立的工作目录或容器；设置最大运行时间和内存上限并在超限时终止；调度层控制并发度、避免资源耗尽。

**解析**：场景要求兼顾安全与稳定，核心是隔离与限流：沙箱隔离、独立环境、时间/内存限制、并发控制共同保证平台不被单个或大量任务拖垮。

### scenario · None



**参考答案**：可能原因包括：任务之间共享了可变的全局状态或工作目录、运行环境（依赖版本等）在不同机器上不一致、评测过程依赖未固定的外部网络资源、判定逻辑本身不确定。改进方向：为每个任务分配独立隔离的环境、固定依赖与运行环境、移除对外部网络的依赖或将其固定、让判定规则确定且一致。

**解析**：不可复现通常源于共享状态、环境不一致、外部依赖不稳定或判定不确定。改进思路是隔离、固定环境、去除不稳定外部依赖并保证判定一致。

### single_choice · None



- [A] 让代码在语法上符合规范
- [B] 限制代码对文件系统、网络等外部资源的访问，使其无法影响宿主环境
- [C] 自动为代码补充缺失的注释
- [D] 把代码翻译成另一种编程语言

**参考答案**：1

**解析**：沙箱的目标是隔离不可信代码，限制其对文件系统、网络、进程等外部资源的访问，保护宿主环境。语法检查、注释补充、语言翻译都不是沙箱的核心。

### single_choice · None



- [A] 无限等待，直到用户程序自行结束
- [B] 设置最大运行时间，超时后终止进程并给出相应判定
- [C] 超时后直接判定为编译错误
- [D] 超时后忽略该次评测，不记录任何结果

**参考答案**：1

**解析**：合理处理超时是设置时间上限并在超时后强制终止、记录为超时结果。无限等待会导致任务堆积；判定为编译错误混淆了错误类型；忽略结果则丢失信息。

### single_choice · None



- [A] 提高代码执行速度
- [B] 避免任务之间相互干扰，保证结果的可复现性
- [C] 减少代码本身的 bug
- [D] 让评测平台不再需要调度器

**参考答案**：1

**解析**：独立环境的主要收益是隔离：防止任务间通过文件、进程、环境变量等相互干扰，从而保证结果可复现。它不直接提升速度，也不修复代码 bug，更不会取消调度需求。

### single_choice · None



- [A] 程序输出为空
- [B] 程序输出末尾多了空白字符或换行，但语义完全正确
- [C] 程序崩溃
- [D] 程序没有输出任何错误信息

**参考答案**：1

**解析**：完全相等比较对尾部空白、换行等不敏感差异过于严格，可能把语义正确的输出判错。空输出、崩溃、无错误信息并不直接说明相等比较的局限。

### single_choice · None



- [A] 让代码运行得更快
- [B] 使任务排队/优先级策略与具体的运行方式解耦，便于扩展
- [C] 减少评测平台需要支持的编程语言数量
- [D] 避免使用任何并发机制

**参考答案**：1

**解析**：分层让调度策略（排队、优先级、并发度）与执行细节（如何启动进程、如何隔离）解耦，便于替换或扩展其中一层。它与运行速度、语言数量、是否并发无必然关系。

### single_choice · None



- [A] 让平台界面更美观
- [B] 帮助提交者准确定位问题并给出有针对性的反馈
- [C] 减少平台的代码量
- [D] 增加评测任务的数量

**参考答案**：1

**解析**：区分不同失败类型是为了给出有意义的诊断反馈，帮助提交者定位问题。它不是为了美观、减少代码量或增加任务数量。

### multi_choice · None



- [A] 对每个任务限制运行时间和内存使用
- [B] 在隔离环境中运行不可信代码
- [C] 让所有任务共享同一个可写工作目录
- [D] 对评测结果进行一致性的判定逻辑

**参考答案**：[0, 1, 3]

**解析**：资源限制、隔离运行、一致的判定逻辑都有助于公平与安全。共享可写工作目录会导致任务间互相干扰，破坏公平与安全，因此不选。

### multi_choice · None



- [A] 判定应当基于明确的规则，保证同一输入得到一致结论
- [B] 判定只能使用字符串完全相等这一种方式
- [C] 判定可以针对不同题目采用容差比较、特殊判定等策略
- [D] 判定结果应当与运行结果（如超时、崩溃）区分开

**参考答案**：[0, 1, 3]

**解析**：判定应当规则明确、一致，并且区分运行错误与答案错误，同时不同题目可采用不同判定策略。『只能用字符串相等』是常见误解，是错误的。
