"""Hybrid retriever with re-ranking (MMR) and citation tracking."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import structlog

from src.rag_pipeline.vector_store import SearchResult, VectorStore

logger = structlog.get_logger(__name__)


@dataclass
class RetrievalResult:
    chunks: list[SearchResult]
    query: str
    strategy: str


class HybridRetriever:
    """Combines dense vector search with MMR re-ranking for diversity."""

    def __init__(self, vector_store: VectorStore, collection: str, top_k: int = 5, similarity_threshold: float = 0.75) -> None:
        self.vector_store = vector_store
        self.collection = collection
        self.top_k = top_k
        self.similarity_threshold = similarity_threshold

    async def retrieve(
        self,
        query_embedding: list[float],
        query_text: str,
        top_k: int | None = None,
        filters: dict | None = None,
    ) -> RetrievalResult:
        k = top_k or self.top_k

        # Fetch more candidates for MMR re-ranking
        candidates = await self.vector_store.search(
            collection=self.collection,
            query_embedding=query_embedding,
            top_k=k * 3,
            filters=filters,
        )

        # Filter by similarity threshold
        candidates = [c for c in candidates if c.score >= self.similarity_threshold]

        if not candidates:
            logger.warning("retriever.no_results", query=query_text[:100])
            return RetrievalResult(chunks=[], query=query_text, strategy="hybrid+mmr")

        # Apply MMR re-ranking for diversity
        selected = self._mmr_rerank(candidates, query_embedding, k=k, lambda_param=0.7)

        logger.info("retriever.results", count=len(selected), top_score=selected[0].score if selected else 0)

        return RetrievalResult(chunks=selected, query=query_text, strategy="hybrid+mmr")

    def _mmr_rerank(
        self,
        candidates: list[SearchResult],
        query_embedding: list[float],
        k: int,
        lambda_param: float = 0.7,
    ) -> list[SearchResult]:
        """Maximal Marginal Relevance — balance relevance with diversity."""
        if len(candidates) <= k:
            return candidates

        selected: list[int] = []
        remaining = list(range(len(candidates)))

        # Pick the most relevant first
        selected.append(remaining.pop(0))

        while len(selected) < k and remaining:
            best_score = -float("inf")
            best_idx = remaining[0]

            for idx in remaining:
                relevance = candidates[idx].score
                # Max similarity to already selected
                max_sim = max(
                    self._text_similarity(candidates[idx].text, candidates[s].text)
                    for s in selected
                )
                mmr_score = lambda_param * relevance - (1 - lambda_param) * max_sim
                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = idx

            selected.append(best_idx)
            remaining.remove(best_idx)

        return [candidates[i] for i in selected]

    @staticmethod
    def _text_similarity(text_a: str, text_b: str) -> float:
        """Simple Jaccard similarity between two texts."""
        words_a = set(text_a.lower().split())
        words_b = set(text_b.lower().split())
        if not words_a or not words_b:
            return 0.0
        intersection = words_a & words_b
        union = words_a | words_b
        return len(intersection) / len(union)