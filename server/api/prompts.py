from string import Template

from fastapi import APIRouter, HTTPException

from server.core.embedder import embed_documents, embed_query
from server.core.model_registry import get_index_name
from server.db.atlas import SESSION_CHUNKS_COLLECTION, get_collection
from server.models.prompts import (
    PromptIndexRequest,
    PromptQueryRequest,
    PromptQueryResponse,
    PromptRenderRequest,
    PromptRenderResponse,
    PromptResult,
)
from server.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.post("/index")
async def index_prompts(request: PromptIndexRequest):
    """Index prompt documents into the vector store."""
    logger.info(
        f"Indexing {len(request.documents)} prompts for library={request.library_id}"
    )

    if not request.documents:
        raise HTTPException(status_code=400, detail="No documents provided")

    texts = [doc.text for doc in request.documents]
    embeddings = embed_documents(texts, request.embedding_model, provider="local")

    docs = []
    for doc, embedding in zip(request.documents, embeddings):
        docs.append(
            {
                "chunk_id": doc.prompt_id,
                "session_id": request.library_id,
                "text": doc.text,
                "source": "prompt",
                "title": doc.title,
                "description": doc.description,
                "tags": doc.tags,
                "file_path": doc.file_path,
                "metadata": doc.metadata,
                "embedding_model": doc.embedding_model,
                "embedding": embedding,
                "created_at": doc.created_at,
            }
        )

    collection = get_collection(SESSION_CHUNKS_COLLECTION)
    collection.insert_many(docs)

    logger.info(f"Indexed {len(docs)} prompts for library={request.library_id}")
    return {
        "status": "indexed",
        "library_id": request.library_id,
        "documents_indexed": len(docs),
    }


@router.get("/libraries")
async def list_libraries():
    """List all prompt library IDs that have documents in the vector store."""
    collection = get_collection(SESSION_CHUNKS_COLLECTION)
    library_ids = collection.distinct("session_id", {"source": "prompt"})
    return {"libraries": library_ids}


@router.post("/query")
async def query_prompts(request: PromptQueryRequest):
    """Semantically search indexed prompt documents."""
    logger.info(
        f"Querying prompts: query={request.query!r}, library={request.library_id}"
    )

    query_embedding = embed_query(request.query, request.embedding_model, provider="local")
    index_name = get_index_name(request.embedding_model)

    collection = get_collection(SESSION_CHUNKS_COLLECTION)

    filter_clause: dict = {
        "embedding_model": {"$eq": request.embedding_model},
        "source": {"$eq": "prompt"},
    }
    if request.library_id:
        filter_clause["session_id"] = {"$eq": request.library_id}
    if request.tags:
        filter_clause["tags"] = {"$in": request.tags}

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
                "title": 1,
                "description": 1,
                "tags": 1,
                "file_path": 1,
                "metadata": 1,
                "score": {"$meta": "vectorSearchScore"},
            }
        },
    ]

    results = list(collection.aggregate(pipeline))
    logger.info(f"Prompt query returned {len(results)} results")

    prompt_results = []
    for rank, doc in enumerate(results, start=1):
        prompt_results.append(
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

    return PromptQueryResponse(
        query=request.query,
        results=prompt_results,
        total=len(prompt_results),
    )


@router.post("/render")
async def render_prompt(request: PromptRenderRequest):
    """Render a prompt template with variable substitution."""
    logger.info(f"Rendering prompt template: {request.template_id}")

    collection = get_collection(SESSION_CHUNKS_COLLECTION)
    doc = collection.find_one(
        {"chunk_id": request.template_id, "source": "prompt"},
        {"_id": 0, "text": 1},
    )

    if not doc:
        raise HTTPException(status_code=404, detail="Template not found")

    template = Template(doc["text"])
    rendered_text = template.safe_substitute(request.variables)
    variables_used = list(request.variables.keys())

    logger.info(
        f"Rendered prompt template: {request.template_id} "
        f"with {len(variables_used)} variables"
    )

    return PromptRenderResponse(
        rendered_text=rendered_text,
        template_id=request.template_id,
        variables_used=variables_used,
    )


@router.delete("/library/{library_id}")
async def delete_library(library_id: str):
    """Delete all prompts for a given library."""
    logger.info(f"Deleting prompt library: {library_id}")
    collection = get_collection(SESSION_CHUNKS_COLLECTION)
    result = collection.delete_many({"session_id": library_id, "source": "prompt"})
    logger.info(f"Deleted {result.deleted_count} prompts from library={library_id}")
    return {
        "status": "deleted",
        "library_id": library_id,
        "deleted_count": result.deleted_count,
    }
