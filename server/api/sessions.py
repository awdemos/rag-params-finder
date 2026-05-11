from fastapi import APIRouter, HTTPException, WebSocket

from server.core.embedder import embed_documents, embed_query
from server.core.model_registry import get_index_name
from server.db.atlas import SESSION_CHUNKS_COLLECTION, get_collection
from server.models.sessions import (
    SessionChunk,
    SessionChunkIndexResponse,
    SessionChunkResult,
    SessionIndexRequest,
    SessionQueryRequest,
    SessionQueryResponse,
    WebSocketMessage,
    WebSocketResponse,
)
from server.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.post("/index")
async def index_session(request: SessionIndexRequest):
    """Index session chunks into the vector store."""
    logger.info(
        f"Indexing {len(request.chunks)} chunks for session={request.session_id}"
    )

    if not request.chunks:
        raise HTTPException(status_code=400, detail="No chunks provided")

    texts = [chunk.text for chunk in request.chunks]
    embeddings = embed_documents(texts, request.embedding_model, provider="local")

    docs = []
    for chunk, embedding in zip(request.chunks, embeddings):
        docs.append(
            {
                "chunk_id": chunk.chunk_id,
                "session_id": chunk.session_id,
                "text": chunk.text,
                "source": chunk.source,
                "metadata": chunk.metadata,
                "embedding_model": chunk.embedding_model,
                "embedding": embedding,
                "created_at": chunk.created_at,
            }
        )

    collection = get_collection(SESSION_CHUNKS_COLLECTION)
    collection.insert_many(docs)

    logger.info(f"Indexed {len(docs)} chunks for session={request.session_id}")
    return {
        "status": "indexed",
        "session_id": request.session_id,
        "chunks_indexed": len(docs),
    }


@router.get("/indexed")
async def list_indexed_sessions():
    """List all session_ids that have chunks in the vector store."""
    collection = get_collection(SESSION_CHUNKS_COLLECTION)
    session_ids = collection.distinct("session_id")
    return {"sessions": session_ids}


@router.post("/query")
async def query_sessions(request: SessionQueryRequest):
    """Semantically search indexed session chunks."""
    logger.info(
        f"Querying sessions: query={request.query!r}, "
        f"session={request.session_id}, source={request.source}"
    )

    query_embedding = embed_query(request.query, request.embedding_model, provider="local")
    index_name = get_index_name(request.embedding_model)

    collection = get_collection(SESSION_CHUNKS_COLLECTION)

    filter_clause: dict = {
        "embedding_model": {"$eq": request.embedding_model},
    }
    if request.session_id:
        filter_clause["session_id"] = {"$eq": request.session_id}
    if request.source:
        filter_clause["source"] = {"$eq": request.source}

    pipeline = [
        {
            "$vectorSearch": {
                "index": index_name,
                "path": "embedding",
                "queryVector": query_embedding,
                "numCandidates": request.top_k * 2,
                "limit": request.top_k,
                "filter": filter_clause,
            }
        },
        {
            "$project": {
                "_id": 0,
                "chunk_id": 1,
                "session_id": 1,
                "text": 1,
                "source": 1,
                "metadata": 1,
                "score": {"$meta": "vectorSearchScore"},
            }
        },
    ]

    results = list(collection.aggregate(pipeline))
    logger.info(f"Session query returned {len(results)} results")

    chunk_results = []
    for rank, doc in enumerate(results, start=1):
        chunk_results.append(
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

    return SessionQueryResponse(
        query=request.query,
        results=chunk_results,
        total=len(chunk_results),
    )


def _build_vector_search_pipeline(
    query_embedding: list[float],
    embedding_model: str,
    top_k: int,
    session_id: str | None = None,
    source: str | None = None,
) -> list[dict]:
    """Build the MongoDB vector search pipeline for session chunks."""
    index_name = get_index_name(embedding_model)

    filter_clause: dict = {
        "embedding_model": {"$eq": embedding_model},
    }
    if session_id:
        filter_clause["session_id"] = {"$eq": session_id}
    if source:
        filter_clause["source"] = {"$eq": source}

    return [
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
        {
            "$project": {
                "_id": 0,
                "chunk_id": 1,
                "session_id": 1,
                "text": 1,
                "source": 1,
                "metadata": 1,
                "score": {"$meta": "vectorSearchScore"},
            }
        },
    ]


def _run_session_query(
    query: str,
    embedding_model: str,
    top_k: int,
    session_id: str | None = None,
    source: str | None = None,
) -> list[SessionChunkResult]:
    """Run a vector search query against indexed session chunks."""
    query_embedding = embed_query(query, embedding_model, provider="local")
    pipeline = _build_vector_search_pipeline(
        query_embedding, embedding_model, top_k, session_id, source
    )

    collection = get_collection(SESSION_CHUNKS_COLLECTION)
    results = list(collection.aggregate(pipeline))

    chunk_results = []
    for rank, doc in enumerate(results, start=1):
        chunk_results.append(
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
    return chunk_results


@router.post("/chunk")
async def index_session_chunk(chunk: SessionChunk) -> SessionChunkIndexResponse:
    """Index a single session chunk into the vector store."""
    logger.info(f"Indexing single chunk: chunk_id={chunk.chunk_id}")

    embedding = embed_query(chunk.text, chunk.embedding_model, provider="local")

    doc = {
        "chunk_id": chunk.chunk_id,
        "session_id": chunk.session_id,
        "text": chunk.text,
        "source": chunk.source,
        "metadata": chunk.metadata,
        "embedding_model": chunk.embedding_model,
        "embedding": embedding,
        "created_at": chunk.created_at,
    }

    collection = get_collection(SESSION_CHUNKS_COLLECTION)
    collection.insert_one(doc)

    logger.info(f"Indexed chunk: chunk_id={chunk.chunk_id}")
    return SessionChunkIndexResponse(
        status="indexed",
        chunk_id=chunk.chunk_id,
        session_id=chunk.session_id,
    )


@router.websocket("/ws")
async def sessions_websocket(websocket: WebSocket):
    """Real-time WebSocket for indexing and querying session chunks."""
    await websocket.accept()
    logger.info("WebSocket connection opened")

    try:
        while True:
            raw_message = await websocket.receive_json()
            try:
                message = WebSocketMessage(**raw_message)
            except Exception as validation_error:
                response = WebSocketResponse(
                    error=f"Invalid message: {validation_error}"
                )
                await websocket.send_json(response.model_dump(exclude_none=True))
                continue

            if message.action == "index":
                if message.chunk is None:
                    response = WebSocketResponse(
                        error="Missing 'chunk' field for index action"
                    )
                    await websocket.send_json(response.model_dump(exclude_none=True))
                    continue

                chunk = message.chunk
                embedding = embed_query(
                    chunk.text, chunk.embedding_model, provider="local"
                )

                doc = {
                    "chunk_id": chunk.chunk_id,
                    "session_id": chunk.session_id,
                    "text": chunk.text,
                    "source": chunk.source,
                    "metadata": chunk.metadata,
                    "embedding_model": chunk.embedding_model,
                    "embedding": embedding,
                    "created_at": chunk.created_at,
                }

                collection = get_collection(SESSION_CHUNKS_COLLECTION)
                collection.insert_one(doc)

                response = WebSocketResponse(
                    status="ok",
                    chunk_id=chunk.chunk_id,
                )
                await websocket.send_json(response.model_dump(exclude_none=True))

            elif message.action == "query":
                if message.query is None:
                    response = WebSocketResponse(
                        error="Missing 'query' field for query action"
                    )
                    await websocket.send_json(response.model_dump(exclude_none=True))
                    continue

                results = _run_session_query(
                    query=message.query,
                    embedding_model=message.chunk.embedding_model
                    if message.chunk
                    else "all-MiniLM-L6-v2",
                    top_k=message.top_k,
                    session_id=message.chunk.session_id if message.chunk else None,
                )

                response = WebSocketResponse(
                    results=results,
                )
                await websocket.send_json(response.model_dump(exclude_none=True))

            else:
                response = WebSocketResponse(
                    error=f"Unknown action: {message.action}"
                )
                await websocket.send_json(response.model_dump(exclude_none=True))

    except Exception as e:
        logger.warning(f"WebSocket error: {e}")
        try:
            response = WebSocketResponse(error=str(e))
            await websocket.send_json(response.model_dump(exclude_none=True))
        except Exception:
            pass
    finally:
        logger.info("WebSocket connection closed")
        try:
            await websocket.close()
        except Exception:
            pass
