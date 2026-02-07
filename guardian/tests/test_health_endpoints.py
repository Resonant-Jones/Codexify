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
