import importlib
import json
from contextlib import closing, contextmanager
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from guardian.agents.events import AgentEventPublisher
from guardian.agents.store import AgentStore
from guardian.connections.catalog import get_catalog
from guardian.core import dependencies
from guardian.routes import agent_orchestration


@contextmanager
def _build_supported_profile_client(monkeypatch):
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-api-key")
    monkeypatch.setenv("ENABLE_CONNECTOR_WORKER", "0")
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "local_safe")
    monkeypatch.setenv("CODEXIFY_SUPPORTED_PROFILE", "v1-local-core-web-mcp")
    monkeypatch.setenv("CODEXIFY_BETA_CORE_ONLY", "0")
    for flag in (
        "CODEXIFY_ENABLE_ADMIN_ROUTES",
        "CODEXIFY_ENABLE_AGENT_ORCHESTRATION_ROUTES",
        "CODEXIFY_ENABLE_CODING_WORK_ORDERS_ROUTES",
        "CODEXIFY_ENABLE_OBSIDIAN_ROUTES",
    ):
        monkeypatch.setenv(flag, "1")

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


CODING_EXECUTE_ROUTE = "/api/agents/coding/execute"

# The authenticated single-user identity the supported local profile resolves
# for this deployment. The request body must match it; the body never grants
# account authority by itself.
CODING_TEST_ACCOUNT = "local"
CODING_TEST_THREAD_ID = "4242"
CODING_TEST_SOURCE_MESSAGE_ID = "9091"
CODING_TEST_PROJECT_ID = "4242"
CODING_TEST_PROVIDER_ID = "test-provider"
CODING_TEST_MODEL_ID = "test-model-a"
CODING_TEST_CREDENTIAL_REF = "credential-account-local"

# Stands in for secret-bearing credential custody data. The accepted
# execution binding must project safe authority metadata only.
CODING_CREDENTIAL_SECRET_SENTINEL = "SECRET-SENTINEL-must-not-cross-the-task-boundary"


def _coding_execute_body(**overrides: Any) -> dict[str, Any]:
    """Canonical, schema-valid Coding Loop request body.

    Every identifier is a synthetic test label, not a credential and not a
    durable identity. This body only proves the route's request contract;
    authority is established separately.
    """
    body: dict[str, Any] = {
        "coding_task_id": "proof-task-001",
        "thread_id": CODING_TEST_THREAD_ID,
        "source_message_id": CODING_TEST_SOURCE_MESSAGE_ID,
        "attempt_id": "attempt-1",
        "user_id": CODING_TEST_ACCOUNT,
        "project_id": CODING_TEST_PROJECT_ID,
        "adapter_kind": "pi_codex_runner",
        "instructions": "echo proof",
        "repo_root": "/tmp",
        "context_summary": None,
        "permission_policy": {
            "allow_shell": False,
            "allow_network": False,
            "allow_write": False,
            "allowed_paths": [],
            "max_runtime_seconds": 30,
        },
        "provider_id": CODING_TEST_PROVIDER_ID,
        "model_id": CODING_TEST_MODEL_ID,
        "credential_ref": CODING_TEST_CREDENTIAL_REF,
    }
    body.update(overrides)
    return body


class _RecordingAgentStore:
    """In-memory AgentStore that also records accepted writes."""

    def __init__(self) -> None:
        self.inner = AgentStore()
        self.deployments: list[dict[str, Any]] = []
        self.runs: list[dict[str, Any]] = []

    @property
    def db(self) -> Any:
        return self.inner.db

    def configure_db(self, db: Any | None) -> None:
        self.inner.configure_db(db)

    def create_deployment(self, **kwargs: Any) -> dict[str, Any]:
        self.deployments.append(dict(kwargs))
        return self.inner.create_deployment(**kwargs)

    def create_run(self, **kwargs: Any) -> dict[str, Any]:
        self.runs.append(dict(kwargs))
        return self.inner.create_run(**kwargs)


class _ReadbackStoreSpy:
    """Records the account scope each Agent/Coding readback reader receives.

    This is a route-to-store argument recorder, not durable ownership proof.
    The account readers keep their own durable account-origin provenance and
    canonical thread ownership requirements; the spy only shows which
    account scope the route asked for.
    """

    def __init__(
        self,
        *,
        coding_runs: list[dict[str, Any]] | None = None,
        account_runs: list[dict[str, Any]] | None = None,
        coding_snapshot: dict[str, Any] | None = None,
        account_run: dict[str, Any] | None = None,
        run: dict[str, Any] | None = None,
    ) -> None:
        self.coding_runs = coding_runs
        self.account_runs = account_runs
        self.coding_snapshot = coding_snapshot
        self.account_run = account_run
        self.run = run
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def get_coding_run_snapshot(
        self, run_id: str, *, user_id: str | None = None
    ) -> dict[str, Any] | None:
        self.calls.append(
            ("get_coding_run_snapshot", {"run_id": run_id, "user_id": user_id})
        )
        return self.coding_snapshot

    def list_coding_runs_for_thread(
        self, thread_id: int, *, user_id: str | None = None
    ) -> list[dict[str, Any]] | None:
        self.calls.append(
            ("list_coding_runs_for_thread", {"thread_id": thread_id, "user_id": user_id})
        )
        return self.coding_runs

    def get_account_run(self, run_id: str, *, user_id: str) -> dict[str, Any] | None:
        self.calls.append(("get_account_run", {"run_id": run_id, "user_id": user_id}))
        return self.account_run

    def list_account_runs_for_thread(
        self, thread_id: int, *, user_id: str
    ) -> list[dict[str, Any]] | None:
        self.calls.append(
            ("list_account_runs_for_thread", {"thread_id": thread_id, "user_id": user_id})
        )
        return self.account_runs

    def get_run(self, run_id: str, *, user_id: str | None = None) -> dict[str, Any] | None:
        self.calls.append(("get_run", {"run_id": run_id, "user_id": user_id}))
        return self.run

    def list_runs_for_thread(self, thread_id: int) -> list[dict[str, Any]]:
        raise AssertionError(
            "Account readback must not fall back to the unscoped thread list"
        )


class _CodingExecutionIsolation:
    """Scoped synthetic downstream authority for one Coding Loop request.

    These are controlled doubles. They do not establish that the production
    PostgreSQL lineage lookup or the production credential-authorization
    implementation accept this request. The independent authorization tests
    retain responsibility for those claims.
    """

    def __init__(self) -> None:
        self.store = _RecordingAgentStore()
        self.queued: list[dict[str, Any]] = []
        self.events: list[tuple[str, str, dict[str, Any]]] = []
        self.lineage_calls: list[dict[str, Any]] = []
        self.credential_calls: list[dict[str, Any]] = []


@contextmanager
def _isolate_coding_execution(monkeypatch):
    """Replace Coding Loop downstream effects for one test only.

    AgentStore persistence, the agent event publisher, and the coding
    execution enqueue are all replaced or redirected, so no deployment, run,
    event stream, or queue item reaches real storage, Redis, or a worker.
    """
    isolation = _CodingExecutionIsolation()

    def fake_lineage(
        *,
        account_id: str,
        thread_id: str,
        source_message_id: str,
        requested_project_id: str | None,
    ) -> str | None:
        isolation.lineage_calls.append(
            {
                "account_id": account_id,
                "thread_id": thread_id,
                "source_message_id": source_message_id,
                "requested_project_id": requested_project_id,
            }
        )
        return (
            str(requested_project_id) if requested_project_id is not None else None
        )

    def fake_authorize_credential_selection(
        _db: Any,
        *,
        credential_ref: str,
        account_id: str,
        provider_id: str,
        model_id: str,
    ) -> dict[str, Any]:
        isolation.credential_calls.append(
            {
                "credential_ref": credential_ref,
                "account_id": account_id,
                "provider_id": provider_id,
                "model_id": model_id,
            }
        )
        return {
            "credential_ref": credential_ref,
            "owner_scope": "account",
            "owner_id": account_id,
            "provider_id": provider_id,
            "credential_type": "api_key",
            "funding_route": "user_byok",
            "source_class": "account_api_key",
            "usage_policy_ref": None,
            # Secret-bearing custody data stands in for the real credential.
            # The binding builder must project only safe authority metadata.
            "api_key": CODING_CREDENTIAL_SECRET_SENTINEL,
        }

    def fake_publish(
        task_id: str,
        event_type: str,
        data: dict[str, Any] | None = None,
    ) -> str:
        isolation.events.append((task_id, event_type, dict(data or {})))
        return "1-0"

    def fake_enqueue_coding_execution(payload: dict[str, Any]) -> str:
        isolation.queued.append(dict(payload))
        return "task-coding-test"

    with monkeypatch.context() as patch:
        patch.setattr(
            agent_orchestration, "_validate_coding_lineage", fake_lineage
        )
        patch.setattr(
            agent_orchestration,
            "authorize_credential_selection",
            fake_authorize_credential_selection,
        )
        patch.setattr(agent_orchestration, "_store", isolation.store)
        patch.setattr(
            agent_orchestration, "_event_publisher", AgentEventPublisher()
        )
        patch.setattr("guardian.agents.events.task_events.publish", fake_publish)
        patch.setattr(
            "guardian.queue.redis_queue.enqueue_coding_execution",
            fake_enqueue_coding_execution,
        )
        yield isolation
    # The scoped patch context has restored every replaced module attribute.


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

        with _isolate_coding_execution(monkeypatch) as isolation:
            response = client.post(
                CODING_EXECUTE_ROUTE,
                headers=headers,
                json=_coding_execute_body(),
            )

        # Route must accept the request (not 404).
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )
        body = response.json()
        assert body.get("ok") is True
        assert body.get("status") == "accepted"
        assert body.get("run_id")
        assert body.get("deployment_id")

        # Exactly one execution task was captured, and nothing reached Redis.
        assert len(isolation.queued) == 1
        payload = isolation.queued[0]
        assert len(isolation.store.deployments) == 1
        assert len(isolation.store.runs) == 1

        binding = payload["execution_binding"]
        assert binding["provider_id"] == CODING_TEST_PROVIDER_ID
        assert binding["model_id"] == CODING_TEST_MODEL_ID
        assert binding["credential_ref"] == CODING_TEST_CREDENTIAL_REF
        assert binding["harness_id"] == "pi"
        assert binding["credential_owner_id"] == CODING_TEST_ACCOUNT

        # The authenticated account identity and the accepted source
        # thread/message lineage are retained.
        assert payload["user_id"] == CODING_TEST_ACCOUNT
        assert payload["thread_id"] == int(CODING_TEST_THREAD_ID)
        assert payload["source_thread_id"] == int(CODING_TEST_THREAD_ID)
        assert payload["source_message_id"] == int(CODING_TEST_SOURCE_MESSAGE_ID)
        assert payload["project_id"] == CODING_TEST_PROJECT_ID
        assert payload["permission_policy"]["allow_shell"] is False
        assert payload["permission_policy"]["allow_write"] is False

        # The accepted binding carries safe authority metadata only. The
        # credential type is a label; no secret-bearing field may cross the
        # task boundary.
        serialized = json.dumps(payload)
        assert CODING_CREDENTIAL_SECRET_SENTINEL not in serialized
        assert not (
            {"api_key", "api_secret", "secret", "credential_secret", "token"}
            & set(binding)
        )

        # The synthetic authority callbacks received the submitted identity
        # and selection arguments.
        assert isolation.lineage_calls == [
            {
                "account_id": CODING_TEST_ACCOUNT,
                "thread_id": CODING_TEST_THREAD_ID,
                "source_message_id": CODING_TEST_SOURCE_MESSAGE_ID,
                "requested_project_id": CODING_TEST_PROJECT_ID,
            }
        ]
        assert isolation.credential_calls == [
            {
                "credential_ref": CODING_TEST_CREDENTIAL_REF,
                "account_id": CODING_TEST_ACCOUNT,
                "provider_id": CODING_TEST_PROVIDER_ID,
                "model_id": CODING_TEST_MODEL_ID,
            }
        ]

        # The route emitted the created event on the replaced publisher.
        created = [
            data
            for _task_id, event_type, data in isolation.events
            if event_type == "created"
        ]
        assert len(created) == 1
        assert created[0]["execution_binding_id"] == binding["binding_id"]


def test_coding_loop_execute_rejects_unauthenticated(
    monkeypatch,
) -> None:
    """Prove Coding Loop execute route enforces authentication.
    Requests without a valid API key must be rejected."""
    with _build_supported_profile_client(monkeypatch) as client:
        with _isolate_coding_execution(monkeypatch) as isolation:
            # Send a deliberately wrong API key; the route must reject it.
            # The body is schema-valid, so a rejection cannot be explained by
            # request validation standing in for an authentication proof.
            response = client.post(
                CODING_EXECUTE_ROUTE,
                headers={"X-API-Key": "wrong-key"},
                json=_coding_execute_body(coding_task_id="noauth-task"),
            )

            assert response.status_code in {401, 403}
            # No authority was granted and nothing was accepted.
            assert isolation.lineage_calls == []
            assert isolation.credential_calls == []
            assert isolation.queued == []
            assert isolation.store.deployments == []
            assert isolation.store.runs == []


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


def test_supported_profile_exposes_read_only_connections_without_legacy_connectors(
    monkeypatch,
) -> None:
    with _build_supported_profile_client(monkeypatch) as client:
        headers = {"X-API-Key": "test-api-key"}

        listing = client.get("/api/connections", headers=headers)
        assert listing.status_code == 200
        payload = listing.json()
        assert payload["categories"] == ["inference", "knowledge", "messaging", "web"]
        assert len(payload["items"]) == len(get_catalog())
        assert len(payload["items"]) > 0

        detail = client.get("/api/connections/deepseek", headers=headers)
        assert detail.status_code == 200
        assert detail.json()["id"] == "deepseek"
        assert (
            client.get(
                "/api/connections/does_not_exist", headers=headers
            ).status_code
            == 404
        )

        assert client.get("/api/connectors", headers=headers).status_code == 404

        paths = client.get("/openapi.json").json().get("paths", {})
        assert "/api/connections" in paths
        assert "/api/connections/{connection_id}" in paths
        assert "/api/connectors" not in paths
        assert set(paths["/api/connections"]) == {"get"}
        assert set(paths["/api/connections/{connection_id}"]) == {"get"}
        assert "/api/knowledge/notion/search" in paths
        assert "/api/knowledge/notion/read/{object_id}" in paths
        assert set(paths["/api/knowledge/notion/search"]) == {"get"}
        assert "/api/knowledge/google-drive/search" in paths
        assert "/api/knowledge/google-drive/read/{object_id}" in paths
        assert set(paths["/api/knowledge/google-drive/search"]) == {"get"}
        command_manifest = client.get(
            "/api/guardian/commands/manifest", headers=headers
        ).json()
        command_paths = {
            (command["method"], command["path_template"])
            for command in command_manifest["commands"]
        }
        assert ("GET", "/api/knowledge/notion/search") in command_paths
        assert ("GET", "/api/knowledge/notion/read/{object_id}") in command_paths
        assert ("GET", "/api/knowledge/google-drive/search") in command_paths
        assert ("GET", "/api/knowledge/google-drive/read/{object_id}") in command_paths


def test_supported_profile_mounts_minimax_oauth_routes_as_internal_only(
    monkeypatch,
) -> None:
    """MiniMax OAuth provider-specific auth routes must be mounted under
    the supported local profile but hidden from public OpenAPI according
    to current internal-only behavior. Connector-quarantine assertions
    are not weakened.
    """

    with _build_supported_profile_client(monkeypatch) as client:
        headers = {"X-API-Key": "test-api-key"}

        # Connector quarantine is unchanged.
        assert client.get("/api/connectors", headers=headers).status_code == 404

        paths = client.get("/openapi.json").json().get("paths", {})
        # MiniMax OAuth routes are intentionally hidden from public
        # OpenAPI per the internal-only posture. Their handlers do
        # exist; the supported profile simply suppresses schema
        # visibility.
        assert "/api/connect/minimax/start" not in paths
        assert "/api/connect/minimax/poll" not in paths
        assert "/api/connect/minimax/disconnect" not in paths
        assert "/api/connect/minimax/status" not in paths
        # Other OAuth/connector surfaces remain absent.
        assert "/api/connect/google/start" not in paths
        # Credential mutation routes remain mounted but schema-hidden as an
        # internal provider-specific setup surface.
        assert "/api/connect/notion/configure" not in paths
        assert "/api/connect/notion/validate" not in paths
        assert "/api/connect/notion/disconnect" not in paths
        assert "/api/connect/google-drive/start" not in paths
        assert "/api/connect/google-drive/validate" not in paths
        assert "/api/connect/google-drive/disconnect" not in paths
        # The internal route is mounted even though it is hidden from public
        # OpenAPI; a storage-unavailable response still proves it did not
        # regress to a quarantined 404.
        assert (
            client.get("/api/connect/notion/status", headers=headers).status_code
            != 404
        )
        assert (
            client.get("/api/connect/google-drive/status", headers=headers).status_code
            != 404
        )


def test_agent_orchestration_chat_readback_enforced(
    monkeypatch,
) -> None:
    """Prove coding readback is mounted and requires durable thread authority."""
    with _build_supported_profile_client(monkeypatch) as client:
        openapi = client.get("/openapi.json")
        assert openapi.status_code == 200
        assert "/api/chat/{thread_id}/coding-runs" in openapi.json().get("paths", {})

        headers = {"X-API-Key": "test-api-key"}
        authenticated = client.get("/api/chat/1/coding-runs", headers=headers)
        # This fixture establishes no durable account-owned thread.
        assert authenticated.status_code == 404

        # Wrong key must be rejected.
        wrong_key_response = client.get(
            "/api/chat/1/coding-runs",
            headers={"X-API-Key": "wrong-key"},
        )
        assert wrong_key_response.status_code in {401, 403}


def test_authenticated_read_user_rejects_unresolved_identities() -> None:
    """Prove the readback identity helper fails closed.

    A missing, blank, or unresolved dependency identity must never be
    treated as an account scope.
    """
    for unresolved in (None, "", "   ", "Depends(get_current_user)"):
        with pytest.raises(HTTPException) as excinfo:
            agent_orchestration._authenticated_read_user(unresolved)
        assert excinfo.value.status_code == 401
        assert excinfo.value.detail == "account_identity_missing"

    assert (
        agent_orchestration._authenticated_read_user("account-a") == "account-a"
    )


def test_agent_readback_uses_authenticated_account_scope(monkeypatch) -> None:
    """Prove Agent/Coding readback asks the store for the authenticated
    account rather than rejecting the request on an identity mismatch."""
    with _build_supported_profile_client(monkeypatch) as client:
        headers = {"X-API-Key": "test-api-key"}
        spy = _ReadbackStoreSpy(coding_runs=[], account_runs=[])
        monkeypatch.setattr(agent_orchestration, "_store", spy)

        coding_runs = client.get("/api/chat/7/coding-runs", headers=headers)
        assert coding_runs.status_code == 200, coding_runs.text
        agent_runs = client.get("/api/chat/7/agent-runs", headers=headers)
        assert agent_runs.status_code == 200, agent_runs.text

        # Both thread lists were read with the authenticated account scope.
        assert spy.calls == [
            (
                "list_coding_runs_for_thread",
                {"thread_id": 7, "user_id": "local"},
            ),
            (
                "list_account_runs_for_thread",
                {"thread_id": 7, "user_id": "local"},
            ),
        ]


def test_agent_readback_fails_closed_without_authenticated_identity(
    monkeypatch,
) -> None:
    """Prove readback refuses to look up a resource without an account.

    The request still authenticates with the API key; only the account
    identity fails to resolve.
    """
    monkeypatch.setattr(dependencies, "get_single_user_id", lambda: "")
    with _build_supported_profile_client(monkeypatch) as client:
        headers = {"X-API-Key": "test-api-key"}
        spy = _ReadbackStoreSpy(coding_runs=[], account_runs=[])
        monkeypatch.setattr(agent_orchestration, "_store", spy)

        response = client.get("/api/chat/7/coding-runs", headers=headers)

        assert response.status_code == 401
        # No durable resource lookup was attempted.
        assert spy.calls == []


def test_agent_readback_hides_unknown_resource_without_unscoped_fallback(
    monkeypatch,
) -> None:
    """Prove an unknown resource stays existence-hidden and never falls
    back to an unscoped store read."""
    with _build_supported_profile_client(monkeypatch) as client:
        headers = {"X-API-Key": "test-api-key"}
        spy = _ReadbackStoreSpy(coding_runs=None, account_runs=None)
        monkeypatch.setattr(agent_orchestration, "_store", spy)

        thread_response = client.get("/api/chat/7/coding-runs", headers=headers)
        assert thread_response.status_code == 404
        run_response = client.get("/api/agents/runs/missing-run/coding", headers=headers)
        assert run_response.status_code == 404

        # Only the account-scoped readers were used.
        assert spy.calls == [
            (
                "list_coding_runs_for_thread",
                {"thread_id": 7, "user_id": "local"},
            ),
            (
                "get_coding_run_snapshot",
                {"run_id": "missing-run", "user_id": "local"},
            ),
        ]


def test_agent_readback_rejects_foreign_account_selection(monkeypatch) -> None:
    """Prove a forged X-User-Id header cannot select another account."""
    with _build_supported_profile_client(monkeypatch) as client:
        spy = _ReadbackStoreSpy(coding_runs=None, account_runs=None)
        monkeypatch.setattr(agent_orchestration, "_store", spy)

        response = client.get(
            "/api/chat/7/coding-runs",
            headers={"X-API-Key": "test-api-key", "X-User-Id": "other-account"},
        )

        assert response.status_code == 404
        # The forged header did not replace the authenticated account scope.
        assert spy.calls == [
            (
                "list_coding_runs_for_thread",
                {"thread_id": 7, "user_id": "local"},
            ),
        ]


def test_agent_readback_preserves_local_operator_threadless_run(
    monkeypatch,
) -> None:
    """Prove the local operator lane keeps its bounded threadless read.

    A threadless operator-created run remains readable under the local
    operator API key. This is the explicit local compatibility path, not
    remote account authority.
    """
    with _build_supported_profile_client(monkeypatch) as client:
        local_store = AgentStore()
        deployment = local_store.create_deployment(
            flow_id="operator-threadless",
            thread_id=None,
            spec_json={},
            spec_hash="operator-threadless-spec",
        )
        run = local_store.create_run(
            deployment_id=str(deployment["deployment_id"]),
            thread_id=None,
            status="running",
        )
        monkeypatch.setattr(agent_orchestration, "_store", local_store)

        response = client.get(
            f"/api/agents/runs/{run['run_id']}",
            headers={"X-API-Key": "test-api-key"},
        )

        assert response.status_code == 200, response.text
        assert response.json()["run"]["thread_id"] is None


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
        with _isolate_coding_execution(monkeypatch) as isolation:
            response = client.post(
                CODING_EXECUTE_ROUTE,
                headers=headers,
                json=_coding_execute_body(coding_task_id="regression-check"),
            )
            assert response.status_code == 200, response.text
            assert response.json().get("status") == "accepted"
            assert len(isolation.queued) == 1


@pytest.mark.parametrize(
    "missing_field",
    ["provider_id", "model_id", "credential_ref"],
)
def test_coding_loop_execute_requires_binding_identity_fields(
    monkeypatch,
    missing_field,
) -> None:
    """Prove the execution-binding identity fields stay required.

    A future implementation that silently makes any of them optional would
    let a request reach authority resolution without a selected provider,
    model, or credential reference.
    """
    with _build_supported_profile_client(monkeypatch) as client:
        headers = {"X-API-Key": "test-api-key"}
        body = _coding_execute_body()
        body.pop(missing_field)

        with _isolate_coding_execution(monkeypatch) as isolation:
            response = client.post(
                CODING_EXECUTE_ROUTE,
                headers=headers,
                json=body,
            )

            assert response.status_code == 422, response.text
            detail = response.json()["detail"]
            assert any(
                error.get("type") == "missing"
                and list(error.get("loc") or []) == ["body", missing_field]
                for error in detail
            ), detail
            # Nothing was authorized, created, or enqueued.
            assert isolation.lineage_calls == []
            assert isolation.credential_calls == []
            assert isolation.queued == []
            assert isolation.store.deployments == []
            assert isolation.store.runs == []


def test_coding_loop_execute_rejects_account_identity_mismatch(
    monkeypatch,
) -> None:
    """Prove the request body cannot supply account authority.

    The authenticated account identity is Guardian-controlled; a body that
    names a different account must be refused before any authority check.
    """
    with _build_supported_profile_client(monkeypatch) as client:
        headers = {"X-API-Key": "test-api-key"}

        with _isolate_coding_execution(monkeypatch) as isolation:
            response = client.post(
                CODING_EXECUTE_ROUTE,
                headers=headers,
                json=_coding_execute_body(user_id="other-account"),
            )

            assert response.status_code == 403, response.text
            # No execution binding was authorized and nothing was created.
            assert isolation.lineage_calls == []
            assert isolation.credential_calls == []
            assert isolation.queued == []
            assert isolation.store.deployments == []
            assert isolation.store.runs == []


def test_coding_loop_execution_isolation_restores_module_state(
    monkeypatch,
) -> None:
    """Prove the Coding Loop isolation is scoped to its own test."""
    originals = {
        "lineage": agent_orchestration._validate_coding_lineage,
        "authorize": agent_orchestration.authorize_credential_selection,
        "store": agent_orchestration._store,
        "publisher": agent_orchestration._event_publisher,
    }

    with _isolate_coding_execution(monkeypatch):
        assert agent_orchestration._validate_coding_lineage is not originals["lineage"]
        assert (
            agent_orchestration.authorize_credential_selection
            is not originals["authorize"]
        )
        assert agent_orchestration._store is not originals["store"]
        assert agent_orchestration._event_publisher is not originals["publisher"]

    assert agent_orchestration._validate_coding_lineage is originals["lineage"]
    assert (
        agent_orchestration.authorize_credential_selection is originals["authorize"]
    )
    assert agent_orchestration._store is originals["store"]
    assert agent_orchestration._event_publisher is originals["publisher"]


@pytest.mark.parametrize("route_enabled", [True, False], ids=["admitted", "flag-disabled"])
def test_whooshd_profile_mounts_authenticated_persona_profiles(
    monkeypatch, route_enabled,
) -> None:
    from tests.auth.test_private_preview_access import _preview_env, _session_headers
    from tests.utils import get_test_auth_headers
    from guardian.core import event_bus
    import guardian.guardian_api as guardian_api
    import guardian.routes.persona_profiles as persona_routes

    try:
        with monkeypatch.context() as env:
            _preview_env(env)
            env.setenv("GUARDIAN_AUTH_MODE", "remote")
            env.setenv("ENABLE_CONNECTOR_WORKER", "0")
            env.setenv("CODEXIFY_SUPPORTED_PROFILE", "v1-whooshd-deepseek-web")
            if route_enabled:
                # Test ordinary default admission, without forcing the flag on.
                env.delenv("CODEXIFY_ENABLE_PERSONA_PROFILE_ROUTES", raising=False)
            else:
                env.setenv("CODEXIFY_ENABLE_PERSONA_PROFILE_ROUTES", "false")
            guardian_api = importlib.reload(guardian_api)
            # Only persistence IO is stubbed. Authentication, allowlist, scope
            # resolution, router registration, and route handler remain real.
            listing = MagicMock(return_value=[])
            env.setattr(persona_routes, "list_persona_profiles", listing)
            # Match the existing mounted-route fixture: no service lifespan.
            with closing(TestClient(guardian_api.app)) as client:
                paths = client.get("/openapi.json").json()["paths"]
                mounted = guardian_api.app.state.supported_profile_enabled_labels
                headers = _session_headers("admin@example.com")
                if not route_enabled:
                    assert "/api/persona-profiles" not in paths
                    assert "/api/persona-profiles/{profile_id}" not in paths
                    assert "persona_profiles" not in mounted
                    assert client.get("/api/persona-profiles", headers=headers).status_code == 404
                    listing.assert_not_called()
                    return

                assert "/api/persona-profiles" in paths
                assert set(paths["/api/persona-profiles"]) == {"get", "post"}
                assert set(paths["/api/persona-profiles/{profile_id}"]) == {"get", "patch"}
                assert "persona_profiles" in mounted
                assert client.get("/api/persona-profiles").status_code == 401
                assert client.get(
                    "/api/persona-profiles", headers=get_test_auth_headers()
                ).status_code == 401
                assert client.get(
                    "/api/persona-profiles",
                    headers=_session_headers("unapproved@example.com"),
                ).status_code == 401
                listing.assert_not_called()
                for email in ("admin@example.com", "guest@example.com"):
                    response = client.get(
                        "/api/persona-profiles",
                        headers={**_session_headers(email), "X-User-Id": "foreign@example.com"},
                    )
                    assert response.status_code == 200
                    assert response.json() == {"ok": True, "profiles": []}
                    listing.assert_called_with(account_id=email)
                assert listing.call_count == 2
                for path in ("/api/imprint/status", "/api/system_prompt/summary", "/api/connectors"):
                    assert path not in paths
                    assert client.get(path, headers=headers).status_code == 404
    finally:
        event_bus.reset()
        # Restore module route registration after restoring the patched env.
        importlib.reload(guardian_api)
