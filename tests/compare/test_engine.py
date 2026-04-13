from __future__ import annotations

import json

import httpx
import pytest

from llmscope.compare.engine import CompareResult, compare_models
from llmscope.types.signals import QualityResult


def _ndjson(*chunks: dict[str, object]) -> bytes:
    return b"\n".join(json.dumps(c).encode() for c in chunks)


class _MockStream(httpx.AsyncByteStream):
    def __init__(self, body: bytes) -> None:
        self._body: bytes = body

    async def __aiter__(self):  # type: ignore[override]
        yield self._body


class _MockTransport(httpx.AsyncBaseTransport):
    def __init__(self, body: bytes) -> None:
        self._body: bytes = body

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, stream=_MockStream(self._body))


@pytest.mark.asyncio
async def test_compare_single_model_returns_one_result() -> None:
    body = _ndjson(
        {"response": "Hello"},
        {"response": " world"},
        {"response": ""},
    )
    transport = _MockTransport(body)
    results = await compare_models(
        prompt="hi",
        models=["llama3.2"],
        backend_url="http://localhost:11434",
        transport=transport,
    )
    assert len(results) == 1
    assert results[0].model == "llama3.2"


@pytest.mark.asyncio
async def test_compare_result_is_typed_model() -> None:
    body = _ndjson({"response": "hi"})
    transport = _MockTransport(body)
    results = await compare_models(
        prompt="test",
        models=["model-a"],
        backend_url="http://localhost:11434",
        transport=transport,
    )
    r: CompareResult = results[0]
    assert isinstance(r, CompareResult)
    assert isinstance(r.quality, QualityResult)


@pytest.mark.asyncio
async def test_compare_output_concatenates_tokens() -> None:
    body = _ndjson(
        {"response": "the "},
        {"response": "cat"},
        {"response": " sat"},
    )
    transport = _MockTransport(body)
    results = await compare_models(
        prompt="prompt",
        models=["m"],
        backend_url="http://localhost:11434",
        transport=transport,
    )
    assert results[0].output == "the cat sat"


@pytest.mark.asyncio
async def test_compare_token_count_correct() -> None:
    body = _ndjson(
        {"response": "a"},
        {"response": "b"},
        {"response": "c"},
    )
    transport = _MockTransport(body)
    results = await compare_models(
        prompt="p",
        models=["m"],
        backend_url="http://localhost:11434",
        transport=transport,
    )
    assert results[0].token_count == 3


@pytest.mark.asyncio
async def test_compare_multiple_models_returns_all() -> None:
    body = _ndjson({"response": "ok"})
    results = await compare_models(
        prompt="p",
        models=["m1", "m2", "m3"],
        backend_url="http://localhost:11434",
        transport=_MockTransport(body),
    )
    assert len(results) == 3
    models = [r.model for r in results]
    assert "m1" in models
    assert "m2" in models
    assert "m3" in models


@pytest.mark.asyncio
async def test_compare_empty_response_yields_zero_tokens() -> None:
    body = _ndjson({"response": ""})
    transport = _MockTransport(body)
    results = await compare_models(
        prompt="p",
        models=["m"],
        backend_url="http://localhost:11434",
        transport=transport,
    )
    assert results[0].token_count == 1
    assert results[0].output == ""


@pytest.mark.asyncio
async def test_compare_tps_positive_for_nonempty_response() -> None:
    body = _ndjson({"response": "a"}, {"response": "b"})
    transport = _MockTransport(body)
    results = await compare_models(
        prompt="p",
        models=["m"],
        backend_url="http://localhost:11434",
        transport=transport,
    )
    assert results[0].tps >= 0.0


@pytest.mark.asyncio
async def test_compare_skips_non_json_lines() -> None:
    body = b"not-json\n" + json.dumps({"response": "hi"}).encode()
    transport = _MockTransport(body)
    results = await compare_models(
        prompt="p",
        models=["m"],
        backend_url="http://localhost:11434",
        transport=transport,
    )
    assert results[0].output == "hi"
