"""
Proof-level tests for the task event route and Redis stream mock.

Verifies:
- Existing GET /api/tasks/{task_id}/events route source is present
- In-memory Redis xadd/xread stream operations work correctly
"""

import pytest


@pytest.fixture(autouse=True)
def _hermetic_redis():
    """Ensure in-memory Redis is active for deterministic tests."""
    from guardian.queue import redis_queue

    redis_queue._CLIENT = redis_queue._InMemoryRedis()
    redis_queue._QUEUE_CLIENT = redis_queue._InMemoryRedis()


class TestTaskEventRouteExists:
    """Proof that the task event route source is present."""

    def test_route_is_registered_in_source(self):
        """The route is registered directly in guardian_api.py."""
        import os

        api_path = os.path.join(
            os.path.dirname(__file__),
            "..", "guardian", "guardian_api.py",
        )
        api_path = os.path.normpath(api_path)
        with open(api_path) as f:
            source = f.read()
        assert "/api/tasks/{task_id}/events" in source, (
            "Expected /api/tasks/{task_id}/events route in guardian_api.py"
        )


class TestInMemoryRedisStreams:
    """Proof that _InMemoryRedis xadd/xread work for task event testing."""

    def test_xadd_returns_entry_id(self):
        from guardian.queue.redis_queue import _InMemoryRedis

        redis = _InMemoryRedis()
        eid = redis.xadd("mystream", {"type": "task.created", "data": "{}"})
        assert isinstance(eid, str)
        assert "-" in eid

    def test_xread_returns_entries(self):
        from guardian.queue.redis_queue import _InMemoryRedis

        redis = _InMemoryRedis()
        redis.xadd("s1", {"k": "v1"})
        redis.xadd("s1", {"k": "v2"})

        result = redis.xread(streams={"s1": "0-0"}, count=10)
        assert len(result) == 1
        _, entries = result[0]
        assert len(entries) == 2

    def test_xread_empty_for_unknown_stream(self):
        from guardian.queue.redis_queue import _InMemoryRedis

        redis = _InMemoryRedis()
        result = redis.xread(streams={"nonexistent": "0-0"})
        assert result == []

    def test_xread_respects_last_id(self):
        from guardian.queue.redis_queue import _InMemoryRedis

        redis = _InMemoryRedis()
        eid1 = redis.xadd("s2", {"n": "1"})
        eid2 = redis.xadd("s2", {"n": "2"})

        result = redis.xread(streams={"s2": eid1})
        _, entries = result[0]
        assert len(entries) == 1
        assert entries[0][0] == eid2

    def test_xread_respects_count(self):
        from guardian.queue.redis_queue import _InMemoryRedis

        redis = _InMemoryRedis()
        for i in range(5):
            redis.xadd("s3", {"i": str(i)})

        result = redis.xread(streams={"s3": "0-0"}, count=2)
        _, entries = result[0]
        assert len(entries) == 2

    def test_xadd_preserves_fields(self):
        from guardian.queue.redis_queue import _InMemoryRedis

        redis = _InMemoryRedis()
        eid = redis.xadd("s4", {"type": "task.completed", "data": '{"ok":true}'})
        result = redis.xread(streams={"s4": "0-0"})
        _, entries = result[0]
        assert entries[0][1]["type"] == "task.completed"
        assert entries[0][1]["data"] == '{"ok":true}'
