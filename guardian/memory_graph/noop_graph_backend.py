"""Default no-op graph backend implementations."""

from __future__ import annotations

from typing import Any

from guardian.memory_graph.graph_backend import (
    GRAPH_BACKEND_KIND_NOOP,
    GRAPH_BACKEND_RESULT_STATUS_NOOP,
    GRAPH_BACKEND_RESULT_STATUS_SKIPPED,
    GraphBackendAdapter,
    GraphBackendWriteResult,
)


class NoOpGraphBackend:
    backend_kind = GRAPH_BACKEND_KIND_NOOP

    def write_graph_candidates(
        self, graph_write_task: dict[str, Any]
    ) -> GraphBackendWriteResult:
        graph_write_id = str(
            graph_write_task.get("graph_write_id") or ""
        ).strip()
        nodes = graph_write_task.get("nodes")
        edges = graph_write_task.get("edges")
        node_count = len(nodes) if isinstance(nodes, list) else 0
        edge_count = len(edges) if isinstance(edges, list) else 0
        return GraphBackendWriteResult(
            status=GRAPH_BACKEND_RESULT_STATUS_NOOP,
            backend_kind=self.backend_kind,
            graph_write_id=graph_write_id,
            node_count=node_count,
            edge_count=edge_count,
            metadata={"reason": "graph_writes_disabled"},
        )


_NOOP_GRAPH_BACKEND_ADAPTER: GraphBackendAdapter | None = None


def _coerce_int(raw: Any) -> int:
    try:
        return max(0, int(raw))
    except (TypeError, ValueError):
        return 0


def _coerce_list(raw: Any) -> list:
    return list(raw) if isinstance(raw, (list, tuple)) else []


class NoopGraphBackendAdapter:
    """Adapter placeholder that preserves the graph lane's current behavior."""

    def write_graph_task(self, task: dict) -> GraphBackendWriteResult:
        if not isinstance(task, dict):
            return GraphBackendWriteResult(
                status=GRAPH_BACKEND_RESULT_STATUS_SKIPPED,
                graph_write_id="",
                node_count=0,
                edge_count=0,
                warnings=["invalid_task_type"],
                metadata={"task_type": type(task).__name__},
            )

        return GraphBackendWriteResult(
            status=GRAPH_BACKEND_RESULT_STATUS_NOOP,
            graph_write_id=str(task.get("graph_write_id") or "").strip(),
            node_count=_coerce_int(
                task.get("node_count") or len(_coerce_list(task.get("nodes")))
            ),
            edge_count=_coerce_int(
                task.get("edge_count") or len(_coerce_list(task.get("edges")))
            ),
            warnings=_coerce_list(task.get("warnings")),
            metadata={
                "request_id": str(task.get("request_id") or "").strip(),
                "thread_id": task.get("thread_id"),
                "candidate_trace_id": str(
                    task.get("candidate_trace_id") or ""
                ).strip(),
                "idempotency_key": str(
                    task.get("idempotency_key") or ""
                ).strip(),
                "receipt_status": str(task.get("receipt_status") or "").strip(),
            },
        )


def get_graph_backend_adapter() -> GraphBackendAdapter:
    global _NOOP_GRAPH_BACKEND_ADAPTER
    if _NOOP_GRAPH_BACKEND_ADAPTER is None:
        _NOOP_GRAPH_BACKEND_ADAPTER = NoopGraphBackendAdapter()
    return _NOOP_GRAPH_BACKEND_ADAPTER


__all__ = [
    "NoOpGraphBackend",
    "NoopGraphBackendAdapter",
    "get_graph_backend_adapter",
]
