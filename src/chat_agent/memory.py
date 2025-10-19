"""Conversation memory management for chat sessions."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class Message:
    role: str  # "user" | "assistant" | "system"
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass
class Session:
    session_id: str
    messages: list[Message] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class ConversationMemory:
    """In-memory conversation store with session management."""

    def __init__(self, max_messages_per_session: int = 50) -> None:
        self._sessions: dict[str, Session] = {}
        self.max_messages = max_messages_per_session

    def create_session(self) -> str:
        session_id = f"sess_{uuid.uuid4().hex[:12]}"
        self._sessions[session_id] = Session(session_id=session_id)
        return session_id

    def get_session(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    def add_message(self, session_id: str, role: str, content: str) -> None:
        session = self._sessions.get(session_id)
        if not session:
            session = Session(session_id=session_id)
            self._sessions[session_id] = session

        session.messages.append(Message(role=role, content=content))

        # Trim old messages if exceeding limit
        if len(session.messages) > self.max_messages:
            session.messages = session.messages[-self.max_messages :]

    def get_messages(self, session_id: str) -> list[dict[str, str]]:
        session = self._sessions.get(session_id)
        if not session:
            return []
        return [{"role": m.role, "content": m.content} for m in session.messages]

    def delete_session(self, session_id: str) -> bool:
        return self._sessions.pop(session_id, None) is not None
