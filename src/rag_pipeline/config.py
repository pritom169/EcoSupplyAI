"""Configuration for the RAG Pipeline service."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class RAGSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    AZURE_OPENAI_ENDPOINT: str = Field(default="https://example.openai.azure.com/")
    AZURE_OPENAI_API_KEY: str = Field(default="change-me")
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT: str = Field(default="text-embedding-3-small")
    AZURE_OPENAI_API_VERSION: str = Field(default="2024-12-01-preview")

    QDRANT_HOST: str = Field(default="localhost")
    QDRANT_PORT: int = Field(default=6333)
    COLLECTION_NAME: str = Field(default="ecosupplyai_docs")

    CHUNK_SIZE: int = Field(default=512)
    CHUNK_OVERLAP: int = Field(default=50)
    TOP_K: int = Field(default=5)
    SIMILARITY_THRESHOLD: float = Field(default=0.75)

    OTEL_SERVICE_NAME: str = Field(default="ecosupplyai-rag-pipeline")


@lru_cache(maxsize=1)
def get_rag_settings() -> RAGSettings:
    return RAGSettings()