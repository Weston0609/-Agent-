# s8u3l2 模型注册表（Model Registry） / 一堂 40 分钟的 MLOps A/B 测试讲义

> 来源 `content/lessons/s8u3l2.json`

## arch.mlops.model_registry

# 模型注册表（Model Registry）

> **一句话直觉**：模型注册表就像“模型们的 GitHub + 版本仓库 + 说明书”，让训练出来的模型不再散落在个人电脑里，而是能被团队发现、追踪、审批、上线和回滚。

---

## 1. 为什么需要模型注册表？

在机器学习项目里，模型不是只训练一次就结束。你会遇到：

- 今天调了超参数，效果 +0.5%；
- 下周换了数据，效果又变了；
- 线上要回滚到上周版本；
- 同事问你：“这个模型是谁训练的？用了哪份数据？指标是多少？”

如果模型文件叫 `model_final_v2_真的最终版.pkl`，这些问题会非常难回答。

模型注册表（Model Registry）是 MLOps（Machine Learning Operations，机器学习运维）中的核心组件，用来统一管理模型的**版本、元数据、阶段和血统**。

---

## 2. 核心概念：模型版本、阶段与元数据

一个模型注册表通常管理三类信息：

1. **模型版本（Model Version）**：每次训练产生一个新版本，例如 v1、v2、v3。
2. **阶段（Stage）**：模型当前处于什么状态，例如 `Staging`（预发布）、`Production`（生产）、`Archived`（归档）。
3. **元数据（Metadata）**：训练参数、数据集、评估指标、创建人、创建时间、代码提交号等。

可以把它想成一张“模型身份证”：

| 字段 | 示例 |
|---|---|
| 模型名 | iris-classifier |
| 版本 | 3 |
| 阶段 | Production |
| 准确率 | 0.96 |
| 数据集 | iris-v2 |
| 创建人 | alice |

下面用纯 Python 模拟一个最小注册表：

```python
# 一个极简模型注册表：用字典保存模型版本与元数据
registry = {}

def register_model(name, version, stage, metrics, metadata=None):
    """注册一个模型版本"""
    key = f"{name}:{version}"
    registry[key] = {
        "name": name,
        "version": version,
        "stage": stage,
        "metrics": metrics,
        "metadata": metadata or {},
    }
    return key

# 注册两个版本
register_model("iris-clf", 1, "Staging", {"accuracy": 0.91})
register_model("iris-clf", 2, "Production", {"accuracy": 0.96}, {"dataset": "iris-v2"})

print(registry)
```

---

## 3. 模型注册表如何融入 MLOps 流程？

典型流程是：

1. **训练**：产生模型文件和指标。
2. **注册**：把模型登记到注册表，生成新版本。
3. **审批/评估**：模型从 `Staging` 进入 `Production` 前，通常要人工或自动审批。
4. **部署**：推理服务按注册表里 `Production` 阶段的模型加载。
5. **监控与回滚**：发现效果下降时，把旧版本重新设为 `Production`。

下面模拟“上线”和“回滚”：

```python
# 阶段流转：把某个版本推进到 Production，并归档旧版本
def promote_to_production(name, version):
    target_key = f"{name}:{version}"
    for key, info in registry.items():
        if info["name"] == name and info["stage"] == "Production":
            info["stage"] = "Archived"  # 旧生产版本归档
    registry[target_key]["stage"] = "Production"

promote_to_production("iris-clf", 1)  # 回滚到 v1
print({k: v["stage"] for k, v in registry.items()})
```

---

## 4. 工程级注册表通常长什么样？

真实系统里，模型注册表通常由专门平台提供，例如 MLflow Model Registry、Weights & Biases、SageMaker Model Registry、Azure ML Registry 等。它们一般提供：

- REST API / Python SDK：程序化注册和查询；
- 版本对比：指标、参数、图表；
- 权限控制：谁能审批、谁能部署；
- 模型血缘：关联数据集、代码 commit、实验 ID；
- 与 CI/CD（Continuous Integration / Continuous Delivery，持续集成/持续交付）集成。

下面用伪代码展示“按阶段加载生产模型”的工程思路：

```python
# 伪代码：推理服务从注册表加载当前 Production 模型
def load_production_model(name):
    for key, info in registry.items():
        if info["name"] == name and info["stage"] == "Production":
            # 真实系统会从对象存储下载模型文件
            return f"loading model {key} with accuracy={info['metrics']['accuracy']}"
    raise ValueError(f"No production model found for {name}")

print(load_production_model("iris-clf"))
```

---

## 5. 零基础到工程级的关键认知

学完这一节，你至少要记住：

- 模型注册表解决的是**模型资产管理**问题，不是训练算法问题；
- 核心是**版本 + 阶段 + 元数据**；
- 没有注册表，模型就无法可靠地复现、审批、部署和回滚；
- 工程实践中，优先使用成熟平台，而不是自己维护 Excel 或文件夹命名规范。

> 一句话总结：模型注册表让模型从“个人文件”变成“可治理的团队资产”。

```python
import hashlib
import json
from datetime import datetime

# ---------- 最小模型注册表实现 ----------
class SimpleModelRegistry:
    def __init__(self):
        self._store = {}

    def _key(self, name, version):
        return f"{name}:{version}"

    def register(self, name, version, stage, metrics, metadata=None):
        """注册模型版本"""
        key = self._key(name, version)
        record = {
            "name": name,
            "version": version,
            "stage": stage,
            "metrics": metrics,
            "metadata": metadata or {},
            "created_at": datetime.utcnow().isoformat(),
        }
        self._store[key] = record
        return key

    def promote(self, name, version, stage):
        """推进模型阶段；若设为 Production，旧 Production 自动归档"""
        target = self._key(name, version)
        if target not in self._store:
            raise KeyError(f"模型不存在: {target}")
        if stage == "Production":
            for key, info in self._store.items():
                if info["name"] == name and info["stage"] == "Production":
                    info["stage"] = "Archived"
        self._store[target]["stage"] = stage

    def get_production(self, name):
        """获取当前生产模型"""
        for key, info in self._store.items():
            if info["name"] == name and info["stage"] == "Production":
                return key, info
        raise ValueError(f"没有生产模型: {name}")

    def snapshot_hash(self):
        """生成注册表内容哈希，便于审计"""
        raw = json.dumps(self._store, sort_keys=True, default=str).encode()
        return hashlib.sha256(raw).hexdigest()


# ---------- 使用示例 ----------
if __name__ == "__main__":
    reg = SimpleModelRegistry()

    reg.register("iris-clf", 1, "Staging", {"accuracy": 0.91})
    reg.register("iris-clf", 2, "Staging", {"accuracy": 0.96}, {"dataset": "iris-v2"})

    reg.promote("iris-clf", 1, "Production")
    key, info = reg.get_production("iris-clf")
    print("当前生产模型:", key, info["metrics"])

    # 回滚：把 v2 推为 Production，v1 自动归档
    reg.promote("iris-clf", 2, "Production")
    key, info = reg.get_production("iris-clf")
    print("回滚后生产模型:", key, info["metadata"])

    print("注册表哈希:", reg.snapshot_hash()[:16], "...")
```

## arch.mlops.ab_test

# 一堂 40 分钟的 MLOps A/B 测试讲义

## 一句话直觉
A/B 测试（A/B testing）就是让线上真实用户随机分成两组，分别体验新旧两个模型或策略，用数据判断新版本是否真的更好——没有它，模型上线只能靠拍脑袋。

---

## 1. 为什么 MLOps 必须做 A/B 测试

离线指标（offline metric）提升，不等于线上业务指标（online metric）提升。原因包括分布偏移（distribution shift）、反馈回路（feedback loop）、延迟约束（latency constraint）和用户体验差异。A/B 测试是唯一能在生产环境中建立因果关系的工程手段。

**关键结论：** 离线评估回答“模型准不准”，A/B 测试回答“用户满不满意、业务涨不涨”。

```python
# 示例：离线 AUC 提升了，但线上未必更好
# 这只是一个示意，说明离线/线上指标可能背离
import random

# 模拟：离线 AUC 从 0.80 提到 0.82
offline_auc_old = 0.80
offline_auc_new = 0.82

# 模拟：线上转化率反而下降
online_cvr_old = 0.050
online_cvr_new = 0.048

print(f\"离线 AUC: {offline_auc_old} -> {offline_auc_new}\")
print(f\"线上 CVR: {online_cvr_old} -> {online_cvr_new}\")
# 离线提升不代表线上提升，必须做在线实验
```

---

## 2. A/B 测试的核心要素：分流、指标、显著性

要做一次可信的 A/B 测试，至少需要三件事：

1. **随机分流（random assignment）**：确保两组用户在统计上可比，避免辛普森悖论（Simpson's paradox）。
2. **明确指标（metric）**：一个主指标（primary metric）+ 若干护栏指标（guardrail metric）。
3. **显著性检验（significance test）**：判断差异是真实效果还是随机波动。

**关键结论：** 没有随机化，就没有因果；没有预注册指标，就没有可信结论。

```python
# 示例：用哈希做稳定的用户分流
import hashlib

def assign_group(user_id: str, salt: str = \"exp_2025_01\") -> str:
    \"\"\"根据 user_id 稳定分流到 A/B 组，保证同一用户多次请求结果一致。\"\"\"
    key = f\"{salt}:{user_id}\".encode(\"utf-8\")
    h = int(hashlib.md5(key).hexdigest(), 16)
    return \"A\" if h % 100 < 50 else \"B\"

# 同一用户始终进入同一组
print(assign_group(\"user_123\"))
print(assign_group(\"user_123\"))
print(assign_group(\"user_456\"))
```

---

## 3. 最小可运行 A/B 测试：从数据到结论

真实场景中，我们通常会统计两组的转化次数和样本量，然后用双样本比例检验（two-proportion z-test）判断差异是否显著。

**关键结论：** p 值（p-value）小不等于效果大，要同时看置信区间（confidence interval）和业务收益。

```python
# 示例：用 statsmodels 做双样本比例检验
import numpy as np
from statsmodels.stats.proportion import proportions_ztest

# 假设：A 组 10000 人，转化 500；B 组 10000 人，转化 550
conversions = np.array([500, 550])
nobs = np.array([10000, 10000])

z_stat, p_value = proportions_ztest(conversions, nobs)
print(f\"z = {z_stat:.4f}, p = {p_value:.4f}\")

if p_value < 0.05:
    print(\"差异统计显著，B 组可能更好\")
else:
    print(\"差异不显著，不能下结论\")
```

---

## 4. MLOps 中的工程化落地：实验平台与模型切换

在生产环境，A/B 测试通常由实验平台（experimentation platform）支撑，核心包括：

- **配置中心（config center）**：管理实验开关、流量比例、模型版本。
- **特征/模型路由（model routing）**：按分流结果调用不同模型。
- **日志与指标管道（logging & metric pipeline）**：实时收集曝光、转化、延迟。
- **自动回滚（auto rollback）**：护栏指标恶化时自动停止实验。

**关键结论：** 实验平台的目标是让“开实验、看指标、做决策、回滚”变成自助化、可审计的流程。

```python
# 示例：简化的模型路由 + 实验配置
import random

# 实验配置：A 组用旧模型，B 组用新模型，各 50% 流量
EXPERIMENT = {
    \"name\": \"rec_model_v2\",
    \"traffic\": {\"A\": 0.5, \"B\": 0.5},
    \"models\": {\"A\": \"model_v1\", \"B\": \"model_v2\"},
}

def route_model(user_id: str) -> str:
    # 简化：用随机数代替哈希分流，仅用于演示
    group = \"A\" if random.random() < EXPERIMENT[\"traffic\"][\"A\"] else \"B\"
    return EXPERIMENT[\"models\"][group]

for uid in [\"u1\", \"u2\", \"u3\"]:
    print(uid, \"->\", route_model(uid))
```

---

## 5. 从入门到工程级：常见坑与最佳实践

- **样本量不足**：实验前用功效分析（power analysis）估算所需样本。
- **多重比较（multiple comparisons）**：同时看太多指标会假阳性，需校正。
- **网络效应（network effect）**：用户之间互相影响时，随机化单元要调整。
- **新奇效应（novelty effect）**：新模型初期可能虚高，需观察长期指标。
- **指标污染**：日志丢失、延迟、重复上报都会破坏实验。

**关键结论：** A/B 测试是工程 + 统计 + 产品的交叉学科，单靠算法无法保证线上收益。

```python
# 示例：用功效分析估算样本量（简化版）
from statsmodels.stats.power import NormalIndPower
from statsmodels.stats.proportion import proportion_effectsize

# 基线转化率 5%，希望检测到提升到 5.5%
p1, p2 = 0.05, 0.055
effect_size = proportion_effectsize(p2, p1)
power_analysis = NormalIndPower()

# alpha=0.05, power=0.8
n = power_analysis.solve_power(
    effect_size=effect_size, alpha=0.05, power=0.8, ratio=1.0
)
print(f\"每组至少需要样本量: {int(n) + 1}\")
```

---

## 动手练习

**任务：** 在本地实现一个最小的 A/B 测试模拟器。

1. 生成 20000 个用户 ID。
2. 用哈希分流函数把它们稳定分成 A/B 两组（各 50%）。
3. 假设 A 组真实转化率为 5%，B 组为 5.5%，模拟每组的转化结果。
4. 用 `proportions_ztest` 计算 p 值，并输出结论。
5. 改变 B 组真实转化率为 5.1%、5.5%、6.0%，观察 p 值变化，并解释为什么样本量会影响显著性。

**提交要求：** 一个可运行 Python 脚本，输出分流人数、转化率、p 值和结论。


---

## 本课题目

### single_choice · None



- [A] 存储训练数据集的原始副本并做数据版本控制
- [B] 记录模型的版本、阶段（如 Staging/Production）及其元数据，供部署与审计使用
- [C] 替代模型训练框架，直接负责梯度下降与参数更新
- [D] 在推理时承担 GPU 显存分配与算力调度

**参考答案**：1

**解析**：模型注册表用于对已训练的模型进行版本化、阶段管理与元数据（指标、来源、签名等）记录，是部署和审计的枢纽。数据版本由数据管理工具负责，训练由训练框架负责，显存与算力属于运行时/编排职责。

### single_choice · None



- [A] 只把模型权重文件重命名为带日期的新文件名，放在共享盘
- [B] 将模型工件与指标、超参数、数据版本、代码提交等信息一并写入模型注册表
- [C] 把评估指标写进训练日志文件，模型权重保持原文件名不变
- [D] 仅在实验跟踪工具里记录指标，不登记模型工件本身

**参考答案**：1

**解析**：模型注册表的价值在于把模型工件和其上下文（指标、超参、数据/代码版本）关联起来，支持复现与追溯。仅重命名文件或只记录指标都无法满足完整追溯需求。

### single_choice · None



- [A] 版本号必须严格按整数递增，不允许使用语义化版本
- [B] 每个版本对应一次注册的模型工件及其元数据快照，可独立被引用与部署
- [C] 同一模型的所有版本共享同一份权重文件
- [D] 版本一旦创建就不可查询历史记录

**参考答案**：1

**解析**：每个版本是一次注册的模型工件与元数据的快照，可独立引用、比较和部署。版本号格式无强制要求，各版本工件独立，历史记录可查询。

### single_choice · None



- [A] 降低模型训练的计算成本
- [B] 作为单一事实来源，驱动下游部署与运维自动化
- [C] 替代特征存储，统一管理特征
- [D] 自动生成训练数据

**参考答案**：1

**解析**：注册表作为模型交付的单一事实来源，阶段变更可驱动下游部署自动化。它不降低训练成本，也不替代特征存储或生成数据。

### single_choice · None



- [A] 减少模型文件占用的存储空间
- [B] 在出现问题时能够追溯到具体数据，支持复现与合规审计
- [C] 提高模型推理速度
- [D] 自动清洗训练数据

**参考答案**：1

**解析**：记录数据版本是为了建立模型与训练数据的血缘关系，支持复现、问题排查与合规审计。它与存储优化、推理速度或数据清洗无关。

### single_choice · None



- [A] 描述模型的用途、限制、训练数据与评估结果，供使用者判断适用性
- [B] 记录模型文件的 MD5 校验值以校验完整性
- [C] 规定模型推理时的线程数
- [D] 存储模型的二进制权重

**参考答案**：0

**解析**：模型卡片用于说明模型用途、限制、数据与评估等，帮助使用者判断适用性与风险。校验值、线程数或权重存储是其他机制。

### single_choice · None



- [A] 允许任何人随意修改所有模型的阶段
- [B] 通过访问控制与命名空间/项目隔离，并明确模型所有权与阶段变更权限
- [C] 将所有模型都标记为 Production 以便使用
- [D] 禁止记录模型元数据以减少冲突

**参考答案**：1

**解析**：访问控制、项目隔离与明确的所有权及权限能降低误用风险。随意修改阶段、全部标记为 Production 或禁止元数据都会加剧混乱。

### single_choice · None



- [A] 该版本已被删除，无法恢复
- [B] 该版本不再推荐使用，但仍保留记录以备追溯
- [C] 该版本正在生产环境服务流量
- [D] 该版本是当前最佳模型

**参考答案**：1

**解析**：Archived 表示不再推荐使用但保留记录用于追溯，并非删除。生产服务对应 Production，最佳模型通常也由阶段或标签体现。

### single_choice · None



- [A] 模型的推理代码
- [B] 版本与实验运行/代码提交/数据版本的关联元数据
- [C] 模型文件的压缩格式
- [D] 推理服务器的 IP 地址

**参考答案**：1

**解析**：缺少版本与实验运行、代码提交、数据版本等关联元数据时，无法追溯版本来源。推理代码、压缩格式或 IP 地址并非版本溯源的关键。

### single_choice · None



- [A] 自动提升模型精度
- [B] 提供模型版本、审批、阶段变更与血缘的不可篡改或可审计记录
- [C] 替代法务团队出具合规报告
- [D] 加密所有训练数据

**参考答案**：1

**解析**：注册表通过版本、审批、阶段变更与血缘等记录支持审计。它不能提升精度、替代法务或加密数据。

### single_choice · None



- [A] 服务端直接读取训练脚本源码
- [B] 服务端根据注册表中指定版本/阶段的模型工件地址进行拉取或加载
- [C] 服务端必须重新训练模型
- [D] 服务端只能加载本地磁盘上任意文件

**参考答案**：1

**解析**：服务端依据注册表中指定版本或阶段的工件地址拉取/加载模型。读取源码、重训或任意本地文件都不符合注册表驱动的部署方式。

### single_choice · None



- [A] 标签和阶段完全等价，可互换使用
- [B] 阶段通常表达生命周期状态，标签更灵活，可用于分类、环境或自定义标记
- [C] 标签只能表示生产环境
- [D] 阶段只能表示归档状态

**参考答案**：1

**解析**：阶段表达生命周期状态（如 Staging/Production），标签更灵活，可用于分类、环境或其他自定义标记。两者不等价，也非仅限某一种取值。

### single_choice · None



- [A] 删除当前 Production 版本的记录，再重新训练一个新模型
- [B] 通过版本历史与阶段变更记录，将上一版本重新提升为 Production
- [C] 只能通过手动覆盖模型文件来切换，注册表不参与阶段管理
- [D] 必须重新执行全部训练流程，注册表不支持回退

**参考答案**：1

**解析**：注册表维护版本历史与阶段状态，允许将旧版本重新提升为 Production 实现回退。删除记录或重训并非必要，且阶段管理正是注册表的核心能力之一。

### single_choice · None



- [A] 实验跟踪记录训练过程中的参数与指标；注册表管理可部署的模型版本及其生命周期阶段
- [B] 实验跟踪只能记录损失曲线；注册表只能记录准确率
- [C] 两者完全等价，只是名称不同
- [D] 注册表只用于记录实验参数；实验跟踪只用于部署模型

**参考答案**：0

**解析**：实验跟踪侧重记录实验运行的过程性信息（参数、指标、工件），注册表侧重对已选定模型进行版本化与生命周期阶段管理，两者互补但职责不同。

### single_choice · None



- [A] 模型文件在磁盘上的物理存储路径
- [B] 模型在生命周期中所处的状态，供部署流水线据此决定是否上线
- [C] 模型训练时使用的学习率大小
- [D] 模型推理时的批大小（batch size）

**参考答案**：1

**解析**：阶段是模型生命周期的逻辑状态标记，部署流水线可据此自动决定是否将某版本投入服务。它不表示存储路径、学习率或批大小。

### single_choice · None



- [A] 仅记录模型名称和创建时间
- [B] 训练数据版本、代码提交哈希、评估指标、超参数与模型签名
- [C] 仅记录评估指标和模型大小
- [D] 仅记录训练时使用的 GPU 型号

**参考答案**：1

**解析**：可追溯性要求把模型与其训练上下文关联，包括数据版本、代码版本、指标、超参数和输入输出签名等。信息过少无法支持复现与审计。

### single_choice · None



- [A] 确定模型的训练时间长短
- [B] 明确模型推理时输入输出的结构、类型与名称，便于服务端正确调用
- [C] 决定模型使用哪种优化器
- [D] 控制模型在注册表中的访问权限

**参考答案**：1

**解析**：模型签名描述推理接口的输入输出契约（名称、类型、形状等），使部署与服务端能按正确方式调用模型。它与训练时长、优化器或权限无关。

### single_choice · None



- [A] 作为代码仓库的替代品，存放训练脚本源码
- [B] 作为模型交付的枢纽：流水线将训练产物注册为版本，并依据阶段触发部署或审批
- [C] 作为监控系统，实时采集线上推理延迟
- [D] 作为数据标注工具，供标注人员使用

**参考答案**：1

**解析**：注册表是模型交付流水线的枢纽，训练产物在此登记为版本，流水线依据阶段变更触发部署、审批或回滚。它不替代代码仓库，也不负责监控或数据标注。

### single_choice · None



- [A] 为模型版本添加描述和标签
- [B] 将某版本从 Staging 提升为 Production
- [C] 在注册表内直接对模型执行反向传播以更新权重
- [D] 查询某模型的所有历史版本

**参考答案**：2

**解析**：注册表负责版本、元数据和阶段管理，不承担模型训练/反向传播等计算任务。添加描述、阶段提升和版本查询都是其典型功能。

### single_choice · None



- [A] 通过阶段状态与审批记录，使部署流水线只在满足条件时推进
- [B] 通过自动重训模型来替代人工审批
- [C] 通过删除未审批的版本以阻止部署
- [D] 注册表无法支持审批流程，必须依赖外部工单系统

**参考答案**：0

**解析**：注册表可通过阶段状态和审批/变更记录与流水线集成，实现门禁式部署。重训或删除版本并非审批机制，注册表通常也能与外部审批系统协同。

### single_choice · None



- [A] 两组样本量必须完全相等
- [B] 观测到的组间差异相对于随机波动是否足够大
- [C] 实验组绝对数值一定大于对照组
- [D] 实验持续时间越长结论越正确

**参考答案**：1

**解析**：A/B 实验的显著性判断本质是看观测差异是否超出随机波动可解释的范围（如 p 值/置信区间）。样本量相等不是必要条件（不等样本也可检验）；数值大小和时长本身不构成可信依据。

### single_choice · None



- [A] 原假设为真的概率是 3%
- [B] 实验组一定优于对照组
- [C] 在原假设成立的前提下，观测到当前或更极端差异的概率约为 3%
- [D] 结论有 3% 的概率是错的

**参考答案**：2

**解析**：p 值定义是「原假设成立时观测到当前或更极端结果的概率」。它不等于原假设为真的概率，也不等于结论出错概率（那是第二类错误/假发现率的混淆）。

### fill_blank · None



**参考答案**：["power", "功效", "统计功效", "1-beta", "1-β"]

**解析**：统计功效（power）= 1 - β，表示在效应真实存在时正确检测出它的概率，工程上常以 0.8 为目标。

### fill_blank · None



**参考答案**：["α", "alpha", "αlpha"]

**解析**：显著性水平用 α 表示，常用 0.05，它约束第一类错误（假阳性）的概率上限。

### code_reading · None



**参考答案**：输出 False。因为 p 值 0.21 大于显著性水平 0.05，不能拒绝原假设，即在当前数据下没有统计证据表明实验组与对照组存在显著差异（可能是样本量太小、效应小或真实无差异）。

**解析**：p 值大于 α 时不拒绝原假设，输出比较结果为 False，结论是不能声称实验组有效。注意不能反向证明「一定没有差异」，只是证据不足。

### code_reading · None



**参考答案**：两次调用结果相同。因为哈希函数对相同输入是确定性的，同一 user 在同一实验下每次都会被稳定分到同一组。加入 experiment_key 是为了让同一用户在不同实验之间相互独立地重新分桶，避免不同实验的分组产生系统性关联。

**解析**：基于确定性哈希的分流保证用户分组稳定（可复现），前缀 experiment_key 使不同实验的分桶相互独立。这是 A/B 分流中常见设计。

### code_reading · None



**参考答案**：95% 置信区间不包含 0，说明在 0.05 显著性水平下该差异在统计上显著，即有证据表明实验组与对照组的转化率存在差异。若区间包含 0，则不能排除「无差异」这一可能。

**解析**：双侧检验中，置信区间是否包含 0 与 p 值是否小于 α 判定一致。区间不含 0 表示在 95% 置信水平上差异「不可能是零」。

### scenario · None



**解析**：第三天很可能样本量不足且存在新奇效应/周期性波动，提前查看并据显著结果决策会显著提升假阳性率（peeking 问题）。应达到预先计算的样本量并跑完计划的实验周期后再判定。

### scenario · None



**解析**：应把转化率与客单价的综合效果（如 GMV/利润）以及护栏指标一起评估，判断 0.5% 转化提升是否能覆盖客单价下降，并结合业务目标做权衡，而不能只看单一显著指标上线。

### scenario · None



**解析**：同时比较多个变体属于多重比较，未做 Bonferroni 或 FDR 等校正会抬高家族错误率，使假阳性概率远超 0.05。建议预先注册假设、减少同时检验的变量、或对 p 值进行多重比较校正。

### single_choice · None



- [A] 可以用来验证分流和统计管线是否无偏，正常情况下不应出现显著差异
- [B] 可以替代 A/B 实验得出业务结论
- [C] 一定会得到显著结果
- [D] 只有在实验失败时才需要做

**参考答案**：0

**解析**：A/A 实验在两组处理相同时应得到无显著差异的结果，用于校验分流、指标口径与统计实现是否正确，是实验平台常见的健康检查手段。

### single_choice · None



- [A] 只看实验前两天的数据
- [B] 根据短期结果立即全量上线
- [C] 尊重预先设定的实验周期，并评估是否需要更长的观察窗口
- [D] 把实验组和对照组反过来重复一次即可

**参考答案**：2

**解析**：留存和自适应类效果需要更长时间才能体现，短期数据可能低估或高估真实影响。应遵循预先设定的周期，必要时延长时间窗观察长期效应。

### single_choice · None



- [A] 实验没有随机分组
- [B] 样本量极大导致极小的差异也被判定为显著
- [C] 对照组数据被删除
- [D] 使用了单尾检验

**参考答案**：1

**解析**：样本量极大时，即使实际效应量极小也容易通过显著性检验。这体现了统计显著与业务显著（实用显著性/最小可检测效应）的区别。

### single_choice · None



- [A] 计算实验的 p 值
- [B] 确定需要的样本量，以有足够把握检测出预期效应
- [C] 决定对照组和实验组的颜色
- [D] 保证实验结果一定显著

**参考答案**：1

**解析**：功效分析用于在给定显著性水平、预期效应量和目标功效（通常 0.8）下估计所需样本量，避免样本不足导致漏检真实效应。它不能保证结果显著。

### single_choice · None



- [A] 只要用户量大就无需随机化
- [B] 分流应保证每个用户被分到各组概率一致，且分组与用户特征独立
- [C] 应该把活跃用户集中分到实验组
- [D] 分流只在实验开始时做一次，之后可以凭经验调整

**参考答案**：1

**解析**：随机化要求分配概率一致且与潜在结果/特征独立，才能让组间差异可归因于处理。按活跃度集中分配或事后调整会引入选择偏差。

### multi_choice · None



- [A] 在实验中途因「看起来显著」就提前停止
- [B] 多重比较未做校正
- [C] 实验组和对照组用户特征分布高度相似
- [D] 样本比例失衡且与分组相关（如某些设备只进实验组）

**参考答案**：[0, 1, 3]

**解析**：提前停止会导致假阳性膨胀；多重比较不校正会提高家族错误率；分组与用户特征相关会引入选择偏差。组间特征相似恰恰是随机化成功的表现，不是陷阱。

### multi_choice · None



- [A] 分流随机且组间可比较
- [B] 样本量足以检测目标效应
- [C] 事先确定了主要指标和停止规则
- [D] 分析时只报告显著的结果

**参考答案**：[0, 1, 2]

**解析**：随机分组、充足样本量、预先注册主要指标与停止规则都是可信结论的基础。只报告显著结果属于发表/选择偏差，会误导结论。

### multi_choice · None



- [A] 第一类错误是原假设为真却拒绝了它（假阳性）
- [B] 第二类错误是效应真实存在却未检测到（假阴性）
- [C] 降低显著性水平 α 通常会增加第二类错误风险
- [D] 增大样本量可以同时减少第一类和第二类错误

**参考答案**：[0, 1, 2, 3]

**解析**：四句均正确。α 越严格越难拒绝原假设，漏检风险上升；样本量增大会同时降低两类错误（在效应固定时提高功效并收紧判定）。

### multi_choice · None



- [A] 页面加载延迟
- [B] 崩溃率
- [C] 核心转化率
- [D] 用户投诉率

**参考答案**：[0, 1, 3]

**解析**：护栏指标用于监控实验是否带来负面影响，如性能、稳定性、体验类指标。核心转化率通常是主要评估指标，而非护栏指标。

### fill_blank · None



**参考答案**：["二", "2", "第二", "II", "type ii", "TypeII"]

**解析**：第二类错误（假阴性）指真实效应存在却未拒绝原假设，与实验功效（1-β）相关。
