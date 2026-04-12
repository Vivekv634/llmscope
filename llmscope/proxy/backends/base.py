from __future__ import annotations

from typing import Protocol


class AbstractBackend(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def base_url(self) -> str: ...

    def generate_url(self) -> str: ...

    def chat_url(self) -> str: ...

    async def parse_chunk(self, raw: str) -> str: ...
