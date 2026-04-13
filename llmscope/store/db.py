from __future__ import annotations

import json
import os
import pathlib
from datetime import UTC, datetime

import duckdb

from llmscope.signals.quality import output_entropy
from llmscope.store import queries
from llmscope.types.events import DoneEvent, RunStartEvent, TokenEvent, TTFTEvent
from llmscope.types.runs import OutputRecord, RunRecord, TokenRecord
from llmscope.types.stats import StatsRecord

SCHEMA_VERSION: int = 1


class DatabaseStore:
    def __init__(self, db_path: str) -> None:
        if db_path == ":memory:":
            self._conn: duckdb.DuckDBPyConnection = duckdb.connect(":memory:")
        else:
            expanded: str = os.path.expanduser(db_path)
            os.makedirs(os.path.dirname(expanded), exist_ok=True)
            self._conn = duckdb.connect(expanded)
        self._apply_schema()

    def _apply_schema(self) -> None:
        schema_path: pathlib.Path = pathlib.Path(__file__).parent / "schema.sql"
        sql_text: str = schema_path.read_text()
        statements: list[str] = [
            s.strip() for s in sql_text.split(";") if s.strip()
        ]
        for statement in statements:
            self._conn.execute(statement)
        row = self._conn.execute(
            "SELECT version FROM schema_version ORDER BY applied_at DESC LIMIT 1"
        ).fetchone()
        if row is None:
            self._conn.execute(
                "INSERT INTO schema_version (version) VALUES (?)",
                [SCHEMA_VERSION],
            )

    def get_schema_version(self) -> int:
        row = self._conn.execute(
            "SELECT version FROM schema_version ORDER BY applied_at DESC LIMIT 1"
        ).fetchone()
        return int(row[0]) if row else 0

    def record_start(self, event: RunStartEvent) -> None:
        self._conn.execute(
            """
            INSERT INTO runs
                (run_id, model, backend, prompt_hash, prompt_text, created_at, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT DO NOTHING
            """,
            [
                event.run_id,
                event.model,
                event.backend,
                event.prompt_hash,
                event.prompt_text,
                datetime.now(UTC).replace(tzinfo=None),
                json.dumps([]),
            ],
        )

    def record_ttft(self, event: TTFTEvent) -> None:
        self._conn.execute(
            "UPDATE runs SET ttft_ms = ? WHERE run_id = ?",
            [event.ttft_ms, event.run_id],
        )

    def record_token(self, event: TokenEvent) -> None:
        self._conn.execute(
            """
            INSERT INTO tokens (run_id, position, text, arrived_at_ms)
            VALUES (?, ?, ?, ?)
            ON CONFLICT DO NOTHING
            """,
            [event.run_id, event.position, event.text, event.arrived_at_ms],
        )

    def finalize_run(self, event: DoneEvent) -> None:
        rows: list[tuple[object, ...]] = self._conn.execute(
            "SELECT text, arrived_at_ms FROM tokens WHERE run_id = ? ORDER BY position",
            [event.run_id],
        ).fetchall()
        token_count: int = len(rows)
        tps: float = (
            round(token_count / (event.total_ms / 1000.0), 2)
            if event.total_ms > 0
            else 0.0
        )
        token_texts: list[str] = [
            str(row[0]) for row in rows if row[0] is not None
        ]
        full_text: str = "".join(token_texts)
        quality_score: float = output_entropy(token_texts).entropy_score
        self._conn.execute(
            """
            UPDATE runs
            SET total_ms = ?, token_count = ?, tps = ?, quality_score = ?
            WHERE run_id = ?
            """,
            [event.total_ms, token_count, tps, quality_score, event.run_id],
        )
        self._conn.execute(
            """
            INSERT INTO outputs (run_id, full_text, token_count)
            VALUES (?, ?, ?)
            ON CONFLICT DO NOTHING
            """,
            [event.run_id, full_text, token_count],
        )

    def set_tags(self, run_id: str, tags: list[str]) -> None:
        self._conn.execute(
            "UPDATE runs SET tags = ? WHERE run_id = ?",
            [json.dumps(tags), run_id],
        )

    def get_run(self, run_id: str) -> RunRecord | None:
        return queries.get_run_by_id(self._conn, run_id)

    def list_runs(
        self,
        limit: int = 50,
        model: str | None = None,
        tag: str | None = None,
        q: str | None = None,
    ) -> list[RunRecord]:
        return queries.list_runs(self._conn, limit, model=model, tag=tag, q=q)

    def list_tags(self) -> list[str]:
        return queries.list_tags(self._conn)

    def get_tokens(self, run_id: str) -> list[TokenRecord]:
        return queries.get_tokens_for_run(self._conn, run_id)

    def get_output(self, run_id: str) -> OutputRecord | None:
        return queries.get_output_for_run(self._conn, run_id)

    def get_stats(self) -> StatsRecord:
        return queries.get_stats(self._conn)

    def close(self) -> None:
        self._conn.close()
