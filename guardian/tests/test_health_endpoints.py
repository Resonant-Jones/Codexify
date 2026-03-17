import requests
from fastapi.testclient import TestClient

from guardian.guardian_api import app


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
        assert minimax["models"] == []
        assert minimax["model_index"]["state"] == "degraded"
        assert "timed out" in minimax["model_index"]["reason"].lower()
    finally:
        for field, value in snapshot.items():
            setattr(settings, field, value)
