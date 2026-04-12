from __future__ import annotations

import pytest
from pydantic import ValidationError

from llmscope.types.config import AppConfig


class TestAppConfig:
    def test_defaults(self) -> None:
        cfg = AppConfig()
        assert cfg.proxy_port == 8080
        assert cfg.backend == "ollama"
        assert cfg.backend_url == "http://localhost:11434"
        assert cfg.queue_maxsize == 10_000
        assert cfg.stall_threshold_ms == 500.0
        assert cfg.dashboard_port == 3000

    def test_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LLMSCOPE_PROXY_PORT", "9090")
        monkeypatch.setenv("LLMSCOPE_BACKEND", "llamacpp")
        cfg = AppConfig()
        assert cfg.proxy_port == 9090
        assert cfg.backend == "llamacpp"

    def test_invalid_backend_literal_rejected(self) -> None:
        with pytest.raises(ValidationError):
            AppConfig(backend="openai")  # type: ignore[arg-type]

    def test_proxy_port_lower_bound(self) -> None:
        with pytest.raises(ValidationError):
            AppConfig(proxy_port=0)

    def test_proxy_port_upper_bound(self) -> None:
        with pytest.raises(ValidationError):
            AppConfig(proxy_port=65536)

    def test_queue_maxsize_must_be_positive(self) -> None:
        with pytest.raises(ValidationError):
            AppConfig(queue_maxsize=0)

    def test_stall_threshold_must_be_positive(self) -> None:
        with pytest.raises(ValidationError):
            AppConfig(stall_threshold_ms=0.0)

    def test_custom_db_path(self) -> None:
        cfg = AppConfig(db_path="/tmp/test.db")
        assert cfg.db_path == "/tmp/test.db"

    def test_both_backends_accepted(self) -> None:
        assert AppConfig(backend="ollama").backend == "ollama"
        assert AppConfig(backend="llamacpp").backend == "llamacpp"
