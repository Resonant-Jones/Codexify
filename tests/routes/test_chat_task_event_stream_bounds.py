"""Exercise the actual SSE generator with transport seams, no task mutation."""
from unittest.mock import MagicMock

import pytest

from guardian.guardian_api import stream_task_events
from guardian.queue import task_events


class Request:
    def __init__(self, checks=None):
        self.checks = iter(checks or [False])
    async def is_disconnected(self):
        return next(self.checks, True)


async def collect(request, **kwargs):
    response = await stream_task_events(request, "task-a", last_id_query=kwargs.get("last_id", "0-0"),
        last_event_id_header=kwargs.get("header"), api_key="test-api-key")
    return "".join([row async for row in response.body_iterator])


@pytest.mark.asyncio
async def test_transport_error_closes_subscription_without_inventing_terminal(monkeypatch):
    reader = MagicMock(side_effect=RuntimeError("lost transport"))
    monkeypatch.setattr(task_events, "read_events_bounded", reader)
    monkeypatch.setattr(task_events, "read_events", lambda *a, **kw: pytest.fail("legacy reader"))
    body = await collect(Request())
    assert body == "retry: 3000\n\n"
    reader.assert_called_once_with("task-a", "0-0", block_ms=1000, count=100)


@pytest.mark.asyncio
async def test_disconnected_consumer_starts_no_read(monkeypatch):
    reader = MagicMock()
    monkeypatch.setattr(task_events, "read_events_bounded", reader)
    assert await collect(Request([True])) == "retry: 3000\n\n"
    reader.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("terminal", ["task.completed", "task.failed", "task.cancelled"])
async def test_resume_cursor_and_terminal_order_are_preserved(monkeypatch, terminal):
    reader = MagicMock(return_value=[("6-0", {"type": "task.chunk", "data": {"delta": "Hi"}}),
        ("7-0", {"type": terminal, "data": {"thread_id": 1}}),
        ("8-0", {"type": "task.chunk", "data": {"delta": "late"}})])
    monkeypatch.setattr(task_events, "read_events_bounded", reader)
    body = await collect(Request(), header="5-0", last_id="1-0")
    reader.assert_called_once_with("task-a", "5-0", block_ms=1000, count=100)
    assert body.index("id: 6-0") < body.index("id: 7-0")
    assert f"event: {terminal}" in body and '"delta": "Hi"' in body
    assert "8-0" not in body and "late" not in body


@pytest.mark.asyncio
@pytest.mark.parametrize("configured,expected", [("15000", 1000), ("0", 1), ("-5", 1)])
async def test_config_never_issues_zero_or_unbounded_block(monkeypatch, configured, expected):
    monkeypatch.setenv("TASK_EVENT_BLOCK_MS", configured)
    reader = MagicMock(return_value=[])
    monkeypatch.setattr(task_events, "read_events_bounded", reader)
    await collect(Request([False, True]))
    reader.assert_called_once_with("task-a", "0-0", block_ms=expected, count=100)


@pytest.mark.asyncio
async def test_invalid_configuration_closes_without_read(monkeypatch):
    monkeypatch.setenv("TASK_EVENT_BLOCK_MS", "not-a-number")
    reader = MagicMock()
    monkeypatch.setattr(task_events, "read_events_bounded", reader)
    assert await collect(Request()) == "retry: 3000\n\n"
    reader.assert_not_called()


@pytest.mark.asyncio
async def test_empty_bounded_polls_retain_ping_and_cursor(monkeypatch):
    reader = MagicMock(return_value=[])
    monkeypatch.setattr(task_events, "read_events_bounded", reader)
    body = await collect(Request([False] * 15 + [True]), header="5-0")
    assert body == "retry: 3000\n\n: ping\n\n"
    assert reader.call_count == 15
    assert all(call.args == ("task-a", "5-0") for call in reader.call_args_list)
