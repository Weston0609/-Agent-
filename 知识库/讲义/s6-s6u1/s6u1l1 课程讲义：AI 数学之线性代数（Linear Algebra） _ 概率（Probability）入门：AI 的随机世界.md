# s6u1l1 课程讲义：AI 数学之线性代数（Linear Algebra） / 概率（Probability）入门：AI 的随机世界观

> 来源 `content/lessons/s6u1l1.json`

## ai.math.linear_algebra

# 课程讲义：AI 数学之线性代数（Linear Algebra）

## 一句话直觉

**线性代数就是“用矩阵和向量批量处理数据”的语言**：当你的模型有百万参数、一批图像有上千张时，逐元素循环太慢，必须用向量化（vectorization）把计算压缩成矩阵乘法，而线性代数就是描述这套运算的语法。

学完本讲，你会在本地用 Python 跑通从标量、向量、矩阵到特征分解的完整链路，理解为什么神经网络、协同过滤、PageRank 都建立在矩阵之上。

---

## 1. 为什么 AI 工程师必须懂线性代数

### 1.1 从一次“慢查询”说起

假设你用前几节课的 FastAPI 服务返回推荐分数，每个用户要跟 10 万物品算点积。如果用 Python for 循环：

```python
# 慢到不可用
def dot_loop(a, b):
    s = 0
    for i in range(len(a)):
        s += a[i] * b[i]
    return s
```

而用 NumPy（前序知识点里的 `py.data.numpy`）：

```python
import numpy as np
a = np.random.rand(100_000)
b = np.random.rand(100_000)
%time s = a @ b   # 一行代码，底层 BLAS，快几十到上百倍
```

**结论：线性代数的第一个价值是可计算性（computational efficiency）。** 统一成向量、矩阵后，框架可以调用底层 BLAS（Basic Linear Algebra Subprograms）做并行、缓存友好、SIMD 加速。

### 1.2 它在 AI 里出现的位置

- 神经网络一层：`y = W x + b`，其中 `W` 是矩阵，`x` 是向量。
- 注意力（attention）：`softmax(Q Kᵀ / √d) V`，全是矩阵乘。
- 词嵌入（embedding）：查表就是矩阵行切片。
- 降维、推荐、检索：SVD、PCA、余弦相似度。

所以接下来的 4 节按这个顺序走：**向量 → 矩阵 → 矩阵运算 → 分解与应用**。

---

## 2. 向量（Vector）：数据的最小单位

向量是“一列有序的数”。在 AI 里，一条样本、一个词嵌入、一组参数都可以是向量。

### 2.1 创建与形状

```python
import numpy as np
v = np.array([1.0, 2.0, 3.0])   # 一维数组，形状 (3,)
w = np.array([[1.0], [2.0], [3.0]])  # 列向量，形状 (3, 1)
print(v.shape, w.shape)  # (3,) (3, 1)
```

### 2.2 点积（dot product）与相似度

点积定义：`a · b = Σ aᵢbᵢ = |a||b|cosθ`。它同时给出两个信息：**投影长度**和**夹角**。

```python
v = np.array([1.0, 2.0, 3.0])
u = np.array([2.0, 0.0, 1.0])
print(v @ u)              # 5.0
def cos_sim(a, b):
    return a @ b / (np.linalg.norm(a) * np.linalg.norm(b))
print(round(cos_sim(v, u), 4))  # 0.5976
```

**关键结论：余弦相似度（cosine similarity）只看方向，不看长度，因此常用于文本/图像检索。** 注意点积对长度敏感，如果向量被放大 10 倍，点积变大但余弦不变。

### 2.3 范数（norm）

范数是“向量的长度”：

```python
print(np.linalg.norm(v, ord=2))  # L2 范数 sqrt(14)=3.7417
print(np.linalg.norm(v, ord=1))  # L1 范数 6.0
print(np.linalg.norm(v, ord=np.inf))  # L∞ 范数 3.0
```

工程里正则化（regularization）就是给损失函数加 L1/L2 范数项。

---

## 3. 矩阵（Matrix）：批量线性变换

矩阵可以看作“一组向量”，也可以看作“一个线性变换（linear transformation）”。

### 3.1 形状与切片

```python
A = np.arange(12).reshape(3, 4)  # 3 行 4 列
print(A.shape)          # (3, 4)
print(A[1, 2])          # 6
print(A[:, 1])          # 第 2 列
print(A[1, :])          # 第 2 行
```

**工程约定：** 机器学习常写成 `X` 形状 `(n_samples, n_features)`，神经网络权重 `W` 形状 `(out_features, in_features)`。

### 3.2 矩阵乘向量：一层线性层

```python
W = np.random.randn(5, 3)   # 把 3 维映射到 5 维
y = W @ np.array([1.0, 2.0, 3.0])
print(y.shape)              # (5,)
```

这就是 `nn.Linear(3, 5)` 的底层。

### 3.3 矩阵乘矩阵

`(m, k) @ (k, n) -> (m, n)`，内维必须一致：

```python
A = np.random.randn(4, 3)
B = np.random.randn(3, 2)
print((A @ B).shape)   # (4, 2)
```

**常见误区提前说：** `A * B` 是逐元素乘（element-wise，也叫 Hadamard 积），要求形状相同；`A @ B` 才是矩阵乘。两者完全不同。

---

## 4. 矩阵运算：逆、转置与线性方程组

### 4.1 转置（transpose）

```python
A = np.arange(6).reshape(2, 3)
print(A.T.shape)   # (3, 2)
```

转置在注意力中让 `K` 变成 `Kᵀ` 以便跟 `Q` 做内积。

### 4.2 逆矩阵（inverse）与求解

方阵 `A` 如果满秩，就有逆 `A⁻¹`，满足 `A A⁻¹ = I`。但工程上**不要显式求逆**，而是用 `solve`：

```python
A = np.array([[3.0, 1.0], [1.0, 2.0]])
b = np.array([9.0, 8.0])
x_bad = np.linalg.inv(A) @ b     # 可行但数值不稳
x_ok = np.linalg.solve(A, b)     # 推荐
print(np.allclose(x_bad, x_ok))  # True
```

**结论：`solve` 用分解法（LU 等）更快更稳，求逆只在理论推导或需要完整逆矩阵时用。**

### 4.3 秩（rank）与奇异（singular）

```python
A = np.array([[1.0, 2.0], [2.0, 4.0]])
print(np.linalg.matrix_rank(A))  # 1，第二行是第一行的 2 倍
# np.linalg.solve(A, [1, 2])     # 会抛 LinAlgError: singular matrix
```

线性相关（linearly dependent）导致矩阵奇异，线性方程组无唯一解，这在训练里表现为特征冗余、梯度消失。

---

## 5. 特征分解与应用：PCA、SVD 与降维

### 5.1 特征值/特征向量（eigenvalue/eigenvector）

对方阵 `A`，若 `A v = λ v`，则 `v` 是特征向量，`λ` 是特征值。含义是：**线性变换不改变 v 的方向，只按 λ 缩放。**

```python
A = np.array([[2.0, 0.0], [0.0, 3.0]])
vals, vecs = np.linalg.eig(A)
print(vals)          # [2. 3.]
print(vecs)          # 单位坐标轴
```

### 5.2 奇异值分解（SVD）：任意矩阵都能用

`A = U Σ Vᵀ`。SVD 不要求方阵、不要求可逆，是推荐、压缩、PCA 的核心。

```python
A = np.random.randn(5, 3)
U, S, Vt = np.linalg.svd(A, full_matrices=False)
print(U.shape, S.shape, Vt.shape)  # (5, 3) (3,) (3, 3)
# 用前两个奇异值重建，做低秩近似
k = 2
A_approx = U[:, :k] @ np.diag(S[:k]) @ Vt[:k, :]
print(np.linalg.norm(A - A_approx))  # 残差
```

### 5.3 PCA：用 SVD 做降维

PCA（Principal Component Analysis）就是把数据中心化后做 SVD，取前 k 个方向。

```python
def pca(X, k):
    X = X - X.mean(axis=0)          # 中心化
    U, S, Vt = np.linalg.svd(X, full_matrices=False)
    return X @ Vt[:k, :].T          # 投影到前 k 个主成分

X = np.random.randn(100, 5)
Z = pca(X, 2)
print(Z.shape)  # (100, 2)
```

**关键结论：** 在 AI 里，embedding 降维、推荐中的矩阵分解、检索中的低秩近似，都能统一到 SVD/PCA 这套语言下。

---

## 6. 工程收尾：性能与数值稳定性清单

- 用 `@` / `np.matmul`，别用 `np.dot` 混多维语义。
- 避免显式 `inv`，优先 `solve` / `lstsq`。
- 形状对齐是 90% 的 bug 来源，打印 `.shape` 比 print 值更有效。
- 用 `float32`/`float64` 区分场景，深度学习常用 `float32`。
- 大矩阵分块（blocking）、批处理（batching）能显著减少内存峰值。

```python
import numpy as np

def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """余弦相似度：只看向量方向，忽略长度"""
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12))

def linear_layer(W: np.ndarray, x: np.ndarray, b: np.ndarray) -> np.ndarray:
    """一层线性变换 y = Wx + b，对应 nn.Linear"""
    return W @ x + b

def pca(X: np.ndarray, k: int) -> np.ndarray:
    """用 SVD 实现 PCA 降维，返回 (n_samples, k)"""
    Xc = X - X.mean(axis=0)
    U, S, Vt = np.linalg.svd(Xc, full_matrices=False)
    return Xc @ Vt[:k, :].T

def main() -> None:
    # 1) 向量与相似度
    v = np.array([1.0, 2.0, 3.0])
    u = np.array([2.0, 0.0, 1.0])
    print("cos_sim:", round(cosine_similarity(v, u), 4))

    # 2) 矩阵乘向量（一层线性层）
    W = np.random.randn(5, 3)   # 3 -> 5 维
    b = np.zeros(5)
    print("linear out shape:", linear_layer(W, v, b).shape)

    # 3) 解线性方程组（不要显式求逆）
    A = np.array([[3.0, 1.0], [1.0, 2.0]])
    rhs = np.array([9.0, 8.0])
    print("solve:", np.linalg.solve(A, rhs))

    # 4) SVD 低秩近似
    M = np.random.randn(6, 4)
    U, S, Vt = np.linalg.svd(M, full_matrices=False)
    k = 2
    M_approx = U[:, :k] @ np.diag(S[:k]) @ Vt[:k, :]
    print("low-rank err:", float(np.linalg.norm(M - M_approx)))

    # 5) PCA 降维
    X = np.random.randn(100, 5)
    print("pca shape:", pca(X, 2).shape)

if __name__ == "__main__":
    main()
```

## ai.math.prob

# 概率（Probability）入门：AI 的随机世界观

**一句话直觉**：概率是用来量化“不确定性”的语言；AI 模型几乎都在处理不确定信息，所以概率是 AI 数学的起点。

---

## 1. 为什么 AI 需要概率

AI 系统常常面对不完整信息：图像像素有噪声、用户行为不可完全预测、模型参数不确定。概率让我们用数值表达“某件事发生的可能性”，并用数学规则进行推理与学习。

关键结论：**概率把“可能”变成可计算、可比较、可更新的数。**

```python
# 用一个最简单的例子说明：抛硬币
# 概率 P(正面)=0.5，表示长期重复中正面出现的比例接近一半
import random

random.seed(0)
trials = 10000
heads = sum(random.random() < 0.5 for _ in range(trials))
print(heads / trials)  # 约等于 0.5
```

---

## 2. 样本空间、事件与概率

- 样本空间（sample space）：所有可能结果的集合，记作 \(\Omega\)。
- 事件（event）：样本空间的一个子集。
- 概率（probability）：给事件分配一个 0 到 1 之间的数，且所有可能结果的概率之和为 1。

关键结论：**概率是定义在事件上的函数，满足非负性、归一性和可加性。**

```python
# 掷一个六面骰子：样本空间 {1,2,3,4,5,6}
# 事件 A = 点数为偶数 = {2,4,6}
dice = [1, 2, 3, 4, 5, 6]
event_A = [x for x in dice if x % 2 == 0]

# 等可能模型下：P(A)=|A|/|Omega|
P_A = len(event_A) / len(dice)
print(P_A)  # 0.5
```

---

## 3. 条件概率与独立性

条件概率（conditional probability）\(P(A|B)\) 表示在已知 B 发生的情况下 A 发生的概率。公式：

\[
P(A|B)=\frac{P(A\cap B)}{P(B)}
\]

如果 \(P(A|B)=P(A)\)，就说 A 与 B 独立（independent）。

关键结论：**条件概率是“更新信念”的核心，AI 中大量推理都是条件概率。**

```python
# 一副牌：52 张，4 张 A
# A = 抽到 A，B = 抽到红桃
# P(A|B) = P(A 且 B) / P(B) = (1/52) / (13/52) = 1/13
P_A_and_B = 1 / 52
P_B = 13 / 52
P_A_given_B = P_A_and_B / P_B
print(P_A_given_B)  # 1/13 ≈ 0.0769
```

---

## 4. 随机变量、期望与方差

随机变量（random variable）是把结果映射为数值的函数。

- 期望（expectation）\(E[X]\)：长期平均取值。
- 方差（variance）\(Var(X)\)：取值围绕期望的波动大小。

关键结论：**期望描述“中心”，方差描述“不确定性”。**

```python
# 离散随机变量 X：掷骰子点数
xs = [1, 2, 3, 4, 5, 6]
ps = [1/6] * 6

E_X = sum(x * p for x, p in zip(xs, ps))
Var_X = sum((x - E_X) ** 2 * p for x, p in zip(xs, ps))
print(E_X)    # 3.5
print(Var_X)  # 约 2.9167
```

---

## 5. 从概率到 AI：贝叶斯与最大似然

贝叶斯公式（Bayes' theorem）：

\[
P(H|D)=\frac{P(D|H)P(H)}{P(D)}
\]

- \(P(H)\)：先验（prior）
- \(P(D|H)\)：似然（likelihood）
- \(P(H|D)\)：后验（posterior）

AI 中常见做法：用数据 D 更新对假设 H 的信念。最大似然估计（MLE）则寻找让数据出现概率最大的参数。

关键结论：**概率不仅是描述工具，也是 AI 从数据中学习的数学框架。**

```python
# 简化贝叶斯示例：疾病检测
# 患病率 P(H)=0.01，检测灵敏度 P(D|H)=0.99，误报率 P(D|~H)=0.05
P_H = 0.01
P_not_H = 1 - P_H
P_D_given_H = 0.99
P_D_given_not_H = 0.05

P_D = P_D_given_H * P_H + P_D_given_not_H * P_not_H
P_H_given_D = P_D_given_H * P_H / P_D
print(P_H_given_D)  # 约 0.1667，即使检测阳性，患病概率仍不高
```

---

## 动手练习

**任务**：模拟“两个骰子点数之和”的概率分布。

1. 用 Python 枚举所有 36 种等可能结果。
2. 计算点数之和为 7 的概率。
3. 计算点数之和的期望与方差。
4. 用随机模拟 100000 次验证你的结果。

提示：先构造样本空间 `[(i,j) for i in range(1,7) for j in range(1,7)]`，再统计频数。

```python
import random
from collections import Counter

# 枚举两个骰子的所有结果
outcomes = [(i, j) for i in range(1, 7) for j in range(1, 7)]
sums = [i + j for i, j in outcomes]

# 理论概率：和为 7
p7_theory = sum(1 for s in sums if s == 7) / len(sums)
print("理论 P(和为7):", p7_theory)

# 理论期望与方差
E = sum(sums) / len(sums)
Var = sum((s - E) ** 2 for s in sums) / len(sums)
print("理论期望:", E)
print("理论方差:", Var)

# 随机模拟验证
random.seed(42)
trials = 100000
sim_sums = [random.randint(1, 6) + random.randint(1, 6) for _ in range(trials)]
counter = Counter(sim_sums)
print("模拟 P(和为7):", counter[7] / trials)
print("模拟期望:", sum(sim_sums) / trials)
```


---

## 本课题目

### single_choice · None



- [A] A @ B 合法且结果为 (2,3)，与 A * B 完全相同。
- [B] A @ B 会因维度不匹配而报错，因为矩阵乘法要求左矩阵列数等于右矩阵行数。
- [C] A @ B 合法且结果为 (3,2)，因为会自动转置右矩阵。
- [D] A @ B 合法且结果为标量，因为会自动展平后做点积。

**参考答案**：1

**解析**：矩阵乘法要求 A 的列数等于 B 的行数；A 为 (2,3)、B 为 (2,3) 时 3 != 2，因此会报错。逐元素乘法要求形状相同或可广播。

### single_choice · None



- [A] 点积：标量；外积：(n, n)。
- [B] 点积：(n, n)；外积：标量。
- [C] 点积：标量；外积：(n,)。
- [D] 点积：(n,)；外积：(n, n)。

**参考答案**：0

**解析**：点积把两个向量对应元素相乘再求和，得到标量；外积把 x 的每个元素与 y 的每个元素相乘，得到 n×n 矩阵。

### single_choice · None



- [A] (in,)
- [B] (out,)
- [C] (out, in)
- [D] (in, out)

**参考答案**：1

**解析**：矩阵 (out, in) 与向量 (in,) 相乘，结果维度由矩阵行数决定，为 (out,)。

### single_choice · None



- [A] A 和 B 必须都是方阵。
- [B] A 和 B 形状相同。
- [C] A 和 B 必须都可逆。
- [D] A 和 B 的秩必须相同。

**参考答案**：1

**解析**：矩阵加法要求两个矩阵形状完全一致，逐元素相加。

### single_choice · None



- [A] 秩等于列数。
- [B] 秩小于列数。
- [C] 秩等于行数。
- [D] 秩为 0。

**参考答案**：1

**解析**：列向量线性相关意味着存在非平凡线性组合为零，因此列秩小于列数，即秩小于列数。

### single_choice · None



- [A] β = (X^T X)^{-1} X^T y
- [B] β = X^{-1} y
- [C] β = X^T y
- [D] β = (X X^T)^{-1} y

**参考答案**：0

**解析**：当 X 列满秩时，X^T X 可逆，正规方程给出 β = (X^T X)^{-1} X^T y，这是最小二乘解。

### single_choice · None



- [A] A 可逆。
- [B] A 的秩小于阶数。
- [C] A 是零矩阵。
- [D] A 的特征值全为 1。

**参考答案**：1

**解析**：行列式为 0 说明矩阵不可逆，即不满秩，因此秩小于阶数。零矩阵只是其中一种特殊情况。

### single_choice · None



- [A] Q^T Q = I，且 Q 保持向量长度不变。
- [B] Q 一定是上三角矩阵。
- [C] Q 的行列式一定为 0。
- [D] Q 的列向量一定线性相关。

**参考答案**：0

**解析**：正交矩阵满足 Q^T Q = I，其列向量构成标准正交基，并且对向量做变换时不改变长度。

### single_choice · None



- [A] A 的特征值。
- [B] A 的奇异值，通常非负且按从大到小排列。
- [C] A 的列向量。
- [D] A 的行列式。

**参考答案**：1

**解析**：SVD 中 Σ 的对角元素是奇异值，它们是非负的，并且通常按降序排列。

### single_choice · None



- [A] 正交。
- [B] 共线（或其中一个为零向量）。
- [C] 长度相等。
- [D] 内积为 1。

**参考答案**：1

**解析**：线性相关意味着一向量可由另一向量线性表示，几何上共线；若其中一个为零向量也视为线性相关。

### single_choice · None



- [A] 矩阵所有元素之和。
- [B] 矩阵主对角线元素之和。
- [C] 矩阵的行列式。
- [D] 矩阵的秩。

**参考答案**：1

**解析**：迹是主对角线元素之和，它也等于矩阵所有特征值之和（代数重数计）。

### single_choice · None



- [A] 向量个数等于空间维数且线性无关。
- [B] 向量个数等于空间维数且线性相关。
- [C] 向量两两正交但可以线性相关。
- [D] 向量个数任意，只要张成空间即可。

**参考答案**：0

**解析**：基必须线性无关且能张成整个空间；对于有限维空间，其向量个数等于维数。仅张成空间但线性相关的是生成集，不是基。

### single_choice · None



- [A] 一定有唯一解，因为线性方程组总是可解的。
- [B] 可能无解，也可能有无穷多解，取决于 b 是否在 A 的列空间内。
- [C] 一定有无穷多解，因为奇异矩阵意味着自由变量存在。
- [D] 一定无解，因为奇异矩阵不可逆。

**参考答案**：1

**解析**：奇异矩阵不可逆，因此不能保证唯一解。若 b 不在列空间中则无解；若在列空间中则有无穷多解。

### single_choice · None



- [A] 秩等于矩阵的行数，与列数无关。
- [B] 秩等于矩阵中非零元素的个数。
- [C] 秩等于矩阵行向量组或列向量组中极大线性无关组的向量个数。
- [D] 秩等于矩阵的行列式值。

**参考答案**：2

**解析**：秩刻画的是行（列）向量组的线性无关程度，等于极大线性无关组中向量的个数，也与矩阵对应线性变换像空间的维数一致。

### single_choice · None



- [A] (m, n)
- [B] (n, m)
- [C] (m, m)
- [D] (n, n)

**参考答案**：1

**解析**：转置将行与列互换，因此 (m, n) 矩阵转置后形状为 (n, m)。

### single_choice · None



- [A] 平行
- [B] 正交
- [C] 线性相关
- [D] 相等

**参考答案**：1

**解析**：内积为 0 且均非零，表示两向量夹角为 90 度，即正交。

### single_choice · None



- [A] λv
- [B] λ + v
- [C] v/λ
- [D] λI

**参考答案**：0

**解析**：按定义，特征向量在被矩阵作用后只发生伸缩，不改变方向：Av = λv。

### single_choice · None



- [A] 协方差矩阵特征值最小的特征向量
- [B] 协方差矩阵特征值最大的特征向量
- [C] 数据矩阵的零空间向量
- [D] 任意单位向量

**参考答案**：1

**解析**：PCA 要最大化投影方差，因此选协方差矩阵最大特征值对应的特征向量作为主成分方向。

### single_choice · None



- [A] A 一定是方阵且 B 是 A 的逆矩阵。
- [B] A、B 可以不是方阵，但 A 是 B 的左逆。
- [C] A、B 必须都是零矩阵。
- [D] A、B 的行列式都为 0。

**参考答案**：1

**解析**：AB = I 只说明 A 是 B 的左逆（或 B 是 A 的右逆），并不要求二者是方阵；只有方阵时才谈可逆与逆矩阵。

### single_choice · None



- [A] L2 范数是各分量绝对值之和，L1 范数是平方和开根号。
- [B] L2 范数是平方和开根号，L1 范数是各分量绝对值之和。
- [C] 两者完全相同。
- [D] L2 范数只适用于二维向量，L1 范数适用于任意维。

**参考答案**：1

**解析**：L2 范数为欧几里得长度，即平方和开根号；L1 范数为各分量绝对值之和。

### single_choice · None



- [A] 0.50
- [B] 0.67
- [C] 0.80
- [D] 0.57

**参考答案**：2

**解析**：精确率 = TP/(TP+FP) = 40/(40+10) = 0.80。0.67 是召回率 40/60，0.57 是准确率 70/100，0.50 是常见误算。

### single_choice · None



- [A] 模型把大部分正样本都找了出来，但预测为正的样本中很多是错的
- [B] 模型预测为正的样本几乎都是对的，但漏掉了很多正样本
- [C] 模型的准确率一定等于 0.6
- [D] 模型无法计算 F1 分数

**参考答案**：0

**解析**：高召回低精确意味着漏检少但误报多。B 描述的是高精确低召回，C 的准确率与两者无固定等式，D 错误，F1 可直接计算。

### multi_choice · None



- [A] 方差衡量取值相对于均值的离散程度
- [B] 期望为 0 表示随机变量恒等于 0
- [C] 协方差为正说明两个变量倾向于同向变化
- [D] 方差越大，标准差越小

**参考答案**：[0, 2]

**解析**：方差反映离散程度，协方差为正表示同向变化。期望为 0 不代表恒为 0（如均匀分布 [-1,1]）；标准差是方差的算术平方根，方差越大标准差越大。

### multi_choice · None



- [A] 后验概率 = 似然 × 先验 / 证据
- [B] 先验概率的选取不会影响后验结果
- [C] 当样本量很大时，后验往往由数据主导，对先验不敏感
- [D] 贝叶斯更新可以在观测到新数据后迭代进行

**参考答案**：[0, 2, 3]

**解析**：贝叶斯公式的形式为 后验∝似然×先验；先验会直接影响后验，尤其在小样本下；数据量大时似然项主导；贝叶斯更新天然支持迭代。

### multi_choice · None



- [A] 方差
- [B] 标准差
- [C] 取值范围的极差
- [D] 样本编号的最大值

**参考答案**：[0, 1, 2]

**解析**：方差、标准差、极差都反映离散/不确定性；样本编号最大值只是索引，与分布不确定性无关。

### fill_blank · None



**参考答案**：["相关", "相关系数", "皮尔逊相关", "Pearson"]

**解析**：相关系数是协方差经两变量标准差归一化后的量，无量纲且取值在 [-1,1]。

### fill_blank · None



**参考答案**：["k^2", "k²", "k**2", "k的平方", "k*k"]

**解析**：方差对常数缩放具有平方效应：Var(kX)=k²Var(X)，等价写法如 k²、k^2、k**2 均可接受。

### fill_blank · None



**参考答案**：["0.2", ".2", "0.20"]

**解析**：独立时 P(A∩B)=P(A)·P(B)=0.4×0.5=0.2。0.9 是误用加法公式的结果。

### code_reading · None



**参考答案**：输出 "5 True"。random.random() 返回 [0.0, 1.0) 区间内的浮点数，共生成 5 个，故 len 为 5，all 检查每个值都在 [0,1) 内，恒为 True。

**解析**：random.random() 的语义是返回 [0.0, 1.0) 均匀浮点数，与种子无关，种子只决定具体序列而不影响取值范围和长度。

### code_reading · None



**参考答案**：输出 "3.33 True"。mean 为 (1+2+2+4+5+6)/6 ≈ 3.333，保留两位小数为 3.33；数据并非完全相同，pstdev（总体标准差）严格大于 0，故为 True。

**解析**：statistics.mean 计算算术平均；pstdev 计算总体标准差（分母为 N）。数据有波动，标准差必然大于 0。

### code_reading · None



**参考答案**：输出 0.1995。因为 x=mu，指数部分为 0，exp(0)=1，pdf 化简为 1/(σ√(2π)) = 1/(2×2.5066) ≈ 0.1995。

**解析**：正态分布密度在均值处取最大值 1/(σ√(2π))，本题均值为 10 且 x=10，因此指数项为 1，直接得到常数结果。

### scenario · None



**解析**：降低阈值会使更多样本被判为正类，提高召回率但降低精确率；风控场景中漏检欺诈（FN）代价高，应优先提升召回率，并通过代价矩阵/业务成本量化权衡。

### single_choice · None



- [A] P(A|B) = P(B|A)
- [B] P(A|B) = P(A∩B) / P(B)，当 P(B) > 0
- [C] P(A|B) = P(A) · P(B)
- [D] P(A|B) 一定大于 P(A)

**参考答案**：1

**解析**：条件概率定义为 P(A|B)=P(A∩B)/P(B)（P(B)>0）。对称性只对特定分布成立，乘法公式仅当独立时成立，条件概率可大可小。

### scenario · None



**解析**：切比雪夫不等式不依赖分布形态，仅用均值和标准差给出概率下界，因此对任意分布都成立，虽然较保守但安全；正态近似需要近似正态假设，在偏态或重尾下失效。

### single_choice · None



- [A] Cov(X, Y) = 0
- [B] E(XY) ≠ E(X)E(Y)
- [C] Var(X + Y) = Var(X) − Var(Y)
- [D] P(X = Y) = 1

**参考答案**：0

**解析**：独立可推出协方差为 0（但不相关不一定独立）。B 反了，C 应为 Var(X)+Var(Y)，D 与独立无关。

### single_choice · None



- [A] 99%
- [B] 约 17%
- [C] 约 50%
- [D] 约 1%

**参考答案**：1

**解析**：由贝叶斯公式：P(病|阳)=0.99×0.01/(0.99×0.01+0.05×0.99)≈0.0099/0.0594≈0.167。忽略先验（基率谬误）会误选 99%。

### single_choice · None



- [A] 随机变量取值中出现次数最多的值
- [B] 随机变量各取值按概率加权的平均结果，反映长期重复试验的均值
- [C] 随机变量取值的最大值
- [D] 随机变量取值的中位数

**参考答案**：1

**解析**：期望是概率加权平均，不等于众数、最大值或中位数。

### single_choice · None



- [A] 约 68%
- [B] 至少 75%
- [C] 至少 50%
- [D] 约 95%

**参考答案**：1

**解析**：区间为均值 ± 2 个标准差，切比雪夫不等式给出 1 − 1/k² = 1 − 1/4 = 75%（分布任意）；68%/95% 是正态分布的经验值。

### single_choice · None



- [A] 任何分布中都有 99.7% 的数据落在均值 ± 3 个标准差内
- [B] 对正态分布而言，约 99.7% 的数据落在均值 ± 3 个标准差内
- [C] 正态分布中均值的概率等于 1
- [D] 标准差越大，分布越集中

**参考答案**：1

**解析**：3σ 原则只对正态分布成立；其他分布需借助切比雪夫不等式。连续分布中单点概率为 0，标准差越大分布越分散。

### single_choice · None



- [A] 原假设为真的概率是 0.03
- [B] 在 α=0.05 下结果统计显著，可在原假设下拒绝它
- [C] 该效应一定有实际业务价值
- [D] p 值越小说明效应量一定越大

**参考答案**：1

**解析**：p 值是在原假设为真时观测到当前或更极端结果的概率，不是原假设为真的概率；显著不能等同于有业务价值或效应量大。

### single_choice · None



- [A] 标准化后每个值都变成 1
- [B] 除以 0，导致非法值（inf/NaN）
- [C] 标准化后数据服从正态分布
- [D] 没有任何问题

**参考答案**：1

**解析**：z-score 标准化公式 (x − μ)/σ 中 σ=0 会导致除零错误或无效值，工程中需先检测或跳过常数列。
