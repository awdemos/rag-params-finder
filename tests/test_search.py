"""Tests for cross-library search across sessions and prompts."""

from unittest.mock import MagicMock

from fastapi.testclient import TestClient


class TestCrossLibrarySearch:
    def test_cross_library_search(
        self,
        client: TestClient,
        mock_collection: MagicMock,
    ) -> None:
        """Query both sessions and prompts with the same embedding and verify aggregation."""
        # Mock session query results
        mock_collection.aggregate.side_effect = [
            # Sessions aggregate response
            [
                {
                    "chunk_id": "chunk-1",
                    "session_id": "session-abc",
                    "text": "Hello from session",
                    "source": "message",
                    "metadata": {},
                    "score": 0.95,
                }
            ],
            # Prompts aggregate response
            [
                {
                    "chunk_id": "prompt-1",
                    "session_id": "lib-1",
                    "text": "Hello from prompt",
                    "title": "Greeting",
                    "description": None,
                    "tags": [],
                    "file_path": None,
                    "metadata": {},
                    "score": 0.88,
                }
            ],
        ]

        session_payload = {
            "query": "hello",
            "embedding_model": "all-MiniLM-L6-v2",
            "top_k": 5,
        }
        prompt_payload = {
            "query": "hello",
            "embedding_model": "all-MiniLM-L6-v2",
            "top_k": 5,
        }

        session_response = client.post("/sessions/query", json=session_payload)
        prompt_response = client.post("/prompts/query", json=prompt_payload)

        assert session_response.status_code == 200
        assert prompt_response.status_code == 200

        session_data = session_response.json()
        prompt_data = prompt_response.json()

        # Verify session results
        assert session_data["query"] == "hello"
        assert session_data["total"] == 1
        assert session_data["results"][0]["chunk_id"] == "chunk-1"
        assert session_data["results"][0]["source"] == "message"
        assert session_data["results"][0]["score"] == 0.95

        # Verify prompt results
        assert prompt_data["query"] == "hello"
        assert prompt_data["total"] == 1
        assert prompt_data["results"][0]["prompt_id"] == "prompt-1"
        assert prompt_data["results"][0]["title"] == "Greeting"
        assert prompt_data["results"][0]["score"] == 0.88

        # Both endpoints were called (aggregate called twice)
        assert mock_collection.aggregate.call_count == 2
