from __future__ import annotations

from guardian.queue import redis_queue


def test_connect_clients_use_distinct_socket_timeouts(monkeypatch):
    calls: list[tuple[str, dict[str, object]]] = []

    class FakeRedis:
        @classmethod
        def from_url(cls, url: str, **kwargs):
            calls.append((url, kwargs))
            return object()

    monkeypatch.setattr(redis_queue.redis, "Redis", FakeRedis)

    redis_queue._connect_request_client()
    redis_queue._connect_queue_client()

    assert len(calls) == 2
    assert calls[0][1]["socket_timeout"] == 2
    assert calls[1][1]["socket_timeout"] is None
    assert calls[0][1]["socket_connect_timeout"] == 2
    assert calls[1][1]["socket_connect_timeout"] == 2


def test_dequeue_blocking_uses_queue_client(monkeypatch):
    def fail_request_client(*_args, **_kwargs):
        raise AssertionError(
            "blocking dequeue should not use the request redis client"
        )

    calls: list[tuple[str, int]] = []

    monkeypatch.setattr(redis_queue, "_with_reconnect", fail_request_client)
    monkeypatch.setattr(
        redis_queue.queue_redis,
        "brpop",
        lambda name, timeout=0: calls.append((name, timeout))
        or (name, '{"task_id":"task-123"}'),
    )

    payload = redis_queue.dequeue("codexify:test", block=True, timeout=5)

    assert payload == {"task_id": "task-123"}
    assert calls == [("codexify:test", 5)]
