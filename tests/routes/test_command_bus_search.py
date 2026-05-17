from __future__ import annotations

import importlib
import os
from contextlib import contextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from guardian.routes import command_bus

_GUARDIAN_API_ENV_KEYS = (
    "GUARDIAN_API_KEY",
    "ENABLE_CONNECTOR_WORKER",
    "GUARDIAN_EXPOSURE_MODE",
    "GUARDIAN_PUBLIC_PROFILE",
    "GUARDIAN_PUBLIC_ROUTES_FILE",
    "CODEXIFY_SUPPORTED_PROFILE",
)


def _snapshot_guardian_api_env() -> dict[str, str | None]:
    return {key: os.environ.get(key) for key in _GUARDIAN_API_ENV_KEYS}


def _restore_guardian_api_env(snapshot: dict[str, str | None]) -> None:
    for key, value in snapshot.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


def _build_client(monkeypatch) -> TestClient:
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-key")
    monkeypatch.setenv("DEBUG", "1")
    command_bus.configure_db(None)

    app = FastAPI()

    @app.get("/health", operation_id="health_check")
    def health() -> dict[str, bool]:
        return {"ok": True}

    @app.get("/projects/{project_id}", operation_id="project_lookup")
    def project_lookup(project_id: int) -> dict[str, Any]:
        return {"project_id": project_id}

    app.include_router(command_bus.router)
    return TestClient(app)


@contextmanager
def _build_public_allowlist_client(monkeypatch):
    snapshot = _snapshot_guardian_api_env()
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-api-key")
    monkeypatch.setenv("ENABLE_CONNECTOR_WORKER", "0")
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "public_allowlist")
    monkeypatch.setenv("GUARDIAN_PUBLIC_PROFILE", "connectors_runtime")
    monkeypatch.setenv(
        "GUARDIAN_PUBLIC_ROUTES_FILE", "config/public_routes.yaml"
    )
    monkeypatch.setenv("CODEXIFY_SUPPORTED_PROFILE", "v1-local-core-web-mcp")

    import guardian.guardian_api as guardian_api

    guardian_api = importlib.reload(guardian_api)
    client = TestClient(guardian_api.app)
    try:
        yield client
    finally:
        client.close()
        _restore_guardian_api_env(snapshot)
        from guardian.core import event_bus

        event_bus.reset()
        importlib.reload(guardian_api)


def test_search_endpoint_returns_matching_command_result(monkeypatch) -> None:
    client = _build_client(monkeypatch)

    response = client.get(
        "/api/guardian/commands/search",
        params={"q": "health", "limit": 20},
        headers={"X-API-Key": "test-key", "X-User-Id": "operator"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == "health"
    assert payload["results"]
    assert payload["results"][0]["command_id"] == "op::health_check"


def test_search_endpoint_respects_limit(monkeypatch) -> None:
    client = _build_client(monkeypatch)

    response = client.get(
        "/api/guardian/commands/search",
        params={"q": "op::", "limit": 1},
        headers={"X-API-Key": "test-key", "X-User-Id": "operator"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["limit"] == 1
    assert len(payload["results"]) == 1


def test_search_endpoint_returns_empty_results_for_blank_query(monkeypatch) -> None:
    client = _build_client(monkeypatch)

    response = client.get(
        "/api/guardian/commands/search",
        params={"q": "   ", "limit": 20},
        headers={"X-API-Key": "test-key", "X-User-Id": "operator"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["results"] == []


def test_search_endpoint_does_not_call_command_execution(monkeypatch) -> None:
    client = _build_client(monkeypatch)
    called = {"invoke": 0}

    async def _unexpected_invoke(*args: Any, **kwargs: Any) -> dict[str, Any]:
        called["invoke"] += 1
        raise AssertionError("invoke should not be called by search")

    monkeypatch.setattr(command_bus, "execute_invoke", _unexpected_invoke)

    response = client.get(
        "/api/guardian/commands/search",
        params={"q": "health", "limit": 20},
        headers={"X-API-Key": "test-key", "X-User-Id": "operator"},
    )

    assert response.status_code == 200
    assert called["invoke"] == 0


def test_search_endpoint_respects_internal_surface_posture(monkeypatch) -> None:
    with _build_public_allowlist_client(monkeypatch) as client:
        response = client.get(
            "/api/guardian/commands/search",
            params={"q": "health", "limit": 20},
            headers={"X-API-Key": "test-api-key"},
        )

    assert response.status_code == 403
    assert response.json() == {"ok": False, "error": "forbidden"}
