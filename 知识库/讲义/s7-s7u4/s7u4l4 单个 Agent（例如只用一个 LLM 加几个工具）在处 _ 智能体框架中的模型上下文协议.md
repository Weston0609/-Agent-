# s7u4l4 单个 Agent（例如只用一个 LLM 加几个工具）在处 / 智能体框架中的模型上下文协议

> 来源 `content/lessons/s7u4l4.json`

## agent.fw.crewai

## 一句话直觉

**CrewAI** 是一个让多个 **AI Agent（智能体）** 像一支团队一样分工协作的 Python 框架：你定义角色、任务和流程，它负责调度它们互相对话、调用工具，最终交付结果。

---

### 1. 为什么需要 CrewAI：从单 Agent 到多 Agent 协作

单个 Agent（例如只用一个 LLM 加几个工具）在处理复杂任务时容易上下文混乱、职责不清。**CrewAI** 的核心思想是：把复杂任务拆成多个角色（Role），每个角色有独立的目标（Goal）、背景（Backstory）和可用工具（Tools），再由一个流程（Process）把它们串起来。

三个核心概念：

- **Agent（智能体）**：一个有身份、有目标、有工具的 AI 角色。
- **Task（任务）**：一段明确要完成的工作描述，可指定由哪个 Agent 执行、输出格式如何。
- **Crew（团队）**：把多个 Agent 和 Task 组合起来，按某种流程执行。

流程目前常用两种：

- **Sequential（顺序流程）**：任务依次执行，前一个的输出作为后一个的上下文。
- **Hierarchical（层级流程）**：有一个 Manager Agent 负责分配和汇总。

```python
# 最小可运行示例：两个 Agent 顺序协作
# 安装：pip install crewai crewai-tools
from crewai import Agent, Task, Crew, Process

# 1) 定义研究员 Agent
researcher = Agent(
    role="研究员",
    goal="收集主题的关键信息",
    backstory="你擅长快速调研并提炼要点",
    verbose=True,
)

# 2) 定义写作 Agent
writer = Agent(
    role="写作者",
    goal="把调研结果写成通俗短文",
    backstory="你擅长把复杂内容写清楚",
    verbose=True,
)

# 3) 定义任务
task1 = Task(
    description="调研 Python 异步编程的核心概念",
    expected_output="一份 5 条要点的清单",
    agent=researcher,
)

task2 = Task(
    description="基于调研要点写一篇 200 字介绍",
    expected_output="一篇 200 字中文短文",
    agent=writer,
)

# 4) 组队并执行
crew = Crew(
    agents=[researcher, writer],
    tasks=[task1, task2],
    process=Process.sequential,
)

result = crew.kickoff()
print(result)
```

---

### 2. Agent 的关键参数：角色、记忆与工具

要让 Agent 表现稳定，关键是写清楚三件事：`role`（角色名）、`goal`（目标）、`backstory`（背景故事）。**Backstory** 不是装饰，它会影响模型的行为风格和决策倾向。

另一个重点是 **Tools（工具）**。CrewAI 支持把普通 Python 函数包装成工具，让 Agent 在需要时调用。常用做法是继承 `BaseTool` 或用 `@tool` 装饰器。

```python
# 给 Agent 添加自定义工具
from crewai import Agent
from crewai.tools import tool

@tool("字数统计")
def count_words(text: str) -> int:
    """返回输入文本的字数"""
    return len(text)

analyst = Agent(
    role="文本分析师",
    goal="统计并解释文本长度",
    backstory="你善于用数据描述文本",
    tools=[count_words],
    verbose=True,
)
```

---

### 3. Task 的输出控制：expected_output 与上下文传递

`expected_output` 是 CrewAI 里被低估但极其重要的字段。它告诉模型"交付物长什么样"，能显著提升输出稳定性。

顺序流程中，前一个 Task 的输出会自动进入后一个 Task 的上下文（context）。你也可以通过 `context=[task1]` 显式指定依赖。

```python
from crewai import Task

task_a = Task(
    description="列出 3 个 Python 常用 Web 框架",
    expected_output="编号列表，每项含名称和一句说明",
    agent=researcher,
)

task_b = Task(
    description="对上一个任务的结果做对比分析",
    expected_output="一张 Markdown 表格：框架、优点、缺点",
    agent=analyst,
    context=[task_a],   # 显式声明依赖
)
```

---

### 4. 记忆、回调与工程化要点

真实项目中，CrewAI 常用能力包括：

- **Memory（记忆）**：`memory=True` 启用短期/长期记忆，让 Agent 记住历史交互。
- **Callback（回调）**：在任务开始/结束时触发函数，用于日志、监控、通知。
- **max_iter / max_rpm**：控制单个 Agent 的最大迭代次数和每分钟请求数，避免失控和限流失败。
- **输出格式**：可通过 `output_file` 把结果写文件，或用 Pydantic 模型做结构化输出。

```python
from crewai import Crew, Process

def on_task_done(output):
    print("[回调] 任务完成:", str(output)[:80])

crew = Crew(
    agents=[researcher, writer],
    tasks=[task1, task2],
    process=Process.sequential,
    memory=True,
    task_callback=on_task_done,
    max_rpm=30,
)

result = crew.kickoff(inputs={"topic": "Python 异步编程"})
print(result)
```

---

### 5. 什么场景适合用 CrewAI

适合：

- 需要多角色分工的内容生产（调研 → 写作 → 校对）。
- 需要工具调用 + 多步推理的自动化流程。
- 快速原型验证多 Agent 思路。

不太适合：

- 对延迟极致敏感的单步调用（直接调 LLM 更快）。
- 强确定性、无需自然语言推理的任务（用普通代码即可）。

---

### 动手练习

**任务**：在本地搭建一个 2 人 Crew，完成"给定一个 Python 库名，输出一段 150 字以内的中文介绍"。

要求：

1. 安装 `pip install crewai crewai-tools`，并配置好 `OPENAI_API_KEY`（或兼容的本地模型）。
2. 定义两个 Agent：`researcher`（负责提炼该库的用途与 3 个关键特性）和 `writer`（负责写成 150 字短文）。
3. 定义两个 Task，使用 `Process.sequential`，并显式写清每个 Task 的 `expected_output`。
4. 用 `crew.kickoff(inputs={"library": "requests"})` 运行，打印结果。
5. 进阶：给 researcher 加一个自定义工具，用 `len()` 统计输出字符数，并在最终结果里附上字数。

提交物：一个 `.py` 文件 + 终端运行截图或输出文本。

## agent.fw.mcp_protocol

# agent.fw.mcp_protocol：智能体框架中的模型上下文协议

## 一句话直觉
**MCP（Model Context Protocol，模型上下文协议）** 就像给 AI 智能体（Agent）装了一个“万能插头”，让它能用统一的方式调用外部工具、读取数据、连接服务，而不必为每个工具单独写适配代码。它解决的是 **“智能体如何标准化地感知和操作外部世界”** 的问题。

---

## 1. 为什么需要 MCP？—— 从“手写胶水”到“标准接口”

在没有 MCP 的时候，如果你想让一个 LLM（Large Language Model，大语言模型）智能体去查天气、读文件、发邮件，你通常要：
- 为每个工具写一个函数；
- 把函数描述塞进 prompt；
- 解析模型输出的 JSON；
- 手动路由到对应函数。

每个工具、每个框架、每个模型都要重复这套“胶水代码”。

**MCP 的核心思想**：定义一个 **客户端-服务器（Client-Server）** 协议。
- **MCP Server**：把工具、资源、提示模板暴露成标准接口。
- **MCP Client**：智能体框架通过统一协议发现并调用这些能力。

这样，任何一个支持 MCP 的智能体，都能即插即用地使用任何 MCP Server。

```python
# 直觉演示：没有 MCP 时，你手动定义工具
import json

def get_weather(city: str) -> str:
    return f"{city} 晴，25°C"

tools = {
    "get_weather": get_weather
}

# 模型输出：{"tool": "get_weather", "args": {"city": "北京"}}
model_output = '{"tool": "get_weather", "args": {"city": "北京"}}'
parsed = json.loads(model_output)
result = tools[parsed["tool"]](**parsed["args"])
print(result)  # 北京 晴，25°C
```

> 这段代码能跑，但每加一个工具就要改 `tools` 字典和 prompt，无法跨框架复用。MCP 就是来标准化这件事的。

---

## 2. MCP 的三个核心原语（Primitives）

MCP 协议把服务器能提供的东西分成三类：

| 原语 | 英文 | 作用 | 类比 |
|------|------|------|------|
| 工具 | Tools | 可被模型调用的函数 | 智能体的“手” |
| 资源 | Resources | 可读取的数据（文件、数据库行） | 智能体的“眼睛” |
| 提示 | Prompts | 预定义的提示模板 | 智能体的“话术本” |

**Tools** 是最常用的。一个 MCP Server 启动后，Client 可以发送 `tools/list` 请求获取所有工具描述，再发送 `tools/call` 执行。

```python
# 模拟 MCP 协议的消息结构（简化版）
# 实际 MCP 使用 JSON-RPC 2.0 传输

# 1. Client 请求工具列表
list_request = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list",
    "params": {}
}

# 2. Server 返回工具描述
list_response = {
    "jsonrpc": "2.0",
    "id": 1,
    "result": {
        "tools": [
            {
                "name": "get_weather",
                "description": "查询指定城市的天气",
                "inputSchema": {
                    "type": "object",
                    "properties": {"city": {"type": "string"}},
                    "required": ["city"]
                }
            }
        ]
    }
}

# 3. Client 调用工具
call_request = {
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {"name": "get_weather", "arguments": {"city": "上海"}}
}

print(list_response["result"]["tools"][0]["name"])  # get_weather
print(call_request["params"]["arguments"])           # {'city': '上海'}
```

> 关键点：工具的描述（name, description, inputSchema）是**机器可读**的，智能体可以自动发现并决定调用哪个工具。

---

## 3. 传输层：MCP 怎么通信？

MCP 不绑定具体传输方式，常见有两种：

1. **stdio（标准输入输出）**：Client 启动 Server 子进程，通过 stdin/stdout 交换 JSON-RPC 消息。适合本地工具。
2. **Streamable HTTP / SSE**：通过 HTTP 长连接通信。适合远程服务。

下面用 Python 标准库模拟一个 **stdio 风格的 MCP Server**，它从标准输入读请求，向标准输出写响应。

```python
# mcp_server_demo.py
# 运行方式：echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | python mcp_server_demo.py
import sys
import json

TOOLS = [
    {
        "name": "get_weather",
        "description": "查询指定城市的天气",
        "inputSchema": {
            "type": "object",
            "properties": {"city": {"type": "string"}},
            "required": ["city"]
        }
    }
]

def handle(request: dict) -> dict:
    method = request.get("method")
    req_id = request.get("id")
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOLS}}
    elif method == "tools/call":
        name = request["params"]["name"]
        args = request["params"]["arguments"]
        if name == "get_weather":
            text = f"{args['city']} 晴，25°C"
            return {"jsonrpc": "2.0", "id": req_id, "result": {"content": [{"type": "text", "text": text}]}}
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": "Method not found"}}

for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    request = json.loads(line)
    response = handle(request)
    print(json.dumps(response), flush=True)
```

> 这就是 MCP Server 的最小骨架：读 JSON-RPC → 处理 → 写 JSON-RPC。真实 MCP SDK 帮你封装了这些细节。

---

## 4. 智能体如何用 MCP：一个最小 Client

智能体框架作为 MCP Client，需要：
1. 启动或连接 Server；
2. 调用 `tools/list` 获取工具；
3. 把工具描述转成 LLM 能理解的格式（如 OpenAI function calling）；
4. 当 LLM 决定调用工具时，发送 `tools/call`；
5. 把结果返回给 LLM。

下面用 Python 模拟这个流程（不依赖真实 LLM，用规则模拟模型决策）。

```python
# mcp_client_demo.py
import json
import subprocess

class MCPClient:
    def __init__(self, server_cmd):
        self.proc = subprocess.Popen(
            server_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True
        )
        self._id = 0

    def _send(self, method, params=None):
        self._id += 1
        req = {"jsonrpc": "2.0", "id": self._id, "method": method, "params": params or {}}
        self.proc.stdin.write(json.dumps(req) + "\n")
        self.proc.stdin.flush()
        line = self.proc.stdout.readline()
        return json.loads(line)

    def list_tools(self):
        return self._send("tools/list")["result"]["tools"]

    def call_tool(self, name, arguments):
        return self._send("tools/call", {"name": name, "arguments": arguments})

# 启动 Server 子进程
client = MCPClient(["python", "mcp_server_demo.py"])

tools = client.list_tools()
print("发现工具：", [t["name"] for t in tools])

# 模拟 LLM 决定调用 get_weather
result = client.call_tool("get_weather", {"city": "广州"})
print("调用结果：", result["result"]["content"][0]["text"])
```

> 运行后输出：
> ```
> 发现工具： ['get_weather']
> 调用结果： 广州 晴，25°C
> ```

---

## 5. 工程化要点与生态

在真实项目中，你不需要手写 JSON-RPC。官方和社区提供了 SDK：
- **Python SDK**：`pip install mcp`，提供 `Server`、`ClientSession`、`stdio_server` 等。
- **TS/JS SDK**：`@modelcontextprotocol/sdk`。

工程上注意：
- **工具描述要清晰**：LLM 靠 description 选择工具，写不好就会选错。
- **inputSchema 用 JSON Schema**：参数类型、必填项、枚举值都要写清楚。
- **错误处理**：工具失败要返回结构化错误，而不是抛异常导致连接断开。
- **安全边界**：MCP Server 可能访问文件系统、网络，要限制权限。
- **生命周期**：Client 负责启动/关闭 Server 子进程，避免僵尸进程。

```python
# 使用官方 mcp SDK 的伪代码（需安装 mcp）
# from mcp.server import Server
# from mcp.server.stdio import stdio_server
#
# app = Server("weather-server")
#
# @app.list_tools()
# async def list_tools():
#     return [{"name": "get_weather", "description": "...", "inputSchema": {...}}]
#
# @app.call_tool()
# async def call_tool(name, arguments):
#     ...
#
# async def main():
#     async with stdio_server() as (read, write):
#         await app.run(read, write)
```

> 官方 SDK 把传输、消息路由、生命周期都封装好了，你只需关注工具逻辑。

---

## 动手练习

**任务**：实现一个 MCP Server，暴露两个工具，并写一个 Client 调用它们。

1. 基于本文的 `mcp_server_demo.py`，新增一个工具 `add_numbers`，接受 `a`、`b` 两个数字，返回它们的和。
2. 编写一个 Client，依次：
   - 调用 `tools/list`，打印所有工具名；
   - 调用 `add_numbers`，参数 `a=3, b=5`；
   - 打印返回结果（应为 `8`）。
3. 挑战：让 Client 在调用前先打印工具的 `description` 和 `inputSchema`，模拟 LLM 选择工具所需的信息。

**提交要求**：两个 `.py` 文件，能通过 `python client.py` 一键运行并输出正确结果。

**提示**：
- Server 的 `handle` 函数里加一个 `elif name == "add_numbers"` 分支。
- 返回格式遵循 MCP：`{"content": [{"type": "text", "text": str(result)}]}`。
- 注意数字类型转换，`arguments` 里可能是字符串或数字，统一用 `float` 或 `int`。


---

## 本课题目

### single_choice · None



- [A] 把两个智能体放进同一个 Crew，并通过任务之间的上下文依赖来传递结果
- [B] 把两个智能体合并成一个智能体，用一段更长的提示词同时完成调研和写作
- [C] 分别创建两个互不相关的 Crew，让它们通过读写同一个全局变量通信
- [D] 只创建一个任务，让框架自动拆分给两个智能体并行执行

**参考答案**：0

**解析**：CrewAI 的核心抽象是 Crew（智能体团队）和 Task（任务），任务之间可以通过上下文依赖串联，从而让下游任务使用上游任务的产出。合并智能体会削弱分工；两个独立 Crew 无法直接共享任务上下文；单个任务不会被自动拆分给多个智能体。

### single_choice · None



- [A] Task 定义要做什么，Agent 定义由谁来做以及具备什么角色能力
- [B] Agent 定义要做什么，Task 定义由谁来做
- [C] 一个 Agent 在同一时刻只能绑定一个 Task，且该 Task 不能再被其他 Agent 使用
- [D] Task 必须比 Agent 先创建，否则无法建立关联

**参考答案**：0

**解析**：在 CrewAI 里，Agent 描述角色、目标与背景能力，Task 描述具体工作内容与期望输出，任务被分配给某个智能体执行。Agent 与 Task 的创建顺序并无强制要求；同一任务通常分配给一个智能体执行，但概念上任务是被分配的对象而非智能体的独占属性。

### single_choice · None



- [A] 采用层级式的流程编排，让管理者负责协调其他智能体
- [B] 采用顺序式流程，让第一个智能体顺次调用后面的智能体
- [C] 把管理者也写进每个任务的描述里，让模型自行决定
- [D] 增加智能体数量，数量越多越容易自动形成管理关系

**参考答案**：0

**解析**：层级式编排会引入管理者角色来分配任务、协调其他智能体。顺序式是逐个执行任务；把管理者写进描述并不能形成真正的协调结构；智能体数量增加不会自动产生管理关系。

### single_choice · None



- [A] 补充任务的详细描述与期望产出说明，明确范围、角度和输出形式
- [B] 换一个参数更大的模型即可，任务描述不影响结果
- [C] 把该任务拆成十个智能体分别执行同一句话
- [D] 关闭所有工具，让模型只能凭记忆回答

**参考答案**：0

**解析**：任务描述与期望产出是引导模型行为的关键输入，过于笼统会导致输出发散。仅更换模型或增加智能体数量并不能弥补需求描述的缺失；关闭工具通常会让结果更差。

### single_choice · None



- [A] 工具为智能体提供与外部系统交互的能力，智能体会根据任务需要决定是否调用
- [B] 工具一旦配置就会在每个任务中无条件执行一次
- [C] 工具只能由 Crew 的管理者智能体调用
- [D] 工具的输出会直接覆盖任务的最终答案

**参考答案**：0

**解析**：工具用于扩展智能体的外部交互能力，是否调用由智能体根据任务判断。工具并非无条件执行，也不限于管理者调用，其输出通常作为参考信息而非直接覆盖最终答案。

### single_choice · None



- [A] 便于下游程序或下游任务稳定地解析和使用该输出
- [B] 可以绕过模型调用，直接由框架生成结果
- [C] 可以省去为智能体配置角色设定的步骤
- [D] 可以自动让该任务跳过执行

**参考答案**：0

**解析**：要求结构化输出主要是为了便于机器解析与下游消费。它并不会绕过模型调用、省去角色设定或让任务跳过执行。

### single_choice · None



- [A] 直接删除该工具并期望智能体从此不再需要外部信息
- [B] 检查工具的参数说明是否清晰，必要时补充使用说明
- [C] 在任务描述中说明何时应该使用该工具
- [D] 审视工具的返回内容是否过于冗长或难以理解

**参考答案**：0

**解析**：工具调用效果差通常与参数说明、调用时机引导、返回内容质量有关。直接删除工具并不能解决信息获取需求，反而可能让智能体只能凭空作答。

### single_choice · None



- [A] 让智能体在任务之间保留和复用信息，改善多步协作的连贯性
- [B] 替代任务之间的依赖声明，自动决定任务顺序
- [C] 存储模型的权重参数以加速推理
- [D] 保证智能体不会产生任何错误输出

**参考答案**：0

**解析**：记忆能力用于跨任务保留与复用信息，提升协作连贯性。它不负责决定任务顺序，也不存储模型权重，更无法保证输出绝对正确。

### single_choice · None



- [A] 该任务缺少执行主体，需要显式分配或由流程编排中的管理者来指派
- [B] 框架会自动创建一个新智能体来执行该任务
- [C] 该任务会被自动跳过并从 Crew 中移除
- [D] 框架会把它当作普通文本直接返回，不执行任何推理

**参考答案**：0

**解析**：任务需要明确的执行主体，缺少分配时需要显式指定或在层级式编排下由管理者指派。框架不会自动创造新智能体、静默跳过任务或直接返回文本。

### single_choice · None



- [A] 通过角色分工让不同智能体专注各自擅长的环节，提升复杂任务的整体质量
- [B] 智能体越多，模型的总参数量越大，回答一定越准确
- [C] 多智能体可以完全消除大模型的幻觉问题
- [D] 多智能体可以让任务执行速度恒定快于单智能体

**参考答案**：0

**解析**：多智能体协作的价值在于分工与专业化，从而提升复杂任务质量。它不会增加模型参数量，不能消除幻觉，也不保证速度恒定更快。

### single_choice · None



- [A] 数据收集 → 数据分析 → 报告撰写，并让后两者引用前序任务的产出
- [B] 报告撰写 → 数据分析 → 数据收集，因为要先有结论
- [C] 数据收集 → 报告撰写 → 数据分析，因为报告是中间产物
- [D] 三个任务顺序任意，只要都放在同一个 Crew 中即可

**参考答案**：0

**解析**：顺序编排应遵循信息依赖方向：先收集数据，再分析，最后撰写报告，并通过上下文引用串联。倒置或随意排列会导致下游任务缺少必要输入。

### single_choice · None



- [A] 该智能体在推理和生成时使用哪个大语言模型
- [B] 该智能体可以访问哪些外部工具
- [C] 该智能体在 Crew 中的执行优先级
- [D] 该智能体的任务会被分配给哪个下游智能体

**参考答案**：0

**解析**：llm 配置指定智能体使用的语言模型。可访问的工具由 tools 决定，执行顺序由流程编排决定，下游分配由任务依赖与编排决定。

### single_choice · None



- [A] 在该任务的 context 中引用前一个任务，使其依赖前序结果
- [B] 把所有任务放进同一个列表，框架就会自动串行执行且传递结果
- [C] 给两个任务设置相同的 agent，让它们共享记忆
- [D] 把前一个任务的输出写进环境变量，再在提示词里读取

**参考答案**：0

**解析**：CrewAI 通过任务之间的上下文引用表达依赖，使下游任务能够访问上游任务的输出。仅仅把任务放进列表并不保证结果传递语义；共享 agent 不等于共享任务结果；用环境变量手工传递偏离了框架的任务上下文机制。

### single_choice · None



- [A] 针对最终任务产出设定评价标准，结合中间任务的输出质量进行整体评估
- [B] 只看运行时间，运行越快说明效果越好
- [C] 只看智能体数量，数量越多说明设计越完善
- [D] 只要模型没有报错就说明效果达标

**参考答案**：0

**解析**：多智能体应用的效果应围绕最终产出质量和中间环节质量来评估。运行时间、智能体数量和是否报错都不能单独代表效果好坏。

### single_choice · None



- [A] Crew 中任务的整体执行编排方式，例如顺序执行或按层级协作
- [B] 单个 Agent 内部的提示词渲染流程
- [C] 模型调用时的重试与超时策略
- [D] 向量数据库的索引构建过程

**参考答案**：0

**解析**：Process 描述 Crew 层面任务的编排方式，例如顺序流程或层级流程（由管理者智能体协调）。提示词渲染、模型调用重试、向量索引都不属于 Process 的语义。

### single_choice · None



- [A] 任务之间的依赖关系没有明确声明，或者选用的流程编排方式不适合当前协作模式
- [B] 智能体数量太多，CrewAI 不支持超过两个智能体
- [C] 没有为每个智能体配置独立的 API Key
- [D] 任务描述写得太详细，导致模型无法理解

**参考答案**：0

**解析**：任务顺序与稳定性通常取决于依赖声明和流程编排方式。CrewAI 支持多个智能体；API Key 通常按模型提供方配置而非每个智能体独立；任务描述详细一般有助于理解而非破坏理解。

### single_choice · None



- [A] 通过角色设定引导模型的行为风格与决策倾向
- [B] 限制该智能体可以调用的工具数量
- [C] 指定该智能体使用哪个大模型提供商
- [D] 决定该智能体在 Crew 中的执行顺序

**参考答案**：0

**解析**：role、goal、backstory 用于塑造智能体的角色定位和行为倾向，属于提示层面的设定。工具数量由 tools 配置决定，模型提供商由 llm 配置决定，执行顺序由任务与流程编排决定。

### single_choice · None



- [A] 为该智能体配置相应的工具，使其在需要时调用
- [B] 在 backstory 中写明数据库的连接字符串，模型会自动连接
- [C] 把数据库内容全部粘贴进任务描述
- [D] 修改 Crew 的 Process 为层级模式即可自动访问数据库

**参考答案**：0

**解析**：智能体要访问外部系统需要具备相应工具。连接字符串写在角色设定里并不会让模型自动建立连接；粘贴全部数据不可扩展；Process 只决定编排方式，不提供数据访问能力。

### single_choice · None



- [A] 它描述任务期望的产出形式，有助于约束智能体的输出结构
- [B] 它是运行时自动校验输出格式的强类型 schema
- [C] 它会被直接当作最终答案返回，模型不会覆盖它
- [D] 它只能填写自然语言，不能描述结构化格式

**参考答案**：0

**解析**：expected_output 是对期望产出的说明，用于引导模型生成符合要求的输出。它本身不是强制校验的 schema，也不是最终答案，且可以描述结构化格式（如 JSON 字段说明）。

### single_choice · None



- [A] 在任务的上下文引用中包含前一个任务
- [B] 把前一个任务的 agent 直接传给当前任务
- [C] 把前一个任务的工具列表复制到当前任务
- [D] 把两个任务合并为一个任务

**参考答案**：0

**解析**：任务通过上下文引用获取前序任务的输出。传递 agent 或工具列表并不会传递任务结果；合并任务则失去了依赖编排的意义。

### single_choice · None



- [A] 智能体之间共享的是通过任务上下文传递的产出，而不是隐式的全部推理过程
- [B] Crew 中的智能体数量必须为奇数才能共享信息
- [C] 共享推理过程需要手动开启 memory 参数，且默认关闭
- [D] CrewAI 的智能体之间完全无法共享任何信息

**参考答案**：0

**解析**：CrewAI 通过任务上下文把上游任务的产出传递给下游任务，而不是让所有智能体自动读取彼此的完整推理轨迹。智能体之间并非完全无法共享信息；数量与奇偶无关。

### single_choice · None



- [A] 提供工具能力的 MCP Server
- [B] 集成大模型的应用（如 IDE 插件、Agent 运行时）
- [C] 操作系统内核
- [D] Python 解释器本身

**参考答案**：1

**解析**：MCP 采用客户端-服务端模型。集成大模型的应用是 Client，负责发起连接、列出并调用工具；提供能力的进程是 Server。操作系统与解释器都不是 MCP 角色。

### single_choice · None



- [A] MCP 只能在本地进程间通信，无法跨网络
- [B] MCP 只支持 HTTP，不支持标准输入输出
- [C] MCP 可通过标准输入输出（stdio）或基于网络的传输进行通信
- [D] MCP 强制要求使用 gRPC 作为唯一传输方式

**参考答案**：2

**解析**：MCP 支持多种传输方式，常见的是 stdio（本地子进程）以及基于 HTTP/SSE 的网络传输，因此 3 正确，其余选项把它局限为单一传输方式。

### multi_choice · None



- [A] tools（可执行操作）
- [B] resources（可读取的数据）
- [C] prompts（可复用提示模板）
- [D] 修改客户端操作系统的内核参数

**参考答案**：[0, 1, 2]

**解析**：MCP 服务端暴露的三类核心能力是 tools、resources、prompts。修改内核参数属于越权行为，不是协议定义的能力类型。

### multi_choice · None



- [A] 为参数提供清晰的类型与必填约束
- [B] 为工具写明确描述，说明用途与副作用
- [C] 在工具内部对非法输入返回结构化错误，而不是崩溃
- [D] 故意隐藏参数 schema，让模型靠猜

**参考答案**：[0, 1, 2]

**解析**：好的工具设计需要有清晰的参数约束、描述和健壮的错误处理；隐藏 schema 会让调用方难以构造合法请求，是不良实践。

### multi_choice · None



- [A] 客户端也可以声明自身支持的能力，供服务端使用
- [B] 这类反向能力让服务端能请求客户端执行模型采样等操作
- [C] 能力是否需要由双方在握手时协商确定
- [D] 客户端能力无需声明，服务端可以随意调用

**参考答案**：[0, 1, 2]

**解析**：MCP 是双向的：客户端也可声明能力（如 sampling、roots），服务端可据此发起反向请求。是否可用取决于握手协商，不能假定随意可调用。

### multi_choice · None



- [A] 传入的参数不符合工具的输入 schema
- [B] 在初始化握手完成前就发起工具调用
- [C] 工具在服务端执行时抛出未处理异常
- [D] 客户端和服务端协议版本严重不兼容

**参考答案**：[0, 1, 2, 3]

**解析**：参数不合法、时机不对（未完成初始化）、服务端执行异常、协议版本不兼容都会导致调用失败，这是协议与实现层面的典型问题。

### fill_blank · None



**参考答案**：["tools", "tool", "Tools"]

**解析**：MCP 把可执行操作定义为 tools，客户端列举并调用它们；而可读取的数据是 resources，可复用模板是 prompts。

### fill_blank · None



**参考答案**：["capabilities", "capability", "Capabilities"]

**解析**：初始化阶段双方交换 capabilities，声明各自支持的能力，之后才能安全地调用对方支持的功能。

### code_reading · None



**参考答案**：该调用很可能失败：一是参数 q 传入了整数 123，不符合工具要求的字符串类型，会触发参数校验错误；二是初始化握手未真正完成，客户端可能尚未获得合法的工具清单与协商结果，调用可能被拒绝。正确做法是先完成 initialize 握手，再按 schema 传入字符串参数。

**解析**：考点包含参数 schema 校验与初始化时序。参数类型不符会校验失败；握手未完成则调用缺乏前提，二者都可能导致失败。

### code_reading · None



**参考答案**：选 C。schema 要求必填字段 path 且类型为字符串，只有 C 同时满足字段名、类型与必填要求；A 类型错误，B 字段名错误，D 缺少必填字段。

**解析**：考查对输入 schema 中 properties 与 required 的理解：字段名、类型、是否必填三者都要满足。

### scenario · None



**解析**：「有时成功、有时未知工具」通常与时序相关：可能在初始化握手未完成或工具清单尚未刷新时就发起了调用。应先确保 initialize 与 capabilities 协商完成，再列举工具清单，并在工具集变化后重新列举，避免使用过期缓存。

### scenario · None



**解析**：在 stdio 传输下，标准输出被用于传输 JSON-RPC 协议消息，若混入调试日志会破坏消息格式导致客户端解析失败。日志应写入标准错误或文件，保证标准输出只承载协议消息。

### single_choice · None



- [A] 可由模型调用、带有输入参数并可返回结果的函数式操作
- [B] 预先写在提示词里的静态文本片段
- [C] 服务端日志文件
- [D] 客户端用于配色的一组主题资源

**参考答案**：0

**解析**：MCP 的 tools 是可以被模型调用的可执行操作，带参数 schema 与返回值；resources 才是可读取的数据/文件类内容，prompts 是可复用的提示模板。

### single_choice · None



- [A] resources 一定需要网络，tools 一定需要磁盘
- [B] resources 用于提供可读取的数据内容，tools 用于执行动作或计算
- [C] 两者完全等价，只是命名不同
- [D] tools 只能返回字符串，resources 只能返回字节

**参考答案**：1

**解析**：resources 提供可供读取的上下文数据（如文件、文本片段），tools 执行带有副作用或计算逻辑的操作。二者语义不同，不是简单等价。

### single_choice · None



- [A] 它是服务端定义的可复用提示模板，客户端可获取并按需向模型注入
- [B] 它是模型训练用的数据集
- [C] 它是客户端强制执行的系统指令，服务端无法定义
- [D] 它是用来替代 tools 的一种可执行函数

**参考答案**：0

**解析**：MCP 的 prompts 由服务端定义并暴露为可复用模板，客户端可以列出并获得其内容，用于构造上下文。它既可被服务端定义，也不可执行，不同于 tools。

### single_choice · None



- [A] 使用制表符分隔的自由文本
- [B] 使用符合 JSON-RPC 风格的结构化消息，按行或按长度前缀分隔
- [C] 使用二进制 protocol buffers，且不可读
- [D] 使用纯 HTML 页面

**参考答案**：1

**解析**：MCP 消息基于 JSON-RPC 风格的结构化请求/响应/通知，在 stdio 上按行或长度前缀切分。它不是纯文本、HTML 或强制 protobuf。

### single_choice · None



- [A] 直接调用某个具体工具并等待结果
- [B] 进行初始化握手，交换协议版本与双方能力声明
- [C] 立刻断开连接以避免超时
- [D] 先删除服务端的所有资源

**参考答案**：1

**解析**：连接建立后规范要求先做初始化握手，协商协议版本并交换 capabilities，之后才能安全地列出与调用能力。跳过初始化可能导致调用失败。

### single_choice · None



- [A] 读取服务端源码文件
- [B] 通过列举能力的请求获取工具清单及其输入参数 schema
- [C] 由用户手动在提示词里写死工具名
- [D] 凭猜测直接调用直到成功

**参考答案**：1

**解析**：客户端通过 tools/list 之类的列举请求获得工具定义，包括名称、描述和输入参数的 JSON Schema，从而构造合法调用。其余方式都不是协议内做法。

### single_choice · None



- [A] 为了让服务端代码更短
- [B] 为了让客户端/模型知道应当如何构造合法参数，并支持校验
- [C] 为了加密传输内容
- [D] 为了决定客户端使用哪种编程语言

**参考答案**：1

**解析**：参数 schema 描述了参数名、类型、是否必填等，使模型与客户端能构造出合法请求，也便于在调用前做校验，而不是用于加密或决定语言。

### single_choice · None



- [A] 客户端与服务端在初始化阶段声明各自支持的特性，双方据此决定可用交互方式
- [B] 只在连接断开时协商，与功能无关
- [C] 由操作系统自动完成，应用无需感知
- [D] 能力协商只用于计费

**参考答案**：0

**解析**：能力协商发生在初始化阶段，双方声明诸如是否支持 resources、tools、prompts 或实验性特性等，从而避免调用对方不支持的能力。
