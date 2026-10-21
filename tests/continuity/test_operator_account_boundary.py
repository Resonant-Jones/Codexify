"""Fail-closed containment of the legacy, account-unbound operator surface."""

from unittest.mock import Mock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from guardian.core import dependencies
from guardian.core.auth import OPERATOR_SESSION_PURPOSE, issue_session_token
from guardian.routes import continuity_operator as routes


PATHS = [
    ("POST", "/reality-stamp"),
    ("GET", "/context-packets/account-a-packet"),
    ("GET", "/diagnostics"),
    ("GET", "/reality-states/account-a-state"),
    ("GET", "/reality-commits/account-a-commit"),
    ("GET", "/state-packet-links/account-a-link"),
]


def _payload():
    return {
        "action_id": "attempt",
        "actor_id": "account-a",
        "packet_id": "packet",
        "created_at": "2026-10-21T00:00:00Z",
        "summary": "attempt",
        "user_id": "account-a",
        "project_id": "account-a-project",
        "thread_id": "account-a-thread",
    }


@pytest.fixture
def operator_client(monkeypatch):
    monkeypatch.setenv("GUARDIAN_SESSION_SECRET", "continuity-boundary-test-secret")
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", "local")
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "local_safe")
    monkeypatch.setattr(
        dependencies.get_core_settings(), "CODEXIFY_MULTI_USER_ENABLED", False
    )
    app = FastAPI()
    app.include_router(routes.router)
    with TestClient(app) as client:
        yield client


@pytest.mark.parametrize("method,path", PATHS)
@pytest.mark.parametrize("mode", ["remote", "preview", "multiuser"])
@pytest.mark.parametrize("credential", ["operator_token", "api_key"])
def test_unbound_operator_cannot_reach_database(
    monkeypatch, operator_client, method, path, mode, credential
):
    if mode == "remote":
        monkeypatch.setenv("GUARDIAN_AUTH_MODE", "remote")
    elif mode == "preview":
        monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "private_preview")
    else:
        monkeypatch.setattr(
            dependencies.get_core_settings(), "CODEXIFY_MULTI_USER_ENABLED", True
        )
    database = Mock(side_effect=AssertionError("Unauthorized database access"))
    monkeypatch.setattr(routes, "get_database_dsn", database)
    # Neither an operator subject nor forged ownership claims establish an account.
    headers = {"X-User-Id": "account-a"}
    if credential == "operator_token":
        token, _ = issue_session_token(
            subject="account-a", purpose=OPERATOR_SESSION_PURPOSE, ttl_seconds=60
        )
        headers["Authorization"] = f"Bearer {token}"
    else:
        headers["X-API-Key"] = "test-api-key"
    response = operator_client.request(
        method,
        "/api/operator/continuity" + path,
        headers=headers,
        **({"json": _payload()} if method == "POST" else {}),
    )
    assert response.status_code == 403, response.text
    database.assert_not_called()


@pytest.mark.parametrize("method,path", PATHS)
def test_local_single_user_can_reach_existing_operation(
    monkeypatch, operator_client, method, path
):
    database = Mock(side_effect=HTTPException(status_code=503, detail="DB sentinel"))
    monkeypatch.setattr(routes, "get_database_dsn", database)
    response = operator_client.request(
        method,
        "/api/operator/continuity" + path,
        headers={"X-API-Key": "test-api-key"},
        **({"json": _payload()} if method == "POST" else {}),
    )
    assert response.status_code == 503
    assert response.json()["detail"] == "DB sentinel"
    database.assert_called_once_with()
