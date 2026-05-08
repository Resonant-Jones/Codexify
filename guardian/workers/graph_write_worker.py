"""Inspection-only worker scaffold for graph-write tasks.

This worker intentionally performs no persistence. It consumes derived
graph-write tasks, inspects their structure, and logs a deterministic summary
so future graph materialization can attach to a stable seam without changing
canonical behavior.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from guardian.memory_graph.graph_backend import (
    GRAPH_BACKEND_RESULT_STATUS_FAILED,
)
from guardian.memory_graph.graph_backend_factory import get_graph_backend
from guardian.memory_graph.graph_write_identity import (
    build_graph_write_identity,
)
from guardian.queue.graph_write_receipts import claim_graph_write_receipt
from guardian.queue.redis_queue import GRAPH_WRITE_QUEUE, get_redis_connection

logger = logging.getLogger(__name__)

GRAPH_WRITE_WORKER_SUMMARY_LOG = "graph_write_worker_inspected_task"
GRAPH_WRITE_WORKER_WARNING_LOG = "graph_write_worker_task_warnings"
GRAPH_WRITE_WORKER_DUPLICATE_LOG = "graph_write_worker_duplicate_task_skipped"
GRAPH_WRITE_WORKER_RECEIPT_CLAIM_FAILED_LOG = (
    "graph_write_worker_receipt_claim_failed"
)
GRAPH_WRITE_WORKER_BACKEND_RESULT_LOG = "graph_write_worker_backend_result"
GRAPH_WRITE_WORKER_BACKEND_FAILURE_LOG = "graph_write_worker_backend_failed"


def _coerce_mapping_list(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, (list, tuple)):
        return []
    result: list[dict[str, Any]] = []
    for item in raw:
        if isinstance(item, dict):
            result.append(dict(item))
    return result


def _coerce_warning_list(raw: Any) -> list[str]:
    if not isinstance(raw, (list, tuple)):
        return []
    result: list[str] = []
    for item in raw:
        value = str(item).strip()
        if value:
            result.append(value)
    return result


def _coerce_task_identity(
    task: dict[str, Any],
    *,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    warnings: list[str],
) -> dict[str, Any]:
    graph_write_id = str(task.get("graph_write_id") or "").strip()
    idempotency_key = str(task.get("idempotency_key") or "").strip()
    if graph_write_id and idempotency_key:
        return {
            "graph_write_id": graph_write_id,
            "idempotency_key": idempotency_key,
        }
    fallback = build_graph_write_identity(
        request_id=str(task.get("request_id") or ""),
        thread_id=task.get("thread_id") or "",
        candidate_trace_id=str(task.get("candidate_trace_id") or ""),
        nodes=nodes,
        edges=edges,
        warnings=warnings,
    )
    return {
        "graph_write_id": fallback["graph_write_id"],
        "idempotency_key": fallback["idempotency_key"],
    }


def process_graph_write_task(task: dict) -> None:
    if not isinstance(task, dict):
        logger.warning(
            "[graph-write] malformed task ignored task_type=%s",
            type(task).__name__,
        )
        return

    request_id = str(task.get("request_id") or "").strip()
    thread_id = task.get("thread_id")
    candidate_trace_id = str(task.get("candidate_trace_id") or "").strip()
    nodes = _coerce_mapping_list(task.get("nodes"))
    edges = _coerce_mapping_list(task.get("edges"))
    warnings = _coerce_warning_list(task.get("warnings"))
    identity = _coerce_task_identity(
        task,
        nodes=nodes,
        edges=edges,
        warnings=warnings,
    )
    graph_write_id = identity["graph_write_id"]
    idempotency_key = identity["idempotency_key"]

    try:
        redis = get_redis_connection()
    except Exception:
        logger.exception(
            f"[graph-write] {GRAPH_WRITE_WORKER_RECEIPT_CLAIM_FAILED_LOG}",
            extra={
                "request_id": request_id,
                "thread_id": thread_id,
                "candidate_trace_id": candidate_trace_id,
                "graph_write_id": graph_write_id,
                "idempotency_key": idempotency_key,
            },
        )
        return

    try:
        claimed = claim_graph_write_receipt(redis, idempotency_key)
    except Exception:
        logger.exception(
            f"[graph-write] {GRAPH_WRITE_WORKER_RECEIPT_CLAIM_FAILED_LOG}",
            extra={
                "request_id": request_id,
                "thread_id": thread_id,
                "candidate_trace_id": candidate_trace_id,
                "graph_write_id": graph_write_id,
                "idempotency_key": idempotency_key,
            },
        )
        return

    if not claimed:
        logger.info(
            f"[graph-write] {GRAPH_WRITE_WORKER_DUPLICATE_LOG}",
            extra={
                "request_id": request_id,
                "thread_id": thread_id,
                "candidate_trace_id": candidate_trace_id,
                "graph_write_id": graph_write_id,
                "idempotency_key": idempotency_key,
            },
        )
        return

    backend = get_graph_backend()
    backend_name = getattr(backend, "backend_kind", "unknown")

    node_types = sorted(
        {
            str(node.get("node_type") or "").strip()
            for node in nodes
            if str(node.get("node_type") or "").strip()
        }
    )
    edge_types = sorted(
        {
            str(edge.get("edge_type") or "").strip()
            for edge in edges
            if str(edge.get("edge_type") or "").strip()
        }
    )

    logger.info(
        f"[graph-write] {GRAPH_WRITE_WORKER_SUMMARY_LOG}",
        extra={
            "request_id": request_id,
            "thread_id": thread_id,
            "candidate_trace_id": candidate_trace_id,
            "graph_write_id": graph_write_id,
            "idempotency_key": idempotency_key,
            "node_count": len(nodes),
            "edge_count": len(edges),
            "warning_count": len(warnings),
            "node_types": node_types,
            "edge_types": edge_types,
            "backend_kind": backend_name,
        },
    )

    if warnings:
        logger.warning(
            f"[graph-write] {GRAPH_WRITE_WORKER_WARNING_LOG}",
            extra={
                "request_id": request_id,
                "thread_id": thread_id,
                "candidate_trace_id": candidate_trace_id,
                "warnings": list(warnings),
            },
        )

    try:
        backend_result = backend.write_graph_candidates(task)
    except Exception:
        logger.exception(
            f"[graph-write] {GRAPH_WRITE_WORKER_BACKEND_FAILURE_LOG}",
            extra={
                "request_id": request_id,
                "thread_id": thread_id,
                "candidate_trace_id": candidate_trace_id,
                "graph_write_id": graph_write_id,
                "idempotency_key": idempotency_key,
                "backend_kind": backend_name,
            },
        )
        return

    logger.info(
        f"[graph-write] {GRAPH_WRITE_WORKER_BACKEND_RESULT_LOG}",
        extra={
            "request_id": request_id,
            "thread_id": thread_id,
            "candidate_trace_id": candidate_trace_id,
            "graph_write_id": graph_write_id,
            "idempotency_key": idempotency_key,
            "backend_kind": backend_result.backend_kind,
            "backend_status": backend_result.status,
            "node_count": backend_result.node_count,
            "edge_count": backend_result.edge_count,
        },
    )

    if backend_result.status == GRAPH_BACKEND_RESULT_STATUS_FAILED:
        logger.warning(
            f"[graph-write] {GRAPH_WRITE_WORKER_BACKEND_FAILURE_LOG}",
            extra={
                "request_id": request_id,
                "thread_id": thread_id,
                "candidate_trace_id": candidate_trace_id,
                "graph_write_id": graph_write_id,
                "idempotency_key": idempotency_key,
                "backend_kind": backend_result.backend_kind,
                "backend_metadata": dict(backend_result.metadata),
            },
        )


def run_graph_write_worker() -> None:
    redis = get_redis_connection()
    logger.info("[graph-write] worker started queue=%s", GRAPH_WRITE_QUEUE)

    while True:
        result = redis.blpop(GRAPH_WRITE_QUEUE, timeout=5)
        if not result:
            time.sleep(0.2)
            continue

        _, raw = result
        try:
            decoded = json.loads(raw)
        except Exception:
            logger.exception("[graph-write] failed to decode task")
            continue

        try:
            process_graph_write_task(decoded)
        except Exception:
            logger.exception("[graph-write] task processing failed")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_graph_write_worker()


__all__ = [
    "GRAPH_WRITE_WORKER_SUMMARY_LOG",
    "GRAPH_WRITE_WORKER_WARNING_LOG",
    "GRAPH_WRITE_WORKER_DUPLICATE_LOG",
    "GRAPH_WRITE_WORKER_RECEIPT_CLAIM_FAILED_LOG",
    "GRAPH_WRITE_WORKER_BACKEND_RESULT_LOG",
    "GRAPH_WRITE_WORKER_BACKEND_FAILURE_LOG",
    "process_graph_write_task",
    "run_graph_write_worker",
]
