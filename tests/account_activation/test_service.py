from __future__ import annotations

import base64
import inspect
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.account_activation.service import (
    ActivationAuthorizationError,
    ActivationConflictError,
    ActivationStateError,
    ActivationUnavailableError,
    issue_activation,
    normalize_recipient_email,
    redeem_activation,
    revoke_activation,
)
from guardian.account_activation.tokens import digest_activation_token
from guardian.core.passwords import hash_password, verify_password
from guardian.db.models import (
    AccountActivationCapability,
    AuditLog,
    User,
)

NOW = datetime(2026, 9, 17, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def session_factory():
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
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    with factory() as session:
        session.add(
            User(
                id="operator@example.com",
                username="operator@example.com",
                email="operator@example.com",
                password_hash=hash_password("operator-test-password"),
                role="admin",
                created_at=NOW,
            )
        )
        session.commit()
    return factory


def _issue(
    session: Session,
    *,
    email: str = "recipient@example.com",
    role: str = "guest",
    now: datetime = NOW,
    expires_at: datetime | None = None,
):
    return issue_activation(
        session,
        recipient_email=email,
        intended_role=role,
        created_by_user_id="operator@example.com",
        expires_at=expires_at or now + timedelta(hours=24),
        now=now,
    )


def test_token_has_256_bits_of_entropy_and_only_digest_is_persisted(
    session_factory,
):
    with session_factory() as session:
        issued = _issue(session)
        session.commit()
        raw_token = issued.raw_token
        activation_id = issued.capability.activation_id

    decoded = base64.urlsafe_b64decode(raw_token + "=" * (-len(raw_token) % 4))
    assert len(decoded) >= 32

    with session_factory() as session:
        capability = session.get(AccountActivationCapability, activation_id)
        assert capability is not None
        assert capability.token_digest == digest_activation_token(raw_token)
        assert raw_token not in {
            str(value)
            for value in vars(capability).values()
            if isinstance(value, str)
        }
        audits = session.scalars(select(AuditLog)).all()
        assert audits
        assert all(raw_token not in str(vars(row)) for row in audits)


def test_issuance_normalizes_recipient_and_binds_canonical_role(session_factory):
    with session_factory() as session:
        issued = _issue(
            session,
            email="  Recipient@Example.COM  ",
            role="GUEST",
        )
        session.commit()
        assert issued.capability.recipient_email == "recipient@example.com"
        assert issued.capability.intended_role == "guest"
        assert issued.capability.expires_at == NOW + timedelta(hours=24)


@pytest.mark.parametrize("role", ["", "owner", "administrator"])
def test_issuance_rejects_noncanonical_roles(session_factory, role):
    with session_factory() as session:
        with pytest.raises(ValueError, match="role must be admin or guest"):
            _issue(session, role=role)


def test_issuance_requires_existing_admin_operator(session_factory):
    with session_factory() as session:
        with pytest.raises(ActivationAuthorizationError):
            issue_activation(
                session,
                recipient_email="recipient@example.com",
                intended_role="guest",
                created_by_user_id="missing@example.com",
                expires_at=NOW + timedelta(hours=1),
                now=NOW,
            )


def test_issuance_refuses_existing_canonical_user(session_factory):
    with session_factory() as session:
        session.add(
            User(
                id="existing-id",
                username="existing-name",
                email="recipient@example.com",
                password_hash=hash_password("existing-password"),
                role="guest",
                created_at=NOW,
            )
        )
        session.commit()
        with pytest.raises(ActivationConflictError, match="canonical account"):
            _issue(session)


def test_duplicate_usable_activation_requires_revocation(session_factory):
    with session_factory() as session:
        first = _issue(session)
        session.commit()

    with session_factory() as session:
        with pytest.raises(ActivationConflictError, match="revoke it first"):
            _issue(session, now=NOW + timedelta(minutes=1))
        session.rollback()
        revoked = revoke_activation(
            session,
            activation_id=first.capability.activation_id,
            actor_user_id="operator@example.com",
            now=NOW + timedelta(minutes=2),
        )
        session.commit()
        assert revoked.revoked_at == NOW + timedelta(minutes=2)

    with session_factory() as session:
        replacement = _issue(session, now=NOW + timedelta(minutes=3))
        session.commit()
        assert replacement.capability.activation_id != first.capability.activation_id


def test_expired_activation_does_not_block_replacement(session_factory):
    with session_factory() as session:
        first = _issue(
            session,
            expires_at=NOW + timedelta(hours=1),
        )
        session.commit()
    with session_factory() as session:
        replacement = _issue(
            session,
            now=NOW + timedelta(hours=2),
            expires_at=NOW + timedelta(hours=3),
        )
        session.commit()
        assert replacement.capability.activation_id != first.capability.activation_id


def test_valid_redemption_creates_bound_user_and_consumes_once(session_factory):
    password = "recipient-selected-password"
    with session_factory() as session:
        issued = _issue(session, email="  Bound@Example.COM ", role="admin")
        session.commit()

    with session_factory() as session:
        user = redeem_activation(
            session,
            raw_token=issued.raw_token,
            password=password,
            now=NOW + timedelta(minutes=1),
        )
        session.commit()
        activation_id = issued.capability.activation_id
        assert user.id == "bound@example.com"
        assert user.username == "bound@example.com"
        assert user.email == "bound@example.com"
        assert user.role == "admin"
        assert user.password_hash != password
        assert verify_password(password, user.password_hash)

    with session_factory() as session:
        capability = session.get(AccountActivationCapability, activation_id)
        assert capability is not None
        assert capability.consumed_at.replace(
            tzinfo=timezone.utc
        ) == NOW + timedelta(minutes=1)
        assert capability.resulting_user_id == "bound@example.com"
        with pytest.raises(ActivationUnavailableError):
            redeem_activation(
                session,
                raw_token=issued.raw_token,
                password="second-password",
                now=NOW + timedelta(minutes=2),
            )


@pytest.mark.parametrize("kind", ["expired", "revoked", "unknown", "malformed"])
def test_unusable_activation_failures_are_generic(session_factory, kind):
    with session_factory() as session:
        issued = _issue(
            session,
            expires_at=NOW + timedelta(minutes=10),
        )
        if kind == "revoked":
            revoke_activation(
                session,
                activation_id=issued.capability.activation_id,
                actor_user_id="operator@example.com",
                now=NOW + timedelta(minutes=1),
            )
        session.commit()

    raw_token = issued.raw_token
    current = NOW + timedelta(minutes=1)
    if kind == "expired":
        current = NOW + timedelta(minutes=11)
    elif kind == "unknown":
        raw_token = "x" * 43
    elif kind == "malformed":
        raw_token = "short"

    with session_factory() as session:
        with pytest.raises(
            ActivationUnavailableError, match="activation_unavailable"
        ):
            redeem_activation(
                session,
                raw_token=raw_token,
                password="recipient-password",
                now=current,
            )


def test_existing_account_collision_does_not_consume_activation(session_factory):
    with session_factory() as session:
        issued = _issue(session)
        session.commit()
        activation_id = issued.capability.activation_id

    with session_factory() as session:
        session.add(
            User(
                id="recipient@example.com",
                username="recipient@example.com",
                email="recipient@example.com",
                password_hash=hash_password("preexisting-password"),
                role="guest",
                created_at=NOW,
            )
        )
        session.commit()

    with session_factory() as session:
        with pytest.raises(ActivationUnavailableError):
            redeem_activation(
                session,
                raw_token=issued.raw_token,
                password="new-password",
                now=NOW + timedelta(minutes=1),
            )
        session.rollback()

    with session_factory() as session:
        capability = session.get(AccountActivationCapability, activation_id)
        assert capability is not None
        assert capability.consumed_at is None
        assert capability.resulting_user_id is None


def test_user_creation_failure_rolls_back_without_consuming(
    session_factory, monkeypatch
):
    with session_factory() as session:
        issued = _issue(session)
        session.commit()
        activation_id = issued.capability.activation_id

    from guardian.account_activation import service

    monkeypatch.setattr(
        service,
        "hash_password",
        lambda _password: (_ for _ in ()).throw(RuntimeError("hash failed")),
    )
    with session_factory() as session:
        with pytest.raises(RuntimeError, match="hash failed"):
            redeem_activation(
                session,
                raw_token=issued.raw_token,
                password="recipient-password",
                now=NOW + timedelta(minutes=1),
            )
        session.rollback()

    with session_factory() as session:
        capability = session.get(AccountActivationCapability, activation_id)
        assert capability is not None
        assert capability.consumed_at is None
        assert capability.resulting_user_id is None
        assert session.get(User, "recipient@example.com") is None


def test_revoke_rejects_terminal_transition(session_factory):
    with session_factory() as session:
        issued = _issue(session)
        revoke_activation(
            session,
            activation_id=issued.capability.activation_id,
            actor_user_id="operator@example.com",
            now=NOW + timedelta(minutes=1),
        )
        session.commit()
    with session_factory() as session:
        with pytest.raises(ActivationStateError, match="already revoked"):
            revoke_activation(
                session,
                activation_id=issued.capability.activation_id,
                actor_user_id="operator@example.com",
                now=NOW + timedelta(minutes=2),
            )


def test_redemption_interface_cannot_accept_email_or_role():
    parameters = inspect.signature(redeem_activation).parameters
    assert "recipient_email" not in parameters
    assert "email" not in parameters
    assert "role" not in parameters
    assert normalize_recipient_email(" User@Example.COM ") == "user@example.com"
