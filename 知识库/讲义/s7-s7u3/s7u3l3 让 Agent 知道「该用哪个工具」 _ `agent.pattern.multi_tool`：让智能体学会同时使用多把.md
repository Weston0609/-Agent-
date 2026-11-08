# s7u3l3 让 Agent 知道「该用哪个工具」 / `agent.pattern.multi_tool`：让智能体学会同时使用多把工具

> 来源 `content/lessons/s7u3l3.json`

## agent.pattern.tool_router

# agent.pattern.tool_router：让 Agent 知道「该用哪个工具」

## 一句话直觉

当 AI Agent（智能体）手里有十几个工具（搜索、计算器、数据库、发邮件……）时，用户一句话进来，它必须**先判断该调用哪个（或哪几个）工具**，再去填空调用——这个「先选工具，再填参数」的模式就叫 **Tool Router（工具路由）**。

它是所有 Agent 的起点：没有路由，工具再多也只是一个摆设的抽屉。

---

## 1. 为什么需要 Tool Router

一个 Agent 的核心循环通常是：

```
用户输入 → 选择工具 → 填参数 → 执行 → 观察结果 → 生成回答
```

Tool Router 就是第二步。它本质上是一个**分类 + 参数抽取**问题：

- 输入：用户自然语言 + 一份工具清单（每个工具有名字、描述、参数 schema）
- 输出：`(tool_name, arguments)` 或「无需调用工具」

现代做法把这件事交给 LLM（大语言模型）用 **function calling / tool calling** 完成；传统做法可以是一个分类器或关键词匹配。我们先讲传统做法理解本质，再上 LLM。

---

## 2. 工具注册表：给每个工具一个「身份证」

要让路由器能选工具，工具必须具备**结构化元数据**：名字、描述、参数类型。Python 里用 `dataclass` 和 `typing` 表达最自然。

注意：从 Python 3.9 起，内置的 `tuple`、`dict`、`list` 已经支持直接下标（`tuple[int, str]`），`typing.Tuple`、`typing.Dict` 只是**弃用的别名**。新代码优先用内置泛型。

```python
from dataclasses import dataclass, field
from typing import Callable, Any

@dataclass
class Tool:
    name: str
    description: str
    # 参数名 -> 类型说明字符串，例如 {"city": "str"}
    parameters: dict[str, str] = field(default_factory=dict)
    func: Callable[..., Any] | None = None

    def to_schema(self) -> dict:
        """导出成 LLM 能读的 JSON schema 风格。"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }
```

**关键结论**：路由器是「读」注册表的，而不是「猜」函数的——工具必须有可以被程序读取的描述。

---

## 3. 最简单的路由器：关键词打分（理解本质）

在接入 LLM 之前，先用一个玩具路由器把「选择」逻辑跑通。它把所有工具的 name + description 拼起来，跟用户输入做词重叠打分，选最高分。

```python
class KeywordRouter:
    def __init__(self, tools: list[Tool]):
        self.tools = tools

    def route(self, query: str) -> tuple[str | None, float]:
        q = query.lower()
        best, best_score = None, 0.0
        for t in self.tools:
            text = (t.name + " " + t.description).lower()
            # 单词级重叠
            score = sum(1 for w in q.split() if w in text)
            if score > best_score:
                best, best_score = t.name, float(score)
        return best, best_score
```

**关键结论**：路由 = 打分 = argmax。换掉打分函数，就换掉了整个路由器。

---

## 4. LLM 作为路由器：function calling 形态

真正工程上，打分交给 LLM。你只需把工具 schema 作为 `tools` 参数传给模型，模型返回「要调哪个工具 + 参数」。下面是伪代码（各家 SDK 名字略有差异，模式一致）：

```python
def route_with_llm(client, tools: list[Tool], user_input: str):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "你是工具路由，只负责选工具和填参数。"},
            {"role": "user", "content": user_input},
        ],
        tools=[{"type": "function", "function": t.to_schema()} for t in tools],
        tool_choice="auto",  # 允许「不调用工具」
    )
    msg = response.choices[0].message
    if not msg.tool_calls:
        return None, {}          # 走纯聊天
    call = msg.tool_calls[0]
    import json
    return call.function.name, json.loads(call.function.arguments)
```

**关键结论**：LLM 只负责「选 + 填」，**执行**和**错误处理**仍然是你的 Python 代码的事。这是 Agent 架构里最容易被混淆的边界。

---

## 5. 把路由串成一个可用的 Agent 步骤

最终形态是三步：路由 → 校验 → 分发。校验很重要：LLM 可能编造不存在的工具名或漏填参数。

```python
class Agent:
    def __init__(self, tools: list[Tool]):
        self.registry = {t.name: t for t in tools}

    def dispatch(self, tool_name: str, args: dict) -> Any:
        if tool_name not in self.registry:
            raise ValueError(f"未知工具: {tool_name}")
        tool = self.registry[tool_name]
        missing = [k for k in tool.parameters if k not in args]
        if missing:
            raise ValueError(f"缺少参数: {missing}")
        return tool.func(**args) if tool.func else None
```

**关键结论**：路由器的输出必须被**外部校验**，永远不要相信 LLM 一定会给你合法工具名和完整参数。

---

## 动手练习

在本地写一个 `mini_router.py`，完成：

1. 用 `@dataclass` 定义 `Tool`，字段：`name`、`description`、`parameters`（dict）。
2. 注册 3 个工具：`get_weather(city: str)`、`add(a: int, b: int)`、`send_email(to: str, subject: str)`，`func` 用简单 print 占位。
3. 实现 `KeywordRouter.route(query)`，返回 `(tool_name, score)`。
4. 用 `Agent.dispatch` 跑通三个测试 query：
   - `"北京天气怎么样"` → 期望 `get_weather`
   - `"1 加 2 等于几"` → 期望 `add`
   - `"给 alice 发邮件"` → 期望 `send_email`
5. 打印每一次「路由结果」和「分发结果」。

进阶：把 `KeywordRouter` 换成调用任一 LLM 的 function calling 版本，保持 `Agent.dispatch` 不变，验证接口一致性。

```python
from dataclasses import dataclass, field
from typing import Callable, Any


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, str] = field(default_factory=dict)
    func: Callable[..., Any] | None = None

    def to_schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }


class KeywordRouter:
    """最朴素的工具路由器：按词重叠打分。"""

    def __init__(self, tools: list[Tool]):
        self.tools = tools

    def route(self, query: str) -> tuple[str | None, float]:
        q = query.lower()
        best_name, best_score = None, 0.0
        for t in self.tools:
            text = (t.name + " " + t.description).lower()
            score = float(sum(1 for w in q.split() if w in text))
            if score > best_score:
                best_name, best_score = t.name, score
        return best_name, best_score


class Agent:
    def __init__(self, tools: list[Tool]):
        self.registry = {t.name: t for t in tools}

    def dispatch(self, tool_name: str, args: dict) -> Any:
        if tool_name not in self.registry:
            raise ValueError(f"未知工具: {tool_name}")
        tool = self.registry[tool_name]
        missing = [k for k in tool.parameters if k not in args]
        if missing:
            raise ValueError(f"缺少参数: {missing}")
        return tool.func(**args) if tool.func else None


# --- 组装 ---
if __name__ == "__main__":
    tools = [
        Tool("get_weather", "查询天气 weather", {"city": "str"},
             lambda city: f"{city} 晴"),
        Tool("add", "加法计算 add", {"a": "int", "b": "int"},
             lambda a, b: a + b),
        Tool("send_email", "发送邮件 email", {"to": "str", "subject": "str"},
             lambda to, subject: f"已发给 {to}: {subject}"),
    ]
    router = KeywordRouter(tools)
    agent = Agent(tools)

    for q in ["weather 北京", "add 1 2", "email alice hello"]:
        name, score = router.route(q)
        print(f"query={q!r} -> tool={name} score={score}")
```

## agent.pattern.multi_tool

# `agent.pattern.multi_tool`：让智能体学会同时使用多把工具

## 一句话直觉（为什么要学它）

当你问 AI“北京今天适合跑步吗？”它需要同时查天气、看空气质量、再推荐路线——这把“多个工具协同完成任务”的套路，就是 `multi_tool` 模式。

---

## 一、从一个工具到多个工具：为什么要多工具？

**工具（Tool）** 在 AI 智能体（Agent）语境里，指的是智能体可以调用的外部函数或 API，比如查天气、算数学、搜网页。

早期智能体往往只挂一个工具。但真实任务很少只用一把锤子。你问“帮我订一张明天从上海到北京的高铁票”，智能体要先查车次、再比价格、最后下单——每一步都可能对应不同工具。

**关键结论**：多工具模式（multi-tool pattern）的核心，是让智能体根据任务自动选择并串联多个工具，而不是把全部逻辑塞进一个函数里。

```python
# 三个独立的小工具，各自只做一件事
def get_weather(city: str) -> str:
    """查询天气，返回字符串"""
    return f"{city} 晴，25℃"

def get_air_quality(city: str) -> str:
    """查询空气质量"""
    return f"{city} 空气优，AQI 35"

def suggest_route(city: str) -> str:
    """推荐跑步路线"""
    return f"{city} 推荐滨江步道"

# 组合调用，形成一次完整回答
def answer(city: str) -> str:
    return " | ".join([
        get_weather(city),
        get_air_quality(city),
        suggest_route(city),
    ])

print(answer("北京"))
```

---

## 二、工具必须长一个样：统一接口（Uniform Interface）

多工具模式要跑通，前提是所有工具**长得一模一样**：相同的入参风格、相同的返回结构。否则智能体没法自动挑选和拼接。

在 Python 里，最通用的做法是用 **元组（tuple）** 或字典把每个工具的描述、参数、函数打包。注意：单元素元组必须加逗号，否则 Python 会把它当成普通括号。

```python
# 单元素元组必须带逗号，这是 Python 的硬规则
FILES = ('setup.cfg',)   # 正确：单元素元组
# FILES = ('setup.cfg')  # 错误：这只是字符串

# 用元组统一描述工具： (名字, 描述, 函数)
tools = [
    ('get_weather', '查询指定城市天气', get_weather),
    ('get_air_quality', '查询指定城市空气质量', get_air_quality),
    ('suggest_route', '推荐指定城市跑步路线', suggest_route),
]

for name, desc, fn in tools:
    print(name, '->', desc, '->', fn.__name__)
```

**关键结论**：统一的元组结构让智能体“看到”工具列表时能一致地解析，避免为每个工具写特殊分支。

---

## 三、让智能体自己挑工具：路由（Routing）

有了统一接口，就可以做一个极简路由器：根据用户问题的关键词，决定调用哪几个工具。这就是多工具模式的最小可用版本。

```python
def route(question: str) -> list:
    """根据问题关键词返回要调用的工具名列表"""
    plan = []
    if '天气' in question or '跑步' in question:
        plan.append('get_weather')
    if '空气' in question or '跑步' in question:
        plan.append('get_air_quality')
    if '路线' in question or '跑步' in question:
        plan.append('suggest_route')
    return plan

print(route('北京今天适合跑步吗？'))
```

**关键结论**：多工具模式不必一开始就用大模型做规划，规则路由也能清楚地展示“选择—调用—聚合”的结构。

---

## 四、把结果聚合起来：聚合（Aggregation）

选好了工具，还要把多个返回结果合并成一条人类可读的答案。聚合层让智能体的输出保持整洁。

```python
TOOL_MAP = {name: fn for name, _, fn in tools}

def run_multi_tool(question: str, city: str) -> str:
    names = route(question)
    results = [TOOL_MAP[n](city) for n in names]
    return "\n".join(results)

print(run_multi_tool('北京今天适合跑步吗？', '北京'))
```

**关键结论**：把“选工具”“调工具”“拼结果”分成三层，代码可读、可测、可扩展。

---

## 五、工程级考量：错误、超时与可观测性

真实工程里工具会失败：网络断了、参数不对、超时。多工具模式必须处理**部分失败**——某个工具挂了，整体不能全崩。

```python
import time

def safe_call(fn, city: str, retries: int = 2) -> str:
    """带重试的安全调用，失败返回错误说明"""
    for i in range(retries + 1):
        try:
            return fn(city)
        except Exception as e:
            if i == retries:
                return f"[工具失败] {e}"
            time.sleep(0.1)

def run_safe(question: str, city: str) -> str:
    names = route(question)
    return "\n".join(safe_call(TOOL_MAP[n], city) for n in names)

print(run_safe('北京今天适合跑步吗？', '北京'))
```

**关键结论**：多工具模式的工程价值在于“单个工具失败不影响整体回答”，并留下可观测的错误信息。

---

## 动手练习

**任务**：在本地新建 `multi_tool_demo.py`，实现一个“旅行助手”智能体，满足：

1. 至少定义 3 个工具：查天气、查汇率、查景点。
2. 用元组 `(name, description, function)` 统一注册工具。
3. 写一个 `route(question)` 函数，依据关键词返回要调用的工具名列表。
4. 写一个 `run(question, city)` 函数，调用选中的工具并把结果拼成多行文本。
5. 用一个会抛异常的工具（如 `get_exchange_rate` 里 `raise ValueError('汇率服务不可用')`）测试 `safe_call` 的重试与降级。

运行示例：

```python
print(run('去杭州旅游要带伞吗？顺便看看汇率和景点', '杭州'))
```

期望输出至少包含天气、汇率、景点三部分，且某一工具失败时其他结果仍能正常打印。

```python
import time

# ---------- 1. 定义三个独立工具 ----------
def get_weather(city: str) -> str:
    """查询天气，返回简短描述"""
    return f"{city} 晴，25℃"

def get_air_quality(city: str) -> str:
    """查询空气质量"""
    return f"{city} 空气优，AQI 35"

def suggest_route(city: str) -> str:
    """推荐跑步路线"""
    return f"{city} 推荐滨江步道"

# ---------- 2. 统一注册为 (name, description, function) 元组 ----------
tools = [
    ('get_weather', '查询指定城市天气', get_weather),
    ('get_air_quality', '查询指定城市空气质量', get_air_quality),
    ('suggest_route', '推荐指定城市跑步路线', suggest_route),
]
TOOL_MAP = {name: fn for name, _, fn in tools}

# ---------- 3. 根据问题路由到工具名列表 ----------
def route(question: str) -> list:
    """多工具模式的最小路由器：按关键词决定调用哪些工具"""
    plan = []
    if '天气' in question or '跑步' in question:
        plan.append('get_weather')
    if '空气' in question or '跑步' in question:
        plan.append('get_air_quality')
    if '路线' in question or '跑步' in question:
        plan.append('suggest_route')
    return plan

# ---------- 4. 带重试与降级的安全调用 ----------
def safe_call(fn, city: str, retries: int = 2) -> str:
    """单个工具失败不影响整体，最多重试 retries 次"""
    for i in range(retries + 1):
        try:
            return fn(city)
        except Exception as e:
            if i == retries:
                return f"[工具失败] {e}"
            time.sleep(0.1)

# ---------- 5. 聚合多个工具的结果 ----------
def run_multi_tool(question: str, city: str) -> str:
    names = route(question)
    return "\n".join(safe_call(TOOL_MAP[n], city) for n in names)

if __name__ == '__main__':
    print(run_multi_tool('北京今天适合跑步吗？', '北京'))
    # 输出示例：
    # 北京 晴，25℃
    # 北京 空气优，AQI 35
    # 北京 推荐滨江步道
```


---

## 本课题目

### single_choice · None



- [A] 工具路由（Tool Router）：先对用户意图进行分类，再决定调用哪个工具或是否直接回答
- [B] 函数调用（Function Calling）：模型在生成过程中直接输出结构化参数来调用函数
- [C] 思维链（Chain of Thought）：让模型逐步推理后再给出最终答案
- [D] 检索增强生成（RAG）：先从知识库检索相关内容再生成回答

**参考答案**：0

**解析**：题干强调「先判断交给哪个工具」，属于工具路由模式。函数调用是路由后真正执行工具时的机制；思维链是推理方式；RAG 是检索与生成结合，均不涉及工具选择决策。

### single_choice · None



- [A] 直接返回工具执行后的最终答案
- [B] 返回一个工具标识（如工具名称或编号），由主流程据此分发
- [C] 返回用户原始输入的改写版本
- [D] 返回本次对话的 token 消耗统计

**参考答案**：1

**解析**：路由模块的职责是「选路」，输出应是工具标识或路由决策，而不是执行结果、输入改写或统计信息。

### single_choice · None



- [A] 分类模型一定比大模型更准确
- [B] 可在低延迟/低成本下完成路由，但泛化能力可能不如大模型，需要更多训练数据
- [C] 分类模型无法处理自然语言输入
- [D] 分类模型不能输出多个类别

**参考答案**：1

**解析**：小模型路由的典型权衡是效率提升但泛化可能变差。它并非必然更准，也能处理文本并支持多分类，因此其余选项错误。

### single_choice · None



- [A] 路由模型随机或错误地在两者之间选择
- [B] 路由模型自动合并两个工具
- [C] 路由模型拒绝输出任何工具名
- [D] 工具注册表被清空

**参考答案**：0

**解析**：描述重叠会降低路由的区分度，导致误选。模型不会自动合并工具或清空注册表，也不会因此必然拒绝输出。

### single_choice · None



- [A] 直接把超时错误原文返回给用户，不做任何处理
- [B] 静默忽略失败，返回一个空答案
- [C] 捕获失败信息，回退到无需工具的回答或重试，并把情况告知用户
- [D] 把该工具从注册表中永久删除

**参考答案**：2

**解析**：稳健设计应处理失败并给出可理解的反馈，必要时重试或回退。直接抛错、静默忽略、永久删除工具都过于极端。

### single_choice · None



- [A] 仅用户当前这一句话
- [B] 仅系统时间
- [C] 用户当前输入、可用的工具列表及描述，必要时还包括对话历史
- [D] 仅工具的返回结果

**参考答案**：2

**解析**：路由需要知道用户要什么以及有哪些工具可用，多轮场景下还需要对话历史。仅用当前句、时间或工具返回值都不足以做出正确路由。

### single_choice · None



- [A] 增加搜索工具的调用超时时间
- [B] 在路由提示词或训练数据中明确「闲聊/无需工具」这一类，并加入相应样本
- [C] 把搜索工具改名为更短的名字
- [D] 减少工具返回结果的字段数量

**参考答案**：1

**解析**：问题在于路由缺少「无需工具」这一类的判别能力，应补充该类别的定义与样本。超时、改名、精简返回字段都不解决误路由。

### single_choice · None



- [A] 最终回答的平均长度
- [B] 路由准确率：将路由结果与人工标注的正确工具进行比较
- [C] 系统的内存占用
- [D] 工具注册表的工具总数

**参考答案**：1

**解析**：路由准确率直接衡量路由决策与期望工具的一致性。回答长度、内存、工具数量都不能反映路由是否正确。

### single_choice · None



- [A] 路由模块无法得到工具列表
- [B] 用户直接看到工具返回的结构化数据，缺乏对问题的针对性解释
- [C] 工具无法被调用
- [D] 路由准确率会下降到零

**参考答案**：1

**解析**：缺少整合阶段会导致工具原始输出直接暴露给用户。路由、工具调用并不依赖整合阶段，因此其余选项不成立。

### single_choice · None



- [A] 减少总调用次数
- [B] 每一步职责更单一，便于调试、评估和替换，出错时更容易定位问题
- [C] 可以完全避免参数抽取错误
- [D] 保证路由一定正确

**参考答案**：1

**解析**：拆分步骤可提升可调试性与可维护性，但不能保证零错误。它通常会增加调用次数，且路由正确性仍需评估验证。

### single_choice · None



- [A] 忽略新工具，只使用启动时固定的工具列表
- [B] 在每次路由时读取当前最新的工具注册表，使新工具立即可被路由到
- [C] 要求重启整个系统后才能使用新工具
- [D] 把新工具的描述硬编码进提示词

**参考答案**：1

**解析**：动态注册要求路由在运行时读取最新工具列表，否则新工具永远不被选中。重启或硬编码都违背动态注册的初衷；忽略新工具等于功能失效。

### single_choice · None



- [A] 让工具在被调用时校验输入是否符合自身职责，不符合则返回明确的错误信息
- [B] 让所有工具都返回相同格式的占位结果
- [C] 取消所有工具的输入校验以提升速度
- [D] 让路由模块忽略工具的返回信息

**参考答案**：0

**解析**：工具端做输入校验并返回明确错误，可使错误路由被尽早发现并由主流程回退或重路由。取消校验、统一占位结果、忽略返回信息都会掩盖问题。

### single_choice · None



- [A] 随机选择一个工具执行以避免空路由
- [B] 报错并终止对话
- [C] 返回一个表示「无需工具」的路由结果，交给主模型直接生成回答
- [D] 强制调用所有已注册工具并取第一个成功的结果

**参考答案**：2

**解析**：路由结果可以包含「不调用工具」这一分支，这是工具路由与纯函数调用的重要区别。随机选择或强制调用所有工具都会引入错误行为。

### single_choice · None



- [A] 规则匹配速度太慢
- [B] 关键词规则无法覆盖语义等价的表达，导致漏路由
- [C] 规则匹配会导致工具被重复调用
- [D] 规则匹配无法返回工具名称

**参考答案**：1

**解析**：该请求语义上需要天气信息，但未包含「天气」关键词，说明纯关键词规则的泛化能力不足。速度、重复调用、返回值格式都不是该场景的核心问题。

### single_choice · None



- [A] 减少模型生成答案所需的 token 数
- [B] 让路由模型基于语义而非字符串匹配来选择工具
- [C] 保证工具调用一定成功
- [D] 避免主模型参与后续回答

**参考答案**：1

**解析**：提供工具描述能让路由模型进行语义判断，从而选择正确的工具。它不能保证调用成功，也不必然减少 token，更不会排除主模型。

### single_choice · None



- [A] 搜索网页，因为网页信息更新更快
- [B] 查询本地数据库，因为该问题指向内部业务数据
- [C] 两个都调用，然后让模型挑一个结果
- [D] 都不调用，直接让模型编造一个合理数字

**参考答案**：1

**解析**：「我们公司上季度销售额」属于内部数据，应走本地数据库。网页搜索适合公开信息；同时调用两个工具会造成资源浪费；让模型编造数字违背事实性原则。

### single_choice · None



- [A] 忽略该结果，直接返回空字符串
- [B] 把不存在的工具名当作新工具动态注册
- [C] 捕获该错误并回退到「无需工具、由主模型回答」或重新路由
- [D] 无限循环重新路由直到得到有效工具名

**参考答案**：2

**解析**：对无效路由结果应做容错回退，避免崩溃或死循环。动态注册不存在的工具既不安全也不合理；返回空字符串对用户无意义。

### single_choice · None



- [A] 禁止工具返回 JSON，强制返回纯文本
- [B] 在工具返回后增加一步「结果整合/格式化」，由主模型结合用户问题生成自然语言回答
- [C] 让路由模块直接生成最终答案
- [D] 把 JSON 中的所有键名改成中文

**参考答案**：1

**解析**：工具路由通常与「结果整合」阶段配合，把结构化结果转成对用户友好的回答。禁止工具返回 JSON 会限制表达力；路由模块不负责生成答案；改键名不解决可读性问题。

### single_choice · None



- [A] 两者完全等价，只是叫法不同
- [B] 函数调用是模型输出结构化调用的能力，工具路由是决定「调用哪个/是否调用」的决策层，二者可配合使用
- [C] 有了函数调用就不需要工具路由
- [D] 工具路由只能用于非函数调用的场景

**参考答案**：1

**解析**：函数调用解决「怎么调用」，工具路由解决「调不调、调哪个」，二者是不同层次的能力，可组合使用。因此 A、C、D 都错误。

### single_choice · None



- [A] 路由速度变慢
- [B] 无法完成需要多个工具协作（翻译工具 + 云盘工具）的任务
- [C] 翻译质量下降
- [D] 云盘工具无法被注册

**参考答案**：1

**解析**：单工具限制使需要多步工具协作的任务无法完成。速度、翻译质量、工具注册与该限制无直接关系。

### single_choice · None



- [A] 一个智能体在同一轮对话中只能调用一个固定的工具
- [B] 智能体可以在一次任务中根据上下文自主选择并调用多个不同的工具
- [C] 多个智能体必须同时并行运行，各自调用不同的工具
- [D] 工具必须由人类在每步手动指定后才能被调用

**参考答案**：1

**解析**：多工具模式的核心是『一个智能体面对多种可用工具，依据任务需要自主决定调用哪个（或哪些）工具』，而不是固定单工具、强制多智能体并行或必须人工指定。

### single_choice · None



- [A] 多工具模式中只有一个决策主体（一个智能体），它通过选择不同工具来扩展能力；多智能体模式中存在多个独立的决策主体
- [B] 多工具模式必须依赖多智能体才能实现
- [C] 多智能体模式中每个智能体只能使用一个工具
- [D] 两者完全等价，只是命名不同

**参考答案**：0

**解析**：区分的关键在于『决策主体的数量』：多工具是单一智能体 + 多个工具；多智能体是多个智能体，各自可有自己的工具集。二者不等价，也非互相必需。

### multi_choice · None



- [A] 智能体依据工具名称和描述来判断该调用哪个工具
- [B] 工具返回结果会作为新的上下文，影响后续决策
- [C] 智能体可能在一轮中不调用任何工具而直接回答
- [D] 智能体必须先调用工具才能产生任何回复

**参考答案**：[0, 1, 2]

**解析**：模型可基于描述选择工具、会根据工具结果继续判断，也可以在不需要工具时直接回答。『必须先调用工具』是错误限制。

### fill_blank · None



**参考答案**：["描述", "description", "自然语言描述", "工具描述"]

**解析**：工具的名称与描述是模型进行工具选择的关键依据，描述用自然语言说明该工具的用途与适用场景。

### fill_blank · None



**参考答案**：["数量", "个数", "数目", "多少"]

**解析**：多工具模式是单一智能体搭配多个工具；多智能体模式存在多个独立决策主体。区分点在于决策主体的数量。

### code_reading · None



**参考答案**：智能体可能先调用『查天气』了解下周北京气温，再调用『推荐酒店』、『订机票』等工具，最终综合结果给出行程建议。这体现了多工具模式下单个智能体依据任务上下文，自主选择并按需串联调用多个不同工具的能力。

**解析**：该任务需要多种能力（天气、交通、住宿），单一智能体会根据上下文决定调用哪些工具及顺序，这正是多工具模式的典型表现。

### code_reading · None



**参考答案**：应选择工具A。因为用户想了解的是『现在的天气』（实时），而工具A的描述是实时天气查询，工具B是未来一周预报，与需求不符。这说明工具描述是模型匹配用户意图、做出正确选择的关键依据。

**解析**：工具选择依赖描述与用户意图的匹配度。实时需求对应实时工具，预报工具不匹配，选错即体现描述理解偏差。

### code_reading · None



**参考答案**：可以。多工具模式并不要求每轮都必须调用工具。当智能体已有能力（如简单算术）直接得出答案时，可以不调用工具直接回复。是否调用工具取决于任务是否需要外部能力。

**解析**：多工具模式是『按需调用』，不是『必须调用』。简单问题模型可直接作答，体现了决策的灵活性。

### scenario · None



**解析**：这类问题需要从工具描述清晰度、调用顺序引导和上下文依赖几方面改进：明确说明『创建会议前应先查日历』，在描述中体现工具间的依赖关系，或通过提示引导多步调用。开放题只要覆盖关键词即可。

### scenario · None



**解析**：50+ 工具会造成选择困难与延迟。诊断应从工具数量是否过多、描述是否重叠模糊、职责是否单一入手，优化方式包括精简合并工具、澄清描述、必要时按场景分组或动态筛选可选工具，从而提升选择准确率。

### single_choice · None



- [A] 工具的源码实现细节
- [B] 每个工具的名称与自然语言描述（以及参数说明），结合当前对话上下文
- [C] 操作系统的环境变量
- [D] 用户的 IP 地址

**参考答案**：1

**解析**：工具的名称、描述和参数 schema 是智能体进行工具选择的主要依据，模型据此判断哪个工具适合当前任务；源码细节、环境变量、IP 一般与选择无关。

### single_choice · None



- [A] 保持重叠，让模型随便选，反正都能用
- [B] 删除其中一个工具，即使它还有其他有用功能
- [C] 精简或合并工具，使其职责边界清晰、描述互不混淆
- [D] 把两个工具的描述都改成一模一样的文字

**参考答案**：2

**解析**：工具描述重叠会让模型难以判断该选哪个，导致选择不稳定。工程上应明确划分职责或合并工具，让边界清晰，而非放任重叠或粗暴删除。

### single_choice · None



- [A] 立刻结束任务，不再考虑其他工具
- [B] 把结果作为新的上下文，判断是否需要继续调用其他工具或给出最终回答
- [C] 自动重新调用同一个工具直到成功
- [D] 丢弃结果，从头开始

**参考答案**：1

**解析**：多工具模式是迭代的：工具返回结果会回填到上下文中，智能体据此决定下一步——再调工具还是输出答案。直接结束或盲目重试都不合理。

### single_choice · None



- [A] 只提供一个万能工具，里面写死所有逻辑
- [B] 提供『查天气』和『服饰推荐』两个工具，智能体先调查天气，再依据结果调推荐工具
- [C] 把两个子任务分别交给两个完全独立的智能体，互不通信
- [D] 让用户自己查天气再告诉智能体

**参考答案**：1

**解析**：多工具模式鼓励把能力拆成明确、专一的工具，由同一智能体按需串联调用。万能工具违背职责单一，两个不通信的智能体也不是多工具模式的重点。

### single_choice · None



- [A] 描述只是给人看的注释，对模型没有影响
- [B] 描述是模型判断何时该调用该工具的重要线索，写得越清晰越好
- [C] 描述必须和函数名一模一样才有用
- [D] 描述越长越好，越啰嗦模型越容易选对

**参考答案**：1

**解析**：工具描述会作为提示的一部分提供给模型，是选择工具的关键依据，应准确、简洁、突出适用场景。它既不是无用注释，也不是越长越好。

### single_choice · None



- [A] 这是错误用法，一次任务只能调用一个工具
- [B] 这是允许的，多工具模式本就支持在任务中按需多次调用不同工具
- [C] 只有多智能体模式才允许多次调用
- [D] 必须三个工具同时并行调用才算正确

**参考答案**：1

**解析**：多工具模式允许在一个任务中多次、按需调用不同工具（可串行也可并行）。限制为单次调用或多智能体专属都是对模式的误解。

### multi_choice · None



- [A] 每个工具职责单一、边界清晰
- [B] 为工具提供准确且简洁的自然语言描述
- [C] 让多个工具的功能和描述高度重叠以增加冗余
- [D] 为工具参数定义清晰的类型和含义说明
- [E] 把所有功能塞进一个大工具以避免选择困难

**参考答案**：[0, 1, 3]

**解析**：职责单一、描述准确、参数清晰都是良好工具设计要素；功能重叠会干扰选择，大而全的工具违背单一职责、增加调用复杂度，均不合理。

### multi_choice · None



- [A] 工具数量过多导致模型选择困难或选错
- [B] 工具描述重叠导致调用结果不稳定
- [C] 工具调用链过长导致延迟或错误累积
- [D] 工具越多，智能体一定越准确

**参考答案**：[0, 1, 2]

**解析**：工具过多、描述重叠、链路过长都是真实存在的挑战；『工具越多越准确』是错误认知，工具过多反而会降低选择准确率。
