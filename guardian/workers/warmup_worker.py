"""Warm-up worker for preloading local models."""

from __future__ import annotations

import logging
import os
import time
from typing import Iterable, List

from redis.exceptions import TimeoutError as RedisTimeoutError

from guardian.core.ai_router import call_local
from guardian.queue import task_events
from guardian.queue.redis_queue import clear_cancelled, dequeue, is_cancelled
from guardian.tasks.types import WarmupTask, task_from_dict

logger = logging.getLogger(__name__)

QUEUE_NAME = os.getenv("WARMUP_QUEUE_NAME", "codexify:queue:system")
MAX_RETRIES = int(os.getenv("WARMUP_MAX_RETRIES", "5"))
BACKOFF_BASE_SECONDS = float(os.getenv("WARMUP_BACKOFF_BASE_SECONDS", "1.0"))
BACKOFF_MAX_SECONDS = float(os.getenv("WARMUP_BACKOFF_MAX_SECONDS", "8.0"))


def _is_embedding_model(model: str) -> bool:
    norm = str(model or "").strip().lower()
    if not norm:
        return False
    candidates = [
        os.getenv("LOCAL_EMBED_MODEL"),
        os.getenv("LOCAL_EMBEDDING_MODEL"),
        os.getenv("LOCAL_EMBEDDER_MODEL"),
        os.getenv("EMBEDDING_MODEL"),
        os.getenv("CODEXIFY_LOCAL_MODEL"),
    ]
    for candidate in candidates:
        if norm == str(candidate or "").strip().lower():
            return True
    return False


def _safe_publish(task_id: str, event_type: str, data: dict) -> None:
    try:
        task_events.publish(task_id, event_type, data)
    except Exception as exc:
        logger.warning("[warmup] failed to publish event: %s", exc)


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


def _run_task(task: WarmupTask) -> None:
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
    logger.info("[warmup] worker started queue=%s", QUEUE_NAME)
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
        _run_task(task)


if __name__ == "__main__":
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    run_forever()
