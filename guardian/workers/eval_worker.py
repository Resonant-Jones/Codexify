"""Best-effort post-completion evaluation worker."""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

from guardian.core import dependencies
from guardian.evals.groundedness import evaluate_groundedness
from guardian.evals.spine import (
    EVAL_QUEUE_NAME,
    build_verdict_record,
    get_trace_snapshot_by_id,
    persist_eval_verdicts,
)
from guardian.queue.redis_queue import dequeue, get_redis_connection
from guardian.tasks.types import EvalTask, task_from_dict

logger = logging.getLogger(__name__)


def _task_dict(task: Any) -> dict[str, Any]:
    if isinstance(task, dict):
        return dict(task)
    to_dict = getattr(task, "to_dict", None)
    if callable(to_dict):
        return dict(to_dict())
    return dict(getattr(task, "__dict__", {}))


def process_eval_task(task: EvalTask) -> dict[str, Any] | None:
    chatlog_db = getattr(dependencies, "chatlog_db", None)
    if chatlog_db is None:
        logger.warning("[eval] chatlog_db unavailable; skipping task")
        return None

    trace_snapshot_id = str(
        getattr(task, "trace_snapshot_id", "") or ""
    ).strip()
    if not trace_snapshot_id:
        logger.warning(
            "[eval] missing trace_snapshot_id task_id=%s", task.task_id
        )
        return None

    trace_snapshot = get_trace_snapshot_by_id(
        chatlog_db,
        trace_snapshot_id=trace_snapshot_id,
    )
    if not trace_snapshot:
        logger.warning(
            "[eval] trace snapshot missing trace_snapshot_id=%s task_id=%s",
            trace_snapshot_id,
            task.task_id,
        )
        return None

    try:
        verdict = evaluate_groundedness(trace_snapshot)
        record = build_verdict_record(
            eval_task=task,
            trace_snapshot=trace_snapshot,
            verdict=verdict,
        )
        persisted = persist_eval_verdicts(chatlog_db, [record])
    except Exception:
        logger.warning(
            "[eval] task failed trace_snapshot_id=%s task_id=%s",
            trace_snapshot_id,
            task.task_id,
            exc_info=True,
        )
        return None
    if not persisted:
        logger.warning(
            "[eval] verdict persistence returned no rows trace_snapshot_id=%s task_id=%s",
            trace_snapshot_id,
            task.task_id,
        )
        return None
    return {
        "trace_snapshot": trace_snapshot,
        "verdicts": persisted,
    }


def run_eval_worker() -> None:
    redis = get_redis_connection()
    logger.info("[eval] worker started queue=%s", EVAL_QUEUE_NAME)

    while True:
        result = redis.blpop(EVAL_QUEUE_NAME, timeout=5)
        if not result:
            time.sleep(0.2)
            continue

        _, raw = result
        try:
            decoded = json.loads(raw)
        except Exception:
            logger.exception("[eval] failed to decode task")
            continue

        try:
            task = task_from_dict(decoded)
        except Exception:
            logger.exception("[eval] failed to parse task payload")
            continue

        if not isinstance(task, EvalTask):
            logger.debug(
                "[eval] skipping non-eval task type=%s",
                getattr(task, "type", ""),
            )
            continue

        try:
            process_eval_task(task)
        except Exception:
            logger.exception("[eval] task processing failed")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_eval_worker()


__all__ = ["process_eval_task", "run_eval_worker"]
