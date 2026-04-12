from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Optional

import httpx

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from llmscope.compare.engine import CompareResult, compare_models
from llmscope.proxy.backends.base import AbstractBackend
from llmscope.proxy.interceptor import intercept_stream
from llmscope.signals.latency import compute_latency
from llmscope.signals.quality import output_entropy
from llmscope.store.db import DatabaseStore
from llmscope.types.config import AppConfig
from llmscope.types.events import (
    DoneEvent,
    QueueEvent,
    RunStartEvent,
    TTFTEvent,
    TokenEvent,
)
from llmscope.types.runs import OutputRecord, RunRecord, TokenRecord
from llmscope.types.signals import SignalResponse

_logger: logging.Logger = logging.getLogger(__name__)

_Subscribers = dict[str, list[asyncio.Queue[str]]]


class CompareRequest(BaseModel):
    prompt: str
    models: list[str]


def _broadcast(subscribers: _Subscribers, run_id: str, payload: str) -> None:
    for q in subscribers.get(run_id, []):
        try:
            q.put_nowait(payload)
        except asyncio.QueueFull:
            pass


async def queue_worker(
    queue: asyncio.Queue[QueueEvent],
    db: DatabaseStore,
    subscribers: _Subscribers,
) -> None:
    while True:
        event: QueueEvent = await queue.get()
        if isinstance(event, RunStartEvent):
            db.record_start(event)
        elif isinstance(event, TTFTEvent):
            db.record_ttft(event)
            _logger.info("run=%s TTFT=%.1fms", event.run_id, event.ttft_ms)
        elif isinstance(event, TokenEvent):
            db.record_token(event)
            _broadcast(subscribers, event.run_id, event.model_dump_json())
        elif isinstance(event, DoneEvent):
            db.finalize_run(event)
            _broadcast(subscribers, event.run_id, event.model_dump_json())
            _logger.info(
                "run=%s done total=%.1fms", event.run_id, event.total_ms
            )
        queue.task_done()


def create_app(
    config: AppConfig,
    db: DatabaseStore,
    backend: AbstractBackend,
) -> FastAPI:
    queue: asyncio.Queue[QueueEvent] = asyncio.Queue(
        maxsize=config.queue_maxsize
    )
    subscribers: _Subscribers = {}

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        worker_task: asyncio.Task[None] = asyncio.create_task(
            queue_worker(queue, db, subscribers)
        )
        yield
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass

    app: FastAPI = FastAPI(lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.post("/api/compare", response_model=list[CompareResult])
    async def api_compare(body: CompareRequest) -> list[CompareResult]:
        return await compare_models(
            prompt=body.prompt,
            models=body.models,
            backend_url=config.backend_url,
        )

    @app.post("/api/generate")
    async def proxy_generate(request: Request) -> StreamingResponse:
        return await intercept_stream(
            request, backend.generate_url(), queue, backend
        )

    @app.post("/api/chat")
    async def proxy_chat(request: Request) -> StreamingResponse:
        return await intercept_stream(
            request, backend.chat_url(), queue, backend
        )

    @app.get("/api/models", response_model=list[str])
    async def list_models() -> list[str]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{config.backend_url}/api/tags")
                resp.raise_for_status()
                data: object = resp.json()
                if not isinstance(data, dict):
                    return []
                models_raw: object = data.get("models", [])
                if not isinstance(models_raw, list):
                    return []
                return [
                    str(m["name"])
                    for m in models_raw
                    if isinstance(m, dict) and "name" in m
                ]
        except httpx.HTTPError:
            raise HTTPException(status_code=502, detail="backend unreachable")

    @app.get("/api/runs", response_model=list[RunRecord])
    async def list_runs(limit: int = 50) -> list[RunRecord]:
        return db.list_runs(limit=limit)

    @app.get("/api/runs/{run_id}", response_model=RunRecord)
    async def get_run(run_id: str) -> RunRecord:
        result: Optional[RunRecord] = db.get_run(run_id)
        if result is None:
            raise HTTPException(status_code=404, detail="run not found")
        return result

    @app.get("/api/runs/{run_id}/tokens", response_model=list[TokenRecord])
    async def get_tokens(run_id: str) -> list[TokenRecord]:
        return db.get_tokens(run_id)

    @app.get("/api/runs/{run_id}/output", response_model=OutputRecord)
    async def get_output(run_id: str) -> OutputRecord:
        result: Optional[OutputRecord] = db.get_output(run_id)
        if result is None:
            raise HTTPException(status_code=404, detail="output not found")
        return result

    @app.get("/api/runs/{run_id}/signals", response_model=SignalResponse)
    async def get_signals(run_id: str) -> SignalResponse:
        run: Optional[RunRecord] = db.get_run(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="run not found")
        tokens: list[TokenRecord] = db.get_tokens(run_id)
        latency = compute_latency(
            arrived_ms=[t.arrived_at_ms for t in tokens],
            ttft_ms=run.ttft_ms or 0.0,
            total_ms=run.total_ms or 0.0,
            stall_threshold_ms=config.stall_threshold_ms,
        )
        quality = output_entropy([t.text for t in tokens])
        return SignalResponse(latency=latency, quality=quality)

    @app.websocket("/ws/stream/{run_id}")
    async def ws_stream(websocket: WebSocket, run_id: str) -> None:
        await websocket.accept()
        q: asyncio.Queue[str] = asyncio.Queue(maxsize=500)
        subscribers.setdefault(run_id, []).append(q)
        try:
            while True:
                try:
                    msg: str = await asyncio.wait_for(q.get(), timeout=30.0)
                    await websocket.send_text(msg)
                    if '"type":"done"' in msg:
                        break
                except asyncio.TimeoutError:
                    await websocket.send_text('{"type":"ping"}')
        except WebSocketDisconnect:
            pass
        finally:
            subs: list[asyncio.Queue[str]] = subscribers.get(run_id, [])
            if q in subs:
                subs.remove(q)
            if not subs:
                subscribers.pop(run_id, None)

    return app
