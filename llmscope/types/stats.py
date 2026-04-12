from __future__ import annotations

from pydantic import BaseModel, Field


class StatsRecord(BaseModel):
    total_runs: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    avg_tps: float = Field(ge=0)
    avg_ttft_ms: float = Field(ge=0)
    model_breakdown: dict[str, int]
