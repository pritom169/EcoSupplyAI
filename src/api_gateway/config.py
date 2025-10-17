"""Configuration for the EcoSupplyAI API Gateway."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore"
    )

    # JWT
    JWT_SECRET_KEY: str = Field(default="change-me-in-production")
    JWT_ALGORITHM: str = Field(default="HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30)

    # CORS
    ALLOWED_ORIGINS: list[str] = Field(
        default=["https://app.ecosupplyai.dev", "http://localhost:3000"]
    )

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://ecosupplyai:ecosupplyai@localhost:5432/ecosupplyai"
    )

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = Field(default=60)

    # PII filtering
    PII_DETECTION_ENABLED: bool = Field(default=True)

    # Downstream service URLs
    CHAT_AGENT_URL: str = Field(default="http://localhost:8001")
    RAG_SERVICE_URL: str = Field(default="http://localhost:8002")
    SCORING_SERVICE_URL: str = Field(default="http://localhost:8003")
    FORECAST_SERVICE_URL: str = Field(default="http://localhost:8004")
    CONTENT_GEN_URL: str = Field(default="http://localhost:8005")
    WORKFLOW_ENGINE_URL: str = Field(default="http://localhost:8006")

    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0")

    # Observability
    OTEL_EXPORTER_OTLP_ENDPOINT: str = Field(default="http://localhost:4317")
    OTEL_SERVICE_NAME: str = Field(default="ecosupplyai-api-gateway")

    # Server
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8000)
    DEBUG: bool = Field(default=False)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()