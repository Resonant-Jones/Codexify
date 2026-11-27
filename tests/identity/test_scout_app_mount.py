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
                    client.get("/api/auth/scout/profile"),
                    client.patch(
                        "/api/auth/scout/profile", json={"greeting_name": None}
                    ),
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


def test_preview_supported_profile_mounts_narrow_scout_profile(monkeypatch):
    import importlib
    from contextlib import nullcontext
    from types import SimpleNamespace
    from unittest.mock import Mock

    import fakeredis

    from guardian import guardian_api
    from guardian.core import auth, scout_account_transport, session_store
    from guardian.routes import scout_auth

    monkeypatch.setenv("CODEXIFY_SUPPORTED_PROFILE", "v1-whooshd-deepseek-web")
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", "remote")
    monkeypatch.setenv("CODEXIFY_MULTI_USER_ENABLED", "true")
    monkeypatch.setenv("GUARDIAN_SESSION_SECRET", "synthetic-mounted-profile-fixture")
    subject = "fixture@example.invalid"
    monkeypatch.setenv("CODEXIFY_PREVIEW_APPROVED_EMAILS", subject)
    monkeypatch.setattr(
        scout_account_transport, "verify_access_assertion", lambda _: None
    )
    monkeypatch.setattr(scout_auth, "verify_access_assertion", lambda _: None)
    store = session_store.SessionStore(fakeredis.FakeRedis())
    monkeypatch.setattr(session_store, "_SESSION_STORE", store)
    token, _ = auth.issue_session_token(
        subject=subject, purpose=auth.ACCOUNT_SESSION_PURPOSE
    )
    store.store(token, subject, 300)
    session = Mock()
    session.execute.return_value.scalar_one_or_none.return_value = "Explicit Greeting"
    session.get.return_value = None
    monkeypatch.setattr(
        scout_auth,
        "load_guardian_db_from_env",
        lambda: SimpleNamespace(get_session=lambda: nullcontext(session)),
    )
    importlib.reload(guardian_api)
    # Match the serving route posture, but never run database-producing lifespan.
    client = _scout_client(guardian_api.app, base_url="https://preview.codexify.space")
    headers = {
        "X-Guardian-Account-Session": token,
        "CF-Access-Jwt-Assertion": "synthetic-access",
    }
    try:
        routes = [
            r
            for r in guardian_api.app.routes
            if getattr(r, "path", None) == "/api/auth/scout/profile"
        ]
        assert len(routes) == 2
        assert {tuple(r.methods) for r in routes} == {("GET",), ("PATCH",)}
        for suffix, methods in (
            ("/presentation", {"GET", "PATCH"}),
            ("/presentation/wallpaper", {"GET", "PUT"}),
        ):
            mounted = [
                r
                for r in guardian_api.app.routes
                if getattr(r, "path", None) == "/api/auth/scout/profile" + suffix
            ]
            assert {method for r in mounted for method in r.methods} == methods
        assert not any(
            getattr(r, "path", None) == "/api/user/profile"
            for r in guardian_api.app.routes
        )
        response = client.get(
            "/api/auth/scout/profile?user_id=other@example.invalid", headers=headers
        )
        assert response.status_code == 200
        assert response.json() == {"greeting_name": "Explicit Greeting"}
        assert response.headers["Cache-Control"] == "no-store"
        assert response.headers["Referrer-Policy"] == "no-referrer"
        statement = session.execute.call_args.args[0]
        assert list(statement.compile().params.values()) == [subject]
        assert list(statement.selected_columns.keys()) == ["greeting_name"]
        from guardian.presentation_tokens import PRESENTATION_DEFAULTS

        presentation = client.get(
            "/api/auth/scout/profile/presentation?workspace_id=11111111-1111-4111-8111-111111111111",
            headers=headers,
        )
        assert presentation.status_code == 200
        assert presentation.json()["settings"] == PRESENTATION_DEFAULTS
        assert presentation.json()["wallpaper_url"] is None
        assert presentation.headers["Cache-Control"] == "no-store"
        assert (
            client.patch(
                "/api/auth/scout/profile",
                headers=headers,
                json={"display_name": "Injected"},
            ).status_code
            == 400
        )
        assert (
            client.get(
                "/api/user/profile", headers={"Authorization": "Bearer " + token}
            ).status_code
            == 404
        )
        assert (
            client.get(
                "/api/auth/scout/profile", headers={"X-Guardian-Account-Session": token}
            ).status_code
            == 400
        )
        store.revoke(token)
        assert client.get("/api/auth/scout/profile", headers=headers).status_code == 401
        assert session.execute.call_count == 1
        session.add.assert_not_called()
        session.flush.assert_not_called()
        session.commit.assert_not_called()
    finally:
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

    monkeypatch.setenv("GUARDIAN_SESSION_SECRET", "synthetic-mounted-task-fixture")
    monkeypatch.setenv("CODEXIFY_PREVIEW_APPROVED_EMAILS", "fixture@example.com")
    # The mounted route derives its bounded transport block from this variable.
    # Pin it so the expected bounded read is deterministic.
    monkeypatch.setenv("TASK_EVENT_BLOCK_MS", "250")
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
    terminal_event = ("1-0", {"type": "task.completed", "data": {"thread_id": 76}})
    # The mounted route consumes the bounded reader. Patching only the legacy
    # unbounded reader left the SSE generator polling a transport that never
    # produced a terminal event, so the response body never completed.
    bounded_reader = Mock(return_value=[terminal_event])
    legacy_reader = Mock(return_value=[terminal_event])
    monkeypatch.setattr(guardian_api, "chatlog_db", db)
    monkeypatch.setattr(
        "guardian.core.task_event_access.get_chat_completion_attempt_by_task_id", lookup
    )
    monkeypatch.setattr(task_events, "read_events_bounded", bounded_reader)
    monkeypatch.setattr(task_events, "read_events", legacy_reader)
    headers = {"X-Guardian-Account-Session": token}
    if case != "no_access":
        headers["CF-Access-Jwt-Assertion"] = "synthetic-assertion"
    client = _scout_client(guardian_api.app, base_url="https://preview.codexify.space")
    try:
        response = client.get("/api/tasks/scout-fixture-task/events", headers=headers)
    finally:
        client.close()
    assert response.status_code == expected
    if case in {"owner", "other_owner"}:
        lookup.assert_called_once_with(db, "scout-fixture-task")
        db.get_chat_thread.assert_called_once_with(76)
    else:
        lookup.assert_not_called()
        db.get_chat_thread.assert_not_called()
    # The bounded transport is the only reader this route may reach.
    legacy_reader.assert_not_called()
    if expected == 200:
        bounded_reader.assert_called_once_with(
            "scout-fixture-task", "0-0", block_ms=250, count=100
        )
        assert "event: task.completed" in response.text
        assert '"thread_id": 76' in response.text
        assert response.headers["X-Scout-Access-Admission"] == "edge-consumed"
    else:
        bounded_reader.assert_not_called()
        assert "task.completed" not in response.text
