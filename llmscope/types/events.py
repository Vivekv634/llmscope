from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field


class RunStartEvent(BaseModel):
    type: Literal["start"]
    run_id: str = Field(min_length=1)
    model: str = Field(min_length=1)
    backend: str = Field(min_length=1)
    prompt_hash: str = Field(min_length=1)
    prompt_text: str


class TTFTEvent(BaseModel):
    type: Literal["ttft"]
    run_id: str = Field(min_length=1)
    ttft_ms: float = Field(gt=0)


class TokenEvent(BaseModel):
    type: Literal["token"]
    run_id: str = Field(min_length=1)
    position: int = Field(ge=0)
    text: str
    arrived_at_ms: float = Field(ge=0)


class DoneEvent(BaseModel):
    type: Literal["done"]
    run_id: str = Field(min_length=1)
    total_ms: float = Field(gt=0)


QueueEvent = Annotated[
    Union[RunStartEvent, TTFTEvent, TokenEvent, DoneEvent],
    Field(discriminator="type"),
]
