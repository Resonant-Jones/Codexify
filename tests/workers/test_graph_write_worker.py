from __future__ import annotations

import logging
from unittest.mock import MagicMock

from guardian.workers import graph_write_worker


def _task() -> dict[str, object]:
    return {
        "request_id": "req-1",
        "thread_id": 7,
        "candidate_trace_id": "trace-1",
        "created_at": "2026-01-01T00:00:00Z",
        "nodes": [
            {
                "node_key": "graph:document:1",
                "node_type": "Document",
                "source_type": "retrieval",
                "source_id": "doc-1",
                "content": "Project brief",
                "metadata": {"thread_id": "thread-1"},
            }
        ],
        "edges": [
            {
                "edge_type": "PART_OF_THREAD",
                "from_node_key": "graph:document:1",
                "to_node_key": "graph:thread:1",
                "metadata": {"thread_id": "thread-1"},
            }
        ],
        "warnings": [],
    }


def _record_by_message(caplog, message: str):
    return next(
        record for record in caplog.records if record.getMessage() == message
    )


def test_graph_write_worker_logs_summary_for_valid_task(caplog):
    caplog.set_level(logging.INFO)

    graph_write_worker.process_graph_write_task(_task())

    summary = _record_by_message(
        caplog,
        f"[graph-write] {graph_write_worker.GRAPH_WRITE_WORKER_SUMMARY_LOG}",
    )
    assert summary.request_id == "req-1"
    assert summary.thread_id == 7
    assert summary.candidate_trace_id == "trace-1"
    assert summary.node_count == 1
    assert summary.edge_count == 1
    assert summary.warning_count == 0
    assert summary.node_types == ["Document"]
    assert summary.edge_types == ["PART_OF_THREAD"]


def test_graph_write_worker_logs_warnings_when_present(caplog):
    caplog.set_level(logging.INFO)

    task = _task()
    task["warnings"] = ["ambiguous_relationship"]

    graph_write_worker.process_graph_write_task(task)

    warning = _record_by_message(
        caplog,
        f"[graph-write] {graph_write_worker.GRAPH_WRITE_WORKER_WARNING_LOG}",
    )
    assert warning.warnings == ["ambiguous_relationship"]


def test_graph_write_worker_survives_malformed_task(caplog):
    caplog.set_level(logging.WARNING)

    graph_write_worker.process_graph_write_task(None)

    assert any(
        "malformed task ignored" in record.getMessage()
        for record in caplog.records
    )


def test_graph_write_worker_does_not_persist_or_call_graph_backend(
    monkeypatch,
):
    enqueue_spy = MagicMock(
        side_effect=AssertionError("queue fan-out not expected")
    )
    redis_spy = MagicMock(
        side_effect=AssertionError("redis client not expected")
    )
    graph_backend_spy = MagicMock(
        side_effect=AssertionError("graph backend not expected")
    )

    monkeypatch.setattr(
        graph_write_worker,
        "enqueue",
        enqueue_spy,
        raising=False,
    )
    monkeypatch.setattr(
        graph_write_worker,
        "get_redis_connection",
        redis_spy,
    )
    monkeypatch.setattr(
        graph_write_worker,
        "write_graph_candidates",
        graph_backend_spy,
        raising=False,
    )

    graph_write_worker.process_graph_write_task(_task())

    enqueue_spy.assert_not_called()
    redis_spy.assert_not_called()
    graph_backend_spy.assert_not_called()
