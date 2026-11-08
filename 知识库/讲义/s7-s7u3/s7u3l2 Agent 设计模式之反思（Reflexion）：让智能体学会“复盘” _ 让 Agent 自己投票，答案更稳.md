# s7u3l2 Agent 设计模式之反思（Reflexion）：让智能体学会“复盘” / 让 Agent 自己投票，答案更稳

> 来源 `content/lessons/s7u3l2.json`

## agent.pattern.reflexion

# Agent 设计模式之反思（Reflexion）：让智能体学会“复盘”

> **一句话直觉**：Reflexion（反思）就是让 AI 智能体（Agent）在完成任务失败后，像人类一样先“复盘”错在哪、下次怎么改，把反思结果存进记忆，再重试一次——从而不靠重新训练模型，也能持续提升表现。

本讲面向零基础到工程级，循序渐进地拆解反思模式。

---

## 一、为什么需要反思？从“一问一答”到“自我改进”

传统的 LLM（Large Language Model，大语言模型）调用是**单次映射**：输入问题 → 输出答案。它有三类典型失败：

1. **一次性犯错**：多步推理中第一步算错，后面全错。
2. **不会从错误中学习**：同一个错误下次还会犯。
3. **缺少外部信号**：模型不知道自己对不对，因为它没有“打分器”。

**反思模式**的核心思路是引入一个**闭环（loop）**：执行 → 评估 → 反思 → 再执行。关键是新增两块东西：

- **评估器（Evaluator）**：判断本轮结果好还是坏（可以是单元测试、规则、另一个 LLM 打分）。
- **反思记忆（Reflection Memory）**：把“为什么失败、下次怎么改”写成自然语言，存起来，在下一轮拼进提示词（Prompt）。

这就是论文 *Reflexion: Language Agents with Verbal Reinforcement Learning* (Shinn et al., 2023) 的核心。它不是用梯度更新参数，而是用**语言作为强化信号**。

---

## 二、反思模式的四步循环（核心骨架）

用伪代码描述反思循环：

```
reflections = []              # 反思记忆
for attempt in range(MAX):
    result = actor(task, reflections)      # 1. 执行
    ok, feedback = evaluator(result)       # 2. 评估
    if ok:
        return result                      # 成功即返回
    reflection = reflector(task, result, feedback)  # 3. 反思
    reflections.append(reflection)         # 4. 存入记忆
return best_so_far
```

四个角色对应四个可替换的组件：

| 角色 | 职责 | 工程常见实现 |
|------|------|--------------|
| Actor（执行者） | 根据任务和反思生成输出 | LLM + Prompt |
| Evaluator（评估者） | 判断对错并给出反馈 | 单元测试 / 规则 / LLM 裁判 |
| Reflector（反思者） | 生成结构化反思文本 | LLM + 反思模板 |
| Memory（记忆） | 累积反思，避免重蹈覆辙 | 列表 / 向量库 |

下面用最朴素的方式实现这四步（后续小节会分别加强）。

```python
# reflexion_skeleton.py
# 用可插入的“伪 LLM”演示反思循环的骨架，便于理解流程

from typing import Callable, List, Tuple

# 1. Actor：把任务和之前的反思拼进 prompt，产生答案
def actor(task: str, reflections: List[str]) -> str:
    memory = "\n".join(f"- {r}" for r in reflections) or "（暂无反思）"
    return f"[答案] task={task} | 已参考反思：{memory}"

# 2. Evaluator：返回 (是否通过, 反馈)
def evaluator(answer: str) -> Tuple[bool, str]:
    ok = "正确" in answer  # 玩具规则：必须包含“正确”
    return ok, "需要包含关键字『正确』" if not ok else "通过"

# 3. Reflector：根据失败反馈生成反思文本
def reflector(task: str, answer: str, feedback: str) -> str:
    return f"任务『{task}』失败原因：{feedback}；下次需修正。"

def reflexion_loop(task: str, max_attempts: int = 3) -> str:
    reflections: List[str] = []
    for i in range(1, max_attempts + 1):
        ans = actor(task, reflections)
        ok, fb = evaluator(ans)
        print(f"Attempt {i}: ok={ok}, feedback={fb}")
        if ok:
            return ans
        reflections.append(reflector(task, ans, fb))  # 4. 累积反思
    return "达到最大尝试次数"

if __name__ == "__main__":
    print(reflexion_loop("写出一个单词"))
```

运行后你会看到反思被逐轮“喂回”给 Actor，这就是反思模式的本质。

---

## 三、评估器（Evaluator）：反思是否有效，全靠它

反思循环的质量取决于**评估信号**是否可靠。评估器分三类：

1. **客观评估**：单元测试、编译通过、Schema 校验、数学公式代入验证。**最可靠**。
2. **规则/启发式**：字数、关键字、正则。**便宜但不精确**。
3. **LLM 裁判（LLM-as-a-Judge）**：用另一个 LLM 打分或判对错。**通用但会漂移**。

工程建议：**能客观就客观**。反思循环天然适配代码、SQL、数学题这类**有可执行验证**的任务。

下面用 Python 的 `exec` 做一个真实的“运行单元测试”评估器：

```python
# evaluator_exec.py
# 用真实执行来评估 LLM 生成的代码，是最可靠的评估方式

def code_evaluator(generated_func_src: str, test_cases):
    """
    generated_func_src: 一段定义函数的源码字符串，如 'def add(a,b): return a+b'
    test_cases: [(args, expected), ...]
    返回 (是否全部通过, 反馈文本)
    """
    ns = {}  # 命名空间
    try:
        exec(generated_func_src, ns)
    except Exception as e:
        return False, f"代码无法编译/执行：{e!r}"

    func_names = [n for n in ns if callable(ns[n]) and not n.startswith("__")]
    if not func_names:
        return False, "源码里没有定义任何函数"
    fn = ns[func_names[0]]

    errors = []
    for args, expected in test_cases:
        try:
            got = fn(*args)
        except Exception as e:
            errors.append(f"调用 {fn.__name__}{args} 抛异常：{e!r}")
            continue
        if got != expected:
            errors.append(f"{fn.__name__}{args} 期望 {expected}，实得 {got}")
    return (len(errors) == 0), ("全部通过" if not errors else "; ".join(errors))

if __name__ == "__main__":
    src = "def add(a, b):\n    return a + b\n"
    print(code_evaluator(src, [((1, 2), 3), ((0, 0), 0)]))
    bad = "def add(a, b):\n    return a - b\n"
    print(code_evaluator(bad, [((1, 2), 3)]))
```

这类评估器把“是否正确”变成机器可判定的信号，反思就有了“靶心”。

---

## 四、反思记忆（Reflection Memory）：让经验可累积

反思文本必须**结构化且可复用**。否则每次反思一堆废话，下一轮 prompt 里塞满无关信息，反而拖累模型。

一个实用的模板：

```
<失败原因>
<具体反例（哪一步错）>
<改进策略（可操作的动作）>
```

同时要**去重/压缩**，避免反思越滚越长。简单做法：

- 只保留最近 K 条反思；
- 或让 LLM 把历史反思“摘要成一份 checklist”。

```python
# memory.py
# 反思记忆：去重 + 限长，避免 prompt 无限膨胀

from collections import OrderedDict
from typing import Iterable, List

class ReflectionMemory:
    def __init__(self, capacity: int = 5):
        self.capacity = capacity
        self._items: "OrderedDict[str, None]" = OrderedDict()

    def add(self, reflection: str) -> None:
        r = reflection.strip()
        if not r:
            return
        # 已存在则移到最新
        self._items.pop(r, None)
        self._items[r] = None
        # 超出容量淘汰最旧
        while len(self._items) > self.capacity:
            self._items.popitem(last=False)

    def extend(self, refs: Iterable[str]) -> None:
        for r in refs:
            self.add(r)

    def as_prompt_block(self) -> str:
        if not self._items:
            return "（暂无历史反思）"
        return "\n".join(f"- {r}" for r in self._items.keys())

if __name__ == "__main__":
    mem = ReflectionMemory(capacity=3)
    mem.extend(["r1", "r2", "r3", "r4", "r2"])
    print(mem.as_prompt_block())
```

注意 `OrderedDict.popitem(last=False)` 的用法：弹出最旧一条，这是 LRU（Least Recently Used，最近最少使用）风格的淘汰策略。

---

## 五、工程化要点与陷阱

把反思模式真正上线，需要关注以下工程问题：

1. **评估器优先选客观信号**。LLM 裁判会“幻觉”，尤其是打分类评分。
2. **反思要短、要具体、要可操作**。避免出现“下次更努力”这种废话。
3. **设置重试上限**。`max_attempts` 防止死循环 + 烧钱。
4. **记录轨迹（trace）**。每一轮的 actor 输出、评估反馈、反思都要落日志，便于调试与 ablation（消融实验）。
5. **反思 ≠ 重试**。纯重试只是换一次随机性；反思必须让下一轮 prompt 里出现**新信息**。
6. **反思可以跨任务共享**。同一类任务的反思可以放进向量库（vector store），做跨会话的“经验复用”。
7. **提示注入风险**：如果反思文本由外部/不可信输入构造，可能被注入恶意指令，需要清洗。

下面这个例子把“有反思”与“无反思”做对比，直观展示增益：

```python
# ab_test_reflexion.py
# 对比：无反思 vs 有反思 在同一个“需要给函数加上类型注解”的任务上的表现

from typing import List

# 玩具 Actor：无反思时永远给出同一个错误答案
def actor(task: str, reflections: List[str]) -> str:
    if not reflections:
        return "def add(a, b): return a + b"  # 缺类型注解
    if "类型注解" in " ".join(reflections):
        return "def add(a: int, b: int) -> int: return a + b"
    return "def add(a, b): return a + b"

# Evaluator：检查是否含有 '->' 注解
def evaluator(code: str):
    ok = "->" in code and ":" in code
    return ok, ("通过" if ok else "缺少类型注解（Type Hints）")

def reflector(task, code, feedback):
    return f"上一次输出缺少：{feedback}"

def run(use_reflection: bool):
    reflections: List[str] = []
    for i in range(3):
        code = actor("给 add 函数加类型注解", reflections)
        ok, fb = evaluator(code)
        if ok:
            return i + 1, code
        if use_reflection:
            reflections.append(reflector("task", code, fb))
    return -1, "未成功"

if __name__ == "__main__":
    print("无反思:", run(False))
    print("有反思:", run(True))
```

运行后会看到：无反思的 Actor 一直给同一个错误答案；有反思的 Actor 在拿到反思后作出了修正。

---

## 收束

Reflexion 的本质：**用语言承载强化信号 + 用记忆改变下一轮 prompt**。它把“训练模型去变好”转换成“训练提示去变好”，工程成本低、可解释性强，是目前 Agent 循环里最常用的模式之一。理解了 Actor / Evaluator / Reflector / Memory 四件套 + 循环终止条件，你就能把任何 LLM 任务改造成具备自我改进能力的智能体。

```python
# reflexion_demo.py
# 完整可运行的最小 Reflexion 演示：任务 = 写一个通过所有测试用例的 add 函数
# 运行：python reflexion_demo.py

from typing import Callable, List, Tuple

TEST_CASES = [((1, 2), 3), ((0, 0), 0), ((-1, 1), 0)]

# --- 1. Actor：可被反思“纠正”的伪 LLM ---
def actor(reflections: List[str]) -> str:
    joined = " ".join(reflections)
    if "减法" in joined:
        # 已经知道上次用了减法，这次改成加法
        return "def add(a, b):\n    return a + b\n"
    # 第一轮：故意写错（用减法）
    return "def add(a, b):\n    return a - b\n"

# --- 2. Evaluator：真实执行 + 断言 ---
def evaluator(src: str) -> Tuple[bool, str]:
    ns = {}
    try:
        exec(src, ns)
    except Exception as e:
        return False, f"执行异常：{e!r}"
    fn = ns.get("add")
    if not callable(fn):
        return False, "未定义 add 函数"
    details = []
    for args, expected in TEST_CASES:
        try:
            got = fn(*args)
        except Exception as e:
            details.append(f"add{args} 抛异常 {e!r}")
            continue
        if got != expected:
            details.append(f"add{args} 期望 {expected} 实得 {got}")
    return (not details), ("通过" if not details else "; ".join(details))

# --- 3. Reflector：把反馈转成“可操作反思” ---
def reflector(src: str, feedback: str) -> str:
    if "期望 3 实得 -1" in feedback or "减法" in src:
        return "上次用减法实现 add，应改用加法。"
    return f"上次失败：{feedback}"

# --- 4. 主循环 ---
def reflexion_loop(max_attempts: int = 3) -> str:
    reflections: List[str] = []
    for i in range(1, max_attempts + 1):
        src = actor(reflections)
        ok, fb = evaluator(src)
        print(f"[Attempt {i}] ok={ok} feedback={fb}")
        if ok:
            print("最终代码：\n" + src)
            return src
        reflections.append(reflector(src, fb))
    print("达到最大尝试次数，未通过。")
    return ""

if __name__ == "__main__":
    reflexion_loop()

# 预期输出：
# [Attempt 1] ok=False feedback=add(1, 2) 期望 3 实得 -1; ...
# [Attempt 2] ok=True feedback=通过
# 最终代码：
# def add(a, b):
#     return a + b
```

## agent.pattern.self_consistency

# agent.pattern.self_consistency：让 Agent 自己投票，答案更稳

> **一句话直觉**：同一个问题让模型独立答多次，再取“多数票”，通常比只答一次更可靠——这就是自一致性（self-consistency）。

---

## 1. 为什么需要自一致性？

大语言模型（LLM, Large Language Model）的输出带有随机性（randomness）。同一个问题问两次，可能得到不同答案。如果其中一次答错了，单次结果就不可信。

自一致性（self-consistency）的核心思想是：**不要相信一次采样，而是采样多条推理路径，用投票选出最一致的答案**。它源于一个简单观察：复杂推理题中，正确答案往往会被多条不同推理路径同时得到，而错误答案通常各自为政。

**关键结论**：自一致性 = 多次独立采样 + 答案聚合（通常取众数）。

```python
# 直觉演示：同一个问题问 5 次，统计答案分布
answers = ["42", "42", "41", "42", "43"]
from collections import Counter

# 众数（mode）就是出现次数最多的答案
tally = Counter(answers)
print("票数统计:", tally)
print("最终答案:", tally.most_common(1)[0][0])  # 输出 42
```

---

## 2. 最小实现：从一次调用到多次投票

一个可复用的自一致性函数需要三部分：

1. **采样器（sampler）**：给出一次回答；
2. **聚合器（aggregator）**：把多个回答归并成最终答案；
3. **主流程**：并行或串行调用 N 次，然后聚合。

下面先写一个不依赖任何大模型 API 的纯逻辑版本，方便理解。

**关键结论**：把“模型”抽象成一个函数，自一致性就是“调用 N 次 + 统计”。

```python
from collections import Counter
from typing import Callable

def self_consistency(
    question: str,
    sampler: Callable[[str], str],  # 采样一次，返回答案字符串
    n: int = 5,                     # 采样次数
) -> str:
    """采样 n 次，返回出现次数最多的那个答案。"""
    answers = [sampler(question) for _ in range(n)]
    return Counter(answers).most_common(1)[0][0]

# 一个假“模型”：60% 概率答对，40% 概率答错
import random
random.seed(0)

def fake_model(q: str) -> str:
    return "42" if random.random() < 0.6 else random.choice(["41", "43"])

print(self_consistency("6*7=?", fake_model, n=9))  # 大概率输出 42
```

---

## 3. 工程进阶：归一化与并行

真实场景里，答案表面不同但语义相同。例如 `"42"`、`" 42 "`、`"答案是42"` 应该视为同一票。因此聚合前要做**归一化（normalization）**。

另外，采样是 I/O 密集任务，用线程池（thread pool）并行能把 N 次调用压缩到接近一次的时间。

**关键结论**：工程化的自一致性 = 归一化 + 并行采样 + 稳健投票。

```python
import re
import random
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

def normalize(text: str) -> str:
    """抽取文本中的数字/小写字母，用于把语义相同的答案归为一票。"""
    text = text.strip().lower()
    m = re.search(r"-?\d+", text)   # 简单场景：只取数字
    return m.group(0) if m else text

def self_consistency_v2(
    question: str,
    sampler: Callable[[str], str],
    n: int = 8,
    workers: int = 4,
) -> tuple[str, Counter]:
    """并行采样 n 次，归一化后投票；返回最终答案和完整票数。"""
    with ThreadPoolExecutor(max_workers=workers) as pool:
        raw = list(pool.map(lambda _: sampler(question), range(n)))
    votes = Counter(normalize(a) for a in raw)
    return votes.most_common(1)[0][0], votes

random.seed(1)
def noisy_model(q: str) -> str:
    return random.choice(["The answer is 42", " 42 ", "42!", "41", "43"])

answer, votes = self_consistency_v2("6*7=?", noisy_model, n=20, workers=8)
print("最终答案:", answer)
print("票数分布:", votes)
```

---

## 4. 何时有效、何时失效

自一致性不是银弹，它有明确的适用边界。

**适用**：
- 有**唯一正确答案**的任务：数学题、选择题、事实问答、代码输出。
- 单次采样有随机性，但正确路径“更常被走到”。

**失效**：
- **开放式生成**（写诗、头脑风暴）：没有客观众数。
- **极高错误偏置**：如果模型 95% 都答错，投票也救不回来。
- **成本敏感**：N 次采样 = N 倍 token 成本，需要权衡。

**关键结论**：自一致性适用于“答案可枚举、正确率不为零”的任务。

```python
# 反例：开放式任务没有众数
open_answers = ["写一首诗", "编个故事", "画幅画", "写一首诗"]
# 众数是“写一首诗”，但这只是重复，不是“正确答案”
```

---

## 5. 与 Agent 的关系

在 Agent（智能体）系统中，自一致性常用于：

- **工具调用**：让 Agent 多次规划同一个子任务，投票选出最常被选中的工具/参数；
- **最终答案**：多轮 ReAct（Reason + Act）产生多个答案，投票决定交付哪个；
- **异常兜底**：当单次结果置信度低时，自动开启多采样复核。

它是**最便宜、最容易落地的可靠性增强手段**之一：不需要训练，不需要改模型，只需要包装一层循环。

**关键结论**：自一致性是 Agent 可靠性的“第一道保险”，实现成本极低。

```python
# Agent 场景示意：多次规划，投票选工具
plans = ["search", "search", "calculator", "search", "calculator"]
from collections import Counter
chosen = Counter(plans).most_common(1)[0][0]
print("Agent 选择工具:", chosen)  # search
```

---

## 动手练习

写一个 `majority_vote` 函数，输入一个字符串列表，返回出现次数最多的字符串。要求：

1. 使用 `collections.Counter` 统计；
2. 若出现平票，返回**按字母序最小**的那个（提示：先排序再 `most_common`）；
3. 写 3 个测试用例覆盖：普通多数、平票、全部相同。

然后把它接上你刚才写的 `self_consistency_v2`，用 `n=10` 跑一遍，观察票数分布。

```python
# 参考模板
def majority_vote(answers: list[str]) -> str:
    # TODO: 你的实现
    ...

assert majority_vote(["a", "a", "b"]) == "a"
assert majority_vote(["b", "a"]) == "a"      # 平票取字母序最小
assert majority_vote(["x", "x", "x"]) == "x"
print("全部通过")
```

```python
import re
import random
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

def normalize(text: str) -> str:
    """归一化：抽取数字或小写字母，把语义相同的答案归为一票。"""
    text = text.strip().lower()
    m = re.search(r"-?\d+", text)
    return m.group(0) if m else text

def self_consistency(
    question: str,
    sampler: Callable[[str], str],
    n: int = 8,
    workers: int = 4,
) -> tuple[str, Counter]:
    """并行采样 n 次，归一化后投票；返回最终答案和完整票数。"""
    with ThreadPoolExecutor(max_workers=workers) as pool:
        raw = list(pool.map(lambda _: sampler(question), range(n)))
    votes = Counter(normalize(a) for a in raw)
    return votes.most_common(1)[0][0], votes

# 一个模拟模型：大多数时候答对，偶尔答错
random.seed(42)
def noisy_model(q: str) -> str:
    return random.choice(["The answer is 42", " 42 ", "42!", "41", "43"])

if __name__ == "__main__":
    answer, votes = self_consistency("6*7=?", noisy_model, n=20, workers=8)
    print("最终答案:", answer)
    print("票数分布:", votes)
```


---

## 本课题目

### single_choice · None



- [A] 只执行一次任务并返回结果
- [B] 执行任务后对结果进行自我评估，并根据评估修正后续行为
- [C] 只依赖外部工具调用，不需要模型推理
- [D] 将所有决策完全交给用户人工判断

**参考答案**：1

**解析**：反思模式的关键是“行动—评估—修正”的迭代循环，通过自我反馈提升后续输出质量。

### single_choice · None



- [A] 单次提示
- [B] 反思
- [C] 随机采样
- [D] 纯规则匹配

**参考答案**：1

**解析**：先自我检查、再根据检查结果重新生成，是反思模式的典型流程。

### single_choice · None



- [A] 记忆必须永久存储在硬盘上才有效
- [B] 记忆可以保存此前尝试和反思，供后续轮次参考
- [C] 记忆会替代所有模型推理
- [D] 记忆只能保存数字，不能保存文本

**参考答案**：1

**解析**：在反思模式中，记忆通常用于保存历史尝试与反思，使后续轮次能参考过去经验。

### single_choice · None



- [A] 只需要返回当前时间的简单查询
- [B] 需要多步推理且答案质量可通过反馈逐步提升的任务
- [C] 只需要做一次乘法运算
- [D] 只需要读取一个固定常量

**参考答案**：1

**解析**：反思模式适合需要多步推理、能够根据反馈逐步改进的任务，而不是极简单的一次性查询。

### single_choice · None



- [A] 智能体更早停止，可能错过明显可改进的错误
- [B] 智能体一定会无限循环
- [C] 模型参数会翻倍
- [D] 用户输入会被改写

**参考答案**：0

**解析**：评估过于宽松会让本应继续修正的情况被判定为通过，导致过早停止并保留错误。

### single_choice · None



- [A] 反思内容越长越好，不需要筛选
- [B] 反思内容应简洁、具体，并聚焦可执行的改进点
- [C] 必须把完整历史逐字全部拼进去，不能摘要
- [D] 反思内容必须使用另一种编程语言

**参考答案**：1

**解析**：反思内容如果冗长或模糊，会浪费上下文并干扰模型；简洁具体的改进点更有帮助。

### single_choice · None



- [A] 纯随机生成
- [B] 反思
- [C] 一次性编译
- [D] 静态类型检查

**参考答案**：1

**解析**：根据测试失败信息进行修改并重试，是反思模式在代码生成中的典型体现。

### single_choice · None



- [A] 多轮反思一定比单轮差
- [B] 多轮反思允许模型根据反馈迭代改进，但也会增加开销
- [C] 单轮模式一定包含反思步骤
- [D] 多轮反思不需要任何输入

**参考答案**：1

**解析**：多轮反思通过迭代反馈可能提升质量，但也带来更多计算与调用成本。

### single_choice · None



- [A] 模型随机输出一个数字
- [B] 评估器判定结果已满足要求，或达到最大轮数
- [C] 用户关闭显示器
- [D] 程序开始运行

**参考答案**：1

**解析**：常见终止条件包括评估通过或达到预设最大轮数，以避免无休止反思。

### single_choice · None



- [A] 模型必然自动修正所有错误
- [B] 模型可能重复相同错误，因为没有获得新的改进信息
- [C] 系统会自动切换成另一个模型
- [D] 用户输入会被自动清空

**参考答案**：1

**解析**：没有反思信号时，重复输入相同内容很难带来改进，容易重复原有错误。

### single_choice · None



- [A] 替代模型进行所有推理
- [B] 为评估或反思提供客观信号
- [C] 自动修改用户需求
- [D] 保证模型不需要任何输入

**参考答案**：1

**解析**：外部工具能提供测试结果、检索信息等客观信号，帮助评估器生成更可靠的反思。

### single_choice · None



- [A] 一次失败后永远放弃
- [B] 从失败中提取原因，并在下一次尝试中调整策略
- [C] 忽略失败，继续随机尝试
- [D] 把所有失败原因都归咎于用户

**参考答案**：1

**解析**：试错学习强调从失败中提炼可复用经验，并在后续尝试中改进策略。

### single_choice · None



- [A] 自我评估只能由人工完成
- [B] 自我评估的结果可以用于指导下一轮尝试
- [C] 自我评估必须返回布尔值 True 或 False
- [D] 自我评估会直接修改原始用户输入

**参考答案**：1

**解析**：自我评估的目的是产生可操作的反馈，用于改进后续轮次，而不是直接修改用户输入。

### single_choice · None



- [A] 指出上一轮答案中的逻辑漏洞
- [B] 给出下一轮应重点改进的方向
- [C] 记录本轮尝试中缺失的关键信息
- [D] 直接返回一个完全无关的随机字符串

**参考答案**：3

**解析**：反思步骤应产生与任务相关的诊断信息，随机字符串没有反思价值。

### single_choice · None



- [A] 必须使用 GPU 训练模型
- [B] 需要额外的模型调用或计算轮次
- [C] 必须连接互联网
- [D] 必须使用数据库

**参考答案**：1

**解析**：反思通常需要多轮生成、评估或修正，因此会增加调用次数或计算开销。

### single_choice · None



- [A] 模型一定会自动变聪明
- [B] 可能陷入无限循环或过度修正
- [C] 用户输入会被自动删除
- [D] 系统会跳过所有评估步骤

**参考答案**：1

**解析**：缺少终止条件时，反复反思可能导致循环或过度修正，因此通常需要最大轮数等限制。

### single_choice · None



- [A] 增加模型参数数量
- [B] 把历史反思作为上下文，帮助模型避免重复错误
- [C] 替代所有外部工具调用
- [D] 保证输出一定完全正确

**参考答案**：1

**解析**：把反思写入后续上下文，可以让模型在下一轮生成时参考此前教训，减少重复错误。

### single_choice · None



- [A] result = model(prompt); return result
- [B] while 未达到最大轮数: 生成结果; 评估结果; 若通过则结束; 否则生成反思并加入下一轮输入
- [C] for i in range(10): print(i)
- [D] if user_input == '': raise ValueError

**参考答案**：1

**解析**：反思模式的基本结构包含生成、评估、条件终止以及将反思反馈到下一轮。

### single_choice · None



- [A] 生成最终用户界面
- [B] 判断上一轮输出是否满足要求，并提供反馈信号
- [C] 替代所有业务逻辑
- [D] 永久保存用户密码

**参考答案**：1

**解析**：评估器用于判断当前输出质量并产生反馈，是反思循环能否继续或终止的关键。

### single_choice · None



- [A] 永远继续，不设任何上限
- [B] 达到预设最大轮数后返回当前最佳结果或报告失败
- [C] 直接删除用户问题
- [D] 忽略评估结果并继续调用

**参考答案**：1

**解析**：为避免无限循环，应设置最大轮数，并在达到上限后返回当前最佳结果或明确失败。

### single_choice · None



- [A] 让智能体只执行一次推理，以减少计算成本
- [B] 让智能体对同一问题多次独立推理，再对结果进行聚合或投票
- [C] 让智能体在每次推理时都使用相同的随机种子以保证一致性
- [D] 让智能体将任务拆分成多个子任务并顺序执行

**参考答案**：1

**解析**：self-consistency 的核心是多次独立采样推理路径，然后通过多数投票等方式聚合结果，以提高答案的可靠性。选项 A 与自洽性相反；选项 C 虽然看似一致，但自洽性恰恰依赖多样化采样而非固定种子；选项 D 描述的是任务分解模式。

### single_choice · None



- [A] self-consistency 总是比单次推理更快，因为可以并行
- [B] self-consistency 通过多路径采样降低了单次推理中因随机性导致的错误，但计算开销更大
- [C] self-consistency 不需要任何推理过程，直接输出答案
- [D] self-consistency 只能用于数学题，不能用于其他领域

**参考答案**：1

**解析**：self-consistency 通过多路径采样和聚合提高了鲁棒性，但需要多次推理，计算成本高于单次链式推理。A 错误，因为更多推理通常更慢；C 错误，因为它仍然依赖推理过程；D 错误，因为该方法可迁移到多种需要推理的任务。

### multi_choice · None



- [A] 需要从多个候选答案中选出最一致答案的逻辑推理题
- [B] 对同一段代码进行多次独立审查，汇总发现的缺陷
- [C] 要求实时响应且计算预算极低的简单查询
- [D] 需要高可靠性的数学计算题
- [E] 生成一段没有标准答案的创意故事

**参考答案**：[0, 1, 3]

**解析**：self-consistency 适合有可聚合答案且对可靠性要求高的任务，如逻辑推理、数学计算和多次独立审查。实时低预算场景不适合，因为多路径采样开销大；无标准答案的创意生成也难以投票。

### multi_choice · None



- [A] 对最终答案进行多数投票
- [B] 根据每条路径的置信度进行加权投票
- [C] 随机选择其中一条路径的答案
- [D] 先对答案进行归一化或等价性判断，再投票
- [E] 直接拼接所有路径的答案作为最终输出

**参考答案**：[0, 1, 3]

**解析**：多数投票、加权投票以及先归一化再投票都是合理的聚合策略。随机选择忽略了聚合的意义；直接拼接所有答案通常不是有效的最终输出。

### fill_blank · None



**参考答案**：["多数投票", "投票", "majority vote", "majority voting"]

**解析**：最常见的聚合方法是多数投票（majority vote），即选择出现次数最多的答案。

### fill_blank · None



**参考答案**：["多", "多于一", ">=2", "若干", "multiple", "several"]

**解析**：self-consistency 通过生成多条（多于一）推理路径并聚合结果来提高可靠性。

### fill_blank · None



**参考答案**：["温度", "temperature", "随机性", "采样温度"]

**解析**：提高温度（temperature）可以增加采样的随机性，从而产生多样化的推理路径。贪婪解码会消除这种多样性。

### code_reading · None



**参考答案**：体现了 self-consistency（自洽性）模式。关键步骤是：对同一问题多次独立采样（temperature=0.8 引入随机性），然后用 most_common 进行多数投票聚合，得到最终答案。

**解析**：代码通过循环多次调用 solve 并改变温度来生成多条路径，再用 most_common 聚合，这正是 self-consistency 的典型实现。

### code_reading · None



**参考答案**：没有体现 self-consistency。因为它只生成了一条路径（n=1），且 temperature=0.0 表示贪婪解码，没有多样性和聚合过程，只是单次确定性推理。

**解析**：self-consistency 需要多条独立采样路径并进行聚合。该代码只采样一次且温度为 0，不具备多样性和投票机制。

### code_reading · None



**参考答案**：返回 'B'。这体现了多数投票（majority vote）聚合策略，选择出现次数最多的答案。

**解析**：results 中 'B' 出现 2 次，'A' 出现 1 次，max 根据计数选择 'B'。这是 self-consistency 中常用的多数投票聚合。

### scenario · None



**解析**：应用 self-consistency 时，团队应对同一问题多次独立采样生成多条推理路径，通过多数投票等聚合策略选择最终答案。关键点包括：保证采样多样性（如提高温度）、选择合适的采样次数、设计聚合策略，并权衡增加的计算成本。

### scenario · None



**解析**：所有路径犯同一错误说明可能存在系统性偏差或采样多样性不足。改进方向包括：调整采样策略（如提高温度、使用不同提示词或角色设定）、检查提示词是否引导了错误方向，以及评估模型本身的能力是否不足以解决该问题。

### single_choice · None



- [A] A
- [B] B
- [C] C
- [D] 无法确定，需要重新生成

**参考答案**：0

**解析**：多数投票选择出现次数最多的答案。A 出现 3 次，B 和 C 各 1 次，因此最终答案为 A。

### single_choice · None



- [A] 多次采样必须使用完全相同的提示词和相同的随机种子
- [B] 多次采样应使用相同提示词但允许解码过程引入随机性，从而产生不同推理路径
- [C] 每次采样都必须人工修改提示词以引入多样性
- [D] 独立采样意味着每次采样不能使用相同的模型

**参考答案**：1

**解析**：独立采样指在相同输入下通过解码随机性（如温度采样）生成多条不同推理路径。固定随机种子会消除多样性，人工修改提示词或更换模型则不是标准做法。

### single_choice · None



- [A] 每条推理路径的中间步骤
- [B] 每条推理路径的最终答案
- [C] 每条推理路径对应的模型参数
- [D] 每条推理路径的提示词长度

**参考答案**：1

**解析**：self-consistency 通常在最终答案层面进行聚合，如多数投票。中间步骤可能不同，参数和提示词长度不是聚合对象。

### single_choice · None



- [A] 将一段文本从英文翻译成中文，只要求一种标准译法
- [B] 求解一道有唯一数值答案的数学应用题
- [C] 根据用户输入生成一首自由格式的诗歌
- [D] 对一张图片进行物体分类，且模型只输出一个标签

**参考答案**：1

**解析**：self-consistency 适合有可比较、可聚合的最终答案的任务，如有唯一数值答案的数学题。自由格式诗歌没有统一答案，难以投票；翻译和分类通常需要单一确定性输出，也不适合多路径投票。

### single_choice · None



- [A] 采样次数太少，导致没有覆盖到正确答案
- [B] 模型对这个问题有系统性偏差，且采样多样性不足
- [C] 多数投票算法本身有缺陷，无法处理相同答案
- [D] self-consistency 模式不适用于任何任务

**参考答案**：1

**解析**：当所有路径都给出相同错误答案时，通常说明模型存在系统性偏差，或者采样多样性不足（如温度过低），导致错误被一致地重复。增加采样多样性或次数可能缓解，但根本原因在于偏差和多样性。

### single_choice · None



- [A] 降低 top-k 的值到 1
- [B] 提高温度（temperature）或使用核采样（top-p）
- [C] 将最大生成长度设置为 1
- [D] 关闭所有随机性，使用贪婪解码

**参考答案**：1

**解析**：提高温度或使用核采样可以增加输出的随机性，从而产生多样化的推理路径。贪婪解码和 top-k=1 都会降低多样性；最大生成长度与多样性无关。

### multi_choice · None



- [A] 采样路径的数量
- [B] 单条路径推理的质量
- [C] 聚合策略（如多数投票、加权投票）
- [D] 模型的参数量大小
- [E] 采样时引入的多样性程度

**参考答案**：[0, 1, 2, 4]

**解析**：采样数量、单条路径质量、聚合策略和多样性程度都会直接影响自洽性结果的可靠性。模型参数量虽然可能间接影响能力，但不是 self-consistency 流程设计中的直接决定因素，因此不作为必选项。

### multi_choice · None



- [A] 计算成本随采样次数线性增长
- [B] 对于没有唯一正确答案的开放式生成任务，投票聚合效果有限
- [C] 它完全消除了模型的所有错误
- [D] 如果所有采样路径共享同一系统性偏差，投票也无法纠正
- [E] 它通常需要能够比较或聚合最终答案的机制

**参考答案**：[0, 1, 3, 4]

**解析**：self-consistency 的计算成本随采样次数增加；开放式任务难以投票；系统性偏差无法通过投票消除；需要可聚合的答案机制。它并不能消除所有错误，因此 C 错误。
