"""RAG Pipeline FastAPI service."""

from __future__ import annotations

from pathlib import Path

import structlog
from fastapi import FastAPI, HTTPException, UploadFile
from openai import AsyncAzureOpenAI
from opentelemetry import trace
from pydantic import BaseModel, Field

from src.rag_pipeline.config import get_rag_settings
from src.rag_pipeline.embedder import AzureOpenAIEmbedder
from src.rag_pipeline.ingest import IngestPipeline
from src.rag_pipeline.prompts import RAG_NO_CONTEXT_RESPONSE, RAG_SYSTEM_PROMPT, RAG_USER_TEMPLATE
from src.rag_pipeline.retriever import HybridRetriever
from src.rag_pipeline.vector_store import QdrantVectorStore

logger = structlog.get_logger(__name__)
tracer = trace.get_tracer(__name__)
app = FastAPI(title="EcoSupplyAI RAG Pipeline", version="0.1.0")


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2048)
    top_k: int = Field(default=5, ge=1, le=20)
    filters: dict | None = None


class SourceReference(BaseModel):
    text: str
    source_file: str
    relevance_score: float


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceReference]
    token_usage: dict[str, int]


@app.post("/rag/query", response_model=QueryResponse)
async def query_rag(request: QueryRequest) -> QueryResponse:
    settings = get_rag_settings()

    with tracer.start_as_current_span("rag.query") as span:
        span.set_attribute("rag.question_length", len(request.question))

        # Embed query
        embedder = AzureOpenAIEmbedder(settings)
        query_embedding = await embedder.embed(request.question)

        # Retrieve relevant chunks
        store = QdrantVectorStore(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
        retriever = HybridRetriever(
            vector_store=store,
            collection=settings.COLLECTION_NAME,
            top_k=request.top_k,
            similarity_threshold=settings.SIMILARITY_THRESHOLD,
        )
        retrieval = await retriever.retrieve(query_embedding, request.question, filters=request.filters)

        if not retrieval.chunks:
            return QueryResponse(answer=RAG_NO_CONTEXT_RESPONSE, sources=[], token_usage={})

        # Build context from retrieved chunks
        context = "\n\n---\n\n".join(
            f"[Source: {c.metadata.get('source_file', 'unknown')}]\n{c.text}"
            for c in retrieval.chunks
        )

        # Generate answer with LLM
        llm = AsyncAzureOpenAI(
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION,
        )
        user_prompt = RAG_USER_TEMPLATE.format(context=context, question=request.question)
        completion = await llm.chat.completions.create(
            model=settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT.replace("embedding", "gpt-4o"),
            messages=[
                {"role": "system", "content": RAG_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=1024,
        )

        answer = completion.choices[0].message.content or ""
        usage = {
            "prompt_tokens": completion.usage.prompt_tokens if completion.usage else 0,
            "completion_tokens": completion.usage.completion_tokens if completion.usage else 0,
        }

        sources = [
            SourceReference(
                text=c.text[:200],
                source_file=c.metadata.get("source_file", "unknown"),
                relevance_score=round(c.score, 3),
            )
            for c in retrieval.chunks
        ]

        return QueryResponse(answer=answer, sources=sources, token_usage=usage)


@app.post("/rag/ingest")
async def ingest_documents(source_dir: str = "data/sample/documents") -> dict:
    pipeline = IngestPipeline()
    return await pipeline.ingest_directory(source_dir)


@app.get("/rag/health")
async def health() -> dict:
    return {"status": "healthy", "service": "rag-pipeline"}


@app.get("/rag/ready")
async def ready() -> dict:
    return {"status": "ready"}