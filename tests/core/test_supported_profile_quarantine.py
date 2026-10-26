import importlib
from contextlib import closing, contextmanager
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from guardian.connections.catalog import get_catalog


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


def _incomplete_coding_execute_body() -> dict:
    """Return a coding-execution body that omits execution-binding identity.

    `CodingAgentTaskEnvelope` requires an explicit provider, model, and
    credential reference. This body omits exactly those three fields, so it
    is structurally incomplete in the way the request contract requires.
    """
    return {
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
    }


def _complete_coding_execute_body() -> dict:
    """Return a coding-execution body carrying explicit execution identity.

    The credential reference is deliberately not resolvable. A request that
    names an explicit identity must still be denied unless Guardian
    authorizes it, so this body proves authorization rather than asserting it.
    """
    return {
        **_incomplete_coding_execute_body(),
        "provider_id": "deepseek",
        "model_id": "deepseek-chat",
        "credential_ref": "ccr_unresolvable_reference",
    }


def _required_body_fields(openapi: dict, operation: dict) -> set[str]:
    """Return the request-body fields the published contract declares required."""
    schema = (
        operation.get("requestBody", {})
        .get("content", {})
        .get("application/json", {})
        .get("schema", {})
    )
    reference = schema.get("$ref", "")
    if reference:
        schema = (
            openapi.get("components", {})
            .get("schemas", {})
            .get(reference.rsplit("/", 1)[-1], {})
        )
    return set(schema.get("required", []))


def _missing_validation_fields(response) -> set[str]:
    """Return the body fields a validation rejection reported as missing."""
    return {
        error["loc"][-1]
        for error in response.json()["detail"]
        if error.get("type") == "missing"
    }


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


def test_coding_loop_execute_route_registered_and_rejects_incomplete_binding(
    monkeypatch,
) -> None:
    """Prove POST /api/agents/coding/execute is registered in the supported
    local profile, and that request validation is what rejects a request
    which omits execution-binding identity.

    A mounted route is not permission to execute. `CodingAgentTaskEnvelope`
    requires an explicit provider, model, and credential reference, so an
    incomplete body is rejected with HTTP 422 by request validation, before
    account, lineage, or credential authority is consulted. The route must
    not be confused with an unmounted route, which answers 404.
    """
    with _build_supported_profile_client(monkeypatch) as client:
        headers = {"X-API-Key": "test-api-key"}

        openapi = client.get("/openapi.json").json()
        paths = openapi.get("paths", {})
        assert "/api/agents/coding/execute" in paths
        # POST is the supported method for execution intake.
        assert "post" in paths["/api/agents/coding/execute"]

        response = client.post(
            "/api/agents/coding/execute",
            headers=headers,
            json=_incomplete_coding_execute_body(),
        )

        # The route is mounted and reached request validation.
        assert (
            response.status_code == 422
        ), f"Expected 422, got {response.status_code}: {response.text}"
        # It is not an unmounted route.
        assert response.status_code != 404

        # The rejection must name the missing execution-binding identity.
        assert {"provider_id", "model_id", "credential_ref"} <= (
            _missing_validation_fields(response)
        )

        # No coding task was accepted.
        body = response.json()
        assert body.get("ok") is not True
        assert body.get("status") != "accepted"
        assert "run_id" not in body


def test_coding_loop_execute_rejects_unauthenticated(
    monkeypatch,
) -> None:
    """Prove Coding Loop execute route enforces authentication.

    A caller without a valid API key must be rejected, and must be rejected
    before request validation or execution authorization can say anything
    about its body. Request validation becoming stricter must not weaken
    the authentication boundary.
    """
    with _build_supported_profile_client(monkeypatch) as client:
        # A deliberately wrong API key with an incomplete body. The route must
        # reject the caller on authentication, not answer 422 about the body:
        # that would disclose the request contract to an unauthenticated
        # caller and would mean authentication no longer precedes validation.
        incomplete = client.post(
            "/api/agents/coding/execute",
            headers={"X-API-Key": "wrong-key"},
            json=_incomplete_coding_execute_body(),
        )
        assert (
            incomplete.status_code == 401
        ), f"Expected 401, got {incomplete.status_code}: {incomplete.text}"
        assert incomplete.status_code not in {200, 422}

        # The same wrong key with a complete body, naming an explicit
        # provider, model, and credential reference, must still be rejected.
        # Naming an execution identity must not bypass authentication, and an
        # unresolvable credential reference must not be treated as authority.
        complete = client.post(
            "/api/agents/coding/execute",
            headers={"X-API-Key": "wrong-key"},
            json=_complete_coding_execute_body(),
        )
        assert (
            complete.status_code == 401
        ), f"Expected 401, got {complete.status_code}: {complete.text}"
        assert complete.status_code not in {200, 422}


def test_coding_loop_route_visible_in_openapi(
    monkeypatch,
) -> None:
    """Prove Coding Loop execute route is visible in OpenAPI.

    The published contract must also declare the execution-binding identity
    it requires, so the documented request shape and the enforced request
    shape cannot drift apart.
    """
    with _build_supported_profile_client(monkeypatch) as client:
        openapi = client.get("/openapi.json").json()
        paths = openapi.get("paths", {})
        assert "/api/agents/coding/execute" in paths
        assert "/api/agents/runs/{run_id}/coding" in paths
        assert "/api/chat/{thread_id}/coding-runs" in paths

        execute = paths["/api/agents/coding/execute"]
        # POST is the supported method for execution intake.
        assert "post" in execute
        assert "get" not in execute

        required = _required_body_fields(openapi, execute["post"])
        assert {"provider_id", "model_id", "credential_ref"} <= required


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
    """Prove coding readback is mounted and requires account authority.

    The readback route is registered, but an operator API key is not an
    account principal. The route therefore denies the caller at the
    account-identity boundary, before any thread lookup, so it discloses no
    thread existence and returns no coding run.
    """
    with _build_supported_profile_client(monkeypatch) as client:
        openapi = client.get("/openapi.json")
        assert openapi.status_code == 200
        assert "/api/chat/{thread_id}/coding-runs" in openapi.json().get("paths", {})

        headers = {"X-API-Key": "test-api-key"}
        authenticated = client.get("/api/chat/1/coding-runs", headers=headers)
        # The route is mounted and reached, so this is not an unmounted-route
        # 404.
        assert authenticated.status_code != 404
        # The caller carries no account identity, so the account-authority
        # boundary denies the read before any thread lookup.
        assert (
            authenticated.status_code == 403
        ), f"Expected 403, got {authenticated.status_code}: {authenticated.text}"
        assert authenticated.json()["detail"] == "account_identity_mismatch"
        # No coding run is disclosed.
        assert "runs" not in authenticated.json()

        # Wrong key must be rejected before the account-identity comparison.
        wrong_key_response = client.get(
            "/api/chat/1/coding-runs",
            headers={"X-API-Key": "wrong-key"},
        )
        assert wrong_key_response.status_code == 401, (
            f"Expected 401, got {wrong_key_response.status_code}: "
            f"{wrong_key_response.text}"
        )


def test_missing_route_does_not_regress_to_unclassified_404(
    monkeypatch,
) -> None:
    """Prove that a nonexistent endpoint still returns 404, and that the
    Coding Loop execute route stays distinguishable from an unmounted route.

    The execute route is mounted, so a structurally incomplete body is
    rejected by request validation with 422 rather than falling through to
    the 404 of an unknown path.
    """
    with _build_supported_profile_client(monkeypatch) as client:
        headers = {"X-API-Key": "test-api-key"}

        # A genuinely unknown path must still 404.
        assert client.get("/api/nonexistent/endpoint", headers=headers).status_code == 404

        # The Coding Loop execute route is mounted, so it must not answer 404.
        response = client.post(
            "/api/agents/coding/execute",
            headers=headers,
            json=_incomplete_coding_execute_body(),
        )
        assert (
            response.status_code == 422
        ), f"Expected 422, got {response.status_code}: {response.text}"
        assert response.status_code != 404


def test_coding_execute_incomplete_request_reaches_no_dispatch_boundary(
    monkeypatch,
) -> None:
    """Prove an incomplete coding-execution request stops before every
    dispatch boundary.

    Guardian resolves execution-binding authority before it creates a
    deployment or a coding run, publishes an accepted execution event,
    acquires credential authority, or enqueues a worker task. A request
    rejected by request validation must reach none of them.
    """
    from guardian.agents.events import AgentEventPublisher
    from guardian.agents.store import AgentStore
    from guardian.queue import redis_queue
    from guardian.routes import agent_orchestration

    reached: list[str] = []
    published_events: list[dict] = []

    def _record(name):
        def _call(*args, **kwargs):
            reached.append(name)
            raise AssertionError(f"dispatch boundary reached: {name}")

        return _call

    def _record_event(*args, **kwargs):
        published_events.append(kwargs)

    monkeypatch.setattr(AgentStore, "create_deployment", _record("create_deployment"))
    monkeypatch.setattr(AgentStore, "create_run", _record("create_run"))
    monkeypatch.setattr(AgentEventPublisher, "emit", _record_event)
    monkeypatch.setattr(
        redis_queue,
        "enqueue_coding_execution",
        _record("enqueue_coding_execution"),
    )
    monkeypatch.setattr(
        agent_orchestration,
        "authorize_credential_selection",
        _record("authorize_credential_selection"),
    )

    with _build_supported_profile_client(monkeypatch) as client:
        response = client.post(
            "/api/agents/coding/execute",
            headers={"X-API-Key": "test-api-key"},
            json=_incomplete_coding_execute_body(),
        )

    assert response.status_code == 422
    # No deployment, no coding run, no worker task, and no credential
    # authority.
    assert reached == []
    # No accepted execution event was published for this request.
    assert not [
        event
        for event in published_events
        if (event.get("payload") or {}).get("coding_task_id")
    ]


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
