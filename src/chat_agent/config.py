"""Configuration for the Chat Agent service."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ChatAgentSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    AZURE_OPENAI_ENDPOINT: str = Field(default="https://example.openai.azure.com/")
    AZURE_OPENAI_API_KEY: str = Field(default="change-me")
    AZURE_OPENAI_DEPLOYMENT_NAME: str = Field(default="gpt-4o")
    AZURE_OPENAI_API_VERSION: str = Field(default="2024-12-01-preview")

    RAG_SERVICE_URL: str = Field(default="http://localhost:8002")
    SCORING_SERVICE_URL: str = Field(default="http://localhost:8003")
    FORECAST_SERVICE_URL: str = Field(default="http://localhost:8004")

    MAX_TURNS: int = Field(default=10)
    TEMPERATURE: float = Field(default=0.3)
    MEMORY_TYPE: str = Field(default="buffer")  # "buffer" or "summary"


@lru_cache(maxsize=1)
def get_chat_settings() -> ChatAgentSettings:
    return ChatAgentSettings()