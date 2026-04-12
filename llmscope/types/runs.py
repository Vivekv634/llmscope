"""Database row types for runs, tokens, and outputs.

These models are the single source of truth for what gets stored in
DuckDB and what gets returned from query helpers. All DB query methods
return instances of these models — never raw tuples or dicts.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class RunRecord(BaseModel):
    """Mirrors the `runs` table row exactly."""

    run_id: str = Field(min_length=1)
    model: str = Field(min_length=1)
    backend: str = Field(min_length=1, description="'ollama' or 'llamacpp'")
    prompt_hash: str = Field(min_length=1, description="SHA-256 hex of prompt text")
    prompt_text: Optional[str] = None
    created_at: datetime
    ttft_ms: Optional[float] = Field(default=None, gt=0)
    total_ms: Optional[float] = Field(default=None, gt=0)
    token_count: Optional[int] = Field(default=None, ge=0)
    tps: Optional[float] = Field(default=None, ge=0)
    quality_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    tags: list[str] = Field(default_factory=list)


class TokenRecord(BaseModel):
    """Mirrors the `tokens` table row exactly."""

    id: Optional[int] = Field(default=None, ge=1)
    run_id: str = Field(min_length=1)
    position: int = Field(ge=0)
    text: str
    arrived_at_ms: float = Field(ge=0)


class OutputRecord(BaseModel):
    """Mirrors the `outputs` table row exactly."""

    run_id: str = Field(min_length=1)
    full_text: str
    token_count: int = Field(ge=0)
