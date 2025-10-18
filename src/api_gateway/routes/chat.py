"""Chat routes — proxy to the Chat Agent service."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends
from opentelemetry import trace
from pydantic import BaseModel, Field

from src.api_gateway.config import Settings, get_settings
from src.api_gateway.middleware.auth import get_current_user
from src.api_gateway.middleware.pii_filter import PIIFilter
from src.api_gateway.middleware.rate_limiter import rate_limit_dependency

import httpx

logger = structlog.get_logger(__name__)
tracer = trace.get_tracer(__name__)
router = APIRouter()


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4096, examples=["What is the ESG score for GreenTex GmbH?"])
    session_id: str | None = Field(default=None, examples=["sess_abc123"])
    stream: bool = Field(default=False)


class Source(BaseModel):
    document: str
    relevance_score: float


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    sources: list[Source] = []
    token_usage: dict[str, int] = {}


@router.post("/chat", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    user: dict = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
    _rate_limit: None = Depends(rate_limit_dependency),
) -> ChatResponse:
    with tracer.start_as_current_span("chat.send_message") as span:
        span.set_attribute("user.id", user["user_id"])

        # PII filter on input
        pii_filter = PIIFilter(enabled=settings.PII_DETECTION_ENABLED)
        sanitized_message = pii_filter.sanitize_input(request.message)

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{settings.CHAT_AGENT_URL}/chat/message",
                json={
                    "message": sanitized_message,
                    "session_id": request.session_id,
                    "user_id": user["user_id"],
                },
            )
            response.raise_for_status()
            data = response.json()

        # PII filter on output
        sanitized_reply = pii_filter.sanitize_output(data.get("reply", ""))

        return ChatResponse(
            reply=sanitized_reply,
            session_id=data.get("session_id", ""),
            sources=data.get("sources", []),
            token_usage=data.get("token_usage", {}),
        )


@router.get("/chat/history/{session_id}")
async def get_chat_history(
    session_id: str,
    user: dict = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{settings.CHAT_AGENT_URL}/chat/sessions/{session_id}")
        response.raise_for_status()
        return response.json()