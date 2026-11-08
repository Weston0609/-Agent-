# s7u3l1 Agent 模式之 ReAct：让模型学会「边想边做」 / Agent 设计模式：Plan-Execute（先规划，后执行）

> 来源 `content/lessons/s7u3l1.json`

## agent.pattern.react

# Agent 模式之 ReAct：让模型学会「边想边做」

## 一句话直觉

**ReAct（Reasoning + Acting，推理 + 行动）** 是让大语言模型（LLM，Large Language Model）像一位边思考边动手的助手：它先写下一段推理，再决定调用哪个工具，看到工具结果后继续推理，如此循环，直到能给出最终答案。

为什么要学它？因为**纯推理**的模型容易一本正经地胡说八道（幻觉，hallucination），而**纯行动**的模型又不知道下一步该做什么。ReAct 把两者交替进行，让 Agent（智能体）既能「想清楚」，又能「做到位」。

---

## 1. 为什么需要 ReAct：从「一问一答」到「边想边做」

传统 LLM 调用是「输入 prompt → 输出文本」的一次性过程。面对「北京今天比上海冷吗？」这类问题，模型只能靠记忆答，答案可能过期或错误。

ReAct 的核心思想是引入一个**循环（loop）**：

1. **Thought（思考）**：模型用自然语言写下当前推理。
2. **Action（行动）**：模型选择一个工具并给出参数。
3. **Observation（观察）**：把工具返回的结果喂回模型。
4. 回到第 1 步，直到模型输出 **Final Answer（最终答案）**。

这个循环让模型能用外部世界的真实信息不断修正自己的推理。

```python
# 用伪代码展示 ReAct 的核心循环，帮助建立整体印象

def react_loop(question: str, max_steps: int = 5):
    """最简 ReAct 循环：Thought -> Action -> Observation -> ..."""
    scratchpad = f"Question: {question}\n"  # 草稿纸，累积历史
    for step in range(max_steps):
        llm_output = fake_llm(scratchpad)       # 让 LLM 决定下一步
        if "Final Answer:" in llm_output:       # 若已能给答案，就收工
            return llm_output.split("Final Answer:")[-1].strip()
        scratchpad += llm_output + "\n"        # 记录 Thought + Action
        obs = run_tool(llm_output)              # 执行工具
        scratchpad += f"Observation: {obs}\n"  # 把观察结果写回草稿
    return "达到最大步数，未能完成"

def fake_llm(prompt: str) -> str:
    return "Thought: 我需要先查天气。\nAction: get_weather[city=北京]"

def run_tool(action: str) -> str:
    return "北京：-2℃"

print(react_loop("北京今天冷吗？"))  # 仅演示循环骨架
```

---

## 2. 三件套：Thought / Action / Observation 的协议

ReAct 的本质是一套**文本协议（text protocol）**。模型和外部程序约定好几个关键前缀词，程序靠解析它们来触发动作。

| 字段 | 含义 | 谁产生 |
|------|------|--------|
| `Thought` | 模型的内部推理 | LLM |
| `Action` | 要调用的工具名 + 参数 | LLM |
| `Observation` | 工具执行后的返回值 | 宿主程序 |
| `Final Answer` | 最终回答 | LLM |

只要约定好这套前缀，任何 LLM 都能被「套上」ReAct 外壳。

```python
import re

# 用正则从 LLM 输出里解析 Action 与参数
ACTION_RE = re.compile(r"Action:\s*(\w+)\[(.*?)\]")

def parse_action(text: str):
    """从 LLM 输出文本中抽取 (工具名, 参数字符串)。"""
    match = ACTION_RE.search(text)
    if not match:
        return None, None
    tool_name, args_str = match.group(1), match.group(2)
    return tool_name, args_str

sample = "Thought: 我需要查天气。\nAction: get_weather[city=北京]"
print(parse_action(sample))  # ('get_weather', 'city=北京')
```

---

## 3. 工具注册表：让 Agent 知道能「动手」做什么

ReAct 里的「行动」不是一个抽象概念，而是一张**工具表（tool registry）**：键是工具名，值是可调用的 Python 函数。每一轮模型选择工具，程序就查表执行。

```python
# 一个极简工具注册表
TOOLS = {}

def tool(name: str):
    """装饰器：把函数注册到 TOOLS 表里。"""
    def wrap(fn):
        TOOLS[name] = fn
        return fn
    return wrap

@tool("get_weather")
def get_weather(city: str) -> str:
    """假装查天气，返回字符串。"""
    data = {"北京": "-2℃ 晴", "上海": "6℃ 多云"}
    return data.get(city, "未知城市")

@tool("calc")
def calc(expr: str) -> str:
    """安全计算简单算术表达式。"""
    try:
        return str(eval(expr, {"__builtins__": {}}, {}))
    except Exception as e:
        return f"计算错误: {e}"

print(TOOLS.keys())          # dict_keys(['get_weather', 'calc'])
print(get_weather("北京"))   # -2℃ 晴
```

---

## 4. 组装一个最小可跑的 ReAct Agent

现在把前面几块拼起来：**解析 + 工具表 + 循环**，得到可运行的 ReAct 骨架。为了让代码离线可跑，用一个「假 LLM」模拟模型输出，你可以随时把它替换成真实的 OpenAI / 本地模型调用。

```python
import re

TOOLS = {}
def tool(name):
    def wrap(fn): TOOLS[name] = fn; return fn
    return wrap

@tool("get_weather")
def get_weather(city: str) -> str:
    return {"北京": "-2℃", "上海": "6℃"}.get(city, "未知")

ACTION_RE = re.compile(r"Action:\s*(\w+)\[(.*?)\]")

def parse_kv(args_str: str):
    """把 'city=北京' 解析成 {'city': '北京'}。"""
    kv = {}
    for part in args_str.split(","):
        if "=" in part:
            k, v = part.split("=", 1)
            kv[k.strip()] = v.strip()
    return kv

def fake_llm(scratchpad: str) -> str:
    """用一个基于规则的'假模型'演示协议；真实使用时换为真正的 LLM。"""
    if "Observation:" not in scratchpad:
        return "Thought: 先查北京天气。\nAction: get_weather[city=北京]"
    return "Thought: 已经知道结果。\nFinal Answer: 北京 -2℃。"

def react(question: str, max_steps: int = 5) -> str:
    scratchpad = f"Question: {question}\n"
    for _ in range(max_steps):
        out = fake_llm(scratchpad)
        scratchpad += out + "\n"
        if "Final Answer:" in out:
            return out.split("Final Answer:")[-1].strip()
        m = ACTION_RE.search(out)
        if not m:
            return "解析失败，终止"
        name, args_str = m.group(1), m.group(2)
        obs = TOOLS[name](**parse_kv(args_str)) if name in TOOLS else "未知工具"
        scratchpad += f"Observation: {obs}\n"
    return "超过最大步数"

print(react("北京今天冷不冷？"))
```

---

## 5. 工程化要点：让 ReAct 从玩具走向生产

一个能上线的 ReAct Agent，需要处理下面这些工程问题：

1. **最大步数（max_steps）**：防止死循环。
2. **超时与重试**：工具调用可能失败。
3. **输出格式约束**：用 JSON 或函数调用（function calling）让解析更稳。
4. **上下文长度管理**：scratchpad 会越来越长，要截断或摘要。
5. **可观测性（observability）**：记录每一轮 Thought/Action/Observation，方便调试。
6. **安全**：工具执行要沙箱化，禁止 `eval` 执行任意代码。

```python
# 演示带超时与日志的健壮性增强
import time, json

def safe_call(fn, timeout=2.0, **kwargs):
    start = time.time()
    result = fn(**kwargs)
    elapsed = time.time() - start
    if elapsed > timeout:
        return f"工具超时: {elapsed:.2f}s"
    return result

def log_step(step: int, kind: str, content: str):
    """结构化日志，便于事后回放。"""
    print(json.dumps({"step": step, "kind": kind, "content": content}, ensure_ascii=False))

log_step(1, "Thought", "先查北京天气")
log_step(1, "Action", "get_weather(city=北京)")
print(safe_call(get_weather, city="北京"))
```

---

## 小结

- ReAct = **推理（Reasoning）+ 行动（Acting）**，通过 Thought/Action/Observation 循环让 Agent 边想边做。
- 关键部件：**文本协议、工具注册表、循环控制器、解析器**。
- 工程化重点：步数限制、超时重试、格式约束、可观测性、安全沙箱。
- 它是一切现代 Agent（如 LangChain Agent、AutoGPT、OpenAI Assistants）的思想基础。

---

## 动手练习

**任务**：给自己写一个能回答「两数相减结果是否是质数」的 ReAct Agent。

要求：
1. 注册两个工具：`subtract[a,b]` 返回 `a-b`；`is_prime[n]` 返回 `True/False`。
2. 用「假 LLM」模拟三轮：先 `subtract`，拿到 Observation 后再 `is_prime`，最后给出 Final Answer。
3. 打印每一步的 `Thought / Action / Observation`，方便观察循环。
4. 加入 `max_steps=5` 和「未知工具」的兜底处理。

提示：可以复用本讲义第 4 节的骨架，把工具表和 fake_llm 换掉即可。完成后再尝试把 `fake_llm` 换成真实的 OpenAI `chat.completions` 调用，只需把 Tool 表转成函数描述放入 prompt 即可。

```python
import re

# ===== 工具注册表 =====
TOOLS = {}

def tool(name: str):
    def wrap(fn):
        TOOLS[name] = fn
        return fn
    return wrap

@tool("get_weather")
def get_weather(city: str) -> str:
    return {"北京": "-2℃ 晴", "上海": "6℃ 多云"}.get(city, "未知城市")

@tool("calc")
def calc(expr: str) -> str:
    try:
        return str(eval(expr, {"__builtins__": {}}, {}))
    except Exception as e:
        return f"计算错误: {e}"

# ===== 协议解析 =====
ACTION_RE = re.compile(r"Action:\s*(\w+)\[(.*?)\]")

def parse_kv(args_str: str):
    kv = {}
    for part in args_str.split(","):
        if "=" in part:
            k, v = part.split("=", 1)
            kv[k.strip()] = v.strip()
    return kv

# ===== 假 LLM，方便离线运行 =====
def fake_llm(scratchpad: str) -> str:
    if "Observation:" not in scratchpad:
        return "Thought: 我需要先查询北京天气。\nAction: get_weather[city=北京]"
    return "Thought: 已有结果，可以回答。\nFinal Answer: 北京今天 -2℃，很冷。"

# ===== ReAct 主循环 =====
def react(question: str, max_steps: int = 5) -> str:
    scratchpad = f"Question: {question}\n"
    for step in range(1, max_steps + 1):
        out = fake_llm(scratchpad)
        print(f"--- Step {step} ---\n{out}")
        scratchpad += out + "\n"
        if "Final Answer:" in out:
            return out.split("Final Answer:")[-1].strip()
        m = ACTION_RE.search(out)
        if not m:
            return "解析失败，终止"
        name, args_str = m.group(1), m.group(2)
        obs = TOOLS[name](**parse_kv(args_str)) if name in TOOLS else "未知工具"
        print(f"Observation: {obs}")
        scratchpad += f"Observation: {obs}\n"
    return "超过最大步数"

if __name__ == "__main__":
    print("最终答案:", react("北京今天冷不冷？"))
```

## agent.pattern.plan_execute

# Agent 设计模式：Plan-Execute（先规划，后执行）

> 一句话直觉：复杂的任务不要一步到位，先让 AI 拆成步骤清单，再一步一步去做，比“一口气干完”更稳、更准、更好调试。

---

## 一、为什么需要 Plan-Execute？

当我们让大语言模型（LLM，Large Language Model）直接完成一个复杂任务时（比如“帮我研究三家竞品并写一份报告”），它常常会：
- 遗漏步骤；
- 顺序错乱；
- 中途跑偏；
- 出错后不知道从哪继续。

**Plan-Execute 模式**把任务拆成两个阶段：

1. **Plan（规划）**：先把任务拆成有序的步骤清单。
2. **Execute（执行）**：逐步执行每一步，可以让不同步骤用不同工具或不同提示词。

这样做的好处是**可解释、可调试、可复用**：你能看到 Agent 到底想干嘛，也能在任一步骤插桩、重试或替换。

---

## 二、Plan-Execute 的最小骨架

最朴素的实现只有两个函数：

```python
from typing import List

def plan(task: str) -> List[str]:
    \"\"\"把任务拆成步骤列表。\"\"\"
    ...

def execute(step: str) -> str:
    \"\"\"执行单个步骤，返回结果。\"\"\"
    ...
```

然后把它们串起来：

```python
def run(task: str) -> List[str]:
    results = []
    for step in plan(task):
        results.append(execute(step))
    return results
```

**关键结论**：Plan-Execute 的本质是“O(=结构化输出) + 循环”。规划阶段把自然语言任务转成**结构化的步骤列表**（通常是 `List[str]` 或 `List[dict]`），执行阶段就是一个 for 循环。

---

## 三、把 Planner 交给 LLM

零基础阶段可以先用规则模拟，工程级阶段就要让 LLM 输出结构化步骤。做法是：**在提示词中明确要求返回 JSON 数组**。

```python
import json
from typing import List

PLANNER_PROMPT = \"\"\"
你是一个规划器。把用户任务拆成 3~6 个有序步骤。
只输出 JSON 数组，元素是字符串，不要任何解释。
任务：{task}
\"\"\"

def plan_with_llm(llm, task: str) -> List[str]:
    raw = llm(PLANNER_PROMPT.format(task=task))
    steps = json.loads(raw)          # 若模型可能加代码块，需先 strip
    assert isinstance(steps, list)
    return [str(s) for s in steps]
```

**要点**：
- 明确要求 JSON，避免模型返回“第一步……第二步……”这种非结构化文本。
- 加 `assert` 或 `try/except` 做校验，这是工程级与玩具代码的分水岭。

---

## 四、执行阶段：把每个步骤当一次独立调用

执行阶段不要偷懒把“原任务 + 全部步骤 + 当前步骤”一股脑塞给 LLM，**要让每一步的上下文最小必要**。这样能减少幻觉（hallucination）和串扰。

```python
def execute_step(llm, task: str, step: str, history: List[str]) -> str:
    prompt = f\"\"\"
总任务：{task}
已完成：{history}
当前步骤：{step}
请只完成当前步骤，并输出这一步的结果。
\"\"\"
    return llm(prompt)
```

**关键结论**：Plan 是“共享上下文”，Execute 是“隔离上下文”。每个步骤只关心自己和已经完成的部分，避免上下文越长越糊涂。

---

## 五、加上重规划（Re-plan）才能实用

真实任务里，某一步失败或输出不符合预期是常态。工程级 Plan-Execute 会在执行中检查结果，必要时**触发重规划**。

```python
def run_with_replan(llm, task: str, max_rounds: int = 3) -> List[str]:
    steps = plan_with_llm(llm, task)
    results: List[str] = []
    for _ in range(max_rounds):
        failed = False
        for step in steps:
            out = execute_step(llm, task, step, results)
            if not out or \"失败\" in out:
                failed = True
                break
            results.append(out)
        if not failed:
            return results
        # 失败则重新规划剩下的部分
        steps = plan_with_llm(llm, f\"原任务：{task}；已完成：{results}\")
    return results
```

**要点**：
- 重规划时把“已完成结果”作为输入，避免重复劳动。
- 设置 `max_rounds` 防死循环，这是生产环境的必备。

---

## 六、工程级建议小结

| 维度 | 建议 |
|---|---|
| 规划输出 | 强制 JSON，校验类型 |
| 步骤粒度 | 3~6 步，太细碎反而增加 token |
| 执行上下文 | 只给当前步骤 + 已完成的摘要 |
| 失败处理 | 检查输出 + 重规划 + 最大轮数 |
| 可观测性 | 每步日志（logging）记输入输出 |
| 可测试性 | Planner / Executor 解耦，方便单测 |

---

## 七、动手练习

**任务**：实现一个 `ResearchAgent`，用 Plan-Execute 模式完成“调研 3 个 Python Web 框架并输出对比”。

要求：
1. 实现 `plan(task) -> List[str]`，用**规则**返回 5 步（如：列出候选框架 → 收集资料 → 对比维度 → 写结论 → 整理输出）。
2. 实现 `execute(step) -> str`，用一个假的 `fake_llm(prompt)` 函数（谁调用都返回 `f\"已完成：{prompt[:20]}...\"`）。
3. 写 `run(task)` 依次执行并打印每一步结果。
4. **进阶**：给 `execute` 加一个“随机失败”模拟，失败时触发重规划。

完成后你会对 Plan-Execute 的“结构化规划 + 循环执行 + 失败容错”有完整的手感。

```python
from typing import List
import json

# ---------- 1. 一个假的 LLM，用于演示（真实项目换成 API 调用） ----------
def fake_llm(prompt: str) -> str:
    # 若是规划阶段，返回 JSON 步骤列表
    if "规划器" in prompt or "JSON" in prompt:
        return json.dumps([
            "列出候选项",
            "收集每个候选项的信息",
            "按统一维度对比",
            "给出结论"
        ], ensure_ascii=False)
    # 否则当作执行阶段
    return f"已完成步骤：{prompt[:30]}..."

# ---------- 2. Planner ----------
def plan(task: str) -> List[str]:
    prompt = f"你是规划器，把任务拆成 3~6 步，只输出 JSON 数组。任务：{task}"
    raw = fake_llm(prompt)
    steps = json.loads(raw)
    assert isinstance(steps, list) and all(isinstance(s, str) for s in steps)
    return steps

# ---------- 3. Executor ----------
def execute(task: str, step: str, history: List[str]) -> str:
    prompt = f"任务：{task}\n已完成：{history}\n当前步骤：{step}"
    return fake_llm(prompt)

# ---------- 4. 串联：Plan -> Execute ----------
def run(task: str) -> List[str]:
    steps = plan(task)
    print("[Plan]", steps)
    results: List[str] = []
    for i, step in enumerate(steps, 1):
        out = execute(task, step, results)
        print(f"[Step {i}] {step} -> {out}")
        results.append(out)
    return results

if __name__ == "__main__":
    run("调研 3 个 Python Web 框架并输出对比")
```


---

## 本课题目

### single_choice · None



- [A] 先一次性输出最终答案，再补充说明推理过程
- [B] 在每一步交替输出自然语言推理与一个可供外部执行的动作，并根据动作返回的结果继续推理
- [C] 只输出工具调用的 JSON，不输出任何自然语言推理
- [D] 把所有可能的工具调用全部并行发出，最后再统一汇总

**参考答案**：1

**解析**：ReAct 的关键在于推理（Thought）与行动（Action）交替进行，并把环境返回的 Observation 反馈到下一轮推理中。A 是事后解释，C 丢失了推理轨迹，D 忽略了 Observation 对后续决策的影响。

### single_choice · None



- [A] 外部工具返回的 Observation 太长，模型无法处理
- [B] 提示或输出解析规则没有强制要求每轮必须产生一个可执行动作，模型停留在纯推理状态
- [C] 模型上下文窗口不足，无法记住之前的思考
- [D] 温度参数被设置为 0，导致模型不输出动作

**参考答案**：1

**解析**：ReAct 的循环依赖「每轮产出一个动作」。若提示未约束输出格式或解析器允许纯文本通过，模型可能一直停留在 Thought 阶段。温度、上下文长度、Observation 长度都可能影响效果，但不是这种「从不行动」现象的直接原因。

### single_choice · None



- [A] 该问题可能不需要外部信息，模型判断可直接作答
- [B] ReAct 模式不允许直接回答，一定是实现有 bug
- [C] 模型一定没有读取到工具列表
- [D] Observation 一定被清空了

**参考答案**：0

**解析**：ReAct 并不强制每次都必须调用工具。如果模型判断问题可由既有知识直接回答，跳过 Action 是允许的。B 把模式当成硬约束，C/D 是无依据的推断。

### single_choice · None



- [A] 模型参数被修改
- [B] 上下文迅速膨胀，并可能让模型重复执行相同动作
- [C] 工具调用会被自动禁用
- [D] 模型的温度参数被重置

**参考答案**：1

**解析**：无节制地累积 Observation 会消耗上下文窗口，并可能诱导模型重复相同动作（因为看起来任务尚未完成）。常见缓解方式是摘要、截断或只保留关键片段。A/C/D 都不是真实机制。

### single_choice · None



- [A] 它必须被外部工具执行后才能生效
- [B] 它是对当前状态的自然语言推理，用于决定下一步动作
- [C] 它必须与 Action 输出完全相同
- [D] 它是可选的，去掉后 ReAct 效果不变

**参考答案**：1

**解析**：Thought 是模型内部的推理表征，用于指导动作选择；它本身不被执行。它与 Action 是不同字段，去掉后智能体就退化为「直接动作」的策略，丧失 ReAct 的推理-行动耦合优势。

### single_choice · None



- [A] 提高生成时的随机性
- [B] 在提示中给出工具参数的 schema 以及正确/错误示例
- [C] 增加最大轮数到 100
- [D] 把 Observation 全部翻译成英文

**参考答案**：1

**解析**：参数错误主要源于模型对参数格式与含义理解不足。给出 schema 和正反示例是最直接的约束手段。随机性、轮数、语言转换都不是针对参数正确性的直接措施。

### single_choice · None



- [A] 把异常信息作为 Observation 反馈给模型，让它决定如何调整
- [B] 静默吞掉异常，继续下一轮
- [C] 直接把异常堆栈作为最终答案返回给用户
- [D] 回滚到上一轮并重复执行同一个动作

**参考答案**：0

**解析**：ReAct 的鲁棒性来自「反馈闭环」。把错误信息作为 Observation 让模型换参数或换工具，是符合范式的做法。静默吞掉会丢失信息，把堆栈当答案对用户无意义，无条件重试可能造成死循环。

### single_choice · None



- [A] 调用计算器求一个表达式的值
- [B] 查询数据库获取某条记录
- [C] 在模型内部直接修改自己的权重参数
- [D] 调用搜索接口获取最新资料

**参考答案**：2

**解析**：ReAct 的 Action 是通过外部接口可执行的离散操作。推理阶段的模型不能也不应在线修改自身权重。A/B/D 都是典型的外部工具调用。

### single_choice · None



- [A] 工具返回的 Observation 被截断或未拼回上下文，模型不知道已经执行过
- [B] 模型的上下文窗口过大
- [C] 工具数量太少
- [D] 用户的问题过于简单

**参考答案**：0

**解析**：重复相同动作通常意味着模型看不到或误解了上轮结果。Observation 未回填、被截断、或被摘要时丢掉了关键信息，都会导致这种循环。上下文更大、工具更少、问题更简单都不是直接原因。

### single_choice · None



- [A] ReAct 总是一次调用就能完成，因此更快
- [B] ReAct 需要多轮模型调用与工具执行，延迟和成本通常更高
- [C] ReAct 不需要任何提示词
- [D] ReAct 可以完全避免模型幻觉

**参考答案**：1

**解析**：ReAct 通过多轮推理和外部调用换取事实性与可调整性，代价是更多的模型调用、工具延迟与 token 消耗。它不能完全消除幻觉，也需要提示与格式约束。

### single_choice · None



- [A] 让模型在 Thought 中输出一个特殊标记或使用专门的结束动作，表示不再需要调用工具
- [B] 固定跑满最大轮数才停止
- [C] 只要出现 Observation 就判定完成
- [D] 由工具自行决定何时结束并关闭进程

**参考答案**：0

**解析**：ReAct 循环需要一个可识别的终止信号，常见做法是模型输出 final answer 标记或调用一个终结动作。跑满最大轮数是兜底而非正常终止，出现 Observation 并不代表任务完成，工具通常不具备全局停止权。

### single_choice · None



- [A] 减少模型需要生成的 token 总数
- [B] 帮助模型模仿正确的输出结构，提高格式服从率
- [C] 让模型不再需要工具描述
- [D] 自动提升模型的基础能力

**参考答案**：1

**解析**：few-shot 示例的作用是示范输出结构与循环模式，提升格式服从性与动作选择质量。它不减少总 token，也不能替代工具描述，更不会改变模型本身的能力。

### single_choice · None



- [A] Observation → Thought → Action
- [B] Action → Thought → Observation
- [C] Thought → Action → Observation
- [D] Thought → Observation → Action

**参考答案**：2

**解析**：ReAct 的典型顺序是：先产生推理（Thought），据此选择一个动作（Action），执行该动作后得到环境反馈（Observation），再将 Observation 作为下一轮 Thought 的输入。

### single_choice · None



- [A] 模型是否被要求只输出 JSON
- [B] Observation 是否真的进入了下一轮提示词，以及提示中是否有鼓励「根据观察调整」的指令
- [C] 工具是否用 Python 编写
- [D] 用户问题是否过长

**参考答案**：1

**解析**：「看到结果却不变招」通常意味着反馈没有进入上下文，或提示未强调依据 Observation 调整。检查提示拼装与指令是最优先的。输出格式、工具语言、问题长度都不是首要因素。

### single_choice · None



- [A] 它是模型对自身推理过程的总结，不依赖外部环境
- [B] 它是外部工具或环境对前一动作的返回结果，作为下一轮推理的输入
- [C] 它是用户最初提出的问题，只在第一轮出现
- [D] 它是模型在无法继续时输出的终止标记

**参考答案**：1

**解析**：Observation 是环境/工具对 Action 的执行结果，它被拼回上下文，影响下一轮 Thought 和 Action，是 ReAct 与纯思维链（CoT）的关键差别。

### single_choice · None



- [A] 忽略该 Observation，直接编造一个答案
- [B] 把该 Observation 原样重复作为最终答案输出
- [C] 在下一轮 Thought 中考虑换关键词、换工具或承认无法完成，再决定下一步 Action
- [D] 立即抛出异常终止整个循环

**参考答案**：2

**解析**：ReAct 的价值在于把失败反馈纳入推理。合理的做法是在下一轮 Thought 中调整策略（换查询、换工具或给出无法完成的结论）。A 违背忠实性，B 不是任务答案，D 过于粗暴且不具备鲁棒性。

### single_choice · None



- [A] 生成的推理文本更长，因此答案更准确
- [B] 模型参数更多，因此推理能力更强
- [C] 能够通过动作与环境交互，把真实信息引入推理过程
- [D] 不需要任何提示词，模型会自动进入推理状态

**参考答案**：2

**解析**：ReAct 的核心增益是「与外部环境交互」：动作可以查询、计算、访问数据库，Observation 为推理提供事实依据。文本长度、参数规模、提示词是否存在都不是其本质区别。

### single_choice · None



- [A] 模型仍然可以完成多步任务，只是日志更短
- [B] 模型只有一次思考与一次行动机会，无法根据 Observation 修正后续决策
- [C] 模型会进入无限循环
- [D] 模型会自动切换为思维链模式

**参考答案**：1

**解析**：ReAct 需要多轮迭代才能利用 Observation 调整策略。最大轮数为 1 时，Observation 无法进入第二轮推理，退化为「一步动作 + 直接回答」。

### single_choice · None



- [A] 使用明确的分隔标记把 Thought、Action、Action Input 分开
- [B] 把所有内容写成一段自由散文，没有固定字段或结束标记
- [C] 要求 Action 只能是预定义工具名之一
- [D] 在提示中给出完整的循环示例作为格式示范

**参考答案**：1

**解析**：ReAct 依赖程序从模型输出中抽取 Action 及其输入。自由散文缺乏可解析结构，会导致抽取失败或误抽取。分隔标记、枚举工具名、few-shot 示例都是提升稳定性的常见做法。

### single_choice · None



- [A] 两个都执行，把两个 Observation 都拼回上下文
- [B] 只执行第一个，忽略第二个
- [C] 丢弃本轮输出并提示模型重新生成，要求本轮只给出一个 Action
- [D] 任选一个执行，并在下一轮禁止模型再使用工具

**参考答案**：2

**解析**：ReAct 的设计是每轮一个动作，以保证 Thought–Action–Observation 的因果链清晰。出现多个动作通常意味着格式违约，应重新生成而不是随意选择（A 会破坏因果链，B/C 的随意性会引入不可预测行为）。

### single_choice · None



- [A] 减少模型输出的 token 数量
- [B] 提高模型选择正确动作并正确构造参数的几率
- [C] 让模型不再需要 Observation
- [D] 绕过最大轮数限制

**参考答案**：1

**解析**：工具描述是模型进行动作选择的依据。描述越清晰（名称、用途、参数类型与示例），越不容易选错工具或传错参数。它不改变 Observation 的必要性，也与轮数限制无关。

### single_choice · None



- [A] 每一步都根据上一步的观察结果即时决定下一个动作
- [B] 先产出一个完整的、分解好的任务步骤清单，再按清单逐项执行
- [C] 把所有工具调用并行发出，再统一汇总结果
- [D] 完全不做规划，直接由模型一次性生成最终答案

**参考答案**：1

**解析**：Plan-and-Execute 的关键是「先规划、后执行」：规划器一次性给出分解后的步骤序列，执行器再逐步完成。选项 0 描述的是 ReAct 式的逐步推理-行动循环，选项 2 描述的是并行工具调用，选项 3 是无规划的直出，均不符合。

### single_choice · None



- [A] Plan-and-Execute 通常减少了对大模型的调用次数，因为规划只做一次而执行按步进行
- [B] Plan-and-Execute 完全不需要执行阶段的模型调用
- [C] 逐步推理模式一定比 Plan-and-Execute 更节省 token
- [D] Plan-and-Execute 无法处理多步骤任务

**参考答案**：0

**解析**：Plan-and-Execute 把「规划」与「执行」分离，规划只需一次较大调用，执行阶段可以用更小/更便宜的模型按步执行，总体上减少了昂贵模型的反复调用。它仍需要执行阶段的模型调用，也能处理多步骤任务，因此其余选项错误。

### multi_choice · None



- [A] 规划阶段可以一次性看到全局，减少局部最优导致的任务遗漏
- [B] 执行阶段可用更小或更廉价的模型逐步完成，降低成本
- [C] 执行器可以按步骤并行调度互不依赖的子任务
- [D] 完全消除模型幻觉，保证输出一定正确
- [E] 无需任何外部工具即可完成所有任务

**参考答案**：[0, 1, 2]

**解析**：全局规划、降低执行阶段模型成本、以及按依赖并行调度都是 Plan-and-Execute 的典型好处。但它不能消除幻觉，也不能脱离外部工具完成所有任务。

### multi_choice · None



- [A] 计划器负责把复杂任务分解为可执行的步骤序列
- [B] 执行器负责实际调用工具、收集观察结果
- [C] 计划器和执行器可以由同一个语言模型扮演，但职责不同
- [D] 执行器的反馈可以回流给计划器，从而驱动重规划
- [E] 执行器一旦启动，就必须严格执行原计划、不允许任何改变

**参考答案**：[0, 1, 2, 3]

**解析**：两个角色可以共用同一模型，但逻辑职责不同：规划产出步骤，执行落实步骤，并把反馈回流以支持重规划。执行器并非不可变更，重规划正是对计划进行调整。

### multi_choice · None



- [A] 必须先明确步骤之间的数据依赖关系
- [B] 需要处理并发写同一资源时的冲突
- [C] 并行步骤的失败要有统一的汇总和重试策略
- [D] 并行步骤必须使用同一个随机种子才能保证正确性

**参考答案**：[0, 1, 2]

**解析**：并行执行的前提是依赖清晰，其次要处理资源竞争与失败汇总。随机种子与并行正确性无直接关系，属于错误干扰项。

### multi_choice · None



- [A] 任务步骤多，逐步推理经常在中间迷路、遗漏后续子任务
- [B] 每个子任务都依赖前面的输出，且数量固定、可预先列举
- [C] 需要在执行前先向用户展示完整任务清单以获得确认
- [D] 任务只是一次简单的加法运算

**参考答案**：[0, 1, 2]

**解析**：步数多容易迷路、依赖强且可预列举、需要展示清单给用户确认，这些都是 Plan-and-Execute 的适用信号。简单加法属于过度设计，不构成切换理由。

### fill_blank · None



**参考答案**：["规划器", "计划器", "planner", "Planner"]

**解析**：重规划由规划器（Planner）执行：收到执行器反馈后修订剩余步骤。

### fill_blank · None



**参考答案**：["执行器", "Executor", "executor"]

**解析**：执行器（Executor）负责落实每一步的具体动作并收集结果。

### fill_blank · None



**参考答案**：["工具", "工具列表", "tools", "tool"]

**解析**：每步需要声明可用工具（以及参数），执行器才知道该调用哪个具体函数。

### code_reading · None



**参考答案**：当某步出错时，代码调用 planner.replan(...) 让规划器基于原任务、原计划、出错步骤和错误信息生成一份新的计划，赋值给 plan 后立即 break 跳出当前 for 循环。break 的作用是中止对旧计划的继续执行，避免沿着已经失效的旧步骤序列继续往下走，从而让后续逻辑可以用新的 plan 重新开始执行。

**解析**：此伪代码演示 Plan-and-Execute 的重规划触发：出错 → 重新规划 → 跳出旧循环。break 防止在旧计划上继续执行错误步骤。

### code_reading · None



**参考答案**：返回字符串 "dependency_missing: " 加上该步骤的名称。这样设计的好处是在执行前就检查数据依赖是否满足，能及早发现计划中步骤顺序安排错误，避免把不满足依赖的步骤强行执行而导致的隐蔽错误或崩溃。

**解析**：该代码在每步执行前检查依赖，未满足则提前返回带步骤名的错误信息，属于「依赖前置检查」的典型做法。

### scenario · None



**解析**：该场景的关键失败模式是逐步推理在长任务中迷失全局，适合切换到 Plan-and-Execute：先一次性产出步骤清单（搜索、抓取、提取、汇总、撰写），明确步骤依赖，执行时按步推进；对抓取失败等异常做重规划。这样能避免遗漏后续子任务。

### single_choice · None



- [A] 直接放弃整个任务并返回错误
- [B] 忽略失败步骤，继续执行第 4 步及之后的所有步骤
- [C] 把失败信息反馈给规划器（或重规划模块），让它修订后续步骤后再继续
- [D] 重新从第 1 步开始无条件重跑整份计划

**参考答案**：2

**解析**：Plan-and-Execute 的经典增强是「重规划」（re-plan）：执行器把观察/错误反馈给规划器，规划器据此调整剩余步骤。直接放弃或忽略失败都不合理；无条件重跑整份计划代价高且可能死循环。

### scenario · None



**解析**：健壮方案应把第 5 步的超时作为观察/错误反馈给规划器，触发重规划：考虑重试、更换工具或调整后续步骤。这样任务不必整体失败，可继续被完成。

### single_choice · None



- [A] 负责拆解用户意图并生成完整步骤清单
- [B] 负责按当前步骤调用工具并收集观察结果，把结果交给下一步或反馈给规划器
- [C] 只负责把最终答案格式化输出，不参与任何工具调用
- [D] 负责决定是否终止整个智能体进程

**参考答案**：1

**解析**：执行器接收规划好的单步（或一组步骤），完成工具调用、结果收集，并把观察结果传递下去或反馈给规划器。步骤拆解是规划器的职责，格式化输出与进程终止都不是执行器的核心定义。

### single_choice · None



- [A] 一句话闲聊，需要极低延迟返回
- [B] 需要多步骤、跨多个工具、有明确依赖顺序的复杂任务
- [C] 只需要一次简单的字符串大小写转换
- [D] 任务无法被分解为任何子步骤

**参考答案**：1

**解析**：Plan-and-Execute 的优势在于面对多步骤、工具依赖强的复杂任务时，先有全局规划可以保证步骤有序、减少遗漏。闲聊、简单单步操作或不可分解任务，用该模式属于过度设计。

### single_choice · None



- [A] 无法使用任何外部工具
- [B] 初始规划一旦偏离真实情况，后续步骤会沿着错误路线执行，直到被重规划纠正
- [C] 不需要任何语言模型参与
- [D] 只能处理单步任务

**参考答案**：1

**解析**：因为计划是先于执行整体生成的，如果初始假设与实际环境不符，错误会沿着计划传播。这正是需要重规划机制的原因。Plan-and-Execute 依然用工具、用模型，也能处理多步任务。

### single_choice · None



- [A] 只在规划阶段被使用，用于生成步骤清单
- [B] 只在执行阶段被使用，用于决定调用哪个具体函数
- [C] 在规划阶段和执行阶段都可能被使用，用于约束可用动作空间
- [D] 只在最后总结阶段被使用

**参考答案**：2

**解析**：规划时规划器需要知道有哪些可用工具，才能把步骤映射到工具上；执行时执行器也要根据工具描述构造调用参数。因此两个阶段都可能用到工具描述。

### single_choice · None



- [A] 一个字符串，只是自然语言概述
- [B] 一个有序的步骤列表，每步包含描述、可用工具和预期输出
- [C] 一个随机整数种子
- [D] 一个包含所有工具源码的字典

**参考答案**：1

**解析**：实用系统通常把计划表示为有序步骤列表，每步包含任务描述、可用的工具/参数和预期输出，方便执行器按步消费。纯自然语言概述对执行器帮助有限，种子和工具源码都不是计划表示。

### single_choice · None



- [A] 减少模型的 token 消耗
- [B] 避免执行时某步需要的数据尚未被上游步骤产出，导致中途失败
- [C] 防止工具被重复调用
- [D] 强制所有步骤并行运行

**参考答案**：1

**解析**：依赖声明能让执行器确定步骤顺序或并行度。如果步骤需要的数据尚未产出，就会执行失败。明确依赖可以避免这种顺序性错误。

### single_choice · None



- [A] 某步工具调用返回错误
- [B] 执行结果与规划时的预期输出明显不符
- [C] 执行器发现需要执行一个新步骤，而它不在原计划中
- [D] 系统检测到用户界面颜色发生变化

**参考答案**：3

**解析**：重规划的触发来自执行层面的反馈：工具报错、结果异常、出现计划外步骤等。用户界面颜色与业务规划无关，不属于触发条件。
