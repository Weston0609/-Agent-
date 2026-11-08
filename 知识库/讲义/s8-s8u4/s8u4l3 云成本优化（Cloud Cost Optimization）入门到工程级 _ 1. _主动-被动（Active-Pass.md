# s8u4l3 云成本优化（Cloud Cost Optimization）入门到工程级 / 1. **主动-被动（Active-Passive）**

> 来源 `content/lessons/s8u4l3.json`

## arch.cloud.cost_optim

# 云成本优化（Cloud Cost Optimization）入门到工程级

## 一句话直觉

**你花钱买的不是服务器，而是「算力时间」——云成本优化的本质就是：用最少的钱，买到刚好够用的算力，并把闲置和浪费降到最低。**

学完这一节，你能回答三个问题：钱花在哪了？为什么浪费了？怎么省下来？

---

## 1. 成本从哪里来：云账单的四块拼图

云支出通常由四类资源构成（不同云厂商命名略有差异）：

- **计算（Compute）**：CPU/GPU 实例、容器、Serverless 函数。
- **存储（Storage）**：对象存储、块存储、快照。
- **网络（Network）**：出流量（Egress）、跨区传输、NAT 网关。
- **托管服务（Managed Services）**：数据库、消息队列、日志系统。

成本优化的第一步永远不是「省钱」，而是**算清楚单位成本**，即每个业务动作的真实开销。

### 核心公式：单位经济学（Unit Economics）

```python
# 计算「每次推理」或「每个用户」的成本，而不是只看总账单
total_monthly_cost = 3000.0   # 云账单（美元/月）
requests_per_month = 5_000_000  # 月请求数
cost_per_request = total_monthly_cost / requests_per_month
print(f"单次请求成本: ${cost_per_request:.6f}")  # 0.000600
```

**结论**：只有把成本摊到「一次请求 / 一个用户 / 一次训练」上，你才有可比较、可优化的指标。

---

## 2. 浪费的三大来源：别急着砍规格，先找漏点

按业界经验，云账单里 30%~50% 是可回收浪费，主要来自三类：

1. **闲置（Idle）**：实例开着但 CPU 利用率 < 5%，如忘记关掉的开发机、GPU 训练完未释放。
2. **过度配置（Over-provisioning）**：按峰值买容量，导致 90% 时间在浪费。
3. **架构低效（Architectural Inefficiency）**：同步调用、跨区流量、日志全量落盘等隐性成本。

```python
# 用简单利用率表找出「该杀的实例」
instances = [
    {"id": "i-dev-01", "cpu_util": 0.02, "cost": 120},
    {"id": "i-gpu-02",  "cpu_util": 0.85, "cost": 800},
    {"id": "i-batch-03","cpu_util": 0.03, "cost": 300},
]
idle = [i for i in instances if i["cpu_util"] < 0.05]
print("闲置实例:", [i["id"] for i in idle])
print("可回收金额/月:", sum(i["cost"] for i in idle))
```

**结论**：优化顺序应是 **先关闲置 → 再调规格 → 最后才改架构**，投入产出比最高。

---

## 3. 五种主流优化手段

### 3.1 合理选型（Right-sizing）
按 P95 负载而不是峰值买机器。

```python
import statistics
latencies = [50, 55, 52, 60, 58, 300, 54, 53, 57, 56]  # ms
p95 = sorted(latencies)[int(len(latencies)*0.95)]
print(f"P95 延迟: {p95} ms -> 按此规格选型，而非按最大值 300")
```

### 3.2 弹性伸缩（Auto-scaling）
按负载动态增减实例，避免为峰值长期付费。

```python
# 简单伸缩策略：CPU > 70% 扩容，< 30% 缩容
def scale(current, cpu):
    if cpu > 0.7: return min(current + 1, 20)
    if cpu < 0.3: return max(current - 1, 2)
    return current
print(scale(5, 0.85), scale(5, 0.2), scale(5, 0.5))  # 6 4 5
```

### 3.3 预留与竞价（Reserved / Spot）
- **预留实例（Reserved Instance）**：承诺 1~3 年，折扣 30%~60%，适合稳定负载。
- **竞价实例（Spot Instance）**：折扣 60%~90%，但可能被回收，适合可中断任务（如批处理、训练）。

```python
def blended_cost(base, pct_reserved=0.6, pct_spot=0.3):
    on_demand = 1 - pct_reserved - pct_spot
    return base * (pct_reserved*0.5 + pct_spot*0.2 + on_demand*1.0)
print(f"混合采购后单价: ${blended_cost(1.0):.3f}（原价 $1.000）")
```

### 3.4 存储分层（Storage Tiering）
热数据放标准层，冷数据放归档层（价格差可达 10 倍以上）。

```python
# 按访问频率分层：最近 30 天热存，其余归档
files = [{"name":"a", "days_since_access": 2},
         {"name":"b", "days_since_access": 400}]
for f in files:
    tier = "STANDARD" if f["days_since_access"] < 30 else "ARCHIVE"
    print(f"{f['name']} -> {tier}")
```

### 3.5 架构级优化
- 把训练任务放到 GPU 竞价池，用**检查点（Checkpoint）** 抗中断。
- 用**批处理（Batching）** 提高 GPU 利用率。
- 减少跨区（Cross-AZ）流量。

```python
# 批处理：GPU 利用率从 20% 提升到 80%，单位成本下降 4 倍
util_before, util_after = 0.2, 0.8
print(f"单位成本降低: {(1/util_before - 1/util_after)/(1/util_before):.0%}")
```

---

## 4. 工程级做法：可观测性 + 预算告警 + 持续治理

真正落地的成本优化是一套**持续流程**，不是一次性动作：

1. **打标签（Tagging）**：所有资源必须带 `team` / `project` / `env` 标签，否则无法归因。
2. **可观测性（Observability）**：每日抓取账单 + 利用率指标，做趋势对比。
3. **预算告警（Budget Alert）**：月度预算达 80% 自动告警。
4. **定期复盘**：每月清理闲置、审查预留覆盖率、评估架构。

```python
# 一个最小可用的成本看板逻辑
budget = 5000
current = 4300
usage_ratio = current / budget
if usage_ratio >= 0.8:
    print(f"⚠️ 预算告警：已使用 {usage_ratio:.0%}")
tags_ok = {"team": "ml", "env": "prod"}
assert "team" in tags_ok and "env" in tags_ok, "资源必须打标签"
print("标签检查通过，可归因")
```

**结论**：成本优化的工程化 = **度量 → 告警 → 治理 → 复盘** 的闭环。

---

## 5. 总结：记住这条清单

- 用单位经济学（Unit Economics）衡量成本，不看总账单。
- 先关闲置，再调规格，最后动架构。
- 三种采购方式混用：按需 + 预留 + 竞价。
- 存储分层、批处理、减少跨区是常见「免费午餐」。
- 没有标签就没有成本治理。

---

## 动手练习

**任务**：给你一个月的云账单数据（下表中的小样本），完成一份「优化建议报告」。

数据（`instances.csv` 内容，可自行保存）：
```
id,type,cpu_util,cost_per_month,tags
web-01,t3.medium,0.15,60,team=web;env=prod
web-02,t3.medium,0.08,60,team=web;env=prod
batch-01,c5.4xlarge,0.03,500,team=data
batch-02,c5.4xlarge,0.75,500,team=data
gpu-01,p3.2xlarge,0.90,2500,team=ml
gpu-02,p3.2xlarge,0.00,2500,team=ml
```

**要求**：
1. 用 Python 读取数据（可硬编码为列表）。
2. 识别出所有 `cpu_util < 0.05` 的闲置实例，计算可回收金额。
3. 对 `team=ml` 的 GPU 实例给出「竞价实例 + 检查点」的建议。
4. 打印一份格式化的报告，包含：总成本、可优化金额、优化后预期成本。

**交付物**：一个 `cost_report.py` 脚本 + 运行输出。

**评分要点**：能否正确识别闲置、是否给出采购策略建议、报告是否可读。

```python
# cost_report.py —— 云成本优化最小示例
instances = [
    {"id": "web-01",   "type": "t3.medium", "cpu_util": 0.15, "cost": 60,   "tags": {"team": "web", "env": "prod"}},
    {"id": "web-02",   "type": "t3.medium", "cpu_util": 0.08, "cost": 60,   "tags": {"team": "web", "env": "prod"}},
    {"id": "batch-01", "type": "c5.4xlarge","cpu_util": 0.03, "cost": 500,  "tags": {"team": "data"}},
    {"id": "batch-02", "type": "c5.4xlarge","cpu_util": 0.75, "cost": 500,  "tags": {"team": "data"}},
    {"id": "gpu-01",   "type": "p3.2xlarge","cpu_util": 0.90, "cost": 2500, "tags": {"team": "ml"}},
    {"id": "gpu-02",   "type": "p3.2xlarge","cpu_util": 0.00, "cost": 2500, "tags": {"team": "ml"}},
]

# 1) 总成本
total_cost = sum(i["cost"] for i in instances)

# 2) 识别闲置 (cpu_util < 0.05)
idle = [i for i in instances if i["cpu_util"] < 0.05]
idle_saving = sum(i["cost"] for i in idle)

# 3) GPU 竞价策略：占 ml 团队的 70% 折扣
ml_gpus = [i for i in instances if i["tags"].get("team") == "ml" and i["cpu_util"] > 0.5]
ml_cost = sum(i["cost"] for i in ml_gpus)
spot_saving = ml_cost * 0.7  # 竞价折扣 70%

# 4) 报告
print("=" * 40)
print(f"总成本            : ${total_cost:,}")
print(f"闲置实例          : {[i['id'] for i in idle]}")
print(f"闲置可回收        : ${idle_saving:,}")
print(f"GPU 竞价可节省    : ${spot_saving:,.0f}")
print(f"优化后预期成本    : ${total_cost - idle_saving - spot_saving:,.0f}")
print("=" * 40)
```

## arch.cloud.multi_region

## 一句话直觉

**多区域（Multi-Region）架构**就是让同一个系统同时跑在地理上相隔很远的多个云区域里，这样一处机房挂了，其他区域还能继续服务用户——它是把"可用性"和"延迟"从单点提升到全球级别的第一课。

---

### 1. 什么是区域与多区域

**区域（Region）** 是云厂商在地理上划分的独立数据中心集群，比如 `us-east-1`、`ap-southeast-1`、`cn-hangzhou`。每个区域内部又有多个**可用区（Availability Zone, AZ）**，AZ 之间电力、网络、冷却相互独立。

**多区域（Multi-Region）** 指同一个应用部署在至少两个不同 Region 中。它的目标不是简单的"备份"，而是让流量可以在区域之间切换或分流。

```python
# 用字典模拟一个多区域部署清单
regions = {
    "us-east-1": {"zones": ["us-east-1a", "us-east-1b"], "role": "active"},
    "ap-southeast-1": {"zones": ["ap-southeast-1a", "ap-southeast-1b"], "role": "active"},
}

for name, info in regions.items():
    print(f"{name} -> AZ 数量: {len(info['zones'])}, 角色: {info['role']}")
```

**关键结论：** 一个 Region 内多 AZ 解决的是"单机房故障"，多 Region 解决的是"整个地理区域故障"，二者是包含关系。

---

### 2. 为什么需要多区域：可用性、延迟、合规

- **可用性（Availability）**：单区域即使多 AZ，也可能因为区域级网络或控制面故障而整体不可用。
- **延迟（Latency）**：用户在日本，请求打到美国东海岸，光速往返就要 150ms 以上。就近接入能把延迟压到几十毫秒。
- **合规（Compliance）**：某些国家要求用户数据必须留在本国境内，必须本地部署。

```python
# 用简单的数学示意 RTT（往返时延）对用户体验的影响
import math

def rtt_ms(distance_km: float) -> float:
    # 光纤中光速约为 200,000 km/s，往返乘 2
    return distance_km * 2 / 200_000 * 1000

print("东京 -> 东京 :", round(rtt_ms(500), 1), "ms")
print("东京 -> 美国西海岸:", round(rtt_ms(8800), 1), "ms")
print("东京 -> 美国东海岸:", round(rtt_ms(11000), 1), "ms")
```

**关键结论：** 多区域不是"更贵更稳"的玄学，而是用物理距离换延迟、用冗余换可用性的工程取舍。

---

### 3. 多区域架构的三种典型模式

1. **主动-被动（Active-Passive）**：一个区域接流量，另一个区域热备，故障时切换。实现简单，但备用区域平时浪费资源，切换时有 RTO（恢复时间目标）。
2. **主动-主动（Active-Active）**：两个区域同时接流量，就近路由。可用性和延迟都最好，但数据一致性最难。
3. **分片式（Sharded / Cell-Based）**：每个区域只服务一部分用户，通过路由把用户"钉"在某个区域。

```python
# 主动-主动的极简流量路由示例
def route_user(user_region: str, healthy_regions: list[str]) -> str:
    if user_region in healthy_regions:
        return user_region  # 就近
    return healthy_regions[0]  # 降级到任意健康区域

healthy = ["us-east-1", "ap-southeast-1"]
print(route_user("ap-southeast-1", healthy))  # 命中本地
print(route_user("eu-west-1", healthy))        # 回退
```

**关键结论：** 模式选择由业务决定：能接受短暂停机就用主动-被动，要求极致体验才上主动-主动。

---

### 4. 数据一致性与复制：多区域最硬的骨头

跨区域复制（Replication）有同步和异步两种：

- **同步复制（Synchronous）**：写请求要等所有区域确认，强一致，但延迟高、可用性差。
- **异步复制（Asynchronous）**：本地写完就返回，后台复制，延迟低，但可能丢数据或读到旧值。
- **CRDT / 最终一致（Eventual Consistency）**：冲突用规则自动合并，适合计数器、集合等场景。

```python
# 用版本号模拟"最后写入胜出"（Last-Write-Wins）
from dataclasses import dataclass

@dataclass
class Record:
    value: str
    version: int

def merge(a: Record, b: Record) -> Record:
    return a if a.version >= b.version else b

r1 = Record("from-east", 3)
r2 = Record("from-west", 5)
print(merge(r1, r2).value)  # from-west
```

**关键结论：** 多区域下不要幻想"完美强一致 + 低延迟 + 高可用"同时成立，CAP 定理（Consistency, Availability, Partition tolerance）会逼你选边。

---

### 5. 工程落地：DNS、健康检查与故障切换

多区域落地的最后一公里是**流量调度**：

- **DNS 地理路由（GeoDNS）**：根据用户 IP 返回最近区域的地址。
- **Anycast**：同一 IP 在全球多节点宣告，网络层自动选最近。
- **健康检查（Health Check）**：探测区域是否可用，不可用就从 DNS 摘掉。
- **故障切换（Failover）**：自动或手动把流量切到健康区域。

```python
# 模拟一次带健康检查的 GeoDNS 解析
geo_map = {"JP": "ap-southeast-1", "US": "us-east-1"}
health = {"ap-southeast-1": True, "us-east-1": False}

def resolve(country: str) -> str:
    primary = geo_map.get(country, "us-east-1")
    if health.get(primary, False):
        return primary
    # 回退到任意健康区域
    return next(r for r, ok in health.items() if ok)

print(resolve("JP"))
print(resolve("US"))
```

**关键结论：** 多区域不是部署完就结束，而是一个持续监控、演练、切换的运维闭环。

```python
import time
from dataclasses import dataclass, field

@dataclass
class Region:
    name: str
    latency_ms: int
    healthy: bool = True
    writes: int = 0

class MultiRegionStore:
    """极简多区域键值存储：本地写、异步复制、读就近。"""
    def __init__(self, regions):
        self.regions = {r.name: r for r in regions}
        self.data = {r.name: {} for r in regions}

    def write(self, region_name, key, value):
        region = self.regions[region_name]
        if not region.healthy:
            raise RuntimeError(f"{region_name} 不可用")
        self.data[region_name][key] = value
        region.writes += 1
        self._replicate(key, value, source=region_name)

    def _replicate(self, key, value, source):
        for name, region in self.regions.items():
            if name == source or not region.healthy:
                continue
            time.sleep(region.latency_ms / 1000)  # 模拟网络延迟
            self.data[name][key] = value

    def read_nearest(self, user_region):
        candidates = [r for r in self.regions.values() if r.healthy]
        nearest = min(candidates, key=lambda r: r.latency_ms)
        return nearest.name, self.data[nearest.name]

if __name__ == "__main__":
    store = MultiRegionStore([
        Region("us-east-1", latency_ms=10),
        Region("ap-southeast-1", latency_ms=20),
    ])
    store.write("ap-southeast-1", "user:1", "alice")
    print(store.read_nearest("ap-southeast-1"))
    print(store.read_nearest("us-east-1"))
```


---

## 本课题目

### single_choice · None



- [A] 预留实例锁定了实例族与地域，若半年后需要换更大规格或换地域，灵活性会受限，可能产生浪费
- [B] 预留实例随时可以无损退订，所以完全不必担心负载变化
- [C] 预留实例自动随负载扩容，因此是最佳选择
- [D] 预留实例只对无状态服务有效，对有状态服务没有折扣

**参考答案**：0

**解析**：预留实例以承诺换取折扣，通常绑定实例族、地域和期限，需求变化时灵活性差、可能闲置浪费，这是成本优化中「承诺折扣 vs 弹性」的核心权衡。

### single_choice · None



- [A] 购买包年包月的专用物理机，因为稳定
- [B] 使用按量付费/竞价实例，任务结束后释放资源
- [C] 无论如何都应选择预留实例，因为单价最低
- [D] 把任务改成 7x24 运行以摊薄成本

**参考答案**：1

**解析**：间歇性、可中断的工作负载适合按量付费或竞价实例，只为实际使用时间付费；包年包月会让大量空闲时间也被计费。

### single_choice · None



- [A] 保持现状，因为大规格更稳定
- [B] 按日常负载配置资源，峰值时通过自动伸缩或弹性负载均衡应对
- [C] 把规格再提高一倍以留足余量
- [D] 取消所有监控以节省费用

**参考答案**：1

**解析**：容量应按常态负载规划，峰值通过弹性能力吸收；长期按极端峰值配置会导致大部分容量闲置付费。

### single_choice · None



- [A] 闲置资源不影响成本，可以忽略
- [B] 定期盘点未挂载的存储卷、未使用的弹性 IP、长期空闲的实例并释放，可显著降本
- [C] 只要资源创建过就必须付费一辈子
- [D] 闲置资源会自动被云厂商回收并退费

**参考答案**：1

**解析**：未挂载的卷、未绑定的 IP、空闲实例等仍会产生费用，需要通过盘点与清理来消除浪费；云厂商通常不会自动回收。

### single_choice · None



- [A] 只看本月总账单，不做任何对比
- [B] 对比优化前后同类工作负载的单位成本（如每千次请求成本）
- [C] 只看资源数量有没有减少
- [D] 只关注单价是否下降

**参考答案**：1

**解析**：单位成本（每请求/每用户/每任务成本）能剔除业务量变化的影响，是衡量优化效果更可靠的指标。

### single_choice · None



- [A] 它们是最昂贵的实例类型，只适合关键业务
- [B] 价格较低但可能被回收，适合可中断、可重试的批处理类任务
- [C] 一旦申请就永久不会被中断
- [D] 它们与按量付费实例价格完全相同

**参考答案**：1

**解析**：竞价实例以可能被回收换取更低价格，适合无状态、可重试的批处理；对有状态或强一致要求的服务风险较高。

### single_choice · None



- [A] 把所有实例规格统一调大以保证性能
- [B] 根据实际监控数据把实例调整为更匹配负载的规格
- [C] 只调整存储类型，不调整计算资源
- [D] 把实例迁移到更贵的区域

**参考答案**：1

**解析**：右调规格是依据真实利用率选择合适规格，避免长期资源过大造成浪费或过小影响性能。

### single_choice · None



- [A] 提高后端服务器规格以加快读取
- [B] 引入 CDN/缓存层，让静态内容就近分发并减少回源
- [C] 把图片改为更小的分辨率并删除原图
- [D] 限制用户访问频率

**参考答案**：1

**解析**：CDN 与缓存能显著降低回源流量和源站负载，从而降低带宽与计算成本；单纯提升规格或删数据不是合理的成本优化。

### single_choice · None



- [A] 设置预算告警会自动阻止所有资源创建
- [B] 设置预算与成本告警可以在费用异常增长时及时通知，便于人工介入
- [C] 预算功能只对大企业有效，小团队无意义
- [D] 预算告警只能按月设置，不能按项目设置

**参考答案**：1

**解析**：预算与告警用于及时发现异常支出并触发处理流程，本身不强制阻断资源；可按多种维度设置。

### single_choice · None



- [A] 提高单价折扣
- [B] 隔离账单与权限，便于按环境/团队核算成本并防止误用
- [C] 自动减少所有资源费用
- [D] 免除网络流量费用

**参考答案**：1

**解析**：账号隔离是成本治理的常见手段：账单边界清晰、权限可控，能防止资源被随意创建导致费用失控。

### single_choice · None



- [A] 无论是否调用都按固定月费收取
- [B] 按实际调用次数与执行时长计费，低流量场景可能更省，但高频持续负载下未必比常驻实例便宜
- [C] Serverless 一定比虚拟机便宜
- [D] Serverless 不产生任何费用

**参考答案**：1

**解析**：Serverless 计费与使用强相关，适合间歇或突发负载；持续高负载时按调用计费可能超过常驻实例，需要根据负载特征选择。

### single_choice · None



- [A] 检查是否存在跨可用区/跨地域的频繁调用或不当的公网出口路径
- [B] 提高实例 CPU 规格
- [C] 增加更多存储卷
- [D] 关闭监控系统

**参考答案**：0

**解析**：流量费用异常往往来自架构路径问题：跨区调用、绕行公网、NAT 出口设计不当等，应优先从网络拓扑排查。

### single_choice · None



- [A] 数据写入后 1 秒内被高频读取
- [B] 访问日志写入后 30 天内偶尔查询，之后几乎不再访问但需长期留存
- [C] 需要低延迟随机读写的数据库文件
- [D] 需要在多台服务器间共享的块设备

**参考答案**：1

**解析**：生命周期策略用于随访问频率下降将数据从高频层转移到低频/归档层，适合「先热后冷且需长期保留」的数据。

### single_choice · None



- [A] 按量付费单价通常更高，但无需长期承诺，适合需求不确定的场景
- [B] 按量付费单价通常更低，且无任何使用限制
- [C] 包年包月一定比按量付费总成本更低，无论使用多久
- [D] 两者单价完全相同，区别仅在计费周期

**参考答案**：0

**解析**：云厂商用折扣换取用户的长期承诺：按量单价高但灵活，包年/预留单价低但需承诺期限，是否更省取决于实际使用时长。

### single_choice · None



- [A] 把实例规格统一调小，白天再加回来
- [B] 配置基于负载的自动伸缩，在低峰期缩减实例数量
- [C] 把所有实例改为预留实例
- [D] 提高监控告警阈值

**参考答案**：1

**解析**：负载有明显峰谷时，自动伸缩让资源跟随需求变化，避免低峰期为空闲容量付费，这是弹性带来的成本优化。

### single_choice · None



- [A] 为每个容器预留远超实际需求的 CPU 和内存
- [B] 根据实际用量设置合理的资源请求与限制并提高装箱率
- [C] 让所有容器都使用独占的物理节点
- [D] 把容器改为在本地机房运行

**参考答案**：1

**解析**：合理设置 requests/limits 并提高节点装箱率，可以让同样的硬件承载更多负载；过度预留则会造成资源碎片和浪费。

### single_choice · None



- [A] 云上所有网络流量都完全免费
- [B] 把数据从云内传到公网通常会计费，且跨可用区/跨地域传输也可能产生费用
- [C] 只有入网流量收费，出网流量免费
- [D] 出网流量只在夜间收费

**参考答案**：1

**解析**：多数云厂商对公网出流量、跨区/跨地域流量计费，入网流量通常免费，网络设计不当会带来难以察觉的成本。

### single_choice · None



- [A] 让所有服务随机分布在所有可用区，不做任何约束
- [B] 将频繁通信的服务尽量部署在同一可用区内，或利用同区域内的本地路由
- [C] 把所有服务集中到单一可用区以彻底消除跨区流量
- [D] 关闭所有可用区之间的网络连通

**参考答案**：1

**解析**：跨可用区会产生流量费用并增加延迟，减少跨区调用能在保持一定冗余的前提下优化成本；但把所有服务塞进单可用区会牺牲高可用。

### single_choice · None



- [A] 把数据库从托管服务迁移到自建虚拟机以省掉服务费
- [B] 分析慢查询与索引使用情况，优化查询并选择合适的实例规格与存储类型
- [C] 关闭数据库备份以节省存储费用
- [D] 把所有数据表都加上冗余索引

**参考答案**：1

**解析**：数据库成本优化通常从查询效率、索引、实例规格与存储层级入手；盲目自建或关闭备份会引入风险，加冗余索引反而增加开销。

### single_choice · None



- [A] 标签只用于美化资源列表，对成本分析没有帮助
- [B] 给资源打上项目/团队/环境等标签，可以按维度归集和分摊费用，定位成本来源
- [C] 标签会自动降低资源单价
- [D] 标签只能设置一个，不能组合使用

**参考答案**：1

**解析**：标签是把账单映射到业务维度的基础能力，缺标签会导致无法定位成本归属；标签本身不会改变单价。

### single_choice · None



- [A] 降低用户访问延迟
- [B] 减少代码的单元测试数量
- [C] 消除所有类型的软件缺陷
- [D] 自动提高数据库的写入吞吐量

**参考答案**：0

**解析**：多区域部署把服务实例放在离用户更近的位置，最直接的收益是网络往返时间变短，访问延迟降低。它不能消除缺陷，也不必然提升单库写入吞吐。

### single_choice · None



- [A] 区域是同一个机房内的一组机架
- [B] 区域是地理上相互隔离的一组数据中心，通常拥有独立的供电与网络
- [C] 区域等同于一个操作系统进程
- [D] 区域是代码仓库中的一个分支

**参考答案**：1

**解析**：区域通常指地理隔离、具备相对独立基础设施的一组数据中心。机架属于更细粒度的概念，区域与进程、代码分支无关。

### multi_choice · None



- [A] 降低地理上分散用户的访问延迟
- [B] 在某区域故障时仍能继续提供服务，提升可用性
- [C] 满足数据必须留在特定地理范围内的合规要求
- [D] 自动让所有单元测试都通过
- [E] 显著减少代码总量

**参考答案**：[0, 1, 2]

**解析**：多区域的常见动机是降低延迟、提升容灾可用性和满足数据驻留合规。让测试通过、减少代码量与其无关。

### multi_choice · None



- [A] 一致性模型（强一致还是最终一致）
- [B] 冲突检测与解决策略
- [C] 跨区域链路的延迟与带宽
- [D] 开发者的编辑器配色方案

**参考答案**：[0, 1, 2]

**解析**：一致性强弱、冲突处理以及链路延迟带宽都会直接影响跨区域数据同步的正确性与性能。编辑器配色与此无关。

### multi_choice · None



- [A] 可以基于用户地理位置把请求路由到最近区域
- [B] 路由策略需要考虑目标区域是否健康
- [C] 把所有流量强制路由到单一区域一定比就近路由延迟更低
- [D] 路由决策可能受到数据驻留等合规约束影响

**参考答案**：[0, 1, 3]

**解析**：就近路由、健康感知和合规约束都是真实存在的路由考量；强制单区域路由通常不会比就近路由延迟更低。

### multi_choice · None



- [A] 不同区域的副本在同一时刻可能读到不同的值
- [B] 短暂的读陈旧数据窗口
- [C] 所有写操作都会瞬时在全局可见
- [D] 需要设计冲突解决或幂等机制

**参考答案**：[0, 1, 3]

**解析**：最终一致意味着副本间存在短暂不一致窗口，可能读到陈旧数据，并需要冲突或幂等处理。写操作瞬时全局可见与最终一致矛盾。

### fill_blank · None



**参考答案**：["冲突解决", "冲突处理", "conflict resolution"]

**解析**：多主或跨区域写入容易产生冲突，必须有一套冲突检测与解决策略来收敛到一致状态。

### fill_blank · None



**参考答案**：["区域", "地理区域", "region", "边缘节点"]

**解析**：把资源分布到多个区域或边缘节点，让用户就近获取，是多区域下降低延迟的常见手段。

### code_reading · None



**参考答案**：可能读到旧值（写尚未同步过去），因为跨区域复制是异步进行的，此时系统表现为最终一致而非强一致。

**解析**：写只在本地副本立即生效，随后异步复制到其他区域，因此另一区域短时间内可能读到尚未更新的旧数据。

### code_reading · None



**参考答案**：同时考虑了区域的健康状态（是否可用）和与用户的地理距离（就近选择）。

**解析**：先过滤掉不健康的区域，再从健康区域中按距离选取最近的一个，兼顾了可用性与延迟。

### scenario · None



**解析**：场景要求在就近访问、容灾和跨区域可见性之间取舍。合理回答应指出跨区域强一致会抬高延迟，并围绕一致性模型选择、数据同步策略、故障隔离与路由等给出权衡方案。

### scenario · None



**解析**：该场景的核心矛盾在于数据驻留合规与全局统一视图之间的冲突。回答应指出需要按区域就地存储受约束数据，并通过受控的聚合或查询路径提供统一视图，同时处理好一致性问题。

### single_choice · None



- [A] 把变量名改得更短
- [B] 确定各区域之间数据如何同步与冲突如何解决
- [C] 把日志级别统一改成 DEBUG
- [D] 删除所有自动化测试以加快发布

**参考答案**：1

**解析**：多区域的核心难点在于跨区域数据一致性与冲突处理，而不是命名、日志级别或减少测试。

### single_choice · None



- [A] 一个区域的故障不应导致其他区域的服务同时不可用
- [B] 所有区域的数据库必须共用同一块磁盘
- [C] 每次发布必须同时在所有区域回滚
- [D] 用户只能访问自己所在区域的服务

**参考答案**：0

**解析**：故障隔离的目标是把故障影响限制在局部，避免单区域问题波及全局。共用磁盘反而会放大故障，回滚策略与隔离无关。

### single_choice · None



- [A] 单区域单活
- [B] 多区域读扩展、单点写入（主从式多区域）
- [C] 完全对等的多主写入
- [D] 无状态边缘缓存

**参考答案**：1

**解析**：读可以在多个区域本地处理，而写集中在主区域，是一种常见的折中方案，避免了多主写入的冲突问题。

### single_choice · None



- [A] CPU 主频会下降
- [B] 网络往返延迟显著增大，且可能受跨区域链路波动影响
- [C] 内存容量会自动减半
- [D] 代码编译时间变长

**参考答案**：1

**解析**：跨区域通信受物理距离与链路质量影响，延迟更高且更不稳定，这是多区域设计需要重点权衡的因素。

### single_choice · None



- [A] 这是完全免费的，任何数据库都天然支持
- [B] 就近读写与强一致通常存在张力，需要在一致性、延迟和可用性之间权衡
- [C] 只要多加几台服务器就能自动实现
- [D] 强一致一定会让延迟变得更低

**参考答案**：1

**解析**：跨区域强一致需要协调多个区域的副本，往往带来更高延迟；就近读写则倾向本地化。两者需要权衡，属于典型的分布式取舍。

### single_choice · None



- [A] 数据库所在区域一旦故障，会波及所有区域的服务
- [B] 用户的访问延迟会降低到零
- [C] 数据会自动分片到各区域
- [D] 各区域之间的网络延迟会消失

**参考答案**：0

**解析**：共享单一数据库会形成跨区域的单点故障，丧失了故障隔离的意义，某一区域出问题可能影响全局。

### single_choice · None



- [A] 数据必须加密存储在所有区域
- [B] 某些用户数据必须存储在规定的地理区域境内，不得随意跨境传输
- [C] 所有数据必须集中存放在总部机房
- [D] 数据只能由单一区域的运维人员访问

**参考答案**：1

**解析**：数据驻留/主权要求数据留存和处理的物理位置符合当地法规，这会直接影响多区域的复制与路由策略。

### single_choice · None



- [A] 进程永远不会退出
- [B] 健康检查会一直返回失败
- [C] 实例可能在依赖不可用时仍被判定为健康，继续接收流量并大量报错
- [D] 数据库会自动切换主区域

**参考答案**：2

**解析**：仅检查进程存活的健康检查无法反映真实可用性，实例可能在依赖不可达时仍被判为健康，导致流量被误导并放大错误。
