from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path

import pytest

from llmscope.export.csv_export import CsvExporter
from llmscope.export.json_export import JsonExporter
from llmscope.export.report import HtmlReportExporter
from llmscope.types.runs import RunRecord


def _make_run(run_id: str = "run-abc") -> RunRecord:
    return RunRecord(
        run_id=run_id,
        model="llama3.2",
        backend="ollama",
        prompt_hash="abc123",
        prompt_text="hello",
        created_at=datetime(2025, 1, 15, 10, 0, 0),
        ttft_ms=100.0,
        total_ms=2000.0,
        token_count=50,
        tps=25.0,
        quality_score=0.75,
        tags=["test"],
    )


class TestJsonExporter:
    @pytest.mark.asyncio
    async def test_creates_file(self, tmp_path: Path) -> None:
        output = str(tmp_path / "out.json")
        await JsonExporter().export([_make_run()], output)
        assert Path(output).exists()

    @pytest.mark.asyncio
    async def test_output_is_valid_json(self, tmp_path: Path) -> None:
        output = str(tmp_path / "out.json")
        await JsonExporter().export([_make_run()], output)
        data = json.loads(Path(output).read_text())
        assert isinstance(data, list)
        assert len(data) == 1

    @pytest.mark.asyncio
    async def test_run_id_present_in_output(self, tmp_path: Path) -> None:
        run = _make_run("run-xyz")
        output = str(tmp_path / "out.json")
        await JsonExporter().export([run], output)
        data = json.loads(Path(output).read_text())
        assert data[0]["run_id"] == "run-xyz"

    @pytest.mark.asyncio
    async def test_multiple_runs_exported(self, tmp_path: Path) -> None:
        runs = [_make_run(f"run-{i}xx") for i in range(3)]
        output = str(tmp_path / "out.json")
        await JsonExporter().export(runs, output)
        data = json.loads(Path(output).read_text())
        assert len(data) == 3

    @pytest.mark.asyncio
    async def test_empty_runs_exports_empty_list(self, tmp_path: Path) -> None:
        output = str(tmp_path / "out.json")
        await JsonExporter().export([], output)
        data = json.loads(Path(output).read_text())
        assert data == []


class TestCsvExporter:
    @pytest.mark.asyncio
    async def test_creates_file(self, tmp_path: Path) -> None:
        output = str(tmp_path / "out.csv")
        await CsvExporter().export([_make_run()], output)
        assert Path(output).exists()

    @pytest.mark.asyncio
    async def test_has_header_row(self, tmp_path: Path) -> None:
        output = str(tmp_path / "out.csv")
        await CsvExporter().export([_make_run()], output)
        reader = csv.DictReader(Path(output).open())
        assert "run_id" in (reader.fieldnames or [])
        assert "model" in (reader.fieldnames or [])

    @pytest.mark.asyncio
    async def test_data_row_matches_run(self, tmp_path: Path) -> None:
        run = _make_run("run-abc")
        output = str(tmp_path / "out.csv")
        await CsvExporter().export([run], output)
        rows = list(csv.DictReader(Path(output).open()))
        assert len(rows) == 1
        assert rows[0]["run_id"] == "run-abc"
        assert rows[0]["model"] == "llama3.2"

    @pytest.mark.asyncio
    async def test_tags_joined_by_comma(self, tmp_path: Path) -> None:
        _make_run()
        run2 = RunRecord(
            run_id="run-tag",
            model="m",
            backend="ollama",
            prompt_hash="h",
            created_at=datetime(2025, 1, 1),
            tags=["a", "b", "c"],
        )
        output = str(tmp_path / "out.csv")
        await CsvExporter().export([run2], output)
        rows = list(csv.DictReader(Path(output).open()))
        assert rows[0]["tags"] == "a,b,c"


class TestHtmlReportExporter:
    @pytest.mark.asyncio
    async def test_creates_file(self, tmp_path: Path) -> None:
        output = str(tmp_path / "report.html")
        await HtmlReportExporter().export([_make_run()], output)
        assert Path(output).exists()

    @pytest.mark.asyncio
    async def test_output_contains_html_structure(self, tmp_path: Path) -> None:
        output = str(tmp_path / "report.html")
        await HtmlReportExporter().export([_make_run()], output)
        content = Path(output).read_text()
        assert "<!DOCTYPE html>" in content
        assert "<table>" in content

    @pytest.mark.asyncio
    async def test_run_model_appears_in_output(self, tmp_path: Path) -> None:
        output = str(tmp_path / "report.html")
        await HtmlReportExporter().export([_make_run()], output)
        content = Path(output).read_text()
        assert "llama3.2" in content

    @pytest.mark.asyncio
    async def test_title_appears_in_output(self, tmp_path: Path) -> None:
        output = str(tmp_path / "report.html")
        await HtmlReportExporter().export(
            [_make_run()], output, title="My Report"
        )
        content = Path(output).read_text()
        assert "My Report" in content

    @pytest.mark.asyncio
    async def test_empty_runs_still_produces_valid_html(
        self, tmp_path: Path
    ) -> None:
        output = str(tmp_path / "report.html")
        await HtmlReportExporter().export([], output)
        content = Path(output).read_text()
        assert "<!DOCTYPE html>" in content
