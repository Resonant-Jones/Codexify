"""Actual app mount proof without running database-producing lifespan startup."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _isolated_hosted_app(monkeypatch):
    import importlib

    from guardian import guardian_api
    from guardian.core import event_bus

    try:
        with monkeypatch.context() as env:
            env.setenv("GUARDIAN_API_KEY", "synthetic-app-mount-fixture")
            env.setenv("GUARDIAN_EXPOSURE_MODE", "private_preview")
            env.setenv("ENABLE_CONNECTOR_WORKER", "0")
            env.setenv("CODEXIFY_BETA_CORE_ONLY", "0")
            env.setenv("CODEXIFY_ENABLE_AUTH_ROUTES", "true")
            env.delenv("CODEXIFY_SUPPORTED_PROFILE", raising=False)
            # Earlier tests can leave app wiring under a quarantined profile.
            # Reload only; never run the database-producing lifespan.
            importlib.reload(guardian_api)
            yield
    finally:
        event_bus.reset()
        importlib.reload(guardian_api)


def _scout_client(*args, **kwargs):
    client = TestClient(*args, **kwargs)
    # The repository bootstrap injects an operator key by default. Scout tests
    # must exercise only the credential selectors explicitly supplied per call.
    client.headers.pop("X-API-Key", None)
    return client


def test_actual_app_mounts_handoff_and_rejects_unqualified_transport(monkeypatch):
    monkeypatch.setenv("GUARDIAN_API_KEY", "synthetic-app-mount-fixture")
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "private_preview")
    from guardian.guardian_api import app

    # No context manager: do not start application/database lifespan hooks.
    with_client = _scout_client(app, base_url="https://preview.codexify.space")
    handoff = with_client.post(
        "/api/auth/scout/handoff", json={"challenge": "c" * 43, "state": "s" * 43}
    )
    assert handoff.status_code == 401
    assert handoff.json()["detail"] == "Hosted admission required"
    response = with_client.post(
        "/api/auth/scout/exchange", json={"code": "c" * 43, "verifier": "v" * 43}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Hosted admission required"
    denied = with_client.get(
        "/api/chat/threads",
        headers={
            "Authorization": "Bearer oauth:synthetic",
            "X-Guardian-Account-Session": "synthetic",
        },
    )
    assert denied.status_code == 400
    assert denied.json()["detail"] == "Hosted account transport rejected"
    with_client.close()


@pytest.mark.parametrize("posture", ["enabled", "flag-disabled", "profile-quarantined"])
def test_scout_auth_family_obeys_mainline_auth_route_gate(monkeypatch, posture):
    import importlib

    from guardian import guardian_api
    from guardian.core import event_bus

    try:
        with monkeypatch.context() as env:
            env.setenv("GUARDIAN_API_KEY", "synthetic-app-mount-fixture")
            env.setenv("GUARDIAN_EXPOSURE_MODE", "private_preview")
            env.setenv("ENABLE_CONNECTOR_WORKER", "0")
            env.setenv("CODEXIFY_BETA_CORE_ONLY", "0")
            env.setenv(
                "CODEXIFY_ENABLE_AUTH_ROUTES",
                "false" if posture == "flag-disabled" else "true",
            )
            if posture == "profile-quarantined":
                env.setenv("CODEXIFY_SUPPORTED_PROFILE", "v1-local-core-web-mcp")
            else:
                env.delenv("CODEXIFY_SUPPORTED_PROFILE", raising=False)
            importlib.reload(guardian_api)
            client = _scout_client(
                guardian_api.app, base_url="https://preview.codexify.space"
            )
            try:
                responses = [
                    client.post(
                        "/api/auth/scout/handoff",
                        json={"challenge": "c" * 43, "state": "s" * 43},
                    ),
                    client.post(
                        "/api/auth/scout/exchange",
                        json={"code": "c" * 43, "verifier": "v" * 43},
                    ),
                    client.put(
                        "/api/auth/scout/qualification/12345678-1234-4234-8234-123456789abc"
                    ),
                    client.get(
                        "/api/auth/scout/qualification/12345678-1234-4234-8234-123456789abc"
                    ),
                    client.post(
                        "/api/auth/scout/qualification/12345678-1234-4234-8234-123456789abc/browser",
                        json={"event": "loaded"},
                    ),
                ]
                expected = 401 if posture == "enabled" else 404
                assert [response.status_code for response in responses] == [
                    expected
                ] * len(responses)
            finally:
                client.close()
    finally:
        event_bus.reset()
        importlib.reload(guardian_api)


def test_actual_account_route_never_uses_access_as_missing_account_identity(
    monkeypatch,
):
    monkeypatch.setenv("GUARDIAN_API_KEY", "synthetic-app-mount-fixture")
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "private_preview")
    from guardian.core import scout_account_transport as transport
    from guardian.guardian_api import app

    monkeypatch.setattr(transport, "verify_access_assertion", lambda _: None)
    client = _scout_client(app, base_url="https://preview.codexify.space")
    for account in [None, "fixture-invalid-account"]:
        headers = {"CF-Access-Jwt-Assertion": "fixture-access"}
        if account is not None:
            headers["X-Guardian-Account-Session"] = account
        response = client.get("/api/chat/threads", headers=headers)
        assert response.status_code == 401
        assert "threads" not in response.json()
    client.close()


@pytest.mark.parametrize(
    "case,expected",
    [("owner", 200), ("other_owner", 403), ("revoked", 401), ("no_access", 400)],
)
def test_hosted_transport_retains_mainline_durable_task_authorization(
    monkeypatch, case, expected
):
    from unittest.mock import Mock

    import fakeredis

    from guardian import guardian_api
    from guardian.core import auth, scout_account_transport, session_store
    from guardian.queue import task_events

    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "private_preview")
    monkeypatch.setenv("GUARDIAN_SESSION_SECRET", "synthetic-mounted-task-fixture")
    monkeypatch.setenv("CODEXIFY_PREVIEW_APPROVED_EMAILS", "fixture@example.com")
    monkeypatch.setattr(
        scout_account_transport, "verify_access_assertion", lambda _: None
    )
    store = session_store.SessionStore(fakeredis.FakeRedis())
    monkeypatch.setattr(session_store, "_SESSION_STORE", store)
    token, _ = auth.issue_session_token(
        subject="fixture@example.com", purpose=auth.ACCOUNT_SESSION_PURPOSE
    )
    store.store(token, "fixture@example.com", 300)
    if case == "revoked":
        store.revoke(token)

    db = Mock()
    db.get_chat_thread.return_value = {
        "id": 76,
        "user_id": (
            "other@example.com" if case == "other_owner" else "fixture@example.com"
        ),
    }
    lookup = Mock(
        return_value={"backend_task_id": "scout-fixture-task", "thread_id": 76}
    )
    events = Mock(
        return_value=[("1-0", {"type": "task.completed", "data": {"thread_id": 76}})]
    )
    monkeypatch.setattr(guardian_api, "chatlog_db", db)
    monkeypatch.setattr(
        "guardian.core.task_event_access.get_chat_completion_attempt_by_task_id", lookup
    )
    monkeypatch.setattr(task_events, "read_events", events)
    headers = {"X-Guardian-Account-Session": token}
    if case != "no_access":
        headers["CF-Access-Jwt-Assertion"] = "synthetic-assertion"
    client = _scout_client(guardian_api.app, base_url="https://preview.codexify.space")
    response = client.get("/api/tasks/scout-fixture-task/events", headers=headers)
    client.close()
    assert response.status_code == expected
    if case in {"owner", "other_owner"}:
        lookup.assert_called_once()
        db.get_chat_thread.assert_called_once_with(76)
    else:
        lookup.assert_not_called()
        db.get_chat_thread.assert_not_called()
    if expected == 200:
        events.assert_called_once()
        assert "event: task.completed" in response.text
        assert response.headers["X-Scout-Access-Admission"] == "edge-consumed"
    else:
        events.assert_not_called()
