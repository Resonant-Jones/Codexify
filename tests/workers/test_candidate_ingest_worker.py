from __future__ import annotations

import logging
from unittest.mock import MagicMock

from guardian.core.candidate_normalizer import (
    NormalizedEntity,
    NormalizedEntitySet,
)
from guardian.memory_graph.graph_candidate_mapper import (
    GraphEdgeCandidate,
    GraphNodeCandidate,
    GraphWriteCandidateSet,
)
from guardian.workers import candidate_ingest_worker


def _task(*, payload: dict[str, object]) -> dict[str, object]:
    return {
        "request_id": "req-1",
        "thread_id": 7,
        "candidate_trace_id": "trace-1",
        "created_at": "2026-01-01T00:00:00Z",
        "payload": payload,
    }


def _record_by_message(caplog, message: str):
    return next(
        record for record in caplog.records if record.getMessage() == message
    )


def test_candidate_ingest_worker_maps_graph_candidates_and_logs_summary(
    caplog,
):
    caplog.set_level(logging.INFO)

    ok = candidate_ingest_worker.process_candidate_ingest_task(
        _task(
            payload={
                "messages": [
                    {
                        "id": "msg-1",
                        "content": "Source message",
                    }
                ],
                "documents": [
                    {
                        "id": "doc-1",
                        "content": "Derived document",
                        "source_message_id": "msg-1",
                    }
                ],
            }
        )
    )

    assert ok is True
    summary = _record_by_message(
        caplog,
        f"[candidate-ingest] {candidate_ingest_worker.GRAPH_CANDIDATE_SUMMARY_LOG}",
    )
    assert summary.request_id == "req-1"
    assert summary.thread_id == 7
    assert summary.candidate_trace_id == "trace-1"
    assert summary.node_count == 2
    assert summary.edge_count == 1
    assert summary.warning_count == 0
    assert summary.node_types == ["Document", "Message"]
    assert summary.edge_types == ["DERIVED_FROM"]


def test_candidate_ingest_worker_logs_graph_candidate_warnings(caplog):
    caplog.set_level(logging.INFO)

    ok = candidate_ingest_worker.process_candidate_ingest_task(
        _task(
            payload={
                "graph": [
                    {
                        "content": "Graph fragment",
                        "confidence": 0.7,
                    }
                ]
            }
        )
    )

    assert ok is True
    summary = _record_by_message(
        caplog,
        f"[candidate-ingest] {candidate_ingest_worker.GRAPH_CANDIDATE_SUMMARY_LOG}",
    )
    warning = _record_by_message(
        caplog,
        f"[candidate-ingest] {candidate_ingest_worker.GRAPH_CANDIDATE_WARNING_LOG}",
    )
    assert summary.node_count == 1
    assert summary.edge_count == 0
    assert summary.warning_count == 1
    assert summary.node_types == ["Unknown"]
    assert summary.edge_types == []
    assert warning.warnings == ["unknown_entity_type"]


def test_candidate_ingest_worker_survives_graph_mapping_failure(
    caplog, monkeypatch
):
    caplog.set_level(logging.INFO)

    monkeypatch.setattr(
        candidate_ingest_worker,
        "map_to_graph_write_candidates",
        MagicMock(side_effect=RuntimeError("boom")),
    )

    ok = candidate_ingest_worker.process_candidate_ingest_task(
        _task(
            payload={
                "documents": [
                    {
                        "id": "doc-1",
                        "content": "Recovered document",
                    }
                ]
            }
        )
    )

    assert ok is False
    assert any(
        record.levelno >= logging.ERROR
        and "graph candidate mapping failed" in record.getMessage()
        for record in caplog.records
    )


def test_candidate_ingest_worker_still_does_not_persist_or_enqueue_follow_on_work(
    monkeypatch,
):
    normalized = NormalizedEntitySet(
        entities=[
            NormalizedEntity(
                type="document",
                content="Recovered document",
                source="retrieval",
                confidence=0.8,
                metadata={"field": "documents", "thread_id": "thread-1"},
            )
        ],
        warnings=[],
    )
    graph_candidates = GraphWriteCandidateSet(
        nodes=[
            GraphNodeCandidate(
                node_key="graph:document:1",
                node_type="Document",
                source_type="retrieval",
                source_id="doc-1",
                content="Recovered document",
                metadata={"normalized_type": "document"},
            )
        ],
        edges=[
            GraphEdgeCandidate(
                edge_type="PART_OF_THREAD",
                from_node_key="graph:document:1",
                to_node_key="graph:thread:1",
                metadata={"thread_id": "thread-1"},
            )
        ],
        warnings=[],
    )
    normalize_spy = MagicMock(return_value=normalized)
    map_spy = MagicMock(return_value=graph_candidates)
    queue_spy = MagicMock(
        side_effect=AssertionError("queue fan-out not expected")
    )
    persistence_spy = MagicMock(
        side_effect=AssertionError("canonical persistence not expected")
    )

    monkeypatch.setattr(
        candidate_ingest_worker,
        "normalize_candidate_trace",
        normalize_spy,
    )
    monkeypatch.setattr(
        candidate_ingest_worker,
        "map_to_graph_write_candidates",
        map_spy,
    )
    monkeypatch.setattr(
        candidate_ingest_worker,
        "get_redis_connection",
        queue_spy,
    )
    monkeypatch.setattr(
        candidate_ingest_worker,
        "store_candidate_trace",
        persistence_spy,
        raising=False,
    )

    ok = candidate_ingest_worker.process_candidate_ingest_task(
        _task(
            payload={
                "documents": [
                    {
                        "content": "Recovered document",
                    }
                ]
            }
        )
    )

    assert ok is True
    normalize_spy.assert_called_once()
    map_spy.assert_called_once()
    queue_spy.assert_not_called()
    persistence_spy.assert_not_called()
