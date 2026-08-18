import importlib
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock

from fastapi.testclient import TestClient


@contextmanager
def _build_supported_profile_client(monkeypatch):
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-api-key")
    monkeypatch.setenv("ENABLE_CONNECTOR_WORKER", "0")
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "local_safe")
    monkeypatch.setenv("CODEXIFY_SUPPORTED_PROFILE", "v1-local-core-web-mcp")

    import guardian.guardian_api as guardian_api

    guardian_api = importlib.reload(guardian_api)
    client = TestClient(guardian_api.app)
    try:
        yield client
    finally:
        client.close()
        from guardian.core import event_bus

        event_bus.reset()
        importlib.reload(guardian_api)


def test_supported_profile_quarantines_legacy_tools_and_hides_command_bus_schema(
    monkeypatch,
) -> None:
    with _build_supported_profile_client(monkeypatch) as client:
        headers = {"X-API-Key": "test-api-key"}

        assert (
            client.get("/api/tools/manifest", headers=headers).status_code
            == 404
        )
        assert client.get("/tools/manifest", headers=headers).status_code == 404

        command_manifest = client.get(
            "/api/guardian/commands/manifest", headers=headers
        )
        assert command_manifest.status_code == 200

        openapi = client.get("/openapi.json").json()
        assert "/api/guardian/commands/manifest" not in openapi.get("paths", {})
        assert "/api/tools/manifest" not in openapi.get("paths", {})
        assert "/tools/manifest" not in openapi.get("paths", {})


def test_supported_profile_mounts_obsidian_routes_without_widening_quarantine(
    monkeypatch, tmp_path
) -> None:
    with _build_supported_profile_client(monkeypatch) as client:
        import guardian.routes.obsidian as obsidian_routes

        vault = tmp_path / "vault"
        vault.mkdir()
        fake_db = MagicMock()
        fake_db.get_connector_config.return_value = None
        fake_db.create_connector_config.side_effect = (
            lambda name, type_, config: {
                "name": name,
                "type": type_,
                "settings": config,
            }
        )
        monkeypatch.setattr(obsidian_routes, "chatlog_db", fake_db)

        openapi = client.get("/openapi.json").json()
        paths = openapi.get("paths", {})
        assert "/api/obsidian/config" in paths
        assert "/api/obsidian/preview" in paths
        assert "/api/obsidian/index" in paths

        unauthenticated = client.get("/api/obsidian/config")
        assert unauthenticated.status_code in {401, 403, 404}

        headers = {"X-API-Key": "test-api-key"}
        configured = client.put(
            "/api/obsidian/config",
            headers=headers,
            json={
                "vault_root": str(vault),
                "allowed_paths": None,
                "allowed_tags": None,
            },
        )
        assert configured.status_code == 200
        assert configured.json()["config"]["vault_root"] == str(
            Path(vault).resolve()
        )

        assert client.get("/api/tools/manifest", headers=headers).status_code == 404
        assert client.get("/api/connectors", headers=headers).status_code == 404


def test_supported_profile_promotes_bounded_settings_and_connections_only(
    monkeypatch,
) -> None:
    with _build_supported_profile_client(monkeypatch) as client:
        headers = {"X-API-Key": "test-api-key"}
        openapi = client.get("/openapi.json").json()
        paths = openapi.get("paths", {})

        assert "/api/imprint/status" in paths
        assert "/api/imprint/proposal" in paths
        assert "/api/system_prompt/summary" in paths
        assert "/api/system_docs" in paths
        assert "/api/connections" in paths
        assert "/api/connectors" not in paths

        assert client.get("/api/connections", headers=headers).status_code == 200
        assert client.get("/api/connectors", headers=headers).status_code == 404

        # The promoted surfaces remain Guardian-authenticated.
        wrong_headers = {"X-API-Key": "wrong-key"}
        assert (
            client.get("/api/imprint/status", headers=wrong_headers).status_code
            in {401, 403}
        )
        assert (
            client.get(
                "/api/system_prompt/summary", headers=wrong_headers
            ).status_code
            in {401, 403}
        )


def test_coding_loop_execute_route_mounted_in_local_profile(
    monkeypatch,
) -> None:
    """Prove POST /api/agents/coding/execute is reachable in the
    supported local operator profile."""
    with _build_supported_profile_client(monkeypatch) as client:
        headers = {"X-API-Key": "test-api-key"}

        response = client.post(
            "/api/agents/coding/execute",
            headers=headers,
            json={
                "coding_task_id": "proof-task-001",
                "thread_id": "1",
                "source_message_id": "1",
                "attempt_id": "attempt-1",
                "user_id": "local",
                "project_id": None,
                "adapter_kind": "pi_codex_runner",
                "instructions": "echo proof",
                "repo_root": "/tmp",
                "context_summary": None,
                "permission_policy": {
                    "allow_shell": True,
                    "allow_network": False,
                    "allow_write": False,
                    "allowed_paths": [],
                    "max_runtime_seconds": 30,
                },
            },
        )

        # Route must accept the request (not 404).
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )
        body = response.json()
        assert body.get("ok") is True
        assert body.get("status") == "accepted"
        assert "run_id" in body


def test_coding_loop_execute_rejects_unauthenticated(
    monkeypatch,
) -> None:
    """Prove Coding Loop execute route enforces authentication.
    Requests without a valid API key must be rejected."""
    with _build_supported_profile_client(monkeypatch) as client:
        # Send a deliberately wrong API key; the route must reject it.
        response = client.post(
            "/api/agents/coding/execute",
            headers={"X-API-Key": "wrong-key"},
            json={
                "coding_task_id": "noauth-task",
                "thread_id": "1",
                "source_message_id": "1",
                "attempt_id": "attempt-1",
                "user_id": "local",
                "project_id": None,
                "adapter_kind": "pi_codex_runner",
                "instructions": "echo noauth",
                "repo_root": "/tmp",
                "context_summary": None,
                "permission_policy": {
                    "allow_shell": True,
                    "allow_network": False,
                    "allow_write": False,
                    "allowed_paths": [],
                    "max_runtime_seconds": 30,
                },
            },
        )
        assert response.status_code in {401, 403}


def test_coding_loop_route_visible_in_openapi(
    monkeypatch,
) -> None:
    """Prove Coding Loop execute route is visible in OpenAPI."""
    with _build_supported_profile_client(monkeypatch) as client:
        openapi = client.get("/openapi.json").json()
        paths = openapi.get("paths", {})
        assert "/api/agents/coding/execute" in paths
        assert "/api/agents/runs/{run_id}/coding" in paths
        assert "/api/chat/{thread_id}/coding-runs" in paths


def test_unrelated_quarantined_routes_remain_unavailable(
    monkeypatch,
) -> None:
    """Prove quarantined routes (tools, connectors, etc.) still return 404
    even after Coding Loop routes are enabled."""
    with _build_supported_profile_client(monkeypatch) as client:
        headers = {"X-API-Key": "test-api-key"}

        assert client.get("/api/tools/manifest", headers=headers).status_code == 404
        assert client.get("/api/connectors", headers=headers).status_code == 404
        assert client.get("/api/federation/ping", headers=headers).status_code == 404


def test_agent_orchestration_chat_readback_enforced(
    monkeypatch,
) -> None:
    """Prove thread-level coding-run projection route is mounted
    and enforces authentication for invalid keys."""
    with _build_supported_profile_client(monkeypatch) as client:
        headers = {"X-API-Key": "test-api-key"}
        authenticated = client.get("/api/chat/1/coding-runs", headers=headers)
        # Expect 200 (empty list) not 404.
        assert authenticated.status_code == 200

        # Wrong key must be rejected.
        wrong_key_response = client.get(
            "/api/chat/1/coding-runs",
            headers={"X-API-Key": "wrong-key"},
        )
        assert wrong_key_response.status_code in {401, 403}


def test_missing_route_does_not_regress_to_unclassified_404(
    monkeypatch,
) -> None:
    """Prove that a nonexistent endpoint still returns 404, but the
    Coding Loop execute route returns 200 acceptance."""
    with _build_supported_profile_client(monkeypatch) as client:
        headers = {"X-API-Key": "test-api-key"}

        # A genuinely unknown path must still 404.
        assert client.get("/api/nonexistent/endpoint", headers=headers).status_code == 404

        # The Coding Loop execute route must 200.
        response = client.post(
            "/api/agents/coding/execute",
            headers=headers,
            json={
                "coding_task_id": "regression-check",
                "thread_id": "1",
                "source_message_id": "1",
                "attempt_id": "attempt-1",
                "user_id": "local",
                "project_id": None,
                "adapter_kind": "pi_codex_runner",
                "instructions": "echo regression check",
                "repo_root": "/tmp",
                "context_summary": None,
                "permission_policy": {
                    "allow_shell": True,
                    "allow_network": False,
                    "allow_write": False,
                    "allowed_paths": [],
                    "max_runtime_seconds": 30,
                },
            },
        )
        assert response.status_code == 200
