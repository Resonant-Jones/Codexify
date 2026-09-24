from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import StatementError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.account_activation.service import issue_activation
from guardian.cli import tester_account_activation as cli
from guardian.core.passwords import hash_password
from guardian.db.models import AccountActivationCapability, User

RAW_TOKEN = "A" * 43
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
        self._factory = sessionmaker(
            bind=engine,
            expire_on_commit=False,
            future=True,
        )
        self.commit_count = 0
        with self.get_session() as session:
            session.add(
                User(
                    id="operator@example.com",
                    username="operator@example.com",
                    email="operator@example.com",
                    password_hash=hash_password("operator-password"),
                    role="admin",
                    created_at=datetime.now(timezone.utc),
                )
            )
            session.commit()
        self.commit_count = 0

    @contextmanager
    def get_session(self):
        session = self._factory()
        original_commit = session.commit

        def counting_commit(*args, **kwargs):
            self.commit_count += 1
            return original_commit(*args, **kwargs)

        session.commit = counting_commit  # type: ignore[method-assign]
        try:
            yield session
        finally:
            session.close()


def _tester_posture(monkeypatch) -> None:
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", "remote")
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "local_safe")
    monkeypatch.setenv("CODEXIFY_SUPPORTED_PROFILE", "v1-friends-family-web")


def _run(monkeypatch, capsys, db, argv, *, succeeds: bool):
    monkeypatch.setattr(cli, "load_guardian_db_from_env", lambda: db)
    db.commit_count = 0
    if succeeds:
        code = cli.main(argv)
    else:
        with pytest.raises(SystemExit) as exc:
            cli.main(argv)
        code = exc.value.code
    return code, capsys.readouterr()


@contextmanager
def _commit_failing_session(db: _ActivationDb, error: StatementError):
    session = db._factory()

    def fail_commit(*args, **kwargs):
        raise error

    session.commit = fail_commit  # type: ignore[method-assign]
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def test_runtime_posture_is_fail_closed(monkeypatch, capsys):
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", "local")
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "local_safe")
    monkeypatch.setenv("CODEXIFY_SUPPORTED_PROFILE", "v1-friends-family-web")
    db = _ActivationDb()
    code, captured = _run(
        monkeypatch,
        capsys,
        db,
        [
            "issue",
            "--email",
            "recipient@example.com",
            "--role",
            "guest",
            "--actor-user-id",
            "operator@example.com",
            "--base-url",
            "https://preview.example.com",
        ],
        succeeds=False,
    )
    assert code == 2
    assert "GUARDIAN_AUTH_MODE=remote" in captured.err
    assert db.commit_count == 0


def test_issue_prints_one_url_and_no_secret_metadata(
    monkeypatch, capsys
):
    _tester_posture(monkeypatch)
    db = _ActivationDb()
    from guardian.account_activation import service

    monkeypatch.setattr(service, "generate_activation_token", lambda: RAW_TOKEN)
    code, captured = _run(
        monkeypatch,
        capsys,
        db,
        [
            "issue",
            "--email",
            "  Recipient@Example.COM ",
            "--role",
            "guest",
            "--actor-user-id",
            "operator@example.com",
            "--base-url",
            "https://preview.example.com/",
        ],
        succeeds=True,
    )

    assert code == 0
    assert db.commit_count == 1
    assert captured.err == ""
    assert captured.out.count("Activation URL:") == 1
    assert captured.out.count(RAW_TOKEN) == 1
    assert (
        f"Activation URL: https://preview.example.com/activate#token={RAW_TOKEN}"
        in captured.out
    )
    assert "digest" not in captured.out.casefold()
    assert "password" not in captured.out.casefold()

    with db.get_session() as session:
        capability = session.query(AccountActivationCapability).one()
        assert capability.recipient_email == "recipient@example.com"
        assert capability.token_digest != RAW_TOKEN


def test_issue_database_failure_is_bounded_and_prints_no_url(
    monkeypatch, capsys
):
    _tester_posture(monkeypatch)
    db = _ActivationDb()
    error = _database_failure()
    monkeypatch.setattr(
        db, "get_session", lambda: _commit_failing_session(db, error)
    )

    code, captured = _run(
        monkeypatch,
        capsys,
        db,
        [
            "issue",
            "--email",
            "recipient@example.com",
            "--role",
            "guest",
            "--actor-user-id",
            "operator@example.com",
            "--base-url",
            "https://preview.example.com",
        ],
        succeeds=False,
    )

    assert code == 2
    assert captured.out == ""
    assert "Activation URL:" not in captured.err
    assert cli._DATABASE_OPERATION_FAILED in captured.err
    for sentinel in (SENSITIVE_ACTIVATION_DIGEST, SENSITIVE_PASSWORD_HASH):
        assert sentinel not in captured.out
        assert sentinel not in captured.err

    with db._factory() as session:
        assert session.query(AccountActivationCapability).count() == 0


def test_revoke_database_failure_is_bounded_and_secret_free(
    monkeypatch, capsys
):
    _tester_posture(monkeypatch)
    db = _ActivationDb()
    now = datetime.now(timezone.utc)
    with db.get_session() as session:
        issued = issue_activation(
            session,
            recipient_email="recipient@example.com",
            intended_role="guest",
            created_by_user_id="operator@example.com",
            expires_at=now + timedelta(hours=1),
            now=now,
        )
        session.commit()
        activation_id = issued.capability.activation_id

    error = _database_failure()
    monkeypatch.setattr(
        db, "get_session", lambda: _commit_failing_session(db, error)
    )
    code, captured = _run(
        monkeypatch,
        capsys,
        db,
        [
            "revoke",
            "--activation-id",
            activation_id,
            "--actor-user-id",
            "operator@example.com",
        ],
        succeeds=False,
    )

    assert code == 2
    assert captured.out == ""
    assert "Revoked activation:" not in captured.err
    assert cli._DATABASE_OPERATION_FAILED in captured.err
    for sentinel in (SENSITIVE_ACTIVATION_DIGEST, SENSITIVE_PASSWORD_HASH):
        assert sentinel not in captured.out
        assert sentinel not in captured.err

    with db._factory() as session:
        capability = session.get(AccountActivationCapability, activation_id)
        assert capability is not None
        assert capability.revoked_at is None


@pytest.mark.parametrize(
    "base_url",
    [
        "preview.example.com",
        "ftp://preview.example.com",
        "https://user:secret@preview.example.com",
        "https://preview.example.com?token=bad",
        "https://preview.example.com#fragment",
    ],
)
def test_issue_rejects_malformed_or_secret_bearing_base_urls(
    monkeypatch, capsys, base_url
):
    _tester_posture(monkeypatch)
    db = _ActivationDb()
    code, captured = _run(
        monkeypatch,
        capsys,
        db,
        [
            "issue",
            "--email",
            "recipient@example.com",
            "--role",
            "guest",
            "--actor-user-id",
            "operator@example.com",
            "--base-url",
            base_url,
        ],
        succeeds=False,
    )
    assert code == 2
    assert "base URL" in captured.err
    assert db.commit_count == 0


def test_issue_rejects_noncanonical_role(monkeypatch, capsys):
    _tester_posture(monkeypatch)
    db = _ActivationDb()
    code, captured = _run(
        monkeypatch,
        capsys,
        db,
        [
            "issue",
            "--email",
            "recipient@example.com",
            "--role",
            "owner",
            "--actor-user-id",
            "operator@example.com",
            "--base-url",
            "https://preview.example.com",
        ],
        succeeds=False,
    )
    assert code == 2
    assert "invalid choice" in captured.err
    assert db.commit_count == 0


def test_revoke_preserves_capability_lineage(monkeypatch, capsys):
    _tester_posture(monkeypatch)
    db = _ActivationDb()
    now = datetime.now(timezone.utc)
    with db.get_session() as session:
        issued = issue_activation(
            session,
            recipient_email="recipient@example.com",
            intended_role="guest",
            created_by_user_id="operator@example.com",
            expires_at=now + timedelta(hours=1),
            now=now,
        )
        session.commit()
        activation_id = issued.capability.activation_id
    db.commit_count = 0

    code, captured = _run(
        monkeypatch,
        capsys,
        db,
        [
            "revoke",
            "--activation-id",
            activation_id,
            "--actor-user-id",
            "operator@example.com",
        ],
        succeeds=True,
    )
    assert code == 0
    assert db.commit_count == 1
    assert captured.out.count(activation_id) == 1
    assert RAW_TOKEN not in captured.out

    with db.get_session() as session:
        capability = session.get(AccountActivationCapability, activation_id)
        assert capability is not None
        assert capability.revoked_at is not None
