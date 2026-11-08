# s1u3l3 40 分钟讲义：Python 的 for 循环与 range() / 让循环同时拿到「第几个」和「是什么」

> 来源 `content/lessons/s1u3l3.json`

## py.flow.for_range

# 40 分钟讲义：Python 的 for 循环与 range()

> 知识点 ID：`py.flow.for_range`　|　课程：s1u3l3　|　前置：无

## 一句话直觉

**`for` 循环是 Python 里「把一件事重复做 N 遍」的最标准写法，而 `range()` 是它最常见的搭档——一个负责『反复执行』，一个负责『生成一串整数编号』。**

学会了这一对，你就能：遍历列表、按索引访问、生成序列、写累加器、做批量数据处理——这是后面所有算法与 AI 工程代码的语法地基。

---

## 第 1 节　什么是 for 循环？

**`for` 循环（for loop）**：把一段代码块重复执行，每一次从「可迭代对象（iterable）」中取出一个元素。

**可迭代对象（iterable）**：能被逐个取元素的东西，比如字符串、列表、元组、`range` 对象。

Python 的 `for` 写法是 `for 变量 in 可迭代对象:`，**不需要**手动维护下标。

```python
# 例 1：按「元素」直接遍历，这是 Python 最地道的写法
fruits = [\"apple\", \"banana\", \"cherry\"]
for fruit in fruits:          # 每轮 fruit 依次等于列表里的一个元素
    print(fruit)
# 输出: apple / banana / cherry

# 例 2：遍历字符串（字符串也是可迭代对象）
for ch in \"abc\":
    print(ch)
# 输出: a / b / c
```

**关键结论**：只要对象是 iterable，就能用 `for ... in ...`。这就是 `for` 的通用能力。

---

## 第 2 节　range()：生成整数序列

很多时候我们不是想遍历已存在的数据，而是想「重复 N 次」或者「用 0,1,2,... 做下标」。这时用 **`range()`**。

`range()` 返回一个惰性序列（lazy sequence），只有真正迭代时才产生整数，内存开销极小。三种形态：

- `range(stop)` → `0, 1, ..., stop-1`
- `range(start, stop)` → `start, ..., stop-1`
- `range(start, stop, step)` → 按 `step` 步长走

```python
# range(stop)：0 到 stop-1，不含 stop
for i in range(3):
    print(i)            # 0 1 2

# range(start, stop)
for i in range(2, 5):
    print(i)            # 2 3 4

# range(start, stop, step)：步长可为负
for i in range(10, 0, -2):
    print(i)            # 10 8 6 4 2

# 常用：用 range 生成下标，配合索引访问列表
nums = [10, 20, 30]
for i in range(len(nums)):
    print(i, nums[i])   # 0 10 / 1 20 / 2 30
```

**关键结论**：`range` 的区间是**左闭右开**（`start` 取得到，`stop` 取不到），这是 Python 里最统一的约定。

---

## 第 3 节　for 循环里的三个控制关键字：break / continue / else

循环不只有「老老实实跑完」，还有中途干预的语法。

- **`break`**：立刻跳出整个循环。
- **`continue`**：跳过本轮剩余代码，进入下一轮。
- **`for ... else`**：如果循环**没有被 break 中断**，就执行 `else` 块。

```python
# break：找到 3 就不找了
for i in range(10):
    if i == 3:
        break
    print(i)            # 0 1 2

# continue：跳过偶数
for i in range(6):
    if i % 2 == 0:
        continue
    print(i)            # 1 3 5

# for...else：没被 break，算作「完整跑完」
for i in range(5):
    if i == 100:
        print(\"found\")
        break
else:
    print(\"no break happened\")   # 会打印这一行
```

**关键结论**：`for...else` 不是「否则」，它是「循环正常结束才执行」，常见于「查找不到就报错」的场景。

---

## 第 4 节　常见组合与惯用法（idiomatic patterns）

工程里，`for` + `range` 往往和以下模式一起出现：

1. **累加器（accumulator）**：用一个变量把每轮结果累积起来。
2. **枚举（enumerate）**：需要下标又需要元素时比 `range(len(...))` 更 Pythonic。
3. **嵌套循环（nested loop）**：二维数据、乘法表、矩阵遍历。
4. **推导式（comprehension）**：把简单 for 循环压成一行。

```python
# 1. 累加器：1 到 100 求和
total = 0
for i in range(1, 101):
    total += i
print(total)              # 5050

# 2. enumerate：同时拿到下标和元素，比 range(len(...)) 更清晰
for idx, fruit in enumerate([\"a\", \"b\", \"c\"]):
    print(idx, fruit)

# 3. 嵌套循环：打印 3x3 乘法表片段
for i in range(1, 4):
    for j in range(1, 4):
        print(i * j, end=\" \")
    print()

# 4. 推导式：等价于「建一个 0..4 的平方列表」
squares = [x * x for x in range(5)]
print(squares)            # [0, 1, 4, 9, 16]
```

**关键结论**：Python 提倡「遍历元素本身」，`range(len(...))` 只有在「真的需要下标」时才用；能用 `enumerate` 或推导式就别硬套 `range`。

---

## 第 5 节　快速对照与易错点地图

| 写法 | 含义 | 提示 |
|---|---|---|
| `for x in seq:` | 遍历元素 | 最地道 |
| `for i in range(n):` | 重复 n 次 / 取 0..n-1 | 不含 n |
| `for i in range(a, b):` | a..b-1 | 左闭右开 |
| `for i in range(a, b, s):` | 步长 s | s 可为负 |
| `break` | 立即退出循环 | 只退最内层 |
| `continue` | 跳过本轮 | 剩下的本轮代码不执行 |
| `for...else` | 未 break 才走 else | 不是\"否则\" |

---

## 动手练习（本地完成）

**任务：写一个 FizzBuzz（经典面试题），用本课学的 for + range + 条件控制完成。**

要求：
1. 用 `for i in range(1, 21):` 遍历 1 到 20。
2. 如果是 3 的倍数 → 打印 `Fizz`。
3. 如果是 5 的倍数 → 打印 `Buzz`。
4. 同时是 3 和 5 的倍数 → 打印 `FizzBuzz`。
5. 其余情况打印数字本身。
6. **进阶**：写完后用列表推导式改写为一行，把结果存进一个 `result` 列表。

参考输出开头：`1, 2, Fizz, 4, Buzz, Fizz, 7, 8, Fizz, Buzz, 11, Fizz, 13, 14, FizzBuzz, ...`

> 提示：先处理最特殊的条件（同时被 3 和 5 整除），再处理一般条件，否则会被覆盖。

```python
# -*- coding: utf-8 -*-
"""py.flow.for_range 综合示例：for 循环 + range() 全形态演示。

直接运行本文件即可看到每段输出；可逐段注释验证。
"""

# --- 1) 遍历可迭代对象本身（最地道） ---
fruits = ["apple", "banana", "cherry"]
for fruit in fruits:
    print("fruit:", fruit)

# --- 2) range 三种形态 ---
for i in range(3):              # 0,1,2
    print("range(stop):", i)
for i in range(2, 5):           # 2,3,4
    print("range(start, stop):", i)
for i in range(10, 0, -2):      # 10,8,6,4,2
    print("range(step):", i)

# --- 3) break / continue / else ---
for i in range(10):
    if i == 3:
        break
    print("before break:", i)

for i in range(6):
    if i % 2 == 0:
        continue
    print("odd only:", i)

for i in range(5):
    if i == 100:
        print("found")
        break
else:
    print("no break -> else branch")

# --- 4) 累加器 + enumerate + 嵌套 + 推导式 ---
total = 0
for i in range(1, 101):         # 1..100 求和
    total += i
print("sum 1..100 =", total)

for idx, fruit in enumerate(fruits):
    print("enumerate:", idx, fruit)

for i in range(1, 4):           # 3x3 表
    for j in range(1, 4):
        print(i * j, end=" ")
    print()

squares = [x * x for x in range(5)]
print("squares =", squares)     # [0, 1, 4, 9, 16]

# --- 5) 练习参考实现：FizzBuzz ---
for i in range(1, 21):
    if i % 15 == 0:
        print("FizzBuzz")
    elif i % 3 == 0:
        print("Fizz")
    elif i % 5 == 0:
        print("Buzz")
    else:
        print(i)
```

## py.flow.enumerate

# py.flow.enumerate：让循环同时拿到「第几个」和「是什么」

> **一句话直觉**：当你既想知道「这是第几个元素」，又想知道「这个元素是什么」时，不要再自己维护计数器——`enumerate()`（枚举）一行就够。

---

## 0. 为什么需要 enumerate？

在 Python 里遍历一个列表非常自然：

```python
fruits = ["apple", "banana", "cherry"]
for fruit in fruits:
    print(fruit)
```

但很多时候你不仅需要元素，还需要它的**下标（index）**。例如打印带编号的菜单：

```
1. apple
2. banana
3. cherry
```

零基础时最常见的写法是「自己维护一个计数器」：

```python
fruits = ["apple", "banana", "cherry"]
i = 0
for fruit in fruits:
    print(i, fruit)
    i += 1
```

能跑，但有两个问题：

1. **啰嗦**：每次循环都要小心维护 `i`，容易忘写 `i += 1` 或写错位置。
2. **容易出 bug**：一旦循环里有 `continue`、`break`、异常，计数逻辑很容易漏掉或重复。

`enumerate()` 就是为这个场景设计的：它把「可迭代对象（iterable）」包装成一个新的迭代器（iterator），每次产出 `(下标, 元素)` 的二元组（tuple）。

---

## 1. 基本用法：一行拿到下标 + 元素

`enumerate(iterable, start=0)`：

- `iterable`：任何可迭代对象，例如列表、字符串、元组、文件对象等。
- `start`：索引起始值，默认是 `0`，可以改成 `1` 让它更符合人类习惯。

```python
# 示例 1：最基础的 enumerate 用法
fruits = ["apple", "banana", "cherry"]

for index, fruit in enumerate(fruits):
    print(index, fruit)
# 输出：
# 0 apple
# 1 banana
# 2 cherry
```

上面这行 `for index, fruit in enumerate(fruits):` 体现了 Python 的**元组解包（tuple unpacking）**：每次迭代得到 `(index, fruit)`，直接拆成两个变量。等价于：

```python
for pair in enumerate(fruits):
    index, fruit = pair
    print(index, fruit)
```

**关键结论**：`enumerate` 返回的是一个迭代器，每次产出的是 `(index, item)`，所以自然可以用两个变量接收。

---

## 2. 改变起始编号：`start` 参数

很多业务里编号要从 `1` 开始（例如「第 1 名、第 2 名」），不要用 `index + 1` 这类手工偏移，直接用 `start=1`。

```python
# 示例 2：start 参数，让编号从 1 开始
fruits = ["apple", "banana", "cherry"]

for rank, fruit in enumerate(fruits, start=1):
    print(f"第 {rank} 名：{fruit}")
# 输出：
# 第 1 名：apple
# 第 2 名：banana
# 第 3 名：cherry
```

`start` 可以是任意整数，甚至是负数：

```python
# 示例 3：start 为负数
for i, ch in enumerate("abc", start=-1):
    print(i, ch)
# 输出：
# -1 a
# 0 b
# 1 c
```

**关键结论**：`start` 只影响编号，不影响遍历顺序和元素本身；它默认是 `0`。

---

## 3. 与常见场景结合：字典、字符串、文件、生成器

`enumerate` 不关心对象是什么类型，只要它是**可迭代的（iterable）**。

```python
# 示例 4：字符串、字典、生成器都能用

# 4.1 遍历字符串
for i, ch in enumerate("Py", start=1):
    print(i, ch)
# 输出：
# 1 P
# 2 y

# 4.2 遍历字典（默认遍历 key）
scores = {"alice": 90, "bob": 85}
for i, name in enumerate(scores):
    print(i, name)
# 输出：
# 0 alice
# 1 bob

# 4.3 遍历生成器表达式（惰性求值）
squares = (x * x for x in range(3))
for i, sq in enumerate(squares):
    print(i, sq)
# 输出：
# 0 0
# 1 1
# 2 4
```

**关键结论**：`enumerate` 是「迭代器包装器」，几乎可以包装任何可迭代对象；它自身也是惰性的（lazy），不会一次性把所有元素算出来。

---

## 4. 工程级用法：同时拿下标和值做判断、构建索引、行号日志

在真实项目里，`enumerate` 常出现在这些地方：

### 4.1 找到第一个满足条件的元素位置

```python
# 示例 5：找第一个负数
numbers = [3, 5, -1, 7, -2]
for i, n in enumerate(numbers):
    if n < 0:
        print(f"第一个负数是 {n}，位置 {i}")
        break
# 输出：第一个负数是 -1，位置 2
```

### 4.2 构建「值 → 位置」的映射

```python
# 示例 6：构建索引字典
words = ["a", "b", "c"]
pos = {word: i for i, word in enumerate(words)}
print(pos)  # {'a': 0, 'b': 1, 'c': 2}
```

### 4.3 处理文件行号（日志、报错定位）

```python
# 示例 7：读取文件并带上行号
# 假设本地有一个 data.txt，内容为三行文本
with open("data.txt", "r", encoding="utf-8") as f:
    for line_no, line in enumerate(f, start=1):
        # line 末尾通常带 \n，用 rstrip 去掉
        print(f"Line {line_no}: {line.rstrip()}")
```

**关键结论**：凡是「需要下标 + 元素」的场景，第一反应应该是 `enumerate`，而不是手动维护 `i`。

---

## 5. 什么时候不该用 enumerate？

`enumerate` 不是万能的：

1. **只需要元素时**：直接 `for x in xs:`；加 `enumerate` 是噪音。
2. **需要同时遍历多个序列时**：用 `zip(a, b)`，或者 `zip` 后再 `enumerate`。
3. **需要随机访问下标时**：直接用 `xs[i]`，或者用 `range(len(xs))`（但通常不如 `enumerate`）。
4. **需要「反向带下标」时**：用 `reversed()` 或 `enumerate(reversed(xs))`，不要用 `xs[::-1]` 再 `enumerate`（会复制列表）。

```python
# 示例 8：把 enumerate 和 zip 组合使用
names = ["alice", "bob"]
ages = [30, 25]
for i, (name, age) in enumerate(zip(names, ages), start=1):
    print(f"{i}. {name} 年龄 {age}")
# 输出：
# 1. alice 年龄 30
# 2. bob 年龄 25
```

**关键结论**：`enumerate` 负责「编号」，`zip` 负责「并行」，两者可以叠加使用。

---

## 6. 工程小贴士

- `enumerate` 返回的迭代器是**一次性**的：遍历完就空了，需要再用请重新 `list(...)` 或重新创建。
- 变量命名建议用 `i`、`index`、`idx`、`line_no` 这类有意义的名字，而不是 `a`、`b`。
- `start` 可以是关键字参数，也可以按位置传：`enumerate(xs, 1)` 等价于 `enumerate(xs, start=1)`。
- 与列表推导（list comprehension）结合时非常自然：`[f(i, x) for i, x in enumerate(xs)]`。

---

## 7. 动手练习

**任务：写一个「日志行号 + 关键词定位」小脚本。**

要求：

1. 在本地创建一个文件 `access.log`，写入若干行日志，例如：
   ```
   INFO  user=alice action=login
   WARN  user=bob action=retry
   ERROR user=alice action=checkout
   INFO  user=carol action=login
   ```
2. 写一个 Python 脚本 `scan_log.py`，用 `enumerate` 读取文件并：
   - 打印每一行的行号（从 1 开始）和内容（去掉末尾换行）。
   - 如果该行包含 `ERROR`，额外打印一行 `  --> 第 N 行出现 ERROR`。
3. 最后统计并打印：包含 `ERROR` 的行一共有多少行、分别是哪些行号。

参考输出示例：

```
Line 1: INFO  user=alice action=login
Line 2: WARN  user=bob action=retry
Line 3: ERROR user=alice action=checkout
  --> 第 3 行出现 ERROR
Line 4: INFO  user=carol action=login

共发现 1 行 ERROR，行号：3
```

提示：使用 `with open(..., encoding="utf-8") as f:` 和 `for line_no, line in enumerate(f, start=1):`。

完成后，把 `enumerate` 换成手动维护 `i` 的写法对比一下，感受为什么 `enumerate` 更安全、更清晰。

```python
# 可直接运行：演示 enumerate 的核心用法
fruits = ["apple", "banana", "cherry"]

# 1) 默认从 0 开始
for i, fruit in enumerate(fruits):
    print(i, fruit)

print("---")

# 2) start=1 更符合人类编号习惯
for rank, fruit in enumerate(fruits, start=1):
    print(f"第 {rank} 名：{fruit}")

print("---")

# 3) 与条件判断组合：找第一个负数
numbers = [3, 5, -1, 7, -2]
for i, n in enumerate(numbers):
    if n < 0:
        print(f"第一个负数是 {n}，位置 {i}")
        break

print("---")

# 4) 与字典推导组合：值 -> 位置
words = ["a", "b", "c"]
pos = {word: i for i, word in enumerate(words)}
print(pos)
```


---

## 本课题目

### single_choice · None



- [A] 0 1 2
- [B] 1 2 3
- [C] 0 1 2 3
- [D] 1 2 3 4

**参考答案**：0

**解析**：range(3) 生成 0、1、2，共 3 个数，因此循环体执行 3 次，依次打印 0、1、2。

### single_choice · None



- [A] 3 个
- [B] 4 个
- [C] 5 个
- [D] 1 个

**参考答案**：1

**解析**：range(1, 5) 从 1 开始、到 5 之前结束，包含 1、2、3、4，共 4 个。

### single_choice · None



- [A] abc
- [B] bcd
- [C] abcd
- [D] cde

**参考答案**：0

**解析**：range 从 ord('a') 开始，连续三个整数对应 'a'、'b'、'c'。

### single_choice · None



- [A] 2
- [B] 0
- [C] 1
- [D] 10

**参考答案**：0

**解析**：从 10 开始以步长 -2 递减：10、8、6、4、2；再减 2 得 0，已不在范围内，故最后一个为 2。

### single_choice · None



- [A] [0, 2, 4]
- [B] [2, 4, 6]
- [C] [0, 1, 2]
- [D] [0, 2, 4, 6]

**参考答案**：0

**解析**：i 为 0、1、2，i*2 得到 0、2、4，依次加入列表，结果为 [0, 2, 4]。

### single_choice · None



- [A] 6 个
- [B] 5 个
- [C] 8 个
- [D] 9 个

**参考答案**：0

**解析**：外层执行 2 次，内层每次执行 3 次，共 2×3=6 次打印。

### single_choice · None



- [A] 0 - 2 -
- [B] 0 1 2 3
- [C] 0 2
- [D] - - - -

**参考答案**：0

**解析**：i 为 0、2 时打印数字，i 为 1、3 时打印 '-'，所以是 0 - 2 -。

### single_choice · None



- [A] 1 3 5
- [B] 1 2 3 4 5
- [C] 2 4 6
- [D] 1 4

**参考答案**：0

**解析**：从 1 开始步长为 2：1、3、5；下一个 7 超出范围，故输出 1 3 5。

### single_choice · None



- [A] 包含 0 到 9 共 10 个整数
- [B] 包含 0 到 10 共 11 个整数
- [C] 包含 1 到 9 共 9 个整数
- [D] 包含 0 到 9 共 9 个整数

**参考答案**：0

**解析**：range(0, 10) 从 0 到 10 之前（不含 10），共 10 个整数 0~9。

### single_choice · None



- [A] 抛出 IndentationError
- [B] 正常打印 0 1 2
- [C] 只打印 0
- [D] 无限循环

**参考答案**：0

**解析**：Python 通过缩进确定循环体，print 未缩进会引发 IndentationError。

### single_choice · None



- [A] 3 2 1 Go
- [B] 3 2 1 0 Go
- [C] 1 2 3 Go
- [D] Go 3 2 1

**参考答案**：0

**解析**：range(3, 0, -1) 得到 3、2、1，循环结束后打印 Go，所以是 3 2 1 Go。

### single_choice · None



- [A] 4
- [B] 3
- [C] 5
- [D] 6

**参考答案**：0

**解析**：从 2 开始步长 5：2、7、12、17；再加 5 得 22 超出范围，共 4 次。

### single_choice · None



- [A] 2 5 8
- [B] 2 4 6 8
- [C] 3 6 9
- [D] 2 5 8 11

**参考答案**：0

**解析**：起始为 2，步长为 3，依次得到 2、5、8；再加 3 得 11，已超过 10（不含），停止。

### single_choice · None



- [A] ||0|01|
- [B] |0|01|
- [C] 0|01|2|
- [D] |||

**参考答案**：0

**解析**：i=0 时内层不执行，打印 '|'；i=1 时打印 0，再打印 '|'；i=2 时打印 01，再打印 '|'，合并为 ||0|01|。

### single_choice · None



- [A] range(5, 0, -1)
- [B] range(1, 5)
- [C] range(5, 0)
- [D] range(0, 5, -1)

**参考答案**：0

**解析**：range(start, stop, step) 若要递减必须给负步长；range(5, 0, -1) 得到 5、4、3、2、1。

### single_choice · None



- [A] 0 个
- [B] 1 个
- [C] 2 个
- [D] 会报错

**参考答案**：0

**解析**：range(0) 是空序列，循环体一次都不会执行。

### single_choice · None



- [A] 3
- [B] 4
- [C] 0
- [D] 未定义

**参考答案**：0

**解析**：range(4) 遍历 0、1、2、3，循环结束后 i 保留最后一次迭代的值 3。

### single_choice · None



- [A] 0 2
- [B] 0 1 2
- [C] 1
- [D] 什么也不打印

**参考答案**：0

**解析**：i 为 1 时执行 continue 跳过本次打印，因此只打印 0 和 2。

### single_choice · None



- [A] 0 1 2
- [B] 0 1 2 3
- [C] 0 1 2 3 4
- [D] 3 4

**参考答案**：0

**解析**：i 等于 3 时 break 立即终止整个循环，因此只打印 0、1、2。

### single_choice · None



- [A] 1 4 9
- [B] 1 2 3
- [C] 2 4 6
- [D] 1 4 9 16

**参考答案**：0

**解析**：i 依次为 1、2、3，打印它们的平方：1、4、9。

### single_choice · None



- [A] 1, 11
- [B] 1, 10
- [C] 0, 10
- [D] 10

**参考答案**：0

**解析**：要包括 1 到 10，需 range(1, 11)，stop 为 11 时才能取到 10。

### single_choice · None



- [A] 0 a
  1 b
  2 c
- [B] 1 a
  2 b
  3 c
- [C] a 0
  b 1
  c 2
- [D] 0 a
  0 b
  0 c

**参考答案**：0

**解析**：enumerate 默认从 0 开始计数，依次返回 (索引, 元素) 元组，解包为 i 和 ch，因此输出索引从 0 开始。

### single_choice · None



- [A] 0 a
  1 b
  2 c
- [B] 1 a
  2 b
  3 c
- [C] 1 a
  1 b
  1 c
- [D] 报错，因为第二个位置参数不能直接传整数

**参考答案**：1

**解析**：enumerate 的第二个参数是起始值，start=1 表示计数从 1 开始，因此输出 1 a、2 b、3 c。该参数可以位置传参也可关键字传参。

### multi_choice · None



- [A] enumerate 是内置函数，不需要 import
- [B] enumerate 返回的是迭代器，可以传给 list() 转成列表
- [C] enumerate 的第二个参数用于指定起始计数
- [D] enumerate 会修改原可迭代对象

**参考答案**：[0, 1, 2]

**解析**：enumerate 是内置函数无需导入，返回迭代器，可指定起始值。它不会修改原对象，只是遍历。

### multi_choice · None



- [A] pairs 的值是 [(10, 'a'), (11, 'b')]
- [B] pairs 的值是 [(0, 'a'), (1, 'b')]
- [C] 起始计数被设为 10
- [D] pairs 是一个迭代器，可以反复遍历

**参考答案**：[0, 2]

**解析**：start=10 使计数从 10 开始，因此得到 [(10,'a'),(11,'b')]。list() 转换后 pairs 是列表而非迭代器，可反复遍历。

### multi_choice · None



- [A] 需要在遍历列表的同时获知每个元素的下标
- [B] 需要在遍历字符串时找出某个字符出现的所有位置
- [C] 想对两个等长列表做元素级配对遍历
- [D] 想按索引修改列表中的元素并需要知道当前索引

**参考答案**：[0, 1, 3]

**解析**：enumerate 适用于需要索引与元素的场景（查找位置、按索引修改等）。两列表元素级配对是 zip 的典型用途，不是 enumerate 的强项。

### multi_choice · None



- [A] 对同一个 enumerate 对象重复 for 循环，第二次不会产出元素
- [B] 如果想多次使用，应先转成 list 保存
- [C] enumerate 每次 for 都会自动重置，可以无限次复用
- [D] 迭代器被耗尽后再调用 next() 会抛 StopIteration

**参考答案**：[0, 1, 3]

**解析**：enumerate 返回的迭代器只能消费一次，耗尽后再遍历得到空，耗尽后 next() 抛 StopIteration。需要复用时应转 list。

### fill_blank · None



**参考答案**：["enumerate", "enumerate "]

**解析**：enumerate 正是同时产出索引和元素的函数，填入 enumerate 即可完成解包。

### fill_blank · None



**参考答案**：["start"]

**解析**：enumerate 的起始计数参数名为 start，写成 start=100 即从 100 开始计数。

### code_reading · None



**参考答案**：1:a
2:bb
3:ccc

**解析**：start=1 使计数从 1 开始，配合 f-string 输出 i:w，得到 1:a、2:bb、3:ccc。

### code_reading · None



**参考答案**：0 x
1 y

**解析**：遍历字典默认迭代键，enumerate 因此产出 (索引, 键)。输出 0 x 和 1 y，值是键而不是值，也不是键值对。

### scenario · None



**解析**：把 enumerate 包在生成器上再 list() 会一次性把所有元素读入内存，对大生成器不友好。更好的做法是直接在 for 循环里使用 enumerate，惰性遍历，找到即可 break 返回，不用构建完整列表。

### scenario · None



**解析**：enumerate 返回一次性的迭代器，第一次 for 后即被耗尽，再遍历得到空。若需要多处遍历，可先 `pairs = list(enumerate(data))` 保存，或每次需要时重新调用 enumerate(data)。

### single_choice · None



- [A] 它返回一个列表，元素是 (索引, 元素) 元组
- [B] 它返回一个迭代器，每次产出 (索引, 元素) 元组
- [C] 它返回一个字典，键是索引、值是元素
- [D] 它返回一个字符串，内容是索引和元素拼接

**参考答案**：1

**解析**：enumerate 返回的是一个惰性迭代器对象，每次迭代产出一个 (索引, 元素) 元组，而不是列表或字典，因此不能直接下标访问。

### single_choice · None



- [A] [(0, 'x'), (1, 'y')] 然后 [(0, 'x'), (1, 'y')]
- [B] [(0, 'x'), (1, 'y')] 然后 []
- [C] [] 然后 [(0, 'x'), (1, 'y')]
- [D] 两次都报错，因为 enumerate 不能转 list

**参考答案**：1

**解析**：enumerate 返回迭代器，迭代器只能被消费一次。第一次 list() 耗尽后，第二次再转就得到空列表。

### single_choice · None



- [A] for i in range(len(seq)):
      print(i, seq[i])
- [B] for i, item in enumerate(seq):
      print(i, item)
- [C] i = 0
  for item in seq:
      print(i, item)
      i += 1
- [D] for item, i in enumerate(seq):
      print(i, item)

**参考答案**：1

**解析**：enumerate 直接产出 (索引, 元素)，是同时拿索引和元素的惯用写法。选项 0 虽能工作但更啰嗦；选项 2 容易忘记自增；选项 3 解包顺序反了，i 实际是元素。

### single_choice · None



- [A] 1 b
- [B] 0 a
- [C] 报错，i 和 v 在循环外不可见
- [D] None None

**参考答案**：0

**解析**：Python 的 for 循环变量在循环结束后仍然保留最后一次迭代的值，所以 i 是 1、v 是 'b'。

### single_choice · None



- [A] enumerate 只能用于列表，不能用于字符串或字典
- [B] enumerate 可以作用于任何可迭代对象，包括字符串、列表、生成器
- [C] enumerate 遍历字典时会自动把键值对作为元素返回
- [D] enumerate 必须配合 len() 使用才能得到索引

**参考答案**：1

**解析**：enumerate 接受任意可迭代对象。遍历字典时，迭代的是键（默认行为），元素是键而不是键值对；它不需要 len()。

### single_choice · None



- [A] [2, 3]
- [B] [1, 2]
- [C] ['l', 'l']
- [D] [2, 3, 4]

**参考答案**：0

**解析**：字符串 'hello' 中字符 'l' 出现在索引 2 和 3，列表推导式配合 enumerate 收集满足条件的索引。

### single_choice · None



- [A] 0 1 2
  1 3 4
- [B] 1 1 2
  2 3 4
- [C] 0 (1, 2)
  1 (3, 4)
- [D] 报错，不能同时解包两层

**参考答案**：0

**解析**：enumerate 产出 (索引, (a, b))，外层解包得到索引和元组，再对元组二次解包得到 a、b，输出 0 1 2 和 1 3 4。

### single_choice · None



- [A] start 可以是负数，如 enumerate(seq, start=-1)
- [B] start 只能是 0 或 1
- [C] start 可以是任意整数
- [D] start 可以省略，默认为 0

**参考答案**：1

**解析**：start 可以是任意整数（含负数），并非只能是 0 或 1。因此‘只能是 0 或 1’这一说法错误。
