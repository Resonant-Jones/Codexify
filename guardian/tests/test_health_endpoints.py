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
