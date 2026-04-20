from __future__ import annotations

import logging
from unittest.mock import MagicMock

from guardian.core.candidate_normalizer import (
    NormalizedEntity,
    NormalizedEntitySet,
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


def test_candidate_ingest_worker_normalizes_payload_and_logs_summary(
    caplog,
):
    caplog.set_level(logging.INFO)

    ok = candidate_ingest_worker.process_candidate_ingest_task(
        _task(
            payload={
                "documents": [
                    {
                        "id": "doc-1",
                        "content": "Document body",
                        "confidence": 0.9,
                    }
                ]
            }
        )
    )

    assert ok is True
    summary = next(
        record
        for record in caplog.records
        if record.getMessage()
        == "[candidate-ingest] candidate_ingest_worker_normalized"
    )
    assert summary.request_id == "req-1"
    assert summary.thread_id == 7
    assert summary.candidate_trace_id == "trace-1"
    assert summary.entity_count == 1
    assert summary.warning_count == 0
    assert summary.entity_types == ["document"]


def test_candidate_ingest_worker_logs_normalization_warnings_for_empty_payload(
    caplog,
):
    caplog.set_level(logging.INFO)

    ok = candidate_ingest_worker.process_candidate_ingest_task(
        _task(payload={})
    )

    assert ok is True
    summary = next(
        record
        for record in caplog.records
        if record.getMessage()
        == "[candidate-ingest] candidate_ingest_worker_normalized"
    )
    warning = next(
        record
        for record in caplog.records
        if record.getMessage()
        == "[candidate-ingest] candidate_ingest_worker_normalization_warnings"
    )
    assert summary.entity_count == 0
    assert summary.warning_count == 1
    assert summary.entity_types == []
    assert warning.warnings == ["empty_candidate_trace"]


def test_candidate_ingest_worker_survives_malformed_payload(caplog):
    caplog.set_level(logging.INFO)

    ok = candidate_ingest_worker.process_candidate_ingest_task(
        _task(
            payload={
                "documents": [
                    {},
                    {
                        "content": "Recovered document",
                        "confidence": 0.8,
                    },
                ]
            }
        )
    )

    assert ok is True
    summary = next(
        record
        for record in caplog.records
        if record.getMessage()
        == "[candidate-ingest] candidate_ingest_worker_normalized"
    )
    warning = next(
        record
        for record in caplog.records
        if record.getMessage()
        == "[candidate-ingest] candidate_ingest_worker_normalization_warnings"
    )
    assert summary.entity_count == 1
    assert summary.warning_count == 1
    assert summary.entity_types == ["document"]
    assert "malformed_candidate_entry" in warning.warnings


def test_candidate_ingest_worker_does_not_persist_or_enqueue_follow_on_work(
    monkeypatch,
):
    normalized = NormalizedEntitySet(
        entities=[
            NormalizedEntity(
                type="document",
                content="Recovered document",
                source="retrieval",
                confidence=0.8,
                metadata={"field": "documents"},
            )
        ],
        warnings=[],
    )
    normalize_spy = MagicMock(return_value=normalized)
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
    queue_spy.assert_not_called()
    persistence_spy.assert_not_called()
