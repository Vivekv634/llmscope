from __future__ import annotations

from pydantic import BaseModel, Field


class LatencyResult(BaseModel):
    ttft_ms: float = Field(ge=0)
    total_ms: float = Field(ge=0)
    tps: float = Field(ge=0)
    stall_positions: list[int] = Field(default_factory=list)


class QualityResult(BaseModel):
    entropy_score: float = Field(ge=0.0, le=1.0)
    token_count: int = Field(ge=0)


class DriftResult(BaseModel):
    run_a_id: str = Field(min_length=1)
    run_b_id: str = Field(min_length=1)
    cosine_drift: float = Field(ge=0.0, le=1.0)
    is_significant: bool


class SignalResponse(BaseModel):
    latency: LatencyResult
    quality: QualityResult
