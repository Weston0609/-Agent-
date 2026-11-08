# s6u1l2 PyTorch 张量（Tensor）入门：从零到工程级 / 让 PyTorch 自动帮你算梯度

> 来源 `content/lessons/s6u1l2.json`

## ai.torch.tensor

# PyTorch 张量（Tensor）入门：从零到工程级

> **一句话直觉**：PyTorch 张量就是“能跑在 GPU 上、会自动求导、还能像 NumPy 一样做数值计算的多维数组”。深度学习里的一切数据（图片、文本、参数、梯度）最终都会变成张量。

---

## 1. 为什么需要张量（Tensor）？

在深度学习（Deep Learning）中，我们几乎总在处理**多维数组**：

- 一张灰度图：`(H, W)`（高、宽）
- 一批彩色图：`(N, C, H, W)`（批量、通道、高、宽）
- 一个词向量：`(embedding_dim,)`
- 一个线性层权重：`(out_features, in_features)`

NumPy 的 `ndarray` 已经能做多维数组，但它有两个关键缺口：

1. **没有 GPU 加速**：深度学习训练需要大量矩阵乘法，CPU 太慢。
2. **没有自动求导（autograd）**：反向传播（backpropagation）需要自动计算梯度。

PyTorch 的 `torch.Tensor` 同时补齐了这两点，并且 API 与 NumPy 高度相似，学习成本很低。

---

## 2. 创建张量：从 Python 列表到设备（device）

张量创建的常见方式：

- `torch.tensor(data)`：从 Python 列表/NumPy 数组复制数据创建。
- `torch.zeros/ones/empty`：按形状创建。
- `torch.randn/rand`：随机初始化。
- `torch.arange/linspace`：序列生成。

关键属性：

- `shape` / `size()`：形状
- `dtype`：数据类型（如 `torch.float32`）
- `device`：所在设备（`cpu` 或 `cuda`）
- `requires_grad`：是否需要求导

**工程要点**：模型和数据必须在**同一设备**上，否则会报错。

```python
import torch

# 从列表创建
x = torch.tensor([[1, 2], [3, 4]])
print(x.shape, x.dtype, x.device)  # torch.Size([2, 2]) torch.int64 cpu

# 指定浮点类型与设备
x = torch.tensor([[1.0, 2.0]], dtype=torch.float32, device='cpu')

# 常用工厂函数
a = torch.zeros(2, 3)
b = torch.ones(2, 3)
c = torch.randn(2, 3)          # 标准正态分布
d = torch.arange(0, 10, 2)     # [0, 2, 4, 6, 8]
```

---

## 3. 形状操作：reshape、view、permute、squeeze

形状（shape）操作是张量使用中最频繁、也最容易出错的部分。

- `reshape`：改变形状，必要时复制数据，最通用。
- `view`：要求内存连续（contiguous），否则报错；否则与 reshape 等价。
- `permute`：交换维度顺序，常用于 `(N,H,W,C) -> (N,C,H,W)`。
- `squeeze/unsqueeze`：删除/增加大小为 1 的维度。
- `transpose`：交换两个维度。

**工程要点**：遇到 `view` 报错时，先用 `.contiguous()`，或直接改用 `.reshape()`。

```python
x = torch.arange(12).reshape(2, 6)
print(x.shape)                 # torch.Size([2, 6])

# 增加/删除维度
y = x.unsqueeze(0)             # (1, 2, 6)
z = y.squeeze(0)               # (2, 6)

# 交换维度
img = torch.randn(2, 3, 32, 32)     # (N, C, H, W)
img_hwc = img.permute(0, 2, 3, 1)   # (N, H, W, C)
print(img_hwc.shape)                # torch.Size([2, 32, 32, 3])
```

---

## 4. 自动求导（autograd）：requires_grad 与 backward

PyTorch 的自动求导机制会记录所有对 `requires_grad=True` 张量的操作，构建计算图（computation graph）。调用 `backward()` 后，梯度会累积到叶子张量的 `.grad` 属性。

关键概念：

- **叶子张量（leaf tensor）**：用户直接创建的张量，默认是叶子。
- **非叶子张量**：由运算产生。
- **梯度累积**：多次 `backward()` 会累加，通常每步要 `optimizer.zero_grad()` 或 `x.grad.zero_()`。
- **detach()**：从计算图中脱离，不参与求导。
- **with torch.no_grad()**：推理时关闭梯度，节省显存。

```python
x = torch.tensor([2.0, 3.0], requires_grad=True)
y = x ** 2 + 3 * x   # y = x^2 + 3x
y.sum().backward()
print(x.grad)        # dy/dx = 2x + 3 => [7., 9.]

# 推理时关闭梯度
with torch.no_grad():
    z = x * 2
print(z.requires_grad)  # False
```

---

## 5. 设备与 NumPy 互操作：进入真实工程

工程中经常需要在 CPU/GPU、NumPy/PyTorch 之间转换：

- `tensor.to('cuda')` / `.cpu()`：迁移设备。
- `tensor.numpy()`：转 NumPy（共享内存，仅限 CPU）。
- `torch.from_numpy(arr)`：NumPy 转张量（共享内存）。
- `tensor.item()`：取标量值（Python 数字）。

**工程要点**：

- GPU 张量不能直接 `.numpy()`，需先 `.cpu()`。
- 共享内存意味着修改一方会影响另一方。
- 训练循环里常见写法：`data = data.to(device)`。

```python
import numpy as np

arr = np.array([1.0, 2.0, 3.0])
t = torch.from_numpy(arr)
t[0] = 100
print(arr)   # [100.   2.   3.]  共享内存

device = 'cuda' if torch.cuda.is_available() else 'cpu'
t2 = torch.randn(3).to(device)
print(t2.device)

# 标量提取
print(t2.sum().item())
```

---

## 结尾：动手练习

**任务：手写一个线性回归的“一步”前向+反向**

1. 用 `torch.randn` 生成 100 个样本，真实关系为 `y = 3x + 2 + 噪声`。
2. 定义可学习参数 `w = torch.randn(1, requires_grad=True)`、`b = torch.zeros(1, requires_grad=True)`。
3. 计算预测 `y_pred = w * x + b`，损失用均方误差 `loss = ((y_pred - y) ** 2).mean()`。
4. 调用 `loss.backward()`，打印 `w.grad` 和 `b.grad`。
5. 用 `with torch.no_grad(): w -= 0.01 * w.grad; b -= 0.01 * b.grad` 做一步梯度下降。
6. 重复 100 次，观察 `w` 是否接近 3、`b` 是否接近 2。

**提示**：每步更新前记得 `w.grad.zero_()`、`b.grad.zero_()`，否则梯度会累积。

## ai.torch.autograd

# ai.torch.autograd：让 PyTorch 自动帮你算梯度

## 一句话直觉

`autograd`（自动微分，automatic differentiation）是 PyTorch 的"自动求导引擎"：你只要用 `Tensor`（张量）把前向计算写出来，它就能沿着计算图（computation graph）反向自动算出每个参数的梯度（gradient），你无需手推导数公式。这是所有深度学习训练循环的地基。

---

## 1. 为什么需要 autograd：从手算导数到自动反向传播

神经网络的训练本质是：定义损失（loss），然后对每个参数求偏导 `∂loss/∂w`，再用梯度下降更新参数 `w ← w − lr · ∂loss/∂w`。

手算导数对几十亿参数的模型是不可能的。`autograd` 的做法是：**记录你每一步的运算**，反向时按链式法则（chain rule）自动回放。

```python
import torch

# 创建一个需要梯度的张量：requires_grad=True 是关键开关
x = torch.tensor(2.0, requires_grad=True)
y = x ** 2 + 3 * x + 1          # 前向：y = x^2 + 3x + 1

# 反向传播：自动求 dy/dx = 2x + 3，在 x=2 处应为 7
y.backward()
print(x.grad)                    # 输出: tensor(7.)
```

结论：**`requires_grad=True` 让张量进入"计算图"，`.backward()` 触发反向自动求导，结果存在 `.grad` 里。**

---

## 2. 计算图与叶子张量：谁有梯度，谁没有

Autograd 内部维护一张有向无环图（DAG，Directed Acyclic Graph）：

- **叶子张量（leaf tensor）**：由用户直接创建的（如 `torch.tensor(..., requires_grad=True)` 或 `nn.Parameter`）。反向传播结束后，梯度只保存在叶子的 `.grad` 上。
- **非叶子张量**：由运算产生的中间结果，默认反向结束时梯度会被释放（除非调用 `.retain_grad()`）。

```python
import torch

a = torch.tensor(2.0, requires_grad=True)   # 叶子
b = a * 3                                    # 非叶子中间量
c = b ** 2                                   # 最终输出

c.backward()
print(a.grad)                                 # tensor(36.)  因为 dc/da = 2*(3a)*3 = 18a = 36
print(b.grad)                                 # None（默认不保留）
print(b.is_leaf, a.is_leaf)                   # False True
```

结论：**只有叶子张量默认保留梯度；中间张量想拿梯度需要 `retain_grad()`。**

---

## 3. 梯度累积、清零与 `torch.no_grad()`

默认 `.backward()` 是**累加**到 `.grad`，不是覆盖。所以训练循环里必须手动清零，否则梯度会越加越大。另外，推理（inference）阶段不需要计算图，应使用 `torch.no_grad()` 关闭以省显存。

```python
import torch

w = torch.tensor(1.0, requires_grad=True)

# 第一次反向
(w * 2).backward()
print(w.grad)                    # tensor(2.)

# 第二次反向 —— 梯度会累加，变成 4
(w * 2).backward()
print(w.grad)                    # tensor(4.)

# 手动清零
w.grad.zero_()
print(w.grad)                    # tensor(0.)

# 推理阶段：不构建计算图，节省内存
with torch.no_grad():
    out = w * 2
    print(out.requires_grad)     # False
```

结论：**每步 `optimizer.zero_grad()`（等价于把各 `param.grad` 置零）是训练循环的标准动作；纯推理用 `torch.no_grad()`。**

---

## 4. 实战：用 autograd 手动实现一次梯度下降

不用 optimizer，我们完全靠 autograd 更新一个线性回归参数，感受"反向传播 + 参数更新"的完整闭环。

```python
import torch

# 目标：拟合 y = 3x + 2
X = torch.tensor([[1.0], [2.0], [3.0], [4.0]])
Y = 3 * X + 2

w = torch.tensor([[0.0]], requires_grad=True)
b = torch.tensor([[0.0]], requires_grad=True)

lr = 0.01
for step in range(200):
    pred = X @ w + b
    loss = ((pred - Y) ** 2).mean()   # MSE 损失

    loss.backward()                    # 反向自动求 grad

    with torch.no_grad():              # 更新时不参与图构建
        w -= lr * w.grad
        b -= lr * b.grad

    w.grad.zero_()                     # 清空梯度，避免累加
    b.grad.zero_()

print(w.item(), b.item())              # 接近 3.0 和 2.0
```

结论：**`loss.backward()` → `param -= lr * param.grad` → `grad.zero_()` 三步，就是整个训练引擎的最小原型。**

---

## 5. 进阶要点：`detach`、高阶梯度与 `nn.Module` 的关系

- `t.detach()`：从计算图剥离，返回一个共享数据但 `requires_grad=False` 的新张量。常用于把张量当"常量"用。
- 高阶梯度：对 `.grad` 再求导，需要 `create_graph=True`。
- `nn.Parameter` 的 `requires_grad` 默认为 `True`，`loss.backward()` 会自动填充它们的 `.grad`，这就是 `optimizer.step()` 背后的机制。

```python
import torch

# detach 示例
x = torch.tensor(2.0, requires_grad=True)
y = x ** 2
z = y.detach()                 # z 与 y 共享数值，但脱离图
print(z.requires_grad)         # False

# 高阶梯度示例
t = torch.tensor(2.0, requires_grad=True)
f = t ** 3                     # f = t^3

# 一阶导
(g1,) = torch.autograd.grad(f, t, create_graph=True)
print(g1)                       # 3*t^2 = 12

# 二阶导
(g2,) = torch.autograd.grad(g1, t)
print(g2)                       # 6*t = 12
```

结论：**`detach()` 用于切断梯度流；`create_graph=True` 支持求高阶导；autograd 是 `nn.Module` 与各种优化器工作的底层协议。**

---

## 动手练习（本地完成）

**任务：用 autograd 从零拟合一条二次曲线，并在图上观察损失下降。**

1. 构造数据：`X = torch.linspace(-2, 2, 100).unsqueeze(1)`，令 `Y = 2*X**2 - 3*X + 1 + 0.1*torch.randn_like(X)`（加一点噪声）。
2. 定义参数 `a, b, c`，均为 `nn.Parameter` 或带 `requires_grad=True` 的张量，初值 0。
3. 前向：`pred = a*X**2 + b*X + c`；损失：`((pred - Y)**2).mean()`。
4. 训练 500 步，学习率自选，每 100 步打印一次 loss；训练后打印 `a, b, c`，应接近 `2, -3, 1`。
5. 额外挑战：把 `loss.backward()` 外部套上 `torch.autograd.grad(loss, [a,b,c])` 手动取梯度，与用 `.backward()` 的方式对比输出。

**验收标准**：训练结束后 `a≈2, b≈-3, c≈1`，且 loss 明显下降。


---

## 本课题目

### single_choice · None



- [A] 张量不能与 NumPy 数组进行转换
- [B] CPU 上的张量可以通过 .numpy() 转为 NumPy 数组，NumPy 数组也可通过 torch.from_numpy() 转成张量
- [C] tensor.numpy() 会复制一份数据，修改数组不会影响原张量
- [D] GPU 上的张量可以直接调用 .numpy()

**参考答案**：1

**解析**：CPU 张量与 NumPy 数组可以互相转换：tensor.numpy() 得到数组，torch.from_numpy() 得到张量，且二者常共享内存。GPU 张量必须先 .cpu() 才能转 numpy。选项 C 错误，因为它通常共享内存而非复制。

### single_choice · None



- [A] torch.int64
- [B] torch.float32
- [C] torch.int32
- [D] torch.bool

**参考答案**：1

**解析**：整数张量参与真除法 / 时会进行类型提升，结果变为浮点类型，默认浮点 dtype 为 torch.float32。整除 // 才会保持整数类型。

### single_choice · None



- [A] (3, 4)
- [B] (4, 3)
- [C] (12,)
- [D] (1, 12)

**参考答案**：1

**解析**：.T 对二维张量进行转置，形状 (3,4) 变为 (4,3)。需注意 .T 是维度反转，对非连续转置后张量可能不连续。

### single_choice · None



- [A] detach 会从计算图中分离张量，返回共享数据但不需要梯度的新张量
- [B] detach 会复制数据，与原张量完全独立
- [C] detach 会删除原张量
- [D] detach 会停止原张量的梯度追踪，使其 requires_grad 变为 False

**参考答案**：0

**解析**：detach 返回一个与计算图断开的新张量，二者共享底层数据，对新张量的原地修改会影响原张量。它不改变原张量自身的 requires_grad。

### single_choice · None



- [A] (2, 3)
- [B] (1, 2, 3)
- [C] (2, 1, 3)
- [D] (2, 3, 1)

**参考答案**：1

**解析**：unsqueeze(0) 在第 0 维前插入一个大小为 1 的维度，形状变为 (1, 2, 3)。squeeze 则移除大小为 1 的维度。

### multi_choice · None



- [A] torch.tensor([1.0, 2.0]) 的 dtype 是 torch.float32
- [B] 可以使用 .to(torch.float64) 显式转换张量 dtype
- [C] 整数张量与浮点张量相加会报错
- [D] torch.tensor([True, False]) 的 dtype 是 torch.bool
- [E] dtype 转换一定会复制数据，且不可逆

**参考答案**：[0, 1, 3]

**解析**：A 正确，浮点默认 float32；B 正确，.to 可转 dtype；D 正确，布尔输入得到 bool 张量。C 错误，类型提升会自动发生；E 错误，dtype 转换可逆且不一定总复制。

### multi_choice · None



- [A] x.view(...)（在内存连续时）
- [B] x.reshape(...)（在可能时）
- [C] x.clone()
- [D] x.transpose(0, 1)
- [E] x + 1

**参考答案**：[0, 1, 3]

**解析**：view 和可兼容的 reshape 返回视图；transpose 返回共享数据的视图，但通常不连续。clone 和算术运算 x+1 都产生新数据。

### multi_choice · None



- [A] torch.zeros(2, 3) 创建全 0 浮点张量
- [B] torch.ones_like(x) 创建与 x 形状相同的全 1 张量，dtype 与 x 一致
- [C] torch.arange(5) 得到 [0,1,2,3,4]
- [D] torch.randn(2, 2) 产生均匀分布 [0,1) 的随机数
- [E] torch.full((2,), 7) 创建元素全为 7 的张量

**参考答案**：[0, 1, 2, 4]

**解析**：A、B、C、E 均正确。D 错误，randn 产生标准正态分布，均匀分布是 torch.rand。

### multi_choice · None



- [A] x.flatten() 将张量展平为一维
- [B] x.squeeze() 会移除所有大小为 1 的维度
- [C] x.permute(1, 0) 与 x.transpose(0, 1) 对二维张量效果相同
- [D] x.repeat(2, 3) 与 x.expand(2, 3) 都会复制数据
- [E] unsqueeze 只能插入大小为 1 的维度

**参考答案**：[0, 1, 2, 4]

**解析**：A、B、C、E 正确。D 错误：repeat 复制数据，expand 仅创建视图不复制（要求原维度为 1 或被广播）。

### fill_blank · None



**参考答案**：["reshape", "torch.reshape", "reshape(2, 3)"]

**解析**：reshape 在内存可行时返回视图，不可行时会复制，能同时处理连续和非连续张量，因此适用范围比 view 更广。答案为 reshape。

### fill_blank · None



**参考答案**：["广播", "broadcasting", "广播机制", "Broadcasting"]

**解析**：PyTorch 的广播机制会在维度兼容时自动扩展较小张量进行逐元素运算，形状 (3,) 与 (1,) 可广播为 (3,)。

### code_reading · None



**参考答案**：输出 tensor([100, 2, 3])。因为 y = x 只是让两个变量指向同一个张量对象，通过 y 修改元素会反映到 x；要得到独立副本应使用 x.clone()。

**解析**：张量赋值不复制数据，y 和 x 引用同一对象，故原地修改相互可见。

### single_choice · None



- [A] 两者都要求张量在内存中连续，否则报错
- [B] view 只能用于非连续张量，reshape 只能用于连续张量
- [C] reshape 在可能时返回视图，在无法保持连续时返回拷贝；view 对非连续张量会报错
- [D] 两者总返回拷贝，不会与原张量共享内存

**参考答案**：2

**解析**：view 要求张量内存布局兼容，非连续时抛错；reshape 更灵活，可行时返回视图，否则复制数据后返回新张量。这是常见易错点。

### scenario · None



**解析**：应先用 reshape 或（在内存连续时）view 将 (batch, seq, hidden) 展平为 (batch*seq, hidden) 进行计算，再用 reshape 恢复为 (batch, seq, hidden)。选择 reshape 更稳妥，因其兼容非连续张量，不能保证连续时才做拷贝。

### single_choice · None



- [A] (4, 5)
- [B] (3, 4)
- [C] (1, 4, 5)
- [D] (3, 5)

**参考答案**：0

**解析**：用整数下标索引会移除该维度，因此 a[1] 形状为 (4, 5)。若用切片 a[1:2] 则保留维度，形状为 (1, 4, 5)。

### single_choice · None



- [A] 只有形状完全相同的张量才能进行逐元素运算
- [B] 从最后一维开始比较，维度相等或其中一方为 1 时才可广播
- [C] 广播只适用于加法，不适用于乘法
- [D] 形状 (3, 1) 与 (3,) 不能广播

**参考答案**：1

**解析**：广播从尾部维度对齐，逐个比较：相等或其中一个为 1 则兼容，否则报错。形状 (3,1) 与 (3,) 会对齐为 (3,1) 与 (1,3)，无法广播，故 D 说法虽对但非规则描述。

### single_choice · None



- [A] tensor([4, 6])
- [B] tensor([3, 7])
- [C] tensor(10)
- [D] tensor([6, 4])

**参考答案**：0

**解析**：dim=0 表示沿第 0 维（行方向）求和，即对每列求和：1+3=4，2+4=6，得到 [4, 6]。dim=1 才是行内求和得到 [3, 7]。

### single_choice · None



- [A] in-place 操作不会改变原张量的数据
- [B] in-place 操作会返回一个新张量，原张量不变
- [C] in-place 操作直接修改原张量数据，可能影响依赖该张量的计算图
- [D] in-place 操作只能用于 GPU 张量

**参考答案**：2

**解析**：带下划线后缀的方法（如 add_）原地修改张量并返回自身，可能与自动求导的图产生冲突，导致反向传播报错，使用需谨慎。

### single_choice · None



- [A] 两者完全等价，没有区别
- [B] torch.tensor() 从数据推断 dtype，torch.Tensor() 是默认浮点类型的别名，传入数据会被当作 float 处理
- [C] torch.Tensor() 总是创建整数张量
- [D] torch.tensor() 只能创建标量

**参考答案**：1

**解析**：torch.tensor() 是推荐的工厂函数，依据输入推断 dtype；torch.Tensor() 是默认浮点类型（float32）的别名，传入列表会被转成浮点，可能导致意外的类型。

### single_choice · None



- [A] 自动把 CPU 张量搬到 GPU 后运算
- [B] 自动把 GPU 张量搬到 CPU 后运算
- [C] 抛出 RuntimeError，提示设备不一致
- [D] 结果是一个 CPU 张量

**参考答案**：2

**解析**：PyTorch 不会自动跨设备搬运数据，参与运算的张量必须处于同一设备，否则抛出运行时错误。需要显式 .to(device) 或 .cuda()/.cpu()。

### single_choice · None



- [A] 布尔索引要求 mask 与原张量形状完全一致，返回一维张量
- [B] 布尔索引只能用于一维张量
- [C] 布尔索引返回的张量与 mask 形状相同
- [D] 布尔索引中 True 的位置会被丢弃

**参考答案**：0

**解析**：布尔 mask 需与原张量形状一致，结果是一维张量，元素为 mask 中 True 对应位置的值。False 位置被丢弃。

### single_choice · None



- [A] 所有张量默认都记录梯度
- [B] 只有 requires_grad=True 的张量才记录梯度
- [C] 只有浮点型张量默认记录梯度
- [D] 只有 CUDA 张量默认记录梯度

**参考答案**：1

**解析**：PyTorch 中只有显式设置 requires_grad=True 的张量才会在计算图中被追踪并计算梯度；默认创建的新张量 requires_grad=False。

### single_choice · None



- [A] tensor([2.])
- [B] tensor([4.])
- [C] tensor([1.])
- [D] None

**参考答案**：1

**解析**：y = x²，对 x 求导为 2x，当 x=2 时导数为 4，因此 x.grad 为 tensor([4.])。

### multi_choice · None



- [A] requires_grad=True 的浮点张量参与运算会构建计算图
- [B] requires_grad=False 的张量参与运算不会出现在计算图中
- [C] requires_grad 可以在创建张量时通过参数指定
- [D] requires_grad 只能在创建张量时指定，之后无法修改
- [E] 只有 requires_grad=True 的叶子张量才会在 backward 后保存 .grad

**参考答案**：[0, 1, 2, 4]

**解析**：requires_grad 可在创建时设定，也可通过 requires_grad_() 或 .requires_grad 属性修改；选项 D 的说法错误。其余描述符合 autograd 的行为。

### multi_choice · None



- [A] 推理阶段可使用 no_grad 上下文节省显存
- [B] 对需要多次反传的图应设置 retain_graph=True
- [C] 累积梯度时需要在合适时机手动清零 .grad
- [D] 为避免 in-place 报错，应尽量避免在有梯度路径上原地修改张量
- [E] 只要张量是 float 类型就一定会被 autograd 追踪

**参考答案**：[0, 1, 2, 3]

**解析**：float 类型并不意味着自动追踪，仍需 requires_grad=True。其余选项均为使用 autograd 时的常见注意事项。

### multi_choice · None



- [A] 当对非标量输出调用 backward() 时必须提供 gradient 参数
- [B] gradient 参数的形状应与被求导输出的形状一致
- [C] gradient 参数表示对输出各分量施加的权重
- [D] 对非标量输出调用 backward() 无论如何都不需要 gradient 参数
- [E] gradient 参数可以省略，此时自动按 1 填充

**参考答案**：[0, 1, 2]

**解析**：对非标量输出必须传入形状匹配的 gradient 作为各分量的权重；不能省略，也不会自动填充。

### multi_choice · None



- [A] 使用 with torch.no_grad(): 包裹计算
- [B] 对输入张量使用 detach() 后再计算
- [C] 将张量的 requires_grad 设置为 False
- [D] 改用 with torch.enable_grad():
- [E] 对中间张量调用 retain_grad()

**参考答案**：[0, 1, 2]

**解析**：no_grad 上下文、detach() 以及设置 requires_grad=False 都能避免追踪；enable_grad 与 retain_grad 反而与追踪相关，不用于屏蔽。

### fill_blank · None



**参考答案**：["zero_grad", "zero_grad()", "optimizer.zero_grad()"]

**解析**：optimizer.zero_grad() 用于把优化器管理的所有参数的 .grad 清零，是训练循环中的标准做法。

### fill_blank · None



**参考答案**：["retain_graph", "retain_graph=True"]

**解析**：retain_graph=True 会让 backward() 不释放中间缓存，从而支持在相同图上再次反传。

### code_reading · None



**参考答案**：输出 tensor([2., 4., 6.])。因为 y = Σx_i²，对每个 x_i 求导为 2x_i，故梯度为 [2, 4, 6]。

**解析**：标量 y 可以直接 backward()，梯度为对每个元素求导得到的向量，即 2x。

### code_reading · None



**参考答案**：代码会报错，因为 y 是非标量张量，调用 backward() 时必须传入 gradient 参数以指定各分量的权重，否则无法直接反传。

**解析**：非标量输出需要 gradient 参数（与输出同形状）来指定回传权重的加权和。

### scenario · None



**解析**：在推理时使用 with torch.no_grad(): 上下文关闭梯度记录，避免构建计算图并保存中间激活，从而降低显存与计算开销。

### scenario · None



**解析**：默认 backward() 会释放中间缓存，第二次反传会因缺少缓存而报错；需要设置 retain_graph=True 保留计算图，或在必要时重建前向图。

### single_choice · None



- [A] 任何张量都可以直接调用 backward() 而不需要参数
- [B] 非标量张量调用 backward() 必须传入 gradient 参数指定各分量权重
- [C] 标量张量调用 backward() 必须传入 gradient 参数
- [D] non-scalar 张量不能调用 backward()

**参考答案**：1

**解析**：backward() 对标量输出可直接调用；对非标量输出必须通过 gradient 参数提供与输出同形状的权重张量（相当于对输出做加权求和后再反传）。

### single_choice · None



- [A] 在计算时使用 with torch.no_grad():
- [B] 在计算时使用 with torch.enable_grad():
- [C] 在计算前调用 tensor.detach_() 对输入张量
- [D] 把中间张量的 dtype 改为 int

**参考答案**：0

**解析**：with torch.no_grad(): 上下文会临时关闭梯度记录，常用于推理或参数更新；enable_grad 反而是开启。detach_ 会原地分离但并非通用屏蔽手段，改 dtype 也不是正确方式。

### single_choice · None



- [A] 依然可以正常计算梯度
- [B] 会报错，因为中间缓存已被释放
- [C] 自动重新构建计算图并继续
- [D] 只会返回第一次的梯度

**参考答案**：1

**解析**：默认 backward() 会释放计算图中间缓存，第二次调用会因缺少所需缓存而报错；如确需多次反传，应设置 retain_graph=True。

### single_choice · None



- [A] detach() 返回一个与原张量共享数据但不再需要梯度的新张量
- [B] detach() 会复制数据并保留梯度历史
- [C] no_grad() 会影响整个程序后续所有计算，无法局部恢复
- [D] detach() 与 data 属性完全等价，没有任何差别

**参考答案**：0

**解析**：detach() 返回共享底层存储但不带梯度历史的新张量；no_grad() 是上下文级开关；.data 属性虽共享数据但绕过版本检查，通常不建议使用。

### single_choice · None



- [A] 非叶子张量默认不会保存 grad，只有叶子张量默认保留 grad
- [B] 所有张量调用 backward 后都会保存 grad
- [C] 叶子张量一定是 requires_grad=False 的张量
- [D] 非叶子张量只要设置了 requires_grad=True 就一定会保留 grad

**参考答案**：0

**解析**：默认情况下只有叶子张量（如模型参数、输入）会累积 grad；非叶子中间结果不会保存 grad，若要保存需要通过 retain_grad() 显式指定。

### single_choice · None



- [A] 每次 backward() 都会清空之前的 grad 并重新赋值
- [B] 多次 backward() 会把梯度累加到 grad 上，通常需要在合适时手动清零
- [C] 梯度累积只对 CUDA 张量有效
- [D] 调用 backward() 会自动清零并写入新值

**参考答案**：1

**解析**：PyTorch 的 grad 会在多次 backward 调用间累积；在训练循环中通常在每次迭代开始前调用 optimizer.zero_grad() 或手动将 grad 置零。

### single_choice · None



- [A] 任何时候 in-place 操作都能被 autograd 正确支持
- [B] 当某个张量被用于计算梯度且随后被 in-place 修改时，可能抛出错误或产生不正确梯度
- [C] in-place 操作会自动克隆一份新的计算图
- [D] 只要张量不是叶子张量就一定能安全地 in-place 修改

**参考答案**：1

**解析**：in-place 操作若破坏了反向传播所需的中间值会报 version mismatch 等错误；因此要注意避免在需要梯度追踪的路径上原地修改张量。

### single_choice · None



- [A] torch.autograd.grad() 会把结果累加到输入的 .grad 上
- [B] torch.autograd.grad() 返回梯度但不自动写入 .grad，而 backward() 会写入叶子张量的 .grad
- [C] 两者完全等价，没有区别
- [D] torch.autograd.grad() 不能指定对哪些输入求导

**参考答案**：1

**解析**：torch.autograd.grad() 用于直接获取指定输入的梯度并返回，不修改 .grad；而 backward() 会把梯度累积到叶子张量的 .grad 属性上。
