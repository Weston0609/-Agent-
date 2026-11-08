# s1u4l1 Python 列表基础：从直觉到工程 / Python 列表方法：从零基础到工程级

> 来源 `content/lessons/s1u4l1.json`

## py.type.list_basic

# Python 列表基础：从直觉到工程

## 一句话直觉

**列表（list）是 Python 里最常用的“有序可变容器”**，它像一排带编号的储物柜：你可以按位置取放东西、随时增删改，还能一次遍历所有内容。学会它，你就能组织批量数据（如成绩、姓名、日志），这是后面学习循环、函数、数据处理的地基。

> 术语说明：
> - **列表（list）**：Python 内置的一种序列类型，元素有序、可修改。
> - **容器（container）**：能装多个对象的对象。
> - **可变（mutable）**：创建后还能修改内容。
> - **序列（sequence）**：按位置索引访问的容器，如 list、tuple、str。

---

## 1. 创建列表与按位置访问

列表用方括号 `[]` 创建，元素之间用逗号分隔。元素可以是任意类型，也可以混合。

- **索引（index）**：从 `0` 开始，`list[0]` 是第一个，`list[-1]` 是最后一个。
- **切片（slice）**：`list[start:stop:step]` 取子列表，左闭右开。
- **长度**：`len(list)`。

```python
# 创建列表
scores = [90, 85, 77, 92]

# 按索引访问（从 0 开始）
print(scores[0])   # 90
print(scores[-1])  # 92，最后一个

# 切片：取前三个
print(scores[0:3]) # [90, 85, 77]

# 长度
print(len(scores)) # 4
```

**关键结论**：列表索引从 0 开始，负索引从末尾倒数；切片返回新列表。

---

## 2. 修改列表：增、删、改

列表是**可变**的，所以可以原地修改。常用操作：

- `append(x)`：末尾追加一个元素。
- `insert(i, x)`：在下标 `i` 处插入。
- `pop()` / `pop(i)`：删除并返回末尾或指定位置元素。
- `remove(x)`：删除第一个等于 `x` 的元素。
- `list[i] = new_value`：按下标替换。

```python
nums = [1, 2, 3]

nums.append(4)        # 末尾追加
print(nums)           # [1, 2, 3, 4]

nums.insert(0, 0)     # 在下标 0 插入 0
print(nums)           # [0, 1, 2, 3, 4]

last = nums.pop()     # 删除末尾并返回
print(last, nums)     # 4 [0, 1, 2, 3]

nums.remove(2)        # 删除第一个 2
print(nums)           # [0, 1, 3]

nums[0] = 100         # 修改下标 0
print(nums)           # [100, 1, 3]
```

**关键结论**：列表的修改方法大多返回 `None`，直接改原列表，不要写成 `nums = nums.append(4)`。

---

## 3. 遍历列表：for 循环与推导式

遍历列表最常用 `for` 循环；如果想把每个元素变换后生成新列表，用**列表推导式（list comprehension）**更简洁。

```python
fruits = ["apple", "banana", "cherry"]

# 普通 for 遍历
for fruit in fruits:
    print(fruit)

# 带索引遍历
for i, fruit in enumerate(fruits):
    print(i, fruit)

# 列表推导式：每个元素长度
lengths = [len(fruit) for fruit in fruits]
print(lengths)  # [5, 6, 6]
```

**关键结论**：`for x in list` 直接拿元素；需要下标时用 `enumerate(list)`；推导式适合“映射/过滤”场景。

---

## 4. 列表与类型提示：`list[int]` 是什么意思

Python 运行时**不会强制检查**类型提示（type hints），但类型检查器（type checker，如 mypy、pyright）、IDE 和 linter 会利用它帮你提前发现错误。

- `list[int]` 表示“元素为 int 的列表”。
- `list[str]` 表示“元素为 str 的列表”。
- 函数参数和返回值都可以加类型提示。

```python
def total(scores: list[int]) -> int:
    """返回分数总和；类型提示说明 scores 是 int 列表，返回 int"""
    return sum(scores)

print(total([90, 85, 77]))  # 252
```

**关键结论**：`list[int]` 是写给“人和工具”看的，不是运行时强制；但它能显著提升工程代码的可维护性。

---

## 5. 常见陷阱与工程建议

- **索引越界**：访问 `list[10]` 但长度只有 3，会抛 `IndexError`。
- **浅拷贝（shallow copy）**：`b = a` 只是别名，改 `b` 会影响 `a`；要独立副本用 `a.copy()` 或 `a[:]`。
- **循环中删元素**：边遍历边 `remove` 容易漏元素；可倒序遍历或生成新列表。
- **可变默认参数**：`def f(x, acc=[])` 是经典坑，默认列表会被复用；应写 `acc=None` 再内部创建。

```python
a = [1, 2, 3]
b = a          # 别名，不是拷贝
b.append(4)
print(a)       # [1, 2, 3, 4]

c = a.copy()   # 浅拷贝
c.append(5)
print(a)       # [1, 2, 3, 4]
print(c)       # [1, 2, 3, 4, 5]
```

**关键结论**：赋值不是拷贝；要独立列表就用 `copy()` 或切片。

---

## 动手练习

**任务**：写一个 Python 脚本 `score_report.py`，完成：

1. 定义列表 `scores = [88, 92, 79, 93, 85]`。
2. 用函数 `add_score(scores: list[int], value: int) -> None` 在末尾追加一个分数。
3. 用函数 `average(scores: list[int]) -> float` 返回平均分。
4. 用列表推导式生成 `passed = [s for s in scores if s >= 60]`。
5. 打印：原始列表、平均分、及格列表、最高分与最低分。

**提示**：
- 平均分用 `sum(scores) / len(scores)`。
- 最高分 `max(scores)`，最低分 `min(scores)`。
- 运行后观察输出，尝试修改分数再运行。

完成后，你已掌握列表的创建、访问、修改、遍历和类型提示，可以进入下一课学习元组（tuple）与字典（dict）。

```python
# score_report.py
# 一个可运行的列表示例：创建、修改、遍历、类型提示

def add_score(scores: list[int], value: int) -> None:
    """在列表末尾追加一个分数"""
    scores.append(value)


def average(scores: list[int]) -> float:
    """返回平均分；类型提示说明 scores 是 int 列表，返回 float"""
    return sum(scores) / len(scores)


# 1. 创建列表
scores = [88, 92, 79, 93, 85]

# 2. 追加分数
add_score(scores, 90)

# 3. 计算平均分
avg = average(scores)

# 4. 列表推导式：过滤及格分数
passed = [s for s in scores if s >= 60]

# 5. 打印结果
print("原始列表:", scores)
print("平均分:", avg)
print("及格列表:", passed)
print("最高分:", max(scores))
print("最低分:", min(scores))

# 额外演示：索引、切片、修改
print("第一个分数:", scores[0])
print("最后一个分数:", scores[-1])
print("前三个分数:", scores[:3])
scores[0] = 95
print("修改后列表:", scores)
```

## py.type.list_method

# Python 列表方法：从零基础到工程级

## 一句话直觉

列表（list）是 Python 里最常用的"容器"，而**列表方法**就是你对这个容器进行增删改查、排序、复制的"操作面板"——掌握它，你就能用一行代码完成别人写十行的数据处理。

---

## 1. 什么是列表方法？为什么它无处不在？

列表（list）是 Python 内置的可变（mutable）有序序列。每个列表对象都自带一批**方法（method）**——也就是"绑定在对象上的函数"，调用格式是 `列表.方法名(参数)`。

列表方法的特点：
- **原地修改（in-place）**：多数方法（如 `append`、`sort`、`extend`）直接改动原列表，返回 `None`。
- **返回新对象**：少数方法（如 `copy`）返回新列表。

```python
nums = [3, 1, 2]
result = nums.sort()   # 原地排序，返回值是 None
print(nums)            # [1, 2, 3]
print(result)          # None —— 别把返回值当排序结果用
```

> 关键结论：**凡是"原地修改"的方法都返回 `None`，千万不要写 `nums = nums.sort()`**。

---

## 2. 增删改：最常用的几个方法

- `append(x)`：在尾部追加**一个**元素。
- `insert(i, x)`：在下标 `i` 前插入 `x`。
- `extend(iterable)`：把另一个可迭代对象（iterable）的所有元素逐个追加。
- `remove(x)`：删除**第一个**等于 `x` 的元素，找不到会抛 `ValueError`。
- `pop(i=-1)`：弹出并返回下标 `i` 的元素（默认末尾）。
- `clear()`：清空列表。

```python
fruits = ["apple", "banana"]
fruits.append("cherry")           # 尾部追加
fruits.insert(1, "blueberry")     # 插到下标 1 前
fruits.extend(["date", "elder"])  # 批量追加
print(fruits)
# ['apple', 'blueberry', 'banana', 'cherry', 'date', 'elder']

last = fruits.pop()               # 弹出末尾
fruits.remove("banana")           # 删除第一个 'banana'
print(last, fruits)
# elder ['apple', 'blueberry', 'cherry', 'date']
```

> 关键结论：**`append(x)` 把 `x` 当一个元素；`extend(x)` 把 `x` 里的每个元素都加进来**。传字符串给 `append` 是加一整个字符串，而 `extend` 会把它拆成字符。

---

## 3. 查找与统计：index、count、in

- `index(x)`：返回第一个 `x` 的下标，找不到抛 `ValueError`。
- `count(x)`：返回 `x` 出现的次数。
- `x in lst`：成员判断，返回布尔值（不是方法，但几乎总是搭配使用）。

```python
scores = [88, 92, 88, 75, 92, 88]
print(scores.count(88))    # 3
print(scores.index(75))    # 3
print(88 in scores)        # True

# 安全查找：不想抛异常就先判断
if 100 in scores:
    print(scores.index(100))
else:
    print("100 not found")
```

> 关键结论：**`index` 找不到会抛异常**，生产中常先用 `in` 或配合 `try/except` 使用。

---

## 4. 排序与反转：sort、reverse、key 参数

- `sort(key=None, reverse=False)`：**原地**排序。
- `reverse()`：**原地**反转。
- 想得到新列表用内置函数 `sorted(lst)`（返回新列表，原列表不变）。

`key` 接收一个函数，用于计算排序依据，这是工程里最常用的技巧。

```python
people = [("Alice", 30), ("Bob", 25), ("Cara", 35)]
people.sort(key=lambda p: p[1])          # 按年龄升序
print(people)                            # [('Bob', 25), ('Alice', 30), ('Cara', 35)]

people.sort(key=lambda p: p[1], reverse=True)  # 按年龄降序
print(people)                            # [('Cara', 35), ('Alice', 30), ('Bob', 25)]

nums = [1, 2, 3]
nums.reverse()
print(nums)                              # [3, 2, 1]
```

> 关键结论：**排序规则复杂时，用 `key=` 而不是自己写比较函数**。`key` 只被调用一次每个元素，比 `cmp` 风格高效得多。

---

## 5. 复制与踩坑：copy、切片、别名陷阱

- `copy()`：返回**浅拷贝（shallow copy）**，嵌套的可变对象仍共享。
- `lst[:]` 等价于浅拷贝。
- 想深拷贝用 `copy.deepcopy`。

```python
import copy

a = [[1, 2], [3, 4]]
b = a.copy()          # 浅拷贝：外层新，内层共享
b[0].append(99)
print(a)              # [[1, 2, 99], [3, 4]] —— a 也被改了！

c = copy.deepcopy(a)  # 深拷贝：完全独立
c[0].append(100)
print(a)              # 不受影响
```

> 关键结论：**`=` 只是别名，`copy()` 只复制一层，嵌套结构要 `deepcopy`**。

---

## 6. 方法速查表

| 方法 | 作用 | 是否原地 | 返回 |
|---|---|---|---|
| `append(x)` | 尾部加一个元素 | 是 | None |
| `extend(it)` | 追加可迭代对象全部元素 | 是 | None |
| `insert(i, x)` | 在下标 i 前插入 | 是 | None |
| `remove(x)` | 删除第一个 x | 是 | None |
| `pop(i=-1)` | 弹出下标 i 的元素 | 是 | 被弹出的元素 |
| `clear()` | 清空 | 是 | None |
| `index(x)` | 返回第一个 x 的下标 | 否 | int |
| `count(x)` | 统计 x 出现次数 | 否 | int |
| `sort(key, reverse)` | 原地排序 | 是 | None |
| `reverse()` | 原地反转 | 是 | None |
| `copy()` | 浅拷贝 | 否 | 新 list |

---

## 动手练习

**任务：写一个"学生成绩分析器"**

给定如下数据（每个元素是 `(姓名, 分数)` 元组）：

```python
students = [
    ("Alice", 88),
    ("Bob", 72),
    ("Cara", 95),
    ("Dan", 88),
    ("Eve", 60),
]
```

请在本地写一段脚本完成：

1. 用 `append` 追加一个新学生 `("Frank", 80)`。
2. 用 `sort(key=..., reverse=True)` 按分数从高到低排序。
3. 用 `pop()` 取出分数最高的学生并打印。
4. 打印输出分数 88 出现了几次（用 `count` 需要对分数列表或用循环）。
5. 用 `copy()` 复制一份，再给副本 `insert(0, ("Zoe", 100))`，验证原列表是否变化。

**挑战（可选）**：把第 4 步用一行 `sum` + 生成器表达式实现，体会列表方法之外的另一种风格。

```python
# 可直接运行：演示列表常用方法
students = [
    ("Alice", 88),
    ("Bob", 72),
    ("Cara", 95),
    ("Dan", 88),
    ("Eve", 60),
]

# 1. 追加
students.append(("Frank", 80))

# 2. 按分数降序排序（原地）
students.sort(key=lambda s: s[1], reverse=True)
print("Sorted:", students)

# 3. 弹出最高分
top = students.pop(0)
print("Top student:", top)

# 4. 统计 88 分的个数
count_88 = sum(1 for _, score in students if score == 88)
print("Count of 88:", count_88)

# 5. 浅拷贝后修改副本
snapshot = students.copy()
snapshot.insert(0, ("Zoe", 100))
print("Original :", students)
print("Snapshot :", snapshot)
```


---

## 本课题目

### single_choice · None



- [A] [1, 2, 3]
- [B] [1, 2, 3, 4]
- [C] [4]
- [D] 报错，因为 b 未定义

**参考答案**：1

**解析**：b = a 并不会复制列表，而是让 b 与 a 指向同一个列表对象。对 b 调用 append 会修改这个共享对象，所以 a 和 b 都变成 [1, 2, 3, 4]。这是列表可变性最常见的陷阱。

### single_choice · None



- [A] b = a[:]
- [B] b = list(a)
- [C] b = copy.copy(a)
- [D] b = a

**参考答案**：3

**解析**：b = a 只是新增一个名字指向同一个列表对象，二者共享内存。切片 a[:]、list(a) 以及 copy.copy(a) 都会创建一个浅拷贝的新列表，对顶层元素的修改互不影响。

### single_choice · None



- [A] [1, 3]
- [B] [1, 2]
- [C] [2, 3]
- [D] 报错，remove 只能删下标

**参考答案**：0

**解析**：remove(value) 按值删除第一个匹配的元素，这里删除 2，剩下 [1, 3]。若按位置删除应用 del 或 pop(index)。

### multi_choice · None



- [A] b = a[:]
- [B] b = sorted(a)
- [C] a.sort()
- [D] b = list(a)
- [E] a.reverse()

**参考答案**：[0, 1, 3]

**解析**：a[:] 与 list(a) 是浅拷贝，产生新列表；sorted(a) 返回排序后的新列表，不改变原列表。而 a.sort() 与 a.reverse() 都是原地修改 a 本身并返回 None。

### multi_choice · None



- [A] 列表是可变的，可以增删改元素
- [B] 元组是不可变的，创建后不能修改其顶层元素
- [C] 列表和元组都支持索引和切片
- [D] 元组不能被迭代

**参考答案**：[0, 1, 2]

**解析**：列表可变、元组不可变，这是两者的核心区别；但二者都是序列，都支持索引、切片和迭代。因此「元组不能被迭代」是错误的。

### multi_choice · None



- [A] b 的值为 [2, 3]
- [B] 修改 b 的顶层元素不会影响 a
- [C] b 与 a 是同一个对象
- [D] a 会被修改为 [2, 3]

**参考答案**：[0, 1]

**解析**：切片 a[1:3] 取下标 1、2 得到 [2, 3]，并生成一个新的列表对象，因此修改 b 不影响 a；a 本身保持不变。b 与 a 不是同一个对象，a 也不会被改变。

### multi_choice · None



- [A] 结果列表是 [0, 2, 4]
- [B] if 子句用于过滤元素
- [C] range(5) 产生 0 到 4
- [D] 结果列表是 [1, 3]

**参考答案**：[0, 1, 2]

**解析**：range(5) 产生 0,1,2,3,4；if x % 2 == 0 只保留偶数，即 0,2,4。if 子句在这里起过滤作用。结果不是 [1,3]。

### fill_blank · None



**参考答案**：["n*n", "n**2", "n * n", "n ** 2"]

**解析**：列表推导式的表达式部分应计算元素的平方，即 n*n 或 n**2，从而得到 [100, 400, 900, 1600, 2500]。

### fill_blank · None



**参考答案**：["nums[-1]", "nums[len(nums)-1]"]

**解析**：取最后一个元素可用负索引 nums[-1]，或正索引 nums[len(nums)-1]。前者更简洁且是常用写法。

### code_reading · None



**参考答案**：输出：[100, 2, 3] [1, 2, 3]

**解析**：b = a 让 b 与 a 共享同一对象，修改 b[0] 会同时改变 a，所以 a 变成 [100, 2, 3]。c = a[:] 是浅拷贝，与 a 独立，因此 c 保持原来的 [1, 2, 3]。

### code_reading · None



**参考答案**：输出：[2, 4]

**解析**：切片 nums[1:4:2] 表示从下标 1 开始（含），到下标 4 结束（不含），步长为 2。先确定范围 [2, 3, 4]（下标 1,2,3），再每隔 2 个取一个，得到下标 1 的 2 和下标 3 的 4。

### scenario · None



**解析**：u1_tags = tags 和 u2_tags = tags 都是引用赋值，三个变量指向同一个列表对象，任何一方修改都会体现在其他变量上，这就是别名（aliasing）现象。要让每个用户独立，应在赋值时做浅拷贝，例如 u1_tags = tags[:] 或 list(tags) 或 import copy 后 copy.copy(tags)，这样每个变量指向不同的列表对象。

### single_choice · None



- [A] 4
- [B] 5
- [C] 2
- [D] 报错 IndexError

**参考答案**：0

**解析**：负索引从末尾计数，-1 表示最后一个元素 5，-2 表示倒数第二个元素 4。因此输出 4。

### single_choice · None



- [A] 返回 None
- [B] 返回 3
- [C] 抛出 IndexError
- [D] 自动扩展列表并返回 0

**参考答案**：2

**解析**：列表下标从 0 开始，有效范围是 -3 到 2。nums[3] 越界，Python 会抛出 IndexError，而不是返回 None 或自动扩容。若需要安全访问，应先用长度判断或用切片。

### single_choice · None



- [A] nums[2:3]
- [B] nums[2:4]
- [C] nums[3:4]
- [D] nums[1:3]

**参考答案**：1

**解析**：切片遵循「含头不含尾」，nums[2:4] 取下标 2 和 3 的元素，即 [3, 4]。nums[2:3] 只取到 [3]；nums[3:4] 是 [4]；nums[1:3] 是 [2, 3]。

### single_choice · None



- [A] [1, 2, 3]
- [B] [3, 2, 1]
- [C] [1, 3]
- [D] 报错，切片步长不能为负

**参考答案**：1

**解析**：切片的第三个参数是步长，[::-1] 表示从头到尾以步长 -1 取值，即反转列表，得到 [3, 2, 1]。步长为负是合法且常用的反转写法。

### single_choice · None



- [A] [1, 2, 3]
- [B] [1, 2, 3, 4]
- [C] [4]
- [D] 报错

**参考答案**：0

**解析**：a[:] 产生一个浅拷贝的新列表，b 与 a 指向不同对象。对 b 追加元素不会影响 a，所以 a 仍为 [1, 2, 3]。注意这与 b = a 有本质区别。

### single_choice · None



- [A] [x*x for x in range(4)]
- [B] [x*x for x in range(0, 8, 2)]
- [C] [x*2 for x in range(4)]
- [D] [x*x for x in range(1, 5)]

**参考答案**：1

**解析**：range(0, 8, 2) 产生 0, 2, 4, 6，平方后是 0, 4, 16, 36。range(4) 是 0..3，平方为 0,1,4,9；[x*2 ...] 是翻倍不是平方；range(1,5) 平方是 1,4,9,16。

### single_choice · None



- [A] 3
- [B] 4
- [C] 2
- [D] 报错

**参考答案**：0

**解析**：len 只统计列表顶层元素个数。外层列表有三个元素：1、内层列表 [2, 3] 和 4，因此返回 3。嵌套列表并不展开计数。

### single_choice · None



- [A] [99, 1, 2, 3]
- [B] [1, 99, 2, 3]
- [C] [1, 2, 99, 3]
- [D] [1, 2, 3, 99]

**参考答案**：1

**解析**：insert(index, value) 在指定下标处插入元素，原下标及之后的元素向后移动。nums.insert(1, 99) 把 99 放在下标 1，得到 [1, 99, 2, 3]。

### single_choice · None



- [A] [1, 2, 3, 4, 5]
- [B] [1, 2, 3, [4, 5]]
- [C] [1, 2, 3, 4, 5, [4, 5]]
- [D] 报错，因为 append 只能接受一个元素

**参考答案**：1

**解析**：append 把参数作为单个元素整体追加到列表末尾，不会把可迭代对象展开。若想展开应使用 extend。

### single_choice · None



- [A] sorted(nums)
- [B] nums.sort()
- [C] nums = sorted(nums)
- [D] nums.reverse()

**参考答案**：1

**解析**：list.sort() 原地排序并返回 None；sorted() 返回新列表，原列表不变。

### multi_choice · None



- [A] sort() 是列表的方法，sorted() 是内置函数
- [B] sort() 原地排序，返回 None
- [C] sorted() 返回新列表，原列表不变
- [D] 两者都只能用于列表
- [E] 两者都支持 reverse 和 key 参数

**参考答案**：[0, 1, 2, 4]

**解析**：sorted() 可作用于任意可迭代对象，而 sort() 只属于列表，故「两者都只能用于列表」错误。二者都支持 key 与 reverse。

### fill_blank · None



**参考答案**：["sort", "sort()"]

**解析**：list.sort 支持 reverse 参数，reverse=True 时原地降序排列并返回 None。

### fill_blank · None



**参考答案**：["remove"]

**解析**：remove 按值删除第一个匹配项；若只想去掉某个下标，应使用 pop 或 del。

### code_reading · None



**参考答案**：先输出 None，再输出 [1, 2, 3, 4]

**解析**：append 原地修改列表并返回 None，因此 result 是 None，而 lst 已被追加 4。

### code_reading · None



**参考答案**：[1, 2, 3, 4]

**解析**：b = a 只复制引用，两个名字指向同一个列表对象，通过 b 的修改在 a 上同样可见。若需独立副本应使用 a.copy() 或 a[:]。

### code_reading · None



**参考答案**：[10, 20, 30, 99]

**解析**：insert 的下标超出范围时不会报错，而是把元素追加到列表末尾，因此 99 被放在最后。

### code_reading · None



**参考答案**：0

**解析**：clear() 移除列表中所有元素，使列表变为空列表，长度为 0。

### scenario · None



**解析**：append 把参数作为单个元素整体加入；extend 则遍历可迭代对象，将其中的元素逐个展开追加。用 append(batch) 会导致列表里出现嵌套子列表，而 extend(batch) 才等价于逐条合并。

### scenario · None



**解析**：排序改变原列表说明用了 list.sort()，它是原地方法。要保持调用方数据不变，可改用 sorted(列表) 返回新列表，或先 lst.copy() 再对副本调用 sort。

### single_choice · None



- [A] 1
- [B] 4
- [C] [1, 2, 3]
- [D] [1, 2, 3, 4]

**参考答案**：1

**解析**：pop() 不传参数时移除并返回最后一个元素，因此返回 4，同时列表变为 [1, 2, 3]。

### single_choice · None



- [A] [99, 1, 2, 3]
- [B] [1, 99, 2, 3]
- [C] [1, 2, 99, 3]
- [D] [1, 2, 3, 99]

**参考答案**：1

**解析**：insert(index, value) 将元素插入到指定下标处，原有该位置及之后的元素整体后移，因此 99 落在下标 1。

### single_choice · None



- [A] 1
- [B] 3
- [C] [1, 3]
- [D] 报错，因为 2 出现了两次

**参考答案**：0

**解析**：list.index(x) 返回第一个值为 x 的元素下标，重复出现不会报错，返回最先匹配的位置 1。

### single_choice · None



- [A] 移除下标为 x 的元素
- [B] 移除列表中第一个值等于 x 的元素
- [C] 移除列表中所有值等于 x 的元素
- [D] 返回被移除的元素

**参考答案**：1

**解析**：remove(x) 按值删除，只删除第一个匹配项且返回 None；按位置删除应使用 pop(index) 或 del。

### single_choice · None



- [A] [1, 2, 3, 'ab']
- [B] [1, 2, 3, 'a', 'b']
- [C] [1, 2, 3, 'a', 'b', 'ab']
- [D] 报错，extend 只接受列表

**参考答案**：1

**解析**：extend 接受任意可迭代对象，并逐元素追加。字符串是字符序列，所以 'a' 和 'b' 分别被追加。

### single_choice · None



- [A] b = a + [4]
- [B] b = a.copy()
- [C] a.sort()
- [D] b = sorted(a)

**参考答案**：2

**解析**：只有 list.sort() 是原地修改。a + [4]、a.copy()、sorted(a) 都产生新对象，不改变原列表。

### multi_choice · None



- [A] lst.append(4)
- [B] lst.extend([4])
- [C] lst.insert(len(lst), 4)
- [D] lst + [4]
- [E] lst = lst + [4]

**参考答案**：[0, 1, 2, 4]

**解析**：前三者与最后一项都能让变量指向含 4 的列表。第四项 lst + [4] 只是产生新列表而未赋值，原变量仍为 [1,2,3]。

### multi_choice · None



- [A] pop() 默认删除并返回最后一个元素
- [B] pop(i) 删除并返回下标 i 处的元素
- [C] pop 越界会引发 IndexError
- [D] pop 删除元素后返回 None
- [E] pop 可以按值删除元素

**参考答案**：[0, 1, 2]

**解析**：pop 按下标删除并返回被删元素，不返回 None；按下标越界会报 IndexError。按值删除应使用 remove。
