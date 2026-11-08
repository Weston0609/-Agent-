# s7u5l1 `agent.multi.supervisor` 教学讲义 / 多智能体分层架构 (Hierarchical Multi-Agent Architecture)

> 来源 `content/lessons/s7u5l1.json`

## agent.multi.supervisor

# `agent.multi.supervisor` 教学讲义

## 一句话直觉

当你让 AI 只做一件事的时候，你只需要对一个 Agent 说一句话；但当任务需要「先查资料、再写代码、再验证、再汇报」时，单个 Agent 容易乱，于是我们引入一个 **Supervisor（监督者/主管）Agent** 来统筹其他子 Agent —— 这就是 `agent.multi.supervisor` 要解决的问题。

---

## 1. 为什么要学它：从单 Agent 到多 Agent

一个单独的 Agent（智能体）本质上就是一个「会调用工具的 LLM 循环」：

```
用户 → LLM → 决定调用工具 → 观察结果 → LLM → ... → 最终回答
```

当任务变复杂，这个循环会遇到三个真实问题：

1. **上下文爆炸**：一个 Agent 要记住所有历史，Prompt 会越来越长。
2. **角色冲突**：同一个 Agent 既要当「研究员」又要当「程序员」又要当「审查员」，容易互相干扰。
3. **无法并行**：串行执行，效率低。

**多 Agent（Multi-Agent）** 的思路是：把任务拆给不同的专职 Agent。
**Supervisor（监督者）** 则是这些 Agent 里的「组长」：它不亲自干重活，只负责**决定下一步交给谁**。

---

## 2. Supervisor 的核心结构

一个最小可用的 Supervisor 由三部分组成：

| 角色 | 职责 | 类比 |
| --- | --- | --- |
| **Supervisor** | 读当前状态，决定下一个该谁做 | 项目经理 |
| **Workers（子 Agent）** | 各自完成自己的专长任务 | 研究员 / 编码员 / 审查员 |
| **Shared State（共享状态）** | 存储所有消息和中间产物 | 项目文档 |

执行流程可以画成一张「状态机」图：

```
       ┌────────────┐
       │ Supervisor │◄──────┐
       └─────┬──────┘       │
             │ 路由决策        │ 完成后回到 Supervisor
             ▼               │
   ┌────┬────┬────┐          │
   │ R  │ C  │ V  │──────────┘
   └────┴────┴────┘
   Researcher / Coder / Verifier
```

关键点：**Supervisor 本身永远不返回最终答案**，它只返回「下一个节点是谁」或「FINISH」。这是它与普通 Agent 最大的区别。

---

## 3. 用一个最小的 Python 例子理解路由

先不引入任何框架，用纯 Python 模拟 Supervisor 的决策逻辑，这样你能看清本质：

```python
# 极简 Supervisor 决策函数：只做「下一步交给谁」的判断
from typing import Literal

Node = Literal["Researcher", "Coder", "Verifier", "FINISH"]

def supervisor(state: dict) -> Node:
    """根据共享状态决定下一个执行者。"""
    history = state["history"]
    if "research" not in state:
        return "Researcher"      # 第一步：先查资料
    if "code" not in state:
        return "Coder"          # 第二步：再写代码
    if "verified" not in state:
        return "Verifier"      # 第三步：验证
    return "FINISH"              # 全部完成
```

上面这段代码展示的就是 **Supervisor Pattern（监督者模式）** 的全部精髓：**用状态决定路由，而不是用 LLM 硬算**。真实工程中这一步通常由 LLM 完成（让模型返回下一个节点名），但逻辑完全一致。

---

## 4. 用 LLM 充当 Supervisor 的标准写法

生产级的 Supervisor 通常让 LLM 输出结构化路由决策。下面是可运行骨架（伪 LLM，方便本地无 API 运行）：

```python
import json
from typing import Literal, TypedDict

class State(TypedDict):
    task: str
    history: list[dict]

# 用一个假 LLM 代替真正的模型调用，方便离线测试
def fake_llm(prompt: str) -> str:
    # 真实场景里这里换成 openai.chat.completions.create(...)
    if "research" not in prompt:
        return json.dumps({"next": "Researcher"})
    if "code" not in prompt:
        return json.dumps({"next": "Coder"})
    return json.dumps({"next": "FINISH"})

def supervisor(state: State) -> str:
    prompt = f"""你是主管 Agent。当前任务：{state['task']}
历史：{state['history']}
请从 [Researcher, Coder, FINISH] 中选下一个执行者，返回 JSON：{{\"next\": ...}}"""
    raw = fake_llm(prompt)
    return json.loads(raw)["next"]

# 模拟一轮调度
state = {"task": "写一个冒泡排序并测试", "history": []}
print(supervisor(state))                    # Researcher
state["history"].append({"agent": "Researcher", "out": "research"})
print(supervisor(state))                    # Coder
state["history"].append({"agent": "Coder", "out": "code"})
print(supervisor(state))                    # FINISH
```

输出：

```
Researcher
Coder
FINISH
```

**要点**：Supervisor 输出的是「下一个节点名」，调度循环由外部执行器（executor）负责。LLM 只做决策，不做副作用，这样系统才好测试。

---

## 5. 什么时候该用 Supervisor，什么时候不该用

**该用**：
- 任务可以被清晰拆成串行/并行子阶段（研究 → 编码 → 验证）。
- 每个子阶段有明确专长（不同 Prompt / 不同工具）。
- 需要可观测性（谁做了什么、卡在哪里）。

**不该用**：
- 单轮问答（一问一答）—— 引入 Supervisor 只会让延迟翻倍。
- 子任务之间耦合度极高，每次都要交换大量上下文 —— 共享状态会变成瓶颈。
- 无法定义清晰的终止条件 —— Supervisor 会陷入「再派一个 Agent 试试」的死循环。

**记住一条工程原则**：Supervisor 的价值在 **编排（orchestration）**，不在 **智能**。如果任务本身不需要编排，就不要加它。

---

## 动手练习

**任务**：在本地实现一个「3 节点 Supervisor」系统，要求：

1. 定义三个子 Agent：`Researcher`、`Writer`、`Reviewer`，每个只用 `print` 模拟动作。
2. 定义一个 `supervisor(state)` 函数，规则如下：
   - 如果 `state` 里没有 `final_text`，派 `Researcher`；
   - 如果 `state` 里有 `final_text` 但没有 `review`，派 `Reviewer`；
   - 如果 `state` 里已有 `review` 且值为 `"pass"`，返回 `"FINISH"`；
   - 否则派 `Writer` 重写。
3. 写一个 `run(task)` 主循环，最多 10 轮，打印每轮 Supervisor 的决策和状态变化。
4. **加分项**：如果 10 轮内没 FINISH，抛出异常，并打印当前 `state`。

**验收标准**：
- 打印顺序能清楚看出「谁被派了 → 做了什么 → 状态怎么变」。
- 用同一份 `state` 字典贯穿全程，验证「共享状态」概念。

完成后你就掌握了 Supervisor Pattern 的最小可用形态，之后换成真实 LLM 只需替换 `supervisor` 内部的判断逻辑。

```python
import json
from typing import Literal, TypedDict

class State(TypedDict, total=False):
    task: str
    research: str
    draft: str
    review: str
    history: list[dict]

Node = Literal["Researcher", "Writer", "Reviewer", "FINISH"]

def supervisor(state: State) -> Node:
    """Supervisor 只做路由：读共享状态，返回下一个节点。"""
    if "research" not in state:
        return "Researcher"
    if "draft" not in state:
        return "Writer"
    if "review" not in state:
        return "Reviewer"
    if state["review"] == "pass":
        return "FINISH"
    # 未通过则让 Writer 重写
    state.pop("review", None)
    state.pop("draft", None)
    return "Writer"

def researcher(state: State) -> None:
    state["research"] = f"关于《{state['task']}》的调研要点"
    state["history"].append({"agent": "Researcher", "draft": state["research"]})

def writer(state: State) -> None:
    state["draft"] = f"基于『{state['research']}』撰写的初稿"
    state["history"].append({"agent": "Writer", "draft": state["draft"]})

def reviewer(state: State) -> None:
    # 简单规则：提到 '调研' 就通过，否则打回
    state["review"] = "pass" if "调研" in state["draft"] else "revise"
    state["history"].append({"agent": "Reviewer", "review": state["review"]})

WORKERS = {
    "Researcher": researcher,
    "Writer": writer,
    "Reviewer": reviewer,
}

def run(task: str, max_rounds: int = 10) -> State:
    state: State = {"task": task, "history": []}
    for i in range(max_rounds):
        nxt = supervisor(state)
        print(f"[Round {i + 1}] Supervisor -> {nxt}")
        if nxt == "FINISH":
            print("任务完成。")
            return state
        WORKERS[nxt](state)
    raise RuntimeError(f"超过 {max_rounds} 轮仍未完成，当前状态：{json.dumps(state, ensure_ascii=False)}")

if __name__ == "__main__":
    final_state = run("写一篇关于多 Agent 的短文")
    print("最终状态 keys：", list(final_state.keys()))
```

## agent.multi.hierarchical

# 多智能体分层架构 (Hierarchical Multi-Agent Architecture)

> 一句话直觉：当任务复杂到单个智能体「脑子不够用」时，就找一个「总指挥」智能体去调度一群「专家」智能体——这就是分层多智能体。

本讲是 `agent.multi.hierarchical` 的入门，前置知识为空，所以我们会从「什么是智能体」讲起，逐步搭建一个可以运行的分层多智能体系统。

---

## 一、为什么要学「分层多智能体」？

想象你要完成一个复杂任务：「帮我分析一家公司的财报并给出投资建议」。

- 单个智能体（Agent，即能自主调用工具、思考并行动的 AI 程序）要把「抓数据 → 算指标 → 写分析 → 出建议」全干完，容易出现：**上下文过长、职责混乱、出错难追踪**。
- 换成**分层结构**：一个**管理者智能体（Manager Agent）**只负责「拆解任务、分派、汇总」；下面挂 **研究员智能体（Researcher）**、**分析师智能体（Analyst）**、**撰写智能体（Writer）** 各司其职。

这就是**分层多智能体（Hierarchical Multi-Agent）**：用树状的「管理者—工作者（Manager–Worker）」结构，把复杂任务分解到多个专职智能体上。

**核心思想一句话**：*分工 + 分层调度 = 可扩展的复杂任务处理。*

---

## 二、三个关键概念

### 1. 智能体（Agent）

一个智能体至少包含：

- **角色（Role）**：它是谁，负责什么。
- **工具（Tool）**：它能调用什么函数（搜索、计算、写文件……）。
- **消息（Message）**：它接收输入、输出结果。

```python
# 一个最小智能体：就是「角色 + 一个处理函数」
class SimpleAgent:
    def __init__(self, name, role):
        self.name = name
        self.role = role

    def run(self, task: str) -> str:
        # 真实场景里这里会调用 LLM；此处用字符串模拟
        return f"[{self.name}] 处理任务: {task}"
```

### 2. 分层（Hierarchical）

把智能体组织成**树**：

```
              Manager
             /   |    \
       Worker1 Worker2 Worker3
```

- **Manager** 只关心：*分解任务、选谁干、合并结果*。
- **Worker** 只关心：*执行分配到的子任务*。

好处：每一层职责单一，容易替换、容易加新 Worker。

### 3. 任务分解（Task Decomposition）

分层的关键动作就是**把一个大任务切成若干可并行的子任务**。这一步通常在 Manager 内完成。

```python
def decompose(task: str) -> list[str]:
    # 真实场景由 LLM 生成；这里用规则模拟
    if "财报" in task:
        return ["收集财报数据", "计算关键财务比率", "撰写分析报告"]
    return [task]
```

---

## 三、最小可运行的分层多智能体

我们用一个 Manager + 三个 Worker 组成一个分层系统，跑通「任务分解 → 分派 → 执行 → 汇总」的完整链路。

```python
class Worker(SimpleAgent):
    def run(self, task: str) -> str:
        # 每个 Worker 只管自己的那一段
        return f"[{self.name}/{self.role}] 完成 -> {task}"

class ManagerAgent:
    def __init__(self, workers):
        self.workers = workers          # 下层工作者

    def handle(self, task: str) -> str:
        subtasks = decompose(task)      # 1. 分解
        results = []
        for i, sub in enumerate(subtasks):
            worker = self.workers[i % len(self.workers)]  # 2. 分派
            results.append(worker.run(sub))
        return "\n".join(results)       # 3. 汇总
```

这就是**分层多智能体的最小骨架**——它和工业界 LangGraph / CrewAI 里的 Hierarchical 模式思想完全一致，只是把「规则分解」换成「LLM 分解」、把「print」换成「真实工具调用」。

---

## 四、分层 vs 扁平：什么时候该用分层？

| 场景 | 推荐结构 |
|---|---|
| 任务简单、步骤少 | 单智能体（Single Agent） |
| 任务可拆成并列子任务 | 扁平多智能体（Flat Multi-Agent） |
| 子任务本身还需要再拆 / 需要统一裁决 | **分层多智能体（Hierarchical）** |

分层的两个典型收益：

1. **上下文隔离**：Manager 不用看每个 Worker 的全部推理过程，只接收精炼后的结果。
2. **可扩展**：新增一个 Worker，只需在 Manager 的分派表里注册，其它层不用动。

---

## 五、工程级要点（写进生产代码前务必记住）

1. **Manager 是单点瓶颈**：它挂了整套系统就挂了，需要超时与降级。
2. **避免无限递归**：Worker 如果想「再往下叫一个 Agent」，要给整棵调用树设**最大深度（max_depth）**。
3. **结果合并（Result Aggregation）要显式**：Manager 必须定义清晰的合并策略（拼接？投票？再喂给 LLM 总结？），否则容易丢信息。
4. **可观测性（Observability）**：每个 Agent 的输入输出都要打日志，否则分层一深就成大黑盒。

```python
# 加入 max_depth 防递归爆炸
def run_hierarchical(manager, task, depth=0, max_depth=3):
    if depth >= max_depth:
        raise RuntimeError("超过最大层级，停止递归")
    return manager.handle(task)
```

```python
"""分层多智能体最小可运行示例。"""

# ---------- 1. 基础智能体 ----------
class SimpleAgent:
    def __init__(self, name: str, role: str):
        self.name = name
        self.role = role

    def run(self, task: str) -> str:
        return f"[{self.name}] 处理任务: {task}"


# ---------- 2. 工作者：只执行分配到的子任务 ----------
class Worker(SimpleAgent):
    def run(self, task: str) -> str:
        return f"[{self.name}/{self.role}] 完成 -> {task}"


# ---------- 3. 任务分解（真实场景由 LLM 生成） ----------
def decompose(task: str) -> list[str]:
    if "财报" in task:
        return ["收集财报数据", "计算关键财务比率", "撰写分析报告"]
    return [task]


# ---------- 4. 管理者：分解 + 分派 + 汇总 ----------
class ManagerAgent:
    def __init__(self, workers: list[Worker]):
        self.workers = workers

    def handle(self, task: str) -> str:
        subtasks = decompose(task)              # 1. 分解
        results = []
        for i, sub in enumerate(subtasks):
            worker = self.workers[i % len(self.workers)]  # 2. 分派
            results.append(worker.run(sub))
        return "\n".join(results)               # 3. 汇总


# ---------- 5. 顶层入口：带最大深度保护 ----------
def run_hierarchical(manager: ManagerAgent, task: str,
                     depth: int = 0, max_depth: int = 3) -> str:
    if depth >= max_depth:
        raise RuntimeError("超过最大层级，停止递归")
    return manager.handle(task)


# ---------- 6. 组装并运行 ----------
if __name__ == "__main__":
    w1 = Worker("Researcher", "收集数据")
    w2 = Worker("Analyst", "分析数据")
    w3 = Worker("Writer", "撰写报告")

    manager = ManagerAgent([w1, w2, w3])
    output = run_hierarchical(manager, "帮我分析这家公司的财报并给出投资建议")
    print(output)
```


---

## 本课题目

### single_choice · None



- [A] 直接执行所有子任务，不分配给其他智能体
- [B] 协调、调度多个子智能体，并根据任务结果决定下一步行动
- [C] 仅负责记录日志，不参与任务决策
- [D] 替代所有子智能体，独立完成整个任务

**参考答案**：1

**解析**：Supervisor 模式的核心是充当协调者/调度者，负责任务分解、分配给合适的子智能体，并根据返回结果决定后续步骤（继续、结束或重新分配）。它不直接包揽所有执行工作，也不仅仅是日志记录者。

### single_choice · None



- [A] Supervisor 必须知道每个子智能体的内部实现细节才能调度
- [B] 子智能体之间必须直接互相通信，supervisor 不参与
- [C] Supervisor 根据任务需求选择子智能体，子智能体只负责处理被分配的子任务
- [D] Supervisor 只能调度一个子智能体，不能有多个

**参考答案**：2

**解析**：Supervisor 通过抽象接口调度子智能体，不需要了解其内部实现；子智能体专注于被分配的子任务。子智能体之间通常不直接通信，而是通过 supervisor 协调。Supervisor 可以管理多个子智能体。

### single_choice · None



- [A] 子智能体在运行时随机出现，supervisor 无法预知
- [B] Supervisor 维护一个子智能体列表或注册表，并根据任务需求从中选择
- [C] Supervisor 必须遍历整个文件系统查找子智能体
- [D] 子智能体通过蓝牙自动连接 supervisor

**参考答案**：1

**解析**：在实际实现中，supervisor 通常维护一个已知子智能体的列表或注册表，包含每个子智能体的名称、能力描述等信息，从而根据任务需求选择合适的子智能体。子智能体不会随机出现，也不需要遍历文件系统或蓝牙连接。

### single_choice · None



- [A] 消息只能从 supervisor 传给子智能体，不能反向传递
- [B] 消息可以在 supervisor 和子智能体之间双向传递，用于任务分配和结果返回
- [C] 消息传递必须使用 HTTP 协议，不能用其他方式
- [D] 消息传递只能传递纯文本，不能传递结构化数据

**参考答案**：1

**解析**：在 supervisor 模式中，消息传递通常是双向的：supervisor 向子智能体发送任务指令，子智能体向 supervisor 返回结果或状态。消息传递的实现方式多样，不限于 HTTP，也可以传递结构化数据。

### single_choice · None



- [A] 将所有子智能体的逻辑都写在 supervisor 内部
- [B] 为每个子智能体定义清晰的职责边界和输入输出接口
- [C] 让所有子智能体共享同一个全局变量，随意修改
- [D] 避免为子智能体编写任何文档

**参考答案**：1

**解析**：为每个子智能体定义清晰的职责边界和输入输出接口，有助于降低耦合、提高可维护性和可测试性。把所有逻辑塞进 supervisor、共享全局变量随意修改、不写文档都会降低可维护性。

### single_choice · None



- [A] 禁止人类参与任何决策
- [B] 在 supervisor 决定下一步之前，允许人类审查或修改决策
- [C] 让人类直接替代所有子智能体
- [D] 人类只能作为子智能体之一，不能审查 supervisor

**参考答案**：1

**解析**：在 supervisor 模式中，人工介入通常通过在 supervisor 决策点之前或之后插入人工审查/确认环节来实现，人类可以批准、修改或拒绝 supervisor 的下一步决定。人类不一定替代子智能体，也可以参与审查。

### single_choice · None



- [A] Supervisor 的决策是完全随机的，没有依据
- [B] Supervisor 根据当前状态、任务目标和子智能体能力，选择最优的下一步行动
- [C] Supervisor 的决策只依赖于第一次输入，后续不再改变
- [D] Supervisor 的决策必须由外部程序硬编码，不能动态调整

**参考答案**：1

**解析**：Supervisor 的决策本质上是基于当前状态、任务目标和可用子智能体能力，动态选择下一步行动（调用哪个子智能体或结束）。它不是随机的，也不局限于第一次输入，通常可以动态调整。

### single_choice · None



- [A] 让 A 直接修改 B 的内部变量
- [B] 通过 supervisor 或共享状态来传递中间结果
- [C] 让 A 和 B 通过全局变量直接通信，绕过 supervisor
- [D] 禁止 A 和 B 共享任何信息

**参考答案**：1

**解析**：在 supervisor 模式中，推荐通过 supervisor 或共享状态来传递中间结果，这样保持协调中心化、便于追踪和调试。直接修改其他智能体内部变量或绕过 supervisor 使用全局变量会破坏封装和可维护性。

### single_choice · None



- [A] 终止条件只能由子智能体决定，supervisor 无权决定
- [B] 终止条件可以由 supervisor 根据任务完成情况、步数上限或外部信号来决定
- [C] 终止条件必须硬编码在操作系统层面
- [D] Supervisor 模式不需要终止条件，可以无限运行

**参考答案**：1

**解析**：终止条件通常由 supervisor 根据任务是否完成、是否达到最大步数、是否收到外部停止信号等来决定。子智能体也可以报告完成，但最终决定权通常在 supervisor。无限运行不是合理设计。

### single_choice · None



- [A] 通过查表法，预先列出所有可能的决策
- [B] 通过生成结构化的输出（如函数调用或路由指令）来表达下一步决策
- [C] 通过随机数生成器选择
- [D] 通过读取子智能体的源代码

**参考答案**：1

**解析**：基于大语言模型的 supervisor 通常通过生成结构化输出（如工具调用、JSON 路由指令等）来表达下一步决策，而不是查表、随机选择或读取源代码。

### single_choice · None



- [A] Supervisor 根据任务需求动态选择合适的子智能体
- [B] Supervisor 在每一步都调用所有子智能体，然后从中挑选结果
- [C] Supervisor 设置合理的终止条件
- [D] Supervisor 维护清晰的子智能体注册表

**参考答案**：1

**解析**：如果 supervisor 在每一步都调用所有子智能体再挑选结果，会造成大量不必要的计算和资源浪费，导致效率低下。动态选择、合理终止条件和清晰注册表都是提高效率的做法。

### single_choice · None



- [A] 仅基于子智能体的名称长度
- [B] 基于当前状态、任务目标、子智能体能力描述以及历史交互信息
- [C] 仅基于随机数
- [D] 仅基于系统的当前时间

**参考答案**：1

**解析**：路由决策通常综合考虑当前状态、任务目标、子智能体的能力描述以及历史交互信息，选择最合适的下一步。仅基于名称长度、随机数或时间都不是合理的路由依据。

### single_choice · None



- [A] 决定网络数据包走哪条物理线路
- [B] 根据当前状态和任务需求，决定下一个被调用的智能体是谁
- [C] 对子智能体的输出进行加密
- [D] 自动生成子智能体的源代码

**参考答案**：1

**解析**：在 supervisor 模式中，路由机制负责根据当前对话状态、任务进展或 supervisor 的决策，选择下一个要调用的智能体（或结束流程）。它与网络路由无关，也不涉及加密或代码生成。

### single_choice · None



- [A] 单个简单的数学计算任务
- [B] 需要多个专业领域智能体协作完成的复杂任务，且需要统一协调
- [C] 仅需要调用一次外部 API 的场景
- [D] 纯静态文本格式化任务

**参考答案**：1

**解析**：Supervisor 模式适用于需要多个专业智能体协作、且需要统一协调调度的复杂任务。简单计算、单次 API 调用和纯静态格式化通常不需要多智能体协调，用单一函数或智能体即可。

### single_choice · None



- [A] 子智能体直接结束整个流程
- [B] 子智能体将结果返回给 supervisor，由 supervisor 决定下一步
- [C] 子智能体自动变成新的 supervisor
- [D] 子智能体直接调用其他所有子智能体

**参考答案**：1

**解析**：子智能体完成被分配的任务后，通常将结果返回给 supervisor，由 supervisor 根据结果决定是继续分配、结束流程还是调整策略。子智能体不会自动结束整个流程或变成 supervisor。

### single_choice · None



- [A] 状态只保存在 supervisor 中，子智能体无法访问
- [B] 状态用于在 supervisor 和子智能体之间传递上下文和中间结果
- [C] 状态一旦创建就不能修改
- [D] 状态只能存储字符串，不能存储列表或字典

**参考答案**：1

**解析**：在多智能体系统中，状态通常用于在 supervisor 和子智能体之间共享上下文、消息历史和中间结果。状态可以被读写和更新，也可以包含多种数据类型。子智能体通常可以访问状态中与其任务相关的部分。

### single_choice · None



- [A] 让 supervisor 永远不结束，保持运行
- [B] 设置最大迭代次数或明确的终止条件
- [C] 禁止子智能体返回任何结果
- [D] 让所有子智能体都返回相同的内容

**参考答案**：1

**解析**：设置最大迭代次数或明确的终止条件（如任务完成、达到步数上限）是避免 supervisor 无限循环的常见做法。永远运行、禁止返回结果或返回相同内容都不是合理的解决方案。

### single_choice · None



- [A] Supervisor 模式中智能体按固定顺序执行，流水线模式是动态的
- [B] Supervisor 模式由一个中心协调者动态决定调用哪个智能体，流水线模式按预定义顺序执行
- [C] 两者完全相同，只是名称不同
- [D] 流水线模式必须使用 supervisor，supervisor 模式不需要流水线

**参考答案**：1

**解析**：Supervisor 模式的特点是有一个中心协调者（supervisor）动态决定下一步调用哪个智能体；流水线模式则按预先定义好的固定顺序依次执行各步骤。两者在控制流和灵活性上有明显区别。

### single_choice · None



- [A] 忽略该子智能体的失败，直接进入下一步
- [B] Supervisor 根据失败信息决定重新分配、更换子智能体或终止流程
- [C] 让该子智能体无限重试直到成功
- [D] 自动删除该子智能体并重新启动整个系统

**参考答案**：1

**解析**：当子智能体失败时，supervisor 应根据返回的错误信息或状态，决定是重新分配任务、换一个子智能体、调整策略还是终止流程。忽略失败、无限重试或重启整个系统都不是合理的默认处理方式。

### single_choice · None



- [A] 任务需要多个专业领域知识协作
- [B] 任务需要动态决定调用顺序
- [C] 任务非常简单，单个函数或单个智能体即可完成
- [D] 任务需要多个智能体并行处理不同子任务

**参考答案**：2

**解析**：如果任务非常简单，单个函数或单个智能体就能完成，引入 supervisor 多智能体模式会增加不必要的复杂度和开销，属于过度设计。其他选项都是 supervisor 模式的合理应用场景。

### single_choice · None



- [A] 直接执行所有底层工具调用
- [B] 负责将任务分解并分派给下层子 Agent，同时汇总结果
- [C] 只负责记录日志，不参与决策
- [D] 替代所有子 Agent 完成推理

**参考答案**：1

**解析**：分层多智能体结构中，顶层 Agent 通常承担任务分解、协调分派和结果汇总的职责，而非直接执行所有底层操作。

### single_choice · None



- [A] 所有 Agent 之间必须两两通信，效率最高
- [B] 通过层级划分降低协调复杂度，便于管理大规模 Agent 协作
- [C] 完全不需要任何通信机制
- [D] 每个 Agent 都必须具备完全相同的技能

**参考答案**：1

**解析**：分层结构通过将协调职责分层，减少了扁平结构中任意两两通信带来的复杂度，适合大规模协作。

### single_choice · None



- [A] 所有 Agent 同时独立运行且互不干涉
- [B] 高层决定总体目标，低层按分派执行并向高层反馈
- [C] 只有底层 Agent 具有决策能力
- [D] 控制流与 Agent 层级完全无关

**参考答案**：1

**解析**：分层控制流体现为高层定目标、低层执行反馈，形成自上而下与自下而上的结合。

### multi_choice · None



- [A] 它通过层级组织来降低协调复杂度
- [B] 顶层 Agent 常负责任务分解与结果汇总
- [C] 它要求所有 Agent 必须两两直接通信
- [D] 它可以支持大规模 Agent 的协作
- [E] 它天然消除了所有通信开销

**参考答案**：[0, 1, 3]

**解析**：分层架构降低协调复杂度、支持大规模协作，顶层常负责分解与汇总；但不需要两两全连接，也不会消除通信开销。

### multi_choice · None



- [A] 如何划分层级与职责
- [B] 如何在层间传递消息与控制流
- [C] 如何避免所有 Agent 共享同一份状态导致冲突
- [D] 如何让所有 Agent 使用完全相同的实现代码
- [E] 如何设计异常上报与重试机制

**参考答案**：[0, 1, 4]

**解析**：层级划分、层间通信与控制流、异常上报与重试是设计要点；共享状态是否需要隔离因系统而异，而强制相同实现代码并非必要。

### multi_choice · None



- [A] 任务在层间反复往返，始终无法下沉到执行的 Agent
- [B] 上层把任务委派后就完全失去跟踪，导致无法汇总
- [C] 系统按任务抽象层次清晰划分了职责
- [D] 大量子任务被无限循环重试且无上报机制
- [E] 每层都有明确的职责边界

**参考答案**：[0, 1, 3]

**解析**：任务反复往返、委派后无跟踪、无限重试无上报，都是设计缺陷的信号；清晰分层和明确职责是良好设计，不是问题。

### multi_choice · None



- [A] 当子任务超出当前层能力时可向上层上报
- [B] 上报有助于避免任务被静默丢弃
- [C] 上报机制应配合超时或重试策略
- [D] 上报意味着所有任务都必须返回到顶层处理
- [E] 上报后上层可决定转交、补充信息或降级处理

**参考答案**：[0, 1, 2, 4]

**解析**：上报用于处理超能力或异常情况，避免静默丢弃，并常配合超时重试；但不需要所有任务都回到顶层。

### fill_blank · None



**参考答案**：["委派", "delegation", "任务委派"]

**解析**：上层把子任务交给下层处理的过程一般称为委派（delegation）。

### fill_blank · None



**参考答案**：["抽象", "抽象层次", "抽象程度", "abstraction"]

**解析**：分层通常按任务抽象程度组织，上层偏高层目标，下层偏具体执行。

### code_reading · None



**参考答案**：输出为 ['a executed x', 'b executed y']，体现了顶层 Agent 将任务分解为子任务并分派给下层 Agent 执行的分层委派行为。

**解析**：顶层把 'x+y' 拆成 x 和 y 分派给两个下属，下属分别执行，体现了任务分解与分层委派。

### code_reading · None



**参考答案**：缺陷在于：当下属无法处理任务时无条件地向上层上交，若上层也把任务交回或没有终止条件，任务可能在层间无限往返而无法被真正执行或丢弃，缺少有效的终止、兜底或上报终止机制。

**解析**：该伪代码在所有情况下都向上层转移，缺少终止条件和真正的执行逻辑，可能造成层间无限循环。

### scenario · None



**解析**：报告撰写任务可自然分解为检索、撰写、校对等子任务，分层结构便于顶层分解与分派、下层执行，顶层再协调与汇总，从而降低协调复杂度。

### single_choice · None



- [A] 只有一个简单任务需要单个 Agent 完成
- [B] 任务可以自然分解为多个子任务，且子任务之间需要协调配合
- [C] 任务完全不需要任何推理
- [D] 只要求输出一段固定的静态文本

**参考答案**：1

**解析**：当任务具有可分解性且子任务之间存在协调需求时，分层架构能有效组织协作。

### scenario · None



**解析**：应引入超时机制、失败上报、有限重试与监控告警，并在必要时提供兜底处理，避免子任务静默卡住导致整体无法汇总。

### single_choice · None



- [A] 直接丢弃该子任务并结束
- [B] 将其上报给上层，或转交给同层其他更合适的 Agent
- [C] 伪造一个结果返回
- [D] 无限循环重试直到超时

**参考答案**：1

**解析**：分层结构的意义之一就是支持上报与转交机制，使任务能得到恰当处理，而不是丢弃或伪造结果。

### single_choice · None



- [A] 所有 Agent 必须与所有其他 Agent 直接通信
- [B] 通信通常沿层级进行，但也可允许受控的跨层通信
- [C] 通信只能在最底层 Agent 之间发生
- [D] 分层结构中不允许任何消息传递

**参考答案**：1

**解析**：分层结构通常以层级通信为主，但实际系统常允许受控的跨层或横向通信以提高灵活性。

### single_choice · None



- [A] 按照字母顺序排列 Agent 名称
- [B] 按照任务抽象程度或职责范围，上层处理高层目标，下层处理具体执行
- [C] 按照 Agent 创建时间的先后
- [D] 按照随机方式分配

**参考答案**：1

**解析**：分层通常按任务抽象层次或职责范围划分，上层聚焦高层目标与协调，下层聚焦具体执行。

### single_choice · None



- [A] 委派意味着上层完全放弃对任务的跟踪
- [B] 委派是上层将子任务交给下层处理，但仍可能保留协调与汇总职责
- [C] 委派后上层不再需要接收任何反馈
- [D] 委派只能发生在同一层内部

**参考答案**：1

**解析**：委派是向下分配任务，但上层通常仍需协调、跟踪进度并汇总结果。

### single_choice · None



- [A] 完全无法扩展
- [B] 层级增多可能引入额外通信延迟和协调开销
- [C] 无法处理任何复杂任务
- [D] 所有 Agent 必须使用同一编程语言

**参考答案**：1

**解析**：层级越多，消息在层间传递的路径可能越长，从而带来延迟和协调开销，是该架构的权衡之一。

### single_choice · None



- [A] 立即把所有细节一次性交给最底层
- [B] 先解析和分解任务，形成子任务计划，再按计划分派
- [C] 跳过分解直接返回用户请求原文
- [D] 只把请求保存到日志

**参考答案**：1

**解析**：规范流程通常是先解析分解任务并形成计划，再分派给下层，而非盲目下放或跳过处理。

### single_choice · None



- [A] 只需返回最底层第一个完成的结果即可
- [B] 通常由上层收集并整合下层各子任务的结果，形成统一输出
- [C] 汇总必须由最底层 Agent 完成
- [D] 无需汇总，直接丢弃下层结果

**参考答案**：1

**解析**：结果汇总一般由上层负责，将各子任务产出整合为一致的最终输出。
