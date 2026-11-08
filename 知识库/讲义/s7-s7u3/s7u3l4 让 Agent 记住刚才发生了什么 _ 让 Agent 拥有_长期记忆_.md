# s7u3l4 让 Agent 记住刚才发生了什么 / 让 Agent 拥有"长期记忆"

> 来源 `content/lessons/s7u3l4.json`

## agent.pattern.memory_short

# agent.pattern.memory_short：让 Agent 记住刚才发生了什么

> **一句话直觉**：Agent（智能体）每一轮调用都是「无状态」的——模型不记得上一句话说了什么；短期记忆（short-term memory）就是我们在调用之间手动维护的「最近对话窗口」，让多轮对话、工具调用和任务续跑成为可能。

---

## 1. 为什么要学「短期记忆」？

大语言模型（LLM, Large Language Model）API 是**无状态**的（stateless）：你每次 `client.chat(...)` 传入的消息列表就是全部上下文，模型不会自己保留历史。

因此一个「Agent」想要像人类一样多轮对话、记住上一步调用了哪个工具、上一步的参数是什么，就必须由我们**在外层维护一份消息列表**。这份列表就是「短期记忆」。

- **没有短期记忆**：Agent 是「失忆的金鱼」，每轮都从零开始。
- **有短期记忆**：Agent 能指代消解（「它」「刚才那个文件」）、能接续工具调用结果、能完成多步任务。
- **短期记忆 vs 长期记忆**：短期 = 当前会话窗口内的消息；长期（long-term）= 跨会话持久化的向量库 / 数据库。本节只讲短期。

一句话：**短期记忆 = 你手动传给模型的 messages 列表 + 有效的裁剪策略**。

---

## 2. 最简形态：一个 `list` 就够了

Python 的 `list` 就是最天然的短期记忆容器。每条消息是一个 `dict`（OpenAI 风格）或一个对象。

```python
# 最简短期记忆：一个 list[dict]
messages = [
    {"role": "system", "content": "你是一个简洁的助手。"},
]

def chat(history, user_input):
    # 1) 把用户输入追加进记忆
    history.append({"role": "user", "content": user_input})
    # 2) 假装调用模型（此处用占位函数替代真实 API）
    reply = fake_llm(history)
    # 3) 把模型回复也追加进记忆，供下一轮使用
    history.append({"role": "assistant", "content": reply})
    return reply

def fake_llm(history):
    # 演示用：回显最后一条用户消息
    return f"你说的是：{history[-2]['content']}"

print(chat(messages, "你好"))
print(chat(messages, "我上句说了什么？"))
print(messages)  # 可以看到完整的历史被保留了
```

**关键点**：
- 每条消息有 `role`（system / user / assistant / tool）和 `content`。
- 记忆是**逐步 append**的，不是覆盖的。
- 模型只看到你传进去的 `messages`，看不到「上一次调用」。

---

## 3. 用「双端队列 + 滑动窗口」限制长度

记忆不能无限增长：模型有上下文窗口（context window）上限，token 越多越贵、越慢。

最常见的做法是**保留最近 N 条消息**（sliding window）。Python 的 `collections.deque` 带 `maxlen`，天然适合做这个。

```python
from collections import deque

class ShortTermMemory:
    def __init__(self, max_turns: int = 5, system_prompt: str = "你是一个助手。"):
        # 注意：system 消息通常「固定保留」，不参与淘汰
        self.system = {"role": "system", "content": system_prompt}
        # maxlen 表示最多存 2*max_turns 条（一问一答算一轮）
        self.history = deque(maxlen=max_turns * 2)

    def add_user(self, text: str):
        self.history.append({"role": "user", "content": text})

    def add_assistant(self, text: str):
        self.history.append({"role": "assistant", "content": text})

    def to_messages(self) -> list[dict]:
        # 每次拼装：system 永远在最前，然后才是窗口内的历史
        return [self.system, *self.history]

mem = ShortTermMemory(max_turns=2)
mem.add_user("我叫小明")
mem.add_assistant("你好，小明！")
mem.add_user("我今年 10 岁")
mem.add_assistant("记住了。")
mem.add_user("我最喜欢的颜色是蓝色")
mem.add_assistant("好的。")
mem.add_user("我叫什么？")  # 超过窗口，早期信息被挤掉

for m in mem.to_messages():
    print(m)
```

**关键点**：
- `deque(maxlen=...)` 自动丢弃最老的条目，**O(1)** 效率。
- `system` 消息通常固定在队首，不参与淘汰。
- 窗口的「容量」应按**轮数（turn）**而不是条数思考，避免 system / tool 消息打乱节奏。

---

## 4. 进阶：把「工具调用」也纳入记忆

真实 Agent 常常调用工具（tool use）。工具调用的请求与结果也是记忆的一部分，否则模型会重复调用或找不到结果。

```python
import json

class ToolAwareMemory(ShortTermMemory):
    def add_tool_call(self, call_id: str, name: str, args: dict):
        # assistant 发起的 tool_call
        self.history.append({
            "role": "assistant",
            "content": None,
            "tool_calls": [{
                "id": call_id,
                "type": "function",
                "function": {"name": name, "arguments": json.dumps(args)},
            }],
        })

    def add_tool_result(self, call_id: str, result: str):
        # 工具执行结果，用 tool_call_id 关联
        self.history.append({
            "role": "tool",
            "tool_call_id": call_id,
            "content": result,
        })

mem = ToolAwareMemory(max_turns=3)
mem.add_user("北京现在天气如何？")
mem.add_tool_call("call_1", "get_weather", {"city": "北京"})
mem.add_tool_result("call_1", "晴，25℃")
mem.add_assistant("北京现在晴，25℃。")

for m in mem.to_messages():
    print(m)
```

**关键点**：
- `tool_call.id` 与 `tool_call_id` **必须配对**，否则 API 会报错。
- 裁剪窗口时，不能把某对 (tool_call, tool_result) 切成两半——这是最常见的坑。

---

## 5. 工程化：什么时候该「压缩」而不是「截断」

滑动窗口简单粗暴，但会丢失早期重要信息（如用户姓名）。

工程上常见策略：

1. **滑动窗口**：只保留最近 K 轮。简单、便宜。
2. **摘要压缩（summarization）**：把最老的若干轮交给模型生成一段摘要，替换掉原始消息。
3. **混合策略**：system + 摘要 + 最近 K 轮。

```python
def compress(memory: ShortTermMemory, llm_summarize) -> str:
    """把当前所有历史压成一句摘要。"""
    text = "\n".join(f"{m['role']}: {m['content']}" for m in memory.history)
    return llm_summarize(text)

# 示意：真实场景下 llm_summarize 会调一次模型
def fake_summarize(text):
    return "用户叫小明，10 岁，喜欢蓝色。"

summary = compress(mem, fake_summarize)
new_messages = [mem.system, {"role": "system", "content": f"历史摘要：{summary}"}]
print(new_messages)
```

**关键点**：
- 压缩能保留「事实」，代价是一次额外模型调用。
- 摘要本身也可能丢信息，需要定期回到窗口中的原文。
- 生产环境通常还会对记忆做**持久化**（如 SQLite / Redis），下次会话再加载。

---

## 小结

| 层级 | 结构 | 适用场景 |
|---|---|---|
| 最简 | `list[dict]` + append | Demo、单轮任务 |
| 滑窗 | `deque(maxlen=N)` | 多轮对话、成本敏感 |
| 工具感知 | 带 `tool_calls` / `tool_call_id` | Function Calling Agent |
| 摘要 | window + LLM summarize | 长会话、需保留早期事实 |

**核心心智模型**：短期记忆不是模型的能力，而是**你在调用之间维护的一个列表**；你要为它的**长度、结构、淘汰规则**负责。

---

## 动手练习

**任务**：实现一个 `ChatAgent` 类，满足：

1. 内部持有 `ShortTermMemory`，窗口大小为 **3 轮**，`system` prompt 固定为「你是一个中文客服助手。」
2. 提供一个 `reply(user_text: str) -> str` 方法；由于本节不依赖任何真实 LLM，**模拟模型**只需返回：
   ```
   "[收到] " + user_text + " | 记忆中共有 N 轮对话"
   ```
   其中 N 是当前窗口中实际存有的轮数。
3. 连续调用 `reply` 对话 6 次，最后打印 `to_messages()` 的输出，验证：
   - `system` 始终在第一行；
   - 记忆里最多只有 3 轮 user/assistant 消息对；
   - 更早的对话已经被淘汰。
4. **加分项**：为淘汰的历史生成一句「摘要」消息，插在 `system` 之后，并在最终 `print` 中展示出来。

**提交形式**：一个可 `python agent.py` 直接运行的脚本，末尾用注释写出你观察到窗口生效的证据（哪几轮被丢弃了）。

```python
from collections import deque

class ShortTermMemory:
    def __init__(self, max_turns=3, system_prompt="你是一个中文客服助手。"):
        self.system = {"role": "system", "content": system_prompt}
        self.max_turns = max_turns
        self.history = deque(maxlen=max_turns * 2)

    def add_user(self, text):
        self.history.append({"role": "user", "content": text})

    def add_assistant(self, text):
        self.history.append({"role": "assistant", "content": text})

    def turn_count(self):
        return sum(1 for m in self.history if m["role"] == "user")

    def to_messages(self):
        return [self.system, *self.history]

class ChatAgent:
    def __init__(self):
        self.memory = ShortTermMemory(max_turns=3)

    def reply(self, user_text):
        self.memory.add_user(user_text)
        # 模拟模型：真实场景下这里会调用 LLM
        n = self.memory.turn_count()
        answer = f"[收到] {user_text} | 记忆中共有 {n} 轮对话"
        self.memory.add_assistant(answer)
        return answer

if __name__ == "__main__":
    agent = ChatAgent()
    for i in range(1, 7):
        print(agent.reply(f"第 {i} 次提问"))
    print("\n--- 最终记忆 ---")
    for m in agent.memory.to_messages():
        print(m)
```

## agent.pattern.memory_long

# agent.pattern.memory_long：让 Agent 拥有"长期记忆"

> **一句话直觉**：如果你每次问 AI 助手都要重新介绍自己，你一定会烦——`memory_long` 就是让 Agent 把"你是谁、聊过什么、知道什么"跨会话持久保存下来的那套机制。

---

## 1. 为什么要学它？

大语言模型（LLM, Large Language Model）有一个硬伤：**无状态（stateless）**。它的每次调用都像失忆症患者醒来，只能看见你这次塞进去的上下文（context），一旦会话结束，之前所有对话全都烟消云散。

短期记忆（short-term memory）靠的是把当前对话历史一股脑塞进上下文窗口（context window）——简单，但有几个致命问题：

1. **窗口有限**：即使是 128K token 的模型，也装不下你和用户一年的对话。
2. **成本线性上涨**：每次都要把全部历史重新发一遍，token 费越滚越多。
3. **无法跨会话**：今天聊过的偏好，明天开新窗口就归零了。

**长期记忆（long-term memory）** 就是为了解决这三件事而出现的：把对话中值得留下的信息提取出来，存储到外部（向量数据库、键值存储、文件），在需要时按相关性检索回来，拼进新的上下文。

这是所有"像样的" Agent 系统的核心组件之一。

---

## 2. 长期记忆的四个核心动作

长期记忆不是"把对话原文存下来"那么粗暴，它要经过一条**流水线**：

| 阶段 | 英文 | 做什么 |
|------|------|--------|
| 提取 | extract | 从对话里挑出值得长期记住的事实/偏好 |
| 存储 | store | 把提取结果写入外部存储（可带 embedding） |
| 检索 | retrieve | 新对话开始时按相关性获取相关记忆 |
| 注入 | inject | 把检索到的记忆拼进 prompt |

下面我们用最朴素的方式实现这四步（用 Python 标准库，不依赖任何第三方包）。

```python
import json
import re

# ---------- 阶段 1：提取（extract） ----------
# 用规则模拟 LLM 的"记忆提取"：只挑含关键词的句子
def extract_memories(utterance: str) -> list[str]:
    """从一段话中抽取值得长期记住的句子。"""
    keywords = ["我叫", "我的", "我喜欢", "我不喜欢", "我住在", "我是"]
    sentences = re.split(r"[。！？!?.]", utterance)
    return [s.strip() for s in sentences if s.strip() and any(k in s for k in keywords)]

# ---------- 阶段 2：存储（store） ----------
# 用 JSON 文件当作简易持久层
class LongTermStore:
    def __init__(self, path: str = "memory.json") -> None:
        self.path = path
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.data: list[str] = json.load(f)
        except FileNotFoundError:
            self.data = []

    def add(self, items: list[str]) -> None:
        for x in items:
            if x not in self.data:       # 简单去重
                self.data.append(x)
        self._flush()

    def _flush(self) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

# ---------- 阶段 3：检索（retrieve） ----------
# 这里用一个极简的"关键词重合度"打分，真实工程会用 embedding
def retrieve(store: LongTermStore, query: str, top_k: int = 3) -> list[str]:
    q_tokens = set(query)
    scored = [(len(q_tokens & set(m)), m) for m in store.data]
    scored.sort(reverse=True)
    return [m for s, m in scored[:top_k] if s > 0]

# ---------- 阶段 4：注入（inject） ----------
def build_prompt(user_query: str, memories: list[str]) -> str:
    if not memories:
        return user_query
    joined = "\n".join(f"- {m}" for m in memories)
    return f"已知用户信息：\n{joined}\n\n用户问：{user_query}"
```

**要点**：生产环境里，阶段 1 交给 LLM 做（让它返回 JSON 列表），阶段 2 用向量数据库（Chroma/Pinecone/pgvector），阶段 3 用 embedding 相似度做检索。骨架完全一样。

---

## 3. 一次完整的"写入 + 读取"演示

把四大动作串起来看，逻辑就非常直观了——**第一轮对话产生记忆，第二轮对话消费记忆**。

```python
store = LongTermStore("memory.json")

# 第一轮：用户说了个人信息
turn1 = "我叫小林。我住在杭州。我喜欢喝美式咖啡。"
store.add(extract_memories(turn1))
print("存储后：", store.data)
# => ['我叫小林', '我住在杭州', '我喜欢喝美式咖啡']

# 第二次会话（新进程，用户换了话题）
store2 = LongTermStore("memory.json")            # 重新加载，模拟新会话
turn2 = "帮我推荐一家附近适合办公的咖啡馆？"
memories = retrieve(store2, turn2, top_k=2)
print("检索到：", memories)
print(build_prompt(turn2, memories))
```

注意 $	exttt{store2}$ 是重新 `LongTermStore("memory.json")` 出来的，但这不关键——关键是文件在磁盘上，进程重启后记忆仍在。这就是长期记忆与短期记忆的本质区别。

---

## 4. 长期记忆的三种典型策略

工程中常见三种模式，按需选择：

1. **Profile（画像式）**
   只存"事实"：姓名、职业、偏好。适合客服、个性化助手。
   优点：token 省；缺点：丢失语境。

2. **Episodic（事件式）**
   存"发生过的事"：某天讨论过某 bug、某次会议结论。
   优点：能回答"我们上次聊到哪了"；缺点：需要时间戳和去重。

3. **Summary（摘要式）**
   把历史压缩成一段滚动摘要，每次新对话结束就更新它。
   优点：无上限；缺点：细节会丢，且需要 LLM 参与。

实际系统往往是三者的混合：画像常驻 prompt 顶部，事件按相关性检索，摘要兜底。

---

## 5. 工程上必须处理的三件事

- **去重**：用户会说"我住在杭州"十遍，不能存十条。用键值合并（key = 事实类型，value = 内容）。
- **时效**：住址变了，旧地址要失效。给每条记忆加 `updated_at` 字段，检索时优先新版本。
- **隐私**：长期记忆里可能有 PII（personally identifiable information），要能按用户删除（GDPR 的"被遗忘权"）。

下面这段代码演示"覆盖式"更新——同一个 key 只保留最新值：

```python
from datetime import datetime

class KeyedMemory:
    """按 key 覆盖的长期记忆，解决去重与时效问题。"""
    def __init__(self) -> None:
        self.data: dict[str, dict] = {}

    def upsert(self, key: str, value: str) -> None:
        self.data[key] = {"value": value, "updated_at": datetime.now().isoformat()}

    def get(self, key: str) -> str | None:
        item = self.data.get(key)
        return item["value"] if item else None

mem = KeyedMemory()
mem.upsert("city", "杭州")
mem.upsert("city", "上海")   # 覆盖旧地址
print(mem.get("city"))        # => 上海
```

---

## 6. 动手练习

**任务**：写一个 `personal_agent.py`，实现一个带长期记忆的命令行小助手，要求：

1. 用循环不断 `input()` 读取用户输入，输入 `exit` 退出。
2. 每轮输入先用 `extract_memories()` 看看是否需要写入长期记忆；如果需要，写入 `memory.json`。
3. 每次回答前，先调用 `retrieve()` 拿到相关记忆，用 `build_prompt()` 拼好后打印出来（不需要真的调用 LLM）。
4. **加分项**：把 `LongTermStore` 换成第 5 节的 `KeyedMemory` 版本，让"我住在杭州"这句再被说出来时能覆盖旧地址。

**验收标准**：
- 关闭程序再重启，输入"我住哪儿？"时，能检索出之前存的地址。
- 同一句"我叫小林"说两遍，文件里只有一条。
- 说"我搬到北京了"后，`memory.json` 里的 `city` 只保留最新的值。

**提示**：先让四个函数各自跑通，再串起来。做到第 3 步就已经是一个能用的长期记忆原型了；真正的生产版本只是把"规则"换成"LLM + 向量数据库"，骨架完全一致。


---

## 本课题目

### single_choice · None



- [A] 这是短期记忆的一种落地方式，只能保留有限上下文，超出窗口的信息会丢失
- [B] 这是长期记忆，因为所有历史都会被持久化到数据库
- [C] 这不是任何形式的记忆，只是无状态的单次调用
- [D] 这是摘要式记忆，因为原文被压缩成了要点

**参考答案**：0

**解析**：只保留最近若干轮、超出部分丢弃，属于典型的短期/工作记忆窗口机制，容量有限且旧信息丢失。B 错，因为没有持久化；C 错，因为保留了多轮上下文说明有状态；D 错，因为没有做摘要压缩。

### single_choice · None



- [A] 对历史做裁剪或摘要，只保留与当前任务相关的部分
- [B] 把 temperature 调成 0 以减少 token 消耗
- [C] 把系统提示词删掉，腾出空间给历史
- [D] 改用流式输出，让长历史不再计入上下文

**参考答案**：0

**解析**：上下文超限应从历史管理入手：裁剪、摘要或按相关性筛选。B 错，temperature 不影响输入长度；C 错，删除系统提示会破坏行为约束，且不解决根本问题；D 错，流式输出只是返回方式，不减少输入 token。

### single_choice · None



- [A] 关键约束不会因短期记忆窗口裁剪而丢失
- [B] 系统提示词的 token 不计入上下文长度
- [C] 系统提示词会被模型持久化到磁盘
- [D] 系统提示词能覆盖用户的错误输入

**参考答案**：0

**解析**：把关键约束放在始终保留的位置，可避免被滑动窗口淘汰。B 错，系统提示词同样计入上下文；C 无依据；D 夸大其作用。

### single_choice · None



- [A] 此前只使用了会话内的短期记忆，没有跨会话的持久化与检索
- [B] 模型在夜间被重新训练了
- [C] 用户的偏好属于模型无法理解的类型
- [D] 该会话的 temperature 设置过高

**参考答案**：0

**解析**：会话内有效、跨会话失效正是短期记忆的特征，要跨会话需额外持久化。B、C、D 均无依据。

### single_choice · None



- [A] 长上下文中相关信息可能被稀释，位置与显著性会影响模型对它的利用
- [B] 模型只会读取最后一条消息，其余全部丢弃
- [C] 只要在上下文窗口内，任何位置的信息都会被同等利用
- [D] 历史消息会被自动压缩为哈希值

**参考答案**：0

**解析**：研究表明长上下文中的信息利用并非均匀，位置与显著性有影响，这也是需要检索/摘要的原因之一。B 过于绝对；C 与现象矛盾；D 无依据。

### single_choice · None



- [A] 更贴近模型的实际输入限制，避免长短不一的单轮消息导致超限或浪费
- [B] 能保证语义完整性，绝不会截断一条消息
- [C] 能自动生成对话摘要
- [D] 可以完全替代长期记忆

**参考答案**：0

**解析**：token 计数直接对应模型输入上限，能更精细化控制预算。B 错，按 token 裁剪可能截断消息；C、D 都不是裁剪策略本身的功能。

### single_choice · None



- [A] 历史消息是否被正确保留并传入了本次请求
- [B] 模型的参数量是否足够大
- [C] 是否开启了流式输出
- [D] API 的调用频率是否受限

**参考答案**：0

**解析**：重复询问通常意味着前文未被有效保留/传入。B、C、D 与该症状缺乏直接因果联系。

### single_choice · None



- [A] 请求 token 持续增长，最终超出上下文限制或显著增加成本与延迟
- [B] 模型会自动删除最旧的消息以腾出空间
- [C] 上下文长度不受历史条数影响
- [D] 模型会自动把历史转成长期记忆

**参考答案**：0

**解析**：无裁剪会导致输入持续膨胀直至超限或成本攀升。B 错，消息管理由调用方负责；C、D 无依据。

### single_choice · None



- [A] 用一段压缩文本替代早期多轮原文，能在有限 token 内保留大意，但可能丢失细节
- [B] 摘要能无损还原全部历史细节
- [C] 摘要后就可以取消上下文窗口限制
- [D] 摘要只能由用户手动提供

**参考答案**：0

**解析**：摘要是有损压缩，节省 token 但会损失细节。B 错，摘要非无损；C 错，摘要本身也占 token；D 错，摘要可由系统自动生成。

### single_choice · None



- [A] 多步任务中 Agent 忘了前面步骤已确认的参数，导致重复确认或前后矛盾
- [B] Agent 的回答风格偶尔变化
- [C] Agent 的响应速度随并发上升而下降
- [D] Agent 在某次调用中返回了错误码

**参考答案**：0

**解析**：遗忘已确认参数是短期记忆失效的典型表现。B 属风格波动，C 属性能问题，D 属接口错误，均非记忆缺失。

### single_choice · None



- [A] 模型能知晓自己先前的回答，从而保持一致并避免重复
- [B] 可以降低每次请求的 token 数
- [C] 可以让模型绕过系统提示词
- [D] 可以自动形成跨会话的长期记忆

**参考答案**：0

**解析**：助手回复构成模型对自身状态的记录，有助于一致性与避免重复。B 错，保留更多内容会增加 token；C、D 无依据。

### single_choice · None



- [A] 保留任务相关关键信息（如摘要、已确定的参数）并适当放宽近期窗口
- [B] 完全关闭历史，改为每轮独立请求
- [C] 把 temperature 提高以增强模型的记忆
- [D] 把模型换成更小的版本以减少 token

**参考答案**：0

**解析**：解法是在成本与信息保留之间做权衡，保留关键状态并适度放宽窗口。B 会丧失多步状态；C 与记忆无关；D 可能降低能力且不解决历史丢失问题。

### single_choice · None



- [A] 短期记忆通常只在当前会话/任务内有效，长期记忆需要额外的存储与检索机制跨会话保留
- [B] 短期记忆必须写入向量数据库，长期记忆只能放在内存里
- [C] 两者的唯一区别是存储介质是内存还是硬盘
- [D] 只要保存了历史记录，就一定是长期记忆

**参考答案**：0

**解析**：短期记忆服务于当前会话窗口，长期记忆需要持久化和检索以跨会话复用。B 恰好说反；C 把区别简化为介质，忽略了生命周期与检索方式；D 忽略了「跨会话可检索」这一关键。

### single_choice · None



- [A] 短期记忆窗口太窄，关键信息已被挤出上下文
- [B] 模型不具备中文理解能力
- [C] 订单号必须写在系统提示词里才生效
- [D] 地址修改属于模型知识截止日期之后的事件

**参考答案**：0

**解析**：仅保留一轮导致早前信息丢失，是短期记忆窗口过窄的典型症状。B、D 与现象无关；C 是一种做法建议，但根因是历史被丢弃而非存放位置。

### single_choice · None



- [A] 对早期对话生成摘要，并把摘要与最近若干轮原文一起放入上下文
- [B] 把最近若干轮的轮数调小，让上下文更干净
- [C] 每次请求都重新初始化对话，避免历史干扰
- [D] 把历史消息的 role 全部改成 system

**参考答案**：0

**解析**：摘要 + 近期原文是常见的滑动窗口加压缩策略，兼顾长程信息与细节。B 会加剧丢失；C 等于放弃多轮状态；D 改变角色会破坏对话结构语义，并非记忆管理手段。

### single_choice · None



- [A] 顺序性/时序性，模型依赖消息先后顺序理解指代与因果
- [B] 幂等性，重复发送同样的历史不会影响结果
- [C] 可持久性，进程重启后历史自动恢复
- [D] 随机性，顺序对理解没有影响

**参考答案**：0

**解析**：对话历史的顺序承载了指代消解与因果推断信息。B、C 描述的特性并不由追加历史保证；D 与事实相反。

### single_choice · None



- [A] 模型看不到自己此前的承诺与结论，容易自相矛盾或重复提问
- [B] 模型会因此获得更强的推理能力
- [C] 上下文长度会显著增加
- [D] 用户消息的语义会被自动补全

**参考答案**：0

**解析**：助手回复中往往包含已确认的结论与承诺，删除后模型失去自身状态的记录，导致不一致。B 无依据；C 恰恰相反；D 无依据。

### single_choice · None



- [A] 需要在信息保留与 token 成本/延迟之间权衡，窗口过小会丢信息，过大则成本和延迟上升
- [B] 窗口越大越好，应始终使用模型支持的最大上下文
- [C] 窗口越小越好，因为历史越少模型越准确
- [D] 窗口大小与应用场景无关，可按固定值设定

**参考答案**：0

**解析**：窗口大小是成本、延迟与信息完整度的权衡。B 忽略成本与「中间信息被稀释」的效应；C 会丢失关键上下文；D 忽视场景差异。

### single_choice · None



- [A] 无法确定「北京」是出发地还是目的地，也可能忘了要订机票这件事
- [B] 仍能准确完成订票，因为北京已包含在消息中
- [C] 会自动从模型训练数据里推断出目的地
- [D] 会把北京理解为航班号

**参考答案**：0

**解析**：缺少前文时，单条消息的指代与意图无法确定，这是短期记忆缺失的直接体现。B、C、D 都假设了不存在的上下文或能力。

### single_choice · None



- [A] 把用户画像写入向量库，后续会话按相似度检索调用
- [B] 滑动窗口保留最近若干轮对话
- [C] 对早期对话生成摘要后拼接进上下文
- [D] 在上下文即将超限时丢弃最旧的消息

**参考答案**：0

**解析**：向量库持久化 + 跨会话相似度检索属于长期记忆的典型机制。B、C、D 都是会话内上下文窗口的管理方式。

### single_choice · None



- [A] 长期记忆就是把整个对话历史原文一直塞进 prompt
- [B] 长期记忆是把跨会话/跨轮次仍值得保留的信息抽取、存储，并在需要时检索回来
- [C] 长期记忆是模型的参数，训练后不会改变
- [D] 长期记忆只能存用户最近说的 3 句话

**参考答案**：1

**解析**：长期记忆的核心是持久化地保留跨轮次/跨会话仍有价值的信息，并以检索方式按需注入，而非简单堆积全部历史。把全部历史塞进 prompt 属于短期上下文，会带来长度和成本问题；模型参数是权重知识，不是运行时记忆。

### single_choice · None



- [A] 短期上下文通常指当前会话窗口内的消息，长期记忆则跨越会话持续存在
- [B] 短期上下文必须写入数据库，长期记忆只在内存里
- [C] 两者完全等价，只是叫法不同
- [D] 长期记忆一定比短期上下文更准确，所以可以直接丢弃上下文

**参考答案**：0

**解析**：短期上下文局限于当前会话窗口，长期记忆需要持久化存储、可跨会话检索。二者互补，长期记忆检索有噪声，不能完全替代上下文。

### single_choice · None



- [A] 把所有召回的记忆原文无缝拼在用户消息前面，不加任何说明
- [B] 用明确的分隔与标签标明这是「历史记忆」并注明时间，避免模型把它当成当前指令
- [C] 把记忆混进系统提示词里的安全规则部分
- [D] 直接覆盖用户当前的输入

**参考答案**：1

**解析**：记忆注入需与当前指令区分，并标注时间/来源，防止提示注入或时间混淆。直接拼接或混入安全规则容易引发误用。

### multi_choice · None



- [A] 写入时抽取哪些信息值得长期保留
- [B] 如何处理信息更新与冲突（如用户搬家）
- [C] 如何按用户隔离与保护隐私
- [D] 如何控制记忆库规模并做过期淘汰
- [E] 如何把长期记忆直接编译进模型权重

**参考答案**：[0, 1, 2, 3]

**解析**：写入筛选、冲突更新、隔离隐私、规模控制都是长期记忆的核心工程问题。把记忆编译进模型权重不是运行时长期记忆的常规做法。

### multi_choice · None



- [A] 为记忆条目附加时间与来源等元数据
- [B] 在向量召回后加入重排步骤
- [C] 按当前查询改写/扩展再检索
- [D] 把所有历史不加过滤地全量召回后塞进 prompt

**参考答案**：[0, 1, 2]

**解析**：元数据、重排、查询改写都能提高召回质量；全量召回会引入噪声并挤占上下文，反而降低准确度。

### multi_choice · None



- [A] 短期上下文负责当前会话的连贯性，长期记忆补充跨会话的稳定信息
- [B] 长期记忆检索结果也需占用 prompt 预算，应控制数量
- [C] 有了长期记忆就可以完全丢弃当前会话上下文
- [D] 两者可以结合使用，但要注意注入内容与当前指令的区分

**参考答案**：[0, 1, 3]

**解析**：二者互补而非替代。检索记忆占用上下文预算需限额；完全丢弃当前上下文会破坏对话连贯性和指代解析。

### fill_blank · None



**参考答案**：["更新", "update", "覆盖", "冲突消解", "更新/覆盖"]

**解析**：对已存在记忆的处理称为更新（update），常配合冲突消解与时间戳优先策略。

### fill_blank · None



**参考答案**：["用户", "用户ID", "user_id", "userId", "租户", "tenant", "租户ID", "用户/租户"]

**解析**：按用户或租户标识隔离是隐私保护与正确个性化的前提。

### code_reading · None



**参考答案**：解决了信息更新与去重的问题：先抽取关键信息，再按（用户, 键）查询是否已存在，存在则更新（覆盖旧值并刷新时间戳），不存在才插入，从而避免同一事实重复存储、并让新信息覆盖过期信息。

**解析**：该流程展示了「抽取—查重—更新或插入」的典型写入模式，核心是防止重复和保证新信息优先。

### code_reading · None



**参考答案**：先用较大的 top_k 做粗召回以保证相关记忆不被漏掉，再用重排按相关性与时效/重要性精选前 3 条注入。不全部放入的原因是 prompt 预算有限，过多低相关记忆会引入噪声、稀释关键信息并增加成本。

**解析**：体现「粗召回 + 精排 + 限额注入」的经典两阶段检索思想。

### scenario · None



**解析**：问题可能出在写入阶段的抽取或触发条件未覆盖该类信息，或写入后未做冲突更新。需要检查抽取规则、写入时机，并引入时间戳与冲突消解，确保新信息覆盖旧值，同时确认检索能拿到最新条目。

### scenario · None



**解析**：需在存储层按租户/用户分区或打标，在检索层强制附加租户过滤条件，并做权限校验与测试，防止跨租户召回；不能只依赖向量相似度而忽略过滤条件。

### single_choice · None



- [A] 存储成本反而下降
- [B] 检索时噪声大、相关性下降，且可能把过时或矛盾的信息也召回
- [C] 模型会自动过滤掉所有无用信息
- [D] 长期记忆会自动变成模型参数

**参考答案**：1

**解析**：长期记忆需要写入筛选（哪些值得记）与更新（如覆盖过时信息）。全量写入会导致检索库噪声高、召回矛盾信息，降低回答质量。

### single_choice · None



- [A] 只需要写入，不需要检索，因为写入后模型自然能想起来
- [B] 只需要检索，不需要写入，因为历史本来就在日志里
- [C] 写入决定「存什么、存多久、如何合并」，检索决定「当前这轮把哪些记忆取回来用」
- [D] 写入和检索都必须同步阻塞主流程，不能异步

**参考答案**：2

**解析**：写入负责抽取/去重/更新/过期，检索负责按当前查询召回相关记忆。两者职责不同，且写入常可异步进行以避免阻塞响应。

### single_choice · None



- [A] 两条都保留，检索时随机返回一条
- [B] 保留两条，但用时间戳标注，检索时优先返回较新的那条并可覆盖旧值
- [C] 只保留最早的那条，因为先说的更真实
- [D] 两条都删除，避免矛盾

**参考答案**：1

**解析**：长期记忆要处理信息更新：通常用时间戳或冲突消解策略，让较新的信息优先，必要时覆盖或标记旧值失效，而不是随机返回或全部删除。

### single_choice · None



- [A] 让存储文件看起来更整齐
- [B] 支持按时间/来源/用户过滤与排序，并支持冲突消解和过期淘汰
- [C] 提高模型参数量
- [D] 减少必要的检索开销

**参考答案**：1

**解析**：元数据使记忆可过滤、可排序、可去重、可过期，是多用户隔离和冲突消解的基础，而非仅仅为了整齐。

### single_choice · None



- [A] 用户的稳定偏好（如语言、称呼方式）
- [B] 用户长期目标或身份信息
- [C] 当前这一轮临时传入的一段待总结文本
- [D] 过去会话中达成的关键结论

**参考答案**：2

**解析**：当前轮次的临时文本属于工作/短期上下文，处理完通常不需要长期保留。稳定偏好、身份、跨会话结论才是长期记忆的典型对象。

### single_choice · None



- [A] 长期记忆一旦写入就永远不能删除
- [B] 可以基于时间、访问频率或重要性对记忆做衰减和淘汰，避免无限膨胀
- [C] 过期策略只适用于缓存，与长期记忆无关
- [D] 淘汰必须一次删除全部记忆

**参考答案**：1

**解析**：长期记忆库若无淘汰会无限膨胀且噪声上升。基于时间衰减、访问频次、重要性评分等策略可控制规模，是常见工程做法。

### single_choice · None



- [A] 按用户/租户隔离，确保不会把 A 的记忆返回给 B
- [B] 必须一次性召回全部用户的记忆
- [C] 检索结果必须按字母序排列
- [D] 检索只能返回一条记忆

**参考答案**：0

**解析**：多用户场景必须做隔离过滤，否则会造成隐私泄露和错误个性化。其他选项不是关键约束甚至是误解。

### single_choice · None



- [A] 让存储量变小
- [B] 在粗召回结果中按相关性/重要性/时效性等更精细地排序，提高进入 prompt 的记忆质量
- [C] 把长期记忆转成模型参数
- [D] 替代写入阶段

**参考答案**：1

**解析**：向量召回偏重语义相近但精度有限，重排可用更精细的模型或规则（时效、重要性、来源可信度）优化最终注入顺序，提升质量。
