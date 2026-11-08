# s7u5l3 多智能体协作中的"交接棒" / 多个 Agent（智能体）协作时，需要一

> 来源 `content/lessons/s7u5l3.json`

## agent.multi.handoff

# agent.multi.handoff：多智能体协作中的"交接棒"

> **一句话直觉**：单个智能体（Agent）像一个全栈员工，遇到跨领域的复杂任务就会力不从心；`handoff`（交接）就是让多个专精智能体像接力赛一样把任务一棒一棒传下去，各司其职、协同完成。

---

## 0. 为什么需要 handoff？

假设你要做一个"帮我订机票+推荐酒店+写行程"的助手。

- 一个 Agent 全包：提示词（prompt）会失控、工具（tools）会打架、上下文（context）会爆炸。
- 三个专职 Agent：机票 Agent 只负责航班，酒店 Agent 只负责住宿，行程 Agent 只负责总结——这叫**多智能体（Multi-Agent）架构**。

但它们不能各自为政，任务得从一个 Agent **交给**另一个 Agent，这个"交棒"的动作就是 **handoff**。

> 通俗类比：客服转人工、医院分诊、餐厅里服务员把订单传给后厨——都是 handoff。

---

## 1. 核心概念：handoff 到底是什么？

**handoff（交接） = 一个 Agent 决定"这一步该我停下，交给谁继续"，并把当前状态传递过去的动作。**

它包含三个要素：

| 要素 | 英文 | 说明 |
|---|---|---|
| 触发条件 | trigger | 什么情况下决定交出去（如：用户问的是航班问题） |
| 目标 Agent | target | 交给谁（如：`flight_agent`） |
| 状态载荷 | payload / context | 带上哪些信息（用户原话、已收集的槽位等） |

关键点：**handoff 不是函数调用那么简单**，它意味着"控制权"（control）正式转移，接下来的对话由新 Agent 主导。

---

## 2. 最小实现：用 Python 模拟一次 handoff

我们先抛开框架（如 OpenAI Swarm、LangGraph），用最朴素的 Python 把 handoff 的本质写出来——这样你才不会被 API 名称迷惑。

```python
# 一个最小的 handler 注册表：名字 -> 处理函数
def flight_agent(state):
    return f"[机票Agent] 已为 {state['user']} 查询上海->北京航班"

def hotel_agent(state):
    return f"[酒店Agent] 已为 {state['user']} 推荐3家酒店"

AGENTS = {
    "flight": flight_agent,
    "hotel": hotel_agent,
}

def router(user_input, state):
    """根据用户输入决定 handoff 到哪个 Agent。"""
    if "机票" in user_input or "航班" in user_input:
        return "flight"
    if "酒店" in user_input or "住宿" in user_input:
        return "hotel"
    return None

def run(user_input, state):
    target = router(user_input, state)
    if target is None:
        return "[主Agent] 我不确定，请重新描述"
    # 关键：这就是一次 handoff
    return AGENTS[target](state)

# 试跑
state = {"user": "小王", "history": []}
print(run("帮我订机票", state))
print(run("再推荐个酒店", state))
```

输出：

```
[机票Agent] 已为 小王 查询上海->北京航班
[酒店Agent] 已为 小王 推荐3家酒店
```

**这一段就是 handoff 的全部骨架**：路由 → 找 Agent → 传状态 → 执行。后期所有框架都只是把这三步工程化。

---

## 3. 状态传递：handoff 的"接力棒"

接力赛跑丢棒 = 任务失败。handoff 最容易出 bug 的地方就是**状态没带全**。

一个健壮的 handoff 至少要传递：

- `user_input`：原始问题（防止下一位 Agent 上下文缺失）
- `history`：之前几个 Agent 已经做了什么
- `slots`：已收集的结构化信息（出发地、日期…）
- `next`：本次交给谁（有些框架把这个显式写在消息里）

```python
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class HandoffState:
    user_input: str
    history: List[str] = field(default_factory=list)
    slots: Dict[str, str] = field(default_factory=dict)
    next: Optional[str] = None   # 显式记录交接目标

# Agent 执行完后，把"我做了什么"写进 history，再把控制权 shift
def flight_agent(state: HandoffState) -> HandoffState:
    state.slots["route"] = "SHA->PEK"
    state.history.append("flight_agent: 查到了 SHA->PEK 的航班")
    state.next = "hotel"   # 显式 handoff 到酒店 Agent
    return state

def hotel_agent(state: HandoffState) -> HandoffState:
    state.slots["hotel"] = "外滩某酒店"
    state.history.append("hotel_agent: 推荐了外滩酒店")
    state.next = None      # 结束
    return state

REGISTRY = {"flight": flight_agent, "hotel": hotel_agent}

def run_chain(state: HandoffState, entry="flight", max_steps=5):
    state.next = entry
    step = 0
    while state.next and step < max_steps:
        agent = REGISTRY[state.next]
        state = agent(state)
        step += 1
    return state

s = HandoffState(user_input="帮我订上海到北京的机票和酒店")
s = run_chain(s)
print(s.history)
print(s.slots)
```

输出：

```
['flight_agent: 查到了 SHA->PEK 的航班', 'hotel_agent: 推荐了外滩酒店']
{'route': 'SHA->PEK', 'hotel': '外滩某酒店'}
```

**关键工程点**：

- `next` 字段就是接力棒，谁改它谁负责往下传。
- `max_steps` 是**死循环保险丝**。两个 Agent 互相 handoff 会无限循环，这是实战里最常见的翻车现场。
- `history` 用追加（append）而不是覆盖，才能让最后出面回答用户的 Agent 有完整上下文。

---

## 4. 控制权模式：谁是"主管"？

multi-handoff 有两种经典拓扑（topology，拓扑结构）：

### 4.1 链式（Chain）
A → B → C → 结束。适合流程固定的场景（订票→选座→支付）。

### 4.2 星型（Hub-and-Spoke / Supervisor）
有一个"主管 Agent"统一接收所有请求，再决定分给谁，谁做完再回报主管。

```python
def supervisor(user_input: str) -> str:
    """主管 Agent：不干活，只分派。"""
    if "机票" in user_input:
        return "flight"
    if "酒店" in user_input:
        return "hotel"
    return "fallback"

def worker(agent_name: str, user_input: str):
    fake_skill = {
        "flight": "[机票] 查到 3 个航班",
        "hotel":  "[酒店] 推荐 3 家酒店",
        "fallback": "[兜底] 无法处理",
    }
    return fake_skill[agent_name]

def hub_handle(user_input: str):
    agent = supervisor(user_input)
    result = worker(agent, user_input)
    return f"主管分派给 {agent}，返回：{result}"

print(hub_handle("我想订机票"))
print(hub_handle("找个酒店"))
```

**选型直觉**：
- 步骤固定 → 链式，简单可控。
- 用户意图不确定、Agent 数量多 → 星型，主管集中决策，方便做日志和限流。

---

## 5. 工程级陷阱与防护清单

真正部署时，handoff 需要考虑的不只是路由：

| 风险 | 表现 | 防护 |
|---|---|---|
| 无限循环 | A→B→A→B… | `max_steps`、重复目标检测 |
| 状态丢失 | 下一个 Agent 不知道已经聊过什么 | 显式携带 `history` 和 `slots` |
| 权限越界 | Agent 误用了不属于它的工具 | 每个 Agent 独立工具集 |
| 幻觉交接 | LLM 编出一个不存在的 Agent 名 | 目标做白名单校验 |
| 上下文爆炸 | history 越滚越长 | 对 history 做摘要（summary）后再传 |

**校验示例**：

```python
ALLOWED = {"flight", "hotel", "fallback"}

def safe_handoff(target: str) -> str:
    if target not in ALLOWED:
        return "fallback"
    return target

# 即使 LLM 幻觉出 "rocket_agent"，也不会崩溃
print(safe_handoff("rocket_agent"))   # fallback
print(safe_handoff("hotel"))           # hotel
```

---

## 6. 小结

- **handoff 的本质**：任务控制权从一个 Agent 转移到另一个 Agent，并携带必要状态。
- **三要素**：触发条件、目标 Agent、状态载荷。
- **两种拓扑**：链式（固定流程）与星型（主管调度）。
- **四项工程细节**：状态显式传递、循环保险丝、白名单校验、历史摘要。

掌握这些，无论你后面用 LangGraph、OpenAI Swarm、CrewAI 还是自研框架，读文档时都会秒懂。

---

## 7. 动手练习

**任务**：实现一个三 Agent 客服系统，用户说一句话，系统自动 handoff 完成服务。

要求：

1. 定义三个 Agent：
   - `order_agent`：处理"查订单"
   - `refund_agent`：处理"退款"
   - `tech_agent`：处理"报修/故障"
2. 用一个 `HandoffState` 数据类保存 `user_input`、`history`、`next`。
3. 用户输入"我想退款，因为我的洗衣机坏了"：
   - 应该先 handoff 到 `tech_agent`（先确认故障），
   - `tech_agent` 处理完后 handoff 到 `refund_agent` 完成退款。
4. 加 `max_steps=5` 保险丝，并在最后打印：完整 `history`、走过的 Agent 顺序、最终回复。
5. 加分项：加一个 `safe_handoff` 白名单校验，检测到非法 Agent 名时走 `fallback` 并记录一条告警到 `history`。

**预期结果**（示意）：

```
Agent 顺序: tech -> refund
history:
  - tech_agent: 已登记故障工单 #1024
  - refund_agent: 已发起退款，金额 199 元
最终回复: 您的洗衣机故障已登记，退款 199 元将在 3 个工作日到账
```

完成这道题，你就把"路由、状态、控制权、防护"四件事全都亲手走了一遍，handoff 的基础就打牢了。

```python
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class HandoffState:
    user_input: str
    history: List[str] = field(default_factory=list)
    slots: Dict[str, str] = field(default_factory=dict)
    next: Optional[str] = None

ALLOWED = {"tech", "refund", "fallback"}

def safe_handoff(target: str, state: HandoffState) -> str:
    if target not in ALLOWED:
        state.history.append(f"warn: illegal handoff -> {target}, fallback")
        return "fallback"
    return target

def tech_agent(state: HandoffState) -> HandoffState:
    state.slots["ticket"] = "#1024"
    state.history.append(f"tech_agent: 已登记故障工单 {state.slots['ticket']}")
    state.next = safe_handoff("refund", state)
    return state

def refund_agent(state: HandoffState) -> HandoffState:
    state.slots["refund"] = "199"
    state.history.append(f"refund_agent: 已发起退款，金额 {state.slots['refund']} 元")
    state.next = None
    return state

def fallback_agent(state: HandoffState) -> HandoffState:
    state.history.append("fallback_agent: 无法处理，转人工")
    state.next = None
    return state

REGISTRY = {"tech": tech_agent, "refund": refund_agent, "fallback": fallback_agent}

def run_chain(state: HandoffState, entry: str = "tech", max_steps: int = 5):
    state.next = safe_handoff(entry, state)
    order = []
    step = 0
    while state.next and step < max_steps:
        name = state.next
        order.append(name)
        state = REGISTRY[name](state)
        step += 1
    return state, order

if __name__ == "__main__":
    s = HandoffState(user_input="我想退款，因为我的洗衣机坏了")
    s, order = run_chain(s)
    print("Agent 顺序:", " -> ".join(order))
    print("history:")
    for line in s.history:
        print("  -", line)
    print("最终回复: 您的洗衣机故障已登记，退款", s.slots["refund"], "元将在 3 个工作日到账")
```

## agent.multi.shared_memory

# agent.multi.shared_memory

## 一句话直觉

多个 Agent（智能体）协作时，需要一个共同的“白板”来读写信息，`shared_memory` 就是这个白板——没有它，每个 Agent 只能各说各话。

---

## 1. 为什么多 Agent 需要共享记忆

单个 Agent 工作时，它的“记忆”就是自己的对话上下文（context）。但当多个 Agent 一起完成一个任务时，比如：

- Agent A 负责搜索资料
- Agent B 负责写代码
- Agent C 负责测试

它们必须能**看到彼此产出的中间结果**。否则 A 搜到的资料 B 拿不到，B 写的代码 C 测不了。

这就是 **shared_memory（共享记忆）** 的用途：一个所有 Agent 都能读写的公共数据结构。

> 术语：
> - Agent（智能体）：能自主感知环境并采取行动的程序。
> - Context（上下文）：模型一次调用时能看到的所有文本。
> - Shared Memory（共享记忆）：多个 Agent 共同读写的存储区。

```python
# 最朴素的“共享记忆”：一个所有 Agent 都能访问的字典
shared_memory = {}

def agent_a_write():
    shared_memory['research'] = "Python 的 dict 是有序的"

def agent_b_read():
    # B 能看到 A 写进去的内容
    return shared_memory.get('research', '暂无资料')

agent_a_write()
print(agent_b_read())  # Python 的 dict 是有序的
```

---

## 2. 共享记忆的最小接口：读、写、列目录

一个能用的 shared_memory 至少要有三个操作：

| 操作 | 含义 | Python 类比 |
|------|------|-------------|
| `write(key, value)` | 写入或覆盖一条记忆 | `d[k] = v` |
| `read(key)` | 读取一条记忆 | `d[k]` |
| `list_keys()` | 列出所有记忆的键 | `list(d.keys())` |

用一个类封装起来，比裸字典更容易扩展（以后要加锁、加版本号、加持久化都在这里改）：

```python
class SharedMemory:
    """多 Agent 共享的白板。"""

    def __init__(self):
        self._store = {}

    def write(self, key, value):
        # 写入或覆盖
        self._store[key] = value

    def read(self, key, default=None):
        # 读取，缺失时给默认值
        return self._store.get(key, default)

    def list_keys(self):
        # 列出所有键，便于 Agent 发现别人写了什么
        return list(self._store.keys())


mem = SharedMemory()
mem.write('task', '写一个排序函数')
mem.write('status', 'in_progress')
print(mem.list_keys())   # ['task', 'status']
print(mem.read('task'))  # 写一个排序函数
```

---

## 3. 让记忆“有结构”：消息日志式共享

只存 key-value 有个问题：Agent 之间往往是在**对话**，一次写一条容易丢历史。
更实用的做法是存一个**消息列表**（message log），每条消息包含：谁写的、什么时候写的、内容是什么。

```python
import time

class MessageBoard:
    """消息日志式共享记忆：追加写入，保留完整历史。"""

    def __init__(self):
        self._messages = []

    def post(self, sender, content):
        # 每条消息记录发送者、时间、内容
        self._messages.append({
            'sender': sender,
            'time': time.time(),
            'content': content,
        })

    def history(self):
        # 返回全部历史（副本，防止外部乱改）
        return list(self._messages)

    def last_from(self, sender):
        # 某个 Agent 最近一条发言
        for msg in reversed(self._messages):
            if msg['sender'] == sender:
                return msg['content']
        return None


board = MessageBoard()
board.post('searcher', '找到了 3 篇相关论文')
board.post('coder', '根据资料写好了初版')
board.post('tester', '第 2 个测试失败')

print(board.last_from('coder'))   # 根据资料写好了初版
print(len(board.history()))       # 3
```

---

## 4. 并发下的陷阱：多个 Agent 同时写

真实系统里，多个 Agent 可能是**多个线程**在跑。这时“先读后写”会出现竞态条件（race condition）：两个 Agent 都读到旧值，然后都写回，后者覆盖前者。

解决办法是用**锁**（Lock）把“读-改-写”三步保护成原子操作。

```python
import threading

class SafeCounter:
    """线程安全的共享计数器。"""

    def __init__(self):
        self._lock = threading.Lock()
        self._value = 0

    def increment(self):
        # with 保证同一时刻只有一个线程进入
        with self._lock:
            self._value += 1

    @property
    def value(self):
        with self._lock:
            return self._value


counter = SafeCounter()
threads = [threading.Thread(target=counter.increment) for _ in range(1000)]
for t in threads:
    t.start()
for t in threads:
    t.join()

print(counter.value)  # 1000，稳定正确
```

> 如果没有 `threading.Lock`，这个数字通常会小于 1000，因为发生了丢失更新。

---

## 5. 工程级封装：把上面几点合起来

一个可用的 `SharedMemory` 一般要同时具备：

1. 键值读写（第 2 节）
2. 消息日志（第 3 节）
3. 线程安全（第 4 节）
4. 命名空间（namespace），让不同任务的记忆互不干扰

```python
import threading
import time

class SharedMemory:
    """带命名空间和线程安全的多 Agent 共享记忆。"""

    def __init__(self):
        self._lock = threading.Lock()
        self._kv = {}        # (namespace, key) -> value
        self._log = []       # 全局消息日志

    def write(self, namespace, key, value):
        with self._lock:
            self._kv[(namespace, key)] = value

    def read(self, namespace, key, default=None):
        with self._lock:
            return self._kv.get((namespace, key), default)

    def post(self, namespace, sender, content):
        with self._lock:
            self._log.append({
                'namespace': namespace,
                'sender': sender,
                'time': time.time(),
                'content': content,
            })

    def history(self, namespace):
        with self._lock:
            return [m for m in self._log if m['namespace'] == namespace]
```

使用示例：

```python
mem = SharedMemory()
mem.write('task-1', 'goal', '写一个排序函数')
mem.post('task-1', 'planner', '把任务拆成 3 步')
mem.post('task-1', 'coder', '第 1 步完成')

print(mem.read('task-1', 'goal'))       # 写一个排序函数
print(len(mem.history('task-1')))       # 2
```

---

## 结尾 · 动手练习

**任务**：在你的电脑上实现一个“两 Agent 协作”小系统。

要求：

1. 复用上面第 5 节的 `SharedMemory`（可以复制粘贴）。
2. 写两个函数 `agent_researcher(mem)` 和 `agent_writer(mem)`：
   - `agent_researcher` 往 namespace=`'demo'` 里 `write('finding', '...')` 写一条“研究结论”，并 `post` 一条消息说“我完成了”。
   - `agent_writer` 从同一个 namespace 里 `read('finding')`，并 `post` 一条消息，内容是“我基于 <finding> 写了段落”。
3. 用两个 `threading.Thread` 同时启动这两个函数，`join` 之后打印 `mem.history('demo')`。
4. 观察到什么？如果 writer 先跑，会发生什么？把 writer 的读取逻辑改成“如果没读到就等 0.1 秒重试”，再看一次结果。

**考察点**：共享记忆的读写顺序、竞态条件的真实感受、以及“等待-重试”这种最基本的同步策略。

```python
import threading
import time

class SharedMemory:
    """带命名空间和线程安全的多 Agent 共享记忆。"""

    def __init__(self):
        self._lock = threading.Lock()
        self._kv = {}
        self._log = []

    def write(self, namespace, key, value):
        with self._lock:
            self._kv[(namespace, key)] = value

    def read(self, namespace, key, default=None):
        with self._lock:
            return self._kv.get((namespace, key), default)

    def post(self, namespace, sender, content):
        with self._lock:
            self._log.append({
                'namespace': namespace,
                'sender': sender,
                'time': time.time(),
                'content': content,
            })

    def history(self, namespace):
        with self._lock:
            return [m for m in self._log if m['namespace'] == namespace]


def agent_researcher(mem):
    time.sleep(0.05)  # 模拟一点工作耗时
    mem.write('demo', 'finding', 'dict 在 Python 3.7+ 中保持插入顺序')
    mem.post('demo', 'researcher', '研究完成')


def agent_writer(mem):
    # 简单重试：最多等 1 秒
    finding = None
    for _ in range(10):
        finding = mem.read('demo', 'finding')
        if finding is not None:
            break
        time.sleep(0.1)
    mem.post('demo', 'writer', f'基于{finding!r}写了一段')


if __name__ == '__main__':
    mem = SharedMemory()
    t1 = threading.Thread(target=agent_researcher, args=(mem,))
    t2 = threading.Thread(target=agent_writer, args=(mem,))
    t1.start(); t2.start()
    t1.join(); t2.join()

    for msg in mem.history('demo'):
        print(f"[{msg['sender']}] {msg['content']}")
```


---

## 本课题目

### single_choice · None



- [A] 控制权被转移给另一个 Agent，由后者继续完成后续交互
- [B] 多个 Agent 同时运行并各自独立回答同一问题
- [C] 接待 Agent 仍持续监听但不再产生任何输出
- [D] 两个 Agent 共享同一份代码但使用不同的提示词

**参考答案**：0

**解析**：交接（handoff）的本质是把会话控制权转移给另一个 Agent，由接收方继续处理；同时运行、不再输出或仅共享代码都不等同于控制权转移。

### single_choice · None



- [A] 把工具返回值当作普通文本拼接到回复中
- [B] 通过工具调用触发一次 Agent 交接
- [C] 重新初始化整个多 Agent 系统
- [D] 并行调用退款 Agent 与主 Agent 轮流作答

**参考答案**：1

**解析**：当工具调用的作用是把控制权指向另一个 Agent 时，这是典型的交接机制；它并不要求重新初始化系统，也不是把返回值当文本拼接。

### single_choice · None



- [A] 让接收 Agent 重新向用户询问全部信息
- [B] 把已有的消息历史一并传递给接收 Agent
- [C] 只传递系统提示词，不传历史
- [D] 让原 Agent 在后台继续生成回复并转发

**参考答案**：1

**解析**：把消息历史随交接一起传递，可以让接收方无缝继续对话；反复询问用户或让原 Agent 后台转发都不属于真正的交接。

### single_choice · None



- [A] 用户会收到多条可能互相矛盾的回复
- [B] 系统会立即崩溃
- [C] 接收 Agent 无法读取任何历史
- [D] 工具调用会失效

**参考答案**：0

**解析**：这不是交接而是并行输出，用户可能收到多个不一致的回复，违背了交接中控制权单一的原则。

### single_choice · None



- [A] 用于计算模型的温度参数
- [B] 用于决定下一个回复由哪个 Agent 生成
- [C] 用于压缩历史消息
- [D] 用于选择向量数据库

**参考答案**：1

**解析**：跟踪当前负责方可以在交接后正确路由后续输入，避免多个 Agent 同时响应或无人响应。

### single_choice · None



- [A] 用户问题跨越多个领域且需要不同专家依次处理
- [B] 用户问题简单到可由当前 Agent 直接回答
- [C] 用户明确要求转接给人工或特定角色
- [D] 当前 Agent 缺少完成任务的必要工具

**参考答案**：1

**解析**：能直接回答的问题无需交接；剩余选项都是交接的合理场景，因为需要不同能力或角色。

### single_choice · None



- [A] 交接后控制权转移，而工具调用后原 Agent 通常继续主导
- [B] 工具调用不能返回任何文本
- [C] 交接只能发生一次
- [D] 工具调用必须使用不同的模型

**参考答案**：0

**解析**：作为工具调用时，被调用的 Agent 只是完成一次子任务并把结果返回；交接则是把会话主导权整体转移。

### single_choice · None



- [A] 模型可能过于轻易地触发交接，把本可回答的问题推给别人
- [B] 模型会完全忽略该工具
- [C] 系统会丢失所有历史
- [D] 接收 Agent 会自动拒绝

**参考答案**：0

**解析**：把「无法回答」作为触发条件容易让模型在不确定时过早交接，需要在提示或策略中加以约束。

### single_choice · None



- [A] 永远停留在第一个接收的 Agent
- [B] 根据当前问题再次判断是否需要交接
- [C] 把两个问题合并成一个回答
- [D] 拒绝回答第二个问题

**参考答案**：1

**解析**：用户话题可能变化，交接策略应允许根据当前问题重新评估目标 Agent，而不是一次交接后永久固定。

### single_choice · None



- [A] 提高模型温度
- [B] 增加历史消息长度
- [C] 明确各 Agent 的职责边界并限制交接次数
- [D] 把两个 Agent 合并成同一个模型

**参考答案**：2

**解析**：职责不清是来回推诿的常见根因，配合最大交接次数可以有效终止循环；调节温度或加长历史都无助于解决。

### single_choice · None



- [A] 原 Agent 与接收 Agent 都各自输出一条完整回复
- [B] 只有接收 Agent 输出面向用户的回复
- [C] 由系统随机选择一个 Agent 输出
- [D] 两个 Agent 都不输出，等待用户再次提问

**参考答案**：1

**解析**：交接后由接收方统一对外输出，可以避免重复和矛盾；双方都输出或随机选择都会造成混乱。

### single_choice · None



- [A] 接收 Agent 无法区分这是工具结果还是用户输入
- [B] 系统会拒绝生成回复
- [C] 模型会自动切换为并行模式
- [D] 工具调用次数会减少

**参考答案**：0

**解析**：消息角色和来源影响模型对上下文的理解；把工具结果混成普通文本会破坏语义结构，使接收方难以正确解读。

### single_choice · None



- [A] 交接之后原 Agent 仍负责最终输出，只是辅助新 Agent
- [B] 并行协作中每个 Agent 都必须知道其他 Agent 的完整历史
- [C] 交接强调控制权在同一时刻只由一方掌握并发生转移
- [D] 两者在实现上完全等价，只是命名不同

**参考答案**：2

**解析**：交接的核心是控制权的转移，通常同一时刻只有一方掌握会话主导权；并行协作则可能多个 Agent 同时工作，两者不等价。

### single_choice · None



- [A] 系统会拒绝执行交接
- [B] 接收 Agent 的回答会与原任务脱节或重复提问
- [C] 接收 Agent 会自动拒绝处理并交还给原 Agent
- [D] 交接会变成并行执行

**参考答案**：1

**解析**：上下文是交接能否顺畅的关键之一；缺少上下文会导致接收方无法理解前因后果，从而答非所问或重复询问。

### single_choice · None



- [A] 避免两个 Agent 同时向用户输出造成混乱
- [B] 减少系统的内存占用
- [C] 让原 Agent 能继续并行处理其他用户
- [D] 强制所有 Agent 使用相同的模型

**参考答案**：0

**解析**：控制权已经转移，如果原 Agent 仍输出，用户会收到冲突或重复的回复；这一约束主要是为了避免双头输出。

### single_choice · None



- [A] 当前 Agent 的回复字数超过阈值
- [B] 用户连续发送了两条消息
- [C] 当前 Agent 无法可靠完成用户请求，而另一个 Agent 更擅长该领域
- [D] 系统运行时间超过五分钟

**参考答案**：2

**解析**：交接应基于能力匹配：当前 Agent 不擅长而另一 Agent 更合适时才是合理触发；字数、消息条数或运行时间都不是充分理由。

### single_choice · None



- [A] 上下文溢出
- [B] 交接循环
- [C] 工具调用失败
- [D] 模型幻觉

**参考答案**：1

**解析**：互相推诿导致控制权来回转移，属于交接循环，需要通过明确的归属规则或最大交接次数来规避。

### single_choice · None



- [A] 禁止任何 Agent 发起交接
- [B] 每次交接后清空全部历史
- [C] 设置最大交接次数并在超限时由兜底逻辑处理
- [D] 让所有 Agent 共用一个系统提示词

**参考答案**：2

**解析**：设置最大交接次数并配合兜底处理，可以在保留交接能力的同时避免无限循环；完全禁止或清空历史都会带来其他问题。

### single_choice · None



- [A] 让接收方明确自己的角色与任务边界
- [B] 减少模型的 token 消耗
- [C] 使交接变成同步调用
- [D] 避免使用工具调用

**参考答案**：0

**解析**：明确目标 Agent 与用户输入是两种不同信息，分开传递有助于接收方理解自己该承担的角色和职责。

### single_choice · None



- [A] 用户问题中出现「合同」「赔偿」等关键词
- [B] 主 Agent 对该问题的置信度很低
- [C] 法务 Agent 当前在线
- [D] 用户消息长度恰好是 42 个字符

**参考答案**：3

**解析**：消息长度与是否需要法律支持没有因果关系，用它作为交接依据属于偶然特征，不可靠。

### single_choice · None



- [A] 共享内存就是让所有 agent 直接操作各自的私有变量，通过命名巧合实现互通
- [B] 共享内存是一块被多个 agent 共同访问、需要协调读写以避免冲突的状态存储区域
- [C] 共享内存一经创建，任何 agent 都可以随意修改且无需任何同步机制
- [D] 共享内存只能被一个 agent 访问，其他 agent 必须通过消息队列间接读取

**参考答案**：1

**解析**：共享内存的核心是「多访问者 + 同一份状态 + 需要协调」。A 只是巧合通信不是共享；C 忽略了并发写冲突；D 描述的是排他/间接访问，与共享内存定义相反。

### single_choice · None



- [A] 7，因为两个 agent 的写入会被系统自动合并
- [B] 6，因为两次加 1 都会生效
- [C] 5，因为写回被拒绝
- [D] 可能是 5 或 6，取决于是否发生读-改-写竞态覆盖

**参考答案**：3

**解析**：若两次读-改-写交错执行（都读到 5 再各自写 6），结果为 6 但丢失一次更新语义；若其中一个写入被后续覆盖或时序不同，可能仅保留 6 或退化为 5 的情况，关键是竞态导致结果不确定。

### multi_choice · None



- [A] 并发读写引发的竞态条件
- [B] 写入后其他 agent 的可见性与顺序
- [C] 共享数据的整体容量是否足够大
- [D] 基于旧快照写回导致的丢失更新

**参考答案**：[0, 1, 3]

**解析**：竞态、可见性、丢失更新都是共享内存的核心正确性问题。容量属于资源/性能范畴，不是正确性本身。

### multi_choice · None



- [A] 将共享状态按领域拆分为多个独立区域，减少同一把锁的争用
- [B] 对计数类更新使用原子操作而非读-改-写
- [C] 所有 agent 都先读取整份快照再整体写回
- [D] 采用乐观并发控制，在提交前检测版本是否被修改

**参考答案**：[0, 1, 3]

**解析**：拆分区域、原子操作、乐观并发（版本检测）都能降低冲突或检测冲突。C 的整快照写回正是丢失更新的典型来源，会加剧问题。

### multi_choice · None



- [A] 加锁能保证临界区互斥，但会带来等待和潜在死锁风险
- [B] 只要加了锁，就一定不会有任何并发问题
- [C] 锁的粒度越粗，通常并发度越低
- [D] 持锁期间执行耗时操作会放大其他 agent 的等待时间

**参考答案**：[0, 2, 3]

**解析**：锁保证互斥但非万能（不能解决一致性与死锁等全部问题），粗粒度降低并发度，长持锁放大等待。B 是绝对化误解。

### multi_choice · None



- [A] 强一致通常需要更多同步开销，可能降低可用性或延迟
- [B] 最终一致允许短时间内 agent 看到不同数据
- [C] 强一致和最终一致可以完全同时零成本实现
- [D] 一致性模型的选择会影响系统的响应时间和容错能力

**参考答案**：[0, 1, 3]

**解析**：一致性模型存在权衡：强一致代价高，最终一致有窗口期。一致性选择确实影响延迟与容错。C 与权衡本质矛盾。

### fill_blank · None



**参考答案**：["竞态", "竞态条件", "race", "race condition"]

**解析**：多个访问者以不确定顺序操作同一份数据、结果依赖时序，就是竞态（race condition）。

### fill_blank · None



**参考答案**：["临界", "临界区", "critical", "critical section"]

**解析**：临界区指一次只允许一个执行体进入的代码段，用锁等机制保护。

### fill_blank · None



**参考答案**：["原子", "原子性", "atomic", "atomicity"]

**解析**：不可分割、无中间可见状态即原子性，是并发正确性的基础性质之一。

### code_reading · None



**参考答案**：通常小于 200000，且每次运行结果可能不同。因为 `counter = counter + 1` 不是原子操作，包含读取、加一、写回三步，两个线程交错执行会互相覆盖，导致部分自增丢失。

**解析**：该代码演示了共享变量上的读-改-写竞态：两个线程可能同时读到相同的旧值再各自加一写回，造成丢失更新，因此结果不确定且一般小于预期。

### code_reading · None



**参考答案**：输出稳定为 200000。`with lock` 使读-改-写序列成为临界区，保证同一时刻只有一个线程执行该序列，消除了竞态和丢失更新。

**解析**：加锁把非原子的读-改-写包裹为互斥临界区，使自增不会交错，因此计数结果确定且正确。

### scenario · None



**解析**：问题根源是取任务与写回都不是原子操作，存在竞态。改造应让「取出任务」成为原子操作（加锁或使用并发安全队列），并对状态写回采用互斥或版本检测，避免丢失更新。

### single_choice · None



- [A] 给每个 agent 分配更快的 CPU
- [B] 在共享内存读写时使用锁或其他互斥/原子机制
- [C] 增加共享内存的总容量
- [D] 让所有 agent 只在启动时访问一次共享内存

**参考答案**：1

**解析**：竞态的本质是读-改-写不是原子操作，需通过锁、原子操作或事务来保证临界区互斥。增加资源或容量都不解决并发覆盖问题。

### single_choice · None



- [A] 共享内存耦合更松，消息传递耦合更紧
- [B] 共享内存需要访问者自己处理同步，消息传递把同步隐含在收发语义中
- [C] 消息传递一定比共享内存快，因为它不需要锁
- [D] 共享内存无法在多个 agent 之间传递复杂结构，只能传整数

**参考答案**：1

**解析**：共享内存由访问者显式处理并发协调；消息传递通过通道/队列的收发语义天然避免了直接共享写冲突（但仍有其他一致性问题）。A 把耦合方向说反；C、D 为绝对化错误。

### single_choice · None



- [A] 副本之间出现不一致，读取到过期数据
- [B] 内存占用变小导致数据丢失
- [C] 同步次数减少使网络带宽耗尽
- [D] agent 数量增加使单机 CPU 降频

**参考答案**：0

**解析**：副本 + 延迟同步会带来一致性与可见性延迟问题（读到旧值）。B、C、D 与复制同步机制的典型风险无关，属于编造后果。

### single_choice · None



- [A] 共享内存的物理地址是否可被操作系统访问
- [B] 某 agent 的写入何时、以何顺序能被其他 agent 观察到
- [C] 共享内存是否够大以容纳所有 agent 的数据
- [D] agent 是否能被其他 agent 的身份认证系统识别

**参考答案**：1

**解析**：可见性关注写入后其他访问者能否及时看到以及看到哪个版本，与内存地址、容量、身份认证都无关。

### single_choice · None



- [A] 一个普通 Python list，各 agent 用 list.pop(0) 取任务
- [B] 一个普通字典，各 agent 用同名键读写
- [C] 带锁的队列结构，取出操作具备原子性
- [D] 一个全局变量，各 agent 直接赋值覆盖

**参考答案**：2

**解析**：任务队列需要并发安全地「取走且只取走一次」，需要原子取出（如带锁队列）。普通 list.pop(0)、字典覆盖、全局变量赋值都存在竞态或语义错误。

### single_choice · None



- [A] A 字段类型不合法被拒绝
- [B] 两个 agent 各自基于旧快照整体覆盖写回，导致彼此字段互相覆盖
- [C] 共享内存容量不足只保留一个字段
- [D] 字段名冲突使系统随机丢弃一个

**参考答案**：1

**解析**：整快照覆盖写会把对方基于旧快照的写覆盖掉，产生丢失更新。类型、容量、字段名都不会导致这种随机字段丢失。

### single_choice · None



- [A] 操作结果一定是整数
- [B] 操作完成后内存被清空
- [C] 操作对外表现为不可分割，中间状态不会被其他访问者观察到
- [D] 操作只能在单线程程序中执行

**参考答案**：2

**解析**：原子性指操作不可分割、无中间可见状态。与数据类型、是否清空内存、是否单线程无关。

### single_choice · None



- [A] 缩小共享区域的粒度，减少锁的持有时间和冲突范围
- [B] 把所有共享数据改为全局变量直接访问
- [C] 禁止任何 agent 读取共享数据
- [D] 把共享数据复制到每个 agent 并不再同步

**参考答案**：0

**解析**：细化锁粒度可降低冲突是并发优化的常见手段。B 会加剧竞态；C 破坏功能；D 会造成严重不一致。
