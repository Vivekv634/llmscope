from __future__ import annotations

import json
import pathlib
from unittest.mock import MagicMock, patch

import httpx
import pytest
from click.testing import CliRunner

from llmscope.cli import main
from llmscope.store.db import DatabaseStore
from llmscope.types.events import DoneEvent, RunStartEvent, TTFTEvent, TokenEvent


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def tmp_db(tmp_path: pathlib.Path) -> tuple[DatabaseStore, str]:
    db_path = str(tmp_path / "test.db")
    db = DatabaseStore(db_path)
    return db, db_path


def _seed(db: DatabaseStore, run_id: str = "run-abc12345") -> str:
    db.record_start(
        RunStartEvent(
            type="start",
            run_id=run_id,
            model="llama3.2",
            backend="ollama",
            prompt_hash="hash1",
            prompt_text="hello world",
        )
    )
    db.record_ttft(TTFTEvent(type="ttft", run_id=run_id, ttft_ms=120.5))
    db.record_token(
        TokenEvent(type="token", run_id=run_id, position=0, text="Hello", arrived_at_ms=120.5)
    )
    db.record_token(
        TokenEvent(type="token", run_id=run_id, position=1, text=" world", arrived_at_ms=200.0)
    )
    db.finalize_run(DoneEvent(type="done", run_id=run_id, total_ms=800.0))
    return run_id


class TestConfigShow:
    def test_prints_defaults(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["config", "show"])
        assert result.exit_code == 0
        assert "proxy_port" in result.output
        assert "backend_url" in result.output

    def test_reflects_port_option(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["config", "show", "--port", "9090"])
        assert result.exit_code == 0
        assert "9090" in result.output

    def test_reflects_backend_url_option(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["config", "show", "--backend-url", "http://custom:5000"])
        assert result.exit_code == 0
        assert "http://custom:5000" in result.output

    def test_reflects_backend_choice(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["config", "show", "--backend", "llamacpp"])
        assert result.exit_code == 0
        assert "llamacpp" in result.output


class TestInspectList:
    def test_empty_db_prints_no_runs(
        self, runner: CliRunner, tmp_db: tuple[DatabaseStore, str]
    ) -> None:
        db, db_path = tmp_db
        db.close()
        result = runner.invoke(main, ["inspect", "list", "--db", db_path])
        assert result.exit_code == 0
        assert "no runs" in result.output

    def test_seeded_run_appears_in_list(
        self, runner: CliRunner, tmp_db: tuple[DatabaseStore, str]
    ) -> None:
        db, db_path = tmp_db
        run_id = _seed(db)
        db.close()
        result = runner.invoke(main, ["inspect", "list", "--db", db_path])
        assert result.exit_code == 0
        assert run_id[:8] in result.output
        assert "llama3.2" in result.output

    def test_limit_option_respected(
        self, runner: CliRunner, tmp_db: tuple[DatabaseStore, str]
    ) -> None:
        db, db_path = tmp_db
        for i in range(5):
            _seed(db, f"run-{i:03d}xxxxx")
        db.close()
        result = runner.invoke(main, ["inspect", "list", "--db", db_path, "--limit", "2"])
        assert result.exit_code == 0
        lines = [l for l in result.output.splitlines() if "run-" in l]
        assert len(lines) == 2


class TestInspectShow:
    def test_shows_run_details(
        self, runner: CliRunner, tmp_db: tuple[DatabaseStore, str]
    ) -> None:
        db, db_path = tmp_db
        run_id = _seed(db)
        db.close()
        result = runner.invoke(main, ["inspect", "show", run_id, "--db", db_path])
        assert result.exit_code == 0
        assert run_id in result.output
        assert "llama3.2" in result.output
        assert "ollama" in result.output

    def test_shows_output_text(
        self, runner: CliRunner, tmp_db: tuple[DatabaseStore, str]
    ) -> None:
        db, db_path = tmp_db
        run_id = _seed(db)
        db.close()
        result = runner.invoke(main, ["inspect", "show", run_id, "--db", db_path])
        assert result.exit_code == 0
        assert "Hello world" in result.output

    def test_missing_run_prints_error(
        self, runner: CliRunner, tmp_db: tuple[DatabaseStore, str]
    ) -> None:
        db, db_path = tmp_db
        db.close()
        result = runner.invoke(main, ["inspect", "show", "no-such-run", "--db", db_path])
        assert result.exit_code == 0
        assert "not found" in result.output


class TestInspectReplay:
    def test_fast_replay_prints_tokens(
        self, runner: CliRunner, tmp_db: tuple[DatabaseStore, str]
    ) -> None:
        db, db_path = tmp_db
        run_id = _seed(db)
        db.close()
        result = runner.invoke(
            main, ["inspect", "replay", run_id, "--db", db_path, "--fast"]
        )
        assert result.exit_code == 0
        assert "Hello" in result.output
        assert "world" in result.output

    def test_missing_run_prints_error(
        self, runner: CliRunner, tmp_db: tuple[DatabaseStore, str]
    ) -> None:
        db, db_path = tmp_db
        db.close()
        result = runner.invoke(
            main, ["inspect", "replay", "no-such", "--db", db_path, "--fast"]
        )
        assert result.exit_code == 0
        assert "not found" in result.output


class TestDbStats:
    def test_empty_db_shows_zeros(
        self, runner: CliRunner, tmp_db: tuple[DatabaseStore, str]
    ) -> None:
        db, db_path = tmp_db
        db.close()
        result = runner.invoke(main, ["db", "stats", "--db", db_path])
        assert result.exit_code == 0
        assert "total_runs" in result.output
        assert "0" in result.output

    def test_seeded_db_shows_counts(
        self, runner: CliRunner, tmp_db: tuple[DatabaseStore, str]
    ) -> None:
        db, db_path = tmp_db
        _seed(db)
        db.close()
        result = runner.invoke(main, ["db", "stats", "--db", db_path])
        assert result.exit_code == 0
        assert "llama3.2" in result.output


class TestStatus:
    def test_proxy_up_prints_stats(self, runner: CliRunner) -> None:
        fake_stats = {
            "total_runs": 3,
            "total_tokens": 120,
            "avg_tps": 14.5,
            "avg_ttft_ms": 210.0,
            "model_breakdown": {"llama3.2": 3},
        }
        mock_resp = MagicMock()
        mock_resp.json.return_value = fake_stats
        mock_resp.raise_for_status = MagicMock()
        with patch("llmscope.cli.httpx.get", return_value=mock_resp):
            result = runner.invoke(main, ["status"])
        assert result.exit_code == 0
        assert "UP" in result.output
        assert "llama3.2" in result.output
        assert "3" in result.output

    def test_proxy_down_exits_nonzero(self, runner: CliRunner) -> None:
        with patch(
            "llmscope.cli.httpx.get",
            side_effect=httpx.ConnectError("refused"),
        ):
            result = runner.invoke(main, ["status"])
        assert result.exit_code != 0
        assert "DOWN" in result.output


class TestInit:
    def test_creates_db_directory(
        self, runner: CliRunner, tmp_path: pathlib.Path
    ) -> None:
        db_path = str(tmp_path / "newdir" / "traces.db")
        with patch.dict("os.environ", {"LLMSCOPE_DB_PATH": db_path}):
            with patch("llmscope.cli.httpx.get", side_effect=httpx.ConnectError("x")):
                result = runner.invoke(main, ["init"])
        assert result.exit_code == 0
        assert (tmp_path / "newdir").exists()

    def test_prints_schema_version(
        self, runner: CliRunner, tmp_path: pathlib.Path
    ) -> None:
        db_path = str(tmp_path / "traces.db")
        with patch.dict("os.environ", {"LLMSCOPE_DB_PATH": db_path}):
            with patch("llmscope.cli.httpx.get", side_effect=httpx.ConnectError("x")):
                result = runner.invoke(main, ["init"])
        assert result.exit_code == 0
        assert "schema v1" in result.output

    def test_backend_reachable_prints_ok(
        self, runner: CliRunner, tmp_path: pathlib.Path
    ) -> None:
        db_path = str(tmp_path / "traces.db")
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        with patch.dict("os.environ", {"LLMSCOPE_DB_PATH": db_path}):
            with patch("llmscope.cli.httpx.get", return_value=mock_resp):
                result = runner.invoke(main, ["init"])
        assert result.exit_code == 0
        assert "[ok] backend" in result.output

    def test_backend_unreachable_prints_warning(
        self, runner: CliRunner, tmp_path: pathlib.Path
    ) -> None:
        db_path = str(tmp_path / "traces.db")
        with patch.dict("os.environ", {"LLMSCOPE_DB_PATH": db_path}):
            with patch("llmscope.cli.httpx.get", side_effect=httpx.ConnectError("x")):
                result = runner.invoke(main, ["init"])
        assert result.exit_code == 0
        assert "[!]" in result.output


class TestExport:
    def test_json_export(
        self, runner: CliRunner, tmp_db: tuple[DatabaseStore, str], tmp_path: pathlib.Path
    ) -> None:
        db, db_path = tmp_db
        _seed(db)
        db.close()
        out = str(tmp_path / "out.json")
        result = runner.invoke(
            main, ["export", "--format", "json", "--output", out, "--db", db_path]
        )
        assert result.exit_code == 0
        data = json.loads(pathlib.Path(out).read_text())
        assert len(data) == 1
        assert data[0]["model"] == "llama3.2"

    def test_csv_export(
        self, runner: CliRunner, tmp_db: tuple[DatabaseStore, str], tmp_path: pathlib.Path
    ) -> None:
        db, db_path = tmp_db
        _seed(db)
        db.close()
        out = str(tmp_path / "out.csv")
        result = runner.invoke(
            main, ["export", "--format", "csv", "--output", out, "--db", db_path]
        )
        assert result.exit_code == 0
        content = pathlib.Path(out).read_text()
        assert "llama3.2" in content

    def test_html_export(
        self, runner: CliRunner, tmp_db: tuple[DatabaseStore, str], tmp_path: pathlib.Path
    ) -> None:
        db, db_path = tmp_db
        _seed(db)
        db.close()
        out = str(tmp_path / "out.html")
        result = runner.invoke(
            main, ["export", "--format", "html", "--output", out, "--db", db_path]
        )
        assert result.exit_code == 0
        content = pathlib.Path(out).read_text()
        assert "<html" in content
        assert "llama3.2" in content

    def test_export_prints_count(
        self, runner: CliRunner, tmp_db: tuple[DatabaseStore, str], tmp_path: pathlib.Path
    ) -> None:
        db, db_path = tmp_db
        _seed(db)
        db.close()
        out = str(tmp_path / "out.json")
        result = runner.invoke(
            main, ["export", "--format", "json", "--output", out, "--db", db_path]
        )
        assert "1 run" in result.output


class TestStart:
    def test_invokes_uvicorn(self, runner: CliRunner) -> None:
        with patch("llmscope.cli.uvicorn.run") as mock_run, \
             patch("llmscope.cli.DatabaseStore"):
            result = runner.invoke(main, ["start", "--port", "8888"])
        assert result.exit_code == 0
        mock_run.assert_called_once()
        _, kwargs = mock_run.call_args
        assert kwargs["port"] == 8888

    def test_custom_backend_url(self, runner: CliRunner) -> None:
        with patch("llmscope.cli.uvicorn.run"), \
             patch("llmscope.cli.DatabaseStore"):
            result = runner.invoke(
                main, ["start", "--backend-url", "http://myhost:11434"]
            )
        assert result.exit_code == 0
        assert "http://myhost:11434" in result.output


class TestCompareDrift:
    def test_prints_drift_result(
        self, runner: CliRunner, tmp_db: tuple[DatabaseStore, str]
    ) -> None:
        db, db_path = tmp_db
        run_a = _seed(db, "run-aaa11111")
        run_b = _seed(db, "run-bbb22222")
        db.close()
        result = runner.invoke(
            main,
            ["compare", "drift", "--run-a", run_a, "--run-b", run_b, "--db", db_path],
        )
        assert result.exit_code == 0
        assert "drift" in result.output

    def test_missing_run_a_prints_error(
        self, runner: CliRunner, tmp_db: tuple[DatabaseStore, str]
    ) -> None:
        db, db_path = tmp_db
        run_b = _seed(db, "run-bbb22222")
        db.close()
        result = runner.invoke(
            main,
            ["compare", "drift", "--run-a", "no-such", "--run-b", run_b, "--db", db_path],
        )
        assert result.exit_code == 0
        assert "not found" in result.output
