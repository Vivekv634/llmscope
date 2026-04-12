from __future__ import annotations

import json

from llmscope.types.config import AppConfig


class LlamaCppBackend:
    def __init__(self, config: AppConfig) -> None:
        self._config: AppConfig = config

    @property
    def name(self) -> str:
        return "llamacpp"

    @property
    def base_url(self) -> str:
        return self._config.backend_url

    def generate_url(self) -> str:
        return f"{self.base_url}/completion"

    def chat_url(self) -> str:
        return f"{self.base_url}/v1/chat/completions"

    async def parse_chunk(self, raw: str) -> str:
        stripped: str = raw.strip()
        if stripped.startswith("data: "):
            stripped = stripped[6:]
        if stripped == "[DONE]":
            return ""
        try:
            data: object = json.loads(stripped)
            if isinstance(data, dict):
                return str(data.get("content", ""))
            return ""
        except json.JSONDecodeError:
            return ""
