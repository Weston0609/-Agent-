# s6u2l1 神经网络中的线性层（Linear Layer） / 神经网络的一层通常写成： / 损失函数（Loss Function）：让神经网络知道「错在哪、错多少」

> 来源 `content/lessons/s6u2l1.json`

## ai.nn.linear

# 神经网络中的线性层（Linear Layer）

> **一句话直觉**：如果神经网络是一座城市，线性层就是城市里所有道路的交汇点——它把输入信号按不同权重“混合”后再传递出去，是整个深度学习模型最基础、最频繁使用的计算单元。

---

## 1. 什么是线性层？

线性层（Linear Layer），也叫全连接层（Fully Connected Layer，FC）或稠密层（Dense Layer），做的事情非常朴素：

$$y = xW^T + b$$

- **x**：输入向量或一批输入，形状为 `(batch_size, in_features)`
- **W**：权重矩阵（weight），形状为 `(out_features, in_features)`
- **b**：偏置向量（bias），形状为 `(out_features,)`
- **y**：输出，形状为 `(batch_size, out_features)`

**关键结论**：线性层本质上是一次矩阵乘法加一次加法。它不做非线性变换——这正是为什么神经网络中线性层后面总要接一个激活函数（activation function，如 ReLU）。

```python
# 用 NumPy 手动实现一个线性层的前向计算
import numpy as np

# 假设输入：2 个样本，每个样本 3 个特征
x = np.array([[1.0, 2.0, 3.0],
              [4.0, 5.0, 6.0]])          # shape: (2, 3)

W = np.array([[0.1, 0.2, 0.3],           # shape: (2, 3)
              [0.4, 0.5, 0.6]])
b = np.array([0.01, 0.02])               # shape: (2,)

y = x @ W.T + b                          # (2,3) @ (3,2) + (2,) -> (2,2)
print(y)
# [[1.41 3.32]
#  [3.21 7.82]]
```

---

## 2. 为什么它被称为“全连接”？

“全连接”的意思是：**输入的每一个特征都与输出的每一个特征相连**。

假设输入有 `in_features` 个特征，输出有 `out_features` 个特征，那么权重矩阵一共有 `in_features × out_features` 个可学习参数，再加上 `out_features` 个偏置。

参数量计算公式：

$$\text{params} = \text{in\_features} \times \text{out\_features} + \text{out\_features}$$

**关键结论**：全连接层的参数量随输入和输出维度乘积增长，因此在高维输入（如图像像素）上会迅速膨胀，这也是 CNN（卷积神经网络）出现的原因之一。

```python
# 演示参数量增长
for in_f, out_f in [(784, 128), (784, 512), (1024, 1024)]:
    params = in_f * out_f + out_f
    print(f"in={in_f:<5} out={out_f:<5} -> {params:,} 个参数")
# in=784   out=128   -> 100,480 个参数
# in=784   out=512   -> 401,920 个参数
# in=1024  out=1024  -> 1,049,600 个参数
```

---

## 3. 用 PyTorch 实现线性层

PyTorch 提供了 `nn.Linear`，它自动管理权重初始化、梯度计算和参数更新。

**关键结论**：`nn.Linear(in_features, out_features)` 会自动创建形状为 `(out_features, in_features)` 的权重和形状为 `(out_features,)` 的偏置，并在前向传播时自动处理批次维度。

```python
import torch
import torch.nn as nn

# 定义：输入 3 维，输出 2 维
linear = nn.Linear(in_features=3, out_features=2)

# 查看权重和偏置的形状
print("weight shape:", linear.weight.shape)  # torch.Size([2, 3])
print("bias shape:  ", linear.bias.shape)    # torch.Size([2])

# 前向传播
x = torch.tensor([[1.0, 2.0, 3.0],
                  [4.0, 5.0, 6.0]])          # (2, 3)
y = linear(x)
print("output shape:", y.shape)              # torch.Size([2, 2])
print(y)
```

---

## 4. 线性层在神经网络中的位置

一个典型的多层感知机（Multilayer Perceptron，MLP）就是“线性层 + 激活函数”的堆叠：

```python
import torch.nn as nn

model = nn.Sequential(
    nn.Linear(784, 256),   # 输入层 -> 隐藏层
    nn.ReLU(),             # 非线性激活
    nn.Linear(256, 10),    # 隐藏层 -> 输出层
)

x = torch.randn(8, 784)    # 8 个样本，每个 784 维
logits = model(x)
print(logits.shape)        # torch.Size([8, 10])
```

**关键结论**：如果没有激活函数，多层线性层叠加等价于单层线性层——因为矩阵乘积仍然是矩阵乘积。非线性激活函数是引入表达力的关键。

```python
# 验证：两个线性层叠加，若无激活函数，等价于一个线性层
import torch
import torch.nn as nn

lin1 = nn.Linear(4, 3)
lin2 = nn.Linear(3, 2)

x = torch.randn(1, 4)
y_two = lin2(lin1(x))

# 手动融合成一个等价线性层
W_combined = lin2.weight @ lin1.weight         # (2,3) @ (3,4) = (2,4)
b_combined = lin2.weight @ lin1.bias + lin2.bias  # (2,)

y_fused = x @ W_combined.T + b_combined
print(torch.allclose(y_two, y_fused, atol=1e-6))  # True
```

---

## 5. 工程中的实践要点

- **初始化（Initialization）**：PyTorch 默认使用 Kaiming 均匀初始化，但有时需要手动调整。
- **设备（Device）**：线性层需要和输入在同一设备（CPU/GPU）上。
- **数据类型（dtype）**：`float32` 是默认，混合精度训练时用 `float16`。
- **调试**：打印 `weight.shape` 和 `bias.shape` 是排查维度错误的第一手段。

```python
import torch
import torch.nn as nn

linear = nn.Linear(4, 2)
print("默认初始化 weight:", linear.weight)
print("默认初始化 bias:  ", linear.bias)

# 手动初始化
nn.init.zeros_(linear.bias)
nn.init.xavier_uniform_(linear.weight)
print("手动初始化后 weight:", linear.weight)
```

---

## 动手练习

**任务**：在本地完成以下练习。

1. 用 NumPy 手动实现一个线性层的前向传播函数 `my_linear(x, W, b)`，返回 `x @ W.T + b`。
2. 构造输入 `x` 形状 `(5, 4)`，权重 `W` 形状 `(3, 4)`，偏置 `b` 形状 `(3,)`，计算输出并打印形状。
3. 用 PyTorch 的 `nn.Linear(4, 3)` 对同一个 `x` 做前向传播，验证输出形状与手动实现一致。
4. 在 PyTorch 版本中，把 `linear.weight` 和 `linear.bias` 替换为你手动构造的 `W` 和 `b`，验证输出与你 NumPy 实现的输出完全一致（用 `torch.allclose` 检查）。
5. **进阶**：堆叠两个线性层（无激活函数），手动融合成单个线性层，验证输出一致。

**提示**：注意 `nn.Linear` 的权重形状是 `(out_features, in_features)`，而不是 `(in_features, out_features)`。

## ai.nn.activation

## 一句话直觉
**激活函数（Activation Function）**是神经网络里“引入非线性”的开关：没有它，再多层线性层叠起来也只等价于一层线性模型。

---

## 1. 为什么需要激活函数？

神经网络的一层通常写成：

$$y = Wx + b$$

这是**线性变换（Linear Transformation）**。如果每一层都只有线性变换：

$$y = W_2(W_1x + b_1) + b_2 = (W_2W_1)x + (W_2b_1 + b_2)$$

仍然是一个线性函数。也就是说，**没有激活函数，深度网络会退化成单层线性模型**，无法拟合异或（XOR）、图像、语言等复杂模式。

激活函数的作用：在每层线性变换后加入一个**非线性函数（Non-linear Function）**，让网络具备逼近任意复杂函数的能力。

```python
import torch
import torch.nn as nn

# 没有激活函数：两层线性层仍然等价于一层线性层
linear1 = nn.Linear(2, 2)
linear2 = nn.Linear(2, 1)
x = torch.randn(1, 2)
y_no_act = linear2(linear1(x))
print("无激活输出:", y_no_act)
```

---

## 2. 常见激活函数长什么样？

### 2.1 Sigmoid

$$\sigma(x)=\frac{1}{1+e^{-x}}$$

特点：输出范围 $(0,1)$，曾经常用于二分类输出层。

缺点：
- 容易**梯度消失（Gradient Vanishing）**；
- 输出不是零中心（Not Zero-Centered），影响优化。

```python
import torch
import torch.nn as nn

x = torch.tensor([-2.0, 0.0, 2.0])
sigmoid = nn.Sigmoid()
print("Sigmoid:", sigmoid(x))
```

### 2.2 Tanh

$$\tanh(x)=\frac{e^x-e^{-x}}{e^x+e^{-x}}$$

特点：输出范围 $(-1,1)$，是零中心的，比 Sigmoid 稍好。

缺点：两端仍然饱和，仍可能梯度消失。

```python
import torch
import torch.nn as nn

x = torch.tensor([-2.0, 0.0, 2.0])
tanh = nn.Tanh()
print("Tanh:", tanh(x))
```

### 2.3 ReLU

$$\mathrm{ReLU}(x)=\max(0,x)$$

特点：
- 计算简单；
- 正区间梯度恒为 1，缓解梯度消失；
- 是深度学习最常用的默认激活函数之一。

缺点：
- 负区间梯度为 0，可能出现**神经元死亡（Dead Neuron）**；
- 输出不是零中心。

```python
import torch
import torch.nn as nn

x = torch.tensor([-2.0, 0.0, 2.0])
relu = nn.ReLU()
print("ReLU:", relu(x))
```

### 2.4 LeakyReLU / GELU / SiLU

为了解决 ReLU 的死亡神经元问题，出现了 LeakyReLU：

$$\mathrm{LeakyReLU}(x)=\max(\alpha x,x)$$

GELU 和 SiLU 则是现代 Transformer、CNN 中常见的平滑激活函数。

```python
import torch
import torch.nn as nn

x = torch.tensor([-2.0, 0.0, 2.0])
print("LeakyReLU:", nn.LeakyReLU(0.01)(x))
print("GELU:", nn.GELU()(x))
print("SiLU:", nn.SiLU()(x))
```

---

## 3. 在 PyTorch 中怎么用激活函数？

两种常见写法：

1. **函数式（Functional）**：`torch.relu(x)`、`torch.sigmoid(x)`
2. **模块式（Module）**：`nn.ReLU()`、`nn.Sigmoid()`

在定义网络时，通常把激活函数放在线性层或卷积层之后。

```python
import torch
import torch.nn as nn

class MLP(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(2, 4),
            nn.ReLU(),          # 隐藏层激活
            nn.Linear(4, 1),
            nn.Sigmoid()        # 二分类输出层激活
        )

    def forward(self, x):
        return self.net(x)

model = MLP()
x = torch.randn(3, 2)
print("MLP 输出:", model(x))
```

---

## 4. 如何选择激活函数？

- **隐藏层默认**：ReLU；如果出现死亡神经元，可用 LeakyReLU、GELU、SiLU。
- **二分类输出层**：Sigmoid。
- **多分类输出层**：通常配合 `CrossEntropyLoss` 使用，不需要手动加 Softmax。
- **回归输出层**：通常不加激活函数。
- **Transformer / 大模型**：GELU、SiLU 很常见。

```python
import torch
import torch.nn as nn

# 多分类：输出 logits，CrossEntropyLoss 内部包含 LogSoftmax
logits = torch.randn(2, 5)
target = torch.tensor([1, 3])
loss_fn = nn.CrossEntropyLoss()
loss = loss_fn(logits, target)
print("多分类 loss:", loss)

# 二分类：Sigmoid + BCEWithLogitsLoss 更稳定
logits = torch.randn(2, 1)
target = torch.tensor([[1.0], [0.0]])
loss_fn = nn.BCEWithLogitsLoss()
loss = loss_fn(logits, target)
print("二分类 loss:", loss)
```

---

## 5. 工程实践中的关键点

1. **激活函数通常不改变张量形状**，只逐元素变换。
2. **不要在输出层乱加 ReLU**，除非任务确实需要非负输出。
3. **训练不稳定时**，可以尝试换激活函数，例如 ReLU -> GELU。
4. **激活函数也有可学习参数**，例如 PReLU。
5. **理解激活函数，是理解深度网络表达能力的第一步**。

```python
import torch
import torch.nn as nn

# PReLU 带可学习参数
prelu = nn.PReLU(num_parameters=1)
x = torch.tensor([-2.0, 0.0, 2.0])
print("PReLU:", prelu(x))
print("PReLU 参数:", prelu.weight)
```

## ai.nn.loss

# 损失函数（Loss Function）：让神经网络知道「错在哪、错多少」

> 一句话直觉：损失函数就是模型的「疼痛传感器」——它把预测和真实答案的差距量化成一个数，训练过程就是不断让这个数变小。

学习本讲前，假设你只懂最基础的 Python。我们会从「为什么要有个分数」讲到工程里怎么选、怎么调。全程代码可直接复制运行。

---

## 1. 为什么需要损失函数？

想象你在教一个小孩认猫。他指着一只狗说「猫」。你怎么纠正他？你得先意识到「他错了」，而且错得越离谱，纠正力度越大。

神经网络也一样。它前向传播（forward propagation）输出一个预测值，比如 `0.3`。真实答案是 `1.0`。如果没有任何机制衡量「差多少」，模型就不知道该往哪个方向调整参数（parameters）。

损失函数（Loss Function，也叫代价函数 Cost Function、目标函数 Objective Function）负责：
- 把「预测 vs 真实」压缩成一个标量（scalar）数值；
- 这个数值可导（differentiable），从而能用梯度下降（Gradient Descent）反向传播（Backpropagation）更新权重。

**关键结论：损失函数是训练的信号源。没有它，网络只是一堆随机数。**

```python
import torch  # 用 PyTorch 演示；安装：pip install torch

# 假设模型对 3 个样本的预测值
y_pred = torch.tensor([0.3, 0.7, 0.9])
# 真实标签
y_true = torch.tensor([1.0, 1.0, 0.0])

# 均方误差（MSE）：平均每个样本 (pred - true)^2
loss_fn = torch.nn.MSELoss()
loss = loss_fn(y_pred, y_true)
print("MSE loss =", loss.item())  # 输出一个标量，这就是「疼痛值」
```

---

## 2. 回归任务常用：MSE 与 MAE

当你要预测的是连续数值（房价、温度、销量），叫回归（Regression）。

- **均方误差（Mean Squared Error, MSE）**：`mean((y_pred - y_true)^2)`。对大误差惩罚重，梯度平滑，但容易被离群点（outlier）带偏。
- **平均绝对误差（Mean Absolute Error, MAE）**：`mean(|y_pred - y_true|)`。对离群点更鲁棒，但在 0 点不可导，收敛可能慢。

**关键结论：误差的「平方」放大了大错的代价；误差的「绝对值」更公平但不够光滑。**

```python
import torch
import torch.nn as nn

pred = torch.tensor([2.0, 4.0, 6.0])
true = torch.tensor([2.5, 5.0, 5.5])

mse = nn.MSELoss()(pred, true)
mae = nn.L1Loss()(pred, true)  # L1Loss 就是 MAE
print(f"MSE={mse.item():.4f}, MAE={mae.item():.4f}")
# MSE 对 4.0 vs 5.0 这种较大误差惩罚更重，所以通常比 MAE 大
```

---

## 3. 分类任务常用：交叉熵（Cross-Entropy）

当你要判断「是猫/是狗」「这封邮件是不是垃圾邮件」，叫分类（Classification）。

分类模型通常先输出 logits（未归一化的分数），再通过 Softmax（多分类）或 Sigmoid（二分类）变成概率。

交叉熵（Cross-Entropy, CE）衡量两个概率分布的差异：预测越自信地犯错，损失越大。

二分类用 **BCEWithLogitsLoss**（内部自带 Sigmoid，数值更稳定）；多分类用 **CrossEntropyLoss**（内部自带 Softmax）。

**关键结论：分类问题几乎不用 MSE，因为交叉熵的梯度对「自信的错误」惩罚更合理，训练更快。**

```python
import torch
import torch.nn as nn

# --- 二分类示例 ---
logits = torch.tensor([2.0, -1.0, 0.5])   # 模型原始输出
labels = torch.tensor([1.0, 0.0, 1.0])    # 0/1 标签
bce = nn.BCEWithLogitsLoss()(logits, labels)
print("BCE loss =", bce.item())

# --- 多分类示例（3 个类别）---
logits_mc = torch.tensor([[2.0, 1.0, 0.1],   # 样本1
                          [0.5, 2.5, 0.3]])  # 样本2
labels_mc = torch.tensor([0, 1])             # 正确类别索引
ce = nn.CrossEntropyLoss()(logits_mc, labels_mc)
print("CrossEntropy loss =", ce.item())
```

---

## 4. 工程视角：损失函数怎么选、怎么调

选损失函数不是「越高级越好」，而是看任务和标签：

| 任务 | 输出 | 常用损失 |
|---|---|---|
| 回归 | 连续值 | MSELoss / L1Loss / SmoothL1Loss |
| 二分类 | 1 个 logit | BCEWithLogitsLoss |
| 多分类 | C 个 logit | CrossEntropyLoss |
| 类别极不平衡 | C 个 logit | CrossEntropyLoss(weight=...) |
| 多标签分类 | C 个独立 logit | BCEWithLogitsLoss |

工程要点：
1. **数值稳定性（numerical stability）**：优先用带 `WithLogits` 的版本，避免手动 Softmax/Sigmoid 后取 log 导致溢出。
2. **类别权重（class weight）**：少数类样本给更高权重，缓解不平衡。
3. **多任务（multi-task）**：总损失 = `w1 * loss1 + w2 * loss2`，权重是超参数（hyperparameter）。
4. **监控 loss 曲线**：训练 loss 不降，先检查标签格式、损失函数是否匹配任务。

**关键结论：损失函数和任务、标签编码方式必须严格匹配。错配是新手最常见的「训练完全不收敛」原因。**

```python
import torch
import torch.nn as nn

# 类别不平衡：类别 0 有 100 个样本，类别 1 只有 10 个
# 给类别 1 更高权重，让模型不敢忽略它
weights = torch.tensor([1.0, 10.0])
logits = torch.tensor([[2.0, 0.1], [0.2, 1.8]])
labels = torch.tensor([0, 1])
loss_fn = nn.CrossEntropyLoss(weight=weights)
print("加权 CE loss =", loss_fn(logits, labels).item())

# 多任务损失组合示例
task_a_loss = torch.tensor(0.5)
task_b_loss = torch.tensor(1.2)
total = 0.7 * task_a_loss + 0.3 * task_b_loss
print("Total multi-task loss =", total.item())
```

---

## 5. 一个完整的最小训练循环

把前面串起来：定义模型、损失、优化器（Optimizer），跑几步梯度下降，观察 loss 是否下降。

**关键结论：损失函数只有嵌入「前向 → 算 loss → 反向 → 更新」的循环里才有意义。**

```python
import torch
import torch.nn as nn

# 1. 造一份极简数据：y = 2x + 1
torch.manual_seed(0)
X = torch.randn(100, 1)
y = 2 * X + 1 + 0.1 * torch.randn(100, 1)

# 2. 定义模型：一层线性层
model = nn.Linear(1, 1)

# 3. 损失函数 & 优化器
loss_fn = nn.MSELoss()
optimizer = torch.optim.SGD(model.parameters(), lr=0.1)

# 4. 训练循环
for epoch in range(50):
    pred = model(X)              # 前向传播
    loss = loss_fn(pred, y)      # 计算损失
    optimizer.zero_grad()        # 清空旧梯度
    loss.backward()              # 反向传播
    optimizer.step()             # 更新参数
    if epoch % 10 == 0:
        print(f"Epoch {epoch:02d}, loss={loss.item():.4f}")

# 5. 看看学到的参数（应接近 w=2, b=1）
w, b = model.weight.item(), model.bias.item()
print(f"Learned: w={w:.3f}, b={b:.3f}")
```

看到 loss 从大变小、`w` 接近 2、`b` 接近 1，说明损失函数正确地把「错多少」传导给了参数更新。


---

## 本课题目

### single_choice · None



- [A] (4, 3)
- [B] (3, 4)
- [C] (4,)
- [D] (3,)

**参考答案**：1

**解析**：nn.Linear 的 weight 形状为 (out_features, in_features)，即 (3, 4)；偏置 bias 的形状为 (out_features,)，即 (3,)。干扰项 (4, 3) 是常见误解，误以为与输入维度在前。

### single_choice · None



- [A] (2, 5)
- [B] (2, 8)
- [C] (5, 2)
- [D] (8, 5)

**参考答案**：0

**解析**：nn.Linear 对输入的最后一维做线性变换，输出最后一维变为 out_features=5，前面维度不变，因此输出形状为 (2, 5)。干扰项 (2, 8) 是错误地认为维度不变，其余选项是把维度顺序弄错。

### single_choice · None



- [A] 形状 (7, 5)
- [B] 形状 (2, 7, 5)
- [C] 形状 (5,)
- [D] 形状 (7, 6)

**参考答案**：3

**解析**：nn.Linear(5, 3) 要求输入最后一维为 5。形状 (7, 6) 最后一维是 6，不匹配，会报错。其余选项最后一维均为 5，合法。

### single_choice · None



- [A] 输出的最后一维等于 out_features
- [B] 输出的最后一维等于 in_features
- [C] 输出与输入形状完全一致
- [D] 输出维度与批量大小有关

**参考答案**：0

**解析**：nn.Linear 只改变最后一维，从 in_features 变为 out_features，批量维度保持不变。干扰项误以为输出维度与批量大小相关或忽略维度变换。

### single_choice · None



- [A] 1280
- [B] 1290
- [C] 1280+10
- [D] 128×10+128

**参考答案**：1

**解析**：权重参数量为 10×128=1280，偏置参数量为 10，合计 1290。干扰项 1280 忽略偏置，其他选项计算方式错误。

### single_choice · None



- [A] nn.Linear(4, 3, bias=False)
- [B] nn.Linear(4, 3, use_bias=False)
- [C] nn.Linear(4, 3, bias=0)
- [D] nn.Linear(4, 3).no_bias()

**参考答案**：0

**解析**：nn.Linear 使用 bias 参数控制是否包含偏置，设为 False 即无偏置。干扰项使用了不存在的参数名或方法。

### single_choice · None



- [A] 2
- [B] 7
- [C] 5
- [D] 14

**参考答案**：1

**解析**：weight 形状为 (out_features, in_features)，所以 out_features=7。干扰项 2 是误把 in_features 当 out_features。

### single_choice · None



- [A] (16, 32, 128)
- [B] (16, 128, 64)
- [C] (16, 32, 64)
- [D] (128, 32, 64)

**参考答案**：0

**解析**：nn.Linear 只对最后一维进行变换，前面维度 (16, 32) 保持不变，最后一维由 64 变为 128，输出为 (16, 32, 128)。

### single_choice · None



- [A] nn.Linear(C, D)
- [B] nn.Linear(D, C)
- [C] nn.Linear(N, D)
- [D] nn.Linear(C, N)

**参考答案**：0

**解析**：输入最后一维为 C，需要映射到 D，因此 in_features=C、out_features=D，即 nn.Linear(C, D)。干扰项把输入输出维度写反或用了批量维度。

### single_choice · None



- [A] nn.Linear 就是全连接层，对输入的每个位置做独立的线性变换
- [B] nn.Linear 内部包含非线性激活函数
- [C] nn.Linear 只处理二维输入
- [D] nn.Linear 是卷积层的一种

**参考答案**：0

**解析**：nn.Linear 即全连接层，对每个样本（或序列位置）独立进行线性加权求和，不包含激活函数。干扰项误以为含激活、只处理二维或与卷积混淆。

### single_choice · None



- [A] 正常运行，输出维度为 10
- [B] 报错，因为缺少 out_features 参数
- [C] 正常运行，输出维度为 1
- [D] 正常运行，但 in_features 默认从 1 开始

**参考答案**：1

**解析**：nn.Linear 需要同时指定 in_features 和 out_features，只传一个参数会抛出 TypeError。这是常见笔误。

### single_choice · None



- [A] 对输入的 3 个特征做加权求和后加上对应偏置，得到 2 个输出值
- [B] 对输入的 3 个特征分别乘以偏置，得到 3 个输出值
- [C] 输入与权重逐元素相乘，得到 (1, 3) 输出
- [D] 将输入广播到 (1, 2)，逐元素相加

**参考答案**：0

**解析**：全连接计算为 y = xW^T + b，输入 3 维经过权重 (2, 3) 映射为 2 维，每个输出由 3 个加权和加对应偏置构成。干扰项混淆了矩阵乘法与逐元素运算。

### single_choice · None



- [A] 3 和 6
- [B] 6 和 3
- [C] 3 和 3
- [D] 6 和 6

**参考答案**：0

**解析**：nn.Linear 权重形状为 (out_features, in_features)，偏置为 (out_features,)。由 (6, 3) 可知 out_features=6、in_features=3。干扰项 6 和 3 是将其顺序理解为 (in_features, out_features)。

### single_choice · None



- [A] torch.nn.Linear(10, 4)
- [B] torch.nn.Linear(4, 10)
- [C] torch.nn.Linear(in_features=4, out_features=10)
- [D] torch.nn.Linear(10)

**参考答案**：0

**解析**：nn.Linear 的前两个参数依次为 in_features 和 out_features，正确写法是 nn.Linear(10, 4)。干扰项把参数顺序写反，或只提供一个参数（会报错缺少 out_features）。

### single_choice · None



- [A] (3, 2)
- [B] (2, 3)
- [C] (3, 5)
- [D] (5, 2)

**参考答案**：0

**解析**：批量维度 3 保留，最后一维由 in_features=5 映射为 out_features=2，输出为 (3, 2)。干扰项 (2, 3) 是错误交换了维度顺序，(3, 5) 是忽略映射，(5, 2) 是混淆了权重形状。

### single_choice · None



- [A] 最后一维为 6
- [B] 最后一维为 5
- [C] 最后一维为 4
- [D] 任意维度均可

**参考答案**：0

**解析**：in_features 必须等于输入最后一维，权重 (5, 6) 对应 in_features=6，因此输入最后一维需为 6。干扰项混淆了 in_features 与 out_features。

### single_choice · None



- [A] (out_features,)
- [B] (in_features,)
- [C] (out_features, in_features)
- [D] (1, out_features)

**参考答案**：0

**解析**：nn.Linear 的 bias 是一维张量，长度为 out_features，与权重每一行对应。干扰项常被误以为是 (in_features,) 或二维。

### single_choice · None



- [A] 它只能处理一维输入
- [B] 它可以接受任意形状的输入，但要求最后一维等于 in_features
- [C] 它要求输入必须是二维 (N, in_features)
- [D] 它会在输出前自动加入 Softmax

**参考答案**：1

**解析**：nn.Linear 对输入最后一维进行线性变换，可接受任意带批量维度的输入，只要最后一维等于 in_features。干扰项把它误当成只接受一维或二维输入，或误以为内含激活函数。

### single_choice · None



- [A] True（默认存在偏置）
- [B] False（默认无偏置）
- [C] 0
- [D] None

**参考答案**：0

**解析**：PyTorch 的 nn.Linear 默认 bias=True，即默认包含偏置项。干扰项常见误解是以为默认无偏置或默认值为 0。

### single_choice · None



- [A] (4, 1)
- [B] (4,)
- [C] (1, 4)
- [D] (6, 1)

**参考答案**：0

**解析**：批量维度 4 保留，最后一维映射为 1，输出形状为 (4, 1)。干扰项 (4,) 是误以为线性层会自动去维。

### single_choice · None



- [A] 把输入特征缩放到 0 到 1 之间
- [B] 为网络引入非线性，使模型能拟合复杂函数
- [C] 减少参数数量，防止过拟合
- [D] 加速梯度下降的收敛速度，但会去掉非线性

**参考答案**：1

**解析**：若没有非线性激活函数，多层网络叠加后仍等价于单个线性变换，无法拟合复杂函数。激活函数的作用是引入非线性，而不是归一化、减少参数或去掉非线性。

### single_choice · None



- [A] 输出范围为 (-1, 1)，且关于原点对称
- [B] 输出范围为 (0, 1)，当输入绝对值很大时梯度会趋近于 0
- [C] 输出范围为 [0, +∞)，不会出现梯度消失
- [D] 在 x=0 处输出为 0，常用于输出层做概率

**参考答案**：1

**解析**：Sigmoid 输出在 (0,1)，两端饱和导致导数接近 0，容易梯度消失。它是非负的、在 x=0 处输出 0.5，不是 0，也不关于原点对称。

### single_choice · None



- [A] 它是一种平滑、非单调的激活，形式与高斯分布累积相关，常用于 Transformer
- [B] 它是分段线性的，和 ReLU 完全相同
- [C] 它没有负值，输出范围是 [0, +∞)
- [D] 它只能用于卷积网络，不能用于 Transformer

**参考答案**：0

**解析**：GELU 是平滑、非单调的激活，常写作 x·Φ(x)（Φ 为标准正态 CDF），在 Transformer 等模型中广泛使用，并不是分段线性。

### single_choice · None



- [A] 它是平滑非单调的，在负值区域有小幅负输出，常与 ReLU 系列作对比
- [B] 它是单调递增且有界的，输出在 (0,1)
- [C] 它将所有负输入置为 0
- [D] 它需要手动指定负半轴斜率参数 α

**参考答案**：0

**解析**：Swish/SiLU 平滑、非单调，负区有小的负值，整体无界；它不在负区置 0，也不需要像 Leaky ReLU 那样手动给出负斜率。

### multi_choice · None



- [A] Sigmoid 与 tanh 在输入绝对值很大时导数趋近于 0，可能导致梯度消失
- [B] ReLU 在正半轴导数恒为 1，在一定程度上缓解梯度消失
- [C] ReLU 在负半轴导数为 0，可能造成神经元死亡
- [D] Softmax 常用于隐层，因为它的导数恒为 1

**参考答案**：[0, 1, 2]

**解析**：Sigmoid/tanh 两端饱和导致梯度消失；ReLU 正半轴梯度为 1 缓解该问题，但负半轴梯度为 0 有死亡风险。Softmax 常作多分类输出层，且其导数并非恒为 1。

### multi_choice · None



- [A] ReLU 计算简单，是许多网络默认的隐层激活
- [B] Leaky ReLU 在负半轴引入小斜率，可缓解神经元死亡
- [C] PReLU 将负半轴斜率作为可学习参数
- [D] ReLU 的输出是零中心的

**参考答案**：[0, 1, 2]

**解析**：ReLU 计算简单、常用；Leaky ReLU 负半轴固定小斜率，PReLU 将斜率设为可学习参数。ReLU 输出非负，不是零中心。

### multi_choice · None



- [A] 二分类常用 Sigmoid 输出一个概率
- [B] 多分类常用 Softmax 输出各类概率
- [C] 回归任务常使用恒等映射（不加激活）
- [D] 多分类输出层使用 Softmax 后，各类别概率之和约为 1

**参考答案**：[0, 1, 2, 3]

**解析**：Sigmoid 适合二分类概率，Softmax 适合多分类概率分布且和为 1，回归通常不加激活（线性输出）。四项均正确。

### fill_blank · None



**参考答案**：["0, 5", "0 5", "0,5", "0、5"]

**解析**：ReLU 对负输入输出 0，对正输入原样输出，因此 -3→0，5→5。

### fill_blank · None



**参考答案**：["tanh, softmax", "tanh softmax", "tanh、softmax", "tanh, Softmax"]

**解析**：tanh 输出 (-1,1) 且零中心；Softmax 把实数向量转成和为 1 的概率分布，用于多分类输出层。

### code_reading · None



**参考答案**：输出为 [0. 0. 2.]。因为 ReLU 对每个元素取 max(0, x)：-2 落到 0，0 仍是 0，2 保持为 2。

**解析**：np.maximum(0, x) 逐元素计算 max(0, x)，这正是 ReLU 的向量化实现，负值被截断为 0，非负值保持原样。

### code_reading · None



**参考答案**：f(-1000) ≈ 0，f(0) = 0.5，f(1000) ≈ 1。说明 Sigmoid 输出在 (0,1)，两端会饱和，导数在两端趋近 0（梯度消失）。

**解析**：Sigmoid 是 S 形有界函数，极端输入时输出贴近 0 或 1，对应导数趋于 0，这正是深层网络中梯度消失的根源之一。

### scenario · None



**解析**：Sigmoid 两端饱和会导致梯度消失，深层网络难以训练。换成 ReLU 等非饱和激活可缓解梯度消失、加快收敛，同时仍保留非线性。关键词需覆盖替换方向、原因（梯度消失）与效果（收敛）。

### single_choice · None



- [A] 输出范围为 (0, 1)，和 Sigmoid 完全相同
- [B] 输出范围为 (-1, 1)，且零中心化，通常比 Sigmoid 收敛更快
- [C] 输出范围为 (-∞, +∞)，是无界函数
- [D] 在输入很大时导数趋近于 1，不会饱和

**参考答案**：1

**解析**：tanh 输出 (-1,1) 且零中心，通常比 Sigmoid 收敛更好，但两端同样饱和，仍存在梯度消失问题，并不是无界函数。

### single_choice · None



- [A] 当 x<0 时输出为 x，负半轴梯度为 1
- [B] 当 x>0 时梯度恒为 1，当 x<0 时梯度为 0，可能出现『神经元死亡』
- [C] 输出范围是 (-1, 1)，适合作为概率输出
- [D] ReLU 处处可导，不会出现不可导点

**参考答案**：1

**解析**：ReLU 正半轴梯度为 1，负半轴输出恒为 0、梯度为 0，若某神经元长期落在负区可能不再更新（死亡）。它在 x=0 处不可导。

### single_choice · None



- [A] 让负半轴也有一个小的非零斜率，缓解神经元死亡问题
- [B] 把输出范围限制在 (0, 1)
- [C] 使函数在 x=0 处可导
- [D] 让负半轴输出恒为 0，从而更快

**参考答案**：0

**解析**：Leaky ReLU 在负半轴给出小斜率 α，使负区梯度非零，缓解 ReLU 的神经元死亡，但它在 x=0 处仍不可导，也不把输出限制到 (0,1)。

### single_choice · None



- [A] 隐层，输出为 [-1,1] 的特征
- [B] 多分类输出层，输出各类别的概率分布，各分量非负且和为 1
- [C] 二分类隐层，输出为单个 0/1 值
- [D] 任意层，用于把输入标准化为均值 0 方差 1

**参考答案**：1

**解析**：Softmax 把一组实数映射为分布，常用于多分类输出层，分量在 (0,1) 且和为 1，表示各类别概率；标准化均值方差是另一类操作。

### single_choice · None



- [A] ReLU
- [B] tanh
- [C] Leaky ReLU
- [D] Maxout

**参考答案**：1

**解析**：tanh 平滑可导、输出有界 (-1,1) 且零中心；ReLU 与 Leaky ReLU 都是分段线性、非平滑；Maxout 也是分段线性且非平滑。

### single_choice · None



- [A] 输出不是零中心，且深层梯度易消失，训练缓慢
- [B] 输出范围过大，导致数值溢出
- [C] 会把网络变成纯线性模型
- [D] 计算量太大，无法在 GPU 上运行

**参考答案**：0

**解析**：Sigmoid 输出非零中心、两端饱和使梯度很小，深层网络易梯度消失，训练慢；它计算并不特别昂贵，也不会变成线性模型。

### single_choice · None



- [A] 回归任务常不加激活或使用恒等映射；二分类常用 Sigmoid；多分类常用 Softmax
- [B] 任何任务输出层都必须使用 Softmax
- [C] 二分类输出层必须使用 tanh
- [D] 输出层不应使用任何激活函数，否则无法反传

**参考答案**：0

**解析**：输出层激活由任务决定：回归用线性/恒等，二分类用 Sigmoid 给概率，多分类用 Softmax；输出层使用激活不影响反传。

### single_choice · None



- [A] x>0 时输出 x，x<0 时输出 α(e^x - 1)，负区输出可接近 -α 且梯度非零
- [B] 其输出恒为非负数
- [C] 它把负半轴完全置为 0
- [D] 它在整个定义域上不可导

**参考答案**：0

**解析**：ELU 正半轴为 x，负半轴为 α(e^x-1)，输出下限为 -α，负区平滑且梯度非零；它并非处处不可导，负区也不是恒为 0。

### single_choice · None



- [A] 直接决定网络有多少层
- [B] 衡量模型预测值与真实目标之间的差距，为参数更新提供优化信号
- [C] 对输入数据做归一化处理
- [D] 决定每个神经元的激活函数类型

**参考答案**：1

**解析**：损失函数量化预测与目标之间的差异，反向传播据此计算梯度来更新参数。层数、归一化、激活函数都各自是独立的设计要素，不由损失函数决定。

### single_choice · None



- [A] 均方误差（MSE）
- [B] 二元交叉熵（BCE）
- [C] 交叉熵损失（Cross Entropy，配合 softmax）
- [D] 平均绝对误差（MAE）

**参考答案**：2

**解析**：互斥多分类通常用 softmax + 交叉熵，它与最大似然一致且梯度形式良好。BCE 适用于多个独立的二分类标签；MSE/MAE 常用于回归。

### multi_choice · None



- [A] 互斥多分类常用 softmax + 交叉熵
- [B] 多标签分类可对每个标签使用二元交叉熵
- [C] 回归任务常用 MSE、MAE 或 Huber 损失
- [D] 交叉熵损失天然适合回归连续值预测
- [E] 任何任务都应使用同一种损失函数

**参考答案**：[0, 1, 2]

**解析**：前三项符合常见任务与损失的对应关系；交叉熵面向概率/类别分布，不天然适合回归连续值；不同任务应选择匹配的损失。

### multi_choice · None



- [A] 检查是否存在先做 softmax 再取对数导致的数值下溢
- [B] 检查学习率是否过大导致参数飞散
- [C] 检查输入或标签是否有异常值/非法取值
- [D] 直接放弃损失函数，改为不训练
- [E] 使用带 logits 的稳定实现替代手动 softmax+log

**参考答案**：[0, 1, 2, 4]

**解析**：NaN 常见来源包括数值下溢、学习率过大、异常输入/标签。使用更稳定的实现和排查数据是正确处理；放弃训练不是合理方案。

### multi_choice · None



- [A] softmax 交叉熵隐含各类别互斥（概率和为 1）
- [B] 二元交叉熵对每个输出独立判断，概率不要求和为 1
- [C] 多标签任务（一个样本可有多个标签）更适合二元交叉熵
- [D] 二元交叉熵要求各类别概率之和必须为 1
- [E] softmax 交叉熵中一个样本只能有一个正确类别

**参考答案**：[0, 1, 2, 4]

**解析**：softmax 交叉熵对应互斥单标签，一个样本仅一个正类且概率和为 1；BCE 各输出独立，适合多标签，且不要求概率和为 1。所以第 4 项错误。

### multi_choice · None



- [A] 标签的编码方式（one-hot、类别索引等）
- [B] 是否对损失做加权或归一化
- [C] 预测值是否以 logits 形式传入
- [D] 优化器的学习率与批量大小
- [E] 损失函数的实现是否数值稳定

**参考答案**：[0, 1, 2, 3, 4]

**解析**：标签编码、损失加权/归一化、logits 与概率的差别、优化器超参、数值稳定性都会影响损失的实际行为和训练结果，全部正确。

### fill_blank · None



**参考答案**：["交叉熵", "交叉熵损失", "cross entropy", "cross-entropy", "CrossEntropyLoss"]

**解析**：互斥多分类的标准做法是 softmax 输出概率后使用交叉熵损失，它等价于对真实类别概率取负对数。

### fill_blank · None



**参考答案**：["均方", "均方误差", "MSE", "mean squared error", "mean squared error loss"]

**解析**：均方误差（MSE）对误差取平方，大误差被放大，因此对离群点敏感；MAE/Huber 相对更鲁棒。

### fill_blank · None



**参考答案**：["二元交叉熵", "二值交叉熵", "binary cross entropy", "BCE", "BCELoss", "binary cross-entropy"]

**解析**：多标签各标签独立，对每个输出用 sigmoid + 二元交叉熵（BCE）是标准做法，不要求各标签概率和为 1。

### code_reading · None



**参考答案**：先显式做 softmax 再取对数，会在概率极小时发生数值下溢或对 0 取对数，导致 loss 变成 inf/NaN 或梯度不稳定；带 logits 的交叉熵内部使用 log-sum-exp 等稳定技巧，能避免该问题。

**解析**：softmax 后某些类别概率可能小到浮点数无法表示，直接取对数会得到 -inf，进而产生 NaN。稳定的交叉熵实现把两步合并在对数域计算，规避下溢。

### code_reading · None



**参考答案**：计算的是交叉熵损失（对 one-hot 标签等于负对数似然）。真实类别预测概率越低，-log(概率) 越大，惩罚越强；概率越接近 1，损失越接近 0。

**解析**：one-hot 标签下 -sum(label*log(pred))/N 只保留正确类别的 -log(p)，即交叉熵/负对数似然。其曲线在 p→0 时急剧上升，故对高置信度错误惩罚极重。

### scenario · None



**解析**：softmax 交叉熵假设类别互斥、概率和为 1，只允许一个正类，因此无法表达多标签。多标签应改为对每个标签独立使用 sigmoid + 二元交叉熵，各标签概率互不约束。

### single_choice · None



- [A] 两者完全等价，没有任何区别，只是名字不同
- [B] 交叉熵等于负对数似然，在分类中常指对正确类别概率取负对数
- [C] 交叉熵只用于回归，NLL 只用于分类
- [D] 交叉熵不需要真实标签即可计算

**参考答案**：1

**解析**：对 one-hot 标签的分类任务，交叉熵就等于对真实类别预测概率取负对数，即负对数似然。二者在分类语境下表达的是同一目标。

### scenario · None



**解析**：MSE 对误差平方，极端样本带来的大误差被放大，梯度被离群点主导。可改用对离群点更鲁棒的 MAE 或 Huber 损失，或在数据层面清洗/裁剪异常样本。

### single_choice · None



- [A] 反向传播时对权重的更新次数
- [B] 需要对所有类别计算归一化分母，类别越多计算越贵
- [C] 标签编码的位数
- [D] 优化器的学习率设置

**参考答案**：1

**解析**：softmax 需要对全部类别求和得到归一化项，类别数量大时该步骤开销显著，因此会出现负采样、层次 softmax 等近似方法。

### single_choice · None



- [A] 均方误差（MSE），因为对大误差惩罚更重
- [B] 平均绝对误差（MAE）或 Huber 类损失，对离群点更鲁棒
- [C] 交叉熵损失
- [D] hinge 损失

**参考答案**：1

**解析**：MSE 对大误差是平方惩罚，离群点影响被放大；MAE 是线性惩罚，Huber 在大误差处转为线性，二者对离群点更鲁棒。

### single_choice · None



- [A] BCE 要求标签必须是互斥的多类别之一
- [B] 一个样本可以同时属于多个类别时，可对每个类别独立使用 BCE
- [C] BCE 只能配合 softmax 使用，不能配合 sigmoid
- [D] BCE 的输入必须是未归一化的 logits 才有意义，概率值不可用

**参考答案**：1

**解析**：多标签场景下各类别相互独立，对每个类别用 sigmoid + BCE 是标准做法。BCE 常配合 sigmoid 使用，输入既可用概率也可用 logits（数值稳定性不同）。

### single_choice · None



- [A] 最大化模型对训练数据的似然
- [B] 最小化模型的参数量
- [C] 最大化模型输出分布的熵
- [D] 最小化输入数据的维度

**参考答案**：0

**解析**：交叉熵等价于负对数似然，最小化它即最大化训练数据的似然，这是最大似然估计的体现。最大化输出熵反而会让分布更均匀，不是目标。

### single_choice · None



- [A] 损失函数选错了，必须立刻更换
- [B] 模型开始过拟合，训练集被记忆而泛化变差
- [C] 学习率一定太大导致梯度爆炸
- [D] 数据标签全部错误

**参考答案**：1

**解析**：训练损失下降而验证损失上升是过拟合的典型信号。它并不直接说明损失函数错误；梯度爆炸通常表现为损失剧烈震荡或变为 NaN。

### single_choice · None



- [A] 合并后模型参数量更少
- [B] 分开先做 softmax 再取对数在数值上更易下溢/不稳定，合并实现更稳定
- [C] 合并后不需要真实标签
- [D] 合并后可以省略反向传播

**参考答案**：1

**解析**：先 softmax 再求对数可能产生极小概率导致数值下溢，合并实现的内部使用 log-sum-exp 等技巧，梯度更稳定，这与参数量和是否需要标签无关。

### single_choice · None



- [A] 损失函数必须对模型参数可微（或至少可用次梯度）才能用梯度类优化器
- [B] 损失函数的选择会影响梯度的形状与训练难度
- [C] 只要损失函数选对了，模型结构、数据和优化器都无关紧要
- [D] 多任务时可以把多个损失加权求和作为总损失

**参考答案**：2

**解析**：损失函数只是训练中的一个环节，模型结构、数据质量、优化器与超参都强烈影响最终效果，说其他因素无关紧要明显错误。
