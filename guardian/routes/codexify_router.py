from fastapi import APIRouter, HTTPException
from typing import Any, List, Optional
from pydantic import BaseModel

# Local imports – these modules are created in this task
from guardian.embedding_engine import get_embedding
from guardian.vector_store import VectorStore

router = APIRouter()

# ----------------------------------------------------------------------
# Request models
# ----------------------------------------------------------------------
class CodexifyRequest(BaseModel):
    """Payload for the original /codexify endpoint."""
    text: str
    tags: Optional[List[str]] = None


class EmbedRequest(BaseModel):
    """Payload for the /embed endpoint."""
    text: str


class SearchRequest(BaseModel):
    """Payload for the /search endpoint."""
    query: str


# ----------------------------------------------------------------------
# Global in‑memory vector store (FAISS based)
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
    in‑memory vector store.
    """
    try:
        embedding = get_embedding(payload.text)
        # Store the embedding together with the original text as metadata
        vector_store.add(text=payload.text, embedding=embedding, metadata={})
        return {"embedding": embedding, "message": "Embedding stored successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search")
async def search_endpoint(payload: SearchRequest) -> dict[str, Any]:
    """
    Search the vector store for the most similar embeddings to the
    query text. Returns the top 5 results with similarity scores.
    """
    try:
        query_emb = get_embedding(payload.query)
        results = vector_store.search(query_emb, top_k=5)
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
