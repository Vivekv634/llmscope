from __future__ import annotations

import json

from llmscope.types.config import AppConfig


class OllamaBackend:
    def __init__(self, config: AppConfig) -> None:
        self._config: AppConfig = config

    @property
    def name(self) -> str:
        return "ollama"

    @property
    def base_url(self) -> str:
        return self._config.backend_url

    def generate_url(self) -> str:
        return f"{self.base_url}/api/generate"

    def chat_url(self) -> str:
        return f"{self.base_url}/api/chat"

    async def parse_chunk(self, raw: str) -> str:
        try:
            data: object = json.loads(raw)
            if isinstance(data, dict):
                return str(data.get("response", ""))
            return ""
        except json.JSONDecodeError:
            return ""
