# s7u1l2 LLM 本质是在预测下一个 token（词元） / 传统调用 LLM 时，我们常用**思维链（Chain o / 让大模型学会“边想边做”

> 来源 `content/lessons/s7u1l2.json`

## agent.llm.cot

## 一句话直觉

**思维链（Chain-of-Thought, CoT）** 就是让大语言模型（LLM）在给出最终答案前，先把推理过程一步一步写出来，从而把“猜答案”变成“算答案”。

> 你学它，是因为很多任务（数学、逻辑、多步决策）只要让模型“先想再答”，准确率就会显著提升，而且你不需要重新训练模型。

---

## 1. 为什么需要 CoT：LLM 的“直觉回答”会翻车

LLM 本质是在预测下一个 token（词元）。如果你直接问一个多步问题，它容易凭模式匹配给出一个看似合理但错误的答案。

**关键结论**：把推理过程显式写出来，等于给模型更多中间 token 来“计算”，错误率会下降。

```python
# 演示：直接回答 vs 思维链回答的提示词差异
# 这里不调用真实 API，只展示提示词构造方式

question = "一个商店有 23 个苹果，又进了 17 个，卖掉了 30 个，还剩多少？"

# 方式 A：直接回答（模型容易猜错）
prompt_direct = f"问题：{question}\n答案："

# 方式 B：思维链（让模型先写步骤）
prompt_cot = f"问题：{question}\n请一步一步推理，最后给出答案。\n推理："

print("直接提示词：\n", prompt_direct)
print("CoT 提示词：\n", prompt_cot)
```

---

## 2. 最基础的 CoT：零样本思维链（Zero-shot CoT）

你只需要在提示词里加一句 **“Let's think step by step”**（让我们一步一步思考），就能触发模型的推理行为。这叫零样本思维链。

**关键结论**：零样本 CoT 不需要示例，成本低，适合快速实验。

```python
# 零样本 CoT 的通用模板
def zero_shot_cot(question: str) -> str:
    """构造零样本思维链提示词"""
    return f"问题：{question}\n让我们一步一步思考。\n"

q = "如果 3 个人 3 天喝 3 桶水，那么 9 个人 9 天喝多少桶水？"
print(zero_shot_cot(q))
```

---

## 3. 更稳的 CoT：少样本思维链（Few-shot CoT）

给模型几个“问题 + 推理过程 + 答案”的示例，它就会模仿这种格式。示例越多、越贴近任务，效果通常越好。

**关键结论**：少样本 CoT 比零样本更可控，但会占用更多上下文窗口（context window）。

```python
# 少样本 CoT：用示例教模型“先推理再回答”
few_shot_prompt = """问题：2 个盒子各有 3 个球，一共几个球？
推理：2 个盒子，每个 3 个球，所以 2 × 3 = 6。
答案：6

问题：小明有 5 元，买了 2 支 1.5 元的笔，还剩多少？
推理：2 支笔共 2 × 1.5 = 3 元，5 - 3 = 2 元。
答案：2

问题：一个长方形长 4，宽 3，面积是多少？
推理：面积 = 长 × 宽 = 4 × 3 = 12。
答案：12
"""

print(few_shot_prompt)
```

---

## 4. 工程级 CoT：让模型输出结构化推理 + 答案

在真实 Agent 系统里，你通常需要程序能解析结果。所以要让模型把“推理”和“最终答案”分开，最好用 JSON 或固定标记。

**关键结论**：结构化输出让 CoT 可被下游代码消费，是 Agent 可靠性的基础。

```python
import json
import re

# 模拟一个 LLM 的 CoT 输出（真实场景由 API 返回）
llm_output = """
推理：先算苹果总数 23 + 17 = 40，再减去卖掉 30，得到 40 - 30 = 10。
答案：10
"""

def parse_cot(text: str) -> dict:
    """从 CoT 文本中提取推理和答案"""
    reasoning = re.search(r"推理：(.+)", text)
    answer = re.search(r"答案：(.+)", text)
    return {
        "reasoning": reasoning.group(1).strip() if reasoning else None,
        "answer": answer.group(1).strip() if answer else None,
    }

result = parse_cot(llm_output)
print(json.dumps(result, ensure_ascii=False, indent=2))
```

---

## 5. CoT 的变体与选择建议

- **Zero-shot CoT**：最快，适合简单任务。
- **Few-shot CoT**：更稳，适合格式要求高的任务。
- **Self-Consistency（自洽性）**：让模型多次采样 CoT，投票选多数答案，提升鲁棒性。
- **Least-to-Most（由易到难）**：先拆解子问题，再逐个解决。

**关键结论**：没有万能 CoT，按任务复杂度、成本、延迟选型。

```python
# Self-Consistency 思路：多次采样，投票选多数
# 这里用模拟答案演示投票逻辑
from collections import Counter

simulated_answers = ["10", "10", "12", "10", "12"]
most_common = Counter(simulated_answers).most_common(1)[0][0]
print("多数投票答案：", most_common)
```

---

## 动手练习

**任务**：写一个 Python 脚本 `cot_demo.py`，完成以下功能：

1. 定义一个函数 `build_cot_prompt(question: str) -> str`，生成零样本 CoT 提示词。
2. 定义一个函数 `parse_cot(text: str) -> dict`，从模型输出中提取 `reasoning` 和 `answer`。
3. 用下面这个问题测试：
   > 一个班级有 40 名学生，其中 60% 是女生，女生中有 1/3 参加了数学竞赛，参加竞赛的女生有多少人？
4. 手动模拟一段模型输出（或调用任意 LLM API），用 `parse_cot` 解析并打印结果。

**提交要求**：代码可运行，输出包含推理过程和最终答案。

```python
import re
import json

def build_cot_prompt(question: str) -> str:
    """构造零样本思维链提示词"""
    return f"问题：{question}\n让我们一步一步思考。\n推理："

def parse_cot(text: str) -> dict:
    """从 CoT 文本中提取推理和答案"""
    reasoning = re.search(r"推理：(.+)", text)
    answer = re.search(r"答案：(.+)", text)
    return {
        "reasoning": reasoning.group(1).strip() if reasoning else None,
        "answer": answer.group(1).strip() if answer else None,
    }

question = "一个班级有 40 名学生，其中 60% 是女生，女生中有 1/3 参加了数学竞赛，参加竞赛的女生有多少人？"

# 真实场景中，这里应调用 LLM API 获取输出
# 下面手写一段模拟的 CoT 输出
llm_output = """
推理：40 名学生中 60% 是女生，所以女生有 40 × 0.6 = 24 人。
女生中有 1/3 参加竞赛，所以参赛女生为 24 × (1/3) = 8 人。
答案：8
"""

print("提示词：")
print(build_cot_prompt(question))
print("解析结果：")
print(json.dumps(parse_cot(llm_output), ensure_ascii=False, indent=2))
```

## agent.llm.tot

## 一句话直觉

**思维树（Tree of Thoughts, ToT）** 就是让大语言模型（LLM）像人一样“多想几步、比较几种方案、再决定走哪条路”，而不是一条路走到黑。

---

## 1. 为什么需要 ToT：从“单线思考”到“会搜索的思考”

传统调用 LLM 时，我们常用**思维链（Chain of Thought, CoT）**：让模型一步步推理，最后给答案。但它有两个问题：

1. **一条路走到黑**：如果第一步想错，后面越错越远。
2. **不会回头**：不能比较多个方案、也不能撤销错误分支。

ToT 的核心思想是：把推理过程组织成一棵**树**，每个节点是一个“思考状态（thought）”，每个分支是一种可能思路。模型可以：

- **生成多个候选想法**
- **评估每个想法好不好**
- **选择最有希望的分支继续扩展**
- **必要时回溯（backtrack）**

一句话：**ToT = LLM + 搜索（Search）**。

---

## 2. ToT 的四个关键动作

一个最小可用的 ToT 通常循环做四件事：

1. **扩展（Expand）**：从当前状态生成若干候选下一步。
2. **评估（Evaluate）**：给每个候选打分，或判断“是否可行/是否接近目标”。
3. **选择（Select）**：保留 top-k 个候选，或按概率采样。
4. **回溯/继续（Backtrack / Continue）**：如果某分支失败，就退回上一层换分支。

> 直觉类比：下棋时，你不会只看一步，而是会想“如果我走这里，对手可能怎么走，我再怎么走”。ToT 就是把这种“试算”交给 LLM。

---

## 3. 一个极简 ToT 的工程结构

下面是一个不依赖任何外部库的 ToT 骨架。它用字典模拟“树节点”，用简单的分数函数模拟“评估器”。

```python
# 极简 ToT 骨架：每个节点保存状态、父节点、分数
class ThoughtNode:
    def __init__(self, state, parent=None):
        self.state = state          # 当前思考状态，比如一段文字
        self.parent = parent        # 父节点，用于回溯
        self.children = []          # 子节点
        self.score = 0.0            # 评估分数

    def add_child(self, child):
        self.children.append(child)
        child.parent = self


def tot_search(root_state, expand_fn, evaluate_fn, select_k=2, max_depth=3):
    """
    root_state: 初始状态
    expand_fn: 输入 state，返回若干候选 state
    evaluate_fn: 输入 state，返回分数
    """
    root = ThoughtNode(root_state)
    frontier = [root]  # 当前层待扩展节点

    for depth in range(max_depth):
        next_frontier = []
        for node in frontier:
            # 1. 扩展
            for cand_state in expand_fn(node.state):
                child = ThoughtNode(cand_state)
                node.add_child(child)
                child.score = evaluate_fn(cand_state)
                next_frontier.append(child)
        # 2. 选择：只保留分数最高的 k 个
        next_frontier.sort(key=lambda n: n.score, reverse=True)
        frontier = next_frontier[:select_k]
        if not frontier:
            break

    # 返回当前层分数最高的节点
    best = max(frontier, key=lambda n: n.score)
    return best

# 示例：模拟“凑 24 点”的一步
# 假设状态是 (当前数字列表, 当前表达式)
# 这里只用极简打分：数字越少越接近目标

def expand_fn(state):
    nums, expr = state
    if len(nums) < 2:
        return []
    a, b = nums[0], nums[1]
    rest = nums[2:]
    return [
        (rest + [a + b], f"({expr}) + {b}" if expr else f"{a}+{b}"),
        (rest + [a * b], f"({expr}) * {b}" if expr else f"{a}*{b}"),
        (rest + [abs(a - b)], f"|({expr}) - {b}|" if expr else f"|{a}-{b}|"),
    ]

def evaluate_fn(state):
    nums, expr = state
    if len(nums) == 1 and nums[0] == 24:
        return 100.0
    if len(nums) == 1:
        return -abs(nums[0] - 24)
    return 10.0 / len(nums)  # 数字越少，分数越高

best = tot_search(([4, 6, 2, 3], ""), expand_fn, evaluate_fn, select_k=3, max_depth=4)
print("最佳状态:", best.state)
```

---

## 4. 用 LLM 做“扩展”和“评估”

真实 ToT 里，`expand_fn` 和 `evaluate_fn` 由 LLM 完成。常见提示词（Prompt）模式：

**扩展提示词：**

> 当前问题：{problem}
> 当前思路：{state}
> 请给出 3 个可能的下一步思路，每行一个，不要编号。

**评估提示词：**

> 当前问题：{problem}
> 当前思路：{state}
> 请判断这个思路是否可行，并给 0-10 分。只输出一个数字。

下面是一个调用 LLM 的伪代码结构：

```python
# 假设你有一个 call_llm(prompt) -> str 的函数
def llm_expand(problem, state, n=3):
    prompt = f"问题：{problem}\n当前思路：{state}\n请给出{n}个下一步思路，每行一个："
    text = call_llm(prompt)
    return [line.strip() for line in text.split("\n") if line.strip()]

def llm_evaluate(problem, state):
    prompt = f"问题：{problem}\n思路：{state}\n请打分0-10，只输出数字："
    try:
        return float(call_llm(prompt).strip())
    except ValueError:
        return 0.0
```

> 工程要点：LLM 输出不稳定，必须做**解析容错**（try/except、正则提取数字、限制重试次数）。

---

## 5. ToT 适合什么、不适合什么

**适合：**

- 需要**多步规划**的任务：数学题、逻辑谜题、代码生成、旅行规划。
- 需要**比较多个方案**并选优的任务。
- 单次 CoT 容易“一步错步步错”的任务。

**不适合：**

- 简单问答、事实查询：ToT 会浪费 token 和时间。
- 对延迟极敏感的场景：搜索会成倍增加 LLM 调用次数。

**成本直觉：** 如果每层扩展 3 个分支、保留 3 个、深度 4，最坏情况下调用次数约为 `3 + 3*3 + ...`，很容易达到几十次 LLM 调用。所以实际工程中要限制深度和宽度。

---

## 动手练习

**任务：实现一个“数字凑 24”的 ToT 小搜索器。**

要求：

1. 输入 4 个 1-10 的整数。
2. 每一步允许从当前数字列表中选两个数，做 `+ - * /` 之一，把结果放回列表。
3. 用 ToT 搜索：每层扩展所有可能操作，评估函数用“离 24 的差距越小分越高”。
4. 找到第一个结果为 24 的表达式就停止，并打印表达式。
5. 限制最大深度为 4，避免无限扩展。

**示例输入：** `[4, 6, 2, 3]`

**期望输出类似：** `((4+6)+2)*3 = 36` 或找到 `4*6*(3-2)=24` 这类正确表达式。

提示：

- 用 `fractions.Fraction` 避免浮点误差。
- 状态可以存 `(数字列表, 表达式字符串)`。
- 评估函数：若只剩一个数且等于 24，返回 100；否则返回 `-abs(当前结果 - 24)`。

完成后，你可以把 `evaluate_fn` 换成 LLM 打分，就得到了一个“LLM 版 ToT 搜索器”。

```python
from fractions import Fraction

class Node:
    def __init__(self, nums, expr, parent=None):
        self.nums = nums          # 当前数字列表
        self.expr = expr          # 当前表达式字符串
        self.parent = parent
        self.children = []
        self.score = 0.0

def expand(node):
    """从当前数字中选两个，做四则运算，生成子节点。"""
    nums = node.nums
    children = []
    n = len(nums)
    for i in range(n):
        for j in range(i + 1, n):
            a, b = nums[i], nums[j]
            rest = [nums[k] for k in range(n) if k != i and k != j]
            # 加
            children.append(Node(rest + [a + b], f"({node.expr}+{b})" if node.expr else f"({a}+{b})", node))
            # 乘
            children.append(Node(rest + [a * b], f"({node.expr}*{b})" if node.expr else f"({a}*{b})", node))
            # 减
            children.append(Node(rest + [a - b], f"({node.expr}-{b})" if node.expr else f"({a}-{b})", node))
            children.append(Node(rest + [b - a], f"({b}-{node.expr})" if node.expr else f"({b}-{a})", node))
            # 除
            if b != 0:
                children.append(Node(rest + [a / b], f"({node.expr}/{b})" if node.expr else f"({a}/{b})", node))
            if a != 0:
                children.append(Node(rest + [b / a], f"({b}/{node.expr})" if node.expr else f"({b}/{a})", node))
    return children

def evaluate(node):
    """若结果为 24 给 100，否则离 24 越近分越高。"""
    if len(node.nums) == 1:
        if node.nums[0] == 24:
            return 100.0
        return -abs(float(node.nums[0]) - 24.0)
    return 0.0

def tot_24(nums, max_depth=4, select_k=5):
    root = Node([Fraction(x) for x in nums], "")
    frontier = [root]
    for depth in range(max_depth):
        next_frontier = []
        for node in frontier:
            for child in expand(node):
                child.score = evaluate(child)
                node.children.append(child)
                next_frontier.append(child)
        next_frontier.sort(key=lambda n: n.score, reverse=True)
        frontier = next_frontier[:select_k]
        for node in frontier:
            if len(node.nums) == 1 and node.nums[0] == 24:
                return node.expr
    return None

if __name__ == "__main__":
    result = tot_24([4, 6, 2, 3])
    print("找到表达式:", result)
```

## agent.llm.react

# agent.llm.react：让大模型学会“边想边做”

> **一句话直觉**：ReAct（Reasoning + Acting，推理与行动）让大语言模型（LLM, Large Language Model）不再只是“一口气猜答案”，而是像人一样**先想一步、再查一下、再想下一步**，最终得出更可靠的结论。

---

## 1. 为什么需要 ReAct？

普通 LLM 回答问题时，是**一次性生成**完整答案。这有三个致命弱点：

1. **容易幻觉（hallucination）**：模型会自信地编造事实。
2. **无法获取新信息**：训练数据截止之后就一无所知。
3. **无法执行操作**：不能查数据库、调 API、算数学。

ReAct 的核心思想最早由 Google 与 Princeton 在 2022 年论文《ReAct: Synergizing Reasoning and Acting in Language Models》提出：**让模型把“思考（Thought）”和“行动（Action）”交替输出**，形成循环：

```
Thought → Action → Observation → Thought → Action → ... → Final Answer
```

- **Thought（思考）**：模型内部的推理，用自然语言写出来。
- **Action（行动）**：调用一个外部工具（tool），比如搜索、计算器。
- **Observation（观察）**：工具返回的结果，回灌给模型。

---

## 2. 最小可运行的 ReAct 循环

我们不用任何框架，用纯 Python 模拟一个 ReAct 循环，先建立直觉。

**关键结论**：ReAct 本质上就是一个 `while` 循环 + 一个“会输出结构化文本的 LLM”。

```python
# 伪 LLM：用固定规则模拟模型输出，方便零依赖运行
def fake_llm(prompt: str) -> str:
    if "巴黎" not in prompt and "人口" in prompt:
        return "Thought: 我不知道巴黎人口，需要搜索。\nAction: search[巴黎人口]"
    if "Observation: 巴黎人口" in prompt:
        return "Thought: 已经拿到数据，可以回答了。\nFinal Answer: 巴黎人口约 210 万（市区）。"
    return "Final Answer: 我不知道。"

# 工具：模拟一个搜索
TOOLS = {
    "search": lambda q: "巴黎人口约 210 万（市区）",
}

def parse_action(text: str):
    """从 LLM 输出中解析出 Action，例如 Action: search[巴黎人口]"""
    for line in text.splitlines():
        if line.startswith("Action:"):
            raw = line[len("Action:"):].strip()  # 例如 search[巴黎人口]
            name, arg = raw.split("[", 1)
            return name.strip(), arg.rstrip("]")
    return None, None

def react(question: str, max_steps: int = 5) -> str:
    scratchpad = f"Question: {question}\n"  # 记录整个过程
    for step in range(max_steps):
        output = fake_llm(scratchpad)
        scratchpad += output + "\n"
        print(f"--- Step {step} ---\n{output}")
        if "Final Answer:" in output:
            return output.split("Final Answer:")[1].strip()
        name, arg = parse_action(output)
        if name in TOOLS:
            obs = TOOLS[name](arg)
            scratchpad += f"Observation: {obs}\n"
        else:
            scratchpad += "Observation: 未知工具\n"
    return "达到最大步数，未收敛"

print(react("巴黎有多少人口？"))
```

运行后你会看到三段输出：Thought → Action → Observation → Thought → Final Answer，这就是 ReAct 的骨架。

---

## 3. 用真实 LLM 驱动 ReAct

真实场景里，`fake_llm` 换成一个真正的 LLM（如 OpenAI、Claude、通义千问），并在 system prompt（系统提示词）里告诉它输出格式。

**关键结论**：ReAct 的“协议”是靠 prompt 约定的，模型只要能稳定吐出 `Thought/Action/Final Answer` 格式就能工作。

```python
SYSTEM_PROMPT = """你是一个 ReAct 智能体。
可用工具:
- search[query]: 搜索网页
- calc[expr]: 计算数学表达式

严格按以下格式输出，不要多余文字:
Thought: 你要做什么推理
Action: 工具名[参数]
(或) Final Answer: 最终答案
"""

# 真实调用示例（伪代码，需替换为你的 LLM SDK）
# from openai import OpenAI
# client = OpenAI()
# resp = client.chat.completions.create(
#     model="gpt-4o-mini",
#     messages=[
#         {"role": "system", "content": SYSTEM_PROMPT},
#         {"role": "user", "content": scratchpad},
#     ],
# )
# output = resp.choices[0].message.content
```

要点：
- 每次只把 **scratchpad（草稿本）** 作为 user message 传进去，模型就记得此前的 Thought/Action/Observation。
- 用 `stop=["Observation:"]`（如果 SDK 支持）避免模型自己编造 Observation。

---

## 4. 工程化：工具注册与容错

在真实 Agent（智能体）里，工具是核心资产。一个可维护的设计是**注册表模式**。

**关键结论**：工具函数要统一签名、统一返回字符串，并且必须处理“参数不合法”的情况。

```python
import ast, operator as op

TOOL_REGISTRY = {}
def tool(name):
    def deco(fn):
        TOOL_REGISTRY[name] = fn
        return fn
    return deco

@tool("calc")
def calc(expr: str) -> str:
    """只允许 + - * / 和数字，避免 eval 注入。"""
    allowed = {ast.Add: op.add, ast.Sub: op.sub,
               ast.Mult: op.mul, ast.Div: op.truediv}
    def ev(node):
        if isinstance(node, ast.Num):      # Python 3.8+
            return node.n
        if isinstance(node, ast.BinOp) and type(node.op) in allowed:
            return allowed[type(node.op)](ev(node.left), ev(node.right))
        raise ValueError("不支持的表达式")
    try:
        return str(ev(ast.parse(expr, mode="eval").body))
    except Exception as e:
        return f"ERROR: {e}"

@tool("search")
def search(query: str) -> str:
    # 真实场景接 Bing / Google / 向量库
    return f"[模拟搜索结果] 关于 '{query}' 的信息..."
```

容错清单：
- 工具返回 `ERROR: ...` 时，让模型看到并自行决定下一步；
- 限制 `max_steps`，防止无限循环；
- 解析失败的 Action 要回灌 `Observation: 格式错误，请重新输出`。

---

## 5. ReAct 的边界与延伸

- **不是万能**：如果任务不需要外部信息，ReAct 的额外循环反而增加延迟和 token 成本。
- **和 CoT 的关系**：Chain-of-Thought（思维链）只“想”不“做”；ReAct = CoT + Tools。
- **和 Plan-and-Execute 的关系**：ReAct 是“走一步看一步”，Plan-and-Execute 是先规划再执行，长任务更适合后者。
- **现代形态**：LangChain、LlamaIndex、AutoGPT 里的 Agent 基本都是 ReAct 的变种；OpenAI 的 Function Calling / Tool Use 是把 Output 解析换成结构化 JSON，但循环一模一样。

---

## 动手练习

**任务**：给上面的 ReAct 循环加一个新工具 `weather[city]`，返回该城市的模拟天气（可硬编码几个城市）；并让 Agent 能回答“北京和上海的天气分别如何，哪个更适合跑步？”

**验收标准**：
1. 至少调用 `weather` 两次（两个城市）。
2. 最后给出 `Final Answer` 并包含推理过程。
3. 加入 `max_steps=8` 防止死循环。

**提示**：你只需要在 `TOOL_REGISTRY` 里注册 `weather`，并在 `SYSTEM_PROMPT` 的工具列表里补上它，然后修改 `fake_llm`（或接真实 LLM）让它学会分别查两个城市。

```python
import ast, operator as op

# ---------- 工具注册 ----------
TOOL_REGISTRY = {}
def tool(name):
    def deco(fn):
        TOOL_REGISTRY[name] = fn
        return fn
    return deco

@tool("search")
def search(query: str) -> str:
    db = {"巴黎人口": "巴黎市区人口约 210 万",
          "北京天气": "北京：晴，25°C，微风",
          "上海天气": "上海：小雨，22°C，湿度大"}
    return db.get(query, f"[无结果] {query}")

@tool("calc")
def calc(expr: str) -> str:
    allowed = {ast.Add: op.add, ast.Sub: op.sub,
               ast.Mult: op.mul, ast.Div: op.truediv}
    def ev(n):
        if isinstance(n, ast.Num): return n.n
        if isinstance(n, ast.BinOp) and type(n.op) in allowed:
            return allowed[type(n.op)](ev(n.left), ev(n.right))
        raise ValueError("unsupported")
    try:
        return str(ev(ast.parse(expr, mode="eval").body))
    except Exception as e:
        return f"ERROR: {e}"

# ---------- 伪 LLM ----------
def fake_llm(scratchpad: str) -> str:
    if "Final Answer" in scratchpad:
        return "Final Answer: 完成"
    if "巴黎人口" not in scratchpad and "巴黎" in scratchpad:
        return "Thought: 需要查巴黎人口。\nAction: search[巴黎人口]"
    if "Observation: 巴黎市区人口" in scratchpad and "Final" not in scratchpad:
        return "Final Answer: 巴黎市区人口约 210 万"
    return "Final Answer: 我无法回答"

# ---------- 循环 ----------
def parse_action(text):
    for line in text.splitlines():
        if line.startswith("Action:"):
            raw = line.split("Action:", 1)[1].strip()
            name, arg = raw.split("[", 1)
            return name.strip(), arg.rstrip("]")
    return None, None

def react(question, max_steps=8):
    sp = f"Question: {question}\n"
    for i in range(max_steps):
        out = fake_llm(sp)
        sp += out + "\n"
        if "Final Answer:" in out:
            return out.split("Final Answer:")[1].strip()
        name, arg = parse_action(out)
        if name in TOOL_REGISTRY:
            sp += f"Observation: {TOOL_REGISTRY[name](arg)}\n"
        else:
            sp += "Observation: 未知工具\n"
    return "超过最大步数"

if __name__ == "__main__":
    print(react("巴黎有多少人口？"))
    print(react("2+3*4 等于多少？"))
```


---

## 本课题目

### single_choice · None



- [A] 减少模型推理时的计算资源消耗
- [B] 让模型在给出最终答案前展示中间推理步骤
- [C] 强制模型只输出结构化 JSON 格式
- [D] 提高模型对输入文本的编码速度

**参考答案**：1

**解析**：思维链提示的核心是引导模型显式地生成中间推理步骤，从而提升复杂推理任务的准确性。它不直接减少计算资源、不强制输出格式，也不影响编码速度。

### single_choice · None



- [A] 在提示中给出 5 个完整的推理示例
- [B] 在提示末尾加上“让我们一步一步思考”之类的引导语
- [C] 要求模型仅输出最终答案，不展示过程
- [D] 使用 Python 代码定义计算图后再提问

**参考答案**：1

**解析**：零样本思维链通过添加“Let's think step by step”等引导语触发推理，不依赖示例。给出多个示例属于少样本 CoT；仅输出答案与 CoT 相反；定义计算图属于程序辅助推理。

### single_choice · None



- [A] 任务需要多步逻辑推理
- [B] 提示中要求模型展示推理过程
- [C] 任务非常简单，模型直接回答即可
- [D] 示例中的推理步骤逻辑清晰

**参考答案**：2

**解析**：对于非常简单的任务，CoT 可能增加不必要的输出长度甚至引入干扰，收益有限。多步推理、要求展示过程、清晰示例通常都是 CoT 的有利条件。

### single_choice · None



- [A] 把系统提示改成“不要思考”
- [B] 在提示中加入一个完整的少样本推理示例
- [C] 把模型温度调到 0 并删除所有示例
- [D] 要求模型只输出最终答案

**参考答案**：1

**解析**：加入少样本示例可以更具体地示范期望的推理格式，比单纯一句引导语更有效。改成“不要思考”、删除示例、只输出答案都与目标相反。

### single_choice · None



- [A] 思维链展示的推理过程一定与模型内部真实计算完全一致
- [B] 思维链提供了可读的推理痕迹，但不保证完全反映内部机制
- [C] 思维链没有任何可解释性价值
- [D] 思维链只能用于调试，不能用于生产

**参考答案**：1

**解析**：CoT 提供了人类可读的推理过程，有助于理解和调试，但它并不保证忠实反映模型内部真实计算。因此“完全一致”“没有价值”“只能调试”都过于绝对。

### single_choice · None



- [A] 一定会提高用户满意度
- [B] 可能泄露提示中的敏感信息或暴露内部策略
- [C] 会让模型无法继续生成文本
- [D] 会改变模型的参数规模

**参考答案**：1

**解析**：推理过程可能包含系统提示、内部策略或敏感数据，直接展示给用户存在泄露风险。它不会改变参数规模，也不会导致模型无法生成。

### single_choice · None



- [A] 思维链提示的输出一定更短
- [B] 思维链提示的输出通常包含更多中间推理文字
- [C] 思维链提示的输出只能是 JSON
- [D] 思维链提示的输出不包含任何自然语言

**参考答案**：1

**解析**：CoT 的输出通常更长，因为包含中间推理步骤。它不强制 JSON，也不排斥自然语言，更不会一定更短。

### single_choice · None



- [A] 只看最终答案是否正确，完全不看推理过程
- [B] 同时评估最终答案和推理过程的合理性
- [C] 只评估推理过程是否好看
- [D] 只统计输出字符数

**参考答案**：1

**解析**：合理的评估应同时关注答案正确性和推理过程质量，因为过程错误可能在其他输入上导致失败。只看答案、只看过程或只看长度都不全面。

### single_choice · None



- [A] 请逐步推导，并说明每一步的依据。
- [B] 请先列出已知条件，再选择合适公式。
- [C] 请随便写几步，然后给出一个答案。
- [D] 请验证每一步计算是否正确。

**参考答案**：2

**解析**：“随便写几步”会诱导模型生成形式化、无实质推理的步骤。其他选项都要求依据、条件、公式或验证，更可能引导真实推理。

### single_choice · None



- [A] 完全替代工具调用
- [B] 帮助模型规划何时以及如何调用工具
- [C] 让工具调用变得不必要
- [D] 阻止模型使用任何外部 API

**参考答案**：1

**解析**：CoT 可以辅助规划工具的使用时机和方式，但不能完全替代工具，也不会让工具变得不必要或阻止调用。

### single_choice · None



- [A] 减少推理步骤，让模型直接给答案
- [B] 要求模型在每一步后进行自检或验证
- [C] 把温度调到最高以增加随机性
- [D] 删除所有示例

**参考答案**：1

**解析**：要求模型在每一步自检或验证，可以及时发现并纠正中间错误。减少步骤、提高温度、删除示例都不利于推理可靠性。

### single_choice · None



- [A] 思维链可以解决所有类型的推理问题
- [B] 思维链对某些任务可能无效，甚至可能引入错误
- [C] 思维链只适用于英文任务
- [D] 思维链会显著降低模型的通用能力

**参考答案**：1

**解析**：CoT 并非万能，对某些任务可能无效或引入错误，需要结合任务特点使用。它不限于英文，也不会系统性降低通用能力。

### single_choice · None



- [A] 步骤越简洁越好，最好只保留最终结果
- [B] 步骤应包含与任务相关的中间推导，且逻辑连贯
- [C] 步骤必须使用与最终答案相同的语言，否则无效
- [D] 步骤应该随机打乱顺序以增强泛化

**参考答案**：1

**解析**：少样本 CoT 的示例需要展示连贯、可理解的中间推理过程，才能引导模型模仿。省略步骤、强制同语言、随机打乱都会削弱引导效果。

### single_choice · None



- [A] 模型参数在提示后发生了更新
- [B] 显式推理步骤帮助模型分解了多步计算
- [C] 思维链提示降低了问题的难度
- [D] 模型在输出答案前进行了联网搜索

**参考答案**：1

**解析**：CoT 通过让模型把多步问题拆解为中间步骤，减少直接跳跃到答案带来的错误。模型参数不会因提示改变，问题难度本身也未变，联网搜索并非 CoT 的默认行为。

### single_choice · None



- [A] 思维链提示对小模型和大模型的效果完全一样
- [B] 思维链提示通常在大模型上更能发挥优势
- [C] 思维链提示只对小模型有效
- [D] 思维链提示会显著降低大模型的推理能力

**参考答案**：1

**解析**：研究表明，CoT 的收益通常随模型规模增大而更明显，小模型可能生成不连贯的推理链。因此“完全一样”“只对小模型有效”“降低大模型能力”都不准确。

### single_choice · None



- [A] 判断一个句子是否包含某个关键词
- [B] 求解需要多步推理的数学文字题
- [C] 把一段文本复制到另一个字段
- [D] 检查字符串长度是否超过 100

**参考答案**：1

**解析**：CoT 对需要多步推理的任务（如数学文字题）帮助最大。简单匹配、复制、长度检查等单步任务通常不需要 CoT，甚至可能引入不必要的输出。

### single_choice · None



- [A] 忽略推理过程，只保留最终答案
- [B] 认为过程错误不影响智能体的可靠性
- [C] 仍应关注推理过程，因为过程错误可能导致其他输入下答案错误
- [D] 立即删除该模型的全部参数

**参考答案**：2

**解析**：CoT 的价值在于可解释性和稳定性，过程错误即使偶然得到正确答案，也说明推理不可靠，换一个输入可能失败。忽略过程、认为无影响或删除参数都不合理。

### single_choice · None



- [A] 请直接给出答案，不要解释。
- [B] 请先分析已知条件，再逐步推导，最后给出答案。
- [C] 请把答案翻译成英文。
- [D] 请用一句话概括这段文字。

**参考答案**：1

**解析**：“先分析已知条件，再逐步推导，最后给出答案”明确要求中间推理步骤，符合 CoT。直接给答案、翻译、概括都没有要求多步推理。

### single_choice · None



- [A] 自洽性只生成一条推理链，普通 CoT 生成多条
- [B] 自洽性生成多条推理链并投票选择最一致的答案
- [C] 自洽性不需要模型进行推理
- [D] 自洽性只能用于图像任务

**参考答案**：1

**解析**：Self-Consistency 通过采样多条推理路径，再对最终答案进行多数投票，以提高鲁棒性。普通 CoT 通常只生成一条链；自洽性仍依赖推理；也不是图像专用。

### single_choice · None



- [A] 直接作为最终用户可见的答案，无需任何后处理
- [B] 作为中间推理记录，供后续步骤或工具调用参考
- [C] 替代所有工具调用，因为模型已推理出结果
- [D] 作为模型训练时的梯度更新信号

**参考答案**：1

**解析**：CoT 输出常作为中间推理，帮助后续决策、工具选择或校验，而不是直接当作最终答案。它不能替代工具调用，也不是训练时的梯度信号。

### single_choice · None



- [A] 它要求模型一次性输出完整推理链，不能回头修改
- [B] 它在推理过程中生成多个候选思路，并能对其评估、选择或回溯
- [C] 它只能用于数学计算题，不能用于写作类任务
- [D] 它通过微调模型参数来扩大推理搜索空间

**参考答案**：1

**解析**：ToT 的核心是在推理时把思考过程建模成树状搜索：每个节点是一个中间思路，可以生成多个分支，通过评估函数给分支打分，再用搜索策略（如 BFS/DFS/beam）选择扩展或回溯，而不是一条路走到黑。A 描述的是普通链式思维；C 缩小了适用范围；D 与参数无关，ToT 是推理时的策略。

### single_choice · None



- [A] 决定模型生成时使用哪个温度参数
- [B] 把最终答案翻译成自然语言
- [C] 为每个候选中间思路打分，帮助搜索决定扩展、保留还是剪枝
- [D] 统计整棵树一共有多少个节点

**参考答案**：2

**解析**：评估函数用于判断某个中间思路「是否值得继续往下走」，它可以是模型自我评估、启发式规则或外部工具的验证结果。搜索策略依赖这些分数做取舍。温度属于采样参数，翻译是输出环节，节点计数与推理质量无关。

### multi_choice · None



- [A] 让模型自己对候选思路做出评价或打分
- [B] 用外部工具或规则对中间状态做校验
- [C] 根据是否满足题目约束来筛选
- [D] 完全随机保留，不设任何判断依据

**参考答案**：[0, 1, 2]

**解析**：评估可以是模型自评、外部工具验证或基于规则/约束的检查，这些都能为搜索提供取舍依据。D 相当于放弃评估，退化为盲目搜索，不符合 ToT 的评估环节设计初衷。

### multi_choice · None



- [A] 往往需要多次尝试、存在多条可行路径
- [B] 中间步骤的好坏可以被部分判断（哪怕不完美）
- [C] 最终答案的正确性完全无法定义，也没有任何评判标准
- [D] 通常比一次性直接回答更消耗算力

**参考答案**：[0, 1, 3]

**解析**：ToT 适合路径多、可部分评估中间状态的任务，其代价是更高算力。C 若成立，则评估和搜索都失去依据，反而不适合 ToT，属于对适用边界的误解。

### fill_blank · None



**参考答案**：["剪枝", "pruning", "Pruning", "剪枝(pruning)"]

**解析**：丢弃低分分支以节省计算叫剪枝（pruning），是 ToT 在有限预算下控制开销的关键手段；它与回溯（回到上层换分支）是相关但不同的操作。

### fill_blank · None



**参考答案**：["回溯", "backtracking", "Backtracking", "回退"]

**解析**：回溯（backtracking）让方法可以撤销不佳选择并从上层节点重新探索，这正是 ToT 比单向链式思维更容错的原因。

### code_reading · None



**参考答案**：它在每一层为每个节点生成多个候选思路，用评估函数过滤掉低于阈值的候选，再进入下一层，属于带评估过滤（剪枝）的逐层搜索；只有达到阈值分数的分支才会被保留到下一轮，最终返回评估最高的思路。

**解析**：关键在于识别出两个动作：一是对每个节点的分支生成（体现树的可分支），二是用评估阈值过滤（体现剪枝）。这两点共同构成 ToT 的「生成—评估—筛选」循环；它不是单纯的一次性链式推理。

### code_reading · None



**参考答案**：会引发模型调用次数随分支数和深度呈指数式增长，导致显著的成本与延迟上升，甚至难以及时结束；通常需要引入深度/宽度上限和剪枝来约束。

**解析**：每层多分支、每分支都递归到最深、且每个候选都调用模型打分，其调用量会随层数指数膨胀。ToT 的实用化必须配合分支上限、深度限制和评估剪枝来控制规模。

### scenario · None



**解析**：该任务有多个可行路径、中间状态可部分评判，且对纠错有需求，符合 ToT 的适用特征，因此建议引入。落地上要：为每步生成多个候选分支；用评估函数（模型自评或规则/工具校验）给分支打分；靠剪枝和深度/宽度上限控制成本；在走偏时回溯到上层节点换分支。同时要承认 ToT 会带来更多模型调用，需要权衡收益与延迟。

### scenario · None



**解析**：ToT 的价值来自「存在多条推理路径、中间状态可评估、需要探索与回溯」。简单分类任务一次性即可给出结果，缺少可分支的中间步骤，改用 ToT 只会增加模型调用和延迟，而不会带来对应收益，属于用错场景；应建议保持单次判断或选用更合适的轻量方案。

### scenario · None



**解析**：评估函数若对所有分支给出相同分数，等于没有取舍依据，搜索会近乎盲目地铺开。应让评估能区分优劣（自评、规则或工具校验），配合剪枝、对相似分支去重、设置深度/宽度上限，并选用合适的搜索策略（如最佳优先）以避免分支爆炸。

### scenario · None



**解析**：区别要点在于：链式思维是单条线性推理链，不能纠错；思维树在每步可生成多个分支，经评估取舍并可回溯。判断标准是任务是否「存在多条可行路径且中间状态可部分评判、需要试探与纠错」——若是则适合，若一次判断即可完成、没有中间步骤，则引入只会徒增成本。

### single_choice · None



- [A] 让每一步推理更简短
- [B] 引入分支生成与对分支的取舍/回溯，从而可以探索多条推理路径
- [C] 强制模型只输出一个答案以降低开销
- [D] 把推理过程全部交给外部数据库完成

**参考答案**：1

**解析**：CoT 是线性的单条推理链，一旦某步走错就难以挽回；ToT 在每步可以生成多个候选思路并评估取舍，必要时回溯，因此能探索和比较不同路径。A、C 与 ToT 特征相反或无关，D 是对工具调用的误解。

### single_choice · None



- [A] 直接一次生成答案（无推理）
- [B] 固定顺序的链式思维，且不允许回溯
- [C] 思维树，借助分支生成与评估来搜索
- [D] 把所有问题都改成单选题

**参考答案**：2

**解析**：当任务需要探索多种可能方案、且中间状态可以部分评判（如规划、谜题求解、代码设计权衡）时，ToT 的分支+评估+搜索更有利。A 缺乏推理；B 无法纠错；D 与推理方法无关。

### single_choice · None



- [A] 删除模型的参数以减小显存占用
- [B] 丢弃评估分数低、明显不可能通向好结果的候选分支，以节省计算
- [C] 把多个候选答案合并成一个
- [D] 减少提示词中的示例数量

**参考答案**：1

**解析**：剪枝是在搜索过程中放弃低价值分支，从而把有限的计算预算花在更有希望的方向上，这是 ToT 控制成本的关键手段之一。它不涉及模型参数、不合并答案、也不等于少写示例。

### single_choice · None



- [A] 无限制地在每一层生成尽可能多的分支
- [B] 对每个分支都展开到最终答案再比较
- [C] 设置分支数量上限、搜索深度上限，并借助评估提前剪枝
- [D] 把温度调成 0 就能完全消除成本

**参考答案**：2

**解析**：ToT 相比 CoT 会显著增加模型调用次数，因此常用宽度/深度上限和评估剪枝来约束开销。A、B 会放大成本；D 中把温度设为 0 只是减少随机性，并不解决多分支带来的调用次数问题。

### single_choice · None



- [A] 回到之前某个中间思路，改从另一条分支继续探索
- [B] 删除模型权重后重新训练
- [C] 把已经得到的最终答案重新提交一遍
- [D] 在提示词里重复一遍问题

**参考答案**：0

**解析**：回溯是搜索机制：当某条路径评估不佳或走入死胡同时，退回到上层节点并尝试其他分支，这正是 ToT 能纠错的原因。其余选项都属于对「回溯」的字面或无关联想。

### single_choice · None



- [A] 它可以生成多个候选的中间思路
- [B] 它需要对候选思路进行评估或排序
- [C] 它必须对模型进行微调后才能使用
- [D] 它可以配合搜索策略（如广度优先或最佳优先）使用

**参考答案**：2

**解析**：ToT 是一种推理/提示层面的策略，通常无需微调即可使用，靠生成多分支和评估来选择路径。A、B、D 都是其典型特征。指出「必须微调」是常见误解。

### multi_choice · None



- [A] 把推理过程组织成可分支的节点
- [B] 对候选思路进行评估打分
- [C] 用某种搜索策略在分支间选择
- [D] 只能使用一次模型调用、且不允许重复调用

**参考答案**：[0, 1, 2]

**解析**：ToT 由「思路生成成节点」「评估」「搜索/选择（含剪枝回溯）」三部分协同构成。D 与其机制相反——ToT 恰恰常常需要多次模型调用来生成和评估分支。

### multi_choice · None



- [A] 在推理过程中有机会纠正中间的糟糕选择
- [B] 能够同时探索多种解题思路并比较优劣
- [C] 一定能让模型调用次数减少、延迟下降
- [D] 对需要试探和规划的任务可能提升解题成功率

**参考答案**：[0, 1, 3]

**解析**：ToT 通过分支、评估和回溯来纠错、比较不同路径，常在规划/试探类任务上更有效。但它的代价正是更多的模型调用和更高延迟，所以 C 是错误的方向性描述，属于常见误解。

### single_choice · None



- [A] Thought
- [B] Action
- [C] Observation
- [D] 三者都由模型生成

**参考答案**：2

**解析**：Thought 与 Action 是模型生成的推理与调用意图，Observation 是执行 Action 后由环境/工具回传的结果，模型不能自行编造（否则就是幻觉观测）。

### single_choice · None



- [A] 先一次性把所有推理做完，再批量执行所有行动
- [B] 推理与行动交替进行，每一步行动的结果会影响下一步推理
- [C] 行动是可有可无的，纯推理即可完成任务
- [D] 行动结果只用于最终答案展示，不参与后续推理

**参考答案**：1

**解析**：ReAct 的核心是交错（interleaving）：Thought 引导 Action，Observation 反馈回上下文再驱动下一轮 Thought，形成闭环。

### multi_choice · None



- [A] 工具返回的原始 JSON 数据
- [B] 检索到的文档片段
- [C] 模型对下一步要做什么的内心独白
- [D] 工具执行报错信息

**参考答案**：[0, 1, 3]

**解析**：Observation 是执行 Action 后环境返回的结果，包含数据、检索片段或错误信息；模型的内心独白属于 Thought，不是 Observation。

### multi_choice · None



- [A] 为工具定义清晰的名字和参数说明
- [B] 对 Action 输出做严格的解析与校验
- [C] 允许模型在工具报错时直接编造成功结果
- [D] 设置最大步数与停滞检测

**参考答案**：[0, 1, 3]

**解析**：清晰工具定义、严格解析、步数与停滞控制都能提升稳定性；编造成功结果会破坏可观测性，是反模式。

### multi_choice · None



- [A] CoT 只有推理，没有与外部环境交互的行动
- [B] ReAct 可以被看作在推理之外引入行动与观测的扩展
- [C] 两者都不需要提示词
- [D] ReAct 的 Observation 能为推理提供 CoT 所不具备的外部事实

**参考答案**：[0, 1, 3]

**解析**：CoT 侧重内部推理链，缺乏外部工具交互；ReAct 引入 Action/Observation 提供外部事实。两者都需要提示词，故 C 错。

### fill_blank · None



**参考答案**：["Thought, Action, Observation", "Thought/ Action/ Observation", "Thought、Action、Observation"]

**解析**：ReAct 的三段式结构为 Thought（推理）→ Action（行动）→ Observation（观测），顺序与名称需对应正确。

### fill_blank · None



**参考答案**：["max_steps", "max steps", "maximum steps", "max_iterations"]

**解析**：最大步数/迭代上限（max_steps 或 max_iterations）是控制循环收敛与成本的常见安全机制。

### fill_blank · None



**参考答案**：["上下文", "context", "对话历史", "message history"]

**解析**：历史 Thought/Action/Observation 需要保留在上下文中，后续轮次才能正确引用早前观测。

### code_reading · None



**参考答案**：模型每轮只能看到初始 prompt，看不到之前的 Thought/Action/Observation，会丢失早期观测并可能重复相同动作、无法收敛（或被 max_steps 截断）。

**解析**：history 的作用是累积观测并回灌到下一轮提示中；删除后 ReAct 闭环被破坏，观测无法影响后续推理，导致重复或停滞。

### code_reading · None



**参考答案**：不执行工具，而是把「未知工具」的错误信息作为 Observation 返回给模型；好处是让模型在下一轮根据该反馈纠正动作，而不是崩溃或静默失败，保持闭环可恢复。

**解析**：把调用错误转化为可读 Observation，使模型有机会自我纠正，是提升 ReAct 鲁棒性的常见做法。

### scenario · None



**解析**：诊断方向：检查工具描述/命名是否清晰可被模型选择；提示是否明确要求先 Action 再作答；格式是否可解析；观测是否回灌。改进：完善工具说明、强化格式约束、在无观测时禁止断言事实、对事实类问题要求引用 Observation。

### scenario · None



**解析**：改进方向：(1) 停滞/重复检测，发现相同 Action+参数时提示模型或强制换策略；(2) 限制最大步数并给出兜底回复；(3) 在 Observation 中回传「已查询过、无新信息」以驱动模型更新推理；(4) 优化工具返回结果的信息量。原理都是打破无效闭环、让观测有效驱动下一步推理。

### single_choice · None



- [A] 工具执行速度太慢
- [B] 模型陷入循环，未能根据已有观测更新推理
- [C] Observation 格式不对导致模型无法读取
- [D] 工具返回了正确答案

**参考答案**：1

**解析**：重复相同动作而无进展是典型的推理停滞（loop），说明模型没有利用已有 Observation 推进 Thought，需要引入去重/终止/提示干预。

### single_choice · None



- [A] 它完全消除了模型的幻觉
- [B] 它通过外部工具观测为推理提供事实依据，从而减少凭空猜测
- [C] 它不需要任何提示词设计
- [D] 它保证在固定步数内一定得到正确答案

**参考答案**：1

**解析**：ReAct 通过 Action 获取真实 Observation 来支撑推理，能降低但不能完全消除幻觉，也不保证一定收敛到正确答案。

### single_choice · None



- [A] 调用计算器求 17 的三次方
- [B] 查询天气 API 获取某城市当前温度
- [C] 检索知识库中关于退货政策的条款
- [D] 把模型自己上一轮的 Thought 当作事实直接照抄为最终结论

**参考答案**：3

**解析**：Action 应当是能与外部环境交互、产生可验证 Observation 的操作；把自身 Thought 当事实输出不是行动，反而会放大幻觉。

### single_choice · None



- [A] 让输出更美观
- [B] 便于程序稳定解析出要执行的工具及参数
- [C] 减少 token 消耗
- [D] 强制模型只输出自然语言

**参考答案**：1

**解析**：结构化格式使外层程序能可靠解析 Action 名称与参数并执行，格式混乱会导致解析失败、循环中断或误执行。

### single_choice · None



- [A] 提高单次工具调用的准确性
- [B] 防止无进展的循环无限进行、控制成本与延迟
- [C] 保证答案一定正确
- [D] 让模型记住历史对话

**参考答案**：1

**解析**：最大步数是安全阀，用于在模型不收敛时及时终止，避免无限循环带来的耗时与费用，但并不提升正确性。

### single_choice · None



- [A] 编造一个工具名并假装调用成功
- [B] 把 Observation 伪造为成功结果继续推理
- [C] 明确说明工具不足或请求澄清，而不是伪造观测
- [D] 无限重试同一个动作直到成功

**参考答案**：2

**解析**：伪造 Observation 会破坏闭环的可信性；正确做法是如实反馈能力边界（如输出无法完成或请求补充工具/信息）。

### single_choice · None



- [A] 因为 Observation 越长越好
- [B] 因为后续推理依赖它作为事实依据，编造会污染整条推理链
- [C] 因为工具调用必须花费 token
- [D] 因为 Observation 必须是 JSON

**参考答案**：1

**解析**：Observation 是闭环中的事实锚点，一旦捏造，后续 Thought 都建立在虚假前提上，错误会级联放大。

### single_choice · None



- [A] 工具本身执行失败
- [B] 上下文管理/历史观测未正确保留或被截断
- [C] 模型温度设置过高
- [D] Action 名称拼写错误

**参考答案**：1

**解析**：ReAct 依赖上下文携带历史 Thought/Action/Observation；若上下文被截断或未保留，就会丢失早期的关键观测。
