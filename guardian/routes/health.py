"""
Health Routes
~~~~~~~~~~~~~

Health check endpoints for monitoring subsystem status.
Mounted without a prefix to preserve public paths like /health/chat.
"""

import logging
from fastapi import APIRouter, Depends, Response
from guardian.core import metrics

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
    # Lazy import to avoid circular dependency - guardian_api imports this module,
    # so we can't import from it at module level. By the time this handler runs,
    # guardian_api is fully loaded and these symbols are available.
    from guardian.guardian_api import chatlog_db, DB_BACKEND

    try:
        threads = chatlog_db.count_chat_threads()
        messages = chatlog_db.count_all_messages()
    except Exception as _e:
        logger.warning("[health/chat] check failed: %s", _e)
        threads = 0
        messages = 0
    return {"ok": True, "threads": threads, "messages": messages, "backend": DB_BACKEND}


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

    Note: This endpoint uses lazy imports to avoid circular dependencies.
    Authentication should be added at the app level if needed.
    """
    # Lazy import to avoid circular dependency
    from guardian.guardian_api import (
        DB_BACKEND,
        PG_DSN,
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
        "pg_dsn_masked": _mask_dsn(PG_DSN) if PG_DSN else None,
        "api_key_masked": masked_api_key,
    }
