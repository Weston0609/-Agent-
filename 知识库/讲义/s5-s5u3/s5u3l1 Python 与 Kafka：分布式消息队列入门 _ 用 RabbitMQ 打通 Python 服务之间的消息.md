# s5u3l1 Python 与 Kafka：分布式消息队列入门 / 用 RabbitMQ 打通 Python 服务之间的消息

> 来源 `content/lessons/s5u3l1.json`

## py.mq.kafka

# Python 与 Kafka：分布式消息队列入门

> 一句话直觉：Kafka（分布式消息队列）就像一条永不断电的传送带，生产者往上面放包裹，消费者从上面取包裹，Python 用 `confluent-kafka` 库就能轻松接上这条传送带。

---

## 一、为什么需要 Kafka？

在没有消息队列（Message Queue）的世界里，服务 A 想通知服务 B，最直接的方式是「A 直接调用 B 的接口」。这会导致：

- **耦合**：B 挂了，A 也受影响。
- **洪峰**：双十一流量暴涨，B 直接被压垮。
- **丢数据**：B 重启期间 A 发的消息全丢了。

Kafka 用「**发布订阅（Pub/Sub）**」解决它：A 只管把消息写进 Kafka，B 按自己的节奏读。中间这条「传送带」叫做 **Topic（主题）**，消息按顺序追加，默认保留 7 天，可以反复消费。

---

## 二、Kafka 的四个核心概念

| 概念 | 英文 | 类比 |
|------|------|------|
| Topic | Topic | 传送带的名称，比如 `orders` |
| Producer | Producer | 往传送带上放包裹的人 |
| Consumer | Consumer | 从传送带上取包裹的人 |
| Partition | Partition | 传送带被切成 N 条并行通道，提升吞吐 |

一条消息在 Kafka 里长这样：

```
(key, value, timestamp, headers)   # value 通常是 JSON bytes
```

消费者通过 **消费组（Consumer Group）** 组织：同组内一条消息只被一个人消费（负载均衡），不同组之间互不影响（广播）。

---

## 三、Python 客户端选型

- **`kafka-python`**：纯 Python 实现，安装简单，但性能一般，维护不活跃。
- **`confluent-kafka`**（推荐）：基于 C 库 `librdkafka` 的官方封装，性能高、API 稳定、生产级。

安装：

```bash
pip install confluent-kafka
```

本地没有 Kafka？用 Docker 一键起一个单节点（KRaft 模式，不需要 ZooKeeper）：

```bash
docker run -d --name kafka -p 9092:9092 \
  apache/kafka:latest
```

---

## 四、最小可用示例：生产一条消息

```python
from confluent_kafka import Producer
import json

# 1. 创建生产者，bootstrap.servers 指向 broker 地址
producer = Producer({"bootstrap.servers": "localhost:9092"})

# 2. 投递回调：确认消息是否送达
def delivery_report(err, msg):
    if err is not None:
        print(f"投递失败: {err}")
    else:
        print(f"送达 topic={msg.topic()} partition={msg.partition()} offset={msg.offset()}")

# 3. 生产消息：key 决定分区，value 必须是 bytes
payload = json.dumps({"order_id": 1001, "amount": 99.9}).encode("utf-8")
producer.produce("orders", key=b"1001", value=payload, callback=delivery_report)

# 4. 每轮循环都要 poll，触发回调 + 发送缓冲区
producer.flush()   # 程序退出前确保全部发出
```

**关键点**：`produce()` 是异步的，不调用 `flush()` 或 `poll()`，消息可能还在本地缓冲区就退出了。

---

## 五、最小可用示例：消费一条消息

```python
from confluent_kafka import Consumer
import json

consumer = Consumer({
    "bootstrap.servers": "localhost:9092",
    "group.id": "order-worker",          # 同组的 consumer 平分分区
    "auto.offset.reset": "earliest",     # 无历史位点时从最早开始读
    "enable.auto.commit": False,         # 手动提交，避免丢消息
})

consumer.subscribe(["orders"])

try:
    while True:
        msg = consumer.poll(timeout=1.0)   # 阻塞最多 1 秒
        if msg is None:
            continue                        # 暂时没有新消息
        if msg.error():
            print(f"消费出错: {msg.error()}")
            continue

        data = json.loads(msg.value().decode("utf-8"))
        print(f"收到订单: {data} @ offset={msg.offset()}")

        # 业务处理成功后，再提交 offset（at-least-once 语义）
        consumer.commit(msg)
except KeyboardInterrupt:
    pass
finally:
    consumer.close()   # 优雅关闭，会离开消费组并触发 rebalance
```

**关键点**：

- `group.id` 相同的消费者会自动分摊分区，扩容时触发 **重平衡（Rebalance）**。
- 手动 `commit()` 保证「至少一次」；要「精确一次」需要事务 API，属于进阶话题。
- `consumer.close()` 必须调用，否则组内其他成员要等 session 超时才能接班。

---

## 六、把它放进工程：分层职责

```
[Web 服务] --produce--> [Kafka topic: orders] --consume--> [Worker 进程]
                                    |
                                    v
                            [下游: DB / 风控 / 推荐]
```

工程实践清单：

1. **序列化统一**：全公司用 JSON + UTF-8，或 Avro/Protobuf + Schema Registry。
2. **幂等**：消息可能重复（at-least-once），消费者用 `order_id` 做去重。
3. **监控**：暴露 consumer lag（积压量），lag 持续上涨就是处理不过来了。
4. **优雅退出**：捕获 `SIGTERM`，先 `close()` 再退出。
5. **配置外置**：`bootstrap.servers`、`group.id` 从环境变量读，不要硬编码。

---

## 七、小结

- Kafka = 分布式、可持久化、可回放的发布订阅系统。
- Python 首选 `confluent-kafka`，生产者异步投递 + flush，消费者轮询 + 手动提交。
- 生产环境关注三件事：**幂等、lag 监控、优雅关闭**。

## py.mq.rabbitmq

# py.mq.rabbitmq：用 RabbitMQ 打通 Python 服务之间的消息

> **一句话直觉**：当你的 Python 程序需要把任务「丢出去」让别的程序异步处理时，RabbitMQ（消息队列，Message Queue）就是那个可靠的中转站——生产者只管把消息投进队列，消费者按自己的节奏慢慢取，两边完全解耦。

---

## 1. 为什么需要消息队列？

假设你写了一个 Web 接口，用户下单后要发邮件、生成 PDF、通知仓库。如果全写在请求里同步执行，用户会等很久，任何一环挂了整条链都失败。

**消息队列（Message Queue，MQ）** 解决三个问题：

| 问题 | MQ 的答案 |
|------|-----------|
| 同步阻塞 | 生产者投递后立刻返回 |
| 服务耦合 | 双方只认消息格式，不认对方地址 |
| 流量峰值 | 队列做缓冲区，消费者按能力消费 |

RabbitMQ（Rabbit Message Queue）是最主流的开源 MQ 之一，实现了 **AMQP（Advanced Message Queuing Protocol，高级消息队列协议）**，用 Erlang 编写，稳定、生态好，Python 端官方库是 `pika`。

**核心角色（首次出现术语）**：

- **Producer（生产者）**：发消息的程序
- **Consumer（消费者）**：收消息的程序
- **Queue（队列）**：RabbitMQ 内部存消息的容器
- **Exchange（交换机）**：生产者实际投递的目标，由它按规则路由到队列
- **Binding（绑定）**：Exchange 与 Queue 之间的路由规则
- **Routing Key（路由键）**：消息上携带的标签，Exchange 用它做路由

---

## 2. 安装与最短可用示例

安装 Python 客户端：

```bash
pip install pika
```

本地跑一个 RabbitMQ（推荐 Docker）：

```bash
docker run -d --name rabbit -p 5672:5672 -p 15672:15672 rabbitmq:3-management
# 管理后台：http://localhost:15672  默认 guest/guest
```

下面是最小的「发一条 / 收一条」示例，用默认交换机（default exchange，名字为 `""`）直接按队列名投递：

```python
import pika

# 1. 建立连接（TCP）
connection = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
channel = connection.channel()

# 2. 声明队列：幂等操作，存在则复用
channel.queue_declare(queue="hello")

# 3. 发消息到默认交换机，routing_key 就是队列名
channel.basic_publish(
    exchange="",
    routing_key="hello",
    body=b"Hello RabbitMQ",
)
print("[x] sent")
connection.close()
```

```python
import pika

connection = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
channel = connection.channel()
channel.queue_declare(queue="hello")

# 回调：每收到一条就执行一次
def on_message(ch, method, properties, body):
    print(f"[x] received: {body!r}")

def on_message(ch, method, properties, body):
    print(f"[x] received: {body!r}")

channel.basic_consume(
    queue="hello",
    on_message_callback=on_message,
    auto_ack=True,  # 稍后会讨论：这里先设为自动确认
)
print("[*] waiting...")
channel.start_consuming()  # 阻塞循环
```

**结论**：队列名是双方约定的「地址」，`queue_declare` 是幂等的，双方都必须声明。

---

## 3. 消息确认（Ack）与可靠性

上面的 `auto_ack=True` 有个致命问题：消费者一拿到消息，RabbitMQ 立刻标记为已消费。如果消费者在回调里崩溃，这条消息就永久丢了。

**Ack（Acknowledgement，确认）** 是 RabbitMQ 保证「至少一次投递」的机制：消费者处理成功后手动告诉服务器「可以删了」。

```python
import pika, time

connection = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
channel = connection.channel()
channel.queue_declare(queue="tasks", durable=True)  # 队列持久化

def on_message(ch, method, properties, body):
    print(f"[x] processing: {body!r}")
    time.sleep(1)  # 模拟耗时任务
    # 手动 Ack：告诉 RabbitMQ 这条可以删了
    ch.basic_ack(delivery_tag=method.delivery_tag)

# 公平分发：一次只给消费者一条，处理完再给下一条
channel.basic_qos(prefetch_count=1)
channel.basic_consume(queue="tasks", on_message_callback=on_message)
channel.start_consuming()
```

生产者端如果要消息也持久化，需同时设置队列和消息的 durability：

```python
channel.basic_publish(
    exchange="",
    routing_key="tasks",
    body=b"long job",
    properties=pika.BasicProperties(delivery_mode=2),  # 2 = persistent
)
```

**结论**：生产端 `delivery_mode=2` + 队列 `durable=True` + 消费端手动 Ack，是 RabbitMQ 可靠投递的三件套。

---

## 4. Exchange 与路由模式

生产者几乎不直接发到队列，而是发给 Exchange，由 Exchange 决定去哪。常见的四种类型：

| 类型 | 路由规则 | 典型场景 |
|------|----------|----------|
| `direct` | routing_key 完全匹配 | 按任务类型分发 |
| `fanout` | 广播到所有绑定队列 | 日志、通知 |
| `topic` | 通配符匹配 `*`（一个词）和 `#`（任意词） | 按主题订阅 |
| `headers` | 按 headers 匹配 | 少用 |

**fanout（广播）示例**：多个消费者同时收到同一条消息。

```python
import pika

connection = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
channel = connection.channel()

# 声明一个 fanout 交换机
channel.exchange_declare(exchange="logs", exchange_type="fanout")

# 声明一个临时队列（exclusive=True：连接断开自动删除）
result = channel.queue_declare(queue="", exclusive=True)
queue_name = result.method.queue  # 随机生成的名字

# 绑定到交换机
channel.queue_bind(exchange="logs", queue=queue_name)

print(f"[*] waiting on {queue_name}")
channel.basic_consume(
    queue=queue_name,
    on_message_callback=lambda ch, m, p, b: print(f"[x] {b!r}"),
    auto_ack=True,
)
channel.start_consuming()
```

生产者只要往 `logs` 这个 fanout exchange 发消息，所有绑定过的队列都能收到一份。

**topic 模式**更能体现「选择性订阅」：

```python
# 绑定：只在 routing_key 形如 "kern.*" 时接收
channel.queue_bind(exchange="topic_logs", queue=queue_name, routing_key="kern.*")

# 生产者
channel.basic_publish(exchange="topic_logs", routing_key="kern.info", body=b"ok")
```

**结论**：Exchange 是 RabbitMQ 路由的灵魂，选对类型就能实现「点对点、广播、订阅」等模式。

---

## 5. 工程级封装建议

写进真实项目时，直接裸用 `pika` 会遇到：连接丢失、回调里抛异常、心跳超时。建议做最简封装：

```python
import pika, json, logging

log = logging.getLogger(__name__)

class MQClient:
    def __init__(self, host="localhost", queue="default", durable=True):
        self.queue = queue
        self.params = pika.ConnectionParameters(host=host, heartbeat=30)
        self.conn = pika.BlockingConnection(self.params)
        self.ch = self.conn.channel()
        self.ch.queue_declare(queue=queue, durable=durable)
        self.ch.basic_qos(prefetch_count=1)

    def publish(self, payload: dict, routing_key: str | None = None):
        self.ch.basic_publish(
            exchange="",
            routing_key=routing_key or self.queue,
            body=json.dumps(payload).encode(),
            properties=pika.BasicProperties(delivery_mode=2),
        )

    def consume(self, handler):
        def _wrap(ch, method, props, body):
            try:
                handler(json.loads(body))
                ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception:
                log.exception("handler failed, requeue")
                # 失败：不 ack，消息会重新入队（也可投递到死信队列）
        self.ch.basic_consume(queue=self.queue, on_message_callback=_wrap)
        self.ch.start_consuming()

    def close(self):
        if self.conn.is_open:
            self.conn.close()
```

真实生产还要考虑：

- **消息幂等**：至少一次投递意味着可能重复，消费端要有去重（唯一 ID）。
- **死信队列（DLX，Dead Letter Exchange）**：处理失败多次的消息转出去，别卡住主队列。
- **心跳与重连**：长连接会因网络/空闲被断开，`pika` 里可通过 `ConnectionParameters(heartbeat=N)` 配合外层重试循环。

**结论**：把 ack、序列化、异常处理封装到一个小类里，业务代码就只关心 `publish` 和 `consume`。

---

## 动手练习

**目标**：写一个「订单处理」小系统，练习 direct exchange 路由与手动 ack。

**任务**：

1. 在 RabbitMQ 中声明一个 direct exchange，名字 `orders`。
2. 创建两个队列：`orders.pay`、`orders.ship`。
3. 分别用 routing_key `pay` 和 `ship` 把它们绑定到 `orders` 上。
4. 写一个生产者 `producer.py`，从命令行接收订单号与类型，把消息发到对应 routing_key：

   ```bash
   python producer.py ORDER-001 pay
   python producer.py ORDER-002 ship
   ```

   消息体用 JSON：`{"order_id": "ORDER-001", "action": "pay"}`。

5. 写两个消费者：`consumer_pay.py` 只监听 `orders.pay`，`consumer_ship.py` 只监听 `orders.ship`。
   - 消费端打印订单号，**必须手动 ack**。
   - 用 `prefetch_count=1`。

6. **进阶**：在 `consumer_pay.py` 里加一行 `raise RuntimeError("boom")` 模拟失败，观察消息是否会被反复投递。然后把它改为投递到死信队列（提示：在 `queue_declare` 时加 `arguments={"x-dead-letter-exchange": "orders.dlx"}`，并提前声明 `orders.dlx`）。

**验收**：

- 启动两个消费者，用生产者分别发不同 routing_key，观察只有对应消费者收到。
- 在管理后台 `http://localhost:15672` 看到两个队列的 Ready / Unacked / Total 数字变化。

完成后你已经掌握 RabbitMQ 在 Python 里最核心的 90% 用法。


---

## 本课题目

### single_choice · None



- [A] producer.send('topic', value=b'msg', callback=lambda *a: None).get()
- [B] producer.send('topic', b'msg').add_callback(lambda *a: None)
- [C] producer.send('topic', b'msg') 后立即调用 producer.flush() 以保证回调被触发
- [D] producer.poll(0) 会阻塞直到回调执行完毕

**参考答案**：2

**解析**：常见客户端在 send 返回后不会立即触发回调，需要 poll/flush 推动回调执行。选项 C 提示 flush 保证回调被触发；A 的 get 是同步阻塞语义不一致；B 的写法在 kafka-python 中并不存在 add_callback；D 混淆了 poll 语义。

### single_choice · None



- [A] 同一个消费者组内，一个分区可以被多个消费者同时消费
- [B] 不同消费者组各自独立消费同一主题，互不影响
- [C] 消费者组仅在手动提交偏移量时才会生效
- [D] 一个主题的分区数必须大于消费者组数量

**参考答案**：1

**解析**：消费者组与分区是一对多关系：组内一个分区同一时刻只由一个消费者消费，但不同组的消费互不影响。A 错在组内会被拆分；C 与偏移量提交方式无关；D 没有此限制。

### single_choice · None



- [A] 每个消费者都会分到至少一个分区
- [B] 部分消费者处于空闲状态，不会分到分区
- [C] Kafka 会自动增加分区以匹配消费者数量
- [D] 消费者组会拒绝新消费者加入

**参考答案**：1

**解析**：分区数决定组内并行度上限，多出的消费者会空闲。Kafka 不会自动扩分区，也不会拒绝加入。

### single_choice · None



- [A] 生产者不等待任何确认
- [B] 仅等待 leader 写入本地日志即返回
- [C] 等待所有同步副本确认后才认为发送成功
- [D] 等待消费者确认后再返回

**参考答案**：2

**解析**：acks='all' 表示等待 ISR 中所有副本确认，可靠性最高。A 是 acks=0；B 是 acks=1；D 混淆了消费者确认。

### single_choice · None



- [A] Kafka 自动丢弃该消息并继续
- [B] 消费者循环中断，偏移量提交状态取决于提交时机
- [C] broker 自动重发到其它分区
- [D] 该分区被永久关闭

**参考答案**：1

**解析**：异常未捕获会中断消费循环；是否会重复消费取决于提交时机。Kafka 不会自动丢弃或重发到其它分区，分区也不会被关闭。

### single_choice · None



- [A] 一个 topic 只能有一个 partition
- [B] 一个 partition 可以属于多个 topic
- [C] 一个 topic 由多个 partition 组成，partition 是并行与有序的基本单位
- [D] partition 是逻辑概念，topic 是物理概念

**参考答案**：2

**解析**：topic 逻辑上由多个 partition 组成，partition 提供并行度与分区内有序性。A、B 与事实相反；D 说反了。

### single_choice · None



- [A] 当没有已提交偏移量时，从分区最早的消息开始消费
- [B] 每次启动都从最早消息重新消费
- [C] 忽略已提交偏移量，总是从头开始
- [D] 只在手动提交模式下生效

**参考答案**：0

**解析**：auto_offset_reset 仅在无有效已提交偏移量（或越界）时生效，earliest 表示从最早可用消息开始。B、C 误解为总是从头；D 与提交模式无关。

### single_choice · None



- [A] 生产者发送速率过高
- [B] 消费者加入、离开或会话超时导致组内成员变化
- [C] 主题的消息数量达到上限
- [D] broker 的磁盘使用率超过阈值

**参考答案**：1

**解析**：再均衡由消费者组成员变化或订阅变化等触发，用于重新分配分区。A、C、D 不是再均衡的触发条件。

### single_choice · None



- [A] Kafka 消息只能发送字符串
- [B] 生产者的 value_serializer 负责把对象转换为字节
- [C] 消费者不需要反序列化即可直接得到原始对象
- [D] 序列化由 broker 完成

**参考答案**：1

**解析**：序列化在客户端完成，生产者把对象转字节，消费者把字节还原。A 错误；C 反序列化是必需的；D 与 broker 无关。

### single_choice · None



- [A] 设置 max_in_flight_requests_per_connection 很大并开启重试
- [B] 对同一 key 使用相同分区策略，并避免并发乱序重试
- [C] 关闭 acks 以提高吞吐
- [D] 把消息全部发送到不同主题

**参考答案**：1

**解析**：分区内有序的前提是相同 key 路由到同一分区，且并发/重试不破坏顺序。A 反而可能乱序；C 影响可靠性；D 与分区有序无关。

### single_choice · None



- [A] 告诉 broker 该消费者已经处理到哪个位置
- [B] 删除已消费的消息
- [C] 增加主题的分区数
- [D] 提升生产者的发送速度

**参考答案**：0

**解析**：提交偏移量用于记录消费进度，供重启/再均衡后继续消费。Kafka 不会因提交而立即删除消息，也与分区数、生产者速度无关。

### single_choice · None



- [A] 先提交偏移量再处理消息
- [B] 处理完成后才提交偏移量，且提交前发生异常重启
- [C] 使用 acks=all
- [D] 消费者组 id 与生产者相同

**参考答案**：1

**解析**：先处理后提交是“至少一次”语义，异常重启会导致重复消费。A 会导致丢失；C 是生产者可靠性配置；D 无此关联。

### single_choice · None



- [A] 消息会重复消费（至少一次语义）
- [B] 消息会丢失（至多一次语义）
- [C] 消费者会自动跳过失败的消息
- [D] 分区分配会被重新触发

**参考答案**：0

**解析**：先处理后提交，若处理完成但提交前崩溃，重启后会从上次提交处重新消费，因此是“至少一次”。B 对应先提交后处理；C、D 与该顺序无直接关系。

### single_choice · None



- [A] 分区数越少，整体吞吐一定越高
- [B] 同一消费者组内，分区数决定了最大并行消费度
- [C] 分区内消息是无序的，跨分区才有序
- [D] 分区数只能在创建主题时设定，之后不可调整

**参考答案**：1

**解析**：一个分区同一时刻只能被组内一个消费者消费，因此并行度上限受分区数限制。A 相反；C 说反了，分区内有序、跨分区无序；D 分区数通常可以增加（虽然不减少）。

### single_choice · None



- [A] Kafka 默认不做 key 到分区的映射
- [B] 生产者的分区器对 key 做哈希后选择分区
- [C] 消费者组根据 key 重新排序
- [D] 消息的 headers 中自动包含分区号

**参考答案**：1

**解析**：生产者默认分区器会对 key 进行哈希，从而把相同 key 路由到同一分区。A 错误；C 是消费侧、与写入顺序无关；D 混淆 headers 与分区元数据。

### single_choice · None



- [A] 标识整个 Kafka 集群
- [B] 决定该消费者属于哪个消费者组，从而影响分区分配
- [C] 指定从哪个主题读取消息
- [D] 设置消费者与 broker 之间的网络超时

**参考答案**：1

**解析**：group_id 是消费者组标识，用于分区分配与偏移量存储。A 是集群概念；C 是 topic 参数；D 是连接配置。

### single_choice · None



- [A] 为了强制消费者提交偏移量
- [B] 为了与 broker 保持心跳、拉取消息并触发协调逻辑
- [C] 为了主动关闭网络连接
- [D] 为了重新创建消费者实例

**参考答案**：1

**解析**：消费者需要 poll 来拉取数据并维持会话心跳，否则可能被判定为离线而触发再均衡。A 与提交偏移量无必然关系；C、D 不是 poll 的目的。

### single_choice · None



- [A] 消费者尚未启动
- [B] 生产者缓冲区中的消息尚未发送，需要 flush 或等待发送完成
- [C] 主题分区数太少
- [D] 消息 key 重复

**参考答案**：1

**解析**：生产者通常批量、异步发送，进程退出前若未 flush，缓冲区消息可能丢失。A、C、D 与该现象不直接对应。

### single_choice · None



- [A] offset 在整个主题内全局唯一且连续
- [B] offset 在每个分区内单调递增
- [C] offset 由消费者分配
- [D] offset 与分区无关，可跨分区比较大小

**参考答案**：1

**解析**：offset 是分区内的位置标识，分区内单调递增，跨分区不可直接比较。A 错在“主题内全局”；C 由 broker 分配；D 与分区无关的说法错误。

### single_choice · None



- [A] 消息永远不会重复
- [B] 消息可能在处理完成前就被提交，导致丢失
- [C] 分区不会被分配给该消费者
- [D] 消费者将无法加入消费者组

**参考答案**：1

**解析**：自动提交按时间间隔进行，可能在业务处理完成前提交，从而在崩溃时丢失消息。A 过于绝对；C、D 与提交方式无关。

### single_choice · None



- [A] 队列名称
- [B] 路由键（Routing Key）和交换机名称
- [C] 消费者 ID
- [D] 消息优先级

**参考答案**：1

**解析**：RabbitMQ 中生产者将消息发布到交换机，并附带一个路由键。交换机根据自身类型和绑定规则决定将消息路由到哪些队列。生产者通常不直接指定队列名称（除非使用默认交换机且路由键等于队列名）。

### single_choice · None



- [A] 消息会被自动丢弃
- [B] 消息会被路由到该队列（如果使用默认交换机）
- [C] 消息会被退回给生产者并报错
- [D] 消息会进入死信队列

**参考答案**：1

**解析**：RabbitMQ 有一个默认交换机（名称为空字符串），它会自动将消息路由到与路由键同名的队列。因此，如果生产者使用默认交换机并指定路由键为队列名，消息会进入该队列。

### single_choice · None



- [A] 消费者处理完消息后需要手动发送 ack
- [B] 消息一旦被消费者接收就自动确认，无需手动 ack
- [C] 消息发送失败时自动重试
- [D] 队列自动删除已确认的消息

**参考答案**：1

**解析**：auto_ack=True 表示自动确认模式：RabbitMQ 将消息发送给消费者后立即认为消息已被确认并删除，不等待消费者处理完成。如果消费者处理失败，消息会丢失。

### multi_choice · None



- [A] fanout 交换机会将消息广播到所有绑定的队列
- [B] direct 交换机根据路由键与绑定键的完全匹配进行路由
- [C] topic 交换机支持通配符 * 和 # 进行模式匹配
- [D] headers 交换机根据消息头属性进行匹配，忽略路由键
- [E] fanout 交换机支持路由键通配符匹配

**参考答案**：[0, 1, 2, 3]

**解析**：fanout 广播到所有绑定队列，忽略路由键；direct 精确匹配；topic 支持 * 和 # 通配符；headers 根据消息头匹配。fanout 不支持通配符，因此第 5 项错误。

### multi_choice · None



- [A] 将队列声明为 durable
- [B] 将消息设置为持久化（delivery_mode=2）
- [C] 消费者使用手动 ack 并在处理成功后确认
- [D] 使用 auto_ack=True 自动确认消息
- [E] 在生产端启用发布确认（publisher confirms）

**参考答案**：[0, 1, 2, 4]

**解析**：队列持久化、消息持久化、手动 ack、发布确认都能提高可靠性。auto_ack=True 会在消息接收时立即确认，若消费者处理失败消息会丢失，降低可靠性。

### multi_choice · None



- [A] 消息被消费者 basic_reject 且 requeue=False
- [B] 消息在队列中过期（TTL 到期）
- [C] 队列达到最大长度，新消息被丢弃
- [D] 消息被成功确认
- [E] 消息被路由到不存在的队列

**参考答案**：[0, 1, 2]

**解析**：死信的三个常见原因：被拒绝且不重新入队、消息过期、队列超长。成功确认的消息会被删除，不会成为死信；路由到不存在的队列时消息会被丢弃或退回，但不会进入死信队列（除非配置了备用交换机）。

### fill_blank · None



**参考答案**：["零个或多个", "0个或多个", "0或多个", "任意个", "零或多", "0或多"]

**解析**：topic 交换机中 `#` 匹配零个或多个单词，`*` 匹配恰好一个单词。因此 `#.error` 可以匹配 `error`（零个单词）、`app.error`（一个单词）等。

### fill_blank · None



**参考答案**：["True", "true", "真", "是"]

**解析**：将 requeue 设置为 True 表示消息被拒绝后重新放回队列，可能被其他消费者消费；设置为 False 则消息可能进入死信队列或被丢弃。

### fill_blank · None



**参考答案**：["localhost", "127.0.0.1", "本机", "本地"]

**解析**：RabbitMQ 默认监听 5672 端口，本地运行时主机名通常为 localhost 或 127.0.0.1。

### code_reading · None



**参考答案**：消息会被同时路由到 q1 和 q2 两个队列，因为 fanout 交换机会将消息广播到所有绑定的队列。

**解析**：fanout 类型的交换机会忽略 routing_key，将消息投递到所有与之绑定的队列。这里 q1 和 q2 都绑定到了 logs 交换机，因此两者都会收到消息。

### code_reading · None



**参考答案**：第二次调用会抛出错误（如 PRECONDITION_FAILED），因为已存在的队列属性与声明参数不匹配。RabbitMQ 不允许用不同属性重新声明同名队列。

**解析**：RabbitMQ 中队列声明是幂等的，但前提是参数完全一致。如果尝试用不同的 durable 值重新声明同名队列，会返回通道级错误，导致连接关闭。

### scenario · None



**解析**：问题原因：消费者处理能力不足导致消息堆积；消费者超时断开且消息未确认，重新入队形成恶性循环。改进措施：设置合理的 prefetch_count 限制未确认消息数量；使用手动 ack 并在处理成功后确认；对失败消息设置重试次数并转入死信队列，避免无限重入队；增加消费者数量或优化处理逻辑。

### single_choice · None



- [A] fanout
- [B] direct
- [C] topic
- [D] headers

**参考答案**：1

**解析**：direct 类型的交换机会将消息路由到绑定键与路由键完全相等的队列。fanout 会忽略路由键广播到所有绑定队列；topic 支持通配符匹配；headers 根据消息头属性匹配。

### scenario · None



**解析**：应选择 fanout 类型的交换机，因为它会将消息广播到所有与之绑定的队列。每个下游系统声明自己的队列并绑定到该交换机，这样每个下游都能独立收到全部日志消息，互不影响。如果使用 direct 或 topic，则需要为每个下游配置相同的路由键，但 fanout 更简单直接，适合广播场景。

### single_choice · None



- [A] app.error.log
- [B] app.error
- [C] error.app
- [D] app.error.log.detail

**参考答案**：1

**解析**：topic 交换机中 `*` 匹配一个单词，`#` 匹配零个或多个单词。绑定键 `*.error` 要求路由键正好是两个单词且第二个是 error。`app.error` 符合；`app.error.log` 有三个单词；`error.app` 顺序不对；`app.error.log.detail` 单词数更多。

### single_choice · None



- [A] 消息被自动确认并删除
- [B] 消息会重新入队并可能被其他消费者消费
- [C] 消息会进入死信队列
- [D] 消息会永久丢失

**参考答案**：1

**解析**：当消费者未发送 ack 就断开连接时，RabbitMQ 会认为消息未被成功处理，将其重新入队（redeliver），可能被其他消费者消费。这保证了消息至少被处理一次。

### single_choice · None



- [A] 表示使用默认交换机，消息会路由到 routing_key 指定的队列
- [B] 表示没有交换机，消息直接发送到队列
- [C] 表示使用 fanout 交换机
- [D] 这是错误用法，必须指定交换机名称

**参考答案**：0

**解析**：空字符串 `''` 是 RabbitMQ 默认交换机的名称。默认交换机会将消息路由到与 routing_key 同名的队列。因此这里消息会进入 task_queue 队列。

### single_choice · None



- [A] 设置消息的优先级为 1
- [B] 限制消费者最多同时处理 1 条未确认的消息
- [C] 设置队列的最大长度为 1
- [D] 设置消息的过期时间为 1 秒

**参考答案**：1

**解析**：prefetch_count 用于设置消费者同时最多接收但未确认的消息数量。设置为 1 表示消费者一次只处理一条消息，处理完并确认后才会收到下一条，常用于实现公平分发。

### single_choice · None



- [A] 消息被消费者成功确认
- [B] 消息被拒绝（basic_reject 或 basic_nack）且 requeue=false
- [C] 消息被路由到多个队列
- [D] 消息被持久化

**参考答案**：1

**解析**：消息进入死信队列的常见原因包括：被消费者拒绝且不重新入队、消息过期（TTL）、队列达到最大长度。成功确认的消息会被删除；路由到多个队列与死信无关；持久化是消息存储方式。

### single_choice · None



- [A] 消息仍然存在，因为队列是持久的
- [B] 消息会丢失，因为消息本身没有持久化
- [C] 消息会被自动转移到其他队列
- [D] 消息会被自动重新发布

**参考答案**：1

**解析**：队列持久化（durable）只保证队列本身在重启后存在，但不保证队列中的消息不丢失。要让消息在重启后仍然存在，必须同时将消息标记为持久化（delivery_mode=2）。

### single_choice · None



- [A] 队列只能由声明它的连接使用，连接关闭后队列自动删除
- [B] 队列是持久的，重启后仍然存在
- [C] 队列会自动转发消息到其他队列
- [D] 队列只能被一个消费者消费

**参考答案**：0

**解析**：exclusive=True 表示队列是排他的，仅对声明它的连接可见，并且在该连接关闭时自动删除。常用于临时队列（如 RPC 回调队列）。
