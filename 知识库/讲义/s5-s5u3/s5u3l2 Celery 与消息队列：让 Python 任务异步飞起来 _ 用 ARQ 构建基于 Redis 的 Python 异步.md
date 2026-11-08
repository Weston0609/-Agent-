# s5u3l2 Celery 与消息队列：让 Python 任务异步飞起来 / 用 ARQ 构建基于 Redis 的 Python 异步任务队列

> 来源 `content/lessons/s5u3l2.json`

## py.mq.celery

# Celery 与消息队列：让 Python 任务异步飞起来

## 一句话直觉

> 当用户点下「下单」按钮，你不希望页面卡 30 秒等发票邮件发完才返回——**Celery** 就是把这件「慢活」丢进消息队列（Message Queue），让另一台机器上的工人（Worker）慢慢做，主程序立刻回应用户。

---

## 1. 为什么需要 Celery：从同步阻塞说起

一个 Web 请求从浏览器出发，通常要在几百毫秒内返回，否则用户就会觉得「卡」。但现实中有大量耗时的活：

- 发送邮件 / 短信
- 生成 PDF 报表、转码视频
- 调用慢速第三方 API（AI 推理、支付回调）
- 批量写数据库、跑定时统计

如果把这些逻辑写在视图（View）函数里同步执行，会带来三个问题：

1. **延迟高**：用户必须等所有步骤完成。
2. **易失败**：发邮件超时会连带整个请求失败。
3. **难扩展**：流量大时只能加机器跑 Web，但其实该加的是「干重活」的机器。

**消息队列（Message Queue）** 的核心思想：把「要做什么」打包成一条消息（Message）塞进队列（Broker），由一个或多个消费者（Consumer）异步取出执行。

**Celery** 是 Python 生态里最主流的分布式任务队列（Distributed Task Queue）——它把「定义任务、发消息、消费消息、追踪结果、定时调度」这一整条链路都封装好了。

---

## 2. Celery 的四个核心角色

学 Celery 一定要先把这张图刻进脑子：

```
  [你的代码]                  [消息中间件]                [工人]                 [结果存储]
  Producer  ──发送任务──▶  Broker (Redis/RabbitMQ) ──▶  Worker ──结果──▶  Backend (Redis/DB)
```

| 角色 | 英文 | 作用 | 常见选型 |
|------|------|------|----------|
| 生产者 | Producer | 定义并发起任务 | 你的 Django/Flask/FastAPI 代码 |
| 消息中间件 | Broker | 存放待执行任务 | Redis、RabbitMQ |
| 工人 | Worker | 拉取并执行任务 | `celery -A app worker` 启动的进程 |
| 结果存储 | Backend | 存放任务返回值/状态 | Redis、数据库 |

关键结论：**Broker 必须比 Worker 先可用**，Worker 才能取任务；Backend 只在需要拿返回值时才需要。

---

## 3. 从零写一个最小 Celery

### 3.1 定义 Task

```python
# tasks.py
from celery import Celery

# 用 Redis 做 broker 和 backend
app = Celery(
    "demo",
    broker="redis://localhost:6379/0",   # 任务队列
    backend="redis://localhost:6379/1",  # 任务结果
)

@app.task                    # 装饰器把普通函数变成「可被 Celery 调度的任务」
def add(x: int, y: int) -> int:
    """最简单的任务：两数相加"""
    return x + y

@app.task
def send_email(to: str, subject: str) -> str:
    """模拟一个耗时任务：假装发邮件 3 秒"""
    import time
    time.sleep(3)
    return f"Mail to {to} sent"
```

`@app.task` 是全部魔法所在——它把函数改造成一个 `Task` 对象，既能在本地同步执行（`add()`），也能异步分发（`add.delay(...)`）。

### 3.2 启动 Worker

在终端执行：

```bash
celery -A tasks worker --loglevel=info
```

你会看到 Worker 开始监听 Redis 中的 `celery` 队列。

### 3.3 从主程序发送任务

```python
# main.py
from tasks import add, send_email

# 同步调用（在本进程直接执行，不经过队列）
print("sync:", add(2, 3))         # 直接返回 5

# 异步调用：扔进队列，立即返回一个 AsyncResult
result = add.delay(2, 3)
print("task id:", result.id)

# 阻塞式拿结果（生产环境通常不用 get，而是靠轮询或回调）
print("result:", result.get(timeout=10))   # 5

# 耗时任务立刻返回，不阻塞
r = send_email.delay("a@b.com", "hello")
print("已派发，主程序继续往下走")
```

关键结论：`.delay()` 与 `apply_async()` 是异步派发入口；前者是后者的语法糖。

---

## 4. 生产里的四个关键话题

### 4.1 任务状态与重试

任务可能失败（网络抖动、第三方限流）。Celery 提供内建重试：

```python
@app.task(bind=True, max_retries=3, default_retry_delay=5)
def fetch_url(self, url: str) -> str:
    try:
        import requests
        return requests.get(url, timeout=5).text
    except Exception as exc:
        # 5 秒后重试，最多 3 次
        raise self.retry(exc=exc)
```

`bind=True` 让函数第一个参数变成 `self`（任务实例），这样才能调用 `self.retry`。

### 4.2 幂等性与任务 ID

现实世界中没有「恰好一次」的保证，只有 **至少一次（at-least-once）**。这意味着**同一个任务可能被执行多次**。所以：

- 发邮件前先查「这个用户今天是否已收到」
- 扣库存用数据库唯一键约束
- 关键任务用 `task_id` 做去重

### 4.3 定时任务（Celery Beat）

Celery 自带一个「节拍器」进程 Beat，按 crontab 语法周期性派发任务：

```python
app.conf.beat_schedule = {
    "every-30s": {
        "task": "tasks.add",
        "schedule": 30.0,
        "args": (1, 2),
    },
}
```

启动：`celery -A tasks beat --loglevel=info`。

### 4.4 队列隔离与限流

不要把「慢任务」和「快任务」混在一个队列里，否则慢任务会饿死快任务：

```python
@app.task(queue="slow")
def render_video(path: str): ...

@app.task(queue="fast")
def send_sms(phone: str, text: str): ...
```

启动不同 Worker 监听不同队列：`celery -A tasks worker -Q fast`。

---

## 5. 把 Celery 放进一个真实工程

推荐布局（以 Django/Flask 为例）：

```
myproject/
├── myproject/celery.py     # 创建 app 实例
├── myproject/settings.py   # broker_url、backend_url
├── myapp/tasks.py          # 具体任务
└── manage.py
```

```python
# myproject/celery.py
import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproject.settings")
app = Celery("myproject")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()      # 自动扫描所有 app/tasks.py
```

视图里只需要 `send_email.delay(...)` 一行，业务逻辑与异步解耦。

---

## 小结表

| 概念 | 一句话 |
|------|--------|
| Broker | 存任务的仓库（Redis / RabbitMQ） |
| Worker | 真正的执行进程 |
| Backend | 存结果的仓库 |
| `@app.task` | 把函数变成任务 |
| `.delay()` | 异步派发（立即返回） |
| `.get()` | 阻塞拿结果（谨慎使用） |
| Beat | 定时派发器 |
| `-Q` | 按队列隔离 Worker |

学了这一节，你已经掌握了 Celery 的 80%：定义任务、派发任务、消费任务、拿结果、定时、隔离。剩下的 20% 是在具体项目里根据业务打磨重试策略、监控（Flower）和队列容量。

## py.mq.arq

# py.mq.arq：用 ARQ 构建基于 Redis 的 Python 异步任务队列

## 一句话直觉

**当你有一个 Web 请求不能让用户干等 30 秒（比如发邮件、跑模型推理、生成报表），你就要把这件事「扔给后台」异步执行——ARQ（Async Redis Queue）就是干这件事的：它是一个用 Python `asyncio` 写、以 Redis 为后端、可水平扩展的轻量任务队列（Task Queue）库。**

本讲用 5 个小节，从「为什么需要队列」一路讲到「生产可用的 worker 结构」。

---

## 第 1 节：为什么需要任务队列？（Message Queue 的动机）

### 1.1 同步阻塞的痛点

假设你写了一个 FastAPI 接口，用户注册后要发一封欢迎邮件：

```python
@app.post("/signup")
async def signup(email: str):
    user = await db.create_user(email)
    await send_email(email, "Welcome!")   # 慢！SMTP 可能要 2~5 秒
    return {"ok": True}
```

问题：
- 邮件 SMTP 服务器慢，**用户要陪着等**；
- 邮件失败会让整个注册接口 500；
- 流量高峰时，邮件任务把 Web 进程的协程（coroutine）全占满。

### 1.2 解耦思路

把「必须立刻完成」和「可以稍后完成」拆开：

- Web 进程只负责 **入队（enqueue）**：把一个「任务描述」写到 Redis；
- 独立的后台进程 **worker** 从 Redis 取任务、执行、写回结果。

这就是 **生产者–消费者（Producer–Consumer）** 模式，也是所有任务队列（Celery、RQ、Dramatiq、ARQ）的共同骨架。

### 1.3 ARQ 的定位

| 库 | 语言模型 | 后端 | 特点 |
|---|---|---|---|
| Celery | 同步为主 | 多种 | 功能全但重 |
| RQ | 同步 | Redis | 简单，但不支持 asyncio |
| **ARQ** | **async/await** | Redis | 轻量、专为 asyncio 设计、类型友好 |

ARQ 的官方口号就是 *"asyncio + redis = 💜"*。

---

## 第 2 节：ARQ 三大核心概念

ARQ 只有三个概念，先记住这个心智模型：

1. **Task（任务）**：一个 `async def` 函数，接收 `ctx` 和业务参数。
2. **Queue / Redis**：任务的存储与传递介质。
3. **Worker（工作进程）**：一个独立进程，不断从 Redis 拉任务执行。

数据流：

```
生产者:  enqueue_job("send_email", "a@b.com")
            │
            ▼
         Redis (job 序列化后存这里)
            │
            ▼
消费者:  worker 拉取 → 反序列化 → 执行 async def send_email(ctx, to)
            │
            ▼
        结果写回 Redis（可选）
```

### 2.1 安装

```bash
pip install arq redis
# 还需要一个本地 Redis：docker run -p 6379:6379 redis:7
```

---

## 第 3 节：最小可运行示例（Hello Worker）

先看完整代码，再解释每一部分。

### 3.1 定义任务与应用

```python
# worker.py
import asyncio
from arq import create_pool
from arq.connections import RedisSettings

async def send_email(ctx, to: str, subject: str) -> str:
    """任务函数：第一个参数必须是 ctx（WorkerContext）。"""
    print(f"[worker] 正在给 {to} 发送: {subject}")
    await asyncio.sleep(2)   # 模拟耗时 I/O
    return f"已发送给 {to}"

async def startup(ctx):
    """worker 启动时执行一次，可初始化 DB 连接池等。"""
    ctx["db"] = object()    # 演示：把共享资源挂到 ctx 上
    print("[worker] 启动完成")

async def shutdown(ctx):
    """worker 关闭时执行一次，用于清理。"""
    print("[worker] 已关闭")

class WorkerSettings:
    functions = [send_email]              # 注册所有任务
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings(host="localhost", port=6379)
    max_jobs = 10                         # 并发执行上限
    job_timeout = 60                      # 单任务超时（秒）
```

### 3.2 生产者：入队

```python
# producer.py
import asyncio
from arq import create_pool
from arq.connections import RedisSettings

async def main():
    # 创建 Redis 连接池
    redis = await create_pool(RedisSettings())
    # 入队：函数名 + 位置参数
    job = await redis.enqueue_job("send_email", "alice@example.com", "Welcome")
    print(f"已入队, job_id = {job.job_id}")
    await redis.close()

if __name__ == "__main__":
    asyncio.run(main())
```

### 3.3 启动 worker

```bash
# 方式 A：用 CLI（推荐）
arq worker.WorkerSettings

# 方式 B：程序内启动
# python -c "import asyncio; from arq import run_worker; from worker import WorkerSettings; asyncio.run(run_worker(WorkerSettings))"
```

打开两个终端：一个跑 worker，一个跑 `producer.py`。你会在 worker 终端看到任务被消费。

---

## 第 4 节：任务管理进阶

### 4.1 带超时与重试的任务

ARQ 的重试是 **任务自己抛异常** 触发的：

```python
import asyncio
from arq import Retry

async def flaky_task(ctx, url: str):
    attempt = ctx["job_try"]         # 内置字段，第几次尝试
    if attempt < 3:
        raise Retry(defer=5)         # 5 秒后重试
    return f"第 {attempt} 次成功: {url}"
```

### 4.2 延迟执行与定时任务

```python
# 30 秒后执行
await redis.enqueue_job("send_email", "bob@x.com", "Hi", _defer_by=30)

# 每天 9 点执行（cron 表达式）
class WorkerSettings:
    cron_jobs = [
        arq.cron(send_email, hour=9, minute=0, args=("ops@x.com", "Daily")),
    ]
```

### 4.3 取结果

```python
job = await redis.enqueue_job("send_email", "c@x.com", "Hey")
result = await job.result(timeout=10)   # 阻塞等结果
print(result)
```

---

## 第 5 节：工程级实践

### 5.1 文件布局（推荐）

```
myproj/
├── tasks.py        # 定义所有 async 任务函数
├── settings.py     # WorkerSettings
├── producer.py     # 业务侧的入队入口
└── worker.py       # 只是 import WorkerSettings
```

### 5.2 常见工程要点

- **`ctx` 是状态总线**：把 DB pool、HTTP client 放进 `startup` 的 `ctx` 中，避免每个任务新建连接。
- **任务函数要幂等（idempotent）**：重试机制下，同一任务可能被执行多次，发邮件、扣款等操作要能去重。
- **序列化限制**：ARQ 默认用 `pickle`（老版本）或可配置 `pickle`/`json`。参数必须可序列化，不要传 ORM 对象，传 `id` 让 worker 自己查。
- **监控**：Redis 里 `arq:queue`、`arq:job:*` 等 key 就是全部运行状态，`redis-cli llen arq:queue` 能看一眼积压。
- **多 worker**：直接启动多个 `arq worker.WorkerSettings` 进程即可，靠 Redis 原子操作天然分流。
- **优雅退出**：`on_shutdown` 里关闭连接池、flush 日志。worker 收到 SIGTERM 后会等正在跑的任务结束（受 `job_timeout` 约束）。

### 5.3 FastAPI 中的典型用法

```python
from fastapi import FastAPI
from arq import create_pool
from arq.connections import RedisSettings

app = FastAPI()
redis = None

@app.on_event("startup")
async def _startup():
    global redis
    redis = await create_pool(RedisSettings())

@app.post("/signup")
async def signup(email: str):
    await redis.enqueue_job("send_email", email, "Welcome")
    return {"queued": True}         # 立刻返回，不等邮件
```

这就是开头那个痛点的正解。

---

## 动手练习

**目标：实现一个「图片处理队列」的最小闭环。**

需求：
1. 定义任务 `resize_image(ctx, image_id: int)`：模拟「读取 → 缩放 → 保存」三次 I/O（每次 `asyncio.sleep(1)`），并打印进度。
2. 任务第一次执行有人为 40% 概率失败，通过 `Retry` 最多重试 3 次。
3. 写一个 `producer.py`，一次入队 10 个不同 `image_id`，并打印所有 `job_id`。
4. 启动 `arq` worker，观察：
   - 同一时刻最多处理几个任务？（通过 `max_jobs=3` 控制）
   - 重试日志里能看到 `ctx["job_try"]` 从 1 递增。
5. 附加题：给 `send_email` 加一个 cron 任务，每天早上 8:00 给 `admin@example.com` 发一封「今日报告」。

**验收标准**：
- 10 个任务全部最终成功；
- worker 日志中每个任务的开始、结束时间可辨认；
- `redis-cli keys 'arq:*'` 能看到队列与结果 key。

**本地运行命令**：

```bash
docker run -d -p 6379:6379 redis:7
arq worker.WorkerSettings          # 终端 1
python producer.py                 # 终端 2
```


---

## 本课题目

### single_choice · None



- [A] 它会把任务消息发送到 broker，由 worker 进程异步执行，调用方立即得到一个 AsyncResult
- [B] 它会在当前进程中同步执行任务函数并返回计算结果
- [C] 它会直接抛出异常，因为任务函数不能被其他进程调用
- [D] 它会阻塞直到 worker 执行完毕并把返回值直接返回给调用方

**参考答案**：0

**解析**：delay 是 apply_async 的快捷方式，会把任务序列化后投递到 broker，立即返回 AsyncResult，不会等待结果。B 混淆了直接调用与 delay；C、D 误解了异步语义。

### single_choice · None



- [A] 计算两个整数的和并在页面上立刻显示
- [B] 用户注册后发送欢迎邮件，且邮件发送失败不应影响注册接口响应
- [C] 读取当前请求的 URL 路径并做路由匹配
- [D] 校验前端提交的表单字段是否为空

**参考答案**：1

**解析**：耗时或可能失败、且不要求同步返回的副作用类操作适合异步化；A、C、D 都是轻量且需要即时结果的操作，异步化反而增加复杂度。

### single_choice · None



- [A] 在任务函数里使用 while True: time.sleep(86400) 循环
- [B] 在系统中用 cron 每分钟调用一次 delay，并在代码里判断时间
- [C] 使用 Celery beat 配合 crontab 或 schedule 配置定时调度
- [D] 在 worker 启动命令中加上 --daily 参数

**参考答案**：2

**解析**：Celery beat 是内置的定时调度组件，支持 crontab 表达式。A 会长期占用一个 worker 槽位；B 可行但不属于 Celery 内建定时机制且实现繁琐；D 不存在该参数。

### single_choice · None



- [A] 所有子进程共享同一份全局变量，计数完全准确
- [B] 每个子进程有独立的全局变量副本，计数结果可能不符合预期
- [C] Celery 会自动把全局变量同步到 backend，不会出错
- [D] prefork 模式下任务只能串行执行，因此计数不会出错

**参考答案**：1

**解析**：prefork 使用多进程，进程间不共享内存，全局变量各自独立。A、C 误解了进程隔离；D 误以为 prefork 是串行的。

### single_choice · None



- [A] RabbitMQ
- [B] Redis
- [C] Amazon SQS
- [D] PostgreSQL 的 JSONB 字段

**参考答案**：3

**解析**：RabbitMQ、Redis、SQS 都是常见 broker 实现；数据库字段本身不是消息中间件，不能直接充当 broker（虽然结果可以存到数据库）。

### single_choice · None



- [A] apply_async 只能同步执行任务，delay 才是异步的
- [B] delay 是 apply_async 的简化形式，apply_async 支持更多参数如 countdown、eta
- [C] 两者完全等价，没有任何区别
- [D] delay 会把结果直接写入数据库，apply_async 不会

**参考答案**：1

**解析**：delay(*args) 等价于 apply_async(args)，命名参数不通过 delay 传递；apply_async 支持 countdown、eta、queue、routing_key 等。A 把两者语义弄反；C、D 与事实不符。

### single_choice · None



- [A] 普通函数只有在被 @app.task 装饰后才会随任务重试而重复执行
- [B] 普通函数在任务函数体内部被调用，任务重试时其函数体会再次执行
- [C] 普通函数必须注册到 backend 才能被执行
- [D] 普通函数会自动变成 Celery 任务

**参考答案**：1

**解析**：重试是重新执行整个任务函数体，函数体内调用的普通函数自然也会再次执行。A 把函数内调用与注册任务混淆；C、D 与事实不符。

### single_choice · None



- [A] backend 中结果存储空间不足
- [B] 没有任何 worker 进程启动，或 worker 监听的路由与任务投递的队列不一致
- [C] 任务函数返回了 None
- [D] 任务函数使用了 @app.task 装饰器

**参考答案**：1

**解析**：消费依赖 worker 订阅相应队列。A 会影响结果查询但不阻止消费；C 返回 None 是正常情况；D 是使用任务的正常方式。

### single_choice · None



- [A] 它表示任务在投递到 broker 时立即确认，因此绝不会重复执行
- [B] 它表示任务在 worker 执行完成后才确认消息，可能提高可靠性但也更易重复执行
- [C] 它决定任务结果被保存到 backend 的时间
- [D] 它只对定时任务有效，对普通任务无影响

**参考答案**：1

**解析**：acks_late=True 使确认发生在执行后，worker 崩溃时任务可能被重新投递，从而重复执行，属于用幂等换可靠性。A 恰恰相反；C、D 与该配置无关。

### single_choice · None



- [A] 必须同时配置 BROKER_URL 和 RESULT_BACKEND，否则任务无法投递
- [B] 可以只配置 broker，不配置 backend；此时不要调用 result.get()
- [C] 必须把 backend 设置为 broker 的同一地址，否则会报错
- [D] 只能把结果写入本地文件，无法关闭结果存储

**参考答案**：1

**解析**：broker 是必需项，backend 只在需要查询结果或使用某些 canvas 特性时才需要。A 过于绝对；C 不是必要条件；D 也不准确。

### single_choice · None



- [A] get() 会返回第一个完成的任务的结果
- [B] get() 会返回按原顺序排列的结果列表，且会等待所有子任务完成
- [C] group 中的任务会串行执行，get() 返回最后一个结果
- [D] group 不能用于并行场景，只能配合 chain 使用

**参考答案**：1

**解析**：group 表示并行执行的一组任务，GroupResult.get() 会等待全部完成并返回对应顺序的结果。A 混淆了 first 语义；C、D 与 group 的设计目的相悖。

### single_choice · None



- [A] 因为 get() 会修改 backend 中的数据，导致结果丢失
- [B] 因为 get() 会阻塞当前请求线程，可能导致请求超时或吞吐下降
- [C] 因为 get() 只能在 worker 进程内调用，Web 进程中调用会报错
- [D] 因为 get() 会取消任务的执行

**参考答案**：1

**解析**：get() 是阻塞调用，在请求线程中长时间等待会占用连接与线程资源。A、C、D 都是对 get() 行为的臆造。

### single_choice · None



- [A] broker 负责存储任务执行结果，backend 负责传递任务消息
- [B] broker 和 backend 必须是同一个服务，否则任务无法执行
- [C] broker 负责传递任务消息，backend 负责存储任务执行结果（若需要获取结果）
- [D] backend 负责传递任务消息，broker 负责定时调度任务

**参考答案**：2

**解析**：broker（如 Redis、RabbitMQ）承担消息传输；backend 用于保存结果供 AsyncResult 查询。A、D 把两者职责颠倒，B 误以为二者必须相同。

### single_choice · None



- [A] worker 启动时会根据配置中的 include/imports 或自动发现规则导入任务模块
- [B] worker 会在每个任务消息到达时，从消息中携带的源码动态执行任务
- [C] 任务函数必须在 broker 中注册后才能被 worker 找到
- [D] worker 只能执行与自身同一文件内定义的任务

**参考答案**：0

**解析**：worker 需要预先导入定义任务的模块，通常通过 Celery(include=[...]) 或 autodiscover_tasks 等完成。B 混淆了消息与源码；C、D 与框架机制不符。

### single_choice · None



- [A] r.get() 会在当前进程内直接算出 5 并返回
- [B] 任务被自动改为同步执行，r.get() 正常返回 5
- [C] r.get() 会一直阻塞等待结果，直到超时（若设置了 timeout）或永久等待
- [D] delay 会立即抛出异常，因此根本拿不到 r

**参考答案**：2

**解析**：消息已进入 broker 但没有 worker 消费，结果不会产生，get() 会阻塞等待。A、B 混淆了本地调用与任务执行；D 只在 broker 不可达等情况下才可能失败，消息成功入队不会立刻抛错。

### single_choice · None



- [A] 任务参数会被 pickle 序列化后经 broker 传输，因此传入不可序列化的对象可能失败
- [B] 任务参数通过共享内存传递给 worker，因此可以传任意 Python 对象
- [C] 任务参数只支持字符串类型，其他类型会被自动转成字符串
- [D] 任务参数由 worker 直接读取调用方的局部变量，无需序列化

**参考答案**：0

**解析**：消息需要序列化（默认 JSON，可配置 pickle 等），不可序列化对象会导致投递或消费失败。B、D 误解了跨进程通信方式；C 过于绝对，JSON 也支持数字、列表等。

### single_choice · None



- [A] 在任务函数里写 for 循环调用自身 3 次
- [B] 使用任务对象的 retry 方法或 autoretry_for 配置，并设置 max_retries
- [C] 把任务装饰器的 name 改成 retry_3_times
- [D] 在 worker 启动命令后加 --retry-3

**参考答案**：1

**解析**：Celery 提供 self.retry()/retry() 与 autoretry_for、max_retries 等机制。A 会造成同步递归且丢失异步语义；C 只改名字无实际作用；D 不存在这样的启动参数。

### single_choice · None



- [A] Celery 保证每个任务消息只会被消费一次，所以任务天然幂等
- [B] 默认情况下任务可能因 worker 崩溃后重新入队等原因被多次执行，业务需自行保证幂等
- [C] 只有在 broker 使用 RabbitMQ 时才可能重复执行，Redis 不会
- [D] 只要设置了 acks_late=False 就绝对不会重复执行

**参考答案**：1

**解析**：Celery 默认是 at-least-once 语义，重试、确认时机、worker 崩溃等都可能导致重复执行。A、C、D 都是对投递语义的常见误解。

### single_choice · None



- [A] 按顺序写这两行 delay 调用即可保证先后执行
- [B] 使用 chain(task_a.s(), task_b.s())() 构造任务链
- [C] 在两个 delay 之间插入 time.sleep(1) 来保证顺序
- [D] 把两个任务写在同一个模块中即可自动串行

**参考答案**：1

**解析**：delay 只是投递消息，两个 worker 可并行消费，无法保证顺序。chain 等 canvas 原语用于表达任务依赖。A、C、D 都误以为投递顺序或代码位置能决定执行顺序。

### single_choice · None



- [A] 字符串
- [B] 整数
- [C] 打开的数据库连接对象
- [D] 由基本类型组成的列表

**参考答案**：2

**解析**：数据库连接、文件句柄、socket 等包含不可序列化的运行时状态，不能跨进程传递；字符串、整数和基本类型列表在 JSON 下都可序列化。

### single_choice · None



- [A] 它决定了同时可以投递到 broker 的消息总数上限
- [B] 它决定了单个 worker 进程/线程池中并发执行任务的槽位数量
- [C] 它等于 broker 中队列的数量
- [D] 它控制任务结果在 backend 中的保存时长

**参考答案**：1

**解析**：concurrency 是 worker 的并发度，例如 prefork 模式下的子进程数。A 混淆了队列长度与并发；C 与队列数量无关；D 对应 result_expires 之类的配置。

### single_choice · None



- [A] arq 基于 asyncio，Worker 与任务函数都是协程，依赖 Redis 存储队列与状态
- [B] arq 基于多线程，任务函数必须是普通同步函数
- [C] arq 不需要任何外部存储，任务全部在进程内内存队列中排队
- [D] arq 的任务只能用 celery 的协议序列化，且必须配合 RabbitMQ 使用

**参考答案**：0

**解析**：arq 的定位就是 asyncio 原生的任务队列，Worker 以事件循环运行，任务函数是协程，队列与结果状态都放在 Redis 里。B 错在把 asyncio 说成多线程；C 忽略了 Redis 这一必需依赖；D 是把 celery 的生态强行安到 arq 上。

### single_choice · None



- [A] 通过 WorkerSettings 类集中声明 functions、redis_settings 等配置，再用 arq 命令行或 Worker 对象启动
- [B] 通过继承 threading.Thread 并重写 run 方法启动
- [C] 通过装饰器把一个函数直接注册成操作系统守护进程
- [D] 通过 asyncio.create_task 直接创建，无需任何配置

**参考答案**：0

**解析**：arq 的惯用做法是定义一个 WorkerSettings 类，把任务函数列表 functions、Redis 连接配置 redis_settings、队列名、并发数等写在里面，随后用 arq 命令或以编程方式构造 Worker 启动。其余选项描述的机制并不存在于 arq 的启动模型中。

### multi_choice · None



- [A] arq 原生基于 asyncio，任务函数是协程；celery 传统上以同步任务为主
- [B] arq 依赖 Redis 作为 broker/结果存储；celery 支持多种 broker（如 RabbitMQ、Redis）
- [C] arq 属于轻量级异步任务队列，配置集中在 WorkerSettings 中
- [D] arq 的功能与 celery 完全等价，可以无缝互相替换任务定义

**参考答案**：[0, 1, 2]

**解析**：arq 是 asyncio 原生、以 Redis 为核心、以 WorkerSettings 集中配置的轻量异步队列；celery 支持多 broker 且以同步任务为主。D 错在“完全等价、无缝替换”，二者的任务定义与配置模型并不通用。

### multi_choice · None



- [A] functions：注册可被 Worker 执行的任务函数列表
- [B] redis_settings：Redis 连接参数
- [C] max_jobs：单个 Worker 的并发任务上限
- [D] queue_name：指定监听的队列名
- [E] thread_count：操作系统级线程池大小，arq 强制要求配置

**参考答案**：[0, 1, 2, 3]

**解析**：functions、redis_settings、max_jobs、queue_name 都是 arq 配置中的常见项。thread_count 并非 arq 的强制配置项，arq 基于 asyncio 而非以线程池为核心。

### multi_choice · None



- [A] 对可能长时间等待的操作设置合理超时，避免任务无期限挂起
- [B] 捕获 asyncio.CancelledError 时做必要的清理后再按需抛出
- [C] 任务中打开的外部资源（连接、文件等）在 finally 中释放
- [D] 依赖 Worker 强制杀进程来回收资源，任务代码里无需处理清理

**参考答案**：[0, 1, 2]

**解析**：超时设置、对取消异常的合理处理、finally 中释放资源，都是应对取消/超时的正确实践。把资源回收完全交给进程被杀会导致泄漏或状态不一致，是错误做法。

### fill_blank · None



**参考答案**：["functions", "WorkerSettings.functions", "functions 属性"]

**解析**：arq 通过 WorkerSettings 的 functions 属性登记任务函数，只有出现在该列表中的函数名才能被 enqueue_job 使用。

### fill_blank · None



**参考答案**：["ctx", "上下文 ctx", "context", "ctx（上下文对象）"]

**解析**：arq 任务函数签名约定第一个参数是上下文对象，惯例命名为 ctx。通过它访问 redis、job_id、job_try 等信息。

### code_reading · None



**参考答案**：Worker 会调用 add(ctx, 3, 5)：ctx 为 Worker 注入的任务上下文对象，a=3、b=5；函数返回 8，该返回值会作为任务结果写入 arq 的结果存储，可被调用方查询。

**解析**：enqueue_job 的第一个参数是任务函数名，其后按位置传入业务参数，arq 在调度执行时会自动把上下文对象作为位置参数 0 注入，因此业务参数 a、b 分别对应 3 和 5，返回值 8 作为任务结果保存。

### code_reading · None



**参考答案**：当任务被执行的次数（job_try）小于 3 时抛出 Retry，任务会被延迟约 1 后重新入队执行；当尝试次数达到 3 时不再重试，直接返回 n*2 作为结果。即最多重试两次、第 3 次尝试时成功返回。

**解析**：arq 的任务上下文中 job_try 表示当前是第几次尝试；抛出 Retry 会按 defer 指定的延迟重新调度。job_try 从 1 开始计数，小于 3 时（第 1、2 次）重试，第 3 次满足条件直接返回。

### scenario · None



**解析**：核心是把不同优先级的任务拆到不同队列，用 queue_name 区分，并给关键队列分配独立 Worker（或调整 max_jobs 隔离并发额度），使慢任务无法挤占紧急任务的执行资源。

### scenario · None



**解析**：arq 基于 asyncio，任务函数必须是协程（async def），在协程中调用同步阻塞库（如 requests）会阻塞事件循环，导致并发无法提升甚至整个 Worker 卡住。改造方向是把任务函数改成协程，使用异步库或把阻塞调用放到线程池执行，同时保证 Redis 等连接复用。

### single_choice · None



- [A] 异常被 Worker 捕获并记录，任务被标记为失败，其它任务继续正常执行
- [B] 整个 Worker 进程崩溃退出，正在排队的任务全部丢失
- [C] 异常被静默吞掉，任务被当作成功完成写入结果
- [D] Worker 会无限重试该任务直到成功，不再处理其它任务

**参考答案**：0

**解析**：arq 中单个任务抛异常不会拖垮 Worker，异常会被捕获并记入日志，该次执行记为失败。不会静默当成功，也不会导致进程崩溃或无限重试（重试需显式配置）。

### single_choice · None



- [A] max_jobs
- [B] pool_size
- [C] num_workers
- [D] semaphore

**参考答案**：0

**解析**：WorkerSettings 中的 max_jobs 控制一个 Worker 在任一时刻并发执行的任务上限。pool_size 是数据库连接池概念，num_workers 是 arq 命令行的进程数参数，semaphore 不是 Worker 配置项。

### single_choice · None



- [A] async def send_email(ctx, user_id: int) -> str
- [B] def send_email(user_id: int) -> str
- [C] async def send_email() -> str（不接受任何参数）
- [D] async def send_email(ctx) -> str（只能有一个参数）

**参考答案**：0

**解析**：arq 的任务函数必须是协程，且第一个位置参数约定为上下文对象 ctx（承载 job_id、redis、重试次数等信息），之后才是业务参数。B 缺 async 与 ctx；C 缺 ctx 无法访问任务上下文；D 把 ctx 当成唯一参数也不对，业务参数是可选的。

### single_choice · None



- [A] 在任务内部抛出 arq 提供的重试异常（如 Retry），或依赖配置的 max_tries 在失败后重试
- [B] 只要任务返回 False 就会自动无限重试
- [C] 必须手动重新调用 enqueue_job 才算重试，没有内置机制
- [D] 在 Redis 里执行 RETRY 命令即可

**参考答案**：0

**解析**：arq 支持在协程里抛出 Retry 来主动要求重试，同时可通过 WorkerSettings 的 max_tries 等设置限定失败重试次数。返回值决定重试、无限重试、手动重试、Redis 命令重试都是常见误解。

### single_choice · None



- [A] 每个队列在 Redis 中以带前缀的 key 组织，默认队列名为 arq:queue，可通过 queue_name 配置
- [B] 队列是操作系统级别的命名管道，与 Redis 无关
- [C] 队列名必须是 UUID，不能使用 arq:queue 这种字符串
- [D] 队列名只影响日志输出，实际所有任务都进同一个全局列表

**参考答案**：0

**解析**：arq 用 Redis 中带前缀的 key 表示队列，默认队列名是 arq:queue，可用 queue_name 自定义。队列不是命名管道，不要求 UUID，队列名确实决定任务进哪个 key 列表，不是只影响日志。

### single_choice · None



- [A] 在入队时指定 _defer_by 或 _defer_until 等参数，任务先进入 Redis 的有序结构，到期后由 Worker 取走
- [B] 在任务函数里写 time.sleep(600) 阻塞当前 Worker
- [C] 开一个独立线程轮询时间，到点再手动调用函数
- [D] 延迟执行在 arq 中不被支持，必须借助外部定时器

**参考答案**：0

**解析**：arq 支持延迟任务：入队时用 _defer_by（相对时间）或 _defer_until（绝对时间），任务不立即进主队列而是按时间排序，到期后由 Worker 调度执行。sleep 阻塞会浪费并发额度，开线程或断言不支持都是误解。

### single_choice · None



- [A] 入队时会报错提示该函数未注册，任务不会进入队列
- [B] 入队成功，Worker 执行到该任务时会自动跳过且不留痕
- [C] 入队成功，Worker 执行时自动把函数名当作命令在系统 shell 中执行
- [D] 入队成功，并且会被自动注册为临时函数

**参考答案**：0

**解析**：arq 在入队阶段会检查函数名是否已注册（在 WorkerSettings.functions 中声明），未注册会直接报错，避免任务被静默丢弃。跳过、当 shell 执行、自动注册都不是 arq 的行为。

### single_choice · None



- [A] 通常通过任务第一个参数 ctx 拿到已连接的 redis 客户端（如 ctx['redis']）使用
- [B] 在任务里用 new Redis() 手动创建新连接，并保证不关闭
- [C] 任务函数不能访问 Redis，只能操作本地变量
- [D] 必须通过 os.system 调用 redis-cli 才能操作

**参考答案**：0

**解析**：arq 把复用的 redis 客户端放在任务上下文 ctx 中，任务直接用 ctx 里的连接即可，避免每次新建连接。手动 new 且不关闭会泄漏连接；说不能访问或必须用 redis-cli 都是误解。
