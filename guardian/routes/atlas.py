"""Atlas routes — bulk chunk listing for the 2D embedding map in webui-basic."""
from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field

from guardian.core.dependencies import (
    RequestUserScope,
    get_request_user_scope,
    get_single_user_id,
    get_vector_store,
    require_api_key,
)
from guardian.vector.store import _normalize_namespace

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/atlas", tags=["Atlas"])


class AtlasChunkMetadata(BaseModel):
    """Pass-through chunk metadata; extra keys are preserved."""

    model_config = ConfigDict(extra="ignore")

    source: Optional[str] = None
    doc_id: Optional[str] = None
    thread_id: Optional[str] = None
    project_id: Optional[str] = None
    namespace: Optional[str] = None
    role: Optional[str] = None
    timestamp: Optional[str] = None
    title: Optional[str] = None
    slug: Optional[str] = None


class AtlasChunk(BaseModel):
    id: str
    text: str
    preview: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    embedding: list[float] = Field(default_factory=list)


class AtlasChunksResponse(BaseModel):
    ok: bool = True
    backend: str
    total: int
    limit: int
    offset: int
    next_offset: Optional[int]
    has_more: bool
    items: list[AtlasChunk]


@router.get("/chunks", response_model=AtlasChunksResponse)
def atlas_list_chunks(
    project_id: Optional[int] = Query(default=None),
    namespace: Optional[str] = Query(default=None),
    limit: int = Query(default=500, ge=1, le=5000),
    offset: int = Query(default=0, ge=0),
    text_preview_chars: int = Query(default=200, ge=0, le=2000),
    include_embeddings: bool = Query(default=True),
    api_key: str = Depends(require_api_key),
    request_user_scope: RequestUserScope = Depends(get_request_user_scope),
) -> AtlasChunksResponse:
    """Return a paginated, user-scoped slice of vector store chunks for Atlas.

    The response includes the raw embedding vectors so the browser can run
    PCA locally. ``user_id`` is *always* derived from the request scope and
    never accepted from the client — this is the only safe way to prevent
    cross-tenant leaks when listing arbitrary chunks.
    """
    del api_key  # satisfied by Depends; kept in signature for parity with sibling routes

    scoped_user_id = request_user_scope.user_id or get_single_user_id()

    effective_namespace = _normalize_namespace(namespace)
    if effective_namespace is None and project_id is not None:
        effective_namespace = f"project:{project_id}"

    where: dict[str, Any] = {"user_id": str(scoped_user_id)}
    if effective_namespace:
        where["namespace"] = effective_namespace

    try:
        vector_store = get_vector_store()
    except Exception as exc:
        logger.warning("Atlas: vector store unavailable: %s", exc)
        return AtlasChunksResponse(
            backend="none",
            total=0,
            limit=limit,
            offset=offset,
            next_offset=None,
            has_more=False,
            items=[],
        )

    embedder = getattr(vector_store, "embedder", None)
    iter_method = getattr(embedder, "iter_chunks_for_atlas", None)
    if iter_method is None:
        # Older embedder without Atlas support — return empty rather than 501
        # so the UI degrades gracefully.
        logger.info("Atlas: embedder lacks iter_chunks_for_atlas; returning empty")
        return AtlasChunksResponse(
            backend=getattr(embedder, "store", "none") or "none",
            total=0,
            limit=limit,
            offset=offset,
            next_offset=None,
            has_more=False,
            items=[],
        )

    result = iter_method(
        where=where,
        limit=limit,
        offset=offset,
        include_embeddings=include_embeddings,
        text_preview_chars=text_preview_chars,
    )

    raw_items = result.get("items") or []
    items = [
        AtlasChunk(
            id=str(item.get("id", "")),
            text=str(item.get("text", "") or ""),
            preview=str(item.get("preview", "") or ""),
            metadata=dict(item.get("metadata") or {}),
            embedding=list(item.get("embedding") or []),
        )
        for item in raw_items
    ]

    total = int(result.get("total") or 0)
    backend = str(result.get("backend") or "none")
    next_offset = (offset + len(items)) if len(items) >= limit and (offset + len(items)) < total else None

    return AtlasChunksResponse(
        backend=backend,
        total=total,
        limit=limit,
        offset=offset,
        next_offset=next_offset,
        has_more=next_offset is not None,
        items=items,
    )