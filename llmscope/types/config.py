from __future__ import annotations

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LLMSCOPE_", env_file=".env")

    proxy_port: int = Field(default=8080, gt=0, lt=65536)
    backend: Literal["ollama", "llamacpp"] = "ollama"
    backend_url: str = Field(default="http://localhost:11434")
    db_path: str = Field(default="~/.llmscope/traces.db")
    queue_maxsize: int = Field(default=10_000, gt=0)
    stall_threshold_ms: float = Field(default=500.0, gt=0)
    dashboard_port: int = Field(default=3000, gt=0, lt=65536)
