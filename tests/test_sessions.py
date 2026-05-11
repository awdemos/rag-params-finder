"""Tests for session endpoints."""

from unittest.mock import MagicMock

from fastapi.testclient import TestClient


class TestIndexSessions:
    def test_index_sessions(
        self,
        client: TestClient,
        mock_collection: MagicMock,
        sample_session_chunk: dict,
    ) -> None:
        """Batch index session chunks and verify response."""
        payload = {
            "session_id": "session-abc",
            "chunks": [sample_session_chunk],
            "embedding_model": "all-MiniLM-L6-v2",
        }

        response = client.post("/sessions/index", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "indexed"
        assert data["session_id"] == "session-abc"
        assert data["chunks_indexed"] == 1
        mock_collection.insert_many.assert_called_once()
        inserted = mock_collection.insert_many.call_args[0][0]
        assert len(inserted) == 1
        assert inserted[0]["chunk_id"] == "chunk-1"
        assert inserted[0]["session_id"] == "session-abc"
        assert inserted[0]["text"] == "Hello world"
        assert inserted[0]["source"] == "message"
        assert inserted[0]["embedding"] == [0.1, 0.2, 0.3]

    def test_index_sessions_empty(self, client: TestClient) -> None:
        """400 error for empty chunks."""
        payload = {
            "session_id": "session-abc",
            "chunks": [],
            "embedding_model": "all-MiniLM-L6-v2",
        }

        response = client.post("/sessions/index", json=payload)

        assert response.status_code == 400
        assert response.json()["detail"] == "No chunks provided"


class TestQuerySessions:
    def test_query_sessions(
        self,
        client: TestClient,
        mock_collection: MagicMock,
        mock_embed_query: MagicMock,
    ) -> None:
        """Semantic search sessions and verify response structure."""
        mock_collection.aggregate.return_value = [
            {
                "chunk_id": "chunk-1",
                "session_id": "session-abc",
                "text": "Hello world",
                "source": "message",
                "metadata": {"foo": "bar"},
                "score": 0.95,
            }
        ]

        payload = {
            "query": "hello",
            "embedding_model": "all-MiniLM-L6-v2",
            "top_k": 5,
        }

        response = client.post("/sessions/query", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "hello"
        assert data["total"] == 1
        assert len(data["results"]) == 1
        result = data["results"][0]
        assert result["chunk_id"] == "chunk-1"
        assert result["session_id"] == "session-abc"
        assert result["text"] == "Hello world"
        assert result["source"] == "message"
        assert result["score"] == 0.95
        assert result["rank"] == 1
        mock_embed_query.assert_called_once()
        mock_collection.aggregate.assert_called_once()

    def test_query_sessions_with_filter(
        self,
        client: TestClient,
        mock_collection: MagicMock,
    ) -> None:
        """Test session_id and source filters are passed to aggregate."""
        mock_collection.aggregate.return_value = []

        payload = {
            "query": "hello",
            "session_id": "session-abc",
            "source": "message",
            "embedding_model": "all-MiniLM-L6-v2",
            "top_k": 5,
        }

        response = client.post("/sessions/query", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["results"] == []

        pipeline = mock_collection.aggregate.call_args[0][0]
        vector_search = pipeline[0]["$vectorSearch"]
        filter_clause = vector_search["filter"]
        assert filter_clause["session_id"] == {"$eq": "session-abc"}
        assert filter_clause["source"] == {"$eq": "message"}
        assert filter_clause["embedding_model"] == {"$eq": "all-MiniLM-L6-v2"}


class TestListIndexedSessions:
    def test_list_indexed_sessions(
        self,
        client: TestClient,
        mock_collection: MagicMock,
    ) -> None:
        """Mock collection.distinct and verify response."""
        mock_collection.distinct.return_value = ["session-abc", "session-def"]

        response = client.get("/sessions/indexed")

        assert response.status_code == 200
        data = response.json()
        assert data["sessions"] == ["session-abc", "session-def"]
        mock_collection.distinct.assert_called_once_with("session_id")
