# s8u4l1 Kubernetes 入门：从零到工程级 / GPU 调度（GPU Scheduling）入门：从零理解云计算里的“抢显卡”艺术

> 来源 `content/lessons/s8u4l1.json`

## arch.cloud.k8s

# Kubernetes 入门：从零到工程级

> **一句话直觉**：Kubernetes（简称 K8s）就像你训练好模型之后，负责把模型“放进盒子、贴上标签、分发到不同机器、随时扩容、坏了自己重启”的自动化集装箱调度系统——它让 AI 服务在生产环境里跑得稳、扩得快。

前置说明：本讲假定你会写 Python、训练过简单模型（哪怕只是 `y = wx + b`），但**完全没接触过容器和云原生**。学完后你能读懂一份 K8s 配置文件，并在本地用 `kind`/`minikube` 把一个小模型服务跑起来。

---

## 一、为什么需要 Kubernetes：从“跑脚本”到“跑服务”

你本地训练完模型，用 `flask` 或 `FastAPI` 起一个接口，`python app.py` 就跑起来了。但生产环境马上会遇到三个问题：

1. **进程挂了没人管**——机器重启、内存溢出、代码 bug，服务就死了。
2. **流量涨了要扩机器**——双十一来了，1 台机器扛不住，要 10 台；大促结束又要缩回去。
3. **多台机器怎么调度**——10 个服务、20 台机器，谁部署在哪、端口怎么分配、怎么升级不停机？

Kubernetes 把“机器”抽象成**集群（Cluster）**，把“服务”抽象成**Pod**，然后帮你自动完成调度、重启、扩容、滚动升级。

**核心对象（第一次出现附英文）**：

- **Cluster（集群）**：一组机器的集合，分控制面（Control Plane）和工作节点（Worker Node）。
- **Pod**：K8s 最小调度单元，通常包含一个容器（Container），是容器的“外壳”。
- **Deployment（部署）**：描述“我要 3 个 Pod 副本（Replica）跑这个镜像”，负责滚动升级、回滚。
- **Service（服务）**：给一组 Pod 提供一个稳定的虚拟 IP 和 DNS 名，做负载均衡。
- **Namespace（命名空间）**：逻辑隔离，团队/环境（dev、prod）各一个。

---

## 二、用一个 YAML 描述你的模型服务

K8s 的所有对象都用 **YAML（YAML Ain't Markup Language）** 声明。你只写“期望状态（Desired State）”，K8s 负责让它成真——这叫**声明式 API（Declarative API）**。

下面是一个最小可用的 Deployment，把一个假想的模型服务跑 2 个副本：

```yaml
# model-deploy.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: model-server
spec:
  replicas: 2                # 期望 2 个副本
  selector:
    matchLabels:
      app: model-server
  template:                  # Pod 模板
    metadata:
      labels:
        app: model-server
    spec:
      containers:
      - name: server
        image: myrepo/model-server:1.0   # 你的模型镜像
        ports:
        - containerPort: 8000
```

配套一个 Service，让外界能访问：

```yaml
apiVersion: v1
kind: Service
metadata:
  name: model-service
spec:
  selector:
    app: model-server        # 选中上面 Deployment 的 Pod
  ports:
  - port: 80
    targetPort: 8000
  type: ClusterIP             # 集群内部 IP；外网用 LoadBalancer/NodePort
```

用 `kubectl apply -f model-deploy.yaml` 提交，K8s 就开始干活了。

---

## 三、自愈与扩缩容：K8s 帮你干的两件大事

**自愈（Self-healing）**：Pod 挂了，ReplicaSet（Deployment 背后的控制器）发现“实际副本数 < 期望副本数”，立刻起一个新的。你杀掉一个 Pod，几秒后又会自动补齐。

**水平扩缩容（HPA, Horizontal Pod Autoscaler）**：根据 CPU/GPU 或自定义指标自动调整 `replicas`。比如：

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: model-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: model-server
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70   # CPU 平均超 70% 就扩容
```

---

## 四、在本地跑一个 K8s：kind 与 kubectl

没有云账号无所谓，本地也能玩。推荐 **kind（Kubernetes in Docker）**，用 Docker 起一个单节点集群：

```bash
# 安装（macOS 示例，Linux/Windows 类似）
brew install kind kubectl docker

# 创建一个集群
kind create cluster --name demo

# 查看节点
kubectl get nodes
```

然后写一个真正能跑的 Python 示例：我写一个最小的 Flask 服务，模拟“模型推理”，打成镜像，部署到 kind 里，验证能自愈。

**`app.py`**（模拟模型服务）：

```python
# app.py
from flask import Flask, jsonify
import os

app = Flask(__name__)

@app.route("/predict")
def predict():
    # 真实场景这里会加载 PyTorch 模型做推理
    return jsonify({"prediction": 0.87, "pod": os.environ.get("HOSTNAME", "unknown")})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
```

**`Dockerfile`**：

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY app.py .
RUN pip install flask
CMD ["python", "app.py"]
```

**构建并加载到 kind**：

```bash
# 构建镜像（注意镜像名带标签）
docker build -t model-server:1.0 .

# 把镜像直接塞进 kind 集群（本地开发很方便）
kind load docker-image model-server:1.0 --name demo

# 部署（把上面 yaml 中的 image 换成 model-server:1.0，且去掉 imagePullPolicy 或设 IfNotPresent）
kubectl apply -f model-deploy.yaml
kubectl apply -f service.yaml

# 查看状态
kubectl get pods
kubectl get svc
```

到这里你就完成了一次“训练完模型 → 容器化 → 部署到 K8s → 自愈扩容”的闭环。

---

## 五、工程级视角：生产环境的几个必知点

1. **健康检查（Probe）**：`livenessProbe` 判断容器是否要重启，`readinessProbe` 判断是否能接流量。模型服务启动慢，`readinessProbe` 尤其关键。
2. **资源配额（Resource Requests/Limits）**：不写 request，调度器不知道给你留多少资源；不写 limit，一个 Pod 可能把节点打爆。GPU 场景要用 `nvidia.com/gpu`。
3. **配置与密钥（ConfigMap / Secret）**：模型路径、超参放 ConfigMap，API Key、数据库密码放 Secret，不要硬编码进镜像。
4. **持久化存储（PV/PVC）**：模型权重、日志需要挂载卷；大模型建议直接挂对象存储。
5. **滚动更新与回滚（Rolling Update / Rollback）**：`kubectl rollout status` 看进度，`kubectl rollout undo` 一键回滚出事的版本。
6. **可观测性（Observability）**：日志（`kubectl logs`）、指标（Prometheus）、链路（OpenTelemetry）三件套。

> 一句话总结：**K8s = 声明式 + 控制器循环（Control Loop）**。你写期望状态，它不断对比实际状态并修正。理解这个循环，就理解了 K8s 的一切。

## arch.cloud.gpu_scheduling

# GPU 调度（GPU Scheduling）入门：从零理解云计算里的“抢显卡”艺术

> **一句话直觉**：GPU 调度就是让多个程序（任务）公平、高效、不打架地共用同一块或多块 GPU，就像餐厅领位员把有限座位分给不同客人，既要坐满，又不能让谁等太久。

---

## 1. 为什么需要 GPU 调度？

在云计算（Cloud Computing）和 AI 训练中，GPU（Graphics Processing Unit，图形处理器）非常贵、非常少。如果让每个任务独占一块 GPU，很多任务其实用不满，造成浪费；如果随便抢，就会互相干扰甚至崩溃。

**GPU 调度要解决三个核心问题：**

1. **隔离（Isolation）**：任务之间不能互相踩内存、抢算力到死锁。
2. **利用率（Utilization）**：尽量让 GPU 一直在干活。
3. **公平与优先级（Fairness & Priority）**：重要任务先跑，小任务别饿死。

下面用 Python 模拟一个最朴素的调度器，先建立直觉。

```python
# 极简 GPU 调度器：按显存需求排队，能放就放
class SimpleGPUScheduler:
    def __init__(self, total_memory_gb):
        self.total = total_memory_gb
        self.used = 0
        self.running = []

    def submit(self, task):
        name, need = task['name'], task['memory_gb']
        if self.used + need <= self.total:
            self.used += need
            self.running.append(name)
            print(f"[启动] {name} 占用 {need}GB，当前 {self.used}/{self.total}GB")
            return True
        print(f"[等待] {name} 需要 {need}GB，显存不足")
        return False

    def finish(self, name):
        for t in self.running:
            if t == name:
                self.running.remove(name)
                # 这里简化：假设任务释放固定 4GB
                self.used -= 4
                print(f"[完成] {name}，释放后 {self.used}/{self.total}GB")
                return

s = SimpleGPUScheduler(8)
s.submit({'name': '训练A', 'memory_gb': 4})
s.submit({'name': '推理B', 'memory_gb': 3})
s.submit({'name': '训练C', 'memory_gb': 4})
s.finish('训练A')
s.submit({'name': '训练C', 'memory_gb': 4})
```

---

## 2. 调度的三个层次：节点、GPU、进程

GPU 调度不是只看“哪块卡空着”，而是分层的：

- **节点级（Node-level）**：Kubernetes（容器编排系统）决定把 Pod（最小部署单元）放到哪台机器。
- **GPU 级（Device-level）**：一台机器有多块 GPU，选哪块？
- **进程级（Process-level）**：一块 GPU 被多个进程共享时，怎么分时间片或显存？

**关键结论**：越往下层，越依赖硬件和驱动能力，比如 NVIDIA MPS（Multi-Process Service，多进程服务）允许多进程共享一块 GPU 的算力。

```python
# 模拟节点级 + GPU 级调度：先选节点，再选 GPU
nodes = {
    'node-1': [{'id': 0, 'free_mem': 8}, {'id': 1, 'free_mem': 8}],
    'node-2': [{'id': 0, 'free_mem': 16}],
}

def schedule(task_mem):
    # 节点级：找有空闲 GPU 的节点
    for node, gpus in nodes.items():
        for gpu in gpus:
            if gpu['free_mem'] >= task_mem:
                gpu['free_mem'] -= task_mem
                print(f"任务({task_mem}GB) -> {node} / GPU-{gpu['id']}")
                return
    print(f"任务({task_mem}GB) 无法调度：资源不足")

schedule(6)
schedule(6)
schedule(10)
print(nodes)
```

---

## 3. 常见调度策略：先来先服务、最短作业优先、公平共享

没有一种策略适合所有场景。云计算里常组合使用：

- **FIFO（First In First Out，先来先服务）**：简单，但大任务会堵住后面小任务。
- **SJF（Shortest Job First，最短作业优先）**：平均等待时间短，但长任务可能饿死。
- **Fair Sharing（公平共享）**：每个用户/团队轮流用，适合多租户。
- **Bin Packing（装箱）**：把任务尽量塞满 GPU，提高利用率。

**关键结论**：生产系统通常用“优先级 + 公平份额 + 抢占（Preemption）”组合。

```python
import heapq

# 用优先队列模拟：数值越小优先级越高
# 任务格式：(优先级, 任务名, 需要显存)
tasks = [(3, '大训练', 8), (1, '紧急推理', 2), (2, '小实验', 1)]
heapq.heapify(tasks)

gpu_mem = 8
while tasks:
    prio, name, need = heapq.heappop(tasks)
    if need <= gpu_mem:
        gpu_mem -= need
        print(f"调度 {name} (优先级{prio}, {need}GB)，剩余 {gpu_mem}GB")
    else:
        print(f"跳过 {name}：显存不足")
```

---

## 4. 隔离与共享：MIG、MPS、时间片

多任务共用 GPU 时，硬件和驱动提供了不同隔离级别：

- **MIG（Multi-Instance GPU，多实例 GPU）**：把一块 A100/H100 物理切成多个小 GPU，显存和算力硬隔离。
- **MPS（Multi-Process Service）**：多个进程共享同一块 GPU 的算力，适合小任务并行。
- **时间片（Time-slicing）**：CUDA（Compute Unified Device Architecture，统一计算设备架构）上下文切换，简单但可能互相干扰。

**关键结论**：要强隔离选 MIG，要高利用率选 MPS 或时间片，但要接受干扰风险。

```python
# 模拟 MIG 硬隔离：每块物理 GPU 切成固定份额
class MIGGPU:
    def __init__(self, total_mem, instances):
        self.slices = [total_mem // instances] * instances
        self.free = self.slices.copy()

    def alloc(self, idx, mem):
        if self.free[idx] >= mem:
            self.free[idx] -= mem
            print(f"MIG 实例 {idx} 分配 {mem}GB，剩余 {self.free[idx]}GB")
        else:
            print(f"MIG 实例 {idx} 不足，需要 {mem}GB，剩余 {self.free[idx]}GB")

g = MIGGPU(40, 4)  # 40GB 切成 4 份，每份 10GB
g.alloc(0, 8)
g.alloc(0, 8)
g.alloc(1, 5)
```

---

## 5. 工程级视角：Kubernetes + GPU Operator

真实云环境里，GPU 调度通常由 Kubernetes 生态完成：

- **Device Plugin（设备插件）**：把 GPU 注册成 `nvidia.com/gpu` 资源。
- **GPU Operator**：自动安装驱动、容器运行时、监控。
- **调度器扩展**：支持拓扑感知（Topology-aware）、NUMA（Non-Uniform Memory Access，非统一内存访问）亲和。

**关键结论**：你写的 YAML 里一句 `resources.limits: nvidia.com/gpu: 1`，背后是整套调度链路。

```python
# 模拟 K8s 资源声明：Pod 申请 1 块 GPU
pod = {
    'name': 'train-job',
    'resources': {'limits': {'nvidia.com/gpu': 1}},
}
node_gpus = 2
if pod['resources']['limits']['nvidia.com/gpu'] <= node_gpus:
    print(f"Pod {pod['name']} 可调度：节点有 {node_gpus} 块 GPU")
else:
    print(f"Pod {pod['name']} 不可调度：GPU 不足")
```

---

## 动手练习

**任务**：实现一个支持“优先级 + 显存”的 GPU 调度模拟器。

要求：
1. 定义 `Task` 类，包含 `name`、`priority`（越小越优先）、`memory_gb`。
2. 实现 `schedule(tasks, total_memory_gb)` 函数，按优先级排序，能放就放，放不下就跳过并记录。
3. 输出：每个任务的调度结果、最终剩余显存、被跳过的任务列表。
4. 测试数据：
   - 任务：`大训练(prio=3, 8GB)`、`紧急推理(prio=1, 2GB)`、`小实验(prio=2, 1GB)`、`中训练(prio=2, 4GB)`
   - GPU 总显存：8GB
5. 加分：支持任务完成后释放显存，再尝试调度被跳过的任务。

```python
import heapq

class Task:
    def __init__(self, name, priority, memory_gb):
        self.name = name
        self.priority = priority
        self.memory_gb = memory_gb

    def __repr__(self):
        return f"Task({self.name}, prio={self.priority}, mem={self.memory_gb}GB)"

def schedule(tasks, total_memory_gb):
    # 按优先级建堆（priority 越小越优先）
    heap = [(t.priority, t.name, t.memory_gb) for t in tasks]
    heapq.heapify(heap)

    free = total_memory_gb
    running = []
    skipped = []

    while heap:
        prio, name, need = heapq.heappop(heap)
        if need <= free:
            free -= need
            running.append((name, need))
            print(f"[调度] {name} (prio={prio}, {need}GB)，剩余 {free}GB")
        else:
            skipped.append((name, need))
            print(f"[跳过] {name} (prio={prio}, {need}GB)，显存不足")

    return running, skipped, free

if __name__ == '__main__':
    tasks = [
        Task('大训练', 3, 8),
        Task('紧急推理', 1, 2),
        Task('小实验', 2, 1),
        Task('中训练', 2, 4),
    ]
    running, skipped, free = schedule(tasks, 8)
    print('\n最终运行:', running)
    print('被跳过:', skipped)
    print('剩余显存:', free, 'GB')
```


---

## 本课题目

### single_choice · None



- [A] 容器镜像的构建工具，用于把源码打成镜像
- [B] 容器编排平台，用于调度、扩缩和管理容器化应用
- [C] 虚拟机管理程序，用于在一台物理机上运行多个操作系统
- [D] 服务网格数据面，用于拦截所有 Pod 之间的网络流量

**参考答案**：1

**解析**：Kubernetes 是容器编排平台，负责调度、自愈、扩缩和服务发现等；镜像构建通常由 Docker/Buildah 等完成，虚拟机由 Hypervisor 管理，服务网格数据面是 Envoy 等代理的职责。

### single_choice · None



- [A] Pod
- [B] Deployment
- [C] ConfigMap
- [D] Namespace

**参考答案**：1

**解析**：Deployment 管理 ReplicaSet，支持滚动更新、回滚和自愈；裸 Pod 不会自动重建，ConfigMap 用于配置注入，Namespace 用于资源隔离。

### single_choice · None



- [A] 它在每个节点上开放一个端口，外部可通过任意节点 IP 加该端口访问服务
- [B] 它只为集群内部提供访问，外部无法访问
- [C] 它自动申请云厂商的负载均衡器
- [D] 它只能用于七层 HTTP 流量

**参考答案**：0

**解析**：NodePort 在每个节点上开放同一个端口并转发到后端 Pod；ClusterIP 仅集群内可达，LoadBalancer 通常申请云负载均衡器，七层路由由 Ingress 负责。

### single_choice · None



- [A] 镜像拉取失败
- [B] 容器启动命令错误
- [C] 集群中没有节点能满足该 Pod 的 CPU 资源请求
- [D] Service 没有正确配置 selector

**参考答案**：2

**解析**：调度器找不到满足 requests 的节点时，Pod 会一直 Pending；镜像拉取失败通常表现为 ImagePullBackOff，命令错误表现为 CrashLoopBackOff，Service selector 不影响调度。

### single_choice · None



- [A] requests 用于调度决策，limits 用于运行时限制容器可用的 CPU 上限
- [B] requests 用于运行时限制，limits 用于调度决策
- [C] 两者完全等价，只是写法不同
- [D] requests 只能用于内存，limits 只能用于 CPU

**参考答案**：0

**解析**：requests 决定调度器在节点上预留多少资源，limits 决定容器运行时能使用的上限；两者可以分别设置，内存超限通常会导致 OOMKilled。

### single_choice · None



- [A] 直接删除 Deployment 并重新创建
- [B] 查看该 Pod 的日志和 describe 事件，定位容器退出原因
- [C] 修改 Service 的 selector
- [D] 扩容节点数量

**参考答案**：1

**解析**：CrashLoopBackOff 表示容器启动后退出又被反复重启，应先通过 kubectl logs 与 kubectl describe 查看退出码和事件；删除重建通常不能解决根因。

### single_choice · None



- [A] 镜像名称或标签拼写错误
- [B] 私有镜像仓库缺少 imagePullSecret
- [C] 节点无法访问镜像仓库网络
- [D] Pod 的 CPU requests 设置过高

**参考答案**：3

**解析**：ImagePullBackOff 与镜像拉取相关：名称、凭证、网络等都可能导致；CPU requests 过高会导致 Pending，而不是拉取失败。

### single_choice · None



- [A] VerticalPodAutoscaler
- [B] HorizontalPodAutoscaler
- [C] ClusterAutoscaler
- [D] PodDisruptionBudget

**参考答案**：1

**解析**：HPA 根据指标（如 CPU 利用率）调整副本数量；VPA 调整单 Pod 的资源请求，ClusterAutoscaler 调整节点数量，PDB 用于限制自愿中断时的可用副本数。

### single_choice · None



- [A] Namespace 提供一种在集群内对资源进行逻辑隔离和分组的方式
- [B] Namespace 可以隔离网络流量，禁止跨 Namespace 通信
- [C] Namespace 能为其中的 Pod 提供独立的 CPU 和内存配额，无需 ResourceQuota
- [D] Namespace 只能由集群管理员创建，普通用户无法使用

**参考答案**：0

**解析**：Namespace 是逻辑隔离与分组手段，默认不限制跨 Namespace 通信，也不会自动限制资源；资源配额需通过 ResourceQuota/LimitRange 显式设置。

### single_choice · None



- [A] NetworkPolicy
- [B] ResourceQuota
- [C] PodSecurityPolicy
- [D] ServiceAccount

**参考答案**：1

**解析**：ResourceQuota 可对 Namespace 内的资源总量（如 requests.cpu、limits.memory）或对象数量进行限制；NetworkPolicy 控制网络，PodSecurityPolicy/Pod Security Admission 控制安全上下文，ServiceAccount 用于身份。

### single_choice · None



- [A] Ingress
- [B] NetworkPolicy
- [C] Service
- [D] ConfigMap

**参考答案**：1

**解析**：NetworkPolicy 定义 Pod 级别的入站/出站规则，可实现默认拒绝并按标签放行；Ingress 是七层入站路由，Service 是负载均衡抽象，ConfigMap 用于配置。

### single_choice · None



- [A] PVC 是存储资源的声明，PV 是实际存储资源，二者通过绑定关联
- [B] PVC 是节点上的本地磁盘，PV 是云上的对象存储
- [C] PVC 只能由管理员手动创建，PV 由应用自动创建
- [D] PVC 和 PV 是同一个概念的不同叫法

**参考答案**：0

**解析**：PVC 表达用户对存储的需求（容量、访问模式），PV 是集群中实际可用的存储资源，二者通过 StorageClass 动态供给或静态绑定关联；Pod 通过 PVC 使用存储。

### single_choice · None



- [A] Deployment
- [B] StatefulSet
- [C] DaemonSet
- [D] Job

**参考答案**：2

**解析**：DaemonSet 保证每个（符合条件的）节点上运行一个 Pod 副本，常用于日志、监控、网络插件等节点级代理；Deployment 副本数按期望值分布，StatefulSet 用于有状态应用，Job 用于一次性任务。

### single_choice · None



- [A] Deployment
- [B] StatefulSet
- [C] DaemonSet
- [D] CronJob

**参考答案**：1

**解析**：StatefulSet 为每个 Pod 提供稳定的序号、稳定的网络标识和独立的 PVC；Deployment 的 Pod 名称和存储不保证稳定，DaemonSet 面向节点级守护进程，CronJob 面向定时任务。

### single_choice · None



- [A] Pod 是 Kubernetes 中最小的可调度单元，可包含一个或多个共享网络命名空间的容器
- [B] Pod 中的多个容器默认各自拥有独立的 IP 地址，需要 Service 才能互通
- [C] Pod 一旦创建就不可被删除，只能通过重启来更新
- [D] Pod 必须由 Deployment 创建，不能单独创建

**参考答案**：0

**解析**：Pod 是最小调度单元，同一 Pod 内多个容器共享网络命名空间（同一 IP、可通过 localhost 互访）和存储卷；Pod 可以单独创建（如 kubectl run），删除后由控制器决定是否重建。

### single_choice · None



- [A] 对方的 Pod IP
- [B] localhost 或 127.0.0.1
- [C] Service 的 ClusterIP
- [D] 节点的 NodePort

**参考答案**：1

**解析**：同一 Pod 内多个容器共享网络命名空间，因此可以直接通过 localhost 访问彼此端口；Pod IP 也是同一个，但从容器内部通常直接用 localhost 最直观。

### single_choice · None



- [A] 把配置硬编码进容器镜像的 ENTRYPOINT
- [B] 使用 ConfigMap 挂载为卷或环境变量
- [C] 使用 Secret 存储普通文本配置
- [D] 把配置写入节点上的 /etc/hosts

**参考答案**：1

**解析**：ConfigMap 用于存储非敏感配置，可以以卷或环境变量方式注入；Secret 适合敏感数据；硬编码和修改节点文件都不利于可移植与变更管理。

### single_choice · None



- [A] 应用的日志级别
- [B] 数据库连接的用户名和密码
- [C] 前端的静态页面路径
- [D] 服务的监听端口号

**参考答案**：1

**解析**：Secret 用于保存密码、令牌、密钥等敏感信息，默认以 base64 编码存储并可配合加密；其他选项属于普通配置，可用 ConfigMap。

### single_choice · None



- [A] Ingress
- [B] Service
- [C] PersistentVolume
- [D] HorizontalPodAutoscaler

**参考答案**：1

**解析**：Service 为一组 Pod 提供稳定的 ClusterIP/域名并做四层负载均衡；Ingress 提供七层 HTTP 路由（通常仍需 Service 作为后端），PV 是存储资源，HPA 负责扩缩。

### single_choice · None



- [A] ClusterIP Service
- [B] NodePort Service
- [C] Ingress
- [D] NetworkPolicy

**参考答案**：2

**解析**：Ingress 定义基于主机名和路径的七层路由规则；ClusterIP 仅集群内可达，NodePort 在节点端口暴露四层服务，NetworkPolicy 用于 Pod 间访问控制。

### single_choice · None



- [A] 任务被拆分到两个节点上，各用 2 张 GPU，正常启动
- [B] 任务一直处于 pending 状态，无法获得满足条件的资源
- [C] 任务自动降级为使用 2 张 GPU 运行
- [D] 调度器会自动扩容节点以满足请求

**参考答案**：1

**解析**：当调度器要求任务的所有资源在单一节点上满足（如 GPU 亲和/拓扑约束），而任何单节点都无法提供 4 张 GPU 时，任务无法被放置，会持续 pending。除非有 gang scheduling 或跨节点组合机制，否则不会自动拆分或降级。

### single_choice · None



- [A] 它只关心 GPU 的数量，不关心 GPU 之间的连接方式
- [B] 它关注 GPU 之间以及 GPU 与 CPU/NIC 之间的连接带宽与延迟，以决定放置位置
- [C] 它要求所有任务必须使用全部 GPU
- [D] 它只在任务运行结束后才生效

**参考答案**：1

**解析**：拓扑感知调度关注 GPU 间（如 NVLink/NVSwitch）以及 GPU 与 CPU、网卡之间的连接关系，目标是让通信密集的任务获得高带宽、低延迟的放置。它并不只是数量匹配。

### single_choice · None



- [A] 节点上 GPU 的数量与型号
- [B] GPU 的当前使用率与显存占用
- [C] 节点上运行的 Python 进程的源代码内容
- [D] 节点与节点之间的网络带宽

**参考答案**：2

**解析**：调度器需要硬件资源、使用状态、网络拓扑等信息来决策，但不需要也不应获取用户进程的源代码内容。

### single_choice · None



- [A] 亲和性表示任务必须使用 GPU，不能使用 CPU
- [B] 亲和性表示任务对 GPU 的放置位置有偏好或约束，例如尽量使用同一节点或同一 NUMA 域
- [C] 亲和性表示任务只能使用一张 GPU
- [D] 亲和性只在任务失败后生效

**参考答案**：1

**解析**：GPU 亲和性是对放置位置的偏好/约束，如尽量同节点、同 NUMA、同 NVLink 域，以提升性能。它与任务是否使用 CPU 无关。

### multi_choice · None



- [A] 任务请求的 GPU 数量与型号
- [B] GPU 之间的互联拓扑（如 NVLink）
- [C] 任务的优先级与抢占策略
- [D] 任务作者的姓名
- [E] 集群的公平性与配额

**参考答案**：[0, 1, 2, 4]

**解析**：调度需要考虑资源请求、拓扑、优先级/抢占、公平性与配额等。任务作者姓名与调度决策无关。

### multi_choice · None



- [A] 采用装箱（bin-packing）策略，把任务集中到尽量少的节点
- [B] 引入 gang scheduling 保证整组任务原子分配
- [C] 允许 GPU 共享与细粒度切分
- [D] 让所有任务随机分配到任意节点，不做整理
- [E] 支持资源回收与重调度

**参考答案**：[0, 1, 2, 4]

**解析**：装箱减少分散、gang scheduling 保证整组可获得、共享与切分提高利用率、回收与重调度整理资源，都有助于缓解碎片。随机分配通常加剧碎片。

### multi_choice · None



- [A] 抢占可以释放资源给更高优先级的任务
- [B] 抢占一定不会影响被抢占任务的进度
- [C] 被抢占任务通常需要保存检查点或重新排队
- [D] 抢占策略需要考虑公平性和饥饿问题

**参考答案**：[0, 2, 3]

**解析**：抢占用于让高优先级任务获得资源；被抢占任务通常需要检查点或重新排队，因此会影响进度；设计时需考虑公平与饥饿。选项 B 说「一定不会影响」是错误的。

### multi_choice · None



- [A] 按团队设置 GPU 配额
- [B] 使用加权公平队列或份额制
- [C] 允许任意用户无限占用所有 GPU
- [D] 对长时间占用不释放的任务进行限制或回收

**参考答案**：[0, 1, 3]

**解析**：配额、加权公平、对长期占用进行限制都有助于公平。允许任意用户无限占用会破坏公平性，不是公平机制。

### fill_blank · None



**参考答案**：["gang scheduling", "gang", "成组调度", "帮派调度"]

**解析**：gang scheduling（成组调度）保证一组任务原子性地获得资源，全部启动或都不启动，避免部分启动导致的死锁。

### fill_blank · None



**参考答案**：["负载均衡", "load balancing", "均衡负载", "平衡负载"]

**解析**：优先选择空闲节点是为了让各节点负载尽量均衡，属于负载均衡策略。

### code_reading · None



**参考答案**：任务会一直处于 pending 状态。因为对每个节点都有 task.gpu_request(4) > node.free_gpu(最多2)，条件始终不成立，place 不会执行，只能 pending。

**解析**：该伪代码只在单节点内检查是否满足请求，没有任何跨节点组合逻辑，所以请求量超过单节点容量时永远无法被放置。

### scenario · None



**解析**：排队久但利用率低通常说明资源碎片严重：空闲 GPU 分散，无法满足需要同节点/连续 GPU 的大任务。改进方向包括：采用 gang scheduling 保证整组原子分配；使用装箱策略减少分散；引入 GPU 共享/切分提高利用率；设置配额与抢占保证公平并回收长期占用资源；考虑拓扑感知放置。

### single_choice · None



- [A] 严格保证每个任务都能在指定时间内获得 GPU
- [B] 优先把 GPU 分配给优先级最高的大任务
- [C] 任务可能被抢占或延迟，资源分配不作强保证
- [D] 只允许一个任务使用所有 GPU

**参考答案**：2

**解析**：best-effort 意味着调度器尽力分配资源，但不提供硬性保证，任务可能被抢占、排队或延迟。这与强保证（如预留、配额）相对。

### single_choice · None



- [A] 一块物理 GPU 在任何情况下都不能被多个进程同时使用
- [B] GPU 共享只能通过时间片轮转实现，不能做显存隔离
- [C] GPU 共享可以通过时间分片或显存/计算切分实现，调度器需要跟踪实际使用量
- [D] GPU 共享会使任务无法使用 CUDA

**参考答案**：2

**解析**：GPU 共享可实现方式包括时间分片（如 MPS、时间片轮转）和资源切分（如 MIG、显存配额）。调度器需要跟踪每块 GPU 的实际使用情况才能正确共享。

### single_choice · None



- [A] 永远不抢占，高优先级任务一直等待
- [B] 可以抢占低优先级任务，释放 GPU 后分配给高优先级任务
- [C] 直接杀死所有低优先级任务，无论资源是否够用
- [D] 把高优先级任务也排到队尾

**参考答案**：1

**解析**：抢占式调度允许高优先级任务抢占低优先级任务的资源。合理做法是仅抢占足够满足高优先级任务的资源，而非无差别杀死所有低优先级任务。

### single_choice · None



- [A] 让每个任务单独运行以节省显存
- [B] 保证一组相互依赖的任务要么全部同时启动，要么都不启动，避免死锁和资源浪费
- [C] 只调度 CPU 任务，不调度 GPU 任务
- [D] 让任务按到达顺序串行执行

**参考答案**：1

**解析**：在分布式训练中，多个 worker 需要同时启动才能通信。gang scheduling 保证整组任务原子性地获得资源，避免部分启动导致互相等待而死锁。

### single_choice · None



- [A] 最大化单节点利用率
- [B] 负载均衡
- [C] 最小化任务数量
- [D] 固定绑定到节点 A

**参考答案**：1

**解析**：把新任务优先放到空闲节点是为了均衡各节点负载，避免热点节点过载，属于负载均衡策略。

### single_choice · None



- [A] 配额表示任务必须使用的 GPU 数量
- [B] 配额是对某用户/团队可占用 GPU 总量的上限限制
- [C] 配额一旦设置就不能修改
- [D] 配额只对 CPU 有效，对 GPU 无效

**参考答案**：1

**解析**：配额是资源占用的上限约束，用于多租户场景中限制某用户或团队最多能占用的 GPU 数量，与任务实际请求量是不同概念。

### single_choice · None



- [A] 没有任何影响
- [B] 导致 GPU 利用率统计偏高，其他任务难以共享空闲显存
- [C] 导致任务无法启动
- [D] 导致 GPU 数量变多

**参考答案**：1

**解析**：按声明量统计会高估实际占用，导致显存未被充分利用，其他任务可能因配额或可用量判断而被拒绝，降低整体利用率。区分声明量与实际使用量是共享调度的关键。

### single_choice · None



- [A] 集群中有 8 张空闲 GPU，但分散在 8 个节点上，无法满足一个需要 8 张同节点 GPU 的任务
- [B] 集群中所有 GPU 都被一个任务占用
- [C] 某节点没有安装 GPU 驱动
- [D] 任务使用了比请求更多的 CPU

**参考答案**：0

**解析**：资源碎片指空闲资源被分散在多个位置，单个位置都无法满足需要连续/同机资源的任务，导致总空闲量足够但无法分配。
