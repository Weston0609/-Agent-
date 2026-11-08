# s6u1l3 在 PyTorch（一个深度学习框架）里，`device / 让张量住进正确的「数字房子」

> 来源 `content/lessons/s6u1l3.json`

## ai.torch.device

## 一句话直觉

在 PyTorch（一个深度学习框架）里，`device`（设备）决定了张量（Tensor）和模型到底跑在 **CPU** 还是 **GPU** 上；不搞清它，模型就会报 “Expected all tensors to be on the same device”。

---

## 1. 什么是 device？为什么需要它？

PyTorch 中的计算发生在某种“设备”上：

- `cpu`：中央处理器，所有机器都有，适合小规模计算和调试。
- `cuda`：NVIDIA GPU 上的并行计算平台，适合大规模矩阵运算。
- `mps`：Apple Silicon 上的 Metal Performance Shaders，Mac 用户的 GPU 后端。

一个张量（Tensor）存有数据，也“住”在某个设备上；两个张量做运算时必须在同一设备。

```python
import torch

# 默认创建在 CPU 上
a = torch.tensor([1.0, 2.0])
print(a.device)          # cpu

# 显式指定设备
b = torch.tensor([3.0, 4.0], device='cpu')
print(b.device)          # cpu
```

---

## 2. 如何查询与选择设备

工程上推荐的做法：写一个 `get_device()` 工具函数，按优先级自动挑选可用设备，这样同一份代码既能在笔记本 CPU 上跑，也能在服务器 GPU 上跑。

```python
import torch

def get_device():
    if torch.cuda.is_available():
        return torch.device('cuda')
    if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        return torch.device('mps')
    return torch.device('cpu')

device = get_device()
print('使用设备:', device)

x = torch.tensor([1.0, 2.0], device=device)
print('x.device =', x.device)
```

常见查询接口：

- `torch.cuda.is_available()`：CUDA 是否可用。
- `torch.cuda.device_count()`：GPU 数量。
- `torch.device('cuda:0')`：指定第 0 号 GPU。

---

## 3. 把张量搬到设备上：`.to()`

`.to(device)` 返回一个位于目标设备上的新张量；`cpu()` / `cuda()` 是它的语法糖。注意 `.to()` 默认**不是原地操作**，要写回变量。

```python
import torch

t = torch.tensor([1.0, 2.0])       # 在 CPU 上
t = t.to('cpu')                    # 显式搬到 CPU
print(t.device)                    # cpu

# 如果有 GPU，可以对比搬运前后的内存/设备
if torch.cuda.is_available():
    t_gpu = t.to('cuda')
    print(t_gpu.device)            # cuda:0
    t_back = t_gpu.cpu()           # 搬回 CPU
    print(t_back.device)           # cpu
```

---

## 4. 模型与优化器也要搬到同一设备

`nn.Module`（神经网络模块）和 `optimizer`（优化器）内部都持有张量，所以也要 `.to(device)`。习惯上把 `device` 提到代码最上层，训练循环里同时保证数据也在同一设备。

```python
import torch
import torch.nn as nn

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

model = nn.Linear(4, 2).to(device)          # 模型搬到设备
optimizer = torch.optim.SGD(model.parameters(), lr=0.01)

x = torch.randn(8, 4).to(device)            # 输入搬到同一设备
y = torch.randn(8, 2).to(device)

loss_fn = nn.MSELoss()
loss = loss_fn(model(x), y)
loss.backward()
optimizer.step()
print('loss device =', loss.device)         # 与 x、model 一致
```

---

## 5. 常见工程模式与调试技巧

- 用 `torch.device` 对象而不是字符串，便于比较、拼接索引（如 `cuda:1`）。
- 保存/加载 checkpoint（检查点）时把张量 `cpu()` 后再 `torch.save`，能避免跨机器设备不匹配。
- 报 “Expected all tensors to be on the same device” 时，先打印 `tensor.device` 与 `model` 参数的 device，再检查 DataLoader（数据加载器）是否把数据搬到了目标设备。

```python
import torch

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print('device =', device, '| type =', device.type)

# 保存时安全起见搬到 CPU
state = {'w': torch.randn(2, 2, device=device).cpu()}
torch.save(state, 'ckpt.pt')
loaded = torch.load('ckpt.pt', map_location='cpu')
print('loaded w device =', loaded['w'].device)   # cpu
```

---

## 动手练习

在本地新建 `device_practice.py`：

1. 写一个 `get_device()`，按 `cuda` → `mps` → `cpu` 的顺序返回可用设备。
2. 打印：`torch.__version__`、设备类型、若可用则打印 GPU 名称。
3. 创建一个 `(3, 3)` 的随机张量，搬到该设备上，再搬回 CPU，打印每一步的 `.device`。
4. 定义 `nn.Linear(3, 1).to(device)`，构造一个同设备的输入，做一次前向传播，打印输出张量的设备。
5. 故意制造一次设备不一致（比如输入留在 CPU），写下报错信息，并改成正确写法让程序跑通。

提交：脚本文件 + 运行输出截图，并写 3 行总结你遇到的第一个设备报错。

## ai.torch.dtype

# ai.torch.dtype：让张量住进正确的「数字房子」

> **一句话直觉**：在 PyTorch 里，`dtype`（data type，数据类型）决定了张量里每个数字用多少位、是整数还是小数存放——它直接影响模型能否训练、速度有多快、显存占多少。

---

## 一、为什么必须先学 dtype？

深度学习的本质是**大量数字的矩阵运算**。同样一个 `0.1`，可以存成 `float32`（4 字节）也可以是 `float64`（8 字节），还可以近似存成 `float16`（2 字节）。

- 用错 dtype：模型可能出现 `RuntimeError: expected scalar type Float but found Double`。
- 用对 dtype：你能把显存占用砍半、把推理速度提升数倍。

所以 `torch.dtype` 是所有 PyTorch 代码的第一块地基。

---

## 二、常见的 torch.dtype 有哪些？

PyTorch 的 dtype 大致分三类：

| 类别 | 代表 dtype | 说明 |
|---|---|---|
| 浮点（floating point） | `torch.float16` / `float32` / `float64` / `bfloat16` | 神经网络权重与激活默认用 `float32` |
| 整型（integer） | `torch.int8/16/32/64`、`uint8` | 索引、标签、量化常用 |
| 布尔（boolean） | `torch.bool` | 掩码（mask） |

> 直觉记法：`float32` 是深度学习世界的「普通话」，其他 dtype 都是为了**省显存**或**省带宽**而存在的方言。

---

## 三、如何查看与指定 dtype？

每个张量都有 `.dtype` 属性；创建时用 `dtype=` 参数指定。

```python
import torch

a = torch.tensor([1, 2, 3])              # 整数会被推断为 int64
print(a.dtype)                            # torch.int64

b = torch.tensor([1.0, 2.0, 3.0])         # 小数默认 float32
print(b.dtype)                            # torch.float32

c = torch.zeros(2, 2, dtype=torch.float64)  # 显式指定
print(c.dtype)                            # torch.float64
```

**关键结论**：整数和小数的默认 dtype 不一样（`int64` vs `float32`），写代码时要养成显式声明的习惯。

---

## 四、dtype 转换：`.to()` 与 `.type()`

转换有两种主流写法，**推荐 `.to()`**，因为它同时能改设备和 dtype。

```python
x = torch.tensor([1.0, 2.0, 3.0])   # float32
y = x.to(torch.float64)             # 转成 float64
print(y.dtype)                       # torch.float64

z = y.to(torch.int32)                # 转 int：直接截断小数部分
print(z, z.dtype)                    # tensor([1, 2, 3]) torch.int32
```

> 注意：`.to()` 默认**返回新张量**，不会原地修改，除非加 `x.to_(...)` 或在 `.to()` 后接赋值。

---

## 五、混合 dtype 运算的陷阱：类型提升（type promotion）

两个不同 dtype 的张量做算术时，PyTorch 会按规则**向上提升**：

```python
import torch
a = torch.tensor([1.0], dtype=torch.float32)
b = torch.tensor([1.0], dtype=torch.float64)
print((a + b).dtype)   # torch.float64

c = torch.tensor([1], dtype=torch.int32)
d = torch.tensor([1.0], dtype=torch.float32)
print((c + d).dtype)   # torch.float32
```

**工程实践**：训练前统一 dtype（一般全部 `float32` 或全部 `bfloat16`），否则会在某些算子上抛错或静默变慢。

---

## 六、一个真实的工程场景：模型与输入的 dtype 必须一致

```python
import torch
import torch.nn as nn

model = nn.Linear(3, 1)                       # 权重默认 float32
x = torch.randn(4, 3, dtype=torch.float64)    # 输入是 float64

# model(x)  # 会报错：expected scalar type Float but found Double
x = x.to(torch.float32)                       # 修复
y = model(x)
print(y.dtype)                                 # torch.float32
```

**结论**：模型权重和输入张量必须 dtype 一致，这是最常见的报错来源之一。

---

## 七、动手练习

**任务**：构造一个长度为 6 的一维张量，完成以下操作并在本地打印结果：

1. 用 `torch.arange` 生成 `0 ~ 5` 的整数张量，打印其 `dtype`。
2. 用 `.to(torch.float32)` 转成浮点，除以 2，打印结果与 dtype。
3. 用 `.to(torch.int32)` 再转回整型，观察小数部分如何变化。
4. 故意把它与一个 `float64` 张量相加，观察提升后的 dtype；然后用 `.to()` 强制统一为 `float32`。

**验收标准**：你能解释每一步 dtype 的变化原因，特别是第 3 步「截断」和第 4 步「提升」的区别。


---

## 本课题目

### single_choice · None



- [A] model.to('cuda')
- [B] model.device('cuda')
- [C] model.gpu()
- [D] model.cuda = True

**参考答案**：0

**解析**：PyTorch 中使用 Tensor.to() 或 Module.to() 方法将张量或模型移动到指定设备，'cuda' 表示 GPU。其余选项都不是 PyTorch 的 API。

### single_choice · None



- [A] CPU 张量和 GPU 张量可以直接进行逐元素相加
- [B] CPU 张量和 GPU 张量不能直接运算，会抛出运行时错误
- [C] CPU 张量和 GPU 张量运算时会自动将结果放到 GPU 上
- [D] CPU 张量和 GPU 张量运算时会自动将结果放到 CPU 上

**参考答案**：1

**解析**：PyTorch 要求参与运算的张量位于同一设备上，否则会报错。需要显式使用 .to() 或 .cpu()/.cuda() 统一设备。

### single_choice · None



- [A] 正确，否则会报错
- [B] 错误，PyTorch 会自动处理设备差异
- [C] 只在训练时正确，推理时无所谓
- [D] 只在多 GPU 时正确

**参考答案**：0

**解析**：模型参数与输入数据必须在同一设备上，否则运算会抛出 RuntimeError。

### single_choice · None



- [A] device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
- [B] device = torch.device('cuda')
- [C] device = 'gpu' if torch.cuda.is_available() else 'cpu'
- [D] device = torch.device('cpu' if torch.cuda.is_available() else 'cuda')

**参考答案**：0

**解析**：通过 torch.cuda.is_available() 判断是否有 GPU，再选择 'cuda' 或 'cpu'，是常见且安全的写法。

### single_choice · None



- [A] 作为 torch.tensor 的 device 参数
- [B] 作为 nn.Module.to() 的参数
- [C] 作为 torch.zeros 的 device 参数
- [D] 以上都可以

**参考答案**：3

**解析**：torch.device 对象可用于张量创建函数的 device 参数，也可用于 Module.to() 等方法。

### single_choice · None



- [A] 如果张量已经在目标设备上，.to() 不会复制数据，直接返回原张量
- [B] .to() 可以同时改变 dtype 和 device
- [C] .to() 总是返回一个新张量
- [D] .to() 可以接受字符串如 'cuda:1' 作为参数

**参考答案**：2

**解析**：.to() 在设备与 dtype 均未改变时可能返回原张量（不复制），并非总是返回新张量。

### single_choice · None



- [A] model.to('cuda:1')
- [B] model.to('cuda:2')
- [C] model.to('gpu:1')
- [D] model.to(1)

**参考答案**：0

**解析**：GPU 编号从 0 开始，第二块 GPU 编号为 1，使用 model.to('cuda:1')。

### single_choice · None



- [A] CPU
- [B] cuda:0
- [C] cuda:1
- [D] 取决于环境，可能报错

**参考答案**：1

**解析**：通过 .to('cuda') 将张量移动到当前默认 GPU，默认为 cuda:0。前提是 CUDA 可用。

### single_choice · None



- [A] t.cpu()
- [B] t.numpy().cpu()
- [C] t.to('cpu') 或 t.cpu()
- [D] t.cuda(False)

**参考答案**：2

**解析**：GPU 张量不能直接调用 .numpy()，需要先 .cpu() 或 .to('cpu') 移回 CPU。

### single_choice · None



- [A] 在 forward 中手动将输入 .to(self.device)
- [B] 在模型定义时设置 self.device 并在训练前将模型 .to(self.device)
- [C] PyTorch 会自动将输入移到模型所在设备
- [D] 以上 A 和 B 都是常见做法

**参考答案**：3

**解析**：常见做法是确定 device 后，将模型 .to(device)，并在 forward 或训练循环中将输入 .to(device)。PyTorch 不会自动移动输入。

### single_choice · None



- [A] 它是一个函数，调用后返回 CPU 张量
- [B] 它是一个 device 对象，表示 CPU 设备
- [C] 它只能在创建张量时使用，不能用于 Module.to()
- [D] 它等价于字符串 'cpu'，但两者不能混用

**参考答案**：1

**解析**：torch.device('cpu') 返回表示 CPU 的 device 对象，可用于张量创建和 Module.to() 等。

### single_choice · None



- [A] t.cuda()
- [B] t.cpu()
- [C] t.float()
- [D] t.to('cuda:0')

**参考答案**：2

**解析**：t.float() 只改变数据类型为 float32，不改变设备。其余选项都涉及设备移动。

### single_choice · None



- [A] 一个字符串，如 'cuda:0'
- [B] 一个 torch.device 对象，表示该张量所在的设备
- [C] 一个布尔值，表示是否在 GPU 上
- [D] 一个整数，表示 GPU 编号

**参考答案**：1

**解析**：t.device 返回 torch.device 对象，如 device(type='cuda', index=0)，而不是字符串或布尔值。

### single_choice · None



- [A] 自动将 a 移到 GPU 后相加
- [B] 自动将 b 移到 CPU 后相加
- [C] 抛出 RuntimeError，提示设备不一致
- [D] 结果 c 会同时在 CPU 和 GPU 上

**参考答案**：2

**解析**：PyTorch 不会自动跨设备移动张量，设备不一致时会抛出 RuntimeError。

### single_choice · None



- [A] torch.cuda.is_available()
- [B] torch.device.available()
- [C] torch.gpu.available()
- [D] torch.cuda.available()

**参考答案**：0

**解析**：torch.cuda.is_available() 是标准 API，返回布尔值表示 CUDA 是否可用。

### single_choice · None



- [A] torch.tensor([1, 2, 3], device='cuda')
- [B] torch.tensor([1, 2, 3], gpu=True)
- [C] torch.tensor([1, 2, 3]).cuda(True)
- [D] torch.tensor([1, 2, 3]).to_gpu()

**参考答案**：0

**解析**：创建张量时可通过 device='cuda' 参数指定设备，或创建后再调用 .to('cuda')。

### single_choice · None



- [A] 将 tensor 复制到 GPU 0 上
- [B] 将 tensor 复制到 CPU 上
- [C] 将 tensor 转换为 float 类型
- [D] 将 tensor 设为可训练

**参考答案**：0

**解析**：to('cuda:0') 将张量移动到编号为 0 的 GPU 上，返回新张量（若原张量已在目标设备上则返回自身）。

### single_choice · None



- [A] 两者完全等价，都表示第一块 GPU
- [B] 'cuda' 表示当前默认 CUDA 设备，'cuda:0' 明确表示编号 0 的 GPU
- [C] 'cuda' 表示所有 GPU，'cuda:0' 表示第一块 GPU
- [D] 'cuda' 表示 CPU，'cuda:0' 表示 GPU

**参考答案**：1

**解析**：torch.device('cuda') 不指定编号，使用当前默认设备；torch.device('cuda:0') 明确指定第 0 块 GPU。

### single_choice · None



- [A] x = x.cuda(); y = y.cuda()
- [B] x = x.to(device); y = y.to(device)，其中 device 为模型所在设备
- [C] x = x.gpu(); y = y.gpu()
- [D] x = x.to('gpu'); y = y.to('gpu')

**参考答案**：1

**解析**：推荐使用 .to(device) 并传入模型所在设备，这样代码在 CPU/GPU 环境下都能运行，且不硬编码设备。

### single_choice · None



- [A] t.cpu()
- [B] t.to('cpu')
- [C] t.clone().cpu()
- [D] 以上都会

**参考答案**：3

**解析**：t.cpu()、t.to('cpu') 以及 t.clone().cpu() 都会返回位于 CPU 的张量（克隆后移动）。

### single_choice · None



- [A] float32 占用 32 位，float64 占用 64 位，后者精度更高但内存和计算开销更大
- [B] float32 只能用于 CPU，float64 只能用于 GPU
- [C] float64 是默认的浮点类型，float32 需要显式指定
- [D] 两者精度相同，只是命名不同

**参考答案**：0

**解析**：float32 是 32 位单精度浮点，float64 是 64 位双精度浮点。float64 精度更高，但内存占用翻倍、计算通常更慢。PyTorch 默认浮点类型是 float32，不是 float64。

### single_choice · None



- [A] torch.int64
- [B] torch.float32
- [C] torch.int32
- [D] torch.uint8

**参考答案**：0

**解析**：torch.tensor 根据输入数据的类型推断 dtype。Python 整数默认对应 torch.int64（long）。浮点才会得到 float32。

### single_choice · None



- [A] torch.float32
- [B] torch.int8
- [C] torch.str
- [D] torch.complex64

**参考答案**：2

**解析**：PyTorch 张量支持 float、int、bool、complex 等多种 dtype，但不支持字符串类型 torch.str。

### multi_choice · None



- [A] torch.float16
- [B] torch.float32
- [C] torch.bfloat16
- [D] torch.int64
- [E] torch.float64

**参考答案**：[0, 1, 2, 4]

**解析**：float16、bfloat16、float32、float64 均为浮点类型。int64 是整型，不属于浮点。

### multi_choice · None



- [A] .to(torch.float64) 返回新张量，不改变原张量
- [B] .float() 是 .to(torch.float32) 的便捷写法
- [C] .long() 可将浮点张量转换为 int64，会截断小数
- [D] dtype 转换会改变张量的 shape
- [E] .half() 转换为 float16

**参考答案**：[0, 1, 2, 4]

**解析**：dtype 转换只改变元素类型，不改变 shape。.float()、.long()、.half() 分别是 float32、int64、float16 的便捷方法。

### multi_choice · None



- [A] 需要较大动态范围以避免上溢时
- [B] 对数值精度要求极高、需要极多位尾数时
- [C] 在支持 bfloat16 的硬件上做混合精度训练时
- [D] 希望与 float32 有相同的指数位表示范围时
- [E] 需要精确表示小数后很多位时

**参考答案**：[0, 2, 3]

**解析**：bfloat16 指数位与 float32 相同，范围大，适合避免上溢并在支持它的硬件上做混合精度训练。但它尾数少，精度低，不适合需要极高精度或很多小数位的场景。

### multi_choice · None



- [A] 作为布尔掩码进行索引选择
- [B] 布尔索引的结果是原张量的子集
- [C] torch.bool 张量可以直接参与常规矩阵乘法
- [D] 可用于条件判断，如 torch.where
- [E] 布尔张量在逻辑运算中可用 &、| 等

**参考答案**：[0, 1, 3, 4]

**解析**：bool 用于掩码、布尔索引、torch.where 以及逻辑运算。常规矩阵乘法需要数值类型，bool 直接做 matmul 会报错。

### multi_choice · None



- [A] tensor.dtype 属性查询
- [B] tensor.to(dtype) 转换
- [C] tensor.type(dtype) 转换
- [D] tensor.cuda() 转换 dtype
- [E] tensor.float() 转 float32

**参考答案**：[0, 1, 2, 4]

**解析**：dtype 查询用 .dtype，转换可用 .to、.type、.float 等。.cuda() 只迁移设备，不改变 dtype。

### fill_blank · None



**参考答案**：["torch.float32", "float32"]

**解析**：由 Python 浮点数构成的张量默认推断为 torch.float32。

### fill_blank · None



**参考答案**：["不能", "no"]

**解析**：.to(dtype) 是 out-of-place 操作，返回新张量，不会就地修改原张量。

### code_reading · None



**参考答案**：torch.int64
torch.float32

**解析**：x 由整数列表创建，dtype 为 torch.int64。.to(torch.float32) 返回新张量 y，dtype 为 torch.float32，x 本身不变。

### scenario · None



**解析**：bfloat16 指数位与 float32 相同，动态范围大，更适合避免上溢/下溢；float16 精度（尾数）更高但范围小。选择需权衡硬件是否支持 bfloat16 以及精度需求。若硬件支持 bfloat16 且更关注范围稳定性，可选 bfloat16；否则在支持 float16 且精度更重要时可选 float16。

### single_choice · None



- [A] .to(torch.float64) 会就地修改原张量并返回 None
- [B] .to(torch.float64) 返回一个新的张量，原张量 dtype 不变（除非使用 in-place 的 .to_ 之类的方法）
- [C] .type(torch.float64) 会报错，因为 type() 只能查询不能转换
- [D] dtype 转换只能通过 .cuda() 完成

**参考答案**：1

**解析**：.to(dtype) 返回新张量，是 out-of-place 操作，原张量不变。.type() 也可用于转换。.cuda() 是设备迁移不是 dtype 转换。

### single_choice · None



- [A] 都是 torch.float32
- [B] float32 和 int64
- [C] float64 和 int32
- [D] 都是 torch.int64

**参考答案**：1

**解析**：含小数点的 Python 浮点数推断为 torch.float32，Python 整数推断为 torch.int64。

### single_choice · None



- [A] torch.bool 张量可以与 torch.float32 张量直接进行矩阵乘法
- [B] torch.bool 常用于掩码（mask）操作，如布尔索引选择元素
- [C] torch.bool 在内存中每个元素占 8 位，和 int8 一样
- [D] torch.bool 是整数类型的别名

**参考答案**：1

**解析**：torch.bool 张量表示真/假，常用于掩码与布尔索引。它不参与常规算术矩阵乘法（会报错或需要转换）。bool 一般占 1 字节但语义上只有 True/False。

### single_choice · None



- [A] x.to(torch.int64)
- [B] x.long().to(torch.float32)
- [C] x.round_() 后再 x.to(torch.bool)
- [D] x.astype(torch.int64)

**参考答案**：0

**解析**：x.to(torch.int64) 将浮点转整数，会截断小数部分（向零取整）。PyTorch 没有 astype 方法（那是 NumPy 的）。

### single_choice · None



- [A] 返回 float64 的新张量，原张量不变
- [B] 就地修改为 float64 并返回自身
- [C] 返回 float32 张量（double 无效）
- [D] 抛出运行时错误

**参考答案**：0

**解析**：.double() 等价于 .to(torch.float64)，返回新张量，原张量 dtype 不变。

### single_choice · None



- [A] bfloat16 有比 float16 更多的尾数位但更少的指数位
- [B] bfloat16 与 float16 都是 16 位，bfloat16 指数位更多、数值范围更大但精度更低
- [C] float16 的动态范围比 float32 还大
- [D] float16 与 bfloat16 可以无损互转

**参考答案**：1

**解析**：bfloat16 和 float16 都占 16 位。bfloat16 的指数位与 float32 相同（8 位），范围大但尾数精度低；float16 尾数多但范围小。二者不能无损互转。

### single_choice · None



- [A] 分别为 int64 和 float32
- [B] 分别为 int32 和 float32
- [C] 分别为 int64 和 float64
- [D] 分别为 int32 和 float64

**参考答案**：0

**解析**：整数列表推断为 torch.int64，浮点列表推断为 torch.float32。

### single_choice · None



- [A] torch.set_default_dtype(torch.float64) 会影响后续用浮点创建的张量，但通常不建议随意更改
- [B] set_default_dtype 只能接受整型
- [C] 设置默认 dtype 没有任何副作用
- [D] 默认 dtype 一旦设置不可更改

**参考答案**：0

**解析**：torch.set_default_dtype 可改变后续浮点张量创建的默认类型，但全局更改会影响整个程序，需谨慎。
