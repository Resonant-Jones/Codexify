"""Typed adapter contract for future graph persistence backends."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

GRAPH_BACKEND_RESULT_STATUS_NOOP = "noop"
GRAPH_BACKEND_RESULT_STATUS_SKIPPED = "skipped"


@dataclass
class GraphBackendWriteResult:
    status: str
    graph_write_id: str
    node_count: int
    edge_count: int
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class GraphBackendAdapter(Protocol):
    def write_graph_task(self, task: dict) -> GraphBackendWriteResult:
        ...


__all__ = [
    "GRAPH_BACKEND_RESULT_STATUS_NOOP",
    "GRAPH_BACKEND_RESULT_STATUS_SKIPPED",
    "GraphBackendAdapter",
    "GraphBackendWriteResult",
]
