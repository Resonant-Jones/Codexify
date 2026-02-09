"""
Health Routes
~~~~~~~~~~~~~

Health check endpoints for monitoring subsystem status.
Mounted without a prefix to preserve public paths like /health/chat.
"""

import logging
import os
from uuid import uuid4

import requests
from fastapi import APIRouter, Depends, Response

from guardian.core import metrics
from guardian.core.dependencies import DB_BACKEND, get_database_dsn

logger = logging.getLogger(__name__)

# Create unprefixed router to preserve /health/chat path
router = APIRouter(tags=["Health"])


def _resolve_llm_health_endpoints() -> list[str]:
    raw = (os.getenv("VAULTNODE_HEALTH_ENDPOINTS") or "").strip()
    if raw:
        endpoints = [part.strip() for part in raw.split(",") if part.strip()]
    else:
        endpoints = ["/healthz", "/ping", "/health", "/api/tags"]

    normalized: list[str] = []
    for endpoint in endpoints:
        normalized.append(
            endpoint if endpoint.startswith("/") else f"/{endpoint}"
        )
    return normalized


def _probe_local_llm(base_url_v1: str, timeout_seconds: float) -> dict:
    health_base = (
        base_url_v1[:-3] if base_url_v1.endswith("/v1") else base_url_v1
    )
    endpoints = _resolve_llm_health_endpoints()
    last_error = "unreachable"

    for endpoint in endpoints:
        url = f"{health_base}{endpoint}"
        try:
            resp = requests.get(url, timeout=timeout_seconds)
            if 200 <= resp.status_code < 300:
                return {
                    "ok": True,
                    "status": "online",
                    "checked_endpoint": endpoint,
                    "http_status": resp.status_code,
                }
            last_error = f"HTTP {resp.status_code} from {endpoint}"
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"

    return {
        "ok": False,
        "status": "offline",
        "checked_endpoints": endpoints,
        "error": last_error,
    }


@router.get("/health")
def health():
    """Base health check endpoint for system-level monitoring."""
    return {"status": "ok"}


@router.get("/health/llm")
@router.get("/api/health/llm")
def health_llm():
    """
    Report active LLM provider reachability for UI preflight checks.

    Returns:
    - status=online when provider appears reachable/configured
    - status=offline when local provider endpoint is unreachable
    - status=misconfigured when required provider config is invalid
    """
    from guardian.core.ai_router import (
        _default_model_for_provider,
        _resolve_local_base,
    )
    from guardian.core.config import (
        LLMConfigError,
        get_settings,
        validate_llm_config,
    )

    settings = get_settings()
    provider = (settings.LLM_PROVIDER or "local").strip().lower()
    model = _default_model_for_provider(provider, settings)

    payload = {"provider": provider, "model": model}

    try:
        validate_llm_config(settings, provider_override=provider)
    except LLMConfigError as exc:
        payload.update(
            {"ok": False, "status": "misconfigured", "error": str(exc)}
        )
        return payload

    if provider == "local":
        timeout = float(os.getenv("HEALTH_LLM_REQUEST_TIMEOUT_SECONDS", "2.5"))
        try:
            local_base = _resolve_local_base(settings)
        except Exception as exc:
            detail = getattr(exc, "detail", str(exc))
            payload.update(
                {"ok": False, "status": "misconfigured", "error": str(detail)}
            )
            return payload
        payload.update(_probe_local_llm(local_base, timeout))
        return payload

    # Cloud providers: keep the check lightweight and config-based.
    payload.update(
        {
            "ok": True,
            "status": "online",
            "mode": "config_only",
        }
    )
    return payload


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
    from guardian.core.dependencies import _mask_dsn

    if format == "prometheus":
        return Response(
            content=metrics.generate_latest(metrics.registry),
            media_type=metrics.CONTENT_TYPE_LATEST,
        )

    # JSON format (default)
    api_key = (os.getenv("GUARDIAN_API_KEY") or "").strip()
    masked_api_key = (
        (api_key[:4] + "…" + api_key[-4:])
        if api_key and len(api_key) > 8
        else api_key
    )

    return {
        "status": "ok",
        "db_backend": DB_BACKEND,
        "pg_dsn_masked": _mask_dsn(get_database_dsn())
        if get_database_dsn()
        else None,
        "api_key_masked": masked_api_key,
    }
