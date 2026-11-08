# s6u3l6 把大模型推理做成高吞吐服务 / 一、一句话直觉 / 学 Ollama 就像学“在自己电脑上装一个可编程的 C

> 来源 `content/lessons/s6u3l6.json`

## ai.llm.vllm

# ai.llm.vllm：把大模型推理做成高吞吐服务

## 一句话直觉
如果你要让大语言模型（LLM, Large Language Model）在线上同时服务很多用户，**vLLM** 就是那个把“一次只算一个请求”变成“很多请求一起高效算”的推理引擎。

---

## 1. 为什么需要 vLLM：从“能跑”到“跑得快”

零基础先记住一个事实：大模型推理（inference）不是只做一次矩阵乘法，而是**自回归生成**（autoregressive generation）——每生成一个 token（词元），都要把前面所有 token 重新送入模型计算。

朴素做法的问题：
- 每个请求单独跑一遍模型，GPU 利用率低。
- 不同请求长度不同，批量处理（batching）很难做。
- KV Cache（键值缓存，Key/Value Cache）占用大量显存，但传统方式碎片化严重。

vLLM 的核心价值：**用更少的 GPU，服务更多的并发请求。**

```python
# 先看一个最朴素的“逐请求推理”思路（伪代码，帮助理解问题）
# 假设 model.generate 一次只能处理一个 prompt
prompts = ["你好", "介绍一下Python", "写一首诗"]
for p in prompts:
    result = model.generate(p)  # 每个请求单独跑，GPU 经常在等
    print(result)
# 问题：3 个请求串行执行，吞吐量低，显存浪费
```

---

## 2. vLLM 的关键武器：PagedAttention 与 Continuous Batching

### 2.1 PagedAttention（分页注意力）

传统 KV Cache 像“连续大数组”，长度变化时容易碎片化。  
PagedAttention 借鉴操作系统虚拟内存分页（paging）思想，把 KV Cache 切成固定大小的 block（块），按需分配。

好处：
- 显存利用率更高。
- 不同请求可以共享 block，减少浪费。
- 支持更长的上下文和更多并发。

### 2.2 Continuous Batching（连续批处理）

传统 batching 要等一批请求都结束后再开始下一批。  
Continuous Batching 是**请求级别动态进出**：某个请求生成完就立刻退出，新请求马上补进来。

效果：GPU 几乎一直在忙，吞吐量显著提升。

```python
# 用 vLLM 的离线批量推理接口感受“批量”与“高吞吐”
from vllm import LLM, SamplingParams

# 1) 加载模型：这里用一个小模型便于本地运行
llm = LLM(model="facebook/opt-125m")

# 2) 采样参数：控制生成行为
sampling_params = SamplingParams(temperature=0.8, top_p=0.95, max_tokens=64)

# 3) 一次传入多个 prompt，vLLM 内部会自动做高效批处理
prompts = [
    "Hello, my name is",
    "The capital of France is",
    "Python is a programming language that",
]
outputs = llm.generate(prompts, sampling_params)

# 4) 打印结果
for output in outputs:
    prompt = output.prompt
    generated = output.outputs[0].text
    print(f"Prompt: {prompt!r}, Generated: {generated!r}")
```

---

## 3. 从离线到在线：vLLM 的服务化用法

vLLM 不只是 Python 库，它还能启动一个 **OpenAI 兼容 API 服务**。这意味着：
- 你可以像调用 OpenAI API 一样调用本地模型。
- 现有基于 OpenAI SDK 的代码几乎不用改。

启动命令示例（终端执行）：

```bash
python -m vllm.entrypoints.openai.api_server \
  --model facebook/opt-125m \
  --host 0.0.0.0 \
  --port 8000
```

然后客户端可以这样请求：

```python
# 用 OpenAI SDK 调用本地 vLLM 服务
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="EMPTY",  # vLLM 本地服务通常不校验 key
)

resp = client.chat.completions.create(
    model="facebook/opt-125m",
    messages=[{"role": "user", "content": "用一句话解释什么是 vLLM"}],
    max_tokens=64,
)

print(resp.choices[0].message.content)
```

---

## 4. 工程级关注点：吞吐、延迟与显存

学 vLLM 不能只会调用，还要知道怎么调优。

- **吞吐量（throughput）**：单位时间处理的 token 数或请求数。  
- **延迟（latency）**：单个请求从发出到收到完整结果的时间。  
- **显存（GPU memory）**：KV Cache 是主要消耗者。

常见调节手段：
- `tensor_parallel_size`：张量并行，多卡拆模型。
- `gpu_memory_utilization`：控制 vLLM 使用多少显存。
- `max_model_len`：限制上下文长度，防止显存爆掉。
- `max_num_seqs`：限制并发序列数。

```python
# 工程化加载示例：显式控制显存与并发
from vllm import LLM, SamplingParams

llm = LLM(
    model="facebook/opt-125m",
    gpu_memory_utilization=0.8,  # 最多使用 80% 显存
    max_model_len=512,           # 限制上下文长度
    max_num_seqs=16,             # 最多同时处理 16 个序列
)

sampling_params = SamplingParams(temperature=0.7, max_tokens=32)
outputs = llm.generate(["Explain vLLM in one sentence."], sampling_params)
print(outputs[0].outputs[0].text)
```

---

## 5. 最小可运行示例：本地跑通 vLLM

如果你本地有 GPU，推荐先安装：

```bash
pip install vllm
```

然后运行下面的代码。若没有 GPU，也可以先读懂逻辑，再到云 GPU 环境执行。

```python
from vllm import LLM, SamplingParams

# 小模型便于快速验证
llm = LLM(model="facebook/opt-125m")

sampling_params = SamplingParams(
    temperature=0.8,
    top_p=0.95,
    max_tokens=64,
)

prompts = [
    "vLLM is",
    "The main benefit of PagedAttention is",
]

outputs = llm.generate(prompts, sampling_params)

for out in outputs:
    print("PROMPT:", out.prompt)
    print("OUTPUT:", out.outputs[0].text)
    print("-" * 40)
```

---

## 动手练习

**任务：搭一个本地 vLLM 迷你服务，并用 Python 客户端调用它。**

1. 安装 vLLM：`pip install vllm openai`
2. 在终端启动 OpenAI 兼容服务：
   ```bash
   python -m vllm.entrypoints.openai.api_server --model facebook/opt-125m --port 8000
   ```
3. 写一个 Python 脚本，向 `http://localhost:8000/v1/chat/completions` 发送 3 条不同问题。
4. 记录每条请求的耗时，并思考：如果把 3 条请求并发发送，总耗时会不会更短？为什么？
5. 进阶：把 `max_tokens` 从 32 改成 128，观察显存和延迟变化。

---

## 常见误区

- 以为 vLLM 能“加速模型本身”。它主要优化的是**推理调度与显存管理**，不是改变模型计算量。
- 以为装了 vLLM 就不需要 GPU。vLLM 主要面向 GPU 推理，CPU 支持有限且慢。
- 把 `max_model_len` 设得过大，导致显存不足或启动失败。
- 以为并发越高越好。并发过高会增加延迟，需要根据显存和业务目标调优。

## ai.llm.tgi

# 一、一句话直觉
TGI（Text Generation Inference，文本生成推理）是 Hugging Face 推出的**面向生产环境的大语言模型推理服务框架**；学它，是为了把“本地能跑的模型”变成“能被多人、稳定、低延迟调用的在线服务”。

---

## 1. 从“能生成”到“能上线”：为什么需要 TGI

很多人第一次用 LLM（Large Language Model，大语言模型）时，是这样写的：

```python
from transformers import pipeline

generator = pipeline("text-generation", model="gpt2")
print(generator("Hello, I am", max_new_tokens=20))
```

这段代码适合实验，但一旦上线会遇到几个问题：

1. **并发差**：每个请求都占一份模型，显存很快爆。
2. **吞吐低**：用户一个一个等，GPU 利用率不高。
3. **缺少服务能力**：没有 HTTP API（Application Programming Interface，应用程序编程接口）、流式输出、监控、限流、健康检查。
4. **部署复杂**：量化、张量并行（Tensor Parallelism，张量并行）、批处理都要自己写。

TGI 的目标就是：**把 LLM 推理做成一个标准化、高性能、可部署的服务**。

### 小结论
TGI 不是模型，也不是训练框架；它是**推理服务层**，负责高效地“接待请求、组织计算、返回结果”。

---

## 2. TGI 的核心能力：它到底解决了什么

TGI 常见能力包括：

- **连续批处理（Continuous Batching）**：请求不必等整批结束，新请求可动态加入，显著提升吞吐。
- **流式输出（Streaming）**：像 ChatGPT 一样逐 token 返回，改善体验。
- **张量并行（Tensor Parallelism）**：大模型可切到多张 GPU 上运行。
- **量化（Quantization）**：用更少显存运行模型，如 bitsandbytes、GPTQ、AWQ 等。
- **OpenAI 兼容 API**：很多场景可无缝替换 OpenAI 接口。
- **可观测性（Observability）**：指标、日志、健康检查。

### 小结论
TGI 的关键词不是“模型效果”，而是**吞吐、延迟、显存、并发、服务化**。

---

## 3. 最小可运行示例：先本地启动一个 TGI 服务

TGI 最常见的启动方式是 Docker（容器化工具）。下面命令会在本机启动一个服务：

```bash
# 需要先安装 Docker，并确保有可用 GPU（CPU 也可体验，但速度慢）
docker run --gpus all --shm-size 1g -p 8080:80 \
  -v $PWD/data:/data \
  ghcr.io/huggingface/text-generation-inference:latest \
  --model-id gpt2
```

含义解释：

- `--gpus all`：使用所有 GPU。
- `-p 8080:80`：把容器 80 端口映射到本机 8080。
- `--model-id gpt2`：指定要加载的模型。

启动后，就可以用 HTTP 请求调用：

```bash
curl 127.0.0.1:8080/generate \
  -X POST \
  -d '{"inputs":"Hello, I am","parameters":{"max_new_tokens":20}}' \
  -H 'Content-Type: application/json'
```

如果你更熟悉 Python，也可以用 `huggingface_hub` 的 InferenceClient：

```python
from huggingface_hub import InferenceClient

client = InferenceClient(model="http://127.0.0.1:8080")
print(client.text_generation("Hello, I am", max_new_tokens=20))
```

### 小结论
TGI 的典型形态是：**模型加载在服务端，客户端通过 HTTP 或 SDK 调用**。

---

## 4. 从工程视角理解 TGI：请求进来后发生了什么

一个请求进入 TGI 后，通常会经历：

1. **Tokenize（分词）**：把文本转成 token id。
2. **排队与批处理（Queue & Batching）**：多个请求被动态合并成 batch。
3. **模型前向计算（Forward Pass）**：GPU 执行推理。
4. **采样（Sampling）**：根据 logits 选择下一个 token。
5. **Detokenize（反分词）**：把 token id 转回文本。
6. **流式返回**：边生成边返回。

可以把它想成一个“餐厅后厨”：

- 顾客 = 请求
- 点菜单 = prompt
- 厨师 = GPU
- 传菜员 = TGI 调度系统
- 连续批处理 = 不再一桌一桌做，而是把多桌菜一起安排

### 小结论
TGI 的价值在于**调度与工程优化**，而不仅仅是“调用模型”。

---

## 5. 什么时候该用 TGI，什么时候不该用

适合使用 TGI 的场景：

- 需要把 LLM 部署成在线 API。
- 多用户并发访问。
- 需要流式输出。
- 需要控制显存、吞吐和延迟。
- 希望兼容 OpenAI 风格接口。

不太适合的场景：

- 只是在 Notebook 里做一次实验。
- 只需要离线批量跑一次。
- 团队没有 GPU 或容器部署条件。
- 模型非常小，普通 Flask/FastAPI 也能满足。

### 小结论
TGI 是**生产推理服务工具**，不是实验工具。学习它的目标是：让你具备把模型“上线”的能力。

---

## 6. 关键参数与调优直觉

常见启动参数：

- `--model-id`：模型 ID。
- `--max-batch-total-tokens`：批处理总 token 上限。
- `--max-concurrent-requests`：最大并发请求数。
- `--max-input-length`：最大输入长度。
- `--max-total-tokens`：最大总长度。
- `--quantize`：量化方式。

调优直觉：

- 显存不够：降低 batch、启用量化、缩短最大长度。
- 延迟高：检查并发、batch 大小、模型大小。
- 吞吐低：提高 batch 上限，但别爆显存。

### 小结论
TGI 调优的核心是：**在显存、吞吐、延迟三者之间找平衡**。

---

## 7. 常见误区

1. **把 TGI 当成模型**：TGI 是推理服务框架，不是模型本身。
2. **以为必须多卡**：单卡也能跑，多卡主要用于大模型。
3. **只看吞吐不看延迟**：批处理提升吞吐，但可能增加单请求等待时间。
4. **忽略显存预算**：长上下文、大 batch、多并发都会吃显存。
5. **直接暴露公网**：生产环境要加鉴权、限流、HTTPS、网关。

---

## 8. 动手练习

**任务：本地启动一个 TGI 服务并完成一次流式调用。**

要求：

1. 安装 Docker。
2. 用 TGI 启动一个小模型，例如 `gpt2` 或 `sshleifer/tiny-gpt2`。
3. 使用 `curl` 调用 `/generate` 接口，拿到生成结果。
4. 使用 `curl` 调用 `/generate_stream` 接口，观察流式返回。
5. 记录：
   - 启动命令
   - 请求命令
   - 返回结果
   - 你观察到的延迟和输出差异

进阶：

- 改 `max_new_tokens`，观察输出长度变化。
- 改 `temperature`，观察随机性变化。
- 如果显存不足，尝试更小模型或量化参数。

---

## 9. 小结

TGI 是 LLM 工程化的重要一环。它把模型推理从“本地函数调用”提升为“可部署、可扩展、可观测”的服务。掌握 TGI，意味着你开始具备把 AI 模型真正交付给用户的能力。

## ai.llm.ollama

## 一句话直觉
学 Ollama 就像学“在自己电脑上装一个可编程的 ChatGPT 引擎”：它把大语言模型（LLM，Large Language Model）的下载、运行和本地 API（Application Programming Interface，应用程序接口）都封装成一条命令，让你不花云端费用、不泄露数据，也能在 Python 里调用 AI。

---

### 1. Ollama 是什么：本地 LLM 的“运行器 + 模型仓库”
Ollama 是一个开源工具，用来在本地运行大语言模型。你不需要自己配置 CUDA（Compute Unified Device Architecture，英伟达 GPU 计算平台）、量化（Quantization，把模型参数从高精度压缩成低精度）或推理引擎（Inference Engine，执行模型计算的程序）。Ollama 负责：
- 下载模型权重：`ollama pull llama3.2`
- 启动本地服务：默认监听 `http://localhost:11434`
- 提供 REST API（Representational State Transfer，表述性状态转移接口）和命令行交互

对 Python 开发者来说，最重要的是：Ollama 暴露了一个 HTTP 接口，我们可以用 `requests` 或官方 `ollama` 包直接调用。

```python
# 检查 Ollama 服务是否在运行
import requests

resp = requests.get("http://localhost:11434/api/tags", timeout=5)
print(resp.status_code)  # 200 表示服务正常
print(resp.json())       # 返回本地已下载的模型列表
```

**关键结论**：Ollama = 本地模型管理 + 本地推理服务 + 简单 API。

---

### 2. 安装与第一次对话：从命令行到 Python
先安装 Ollama（官网下载安装包），然后在终端执行：

```bash
ollama pull llama3.2
ollama run llama3.2
```

这会进入交互式聊天。要用 Python 调用，最直接的方式是发 HTTP 请求：

```python
import requests

url = "http://localhost:11434/api/generate"
payload = {
    "model": "llama3.2",
    "prompt": "用一句话解释什么是大语言模型。",
    "stream": False
}

resp = requests.post(url, json=payload, timeout=60)
print(resp.json()["response"])
```

**关键结论**：Ollama 的核心调用入口是 `/api/generate`，传入 `model` 和 `prompt` 即可。

---

### 3. 聊天接口：从单轮生成到多轮对话
`/api/generate` 适合单轮补全。真实聊天需要记住上下文，这时用 `/api/chat`，消息格式是 `role` + `content`：

```python
import requests

url = "http://localhost:11434/api/chat"
messages = [
    {"role": "system", "content": "你是一个简洁的 Python 助教。"},
    {"role": "user", "content": "什么是列表推导式？"}
]

resp = requests.post(url, json={
    "model": "llama3.2",
    "messages": messages,
    "stream": False
}, timeout=60)

print(resp.json()["message"]["content"])
```

**关键结论**：多轮对话用 `/api/chat`，把历史消息按顺序传入 `messages` 列表。

---

### 4. 用官方 Python 包：更简洁的调用方式
Ollama 提供了 Python 包 `ollama`，安装：

```bash
pip install ollama
```

然后可以这样写：

```python
from ollama import chat

response = chat(
    model="llama3.2",
    messages=[{"role": "user", "content": "写一个 Python 函数计算阶乘。"}]
)
print(response["message"]["content"])
```

流式输出（Streaming，边生成边返回）也很简单：

```python
from ollama import chat

stream = chat(
    model="llama3.2",
    messages=[{"role": "user", "content": "数到 5。"}],
    stream=True
)

for chunk in stream:
    print(chunk["message"]["content"], end="", flush=True)
```

**关键结论**：官方包把 HTTP 细节封装成 `chat()` 和 `generate()`，适合工程代码。

---

### 5. 工程级用法：参数、错误处理与结构化输出
真实项目里要控制随机性、超时、异常，还要让模型输出 JSON（JavaScript Object Notation，一种轻量数据交换格式）。

```python
from ollama import chat
import json

response = chat(
    model="llama3.2",
    messages=[{
        "role": "user",
        "content": "返回 JSON：{'name': 'Ollama', 'type': 'local_llm'}"
    }],
    format="json",  # 要求模型输出 JSON
    options={
        "temperature": 0.2,  # 越低越确定
        "num_predict": 100   # 最多生成 100 个 token
    }
)

data = json.loads(response["message"]["content"])
print(data["name"], data["type"])
```

**关键结论**：`format="json"` 可约束输出格式，`options` 控制生成行为，工程中必须加超时和异常捕获。

---

### 常见误区
- 以为 Ollama 一定要 GPU：CPU 也能跑小模型，只是慢。
- 把 `stream=False` 和流式输出混用：流式时返回的是迭代器，不是完整 JSON。
- 忘记启动 Ollama 服务：Python 调用会连接失败。
- 模型名写错：必须和 `ollama list` 里的名称一致。

---

### 动手练习
任务：写一个 Python 脚本 `ask_ollama.py`，实现：
1. 用 `/api/chat` 或 `ollama.chat` 向本地 `llama3.2` 提问：“用三句话介绍 Python 的虚拟环境”。
2. 开启流式输出，逐字打印结果。
3. 如果连接失败，打印“请先启动 Ollama 服务”。

完成后运行：

```bash
python ask_ollama.py
```


---

## 本课题目

### single_choice · None



- [A] 通过分页注意力机制高效管理 KV 缓存，提升吞吐量
- [B] 通过量化压缩模型权重，降低显存占用
- [C] 通过模型蒸馏技术，减小模型参数量
- [D] 通过数据并行训练，加速模型收敛

**参考答案**：0

**解析**：vLLM 的核心创新是 PagedAttention，用于高效管理 KV 缓存，从而显著提升推理吞吐量。量化、蒸馏、训练加速均非 vLLM 的主要设计目标。

### single_choice · None



- [A] 将 KV 缓存分页存储，按需分配非连续显存块
- [B] 将 KV 缓存全部卸载到 CPU 内存
- [C] 对 KV 缓存进行 8-bit 量化
- [D] 预先为每个请求分配最大长度的连续显存

**参考答案**：0

**解析**：vLLM 的 PagedAttention 将 KV 缓存划分为固定大小的块，按需分配，避免为每个请求预留最大长度连续显存，从而减少碎片。

### single_choice · None



- [A] 更高的吞吐量和更优的显存利用率
- [B] 支持更多种类的模型架构
- [C] 提供更丰富的训练功能
- [D] 内置了数据预处理工具

**参考答案**：0

**解析**：vLLM 的核心优势是推理吞吐量和显存利用率；模型架构支持未必更多，训练功能并非其重点，数据预处理也不是其特色。

### single_choice · None



- [A] 将 gpu_memory_utilization 设置得过高，且并发请求过多
- [B] 将 max_tokens 设置为较小的值
- [C] 将 temperature 设置为 0
- [D] 使用较小的模型

**参考答案**：0

**解析**：gpu_memory_utilization 过高会占满显存，加上并发请求的 KV 缓存增长，容易 OOM；其他选项不会直接导致显存不足。

### single_choice · None



- [A] vLLM 提供 AsyncLLMEngine 用于异步处理请求
- [B] vLLM 只支持同步推理，不支持异步
- [C] 异步接口必须配合多进程才能使用
- [D] 异步接口只能用于训练阶段

**参考答案**：0

**解析**：vLLM 提供 AsyncLLMEngine 支持异步推理，适用于高并发服务；同步和异步均可使用，不限于训练。

### single_choice · None



- [A] 使用 vLLM 提供的 OpenAI 兼容服务器启动命令
- [B] 使用 vLLM 的 Trainer 类导出为 ONNX
- [C] 使用 vLLM 的 Pipeline 类封装为 REST
- [D] 使用 vLLM 的 DataLoader 类生成 API

**参考答案**：0

**解析**：vLLM 提供 OpenAI 兼容的 API 服务器，可通过命令行启动；Trainer、Pipeline、DataLoader 并非 vLLM 的 API 封装工具。

### single_choice · None



- [A] KV 缓存用于存储自注意力机制中的键和值，避免重复计算
- [B] KV 缓存仅在训练阶段使用
- [C] KV 缓存的大小与序列长度无关
- [D] KV 缓存必须存储在 CPU 内存中

**参考答案**：0

**解析**：KV 缓存存储键和值，用于自回归解码时避免重复计算；它主要在推理阶段使用，大小随序列长度增长，通常存储在 GPU 显存。

### single_choice · None



- [A] 动态决定哪些序列加入或退出当前批次
- [B] 将模型权重分配到多张 GPU
- [C] 对输入文本进行分词
- [D] 将模型转换为半精度

**参考答案**：0

**解析**：调度器负责在连续批处理中动态管理序列的加入和退出；权重分配、分词、精度转换由其他组件完成。

### single_choice · None



- [A] 大规模语言模型的训练
- [B] 高吞吐量的在线推理服务
- [C] 离线批量文本生成
- [D] OpenAI 兼容的 API 服务

**参考答案**：0

**解析**：vLLM 专注于推理，不用于训练；在线服务、离线批量生成、OpenAI 兼容 API 都是其典型场景。

### single_choice · None



- [A] generate
- [B] fit
- [C] train
- [D] compile

**参考答案**：0

**解析**：LLM 类通过 generate 方法生成文本；fit、train、compile 并非其推理方法。

### single_choice · None



- [A] dtype
- [B] max_model_len
- [C] seed
- [D] swap_space

**参考答案**：0

**解析**：dtype 指定权重数据类型，如 float16、bfloat16；max_model_len 指定最大序列长度，seed 设置随机种子，swap_space 设置交换空间。

### single_choice · None



- [A] 为每个模型启动独立的 vLLM 服务实例
- [B] 在一个 LLM 实例中加载所有模型
- [C] 使用 vLLM 的 Pipeline 类串联多个模型
- [D] 使用 vLLM 的 DataLoader 类动态加载模型

**参考答案**：0

**解析**：vLLM 的单个 LLM 实例通常对应一个模型；服务多个模型可通过启动多个实例实现。Pipeline 和 DataLoader 并非 vLLM 用于多模型服务的 API。

### single_choice · None



- [A] 请求完成后可立即释放资源并加入新请求，无需等待整批结束
- [B] 将多个请求的输入拼接成一个更长的序列，减少前向次数
- [C] 在训练阶段动态调整批次大小以节省显存
- [D] 自动选择最优的模型并行策略

**参考答案**：0

**解析**：连续批处理允许在序列级别动态加入和退出请求，提高了 GPU 利用率；静态批处理需等待整批完成。

### single_choice · None



- [A] from vllm import LLM; llm = LLM(model="meta-llama/Llama-2-7b-hf")
- [B] import vllm; vllm.load_model("meta-llama/Llama-2-7b-hf")
- [C] from vllm import Model; m = Model.from_pretrained("meta-llama/Llama-2-7b-hf")
- [D] import vllm; vllm.init(model_path="meta-llama/Llama-2-7b-hf")

**参考答案**：0

**解析**：vLLM 提供 LLM 类用于离线推理，通过 LLM(model=...) 加载模型。其他选项中的函数或类并不存在于 vLLM 的公开 API 中。

### single_choice · None



- [A] 它借鉴了操作系统虚拟内存分页的思想来管理 KV 缓存
- [B] 它要求每个序列的 KV 缓存必须存储在连续的显存块中
- [C] 它仅适用于编码器-解码器架构的模型
- [D] 它通过压缩注意力头数量来减少显存占用

**参考答案**：0

**解析**：PagedAttention 借鉴操作系统分页机制，将 KV 缓存分成块并允许非连续存储，从而减少碎片；它适用于自回归解码，不要求连续显存。

### single_choice · None



- [A] 使用 vLLM 的 LLM 类配合 generate 方法批量生成
- [B] 使用 vLLM 的 Trainer 类进行多轮训练
- [C] 使用 vLLM 的 DataLoader 加载数据并调用 fit
- [D] 使用 vLLM 的 Pipeline 类串联多个模型

**参考答案**：0

**解析**：vLLM 的离线推理入口是 LLM 类，通过 generate 方法批量生成。Trainer、DataLoader、Pipeline 等并非 vLLM 的标准离线推理 API。

### single_choice · None



- [A] gpu_memory_utilization
- [B] max_batch_size
- [C] tensor_parallel_size
- [D] dtype

**参考答案**：0

**解析**：gpu_memory_utilization 用于指定 GPU 显存中用于模型权重和 KV 缓存的比例；max_batch_size 控制批大小，tensor_parallel_size 控制张量并行度，dtype 控制数据类型。

### single_choice · None



- [A] 通过设置 tensor_parallel_size 为 GPU 数量，将模型权重切分到多张 GPU 上
- [B] 张量并行会自动将模型转换为量化版本以节省显存
- [C] 张量并行只能在 CPU 上运行，不能使用 GPU
- [D] 张量并行要求每张 GPU 都保存完整的模型权重副本

**参考答案**：0

**解析**：vLLM 通过 tensor_parallel_size 指定张量并行度，将模型权重切分到多张 GPU；它并不自动量化，也不要求每张 GPU 保存完整权重。

### single_choice · None



- [A] temperature
- [B] max_tokens
- [C] top_p
- [D] stop

**参考答案**：0

**解析**：temperature 控制采样随机性；max_tokens 控制最大生成长度；top_p 控制核采样范围；stop 指定停止字符串。

### single_choice · None



- [A] temperature 被设置为 0
- [B] top_p 被设置为 1.0
- [C] max_tokens 被设置为 1
- [D] stop 参数为空

**参考答案**：0

**解析**：temperature=0 时模型进行贪心解码，输出确定；top_p=1.0 仍可能采样；max_tokens 和 stop 不影响随机性。

### single_choice · None



- [A] 静态批处理：必须等同一批所有请求都生成完毕才能返回，短请求会被长请求阻塞
- [B] 连续批处理：某条请求生成结束后，可立即把新请求插入该空闲槽位继续计算
- [C] 连续批处理要求所有请求的输入长度与输出长度完全一致才能工作
- [D] 流式输出必须在静态批处理下才能实现

**参考答案**：1

**解析**：连续批处理（continuous batching）的核心是在序列级别动态调度，某条序列完成后即可让新请求占用其槽位，从而减少 GPU 空闲、降低长尾阻塞。静态批处理才会出现整批等待、被最长请求拖慢的问题；它对输入输出长度一致没有要求。

### single_choice · None



- [A] 把模型权重量化到 4bit 以减少显存占用
- [B] 把 KV 缓存按固定大小的块管理，减少显存碎片并支持块级共享
- [C] 把输入文本按 token 分页以便并行发送 HTTP 请求
- [D] 把多个用户的请求合并成一条 batch 以减少网络往返

**参考答案**：1

**解析**：分页注意力把 KV 缓存切分为固定大小的块，用类似操作系统虚拟内存分页的方式管理，显著降低显存碎片、提高显存利用率，并允许不同序列共享相同的块（如共享前缀）。量化、HTTP 分批、请求合并都不是它的作用。

### single_choice · None



- [A] 它限制的是输入 prompt 的 token 数，与输出无关
- [B] 它限制的是生成的输出 token 数，达到上限后生成会被截断
- [C] 它必须大于上下文窗口大小才能生效
- [D] 它会自动把超出部分的输入截断以保证输出完整

**参考答案**：1

**解析**：max_tokens 通常限制输出侧生成的 token 数，达到上限即停止，可能导致回答被截断。输入长度的限制一般由上下文窗口或服务端的输入长度限制控制，两者不同。

### single_choice · None



- [A] 夜间模型精度更高，计算更快
- [B] 高并发下请求排队等待组批与算力分配的时间增加，导致尾延迟上升
- [C] 白天网络丢包导致重传，延长了延迟
- [D] 白天用户输入的 prompt 更长，所以模型必然变慢

**参考答案**：1

**解析**：在错误率基本不变的前提下，延迟随并发上升，最典型的原因是排队与组批等待，以及共享算力导致的单请求变慢。模型精度不随昼夜变化；题干未提网络或输入长度变化。

### multi_choice · None



- [A] 模型权重的参数量与数值精度
- [B] 同时并发的序列数量（批大小）
- [C] 每条序列的上下文（KV 缓存）长度
- [D] 客户端使用的编程语言
- [E] HTTP 请求头中的 User-Agent

**参考答案**：[0, 1, 2]

**解析**：显存占用主要来自模型权重、KV 缓存以及中间激活。权重规模与精度、并发序列数、上下文长度都会显著影响显存。客户端语言与请求头不影响服务端显存。

### multi_choice · None



- [A] 可以降低显存占用，使更大的模型能放进已有的 GPU
- [B] 可能带来一定的精度损失，需要评估对任务效果的影响
- [C] 量化后模型的计算量与显存占用一定完全不变
- [D] 常与算子优化配合以提升推理吞吐
- [E] 量化只能用于训练阶段，不能在推理阶段使用

**参考答案**：[0, 1, 3]

**解析**：量化降低数值精度，从而减少显存占用并可能借助更高效的算子提升吞吐，但可能带来精度损失，需要针对任务评估。它并非对计算/显存毫无影响，也常用于推理阶段。

### multi_choice · None



- [A] 采用连续批处理而非静态批处理
- [B] 使用分页注意力减少 KV 缓存碎片
- [C] 对请求长度做合理限制并设置合适的批大小上限
- [D] 把每条请求串行处理，处理完一条再取下一条
- [E] 在服务端对相同前缀的请求复用已缓存的 KV 块

**参考答案**：[0, 1, 2, 4]

**解析**：连续批处理、分页 KV 缓存、长度限制与合理批大小、前缀复用都能提升 GPU 利用率与吞吐。逐条串行处理会让 GPU 大量空闲，吞吐反而最低。

### multi_choice · None



- [A] 输出是否达到了 max_tokens 上限而被截断
- [B] 输入长度加上期望输出是否超出了模型的上下文窗口
- [C] 客户端是否对响应做了超时或长度截断处理
- [D] GPU 的算力型号是否影响了 tokenizer 的分词结果
- [E] 服务端是否有停止条件（如停止符）过早触发

**参考答案**：[0, 1, 2, 4]

**解析**：输出被截断常见于达到 max_tokens、超出上下文窗口、客户端侧超时/截断、停止条件过早触发。GPU 型号不影响分词结果。

### fill_blank · None



**参考答案**：["KV", "kv", "KV缓存", "kv cache"]

**解析**：该缓存保存历史 token 的 key 与 value 投影，使每步只需计算新 token，从而显著降低计算量，通常被简称为 KV 缓存。

### fill_blank · None



**参考答案**：["流式", "stream", "streaming", "流式输出"]

**解析**：流式输出把生成过程分块返回给客户端，改善感知延迟。它不改变总计算量。

### code_reading · None



**参考答案**：最多请求生成 16 个输出 token；若模型到 16 个 token 仍未结束，输出会在上限处被截断。

**解析**：max_tokens 限制的是输出侧生成的 token 数。当达到该上限而模型尚未生成结束符时，结果会被截断；这与输入长度无关，也不是模型主动选择停止。

### scenario · None



**解析**：高并发下吞吐提升而首 token 延迟上升，本质是排队与组批等待、以及共享算力导致的单请求变慢。可考虑限制最大批大小、按延迟目标设置调度优先级、缩短排队时间、用分页 KV 缓存与量化降低显存压力以支撑更多并发，或在多副本间做负载均衡，从而在吞吐与延迟之间取得平衡。

### single_choice · None



- [A] 只能通过命令行工具调用，无法用编程语言直接调用
- [B] 通常同时提供 HTTP 接口和兼容 OpenAI 风格的接口，便于已有客户端迁移
- [C] 必须使用 UDP 协议传输才能获得低延迟
- [D] 接口一次只能返回一个 token，无法一次返回多个 token

**参考答案**：1

**解析**：主流推理服务通常暴露 HTTP 接口，并提供与 OpenAI 兼容的请求/响应结构，客户端可复用现有 SDK。传输协议并非必须 UDP；服务也可以在非流式模式下一次性返回完整结果。

### scenario · None



**解析**：多轮对话会让 KV 缓存随上下文增长而持续膨胀，逼近显存上限后新请求无法分配空间而被拒绝。可采取的措施包括：使用分页/块式 KV 缓存减少碎片并支持前缀共享；对上下文长度与并发数设置上限并在超出时排队或拒绝；对权重做量化以腾出显存；把长会话做截断或摘要以控制缓存增长。

### single_choice · None



- [A] 单张 GPU 显存不足以放下完整模型时，把权重切分到多张 GPU 上协同计算
- [B] 把同一个请求复制到多台机器上做冗余计算以提高准确率
- [C] 把多条请求分派到不同的 GPU 上以提升吞吐
- [D] 把模型权重从 GPU 卸载到 CPU 内存以节省显存

**参考答案**：0

**解析**：张量并行把单个层的权重矩阵按维度切分到多张 GPU，每张卡只保存一部分参数，从而让超出单卡显存的模型可以运行。请求级的分派属于数据并行/负载均衡，把权重卸载到 CPU 属于 offload，不是张量并行。

### single_choice · None



- [A] 模型权重被错误地量化，导致计算变慢
- [B] 增大批大小让计算更密集，单请求的排队与等待时间变长，因此首 token 延迟上升
- [C] 客户端网络带宽不足，导致请求发不出去
- [D] KV 缓存被完全禁用，每步都要重新计算全部前缀

**参考答案**：1

**解析**：批大小增大提高 GPU 利用率和整体吞吐，但请求需要等待组批、排队，且与更多序列共享算力，所以单请求的首 token 延迟会上升。这是吞吐与延迟之间的典型权衡，而不是量化或缓存被禁用导致。

### single_choice · None



- [A] temperature 越高，输出分布越尖锐，结果越确定
- [B] temperature 越低，输出分布越平坦，结果越随机
- [C] temperature 接近 0 时倾向于选择概率最高的 token，输出更确定
- [D] temperature 只影响输出长度，不影响 token 选择

**参考答案**：2

**解析**：temperature 用于缩放 logits：值越低分布越尖锐、越接近贪心解码，输出更确定；值越高分布越平坦、随机性越强。它影响的是 token 的选择分布，而不是输出长度。

### single_choice · None



- [A] 因为超出上下文窗口的输入无法被模型正确编码，且输出过长会显著增加显存与时间开销
- [B] 因为 HTTP 协议不允许超过 4096 字节的请求体
- [C] 因为超过限制后模型会自动改用另一个模型回答
- [D] 因为限制长度可以让模型完全避免幻觉

**参考答案**：0

**解析**：模型的上下文窗口有限，超出部分无法被注意力机制覆盖；输出越长，KV 缓存与生成步数越多，显存和时间开销线性增长，因此需要限制长度。HTTP 本身没有这个限制，长度限制也不能消除幻觉。

### single_choice · None



- [A] 减少模型的计算量，让生成更快完成
- [B] 让客户端在生成过程中逐步收到 token，改善感知延迟与交互体验
- [C] 把模型权重分片传输到客户端
- [D] 让服务端可以跳过解码阶段直接返回 prompt

**参考答案**：1

**解析**：流式输出并不减少总计算量，而是让用户在生成过程中逐步看到 token，从而降低感知延迟、改善交互体验。它不传输权重，也不会跳过解码。

### single_choice · None



- [A] 缓存的是模型权重，避免每步重新加载参数
- [B] 缓存的是已生成 token 的 key/value 投影，避免每步对全部前缀重新计算
- [C] 缓存的是用户的原始输入文本，避免重复分词
- [D] 缓存的是最终输出结果，用于命中相同请求时直接返回

**参考答案**：1

**解析**：自回归生成每步只需计算新 token，但注意力需要此前所有 token 的 key/value，因此把这些投影缓存下来，避免重复计算前缀，显著降低每步开销。它缓存的不是权重、原始文本或最终答案。

### single_choice · None



- [A] 把模型权重全部放到 CPU 上，每次前向都从内存读取
- [B] 结合张量并行把权重切分到多卡，并配合合适的批处理与显存管理策略
- [C] 把上下文窗口设为 1，这样显存占用最小
- [D] 关闭 KV 缓存，避免缓存占显存

**参考答案**：1

**解析**：单卡放不下时，常用做法是用张量并行把权重切到多卡，再配合连续批处理和分页 KV 缓存等显存管理策略来支撑并发。全放 CPU 会因带宽瓶颈严重变慢；把上下文设为 1 或关闭 KV 缓存都会破坏功能或使计算量暴涨。

### single_choice · None



- [A] 必须先手动下载模型文件并通过环境变量指定路径，ollama run 才会工作
- [B] ollama run 在本地不存在该模型时通常会自动先拉取再运行
- [C] ollama pull 只能拉取已在本地的模型进行校验，不会真正下载
- [D] 模型拉取后必须手动编译成二进制才能被调用

**参考答案**：1

**解析**：Ollama 的设计是：运行一个本地不存在的模型时，会自动从模型库拉取后再启动；也可以先用 pull 显式拉取。A 错误在于无需手动指定路径；C 曲解了 pull 的作用；D 是常见误解，Ollama 不需要用户手动编译模型。

### single_choice · None



- [A] 它只能被 Ollama 自带的命令行工具访问，其他程序无法调用
- [B] 它默认在本机某端口提供 REST 风格接口，程序可通过 HTTP 请求调用模型
- [C] 它要求必须连接公网才能响应生成请求
- [D] 它只支持流式返回，无法获得一次性完整响应

**参考答案**：1

**解析**：Ollama 在本地启动一个 HTTP 服务，默认监听本机端口，提供 REST 风格接口（如生成、对话等），本地程序可通过 HTTP 调用；也支持流式与非流式。A、C、D 均为常见误解。

### multi_choice · None



- [A] 可以在本地拉取并运行多种开源模型
- [B] 程序可以通过本地 HTTP 接口调用模型完成生成任务
- [C] 模型必须联网才能推理，离线无法使用
- [D] 运行模型会占用本机内存/显存，模型越大占用通常越高

**参考答案**：[0, 1, 3]

**解析**：Ollama 支持本地拉取运行多种开源模型、提供本地 HTTP 接口供程序调用，且推理会占用本地内存/显存。C 错误：一旦模型已在本地，推理可离线进行。

### multi_choice · None



- [A] 按角色（如 system / user / assistant）组织消息列表
- [B] 根据需要传入或覆盖系统提示词来约束模型行为
- [C] 每次请求都把全部历史无限制地拼接进去，从不裁剪
- [D] 通过参数控制是否流式返回

**参考答案**：[0, 1, 3]

**解析**：对话请求通常按角色组织消息、可设置系统提示词、可控制流式。C 不合理：无限制拼接历史会超出上下文窗口并影响效果，应裁剪或摘要。

### multi_choice · None



- [A] 检查是否因内存/显存不足导致大量换页或降级到较慢路径
- [B] 尝试使用量化程度更高、更小的模型变体
- [C] 确认请求是否使用了流式，避免误以为是「卡住」
- [D] 把模型文件复制到多个目录以提升速度

**参考答案**：[0, 1, 2]

**解析**：速度慢常见原因包括资源不足、模型过大，以及把流式输出误判为无响应。复制模型文件不会提升推理速度，D 无依据。

### multi_choice · None



- [A] 可以用任意支持 HTTP 请求的编程语言与之交互
- [B] 通常需要保证请求地址与 Ollama 实际监听的地址、端口一致
- [C] 遇到连接错误时应先确认服务是否已启动
- [D] 必须把模型源码复制到自己的 Python 项目里才能调用

**参考答案**：[0, 1, 2]

**解析**：Ollama 通过 HTTP 暴露能力，任何能发 HTTP 请求的语言都可集成；地址端口需匹配；连接错误优先排查服务是否启动。D 无依据，调用是通过接口而非复制模型源码。

### fill_blank · None



**参考答案**：["请求", "request", "requests", "HTTP 请求", "http 请求"]

**解析**：Ollama 对外提供 REST 风格接口，调用方通过发送 HTTP 请求来使用生成/对话功能。

### fill_blank · None



**参考答案**：["标签", "tag", "tags", "标签（tag）"]

**解析**：模型名后附带的部分（如 :latest 等）是标签，用于区分不同版本或量化规格。

### fill_blank · None



**参考答案**：["temperature", "温度", "temperature 参数", "temp"]

**解析**：temperature 用于控制采样随机性：值越大越随机多样，越小越确定。

### code_reading · None



**参考答案**：能。因为设置了非流式（stream=False），服务会把生成的完整结果聚合后一次性返回，而不是逐段推送，所以调用方能直接拿到一段完整回答文本。

**解析**：该伪代码演示了带系统提示词的对话请求，并显式设置非流式，因此返回的是完整结果；若改为流式则需逐块拼接。

### code_reading · None



**参考答案**：因为本地 Ollama 对话接口通常是无状态的，服务端不替调用方保存上下文，必须由调用方把历史消息一并带上。若不追加历史消息，每轮请求只包含当前这一条，模型看不到之前的对话，就无法进行连贯的多轮对话，会「忘记」上下文。

**解析**：该循环演示了手动维护对话历史：把每轮的模型回复也放回 messages，下一轮请求才带有完整上下文。不维护历史会导致多轮对话失忆。

### scenario · None



**解析**：连接被拒绝通常意味着目标地址端口没有服务在监听。应首先确认 Ollama 服务是否已启动、是否正在监听期望的地址与端口，再核对脚本用的地址端口是否与之完全一致；可分别在终端和脚本中验证连通性。模型是否拉取不直接影响连接是否被拒。

### single_choice · None



- [A] 必须使用流式，否则服务会报错
- [B] 可以通过参数控制是否流式，非流式时得到完整结果后再一次返回
- [C] 非流式会丢失所有 token
- [D] 是否流式由模型文件决定，调用方无法选择

**参考答案**：1

**解析**：Ollama 的生成接口通常支持通过参数选择流式或非流式返回；非流式会聚合完整结果后返回。流式与否由调用参数决定，而非模型文件或强制要求。

### scenario · None



**解析**：Ollama 能在本地运行模型，数据不必离开本机，符合数据可控与离线要求；可通过生成参数（如温度）控制随机程度；但要注意本地内存/显存等资源限制，必要时选用更小或量化程度更高的模型，并妥善管理对话上下文长度。

### single_choice · None



- [A] 标签只是显示用，实际加载的永远是同一个权重
- [B] 标签用于区分同一模型的不同版本或量化规格，不同标签可能对应不同大小与效果
- [C] 标签必须是纯数字，否则无法加载
- [D] 只要模型名相同，标签不同也会强制报错

**参考答案**：1

**解析**：在 Ollama 中，模型名通常可带标签，用来区分不同版本或量化规格，不同标签对应的文件大小与效果可能不同。A、C、D 均为错误理解。

### single_choice · None



- [A] 模型大小与内存占用无关，只要磁盘够就行
- [B] 量化后模型通常更小、更省内存，但可能带来一定效果损失
- [C] 只要把模型放到磁盘上，运行时完全不占内存
- [D] 内存不足时 Ollama 会自动把模型训练得更大以适应

**参考答案**：1

**解析**：量化会压缩权重，使模型文件更小、运行时占用更少内存/显存，但可能牺牲一定质量。运行时必须把权重加载进内存/显存，磁盘够并不等于能跑；内存不足不会「训练得更大」。

### single_choice · None



- [A] 系统提示词只能在服务端配置文件中全局修改，单次请求无法覆盖
- [B] 可以通过请求参数传入或覆盖系统提示词，从而影响模型行为
- [C] 系统提示词对输出没有任何影响
- [D] 系统提示词只对非流式请求生效

**参考答案**：1

**解析**：Ollama 的接口通常允许在请求中传入系统提示词（可覆盖模型自带模板的一部分行为），从而影响生成结果；它对流式与非流式都有效。

### single_choice · None



- [A] 模型权重文件损坏
- [B] 本地 Ollama 服务未启动或监听地址/端口与请求的不一致
- [C] Python 版本过低
- [D] 请求里没有写系统提示词

**参考答案**：1

**解析**：连接被拒绝通常表示目标地址/端口上没有服务在监听，即服务未启动或地址端口不匹配；与权重损坏、Python 版本或是否写系统提示词无关。

### single_choice · None



- [A] Ollama 只能联网使用，与云 API 没有区别
- [B] Ollama 侧重在本地运行模型，数据不必离开本机，但受本地算力限制
- [C] Ollama 运行模型不需要任何硬件资源
- [D] 云 API 无法流式返回，只有 Ollama 可以

**参考答案**：1

**解析**：Ollama 的核心价值是本地运行模型，数据可控、可离线，但受本地内存/算力限制。A、C、D 均为明显错误或常见误解。

### single_choice · None



- [A] 服务端会自动永久保存每次对话，下次请求自动带上全部历史
- [B] 调用方需要在请求中自行携带历史消息，服务端通常不替你管理上下文
- [C] 对话历史只能保存一条消息
- [D] 历史消息越长，模型响应一定越准确，无需裁剪

**参考答案**：1

**解析**：Ollama 的对话接口通常是无状态风格：需要调用方在请求里自行带上历史消息来构造上下文；服务端一般不为调用方维护长期会话；历史过长还会挤占上下文窗口，需要裁剪。

### single_choice · None



- [A] 温度越高输出越确定，越低越随机
- [B] 温度越高输出通常越随机多样，越低越趋向确定性
- [C] 温度只能设为 0 或 1 两个值
- [D] 温度参数只影响服务启动速度，不影响输出

**参考答案**：1

**解析**：temperature 越大，采样分布越平坦，输出越随机多样；越小则越趋向确定性。它会影响输出而非启动速度，取值也非只有 0/1。
