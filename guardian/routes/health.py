"""
Health Routes
~~~~~~~~~~~~~

Health check endpoints for monitoring subsystem status.
Mounted without a prefix to preserve public paths like /health/chat.
"""

import json
import logging
import os
import threading
import time
from uuid import uuid4

import requests
from fastapi import APIRouter, Depends, Query, Request, Response

from guardian.core import metrics
from guardian.core.dependencies import DB_BACKEND, get_database_dsn
from guardian.core.llm_catalog import build_llm_catalog
from guardian.core.provider_registry import (
    normalize_provider,
    resolve_provider_capability,
)

logger = logging.getLogger(__name__)
_LLM_HEALTH_PROBE_CACHE: dict | None = None
_LLM_HEALTH_PROBE_TS = 0.0
_LLM_HEALTH_CACHE_LOCK = threading.Lock()
_LLM_HEALTH_PROBE_INFLIGHT_LOCK = threading.Lock()

# Chat worker heartbeat freshness thresholds.
CHAT_WORKER_HEARTBEAT_FRESH_THRESHOLD_SECONDS = 10.0
CHAT_WORKER_HEARTBEAT_DEAD_THRESHOLD_SECONDS = 60.0

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


def _llm_health_cache_ttl_seconds() -> float:
    raw = (os.getenv("HEALTH_LLM_CACHE_TTL_SECONDS") or "5").strip()
    try:
        ttl = float(raw)
    except ValueError:
        ttl = 5.0
    return max(0.0, ttl)


def _get_cached_probe(ttl_seconds: float) -> dict | None:
    now = time.monotonic()
    with _LLM_HEALTH_CACHE_LOCK:
        if _LLM_HEALTH_PROBE_CACHE is None:
            return None
        if ttl_seconds <= 0:
            return None
        age = now - _LLM_HEALTH_PROBE_TS
        if age > ttl_seconds:
            return None
        return dict(_LLM_HEALTH_PROBE_CACHE)


def _get_latest_probe() -> dict | None:
    with _LLM_HEALTH_CACHE_LOCK:
        if _LLM_HEALTH_PROBE_CACHE is None:
            return None
        return dict(_LLM_HEALTH_PROBE_CACHE)


def _store_probe(probe_payload: dict) -> None:
    global _LLM_HEALTH_PROBE_CACHE, _LLM_HEALTH_PROBE_TS
    with _LLM_HEALTH_CACHE_LOCK:
        _LLM_HEALTH_PROBE_CACHE = dict(probe_payload)
        _LLM_HEALTH_PROBE_TS = time.monotonic()


def _normalize_health_provider(raw_provider: str) -> str:
    provider = normalize_provider(raw_provider)
    if provider and provider != "local":
        return provider

    legacy_backend = (os.getenv("AI_BACKEND") or "").strip().lower()
    if legacy_backend in {"ollama", "local"}:
        return "local"
    if legacy_backend in {"openai", "groq", "alibaba", "minimax"}:
        return legacy_backend
    return "local"


def _classify_chat_worker_heartbeat(
    heartbeat_detected: bool, heartbeat_age_seconds: object
) -> str:
    """Classify chat worker freshness from heartbeat presence and age."""
    if not heartbeat_detected:
        return "dead"

    if not isinstance(heartbeat_age_seconds, (int, float)):
        return "dead"

    heartbeat_age = float(heartbeat_age_seconds)
    if heartbeat_age <= CHAT_WORKER_HEARTBEAT_FRESH_THRESHOLD_SECONDS:
        return "fresh"
    if heartbeat_age <= CHAT_WORKER_HEARTBEAT_DEAD_THRESHOLD_SECONDS:
        return "stale"
    return "dead"


def _collect_completion_service_health() -> dict[str, object]:
    from guardian.queue.redis_queue import get_redis_client

    heartbeat_key = os.getenv(
        "CHAT_WORKER_HEARTBEAT_KEY", "codexify:worker:chat:heartbeat"
    )
    completion_service: dict[str, object] = {
        "ok": False,
        "redis_reachable": False,
        "enqueue_test_ok": False,
        "worker_heartbeat_detected": False,
        "worker_heartbeat_age_seconds": None,
        "heartbeat_key": heartbeat_key,
        "status_reason": "unknown",
        "error": None,
    }

    try:
        client = get_redis_client()
        completion_service["redis_reachable"] = bool(client.ping())

        probe_queue = f"codexify:queue:healthcheck:{uuid4().hex}"
        probe_payload = {
            "probe": "health_chat",
            "probe_id": uuid4().hex,
            "ts": int(time.time()),
        }
        client.lpush(probe_queue, json.dumps(probe_payload))
        popped = client.rpop(probe_queue)
        completion_service["enqueue_test_ok"] = bool(popped)
        try:
            client.delete(probe_queue)
        except Exception:
            logger.debug(
                "[health/chat] probe queue cleanup failed", exc_info=True
            )

        raw_heartbeat = client.get(heartbeat_key)
        completion_service["worker_heartbeat_detected"] = bool(raw_heartbeat)
        if raw_heartbeat:
            heartbeat_payload = {}
            try:
                if isinstance(raw_heartbeat, (bytes, bytearray)):
                    heartbeat_payload = json.loads(
                        raw_heartbeat.decode("utf-8")
                    )
                else:
                    heartbeat_payload = json.loads(str(raw_heartbeat))
            except Exception:
                heartbeat_payload = {}
            ts = heartbeat_payload.get("ts")
            if isinstance(ts, (int, float)):
                completion_service["worker_heartbeat_age_seconds"] = max(
                    0.0, round(time.time() - float(ts), 3)
                )

        completion_service[
            "worker_heartbeat_status"
        ] = _classify_chat_worker_heartbeat(
            completion_service["worker_heartbeat_detected"],
            completion_service["worker_heartbeat_age_seconds"],
        )

        completion_service["ok"] = bool(
            completion_service["redis_reachable"]
            and completion_service["enqueue_test_ok"]
            and completion_service["worker_heartbeat_status"] == "fresh"
        )
        if not completion_service["redis_reachable"]:
            completion_service["status_reason"] = "redis_unreachable"
        elif not completion_service["enqueue_test_ok"]:
            completion_service["status_reason"] = "queue_enqueue_failed"
        elif not completion_service["worker_heartbeat_detected"]:
            completion_service["status_reason"] = "worker_heartbeat_missing"
        elif completion_service["worker_heartbeat_status"] == "stale":
            completion_service["status_reason"] = "worker_heartbeat_stale"
        elif completion_service["worker_heartbeat_status"] == "dead":
            completion_service["status_reason"] = "worker_heartbeat_dead"
        else:
            completion_service["status_reason"] = "ok"
    except Exception as exc:
        completion_service["error"] = f"{type(exc).__name__}: {exc}"
        completion_service["status_reason"] = "probe_failed"
        logger.warning("[health/chat] completion service check failed: %s", exc)

    return completion_service


@router.get("/health")
def health(request: Request):
    """Base health check endpoint for system-level monitoring."""
    payload = {"status": "ok"}
    supported_profile = getattr(request.app.state, "supported_profile", None)
    if supported_profile is not None:
        payload["supported_profile"] = supported_profile
    return payload


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
        _resolve_local_base,
        describe_local_runtime,
    )
    from guardian.core.config import (
        LLMConfigError,
        get_settings,
        validate_llm_config,
    )

    settings = get_settings()
    provider = _normalize_health_provider(settings.LLM_PROVIDER or "local")
    provider_runtime = resolve_provider_capability(provider, settings)
    model = str(provider_runtime.get("default_model") or "").strip()
    completion_service = _collect_completion_service_health()

    payload = {
        "provider": provider,
        "model": model,
        "provider_runtime": provider_runtime,
        "completion_service": completion_service,
    }
    if provider == "local" and model:
        payload["runtime"] = describe_local_runtime(model, settings=settings)

    try:
        validate_llm_config(settings, provider_override=provider)
    except LLMConfigError as exc:
        payload.update(
            {"ok": False, "status": "misconfigured", "error": str(exc)}
        )
        return payload

    if provider == "local":
        timeout = float(os.getenv("HEALTH_LLM_REQUEST_TIMEOUT_SECONDS", "1.0"))
        cache_ttl = _llm_health_cache_ttl_seconds()
        cached = _get_cached_probe(cache_ttl)
        if cached is not None:
            payload.update(cached)
            payload["cache"] = "hit"
            return payload

        if not _LLM_HEALTH_PROBE_INFLIGHT_LOCK.acquire(blocking=False):
            stale = _get_latest_probe()
            if stale is not None:
                payload.update(stale)
                payload["cache"] = "stale"
                return payload
            payload.update(
                {
                    "ok": False,
                    "status": "unknown",
                    "error": "health probe in progress",
                }
            )
            return payload

        try:
            local_base = _resolve_local_base(settings)
        except Exception as exc:
            detail = getattr(exc, "detail", str(exc))
            payload.update(
                {"ok": False, "status": "misconfigured", "error": str(detail)}
            )
            _LLM_HEALTH_PROBE_INFLIGHT_LOCK.release()
            return payload
        try:
            probe_payload = _probe_local_llm(local_base, timeout)
            _store_probe(probe_payload)
            payload.update(probe_payload)
            payload["cache"] = "miss"
        finally:
            _LLM_HEALTH_PROBE_INFLIGHT_LOCK.release()
        return payload

    if not provider_runtime.get("enabled"):
        payload.update(
            {
                "ok": False,
                "status": "misconfigured",
                "error": provider_runtime.get("disabled_reason")
                or "Provider unavailable",
            }
        )
        return payload

    payload.update(
        {
            "ok": False,
            "status": "unknown",
            "mode": "runtime_unprobed",
            "error": (
                "Cloud provider is configured but not actively probed; "
                "runtime availability is unknown."
            ),
        }
    )
    return payload


@router.get("/api/llm/catalog")
def llm_catalog(include: str | None = Query(default=None)):
    include_all = str(include or "").strip().lower() == "all"
    return build_llm_catalog(include_all=include_all)


@router.get("/health/chat")
def health_chat():
    """Get health status of chat subsystem."""
    # Import from core dependencies module
    from guardian.core.dependencies import DB_BACKEND, chatlog_db

    completion_service = _collect_completion_service_health()

    try:
        threads = chatlog_db.count_chat_threads()
        messages = chatlog_db.count_all_messages()
    except Exception as _e:
        logger.warning("[health/chat] check failed: %s", _e)
        threads = 0
        messages = 0

    redis_reachable = bool(completion_service.get("redis_reachable"))
    queue_ok = bool(completion_service.get("enqueue_test_ok"))
    redis_ok = bool(redis_reachable and queue_ok)
    worker_detected = bool(completion_service.get("worker_heartbeat_detected"))
    worker_age_seconds = completion_service.get("worker_heartbeat_age_seconds")
    worker_status = str(
        completion_service.get("worker_heartbeat_status")
        or _classify_chat_worker_heartbeat(worker_detected, worker_age_seconds)
    )

    if not redis_reachable:
        status = "unhealthy"
        notes = [
            "redis unreachable; chat completion cannot be trusted",
        ]
    elif not queue_ok:
        status = "unhealthy"
        notes = [
            "queue round-trip probe failed; chat completion cannot be trusted",
        ]
    elif worker_status == "fresh":
        status = "healthy"
        notes = []
    elif worker_status == "stale":
        status = "degraded"
        notes = [
            "worker heartbeat stale; chat completion may be degraded",
        ]
    else:
        status = "unhealthy"
        if not worker_detected:
            notes = [
                "worker heartbeat missing; chat completion cannot progress",
            ]
        elif worker_age_seconds is None:
            notes = [
                "worker heartbeat age unavailable; chat completion cannot be trusted",
            ]
        else:
            notes = [
                "worker heartbeat dead; chat completion cannot progress",
            ]

    return {
        "ok": status == "healthy",
        "status": status,
        "redis": "ok" if redis_ok else "unhealthy",
        "worker": {
            "status": worker_status,
            "heartbeat_age_seconds": worker_age_seconds
            if worker_detected
            else None,
        },
        "notes": notes,
        "threads": threads,
        "messages": messages,
        "backend": DB_BACKEND,
        "completion_service": completion_service,
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
