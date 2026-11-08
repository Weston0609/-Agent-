# s1u3l2 `while` 循环：让重复工作交给机器 / Python 中的 `break` 与 `continue`：循环流程控制

> 来源 `content/lessons/s1u3l2.json`

## py.flow.while

# `while` 循环：让重复工作交给机器

## 一句话直觉

**当“某件事还没做完”时，就一遍遍重复做，直到条件不再满足——这就是 `while` 循环（while loop）。** 判断、循环、退出，三者构成了程序自动化的核心。

---

## 1. 为什么需要 `while`：从“复制粘贴”到“自动重复”

假设要打印 1 到 5：

```python
print(1)
print(2)
print(3)
print(4)
print(5)
```

如果要打印 1 到 10000 呢？显然不能手写一万行。程序最擅长的事之一就是**重复执行**。`while` 的语法是：

```python
while 条件表达式:
    循环体
```

它的执行逻辑是：

1. 判断 `条件表达式` 是否为 `True`；
2. 若为 `True`，执行一次循环体，然后回到第 1 步；
3. 若为 `False`，跳过循环体，继续执行后面的代码。

```python
count = 1                      # 初始化计数器
while count <= 5:              # 条件：只要 count 不超过 5
    print(count)               # 循环体
    count += 1                 # 让条件最终会变 False，否则会无限循环
```

**关键结论：`while` 循环里一定要有“让条件最终变为 False”的语句，否则就是死循环（infinite loop）。**

---

## 2. 控制循环节奏：`break`、`continue` 与 `else`

有时候条件本身不够表达“何时退出”，我们需要更细粒度的控制：

- **`break`**：立刻终止整个循环；
- **`continue`**：跳过本次剩余循环体，直接进入下一次条件判断；
- **`while ... else`**：只有当循环**自然结束**（条件变 False，没有被 `break` 打断）时才执行 `else`。

```python
n = 0
while n < 10:
    n += 1
    if n == 3:
        continue     # 跳过打印 3，但循环继续
    if n == 6:
        break        # 遇到 6 直接结束循环
    print(n)         # 输出 1 2 4 5
else:
    print("循环自然结束")   # 因为被 break 打断，这行不会执行
```

**关键结论：`break` 是“跳出循环”，`continue` 是“跳过这一轮”，`else` 是“没有被打断时的收尾”。**

---

## 3. 典型模式：计数器、累加器、哨兵值

工程中 `while` 最常见的三种用法：

### 3.1 计数器循环

```python
i = 0
while i < 3:
    print(f"第 {i + 1} 次")
    i += 1
```

### 3.2 累加/累乘

```python
total = 0
k = 1
while k <= 100:
    total += k
    k += 1
print(total)   # 5050
```

### 3.3 哨兵值循环（sentinel loop）

当不知道循环次数，只知道“遇到某个特殊值就停”时，用哨兵值（sentinel）。

```python
while True:
    user_input = input("输入数字（输入 q 退出）：")
    if user_input == "q":
        break
    number = int(user_input)
    print(number * 2)
```

**关键结论：`while True` + `break` 是处理“不确定循环次数”场景最自然的写法。**

---

## 4. 与 `for` 的关系，以及选择原则

`while` 与 `for` 都能做重复，但**选择依据是“你知道重复次数吗？”**：

- 知道遍历对象或次数 → 优先 `for`（更简洁、更安全）；
- 只知道“条件满足就继续” → 用 `while`（更能表达意图）。

```python
# 用 for 打印 1..5
for i in range(1, 6):
    print(i)

# 用 while 打印 1..5
i = 1
while i <= 5:
    print(i)
    i += 1
```

两者在大多数可数场景下等价，但 `while` 更适合“循环条件本身是业务逻辑”的场景，例如“只要服务器未就绪就继续等待”。

---

## 5. 工程级注意点

在真实项目里，`while` 循环要注意以下几点：

1. **防止死循环**：条件变量一定要在循环体内被修改，或使用 `break` 有明确出口；
2. **超时保护**：等待型循环要加最大等待时间，避免程序卡死；
3. **优先使用条件判断而非 `== True/False`**：判断布尔表达式时直接 `if greeting:`，不要写 `if greeting == True:`，后者是可读性差的反模式；
4. **避免在 `finally` 里用 `return/break/continue`**：会吞掉正在传播的异常；
5. **空序列判断**：对于字符串、列表、元组等，直接用真值判断（`if not seq:`），不要用 `len(seq)`。

```python
# 带超时保护的等待循环（模拟）
import time
start = time.time()
timeout = 2.0
ready = False
while not ready:
    if time.time() - start > timeout:
        raise TimeoutError("等待超时")
    # 模拟“就绪检查”
    ready = True
print("准备完成")
```

**关键结论：一个健壮的 `while` 循环，通常由“条件 + 状态更新 + 退出保护”三部分组成。**

---

## 动手练习

**任务：猜数字小游戏（命令行版）**

1. 程序随机生成一个 1~100 之间的整数作为答案；
2. 使用 `while True:` 循环不断读取用户输入；
3. 如果输入的数字比答案大，打印“大了”；比答案小，打印“小了”；
4. 猜中时打印“恭喜猜中！共猜了 N 次”，并用 `break` 退出循环；
5. 如果用户输入 `q`，则打印“游戏已退出”并 `break`；
6. 额外加分：限制最多猜 7 次，超过则打印答案并退出。

提示：使用 `import random` 与 `random.randint(1, 100)` 生成答案；用 `input()` 读输入；注意把字符串转换成 `int`。

## py.flow.break_continue

# Python 中的 `break` 与 `continue`：循环流程控制

> **一句话直觉**：当你“遍历一堆东西”时，`break` 让你立刻抽身离开循环，`continue` 让你跳过当前这一个、直接进入下一个。

在写程序时，我们经常需要“对一批数据做同一件事”。`for` 循环（loop）和 `while` 循环让我们重复执行代码，但真实世界并不总是“从头做到尾”：有时任务已经完成，没必要再往下跑（例如已经找到想找的元素）；有时当前这一个元素不合格，我们想直接跳过它，但不想中断整个流程。`break` 和 `continue` 就是控制这两种“提前脱离”行为的两个关键字（keyword）。它们不改变循环的遍历规则，只影响**本次/本轮**循环控制流的走向。

---

## 1. 基本语法与执行模型

Python 中循环的基本形式是：

```python
for 变量 in 可迭代对象:
    循环体
```

或

```python
while 条件:
    循环体
```

在循环体里，`break` 会**终止整个循环**，跳到循环之后的第一条语句继续执行；
`continue` 会**终止本轮循环的剩余部分**，直接回到循环头部开始下一轮。

用一句话记忆：

- `break`：我不玩了，**整场退出**。
- `continue`：这一轮作废，**进入下一轮**。

```python
# 演示 break 与 continue 的区别
for n in range(1, 6):
    if n == 3:
        continue          # 跳过 3 本身，不打印 3
    if n == 5:
        break             # 遇到 5 直接结束循环
    print(n)
```

运行结果会打印 `1`、`2`、`4`：

- 当 `n == 3` 时，`continue` 让这一轮直接结束，所以 `print(3)` 不会执行；
- 当 `n == 5` 时，`break` 让整个 `for` 循环停止，后面的 5 也不会打印。

---

## 2. `break`：找到了就收工

`break` 最常见的用途，是“我只需要找到一个满足条件的对象，找到就可以结束”。例如在一个列表中查找第一个偶数：

```python
numbers = [3, 7, 11, 8, 9, 12]
found = None

for n in numbers:
    if n % 2 == 0:
        found = n
        break             # 找到了第一个偶数，不用再翻了

print(found)              # 输出 8
```

如果没有 `break`，程序会继续把列表剩下的元素都检查一遍，虽然结果可能一样，但效率更低、表达意图也更模糊。`break` 把“只要第一个”这个意图明确地交给了读代码的人。

同样地，`while True` 配合 `break` 是写“条件在循环内部才确定”的循环的常用写法：

```python
count = 0
while True:
    count += 1
    if count >= 3:
        break
print(count)              # 输出 3
```

---

## 3. `continue`：这一个不要，下一个继续

当“当前这个元素不满足要求，但我不想中断整个循环”时，用 `continue`。例如过滤股票代码中的无效项：

```python
codes = ["AAPL", "", "MSFT", "  ", "GOOG"]

for code in codes:
    if not code.strip():      # 空字符串或纯空白，跳过
        continue
    print(code)
```

输出只有 `AAPL`、`MSFT`、`GOOG`。这样写的好处是“异常/无效分支”在循环开头就被处理掉，主逻辑可以一直保持在同一缩进层，减少嵌套层级。

`continue` 在 `while` 循环中要格外注意：如果跳过的分支里包含了“让循环变量变化”的语句，`continue` 可能会跳过它，导致死循环（infinite loop）。例如下面这段就是错误的：

```python
# ⚠️ 错误示范：跳过 i += 1 会导致无限循环
i = 0
while i < 5:
    if i == 2:
        continue     # 这里直接回到 while 判断，i 永远是 2
    print(i)
    i += 1
```

修正方式是把 `i += 1` 放到 `continue` 之前，或者改用 `for` 循环。

---

## 4. `for / while` 中的 `else` 子句与 `break` 的配合

Python 循环有一个其他语言少见的特性：`for` 和 `while` 后面可以接 `else`。这里的 `else` 意思是“**循环自然结束（没有被 `break` 打断）时执行**”。它在“查找失败才提示”的场景里非常好用：

```python
target = 7
data = [1, 3, 5, 9]

for x in data:
    if x == target:
        print("找到了")
        break
else:
    print("没有找到")     # 只有循环完整跑完才会执行
```

这里 `else` 不是“如果……否则……”的 `else`，而是“循环没有被 `break` 掉”的 `else`。刚接触时容易误读，但记住语义后就非常顺手。

---

## 5. 工程级用法：在数据/训练流程中“跳过脏数据”和“提前停止”

在真实的机器学习（machine learning）或数据处理代码里，`break` 和 `continue` 几乎是必备工具：

- **数据加载（data loading）**：跳过损坏样本、空字段、格式错误的记录；
- **训练循环（training loop）**：早停（early stopping），只要验证指标连续多轮不再提升，就 `break` 退出训练；
- **搜索/匹配**：命中就 `break`，避免无谓遍历。

一个模拟“训练早停”的例子：

```python
losses = [0.9, 0.7, 0.6, 0.605, 0.608, 0.61]
best = float("inf")
patience = 2          # 连续 2 轮没有变好就停
bad_epochs = 0

for epoch, loss in enumerate(losses, start=1):
    if loss < best:
        best = loss
        bad_epochs = 0
        print(f"epoch {epoch}: loss={loss:.3f} 新低")
    else:
        bad_epochs += 1
        print(f"epoch {epoch}: loss={loss:.3f} 未提升 ({bad_epochs}/{patience})")
        if bad_epochs >= patience:
            print("触发早停，结束训练")
            break                 # 提前退出整个训练循环
```

这段代码就是工程上“`break` = 停止大循环”的典型代表。

---

## 小结

| 关键字 | 作用 | 影响的循环 | 常见场景 |
| --- | --- | --- | --- |
| `break` | 立即结束整个循环 | 最内层循环 | 找到目标、早停、搜索命中 |
| `continue` | 结束本轮，进入下一轮 | 最内层循环 | 过滤无效数据、跳过异常分支 |
| `else` | 循环未被 break 时执行 | 与 `break` 配合 | “找不到才提示” |

掌握它们的关键是搞清楚“我现在是在结束整场，还是只跳过这一轮”。

```python
# 可运行示例：从一组用户记录中，找出第一个合法邮箱，并跳过异常数据
users = [
    {"name": "alice", "email": "alice@example.com"},
    {"name": "bob",   "email": ""},
    {"name": "carol", "email": "carol_at_example.com"},
    {"name": "dave",  "email": "dave@example.com"},
]

found = None

for u in users:
    email = u["email"].strip()
    if not email:
        print(f"{u['name']}: 邮箱为空，跳过")
        continue                          # 跳过空邮箱
    if "@" not in email:
        print(f"{u['name']}: 邮箱格式不正确，跳过")
        continue                          # 跳过错格式邮箱
    found = (u["name"], email)
    break                                 # 找到了第一个合法邮箱，停止遍历

if found is not None:
    print(f"使用第一个合法邮箱：{found[0]} <{found[1]}>")
else:
    print("没有找到任何合法邮箱")
```


---

## 本课题目

### single_choice · None



- [A] 0 1 2
- [B] 1 2 3
- [C] 0 1 2 3
- [D] 无限循环

**参考答案**：0

**解析**：i 从 0 开始，每次循环打印后加 1，当 i 等于 3 时条件 i < 3 为假，循环结束。因此输出 0、1、2。

### single_choice · None



- [A] 4 3
- [B] 4 3 2
- [C] 4 3 2 1 0
- [D] 5 4 3

**参考答案**：0

**解析**：每次循环先减 1 再判断。n 依次为 4、3、2，当 n 等于 2 时 break 提前结束，所以只打印了 4 和 3。

### single_choice · None



- [A] 3 2 1
- [B] 1 2 3
- [C] 1 3 2
- [D] 报错

**参考答案**：0

**解析**：pop() 默认弹出末尾元素，列表为空时循环条件为假，输出顺序为 3、2、1。

### single_choice · None



- [A] 1 到 10
- [B] 1 到 5
- [C] 5 到 10
- [D] 什么都不输出

**参考答案**：0

**解析**：pass 是空语句，不改变循环行为，n 从 1 递增到 10 并全部打印。

### single_choice · None



- [A] 1 3
- [B] 1 2 3
- [C] 1 3 4
- [D] 1 2 3 4

**参考答案**：0

**解析**：i 为 2 时被 continue 跳过；i 为 4 时先判断 break 再 print，因此只打印 1 和 3。

### single_choice · None



- [A] 5
- [B] 6
- [C] 10
- [D] 4

**参考答案**：0

**解析**：i 依次为 9、8、7、6、5，当 i 为 5 时不再满足 i > 5，循环结束并输出 5。

### single_choice · None



- [A] while 循环体可能一次都不执行
- [B] while 循环体至少执行一次
- [C] while 循环不能与 else 搭配
- [D] while 循环条件必须使用比较运算符

**参考答案**：0

**解析**：while 是前测试循环，若初始条件为假，循环体一次都不会执行；可以与 else 搭配，条件也可以是任意表达式。

### single_choice · None



- [A] 0 1 2 end
- [B] 0 1 2
- [C] end
- [D] 0 1 2 end end

**参考答案**：0

**解析**：循环正常结束执行 else，先打印 0、1、2，再打印 end。

### single_choice · None



- [A] 3
- [B] 2
- [C] 无限循环
- [D] 1

**参考答案**：0

**解析**：while True 是常见的无限循环写法，通过 break 退出。i 累加至 3 时 break，输出 3。

### single_choice · None



- [A] 2 4 6
- [B] 2 4
- [C] 0 2 4
- [D] 2 4 6 8

**参考答案**：0

**解析**：i 依次为 2、4、6，当 i 为 6 时不满足 i < 5 但 6 在递增后立即打印，所以输出 2、4、6。

### single_choice · None



- [A] 5 4 2 1
- [B] 5 4 3 2 1
- [C] 5 4 3 2 1 跳过 3
- [D] 5 4 2 1 0

**参考答案**：0

**解析**：i 为 3 时被 continue 跳过，且 continue 前先自减，所以不会死循环，最终输出 5、4、2、1。

### single_choice · None



- [A] 21
- [B] 20
- [C] 34
- [D] 13

**参考答案**：0

**解析**：这是斐波那契数列的迭代：b 依次为 1、2、3、5、8、13、21，第一个不小于 20 的 b 是 21。

### single_choice · None



- [A] 1 3 5
- [B] 2 4
- [C] 1 2 3 4 5
- [D] 0 1 2 3 4

**参考答案**：0

**解析**：i 自增后，偶数被 continue 跳过，只打印奇数 1、3、5。

### single_choice · None



- [A] done
- [B] 5
- [C] 无限循环
- [D] 什么都不输出

**参考答案**：0

**解析**：while 循环正常结束（未被 break 中断）时会执行 else 子句，因此打印 done。

### single_choice · None



- [A] 什么都不输出
- [B] completed
- [C] 3
- [D] 无限循环

**参考答案**：0

**解析**：循环被 break 中断时，while 的 else 子句不会执行，因此没有输出。

### single_choice · None



- [A] i = 0
  while i < 5:
      print(i)
- [B] i = 0
  while i < 5:
      print(i)
      i += 1
- [C] for i in range(5):
      print(i)
- [D] i = 5
  while i > 0:
      i -= 1
- [E] 以上都不会

**参考答案**：0

**解析**：第一段代码中 i 从不改变，条件 i < 5 永远为真，会造成无限循环。

### single_choice · None



- [A] 7 4 1 -2
- [B] 10 7 4 1
- [C] 7 4 1
- [D] 10 7 4 1 -2

**参考答案**：0

**解析**：x 依次变化为 7、4、1、-2，条件 x > 0 在 x 为 -2 时不再满足，但 -2 是在循环体内打印的，所以输出包含 -2。

### single_choice · None



- [A] 12
- [B] 8
- [C] 10
- [D] 16

**参考答案**：0

**解析**：total 依次为 4、8、12，当为 12 时不再满足 total < 10，循环结束，最后 print 输出 12。

### single_choice · None



- [A] a b c
- [B] a b c 报错
- [C] abc
- [D] c b a

**参考答案**：0

**解析**：用索引遍历字符串，依次打印 a、b、c，索引在范围内不会报错。

### single_choice · None



- [A] 3 2 1
- [B] 3 2 1 0
- [C] 0 1 2 3
- [D] 无限循环

**参考答案**：0

**解析**：当 i 为非零整数时条件为真，递减到 0 时条件为假循环结束，输出 3、2、1。

### single_choice · None



- [A] 0
  1
  2
- [B] 0
  1
  2
  3
- [C] 0
  1
  2
  3
  4
- [D] 3
  4

**参考答案**：0

**解析**：当 i 等于 3 时执行 break，立即终止整个循环，因此只打印 0、1、2。break 会跳出当前整个循环，而不是只跳过本次迭代。

### single_choice · None



- [A] 0
  1
  2
- [B] 0
  1
  2
  4
- [C] 0
  1
  2
  3
  4
- [D] 3

**参考答案**：1

**解析**：continue 只跳过本次迭代中它之后的语句，循环继续执行。i 为 3 时跳过 print，其余 0、1、2、4 都被打印。

### single_choice · None



- [A] 6
- [B] 7
- [C] 5
- [D] 10

**参考答案**：0

**解析**：i 从 0 到 5 时各执行一次 count += 1，共 6 次；i 为 6 时 break 跳出，不再累加。所以 count 为 6。

### single_choice · None



- [A] 遍历时对每个负数执行 print
- [B] 遍历时遇到负数执行 break
- [C] 遍历时遇到负数执行 continue
- [D] 遍历时跳过所有正数

**参考答案**：1

**解析**：“找到即停止”意味着一旦找到目标就结束循环，break 正是这个语义。continue 只是跳过本次迭代，不会结束循环。

### multi_choice · None



- [A] break 终止整个循环，continue 只结束本次迭代
- [B] 两者都可以用于 for 和 while 循环
- [C] continue 会执行循环的 else 分支
- [D] break 会让循环的 else 分支不执行
- [E] 在 for 循环中 break 后，循环变量会保持原值

**参考答案**：[0, 1, 3, 4]

**解析**：break 终止整个循环，continue 只跳过本次迭代，两者都可用于 for/while。因 break 提前退出时，循环的 else 分支不会执行，而 continue 不阻止 else 执行。

### multi_choice · None



- [A] 跳过列表中所有空字符串，继续处理其余元素
- [B] 找到目标元素后立即停止搜索
- [C] 忽略不符合条件的数据行，继续处理下一行
- [D] 提前结束对文件的读取
- [E] 跳过偶数编号的行

**参考答案**：[0, 2, 4]

**解析**：continue 适合“跳过当前项、继续处理后续项”的场景（跳过空串、忽略不合格行、跳过特定行）。而找到目标后停止或提前结束读取，属于终止整个循环，适合 break。

### multi_choice · None



- [A] 循环正常结束（未被 break 打断）时执行 else
- [B] 循环因 break 退出时不执行 else
- [C] continue 会导致 else 不执行
- [D] else 分支在循环体每次执行后都会运行一次
- [E] 没有 break 的循环结束后一定会执行 else

**参考答案**：[0, 1, 4]

**解析**：循环的 else 仅在循环正常结束（未被 break 打断）时执行一次；continue 不影响 else；若循环体从头到尾没有触发 break，则正常结束后会执行 else。

### multi_choice · None



- [A] 用标志变量配合每层循环的 break
- [B] 把嵌套循环封装成函数并使用 return
- [C] 在循环中抛出异常并在外层捕获
- [D] 使用 continue 从最内层跳到最外层
- [E] 直接在最内层使用 break 就能退出所有层

**参考答案**：[0, 1, 2]

**解析**：break 只跳出所在那一层，因此退出多层循环常用：标志变量逐层 break、封装成函数用 return、或抛异常在外层捕获。continue 和单条 break 都无法跳出所有层。

### fill_blank · None



**参考答案**：["continue"]

**解析**：continue 跳过当前迭代中其后的语句，直接开始下一次迭代，是“跳过本次”的语义。

### fill_blank · None



**参考答案**：["break"]

**解析**：break 会立即终止它所在的那一层循环，程序继续执行循环之后的语句。

### code_reading · None



**参考答案**：0\n1

**解析**：i=0、1 打印；i=2 时 continue 跳过；i=3 时 break 终止循环，因此只打印 0 和 1。

### code_reading · None



**参考答案**：第一次迭代 n=5 时先 n 减为 4，然后 continue；此后打印 4、3、2、1，最后 n 为 0 时循环结束。因此不会打印 5，实际打印 4\n3\n2\n1。

**解析**：continue 之前先把 n 减 1，避免死循环，同时使 n=5 从未被打印。这说明 continue 与循环变量更新的位置会影响结果，也是常见陷阱。

### single_choice · None



- [A] 打印 (0,0)(1,0)(2,0)
- [B] 打印 (0,0)
- [C] 打印 (0,0)(0,1)(1,0)(1,1)(2,0)(2,1)
- [D] 只打印 (0,0)(0,1)

**参考答案**：0

**解析**：内层循环在内层 j 为 1 时 break，只终止内层循环；外层循环继续，所以每轮外层只打印 j=0 的组合，共 (0,0)(1,0)(2,0)。

### scenario · None



**解析**：空行需要跳过本次迭代但继续后续处理，符合 continue 的“跳过本次迭代”语义；而遇到重复 id 要立即停止整个遍历，符合 break 的“终止整个循环”语义。混用两者能满足同一循环内不同条件的处理需求。

### single_choice · None



- [A] break 会同时终止内层和外层循环
- [B] break 只终止包含它的那一层循环
- [C] break 会结束整个程序
- [D] break 只能用在 while 循环中

**参考答案**：1

**解析**：break 只终止它所在的那一层循环。若想跳出多层循环，需要额外机制（如标志变量、return 或异常）。

### single_choice · None



- [A] 1
  3
  5
- [B] 2
  4
- [C] 1
  2
  3
  4
  5
- [D] 5

**参考答案**：0

**解析**：i 从 1 到 5，偶数值（2、4）被 continue 跳过，只打印奇数 1、3、5。continue 之后不执行 print。

### single_choice · None



- [A] continue 会终止循环
- [B] print('after') 永远不会被执行，但 print(i) 会执行
- [C] continue 让循环条件变为 False
- [D] 代码有语法错误

**参考答案**：1

**解析**：这段代码不会“没有输出”，会打印 0、1、2；'after' 永远不打印。若选项中描述“完全不输出”是误解。本题正确理解为 print(i) 正常执行，continue 只跳过其后的语句。

### single_choice · None



- [A] no break
- [B] 什么都不输出
- [C] 5
- [D] 报错

**参考答案**：0

**解析**：循环正常结束（未因 break 提前退出）时执行 else 分支。i 永远不会等于 5，所以循环正常结束，打印 no break。

### single_choice · None



- [A] no break
- [B] 什么都不输出
- [C] 1
- [D] 报错

**参考答案**：1

**解析**：循环因 i==1 时 break 而提前终止，else 分支不执行，所以什么都不打印。

### single_choice · None



- [A] [1, 3]
- [B] [0, 2, 4]
- [C] [1, 3, 5]
- [D] [0, 1, 2, 3, 4]

**参考答案**：0

**解析**：i 超过 4 时 break 终止循环。在 0~4 中，偶数被 continue 跳过，奇数 1、3 被加入，因此是 [1, 3]。

### single_choice · None



- [A] 在 continue 之前修改循环变量
- [B] 在 continue 之后修改循环变量
- [C] 在 break 之前修改循环变量
- [D] 在循环外修改循环变量

**参考答案**：1

**解析**：若把改变循环变量（如 i += 1）放在 continue 之后，遇到 continue 时更新语句被跳过，循环条件不变，导致死循环。
