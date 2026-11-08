"""知识层：抓取去重、向量检索、混合检索 rerank、幻觉拦截。

核心为"零 token"——本地检索/去重不联网；claim_verifier 用引用校验兜底幻觉。
"""
from .claim_verifier import ClaimVerifier
from .ingest import crawl_whitelisted
from .retriever import Retriever
from .vector_store import VectorStore

__all__ = ["ClaimVerifier", "crawl_whitelisted", "Retriever", "VectorStore"]
