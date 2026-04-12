from __future__ import annotations

from typing import Protocol

from llmscope.types.runs import RunRecord


class AbstractExporter(Protocol):
    async def export(self, runs: list[RunRecord], output_path: str) -> None: ...
