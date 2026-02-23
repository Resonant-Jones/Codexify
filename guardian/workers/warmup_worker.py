"""Warm-up worker for preloading local models."""

from __future__ import annotations

import logging
import os
import socket
import time
from typing import Iterable, List
from urllib.parse import urlparse

import requests
from redis.exceptions import TimeoutError as RedisTimeoutError

from guardian.core.ai_router import call_local
from guardian.core.config import get_settings
from guardian.queue import task_events
from guardian.queue.redis_queue import clear_cancelled, dequeue, is_cancelled
from guardian.tasks.types import WarmupTask, task_from_dict

logger = logging.getLogger(__name__)

QUEUE_NAME = os.getenv("WARMUP_QUEUE_NAME", "codexify:queue:system")
MAX_RETRIES = int(os.getenv("WARMUP_MAX_RETRIES", "5"))
BACKOFF_BASE_SECONDS = float(os.getenv("WARMUP_BACKOFF_BASE_SECONDS", "1.0"))
BACKOFF_MAX_SECONDS = float(os.getenv("WARMUP_BACKOFF_MAX_SECONDS", "8.0"))
LOCAL_WARMUP_TIMEOUT_SECONDS = float(
    os.getenv("LOCAL_WARMUP_TIMEOUT_SECONDS", "90")
)
READINESS_TIMEOUT_SECONDS = float(
    os.getenv("WARMUP_READINESS_TIMEOUT_SECONDS", "90")
)
READINESS_BACKOFF_BASE_SECONDS = float(
    os.getenv("WARMUP_READINESS_BACKOFF_BASE_SECONDS", "1.0")
)
READINESS_BACKOFF_MAX_SECONDS = float(
    os.getenv("WARMUP_READINESS_BACKOFF_MAX_SECONDS", "8.0")
)
READINESS_REQUEST_TIMEOUT_SECONDS = float(
    os.getenv("WARMUP_READINESS_REQUEST_TIMEOUT_SECONDS", "2.5")
)
ALLOW_LOCALHOST_VAULTNODE = os.getenv(
    "VAULTNODE_ALLOW_LOCALHOST", ""
).lower() in {
    "1",
    "true",
    "yes",
    "y",
}


def _embeddings_backend() -> str:
    return (os.getenv("CODEXIFY_EMBEDDINGS_BACKEND") or "").strip().lower()


def _is_local_embeddings_backend() -> bool:
    return _embeddings_backend() == "local"


def _get_local_embed_model(*, strict: bool) -> str | None:
    model = (os.getenv("LOCAL_EMBED_MODEL") or "").strip()
    if strict and not model:
        raise RuntimeError(
            "LOCAL_EMBED_MODEL is not set. Set LOCAL_EMBED_MODEL to a local model id or path."
        )
    return model or None


def _is_embedding_model(model: str) -> bool:
    norm = str(model or "").strip().lower()
    if not norm:
        return False
    local_model = _get_local_embed_model(strict=False)
    if local_model and norm == local_model.strip().lower():
        if not _is_local_embeddings_backend():
            logger.info(
                "[warmup] skipping local embedding model=%s because backend=%s",
                model,
                _embeddings_backend() or "<unset>",
            )
        return True
    return False


def _safe_publish(task_id: str, event_type: str, data: dict) -> None:
    try:
        task_events.publish(task_id, event_type, data)
    except Exception as exc:
        logger.warning("[warmup] failed to publish event: %s", exc)


def _normalize_base_url(base_url: str) -> str:
    base_url = (base_url or "").strip()
    if not base_url:
        return ""
    if "://" not in base_url:
        base_url = f"http://{base_url}"
    return base_url.rstrip("/")


def _resolve_vaultnode_base_url() -> str:
    env_base = (os.getenv("VAULTNODE_BASE_URL") or "").strip()
    local_base = (os.getenv("LOCAL_BASE_URL") or "").strip()
    base_url = env_base or local_base
    if not base_url:
        port = (
            os.getenv("VAULTNODE_PORT") or os.getenv("LOCAL_PORT") or "11434"
        ).strip()
        base_url = f"http://vaultnode:{port}"
    return _normalize_base_url(base_url)


def _resolve_health_base(base_url: str) -> str:
    base_url = _normalize_base_url(base_url)
    if base_url.endswith("/v1"):
        return base_url[: -len("/v1")]
    return base_url


def _resolve_health_endpoints() -> list[str]:
    raw = os.getenv("VAULTNODE_HEALTH_ENDPOINTS", "").strip()
    if raw:
        endpoints = [entry.strip() for entry in raw.split(",") if entry.strip()]
    else:
        endpoints = ["/healthz", "/ping"]
    normalized: list[str] = []
    for endpoint in endpoints:
        if not endpoint.startswith("/"):
            endpoint = f"/{endpoint}"
        normalized.append(endpoint)
    return normalized


def _running_in_docker() -> bool:
    return os.path.exists("/.dockerenv") or os.getenv("DOCKER_CONTAINER") == "1"


def _warn_if_localhost(base_url: str) -> None:
    host = urlparse(base_url).hostname or ""
    if host in {"localhost", "127.0.0.1", "::1"} and _running_in_docker():
        if not ALLOW_LOCALHOST_VAULTNODE:
            logger.warning(
                "[warmup] localhost inside Docker points to the container, not VaultNode; "
                "use service name vaultnode (base_url=%s)",
                base_url,
            )


def _resolve_dns(host: str) -> str:
    if not host:
        return "<no host>"
    try:
        infos = socket.getaddrinfo(host, None)
        addresses = sorted({info[4][0] for info in infos})
        return ", ".join(addresses) if addresses else "<no records>"
    except Exception as exc:
        return f"<dns error: {type(exc).__name__}: {exc}>"


def _await_vaultnode_ready(
    base_url: str,
    endpoints: Iterable[str],
    *,
    max_wait_seconds: float | None = None,
    request_timeout: float | None = None,
    backoff_base_seconds: float | None = None,
    backoff_max_seconds: float | None = None,
) -> tuple[bool, Exception | None]:
    max_wait = (
        READINESS_TIMEOUT_SECONDS
        if max_wait_seconds is None
        else float(max_wait_seconds)
    )
    if max_wait <= 0:
        return False, RuntimeError("readiness max wait is non-positive")
    timeout = (
        READINESS_REQUEST_TIMEOUT_SECONDS
        if request_timeout is None
        else float(request_timeout)
    )
    delay = (
        READINESS_BACKOFF_BASE_SECONDS
        if backoff_base_seconds is None
        else float(backoff_base_seconds)
    )
    delay = max(delay, 0.0)
    max_delay = (
        READINESS_BACKOFF_MAX_SECONDS
        if backoff_max_seconds is None
        else float(backoff_max_seconds)
    )
    max_delay = max(max_delay, 0.0)

    health_base = _resolve_health_base(base_url)
    attempt = 0
    last_exc: Exception | None = None
    deadline = time.monotonic() + max_wait
    while True:
        attempt += 1
        for endpoint in endpoints:
            url = f"{health_base}{endpoint}"
            try:
                response = requests.get(url, timeout=timeout)
                if 200 <= response.status_code < 300:
                    if attempt > 1:
                        logger.info(
                            "[warmup] VaultNode ready after %s attempts url=%s",
                            attempt,
                            url,
                        )
                    return True, last_exc
                last_exc = RuntimeError(
                    f"unexpected status={response.status_code} url={url}"
                )
            except Exception as exc:
                last_exc = exc
        if time.monotonic() >= deadline:
            return False, last_exc
        time.sleep(delay)
        delay = min(delay * 2, max_delay) if max_delay > 0 else delay


def _prepare_vaultnode_target() -> tuple[str, str, list[str]]:
    base_url = _resolve_vaultnode_base_url()
    if base_url and not os.getenv("LOCAL_BASE_URL"):
        os.environ["LOCAL_BASE_URL"] = base_url
        settings = get_settings()
        settings.LOCAL_BASE_URL = base_url
        logger.info(
            "[warmup] LOCAL_BASE_URL not set; defaulting to %s",
            base_url,
        )
    _warn_if_localhost(base_url)
    health_base = _resolve_health_base(base_url)
    endpoints = _resolve_health_endpoints()
    return base_url, health_base, endpoints


def _log_vaultnode_failure(
    base_url: str,
    health_base: str,
    endpoints: Iterable[str],
    last_exc: Exception | None,
) -> None:
    host = urlparse(health_base or base_url).hostname or ""
    dns_info = _resolve_dns(host)
    last_error = (
        f"{type(last_exc).__name__}: {last_exc}" if last_exc else "unknown"
    )
    logger.error(
        "[warmup] VaultNode readiness failed base_url=%s health_base=%s endpoints=%s "
        "dns=%s last_error=%s",
        base_url,
        health_base,
        list(endpoints),
        dns_info,
        last_error,
    )


def _warm_model(task: WarmupTask, model: str) -> bool:
    if _is_embedding_model(model):
        logger.info(
            "[warmup] skipping embedding-only model=%s task=%s",
            model,
            task.task_id,
        )
        return True
    attempt = 0
    delay = BACKOFF_BASE_SECONDS
    while True:
        if is_cancelled(task.task_id):
            logger.info(
                "[warmup] cancelled task=%s model=%s", task.task_id, model
            )
            _safe_publish(
                task.task_id,
                "task.cancelled",
                {"model": model, "origin": task.origin},
            )
            clear_cancelled(task.task_id)
            return False
        try:
            call_local(
                [{"role": "user", "content": "."}],
                model=model,
                max_tokens=1,
                temperature=0.0,
                timeout=LOCAL_WARMUP_TIMEOUT_SECONDS,
                log_exceptions=False,
            )
            logger.info(
                "[warmup] success task=%s model=%s", task.task_id, model
            )
            return True
        except Exception as exc:
            attempt += 1
            logger.warning(
                "[warmup] failed task=%s model=%s attempt=%s err=%s",
                task.task_id,
                model,
                attempt,
                exc,
            )
            if attempt >= MAX_RETRIES:
                return False
            time.sleep(delay)
            delay = min(delay * 2, BACKOFF_MAX_SECONDS)


def _run_task(
    task: WarmupTask,
    *,
    base_url: str,
    health_base: str,
    endpoints: list[str],
) -> None:
    _safe_publish(
        task.task_id,
        "task.running",
        {"type": task.type, "origin": task.origin},
    )
    logger.info(
        "[task] running type=%s id=%s origin=%s",
        task.type,
        task.task_id,
        task.origin,
    )
    ready, last_exc = _await_vaultnode_ready(
        health_base,
        endpoints,
    )
    if not ready:
        _log_vaultnode_failure(base_url, health_base, endpoints, last_exc)
        _safe_publish(
            task.task_id,
            "task.failed",
            {"type": task.type, "origin": task.origin, "error": str(last_exc)},
        )
        logger.warning(
            "[task] failed type=%s id=%s origin=%s",
            task.type,
            task.task_id,
            task.origin,
        )
        return
    models = [m for m in task.models if isinstance(m, str) and m.strip()]
    all_ok = True
    for model in models:
        if not _warm_model(task, model.strip()):
            all_ok = False
    if all_ok:
        _safe_publish(
            task.task_id,
            "task.completed",
            {"type": task.type, "origin": task.origin},
        )
        logger.info(
            "[task] completed type=%s id=%s origin=%s",
            task.type,
            task.task_id,
            task.origin,
        )
    else:
        _safe_publish(
            task.task_id,
            "task.failed",
            {"type": task.type, "origin": task.origin},
        )
        logger.warning(
            "[task] failed type=%s id=%s origin=%s",
            task.type,
            task.task_id,
            task.origin,
        )


def run_forever() -> None:
    base_url, health_base, endpoints = _prepare_vaultnode_target()
    logger.info(
        "[warmup] worker started queue=%s base_url=%s health_base=%s endpoints=%s",
        QUEUE_NAME,
        base_url,
        health_base,
        endpoints,
    )
    while True:
        try:
            payload = dequeue(QUEUE_NAME, block=True, timeout=5)
        except RedisTimeoutError:
            logger.debug("[redis] idle timeout; continuing")
            continue
        except Exception as exc:
            logger.warning("[redis] dequeue error; continuing: %s", exc)
            time.sleep(1.0)
            continue

        if not payload:
            continue
        try:
            task = task_from_dict(payload)
        except Exception as exc:
            logger.warning("[warmup] invalid task payload: %s", exc)
            continue
        if not isinstance(task, WarmupTask):
            logger.warning(
                "[warmup] skipping non-warmup task type=%s id=%s",
                task.type,
                task.task_id,
            )
            continue
        if is_cancelled(task.task_id):
            _safe_publish(
                task.task_id,
                "task.cancelled",
                {"type": task.type, "origin": task.origin},
            )
            clear_cancelled(task.task_id)
            logger.info(
                "[task] cancelled type=%s id=%s", task.type, task.task_id
            )
            continue
        _run_task(
            task,
            base_url=base_url,
            health_base=health_base,
            endpoints=endpoints,
        )


if __name__ == "__main__":
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    run_forever()
