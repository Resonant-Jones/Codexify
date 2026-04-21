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

from guardian.core.candidate_normalizer import normalize_candidate_trace
from guardian.memory_graph.graph_candidate_mapper import (
    map_to_graph_write_candidates,
)
from guardian.queue.redis_queue import (
    CANDIDATE_INGEST_QUEUE,
    get_redis_connection,
)
from guardian.tasks.types import CandidateTraceIngestTask

logger = logging.getLogger(__name__)

NORMALIZATION_SUMMARY_LOG = "candidate_ingest_worker_normalized"
NORMALIZATION_WARNING_LOG = "candidate_ingest_worker_normalization_warnings"
GRAPH_CANDIDATE_SUMMARY_LOG = "candidate_ingest_worker_graph_candidates"
GRAPH_CANDIDATE_WARNING_LOG = "candidate_ingest_worker_graph_candidate_warnings"


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


def process_candidate_ingest_task(raw: Any) -> bool:
    normalized_task = _normalize_candidate_ingest_task(raw)
    if normalized_task is None:
        logger.warning(
            "[candidate-ingest] skipping malformed task raw=%r",
            raw,
        )
        return False

    request_id = normalized_task["request_id"]
    thread_id = normalized_task["thread_id"]
    candidate_trace_id = normalized_task["candidate_trace_id"]

    try:
        normalized = normalize_candidate_trace(normalized_task["payload"])
    except Exception:
        logger.exception(
            (
                "[candidate-ingest] normalization failed "
                "request_id=%s thread_id=%s candidate_trace_id=%s"
            ),
            request_id,
            thread_id,
            candidate_trace_id,
        )
        return False

    entity_types = sorted({entity.type for entity in normalized.entities})

    logger.info(
        f"[candidate-ingest] {NORMALIZATION_SUMMARY_LOG}",
        extra={
            "request_id": request_id,
            "thread_id": thread_id,
            "candidate_trace_id": candidate_trace_id,
            "entity_count": len(normalized.entities),
            "warning_count": len(normalized.warnings),
            "entity_types": entity_types,
        },
    )

    if normalized.warnings:
        logger.warning(
            f"[candidate-ingest] {NORMALIZATION_WARNING_LOG}",
            extra={
                "request_id": request_id,
                "thread_id": thread_id,
                "candidate_trace_id": candidate_trace_id,
                "warnings": list(normalized.warnings),
            },
        )

    try:
        graph_candidates = map_to_graph_write_candidates(normalized)
    except Exception:
        logger.exception(
            (
                "[candidate-ingest] graph candidate mapping failed "
                "request_id=%s thread_id=%s candidate_trace_id=%s"
            ),
            request_id,
            thread_id,
            candidate_trace_id,
        )
        return False

    node_types = sorted({node.node_type for node in graph_candidates.nodes})
    edge_types = sorted({edge.edge_type for edge in graph_candidates.edges})

    logger.info(
        f"[candidate-ingest] {GRAPH_CANDIDATE_SUMMARY_LOG}",
        extra={
            "request_id": request_id,
            "thread_id": thread_id,
            "candidate_trace_id": candidate_trace_id,
            "node_count": len(graph_candidates.nodes),
            "edge_count": len(graph_candidates.edges),
            "warning_count": len(graph_candidates.warnings),
            "node_types": node_types,
            "edge_types": edge_types,
        },
    )

    if graph_candidates.warnings:
        logger.warning(
            f"[candidate-ingest] {GRAPH_CANDIDATE_WARNING_LOG}",
            extra={
                "request_id": request_id,
                "thread_id": thread_id,
                "candidate_trace_id": candidate_trace_id,
                "warnings": list(graph_candidates.warnings),
            },
        )

    return True


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

        process_candidate_ingest_task(decoded)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_candidate_ingest_worker()


__all__ = [
    "NORMALIZATION_SUMMARY_LOG",
    "NORMALIZATION_WARNING_LOG",
    "GRAPH_CANDIDATE_SUMMARY_LOG",
    "GRAPH_CANDIDATE_WARNING_LOG",
    "process_candidate_ingest_task",
    "run_candidate_ingest_worker",
]
