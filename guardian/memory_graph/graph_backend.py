"""Typed adapter contract for future graph persistence backends."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

GRAPH_BACKEND_KIND_NOOP = "noop"
GRAPH_BACKEND_KIND_NEO4J = "neo4j"
SUPPORTED_GRAPH_BACKEND_KINDS: tuple[str, ...] = (
    GRAPH_BACKEND_KIND_NOOP,
    GRAPH_BACKEND_KIND_NEO4J,
)

GRAPH_BACKEND_RESULT_STATUS_NOOP = "noop"
GRAPH_BACKEND_RESULT_STATUS_SKIPPED = "skipped"
GRAPH_BACKEND_RESULT_STATUS_WRITTEN = "written"
GRAPH_BACKEND_RESULT_STATUS_FAILED = "failed"


@dataclass(frozen=True)
class GraphBackendWriteResult:
    status: str
    graph_write_id: str
    node_count: int
    edge_count: int
    backend_kind: str = ""
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class GraphBackendAdapter(Protocol):
    backend_kind: str

    def write_graph_candidates(
        self, graph_write_task: dict[str, Any]
    ) -> GraphBackendWriteResult:
        ...

    def write_graph_task(self, task: dict) -> GraphBackendWriteResult:
        ...


__all__ = [
    "GRAPH_BACKEND_KIND_NEO4J",
    "GRAPH_BACKEND_KIND_NOOP",
    "GRAPH_BACKEND_RESULT_STATUS_FAILED",
    "GRAPH_BACKEND_RESULT_STATUS_NOOP",
    "GRAPH_BACKEND_RESULT_STATUS_SKIPPED",
    "GRAPH_BACKEND_RESULT_STATUS_WRITTEN",
    "SUPPORTED_GRAPH_BACKEND_KINDS",
    "GraphBackendAdapter",
    "GraphBackendWriteResult",
]
