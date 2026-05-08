from __future__ import annotations

import logging
from unittest.mock import MagicMock

from guardian.memory_graph.graph_backend import (
    GRAPH_BACKEND_RESULT_STATUS_FAILED,
    GRAPH_BACKEND_RESULT_STATUS_NOOP,
    GRAPH_BACKEND_RESULT_STATUS_WRITTEN,
from guardian.core import graph_write_inspection_store
from guardian.core.graph_write_inspection_store import (
    GRAPH_WRITE_INSPECTION_STATUS_CLAIMED,
    GRAPH_WRITE_INSPECTION_STATUS_DUPLICATE_SKIPPED,
)
from guardian.memory_graph.graph_backend import (
    GRAPH_BACKEND_RESULT_STATUS_NOOP,
    GraphBackendWriteResult,
)
from guardian.workers import graph_write_worker


class _FakeReceiptRedis:
    def __init__(
        self, results: list[bool | None] | None = None, *, failure=None
    ):
        self.results = list(results or [])
        self.failure = failure
        self.calls: list[tuple[str, str, int | None, bool]] = []

    def set(self, key, value, ex=None, nx=False):
        self.calls.append((key, value, ex, nx))
        if self.failure is not None:
            raise self.failure
        if self.results:
            return self.results.pop(0)
        return True


class _BackendSpy:
    def __init__(
        self, result: GraphBackendWriteResult | None = None, *, failure=None
    ):
        self.result = result
        self.failure = failure
        self.calls: list[dict] = []
        self.backend_kind = "neo4j"

    def write_graph_candidates(self, task: dict):
        self.calls.append(dict(task))
        if self.failure is not None:
            raise self.failure
        return self.result


def _task() -> dict[str, object]:
    return {
        "request_id": "req-1",
        "thread_id": 7,
        "candidate_trace_id": "trace-1",
        "created_at": "2026-01-01T00:00:00Z",
        "graph_write_id": "gwr_test_identity",
        "idempotency_key": "graph-write:trace-1:fingerprint-1",
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


def test_graph_write_worker_stores_inspection_snapshot_for_first_seen_task(
    caplog, monkeypatch
):
    caplog.set_level(logging.INFO)
    redis_client = _FakeReceiptRedis(results=[True])
    get_redis_connection_spy = MagicMock(return_value=redis_client)
    monkeypatch.setattr(
        graph_write_worker,
        "get_redis_connection",
        get_redis_connection_spy,
    )
    backend = _BackendSpy(
        GraphBackendWriteResult(
            status=GRAPH_BACKEND_RESULT_STATUS_NOOP,
            backend_kind="noop",
            graph_write_id="gwr_test_identity",
            node_count=1,
            edge_count=1,
            metadata={},
        )
    )
    monkeypatch.setattr(
        graph_write_worker, "get_graph_backend", lambda: backend
    graph_backend_adapter = MagicMock(
        write_graph_task=MagicMock(
            return_value=GraphBackendWriteResult(
                status=GRAPH_BACKEND_RESULT_STATUS_NOOP,
                graph_write_id="gwr_test_identity",
                node_count=1,
                edge_count=1,
            )
        )
    )
    monkeypatch.setattr(
        graph_write_worker,
        "get_graph_backend_adapter",
        MagicMock(return_value=graph_backend_adapter),
    )

    graph_write_worker.process_graph_write_task(_task())

    get_redis_connection_spy.assert_called_once()
    assert len(redis_client.calls) == 1
    receipt_key, receipt_value, ttl, nx = redis_client.calls[0]
    assert receipt_key == (
        "codexify:graph-write:receipt:graph-write:trace-1:fingerprint-1"
    )
    assert receipt_value == "claimed"
    assert ttl == 3600
    assert nx is True

    summary = _record_by_message(
        caplog,
        f"[graph-write] {graph_write_worker.GRAPH_WRITE_WORKER_SUMMARY_LOG}",
    )
    assert summary.request_id == "req-1"
    assert summary.thread_id == 7
    assert summary.candidate_trace_id == "trace-1"
    assert summary.graph_write_id == "gwr_test_identity"
    assert summary.idempotency_key == "graph-write:trace-1:fingerprint-1"
    assert summary.node_count == 1
    assert summary.edge_count == 1
    assert summary.warning_count == 0
    assert summary.node_types == ["Document"]
    assert summary.edge_types == ["PART_OF_THREAD"]
    graph_backend_adapter.write_graph_task.assert_called_once()

    snapshot = graph_write_inspection_store.get_latest_graph_write_inspection(7)
    assert snapshot is not None
    assert snapshot["thread_id"] == 7
    assert snapshot["graph_write_id"] == "gwr_test_identity"
    assert snapshot["receipt_status"] == GRAPH_WRITE_INSPECTION_STATUS_CLAIMED
    assert snapshot["node_count"] == 1
    assert snapshot["edge_count"] == 1
    assert snapshot["warning_count"] == 0
    assert snapshot["node_types"] == ["Document"]
    assert snapshot["edge_types"] == ["PART_OF_THREAD"]


def test_graph_write_worker_uses_noop_backend_by_default(monkeypatch):
    redis_client = _FakeReceiptRedis(results=[True])
    monkeypatch.setattr(
        graph_write_worker,
        "get_redis_connection",
        MagicMock(return_value=redis_client),
    )

    backend = _BackendSpy(
        GraphBackendWriteResult(
            status=GRAPH_BACKEND_RESULT_STATUS_NOOP,
            backend_kind="noop",
            graph_write_id="gwr_test_identity",
            node_count=1,
            edge_count=1,
            metadata={},
        )
    )
    monkeypatch.setattr(
        graph_write_worker, "get_graph_backend", lambda: backend
    )

    graph_write_worker.process_graph_write_task(_task())

    assert len(backend.calls) == 1


def test_graph_write_worker_calls_neo4j_backend_when_explicitly_enabled(
    monkeypatch,
):
    redis_client = _FakeReceiptRedis(results=[True])
    monkeypatch.setattr(
        graph_write_worker,
        "get_redis_connection",
        MagicMock(return_value=redis_client),
    )
    backend = _BackendSpy(
        GraphBackendWriteResult(
            status=GRAPH_BACKEND_RESULT_STATUS_WRITTEN,
            backend_kind="neo4j",
            graph_write_id="gwr_test_identity",
            node_count=1,
            edge_count=1,
            metadata={},
        )
    )
    monkeypatch.setattr(
        graph_write_worker, "get_graph_backend", lambda: backend
    )

    graph_write_worker.process_graph_write_task(_task())

    assert len(backend.calls) == 1


def test_graph_write_worker_duplicate_task_still_skips_before_backend_call(
    monkeypatch,
def test_graph_write_worker_stores_duplicate_skipped_snapshot(
    caplog, monkeypatch
):
    redis_client = _FakeReceiptRedis(results=[True, False])
    graph_backend_adapter = MagicMock(
        write_graph_task=MagicMock(
            return_value=GraphBackendWriteResult(
                status=GRAPH_BACKEND_RESULT_STATUS_NOOP,
                graph_write_id="gwr_test_identity",
                node_count=1,
                edge_count=1,
            )
        )
    )
    monkeypatch.setattr(
        graph_write_worker,
        "get_redis_connection",
        MagicMock(return_value=redis_client),
    )
    backend = _BackendSpy(
        GraphBackendWriteResult(
            status=GRAPH_BACKEND_RESULT_STATUS_WRITTEN,
            backend_kind="neo4j",
            graph_write_id="gwr_test_identity",
            node_count=1,
            edge_count=1,
            metadata={},
        )
    )
    monkeypatch.setattr(
        graph_write_worker, "get_graph_backend", lambda: backend
    monkeypatch.setattr(
        graph_write_worker,
        "get_graph_backend_adapter",
        MagicMock(return_value=graph_backend_adapter),
    )

    task = _task()
    graph_write_worker.process_graph_write_task(task)
    graph_write_worker.process_graph_write_task(task)

    assert len(backend.calls) == 1
    summary_records = [
        record
        for record in caplog.records
        if record.getMessage()
        == f"[graph-write] {graph_write_worker.GRAPH_WRITE_WORKER_SUMMARY_LOG}"
    ]
    duplicate_record = _record_by_message(
        caplog,
        f"[graph-write] {graph_write_worker.GRAPH_WRITE_WORKER_DUPLICATE_LOG}",
    )
    snapshot = graph_write_inspection_store.get_latest_graph_write_inspection(7)

    assert len(summary_records) == 1
    assert duplicate_record.request_id == "req-1"
    assert duplicate_record.thread_id == 7
    assert duplicate_record.candidate_trace_id == "trace-1"
    assert duplicate_record.graph_write_id == "gwr_test_identity"
    assert (
        duplicate_record.idempotency_key == "graph-write:trace-1:fingerprint-1"
    )
    assert graph_backend_adapter.write_graph_task.call_count == 1
    assert snapshot is not None
    assert snapshot["receipt_status"] == (
        GRAPH_WRITE_INSPECTION_STATUS_DUPLICATE_SKIPPED
    )
    assert snapshot["thread_id"] == 7
    assert snapshot["graph_write_id"] == "gwr_test_identity"


def test_graph_write_worker_contains_snapshot_store_failure(
    caplog, monkeypatch
):
    caplog.set_level(logging.INFO)
    redis_client = _FakeReceiptRedis(results=[True])
    monkeypatch.setattr(
        graph_write_worker,
        "get_redis_connection",
        MagicMock(return_value=redis_client),
    )
    monkeypatch.setattr(
        graph_write_worker,
        "store_graph_write_inspection_snapshot",
        MagicMock(side_effect=RuntimeError("snapshot store failed")),
    )

    graph_write_worker.process_graph_write_task(_task())

    assert any(
        record.levelno >= logging.ERROR
        and graph_write_worker.GRAPH_WRITE_WORKER_INSPECTION_STORE_FAILED_LOG
        in record.getMessage()
        for record in caplog.records
    )
    assert any(
        record.getMessage()
        == f"[graph-write] {graph_write_worker.GRAPH_WRITE_WORKER_SUMMARY_LOG}"
        for record in caplog.records
    )


def test_graph_write_worker_contains_receipt_claim_failure(caplog, monkeypatch):
    caplog.set_level(logging.INFO)
    redis_client = _FakeReceiptRedis(failure=RuntimeError("redis down"))
    monkeypatch.setattr(
        graph_write_worker,
        "get_redis_connection",
        MagicMock(return_value=redis_client),
    )

    graph_write_worker.process_graph_write_task(_task())

    assert any(
        record.levelno >= logging.ERROR
        and graph_write_worker.GRAPH_WRITE_WORKER_RECEIPT_CLAIM_FAILED_LOG
        in record.getMessage()
        for record in caplog.records
    )


def test_graph_write_worker_contains_neo4j_backend_failure(caplog, monkeypatch):
    caplog.set_level(logging.INFO)
    redis_client = _FakeReceiptRedis(results=[True])
    monkeypatch.setattr(
        graph_write_worker,
        "get_redis_connection",
        MagicMock(return_value=redis_client),
    )
    backend = _BackendSpy(failure=RuntimeError("driver down"))
    monkeypatch.setattr(
        graph_write_worker, "get_graph_backend", lambda: backend
    )

    graph_write_worker.process_graph_write_task(_task())

    assert len(backend.calls) == 1
    assert any(
        graph_write_worker.GRAPH_WRITE_WORKER_BACKEND_FAILURE_LOG
        in record.getMessage()
        for record in caplog.records
    )


def test_graph_write_worker_logs_failed_backend_result(caplog, monkeypatch):
    caplog.set_level(logging.INFO)
    redis_client = _FakeReceiptRedis(results=[True])
    monkeypatch.setattr(
        graph_write_worker,
        "get_redis_connection",
        MagicMock(return_value=redis_client),
    )
    backend = _BackendSpy(
        GraphBackendWriteResult(
            status=GRAPH_BACKEND_RESULT_STATUS_FAILED,
            backend_kind="neo4j",
            graph_write_id="gwr_test_identity",
            metadata={"reason": "neo4j_write_failed"},
        )
    )
    monkeypatch.setattr(
        graph_write_worker, "get_graph_backend", lambda: backend
    graph_backend_spy = MagicMock(
        return_value=GraphBackendWriteResult(
            status=GRAPH_BACKEND_RESULT_STATUS_NOOP,
            graph_write_id="gwr_test_identity",
            node_count=1,
            edge_count=1,
        )
    )
    monkeypatch.setattr(
        graph_write_worker,
        "get_graph_backend_adapter",
        graph_backend_spy,
    )

    graph_write_worker.process_graph_write_task(_task())

    assert any(
        graph_write_worker.GRAPH_WRITE_WORKER_BACKEND_RESULT_LOG
        in record.getMessage()
        for record in caplog.records
    )
    assert len(redis_client.calls) == 1
    graph_backend_spy.assert_called_once()
