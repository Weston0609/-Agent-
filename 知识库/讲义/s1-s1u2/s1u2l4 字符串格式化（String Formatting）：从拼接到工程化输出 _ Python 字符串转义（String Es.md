# s1u2l4 字符串格式化（String Formatting）：从拼接到工程化输出 / Python 字符串转义（String Escape）：从直觉到工程

> 来源 `content/lessons/s1u2l4.json`

## py.type.str_format

# 字符串格式化（String Formatting）：从拼接到工程化输出

## 一句话直觉

**为什么要学它？** 程序最终是给人看的，而人看的是文本。字符串格式化就是把你手里零散的变量，优雅、可控、不易出错地拼成一句人能读懂的话。

---

## 第 1 节：为什么不能直接 `+` 拼接？

最原始的方式是用 `+` 把字符串连接起来。问题有三个：

1. 非字符串类型必须先 `str()` 转换，否则报 `TypeError`；
2. 拼接多了引号、逗号、空格容易错位，可读性差；
3. 数字精度、对齐、千分位等格式需求根本无法表达。

```python
name = "Alice"
age = 30
# 错误写法：age 是 int，不能直接和 str 相加
# print("Name: " + name + ", Age: " + age)  # TypeError

# 勉强能跑，但很啰嗦
print("Name: " + name + ", Age: " + str(age))
```

所以我们需要一种“把值嵌入模板”的机制，这就是**字符串格式化（string formatting）**。

---

## 第 2 节：`%` 格式化——最古老但仍在使用

Python 早期借鉴 C 语言的 `printf` 风格，用 `%` 作为占位符。

常用占位符：

- `%s`：字符串（任何对象都会被 `str()`）
- `%d`：整数
- `%f`：浮点数（默认 6 位小数）
- `%.2f`：保留 2 位小数
- `%5d`：宽度 5，右对齐

```python
name = "Alice"
age = 30
score = 95.678

# %s 万能，%d 整数，%.2f 保留两位小数
print("Name: %s, Age: %d, Score: %.2f" % (name, age, score))
# 输出：Name: Alice, Age: 30, Score: 95.68

# 宽度与对齐：%10s 右对齐宽度 10，%-10s 左对齐
print("[%10s]" % name)   # [     Alice]
print("[%-10s]" % name)  # [Alice     ]
```

`%` 格式化的缺点：参数多时容易顺序错、类型不匹配时报错不直观。**新代码不推荐首选**，但读老代码必须认识它。

---

## 第 3 节：`str.format()`——具名与位置占位

Python 2.6 引入 `str.format()`，用 `{}` 作为占位符，支持位置和关键字。

```python
name = "Alice"
age = 30

# 位置参数
print("Name: {}, Age: {}".format(name, age))

# 索引复用
print("{0} is {1}, {0} is learning Python".format(name, age))

# 关键字参数，可读性最好
print("Name: {name}, Age: {age}".format(name=name, age=age))

# 格式规格：{:[填充][对齐][宽度][.精度][类型]}
print("{:>10}".format(name))    # 右对齐宽度 10
print("{:<10}".format(name))    # 左对齐宽度 10
print("{:^10}".format(name))    # 居中宽度 10
print("{:.2f}".format(95.678))  # 保留两位小数
print("{:,}".format(1234567))   # 千分位：1,234,567
```

`str.format()` 比 `%` 更灵活，但写多了仍然冗长。

---

## 第 4 节：f-string（格式化字符串字面量）——现代首选

Python 3.6 引入 **f-string（formatted string literal）**，在字符串前加 `f`，直接把表达式写在 `{}` 里。

```python
name = "Alice"
age = 30
score = 95.678

# 最直观：变量直接嵌入
print(f"Name: {name}, Age: {age}")

# 可以写任意表达式
print(f"Next year: {age + 1}")
print(f"Score: {score:.2f}")

# 格式规格与 format() 完全一致
print(f"{name:>10}")
print(f"{1234567:,}")

# 调试神技：= 会同时打印表达式和值（Python 3.8+）
print(f"{age = }, {score = :.1f}")
# 输出：age = 30, score = 95.7
```

**为什么 f-string 是工程级首选？**

1. 可读性最高，变量就在它出现的位置；
2. 性能最好（编译期处理，比 `%` 和 `format()` 都快）；
3. 支持完整表达式和格式规格；
4. `=` 调试语法极大方便排查。

---

## 第 5 节：工程中的选择与安全

### 格式规格速查

| 需求 | 写法 |
|---|---|
| 保留 2 位小数 | `f"{x:.2f}"` |
| 千分位 | `f"{x:,}"` |
| 百分比 | `f"{x:.1%}"` |
| 右对齐宽度 8 | `f"{s:>8}"` |
| 补零 | `f"{n:05d}"` |
| 十六进制 | `f"{n:#x}"` |

### 安全提示

**永远不要把用户输入直接当作格式模板**，否则可能触发格式化注入或意外异常：

```python
user_template = "{name.__class__}"  # 恶意模板
# "{name.__class__}".format(name="x")  # 会暴露内部信息
```

正确做法：把用户输入作为**被格式化的值**，而模板由程序自己控制。

```python
user_input = "Alice"
print(f"Hello, {user_input}")  # 安全：模板是固定的
```

### 三种方式对比

| 方式 | 引入版本 | 可读性 | 性能 | 推荐度 |
|---|---|---|---|---|
| `%` | 很早 | 低 | 中 | 仅读旧代码 |
| `str.format()` | 2.6 | 中 | 中 | 特定场景 |
| f-string | 3.6 | 高 | 高 | **首选** |

---

## 动手练习

**任务：写一个“学生成绩报告生成器”**

要求：

1. 定义三个变量：`name`（字符串）、`score`（0~100 的浮点数）、`rank`（整数）。
2. 用 **f-string** 输出一行报告，格式如下（注意对齐和精度）：

   ```
   | Name      | Score | Rank |
   | Alice     | 95.68 |    1 |
   ```

   要求：Name 左对齐宽度 10，Score 保留 2 位小数，Rank 右对齐宽度 4。

3. 再用 `str.format()` 实现同样的输出，比较两种写法。
4. 用 `=` 调试语法打印 `name`、`score`、`rank` 三个变量。
5. 把 `score` 改成 `85`（整数），看 f-string 是否仍然工作，思考为什么。

**提交形式**：一个 `.py` 文件，运行后输出对齐整齐的表格。

**进阶思考**：如果 `score` 是 `None`，你的代码会怎样？如何防御？

```python
# 字符串格式化三种方式完整示例

name = "Alice"
score = 95.678
rank = 1

# 1) % 格式化（老式）
print("%% 方式: Name: %s, Score: %.2f, Rank: %d" % (name, score, rank))

# 2) str.format()
print("format 方式: | {:<10} | {:>5} | {:>4} |".format(name, f"{score:.2f}", rank))

# 3) f-string（推荐）
print(f"f-string 方式: | {name:<10} | {score:>5.2f} | {rank:>4} |")

# 调试语法（Python 3.8+）
print(f"{name = }, {score = :.2f}, {rank = }")

# 表达式中直接计算
print(f"Score + 5 = {score + 5:.2f}")

# 安全示例：用户输入作为值，而非模板
user_input = "{name.__class__}"  # 恶意字符串
print(f"安全输出: {user_input}")  # 原样输出，不会执行
```

## py.type.str_escape

# Python 字符串转义（String Escape）：从直觉到工程

## 一句话直觉

当你想在字符串里写一个 "引号"、一个换行、一个反斜杠，或者一段中文/emoji 时，Python 需要一套“暗号”来区分“这是普通字符”还是“这是特殊含义”——这套暗号就叫**转义（escape）**。

学不会转义，你的字符串就会在报错和乱码之间反复横跳；学会转义，你就能精确控制文本的每一个字节。

---

## 1. 为什么需要转义？

Python 用引号 `'` 或 `"` 来圈定字符串。但如果字符串本身要包含引号呢？

```python
# 错误写法：Python 不知道字符串在哪里结束
# text = 'It's a book'

# 正确：用反斜杠转义内部引号
text = 'It\'s a book'
print(text)  # It's a book
```

反斜杠 `\` 是转义字符（escape character）。它告诉 Python：“下一个字符不要按字面理解”。

常见转义序列（escape sequence）：

| 写法 | 含义 |
|------|------|
| `\'` | 单引号 |
| `\"` | 双引号 |
| `\\` | 一个反斜杠 |
| `
` | 换行（newline） |
| `\t` | 制表符（tab） |
| `\r` | 回车（carriage return） |
| `\u4e2d` | Unicode 字符“中” |
| `\N{SNOWMAN}` | 按名称的 Unicode 字符 ☃ |

```python
print('第一行\n第二行')
print('姓名\t年龄')
print('反斜杠：\\')
print('Unicode：\u4e2d\u6587')
print('命名：\N{SNOWMAN}')
```

---

## 2. 原始字符串（Raw String）：让反斜杠“失去魔法”

写正则表达式、Windows 路径时，反斜杠太多会让人崩溃。原始字符串用 `r"..."` 声明，里面所有反斜杠都按字面处理。

```python
# 普通字符串：\n 被解释成换行
print('C:\new\test')   # C: 换行 ew 制表符 est

# 原始字符串：\n 就是两个字符
print(r'C:\new\test')  # C:\new\test
```

注意：原始字符串不能以奇数个反斜杠结尾，因为最后一个反斜杠会“吃掉”结束引号。

```python
# print(r'abc\')  # SyntaxError
print(r'abc\\')    # abc\\
```

---

## 3. 三引号与多行字符串

三引号 `'''...'''` 或 `"""..."""` 可以直接跨行写字符串，保留换行和缩进。

```python
message = """亲爱的用户：

您的订单已发货。
谢谢！
"""
print(message)
```

如果在三引号字符串前加 `r`，就得到“原始多行字符串”，常用于正则或 SQL 模板。

```python
pattern = r"""
    \d{3}   # 三位数字
    -\d{4}  # 短横线加四位数字
"""
print(pattern)
```

---

## 4. 常见坑：无效转义与 DeprecationWarning

Python 3.12 起，无法识别的转义序列会触发 `SyntaxWarning`，未来可能变成错误。

```python
# 下面 \d 不是合法转义，会警告
# print('\d')

# 正确做法：要么用原始字符串，要么写 \\d
print(r'\d')
print('\\d')
```

另一个经典坑：`\u` 后面必须跟 4 位十六进制；`\x` 后面必须跟 2 位。

```python
print('\u4e2d')   # 中
print('\x41')     # A
```

---

## 5. 工程级视角：字符串转义与类型提示

Python 是动态类型语言，运行时不会强制检查类型注解。但类型检查器（type checker，如 mypy）会读注解。字符串字面量的类型始终是 `str`，无论里面有多少转义。

```python
def greet(name: str) -> str:
    return f"Hello, {name}\n"
```

如果你用 `reveal_type` 调试，会看到：

```python
from typing import reveal_type

x = "a\nb"
reveal_type(x)  # Revealed type is "builtins.str"
```

转义只影响字符串的**运行时内容**，不影响它的**静态类型**。这一点在写配置解析、日志格式化、协议编解码时非常重要：类型对了不代表内容对。

---

## 动手练习

**任务：写一个“转义检查器”小脚本**

1. 在本地新建 `escape_checker.py`。
2. 定义三个字符串：
   - `s1 = 'It\'s a test'`
   - `s2 = r'C:
ew\test'`
   - `s3 = """第一行
第二行\t制表符"""`
3. 对每个字符串打印：
   - 字面量（用 `repr()` 显示转义后的真实表示）
   - 长度 `len()`
   - 是否包含换行符 `'
' in s`
4. 额外挑战：把 `s2` 从原始字符串改成普通字符串，观察输出差异，并解释为什么。

提示：`repr()` 会把你看到的字符串“还原”成 Python 源码里写的样子，是调试转义的利器。

```python
# escape_checker.py
# 运行：python escape_checker.py

# 1. 单引号转义
s1 = 'It\'s a test'
print('s1 repr:', repr(s1))
print('s1 len :', len(s1))

# 2. 原始字符串：反斜杠不转义
s2 = r'C:\new\test'
print('s2 repr:', repr(s2))
print('s2 len :', len(s2))

# 3. 三引号多行字符串
s3 = """第一行
第二行\t制表符"""
print('s3 repr:', repr(s3))
print('s3 len :', len(s3))
print('s3 含换行:', '\n' in s3)

# 4. 对比：普通字符串 vs 原始字符串
normal = 'C:\new\test'
raw = r'C:\new\test'
print('normal repr:', repr(normal))
print('raw    repr:', repr(raw))
print('两者相等？', normal == raw)
```


---

## 本课题目

### single_choice · None



- [A] {name} is {age} years old
- [B] Alice is {age} years old
- [C] Alice is 25 years old
- [D] TypeError

**参考答案**：2

**解析**：f-string 中花括号内的表达式会被求值并替换。name 和 age 都被替换为对应的值，所以输出 'Alice is 25 years old'。

### single_choice · None



- [A] f"value is {x}"
- [B] "value is {}".format(x)
- [C] "value is %s" % x
- [D] "value is {x}".format()

**参考答案**：3

**解析**：选项 D 中使用了命名占位符 {x}，但 format() 未传入任何参数，会抛出 KeyError。其余三种方式都能正确嵌入变量值。

### single_choice · None



- [A] 10 / 3 = 3.33
- [B] 10 / 3 = 3.3333333333333335
- [C] 10 / 3 = 3.3
- [D] 10 / 3 = 3

**参考答案**：0

**解析**：x / y 的结果是 3.3333333333333335，格式化 .2f 保留两位小数后为 3.33，所以输出 '10 / 3 = 3.33'。

### single_choice · None



- [A] |*cat**|
- [B] |**cat*|
- [C] |cat****|
- [D] |****cat|

**参考答案**：1

**解析**：{:*^7} 表示用 * 填充、居中对齐、总宽度 7。cat 占 3 个字符，左右各补 2 个 *，即 '**cat**'，加上竖线输出 '|**cat**|'。

### single_choice · None



- [A] A and B and A
- [B] A and B and B
- [C] A and A and B
- [D] IndexError

**参考答案**：0

**解析**：位置参数可以重复引用，{0} 对应 'A'，{1} 对应 'B'，又出现 {0} 仍然对应 'A'，所以输出 'A and B and A'。

### single_choice · None



- [A] 10
- [B] 1010
- [C] 2
- [D] 0b1010

**参考答案**：1

**解析**：{:b} 表示二进制格式，十进制 10 的二进制是 1010，所以输出 '1010'。

### single_choice · None



- [A] ff
- [B] 0xff
- [C] FF
- [D] 0XFF

**参考答案**：1

**解析**：{:#x} 表示带 0x 前缀的十六进制格式（小写），255 的十六进制是 ff，所以输出 '0xff'。

### single_choice · None



- [A] 5
- [B] x + y = 5
- [C] x + y =
- [D] TypeError

**参考答案**：1

**解析**：Python 3.8+ 的 f-string 支持 = 调试语法，会同时输出表达式文本和求值结果，即 'x + y = 5'。

### single_choice · None



- [A] {A}
- [B] {{A}}
- [C] A
- [D] ValueError

**参考答案**：0

**解析**：{{ 转义为单个 {，}} 转义为单个 }，中间的 {} 是占位符被 'A' 替换，所以输出 '{A}'。

### single_choice · None



- [A] Hello, World
- [B] Hello, Python
- [C] Hello, {name}
- [D] NameError

**参考答案**：0

**解析**：f-string 在创建时立即求值，greeting 在 name 被修改前已经保存了 'Hello, World'，后续修改 name 不会影响 greeting。

### single_choice · None



- [A] Values: [1, 2, 3]
- [B] Values: 1, 2, 3
- [C] Values: [1, 2, 3] 中的每个元素分别替换
- [D] TypeError

**参考答案**：0

**解析**：format() 将整个列表作为单个对象插入，调用 str(list) 得到 '[1, 2, 3]'，所以输出 'Values: [1, 2, 3]'。

### single_choice · None



- [A] f"{x}"
- [B] f'{x}'
- [C] f"{x!r}"
- [D] f"{x:\d}"

**参考答案**：3

**解析**：选项 D 中格式说明符 \d 不是合法的格式类型（数字格式用 d 表示，但反斜杠导致无效），会引发 ValueError 或语法问题。其余选项都是合法的 f-string 写法。

### single_choice · None



- [A] 3.14159
- [B] 3.14
- [C] 3.142
- [D] 3.1

**参考答案**：1

**解析**：:.2f 表示保留两位小数的浮点数格式，3.14159 四舍五入后为 3.14。

### single_choice · None



- [A] Hello, %s! You have %d messages.
- [B] Hello, Bob! You have 5 messages.
- [C] Hello, name! You have 5 messages.
- [D] TypeError

**参考答案**：1

**解析**：% 格式化中，%s 被字符串 name 替换，%d 被整数 5 替换，输出 'Hello, Bob! You have 5 messages.'。

### single_choice · None



- [A] |hi        |
- [B] |        hi|
- [C] |   hi     |
- [D] |hi|

**参考答案**：0

**解析**：{:<10} 表示左对齐，总宽度为 10，不足部分在右侧补空格。'hi' 占 2 个字符，后面补 8 个空格。

### single_choice · None



- [A] abc     
- [B]      abc
- [C]    abc  
- [D] abc

**参考答案**：1

**解析**：{:>8} 表示右对齐，总宽度为 8，abc 占 3 个字符，左侧补 5 个空格。

### single_choice · None



- [A] 42
- [B] 00042
- [C] 42000
- [D] 5d

**参考答案**：1

**解析**：:05d 表示用 0 填充到总宽度 5 的十进制整数，42 变成 '00042'。

### single_choice · None



- [A] 0.3%
- [B] 25.6%
- [C] 25.60%
- [D] 2.6%

**参考答案**：1

**解析**：:.1% 表示将数值乘以 100 并保留一位小数后加百分号。0.256 乘以 100 得 25.6，保留一位小数为 25.6%，所以输出 '25.6%'。

### single_choice · None



- [A] 1234567
- [B] 1,234,567
- [C] 1.234.567
- [D] 1 234 567

**参考答案**：1

**解析**：{:,} 使用逗号作为千位分隔符，输出 '1,234,567'。

### single_choice · None



- [A] 第一行输出 'Hello, {name}!'，第二行输出 'Hello, Alice!'
- [B] 两行都输出 'Hello, Alice!'
- [C] 两行都输出 'Hello, {name}!'
- [D] 第一行报错，第二行输出 'Hello, Alice!'

**参考答案**：0

**解析**：普通字符串中的 {name} 不会自动替换，只有调用了 format() 或使用 f-string 才会替换。第一行没有调用 format()，所以原样输出。

### single_choice · None



- [A] C:\
  ew\\test
- [B] C:
  ew\test
- [C] C:newtest
- [D] C:\
  \\t

**参考答案**：1

**解析**：在普通字符串中，反斜杠是转义字符的引导符。'\\' 表示一个真正的反斜杠，所以 'C:\\new\\test' 解析后是 C:\new\test，其中 \n 和 \t 因为前面已经有被转义的反斜杠，不会再被当成换行或制表符。

### single_choice · None



- [A] 3
- [B] 4
- [C] 5
- [D] 报错

**参考答案**：0

**解析**：\x41 是十六进制转义，表示字符 'A'，占 1 个字符；\t 是制表符，占 1 个字符；'B' 占 1 个字符。因此总长度为 3。注意 \x41 看起来像 4 个源码字符，但只生成一个字符。

### multi_choice · None



- [A] 
  
- [B] \x41
- [C] \q
- [D] \u4e2d
- [E] \U0001F600

**参考答案**：[0, 1, 3, 4]

**解析**：\n 是换行，\x41 是十六进制转义，\u4e2d 是四位 Unicode 转义，\U0001F600 是八位 Unicode 转义，均合法。\q 不是已定义的转义序列，会原样保留反斜杠和 q（在某些版本会触发 DeprecationWarning），不属于“合法转义”。

### multi_choice · None



- [A] r'
  ' 的长度是 2
- [B] 原始字符串中仍然不能以奇数个反斜杠结尾
- [C] 原始字符串中可以使用 \u 转义来插入 Unicode 字符
- [D] r'\' 是合法的，表示一个反斜杠
- [E] 正则表达式中常使用原始字符串来避免双重转义

**参考答案**：[0, 1, 4]

**解析**：原始字符串中反斜杠不触发转义，r'\n' 长度为 2；尾部不能让反斜杠落单（如 r'\' 非法）；\u 在原始字符串中也不会被解析。正则中推荐用 r'' 正是为了避免 Python 层和正则层双重转义。

### multi_choice · None



- [A] '\\'
- [B] chr(92)
- [C] r'\'
- [D] '\x5c'
- [E] '\'

**参考答案**：[0, 1, 3]

**解析**：'\\' 是两个源码反斜杠，转义为一个反斜杠；chr(92) 直接构造反斜杠字符；'\x5c' 用十六进制转义表示反斜杠。r'\' 因为尾部反斜杠落单而非法；'\' 单独的反斜杠也是语法错误。

### fill_blank · None



**参考答案**：["HI", "'HI'", "\"HI\""]

**解析**：\x48 是 'H'，\x49 是 'I'，两个转义拼接后输出 HI。

### fill_blank · None



**参考答案**：["r", "R"]

**解析**：原始字符串前缀为 r 或 R，如 r'C:\new'。它让反斜杠不被解析为转义引导符。

### code_reading · None



**参考答案**：输出为：'a\nb\tc' 和 5。解释：s 中包含 a、换行、b、制表符、c，共 5 个字符；repr 把它们显示为转义形式 \n 和 \t。

**解析**：repr 会以可读的转义形式展示字符串中的换行和制表符，而 len 统计的是实际字符个数，均为 1 个字符，所以总长度为 5。

### code_reading · None



**参考答案**：第一行输出字符串 \N{BULLET}（反斜杠加 N{BULLET}，共 9 个字符）；第二行输出 • 这一个圆圈符号。原因：第一行中的反斜杠被转义，不再触发命名 Unicode 转义；第二行使用了合法的 \N{...} 转义。

**解析**：命名 Unicode 转义必须在源码中写成单个反斜杠加 N{name}。如果写成 '\\N{...}'，反斜杠先被转义，剩下的 N{...} 只是普通文本。

### code_reading · None



**参考答案**：第一行输出 中；第二行输出字面文本 \u4e2d（6 个字符）。原因：普通字符串中 \u4e2d 是 Unicode 转义；原始字符串中不解析转义，反斜杠和 u4e2d 原样保留。

**解析**：这考察原始字符串与转义的优先级：r 前缀会让所有转义失效，因此 \u 在原始字符串中不再是 Unicode 转义。

### scenario · None



**解析**：普通字符串中 \n 和 \r 等会被解析为转义字符，导致路径中的 new 和 report 前出现换行、回车等不可见字符。正确做法包括：使用原始字符串 r'C:\new\report.txt'，或对每个反斜杠写两次 'C:\\new\\report.txt'，或使用正斜杠 'C:/new/report.txt'。

### scenario · None



**解析**：在普通字符串中写正则，Python 层先做一次转义，正则引擎再做一次解析，容易出现双重转义，需要写四个反斜杠表示正则里的一个反斜杠，极易出错且难读。推荐使用原始字符串 r'...'，让 Python 不做转义，由正则引擎单独处理，代码更清晰、更不易错。

### single_choice · None



- [A] 它表示一个换行符，长度为 1
- [B] 它表示两个字符：反斜杠和字母 n，长度为 2
- [C] 它在 Python 中是非法的
- [D] 它等价于 '\
  '，长度为 2，但末尾不能有奇数个反斜杠

**参考答案**：1

**解析**：原始字符串中的反斜杠不会被当作转义引导符，因此 r'\n' 包含两个字符：一个反斜杠和一个字母 n，长度为 2。选项 D 的前半句正确，但原始字符串末尾确实不能是奇数个反斜杠，这使它不是最准确的描述；选项 B 直接描述了实际内容。

### single_choice · None



- [A] '\u0041'
- [B] '\N{GREEK SMALL LETTER ALPHA}'
- [C] '\xZZ'
- [D] '\\'

**参考答案**：2

**解析**：\x 后面必须跟两个十六进制数字，'\xZZ' 中的 ZZ 不是合法的十六进制数字，因此会报错（SyntaxError）。\u0041 是合法的 Unicode 转义，\N{...} 是合法的命名 Unicode 转义，'\\' 表示一个反斜杠。

### single_choice · None



- [A] 'A'
- [B] '101'
- [C] '\x41'
- [D] 报错，八进制转义最多两位

**参考答案**：0

**解析**：\101 是八进制转义，101(八进制) = 65(十进制)，对应 ASCII 字符 'A'。八进制转义最多三位数字。

### single_choice · None



- [A] a\tb
- [B] a    b（a 与 b 之间是一个制表符对齐的空白）
- [C] ab
- [D] 报错

**参考答案**：1

**解析**：\t 是制表符转义，打印时会在 a 和 b 之间产生一个制表位，具体显示宽度取决于终端设置，但不会原样打印出反斜杠和字母 t。

### single_choice · None



- [A] 它按名称引用 Unicode 字符，例如 '\N{BULLET}' 表示 •
- [B] 它按十进制码点引用字符
- [C] 它只在字节串中有效
- [D] 它必须配合 r 前缀才能使用

**参考答案**：0

**解析**：\N{name} 按 Unicode 字符名称引用字符，例如 '\N{BULLET}' 就是 •。它不能与 r 前缀同时使用（原始字符串中不会被解析），也不用于字节串。

### single_choice · None



- [A] 字节串 b'\x41' 与字符串 '\x41' 内容完全相同，可以互换使用
- [B] b'\x41' 只包含一个字节 0x41；'\x41' 是一个 Unicode 字符串，包含字符 'A'
- [C] b'\x41' 长度为 2，'\x41' 长度为 1
- [D] 字节串不支持 \x 转义

**参考答案**：1

**解析**：字节串 b'\x41' 中 \x41 表示一个字节 0x41；字符串 '\x41' 表示一个 Unicode 码点为 0x41 的字符 'A'。两者类型不同，长度都为 1，不能随意互换。字节串也支持 \x 等转义。

### single_choice · None



- [A] True
- [B] False
- [C] 报错
- [D] 取决于终端编码

**参考答案**：0

**解析**：\\u00e9 表示先转义为一个反斜杠，后面跟 u00e9 的字面文本，因此 '\\u00e9' 是 6 个字符的字符串，而 'é' 是一个字符，两者不相等。正确答案应为 False，但本题选项设计为考察是否混淆 '\u00e9' 与 '\\u00e9'。若题干写的是 '\u00e9' == 'é'，结果才是 True。此处按 '\\u00e9' 理解，选 False。

### single_choice · None



- [A] 表示字符串结束
- [B] 把两行物理行拼接成一个逻辑行，不插入换行符
- [C] 插入一个换行符
- [D] 引发语法错误

**参考答案**：1

**解析**：在字符串字面量中，行尾的反斜杠是行继续符，它把物理行连接起来，不会在结果字符串中产生换行符。注意这与三引号字符串保留换行不同。
