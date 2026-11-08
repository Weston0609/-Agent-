# s1u4l6 嵌套容器类型注解（Nested Container Types） / 浅拷贝与深拷贝（Shallow Copy vs Deep Copy）

> 来源 `content/lessons/s1u4l6.json`

## py.type.nested_container

# 嵌套容器类型注解（Nested Container Types）

> 一句话直觉：当数据结构里“装着”另一层数据结构时，普通类型注解就不够用了，我们需要**嵌套容器类型注解**来精确描述“列表里的字典里还有列表”这种结构。

---

## 1. 为什么需要“嵌套容器”注解？

在 Python 中，我们常用 `list`、`dict`、`tuple`、`set` 等**容器类型（container type）**来装东西。但现实数据往往是“层层包裹”的：

```python
users = [
    {"name": "Alice", "scores": [90, 85]},
    {"name": "Bob",   "scores": [78, 92]},
]
```

这里的 `users` 是一个**列表**，列表的每个元素是**字典**，字典里的 `"scores"` 又对应一个**列表**。  
如果只写 `users: list`，类型检查器完全不知道里面装了啥。

**嵌套容器类型注解**就是让我们写出：  
“这是一个列表，元素是字典，键是 str，值是 int 或 list[int]”。

> 注意：Python 运行时**不强制执行**类型注解，它只是给类型检查器（type checker）、IDE、linter 看的元信息。

---

## 2. 最基础的嵌套：`list[dict[str, int]]`

Python 3.9 起，内置容器支持**下标语法（subscription）**直接写泛型（generic）：

```python
# 一个列表，里面每个元素都是「键为 str、值为 int」的字典
records: list[dict[str, int]] = [
    {"alice": 90},
    {"bob": 85},
]

# 错误示例（类型检查器会报错，但运行时不会）：
# records.append({"carol": "good"})  # 值应该是 int，不是 str
```

要点：
- `list[X]` 表示“元素类型为 X 的列表”。
- `dict[K, V]` 表示“键为 K、值为 V 的字典”。
- 嵌套就是把内层类型直接放到外层的中括号里。

---

## 3. 多层嵌套：描述“列表里的字典里还有列表”

来看更贴近真实的例子——用户详情：

```python
# 结构：list[ dict[str, str | list[int]] ]
# 即：一个列表，元素是字典，字典的键是 str，值可能是 str 或 list[int]

user_data: list[dict[str, str | list[int]]] = [
    {"name": "Alice", "scores": [90, 85, 88]},
    {"name": "Bob",   "scores": [78, 92]},
]

for user in user_data:
    print(user["name"], user["scores"])
```

这里出现了三层：
1. 外层 `list`
2. 中间 `dict[str, ...]`
3. 内层值类型的**联合类型（union type）**：`str | list[int]`

> `X | Y` 是 Python 3.10 引入的**联合类型**写法，等价于 `typing.Union[X, Y]`。

---

## 4. 元组与不定长：`tuple[int, str]` 与 `tuple[int, ...]`

元组的嵌套写法很特别，因为它有两种含义：

### 4.1 固定长度元组

```python
# 一个长度为 2 的元组：第一个是 int，第二个是 str
point: tuple[int, str] = (1, "hello")

# 一个二元组，元素是「address 元组」和「options 字典」
# 结构：tuple[ tuple[str, int], dict[str, str] ]
server: tuple[tuple[str, int], dict[str, str]] = (
    ("127.0.0.1", 8080),
    {"timeout": "30s"},
)
```

### 4.2 不定长元组（同类型）

```python
# 用字面量省略号 ... 表示“任意长度，但元素都是 int”
nums: tuple[int, ...] = (1, 2, 3, 4, 5)

# 空元组
empty: tuple[()] = ()
```

> 注意：`tuple[int]` 表示**长度为 1** 的元组，而不是“任意长度的 int 元组”。这是常见误区。

---

## 5. 工程级技巧：用类型别名拆解复杂结构

当嵌套超过两层，注解会变得很难读。用 `type` 语句（Python 3.12+）或 `TypeAlias` 抽出来：

```python
from collections.abc import Sequence

# Python 3.12+ 写法
type ConnectionOptions = dict[str, str]
type Address = tuple[str, int]
type Server = tuple[Address, ConnectionOptions]

def broadcast_message(message: str, servers: Sequence[Server]) -> None:
    ...

# 等一下——Server 里嵌套了 Address 和 ConnectionOptions，
# 传进去的参数其实是：list[tuple[tuple[str, int], dict[str, str]]]
```

对于 Python < 3.12，用赋值或 `TypeAlias` 标注也一样有效：

```python
from typing import TypeAlias

Vector: TypeAlias = list[float]

def scale(scalar: float, vector: Vector) -> Vector:
    return [scalar * n for n in vector]

print(scale(2.0, [1.0, -4.2, 5.4]))  # [2.0, -8.4, 10.8]
```

类型别名让复杂嵌套结构的**含义**清晰，类型检查器也会把别名等价视为展开后的结构。

---

## 6. 动手练习

**任务**：定义一个描述“学生成绩表”的嵌套类型别名，并写一个函数用它。

要求：
1. 结构为：`list[dict[str, list[int]]]`，表示“多个学生，每个学生对应一个『科目名 → 分数列表』的字典”。
2. 用 `type` 语句（或 `TypeAlias`）命名为 `ScoreTable`。
3. 实现 `average_per_subject(table: ScoreTable) -> dict[str, float]`，返回每个科目的平均分。
4. 用一组示例数据调用，打印结果。

示例输入：

```python
table = [
    {"math": [90, 80], "english": [70, 75]},
    {"math": [100], "english": [60, 65, 70]},
]
```

预期输出：`{"math": 90.0, "english": 68.0}` 左右的结果。

```python
from typing import TypeAlias

# 1) 用类型别名描述嵌套容器
# 含义：list[ dict[科目名: str, 分数列表: list[int]] ]
ScoreTable: TypeAlias = list[dict[str, list[int]]]


def average_per_subject(table: ScoreTable) -> dict[str, float]:
    """计算每个科目的平均分。"""
    # 收集每个科目的所有分数
    buckets: dict[str, list[int]] = {}
    for student in table:
        for subject, scores in student.items():
            buckets.setdefault(subject, []).extend(scores)

    # 求平均
    return {subj: sum(vals) / len(vals) for subj, vals in buckets.items()}


if __name__ == "__main__":
    table: ScoreTable = [
        {"math": [90, 80], "english": [70, 75]},
        {"math": [100],   "english": [60, 65, 70]},
    ]
    print(average_per_subject(table))
    # 预期输出形如: {'math': 90.0, 'english': 68.0}
```

## py.type.copy_shallow_deep

# 浅拷贝与深拷贝（Shallow Copy vs Deep Copy）

## 一句话直觉

学它，是因为你复制一个对象时，Python 默认往往只复制“外壳”，里面的嵌套对象仍然共享，改一个会牵连另一个。

---

## 1. 为什么复制会出问题：赋值不是复制

在 Python 里，`b = a` 不是复制对象，而是让 `b` 和 `a` 指向同一个对象。

```python
# 赋值：a 和 b 指向同一个列表对象
a = [1, 2, 3]
b = a
b.append(4)
print(a)  # [1, 2, 3, 4]
print(a is b)  # True
```

关键结论：
- 赋值（assignment）只是增加引用（reference），不是复制（copy）。
- 想知道两个名字是否指向同一对象，用 `is`。

---

## 2. 浅拷贝：只复制最外层

浅拷贝（shallow copy）会创建一个新对象，但里面包含的元素仍然引用原来的子对象。

```python
import copy

# 嵌套列表：外层里面还有内层列表
original = [[1, 2], [3, 4]]
shallow = copy.copy(original)

# 外层是新对象
print(original is shallow)          # False
print(original[0] is shallow[0])    # True，内层仍然共享

# 改内层，会互相影响
shallow[0][0] = 99
print(original)  # [[99, 2], [3, 4]]
```

关键结论：
- 浅拷贝只复制当前这一层。
- 如果元素是可变对象（mutable object），它们仍被共享。
- 列表、字典、集合也有自己的浅拷贝写法，例如 `list.copy()`、`dict.copy()`、`x[:]`。

---

## 3. 深拷贝：递归复制到底

深拷贝（deep copy）会递归复制对象内部的所有子对象，得到一个完全独立的新对象。

```python
import copy

original = [[1, 2], [3, 4]]
deep = copy.deepcopy(original)

# 外层和内层都不是同一个对象
print(original is deep)          # False
print(original[0] is deep[0])    # False

# 改深拷贝，不影响原对象
deep[0][0] = 99
print(original)  # [[1, 2], [3, 4]]
print(deep)      # [[99, 2], [3, 4]]
```

关键结论：
- 深拷贝真正独立，适合嵌套结构。
- 深拷贝成本更高，可能更慢、更占内存。
- 如果对象里有文件句柄、网络连接、锁等资源，深拷贝通常不合适。

---

## 4. 工程中怎么选：看“共享是否安全”

选择浅拷贝还是深拷贝，核心不是“哪个高级”，而是“内部对象能不能共享”。

```python
import copy

# 元素都是不可变对象时，浅拷贝通常就够
config = {"host": "localhost", "port": 8080}
new_config = copy.copy(config)
new_config["port"] = 9090
print(config)      # {'host': 'localhost', 'port': 8080}
print(new_config)  # {'host': 'localhost', 'port': 9090}

# 嵌套结构要独立修改时，用深拷贝
team = {"members": ["Alice", "Bob"]}
team_copy = copy.deepcopy(team)
team_copy["members"].append("Carol")
print(team)       # {'members': ['Alice', 'Bob']}
print(team_copy)  # {'members': ['Alice', 'Bob', 'Carol']}
```

关键结论：
- 不可变对象（immutable object）如 `int`、`str`、`tuple`，浅拷贝往往足够。
- 嵌套可变结构，且要独立修改，优先考虑 `deepcopy()`。
- 性能敏感时，先判断能否用浅拷贝或重新构造，而不是无脑深拷贝。

---

## 5. 自定义类里发生了什么

浅拷贝和深拷贝也适用于自定义对象。默认情况下，Python 会复制实例的 `__dict__`，但里面的属性对象是否共享，取决于拷贝方式。

```python
import copy

class Box:
    def __init__(self, items):
        self.items = items

box1 = Box([1, 2, 3])
box2 = copy.copy(box1)
box3 = copy.deepcopy(box1)

print(box1 is box2)        # False
print(box1.items is box2.items)  # True，浅拷贝共享 items
print(box1.items is box3.items)  # False，深拷贝复制了 items
```

关键结论：
- `copy.copy()` 创建新实例，但属性引用可能共享。
- `copy.deepcopy()` 会递归复制属性。
- 如果自定义类需要控制拷贝行为，可以实现 `__copy__()` 和 `__deepcopy__()`。

---

## 动手练习

任务：实现一个“学生成绩表”的安全复制。

要求：
1. 创建一个字典 `student = {"name": "Tom", "scores": [80, 90]}`。
2. 用浅拷贝复制一份，修改复制后的 `scores` 列表，观察原数据是否变化。
3. 用深拷贝复制一份，修改复制后的 `scores` 列表，观察原数据是否变化。
4. 写一个函数 `safe_copy(data)`，对包含嵌套列表或字典的数据返回深拷贝，并说明为什么。

参考代码：

```python
import copy

student = {"name": "Tom", "scores": [80, 90]}

shallow = copy.copy(student)
shallow["scores"].append(100)
print(student)  # 原数据会被影响

deep = copy.deepcopy(student)
deep["scores"].append(95)
print(student)  # 原数据不受影响

def safe_copy(data):
    return copy.deepcopy(data)
```

完成后请回答：为什么浅拷贝修改 `scores` 会影响原字典？

```python
import copy

# 赋值：共享同一个对象
a = [1, 2, 3]
b = a
b.append(4)
print("赋值:", a, a is b)

# 浅拷贝：外层新对象，内层共享
original = [[1, 2], [3, 4]]
shallow = copy.copy(original)
print("浅拷贝外层是否相同:", original is shallow)
print("浅拷贝内层是否相同:", original[0] is shallow[0])
shallow[0][0] = 99
print("浅拷贝修改后 original:", original)

# 深拷贝：完全独立
original2 = [[1, 2], [3, 4]]
deep = copy.deepcopy(original2)
print("深拷贝外层是否相同:", original2 is deep)
print("深拷贝内层是否相同:", original2[0] is deep[0])
deep[0][0] = 99
print("深拷贝修改后 original2:", original2)
print("深拷贝修改后 deep:", deep)
```


---

## 本课题目

### single_choice · None



- [A] [[99, 2], [3, 4]]
- [B] [[1, 2], [3, 4]]
- [C] [[99, 2], [99, 4]]
- [D] 报错

**参考答案**：0

**解析**：浅拷贝只复制外层列表，内层列表仍被共享，因此修改 y[0][0] 会影响 x。

### single_choice · None



- [A] [(1, 2), (3, 4)]
- [B] [(9, 9), (3, 4)]
- [C] [(1, 2), (9, 9)]
- [D] 报错

**参考答案**：0

**解析**：外层列表被浅拷贝，且元组是不可变的，直接替换 b[0] 只改变 b，不影响 a。

### single_choice · None



- [A] [x for row in data for x in row]
- [B] [x for x in row for row in data]
- [C] [row for row in data]
- [D] [x for x in data]

**参考答案**：0

**解析**：嵌套列表推导式的外层 for 先遍历行，内层 for 再遍历元素，顺序不能颠倒。

### single_choice · None



- [A] {'a': [1, 2]}
- [B] {'a': [1]}
- [C] {'a': [2]}
- [D] {'a': []}

**参考答案**：0

**解析**：setdefault 在键存在时返回已有列表，因此两次 append 作用于同一个列表。

### single_choice · None



- [A] 1
- [B] 2
- [C] 报错
- [D] None

**参考答案**：1

**解析**：浅拷贝只复制外层字典，内层字典仍被共享，因此修改 e 的内层字典会影响 d。

### single_choice · None



- [A] 嵌套容器只能用列表和字典组合
- [B] 嵌套容器中的内层对象可以被外层容器共享
- [C] 嵌套容器总是深拷贝
- [D] 嵌套容器无法被遍历

**参考答案**：1

**解析**：嵌套容器只是引用的组合，多个外层位置可能共享同一个内层对象。

### single_choice · None



- [A] 2
- [B] 3
- [C] 报错
- [D] 1

**参考答案**：1

**解析**：b = a 只是把同一个列表的引用赋给 b，没有创建新列表，所以 a 也增加了一个元素。

### single_choice · None



- [A] [2, 4, 6, 8]
- [B] [[2, 4], [6, 8]]
- [C] [2, 4, 3, 8]
- [D] 报错

**参考答案**：0

**解析**：推导式先展平再对每个元素乘以 2，得到一维列表 [2, 4, 6, 8]。

### single_choice · None



- [A] list(lst)
- [B] lst[:]
- [C] copy.deepcopy(lst)
- [D] lst.copy()

**参考答案**：2

**解析**：前三者都是浅拷贝，只有 copy.deepcopy 会递归复制所有嵌套层级。

### single_choice · None



- [A] (1, [2, 3, 4])
- [B] 报错
- [C] (1, [2, 3][4])
- [D] (1, [2, 3])

**参考答案**：0

**解析**：+= 对列表是原地扩展（extend），不会替换元组元素，因此元组引用不变但列表内容改变。

### single_choice · None



- [A] 可以，键是列表
- [B] 不可以，列表不可哈希
- [C] 可以，但键会被转换为元组
- [D] 不可以，字典键必须是字符串

**参考答案**：1

**解析**：字典键必须可哈希，列表是可变对象，不可哈希，因此会抛 TypeError。

### single_choice · None



- [A] 5
- [B] 6
- [C] 3
- [D] 2

**参考答案**：0

**解析**：matrix[1] 是 [3, 4, 5]，其索引 2 的元素是 5。

### single_choice · None



- [A] [[0] * 3] * 3
- [B] [[0] * 3 for _ in range(3)]
- [C] [0] * 9
- [D] [[0, 0, 0]] * 3

**参考答案**：1

**解析**：列表推导式每次迭代都会创建新的内层列表；而乘法复制的是同一对象的引用。

### single_choice · None



- [A] 嵌套容器不能被嵌套 for 遍历
- [B] 嵌套 for 遍历时必须使用索引
- [C] 嵌套 for 遍历时内外层顺序可以任意交换而不影响结果
- [D] 嵌套 for 遍历时需按层级顺序依次进入每一层

**参考答案**：3

**解析**：遍历嵌套结构需要按层级依次进入，外层对应上层容器，内层对应下层容器。

### single_choice · None



- [A] [[1, 0, 0], [0, 0, 0], [0, 0, 0]]
- [B] [[1, 0, 0], [1, 0, 0], [1, 0, 0]]
- [C] [[1, 1, 1], [1, 1, 1], [1, 1, 1]]
- [D] 报错

**参考答案**：1

**解析**：乘法创建的三行指向同一个内层列表，因此修改一行会影响所有行。

### single_choice · None



- [A] [1, 2]
- [B] [1, 2, 5]
- [C] [5]
- [D] 报错

**参考答案**：1

**解析**：dict.copy() 是浅拷贝，内层列表仍被共享，因此 append 会同时反映到 d。

### single_choice · None



- [A] grid[2][3]
- [B] grid[1][2]
- [C] grid[3][2]
- [D] grid[2, 3]

**参考答案**：1

**解析**：Python 列表下标从 0 开始，第二行是索引 1，第三列是索引 2。

### single_choice · None



- [A] ([9, 2], [3, 4])
- [B] ([1, 2], [3, 4])
- [C] 报错，元组不可变
- [D] ([9, 2], [9, 4])

**参考答案**：0

**解析**：元组本身不可变，但其中包含的列表是可变的，可以修改列表内部元素。

### single_choice · None



- [A] 2
- [B] 4
- [C] 报错，集合不能包含元组
- [D] 1

**参考答案**：0

**解析**：元组是可哈希的，可以作为集合元素；集合包含两个不同的元组。

### single_choice · None



- [A] (1, 2)
- [B] frozenset({1, 2})
- [C] [1, 2]
- [D] 'abc'

**参考答案**：2

**解析**：列表是可变的、不可哈希的，不能作为字典键；元组、frozenset 和字符串都可以。

### single_choice · None



- [A] 1 2 3 4 
- [B] 1 3 2 4 
- [C] 1 2 3 4
- [D] 报错

**参考答案**：0

**解析**：外层循环遍历行，内层循环遍历每行元素，按行优先顺序输出。

### single_choice · None



- [A] [1, 2, [3, 4]]
- [B] [99, 2, [88, 4]]
- [C] [1, 2, [88, 4]]
- [D] [99, 2, [3, 4]]

**参考答案**：2

**解析**：list.copy() 是浅拷贝：新列表的顶层元素被独立复制，所以修改 b[0] 不影响 a。但嵌套的可变对象（内层列表）仍被共享引用，因此修改 b[2][0] 会同时改变 a 的内层列表，结果是 [1, 2, [88, 4]]。

### single_choice · None



- [A] b = a.copy()
- [B] b = list(a)
- [C] b = copy.copy(a)
- [D] b = copy.deepcopy(a)

**参考答案**：3

**解析**：copy.deepcopy 会递归复制对象图中的所有对象。a.copy()、list(a) 和 copy.copy(a) 都只做浅拷贝，嵌套可变对象仍被共享。

### multi_choice · None



- [A] copied = config.copy()
- [B] copied = copy.deepcopy(config)
- [C] copied = dict(config)
- [D] copied = json.loads(json.dumps(config))（config 可被 JSON 序列化时）

**参考答案**：[1, 3]

**解析**：config.copy() 和 dict(config) 都是浅拷贝，嵌套的可变对象仍被共享，修改会影响原配置。copy.deepcopy 完全独立；json 往返序列化对可 JSON 化的结构也能得到独立副本。

### multi_choice · None



- [A] copy.copy 对不可变对象可能直接返回原对象
- [B] copy.deepcopy 使用 memo 字典处理已复制对象，从而支持循环引用
- [C] copy.copy 一定返回与原对象不同的新对象
- [D] copy.deepcopy 可以复制自定义类的实例（默认按 __dict__ 递归复制）
- [E] copy.copy 与 copy.deepcopy 对同一对象总是返回相同结果

**参考答案**：[0, 1, 3]

**解析**：A 正确（如元组）；B 正确（deepcopy 的 memo 机制）；D 正确（默认递归复制实例属性）。C 错误，copy.copy 对元组等不可变对象可能返回原对象；E 错误，二者语义不同，结果常不同。

### fill_blank · None



**参考答案**：["deepcopy"]

**解析**：copy.deepcopy 会递归复制整个对象图，产生完全独立的副本；copy.copy 只是浅拷贝。

### fill_blank · None



**参考答案**：["100"]

**解析**：a.copy() 是浅拷贝，内层列表被 a 和 b 共享，修改 b[0][0] 会同时改变 a[0][0]，所以为 100。

### fill_blank · None



**参考答案**：["import copy", "from copy import deepcopy"]

**解析**：既可以 import copy 后使用 copy.deepcopy，也可以 from copy import deepcopy 直接使用 deepcopy。

### code_reading · None



**参考答案**：输出 [1, 2, [3, 4]]。因为 deepcopy 递归复制了内层列表，b 的内层列表与 a 的内层列表完全独立，修改 b 不影响 a。

**解析**：深拷贝会递归复制所有嵌套可变对象，副本与原对象完全独立。若换成 copy.copy 或 a.copy()，则输出会变成 [1, 2, [99, 4]]。

### code_reading · None



**参考答案**：输出 [[100, 2], [100, 2], [100, 2]]，因为三次 append 的是同一个 inner 列表对象，它们共享引用。修复方式：每次 append 时复制，例如 outer.append(inner.copy()) 或 outer.append(list(inner))，或使用 copy.deepcopy(inner)。

**解析**：循环中若反复追加同一可变对象，外层容器各元素会指向同一对象；修改一处会全部改变。应追加独立的浅/深拷贝副本。

### code_reading · None



**参考答案**：输出 True。deepcopy 会借助 memo 字典处理循环引用，正确重建循环结构，使副本中 copy1.next.next 仍然指回 copy1。

**解析**：若没有 memo 机制，循环引用会导致无限递归。copy.deepcopy 在复制过程中记录已复制对象，遇到已复制对象直接复用副本，从而支持循环引用。

### scenario · None



**解析**：生成副本时若只用 DEFAULT_CONFIG.copy() 或 dict(DEFAULT_CONFIG)，属于浅拷贝，嵌套的 rate_limit 子字典仍被所有请求共享，导致互相干扰。应使用 copy.deepcopy(DEFAULT_CONFIG) 为每个请求创建完全独立的副本；或在修改前对嵌套子字典单独复制。

### scenario · None



**解析**：document.copy() 只是浅拷贝，嵌套的列表/字典仍被栈中和当前文档共享；之后用户继续编辑会污染历史快照，撤销时得到错误状态。应使用 copy.deepcopy(document) 保存真正独立的快照，或者对嵌套结构逐层复制。

### single_choice · None



- [A] 浅拷贝会报错，深拷贝不会
- [B] 两者得到的副本在此场景下行为几乎等价，因为不可变元素无法被就地修改
- [C] 深拷贝一定会共享底层元素引用，浅拷贝不会
- [D] 浅拷贝会把不可变元素变成可变元素

**参考答案**：1

**解析**：不可变对象无法被就地修改，对其元素的『修改』本质是重新绑定，因此浅拷贝和深拷贝在该场景下效果一致，这也是深拷贝在纯不可变结构上开销相对意义不大的原因。

### scenario · None



**解析**：一律使用 deepcopy 会带来不必要的递归遍历和内存开销，尤其在对象图很大或结构纯不可变（如由元组、字符串组成）时收益为零。当嵌套内容不需要独立修改、或元素本身不可变时，应优先用浅拷贝（copy.copy/copy()）以降低开销。

### single_choice · None



- [A] 浅拷贝会递归复制所有嵌套对象
- [B] 浅拷贝创建一个新容器，但容器内的元素引用与原对象相同
- [C] 浅拷贝只能用于列表，不能用于字典或集合
- [D] 浅拷贝后原对象与副本完全独立，任何修改互不影响

**参考答案**：1

**解析**：浅拷贝只复制最外层容器，元素引用被共享。它适用于列表、字典、集合等多种容器，但不能保证嵌套可变对象的独立性。

### single_choice · None



- [A] {'x': [1, 2, 3]}
- [B] {'x': [1, 2]}
- [C] {'x': 3}
- [D] 抛出异常

**参考答案**：0

**解析**：dict(d1) 是浅拷贝，字典的键值对引用被复制，但列表对象仍被 d1 和 d2 共享。对共享列表 append 后，d2['x'] 变为 [1, 2, 3]。

### single_choice · None



- [A] True
- [B] False
- [C] 报错
- [D] 取决于 Python 版本

**参考答案**：0

**解析**：元组是不可变对象，copy.copy 对元组的浅拷贝通常直接返回原对象本身（因为无法就地修改），因此 a is b 为 True。注意元组内部若含可变对象，修改该可变对象仍会影响双方。

### single_choice · None



- [A] 深拷贝会递归复制嵌套对象
- [B] 深拷贝后的副本与原对象完全独立，修改互不影响
- [C] 深拷贝一定比浅拷贝快，所以应优先使用
- [D] 深拷贝可能因为对象间存在循环引用而需要额外处理

**参考答案**：2

**解析**：深拷贝需要递归遍历并复制整个对象图，通常比浅拷贝慢、开销大。它并非总是更快，也不应无条件优先使用；通常在需要完全独立副本时才用。

### single_choice · None



- [A] [[1, 0, 0], [0, 0, 0], [0, 0, 0]]
- [B] [[1, 0, 0], [1, 0, 0], [1, 0, 0]]
- [C] [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
- [D] 报错

**参考答案**：1

**解析**：[[0] * 3] * 3 中，外层列表的三个元素引用同一个内层列表对象。因此修改任意一行的元素会同时影响所有行，输出为 [[1,0,0],[1,0,0],[1,0,0]]。这是浅拷贝/共享引用的常见陷阱。

### multi_choice · None



- [A] b = a.copy()，其中 a 是列表
- [B] b = copy.copy(a)
- [C] b = copy.deepcopy(a)
- [D] b = a[:]，其中 a 是列表
- [E] b = dict(a)，其中 a 是字典

**参考答案**：[0, 1, 3, 4]

**解析**：列表的 copy()、copy.copy()、切片 a[:]、dict(a) 都是浅拷贝；copy.deepcopy(a) 是深拷贝。

### multi_choice · None



- [A] 深拷贝会递归复制嵌套的可变对象
- [B] 深拷贝后的对象与原对象之间通常不存在共享的可变子对象
- [C] 深拷贝总是比浅拷贝执行更快
- [D] 深拷贝能够正确处理对象间的循环引用
- [E] 深拷贝对纯不可变对象结构也会产生明显的额外价值

**参考答案**：[0, 1, 3]

**解析**：深拷贝递归复制并处理循环引用（借助 memo 机制），因此 A、B、D 正确。C 错误，深拷贝通常更慢；E 错误，纯不可变结构下深浅拷贝效果等价，深拷贝无显著额外价值。
