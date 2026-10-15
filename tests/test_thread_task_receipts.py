"""
Proof-level tests for the thread task receipts route.

Verifies:
- GET /api/chat/{thread_id}/tasks returns expected shape
- Returns empty task list for threads with no tracked tasks
- Returns task receipt when a task has been tracked and has terminal evidence
"""

import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture(autouse=True)
def _hermetic_redis():
    """Ensure in-memory Redis is active for deterministic tests."""
    from guardian.queue import redis_queue

    redis_queue._CLIENT = redis_queue._InMemoryRedis()
    redis_queue._QUEUE_CLIENT = redis_queue._CLIENT


def _mock_thread_scope():
    """Return a mock RequestUserScope that passes all scope checks."""
    scope = MagicMock()
    scope.user_id = 1
    scope.account_id = 1
    scope.scope = "single_user"
    return scope


class TestThreadTasksRoute:
    """Proof that chat_list_tasks returns expected shape."""

    @patch("guardian.routes.chat.chatlog_db")
    def test_no_tasks_for_untracked_thread(self, mock_db):
        from guardian.routes.chat import chat_list_tasks
        import guardian.routes.chat as crc

        mock_db.get_chat_thread.return_value = {"id": 99999, "title": "Test"}

        _orig_require = crc._require_thread_account_scope
        crc._require_thread_account_scope = lambda *a, **kw: None

        try:
            result = chat_list_tasks(
                thread_id=99999,
                api_key="test-api-key",
                request_user_scope=_mock_thread_scope(),
            )
        finally:
            crc._require_thread_account_scope = _orig_require

        assert result["ok"] is True
        assert result["thread_id"] == 99999
        assert result["tasks"] == []
        assert result["count"] == 0

    @patch("guardian.routes.chat.chatlog_db")
    def test_returns_task_receipt_when_tracked(self, mock_db):
        from guardian.routes.chat import (
            _thread_latest_task,
            chat_list_tasks,
        )
        from guardian.queue import redis_queue
        import guardian.routes.chat as crc

        mock_db.get_chat_thread.return_value = {"id": 1, "title": "Test"}

        # Write terminal event into the mock Redis stream
        client = redis_queue.get_queue_redis_client()
        stream_key = "codexify:task:task-test-1:events"
        client.xadd(stream_key, {
            "type": "task.created",
            "task_id": "task-test-1",
            "data": "{}",
            "created_at": "2024-01-01T00:00:00Z",
        })
        client.xadd(stream_key, {
            "type": "task.completed",
            "task_id": "task-test-1",
            "data": '{"ok":true}',
            "created_at": "2024-01-01T00:00:01Z",
        })

        _thread_latest_task[1] = "task-test-1"

        _orig_require = crc._require_thread_account_scope
        crc._require_thread_account_scope = lambda *a, **kw: None

        try:
            result = chat_list_tasks(
                thread_id=1,
                api_key="test-api-key",
                request_user_scope=_mock_thread_scope(),
            )
        finally:
            crc._require_thread_account_scope = _orig_require
            _thread_latest_task.pop(1, None)

        assert result["ok"] is True
        assert result["count"] == 1
        assert result["tasks"][0]["task_id"] == "task-test-1"
        assert result["tasks"][0]["state"] == "terminal"
        assert result["tasks"][0]["event_type"] == "task.completed"

    @patch("guardian.routes.chat.chatlog_db")
    def test_reports_nonterminal_task_honestly(self, mock_db):
        from guardian.routes.chat import (
            _thread_latest_task,
            chat_list_tasks,
        )
        from guardian.queue import redis_queue
        import guardian.routes.chat as crc

        mock_db.get_chat_thread.return_value = {"id": 2, "title": "Test"}

        client = redis_queue.get_queue_redis_client()
        stream_key = "codexify:task:task-progress-1:events"
        client.xadd(stream_key, {
            "type": "task.created",
            "task_id": "task-progress-1",
            "data": "{}",
            "created_at": "2024-01-01T00:00:00Z",
        })

        _thread_latest_task[2] = "task-progress-1"

        _orig_require = crc._require_thread_account_scope
        crc._require_thread_account_scope = lambda *a, **kw: None

        try:
            result = chat_list_tasks(
                thread_id=2,
                api_key="test-api-key",
                request_user_scope=_mock_thread_scope(),
            )
        finally:
            crc._require_thread_account_scope = _orig_require
            _thread_latest_task.pop(2, None)

        assert result["ok"] is True
        assert result["count"] == 1
        assert result["tasks"][0]["task_id"] == "task-progress-1"
        assert result["tasks"][0]["state"] == "nonterminal"
        assert result["tasks"][0]["event_type"] is None


class TestThreadTasksRouteRegistration:
    """Proof the route is registered on the chat router."""

    def test_route_is_registered(self):
        from guardian.routes.chat import router

        paths = [route.path for route in router.routes]
        assert "/threads/{thread_id}/tasks" in paths or \
               "/chat/threads/{thread_id}/tasks" in paths, (
            "Expected /threads/{thread_id}/tasks in chat router paths"
        )
