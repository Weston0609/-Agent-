"""DeepSeek API 封装 —— 唯一烧 token 的网络出口。

仅在 updater 管线调用；离线学习路径永不触达这里。
API key 来自环境变量 DEEPSEEK_API_KEY，缺省时抛错，不静默失败。
"""
from __future__ import annotations

import json
import os
import urllib.request


class DeepSeekClient:
    API_URL = "https://api.deepseek.com/chat/completions"

    def __init__(self, api_key: str | None = None, model: str = "deepseek-chat") -> None:
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY", "")
        self.model = model
        self.last_tokens = 0

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def chat(self, prompt: str, system: str | None = None) -> str:
        if not self.configured:
            raise RuntimeError("未设置 DEEPSEEK_API_KEY，无法调用在线生成")
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        payload = json.dumps({"model": self.model, "messages": messages}).encode("utf-8")
        req = urllib.request.Request(
            self.API_URL, data=payload, method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
        )
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        self.last_tokens = (data.get("usage") or {}).get("total_tokens", 0)
        return data["choices"][0]["message"]["content"]


# 别名：骨架 `from pyai.tools.deepseek_client import DeepSeek`
DeepSeek = DeepSeekClient
