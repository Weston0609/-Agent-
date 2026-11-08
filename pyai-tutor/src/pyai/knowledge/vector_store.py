"""向量存储 —— 纯内存 cosine 相似度（哈希词袋向量）。

W2 D4 决策：不上 Chroma 硬依赖。真向量库需要额外的 embedding 后端（本地 ONNX 模型需下载，
在线 API 要烧 token），两者都与「离线 0 token」冲突；而当前检索只用于
`update` 阶段把抓取到的权威源 chunk 匹配给待生成 KP（几百条文档），内存实现足够。
需要时应整体替换本类——对外接口只有 add / search。
"""
from __future__ import annotations

import math
import re
from collections import Counter

_TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+")


def _bag(text: str) -> Counter:
    return Counter(_TOKEN_RE.findall(text.lower()))


def _cosine(a: Counter, b: Counter) -> float:
    if not a or not b:
        return 0.0
    dot = sum(a[k] * b[k] for k in a.keys() & b.keys())
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


class VectorStore:
    """本地内存向量存储。"""

    def __init__(self) -> None:
        self._docs: dict[str, dict] = {}  # id -> {text, meta}

    def add(self, doc_id: str, text: str, meta: dict | None = None) -> None:
        self._docs[doc_id] = {"text": text, "meta": meta or {}}

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        q = _bag(query)
        scored = []
        for doc_id, d in self._docs.items():
            s = _cosine(q, _bag(d["text"]))
            if s > 0:
                scored.append({"id": doc_id, "score": s, **d})
        scored.sort(key=lambda x: -x["score"])
        return scored[:top_k]

    def __len__(self) -> int:
        return len(self._docs)
