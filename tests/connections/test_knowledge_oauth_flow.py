"""OAuth route/lifecycle integration using disposable SQLite and mocked providers."""

from contextlib import contextmanager
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit
import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.connections import (
    knowledge_oauth as oauth,
    oauth_store as store,
    oauth_providers as providers,
)
from guardian.connections.knowledge_oauth_routes import make_router
from guardian.core.dependencies import require_account_session, get_account_user_id
from guardian.db import models


@pytest.fixture
def setup(monkeypatch):
    monkeypatch.setenv("CODEXIFY_ENABLE_KNOWLEDGE_OAUTH", "1")
    monkeypatch.setenv(
        "GUARDIAN_OAUTH_TOKEN_ENCRYPTION_KEY",
        "YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWE=",
    )
    monkeypatch.delenv("CODEXIFY_PRIVATE_PREVIEW", raising=False)
    for provider, path in [("NOTION", "notion"), ("GITHUB_APP", "github-knowledge")]:
        for suffix, value in [
            ("CLIENT_ID", "id"),
            ("CLIENT_SECRET", "secret"),
            ("REDIRECT_URI", f"https://example.test/api/connect/{path}/oauth/callback"),
        ]:
            monkeypatch.setenv(f"CODEXIFY_{provider}_OAUTH_{suffix}", value)
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    tables = [
        models.User.__table__,
        models.KnowledgeOAuthCredential.__table__,
        models.KnowledgeOAuthFlow.__table__,
        models.NotionConnectionCredential.__table__,
        models.GitHubKnowledgeCredential.__table__,
    ]
    models.Base.metadata.create_all(engine, tables=tables)
    factory = sessionmaker(engine)

    @contextmanager
    def session():
        with factory() as s:
            yield s

    db = SimpleNamespace(get_session=session)
    with session() as s:
        s.add_all(
            [models.User(id=x, username=x, password_hash="unused") for x in ("a", "b")]
        )
        s.commit()
    app = FastAPI()
    app.dependency_overrides[require_account_session] = lambda: "session"
    app.dependency_overrides[get_account_user_id] = lambda: "a"
    for provider in ("github", "notion"):
        app.include_router(make_router(provider, lambda: db))
    monkeypatch.setattr(
        providers,
        "exchange_code",
        lambda *a, **k: providers.OAuthTokens(
            "token", "refresh", 3600, metadata={"workspace_id": "workspace"}
        ),
    )
    monkeypatch.setattr(
        providers, "github_identity", lambda token: {"id": 123, "login": "alice"}
    )
    from guardian.connections.notion.service import NotionClient

    monkeypatch.setattr(NotionClient, "validate", lambda self: None)
    return TestClient(app, base_url="https://example.test"), db, app


def begin(client, name="notion"):
    response = client.post(
        f"/api/connect/{name}/oauth/start", headers={"origin": "https://example.test"}
    )
    assert response.status_code == 200, response.text
    return parse_qs(urlsplit(response.json()["authorization_url"]).query)["state"][0]


def callback(client, state, name="notion"):
    return client.get(
        f"/api/connect/{name}/oauth/callback",
        params={"state": state, "code": "private-code"},
    )


def test_roundtrip_scope_safe_status_replay_and_disconnect(setup):
    client, db, app = setup
    state = begin(client)
    response = callback(client, state)
    assert response.status_code == 200
    assert "private-code" not in response.text
    assert response.headers["referrer-policy"] == "no-referrer"
    assert store.credential(db, "a", "notion").access_token == "token"
    assert store.credential(db, "b", "notion") is None
    assert callback(client, state).status_code == 400
    status = client.get("/api/connect/notion/oauth/status")
    assert status.json()["configured"] is True
    assert "token" not in status.text and "refresh" not in status.text
    assert (
        client.post(
            "/api/connect/notion/oauth/disconnect",
            headers={"origin": "https://example.test"},
        ).status_code
        == 200
    )
    assert store.credential(db, "a", "notion") is None


def test_callback_requires_initiating_browser_and_provider(setup):
    client, db, app = setup
    state = begin(client)
    other = TestClient(app, base_url="https://example.test")
    assert callback(other, state).status_code == 400
    assert callback(client, state, "github-knowledge").status_code == 400
    assert callback(client, state).status_code == 200


def test_start_requires_origin_and_account(setup):
    client, db, app = setup
    assert client.post("/api/connect/notion/oauth/start").status_code == 403
    assert (
        client.post(
            "/api/connect/notion/oauth/start", headers={"origin": "https://evil.test"}
        ).status_code
        == 403
    )
    app.dependency_overrides[get_account_user_id] = lambda: "missing"
    assert (
        client.post(
            "/api/connect/notion/oauth/start",
            headers={"origin": "https://example.test"},
        ).status_code
        == 409
    )


def test_disconnect_during_callback_cannot_resurrect(setup, monkeypatch):
    client, db, _ = setup
    state = begin(client)

    def exchange(*a, **kw):
        store.disconnect(db, "a", "notion")
        return providers.OAuthTokens("late", "refresh", 3600)

    monkeypatch.setattr(providers, "exchange_code", exchange)
    assert callback(client, state).status_code == 400
    assert store.credential(db, "a", "notion") is None


def test_github_requires_explicit_scoped_repositories(setup, monkeypatch):
    client, db, _ = setup
    state = begin(client, "github-knowledge")
    assert callback(client, state, "github-knowledge").status_code == 200
    assert store.status(db, "a", "github")["state"] == "needs_scope"
    monkeypatch.setattr(
        providers,
        "github_installations",
        lambda token: {"installations": [{"id": 1}], "incomplete": False},
    )
    monkeypatch.setattr(
        providers,
        "github_installation_repositories",
        lambda *a: {
            "repositories": [{"id": 7, "full_name": "org/one"}],
            "incomplete": False,
        },
    )
    path = "/api/connect/github-knowledge/oauth/repositories"
    assert (
        client.put(
            path,
            headers={"origin": "https://example.test"},
            json={"installation_id": 2, "repositories": ["org/one"]},
        ).status_code
        == 409
    )
    assert (
        client.put(
            path,
            headers={"origin": "https://example.test"},
            json={"installation_id": 1, "repositories": ["org/two"]},
        ).status_code
        == 409
    )
    assert (
        client.put(
            path,
            headers={"origin": "https://example.test"},
            json={"installation_id": 1, "repositories": ["org/one"]},
        ).json()["configured"]
        is True
    )
    from guardian.connections.github.credentials import configured_connection

    assert configured_connection(db, "a") == ("token", ["org/one"])


def test_refresh_rotation_and_omitted_notion_metadata(setup, monkeypatch):
    client, db, _ = setup
    callback(client, begin(client))
    with db.get_session() as s:
        s.query(models.KnowledgeOAuthCredential).update({"expires_at": time.time() - 1})
        s.commit()
    monkeypatch.setattr(
        providers,
        "refresh_tokens",
        lambda *a, **k: providers.OAuthTokens("next", "next-refresh", 3600),
    )
    snapshot = oauth.credential(db, "a", "notion")
    assert snapshot.access_token == "next"
    assert snapshot.metadata["workspace_id"] == "workspace"


def test_refresh_identity_swap_fails_closed(setup, monkeypatch):
    client, db, _ = setup
    callback(client, begin(client, "github-knowledge"), "github-knowledge")
    with db.get_session() as s:
        s.query(models.KnowledgeOAuthCredential).update({"expires_at": time.time() - 1})
        s.commit()
    monkeypatch.setattr(
        providers,
        "refresh_tokens",
        lambda *a, **k: providers.OAuthTokens("next", "next-refresh", 3600),
    )
    monkeypatch.setattr(
        providers, "github_identity", lambda token: {"id": 666, "login": "other"}
    )
    with pytest.raises(oauth.KnowledgeOAuthError):
        oauth.credential(db, "a", "github")
    assert store.status(db, "a", "github")["state"] == "reconnect_required"


def test_mutating_scope_requires_origin(setup):
    client, _, _ = setup
    assert client.post("/api/connect/notion/oauth/disconnect").status_code != 200
    assert (
        client.put(
            "/api/connect/github-knowledge/oauth/repositories",
            json={"installation_id": 1, "repositories": ["org/one"]},
        ).status_code
        != 200
    )


def test_callback_provider_error_is_not_reflected(setup):
    client, _, _ = setup
    state = begin(client)
    response = client.get(
        "/api/connect/notion/oauth/callback",
        params={"state": state, "error": "secret-error-token"},
    )
    assert response.status_code == 400
    assert "secret-error-token" not in response.text


def test_missing_operator_configuration_is_visible_without_secret(setup, monkeypatch):
    client, _, _ = setup
    monkeypatch.delenv("CODEXIFY_NOTION_OAUTH_CLIENT_SECRET")
    assert client.get("/api/connect/notion/oauth/status").json()["available"] is False
    assert (
        client.post(
            "/api/connect/notion/oauth/start",
            headers={"origin": "https://example.test"},
        ).status_code
        == 409
    )


def test_legacy_setup_blocked_while_oauth_enabled(setup):
    client, db, app = setup
    from guardian.connections.notion import router

    router.configure_db(db)
    app.include_router(router.setup_router)
    response = client.post(
        "/api/connect/notion/configure",
        json={"settings": {"integration_token": "never-store"}},
    )
    assert response.status_code == 409
    assert "never-store" not in response.text


def test_oauth_catalog_requires_actual_mount_and_operator_config(setup, monkeypatch):
    _, _, _ = setup
    from guardian.connections.catalog import (
        _notion_knowledge_entry,
        _github_knowledge_entry,
    )
    from guardian.routes.connections import _project_entry

    for entry, provider in [
        (_notion_knowledge_entry(), "notion"),
        (_github_knowledge_entry(), "github"),
    ]:
        args = dict(
            channel_configs=set(),
            oauth_rows={},
            notion_validation={"state": "unconfigured"},
            github_validation={"state": "unconfigured"},
            github_setup_available=True,
        )
        absent = _project_entry(entry, **args)
        assert absent["oauth"]["launchable"] is False
        assert absent["runtime_binding"]["setup_route"] is None
        mounted = _project_entry(entry, knowledge_oauth_mounted={provider}, **args)
        assert mounted["oauth"]["launchable"] is True
        assert mounted["auth_methods"] == ["oauth_browser"]
        assert mounted["required_fields"] == []


def test_provider_revocation_invalidates_only_matching_oauth_token(setup):
    client, db, _ = setup
    callback(client, begin(client))
    from guardian.connections.notion import credentials

    credentials.mark_validation(
        db, "a", credentials.VALIDATION_AUTHORIZATION_ERROR, expected_token="stale"
    )
    assert store.status(db, "a", "notion")["configured"] is True
    credentials.mark_validation(
        db, "a", credentials.VALIDATION_AUTHORIZATION_ERROR, expected_token="token"
    )
    assert store.status(db, "a", "notion")["state"] == "reconnect_required"


def test_simulated_notion_bridge_callback_read_source_and_revocation(
    setup, monkeypatch
):
    """Real account routes/store, mocked external provider, not live consent proof."""
    client, db, app = setup
    from guardian.connections.notion import router, service

    router.configure_db(db)
    app.include_router(router.operations_router)
    calls = []

    def search(adapter, **kwargs):
        calls.append((adapter._integration_token, kwargs["query"]))
        return {
            "results": [
                {
                    "id": "page-id",
                    "url": "https://www.notion.so/page-id",
                    "title": "Approved page",
                }
            ]
        }

    monkeypatch.setattr(service.NotionClient, "search", search)
    assert callback(client, begin(client)).status_code == 200
    response = client.get("/api/knowledge/notion/search", params={"query": "pilot"})
    assert response.status_code == 200
    assert response.json()["results"][0]["url"] == "https://www.notion.so/page-id"
    assert calls == [("token", "pilot")]
    app.dependency_overrides[get_account_user_id] = lambda: "b"
    assert (
        client.get(
            "/api/knowledge/notion/search", params={"query": "pilot"}
        ).status_code
        == 409
    )
    assert len(calls) == 1
    app.dependency_overrides[get_account_user_id] = lambda: "a"
    assert (
        client.post(
            "/api/connect/notion/oauth/disconnect",
            headers={"origin": "https://example.test"},
        ).status_code
        == 200
    )
    assert (
        client.get(
            "/api/knowledge/notion/search", params={"query": "pilot"}
        ).status_code
        == 409
    )
    assert len(calls) == 1
