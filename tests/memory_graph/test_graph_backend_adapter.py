from __future__ import annotations

from guardian.memory_graph.graph_backend import (
    GRAPH_BACKEND_RESULT_STATUS_FAILED,
    GRAPH_BACKEND_RESULT_STATUS_NOOP,
    GRAPH_BACKEND_RESULT_STATUS_SKIPPED,
    GRAPH_BACKEND_RESULT_STATUS_WRITTEN,
)
from guardian.memory_graph.noop_graph_backend import NoOpGraphBackend


def test_graph_backend_result_status_tokens_are_canonical() -> None:
    assert GRAPH_BACKEND_RESULT_STATUS_NOOP == "noop"
    assert GRAPH_BACKEND_RESULT_STATUS_SKIPPED == "skipped"
    assert GRAPH_BACKEND_RESULT_STATUS_WRITTEN == "written"
    assert GRAPH_BACKEND_RESULT_STATUS_FAILED == "failed"


def test_noop_graph_backend_returns_noop_result() -> None:
    backend = NoOpGraphBackend()
    result = backend.write_graph_candidates(
        {
            "graph_write_id": "gwr_1",
            "nodes": [{"node_key": "a"}],
            "edges": [{"edge_type": "REL"}],
        }
    )

    assert result.status == GRAPH_BACKEND_RESULT_STATUS_NOOP
    assert result.backend_kind == "noop"
    assert result.graph_write_id == "gwr_1"
    assert result.node_count == 1
    assert result.edge_count == 1
