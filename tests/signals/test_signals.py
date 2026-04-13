from __future__ import annotations

import pytest

from llmscope.signals.drift import cosine_drift
from llmscope.signals.latency import compute_latency
from llmscope.signals.quality import output_entropy
from llmscope.types.signals import DriftResult, LatencyResult, QualityResult


class TestComputeLatency:
    def test_basic_returns_latency_result(self) -> None:
        result = compute_latency(
            arrived_ms=[100.0, 200.0, 300.0],
            ttft_ms=100.0,
            total_ms=1000.0,
            stall_threshold_ms=500.0,
        )
        assert isinstance(result, LatencyResult)

    def test_tps_calculated_correctly(self) -> None:
        result = compute_latency(
            arrived_ms=[100.0, 200.0, 300.0, 400.0],
            ttft_ms=100.0,
            total_ms=2000.0,
            stall_threshold_ms=500.0,
        )
        assert result.tps == pytest.approx(2.0, rel=1e-3)

    def test_ttft_and_total_ms_passed_through(self) -> None:
        result = compute_latency(
            arrived_ms=[50.0],
            ttft_ms=42.5,
            total_ms=999.0,
            stall_threshold_ms=500.0,
        )
        assert result.ttft_ms == pytest.approx(42.5)
        assert result.total_ms == pytest.approx(999.0)

    def test_no_stalls_when_gaps_below_threshold(self) -> None:
        result = compute_latency(
            arrived_ms=[100.0, 200.0, 300.0, 400.0],
            ttft_ms=100.0,
            total_ms=1000.0,
            stall_threshold_ms=500.0,
        )
        assert result.stall_positions == []

    def test_stalls_detected_at_correct_positions(self) -> None:
        result = compute_latency(
            arrived_ms=[100.0, 200.0, 800.0, 900.0],
            ttft_ms=100.0,
            total_ms=1000.0,
            stall_threshold_ms=500.0,
        )
        assert result.stall_positions == [2]

    def test_multiple_stalls_detected(self) -> None:
        result = compute_latency(
            arrived_ms=[100.0, 700.0, 800.0, 1500.0],
            ttft_ms=100.0,
            total_ms=2000.0,
            stall_threshold_ms=500.0,
        )
        assert result.stall_positions == [1, 3]

    def test_empty_arrived_ms_returns_zero_tps(self) -> None:
        result = compute_latency(
            arrived_ms=[],
            ttft_ms=0.0,
            total_ms=1000.0,
            stall_threshold_ms=500.0,
        )
        assert result.tps == pytest.approx(0.0)
        assert result.stall_positions == []

    def test_zero_total_ms_returns_zero_tps(self) -> None:
        result = compute_latency(
            arrived_ms=[100.0, 200.0],
            ttft_ms=100.0,
            total_ms=0.0,
            stall_threshold_ms=500.0,
        )
        assert result.tps == pytest.approx(0.0)

    def test_single_token_no_stalls(self) -> None:
        result = compute_latency(
            arrived_ms=[500.0],
            ttft_ms=500.0,
            total_ms=1000.0,
            stall_threshold_ms=200.0,
        )
        assert result.stall_positions == []

    def test_stall_exactly_at_threshold_not_flagged(self) -> None:
        result = compute_latency(
            arrived_ms=[100.0, 600.0],
            ttft_ms=100.0,
            total_ms=1000.0,
            stall_threshold_ms=500.0,
        )
        assert result.stall_positions == []

    def test_stall_just_above_threshold_flagged(self) -> None:
        result = compute_latency(
            arrived_ms=[100.0, 600.1],
            ttft_ms=100.0,
            total_ms=1000.0,
            stall_threshold_ms=500.0,
        )
        assert result.stall_positions == [1]


class TestOutputEntropy:
    def test_empty_returns_zero_score(self) -> None:
        result = output_entropy([])
        assert isinstance(result, QualityResult)
        assert result.entropy_score == pytest.approx(0.0)
        assert result.token_count == 0

    def test_single_token_returns_zero_score(self) -> None:
        result = output_entropy(["hello"])
        assert result.entropy_score == pytest.approx(0.0)
        assert result.token_count == 1

    def test_all_identical_tokens_returns_zero_score(self) -> None:
        result = output_entropy(["the", "the", "the", "the"])
        assert result.entropy_score == pytest.approx(0.0)
        assert result.token_count == 4

    def test_all_unique_tokens_returns_max_score(self) -> None:
        result = output_entropy(["a", "b", "c", "d"])
        assert result.entropy_score == pytest.approx(1.0, rel=1e-5)
        assert result.token_count == 4

    def test_score_in_valid_range(self) -> None:
        result = output_entropy(["the", "cat", "sat", "the", "mat", "the"])
        assert 0.0 <= result.entropy_score <= 1.0

    def test_token_count_matches_input(self) -> None:
        tokens = ["a", "b", "c", "a", "b", "a"]
        result = output_entropy(tokens)
        assert result.token_count == len(tokens)

    def test_higher_diversity_yields_higher_score(self) -> None:
        low_diversity = output_entropy(["the", "the", "the", "cat"])
        high_diversity = output_entropy(["apple", "banana", "cherry", "date"])
        assert high_diversity.entropy_score > low_diversity.entropy_score

    def test_two_equal_frequency_tokens_half_entropy(self) -> None:
        result = output_entropy(["a", "b", "a", "b"])
        assert result.entropy_score == pytest.approx(1.0, rel=1e-5)

    def test_entropy_score_type_is_float(self) -> None:
        result = output_entropy(["x", "y"])
        assert isinstance(result.entropy_score, float)


class TestCosineDrift:
    def test_identical_runs_zero_drift(self) -> None:
        tokens = ["the", "cat", "sat", "on", "the", "mat"]
        result = cosine_drift("run-a", tokens, "run-b", tokens)
        assert isinstance(result, DriftResult)
        assert result.cosine_drift == pytest.approx(0.0, abs=1e-6)
        assert result.is_significant is False

    def test_completely_different_runs_max_drift(self) -> None:
        result = cosine_drift(
            "run-a",
            ["alpha", "beta", "gamma"],
            "run-b",
            ["delta", "epsilon", "zeta"],
        )
        assert result.cosine_drift == pytest.approx(1.0, rel=1e-5)
        assert result.is_significant is True

    def test_both_empty_returns_zero_drift(self) -> None:
        result = cosine_drift("run-a", [], "run-b", [])
        assert result.cosine_drift == pytest.approx(0.0)
        assert result.is_significant is False

    def test_one_empty_run_max_drift(self) -> None:
        result = cosine_drift("run-a", ["hello", "world"], "run-b", [])
        assert result.cosine_drift == pytest.approx(1.0, rel=1e-5)
        assert result.is_significant is True

    def test_partial_overlap_drift_between_zero_and_one(self) -> None:
        result = cosine_drift(
            "run-a",
            ["the", "cat", "sat"],
            "run-b",
            ["the", "dog", "ran"],
        )
        assert 0.0 < result.cosine_drift < 1.0

    def test_run_ids_preserved_in_result(self) -> None:
        result = cosine_drift("run-aaa", ["x"], "run-bbb", ["y"])
        assert result.run_a_id == "run-aaa"
        assert result.run_b_id == "run-bbb"

    def test_drift_is_symmetric(self) -> None:
        tokens_a = ["the", "quick", "brown", "fox"]
        tokens_b = ["the", "lazy", "brown", "dog"]
        result_ab = cosine_drift("a", tokens_a, "b", tokens_b)
        result_ba = cosine_drift("b", tokens_b, "a", tokens_a)
        assert result_ab.cosine_drift == pytest.approx(result_ba.cosine_drift, rel=1e-6)

    def test_drift_within_valid_range(self) -> None:
        result = cosine_drift(
            "a",
            ["foo", "bar", "baz", "foo"],
            "b",
            ["bar", "baz", "qux", "baz"],
        )
        assert 0.0 <= result.cosine_drift <= 1.0

    def test_significance_threshold_above_015(self) -> None:
        result = cosine_drift(
            "a",
            ["alpha", "beta"],
            "b",
            ["gamma", "delta"],
        )
        assert result.is_significant is True
        assert result.cosine_drift > 0.15

    def test_frequency_weighting_affects_drift(self) -> None:
        result_repeat = cosine_drift(
            "a",
            ["the"] * 10 + ["cat"],
            "b",
            ["the"] * 10 + ["dog"],
        )
        result_equal = cosine_drift(
            "a",
            ["the", "cat"],
            "b",
            ["the", "dog"],
        )
        assert result_repeat.cosine_drift < result_equal.cosine_drift
