# s5u2l3 从零到工程级的 Redis Python 实战 / 用 Python 操作 MongoDB

> 来源 `content/lessons/s5u2l3.json`

## py.db.redis

# py.db.redis：从零到工程级的 Redis Python 实战

> **一句话直觉**：Redis 是一个把数据放在内存里的“超快字典服务器”，而 `py.db.redis` 讲的就是用 Python 客户端（redis-py）去读写它——缓存、计数器、排行榜、消息队列，几乎都靠这一招。

---

## 0. 先建立心智模型：Redis 到底是什么？

Redis 全称 **REmote DIctionary Server**（远程字典服务器）。你可以把它想象成一台独立运行、可以被多个进程/多台机器共享的 Python `dict`，但它的键值不是普通变量，而是持久化在内存里、支持过期（expiration）、支持原子操作（atomic operation）的数据结构。

在 Python 里我们使用官方推荐的客户端 **redis-py**（安装包名就是 `redis`）。

```bash
pip install redis
```

```python
import redis

# 默认连接本机 6379 端口
r = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)

# 最像 dict 的两个操作
r.set("user:1:name", "Alice")          # 写入
print(r.get("user:1:name"))              # 读取 -> "Alice"
print(r.exists("user:1:name"))           # 键是否存在 -> 1
r.delete("user:1:name")                  # 删除
```

**关键结论**：`decode_responses=True` 让返回值是 `str` 而不是 `bytes`，在业务代码里几乎总是这样设置。

---

## 1. 连接管理与连接池（Connection Pool）

每次 `redis.Redis()` 都建新连接会很慢。生产环境应复用**连接池**。

```python
import redis

# 显式创建连接池，多个线程/协程共享
pool = redis.ConnectionPool(
    host="localhost",
    port=6379,
    db=0,
    decode_responses=True,
    max_connections=50,      # 池上限
)

r = redis.Redis(connection_pool=pool)
r.set("ping", "pong")
assert r.get("ping") == "pong"
```

**工程建议**：把 `pool` 或 `r` 做成模块级单例（singleton），不要在每个函数里 new。

---

## 2. 五大常用数据类型与 Python 客户端 API

Redis 不只是字符串。它内置了五种“值类型”，每种都对应一组命令。

### 2.1 String（字符串 / 计数器）

```python
r.set("page:home:views", 0)
r.incr("page:home:views")          # 原子 +1
r.incrby("page:home:views", 10)   # 原子 +10
print(r.get("page:home:views"))    # "11"

# 设置 60 秒过期（缓存非常常用）
r.set("cache:token", "abc", ex=60)
print(r.ttl("cache:token"))        # <=60 的剩余秒数
```

### 2.2 Hash（哈希 / 对象）

存一个对象的多个字段，比用 JSON 字符串更省内存、可局部更新。

```python
r.hset("user:1", mapping={"name": "Alice", "age": 30, "city": "Beijing"})
print(r.hget("user:1", "name"))     # "Alice"
print(r.hgetall("user:1"))          # {'name': 'Alice', 'age': '30', 'city': 'Beijing'}
r.hincrby("user:1", "age", 1)      # age -> 31
```

### 2.3 List（列表 / 队列 / 栈）

```python
r.rpush("jobs", "task1", "task2", "task3")   # 右边入队
print(r.lpop("jobs"))      # "task1"  左出队 -> FIFO 队列
print(r.rpop("jobs"))      # "task3"  右出队 -> LIFO 栈
print(r.lrange("jobs", 0, -1))  # 剩余全部
```

### 2.4 Set（无序集合 / 去重、交集）

```python
r.sadd("user:1:tags", "python", "redis", "python")  # 重复自动去重
print(r.smembers("user:1:tags"))   # {'python', 'redis'}
print(r.sismember("user:1:tags", "python"))  # True
```

### 2.5 Sorted Set / ZSet（有序集合 / 排行榜）

每个元素带一个 score，按 score 排序。排行榜、延时队列都靠它。

```python
r.zadd("leaderboard", {"alice": 100, "bob": 95, "carol": 120})
print(r.zrevrange("leaderboard", 0, 2, withscores=True))  # 从高到低取前 3
# [('carol', 120.0), ('alice', 100.0), ('bob', 95.0)]
r.zincrby("leaderboard", 10, "bob")  # bob 加 10 分
```

**关键结论**：选对数据结构比写对代码更重要。排行榜用 ZSet，计数器用 String `INCR`，对象用 Hash。

---

## 3. 过期、原子性与命名规范

### 过期

```python
r.set("code:13800000000", "123456", ex=300)  # 5 分钟验证码
```

### 原子性

Redis 单线程执行命令，像 `INCR`、`SETNX`（set if not exists）天然是原子的，适合做分布式锁。

```python
# 简易分布式锁：谁 set 成功谁持锁
ok = r.set("lock:order:42", "worker-A", nx=True, ex=10)
print(ok)   # True 表示抢到锁
```

### 键命名规范

推荐 `业务:对象:标识[:字段]` 的形式，例如：

- `user:1:profile`
- `cache:article:9001`
- `lock:order:42`

**关键结论**：好的键名让运维排查（如 `SCAN` 匹配）和内存治理都轻松很多。

---

## 4. Pipeline 与事务（Pipeline & Transaction）

网络往返（RTT）是 Redis 性能的大敌。**Pipeline** 把多条命令一次性发出去，再一次性收结果。

```python
pipe = r.pipeline(transaction=True)   # transaction=True 用 MULTI/EXEC 包成一个事务
pipe.set("a", 1)
pipe.incr("a")
pipe.get("a")
results = pipe.execute()
print(results)   # [True, 2, '2']
```

**关键结论**：批量写入、批量计数、需要“原子一批”的场景，一定要用 pipeline；它能把 1000 次操作的延迟从秒级压到毫秒级。

---

## 5. 工程化注意事项

- **序列化**：`decode_responses=True` 只解决 bytes 问题；复杂对象推荐 `json.dumps/loads` 或 `pickle`（注意安全边界）。
- **异常处理**：捕获 `redis.exceptions.ConnectionError`、`TimeoutError` 做重试或降级。
- **超时**：`socket_timeout` / `socket_connect_timeout` 必须设置，避免线程被卡死。
- **不要在 Redis 存大对象**：单个 value 建议控制在 10KB 以内，大对象放对象存储。
- **持久化**：RDB 快照 / AOF 日志是服务端配置，客户端不用管，但要知道“Redis 不是数据库的替代品”，关键数据要落库。

```python
import redis
from redis.exceptions import ConnectionError, TimeoutError

r = redis.Redis(
    host="localhost", port=6379, decode_responses=True,
    socket_timeout=2, socket_connect_timeout=2,
)

try:
    r.ping()
except (ConnectionError, TimeoutError) as e:
    print("Redis 不可用，走降级逻辑:", e)
```

---

## 动手练习

**任务：用 Redis 实现一个“文章浏览量 + Top N 排行榜”小服务。**

1. 启动本地 Redis（`docker run -p 6379:6379 redis:7` 或本机安装）。
2. 安装 `redis` 包：`pip install redis`。
3. 写一个 `view_article(article_id)` 函数：
   - 用 Hash 存文章标题（首次自动写入 `title:{id}`）；
   - 用 `INCR` 把 `article:{id}:views` 加 1；
   - 用 ZSet `article:rank` 对文章热度加 1。
4. 写一个 `top_articles(n=3)` 函数，返回浏览量最高的前 n 篇，包含 id、title、views。
5. 模拟 100 次随机浏览，打印 top3；再给某篇文章设 `EXPIRE` 5 秒，验证它消失后不再出现在排行榜中（提示：删 key 时同步 `ZREM`）。

**验收标准**：能连续跑两次脚本，排行榜结果正确；Redis 重启后数据仍在（说明你配置了持久化，或者至少证明了“数据在服务器端而非 Python 进程内”）。

## py.db.mongo

# py.db.mongo：用 Python 操作 MongoDB

## 一句话直觉

当你需要把一堆「结构不固定、随时可改字段、可能非常大」的 Python 字典存起来、并按任意字段快速查询时，MongoDB 比传统 SQL 表更自然——而 `pymongo` 就是让 Python 与 MongoDB 对话的官方驱动。

---

## 1. MongoDB 与 pymongo 是什么

**MongoDB** 是一个面向文档的 NoSQL（Not Only SQL）数据库，它把数据存成类似 JSON 的 **BSON**（Binary JSON）文档；多个文档组成一个 **集合**（collection）；多个集合组成一个 **数据库**（database）。

Python 的官方驱动叫 **pymongo**，安装方式：

```bash
pip install pymongo
```

你可以把 MongoDB 想象成「一个可以执行任意字典查询的全局 Python list」：

- 数据库 ≈ 一个大的命名空间；
- 集合 ≈ 一个 list；
- 文档 ≈ list 里的一个 dict（额外多了一个 `_id` 字段作为主键）。

**关键结论 1**：pymongo 的增删改查接口几乎就是 Python 字典和列表操作的语法映射，因此学习成本很低。

```python
# demo_01_connect.py
# 说明：连接到本地 MongoDB，并创建/获取一个集合对象
from pymongo import MongoClient

# MongoClient 默认连接 localhost:27017
client = MongoClient("mongodb://localhost:27017")

# 获取（或自动创建）数据库 demo_db 和集合 users
db = client["demo_db"]
users = db["users"]

print("数据库:", db.name)
print("集合:", users.name)
```

---

## 2. 写入：插入文档（Insert）

单条插入用 `insert_one`，批量插入用 `insert_many`。插入后，MongoDB 会自动给文档加上 `_id`（若你没有指定）。

**关键结论 2**：`insert_one` 返回一个 `InsertOneResult` 对象，其 `inserted_id` 就是新文档的 `_id`。

```python
# demo_02_insert.py
from pymongo import MongoClient

users = MongoClient()["demo_db"]["users"]

# 1) 插入单条文档
result = users.insert_one({"name": "alice", "age": 30, "tags": ["py", "ai"]})
print("新文档 _id:", result.inserted_id)

# 2) 插入多条文档
result = users.insert_many([
    {"name": "bob",   "age": 25, "tags": ["go"]},
    {"name": "carol", "age": 35, "tags": ["py", "db"]},
])
print("批量插入的 _id:", result.inserted_ids)
```

---

## 3. 查询：用字典作为条件（Query）

查询条件就是「一个字典」，键是字段名，值是期望值。`find_one` 返回单条 dict 或 `None`；`find` 返回一个可迭代的 **Cursor**（游标）。

**关键结论 3**：查询条件字典支持比较运算符，通过 `$gt`、`$lt`、`$in`、`$regex` 等以「美元符前缀」表达。

```python
# demo_03_query.py
from pymongo import MongoClient

users = MongoClient()["demo_db"]["users"]

# 精确匹配
print(users.find_one({"name": "alice"}))

# 比较：age > 28
for doc in users.find({"age": {"$gt": 28}}):
    print(doc)

# 包含：tags 数组里包含 "py"
for doc in users.find({"tags": "py"}):
    print("含 py 的文档:", doc["name"])

# 投影：只返回 name 字段，不返回 _id
for doc in users.find({}, {"name": 1, "_id": 0}):
    print(doc)
```

---

## 4. 更新与删除（Update / Delete）

更新要区分「替换整条文档」与「修改部分字段」：

- `replace_one(filter, new_doc)`：整条替换；
- `update_one / update_many(filter, {"$set": {...}})`：只修改指定字段；
- `$inc`、`$push`、`$pull` 等是常用的字段级操作符。

**关键结论 4**：不加 `$` 操作符的 update 字典会被当成「整字段替换」，容易误删数据；要用 `$set`、`$inc` 等显式操作符。

```python
# demo_04_update_delete.py
from pymongo import MongoClient

users = MongoClient()["demo_db"]["users"]

# 更新一个字段
users.update_one({"name": "alice"}, {"$set": {"age": 31}})

# 数值自增
users.update_one({"name": "bob"}, {"$inc": {"age": 1}})

# 向数组追加元素
users.update_one({"name": "carol"}, {"$push": {"tags": "mongo"}})

# 删除一条
users.delete_one({"name": "bob"})

# 删除多条
users.delete_many({"age": {"$lt": 20}})
```

---

## 5. 工程级：索引、投影与连接管理

上线代码不能只用 `find({})` 全表扫，否则数据量一大就慢。要点：

1. **索引**（index）：对经常查询的字段建索引，B 树加速；
2. **投影**（projection）：只取需要的字段，减少网络与内存；
3. **批量操作**：`bulk_write` 把多次写合并；
4. **连接管理**：`MongoClient` 是线程安全、带连接池的单例，应用启动时创建一次即可。

**关键结论 5**：`MongoClient` 内部维护连接池，不要每次请求都新建 Client；进程退出时调用 `client.close()`。

```python
# demo_05_engineering.py
from pymongo import MongoClient, ASCENDING

client = MongoClient("mongodb://localhost:27017", maxPoolSize=50)
users = client["demo_db"]["users"]

# 为 name 建立唯一索引（若已存在会忽略）
users.create_index([("name", ASCENDING)], unique=True)

# 只取 name 和 age，按 age 升序
for doc in users.find({"age": {"$gte": 25}}, {"name": 1, "age": 1, "_id": 0}).sort("age", ASCENDING):
    print(doc)

# 应用退出时释放连接
client.close()
```

---

## 动手练习

**任务**：写一个 `notes.py` 脚本，用 pymongo 做一个简易「笔记管理」工具。

要求：

1. 集合为 `demo_db.notes`，每条笔记形如 `{"title": str, "body": str, "tags": [str], "created_at": datetime}`。
2. 实现以下函数：
   - `add_note(title, body, tags)`：插入一条笔记，返回 `_id`；
   - `search_by_tag(tag)`：返回所有包含该 tag 的笔记；
   - `update_body(title, new_body)`：按 title 更新正文；
   - `delete_note(title)`：按 title 删除；
   - `stats()`：打印总笔记数与所有出现过的 tag（去重）。
3. 为 `tags` 建立索引，并至少插入 5 条测试数据，验证以上每个函数。
4. 加分：用 `pytest` 或 `unittest` 写 3 个单元测试，测试前先清空集合。

提示：`$addToSet` 可以去重加入数组；`distinct("tags")` 可以拿到去重后的 tag 列表。


---

## 本课题目

### single_choice · None



- [A] 直接使用用户 ID 作为键名，如 "12345"
- [B] 使用带业务前缀的键名，如 "session:user:12345"
- [C] 使用随机 UUID 作为键名以便分散存储
- [D] 使用包含空格的描述性键名，如 "user session 12345"

**参考答案**：1

**解析**：带业务前缀的键名（如 session:user:12345）可以避免不同业务模块之间的键冲突，便于运维排查和批量管理；纯数字键名容易与其他业务冲突，随机 UUID 不利于排查，含空格的键名虽然 Redis 允许但在命令行和客户端中容易出错。

### single_choice · None



- [A] SET 加 EX 参数写入的值类型不同
- [B] SET 加 EX 参数是原子操作，不会出现设置了值却没有设置过期时间的中间状态
- [C] EXPIRE 不能用于字符串类型的键
- [D] 两者在功能上完全等价，只是写法不同

**参考答案**：1

**解析**：SET 带 EX 参数在一条命令中完成赋值和设置过期时间，是原子操作；分两步执行时，若在 SET 之后、EXPIRE 之前客户端崩溃或网络中断，键就会永久存在，造成内存泄漏。

### multi_choice · None



- [A] 游戏排行榜，按分数排序
- [B] 延时队列，按执行时间排序
- [C] 存储用户的基本信息对象
- [D] 去重统计，同时需要按时间排序

**参考答案**：[0, 1, 3]

**解析**：Sorted Set 按 score 排序，适合排行榜和延时队列；也支持按时间戳作为 score 实现带排序的去重统计。存储用户基本信息对象更适合用 Hash 或 String。

### multi_choice · None



- [A] 缓存穿透是指查询不存在的数据，请求直达数据库
- [B] 缓存击穿是指某个热点键过期瞬间大量请求打到数据库
- [C] 缓存雪崩是指大量键在同一时间过期，导致数据库压力骤增
- [D] 缓存雪崩可以通过给过期时间加随机值来缓解

**参考答案**：[0, 1, 2, 3]

**解析**：四个选项分别正确描述了缓存穿透、击穿、雪崩的定义以及雪崩的一种常见缓解手段（过期时间加随机值）。缓存穿透的常见解法还包括布隆过滤器或缓存空值。

### multi_choice · None



- [A] 使用连接池可以避免频繁创建和销毁连接的开销
- [B] redis.Redis() 默认会使用连接池
- [C] 连接池中的连接数量没有上限，可以无限增长
- [D] 通过 connection_pool 参数可以显式传入自定义连接池

**参考答案**：[0, 1, 3]

**解析**：连接池复用连接，减少开销；redis.Redis() 默认创建并使用 ConnectionPool；可以通过 connection_pool 参数传入自定义连接池。连接池有 max_connections 上限，并非无限增长。

### multi_choice · None



- [A] INCR 和 DECR
- [B] SETNX
- [C] MULTI/EXEC 事务块中的命令序列
- [D] 先用 GET 判断键是否存在，再根据结果 SET

**参考答案**：[0, 1, 2]

**解析**：INCR、DECR、SETNX 都是单条原子命令；MULTI/EXEC 包裹的命令序列作为一个整体执行，不会被其他客户端命令打断。先 GET 再 SET 是两条独立命令，中间可能被其他客户端插入操作，不具备原子性——应使用 SETNX 或 Lua 脚本。

### multi_choice · None



- [A] noeviction 策略下，内存满时写入命令会返回错误
- [B] allkeys-lru 会从所有键中按最近最少使用原则淘汰
- [C] volatile-lru 只从设置了过期时间的键中淘汰
- [D] Redis 默认的淘汰策略是 allkeys-lru

**参考答案**：[0, 1, 2]

**解析**：noeviction 是默认策略，内存满时写命令报错；allkeys-lru 从所有键中淘汰；volatile-lru 只从设置了过期时间的键中淘汰。Redis 默认是 noeviction，不是 allkeys-lru。

### fill_blank · None



**参考答案**：["EX", "ex"]

**解析**：SET 命令的 EX 参数用于指定过期时间（单位：秒），如 SET key value EX 300。对应的还有 PX 参数（单位：毫秒）。

### fill_blank · None



**参考答案**：["TTL", "ttl"]

**解析**：TTL 命令返回键的剩余生存时间（秒），返回 -1 表示键存在但没有设置过期时间，返回 -2 表示键不存在。PTTL 返回毫秒级。

### code_reading · None



**参考答案**：因为 expire 设置了键 'name' 在 1 秒后过期，代码 sleep 了 2 秒后再读取，此时键已经过期被删除，所以 get 返回 None。

**解析**：expire 设置过期时间后，经过指定秒数键会自动失效。sleep 2 秒超过了 1 秒的过期时间，键已被删除，get 对不存在的键返回 None。

### code_reading · None



**参考答案**：incr 每次将键的值加 1，循环执行 5 次后 count 的值为 b'5'。

**解析**：incr 是原子性的自增命令，初始值为 0，循环 5 次后值变为 5。redis-py 的 get 返回 bytes 类型，所以输出 b'5'。

### scenario · None



**参考答案**：["缓存击穿", "热点键", "互斥锁", "逻辑过期", "布隆过滤器"]

**解析**：大量请求同时查询同一个热点键，若该键恰好过期，请求会全部涌向数据库，这是典型的缓存击穿。应对措施包括：用互斥锁保证只有一个请求去加载数据、其他请求等待；对热点键使用逻辑过期（不设物理过期，异步更新）；或提前预热并延长热点键的过期时间。

### single_choice · None



- [A] 存储一个需要频繁整体读取的 JSON 大对象
- [B] 存储一个用户对象的多个字段（如姓名、年龄、邮箱），且需要单独读取或修改某个字段
- [C] 存储一个不断追加的日志列表
- [D] 存储需要按分数排序的排行榜数据

**参考答案**：1

**解析**：Hash 类型适合存储对象的多个字段，可以单独读写某个字段而无需整体序列化/反序列化，也节省键名开销；整体读取的大对象用 String 更简单；追加日志应用 List；排行榜应用 Sorted Set。

### scenario · None



**参考答案**：["未设置过期时间", "EXPIRE", "SET EX", "内存淘汰策略"]

**解析**：最可能的原因是创建 token 键时没有设置过期时间，导致令牌失效后键仍然驻留内存。应养成写缓存键时同时设置过期时间的习惯，使用 SET key value EX seconds 或 EXPIRE 命令；同时可配置合理的内存淘汰策略作为兜底。

### single_choice · None



- [A] RDB 持久化会记录每一条写命令，恢复时逐条重放
- [B] AOF 持久化默认每秒同步一次，可能丢失最近一秒的数据
- [C] 开启 RDB 后就不需要 AOF 了，两者不能同时使用
- [D] AOF 文件永远不会被重写，会无限增长

**参考答案**：1

**解析**：AOF 默认使用 everysec 策略，每秒将缓冲区数据同步到磁盘，因此极端情况下可能丢失最近一秒的写入；RDB 是快照而非命令日志；RDB 和 AOF 可以同时开启；AOF 支持重写（rewrite）来压缩文件体积。

### single_choice · None



- [A] b'10'
- [B] b'11'
- [C] 11
- [D] '11'

**参考答案**：1

**解析**：INCR 命令将键的值加 1，'counter' 从 10 变为 11。redis-py 的 get 方法默认返回 bytes 类型，因此结果是 b'11'，而不是字符串或整数。

### single_choice · None



- [A] SET
- [B] GETSET
- [C] GET
- [D] MSET

**参考答案**：1

**解析**：GETSET 命令在设置新值的同时返回旧值，是原子操作；SET 只设置值不返回旧值；GET 只读取；MSET 批量设置但不返回旧值。注意 GETSET 在新版本中已被标记为废弃，推荐使用 SET 的 GET 选项。

### single_choice · None



- [A] Redis 事务支持回滚，某条命令失败时前面的命令也会被撤销
- [B] Redis 事务中的命令在 EXEC 时才被依次执行，中途出错不会回滚已执行的命令
- [C] Redis 事务中的命令会立即执行，只是结果在 EXEC 时返回
- [D] Redis 不支持事务

**参考答案**：1

**解析**：Redis 事务通过 MULTI 开始、EXEC 提交，命令在 EXEC 时依次执行。与关系型数据库不同，Redis 事务不支持回滚：如果某条命令运行时出错，已执行的命令不会撤销，后续命令仍会继续执行。

### single_choice · None



- [A] Redis 采用定时删除，为每个键创建一个定时器
- [B] Redis 采用惰性删除和定期删除相结合的策略
- [C] Redis 过期键会立即被删除，内存马上释放
- [D] Redis 不会主动删除过期键，只能靠客户端清理

**参考答案**：1

**解析**：Redis 同时使用惰性删除（访问键时检查是否过期）和定期删除（周期性随机抽样检查并删除过期键）两种策略，兼顾 CPU 和内存。定时删除会消耗大量定时器资源，Redis 没有采用。

### single_choice · None



- [A] [b'a', b'b', b'c']
- [B] [b'c', b'b', b'a']
- [C] [b'a', b'b']
- [D] b'a'

**参考答案**：0

**解析**：RPUSH 依次从右侧插入 a、b、c，列表顺序为 a, b, c。LRANGE 0 -1 返回全部元素，redis-py 返回 bytes 列表 [b'a', b'b', b'c']。

### single_choice · None



- [A] 提高读取速度
- [B] 确保缓存数据最终能与数据源保持一致，避免脏数据长期存在
- [C] 减少网络传输量
- [D] 防止 Redis 被攻击

**参考答案**：1

**解析**：设置过期时间可以让缓存中的数据在一定时间后失效，下次读取时重新从数据源加载，从而保证缓存最终一致性，避免数据源已更新而缓存仍是旧值。提高读取速度是缓存本身的目的，与过期时间无关。

### single_choice · None



- [A] 集合必须预先定义严格的字段结构，文档不能包含额外字段
- [B] 一个集合可以存放结构不同的文档，字段可以各不相同
- [C] 文档必须使用整数作为主键，不能使用自动生成的 ObjectId
- [D] 一个数据库只能有一个集合

**参考答案**：1

**解析**：MongoDB 是面向文档的数据库，集合中的文档结构可以不同，属于 schema-less（灵活模式）。集合无需预定义字段，主键默认是 ObjectId，一个数据库可含多个集合。

### single_choice · None



- [A] 通过 MongoClient 建立连接，再从客户端对象取得数据库对象和集合对象进行增删改查
- [B] 必须先调用 connect() 手动建立 TCP 连接，否则任何操作都会报错
- [C] 每次插入文档都必须显式创建 Collection 类实例并注册到数据库
- [D] MongoClient 只能用于读取，写入需要另建 WriteClient

**参考答案**：0

**解析**：PyMongo 的典型用法是用 MongoClient 创建客户端，然后以属性或下标方式取数据库和集合，客户端内部会按需管理连接池；不存在必须手动 connect 或单独的 WriteClient。

### multi_choice · None



- [A] $gt（大于）
- [B] $in（在给定集合内）
- [C] $exists（字段是否存在）
- [D] $commit（提交事务）
- [E] $unwind（展开数组，属于聚合阶段）

**参考答案**：[0, 1, 2]

**解析**：$gt、$in、$exists 都是查询操作符；$commit 不是查询操作符；$unwind 是聚合阶段操作符而非查询筛选操作符。

### multi_choice · None



- [A] 可以一次插入一条文档，也可以批量插入多条文档
- [B] 批量插入时可通过参数控制是否继续处理出错项
- [C] 插入操作可以对同一批文档保证有序或无顺序执行
- [D] 插入文档前必须为集合的所有字段创建索引
- [E] 插入时若指定了重复的 _id，默认会覆盖已有文档

**参考答案**：[0, 1, 2]

**解析**：可单条或批量插入，批量插入可指定是否有序以及出错时是否继续；无需为所有字段先建索引；重复 _id 默认触发唯一键冲突错误而非覆盖。

### multi_choice · None



- [A] 复制集通常包含一个主节点和多个从节点
- [B] 主节点负责处理写操作，从节点可提供读能力
- [C] 主节点故障时，复制集可进行选举产生新的主节点
- [D] 复制集中的每个节点都保存完全不同的数据分片
- [E] 使用复制集后就不需要再做数据备份了

**参考答案**：[0, 1, 2]

**解析**：复制集通过主从复制提供冗余与故障切换，主节点处理写，故障时可选举新主；各节点保存的是同一份数据的副本（分片是另一概念）；复制不能取代备份。

### multi_choice · None



- [A] 内嵌（embed）与引用（reference）的选择
- [B] 文档大小与数据增长趋势
- [C] 读写比例与查询模式
- [D] 是否一定满足第三范式才算合格
- [E] 所有字段都必须放在同一个文档中

**参考答案**：[0, 1, 2]

**解析**：文档模式设计需权衡内嵌还是引用、文档大小、读写与查询模式。MongoDB 不要求满足关系型范式，也不强制所有字段放在同一文档，反范式内嵌常被用来优化读性能。

### fill_blank · None



**参考答案**：["点", ".", "点号", "英文句点", "dot"]

**解析**：MongoDB 使用点号连接嵌套字段路径，如 user.name 或 items.price。

### fill_blank · None



**参考答案**：["_id", "id_", "下划线 id"]

**解析**：文档的主键字段名为 _id，若插入时未提供，驱动会自动生成 ObjectId。

### code_reading · None



**参考答案**：输出 1。因为集合原本为空，insert_one 插入了一条文档，随后 count_documents 统计集合中匹配空条件（即全部）的文档数，结果为 1。insert_one 的返回值是含 inserted_id 的结果对象，不会被打印。

**解析**：考查插入后文档数量变化。insert_one 插入一条文档，count_documents({}) 统计全部文档，因此输出 1。需注意不要把插入结果对象与文档数量混淆。

### code_reading · None



**参考答案**：find 返回的是一个游标（cursor）对象，游标可迭代，遍历时会按需从服务器分批取回匹配到的文档，因此 for 循环能逐个得到符合条件的文档。

**解析**：find 返回游标而非一次性的文档列表，游标是可迭代的，遍历时惰性获取结果，因此可直接用于 for 循环。

### scenario · None



**解析**：此场景考查模式设计中的权衡：根据查询模式决定内嵌或引用、是否需要索引及索引的收益与写入代价。日志写多读按范围，通常建议合适的文档结构、少量针对性索引，并权衡写入开销。

### scenario · None



**解析**：排查慢查询通常从查询条件与排序出发，考虑建立匹配过滤与排序的复合索引，并通过执行计划确认是否命中索引；同时要权衡索引带来的写入与存储开销。

### single_choice · None



- [A] _id 字段可选，不填时文档无法插入
- [B] 插入文档时若不提供 _id，驱动通常会为其生成一个 ObjectId
- [C] _id 必须是字符串类型
- [D] 同一集合中不同文档的 _id 可以重复

**参考答案**：1

**解析**：每个文档都需要唯一的 _id，若未提供，驱动会自动生成 ObjectId。_id 不限于字符串，且在同一集合内必须唯一。

### single_choice · None



- [A] 使用点号路径，如 {"user.name": "Ada"}
- [B] 使用箭头语法，如 {"user->name": "Ada"}
- [C] 必须先对 user 建立索引才能查询子字段
- [D] 只能先把整个 user 子文档取出再在 Python 中过滤

**参考答案**：0

**解析**：MongoDB 使用点号表示嵌套字段路径，如 "user.name"。无需箭头语法，也不必先建索引（索引只影响性能，不影响能否查询）。

### single_choice · None



- [A] 更新时必须传入完整文档，否则未提供的字段会被删除
- [B] 使用类似 $set 的更新操作符可以只修改指定字段，其余字段保持不变
- [C] 更新操作无法只更新匹配到的第一条文档，只能批量更新
- [D] 更新文档时 _id 字段可以被随意修改

**参考答案**：1

**解析**：使用 $set 等更新操作符可只更新指定字段，未涉及字段保持原样。若不使用操作符而直接传文档，则是整体替换。可通过参数控制只更新一条或全部匹配。_id 不可更改。

### single_choice · None



- [A] 调用删除方法时默认就只删第一条
- [B] 删除方法总是一次删除全部匹配文档，无法只删一条
- [C] 传入限定删除数量的参数，将其设为 1
- [D] 先查询出文档再逐条用 _id 删除，且必须手动加锁

**参考答案**：2

**解析**：删除多条/单条的 API 中，可通过参数限制删除数量（如传 1 只删一条）；默认删除行为通常是删除全部匹配。无需手动加锁。

### single_choice · None



- [A] 投影用于筛选返回文档中的哪些字段，可以只返回需要的字段
- [B] 投影只能用于排除 _id 字段，不能选择其他字段
- [C] 投影和查询条件是一回事，都是筛选文档
- [D] 使用投影后查询结果会自动按字段名排序

**参考答案**：0

**解析**：投影决定返回文档包含或排除哪些字段（如只返回 name 而排除 _id）。查询条件是筛选文档，投影是筛选字段，二者不同；投影也不负责排序。

### single_choice · None



- [A] 使用 $or 组合两个相等条件，或使用 $in 列出这两个值
- [B] 使用 $and 组合两个相等条件
- [C] 使用 $not 取反，再配合 $exists
- [D] 依次执行两次查询再在 Python 中合并结果

**参考答案**：0

**解析**：匹配多个候选值可用 $in（如 {"status": {"$in": ["paid","pending"]}}）或 $or；$and 要求同时满足两个相等条件，无法匹配一个字段的两个值。

### single_choice · None



- [A] 索引可以加快查询，但会占用存储并在写入时带来额外开销
- [B] 索引越多越好，不会影响写入性能
- [C] 集合默认对每个字段都建立了索引
- [D] 对嵌套字段无法建立索引

**参考答案**：0

**解析**：索引加速符合条件的查询，但需要存储空间并增加插入/更新的维护成本。默认只对 _id 建索引；嵌套字段也可建索引。

### single_choice · None



- [A] 聚合管道由多个阶段组成，每个阶段接收上一阶段的输出并做处理
- [B] 聚合只能做计数，不能做分组或排序
- [C] 聚合管道各阶段执行顺序任意，结果都一样
- [D] 聚合必须在客户端用 Python 遍历全部文档实现，数据库不提供聚合

**参考答案**：0

**解析**：聚合管道由有序的多个阶段（如匹配、分组、排序）组成，逐步处理文档；阶段顺序会影响结果。MongoDB 在服务端提供聚合能力。
