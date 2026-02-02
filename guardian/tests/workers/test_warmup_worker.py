import requests

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
