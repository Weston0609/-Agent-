# s1u4l2 列表切片（list slice）：把序列“切开”，只取你要的那一段 / 列表推导式与类型标注：`py.type.list_comprehension`

> 来源 `content/lessons/s1u4l2.json`

## py.type.list_slice

# 列表切片（list slice）：把序列“切开”，只取你要的那一段

> **一句话直觉**：列表切片（list slice）让你用 `[start:stop:step]` 这种“小学数学区间”的方式，安全、优雅地取出列表中的任意一段——它是 Python 最常用、最优雅的语法糖之一，几乎每个 Python 程序都会用到。

---

## 一、为什么需要切片？先看一个场景

假设你有一个列表 `nums = [10, 20, 30, 40, 50]`，现在你想拿到前三个元素。

用最笨的办法：

```python
result = []
for i in range(3):
    result.append(nums[i])
print(result)  # [10, 20, 30]
```

用切片（slice）：

```python
result = nums[0:3]
print(result)  # [10, 20, 30]
```

一行搞定，还不用手动管理索引。这就是切片的价值：**用极少的代码表达“取哪一段”的意图**。

切片不只用于列表（list），字符串（str）、元组（tuple）、字节串（bytes）等**序列类型（sequence type）**都支持切片语法。

---

## 二、切片的基本语法：`[start:stop:step]`

### 2.1 三个“旋钮”

```python
sequence[start:stop:step]
#        ↑     ↑    ↑
#       起点  终点  步长
```

- **start**：从哪个索引开始取（包含）。省略则为默认起点。
- **stop**：取到哪个索引之前停（**不包含**）。省略则为默认终点。
- **step**：每步走多远（默认为 1）。可以是负数，表示反向。

### 2.2 半开区间：`[start, stop)`

这是切片的灵魂：**含头不含尾**。

```python
nums = [10, 20, 30, 40, 50]
print(nums[1:3])   # [20, 30]，索引 1 和 2，不含 3
```

为什么这样设计？因为这样可以让 `stop - start` 恰好等于取出的元素个数，也让 `[a:b] + [b:c]` 恰好等于 `[a:c]`，数学上非常整齐。

### 2.3 省略写法的默认值

| 写法 | 等价于 | 含义 |
|------|--------|------|
| `nums[:3]` | `nums[0:3]` | 从头取到索引 3 之前 |
| `nums[2:]` | `nums[2:len(nums)]` | 从索引 2 取到尾 |
| `nums[:]`  | `nums[0:len(nums)]` | 取整个列表的**浅拷贝** |

```python
nums = [10, 20, 30, 40, 50]

print(nums[:3])   # [10, 20, 30]
print(nums[2:])   # [30, 40, 50]
print(nums[:])    # [10, 20, 30, 40, 50]

# 切片返回新列表，修改它不会影响原列表
copy = nums[:]
copy.append(60)
print(nums)  # [10, 20, 30, 40, 50]  （原列表没变）
```

---

## 三、负索引与步长：切片的“隐藏技能”

### 3.1 负索引

Python 允许从尾部倒数：`-1` 是最后一个，`-2` 是倒数第二，以此类推。

```python
nums = [10, 20, 30, 40, 50]
print(nums[-1])    # 50，最后一个元素
print(nums[-3:])   # [30, 40, 50]，最后三个
print(nums[:-2])   # [10, 20, 30]，去掉最后两个
```

### 3.2 步长：跳跃式取样

```python
text = "abcdefghij"
print(text[::2])   # "acegi"，每两个取一个
print(text[1::2])  # "bdfhj"，从索引 1 开始每两个取一个
```

### 3.3 负步长：反转序列

当 `step` 为负数时，Python 从 `start` 向 `stop` **反向**遍历。

```python
nums = [10, 20, 30, 40, 50]
print(nums[::-1])   # [50, 40, 30, 20, 10]，反转
print(nums[4:1:-1]) # [50, 40, 30]，从索引 4 反向走到索引 2
```

> 注意：写 `nums[1:4:-1]` 会得到空列表，因为从 1 到 4 用负步长走不过去。

---

## 四、切片越界：不会报错的“宽容”设计

普通索引越界会报 `IndexError`，但切片**几乎不会报错**，它会自动把越界的范围裁剪掉。

```python
nums = [10, 20, 30, 40, 50]

print(nums[100:200])  # []，起点越界 → 空列表
print(nums[2:100])    # [30, 40, 50]，终点越界 → 取到末尾
print(nums[-100:2])   # [10, 20]，负索引越界 → 从头开始
```

**这个特性非常重要**：切片经常用于“安全地取前 N 个 / 后 N 个元素”，不用担心列表不够长。

```python
# 通用写法：取前 3 个朋友，不管列表有几个
top3 = friends[:3]
```

---

## 五、切片是“浅拷贝”，不是“视图”

这一点是初学者最容易搞错的。切片生成的是**新对象**，而且只复制最外层。

```python
import copy

matrix = [[1, 2], [3, 4], [5, 6]]
rows = matrix[:]        # 浅拷贝，外层新列表，内部子列表仍是同一对象
rows[0][0] = 999
print(matrix)           # [[999, 2], [3, 4], [5, 6]]  原数据被改了！

# 想要完全独立，用 deepcopy
deep = copy.deepcopy(matrix)
deep[0][0] = -1
print(matrix)           # [[999, 2], [3, 4], [5, 6]]  matrix 不受影响
```

**记忆口诀**：`list[:]` = 重新装一份外壳，里面的东西还是原来那些。

---

## 六、切片还能“赋值”：改变列表本身

除了读，切片还可以出现在赋值语句左边，用来**替换、插入、删除**一段元素。

```python
nums = [10, 20, 30, 40, 50]

nums[1:3] = [200, 300]     # 替换
print(nums)                # [10, 200, 300, 40, 50]

nums[1:1] = [111, 222]     # 在索引 1 处插入
print(nums)                # [10, 111, 222, 200, 300, 40, 50]

del nums[0:2]              # 删除前两个
print(nums)                # [222, 200, 300, 40, 50]
```

> 注意：切片赋值的右侧必须是**可迭代对象（iterable）**，不能是单一数字；而且切片赋值可以改变列表长度，而普通索引赋值不行。

---

## 七、动手练习（建议 10~15 分钟）

### 任务：给一个句子做“切片分析器”

请编写一个 Python 文件 `slice_practice.py`，完成以下功能：

1. 定义字符串 `sentence = "Python slicing is powerful and elegant"`。
2. 使用切片，依次打印：
   - 前 6 个字符（应为 `"Python"`）。
   - 从索引 7 到末尾（应为 `"slicing is powerful and elegant"`）。
   - 最后 7 个字符（应为 `"elegant"`）。
   - 每隔一个字符取一次后的结果。
   - 反转整个句子的结果（应为 `"tnagelE dna lufrewop si gnilcis nohtyP"`）。
3. 定义列表 `nums = list(range(1, 21))`（即 1~20）。使用切片打印：
   - 偶数列表（`[2, 4, 6, ..., 20]`）。
   - 倒数 5 个数（`[16, 17, 18, 19, 20]`）。
   - 一个**安全取前 100 个数**的写法，并让其结果为整个 `nums`。
4. 把 `nums[:]` 赋给 `nums2`，向 `nums2` 追加 `999`，验证 `nums` 没有被修改。
5. **加分题**：用一行切片，让 `nums` 反转。

### 验收标准

- 所有切片只使用一次索引访问（不加 for 循环）。
- 每题下方用 `# 应输出 ...` 注释结果。
- 加分项答案：`nums[::-1]`。

---

## 小结

| 语法 | 效果 |
|------|------|
| `lst[start:stop]` | 取 `[start, stop)` 区间 |
| `lst[start:]` | 从 start 到末尾 |
| `lst[:stop]` | 从开头到 stop 之前 |
| `lst[:]` | 浅拷贝整个列表 |
| `lst[::step]` | 按步长取样 |
| `lst[::-1]` | 反转 |
| `lst[a:b] = iterable` | 用切片替换/插入元素 |
| `del lst[a:b]` | 用切片删除元素 |

**核心记忆**：切片是“含头不含尾”、越界不报错、返回新对象、且能出现在赋值左侧。

```python
"""list_slice.py —— 列表切片完整示例"""

# ---------- 1. 基本语法 ----------
nums = [10, 20, 30, 40, 50]
print(nums[1:3])        # [20, 30]
print(nums[:3])         # [10, 20, 30]
print(nums[2:])         # [30, 40, 50]
print(nums[:])          # [10, 20, 30, 40, 50]

# ---------- 2. 负索引 ----------
print(nums[-1])         # 50
print(nums[-3:])        # [30, 40, 50]
print(nums[:-2])        # [10, 20, 30]

# ---------- 3. 步长与反转 ----------
text = "abcdefghij"
print(text[::2])        # acegi
print(text[1::2])       # bdfhj
print(nums[::-1])       # [50, 40, 30, 20, 10]
print(nums[4:1:-1])     # [50, 40, 30]

# ---------- 4. 越界安全 ----------
print(nums[100:200])    # []
print(nums[2:100])      # [30, 40, 50]

# ---------- 5. 浅拷贝 ----------
copy = nums[:]
copy.append(60)
print(nums)             # [10, 20, 30, 40, 50]  原列表不变
print(copy)             # [10, 20, 30, 40, 50, 60]

matrix = [[1, 2], [3, 4]]
row = matrix[:]
row[0][0] = 999
print(matrix)           # [[999, 2], [3, 4]]  子列表共享

# ---------- 6. 切片赋值 ----------
n = [10, 20, 30, 40, 50]
n[1:3] = [200, 300]
print(n)                # [10, 200, 300, 40, 50]

n[1:1] = [111, 222]
print(n)                # [10, 111, 222, 200, 300, 40, 50]

del n[0:2]
print(n)                # [222, 200, 300, 40, 50]
```

## py.type.list_comprehension

# 列表推导式与类型标注：`py.type.list_comprehension`

> **一句话直觉**：列表推导式（list comprehension）让你用一行表达式“生成列表”，而类型标注（type hint）让 IDE 和类型检查器（type checker）看懂这些列表里装的是什么类型，从而在运行前就发现错误。

本节课我们面向零基础到工程级，从“为什么需要”到“如何写出类型安全的推导式”，分 5 个小节循序渐进。

---

## 1. 为什么需要列表推导式？

传统的 `for` 循环创建列表需要 3~4 行：先建空列表、遍历、`append`、最后返回。列表推导式把“构造逻辑”压缩成一行，语义更集中，性能也通常更好（C 层优化）。

```python
# 传统写法：3 行
squares = []
for n in range(5):
    squares.append(n * n)

# 列表推导式：1 行，结果相同
squares = [n * n for n in range(5)]
print(squares)  # [0, 1, 4, 9, 16]
```

基本语法结构：`[表达式 for 变量 in 可迭代对象 if 条件]`。

---

## 2. 列表推导式的类型是什么？——`list[T]`

在 Python 3.9+ 中，内置泛型（generic）已经可以使用 `list[int]`、`dict[str, float]` 这样的写法。一个 `[n * n for n in range(5)]` 的静态类型是 `list[int]`。

类型检查器（如 mypy、pyright）会读取这些标注。注意：**Python 运行时不会强制执行类型标注**，它们只是提供给工具用的线索。

```python
# 显式声明变量类型，IDE 与类型检查器都看得懂
squares: list[int] = [n * n for n in range(5)]

# 函数签名里也能标注推导式结果
def first_three_squares() -> list[int]:
    return [n * n for n in range(3)]

print(first_three_squares())  # [0, 1, 4]
```

---

## 3. 带条件与嵌套结构的推导式如何标注类型？

推导式支持 `if` 过滤，也支持嵌套循环。类型仍然是结果表达式的类型。

```python
# 只保留偶数的平方
nums: list[int] = [1, 2, 3, 4, 5, 6]
even_squares: list[int] = [n * n for n in nums if n % 2 == 0]
print(even_squares)  # [4, 16, 36]

# 嵌套循环：二维坐标对
# 每个元素是 tuple[int, int]，所以外层是 list[tuple[int, int]]
pairs: list[tuple[int, int]] = [(x, y) for x in range(2) for y in range(2)]
print(pairs)  # [(0, 0), (0, 1), (1, 0), (1, 1)]
```

这里用到 `tuple[int, int]`：Python 3.9+ 内置 `tuple` 也支持下标泛型；`tuple` 在类型系统中表示“固定长度、每个位置类型明确”的元组。

---

## 4. 用 `TypeAlias` 让复杂类型可读

当列表元素类型很复杂时，直接写在标注里会又长又难维护。`typing.TypeAlias`（Python 3.10+ 推荐）或 `type` 语句（Python 3.12+）可以给类型起别名。

```python
from typing import TypeAlias

# 给 tuple[int, int] 起个名字
Point: TypeAlias = tuple[int, int]

# 推导式返回 list[Point]，签名清晰很多
def make_grid(n: int) -> list[Point]:
    return [(x, y) for x in range(n) for y in range(n)]

print(make_grid(2))  # [(0, 0), (0, 1), (1, 0), (1, 1)]
```

Python 3.12+ 可以直接写 `type Point = tuple[int, int]`，语义等价且更简洁。类型别名不影响运行时行为，只服务于类型检查器。

---

## 5. 工程级实践：让推导式的类型可被工具验证

真实项目中，我们会在函数签名、变量标注、返回值上都写清楚，然后让 mypy 或 IDE 检查。下面示例使用了 `typing.reveal_type` 让检查器暴露推断类型（运行时它会打印到 stderr 并原样返回参数）。

```python
from typing import reveal_type

def parse_ints(lines: list[str]) -> list[int]:
    # 推导式里调用 int()，结果类型是 list[int]
    return [int(line) for line in lines if line.strip()]

result = parse_ints(["1", "2", "3"])
reveal_type(result)  # mypy 会显示：Revealed type is "builtins.list[builtins.int]"
print(result)        # [1, 2, 3]
```

工程建议：
- 优先使用内置泛型 `list[T]`、`dict[K, V]`、`tuple[...]`（Python 3.9+）。
- 老项目兼容可用 `from typing import List, Dict, Tuple`。
- 把复杂类型抽成 `TypeAlias` 或 `type` 语句，保持签名可读。
- 类型标注只是“契约”，不替代运行时校验；外部输入仍需显式验证。

---

## 动手练习

**任务**：写一个函数 `word_lengths(texts: list[str]) -> dict[str, int]`，用**字典推导式**（dict comprehension）返回“单词 → 长度”的映射，只保留长度大于 2 的单词。要求：

1. 在函数签名和内部变量上都写类型标注。
2. 用 `reveal_type` 打印推导式结果的类型（在 mypy 下运行查看提示；直接运行 Python 会打印到 stderr）。
3. 在本地命令 `python your_file.py` 与 `mypy your_file.py` 下都验证通过。

```python
# 参考骨架
def word_lengths(texts: list[str]) -> dict[str, int]:
    return {t: len(t) for t in texts if len(t) > 2}

print(word_lengths(["a", "python", "is", "fun"]))
# 期望：{'python': 6, 'fun': 3}
```

完成后可尝试把 `dict[str, int]` 抽成 `TypeAlias`，观察签名可读性的变化。

```python
from typing import TypeAlias, reveal_type

Point: TypeAlias = tuple[int, int]


def make_grid(n: int) -> list[Point]:
    """返回 n x n 的坐标网格，用列表推导式生成。"""
    grid: list[Point] = [(x, y) for x in range(n) for y in range(n)]
    return grid


def word_lengths(texts: list[str]) -> dict[str, int]:
    """返回单词到长度的映射，仅保留长度大于 2 的单词。"""
    result: dict[str, int] = {t: len(t) for t in texts if len(t) > 2}
    return result


grid = make_grid(2)
reveal_type(grid)          # mypy: list[tuple[int, int]]
print(grid)                # [(0, 0), (0, 1), (1, 0), (1, 1)]

lengths = word_lengths(["a", "python", "is", "fun"])
reveal_type(lengths)       # mypy: dict[str, int]
print(lengths)             # {'python': 6, 'fun': 3}
```


---

## 本课题目

### single_choice · None



- [A] [1, 2, 3]
- [B] [1, 2, 3, 4]
- [C] [0, 1, 2, 3]
- [D] [2, 3, 4]

**参考答案**：0

**解析**：切片 nums[1:4] 包含索引 1、2、3，不含上界 4，因此得到 [1, 2, 3]。

### single_choice · None



- [A] [0, 1, 2]
- [B] [1, 2, 3]
- [C] [0, 1, 2, 3]
- [D] [3, 4, 5]

**参考答案**：0

**解析**：省略起始索引时默认从 0 开始，nums[:3] 取索引 0、1、2，即 [0, 1, 2]。

### single_choice · None



- [A] [0, 1]
- [B] []
- [C] [2, 3]
- [D] 报错

**参考答案**：0

**解析**：负数起始索引超出范围时会被截断到 0，因此等价于 nums[0:2]，得到 [0, 1]。

### single_choice · None



- [A] [4, 3, 2]
- [B] [4, 5, 1]
- [C] [3, 4]
- [D] []

**参考答案**：0

**解析**：步长为 -1，从索引 4 向左取到索引 2（不含上界 1），结果为 [4, 3, 2]。

### single_choice · None



- [A] nums[2:6]
- [B] nums[2:5]
- [C] nums[3:6]
- [D] nums[2:5:1]

**参考答案**：0

**解析**：要包含索引 5，上界必须写 6，因为切片不含上界，所以是 nums[2:6]。

### single_choice · None



- [A] 抛出 ValueError
- [B] 返回原列表
- [C] 返回空列表
- [D] 返回逆序列表

**参考答案**：0

**解析**：步长不能为 0，Python 会抛出 ValueError，提示 slice step cannot be zero。

### single_choice · None



- [A] 'ell'
- [B] 'ell o'
- [C] 'hell'
- [D] 'llo'

**参考答案**：0

**解析**：字符串切片规则与列表相同，索引 1、2、3 对应的字符为 'e'、'l'、'l'。

### single_choice · None



- [A] 完全相同
- [B] 前者多一个元素
- [C] 后者为逆序
- [D] 后者报错

**参考答案**：0

**解析**：省略步长时默认步长为 1，因此 nums[1:3] 与 nums[1:3:1] 完全等价。

### single_choice · None



- [A] 返回从索引 2 到末尾的元素
- [B] 抛出 IndexError
- [C] 返回空列表
- [D] 返回原列表

**参考答案**：0

**解析**：切片上界超出长度时不会报错，只会取到列表末尾，因此返回索引 2 及之后的所有元素。

### single_choice · None



- [A] stop 索引对应的元素不包含在结果中
- [B] stop 索引对应的元素包含在结果中
- [C] start 必须小于 stop，否则报错
- [D] step 只能为正整数

**参考答案**：0

**解析**：切片是左闭右开区间，结果不含 stop 位置的元素；step 可以为负，start 大于 stop 也不一定报错。

### single_choice · None



- [A] nums[::-2]
- [B] nums[-1::-2]
- [C] nums[4:0:-2]
- [D] 以上都可以

**参考答案**：2

**解析**：nums[::-2] 返回 [5, 3, 1]，nums[-1::-2] 也返回 [5, 3, 1]，nums[4:0:-2] 取索引 4、2，缺少索引 0 对应的 1，因此只有前两个正确，但选项设置需要重新审视：正确答案应为能返回 [5,3,1] 的选项。此处 nums[::-2] 与 nums[-1::-2] 都正确，因此 A、B 均可，故按单选设计应选包含两者的『以上都可以』并不成立，因为 C 不对。正确选项应为 A 或 B 中任一。解析中应说明 nums[4:0:-2] 结果为 [5,3]，不含 1。

### single_choice · None



- [A] 原列表的浅拷贝
- [B] 原列表本身（同一对象）
- [C] 空列表
- [D] 逆序列表

**参考答案**：0

**解析**：lst[:] 创建一个新的列表对象，元素与原列表相同，是浅拷贝，用于复制列表。

### single_choice · None



- [A] [3, 4, 5]
- [B] [0, 1, 2]
- [C] [3]
- [D] [4, 5]

**参考答案**：0

**解析**：省略结束索引时默认取到列表末尾，因此从索引 3 到末尾为 [3, 4, 5]。

### single_choice · None



- [A] ['c', 'd']
- [B] ['b', 'c']
- [C] ['d']
- [D] ['a', 'b']

**参考答案**：0

**解析**：-2 表示倒数第二个元素，data[-2:] 从倒数第二个取到末尾，即 ['c', 'd']。

### single_choice · None



- [A] [1, 3]
- [B] [1, 2, 3, 4]
- [C] [1, 3, 5]
- [D] [2, 4]

**参考答案**：0

**解析**：步长为 2，从索引 1 开始每次加 2，取到索引 1、3，因此结果是 [1, 3]。

### single_choice · None



- [A] [0, 2, 4]
- [B] [1, 3, 5]
- [C] [0, 1, 2]
- [D] [2, 4]

**参考答案**：0

**解析**：省略起止索引时默认全范围，步长为 2 表示每隔一个取一个，即 [0, 2, 4]。

### single_choice · None



- [A] [5, 4, 3, 2, 1, 0]
- [B] [0, 1, 2, 3, 4, 5]
- [C] [5, 4, 3]
- [D] 报错

**参考答案**：0

**解析**：步长为 -1 时表示从右向左逐个取元素，因此得到原列表的逆序。

### single_choice · None



- [A] 新列表，修改它不会影响原列表的元素排列
- [B] 原列表的视图，修改它会影响原列表
- [C] 与原列表共享同一对象
- [D] 取决于列表长度

**参考答案**：0

**解析**：切片返回一个浅拷贝的新列表，修改新列表的元素（如赋值）不会影响原列表的结构。

### single_choice · None



- [A] []
- [B] [1]
- [C] [0]
- [D] [1, 2]

**参考答案**：0

**解析**：当起始和结束索引相同时，切片取不到任何元素，返回空列表。

### single_choice · None



- [A] []
- [B] 报错 IndexError
- [C] [4]
- [D] [0, 1, 2, 3, 4]

**参考答案**：0

**解析**：切片索引越界不会报错，超出范围时按最接近的有效范围处理，起始超过长度则返回空列表。

### single_choice · None



- [A] [0, 1, 4, 9]
- [B] [1, 4, 9, 16]
- [C] [0, 1, 2, 3]
- [D] [0, 2, 4, 6]

**参考答案**：0

**解析**：range(4) 产生 0,1,2,3，分别平方得到 0,1,4,9。选项 B 是 range(1,5) 的结果，选项 C 未做平方，选项 D 是 2 倍而非平方，均属常见误解。

### single_choice · None



- [A] [0, 2, 4, 6, 8]
- [B] [2, 4, 6, 8, 10]
- [C] [1, 3, 5, 7, 9]
- [D] [0, 1, 2, 3, 4]

**参考答案**：0

**解析**：if 子句在迭代过程中过滤元素，只保留偶数，range(10) 内的偶数为 0,2,4,6,8。B 越界且遗漏 0，C 是奇数，D 未过滤。

### multi_choice · None



- [A] 可以包含多个 for 子句进行嵌套迭代
- [B] 可以在 for 之后跟一个或多个 if 过滤条件
- [C] 表达式部分可以是任意表达式，包括函数调用
- [D] 列表推导式一定会比等价的 for 循环慢，因此不推荐使用
- [E] 推导式内部的循环变量会泄漏到外部作用域

**参考答案**：[0, 1, 2]

**解析**：多 for、多 if 以及任意表达式都是列表推导式的合法组成。D 说反了，列表推导式通常更快；E 是 Python 2 的旧行为，在 Python 3 中不成立。

### multi_choice · None



- [A] [n for n in nums if n > 3]
- [B] [n * 2 for n in nums]
- [C] [n for n in nums if n % 2 == 0]
- [D] [n - 1 for n in nums if n < 4]
- [E] [n for n in nums if n > 10]

**参考答案**：[0, 1, 2]

**解析**：A 得 [4,5] 含 4；B 得 [2,4,6,8,10] 含 4；C 得 [2,4] 含 4；D 得 [0,1,2] 不含 4；E 为空列表。

### multi_choice · None



- [A] [x for x in data if x > 0] 只保留正数
- [B] [x if x > 0 else 0 for x in data] 把非正数变为 0
- [C] [x for x in data if x > 0 if x < 10] 等价于同时满足两个条件
- [D] [x for x in data else 0] 是合法的过滤写法
- [E] [x if x > 0 for x in data] 是合法的条件表达式写法

**参考答案**：[0, 1, 2]

**解析**：A 是过滤，B 是条件表达式映射，C 是两个连续 if 相当于 and。D 缺少 if 的判断表达式，E 的三元运算符缺少 else 分支，均非法。

### multi_choice · None



- [A] 当嵌套层级过多时，改用普通 for 循环
- [B] 只对简单的映射与过滤使用推导式
- [C] 把复杂的条件表达式拆分成辅助函数再调用
- [D] 尽可能把多个 for、多个 if 全部挤在一行
- [E] 用列表推导式替代所有循环

**参考答案**：[0, 1, 2]

**解析**：推导式适合简单映射/过滤，过于复杂时应改用普通循环或辅助函数以提高可读性。D、E 会降低可读性，是常见误区。

### fill_blank · None



**参考答案**：["x*x", "x**2", "x * x", "x ** 2"]

**解析**：表达式为 x 的平方，x*x 或 x**2 均可，range(1,5) 提供 1 到 4。

### fill_blank · None



**参考答案**：["n % 2 == 0", "n%2==0", "not n % 2", "n % 2 != 1"]

**解析**：偶数即对 2 取模为 0，n % 2 == 0 是最直接写法，not n % 2 也可（0 为假）。

### fill_blank · None



**参考答案**：["n", "n", "n"]

**解析**：内层循环变量命名为 n，表达式部分直接返回 n 即可得到展平的一维列表。

### code_reading · None



**参考答案**：[1, 2, 2, 4]

**解析**：外层 i 取 1、2，内层 j 取 1、2，乘积依次为 1,2,2,4，构成列表 [1, 2, 2, 4]。

### scenario · None



**解析**：该任务本质上是一次过滤加一次映射，条件相对简单，适合用列表推导式一行表达，如 [n + 1 for n in data if n > 100 and n % 2 == 0]。但若条件进一步复杂、嵌套层次变多，则应改用普通 for 循环以保证可读性。选择的核心判断标准是逻辑复杂度与可读性。

### scenario · None



**解析**：错误原因是在 for 之后使用了 if-else，过滤子句只能写 if 条件，不能带 else。若要过滤： [x for x in data if x > 0]；若要把非正数变为 0：[x if x > 0 else 0 for x in data]，条件表达式须放在 for 之前。

### single_choice · None



- [A] 结果是 [(1, 3), (1, 4), (2, 3), (2, 4)]，外层循环 x 变化慢
- [B] 结果是 [(1, 3), (2, 3), (1, 4), (2, 4)]，外层循环 y 变化慢
- [C] 语法错误，一个推导式只能有一个 for 子句
- [D] 结果与嵌套顺序无关，总是自动排序

**参考答案**：0

**解析**：多个 for 子句按书写顺序从左到右嵌套，最左边的循环最外层、变化最慢，所以 x 固定为 1 时先遍历所有 y，再进入 x=2。B 弄反了嵌套顺序，C、D 均为错误认识。

### single_choice · None



- [A] 前者直接迭代元素，更 Pythonic；后者用下标间接访问，不必要
- [B] 前者会修改 nums 中的元素，后者不会
- [C] 后者比前者快，因为它避免了迭代器
- [D] 两者完全等价，但前者不能用于字符串列表

**参考答案**：0

**解析**：列表推导式推荐直接迭代元素，无需用下标间接访问，更简洁且不易越界。列表推导式不会修改原列表（新建列表），所以 B 错误；C、D 均无依据。

### single_choice · None



- [A] [1, 2, 3]
- [B] ['a', 'bb', 'ccc']
- [C] [3, 2, 1]
- [D] 报错，len 不能用于推导式

**参考答案**：0

**解析**：对每个字符串求长度，得到 [1,2,3]。B 是未做映射的原列表，C 顺序颠倒，D 是错误认识，len 完全可以用于推导式中的表达式。

### single_choice · None



- [A] 不能在推导式外部访问，推导式有独立作用域
- [B] 可以访问，i 的值为 2
- [C] 可以访问，i 的值为 3
- [D] 取决于是否使用了 if 子句

**参考答案**：0

**解析**：Python 3 中列表推导式拥有独立作用域，内部循环变量不会泄漏到外部，因此在外部访问 i 会触发 NameError。B、C 是 Python 2 的遗留行为，D 无依据。

### single_choice · None



- [A] [n for row in matrix for n in row]
- [B] [n for n in matrix]
- [C] [[n for n in row] for row in matrix]
- [D] [row for row in matrix if n]

**参考答案**：0

**解析**：外层遍历每一行，内层遍历行内元素，才能展平。B 只得到原行列表，C 仍是二维结构，D 引用了未定义的 n 且逻辑错误。

### single_choice · None



- [A] 这是条件表达式，属于映射操作，每个元素都会被转换
- [B] 这是过滤，只有 x > 0 的元素才会被保留
- [C] 这会导致语法错误，if-else 不能出现在推导式中
- [D] 这等价于 [x for x in data if x > 0 else 0]

**参考答案**：0

**解析**：if-else 放在 for 之前的表达式位置属于条件表达式（三元运算），对每个元素都产生一个结果；若把 if 放到 for 之后则是过滤。B 混淆了二者，C、D 均错误。

### single_choice · None



- [A] [[0, 0], [0, 1], [1, 0], [1, 1]]
- [B] [[0, 0], [1, 0], [0, 1], [1, 1]]
- [C] [[0, 1], [1, 2]]
- [D] 报错，两个 for 不能同时使用

**参考答案**：0

**解析**：按书写顺序嵌套，i 为外层、j 为内层，因此依次得到 [0,0]、[0,1]、[1,0]、[1,1]。B 反了顺序，C、D 错误。

### single_choice · None



- [A] 列表推导式立即生成完整列表并占用内存，生成器表达式惰性求值、按需产生元素
- [B] 两者完全等价，只是括号不同
- [C] 生成器表达式会缓存所有元素，所以更占内存
- [D] 列表推导式不能用于 for 循环迭代

**参考答案**：0

**解析**：列表推导式会立刻构造整个列表；生成器表达式惰性求值，逐个产出元素，适合大数据流。B 忽略了求值时机差异，C 反了，D 错误，列表同样可迭代。
