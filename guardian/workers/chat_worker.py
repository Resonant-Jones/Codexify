"""Chat completion worker for async tasks.

This worker is intentionally thin: orchestration and routing live in
`guardian.core.chat_completion_service.run_chat_completion_task`.
"""

from __future__ import annotations

import logging
import os
import re
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

from redis.exceptions import TimeoutError as RedisTimeoutError

from guardian.core import dependencies, event_bus
from guardian.core.chat_completion_service import (
    ChatTaskCancelled,
    run_chat_completion_task,
)
from guardian.core.db import GuardianDB
from guardian.queue import task_events
from guardian.queue.redis_queue import clear_cancelled, dequeue, is_cancelled
from guardian.queue.turn_lock import release_turn_lock
from guardian.tasks.types import ChatCompletionTask, task_from_dict

logger = logging.getLogger(__name__)

QUEUE_NAME = os.getenv("CHAT_QUEUE_NAME", "codexify:queue:chat")
CONCURRENCY = int(os.getenv("CHAT_WORKER_CONCURRENCY", "2"))

_MEDIA_DB: GuardianDB | None = None
_MEDIA_MARKER_RE = re.compile(
    r"<!--\s*cfy-media:(image|document):([a-fA-F0-9-]+)\s*-->"
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


def _run_chat_task(task: ChatCompletionTask) -> None:
    run_id = uuid.uuid4().hex
    started = time.monotonic()
    _safe_publish(
        task.task_id,
        "task.running",
        {
            "run_id": run_id,
            "type": task.type,
            "origin": task.origin,
            "thread_id": task.thread_id,
        },
    )
    logger.info(
        "[task] running type=%s id=%s run_id=%s origin=%s thread=%s",
        task.type,
        task.task_id,
        run_id,
        task.origin,
        task.thread_id,
    )

    try:
        if is_cancelled(task.task_id):
            _safe_publish(
                task.task_id,
                "task.cancelled",
                {
                    "run_id": run_id,
                    "thread_id": task.thread_id,
                    "origin": task.origin,
                },
            )
            clear_cancelled(task.task_id)
            logger.info(
                "[task] cancelled type=%s id=%s run_id=%s",
                task.type,
                task.task_id,
                run_id,
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
        duration_ms = int((time.monotonic() - started) * 1000)
        _safe_publish(
            task.task_id,
            "task.completed",
            {
                "run_id": run_id,
                "duration_ms": duration_ms,
                "thread_id": task.thread_id,
                "message_id": result.get("message_id"),
                "provider": result.get("provider"),
                "model": result.get("model"),
                "selection_source": result.get("selection_source"),
                "catalog_version_hash": result.get("catalog_version_hash"),
            },
        )
        logger.info(
            "[task] completed type=%s id=%s run_id=%s thread=%s",
            task.type,
            task.task_id,
            run_id,
            task.thread_id,
        )
    except ChatTaskCancelled:
        _safe_publish(
            task.task_id,
            "task.cancelled",
            {
                "run_id": run_id,
                "thread_id": task.thread_id,
                "origin": task.origin,
            },
        )
        clear_cancelled(task.task_id)
        logger.info(
            "[task] cancelled type=%s id=%s run_id=%s",
            task.type,
            task.task_id,
            run_id,
        )
    except Exception as exc:
        duration_ms = int((time.monotonic() - started) * 1000)
        _safe_publish(
            task.task_id,
            "task.failed",
            {
                "run_id": run_id,
                "duration_ms": duration_ms,
                "error": str(exc),
                "error_type": exc.__class__.__name__,
                "thread_id": task.thread_id,
                "origin": task.origin,
            },
        )
        logger.exception(
            "[task] failed type=%s id=%s run_id=%s err=%s",
            task.type,
            task.task_id,
            run_id,
            exc,
        )
    finally:
        owner = (task.turn_lock_owner or "").strip()
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


def run_forever() -> None:
    _initialize_worker()
    logger.info(
        "[chat-worker] started queue=%s concurrency=%s",
        QUEUE_NAME,
        CONCURRENCY,
    )
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        while True:
            try:
                payload = dequeue(QUEUE_NAME, block=True, timeout=5)
            except RedisTimeoutError:
                logger.debug("[chat-worker] redis idle timeout; continuing")
                continue

            if not payload:
                continue
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
            executor.submit(_run_chat_task, task)


if __name__ == "__main__":
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    run_forever()
