# s1u4l5 Python 类型提示中的 Set：从直觉到工程实践 / 集合类型注解与运算操作

> 来源 `content/lessons/s1u4l5.json`

## py.type.set

# Python 类型提示中的 Set：从直觉到工程实践

> 课程：s1u4l5 ｜ 知识点：py.type.set ｜ 时长：40 分钟

## 🎯 一句话直觉

`set`（集合）是 Python 中「去重 + 快速成员判断」的一等公民；在类型提示（type hints）里，**「元素的无序唯一集合」** 用 `set[T]` 表达，**「只读集合」** 用 `frozenset[T]` 表达，**「抽象集合接口」** 用 `collections.abc.Set[T]` 表达——写对了类型，IDE 和检查器（type checker，如 `mypy` / `pyright`）就能替你在运行前抓住 bug。

---

## 1. 为什么需要 Set 的类型提示？

Python 的运行时**不**强制执行类型注解，但注解是给**静态检查器 / IDE / 文档阅读者**看的（参考官方文档 Note）：

> "The Python runtime does not enforce function and variable type annotations. They can be used by third party tools such as type checkers, IDEs, linters, etc."

没有类型提示时，一个函数收 `set` 还是 `list` 全靠猜；加注解后，误传就会在编辑器里画红线。

```python
# 无类型提示 vs 有类型提示
def dedup_bad(items):            # 谁知道 items 是什么？
    return set(items)

def dedup(items: list[int]) -> set[int]:   # 一眼看清：进 list[int]，出 set[int]
    return set(items)
```

---

## 2. 三个核心形态：`set` / `frozenset` / `Set`

| 写法 | 含义 | 可变？ | 用在什么场景 |
|------|------|--------|--------------|
| `set[T]` | 唯一、无序、可变的集合 | ✅ | 会增删元素的集合 |
| `frozenset[T]` | 不可变的集合，**可哈希（hashable）** | ❌ | 做字典 key、放进另一个 set |
| `Set[T]`（来自 `collections.abc`） | 抽象只读集合接口 | — | 函数参数只读时首选 |

```python
from collections.abc import Set as AbstractSet   # 抽象接口

# 1) 具体可变集合
numbers: set[int] = {1, 2, 3}
numbers.add(4)                                    # OK

# 2) 不可变集合，可作 dict key
tags: frozenset[str] = frozenset({"py", "typing"})
index: dict[frozenset[str], int] = {tags: 1}     # 若用 set 当 key 会 TypeError

# 3) 抽象接口：既能收 set 也能收 frozenset
def count_all(items: AbstractSet[int]) -> int:
    return len(items)

count_all({1, 2})                       # OK
count_all(frozenset({1, 2}))            # OK
```

**结论**：参数位置能只读就用 `AbstractSet[T]`；返回值若允许修改就用 `set[T]`，不允许改就用 `frozenset[T]`。

---

## 3. 泛型参数 T 到底能写什么？

`set[T]` 里的 `T` 可以是任何类型表达式：`int`、`str`、`User`、`tuple[int, str]`、甚至另一个 `set`。

```python
from typing import TypeVar

T = TypeVar("T")                          # 泛型参数

def unique(items: list[T]) -> set[T]:    # 输入 list[T]，输出 set[T]，元素类型保持一致
    return set(items)

print(unique([1, 1, 2]))                 # {1, 2}
print(unique(["a", "b", "a"]))            # {'a', 'b'}
```

这里的 `T` 是**类型变量（TypeVar）**，它的价值是：调用 `unique([1,2])` 时检查器知道返回的是 `set[int]`，而不是笼统的 `set[Any]`。

注意：类型检查器把 `list[float]` 与 `Vector = list[float]` 这种别名视为等价，所以**类型别名（type alias）** 也可以作为一个「元素类型」：

```python
from typing import TypeAlias

UserId: TypeAlias = int                    # 别名，语义上给 int 一个名字
active_users: set[UserId] = {1, 2, 3}
```

---

## 4. 集合的比较与运算：类型提示跟随「输入类型」

`set` 天然支持 `|` `&` `-` `^` 这些集合运算；写类型签名时，最省心的是：**同元素类型 → 同元素类型返回**。

```python
from collections.abc import AbstractSet

def union[T](a: AbstractSet[T], b: AbstractSet[T]) -> set[T]:
    return set(a) | set(b)

def common[T](a: AbstractSet[T], b: AbstractSet[T]) -> set[T]:
    return set(a) & set(b)

print(union({1, 2}, {2, 3}))            # {1, 2, 3}
print(common({1, 2}, {2, 3}))           # {2}
```

**经验法则**：
- 想返回「新集合」时，把可变的 `set[T]` 作为返回类型；
- 只想**读**入参，参数类型用 `AbstractSet[T]`（或 `frozenset[T]`）更宽容。

---

## 5. 与 `NewType` / `Annotated` 组合的常见工程用法

类型提示的价值在**领域建模**上体现得最明显。用 `NewType` 制造「语义上不同的集合类型」，让检查器帮你阻止「把用户集合当成订单集合」这类逻辑错误。

```python
from typing import Annotated, NewType

UserId = NewType("UserId", int)

# 一个「非空集合」的注解（仅语义提示，运行时仍是普通 set）
NonEmptySet = Annotated[set[UserId], "must not be empty"]

def notify(users: NonEmptySet) -> None:
    # 运行时不检查非空；检查器/文档看到注解就知道约束
    print("notify", len(users), "users")

notify({UserId(1), UserId(2)})
```

官方文档对 `Annotated` 的元数据保留有明确示例：

```python
from typing import Annotated, get_type_hints

def f(x: Annotated[int, "metadata"]) -> None: ...

get_type_hints(f)                       # {'x': int, 'return': NoneType}
get_type_hints(f, include_extras=True)  # {'x': Annotated[int, 'metadata'], ...}
```

也就是说：**注解元数据默认会被 `get_type_hints()` 去掉**，需要 `include_extras=True` 才保留——这在写依赖注解的框架（如 FastAPI、Pydantic）时很关键。

---

## 🧪 动手练习（建议 15~20 分钟，本地完成）

**任务：写一个「标签合并器」并加上完整的类型提示。**

需求：
1. 定义 `Tag = NewType("Tag", str)`，代表规范化后的标签。
2. 实现函数 `def merge_tags(groups: list[set[Tag]]) -> set[Tag]:`
   - 返回所有分组的**并集**，元素类型仍然是 `Tag`。
3. 实现函数 `def tag_index(items: list[set[Tag]]) -> dict[frozenset[Tag], int]:`
   - key 是每一组标签（用 `frozenset` 使它可哈希），value 是该组大小。
4. 用 `mypy` 或 `pyright` 检查：故意传一个 `set[int]` 进去，确认它会报错。

**检查清单（自测）**：
- [ ] `mypy demo.py` 无报错
- [ ] 把 `set[Tag]` 改成 `set[int]` 后 `mypy` 报错
- [ ] 尝试把 `set` 直接用作 dict 的 key，确认 `TypeError`，然后改成 `frozenset` 通过

**参考运行方式**：
```bash
pip install mypy
mypy demo.py
```

## py.type.set_ops

# py.type.set_ops：集合类型注解与运算操作

## 一句话直觉

当你想在代码里明确表达“这堆东西是一个集合，而且我会对它做交、并、差运算”时，`py.type.set_ops` 就是帮你把 **集合（set）的类型注解（type hints）** 和 **集合运算（set operations）** 安全地结合起来的工具。

## 1. 为什么需要集合类型注解？

Python 的 `set` 是内置类型，天然支持并集、交集、差集等运算。但在大型工程中，如果函数参数只写 `set`，类型检查器（type checker）不知道里面装的是什么。从 Python 3.9 开始，可以直接用 `set[int]` 这样的泛型（generic）写法表达“整数集合”。

```python
# 函数接收一个整数集合，返回所有元素的平方集合
def square_all(nums: set[int]) -> set[int]:
    return {n * n for n in nums}

print(square_all({1, 2, 3}))  # {1, 4, 9}
```

`set[int]` 是类型注解，运行时不强制检查，但 IDE、mypy、pyright 等工具会帮你提前发现错误。

## 2. 集合的三个核心运算：并集、交集、差集

集合运算在类型层面也是安全的：只要两个操作数都是 `set[T]`，结果仍然是 `set[T]`。

```python
from typing import TypeVar

T = TypeVar('T')

def union(a: set[T], b: set[T]) -> set[T]:
    return a | b          # 并集：属于 a 或属于 b

def intersection(a: set[T], b: set[T]) -> set[T]:
    return a & b          # 交集：同时属于 a 和 b

def difference(a: set[T], b: set[T]) -> set[T]:
    return a - b          # 差集：属于 a 但不属于 b

A = {1, 2, 3, 4}
B = {3, 4, 5, 6}
print(union(A, B))         # {1, 2, 3, 4, 5, 6}
print(intersection(A, B))  # {3, 4}
print(difference(A, B))    # {1, 2}
```

注意：`|`、`&`、`-` 都返回**新集合**，不会修改原集合；对应的就地版本是 `|=`、`&=`、`-=`。

## 3. 集合与其他容器的类型互转

工程中常见需求：把 `list` 转成 `set` 去重，或用 `frozenset` 作为字典键。类型注解可以帮助你表达这些转换。

```python
from typing import Iterable

def unique_items(items: Iterable[int]) -> set[int]:
    return set(items)

def as_frozen(nums: set[int]) -> frozenset[int]:
    return frozenset(nums)

print(unique_items([1, 2, 2, 3]))   # {1, 2, 3}
print(as_frozen({1, 2}))            # frozenset({1, 2})
```

`frozenset[T]` 是不可变集合（immutable set），可哈希（hashable），因此能放进另一个 `set` 或作为 `dict` 的键。

## 4. 抽象集合类型：`AbstractSet` 与 `MutableSet`

如果你只关心“可迭代、可做集合运算”，不关心具体是 `set` 还是 `frozenset`，可以用 `collections.abc` 中的抽象基类（ABC）。

```python
from collections.abc import Set, MutableSet

def count_common(a: Set[int], b: Set[int]) -> int:
    # Set 接受 set 和 frozenset，但不保证能修改
    return len(a & b)

def add_item(s: MutableSet[int], item: int) -> None:
    # MutableSet 保证有 add 方法
    s.add(item)

print(count_common({1, 2, 3}, frozenset({2, 3, 4})))  # 2

bag = {1, 2}
add_item(bag, 3)
print(bag)  # {1, 2, 3}
```

`Set` 和 `MutableSet` 是比 `set` 更宽泛的注解，适合写库时面向接口编程。

## 5. 联合类型与集合运算的结合

有时集合里可能装不同类型的元素，可以用联合类型（union type）表达。

```python
def stringify(nums: set[int | float]) -> set[str]:
    return {str(n) for n in nums}

print(stringify({1, 2.5, 3}))  # {'1', '2.5', '3'}
```

`set[int | float]` 表示集合元素可以是 `int` 或 `float`。运算时类型检查器会保留这个信息，直到你显式转换。

## 小结

- `set[T]` 表达“T 的集合”，支持 `|`、`&`、`-` 等运算，结果类型仍为 `set[T]`。
- `frozenset[T]` 是不可变、可哈希的版本，适合做字典键或放入其他集合。
- 写库时优先用 `collections.abc.Set` / `MutableSet` 作为参数类型，兼容性更好。
- 类型注解不改变运行时行为，但能让 IDE 和类型检查器提前发现错误。

## 动手练习

创建一个文件 `set_ops_demo.py`，完成以下任务：

1. 定义函数 `common_tags(user_a: set[str], user_b: set[str]) -> set[str]`，返回两个用户共同拥有的标签。
2. 定义函数 `only_a_has(user_a: set[str], user_b: set[str]) -> set[str]`，返回只在 `user_a` 中出现的标签。
3. 定义函数 `all_tags(user_a: set[str], user_b: set[str]) -> frozenset[str]`，返回两人所有标签的并集，且结果为不可变集合。
4. 用下面数据测试，并打印结果：
   ```python
   alice = {"python", "ai", "music"}
   bob = {"python", "go", "music", "chess"}
   ```
5. 用 `mypy` 或 `pyright` 检查文件，确保没有类型错误。

提示：使用 `|`、`&`、`-` 运算符，以及 `frozenset()` 构造函数。

```python
from collections.abc import Set, MutableSet
from typing import TypeVar

T = TypeVar('T')

def union(a: set[T], b: set[T]) -> set[T]:
    return a | b

def intersection(a: set[T], b: set[T]) -> set[T]:
    return a & b

def difference(a: set[T], b: set[T]) -> set[T]:
    return a - b

def unique_items(items: list[int]) -> set[int]:
    return set(items)

def as_frozen(nums: set[int]) -> frozenset[int]:
    return frozenset(nums)

def count_common(a: Set[int], b: Set[int]) -> int:
    return len(a & b)

def add_item(s: MutableSet[int], item: int) -> None:
    s.add(item)

A = {1, 2, 3, 4}
B = {3, 4, 5, 6}
print('union:', union(A, B))
print('intersection:', intersection(A, B))
print('difference:', difference(A, B))
print('unique:', unique_items([1, 2, 2, 3]))
print('frozen:', as_frozen({1, 2}))
print('common count:', count_common({1, 2, 3}, frozenset({2, 3, 4})))

bag = {1, 2}
add_item(bag, 3)
print('after add:', bag)
```


---

## 本课题目

### single_choice · None



- [A] {1, 2, 3}
- [B] {1, 2, 2, 3}
- [C] {1, 2, 3, 2}
- [D] 报错：集合中不能重复添加元素

**参考答案**：0

**解析**：集合的元素具有唯一性，add 已存在的元素不会产生任何变化，也不会报错，所以仍是 {1, 2, 3}。

### single_choice · None



- [A] {1, 2, 3}
- [B] {1, 2, 3, 4}
- [C] KeyError
- [D] ValueError

**参考答案**：2

**解析**：remove 删除不存在的元素会抛出 KeyError；如果希望不报错，应使用 discard。

### single_choice · None



- [A] True
- [B] False
- [C] 报错 TypeError
- [D] 报错 ValueError

**参考答案**：0

**解析**：< 表示真子集，a 的所有元素都在 b 中且 a 不等于 b，所以为 True。

### single_choice · None



- [A] True
- [B] False
- [C] 报错 TypeError
- [D] 报错 ValueError

**参考答案**：0

**解析**：<= 表示子集（允许相等），集合相等时仍为 True。

### single_choice · None



- [A] 1 2 3 按固定顺序输出
- [B] 3 2 1 按固定顺序输出
- [C] 元素会按某种不确定的顺序输出
- [D] 报错：集合不可迭代

**参考答案**：2

**解析**：集合是可迭代的，但没有顺序保证，迭代顺序取决于哈希实现，可能因运行环境而异。

### single_choice · None



- [A] 1
- [B] 报错 TypeError：'set' object is not subscriptable
- [C] 报错 IndexError
- [D] 报错 KeyError

**参考答案**：1

**解析**：集合不支持下标访问，因为它是无序的；访问元素需通过迭代或 in 判断。

### single_choice · None



- [A] {1, 2, 3, 4} 然后 {1, 2, 3, 4}
- [B] {1, 2, 3, 4} 然后 {1, 2, 3}
- [C] {1, 2, 3} 然后 {1, 2, 3}
- [D] 报错，union 是原地方法

**参考答案**：1

**解析**：union 返回新集合，不修改原集合；如果要原地更新应使用 update。

### single_choice · None



- [A] {1, 2, 3}
- [B] {1, 2, 3, 4}
- [C] {3, 4}
- [D] 报错，update 只能接收一个元素

**参考答案**：1

**解析**：update 将另一个可迭代对象的元素并入当前集合，是原地修改。

### single_choice · None



- [A] True True
- [B] False False
- [C] True False
- [D] False True

**参考答案**：2

**解析**：in 判断元素是否属于集合，3 在集合中，4 不在。

### single_choice · None



- [A] frozenset 可以添加和删除元素
- [B] frozenset 可哈希，可以作为字典的键
- [C] frozenset 与 set 完全等价，没有区别
- [D] frozenset 不能进行并集运算

**参考答案**：1

**解析**：frozenset 是不可变集合，因此可哈希，可以作为字典的键或另一个集合的元素；它仍支持并集等非修改性运算。

### single_choice · None



- [A] 5
- [B] 4
- [C] 3
- [D] 报错，set 不接受字符串

**参考答案**：1

**解析**：set('hello') 会将字符串拆成单个字符并去重，得到 {'h', 'e', 'l', 'o'}，长度为 4。

### single_choice · None



- [A] {1, 2, 3}
- [B] {1, 2, 3, 4}
- [C] 报错，集合不能被共享
- [D] {4}

**参考答案**：1

**解析**：b = a 让两个变量指向同一个集合对象，对 b 的原地修改会反映到 a。若想复制应使用 a.copy() 或 set(a)。

### single_choice · None



- [A] 3
- [B] 4
- [C] 报错 KeyError
- [D] 报错 ValueError

**参考答案**：0

**解析**：discard 删除不存在的元素时不会报错，集合保持不变，长度仍为 3。

### single_choice · None



- [A] {3}
- [B] {1, 2, 3, 4}
- [C] {1, 2, 4}
- [D] {1, 2, 3, 3, 4}

**参考答案**：1

**解析**：| 表示并集，合并两个集合的所有元素，重复元素只保留一份。

### single_choice · None



- [A] {1, 2, 3, 4}
- [B] {1, 2, 4}
- [C] {3}
- [D] 空集合 set()

**参考答案**：2

**解析**：& 表示交集，只保留同时存在于两个集合中的元素，即 {3}。

### single_choice · None



- [A] {1, 2}
- [B] {1, 2, 4}
- [C] {4}
- [D] {1, 2, 3, 4}

**参考答案**：0

**解析**：- 表示差集，得到在 s 中但不在 t 中的元素，即 {1, 2}。

### single_choice · None



- [A] {3}
- [B] {1, 2, 3, 4}
- [C] {1, 2, 4}
- [D] {1, 2}

**参考答案**：2

**解析**：^ 表示对称差集，保留仅出现在其中一个集合中的元素，即 {1, 2, 4}。

### single_choice · None



- [A] s = {}
- [B] s = set()
- [C] s = set({})
- [D] s = {[]}

**参考答案**：1

**解析**：{} 创建的是空字典，不是空集合；set() 才是创建空集合的正确方式。

### single_choice · None



- [A] 输出 {1, 2, 3, [4, 5]}
- [B] 输出 {1, 2, 3, 4, 5}
- [C] 抛出 TypeError：unhashable type: 'list'
- [D] 抛出 ValueError：集合元素必须是数字

**参考答案**：2

**解析**：集合元素必须是可哈希对象，列表不可哈希，因此添加列表会抛出 TypeError。

### single_choice · None



- [A] 列表 [1, 2]
- [B] 字典 {'a': 1}
- [C] 元组 (1, 2)
- [D] 集合 {1, 2}

**参考答案**：2

**解析**：元组是不可变且可哈希的，可以作为集合元素；列表、字典、集合本身都不可哈希。

### single_choice · None



- [A] {1, 2, 3}
- [B] {1, 2, 2, 3}
- [C] {2}
- [D] 报错，因为 2 已存在

**参考答案**：0

**解析**：集合中的元素具有唯一性，add 一个已存在的元素不会产生重复项，也不会报错，集合保持不变，所以仍是 {1, 2, 3}。

### single_choice · None



- [A] {1, 2, 3, 4, 5}
- [B] {3}
- [C] {1, 2, 4, 5}
- [D] 报错

**参考答案**：1

**解析**：& 是集合的交集运算符，返回两个集合中都存在的元素，a 与 b 共有的元素只有 3。

### single_choice · None



- [A] True True
- [B] True False
- [C] False True
- [D] False False

**参考答案**：0

**解析**：<= 表示子集关系（a 的所有元素都在 b 中），< 表示真子集关系（是子集且两集合不相等）。a 是 b 的子集且不相等，因此两个都为 True。

### multi_choice · None



- [A] 普通集合 set 是可变对象，可以添加或删除元素
- [B] 集合本身不能作为另一个集合的元素，因为 set 不可哈希
- [C] frozenset 是不可变集合，可以作为另一个集合的元素
- [D] frozenset 支持 add 方法来添加元素

**参考答案**：[0, 1, 2]

**解析**：set 可变，因此不可哈希，不能作为集合或字典的键；frozenset 不可变、可哈希，可作为集合元素，但它没有 add 等方法。

### multi_choice · None



- [A] a - b
- [B] b - a
- [C] a ^ b 中所有属于 a 的元素
- [D] {1, 2, 3, 4} & {2, 4}

**参考答案**：[0, 3]

**解析**：a - b 返回在 a 不在 b 的元素，即 {2, 4}；b - a 返回 {5}；a & {2,4} 也是 {2, 4}。a ^ b = {2, 4, 5}，其中属于 a 的部分确实是 {2,4}，但选项表述的是整个表达式与 {2,4} 相等，故不选。

### multi_choice · None



- [A] s.add(5)
- [B] s.remove(1)
- [C] s | {9}
- [D] s.update({7, 8})

**参考答案**：[0, 1, 3]

**解析**：add、remove、update 都会原地修改集合。而 | 运算符返回一个新集合，不会改变原集合（对应的原地版本是 |=）。

### fill_blank · None



**参考答案**：["__contains__", "contains"]

**解析**：in 运算符背后调用的是 __contains__ 方法，用于判断元素是否属于集合。s.__contains__('b') 返回 True。

### fill_blank · None



**参考答案**：["2"]

**解析**：discard(2) 会删除元素 2，集合从 {1,2,3} 变为 {1,3}，元素个数为 2。

### fill_blank · None



**参考答案**：["交集", "交"]

**解析**：& 是交集运算符，返回两个集合共有的元素。

### code_reading · None



**参考答案**：{2, 4} set

**解析**：该代码使用了集合推导式，对 s 中每个元素筛选出偶数。集合推导式的结果类型仍是 set，偶数有 2 和 4，因此输出 {2, 4} set。

### scenario · None



**解析**：求「既浏览又加购」用交集 browsed & carted；求「只浏览没加购」用差集 browsed - carted。集合运算在去重和成员判断上更高效，且代码更简洁，避免手动双重遍历列表。

### scenario · None



**解析**：把列表转成集合可以自动去重，且集合基于哈希，成员判断的平均时间复杂度为 O(1)，比列表的 O(n) 快。但集合是无序的，会失去原列表的顺序信息，也无法通过索引访问。

### single_choice · None



- [A] {3}
- [B] {1, 2, 4, 5}
- [C] {1, 2, 3, 4, 5}
- [D] {1, 2, 3, 3, 4, 5}

**参考答案**：2

**解析**：| 是集合并集运算符，返回两个集合中的所有元素，重复元素只保留一份，所以是 {1, 2, 3, 4, 5}。

### single_choice · None



- [A] 返回同时存在于 a 和 b 中的元素
- [B] 返回在 a 中但不在 b 中的元素
- [C] 返回在 b 中但不在 a 中的元素
- [D] 返回 a 和 b 中所有不重复的元素

**参考答案**：1

**解析**：差集 a - b 返回属于 a 但不属于 b 的元素；方向很重要，a - b 与 b - a 结果通常不同。

### single_choice · None



- [A] {1, 4}
- [B] {2, 3}
- [C] {1, 2, 3, 4}
- [D] 报错

**参考答案**：0

**解析**：^ 是对称差集运算符，返回只出现在其中一个集合中的元素。a 与 b 共有的 2、3 被排除，剩下的 1、4 即为结果。

### single_choice · None



- [A] True
- [B] False
- [C] 1
- [D] 报错

**参考答案**：0

**解析**：in 运算符用于判断元素是否属于集合，2 是集合 s 的元素，因此返回 True。

### single_choice · None



- [A] 1
- [B] 2
- [C] 3
- [D] 6

**参考答案**：2

**解析**：len 返回集合中元素的个数。集合自动去重，{3, 1, 2} 共有 3 个元素。

### single_choice · None



- [A] s = {}
- [B] s = set()
- [C] s = frozenset()
- [D] s = {[]}

**参考答案**：1

**解析**：{} 创建的是空字典而不是空集合；创建空集合必须使用 set()。frozenset() 创建的是不可变集合，{} 内不能放列表（不可哈希）。

### single_choice · None



- [A] s = {1, 2, 3}
- [B] s = {(1, 2), (3, 4)}
- [C] s = {[1, 2], [3, 4]}
- [D] s = {1.5, 'a', (1,)}

**参考答案**：2

**解析**：集合元素必须是可哈希对象。列表是可变对象、不可哈希，因此把列表放入集合会抛出 TypeError。元组、数字、字符串都是可哈希的。

### single_choice · None



- [A] {1, 2, 3}
- [B] {5}
- [C] 报错，KeyError
- [D] {1, 2, 3, 5}

**参考答案**：0

**解析**：discard 删除指定元素，如果元素不存在也不会报错。因为 5 不在集合中，集合保持不变。相比之下 remove 在元素不存在时会抛 KeyError。
