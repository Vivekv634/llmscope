from __future__ import annotations

import asyncio
import hashlib
import json
import time
import uuid
from collections.abc import AsyncGenerator
from typing import Optional

import httpx
from fastapi import Request
from fastapi.responses import StreamingResponse

from llmscope.proxy.backends.base import AbstractBackend
from llmscope.types.events import (
    DoneEvent,
    QueueEvent,
    RunStartEvent,
    TTFTEvent,
    TokenEvent,
)


def _generate_run_id() -> str:
    return uuid.uuid4().hex


def _compute_prompt_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _safe_enqueue(queue: asyncio.Queue[QueueEvent], event: QueueEvent) -> None:
    try:
        queue.put_nowait(event)
    except asyncio.QueueFull:
        pass


async def intercept_stream(
    request: Request,
    target_url: str,
    queue: asyncio.Queue[QueueEvent],
    backend: AbstractBackend,
    transport: Optional[httpx.AsyncBaseTransport] = None,
) -> StreamingResponse:
    body: bytes = await request.body()
    body_data: object = json.loads(body) if body else {}
    model: str = ""
    prompt_text: str = ""
    if isinstance(body_data, dict):
        model = str(body_data.get("model", "unknown"))
        prompt_text = str(body_data.get("prompt", ""))
    else:
        model = "unknown"

    prompt_hash: str = _compute_prompt_hash(prompt_text)
    run_id: str = _generate_run_id()
    t_start: float = time.monotonic()

    _safe_enqueue(
        queue,
        RunStartEvent(
            type="start",
            run_id=run_id,
            model=model,
            backend=backend.name,
            prompt_hash=prompt_hash,
            prompt_text=prompt_text,
        ),
    )

    async def stream_generator() -> AsyncGenerator[bytes, None]:
        first_token: bool = True
        position: int = 0
        client: httpx.AsyncClient = (
            httpx.AsyncClient(transport=transport)
            if transport is not None
            else httpx.AsyncClient()
        )
        async with client:
            async with client.stream(
                "POST",
                target_url,
                content=body,
                headers={"Content-Type": "application/json"},
                timeout=None,
            ) as resp:
                async for chunk in resp.aiter_text():
                    now: float = time.monotonic()
                    if first_token:
                        _safe_enqueue(
                            queue,
                            TTFTEvent(
                                type="ttft",
                                run_id=run_id,
                                ttft_ms=(now - t_start) * 1000,
                            ),
                        )
                        first_token = False
                    _safe_enqueue(
                        queue,
                        TokenEvent(
                            type="token",
                            run_id=run_id,
                            position=position,
                            text=chunk,
                            arrived_at_ms=(now - t_start) * 1000,
                        ),
                    )
                    position += 1
                    yield chunk.encode()

        _safe_enqueue(
            queue,
            DoneEvent(
                type="done",
                run_id=run_id,
                total_ms=(time.monotonic() - t_start) * 1000,
            ),
        )

    return StreamingResponse(stream_generator(), media_type="text/event-stream")
