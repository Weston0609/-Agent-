# s8u5l1 架构系统：聊天应用（Chat Application） / 从零搭建一个 RAG 平台

> 来源 `content/lessons/s8u5l1.json`

## arch.sys.chat_app

# 架构系统：聊天应用（Chat Application）

## 一句话直觉

聊天应用（Chat Application）是理解**实时通信、并发连接、状态管理**的最小工程载体——学会它，你就掌握了后端架构的半壁江山。

---

## 第一节：什么是聊天应用？为什么从它入门架构？

聊天应用（Chat Application）是一个允许多个用户通过**网络（Network）**实时或近实时交换**消息（Message）**的系统。它看起来简单，却天然包含分布式系统的核心难题：

- **并发（Concurrency）**：多个客户端同时在线
- **状态（State）**：谁在线、消息历史、房间成员
- **协议（Protocol）**：客户端与服务端如何对话
- **持久化（Persistence）**：消息要不要存、存哪里

因此，它是学习架构（Architecture）的最佳起点。

最原始的聊天模型是 **C/S 架构（Client/Server）**：客户端连接服务端，服务端维护所有连接并转发消息。

```python
# 最朴素的聊天数据结构：一个内存中的“消息列表”
messages = []  # 全局状态：所有消息

def send_message(user, text):
    """模拟一条消息的发送过程。"""
    messages.append({"user": user, "text": text})  # 追加消息
    return messages[-1]  # 返回刚加入的消息

# 试运行
send_message("Alice", "你好")
send_message("Bob", "嗨！")
print(messages)
# [{'user': 'Alice', 'text': '你好'}, {'user': 'Bob', 'text': '嗨！'}]
```

**关键结论**：聊天应用的核心抽象是“消息”与“连接”。先把这两者建模清楚，再谈网络与并发。

---

## 第二节：从单机到网络——用 Socket 建立连接

要让两台机器对话，需要 **套接字（Socket）**。它是操作系统提供的网络编程接口。Python 的 `socket` 模块来自标准库，按 PEP 8 应放在 import 分组的第一组（标准库）。

服务端流程：绑定地址 → 监听 → 接受连接 → 收发数据。

```python
import socket  # 标准库导入，应在文件顶部

def start_server(host="127.0.0.1", port=9000):
    """启动一个最简单的 TCP 聊天服务端。"""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))   # 绑定地址
    server.listen(5)            # 监听，最多挂起 5 个连接
    print(f"服务端已启动: {host}:{port}")

    conn, addr = server.accept()   # 阻塞等待一个客户端
    print("客户端已连接:", addr)
    data = conn.recv(1024)         # 最多收 1024 字节
    print("收到:", data.decode("utf-8"))
    conn.sendall(b"server received\n")  # 回执
    conn.close()
    server.close()

# start_server()  # 本地运行时取消注释
```

客户端对称地使用 `connect` 与 `sendall`：

```python
import socket

def start_client(host="127.0.0.1", port=9000):
    """连接服务端并发送一条消息。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((host, port))
        s.sendall("你好，服务端".encode("utf-8"))
        reply = s.recv(1024)
        print("服务端回复:", reply.decode("utf-8"))

# start_client()  # 在服务端运行后取消注释
```

**关键结论**：Socket 提供的是**字节流（Byte Stream）**。收发的是 `bytes`，需要显式 `encode`/`decode`；TCP 不保留消息边界，这是后面设计协议的根本原因。

---

## 第三节：多客户端并发——线程与连接表

一个 `accept` 只能处理一个客户端。要支持多人，必须为每个连接分配独立处理逻辑，最直接的方式是**线程（Thread）**。

```python
import socket
import threading

clients = {}  # 连接表: conn -> 用户名
lock = threading.Lock()  # 保护共享状态


def broadcast(sender_conn, message: str):
    """把消息发给除发送者外的所有在线客户端。"""
    with lock:
        targets = list(clients.keys())
    for conn in targets:
        if conn is sender_conn:
            continue
        try:
            conn.sendall(message.encode("utf-8"))
        except OSError:
            pass  # 对方已断开，忽略


def handle_client(conn: socket.socket, addr):
    """每个客户端一个线程的处理函数。"""
    with lock:
        clients[conn] = str(addr)
    broadcast(conn, f"[{addr}] 加入聊天\n")
    try:
        while True:
            data = conn.recv(1024)
            if not data:
                break
            text = data.decode("utf-8").strip()
            broadcast(conn, f"[{addr}] {text}\n")
    finally:
        with lock:
            clients.pop(conn, None)
        broadcast(conn, f"[{addr}] 离开聊天\n")
        conn.close()


def serve(host="127.0.0.1", port=9000):
    """多线程聊天服务端入口。"""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen(50)
    print("多线程聊天服务端启动:", (host, port))
    while True:
        conn, addr = server.accept()
        threading.Thread(
            target=handle_client, args=(conn, addr), daemon=True
        ).start()

# serve()  # 本地运行时取消注释
```

**关键结论**：

1. 共享状态（`clients`）必须用锁（`Lock`）保护，否则并发写会出错。
2. 每个连接一个线程的模型简单直观，但线程数随用户线性增长，**可扩展性有限**。
3. 生产中更常见的是 **事件驱动（Event-Driven）**：如 `asyncio`、`selectors`，单线程处理上万个连接。

---

## 第四节：用 asyncio 改造——单线程处理多连接

`asyncio` 是 Python 标准库的异步 I/O 框架。它用**协程（Coroutine）** 代替线程，用一个事件循环（Event Loop）调度大量连接。

```python
import asyncio

clients = set()  # 在线 writer 集合


async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    """一个客户端的异步处理协程。"""
    addr = writer.get_extra_info("peername")
    clients.add(writer)
    await broadcast(f"[{addr}] 加入\n", exclude=writer)
    try:
        while True:
            data = await reader.read(1024)  # 非阻塞读取
            if not data:
                break
            text = data.decode("utf-8").strip()
            await broadcast(f"[{addr}] {text}\n", exclude=writer)
    finally:
        clients.discard(writer)
        await broadcast(f"[{addr}] 离开\n", exclude=writer)
        writer.close()


async def broadcast(message: str, exclude=None):
    """向所有在线连接发送消息。"""
    for w in list(clients):
        if w is exclude:
            continue
        try:
            w.write(message.encode("utf-8"))
            await w.drain()  # 等待缓冲写入完成
        except (ConnectionError, OSError):
            clients.discard(w)


async def main(host="127.0.0.1", port=9000):
    server = await asyncio.start_server(handle, host, port)
    print("异步聊天服务端启动:", (host, port))
    async with server:
        await server.serve_forever()

# asyncio.run(main())  # 本地运行时取消注释
```

**关键结论**：`async/await` 让高并发代码保持“看似同步”的可读性。相比多线程，它避免了 GIL 和线程切换开销，是聊天类 I/O 密集应用的主流选择，也是理解现代框架（FastAPI、aiohttp、Telegram Bot 等）的基石。

---

## 第五节：工程级的聊天应用还缺什么？

从上面 100 行代码到生产系统，还要补齐：

| 维度 | 单机版本 | 工程级做法 |
|------|----------|------------|
| 协议（Protocol） | 裸 TCP 字节流 | 定义消息帧：长度前缀、JSON/Protobuf |
| 状态 | 进程内存 | Redis / 数据库 |
| 扩展 | 单进程 | 多实例 + 消息队列（Kafka、Redis Pub/Sub） |
| 可靠性 | 无重连 | 心跳（Heartbeat）、断线重连、ACK |
| 安全 | 明文 | TLS、鉴权（Auth）、限流 |
| 可观测 | print | 日志、指标、链路追踪 |

一个最小的“消息帧”协议示例（长度前缀 + JSON）：

```python
import json
import struct

def pack_message(obj: dict) -> bytes:
    """打包: [4字节长度][JSON 负载]。"""
    payload = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    return struct.pack("!I", len(payload)) + payload

def unpack_message(data: bytes) -> dict:
    """还原一条完整帧。"""
    (length,) = struct.unpack("!I", data[:4])
    return json.loads(data[4:4 + length].decode("utf-8"))

raw = pack_message({"user": "Alice", "text": "你好"})
print(unpack_message(raw))  # {'user': 'Alice', 'text': '你好'}
```

**关键结论**：架构 = 分层 + 解耦。把“传输、协议、状态、业务”分成独立模块，每一层都可以独立替换与扩展。

## arch.sys.rag_platform

# arch.sys.rag_platform：从零搭建一个 RAG 平台

> 一句话直觉：RAG（Retrieval-Augmented Generation，检索增强生成）平台让大模型在回答前先“查资料”，从而给出有依据、可溯源、少胡说的答案。

---

## 1. 为什么需要 RAG：大模型的“知识盲区”

大模型（LLM）的知识来自训练数据，存在两个天然问题：

1. **知识陈旧**：训练截止后就不知道新事了。
2. **容易幻觉（hallucination）**：不知道时也会一本正经地编。

RAG 的思路很朴素：**先检索、再生成**。把私有文档、最新资料放进一个可搜索的知识库，用户提问时先检索出相关片段，再让模型基于片段回答。

```python
# 直觉对比：无 RAG vs 有 RAG
def answer_without_rag(question: str) -> str:
    # 模型只能靠记忆，可能幻觉
    return llm(question)  # 例如：“本公司年假是 20 天”（编的）

def answer_with_rag(question: str, retriever) -> str:
    # 先检索证据，再让模型基于证据回答
    docs = retriever.search(question, top_k=3)
    context = "\n".join(d.text for d in docs)
    prompt = f"仅根据以下资料回答：\n{context}\n\n问题：{question}"
    return llm(prompt)
```

**关键结论**：RAG 的价值不是让模型更聪明，而是给它“可核查的上下文”。

---

## 2. RAG 平台的四大核心模块

一个工程级的 RAG 平台 = **加载 → 切块 → 嵌入/索引 → 检索 → 生成** 的流水线，加上元数据、评估与运维。

```python
# RAG 平台最小骨架（伪代码，思路清晰为主）
class RAGPlatform:
    def __init__(self, loader, splitter, embedder, vector_store, llm):
        self.loader = loader            # 1. 文档加载：PDF/Markdown/网页 -> 纯文本
        self.splitter = splitter        # 2. 切块：长文档 -> 小 chunk
        self.embedder = embedder        # 3. 嵌入：文本 -> 向量
        self.vector_store = vector_store# 4. 向量库：存向量并支持相似度搜索
        self.llm = llm                  # 5. 生成：基于检索上下文回答

    def ingest(self, path: str):
        """离线阶段：把文档灌进知识库。"""
        text = self.loader.load(path)
        chunks = self.splitter.split(text, chunk_size=500, overlap=50)
        vectors = self.embedder.embed([c.text for c in chunks])
        self.vector_store.add(chunks, vectors)

    def query(self, question: str, top_k: int = 3) -> str:
        """在线阶段：检索 + 生成。"""
        q_vec = self.embedder.embed([question])[0]
        hits = self.vector_store.search(q_vec, top_k=top_k)
        context = "\n".join(h.text for h in hits)
        return self.llm(f"仅依据资料回答：\n{context}\n\n问题：{question}")
```

**关键结论**：RAG 平台 = 离线索引流水线（ingest） + 在线检索生成流水线（query）。

---

## 3. 向量检索：为什么要“嵌入”

关键词搜索只能匹配字面，换种说法就找不到。**嵌入（embedding）**把文本映射成高维向量，语义相近的文本向量距离更近。

```python
import math

def cosine(a, b):
    # 余弦相似度：1 表示方向一致，0 表示无关
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb + 1e-9)

# 假设 embedder 把“退款政策”和“怎么退货”映射到相近向量
doc_vec = embedder.embed(["我们的退款政策是 7 天内可退"])[0]
q_vec   = embedder.embed(["怎么申请退货？"])[0]
print(cosine(doc_vec, q_vec))  # 期望较高，如 0.75+
```

工程上常用 FAISS、Milvus、pgvector、Chroma 等做**向量库（vector store）**，支持百万级向量的近似最近邻（ANN, Approximate Nearest Neighbor）检索。

**关键结论**：嵌入把“语义相似”变成“向量距离近”，向量库负责快速找出最近的 Top-K。

---

## 4. 切块（Chunking）：最容易被低估的工程细节

文档太长不能整段塞进模型，太碎又会丢失上下文。切块策略直接决定检索质量。

```python
def split_text(text: str, chunk_size: int = 200, overlap: int = 40):
    """按字符切块，相邻块有重叠，避免语义被切断。"""
    chunks, start = [], 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap  # 重叠部分保持上下文连续
    return chunks

doc = "RAG 是检索增强生成。" * 100
chunks = split_text(doc)
print(len(chunks), chunks[0][:60])
```

要点：
- 优先按**语义边界**（段落、标题、句子）切，而不是硬按字符。
- 设置 **overlap**（重叠）防止关键句被切两半。
- 每个 chunk 保留**元数据**（来源文件、页码、时间），方便溯源。

**关键结论**：切块质量 ≈ 检索质量 ≈ 最终回答质量。

---

## 5. 从 Demo 到平台：工程化要补的三件事

一个能上线的 RAG 平台，除了上面五步，还要补：

1. **元数据与过滤**：按用户、部门、时间过滤，避免越权检索。
2. **评估（evaluation）**：用“检索命中率、答案忠实度”等指标持续回归测试。
3. **可观测性**：记录每次 query 的检索片段、耗时、token 消耗，便于排查。

```python
import time

def traced_query(platform, question):
    t0 = time.time()
    hits = platform.vector_store.search(platform.embedder.embed([question])[0], top_k=3)
    answer = platform.llm(question, context=[h.text for h in hits])
    return {
        "answer": answer,
        "sources": [h.meta for h in hits],  # 可溯源
        "latency_ms": int((time.time() - t0) * 1000),
    }
```

**关键结论**：RAG 平台的竞争力不在“能跑通”，而在“检索准、答案可溯源、持续可评估”。

---

## 动手练习

**任务：搭建一个最小可用的本地 RAG 平台（纯 Python，无需外部 API）**

要求：
1. 准备 3~5 个 `.txt` 文件（可以是自己写的笔记）。
2. 实现 `load -> split -> embed -> store -> search` 五个函数。
   - `embed` 可先用简化方案：把文本转为词频向量（bag-of-words）。
   - `search` 用第 3 节的 `cosine` 相似度排序，返回 Top-3。
3. 做一个命令行入口：输入问题，打印最相关的 3 个 chunk 及其来源文件名。
4. 加分项：给每个 chunk 加 `source` 和 `chunk_id` 元数据，输出时显示。

完成后你会得到一个**不依赖大模型**也能检索的 RAG 检索层，之后再接 LLM 即可升级为完整 RAG。

```python
import math, os, glob

def load_docs(folder):
    # 读取文件夹下所有 txt
    return [(os.path.basename(p), open(p, encoding="utf-8").read()) for p in glob.glob(f"{folder}/*.txt")]

def split_text(text, size=200, overlap=40):
    chunks, start = [], 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks

def embed(text):
    # 极简词频向量：按空格切词计数
    vec = {}
    for w in text.split():
        vec[w] = vec.get(w, 0) + 1
    return vec

def cosine(a, b):
    keys = set(a) | set(b)
    dot = sum(a.get(k, 0) * b.get(k, 0) for k in keys)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb + 1e-9)

def build_index(folder):
    index = []
    for fname, text in load_docs(folder):
        for i, c in enumerate(split_text(text)):
            index.append({"source": fname, "chunk_id": i, "text": c, "vec": embed(c)})
    return index

def search(index, question, top_k=3):
    qv = embed(question)
    scored = [(cosine(qv, item["vec"]), item) for item in index]
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:top_k]

if __name__ == "__main__":
    idx = build_index("./docs")  # 需要先准备 docs/*.txt
    for score, item in search(idx, "退款政策"):
        print(f"[{score:.3f}] {item['source']}#{item['chunk_id']}: {item['text'][:50]}")
```


---

## 本课题目

### single_choice · None



- [A] 客户端每隔 1 秒轮询一次服务端接口获取新消息
- [B] 服务端与客户端建立长连接，消息到达后由服务端主动推送
- [C] 客户端把消息写入本地文件，其他客户端读取该文件
- [D] 服务端把消息写入数据库，客户端只在重启时读取一次

**参考答案**：1

**解析**：实时聊天系统通常使用长连接（如 WebSocket）实现服务端主动推送，延迟低、开销小。轮询虽然可行但实时性差、浪费带宽，本地文件和一次性读取都无法满足多端实时同步。

### single_choice · None



- [A] 把所有消息都转成纯文本，图片用 URL 字符串表示，不区分类型
- [B] 为每种消息类型定义不同的数据库表，客户端根据表名判断
- [C] 消息包含统一的消息类型字段，内容部分按类型存放不同结构
- [D] 只在客户端区分类型，服务端原样存储二进制数据，不做任何标记

**参考答案**：2

**解析**：统一消息信封加类型字段的方式具有良好的扩展性，新增消息类型时不必改动整体协议。全部转文本会丢失信息；每类一张表会让客户端耦合数据库结构；服务端完全不标记类型则客户端无法正确解析。

### single_choice · None



- [A] 让每个客户端自己生成时间戳并直接决定顺序
- [B] 由服务端为同一会话的消息分配单调递增序号，客户端按序号排序
- [C] 按消息长度排序
- [D] 按发送者用户名排序

**参考答案**：1

**解析**：由服务端为同一会话分配单调递增序号，客户端按序号排序，能保证顺序一致。客户端时间戳可能不同步，按长度或用户名排序与发送顺序无关。

### single_choice · None



- [A] 撤回时直接从数据库中物理删除该消息记录
- [B] 撤回时把消息标记为已撤回，客户端根据标记显示撤回提示
- [C] 撤回时通知所有客户端清空整个会话
- [D] 撤回只能由发送者在本地删除，不影响其他用户

**参考答案**：1

**解析**：用标记位表示撤回可以保留审计与同步能力，客户端据此展示撤回提示。物理删除会丢失可追溯性，清空整个会话影响过大，只删本地则其他用户仍能看到。

### single_choice · None



- [A] 查询该用户最后一条消息的发送时间
- [B] 维护连接状态表或在线集合，连接建立与断开时更新
- [C] 定期向该用户的邮箱发送确认邮件
- [D] 读取该用户的本地配置文件

**参考答案**：1

**解析**：在线状态应由服务端根据连接生命周期维护，连接建立与断开时更新状态表或在线集合。最后发消息时间不能代表当前在线，邮件和本地配置也无法反映实时连接。

### single_choice · None



- [A] 只依赖长连接，断开就认为用户不再需要消息
- [B] 结合系统级推送通道，在长连接不可用时通过推送通知提醒用户
- [C] 让用户手动每隔几分钟打开一次应用
- [D] 把消息全部改成短信发送

**参考答案**：1

**解析**：移动端长连接可能被系统回收，结合系统级推送通道可以在应用未运行或后台时提醒用户。完全依赖长连接或要求用户频繁手动打开都不可靠，全部改短信则成本高且偏离应用内聊天。

### single_choice · None



- [A] 为每个成员单独复制一份完整消息并逐一发送
- [B] 服务端只保存一份消息，按成员维护投递记录或游标，避免重复复制内容
- [C] 只在群主在线时才允许发送消息
- [D] 要求所有成员必须同时在线才能收到消息

**参考答案**：1

**解析**：群消息只保存一份内容，投递状态按成员记录，可以显著减少存储与冗余。逐一复制整份消息浪费空间，要求群主或全员在线则严重限制可用性。

### single_choice · None



- [A] 为了让消息看起来更长
- [B] 为了在协议升级时能兼容旧客户端，平滑增加字段
- [C] 为了强制所有客户端同时升级
- [D] 为了加密消息内容

**参考答案**：1

**解析**：版本号与可扩展字段让协议可以渐进演进，旧客户端遇到未知字段可忽略，新客户端能识别新字段。这与消息长度、强制升级和加密无关。

### single_choice · None



- [A] 系统提示不进入消息流，只显示在独立角落且不参与排序
- [B] 系统提示作为特殊类型消息进入同一消息流，与其他消息一起排序并标注类型
- [C] 系统提示直接修改用户发送的消息内容
- [D] 系统提示只在服务端日志中记录，客户端不可见

**参考答案**：1

**解析**：系统提示作为特殊类型进入同一消息流，可以保证上下文顺序正确，客户端按类型渲染不同样式。完全隔离会丢失时序，篡改用户消息或只在日志中记录都不符合聊天产品需求。

### single_choice · None



- [A] 只在客户端做限制，服务端不做任何校验
- [B] 在服务端按用户或会话维度限制单位时间内的消息数量
- [C] 在数据库层禁止写入任何消息
- [D] 在客户端禁止用户输入超过 10 个字符

**参考答案**：1

**解析**：服务端按用户或会话维度限流是防止刷屏的有效手段，客户端限制容易被绕过。数据库禁止写入或强制极短输入都不合理。

### single_choice · None



- [A] 只投递给最后登录的那一端
- [B] 投递给该账号所有活跃连接，并同步已读状态
- [C] 随机选择一端投递
- [D] 必须让用户手动选择接收端

**参考答案**：1

**解析**：多端在线时应把消息投递给该账号的所有活跃连接，并同步已读等状态，保证各端体验一致。只投递某端或随机投递会导致其他端丢失消息，手动选择则增加使用负担。

### single_choice · None



- [A] 因为两者完全等价，可以合并为一条路径
- [B] 持久化保证消息可追溯与离线补发，投递关注实时触达，职责不同，分开更利于扩展与容错
- [C] 因为只有持久化才需要网络传输
- [D] 因为投递路径不需要考虑用户在线状态

**参考答案**：1

**解析**：持久化负责可靠存储与离线补发，投递负责实时触达在线连接，两者目标与失败模式不同，分开设计便于独立扩展和容错。两者并不等价，投递也需要考虑在线状态。

### single_choice · None



- [A] 悲观锁
- [B] 乐观 UI 更新
- [C] 轮询
- [D] 服务端渲染

**参考答案**：1

**解析**：先更新界面再发请求属于乐观 UI 更新，用于提升交互体验；若服务端失败再回滚或提示。悲观锁、轮询与服务端渲染都属于其他机制，与这种先展示后提交的模式不同。

### single_choice · None



- [A] 发送方定时重新发送消息，直到收到回复
- [B] 接收方在打开会话时向服务端上报已读位置，服务端再通知发送方
- [C] 服务端在消息写入数据库后自动认为对方已读
- [D] 接收方客户端把已读状态写在自己的本地存储中即可

**参考答案**：1

**解析**：已读回执需要接收端主动上报已读状态，并由服务端转发给发送端。重发消息不能表示已读；写入数据库不等于用户看过；只存本地则发送方无法获知。

### single_choice · None



- [A] 在每个客户端保存所有服务器的 IP 列表
- [B] 消息中转或发布订阅机制，让各服务器之间同步消息
- [C] 只在用户登录的那台服务器上存储全部历史消息
- [D] 要求用户每次发言前手动选择目标服务器

**参考答案**：1

**解析**：多实例部署时，需要消息中转或发布订阅把消息广播到各节点，使连接在不同服务器上的用户都能收到。手工选择服务器或只在单机存储都无法保证跨服务器送达。

### single_choice · None



- [A] 只按消息发送时间建立全局索引，查询时再过滤会话
- [B] 只按发送者昵称建立索引，按昵称查询
- [C] 按会话标识加时间排序建立索引，查询时限定会话并倒序取最近若干条
- [D] 不建立任何索引，每次查询都全表扫描

**参考答案**：2

**解析**：聊天历史通常按会话查询并按时间倒序取最近若干条，因此会话标识加时间的组合索引最有效。仅按时间或昵称过滤会导致大量无效扫描，不建索引在数据量大时性能很差。

### single_choice · None



- [A] 根据消息的发送时间字符串做精确匹配
- [B] 为每条消息分配唯一标识，客户端按标识去重
- [C] 根据消息文本内容哈希去重
- [D] 每次收到消息前先清空界面再全部重新渲染

**参考答案**：1

**解析**：服务端为消息分配唯一 ID，客户端依据 ID 去重最可靠。按时间字符串或文本哈希会误判不同消息，清空重渲染只是掩盖问题且开销大。

### single_choice · None



- [A] 客户端每次按键都向服务端发送一条持久化消息
- [B] 客户端在用户输入时发送轻量事件，接收方收到后显示提示并设置短时过期
- [C] 服务端定时扫描所有用户的输入框内容
- [D] 只有消息发送成功后才显示对方正在输入

**参考答案**：1

**解析**：正在输入属于瞬态状态，应该用轻量、可过期的通知事件实现，不进入持久化消息流。每次按键都持久化或服务端扫描输入框都不现实，消息发送后才提示也失去意义。

### single_choice · None



- [A] 对消息内容做去重，内容相同就丢弃
- [B] 让客户端生成幂等键，服务端依据幂等键判断是否已处理
- [C] 关闭客户端重试机制
- [D] 在消息中附带发送者的 IP 地址并据此去重

**参考答案**：1

**解析**：客户端生成幂等键，服务端据此判断是否已处理同一请求，是防止重复写入的常见做法。按内容去重会误伤合法重复消息；关闭重试牺牲可靠性；按 IP 去重会误伤同一网络下的不同用户。

### single_choice · None



- [A] 用户离线时直接丢弃消息，不做任何处理
- [B] 服务端为每个用户维护未送达队列或未读游标，上线后拉取
- [C] 要求发送方一直保持在线直到接收方上线
- [D] 把消息只保存在发送方本地，接收方上线后从发送方拉取

**参考答案**：1

**解析**：离线消息依赖服务端保存未送达队列或未读游标，用户上线后拉取。丢弃消息或要求发送方挂机都不可行，只存发送方本地在发送方离线后也会丢消息。

### single_choice · None



- [A] 文本分块 → 向量化 → 文本抽取 → 存入向量库
- [B] 文本抽取 → 文本分块 → 向量化 → 存入向量库
- [C] 向量化 → 文本抽取 → 文本分块 → 存入向量库
- [D] 文本分块 → 文本抽取 → 向量化 → 存入向量库

**参考答案**：1

**解析**：RAG 平台处理文档的标准流程是：先从原始文件（如 PDF）中抽取纯文本，再将长文本切分成适合嵌入模型的块（chunk），然后对每个块做向量化，最后写入向量数据库。顺序颠倒会导致对非文本内容做向量化或对未切分的超长文本做嵌入。

### single_choice · None



- [A] 减少大模型的参数量以加快推理速度
- [B] 让大模型的回答能基于外部知识，减少幻觉
- [C] 替代大模型的训练过程，节省算力成本
- [D] 对用户输入做敏感词过滤，提高安全性

**参考答案**：1

**解析**：RAG 的核心价值是把外部知识库中的相关片段作为上下文提供给大模型，使生成内容有事实依据，从而缓解模型知识过时和幻觉问题。它并不改变模型参数、不替代训练，也不是安全过滤机制。

### multi_choice · None



- [A] 扫描件通常需要 OCR 才能提取文字
- [B] 表格内容若直接按纯文本处理可能丢失行列结构
- [C] 图片中的文字如果解析阶段不处理，检索时无法被命中
- [D] 文档解析只影响存储速度，不影响检索结果

**参考答案**：[0, 1, 2]

**解析**：扫描件必须 OCR；表格若无结构化处理会丢失行列语义；图片中的文字若不抽取，就不会进入索引，自然检索不到。解析质量直接影响后续分块和检索，绝不只是存储问题。

### multi_choice · None



- [A] 生成阶段温度参数设置过高，输出随机性大
- [B] 检索结果的排序不稳定，关键块有时不在上下文中
- [C] 提示词模板没有强调必须基于给定上下文回答
- [D] 向量数据库的磁盘剩余空间

**参考答案**：[0, 1, 2]

**解析**：温度过高会使生成随机化；检索排序不稳定会导致有时关键上下文缺失；提示词未约束模型基于上下文作答会使其自由发挥。磁盘剩余空间通常不影响语义结果，不是不稳定性的合理原因。

### fill_blank · None



**参考答案**：["chunking", "分块", "文本分块"]

**解析**：该过程英文为 chunking，中文常译为分块。它是 RAG 数据入库前的关键步骤，决定了后续检索的粒度与语义聚焦程度。

### fill_blank · None



**参考答案**：["重叠", "overlap", "重叠区", "overlapping"]

**解析**：块间重叠（overlap）指相邻块共享一段文本，避免答案恰好被切断在两个块之间而无法被完整召回。

### fill_blank · None



**参考答案**：["Augmented", "augmented", "增强"]

**解析**：RAG 全称为 Retrieval-Augmented Generation，中文译为检索增强生成，即在生成前通过检索把外部知识增强到上下文中。

### code_reading · None



**参考答案**：rerank 对初步召回的 10 个候选文档做更精细的相关性重新排序，再取前 3 个最相关的块构造提示词。若去掉它直接用 docs[:3]，由于初检排序可能不够精确，前 3 个块未必是最相关的，关键信息可能没被送入模型，导致生成的回答质量下降或不准确。

**解析**：初检侧重快速召回，排序精度有限；重排序模型基于查询与文档的交互做更精确打分，把真正相关的块提前。跳过重排序容易让次相关甚至不相关的块占据有限的上下文位置。

### code_reading · None



**参考答案**：该提示词没有明确要求模型只能依据给定的参考资料作答，也没有处理资料中不包含答案的情况，模型可能忽略资料凭自身知识生成，从而产生幻觉。改进方式是明确指示模型「仅基于上述资料回答，若资料中没有相关信息则如实说明无法回答」，并可对资料做来源标注与分隔。

**解析**：RAG 的生成效果高度依赖提示词对上下文的约束力。缺少「基于给定资料」的指令和「无答案时如何回应」的兜底规则，会让模型自由发挥，削弱 RAG 抑制幻觉的作用。

### scenario · None



**解析**：跨版本对比类问题往往需要同时召回多份文档的多个块，单块检索易漏，需检查分块策略并引入重排序保证关键块进入上下文；专业术语检索不到通常是因为纯向量检索对精确术语匹配弱，应引入关键词检索（如 BM25）做混合检索，兼顾语义与精确匹配。

### scenario · None



**解析**：文档不断累积会带来冗余和噪声，应先做去重与元数据过滤，减少无效候选；检查分块策略是否产生了过多碎片；向量索引类型与参数（如近似最近邻索引）是否适合当前规模；并可通过重排序在较小候选集上保证精度，从而在不牺牲准确率的前提下降低检索延迟。

### single_choice · None



- [A] 嵌入模型维度太低，无法表达长文本
- [B] 块切得太大且无重叠，关键信息被切断且上下文丢失
- [C] 向量数据库的索引类型选错了
- [D] 大模型的上下文窗口太小，装不下检索结果

**参考答案**：1

**解析**：块过大且无重叠时，一个语义完整的答案可能被切分到相邻两个块中，检索只能命中其中一块，导致上下文不完整。通常做法是设置合适的块大小并加入块间重叠（overlap）来保持语义连续性。

### single_choice · None



- [A] 比较查询向量与文档向量之间的余弦相似度或内积距离
- [B] 比较查询字符串与文档字符串的字符长度差
- [C] 比较文档块的创建时间先后
- [D] 比较文档块中包含的关键词数量

**参考答案**：0

**解析**：向量检索通过度量向量之间的距离或相似度来排序，常见的有余弦相似度、内积、欧氏距离等。字符长度、创建时间、关键词计数都不是向量空间中语义相似度的度量方式。

### single_choice · None



- [A] 向量数据库的存储容量是否不足
- [B] 拼接检索结果与用户问题的提示词模板是否合理
- [C] 文档解析时是否丢失了图片
- [D] 嵌入模型的许可证是否合规

**参考答案**：1

**解析**：当检索结果正确但生成错误时，问题往往出在生成阶段，尤其是提示词模板——它决定了模型如何看到并使用检索到的上下文。应检查模板是否清晰指示模型「基于给定上下文回答」，以及上下文拼接的位置和格式。

### single_choice · None



- [A] 检索阶段负责理解语义并生成最终答案，生成阶段只做格式美化
- [B] 检索阶段负责从知识库中找出相关片段，生成阶段负责结合这些片段组织自然语言回答
- [C] 两个阶段都必须由同一个大模型完成，不能解耦
- [D] 生成阶段必须在检索之前执行，否则无法构造查询

**参考答案**：1

**解析**：RAG 将检索与生成解耦：检索器（常为嵌入模型加向量库）负责召回相关文档片段，生成器（大模型）负责基于这些片段和用户问题产出回答。二者职责不同，且检索先于生成。

### single_choice · None



- [A] 大块会使嵌入向量被稀释，语义焦点模糊，相似度匹配变差
- [B] 大块会让向量数据库无法建立索引
- [C] 大块会被嵌入模型直接拒绝，返回空向量
- [D] 大块会导致文档无法被解析成文本

**参考答案**：0

**解析**：当一个块包含过多主题时，其嵌入向量是所有内容的平均表示，会稀释关键语义，使查询与块的相似度下降，检索命中率降低。适当的小块加重叠通常能提升语义聚焦度。

### single_choice · None



- [A] 只用语义向量检索，关键词检索已被淘汰
- [B] 只用关键词检索，因为向量检索不可靠
- [C] 混合检索，将向量检索与关键词检索（如 BM25）的结果融合排序
- [D] 随机在两种检索方式中选一种

**参考答案**：2

**解析**：混合检索同时运行稠密向量检索（语义）和稀疏关键词检索（如 BM25），再通过倒数排名融合等方式合并结果，能兼顾语义泛化和精确术语匹配，是 RAG 平台的常见实践。

### single_choice · None



- [A] 对检索结果做重排序（rerank），把最相关的块排到前面并优先送入模型
- [B] 把所有检索结果都删掉，重新训练大模型
- [C] 把第 3 块之后的块全部丢弃，只保留第 1、2 块
- [D] 降低嵌入模型的维度

**参考答案**：0

**解析**：重排序模型（reranker）对初步召回的候选块进行更精细的相关性打分并重新排序，把真正相关的块放在上下文靠前位置，能显著提升生成阶段对关键信息的利用。

### multi_choice · None



- [A] 调整分块大小与重叠策略
- [B] 引入重排序模型对候选结果重排
- [C] 采用混合检索融合向量与关键词结果
- [D] 把大模型的温度参数调到最大以增加多样性

**参考答案**：[0, 1, 2]

**解析**：分块策略、重排序和混合检索都直接作用于召回与排序环节，能提升检索质量。调高生成温度只影响输出随机性，与检索质量无关，甚至可能降低回答稳定性。
