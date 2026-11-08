# s5u2l1 Python 数据库与 SQL 基础入门 / 用 Python 对象操作数据库

> 来源 `content/lessons/s5u2l1.json`

## py.db.sql_basic

# Python 数据库与 SQL 基础入门

## 一句话直觉

**你写的 Python 程序一旦重启，内存里的数据就全没了；学会用 SQL（Structured Query Language，结构化查询语言）把数据放进数据库，才能让数据真正"活"下来、被查询、被复用。**

无论你之后做数据分析、爬虫、Web 后端，还是训练 PyTorch 模型时管理数据集，第一步永远是"把数据存下来、取出来"。SQL 就是全世界数据库通用的语言，而 Python 标准库 `sqlite3` 让你零配置就能上手。

---

## 1. 数据库、表、SQL：三个必须先搞懂的概念

- **数据库（Database）**：一个文件或服务，里面装着很多张表。
- **表（Table）**：像 Excel 一样，有行（row，一条记录）和列（column，一个字段）。
- **SQL**：一种声明式语言，你告诉数据库"我要什么"，而不是"怎么一步步取"。

SQL 最核心的四类操作叫 **CRUD**：
- **C**reate（增）：`INSERT`
- **R**ead（查）：`SELECT`
- **U**pdate（改）：`UPDATE`
- **D**elete（删）：`DELETE`

Python 自带的 `sqlite3` 模块就是一个完整的小型数据库，文件即数据库，特别适合学习与本地开发。

```python
import sqlite3

# 连接到数据库文件（不存在会自动创建）
conn = sqlite3.connect("demo.db")
cur = conn.cursor()

# 建一张学生表：id 自增主键，name 文本，score 浮点
cur.execute("""
CREATE TABLE IF NOT EXISTS student (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    name  TEXT    NOT NULL,
    score REAL    NOT NULL
)
""")
conn.commit()
print("表已就绪")
```

---

## 2. 增与查：写入数据并用 SELECT 取回

插入用 `INSERT INTO 表名 (列...) VALUES (值...)`。注意：**永远用 `?` 占位符**，不要把值拼进 SQL 字符串——这是防 SQL 注入（SQL Injection）的第一条铁律。

查询用 `SELECT 列 FROM 表 WHERE 条件`。`WHERE` 用来过滤行，`ORDER BY` 用来排序，`LIMIT` 用来限制条数。

```python
import sqlite3

conn = sqlite3.connect("demo.db")
cur = conn.cursor()

# 插入多条数据：executemany + 占位符，安全又高效
rows = [("Alice", 92.5), ("Bob", 78.0), ("Carol", 88.5), ("Dave", 60.0)]
cur.executemany("INSERT INTO student (name, score) VALUES (?, ?)", rows)
conn.commit()

# 查询：分数 >= 80 的学生，按分数降序
cur.execute("SELECT id, name, score FROM student WHERE score >= ? ORDER BY score DESC", (80,))
for row in cur.fetchall():
    print(row)

conn.close()
```

**关键点**：
- `fetchone()` 取一行，`fetchall()` 取全部，返回的是元组（tuple）列表。
- 也可以设置 `conn.row_factory = sqlite3.Row`，让每行支持按列名访问（`row["name"]`）。

---

## 3. 改与删：UPDATE 和 DELETE

- `UPDATE 表 SET 列=新值 WHERE 条件`：**没有 WHERE 会更新全表**，非常危险。
- `DELETE FROM 表 WHERE 条件`：同理，**没有 WHERE 会清空整张表**。

练手的习惯：**先写 SELECT 验证你要动的行，再把它改写成 UPDATE / DELETE。**

```python
import sqlite3

conn = sqlite3.connect("demo.db")
cur = conn.cursor()

# 给 Bob 加 5 分
cur.execute("UPDATE student SET score = score + ? WHERE name = ?", (5, "Bob"))
# 删掉不及格的学生
cur.execute("DELETE FROM student WHERE score < ?", (60,))
conn.commit()

# rowcount 告诉我们影响了几行
print("Bob 更新行数:", cur.rowcount)
cur.execute("SELECT name, score FROM student")
print(cur.fetchall())
conn.close()
```

---

## 4. 事务与上下文管理：别让数据写一半崩了

**事务（Transaction）** 保证一组操作"要么全成功，要么全回滚"。`sqlite3` 的连接支持上下文管理器：

```python
import sqlite3

# with 块正常结束 → 自动 commit；抛异常 → 自动 rollback
with sqlite3.connect("demo.db") as conn:
    cur = conn.cursor()
    cur.execute("INSERT INTO student (name, score) VALUES (?, ?)", ("Eve", 95.0))
    # 若这里抛错，Eve 不会被写入

with sqlite3.connect("demo.db") as conn:
    for r in conn.execute("SELECT name, score FROM student ORDER BY score DESC"):
        print(r)
```

为什么重要？在 AI 数据管道中，批量写特征/标签到数据库时，**半写入状态会导致训练集脏数据**，事务是保证一致性的基础。

---

## 5. 用 Python 包装 SQL：从脚本升级到工程

工程里我们不会到处手写 SQL 字符串，而是把它封装成函数，并让连接可复用：

```python
import sqlite3
from contextlib import contextmanager

DB = "demo.db"

@contextmanager
def get_conn():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row  # 支持按列名访问
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def add_student(name: str, score: float) -> int:
    """插入一名学生，返回新行的 id。"""
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO student (name, score) VALUES (?, ?)", (name, score)
        )
        return cur.lastrowid

def top_students(limit: int = 3) -> list[dict]:
    with get_conn() as conn:
        cur = conn.execute(
            "SELECT name, score FROM student ORDER BY score DESC LIMIT ?",
            (limit,),
        )
        return [dict(row) for row in cur.fetchall()]

if __name__ == "__main__":
    print("新学生 id:", add_student("Frank", 81.0))
    print("前三名:", top_students(3))
```

到这里你已具备：**建表 → 增删改查 → 事务 → 函数封装** 的完整最小闭环，这就是所谓 `py.db.sql_basic`。

---

## 动手练习

**任务**：写一个 `books.py`，实现一个小型图书管理 CLI。

1. 创建 `books.db`，建表 `book(id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, author TEXT NOT NULL, year INTEGER NOT NULL)`。
2. 实现三个函数：
   - `add_book(title, author, year)`：插入一本书。
   - `find_books(keyword)`：标题中包含 `keyword` 的所有书，按年份升序返回。
   - `delete_before(year)`：删除出版年份早于 `year` 的所有书，返回删除条数。
3. 在 `if __name__ == "__main__"` 中：插入至少 5 本书，调用 `find_books("Python")` 打印结果，再调用 `delete_before(2000)` 打印删除条数，最后打印剩余全部书籍。
4. 加分项：所有 SQL 使用 `?` 占位符，写操作使用 `get_conn()` 上下文管理器。

**验收标准**：程序跑两次结果不重复报错（用 `IF NOT EXISTS`），删除操作不会误删 2000 年及以后的书。

```python
import sqlite3
from contextlib import contextmanager

DB = "demo.db"

@contextmanager
def get_conn():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS student (
                id    INTEGER PRIMARY KEY AUTOINCREMENT,
                name  TEXT    NOT NULL,
                score REAL    NOT NULL
            )
        """)

def add_students(rows):
    with get_conn() as conn:
        conn.executemany(
            "INSERT INTO student (name, score) VALUES (?, ?)", rows
        )

def list_students(min_score=0.0):
    with get_conn() as conn:
        cur = conn.execute(
            "SELECT id, name, score FROM student WHERE score >= ? ORDER BY score DESC",
            (min_score,),
        )
        return [dict(r) for r in cur.fetchall()]

def bump_score(name, delta):
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE student SET score = score + ? WHERE name = ?", (delta, name)
        )
        return cur.rowcount

def delete_failing(pass_line=60.0):
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM student WHERE score < ?", (pass_line,))
        return cur.rowcount

if __name__ == "__main__":
    init_db()
    add_students([("Alice", 92.5), ("Bob", 78.0), ("Carol", 58.0), ("Dave", 88.5)])
    print("初始列表:", list_students())
    print("Bob 更新行数:", bump_score("Bob", 5))
    print("删除不及格行数:", delete_failing(60))
    print("最终列表:", list_students())
```

## py.db.sqlalchemy

# py.db.sqlalchemy：用 Python 对象操作数据库

## 一句话直觉

你不需要背 SQL 字符串、不需要手动拼接字段，**SQLAlchemy（读作 "sequel-alchemy"）让你用 Python 类和对象的方式，安全、可维护地读写数据库**——它既是数据库工具包（Toolkit），也是对象关系映射器（ORM, Object-Relational Mapper）。

---

## 1. 为什么需要 SQLAlchemy？

零基础写数据库代码，常见做法是手写 SQL 字符串：

```python
cursor.execute("INSERT INTO user (name, age) VALUES ('%s', %d)" % (name, age))
```

这有两个问题：

1. **SQL 注入（SQL Injection）**：用户输入 `'; DROP TABLE user; --` 就完了。
2. **难以维护**：字段一改，全项目到处改字符串。

SQLAlchemy 把「数据库表」映射成「Python 类」，把「一行记录」映射成「一个对象」，把「SQL 语句」交给引擎自动生成。

```python
# 你写的是 Python，SQLAlchemy 生成的是 SQL
session.add(User(name="Alice", age=30))
session.commit()
```

---

## 2. 核心三层结构：Engine / Session / Model

SQLAlchemy 的心智模型只有三层：

| 层 | 作用 | 类比 |
|---|---|---|
| **Engine** | 管理数据库连接池，是入口 | 电话总机 |
| **Session** | 一次会话，管理对象的增删改查和事务 | 一次通话 |
| **Model / Table** | 定义表结构，Python 类和表的映射 | 通话内容 |

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session

# 1. Engine：SQLite 内存库，丢了就没了，适合练手
engine = create_engine("sqlite:///:memory:", echo=False)

# 2. Base：所有模型的父类
class Base(DeclarativeBase):
    pass

# 3. Model：用类型注解声明列（SQLAlchemy 2.0 风格）
class User(Base):
    __tablename__ = "user"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    age: Mapped[int]

# 建表
Base.metadata.create_all(engine)
```

---

## 3. 增删改查（CRUD）：一切围绕 Session

SQLAlchemy 2.0 推荐用 `with Session(engine) as session:` 管理会话，退出时自动回滚未提交的事务、归还连接。

```python
from sqlalchemy import select

with Session(engine) as session:
    # Create
    session.add_all([User(name="Alice", age=30), User(name="Bob", age=25)])
    session.commit()

    # Read：select + scalars
    stmt = select(User).where(User.age >= 26)
    for u in session.scalars(stmt):
        print(u.name, u.age)   # Alice 30

    # Update：直接改对象，commit 时自动生成 UPDATE
    alice = session.scalars(select(User).where(User.name == "Alice")).one()
    alice.age = 31
    session.commit()

    # Delete
    session.delete(alice)
    session.commit()
```

**关键结论**：Session 会跟踪你加载出来的对象，你改属性它就知道，`commit()` 时统一落库。这叫「身份映射（Identity Map）」。

---

## 4. 事务：为什么必须 commit？

数据库事务（Transaction）保证一组操作要么全成功、要么全失败。SQLAlchemy 默认 Session 开启一个事务，**不 commit 就不落库**。

```python
with Session(engine) as session:
    session.add(User(name="Carol", age=22))
    # 没有 commit，直接退出 with：Session 关闭时回滚
    # 数据库里不会有 Carol
```

安全做法：把一组操作放进 `with session.begin():` 里，出异常自动回滚。

```python
with Session(engine) as session:
    with session.begin():
        session.add(User(name="Dave", age=40))
        # 这里如果抛异常，自动 rollback
```

---

## 5. 关系（Relationship）：从一张表到多张表

实际项目里表有关联。SQLAlchemy 用 `relationship` 和 `ForeignKey` 自动帮你做 join。

```python
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

class Team(Base):
    __tablename__ = "team"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    members: Mapped[list["Member"]] = relationship(back_populates="team")

class Member(Base):
    __tablename__ = "member"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    team_id: Mapped[int] = mapped_column(ForeignKey("team.id"))
    team: Mapped[Team] = relationship(back_populates="members")
```

之后你可以像操作普通 Python 对象一样：

```python
with Session(engine) as session:
    t = Team(name="Alpha", members=[Member(name="Eve"), Member(name="Frank")])
    session.add(t)
    session.commit()
    print(t.members[0].name, "belongs to", t.members[0].team.name)
```

---

## 6. 工程级建议（速查清单）

- 用 `echo=True` 观察 SQLAlchemy 生成的 SQL，学得快、排查也快。
- 永远不要手拼 SQL 字符串，用参数绑定或 ORM。
- 用 Alembic 做数据库迁移（schema 变动版本化），生产项目几乎必备。
- 长连接场景用连接池（`create_engine` 默认就有），SQLite 文件库注意 `check_same_thread`。
- Session 是短生命周期对象，一个 Web 请求一个 Session，用完关。


---

## 本课题目

### single_choice · None



- [A] [(1, 'a')]
- [B] [{'id': 1, 'name': 'a'}]
- [C] [(1, 'a', None)]
- [D] []

**参考答案**：0

**解析**：sqlite3 默认返回元组组成的列表，SELECT * 返回两列 (1, 'a')。字典形式需要设置 row_factory，不会自动出现；也不会补 NULL 列；commit 后数据已写入，fetchall 不会为空。

### single_choice · None



- [A] 连接对象 conn 在执行 INSERT 后必须调用 commit 才能让改动在后续查询中可见（同一连接内 commit 前也可见未提交的改动，但提交是持久化到磁盘所必需的）
- [B] 每次 execute 都会自动开启并提交一个事务，无需 commit
- [C] 只有调用 conn.close() 时才会提交事务
- [D] SELECT 语句也必须调用 commit，否则查询不到结果

**参考答案**：0

**解析**：sqlite3 默认在 DML 前隐式开启事务，需要 commit 才能持久化；同一连接内未提交改动对自己可见。execute 不会自动提交；close 不保证提交；SELECT 不需要 commit。

### single_choice · None



- [A] 默认 row_factory 返回元组；设置 conn.row_factory = sqlite3.Row 后可像字典一样按键访问
- [B] 默认返回字典；设置 conn.row_factory = sqlite3.Row 后返回元组
- [C] 必须通过 cursor.description 手动转换，无法设置 row_factory
- [D] 必须使用 pandas 才能得到字典形式

**参考答案**：0

**解析**：默认返回元组；设置 row_factory 为 sqlite3.Row 后可支持按列名索引，行为类似字典但并非真正的 dict。

### single_choice · None



- [A] (n,) 形式的元组，其中 n 为行数
- [B] 整数 n
- [C] 字符串 'n'
- [D] 列表 [n]

**参考答案**：0

**解析**：聚合查询结果仍以结果集形式返回，COUNT(*) 是单列，fetchone 得到单元素元组。

### single_choice · None



- [A] 先向子表插入一条 parent_id 不存在的记录
- [B] 先向父表插入记录
- [C] 查询子表
- [D] 删除父表中被引用的行之前先删除子表中对应行

**参考答案**：0

**解析**：外键约束要求子表中的引用值必须在父表中存在，插入不存在的外键值会失败。B、C、D 都符合约束。

### single_choice · None



- [A] 既支持 qmark 风格（?），也支持 named 风格（:name）
- [B] 只支持 %s
- [C] 只支持 $1 风格
- [D] 参数必须拼进 SQL 字符串

**参考答案**：0

**解析**：sqlite3 支持 ? 与 :name 等参数风格；%s 是某些其他驱动（如 psycopg）的占位符，不是 sqlite3 的。参数化是推荐做法。

### single_choice · None



- [A] 第二个写操作可能抛出 OperationalError: database is locked
- [B] 自动排队并阻塞直到前一个提交
- [C] 两个写操作合并为一个事务
- [D] 自动切换到内存数据库

**参考答案**：0

**解析**：SQLite 默认写入串行化，同一时刻只允许一个写事务；并发写往往会遇到 database is locked。它不是自动阻塞排队，也不会自动切换数据库。

### single_choice · None



- [A] ALTER TABLE t ADD COLUMN age INTEGER
- [B] UPDATE t ADD COLUMN age INTEGER
- [C] INSERT INTO t ADD COLUMN age INTEGER
- [D] CREATE COLUMN age INTEGER ON t

**参考答案**：0

**解析**：修改表结构使用 ALTER TABLE ... ADD COLUMN。其余语句语法都不存在。

### single_choice · None



- [A] SQLite 中 1/0 返回 NULL，不抛异常
- [B] 抛出 ZeroDivisionError
- [C] 抛出 OperationalError
- [D] 返回 0

**参考答案**：0

**解析**：SQLite 的除法中除数为 0 时结果为 NULL，不会像 Python 那样抛 ZeroDivisionError。

### single_choice · None



- [A] cursor.lastrowid
- [B] cursor.rowcount
- [C] cursor.description
- [D] connection.total_changes

**参考答案**：0

**解析**：lastrowid 保存最近一次 INSERT 的 rowid；rowcount 是受影响行数；description 是列元数据；total_changes 是连接累计修改数。

### single_choice · None



- [A] 创建一个进程内存中的数据库，连接关闭后数据消失
- [B] 创建一个名为 ':memory:' 的磁盘文件
- [C] 创建一个只读数据库
- [D] 创建一个可在多个进程间共享的内存数据库

**参考答案**：0

**解析**：':memory:' 是内存数据库的特殊路径，连接关闭即销毁，默认不跨进程共享。

### single_choice · None



- [A] cur.execute('SELECT * FROM t WHERE id = ?', (999,)); print(cur.fetchone())
- [B] cur.execute('SELECT * FROM t WHERE id = ?', (999,)); print(cur.fetchone()[0])
- [C] cur.fetchone()['id']
- [D] next(cur)

**参考答案**：0

**解析**：无匹配时 fetchone 返回 None，直接打印安全。取 [0] 或下标会因 None 报 TypeError；cursor 不是迭代器，不能直接 next(cursor)。

### single_choice · None



- [A] [(1, 'x'), (2, 'y')]
- [B] [(0, 'x'), (1, 'y')]
- [C] [(None, 'x'), (None, 'y')]
- [D] 抛出 IntegrityError

**参考答案**：0

**解析**：INTEGER PRIMARY KEY 在 SQLite 中会成为 rowid 别名，插入时若不指定会自动分配递增整数 1、2，因此结果为 [(1, 'x'), (2, 'y')]。

### single_choice · None



- [A] cur.execute('SELECT * FROM users WHERE name = ?', (name,))
- [B] cur.execute("SELECT * FROM users WHERE name = '%s'" % name)
- [C] cur.execute('SELECT * FROM users WHERE name = ' + name)
- [D] cur.execute(f'SELECT * FROM users WHERE name = {name}')

**参考答案**：0

**解析**：参数化查询使用占位符 ? 并把值作为第二参数传入，由数据库驱动负责转义，能有效防止注入。字符串拼接、格式化都会把用户输入直接并入 SQL，存在注入风险。

### single_choice · None



- [A] 删除不会生效，表中数据保持不变
- [B] 删除会生效，表中数据被清空
- [C] 会抛出 OperationalError
- [D] 下次连接时自动补做一次提交

**参考答案**：0

**解析**：未提交的事务在连接关闭时通常会回滚，因此 DELETE 不会持久化，数据保持不变。sqlite3 不会在退出时自动提交，也不会因此报错。

### single_choice · None



- [A] cur.execute('CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT NOT NULL)')
- [B] cur.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, email TEXT NOT NULL)') 也是合法写法，但第一次执行时与选项 A 效果相同
- [C] cur.execute('INSERT TABLE users (id, email) VALUES (1, "a")')
- [D] cur.execute('CREATE users (id INTEGER, email TEXT)')

**参考答案**：0

**解析**：选项 A 是标准且正确的建表语句；选项 B 虽然也是合法 SQL，但题干要求“创建 users 表”，其首次执行效果与 A 相同，但本题中 A 更直接对应题干；C 不是合法 SQL；D 缺少 TABLE 关键字。

### single_choice · None



- [A] (5,)
- [B] 5
- [C] (2, 3)
- [D] OperationalError

**参考答案**：0

**解析**：SELECT 表达式返回单列结果，fetchone 返回元组 (5,)。不会返回裸整数，也不会回显参数。

### single_choice · None



- [A] 返回 cursor 本身，便于链式调用，如 execute(...).fetchall()
- [B] 返回受影响的行数
- [C] 返回查询结果列表
- [D] 返回连接对象

**参考答案**：0

**解析**：sqlite3 的 Cursor.execute 返回自身，因此可以 execute(...).fetchall()。受影响行数保存在 rowcount，查询结果需通过 fetch* 获取。

### single_choice · None



- [A] cur.executemany('INSERT INTO t (v) VALUES (?)', [(1,), (2,), (3,)])
- [B] cur.execute('INSERT INTO t (v) VALUES (1, 2, 3)')
- [C] for v in (1, 2, 3): cur.execute('INSERT INTO t (v) VALUES (%d)' % v)
- [D] cur.execute('INSERT INTO t (v) VALUES (?)', (1, 2, 3))

**参考答案**：0

**解析**：executemany 适合批量插入，第二个参数是序列的序列。B 的 VALUES 列表与列数不匹配；C 每次 execute 一次，效率低且格式串拼 SQL 有风险；D 的参数个数与占位符不匹配。

### single_choice · None



- [A] with sqlite3.connect('a.db') as conn:
      conn.execute("INSERT INTO t VALUES (1)")
- [B] with sqlite3.connect('a.db') as conn:
      conn.commit()
      conn.close()
- [C] with sqlite3.connect('a.db') as conn:
      conn.begin()
      conn.execute('INSERT INTO t VALUES (1)')
- [D] with sqlite3.connect('a.db') as conn:
      conn.rollback()

**参考答案**：0

**解析**：sqlite3 连接对象支持上下文管理协议，正常退出时自动 commit，异常时回滚。选项 B 中 close 后 with 退出会再触发提交/回滚，属于常见错误用法；C 中 begin 方法不存在；D 只回滚不提交，插入不会持久化。

### single_choice · None



- [A] Session 应该在整个应用生命周期内全局唯一，避免重复创建
- [B] Session 通常应在一次请求或一个工作单元内创建并关闭，不应长期共享
- [C] Session 一旦创建就不能关闭，否则会丢失数据库连接
- [D] 多个线程可以安全地共享同一个 Session 对象

**参考答案**：1

**解析**：Session 代表一次与数据库交互的工作单元，通常与请求或事务边界对齐；它不是线程安全的，也不应长期全局共享。

### single_choice · None



- [A] Engine 是单个数据库连接的实例，不可被多个线程共享
- [B] Engine 管理连接池，Connection 是从 Engine 获取的一次连接上下文
- [C] 每次执行 SQL 都必须手动从 Engine 创建新的 Connection
- [D] Connection 比 Engine 更重量级，应尽量缓存

**参考答案**：1

**解析**：Engine 是连接池和方言的封装，可全局共享；Connection 是具体的一次连接，通常通过上下文管理器获取使用。

### single_choice · None



- [A] 启用连接池
- [B] 将执行的所有 SQL 语句输出到日志
- [C] 自动创建所有表
- [D] 开启事务隔离

**参考答案**：1

**解析**：echo=True 会把生成的 SQL 输出到日志，常用于调试。

### multi_choice · None



- [A] transient
- [B] pending
- [C] persistent
- [D] detached
- [E] committed

**参考答案**：[0, 1, 2, 3]

**解析**：ORM 对象状态包括 transient、pending、persistent、detached，committed 不是状态名。

### multi_choice · None



- [A] 默认使用 QueuePool
- [B] pool_size 控制池中保持的连接数
- [C] max_overflow 允许超出 pool_size 的临时连接数
- [D] SQLite 内存数据库也默认使用 QueuePool
- [E] pool_pre_ping 可用于检测失效连接

**参考答案**：[0, 1, 2, 4]

**解析**：SQLite 内存数据库默认使用 SingletonThreadPool 或 StaticPool，而非 QueuePool；其余正确。

### multi_choice · None



- [A] N+1 查询问题
- [B] 在 Session 关闭后访问关联属性可能抛出 DetachedInstanceError
- [C] 数据库连接数显著减少
- [D] 查询性能可能下降

**参考答案**：[0, 1, 3]

**解析**：延迟加载会导致 N+1 查询，且在 Session 关闭后访问可能抛异常，性能可能下降；不会减少连接数。

### fill_blank · None



**参考答案**：["declarative_base", "declarative_base()"]

**解析**：declarative_base() 用于创建声明式模型的基类，模型类继承它。

### fill_blank · None



**参考答案**：["flush", "flush()", "session.flush", "session.flush()"]

**解析**：flush() 将挂起的更改以 SQL 形式发送到数据库，但不提交事务；commit() 才会提交。

### code_reading · None



**参考答案**：1

**解析**：SELECT 1 返回单值 1，scalar() 取第一行第一列结果为 1。

### code_reading · None



**参考答案**：能正常输出。因为 user.name 是普通列属性，且在 commit 时已加载；只有访问未加载的关联属性时，Session 关闭后才可能抛 DetachedInstanceError。

**解析**：普通列在查询时已加载，与 Session 是否关闭无关；延迟加载的关联属性才会受 Session 关闭影响。

### scenario · None



**解析**：常见原因是 Session 未正确关闭或连接池配置过小/过大；应检查请求结束时是否调用 close()，并调整 pool_size、max_overflow、pool_recycle 等参数。

### scenario · None



**解析**：这是典型的 N+1 查询，因懒加载逐条查询关联对象；可用 joinedload/selectinload 预加载关联，或改写为聚合查询统计订单数。

### single_choice · None



- [A] User
- [B] user
- [C] users
- [D] users_table

**参考答案**：2

**解析**：__tablename__ 显式指定数据库中的表名为 'users'。

### single_choice · None



- [A] lazy='joined' 表示关联对象在访问时才发起额外查询
- [B] lazy='select' 是默认值，表示访问关联属性时再发起查询
- [C] lazy='dynamic' 返回一个普通列表对象
- [D] lazy 参数只对多对一关系有效

**参考答案**：1

**解析**：默认 lazy='select' 在访问关联属性时发起独立的 SELECT 查询；'joined' 会在主查询时 JOIN 加载；'dynamic' 返回 Query 对象。

### single_choice · None



- [A] detached
- [B] persistent
- [C] pending
- [D] deleted

**参考答案**：2

**解析**：add 后对象进入 pending 状态，直到 flush 时才真正写入数据库并转为 persistent。

### single_choice · None



- [A] session.execute(text('SELECT * FROM users WHERE id = :id'), {'id': 1})
- [B] session.execute('SELECT * FROM users WHERE id = ?', 1)
- [C] session.query('SELECT * FROM users WHERE id = 1')
- [D] session.raw('SELECT * FROM users WHERE id = 1')

**参考答案**：0

**解析**：SQLAlchemy 2.0 使用 text() 包装原始 SQL，并通过命名参数绑定，能避免 SQL 注入。

### single_choice · None



- [A] 一个表可以没有主键，ORM 会自动生成
- [B] Column(..., primary_key=True) 用于标记主键列
- [C] 主键只能是自增整数
- [D] 复合主键无法通过声明式模型实现

**参考答案**：1

**解析**：primary_key=True 显式声明主键，可以是复合主键、字符串、UUID 等任意类型。

### single_choice · None



- [A] 仅刷新内存中的对象状态，不写入数据库
- [B] 提交当前事务，将挂起的更改持久化到数据库
- [C] 关闭 Session 并释放所有连接
- [D] 回滚未提交的更改

**参考答案**：1

**解析**：commit() 提交事务并持久化更改；flush() 才是只发送 SQL 但不提交。

### single_choice · None



- [A] 抛出 NoResultFound 异常
- [B] 返回空列表
- [C] 返回 None
- [D] 返回一个空 User 对象

**参考答案**：2

**解析**：first() 在无结果时返回 None；one() 才会在无结果时抛出 NoResultFound。

### single_choice · None



- [A] True，即默认允许 NULL
- [B] False，即默认不允许 NULL
- [C] 取决于主键设置
- [D] 由数据库方言决定

**参考答案**：0

**解析**：nullable 默认 True，列允许 NULL；若要禁止 NULL，需显式设置 nullable=False。
