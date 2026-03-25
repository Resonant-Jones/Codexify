import logging

import pytest

from guardian.queue.redis_queue import QueueEnqueueError


def _build_enqueue_error(
    queue_name: str,
) -> tuple[QueueEnqueueError, Exception]:
    cause = RuntimeError("redis down")
    try:
        raise cause
    except Exception as exc:
        try:
            raise QueueEnqueueError(queue_name, cause=exc) from exc
        except QueueEnqueueError as err:
            return err, cause


def test_chat_complete_enqueue_failure_returns_503(
    test_client, mock_db, monkeypatch, caplog
):
    error, cause = _build_enqueue_error("codexify:queue:chat")

    def _raise_enqueue(*_args, **_kwargs):
        raise error

    monkeypatch.setattr("guardian.routes.chat.enqueue", _raise_enqueue)
    monkeypatch.setattr(
        "guardian.routes.chat.acquire_turn_lock", lambda *_a, **_k: True
    )
    monkeypatch.setattr(
        "guardian.routes.chat.release_turn_lock", lambda *_a, **_k: None
    )

    caplog.set_level(logging.ERROR, logger="guardian.routes.chat")
    response = test_client.post(
        "/api/chat/1/complete", json={}, headers={"X-Request-ID": "req-123"}
    )
    assert response.status_code == 503
    detail = response.json().get("detail", {})
    assert detail.get("error_code") == "CHAT_COMPLETE_ENQUEUE_FAILED"

    matching = [
        record
        for record in caplog.records
        if getattr(record, "error_code", None) == "CHAT_COMPLETE_ENQUEUE_FAILED"
    ]
    assert matching
    record = matching[0]
    assert record.thread_id == 1
    assert record.queue_name == "codexify:queue:chat"
    assert record.cause_class == type(cause).__name__
    assert record.request_id == response.headers.get("X-Request-ID")
    assert hasattr(record, "depth_mode")


def test_queue_enqueue_error_preserves_cause():
    cause = RuntimeError("boom")
    try:
        raise cause
    except Exception as exc:
        with pytest.raises(QueueEnqueueError) as err:
            raise QueueEnqueueError("queue:test", cause=exc) from exc
    assert err.value.__cause__ is cause
    assert err.value.cause is cause
    assert err.value.queue_name == "queue:test"
