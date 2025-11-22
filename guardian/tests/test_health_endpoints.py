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
