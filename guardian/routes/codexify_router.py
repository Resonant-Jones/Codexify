import re
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from guardian.core.dependencies import get_current_user, require_api_key

# Use the unified VectorStore
from guardian.vector.store import VectorStore

router = APIRouter()

MAX_CODEXIFY_TEXT_CHARS = 12_000
MAX_EMBED_TEXT_CHARS = 20_000
MAX_SEARCH_QUERY_CHARS = 2_048
MAX_TAG_COUNT = 32


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
    namespace: Optional[str] = None


class SearchRequest(BaseModel):
    """Payload for the /search endpoint."""

    query: str
    namespace: Optional[str] = None


# ----------------------------------------------------------------------
# Global unified vector store
# ----------------------------------------------------------------------
vector_store = VectorStore()


def _normalize_user_namespace(user_id: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]", "_", (user_id or "").strip().lower())
    cleaned = cleaned or "local"
    return f"user:{cleaned}"


def _resolve_namespace(requested_namespace: str | None, user_id: str) -> str:
    owner_namespace = _normalize_user_namespace(user_id)
    requested = (requested_namespace or "").strip()
    if not requested:
        return owner_namespace
    if requested != owner_namespace:
        raise HTTPException(
            status_code=403,
            detail="Namespace is restricted to the authenticated user",
        )
    return requested


# ----------------------------------------------------------------------
# Endpoints
# ----------------------------------------------------------------------
@router.post("/codexify")
async def codexify_endpoint(
    payload: CodexifyRequest,
    api_key: str = Depends(require_api_key),
) -> dict[str, Any]:
    """
    Original Codexify endpoint – unchanged apart from type hints.
    """
    _ = api_key
    try:
        if len(payload.text or "") > MAX_CODEXIFY_TEXT_CHARS:
            raise HTTPException(
                status_code=413,
                detail=f"text exceeds {MAX_CODEXIFY_TEXT_CHARS} characters",
            )
        return {
            "message": "Codexify processed successfully",
            "text": payload.text,
            "tags": payload.tags,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/embed")
async def embed_endpoint(
    payload: EmbedRequest,
    current_user: str = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Generate an embedding for the provided text and store it in the
    unified vector store.
    """
    try:
        if len(payload.text or "") > MAX_EMBED_TEXT_CHARS:
            raise HTTPException(
                status_code=413,
                detail=f"text exceeds {MAX_EMBED_TEXT_CHARS} characters",
            )
        if payload.tags and len(payload.tags) > MAX_TAG_COUNT:
            raise HTTPException(
                status_code=413,
                detail=f"tags exceeds maximum of {MAX_TAG_COUNT}",
            )
        namespace = _resolve_namespace(payload.namespace, current_user)

        # Compose metadata: merge provided metadata with tags
        md: dict[str, Any] = {}
        if payload.metadata:
            md.update(payload.metadata)
        if payload.tags:
            md["tags"] = list(payload.tags)
        md["namespace"] = namespace
        md["owner_user_id"] = current_user

        # VectorStore handles embedding internally now
        vector_store.add_texts([{"text": payload.text, "meta": md}])

        return {
            "message": "Embedding stored successfully",
            "metadata": {"namespace": namespace},
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search")
async def search_endpoint(
    payload: SearchRequest,
    current_user: str = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Search the vector store for the most similar embeddings to the
    query text. Returns the top 5 results with similarity scores.
    """
    try:
        if len(payload.query or "") > MAX_SEARCH_QUERY_CHARS:
            raise HTTPException(
                status_code=413,
                detail=f"query exceeds {MAX_SEARCH_QUERY_CHARS} characters",
            )
        namespace = _resolve_namespace(payload.namespace, current_user)
        results = vector_store.search(
            payload.query,
            k=5,
            namespace=namespace,
        )
        return {"results": results}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
