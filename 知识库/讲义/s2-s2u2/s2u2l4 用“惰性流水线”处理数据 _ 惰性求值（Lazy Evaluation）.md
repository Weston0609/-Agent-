# s2u2l4 用“惰性流水线”处理数据 / 惰性求值（Lazy Evaluation）

> 来源 `content/lessons/s2u2l4.json`

## py.iter.itertools

# py.iter.itertools：用“惰性流水线”处理数据

**一句话直觉**：`itertools` 是 Python 标准库中专门用来“组装迭代器”的工具箱——它让你像搭积木一样，把数据流切分、组合、过滤、无限生成，而且全程**惰性求值**（lazy evaluation），几乎不占内存。学它，是从“写 for 循环”进阶到“写数据流水线”的关键一步。

---

## 1. 先弄清：什么是迭代器（iterator）和可迭代对象（iterable）

- **可迭代对象**（iterable）：能被 `for` 遍历的东西，如 `list`、`str`、`dict`、文件对象。它实现了 `__iter__()`。
- **迭代器**（iterator）：一个“一次只能往前走、不能回头”的数据流。它同时实现 `__iter__()` 和 `__next__()`。
- **惰性求值**（lazy evaluation）：迭代器不是一次性把所有数据算出来，而是每次 `next()` 才产生下一个值。这意味着它可以表示**无限序列**，也可以处理**超大文件**。

```python
# 用 iter() 把可迭代对象变成迭代器
nums = [1, 2, 3]
it = iter(nums)
print(next(it))  # 1
print(next(it))  # 2
# 迭代器耗尽了会抛 StopIteration，for 循环会自动捕获它
```

**关键结论**：`itertools` 里几乎所有函数返回的都是迭代器，而不是 list。惰性是它省内存的根本原因。

---

## 2. 无穷迭代器：count / cycle / repeat

这三个函数可以生成“永远不会结束”的序列，非常适合配合 `zip`、`islice` 使用。

```python
import itertools

# count(start, step)：从 start 开始，每次加 step
for i in itertools.count(10, 2):
    if i > 18:
        break
    print(i)  # 10 12 14 16 18

# cycle(iterable)：无限循环一个序列
colors = itertools.cycle(['red', 'green'])
print([next(colors) for _ in range(5)])  # ['red','green','red','green','red']

# repeat(obj, times)：重复对象 times 次（省略 times 则无限）
print(list(itertools.repeat('A', 3)))  # ['A', 'A', 'A']
```

**关键结论**：无穷迭代器不能直接 `list()`，必须用 `break` 或 `islice` 限制长度，否则会耗尽内存或死循环。

---

## 3. 组合与切分：chain / islice / groupby / tee

这一组是工程里最常用的“流水线零件”。

```python
import itertools

# chain：把多个可迭代对象串成一条流
print(list(itertools.chain([1, 2], 'ab', (3, 4))))  # [1, 2, 'a', 'b', 3, 4]

# islice：对迭代器做切片（不能用 [a:b] 切迭代器！）
it = itertools.count(1)
print(list(itertools.islice(it, 5)))  # [1, 2, 3, 4, 5]
print(list(itertools.islice(it, 5, 8)))  # [6, 7, 8]

# groupby：按 key 分组（输入必须先按同一 key 排好序！）
data = [('A', 1), ('A', 2), ('B', 3), ('B', 4)]
for key, group in itertools.groupby(data, key=lambda x: x[0]):
    print(key, [v for _, v in group])
# A [1, 2]
# B [3, 4]

# tee：把一个迭代器“分裂”成 n 个独立副本（会缓存，慎用于长流）
a, b = itertools.tee(range(3))
print(list(a), list(b))  # [0,1,2] [0,1,2]
```

**关键结论**：`groupby` 只合并**相邻**的同 key 元素，输入未排序会得到重复分组；`islice` 是唯一能给迭代器“切片”的官方方式。

---

## 4. 过滤与映射：filterfalse / dropwhile / takewhile / starmap / accumulate

这些让流水线更“函数式”。

```python
import itertools, operator

nums = range(1, 8)

# filterfalse：保留“判断为假”的元素
print(list(itertools.filterfalse(lambda x: x % 2 == 0, nums)))  # [1,3,5,7]

# takewhile / dropwhile：一旦条件变化就停止/开始
print(list(itertools.takewhile(lambda x: x < 4, nums)))  # [1,2,3]
print(list(itertools.dropwhile(lambda x: x < 4, nums)))  # [4,5,6,7]

# starmap：对“参数元组”流调用函数
pairs = [(2, 3), (4, 5)]
print(list(itertools.starmap(operator.mul, pairs)))  # [6, 20]

# accumulate：累积（默认求和，可自定义函数）
print(list(itertools.accumulate([1, 2, 3, 4])))  # [1, 3, 6, 10]
```

**关键结论**：`takewhile`/`dropwhile` 只关心“从前往后”的第一个翻转点，输入乱序时语义会与原意不同。

---

## 5. 笛卡尔积与排列组合：product / permutations / combinations

做搜索、枚举、测试用例生成时的常用武器。

```python
import itertools

# product：笛卡尔积
print(list(itertools.product('AB', [1, 2])))
# [('A',1), ('A',2), ('B',1), ('B',2)]

# permutations：排列（考虑顺序）
print(list(itertools.permutations('AB', 2)))  # [('A','B'), ('B','A')]

# combinations：组合（不考虑顺序）
print(list(itertools.combinations('ABC', 2)))
# [('A','B'), ('A','C'), ('B','C')]

# combinations_with_replacement：可重复组合
print(list(itertools.combinations_with_replacement('AB', 2)))
# [('A','A'), ('A','B'), ('B','B')]
```

**关键结论**：`permutations` 规模是 O(n!)，`product` 规模是 O(n^k)，处理大输入前先用 `math` 估算规模，避免爆炸。

---

## 工程级视角：把迭代器当成“管道”

`itertools` 的真正威力是与**生成器表达式**、`map`/`filter` 组合成管道：

```python
import itertools

# 读取多行日志，过滤出 ERROR 行，取前 3 条，并抽出时间戳
lines = (line for line in open('app.log', encoding='utf-8'))
errors = (ln for ln in lines if 'ERROR' in ln)
head = itertools.islice(errors, 3)
for ln in head:
    print(ln.rstrip())
```

这段代码**不会**一次性读入整个文件，无论日志多大，内存占用几乎恒定。

---

## 动手练习

**任务**：写一个函数 `top_words(path, n)`，统计一个文本文件中出现频率最高的 `n` 个单词，要求用 `itertools` 构造流水线，且不一次性把整个文件读成一个大列表。

**要求**：
1. 用 `open(...)` 迭代文件行；
2. 用 `itertools.chain.from_iterable` 或生成器表达式把每行拆成单词；
3. 统一小写，去掉标点；
4. 用 `collections.Counter` 统计，返回出现次数最多的 `n` 个（形如 `[('the', 120), ...]`）；
5. 打印处理耗时。

**验收**：在任意英文 txt 文件上运行，内存占用稳定，结果与 `Counter(text.read().split()).most_common(n)` 在小文件上一致。

**进阶**：改成“统计长度为 k 的单词的 top n”，用 `itertools.filterfalse` 或 `takewhile` 过滤长度。

```python
import itertools
from collections import Counter


def top_words(path: str, n: int):
    """统计文件中出现频率最高的 n 个单词，本质是惰性流水线。"""
    with open(path, "r", encoding="utf-8") as f:
        # 1) 逐行 -> 2) 每行拆词 -> 3) 归一化
        tokens = (
            w.strip(".,!?;:\"'()[]").lower()
            for line in f                      # 惰性读行
            for w in line.split()              # 惰性拆词
        )
        # 4) 丢弃空字符串
        words = itertools.filterfalse(lambda w: not w, tokens)
        # 5) 统计
        return Counter(words).most_common(n)


if __name__ == "__main__":
    import os
    demo = "demo.txt"
    if not os.path.exists(demo):
        with open(demo, "w", encoding="utf-8") as f:
            f.write("Hello world! Hello Python. World of itertools.\n" * 3)

    print(top_words(demo, 3))
    # 期望输出类似：[('hello', 6), ('world', 6), ('itertools', 3)]
```

## py.iter.lazy_eval

# py.iter.lazy_eval：惰性求值（Lazy Evaluation）

> **一句话直觉**：惰性求值就是“先不急着算，等真正需要结果时才算”，这样能省内存、省时间，还能处理无限序列（infinite sequence）。

---

## 1. 从“立刻算”到“用的时候再算”

传统写法里，`[x*x for x in range(10**8)]` 会立刻在内存中生成一个含一亿个元素的列表（list）。

而**惰性求值（lazy evaluation）** 的思路是：先描述“怎么算”，但不立刻算；只有当你真的去取元素时，才一步一步算。

Python 里实现惰性求值最核心的工具是**生成器（generator）** 和**迭代器（iterator）**。

```python
# 立刻求值：列表推导式（list comprehension）会马上占内存
eager = [x * x for x in range(5)]
print(eager)  # [0, 1, 4, 9, 16]

# 惰性求值：生成器表达式（generator expression）
lazy = (x * x for x in range(5))
print(lazy)   # <generator object ...>，此时还没算
print(next(lazy))  # 0，取一个才算一个
print(next(lazy))  # 1
```

**关键结论**：生成器表达式用 `()`，列表推导式用 `[]`；前者是惰性的，后者是立即求值的。

---

## 2. 生成器函数（generator function）：yield 的魔法

只要函数体里出现 `yield`，这个函数就变成**生成器函数**。调用它不会执行函数体，而是返回一个生成器对象。

```python
def count_up(n):
    """惰性产生 0 到 n-1"""
    i = 0
    while i < n:
        yield i      # 每次执行到这里暂停，把 i 交出去
        i += 1

gen = count_up(3)
print(next(gen))  # 0
print(next(gen))  # 1
print(next(gen))  # 2
# print(next(gen))  # 再取会抛 StopIteration

# 用 for 循环自动处理 StopIteration
for v in count_up(3):
    print(v)  # 0 1 2
```

**关键结论**：`yield` 让函数“暂停并可恢复”，这是惰性求值在 Python 中最标准写法。

---

## 3. 迭代器协议（iterator protocol）：for 背后的机制

Python 的 `for` 循环其实是对**可迭代对象（iterable）** 调用 `iter()` 得到**迭代器（iterator）**，再反复调用 `next()`。

```python
nums = [10, 20, 30]          # 列表是 iterable，不是 iterator
it = iter(nums)              # 得到 iterator
print(next(it))  # 10
print(next(it))  # 20

# 自己实现一个迭代器类
class CountDown:
    def __init__(self, start):
        self.n = start
    def __iter__(self):
        return self
    def __next__(self):
        if self.n <= 0:
            raise StopIteration
        self.n -= 1
        return self.n + 1

for x in CountDown(3):
    print(x)  # 3 2 1
```

**关键结论**：实现 `__iter__` 和 `__next__` 就是自定义迭代器；`for` 会自动调用这两者。

---

## 4. 惰性求值的三大收益

### 4.1 省内存：处理大文件

```python
# 假设 data.txt 有 1 亿行，下面这种写法会把整个文件读入内存
# lines = open("data.txt").readlines()

# 惰性写法：一次只读一行
def read_lines(path):
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            yield line.strip()

# for line in read_lines("data.txt"):
#     process(line)   # 内存占用恒定
```

### 4.2 处理无限序列

```python
def naturals():
    """自然数序列，无限长，但不会撑爆内存"""
    n = 0
    while True:
        yield n
        n += 1

import itertools
# 取前 5 个
print(list(itertools.islice(naturals(), 5)))  # [0, 1, 2, 3, 4]
```

### 4.3 提前短路：只算需要的那部分

```python
def expensive(x):
    print(f"计算 {x}...")
    return x * x

# 找到第一个平方大于 20 的数就停
gen = (expensive(x) for x in range(100))
for v in gen:
    if v > 20:
        print("命中:", v)
        break
# 只会打印前几个“计算 x...”，不会算 100 个
```

**关键结论**：惰性求值把“计算”与“取值”解耦，天然支持流式处理与短路优化。

---

## 5. 惰性与“一次性”：迭代器的陷阱

迭代器只能被遍历一次；再遍历就空了。这是新手最容易踩的坑。

```python
gen = (x for x in range(3))
print(list(gen))  # [0, 1, 2]
print(list(gen))  # []  —— 已经耗尽！

# 如果需要多次遍历，要么重新创建生成器，要么用 list 缓存
def make_gen():
    return (x for x in range(3))

print(list(make_gen()))  # [0, 1, 2]
print(list(make_gen()))  # [0, 1, 2]
```

**关键结论**：迭代器是“一次性消耗品”；需要多次使用就把它实体化或重新生成。

```python
# 综合示例：惰性求值 + 生成器流水线，统计一个大范围内满足条件的数
# 运行环境：Python 3.8+

import itertools


def numbers(start=0):
    """无限自然数流（惰性）"""
    n = start
    while True:
        yield n
        n += 1


def is_prime(n):
    """判断素数"""
    if n < 2:
        return False
    for i in range(2, int(n ** 0.5) + 1):
        if n % i == 0:
            return False
    return True


# 流水线：无限数 -> 过滤出素数 -> 只取前 10 个
prime_stream = (x for x in numbers(2) if is_prime(x))
first_10_primes = list(itertools.islice(prime_stream, 10))
print("前 10 个素数:", first_10_primes)

# 验证惰性：用生成器表达式遍历大范围，但只用前 5 个
squares = (x * x for x in range(10 ** 9))   # 不会真的算 10 亿次
print("前 5 个平方:", list(itertools.islice(squares, 5)))

# 自定义迭代器：倒计时
def countdown(n):
    while n > 0:
        yield n
        n -= 1

print("倒计时:", list(countdown(5)))
```


---

## 本课题目

### single_choice · None



- [A] [10, 13, 16]
- [B] [10, 11, 12]
- [C] [3, 13, 23]
- [D] 会报错，因为 count 不能转换成列表

**参考答案**：0

**解析**：itertools.count(start, step) 从 start 开始，每次增加 step，返回无限迭代器。因此前三个元素为 10、13、16。虽然它是无限迭代器，但 list() 会尝试全部消费，若只取前几个必须用 islice，这里 list() 会挂起，所以严格来说这段代码不会正常返回。选项中最符合 count 语义的是 [10, 13, 16]。

### single_choice · None



- [A] itertools.repeat
- [B] itertools.cycle
- [C] itertools.chain
- [D] itertools.islice

**参考答案**：1

**解析**：itertools.cycle 会保存输入元素并无限重复输出。repeat 是重复同一个值（不循环整体），chain 是串联多个迭代器，islice 是切片。

### single_choice · None



- [A] [1, 3, 6, 10]
- [B] [1, 2, 3, 4]
- [C] [10]
- [D] [1, 2, 6, 24]

**参考答案**：0

**解析**：accumulate 默认做累加，输出前缀和 1, 1+2, 1+2+3, ...，即 [1,3,6,10]。可用 func 参数改成其他二元运算。

### single_choice · None



- [A] tee 会立刻把整个可迭代对象复制成多个独立的完整副本，内存开销与副本数无关
- [B] tee 把可迭代对象拆成 n 个独立迭代器，但底层可能缓存元素，需谨慎使用以免内存增长
- [C] tee 只能生成两个迭代器
- [D] tee 返回的是列表而不是迭代器

**参考答案**：1

**解析**：tee 把迭代器拆成多个独立迭代器，内部会缓存尚未被其他分支消费的元素，若消费速度不一致会导致缓存膨胀。不限制为两个，返回元组包含 n 个迭代器。

### multi_choice · None



- [A] 大多数 itertools 函数返回的是惰性迭代器，不会立即计算全部结果
- [B] itertools.count 返回无限迭代器
- [C] itertools.chain 会对输入去重
- [D] itertools.groupby 要求输入按分组键排序才能正确全局分组

**参考答案**：[0, 1, 3]

**解析**：itertools 通常是惰性的，很多返回迭代器；count 无限；groupby 只对相邻元素分组，若要全局分组应先排序；chain 不去重，故第三个错误。

### multi_choice · None



- [A] itertools.combinations
- [B] itertools.permutations
- [C] itertools.product
- [D] itertools.cumsum

**参考答案**：[0, 1, 2]

**解析**：combinations 生成组合，permutations 生成排列，product 生成笛卡尔积。cumsum 不是 itertools 的函数（accumulate 才是做累积运算的），也不生成组合类结果。

### multi_choice · None



- [A] islice 可以作用于迭代器，而切片语法一般作用于序列
- [B] islice 支持惰性消费，不要求上游先物化
- [C] islice 支持负数步长
- [D] islice(iterable, stop) 只取前 stop 个元素

**参考答案**：[0, 1, 3]

**解析**：islice 面向任意可迭代对象且惰性，islice(it, n) 取前 n 个。它不支持负索引或负步长，因此第三个选项错误。

### fill_blank · None



**参考答案**：["cycle", "itertools.cycle"]

**解析**：itertools.cycle(iterable) 会逐个产出元素并在耗尽后从头重复，形成无限迭代器。

### fill_blank · None



**参考答案**：["combinations", "itertools.combinations"]

**解析**：itertools.combinations(iterable, r) 生成不考虑顺序的组合；若允许重复则用 combinations_with_replacement。

### code_reading · None



**参考答案**：[1, 2, 3, 4, 5, 1, 2]。cycle 会循环重复 nums，islice 取前 7 个元素，因此第二轮回到开头取到 1、2。

**解析**：cycle 无限循环输入序列，islice 截取前 7 个，于是结果覆盖完整一轮 5 个再取下一轮前 2 个。考查 cycle 与 islice 的组合使用及惰性截断。

### code_reading · None



**参考答案**：因为 groupby 只对相邻的相同元素分组，data 中 a、b 交替出现，所以每个元素都自成一组，输出四组而不是把两个 a 合成一组。若要按值全局分组，应先对 data 排序再 groupby。

**解析**：groupby 的分组依据是相邻元素是否相等，而不是全集合聚合，这是常见误解。要得到全局分组需先排序。

### scenario · None



**解析**：可以使用生成器按需 yield 每页数据，再用 itertools.chain 或 chain.from_iterable 把逐页结果串联成单一惰性迭代流；若需要加终止条件可用 takewhile 或 islice 限制数量。关键是保持惰性，避免提前把全部页物化到内存，同时把请求发起推迟到消费时。

### single_choice · None



- [A] [0, 1, 2]
- [B] [1, 2, 3]
- [C] [0, 1, 2, 3]
- [D] 会无限循环，无法输出

**参考答案**：0

**解析**：count() 默认从 0 开始，islice(iterable, stop) 取前 stop 个元素，即 0、1、2。islice 用于安全地从无限迭代器中截取有限部分。

### scenario · None



**解析**：groupby 只对相邻的相同键分组，日志级别无序，直接分组会把同一级别拆成多组，导致统计错误。若坚持用 groupby，必须先按级别排序（但排序大迭代器成本高、且会物化）。更合适的是用字典或 collections.Counter 单次遍历累计计数，保持 O(n) 且不依赖顺序。

### single_choice · None



- [A] chain 会把多个可迭代对象合并成一个，但会先全部物化为列表再输出
- [B] chain 按顺序连接多个可迭代对象，惰性地逐个产出元素
- [C] chain 只能接受两个参数
- [D] chain 会去重后输出

**参考答案**：1

**解析**：itertools.chain 按顺序惰性地产出各可迭代对象的元素，不会预先物化，也不去重，可接受多个（含 chain.from_iterable 处理嵌套）。

### single_choice · None



- [A] [('A', 'B'), ('A', 'C'), ('B', 'C')]
- [B] [('A', 'B'), ('B', 'A'), ('A', 'C'), ('C', 'A'), ('B', 'C'), ('C', 'B')]
- [C] [('A', 'B'), ('A', 'C')]
- [D] [('A', 'A'), ('B', 'B'), ('C', 'C')]

**参考答案**：0

**解析**：combinations(iterable, r) 生成不重复、顺序固定的组合，不考虑排列。ABC 取两个的组合正是 AB、AC、BC。

### single_choice · None



- [A] itertools.combinations
- [B] itertools.combinations_with_replacement
- [C] itertools.permutations
- [D] itertools.product 只限于两个输入

**参考答案**：2

**解析**：permutations 生成排列，顺序不同视为不同结果。combinations 与 combinations_with_replacement 不考虑顺序；product 是笛卡尔积，可接受 repeat 参数，可多于两个输入。

### single_choice · None



- [A] A 3 / B 2 / C 2
- [B] A 1 / A 1 / A 1 / B 1 ...
- [C] A 3 / B 2
- [D] 会报错，groupby 需要排序

**参考答案**：0

**解析**：groupby 按相邻元素分组，同组连续则归为一组。AAABBCC 的顺序输出 A:3、B:2、C:2。注意它只对相邻相同元素分组，不会全局聚合。

### single_choice · None



- [A] 等价于 product('AB', 'AB')，输出 4 个元组
- [B] 等价于 combinations('AB', 2)
- [C] 输出 2 个元组
- [D] repeat 参数不存在，会报 TypeError

**参考答案**：0

**解析**：product 的 repeat 参数表示将输入重复若干次做笛卡尔积，product('AB', repeat=2) 等价于 product('AB','AB')，输出 AA、AB、BA、BB 共 4 个。

### single_choice · None



- [A] [[1, 2, 3], [1, 2, 3]]
- [B] [1, 2, 3, 1, 2, 3]
- [C] [1, 2, 3]
- [D] [2, 2, 2]

**参考答案**：0

**解析**：repeat(obj, times) 重复产出同一个对象 times 次，每个元素是同一个列表对象，所以是 [[1,2,3],[1,2,3]]，而不是展开元素。

### single_choice · None



- [A] itertools.zip_longest
- [B] itertools.chain
- [C] itertools.product
- [D] itertools.islice

**参考答案**：3

**解析**：严格来说按位置聚合且最短停止是内置 zip，itertools 中对应行为可由 zip 直接完成；zip_longest 会用填充值补齐到最长。选项中 zip_longest 是变长补齐版本，chain 是串联，product 是笛卡尔积，islice 是切片。本题考查区分这些常用函数。

### single_choice · None



- [A] 迭代器在创建时就会立即计算出所有元素并存入内存
- [B] 迭代器只有在被请求下一个元素时才计算出该元素
- [C] 迭代器只能用于 for 循环，不能用于其他上下文
- [D] 迭代器一旦创建，其元素数量必须提前确定

**参考答案**：1

**解析**：惰性求值是迭代器的核心特征：元素按需生成，调用 next() 时才计算下一个值，因此可以表示无限序列并节省内存。A 描述的是列表等急切求值；C 错误，迭代器可用于 next()、解包、sum() 等多种上下文；D 错误，生成器可产生无限序列。

### single_choice · None



- [A] start
  created
  middle
- [B] created
  start
- [C] start
  middle
  created
- [D] created
  start
  middle

**参考答案**：1

**解析**：调用生成器函数只是创建生成器对象，函数体不会执行，因此先打印 'created'。第一次调用 next(g) 才真正开始执行函数体，打印 'start' 并停在第一个 yield。'middle' 要等到第二次 next 才会打印。

### multi_choice · None



- [A] 生成器表达式 (x for x in range(5))
- [B] 生成器函数调用后返回的生成器对象
- [C] 列表推导 [x for x in range(5)]
- [D] 内置 range(5)

**参考答案**：[0, 1, 3]

**解析**：生成器表达式、生成器对象和 range 都是惰性的，按需产生元素。列表推导是急切求值，会立即构造出完整列表并占用相应内存。

### multi_choice · None



- [A] 可以处理超出内存容量的大数据集或无限序列
- [B] 能避免不必要的计算，只在需要时计算元素
- [C] 可以让迭代器支持多次重复迭代
- [D] 可以降低峰值内存占用

**参考答案**：[0, 1, 3]

**解析**：惰性求值节省内存、支持无限序列、只在需要时计算，都是它的优点。但惰性迭代器通常是一次性的，不能因此支持重复迭代；要重复迭代需重新创建或缓存（如用 list 或 tee）。

### multi_choice · None



- [A] 生成器对象被迭代完后，再次迭代会立即结束
- [B] 迭代器与可迭代对象不同，通常只能迭代一次
- [C] list(iterator) 会消费掉迭代器中的元素
- [D] 迭代器耗尽后会自动重新从头开始

**参考答案**：[0, 1, 2]

**解析**：迭代器是消费型的：一旦耗尽，再次迭代只会得到空结果或立即 StopIteration。list(iterator) 会消耗其中所有元素。D 错误，迭代器不会自动重置，需新建或借助 itertools.tee。

### multi_choice · None



- [A] 它只在被迭代时逐个计算元素
- [B] 它不能被多次迭代，因为是一次性迭代器
- [C] 把生成器表达式传给 sum、any、max 等函数是安全的
- [D] 它会立即在创建时求值所有元素

**参考答案**：[0, 1, 2]

**解析**：生成器表达式是惰性的一次性迭代器，只在迭代时计算元素，因此可以安全地传给所有接受可迭代对象的函数（sum、any、max 等）。D 错误，它不会在创建时立即求值全部元素。

### fill_blank · None



**参考答案**：["yield", "yield 关键字", "yield语句", "yield 语句"]

**解析**：使用 yield 的函数是生成器函数；调用它返回生成器对象，函数体在迭代时才执行，每遇到 yield 暂停并产出一个值，从而实现惰性求值。若用 return 则函数会立刻完整执行并返回值。

### fill_blank · None



**参考答案**：["StopIteration", "StopIteration异常", "StopIteration 异常"]

**解析**：迭代器在耗尽时必须抛出 StopIteration，for 循环和 next() 等机制依赖此异常判断迭代结束。抛出其他异常会被视为错误而非正常终止。

### code_reading · None



**参考答案**：0 1 2

**解析**：counter 是一个产生无限序列的生成器。每次 next 在 yield 处恢复执行并产出当前 n，然后 n 自增。三次 next 依次产出 0、1、2，用空格分隔打印。惰性求值使得无限循环不会真正无限执行。

### scenario · None



**解析**：应逐行迭代文件对象（如 for line in open(...)），利用文件对象与迭代器的惰性求值特性，一次只在内存中保留一行，从而在有限内存下处理超大文件。绝不能使用 readlines() 或 list(open(...)) 一次性把整个文件读入内存。

### scenario · None



**解析**：根源是生成器是一次性迭代器，第一次遍历已将其耗尽，不能重复迭代。修复思路：一是让函数每次返回一个新的生成器（重新调用生成器函数）；二是把结果缓存为列表等可重复迭代的容器（用 list 保存）；也可借助 itertools.tee 复制迭代器，但其内部会缓存，需注意内存。

### single_choice · None



- [A] [x * 2 for x in range(1000000)]
- [B] (x * 2 for x in range(1000000))
- [C] {x * 2 for x in range(1000000)}
- [D] list(map(lambda x: x * 2, range(1000000)))

**参考答案**：1

**解析**：圆括号的生成器表达式是惰性求值，只在迭代时逐个计算。方括号列表推导、集合推导和 list(map(...)) 都会立即构造出包含全部一百万个元素的容器，属于急切求值。

### single_choice · None



- [A] 会立即在内存中创建一个包含十亿个整数的列表
- [B] 是一个可迭代对象，按需产生整数，几乎不占额外内存
- [C] 只能迭代一次，第二次迭代会抛出 StopIteration
- [D] 会抛出 MemoryError，因为数字太大

**参考答案**：1

**解析**：range 返回的是一个惰性的可迭代对象（序列类型），只在迭代时按需计算每个整数，占用内存为常数级别。它不是一次性迭代器，因此可以被多次迭代。A 描述的是 list(range(...))。

### single_choice · None



- [A] [0, 1, 2]
  [0, 1, 2]
- [B] [0, 1, 2]
  []
- [C] []
  [0, 1, 2]
- [D] 抛出异常

**参考答案**：1

**解析**：生成器是一次性迭代器。第一次 list(g) 消费掉全部元素后，生成器已耗尽；第二次 list(g) 得到空列表 []。这是惰性迭代器常见的陷阱：迭代器与可迭代对象不同，不能重复迭代。

### single_choice · None



- [A] lines = open('big.txt').readlines()[:100]
- [B] lines = [line for line in open('big.txt')][:100]
- [C] from itertools import islice; lines = list(islice(open('big.txt'), 100))
- [D] lines = list(open('big.txt'))[100:]

**参考答案**：2

**解析**：islice 对可迭代对象做惰性切片，只取前 100 行即在迭代层面停止，不会读取整个文件。readlines()、列表推导、list(open(...)) 都会先把整个文件读入内存，违背惰性初衷。

### single_choice · None



- [A] __init__ 和 __del__
- [B] __iter__ 和 __next__
- [C] __getitem__ 和 __len__
- [D] __call__ 和 __repr__

**参考答案**：1

**解析**：迭代器协议要求对象实现 __iter__（返回自身）和 __next__（返回下一个元素或在耗尽时抛出 StopIteration）。惰性求值正是通过反复调用 __next__ 按需产生元素实现的。

### single_choice · None



- [A] 因为 yield 会导致语法错误
- [B] 因为生成器的函数体在调用时不执行，要等到迭代时才执行
- [C] 因为 print 在生成器内被禁用
- [D] 因为 x 需要先被显式初始化

**参考答案**：1

**解析**：调用生成器函数只返回生成器对象，并不运行函数体。只有对它迭代（如 next()、for）时，函数体才会执行到第一个 yield，此时 'computing' 才被打印。这是惰性的直接体现。

### single_choice · None



- [A] 两者结果相同，但前者不构造中间列表，内存更省
- [B] 前者结果是错的，因为生成器表达式不能传给 sum
- [C] 后者内存更省，因为列表更快
- [D] 两者完全等价，连内存占用都相同

**参考答案**：0

**解析**：sum 接受任意可迭代对象。传入生成器表达式时按需产生每个元素，不构造中间列表；传入列表推导则会先建立整个列表。两者结果相同，但惰性版本内存效率更高。

### single_choice · None



- [A] 它内部把整数预先分配了一部分缓存
- [B] 它是惰性迭代器，只在每次 next 时计算下一个值，不预先生成全部
- [C] 它在达到内存上限后会自动停止
- [D] 无限序列在 Python 中一定会在某个点停止

**参考答案**：1

**解析**：惰性求值使无限序列成为可能：count 只在被请求时才产生下一个值，从不预先计算全部。若用急切求值（如列表），无限序列会立即耗尽内存。
