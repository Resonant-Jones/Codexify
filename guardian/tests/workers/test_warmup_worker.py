import logging

import requests

from guardian.tasks.types import WarmupTask
from guardian.workers import warmup_worker


def test_await_vaultnode_ready_retries_until_success(monkeypatch):
    calls = {"count": 0}

    def fake_get(url, timeout):
        calls["count"] += 1
        if calls["count"] < 3:
            raise requests.ConnectionError("boom")

        class Response:
            status_code = 200

        return Response()

    monkeypatch.setattr(warmup_worker.requests, "get", fake_get)
    monkeypatch.setattr(warmup_worker.time, "sleep", lambda *_: None)

    ready, _last_exc = warmup_worker._await_vaultnode_ready(
        "http://vaultnode:11434",
        ["/healthz"],
        max_wait_seconds=1.0,
        request_timeout=0.01,
        backoff_base_seconds=0.0,
        backoff_max_seconds=0.0,
    )

    assert ready is True
    assert calls["count"] == 3


def test_await_vaultnode_ready_returns_last_error(monkeypatch):
    def fake_get(url, timeout):
        raise requests.Timeout("nope")

    monkeypatch.setattr(warmup_worker.requests, "get", fake_get)
    monkeypatch.setattr(warmup_worker.time, "sleep", lambda *_: None)

    ready, last_exc = warmup_worker._await_vaultnode_ready(
        "http://vaultnode:11434",
        ["/healthz"],
        max_wait_seconds=0.02,
        request_timeout=0.01,
        backoff_base_seconds=0.0,
        backoff_max_seconds=0.0,
    )

    assert ready is False
    assert isinstance(last_exc, requests.Timeout)


def test_startup_warmup_is_best_effort_and_low_noise(monkeypatch, caplog):
    published: list[tuple[str, dict[str, object]]] = []
    call_args: list[dict[str, object]] = []
    sleep_calls: list[float] = []

    monkeypatch.setattr(
        warmup_worker,
        "_await_vaultnode_ready",
        lambda *_a, **_k: (True, None),
    )
    monkeypatch.setattr(
        warmup_worker,
        "_safe_publish",
        lambda _task_id, event_type, data: published.append(
            (event_type, dict(data or {}))
        ),
    )
    monkeypatch.setattr(
        warmup_worker.time,
        "sleep",
        lambda seconds: sleep_calls.append(seconds),
    )

    def fake_call_local(messages, **kwargs):
        call_args.append({"messages": messages, **kwargs})
        raise TimeoutError("local model timed out")

    monkeypatch.setattr(warmup_worker, "call_local", fake_call_local)

    task = WarmupTask(
        task_id="warmup-startup",
        origin="startup",
        models=["configured-local-model"],
    )

    with caplog.at_level(logging.WARNING):
        warmup_worker._run_task(
            task,
            base_url="http://vaultnode:11434",
            health_base="http://vaultnode:11434",
            endpoints=["/healthz"],
        )

    assert [event_type for event_type, _payload in published] == [
        "task.running",
        "task.failed",
    ]
    assert published[0][1] == {"type": "warmup", "origin": "startup"}
    assert published[1][1] == {"type": "warmup", "origin": "startup"}
    assert len(call_args) == 1
    assert call_args[0]["model"] == "configured-local-model"
    assert sleep_calls == []

    warnings = [record.message for record in caplog.records]
    assert len(warnings) == 1
    assert "startup warmup best-effort failed" in warnings[0]
    assert "models=configured-local-model" in warnings[0]


def test_non_startup_warmup_still_retries_before_succeeding(monkeypatch):
    published: list[tuple[str, dict[str, object]]] = []
    call_args: list[dict[str, object]] = []
    sleep_calls: list[float] = []
    attempts = {"count": 0}

    monkeypatch.setattr(
        warmup_worker,
        "_await_vaultnode_ready",
        lambda *_a, **_k: (True, None),
    )
    monkeypatch.setattr(
        warmup_worker,
        "_safe_publish",
        lambda _task_id, event_type, data: published.append(
            (event_type, dict(data or {}))
        ),
    )
    monkeypatch.setattr(
        warmup_worker.time,
        "sleep",
        lambda seconds: sleep_calls.append(seconds),
    )

    def fake_call_local(messages, **kwargs):
        attempts["count"] += 1
        call_args.append({"messages": messages, **kwargs})
        if attempts["count"] < 3:
            raise RuntimeError("local model still warming up")
        return {"ok": True}

    monkeypatch.setattr(warmup_worker, "call_local", fake_call_local)
    monkeypatch.setattr(warmup_worker, "BACKOFF_BASE_SECONDS", 0.0)
    monkeypatch.setattr(warmup_worker, "BACKOFF_MAX_SECONDS", 0.0)
    monkeypatch.setattr(warmup_worker, "MAX_RETRIES", 5)

    task = WarmupTask(
        task_id="warmup-api",
        origin="api",
        models=["configured-local-model"],
    )

    warmup_worker._run_task(
        task,
        base_url="http://vaultnode:11434",
        health_base="http://vaultnode:11434",
        endpoints=["/healthz"],
    )

    assert [event_type for event_type, _payload in published] == [
        "task.running",
        "task.completed",
    ]
    assert len(call_args) == 3
    assert all(call["model"] == "configured-local-model" for call in call_args)
    assert sleep_calls == [0.0, 0.0]
