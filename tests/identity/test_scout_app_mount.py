"""Actual app mount proof without running database-producing lifespan startup."""

from fastapi.testclient import TestClient


def test_actual_app_mounts_handoff_and_rejects_unqualified_transport(monkeypatch):
    monkeypatch.setenv("GUARDIAN_API_KEY", "synthetic-app-mount-fixture")
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "private_preview")
    from guardian.guardian_api import app

    paths = {route.path for route in app.routes}
    assert {"/api/auth/scout/handoff", "/api/auth/scout/exchange"} <= paths
    # No context manager: do not start application/database lifespan hooks.
    with_client = TestClient(app, base_url="https://preview.codexify.space")
    response = with_client.post(
        "/api/auth/scout/exchange", json={"code": "c" * 43, "verifier": "v" * 43}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Hosted admission required"
    denied = with_client.get(
        "/api/chat/threads",
        headers={
            "Authorization": "Bearer oauth:synthetic",
            "X-Guardian-Account-Session": "synthetic",
        },
    )
    assert denied.status_code == 400
    assert denied.json()["detail"] == "Hosted account transport rejected"
    with_client.close()
