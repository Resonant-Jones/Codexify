"""
Health Routes
~~~~~~~~~~~~~

Health check endpoints for monitoring subsystem status.
Mounted without a prefix to preserve public paths like /health/chat.
"""

import logging
from uuid import uuid4

from fastapi import APIRouter, Depends, Response

from guardian.core import metrics
from guardian.core.dependencies import DB_BACKEND, get_database_dsn

logger = logging.getLogger(__name__)

# Create unprefixed router to preserve /health/chat path
router = APIRouter(tags=["Health"])


@router.get("/health")
def health():
    """Base health check endpoint for system-level monitoring."""
    return {"status": "ok"}


@router.get("/health/chat")
def health_chat():
    """Get health status of chat subsystem."""
    # Import from core dependencies module
    from guardian.core.dependencies import DB_BACKEND, chatlog_db

    try:
        threads = chatlog_db.count_chat_threads()
        messages = chatlog_db.count_all_messages()
    except Exception as _e:
        logger.warning("[health/chat] check failed: %s", _e)
        threads = 0
        messages = 0
    return {
        "ok": True,
        "threads": threads,
        "messages": messages,
        "backend": DB_BACKEND,
    }


@router.get("/health/memory")
def health_memory():
    """
    Get health status of memory subsystem.

    Returns a simple JSON payload with ok flag and per-silo counts.
    """
    try:
        # Import lightweight dependencies lazily to avoid circulars
        from guardian.core.dependencies import chatlog_db
        from guardian.routes.memory import EPHEMERAL_MEMORY

        ephemeral_count = len(EPHEMERAL_MEMORY)
        midterm = chatlog_db.count_memories("midterm") if chatlog_db else 0
        longterm = chatlog_db.count_memories("longterm") if chatlog_db else 0
    except Exception as _e:
        logger.warning("[health/memory] check failed: %s", _e)
        ephemeral_count = midterm = longterm = 0

    return {
        "ok": True,
        "counts": {
            "ephemeral": ephemeral_count,
            "midterm": midterm,
            "longterm": longterm,
        },
    }


@router.get("/health/vector")
def health_vector():
    """Get health status of the vector store (add + search probe)."""
    try:
        import os
        import tempfile

        from backend.rag.embedder import Embedder
        from guardian.core import dependencies
        from guardian.vector.store import VectorStore

        vector_store = dependencies._vector_store
        backend = (
            getattr(vector_store.embedder, "store", None)
            if vector_store is not None
            else None
        )
        if not backend:
            backend = (
                os.getenv("CODEXIFY_VECTOR_STORE", "faiss").strip().lower()
            )

        probe_id = uuid4().hex
        probe_text = f"health_check_{probe_id}"
        probe_meta = {"health_check": True, "id": probe_id}

        if backend == "chroma":
            source = "probe"
            with tempfile.TemporaryDirectory() as tmp_dir:
                embedder = Embedder(
                    store="chroma",
                    chroma_path=tmp_dir,
                    collection=f"health_{probe_id}",
                )
                result = embedder.embed_and_index(
                    [probe_text], metadatas=[probe_meta], ids_prefix="health"
                )
                added = int(result.get("count", 0))
                matches = embedder.search(probe_text, k=1)
        else:
            source = "shared"
            if vector_store is None:
                vector_store = VectorStore()
                source = "local"
            added = vector_store.add_texts(
                [{"text": probe_text, "meta": probe_meta}]
            )
            matches = vector_store.search(probe_text, k=1)
        ok = bool(matches)

        return {
            "ok": ok,
            "status": "ok" if ok else "error",
            "backend": backend,
            "source": source,
            "added": added,
            "matches": len(matches),
        }
    except Exception as exc:
        logger.warning("[health/vector] check failed: %s", exc)
        return {
            "ok": False,
            "status": "error",
            "backend": "unknown",
            "error": str(exc),
        }


@router.get("/metrics")
def prometheus_metrics():
    """
    Expose system metrics in Prometheus format.

    This endpoint is intentionally unauthenticated to allow Prometheus
    scraping without API key requirements.
    """
    output = metrics.generate_latest(metrics.registry)
    return Response(content=output, media_type=metrics.CONTENT_TYPE_LATEST)


@router.get("/health/deps")
def health_deps(format: str = "json"):
    """
    Diagnostic endpoint for dependency configuration.

    Supports hybrid output:
    - format=json (default): Returns JSON with masked configuration details
    - format=prometheus: Returns Prometheus-compatible metrics
    """
    # Import from core dependencies module
    from guardian.core.dependencies import API_KEY, _mask_dsn

    if format == "prometheus":
        return Response(
            content=metrics.generate_latest(metrics.registry),
            media_type=metrics.CONTENT_TYPE_LATEST,
        )

    # JSON format (default)
    masked_api_key = (
        (API_KEY[:4] + "…" + API_KEY[-4:])
        if API_KEY and len(API_KEY) > 8
        else API_KEY
    )

    return {
        "status": "ok",
        "db_backend": DB_BACKEND,
        "pg_dsn_masked": _mask_dsn(get_database_dsn())
        if get_database_dsn()
        else None,
        "api_key_masked": masked_api_key,
    }
