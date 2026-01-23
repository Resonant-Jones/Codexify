"""
Embeddings endpoint for frontend usage.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from guardian.core.dependencies import require_api_key
from guardian.embedding_engine import get_embedding

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
    provider = body.embedder or "dummy"
    vectors = [get_embedding(text) for text in body.texts]
    return EmbeddingsResponse(
        provider=provider, model=body.model, vectors=vectors
    )
