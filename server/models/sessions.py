from datetime import datetime

from pydantic import BaseModel, Field


class SessionChunk(BaseModel):
    """A single chunk of an OpenCode session (message, todo, error, decision, file_change)."""

    chunk_id: str
    session_id: str
    text: str
    source: str = Field(
        ..., pattern="^(message|todo|error|decision|file_change|summary)$"
    )
    metadata: dict = Field(default_factory=dict)
    embedding_model: str = "all-MiniLM-L6-v2"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SessionIndexRequest(BaseModel):
    """Request to index session chunks into the vector store."""

    session_id: str
    chunks: list[SessionChunk]
    embedding_model: str = "all-MiniLM-L6-v2"


class SessionQueryRequest(BaseModel):
    """Request to semantically search indexed session chunks."""

    query: str
    session_id: str | None = None
    source: str | None = Field(
        default=None, pattern="^(message|todo|error|decision|file_change|summary)$"
    )
    embedding_model: str = "all-MiniLM-L6-v2"
    top_k: int = 10


class SessionChunkResult(BaseModel):
    """A single chunk returned from a session query."""

    chunk_id: str
    session_id: str
    text: str
    source: str
    metadata: dict
    score: float
    rank: int


class SessionQueryResponse(BaseModel):
    """Response from a session semantic search."""

    query: str
    results: list[SessionChunkResult]
    total: int


class SessionChunkIndexResponse(BaseModel):
    """Response from indexing a single session chunk."""

    status: str
    chunk_id: str
    session_id: str


class WebSocketMessage(BaseModel):
    """Incoming message on the session WebSocket."""

    action: str = Field(..., pattern="^(index|query)$")
    chunk: SessionChunk | None = None
    query: str | None = None
    top_k: int = 5


class WebSocketResponse(BaseModel):
    """Outgoing message on the session WebSocket."""

    status: str | None = None
    chunk_id: str | None = None
    results: list[SessionChunkResult] | None = None
    error: str | None = None
