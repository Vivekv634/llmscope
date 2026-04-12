"""Tests for llmscope/types/runs.py.

Covers: RunRecord, TokenRecord, OutputRecord — field validation,
optional fields, boundary values, and serialisation round-trips.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from llmscope.types.runs import OutputRecord, RunRecord, TokenRecord


class TestRunRecord:
    _now: datetime = datetime(2026, 4, 12, 12, 0, 0, tzinfo=timezone.utc)

    def _valid(self, **overrides: object) -> RunRecord:
        defaults: dict[str, object] = {
            "run_id": "run_abc",
            "model": "llama3",
            "backend": "ollama",
            "prompt_hash": "deadbeef" * 8,
            "created_at": self._now,
        }
        defaults.update(overrides)
        return RunRecord.model_validate(defaults)

    def test_valid_minimal_construction(self) -> None:
        record = self._valid()
        assert record.run_id == "run_abc"
        assert record.tags == []
        assert record.ttft_ms is None

    def test_optional_fields_accepted(self) -> None:
        record = self._valid(
            ttft_ms=12.3,
            total_ms=500.0,
            token_count=80,
            tps=160.0,
            quality_score=0.75,
            tags=["experiment"],
        )
        assert record.quality_score == 0.75
        assert record.tags == ["experiment"]

    def test_quality_score_upper_bound(self) -> None:
        with pytest.raises(ValidationError):
            self._valid(quality_score=1.1)

    def test_quality_score_lower_bound(self) -> None:
        with pytest.raises(ValidationError):
            self._valid(quality_score=-0.1)

    def test_quality_score_boundary_zero(self) -> None:
        record = self._valid(quality_score=0.0)
        assert record.quality_score == 0.0

    def test_quality_score_boundary_one(self) -> None:
        record = self._valid(quality_score=1.0)
        assert record.quality_score == 1.0

    def test_ttft_ms_must_be_positive(self) -> None:
        with pytest.raises(ValidationError):
            self._valid(ttft_ms=0.0)

    def test_token_count_zero_allowed(self) -> None:
        record = self._valid(token_count=0)
        assert record.token_count == 0

    def test_token_count_negative_rejected(self) -> None:
        with pytest.raises(ValidationError):
            self._valid(token_count=-1)

    def test_run_id_empty_string_rejected(self) -> None:
        with pytest.raises(ValidationError):
            self._valid(run_id="")

    def test_model_empty_string_rejected(self) -> None:
        with pytest.raises(ValidationError):
            self._valid(model="")

    def test_serialisation_round_trip(self) -> None:
        record = self._valid(ttft_ms=50.0, tps=100.0, tags=["a", "b"])
        restored = RunRecord.model_validate_json(record.model_dump_json())
        assert restored == record


class TestTokenRecord:
    def test_valid_construction(self) -> None:
        record = TokenRecord(run_id="r1", position=0, text="Hi", arrived_at_ms=0.0)
        assert record.id is None
        assert record.position == 0

    def test_position_negative_rejected(self) -> None:
        with pytest.raises(ValidationError):
            TokenRecord(run_id="r1", position=-1, text="x", arrived_at_ms=0.0)

    def test_arrived_at_ms_negative_rejected(self) -> None:
        with pytest.raises(ValidationError):
            TokenRecord(run_id="r1", position=0, text="x", arrived_at_ms=-0.1)

    def test_id_provided(self) -> None:
        record = TokenRecord(id=42, run_id="r1", position=0, text="x", arrived_at_ms=1.0)
        assert record.id == 42

    def test_id_must_be_ge_one(self) -> None:
        with pytest.raises(ValidationError):
            TokenRecord(id=0, run_id="r1", position=0, text="x", arrived_at_ms=1.0)

    def test_serialisation_round_trip(self) -> None:
        record = TokenRecord(id=1, run_id="r1", position=5, text="world", arrived_at_ms=22.2)
        restored = TokenRecord.model_validate_json(record.model_dump_json())
        assert restored == record


class TestOutputRecord:
    def test_valid_construction(self) -> None:
        record = OutputRecord(run_id="r1", full_text="Hello world", token_count=2)
        assert record.token_count == 2

    def test_token_count_zero_allowed(self) -> None:
        record = OutputRecord(run_id="r1", full_text="", token_count=0)
        assert record.token_count == 0

    def test_token_count_negative_rejected(self) -> None:
        with pytest.raises(ValidationError):
            OutputRecord(run_id="r1", full_text="x", token_count=-1)

    def test_run_id_empty_string_rejected(self) -> None:
        with pytest.raises(ValidationError):
            OutputRecord(run_id="", full_text="x", token_count=1)

    def test_serialisation_round_trip(self) -> None:
        record = OutputRecord(run_id="r1", full_text="Hello", token_count=1)
        restored = OutputRecord.model_validate_json(record.model_dump_json())
        assert restored == record
