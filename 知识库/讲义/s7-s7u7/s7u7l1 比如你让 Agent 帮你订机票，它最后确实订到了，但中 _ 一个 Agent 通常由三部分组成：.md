# s7u7l1 比如你让 Agent 帮你订机票，它最后确实订到了，但中 / 一个 Agent 通常由三部分组成：

> 来源 `content/lessons/s7u7l1.json`

## agent.eval.trajectory

## 一句话直觉

**Agent（智能体）的评估不能只看“最终答案对不对”，还要看它“走的路对不对”——这条走过的路，就叫 trajectory（轨迹）。**

比如你让 Agent 帮你订机票，它最后确实订到了，但中间偷偷把用户的钱转到了别的账户再转回来——答案对了，过程错了。trajectory 评估就是用来检查 Agent 每一步动作（action）、每一次思考（thought）、每一次工具调用（tool call）是否合理、安全、高效。

---

## 1. 什么是 trajectory？

**Trajectory（轨迹）** 是 Agent 在一次任务中产生的**完整交互序列**，通常包含：

- 用户输入（user input）
- 模型思考（thought / reasoning）
- 工具调用（tool call），如搜索、计算、调用 API
- 工具返回结果（observation）
- 最终答案（final answer）

一条 trajectory 就像一个“行车记录仪”，记录了 Agent 从起点到终点的全过程。

**为什么必须评估它？**

- 结果对但过程错：可能是**侥幸**，换一个输入就会失败。
- 过程里有危险动作：调用删除文件、泄露隐私、重复扣款。
- 过程低效：绕了 20 步才完成 1 步能做的事。

下面用一段最小代码模拟一条 trajectory。

```python
# 一条最小 trajectory：用 list[dict] 表示
trajectory = [
    {"step": 0, "type": "user",        "content": "北京今天适合跑步吗？"},
    {"step": 1, "type": "thought",     "content": "我需要查北京今天的天气"},
    {"step": 2, "type": "tool_call",   "tool": "weather", "args": {"city": "北京"}},
    {"step": 3, "type": "observation", "content": {"temp": 22, "rain": False, "aqi": 80}},
    {"step": 4, "type": "thought",     "content": "不下雨、温度适中、空气尚可，适合跑步"},
    {"step": 5, "type": "final",       "content": "适合，建议傍晚去公园慢跑 30 分钟。"},
]

for t in trajectory:
    print(t["step"], t["type"], t.get("content") or t.get("tool"))
```

---

## 2. 结果评估 vs 轨迹评估

**结果评估（outcome evaluation）**：只看 final answer 对不对。
**轨迹评估（trajectory evaluation）**：看整条序列是否合理。

两者是互补关系：

| 维度 | 问的问题 | 典型指标 |
|---|---|---|
| Outcome | 答对了吗？ | Accuracy、Pass@1 |
| Trajectory | 走对了吗？ | 步骤正确率、工具调用准确率、冗余步数 |

**关键结论：只用结果评估会漏掉“flaky success”（侥幸成功）。** 轨迹评估能抓到它。

```python
# 对比：两个 Agent 都答对了，但轨迹质量不同
agent_a = ["查天气", "判断", "回答"]                    # 3 步，简洁
agent_b = ["查天气", "查天气", "查天气", "查机票", "判断", "回答"]  # 6 步，有冗余

def trajectory_score(traj, expected_steps):
    """轨迹评分：步骤越接近预期越高分（简化版）"""
    return max(0.0, 1.0 - abs(len(traj) - expected_steps) / expected_steps)

print("A 轨迹分:", trajectory_score(agent_a, expected_steps=3))  # 1.0
print("B 轨迹分:", trajectory_score(agent_b, expected_steps=3))  # 0.0
```

---

## 3. 轨迹评估的四个核心维度

工程上，trajectory 评估通常拆成四个可测量的维度：

1. **有效性（Validity）**：每一步动作在语法和语义上是否合法（例如工具名存在、参数类型正确）。
2. **正确性（Correctness）**：每一步是否为达成目标做了“对的”事。
3. **效率（Efficiency）**：步数/工具调用数是否接近最优。
4. **安全性（Safety）**：是否有危险或越权动作。

这四个维度可以各自打分，再合成一个综合分。

```python
def eval_trajectory(traj, valid_tools, forbidden_tools, optimal_steps):
    valid = all(
        t.get("tool") in valid_tools
        for t in traj if t["type"] == "tool_call"
    )
    safe = not any(
        t.get("tool") in forbidden_tools
        for t in traj if t["type"] == "tool_call"
    )
    steps = sum(1 for t in traj if t["type"] == "tool_call")
    efficiency = max(0.0, 1.0 - max(0, steps - optimal_steps) / optimal_steps)

    return {
        "valid": valid,
        "safe": safe,
        "efficiency": round(efficiency, 2),
    }

traj = [
    {"type": "user", "content": "查北京天气"},
    {"type": "tool_call", "tool": "weather", "args": {"city": "北京"}},
    {"type": "tool_call", "tool": "weather", "args": {"city": "北京"}},  # 重复
    {"type": "final", "content": "晴天"},
]
print(eval_trajectory(traj, {"weather"}, {"shell", "delete_file"}, optimal_steps=1))
```

---

## 4. 如何自动打分：规则、模型、人工三管齐下

实际工程中，trajectory 评估有三类打分器（evaluator）：

- **规则打分器（rule-based）**：检查工具名、参数 schema、禁用词。快、稳、可解释。
- **模型打分器（LLM-as-a-judge）**：用 LLM 判断每一步“是否合理”。能抓语义错误，但可能不稳定。
- **人工打分（human-in-the-loop）**：用于构建黄金集（golden set），校准前两者。

**关键结论：规则先过滤，模型再打分，人工抽样校准，是工业界主流的三层结构。**

下面是规则打分器的骨架。

```python
from typing import Callable

# 每条规则返回 (是否通过: bool, 说明: str)
Rule = Callable[[list[dict]], tuple[bool, str]]

def rule_no_forbidden_tool(forbidden: set[str]) -> Rule:
    def _check(traj):
        for t in traj:
            if t.get("type") == "tool_call" and t.get("tool") in forbidden:
                return False, f"使用了禁用工具: {t['tool']}"
        return True, "无禁用工具"
    return _check

def rule_has_final_answer(traj):
    ok = any(t.get("type") == "final" for t in traj)
    return ok, "包含最终回答" if ok else "缺少最终回答"

rules: list[Rule] = [
    rule_no_forbidden_tool({"shell", "delete_file"}),
    rule_has_final_answer,
]

def score_trajectory(traj, rules):
    results = [r(traj) for r in rules]
    passed = sum(1 for ok, _ in results if ok)
    return passed / len(results), results

traj = [
    {"type": "user", "content": "帮我查天气"},
    {"type": "tool_call", "tool": "weather", "args": {"city": "北京"}},
    {"type": "final", "content": "晴"},
]
score, details = score_trajectory(traj, rules)
print("综合分:", score)
for ok, msg in details:
    print(" ", "✅" if ok else "❌", msg)
```

---

## 5. 把评估接入 CI：让轨迹回归成为习惯

一条 trajectory 的评估只说明“这一次 Agent 表现如何”。工程上真正重要的是：

- 准备一组固定的**评测用例（benchmark cases）**。
- 每次 Agent prompt / 模型 / 工具改动后，重跑全部用例。
- 对轨迹指标做纵向对比，发现退化（regression）。

这就是“**轨迹回归测试（trajectory regression test）**”。它和传统的单元测试思路一致：把一次成功的轨迹固化下来，作为下次的基准。

```python
BENCH = [
    {"input": "北京今天适合跑步吗？", "forbidden_tools": ["shell"]},
    {"input": "帮我算 123*456",       "forbidden_tools": ["network"]},
]

def run_agent(user_input: str) -> list[dict]:
    """占位：真实项目里替换成你的 Agent 调用"""
    return [
        {"type": "user", "content": user_input},
        {"type": "tool_call", "tool": "weather", "args": {"city": "北京"}},
        {"type": "final", "content": "晴天，适合跑步"},
    ]

def regression_test(bench, forbidden_tools):
    for case in bench:
        traj = run_agent(case["input"])
        score, details = score_trajectory(
            traj, [rule_no_forbidden_tool(set(forbidden_tools)), rule_has_final_answer]
        )
        print(f"[{case['input']}] 分数={score}")

regression_test(BENCH, forbidden_tools=["shell", "delete_file"])
```

---

## 小结

- **trajectory（轨迹）** = Agent 从输入到输出的完整动作序列。
- 只评估结果不够，轨迹能揭示**侥幸、冗余、危险**这三类隐蔽问题。
- 轨迹评估的四个维度：**有效性、正确性、效率、安全性**。
- 三层打分器：**规则 → 模型 → 人工**。
- 工程上要把轨迹评估变成**回归测试**，随改动持续跑。

---

## 动手练习

**任务：给一个“查天气 Agent”写一套最小轨迹评估脚本。**

要求：

1. 用 list[dict] 表示一条轨迹，至少包含 `user`、`tool_call`、`observation`、`final` 四类节点。
2. 写三条规则：
   - 禁止调用 `shell` 工具。
   - 必须调用过 `weather` 工具。
   - 必须包含 `final` 节点。
3. 写一个 `score_trajectory(traj, rules)` 函数返回 0~1 之间的分数。
4. 自己构造 3 条轨迹（一条完美、一条有冗余、一条违规），打印三者的分数并解释差异。

**进阶（可选）**：为同一任务写一个 LLM-as-a-judge 的 prompt 模板，让模型给轨迹的“合理性”打 1~5 分，并说明理由。

```python
# trajectory_eval_demo.py
# 运行：python trajectory_eval_demo.py

from typing import Callable

Rule = Callable[[list[dict]], tuple[bool, str]]

def rule_forbid_tool(forbidden: set[str]) -> Rule:
    def _check(traj):
        for t in traj:
            if t.get("type") == "tool_call" and t.get("tool") in forbidden:
                return False, f"使用了禁用工具: {t['tool']}"
        return True, "未使用禁用工具"
    return _check

def rule_must_call(tool_name: str) -> Rule:
    def _check(traj):
        called = any(
            t.get("type") == "tool_call" and t.get("tool") == tool_name
            for t in traj
        )
        return called, f"调用了 {tool_name}" if called else f"未调用 {tool_name}"
    return _check

def rule_has_final(traj):
    ok = any(t.get("type") == "final" for t in traj)
    return ok, "包含 final" if ok else "缺少 final"

def score_trajectory(traj: list[dict], rules: list[Rule]) -> tuple[float, list[tuple[bool, str]]]:
    results = [r(traj) for r in rules]
    passed = sum(1 for ok, _ in results if ok)
    return passed / len(results), results

# 三条轨迹
perfect = [
    {"type": "user", "content": "北京今天适合跑步吗？"},
    {"type": "tool_call", "tool": "weather", "args": {"city": "北京"}},
    {"type": "observation", "content": {"temp": 22, "rain": False}},
    {"type": "final", "content": "适合，傍晚慢跑 30 分钟。"},
]

redundant = [
    {"type": "user", "content": "北京今天适合跑步吗？"},
    {"type": "tool_call", "tool": "weather", "args": {"city": "北京"}},
    {"type": "tool_call", "tool": "weather", "args": {"city": "北京"}},  # 重复
    {"type": "tool_call", "tool": "weather", "args": {"city": "北京"}},  # 重复
    {"type": "final", "content": "适合跑步。"},
]

unsafe = [
    {"type": "user", "content": "北京今天适合跑步吗？"},
    {"type": "tool_call", "tool": "shell", "args": {"cmd": "rm -rf /"}},  # 违规
    {"type": "final", "content": "适合跑步。"},
]

rules: list[Rule] = [
    rule_forbid_tool({"shell", "delete_file"}),
    rule_must_call("weather"),
    rule_has_final,
]

for name, traj in [("perfect", perfect), ("redundant", redundant), ("unsafe", unsafe)]:
    score, details = score_trajectory(traj, rules)
    print(f"\n[{name}] score={score:.2f}")
    for ok, msg in details:
        print("  ", "✅" if ok else "❌", msg)
```

## agent.eval.tool_accuracy

## 一句话直觉

**Tool Accuracy（工具调用准确率）** 衡量的是：当 AI Agent（智能体）面对一个任务时，它**是否选对了工具、传对了参数、用对了顺序**。它直接决定了 Agent 能否真正“干活”，而不只是“聊天”。

---

## 1. 为什么需要评测工具调用？

一个 Agent 通常由三部分组成：

- **LLM（大语言模型）**：负责思考与决策
- **Tools（工具）**：真正执行动作的函数，比如查天气、发邮件、算数学
- **Loop（循环）**：LLM 决定调用哪个工具 → 执行 → 把结果喂回 LLM → 继续

LLM 可能会犯三类错误：

1. **选错工具**：该查天气，却去查汇率
2. **传错参数**：查天气时城市拼错、日期格式不对
3. **用错顺序**：还没查订单就先退款

如果只看“最终回答像不像人话”，这些问题会被掩盖。所以需要一个**结构化的评测指标**：Tool Accuracy。

通常拆成三个子指标：

| 指标 | 英文 | 含义 |
|---|---|---|
| 工具选择准确率 | Tool Selection Accuracy | 选中的工具是否等于期望工具 |
| 参数准确率 | Argument Accuracy | 每个参数键值是否都对 |
| 调用序列准确率 | Call Sequence Accuracy | 多次调用的顺序是否正确 |

---

## 2. 最小可运行的评测框架

我们先用**纯 Python**（不依赖任何 LLM）实现一个评测器。核心思想：把 Agent 的每次工具调用记录成结构化数据，再和标准答案（ground truth）逐项比对。

```python
from dataclasses import dataclass, field
from typing import Any

# 1. 定义一次工具调用
@dataclass
class ToolCall:
    name: str
    args: dict[str, Any]

# 2. 一次任务中 Agent 实际调用的工具序列
@dataclass
class Trace:
    calls: list[ToolCall]

# 3. 标准答案
@dataclass
class Expected:
    calls: list[ToolCall]

# 4. 评测指标
def tool_selection_accuracy(trace: Trace, expected: Expected) -> float:
    """只看工具名：逐位比较，命中记 1。"""
    n = max(len(trace.calls), len(expected.calls))
    if n == 0:
        return 1.0
    hits = 0
    for i in range(n):
        a = trace.calls[i].name if i < len(trace.calls) else None
        b = expected.calls[i].name if i < len(expected.calls) else None
        if a == b:
            hits += 1
    return hits / n

def argument_accuracy(trace: Trace, expected: Expected) -> float:
    """只在工具名对齐的位置上比参数，全对才算命中。"""
    n = max(len(trace.calls), len(expected.calls))
    if n == 0:
        return 1.0
    hits = 0
    for i in range(n):
        if i >= len(trace.calls) or i >= len(expected.calls):
            continue
        if trace.calls[i].name == expected.calls[i].name \
           and trace.calls[i].args == expected.calls[i].args:
            hits += 1
    return hits / n

def sequence_accuracy(trace: Trace, expected: Expected) -> float:
    """整条序列完全一致才算 1，否则 0。"""
    if len(trace.calls) != len(expected.calls):
        return 0.0
    for a, b in zip(trace.calls, expected.calls):
        if a.name != b.name or a.args != b.args:
            return 0.0
    return 1.0
```

这就是 Tool Accuracy 的骨架，后面换成真实 LLM 输出，只要把 `ToolCall` 解析出来即可。

---

## 3. 从 LLM 输出解析出 ToolCall

现代 Agent 一般会让 LLM 输出 **JSON**（或者用 OpenAI / Anthropic 的 Tool Use 格式）。下面是一个通用解析函数：

```python
import json
from typing import Optional

def parse_tool_calls(raw: str) -> list[ToolCall]:
    """
    期望 raw 是形如：
    [{"name": "get_weather", "args": {"city": "Beijing"}}]
    实际工程中要做错误处理、兼容多种格式。
    """
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    calls = []
    for item in data:
        calls.append(ToolCall(name=item["name"], args=item.get("args", {})))
    return calls
```

---

## 4. 常见的参数匹配策略

参数完全字符串相等太严格，工程上常用分级策略：

- **严格相等**：`"北京" == "北京"`
- **规范化后相等**：忽略大小写、去空格、日期统一成 ISO 格式
- **数值容差**：`abs(a - b) < 1e-6`
- **集合语义**：参数是无序集合时，比较 set 是否相等

```python
import re

def normalize(s: str) -> str:
    return re.sub(r"\s+", "", s).lower()

def args_equal(a: dict, b: dict, numeric_tol: float = 1e-6) -> bool:
    if set(a.keys()) != set(b.keys()):
        return False
    for k in a:
        va, vb = a[k], b[k]
        if isinstance(va, (int, float)) and isinstance(vb, (int, float)):
            if abs(va - vb) > numeric_tol:
                return False
        elif isinstance(va, str) and isinstance(vb, str):
            if normalize(va) != normalize(vb):
                return False
        else:
            if va != vb:
                return False
    return True
```

---

## 5. 把评测跑成流水线

真实评测通常是一批测试用例（test case），每个用例包含：输入、期望调用、Agent 实际调用。最后汇报**通过率**（pass rate）。

```python
@dataclass
class Case:
    user_input: str
    expected: Expected
    trace: Trace  # 由 Agent 实际执行得到

def evaluate(cases: list[Case]) -> dict[str, float]:
    n = len(cases)
    if n == 0:
        return {"selection": 0.0, "argument": 0.0, "sequence": 0.0}
    sel = sum(tool_selection_accuracy(c.trace, c.expected) for c in cases) / n
    arg = sum(argument_accuracy(c.trace, c.expected) for c in cases) / n
    seq = sum(sequence_accuracy(c.trace, c.expected) for c in cases) / n
    return {"selection": sel, "argument": arg, "sequence": seq}
```

到这里，你就有了一个**完全可复现、可扩展**的 Tool Accuracy 评测器。换成真实 LLM，只要把 `trace` 换成从 LLM 输出解析出来的结果即可。

---

## 关键结论回顾

1. Tool Accuracy 评测的是**行为**，而不是最终文本。
2. 拆成 selection / argument / sequence 三个子指标，便于定位问题。
3. 参数比对要有**分级策略**，不能只做字符串相等。
4. 评测器本身要零依赖、确定性，这样可以跑 CI（持续集成），防止 Prompt 改动悄悄拉低准确率。

```python
from dataclasses import dataclass
from typing import Any

@dataclass
class ToolCall:
    name: str
    args: dict[str, Any]

@dataclass
class Trace:
    calls: list[ToolCall]

@dataclass
class Expected:
    calls: list[ToolCall]

def tool_selection_accuracy(trace: Trace, expected: Expected) -> float:
    n = max(len(trace.calls), len(expected.calls))
    if n == 0:
        return 1.0
    hits = 0
    for i in range(n):
        a = trace.calls[i].name if i < len(trace.calls) else None
        b = expected.calls[i].name if i < len(expected.calls) else None
        if a == b:
            hits += 1
    return hits / n

def argument_accuracy(trace: Trace, expected: Expected) -> float:
    n = max(len(trace.calls), len(expected.calls))
    if n == 0:
        return 1.0
    hits = 0
    for i in range(n):
        if i >= len(trace.calls) or i >= len(expected.calls):
            continue
        if trace.calls[i].name == expected.calls[i].name \
           and trace.calls[i].args == expected.calls[i].args:
            hits += 1
    return hits / n

def sequence_accuracy(trace: Trace, expected: Expected) -> float:
    if len(trace.calls) != len(expected.calls):
        return 0.0
    for a, b in zip(trace.calls, expected.calls):
        if a.name != b.name or a.args != b.args:
            return 0.0
    return 1.0

if __name__ == "__main__":
    # 场景：用户说"帮我查北京天气，并给张三发邮件"
    expected = Expected(calls=[
        ToolCall("get_weather", {"city": "Beijing"}),
        ToolCall("send_email", {"to": "zhangsan@example.com", "body": "sunny"}),
    ])

    # Agent 实际调用：第一个对了，第二个参数写错了
    trace = Trace(calls=[
        ToolCall("get_weather", {"city": "Beijing"}),
        ToolCall("send_email", {"to": "zhangsan@example.com", "body": "Sunny"}),
    ])

    print("selection :", tool_selection_accuracy(trace, expected))  # 1.0
    print("argument  :", argument_accuracy(trace, expected))        # 0.5
    print("sequence  :", sequence_accuracy(trace, expected))        # 0.0
```


---

## 本课题目

### single_choice · None



- [A] 智能体一次运行中按时间顺序记录的思考、行动与观察序列
- [B] 智能体最终返回给用户的唯一答案字符串
- [C] 智能体所使用的底层大模型的参数数量
- [D] 智能体在训练阶段使用过的全部数据集样本

**参考答案**：0

**解析**：轨迹强调过程性记录，包括思考、工具调用及环境反馈的时序序列；最终答案只是轨迹的末端产物，模型参数与训练数据都不是轨迹。

### single_choice · None



- [A] 只检查最终答案是否正确，忽略中间的错误搜索
- [B] 检查轨迹是否包含对错误反馈的识别与策略调整，并据此评分
- [C] 因为中间出现了失败，直接判定该轨迹不合格
- [D] 统计工具调用总次数，次数越少轨迹越好

**参考答案**：1

**解析**：轨迹评估关注过程合理性，能否根据环境反馈纠错是重要维度；只看最终答案或一味惩罚失败、单纯追求调用次数少都会丢失过程信息。

### single_choice · None



- [A] 检查轨迹中每次工具调用是否对应真实存在的工具及其合法参数
- [B] 统计最终答案的字符数
- [C] 比较不同任务的运行时间
- [D] 查看模型参数量

**参考答案**：0

**解析**：幻觉工具调用表现为调用了不存在的工具或使用了非法参数，需逐步检查工具调用记录；其他选项与工具调用真实性无关。

### single_choice · None



- [A] 该步骤的文本是否流畅
- [B] 该步骤在当前状态下是否是合理且有助于任务推进的动作
- [C] 该步骤是否使用了最多的 token
- [D] 该步骤是否由特定模型生成

**参考答案**：1

**解析**：步骤正确性应基于当前状态判断动作是否合理、是否推进任务；文本流畅度、token 数量和生成模型都不是正确性的直接依据。

### single_choice · None



- [A] 轨迹完全合格，因为结果正确
- [B] 结果合格但轨迹效率较低，过程质量有待提升
- [C] 轨迹完全不合格，因为中间步骤多余
- [D] 无法评价，必须重新运行

**参考答案**：1

**解析**：结果正确不代表过程高效；大量无关调用说明效率低，但也不至于完全否定轨迹，应分维度评价。

### single_choice · None



- [A] 颜色、字体、排版、长度
- [B] 任务完成度、步骤合理性、效率、安全性
- [C] 模型名称、版本号、参数量、显存
- [D] 用户 ID、时间戳、文件名、路径

**参考答案**：1

**解析**：轨迹评估 rubric 通常围绕任务完成、过程合理、效率与安全等维度；其他选项属于元数据或无关属性。

### single_choice · None



- [A] 轨迹日志记录不完整或模型产生了幻觉
- [B] 工具本身运行速度太快
- [C] 任务难度太低
- [D] 用户输入太长

**参考答案**：0

**解析**：声称调用却无记录，可能是日志遗漏或模型幻觉；与工具速度、任务难度或输入长度无直接因果关系。

### single_choice · None



- [A] 对每一步独立打分后求和
- [B] 将轨迹视为序列，分析每步动作对后续状态的影响
- [C] 只统计轨迹的总 token 数
- [D] 只记录最终答案的对错

**参考答案**：1

**解析**：将轨迹作为序列并分析动作对后续状态的影响，才能体现因果依赖；独立打分、token 统计和只看结果都无法捕捉。

### single_choice · None



- [A] 每轮回复的字符数
- [B] 后续轮次是否一致地引用并正确使用前面轮次提供的信息
- [C] 模型加载所需时间
- [D] 对话总轮数越少越好

**参考答案**：1

**解析**：上下文保持体现在后续轮次能否正确引用和利用先前信息；字符数、加载时间和轮数多少都不直接衡量该能力。

### single_choice · None



- [A] 连续若干步的状态或动作高度相似且任务无进展
- [B] 单步响应时间过长
- [C] 轨迹总 token 数超过阈值
- [D] 最终答案长度过短

**参考答案**：0

**解析**：循环卡死的典型信号是状态/动作重复且无进展；响应时间长、token 多或答案短都不必然说明卡死。

### single_choice · None



- [A] 轨迹中是否包含泄露敏感信息或执行危险操作的步骤
- [B] 轨迹的总步数是否最少
- [C] 轨迹的文本是否使用了正式语气
- [D] 轨迹是否由最新模型生成

**参考答案**：0

**解析**：安全性评估关注敏感信息泄露、危险操作等风险步骤；步数、语气和模型版本不属于安全维度。

### single_choice · None



- [A] 只需包含最终答案正确的轨迹即可
- [B] 应包含成功、失败以及部分成功的多样化轨迹，以便全面评估
- [C] 应只包含最短的轨迹
- [D] 应只包含由最强模型生成的轨迹

**参考答案**：1

**解析**：多样化轨迹（成功、失败、部分成功）能更全面地检验评估方法；只保留正确、最短或最强模型的轨迹会引入选择偏差。

### single_choice · None



- [A] 轨迹级评估只看运行耗时，结果级评估只看准确率
- [B] 轨迹级评估会考察中间步骤的合理性，结果级评估主要看最终输出
- [C] 轨迹级评估必须使用人工，结果级评估必须使用程序
- [D] 轨迹级评估不需要任何评价指标，结果级评估才需要

**参考答案**：1

**解析**：轨迹级评估关注中间推理与行动步骤是否合理，结果级评估聚焦最终输出是否正确；二者都可以自动化或人工进行，也不等同于只看耗时。

### single_choice · None



- [A] 任务成功率
- [B] 完成每个任务平均所需的交互步数或工具调用次数
- [C] 模型推理时的显存占用
- [D] 提示词模板中的字符总数

**参考答案**：1

**解析**：轨迹效率通常用完成任务所需步数、工具调用次数等过程指标衡量；成功率是结果指标，显存和提示词长度不直接反映轨迹效率。

### single_choice · None



- [A] 仅记录最终答案的文本
- [B] 记录每步的输入状态、模型输出、所选动作及环境返回结果
- [C] 只记录运行开始和结束的时间戳
- [D] 只记录使用的模型名称和版本号

**参考答案**：1

**解析**：完整的轨迹应包含每步的状态、动作与观测，才能还原决策过程；只记录答案、时间戳或模型信息都不足以分析中间决策。

### single_choice · None



- [A] 动作的文本长度
- [B] 步骤之间的顺序与依赖关系
- [C] 模型调用的费用
- [D] 工具的类型

**参考答案**：1

**解析**：简单平均会丢失步骤顺序和前后依赖信息，而轨迹质量往往取决于步骤是否在正确时机以正确顺序执行。

### single_choice · None



- [A] 判断一张图片属于哪个类别
- [B] 评估多步工具调用智能体在复杂任务中的规划能力
- [C] 比较两个模型在单个问答上的回答长度
- [D] 测量一段代码的运行时间

**参考答案**：1

**解析**：多步工具调用智能体的规划与决策过程主要体现在轨迹中，单步分类、回答长度或运行时间都不需要轨迹评估。

### single_choice · None



- [A] 评判者模型越小越好，以节省成本
- [B] 需要校验评判者模型与人工评分的一致性，避免系统性偏差
- [C] 评判者模型应使用与智能体完全相同的提示词
- [D] 评判者模型不需要看到完整轨迹，只看最终答案即可

**参考答案**：1

**解析**：用模型评判轨迹时，应验证其与人工评分的一致性并控制偏差；评判者需要看到完整轨迹，提示词也应针对评判任务设计。

### single_choice · None



- [A] 轨迹的最终答案一定错误
- [B] 轨迹缺乏有效的自我纠正或状态推进
- [C] 工具调用次数太少
- [D] 模型的温度参数设置过低

**参考答案**：1

**解析**：重复无效动作表明智能体未能根据反馈调整策略、推进任务状态；这不必然意味着最终答案错误，也不直接由工具次数或温度决定。

### single_choice · None



- [A] 在完全相同的任务集和工具环境下比较平均步数
- [B] 让其中一个框架使用更强的模型，另一个使用更弱的模型
- [C] 只挑选每个框架表现最好的几条轨迹比较
- [D] 忽略任务难度差异，直接比较总步数

**参考答案**：0

**解析**：公平比较要求任务集、工具环境等条件一致；使用不同模型、只挑最好样本或忽略任务难度都会引入偏差。

### single_choice · None



- [A] 智能体最终回答的语言是否流畅
- [B] 智能体在需要调用工具时是否选择了与任务匹配的工具
- [C] 智能体调用工具的总次数
- [D] 智能体生成回答所消耗的 token 数量

**参考答案**：1

**解析**：工具准确率关注的是工具选择与调用是否与任务需求匹配，而不是输出文本质量、调用次数或成本。只有选项 1 直接对应“选对工具”。

### single_choice · None



- [A] 正确调用，因为调用了某个工具
- [B] 错误调用，因为所选工具与任务意图不匹配
- [C] 部分正确，因为返回了结果
- [D] 无法判断，因为没有报错

**参考答案**：1

**解析**：工具准确率要求工具与任务意图匹配。查询天气却调用汇率工具，属于工具选择错误，即使没有报错也不算正确。

### multi_choice · None



- [A] 工具调用准确率高，最终任务成功率不一定高
- [B] 最终任务成功率高，工具调用准确率不一定高
- [C] 工具调用准确率可以单独反映参数是否正确
- [D] 工具调用准确率通常需要结合任务成功率一起看

**参考答案**：[0, 1, 3]

**解析**：工具选对但参数或后续推理出错仍可能导致任务失败，因此两者并不互相决定；工具准确率应结合任务成功率综合评估。工具选择准确率本身不一定覆盖参数正确性，故选项 2 不严谨。

### fill_blank · None



**参考答案**：["任务总数", "总任务数", "任务总数量", "total tasks"]

**解析**：准确率是正确数占总数的比例，分母应为任务总数。

### fill_blank · None



**参考答案**：["多余", "冗余", "假阳性", "false positive"]

**解析**：期望不调用却调用了，称为多余调用或冗余调用，在分类视角下是假阳性。

### fill_blank · None



**参考答案**：["参数", "parameter", "arguments"]

**解析**：工具选对但参数不对，属于工具参数错误，是工具准确率评估中的一种细分错误。

### code_reading · None



**参考答案**：0.75

**解析**：逐项比对：weather==weather 对，weather!=exchange_rate 错，none==none 对，exchange_rate==exchange_rate 对，共 3/4 = 0.75。

### code_reading · None



**参考答案**：1 0

**解析**：第 2 个任务期望 none 但实际 search，属于多余调用（假阳性），false_positive=1；没有任何期望调用却实际为 none 的情况，false_negative=0。

### code_reading · None



**参考答案**：0.0；因为当任务数为 0 时直接做除法会触发除零错误，因此返回 0.0 作为边界保护。

**解析**：空列表时 n=0，若不处理会 ZeroDivisionError；代码通过三元表达式在 n>0 时才做除法，否则返回 0.0。

### scenario · None



**解析**：合理的设计应包含对每个任务标注期望工具（包括 none）、加入无需调用工具的对照任务、记录参数正确性、并按错误类型分类统计，最后以正确数/总数计算准确率。

### scenario · None



**解析**：工具选择准确率高但任务成功率低，可能是因为参数错误、多步任务中后续步骤出错、工具返回结果未被正确使用等。应补充参数级评估、多步逐步评估，并将工具准确率与任务成功率综合评估。

### scenario · None



**解析**：把参数错误计为选择正确会掩盖真实问题。应将工具选择准确率与参数准确率区分开来统计，分别报告，才能准确反映智能体的工具调用能力。

### single_choice · None



- [A] 智能体的历史调用记录
- [B] 用户的口头评价
- [C] 人工标注或规则定义的期望工具调用
- [D] 模型的参数量

**参考答案**：2

**解析**：准确率是一种有监督的匹配度量，需要以期望（参考答案）为基准。期望工具调用通常来自人工标注或规则定义。

### single_choice · None



- [A] 30%
- [B] 70%
- [C] 100%
- [D] 无法计算

**参考答案**：1

**解析**：工具选择准确率 = 正确选择数 / 总任务数 = 7 / 10 = 70%。

### single_choice · None



- [A] 任务需要查询天气，智能体调用了汇率工具
- [B] 任务需要查询天气，智能体调用了天气工具但把城市名写错
- [C] 任务不需要任何工具，智能体却调用了工具
- [D] 任务需要两个工具，智能体只调用了一个

**参考答案**：1

**解析**：工具选择错误指选错工具，工具参数错误指工具选对了但参数不对。选项 1 中工具选对、城市参数写错，属于参数错误。

### single_choice · None



- [A] 正确调用
- [B] 多余调用（假阳性）
- [C] 漏调用（假阴性）
- [D] 参数错误

**参考答案**：1

**解析**：期望是不调用却调用了，属于多余调用，也常称为假阳性。漏调用则是期望调用却未调用。

### single_choice · None



- [A] 多余调用
- [B] 漏调用（假阴性）
- [C] 参数错误
- [D] 工具选择正确

**参考答案**：1

**解析**：期望调用工具却未调用，属于漏调用，也称假阴性，是工具准确率评估中常见的一类错误。

### single_choice · None



- [A] 只看最后一步是否调用了工具
- [B] 逐步比对每一步的工具选择是否与期望一致
- [C] 只看总调用次数是否等于期望次数
- [D] 只看最终答案是否包含关键词

**参考答案**：1

**解析**：多步任务中每一步的工具选择都可能影响结果，逐步比对才能准确反映工具选择准确率。只统计次数或只看最后一步会掩盖中间错误。

### multi_choice · None



- [A] 工具选择错误
- [B] 工具参数错误
- [C] 多余调用
- [D] 漏调用
- [E] 输出文本错别字

**参考答案**：[0, 1, 2, 3]

**解析**：工具选择错误、参数错误、多余调用、漏调用都与工具调用直接相关，属于工具准确率评估范畴；输出文本错别字属于生成质量，不属于工具调用准确率。

### multi_choice · None



- [A] 为每个任务标注期望调用的工具
- [B] 包含一些不需要调用工具的任务作为对照
- [C] 只收集模型容易答对的简单任务
- [D] 为需要参数的任务标注关键参数
- [E] 把所有任务都设计成需要调用同一个工具

**参考答案**：[0, 1, 3]

**解析**：评估集需要期望标注和参数标注作为基准，并应包含不需调用工具的对照任务以检测多余调用。只收集简单任务或全部使用同一工具会导致评估偏差，不合理。
