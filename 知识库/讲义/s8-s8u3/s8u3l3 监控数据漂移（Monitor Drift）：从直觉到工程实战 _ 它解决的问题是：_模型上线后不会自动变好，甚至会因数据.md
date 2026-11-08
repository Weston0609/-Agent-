# s8u3l3 监控数据漂移（Monitor Drift）：从直觉到工程实战 / 它解决的问题是：**模型上线后不会自动变好，甚至会因数据

> 来源 `content/lessons/s8u3l3.json`

## arch.mlops.monitor_drift

# 监控数据漂移（Monitor Drift）：从直觉到工程实战

> **一句话直觉**：模型上线后，世界会变，输入数据分布也会变；如果没人盯着这种“漂移”，模型可能悄悄变差——监控漂移就是给模型装上“体检仪”。

---

## 1. 为什么需要监控数据漂移？

在机器学习运维（MLOps，Machine Learning Operations）中，**数据漂移（Data Drift）** 指模型上线后，线上输入数据的分布与训练数据分布出现显著差异。它不一定立刻导致模型报错，但会让预测准确率（accuracy）慢慢下降。

**核心结论**：模型训练完成不是终点，持续监控输入分布与预测分布，才能及时发现“模型还活着，但已经不准了”。

下面用一段代码模拟训练集与线上新数据的分布差异，并计算简单的漂移指标。

```python
# 示例：用 Python 标准库和 numpy 模拟并检测数据漂移
import numpy as np

# 训练数据：年龄，均值 35，标准差 5
np.random.seed(42)
train_age = np.random.normal(loc=35, scale=5, size=1000)

# 线上新数据：均值漂移到 45（用户群体变老）
prod_age = np.random.normal(loc=45, scale=5, size=1000)

# 用均值差与标准化均值差（类似 Cohen's d）粗略衡量漂移
mean_shift = prod_age.mean() - train_age.mean()
pooled_std = np.sqrt((train_age.std()**2 + prod_age.std()**2) / 2)
cohens_d = mean_shift / pooled_std

print(f"训练均值: {train_age.mean():.2f}, 线上均值: {prod_age.mean():.2f}")
print(f"均值漂移: {mean_shift:.2f}, Cohen's d: {cohens_d:.2f}")
# 输出会显示明显漂移，工程上 Cohen's d > 0.2 就值得关注
```

---

## 2. 漂移的常见类型：数据漂移、概念漂移、标签漂移

- **数据漂移（Data Drift / Covariate Shift）**：输入特征 \(X\) 的分布 \(P(X)\) 变了，但 \(P(Y|X)\) 没变。  
  例：用户年龄整体变大。
- **概念漂移（Concept Drift）**：输入与标签的关系 \(P(Y|X)\) 变了。  
  例：同样的用户行为，过去代表“会购买”，现在代表“不会购买”。
- **标签漂移（Label Drift / Prior Shift）**：标签 \(Y\) 的分布 \(P(Y)\) 变了。  
  例：正样本比例从 5% 涨到 20%。

**核心结论**：不同类型漂移需要不同监控指标；工程上通常同时监控输入特征和输出预测。

```python
# 示例：分别检查输入漂移和标签漂移
import numpy as np

np.random.seed(0)
# 训练集标签：正样本 5%
train_y = np.random.binomial(1, 0.05, 1000)
# 线上标签：正样本 20%
prod_y = np.random.binomial(1, 0.20, 1000)

print(f"训练正样本率: {train_y.mean():.2%}")
print(f"线上正样本率: {prod_y.mean():.2%}")

# 输入特征漂移与标签漂移可以同时发生
```

---

## 3. 常用漂移检测方法：从统计检验到距离度量

工程上最常用的方法有三类：

1. **统计检验（Statistical Test）**：如 KS 检验（Kolmogorov-Smirnov Test）、卡方检验（Chi-square Test）。  
   适合判断两组样本是否来自同一分布。
2. **距离/散度度量（Distance / Divergence）**：如 PSI（Population Stability Index，群体稳定性指标）、KL 散度（Kullback-Leibler Divergence）。  
   适合给漂移一个可解释的数值。
3. **模型判别法（Adversarial Validation）**：训练一个分类器区分“训练数据 vs 线上数据”，如果 AUC 高，说明漂移大。

**核心结论**：PSI 在工业界最常用，因为它简单、可解释、对分箱友好。

```python
# 示例：计算 PSI（Population Stability Index）
import numpy as np

def calculate_psi(expected, actual, buckets=10):
    """计算 PSI，expected 为训练分布，actual 为线上分布"""
    # 用训练数据的分位数做分箱边界
    breakpoints = np.percentile(expected, np.linspace(0, 100, buckets + 1))
    breakpoints[0], breakpoints[-1] = -np.inf, np.inf

    expected_counts = np.histogram(expected, bins=breakpoints)[0] / len(expected)
    actual_counts = np.histogram(actual, bins=breakpoints)[0] / len(actual)

    # 避免 log(0)
    expected_counts = np.clip(expected_counts, 1e-6, None)
    actual_counts = np.clip(actual_counts, 1e-6, None)

    psi = np.sum((actual_counts - expected_counts) * np.log(actual_counts / expected_counts))
    return psi

np.random.seed(42)
train = np.random.normal(35, 5, 1000)
prod = np.random.normal(45, 5, 1000)

psi_value = calculate_psi(train, prod)
print(f"PSI: {psi_value:.3f}")
# 经验规则：PSI < 0.1 稳定；0.1~0.25 需关注；> 0.25 显著漂移
```

---

## 4. 工程落地：监控系统与告警策略

一个可落地的漂移监控系统通常包含：

- **数据采集**：记录线上请求的特征与预测结果。
- **基准分布**：保存训练集或历史窗口的分布作为参照。
- **定时计算**：按小时/天计算 PSI、KS 等指标。
- **告警与回滚**：超过阈值触发告警，必要时回滚模型或重新训练。
- **可视化**：用仪表盘展示趋势，避免只看单点。

**核心结论**：漂移监控不是一次性脚本，而是一个持续运行的管道（pipeline）。

```python
# 示例：一个极简的漂移监控伪代码结构
class DriftMonitor:
    def __init__(self, baseline_data, threshold=0.25):
        self.baseline = baseline_data
        self.threshold = threshold

    def check(self, new_data):
        psi = calculate_psi(self.baseline, new_data)
        if psi > self.threshold:
            return {"status": "ALERT", "psi": psi}
        return {"status": "OK", "psi": psi}

monitor = DriftMonitor(train)
result = monitor.check(prod)
print(result)
```

---

## 5. 与 MLOps 其他环节的关系

漂移监控位于 MLOps 闭环的“监控与反馈”阶段：

- **上游**：模型训练、评估、部署。
- **下游**：触发重新训练（retraining）、模型回滚（rollback）、数据标注（labeling）。
- **配套**：模型性能监控（accuracy、AUC）、系统监控（延迟、吞吐）。

**核心结论**：漂移监控是模型生命周期管理的关键传感器，没有它，MLOps 闭环不完整。

---

## 动手练习

**任务**：在本机创建一个 Python 脚本 `drift_demo.py`，完成以下步骤：

1. 生成两组一维数据：训练集 `N(0, 1)`，线上集 `N(0.5, 1.2)`，各 2000 个样本。
2. 实现 `calculate_psi` 函数，分 10 箱计算 PSI。
3. 分别计算并打印 PSI、均值差、KS 检验的 p 值（可用 `scipy.stats.ks_2samp`）。
4. 根据 PSI 判断是否告警（阈值 0.25），并打印结论。

**提示**：运行 `pip install numpy scipy` 安装依赖。

**进阶**：把训练集换成真实数据集（如 sklearn 的 iris），对每个特征分别计算 PSI，找出漂移最大的特征。

```python
import numpy as np

def calculate_psi(expected, actual, buckets=10):
    """计算 PSI（Population Stability Index）"""
    breakpoints = np.percentile(expected, np.linspace(0, 100, buckets + 1))
    breakpoints[0], breakpoints[-1] = -np.inf, np.inf
    expected_counts = np.histogram(expected, bins=breakpoints)[0] / len(expected)
    actual_counts = np.histogram(actual, bins=breakpoints)[0] / len(actual)
    expected_counts = np.clip(expected_counts, 1e-6, None)
    actual_counts = np.clip(actual_counts, 1e-6, None)
    return np.sum((actual_counts - expected_counts) * np.log(actual_counts / expected_counts))

np.random.seed(42)
train = np.random.normal(35, 5, 1000)
prod = np.random.normal(45, 5, 1000)
psi = calculate_psi(train, prod)
print(f"PSI: {psi:.3f}")
if psi > 0.25:
    print("告警：检测到显著数据漂移")
else:
    print("当前分布稳定")
```

## arch.mlops.feedback_loop

## 一句话直觉
**反馈闭环（Feedback Loop）** 就是让上线后的 AI 模型（AI Model）能持续从真实用户行为里“看到自己做得怎么样”，再把学到的东西回流到数据、训练和部署里——它不是一次性交付，而是一条持续改进的回路。

---

## 1. 什么是 MLOps 里的反馈闭环？

**MLOps（Machine Learning Operations）** 是把机器学习（Machine Learning）从实验推向生产的一整套工程实践。
**反馈闭环（Feedback Loop）** 指的是：

> 模型上线 → 用户产生行为/标注/纠正 → 这些信号被采集、清洗、标注 → 重新训练/评估 → 新模型再上线

它解决的问题是：**模型上线后不会自动变好，甚至会因数据分布变化而变差（Data Drift / Concept Drift）**。

一个最小心智模型是：

```
用户请求 -> 模型预测 -> 用户反馈 -> 数据回流 -> 再训练 -> 新模型上线
   ^                                                        |
   |________________________________________________________|
```

```python
# 最小闭环的抽象：用一个字典模拟“反馈记录”
feedback_log = []

def predict_and_collect(user_input, model_version="v1"):
    # 模拟模型预测：这里用“输入长度”作为假预测
    prediction = len(user_input) % 2  # 0 或 1
    feedback_log.append({
        "input": user_input,
        "prediction": prediction,
        "model_version": model_version,
        "label": None  # 等用户反馈后再填
    })
    return prediction

# 模拟一次线上请求
pred = predict_and_collect("hello world")
print("预测结果:", pred)
print("当前反馈日志:", feedback_log)
```

---

## 2. 反馈信号从哪里来？

常见来源分三类：

1. **显式反馈（Explicit Feedback）**：用户点赞/点踩、评分、纠错。
2. **隐式反馈（Implicit Feedback）**：点击、停留时长、是否购买、是否复制结果。
3. **人工标注（Human Labeling）**：专家抽检、主动学习（Active Learning）挑样本。

关键点：**不是所有反馈都能直接当标签**。隐式反馈往往有噪声，需要定义“代理指标（Proxy Metric）”。

```python
# 模拟三种反馈的采集与聚合
raw_feedbacks = [
    {"type": "explicit", "value": 1},   # 点赞
    {"type": "implicit", "value": 0},   # 未点击
    {"type": "human", "value": 1},      # 人工标注为正确
]

def aggregate_feedback(feedbacks):
    # 简单加权：显式 1.0，隐式 0.5，人工 1.5
    weights = {"explicit": 1.0, "implicit": 0.5, "human": 1.5}
    score = 0.0
    weight_sum = 0.0
    for fb in feedbacks:
        w = weights[fb["type"]]
        score += w * fb["value"]
        weight_sum += w
    return score / weight_sum if weight_sum else 0.0

print("聚合反馈分数:", aggregate_feedback(raw_feedbacks))
```

---

## 3. 闭环的工程结构：数据、训练、部署怎么串？

一个可落地的 MLOps 反馈闭环通常包含：

- **数据采集（Data Collection）**：日志、埋点、消息队列。
- **数据版本化（Data Versioning）**：DVC、LakeFS、Delta Lake。
- **特征存储（Feature Store）**：离线/在线特征一致。
- **训练流水线（Training Pipeline）**：可重复、可调度。
- **模型注册（Model Registry）**：版本、阶段、审批。
- **在线服务（Online Serving）**：A/B 测试、影子模式（Shadow Mode）。
- **监控与告警（Monitoring & Alerting）**：延迟、漂移、业务指标。

核心原则：**闭环不是“自动重训”这么简单，而是“可观测 → 可决策 → 可回滚”**。

```python
# 用纯 Python 模拟一个最小训练流水线：从反馈日志到新模型版本
import random
random.seed(0)

# 1) 收集带标签样本（这里用反馈日志里的 prediction + label）
samples = [
    {"x": 1, "y": 1},
    {"x": 2, "y": 0},
    {"x": 3, "y": 1},
    {"x": 4, "y": 0},
]

# 2) 极简“训练”：找一个阈值，使分类错误最少
best_threshold, best_err = None, 999
def predict(x, threshold):
    return 1 if x >= threshold else 0

for t in [0.5, 1.5, 2.5, 3.5, 4.5]:
    err = sum(predict(s["x"], t) != s["y"] for s in samples)
    if err < best_err:
        best_err, best_threshold = err, t

print(f"新模型阈值={best_threshold}, 错误数={best_err}")

# 3) 模拟注册新版本
model_registry = {"v1": {"threshold": 2.5}, "v2": {"threshold": best_threshold}}
print("模型注册表:", model_registry)
```

---

## 4. 闭环的常见风险：反馈偏差与自激循环

反馈闭环不是“越自动越好”，它有两个经典坑：

1. **反馈偏差（Feedback Bias）**：用户只对部分样本反馈，导致训练数据有偏。
2. **自激循环（Self-Reinforcing Loop）**：模型只推它已经喜欢的，用户也只反馈那些，导致多样性崩塌。

应对思路：
- 保留随机探索（Exploration）、A/B 测试。
- 对反馈做重加权（Reweighting）或逆概率加权（Inverse Propensity Weighting）。
- 设置“黄金数据集（Golden Dataset）”做无偏评估。

```python
# 用逆概率加权（IPW）缓解反馈偏差的直觉示例
# 假设曝光概率 prop 越小，该样本越稀有，应给更高权重
feedbacks = [
    {"sample_id": "a", "propensity": 0.9, "label": 1},
    {"sample_id": "b", "propensity": 0.2, "label": 0},
]

def ipw_weight(propensity):
    return 1.0 / max(propensity, 1e-6)

weighted = [(fb["sample_id"], fb["label"], ipw_weight(fb["propensity"])) for fb in feedbacks]
print("IPW 权重:", weighted)
```

---

## 5. 一个工程级最小闭环蓝图

把上面的点串起来，一个可运行的最小闭环可以这样组织：

1. 请求进来，模型打分并记录 `request_id`。
2. 用户行为异步写入日志表。
3. 定时任务把日志 join 成训练样本。
4. 触发训练，产出新模型。
5. 通过影子模式或 A/B 测试评估。
6. 达标则切换版本，否则回滚。

```python
# 端到端伪代码：请求 -> 记录 -> 回流 -> 训练 -> 评估 -> 上线决策
import time

def serve(request_id, x, model_version):
    # 模拟在线服务
    score = x * 1.0  # 假打分
    return {"request_id": request_id, "score": score, "model_version": model_version}

def collect_feedback(request_id, label):
    # 模拟异步写日志
    return {"request_id": request_id, "label": label, "ts": time.time()}

def train_from_logs(logs):
    # 模拟训练：返回新版本号
    return "v_next"

def evaluate(new_version, baseline_version, metric_new, metric_base):
    return metric_new > metric_base

# 1) 线上请求
resp = serve("req_1", x=2.0, model_version="v1")
# 2) 用户反馈回流
log = collect_feedback(resp["request_id"], label=1)
# 3) 训练新模型
new_version = train_from_logs([log])
# 4) 评估并决策
should_deploy = evaluate(new_version, "v1", metric_new=0.9, metric_base=0.8)
print("是否上线新模型:", should_deploy)
```

---

## 动手练习

**任务：在本地实现一个“电影推荐”的最小反馈闭环原型。**

要求：
1. 用 Python 写一个 `recommend(user_id)`，从 5 部电影里随机或按简单规则推荐 1 部。
2. 记录每次推荐结果到 `feedback_log`（包含 `user_id`、`movie_id`、`model_version`）。
3. 模拟用户反馈：用户对推荐的电影给出 0/1 评分（可手动输入或随机生成）。
4. 每隔 10 条反馈，用这些数据“训练”一个极简模型（例如统计每部电影的平均好评率，下次优先推荐好评率高的）。
5. 打印出每一轮推荐和模型更新后的推荐策略变化。

交付物：一个 `.py` 文件 + 一段 5 行以内的说明，解释你的闭环里“反馈如何影响下一次推荐”。

提示：不必用真实机器学习库，重点是**闭环结构**：请求 → 反馈 → 数据 → 策略更新 → 再请求。

```python
import random
from collections import defaultdict

random.seed(42)

MOVIES = ["M1", "M2", "M3", "M4", "M5"]
feedback_log = []
stats = {m: {"good": 0, "total": 0} for m in MOVIES}


def recommend(user_id):
    # 简单策略：好评率高的优先，未被充分探索的也给机会
    scores = {}
    for m in MOVIES:
        s = stats[m]
        rate = (s["good"] + 1) / (s["total"] + 2)  # 拉普拉斯平滑
        scores[m] = rate + random.random() * 0.1
    movie = max(scores, key=scores.get)
    feedback_log.append({"user_id": user_id, "movie_id": movie, "model_version": "v1"})
    return movie


def collect_feedback(movie_id, label):
    stats[movie_id]["total"] += 1
    stats[movie_id]["good"] += label


for i in range(20):
    user = f"u{i % 3}"
    movie = recommend(user)
    label = 1 if random.random() > 0.4 else 0
    collect_feedback(movie, label)
    if (i + 1) % 10 == 0:
        print(f"第 {i+1} 轮后统计:", stats)

print("反馈日志条数:", len(feedback_log))
```


---

## 本课题目

### single_choice · None



- [A] 数据漂移指输入特征分布发生变化，概念漂移指输入与标签之间的真实关系发生变化
- [B] 数据漂移指模型预测分数分布发生变化，概念漂移指特征分布发生变化
- [C] 数据漂移只在训练阶段出现，概念漂移只在推理阶段出现
- [D] 两者是同一现象的不同叫法，都仅指模型准确率下降

**参考答案**：0

**解析**：数据漂移关注输入特征边缘分布 P(X) 的变化；概念漂移关注条件分布 P(Y|X) 的变化，即输入到输出的映射关系改变。预测分数分布变化通常是数据漂移的结果或代理指标，而非定义本身。

### single_choice · None



- [A] 概念漂移
- [B] 数据漂移（协变量偏移）
- [C] 标签漂移
- [D] 模型退化

**参考答案**：1

**解析**：输入特征 P(X) 改变而 P(Y|X) 未变，属于协变量偏移，即数据漂移。标签漂移指 P(Y) 变化；概念漂移要求 P(Y|X) 改变；模型退化是结果并非漂移类型。

### single_choice · None



- [A] 结合业务变更记录与数据管道排查，确认是真实数据变化还是采集/预处理问题
- [B] 立即删除该特征并重训模型
- [C] 忽略告警，因为业务变更与模型无关
- [D] 直接把阈值调高以避免再次告警

**参考答案**：0

**解析**：漂移告警需与业务变更、数据管道变更联合分析，区分真实分布变化与数据质量问题。删除特征、忽略告警或调高阈值都属于未经诊断的过激或掩盖行为。

### single_choice · None



- [A] 统计显著说明分布差异不太可能由随机波动造成，但不一定对业务指标有实质影响
- [B] 统计显著必然意味着业务指标会显著下降
- [C] 业务影响大时统计检验一定显著
- [D] 两者完全等价，可互相替代

**参考答案**：0

**解析**：大样本下微小差异也可能统计显著；业务影响需结合效果指标与成本评估。两者相关但不等价，不能互相替代。

### single_choice · None



- [A] 标签漂移/概念漂移，因为 P(Y|X) 的定义发生了变化
- [B] 输入数据漂移，因为特征分布改变了
- [C] 模型架构失效
- [D] 与漂移无关，只是评估口径变化

**参考答案**：0

**解析**：标签定义改变会改变 P(Y|X)，属于概念漂移的一种来源（标签漂移）。输入特征分布未变，因此不是数据漂移；也不是架构问题。

### single_choice · None



- [A] 异步采集特征与预测的摘要统计，离线或近线计算漂移指标
- [B] 在每个请求内同步运行完整的 KS 检验与 PSI 计算
- [C] 把监控线程优先级设到最高并阻塞推理主线程
- [D] 关闭所有日志，避免 IO 影响

**参考答案**：0

**解析**：监控通常与推理解耦：采样或聚合统计后异步/近线计算。同步跑重统计会拖慢延迟；关闭日志会丧失可观测性。

### single_choice · None



- [A] 对高吞吐服务可按比例采样后再计算分布，但需保证采样随机且样本量足够支撑统计检验
- [B] 采样越少越好，因为样本越少计算越快，结论越准
- [C] 只能全量采集，任何采样都会使漂移检测完全失效
- [D] 采样必须按照预测分数排序后取前 10 个

**参考答案**：0

**解析**：随机采样可降低开销，但样本量过小会削弱检验功效；按预测分数取前几名会引入严重偏差，不能代表整体分布。

### single_choice · None



- [A] 真实标签往往延迟到达，且准确率是滞后指标，无法及时发现输入或预测分布的变化
- [B] 准确率只能取整数，不能反映模型状态
- [C] 准确率会被标签泄漏影响，因此完全不能用
- [D] 准确率需要 GPU 才能计算

**参考答案**：0

**解析**：准确率依赖真实标签，通常滞后，且不能定位漂移来源。它并非不能用，只是常需与分布类指标配合。

### single_choice · None



- [A] 该分箱对 PSI 的贡献为 0，可跳过或用平滑处理后计算
- [B] PSI 会变成无穷大，必须丢弃整个特征
- [C] PSI 会自动变为负数
- [D] 必须把该分箱合并到模型输出层

**参考答案**：0

**解析**：PSI 项含比例对数比，双零时按极限约定贡献 0；单侧为零则需平滑以避免无穷。不会自动变负，也无需丢弃特征。

### single_choice · None



- [A] 对每个特征分别计算漂移指标并按重要性/贡献度排序，同时保留特征级时间序列
- [B] 只保留一个全局漂移分数，不记录任何分特征信息
- [C] 只在模型训练时计算漂移，推理时不计算
- [D] 把漂移告警发送到与模型无关的营销群

**参考答案**：0

**解析**：特征级指标与时间序列有助于根因定位。仅有全局分数难以诊断；推理期往往是漂移最需要被监控的阶段。

### single_choice · None



- [A] 检测到漂移后应触发调查、评估影响，并在必要时触发重训或调整数据管道，再验证效果
- [B] 检测到漂移后必须立即无条件重训模型
- [C] 检测到漂移后应永久停用该模型
- [D] 漂移监控是纯离线报表，不需要任何后续动作

**参考答案**：0

**解析**：漂移监控的价值在于闭环：检测→诊断→决策（重训/调管道/忽略）→验证。无条件重训或停用都是缺少评估的极端做法。

### single_choice · None



- [A] 模型在推理时预测质量下降，因为模型学到的模式在新分布上不适用
- [B] 训练集准确率自动提高
- [C] 模型参数量自动减少
- [D] 标签编码方式自动改变

**参考答案**：0

**解析**：分布外输入会使模型泛化失效。训练集表现、参数量、标签编码不会因此自动改变。

### single_choice · None



- [A] PSI < 0.1 表示分布稳定，0.1 ≤ PSI < 0.25 表示中度变化，PSI ≥ 0.25 表示显著变化
- [B] PSI < 0.5 表示稳定，0.5 ≤ PSI < 1 表示中度变化，PSI ≥ 1 表示显著变化
- [C] PSI 越接近 1 越稳定，越接近 0 越不稳定
- [D] PSI 只能取值 0 或 1，表示是否发生漂移

**参考答案**：0

**解析**：PSI 的经典经验阈值是 0.1 和 0.25；0.25 以上通常触发告警。PSI 是非负连续值，不是二值，也不是越大越稳定。

### single_choice · None



- [A] 说明特征分布与参考分布存在统计学显著差异，提示可能发生漂移
- [B] 说明特征分布与参考分布完全相同
- [C] 说明模型准确率一定下降了 1%
- [D] 说明该特征一定是导致漂移的原因，可直接删除

**参考答案**：0

**解析**：p 值小意味着拒绝『两分布相同』的原假设，提示分布差异显著。但统计显著不等于业务影响显著，也不能直接断定准确率下降或该特征为唯一原因。

### single_choice · None



- [A] 监控输入特征分布与预测分数分布的变化
- [B] 直接计算推理集上的准确率
- [C] 统计模型文件的大小变化
- [D] 检查训练脚本的运行时长

**参考答案**：0

**解析**：真实标签往往延迟或缺失，因此常用输入分布和预测输出分布作为代理。准确率需要标签才能计算；模型文件大小与训练时长与漂移无关。

### single_choice · None



- [A] 告警疲劳，运维人员开始忽略告警，真正的问题被淹没
- [B] 漂移检测的统计功效显著提高，模型自动修复
- [C] 模型训练速度自动提升
- [D] 训练数据的标签质量自动改善

**参考答案**：0

**解析**：过低阈值会造成大量假阳性，引发告警疲劳。漂移告警本身不会自动修复模型、提升训练速度或改善标签质量。

### single_choice · None



- [A] 参考窗口通常取训练数据或某段稳定期的数据，检测窗口取近期数据，两者比较判断是否漂移
- [B] 参考窗口必须与检测窗口完全重叠，否则比较无意义
- [C] 参考窗口只能取最近一天的数据，检测窗口取过去一年
- [D] 参考窗口与检测窗口的大小必须严格相等，否则任何统计检验都无效

**参考答案**：0

**解析**：漂移检测本质是把当前观测（检测窗口）与基线（参考窗口，常为训练分布或稳定期）做对比。窗口可以不等长，但需注意检验方法对样本量的假设。

### single_choice · None



- [A] 引入季节性基线或按时间分桶建立参考分布，避免用全年统一基线误报
- [B] 永久关闭该特征的漂移监控
- [C] 将告警阈值提高到无穷大
- [D] 每次告警就立即全量重训模型

**参考答案**：0

**解析**：周期性漂移应用季节性/分桶基线来区分『预期波动』与『异常漂移』。关闭监控、无限阈值或每次全量重训都是过度或不足的反应。

### single_choice · None



- [A] 关键特征的分布统计量（均值、分位数、直方图）
- [B] 模型预测分数的分布
- [C] 推理请求量随时间的变化
- [D] 开发人员本地 IDE 的主题配色

**参考答案**：3

**解析**：特征分布、预测分布、请求量都可作为漂移与系统健康的信号；IDE 主题配色与模型或数据分布无关。

### single_choice · None



- [A] 假阳性率随特征数量增加而膨胀，容易误报漂移
- [B] 假阴性率必然降到零
- [C] 每个特征的 p 值会自动变小
- [D] 模型会自动选择正确的特征

**参考答案**：0

**解析**：多重比较会抬高整体第一类错误率，需用 Bonferroni、FDR 等方法校正。它不会自动降低假阴性或改变单个 p 值的计算。

### single_choice · None



- [A] 把模型训练代码自动部署到生产环境
- [B] 将生产环境中模型的表现与数据回流到训练与评估环节，驱动模型持续迭代
- [C] 对训练数据进行一次性的离线清洗
- [D] 用更高的硬件配置加速模型推理

**参考答案**：1

**解析**：反馈闭环关注的是生产数据/效果反馈回到训练与评估流程，形成可持续迭代的循环，而不是单纯的部署、一次性清洗或硬件加速。

### single_choice · None



- [A] 模型推理延迟必然升高
- [B] 训练数据的分布逐渐与线上真实分布脱节，模型效果随时间衰减
- [C] 在线服务无法处理并发请求
- [D] 特征存储（feature store）会自动停止工作

**参考答案**：1

**解析**：缺乏数据回流会导致训练分布与线上分布产生偏移（data drift），模型效果随时间和业务变化而衰减，这正是反馈闭环要解决的问题。

### single_choice · None



- [A] 替代所有在线 A/B 测试
- [B] 在只有旧策略日志的情况下，估计新策略的在线表现，缓解曝光偏差
- [C] 提高模型训练速度
- [D] 减少特征存储开销

**参考答案**：1

**解析**：反事实评估通过重要性采样等方法，利用旧策略日志估计新策略效果，是闭环中缓解反馈偏差的重要工具，但不能完全替代在线验证。

### single_choice · None



- [A] 直接替换，不需要任何验证
- [B] 先用小流量灰度发布，对比新旧模型指标后再逐步放量
- [C] 只在夜间替换，避免影响用户
- [D] 先删除旧模型再上线新模型

**参考答案**：1

**解析**：灰度发布可以在小流量下验证新模型，降低反馈闭环自动迭代带来的线上风险，是稳健的迭代实践。

### single_choice · None



- [A] 把模型参数量减少一半
- [B] 建立自动化的漂移检测与重训触发流水线
- [C] 把离线特征改成在线特征
- [D] 增加训练样本的采样比例

**参考答案**：1

**解析**：闭环迭代周期的瓶颈常在检测与触发环节，自动化监控和触发流水线可显著缩短响应时间。

### multi_choice · None



- [A] 线上数据与标签的回流机制
- [B] 模型效果的监控与漂移检测
- [C] 基于反馈的模型重训或更新策略
- [D] 在线推理服务的 GPU 驱动版本管理

**参考答案**：[0, 1, 2]

**解析**：数据回流、监控漂移检测、重训/更新策略是闭环的核心环节。GPU 驱动版本管理属于基础设施运维，不属于反馈闭环本身的核心概念。

### multi_choice · None



- [A] 保证流量随机分配到各组
- [B] 预先定义主要评估指标和停止规则
- [C] 持续观察并随时根据结果提前结束实验
- [D] 保证实验组和对照组在关键维度上可比

**参考答案**：[0, 1, 3]

**解析**：随机分配、预先定义指标和停止规则、组间可比性是 A/B 测试可靠性的基础；随时提前结束会导致 peeking bias。

### multi_choice · None



- [A] 输入特征分布随时间变化
- [B] 特征与标签的条件概率关系变化
- [C] 标签的先验分布发生变化
- [D] 服务器日志文件体积增大

**参考答案**：[0, 1, 2]

**解析**：数据漂移包括协变量漂移（输入分布变化）、概念漂移（条件关系变化）和标签漂移（先验变化）。日志体积增大只是运维现象。

### fill_blank · None



**参考答案**：["data drift", "数据漂移", "covariate shift", "协变量漂移"]

**解析**：输入分布变化最常见的形式是数据漂移/协变量漂移，注意与概念漂移区分。

### fill_blank · None



**参考答案**：["counterfactual", "counterfactual evaluation", "反事实评估", "off-policy evaluation", "离线策略评估"]

**解析**：反事实评估/离线策略评估利用旧策略日志估计新策略效果，是缓解曝光偏差的关键方法。

### code_reading · None



**参考答案**：只用最近 24 小时线上日志作为训练数据，可能导致训练与评估数据完全来自当前线上策略，形成曝光偏差/反馈回路偏差，且样本量可能不足、无法覆盖长尾；另外阈值触发单一，缺少标签延迟处理。核心问题：训练数据仅来自旧策略且数据窗口过短，容易引入反馈偏差和分布狭窄。

**解析**：该逻辑只依据最近一天的数据重训并灰度，未处理旧策略日志带来的选择偏差、标签延迟和数据量不足问题，可能使模型越训越窄。

### scenario · None



**解析**：只用旧策略日志重训会导致曝光偏差并不断自我强化，形成反馈回路偏差，导致推荐集中到少数热门项。改进方向包括引入探索机制、使用反事实/离线策略评估、保持一定随机流量、灰度验证后再全量。

### single_choice · None



- [A] 离线评估可以用历史数据快速验证，但在线评估才能反映真实业务指标和用户反馈
- [B] 只要离线指标提升，线上效果就一定提升
- [C] 在线评估只适用于无监督学习
- [D] 离线评估必须每天重训一次模型才有效

**参考答案**：0

**解析**：离线评估基于历史数据，成本低但可能与线上存在偏差；在线评估（如 A/B 测试）能反映真实业务影响，两者互补，是闭环的重要环节。

### single_choice · None



- [A] 把用户随机分配到对照组和实验组
- [B] 在测试中途根据初期结果不断调整流量分配比例
- [C] 预先定义好主要评估指标
- [D] 保证两组样本量足够大

**参考答案**：1

**解析**：中途根据结果动态调整流量会造成选择偏差和多看偏差（peeking bias），破坏随机对照前提，使统计推断不可靠。

### single_choice · None



- [A] 在模型训练前减少数据量
- [B] 提前发现线上输入分布与训练分布不一致，触发重训或告警
- [C] 自动生成新的特征
- [D] 替代模型压缩与量化

**参考答案**：1

**解析**：漂移检测通过监控输入/输出分布变化，及时发现模型失效风险并触发闭环中的重训或人工介入，是闭环监控的关键组件。

### single_choice · None



- [A] 模型权重被意外重置
- [B] 可能发生了概念漂移（concept drift），即特征与标签之间的关系发生了变化
- [C] 服务端 CPU 负载过高
- [D] 特征存储容量不足

**参考答案**：1

**解析**：输入分布不变而预测/标签关系变化，属于概念漂移。数据漂移检测需要区分数据漂移与概念漂移。

### single_choice · None



- [A] 标签总是可以即时获得，没有挑战
- [B] 真实标签往往有延迟（如用户最终是否购买），需要等待和归因
- [C] 标签只能以图像形式存储
- [D] 标签无法用于监督学习

**参考答案**：1

**解析**：许多业务场景的真实标签存在延迟（延迟反馈问题），需要设计延迟标签处理和归因机制，这是反馈闭环工程中的核心难点之一。

### single_choice · None



- [A] 数据泄露
- [B] 延迟反馈（delayed feedback）
- [C] 特征交叉
- [D] 梯度消失

**参考答案**：1

**解析**：标签在动作发生后需要等待一段时间才可获得，称为延迟反馈，必须在闭环设计中显式处理。

### single_choice · None



- [A] 只监控服务器的 CPU 和内存
- [B] 监控模型输入分布、输出分布和业务指标，一旦异常就触发告警或重训
- [C] 只在模型上线前运行一次
- [D] 替代离线训练流程

**参考答案**：1

**解析**：模型监控覆盖数据分布、预测分布和业务 KPI，是闭环中触发迭代动作的传感环节。

### single_choice · None



- [A] 训练速度过慢
- [B] 可能引入曝光偏差（exposure bias）或反馈回路偏差，因为数据只来自旧策略的展示
- [C] 模型一定会过拟合测试集
- [D] 特征维度会不断减少

**参考答案**：1

**解析**：只使用旧策略产生的日志训练新策略，会引入曝光偏差；若不断自我强化，还可能形成反馈回路偏差（feedback loop bias），使闭环退化。
