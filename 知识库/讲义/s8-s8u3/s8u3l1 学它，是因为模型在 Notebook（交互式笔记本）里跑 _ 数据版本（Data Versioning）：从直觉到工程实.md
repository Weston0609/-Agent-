# s8u3l1 学它，是因为模型在 Notebook（交互式笔记本）里跑 / 数据版本（Data Versioning）：从直觉到工程实践

> 来源 `content/lessons/s8u3l1.json`

## arch.mlops.pipeline

## 一句话直觉
**MLOps Pipeline（机器学习运维流水线）** 就是把“数据 → 训练 → 评估 → 部署 → 监控”这一串本来靠人肉脚本和手动操作完成的步骤，变成一条**可重复、可追踪、可自动化**的流水线。

学它，是因为模型在 Notebook（交互式笔记本）里跑通一次不等于能长期稳定运行；真实工程里，数据会变、模型会老、线上会出错，只有流水线才能让 AI 系统像软件一样持续交付。

---

## 1. 从“脚本”到“流水线”：为什么需要 Pipeline
零基础时，最常见的做法是写几个脚本：`download_data.py`、`train.py`、`evaluate.py`。问题在于：
- 步骤之间靠人工记得先跑哪个；
- 参数散落在代码里，换一次实验要改多处；
- 没有统一记录“这次模型是用哪份数据、哪组参数产出的”。

Pipeline 的核心思想是：把每个步骤定义成**组件（Component）**，由调度器按依赖关系执行。

关键结论：**Pipeline 不是更复杂的脚本，而是把脚本之间的依赖、参数和产物显式声明出来。**

```python
# 用纯 Python 模拟一个最小 pipeline：每一步是一个函数，按顺序执行
def load_data():
    return [1, 2, 3, 4, 5]

def train(data):
    return sum(data) / len(data)  # 假装训练出一个“均值模型”

def evaluate(model, data):
    return model  # 假装评估

# 流水线：显式串联，而不是靠人记住顺序
data = load_data()
model = train(data)
metric = evaluate(model, data)
print("metric:", metric)
```

---

## 2. Pipeline 的四个核心要素
工程级 MLOps Pipeline 通常包含四类对象：
1. **组件（Component）**：一个可独立执行的任务，如数据校验、训练、评估。
2. **产物（Artifact）**：组件产生的文件或对象，如数据集、模型权重、评估报告。
3. **参数（Parameter）**：控制组件行为的配置，如学习率、树深度。
4. **编排（Orchestration）**：决定谁先跑、谁依赖谁，如 Kubeflow Pipelines、Airflow、Metaflow。

关键结论：**组件 + 产物 + 参数 + 编排，四者缺一不可；只写函数不叫工程级 Pipeline。**

```python
# 用字典声明“组件、参数、产物”，这是很多 Pipeline 框架的简化模型
pipeline_spec = {
    "components": {
        "preprocess": {"params": {"test_size": 0.2}, "outputs": ["train_set", "test_set"]},
        "train":      {"params": {"lr": 0.1},          "outputs": ["model"]},
        "evaluate":   {"params": {},                   "outputs": ["metrics"]},
    },
    "edges": [("preprocess", "train"), ("train", "evaluate")],  # 依赖关系
}
print(pipeline_spec["edges"])
```

---

## 3. 可重复性：参数化与版本化
如果 Pipeline 里写死路径和超参数，换一台机器或换一份数据就会失败。工程做法是：
- 所有可变项都做成参数；
- 数据、模型、代码都记录版本；
- 每次运行生成唯一的 **Run ID（运行标识）**，便于回溯。

关键结论：**可重复性 = 参数化 + 版本化 + 运行记录；没有它，Pipeline 只是自动化的幻觉。**

```python
import hashlib, json

# 用哈希模拟“数据版本”：同样内容得到同样 ID
def data_version(rows):
    payload = json.dumps(rows, sort_keys=True).encode()
    return hashlib.md5(payload).hexdigest()[:8]

rows = [{"x": 1, "y": 0}, {"x": 2, "y": 1}]
print("data_version:", data_version(rows))  # 换数据就会变

# 运行记录：把参数和版本绑在一起
run = {"run_id": "run-001", "params": {"lr": 0.1}, "data_version": data_version(rows)}
print(run)
```

---

## 4. 自动化与持续交付：从手动到触发
Pipeline 真正的价值是“自动跑”。常见触发方式：
- 定时触发：每天凌晨重新训练；
- 事件触发：新数据到达、代码合并；
- 条件触发：监控发现模型指标下降，自动重训。

关键结论：**Pipeline 的终点不是训练完，而是把“训练—评估—部署—监控”串成闭环。**

```python
# 用简单条件模拟“监控触发重训”
def should_retrain(current_auc, threshold=0.8):
    return current_auc < threshold

current_auc = 0.75
if should_retrain(current_auc):
    print("触发重训流水线")
else:
    print("模型健康，继续服务")
```

---

## 5. 一个工程级 Pipeline 的骨架
真实系统里，你会用 Kubeflow、Airflow、Metaflow、ZenML 等工具。它们共同的结构是：
- Step 1 数据摄入与校验；
- Step 2 特征工程；
- Step 3 训练；
- Step 4 评估与门槛检查；
- Step 5 注册模型；
- Step 6 部署；
- Step 7 监控与回滚。

关键结论：**Pipeline 是 MLOps 的骨架；没有 Pipeline，模型无法规模化、可审计地交付。**

```python
# 用列表表示工程级流水线的阶段，便于后续替换成真实编排工具
stages = [
    "ingest", "validate", "featurize", "train",
    "evaluate", "register", "deploy", "monitor"
]
for i, s in enumerate(stages, 1):
    print(f"Step {i}: {s}")
```

---

## 动手练习
任务：在本地用纯 Python 写一个最小 MLOps Pipeline。

要求：
1. 定义三个函数：`load_data()`、`train(data, lr)`、`evaluate(model, data)`；
2. 用字典保存参数 `{"lr": 0.1}` 和运行记录 `run_id`；
3. 打印每一步的产物和最终指标；
4. 修改 `lr`，观察输出变化；
5. 额外挑战：给 `load_data()` 加一个 `data_version`，并打印出来。

完成后，你就理解了 Pipeline 的最小闭环：**参数 → 组件 → 产物 → 记录**。

```python
import hashlib, json

# 最小 MLOps Pipeline：参数、组件、产物、运行记录
def load_data():
    return [1, 2, 3, 4, 5]

def train(data, lr):
    # 用 lr 影响“模型”，这里简化为加权平均
    return sum(x * lr for x in data) / len(data)

def evaluate(model, data):
    return abs(model - sum(data) / len(data))

def data_version(rows):
    return hashlib.md5(json.dumps(rows, sort_keys=True).encode()).hexdigest()[:8]

params = {"lr": 0.1}
run_id = "run-001"

data = load_data()
model = train(data, params["lr"])
metric = evaluate(model, data)

print({
    "run_id": run_id,
    "params": params,
    "data_version": data_version(data),
    "model": model,
    "metric": metric,
})
```

## arch.mlops.data_version

# 数据版本（Data Versioning）：从直觉到工程实践

> **一句话直觉**：如果代码有 Git，那数据也该有“Git”——数据版本管理让你在任何时候都能知道“模型当时用的是什么数据”，并能一键复现。

---

## 1. 为什么需要数据版本？

在机器学习（Machine Learning, ML）里，代码只是一小部分，**数据才是模型行为的主要决定因素**。

- 你训练了一个准确率 95% 的模型，三周后想复现，却发现数据被同事覆盖了。
- 你想知道“为什么线上模型变差了”，却无法回溯当时训练用的是哪一版数据。
- 你想做 A/B 实验，但两份数据集的差异没人说得清。

**数据版本（Data Versioning）** 就是给数据打上不可变的“快照 ID”，让每次训练、评估、上线都能精确指向一份确定的数据。

它解决三个工程问题：
1. **可复现（Reproducibility）**：给定版本号，能拿到完全相同的数据。
2. **可追溯（Traceability）**：从模型反查到数据，从数据正查到模型。
3. **可协作（Collaboration）**：多人改数据不互相覆盖，像 Git 分支一样并行。

---

## 2. 数据版本的核心思想：内容寻址

Git 之所以能版本化代码，是因为它用 **内容寻址（Content-Addressable Storage）**：文件内容的哈希（Hash）就是它的 ID。

数据版本工具（如 DVC、LakeFS、Pachyderm）大多沿用这个思路：

- 对文件或分片计算哈希（如 SHA-256）。
- 哈希值作为该数据的唯一标识。
- 元数据（路径、大小、哈希、时间）存进一个轻量“清单（Manifest）”。
- 真正的数据放在对象存储（S3、OSS、MinIO）里，按哈希寻址。

这样做的好处：
- **去重**：相同内容只存一份。
- **不可变**：改内容就换哈希，旧版本永远可查。
- **可校验**：下载后重算哈希，能发现损坏。

---

## 3. 最小可运行实现：自己写一个数据版本器

下面这段代码不依赖任何第三方库，用标准库实现“内容哈希 + 版本清单”，帮你建立直觉。

```python
import hashlib
import json
import os
from pathlib import Path
from datetime import datetime


def file_hash(path: Path) -> str:
    """计算文件的 SHA-256 哈希，作为内容 ID。"""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def snapshot(data_dir: str, manifest_path: str = "manifest.json") -> dict:
    """对目录做一次快照，返回版本清单。"""
    root = Path(data_dir)
    files = sorted(p for p in root.rglob("*") if p.is_file())

    entries = []
    for p in files:
        entries.append({
            "path": str(p.relative_to(root)),
            "size": p.stat().st_size,
            "sha256": file_hash(p),
        })

    # 对整个清单再算一次哈希，作为“数据集版本号”
    payload = json.dumps(entries, sort_keys=True, ensure_ascii=False)
    version_id = hashlib.sha256(payload.encode()).hexdigest()[:12]

    manifest = {
        "version_id": version_id,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "files": entries,
    }
    Path(manifest_path).write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return manifest


if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    Path("data/train.txt").write_text("hello data versioning", encoding="utf-8")
    m = snapshot("data")
    print("版本号:", m["version_id"])
    print("文件数:", len(m["files"]))
```

运行后你会得到一个 `manifest.json`，里面有版本号和每个文件的哈希。改一个字节，版本号就会变——这就是“不可变快照”。

---

## 4. 工程级实践：DVC 与数据血缘

真实项目里，数据可能有几十 GB，直接复制不现实。常用工具是 **DVC（Data Version Control）**，它把大文件存到远端，把 `.dvc` 元数据文件交给 Git 管理。

典型工作流：

```bash
# 1. 初始化
git init && dvc init

# 2. 跟踪数据目录
dvc add data/raw

# 3. 提交元数据（不是数据本身）
git add data/raw.dvc .gitignore
git commit -m "feat: 加入原始数据集 v1"

# 4. 推送到远端存储
dvc remote add -d storage s3://my-bucket/dvcstore
dvc push

# 5. 任何人 clone 后一键还原
git clone <repo> && dvc pull
```

关键概念：
- `.dvc` 文件：记录了数据哈希和路径的“指针”。
- **数据血缘（Data Lineage）**：从原始数据 → 清洗 → 特征 → 训练集的完整链条。DVC 用 `dvc.yaml` 定义流水线（Pipeline），每一步都有输入输出哈希。
- **缓存（Cache）**：`.dvc/cache` 内容寻址存储，天然去重。

这样，模型版本、代码版本、数据版本三者通过 Git 提交 ID 绑定，实现端到端可复现。

---

## 5. 数据版本在 MLOps 中的位置

一个成熟的 **MLOps（Machine Learning Operations）** 系统通常包含：

| 维度 | 工具示例 | 作用 |
|------|---------|------|
| 代码版本 | Git | 追踪代码变更 |
| 数据版本 | DVC / LakeFS / Pachyderm | 追踪数据变更 |
| 模型版本 | MLflow / Weights & Biases | 追踪模型与指标 |
| 实验追踪 | MLflow / W&B | 记录参数、指标、产物 |

**最佳实践**：每次训练产出一个“三元组”——`(code_commit, data_version, model_uri)`，写进模型注册表（Model Registry）。这样线上任何一次预测都能溯源。

---

## 6. 小结

- 数据版本 = 给数据打不可变哈希 ID，让训练可复现、可追溯。
- 核心机制是内容寻址：哈希即身份。
- 小项目可以自己写 manifest，大项目用 DVC/LakeFS。
- 工程上要和 Git、模型注册表联动，形成完整血缘。

**记住一句话**：没有数据版本的 MLOps，等于没有 Git 的软件开发。

```python
import hashlib
import json
import os
from pathlib import Path
from datetime import datetime


def file_hash(path: Path) -> str:
    """计算文件的 SHA-256 哈希，作为内容 ID。"""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def snapshot(data_dir: str, manifest_path: str = "manifest.json") -> dict:
    """对目录做一次快照，返回版本清单。"""
    root = Path(data_dir)
    files = sorted(p for p in root.rglob("*") if p.is_file())

    entries = []
    for p in files:
        entries.append({
            "path": str(p.relative_to(root)),
            "size": p.stat().st_size,
            "sha256": file_hash(p),
        })

    # 对整个清单再算一次哈希，作为“数据集版本号”
    payload = json.dumps(entries, sort_keys=True, ensure_ascii=False)
    version_id = hashlib.sha256(payload.encode()).hexdigest()[:12]

    manifest = {
        "version_id": version_id,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "files": entries,
    }
    Path(manifest_path).write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return manifest


if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    Path("data/train.txt").write_text("hello data versioning", encoding="utf-8")
    m = snapshot("data")
    print("版本号:", m["version_id"])
    print("文件数:", len(m["files"]))

    # ---- 动手练习提示 ----
    # 1. 修改 data/train.txt 的内容，重新运行 snapshot，观察 version_id 变化。
    # 2. 增加一个 data/val.txt，再运行一次，对比 manifest。
    # 3. 尝试用 dvc add data 替代自写脚本，比较两者差异。
```


---

## 本课题目

### single_choice · None



- [A] 流水线只是把脚本换个文件名的说法，功能完全一样
- [B] 流水线把流程拆分为可独立执行、可复用的阶段（如数据准备、训练、评估、部署），并明确阶段间依赖与产物传递
- [C] 流水线一定要求使用 GPU 集群，否则无法运行
- [D] 流水线只能用于深度学习模型，传统机器学习无法使用

**参考答案**：1

**解析**：流水线的核心在于将端到端流程分解为职责清晰、可独立运行与复用的阶段，并显式定义阶段间的依赖关系和产物（artifact）传递方式；它与是否使用 GPU、是否是深度学习无关。其余选项是对流水线的常见误解。

### single_choice · None



- [A] 训练步骤可以随意修改上游代码而无需重新跑数据准备
- [B] 当只想重新训练模型时，可以复用已产出的数据集，跳过耗时的数据准备步骤
- [C] 流水线会自动提升模型精度
- [D] 可以保证数据集永远不会变化

**参考答案**：1

**解析**：阶段化并通过产物传递依赖，使得下游阶段可在上游产物未变化时复用其结果，从而避免重复执行耗时的上游步骤。流水线本身不会提升精度，也不会让上游代码随意修改还跳过重跑（那反而会破坏一致性）。

### single_choice · None



- [A] 训练速度变快
- [B] 线上线下特征分布不一致，导致线上效果明显差于离线评估（训练-服务偏差）
- [C] 模型参数自动变大
- [D] 数据校验阶段会自动修复这种不一致

**参考答案**：1

**解析**：训练与服务特征逻辑不一致会造成训练-服务偏差（training-serving skew），使线上表现与离线评估不符。它不会自动提升速度或被校验阶段自动修复，需要靠共享特征逻辑与一致性检查来避免。

### multi_choice · None



- [A] 记录每次运行使用的代码版本与数据版本
- [B] 记录训练所用的超参数与依赖环境信息
- [C] 产物统一存放在无版本标识的临时目录中
- [D] 为每次流水线运行保留可查询的运行记录与日志

**参考答案**：[0, 1, 3]

**解析**：代码/数据版本、超参数与环境信息、运行记录与日志都是复现与追溯的关键；把产物放在无版本标识的临时目录反而会破坏可追溯性。

### multi_choice · None



- [A] 让每个阶段有清晰的输入、输出与职责，便于独立测试与复用
- [B] 把数据校验与模型评估这类质量关卡独立出来，便于阻断不合格流程
- [C] 把所有逻辑塞进一个阶段，减少阶段数量以提高可维护性
- [D] 为耗时较长的阶段设计可复用其产物的机制，避免重复执行

**参考答案**：[0, 1, 3]

**解析**：清晰职责、独立质量关卡、产物复用都是良好阶段划分的要点；把所有逻辑塞进一个阶段会失去阶段化带来的可测试性与可复用性。

### multi_choice · None



- [A] 质量门可以在早期阶段就暴露问题，降低下游排查成本
- [B] 质量门的阈值应可配置，便于根据不同业务调整严格程度
- [C] 质量门一旦设置就永远不能调整，否则流水线会失效
- [D] 质量门触发阻断时应给出清晰的原因与相关记录，便于定位

**参考答案**：[0, 1, 3]

**解析**：质量门的价值在于尽早暴露问题、阈值可配置、阻断时提供清晰原因与记录；说阈值永远不能调整是对质量门的误解。

### multi_choice · None



- [A] 在线推理服务的延迟与错误率出现异常上升
- [B] 线上输入数据的分布相对训练数据发生明显偏移
- [C] 开发者本地编辑器的主题颜色变化
- [D] 流水线中某个阶段频繁失败或运行时间显著变长

**参考答案**：[0, 1, 3]

**解析**：推理服务指标异常、数据分布漂移、阶段失败或耗时异常都属于流水线监控的范畴；编辑器主题颜色与生产流水线无关。

### fill_blank · None



**参考答案**：["产物", "artifact", "artifacts", "工件"]

**解析**：流水线阶段之间传递的、需要被保存与追溯的输出（如模型文件、数据集、报告）通常称为产物（artifact）。

### fill_blank · None



**参考答案**：["门", "质量门", "gate", "quality gate"]

**解析**：质量门（quality gate）是在流水线中根据预设标准决定是否放行的检查点，用于阻断不合格的数据或模型向下游传播。

### code_reading · None



**参考答案**：评估指标 auc 小于 0.8 时会抛出 PipelineError，导致 deploy(model) 不会被执行，即不达标模型不会被部署。这样设计是为了用质量门阻断不合格模型进入线上，避免其影响线上服务。

**解析**：代码中有两处显式的质量门：数据校验失败和评估不达标都会抛出异常，从而中断后续步骤（部署）。这是流水线中常见的质量门设计，作用是阻止不合格产物向下游传播。

### code_reading · None



**参考答案**：好处是在数据准备产物已存在且未过期时直接复用，避免重复执行耗时的 prepare_data，节省时间与计算资源；这体现了流水线通过产物传递实现阶段结果复用（缓存）的特性，同时用过期检查保证数据不会无限期陈旧。

**解析**：该片段用缓存判断跳过耗时的上游阶段，直接加载已有产物，属于流水线产物复用/缓存的典型做法；过期检查则避免了一直使用陈旧数据的风险。

### scenario · None



**解析**：合理的改造是把流程拆分为职责清晰的阶段，阶段间通过带版本标识的产物传递依赖；下游阶段在上游产物未变化时可复用已有结果，从而避免每次都从头执行（缓解慢）；同时记录代码、数据、参数与产物版本，使结果可追溯与复现（缓解不可复现）。

### single_choice · None



- [A] 只要保存了最终模型文件，就一定可以复现训练过程
- [B] 复现需要记录代码版本、数据版本、运行参数与运行环境，仅靠模型文件通常不够
- [C] 可复现性指的是每次运行都能得到完全相同的随机数
- [D] 可复现性只与硬件有关，与数据和代码无关

**参考答案**：1

**解析**：要复现一次训练结果，需要固定或记录代码版本、数据版本、超参数、依赖环境及随机种子等多种因素；仅保存模型权重无法说明它是如何产生的。随机种子只是其中一环，硬件也只是环境的一部分。

### single_choice · None



- [A] 无条件把新模型直接替换线上模型
- [B] 让流水线在该阈值未达标时阻止部署，并留下评估记录供人工查看
- [C] 删除评估阶段，避免它影响发布速度
- [D] 把评估指标的阈值改成 0，让所有模型都通过

**参考答案**：1

**解析**：流水线中的质量门（quality gate）应在指标不达标时阻断部署，并保留评测结果作为可追溯记录；无条件替换或将阈值改成 0 都会让门禁失去意义。

### single_choice · None



- [A] 产物只保存在某人本地电脑上，谁需要谁去拷贝
- [B] 把产物存到共享的、带版本标识的存储位置，并在阶段间通过引用该位置来传递
- [C] 产物每次运行都用同一个固定文件名覆盖，不保留历史
- [D] 产物不需要记录，反正可以随时重新生成

**参考答案**：1

**解析**：阶段间通过带版本标识的共享存储传递产物，才能保证下游可复现、可追溯和可回滚。本地保存、固定文件名覆盖或不记录都会导致不可复现或覆盖历史。

### single_choice · None



- [A] 让训练阶段自己偷偷忽略缺失值，不告诉任何人
- [B] 在数据校验阶段明确产出校验报告并据此决定是否继续或告警，而不是把问题藏到下游
- [C] 直接删除整个流水线，重新手工处理数据
- [D] 把校验阈值全部关闭，让流程先跑通再说

**参考答案**：1

**解析**：把数据质量检查放在专门的校验阶段并产出报告、触发告警或阻断，能让问题在最早、最易定位的位置暴露。藏到下游会放大排查成本，关闭阈值则让校验形同虚设。

### single_choice · None



- [A] 超参数调优必须写在训练阶段之外，否则流水线无法运行
- [B] 调优可以在流水线中作为训练阶段的一部分或独立阶段，但需要明确其产物（如最优超参数或最优模型）如何传给后续阶段
- [C] 超参数调优会破坏流水线的可复现性，所以流水线中禁止调优
- [D] 调优只有深度学习模型才需要，流水线只支持深度学习

**参考答案**：1

**解析**：调优可以内嵌于训练阶段也可以独立成阶段，关键是其结果要作为明确的产物传递给评估和部署阶段，以保证依赖清晰与可复现。是否使用调优与模型类型、流水线可用性无关。

### single_choice · None



- [A] 删除上一版本的模型以节省存储空间
- [B] 保留并标识上一版本的模型与服务配置，以便在异常时快速切回
- [C] 把部署阶段改成只在有人手动点击时运行，且不记录版本
- [D] 把线上服务的所有日志关闭以减少干扰

**参考答案**：1

**解析**：安全回滚依赖上一版本模型与配置仍然可用且可识别，因此部署前应保留并标注旧版本。删除旧版本、不记录版本或关闭日志都会让回滚与事后排查变得困难。

### single_choice · None



- [A] 流水线只能由人工手动触发，任何自动触发都是不安全的
- [B] 流水线可以由代码提交、定时任务、上游产物更新或人工等多种方式触发，并可根据场景组合使用
- [C] 流水线必须每天固定时间触发，其他方式都不合法
- [D] 只要配置了自动触发，就不需要任何质量检查

**参考答案**：1

**解析**：流水线的触发方式可以多样（提交触发、定时触发、事件触发、手动触发等），具体组合取决于业务需求；自动触发并不排斥质量检查，二者应配合使用。

### single_choice · None



- [A] 两者完全一样，没有任何区别
- [B] 在线推理流水线更关注低延迟与稳定性，离线训练流水线更关注吞吐与可复现，二者关注点不同
- [C] 离线训练流水线必须比在线推理流水线延迟更低
- [D] 在线推理流水线不需要任何监控

**参考答案**：1

**解析**：在线推理面向请求的低延迟、高可用；离线训练面向大批量数据处理、可复现与实验迭代，两者优化目标不同。说二者完全一样或在线不需要监控都是常见误解。

### single_choice · None



- [A] 压缩数据体积以节省存储空间
- [B] 保证任何一次训练结果都能追溯到当时使用的确切数据快照，从而可复现
- [C] 提升模型推理时读取数据的速度
- [D] 对数据进行加密以满足合规要求

**参考答案**：1

**解析**：数据版本化的核心价值是可追溯与可复现：一旦记录下某次训练对应的数据快照，就能在需要时重新训练出可比较的模型。压缩、加速、加密是其他维度的目标，与版本化本身无直接关系。

### single_choice · None



- [A] 继续用 Git，但每次只 clone 最新的浅层提交
- [B] 改用专门的数据版本工具（如基于内容寻址的存储 + 版本引用），仅把指针或元数据纳入 Git
- [C] 把所有图片转成文本再提交
- [D] 给 Git 仓库增加更多内存

**参考答案**：1

**解析**：Git 面向文本源码设计，不适合大体积二进制数据。业界常见做法是把大文件存到对象存储，由内容哈希寻址，Git 中只保留指向具体版本的指针/元数据。浅克隆只是缓解，无法解决根本问题。

### single_choice · None



- [A] 两次训练除数据集版本外，其余配置（代码、超参、随机种子等）应保持一致
- [B] 必须使用不同的机器
- [C] 必须使用不同的编程语言
- [D] 数据集越大越好，无需控制变量

**参考答案**：0

**解析**：要归因于数据差异，就必须控制其他变量，即除数据版本外其余条件尽量一致，否则无法判断差异来源。换机器或语言只会引入更多噪声。

### multi_choice · None



- [A] 为每个数据版本记录内容标识或明确的版本号
- [B] 将数据版本与训练运行、模型产物建立关联
- [C] 允许直接原地修改已发布的数据集而不留任何记录
- [D] 对数据变更保留变更说明与责任人
- [E] 删除所有历史版本以节省空间

**参考答案**：[0, 1, 3]

**解析**：可标识、可关联、可审计（变更说明与责任人）是良好实践；原地修改不留记录和删除全部历史会破坏可复现性与审计能力，属于反模式。

### multi_choice · None



- [A] 唯一性：能唯一区分不同内容的数据
- [B] 稳定性：相同内容始终对应同一标识
- [C] 可关联性：能被训练配置和模型产物引用
- [D] 可变性：随使用者的心情随意更改

**参考答案**：[0, 1, 2]

**解析**：唯一、稳定、可关联是可复现体系的基础。标识可变会破坏追溯，因此不是应具备的特性。

### multi_choice · None



- [A] 评估数据规模与访问模式，决定用对象存储还是分布式文件系统承载
- [B] 明确需要区分「原始数据」与「加工后数据」的版本
- [C] 只关心模型代码版本，数据无所谓
- [D] 规划如何把数据版本写进训练配置文件与实验记录

**参考答案**：[0, 1, 3]

**解析**：存储选型、区分原始与加工数据、纳入配置与实验记录都是落地要点。忽视数据版本会直接破坏可复现性，因此第三个选项不合理。

### fill_blank · None



**参考答案**：["哈希", "hash", "哈希值", "散列值"]

**解析**：内容寻址的核心是对数据内容计算哈希，用哈希值作为标识，从而获得去重与完整性校验能力。

### fill_blank · None



**参考答案**：["数据", "数据集", "data", "dataset"]

**解析**：模型结果由代码、超参和数据共同决定，缺少数据版本就无法复现，因此运行记录必须包含数据版本。

### code_reading · None



**参考答案**：返回值会改变，因为函数对所有文件的实际字节内容做了哈希，内容一变哈希就变。相比只按路径标识，它能感知到内容的修改，避免把已变化的数据误当成同一版本。

**解析**：该函数的标识来源于内容而非名字，因此内容变化会改变标识。路径标识无法感知内容变化，这是内容寻址在数据版本化中的关键优势。

### code_reading · None



**参考答案**：能提供关键线索。配置中记录的数据版本字段把本次训练绑定到一个确定的数据快照，便于回查该版本数据是否被替换或含问题样本，从而把问题定位到数据层面。

**解析**：数据版本写进训练配置后，实验与数据建立可追溯关联，是排查效果异常的重要手段。仅有超参和种子无法解释数据引起的波动。

### scenario · None



**解析**：回答应围绕为数据引入可标识的版本、在训练运行中记录数据版本以支持追溯与复现，并在事故时能回滚到旧版本数据重训来验证因果。

### scenario · None



**解析**：应使用不可变快照或内容标识固定每次使用的数据，用版本标识唯一指代，并记录从原始数据到加工数据的处理步骤（血缘），使模型产物可反查到确切的数据来源与加工链路。

### single_choice · None



- [A] 有了模型版本就不需要数据版本，因为模型已包含全部信息
- [B] 数据版本和模型版本互不相关，各自独立管理即可
- [C] 模型版本应当能关联到其训练所用的数据版本，否则难以复现和排查问题
- [D] 数据版本一旦确定，模型版本就永远不会变化

**参考答案**：2

**解析**：模型是从数据中学习得到的，若不记录训练时用的数据版本，就无法复现结果或定位数据导致的偏差，因此二者应建立关联。其余选项都忽视了可复现性这一关键需求。

### single_choice · None



- [A] 哈希值更短，方便手写
- [B] 相同内容必定得到相同标识，不同内容几乎不会碰撞，天然具备去重与完整性校验能力
- [C] 哈希值可以随意修改，便于迭代
- [D] 哈希不需要计算，节省 CPU

**参考答案**：1

**解析**：内容哈希是对数据内容本身计算得出的，因此同样的内容得到同样的标识，可用于去重和校验数据是否被篡改或损坏。人工编号无法保证内容与标识的对应关系。

### single_choice · None



- [A] 只记在个人笔记本里
- [B] 随每次训练运行的实验记录一起保存，并可从模型产物反查
- [C] 只在数据交付时口头告知
- [D] 不需要记录，反正数据不会变

**参考答案**：1

**解析**：数据版本标识需要与实验/模型产物绑定，才能在事后反查某模型对应哪份数据。仅口头或私人记录无法满足团队协作和审计要求。

### single_choice · None



- [A] 不会有任何问题，路径相同即视为同一版本
- [B] 系统会误认为数据未变，导致用旧标签训练的结论被错误地当成新数据的结果
- [C] 文件路径会被自动更新
- [D] 标注修正会自动同步到所有模型

**参考答案**：1

**解析**：仅依赖路径无法感知内容变化，修正后的数据会被当作同一版本，进而造成复现和对比的混乱。这正是需要按内容或显式版本号管理的原因。

### single_choice · None



- [A] 记录数据的来源、经过的处理步骤以及流向，便于追溯和影响分析
- [B] 把数据按大小排序
- [C] 为数据设置访问密码
- [D] 统计模型参数量

**参考答案**：0

**解析**：数据血缘描述数据从产生到使用的完整链路，包括来源、加工和去向，是排查问题与评估变更影响的重要依据，与排序、加密、参数量无关。

### single_choice · None



- [A] 线上模型效果突然下降，团队能快速定位到是上游某批数据被替换，并回滚到旧版本数据重训
- [B] 数据集越大越好，不需要版本
- [C] 每次都从头采集数据
- [D] 把数据全部删掉重建

**参考答案**：0

**解析**：数据版本化的价值在事故排查与回滚场景中最明显：能迅速确定是数据哪一批次发生了变化并回退。其余选项恰恰是缺乏版本管理的表现。

### single_choice · None



- [A] 快照必须复制全部数据的物理副本，不能引用共享存储
- [B] 快照代表某一时刻的数据状态，可通过引用不可变存储实现而无需全量复制
- [C] 快照只能保存一次，之后不能更新
- [D] 快照与版本化是同一概念，二者完全等同

**参考答案**：1

**解析**：快照是某一时刻数据状态的表示，借助不可变存储或写时复制机制可实现高效快照，不必全量物理复制。快照是版本化的一种实现手段，但两者不完全等同。

### single_choice · None



- [A] 存储与传输成本随版本数快速增长，且冗余严重
- [B] 模型准确率必定下降
- [C] 训练速度必定变慢
- [D] 标签会自动丢失

**参考答案**：0

**解析**：每次全量新版本会导致大量重复数据，存储和传输开销随版本累积而膨胀。采用增量或引用共享的方式可缓解，但并不会直接影响模型准确率或标签本身。
