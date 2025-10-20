"""Chat Agent FastAPI service."""

from __future__ import annotations

import structlog
from fastapi import FastAPI, HTTPException
from langchain_core.messages import HumanMessage
from opentelemetry import trace
from pydantic import BaseModel, Field

from src.chat_agent.graph import build_agent_graph
from src.chat_agent.memory import ConversationMemory

logger = structlog.get_logger(__name__)
tracer = trace.get_tracer(__name__)
app = FastAPI(title="EcoSupplyAI Chat Agent", version="0.1.0")

memory = ConversationMemory()
agent_graph = build_agent_graph()


class MessageRequest(BaseModel):
    message: str = Field(..., min_length=1)
    session_id: str | None = None
    user_id: str | None = None


class MessageResponse(BaseModel):
    reply: str
    session_id: str
    sources: list[dict] = []
    token_usage: dict[str, int] = {}


@app.post("/chat/message", response_model=MessageResponse)
async def process_message(request: MessageRequest) -> MessageResponse:
    with tracer.start_as_current_span("chat.process_message"):
        # Get or create session
        session_id = request.session_id or memory.create_session()
        memory.add_message(session_id, "user", request.message)

        # Run through the agent graph
        initial_state = {
            "messages": [HumanMessage(content=request.message)],
            "plan": [],
            "current_step": 0,
            "results": {},
            "final_answer": "",
        }

        result = await agent_graph.ainvoke(initial_state)

        reply = result.get("final_answer", "I was unable to process your request.")
        memory.add_message(session_id, "assistant", reply)

        sources = []
        rag_result = result.get("results", {}).get("rag", {})
        if isinstance(rag_result, dict):
            sources = rag_result.get("sources", [])

        return MessageResponse(
            reply=reply,
            session_id=session_id,
            sources=sources,
        )


@app.get("/chat/sessions/{session_id}")
async def get_session(session_id: str) -> dict:
    session = memory.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "session_id": session.session_id,
        "messages": memory.get_messages(session_id),
        "created_at": session.created_at,
    }


@app.delete("/chat/sessions/{session_id}")
async def delete_session(session_id: str) -> dict:
    deleted = memory.delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "deleted"}


@app.get("/chat/health")
async def health() -> dict:
    return {"status": "healthy", "service": "chat-agent"}


@app.get("/chat/ready")
async def ready() -> dict:
    return {"status": "ready"}
