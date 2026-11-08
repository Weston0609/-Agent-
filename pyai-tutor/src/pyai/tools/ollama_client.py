"""本地 Ollama 封装 —— 无 DEEPSEEK_API_KEY 时的离线生成后端（W6 D4/D5）。

零 token、零外部服务：只连本机 127.0.0.1:11434。没装/没启动 Ollama 时 `configured=False`，
更新管道自动跳过生成阶段（status=skipped_no_key），完全不影响离线学习路径。

接口与 DeepSeekClient 对齐（configured / chat / last_tokens），管道可互换使用。
"""
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request

log = logging.getLogger(__name__)


class OllamaClient:
    def __init__(self, base_url: str = "http://127.0.0.1:11434", model: str = "qwen2.5:7b",
                 timeout: int = 300) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.last_tokens = 0          # 本地推理不产生 API 计费
        self._probed: bool | None = None

    @property
    def configured(self) -> bool:
        """探活一次并缓存：GET /api/tags 通即视为可用。"""
        if self._probed is None:
            self._probed = self._probe()
        return self._probed

    def _probe(self) -> bool:
        try:
            with urllib.request.urlopen(f"{self.base_url}/api/tags", timeout=3) as resp:
                return resp.status == 200
        except (urllib.error.URLError, OSError, ValueError):
            return False

    def chat(self, prompt: str, system: str | None = None) -> str:
        if not self.configured:
            raise RuntimeError("本地 Ollama 不可达，无法离线生成")
        payload: dict = {"model": self.model, "prompt": prompt, "stream": False}
        if system:
            payload["system"] = system
        req = urllib.request.Request(
            f"{self.base_url}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data.get("response", "")


# 别名：与 DeepSeek 命名风格一致
Ollama = OllamaClient
