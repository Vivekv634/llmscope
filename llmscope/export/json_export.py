from __future__ import annotations

import json

import anyio

from llmscope.types.runs import RunRecord


class JsonExporter:
    async def export(self, runs: list[RunRecord], output_path: str) -> None:
        payload: list[dict[str, object]] = [
            r.model_dump(mode="json") for r in runs
        ]
        data: str = json.dumps(payload, indent=2, default=str)
        async with await anyio.open_file(output_path, "w", encoding="utf-8") as f:
            await f.write(data)
