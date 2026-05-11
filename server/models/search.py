from pydantic import BaseModel

from server.models.prompts import PromptResult
from server.models.sessions import SessionChunkResult


class CrossLibrarySearchRequest(BaseModel):
    """Request to search across both sessions and prompts simultaneously."""

    query: str
    session_id: str | None = None
    library_id: str | None = None
    top_k_per_source: int = 5
    embedding_model: str = "all-MiniLM-L6-v2"


class CrossLibrarySearchResponse(BaseModel):
    """Response from a cross-library semantic search."""

    query: str
    sessions: list[SessionChunkResult]
    prompts: list[PromptResult]
    total: int
