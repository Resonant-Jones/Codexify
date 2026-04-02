from __future__ import annotations

import json

import pytest

from guardian.core.ai_router import LOCAL_MODEL_RESOLUTION_ERROR, call_local
from guardian.core.config import get_settings
from guardian.routes import health as health_routes


class _FakeRedisClient:
    def __init__(
        self,
        *,
        heartbeat_value=None,
        queue_depth: int = 0,
        pop_value: bytes | None = b"ok",
        ping_ok: bool = True,
    ) -> None:
        self.heartbeat_value = heartbeat_value
        self.queue_depth = queue_depth
        self.pop_value = pop_value
        self.ping_ok = ping_ok

    def ping(self) -> bool:
        return self.ping_ok

    def lpush(self, *_args, **_kwargs) -> int:
        return 1

    def rpop(self, *_args, **_kwargs):
        return self.pop_value

    def delete(self, *_args, **_kwargs) -> int:
        return 1

    def get(self, _key):
        return self.heartbeat_value

    def llen(self, _key) -> int:
        return self.queue_depth


class _MockResponse:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def json(self) -> dict:
        return self._payload


class _MockRawResponse:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self.status_code = status_code
        self.content = json.dumps(payload).encode("utf-8")

    def json(self) -> dict:
        return json.loads(self.content.decode("utf-8"))


def _mock_local_runtime_request(
    url: str,
    *args,
    **kwargs,
) -> _MockResponse:
    _ = (args, kwargs)
    if url.endswith("/api/tags"):
        return _MockResponse({"models": [{"name": "qwen3.5:0.8b"}]})
    return _MockResponse({"status": "ok"})


def _healthy_completion_service() -> dict[str, object]:
    return {
        "ok": True,
        "redis_reachable": True,
        "enqueue_test_ok": True,
        "worker_heartbeat_detected": True,
        "worker_heartbeat_age_seconds": 0.5,
        "worker_heartbeat_status": "fresh",
        "worker_heartbeat_reason": "ok",
        "worker_heartbeat_detail": None,
        "heartbeat_key": "codexify:worker:chat:heartbeat",
        "status_reason": "ok",
        "error": None,
        "dependency": None,
        "dependency_unavailable": False,
    }


def _healthy_queue() -> dict[str, object]:
    return {
        "depth": 0,
        "status": "progressing",
        "error": None,
        "dependency": None,
        "dependency_unavailable": False,
    }


def _snapshot_settings(settings):
    return {
        "LLM_PROVIDER": settings.LLM_PROVIDER,
        "ALLOW_CLOUD_PROVIDERS": settings.ALLOW_CLOUD_PROVIDERS,
        "CODEXIFY_LOCAL_ONLY_MODE": settings.CODEXIFY_LOCAL_ONLY_MODE,
        "CODEXIFY_EGRESS_ALLOWLIST": settings.CODEXIFY_EGRESS_ALLOWLIST,
        "LOCAL_BASE_URL": settings.LOCAL_BASE_URL,
        "LOCAL_API_KEY": settings.LOCAL_API_KEY,
        "LOCAL_LLM_MODEL": settings.LOCAL_LLM_MODEL,
        "LOCAL_CHAT_MODEL": settings.LOCAL_CHAT_MODEL,
        "DEFAULT_LOCAL_MODEL": settings.DEFAULT_LOCAL_MODEL,
        "LLM_MODEL": settings.LLM_MODEL,
    }


def _apply_local_only_runtime(settings) -> None:
    settings.LLM_PROVIDER = "local"
    settings.ALLOW_CLOUD_PROVIDERS = False
    settings.CODEXIFY_LOCAL_ONLY_MODE = True
    settings.CODEXIFY_EGRESS_ALLOWLIST = ""
    settings.LOCAL_BASE_URL = "http://host.docker.internal:11434/v1"
    settings.LOCAL_API_KEY = "local"
    settings.LOCAL_LLM_MODEL = "library2/ministral-3:8b"
    settings.LOCAL_CHAT_MODEL = "qwen3.5:0.8b"
    settings.DEFAULT_LOCAL_MODEL = "library2/ministral-3:8b"
    settings.LLM_MODEL = "library2/ministral-3:8b"


def _heartbeat_bytes(payload: object) -> bytes:
    return json.dumps(payload).encode("utf-8")


def _patch_local_health_runtime(monkeypatch) -> None:
    monkeypatch.setattr(
        "guardian.core.ai_router.requests.get",
        _mock_local_runtime_request,
    )
    monkeypatch.setattr(
        "guardian.routes.health.requests.get",
        _mock_local_runtime_request,
    )


def _install_fake_redis(monkeypatch, client: _FakeRedisClient) -> None:
    monkeypatch.setattr(
        "guardian.queue.redis_queue.get_redis_client",
        lambda: client,
    )


@pytest.fixture(autouse=True)
def _reset_health_route_state():
    health_routes._CHAT_QUEUE_LAST_DEPTH = None
    health_routes._CHAT_QUEUE_LAST_CHECK_TS = 0.0
    health_routes._LLM_HEALTH_PROBE_CACHE = None
    health_routes._LLM_HEALTH_PROBE_TS = 0.0
    yield
    health_routes._CHAT_QUEUE_LAST_DEPTH = None
    health_routes._CHAT_QUEUE_LAST_CHECK_TS = 0.0
    health_routes._LLM_HEALTH_PROBE_CACHE = None
    health_routes._LLM_HEALTH_PROBE_TS = 0.0


def test_health_llm_reports_effective_local_chat_model(
    test_client,
    monkeypatch,
):
    monkeypatch.setattr(
        "guardian.core.ai_router.requests.get",
        _mock_local_runtime_request,
    )
    monkeypatch.setattr(
        "guardian.routes.health.requests.get",
        _mock_local_runtime_request,
    )
    monkeypatch.setattr(
        health_routes,
        "_collect_completion_service_health",
        _healthy_completion_service,
    )
    health_routes._LLM_HEALTH_PROBE_CACHE = None
    health_routes._LLM_HEALTH_PROBE_TS = 0.0

    settings = get_settings()
    snapshot = _snapshot_settings(settings)
    try:
        _apply_local_only_runtime(settings)
        payload = test_client.get("/health/llm").json()
        assert payload["model"] == "qwen3.5:0.8b"
        assert payload["provider_runtime"]["default_model"] == "qwen3.5:0.8b"
        assert payload["model_resolution"]["source"] == "LOCAL_CHAT_MODEL"
        assert payload["runtime"]["reasoning"]["mode"] == "no_think"
    finally:
        for field, value in snapshot.items():
            setattr(settings, field, value)
        health_routes._LLM_HEALTH_PROBE_CACHE = None
        health_routes._LLM_HEALTH_PROBE_TS = 0.0


def test_health_chat_reports_effective_local_chat_model(
    test_client,
    monkeypatch,
):
    monkeypatch.setattr(
        "guardian.core.ai_router.requests.get",
        _mock_local_runtime_request,
    )
    monkeypatch.setattr(
        health_routes,
        "_collect_completion_service_health",
        _healthy_completion_service,
    )
    monkeypatch.setattr(
        health_routes, "_collect_chat_queue_health", _healthy_queue
    )

    settings = get_settings()
    snapshot = _snapshot_settings(settings)
    try:
        _apply_local_only_runtime(settings)
        payload = test_client.get("/health/chat").json()
        assert payload["model"] == "qwen3.5:0.8b"
        assert payload["provider_runtime"]["default_model"] == "qwen3.5:0.8b"
        assert payload["model_resolution"]["source"] == "LOCAL_CHAT_MODEL"
        assert payload["runtime"]["reasoning"]["mode"] == "no_think"
    finally:
        for field, value in snapshot.items():
            setattr(settings, field, value)


def test_health_surfaces_match_executed_local_model(
    test_client,
    monkeypatch,
):
    captured: dict[str, object] = {}

    def _mock_post(url: str, *, json, headers, timeout):
        captured["url"] = url
        captured["json"] = json
        _ = (headers, timeout)
        return _MockRawResponse({"message": {"content": "Strict reply"}})

    monkeypatch.setattr(
        "guardian.core.ai_router.requests.get",
        _mock_local_runtime_request,
    )
    monkeypatch.setattr(
        "guardian.routes.health.requests.get",
        _mock_local_runtime_request,
    )
    monkeypatch.setattr("guardian.core.ai_router.requests.post", _mock_post)
    monkeypatch.setattr(
        health_routes,
        "_collect_completion_service_health",
        _healthy_completion_service,
    )
    monkeypatch.setattr(
        health_routes, "_collect_chat_queue_health", _healthy_queue
    )
    health_routes._LLM_HEALTH_PROBE_CACHE = None
    health_routes._LLM_HEALTH_PROBE_TS = 0.0

    settings = get_settings()
    snapshot = _snapshot_settings(settings)
    try:
        _apply_local_only_runtime(settings)
        result = call_local(
            [{"role": "user", "content": "hello"}],
            "library2/ministral-3:8b",
            settings=settings,
        )
        llm_payload = test_client.get("/health/llm").json()
        chat_payload = test_client.get("/health/chat").json()

        assert result == "Strict reply"
        assert captured["json"]["model"] == "qwen3.5:0.8b"
        assert llm_payload["model"] == captured["json"]["model"]
        assert (
            llm_payload["provider_runtime"]["default_model"]
            == captured["json"]["model"]
        )
        assert chat_payload["model"] == captured["json"]["model"]
        assert (
            chat_payload["provider_runtime"]["default_model"]
            == captured["json"]["model"]
        )
    finally:
        for field, value in snapshot.items():
            setattr(settings, field, value)
        health_routes._LLM_HEALTH_PROBE_CACHE = None
        health_routes._LLM_HEALTH_PROBE_TS = 0.0


def test_health_llm_surfaces_local_model_resolution_error(
    test_client,
    monkeypatch,
):
    monkeypatch.setattr(
        "guardian.core.ai_router.requests.get",
        _mock_local_runtime_request,
    )
    monkeypatch.setattr(
        "guardian.routes.health.requests.get",
        _mock_local_runtime_request,
    )
    monkeypatch.setattr(
        health_routes,
        "_collect_completion_service_health",
        _healthy_completion_service,
    )
    health_routes._LLM_HEALTH_PROBE_CACHE = None
    health_routes._LLM_HEALTH_PROBE_TS = 0.0

    settings = get_settings()
    snapshot = _snapshot_settings(settings)
    try:
        _apply_local_only_runtime(settings)
        settings.LOCAL_CHAT_MODEL = ""
        payload = test_client.get("/health/llm").json()
        assert payload["status"] == "misconfigured"
        assert payload["error"] == LOCAL_MODEL_RESOLUTION_ERROR
        assert payload["failure_kind"] == "local_model_missing"
    finally:
        for field, value in snapshot.items():
            setattr(settings, field, value)
        health_routes._LLM_HEALTH_PROBE_CACHE = None
        health_routes._LLM_HEALTH_PROBE_TS = 0.0


def test_health_chat_treats_fresh_redis_heartbeat_as_live(
    test_client,
    monkeypatch,
):
    fixed_now = 1_700_000_000.0
    heartbeat_age = 1.5
    heartbeat_payload = _heartbeat_bytes(
        {
            "worker": "chat",
            "status": "idle",
            "timestamp": str(fixed_now - heartbeat_age),
        }
    )

    _patch_local_health_runtime(monkeypatch)
    _install_fake_redis(
        monkeypatch,
        _FakeRedisClient(heartbeat_value=heartbeat_payload, queue_depth=0),
    )
    monkeypatch.setattr(health_routes.time, "time", lambda: fixed_now)

    payload = test_client.get("/health/chat").json()

    assert payload["ok"] is True
    assert payload["status"] == "healthy"
    assert payload["redis"] == "ok"
    assert payload["worker"]["status"] == "fresh"
    assert payload["worker"]["reason"] == "ok"
    assert payload["worker"]["heartbeat_age_seconds"] == pytest.approx(
        heartbeat_age, abs=0.001
    )
    assert payload["completion_service"]["worker_heartbeat_detected"] is True
    assert payload["completion_service"]["worker_heartbeat_status"] == "fresh"
    assert payload["completion_service"]["status_reason"] == "ok"
    assert any("queue empty" in str(note).lower() for note in payload["notes"])


def test_health_chat_surfaces_stale_worker_heartbeat(
    test_client,
    monkeypatch,
):
    fixed_now = 1_700_000_000.0
    heartbeat_age = (
        health_routes.CHAT_WORKER_HEARTBEAT_FRESH_THRESHOLD_SECONDS + 5.0
    )
    heartbeat_payload = _heartbeat_bytes({"ts": fixed_now - heartbeat_age})

    _patch_local_health_runtime(monkeypatch)
    _install_fake_redis(
        monkeypatch,
        _FakeRedisClient(heartbeat_value=heartbeat_payload, queue_depth=0),
    )
    monkeypatch.setattr(health_routes.time, "time", lambda: fixed_now)

    payload = test_client.get("/health/chat").json()

    assert payload["ok"] is False
    assert payload["status"] == "degraded"
    assert payload["worker"]["status"] == "stale"
    assert payload["worker"]["reason"] == "ok"
    assert payload["completion_service"]["status_reason"] == (
        "worker_heartbeat_stale"
    )
    assert any(
        "worker heartbeat stale" in str(note).lower()
        for note in payload["notes"]
    )


def test_health_chat_marks_malformed_worker_heartbeat_explicitly(
    test_client,
    monkeypatch,
):
    fixed_now = 1_700_000_000.0
    heartbeat_payload = _heartbeat_bytes(
        {
            "worker": "chat",
            "status": "idle",
            "ts": "still-not-a-timestamp",
        }
    )

    _patch_local_health_runtime(monkeypatch)
    _install_fake_redis(
        monkeypatch,
        _FakeRedisClient(heartbeat_value=heartbeat_payload, queue_depth=0),
    )
    monkeypatch.setattr(health_routes.time, "time", lambda: fixed_now)

    payload = test_client.get("/health/chat").json()

    assert payload["ok"] is False
    assert payload["status"] == "unhealthy"
    assert payload["worker"]["status"] == "dead"
    assert payload["worker"]["reason"] == "malformed"
    assert payload["worker"]["detail"] == "timestamp_invalid"
    assert payload["completion_service"]["worker_heartbeat_detected"] is True
    assert payload["completion_service"]["worker_heartbeat_status"] == "dead"
    assert payload["completion_service"]["status_reason"] == (
        "worker_heartbeat_malformed"
    )
    assert any(
        "worker heartbeat malformed" in str(note).lower()
        for note in payload["notes"]
    )


def test_health_chat_preserves_missing_worker_heartbeat_behavior(
    test_client,
    monkeypatch,
):
    fixed_now = 1_700_000_000.0

    _patch_local_health_runtime(monkeypatch)
    _install_fake_redis(
        monkeypatch,
        _FakeRedisClient(heartbeat_value=None, queue_depth=0),
    )
    monkeypatch.setattr(health_routes.time, "time", lambda: fixed_now)

    payload = test_client.get("/health/chat").json()

    assert payload["ok"] is False
    assert payload["status"] == "unhealthy"
    assert payload["worker"]["status"] == "dead"
    assert payload["worker"]["reason"] == "missing"
    assert payload["worker"]["heartbeat_age_seconds"] is None
    assert payload["completion_service"]["worker_heartbeat_detected"] is False
    assert payload["completion_service"]["status_reason"] == (
        "worker_heartbeat_missing"
    )
    assert any(
        "worker heartbeat missing" in str(note).lower()
        for note in payload["notes"]
    )


def test_health_chat_keeps_queue_round_trip_truth_with_fresh_heartbeat(
    test_client,
    monkeypatch,
):
    fixed_now = 1_700_000_000.0
    heartbeat_age = 1.0
    heartbeat_payload = _heartbeat_bytes({"ts": fixed_now - heartbeat_age})

    _patch_local_health_runtime(monkeypatch)
    _install_fake_redis(
        monkeypatch,
        _FakeRedisClient(
            heartbeat_value=heartbeat_payload,
            queue_depth=0,
            pop_value=None,
        ),
    )
    monkeypatch.setattr(health_routes.time, "time", lambda: fixed_now)

    payload = test_client.get("/health/chat").json()

    assert payload["ok"] is False
    assert payload["status"] == "unhealthy"
    assert payload["redis"] == "unhealthy"
    assert payload["worker"]["status"] == "fresh"
    assert payload["worker"]["reason"] == "ok"
    assert payload["completion_service"]["enqueue_test_ok"] is False
    assert payload["completion_service"]["worker_heartbeat_status"] == "fresh"
    assert payload["completion_service"]["status_reason"] == (
        "queue_enqueue_failed"
    )
    assert any(
        "queue round-trip probe failed" in str(note).lower()
        for note in payload["notes"]
    )
