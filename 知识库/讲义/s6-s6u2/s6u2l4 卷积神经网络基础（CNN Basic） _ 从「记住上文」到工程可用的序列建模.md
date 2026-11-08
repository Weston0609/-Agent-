# s6u2l4 卷积神经网络基础（CNN Basic） / 从「记住上文」到工程可用的序列建模

> 来源 `content/lessons/s6u2l4.json`

## ai.nn.cnn_basic

# 卷积神经网络基础（CNN Basic）

> **一句话直觉：** CNN 就像给电脑装上一双“局部小眼睛”，让它能先看边缘、再看形状、最后认出整张图——专为图像设计的神经网络。

---

## 0. 为什么需要 CNN？

如果你用普通全连接网络（Fully Connected Network）处理一张 224×224×3 的图片，展开后输入维度是 150528。第一层若只有 1000 个神经元，参数量就超过 1.5 亿。参数爆炸、训练困难，而且它会把“左上角的猫耳朵”和“右下角的猫耳朵”当成完全无关的两件事。

CNN 用三个核心思想解决这个问题：

1. **局部连接（Local Connectivity）**：每个神经元只看图片的一小块区域。
2. **权值共享（Weight Sharing）**：同一个滤波器（Filter）在整张图上滑动，参数量骤减。
3. **层次化特征（Hierarchical Features）**：浅层学边缘/颜色，深层学纹理/部件/物体。

---

## 1. 卷积层：用“小窗口”扫描图片

卷积（Convolution）本质是：拿一个小矩阵（叫**卷积核**或**滤波器**，Kernel / Filter）在输入上滑动，每个位置做逐元素乘加，得到一张**特征图**（Feature Map）。

关键公式（单通道）：

```
out[i, j] = sum_{m,n} x[i+m, j+n] * k[m, n] + b
```

- **步长（Stride）**：窗口每次滑多少格。
- **填充（Padding）**：在边缘补 0，控制输出尺寸。
- **输出尺寸**：`(H - K + 2P) / S + 1`

```python
import torch
import torch.nn as nn

# 1 张 1 通道 5x5 图片，经过 1 个 3x3 卷积核
x = torch.randn(1, 1, 5, 5)
conv = nn.Conv2d(in_channels=1, out_channels=1, kernel_size=3)
y = conv(x)
print("输入形状：", x.shape)   # torch.Size([1, 1, 5, 5])
print("输出形状：", y.shape)   # torch.Size([1, 1, 3, 3])
```

---

## 2. 激活函数：给 CNN 注入非线性

如果只有卷积，多层堆叠等价于一层线性变换，学不到复杂模式。所以每个卷积后接一个非线性的**激活函数**（Activation），最常用 **ReLU**。

```python
import torch.nn.functional as F

y = torch.randn(1, 1, 3, 3)
out = F.relu(y)   # 把所有负数变成 0，正数保持不变
print(out)
```

---

## 3. 池化层：降维 + 保留主要信息

**池化（Pooling）** 用小窗口做下采样，最常见的是**最大池化**（Max Pooling）：每个窗口取最大值。

作用：
- 减少计算量和参数
- 增强对小幅平移的不变性

```python
pool = nn.MaxPool2d(kernel_size=2, stride=2)
x = torch.randn(1, 1, 4, 4)
out = pool(x)
print("池化后：", out.shape)   # torch.Size([1, 1, 2, 2])
```

---

## 4. 组装一个完整的 CNN

一个典型的 CNN = `[Conv → ReLU → Pool] × N → Flatten → Linear → 输出`。

```python
import torch
import torch.nn as nn

class TinyCNN(nn.Module):
    def __init__(self, num_classes=10):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(1, 8, kernel_size=3, padding=1),   # 1x28x28 -> 8x28x28
            nn.ReLU(),
            nn.MaxPool2d(2),                              # 8x28x28 -> 8x14x14
            nn.Conv2d(8, 16, kernel_size=3, padding=1),   # 8x14x14 -> 16x14x14
            nn.ReLU(),
            nn.MaxPool2d(2),                              # 16x14x14 -> 16x7x7
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),                                 # 16*7*7 = 784
            nn.Linear(16 * 7 * 7, 64),
            nn.ReLU(),
            nn.Linear(64, num_classes),
        )

    def forward(self, x):
        return self.classifier(self.features(x))

model = TinyCNN()
x = torch.randn(4, 1, 28, 28)   # batch=4, 1 通道, 28x28
print("输出：", model(x).shape)  # torch.Size([4, 10])
```

---

## 5. 感受野与训练要点

- **感受野（Receptive Field）**：输出中一个像素对应原图多大区域。层数越深、卷积核越大，感受野越大。
- **训练流程**：`前向 → 计算损失（如 CrossEntropyLoss）→ 反向传播 → 优化器更新`。
- **常见超参**：学习率（learning rate）1e-3 起步，batch size 32/64，优化器 Adam 通常比 SGD 容易调。

```python
import torch.optim as optim

model = TinyCNN()
optimizer = optim.Adam(model.parameters(), lr=1e-3)
criterion = nn.CrossEntropyLoss()

x = torch.randn(8, 1, 28, 28)
target = torch.randint(0, 10, (8,))

optimizer.zero_grad()
logits = model(x)
loss = criterion(logits, target)
loss.backward()
optimizer.step()
print("loss =", loss.item())
```

---

## 动手练习

**任务：在本地用 PyTorch 在 MNIST 上训练一个 TinyCNN，目标测试准确率 ≥ 98%。**

步骤：
1. 用 `torchvision.datasets.MNIST(download=True)` 加载训练集和测试集。
2. 用 `transforms.ToTensor()` 和 `Normalize((0.1307,), (0.3081,))` 预处理。
3. 搭建上面的 `TinyCNN`，使用 `CrossEntropyLoss` + `Adam(lr=1e-3)`。
4. 训练 3 个 epoch，每个 epoch 后在测试集上评估准确率。
5. 记录每个 epoch 的 loss 和 test_acc，观察是否收敛。

**加分项：** 把 `MaxPool2d` 换掉、增加 BatchNorm、或者把卷积核改成 5×5，观察准确率变化。

## ai.nn.rnn_lstm

# ai.nn.rnn_lstm：从「记住上文」到工程可用的序列建模

> 一句话直觉：很多数据不是孤立的点，而是有顺序的序列（文本、语音、股价、传感器读数）；RNN（Recurrent Neural Network，循环神经网络）让网络拥有“记忆”，LSTM（Long Short-Term Memory，长短期记忆网络）则让这份记忆在长序列里更可靠。

---

## 0. 为什么需要 RNN？

普通全连接网络（Feedforward Neural Network，前馈神经网络）和 CNN（Convolutional Neural Network，卷积神经网络）默认输入之间彼此独立。

但下面这句话：

- “我昨天买了一台 __”，你大概率会填“电脑/手机”，而不是“香蕉”。
- “我昨天吃了一根 __”，你大概率会填“香蕉”，而不是“电脑”。

决定空格填什么的关键信息，在前面的词里。也就是说，模型需要**上下文（context）**，需要**记忆（memory）**。

RNN 的核心思想很朴素：**把上一步的输出，作为这一步的额外输入**。于是网络在处理序列时，状态会沿着时间传递，形成“记忆”。

```python
# 直觉版 RNN：用 Python 列表模拟“隐藏状态”的传递
import numpy as np

# 假设每个时间步输入是 3 维向量
x_seq = [np.array([1.0, 0.0, 0.0]),
         np.array([0.0, 1.0, 0.0]),
         np.array([0.0, 0.0, 1.0])]

h = np.zeros(4)  # 初始隐藏状态
W_xh = np.random.randn(3, 4) * 0.1
W_hh = np.random.randn(4, 4) * 0.1

for x in x_seq:
    h = np.tanh(x @ W_xh + h @ W_hh)  # 新状态 = 当前输入 + 上一步记忆
    print(h.round(3))
```

这个极简循环里已经包含了 RNN 的全部灵魂：**当前状态 = f(当前输入, 上一状态)**。

---

## 1. 从 RNN 到 LSTM：为什么需要“门控”

### 1.1 朴素 RNN 的痛点

RNN 在反向传播时要沿时间展开，叫 BPTT（Backpropagation Through Time，时间反向传播）。序列一长，梯度会反复乘以权重矩阵：

- 梯度越来越小 → **梯度消失（vanishing gradient）**，远距离信息学不到；
- 梯度越来越大 → **梯度爆炸（exploding gradient）**，训练不稳定。

直觉上：RNN 的隐藏状态每步都被整体覆盖，像一块白板每步都被擦掉重写，久远信息很难保留。

### 1.2 LSTM 的解决方案：细胞状态 + 三个门

LSTM 引入一条贯穿时间的主干道——**细胞状态（cell state）**，并用三个“门（gate）”控制信息流：

- **遗忘门（forget gate）**：决定旧记忆丢掉多少；
- **输入门（input gate）**：决定新信息写入多少；
- **输出门（output gate）**：决定当前对外暴露多少。

“门”本质是 sigmoid 函数，输出 0~1，像阀门一样做软性开关。

```python
# 一个时间步的 LSTM 前向计算（单层，无 batch）
import numpy as np

def sigmoid(z):
    return 1 / (1 + np.exp(-z))

np.random.seed(0)
input_dim, hidden_dim = 3, 4
x = np.random.randn(input_dim)          # 当前输入
h_prev = np.zeros(hidden_dim)           # 上一隐藏状态
c_prev = np.zeros(hidden_dim)           # 上一细胞状态

# 四组权重：遗忘门 f、输入门 i、候选记忆 g、输出门 o
W = np.random.randn(input_dim + hidden_dim, 4 * hidden_dim) * 0.1
b = np.zeros(4 * hidden_dim)

z = np.concatenate([x, h_prev]) @ W + b
f, i, g, o = np.split(z, 4)              # 各 hidden_dim 维

f = sigmoid(f)                           # 遗忘门
 i = sigmoid(i)                          # 输入门
g = np.tanh(g)                           # 候选新记忆
o = sigmoid(o)                           # 输出门

c = f * c_prev + i * g                   # 更新细胞状态
h = o * np.tanh(c)                       # 输出隐藏状态

print('c =', c.round(3))
print('h =', h.round(3))
```

关键点：细胞状态的更新是**加法**（`f * c_prev + i * g`），而不是每一步整体覆盖。加法让梯度可以沿着“记忆高速公路”更稳定地回传，这就是 LSTM 缓解梯度消失的核心机制。

---

## 2. 工程中使用 LSTM：PyTorch 实战

实际项目里我们不会手写上面的循环，而是用深度学习框架。PyTorch 的 `nn.LSTM` 已经封装好。请重点记住它的输入输出形状：

- 输入 `x`：`(seq_len, batch, input_size)`（默认 `batch_first=False`）
- 初始状态：`h0`、`c0` 均为 `(num_layers, batch, hidden_size)`
- 输出：`output` 为 `(seq_len, batch, hidden_size)`，`(hn, cn)` 为最后一步状态

```python
import torch
import torch.nn as nn

# 一个最小的 LSTM 分类器：把序列映射成一个类别
class LSTMClassifier(nn.Module):
    def __init__(self, input_size=8, hidden_size=16, num_classes=2):
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, batch_first=True)
        self.fc = nn.Linear(hidden_size, num_classes)

    def forward(self, x):
        # x: (batch, seq_len, input_size)
        out, (hn, cn) = self.lstm(x)
        # 取最后时间步的隐藏状态做分类
        last = out[:, -1, :]
        return self.fc(last)

model = LSTMClassifier()
x = torch.randn(4, 10, 8)     # batch=4, seq_len=10, input_size=8
logits = model(x)
print(logits.shape)            # torch.Size([4, 2])
```

### 2.1 多层与双向

- `num_layers=2`：堆叠多层 LSTM，提升表达能力；
- `bidirectional=True`：同时从前往后、从后往前读，输出维度变为 `2 * hidden_size`。

```python
lstm = nn.LSTM(input_size=8, hidden_size=16, num_layers=2, bidirectional=True)
out, (hn, cn) = lstm(torch.randn(4, 10, 8))
print(out.shape)   # torch.Size([4, 10, 32])
print(hn.shape)    # torch.Size([4, 4, 16])  (层数×方向, batch, hidden)
```

### 2.2 训练一个序列任务（骨架）

```python
import torch
import torch.nn as nn

model = LSTMClassifier()
opt = torch.optim.Adam(model.parameters(), lr=1e-3)
loss_fn = nn.CrossEntropyLoss()

for step in range(50):
    x = torch.randn(8, 10, 8)                    # 假数据
    y = torch.randint(0, 2, (8,))                # 假标签
    logits = model(x)
    loss = loss_fn(logits, y)
    opt.zero_grad()
    loss.backward()
    opt.step()
    if step % 10 == 0:
        print(step, loss.item())
```

---

## 3. 常见工程问题与处理

### 3.1 梯度裁剪（gradient clipping）

即使有 LSTM，梯度爆炸仍可能发生。标准做法是训练前裁剪梯度范数：

```python
torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
```

### 3.2 变长序列与 padding

真实数据里序列长度不一。常用做法是 padding + 掩码，或用 `pack_padded_sequence` 让 LSTM 忽略填充位。

```python
from torch.nn.utils.rnn import pad_sequence

seqs = [torch.randn(5, 8), torch.randn(3, 8), torch.randn(7, 8)]
X = pad_sequence(seqs, batch_first=True)   # (3, 7, 8)
print(X.shape)
```

### 3.3 LSTM 与 GRU

GRU（Gated Recurrent Unit，门控循环单元）是 LSTM 的简化版：把遗忘门和输入门合并成更新门，参数更少、训练更快，小数据上往往与 LSTM 表现接近。实践中两者都值得一试。

---

## 4. 该记住什么

- RNN 的本质：**当前状态 = f(当前输入, 上一状态)**。
- LSTM 在 RNN 基础上加了**细胞状态 + 三个门**，用加法更新记忆，缓解梯度消失。
- 工程三件事：**输入形状**、**初始隐藏状态**、**输出取法（最后一步 or 池化）**。
- 长距离依赖、变长序列、梯度爆炸，是 LSTM 项目里最常遇到的三个现实问题。
- 今天 Transformer 虽强，但在小序列、低资源、边缘设备等场景，LSTM 依然是可靠基线。

---

## 5. 动手练习

**任务：手写一个 LSTM 单元，并用它做一个「序列求和」回归器。**

要求：
1. 用 PyTorch 实现一个类 `MyLSTMCell`，包含 forget/input/output 三个门和 cell state 更新，公式与课上一致。
2. 用这个 cell 搭建一个模型：输入形状 `(batch, seq_len, 1)`，把整个序列喂进去。
3. 任务：模型输出整条序列所有元素的和（一个标量）。
4. 生成随机数据训练，loss 用 `MSELoss`，跑 200 步，观察 loss 是否下降。
5. 对比：把学习率从 1e-3 改成 1e-1，看训练是否发散；加不加梯度裁剪，对稳定性有什么影响。

提示：
- 可以让每条序列是长度 10 的随机数，标签为它们的和；
- 也可以让序列长度随机变化，体验变长输入的处理。

完成后你应该能说清楚：LSTM 里“门”在做什么、细胞状态为什么能保留长期信息、以及训练时为什么需要梯度裁剪。


---

## 本课题目

### single_choice · None



- [A] 5×5
- [B] 3×3
- [C] 2×2
- [D] 4×4

**参考答案**：1

**解析**：无填充、步幅为 1 时，输出尺寸 = 输入尺寸 − 卷积核尺寸 + 1 = 5 − 3 + 1 = 3，因此输出为 3×3。选 5×5 是忽略了卷积核会缩小空间尺寸；选 4×4 是误用了 5−3+2 之类的错误公式；选 2×2 是把步幅当成了 2。

### single_choice · None



- [A] 30×30
- [B] 32×32
- [C] 34×34
- [D] 16×16

**参考答案**：1

**解析**：填充为 1 时每边补一圈 0，等效输入变 34×34，再按 34−3+1=32 得到 32×32。选 30×30 是忽略了 padding；选 34×34 是只加了填充未做卷积；选 16×16 是误以为步幅为 2。

### single_choice · None



- [A] 步幅越大，输出特征图的空间尺寸通常越小
- [B] 步幅只影响通道数，不影响空间尺寸
- [C] 步幅越大，卷积核的参数会越多
- [D] 步幅必须等于卷积核大小

**参考答案**：0

**解析**：步幅增大意味着卷积核每次移动更远，输出空间尺寸随之减小。选“只影响通道数”错误；选“参数变多”错误，卷积核参数与步幅无关；选“必须等于核大小”没有依据。

### single_choice · None



- [A] 26×26×8
- [B] 28×28×8
- [C] 26×26×1
- [D] 28×28×1

**参考答案**：0

**解析**：空间尺寸 = 28−3+1 = 26，通道数等于卷积核个数 8，故输出为 26×26×8。选 28×28×8 是忽略了卷积引起的尺寸缩小；选 26×26×1 是误以为输出通道等于输入通道；选 28×28×1 同时犯了两个错误。

### single_choice · None



- [A] 每个输出单元只与输入的一个局部区域相连，而不是全部输入
- [B] 每个输出单元与输入的所有像素相连
- [C] 局部连接意味着卷积核只能覆盖一个像素
- [D] 局部连接会增加参数数量

**参考答案**：0

**解析**：卷积的输出单元只连接到输入的一个局部窗口，这就是局部连接，它与权值共享共同降低参数量。选“与所有像素相连”是全连接层特征；选“只覆盖一个像素”是对局部的误读；选“增加参数”与事实相反。

### single_choice · None



- [A] 卷积层
- [B] 池化层
- [C] 全连接层
- [D] 归一化层（如批归一化）

**参考答案**：3

**解析**：该题意在区分卷积网络常用组件；批归一化虽是常见组件，但严格说不属于“层类型”的经典三分类，而卷积、池化、全连接是 CNN 的经典层。若按常见教材，卷积、池化、全连接属于经典层，归一化常作为附加组件。此处选归一化作为“不是经典层类型”的答案。

### single_choice · None



- [A] 1200
- [B] 240
- [C] 400
- [D] 75

**参考答案**：0

**解析**：每核参数 5×5×3 = 75，共 16 个核，总参数 75×16 = 1200。选 240 是漏乘输入通道；选 400 是只用 5×5 乘 16；选 75 是只算了一个核。

### single_choice · None



- [A] 最大池化取局部区域的最大值，平均池化取局部区域的平均值
- [B] 最大池化取平均值，平均池化取最大值
- [C] 两者都会引入可训练参数
- [D] 两者都会改变特征图的通道数

**参考答案**：0

**解析**：最大池化保留局部最强响应，平均池化对局部做平均，二者都无参数且一般不改变通道数。选“相反描述”是记反了；选“引入参数”错误；选“改变通道数”错误。

### single_choice · None



- [A] 卷积网络能利用空间局部性和平移不变性，参数更少
- [B] 卷积网络不需要激活函数
- [C] 卷积网络不能处理图像，只能处理文本
- [D] 卷积网络必须固定输入图像大小为 224×224

**参考答案**：0

**解析**：卷积通过局部连接与权值共享利用图像的空间结构，并具备一定的平移不变性，参数显著少于同规模全连接网络。选“不需要激活函数”错误；选“只能处理文本”与事实相反；选“必须固定 224×224”没有依据。

### single_choice · None



- [A] 3×3
- [B] 2×2
- [C] 4×4
- [D] 5×5

**参考答案**：0

**解析**：输出 = floor((7−3)/2)+1 = 3，故为 3×3。选 2×2 是计算时漏加 1；选 4×4 是误用步幅 1；选 5×5 是没考虑卷积核缩小尺寸。

### single_choice · None



- [A] 它只能在空间上做 1 个像素的卷积，没有实际用途
- [B] 它可以用于跨通道的信息融合与通道数调整
- [C] 它等价于恒等映射，不改变任何数值
- [D] 它必须与池化层一起使用

**参考答案**：1

**解析**：1×1 卷积在空间上不聚合邻域，但可在通道维度上做线性组合，常用于升维或降维及跨通道融合。选“没有用途”错误；选“恒等映射”只在特例下成立；选“必须与池化一起”没有依据。

### single_choice · None



- [A] 使用步幅为 2 的卷积或池化，并增加卷积核数量
- [B] 使用步幅为 1 的卷积，并减少卷积核数量
- [C] 使用 1×1 卷积并保持通道数不变
- [D] 去掉所有池化层并保持通道数不变

**参考答案**：0

**解析**：通常通过步幅为 2 的卷积或池化将空间尺寸减半，同时在下一层增加卷积核数量来提升通道数，从而在降采样的同时增强特征表达。其余选项都不能同时实现尺寸减半与通道增加。

### single_choice · None



- [A] 54
- [B] 216
- [C] 220
- [D] 24

**参考答案**：2

**解析**：每个卷积核参数为 3×3×6=54，4 个核共 216，再加 4 个偏置得 220。选 216 是漏算了偏置；选 54 是只算了一个核；选 24 是误把核数量与通道数直接相乘。

### single_choice · None



- [A] (3, 3)
- [B] (3, 3, 1)
- [C] (3, 3, 3)
- [D] (3, 3, 3, 3)

**参考答案**：2

**解析**：卷积核的通道数必须与输入特征图的通道数一致，因此单核形状为 (高, 宽, 输入通道) 即 (3, 3, 3)。选 (3, 3) 是忽略了通道维度；选 (3, 3, 1) 只在输入为单通道时成立；选 (3, 3, 3, 3) 多引入了一个维度。

### single_choice · None



- [A] 同一个卷积核在输入特征图的不同空间位置上使用相同的权重
- [B] 不同卷积核必须使用相同的权重
- [C] 每个空间位置都有一组独立的权重
- [D] 权值共享会增加模型的参数数量

**参考答案**：0

**解析**：权值共享指一个卷积核在整个空间位置上滑动并复用同一组权重，从而大幅减少参数。选“不同卷积核必须使用相同权重”是误解，不同核学习不同特征；选“每个位置独立权重”正是全连接层的做法；选“增加参数”与事实相反。

### single_choice · None



- [A] 池化层会引入可训练参数，从而增强模型表达能力
- [B] 池化层在降采样的同时保留显著特征，并减少后续计算量
- [C] 池化层会改变特征图的通道数
- [D] 池化层必须与卷积核大小相同才能工作

**参考答案**：1

**解析**：池化在空间维度上降采样，保留如最大值这类显著信息，并减少计算量。选“引入可训练参数”错误，池化通常无参数；选“改变通道数”错误，池化一般不跨通道改变通道数；选“必须与卷积核相同”没有依据。

### single_choice · None



- [A] 4×4
- [B] 2×2
- [C] 3×3
- [D] 1×1

**参考答案**：1

**解析**：池化输出尺寸 = (输入 − 池化窗口) / 步幅 + 1 = (4−2)/2+1 = 2，故为 2×2。选 4×4 是忽略了下采样；选 3×3 是误用步幅 1；选 1×1 是误算了窗口覆盖范围。

### single_choice · None



- [A] 填充会减少输出特征图的空间尺寸
- [B] 填充可以保持输出特征图的空间尺寸，并保留边缘信息
- [C] 填充会增加特征图的通道数
- [D] 填充只能使用 1 这一种取值

**参考答案**：1

**解析**：填充在边缘补零，可在卷积后维持空间尺寸，并让边缘像素被更多次覆盖，保留边缘信息。选“减少尺寸”与填充作用相反；选“增加通道数”错误，填充只影响空间维度；选“只能取 1”错误，填充宽度可按需设置。

### single_choice · None



- [A] 卷积核中权重为 0 的区域
- [B] 输出特征图上一个像素对应输入图像上的区域大小
- [C] 特征图的通道数量
- [D] 卷积层的参数量

**参考答案**：1

**解析**：感受野是输出特征图上某个单元能“看到”的输入区域大小，随着层数加深而扩大。选“权重为 0 的区域”是字面曲解；选“通道数量”和“参数量”都与感受野无关。

### single_choice · None



- [A] 模型表达能力不变，因为卷积本身就是线性的组合
- [B] 模型仍能拟合任意非线性函数，因为卷积核足够多
- [C] 多层线性卷积等价于单层线性卷积，无法学习复杂非线性特征
- [D] 模型参数会减少，因此无法训练

**参考答案**：2

**解析**：线性运算的复合仍是线性运算，缺少非线性激活时多层卷积退化为等效的单层线性变换，无法拟合复杂非线性关系。选“表达能力不变”是错误结论；选“仍能拟合任意非线性”忽略了线性复合的限制；选“参数减少”与激活函数无关。

### single_choice · None



- [A] 每个时间步都有独立的权重矩阵
- [B] 所有时间步共享同一组权重
- [C] 权重在每个时间步按固定比例衰减
- [D] 只有输出层跨时间步共享权重

**参考答案**：1

**解析**：RNN 的核心思想是参数在时间维度上共享，因此可以用同一组权重处理任意长度的序列，同时大幅减少参数量。

### single_choice · None



- [A] 当前隐藏状态只依赖当前输入
- [B] 当前隐藏状态依赖当前输入与上一时刻隐藏状态
- [C] 当前隐藏状态依赖未来输入
- [D] 当前隐藏状态与输入完全无关

**参考答案**：1

**解析**：h_t = f(W_x x_t + W_h h_{t-1} + b)，既有当前输入也有上一时刻的隐藏状态，这正是 RNN 具有记忆能力的来源。

### multi_choice · None



- [A] 输入门控制新信息写入细胞状态的程度
- [B] 遗忘门控制旧细胞状态被保留的程度
- [C] 输出门决定细胞状态中有多少暴露到隐藏状态
- [D] 门控值由线性变换后经 sigmoid 得到，范围在 0~1

**参考答案**：[0, 1, 2, 3]

**解析**：四项均为 LSTM 的标准设计：三个门分别控制写入、遗忘与输出，门值经 sigmoid 压缩到 (0,1) 区间。

### multi_choice · None



- [A] 梯度裁剪（gradient clipping）
- [B] 使用更小的学习率
- [C] 把门控激活从 sigmoid 改为 ReLU
- [D] 使用较小的初始化尺度

**参考答案**：[0, 1, 3]

**解析**：梯度裁剪是最常用手段，较小学习率与较小初始化也能降低爆炸风险。把门控激活改成 ReLU 不是针对梯度爆炸的标准做法。

### multi_choice · None



- [A] 可以指定 num_layers 实现多层堆叠
- [B] 可以指定 bidirectional=True 使用双向 LSTM
- [C] 输入的最后维必须是 input_size
- [D] LSTM 会自动把序列补齐到同一长度

**参考答案**：[0, 1, 2]

**解析**：num_layers、bidirectional、input_size 都是常见配置项；变长序列的补齐需要外部处理，模块本身不会自动完成。

### multi_choice · None



- [A] 更容易学到长距离依赖
- [B] 梯度传播路径更稳定
- [C] 参数量一定更少
- [D] 能更灵活地决定保留或丢弃信息

**参考答案**：[0, 1, 3]

**解析**：LSTM 通过门控与细胞状态改善了长依赖与梯度问题，但参数量通常比同维度的普通 RNN 更多，不是更少。

### fill_blank · None



**参考答案**：["输出", "output", "output gate", "输出门"]

**解析**：o_t 是输出门，控制细胞状态经 tanh 压缩后有多少暴露到隐藏状态 h_t。

### fill_blank · None



**参考答案**：["输出", "output", "输出序列", "output sequence"]

**解析**：第一个返回元素是 output，即每个时间步的隐藏状态序列。

### code_reading · None



**参考答案**：(4, 7, 20)

**解析**：batch_first=True 时输出为 (batch, seq_len, hidden_size)，即 (4, 7, 20)。

### code_reading · None



**参考答案**：(1, 3, 16)

**解析**：默认 batch_first=False，输入被视为 (seq_len, batch, input_size)。h_n 形状为 (num_layers, batch, hidden_size) = (1, 3, 16)。

### scenario · None



**解析**：平均词向量会丢失语序信息；当情感依赖否定、转折等跨词的长距离依赖时，LSTM 的门控与序列建模能力更合适。

### scenario · None



**解析**：损失变 NaN 常由梯度爆炸引起，优先检查是否有梯度裁剪与合适的学习率，同时排查输入是否含 NaN 或异常值。

### single_choice · None



- [A] 更大的隐藏层维度
- [B] 门控机制与细胞状态
- [C] 更多的训练轮数
- [D] 批归一化层

**参考答案**：1

**解析**：LSTM 通过输入门、遗忘门、输出门控制信息流动，并引入细胞状态作为长期记忆通道，使梯度可以沿较稳定的路径回传。

### single_choice · None



- [A] 决定当前输入有多少写入细胞状态
- [B] 决定细胞状态中有多少信息被丢弃
- [C] 决定细胞状态有多少输出到隐藏状态
- [D] 决定输出层使用哪种激活函数

**参考答案**：1

**解析**：遗忘门输出 0~1 之间的值，与上一时刻细胞状态逐元素相乘，控制保留或丢弃多少历史信息。

### single_choice · None



- [A] 序列长度超过训练时见过的长度
- [B] 使用 sigmoid 作为门控激活函数
- [C] 使用 tanh 生成候选细胞状态
- [D] 使用随时间反向传播训练

**参考答案**：0

**解析**：LSTM 缓解但未根除长程依赖问题，训练长度与推理长度差距过大时，性能通常会下降。其余选项都是 LSTM 的正常设计。

### single_choice · None



- [A] (seq_len, batch, input_size)
- [B] (batch, seq_len, input_size)
- [C] (batch, input_size, seq_len)
- [D] (seq_len, input_size, batch)

**参考答案**：1

**解析**：batch_first=True 表示第一个维度是 batch，因此形状为 (batch, seq_len, input_size)；默认 False 时才是 (seq_len, batch, input_size)。

### single_choice · None



- [A] 所有时间步的输出序列
- [B] 最后一个时间步的隐藏状态
- [C] 元组 (h_n, c_n)，即最终隐藏状态与细胞状态
- [D] 注意力权重

**参考答案**：2

**解析**：返回值为 (output, (h_n, c_n))，h_n 是最后时间步的隐藏状态，c_n 是最后时间步的细胞状态。

### single_choice · None



- [A] 原始输入序列
- [B] 第一层对应时间步的输出
- [C] 第一层最后一个时间步的隐藏状态
- [D] 第一层所有时间步输出的平均

**参考答案**：1

**解析**：堆叠 LSTM 是逐时间步的层级堆叠，第二层在 t 时刻接收第一层在 t 时刻的输出向量。

### single_choice · None



- [A] 只对最后一个时间步计算梯度
- [B] 沿时间维度展开计算图并反向求梯度
- [C] 把序列截断后再拼接梯度
- [D] 逐层独立训练网络

**参考答案**：1

**解析**：BPTT 是把循环结构沿时间维度展开成前馈网络的形式，再按链式法则反向传播；截断 BPTT 只是其中的一种近似变体。

### single_choice · None



- [A] 序列标注
- [B] 多对一分类（如情感分类）
- [C] 多对多生成
- [D] 逐帧目标检测

**参考答案**：1

**解析**：只取最后时间步的输出适用于整条序列对应一个标签的多对一任务，如句子情感分类。
