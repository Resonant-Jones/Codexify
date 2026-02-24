from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from guardian.routes import command_bus, tools


def _build_client(monkeypatch) -> TestClient:
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-key")
    command_bus.configure_db(None)
    tools.JOBS.clear()

    app = FastAPI()

    @app.get("/ping", operation_id="ping_ping_get")
    def ping() -> dict[str, bool]:
        return {"ok": True}

    @app.post("/write", operation_id="write_item")
    def write(payload: dict[str, Any]) -> dict[str, Any]:
        return {"ok": True, "payload": payload}

    app.include_router(command_bus.router)
    app.include_router(tools.router)
    app.include_router(tools.api_router)
    return TestClient(app)


def _auth_headers() -> dict[str, str]:
    return {"X-API-Key": "test-key", "X-User-Id": "local"}


def test_manifest_default_returns_envelope(monkeypatch) -> None:
    client = _build_client(monkeypatch)

    response = client.get("/api/tools/manifest", headers=_auth_headers())
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, dict)
    assert payload["tool_manifest_version"] == "2.0"
    assert isinstance(payload["manifest_version"], str)
    assert isinstance(payload["generated_at"], str)
    assert isinstance(payload["command_manifest_hash"], str)
    assert len(payload["command_manifest_hash"]) == 64
    assert isinstance(payload["tools"], list)
    assert isinstance(payload["openai_tools"], list)


def test_manifest_route_ownership_and_openapi_format_param(monkeypatch) -> None:
    client = _build_client(monkeypatch)

    # Route ownership and no-shadowing check.
    route_map: dict[str, list[str]] = {}
    for route in client.app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", set())
        endpoint = getattr(route, "endpoint", None)
        if (
            path in {"/api/tools/manifest", "/tools/manifest"}
            and "GET" in methods
        ):
            route_map.setdefault(path, []).append(
                f"{endpoint.__module__}.{endpoint.__name__}"
            )

    assert route_map["/api/tools/manifest"] == [
        "guardian.routes.tools.api_tools_manifest"
    ]
    assert route_map["/tools/manifest"] == [
        "guardian.routes.tools.tools_manifest"
    ]

    # OpenAPI must advertise the format query param.
    openapi = client.get("/openapi.json").json()
    params = (
        openapi.get("paths", {})
        .get("/api/tools/manifest", {})
        .get("get", {})
        .get("parameters", [])
    )
    param_names = [item.get("name") for item in params]
    assert "format" in param_names


def test_manifest_explicit_envelope_format(monkeypatch) -> None:
    client = _build_client(monkeypatch)
    response = client.get(
        "/api/tools/manifest?format=envelope", headers=_auth_headers()
    )
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, dict)
    assert "tools" in payload
    assert isinstance(payload["tools"], list)


def test_manifest_format_array_matches_envelope_length(monkeypatch) -> None:
    client = _build_client(monkeypatch)
    envelope = client.get("/api/tools/manifest", headers=_auth_headers()).json()

    response = client.get(
        "/api/tools/manifest?format=array", headers=_auth_headers()
    )
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    assert len(payload) == len(envelope["tools"])
    assert payload
    first = payload[0]
    assert "name" in first
    assert "command_id" in first
    assert "args_schema" in first


def test_manifest_hash_is_deterministic(monkeypatch) -> None:
    client = _build_client(monkeypatch)
    first = client.get("/api/tools/manifest", headers=_auth_headers()).json()
    second = client.get("/api/tools/manifest", headers=_auth_headers()).json()
    assert first["command_manifest_hash"] == second["command_manifest_hash"]


def test_tools_alias_mirrors_api_manifest(monkeypatch) -> None:
    client = _build_client(monkeypatch)

    api_envelope = client.get(
        "/api/tools/manifest", headers=_auth_headers()
    ).json()
    tools_envelope_response = client.get(
        "/tools/manifest", headers=_auth_headers()
    )
    assert tools_envelope_response.status_code == 200
    tools_envelope = tools_envelope_response.json()
    assert isinstance(tools_envelope, dict)
    assert (
        tools_envelope["command_manifest_hash"]
        == api_envelope["command_manifest_hash"]
    )
    assert len(tools_envelope["tools"]) == len(api_envelope["tools"])

    api_array = client.get(
        "/api/tools/manifest?format=array", headers=_auth_headers()
    ).json()
    tools_array = client.get(
        "/tools/manifest?format=array", headers=_auth_headers()
    ).json()
    assert isinstance(api_array, list)
    assert isinstance(tools_array, list)
    assert len(api_array) == len(tools_array)


def test_manifest_bad_format_returns_400(monkeypatch) -> None:
    client = _build_client(monkeypatch)
    response = client.get(
        "/api/tools/manifest?format=unsupported", headers=_auth_headers()
    )
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["error"] == "invalid_manifest_format"


def test_manifest_auth_rejects_blank_api_key_on_both_prefixes(
    monkeypatch,
) -> None:
    client = _build_client(monkeypatch)
    blank_headers = {"X-API-Key": "", "X-User-Id": "local"}

    api_response = client.get("/api/tools/manifest", headers=blank_headers)
    tools_response = client.get("/tools/manifest", headers=blank_headers)

    assert api_response.status_code == 401
    assert tools_response.status_code == 401
