# s7u7l3 Agent 可观测性（Observability）与 LangSmith：从零到工程级 / 用 Langfuse 给 Agent 装上“黑匣子”：从零到工程级 / AI Agent 通常由 **LLM（大语言模型）调用*

> 来源 `content/lessons/s7u7l3.json`

## agent.obs.langsmith

# Agent 可观测性（Observability）与 LangSmith：从零到工程级

> **一句话直觉**：当你的 AI Agent（智能体）在真实场景里跑起来，你不可能靠 `print` 猜它为什么答错——LangSmith 就是替你记录**每一步思考、每次工具调用、每笔 token 花费**的"行车记录仪 + 诊断仪"。

---

## 一、为什么 Agent 需要可观测性？（5 分钟）

普通函数的输入输出是一对一的，出错好复现。但 Agent 是一个**多步、带工具、带分支**的推理循环（reasoning loop）：

```
用户问题 → LLM 思考 → 选工具 → 执行工具 → 再思考 → ... → 最终答案
```

问题来了：
- 中间哪一步跑偏了？
- 是 Prompt 写错了，还是工具返回垃圾数据？
- 为什么这次花了 8 秒、贵了 0.5 元？

**可观测性（Observability）** 就是让你能**回看、搜索、对比、复现**每一次运行的完整轨迹（trace）。LangSmith 是 LangChain 官方提供的托管平台，专门干这件事，并且对非 LangChain 框架也友好。

---

## 二、核心概念：Trace、Run、Span（8 分钟）

三个词一定要分清：

| 术语 | 英文 | 含义 |
|---|---|---|
| 运行 | Run | 一次被记录的单元（一次 LLM 调用、一次工具执行） |
| 追踪 | Trace | 一次完整任务的全过程，由多个 Run 组成的一棵树 |
| 跨度 | Span | 一次 Run 的持续时间/层级，和 Trace 里的节点同义 |

直觉：**Trace 是一棵树的根，每个 Run 是树上的一个节点**。

**关键结论**：你不需要 LangChain 也能用 LangSmith，只要用它的 `@traceable` 装饰器或 SDK 上报即可。

```python
# 最简示例：用 @traceable 记录一个普通函数
from langsmith import traceable

@traceable  # 被装饰的函数会自动成为一个 Run，并记录输入/输出/耗时
 def add(a: int, b: int) -> int:
    return a + b

# 调用时就会自动上报到 LangSmith（需先配置环境变量）
print(add(2, 3))
```

---

## 三、接入 LangSmith：三步走（8 分钟）

### 步骤 1：拿 API Key 并设置环境变量

```python
import os

# 实际使用时应从系统环境变量读取，不要硬编码在代码里
os.environ["LANGCHAIN_TRACING_V2"] = "true"                              # 打开上报开关
os.environ["LANGCHAIN_API_KEY"]  = "ls__xxx"                           # 你的 LangSmith Key
os.environ["LANGCHAIN_PROJECT"]  = "my-first-agent"                    # 项目名，方便分组
```

### 步骤 2：包一层 traceable，构造嵌套的 Trace 树

```python
from langsmith import traceable

@traceable(name="retrieve")            # 名字会直接显示在 LangSmith UI 里
 def retrieve_docs(query: str) -> list[str]:
    return ["doc-A", "doc-B"]           # 假装检索

@traceable(name="agent")                # 父节点
 def agent(question: str) -> str:
    docs = retrieve_docs(question)      # 子节点会自动挂到 agent 下
    return f"基于 {docs} 回答：{question}"

print(agent("什么是 LangSmith?"))
```

### 步骤 3：去 UI 看"这棵树"

跑完后打开 smith.langchain.com，你会看到：
- 一棵可折叠的调用树
- 每个节点的输入、输出、耗时、token 数
- 出错时的完整堆栈

**关键结论**：装饰器可以层层嵌套，LangSmith 会自动还原**调用层级**——这就是 Agent 可观测性的核心价值。

---

## 四、给 LLM 调用打上元数据（metadata）与标签（tags）（9 分钟）

只记录输入输出还不够，工程中你还需要**分组、过滤、对比实验**。

```python
from langsmith import traceable

@traceable(
    name="answer",
    tags=["v2-prompt", "gpt-4o"],           # 标签：方便按实验版本筛选
    metadata={"user_id": "u_001", "env": "prod"},  # 元数据：业务字段
)
 def answer(question: str) -> str:
    # 这里可以替换成真正的 LLM 调用
    return f"[冒充 LLM] answer to: {question}"

answer("LangSmith 能测什么？")
```

用途举例：
- 按 `tags=["v2-prompt"]` 过滤，看新 Prompt 是否比旧的好；
- 按 `metadata["user_id"]` 找某个用户抱怨的那次运行；
- 按耗时排序，找性能瓶颈。

**关键结论**：`tags` 用于**实验维度**，`metadata` 用于**业务维度**，两者配合才能做可对比的评估（evaluation）。

---

## 五、一次最小可运行的 Agent 观测（10 分钟）

下面把一个"伪 Agent"接上 LangSmith，包含：LLM 节点 → 工具节点 → 汇总节点。

```python
import os
from langsmith import traceable

# 请先 export LANGCHAIN_TRACING_V2=true LANGCHAIN_API_KEY=... LANGCHAIN_PROJECT=demo

@traceable(name="llm_think")
 def llm_think(question: str) -> dict:
    # 假装是 LLM 决定调用哪个工具
    return {"tool": "search", "args": {"q": question}}

@traceable(name="tool_search")
 def tool_search(q: str) -> str:
    return f"搜索结果：关于 {q} 的 3 条摘要"

@traceable(name="agent_root")
 def run_agent(question: str) -> str:
    plan = llm_think(question)
    obs  = tool_search(plan["args"]["q"])
    return f"最终回答（依据：{obs}）"

if __name__ == "__main__":
    print(run_agent("LangSmith 有什么用？"))
```

运行后到 LangSmith 项目页看 `agent_root` 这棵树，你会看到三层节点、每一步输入输出。

**关键结论**：Agent 越好用、链路越长，你就越离不开"看树"的能力——这也是课程 s7u7l3 的起点。

---

## 六、常见误区（先记在心里，练完再看一遍）

- **只把 Key 写在代码里**：会泄露，请用环境变量或密钥管理。
- **只对根函数加 `@traceable`**：树会扁平，看不到内部步骤；要给关键子步骤也加。
- **把 tags 和 metadata 混用**：tags 是列表用于筛选，metadata 是字典用于检索业务字段。
- **忘记设置 `LANGCHAIN_PROJECT`**：所有实验混在一个项目里，无法对比。
- **在循环里加 `@traceable` 却记录太多**：会产生大量 Run，注意采样或加条件。

---

## 七、动手练习（课后 20~30 分钟）

**任务**：实现一个 3 步 Agent 并用 LangSmith 观测它。

1. 注册 LangSmith，拿到 API Key，导出为环境变量（`LANGCHAIN_TRACING_V2=true`、`LANGCHAIN_API_KEY=...`、`LANGCHAIN_PROJECT=hw-obs`）。
2. 用 `@traceable` 实现三个函数：
   - `plan(question)`：返回一个 dict，包含要用的工具名和参数；
   - `use_tool(tool, args)`：根据名字返回一段模拟结果；
   - `final(question)`：串联前两步，返回最终字符串。
3. 给 `final` 加上 `tags=["hw", "v1"]` 和 `metadata={"student": "你的名字"}`。
4. 运行 3 个不同问题，打开 LangSmith UI：
   - 找出耗时最长的节点；
   - 按 `tag=hw` 过滤出你本次的 3 条 Trace；
   - 截图你看到的那棵树的结构，写下你的观察。

**验收标准**：能在 UI 中看到 `final → plan / use_tool` 的嵌套结构，并能按标签筛选。

---

## 八、小结

- LangSmith 解决的是 **Agent 多步执行的"可回看、可对比"问题**；
- 核心模型是 **Trace（树）+ Run/Span（节点）**；
- 接入方式最低只要一个 `@traceable`；
- 工程化靠 **tags + metadata + 多项目分层**。

下一步就进入真正用 LangChain 构建 Agent，再用 LangSmith 全程观测它。

## agent.obs.langfuse

# 用 Langfuse 给 Agent 装上“黑匣子”：从零到工程级

> **一句话直觉**：Agent（智能体）一旦跑起来就像一只会自己改路线的黑盒子，Langfuse 就是它的飞行记录仪——每一步 LLM 调用、每一次工具触发、每一分钱花了多少，都能回放、能溯源、能量化。

---

## 1. 为什么 Agent 需要可观测性（Observability）

普通函数出 bug，看堆栈就行；Agent 出 bug，往往是“答案不对，但程序没报错”。原因在于 Agent 的执行是**多步、带循环、由 LLM 动态决策**的：调用了哪个工具、prompt 长什么样、检索回了什么、模型返回了什么，全是运行时才确定的。

没有观测，你只能靠 `print` 猜；有了 **可观测性（Observability）**，你能把一次运行拆成结构化的 **Trace（追踪）→ Span（跨度）→ Generation（生成）** 三层，逐层查看输入输出、耗时、token 与成本。

> 关键结论：**Agent 的调试问题，80% 是“我看不到中间过程”造成的**，不是模型太笨。

---

## 2. Langfuse 是什么：一个开源的 LLM 追踪平台

**Langfuse** 是一个开源的 LLM 工程平台（LLM Engineering Platform），提供三大能力：

- **Tracing（追踪）**：记录一次完整请求的所有嵌套步骤。
- **Prompt Management（提示词管理）**：把 prompt 当作可版本化的资产，而不是硬编码字符串。
- **Evaluation（评估）**：给 trace 打分、跑数据集回归。

它有两种用法：**Cloud 版**（注册即用）或**自托管**（Docker Compose 一条命令起）。对学习者最友好的是先用 Cloud 免费项目拿一对密钥：`LANGFUSE_PUBLIC_KEY` 和 `LANGFUSE_SECRET_KEY`。

> 关键结论：Langfuse 的 SDK 只负责“上报数据”，你可以把它当成**异步的、非阻塞的日志库**来用，不改变你的业务逻辑。

---

## 3. 最小可用示例：装饰器 5 行接入

安装：

```bash
pip install langfuse openai
```

最省心的方式是 `@observe()` 装饰器：它自动把你函数的入参、返回值、异常包装成一个 span。首次使用务必调用 `langfuse.flush()`，否则进程退出时缓冲区里的数据可能还没发出去。

```python
# 示例代码见字段 example_code
```

这段代码会生成一条 trace，name 是函数名，`generation` 类型的那层会自动带模型名与 token 统计（需配合 OpenAI 集成）。

> 关键结论：**忘了 flush，就等于飞行记录仪没插电**——本地看着正常，平台上一片空白。

---

## 4. 手动构造 Trace：把 Agent 的每一步显式化

装饰器适合快速接入，但 Agent 的典型结构是“主循环 + 若干子步骤”，这时更推荐**手动创建 span**，可以自由命名、挂 metadata、把 tool call 独立出来。核心 API 只有四个：

- `langfuse.trace()`：创建一条顶层追踪。
- `trace.span(name=...)`：创建子步骤。
- `span.generation(model=..., input=..., output=...)`：标记一次 LLM 调用。
- `span.end()` / `trace.update(...)`：收尾并补充最终结果。

这种写法让 trace 的时间轴和你脑中的 Agent 流程图一一对应，排查问题时能直接定位到“第 3 步检索返回了空”。

> 关键结论：**把 Agent 的“思考-行动-观察”循环，逐节点映射为 span，可观测性就变成了可读的时间轴。**

---

## 5. 从 Trace 到评估：让观测数据产生价值

只记录不评估，数据只是垃圾。Langfuse 允许你给 trace 附加 `score`（分数）、`tag`（标签）和 `metadata`：

- **在线打分**：用户点了 👍/👎，就写一条 `trace.score(name="user_feedback", value=1)`。
- **离线评估**：用数据集跑回归，把 `correctness`、`faithfulness` 等指标写到平台上对比版本。

这样你就从“单次调试”进阶到“**版本级质量管控**”：改了 prompt 或换了模型，跑一遍数据集，分数掉没掉一目了然。

> 关键结论：**Trace 解决“这一次为什么错”，Score 解决“这一版是不是变差了”。**

---

## 动手练习

**任务**：写一个最小 Agent，用 Langfuse 记录一次“查天气”的完整调用。

1. 定义一个 `get_weather(city)` 函数，返回假数据（如 `{"city": "北京", "temp": 26}`），用 `@observe()` 装饰。
2. 定义 `agent(query)` 函数：先调用一次 LLM（可用 `openai` 或直接 mock 一个字符串），再根据关键词决定是否调用 `get_weather`，最后返回自然语言答案。整个 `agent` 也要用 `@observe()`。
3. 在 `if __name__ == "__main__":` 里执行一次 `agent("北京今天多少度？")`，并调用 `langfuse.flush()`。
4. 打开 Langfuse 项目的 Traces 页面，确认能看到嵌套的 span 树，并截图。
5. 进阶：用 `trace.score(name="user_feedback", value=1)` 给这次 trace 打一个好评。

**验收标准**：平台上出现一条名为 `agent` 的 trace，内部含 `get_weather` 子 span，且能看到你写入的 score。

## agent.obs.opentelemetry

## 一句话直觉

**OpenTelemetry（开放遥测，常缩写为 OTel）** 就像给 AI Agent（智能体）装上的“飞行数据记录仪”：它统一采集 **Trace（链路）**、**Metrics（指标）**、**Logs（日志）**，让你在复杂调用链中一眼看出“谁慢、谁错、谁贵”。

---

## 1. 为什么 AI Agent 需要 OpenTelemetry？

AI Agent 通常由 **LLM（大语言模型）调用**、**工具调用（Tool Calling）**、**检索（Retrieval）**、**记忆（Memory）** 等多步组成，一次用户请求可能跨 5~20 个内部步骤。没有可观测性（Observability），你只能看到“最终答案错了”，却不知道是：

- 检索召回错了？
- LLM 超时了？
- 工具参数传错了？
- 重试导致成本飙升？

OpenTelemetry 提供 **厂商中立（vendor-neutral）** 的标准：一次埋点，可导出到 Jaeger、Tempo、Datadog、Langfuse 等任意后端。

```python
# 直觉示例：没有 OTel 时，你只能靠 print 猜问题
# 有了 OTel，每一步都是一个带属性的 Span（跨度）
print("开始检索...")
print("开始调用 LLM...")
print("调用工具 weather...")
# 问题：无法知道每步耗时、父子关系、错误原因
```

---

## 2. 三个核心概念：Trace / Span / Attribute

- **Trace（链路）**：一次完整请求的全局 ID，比如一次用户提问。
- **Span（跨度）**：链路中的一个操作单元，有开始/结束时间、状态、父子关系。
- **Attribute（属性）**：Span 上的键值对，比如 `gen_ai.model="gpt-4o"`、`tool.name="weather"`。
- **Context Propagation（上下文传播）**：让子 Span 自动挂到父 Span 下，跨函数、跨服务传递。

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

# 1. 初始化 TracerProvider（追踪提供者）
provider = TracerProvider()
provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
trace.set_tracer_provider(provider)

tracer = trace.get_tracer("agent.demo")

# 2. 创建父子 Span
with tracer.start_as_current_span("user_request") as root:
    root.set_attribute("user.id", "u_001")
    with tracer.start_as_current_span("retrieve") as child:
        child.set_attribute("retriever.top_k", 5)
    with tracer.start_as_current_span("llm_call") as child:
        child.set_attribute("gen_ai.model", "gpt-4o")
        child.set_attribute("gen_ai.usage.input_tokens", 128)
# 输出：两条子 Span 自动挂在 root 下
```

---

## 3. 初始化 SDK：让 Span 真正被导出

默认 API 是“空实现”，必须配置 **SDK（软件开发工具包）** 和 **Exporter（导出器）**。生产常用 **OTLP（OpenTelemetry Protocol）** 导出到 Collector（收集器）。

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource

# 用 Resource 描述服务身份
resource = Resource.create({
    "service.name": "my-agent",
    "service.version": "0.1.0",
    "deployment.environment": "dev",
})

provider = TracerProvider(resource=resource)
# Batch 批量导出，性能优于 Simple
provider.add_span_processor(
    BatchSpanProcessor(OTLPSpanExporter(endpoint="http://localhost:4317", insecure=True))
)
trace.set_tracer_provider(provider)

# 本地调试可换成 ConsoleSpanExporter
```

---

## 4. 语义约定（Semantic Conventions）：AI Agent 的统一字段

OTel 定义了 **GenAI Semantic Conventions（生成式 AI 语义约定）**，比如：

| 字段 | 含义 |
|---|---|
| `gen_ai.system` | 供应商，如 `openai` |
| `gen_ai.request.model` | 请求模型 |
| `gen_ai.usage.input_tokens` | 输入 token 数 |
| `gen_ai.usage.output_tokens` | 输出 token 数 |
| `gen_ai.operation.name` | 操作名，如 `chat` |

统一字段后，不同 Agent 的 Trace 可以在同一看板里聚合分析成本与延迟。

```python
with tracer.start_as_current_span("chat") as span:
    span.set_attribute("gen_ai.system", "openai")
    span.set_attribute("gen_ai.request.model", "gpt-4o")
    span.set_attribute("gen_ai.operation.name", "chat")
    # 业务结束后回填 token 使用量
    span.set_attribute("gen_ai.usage.input_tokens", 512)
    span.set_attribute("gen_ai.usage.output_tokens", 128)
```

---

## 5. 在 Agent 里做装饰器埋点：一行包裹工具调用

工程上不想在每个函数手写 `start_as_current_span`，可用装饰器或自动埋点库（如 `opentelemetry-instrumentation-*`）。

```python
import functools
from opentelemetry import trace

tracer = trace.get_tracer("agent.tools")

def traced(name: str):
    """把任意函数包装成一个 Span 的装饰器"""
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            with tracer.start_as_current_span(name) as span:
                try:
                    result = fn(*args, **kwargs)
                    span.set_status(trace.Status(trace.StatusCode.OK))
                    return result
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                    raise
        return wrapper
    return deco

@traced("tool.weather")
def get_weather(city: str) -> str:
    return f"{city}: sunny"

print(get_weather("Beijing"))
```

---

## 6. 完整最小闭环：本地 Collector + Jaeger

1. `pip install opentelemetry-sdk opentelemetry-exporter-otlp`
2. `docker run -d -p 16686:16686 -p 4317:4317 jaegertracing/all-in-one`
3. 用上面第 3 节代码导出到 `localhost:4317`
4. 打开 `http://localhost:16686` 搜索 `my-agent` 服务即可看到链路。

这是从零到工程级最短路径：**API → SDK → Exporter → Collector → UI**。


---

## 本课题目

### single_choice · None



- [A] 开启 LangSmith 的追踪功能，将运行轨迹上传到 LangSmith 平台
- [B] 指定 LangSmith 的 API 密钥，用于身份验证
- [C] 设置 LangChain 的日志级别为详细模式
- [D] 指定 LangSmith 项目的名称，用于分组追踪记录

**参考答案**：0

**解析**：LANGCHAIN_TRACING_V2 是开启 LangSmith 追踪的开关；API 密钥由 LANGCHAIN_API_KEY 指定，项目名由 LANGCHAIN_PROJECT 指定，日志级别则由 LangChain 自身的日志配置控制。

### single_choice · None



- [A] LANGCHAIN_TRACING_V2
- [B] LANGCHAIN_API_KEY
- [C] LANGCHAIN_PROJECT
- [D] LANGCHAIN_ENDPOINT

**参考答案**：2

**解析**：LANGCHAIN_PROJECT 用于指定追踪记录归属的项目名称。LANGCHAIN_TRACING_V2 是追踪开关，LANGCHAIN_API_KEY 是密钥，LANGCHAIN_ENDPOINT 用于设置服务地址。

### single_choice · None



- [A] 一个 run 可以同时属于多个 project
- [B] 一个 project 下可以包含多个 run，用于把相关追踪组织在一起
- [C] 一个 project 只能包含一个 run
- [D] project 与 run 之间没有关联，只是命名相似

**参考答案**：1

**解析**：LangSmith 的 project 是 run 的集合容器，一个 project 下可以有多个 run；每个 run 归属于一个 project，而不是多个，也不是一对一。

### single_choice · None



- [A] 在运行前通过环境变量开启追踪并配置好密钥和项目
- [B] 在 agent 的每个函数里手写 HTTP 请求上传日志
- [C] 把 agent 依赖的每个库都替换成自己实现
- [D] 只能通过重写 agent 框架源码来实现

**参考答案**：0

**解析**：LangSmith 与 LangChain 集成后，可以通过环境变量开启追踪并配置密钥、项目名，无需改动业务代码；手写上传、替换依赖或改框架源码都不是必要做法。

### single_choice · None



- [A] LangSmith 是 LangChain 的替代品，二者不能同时使用
- [B] LangSmith 是用于追踪和评估 LLM 应用（含 LangChain 应用）的平台，二者可配合使用
- [C] LangSmith 只能追踪非 LangChain 框架的应用
- [D] LangSmith 是 LangChain 内部的一个字符串处理函数

**参考答案**：1

**解析**：LangSmith 是面向 LLM 应用的追踪与评估平台，可以与 LangChain 应用配合使用，也支持其他框架或自研代码；它不替代 LangChain，也不只是一个字符串函数。

### single_choice · None



- [A] run 的状态字段（如 error）
- [B] run 的创建时间戳的小数部分
- [C] run 的父 run 的名称长度
- [D] run 所属 project 名称的首字母

**参考答案**：0

**解析**：LangSmith 的 run 记录了执行状态，失败时会标记为错误状态，便于筛选；时间戳小数、父 run 名称长度、项目名首字母都不携带错误信息。

### single_choice · None



- [A] 该次 LLM 调用从发起到返回所花费的时间
- [B] 该次调用消耗的 token 总数
- [C] 该次调用使用的模型名称
- [D] 该次调用所属项目的名称

**参考答案**：0

**解析**：latency 表示该次 run 的耗时，即从发起到返回的时间；token 数、模型名、项目名分别是其他字段，不由 latency 反映。

### single_choice · None



- [A] 查看该 run 的输入消息内容，确认提示词或上下文是否过长
- [B] 直接删除该项目下所有追踪记录
- [C] 把 LANGCHAIN_TRACING_V2 设为 false 后重跑
- [D] 修改 run 的 latency 字段使其变小

**参考答案**：0

**解析**：token 用量高通常与输入上下文或提示词过长有关，查看 run 的输入消息内容可以定位；删除记录、关闭追踪或改延迟字段都无法帮助分析 token 用量的来源。

### single_choice · None



- [A] 判断新版本在代表性样本上是否比旧版本表现更好
- [B] 自动合并两个版本的代码到一个分支
- [C] 确保两个版本使用完全相同的随机种子，否则评估无效
- [D] 把旧版本的追踪记录删除以节省空间

**参考答案**：0

**解析**：在相同 dataset 上运行两个版本并比较评估分数，可以判断新版本是否更优；这不是自动合并代码，随机种子一致不是评估有效的前提，也不需要删除旧追踪记录。

### single_choice · None



- [A] 追踪需要序列化并上传运行数据，会带来额外的网络与处理开销
- [B] 开启追踪会把 Python 解释器切换到调试模式，导致所有代码变慢数倍
- [C] 开启追踪会让 LLM 的推理速度下降，因为模型需要生成更多 token
- [D] 开启追踪会禁用操作系统的缓存机制

**参考答案**：0

**解析**：追踪机制需要采集、序列化并上传 run 数据，确实可能引入一定的额外开销；但它不会切换解释器调试模式、不会让模型多生成 token，也不会禁用系统缓存。

### single_choice · None



- [A] inputs 表示该 run 的输入，outputs 表示该 run 产生的结果
- [B] inputs 表示该 run 所属项目，outputs 表示该 run 的标签
- [C] inputs 表示该 run 的依赖版本，outputs 表示该 run 的耗时
- [D] inputs 表示该 run 的错误信息，outputs 表示该 run 的创建时间

**参考答案**：0

**解析**：inputs/outputs 分别记录该 run 的输入与输出内容；依赖版本、耗时、错误信息、创建时间、标签等是 run 上的其他字段，不应与 inputs/outputs 混淆。

### single_choice · None



- [A] 排查一个多步 agent 在某一步工具调用后回答偏离预期的问题
- [B] 训练一个新的基础大语言模型
- [C] 对 Python 代码做静态类型检查
- [D] 压缩本地磁盘上的日志文件

**参考答案**：0

**解析**：LangSmith 追踪适合观察 LLM 应用的执行链路，定位某一步输入输出异常等问题；它不用于训练基础模型、静态类型检查或磁盘日志压缩。

### single_choice · None



- [A] 追踪请求因缺少认证而无法上传到 LangSmith 平台
- [B] agent 代码会抛出语法错误，无法运行
- [C] LangSmith 会自动使用匿名模式记录，无需密钥
- [D] 追踪会被静默关闭，但 agent 仍能正常运行

**参考答案**：0

**解析**：LangSmith 上传追踪数据需要 API 密钥进行认证；缺少密钥时追踪无法上传，但 agent 本身通常仍可运行，因此不是语法错误，也不是自动匿名，也不等同于静默关闭追踪开关。

### single_choice · None



- [A] 在 LangSmith 界面中按标签筛选 run，以聚焦特定类型或来源的运行
- [B] 让 LLM 根据标签自动改写 run 的输入
- [C] 把标签作为 API Key 使用
- [D] 让标签替代 run 的 outputs 字段

**参考答案**：0

**解析**：标签主要用于筛选和分组 run，方便聚焦分析；标签不会改写 run 输入、不能作为 API Key，也不会替代 outputs 字段。

### single_choice · None



- [A] 追踪数据中可能包含的用户敏感信息，以及相应的脱敏或屏蔽策略
- [B] LangSmith 平台界面的字体大小
- [C] run 标签是否按字母顺序排列
- [D] 项目名称是否包含连字符

**参考答案**：0

**解析**：追踪会把输入输出等数据上传到平台，生产环境中需要关注敏感信息的脱敏或屏蔽；字体、标签排序、项目名格式与隐私无关。

### single_choice · None



- [A] 一个 Python 模块文件
- [B] 一次 run（例如一次 LLM 调用、一次工具调用或一次链的调用）
- [C] 一个环境变量
- [D] 一个 LangChain 依赖包的版本

**参考答案**：1

**解析**：LangSmith 的追踪树由 run 组成，每个 run 对应一次可追踪的操作，如 LLM 调用、工具调用、链调用等；它不表示模块文件、环境变量或依赖版本。

### single_choice · None



- [A] 所有 run 都是平级的，不存在父子关系
- [B] 父 run 表示更高层的操作，子 run 表示其内部调用的更细粒度操作
- [C] 只有 LLM 调用才能作为父 run，工具调用只能作为子 run
- [D] 父子关系由 run 的执行时间长短决定，与调用嵌套无关

**参考答案**：1

**解析**：LangSmith 用嵌套的 run 表示调用层级：父 run 对应外层操作，子 run 对应其内部发起的更细粒度调用；父子关系由调用嵌套决定，而非执行时间或 run 类型。

### single_choice · None



- [A] 查看对应工具调用 run 的输入与输出，并与 LLM run 的输出进行对比
- [B] 直接修改 agent 的提示词并重新运行，不查看追踪
- [C] 关闭追踪以减少干扰，只观察最终答案
- [D] 把 temperature 调成 0 后重新运行，不查看历史记录

**参考答案**：0

**解析**：LangSmith 追踪中工具调用 run 会记录传给工具的输入和工具返回的输出，结合 LLM run 的输出可以判断参数是模型生成错误还是工具执行错误；不查看追踪或关闭追踪无法定位问题环节。

### single_choice · None



- [A] 提高 LLM 的推理速度
- [B] 对 run 进行分类和筛选，便于按标签检索与聚合分析
- [C] 为 run 自动生成单元测试
- [D] 加密 run 中的敏感数据

**参考答案**：1

**解析**：tags 是附加在 run 上的标签元数据，用于分类、过滤和聚合分析；它不改变模型推理速度，不生成测试，也不用于加密数据。

### single_choice · None



- [A] 修改 LANGCHAIN_PROJECT 为用户的 ID
- [B] 在 run 的 metadata 中记录用户或会话标识
- [C] 为每个用户单独安装一份 LangSmith
- [D] 把用户 ID 拼接到 API Key 后面

**参考答案**：1

**解析**：LangSmith 支持在 run 上附加 metadata 来记录业务上下文字段，如用户 ID、会话 ID 等；修改项目名、重复安装或拼接 API Key 都不是正确做法。

### single_choice · None



- [A] 存储模型权重文件
- [B] 保存一组带输入（及可选期望输出）的样本，用于批量运行和评估
- [C] 代替向量数据库进行检索
- [D] 缓存 LLM 的响应以节省费用

**参考答案**：1

**解析**：LangSmith 的 dataset 是一组用于评估的样本集合，包含输入和可选的参考输出，可以在其上批量运行目标系统并进行打分；它不存储模型权重、不做检索、也不是响应缓存。

### single_choice · None



- [A] 定义如何把 agent 的输出与参考结果进行比较并给出分数
- [B] 负责启动 agent 进程并分配 CPU
- [C] 自动修复 agent 中被判为错误的回答
- [D] 把 agent 的代码部署到生产环境

**参考答案**：0

**解析**：evaluator 定义评估逻辑，负责比较输出与参考结果并产出分数或标签；它不负责进程调度、自动修复回答，也不负责部署。

### single_choice · None



- [A] 一个 trace 只能包含一个 span，多了会报错
- [B] trace 是一次完整请求的顶层容器，span 是其中某个具体步骤的嵌套记录
- [C] span 必须在 trace 之前创建，否则数据丢失
- [D] trace 与 span 是同义词，可互换使用

**参考答案**：1

**解析**：Langfuse 的数据模型中，trace 代表一次端到端请求/会话的顶层容器，span（observation）表示其中某个具体步骤（如检索、LLM 调用），可以多层嵌套。因此 B 正确。A、C、D 都是常见误解。

### single_choice · None



- [A] 把回答文本写入一个本地日志文件即可，Langfuse 会自动读取
- [B] 在创建该 observation 时把回答文本作为 output 字段传入，并结束该 observation
- [C] 把回答文本拼接到 trace 的 name 字段里
- [D] 回答文本无需保存，Langfuse 只记录耗时

**参考答案**：1

**解析**：Langfuse 的 observation 支持 input/output 字段，用于保存该步骤的输入和输出（如生成的回答）。应把回答作为 output 传入并在结束时提交。A、C、D 都偏离了数据模型。

### multi_choice · None



- [A] 使用异步上报，避免阻塞业务逻辑
- [B] 启用批量发送，减少网络往返次数
- [C] 在网络异常时对上报做容错/丢弃，避免拖垮主流程
- [D] 在每次 LLM 调用前同步等待上报完成再继续

**参考答案**：[0, 1, 2]

**解析**：异步、批量、容错都能降低追踪对主流程的干扰。D 反而把追踪放在关键路径上做同步等待，增加延迟。

### multi_choice · None



- [A] 为每个关键步骤创建可识别的 observation，名称能体现步骤含义
- [B] 在同一 trace 内保留步骤间的父子关系
- [C] 把整个 Agent 的完整运行压缩成一条无子节点的 trace 以省事
- [D] 为能区分同一次请求的步骤提供一致的 trace 关联

**参考答案**：[0, 1, 3]

**解析**：清晰命名、保留父子关系、维持 trace 关联，是良好追踪结构的基础。C 放弃层级会导致难以定位问题。

### fill_blank · None



**参考答案**：["trace", "追踪", "trace（追踪）"]

**解析**：trace 是顶层容器，observation/span 是其中的步骤记录。此空考察二者层级关系的命名。

### fill_blank · None



**参考答案**：["score", "评分", "score（评分）"]

**解析**：score 用于量化质量，可来自人工或自动评估，并附加到 trace 或 observation 上。

### code_reading · None



**参考答案**：retrieve 和 generate 都是该 trace 下的子 observation（span），与 trace 构成父子层级，可展开查看各自的 input/output。

**解析**：代码通过 trace 启动并结束两个 span，二者都归属于同一顶层 trace，因此呈现为父子嵌套结构，而非彼此独立。

### code_reading · None



**参考答案**：记录了用户标识（user_id）、自定义元数据（metadata，如模型名）以及该 trace 的输出（output）。

**解析**：user_id 用于按用户关联，metadata 保存上下文信息，output 保存结果。三者都是 trace 上的可查询字段。

### code_reading · None



**参考答案**：它创建了一条 trace，并给该 trace 附加了一个名为 quality、值为 0.8 的 score，同时带有评语注释。

**解析**：score 可附加到 trace 上用于质量评估，包含 name、value 与可选 comment，便于后续筛选与统计。

### scenario · None



**解析**：应把每次请求作为一条 trace，检索与生成分别作为其下的子 observation，并记录各自的 input 与 output。排查时对比检索 span 的 output（拿到的资料）与生成 span 的 input/output，即可判断问题出现在检索还是生成。关键词覆盖 trace/span/observation/input/output/嵌套。

### scenario · None



**解析**：把人工反馈与自动评估都写成 score 附加到对应 trace 上，用 score 的 name/label 区分来源（如 human_feedback、auto_eval），从而既能统计又有区分。关键词覆盖 score/trace/来源/人工/自动/name 或 label。

### scenario · None



**解析**：可采用异步上报、批量发送，将追踪放在后台线程/队列，避免阻塞主流程；同时为上报增加容错与丢弃策略，防止网络问题拖垮业务。这些做法仍保留 trace/span 数据，只是不占用关键路径。关键词覆盖异步/批量/非阻塞/容错。

### single_choice · None



- [A] 为每个环境使用不同的 Langfuse 项目/密钥，或给 trace 打上环境标签
- [B] 只在生产环境启用 Langfuse，开发环境禁用
- [C] 用不同的 trace name 前缀随意区分，没有其它机制
- [D] 在每条 trace 的 output 里写一句“这是生产环境”

**参考答案**：0

**解析**：Langfuse 支持通过项目、密钥及 trace 标签（tags）来隔离与筛选不同环境的数据。A 是最规范的做法。B 会丢失开发数据；C 不够规范；D 把元信息塞进 output 不合理。

### single_choice · None



- [A] score 只能由人工在 UI 上打分，无法通过 API 写入
- [B] score 可以附加到 trace 或某个 observation 上，用于量化质量（如人工评分、自动评估结果）
- [C] score 就是 trace 的耗时字段
- [D] 一旦给 trace 打分，就不能再修改该 trace

**参考答案**：1

**解析**：Langfuse 的 score 是可以附加到 trace 或 observation 的质量指标，既支持人工评分也可通过 SDK/API 写入自动评估结果。A、C、D 均不正确。

### single_choice · None



- [A] 为每次工具调用创建一个嵌套的 observation（span），归属于外层 trace
- [B] 把所有步骤合并成一条 trace，不创建任何子 observation
- [C] 为每个步骤创建一个独立的 trace，互不关联
- [D] 只在最终回答时创建一条 trace

**参考答案**：0

**解析**：要体现层级结构，应在顶层 trace 下为每个步骤创建嵌套 observation，这样在 UI 中能展开查看调用链。B 丢失结构，C 割裂了关联，D 缺少过程信息。

### single_choice · None



- [A] Langfuse 只能在线实时上报，无法批量异步发送
- [B] Langfuse SDK 通常支持同步与异步上报，异步上报可减少对主流程的阻塞
- [C] 上报必须先手动序列化成 CSV 再上传
- [D] Langfuse 不支持批量导入历史数据

**参考答案**：1

**解析**：Langfuse 的 SDK 支持同步/异步等多种上报方式，异步与批处理可降低对主流程的延迟影响。A、C、D 均为错误描述。

### single_choice · None



- [A] 一条顶层 trace，下面包含检索 span 和生成 span 两个子 observation
- [B] 一条 trace 只放检索，另一条无关的 trace 只放生成
- [C] 把检索和生成结果写进同一条 trace 的 name
- [D] 不创建 trace，只记录最终答案

**参考答案**：0

**解析**：RAG 是一次完整请求，适合用一条顶层 trace 承载，检索与生成作为其下的子 observation。这样能清晰呈现各阶段耗时与输入输出。

### single_choice · None



- [A] 把每个用户的明文密码作为 user id 记录，便于排查
- [B] 记录一个稳定的匿名用户标识（如内部 ID），便于按用户筛选会话
- [C] user id 必须是真实姓名，否则数据无效
- [D] Langfuse 不支持按用户筛选 trace

**参考答案**：1

**解析**：user id 用于把同一次会话或同一用户的多条 trace 关联起来，应使用稳定的匿名标识以兼顾可用性与隐私。A 会导致敏感信息泄露；C、D 不成立。

### multi_choice · None



- [A] 调用的模型名称与版本
- [B] 本次请求的业务场景或功能模块名
- [C] 用户的登录密码
- [D] 会话/请求的关联标识（如 session id）

**参考答案**：[0, 1, 3]

**解析**：模型名、业务模块、session id 都属于有助于分析与筛选的上下文元数据。用户密码属于敏感凭证，绝不能写入追踪数据。

### multi_choice · None



- [A] 人工在评估界面标注
- [B] 用另一个 LLM 做自动评估后写入
- [C] 基于规则的自动检查（如格式校验）写入
- [D] 根据用户是否点击按钮直接推断，无需任何写入

**参考答案**：[0, 1, 2]

**解析**：分数可来自人工标注、LLM 自动评估、规则评估等。D 的问题在于“无需任何写入”——若不把结果写入 Langfuse，就不会形成可查询的 score。

### single_choice · None



- [A] Exporter
- [B] Provider（如 TracerProvider）
- [C] SpanProcessor
- [D] Resource

**参考答案**：1

**解析**：Provider 是 OpenTelemetry API 的入口，TracerProvider 负责创建 Tracer，MeterProvider 创建 Meter，LoggerProvider 创建 Logger。Exporter 只负责导出数据，SpanProcessor 处理 Span 生命周期，Resource 描述实体属性。

### single_choice · None



- [A] 相同的 trace_id
- [B] 父 Span 的 span_id 作为子 Span 的 parent_span_id，且共享同一 trace_id
- [C] 相同的 span_name
- [D] 相同的 Resource 属性

**参考答案**：1

**解析**：同一 Trace 内的所有 Span 共享 trace_id，子 Span 通过 parent_span_id 指向父 Span 来确立层级关系。仅 trace_id 相同只能说明属于同一 Trace，不能确定父子顺序。

### single_choice · None



- [A] 存储跨进程传递的键值对，通常用于跨服务的上下文属性，而不作为 Span 属性自动导出
- [B] 替代 trace_id
- [C] 保存采样率
- [D] 记录异常堆栈

**参考答案**：0

**解析**：Baggage 用于在请求链路中跨进程携带键值对信息。它不会自动成为 Span 属性；如需观察，需要显式写入 Span 属性或作为指标。

### single_choice · None



- [A] 两者完全等价，调用任一即可
- [B] record_exception 记录异常事件，set_status 更新 Span 的状态码；通常可同时使用
- [C] set_status 会自动记录异常对象
- [D] record_exception 会强制将 Span 设为 OK

**参考答案**：1

**解析**：record_exception 会把异常作为事件附加到 Span 上；set_status 则是更新 Span 的状态（如 ERROR + 描述）。通常两者一起调用以表达错误。

### single_choice · None



- [A] import py.env.install as otel
- [B] from opentelemetry import trace
- [C] import opentelemetry.agent.obs.opentelemetry
- [D] from otel import trace

**参考答案**：1

**解析**：opentelemetry 是真实存在的 Python 包，常用 `from opentelemetry import trace`。其他选项均非真实模块路径。

### multi_choice · None



- [A] Traces
- [B] Metrics
- [C] Logs
- [D] Screenshots

**参考答案**：[0, 1, 2]

**解析**：OpenTelemetry 的重点是 traces、metrics、logs 三类信号（有时还包括 baggage、profiles 等扩展）。Screenshots 不属于遥测信号。

### multi_choice · None



- [A] W3C TraceContext
- [B] W3C Baggage
- [C] B3（Zipkin 风格）
- [D] OTLP-JSON-Span

**参考答案**：[0, 1, 2]

**解析**：常见的传播格式包括 W3C TraceContext、W3C Baggage、B3、Jaeger 等。OTLP-JSON-Span 并非传播格式，OTLP 是导出协议。

### multi_choice · None



- [A] 在 Metric 属性中避免使用用户 ID、请求 ID 等唯一值
- [B] 对 Span Name 使用稳定的模板化命名，如 “GET /users/{id}”
- [C] 对所有 Span 都记录原始 URL 带查询字符串
- [D] 使用 view 或聚合对 Metric 属性做限制

**参考答案**：[0, 1, 3]

**解析**：高基数常见来源是把唯一值放进 Metric 属性，或把带 ID 的 URL 直接作为 Span Name。模板化命名、限制属性、使用 view 都能缓解。记录带查询串的原始 URL 会加剧基数问题。

### multi_choice · None



- [A] TracerProvider
- [B] BatchSpanProcessor
- [C] OTLPSpanExporter
- [D] py.env.install

**参考答案**：[0, 1, 2]

**解析**：TracerProvider、BatchSpanProcessor、OTLPSpanExporter 都是 opentelemetry-sdk / opentelemetry-exporter-otlp 中真实存在的类。py.env.install 是教学系统内部编号，不是 API。

### fill_blank · None



**参考答案**：["Resource", "resource", "OTel Resource", "OpenTelemetry Resource"]

**解析**：Resource 描述产生遥测数据的实体及其属性。service.name 是其中最重要的属性之一，会被附加到导出的 traces/metrics/logs 上。

### code_reading · None



**参考答案**：输出两个 Span，名称分别为 parent 和 child；child 的 parent_span_id 指向 parent 的 span_id，两者共享同一个 trace_id。

**解析**：start_as_current_span 会把新 Span 设为当前上下文，嵌套调用会以当前 Span 作为父级。SimpleSpanProcessor 会将每个结束的 Span 立即导出到 ConsoleSpanExporter。

### scenario · None



**解析**：Trace 数量暴增往往与采样策略（如 AlwaysOn）有关，应改为 ParentBased + TraceIdRatioBased 或经由 Collector 采样；链路不完整通常是因为跨服务未正确传播上下文，需要配置 W3C TraceContext 之类的 propagator，并在 HTTP 客户端/服务端正确 inject/extract traceparent。

### single_choice · None



- [A] Context 会自动跨线程和跨进程传递，无需任何处理
- [B] Context 用于在进程内传递当前 Span 等信息，跨进程需借助 W3C TraceContext 等传播格式
- [C] Context 只能在同一函数内使用
- [D] Context 直接等同于 trace_id

**参考答案**：1

**解析**：Context 是进程内的传播载体，保存当前活跃的 Span 等。跨进程/跨网络需要 Inject/Extract 配合 W3C TraceContext（traceparent/tracestate）等标准格式。Context 不会自动跨线程传递。

### single_choice · None



- [A] 一种 JSON 日志格式
- [B] OpenTelemetry Protocol，用于在 SDK 与 Collector/后端之间传输遥测数据
- [C] 一种采样算法
- [D] Python 的标准日志模块

**参考答案**：1

**解析**：OTLP 是 OpenTelemetry 定义的标准传输协议，支持 gRPC 与 HTTP，用于导出 traces/metrics/logs。它不是日志格式、采样算法，也不是 Python 模块。

### single_choice · None



- [A] Counter 只能增加，UpDownCounter 可以增加也可减少
- [B] Counter 记录时间，UpDownCounter 记录数值
- [C] Counter 是同步的，UpDownCounter 只能是异步的
- [D] 两者完全等价，只是命名不同

**参考答案**：0

**解析**：Counter 是单调递增的累计量（如请求数），UpDownCounter 支持正负增减（如队列长度变化）。两者都可同步或异步使用。

### single_choice · None



- [A] 它定义单个 Span 的耗时
- [B] 它描述产生遥测数据的实体（如 service.name、host.name 等属性）
- [C] 它是导出数据的网络协议
- [D] 它用于设置采样率

**参考答案**：1

**解析**：Resource 表示产生遥测数据的实体身份信息，典型属性包括 service.name、service.version、host.name 等，会在导出的数据中附加。耗时为 Span 的属性，协议为 OTLP，采样由 Sampler 决定。

### single_choice · None



- [A] 它保证每次写入都同步落盘
- [B] 它批量异步导出 Span，减少网络开销，适合生产环境
- [C] 它自动为每个 Span 生成 trace_id
- [D] 它会把 Span 转换成日志

**参考答案**：1

**解析**：BatchSpanProcessor 异步批量导出，能显著降低导出开销，适用于生产。SimpleSpanProcessor 每个 Span 都同步导出，通常只用于调试或测试。

### single_choice · None



- [A] http.method
- [B] http.status_code
- [C] http.url
- [D] net.peer.name

**参考答案**：1

**解析**：根据语义约定，HTTP 状态码记录在 http.status_code（注意在新版语义约定中可能演进为 http.response.status_code）。http.method 记录方法，http.url 记录 URL，net.peer.name 记录对端名称。

### single_choice · None



- [A] 它是 Python 的必装依赖库
- [B] 它是一个独立进程/服务，可接收、处理并导出多种格式的遥测数据
- [C] 它只能处理 logs
- [D] 它替代了所有的 SDK

**参考答案**：1

**解析**：Collector 是独立的中间层服务，通过 receiver/processor/exporter 管线处理 traces、metrics、logs。它不是 Python 依赖库，也不替代 SDK。

### single_choice · None



- [A] 是否记录 Span 的属性
- [B] 是否导出某个 Trace 或其部分 Span
- [C] Span 的命名规则
- [D] 网络的传输协议

**参考答案**：1

**解析**：Sampler 决定某条 Trace（或某个 Span）是否被记录/导出。常见的 ParentBased、TraceIdRatioBased、AlwaysOn/AlwaysOff。采样不影响属性内容、命名或协议。
