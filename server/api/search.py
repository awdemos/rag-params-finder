from fastapi import APIRouter

from server.core.embedder import embed_query
from server.core.model_registry import get_index_name
from server.db.atlas import SESSION_CHUNKS_COLLECTION, get_collection
from server.models.prompts import PromptResult
from server.models.search import CrossLibrarySearchRequest, CrossLibrarySearchResponse
from server.models.sessions import SessionChunkResult
from server.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


def _build_session_filter(request: CrossLibrarySearchRequest) -> dict:
    filter_clause: dict = {
        "embedding_model": {"$eq": request.embedding_model},
        "source": {"$ne": "prompt"},
    }
    if request.session_id:
        filter_clause["session_id"] = {"$eq": request.session_id}
    return filter_clause


def _build_prompt_filter(request: CrossLibrarySearchRequest) -> dict:
    filter_clause: dict = {
        "embedding_model": {"$eq": request.embedding_model},
        "source": {"$eq": "prompt"},
    }
    if request.library_id:
        filter_clause["session_id"] = {"$eq": request.library_id}
    return filter_clause


def _run_vector_search(
    query_embedding: list[float],
    index_name: str,
    filter_clause: dict,
    top_k: int,
    projection: dict,
) -> list[dict]:
    collection = get_collection(SESSION_CHUNKS_COLLECTION)
    pipeline = [
        {
            "$vectorSearch": {
                "index": index_name,
                "path": "embedding",
                "queryVector": query_embedding,
                "numCandidates": top_k * 2,
                "limit": top_k,
                "filter": filter_clause,
            }
        },
        {"$project": projection},
    ]
    return list(collection.aggregate(pipeline))


def _to_session_results(docs: list[dict]) -> list[SessionChunkResult]:
    results = []
    for rank, doc in enumerate(docs, start=1):
        results.append(
            SessionChunkResult(
                chunk_id=doc["chunk_id"],
                session_id=doc["session_id"],
                text=doc["text"],
                source=doc["source"],
                metadata=doc.get("metadata", {}),
                score=doc["score"],
                rank=rank,
            )
        )
    return results


def _to_prompt_results(docs: list[dict]) -> list[PromptResult]:
    results = []
    for rank, doc in enumerate(docs, start=1):
        results.append(
            PromptResult(
                prompt_id=doc["chunk_id"],
                text=doc["text"],
                title=doc.get("title"),
                description=doc.get("description"),
                tags=doc.get("tags", []),
                file_path=doc.get("file_path"),
                metadata=doc.get("metadata", {}),
                score=doc["score"],
                rank=rank,
            )
        )
    return results


@router.post("")
async def cross_library_search(request: CrossLibrarySearchRequest):
    """Search across both sessions and prompts simultaneously."""
    logger.info(
        f"Cross-library search: query={request.query!r}, "
        f"session={request.session_id}, library={request.library_id}"
    )

    query_embedding = embed_query(request.query, request.embedding_model, provider="local")
    index_name = get_index_name(request.embedding_model)

    session_filter = _build_session_filter(request)
    prompt_filter = _build_prompt_filter(request)

    session_projection = {
        "_id": 0,
        "chunk_id": 1,
        "session_id": 1,
        "text": 1,
        "source": 1,
        "metadata": 1,
        "score": {"$meta": "vectorSearchScore"},
    }
    prompt_projection = {
        "_id": 0,
        "chunk_id": 1,
        "session_id": 1,
        "text": 1,
        "title": 1,
        "description": 1,
        "tags": 1,
        "file_path": 1,
        "metadata": 1,
        "score": {"$meta": "vectorSearchScore"},
    }

    session_docs = _run_vector_search(
        query_embedding,
        index_name,
        session_filter,
        request.top_k_per_source,
        session_projection,
    )
    prompt_docs = _run_vector_search(
        query_embedding,
        index_name,
        prompt_filter,
        request.top_k_per_source,
        prompt_projection,
    )

    session_results = _to_session_results(session_docs)
    prompt_results = _to_prompt_results(prompt_docs)

    total = len(session_results) + len(prompt_results)
    logger.info(
        f"Cross-library search returned {len(session_results)} sessions, "
        f"{len(prompt_results)} prompts (total={total})"
    )

    return CrossLibrarySearchResponse(
        query=request.query,
        sessions=session_results,
        prompts=prompt_results,
        total=total,
    )
