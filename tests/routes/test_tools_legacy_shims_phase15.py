from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from guardian.routes import command_bus, tools


def _build_client(monkeypatch) -> TestClient:
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-key")
    monkeypatch.setenv(
        "GUARDIAN_COMMAND_BUS_LOOPBACK_BASE", "http://127.0.0.1:9999"
    )
    command_bus.configure_db(None)
    tools.JOBS.clear()

    app = FastAPI()

    @app.get("/health", operation_id="health_check")
    def health(check: str | None = None) -> dict[str, Any]:
        return {"ok": True, "check": check}

    @app.post("/write", operation_id="write_item")
    def write(payload: dict[str, Any]) -> dict[str, Any]:
        return {"ok": True, "payload": payload}

    app.include_router(command_bus.router)
    app.include_router(tools.router)
    app.include_router(tools.api_router)
    return TestClient(app)


def _auth_headers(user_id: str | None = "operator") -> dict[str, str]:
    headers = {"X-API-Key": "test-key"}
    if user_id is not None:
        headers["X-User-Id"] = user_id
    return headers


def _install_fake_loopback(monkeypatch, captured: list[dict[str, Any]]) -> None:
    class _FakeResponse:
        status_code = 200
        headers = {"content-type": "application/json"}

        @property
        def text(self) -> str:
            return '{"ok": true}'

        def json(self) -> dict[str, bool]:
            return {"ok": True}

    class _FakeAsyncClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            _ = args, kwargs

        async def __aenter__(self) -> "_FakeAsyncClient":
            return self

        async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
            _ = exc_type, exc, tb

        async def request(self, **kwargs: Any) -> _FakeResponse:
            captured.append(dict(kwargs))
            return _FakeResponse()

    monkeypatch.setattr(
        "guardian.command_bus.loopback_http_adapter.httpx.AsyncClient",
        _FakeAsyncClient,
    )


def test_legacy_manifest_returns_deprecation_header(monkeypatch) -> None:
    client = _build_client(monkeypatch)

    response = client.get("/tools/manifest", headers=_auth_headers())
    assert response.status_code == 200
    assert response.headers["X-Codexify-Deprecated"] == "true"
    assert (
        response.headers["X-Codexify-Deprecation-Replaced-By"]
        == "/api/guardian/commands/manifest"
    )
    assert response.headers["X-Codexify-Deprecation-Phase"] == "1.5"

    payload = response.json()
    assert isinstance(payload, list)
    assert any(item.get("name") == "op::health_check" for item in payload)

    alias_response = client.get("/api/tools/manifest", headers=_auth_headers())
    assert alias_response.status_code == 200
    assert alias_response.headers["X-Codexify-Deprecated"] == "true"


def test_legacy_execute_forward_read_only_not_blocked(monkeypatch) -> None:
    captured: list[dict[str, Any]] = []
    _install_fake_loopback(monkeypatch, captured)
    client = _build_client(monkeypatch)

    response = client.post(
        "/tools/execute",
        headers=_auth_headers(),
        json={"name": "health_check", "args": {"check": "yes"}},
    )
    assert response.status_code == 200
    assert response.headers["X-Codexify-Deprecated"] == "true"
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["job_id"] == payload["run_id"]
    assert payload["command_id"] == "op::health_check"
    assert payload["result"]["status_code"] == 200

    assert len(captured) == 1
    assert captured[0]["method"] == "GET"
    assert captured[0]["url"] == "http://127.0.0.1:9999/health"
    assert captured[0]["params"] == {"check": "yes"}


def test_legacy_execute_blocks_mutating_commands(monkeypatch) -> None:
    client = _build_client(monkeypatch)
    response = client.post(
        "/api/tools/execute",
        headers=_auth_headers(),
        json={"method": "POST", "path": "/write", "args": {"value": 1}},
    )
    assert response.status_code == 200
    assert response.headers["X-Codexify-Deprecated"] == "true"
    payload = response.json()
    assert payload["status"] == "blocked"
    assert payload["error"] == "phase1_write_blocked"
    assert payload["result"]["error"] == "phase1_write_blocked"


def test_legacy_execute_synthesizes_actor_from_x_user_id(monkeypatch) -> None:
    captured: list[dict[str, Any]] = []
    _install_fake_loopback(monkeypatch, captured)
    client = _build_client(monkeypatch)

    response = client.post(
        "/tools/execute",
        headers=_auth_headers(user_id="shim-operator"),
        json={"name": "health_check", "args": {"check": "actor"}},
    )
    assert response.status_code == 200
    payload = response.json()
    run_id = payload["job_id"]

    run = command_bus._store.get_run(run_id)
    assert run is not None
    assert run["actor_kind"] == "human"
    assert run["actor_id"] == "shim-operator"
    assert run["auth_subject"] == "shim-operator"


def test_legacy_execute_synthesizes_actor_from_single_user_fallback(
    monkeypatch,
) -> None:
    captured: list[dict[str, Any]] = []
    _install_fake_loopback(monkeypatch, captured)
    monkeypatch.setenv("CODEXIFY_SINGLE_USER_ID", "single-user")
    client = _build_client(monkeypatch)

    response = client.post(
        "/tools/execute",
        headers=_auth_headers(user_id=None),
        json={"name": "health_check", "args": {"check": "fallback"}},
    )
    assert response.status_code == 200
    payload = response.json()
    run_id = payload["job_id"]

    run = command_bus._store.get_run(run_id)
    assert run is not None
    assert run["actor_kind"] == "human"
    assert run["actor_id"] == "single-user"
    assert run["auth_subject"] == "single-user"


def test_legacy_execute_rejects_missing_actor_and_identity(monkeypatch) -> None:
    client = _build_client(monkeypatch)
    monkeypatch.setattr(tools, "_resolve_auth_subject", lambda _request: None)

    response = client.post(
        "/tools/execute",
        headers=_auth_headers(user_id=None),
        json={"name": "health_check"},
    )
    assert response.status_code == 401
    assert response.headers["X-Codexify-Deprecated"] == "true"
    assert response.json()["detail"]["error"] == "missing_identity_context"
