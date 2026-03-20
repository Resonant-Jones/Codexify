import json

import pytest
import requests
from fastapi.testclient import TestClient

from guardian.guardian_api import app
from guardian.routes import health as health_routes


class _FakeRedisClient:
    def __init__(self, heartbeat_value):
        self.heartbeat_value = heartbeat_value

    def ping(self):
        return True

    def lpush(self, *args, **kwargs):
        return 1

    def rpop(self, *args, **kwargs):
        return b"ok"

    def delete(self, *args, **kwargs):
        return 1

    def get(self, key):
        return self.heartbeat_value


def test_health_endpoints_ok():
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json().get("status") == "ok"

    deps = client.get("/health/deps")
    assert deps.status_code == 200
    data = deps.json()
    assert data.get("status") == "ok"


def test_health_llm_reports_local_online(monkeypatch):
    from guardian.core.config import get_settings

    settings = get_settings()
    prev_provider = settings.LLM_PROVIDER
    prev_local_base = settings.LOCAL_BASE_URL

    settings.LLM_PROVIDER = "local"
    settings.LOCAL_BASE_URL = "http://127.0.0.1:11434/v1"

    class _Resp:
        status_code = 200

    monkeypatch.setattr(
        "guardian.routes.health.requests.get", lambda *a, **k: _Resp()
    )

    client = TestClient(app)
    try:
        resp = client.get("/api/health/llm")
        assert resp.status_code == 200
        payload = resp.json()
        assert payload.get("ok") is True
        assert payload.get("status") == "online"
        assert payload.get("provider") == "local"
    finally:
        settings.LLM_PROVIDER = prev_provider
        settings.LOCAL_BASE_URL = prev_local_base


def test_health_llm_cloud_configured_is_truthful_unknown(monkeypatch):
    from guardian.core.config import get_settings

    settings = get_settings()
    snapshot = {
        "LLM_PROVIDER": settings.LLM_PROVIDER,
        "ALLOW_CLOUD_PROVIDERS": settings.ALLOW_CLOUD_PROVIDERS,
        "CODEXIFY_LOCAL_ONLY_MODE": settings.CODEXIFY_LOCAL_ONLY_MODE,
        "CODEXIFY_EGRESS_ALLOWLIST": settings.CODEXIFY_EGRESS_ALLOWLIST,
        "GROQ_API_KEY": settings.GROQ_API_KEY,
    }

    monkeypatch.setattr(
        "guardian.routes.health._collect_completion_service_health",
        lambda: {
            "ok": True,
            "redis_reachable": True,
            "enqueue_test_ok": True,
            "worker_heartbeat_detected": True,
            "worker_heartbeat_age_seconds": 0.5,
            "status_reason": "ok",
            "error": None,
        },
    )

    settings.LLM_PROVIDER = "groq"
    settings.ALLOW_CLOUD_PROVIDERS = True
    settings.CODEXIFY_LOCAL_ONLY_MODE = False
    settings.CODEXIFY_EGRESS_ALLOWLIST = "groq"
    settings.GROQ_API_KEY = "groq-key"

    client = TestClient(app)
    try:
        resp = client.get("/api/health/llm")
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["provider"] == "groq"
        assert payload["status"] == "unknown"
        assert payload["ok"] is False
        assert payload["mode"] == "runtime_unprobed"
        assert payload["provider_runtime"]["enabled"] is True
        assert payload["completion_service"]["status_reason"] == "ok"
    finally:
        for field, value in snapshot.items():
            setattr(settings, field, value)


def test_health_and_catalog_share_dynamic_provider_model_index_state(
    monkeypatch,
):
    from guardian.core.config import get_settings

    class _Resp:
        def __init__(self, payload, status_code=200):
            self._payload = payload
            self.status_code = status_code

        def json(self):
            return self._payload

    settings = get_settings()
    snapshot = {
        "LLM_PROVIDER": settings.LLM_PROVIDER,
        "ALLOW_CLOUD_PROVIDERS": settings.ALLOW_CLOUD_PROVIDERS,
        "CODEXIFY_LOCAL_ONLY_MODE": settings.CODEXIFY_LOCAL_ONLY_MODE,
        "CODEXIFY_EGRESS_ALLOWLIST": settings.CODEXIFY_EGRESS_ALLOWLIST,
        "MINIMAX_API_KEY": settings.MINIMAX_API_KEY,
        "MINIMAX_API_BASE": settings.MINIMAX_API_BASE,
        "MINIMAX_MODEL": settings.MINIMAX_MODEL,
    }

    monkeypatch.setattr(
        "guardian.routes.health._collect_completion_service_health",
        lambda: {
            "ok": True,
            "redis_reachable": True,
            "enqueue_test_ok": True,
            "worker_heartbeat_detected": True,
            "worker_heartbeat_age_seconds": 0.5,
            "status_reason": "ok",
            "error": None,
        },
    )
    monkeypatch.setattr(
        "guardian.core.llm_catalog.requests.get",
        lambda url, *args, **kwargs: _Resp({"data": []}, status_code=404),
    )
    monkeypatch.setattr(
        "guardian.core.provider_registry.requests.get",
        lambda url, headers, timeout: (_ for _ in ()).throw(
            requests.exceptions.Timeout("timed out")
        ),
    )

    settings.LLM_PROVIDER = "minimax"
    settings.ALLOW_CLOUD_PROVIDERS = True
    settings.CODEXIFY_LOCAL_ONLY_MODE = False
    settings.CODEXIFY_EGRESS_ALLOWLIST = "minimax"
    settings.MINIMAX_API_KEY = "minimax-key"
    settings.MINIMAX_API_BASE = "https://api.minimax.local/v1"
    settings.MINIMAX_MODEL = "minimax-chat"

    client = TestClient(app)
    try:
        health = client.get("/api/health/llm")
        assert health.status_code == 200
        health_payload = health.json()

        catalog = client.get("/api/llm/catalog")
        assert catalog.status_code == 200
        catalog_payload = catalog.json()
        minimax = next(
            provider
            for provider in catalog_payload["providers"]
            if provider["id"] == "minimax"
        )

        assert health_payload["provider"] == "minimax"
        assert health_payload["model"] == "minimax-chat"
        assert (
            health_payload["provider_runtime"]["model_index"]
            == minimax["model_index"]
        )
        assert (
            health_payload["provider_runtime"]["available"]
            == minimax["available"]
        )
        assert (
            health_payload["provider_runtime"]["enabled"] == minimax["enabled"]
        )
        assert minimax["model_index"]["state"] == "degraded"
        assert "timed out" in minimax["model_index"]["reason"].lower()
    finally:
        for field, value in snapshot.items():
            setattr(settings, field, value)


def test_completion_service_health_computes_heartbeat_age(monkeypatch):
    fixed_now = 1_700_000_000.0
    heartbeat_age = 27.5
    heartbeat_payload = json.dumps({"ts": fixed_now - heartbeat_age}).encode(
        "utf-8"
    )

    monkeypatch.setattr(
        "guardian.queue.redis_queue.get_redis_client",
        lambda: _FakeRedisClient(heartbeat_payload),
    )
    monkeypatch.setattr(health_routes.time, "time", lambda: fixed_now)

    payload = health_routes._collect_completion_service_health()

    assert payload["redis_reachable"] is True
    assert payload["worker_heartbeat_detected"] is True
    assert payload["worker_heartbeat_status"] == "stale"
    assert payload["worker_heartbeat_age_seconds"] == pytest.approx(
        heartbeat_age, abs=0.001
    )


@pytest.mark.parametrize(
    (
        "completion_service",
        "expected_ok",
        "expected_status",
        "expected_worker_status",
        "expected_note",
    ),
    [
        (
            {
                "redis_reachable": True,
                "enqueue_test_ok": False,
                "worker_heartbeat_detected": True,
                "worker_heartbeat_age_seconds": 0.5,
                "status_reason": "queue_enqueue_failed",
                "error": None,
            },
            False,
            "unhealthy",
            "fresh",
            "queue round-trip probe failed",
        ),
        (
            {
                "redis_reachable": True,
                "enqueue_test_ok": True,
                "worker_heartbeat_detected": True,
                "worker_heartbeat_age_seconds": 0.5,
                "status_reason": "ok",
                "error": None,
            },
            True,
            "healthy",
            "fresh",
            None,
        ),
        (
            {
                "redis_reachable": True,
                "enqueue_test_ok": True,
                "worker_heartbeat_detected": True,
                "worker_heartbeat_age_seconds": 10.0,
                "status_reason": "ok",
                "error": None,
            },
            True,
            "healthy",
            "fresh",
            None,
        ),
        (
            {
                "redis_reachable": True,
                "enqueue_test_ok": True,
                "worker_heartbeat_detected": True,
                "worker_heartbeat_age_seconds": 10.001,
                "status_reason": "ok",
                "error": None,
            },
            False,
            "degraded",
            "stale",
            "worker heartbeat stale",
        ),
        (
            {
                "redis_reachable": True,
                "enqueue_test_ok": True,
                "worker_heartbeat_detected": True,
                "worker_heartbeat_age_seconds": 60.0,
                "status_reason": "ok",
                "error": None,
            },
            False,
            "degraded",
            "stale",
            "worker heartbeat stale",
        ),
        (
            {
                "redis_reachable": True,
                "enqueue_test_ok": True,
                "worker_heartbeat_detected": True,
                "worker_heartbeat_age_seconds": 60.001,
                "status_reason": "ok",
                "error": None,
            },
            False,
            "unhealthy",
            "dead",
            "worker heartbeat dead",
        ),
        (
            {
                "redis_reachable": True,
                "enqueue_test_ok": True,
                "worker_heartbeat_detected": False,
                "worker_heartbeat_age_seconds": None,
                "status_reason": "worker_heartbeat_missing",
                "error": None,
            },
            False,
            "unhealthy",
            "dead",
            "worker heartbeat missing",
        ),
        (
            {
                "redis_reachable": False,
                "enqueue_test_ok": False,
                "worker_heartbeat_detected": False,
                "worker_heartbeat_age_seconds": None,
                "status_reason": "redis_unreachable",
                "error": None,
            },
            False,
            "unhealthy",
            "dead",
            "redis unreachable",
        ),
    ],
)
def test_health_chat_classifies_worker_freshness(
    monkeypatch,
    completion_service,
    expected_ok,
    expected_status,
    expected_worker_status,
    expected_note,
):
    monkeypatch.setattr(
        health_routes,
        "_collect_completion_service_health",
        lambda: completion_service,
    )

    client = TestClient(app)
    resp = client.get("/health/chat")
    assert resp.status_code == 200

    payload = resp.json()
    assert payload["ok"] is expected_ok
    assert payload["status"] == expected_status
    assert payload["redis"] == (
        "ok"
        if completion_service["redis_reachable"]
        and completion_service["enqueue_test_ok"]
        else "unhealthy"
    )
    assert payload["worker"]["status"] == expected_worker_status
    if completion_service["worker_heartbeat_detected"]:
        assert (
            payload["worker"]["heartbeat_age_seconds"]
            == completion_service["worker_heartbeat_age_seconds"]
        )
    else:
        assert payload["worker"]["heartbeat_age_seconds"] is None

    if expected_note is None:
        assert payload["notes"] == []
    else:
        assert any(
            expected_note in str(note).lower() for note in payload["notes"]
        )
