"""Bounded observation preserves transport data without assigning task truth."""
from contextlib import contextmanager

import pytest

from guardian.core import chat_redis_deadline as bounds
from guardian.queue import task_events


def test_scoped_read_decodes_and_preserves_cursor_without_using_queue_client(monkeypatch):
    calls = []
    @contextmanager
    def scope(seconds):
        calls.append(("scope", seconds))
        yield
        calls.append(("closed",))
    class Client:
        def xread(self, **kwargs):
            calls.append(kwargs)
            return [("stream", [("5-0", {"type": "task.chunk", "data": '{"delta":"Hi"}'}),
                                ("6-0", {"type": "task.completed", "data": '{"message_id":42}'}),
                                ("7-0", {"data": "not-json"})])]
    monkeypatch.setattr(task_events, "redis_operation_scope", scope)
    monkeypatch.setattr(task_events, "get_redis_client", lambda: Client())
    monkeypatch.setattr(task_events, "get_queue_redis_client", lambda: pytest.fail("unbounded queue client"))
    result = task_events.read_events_bounded("task-a", "4-0", block_ms=500, count=100)
    assert calls == [("scope", 2.0), {"streams": {"codexify:task:task-a:events": "4-0"}, "block": 500, "count": 100}, ("closed",)]
    assert [row[0] for row in result] == ["5-0", "6-0", "7-0"]
    assert result[0][1]["data"] == {"delta": "Hi"}
    assert result[1][1]["data"] == {"message_id": 42}
    assert result[2][1] == {"type": "task.event", "task_id": "task-a", "data": {}, "created_at": None}


@pytest.mark.parametrize("field,value", [("block_ms", 0), ("block_ms", -1), ("block_ms", 1001),
    ("block_ms", float("inf")), ("block_ms", True), ("count", 0), ("count", 101), ("count", 2.5)])
def test_invalid_limits_fail_before_client_or_scope(monkeypatch, field, value):
    monkeypatch.setattr(task_events, "get_redis_client", lambda: pytest.fail("client started"))
    monkeypatch.setattr(task_events, "redis_operation_scope", lambda *a: pytest.fail("scope started"))
    with pytest.raises(ValueError):
        task_events.read_events_bounded("task-a", "0-0", **{field: value})


def test_inherited_accepted_budget_cannot_be_replaced(monkeypatch):
    monkeypatch.setattr(task_events, "get_redis_client", lambda: pytest.fail("client started"))
    with bounds.redis_operation_scope(.25):
        original = bounds._budget.get()
        with pytest.raises(ValueError, match="inherited budget"):
            task_events.read_events_bounded("task-a", "0-0")
        assert bounds._budget.get() is original


def test_read_error_is_not_retried_or_reported_as_empty_success(monkeypatch):
    calls = []
    class Client:
        def xread(self, **kwargs):
            calls.append(kwargs)
            raise RuntimeError("lost transport")
    monkeypatch.setattr(task_events, "get_redis_client", lambda: Client())
    monkeypatch.setattr(task_events.time, "sleep", lambda *a: pytest.fail("unbounded retry sleep"))
    with pytest.raises(RuntimeError, match="lost transport"):
        task_events.read_events_bounded("task-a", "0-0")
    assert len(calls) == 1
    assert bounds._budget.get() is None
