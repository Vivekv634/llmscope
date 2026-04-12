from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator
from typing import Any

import httpx
import pytest
from starlette.requests import Request
from starlette.types import Message, Receive, Scope

from llmscope.proxy.backends.ollama import OllamaBackend
from llmscope.proxy.interceptor import intercept_stream
from llmscope.types.config import AppConfig
from llmscope.types.events import (
    DoneEvent,
    QueueEvent,
    RunStartEvent,
    TTFTEvent,
    TokenEvent,
)


class _MockAsyncStream(httpx.AsyncByteStream):
    def __init__(self, chunks: list[bytes]) -> None:
        self._chunks: list[bytes] = chunks

    async def __aiter__(self) -> AsyncGenerator[bytes, None]:
        for chunk in self._chunks:
            yield chunk


class _MockAsyncTransport(httpx.AsyncBaseTransport):
    def __init__(self, chunks: list[bytes]) -> None:
        self._chunks: list[bytes] = chunks

    async def handle_async_request(
        self, request: httpx.Request
    ) -> httpx.Response:
        return httpx.Response(200, stream=_MockAsyncStream(self._chunks))


def _build_request(body: bytes) -> Request:
    scope: Scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/generate",
        "query_string": b"",
        "headers": [(b"content-type", b"application/json")],
        "root_path": "",
        "scheme": "http",
        "server": ("testserver", 80),
    }

    async def receive() -> Message:
        return {"type": "http.request", "body": body, "more_body": False}

    return Request(scope, receive=receive)


def _make_ollama_chunk(text: str, done: bool = False) -> bytes:
    return (
        json.dumps({"model": "llama3", "response": text, "done": done}) + "\n"
    ).encode()


@pytest.fixture
def config() -> AppConfig:
    return AppConfig()


@pytest.fixture
def backend(config: AppConfig) -> OllamaBackend:
    return OllamaBackend(config)


@pytest.fixture
def queue() -> asyncio.Queue[QueueEvent]:
    return asyncio.Queue(maxsize=1000)


class TestInterceptStream:
    async def test_run_start_event_emitted(
        self,
        backend: OllamaBackend,
        queue: asyncio.Queue[QueueEvent],
    ) -> None:
        chunks = [_make_ollama_chunk("Hello"), _make_ollama_chunk("", done=True)]
        transport = _MockAsyncTransport(chunks)
        body = json.dumps({"model": "llama3", "prompt": "hi"}).encode()
        request = _build_request(body)

        response = await intercept_stream(
            request, "http://fake/api/generate", queue, backend, transport
        )
        async for _ in response.body_iterator:
            pass

        events: list[QueueEvent] = []
        while not queue.empty():
            events.append(queue.get_nowait())

        start_events = [e for e in events if isinstance(e, RunStartEvent)]
        assert len(start_events) == 1
        assert start_events[0].model == "llama3"
        assert start_events[0].backend == "ollama"

    async def test_ttft_event_emitted_on_first_chunk(
        self,
        backend: OllamaBackend,
        queue: asyncio.Queue[QueueEvent],
    ) -> None:
        chunks = [_make_ollama_chunk("Hello"), _make_ollama_chunk("", done=True)]
        transport = _MockAsyncTransport(chunks)
        body = json.dumps({"model": "llama3", "prompt": "hi"}).encode()
        request = _build_request(body)

        response = await intercept_stream(
            request, "http://fake/api/generate", queue, backend, transport
        )
        async for _ in response.body_iterator:
            pass

        events: list[QueueEvent] = []
        while not queue.empty():
            events.append(queue.get_nowait())

        ttft_events = [e for e in events if isinstance(e, TTFTEvent)]
        assert len(ttft_events) == 1
        assert ttft_events[0].ttft_ms > 0

    async def test_token_events_emitted_per_chunk(
        self,
        backend: OllamaBackend,
        queue: asyncio.Queue[QueueEvent],
    ) -> None:
        chunks = [
            _make_ollama_chunk("Hello"),
            _make_ollama_chunk(" world"),
            _make_ollama_chunk("", done=True),
        ]
        transport = _MockAsyncTransport(chunks)
        body = json.dumps({"model": "llama3", "prompt": "hi"}).encode()
        request = _build_request(body)

        response = await intercept_stream(
            request, "http://fake/api/generate", queue, backend, transport
        )
        async for _ in response.body_iterator:
            pass

        events: list[QueueEvent] = []
        while not queue.empty():
            events.append(queue.get_nowait())

        token_events = [e for e in events if isinstance(e, TokenEvent)]
        assert len(token_events) == 3
        assert token_events[0].position == 0
        assert token_events[1].position == 1
        assert token_events[2].position == 2

    async def test_done_event_emitted_at_end(
        self,
        backend: OllamaBackend,
        queue: asyncio.Queue[QueueEvent],
    ) -> None:
        chunks = [_make_ollama_chunk("Hi"), _make_ollama_chunk("", done=True)]
        transport = _MockAsyncTransport(chunks)
        body = json.dumps({"model": "llama3", "prompt": "hello"}).encode()
        request = _build_request(body)

        response = await intercept_stream(
            request, "http://fake/api/generate", queue, backend, transport
        )
        async for _ in response.body_iterator:
            pass

        events: list[QueueEvent] = []
        while not queue.empty():
            events.append(queue.get_nowait())

        done_events = [e for e in events if isinstance(e, DoneEvent)]
        assert len(done_events) == 1
        assert done_events[0].total_ms > 0

    async def test_chunks_forwarded_to_client(
        self,
        backend: OllamaBackend,
        queue: asyncio.Queue[QueueEvent],
    ) -> None:
        raw_chunks = [_make_ollama_chunk("Hello"), _make_ollama_chunk(" world")]
        transport = _MockAsyncTransport(raw_chunks)
        body = json.dumps({"model": "llama3", "prompt": "hi"}).encode()
        request = _build_request(body)

        response = await intercept_stream(
            request, "http://fake/api/generate", queue, backend, transport
        )
        received: list[bytes] = []
        async for chunk in response.body_iterator:
            if isinstance(chunk, bytes):
                received.append(chunk)

        assert b"".join(received) == b"".join(raw_chunks)

    async def test_all_run_ids_match(
        self,
        backend: OllamaBackend,
        queue: asyncio.Queue[QueueEvent],
    ) -> None:
        chunks = [_make_ollama_chunk("Hi"), _make_ollama_chunk("", done=True)]
        transport = _MockAsyncTransport(chunks)
        body = json.dumps({"model": "llama3", "prompt": "test"}).encode()
        request = _build_request(body)

        response = await intercept_stream(
            request, "http://fake/api/generate", queue, backend, transport
        )
        async for _ in response.body_iterator:
            pass

        events: list[QueueEvent] = []
        while not queue.empty():
            events.append(queue.get_nowait())

        run_ids: set[str] = {e.run_id for e in events}
        assert len(run_ids) == 1

    async def test_prompt_hash_computed_from_prompt_text(
        self,
        backend: OllamaBackend,
        queue: asyncio.Queue[QueueEvent],
    ) -> None:
        import hashlib

        chunks = [_make_ollama_chunk("Hi")]
        transport = _MockAsyncTransport(chunks)
        prompt = "test prompt"
        body = json.dumps({"model": "llama3", "prompt": prompt}).encode()
        request = _build_request(body)

        response = await intercept_stream(
            request, "http://fake/api/generate", queue, backend, transport
        )
        async for _ in response.body_iterator:
            pass

        events: list[QueueEvent] = []
        while not queue.empty():
            events.append(queue.get_nowait())

        start = next(e for e in events if isinstance(e, RunStartEvent))
        expected_hash = hashlib.sha256(prompt.encode()).hexdigest()
        assert start.prompt_hash == expected_hash
