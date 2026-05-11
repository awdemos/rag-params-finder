"""Tests for prompt endpoints."""

from unittest.mock import MagicMock

from fastapi.testclient import TestClient


class TestIndexPrompts:
    def test_index_prompts(
        self,
        client: TestClient,
        mock_collection: MagicMock,
        sample_prompt_document: dict,
    ) -> None:
        """Batch index prompt documents and verify response."""
        payload = {
            "library_id": "my-library",
            "documents": [sample_prompt_document],
            "embedding_model": "all-MiniLM-L6-v2",
        }

        response = client.post("/prompts/index", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "indexed"
        assert data["library_id"] == "my-library"
        assert data["documents_indexed"] == 1
        mock_collection.insert_many.assert_called_once()
        inserted = mock_collection.insert_many.call_args[0][0]
        assert len(inserted) == 1
        assert inserted[0]["chunk_id"] == "prompt-1"
        assert inserted[0]["session_id"] == "my-library"
        assert inserted[0]["text"] == "Summarize the following text"
        assert inserted[0]["source"] == "prompt"
        assert inserted[0]["title"] == "Summarizer"
        assert inserted[0]["description"] == "A prompt for summarization"
        assert inserted[0]["tags"] == ["nlp", "summarization"]
        assert inserted[0]["file_path"] == "/prompts/summarize.md"
        assert inserted[0]["embedding"] == [0.1, 0.2, 0.3]

    def test_index_prompts_empty(self, client: TestClient) -> None:
        """400 error for empty documents."""
        payload = {
            "library_id": "my-library",
            "documents": [],
            "embedding_model": "all-MiniLM-L6-v2",
        }

        response = client.post("/prompts/index", json=payload)

        assert response.status_code == 400
        assert response.json()["detail"] == "No documents provided"


class TestQueryPrompts:
    def test_query_prompts(
        self,
        client: TestClient,
        mock_collection: MagicMock,
        mock_embed_query: MagicMock,
    ) -> None:
        """Semantic search prompts and verify response structure."""
        mock_collection.aggregate.return_value = [
            {
                "chunk_id": "prompt-1",
                "session_id": "my-library",
                "text": "Summarize the following text",
                "title": "Summarizer",
                "description": "A prompt for summarization",
                "tags": ["nlp", "summarization"],
                "file_path": "/prompts/summarize.md",
                "metadata": {"author": "test"},
                "score": 0.92,
            }
        ]

        payload = {
            "query": "summarize",
            "embedding_model": "all-MiniLM-L6-v2",
            "top_k": 5,
        }

        response = client.post("/prompts/query", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "summarize"
        assert data["total"] == 1
        assert len(data["results"]) == 1
        result = data["results"][0]
        assert result["prompt_id"] == "prompt-1"
        assert result["text"] == "Summarize the following text"
        assert result["title"] == "Summarizer"
        assert result["description"] == "A prompt for summarization"
        assert result["tags"] == ["nlp", "summarization"]
        assert result["file_path"] == "/prompts/summarize.md"
        assert result["score"] == 0.92
        assert result["rank"] == 1
        mock_embed_query.assert_called_once()
        mock_collection.aggregate.assert_called_once()

    def test_query_prompts_with_library_filter(
        self,
        client: TestClient,
        mock_collection: MagicMock,
    ) -> None:
        """Test library_id filter is passed to aggregate."""
        mock_collection.aggregate.return_value = []

        payload = {
            "query": "summarize",
            "library_id": "my-library",
            "embedding_model": "all-MiniLM-L6-v2",
            "top_k": 5,
        }

        response = client.post("/prompts/query", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["results"] == []

        pipeline = mock_collection.aggregate.call_args[0][0]
        vector_search = pipeline[0]["$vectorSearch"]
        filter_clause = vector_search["filter"]
        assert filter_clause["session_id"] == {"$eq": "my-library"}
        assert filter_clause["source"] == {"$eq": "prompt"}
        assert filter_clause["embedding_model"] == {"$eq": "all-MiniLM-L6-v2"}


class TestListLibraries:
    def test_list_libraries(
        self,
        client: TestClient,
        mock_collection: MagicMock,
    ) -> None:
        """Mock distinct with filter and verify response."""
        mock_collection.distinct.return_value = ["lib-1", "lib-2"]

        response = client.get("/prompts/libraries")

        assert response.status_code == 200
        data = response.json()
        assert data["libraries"] == ["lib-1", "lib-2"]
        mock_collection.distinct.assert_called_once_with("session_id", {"source": "prompt"})


class TestDeleteLibrary:
    def test_delete_library(
        self,
        client: TestClient,
        mock_collection: MagicMock,
    ) -> None:
        """Mock delete_many and verify response."""
        mock_result = MagicMock()
        mock_result.deleted_count = 3
        mock_collection.delete_many.return_value = mock_result

        response = client.delete("/prompts/library/my-library")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "deleted"
        assert data["library_id"] == "my-library"
        assert data["deleted_count"] == 3
        mock_collection.delete_many.assert_called_once_with(
            {"session_id": "my-library", "source": "prompt"}
        )
