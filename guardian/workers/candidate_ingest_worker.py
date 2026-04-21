"""Worker for candidate_trace ingestion scaffolding.

This worker intentionally performs no persistence. It only normalizes and logs
candidate-trace ingestion payloads so future graph/entity extraction can attach
to a stable seam without affecting chat completion.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from guardian.queue.redis_queue import (
    CANDIDATE_INGEST_QUEUE,
    get_redis_connection,
)
from guardian.tasks.types import CandidateTraceIngestTask

logger = logging.getLogger(__name__)


def _normalize_candidate_ingest_task(
    raw: Any,
) -> CandidateTraceIngestTask | None:
    if not isinstance(raw, dict):
        return None

    request_id = str(raw.get("request_id") or "").strip()
    candidate_trace_id = str(raw.get("candidate_trace_id") or "").strip()
    created_at = str(raw.get("created_at") or "").strip()
    try:
        thread_id = int(raw.get("thread_id"))
    except (TypeError, ValueError):
        return None

    payload = raw.get("payload")
    if (
        not request_id
        or thread_id <= 0
        or not candidate_trace_id
        or not created_at
        or not isinstance(payload, dict)
    ):
        return None

    return {
        "request_id": request_id,
        "thread_id": thread_id,
        "candidate_trace_id": candidate_trace_id,
        "created_at": created_at,
        "payload": dict(payload),
    }


def run_candidate_ingest_worker() -> None:
    redis = get_redis_connection()
    logger.info(
        "[candidate-ingest] worker started queue=%s",
        CANDIDATE_INGEST_QUEUE,
    )

    while True:
        result = redis.blpop(CANDIDATE_INGEST_QUEUE, timeout=5)
        if not result:
            time.sleep(0.2)
            continue

        _, raw = result
        try:
            decoded = json.loads(raw)
        except Exception:
            logger.exception("[candidate-ingest] failed to decode task")
            continue

        normalized = _normalize_candidate_ingest_task(decoded)
        if normalized is None:
            logger.warning(
                "[candidate-ingest] skipping malformed task raw=%r",
                decoded,
            )
            continue

        logger.info(
            "[candidate-ingest] received request_id=%s thread_id=%s candidate_trace_id=%s",
            normalized["request_id"],
            normalized["thread_id"],
            normalized["candidate_trace_id"],
        )
        logger.debug(
            "[candidate-ingest] normalized task=%s",
            json.dumps(
                {
                    "request_id": normalized["request_id"],
                    "thread_id": normalized["thread_id"],
                    "candidate_trace_id": normalized["candidate_trace_id"],
                    "created_at": normalized["created_at"],
                },
                sort_keys=True,
            ),
        )
        logger.debug(
            "[candidate-ingest] normalized candidate payload=%s",
            json.dumps(
                normalized["payload"],
                default=str,
                sort_keys=True,
            ),
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_candidate_ingest_worker()


__all__ = ["run_candidate_ingest_worker"]
