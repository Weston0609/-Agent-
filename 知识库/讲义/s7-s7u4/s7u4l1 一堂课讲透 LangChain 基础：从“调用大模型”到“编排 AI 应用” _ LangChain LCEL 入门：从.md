# s7u4l1 一堂课讲透 LangChain 基础：从“调用大模型”到“编排 AI 应用” / LangChain LCEL 入门：从零到工程级

> 来源 `content/lessons/s7u4l1.json`

## agent.fw.langchain_basic

# 一堂课讲透 LangChain 基础：从“调用大模型”到“编排 AI 应用”

> **一句话直觉：** 如果大语言模型（Large Language Model, LLM）是一台强大的发动机，那么 **LangChain** 就是给 AI 应用装上传动轴、仪表盘和方向盘的整套底盘——它让你不必从零造轮子，就能把模型、提示词（Prompt）、外部数据、工具和记忆串成可运行、可扩展、可维护的工程系统。

---

## 1. 为什么需要 LangChain：从单次调用到复杂应用

**核心结论：** 单独调用大模型只能完成“输入文本 → 输出文本”的一次性任务；真实 AI 应用需要多步骤推理、外部知识检索、工具调用、对话记忆和流程控制，LangChain 提供了这些能力的标准抽象。

你可以把 LangChain 理解为一套 **LLM 应用开发框架（Framework）**。它的核心价值不是“帮你调用模型”，而是“帮你组织复杂 LLM 工作流（Workflow）”。

最基础的调用长这样：

```python
# 示例：不依赖 LangChain，直接调用 OpenAI SDK
from openai import OpenAI

client = OpenAI(api_key="你的 API Key")
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "用一句话解释什么是 LangChain"}],
)
print(response.choices[0].message.content)
```

这段代码能跑，但当你需要：换模型、加提示词模板、接知识库、保留历史、调用工具、做链式组合时，代码会迅速膨胀。LangChain 的目标就是把这些问题标准化。

---

## 2. LangChain 的核心抽象：模型、提示词、输出解析器

**核心结论：** LangChain 用 **ChatModel**、**PromptTemplate**、**OutputParser** 三个抽象，把“模型调用”拆成可组合、可替换、可测试的组件。

### 2.1 模型（Model）

LangChain 中常见的模型接口包括：

- **LLM**：输入字符串，输出字符串，偏旧式补全模型。
- **ChatModel**：输入消息列表，输出消息对象，当前主流。
- **Embeddings**：把文本转成向量，用于检索和相似度计算。

```python
# 示例：使用 LangChain 的 ChatModel
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="gpt-4o-mini",
    api_key="你的 API Key",  # 实际项目建议用环境变量
    temperature=0.7,
)

response = llm.invoke("用一句话解释什么是 LangChain")
print(type(response))
print(response.content)
```

### 2.2 提示词模板（Prompt Template）

**核心结论：** 提示词模板把“固定指令”和“动态变量”分离，避免字符串拼接带来的混乱。

```python
# 示例：PromptTemplate 与 ChatPromptTemplate
from langchain_core.prompts import ChatPromptTemplate

prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一位资深 Python 与 AI 架构师导师。"),
    ("human", "请用一句话解释 {concept}。"),
])

messages = prompt.invoke({"concept": "LangChain"})
print(messages)
```

### 2.3 输出解析器（Output Parser）

**核心结论：** 模型输出是非结构化文本，输出解析器把它转成程序可用的结构化数据，例如 JSON、列表或 Pydantic 对象。

```python
# 示例：把模型输出解析成结构化 JSON
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

parser = JsonOutputParser()
prompt = ChatPromptTemplate.from_template(
    "请返回 JSON，包含字段 name 和 purpose，解释 {concept}。\n{format_instruction}"
).partial(format_instruction=parser.get_format_instructions())

llm = ChatOpenAI(model="gpt-4o-mini", api_key="你的 API Key")
chain = prompt | llm | parser

result = chain.invoke({"concept": "LangChain"})
print(result)
```

---

## 3. 链（Chain）与 LCEL：把组件串起来

**核心结论：** LangChain 表达式语言（LangChain Expression Language, LCEL）用管道符 `|` 把提示词、模型、解析器组合成链（Chain），实现声明式编排。

LCEL 的关键优势是：统一接口、支持流式输出、支持异步、支持批处理、便于调试。

```python
# 示例：用 LCEL 构建最小链
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

prompt = ChatPromptTemplate.from_template("请用一句话解释 {topic}")
llm = ChatOpenAI(model="gpt-4o-mini", api_key="你的 API Key")
parser = StrOutputParser()

chain = prompt | llm | parser

# 单次调用
print(chain.invoke({"topic": "什么是 LCEL"}))

# 批量调用
print(chain.batch([{"topic": "LangChain"}, {"topic": "RAG"}]))
```

链的本质是 **Runnable**：任何实现了 `invoke`、`batch`、`stream`、`ainvoke` 等方法的对象都可以接入 LCEL。

---

## 4. 记忆、工具与检索：让应用具备上下文与行动能力

**核心结论：** LangChain 通过 **Memory**、**Tool**、**Retriever** 等组件，让 LLM 应用从“无状态问答”升级为“有记忆、能查资料、会调用工具”的智能体（Agent）基础形态。

### 4.1 记忆（Memory）

在 LangChain 新版本中，对话历史通常通过 **RunnableWithMessageHistory** 或显式消息列表管理。

```python
# 示例：用消息历史维护多轮对话
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage

prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个简洁的助手。"),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{input}"),
])

llm = ChatOpenAI(model="gpt-4o-mini", api_key="你的 API Key")
chain = prompt | llm

history = [
    HumanMessage(content="我叫小明"),
    AIMessage(content="你好，小明！"),
]

response = chain.invoke({"history": history, "input": "我叫什么名字？"})
print(response.content)
```

### 4.2 工具（Tool）

**核心结论：** 工具让模型可以调用外部函数，例如计算器、搜索、数据库查询。

```python
# 示例：定义一个简单工具
from langchain_core.tools import tool

@tool
def add(a: int, b: int) -> int:
    """计算两个整数之和。"""
    return a + b

print(add.name)
print(add.description)
print(add.invoke({"a": 3, "b": 5}))
```

### 4.3 检索器（Retriever）

**核心结论：** 检索器负责从向量数据库或文档库中找到与问题最相关的片段，是 RAG（Retrieval-Augmented Generation，检索增强生成）的关键组件。

```python
# 示例：最小检索思路（伪代码示意，需配合向量库）
# from langchain_community.vectorstores import FAISS
# from langchain_openai import OpenAIEmbeddings
#
# vectorstore = FAISS.from_texts(["LangChain 是 LLM 应用框架", "LCEL 用管道符组合组件"],
#                                embedding=OpenAIEmbeddings(api_key="你的 API Key"))
# retriever = vectorstore.as_retriever()
# docs = retriever.invoke("LCEL 是什么")
# print(docs)
```

---

## 5. 从链到智能体：LangChain 的工程化路线

**核心结论：** 当链需要“根据情况决定下一步做什么”时，就进入智能体（Agent）范畴；LangChain 提供 Agent、Tool Calling、LangGraph 等能力支撑更复杂编排。

学习路径建议：

1. 先掌握 `ChatModel + PromptTemplate + OutputParser`。
2. 再用 LCEL 组合链。
3. 然后加入 Memory、Tool、Retriever。
4. 最后学习 Agent 与 LangGraph。

```python
# 示例：创建一个会调用工具的简单 Agent
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate

@tool
def multiply(a: int, b: int) -> int:
    """计算两个整数乘积。"""
    return a * b

llm = ChatOpenAI(model="gpt-4o-mini", api_key="你的 API Key")
prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个会使用工具的助手。"),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])

agent = create_tool_calling_agent(llm, [multiply], prompt)
executor = AgentExecutor(agent=agent, tools=[multiply], verbose=True)

print(executor.invoke({"input": "请计算 12 乘以 7"})["output"])
```

---

## 动手练习：构建你的第一个 LangChain 命令行助手

**任务：** 在本地创建一个 Python 文件 `mini_assistant.py`，实现一个命令行 AI 助手，要求：

1. 使用 `ChatOpenAI` 调用模型。
2. 使用 `ChatPromptTemplate` 定义系统角色：你是简洁的 Python 导师。
3. 使用 `StrOutputParser` 解析输出。
4. 用 LCEL 组合成链。
5. 支持连续多轮输入，用户输入 `exit` 退出。
6. 每轮把历史消息传入链，实现简单记忆。

**提示：** 可先实现单轮，再加入 `history` 列表；消息可用 `HumanMessage` 和 `AIMessage`。

**进阶：** 增加一个 `@tool` 计算器工具，并尝试用 Agent 替代普通链。

---

**本课小结：** LangChain 基础不是背 API，而是理解“模型、提示词、解析器、链、记忆、工具、检索、智能体”这套组合思维。掌握它，你就拥有了把 LLM 从玩具变成工程的底盘。

## agent.fw.langchain_lcel

# LangChain LCEL 入门：从零到工程级

> **一句话直觉**：LCEL（LangChain Expression Language，LangChain 表达式语言）让你**用管道符 `|` 把提示、模型、解析器串成一条可复用、可流式、可并行的 AI 处理链**，像搭乐高一样构建 LLM 应用。

---

## 1. 为什么需要 LCEL？

在没有 LCEL 之前，调用一个大模型要写很多样板代码：构造 Prompt、调用模型、解析输出、异常处理、日志追踪……一旦链条变长，代码会变得臃肿、难复用、难测试。

LCEL 的核心思想是：**统一接口 + 组合子**。

- 任何 LCEL 组件都是一个 `Runnable`（可运行对象），都支持 `invoke`、`batch`、`stream`、`ainvoke` 等方法。
- 用 `|` 运算符把多个 Runnable 组合成一个新的 Runnable。

```python
# 这是 LCEL 最基本的骨架：Prompt | Model | Parser
chain = prompt | model | parser
result = chain.invoke({"topic": "Python"})
```

---

## 2. 三大基础积木：Prompt、Model、Parser

LCEL 链最经典的形态就是 **PromptTemplate → ChatModel → OutputParser**。

- **PromptTemplate（提示模板）**：把变量替换进字符串，生成最终发给模型的消息。
- **ChatModel（聊天模型）**：接收消息，返回 `AIMessage`。
- **OutputParser（输出解析器）**：把 `AIMessage` 转成 str、JSON、Pydantic 对象等。

```python
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

prompt = ChatPromptTemplate.from_template("用一句话解释 {topic}")
model = ChatOpenAI(model="gpt-4o-mini", temperature=0)
parser = StrOutputParser()

chain = prompt | model | parser
print(chain.invoke({"topic": "LCEL"}))
```

**关键结论**：`|` 并不是 Python 原生的运算符，而是 LangChain 给 `Runnable` 重载的 `__or__`，效果等价于 `RunnableSequence(prompt, model, parser)`。

---

## 3. 四种调用方式：invoke / batch / stream / ainvoke

只要对象是 `Runnable`，就自动获得这四种能力，这正是 LCEL 相对手写函数的工程优势。

```python
# 1. invoke：单条同步
chain.invoke({"topic": "向量数据库"})

# 2. batch：批量并行（自动并发）
chain.batch([{"topic": "RAG"}, {"topic": "Agent"}])

# 3. stream：流式逐 token 输出
for chunk in chain.stream({"topic": "LCEL"}):
    print(chunk, end="", flush=True)

# 4. ainvoke：异步，适合 FastAPI 等异步框架
# await chain.ainvoke({"topic": "LCEL"})
```

**关键结论**：你写在链里的每一步，只要实现了 Runnable 协议，**流式、批处理、异步能力会自动向下传递**，不需要额外改造。

---

## 4. 进阶组合：RunnableParallel 与 RunnablePassthrough

真实业务里经常需要：把同样的输入同时喂给多个分支，或把原始输入原样传递下去。

- **RunnableParallel（并行）**：把一个 dict 的多个键同时计算。
- **RunnablePassthrough（透传）**：把输入原封不动传到下一步，常用在 RAG 里把「问题」和「检索结果」一起送进 prompt。
- **RunnableLambda（自定义函数包装）**：把任意 Python 函数变成 Runnable。

```python
from langchain_core.runnables import RunnableParallel, RunnablePassthrough, RunnableLambda

retriever = RunnableLambda(lambda q: f"关于「{q}」的检索结果...")

rag_chain = (
    RunnableParallel(context=retriever, question=RunnablePassthrough())
    | ChatPromptTemplate.from_template("资料：{context}\n问题：{question}\n请回答：")
    | model
    | StrOutputParser()
)

print(rag_chain.invoke("什么是 LCEL？"))
```

**关键结论**：LCEL 的组合是**声明式**的——你描述数据怎么流动，而不是写 for 循环去驱动它。

---

## 5. 工程级能力：LCEL 带来的开箱即用特性

| 能力 | 说明 |
|---|---|
| **流式（Streaming）** | 每个 Runnable 都支持 `stream`，首 token 延迟大幅降低 |
| **并行（Parallel）** | `RunnableParallel` 与 `batch` 自动并发 |
| **重试 / 回退** | `.with_retry()`、`.with_fallbacks()` |
| **可观测（Observability）** | 天然集成 LangSmith，每一步都能看到输入输出 |
| **异步（Async）** | `.ainvoke` / `.astream` / `.abatch` |
| **类型安全** | 与 Pydantic 输出解析器配合，返回结构化对象 |

```python
# 工程实践：加重试 + 回退 + 结构化输出
from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser

class Topic(BaseModel):
    name: str = Field(description="主题名")
    summary: str = Field(description="一句话摘要")

parser = PydanticOutputParser(pydantic_object=Topic)
prompt = ChatPromptTemplate.from_template("介绍 {topic}\n{format_instructions}")
prompt = prompt.partial(format_instructions=parser.get_format_instructions())

robust_chain = (prompt | model | parser).with_retry(stop_after_attempt=3)
print(robust_chain.invoke({"topic": "LCEL"}))
```

**关键结论**：LCEL 不是语法糖，它是 LangChain 把「AI 应用流水线」抽象成一个**统一可组合接口**的工程基石；后面的 RAG、Agent、工具调用，全都建立在这套 Runnable 协议之上。


---

## 本课题目

### single_choice · None



- [A] Prompt + Model + Output Parser 组成可复用链
- [B] 只有数据库连接和 ORM 映射
- [C] 只有静态 HTML 模板渲染
- [D] 只有操作系统进程调度配置

**参考答案**：0

**解析**：LangChain 的基础用法是把提示模板、模型调用和输出解析组合成链（Chain），使流程可复用、可组合；其他选项与该框架定位无关。

### single_choice · None



- [A] 它负责训练模型权重
- [B] 它把变量填充进提示文本，形成最终发给模型的提示
- [C] 它直接管理向量数据库的索引文件
- [D] 它替代 Python 的异常处理机制

**参考答案**：1

**解析**：PromptTemplate 的职责是模板化提示文本并做变量替换；训练模型、向量索引、异常处理都不是它的功能。

### single_choice · None



- [A] 调用模板对象的 format 方法并传入变量
- [B] 调用 print 并期望自动替换
- [C] 使用 len 函数
- [D] 使用 sorted 排序变量名

**参考答案**：0

**解析**：提示模板提供格式化接口，传入变量得到最终文本；print、len、sorted 都不做模板替换。

### single_choice · None



- [A] Runnable 是统一的可调用接口，支持 invoke、batch、stream 等调用方式
- [B] Runnable 只能用于多线程
- [C] Runnable 是数据库事务
- [D] Runnable 是 Python 的装饰器语法

**参考答案**：0

**解析**：Runnable 抽象统一了同步/批量/流式调用方式；它不是线程、事务或装饰器语法。

### multi_choice · None



- [A] 提示模板（Prompt Template）
- [B] 聊天模型（Chat Model）
- [C] 输出解析器（Output Parser）
- [D] 操作系统内核调度器

**参考答案**：[0, 1, 2]

**解析**：提示模板、聊天模型、输出解析器是常见核心组件；操作系统内核调度器不属于 LangChain 组件。

### multi_choice · None



- [A] 支持用管道符组合多个 Runnable
- [B] 支持流式输出
- [C] 支持批量调用
- [D] 要求所有组件必须是字符串类型

**参考答案**：[0, 1, 2]

**解析**：LCEL 支持组合、流式、批量等；并不要求组件是字符串类型，组件可以是各种 Runnable。

### multi_choice · None



- [A] 把文档切分为片段并建立向量索引
- [B] 根据用户问题检索相关片段
- [C] 把检索到的片段作为上下文放入提示
- [D] 把模型的权重在本地重新训练一遍

**参考答案**：[0, 1, 2]

**解析**：RAG 典型流程包括切分、索引、检索、拼上下文；不需要在本地重新训练模型权重。

### multi_choice · None



- [A] system 消息常用于设定助手的行为与约束
- [B] human 消息表示用户输入
- [C] ai 消息表示模型回复
- [D] 所有消息必须使用完全相同的角色名

**参考答案**：[0, 1, 2]

**解析**：system/human/ai 分别对应约束、用户输入、模型回复；不同角色可以混合使用，不必完全相同。

### fill_blank · None



**参考答案**：["|", "管道符", "管道"]

**解析**：LCEL 使用管道符 `|` 把前一个组件的输出传给下一个组件，从而组合成链。

### fill_blank · None



**参考答案**：["Output Parser", "输出解析器", "output parser", "parser"]

**解析**：输出解析器负责把模型返回的文本解析为结构化数据（如 JSON、列表）。

### code_reading · None



**参考答案**：由 PromptTemplate 模板中的占位符 {sentence} 定义；必须提供是为了让格式化的提示模板完成变量替换，否则模板无法生成最终提示文本。

**解析**：模板里的 `{sentence}` 声明了所需输入变量，invoke 时传入字典以完成填充；缺少变量就无法生成完整提示。

### code_reading · None



**参考答案**：方式一 invoke 处理单个输入，返回单个结果；方式二 batch 一次处理多个输入，返回结果列表（顺序对应输入）。

**解析**：Runnable 接口提供单条调用 invoke 与批量调用 batch；batch 适合同时处理多个输入，减少重复调用开销。

### single_choice · None



- [A] 一条 SQL 查询语句
- [B] 把多个组件按顺序或条件组合成一个可调用流程
- [C] Python 的继承关系树
- [D] 一组互不相关的日志文件

**参考答案**：1

**解析**：链强调组件的编排与复用，把提示、模型、解析器等串起来；它不指 SQL、继承树或日志文件。

### scenario · None



**解析**：需要在多轮之间保留对话历史（Memory / 消息列表），并把历史作为上下文注入每次请求，模型才能理解指代；这正是 Memory 与消息角色机制要解决的问题。

### single_choice · None



- [A] 把模型返回的自由文本转换为结构化数据或指定格式
- [B] 压缩图片体积
- [C] 给模型增加 GPU 显存
- [D] 修改操作系统环境变量

**参考答案**：0

**解析**：Output Parser 用于解析模型输出（如 JSON、列表），便于后续程序处理；其余选项与文本解析无关。

### single_choice · None



- [A] 它们只是颜色标记，不影响模型行为
- [B] system 通常用于设定整体行为约束，human 表示用户输入，ai 表示模型回复
- [C] 所有消息必须是同一种角色
- [D] human 消息只能出现一次

**参考答案**：1

**解析**：聊天模型按角色区分消息来源，system 设定约束，human 是用户，ai 是模型；角色会影响模型理解上下文。

### single_choice · None



- [A] 只有 HTTP 状态码
- [B] 模型生成的消息内容（如文本）以及可能的附加元数据
- [C] 只有数据库主键
- [D] 只有 Python 版本号

**参考答案**：1

**解析**：聊天模型的返回一般是消息对象，含内容与元数据；不会只返回状态码、主键或版本号。

### single_choice · None



- [A] 它是按位或运算，与链无关
- [B] 它用于把前一个组件的输出作为后一个组件的输入，形成组合链
- [C] 它只能用于整数
- [D] 它会删除所有变量

**参考答案**：1

**解析**：在 LCEL 中 `|` 表示组件组合，前一个 Runnable 的输出传给下一个；不是普通按位或，也不限于整数。

### single_choice · None



- [A] 检索（Retrieval）相关组件，把相关文档片段作为上下文
- [B] 更长的变量名
- [C] 更多的注释
- [D] 把 Python 版本降级

**参考答案**：0

**解析**：检索增强生成（RAG）通过检索相关文档片段并放入提示上下文，降低幻觉；变量名、注释、版本降级无此作用。

### single_choice · None



- [A] 在多次交互之间保存和传递对话历史或状态
- [B] 释放 Python 对象内存
- [C] 加速 CPU 缓存
- [D] 管理磁盘分区

**参考答案**：0

**解析**：Memory 关注对话状态或历史的保存与注入；名字虽含“内存”，但不是底层内存管理。

### single_choice · None



- [A] 工具是模型可以调用以执行具体动作（如计算、查询）的函数封装
- [B] 工具是 Python 的 try/except 语法
- [C] 工具只能用于打印日志
- [D] 工具必须返回图片

**参考答案**：0

**解析**：工具把外部能力封装成模型可调用的接口，用于计算、检索等；与异常语法、日志、图片返回无必然关系。

### single_choice · None



- [A] 它把前一个组件的输出作为后一个组件的输入参数调用
- [B] 它把多个组件合并成一个新的 Python 类，运行时随机选择一个执行
- [C] 它把组件列表传给线程池并行执行
- [D] 它只是语法糖，等价于把对象放进一个 Python 列表

**参考答案**：0

**解析**：LCEL 的管道运算符在底层通过 Runnable 的 __or__ 组合成 RunnableSequence，运行时把上游输出传给下游的 invoke/stream 等方法，形成数据流。它并非随机选择、并行执行或单纯的列表容器。

### single_choice · None



- [A] 只能调用 invoke，不能调用 batch 或 stream
- [B] 同一个链对象通常可以调用 invoke、batch、stream 等方法
- [C] 必须先用 compile() 编译，否则不能调用
- [D] 调用 stream 时返回的是一个字符串列表

**参考答案**：1

**解析**：LCEL 构建出的 Runnable 统一实现了 invoke、batch、stream、ainvoke 等接口，所以同一个链可切换调用方式；不需要 compile；stream 返回的是迭代器/生成器而非字符串列表。

### multi_choice · None



- [A] invoke 处理单个输入
- [B] stream 以分片方式返回输出
- [C] batch 批量处理多个输入
- [D] 用 `|` 把两个 Runnable 组合成新的 Runnable
- [E] 必须避免使用任何输出解析器

**参考答案**：[0, 1, 2, 3]

**解析**：invoke、stream、batch 是 LCEL Runnable 的常见调用方式，`|` 是组合方式；输出解析器是兼容的，并非禁用项，所以最后一项错误。

### multi_choice · None



- [A] 组件可组合，链的构建代码可读性较高
- [B] 组合后仍可保留流式与批处理等统一接口
- [C] 便于与回调、追踪/可观测性工具集成
- [D] 能自动修正大模型的幻觉，保证答案正确

**参考答案**：[0, 1, 2]

**解析**：可组合性、统一运行接口、可观测性集成是 LCEL 的实际优势；但它不能自动消除模型幻觉，那属于提示工程、检索或评估等范畴。

### multi_choice · None



- [A] 明确每个组件的输入/输出契约
- [B] 需要整形时使用 RunnableLambda 或自定义映射函数
- [C] 用 RunnablePassthrough.assign 保留原字段并补充新字段
- [D] 假设下游会自动根据关键词匹配上游字典的键

**参考答案**：[0, 1, 2]

**解析**：明确契约、显式整形、使用 assign 都是正确做法。LCEL 不会自动按键名猜测匹配，所以最后一项是错误的假设。

### multi_choice · None



- [A] 提示模板本身可作为链的一个组件参与 `|` 组合
- [B] 模板的输入通常由上游组件或用户传入的字典提供
- [C] 模板可先用 partial 固定部分变量
- [D] 模板必须放在链的最末端

**参考答案**：[0, 1, 2]

**解析**：提示模板是可组合组件，常位于链中前部，输入来自字典或上游，partial 可预填变量。它通常不是最末端（末端多为模型或解析器），所以最后一项错误。

### multi_choice · None



- [A] Runnable 通常提供 ainvoke 等异步接口
- [B] 在异步链上可用 astream 以异步方式获取分片
- [C] 异步调用与同步调用返回的语义可以不一致
- [D] 使用异步便于在高并发场景下提升吞吐

**参考答案**：[0, 1, 3]

**解析**：LCEL 组件通常同时提供同步与异步接口，异步适合高并发；同一链的同步与异步应保持一致的语义，因此第三项错误。

### fill_blank · None



**参考答案**：["|", "管道符", "pipe", "竖线"]

**解析**：LCEL 用 `|` 运算符把 Runnable 依次组合成链，前一个的输出作为后一个的输入，等价于管道式数据流。

### fill_blank · None



**参考答案**：["Runnable", "runnable", "Runnable 对象", "可运行对象"]

**解析**：Runnable 是 LCEL 的核心抽象，提示模板、模型、解析器及各种工具都实现它，从而获得统一调用接口和组合能力。

### code_reading · None



**参考答案**：out 最可能是字符串（str）。因为链的最后一段是 StrOutputParser()，它会把模型返回的消息内容转换为纯文本字符串，所以整条链的最终输出是字符串。

**解析**：链的输出类型由末端组件决定。StrOutputParser 将模型消息转成字符串，因此 invoke 返回 str 而非 AIMessage。

### code_reading · None



**参考答案**：out 的值是 {'a': 4, 'b': 6}。因为 RunnableParallel 会用同一输入 3 分别调用两个分支：a 分支 3+1=4，b 分支 3*2=6，然后把结果汇聚成一个字典。

**解析**：RunnableParallel 对每个分支应用相同输入，返回以键为标识的字典。因此得到 {'a': 4, 'b': 6}。

### scenario · None



**解析**：解析失败常见于模型输出不规范。可在解析器上启用容错/修复能力（如修复型解析器），或对模型调用加超时与重试，或在解析异常时提供回退分支返回原始文本并提示用户，同时用结构化输出约束模型。关键是识别异常、重试与回退，而不是让异常直接冒泡。

### single_choice · None



- [A] 一定是 AIMessage 对象
- [B] 一定是原始字符串，因为解析器会把它转成字符串
- [C] 取决于 parser 的返回类型，invoke 返回的是整条链最终组件的输出
- [D] 一定是字典，键为 topic

**参考答案**：2

**解析**：链的输出类型由最后一个组件决定。若 parser 是字符串输出解析器则返回字符串，若是结构化解析器则可能返回字典等。因此不能一概而论，需看 parser。

### scenario · None



**解析**：LCEL 链化后仍保留统一接口，因此同一链可用 stream 支持在线流式体验、用 batch 支持离线批量处理，无需重写业务逻辑。把高延迟步骤作为链中一个 Runnable 组件接入，即可复用同一组合结构在不同调用方式下运行。

### single_choice · None



- [A] 使用 RunnableParallel / 字典语法把多个 Runnable 的结果组合成字典再传给下游
- [B] 只能把全部数据一次性传给单个模板，无法分叉
- [C] 必须继承 Runnable 并手写 __call__
- [D] 用 for 循环依次调用每个组件

**参考答案**：0

**解析**：LCEL 支持用字典或 RunnableParallel 表示并行分支，各分支独立处理同一输入，输出汇聚为字典，再交给下游模板使用，这是常见的数据分发手段。

### single_choice · None



- [A] 只有调用 invoke 才支持流式，stream 是同步阻塞的
- [B] 链式组合能保留流式能力，逐个 chunk 传递，而不是等全部生成完才返回
- [C] 流式输出无法与输出解析器一起使用
- [D] stream 会把所有分片拼成一个大字符串后一次返回

**参考答案**：1

**解析**：LCEL 的一大优势是组合后仍保持流式，数据以分片形式逐级传递。虽然某些解析器对分片处理有要求，但并非完全不能配合流式使用。

### single_choice · None



- [A] LCEL 能自动帮你写提示词内容
- [B] LCEL 让组件可组合，并统一获得 invoke/batch/stream/异步等能力及回调、追踪支持
- [C] LCEL 能替代模型的推理过程，速度更快
- [D] LCEL 会把所有网络请求缓存到本地磁盘

**参考答案**：1

**解析**：LCEL 的核心价值是标准化组合与运行接口，从而复用批处理、流式、异步、回调与可观测性等能力。它不生成提示词、不替代模型推理、也不内置磁盘缓存。

### single_choice · None



- [A] 直接传，下游会自己猜到要用哪个键
- [B] 使用 RunnableLambda / 提取函数把字典映射为下游需要的输入结构
- [C] 把字典转成字符串后立刻再解析回来
- [D] 无法处理，必须重写整条链

**参考答案**：1

**解析**：LCEL 不猜测键名，需要显式用 RunnableLambda 或自定义函数做数据整形，把上游输出映射为下游期望的格式，这是链式数据转换的常用方式。

### single_choice · None



- [A] 模板只能接收一个字符串变量
- [B] 模板可接收多个命名变量，调用时用字典提供这些键
- [C] 模板变量名必须与模型名相同
- [D] 模板无法使用部分变量（partial）

**参考答案**：1

**解析**：提示模板支持多个命名占位符，通过字典传入键值；也支持用 partial 预先填充部分变量。命名与模型无关，也不限于单变量。

### single_choice · None



- [A] 丢弃全部输入，返回 None
- [B] 把输入原样传递下去，或结合 assign 把新字段附加到原有数据上
- [C] 把输入随机打乱顺序
- [D] 把输入转成 JSON 字符串

**参考答案**：1

**解析**：RunnablePassthrough 用于透传原输入，常与 assign 搭配在保留原始字段的同时补充新字段，方便下游模板使用。它不做随机、JSON 转换等操作。

### single_choice · None



- [A] 把多个输入作为一个列表批量处理，内部可并发调用各个输入
- [B] 把模型参数批量修改
- [C] 把输出解析成批注
- [D] 清空链中的所有缓存

**参考答案**：0

**解析**：batch 接收一组输入并对每个输入运行链，常用于批量推理，可配合 max_concurrency 控制并发；与参数修改、批注、缓存清理无关。
