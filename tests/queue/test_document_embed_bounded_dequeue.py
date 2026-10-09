"""Document idle intake uses one finite blocking operation, with owned cleanup."""
import json
import time
from unittest.mock import Mock

import pytest
from redis.exceptions import TimeoutError as RedisTimeoutError

from guardian.core import chat_redis_deadline as bounds
from guardian.queue import document_embed_queue as queue
from tests.queue.test_chat_redis_deadline import factory, peer


def test_bounded_document_dequeue_retains_payload_and_scope(monkeypatch):
    def receive(name, *, timeout):
        assert name == queue.QUEUE_NAME and timeout == 1
        assert 0 < bounds._budget.get().remaining() <= 2
        return name, json.dumps({"doc_id": "owned-document", "task_id": "owned-task"})

    client = Mock()
    client.brpop.side_effect = receive
    monkeypatch.setattr(queue, "get_request_redis_client", lambda: client)
    assert queue.dequeue_document_embed_bounded() == {
        "doc_id": "owned-document", "task_id": "owned-task",
    }
    client.rpop.assert_not_called()
    assert bounds._budget.get() is None


def test_held_document_brpop_cannot_escape_two_second_idle_budget(monkeypatch):
    with peer(b"BRPOP") as (state, arrived, eof):
        factory(monkeypatch, state)
        started = time.monotonic()
        with pytest.raises(RedisTimeoutError):
            queue.dequeue_document_embed_bounded(timeout=1)
        assert 1.8 < time.monotonic() - started < 2.8
        assert arrived.is_set() and eof.wait(.25)
        assert state["commands"] == 1
    assert bounds._budget.get() is None


def test_unbounded_document_dequeue_is_rejected_before_io(monkeypatch):
    client = Mock()
    monkeypatch.setattr(queue, "get_request_redis_client", client)
    with pytest.raises(ValueError):
        queue.dequeue_document_embed_bounded(timeout=0)
    client.assert_not_called()
