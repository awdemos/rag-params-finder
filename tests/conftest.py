"""Shared fixtures for rag-params-finder tests."""

from collections.abc import Generator
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def mock_collection() -> MagicMock:
    """Return a mock MongoDB collection."""
    return MagicMock()


@pytest.fixture
def mock_embed_documents() -> Generator[MagicMock, None, None]:
    """Mock embed_documents to return deterministic fake embeddings."""
    with patch("server.api.sessions.embed_documents") as mock_s, patch(
        "server.api.prompts.embed_documents"
    ) as mock_p:

        def _fake_embed(texts: list[str], model: str, provider: str = "local") -> list[list[float]]:
            return [[0.1, 0.2, 0.3] for _ in texts]

        mock_s.side_effect = _fake_embed
        mock_p.side_effect = _fake_embed
        yield mock_s


@pytest.fixture
def mock_embed_query() -> Generator[MagicMock, None, None]:
    """Mock embed_query to return a deterministic fake embedding."""
    with patch("server.api.sessions.embed_query") as mock_s, patch(
        "server.api.prompts.embed_query"
    ) as mock_p:

        def _fake_embed_query(text: str, model: str, provider: str = "local") -> list[float]:
            return [0.1, 0.2, 0.3]

        wrapper = MagicMock()
        wrapper.side_effect = _fake_embed_query
        mock_s.side_effect = wrapper
        mock_p.side_effect = wrapper
        yield wrapper


@pytest.fixture
def client(
    mock_collection: MagicMock,
    mock_embed_documents: MagicMock,
    mock_embed_query: MagicMock,
) -> Generator[TestClient, None, None]:
    """Create a FastAPI TestClient with all external dependencies mocked."""
    with patch("server.db.indexes.ensure_indexes"):
        with patch("server.api.sessions.get_collection", return_value=mock_collection):
            with patch("server.api.prompts.get_collection", return_value=mock_collection):
                from server.main import app

                with TestClient(app) as c:
                    yield c


@pytest.fixture
def sample_session_chunk() -> dict:
    """Return a sample session chunk payload."""
    return {
        "chunk_id": "chunk-1",
        "session_id": "session-abc",
        "text": "Hello world",
        "source": "message",
        "metadata": {"foo": "bar"},
        "embedding_model": "all-MiniLM-L6-v2",
        "created_at": datetime.now(UTC).isoformat(),
    }


@pytest.fixture
def sample_prompt_document() -> dict:
    """Return a sample prompt document payload."""
    return {
        "prompt_id": "prompt-1",
        "text": "Summarize the following text",
        "source": "prompt",
        "title": "Summarizer",
        "description": "A prompt for summarization",
        "tags": ["nlp", "summarization"],
        "file_path": "/prompts/summarize.md",
        "metadata": {"author": "test"},
        "embedding_model": "all-MiniLM-L6-v2",
        "created_at": datetime.now(UTC).isoformat(),
    }
