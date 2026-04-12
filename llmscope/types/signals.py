"""Return types for all signal computation functions.

Signal modules (latency.py, quality.py, drift.py) always return one of
these models. Callers pattern-match on the model fields — never on raw
floats or dicts — so the signal API is stable and type-checked.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class LatencyResult(BaseModel):
    """Output of compute_latency() in signals/latency.py."""

    ttft_ms: float = Field(ge=0, description="Time-to-first-token in ms")
    total_ms: float = Field(ge=0, description="Total generation time in ms")
    tps: float = Field(ge=0, description="Tokens per second")
    stall_positions: list[int] = Field(
        default_factory=list,
        description="Token positions where inter-token gap exceeded the stall threshold",
    )


class QualityResult(BaseModel):
    """Output of output_entropy() in signals/quality.py."""

    entropy_score: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "Normalised Shannon entropy of the token distribution. "
            "0 = fully repetitive, 1 = maximally diverse. "
            "This is a proxy for output confidence, not ground truth."
        ),
    )
    token_count: int = Field(ge=0, description="Number of tokens scored")


class DriftResult(BaseModel):
    """Output of cosine_drift() in signals/drift.py."""

    run_a_id: str = Field(min_length=1)
    run_b_id: str = Field(min_length=1)
    cosine_drift: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "1 - cosine_similarity of token frequency vectors. "
            "0 = identical distribution, 1 = completely different."
        ),
    )
    is_significant: bool = Field(
        description="True when cosine_drift > 0.3 — meaningful behavioural shift"
    )
