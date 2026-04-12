from __future__ import annotations

from datetime import datetime, UTC
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from llmscope.proxy.backends.ollama import OllamaBackend
from llmscope.proxy.server import create_app
from llmscope.store.db import DatabaseStore
from llmscope.types.config import AppConfig
from llmscope.types.events import DoneEvent, RunStartEvent, TTFTEvent, TokenEvent


def _make_app() -> tuple[TestClient, DatabaseStore]:
    config: AppConfig = AppConfig()
    db: DatabaseStore = DatabaseStore(":memory:")
    backend: OllamaBackend = OllamaBackend(config)
    app = create_app(config, db, backend)
    client: TestClient = TestClient(app)
    return client, db


def _seed_run(db: DatabaseStore, run_id: str = "run-abc123") -> str:
    db.record_start(
        RunStartEvent(
            type="start",
            run_id=run_id,
            model="llama3.2",
            backend="ollama",
            prompt_hash="hash1",
            prompt_text="hello",
        )
    )
    db.record_ttft(TTFTEvent(type="ttft", run_id=run_id, ttft_ms=120.5))
    db.record_token(
        TokenEvent(
            type="token",
            run_id=run_id,
            position=0,
            text="Hello",
            arrived_at_ms=120.5,
        )
    )
    db.record_token(
        TokenEvent(
            type="token",
            run_id=run_id,
            position=1,
            text=" world",
            arrived_at_ms=200.0,
        )
    )
    db.finalize_run(DoneEvent(type="done", run_id=run_id, total_ms=800.0))
    return run_id


class TestListRuns:
    def test_empty_db_returns_empty_list(self) -> None:
        client, _ = _make_app()
        resp = client.get("/api/runs")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_returns_seeded_run(self) -> None:
        client, db = _make_app()
        run_id = _seed_run(db)
        resp = client.get("/api/runs")
        assert resp.status_code == 200
        data: list[dict[str, Any]] = resp.json()
        assert len(data) == 1
        assert data[0]["run_id"] == run_id

    def test_limit_parameter_respected(self) -> None:
        client, db = _make_app()
        for i in range(5):
            _seed_run(db, f"run-{i:03d}xxxxxx")
        resp = client.get("/api/runs?limit=3")
        assert resp.status_code == 200
        assert len(resp.json()) == 3


class TestGetRun:
    def test_returns_run_when_found(self) -> None:
        client, db = _make_app()
        run_id = _seed_run(db)
        resp = client.get(f"/api/runs/{run_id}")
        assert resp.status_code == 200
        body: dict[str, Any] = resp.json()
        assert body["run_id"] == run_id
        assert body["model"] == "llama3.2"

    def test_returns_404_when_not_found(self) -> None:
        client, _ = _make_app()
        resp = client.get("/api/runs/nonexistent-id")
        assert resp.status_code == 404

    def test_run_has_tps_after_finalize(self) -> None:
        client, db = _make_app()
        run_id = _seed_run(db)
        resp = client.get(f"/api/runs/{run_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["tps"] is not None
        assert body["tps"] > 0


class TestGetTokens:
    def test_returns_tokens_for_run(self) -> None:
        client, db = _make_app()
        run_id = _seed_run(db)
        resp = client.get(f"/api/runs/{run_id}/tokens")
        assert resp.status_code == 200
        tokens: list[dict[str, Any]] = resp.json()
        assert len(tokens) == 2
        assert tokens[0]["position"] == 0
        assert tokens[1]["position"] == 1

    def test_returns_empty_for_unknown_run(self) -> None:
        client, _ = _make_app()
        resp = client.get("/api/runs/unknown/tokens")
        assert resp.status_code == 200
        assert resp.json() == []


class TestGetOutput:
    def test_returns_output_for_finalized_run(self) -> None:
        client, db = _make_app()
        run_id = _seed_run(db)
        resp = client.get(f"/api/runs/{run_id}/output")
        assert resp.status_code == 200
        body: dict[str, Any] = resp.json()
        assert body["full_text"] == "Hello world"
        assert body["token_count"] == 2

    def test_returns_404_when_output_missing(self) -> None:
        client, db = _make_app()
        db.record_start(
            RunStartEvent(
                type="start",
                run_id="run-noout123",
                model="m",
                backend="ollama",
                prompt_hash="h",
                prompt_text="",
            )
        )
        resp = client.get("/api/runs/run-noout123/output")
        assert resp.status_code == 404


class TestGetSignals:
    def test_returns_signal_response(self) -> None:
        client, db = _make_app()
        run_id = _seed_run(db)
        resp = client.get(f"/api/runs/{run_id}/signals")
        assert resp.status_code == 200
        body: dict[str, Any] = resp.json()
        assert "latency" in body
        assert "quality" in body
        assert body["latency"]["ttft_ms"] == pytest.approx(120.5)

    def test_returns_404_for_unknown_run(self) -> None:
        client, _ = _make_app()
        resp = client.get("/api/runs/no-such-run/signals")
        assert resp.status_code == 404


class TestListModels:
    def test_returns_model_names_from_backend(self) -> None:
        client, _ = _make_app()
        fake_response = {
            "models": [
                {"name": "llama3.1:8b"},
                {"name": "mistral:7b"},
            ]
        }
        with patch(
            "llmscope.proxy.server.httpx.AsyncClient"
        ) as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_resp = MagicMock()
            mock_resp.json.return_value = fake_response
            mock_resp.raise_for_status = MagicMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            resp = client.get("/api/models")
        assert resp.status_code == 200
        names: list[str] = resp.json()
        assert "llama3.1:8b" in names
        assert "mistral:7b" in names

    def test_returns_502_when_backend_unreachable(self) -> None:
        import httpx as _httpx
        client, _ = _make_app()
        with patch(
            "llmscope.proxy.server.httpx.AsyncClient"
        ) as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(
                side_effect=_httpx.ConnectError("refused")
            )
            resp = client.get("/api/models")
        assert resp.status_code == 502
