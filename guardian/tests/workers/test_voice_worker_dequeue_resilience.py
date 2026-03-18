from __future__ import annotations

import threading
from typing import Any

from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError

from guardian.workers import voice_worker


def test_run_forever_retries_transient_dequeue_failures(monkeypatch):
    monkeypatch.setattr(voice_worker, "_initialize_worker", lambda: None)
    monkeypatch.setattr(
        voice_worker, "_publish_worker_heartbeat", lambda *_a, **_k: None
    )

    sleep_calls: list[float] = []
    monkeypatch.setattr(
        voice_worker.time,
        "sleep",
        lambda seconds: sleep_calls.append(seconds),
    )

    calls: list[tuple[Any, Any]] = []
    side_effects: list[BaseException] = [
        RedisConnectionError("redis connection lost"),
        RedisTimeoutError("redis idle timeout"),
        SystemExit("stop"),
    ]

    def fake_dequeue(*args: Any, **kwargs: Any) -> Any:
        calls.append((args, kwargs))
        raise side_effects.pop(0)

    monkeypatch.setattr(voice_worker, "dequeue", fake_dequeue)

    outcome: dict[str, BaseException] = {}

    def runner() -> None:
        try:
            voice_worker.run_forever()
        except BaseException as exc:
            outcome["exc"] = exc

    thread = threading.Thread(target=runner, daemon=True)
    thread.start()
    thread.join(1.0)

    assert not thread.is_alive(), "voice worker loop did not terminate"
    assert isinstance(outcome.get("exc"), SystemExit)
    assert len(calls) == 3
    assert sleep_calls == [1.0]


def test_run_forever_surfaces_non_retryable_dequeue_errors(monkeypatch):
    monkeypatch.setattr(voice_worker, "_initialize_worker", lambda: None)
    monkeypatch.setattr(
        voice_worker, "_publish_worker_heartbeat", lambda *_a, **_k: None
    )
    monkeypatch.setattr(voice_worker.time, "sleep", lambda *_: None)

    calls: list[tuple[Any, Any]] = []

    def fake_dequeue(*args: Any, **kwargs: Any) -> Any:
        calls.append((args, kwargs))
        raise RuntimeError("boom")

    monkeypatch.setattr(voice_worker, "dequeue", fake_dequeue)

    outcome: dict[str, BaseException] = {}

    def runner() -> None:
        try:
            voice_worker.run_forever()
        except BaseException as exc:
            outcome["exc"] = exc

    thread = threading.Thread(target=runner, daemon=True)
    thread.start()
    thread.join(1.0)

    assert not thread.is_alive(), "voice worker loop did not terminate"
    assert isinstance(outcome.get("exc"), RuntimeError)
    assert len(calls) == 1
