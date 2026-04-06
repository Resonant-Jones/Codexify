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
from datetime import datetime, timezone
from uuid import uuid4

import requests
from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import JSONResponse

from guardian.core import metrics
from guardian.core.dependencies import DB_BACKEND, get_database_dsn
from guardian.core.health_service import (
    build_health_response,
    normalize_health_status,
)
from guardian.core.llm_catalog import build_llm_catalog
from guardian.core.provider_registry import (
    normalize_provider,
    resolve_provider_capability,
)
from guardian.core.provider_truth import build_provider_truth

logger = logging.getLogger(__name__)
_LLM_HEALTH_PROBE_CACHE: dict | None = None
_LLM_HEALTH_PROBE_TS = 0.0
_LLM_HEALTH_CACHE_LOCK = threading.Lock()
_LLM_HEALTH_PROBE_INFLIGHT_LOCK = threading.Lock()

# Chat worker heartbeat freshness thresholds.
CHAT_WORKER_HEARTBEAT_FRESH_THRESHOLD_SECONDS = 10.0
CHAT_WORKER_HEARTBEAT_DEAD_THRESHOLD_SECONDS = 60.0

CHAT_QUEUE_NAME = "codexify:queue:chat"
CHAT_QUEUE_HIGH_DEPTH_THRESHOLD = 25
CHAT_QUEUE_PROGRESS_SAMPLE_STALE_SECONDS = 30.0

_CHAT_QUEUE_PROGRESS_LOCK = threading.Lock()
_CHAT_QUEUE_LAST_DEPTH: int | None = None
_CHAT_QUEUE_LAST_CHECK_TS = 0.0

# Create unprefixed router to preserve /health/chat path
router = APIRouter(tags=["Health"])


def _redis_dependency_unavailable_response(
    payload: dict[str, object]
) -> JSONResponse:
    return JSONResponse(status_code=503, content=payload)


def _health_response(
    service: str,
    status: str,
    details: dict[str, object],
    *,
    http_status: int | None = None,
):
    payload = build_health_response(
        service=service, status=normalize_health_status(status), details=details
    )
    for key, value in details.items():
        if key in {"status", "service", "timestamp", "details"}:
            continue
        payload[key] = value
    if http_status is None:
        return payload
    return JSONResponse(status_code=http_status, content=payload)


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


def _probe_local_llm(settings, timeout_seconds: float) -> dict:
    from guardian.core.ai_router import (
        _resolve_local_endpoint_candidates,
        describe_local_endpoint_resolution,
    )

    endpoints = _resolve_llm_health_endpoints()
    attempted_base_urls: list[str] = []
    last_error = "unreachable"
    failure_kind: str | None = None

    for candidate in _resolve_local_endpoint_candidates(settings):
        attempted_base_urls.append(candidate.base_url)
        health_base = (
            candidate.base_url[:-3]
            if candidate.base_url.endswith("/v1")
            else candidate.base_url
        )
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
                        "endpoint_resolution": describe_local_endpoint_resolution(
                            settings,
                            selected_base_url=candidate.base_url,
                            attempted_base_urls=attempted_base_urls,
                            state="available",
                        ),
                    }
                last_error = f"HTTP {resp.status_code} from {endpoint}"
                failure_kind = "provider_http_error"
            except requests.exceptions.RequestException as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                failure_kind = (
                    "provider_timeout"
                    if isinstance(exc, requests.exceptions.Timeout)
                    else "transport_error"
                )
            except Exception as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                failure_kind = "request_error"

    return {
        "ok": False,
        "status": "offline",
        "checked_endpoints": endpoints,
        "error": last_error,
        "endpoint_resolution": describe_local_endpoint_resolution(
            settings,
            attempted_base_urls=attempted_base_urls,
            state="degraded" if attempted_base_urls else "unavailable",
            failure_kind=failure_kind,
            reason=last_error,
        ),
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


def _coerce_chat_worker_heartbeat_timestamp(
    raw_timestamp: object,
) -> float | None:
    if isinstance(raw_timestamp, bool):
        return None

    if isinstance(raw_timestamp, (int, float)):
        return float(raw_timestamp)

    if not isinstance(raw_timestamp, str):
        return None

    value = raw_timestamp.strip()
    if not value:
        return None

    try:
        return float(value)
    except ValueError:
        pass

    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()


def _resolve_chat_worker_heartbeat(
    raw_heartbeat: object,
) -> dict[str, object]:
    evidence: dict[str, object] = {
        "detected": False,
        "age_seconds": None,
        "status": "dead",
        "reason": "missing",
        "detail": None,
    }
    if not raw_heartbeat:
        return evidence

    evidence["detected"] = True
    parsed_payload: object = raw_heartbeat
    raw_text: str | None = None

    if isinstance(raw_heartbeat, (bytes, bytearray)):
        try:
            raw_text = raw_heartbeat.decode("utf-8")
        except UnicodeDecodeError:
            evidence["reason"] = "malformed"
            evidence["detail"] = "payload_decode_failed"
            return evidence
    elif isinstance(raw_heartbeat, str):
        raw_text = raw_heartbeat

    if raw_text is not None:
        try:
            parsed_payload = json.loads(raw_text)
        except Exception:
            parsed_payload = raw_text

    timestamp_value: object | None = None
    if isinstance(parsed_payload, dict):
        for key in ("ts", "timestamp", "last_seen", "updated_at"):
            if key in parsed_payload:
                timestamp_value = parsed_payload.get(key)
                break
        if timestamp_value is None:
            evidence["reason"] = "malformed"
            evidence["detail"] = "timestamp_missing"
            return evidence
    elif isinstance(parsed_payload, (int, float, str)):
        timestamp_value = parsed_payload
    else:
        evidence["reason"] = "malformed"
        evidence["detail"] = "payload_shape_invalid"
        return evidence

    timestamp_seconds = _coerce_chat_worker_heartbeat_timestamp(timestamp_value)
    if timestamp_seconds is None:
        evidence["reason"] = "malformed"
        evidence["detail"] = "timestamp_invalid"
        return evidence

    heartbeat_age_seconds = max(0.0, round(time.time() - timestamp_seconds, 3))
    evidence["age_seconds"] = heartbeat_age_seconds
    evidence["status"] = _classify_chat_worker_heartbeat(
        True, heartbeat_age_seconds
    )
    evidence["reason"] = "ok"
    return evidence


def _collect_chat_queue_health() -> dict[str, object]:
    global _CHAT_QUEUE_LAST_DEPTH, _CHAT_QUEUE_LAST_CHECK_TS

    from guardian.queue.redis_queue import (
        RedisOperationTimeout,
        get_redis_client,
        run_with_redis_timeout,
    )

    queue_health: dict[str, object] = {
        "depth": None,
        "status": "unknown",
        "error": None,
        "dependency": None,
        "dependency_unavailable": False,
    }

    try:
        client = run_with_redis_timeout(get_redis_client)
        llen = getattr(client, "llen", None)
        if not callable(llen):
            queue_health["error"] = "queue_depth_unavailable"
            return queue_health

        depth = max(
            0,
            int(run_with_redis_timeout(lambda: llen(CHAT_QUEUE_NAME))),
        )
        now = time.time()
        with _CHAT_QUEUE_PROGRESS_LOCK:
            previous_depth = _CHAT_QUEUE_LAST_DEPTH
            previous_check_ts = _CHAT_QUEUE_LAST_CHECK_TS
            _CHAT_QUEUE_LAST_DEPTH = depth
            _CHAT_QUEUE_LAST_CHECK_TS = now

        queue_health["depth"] = depth

        if depth == 0:
            queue_health["status"] = "progressing"
            return queue_health

        if previous_depth is None:
            queue_health["status"] = "unknown"
            return queue_health

        if (
            previous_check_ts
            and now - previous_check_ts
            > CHAT_QUEUE_PROGRESS_SAMPLE_STALE_SECONDS
        ):
            queue_health["status"] = "unknown"
            return queue_health

        if depth < previous_depth:
            queue_health["status"] = "progressing"
        else:
            queue_health["status"] = "stalled"
    except (RedisOperationTimeout, Exception) as exc:
        queue_health["error"] = f"{type(exc).__name__}: {exc}"
        queue_health["dependency"] = "redis"
        queue_health["dependency_unavailable"] = True

    return queue_health


def _collect_completion_service_health() -> dict[str, object]:
    from guardian.queue.redis_queue import (
        RedisOperationTimeout,
        get_redis_client,
        run_with_redis_timeout,
    )

    heartbeat_key = os.getenv(
        "CHAT_WORKER_HEARTBEAT_KEY", "codexify:worker:chat:heartbeat"
    )
    completion_service: dict[str, object] = {
        "ok": False,
        "redis_reachable": False,
        "enqueue_test_ok": False,
        "worker_heartbeat_detected": False,
        "worker_heartbeat_age_seconds": None,
        "worker_heartbeat_reason": "missing",
        "worker_heartbeat_detail": None,
        "heartbeat_key": heartbeat_key,
        "status_reason": "unknown",
        "error": None,
        "dependency": None,
        "dependency_unavailable": False,
    }

    try:
        client = run_with_redis_timeout(get_redis_client)
        completion_service["redis_reachable"] = bool(
            run_with_redis_timeout(client.ping)
        )

        probe_queue = f"codexify:queue:healthcheck:{uuid4().hex}"
        probe_payload = {
            "probe": "health_chat",
            "probe_id": uuid4().hex,
            "ts": int(time.time()),
        }
        run_with_redis_timeout(
            lambda: client.lpush(probe_queue, json.dumps(probe_payload))
        )
        popped = run_with_redis_timeout(lambda: client.rpop(probe_queue))
        completion_service["enqueue_test_ok"] = bool(popped)
        try:
            run_with_redis_timeout(lambda: client.delete(probe_queue))
        except (RedisOperationTimeout, Exception):
            logger.debug(
                "[health/chat] probe queue cleanup failed", exc_info=True
            )

        raw_heartbeat = run_with_redis_timeout(
            lambda: client.get(heartbeat_key)
        )
        heartbeat_evidence = _resolve_chat_worker_heartbeat(raw_heartbeat)
        completion_service["worker_heartbeat_detected"] = bool(
            heartbeat_evidence["detected"]
        )
        completion_service["worker_heartbeat_age_seconds"] = heartbeat_evidence[
            "age_seconds"
        ]
        completion_service["worker_heartbeat_reason"] = heartbeat_evidence[
            "reason"
        ]
        completion_service["worker_heartbeat_detail"] = heartbeat_evidence[
            "detail"
        ]

        completion_service["worker_heartbeat_status"] = heartbeat_evidence[
            "status"
        ]

        completion_service["ok"] = bool(
            completion_service["redis_reachable"]
            and completion_service["enqueue_test_ok"]
            and completion_service["worker_heartbeat_status"] == "fresh"
        )
        if not completion_service["redis_reachable"]:
            completion_service["status_reason"] = "redis_unreachable"
        elif not completion_service["enqueue_test_ok"]:
            completion_service["status_reason"] = "queue_enqueue_failed"
        elif completion_service["worker_heartbeat_reason"] == "missing":
            completion_service["status_reason"] = "worker_heartbeat_missing"
        elif completion_service["worker_heartbeat_reason"] == "malformed":
            completion_service["status_reason"] = "worker_heartbeat_malformed"
        elif completion_service["worker_heartbeat_status"] == "stale":
            completion_service["status_reason"] = "worker_heartbeat_stale"
        elif completion_service["worker_heartbeat_status"] == "dead":
            completion_service["status_reason"] = "worker_heartbeat_dead"
        else:
            completion_service["status_reason"] = "ok"
    except (RedisOperationTimeout, Exception) as exc:
        completion_service["error"] = f"{type(exc).__name__}: {exc}"
        completion_service["status_reason"] = "dependency_unavailable"
        completion_service["dependency"] = "redis"
        completion_service["dependency_unavailable"] = True
        logger.warning("[health/chat] completion service check failed: %s", exc)

    return completion_service


@router.get("/health")
def health(request: Request):
    """Base health check endpoint for system-level monitoring."""
    details: dict[str, object] = {}
    supported_profile = getattr(request.app.state, "supported_profile", None)
    if supported_profile is not None:
        details["supported_profile"] = supported_profile
    return _health_response("core", "ok", details)


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
        resolve_local_execution_model,
    )
    from guardian.core.config import (
        LLMConfigError,
        get_settings,
        validate_llm_config,
    )

    settings = get_settings()
    provider = _normalize_health_provider(settings.LLM_PROVIDER or "local")
    provider_runtime = dict(resolve_provider_capability(provider, settings))
    model = str(provider_runtime.get("default_model") or "").strip()
    completion_service = _collect_completion_service_health()
    local_model_resolution = None

    if provider == "local":
        local_model_resolution = resolve_local_execution_model(
            settings=settings,
            requested_model=model,
            validate_availability=True,
            request_get=requests.get,
        )
        if local_model_resolution.model:
            model = local_model_resolution.model
            provider_runtime["default_model"] = model
        if local_model_resolution.failure_kind:
            provider_runtime["enabled"] = False
            provider_runtime["disabled_reason"] = local_model_resolution.message

    payload = {
        "provider": provider,
        "model": model,
        "provider_runtime": provider_runtime,
        "completion_service": completion_service,
    }
    if local_model_resolution is not None:
        payload["model_resolution"] = local_model_resolution.as_dict()
    if provider == "local" and model:
        payload["runtime"] = describe_local_runtime(model, settings=settings)

    def _wrap(status: str, *, http_status: int | None = None):
        envelope = build_health_response(
            "llm", normalize_health_status(status), payload
        )
        if http_status is None:
            return envelope
        return JSONResponse(status_code=http_status, content=envelope)

    try:
        validate_llm_config(settings, provider_override=provider)
    except LLMConfigError as exc:
        payload.update(
            {"ok": False, "status": "misconfigured", "error": str(exc)}
        )
        payload["provider_truth"] = build_provider_truth(
            provider,
            settings,
            capability=provider_runtime,
            discoverable=False,
            selectable=False,
        )
        return _wrap("down")

    if (
        local_model_resolution is not None
        and local_model_resolution.failure_kind
    ):
        payload.update(
            {
                "ok": False,
                "status": "misconfigured",
                "error": payload["model_resolution"]["error"],
                "failure_kind": local_model_resolution.failure_kind,
                "message": local_model_resolution.message,
            }
        )
        payload["provider_truth"] = build_provider_truth(
            provider,
            settings,
            capability=provider_runtime,
            discoverable=bool(
                local_model_resolution.endpoint_resolution
                and str(
                    local_model_resolution.endpoint_resolution.get("state")
                    or ""
                ).strip()
                == "available"
            ),
            selectable=False,
        )
        return _wrap("down")

    if completion_service.get("dependency_unavailable"):
        payload.update(
            {
                "ok": False,
                "status": "dependency_unavailable",
                "error": "dependency_unavailable",
                "dependency": "redis",
            }
        )
        return _wrap("down", http_status=503)

    if provider == "local":
        timeout = float(os.getenv("HEALTH_LLM_REQUEST_TIMEOUT_SECONDS", "1.0"))
        cache_ttl = _llm_health_cache_ttl_seconds()
        cached = _get_cached_probe(cache_ttl)
        if cached is not None:
            payload.update(cached)
            payload["cache"] = "hit"
            payload["provider_truth"] = build_provider_truth(
                provider,
                settings,
                capability=provider_runtime,
                discoverable=bool(payload.get("ok")),
                selectable=bool(payload.get("ok")),
            )
            return _wrap(cached.get("status"))

        if not _LLM_HEALTH_PROBE_INFLIGHT_LOCK.acquire(blocking=False):
            stale = _get_latest_probe()
            if stale is not None:
                payload.update(stale)
                payload["cache"] = "stale"
                payload["provider_truth"] = build_provider_truth(
                    provider,
                    settings,
                    capability=provider_runtime,
                    discoverable=bool(payload.get("ok")),
                    selectable=bool(payload.get("ok")),
                )
                return _wrap(stale.get("status"))
            payload.update(
                {
                    "ok": False,
                    "status": "unknown",
                    "error": "health probe in progress",
                }
            )
            return _wrap("degraded")

        try:
            _resolve_local_base(settings)
        except Exception as exc:
            detail = getattr(exc, "detail", str(exc))
            payload.update(
                {"ok": False, "status": "misconfigured", "error": str(detail)}
            )
            _LLM_HEALTH_PROBE_INFLIGHT_LOCK.release()
            return _wrap("down")
        try:
            probe_payload = _probe_local_llm(settings, timeout)
            _store_probe(probe_payload)
            payload.update(probe_payload)
            payload["cache"] = "miss"
        finally:
            _LLM_HEALTH_PROBE_INFLIGHT_LOCK.release()
        payload["provider_truth"] = build_provider_truth(
            provider,
            settings,
            capability=provider_runtime,
            discoverable=bool(payload.get("ok")),
            selectable=bool(payload.get("ok")),
        )
        return _wrap(payload.get("status"))

    if not provider_runtime.get("enabled"):
        payload.update(
            {
                "ok": False,
                "status": "misconfigured",
                "error": provider_runtime.get("disabled_reason")
                or "Provider unavailable",
            }
        )
        payload["provider_truth"] = build_provider_truth(
            provider,
            settings,
            capability=provider_runtime,
            discoverable=str(
                (provider_runtime.get("model_index") or {}).get("state") or ""
            ).strip()
            == "available",
            selectable=False,
        )
        return _wrap("down")

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
    payload["provider_truth"] = build_provider_truth(
        provider,
        settings,
        capability=provider_runtime,
        discoverable=str(
            (provider_runtime.get("model_index") or {}).get("state") or ""
        ).strip()
        == "available",
        selectable=bool(provider_runtime.get("enabled")),
    )
    return _wrap("degraded")


@router.get("/api/llm/catalog")
def llm_catalog(include: str | None = Query(default=None)):
    include_all = str(include or "").strip().lower() == "all"
    return build_llm_catalog(include_all=include_all)


@router.get("/health/chat")
def health_chat():
    """Get health status of chat subsystem."""
    # Import from core dependencies module
    from guardian.core.config import get_settings
    from guardian.core.dependencies import DB_BACKEND, chatlog_db

    completion_service = _collect_completion_service_health()
    queue_health = _collect_chat_queue_health()
    settings = get_settings()
    provider = _normalize_health_provider(settings.LLM_PROVIDER or "local")
    provider_runtime = dict(resolve_provider_capability(provider, settings))
    local_model_resolution = None
    model = str(provider_runtime.get("default_model") or "").strip()
    if provider == "local":
        from guardian.core.ai_router import (
            describe_local_runtime,
            resolve_local_execution_model,
        )

        local_model_resolution = resolve_local_execution_model(
            settings=settings,
            requested_model=model,
            validate_availability=True,
            request_get=requests.get,
        )
        if local_model_resolution.model:
            model = local_model_resolution.model
            provider_runtime["default_model"] = model
        if local_model_resolution.failure_kind:
            provider_runtime["enabled"] = False
            provider_runtime["disabled_reason"] = local_model_resolution.message

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
    worker_reason = str(
        completion_service.get("worker_heartbeat_reason")
        or ("missing" if not worker_detected else "ok")
    )
    worker_detail = completion_service.get("worker_heartbeat_detail")
    queue_depth = queue_health.get("depth")
    queue_status = str(queue_health.get("status") or "unknown")
    queue_error = queue_health.get("error")
    redis_dependency_unavailable = bool(
        completion_service.get("dependency_unavailable")
        or queue_health.get("dependency_unavailable")
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
        if queue_error == "queue_depth_unavailable":
            status = "degraded"
            notes = [
                "queue depth unavailable; forward progress cannot be assessed",
            ]
        elif queue_depth == 0 or queue_status == "progressing":
            status = "healthy"
            notes = (
                ["queue empty"]
                if queue_depth == 0
                else ["queue backlog detected but progressing"]
            )
        elif queue_status == "unknown":
            status = "degraded"
            if (
                isinstance(queue_depth, int)
                and queue_depth >= CHAT_QUEUE_HIGH_DEPTH_THRESHOLD
            ):
                notes = [
                    "queue backlog high; forward progress is not yet established",
                ]
            else:
                notes = [
                    "queue backlog observed; forward progress is not yet established",
                ]
        else:
            if (
                isinstance(queue_depth, int)
                and queue_depth >= CHAT_QUEUE_HIGH_DEPTH_THRESHOLD
            ):
                status = "unhealthy"
                notes = [
                    "queue backlog high and not progressing; worker may be stuck",
                ]
            else:
                status = "degraded"
                notes = [
                    "queue backlog not progressing; worker may be stuck",
                ]
    elif worker_status == "stale":
        status = "degraded"
        notes = [
            "worker heartbeat stale; chat completion may be degraded",
        ]
    else:
        status = "unhealthy"
        if worker_reason == "missing" or not worker_detected:
            notes = [
                "worker heartbeat missing; chat completion cannot progress",
            ]
        elif worker_reason == "malformed":
            notes = [
                "worker heartbeat malformed; chat completion cannot be trusted",
            ]
        elif worker_age_seconds is None:
            notes = [
                "worker heartbeat age unavailable; chat completion cannot be trusted",
            ]
        else:
            notes = [
                "worker heartbeat dead; chat completion cannot progress",
            ]

    payload = {
        "ok": status == "healthy",
        "status": status,
        "redis": "ok" if redis_ok else "unhealthy",
        "worker": {
            "status": worker_status,
            "reason": worker_reason,
            "heartbeat_age_seconds": worker_age_seconds
            if worker_detected
            else None,
        },
        "queue": {
            "depth": queue_depth,
            "status": queue_status,
        },
        "notes": notes,
        "threads": threads,
        "messages": messages,
        "backend": DB_BACKEND,
        "completion_service": completion_service,
        "provider": provider,
        "model": model,
        "provider_runtime": provider_runtime,
        "provider_truth": build_provider_truth(
            provider,
            settings,
            capability=provider_runtime,
            discoverable=str(
                (provider_runtime.get("model_index") or {}).get("state") or ""
            ).strip()
            == "available"
            if provider != "local"
            else bool(provider_runtime.get("enabled")),
            selectable=bool(provider_runtime.get("enabled")),
        ),
    }
    if worker_detail:
        payload["worker"]["detail"] = worker_detail
    if local_model_resolution is not None:
        payload["model_resolution"] = local_model_resolution.as_dict()
    if provider == "local" and model:
        payload["runtime"] = describe_local_runtime(model, settings=settings)
    if redis_dependency_unavailable:
        payload.update(
            {
                "ok": False,
                "status": "unhealthy",
                "error": "dependency_unavailable",
                "dependency": "redis",
            }
        )
        if not any("redis unavailable" in str(note).lower() for note in notes):
            payload["notes"] = [
                "redis unavailable; chat completion cannot be trusted"
            ] + list(notes)
        return _redis_dependency_unavailable_response(payload)
    if (
        local_model_resolution is not None
        and local_model_resolution.failure_kind
    ):
        payload.update(
            {
                "ok": False,
                "status": "unhealthy",
                "error": payload["model_resolution"]["error"],
                "failure_kind": local_model_resolution.failure_kind,
                "message": local_model_resolution.message,
            }
        )
        payload["notes"] = [
            local_model_resolution.message
            or "local chat model resolution failed"
        ] + list(payload["notes"])
        payload["provider_truth"] = build_provider_truth(
            provider,
            settings,
            capability=provider_runtime,
            discoverable=bool(
                local_model_resolution.endpoint_resolution
                and str(
                    local_model_resolution.endpoint_resolution.get("state")
                    or ""
                ).strip()
                == "available"
            ),
            selectable=False,
        )
    return payload


@router.get("/health/memory")
def health_memory():
    """
    Get health status of memory subsystem.

    Returns a simple JSON payload with ok flag and per-silo counts.
    """
    error: str | None = None
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
        error = str(_e)

    return _health_response(
        "memory",
        "down" if error else "ok",
        {
            "ok": error is None,
            "counts": {
                "ephemeral": ephemeral_count,
                "midterm": midterm,
                "longterm": longterm,
            },
            **({"error": error} if error else {}),
        },
    )


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

        return _health_response(
            "vector",
            "ok" if ok else "down",
            {
                "ok": ok,
                "status": "ok" if ok else "error",
                "backend": backend,
                "source": source,
                "added": added,
                "matches": len(matches),
            },
        )
    except Exception as exc:
        logger.warning("[health/vector] check failed: %s", exc)
        return _health_response(
            "vector",
            "down",
            {
                "ok": False,
                "status": "error",
                "backend": "unknown",
                "error": str(exc),
            },
        )


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

    return _health_response(
        "deps",
        "ok",
        {
            "db_backend": DB_BACKEND,
            "pg_dsn_masked": _mask_dsn(get_database_dsn())
            if get_database_dsn()
            else None,
            "api_key_masked": masked_api_key,
        },
    )


@router.get("/api/health/executors")
def health_executors():
    """
    Report executor availability and auth-state health for all registry executors.

    Returns one row per executor from the canonical registry with:
    - executor_id, label, release_posture
    - installed flag and binary_path if resolved
    - auth_state (authenticated, unauthenticated, unknown)
    - availability_state (ready, degraded, unavailable, not_installed)
    - capability flags and supported_auth_modes
    - status_detail with explanatory text when relevant
    """
    from guardian.core.executors.health import get_all_executor_health

    executors = get_all_executor_health()
    return {
        "executors": [e.to_dict() for e in executors],
    }
