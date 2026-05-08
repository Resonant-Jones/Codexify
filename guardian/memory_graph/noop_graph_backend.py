"""Default graph backend that intentionally performs no persistence."""

from __future__ import annotations

from typing import Any

from guardian.memory_graph.graph_backend import (
    GRAPH_BACKEND_KIND_NOOP,
    GRAPH_BACKEND_RESULT_STATUS_NOOP,
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


__all__ = ["NoOpGraphBackend"]
