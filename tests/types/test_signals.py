from __future__ import annotations

import pytest
from pydantic import ValidationError

from llmscope.types.signals import DriftResult, LatencyResult, QualityResult


class TestLatencyResult:
    def test_valid_construction(self) -> None:
        result = LatencyResult(ttft_ms=50.0, total_ms=1000.0, tps=120.0, stall_positions=[])
        assert result.tps == 120.0
        assert result.stall_positions == []

    def test_stall_positions_populated(self) -> None:
        result = LatencyResult(
            ttft_ms=50.0, total_ms=1000.0, tps=10.0, stall_positions=[3, 7, 12]
        )
        assert result.stall_positions == [3, 7, 12]

    def test_ttft_ms_zero_allowed(self) -> None:
        result = LatencyResult(ttft_ms=0.0, total_ms=100.0, tps=10.0)
        assert result.ttft_ms == 0.0

    def test_ttft_ms_negative_rejected(self) -> None:
        with pytest.raises(ValidationError):
            LatencyResult(ttft_ms=-1.0, total_ms=100.0, tps=10.0)

    def test_tps_zero_allowed(self) -> None:
        result = LatencyResult(ttft_ms=0.0, total_ms=0.0, tps=0.0)
        assert result.tps == 0.0

    def test_tps_negative_rejected(self) -> None:
        with pytest.raises(ValidationError):
            LatencyResult(ttft_ms=10.0, total_ms=100.0, tps=-1.0)

    def test_default_stall_positions_is_empty_list(self) -> None:
        result = LatencyResult(ttft_ms=10.0, total_ms=100.0, tps=5.0)
        assert result.stall_positions == []

    def test_serialisation_round_trip(self) -> None:
        result = LatencyResult(
            ttft_ms=12.3, total_ms=456.7, tps=88.9, stall_positions=[5, 10]
        )
        restored = LatencyResult.model_validate_json(result.model_dump_json())
        assert restored == result


class TestQualityResult:
    def test_valid_construction(self) -> None:
        result = QualityResult(entropy_score=0.75, token_count=100)
        assert result.entropy_score == 0.75

    def test_entropy_score_boundary_zero(self) -> None:
        result = QualityResult(entropy_score=0.0, token_count=1)
        assert result.entropy_score == 0.0

    def test_entropy_score_boundary_one(self) -> None:
        result = QualityResult(entropy_score=1.0, token_count=1)
        assert result.entropy_score == 1.0

    def test_entropy_score_above_one_rejected(self) -> None:
        with pytest.raises(ValidationError):
            QualityResult(entropy_score=1.0001, token_count=1)

    def test_entropy_score_below_zero_rejected(self) -> None:
        with pytest.raises(ValidationError):
            QualityResult(entropy_score=-0.001, token_count=1)

    def test_token_count_zero_allowed(self) -> None:
        result = QualityResult(entropy_score=0.0, token_count=0)
        assert result.token_count == 0

    def test_token_count_negative_rejected(self) -> None:
        with pytest.raises(ValidationError):
            QualityResult(entropy_score=0.5, token_count=-1)

    def test_serialisation_round_trip(self) -> None:
        result = QualityResult(entropy_score=0.42, token_count=50)
        restored = QualityResult.model_validate_json(result.model_dump_json())
        assert restored == result


class TestDriftResult:
    def test_valid_non_significant(self) -> None:
        result = DriftResult(
            run_a_id="a", run_b_id="b", cosine_drift=0.1, is_significant=False
        )
        assert result.is_significant is False

    def test_valid_significant(self) -> None:
        result = DriftResult(
            run_a_id="a", run_b_id="b", cosine_drift=0.5, is_significant=True
        )
        assert result.is_significant is True

    def test_cosine_drift_boundary_zero(self) -> None:
        result = DriftResult(
            run_a_id="a", run_b_id="b", cosine_drift=0.0, is_significant=False
        )
        assert result.cosine_drift == 0.0

    def test_cosine_drift_boundary_one(self) -> None:
        result = DriftResult(
            run_a_id="a", run_b_id="b", cosine_drift=1.0, is_significant=True
        )
        assert result.cosine_drift == 1.0

    def test_cosine_drift_above_one_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DriftResult(
                run_a_id="a", run_b_id="b", cosine_drift=1.0001, is_significant=True
            )

    def test_cosine_drift_below_zero_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DriftResult(
                run_a_id="a", run_b_id="b", cosine_drift=-0.001, is_significant=False
            )

    def test_run_id_empty_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DriftResult(
                run_a_id="", run_b_id="b", cosine_drift=0.1, is_significant=False
            )

    def test_serialisation_round_trip(self) -> None:
        result = DriftResult(
            run_a_id="run1", run_b_id="run2", cosine_drift=0.35, is_significant=True
        )
        restored = DriftResult.model_validate_json(result.model_dump_json())
        assert restored == result
