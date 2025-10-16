"""Embedding generation using Azure OpenAI with caching and cost tracking."""

from __future__ import annotations

import hashlib
from functools import lru_cache
from typing import Any

import structlog
import tiktoken
from openai import AsyncAzureOpenAI

from src.rag_pipeline.config import RAGSettings, get_rag_settings

logger = structlog.get_logger(__name__)

# Pricing per 1M tokens (text-embedding-3-small)
EMBEDDING_COST_PER_1M_TOKENS = 0.02


class AzureOpenAIEmbedder:
    def __init__(self, settings: RAGSettings | None = None) -> None:
        self.settings = settings or get_rag_settings()
        self.client = AsyncAzureOpenAI(
            azure_endpoint=self.settings.AZURE_OPENAI_ENDPOINT,
            api_key=self.settings.AZURE_OPENAI_API_KEY,
            api_version=self.settings.AZURE_OPENAI_API_VERSION,
        )
        self.model = self.settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT
        self._tokenizer = tiktoken.get_encoding("cl100k_base")
        self._cache: dict[str, list[float]] = {}
        self.total_tokens_used: int = 0

    def count_tokens(self, text: str) -> int:
        return len(self._tokenizer.encode(text))

    def _cache_key(self, text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()

    async def embed(self, text: str) -> list[float]:
        key = self._cache_key(text)
        if key in self._cache:
            return self._cache[key]

        result = await self._embed_batch([text])
        self._cache[key] = result[0]
        return result[0]

    async def embed_batch(self, texts: list[str], batch_size: int = 100) -> list[list[float]]:
        all_embeddings: list[list[float]] = []
        uncached_texts: list[str] = []
        uncached_indices: list[int] = []
        results: dict[int, list[float]] = {}

        for i, text in enumerate(texts):
            key = self._cache_key(text)
            if key in self._cache:
                results[i] = self._cache[key]
            else:
                uncached_texts.append(text)
                uncached_indices.append(i)

        # Batch embed uncached texts
        for start in range(0, len(uncached_texts), batch_size):
            batch = uncached_texts[start : start + batch_size]
            embeddings = await self._embed_batch(batch)
            for j, emb in enumerate(embeddings):
                idx = uncached_indices[start + j]
                results[idx] = emb
                self._cache[self._cache_key(batch[j])] = emb

        for i in range(len(texts)):
            all_embeddings.append(results[i])

        return all_embeddings

    async def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        total_tokens = sum(self.count_tokens(t) for t in texts)
        self.total_tokens_used += total_tokens

        logger.info("embedder.batch", count=len(texts), tokens=total_tokens)

        response = await self.client.embeddings.create(input=texts, model=self.model)
        return [item.embedding for item in response.data]

    @property
    def estimated_cost(self) -> float:
        return (self.total_tokens_used / 1_000_000) * EMBEDDING_COST_PER_1M_TOKENS