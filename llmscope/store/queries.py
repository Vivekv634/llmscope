from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import duckdb

from llmscope.types.runs import OutputRecord, RunRecord, TokenRecord
from llmscope.types.stats import StatsRecord

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


def get_run_by_id(conn: duckdb.DuckDBPyConnection, run_id: str) -> RunRecord | None:
    row: tuple[Any, ...] | None = conn.execute(
        f"SELECT {_RUN_COLUMNS} FROM runs WHERE run_id = ?", [run_id]
    ).fetchone()
    if row is None:
        return None
    return _to_run_record(row)


def list_runs(
    conn: duckdb.DuckDBPyConnection,
    limit: int = 50,
    model: str | None = None,
    tag: str | None = None,
    q: str | None = None,
) -> list[RunRecord]:
    conditions: list[str] = []
    params: list[Any] = []

    if model is not None:
        conditions.append("model = ?")
        params.append(model)
    if tag is not None:
        conditions.append("tags LIKE ?")
        params.append(f'%"{tag}"%')
    if q is not None:
        conditions.append("prompt_text ILIKE ?")
        params.append(f"%{q}%")

    where: str = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    params.append(limit)
    rows: list[tuple[Any, ...]] = conn.execute(
        f"SELECT {_RUN_COLUMNS} FROM runs {where} ORDER BY created_at DESC LIMIT ?",
        params,
    ).fetchall()
    return [_to_run_record(row) for row in rows]


def list_tags(conn: duckdb.DuckDBPyConnection) -> list[str]:
    rows: list[tuple[Any, ...]] = conn.execute(
        "SELECT DISTINCT tags FROM runs WHERE tags IS NOT NULL AND tags != '[]'"
    ).fetchall()
    seen: set[str] = set()
    for row in rows:
        try:
            for tag in json.loads(str(row[0])):
                seen.add(str(tag))
        except (json.JSONDecodeError, TypeError):
            pass
    return sorted(seen)


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
) -> OutputRecord | None:
    row: tuple[Any, ...] | None = conn.execute(
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


def get_stats(conn: duckdb.DuckDBPyConnection) -> StatsRecord:
    total_runs_row: tuple[Any, ...] | None = conn.execute(
        "SELECT COUNT(*) FROM runs"
    ).fetchone()
    total_runs: int = int(total_runs_row[0]) if total_runs_row else 0

    total_tokens_row: tuple[Any, ...] | None = conn.execute(
        "SELECT COUNT(*) FROM tokens"
    ).fetchone()
    total_tokens: int = int(total_tokens_row[0]) if total_tokens_row else 0

    avg_tps_row: tuple[Any, ...] | None = conn.execute(
        "SELECT COALESCE(AVG(tps), 0) FROM runs WHERE tps IS NOT NULL"
    ).fetchone()
    avg_tps: float = float(avg_tps_row[0]) if avg_tps_row else 0.0

    avg_ttft_row: tuple[Any, ...] | None = conn.execute(
        "SELECT COALESCE(AVG(ttft_ms), 0) FROM runs WHERE ttft_ms IS NOT NULL"
    ).fetchone()
    avg_ttft_ms: float = float(avg_ttft_row[0]) if avg_ttft_row else 0.0

    model_rows: list[tuple[Any, ...]] = conn.execute(
        "SELECT model, COUNT(*) FROM runs GROUP BY model ORDER BY COUNT(*) DESC"
    ).fetchall()
    model_breakdown: dict[str, int] = {str(row[0]): int(row[1]) for row in model_rows}

    return StatsRecord(
        total_runs=total_runs,
        total_tokens=total_tokens,
        avg_tps=round(avg_tps, 2),
        avg_ttft_ms=round(avg_ttft_ms, 2),
        model_breakdown=model_breakdown,
    )
