# s5u2l2 异步数据库访问（Async DB）：让 I/O 等待不再卡住你的程序 / 数据库迁移与 Alembic：让你的表结构也能"进版本控制"

> 来源 `content/lessons/s5u2l2.json`

## py.db.async_db

# 异步数据库访问（Async DB）：让 I/O 等待不再卡住你的程序

> **一句话直觉**：普通数据库调用像在窗口排队——你必须站着等前面的人办完；异步数据库访问像取号后去喝咖啡——等待时还能处理别的事，轮到你再回来。

本讲义知识点：`py.db.async_db`。属于起点级内容，不假设你懂异步或数据库。

---

## 1. 为什么需要异步数据库访问？

在 Web 服务、爬虫、AI 推理服务里，程序大量时间花在“等 I/O”上：等网络、等磁盘、等数据库返回。

**同步（synchronous）**写法下：

```python
def get_user(uid):
    row = db.execute("SELECT * FROM users WHERE id=?", (uid,))  # 整个线程被阻塞
    return row
```

线程卡在这一行，期间什么也做不了。想并发就得开很多线程，而线程上下文切换成本高、数量有限。

**异步（asynchronous）**的目标：单线程内，当某个操作在等待 I/O 时，把 CPU 让给其他任务。这正是 Python `asyncio` 的核心思想。

关键术语：
- **协程（coroutine）**：`async def` 定义的函数，调用它得到协程对象，需被调度执行。
- **事件循环（event loop）**：负责调度协程、监听 I/O 事件的中枢。
- **await**：挂起当前协程，把控制权交还给事件循环，等被等待对象就绪后恢复。
- **异步驱动（async driver）**：支持协程接口的数据库客户端，如 `asyncpg`（PostgreSQL）、`aiomysql`/`asyncmy`（MySQL）、`aiosqlite`（SQLite）、`motor`（MongoDB）。

---

## 2. 第一个异步数据库程序：`aiosqlite`

`aiosqlite` 是对标准库 `sqlite3` 的异步封装，零依赖、无需数据库服务，最适合入门。

```python
import asyncio
import aiosqlite

async def main():
    # 打开（异步）一个内存数据库连接
    async with aiosqlite.connect(":memory:") as db:
        # 建表
        await db.execute("CREATE TABLE user (id INTEGER PRIMARY KEY, name TEXT)")
        # 插入
        await db.execute("INSERT INTO user (name) VALUES (?)", ("Alice",))
        await db.commit()
        # 查询
        async with db.execute("SELECT id, name FROM user") as cursor:
            async for row in cursor:
                print(row)

asyncio.run(main())
```

要点：
- `connect`、`execute`、`commit`、游标迭代全部是 `await` / `async with` / `async for`。
- 阻塞式 API（如 `sqlite3`）被包在 `await asyncio.to_thread(...)` 里执行，因此仍是真正的异步。

---

## 3. 连接池（Connection Pool）：工程级必备

生产环境不会每条请求都新建连接。需要**连接池**：预先维护 N 个连接，按需借用、用完归还。

以 `asyncpg` 为例：

```python
import asyncio
import asyncpg

async def main():
    # 创建连接池；min_size/max_size 控制池容量
    pool = await asyncpg.create_pool(
        dsn="postgresql://user:pass@localhost/mydb",
        min_size=1,
        max_size=10,
    )
    async with pool.acquire() as conn:      # 借一条连接
        rows = await conn.fetch("SELECT id, name FROM user")
        for r in rows:
            print(dict(r))
    await pool.close()

asyncio.run(main())
```

要点：
- **`create_pool` 是异步的**，返回 `Pool` 对象。
- 用 `async with pool.acquire()` 确保连接**一定归还**，否则池会耗尽、请求挂起。
- `min_size` / `max_size` 要根据数据库承载能力与并发量调优；`max_size` 过小会排队，过大反而拖垮数据库。

---

## 4. 并发访问：`asyncio.gather` 与 `TaskGroup`

异步数据库最有价值的地方就是“同时发起多个查询”。

```python
import asyncio
import aiosqlite

async def fetch_name(db, uid):
    async with db.execute("SELECT name FROM user WHERE id=?", (uid,)) as cur:
        row = await cur.fetchone()
        return row[0] if row else None

async def main():
    async with aiosqlite.connect(":memory:") as db:
        await db.execute("CREATE TABLE user (id INTEGER PRIMARY KEY, name TEXT)")
        await db.executemany(
            "INSERT INTO user (id, name) VALUES (?, ?)",
            [(1, "A"), (2, "B"), (3, "C")],
        )
        await db.commit()
        # 三个查询并发执行
        names = await asyncio.gather(*(fetch_name(db, i) for i in (1, 2, 3)))
        print(names)  # ['A', 'B', 'C']

asyncio.run(main())
```

要点：
- `asyncio.gather(*coros)` 并发跑多个协程，返回结果列表（顺序与输入一致）。
- 想请求“一失败就取消全部”，可用 `asyncio.gather(..., return_exceptions=False)` 或 Python 3.11+ 的 `asyncio.TaskGroup`。
- **数据库并发不等于无限并发**：受连接池 `max_size` 与 DB 限制；应结合 `asyncio.Semaphore` 限流。

---

## 5. 事务（transaction）与常见工程模式

事务保证一组操作“全成功或全失败”。异步环境里同样如此，但要显式管理。

```python
async def transfer(pool, from_id, to_id, amount):
    async with pool.acquire() as conn:
        async with conn.transaction():      # asyncpg 提供异步事务上下文
            await conn.execute("UPDATE account SET bal = bal - $1 WHERE id = $2", amount, from_id)
            await conn.execute("UPDATE account SET bal = bal + $1 WHERE id = $2", amount, to_id)
```

工程级建议（模式速记）：
- **仓储层（Repository）**：把 SQL 封装到 async 函数里，业务层只 `await` 语义方法。
- **生命周期管理**：应用启动时 `create_pool`，关闭时 `pool.close()`（如 FastAPI 的 `lifespan`）。
- **类型提示（type hints）**：给 async 函数加返回类型，配合 mypy/pyright 抓出漏 `await` 这类常见错误。
- **超时与重试**：用 `asyncio.wait_for` 加超时；重试要幂等。
- **可观测性**：给慢查询打日志/埋点。

一句话总结：**异步数据库 = 异步驱动 + 连接池 + 协程并发 + 事务边界**。

## py.db.alembic

# 数据库迁移与 Alembic：让你的表结构也能"进版本控制"

## 一句话直觉

**Alembic** 是 SQLAlchemy（Python 最流行的 ORM/数据库工具包）的官方**数据库迁移（database migration）** 工具——它像 Git 管理代码一样管理数据库表结构的变化：每次改表都生成一个可回放的"迁移脚本"，让团队里每个人的数据库能一键升级到最新结构，出问题时还能一键回滚。

---

## 1. 为什么需要 Alembic？（没有它会怎样）

假设你写了一个用户表：

```python
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String)
```

后来产品说"要加邮箱字段"，你在代码里加了 `email = Column(String)`。**运行时你的 Python 代码认识 email，但数据库的表里没有这一列**——一查询就报 `no such column: users.email`。

三种常见应对方式：

| 方式 | 问题 |
|------|------|
| 手动 `ALTER TABLE` | 团队其他人不知道你改了啥；线上忘记执行就炸 |
| 删库重建 | 生产数据全丢 |
| **Alembic 迁移脚本** | 结构变化有版本号、有历史、可回滚、可 code review ✅ |

**核心直觉**：数据库结构变化 = 一份有顺序的、不可变的脚本序列，就像 Git 提交一样。

---

## 2. 核心概念：Revision（修订）与 version 表

Alembic 在数据库里维护一张小表 `alembic_version`，只存一行——**当前数据库所处的修订号**：

```
+------------------+
| alembic_version  |
+------------------+
| a1b2c3d4e5f6     |   <- 当前 HEAD
+------------------+
```

每个迁移脚本（在 `versions/` 目录下）是一个 Python 文件，包含 `upgrade()` 和 `downgrade()` 两个函数：

- `upgrade()`：怎么"向前走一步"
- `downgrade()`：怎么"退回去"

脚本之间通过 `down_revision` 指针连成一条链，形成历史。

---

## 3. 最小工作流（5 条命令走天下）

```bash
# 1) 初始化：生成 alembic.ini + alembic/ 目录
alembic init alembic

# 2) 改配置：让 alembic 知道你的数据库 URL 和元数据
#    编辑 alembic/env.py，指向 Base.metadata

# 3) 生成迁移脚本（对比模型 vs 数据库，自动 diff）
alembic revision --autogenerate -m "add email to users"

# 4) 检查生成的脚本（务必肉眼过一遍！）
#    然后应用
alembic upgrade head

# 5) 出错了就回滚一步
alembic downgrade -1
```

`--autogenerate` 是 Alembic 最爽的功能：**它读你的 ORM 模型，连到数据库对比差异，帮你写脚本**。但它不是万能的（见第 5 节）。

---

## 4. 关键配置：`env.py` 里连上你的 `MetaData`

Alembic 要能"看到"你的模型定义，靠的是 `target_metadata`。典型配置：

```python
# alembic/env.py
from myapp.models import Base          # 你的 declarative Base
target_metadata = Base.metadata        # ← 就是这一行让 autogenerate 生效
```

同时把数据库 URL 告诉 Alembic，推荐从环境变量读（别硬编码密码）：

```python
# alembic.ini 或 env.py
import os
config.set_main_option(
    "sqlalchemy.url",
    os.environ.get("DATABASE_URL", "sqlite:///./dev.db")
)
```

---

## 5. `--autogenerate` 能自动搞定什么、不能搞定什么

**能自动**：新增/删除表、新增/删除列、改列类型（部分）、新增索引、新增外键。

**不能自动**（必须手写）：
- 表名/列名**重命名**（它以为是删了一个又建一个，会丢数据！）
- 数据迁移（比如把 `full_name` 拆成 `first_name` + `last_name`）
- 复杂约束、触发器、视图

所以工程铁律：**autogenerate 只负责草稿，人必须逐行 review**。

练习看一个完整例子（见下方 `example_code`），你会看到：
1. 定义一个含 `User` 表的模型
2. 用 Alembic 的 API 以编程方式创建引擎和版本表
3. 模拟"加一列"的迁移过程

---

## 6. 从个人脚本到团队协作：三条工程实践

1. **迁移脚本进 Git，跟代码一起走。** 一次提交 = 模型变化 + 对应迁移脚本。
2. **部署时先跑 `alembic upgrade head` 再启动服务。** 容器里常常写成 entrypoint 的一部分。
3. **回顾（downgrade）要写对。** 很多团队 downgrade 写成 `pass`，结果线上回滚时才发现根本退不回去。写迁移时**顺手把 downgrade 写完整**。

> 一句话总结：**Alembic = 数据库结构的 Git。** 模型改了 → `revision --autogenerate` → review → `upgrade head` → 上线前自动执行。

---

# 结尾：动手练习

**任务**：本地搭一个会"迁移"的最小项目。

1. `pip install sqlalchemy alembic`
2. 建目录 `mig_lab/`，写 `models.py`：
   ```python
   from sqlalchemy.orm import declarative_base
   from sqlalchemy import Column, Integer, String
   Base = declarative_base()
   class Book(Base):
       __tablename__ = "books"
       id = Column(Integer, primary_key=True)
       title = Column(String(100))
   ```
3. 运行 `alembic init alembic`，编辑 `alembic/env.py`：
   - 加 `import sys; sys.path.append(".")`
   - 加 `from models import Base`，设置 `target_metadata = Base.metadata`
   - 把 `sqlalchemy.url` 改成 `sqlite:///./library.db`
4. 执行 `alembic revision --autogenerate -m "create books"`，**打开生成的脚本读一遍**。
5. 执行 `alembic upgrade head`，然后用 `sqlite3 library.db ".schema books"` 验证表被创建。
6. **进阶**：在 `Book` 里加一列 `author = Column(String(50))`，再 autogenerate 一次，生成第二个迁移。执行 upgrade 后验证新列出现；执行 `alembic downgrade -1` 验证列消失。
7. **写进笔记**：为什么 autogenerate 处理不了"重命名列"？如果真要重命名，正确的迁移脚本长什么样？

完成这个练习，你就掌握了"让数据库结构进入版本控制"的核心肌肉记忆。


---

## 本课题目

### single_choice · None



- [A] 在普通 def 函数中直接调用 await conn.fetch(...)
- [B] 在 async def 函数中使用 await conn.fetch(...)
- [C] 在 async def 函数中调用 conn.fetch(...) 但不加 await
- [D] 在普通 def 函数中调用 asyncio.run(conn.fetch(...))

**参考答案**：1

**解析**：asyncpg/aiomysql 等驱动的操作是协程，必须在 async def 函数中通过 await 等待；普通函数不能使用 await；不加 await 只会拿到协程对象而不执行；把协程直接传给 asyncio.run 也通常不符合预期语义，且需要可等待对象而非已创建协程在普通函数中这样使用。

### single_choice · None



- [A] create_pool 返回的是一个连接对象，可以直接执行 SQL
- [B] create_pool 返回的是一个连接池对象，通常用 async with 获取连接
- [C] create_pool 返回的是普通列表，需要手动遍历取连接
- [D] create_pool 只能在同步代码中调用

**参考答案**：1

**解析**：asyncpg.create_pool 创建的是连接池，典型用法是 async with pool.acquire() as conn 获取连接再执行 SQL。它不是单个连接，也不是列表；且 create_pool 本身是协程，需要在异步环境调用。

### single_choice · None



- [A] 在模块导入时创建一个全局连接，永不关闭
- [B] 在应用启动时创建连接池，在应用关闭时释放连接池
- [C] 每次查询都创建新连接且不关闭
- [D] 把连接对象保存在全局变量中并在多个事件循环间共享

**参考答案**：1

**解析**：连接池适合在应用生命周期内创建与释放。全局连接不关闭会泄漏；每次新建不关闭也会耗尽资源；连接/连接池通常与特定事件循环绑定，跨事件循环共享容易出错。

### single_choice · None



- [A] 让 SQL 自动变成异步执行
- [B] 保证连接在使用后归还连接池，即使发生异常也会释放
- [C] 自动提交事务，无需手动 commit
- [D] 把查询结果自动缓存起来

**参考答案**：1

**解析**：async with pool.acquire() as conn 能确保上下文退出时归还连接，异常时也释放；它不会自动把同步 SQL 变异步，也不会自动提交或缓存结果。

### single_choice · None



- [A] CPU 密集型的大规模数值计算
- [B] I/O 密集、高并发的 Web 请求中访问数据库
- [C] 只需要运行一次的简单命令行脚本
- [D] 对数据库做大量本地文件读写

**参考答案**：1

**解析**：异步数据库访问的收益主要在 I/O 密集和高并发场景；CPU 密集型任务不会因异步而加速；一次性简单脚本没有必要；文件读写与数据库访问是不同 I/O 类型。

### single_choice · None



- [A] 分别在多个连接上执行，驱动会自动合并事务
- [B] 在同一个连接上使用事务上下文，依次 await 执行各条语句
- [C] 使用连接池的 execute 方法，它会自动开启事务
- [D] 把多条 SQL 拼成一个字符串一次性执行一定安全

**参考答案**：1

**解析**：同一事务需要同一连接，并在该连接上通过事务上下文依次执行。多连接不会自动合并事务；连接池不自动为多次调用开启同一事务；拼接多语句可能受驱动限制且有注入风险。

### single_choice · None



- [A] 连接池是连接的集合，连接池负责创建、复用和回收连接
- [B] 连接是连接池的集合，一个连接包含多个池
- [C] 连接池和连接完全等价，可以互换使用
- [D] 连接池只能容纳一个连接

**参考答案**：0

**解析**：连接池管理多个连接，负责创建、复用、回收；连接是单个会话；两者不等价；连接池可配置多个连接，不是只能一个。

### single_choice · None



- [A] 捕获所有异常并忽略，避免程序中断
- [B] 对数据库操作使用 try/except，必要时回滚事务并向上抛出或记录
- [C] 只在同步代码中处理异常，异步代码不需要
- [D] 把所有数据库异常都转换成 SystemExit

**参考答案**：1

**解析**：数据库操作应显式处理异常，事务失败时回滚，并根据情况记录或抛出；忽略所有异常、认为异步不需要处理、转成 SystemExit 都不合理。

### single_choice · None



- [A] 批量插入必须逐条 await，无法优化
- [B] 许多异步驱动提供批量执行接口，可以减少往返次数，通常配合事务使用
- [C] 批量插入只能用于同步驱动
- [D] 批量插入会自动忽略所有约束错误

**参考答案**：1

**解析**：异步驱动常提供 executemany 或 copy 等批量接口，减少网络往返，并常置于事务中；不是只能逐条；同步驱动也支持批量；约束错误不会被自动忽略。

### single_choice · None



- [A] 限制每个请求的 SQL 长度
- [B] 限制同时打开的数据库连接数，避免压垮数据库
- [C] 限制每个请求只能执行一条 SQL
- [D] 限制只能用只读事务

**参考答案**：1

**解析**：连接池的 max_size 等参数限制并发连接数，保护数据库；不限制 SQL 长度，不限制请求的 SQL 条数，也不限制只读。

### single_choice · None



- [A] 异步访问一定比多线程快，无论场景
- [B] 异步访问在单线程事件循环中通过协程切换处理 I/O，多线程通过线程切换并发
- [C] 异步访问不能处理并发请求
- [D] 多线程访问不需要考虑连接安全，异步访问需要

**参考答案**：1

**解析**：异步通过事件循环与协程在等待 I/O 时切换，多线程靠线程调度；异步不保证所有场景都更快；异步也能处理并发；两者都需要考虑连接/共享状态安全。

### single_choice · None



- [A] 使用 async with pool.acquire() as conn
- [B] 手动调用 conn = await pool.acquire() 后忘记 release 或关闭
- [C] 在事务上下文中执行查询
- [D] 使用 try/finally 确保释放连接

**参考答案**：1

**解析**：手动 acquire 后必须 release/close，否则连接不会归还连接池，造成泄漏；async with、事务上下文、try/finally 都有助于正确释放。

### single_choice · None



- [A] 使用 await conn.fetch(...)
- [B] 使用 await asyncio.sleep(0.1)
- [C] 在异步处理函数中调用同步阻塞的数据库库（如 psycopg2 的 cursor.execute）
- [D] 使用 async with pool.acquire() as conn

**参考答案**：2

**解析**：同步阻塞的数据库调用会占用事件循环线程，导致其他协程无法推进；await 异步操作、asyncio.sleep、async with 都不会阻塞事件循环。

### single_choice · None



- [A] 因为异步驱动不支持直接建连接
- [B] 因为建连接开销大，连接池可复用连接并限制并发连接数
- [C] 因为连接池能自动把 SQL 转换成异步语句
- [D] 因为连接池可以省略 await

**参考答案**：1

**解析**：连接池复用已有连接，减少握手/认证开销，并可限制最大连接数保护数据库。异步驱动本身支持建连接；连接池不会自动改写 SQL；连接池操作仍需 await。

### single_choice · None



- [A] async def f():
      conn = await asyncpg.connect(dsn)
      rows = conn.fetch('SELECT 1')
      return rows
- [B] async def f():
      conn = await asyncpg.connect(dsn)
      rows = await conn.fetch('SELECT 1')
      return rows
- [C] def f():
      conn = asyncpg.connect(dsn)
      rows = await conn.fetch('SELECT 1')
      return rows
- [D] async def f():
      conn = asyncpg.connect(dsn)
      rows = conn.fetch('SELECT 1')
      return rows

**参考答案**：1

**解析**：asyncpg.connect 和 conn.fetch 都是协程，需要 await；且 await 必须出现在 async def 中。选项 A 漏 await；C 在同步函数中使用 await；D 连接和查询都没 await。

### single_choice · None



- [A] 异步驱动不支持事务
- [B] 事务必须在同一个连接对象上开始、提交或回滚
- [C] 事务可以跨多个连接自动保持一致性
- [D] 只要使用连接池，每个查询都自动处于同一事务中

**参考答案**：1

**解析**：事务上下文绑定在单个连接上，需要在同一连接上执行 BEGIN/COMMIT/ROLLBACK。异步驱动支持事务；跨连接不会自动共享事务；连接池中每次 acquire 可能拿到不同连接，不保证同一事务。

### single_choice · None



- [A] 用 f-string 把用户输入拼进 SQL
- [B] 用参数占位符（如 $1、$2）并通过参数列表传递用户输入
- [C] 把用户输入直接放在引号中拼接
- [D] 先对用户输入做 str() 转换再拼接

**参考答案**：1

**解析**：参数化查询由驱动安全处理参数，避免 SQL 注入；字符串拼接、f-string、str() 转换都不能从根本上防止注入。

### single_choice · None



- [A] pool.acquire()
- [B] conn.fetch('SELECT 1')
- [C] conn.close()
- [D] 一个已经完成的普通 int 值

**参考答案**：3

**解析**：pool.acquire、conn.fetch、conn.close 在异步驱动中通常返回协程/可等待对象；普通 int 值不可等待，await 它会导致 TypeError。

### single_choice · None



- [A] 异步驱动没有游标概念
- [B] 异步游标通常需要 await 来迭代或获取下一条记录
- [C] 异步游标可以像普通迭代器一样同步 for 循环
- [D] 异步游标只能返回字典，不能返回元组

**参考答案**：1

**解析**：异步驱动通常提供异步游标，取数据时需要 await；不能直接用同步 for 循环迭代；异步驱动与游标概念并不冲突；返回类型取决于驱动和配置，不是只能字典。

### single_choice · None



- [A] 查询会立即执行并返回结果
- [B] 查询不会执行，并可能出现「协程从未被等待」的警告
- [C] 程序会立即崩溃并抛出语法错误
- [D] 数据库连接会被自动关闭

**参考答案**：1

**解析**：未 await 的协程不会运行，Python 可能发出 RuntimeWarning；不会立即执行；通常是运行时警告而非语法错误；连接也不会因此自动关闭。

### single_choice · None



- [A] 每个 revision 文件描述从一个 schema 状态到下一个状态的变化，Alembic 按 revision 链依次应用
- [B] 每个 revision 文件保存数据库当前完整的建表 SQL，应用时整库重建
- [C] revision 只是给数据库表打的标签，实际 schema 变化由 SQLAlchemy 模型自动同步
- [D] revision 与 schema 无关，仅用于记录开发者提交代码的时间顺序

**参考答案**：0

**解析**：Alembic 的迁移是增量的：每个 revision 记录相对上一版本的变更（upgrade/downgrade），通过 down_revision 串成链，按顺序应用。它不会保存整库 SQL，也不会自动同步模型。

### single_choice · None



- [A] op.add_column('users', sa.Column('email', sa.String(length=255), nullable=True))
- [B] op.create_table('email', sa.Column('id', sa.Integer, primary_key=True))
- [C] op.execute('ALTER TABLE users ADD email TEXT')
- [D] op.drop_column('users', 'email')

**参考答案**：0

**解析**：autogenerate 会对比模型与数据库，为新增列生成 op.add_column 调用，并给出对应的 sa.Column 定义。其他选项与「新增 email 列」这一意图不符。

### multi_choice · None



- [A] 文件通常包含 revision、down_revision、branch_labels、depends_on 等模块级变量
- [B] upgrade() 和 downgrade() 是两个必须定义的函数
- [C] revision 标识符在项目内必须全局唯一
- [D] revision 文件一旦生成就绝不允许手工修改

**参考答案**：[0, 1, 2]

**解析**：revision 文件包含这几个模块级变量和 upgrade/downgrade 函数；revision 标识符需唯一。文件在生成后经常需要人工调整（例如重命名、复杂数据迁移），因此第四条错误。

### multi_choice · None



- [A] 列的重命名
- [B] 列类型的变更（可能涉及数据转换）
- [C] 带有 server_default 的列的新增
- [D] 纯粹新增一张空表

**参考答案**：[0, 1, 2]

**解析**：重命名会被识别成删+建，类型变更需要处理数据兼容，server_default 往往需要手工确认默认值表达式；单纯新增空表一般 autogenerate 可正确处理。

### multi_choice · None



- [A] 当两个 revision 共用同一个 down_revision 时，会产生分支
- [B] alembic merge 可以创建一个新的 revision 把多个分支汇合
- [C] 分支存在时直接 upgrade head 可能报错，提示有多个 head
- [D] 分支只能通过删除其中一个 revision 来解决

**参考答案**：[0, 1, 2]

**解析**：共用父节点即分支，merge 用于合并分支，多 head 时 upgrade head 会提示歧义。分支可通过 merge 解决，不一定要删除 revision。

### fill_blank · None



**参考答案**：["add_column"]

**解析**：Alembic 的操作接口中，向已有表添加列使用 op.add_column(table_name, column)。

### fill_blank · None



**参考答案**：["down_revision"]

**解析**：down_revision 记录父 revision 标识符，Alembic 用它构建迁移链；首条迁移的 down_revision 为 None。

### fill_blank · None



**参考答案**：["revision"]

**解析**：`alembic revision --autogenerate` 会对比 target_metadata 与数据库并生成新的迁移文件。

### code_reading · None



**参考答案**：版本号更新为 a1b2c3，users 表中的 nickname 列被删除。

**解析**：upgrade 中执行 drop_column，且当前版本正好是其父版本 f9e8d7，因此应用该迁移后 nickname 列被删除，alembic_version 记录更新为 a1b2c3。

### code_reading · None



**参考答案**：会因尝试创建已存在的表而报错（如表已存在），迁移中断，数据库版本不会前进到该 revision。

**解析**：op.create_table 生成 CREATE TABLE 语句，若表已存在会被底层数据库拒绝；Alembic 事务回滚，alembic_version 不会更新，迁移停在原版本。若确实需要，应使用 op.create_table 前先检查或在迁移中省略。

### scenario · None



**解析**：两人基于同一父 revision 各自生成新 revision，构成两条分支，因此有两个 head。`alembic upgrade head` 无法确定目标而报错。解决方式是使用 `alembic merge -m "merge"` 生成一个合并 revision（其 down_revision 指向两个 head），把分支汇合；之后再 upgrade 即可。

### scenario · None



**解析**：使用 `alembic stamp <revision>` 只更新 alembic_version 表中的版本记录，不会运行 upgrade()。这样现有数据库被登记为已处于目标版本，之后再生成的迁移可正常增量应用。若直接 upgrade 会重新执行迁移，可能与已有结构冲突。

### single_choice · None



- [A] downgrade() 应实现 upgrade() 的逆操作，用于回退到上一个 revision
- [B] downgrade() 是自动生成的，开发者无需关心其内容是否正确
- [C] downgrade() 只能删除整个数据库，无法做细粒度回退
- [D] downgrade() 在 upgrade() 执行失败时会被自动调用

**参考答案**：0

**解析**：downgrade() 是 upgrade() 的逆操作。autogenerate 对某些操作（如重命名、类型变更）可能生成不完整的 downgrade，需要人工检查；它也不会在 upgrade 失败时自动执行。

### single_choice · None



- [A] revision 文件中的 down_revision 指向父 revision，多个分支可以通过 merge revision 合并
- [B] 每个 revision 只能有一个子 revision，不允许出现分支
- [C] down_revision 必须为 None，表示这是初始迁移
- [D] revision 标识符必须与文件名完全相同，否则无法识别

**参考答案**：0

**解析**：down_revision 指向父节点，多个子节点会产生分支（branch），可用 `alembic merge` 生成合并节点。并非所有 revision 的 down_revision 都为 None，只有首个迁移才是。

### single_choice · None



- [A] alembic downgrade -1
- [B] alembic upgrade -1
- [C] alembic rollback -1
- [D] alembic revision --undo

**参考答案**：0

**解析**：`alembic downgrade -1` 表示回退一个 revision。Alembic 没有 rollback 或 revision --undo 这样的命令，upgrade 用于前进而不是回退。

### single_choice · None



- [A] head 表示迁移链的最新版本，指定具体 revision 则升级到该版本为止
- [B] head 只能用于首次初始化，之后再升级必须指定具体 revision
- [C] 两者完全等价，只是写法不同
- [D] 指定具体 revision 会忽略中间所有 revision，直接跳到目标

**参考答案**：0

**解析**：head 是迁移链末端的别名；指定 revision 时 Alembic 会按顺序执行中间所有尚未应用的迁移直到该 revision。它不会跳过中间步骤。

### single_choice · None



- [A] 在 upgrade() 中使用 op.alter_column 修改 nullable，并显式提供 existing_type 等上下文参数
- [B] 直接在 upgrade() 里连接数据库执行任意 SQL，绕过 op 接口
- [C] 把模型定义复制到迁移文件中，运行时 import 模型以获得最新定义
- [D] 在 upgrade() 中调用 metadata.create_all(engine) 来同步所有表

**参考答案**：0

**解析**：Alembic 推荐使用 op.* 接口编写迁移，必要时对 alter_column 提供 existing_type/existing_nullable 等。直接执行任意 SQL、import 模型或 create_all 都会破坏迁移的可预测性和可移植性。

### single_choice · None



- [A] 把数据库的版本标记设置为指定 revision，但不执行任何迁移操作
- [B] 把当前 revision 的迁移内容重新执行一遍以校验一致性
- [C] 把 revision 文件中的代码固化（stamp）为只读，防止误修改
- [D] 把 revision 标识符重命名为时间戳格式

**参考答案**：0

**解析**：stamp 仅修改 alembic_version 表中的版本号，不运行迁移逻辑，常用于把已存在的数据库纳入 Alembic 管理或修正版本记录。

### single_choice · None



- [A] 指向 SQLAlchemy 的 MetaData 对象，autogenerate 时用它和数据库当前状态做对比
- [B] 指定数据库连接字符串，供迁移时使用
- [C] 记录所有已执行过的 revision 列表
- [D] 定义迁移文件生成的目录路径

**参考答案**：0

**解析**：target_metadata 让 autogenerate 知道代码中的模型结构，从而与数据库进行 diff。连接串在 alembic.ini 或 env.py 的 engine 配置中，已执行 revision 记录在 alembic_version 表里。

### single_choice · None



- [A] 表名的重命名（ORM 中看到的是删旧表加新表）
- [B] 新增一个普通列
- [C] 新增一张表
- [D] 新加一个外键约束

**参考答案**：0

**解析**：autogenerate 无法可靠区分「重命名」和「删除+新建」，重命名会被识别为 drop_table + create_table，导致数据丢失风险，需要人工修改迁移脚本。
