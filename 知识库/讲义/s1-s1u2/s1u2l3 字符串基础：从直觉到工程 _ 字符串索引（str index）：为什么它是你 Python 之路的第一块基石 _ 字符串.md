# s1u2l3 字符串基础：从直觉到工程 / 字符串索引（str index）：为什么它是你 Python 之路的第一块基石 / 字符串是 Python 里最常用的数据类型（type），

> 来源 `content/lessons/s1u2l3.json`

## py.type.str_basic

# 字符串基础：从直觉到工程

> **一句话直觉**：字符串（str）是 Python 里用来表示"文本"的内置类型，几乎所有程序都要跟它打交道，所以它是你学 Python 的第一块地基。

---

## 1. 字符串是什么：一串不可变的字符

在 Python 中，**字符串（string，简称 str）** 是用单引号 `'...'`、双引号 `"..."` 或三引号 `'''...'''` / `"""..."""` 包起来的一串字符序列。

它有两个关键属性：
- **序列（sequence）**：可以通过下标索引、切片、遍历。
- **不可变（immutable）**：一旦创建，就不能修改其中的字符；任何"修改"都会生成新字符串。

```python
s = "hello"
print(s[0])       # 'h'  —— 下标从 0 开始
print(s[-1])      # 'o'  —— 负数表示从末尾倒数
print(s[1:4])     # 'ell' —— 切片，左闭右开
print(len(s))     # 5

# 不可变：下面这行会报错
# s[0] = 'H'      # TypeError: 'str' object does not support item assignment
s2 = 'H' + s[1:]  # 正确做法：拼一个新字符串
print(s2)         # 'Hello'
```

---

## 2. 字面量（literal）：单引号、双引号、三引号、转义

Python 不区分单双引号；三引号可以写多行。**转义字符（escape character）** 用反斜杠 `\` 开头。

```python
print('it\'s ok')          # 单引号里含单引号，需要转义
print("she said: \"hi\"") # 双引号同理
print('a\tb')              # \t 制表符
print('line1\nline2')      # \n 换行

multi = """第一行
第二行"""
print(multi)

# 原始字符串 raw string：\ 不再转义
print(r'C:\Users\new')     # 输出 C:\Users\new
```

**工程提示**：写路径、正则表达式、Windows 路径时，优先用原始字符串 `r'...'`。

---

## 3. 常用操作：拼接、格式化、常用方法

字符串最常用的几类操作：拼接、格式化（f-string）、查找、替换、大小写、拆分与合并。

```python
name = "Ada"
age = 36

# 三种常见拼接方式
print("Hello, " + name)               # 简单拼接
greeting = f"Hello, {name}, age {age}"   # f-string（推荐）
print(greeting)
print("Hello, {}".format(name))       # str.format

# 常用方法
s = "  Hello, World  "
print(s.strip())            # 去掉两端空白
print(s.lower())            # 小写
print(s.upper())            # 大写
print(s.replace('World', 'Python'))
print(s.find('World'))      # 找不到返回 -1
print('World' in s)         # True —— 成员检查

# 拆分与合并
line = "a,b,c"
parts = line.split(',')     # ['a', 'b', 'c']
print(parts)
print('-'.join(parts))      # 'a-b-c'
```

---

## 4. 类型注解中的 str：可读性、静态检查、不强制

Python 3.5 起支持 **类型注解（type hints）**。`str` 是最常见的注解之一。注意：**Python 运行时并不强制类型注解**，它只服务于静态检查器（type checker）、IDE、linter 和读代码的人。

```python
def greet(name: str) -> str:
    return f"Hello, {name}"

print(greet("Ada"))
print(greet(123))   # 运行时不会报错（会拼出 'Hello, 123'），但静态检查器会提示
```

工程价值：
- 函数签名一眼看出"输入是字符串、输出也是字符串"。
- mypy / pyright 等静态检查器可提前发现 `greet(123)` 这类错误。
- 与 `typing` 模块配合时，`str` 还能出现在 `list[str]`、`dict[str, int]`、`Sequence[str]` 等复合类型里。

```python
# 字符串在容器类型注解中很常见
def count_chars(text: str) -> dict[str, int]:
    result: dict[str, int] = {}
    for ch in text:
        result[ch] = result.get(ch, 0) + 1
    return result

print(count_chars("aba"))   # {'a': 2, 'b': 1}
```

---

## 5. 不可变带来的工程影响

因为字符串不可变：
- **可以安全地当字典键（dict key）**：
  ```python
  cache = {"user:1": "Ada"}
  print(cache["user:1"])
  ```
- **可以被多个变量共享**，无需拷贝，安全。
- **循环里频繁拼接会很慢**，因为每拼一次就新建一个字符串。大批量拼接推荐 `list.append` + `''.join(...)`。

```python
# 反例：O(n^2) 的字符串拼接
pieces = ["a", "b", "c", "d"]
bad = ""
for p in pieces:
    bad += p         # 每次都新建字符串

# 正例：先用 list 收集，再一次性 join
good = "".join(pieces)
print(bad, good)
```

---

## 小结对照表

| 主题 | 关键点 |
| --- | --- |
| 本质 | 不可变字符序列 |
| 索引/切片 | 从 0 开始，左闭右开，支持负下标 |
| 字面量 | 单/双/三引号、转义 `\`、原始串 `r'...'` |
| 常用方法 | `strip`、`lower`、`replace`、`split`、`join`、`find`、`in` |
| 类型注解 | `def f(s: str) -> str`，运行时**不强制**，静态检查器用 |
| 性能 | 大拼接用 `''.join([...])`，别在循环里 `+=` |

```python
def count_chars(text: str) -> dict[str, int]:
    """统计字符串中每个字符出现的次数。"""
    result: dict[str, int] = {}
    for ch in text:              # 字符串可迭代
        result[ch] = result.get(ch, 0) + 1
    return result


def normalize(names: list[str]) -> str:
    """去掉首尾空白、首字母大写，再用逗号连接。"""
    cleaned = [n.strip().capitalize() for n in names]
    return ", ".join(cleaned)    # 用 join 而不是 += 拼接


if __name__ == "__main__":
    print(count_chars("aba"))                       # {'a': 2, 'b': 1}
    print(normalize(["  ada ", "BOB", "  cy "]))   # Ada, Bob, Cy
```

## py.type.str_index

# 字符串索引（str index）：为什么它是你 Python 之路的第一块基石

> 一句话直觉：字符串索引让你用“第几个字符”的视角精确地读写文本，是所有文本处理、数据清洗、算法题的起点。

---

## 1. 字符串是什么？索引从哪里开始？

在 Python 里，字符串（`str`）是一串**不可变的字符序列**。每个字符都有一个位置编号，称为**索引（index）**。

关键结论：
- Python 的索引从 **0** 开始，不是 1。
- 最后一个字符的索引是 `len(s) - 1`。
- 可以用**负索引**从末尾倒着数：`-1` 是最后一个，`-2` 是倒数第二个。

```python
# 字符串索引基础
s = "Python"

print(s[0])   # P  —— 第 0 个字符
print(s[1])   # y  —— 第 1 个字符
print(s[-1])  # n  —— 最后一个字符
print(s[-2])  # o  —— 倒数第二个字符
print(len(s)) # 6  —— 字符串长度
```

---

## 2. 索引是“读”操作，字符串不可变

关键结论：
- 字符串是**不可变（immutable）**的，不能通过 `s[0] = 'J'` 直接修改。
- 如果想“修改”，必须创建新字符串，例如拼接、切片或 `replace`。

```python
s = "Python"

# 下面这行会报错：TypeError: 'str' object does not support item assignment
# s[0] = 'J'

# 正确做法：用索引读出字符，再拼成新字符串
new_s = "J" + s[1:]
print(new_s)  # Jython
```

---

## 3. 切片（slice）：一次拿多个字符

切片是索引的扩展，语法是 `s[start:stop:step]`。

关键结论：
- `start` 包含，`stop` **不包含**。
- 省略 `start` 默认从 0 开始；省略 `stop` 默认到末尾。
- `step` 可以为负，表示反向取。

```python
s = "Python"

print(s[0:3])   # Pyt   —— 索引 0、1、2
print(s[:3])    # Pyt   —— 从头到索引 2
print(s[3:])    # hon   —— 从索引 3 到末尾
print(s[::2])   # Pto   —— 每隔一个取一个
print(s[::-1])  # nohtyP —— 反转字符串
```

---

## 4. 索引越界与 `IndexError`

关键结论：
- 访问不存在的索引会抛出 `IndexError`。
- 切片越界**不会报错**，只会返回空串或截断到边界。

```python
s = "Python"

# print(s[100])  # IndexError: string index out of range

print(s[100:200])  # 空字符串，不报错
print(s[-100:])    # Python，负索引越界会被截断
```

---

## 5. 实际工程中的用法：遍历、判断、提取

关键结论：
- 用 `for i, ch in enumerate(s)` 同时拿到索引和字符。
- 用 `in` 判断子串是否存在。
- 用索引和切片做首字母、尾字母、回文判断等。

```python
s = "racecar"

# 同时拿索引和字符
for i, ch in enumerate(s):
    print(i, ch)

# 判断回文：正着读和反着读一样
is_palindrome = s == s[::-1]
print(is_palindrome)  # True

# 提取首字母和尾字母
print(s[0], s[-1])    # r r
```

---

## 动手练习

任务：写一个函数 `analyze_text(text)`，完成以下事情：

1. 打印字符串长度。
2. 打印第一个字符和最后一个字符。
3. 打印反转后的字符串。
4. 判断它是否是回文（正反读一样）。
5. 如果长度大于等于 3，打印中间那一段 `text[1:-1]`。

示例：

```python
def analyze_text(text):
    # 在这里实现
    pass

analyze_text("level")
analyze_text("Python")
```

参考输出：

```
长度: 5
首字符: l
尾字符: l
反转: level
是否回文: True
中间部分: eve

长度: 6
首字符: P
尾字符: n
反转: nohtyP
是否回文: False
中间部分: ytho
```

```python
# 字符串索引完整示例
s = "Python"

print("原字符串:", s)
print("索引 0:", s[0])
print("索引 -1:", s[-1])
print("切片 1:4:", s[1:4])
print("反转:", s[::-1])

# 遍历索引和字符
for i, ch in enumerate(s):
    print(f"第 {i} 个字符是 {ch}")

# 回文判断
word = "level"
print("level 是否回文:", word == word[::-1])
```

## py.type.str_method

## 一句话直觉

字符串是 Python 里最常用的数据类型（type），而字符串方法（str method）就是**让文本变得可加工、可清洗、可组合**的瑞士军刀。

---

## 1. 字符串是不可变的（immutable）

直觉：字符串一旦创建就不能原地修改，所有“修改”都会返回一个新字符串。

```python
s = "hello"
# s.upper() 不会改变 s 本身，而是返回新字符串
print(s.upper())  # HELLO
print(s)          # hello

# 如果想保留结果，必须重新赋值
s = s.upper()
print(s)          # HELLO
```

关键结论：**字符串方法不改变原字符串，只返回新值**。

---

## 2. 大小写与判断方法

直觉：处理用户输入、做校验时，大小写统一和类型判断是最基础的操作。

```python
text = "Python Is Fun"

print(text.lower())        # python is fun
print(text.upper())        # PYTHON IS FUN
print(text.title())        # Python Is Fun
print(text.capitalize())   # Python is fun

print("123".isdigit())     # True
print("abc".isalpha())     # True
print("abc123".isalnum())  # True
print("   ".isspace())     # True
print("Hello".istitle())   # True
```

关键结论：**判断类方法返回 bool，常用于表单校验与分支控制**。

---

## 3. 查找、替换与分割

直觉：真实工程里 80% 的文本处理都围绕“找位置、替换内容、按规则拆开”。

```python
s = "name:alice;age:30;city:beijing"

# 查找
print(s.find("age"))       # 8，找不到返回 -1
print(s.index("age"))      # 8，找不到抛 ValueError
print(s.count(":"))        # 3

# 替换
print(s.replace(":", "="))  # name=alice;age=30;city=beijing

# 分割与连接
parts = s.split(";")
print(parts)                # ['name:alice', 'age:30', 'city:beijing']
print(" | ".join(parts))    # name:alice | age:30 | city:beijing

# 按行分割
lines = "a\nb\nc".splitlines()
print(lines)                # ['a', 'b', 'c']
```

关键结论：**split 用于拆分，join 用于拼接，replace 用于替换**。

---

## 4. 去除空白与填充对齐

直觉：爬虫、日志、表格输出中，去除多余空白和对齐文本非常常见。

```python
raw = "   hello world   "

print(raw.strip())    # "hello world"
print(raw.lstrip())   # "hello world   "
print(raw.rstrip())   # "   hello world"

# 去除指定字符
print("###abc###".strip("#"))  # abc

# 填充对齐
print("42".zfill(5))          # 00042
print("hi".ljust(5, "-"))     # hi---
print("hi".rjust(5, "-"))     # ---hi
print("hi".center(6, "*"))    # **hi**
```

关键结论：**strip 系列清理边缘字符，ljust/rjust/center/zfill 控制输出宽度**。

---

## 5. 格式化与编码相关方法

直觉：字符串最终要输出给人看，或者编码成字节（bytes）进行网络传输。

```python
name, score = "Alice", 95.5

# format 方法
print("{} scored {:.1f}".format(name, score))  # Alice scored 95.5

# 更推荐的 f-string（Python 3.6+）
print(f"{name} scored {score:.1f}")            # Alice scored 95.5

# 编码与解码
data = "你好".encode("utf-8")
print(data)                                    # b'\xe4\xbd\xa0\xe5\xa5\xbd'
print(data.decode("utf-8"))                    # 你好

# 判断前后缀
print("report.pdf".endswith(".pdf"))           # True
print("https://a.com".startswith("https"))     # True
```

关键结论：**format/f-string 负责展示，encode/decode 负责字节转换，startswith/endswith 负责快速匹配**。

---

## 动手练习

任务：写一个函数 `clean_tags(text)`，接收一段用逗号分隔的标签字符串，要求：

1. 去掉每个标签首尾空白；
2. 统一转成小写；
3. 过滤掉空标签；
4. 去重但保持原有顺序；
5. 最后用 `" | "` 连接返回。

示例：

```python
clean_tags(" Python, ,AI , python , Data Science ")
# 输出: "python | ai | data science"
```

提示：可组合使用 `split`、`strip`、`lower`、`join` 和集合去重技巧。

```python
# 可运行示例：字符串方法综合练习
def clean_tags(text: str) -> str:
    parts = text.split(",")
    seen = set()
    result = []
    for p in parts:
        tag = p.strip().lower()
        if tag and tag not in seen:
            seen.add(tag)
            result.append(tag)
    return " | ".join(result)

print(clean_tags(" Python, ,AI , python , Data Science "))
# 输出: python | ai | data science

# 补充示例：常见的清洗与格式化
raw = "   Hello, World!   "
print(raw.strip().lower().replace(",", ""))  # hello world!

name, score = "Bob", 88.888
print(f"{name:>5} -> {score:.2f}")          # '  Bob -> 88.89'

print("abc123".isalnum(), "abc123".isdigit())  # True False
print("file.txt".endswith(".txt"))             # True
print("a,b,c".split(","))                     # ['a', 'b', 'c']
print("- ".join(["x", "y", "z"]))            # x - y - z
```


---

## 本课题目

### single_choice · None



- [A] s 变为 'Hello'
- [B] s 仍为 'hello'，因为字符串是不可变对象，但该语句不会报错
- [C] 程序抛出 TypeError
- [D] s 变为 'H'

**参考答案**：2

**解析**：Python 中的 str 是不可变类型，不能通过下标赋值修改已有字符串，因此 s[0] = 'H' 会抛出 TypeError: 'str' object does not support item assignment。

### single_choice · None



- [A] 'tho'
- [B] 'hon'
- [C] 'yth'
- [D] 'Pyt'

**参考答案**：1

**解析**：s[-3:] 表示从倒数第 3 个字符开始取到末尾。'Python' 的倒数字符依次为 n(-1)、o(-2)、h(-3)，因此结果是 'hon'。

### single_choice · None



- [A] 'hello world'
- [B] 'HELLO WORLD'
- [C] 'Hello World'
- [D] 'Helloworld'

**参考答案**：1

**解析**：str.upper() 返回所有字母大写的新字符串，因此 'Hello World' 变为 'HELLO WORLD'。

### single_choice · None



- [A] True
- [B] False
- [C] 1
- [D] 抛出异常

**参考答案**：0

**解析**：str.startswith(prefix) 判断字符串是否以指定前缀开头，'hello' 以 'he' 开头，返回 True。

### single_choice · None



- [A] True
- [B] False
- [C] 1
- [D] 抛出异常

**参考答案**：1

**解析**：str.isalpha() 要求字符串所有字符都是字母才返回 True。'abc123' 包含数字，因此返回 False。

### single_choice · None



- [A] 4
- [B] 5
- [C] 6
- [D] 报错

**参考答案**：1

**解析**：len() 返回字符串中字符的个数。'hello' 有 5 个字符，因此结果为 5。

### single_choice · None



- [A] True
- [B] False
- [C] 1
- [D] 抛出异常

**参考答案**：0

**解析**：in 运算符用于判断子串是否存在于字符串中。'ell' 是 'hello' 的子串，因此返回 True。

### single_choice · None



- [A] 'hellohellohello'
- [B] 'hello hello hello'
- [C] 'hello3'
- [D] 抛出 TypeError

**参考答案**：0

**解析**：字符串与整数相乘表示重复拼接。'hello' * 3 得到 'hellohellohello'。

### single_choice · None



- [A] 'hello3'
- [B] 'hello hello hello'
- [C] 抛出 TypeError
- [D] 3

**参考答案**：2

**解析**：字符串只能与字符串相加，'hello' + 3 会尝试拼接字符串和整数，抛出 TypeError。若要先转成字符串，应使用 str(3)。

### single_choice · None



- [A] 'cd'
- [B] 'cde'
- [C] 'bc'
- [D] 'def'

**参考答案**：0

**解析**：切片 s[2:4] 包含索引 2 和 3，不包含 4。'abcdef' 中索引 2 是 'c'，索引 3 是 'd'，因此结果为 'cd'。

### single_choice · None



- [A] 1
- [B] 2
- [C] 3
- [D] 0

**参考答案**：1

**解析**：str.count(sub) 返回子串在字符串中出现的非重叠次数。'hello' 中有两个 'l'，因此结果为 2。

### single_choice · None



- [A] True
- [B] False
- [C] 'he'
- [D] 抛出异常

**参考答案**：0

**解析**：s.lower() 先返回 'hello'，然后 startswith('he') 判断是否以 'he' 开头，结果为 True。

### single_choice · None



- [A] 'bd'
- [B] 'bcde'
- [C] 'bdf'
- [D] 'ce'

**参考答案**：0

**解析**：切片 s[1:5:2] 从索引 1 开始，到索引 5 之前结束，步长为 2。索引依次为 1、3，对应字符 'b'、'd'，所以结果是 'bd'。

### single_choice · None



- [A] 'hello'
- [B] 'olleh'
- [C] 'h'
- [D] 抛出异常

**参考答案**：1

**解析**：s[::-1] 使用负步长 -1，从后向前取整个字符串，因此得到反转后的 'olleh'。

### single_choice · None



- [A] 4
- [B] 7
- [C] 5
- [D] -1

**参考答案**：0

**解析**：str.find(sub) 返回子串第一次出现的最低索引。'hello world' 中第一个 'o' 出现在索引 4。

### single_choice · None



- [A] 0
- [B] None
- [C] 抛出 ValueError
- [D] -1

**参考答案**：3

**解析**：str.find 在找不到子串时返回 -1，而不是抛出异常。str.index 在找不到时才会抛出 ValueError。

### single_choice · None



- [A] '  hello  '
- [B] 'hello'
- [C] 'hello  '
- [D] '  hello'

**参考答案**：1

**解析**：str.strip() 不带参数时，去除字符串首尾的空白字符（空格、换行、制表符等），因此结果为 'hello'。

### single_choice · None



- [A] 'heLLo'
- [B] 'heLlo'
- [C] 'heLLo' 且原字符串 s 被修改为 'heLLo'
- [D] 'hello'

**参考答案**：0

**解析**：str.replace 返回一个新字符串，将所有 'l' 替换为 'L'，因此得到 'heLLo'。原字符串 s 不会被修改，因为字符串不可变。

### single_choice · None



- [A] ['a', 'b', 'c']
- [B] 'a b c'
- [C] ('a', 'b', 'c')
- [D] 'abc'

**参考答案**：0

**解析**：str.split(',') 使用逗号作为分隔符，将字符串拆分为列表，结果为 ['a', 'b', 'c']。

### single_choice · None



- [A] 'a,b,c'
- [B] 'abc'
- [C] ['a', ',', 'b', ',', 'c']
- [D] 抛出 TypeError

**参考答案**：0

**解析**：str.join(iterable) 用调用该方法的字符串连接可迭代对象中的字符串元素。','.join(['a','b','c']) 得到 'a,b,c'。

### single_choice · None



- [A] 'P' 和 'n'
- [B] 'P' 和 'o'
- [C] 'y' 和 'n'
- [D] 'y' 和 'o'

**参考答案**：0

**解析**：正索引从 0 开始，s[0] 是首字符 'P'；负索引从 -1 开始指向最后一个字符，s[-1] 是 'n'。

### single_choice · None



- [A] 'h'
- [B] 'o'
- [C] 'l'
- [D] 报 IndexError

**参考答案**：1

**解析**：len(s) 为 5，len(s)-1 为 4，s[4] 即最后一个字符 'o'。这是用长度换算最后一个下标的标准写法。

### multi_choice · None



- [A] s[0:100]
- [B] s[-100:2]
- [C] s[10]
- [D] s[1:4]
- [E] s[:]

**参考答案**：[0, 1, 3, 4]

**解析**：切片对越界的 start/stop 会做截断处理，不报错：s[0:100]='hello'，s[-100:2]='he'，s[:]='hello'。只有直接下标访问 s[10] 越界才会抛 IndexError。

### multi_choice · None



- [A] s[-1]
- [B] s[len(s)-1]
- [C] s[len(s)]
- [D] s[-1:]
- [E] s[0]

**参考答案**：[0, 1, 3]

**解析**：s[-1] 与 s[len(s)-1] 都取下表最后一个字符；s[-1:] 是切片，结果也是最后一个字符组成的字符串。s[len(s)] 越界报错，s[0] 取的是首字符。

### fill_blank · None



**参考答案**：["len(s)-1", "len(s) - 1", "len(s)- 1", "len(s) -1"]

**解析**：最后一个字符的下标等于字符串长度减一，即 len(s)-1。

### fill_blank · None



**参考答案**：["2:5", "2:5:", "2: 5"]

**解析**：切片 s[2:5] 取下标 2、3、4，对应 'c'、'd'、'e'，结果为 'cde'。切片是左闭右开区间。

### fill_blank · None



**参考答案**：["h", "'h'", "\"h\""]

**解析**："Python" 长度为 6，-3 等价于下标 3，对应字符 'h'。

### code_reading · None



**参考答案**：e

**解析**：s[1:5] 得到 'bcde'，再对其取 [-1] 得到最后一个字符 'e'。这是切片后再索引的链式操作。

### code_reading · None



**参考答案**：输出 cba。range(len(s)-1, -1, -1) 生成 2、1、0 的下标序列，依次取 'c'、'b'、'a' 并拼接，实现字符串反转。注意 range 的 stop 取 -1 是由于右开区间，以保证下标 0 被包含。

### code_reading · None



**参考答案**：输出空字符串（打印时为一个空行）。当切片起点超过字符串长度时，结果为空字符串，Python 不会抛出 IndexError。

### scenario · None



**解析**：len(line) 是长度，最大合法下标为 len(line)-1，直接写 line[len(line)] 必然越界并抛 IndexError。稳妥写法有 line[-1] 或 line[len(line)-1]，二者都需要保证字符串非空。空字符串时这两种写法同样会抛 IndexError，因此应先用 if line 或 if len(line) > 0 判断，再决定返回什么（如返回 None、空串或默认校验位）。

### scenario · None



**解析**：str.index 返回的是第一个匹配子串的下标，因此当消息中含冒号时，定位到的仍是第一个冒号，s[s.index(':'):] 会从第一个冒号开始截取，从而保留了标题外的内容。要在第一个冒号处切分，应使用 s.index(':')；若想取冒号之后（不含冒号）的部分，应写 s[s.index(':')+1:]，注意 +1 以避免把冒号本身包含进去。若可能不存在冒号，应使用 find 并检查返回值是否为 -1，避免 ValueError。

### single_choice · None



- [A] 返回空字符串 ''
- [B] 返回 None
- [C] 抛出 IndexError
- [D] 抛出 ValueError

**参考答案**：2

**解析**：字符串长度为 3，合法下标范围是 0~2 或 -1~-3。访问 s[3] 超出范围，Python 抛出 IndexError: string index out of range。

### scenario · None



**解析**：颜色字符串 "#1A2B3C" 长度为 7，索引 0 是 '#'，之后每两个字符为一个通道。R = s[1:3]、G = s[3:5]、B = s[5:7]。切片是左闭右开，所以起点为奇数、终点为起点加 2。常见错误包括把终点写成包含式（如 s[1:2] 只取一个字符）、把起点写成 0 导致带上 '#'，以及用下标 s[7] 访问最后位置而越界抛 IndexError。应始终注意长度与下标上界的关系。

### single_choice · None



- [A] 'b'
- [B] 'e'
- [C] 'f'
- [D] 'd'

**参考答案**：1

**解析**：负索引 -1 指最后一个字符 'f'，-2 指倒数第二个字符 'e'，因此输出 'e'。

### single_choice · None



- [A] s[i] 与 s[-i] 总是指向同一字符
- [B] s[i] 与 s[i-n] 指向同一字符
- [C] s[i] 与 s[n-i] 总是指向同一字符
- [D] s[i] 与 s[i+n] 指向同一字符

**参考答案**：1

**解析**：负索引等价于正索引加上长度：-i 等价于 n - i，因此 s[-i] 等于 s[n-i]；反过来 s[i] 等于 s[i-n]（当 i-n 为负时）。选项 B 描述的是 s[i] == s[i-n] 这一等价转换。

### single_choice · None



- [A] Python
- [B] Pto
- [C] 报错
- [D] 空行

**参考答案**：0

**解析**：range(len(s)) 生成 0 到 5 的下标序列，依次取每个字符并按顺序拼接，输出完整字符串 Python。

### single_choice · None



- [A] start 和 stop 都是闭区间端点，两边都取到
- [B] stop 下标对应的字符会被包含在结果中
- [C] stop 下标对应的字符不会被包含，切片是左闭右开
- [D] start 必须小于 stop，否则一定报错

**参考答案**：2

**解析**：切片是左闭右开区间，包含 start 不包含 stop。当 start >= stop 且步长为正时，结果为空字符串而不是报错。

### single_choice · None



- [A] 'bcd'
- [B] 'cde'
- [C] 'cdef'
- [D] 'bcd e'

**参考答案**：1

**解析**：切片 s[2:5] 取下标 2、3、4，对应字符 'c'、'd'、'e'，结果为 'cde'。

### multi_choice · None



- [A] s[4]
- [B] s[-2]
- [C] s[len(s)-2]
- [D] s[5]
- [E] s[-1]

**参考答案**：[0, 1, 2]

**解析**：s[4]='e'；s[-2] 为倒数第二个字符 'e'；s[len(s)-2]=s[4]='e'。s[5]='f'，s[-1]='f'，均不等于 'e'。

### multi_choice · None



- [A] 字符串是不可变对象，s[0] = 'X' 会抛出 TypeError
- [B] 负索引 -1 表示最后一个字符
- [C] 访问越界下标会抛出 IndexError
- [D] 字符串下标可以是浮点数，如 s[1.0]

**参考答案**：[0, 1, 2]

**解析**：字符串不可变，赋值给下标会抛 TypeError；负索引 -1 表示末尾；越界抛 IndexError。下标必须是整数，s[1.0] 会抛 TypeError，所以 D 错误。

### single_choice · None



- [A] "Hello, World"
- [B] "hello, world"
- [C] "HELLO, WORLD"
- [D] 运行报错

**参考答案**：1

**解析**：str.lower() 返回一个全部字符转为小写的新字符串。原字符串 s 不会被修改，因为字符串是不可变的，但 result 保存的是转换后的结果 "hello, world"。

### single_choice · None



- [A] '  hello  '
- [B] 'hello'
- [C] ' hello '
- [D] 'hello  '

**参考答案**：1

**解析**：strip() 默认去除字符串两端的所有空白字符（空格、制表符、换行等），只作用于两端，不处理中间内容。所以 "  hello  " 变为 "hello"。

### single_choice · None



- [A] "Hello"
- [B] "olleH"
- [C] "H"
- [D] 抛出 ValueError

**参考答案**：1

**解析**：切片 [::-1] 使用步长 -1 将字符串逆序，因此得到 "olleH"。这是不修改原串、返回新字符串的常用逆序写法。

### single_choice · None



- [A] ["a", "b", "c"]
- [B] ["a", "b=c"]
- [C] ["a=b", "c"]
- [D] "a b c"

**参考答案**：1

**解析**：split 的第二个参数 maxsplit=1 表示最多切分一次，所以只在第一个 "=" 处分割，得到 ["a", "b=c"]。

### multi_choice · None



- [A] strip()
- [B] upper()
- [C] replace()
- [D] split()

**参考答案**：[0, 1, 2]

**解析**：strip、upper、replace 都返回新的字符串。split() 返回的是列表，不是字符串，所以不选。字符串是不可变的，所有这类“修改”方法其实都是返回新对象。

### multi_choice · None



- [A] strip() 去除两端空白字符
- [B] lstrip() 只去除左端字符
- [C] strip("ab") 会去除两端所有出现的 a 或 b 字符
- [D] rstrip() 会去除字符串中间的空白字符

**参考答案**：[0, 1, 2]

**解析**：strip 默认去除两端空白；传入参数时，参数被当作“要去除的字符集合”，会去掉两端任意属于该集合的字符；lstrip/rstrip 分别只处理左/右端。rstrip 不影响中间部分，所以 D 错误。

### multi_choice · None



- [A] "123".isdigit()
- [B] "abc".islower()
- [C] "Abc".islower()
- [D] "\t
  ".isspace()

**参考答案**：[0, 1, 3]

**解析**："123" 全为数字，isdigit 为 True；"abc" 全为小写字母，islower 为 True；"Abc" 含有大写字母，islower 为 False；"\t\n" 全是空白字符，isspace 为 True。

### multi_choice · None



- [A] startswith 可以接受字符串元组作为前缀集合
- [B] replace 可以指定替换次数
- [C] find 找不到子串会抛出异常
- [D] replace 返回的是被修改后的原字符串对象本身

**参考答案**：[0, 1]

**解析**：startswith 支持元组前缀；replace 的第三个参数可限制替换次数。find 找不到时返回 -1 而非抛异常，故 C 错误；字符串不可变，replace 返回新字符串，不会修改原对象，故 D 错误。

### fill_blank · None



**参考答案**：["title", "title"]

**解析**：str.title() 会把每个单词的首字母大写、其余字母小写，得到 "Hello World"。注意与 capitalize() 区分，后者只处理整串的第一个字母。

### fill_blank · None



**参考答案**：["lstrip", "lstrip()"]

**解析**：lstrip() 只去除字符串左端的空白字符，保留右端空白，因此 "  hi  " 变为 "hi  "。如果使用 strip() 会连右端也去掉，不符合要求。

### code_reading · None



**参考答案**：2 3

**解析**："Hello" 中 l 出现在下标 2 和 3（下标从 0 开始）。find 返回第一次出现的下标 2，rfind 返回最后一次出现的下标 3。

### code_reading · None



**参考答案**：4 ['a', 'b', '', 'c']

**解析**：split 遇到分隔符就切，连续两个逗号之间会产生一个空字符串元素。所以切分结果为 ['a', 'b', '', 'c']，共有 4 个元素，长度是 4。

### single_choice · None



- [A] "a,b,c".split(",") 返回列表 ["a", "b", "c"]
- [B] "a,b,c".split() 返回字符串 "abc"
- [C] "a,b,c".split(",") 会修改原字符串
- [D] "a b c".split(" ") 与 "a b c".split() 结果总是一样

**参考答案**：0

**解析**：split(",") 按指定分隔符切分并返回列表。split() 也返回列表而非字符串，字符串本身不可变不会被修改；当字符串含连续空白时，split(" ") 与无参 split() 结果不同（无参会合并连续空白），故 D 不正确。

### scenario · None



**解析**：推荐使用 endswith 并传入字符串元组，例如 name.lower().endswith((".csv", ".txt"))，这样一次匹配多种后缀。边界情况是扩展名大小写不一致（如 .CSV），应先用 lower() 统一再比较；同时要注意像 "a.csv.bak" 这类名字以 .bak 结尾不应被误判。

### single_choice · None



- [A] s[0]
- [B] s[-1]
- [C] s[1:4]
- [D] s[0] = "p"

**参考答案**：3

**解析**：字符串是不可变对象，不能通过下标赋值来修改其内容，s[0] = "p" 会抛出 TypeError。取值、负数索引和切片都是合法的读操作。

### single_choice · None



- [A] False False True
- [B] True True True
- [C] False True False
- [D] True False True

**参考答案**：0

**解析**："abc123" 并非全为数字，所以 isdigit() 为 False；并非全为字母，所以 isalpha() 为 False；由于全部由字母和数字组成，isalnum() 为 True。

### single_choice · None



- [A] "heLLo"
- [B] "heLlo"
- [C] "heLloL"
- [D] "HeLLo"

**参考答案**：0

**解析**：replace 默认把字符串中所有出现的 "l" 都替换为 "L"，"hello" 中两个 l 都被替换，得到 "heLLo"。

### single_choice · None



- [A] 两者在找不到子串时都抛异常
- [B] find 找不到返回 -1，index 找不到抛 ValueError
- [C] index 找不到返回 -1，find 找不到抛 ValueError
- [D] find 和 index 都不能接受起止位置参数

**参考答案**：1

**解析**：find() 找不到子串时返回 -1，而 index() 找不到时会抛出 ValueError。两者都可接受可选的起始和结束位置参数。

### single_choice · None



- [A] "abc"
- [B] "a-b-c"
- [C] ["a", "-", "b", "-", "c"]
- [D] 抛出 TypeError

**参考答案**：1

**解析**：join 以调用它的字符串作为连接符，把可迭代对象中的多个字符串依次拼起来，因此 "-".join(["a","b","c"]) 得到 "a-b-c"。要注意 join 只能连接字符串元素，否则会报错。

### single_choice · None



- [A] "image.png".endswith(".png") 返回 True
- [B] "hello".startswith("he") 返回 True
- [C] 两者都可以接受一个字符串元组作为参数来匹配多种前缀或后缀
- [D] 两者都只能一次匹配一个字符

**参考答案**：3

**解析**：startswith 和 endswith 都能接受字符串或字符串元组作为参数，例如 "a.txt".endswith((".txt", ".md"))，因此说它们“只能匹配一个字符”是错误的。

### single_choice · None



- [A] s.startswith("py")
- [B] s.lower().startswith("py")
- [C] s.find("py") == 0
- [D] s.contains("py")

**参考答案**：1

**解析**：要实现不区分大小写的判断，可先把字符串统一为小写再调用 startswith("py")。A 区分大小写；C 用 find 只判断出现位置，对区分大小写仍有要求且语义不清；D 的 contains 不是字符串方法。
