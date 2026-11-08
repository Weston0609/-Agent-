"""检索器 —— 混合检索（向量 + 关键词）+ rerank。

离线零 token：向量用 VectorStore，关键词用 BM25 简化（词频），rerank 用引用计数加权。
"""
from __future__ import annotations

from .vector_store import VectorStore


class Retriever:
    def __init__(self, vector_store: VectorStore) -> None:
        self.vs = vector_store

    def retrieve(self, query: str, top_k: int = 5) -> list[dict]:
        """混合检索：向量 top_k 与关键词 top_k 合并去重，按分排序。"""
        vector_hits = self.vs.search(query, top_k=top_k)
        keyword_hits = self._keyword_search(query, top_k=top_k)
        merged: dict[str, dict] = {}
        for h in vector_hits:
            merged[h["id"]] = {**h, "score": h["score"] * 1.0}
        for h in keyword_hits:
            if h["id"] in merged:
                merged[h["id"]]["score"] += h["score"] * 0.5
            else:
                merged[h["id"]] = {**h, "score": h["score"] * 0.5}
        ranked = sorted(merged.values(), key=lambda x: -x["score"])
        return self._rerank(query, ranked[:top_k])

    def _keyword_search(self, query: str, top_k: int = 5) -> list[dict]:
        terms = set(query.lower().split())
        hits = []
        for doc_id, d in self._iter_docs():
            text = d["text"].lower()
            score = sum(text.count(t) for t in terms if t)
            if score > 0:
                hits.append({"id": doc_id, "score": score, **d})
        hits.sort(key=lambda x: -x["score"])
        return hits[:top_k]

    def _rerank(self, query: str, hits: list[dict]) -> list[dict]:
        # 简化 rerank：title 命中加分
        ql = query.lower()
        for h in hits:
            meta = h.get("meta") or {}
            title = str(meta.get("title", "")).lower()
            if title and any(t in title for t in ql.split()):
                h["score"] += 0.2
        hits.sort(key=lambda x: -x["score"])
        return hits

    def _iter_docs(self):
        # 复用 VectorStore 内部 dict
        return self.vs._docs.items()
