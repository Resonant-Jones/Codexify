"""Focused proof for the canonical, read-only GitHub Knowledge connection."""

from __future__ import annotations

from contextlib import contextmanager

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.connections.github import router as github_routes
from guardian.connections.github import service as github_service
from guardian.db import models as db_models

_API_KEY = "github-test-key"


class _TestDB:
    def __init__(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        db_models.Base.metadata.create_all(
            self.engine,
            tables=[db_models.GitHubKnowledgeCredential.__table__],
        )
        self._SessionLocal = sessionmaker(
            bind=self.engine, autocommit=False, autoflush=False
        )

    @contextmanager
    def get_session(self):
        session = self._SessionLocal()
        try:
            yield session
        finally:
            session.close()

    def credential_for(self, user_id: str):
        with self.get_session() as session:
            return (
                session.query(db_models.GitHubKnowledgeCredential)
                .filter_by(user_id=user_id)
                .one_or_none()
            )


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> tuple[TestClient, _TestDB]:
    monkeypatch.setenv("GUARDIAN_API_KEY", _API_KEY)
    monkeypatch.setenv("DEBUG", "1")
    monkeypatch.setenv("LOCAL_DEV", "true")
    db = _TestDB()
    github_routes.configure_db(db)
    app = FastAPI()
    app.include_router(github_routes.setup_router)
    app.include_router(github_routes.operations_router)
    return TestClient(app), db


def _headers(user_id: str = "user-a") -> dict[str, str]:
    return {"X-API-Key": _API_KEY, "X-User-Id": user_id}


def _configure(client: TestClient, token: str = "github-secret-token") -> None:
    response = client.post(
        "/api/connect/github-knowledge/configure",
        headers=_headers(),
        json={"token": token, "repositories": ["Resonant-Jones/Codexify"]},
    )
    assert response.status_code == 200, response.text


def test_credential_scope_status_and_disconnect(client, monkeypatch):
    test_client, db = client
    _configure(test_client)
    record = db.credential_for("user-a")
    assert record.encrypted_token != "github-secret-token"
    assert record.repositories == ["Resonant-Jones/Codexify"]
    assert db.credential_for("user-b") is None
    status = test_client.get("/api/connect/github-knowledge/status", headers=_headers())
    assert status.status_code == 200
    assert "github-secret-token" not in status.text
    assert "encrypted_token" not in status.text
    assert status.json()["validation"]["state"] == "unvalidated"
    monkeypatch.setattr(github_service.GitHubClient, "validate", lambda self: None)
    assert (
        test_client.post(
            "/api/connect/github-knowledge/validate", headers=_headers()
        ).json()["validation"]["state"]
        == "valid"
    )
    assert (
        test_client.post(
            "/api/connect/github-knowledge/disconnect", headers=_headers("user-b")
        ).json()["removed"]
        is False
    )
    assert db.credential_for("user-a") is not None
    assert (
        test_client.get(
            "/api/knowledge/github/search?repository=Resonant-Jones/Codexify&query=test",
            headers=_headers("user-b"),
        ).status_code
        == 409
    )
    assert (
        test_client.post(
            "/api/connect/github-knowledge/disconnect", headers=_headers()
        ).json()["removed"]
        is True
    )

    def unexpected(*args, **kwargs):
        pytest.fail("no provider call after disconnect")

    monkeypatch.setattr(github_service.GitHubClient, "_request_json", unexpected)
    for path in [
        "/api/knowledge/github/search?repository=Resonant-Jones/Codexify&query=test",
        "/api/knowledge/github/read/Resonant-Jones/Codexify/1",
    ]:
        assert test_client.get(path, headers=_headers()).status_code == 409


def test_cross_repository_refused_before_network(client, monkeypatch):
    test_client, _ = client
    _configure(test_client)

    def unexpected(*args, **kwargs):
        pytest.fail("out-of-scope repository contacted")

    monkeypatch.setattr(github_service.GitHubClient, "_request_json", unexpected)
    for path in [
        "/api/knowledge/github/search?repository=other/private&query=test",
        "/api/knowledge/github/read/other/private/1",
    ]:
        assert test_client.get(path, headers=_headers()).status_code == 403


def test_replacement_invalidates_validation_and_scope(client, monkeypatch):
    test_client, db = client
    _configure(test_client)
    monkeypatch.setattr(github_service.GitHubClient, "validate", lambda self: None)
    test_client.post("/api/connect/github-knowledge/validate", headers=_headers())
    response = test_client.post(
        "/api/connect/github-knowledge/configure",
        headers=_headers(),
        json={"token": "replacement", "repositories": ["owner/new"]},
    )
    assert response.status_code == 200
    assert response.json()["validation"]["state"] == "unvalidated"
    assert db.credential_for("user-a").repositories == ["owner/new"]
    assert db.credential_for("user-a").last_validated_at is None


@pytest.mark.parametrize(
    "repositories", [[], ["https://evil.invalid/repo"], ["owner/../other"], ["*/*"]]
)
def test_bad_scope_not_persisted(client, repositories):
    test_client, db = client
    response = test_client.post(
        "/api/connect/github-knowledge/configure",
        headers=_headers(),
        json={"token": "test", "repositories": repositories},
    )
    assert response.status_code == 422
    assert db.credential_for("user-a") is None


@pytest.mark.parametrize(
    "token", ["sensitive" * 600, {"secret": "must-not-echo"}, 123, None]
)
def test_invalid_token_errors_are_secret_free(client, token):
    test_client, db = client
    response = test_client.post(
        "/api/connect/github-knowledge/configure",
        headers=_headers(),
        json={"token": token, "repositories": ["owner/repo"]},
    )
    assert response.status_code == 422
    assert response.json() == {"detail": {"error": "github_token_required"}}
    assert db.credential_for("user-a") is None


def test_validation_cannot_validate_a_replaced_token(client, monkeypatch):
    test_client, db = client
    _configure(test_client)
    from guardian.connections.github import credentials

    def replace_during_probe(self):
        credentials.configure_token(db, "user-a", "replacement", ["owner/new"])

    monkeypatch.setattr(github_service.GitHubClient, "validate", replace_during_probe)
    response = test_client.post(
        "/api/connect/github-knowledge/validate", headers=_headers()
    )
    assert response.status_code == 200
    assert response.json()["validation"]["state"] == "unvalidated"


@pytest.mark.parametrize(
    "body",
    [
        {"token": "do-not-echo"},
        [{"token": "do-not-echo"}],
        {"token": "do-not-echo", "repositories": "bad"},
    ],
)
def test_setup_schema_errors_never_echo_request(client, body):
    test_client, _ = client
    response = test_client.post(
        "/api/connect/github-knowledge/configure", headers=_headers(), json=body
    )
    assert response.status_code == 422
    assert "do-not-echo" not in response.text
    assert "input" not in response.text


def test_catalog_github_setup_availability_is_mounted_and_account_scoped(client, monkeypatch):
    from guardian.routes import connections
    test_client, db = client
    connections.configure_db(db)
    test_client.app.include_router(connections.router)
    _configure(test_client)
    response = test_client.get('/api/connections/github_knowledge', headers=_headers())
    assert response.status_code == 200
    data = response.json()
    assert data['implementation_state'] == 'experimental'
    assert data['setup_state'] == 'configured'
    assert data['runtime_binding']['setup_route'] == '/api/connect/github-knowledge/configure'
    assert data['validation']['repositories'] == ['Resonant-Jones/Codexify']
    assert 'github-secret-token' not in response.text
    other = test_client.get('/api/connections/github_knowledge', headers=_headers('user-b')).json()
    assert other['setup_state'] == 'needs_setup'
    assert 'repositories' not in other['validation']
    unmounted = FastAPI()
    unmounted.include_router(connections.router)
    data = TestClient(unmounted).get('/api/connections/github_knowledge', headers=_headers()).json()
    assert data['setup_state'] == 'unavailable'
    assert data['runtime_binding']['setup_route'] is None
    assert data['authorization']['available'] is False


def test_catalog_missing_migration_fails_unavailable(client, monkeypatch):
    from guardian.routes import connections
    from guardian.connections.github import credentials
    test_client, db = client
    connections.configure_db(db)
    test_client.app.include_router(connections.router)
    def missing(*args):
        raise RuntimeError('private-db-details')
    monkeypatch.setattr(credentials, 'status_projection', missing)
    response = test_client.get('/api/connections/github_knowledge', headers=_headers())
    assert response.status_code == 200
    assert response.json()['setup_state'] == 'unavailable'
    assert 'private-db-details' not in response.text


def test_remote_setup_and_read_reject_operator_key_as_account(client, monkeypatch):
    from guardian.core import dependencies
    test_client, db = client
    monkeypatch.setattr(dependencies, 'is_private_preview', lambda: False)
    monkeypatch.setattr(dependencies, '_auth_mode', lambda: 'remote')
    response = test_client.post('/api/connect/github-knowledge/configure', headers=_headers(), json={'token': 'never-store', 'repositories': ['owner/repo']})
    assert response.status_code == 401
    assert db.credential_for('user-a') is None
    assert test_client.get('/api/knowledge/github/search?repository=owner/repo&query=test', headers=_headers()).status_code == 401
