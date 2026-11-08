# s8u5l3 数据平台架构入门：从零到工程级 / 成本控制（Cost Control）：架构系统的第一道经济防线

> 来源 `content/lessons/s8u5l3.json`

## arch.sys.data_platform

# 数据平台架构入门：从零到工程级

> **一句话直觉**：数据平台（Data Platform）就是让「数据从产生到变成决策」这条流水线可靠、可复用、可治理的一套系统化工程。

---

## 0. 为什么需要数据平台？

一家公司如果只有几个人，用 Excel 和脚本就能分析数据。但当数据源变成几十个、每天产生上亿条记录、十几个团队都要用数据时，「各写各的脚本」就会崩溃：口径不一致、任务互相踩踏、出了错没人知道。

**数据平台（Data Platform）** 就是把数据采集、存储、加工、服务、治理这几件事用统一的架构和工具承载起来，让数据像自来水一样稳定供应。

---

## 1. 数据平台的五层结构

一个典型的数据平台可以拆成五层，从下往上：

1. **数据源层（Data Source）**：业务数据库、日志、埋点、第三方 API。
2. **采集/接入层（Ingestion）**：把数据搬进来，常见工具有 Flume、Kafka、Flink CDC、Airbyte。
3. **存储层（Storage）**：原始数据放数据湖（Data Lake），结构化数据放数据仓库（Data Warehouse）。
4. **计算/加工层（Processing）**：批处理（Batch）用 Spark/Hive，流处理（Stream）用 Flink/Kafka Streams。
5. **服务与治理层（Serving & Governance）**：BI 报表、指标 API、元数据管理、数据质量、权限。

每一层都通过**接口**解耦：上游只管产出，下游只管消费。这样任何一层替换实现，都不会把整条链路推翻。

```python
# 用一个最简单的方式理解“分层”——每层只暴露一个函数
class DataSource:
    def read(self):
        return [{"id": 1, "amount": 100}, {"id": 2, "amount": 200}]

class Ingestion:
    def __init__(self, source):
        self.source = source
    def fetch(self):
        # 模拟采集：加个采集时间戳
        return [{**row, "ingested_at": "2024-01-01"} for row in self.source.read()]

class Storage:
    def __init__(self):
        self.data = []
    def write(self, rows):
        self.data.extend(rows)
    def read_all(self):
        return self.data

# 串起来
store = Storage()
Ingestion(DataSource()).fetch() and store.write(Ingestion(DataSource()).fetch())
print(store.read_all())
```

---

## 2. 数据建模：把「原始数据」变成「可理解的数据」

数据平台最核心的认知是：**原始数据几乎没法直接用**。所以工程上流行一种分层建模方法，最常见的是 **Medallion 架构（奖牌架构）**：

- **Bronze（青铜层）**：原样落地的原始数据，只加时间戳、来源信息，不清洗。
- **Silver（白银层）**：清洗、去重、标准化后的明细数据。
- **Gold（黄金层）**：面向业务的聚合表，比如「每日 GMV」「用户留存」。

这套分层的价值是：出错时可以逐层回放，业务指标可以追溯到原始记录。

```python
# 用三个函数模拟 Medallion 三层
raw = [
    {"user": "alice", "amount": "100", "ts": "2024-01-01"},
    {"user": "bob",   "amount": "200", "ts": "2024-01-01"},
    {"user": "alice", "amount": "-50", "ts": "2024-01-02"},  # 脏数据
]

# Bronze: 原样保留
def bronze(rows):
    return [dict(r) for r in rows]

# Silver: 类型转换 + 过滤非法值
def silver(rows):
    cleaned = []
    for r in rows:
        try:
            amt = float(r["amount"])
        except ValueError:
            continue
        if amt <= 0:            # 金额必须为正
            continue
        cleaned.append({"user": r["user"], "amount": amt, "ts": r["ts"]})
    return cleaned

# Gold: 按用户聚合
def gold(rows):
    total = {}
    for r in rows:
        total[r["user"]] = total.get(r["user"], 0) + r["amount"]
    return total

print(gold(silver(bronze(raw))))   # {'alice': 100.0, 'bob': 200.0}
```

---

## 3. 数据管道：调度与依赖

数据不会自己流动，需要**调度器（Scheduler）** 按依赖关系触发任务。工业界常用的有 Airflow、Dagster、Prefect。它们共同的关键概念是 **DAG（有向无环图，Directed Acyclic Graph）**：

- 节点（Node）= 一个任务（Task），比如「跑 Silver 层」。
- 边（Edge）= 依赖关系，比如 Silver 必须在 Bronze 之后。

为什么强调「无环」？因为环会让任务互相等待，永远跑不完。

```python
# 一个极简 DAG 调度器：按依赖顺序执行任务
tasks = {
    "bronze": {"deps": [],          "fn": lambda: "raw_data"},
    "silver": {"deps": ["bronze"],  "fn": lambda: "clean_data"},
    "gold":   {"deps": ["silver"],  "fn": lambda: "agg_data"},
}

done = {}
def run(name):
    if name in done:
        return done[name]
    for dep in tasks[name]["deps"]:
        run(dep)                # 先跑依赖
    done[name] = tasks[name]["fn"]()
    print(f"{name} -> {done[name]}")

run("gold")
# 输出顺序保证：bronze -> silver -> gold
```

---

## 4. 数据治理：让平台「可持续」

平台规模一大，治理（Governance）就成为生命线，核心有四件事：

1. **元数据（Metadata）**：表是谁建的、字段什么意思、谁在用。
2. **数据质量（Data Quality）**：非空、唯一、值域、及时性等规则。
3. **血缘（Lineage）**：一张表错误了，能立刻查到它影响了哪些下游。
4. **权限与合规（Access Control & Compliance）**：谁能看哪些列（比如手机号要脱敏）。

这四件事用代码抽象，都可以看作「对数据的附加描述」。比如数据质量就是一组断言：

```python
# 用断言表达数据质量规则
rows = [{"id": 1, "amount": 100}, {"id": 2, "amount": 200}]

rules = [
    ("id 唯一",   lambda r: len({x["id"] for x in r}) == len(r)),
    ("amount>0", lambda r: all(x["amount"] > 0 for x in r)),
]

for name, check in rules:
    assert check(rows), f"质量校验失败: {name}"
print("全部质量规则通过")
```

---

## 5. 工程化视角：把上面四件事拼成一个平台

真正落地时，架构师需要回答四个问题：

- **存哪里**：数据湖（廉价对象存储）+ 数据仓库（高性能查询）双轨并行。
- **怎么算**：批流一体，避免同逻辑维护两套代码。
- **怎么管**：元数据、血缘、质量、权限统一接入一个 catalog（如 DataHub、OpenMetadata）。
- **怎么服务**：对外只暴露稳定的指标 API 或数据集，不让业务直接读原始表。

一个常见落地顺序：先做**采集 + 仓库分层**，再加**调度依赖**，最后补**治理**。不要一开始就追求全家桶。

---

## 动手练习

**任务**：用纯 Python 实现一个「迷你数据平台」，跑通一条从原始数据到业务指标的完整链路。

**要求**：
1. 构造一个列表 `raw`，包含 5 条订单记录（字段：`order_id`、`user`、`amount`、`ts`），其中至少有 1 条 `amount` 为负（脏数据）。
2. 实现三个函数：`bronze(raw)` 原样返回；`silver(rows)` 过滤掉 `amount<=0` 并转成 `float`；`gold(rows)` 按 `user` 汇总总金额。
3. 写一个 `pipeline()` 函数，按 `bronze -> silver -> gold` 顺序执行并返回最终结果。
4. 添加一条数据质量断言：最终每个用户的总额必须大于 0，否则抛 `AssertionError`。
5. 打印最终指标，并把每一步的数据行数打印出来，方便观察分层过滤效果。

**验收标准**：运行后能正确输出每个用户的总金额，且当把 `silver` 中的过滤条件去掉时，质量断言会失败——证明治理层确实在起作用。

---

> **一句话收尾**：数据平台不是某个工具，而是「采集、存储、加工、服务、治理」五件事通过接口分层协作的工程体系；掌握这套结构，你就能在任何公司把杂乱的数据流变成可信赖的数据资产。

```python
# mini_data_platform.py —— 可直接运行

raw = [
    {"order_id": 1, "user": "alice", "amount": "100", "ts": "2024-01-01"},
    {"order_id": 2, "user": "bob",   "amount": "200", "ts": "2024-01-01"},
    {"order_id": 3, "user": "alice", "amount": "-50", "ts": "2024-01-02"},
    {"order_id": 4, "user": "carol", "amount": "300", "ts": "2024-01-02"},
    {"order_id": 5, "user": "bob",   "amount": "150", "ts": "2024-01-03"},
]

def bronze(rows):
    """Bronze: 原样落地，仅做浅拷贝避免污染源数据。"""
    return [dict(r) for r in rows]

def silver(rows):
    """Silver: 类型转换 + 过滤非法金额。"""
    cleaned = []
    for r in rows:
        try:
            amt = float(r["amount"])
        except (TypeError, ValueError):
            continue
        if amt <= 0:
            continue
        cleaned.append({**r, "amount": amt})
    return cleaned

def gold(rows):
    """Gold: 按用户聚合总消费金额。"""
    total = {}
    for r in rows:
        total[r["user"]] = total.get(r["user"], 0.0) + r["amount"]
    return total

def pipeline():
    b = bronze(raw)
    s = silver(b)
    g = gold(s)

    # 数据质量断言：每个用户的总金额必须 > 0
    assert all(v > 0 for v in g.values()), "质量校验失败：存在非正的总金额"

    print(f"bronze rows = {len(b)}")
    print(f"silver rows = {len(s)}")
    print(f"gold        = {g}")
    return g

if __name__ == "__main__":
    pipeline()
```

## arch.sys.cost_control

# 成本控制（Cost Control）：架构系统的第一道经济防线

> 一句话直觉：**当系统能自动按预算“刹车”，你才不会因为一次流量暴涨或代码死循环而收到一张天价账单。**

---

## 0. 为什么需要“成本控制”作为架构起点

在云原生和 AI 服务时代，计算资源是按量付费的。一个没有成本控制（Cost Control）的系统，就像一辆没有刹车的跑车：跑得越快，出事越惨。

成本控制不是“省钱”那么简单，它是**系统稳定性与业务可持续性的基础**。它回答三个问题：

1. 我最多愿意花多少钱？（预算 Budget）
2. 当前花了多少？（度量 Metrics）
3. 超了怎么办？（策略 Policy）

本课从零开始，带你建立一套可运行的成本控制思维和代码骨架。

---

## 1. 预算（Budget）：先画一条不可逾越的红线

预算就是你在一个周期内（比如一天、一个月）允许消耗的最大资源量或金额。

在代码中，我们通常把它表示为一个简单的数据结构：

```python
from dataclasses import dataclass
from datetime import date

@dataclass
class Budget:
    limit: float          # 总预算，单位：元
    period: str           # 周期：'daily' 或 'monthly'
    used: float = 0.0     # 已使用金额

    def remaining(self) -> float:
        """返回剩余可用预算。"""
        return max(0.0, self.limit - self.used)

# 示例：每天最多花 100 元
budget = Budget(limit=100.0, period='daily')
print(budget.remaining())  # 100.0
```

**关键结论**：预算必须是显式的、可查询的、不可为负的。

---

## 2. 度量（Metrics）：没有数据就没有控制

你无法控制你无法测量的东西。成本控制的核心是**实时记录每一次资源消耗**。

最简单的做法：每次调用外部 API 或消耗计算资源时，记录一笔“成本事件”。

```python
from dataclasses import dataclass, field
from typing import List

@dataclass
class CostEvent:
    name: str        # 资源名称，如 'gpt-4-call'
    amount: float    # 本次花费
    timestamp: float # Unix 时间戳

class CostTracker:
    def __init__(self):
        self.events: List[CostEvent] = []

    def record(self, name: str, amount: float, ts: float) -> None:
        """记录一笔成本事件。"""
        self.events.append(CostEvent(name, amount, ts))

    def total(self) -> float:
        """返回所有事件的总花费。"""
        return sum(e.amount for e in self.events)

# 示例
tracker = CostTracker()
tracker.record('gpt-4-call', 0.5, 1700000000.0)
tracker.record('gpt-4-call', 0.3, 1700000060.0)
print(tracker.total())  # 0.8
```

**关键结论**：成本事件是原子记录，必须包含名称、金额和时间。

---

## 3. 策略（Policy）：超预算时自动“刹车”

有了预算和度量，下一步是定义**当花费接近或超过预算时系统的行为**。

常见策略：

- **拒绝（Deny）**：直接禁止新的消耗。
- **降级（Degrade）**：切换到更便宜的模型或资源。
- **告警（Alert）**：通知负责人，但不阻止。

下面是一个可运行的策略执行器：

```python
class CostController:
    def __init__(self, budget: Budget, tracker: CostTracker):
        self.budget = budget
        self.tracker = tracker

    def can_spend(self, amount: float) -> bool:
        """判断当前是否允许再花费 amount。"""
        return self.tracker.total() + amount <= self.budget.limit

    def spend(self, name: str, amount: float, ts: float) -> bool:
        """尝试花费；如果超预算则拒绝并返回 False。"""
        if not self.can_spend(amount):
            print(f'[拒绝] {name} 花费 {amount} 超预算')
            return False
        self.tracker.record(name, amount, ts)
        return True

# 示例
budget = Budget(limit=1.0, period='daily')
tracker = CostTracker()
controller = CostController(budget, tracker)

controller.spend('gpt-4-call', 0.6, 1700000000.0)  # True
controller.spend('gpt-4-call', 0.5, 1700000060.0)  # False，超预算
```

**关键结论**：策略必须是可编程的，并且默认安全（fail-safe）。

---

## 4. 工程级形态：把成本控制接入真实调用链

在真实系统中，成本控制应该作为一个**横切关注点（cross-cutting concern）**，以装饰器或中间件形式包裹昂贵的操作。

```python
import functools
import time
from typing import Callable

def cost_controlled(controller: CostController, unit_cost: float):
    """装饰器：每次调用前检查预算，调用后记录成本。"""
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not controller.can_spend(unit_cost):
                raise RuntimeError('预算不足，调用被拒绝')
            result = func(*args, **kwargs)
            controller.spend(func.__name__, unit_cost, time.time())
            return result
        return wrapper
    return decorator

# 示例
controller = CostController(Budget(limit=2.0, period='daily'), CostTracker())

@cost_controlled(controller, unit_cost=0.8)
def call_llm(prompt: str) -> str:
    return f'回答：{prompt}'

print(call_llm('你好'))  # 正常
print(call_llm('再见'))  # 正常
# 第三次将超预算
# print(call_llm('第三次'))  # RuntimeError
```

**关键结论**：成本控制应透明地嵌入调用链，而不是散落在业务代码中。

---

## 5. 可观测性与闭环：让成本控制自己说话

最后，成本控制系统本身也需要被监控。你需要暴露指标：

- 当前周期已花费金额
- 剩余预算
- 拒绝次数

```python
class ObservableController(CostController):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.denied_count = 0

    def spend(self, name: str, amount: float, ts: float) -> bool:
        ok = super().spend(name, amount, ts)
        if not ok:
            self.denied_count += 1
        return ok

    def report(self) -> dict:
        return {
            'used': self.tracker.total(),
            'limit': self.budget.limit,
            'remaining': self.budget.remaining(),
            'denied': self.denied_count,
        }

# 示例
oc = ObservableController(Budget(limit=1.0, period='daily'), CostTracker())
oc.spend('a', 0.6, time.time())
oc.spend('b', 0.6, time.time())
print(oc.report())
# {'used': 0.6, 'limit': 1.0, 'remaining': 0.4, 'denied': 1}
```

**关键结论**：可观测性让成本控制从“被动封禁”变为“主动运营”。

---

## 动手练习

**任务**：实现一个带“每日重置”功能的成本控制器。

要求：

1. 使用 `datetime.date` 记录当前日期。
2. 每次 `spend` 前检查是否跨天；如果跨天，自动将已用金额清零。
3. 写一个简单测试：模拟两天各花费 80 元，每日预算 100 元，第二天应仍可花费。

提示：可以在 `Budget` 中增加 `last_reset_date` 字段，并在 `CostController` 中增加 `_maybe_reset()` 方法。

完成后，你应该能理解：**成本控制不是一次性的检查，而是一个持续运行的状态机。**

```python
import functools
import time
from dataclasses import dataclass, field
from typing import List, Callable

@dataclass
class Budget:
    limit: float
    period: str
    used: float = 0.0

    def remaining(self) -> float:
        return max(0.0, self.limit - self.used)

@dataclass
class CostEvent:
    name: str
    amount: float
    timestamp: float

class CostTracker:
    def __init__(self):
        self.events: List[CostEvent] = []

    def record(self, name: str, amount: float, ts: float) -> None:
        self.events.append(CostEvent(name, amount, ts))

    def total(self) -> float:
        return sum(e.amount for e in self.events)

class CostController:
    def __init__(self, budget: Budget, tracker: CostTracker):
        self.budget = budget
        self.tracker = tracker
        self.denied_count = 0

    def can_spend(self, amount: float) -> bool:
        return self.tracker.total() + amount <= self.budget.limit

    def spend(self, name: str, amount: float, ts: float) -> bool:
        if not self.can_spend(amount):
            self.denied_count += 1
            print(f'[拒绝] {name} 花费 {amount} 超预算')
            return False
        self.tracker.record(name, amount, ts)
        return True

    def report(self) -> dict:
        return {
            'used': self.tracker.total(),
            'limit': self.budget.limit,
            'remaining': self.budget.remaining(),
            'denied': self.denied_count,
        }

def cost_controlled(controller: CostController, unit_cost: float):
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not controller.can_spend(unit_cost):
                raise RuntimeError('预算不足，调用被拒绝')
            result = func(*args, **kwargs)
            controller.spend(func.__name__, unit_cost, time.time())
            return result
        return wrapper
    return decorator

if __name__ == '__main__':
    budget = Budget(limit=2.0, period='daily')
    tracker = CostTracker()
    controller = CostController(budget, tracker)

    @cost_controlled(controller, unit_cost=0.8)
    def call_llm(prompt: str) -> str:
        return f'回答：{prompt}'

    print(call_llm('你好'))
    print(call_llm('再见'))
    try:
        print(call_llm('第三次'))
    except RuntimeError as e:
        print(f'捕获异常：{e}')

    print(controller.report())
```


---

## 本课题目

### single_choice · None



- [A] 把分析型数据库换成更强的硬件即可
- [B] 引入分层存储与职责分离：原始数据先落到可高吞吐写入的存储，再按需加工进入服务层
- [C] 让 BI 查询改为直连业务库
- [D] 把日志改成按天全量覆盖写入

**参考答案**：1

**解析**：数据平台的典型分层思路是采集/存储、加工、服务各司其职；把高吞吐写入与分析查询压在同一个系统上必然冲突。

### single_choice · None



- [A] 给业务库加只读从库并让下游继续直连
- [B] 搭建统一的数据接入层/ODS 层，下游统一从该层获取数据
- [C] 限制下游任务只能在夜间运行
- [D] 要求每个下游自行缓存数据

**参考答案**：1

**解析**：统一接入层可以解耦源系统与下游消费，避免点对点抽取带来的重复压力和口径不一致；只读从库仍是点对点。

### single_choice · None



- [A] 完全禁止自助取数
- [B] 提供面向主题的汇总层/数据集市，自助查询走该层
- [C] 让业务方自己写优化后的 SQL
- [D] 把所有明细表都加上缓存

**参考答案**：1

**解析**：面向主题的汇总层能在满足自助需求的同时控制查询代价，是数据平台常见的服务层设计。

### single_choice · None



- [A] 固定延迟 30 分钟后开始读取
- [B] 通过调度系统声明依赖，等待上游产出信号后再执行
- [C] 让两个任务同时启动
- [D] 让下游任务循环重试直到成功

**参考答案**：1

**解析**：基于依赖与就绪信号的调度比固定延迟或盲目重试更可靠，是平台调度的核心机制。

### single_choice · None



- [A] 自动提升查询性能
- [B] 可以查询数据血缘、影响范围与资产目录
- [C] 自动修复数据错误
- [D] 自动生成所有报表

**参考答案**：1

**解析**：元数据管理的核心价值在于血缘、影响分析与资产发现，性能优化和错误修复属于其他机制。

### single_choice · None



- [A] 把质量规则写进文档即可
- [B] 在加工链路中内嵌质量校验与阻断/告警机制
- [C] 让下游自行容错
- [D] 只在月末做一次质量检查

**参考答案**：1

**解析**：质量校验应内嵌到链路中并具备阻断或告警能力，才能前置发现问题；文档和事后检查不足以防止返工。

### single_choice · None



- [A] 允许各团队继续维护，只要报表能出数
- [B] 建立统一的公共维度层并由平台统一维护发布
- [C] 把维度表内嵌到每个事实表中
- [D] 禁止使用维度表

**参考答案**：1

**解析**：公共维度层是保证一致性维度与编码统一的关键设计；各团队分治会持续产生口径分叉。

### single_choice · None



- [A] 所有负载都跑在同一套集群同一队列上
- [B] 按负载特征划分资源池/队列，做资源隔离与优先级管理
- [C] 只保留离线计算，取消交互式查询
- [D] 只保留交互式查询，取消离线计算

**参考答案**：1

**解析**：不同负载的资源特征不同，平台需要通过资源池与优先级做隔离，避免相互干扰。

### single_choice · None



- [A] 直接修改并通知下游
- [B] 通过血缘与影响分析评估影响范围，再按兼容方式发布变更
- [C] 停止所有下游任务
- [D] 复制一张新表但不通知任何人

**参考答案**：1

**解析**：在变更前进行影响分析并以兼容方式发布，是平台化变更管理的核心；直接修改或静默新建都会带来隐患。

### single_choice · None



- [A] 继续全量重算，只是把任务提前启动
- [B] 改为按分区增量加工，只处理变化部分
- [C] 把全量结果缓存起来避免重复计算
- [D] 减少历史数据保留量以缩短时间

**参考答案**：1

**解析**：按分区增量加工是应对数据增长的常见架构手段；缓存和提前启动不能从根本上解决计算量问题。

### single_choice · None



- [A] 让业务方直接连生产库查询
- [B] 评估时效需求，若确需实时则通过实时链路产出，否则用准实时/批量链路
- [C] 统一告诉业务方只能 T+1
- [D] 让业务方自己写脚本抓取

**参考答案**：1

**解析**：平台应基于需求评估选择合适时效的链路，而非一刀切拒绝或让业务直连生产系统。

### single_choice · None



- [A] 可以不再需要数据治理
- [B] 新业务接入时可复用已有能力，降低重复建设与维护成本
- [C] 可以完全避免数据质量问题
- [D] 可以不再需要调度系统

**参考答案**：1

**解析**：平台化的核心收益是能力复用与规模化效率；它不能免除治理和调度，反而更依赖这些基础能力。

### single_choice · None



- [A] 要求报表使用者自行核对
- [B] 建立统一的指标定义与公共数据模型，各报表基于同一口径产出
- [C] 把两个报表合并成一个报表
- [D] 让两张报表都改用手工填报

**参考答案**：1

**解析**：口径不一致通常源于缺乏统一的指标与模型定义，架构上应沉淀公共语义层/指标层，而非在展示端修补。

### single_choice · None



- [A] 让业务方接受 10 点后再看
- [B] 引入流式/增量加工链路，缩短数据从产生到可用的时延
- [C] 把加工任务改成手工触发
- [D] 只在有需要时才启动加工

**参考答案**：1

**解析**：时效性问题本质是链路架构问题，采用增量或流式处理可以显著降低端到端延迟；其余选项只是回避或转移问题。

### single_choice · None



- [A] 增加写入重试次数
- [B] 明确该表的单一数据来源与加工链路，按分层原则组织依赖关系
- [C] 给该表加更多索引
- [D] 允许多个任务并行写入以提高效率

**参考答案**：1

**解析**：多写同一张表会带来竞争与不可追溯，平台化要求明确数据血缘与单一加工路径，按分层组织依赖。

### single_choice · None



- [A] 直接删除所有历史数据
- [B] 根据访问频率与保留策略做冷热分层，把低频数据迁到低成本存储
- [C] 继续扩容以应对增长
- [D] 禁止下游查询历史数据

**参考答案**：1

**解析**：冷热分层与生命周期管理是数据平台成本治理的标准手段；直接删除或禁止查询会破坏数据可用性。

### single_choice · None



- [A] 让下游直接依赖源表结构，变更时随时调整
- [B] 在接入层做 schema 管理与契约校验，变更按约定流程发布
- [C] 禁止上游做任何结构变更
- [D] 每次变更后重跑全量任务

**参考答案**：1

**解析**：平台化强调契约与 schema 管理，使变更可控、可追溯；直接依赖源表结构会让下游脆弱。

### single_choice · None



- [A] 硬件成本一定更高
- [B] 同一份数据两套口径，容易产生不一致与重复建设
- [C] 实时链路一定比批处理慢
- [D] 批处理无法处理历史数据

**参考答案**：1

**解析**：两套独立链路容易造成数据口径分叉与资源重复；平台化通常追求批流统一或共享底层存储与语义。

### single_choice · None



- [A] 让所有任务合并成一个超大任务
- [B] 建立任务依赖调度与数据质量校验，失败可定位、可重跑
- [C] 取消所有任务依赖，各自独立执行
- [D] 只在失败时人工通知

**参考答案**：1

**解析**：调度依赖与质量校验是平台可靠性的基础，能实现失败隔离与可恢复；合并任务或取消依赖都会加剧问题。

### single_choice · None



- [A] 把 SQL 复制到更多报表中以保持一致
- [B] 将公共加工逻辑下沉到数据模型/中间层，报表只做展示
- [C] 禁止使用 SQL
- [D] 让每个报表各自维护自己的逻辑

**参考答案**：1

**解析**：公共逻辑下沉到模型层可复用、可治理，报表层只负责展示；复制逻辑会放大维护成本与不一致风险。

### single_choice · None



- [A] 在满足性能与可靠性要求的前提下，尽量降低资源与运维开销
- [B] 把所有组件都改成最便宜的硬件
- [C] 完全消除系统的所有开销
- [D] 只关注一次性的采购成本

**参考答案**：0

**解析**：成本控制不是一味压低价格，而是在满足业务指标（性能、可靠性、可用性等）的约束下优化总体拥有成本，包括资源、运维、人力等。

### single_choice · None



- [A] 仅指服务器采购费用
- [B] 仅指云服务的月度账单
- [C] 包含采购、运维、能耗、人力、迁移与退出等全生命周期成本
- [D] 仅指软件许可费用

**参考答案**：2

**解析**：TCO 覆盖系统全生命周期内的直接与间接成本，采购价只是其中一部分，运维、人力、迁移、退出等同样重要。

### single_choice · None



- [A] 超卖总能省钱且没有风险
- [B] 适度超卖可提高利用率降本，但需评估隔离与争抢风险
- [C] 超卖与成本无关
- [D] 超卖一定会导致系统崩溃

**参考答案**：1

**解析**：在保证隔离与可接受性能的前提下，适度超卖能提升资源利用率降低成本，但过度超卖会带来性能争抢与稳定性风险。

### multi_choice · None



- [A] 根据负载弹性伸缩资源
- [B] 对冷数据进行分层存储或归档
- [C] 持续监控并清理闲置资源
- [D] 对所有服务都按峰值常驻高配资源
- [E] 为稳定基线负载购买预留/折扣资源

**参考答案**：[0, 1, 2, 4]

**解析**：弹性伸缩、分层存储、清理闲置、预留折扣都是常见降本手段；按峰值常驻高配会加剧浪费。

### multi_choice · None



- [A] 业务负载特征（峰值/波动/增长趋势）
- [B] 性能与可靠性要求
- [C] 资源定价模型（按量、预留、竞价等）
- [D] 运维人力与自动化程度
- [E] 架构组件的许可证或托管费用

**参考答案**：[0, 1, 2, 3, 4]

**解析**：成本控制是架构级权衡，需综合负载特征、质量要求、定价模型、运维成本与组件费用等多方面因素。

### multi_choice · None



- [A] 资源利用率长期很低
- [B] 账单持续上涨但业务量未同步增长
- [C] 存在大量无人认领的闲置实例或存储
- [D] 所有服务的容量都精确匹配当前负载并有监控告警

**参考答案**：[0, 1, 2]

**解析**：低利用率、账单与业务脱节、闲置资源都是成本失控信号；精确匹配并有监控属于良好实践。

### multi_choice · None



- [A] 提高可靠性通常需要更多冗余资源，可能增加成本
- [B] 通过降本可以无限降低可靠性而不影响业务
- [C] 需要根据业务等级设定合理的可靠性目标以平衡成本
- [D] 可靠性目标和成本目标之间不存在任何权衡

**参考答案**：[0, 2]

**解析**：冗余与容错通常增加成本，因此要按业务等级设定 SLO，在可靠性与成本间做合理权衡；二者确实存在权衡关系。

### fill_blank · None



**参考答案**：["TCO", "tco", "总体拥有成本", "总拥有成本"]

**解析**：TCO（Total Cost of Ownership，总体拥有成本）强调不只看采购价，而是覆盖全生命周期的综合成本。

### fill_blank · None



**参考答案**：["弹性伸缩", "自动伸缩", "autoscaling", "auto scaling", "弹性扩缩容"]

**解析**：弹性伸缩（autoscaling）让资源随负载动态调整，低谷时释放资源，是控制按量付费成本的关键机制。

### code_reading · None



**参考答案**：识别并清理长期低利用率的闲置实例，减少不必要的资源开销，从而实现成本控制。

**解析**：脚本定期检测长时间低负载的实例，人工确认后释放，是典型的闲置资源治理，直接降低持续计费带来的浪费。

### code_reading · None



**参考答案**：方案B让稳定的基线负载享受预留折扣，波动部分才用按量资源，避免为仅出现在峰值时段的容量长期付费，从而在满足峰值需求的同时降低总成本。

**解析**：峰值常驻会让大部分时间资源闲置；基线预留+峰值弹性能兼顾折扣与弹性，是常见的成本优化组合策略。

### scenario · None



**参考答案**：["分层存储", "冷热分离", "归档", "访问频率", "低成本", "性能"]

**解析**：应按访问频率对数据分层，热数据保留在高性能存储，冷/历史数据转入低成本介质或归档；这样既保证近期查询性能，又显著降低长期存储成本。

### single_choice · None



- [A] 云厂商偷偷涨价
- [B] 仍保留了按峰值配置的常驻资源，未做弹性伸缩
- [C] 夜间网络更贵
- [D] 迁移后代码变慢了

**参考答案**：1

**解析**：按量付费只有在资源能随负载伸缩时才能体现成本优势；若仍按峰值常驻，低谷期资源闲置，费用不会下降。

### scenario · None



**参考答案**：["成本监控", "账单分析", "闲置资源", "异常开销", "标签", "优化"]

**解析**：应借助成本监控与账单分析，按服务/标签拆分费用，定位异常开销来源（如闲置资源、配置变更、未缩容、数据增长等），再针对根因优化并验证效果，形成闭环。

### single_choice · None



- [A] 缓存只会增加成本，没有收益
- [B] 缓存能降低后端负载，从而可能减少所需计算与数据库资源
- [C] 缓存一定能降低所有成本
- [D] 缓存与成本控制无关

**参考答案**：1

**解析**：合理的缓存可以显著降低对后端计算和数据库的压力，进而减少资源规模与费用，但缓存本身也有内存/一致性成本，需权衡。

### single_choice · None



- [A] 系统一定不可用
- [B] 平均资源利用率偏低，造成闲置浪费，抬高成本
- [C] 无法应对突发流量
- [D] 数据一定会丢失

**参考答案**：1

**解析**：按峰值配置虽然能扛住最高负载，但大部分时间资源闲置，利用率低，成本高。更好的做法是结合弹性伸缩与容量预留策略。

### single_choice · None



- [A] 所有数据都放在最高性能的存储介质上
- [B] 对所有数据永不删除、永不归档
- [C] 按访问频率分层存储，冷数据转入低成本介质或归档
- [D] 把数据复制到尽可能多的副本中

**参考答案**：2

**解析**：数据分层（热/温/冷/归档）能根据访问频率匹配存储成本，是控制长期存储成本的关键手段。

### single_choice · None



- [A] 预留一定比按量便宜，任何场景都该买
- [B] 按量一定比预留便宜
- [C] 负载稳定可预测时预留通常更省；负载波动大时按量/弹性更合适
- [D] 两者成本完全一样

**参考答案**：2

**解析**：预留通过承诺换取折扣，适合稳定基线负载；波动部分用按量或弹性资源承接，组合策略通常最优。

### single_choice · None



- [A] 采购成本一次性升高
- [B] 持续为不再需要的资源付费，形成资源浪费
- [C] 数据丢失
- [D] 网络延迟升高

**参考答案**：1

**解析**：扩容后未及时缩容会导致资源长期闲置但持续计费，是常见的成本泄漏来源，需要自动化生命周期管理。

### single_choice · None



- [A] 让系统看起来更专业
- [B] 帮助发现资源浪费点、异常开销与成本趋势，为优化决策提供依据
- [C] 自动降低所有费用
- [D] 替代容量规划

**参考答案**：1

**解析**：没有度量就没有优化。成本可观测性能定位浪费、识别异常、评估优化效果，是成本控制闭环的基础。

### single_choice · None



- [A] 性能
- [B] 可靠性/可用性
- [C] 开发与运维复杂度
- [D] 代码注释的字体大小

**参考答案**：3

**解析**：成本控制需要在性能、可靠性、复杂度等约束下权衡；代码注释字体大小与系统成本无关，是明显的干扰项。
