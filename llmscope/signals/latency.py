from __future__ import annotations

from llmscope.types.signals import LatencyResult


def compute_latency(
    arrived_ms: list[float],
    ttft_ms: float,
    total_ms: float,
    stall_threshold_ms: float,
) -> LatencyResult:
    token_count: int = len(arrived_ms)
    tps: float = (
        round(token_count / (total_ms / 1000.0), 4) if total_ms > 0 else 0.0
    )
    stall_positions: list[int] = []
    for i in range(1, token_count):
        gap: float = arrived_ms[i] - arrived_ms[i - 1]
        if gap > stall_threshold_ms:
            stall_positions.append(i)
    return LatencyResult(
        ttft_ms=ttft_ms,
        total_ms=total_ms,
        tps=tps,
        stall_positions=stall_positions,
    )
