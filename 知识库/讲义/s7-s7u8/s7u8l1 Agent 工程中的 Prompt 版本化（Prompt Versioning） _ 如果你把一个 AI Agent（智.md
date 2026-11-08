# s7u8l1 Agent 工程中的 Prompt 版本化（Prompt Versioning） / 如果你把一个 AI Agent（智能体）改了一行提示词就

> 来源 `content/lessons/s7u8l1.json`

## agent.eng.prompt_versioning

# Agent 工程中的 Prompt 版本化（Prompt Versioning）

## 一句话直觉

**Prompt 是 Agent 的“源代码”之一：它一改，行为、成本、安全性和评测结果都可能变，所以必须像代码一样可追踪、可回滚、可对比、可审计。**

学习 `agent.eng.prompt_versioning` 的目标不是“把提示词存进 Git”这么简单，而是建立一套工程机制：让每一次 Prompt（提示词）变更都有版本号（version）、变更记录（changelog）、实验对照（A/B test）、回滚点（rollback point）和评测指标（evaluation metrics）。

---

## 1. 为什么 Prompt 需要版本化

在传统软件里，代码变更可以通过 Git（分布式版本控制系统）追踪。Agent 系统里，Prompt 往往同时承担：

- 任务说明：告诉模型要做什么。
- 约束条件：禁止什么、必须遵守什么。
- 工具调用规范：如何调用函数、如何输出 JSON。
- 安全边界：防注入、防越权、防泄露。
- 风格与人格：客服语气、品牌口吻、角色设定。

因此 Prompt 变更会直接影响：

- 正确率（accuracy）
- 延迟（latency）
- Token 成本（token cost）
- 安全风险（security risk）
- 用户满意度（user satisfaction）

如果没有版本化，常见问题包括：

1. 线上效果变差，但不知道是哪次 Prompt 改动导致。
2. 多人协作时互相覆盖 Prompt。
3. 回滚只能靠记忆和聊天记录。
4. A/B 测试无法复现。
5. 审计时无法证明当时到底用了哪版 Prompt。


## 2. Prompt 版本化的最小模型

一个可工程化的 Prompt 版本，至少应包含：

- `prompt_id`：Prompt 的稳定标识，例如 `customer_support_agent`。
- `version`：版本号，例如 `1.0.0` 或 `2025-04-01.1`。
- `template`：提示词模板，可含变量占位符。
- `variables`：模板变量定义。
- `model_config`：模型名、温度、最大 token 等。
- `created_at`：创建时间。
- `author`：作者。
- `changelog`：变更说明。
- `tags`：如 `prod`、`staging`、`experiment`。
- `eval_score`：离线评测分数。

最小心智模型：

```text
Prompt = 模板 + 变量 + 模型配置 + 版本元数据
```

这意味着版本化不只是保存字符串，而是保存“可运行配置”。


## 3. 用 Python 实现一个 Prompt 注册表

下面实现一个轻量级 `PromptRegistry`（提示词注册表）。它支持：

- 注册新版本
- 获取指定版本
- 获取当前生产版本
- 回滚到旧版本
- 列出历史

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class PromptVersion:
    prompt_id: str
    version: str
    template: str
    model: str = "gpt-4o-mini"
    temperature: float = 0.0
    changelog: str = ""
    author: str = "unknown"
    tags: List[str] = field(default_factory=list)
    eval_score: Optional[float] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class PromptRegistry:
    def __init__(self):
        self._store: Dict[str, List[PromptVersion]] = {}
        self._production: Dict[str, str] = {}

    def register(self, pv: PromptVersion) -> None:
        self._store.setdefault(pv.prompt_id, []).append(pv)

    def get(self, prompt_id: str, version: str) -> PromptVersion:
        for pv in self._store.get(prompt_id, []):
            if pv.version == version:
                return pv
        raise KeyError(f"Prompt {prompt_id} version {version} not found")

    def promote(self, prompt_id: str, version: str) -> None:
        self.get(prompt_id, version)
        self._production[prompt_id] = version

    def get_production(self, prompt_id: str) -> PromptVersion:
        version = self._production[prompt_id]
        return self.get(prompt_id, version)

    def rollback(self, prompt_id: str, version: str) -> None:
        self.promote(prompt_id, version)

    def history(self, prompt_id: str) -> List[PromptVersion]:
        return list(self._store.get(prompt_id, []))
```

关键结论：**生产环境不应直接引用“最新版”，而应引用一个明确的版本号或别名。** 这样回滚才是确定性的。


## 4. 版本别名与环境隔离

工程中常见做法是使用别名：

- `prod`：当前生产版本
- `staging`：预发布版本
- `canary`：灰度版本
- `experiment_a`：实验组 A

调用方只写 `prompt_id + alias`，由注册表解析到具体版本。

```python
registry = PromptRegistry()

registry.register(PromptVersion(
    prompt_id="support_agent",
    version="1.0.0",
    template="你是客服助手，请用简洁中文回答：{question}",
    changelog="初始版本",
    author="alice",
    tags=["prod"],
))

registry.register(PromptVersion(
    prompt_id="support_agent",
    version="1.1.0",
    template="你是专业客服助手。请先确认用户问题，再给出步骤化回答：{question}",
    changelog="增加步骤化回答要求",
    author="bob",
    tags=["staging"],
    eval_score=0.86,
))

registry.promote("support_agent", "1.0.0")
prod = registry.get_production("support_agent")
print(prod.version, prod.template)
```

关键结论：**别名让调用方稳定，版本号让行为可追踪。**


## 5. Prompt 变更管理与评测闭环

版本化必须和评测（evaluation）结合，否则只是“存档”。推荐流程：

1. 新 Prompt 注册为 `staging`。
2. 跑离线评测集（golden set）。
3. 对比旧版本指标：准确率、格式合规率、拒答率、平均 token。
4. 通过后提升为 `prod`。
5. 线上监控异常，必要时回滚。

```python
from typing import Callable, List


def evaluate(prompt_version: PromptVersion, cases: List[dict], runner: Callable) -> float:
    correct = 0
    for case in cases:
        output = runner(prompt_version.template, case["input"])
        if case["expected"] in output:
            correct += 1
    return correct / len(cases)


# 模拟评测
cases = [
    {"input": "如何退货？", "expected": "退货"},
    {"input": "发票怎么开？", "expected": "发票"},
]

def fake_runner(template: str, user_input: str) -> str:
    return template.format(question=user_input) + " 退货 发票"

v1 = registry.get("support_agent", "1.0.0")
score = evaluate(v1, cases, fake_runner)
print("eval score:", score)
```

关键结论：**没有评测的 Prompt 版本化，只是文件管理；有评测的版本化，才是工程闭环。**


## 6. 工程落地建议

- 把 Prompt 当作配置文件或代码资产，纳入 Git。
- 使用注册表或配置中心管理版本别名。
- 每次变更必须写 changelog。
- 生产调用记录 `prompt_id + version`，便于审计。
- 新版本先 staging，再 canary，再 prod。
- 回滚必须一键完成。
- 评测集要版本化，避免“评测标准漂移”。


## 动手练习

**任务：实现一个带评测门禁的 Prompt 发布流程。**

要求：

1. 创建 `PromptRegistry`。
2. 注册两个版本：`1.0.0` 和 `1.1.0`。
3. 实现 `evaluate` 函数，用至少 3 条测试用例评测两个版本。
4. 只有 `1.1.0` 的评测分数高于 `1.0.0` 且大于等于 0.8 时，才允许 `promote` 到生产。
5. 打印生产版本、评测分数和历史记录。
6. 额外挑战：实现 `rollback` 并演示回滚到 `1.0.0`。

提交内容：Python 脚本 + 运行输出截图或文本。

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Callable


@dataclass
class PromptVersion:
    prompt_id: str
    version: str
    template: str
    model: str = "gpt-4o-mini"
    temperature: float = 0.0
    changelog: str = ""
    author: str = "unknown"
    tags: List[str] = field(default_factory=list)
    eval_score: Optional[float] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class PromptRegistry:
    def __init__(self):
        self._store: Dict[str, List[PromptVersion]] = {}
        self._production: Dict[str, str] = {}

    def register(self, pv: PromptVersion) -> None:
        self._store.setdefault(pv.prompt_id, []).append(pv)

    def get(self, prompt_id: str, version: str) -> PromptVersion:
        for pv in self._store.get(prompt_id, []):
            if pv.version == version:
                return pv
        raise KeyError(f"Prompt {prompt_id} version {version} not found")

    def promote(self, prompt_id: str, version: str) -> None:
        self.get(prompt_id, version)
        self._production[prompt_id] = version

    def get_production(self, prompt_id: str) -> PromptVersion:
        return self.get(prompt_id, self._production[prompt_id])

    def rollback(self, prompt_id: str, version: str) -> None:
        self.promote(prompt_id, version)

    def history(self, prompt_id: str) -> List[PromptVersion]:
        return list(self._store.get(prompt_id, []))


def evaluate(pv: PromptVersion, cases: List[dict], runner: Callable[[str, str], str]) -> float:
    correct = 0
    for case in cases:
        output = runner(pv.template, case["input"])
        if case["expected"] in output:
            correct += 1
    return correct / len(cases)


if __name__ == "__main__":
    registry = PromptRegistry()

    registry.register(PromptVersion(
        prompt_id="support_agent",
        version="1.0.0",
        template="你是客服助手，请用简洁中文回答：{question}",
        changelog="初始版本",
        author="alice",
    ))

    registry.register(PromptVersion(
        prompt_id="support_agent",
        version="1.1.0",
        template="你是专业客服助手。请先确认用户问题，再给出步骤化回答：{question}",
        changelog="增加步骤化回答要求",
        author="bob",
    ))

    cases = [
        {"input": "如何退货？", "expected": "退货"},
        {"input": "发票怎么开？", "expected": "发票"},
        {"input": "物流多久到？", "expected": "物流"},
    ]

    def fake_runner(template: str, user_input: str) -> str:
        return template.format(question=user_input) + " 退货 发票 物流"

    v1 = registry.get("support_agent", "1.0.0")
    v2 = registry.get("support_agent", "1.1.0")

    score1 = evaluate(v1, cases, fake_runner)
    score2 = evaluate(v2, cases, fake_runner)
    v1.eval_score = score1
    v2.eval_score = score2

    print("v1 score:", score1)
    print("v2 score:", score2)

    registry.promote("support_agent", "1.0.0")
    print("initial prod:", registry.get_production("support_agent").version)

    if score2 >= 0.8 and score2 > score1:
        registry.promote("support_agent", "1.1.0")
        print("promoted prod:", registry.get_production("support_agent").version)

    registry.rollback("support_agent", "1.0.0")
    print("after rollback:", registry.get_production("support_agent").version)

    for pv in registry.history("support_agent"):
        print(pv.version, pv.changelog, pv.eval_score)
```

## agent.eng.eval_ci

## 一句话直觉

如果你把一个 AI Agent（智能体）改了一行提示词就上线，你怎么知道它没变笨？`eval_ci` 就是把「评测」变成「持续集成」——每次改代码自动跑一遍测试集，用分数说话，而不是靠感觉。

---

## 1. 为什么 Agent 需要评测（Evaluation）

传统软件的测试是**确定性**的：`add(1,2)` 永远等于 3。而 Agent 的输出是**自然语言 + 工具调用（tool call）**，同一句提示可能返回十种说法，所以不能用 `assert output == "预期值"` 这种写法。

我们需要的是**评测集（eval set）**：一批输入 + 一批判定标准，跑完后得到一个**可比较的分数（score）**。

关键结论：**没有评测分数，就没有资格谈「这次改动是优化」**。

```python
# 最小评测骨架：输入用例 -> 跑 Agent -> 打分成数字
def evaluate(agent_fn, cases, judge_fn):
    total = 0
    for case in cases:                 # 遍历每条测试用例
        output = agent_fn(case["input"])   # 调用待评测的 Agent
        total += judge_fn(output, case["expected"])  # 累加得分
    return total / len(cases)          # 返回平均分
```

---

## 2. 三种打分方式：精确、语义、LLM 裁判

实际工程里有三种主流判定器（judge）：

1. **精确匹配（Exact Match）**：适合答案唯一，比如工具调用参数。
2. **语义相似（Semantic Similarity）**：用向量（embedding）算相似度，适合开放式问答。
3. **LLM-as-a-Judge（大模型裁判）**：让另一个模型给分，适合复杂推理判断，但要防它「护短」。

关键结论：**判定器本身也要被验证**，否则你只是在用随机数当分数。

```python
from difflib import SequenceMatcher

# 语义相似度的零依赖近似实现（真项目里用 embedding 余弦相似度）
def similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()   # 返回 0~1 的相似度

assert similarity("北京是中国的首都", "中国的首都是北京") > 0.7
```

---

## 3. 从「跑评测」到「持续集成（CI）」

**CI（Continuous Integration，持续集成）** 指的是每次提交代码都自动跑一遍检查。把评测接进 CI，就得到 `eval_ci`：

- 每次 PR（Pull Request）触发评测
- 分数 **低于基线（baseline）就红灯，禁止合并**
- 分数写进日志 / 评论，形成历史曲线

关键结论：**评测的价值不在「跑一次」，而在「每次都跑并卡阈值」**。

```python
BASELINE = 0.80          # 当前主分支的分数下限

def ci_gate(score):
    if score < BASELINE:             # 分数掉线
        raise SystemExit(f"FAIL: {score:.2f} < {BASELINE}")  # 退出码非 0 -> CI 红灯
    print(f"PASS: {score:.2f}")

ci_gate(0.83)   # 正常情况打印 PASS
```

---

## 4. 让评测稳定：可复现性（Reproducibility）

Agent 依赖大模型（LLM），而 LLM 默认带随机性。要让它进 CI，必须做三件事：

1. **temperature=0**：让输出尽量确定。
2. **固定随机种子 + 缓存**：记录每次 LLM 返回，避免重复烧钱。
3. **记录版本**：模型名、提示词哈希、代码 commit 都要入库，否则分数无法归因。

关键结论：**不可复现的评测分数等于噪音**。

```python
import hashlib

def prompt_hash(prompt: str) -> str:
    return hashlib.sha256(prompt.encode()).hexdigest()[:8]  # 提示词指纹

# 把指纹写进结果，方便追溯是哪版提示词跑出的分数
record = {"prompt": prompt_hash("你是助手"), "score": 0.85}
print(record)
```

---

## 5. 工程落地：一个可扩展的目录结构

当你把 `eval_ci` 真正放进项目时，建议这样组织：

```
project/
├── evals/
│   ├── cases.jsonl        # 测试用例，一行一条
│   ├── judges.py          # 各种判定器
│   └── runner.py          # 评测入口
└── .github/workflows/eval.yml   # CI 配置
```

`cases.jsonl` 每行形如 `{"input": "1+1=?", "expected": "2"}`，团队可随时加用例，不需要改代码。

关键结论：**评测集是资产，要当代码一样被 review 和版本管理**。

```python
import json
import hashlib
from dataclasses import dataclass, field
from typing import Callable, List, Dict

# ---------- 1. 定义数据结构 ----------
@dataclass
class Case:
    input: str          # Agent 的输入
    expected: str       # 期望答案

@dataclass
class Report:
    score: float
    detail: List[Dict] = field(default_factory=list)

# ---------- 2. 三种判定器 ----------
def exact_match(pred: str, exp: str) -> float:
    return 1.0 if pred.strip() == exp.strip() else 0.0

def contains(pred: str, exp: str) -> float:
    return 1.0 if exp.strip() in pred else 0.0

def llm_judge_stub(pred: str, exp: str) -> float:
    # 真实项目里换成「调用另一个 LLM 打分」
    return 1.0 if any(ch.isdigit() for ch in pred) else 0.5

# ---------- 3. 评测运行器 ----------
def run_eval(agent_fn: Callable[[str], str],
             cases: List[Case],
             judge_fn: Callable[[str, str], float]) -> Report:
    total, detail = 0.0, []
    for c in cases:
        pred = agent_fn(c.input)                    # 跑 Agent
        s = judge_fn(pred, c.expected)              # 打分
        total += s
        detail.append({"input": c.input, "pred": pred, "score": s})
    return Report(score=total / len(cases), detail=detail)

# ---------- 4. CI 闸门 ----------
def ci_gate(report: Report, baseline: float = 0.8) -> None:
    fingerprint = hashlib.sha256(
        json.dumps([d["input"] for d in report.detail]).encode()
    ).hexdigest()[:8]
    print(f"[eval_ci] case-set fingerprint = {fingerprint}")
    if report.score < baseline:
        raise SystemExit(f"FAIL: score={report.score:.2f} < baseline={baseline}")
    print(f"PASS: score={report.score:.2f}")

# ---------- 5. 演示 ----------
def fake_agent(text: str) -> str:
    # 一个极简的“Agent”：只会回答加法，其他统一回复
    if "+" in text:
        a, b = text.split("+")
        return str(int(a) + int(b))
    return "我不知道"

if __name__ == "__main__":
    cases = [Case("1+1", "2"), Case("2+3", "5"), Case("10+20", "30")]
    report = run_eval(fake_agent, cases, exact_match)
    ci_gate(report, baseline=0.99)
```


---

## 本课题目

### single_choice · None



- [A] 可以随时把线上流量切回某个历史版本的提示词配置
- [B] 可以减小模型的参数量从而降低推理成本
- [C] 可以让模型自动改写提示词而无需人工介入
- [D] 可以绕过对模型输出进行评测的环节

**参考答案**：0

**解析**：保存带配置的提示词版本并标记线上版本，核心价值是支持回滚与切换，出现质量回退时可快速恢复。参数量、自动改写、跳过评测都与版本留存无直接因果关系。

### single_choice · None



- [A] 共享文档不支持多人协作编辑
- [B] 提示词的效果依赖其配套的模型与解码配置，只存文本无法还原运行条件
- [C] 提示词文本在复制过程中被自动修改了
- [D] 半年前的模型版本已经无法再被调用

**参考答案**：1

**解析**：提示词的线上表现由文本与其运行配置共同决定，缺少模型/温度/工具等元数据就无法精确复现。其他选项与「无法复现」这一现象无必然联系。

### single_choice · None



- [A] 保证不同版本之间的差异主要来自提示词本身，而非无关变量
- [B] 减少评测所需的算力消耗
- [C] 使评测结果必然为正
- [D] 让评测集不再需要更新

**参考答案**：0

**解析**：控制变量是为了把版本差异归因到提示词上。控制变量可能并不降低算力，也不能保证结果为正，更不会让评测集免于更新。

### single_choice · None



- [A] 可以基于历史版本的差异（diff）快速定位是哪次改动引入的问题
- [B] 可以自动生成替代提示词并上线
- [C] 可以自动修复模型权重中的偏差
- [D] 可以让所有提示词版本自动合并为一个

**参考答案**：0

**解析**：版本间的差异对比能快速圈定可疑改动。版本管理并不自动生成替代提示词、不修改模型权重，也不会把版本合并。

### single_choice · None



- [A] 所有历史版本都应同时生效
- [B] 同一时刻线上通常应指向一个明确的生效版本集合，并可随时切换
- [C] 生效版本只能由模型提供商决定
- [D] 生效版本无法被主动更改

**参考答案**：1

**解析**：线上需要明确的生效版本以便控制和回滚，同时也支持按流量或用户分流到不同版本。它既不是全部同时生效，也不是由外部或不可更改的。

### single_choice · None



- [A] 记录变更人、时间、变更原因及关联版本
- [B] 只保存最新版提示词内容
- [C] 把提示词加密后不再提供读取
- [D] 仅在出现故障后才补写变更记录

**参考答案**：0

**解析**：变更留痕要求记录变更人、时间、原因并关联到版本，用于审计与追溯。只留最新版、加密不可读、事后补写都不满足留痕要求。

### single_choice · None



- [A] 这一定需要生成新的模板版本号
- [B] 模板未变而只有变量值变化时，通常仍属于同一模板版本，但仍需记录变量取值以便复现
- [C] 变量变化会导致模板版本号自动回滚
- [D] 模板版本号与变量取值完全无关，因此无需任何记录

**参考答案**：1

**解析**：模板版本跟踪的是模板结构/文本的变更；变量取值变化属于同一版本下的输入差异。不过为实现可复现，仍需记录实际输入。

### single_choice · None



- [A] 最新版文件体积会越来越大
- [B] 无法在出现质量回退时对比或回滚到已知稳定的历史版本
- [C] 文本文件无法被程序读取
- [D] 会导致模型无法加载提示词

**参考答案**：1

**解析**：丢弃历史版本使回滚与对比无从进行，一旦回退只能重写。文件体积、可读性、加载能力都不是核心风险。

### single_choice · None



- [A] 把提示词改写为可执行代码
- [B] 为提示词变更设置自动化的回归检查与发布门禁
- [C] 用规则引擎替换大语言模型
- [D] 在发布时重新训练模型

**参考答案**：1

**解析**：自动跑评测并在不通过时阻止发布，是回归检查与发布门禁的实践。它并不把提示词变成代码、不以规则引擎替换模型，也不涉及重新训练。

### single_choice · None



- [A] 二者必须绑定为同一个版本号，不能分别管理
- [B] 提示词版本与模型版本是两个相互独立但需配合记录的维度，同一提示词在不同模型上表现可能不同
- [C] 只要模型版本升级，提示词版本必须重置为初始版本
- [D] 模型版本升级后，旧提示词版本会自动失效

**参考答案**：1

**解析**：提示词与模型是两条独立的版本线，但线上效果由二者组合决定，因此需配合记录与验证。强制同一编号、重置、自动失效都不符合实际。

### single_choice · None



- [A] 立刻全量切换到 A 并放弃 B
- [B] 结合业务目标（质量/成本/延迟）与统计显著性，决定分阶段推进或调整后再评估
- [C] 因为两者都有优点所以同时上线给同一用户使用
- [D] 直接判定两个版本都不可用

**参考答案**：1

**解析**：版本取舍是多目标的权衡，需要结合业务约束与统计显著性分阶段决策。全量切换、同用户混用、直接否定都缺乏依据。

### single_choice · None



- [A] 增加文档篇幅以便展示工作量
- [B] 让使用者理解该版本的适用范围与风险，避免误用到不匹配的场景
- [C] 取代所有后续的功能测试
- [D] 使提示词运行得更快

**参考答案**：1

**解析**：标注适用范围、限制与评测结果，是为了让使用者正确选用、避免误用。它不取代测试，也不提升运行速度，更非为了堆文档。

### single_choice · None



- [A] 版本号只在发布成功后才补写，失败版本不记录
- [B] 每次修改提示词都复用同一个版本号，保持编号简洁
- [C] 为每次可上线变更分配唯一且不可变的版本标识，并记录发布时间与变更说明
- [D] 用修改者姓名作为版本号，便于追责

**参考答案**：2

**解析**：唯一且不可变的版本标识配合时间与变更说明，才能把线上行为对应到确切的提示词。复用同一编号会丢失区分度；只记录成功版本会丢失失败排查线索；姓名不能唯一标识变更内容。

### single_choice · None



- [A] 发布前运行回归评测
- [B] 发布时记录本次使用的版本标识
- [C] 发布后保留可回滚的历史版本
- [D] 发布后立即删除全部历史版本以节省存储

**参考答案**：3

**解析**：删除历史版本会破坏回滚与追溯能力，与版本管理目标相悖。回归评测、记录版本、保留历史版本都是常规必要环节。

### single_choice · None



- [A] 提示词的灰度发布与在线对比
- [B] 对模型进行全量微调
- [C] 对提示词进行静态语法检查
- [D] 对向量数据库进行重建索引

**参考答案**：0

**解析**：小流量分流并对比指标是灰度发布/在线 A-B 对比，用于在可控风险下验证新版提示词。微调、语法检查、重建索引都不是分流对比的含义。

### single_choice · None



- [A] 离线评测集无法运行任何自动化脚本
- [B] 离线评测得分与线上真实分布可能不一致，且缺少线上风险的实时观测
- [C] 旧版提示词在替换后会被系统自动删除无法恢复
- [D] 新版提示词一定会消耗更多的 token

**参考答案**：1

**解析**：离线指标无法完全代表线上分布与用户行为，需要灰度与线上观测来降低风险。评测集当然可以跑脚本；旧版是否保留取决于版本管理策略；token 消耗不一定增加。

### single_choice · None



- [A] 在日志中只记录模型名称
- [B] 在日志中记录请求时使用的提示词版本标识及其配置摘要
- [C] 在日志中记录用户的浏览器 UA
- [D] 只记录请求耗时而不记录其他字段

**参考答案**：1

**解析**：只有把请求与所用提示词版本及其配置绑定到日志，才能回溯异常对应的版本。UA、模型名、耗时都不能唯一指向提示词版本。

### single_choice · None



- [A] 提示词修改可以脱离业务代码发布流程独立更新与回滚
- [B] 模型推理速度会显著提升
- [C] 提示词不再需要任何测试
- [D] 业务代码可以不再需要版本控制

**参考答案**：0

**解析**：将提示词从代码中解耦，使其可独立发布与回滚，是版本管理的典型收益。推理速度、测试必要性、代码版本控制都不会因此被取消或提升。

### single_choice · None



- [A] 回滚意味着提示词内容会反向重写模型参数
- [B] 回滚是把线上流量切回某个已知稳定版本，并要求该版本仍可被加载
- [C] 回滚只能在模型重新训练之后进行
- [D] 回滚后旧版本的配置会被永久丢弃

**参考答案**：1

**解析**：回滚本质是切换到已知稳定的历史版本，前提是该版本及其配置仍然保留可加载。回滚不涉及改写模型参数，也不需要重新训练，旧版本更不应被丢弃。

### single_choice · None



- [A] 只有语义完全不同的提示词才需要版本号
- [B] 任何可影响模型输出的变更都应产生新的版本标识以便追溯与对比
- [C] 版本号越少越便于维护
- [D] 标点变化不会影响模型输出，因此无需记录

**参考答案**：1

**解析**：提示词对输出可能有细微甚至显著影响，凡是可影响输出的变更都应留痕，便于对比与定位。版本号多少、标点是否影响输出都不应作为省略记录的理由。

### single_choice · None



- [A] 所有人直接修改线上唯一版本
- [B] 为每个改进方向建立独立版本或分支，先在离线/小流量验证再合入主线
- [C] 禁止任何人修改提示词
- [D] 只在每次发布前备份一次提示词文件

**参考答案**：1

**解析**：独立分支或版本隔离了实验之间的干扰，验证后再合入主线兼顾效率与安全。直接改线上风险高；禁止修改不现实；仅发布前备份无法支持并行探索与回溯。

### single_choice · None



- [A] 每次有人手动跑一次 Agent，凭感觉判断好不好
- [B] 把一组固定输入和期望输出/评分标准写成自动化用例，每次代码变更自动执行
- [C] 只在项目结束时做一次大规模人工评估
- [D] 把评估脚本放在开发者本地，谁愿意跑谁跑

**参考答案**：1

**解析**：评估要成为 CI 的一部分，关键是自动化、可重复、随每次变更执行。手动、一次性、本地随意的评估都脱离了 CI 的核心价值。

### single_choice · None



- [A] 因为测试框架不支持字符串相等比较
- [B] 因为 LLM 输出具有随机性，同一输入可能产生语义相同但措辞不同的回答
- [C] 因为 Agent 运行太慢，无法逐字比较
- [D] 因为评分区间能让所有用例都通过，省去维护成本

**参考答案**：1

**解析**：LLM 输出具有非确定性，逐字相等会大量误报失败。用语义相似度、评分区间或关键字匹配更合理。让所有用例都通过则是评估失效，不是理由。

### multi_choice · None



- [A] 可以为关键指标设置阈值，低于阈值则阻止合并
- [B] 可以对不同严重级别的用例设置不同的阻断策略
- [C] 门禁阈值一旦设定就永远不应调整
- [D] 应当记录每次运行的指标以便追踪趋势

**参考答案**：[0, 1, 3]

**解析**：门禁可设阈值并分级阻断，同时应保存历史指标以观察趋势。但阈值需要随业务和基线变化做合理调整，'永不调整'是错误说法。

### multi_choice · None



- [A] 用例应覆盖典型成功路径
- [B] 用例应覆盖边界与失败/异常路径
- [C] 用例的期望结果应尽量可判定、可复现
- [D] 用例越多越好，无需考虑维护成本

**参考答案**：[0, 1, 2]

**解析**：评估用例要覆盖正例、边界与异常，并保证可判定、可复现。数量并非越多越好，需要权衡维护成本与信号价值。

### fill_blank · None



**参考答案**：["聚合", "平均", "aggregate", "mean"]

**解析**：对同一输入多次运行后取平均值或通过率等聚合指标，能削弱单次随机波动，使结果更稳定可比。

### fill_blank · None



**参考答案**：["Judge", "judge"]

**解析**：LLM-as-a-Judge 即用一个 LLM 按给定准则为另一个模型的输出打分，是自动化评估的常用手段。

### code_reading · None



**参考答案**：因为 LLM/Agent 输出具有随机性，单次运行的结果不稳定；对同一用例多次运行并按比例判断是否通过，可以降低单次随机波动对评估结论的影响，使通过率的测量更稳健、更可复现。

**解析**：该代码体现的就是用多次运行聚合来对抗非确定性。单次结果可能因偶发采样而误判，多次采样后取比例能提高评估信噪比。

### code_reading · None



**参考答案**：它作为 CI 门禁：当当前通过率低于设定的最低阈值时阻断流水线。使用固定阈值是为了容忍评估本身固有的波动，避免与 baseline 做严格逐点比较导致大量误报；但它不能发现相对基线的缓慢下降。

**解析**：固定阈值门禁能过滤小波动，但对'温水煮青蛙'式的缓慢退步不敏感，因此实际中常与趋势监控或基线对比结合使用。

### scenario · None



**解析**：答案应围绕降低评估方差：识别随机来源（采样、工具返回、网络），通过多次运行取聚合、固定数据集与 Judge 版本、控制随机性等手段提升稳定性。

### scenario · None



**解析**：合理答案应包含：为关键指标设阈值并分级阻断、核心用例快速跑、用趋势/基线监控缓慢退化、对评估波动设置容忍区间，从而兼顾敏感性与稳定性。

### single_choice · None



- [A] 直接把通过率阈值调低到 60%，让流水线变绿
- [B] 查看失败的用例明细，区分是真实回归还是评估用例本身不稳定
- [C] 关闭评估阶段，先合并代码再说
- [D] 把失败用例全部标记为 skip

**参考答案**：1

**解析**：通过率骤降应先诊断：是模型/代码回归，还是评估用例的 flaky 问题。调阈值、关闭评估、跳过用例都是掩盖问题。

### single_choice · None



- [A] 评估集应该固定且版本化，同一组用例在多次运行间保持一致以便比较
- [B] 评估集应该每次运行都随机重新生成，避免过拟合
- [C] 评估集应只包含模型一定能答对的简单样例
- [D] 评估集不需要版本控制，改了就改了

**参考答案**：0

**解析**：固定且版本化的评估集才能让不同提交的结果可比，从而发现回归。全部随机、只放简单样例、不做版本控制都会削弱评估的信号价值。

### single_choice · None



- [A] 评估应只关注性能，与正确性无关
- [B] 评估应覆盖任务质量这一核心维度，而非仅看系统指标
- [C] 评估应在生产环境而非 CI 中进行
- [D] 评估应尽量少测，减少流水线耗时

**参考答案**：1

**解析**：Agent 评估的核心是任务完成质量，仅测响应时间无法反映行为是否正确。评估应覆盖质量、鲁棒性、成本等多个维度。

### single_choice · None



- [A] 让 Judge 模型随意给分，不约束评分标准
- [B] 给出明确的评分准则/量规（rubric）并固定 Judge 的提示词与版本
- [C] 每次运行都换一个不同的 Judge 模型
- [D] 只让 Judge 输出 True/False，不给任何理由

**参考答案**：1

**解析**：明确的评分量规、固定的提示词与模型版本能显著降低 Judge 的方差，让 CI 结果稳定可比。随意给分、频繁换模型、不给理由都会引入噪声。

### single_choice · None



- [A] 每次提交都跑全量评估集，不做任何分层
- [B] 分层评估：每次提交跑快速的核心子集，合并到主分支或夜间再跑全量
- [C] 为了省钱完全不跑评估
- [D] 只在发布当天人工抽检几条

**参考答案**：1

**解析**：分层/抽样策略能在反馈速度与覆盖度之间取得平衡：快速子集保证每次提交的即时反馈，全量跑定期覆盖更多用例。完全不做评估或只靠人工抽检都会漏掉回归。

### single_choice · None



- [A] 什么问题都不会遗漏，最终答案对了就够了
- [B] 中间步骤是否合理、工具调用是否恰当、是否产生多余副作用等过程性信息
- [C] 只会遗漏响应时间
- [D] 只会遗漏成本数据

**参考答案**：1

**解析**：只看最终结果会掩盖错误的过程：可能用错误方式凑对了答案，或产生了不应有的操作。过程性评估能定位问题并防止侥幸通过。

### multi_choice · None



- [A] 任务完成的正确性
- [B] 对提示注入等对抗输入的鲁棒性
- [C] 每次运行的 token 消耗与费用
- [D] 评估用例本身的稳定性/是否 flaky

**参考答案**：[0, 1, 2, 3]

**解析**：一个健全的 Agent 评估体系应覆盖质量（正确性）、安全性/鲁棒性、成本以及评估自身的可靠性。四者都应在 CI 中得到体现。

### multi_choice · None



- [A] 固定随机种子或降低采样温度（在允许的范围内）
- [B] 固定评估数据集与 Judge 的提示词版本
- [C] 对多次运行取聚合指标而非单次结果
- [D] 每次运行都更换评估数据集以防止过拟合

**参考答案**：[0, 1, 2]

**解析**：控制随机性、固定数据集与提示词、用多次运行的聚合指标，都能降低方差、提升可比性。频繁更换数据集会破坏可比较性。
