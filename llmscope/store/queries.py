from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, Optional

import duckdb

from llmscope.types.runs import OutputRecord, RunRecord, TokenRecord

_RUN_COLUMNS: str = (
    "run_id, model, backend, prompt_hash, prompt_text, created_at, "
    "ttft_ms, total_ms, token_count, tps, quality_score, tags"
)


def _to_run_record(row: tuple[Any, ...]) -> RunRecord:
    tags_raw: Any = row[11]
    tags: list[str] = json.loads(str(tags_raw)) if tags_raw is not None else []
    created_raw: Any = row[5]
    created_at: datetime = (
        created_raw
        if isinstance(created_raw, datetime)
        else datetime.now(UTC).replace(tzinfo=None)
    )
    return RunRecord(
        run_id=str(row[0]),
        model=str(row[1]),
        backend=str(row[2]),
        prompt_hash=str(row[3]),
        prompt_text=str(row[4]) if row[4] is not None else None,
        created_at=created_at,
        ttft_ms=float(row[6]) if row[6] is not None else None,
        total_ms=float(row[7]) if row[7] is not None else None,
        token_count=int(row[8]) if row[8] is not None else None,
        tps=float(row[9]) if row[9] is not None else None,
        quality_score=float(row[10]) if row[10] is not None else None,
        tags=tags,
    )


def get_run_by_id(
    conn: duckdb.DuckDBPyConnection, run_id: str
) -> Optional[RunRecord]:
    row: Optional[tuple[Any, ...]] = conn.execute(
        f"SELECT {_RUN_COLUMNS} FROM runs WHERE run_id = ?", [run_id]
    ).fetchone()
    if row is None:
        return None
    return _to_run_record(row)


def list_runs(
    conn: duckdb.DuckDBPyConnection, limit: int = 50
) -> list[RunRecord]:
    rows: list[tuple[Any, ...]] = conn.execute(
        f"SELECT {_RUN_COLUMNS} FROM runs ORDER BY created_at DESC LIMIT ?",
        [limit],
    ).fetchall()
    return [_to_run_record(row) for row in rows]


def get_tokens_for_run(
    conn: duckdb.DuckDBPyConnection, run_id: str
) -> list[TokenRecord]:
    rows: list[tuple[Any, ...]] = conn.execute(
        "SELECT run_id, position, text, arrived_at_ms FROM tokens "
        "WHERE run_id = ? ORDER BY position",
        [run_id],
    ).fetchall()
    return [
        TokenRecord(
            run_id=str(row[0]),
            position=int(row[1]),
            text=str(row[2]) if row[2] is not None else "",
            arrived_at_ms=float(row[3]),
        )
        for row in rows
    ]


def get_output_for_run(
    conn: duckdb.DuckDBPyConnection, run_id: str
) -> Optional[OutputRecord]:
    row: Optional[tuple[Any, ...]] = conn.execute(
        "SELECT run_id, full_text, token_count FROM outputs WHERE run_id = ?",
        [run_id],
    ).fetchone()
    if row is None:
        return None
    return OutputRecord(
        run_id=str(row[0]),
        full_text=str(row[1]),
        token_count=int(row[2]),
    )
