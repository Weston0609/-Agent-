# s1u4l4 字典基础 / 字典方法（dict methods）：从查表到工程实践

> 来源 `content/lessons/s1u4l4.json`

## py.type.dict_basic

# py.type.dict_basic：字典基础

## 一句话直觉

字典（dict）就是 Python 里的「通讯录/查表」：你给它一个键（key），它立刻告诉你对应的值（value）。当你要按名字、编号、标签之类的东西快速找数据时，第一个想到的就是它。

本讲义对应课程 `s1u4l4`，知识点 `py.type.dict_basic`，为零基础到工程级准备的字典入门。

---

## 1. 字典是什么：键值对的集合

字典用花括号 `{}` 写，里面是一组 `键: 值` 对，键和值之间用冒号分隔，对与对之间用逗号分隔。

- 键（key）：用来查找的“名字”，必须是不可变（immutable）的类型，如字符串、数字、元组。
- 值（value）：任意 Python 对象，可变、可嵌套都行。

```python
# 用花括号创建字典
person = {"name": "Alice", "age": 30, "city": "Beijing"}

# 用 dict() 构造
empty = dict()                      # 空字典
pairs = dict([("a", 1), ("b", 2)]) # 从可迭代的键值对构造

print(person)        # {'name': 'Alice', 'age': 30, 'city': 'Beijing'}
print(pairs)         # {'a': 1, 'b': 2}
```

**关键结论**：字典不关心顺序（Python 3.7+ 虽然保持插入顺序，但语义上仍按“键”访问），它关心的是“键 → 值”的映射。

---

## 2. 增删改查：四种基本操作

访问用方括号 `d[键]`；赋值 `d[键] = 值` 会更新或新增；删除用 `del d[键]`。

```python
stock = {"apple": 10, "banana": 5}

# 查
print(stock["apple"])      # 10

# 增 / 改：key 存在就覆盖，不存在就新增
stock["apple"] = 12        # 改
stock["cherry"] = 7        # 增

# 删
del stock["banana"]

print(stock)                # {'apple': 12, 'cherry': 7}
```

如果访问不存在的键，会抛 `KeyError`。工程上更常用 `.get()`，它可以在键不存在时返回一个默认值，避免程序崩溃：

```python
print(stock.get("apple"))        # 12
print(stock.get("durian"))       # None
print(stock.get("durian", 0))    # 0
```

**关键结论**：习惯用 `.get(key, default)` 替代 `d[key]`，让你的代码在缺失数据时仍能继续运行。

---

## 3. 遍历字典：keys、values、items

字典的三个视图对象（view）让你可以按需遍历：`.keys()`、`.values()`、`.items()`。

```python
scores = {"math": 90, "english": 85, "science": 92}

# 遍历键
for subject in scores.keys():
    print(subject)

# 遍历值
for score in scores.values():
    print(score)

# 同时拿键和值（工程里最常用）
for subject, score in scores.items():
    print(f"{subject}: {score}")
```

`in` 运算符检查的是“键”是否在字典中，而不是值：

```python
print("math" in scores)     # True
print("history" in scores)  # False
```

**关键结论**：`for k, v in d.items()` 是最常见的遍历方式，几乎成了 Python 的“成语”。

---

## 4. 常用方法与嵌套：工程级用法

一些常用方法：`keys()`、`values()`、`items()`、`get()`、`pop()`、`update()`、`setdefault()`、`clear()`。嵌套字典则用来表示层级数据，比如 JSON 配置。

```python
config = {"db": {"host": "localhost", "port": 5432}, "debug": True}

# 嵌套访问
print(config["db"]["host"])   # localhost

# setdefault：键不存在时才写入默认值
config.setdefault("retries", 3)
print(config["retries"])       # 3

# update：批量更新/合并
config.update({"debug": False, "timeout": 30})
print(config["debug"], config["timeout"])  # False 30

# pop：取出并删除
port = config["db"].pop("port")
print(port, config["db"])      # 5432 {'host': 'localhost'}
```

**关键结论**：字典可以嵌套任意层，用来表示真实世界的结构化数据；`setdefault`、`update`、`pop` 是写“配置合并 / 缓存”类代码的利器。

---

## 5. 类型提示：用 dict[K, V] 标注字典

Python 3.9+ 支持内置泛型 `dict[K, V]`，`typing` 模块里也有等价的写法。类型提示（type hint）不会被运行时强制，但 IDE、mypy、pyright 等静态检查器（static type checker）会据此帮你提前发现错误。

```python
# Python 3.9+ 写法
def total_price(cart: dict[str, float]) -> float:
    return sum(cart.values())

# 旧版本兼容写法
from typing import Dict
def total_price_compat(cart: Dict[str, float]) -> float:
    return sum(cart.values())

print(total_price({"apple": 1.5, "banana": 2.0}))  # 3.5
```

官方文档明确指出：类型提示在运行时不会被强制，它们用于静态检查器、IDE 和 linter。也就是说，写错了 `dict[str, float]` 仍然能跑，但检查工具会提醒你。

**关键结论**：给字典加类型提示，是让“工程级代码”可维护的关键一步：`dict[str, int]` 比裸 `dict` 表达力强得多。

---

## 动手练习

**任务**：写一个小脚本 `word_count.py`，统计一段文本中每个单词出现的次数，并按出现次数从高到低打印前 5 个单词。

要求：
1. 使用字典 `counts` 保存“单词 → 次数”。
2. 使用 `.get(word, 0) + 1` 或 `collections.Counter` 计数。
3. 使用 `sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:5]` 取前 5。
4. 给 `counts` 加上类型提示 `dict[str, int]`。

示例文本：`"the quick brown fox jumps over the lazy dog the fox"`。

预期输出（顺序）：
```
the: 3
fox: 2
quick: 1
brown: 1
jumps: 1
```

完成后，试着改成读取一个 `.txt` 文件并做同样统计。

```python
from collections import Counter

# 示例文本
text = "the quick brown fox jumps over the lazy dog the fox"
words = text.split()

# 方法一：手动用 dict.get 计数
counts: dict[str, int] = {}
for word in words:
    counts[word] = counts.get(word, 0) + 1

# 方法二：更简洁的 Counter
counts2 = Counter(words)

# 取出现次数最多的前 5 个
top5 = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:5]

for word, n in top5:
    print(f"{word}: {n}")

# 基础操作演示
person = {"name": "Alice", "age": 30}
print(person["name"])            # 查
person["city"] = "Beijing"      # 增
person["age"] = 31              # 改
del person["city"]               # 删
print(person)
print("name" in person)          # 成员检查（检查键）
print(person.get("salary", 0))   # 缺失时返回默认值
```

## py.type.dict_method

# 字典方法（dict methods）：从查表到工程实践

> **一句话直觉**：字典（dict）是 Python 里最常用的“键值对仓库”，而 `dict` 的方法（methods）就是你操作这个仓库的“标准工具箱”——学会它们，你写业务代码、做数据处理、实现缓存都会快一个数量级。

本讲义面向零基础到工程级，共 5 个小节，每节都配可运行代码。

---

## 1. 字典是什么？先建立直观

字典（dictionary，`dict`）是一种**可变（mutable）映射（mapping）**：

- 用**键（key）**查找**值（value）**；
- 键必须**可哈希（hashable）**，比如 `str`、`int`、`tuple`；
- 值可以是任意对象；
- 平均查找复杂度 O(1)。

```python
# 创建一个字典
user = {"name": "Alice", "age": 30}

# 用键访问值
print(user["name"])        # Alice

# 用键赋值/修改
user["age"] = 31
print(user)                # {'name': 'Alice', 'age': 31}

# 键不存在时用 [] 会抛 KeyError
# print(user["email"])     # KeyError: 'email'
```

这里 `user["name"]` 是**下标访问**，还不是“方法”。下面我们进入正题：`dict` 自带的**方法**。

---

## 2. 最常用的读取三剑客：`get` / `keys` / `values` / `items`

### 2.1 `get(key, default=None)`：查不到也不报错

业务里最常见的场景是“键可能不存在”。用 `[]` 会崩，用 `get` 更安全。

```python
user = {"name": "Alice"}

# 键不存在时返回 None
print(user.get("email"))              # None

# 键不存在时返回指定默认值
print(user.get("email", "未填写"))   # 未填写

# 键存在时正常返回
print(user.get("name"))               # Alice
```

### 2.2 `keys()` / `values()` / `items()`：遍历视图

这三个方法返回的是**视图对象（view object）**，会随字典变化而变化，不是快照。

```python
scores = {"math": 90, "english": 85, "python": 95}

print(list(scores.keys()))    # ['math', 'english', 'python']
print(list(scores.values()))  # [90, 85, 95]

# items() 返回 (key, value) 元组，是遍历字典最常用的方式
for subject, score in scores.items():
    print(f"{subject}: {score}")
```

### 2.3 视图会“跟着变”

```python
d = {"a": 1}
ks = d.keys()
print(list(ks))     # ['a']
d["b"] = 2
print(list(ks))     # ['a', 'b']  —— 视图跟着更新了
```

---

## 3. 增删改的关键方法：`update` / `setdefault` / `pop` / `popitem` / `clear`

### 3.1 `update(other)`：批量合并/更新

```python
config = {"host": "localhost", "port": 8000}
config.update({"port": 9000, "debug": True})
print(config)  # {'host': 'localhost', 'port': 9000, 'debug': True}
```

### 3.2 `setdefault(key, default)`：不存在才写入

这是构建“分组”“倒排索引”时的神器。

```python
words = ["apple", "banana", "avocado", "blueberry"]
by_first_letter = {}

for w in words:
    by_first_letter.setdefault(w[0], []).append(w)

print(by_first_letter)
# {'a': ['apple', 'avocado'], 'b': ['banana', 'blueberry']}
```

### 3.3 `pop` / `popitem` / `clear`

```python
d = {"x": 1, "y": 2}

# pop 按键删除并返回值
print(d.pop("x"))          # 1
print(d.pop("z", None))    # None（键不存在时返回默认值）
print(d)                   # {'y': 2}

# popitem 删除并返回最后一个插入的键值对（LIFO）
key, value = d.popitem()
print(key, value)          # y 2

# clear 清空
d.clear()
print(d)                   # {}
```

---

## 4. 进阶：`fromkeys` / `copy` / 字典推导式

### 4.1 `fromkeys`：用一组键批量建字典

```python
keys = ["a", "b", "c"]
d = dict.fromkeys(keys, 0)
print(d)  # {'a': 0, 'b': 0, 'c': 0}
```

⚠️ 当默认值是可变对象时，会共享同一个对象（见误区部分）。

### 4.2 `copy()`：浅拷贝

```python
original = {"a": [1, 2]}
shallow = original.copy()
shallow["a"].append(3)
print(original)  # {'a': [1, 2, 3]}  —— 嵌套对象仍是共享的
```

### 4.3 字典推导式（dict comprehension）

```python
squares = {n: n * n for n in range(5)}
print(squares)  # {0: 0, 1: 1, 2: 4, 3: 9, 4: 16}
```

### 4.4 合并运算符（Python 3.9+）

```python
a = {"x": 1}
b = {"y": 2}
print(a | b)   # {'x': 1, 'y': 2}
a |= b
print(a)       # {'x': 1, 'y': 2}
```

---

## 5. 工程视角：类型标注与方法选择

### 5.1 给字典加类型提示（type hints）

```python
from typing import TypedDict

class User(TypedDict):
    name: str
    age: int

user: User = {"name": "Alice", "age": 30}
```

`TypedDict` 能在静态检查器（如 mypy）下发现拼错键、类型错误。

### 5.2 方法选择速查

| 需求 | 推荐方法 |
|------|----------|
| 安全取值 | `get` |
| 遍历键值 | `items()` |
| 分组/初始化 | `setdefault` |
| 批量合并 | `update` / `|=` |
| 安全删除 | `pop(key, default)` |
| 复制一层 | `copy()` |
| 结构约束 | `TypedDict` |

---

## 动手练习

**任务：实现一个“单词首字母分组统计器”。**

要求：

1. 给定一段文本，用 `split()` 拆成单词；
2. 用 `setdefault` 或 `items()` 统计：**每个首字母下有哪些单词**、**每个首字母的单词数量**；
3. 最终输出形如：`a: 3 -> ['apple', 'avocado', 'ant']`；
4. 用 `get` 安全读取某个字母的数量，键不存在时返回 0；
5. 额外用 `TypedDict` 给结果结构加类型提示，并尝试用 mypy 检查。

提示：先构造空字典，遍历单词，用 `word[0].lower()` 作为键。

---

**小结**：`dict` 方法贯穿了从入门到工程的全部环节——安全取值用 `get`，遍历用 `items`，分组用 `setdefault`，合并用 `update`。掌握这套工具箱，你就能写出既简洁又健壮的 Python 数据代码。

```python
from typing import TypedDict, Dict, List


class GroupResult(TypedDict):
    words: Dict[str, List[str]]
    counts: Dict[str, int]


def group_by_first_letter(text: str) -> GroupResult:
    """按首字母分组统计单词。"""
    words_by_letter: Dict[str, List[str]] = {}
    counts: Dict[str, int] = {}

    for word in text.split():
        word = word.strip(".,!?").lower()
        if not word:
            continue
        first = word[0]
        # setdefault 分组：键不存在时先放入空列表
        words_by_letter.setdefault(first, []).append(word)
        # update 累加计数，get 安全读取旧值
        counts[first] = counts.get(first, 0) + 1

    return {"words": words_by_letter, "counts": counts}


def main() -> None:
    text = "Apple banana Avocado blueberry ant Cherry, apple!"
    result = group_by_first_letter(text)

    # 按首字母排序输出
    for letter in sorted(result["words"]):
        words = result["words"][letter]
        count = result["counts"].get(letter, 0)
        print(f"{letter}: {count} -> {words}")

    # 演示 get 默认值
    print("z 的数量:", result["counts"].get("z", 0))

    # 演示 items 遍历
    for letter, count in result["counts"].items():
        assert count == len(result["words"][letter])


if __name__ == "__main__":
    main()
```


---

## 本课题目

### single_choice · None



- [A] {'a': 1, 'b': 2}
- [B] {'b': 2}
- [C] {'a': 1}
- [D] 抛出 KeyError

**参考答案**：0

**解析**：通过键赋值是新增或更新字典项的方式，键 'b' 不存在时会被追加，原有键 'a' 保留。

### single_choice · None



- [A] None
- [B] 0
- [C] 抛出 KeyError
- [D] 抛出 IndexError

**参考答案**：2

**解析**：使用方括号访问不存在的键会抛出 KeyError，而不是返回 None。

### single_choice · None



- [A] {'a': 1, 'b': 2}
- [B] {}
- [C] None
- [D] 抛出异常

**参考答案**：1

**解析**：clear 清空字典中的所有项，d 变为空字典 {}。

### single_choice · None



- [A] ['a'] [1] [('a', 1)]
- [B] ['a'] ['a'] [('a', 1)]
- [C] [1] ['a'] [('a', 1)]
- [D] [('a', 1)] [('a', 1)] [('a', 1)]

**参考答案**：0

**解析**：keys 返回键视图，values 返回值视图，items 返回键值对视图。

### single_choice · None



- [A] a 1 b 2
- [B] a b
- [C] 1 2
- [D] ('a', 1) ('b', 2)

**参考答案**：1

**解析**：直接 for 遍历字典时迭代的是键，而不是值或键值对。

### single_choice · None



- [A] 1
- [B] 100
- [C] None
- [D] 抛出 KeyError

**参考答案**：0

**解析**：setdefault 只有在键不存在时才设置默认值；键 'a' 已存在，故保持不变，仍为 1。

### single_choice · None



- [A] {'a': [1, 2]}
- [B] {'a': [1]}
- [C] {'a': [2]}
- [D] {'a': []}

**参考答案**：0

**解析**：第一次 setdefault 创建并返回空列表，第二次键已存在，返回原列表，两次 append 都作用在同一列表上。

### single_choice · None



- [A] {'a': 1, 'b': 2}
- [B] {'a': 100, 'b': 2}
- [C] {'b': 2}
- [D] {'a': 1, 'a': 100, 'b': 2}

**参考答案**：1

**解析**：update 对已存在的键 'a' 覆盖其值，对新键 'b' 新增，故 a 变为 100。

### single_choice · None



- [A] {0: 0, 1: 2, 2: 4}
- [B] {0: 0, 1: 1, 2: 2}
- [C] [0, 2, 4]
- [D] {1: 2, 2: 4, 3: 6}

**参考答案**：0

**解析**：字典推导式 {k: k * 2 for k in range(3)} 生成键 0、1、2，值为 0、2、4。

### single_choice · None



- [A] 可以，键为列表 [1, 2]
- [B] 不可以，列表不可哈希，不能作为字典键
- [C] 可以，但访问时需要用 d[[1, 2]]
- [D] 可以，键会自动转换为元组 (1, 2)

**参考答案**：1

**解析**：字典的键必须是可哈希对象，列表是可变类型、不可哈希，因此不能作为键。

### single_choice · None



- [A] 0
- [B] 1
- [C] 2
- [D] 抛出 KeyError

**参考答案**：1

**解析**：在 Python 中 1 == True 且 hash(1) == hash(True)，因此它们是同一个键，第二次赋值覆盖第一次，只有一个键值对。

### single_choice · None



- [A] KeyError
- [B] None
- [C] -1
- [D] 'z'

**参考答案**：2

**解析**：pop 的第二个参数是键不存在时返回的默认值，故返回 -1。

### single_choice · None



- [A] KeyError
- [B] None
- [C] 0
- [D] ''

**参考答案**：1

**解析**：dict.get 在键不存在时默认返回 None，这正是它与方括号访问的关键区别。

### single_choice · None



- [A] KeyError
- [B] None
- [C] 0
- [D] 1

**参考答案**：2

**解析**：get 的第二个参数是键不存在时返回的默认值，因此返回 0。

### single_choice · None



- [A] {'a': 1}
- [B] {'a': 99}
- [C] 1
- [D] 99

**参考答案**：1

**解析**：d2 = d1 只赋值引用，两个名字指向同一个字典，修改 d2 也修改了 d1。

### single_choice · None



- [A] d1 和 d2 都是 {'a': 99}
- [B] d1 是 {'a': 1}，d2 是 {'a': 99}
- [C] d1 是 {'a': 99}，d2 是 {'a': 1}
- [D] 两者都抛出异常

**参考答案**：1

**解析**：dict(d1) 创建浅拷贝，d2 是独立对象，修改它不影响 d1。

### single_choice · None



- [A] 2
- [B] 3
- [C] 6
- [D] 抛出异常

**参考答案**：1

**解析**：len 返回字典中键值对的数量，这里有 'a'、'b'、'c' 三个键。

### single_choice · None



- [A] True True
- [B] True False
- [C] False True
- [D] False False

**参考答案**：1

**解析**：in 运算符对字典检查的是键，不是值，因此 'a' in d 为 True，1 in d 为 False。

### single_choice · None



- [A] {'a': 1, 'b': 2}
- [B] {'b': 2}
- [C] {'a': 1}
- [D] {}

**参考答案**：1

**解析**：del 会按键删除对应的键值对，剩余 {'b': 2}。

### single_choice · None



- [A] 1
- [B] 2
- [C] {'b': 2}
- [D] 抛出 KeyError

**参考答案**：0

**解析**：pop 删除指定键并返回其值，所以输出 1（同时 d 变为 {'b': 2}）。

### single_choice · None



- [A] d.get('k') 在键不存在时会抛出 KeyError
- [B] d.get('k') 在键不存在时返回 None（或指定的默认值）
- [C] d.get('k') 会向字典中插入键 'k' 并赋值为 None
- [D] d.get('k') 只能用于读取，不能提供默认值

**参考答案**：1

**解析**：get 方法在键不存在时不会抛异常，而是返回 None，或返回调用时传入的第二个参数作为默认值；它也不会修改字典。

### single_choice · None



- [A] 抛出 KeyError
- [B] None
- [C] 0
- [D] 1

**参考答案**：2

**解析**：pop 在键不存在时若有提供默认值则返回该默认值，不抛异常；这里默认值是 0。

### single_choice · None



- [A] 随机删除并返回一个键值对
- [B] 删除并返回最后一个插入的键值对（LIFO 顺序）
- [C] 删除并返回第一个插入的键值对
- [D] 必须传入键作为参数

**参考答案**：1

**解析**：Python 3.7+ 中 popitem 按 LIFO 顺序移除并返回最后插入的键值对，空字典调用会抛 KeyError。

### multi_choice · None



- [A] get 不会因键不存在而抛 KeyError
- [B] 使用 d['k'] 读取不存在的键会抛 KeyError
- [C] setdefault 可以用于初始化缺失键的默认值
- [D] pop 在键不存在且未提供默认值时会抛 KeyError
- [E] in 运算符会抛出异常，需要用 has_key 代替

**参考答案**：[0, 1, 2, 3]

**解析**：get 和带默认值的 pop 不会抛键错误，d['k'] 与无默认值 pop 会抛 KeyError，setdefault 可初始化默认值；Python 3 中字典没有 has_key 方法，用 in 即可。

### multi_choice · None



- [A] d.update({'a': 1})
- [B] d.setdefault('b', 0)
- [C] d.get('c', 9)
- [D] d.pop('a')
- [E] d.keys()

**参考答案**：[0, 1, 3]

**解析**：update 覆盖/新增键值，setdefault 在键缺失时插入，pop 删除键；get 只是读取，keys 返回视图不修改字典。

### multi_choice · None



- [A] d1.update(d2) 会把 d2 的项并入 d1，键冲突时以 d2 为准
- [B] {**d1, **d2} 生成新字典，冲突时以 d2 为准
- [C] d1 | d2 在 Python 3.9+ 中可用，返回合并后的新字典
- [D] update 会返回合并后的新字典

**参考答案**：[0, 1, 2]

**解析**：update 原地修改并返回 None；{**d1, **d2} 与 d1 | d2 均生成新字典且右侧优先。

### fill_blank · None



**参考答案**：["get", "get()"]

**解析**：字典的 get 方法支持提供默认值，键不存在时返回该默认值而不会抛 KeyError。

### fill_blank · None



**参考答案**：["setdefault", "setdefault()"]

**解析**：setdefault 在键缺失时插入默认值并返回它，键已存在时返回现有值且不修改字典。

### code_reading · None



**参考答案**：None 0
{'a': 1, 'b': 2}

**解析**：两次 get 都不会修改字典：第一次未提供默认值返回 None，第二次提供默认值返回 0；字典内容保持不变。

### code_reading · None



**参考答案**：{'a': 2, 'b': 1}

**解析**：该模式用 get 读取计数（首次为 0）后自增，实现对元素的统计；'a' 出现两次，'b' 一次。

### code_reading · None



**参考答案**：{'y': 2}

**解析**：先用 list(d) 创建键的副本再遍历，避免遍历中修改字典；仅删除值为奇数的项，剩下 {'y': 2}。

### scenario · None



**解析**：可用 counts[api] = counts.get(api, 0) + 1 替代先判断再初始化的两步操作，逻辑集中、不易漏写初始化，语义即“取当前计数（默认 0）再加一”。

### single_choice · None



- [A] 总是把键 'k' 的值设为 []
- [B] 若键存在则返回其当前值，不修改；若不存在则插入并返回 []
- [C] 若键存在则返回 None，不存在则插入 []
- [D] 等价于 d['k'] = [] 后返回 d['k']

**参考答案**：1

**解析**：setdefault 只在键缺失时插入默认值并返回它；键已存在时直接返回已有值，不覆盖。

### scenario · None



**解析**：update 是原地修改并返回 None，因此 result 会是 None。正确做法之一是先用 copy 或 {**base} 构造新字典再 update，之二是使用 {**base, **overrides}（或 Python 3.9+ 的 base | overrides）。

### single_choice · None



- [A] 直接在 for k in d: 循环中执行 del d[k]
- [B] 遍历 list(d.keys()) 拷贝，再根据条件删除
- [C] 遍历 d.items() 并直接 del d[k]
- [D] 遍历 d 时用 d.pop(k) 删除当前键

**参考答案**：1

**解析**：遍历过程中改变字典大小会引发 RuntimeError。先转为列表拷贝再删除是安全的做法。

### single_choice · None



- [A] {'x': 1, 'y': 2, 'z': 4}
- [B] {'x': 1, 'y': 3, 'z': 4}
- [C] {'x': 1, 'y': 3}
- [D] {'y': 2, 'z': 4}

**参考答案**：1

**解析**：update 会覆盖已存在键的值并新增不存在的键，因此 y 变为 3，并新增 z: 4。

### single_choice · None



- [A] 它们返回的都是列表，可以直接索引
- [B] keys() 与 items() 返回视图，支持动态反映字典变化；values() 返回列表
- [C] keys()、values()、items() 都返回动态视图
- [D] items() 返回的是生成器，只能遍历一次

**参考答案**：2

**解析**：三者返回的都是视图对象，会动态反映字典的变化，但不是列表也不是生成器；items() 视图可多次遍历。

### single_choice · None



- [A] 整数 3
- [B] 字符串 'abc'
- [C] 元组 (1, 2)
- [D] 列表 [1, 2]

**参考答案**：3

**解析**：字典键必须可哈希；列表是可变类型，不可哈希，不能作为键。元组若元素均不可变则可哈希，可作键。

### single_choice · None



- [A] ['a', 'b', 'c']
- [B] [1, 2, 3]
- [C] [('a', 1), ('b', 2), ('c', 3)]
- [D] 报错，字典不可迭代

**参考答案**：0

**解析**：直接迭代字典等价于迭代其键，list(d) 得到键的列表（假设插入顺序为 a、b、c）。

### single_choice · None



- [A] 2 b
- [B] 1 b
- [C] 2 a
- [D] 1 a

**参考答案**：1

**解析**：1 与 1.0 哈希值相同且相等，视为同一个键，赋值会覆盖，因此字典只有一项，值为 'b'。

### single_choice · None



- [A] 两者都删除变量 d
- [B] clear() 清空字典内容但保留变量，del d 删除变量本身
- [C] clear() 删除变量，del d 清空内容
- [D] 两者都只清空内容

**参考答案**：1

**解析**：clear() 使字典变为空字典，变量仍存在；del d 会解除变量名绑定，之后引用 d 会 NameError。
