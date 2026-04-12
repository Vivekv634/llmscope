from __future__ import annotations

import pytest

from llmscope.proxy.backends.llamacpp import LlamaCppBackend
from llmscope.proxy.backends.ollama import OllamaBackend
from llmscope.types.config import AppConfig


@pytest.fixture
def config() -> AppConfig:
    return AppConfig(backend_url="http://localhost:11434")


@pytest.fixture
def ollama(config: AppConfig) -> OllamaBackend:
    return OllamaBackend(config)


@pytest.fixture
def llamacpp() -> LlamaCppBackend:
    return LlamaCppBackend(AppConfig(backend_url="http://localhost:8080"))


class TestOllamaBackend:
    def test_name(self, ollama: OllamaBackend) -> None:
        assert ollama.name == "ollama"

    def test_base_url(self, ollama: OllamaBackend) -> None:
        assert ollama.base_url == "http://localhost:11434"

    def test_generate_url(self, ollama: OllamaBackend) -> None:
        assert ollama.generate_url() == "http://localhost:11434/api/generate"

    def test_chat_url(self, ollama: OllamaBackend) -> None:
        assert ollama.chat_url() == "http://localhost:11434/api/chat"

    async def test_parse_chunk_valid_json(self, ollama: OllamaBackend) -> None:
        raw = '{"model":"llama3","response":"Hello","done":false}'
        result = await ollama.parse_chunk(raw)
        assert result == "Hello"

    async def test_parse_chunk_empty_response_field(self, ollama: OllamaBackend) -> None:
        raw = '{"model":"llama3","response":"","done":true}'
        result = await ollama.parse_chunk(raw)
        assert result == ""

    async def test_parse_chunk_missing_response_field(self, ollama: OllamaBackend) -> None:
        raw = '{"model":"llama3","done":true}'
        result = await ollama.parse_chunk(raw)
        assert result == ""

    async def test_parse_chunk_invalid_json(self, ollama: OllamaBackend) -> None:
        result = await ollama.parse_chunk("not json")
        assert result == ""

    async def test_parse_chunk_empty_string(self, ollama: OllamaBackend) -> None:
        result = await ollama.parse_chunk("")
        assert result == ""


class TestLlamaCppBackend:
    def test_name(self, llamacpp: LlamaCppBackend) -> None:
        assert llamacpp.name == "llamacpp"

    def test_base_url(self, llamacpp: LlamaCppBackend) -> None:
        assert llamacpp.base_url == "http://localhost:8080"

    def test_generate_url(self, llamacpp: LlamaCppBackend) -> None:
        assert llamacpp.generate_url() == "http://localhost:8080/completion"

    def test_chat_url(self, llamacpp: LlamaCppBackend) -> None:
        assert llamacpp.chat_url() == "http://localhost:8080/v1/chat/completions"

    async def test_parse_chunk_sse_data_prefix(self, llamacpp: LlamaCppBackend) -> None:
        raw = 'data: {"content":"Hello","stop":false}'
        result = await llamacpp.parse_chunk(raw)
        assert result == "Hello"

    async def test_parse_chunk_done_sentinel(self, llamacpp: LlamaCppBackend) -> None:
        result = await llamacpp.parse_chunk("data: [DONE]")
        assert result == ""

    async def test_parse_chunk_invalid_json(self, llamacpp: LlamaCppBackend) -> None:
        result = await llamacpp.parse_chunk("data: bad json")
        assert result == ""

    async def test_parse_chunk_missing_content_field(self, llamacpp: LlamaCppBackend) -> None:
        raw = 'data: {"stop":true}'
        result = await llamacpp.parse_chunk(raw)
        assert result == ""
