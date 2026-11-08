# s8u4l2 Istio 服务网格（Service Mesh）入门：从零到工程级 / 传统部署方式下，你要提前买好服务器

> 来源 `content/lessons/s8u4l2.json`

## arch.cloud.istio

# Istio 服务网格（Service Mesh）入门：从零到工程级

> **一句话直觉**：当你的 AI 服务从一个 Python 脚本变成由几十个微服务组成的系统时，你会发现「服务之间怎么安全、稳定、可观测地互相调用」比「模型本身」更难搞定——Istio 就是用来解决这件事的「服务间通信基础设施层」。

---

## 0. 为什么 AI 工程师也要懂 Istio？

在 PyTorch 教程里，我们写的是一个 `model = Net()` 然后 `train`。但在真实工程项目中，模型会被拆成：
- 一个**预处理服务**（preprocess）
- 一个**推理服务**（inference，跑 PyTorch）
- 一个**后处理/业务逻辑服务**
- 一个**特征存储服务**（feature store）

于是问题来了：
- 推理服务重启了，预处理服务怎么自动找到新的 IP？
- 想让 5% 流量走新模型做 A/B 测试，怎么做到不改一行业务代码？
- 某个服务被拖慢时，怎么一键熔断，不让整个链路雪崩？
- 想给所有服务之间加 mTLS 加密，难道每段代码都要改？

**Istio 的答案**：把「服务发现、流量管理、安全、可观测」这四件事从业务代码里抽出来，下沉到「Sidecar 代理 + 控制平面」。业务代码只关心「调用谁」，Istio 关心「怎么调用」。

---

## 1. 核心概念：数据平面 vs 控制平面

Istio 的架构分成两层：

| 层 | 组件 | 干啥的 |
|---|---|---|
| **数据平面（Data Plane）** | Envoy 代理（Sidecar） | 每个 Pod 里塞一个，拦截所有进出流量 |
| **控制平面（Control Plane）** | istiod | 下发配置、签发证书、做服务发现 |

关键直觉：**你的 Python 代码完全感知不到 Istio 的存在**。它以为自己在 `POST http://inference-svc:8000/predict`，实际上流量被本地的 Envoy 拦走了，Envoy 再决定发给谁、加什么 header、要不要重试。

```python
# 从 PyTorch 服务端视角看：代码里没有任何 Istio 痕迹
import torch, torch.nn as nn
from fastapi import FastAPI

class Net(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc = nn.Linear(784, 10)
    def forward(self, x):
        return self.fc(x)

app = FastAPI()
model = Net()

@app.post("/predict")
def predict(x: list[float]):
    # 业务代码只管模型推理
    t = torch.tensor([x])
    return {"logits": model(t).tolist()}
# 至于这个服务被谁调用、流量怎么切、mTLS 怎么加——Istio 全包了
```

---

## 2. 流量管理：VirtualService 与 DestinationRule

Istio 最常用的两个 CRD（Custom Resource Definition，自定义资源）：

- **VirtualService**：定义「请求怎么路由」（金丝雀、A/B、重试、超时）
- **DestinationRule**：定义「到达之后怎么处理」（负载均衡、连接池、熔断）

### 场景：让 5% 流量走新模型

```yaml
# 1) VirtualService：按权重切流量
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: inference-svc
spec:
  hosts: ["inference-svc"]
  http:
  - route:
    - destination: {host: inference-svc, subset: v1}
      weight: 95          # 老模型
    - destination: {host: inference-svc, subset: v2}
      weight: 5           # 新模型灰度
---
# 2) DestinationRule：定义 v1/v2 对应的 Pod 标签
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: inference-svc
spec:
  host: inference-svc
  subsets:
  - name: v1
    labels: {version: v1}
  - name: v2
    labels: {version: v2}
```

**注意**：你的 FastAPI 代码一个字没改。这就是服务网格的价值。

---

## 3. 安全：自动 mTLS（Mutual TLS）

Istio 默认开启**自动双向 TLS**：服务 A 调服务 B 时，双方用 Istio 自动签发的证书互相验证。这解决了两件事：

1. **加密**：内网流量也不裸奔
2. **身份**：B 能确认「你真是 A」，而不是某个伪装的服务

```yaml
# 强制全网格 mTLS（默认就是 STRICT，一般不用手写）
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: istio-system
spec:
  mtls:
    mode: STRICT
```

对应的**授权策略**（谁能调谁）：

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: allow-preprocess-to-inference
  namespace: default
spec:
  selector:
    matchLabels: {app: inference-svc}
  action: ALLOW
  rules:
  - from:
    - source:
        principals: ["cluster.local/ns/default/sa/preprocess-svc"]
```

这比在 Python 里手写 JWT 校验靠谱得多。

---

## 4. 可观测性：不写一行埋点代码的监控

Istio 的 Sidecar 会自动采集三类信号：

- **Metrics**：请求量、延迟 P50/P99、错误率（Prometheus 格式）
- **Traces**：分布式调用链（需接 Jaeger/Tempo）
- **Logs**：访问日志

对 AI 工程尤其有价值：**推理服务的 P99 延迟、GPU 请求排队、模型版本维度指标**，全都能从这个层面看到。

```python
# 本地模拟：Istio 暴露的指标长这样（Prometheus 文本格式）
# 真实环境中这些数字由 Envoy 自动产生，无需业务代码
sample_metrics = '''
istio_requests_total{reporter="destination",destination_service="inference-svc",response_code="200"} 10234
istio_request_duration_milliseconds_bucket{destination_service="inference-svc",le="100"} 8000
istio_request_duration_milliseconds_bucket{destination_service="inference-svc",le="500"} 10100
istio_request_duration_milliseconds_bucket{destination_service="inference-svc",le="+Inf"} 10234
'''

# 简单解析：算一下 P99 大概落在哪个桶
import re
buckets = re.findall(r'le="([^"]+)"\} (\d+)', sample_metrics)
print("延迟分桶:", buckets)
# 输出示例: [('100', '8000'), ('500', '10100'), ('+Inf', '10234')]
# P99 ≈ 101 秒内，说明绝大多数请求在 500ms 以内
```

---

## 5. 一次完整的「AI 推理链路」长什么样

```
[Client]
   │
   ▼
[Gateway] ──► [preprocess-svc + Envoy] ──► [inference-svc + Envoy]
                                              │
                                              ▼
                                        [v1: PyTorch 模型]
                                        [v2: 新 PyTorch 模型]  ← 5% 灰度
```

- Gateway 负责南北向流量（外部 → 内部）
- VirtualService 负责东西向流量（内部 → 内部）
- 每个 `+ Envoy` 都是自动注入的 Sidecar
- 全程 mTLS、全程可观测、全程可灰度

---

## 6. 常见误区（先看一眼，别踩坑）

- **Istio ≠ API Gateway**：Gateway 只是 Istio 的一部分，东西向才是主业。
- **Istio 不替你做业务重试逻辑**：它只重试「网络层可重试的错误」，业务幂等性还得自己保证。
- **Sidecar 会加延迟**：通常每跳增加 1~3ms，对 GPU 推理这类长任务是可忽略的，但对高频小请求要评估。
- **不是所有服务都适合上网格**：数据库、消息队列客户端有时候要特殊配置绕过 Sidecar。

---

## 7. 动手练习

**任务**：在本地用 `kind`（Kubernetes in Docker）搭一个最小 Istio 环境，部署两个最小 FastAPI 服务，实现 90/10 灰度。

```bash
# 1) 装 kind 和 kubectl（略），然后：
kind create cluster --name istio-lab

# 2) 装 istioctl
# 参考官方: https://istio.io/latest/docs/setup/getting-started/
istioctl install --set profile=demo -y

# 3) 开启 default 命名空间自动注入
kubectl label namespace default istio-injection=enabled

# 4) 部署两个版本
kubectl apply -f inference-v1.yaml
kubectl apply -f inference-v2.yaml
kubectl apply -f inference-svc.yaml

# 5) 应用上面的 VirtualService + DestinationRule
kubectl apply -f vs-dr.yaml

# 6) 循环请求 100 次，统计 v1/v2 各返回多少次
for i in $(seq 1 100); do
  curl -s http://inference-svc/predict -d '{"x": [0.1]*784}' \
       -H 'Content-Type: application/json' | jq -r .version
done | sort | uniq -c
```

**验收标准**：输出结果约为 `90 v1` 与 `10 v2`。把结果截图发到课程讨论区，并写 3 句话总结：Sidecar 注入前后，`curl` 的返回有什么差别？

---

## 小结

| 概念 | 一句话记忆 |
|---|---|
| Service Mesh | 把服务间通信能力从代码里抽出来 |
| Envoy Sidecar | 每个 Pod 里的「通信秘书」 |
| istiod | 下发配置、签发证书的「大脑」 |
| VirtualService | 定义「请求怎么走」 |
| DestinationRule | 定义「到达后怎么办」 |
| PeerAuthentication | 自动 mTLS，不用改代码 |

记住一句话：**业务代码只管模型，通信和安全交给 Istio。**

## arch.cloud.autoscale

## 一句话直觉

**云自动扩缩容（Cloud Autoscaling）** 就是让系统根据当前负载自动增加或减少计算资源：人多时多开机器，人少时关掉机器，既不让用户卡，也不让老板多花钱。

---

## 第 1 节：为什么需要自动扩缩容

传统部署方式下，你要提前买好服务器。买少了：促销一来网站崩；买多了：平时机器空转烧钱。

自动扩缩容解决的是**容量与需求之间的动态匹配问题**。核心目标有两个：

1. **可用性（Availability）**：负载升高时及时扩容，避免超时和宕机。
2. **成本效率（Cost Efficiency）**：负载降低时及时缩容，避免资源浪费。

关键结论：自动扩缩容不是“越多越好”，而是在 **SLA（Service Level Agreement，服务等级协议）** 和预算之间找平衡。

```python
# 用一个简单模型理解：请求量波动时，固定容量 vs 自动扩缩容
import random

requests = [random.randint(50, 500) for _ in range(12)]  # 12 个时间片的请求量
fixed_capacity = 300  # 固定容量：最多处理 300 请求

def autoscale_capacity(req, min_cap=100, max_cap=500, per_instance=100):
    # 每个实例处理 100 请求，向上取整，再限制在 min/max 之间
    needed = (req + per_instance - 1) // per_instance * per_instance
    return max(min_cap, min(max_cap, needed))

for t, req in enumerate(requests, 1):
    fixed_ok = req <= fixed_capacity
    auto_cap = autoscale_capacity(req)
    auto_ok = req <= auto_cap
    print(f"时间片{t}: 请求{req}, 固定容量{'够' if fixed_ok else '不够'}, 自动容量{auto_cap} {'够' if auto_ok else '不够'}")
```

---

## 第 2 节：扩缩容的两个方向与三类指标

自动扩缩容按方向分：

- **水平扩缩容（Horizontal Scaling / Scale Out & In）**：增加或减少实例数量。比如从 3 台虚拟机变成 10 台。
- **垂直扩缩容（Vertical Scaling / Scale Up & Down）**：增强或减弱单台机器配置。比如把 4 核 8G 换成 16 核 64G。

云原生场景里，**水平扩缩容**更常见，因为它更弹性、更容易自动化。

触发扩缩容的常见指标有三类：

1. **资源指标（Resource Metrics）**：CPU 使用率、内存使用率。
2. **业务指标（Business Metrics）**：每秒请求数 QPS、队列长度、响应时间。
3. **时间指标（Schedule Metrics）**：按计划扩容，比如每天上午 9 点提前扩容。

关键结论：**CPU 适合做兜底指标，业务指标更适合做精准扩容**。

```python
# 根据 CPU 和 QPS 两个指标决定是否扩容
def decide_scale(cpu_percent, qps, current_instances):
    target_cpu = 60
    target_qps_per_instance = 100

    # 方法1：按 CPU 计算期望实例数
    cpu_desired = current_instances * cpu_percent / target_cpu
    # 方法2：按 QPS 计算期望实例数
    qps_desired = qps / target_qps_per_instance

    # 取两者较大值，保证两种压力都能覆盖
    desired = max(cpu_desired, qps_desired)
    return max(1, int(desired + 0.999))  # 向上取整

print(decide_scale(cpu_percent=85, qps=1200, current_instances=4))
print(decide_scale(cpu_percent=20, qps=150, current_instances=4))
```

---

## 第 3 节：自动扩缩容的控制循环

自动扩缩容系统本质上是一个**控制循环（Control Loop）**，一般包含四步：

1. **采集（Collect）**：定期获取指标，比如每 15 秒一次。
2. **评估（Evaluate）**：判断当前指标是否超过阈值或目标值。
3. **决策（Decide）**：计算期望实例数。
4. **执行（Act）**：调用云 API 增加或减少实例。

这个过程会不断重复。工程上最重要的三个参数是：

- **冷却时间（Cooldown）**：扩容或缩容后等待一段时间再评估，避免抖动。
- **最小实例数（Min Instances）**：保证基础可用性。
- **最大实例数（Max Instances）**：防止成本失控。

关键结论：**没有冷却时间和上下限的自动扩缩容，很容易变成“反复横跳”的灾难**。

```python
# 模拟一个带冷却时间的自动扩缩容控制循环
import time

class Autoscaler:
    def __init__(self, min_instances=1, max_instances=10, target_cpu=60, cooldown_seconds=30):
        self.min_instances = min_instances
        self.max_instances = max_instances
        self.target_cpu = target_cpu
        self.cooldown_seconds = cooldown_seconds
        self.current_instances = min_instances
        self.last_scale_time = 0

    def evaluate(self, cpu_percent, now):
        if now - self.last_scale_time < self.cooldown_seconds:
            return f"冷却中，保持 {self.current_instances} 台"

        desired = self.current_instances * cpu_percent / self.target_cpu
        desired = int(desired + 0.999)
        desired = max(self.min_instances, min(self.max_instances, desired))

        if desired != self.current_instances:
            old = self.current_instances
            self.current_instances = desired
            self.last_scale_time = now
            return f"从 {old} 台调整为 {desired} 台"
        return f"保持不变：{self.current_instances} 台"

autoscaler = Autoscaler(min_instances=2, max_instances=8, target_cpu=50, cooldown_seconds=10)
print(autoscaler.evaluate(cpu_percent=90, now=0))
print(autoscaler.evaluate(cpu_percent=90, now=5))
print(autoscaler.evaluate(cpu_percent=90, now=15))
print(autoscaler.evaluate(cpu_percent=10, now=30))
```

---

## 第 4 节：常见扩缩容策略

### 4.1 目标追踪（Target Tracking）

设定一个目标值，比如“平均 CPU 保持在 50%”。系统自动计算需要多少实例。这是最常用、最容易上手的策略。

### 4.2 步进扩缩容（Step Scaling）

根据指标超出阈值的程度，分阶段调整。比如 CPU 超过 70% 加 2 台，超过 90% 加 5 台。

### 4.3 计划扩缩容（Scheduled Scaling）

按时间表执行。比如每天 8:55 扩容到 10 台，22:00 缩容到 2 台。

### 4.4 预测式扩缩容（Predictive Scaling）

用机器学习预测未来负载，提前扩容。适合有明显周期性的业务。

关键结论：**工程上通常组合使用：计划扩缩容兜底大促，目标追踪处理日常波动，步进扩缩容应对突发流量**。

```python
# 三种策略的简单组合示例
def combined_scaling(current_instances, cpu_percent, hour, is_flash_sale=False):
    # 1. 计划扩缩容：每天 9 点前至少 5 台
    if 8 <= hour < 22:
        planned_min = 5
    else:
        planned_min = 2

    # 2. 目标追踪：CPU 目标 50%
    target_desired = int(current_instances * cpu_percent / 50 + 0.999)

    # 3. 步进扩缩容：突发流量额外加机器
    step_extra = 0
    if is_flash_sale:
        step_extra = 5 if cpu_percent > 80 else 2

    desired = max(planned_min, target_desired + step_extra)
    return max(1, min(20, desired))

print(combined_scaling(current_instances=4, cpu_percent=75, hour=10, is_flash_sale=True))
print(combined_scaling(current_instances=4, cpu_percent=20, hour=23, is_flash_sale=False))
```

---

## 第 5 节：工程落地要点与常见误区

### 5.1 指标要选对

CPU 有滞后性，QPS 和队列长度往往更敏感。Web 服务常用 QPS + 响应时间；异步任务常用队列积压量。

### 5.2 扩容要快，缩容要慢

扩容慢会导致用户受损；缩容快会导致刚缩完又来流量，反复震荡。工程上通常设置 **扩容冷却短、缩容冷却长**。

### 5.3 实例要无状态（Stateless）

自动扩缩容要求实例可以随时创建和销毁。会话、文件、本地缓存要外置到 Redis、对象存储或数据库。

### 5.4 必须有上下限和告警

最小实例数保证可用性，最大实例数防止账单爆炸。同时要对“达到最大实例数”告警。

### 5.5 常见误区

- 只配 CPU 阈值，结果 QPS 暴涨时来不及扩容。
- 没有冷却时间，实例数反复横跳。
- 缩容太激进，流量回升时服务已经不可用。
- 忽略启动时间，扩容出来的实例还没准备好就被打挂。
- 没有压测，阈值全靠猜。

```python
# 一个更接近工程实践的扩缩容判断：扩容快、缩容慢，且带上下限
def safe_autoscale(current, cpu, last_scale_direction, minutes_since_last_scale):
    min_instances, max_instances = 2, 20
    scale_out_cooldown, scale_in_cooldown = 2, 10

    desired = int(current * cpu / 50 + 0.999)
    desired = max(min_instances, min(max_instances, desired))

    if desired > current:
        if minutes_since_last_scale < scale_out_cooldown and last_scale_direction == "out":
            return current, "扩容冷却中"
        return desired, "扩容"
    elif desired < current:
        if minutes_since_last_scale < scale_in_cooldown and last_scale_direction == "in":
            return current, "缩容冷却中"
        return desired, "缩容"
    return current, "不变"

print(safe_autoscale(current=5, cpu=90, last_scale_direction="out", minutes_since_last_scale=1))
print(safe_autoscale(current=5, cpu=90, last_scale_direction="out", minutes_since_last_scale=5))
print(safe_autoscale(current=8, cpu=20, last_scale_direction="in", minutes_since_last_scale=3))
print(safe_autoscale(current=8, cpu=20, last_scale_direction="in", minutes_since_last_scale=15))
```

---

## 动手练习

**任务：实现一个迷你自动扩缩容模拟器**

要求：

1. 模拟 24 个小时，每小时一个请求量，请求量有白天高、夜间低的规律，并随机加入突发峰值。
2. 实现一个 `Autoscaler` 类，包含：最小实例数、最大实例数、目标 CPU、扩容冷却、缩容冷却。
3. 假设每个实例处理 100 QPS 时 CPU 达到 100%，根据请求量反推 CPU 使用率。
4. 每小时调用一次扩缩容决策，记录实例数变化。
5. 最后输出：总实例小时数、发生扩容次数、发生缩容次数、是否出现请求量超过容量的情况。

提示：

- 请求量超过容量时，记录一次“过载”。
- 比较“固定 5 台”与“自动扩缩容”的总成本和过载次数。
- 尝试调整目标 CPU 和冷却时间，观察结果变化。

```python
import random

class Autoscaler:
    def __init__(self, min_instances=2, max_instances=20, target_cpu=50,
                 scale_out_cooldown=1, scale_in_cooldown=3, per_instance_qps=100):
        self.min_instances = min_instances
        self.max_instances = max_instances
        self.target_cpu = target_cpu
        self.scale_out_cooldown = scale_out_cooldown
        self.scale_in_cooldown = scale_in_cooldown
        self.per_instance_qps = per_instance_qps
        self.current = min_instances
        self.last_scale_hour = -999
        self.last_direction = None

    def cpu_from_qps(self, qps):
        capacity = self.current * self.per_instance_qps
        return min(100.0, qps / capacity * 100)

    def decide(self, qps, hour):
        cpu = self.cpu_from_qps(qps)
        desired = int(self.current * cpu / self.target_cpu + 0.999)
        desired = max(self.min_instances, min(self.max_instances, desired))

        hours_since = hour - self.last_scale_hour

        if desired > self.current:
            if self.last_direction == "out" and hours_since < self.scale_out_cooldown:
                return self.current, cpu, "扩容冷却"
            self.last_scale_hour = hour
            self.last_direction = "out"
            self.current = desired
            return desired, cpu, "扩容"
        elif desired < self.current:
            if self.last_direction == "in" and hours_since < self.scale_in_cooldown:
                return self.current, cpu, "缩容冷却"
            self.last_scale_hour = hour
            self.last_direction = "in"
            self.current = desired
            return desired, cpu, "缩容"
        return self.current, cpu, "不变"


def generate_qps():
    qps = []
    for hour in range(24):
        base = 200 if 9 <= hour <= 21 else 50
        spike = random.choice([0, 0, 0, 300]) if 10 <= hour <= 20 else 0
        qps.append(base + spike + random.randint(-20, 20))
    return [max(10, q) for q in qps]


def simulate(strategy="auto"):
    qps_list = generate_qps()
    autoscaler = Autoscaler()
    total_instance_hours = 0
    overload_count = 0
    scale_out = scale_in = 0

    for hour, qps in enumerate(qps_list):
        if strategy == "fixed":
            instances = 5
            cpu = min(100.0, qps / (instances * 100) * 100)
            action = "固定"
        else:
            instances, cpu, action = autoscaler.decide(qps, hour)
            if action == "扩容":
                scale_out += 1
            elif action == "缩容":
                scale_in += 1

        capacity = instances * 100
        if qps > capacity:
            overload_count += 1
        total_instance_hours += instances
        print(f"{hour:02d}:00 QPS={qps:4d} CPU={cpu:5.1f}% 实例={instances:2d} 动作={action}")

    print("\n===== 结果 =====")
    print(f"策略: {strategy}")
    print(f"总实例小时: {total_instance_hours}")
    print(f"扩容次数: {scale_out}, 缩容次数: {scale_in}")
    print(f"过载次数: {overload_count}")


random.seed(42)
simulate("fixed")
print()
simulate("auto")
```


---

## 本课题目

### single_choice · None



- [A] 流量被 Envoy Sidecar 直接丢弃，因为没有 VirtualService 授权
- [B] 流量按默认路由规则转发到 reviews 的 Endpoints，Envoy 仍会应用 mTLS 和遥测
- [C] 流量绕过 Sidecar 直连 Pod，因为未配置 VirtualService 时 Sidecar 不安装
- [D] 流量被转发到 reviews，但 Sidecar 会因找不到路由而返回 503

**参考答案**：1

**解析**：Istio 的默认行为是：没有 VirtualService 时，Sidecar 仍会按照 Kubernetes Service 的 Endpoints 进行最基本的负载均衡转发，同时自动启用 mTLS、遥测和访问日志等能力。选项 A 和 D 混淆了「未授权/无路由」与「无虚拟服务」的差别；选项 C 错误，因为 Sidecar 注入与是否配置 VirtualService 无关。

### single_choice · None



- [A] v1，因为第二条 route 是默认路由，会覆盖第一条
- [B] v2，因为匹配到第一条带 headers 条件的路由规则
- [C] v1 和 v2 各 50%，VirtualService 未指定权重时默认均分
- [D] 请求被拒绝，因为一个 HTTP 路由中不允许出现多个 route 块

**参考答案**：1

**解析**：VirtualService 中的 http 规则按顺序匹配，第一条规则匹配到 end-user=jason 后，请求被路由到 subset: v2，不再继续匹配后面的规则。选项 A 误认为后面的默认路由会覆盖；选项 C 把「未设权重」误解为均分；选项 D 错误，一个 http 路由里可以有多个 route 用于加权或匹配多目标。

### single_choice · None



- [A] 它只影响 VirtualService 中匹配到的请求，未匹配的请求不受影响
- [B] 它为该 DestinationRule 对应服务的所有目标实例指定默认负载均衡策略
- [C] 它会把所有流量强制路由到第一个 Endpoint，忽略其他实例
- [D] 它等价于在 VirtualService 中配置 weight 为 100 的单目标路由

**参考答案**：1

**解析**：DestinationRule 中的 trafficPolicy 为该服务提供默认的流量策略，其中的 loadBalancer 指定负载均衡算法，除非在 subset 或 VirtualService 中覆盖。选项 A 错误，trafficPolicy 影响所有到达该 DestinationRule 对应服务的流量；选项 C 把负载均衡误认为固定目标；选项 D 混淆了负载均衡与权重路由。

### single_choice · None



- [A] 总是匹配 istio-system 命名空间下的 reviews
- [B] VirtualService 所在命名空间下的 reviews
- [C] default 命名空间下的 reviews，与 VirtualService 所在命名空间无关
- [D] 所有命名空间下的 reviews，形成全局路由

**参考答案**：1

**解析**：VirtualService 中未带命名空间限定的 host 默认解析为 VirtualService 自身所在命名空间的服务。选项 A、C 默认了其他命名空间；选项 D 错误，Istio 不会自动对所有命名空间同名服务做全局路由。

### single_choice · None



- [A] 请求仍会被转发，mTLS 只用于加密响应
- [B] 请求会在 Sidecar 层被拒绝，因为严格模式下要求双方都出示有效证书
- [C] 请求会被重定向到 HTTPS 端口，然后由客户端重新发起
- [D] 请求会被记录到遥测中，但不会影响实际转发

**参考答案**：1

**解析**：在严格 mTLS 模式下，Istio 要求通信双方都使用有效的 Istio 证书，未携带证书的请求会在 Sidecar 层被拒绝。选项 A、D 低估了 mTLS 的强制作用；选项 C 错误，Istio 的 mTLS 不是通过 HTTP 重定向实现的。

### single_choice · None



- [A] rewrite:
    uri: /v1/reviews
  
- [B] redirect:
    uri: /v1/reviews
  
- [C] route:
  - destination:
      host: reviews
      port: 8080
  
- [D] fault:
    abort:
      httpStatus: 404
  

**参考答案**：0

**解析**：rewrite.uri 用于在转发前重写请求 URI，而 redirect 是返回重定向响应，不会把请求转发到后端。选项 B 混淆了路由与重定向；选项 C 只是普通路由；选项 D 是故障注入。

### single_choice · None



- [A] 为某个工作负载注入 Sidecar 容器
- [B] 限制某个命名空间或工作负载可以访问哪些外部服务，以缩小配置范围
- [C] 定义网格入口的 TLS 证书
- [D] 设置 mTLS 的认证策略

**参考答案**：1

**解析**：Istio 的 Sidecar 资源用于限定 Sidecar 代理的可见范围，比如只允许某命名空间的工作负载访问指定服务，从而减少不必要的配置分发。选项 A 是注入过程，不是 Sidecar 资源的用途；选项 C 是 Gateway 的职责；选项 D 是 PeerAuthentication 等安全资源的职责。

### single_choice · None



- [A] 给每个 Pod 的容器手动添加 Envoy 镜像
- [B] 给目标命名空间打上 istio-injection=enabled 标签，并重建 Pod
- [C] 在 VirtualService 中添加 sidecarInjection: true 字段
- [D] 修改 Kubernetes Service 的 type 为 LoadBalancer

**参考答案**：1

**解析**：Istio 的自动注入通过命名空间标签 istio-injection=enabled 开启，已存在的 Pod 需要重建才能注入。选项 A 不是 Istio 推荐方式；选项 C 中 VirtualService 没有该字段；选项 D 与 Sidecar 注入无关。

### single_choice · None



- [A] VirtualService 会替代 Kubernetes Service 的 DNS 解析，因此可以删除 Service
- [B] VirtualService 依赖于 Kubernetes Service 提供后端 Endpoints，不能完全替代 Service
- [C] VirtualService 只能路由到同一命名空间下的 Service
- [D] VirtualService 的 host 必须使用 Pod IP，不能用 Service 名称

**参考答案**：1

**解析**：VirtualService 依赖 Kubernetes Service 及其 Endpoints 作为后端目标，不能替代 Service 的注册与 DNS 功能。选项 A 错误；选项 C 错误，通过全限定名可以跨命名空间路由；选项 D 错误，host 通常使用 Service 名称。

### single_choice · None



- [A] 无论请求是否成功，总共最多尝试 3 次
- [B] 仅在响应为 5xx 时触发重试，最多额外尝试 3 次，每次尝试的超时时间为 2 秒
- [C] 每次请求会固定重试 3 次，即使后端返回 200 也会重试
- [D] perTryTimeout 表示整个重试过程的总超时时间为 2 秒

**参考答案**：1

**解析**：retries.attempts 表示在失败条件下允许的重试次数，retryOn 指定触发条件（如 5xx），perTryTimeout 是每次尝试的超时时间。选项 A 忽略了 retryOn；选项 C 误认为总是重试；选项 D 把单次超时误认为总超时。

### single_choice · None



- [A] kube-apiserver 直接导出所有服务网格指标
- [B] 数据面的 Envoy Sidecar 和入口 Gateway 上报遥测数据
- [C] CoreDNS 插件自动生成服务网格指标
- [D] Kubernetes Scheduler 在调度时记录流量指标

**参考答案**：1

**解析**：Istio 的遥测数据由数据面的 Envoy 代理（包括工作负载 Sidecar 和 Gateway）采集并上报，选项 B 正确。选项 A、C、D 分别是 API 服务器、DNS 组件和调度器，它们不负责生成服务网格的流量遥测。

### single_choice · None



- [A] 请求会自动回退到 v1
- [B] 请求会失败，因为 subset v3 没有可用的后端实例
- [C] 请求会绕过 Sidecar 直连 reviews 的任意 Pod
- [D] 请求会被路由到 reviews 的 Kubernetes Service，忽略 subset

**参考答案**：1

**解析**：当 VirtualService 将流量固定到某个 subset，而该 subset 对应的后端实例不存在时，Envoy 找不到可用目标，请求会失败。Istio 不会自动回退到其他版本，也不会绕过 subset 回到普通 Service 负载均衡。

### single_choice · None



- [A] route:  - destination: {host: reviews, subset: v1, weight: 80}  - destination: {host: reviews, subset: v2, weight: 20}
- [B] route:  - destination: {host: reviews, subset: v1, weight: 1}  - destination: {host: reviews, subset: v2, weight: 1}
- [C] route:  - destination: {host: reviews, subset: v1, percent: 80}  - destination: {host: reviews, subset: v2, percent: 20}
- [D] route:  - destination: {host: reviews, subset: v1}  - destination: {host: reviews, subset: v2}

**参考答案**：0

**解析**：Istio 的 DestinationWeight 使用 weight 字段，多个 destination 的 weight 之和应为 100，因此 80/20 是正确的写法。选项 B 会让两个版本各承担约 50%；选项 C 中 percent 不是该字段名；选项 D 未指定权重时，流量会在两个 destination 之间均分或按实现默认比例，不能保证 80/20。

### single_choice · None



- [A] 定义允许访问某个服务的 JWT 签发者
- [B] 设置工作负载之间 mTLS 的认证模式（如 STRICT、PERMISSIVE）
- [C] 配置外部访问入口的 TLS 证书
- [D] 指定 VirtualService 的路由目标

**参考答案**：1

**解析**：PeerAuthentication 用于配置对等认证，即工作负载之间 mTLS 的模式，如 STRICT 或 PERMISSIVE。选项 A 对应 RequestAuthentication 或 AuthorizationPolicy；选项 C 由 Gateway 的 TLS 配置负责；选项 D 属于 VirtualService。

### single_choice · None



- [A] VirtualService 的 hosts 必须写为 productpage.default.svc.cluster.local，不能写短名
- [B] DestinationRule 中必须已经定义了名为 v1 和 v2 的 subset
- [C] 必须先为每个 subset 单独创建一个 Kubernetes Service
- [D] Sidecar 必须配置为对 productpage 不做 mTLS，否则 subset 无法生效

**参考答案**：1

**解析**：VirtualService 在 route 中引用 subset 时，DestinationRule 必须先定义同名 subset，否则该 subset 不会被解析。选项 A 错误，short name 在相同 namespace 下可用；选项 C 错误，subset 是基于标签选择的逻辑分组，不需要为每个 subset 创建独立 Service；选项 D 与 subset 是否生效无关。

### single_choice · None



- [A] 所有请求都延迟 5 秒
- [B] 10% 的请求延迟 5 秒，其余请求正常转发到 ratings
- [C] 所有请求中有 10% 被直接拒绝，其余请求延迟 5 秒
- [D] 只有来自特定来源的请求会被延迟 5 秒

**参考答案**：1

**解析**：percentage.value: 10 表示该故障注入仅对 10% 的请求生效，fixedDelay: 5s 表示注入的是 5 秒延迟，而不是拒绝。选项 A 忽略 percentage；选项 C 把 delay 误认为 abort；选项 D 把 source 匹配条件与 percentage 混淆。

### single_choice · None



- [A] 只有通过 istioctl kube-inject 手动注入才能获得 mTLS 能力，自动注入没有 mTLS
- [B] Sidecar 自动注入依赖于命名空间标签 istio-injection=enabled，以及 Pod 模板上的注解
- [C] Sidecar 注入会修改 Kubernetes Service 的 selector，把流量导向 Envoy 代理
- [D] 没有配置 VirtualService 的命名空间不能启用 Sidecar 自动注入

**参考答案**：1

**解析**：Istio 的自动注入通常通过给命名空间打标签 istio-injection=enabled 启用，同时 Pod 模板可使用注解 sidecar.istio.io/inject 控制是否注入。选项 A 错误，自动注入同样能启用 mTLS；选项 C 错误，注入修改的是 Pod 模板而不是 Service selector；选项 D 错误，自动注入与是否配置 VirtualService 无关。

### single_choice · None



- [A] VirtualService 和 DestinationRule
- [B] Gateway 和 VirtualService
- [C] Sidecar 和 ServiceEntry
- [D] PeerAuthentication 和 RequestAuthentication

**参考答案**：1

**解析**：Istio 的入站流量由 Gateway 监听外部端口，再通过绑定到该 Gateway 的 VirtualService 做 Host/Path 路由，因此 Gateway + VirtualService 是常见组合。选项 A 缺少 Gateway，无法对网格外暴露入口；选项 C 的 Sidecar 用于限制某工作负载可见的服务，ServiceEntry 用于登记外部服务；选项 D 属于安全认证相关资源。

### single_choice · None



- [A] 两个 uri 条件必须同时满足，即请求路径既以 /api 开头又恰好是 /health
- [B] 请求路径只要以 /api 开头或恰好等于 /health，即可匹配这条规则
- [C] 只有 /api 开头且不是 /health 的路径才会匹配，因为第二条是排除条件
- [D] 该写法非法，一个 match 数组里不能同时出现 prefix 和 exact

**参考答案**：1

**解析**：match 数组中的多个 match 条目之间是 OR 关系，同一 match 内不同字段之间是 AND 关系，因此这里表示「前缀 /api」或「精确 /health」。选项 A 将数组内条目误认为 AND；选项 C 把第二条误读为排除；选项 D 错误，同一匹配数组中可以出现不同字段类型。

### single_choice · None



- [A] 仍然被 Envoy 代理，因为 Istio 控制面会自动为所有 Pod 注入代理
- [B] 绕过 Sidecar，按普通 Kubernetes 网络方式直连 Pod
- [C] 被 Gateway 自动接管，即使没有配置 Gateway
- [D] 被 VirtualService 强制劫持，即使没有 Sidecar

**参考答案**：1

**解析**：Sidecar 是 Istio 数据面的实际代理，只有注入了 Sidecar 的工作负载才会经过 Envoy 并享受网格能力；没有 Sidecar 且未以其他方式纳入网格的服务，流量会按 Kubernetes 原生网络直连。选项 A、C、D 都高估了 Istio 控制面的自动接管能力。

### single_choice · None



- [A] NetworkPolicy 和 PodDisruptionBudget
- [B] DestinationRule 和 VirtualService
- [C] Ingress 和 ConfigMap
- [D] ServiceAccount 和 RoleBinding

**参考答案**：1

**解析**：灰度发布需要先用 DestinationRule 定义新版本 subset，再用 VirtualService 按权重或匹配条件分配流量，因此这两个资源是核心。选项 A 属于网络策略与可用性保障；选项 C 的 Ingress 是 Kubernetes 原生资源，ConfigMap 不负责流量分配；选项 D 属于权限控制。

### single_choice · None



- [A] 水平伸缩是增加单台机器的 CPU/内存，垂直伸缩是增加机器数量
- [B] 水平伸缩是增加/减少实例数量，垂直伸缩是调整单个实例的规格
- [C] 水平伸缩和垂直伸缩都必须重启整个集群才能生效
- [D] 水平伸缩只能减少实例，垂直伸缩只能增加实例

**参考答案**：1

**解析**：水平伸缩（scale out/in）改变实例数量，垂直伸缩（scale up/down）改变单实例资源规格。A 把两者定义颠倒；C、D 描述错误。

### single_choice · None



- [A] 过去 30 天的总请求数
- [B] 当前 CPU 平均利用率持续高于阈值
- [C] 实例的创建时间
- [D] 实例所在可用区的名字

**参考答案**：1

**解析**：自动伸缩需要能反映当前负载且可随时间变化的指标，CPU 利用率是典型代表。历史总量、创建时间、可用区名都不能反映实时负载压力。

### single_choice · None



- [A] 实例数量频繁波动，产生抖动
- [B] 实例永远不扩容
- [C] 实例数量永远为 0
- [D] 指标无法采集

**参考答案**：1

**解析**：阈值过低会导致轻微波动就触发动作，配合冷却不足会出现伸缩抖动。

### single_choice · None



- [A] 新扩容的实例必须手动加入负载均衡，伸缩组无法自动注册
- [B] 伸缩组新增实例后通常会自动注册到关联的负载均衡目标组
- [C] 负载均衡会阻止伸缩组扩容
- [D] 负载均衡只支持缩容

**参考答案**：1

**解析**：伸缩组通常与负载均衡目标组关联，新实例自动注册、被移除实例自动注销，从而接收/停止接收流量。

### multi_choice · None



- [A] CPU 利用率
- [B] 内存利用率
- [C] 消息队列积压长度
- [D] 实例的创建者用户名
- [E] 网络吞吐/请求速率

**参考答案**：[0, 1, 2, 4]

**解析**：CPU、内存、队列长度、网络/请求速率都能反映负载，是常见动态伸缩指标。创建者用户名与负载无关。

### multi_choice · None



- [A] 设置合理的冷却时间
- [B] 使用较长时间的指标聚合窗口（如 5 分钟均值）而非瞬时值
- [C] 为扩容和缩容设置不同的、更保守的缩容阈值
- [D] 把阈值设为 0 以便最快响应
- [E] 引入一定的容忍区间/滞后区间（hysteresis）

**参考答案**：[0, 1, 2, 4]

**解析**：冷却时间、较长聚合窗口、非对称阈值、滞后区间都能抑制抖动。阈值为 0 反而会加剧抖动。

### multi_choice · None



- [A] 它保证任何缩容动作后实例数不低于该值
- [B] 它可以设为 0，使系统在无流量时完全缩容
- [C] 它必须大于最大容量，否则伸缩组无法创建
- [D] 它通常用于保障基础可用性
- [E] 它等于期望容量后就不允许再扩容

**参考答案**：[0, 1, 3]

**解析**：最小容量是缩容下限，可设为 0（视平台与业务而定），用于保障基础可用性。它不能大于最大容量，也不等于禁止扩容。

### multi_choice · None



- [A] 单机数据库难以做分片、但可以升级机器规格
- [B] 无状态 Web 服务需要应对突发流量
- [C] 有状态应用改造分布式成本极高，短期只能提升单机配置
- [D] 需要快速、弹性地按秒级增减计算能力

**参考答案**：[0, 2]

**解析**：垂直伸缩适合难以分布式改造、但能升级单机规格的场景。需要快速弹性的无状态服务更适合水平伸缩。

### fill_blank · None



**参考答案**：["冷却", "cooldown", "cooldown period", "冷却期"]

**解析**：该机制即冷却时间（cooldown），用于抑制伸缩抖动。

### fill_blank · None



**参考答案**：["最小", "最小容量", "min", "minimum"]

**解析**：最小容量（min capacity）是缩容下限，保障基础可用性。

### code_reading · None



**参考答案**：实例数量会在每次冷却时间结束、且平均 CPU 持续低于缩容阈值时，逐个减少 1 台，直到降到最小容量 2 为止；因为 desired 每次减 1，并由 max(min_capacity, ...) 保证不低于最小容量。

**解析**：这段逻辑体现“渐进缩容 + 冷却 + 最小容量保护”：每次只减 1 台避免抖动，冷却时间限制频率，min_capacity 兜底防止缩到 0。

### scenario · None



**解析**：主要问题是扩容跟不上瞬时增长：5 分钟冷却使扩容次数受限，新实例还有预热/启动延迟。改进可用定时伸缩提前扩容、缩短冷却/加快扩容步长、提前预热实例、并配合队列或限流保护。

### single_choice · None



- [A] 让新实例启动更快
- [B] 防止在短时间内因指标波动而反复扩容/缩容
- [C] 降低云服务商的计费单价
- [D] 提高单个实例的 CPU 性能

**参考答案**：1

**解析**：冷却时间用于在伸缩动作后等待一段时间再评估下一次动作，避免抖动（flapping）。它与启动速度、计费单价、单实例性能无关。

### single_choice · None



- [A] 期望容量必须始终等于最大容量
- [B] 最小容量不能大于最大容量
- [C] 最大容量可以小于最小容量，系统会自动纠正
- [D] 期望容量必须为 0

**参考答案**：1

**解析**：伸缩组约束通常为 min ≤ desired ≤ max，因此最小容量不能大于最大容量。其他选项描述均不成立。

### single_choice · None



- [A] 流量完全随机、无法预测的突发场景
- [B] 已知每天固定时段流量会上升的规律性场景
- [C] 需要对数据库做冷备份的场景
- [D] 需要修改实例操作系统内核的场景

**参考答案**：1

**解析**：定时伸缩适合可预测的周期性负载变化。完全随机的突发更适合基于指标的动态伸缩。

### single_choice · None



- [A] 实例数量永远不会增加
- [B] 实例数量会不断增加但难以回落，造成资源浪费
- [C] 云平台会自动删除所有实例
- [D] 伸缩组会进入只读状态

**参考答案**：1

**解析**：缺少缩容策略时，负载下降后实例不会自动减少，长期会造成成本浪费。其余选项与事实不符。

### single_choice · None



- [A] 平均值会让所有实例看起来都很忙
- [B] 平均值可能掩盖少数实例过载的情况
- [C] 平均值无法被云平台计算
- [D] 平均值只能用于内存指标

**参考答案**：1

**解析**：平均值会平滑掉个别实例的高负载，可能导致该扩容时未扩容。最大值更能暴露热点实例。

### single_choice · None



- [A] 新实例加入后即可立即承担全部生产流量，无需预热
- [B] 新实例启动后可能需要一段时间加载缓存/建立连接，应避免过早评估其指标
- [C] 预热时间越长，扩容速度越快
- [D] 预热时间只对垂直伸缩有效

**参考答案**：1

**解析**：新实例启动初期指标不稳定，过早纳入评估会导致误判。预热时间用于等待实例进入稳定状态。

### single_choice · None



- [A] 让实例的 CPU 频率更高
- [B] 提高对单个可用区故障的容错能力
- [C] 减少实例的启动时间到 0 秒
- [D] 使伸缩策略不再需要指标

**参考答案**：1

**解析**：跨可用区分布可提升可用性，单区故障时其他区实例仍可服务。其余选项与可用区分布无关。

### single_choice · None



- [A] 缩容消费者实例以减少开销
- [B] 扩容消费者实例以加快消息处理
- [C] 停止向队列发送消息
- [D] 把队列改成文件存储

**参考答案**：1

**解析**：队列积压说明消费能力不足，扩容消费者能提升处理速率。缩容会加剧积压。
