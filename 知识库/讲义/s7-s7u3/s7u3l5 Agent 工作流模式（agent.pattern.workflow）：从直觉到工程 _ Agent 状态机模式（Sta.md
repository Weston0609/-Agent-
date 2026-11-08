# s7u3l5 Agent 工作流模式（agent.pattern.workflow）：从直觉到工程 / Agent 状态机模式（State Machine）：让 AI 智能体拥有"记忆"与"流程"

> 来源 `content/lessons/s7u3l5.json`

## agent.pattern.workflow

# Agent 工作流模式（agent.pattern.workflow）：从直觉到工程

## 0. 一句话直觉

**Agent 工作流模式，就是把“让大模型做一件大事”拆成“按固定顺序调用模型完成若干小步骤”，用工程化的流程替代一次性的巨长提示词。**

你不需要一开始就让 LLM（Large Language Model，大语言模型）一口气写完文章、做研究、写代码。相反，你会把它当作一个**可调用的函数**：先让它列提纲，再让它逐段写，再让它自检，最后让它润色。这就是最朴素的 workflow（工作流）。

---

## 1. 为什么需要工作流：单个 LLM 调用的三个工程问题

单个 LLM 调用看起来很简单：`llm(prompt) -> text`。但把它放进真实系统时，会遇到三个问题：

1. **质量不可控**：让它一次输出 3000 字，细节容易跑偏、自相矛盾。
2. **无状态**：每次调用都不记得上一次，无法自然延续。
3. **难测试与调试**：一个巨大的 prompt 出错时，你不知道是哪一段坏了。

工作流模式的核心思想是：**把复杂任务分解为多个小的、可观测的 LLM 调用（或工具调用），按固定顺序/条件连线执行**。它比你想象的更基础，甚至不需要 Agent 框架，几十行 Python 就能实现。

```python
# 最原始的工作流：函数组合
# 每个步骤是一个独立的 LLM 调用，输入输出都是字符串

def llm(prompt: str) -> str:
    """模拟一个 LLM 调用。真实工程里这里会调用 OpenAI/本地模型 API。"""
    return f"[LLM 回答] {prompt[:30]}..."


def step_outline(topic: str) -> str:
    """工作流第 1 步：根据主题生成提纲。"""
    return llm(f"请为主题《{topic}》列出 3 条提纲。")


def step_draft(outline: str) -> str:
    """工作流第 2 步：根据提纲写初稿。"""
    return llm(f"根据以下提纲写一段 100 字初稿：{outline}")


def step_polish(draft: str) -> str:
    """工作流第 3 步：润色初稿。"""
    return llm(f"请润色以下文字：{draft}")


def article_workflow(topic: str) -> str:
    """把上面 3 步串成一条工作流。"""
    outline = step_outline(topic)
    draft = step_draft(outline)
    final = step_polish(draft)
    return final


print(article_workflow("AI 入门"))
```

**关键结论**：工作流的本质是**函数组合**。每个步骤职责单一，出错可定位，容易替换模型和 prompt。

---

## 2. 工作流的最小数据结构：步骤、状态、执行器

当我们不止有 3 步、还想加分支和日志时，把函数硬编码成长串 `a(b(c(d)))` 会很难维护。更工程化的做法是引入三个概念：

- **步骤（Step）**：一个带名字的、可调用的函数，输入输出是工作流状态。
- **状态（State）**：在步骤之间传递的数据，通常是一个字典。
- **执行器（Runner）**：按顺序遍历步骤，把状态一路传下去。

```python
from typing import Callable

# 一个工作流状态就是一个普通字典：所有步骤共享、读写
State = dict[str, str]
Step = Callable[[State], State]


def make_step(name: str, func: Callable[[str], str], key_in: str, key_out: str) -> Step:
    """把一个函数包装成一个可注册的工作流步骤。"""
    def step(state: State) -> State:
        state = dict(state)  # 避免改动外部状态，模拟不可变式传递
        state[key_out] = func(state[key_in])
        print(f"[step:{name}] {key_in} -> {key_out}")
        return state
    return step


def llm(prompt: str) -> str:
    return f"[LLM] {prompt[:20]}..."


workflow: list[Step] = [
    make_step("outline", lambda t: llm(f"列提纲：{t}"), "topic", "outline"),
    make_step("draft",   lambda o: llm(f"写初稿：{o}"), "outline", "draft"),
    make_step("polish",  lambda d: llm(f"润色：{d}"),   "draft",   "final"),
]


def run(workflow: list[Step], init_state: State) -> State:
    """线性执行器：按顺序执行步骤，前一步的输出就是后一步的输入状态。"""
    state = init_state
    for step in workflow:
        state = step(state)
    return state


result = run(workflow, {"topic": "AI 入门"})
print("最终输出：", result["final"])
```

**关键结论**：把步骤抽象成 `State -> State` 的函数，工作流就变成了**列表**。你可以对列表做插入、替换、条件跳过、日志记录——这就是工作流引擎的雏形。

---

## 3. 从线性到条件：加入分支与循环

真实任务很少是纯线性的。典型的两类扩展：

- **条件分支（Conditional Branch）**：根据上一步的结果决定走哪条路。
- **循环（Loop / Reflection）**：让模型自检，不满意就重来，最多重试 N 次。

```python
from typing import Callable

State = dict


def llm(prompt: str) -> str:
    return f"[LLM] {prompt[:20]}..."


def draft_step(state: State) -> State:
    state["draft"] = llm(f"写初稿：{state['topic']}")
    return state


def review_step(state: State) -> State:
    """模拟“评审”步骤：让模型判断草稿是否合格。"""
    # 真实场景这里会调用 LLM 返回 yes/no，这里用简单规则演示
    state["passed"] = len(state["draft"]) > 15
    return state


def polish_step(state: State) -> State:
    state["draft"] = llm(f"润色：{state['draft']}")
    state["round"] = state.get("round", 0) + 1
    return state


def run_with_loop(init_state: State, max_rounds: int = 3) -> State:
    """循环式工作流：草稿 -> 评审 -> 若不过则润色，最多 max_rounds 轮。"""
    state = init_state
    for _ in range(max_rounds):
        state = draft_step(state)
        state = review_step(state)
        if state["passed"]:
            print("评审通过")
            break
        print("评审未通过，进入润色")
        state = polish_step(state)
    return state


print(run_with_loop({"topic": "AI 入门"})["draft"])
```

**关键结论**：加入分支和循环后，工作流从“管道”升级为“流程图”。这就是 Agent 框架（如 LangGraph、CrewAI）要解决的核心问题——把流程图表达出来并可靠执行。

---

## 4. 工程化关注点：可观测、可替换、可测试

工作流模式真正进入生产后，还需要三个工程属性：

1. **可观测（Observability）**：每一步的输入、输出、耗时、模型名都要记录，出问题能回溯。
2. **可替换（Replaceability）**：把 LLM 封装成接口，换模型不改工作流。
3. **可测试（Testability）**：用假的 LLM（返回固定字符串）来单测每个步骤。

```python
import time
from typing import Callable, Protocol


class LLM(Protocol):
    """LLM 接口：真实实现可以是 OpenAI、本地模型或测试用的假模型。"""
    def __call__(self, prompt: str) -> str: ...


def real_llm(prompt: str) -> str:
    # 真实场景：调用 API，这里只演示接口
    return f"[real] {prompt[:20]}"


def fake_llm(prompt: str) -> str:
    """测试用：永远返回固定长度，方便断言。"""
    return "固定回答" * 5


def traced_step(name: str, llm: LLM, prompt_fn: Callable[[dict], str], key_out: str):
    """带日志的工作流步骤工厂：记录耗时和输出长度。"""
    def step(state: dict) -> dict:
        prompt = prompt_fn(state)
        t0 = time.time()
        out = llm(prompt)
        cost = time.time() - t0
        state[key_out] = out
        print(f"[trace] {name}: {cost*1000:.1f}ms, out_len={len(out)}")
        return state
    return step


def run(workflow, state):
    for step in workflow:
        state = step(state)
    return state


# 生产：用 real_llm
prod = [traced_step("outline", real_llm, lambda s: f"列提纲：{s['topic']}", "outline")]
print(run(prod, {"topic": "AI"})["outline"])

# 测试：换成 fake_llm，完全不改工作流结构
prod = [traced_step("outline", fake_llm, lambda s: f"列提纲：{s['topic']}", "outline")]
assert run(prod, {"topic": "AI"})["outline"] == "固定回答" * 5
print("测试通过")
```

**关键结论**：工作流的价值不仅是“拆步骤”，更是把 LLM 不可控的部分隔离在接口后面，让**流程本身变得可测试、可观测、可演进**。

---

## 5. 什么时候用工作流，什么时候用自主 Agent

这是初学者最容易混淆的地方。

| 维度 | 工作流（Workflow） | 自主 Agent（Autonomous Agent） |
|------|---------------------|--------------------------------|
| 控制流 | 由你预先设计好 | 由 LLM 动态决定 |
| 可预测性 | 高 | 低 |
| 调试难度 | 低 | 高 |
| 适合任务 | 流程稳定、步骤可枚举 | 探索性、路径不固定 |
| 成本 | 较低（步骤数固定） | 较高（可能循环多次） |

实践建议：**先写成工作流，只有当工作流的分支实在写不穷举时，再让 Agent 来做决策。** 这叫“workflow first, agent later”。

---

## 6. 动手练习

**任务**：实现一个“读书笔记工作流”。

要求：

1. 定义三个步骤函数：`summarize`（总结原文）、`extract_points`（提取 3 个要点）、`make_questions`（生成 3 个思考题）。
2. 每个步骤内部调用一个 `fake_llm(prompt) -> str`，不用真的接 API，可以用字符串拼接模拟。
3. 写一个 `run_workflow(steps, state)` 执行器，按顺序调用并打印每一步的状态字典。
4. 再实现一个“自检润色”循环：如果总结结果长度小于 20 字符，就重试一次 `summarize`，最多重试 2 次。

**验收标准**：

- 输入 `{"text": "任意一段文字"}`，输出包含 `summary`、`points`、`questions` 三个字段。
- 打印出每一步的 trace 日志。
- 用 `assert` 验证最终字典里三个字段都存在且非空。

提示：可以参考第 2、3 节的代码，把 `Step` 类型统一成 `Callable[[dict], dict]`。

```python
from typing import Callable

State = dict
Step = Callable[[State], State]


def fake_llm(prompt: str) -> str:
    """模拟 LLM：返回带前缀的字符串，方便观察工作流。"""
    return f"[LLM] {prompt[:25]}..."


# ---- 三个步骤 ----
def summarize(state: State) -> State:
    state["summary"] = fake_llm(f"总结原文：{state['text']}")
    print(f"[trace] summarize -> {state['summary']}")
    return state


def extract_points(state: State) -> State:
    state["points"] = fake_llm(f"提取 3 个要点：{state['summary']}")
    print(f"[trace] extract_points -> {state['points']}")
    return state


def make_questions(state: State) -> State:
    state["questions"] = fake_llm(f"生成 3 个思考题：{state['points']}")
    print(f"[trace] make_questions -> {state['questions']}")
    return state


# ---- 执行器 ----
def run_workflow(steps: list[Step], state: State) -> State:
    for step in steps:
        state = step(state)
    return state


# ---- 自检循环：summary 太短就重试 ----
def run_with_self_check(steps: list[Step], state: State, max_retry: int = 2) -> State:
    state = run_workflow(steps[:1], state)  # 先跑 summarize
    retry = 0
    while len(state.get("summary", "")) < 20 and retry < max_retry:
        print(f"[trace] summary 太短，第 {retry+1} 次重试")
        state = summarize(state)
        retry += 1
    state = run_workflow(steps[1:], state)  # 再跑后面两步
    return state


if __name__ == "__main__":
    steps: list[Step] = [summarize, extract_points, make_questions]
    result = run_with_self_check(steps, {"text": "这是一段关于 AI 工作流的示例文字。"})
    assert result.get("summary") and result.get("points") and result.get("questions")
    print("最终状态：", result)
```

## agent.pattern.state_machine

# Agent 状态机模式（State Machine）：让 AI 智能体拥有"记忆"与"流程"

> **一句话直觉**：如果把 Agent（智能体）比作一个正在办事的客服，状态机（State Machine）就是他的"工牌 + 流程手册"——工牌记录他**现在处于哪一步**，手册规定他**下一步该做什么**。没有状态机，Agent 就像失忆的员工，每次对话都从头问一遍。

---

## 一、为什么需要状态机？

### 1.1 从"一问一答"到"多轮任务"

你肯定用过 ChatGPT 这类对话 AI。如果只是聊天，一问一答就够了。但如果你要做一个能**订机票**的 Agent，流程是这样的：

```
用户：我想订机票
Agent：请问去哪？
用户：北京
Agent：请问什么时候出发？
用户：下周一
Agent：确认订单？
用户：确认
Agent：✅ 已为您预订
```

这里 Agent 必须**记住**"我还在问日期"、"用户已经告诉我目的地了"。这个"记住当前进展"的东西，就叫**状态（State）**。

### 1.2 朴素写法的痛点

零基础同学第一反应通常是用一个变量标记进度：

```python
step = "ask_destination"  # 全局变量
```

但这样写很快会遇到问题：
- 状态一多，代码里全是 `if step == ...: elif step == ...`
- 增加一个状态就要改所有分支
- 谁允许切换到谁？完全靠脑子记，容易出 bug

**状态机模式（State Machine Pattern，状态机模式）** 就是把"有哪些状态、每个状态能去哪"这件事，用**结构化**的方式写清楚。

---

## 二、状态机的三个核心概念

状态机其实很简单，只需记住三个词：

| 概念 | 英文 | 含义 | 例子 |
|---|---|---|---|
| 状态 | State | 当前所处的"阶段" | `ASK_DESTINATION`（正在问目的地） |
| 事件 | Event | 触发变化的外部输入 | 用户说了"北京" |
| 转移 | Transition | 从状态 A 到状态 B 的规则 | ASK_DESTINATION + 收到目的地 → ASK_DATE |

**画成图就是这样**：

```
[START] ──用户说"订机票"──▶ [ASK_DESTINATION]
                                    │
                              用户说"北京"
                                    ▼
                              [ASK_DATE]
                                    │
                              用户说"下周一"
                                    ▼
                              [CONFIRM]
                                    │
                              用户说"确认"
                                    ▼
                                 [DONE]
```

每一个箭头就是一条**转移规则（Transition Rule）**。

---

## 三、最小可用实现：用字典定义状态机

Python 里最朴素的状态机可以用**字典（dict）** 实现：键是 `(当前状态, 事件)`，值是 `下一个状态`。

```python
# 状态机的"转移表"（Transition Table）：告诉系统遇到什么事件该去哪
TRANSITIONS = {
    ("START",            "want_book"):  "ASK_DESTINATION",
    ("ASK_DESTINATION",  "give_dest"):  "ASK_DATE",
    ("ASK_DATE",         "give_date"):  "CONFIRM",
    ("CONFIRM",          "yes"):        "DONE",
}

class FlightAgent:
    def __init__(self):
        self.state = "START"      # 当前状态
        self.data = {}            # 累积的信息（记忆）

    def handle(self, event: str, payload: str = "") -> str:
        """接收一个事件，按转移表切到下一个状态，并返回给用户的回复。"""
        key = (self.state, event)
        if key not in TRANSITIONS:
            return f"（当前状态 {self.state} 无法处理事件 {event}）"

        self.state = TRANSITIONS[key]           # 状态转移
        self.data[event] = payload              # 顺手记住信息

        # 每个状态对应的"台词"
        replies = {
            "ASK_DESTINATION": "请问您要去哪里？",
            "ASK_DATE":        f"好的，去{self.data.get('give_dest','?')}。请问什么时候出发？",
            "CONFIRM":         f"确认预订：{self.data.get('give_dest')}，{self.data.get('give_date')}？（是/否）",
            "DONE":            "✅ 已为您预订成功！",
        }
        return replies[self.state]

# --- 试跑一遍 ---
agent = FlightAgent()
print(agent.handle("want_book"))
print(agent.handle("give_dest", "北京"))
print(agent.handle("give_date", "下周一"))
print(agent.handle("yes"))
```

**输出**：
```
请问您要去哪里？
好的，去北京。请问什么时候出发？
确认预订：北京，下周一？（是/否）
✅ 已为您预订成功！
```

**这段代码的三个关键点**：
1. `self.state` 存**当前状态**——这就是 Agent 的"工牌"。
2. `TRANSITIONS` 是**配置**，加新流程只改表，不改逻辑。
3. `self.data` 存**累积信息**——这就是 Agent 的"记忆"。

---

## 四、进阶：用枚举（Enum）让状态更安全

用字符串当状态容易写错（比如 `"START"` 顺手打成 `"STRAT"`，运行时才报错）。工程上更推荐用 **枚举（Enum，枚举类型）**：

```python
from enum import Enum, auto

class State(Enum):
    START = auto()
    ASK_DEST = auto()
    ASK_DATE = auto()
    CONFIRM = auto()
    DONE = auto()

class Event(Enum):
    WANT_BOOK = auto()
    GIVE_DEST = auto()
    GIVE_DATE = auto()
    YES = auto()

# 转移表用 (State, Event) 作为键，IDE 和类型检查器都能帮你查错
TRANSITIONS = {
    (State.START,     Event.WANT_BOOK): State.ASK_DEST,
    (State.ASK_DEST,  Event.GIVE_DEST): State.ASK_DATE,
    (State.ASK_DATE,  Event.GIVE_DATE): State.CONFIRM,
    (State.CONFIRM,   Event.YES):       State.DONE,
}

class FlightAgent:
    def __init__(self):
        self.state: State = State.START
        self.data = {}

    def handle(self, event: Event, payload: str = "") -> str:
        nxt = TRANSITIONS.get((self.state, event))
        if nxt is None:
            return f"[忽略] 状态 {self.state.name} 下无法处理 {event.name}"
        self.state = nxt
        self.data[event.name] = payload
        return f"→ 转移到 {self.state.name}"

# 试一试：忘给日期直接确认，会被拦住
agent = FlightAgent()
print(agent.handle(Event.WANT_BOOK))
print(agent.handle(Event.GIVE_DEST, "上海"))
print(agent.handle(Event.YES))          # 不合规转移，会被拦截
print(agent.handle(Event.GIVE_DATE, "明天"))
print(agent.handle(Event.YES))
```

**好处**：拼错 `State.ASK_DST` 会被 IDE 立刻标红，不用等运行时。

---

## 五、工程化：把状态机做成可配置的类

真实 Agent 里状态会越来越多。我们可以把"状态机骨架"抽象成一个可复用类，让业务方只写**表**和**动作**：

```python
from typing import Callable, Optional

Action = Callable[[dict], str]   # 每个状态进入时要执行的动作（比如调用 LLM）

class StateMachine:
    """通用状态机：表驱动（Table-Driven），逻辑与数据分离。"""
    def __init__(self, init_state: str, transitions: dict, on_enter: dict):
        self.state = init_state
        self.transitions = transitions      # {(state, event): next_state}
        self.on_enter = on_enter            # {state: 动作函数}
        self.context: dict = {}             # 跨状态共享的上下文

    def fire(self, event: str, payload: dict | None = None) -> str:
        # 1) 查表
        nxt: Optional[str] = self.transitions.get((self.state, event))
        if nxt is None:
            return f"[invalid] {self.state} × {event}"

        # 2) 记住输入
        if payload:
            self.context.update(payload)

        # 3) 切换状态
        self.state = nxt

        # 4) 执行该状态的"入场动作"（这里通常是调用 LLM）
        return self.on_enter[self.state](self.context)

# ===== 业务侧只需配置 =====
transitions = {
    ("START",   "user_intent"): "INTENT",
    ("INTENT",  "is_search"):   "SEARCH",
    ("INTENT",  "is_chat"):     "CHAT",
    ("SEARCH",  "done"):        "ANSWER",
    ("CHAT",    "done"):        "ANSWER",
}

def enter_intent(ctx):
    ctx.setdefault("tools", ["search", "chat"])
    return f"请选择工具：{ctx['tools']}"

def enter_search(ctx):
    return f"[调用搜索工具] 查询：{ctx.get('query', '')}"

def enter_chat(ctx):
    return "[调用对话模型] 你好，我是助手～"

def enter_answer(ctx):
    return "[汇总] 任务完成。"

on_enter = {
    "INTENT": enter_intent,
    "SEARCH": enter_search,
    "CHAT":   enter_chat,
    "ANSWER": enter_answer,
}

sm = StateMachine("START", transitions, on_enter)
print(sm.fire("user_intent"))
print(sm.fire("is_search", {"query": "今天天气"}))
print(sm.fire("done"))
```

**输出**：
```
请选择工具：['search', 'chat']
[调用搜索工具] 查询：今天天气
[汇总] 任务完成。
```

看到没？业务逻辑被彻底抽离开——你后面接 LangGraph、接真实 LLM 调用，只要换掉 `on_enter` 里的函数就行。这正是主流 Agent 框架（如 LangGraph 的 `StateGraph`、AutoGen 的 `GroupChat` 状态）背后的思想。

---

## 小结一句话

> **状态机 = 状态（我在哪） + 事件（发生了什么） + 转移表（接下来去哪） + 上下文（我记住了什么）。**

掌握这套模式，你就理解了当下主流 Agent 框架的"骨架"。

```python
from enum import Enum, auto
from typing import Callable

# ========= 1. 定义状态和事件（用枚举更安全） =========
class State(Enum):
    START   = auto()
    ASK_DEST = auto()
    ASK_DATE = auto()
    CONFIRM = auto()
    DONE    = auto()

class Event(Enum):
    WANT_BOOK = auto()
    GIVE_DEST = auto()
    GIVE_DATE = auto()
    YES       = auto()

# ========= 2. 转移表：状态机的大脑 =========
TRANSITIONS = {
    (State.START,    Event.WANT_BOOK): State.ASK_DEST,
    (State.ASK_DEST, Event.GIVE_DEST): State.ASK_DATE,
    (State.ASK_DATE, Event.GIVE_DATE): State.CONFIRM,
    (State.CONFIRM,  Event.YES):       State.DONE,
}

# ========= 3. 通用状态机类 =========
Action = Callable[[dict], str]

class StateMachine:
    """表驱动的状态机：便于扩展到真实 Agent。"""
    def __init__(self, init: State, transitions: dict, on_enter: dict[State, Action]):
        self.state = init
        self.transitions = transitions
        self.on_enter = on_enter
        self.context: dict = {}       # 跨状态共享的记忆

    def fire(self, event: Event, payload: str = "") -> str:
        nxt = self.transitions.get((self.state, event))
        if nxt is None:
            return f"[invalid] 状态 {self.state.name} 无法响应 {event.name}"
        if payload:
            self.context[event.name] = payload
        self.state = nxt
        return self.on_enter[self.state](self.context)

# ========= 4. 每个状态的入场动作（这里假装是回复用户 / 调 LLM） =========
def enter_ask_dest(ctx: dict) -> str:
    return "请问您要去哪里？"

def enter_ask_date(ctx: dict) -> str:
    dest = ctx.get("GIVE_DEST", "?")
    return f"好的，{dest}。请问什么时候出发？"

def enter_confirm(ctx: dict) -> str:
    return f"请确认：去{ctx['GIVE_DEST']}，{ctx['GIVE_DATE']} 出发？（YES 确认）"

def enter_done(ctx: dict) -> str:
    return "✅ 已为您预订成功！"

ON_ENTER = {
    State.ASK_DEST: enter_ask_dest,
    State.ASK_DATE: enter_ask_date,
    State.CONFIRM:  enter_confirm,
    State.DONE:     enter_done,
}

# ========= 5. 跑一遍完整流程 =========
if __name__ == "__main__":
    sm = StateMachine(State.START, TRANSITIONS, ON_ENTER)
    print(sm.fire(Event.WANT_BOOK))
    print(sm.fire(Event.GIVE_DEST, "北京"))
    print(sm.fire(Event.YES))                       # 非法：还没给日期
    print(sm.fire(Event.GIVE_DATE, "下周一"))
    print(sm.fire(Event.YES))
```


---

## 本课题目

### single_choice · None



- [A] 串行链式工作流
- [B] 并行化工作流
- [C] 路由工作流
- [D] 评估-优化工作流

**参考答案**：3

**解析**：该模式先生成多个候选，再通过独立评估步骤筛选或优化，属于评估-优化工作流。串行链式是线性传递；并行化强调同时执行互不依赖的子任务；路由是依据输入选择后续路径。

### single_choice · None



- [A] 路由工作流
- [B] 并行化工作流
- [C] 串行链式工作流
- [D] 人工审核工作流

**参考答案**：0

**解析**：根据输入分类决定后续路径，是路由工作流的典型特征。并行化是同时执行多个分支并汇总；串行链式是固定顺序传递；人工审核强调人的介入。

### single_choice · None



- [A] 所有输入都需要经过完全相同的处理步骤
- [B] 不同类别的输入需要走不同的处理分支
- [C] 需要多个模型同时处理同一份数据
- [D] 需要对同一输出反复生成和评估

**参考答案**：1

**解析**：路由工作流适合按输入类别选择不同分支。所有输入走相同步骤适合串行链式；同时处理同一份数据适合并行化；反复生成评估适合评估-优化。

### single_choice · None



- [A] 并行化工作流中各子任务通常互不依赖，串行链式工作流中后一步依赖前一步输出
- [B] 并行化工作流不需要汇总结果，串行链式工作流需要汇总
- [C] 并行化工作流只能有一个步骤，串行链式工作流可以有多个步骤
- [D] 并行化工作流必须使用路由，串行链式工作流必须使用评估

**参考答案**：0

**解析**：并行化强调子任务互不依赖、同时执行；串行链式强调固定顺序、后一步依赖前一步输出。并行化通常需要汇总；两者都可以有多个步骤；它们不强制依赖路由或评估。

### single_choice · None



- [A] 路由工作流
- [B] 并行化工作流
- [C] 串行链式工作流
- [D] 评估-优化工作流

**参考答案**：1

**解析**：拆分成多个可独立处理的章节并行总结再合并，属于并行化工作流。路由是按类别选择分支；串行链式是顺序执行；评估-优化是生成与评估循环。

### single_choice · None



- [A] 仅返回一个布尔值表示是否通过
- [B] 具体的修改建议或评分维度上的反馈
- [C] 完整的原始输入副本
- [D] 下一个用户的身份信息

**参考答案**：1

**解析**：要让优化环节知道如何改，评估应给出具体反馈或分维度评分。仅返回布尔值信息量太少；原始输入副本和用户身份信息不能直接指导优化。

### single_choice · None



- [A] 串行链式与并行化
- [B] 路由与串行链式
- [C] 并行化与评估-优化
- [D] 评估-优化与路由

**参考答案**：1

**解析**：先判断类型再选择工具属于路由；判断、调用、整理按顺序执行属于串行链式。没有同时并行执行多个分支，也没有生成-评估循环。

### single_choice · None



- [A] 步骤之间的数据传递方式
- [B] 失败时的重试或降级策略
- [C] 模型参数的具体数值来源
- [D] 分支选择或汇总逻辑

**参考答案**：2

**解析**：工作流模式关注步骤编排、数据传递、分支与汇总、失败处理等。模型参数的具体数值来源属于模型配置或调参问题，不是工作流模式本身的核心关注点。

### single_choice · None



- [A] 整个工作流必须立即丢弃所有已完成分支的结果
- [B] 应有重试、降级或忽略该分支并继续汇总的机制
- [C] 必须把失败分支的结果当作正确答案继续使用
- [D] 应关闭所有并行分支改为完全串行执行

**参考答案**：1

**解析**：健壮的工作流会对失败的分支采取重试、降级或跳过并继续汇总等策略。立即丢弃全部结果、把失败结果当正确答案、完全改为串行都不是通用最佳做法。

### single_choice · None



- [A] 并行化处理
- [B] 人工审核或兜底机制
- [C] 评估-优化循环
- [D] 串行链式回退

**参考答案**：1

**解析**：在路由无法可靠决策时交给人工确认，属于引入人工审核或兜底机制。并行化、评估-优化循环、串行链式回退都不是这里的主要手段。

### single_choice · None



- [A] 评估-优化工作流一定比串行链式工作流消耗更少资源
- [B] 评估-优化工作流包含根据评估结果的反馈循环，串行链式工作流没有
- [C] 串行链式工作流不需要任何输入
- [D] 评估-优化工作流不能包含串行步骤

**参考答案**：1

**解析**：评估-优化的关键特征是评估结果反馈给生成环节形成循环；串行链式是单向顺序执行。评估-优化通常消耗更多资源；串行链式也需要输入；评估-优化内部也可以有串行步骤。

### single_choice · None



- [A] 每一步都假设上一步一定成功，不做任何校验
- [B] 为关键步骤设置校验与异常处理，并定义失败后的替代路径
- [C] 尽量把所有步骤合并成一次模型调用以省略中间检查
- [D] 让所有分支都依赖同一个外部服务且不设超时

**参考答案**：1

**解析**：关键步骤设置校验、异常处理和替代路径，可以提升工作流可靠性。不做校验、合并省略检查、单点依赖且无超时都会放大故障影响。

### single_choice · None



- [A] 各步骤之间必须共享同一个提示词模板
- [B] 每一步的输出会作为下一步的输入，按固定顺序执行
- [C] 所有步骤必须同时开始执行以降低延迟
- [D] 它要求每个步骤都调用不同的模型供应商

**参考答案**：1

**解析**：串行链式工作流的核心是固定顺序，前一步输出作为后一步输入。共享提示词模板、同时开始、必须使用不同模型供应商都不是其必要条件。

### single_choice · None



- [A] 路由工作流
- [B] 并行化工作流
- [C] 评估-优化工作流
- [D] 串行链式工作流

**参考答案**：2

**解析**：生成代码后由测试作为评估手段，失败则反馈并重新生成，形成评估-优化循环。路由是分类选择；并行化是同时执行；串行链式没有基于评估的反馈重试。

### single_choice · None



- [A] 串行链式工作流
- [B] 路由工作流
- [C] 并行化工作流
- [D] 评估-优化工作流

**参考答案**：2

**解析**：任务之间无依赖时，可以并行执行多个子任务再汇总结果，以缩短总耗时。串行链式会按顺序执行；路由是选择路径；评估-优化强调生成与评估的迭代。

### single_choice · None



- [A] 路由工作流
- [B] 并行化工作流
- [C] 评估-优化工作流
- [D] 串行链式工作流

**参考答案**：2

**解析**：生成后由独立评估环节给出反馈并驱动重写，属于评估-优化工作流。串行链式不包含根据评估结果回环修改的机制；路由是分类选择；并行化是同时执行。

### single_choice · None



- [A] 由下游智能体执行结束后反向决定
- [B] 由模型或规则对输入进行分类或判断
- [C] 由系统随机分配以平衡负载
- [D] 由用户手动选择每一次的执行路径

**参考答案**：1

**解析**：路由模式的关键是先对输入进行分类或判断，再决定走哪条分支，通常由模型或规则完成。反向决定、随机分配、用户手动选择都不是路由模式的典型做法。

### single_choice · None



- [A] 并行执行的各分支之间必须存在严格的先后依赖
- [B] 并行执行后通常需要一个汇总或聚合步骤来合并结果
- [C] 并行化工作流只能用于图像处理任务
- [D] 并行化工作流不需要任何任务分解

**参考答案**：1

**解析**：并行化工作流将任务分解为可独立执行的子任务并行处理，之后通常需要汇总或聚合。严格先后依赖与并行相矛盾；它不限于图像任务；任务分解是其前提。

### single_choice · None



- [A] 评估-优化工作流
- [B] 路由工作流
- [C] 串行链式工作流
- [D] 并行化工作流

**参考答案**：1

**解析**：先判断意图再分派到不同流程，属于路由工作流。评估-优化涉及生成与评估循环；串行链式是固定顺序；并行化是同时执行多个分支。

### single_choice · None



- [A] 并行化工作流
- [B] 路由工作流
- [C] 串行链式工作流
- [D] 评估-优化工作流

**参考答案**：2

**解析**：两个步骤按固定顺序执行，前一步输出作为后一步输入且不回退，属于串行链式工作流。并行化要求同时执行；路由要求分类选择；评估-优化要求有评估反馈循环。

### single_choice · None



- [A] 工作流会立即抛出异常终止
- [B] 优化环节会失去作用，无法提升输出质量
- [C] 并行分支会自动合并
- [D] 路由决策会变成随机选择

**参考答案**：1

**解析**：评估环节的作用是发现问题并驱动优化。若评估总是通过，优化步骤就不会被触发，工作流退化为一次生成，质量提升有限。其他选项描述的行为与评估结果无关。

### single_choice · None



- [A] Agent 在当前时刻对外部环境的所有感知输入的集合
- [B] Agent 在某一时刻所处的、决定其后续可选动作与转移条件的处境或阶段
- [C] Agent 从启动到当前所执行的全部动作的历史日志
- [D] Agent 内部维护的全部变量的完整快照，包括临时计算中间值

**参考答案**：1

**解析**：状态机中的状态是抽象后「决定下一步行为」的处境，它决定了在该状态下哪些转移被允许。A 描述的是输入/观测，C 是轨迹历史，D 是过度的实现细节快照，都不是状态机的状态定义。

### single_choice · None



- [A] 状态集合的一个成员
- [B] 初始状态的选择
- [C] 状态转移的守卫条件（guard）
- [D] 终止状态的判定

**参考答案**：2

**解析**：「只有满足某条件才允许转移」属于转移上的守卫条件，用来约束状态之间的迁移。它不是状态本身，也不决定初始/终止状态。

### multi_choice · None



- [A] 终止状态表示 Agent 已完成任务或应当停止运行
- [B] 一个状态机可以有多个终止状态
- [C] 终止状态不能有出边
- [D] 终止状态必须与初始状态相同

**参考答案**：[0, 1, 2]

**解析**：终止状态表示流程结束，可以有多个，通常不设出边以避免流程继续。它与初始状态是不同角色，不必相同。

### multi_choice · None



- [A] 将语义相近、转移条件一致的处境合并为一个状态
- [B] 把状态信息中可计算得到的部分放到外部变量而不是拆成新状态
- [C] 为每一种输入组合都单独定义一个状态
- [D] 用层级状态机把公共行为提取到父状态中

**参考答案**：[0, 1, 3]

**解析**：合并等价状态、把可推导信息外置、使用层级状态机都能控制状态数量。为每种输入组合单独建状态恰恰是状态爆炸的常见成因。

### multi_choice · None



- [A] 守卫条件用于判断在给定事件下是否允许某条转移发生
- [B] 当同一事件对应多条转移时，可用互斥的守卫条件决定走哪一条
- [C] 守卫条件应当尽量保持无副作用
- [D] 守卫条件可以修改状态机的状态以辅助判断

**参考答案**：[0, 1, 2]

**解析**：守卫是判断是否允许转移的条件，可用来在多条候选转移间做选择，并应保持无副作用。修改状态属于动作而非守卫的职责。

### multi_choice · None



- [A] 从「解析请求」到「执行工具调用」存在一条守卫条件过宽的转移
- [B] 「校验参数」状态的入口守卫写成了恒真条件
- [C] 状态机缺少初始状态
- [D] 「解析请求」状态的事件被映射到了非预期的目标状态

**参考答案**：[0, 1, 3]

**解析**：跳过校验通常是因为存在越级转移、校验守卫恒真、或事件被错误映射到错误目标。缺少初始状态会导致启动失败，而不是跳过某个中间状态。

### fill_blank · None



**参考答案**：["转移", "迁移", "transition", "transitions"]

**解析**：转移表（迁移表）以「当前状态 × 事件」为索引，给出目标状态与可能的守卫和动作，是状态机实现的核心数据结构。

### fill_blank · None



**参考答案**：["初始", "起始", "initial", "start"]

**解析**：初始状态是状态机开始运行时进入的第一个状态，是所有转移的起点。

### fill_blank · None



**参考答案**：["动作", "action", "actions", "副作用"]

**解析**：动作是在状态进入、退出或转移发生时执行的副作用逻辑，与只做判断的守卫条件相区分。

### code_reading · None



**参考答案**：Executing

**解析**：Idle 收到 e1 进入 Parsing；Parsing 收到 e2 进入 Validating；Validating 收到 e3 进入 Executing。因此最终状态为 Executing。

### code_reading · None



**参考答案**：Unknown

**解析**：A 收到 e1 进入 B，B 收到 e2 进入 C，C 收到 e3 时没有对应转移，于是进入 Unknown 并跳出循环，输出 Unknown。

### scenario · None



**解析**：该问题源于多条输入同时到达时，转移在状态间来回抖动。解决方案包括：把输入先放入缓冲或事件队列再合并处理，对快速连续输入做防抖/节流，在守卫条件中显式要求「输入已稳定」才迁移，并重新审视状态划分，避免把「等待输入」和「已收到输入」混在同一个状态里。

### single_choice · None



- [A] FSM 的状态数必须是无限的，才能表达复杂 Agent 逻辑
- [B] FSM 在任一时刻只处于有限个状态中的一个，且转移由当前状态与输入决定
- [C] FSM 不允许存在从某状态回到自身的转移
- [D] FSM 的转移只能由时间触发，不能由输入事件触发

**参考答案**：1

**解析**：有限状态机的核心特征是状态集合有限、当前时刻处于单一状态、下一状态由当前状态和输入共同决定。自环转移是允许的，转移也可由事件触发，状态数也无需无限。

### scenario · None



**解析**：核心是控制状态爆炸：引入层级状态机把公共转移和行为提取到父状态，合并语义等价的子状态，把可由其他状态推导的信息外置为变量，将状态数与输入组合解耦。这样能显著减少转移数量和漏改风险。

### single_choice · None



- [A] 状态总数减少，运行速度必然变慢
- [B] 无法区分是否已收到输入，导致在缺少输入时也触发下一步动作
- [C] FSM 会退化成无限状态机
- [D] 转移条件会自动失效

**参考答案**：1

**解析**：合并状态会丢失区分不同处境的能力，使得守卫条件无法判断「是否已收到输入」，从而在错误时机触发转移。状态数减少本身不会导致变慢或使 FSM 变为无限。

### single_choice · None



- [A] 表示 Agent 已经完成所有任务的状态
- [B] 表示 Agent 启动后最先进入的状态，是转移的起点
- [C] 表示 Agent 出错时才会进入的状态
- [D] 表示 Agent 可以接受任意输入的万能状态

**参考答案**：1

**解析**：初始状态是运行开始时进入的起点状态，决定了第一条转移从何处出发。终止状态、错误状态、万能状态都是不同概念。

### single_choice · None



- [A] 该状态永远不会被进入
- [B] Agent 进入该状态后会「卡死」，无法继续转移
- [C] 该状态会自动跳到初始状态
- [D] 该状态的守卫条件会失效

**参考答案**：1

**解析**：没有出边且非终止的状态是死状态，进入后无法继续迁移，表现为流程卡死。它仍可能被进入，也不会自动回到初始状态。

### single_choice · None



- [A] 事件是持续存在的，状态是瞬时发生的
- [B] 事件是触发转移的外部或内部信号，状态是系统在两次事件之间所处的处境
- [C] 事件和状态是同一概念的不同叫法
- [D] 事件只能由用户产生，状态只能由程序产生

**参考答案**：1

**解析**：事件是瞬时的触发信号，用来驱动转移；状态是系统在事件之间保持的处境。二者不是同义词，来源也不限于用户或程序。

### single_choice · None



- [A] 动作只能定义在状态上，不能定义在转移上
- [B] 动作是在进入状态、退出状态或执行转移时附带产生的副作用
- [C] 动作决定了状态机的状态数量
- [D] 动作必须是纯函数，不能产生任何副作用

**参考答案**：1

**解析**：动作是状态机执行过程中附带的副作用，可以绑定在进入/退出状态或转移上。它不决定状态数量，也不是必须为纯函数。

### single_choice · None



- [A] 守卫条件变为纯判断，无法执行解析逻辑
- [B] 解析逻辑可能被多次重复执行，因为它会在每次评估守卫时运行
- [C] 状态机会因此进入无限循环
- [D] 转移将无法触发

**参考答案**：1

**解析**：守卫条件可能在一次决策中被多次评估，其中执行有副作用的解析会造成重复计算。守卫应保持无副作用的纯判断，解析这类逻辑更适合放在动作中。

### single_choice · None



- [A] 状态机状态数过多
- [B] 活锁，Agent 会一直在循环中打转而无法完成目标
- [C] 初始状态未定义
- [D] 守卫条件缺失导致转移无法触发

**参考答案**：1

**解析**：无退出条件的循环会让 Agent 在若干状态间反复迁移而不推进目标，属于活锁。它与状态数、初始状态、守卫缺失是不同的缺陷。
