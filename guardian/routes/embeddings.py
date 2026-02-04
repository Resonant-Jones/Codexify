"""
Embeddings endpoint for frontend usage.
"""

import logging
import os
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from guardian.core.dependencies import require_api_key
from guardian.embedding_engine import get_embedding

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api",
    tags=["Embeddings"],
    dependencies=[Depends(require_api_key)],
)


class EmbeddingsRequest(BaseModel):
    texts: List[str]
    embedder: Optional[str] = None
    model: Optional[str] = None


class EmbeddingsResponse(BaseModel):
    provider: str
    model: Optional[str]
    vectors: List[List[float]]


@router.post("/embeddings", response_model=EmbeddingsResponse)
def embeddings(body: EmbeddingsRequest) -> EmbeddingsResponse:
    if not body.texts:
        raise HTTPException(status_code=400, detail="texts must not be empty")
    raw_embedder = (body.embedder or "").strip()
    provider = raw_embedder.lower()
    allow_dummy = os.getenv("CODEXIFY_ALLOW_EMBEDDINGS_FALLBACK", "0").lower() in (
        "1",
        "true",
        "yes",
    )
    if not provider:
        env_provider = (
            os.getenv("CODEXIFY_EMBEDDINGS_BACKEND")
            or os.getenv("EMBEDDING_BACKEND")
            or os.getenv("EMBEDDER")
            or ""
        ).strip()
        provider = env_provider.lower()

    if provider in ("", "dummy", "mock"):
        if not raw_embedder and not allow_dummy:
            raise HTTPException(
                status_code=503,
                detail=(
                    "Embeddings backend is not configured. "
                    "Set embedder=dummy explicitly for mock vectors, or configure a real backend."
                ),
            )
        provider = "dummy"

    try:
        vectors = [
            get_embedding(text, embedder=provider) for text in body.texts
        ]
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        from guardian.vector.store import VectorStore

        vector_store = VectorStore()
        items = [
            {"text": text, "meta": {"source": "api/embeddings"}}
            for text in body.texts
        ]
        vector_store.add_texts(items)
    except Exception as exc:
        logger.warning("[embeddings] vector store ingest failed: %s", str(exc))
    return EmbeddingsResponse(
        provider=provider, model=body.model, vectors=vectors
    )
