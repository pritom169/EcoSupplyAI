"""Vector database interfaces — Qdrant (primary) and Azure AI Search (stub)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import structlog
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

logger = structlog.get_logger(__name__)


@dataclass
class SearchResult:
    chunk_id: str
    text: str
    score: float
    metadata: dict[str, Any]


class VectorStore(ABC):
    @abstractmethod
    async def create_collection(self, name: str, dimension: int) -> None: ...

    @abstractmethod
    async def upsert(self, collection: str, ids: list[str], embeddings: list[list[float]], texts: list[str], metadatas: list[dict]) -> None: ...

    @abstractmethod
    async def search(self, collection: str, query_embedding: list[float], top_k: int = 5, filters: dict | None = None) -> list[SearchResult]: ...

    @abstractmethod
    async def delete_collection(self, name: str) -> None: ...


class QdrantVectorStore(VectorStore):
    def __init__(self, host: str = "localhost", port: int = 6333) -> None:
        self.client = QdrantClient(host=host, port=port)

    async def create_collection(self, name: str, dimension: int) -> None:
        collections = self.client.get_collections().collections
        existing = [c.name for c in collections]
        if name not in existing:
            self.client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=dimension, distance=Distance.COSINE),
            )
            logger.info("vector_store.collection_created", name=name, dimension=dimension)

    async def upsert(
        self,
        collection: str,
        ids: list[str],
        embeddings: list[list[float]],
        texts: list[str],
        metadatas: list[dict],
    ) -> None:
        points = [
            PointStruct(
                id=i,
                vector=embedding,
                payload={"text": text, "chunk_id": chunk_id, **meta},
            )
            for i, (chunk_id, embedding, text, meta) in enumerate(zip(ids, embeddings, texts, metadatas))
        ]
        self.client.upsert(collection_name=collection, points=points)
        logger.info("vector_store.upserted", collection=collection, count=len(points))

    async def search(
        self,
        collection: str,
        query_embedding: list[float],
        top_k: int = 5,
        filters: dict | None = None,
    ) -> list[SearchResult]:
        results = self.client.search(
            collection_name=collection,
            query_vector=query_embedding,
            limit=top_k,
        )
        return [
            SearchResult(
                chunk_id=str(hit.payload.get("chunk_id", "")),
                text=str(hit.payload.get("text", "")),
                score=hit.score,
                metadata={k: v for k, v in hit.payload.items() if k not in ("text", "chunk_id")},
            )
            for hit in results
        ]

    async def delete_collection(self, name: str) -> None:
        self.client.delete_collection(collection_name=name)
        logger.info("vector_store.collection_deleted", name=name)


class AzureAISearchStore(VectorStore):
    """Stub for Azure AI Search integration — same interface as Qdrant."""

    def __init__(self, endpoint: str = "", api_key: str = "", index_name: str = "") -> None:
        self.endpoint = endpoint
        self.api_key = api_key
        self.index_name = index_name

    async def create_collection(self, name: str, dimension: int) -> None:
        logger.info("azure_search.create_index", name=name)
        # Implementation: use azure.search.documents.indexes.SearchIndexClient

    async def upsert(self, collection: str, ids: list[str], embeddings: list[list[float]], texts: list[str], metadatas: list[dict]) -> None:
        logger.info("azure_search.upsert", count=len(ids))

    async def search(self, collection: str, query_embedding: list[float], top_k: int = 5, filters: dict | None = None) -> list[SearchResult]:
        logger.info("azure_search.search")
        return []

    async def delete_collection(self, name: str) -> None:
        logger.info("azure_search.delete_index", name=name)