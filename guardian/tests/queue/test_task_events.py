from __future__ import annotations

from guardian.queue import task_events


def test_read_events_uses_queue_client_defaults(monkeypatch):
    calls: list[dict[str, object]] = []

    class FakeRedis:
        def xread(self, streams, block=None, count=None):
            calls.append(
                {
                    "streams": streams,
                    "block": block,
                    "count": count,
                }
            )
            return [
                (
                    "codexify:task:task-123:events",
                    [
                        (
                            "1-0",
                            {
                                "type": "task.progress",
                                "task_id": "task-123",
                                "data": '{"ok": true}',
                                "created_at": "2026-03-29T00:00:00+00:00",
                            },
                        )
                    ],
                )
            ]

    monkeypatch.setattr(
        task_events,
        "get_queue_redis_client",
        lambda: FakeRedis(),
    )

    events = task_events.read_events("task-123", "0-0")

    assert calls == [
        {
            "streams": {"codexify:task:task-123:events": "0-0"},
            "block": 5000,
            "count": 50,
        }
    ]
    assert events == [
        (
            "1-0",
            {
                "type": "task.progress",
                "task_id": "task-123",
                "data": {"ok": True},
                "created_at": "2026-03-29T00:00:00+00:00",
            },
        )
    ]


def test_read_events_retries_with_backoff(monkeypatch):
    sleep_calls: list[float] = []

    class FakeRedis:
        def __init__(self) -> None:
            self.calls = 0

        def xread(self, streams, block=None, count=None):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("boom")
            return []

    fake_redis = FakeRedis()

    monkeypatch.setattr(
        task_events,
        "get_queue_redis_client",
        lambda: fake_redis,
    )
    monkeypatch.setattr(task_events.time, "sleep", sleep_calls.append)

    events = task_events.read_events("task-123", "0-0")

    assert events == []
    assert fake_redis.calls == 2
    assert sleep_calls == [0.5]
