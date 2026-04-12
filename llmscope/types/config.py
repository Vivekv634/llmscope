"""Application configuration loaded from environment variables or defaults.

All config values have sensible defaults so `llmscope start` works with
zero setup. Each value can be overridden by an env var prefixed LLMSCOPE_
(e.g. LLMSCOPE_PROXY_PORT=9090).
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    """Central config object — one instance per process, passed by reference."""

    model_config = SettingsConfigDict(env_prefix="LLMSCOPE_", env_file=".env")

    proxy_port: int = Field(default=8080, gt=0, lt=65536)
    backend: Literal["ollama", "llamacpp"] = "ollama"
    backend_url: str = Field(
        default="http://localhost:11434",
        description="Base URL of the upstream LLM backend",
    )
    db_path: str = Field(
        default="~/.llmscope/traces.db",
        description="Path to the DuckDB database file",
    )
    queue_maxsize: int = Field(
        default=10_000,
        gt=0,
        description="Max events buffered in the asyncio.Queue before drop policy",
    )
    stall_threshold_ms: float = Field(
        default=500.0,
        gt=0,
        description="Inter-token gap (ms) above which a position is flagged as a stall",
    )
    dashboard_port: int = Field(default=3000, gt=0, lt=65536)
