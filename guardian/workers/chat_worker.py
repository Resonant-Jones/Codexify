"""Chat completion worker for async tasks.

This worker is intentionally thin: orchestration and routing live in
`guardian.core.chat_completion_service.run_chat_completion_task`.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from fastapi import HTTPException
from redis.exceptions import TimeoutError as RedisTimeoutError

from guardian.core import dependencies, event_bus
from guardian.core.chat_completion_service import (
    ChatTaskCancelled,
    run_chat_completion_task,
)
from guardian.core.db import GuardianDB
from guardian.core.metrics import CHAT_TURN_METADATA_PERSIST_FAILURES_TOTAL
from guardian.queue import task_events
from guardian.queue.redis_queue import (
    clear_cancelled,
    dequeue,
    get_redis_client,
    is_cancelled,
)
from guardian.queue.turn_lock import release_turn_lock
from guardian.tasks.types import ChatCompletionTask, task_from_dict

logger = logging.getLogger(__name__)

QUEUE_NAME = os.getenv("CHAT_QUEUE_NAME", "codexify:queue:chat")
CONCURRENCY = int(os.getenv("CHAT_WORKER_CONCURRENCY", "2"))
WORKER_HEARTBEAT_KEY = os.getenv(
    "CHAT_WORKER_HEARTBEAT_KEY", "codexify:worker:chat:heartbeat"
)
WORKER_HEARTBEAT_TTL_SECONDS = int(
    os.getenv("CHAT_WORKER_HEARTBEAT_TTL_SECONDS", "45")
)

_MEDIA_DB: GuardianDB | None = None
_MEDIA_MARKER_RE = re.compile(
    r"<!--\s*cfy-media:(image|document):([a-fA-F0-9-]+)\s*-->"
)
_TURN_ID_ORIGIN_RE = re.compile(
    r"(?:^|\|)turn_id=(?P<turn_id>[a-f0-9-]{36})(?:\||$)",
    flags=re.IGNORECASE,
)
_TURN_COMPLETION_ANCHOR_PREFIX = "codexify:chat:turn-anchor"
_TURN_COMPLETION_ANCHOR_TTL_SECONDS = int(
    os.getenv("CHAT_TURN_COMPLETION_ANCHOR_TTL_SECONDS", "86400")
)
_MIRRORED_LIVE_EVENT_TYPES = {
    "task.running",
    "task.completed",
    "task.failed",
    "task.cancelled",
}


def _coerce_message_id(raw: Any) -> int | None:
    try:
        value = int(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _extract_turn_id(task: ChatCompletionTask) -> str:
    explicit = str(getattr(task, "turn_id", "") or "").strip()
    if explicit:
        return explicit
    origin = str(getattr(task, "origin", "") or "")
    match = _TURN_ID_ORIGIN_RE.search(origin)
    return match.group("turn_id").strip().lower() if match else ""


def _persist_turn_id_metadata(
    *, thread_id: int, message_id: int, turn_id: str
) -> bool:
    """Persist turn correlation key in chat_messages.extra_meta."""
    if not turn_id:
        return True
    chatlog_db = getattr(dependencies, "chatlog_db", None)
    if chatlog_db is None:
        return False

    connect = getattr(chatlog_db, "_connect", None)
    if not callable(connect):
        logger.debug(
            "[chat-worker] chatlog_db has no _connect; skipping turn metadata update"
        )
        return False

    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            """
            UPDATE chat_messages
            SET extra_meta = COALESCE(extra_meta, '{}'::jsonb) || %s::jsonb
            WHERE thread_id = %s
              AND id = %s
            RETURNING id
            """,
            (json.dumps({"turn_id": turn_id}), thread_id, message_id),
        )
        row = cur.fetchone()
        return bool(row)


def _turn_completion_anchor_key(thread_id: int, turn_id: str) -> str:
    return ":".join((_TURN_COMPLETION_ANCHOR_PREFIX, str(thread_id), turn_id))


def _cache_turn_completion_anchor(
    *, thread_id: int, message_id: int, turn_id: str
) -> bool:
    if not turn_id:
        return True
    try:
        client = get_redis_client()
        client.setex(
            _turn_completion_anchor_key(thread_id, turn_id),
            max(60, _TURN_COMPLETION_ANCHOR_TTL_SECONDS),
            str(message_id),
        )
        return True
    except Exception:
        logger.debug(
            "[chat-worker] failed to cache turn completion anchor thread_id=%s turn_id=%s message_id=%s",
            thread_id,
            turn_id,
            message_id,
            exc_info=True,
        )
        return False


def _cached_turn_completion_anchor(
    *, thread_id: int, turn_id: str
) -> int | None:
    if not turn_id:
        return None
    try:
        client = get_redis_client()
        cached = client.get(_turn_completion_anchor_key(thread_id, turn_id))
    except Exception:
        logger.debug(
            "[chat-worker] failed to read cached turn completion anchor thread_id=%s turn_id=%s",
            thread_id,
            turn_id,
            exc_info=True,
        )
        return None
    return _coerce_message_id(cached)


def _record_turn_metadata_persist_failure(reason: str) -> None:
    try:
        CHAT_TURN_METADATA_PERSIST_FAILURES_TOTAL.labels(
            reason=str(reason or "unknown")
        ).inc()
    except Exception:
        logger.debug(
            "[chat-worker] failed to record metadata persist metric reason=%s",
            reason,
            exc_info=True,
        )


def _coerce_row_message_id(row: Any) -> int | None:
    if row is None:
        return None
    if isinstance(row, dict):
        return _coerce_message_id(row.get("id"))
    if isinstance(row, (tuple, list)):
        return _coerce_message_id(row[0] if row else None)
    try:
        return _coerce_message_id(row["id"])  # type: ignore[index]
    except Exception:
        return _coerce_message_id(getattr(row, "id", None))


def _find_assistant_message_id_by_turn_id(
    *, thread_id: int, turn_id: str
) -> int | None:
    if not turn_id:
        return None
    chatlog_db = getattr(dependencies, "chatlog_db", None)
    if chatlog_db is None:
        return _cached_turn_completion_anchor(
            thread_id=thread_id,
            turn_id=turn_id,
        )
    connect = getattr(chatlog_db, "_connect", None)
    if not callable(connect):
        return _cached_turn_completion_anchor(
            thread_id=thread_id,
            turn_id=turn_id,
        )
    try:
        with connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT id
                FROM chat_messages
                WHERE thread_id = %s
                  AND role = 'assistant'
                  AND COALESCE(extra_meta, '{}'::jsonb)->>'turn_id' = %s
                ORDER BY id ASC
                LIMIT 1
                """,
                (thread_id, turn_id),
            )
            message_id = _coerce_row_message_id(cur.fetchone())
            if message_id is not None:
                return message_id
    except Exception:
        logger.debug(
            "[chat-worker] failed turn_id lookup thread_id=%s turn_id=%s",
            thread_id,
            turn_id,
            exc_info=True,
        )
    return _cached_turn_completion_anchor(thread_id=thread_id, turn_id=turn_id)


def _find_assistant_message_for_turn(
    *, thread_id: int, turn_id: str
) -> int | None:
    """Return an existing assistant message id for the turn when present."""
    return _find_assistant_message_id_by_turn_id(
        thread_id=thread_id,
        turn_id=turn_id,
    )


def _publish_worker_heartbeat(status: str = "idle") -> None:
    payload = {
        "worker": "chat",
        "status": status,
        "queue": QUEUE_NAME,
        "ts": int(time.time()),
    }
    try:
        client = get_redis_client()
        client.setex(
            WORKER_HEARTBEAT_KEY,
            max(5, WORKER_HEARTBEAT_TTL_SECONDS),
            json.dumps(payload),
        )
    except Exception as exc:
        logger.debug("[chat-worker] heartbeat update failed: %s", exc)


def _safe_emit_live_event(event_type: str, payload: dict[str, Any]) -> None:
    try:
        event_bus.emit_event(event_type, payload)
    except Exception as exc:
        logger.debug(
            "[chat-worker] failed to mirror live event type=%s err=%s",
            event_type,
            exc,
        )


def _safe_publish(task_id: str, event_type: str, data: dict) -> None:
    """Best-effort event publishing.

    Never raise from the worker hot-path.
    """
    payload: dict
    try:
        payload = dict(data) if isinstance(data, dict) else {"data": data}
    except Exception:
        payload = {"data": str(data)}

    try:
        task_events.publish(task_id, event_type, payload)
    except Exception as exc:
        logger.warning(
            "[chat-worker] failed to publish event type=%s task_id=%s err=%s",
            event_type,
            task_id,
            exc,
        )

    if event_type in _MIRRORED_LIVE_EVENT_TYPES:
        mirror_payload = dict(payload)
        mirror_payload.setdefault("task_id", task_id)
        _safe_emit_live_event(event_type, mirror_payload)


def _describe_task_error(exc: Exception) -> str:
    if isinstance(exc, HTTPException):
        detail = getattr(exc, "detail", "")
        if isinstance(detail, (dict, list)):
            try:
                return json.dumps(detail)
            except Exception:
                return str(detail)
        if detail:
            return str(detail)
    return str(exc) or exc.__class__.__name__


def _classify_runtime_status(detail: str) -> str | None:
    lowered = str(detail or "").strip().lower()
    if not lowered:
        return None
    if "timed out" in lowered or "read timeout" in lowered:
        return "timeout"
    if "connection refused" in lowered:
        return "connection_refused"
    if "failed to resolve" in lowered or "name resolution" in lowered:
        return "dns_error"
    return None


def _run_chat_task(task: ChatCompletionTask) -> None:
    run_id = uuid.uuid4().hex
    started = time.monotonic()
    turn_id = _extract_turn_id(task)
    _safe_publish(
        task.task_id,
        "task.running",
        {
            "run_id": run_id,
            "type": task.type,
            "origin": task.origin,
            "thread_id": task.thread_id,
            "turn_id": turn_id,
        },
    )
    logger.info(
        "[task] running type=%s id=%s run_id=%s origin=%s thread=%s turn_id=%s",
        task.type,
        task.task_id,
        run_id,
        task.origin,
        task.thread_id,
        turn_id,
    )

    try:
        existing_message_id = _find_assistant_message_for_turn(
            thread_id=task.thread_id,
            turn_id=turn_id,
        )
        if existing_message_id is not None:
            duration_ms = int((time.monotonic() - started) * 1000)
            logger.warning(
                "[chat-worker] duplicate_turn_detected thread_id=%s turn_id=%s task_id=%s existing_message_id=%s",
                task.thread_id,
                turn_id,
                task.task_id,
                existing_message_id,
            )
            _safe_publish(
                task.task_id,
                "task.completed",
                {
                    "run_id": run_id,
                    "duration_ms": duration_ms,
                    "thread_id": task.thread_id,
                    "turn_id": turn_id,
                    "message_id": existing_message_id,
                    "provider": task.provider,
                    "model": task.model,
                    "selection_source": "turn_id_dedupe",
                    "catalog_version_hash": None,
                },
            )
            return

        if is_cancelled(task.task_id):
            _safe_publish(
                task.task_id,
                "task.cancelled",
                {
                    "run_id": run_id,
                    "thread_id": task.thread_id,
                    "origin": task.origin,
                    "turn_id": turn_id,
                },
            )
            clear_cancelled(task.task_id)
            logger.info(
                "[task] cancelled type=%s id=%s run_id=%s turn_id=%s",
                task.type,
                task.task_id,
                run_id,
                turn_id,
            )
            return

        if turn_id:
            existing_message_id = _find_assistant_message_id_by_turn_id(
                thread_id=task.thread_id,
                turn_id=turn_id,
            )
            if existing_message_id is not None:
                duration_ms = int((time.monotonic() - started) * 1000)
                logger.warning(
                    "[chat-worker] duplicate_turn_prevented thread_id=%s turn_id=%s task_id=%s message_id=%s",
                    task.thread_id,
                    turn_id,
                    task.task_id,
                    existing_message_id,
                )
                _safe_publish(
                    task.task_id,
                    "task.completed",
                    {
                        "run_id": run_id,
                        "duration_ms": duration_ms,
                        "thread_id": task.thread_id,
                        "turn_id": turn_id,
                        "message_id": existing_message_id,
                        "deduplicated": True,
                        "provider": task.provider,
                        "model": task.model,
                    },
                )
                logger.info(
                    "[task] completed type=%s id=%s run_id=%s thread=%s turn_id=%s message_id=%s deduplicated=%s",
                    task.type,
                    task.task_id,
                    run_id,
                    task.thread_id,
                    turn_id,
                    existing_message_id,
                    True,
                )
                return

        result = run_chat_completion_task(
            task,
            token_callback=lambda token: _safe_publish(
                task.task_id,
                "task.progress",
                {
                    "run_id": run_id,
                    "token": (
                        token[:4096] if isinstance(token, str) else token
                    ),
                    "thread_id": task.thread_id,
                },
            ),
            cancel_check=lambda: is_cancelled(task.task_id),
            persist_assistant_message=True,
        )
        message_id = _coerce_message_id(result.get("message_id"))
        if message_id is None:
            logger.error(
                "[chat-worker] completion_missing_message thread_id=%s turn_id=%s task_id=%s",
                task.thread_id,
                turn_id,
                task.task_id,
            )
            raise RuntimeError("assistant_message_missing")

        cached_anchor = _cache_turn_completion_anchor(
            thread_id=task.thread_id,
            message_id=message_id,
            turn_id=turn_id,
        )
        if turn_id and not cached_anchor:
            logger.warning(
                "[chat-worker] turn_completion_anchor_cache_failed thread_id=%s turn_id=%s task_id=%s message_id=%s",
                task.thread_id,
                turn_id,
                task.task_id,
                message_id,
            )

        if turn_id:
            try:
                persisted = _persist_turn_id_metadata(
                    thread_id=task.thread_id,
                    message_id=message_id,
                    turn_id=turn_id,
                )
                if not persisted:
                    logger.warning(
                        "[chat-worker] completion_turn_metadata_missing thread_id=%s turn_id=%s task_id=%s message_id=%s",
                        task.thread_id,
                        turn_id,
                        task.task_id,
                        message_id,
                    )
                    logger.warning(
                        "[chat-worker] turn_id_metadata_persist_failed reason=persist_returned_false thread_id=%s turn_id=%s task_id=%s message_id=%s",
                        task.thread_id,
                        turn_id,
                        task.task_id,
                        message_id,
                    )
                    _record_turn_metadata_persist_failure(
                        "persist_returned_false"
                    )
            except Exception as exc:
                logger.warning(
                    "[chat-worker] turn_id_metadata_persist_failed reason=exception thread_id=%s turn_id=%s task_id=%s message_id=%s err=%s",
                    task.thread_id,
                    turn_id,
                    task.task_id,
                    message_id,
                    exc,
                    exc_info=True,
                )
                _record_turn_metadata_persist_failure("exception")
        if turn_id:
            canonical_message_id = _find_assistant_message_id_by_turn_id(
                thread_id=task.thread_id,
                turn_id=turn_id,
            )
            if (
                canonical_message_id is not None
                and canonical_message_id != message_id
            ):
                logger.warning(
                    "[chat-worker] completion_duplicate_turn_detected thread_id=%s turn_id=%s task_id=%s canonical_message_id=%s duplicate_message_id=%s",
                    task.thread_id,
                    turn_id,
                    task.task_id,
                    canonical_message_id,
                    message_id,
                )
                message_id = canonical_message_id

        logger.info(
            "[chat-worker] assistant_message_persisted thread_id=%s turn_id=%s task_id=%s assistant_message_id=%s",
            task.thread_id,
            turn_id,
            task.task_id,
            message_id,
        )
        duration_ms = int((time.monotonic() - started) * 1000)
        _safe_publish(
            task.task_id,
            "task.completed",
            {
                "run_id": run_id,
                "duration_ms": duration_ms,
                "thread_id": task.thread_id,
                "turn_id": turn_id,
                "message_id": message_id,
                "provider": result.get("provider"),
                "model": result.get("model"),
                "selection_source": result.get("selection_source"),
                "catalog_version_hash": result.get("catalog_version_hash"),
            },
        )
        logger.info(
            "[task] completed type=%s id=%s run_id=%s thread=%s turn_id=%s message_id=%s",
            task.type,
            task.task_id,
            run_id,
            task.thread_id,
            turn_id,
            message_id,
        )
    except ChatTaskCancelled:
        _safe_publish(
            task.task_id,
            "task.cancelled",
            {
                "run_id": run_id,
                "thread_id": task.thread_id,
                "origin": task.origin,
                "turn_id": turn_id,
            },
        )
        clear_cancelled(task.task_id)
        logger.info(
            "[task] cancelled type=%s id=%s run_id=%s turn_id=%s",
            task.type,
            task.task_id,
            run_id,
            turn_id,
        )
    except Exception as exc:
        duration_ms = int((time.monotonic() - started) * 1000)
        error_detail = _describe_task_error(exc)
        failure_payload = {
            "run_id": run_id,
            "duration_ms": duration_ms,
            "error": error_detail,
            "error_type": exc.__class__.__name__,
            "thread_id": task.thread_id,
            "origin": task.origin,
            "turn_id": turn_id,
        }
        runtime_status = _classify_runtime_status(error_detail)
        if runtime_status:
            failure_payload["runtime_status"] = runtime_status
        if task.provider:
            failure_payload["provider"] = task.provider
        if task.model:
            failure_payload["model"] = task.model
        _safe_publish(
            task.task_id,
            "task.failed",
            failure_payload,
        )
        _safe_emit_live_event(
            "completion.error",
            {
                **failure_payload,
                "task_id": task.task_id,
            },
        )
        logger.exception(
            "[task] failed type=%s id=%s run_id=%s turn_id=%s err=%s",
            task.type,
            task.task_id,
            run_id,
            turn_id,
            exc,
        )
    finally:
        owner = str(getattr(task, "turn_lock_owner", "") or "").strip()
        if not owner:
            owner = str(task.task_id or "").strip()
        if owner:
            try:
                released = release_turn_lock(task.thread_id, owner)
                if not released:
                    logger.debug(
                        "[turn-lock] release skipped thread=%s owner=%s",
                        task.thread_id,
                        owner,
                    )
            except Exception as exc:
                logger.warning(
                    "[turn-lock] release failed thread=%s owner=%s err=%s",
                    task.thread_id,
                    owner,
                    exc,
                )


def _initialize_worker() -> None:
    db = dependencies.init_database()
    if db is None:
        raise RuntimeError("chatlog_db not configured")
    dependencies.init_services(db)
    try:
        if dependencies.ENABLE_OUTBOX:
            event_bus.configure_event_store(db)
    except Exception as exc:
        logger.warning(
            "[chat-worker] outbox disabled; falling back to in-memory: %s",
            exc,
        )
    _publish_worker_heartbeat("starting")


def run_forever() -> None:
    _initialize_worker()
    logger.info(
        "[chat-worker] started queue=%s concurrency=%s",
        QUEUE_NAME,
        CONCURRENCY,
    )
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        while True:
            _publish_worker_heartbeat("idle")
            try:
                payload = dequeue(QUEUE_NAME, block=True, timeout=5)
            except RedisTimeoutError:
                logger.debug("[chat-worker] redis idle timeout; continuing")
                continue

            if not payload:
                continue
            _publish_worker_heartbeat("active")
            try:
                task = task_from_dict(payload)
            except Exception as exc:
                logger.warning("[chat-worker] invalid task payload: %s", exc)
                continue
            if not isinstance(task, ChatCompletionTask):
                logger.warning(
                    "[chat-worker] skipping non-chat task type=%s id=%s",
                    task.type,
                    task.task_id,
                )
                continue
            if isinstance(payload, dict):
                raw_turn_id = payload.get("turn_id")
                if isinstance(raw_turn_id, str) and raw_turn_id.strip():
                    task.turn_id = raw_turn_id.strip()
                raw_owner = payload.get("turn_lock_owner")
                if isinstance(raw_owner, str) and raw_owner.strip():
                    task.turn_lock_owner = raw_owner.strip()
            if is_cancelled(task.task_id):
                _safe_publish(
                    task.task_id,
                    "task.cancelled",
                    {
                        "type": task.type,
                        "origin": task.origin,
                        "turn_id": _extract_turn_id(task),
                    },
                )
                clear_cancelled(task.task_id)
                logger.info(
                    "[task] cancelled type=%s id=%s", task.type, task.task_id
                )
                continue
            executor.submit(_run_chat_task, task)


if __name__ == "__main__":
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    run_forever()
