from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from guardian.command_bus.contracts import CommandSpec
from guardian.command_bus import loopback_http_adapter
from guardian.routes import command_bus, projects
from guardian.tools.chat_exposure import resolve_ordinary_chat_tools


def _build_client(monkeypatch) -> TestClient:
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-key")
    monkeypatch.setenv("DEBUG", "1")
    command_bus.configure_db(None)
    app = FastAPI()

    @app.get("/health", operation_id="health_health_get")
    def health() -> dict[str, bool]:
        return {"ok": True}

    def current_user(request: Request) -> str:
        return request.headers.get("X-User-Id", "operator")

    app.dependency_overrides[command_bus.get_current_user] = current_user
    app.include_router(projects.api_router)
    app.include_router(command_bus.router)
    return TestClient(app)


def _manifest(client: TestClient) -> dict[str, Any]:
    response = client.get(
        "/api/guardian/commands/manifest",
        headers={"X-API-Key": "test-key", "X-User-Id": "operator"},
    )
    assert response.status_code == 200
    return response.json()


def _repository_command(manifest: dict[str, Any]) -> dict[str, Any]:
    matches = [
        command
        for command in manifest["commands"]
        if command.get("operation_id") == "repository.search"
    ]
    assert len(matches) == 1
    return matches[0]


def test_repository_search_manifest_is_derived_from_projects_openapi(
    monkeypatch,
) -> None:
    command = _repository_command(_manifest(_build_client(monkeypatch)))

    assert command["command_id"] == "op::repository.search"
    assert command["aliases"] == [
        "route::GET::/api/projects/{project_id}/repository/search"
    ]
    assert command["method"] == "GET"
    assert command["path_template"] == "/api/projects/{project_id}/repository/search"
    assert command["operation_id"] == "repository.search"
    assert command["layer"] == "raw"
    assert command["risk"] == "read_only"
    assert command["effect"] == "read"
    assert command["idempotency"] == "safe"
    assert command["approval_mode"] == "none"

    input_schema = command["input_schema"]
    assert input_schema["path_params"]["required"] == ["project_id"]
    assert "project_id" in input_schema["path_params"]["properties"]
    assert input_schema["query"]["required"] == ["q"]
    assert set(input_schema["query"]["properties"]) == {"q", "limit"}
    serialized = repr(input_schema)
    for forbidden in (
        "repository_root",
        "canonical_root",
        "discovery_root",
        "account_id",
        "user_id",
        "binding_id",
        "repoPath",
        "cwd",
    ):
        assert forbidden not in serialized


def test_repository_search_command_invokes_once_over_loopback(
    monkeypatch,
) -> None:
    captured: list[dict[str, Any]] = []

    class _FakeResponse:
        status_code = 200
        headers = {"content-type": "application/json"}

        @property
        def text(self) -> str:
            return '{"ok": true}'

        def json(self) -> dict[str, Any]:
            return {
                "ok": True,
                "matches": [
                    {
                        "path": "src/example.py",
                        "line": 2,
                        "snippet": "needle",
                    }
                ],
            }

    class _FakeAsyncClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            _ = args, kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            _ = exc_type, exc, tb

        async def request(self, **kwargs: Any) -> _FakeResponse:
            captured.append(dict(kwargs))
            return _FakeResponse()

    monkeypatch.setenv(
        "GUARDIAN_COMMAND_BUS_LOOPBACK_BASE", "http://127.0.0.1:9999"
    )
    monkeypatch.setattr(
        loopback_http_adapter.httpx, "AsyncClient", _FakeAsyncClient
    )
    client = _build_client(monkeypatch)
    command = _repository_command(_manifest(client))

    response = client.post(
        "/api/guardian/commands/invoke",
        headers={"X-API-Key": "test-key", "X-User-Id": "operator"},
        json={
            "invoke_version": "1.0",
            "command_id": command["command_id"],
            "actor": {"kind": "human", "id": "operator"},
            "arguments": {
                "path_params": {"project_id": 42},
                "query": {"q": "needle", "limit": 5},
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["inline_result"]["status_code"] == 200
    assert len(captured) == 1
    assert captured[0]["method"] == "GET"
    assert (
        captured[0]["url"]
        == "http://127.0.0.1:9999/api/projects/42/repository/search"
    )
    assert captured[0]["params"] == {"q": "needle", "limit": 5}
    assert "json" not in captured[0]
    forwarded = {key.lower(): value for key, value in captured[0]["headers"].items()}
    assert forwarded["x-api-key"] == "test-key"
    assert forwarded["x-user-id"] == "operator"

    events = command_bus.get_store().list_events_after(
        run_id=payload["run_id"], after_seq=0
    )
    assert [event["event_type"] for event in events] == [
        "run.created",
        "run.started",
        "run.completed",
    ]


def test_repository_search_is_never_in_ordinary_chat_exposure() -> None:
    health = CommandSpec(
        command_id="op::health_health_get",
        aliases=["route::GET::/health"],
        layer="raw",
        method="GET",
        path_template="/health",
        operation_id="health_health_get",
        risk="read_only",
        effect="read",
        idempotency="safe",
        approval_mode="none",
        input_schema={
            "path_params": {"properties": {}, "required": []},
            "query": {"properties": {}, "required": []},
            "headers": {"properties": {}, "required": []},
            "body": {},
        },
    )
    repository_search = CommandSpec(
        command_id="op::repository.search",
        aliases=[
            "route::GET::/api/projects/{project_id}/repository/search"
        ],
        layer="raw",
        method="GET",
        path_template="/api/projects/{project_id}/repository/search",
        operation_id="repository.search",
        risk="read_only",
        effect="read",
        idempotency="safe",
        approval_mode="none",
        input_schema={
            "path_params": {"properties": {"project_id": {}}, "required": ["project_id"]},
            "query": {"properties": {"q": {}}, "required": ["q"]},
            "headers": {"properties": {}, "required": []},
            "body": {},
        },
    )

    tools = resolve_ordinary_chat_tools(
        provider="deepseek",
        model="model",
        provider_vendor=None,
        manifest_commands=[health, repository_search],
    )
    assert tools == [
        {
            "command_id": "op::health_health_get",
            "description": "Read the current Guardian health status (GET /health).",
            "input_schema": {
                "type": "object",
                "additionalProperties": False,
                "maxProperties": 0,
            },
        }
    ]
    assert all(tool["command_id"] != "op::repository.search" for tool in tools)
