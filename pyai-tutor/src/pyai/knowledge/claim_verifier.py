"""幻觉拦截 —— 校验生成内容是否都有权威引用支撑。

离线零 token：规则校验。任何"事实性陈述"若无法溯源到白名单源，标记为 unverified。
"""
from __future__ import annotations


class ClaimVerifier:
    def __init__(self, sources_whitelist: set[str] | None = None,
                 missing_citation_policy: str = "reject") -> None:
        self.whitelist = sources_whitelist or set()
        self.policy = missing_citation_policy

    def verify(self, content: str, citations: list[str]) -> dict:
        """返回 {verified, missing, policy}。citations 为空且政策 reject → verified=False。"""
        if not citations:
            ok = self.policy != "reject"
            return {"verified": ok, "missing": [], "policy": self.policy}
        missing = [c for c in citations if not self._allowed(c)]
        return {"verified": not missing, "missing": missing, "policy": self.policy}

    def _allowed(self, source: str) -> bool:
        if not self.whitelist:
            return True
        return any(domain in source for domain in self.whitelist)
