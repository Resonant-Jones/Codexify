from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import logging
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import StatementError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.account_activation.service import (
    issue_activation,
    redeem_activation,
    revoke_activation,
)
from guardian.core.passwords import hash_password
from guardian.db.models import AccountActivationCapability, User

SENSITIVE_ACTIVATION_DIGEST = "SENSITIVE_ACTIVATION_DIGEST"
SENSITIVE_PASSWORD_HASH = "SENSITIVE_PASSWORD_HASH"


def _database_failure() -> StatementError:
    return StatementError(
        "activation persistence failed",
        "INSERT INTO account_activation_capabilities "
        "(token_digest, password_hash) VALUES (:token_digest, :password_hash)",
        {
            "token_digest": SENSITIVE_ACTIVATION_DIGEST,
            "password_hash": SENSITIVE_PASSWORD_HASH,
        },
        RuntimeError("database failure"),
    )


class _ActivationDb:
    def __init__(self) -> None:
        engine = create_engine(
            "sqlite+pysqlite://",
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        User.__table__.create(engine)
        AccountActivationCapability.__table__.create(engine)
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "CREATE TABLE audit_log ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "event TEXT NOT NULL, entity TEXT NOT NULL, "
                "entity_id TEXT NOT NULL, user_id TEXT NOT NULL, "
                "timestamp TIMESTAMP NOT NULL)"
            )
        self._session_factory = sessionmaker(
            bind=engine,
            expire_on_commit=False,
            future=True,
        )
        now = datetime.now(timezone.utc)
        with self.get_session() as session:
            session.add(
                User(
                    id="operator@example.com",
                    username="operator@example.com",
                    email="operator@example.com",
                    password_hash=hash_password("operator-password"),
                    role="admin",
                    created_at=now,
                )
            )
            session.commit()

    @contextmanager
    def get_session(self):
        session = self._session_factory()
        try:
            yield session
        finally:
            session.close()


@pytest.fixture
def activation_client():
    from guardian.routes import auth

    db = _ActivationDb()
    app = FastAPI()
    app.include_router(auth.api_router)
    with patch.object(auth, "load_guardian_db_from_env", return_value=db):
        yield TestClient(app), db


def _issue(db: _ActivationDb, *, now: datetime | None = None):
    issued_at = now or datetime.now(timezone.utc)
    with db.get_session() as session:
        issued = issue_activation(
            session,
            recipient_email="recipient@example.com",
            intended_role="guest",
            created_by_user_id="operator@example.com",
            expires_at=issued_at + timedelta(hours=1),
            now=issued_at,
        )
        session.commit()
        return issued


def test_successful_public_redemption_creates_account_without_session(
    activation_client,
):
    client, db = activation_client
    issued = _issue(db)

    response = client.post(
        "/api/auth/activate",
        json={
            "token": issued.raw_token,
            "password": "recipient-chosen-password",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "user_id": "recipient@example.com",
        "username": "recipient@example.com",
    }
    assert "token" not in response.json()
    assert "expires_at" not in response.json()


def test_activated_account_uses_existing_normal_login(activation_client):
    client, db = activation_client
    issued = _issue(db)
    password = "recipient-chosen-password"
    assert client.post(
        "/api/auth/activate",
        json={"token": issued.raw_token, "password": password},
    ).status_code == 200

    from guardian.routes import auth

    session_store = MagicMock()
    with patch.object(auth, "get_session_store", return_value=session_store):
        login = client.post(
            "/api/auth/login",
            json={"username": "recipient@example.com", "password": password},
        )

    assert login.status_code == 200
    assert login.json()["user_id"] == "recipient@example.com"
    assert login.json()["token"]
    session_store.store.assert_called_once()


@pytest.mark.parametrize(
    "failure_kind",
    ["unknown", "malformed", "expired", "revoked", "consumed"],
)
def test_all_unusable_capabilities_share_one_public_failure(
    activation_client,
    failure_kind,
):
    client, db = activation_client
    now = datetime.now(timezone.utc)
    issued = _issue(
        db,
        now=now - timedelta(hours=2)
        if failure_kind == "expired"
        else now,
    )
    token = issued.raw_token

    if failure_kind == "unknown":
        token = "x" * 43
    elif failure_kind == "malformed":
        token = "short"
    elif failure_kind == "revoked":
        with db.get_session() as session:
            revoke_activation(
                session,
                activation_id=issued.capability.activation_id,
                actor_user_id="operator@example.com",
                now=now,
            )
            session.commit()
    elif failure_kind == "consumed":
        with db.get_session() as session:
            redeem_activation(
                session,
                raw_token=token,
                password="first-password",
                now=now,
            )
            session.commit()

    response = client.post(
        "/api/auth/activate",
        json={"token": token, "password": "new-password"},
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "activation_unavailable"}


def test_unexpected_database_failure_is_generic_and_secret_free(
    activation_client, caplog, monkeypatch
):
    from guardian.routes import auth

    client, _ = activation_client
    monkeypatch.setattr(
        auth,
        "redeem_activation",
        MagicMock(side_effect=_database_failure()),
    )

    with patch.object(
        auth.logger, "warning", wraps=auth.logger.warning
    ) as logger_warning:
        with patch.object(auth.logger, "exception") as logger_exception:
            with caplog.at_level(logging.WARNING, logger=auth.logger.name):
                response = client.post(
                    "/api/auth/activate",
                    json={
                        "token": "synthetic-activation-token",
                        "password": "synthetic-recipient-password",
                    },
                )

    assert response.status_code == 503
    assert response.json() == {"detail": "activation_unavailable"}
    assert "activation_redemption_failed operation=redeem" in caplog.text
    logger_warning.assert_called_once()
    assert logger_warning.call_args.args[-1] == "StatementError"
    logger_exception.assert_not_called()
    for sentinel in (SENSITIVE_ACTIVATION_DIGEST, SENSITIVE_PASSWORD_HASH):
        assert sentinel not in caplog.text
        assert sentinel not in response.text


@pytest.mark.parametrize("extra_field", ["email", "role", "user_id", "actor_id"])
def test_redemption_rejects_caller_supplied_authority_fields(
    activation_client,
    extra_field,
):
    client, db = activation_client
    issued = _issue(db)
    response = client.post(
        "/api/auth/activate",
        json={
            "token": issued.raw_token,
            "password": "recipient-password",
            extra_field: "attacker-controlled",
        },
    )
    assert response.status_code == 422

    with db.get_session() as session:
        capability = session.get(
            AccountActivationCapability, issued.capability.activation_id
        )
        assert capability is not None
        assert capability.consumed_at is None
        assert session.get(User, "recipient@example.com") is None
