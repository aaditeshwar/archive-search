"""Pydantic models for messages, chunks, and API request/response."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Message(BaseModel):
    """Stored mailing list message."""

    message_id: str
    thread_id: str
    author: str = ""
    subject: str = ""
    body: str = ""
    date: datetime | None = None
    url: str = ""
    links: list[str] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class LinkedDoc(BaseModel):
    """Fetched linked document (HTML page or PDF)."""

    url: str
    title: str = ""
    content_type: str = "html"  # html | pdf
    raw_text: str = ""
    message_ids: list[str] = Field(default_factory=list)
    fetched_at: datetime = Field(default_factory=datetime.utcnow)
    fetch_failed: bool = False


class IndexChunk(BaseModel):
    """Chunk stored for vector search."""

    chunk_id: str
    text: str
    embedding: list[float]
    source_type: str  # message | linked_page
    message_id: str = ""
    linked_url: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


# --- API models ---


class SearchRequest(BaseModel):
    """Request body for search/query."""

    query: str
    session_id: str | None = None
    top_k: int = 10
    with_answer: bool = False


class SearchChunk(BaseModel):
    """Chunk returned in search results."""

    text: str
    source_type: str
    message_id: str = ""
    message_url: str = ""
    linked_url: str = ""
    title: str = ""
    score: float = 0.0


class SearchResponse(BaseModel):
    """Response from search/query."""

    chunks: list[SearchChunk]
    answer: str | None = None


class SessionCreate(BaseModel):
    """Create session request (optional body)."""

    pass


class SessionMessage(BaseModel):
    """Single message in a conversation."""

    role: str  # user | assistant
    content: str


class SessionResponse(BaseModel):
    """Session with conversation history."""

    session_id: str
    messages: list[SessionMessage] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
