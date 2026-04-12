"""Queue event types for the proxy hot path.

Every event flowing through the asyncio.Queue is one of these three
shapes. The discriminated union QueueEvent is the only type the queue
worker and interceptor exchange — no raw dicts anywhere.
"""

from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field


class TTFTEvent(BaseModel):
    """Emitted exactly once per run — when the first token arrives."""

    type: Literal["ttft"]
    run_id: str = Field(min_length=1)
    ttft_ms: float = Field(gt=0, description="Time-to-first-token in milliseconds")


class TokenEvent(BaseModel):
    """Emitted once per chunk received from the backend."""

    type: Literal["token"]
    run_id: str = Field(min_length=1)
    position: int = Field(ge=0, description="Zero-based token position in the stream")
    text: str
    arrived_at_ms: float = Field(ge=0, description="Milliseconds since run start")


class DoneEvent(BaseModel):
    """Emitted once per run — when the backend stream closes."""

    type: Literal["done"]
    run_id: str = Field(min_length=1)
    total_ms: float = Field(gt=0, description="Total generation time in milliseconds")


# Discriminated union — the only type that may enter the asyncio.Queue.
# Pydantic uses the `type` field as the discriminator for fast parsing.
QueueEvent = Annotated[
    Union[TTFTEvent, TokenEvent, DoneEvent],
    Field(discriminator="type"),
]
