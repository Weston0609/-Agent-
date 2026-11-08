# s5u2l4 PostgreSQL 索引实战：从零到工程化 / Python 数据库事务隔离级别（Transaction Isolation Level）40 分钟讲义

> 来源 `content/lessons/s5u2l4.json`

## py.db.postgres_index

# PostgreSQL 索引实战：从零到工程化

> **一句话直觉**：索引（Index）就像书的目录——没有它，数据库只能逐页翻整本书（全表扫描），有了它就能几毫秒跳到你要的那一页。

本讲聚焦 Python 通过 `psycopg` 操作 PostgreSQL 时，如何正确地创建、分析和利用索引。前置知识为零，但目标是让你能像工程师一样思考"什么时候该建索引、建什么索引、怎么验证它生效了"。

---

## 1. 为什么需要索引：一张表的"翻页"成本

PostgreSQL（下文简称 PG）在没有索引时执行 `WHERE id = 100` 会做 **全表扫描（Sequential Scan，顺序扫描）**：把每一行都读出来比较。表越大越慢，1000 万行可能要几秒。

索引是一种额外的数据结构（PG 默认是 **B-tree**），让你用接近 `O(log n)` 的代价定位到目标行。

先建一个测试环境（本地需要已安装 PostgreSQL，并运行在默认端口）：

```python
import psycopg  # pip install "psycopg[binary]"

# 连接本地数据库（请替换为你自己的账号密码）
conn = psycopg.connect("dbname=postgres user=postgres password=postgres host=localhost")
conn.autocommit = True
cur = conn.cursor()

# 造一张百万行的用户表
cur.execute("DROP TABLE IF EXISTS users")
cur.execute("""
CREATE TABLE users (
    id      BIGSERIAL PRIMARY KEY,
    email   TEXT NOT NULL,
    age     INT  NOT NULL,
    city    TEXT NOT NULL
)
""")
cur.execute("""
INSERT INTO users (email, age, city)
SELECT 'user' || g || '@x.com',
       (random()*80)::int,
       (ARRAY['bj','sh','gz','sz'])[1 + (random()*3)::int]
FROM generate_series(1, 1_000_000) AS g
""")
print("rows:", cur.execute("SELECT count(*) FROM users").fetchone()[0])
```

**关键结论**：没有索引的等值查询必须读整张表。

---

## 2. 用 `EXPLAIN ANALYZE` 看见"代价"

学会观察执行计划（Execution Plan），是使用索引的第一步。`EXPLAIN ANALYZE` 会真实执行 SQL 并返回每步耗时。

```python
def explain(sql):
    cur.execute("EXPLAIN ANALYZE " + sql)
    for (line,) in cur.fetchall():
        print(line)

explain("SELECT * FROM users WHERE email = 'user999999@x.com'")
# 预期看到：Seq Scan on users  (cost=0.00..19457.00 rows=1 width=..)
#           Planning Time: ...   Execution Time: ~80-150 ms
```

**关键结论**：看三个词——`Seq Scan`（全表扫描，通常要优化）、`Index Scan`/`Index Only Scan`（走索引，好）、`Bitmap Heap Scan`（位图扫描，中等）。`Execution Time` 是真实耗时。

---

## 3. 创建索引：`CREATE INDEX` 与 `CREATE INDEX CONCURRENTLY`

```python
# 普通建索引：会短暂锁表（写阻塞），适合开发/小表
cur.execute("CREATE INDEX idx_users_email ON users (email)")

# 生产环境：用 CONCURRENTLY 避免长时间锁写
# cur.execute("CREATE INDEX CONCURRENTLY idx_users_email ON users (email)")

explain("SELECT * FROM users WHERE email = 'user999999@x.com'")
# 预期看到：Index Scan using idx_users_email on users
#           Execution Time: < 1 ms
```

**关键结论**：
- 默认索引名为 `idx_<表>_<列>`，工程上强烈建议显式命名便于管理。
- 生产库大表建索引必须加 `CONCURRENTLY`（不能放在事务里），否则会阻塞写入。
- PG 会**自动**在主键（PRIMARY KEY）和唯一约束（UNIQUE）列上建索引——不要重复建。

---

## 4. 复合索引与"最左前缀"原则

当查询条件是多列时（例如"按城市找某个年龄区间"），复合索引（Composite Index）经常比单列索引更高效。

```python
cur.execute("CREATE INDEX idx_users_city_age ON users (city, age)")

# ✅ 能用到索引：条件包含最左列 city
explain("SELECT * FROM users WHERE city='bj' AND age=30")

# ✅ 也能用到：只用 city（最左前缀可用）
explain("SELECT * FROM users WHERE city='bj'")

# ❌ 用不到 idx_users_city_age：跳过了最左列 city
explain("SELECT * FROM users WHERE age=30")
```

**关键结论（最左前缀，Leftmost Prefix）**：复合索引 `(a, b, c)` 等价于在 `a`、`(a,b)`、`(a,b,c)` 上都有索引，但不覆盖 `(b)`、`(b,c)`。

工程写法建议：**等值条件列在前，范围条件列在后**。

---

## 5. 覆盖索引（Covering Index）与 `INCLUDE`

如果查询的所有列都能从索引本身拿到，PG 就能做 `Index Only Scan`，连回表（访问堆表）都省了。

```python
# 让索引直接"包住"要查的列
cur.execute("CREATE INDEX idx_users_email_inc ON users (email) INCLUDE (id)")

explain("SELECT id FROM users WHERE email = 'user999999@x.com'")
# 预期看到：Index Only Scan using idx_users_email_inc on users
```

**关键结论**：`INCLUDE` 里的列只用于返回，不参与排序/查找，不会撑大 B-tree 的排序键。这是"用索引替代读表"的最有效手段之一。

---

## 6. 维护与清理：索引不是建了就完事

- 频繁更新的表会产生**索引膨胀（Index Bloat）**，需要 `REINDEX` 或 `VACUUM`。
- 长期不用的索引会拖慢写性能，应定期排查并删除。

```python
# 查看某表上所有索引的使用次数（需要先访问过表）
cur.execute("""
SELECT indexrelname, idx_scan, idx_tup_read
FROM pg_stat_user_indexes
WHERE relname = 'users'
""")
for row in cur.fetchall():
    print(row)

# 删除不再需要的索引（生产用 DROP INDEX CONCURRENTLY）
# cur.execute("DROP INDEX CONCURRENTLY idx_users_email_inc")
```

**关键结论**：`idx_scan = 0` 且运行时间足够长的索引，基本可以删除。

---

## 动手练习

**任务**：在本机 PG 上完成一次"索引优化实验"。

1. 用第 1 节代码建一张 `orders` 表，包含列：`id BIGSERIAL PK`、`user_id BIGINT`、`status TEXT`、`created_at TIMESTAMPTZ`、`amount NUMERIC(10,2)`，插入 **200 万行**随机数据（`generate_series` 即可）。
2. 写一条查询：`SELECT id, amount FROM orders WHERE user_id = ??? AND status = 'paid' ORDER BY created_at DESC LIMIT 10;`，用 `EXPLAIN ANALYZE` 记录耗时。
3. 思考并回答：应该建什么复合索引？写出来后再次 `EXPLAIN ANALYZE`，对比是否出现 `Index Scan` 且耗时下降一个数量级以上。
4. 尝试给这个索引加上 `INCLUDE` 让查询变成 `Index Only Scan`，并说明为什么 `ORDER BY created_at DESC` 也能被索引加速。
5. 最后用 `pg_stat_user_indexes` 验证你的索引确实被使用了（`idx_scan > 0`）。

**验收标准**：两条 `EXPLAIN ANALYZE` 的输出对比截图 + 200 字以内的解释。

## py.db.tx_isolation

# Python 数据库事务隔离级别（Transaction Isolation Level）40 分钟讲义

## 一句话直觉

当多个程序同时读写同一张数据库表时，**事务隔离级别**决定了“别人还没提交的修改，你能不能看见”，它直接决定你的数据会不会出现脏读、不可重复读、幻读。

---

## 1. 为什么需要事务隔离级别

### 1.1 并发写同一份数据会发生什么

假设有两个并发事务 T1、T2 同时操作账户表：

```text
初始：账户 A = 100 元

T1: 读取 A = 100
T2: 读取 A = 100
T1: A = A - 30，写入 70，提交
T2: A = A - 50，写入 50，提交

最终 A = 50，而不是 20 —— 丢失了 T1 的更新
```

这种问题叫**丢失更新（Lost Update）**。事务隔离级别就是为了在“并发性能”和“数据一致性”之间做取舍。

### 1.2 三个典型并发异常

| 异常 | 含义 |
|------|------|
| 脏读（Dirty Read） | 读到了别的事务尚未提交的数据 |
| 不可重复读（Non-Repeatable Read） | 同一事务内两次读同一行，结果不同 |
| 幻读（Phantom Read） | 同一事务内两次范围查询，返回的行数不同 |

---

## 2. SQL 标准定义的四种隔离级别

从低到高：

| 隔离级别 | 脏读 | 不可重复读 | 幻读 |
|----------|------|------------|------|
| READ UNCOMMITTED（读未提交） | 可能 | 可能 | 可能 |
| READ COMMITTED（读已提交） | 不可能 | 可能 | 可能 |
| REPEATABLE READ（可重复读） | 不可能 | 不可能 | 可能（MySQL 通过 MVCC 基本避免） |
| SERIALIZABLE（可串行化） | 不可能 | 不可能 | 不可能 |

隔离级别越高，一致性越强，但并发吞吐越低。

---

## 3. Python 里如何操作隔离级别

Python 标准库 `sqlite3`（SQLite Database）内建支持事务，可以通过 `isolation_level` 控制。

### 3.1 SQLite 的隔离级别

SQLite 支持的隔离级别实际上只有：

- `None`：自动提交（Autocommit）
- `"DEFERRED"`：默认，事务开始时不上锁，第一次读写才加锁
- `"IMMEDIATE"`：事务开始立即加写锁
- `"EXCLUSIVE"`：事务开始立即加排他锁

### 3.2 查看和设置隔离级别

```python
import sqlite3

# 默认是 DEFERRED
conn = sqlite3.connect("demo.db")
print(conn.isolation_level)   # 输出: ''（Python 3.12+ 默认 DEFERRED 表现为 ''）

# 显式设置为 IMMEDIATE
conn.isolation_level = "IMMEDIATE"
conn.close()
```

### 3.3 对 PostgreSQL / MySQL 使用隔离级别

以 `psycopg`（PostgreSQL 驱动）为例：

```python
import psycopg

conn = psycopg.connect("dbname=test user=postgres")
conn.set_isolation_level(psycopg.extensions.ISOLATION_LEVEL_SERIALIZABLE)
```

MySQL 的 `pymysql` 可以通过 SQL 语句设置：

```sql
SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED;
```

---

## 4. 用 Python 观察隔离级别效果

### 4.1 演示“不可重复读”

下面用两个 SQLite 连接模拟：T1 在同一事务中两次读取同一行，T2 在中间修改并提交。

```python
import sqlite3

DB = ":memory:"
# 为了让两个连接共享同一个内存数据库，需要用共享缓存
uri = "file:memdb1?mode=memory&cache=shared"

setup = sqlite3.connect(uri, uri=True, isolation_level=None)
setup.execute("CREATE TABLE account (id INTEGER PRIMARY KEY, balance INTEGER)")
setup.execute("INSERT INTO account VALUES (1, 100)")
setup.close()

# T1
conn1 = sqlite3.connect(uri, uri=True, isolation_level="DEFERRED")
conn1.execute("BEGIN")           # 开启事务
r1 = conn1.execute("SELECT balance FROM account WHERE id=1").fetchone()
print("T1 第一次读：", r1)

# T2 修改并提交
conn2 = sqlite3.connect(uri, uri=True, isolation_level=None)
conn2.execute("UPDATE account SET balance = 200 WHERE id = 1")
conn2.commit()
conn2.close()

# T1 第二次读
r2 = conn1.execute("SELECT balance FROM account WHERE id=1").fetchone()
print("T1 第二次读：", r2)
conn1.commit()
conn1.close()
```

在 SQLite 的 `DEFERRED` 下，因为 T1 已经 `BEGIN`，T2 的写会被阻塞或报 `database is locked`。实际能否复现“不可重复读”取决于引擎的锁与 MVCC 实现。

### 4.2 观察不同隔离级别下的行为差异

在 PostgreSQL 上把同一个脚本用 `READ COMMITTED` 和 `REPEATABLE READ` 各跑一遍，会看到：

- `READ COMMITTED`：两次读结果不同（发生不可重复读）
- `REPEATABLE READ`：两次读结果相同（快照隔离）

这就是隔离级别的实际价值。

---

## 5. 工程级选择建议

- 默认多数数据库是 `READ COMMITTED`，绝大多数 Web 业务够用。
- 涉及资金、库存扣减，考虑使用 `REPEATABLE READ` 或显式加锁 `SELECT ... FOR UPDATE`。
- 金融对账、批处理需要强一致，可使用 `SERIALIZABLE`，但要准备重试逻辑。
- 隔离级别不是万能药，业务层要配合乐观锁（版本号）或悲观锁（`FOR UPDATE`）。

---

## 动手练习

**任务：用 SQLite 观察隔离级别的行为**

1. 创建一个 SQLite 文件数据库 `lab.db`，建立 `account(id, balance)`，插入 `(1, 1000)`。
2. 写一个 Python 脚本，用两个 `sqlite3.Connection`：
   - 连接 A 设置 `isolation_level='DEFERRED'`，`BEGIN` 后读一次 `balance`。
   - 连接 B 用 `isolation_level=None`，执行 `UPDATE` 并 `commit`。
   - 连接 A 再读一次。
3. 打印两次读的结果，观察并解释它们是否相同。
4. 把连接 A 改成 `isolation_level=None` 再跑一次，比较差异。

**进阶**：如果你本地有 PostgreSQL 或 MySQL，把上面的实验换成它们，分别用 `READ COMMITTED` 和 `REPEATABLE READ` 各跑一次，记录结果差异。


---

## 本课题目

### single_choice · None



- [A] CREATE INDEX idx_name ON table_name (column_name);
- [B] CREATE TABLE table_name (column_name INDEX);
- [C] ALTER TABLE table_name ADD column_name INDEX;
- [D] SELECT INDEX ON table_name (column_name);

**参考答案**：0

**解析**：PostgreSQL 使用 CREATE INDEX 语句为表的列创建索引；其他写法均不是合法 SQL 语法。

### single_choice · None



- [A] B-tree 索引只能用于等值查询，不能用于范围查询
- [B] B-tree 索引适用于等值查询和范围查询，且支持排序
- [C] B-tree 索引不能用于文本类型的列
- [D] B-tree 索引必须建立在主键列上

**参考答案**：1

**解析**：B-tree 是 PostgreSQL 默认索引类型，支持等值、范围和排序操作。

### single_choice · None



- [A] B-tree 索引不存储 NULL 值，因此 IS NULL 查询无法使用索引
- [B] B-tree 索引存储 NULL 值，IS NULL 查询可以使用索引
- [C] 只有唯一索引才存储 NULL 值
- [D] 索引对 NULL 值的处理与数据类型无关

**参考答案**：1

**解析**：PostgreSQL 的 B-tree 索引会存储 NULL 值，因此 IS NULL 条件可以利用索引。

### single_choice · None



- [A] 表达式索引只能用于简单的列引用
- [B] 表达式索引允许对函数或表达式的结果建立索引，查询时必须使用相同的表达式才能利用该索引
- [C] 表达式索引不能用于 WHERE 子句
- [D] 表达式索引会自动优化查询，无需匹配表达式

**参考答案**：1

**解析**：表达式索引对函数或表达式的结果建立索引，查询条件必须匹配该表达式才能使用索引。

### single_choice · None



- [A] DROP INDEX idx_name;
- [B] DELETE INDEX idx_name;
- [C] REMOVE INDEX idx_name;
- [D] ALTER TABLE table_name DROP INDEX idx_name;

**参考答案**：0

**解析**：PostgreSQL 使用 DROP INDEX 删除索引；ALTER TABLE ... DROP INDEX 不是标准语法。

### single_choice · None



- [A] B-tree
- [B] Hash
- [C] GiST
- [D] GIN

**参考答案**：1

**解析**：Hash 索引不支持唯一性约束；B-tree、GiST 和 GIN 可以支持唯一性（GIN 通常用于非唯一场景，但技术上可创建唯一索引，实际中较少用）。

### single_choice · None



- [A] CREATE INDEX ON users (age, city);
- [B] CREATE INDEX ON users (city, age);
- [C] CREATE INDEX ON users (age);
- [D] CREATE INDEX ON users (city);

**参考答案**：1

**解析**：等值条件 city 应放在复合索引的第一列，范围条件 age 放在第二列，这样能更有效地利用索引。

### single_choice · None



- [A] 索引膨胀是指索引文件占用空间过大，通常由频繁更新和删除导致
- [B] 索引膨胀只能通过删除并重建索引来解决
- [C] 索引膨胀不会影响查询性能
- [D] 索引膨胀只发生在 B-tree 索引上

**参考答案**：0

**解析**：索引膨胀由频繁更新和删除产生死元组导致，可通过 REINDEX 或 VACUUM 缓解。

### single_choice · None



- [A] 查询使用了索引扫描
- [B] 查询使用了顺序扫描，可能没有合适的索引或索引未被使用
- [C] 查询使用了位图索引扫描
- [D] 查询使用了并行扫描

**参考答案**：1

**解析**：Seq Scan 表示全表顺序扫描，通常意味着没有可用索引或优化器认为顺序扫描更优。

### single_choice · None



- [A] 在 WHERE 子句中对索引列使用 LIKE 'abc%'
- [B] 在 WHERE 子句中对索引列使用 LIKE '%abc'
- [C] 在 WHERE 子句中使用索引列 = 值
- [D] 在 WHERE 子句中使用索引列 BETWEEN 1 AND 10

**参考答案**：1

**解析**：以通配符开头的 LIKE 模式（如 '%abc'）无法利用普通 B-tree 索引。

### single_choice · None



- [A] 普通 CREATE INDEX 允许并发写操作
- [B] CREATE INDEX CONCURRENTLY 比普通 CREATE INDEX 更快
- [C] CREATE INDEX CONCURRENTLY 不能在事务中运行，且可能留下无效索引
- [D] CREATE INDEX CONCURRENTLY 会自动处理所有错误

**参考答案**：2

**解析**：CONCURRENTLY 选项不能在事务块中执行，且失败时可能留下无效索引，速度也较慢。

### single_choice · None



- [A] B-tree
- [B] Hash
- [C] GiST
- [D] GIN

**参考答案**：2

**解析**：GiST 索引支持地理空间数据类型和操作符，常用于 PostGIS 等扩展。

### single_choice · None



- [A] 在 user_id 上创建单列索引
- [B] 在 created_at 上创建单列索引
- [C] 在 (user_id, created_at DESC) 上创建复合索引
- [D] 在 (created_at DESC, user_id) 上创建复合索引

**参考答案**：2

**解析**：最左前缀原则要求复合索引的第一列是查询条件中最常用的过滤列 user_id，第二列用于排序。

### single_choice · None



- [A] 在 WHERE 子句中使用 column = 100
- [B] 在 WHERE 子句中使用 column > 100
- [C] 在 WHERE 子句中使用 UPPER(column) = 'ABC'
- [D] 在 WHERE 子句中使用 column IN (1,2,3)

**参考答案**：2

**解析**：对列使用函数（如 UPPER）会导致普通索引无法直接使用，除非创建了表达式索引。

### single_choice · None



- [A] SELECT * FROM pg_indexes WHERE tablename = 'table_name';
- [B] SHOW INDEXES FROM table_name;
- [C] DESCRIBE INDEXES table_name;
- [D] LIST INDEXES ON table_name;

**参考答案**：0

**解析**：PostgreSQL 提供 pg_indexes 系统视图来查询索引信息；其他命令在 PostgreSQL 中不存在或属于其他数据库系统。

### single_choice · None



- [A] 唯一索引只能通过 UNIQUE 约束自动创建，不能手动创建
- [B] 唯一索引允许列中存在多个 NULL 值
- [C] 唯一索引不允许任何 NULL 值
- [D] 唯一索引只能用于主键列

**参考答案**：1

**解析**：PostgreSQL 中唯一约束允许 NULL 值，且多个 NULL 被认为互不相等，因此可以有多个 NULL。

### single_choice · None



- [A] 部分索引只能用于数值类型的列
- [B] 部分索引通过 WHERE 子句限定索引覆盖的行，适合查询条件固定且只需要部分数据的情况
- [C] 部分索引不能与唯一约束一起使用
- [D] 部分索引会自动更新，无需维护

**参考答案**：1

**解析**：部分索引使用 WHERE 子句只索引符合条件的行，可减少索引大小和提高查询效率。

### single_choice · None



- [A] B-tree
- [B] Hash
- [C] GIN
- [D] GiST

**参考答案**：2

**解析**：GIN 索引适合处理包含多个值的数据类型（如数组、JSONB），支持 @>、? 等操作符。

### single_choice · None



- [A] 经常出现在 WHERE 子句中的列
- [B] 经常用于 JOIN 连接的列
- [C] 经常被更新的列且表写入频繁
- [D] 经常用于 ORDER BY 的列

**参考答案**：2

**解析**：频繁更新的列会导致索引维护开销增大，降低写入性能，因此不适合创建索引。

### single_choice · None



- [A] 该语句会阻塞对表的写操作直到索引创建完成
- [B] 该语句允许在创建索引时并发进行写操作，但可能失败并留下无效索引
- [C] 该语句不能在事务块中执行
- [D] 该语句只能用于唯一索引

**参考答案**：1

**解析**：CONCURRENTLY 选项允许在创建索引时并发写入，但可能失败并留下无效索引，且不能在事务块中执行。选项 C 也是事实，但题目问的是关于该语句的正确说法，B 更全面。

### single_choice · None



- [A] 事务隔离级别不足导致丢失更新
- [B] 事务的原子性被破坏
- [C] 数据库磁盘 IO 错误
- [D] 事务的持久性未开启

**参考答案**：0

**解析**：两个事务基于同一旧值并发写回，其中一个的更新被覆盖，这是典型的丢失更新问题，源于隔离级别不足以阻止并发写冲突，与原子性、持久性和磁盘 IO 无关。

### single_choice · None



- [A] READ UNCOMMITTED 不会出现脏读
- [B] READ COMMITTED 可以避免脏读，但可能出现不可重复读
- [C] REPEATABLE READ 一定完全避免幻读
- [D] SERIALIZABLE 性能最高且允许幻读

**参考答案**：1

**解析**：READ COMMITTED 保证只能读到已提交数据，因此避免脏读，但仍可能出现同一事务内两次读同一行结果不同（不可重复读）。READ UNCOMMITTED 允许脏读；REPEATABLE READ 在标准定义下仍可能出现幻读；SERIALIZABLE 隔离最强但性能最低。

### single_choice · None



- [A] 隔离级别与并发异常无关
- [B] 提高隔离级别往往需要更多锁或更严格的快照控制，增加等待
- [C] SERIALIZABLE 不会降低任何并发度
- [D] 降低隔离级别一定不会引入一致性问题

**参考答案**：1

**解析**：高隔离级别通过更强的锁或更严格的串行化控制来消除异常，代价是更多等待、更低并发。降低级别则可能重新引入脏读、不可重复读等异常。

### multi_choice · None



- [A] READ UNCOMMITTED 允许脏读
- [B] READ COMMITTED 能避免脏读但允许不可重复读
- [C] REPEATABLE READ 在标准定义下仍可能允许幻读
- [D] SERIALIZABLE 完全不允许任何并发执行
- [E] 所有隔离级别都允许脏读

**参考答案**：[0, 1, 2]

**解析**：READ UNCOMMITTED 允许脏读；READ COMMITTED 避免脏读但允许不可重复读；标准的 REPEATABLE READ 仍可能允许幻读（部分数据库实现更强）。SERIALIZABLE 追求串行化等价，并非禁止并发执行，只是保证结果等价；说所有级别都允许脏读是错误的。

### multi_choice · None



- [A] 当前事务的隔离级别
- [B] 并发事务的提交时机
- [C] 数据库使用的多版本快照还是锁读
- [D] 操作系统发行版名称

**参考答案**：[0, 1, 2]

**解析**：结果不一致与隔离级别、并发提交时机以及底层是快照读还是锁读直接相关；操作系统发行版名称与事务可见性语义无关。

### multi_choice · None



- [A] 让多个事务以一致的顺序访问资源
- [B] 尽量缩短事务持有锁的时间
- [C] 合并或减少事务中不必要的锁范围
- [D] 所有事务把隔离级别设为最高并长期持有锁

**参考答案**：[0, 1, 2]

**解析**：统一访问顺序能打破循环等待，缩短持锁时间和缩小锁范围能降低冲突；把隔离级别设为最高并长期持锁会加剧阻塞与死锁。

### multi_choice · None



- [A] 悲观锁假设冲突较多，倾向于先加锁再操作
- [B] 乐观锁通常在提交时检测冲突并处理重试
- [C] 乐观锁在冲突频繁时可能因大量重试导致开销上升
- [D] 悲观锁不会产生任何等待

**参考答案**：[0, 1, 2]

**解析**：悲观锁先加锁避免冲突，但会引入等待甚至死锁；乐观锁后置检测冲突并重试，冲突多时重试开销大。因此悲观锁不会产生等待是错误的。

### fill_blank · None



**参考答案**：["READ COMMITTED", "read committed", "Read Committed", "READ_COMMITTED"]

**解析**：标准顺序为 READ UNCOMMITTED、READ COMMITTED、REPEATABLE READ、SERIALIZABLE，READ COMMITTED 位于第二级。

### fill_blank · None



**参考答案**：["脏读", "dirty read", "Dirty Read"]

**解析**：脏读指读取到未提交且可能回滚的数据，是最低隔离级别下允许的异常。

### fill_blank · None



**参考答案**：["幻读", "phantom read", "Phantom Read"]

**解析**：结果集范围的行数变化即幻读，区别于针对同一行值的不可重复读。

### code_reading · None



**参考答案**：最可能返回 6000。因为 READ COMMITTED 下每次读都取当前最新的已提交版本，会话 B 的更新已提交，因此第二次读取会看到新值，体现为不可重复读。

**解析**：READ COMMITTED 不保证同一事务内重复读一致，只保证不读未提交数据，所以已提交的新值会被看到，即不可重复读。

### code_reading · None



**参考答案**：可能出现丢失更新：两个事务都读到 stock=10，各自计算为 9 并写回，最终库存为 9 而实际应为 8。原因是基于旧值的写回覆盖了对方的更新。

**解析**：读-改-写序列在没有行锁或版本校验的情况下并发执行，会互相覆盖，属于丢失更新，需要加锁或使用带条件的原子更新来避免。

### single_choice · None



- [A] 脏读
- [B] 不可重复读
- [C] 幻读
- [D] 死锁

**参考答案**：2

**解析**：两次相同条件的范围查询之间新增了满足条件的行，结果集行数变化，这是幻读。不可重复读针对同一行的值变化，幻读针对结果集范围的行数变化。

### scenario · None



**解析**：超卖本质是并发下基于旧值的读-改-写导致丢失更新。修复思路包括：提高隔离级别或对相关行加锁（悲观控制），以及使用带条件的原子更新（如更新时附加 stock >= 1 条件）或版本号乐观锁让冲突更新失败重试，从而保证扣减的原子性与一致性。

### single_choice · None



- [A] 幻读
- [B] 脏读
- [C] 不可重复读
- [D] 丢失更新

**参考答案**：1

**解析**：读到了其他事务尚未提交、可能被回滚的数据，就是脏读。它由 READ UNCOMMITTED 或未加控制地读取中间状态引起。

### single_choice · None



- [A] 读操作仍然必须等待写锁释放
- [B] 读操作通常读取一致性快照，减少读写互相阻塞
- [C] 它自动把隔离级别提升到 SERIALIZABLE
- [D] 它取消了回滚日志的使用

**参考答案**：1

**解析**：MVCC 让读操作访问某个时间点的一致性快照而非读取最新未提交数据，从而减少读写阻塞。它不会自动提升隔离级别，通常还需要保留版本或回滚信息来构造快照。

### single_choice · None



- [A] 乐观锁通过数据库全局加锁来保证不发生冲突
- [B] 乐观锁在提交时校验版本，冲突时重试，可减少长时间持锁
- [C] 乐观锁无法检测到并发写冲突
- [D] 乐观锁只能用于读操作

**参考答案**：1

**解析**：乐观锁假设冲突较少，读取时记录版本，更新时以版本为条件更新，失败则重试，从而避免长时间持有数据库锁；它依然能检测冲突（更新影响行数为 0 表示冲突）。

### single_choice · None



- [A] 脏读
- [B] 死锁
- [C] 幻读
- [D] 不可重复读

**参考答案**：1

**解析**：互相持有并等待对方释放锁形成循环等待，就是死锁。数据库的死锁检测会选取代价较小的事务回滚以打破循环。

### single_choice · None



- [A] 锁范围过大可能增加阻塞和死锁概率，应按需缩小范围
- [B] 锁永远不需要释放
- [C] 加锁越多性能越好
- [D] 范围锁只影响读事务

**参考答案**：0

**解析**：为防幻读，高隔离级别可能使用范围锁或间隙锁，锁范围过大会显著增加持有时间、阻塞面和死锁概率，因此应尽量缩小操作范围或缩短事务。

### single_choice · None



- [A] 把隔离级别降到最低即可，无需改动事务逻辑
- [B] 缩短事务持有时间，把非数据库操作移出事务，及时提交
- [C] 将所有查询改为不加任何控制
- [D] 关闭数据库的日志功能

**参考答案**：1

**解析**：长事务会长时间持有锁或快照，放大阻塞。应尽量缩短事务边界，把网络调用、文件处理等耗时非数据库操作放到事务之外，并在合适时机尽快提交。

### single_choice · None



- [A] 该级别下每次读取看到的是最新已提交版本，因此值可能变化
- [B] 该级别禁止重复读取
- [C] 该级别会自动回滚第一个查询
- [D] 该级别下读操作会永远阻塞

**参考答案**：0

**解析**：READ COMMITTED 每次读取都取当前最新的已提交版本，因此同一事务内两次读可能看到不同的值，这正是不可重复读。
