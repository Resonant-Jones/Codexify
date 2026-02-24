from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from guardian.routes import command_bus


def _build_client(monkeypatch) -> TestClient:
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-key")
    monkeypatch.setenv("DEBUG", "1")
    command_bus.configure_db(None)

    app = FastAPI()

    @app.get("/health", operation_id="health_check")
    def health() -> dict[str, bool]:
        return {"ok": True}

    @app.post("/write", operation_id="write_item")
    def write(payload: dict[str, Any]) -> dict[str, Any]:
        return {"ok": True, "payload": payload}

    app.include_router(command_bus.router)
    return TestClient(app)


def _get_manifest(client: TestClient) -> dict[str, Any]:
    response = client.get(
        "/api/guardian/commands/manifest",
        headers={"X-API-Key": "test-key", "X-User-Id": "operator"},
    )
    assert response.status_code == 200
    return response.json()


def _command_id(manifest: dict[str, Any], *, method: str, path: str) -> str:
    for command in manifest.get("commands", []):
        if (
            command.get("method") == method
            and command.get("path_template") == path
        ):
            return str(command["command_id"])
    raise AssertionError(f"missing command for {method} {path}")


def test_invoke_rejects_missing_actor(monkeypatch) -> None:
    client = _build_client(monkeypatch)
    manifest = _get_manifest(client)
    health_command_id = _command_id(manifest, method="GET", path="/health")

    response = client.post(
        "/api/guardian/commands/invoke",
        headers={"X-API-Key": "test-key", "X-User-Id": "operator"},
        json={
            "invoke_version": "1.0",
            "command_id": health_command_id,
            "arguments": {},
        },
    )
    assert response.status_code == 422


def test_invoke_rejects_unsupported_version(monkeypatch) -> None:
    client = _build_client(monkeypatch)
    manifest = _get_manifest(client)
    health_command_id = _command_id(manifest, method="GET", path="/health")

    response = client.post(
        "/api/guardian/commands/invoke",
        headers={"X-API-Key": "test-key", "X-User-Id": "operator"},
        json={
            "invoke_version": "9.9",
            "command_id": health_command_id,
            "actor": {"kind": "human", "id": "operator"},
            "arguments": {},
        },
    )
    assert response.status_code == 400
    payload = response.json()["detail"]
    assert payload["error"] == "unsupported_invoke_version"
    assert payload["supported_invoke_versions"] == ["1.0"]


def test_invoke_rejects_actor_claim_mismatch(monkeypatch) -> None:
    client = _build_client(monkeypatch)
    manifest = _get_manifest(client)
    health_command_id = _command_id(manifest, method="GET", path="/health")

    response = client.post(
        "/api/guardian/commands/invoke",
        headers={"X-API-Key": "test-key", "X-User-Id": "operator"},
        json={
            "invoke_version": "1.0",
            "command_id": health_command_id,
            "actor": {"kind": "human", "id": "someone-else"},
            "arguments": {},
        },
    )
    assert response.status_code == 403
    assert response.json()["detail"]["error"] == "actor_claim_not_permitted"


def test_invoke_blocks_mutating_commands_and_emits_blocked_event(
    monkeypatch,
) -> None:
    client = _build_client(monkeypatch)
    manifest = _get_manifest(client)
    write_command_id = _command_id(manifest, method="POST", path="/write")

    response = client.post(
        "/api/guardian/commands/invoke",
        headers={"X-API-Key": "test-key", "X-User-Id": "operator"},
        json={
            "invoke_version": "1.0",
            "command_id": write_command_id,
            "actor": {"kind": "human", "id": "operator"},
            "arguments": {"body": {"value": 1}},
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "blocked"
    assert payload["error"] in {
        "phase1_write_blocked",
        "policy_require_confirmation:write_effect,risk_high",
    }

    events = command_bus._store.list_events_after(
        run_id=payload["run_id"],
        after_seq=0,
    )
    assert [event["event_type"] for event in events] == [
        "run.created",
        "run.blocked",
    ]


def test_invoke_blocks_recursive_command_targets(monkeypatch) -> None:
    client = _build_client(monkeypatch)
    manifest = _get_manifest(client)
    self_command_id = _command_id(
        manifest, method="GET", path="/api/guardian/commands/manifest"
    )

    response = client.post(
        "/api/guardian/commands/invoke",
        headers={"X-API-Key": "test-key", "X-User-Id": "operator"},
        json={
            "invoke_version": "1.0",
            "command_id": self_command_id,
            "actor": {"kind": "human", "id": "operator"},
            "arguments": {},
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "blocked"
    assert payload["error"] == "recursion_guard_blocked"

    events = command_bus._store.list_events_after(
        run_id=payload["run_id"],
        after_seq=0,
    )
    assert [event["event_type"] for event in events] == [
        "run.created",
        "run.blocked",
    ]


def test_invoke_read_only_uses_loopback_http_and_persists(monkeypatch) -> None:
    captured: list[dict[str, Any]] = []

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

    monkeypatch.setenv(
        "GUARDIAN_COMMAND_BUS_LOOPBACK_BASE", "http://127.0.0.1:9999"
    )
    monkeypatch.setattr(
        "guardian.command_bus.loopback_http_adapter.httpx.AsyncClient",
        _FakeAsyncClient,
    )

    client = _build_client(monkeypatch)
    manifest = _get_manifest(client)
    health_command_id = _command_id(manifest, method="GET", path="/health")

    response = client.post(
        "/api/guardian/commands/invoke",
        headers={"X-API-Key": "test-key", "X-User-Id": "operator"},
        json={
            "invoke_version": "1.0",
            "command_id": health_command_id,
            "actor": {"kind": "human", "id": "operator"},
            "arguments": {"query": {"check": "true"}},
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["inline_result"]["status_code"] == 200
    assert payload["inline_result"]["body"] == {"ok": True}

    assert len(captured) == 1
    assert captured[0]["method"] == "GET"
    assert captured[0]["url"] == "http://127.0.0.1:9999/health"
    assert captured[0]["params"] == {"check": "true"}
    captured_headers = {k.lower(): v for k, v in captured[0]["headers"].items()}
    assert captured_headers["x-api-key"] == "test-key"
    assert captured_headers["x-user-id"] == "operator"

    events = command_bus._store.list_events_after(
        run_id=payload["run_id"],
        after_seq=0,
    )
    assert [event["event_type"] for event in events] == [
        "run.created",
        "run.started",
        "run.completed",
    ]


def test_redaction_is_deterministic_and_hash_is_stable(monkeypatch) -> None:
    client = _build_client(monkeypatch)
    manifest = _get_manifest(client)
    write_command_id = _command_id(manifest, method="POST", path="/write")

    body = {
        "invoke_version": "1.0",
        "command_id": write_command_id,
        "actor": {"kind": "human", "id": "operator"},
        "arguments": {
            "query": {"token": "abc123"},
            "headers": {"Authorization": "Bearer secret", "X-Api-Key": "k1"},
            "body": {"nested": {"password": "pw"}},
        },
    }
    first = client.post(
        "/api/guardian/commands/invoke",
        headers={"X-API-Key": "test-key", "X-User-Id": "operator"},
        json=body,
    )
    second = client.post(
        "/api/guardian/commands/invoke",
        headers={"X-API-Key": "test-key", "X-User-Id": "operator"},
        json=body,
    )
    assert first.status_code == 200
    assert second.status_code == 200

    run1 = command_bus._store.get_run(first.json()["run_id"])
    run2 = command_bus._store.get_run(second.json()["run_id"])
    assert run1 is not None and run2 is not None
    assert run1["args_hash"] == run2["args_hash"]
    assert run1["args_redacted"] == run2["args_redacted"]
    assert run1["args_redacted"]["query"]["token"] == "[REDACTED]"
    assert run1["args_redacted"]["headers"]["Authorization"] == "[REDACTED]"
    assert run1["args_redacted"]["headers"]["X-Api-Key"] == "[REDACTED]"
    assert run1["args_redacted"]["body"]["nested"]["password"] == "[REDACTED]"


def test_invoke_idempotency_reuses_existing_run(monkeypatch) -> None:
    client = _build_client(monkeypatch)
    manifest = _get_manifest(client)
    write_command_id = _command_id(manifest, method="POST", path="/write")

    payload = {
        "invoke_version": "1.0",
        "command_id": write_command_id,
        "actor": {"kind": "human", "id": "operator"},
        "arguments": {"body": {"value": 1}},
        "idempotency_key": "idem-run-1",
    }
    first = client.post(
        "/api/guardian/commands/invoke",
        headers={"X-API-Key": "test-key", "X-User-Id": "operator"},
        json=payload,
    )
    second = client.post(
        "/api/guardian/commands/invoke",
        headers={"X-API-Key": "test-key", "X-User-Id": "operator"},
        json=payload,
    )
    assert first.status_code == 200
    assert second.status_code == 200

    first_payload = first.json()
    second_payload = second.json()
    assert first_payload["run_id"] == second_payload["run_id"]

    run = command_bus._store.get_run_by_idempotency_key(
        write_command_id,
        "idem-run-1",
    )
    assert run is not None
    assert run["run_id"] == first_payload["run_id"]

    events = command_bus._store.list_events_after(
        run_id=first_payload["run_id"],
        after_seq=0,
    )
    assert [event["event_type"] for event in events] == [
        "run.created",
        "run.blocked",
    ]
