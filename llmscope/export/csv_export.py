from __future__ import annotations

import csv
import io

import anyio

from llmscope.types.runs import RunRecord

_FIELDS: list[str] = [
    "run_id",
    "model",
    "backend",
    "prompt_hash",
    "created_at",
    "ttft_ms",
    "total_ms",
    "token_count",
    "tps",
    "quality_score",
    "tags",
]


class CsvExporter:
    async def export(self, runs: list[RunRecord], output_path: str) -> None:
        buf: io.StringIO = io.StringIO()
        writer: csv.DictWriter[str] = csv.DictWriter(
            buf, fieldnames=_FIELDS, extrasaction="ignore"
        )
        writer.writeheader()
        for run in runs:
            row: dict[str, object] = run.model_dump(mode="json")
            row["tags"] = ",".join(run.tags)
            writer.writerow({k: row.get(k, "") for k in _FIELDS})
        async with await anyio.open_file(output_path, "w", encoding="utf-8") as f:
            await f.write(buf.getvalue())
