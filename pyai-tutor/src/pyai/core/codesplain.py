"""代码示例逐行讲解（0 token，纯离线规则）。

学习者在课堂里看到的是一段完整示例代码，但没人告诉他「这一句在干嘛、为什么这么写、
语法是什么、哪里有坑」。这里把一段代码拆成「讲解单元」：

  单元 = 一行或一组逻辑上不可分的连续行（注释块、多行函数/类、if-tool，拿不准就一行一块），
  每块给出：原文行号、说明、为什么这么写、涉及的语法点、容易忽略的地方。

**铁律：说明必须能被规则验证。** 说明要么来自代码里**作者自己写的注释**（作者写的，必然正确），
要么来自按语法形状匹配的**教学提示**（只描述这个写法的通用作用，绝不臆断业务意图）。
拿不准的一律说实话（「这行是普通语句」），不猜、不编。

代码注释优先于规则：作者写了 `# 查版本` 就用它当说明，规则只在没注释时兜底。
"""
from __future__ import annotations

import ast
import io
import re
import tokenize

# 语法提示：(正则, 讲什么写法, 大白话说明, 为什么这么写)
# 只收录真实 Python 写法，命中即用；顺序即优先级，复杂的写前面。
_SYNTAX = [
    (r"^\s*from\s+[\w.]+\s+import\b",
     "从模块里导入指定名字",
     "把某个模块里的具体东西拿进来直接用，不用每次写模块名。",
     "只导需要的部分，比 import * 清楚，也不会撞名字。"),
    (r"^\s*import\s+[\w.]+\s+as\s+\w+",
     "导入并起别名",
     "把模块拿进来，但换个短名字用（as 后面那个）。",
     "长模块名起别名能少打字；别名要见名知意，as m 这种过两天就忘了。"),
    (r"^\s*import\s+[\w, ]+$",
     "导入模块",
     "把现成的工具箱整套拿进来，用的时候写「模块.功能」。",
     "标准库和已装的包都靠 import 才能用；不导入就用不了。"),
    (r"^\s*try\s*:",
     "try / except：先试着做，出事再接住",
     "把可能出错的语句放 try 里，出错就跳到 except，程序不会崩。",
     "真实环境里「文件不在、网络断、包没装」都是常态，必须兜底。"),
    (r"^\s*except\b",
     "捕获异常",
     "这里写「出了什么错、然后怎么办」。",
     "只抓具体异常（如 PackageNotFoundError），别用裸 except 一把抓，否则真 bug 会被吞掉。"),
    (r"^\s*finally\s*:",
     "finally：无论成败都执行",
     "收尾工作放这里，比如关闭文件、释放连接。",
     "try 里提前 return 或抛异常时，finally 仍然会跑。"),
    (r"^\s*(async\s+)?def\s+(\w+)\s*\(",
     "定义函数",
     "给一段逻辑起个名字，以后叫名字就能重复用。",
     "参数写在括号里、结果用 return 交回去；函数让重复代码只写一遍。"),
    (r"^\s*class\s+(\w+)",
     "定义类",
     "把「数据 + 操作数据的方法」打包成一个新类型。",
     "类适合描述有状态的东西；纯计算用函数就够了，不必上类。"),
    (r"^\s*for\s+.*\s+in\s+",
     "for 循环：挨个取出",
     "把容器里的元素一个一个拿出来处理。",
     "遍历时别一边循环一边删除同一个列表，会漏元素。"),
    (r"^\s*while\s+",
     "while 循环：条件为真就一直转",
     "每轮检查条件，真就再做一遍。",
     "循环里必须有能让条件变假的语句，否则死循环。"),
    (r"^\s*if\s+.*:\s*$",
     "if 条件判断",
     "成立就执行缩进的那一块。",
     "Python 靠缩进划分语句块，冒号后必须换行加缩进。"),
    (r"^\s*elif\b",
     "elif：否则如果",
     "前面条件不成立时，再检查这一条。",
     "从上往下匹配，命中第一条就跳出整条 if 链，后面的不再判断。"),
    (r"^\s*else\s*:",
     "else：其余情况",
     "上面条件都不成立时走这里。",
     "for/while 后面也可以带 else，表示「没被 break 打断」，这点很多人不知道。"),
    (r"^\s*return\b",
     "返回结果",
     "把结果交给调用处，函数到此结束。",
     "没写 return 的函数返回 None，不是返回最后一行。"),
    (r"^\s*(yield|await)\b",
     "生成器 / 异步等待",
     "暂停在这里，把控制权交给外部。",
     "含 yield 的函数调用时不执行函数体，要迭代才真正跑。"),
    (r"^\s*with\s+",
     "with：进入上下文，退出自动收尾",
     "块结束时自动关闭文件/连接，不用手写 close。",
     "手动 close 在异常时会漏掉，with 能保证释放。"),
    (r"^\s*raise\b",
     "主动抛错",
     "明确告诉调用方「这样用不对」。",
     "自己抛异常比返回 None 让调用方猜要好。"),
    (r"^\s*assert\b",
     "断言：这里是前提条件",
     "条件不成立就说明程序有 bug，直接停。",
     "assert 在 python -O 下会被去掉，别用它做业务校验。"),
    (r"^\s*(lambda|lambda\s)",
     "匿名函数",
     "临时用一下的小函数，不用起名字。",
     "只能写一个表达式，稍微复杂就该用 def。"),
    (r"^\s*print\s*\(",
     "输出到屏幕",
     "把结果打印出来看。",
     "调试用足够；正式输出该用日志（logging），print 关不掉。"),
    (r"\"\"\"|'''",
     "三引号：多行字符串 / 文档字符串",
     "可以跨行写文本，函数第一句会被当成说明文档。",
     "放在函数/模块开头是 docstring，help() 能读到，也是注释以外的正式说明。"),
    (r"%|\.format\(|(?<![\w])f[\"']",
     "字符串格式化",
     "把变量嵌进文本里。",
     "f-string 最直观；拼接字符串在循环里很慢。"),
    (r"^\s*@\w+",
     "装饰器",
     "在不动函数体的前提下，给它加上额外行为。",
     "装饰器自上而下套、执行顺序由内向外，调试时容易看错。"),
    (r"^\s*break\b",
     "break：跳出整个循环",
     "立刻结束这层循环。",
     "只跳出最内层；外层循环还在继续。"),
    (r"^\s*continue\b",
     "continue：跳过本轮",
     "这一轮剩下的不做，直接下一轮。",
     "常和 if 搭配当筛选器，但写多了会难读。"),
    (r"^\s*pass\b",
     "pass：占位，什么也不做",
     "语法要求这里得有一句，但暂时没内容。",
     "空函数体、空类体必须写点东西，pass 就是那个东西。"),
    (r"^\s*del\s+",
     "del：解除引用",
     "把名字和对象断开。",
     "不等于立即释放内存，只是少了一个引用它的人。"),
    (r"^\s*global\s+|^\s*nonlocal\s+",
     "声明外部变量",
     "告诉 Python：我要改外面那一层的变量，别当成新变量。",
     "不声明就赋值会造出一个同名局部变量，外面的值一点没变——很隐蔽的 bug。"),
]

# 容易忽略的细节：(正则, 说明)，越具体的放越前。
_GOTCHA = [
    (r"except\s*:\s*$", "裸 except 会连 Ctrl-C 都吞掉，应写明具体异常类型。"),
    (r"\bexcept\s+Exception\b", "捕获 Exception 范围过宽，会把真 bug 也藏起来；只在最外层兜底时用。"),
    (r"==\s*(True|False|None)\b", "判断 None 用 is None，别用 == None（None 只有一个，是比身份）。"),
    (r"\bdef\s+\w+\s*\(\s*\w+\s*=\s*(\[\]|\{\})", "别用可变对象（列表/字典）当默认参数：它只创建一次，多次调用会共享。"),
    (r"(?<![\w.])open\s*\(", "打开文件务必用 with，或显式 close；异常时未关闭会漏文件句柄。"),
    (r"\brange\s*\(\s*len\s*\(", "range(len(x)) 多半可以换成直接遍历，或 enumerate 拿下标。"),
    (r"\bfor\s+\w+\s+in\s+\w+\s*:\s*$", "循环里如果删/改这个容器，元素会被跳过，应先复制一份遍历。"),
    (r"\btype\([^)]*\)\s*==\s*", "判断类型优先用 isinstance，== 认不出子类。"),
    (r"\bis\s+[\"']", "字符串比较别用 is（比身份），要用 ==（比值）。"),
    (r"\bimport\s+\*", "import * 会污染命名空间，看不出名字从哪来。"),
    (r"\.append\(.*\)\s*\n\s*\.", "链式调用 append 返回 None，不能接着点。"),
    (r"\bglobal\b", "改全局变量会让代码难追踪，优先用返回值或参数传出去。"),
    (r"\bfrom\s+[\w.]+\s+import\s+\*", "星号导入隐藏依赖来源，读代码时不知道某个名字属于谁。"),
    (r"f[\"'][^\"']*\{[^}]*\.[^}]*\}", "f-string 里能写表达式，但别塞复杂逻辑，先算好再插更清楚。"),
    (r"\bassert\b", "assert 是给开发者自查的，用 -O 运行会被移除，不能当输入校验。"),
    (r"\.sort\(\s*\)", "sort() 就地改原列表、返回 None；要新的用 sorted()。"),
    (r"\blist\s*\(\s*sorted\(", "多套了一层 list()，sorted 本身已经返回列表。"),
    (r"\binput\s*\(", "input 拿到的永远是字符串，比数字要先 int()/float()。"),
]

# 单行注释也要写清楚「这行代码在做什么」，不能只复述注释原文。
_COMMENT_KEY = re.compile(r"^\s*#\s*(\d+[.、)]\s*)?")
_FENCE = re.compile(r"^(\s*)```")
_ASSIGN = re.compile(r"^\s*([A-Za-z_][\w]*(?:\s*,\s*[A-Za-z_][\w]*)*)\s*(=|\+=|-=|\*=)(?!=)")
_CALL = re.compile(r"(?<![\w.])([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)\s*\(")
_OPENERS = ("([{", "([{")
_CLOSERS = (")]}", ")]}")

# 结构类关键字：命中时整块缩进体要一起讲，不能只讲父行。
_BLOCK_KW = re.compile(r"^\s*(try|except|finally|else|for|while|if|elif|with|def|class|async\s+def)\b")


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def _is_blank(line: str) -> bool:
    return not line.strip()


def _paren_delta(line: str) -> int:
    """粗略算括号净开合数（忽略字符串里的括号；示例代码够用）。"""
    clean = re.sub(r"(\"\"\"[\s\S]*?\"\"\"|'''[\s\S]*?'''|#[^\n]*)", "", line)
    clean = re.sub(r"\"[^\"\n]*\"|'[^'\n]*'", "", clean)
    return sum(clean.count(c) for c in _OPENERS[0]) - sum(clean.count(c) for c in _CLOSERS[0])


_TRIPLE = re.compile(r"(\"\"\"|''')")


def _is_docstring_start(line: str) -> bool:
    return bool(_TRIPLE.match(line.strip()))


def _triple_end(lines: list[str], start: int) -> int:
    """从第 start 行（三引号开头）找到收尾行，返回收尾行号（找不到就到文末）。"""
    quote = _TRIPLE.match(lines[start].strip()).group(1)
    rest = lines[start].strip()[3:]
    if quote in rest:                      # """一句话""" 写在一行里
        return start
    for j in range(start + 1, len(lines)):
        if quote in lines[j]:
            return j
    return len(lines) - 1


def _split(code: str) -> list[tuple[int, int]]:
    """把代码切成「讲解单元」：返回 [(起始行号, 结束行号)]，行号从 0 开始、含首含尾。"""
    lines = code.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    units: list[tuple[int, int]] = []
    i, n = 0, len(lines)

    while i < n:
        line = lines[i]
        if _is_blank(line):
            i += 1
            continue
        stripped = line.strip()

        # 1) 注释：只吃紧跟的注释行；空行或代码会断开。
        #    原来把整个文件里的连续注释都并进上一块，导致 try 之后两段不相干的小标题被拼在一起。
        if stripped.startswith("#"):
            j = i
            while j + 1 < n and lines[j + 1].strip().startswith("#"):
                j += 1
            units.append((i, j))
            i = j + 1
            continue

        # 2) 三引号字符串：整段算一个单元（原来逐行拆成 5 个「普通语句」）
        if _is_docstring_start(stripped):
            j = _triple_end(lines, i)
            units.append((i, j))
            i = j + 1
            continue

        # 3) try / except / finally：只取这一条链（try 体 + 各 except/finally 体），
        #    后面平级的 `installed = ...`、`for ...:` 属于下一条语句，不能并进来。
        if re.match(r"^\s*try\s*:", line):
            base = _indent(line)
            j = i + 1
            while j < n:
                s = lines[j].strip()
                if s and _indent(lines[j]) < base:
                    break
                # try 链结束：遇到和 try 同缩进的非 except/finally/else 行
                if s and _indent(lines[j]) == base and not re.match(r"^(except|finally|else)\b", s):
                    break
                j += 1
            units.append((i, j - 1 if j > i + 1 else i))
            i = j
            continue

        # 4) 其它结构关键字：父行 + 整个缩进体（定义函数/类、循环、判断、with 等）
        if _BLOCK_KW.match(line):
            base = _indent(line)
            j = i
            while j + 1 < n:
                nxt = lines[j + 1]
                if _is_blank(nxt):
                    k = j + 1
                    while k < n and _is_blank(lines[k]):
                        k += 1
                    if k < n and _indent(lines[k]) > base:
                        j = k - 1
                        continue
                    break
                if _indent(nxt) <= base:
                    break
                j += 1
            units.append((i, j))
            i = j + 1
            continue

        # 5) 跨行括号：凑到括号平衡
        depth = _paren_delta(line)
        j = i
        while depth > 0 and j + 1 < n:
            j += 1
            depth += _paren_delta(lines[j])
        units.append((i, j))
        i = j + 1
    return units


def _comment_text(lines: list[str]) -> str:
    """取这块里作者自己写的注释（去掉编号与 #），拼成一句说明。"""
    parts = []
    for line in lines:
        s = line.strip()
        if s.startswith("#"):
            text = _COMMENT_KEY.sub("", s).strip()
            if text:
                parts.append(text)
    if not parts:
        return ""
    joined = "；".join(parts)
    return joined if joined.endswith(("。", "！", "？", ".", "!", "?")) else joined + "。"


def _syntax_of(code_lines: list[str]) -> tuple[str, str, str]:
    """按写法匹配语法提示，返回 (讲什么, 说明, 为什么)。命中不了就返回通用描述。"""
    head = "\n".join(code_lines)
    first = code_lines[0] if code_lines else ""
    for pattern, name, what, why in _SYNTAX:
        if re.search(pattern, first, re.M) or re.search(pattern, head, re.M):
            return name, what, why
    # 赋值：说明它在「记下一个值」
    m = _ASSIGN.match(first)
    if m:
        name = m.group(1).strip()
        if m.group(2) == "=":
            return ("给变量赋值",
                    f"把右边的结果存进名字 `{name}`，以后用 `{name}` 就能取到它。",
                    f"赋值只是贴标签，不复制内容；两个名字指向同一对象时改一个会影响另一个。"
                    + (f"另外这里右边是多行表达式，括号没闭合时换行才合法。" if "\n" in first or first.rstrip().endswith(("(", "[", "{")) else ""))
        return ("就地累加/更新",
                f"把右边的结果和 `{name}` 现有值算完再存回 `{name}`。",
                "可变对象用 += 是就地修改，会影响所有指向它的名字。")
    # 调函数
    m = _CALL.search(first)
    if m:
        fn = m.group(1)
        return ("调用函数",
                f"调用 `{fn}(...)`，把参数传进去，拿它的返回值（没有返回值就是 None）。",
                "Python 里函数是一等对象，`fn(...)` 里的参数按位置或名字对应形参。")
    # 表达式
    if re.search(r"[+\-*/%]", first):
        return ("表达式求值", "算出一个结果，本行只是算，没存也没输出。", "运算符有优先级，不确定就加括号。")
    return ("普通语句", "这一行是当前上下文里的一句普通代码。", "读的时候重点看它前后的变量从哪来、到哪去。")


def _gotchas(code_lines: list[str]) -> list[str]:
    joined = "\n".join(code_lines)
    found: list[str] = []
    for pattern, text in _GOTCHA:
        if text in found:
            continue
        if re.search(pattern, joined, re.M):
            found.append(text)
    return found[:3]


def _explain_lines(code_lines: list[str]) -> str:
    """没有注释时，按写法生成逐行说明（只描述这一行自己做了什么）。"""
    for raw in code_lines:
        s = raw.strip()
        if not s or s.startswith("#") or s.startswith(("\"\"\"", "'''")):
            continue
        m = re.match(r"^import\s+([\w.]+)(?:\s+as\s+(\w+))?$", s)
        if m:
            alias = f"，并改名为 `{m.group(2)}`" if m.group(2) else ""
            return f"导入模块 `{m.group(1)}`{alias}，之后就能用它的功能。"
        m = re.match(r"^from\s+([\w.]+)\s+import\s+(.+)$", s)
        if m:
            return f"从模块 `{m.group(1)}` 里取出 `{m.group(2).strip()}` 直接使用。"
        m = re.match(r"^(?:async\s+)?def\s+(\w+)\s*\(([^)]*)\)", s)
        if m:
            args = m.group(2).strip()
            return (f"定义函数 `{m.group(1)}`，参数是 `{args}`；下面缩进的部分是它的功能。"
                    if args else f"定义函数 `{m.group(1)}`，它不接收参数；下面缩进的部分是它的功能。")
        m = re.match(r"^class\s+(\w+)", s)
        if m:
            return f"定义类 `{m.group(1)}`，下面缩进的部分是它的属性和方法。"
        m = re.match(r"^if\s+(.+):$", s)
        if m:
            cond = m.group(1).strip()
            if "__name__" in cond:
                return "只有「直接运行这个文件」时才执行下面的块；被别人 import 时不执行。"
            return f"检查条件 `{cond[:48]}`，成立才执行下面缩进的部分。"
        m = re.match(r"^for\s+(.+?)\s+in\s+(.+):$", s)
        if m:
            return f"把 `{m.group(2).strip()[:36]}` 里的元素逐个取给 `{m.group(1).strip()}`，每取一个跑一遍循环体。"
        m = _CALL.search(s)
        if m and not _ASSIGN.match(raw):
            return f"调用 `{m.group(1)}`，把结果交给调用处。"
        m = _ASSIGN.match(raw)
        if m:
            # 从整块原文取右侧：跨行赋值 installed = sorted(\n ...\n) 才不会只剩 "sorted("
            joined = " ".join("\n".join(code_lines).split())
            pos = joined.find(m.group(2))
            after = joined[pos + len(m.group(2)):].strip() if pos >= 0 else ""
            # 多行表达式要够长才看得出在干什么（sorted(...) 这类循环体常在第 2 行）
            limit = 90 if len(code_lines) > 1 else 44
            return f"算出右边的值（`{after[:limit]}{'…' if len(after) > limit else ''}`），存进 `{m.group(1).strip()}`。"
        return ""
    return ""


def _docstring_text(code_text: str) -> str:
    """三引号块的内容本身往往就是作者写的说明，直接拿去当「这段在讲什么」。

    也用于整个函数：有 docstring 就用它，没有再去掉 def 行看首行。
    """
    try:
        node = ast.parse(code_text)
    except SyntaxError:
        return ""
    raw = ""
    if (node.body and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)):
        raw = node.body[0].value.value
    elif node.body and isinstance(node.body[0], (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        fn = node.body[0]
        doc = ast.get_docstring(fn)
        if doc:
            raw = doc
    if not raw:
        raw = code_text.strip().strip("\"'")
    lines = [" ".join(ln.split()) for ln in raw.splitlines()]
    lines = [ln for ln in lines if ln]
    if not lines:
        return ""
    # 多行说明取前两句，够说明「这段在讲什么」，又不至于太长。
    joined = " ".join(lines)
    m = re.match(r"(.{6,120}?[。：:])", joined)
    return (m.group(1) if m else joined[:120])


def _meaning(block: list[str], code_text: str) -> str:
    """这一段的意思：三引号/函数 docstring 取原文；有注释用注释；否则按写法逐行说明。"""
    if _is_docstring_start(block[0].strip()) or _BLOCK_KW.match(block[0] or ""):
        text = _docstring_text(code_text)
        if text and not text.startswith(block[0].strip()[:8]):
            return text
    comment = _comment_text(block)
    if comment:
        return comment
    return _explain_lines(block)


def explain(code: str) -> list[dict] | None:
    """把一段代码拆成讲解单元。空代码返回 None。"""
    code = (code or "").replace("\r\n", "\n").replace("\r", "\n")
    if not code.strip():
        return None
    lines = code.split("\n")
    out: list[dict] = []
    is_comment_run: list[bool] = []
    for idx, (a, b) in enumerate(_split(code)):
        block = lines[a:b + 1]
        while block and _is_blank(block[-1]):
            block.pop()
        if not block:
            continue
        code_text = "\n".join(block)
        syntax, what, why = _syntax_of(block)
        meaning = _meaning(block, code_text)
        # 注释块：说明取注释原文，语法标注为「注释」，不再硬套上一句的语法名。
        if block[0].strip().startswith("#"):
            syntax, what, why = "注释", "写给人看的说明，Python 执行时完全跳过。", ""
        if _is_docstring_start(block[0].strip()):
            syntax, what, why = (
                "三引号：多行字符串 / 文档字符串",
                "可以跨行写文本；放在文件或函数开头时，它就是正式说明（docstring）。",
                "docstring 能被 help() 读到，比普通注释更「正式」；它不是注释，运行时会生成字符串对象。",
            )
        out.append({
            "index": idx + 1,
            "line_start": a + 1,
            "line_end": a + len(block),
            "code": code_text,
            "meaning": meaning or what,
            "why": why,
            "syntax": f"{syntax}：{what}",
            "gotchas": _gotchas(block),
        })

    if not out:
        return None
    out[0]["overview"] = _summary(code, out)
    return out


def _summary(code: str, units: list[dict]) -> str:
    """整体这段代码在做什么：按出现顺序把各单元的语法名连起来，再点出输入输出。"""
    kinds: list[str] = []
    for u in units:
        k = u["syntax"].split("：")[0].strip()
        if k not in kinds:
            kinds.append(k)
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return "这段代码按「" + " → ".join(kinds) + "」的顺序执行。"
    imports = [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
    prints = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
              and isinstance(n.func, ast.Name) and n.func.id == "print"]
    funcs = [n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]

    bits = []
    if imports:
        names = []
        for n in imports:
            if isinstance(n, ast.ImportFrom) and n.module:
                names.append(n.module)
            names += [a.name for a in n.names]
        seen = list(dict.fromkeys(names))[:4]
        bits.append("先导入 " + "、".join(f"`{x}`" for x in seen))
    if classes:
        bits.append("定义类 " + "、".join(f"`{c}`" for c in classes[:3]))
    if funcs:
        bits.append("定义函数 " + "、".join(f"`{f}`" for f in funcs[:3]))
    if prints:
        bits.append(f"打印 {len(prints)} 处结果")
    tail = "整体按「" + " → ".join(kinds) + "」的顺序执行"
    head = "，".join(bits)
    return (head + "；" + tail + "。") if head else (tail + "。")


def syntax_notes(code: str) -> list[str]:
    """这段代码涉及的全部语法点（去重），给「语法速查」用。"""
    units = explain(code) or []
    seen: list[str] = []
    for u in units:
        k = u["syntax"].split("：")[0].strip()
        if k not in seen:
            seen.append(k)
    return seen


def compile_check(code: str) -> str | None:
    """语法自检：能编译返回 None，否则返回错误说明（用于告诉学习者示例有误）。"""
    try:
        compile(code, "<example>", "exec")
    except SyntaxError as exc:
        return f"第 {exc.lineno} 行：{exc.msg}"
    except (ValueError, TypeError) as exc:      # 空源码 / 含 NUL 之类
        return str(exc)
    return None


if __name__ == "__main__":  # pragma: no cover - 手工试跑
    import json

    sample = 'from importlib import metadata\n\n# 1) 查询某个包是否已安装\ntry:\n    dist = metadata.distribution("pip")\n    print(dist.version)\nexcept metadata.PackageNotFoundError:\n    print("未找到")\n'
    print(json.dumps(explain(sample), ensure_ascii=False, indent=2))
