"""Tests for the authenticated Guardian dashboard snapshot projection."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from guardian.core import dependencies
from guardian.routes import dashboard
from guardian.routes.heartbeat import HeartbeatStatusResponse


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(dashboard.router)
    return TestClient(app)


def test_dashboard_snapshot_requires_auth(monkeypatch):
    monkeypatch.setenv("GUARDIAN_API_KEY", "dashboard-test-key")
    client = _client()

    response = client.get(
        "/api/dashboard/snapshot", headers={"X-API-Key": "wrong-key"}
    )

    assert response.status_code == 401


def test_dashboard_snapshot_projects_canonical_telemetry_and_empty_orientation(
    monkeypatch,
):
    monkeypatch.setenv("GUARDIAN_API_KEY", "dashboard-test-key")
    monkeypatch.setattr(
        dashboard.health_routes,
        "health",
        lambda _request: {"status": "ok", "service": "core"},
    )
    monkeypatch.setattr(
        dashboard.health_routes,
        "health_llm",
        lambda: {"status": "online", "provider": "local", "model": "test-model"},
    )
    monkeypatch.setattr(
        dashboard.health_routes,
        "health_chat",
        lambda: {
            "status": "healthy",
            "worker": {"status": "fresh"},
            "queue": {"status": "progressing"},
        },
    )

    async def heartbeat_fixture():
        return _heartbeat_fixture()

    monkeypatch.setattr(dashboard, "heartbeat_status", heartbeat_fixture)
    monkeypatch.setattr(dependencies, "_sensors", None)

    response = _client().get(
        "/api/dashboard/snapshot",
        headers={"X-API-Key": "dashboard-test-key"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {
        "schema_version",
        "generated_at",
        "source",
        "health",
        "runtime",
        "host",
        "changes",
        "attention",
        "orientation",
    }
    assert payload["schema_version"] == "guardian.dashboard.snapshot.v1"
    assert payload["health"]["llm"]["model"] == "test-model"
    assert payload["health"]["heartbeat"]["latest_date"] == "2026-07-16"
    assert payload["runtime"] == {
        "provider": "local",
        "model": "test-model",
        "chat_status": "healthy",
        "worker_status": "fresh",
        "queue_status": "progressing",
    }
    assert payload["changes"] == []
    assert payload["attention"] == []
    assert payload["orientation"] == {
        "notes": [],
        "presence": [],
        "mentions": [],
    }
    assert payload["host"]["telemetry_source"] == "guardian.sensors.state.Sensors"


def _heartbeat_fixture():
    return HeartbeatStatusResponse(latest_date="2026-07-16")
