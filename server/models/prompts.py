from datetime import datetime

from pydantic import BaseModel, Field


class PromptDocument(BaseModel):
    """A single prompt document from a markdown file."""

    prompt_id: str
    text: str
    source: str = "prompt"
    title: str | None = None
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    file_path: str | None = None
    metadata: dict = Field(default_factory=dict)
    embedding_model: str = "all-MiniLM-L6-v2"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PromptIndexRequest(BaseModel):
    """Request to index prompt documents into the vector store."""

    library_id: str = "default"
    documents: list[PromptDocument]
    embedding_model: str = "all-MiniLM-L6-v2"


class PromptQueryRequest(BaseModel):
    """Request to semantically search indexed prompt documents."""

    query: str
    library_id: str | None = None
    tags: list[str] | None = None
    embedding_model: str = "all-MiniLM-L6-v2"
    top_k: int = 10


class PromptResult(BaseModel):
    """A single prompt returned from a query."""

    prompt_id: str
    text: str
    title: str | None = None
    description: str | None = None
    tags: list[str]
    file_path: str | None = None
    metadata: dict
    score: float
    rank: int


class PromptQueryResponse(BaseModel):
    """Response from a prompt semantic search."""

    query: str
    results: list[PromptResult]
    total: int


class PromptLibraryStatus(BaseModel):
    """Status of a prompt library."""

    library_id: str
    document_count: int
    last_indexed: datetime | None = None


class PromptRenderRequest(BaseModel):
    """Request to render a prompt template with variables."""

    template_id: str
    variables: dict[str, str]


class PromptRenderResponse(BaseModel):
    """Response from rendering a prompt template."""

    rendered_text: str
    template_id: str
    variables_used: list[str]
