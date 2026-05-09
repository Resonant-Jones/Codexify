from __future__ import annotations

from guardian.memory_graph.graph_backend import (
    GRAPH_BACKEND_RESULT_STATUS_FAILED,
    GRAPH_BACKEND_RESULT_STATUS_NOOP,
    GRAPH_BACKEND_RESULT_STATUS_SKIPPED,
    GRAPH_BACKEND_RESULT_STATUS_WRITTEN,
    GraphBackendWriteResult,
)
from guardian.memory_graph.noop_graph_backend import (
    NoOpGraphBackend,
    NoopGraphBackendAdapter,
    get_graph_backend_adapter,
)


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


def test_noop_graph_backend_adapter_returns_noop_result():
    adapter = NoopGraphBackendAdapter()
    result = adapter.write_graph_task(
        {
            "graph_write_id": "gwr-1",
            "nodes": [{}, {}],
            "edges": [{}],
            "warnings": ["one"],
            "request_id": "req-1",
            "thread_id": 7,
            "candidate_trace_id": "trace-1",
            "idempotency_key": "graph-write:1",
            "receipt_status": "claimed",
        }
    )

    assert isinstance(result, GraphBackendWriteResult)
    assert result.status == GRAPH_BACKEND_RESULT_STATUS_NOOP
    assert result.graph_write_id == "gwr-1"
    assert result.node_count == 2
    assert result.edge_count == 1
    assert result.warnings == ["one"]
    assert result.metadata["request_id"] == "req-1"
    assert result.metadata["thread_id"] == 7


def test_noop_graph_backend_adapter_skips_non_dict_payload():
    adapter = NoopGraphBackendAdapter()
    result = adapter.write_graph_task("not-a-dict")

    assert result.status == GRAPH_BACKEND_RESULT_STATUS_SKIPPED
    assert result.graph_write_id == ""
    assert result.node_count == 0
    assert result.edge_count == 0
    assert result.warnings == ["invalid_task_type"]


def test_graph_backend_adapter_factory_returns_default_noop_adapter():
    adapter_one = get_graph_backend_adapter()
    adapter_two = get_graph_backend_adapter()

    assert adapter_one is adapter_two
