"""
Health Routes
~~~~~~~~~~~~~

Health check endpoints for monitoring subsystem status.
Mounted without a prefix to preserve public paths like /health/chat.
"""

import logging
from fastapi import APIRouter, Depends, Response
from guardian.core import metrics
from guardian.core.dependencies import get_database_dsn

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
    from guardian.core.dependencies import chatlog_db, DB_BACKEND

    try:
        threads = chatlog_db.count_chat_threads()
        messages = chatlog_db.count_all_messages()
    except Exception as _e:
        logger.warning("[health/chat] check failed: %s", _e)
        threads = 0
        messages = 0
    return {"ok": True, "threads": threads, "messages": messages, "backend": DB_BACKEND}


@router.get("/health/memory")
def health_memory():
    """
    Get health status of memory subsystem.

    Returns a simple JSON payload with ok flag and per-silo counts.
    """
    try:
        # Import lightweight dependencies lazily to avoid circulars
        from guardian.routes.memory import EPHEMERAL_MEMORY
        from guardian.core.dependencies import chatlog_db

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
    from guardian.core.dependencies import (
        DB_BACKEND,
        SQLITE_PATH,
        API_KEY,
        _mask_dsn,
    )

    if format == "prometheus":
        return Response(
            content=metrics.generate_latest(metrics.registry),
            media_type=metrics.CONTENT_TYPE_LATEST,
        )

    # JSON format (default)
    masked_api_key = (API_KEY[:4] + "…" + API_KEY[-4:]) if API_KEY and len(API_KEY) > 8 else API_KEY

    return {
        "status": "ok",
        "db_backend": DB_BACKEND,
        "sqlite_path": SQLITE_PATH,
        "pg_dsn_masked": _mask_dsn(get_database_dsn()) if get_database_dsn() else None,
        "api_key_masked": masked_api_key,
    }
