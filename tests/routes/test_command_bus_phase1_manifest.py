from __future__ import annotations

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

    app.include_router(command_bus.router)
    return TestClient(app)


def _find_command(manifest: dict, *, method: str, path_template: str) -> dict:
    for command in manifest.get("commands", []):
        if (
            command.get("method") == method
            and command.get("path_template") == path_template
        ):
            return command
    raise AssertionError(f"command not found for {method} {path_template}")


def test_manifest_includes_versions_capabilities_and_stable_ids(
    monkeypatch,
) -> None:
    client = _build_client(monkeypatch)

    response = client.get(
        "/api/guardian/commands/manifest",
        headers={"X-API-Key": "test-key", "X-User-Id": "operator"},
    )
    assert response.status_code == 200
    payload = response.json()

    assert payload["manifest_version"] == "1.0"
    assert payload["generated_at"]
    capabilities = payload["capabilities"]
    assert capabilities["invoke_versions_supported"] == ["1.0"]
    assert capabilities["event_protocol_version"] == "1.0"
    assert "run.blocked" in capabilities["event_types_supported"]
    assert capabilities["approval_modes_supported"] == [
        "none",
        "blocked_phase1",
    ]
    assert capabilities["max_payload_bytes"] > 0

    health = _find_command(payload, method="GET", path_template="/health")
    assert health["command_id"] == "op::health_check"
    assert "route::GET::/health" in health["aliases"]
    assert health["layer"] == "raw"
    assert health["risk"] == "read_only"
    assert health["effect"] == "read"
    assert health["idempotency"] == "safe"
    assert health["approval_mode"] == "none"
    assert set(health["input_schema"].keys()) == {
        "path_params",
        "query",
        "headers",
        "body",
    }
