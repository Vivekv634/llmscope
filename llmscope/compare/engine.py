from __future__ import annotations

import json
import time
from typing import Optional

import httpx
from pydantic import BaseModel, Field

from llmscope.signals.quality import output_entropy
from llmscope.types.signals import QualityResult


class CompareResult(BaseModel):
    model: str = Field(min_length=1)
    ttft_ms: float = Field(ge=0)
    total_ms: float = Field(ge=0)
    token_count: int = Field(ge=0)
    tps: float = Field(ge=0)
    quality: QualityResult
    output: str


async def _run_single(
    prompt: str,
    model: str,
    backend_url: str,
    transport: Optional[httpx.AsyncBaseTransport] = None,
) -> CompareResult:
    tokens: list[str] = []
    t0: float = time.monotonic()
    ttft_ms: float = 0.0
    first: bool = True

    if transport is not None:
        client_ctx = httpx.AsyncClient(transport=transport)
    else:
        client_ctx = httpx.AsyncClient()

    async with client_ctx as client:
        async with client.stream(
            "POST",
            f"{backend_url}/api/generate",
            json={"model": model, "prompt": prompt},
            timeout=None,
        ) as resp:
            async for line in resp.aiter_lines():
                if not line:
                    continue
                try:
                    raw: object = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(raw, dict):
                    continue
                token_text: str = str(raw.get("response", ""))
                now: float = time.monotonic()
                if first and token_text:
                    ttft_ms = (now - t0) * 1000
                    first = False
                tokens.append(token_text)

    total_ms: float = (time.monotonic() - t0) * 1000
    quality: QualityResult = output_entropy(tokens)
    tps: float = (
        round(len(tokens) / (total_ms / 1000.0), 4) if total_ms > 0 else 0.0
    )
    return CompareResult(
        model=model,
        ttft_ms=round(ttft_ms, 2),
        total_ms=round(total_ms, 2),
        token_count=len(tokens),
        tps=tps,
        quality=quality,
        output="".join(tokens),
    )


async def compare_models(
    prompt: str,
    models: list[str],
    backend_url: str,
    transport: Optional[httpx.AsyncBaseTransport] = None,
) -> list[CompareResult]:
    results: list[CompareResult] = []
    for model in models:
        result: CompareResult = await _run_single(
            prompt, model, backend_url, transport
        )
        results.append(result)
    return results
