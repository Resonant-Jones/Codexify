from typing import Any, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# Use the unified VectorStore
from guardian.vector.store import VectorStore

router = APIRouter()


# ----------------------------------------------------------------------
# Request models
# ----------------------------------------------------------------------
class CodexifyRequest(BaseModel):
    """Payload for the original /codexify endpoint."""

    text: str
    tags: Optional[List[str]] = None


class EmbedRequest(BaseModel):
    """Payload for the /embed endpoint.

    Optionally accepts tags/metadata which are stored alongside the text.
    """

    text: str
    tags: Optional[List[str]] = None
    metadata: Optional[dict[str, Any]] = None


class SearchRequest(BaseModel):
    """Payload for the /search endpoint."""

    query: str


# ----------------------------------------------------------------------
# Global unified vector store
# ----------------------------------------------------------------------
vector_store = VectorStore()


# ----------------------------------------------------------------------
# Endpoints
# ----------------------------------------------------------------------
@router.post("/codexify")
async def codexify_endpoint(payload: CodexifyRequest) -> dict[str, Any]:
    """
    Original Codexify endpoint – unchanged apart from type hints.
    """
    try:
        return {
            "message": "Codexify processed successfully",
            "text": payload.text,
            "tags": payload.tags,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/embed")
async def embed_endpoint(payload: EmbedRequest) -> dict[str, Any]:
    """
    Generate an embedding for the provided text and store it in the
    unified vector store.
    """
    try:
        # Compose metadata: merge provided metadata with tags
        md: dict[str, Any] = {}
        if payload.metadata:
            md.update(payload.metadata)
        if payload.tags:
            md["tags"] = list(payload.tags)
            
        # VectorStore handles embedding internally now
        vector_store.add_texts([{"text": payload.text, "meta": md}])
        
        return {"message": "Embedding stored successfully", "metadata": md}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search")
async def search_endpoint(payload: SearchRequest) -> dict[str, Any]:
    """
    Search the vector store for the most similar embeddings to the
    query text. Returns the top 5 results with similarity scores.
    """
    try:
        results = vector_store.search(payload.query, k=5)
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
