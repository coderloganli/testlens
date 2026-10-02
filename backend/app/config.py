from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, read from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://testlens:testlens@localhost:5432/testlens"
    redis_url: str = "redis://localhost:6379/0"

    llm_provider: Literal["fake", "anthropic"] = "fake"
    anthropic_model: str = "claude-opus-5-5"
    anthropic_effort: Literal["low", "medium", "high", "xhigh", "max"] = "medium"
    anthropic_max_tokens: int = 16000

    agent_max_steps: int = 6
    query_cache_ttl_seconds: int = 300
    session_ttl_seconds: int = 3600

    log_level: str = "INFO"
    log_json: bool = True
    otel_service_name: str = "testlens-api"
    otel_exporter_otlp_endpoint: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
