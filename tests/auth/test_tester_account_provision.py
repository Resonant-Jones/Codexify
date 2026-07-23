"""Focused tests for the tester account provisioner.

These tests never touch the live tester database. They reuse the repository's
existing Guardian auth test pattern: a narrow in-memory SQLite engine bound
only to the canonical ``users`` table (which has no Postgres-only columns),
patched in for ``load_guardian_db_from_env``. The real ``users`` CHECK
constraint ('admin', 'guest') is therefore in effect, so the noncanonical-role
guard is exercised through the pure ``resolve_role`` helper as defense in depth.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.cli import tester_account_provision as tap
from guardian.core.passwords import hash_password, verify_password
from guardian.db.models import User

TESTER_PROFILE = "v1-friends-family-web"


def _apply_tester_posture(monkeypatch) -> None:
    """Configure the exact stabilized tester runtime posture."""
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", "remote")
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "local_safe")
    monkeypatch.setenv("CODEXIFY_SUPPORTED_PROFILE", TESTER_PROFILE)


class _FakeStdin:
    def __init__(self, isatty_value: bool) -> None:
        self._isatty = isatty_value

    def isatty(self) -> bool:
        return self._isatty


class _FakeAuthDb:
    """Narrow fake Guardian DB over the canonical users table."""

    def __init__(self) -> None:
        engine = create_engine(
            "sqlite+pysqlite://",
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        User.__table__.create(engine)
        self._session_factory = sessionmaker(
            bind=engine,
            autoflush=False,
            autocommit=False,
            future=True,
        )
        self.commit_count = 0

    @contextmanager
    def get_session(self):
        session = self._session_factory()
        original_commit = session.commit
        owner = self

        def _counting_commit(*args, **kwargs):
            owner.commit_count += 1
            return original_commit(*args, **kwargs)

        session.commit = _counting_commit  # type: ignore[method-assign]
        try:
            yield session
        finally:
            session.close()

    def seed_user(
        self,
        *,
        email: str,
        role: str = "guest",
        password: str = "seed-only-test-password",
    ) -> None:
        with self.get_session() as session:
            session.add(
                User(
                    id=email,
                    username=email,
                    password_hash=hash_password(password),
                    role=role,
                    created_at=datetime.now(timezone.utc),
                )
            )
            session.commit()
        self.commit_count = 0


def _run_main(
    monkeypatch,
    capsys,
    *,
    argv,
    db,
    tty: bool = True,
    getpass_responses=None,
    raises: bool = True,
):
    """Invoke ``main`` with controlled stdin, db, and getpass seams."""
    monkeypatch.setattr(tap, "load_guardian_db_from_env", lambda: db)
    monkeypatch.setattr(tap.sys, "stdin", _FakeStdin(tty))
    if getpass_responses is not None:
        responses = list(getpass_responses)

        def _fake_getpass(prompt="Password: "):
            if not responses:
                raise AssertionError(f"unexpected getpass call: {prompt!r}")
            return responses.pop(0)

        monkeypatch.setattr(tap.getpass, "getpass", _fake_getpass)
    monkeypatch.setattr(
        tap.sys, "argv", ["tester_account_provision", *list(argv)]
    )
    if db is not None:
        db.commit_count = 0

    if raises:
        with pytest.raises(SystemExit) as exc_info:
            tap.main()
        code = exc_info.value.code
    else:
        code = tap.main()
    captured = capsys.readouterr()
    return code, captured


# --------------------------------------------------------------------------
# Runtime posture (fail closed)
# --------------------------------------------------------------------------


def test_posture_rejects_auth_mode_other_than_remote(monkeypatch):
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", "local")
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "local_safe")
    monkeypatch.setenv("CODEXIFY_SUPPORTED_PROFILE", TESTER_PROFILE)
    err = tap.runtime_posture_error()
    assert err is not None
    assert "GUARDIAN_AUTH_MODE=remote" in err


def test_posture_rejects_exposure_mode_other_than_local_safe(monkeypatch):
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", "remote")
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "private_preview")
    monkeypatch.setenv("CODEXIFY_SUPPORTED_PROFILE", TESTER_PROFILE)
    err = tap.runtime_posture_error()
    assert err is not None
    assert "GUARDIAN_EXPOSURE_MODE=local_safe" in err


def test_posture_rejects_profile_other_than_friends_family(monkeypatch):
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", "remote")
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "local_safe")
    monkeypatch.setenv("CODEXIFY_SUPPORTED_PROFILE", "v1-local-core-web-mcp")
    err = tap.runtime_posture_error()
    assert err is not None
    assert "CODEXIFY_SUPPORTED_PROFILE=v1-friends-family-web" in err


def test_posture_rejects_missing_runtime_mode_variables(monkeypatch):
    monkeypatch.delenv("GUARDIAN_AUTH_MODE", raising=False)
    monkeypatch.delenv("GUARDIAN_EXPOSURE_MODE", raising=False)
    monkeypatch.delenv("CODEXIFY_SUPPORTED_PROFILE", raising=False)
    err = tap.runtime_posture_error()
    assert err is not None
    assert "GUARDIAN_AUTH_MODE=remote" in err
    assert "GUARDIAN_EXPOSURE_MODE=local_safe" in err
    assert "CODEXIFY_SUPPORTED_PROFILE=v1-friends-family-web" in err


def test_posture_accepts_exact_tester_runtime(monkeypatch):
    _apply_tester_posture(monkeypatch)
    assert tap.runtime_posture_error() is None


def test_main_refuses_wrong_posture_with_nonzero_exit(monkeypatch, capsys):
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", "local")
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "local_safe")
    monkeypatch.setenv("CODEXIFY_SUPPORTED_PROFILE", TESTER_PROFILE)
    monkeypatch.setattr(tap.sys, "stdin", _FakeStdin(True))
    monkeypatch.setattr(
        tap.sys,
        "argv",
        [
            "tester_account_provision",
            "--email",
            "admin@example.com",
            "--role",
            "admin",
        ],
    )
    with pytest.raises(SystemExit) as exc:
        tap.main()
    assert exc.value.code == 2
    assert "GUARDIAN_AUTH_MODE=remote" in capsys.readouterr().err


# --------------------------------------------------------------------------
# Interactive terminal + password input boundary
# --------------------------------------------------------------------------


def test_main_refuses_noninteractive_stdin(monkeypatch, capsys):
    _apply_tester_posture(monkeypatch)
    db = _FakeAuthDb()
    code, captured = _run_main(
        monkeypatch,
        capsys,
        argv=["--email", "admin@example.com", "--role", "admin"],
        db=db,
        tty=False,
        getpass_responses=[],
    )
    assert code == 2
    assert "interactive terminal" in captured.err
    assert db.commit_count == 0


def test_main_rejects_empty_password(monkeypatch, capsys):
    _apply_tester_posture(monkeypatch)
    db = _FakeAuthDb()
    code, captured = _run_main(
        monkeypatch,
        capsys,
        argv=["--email", "admin@example.com", "--role", "admin"],
        db=db,
        getpass_responses=["", ""],
    )
    assert code == 2
    assert "password" in captured.err.lower()
    assert db.commit_count == 0


def test_main_rejects_mismatched_password_confirmation(monkeypatch, capsys):
    _apply_tester_posture(monkeypatch)
    db = _FakeAuthDb()
    code, captured = _run_main(
        monkeypatch,
        capsys,
        argv=["--email", "admin@example.com", "--role", "admin"],
        db=db,
        getpass_responses=["one-test-only-value", "a-different-test-only-value"],
    )
    assert code == 2
    assert "match" in captured.err.lower()
    assert db.commit_count == 0


# --------------------------------------------------------------------------
# Email + role input validation
# --------------------------------------------------------------------------


def test_main_rejects_malformed_email(monkeypatch, capsys):
    _apply_tester_posture(monkeypatch)
    db = _FakeAuthDb()
    code, captured = _run_main(
        monkeypatch,
        capsys,
        argv=["--email", "not-an-email", "--role", "admin"],
        db=db,
        getpass_responses=[],
    )
    assert code == 2
    assert "email" in captured.err.lower()


def test_normalize_email_rejects_empty_and_missing_components():
    with pytest.raises(ValueError):
        tap.normalize_email("")
    with pytest.raises(ValueError):
        tap.normalize_email("   ")
    with pytest.raises(ValueError):
        tap.normalize_email("no-at-sign")
    with pytest.raises(ValueError):
        tap.normalize_email("@example.com")
    with pytest.raises(ValueError):
        tap.normalize_email("admin@")


def test_normalize_email_trims_case_folds_and_lowercases_local_part():
    assert tap.normalize_email("  Admin@Example.COM ") == "admin@example.com"


def test_main_rejects_new_account_without_role(monkeypatch, capsys):
    _apply_tester_posture(monkeypatch)
    db = _FakeAuthDb()
    code, captured = _run_main(
        monkeypatch,
        capsys,
        argv=["--email", "admin@example.com"],
        db=db,
        getpass_responses=[],
    )
    assert code == 2
    assert "--role is required" in captured.err
    assert db.commit_count == 0
    with db.get_session() as session:
        assert session.get(User, "admin@example.com") is None


def test_argparse_rejects_role_outside_admin_guest(monkeypatch, capsys):
    _apply_tester_posture(monkeypatch)
    db = _FakeAuthDb()
    code, _captured = _run_main(
        monkeypatch,
        capsys,
        argv=["--email", "admin@example.com", "--role", "superuser"],
        db=db,
        getpass_responses=[],
    )
    assert code == 2


# --------------------------------------------------------------------------
# New account creation
# --------------------------------------------------------------------------


def test_main_creates_new_admin_account(monkeypatch, capsys):
    _apply_tester_posture(monkeypatch)
    db = _FakeAuthDb()
    email = "admin@example.com"
    password = "test-only-admin-password"
    code, captured = _run_main(
        monkeypatch,
        capsys,
        argv=["--email", email, "--role", "admin"],
        db=db,
        getpass_responses=[password, password],
        raises=False,
    )
    assert code == 0
    assert db.commit_count == 1
    with db.get_session() as session:
        user = session.get(User, email)
        assert user is not None
        assert user.id == email
        assert user.username == email
        assert user.role == "admin"
        assert user.password_hash.startswith("$2")
        assert user.password_hash != password
        assert verify_password(password, user.password_hash) is True
    assert "Created account" in captured.out
    assert email in captured.out


def test_main_creates_new_guest_account(monkeypatch, capsys):
    _apply_tester_posture(monkeypatch)
    db = _FakeAuthDb()
    email = "guest@example.com"
    password = "test-only-guest-password"
    code, captured = _run_main(
        monkeypatch,
        capsys,
        argv=["--email", email, "--role", "guest"],
        db=db,
        getpass_responses=[password, password],
        raises=False,
    )
    assert code == 0
    assert db.commit_count == 1
    with db.get_session() as session:
        user = session.get(User, email)
        assert user is not None
        assert user.role == "guest"
        assert verify_password(password, user.password_hash) is True
    assert "Created account" in captured.out


# --------------------------------------------------------------------------
# Existing account reset + role behavior
# --------------------------------------------------------------------------


def test_main_resets_password_preserving_role_when_role_omitted(
    monkeypatch, capsys
):
    _apply_tester_posture(monkeypatch)
    db = _FakeAuthDb()
    email = "guest@example.com"
    db.seed_user(email=email, role="guest", password="seed-only-test-password")
    new_password = "test-only-rotated-password"
    code, captured = _run_main(
        monkeypatch,
        capsys,
        argv=["--email", email],
        db=db,
        getpass_responses=[new_password, new_password],
        raises=False,
    )
    assert code == 0
    assert db.commit_count == 1
    with db.get_session() as session:
        user = session.get(User, email)
        assert user is not None
        assert user.role == "guest"
        assert verify_password(new_password, user.password_hash) is True
        assert verify_password("seed-only-test-password", user.password_hash) is False
    assert "preserved" in captured.out


def test_main_resets_password_and_changes_role_only_when_role_explicit(
    monkeypatch, capsys
):
    _apply_tester_posture(monkeypatch)
    db = _FakeAuthDb()
    email = "switch@example.com"
    db.seed_user(email=email, role="guest", password="seed-only-test-password")
    new_password = "test-only-switched-password"
    code, captured = _run_main(
        monkeypatch,
        capsys,
        argv=["--email", email, "--role", "admin"],
        db=db,
        getpass_responses=[new_password, new_password],
        raises=False,
    )
    assert code == 0
    assert db.commit_count == 1
    with db.get_session() as session:
        user = session.get(User, email)
        assert user is not None
        assert user.role == "admin"
        assert verify_password(new_password, user.password_hash) is True
    assert "role set to admin" in captured.out


def test_resolve_role_rejects_existing_noncanonical_role():
    # The users CHECK constraint prevents noncanonical roles from persisting
    # normally; this guard is defense in depth (e.g. legacy/manual edits).
    with pytest.raises(ValueError) as exc:
        tap.resolve_role("superuser", None)
    assert "noncanonical role" in str(exc.value)
    with pytest.raises(ValueError):
        tap.resolve_role("superuser", "admin")


# --------------------------------------------------------------------------
# Hashing + non-disclosure
# --------------------------------------------------------------------------


def test_stored_password_is_hashed_not_plaintext(monkeypatch, capsys):
    _apply_tester_posture(monkeypatch)
    db = _FakeAuthDb()
    email = "hashed@example.com"
    password = "test-only-plaintext-guard-password"
    _run_main(
        monkeypatch,
        capsys,
        argv=["--email", email, "--role", "guest"],
        db=db,
        getpass_responses=[password, password],
        raises=False,
    )
    with db.get_session() as session:
        user = session.get(User, email)
        assert user is not None
        assert user.password_hash != password
        assert "$" in user.password_hash
        assert password not in user.password_hash


def test_success_output_never_discloses_password_or_hash(monkeypatch, capsys):
    _apply_tester_posture(monkeypatch)
    db = _FakeAuthDb()
    email = "secret@example.com"
    password = "never-print-this-test-only-value"
    _run_main(
        monkeypatch,
        capsys,
        argv=["--email", email, "--role", "guest"],
        db=db,
        getpass_responses=[password, password],
        raises=False,
    )
    with db.get_session() as session:
        user = session.get(User, email)
        assert user is not None
        stored_hash = user.password_hash
    combined = capsys.readouterr().out
    assert password not in combined
    assert stored_hash not in combined


def test_success_output_does_not_print_database_dsn(monkeypatch, capsys):
    _apply_tester_posture(monkeypatch)
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://dsn-marker-user:dsn-marker-pass@dsn-marker-host/dsn-marker-db",
    )
    db = _FakeAuthDb()
    email = "quiet@example.com"
    _run_main(
        monkeypatch,
        capsys,
        argv=["--email", email, "--role", "guest"],
        db=db,
        getpass_responses=["test-only-password", "test-only-password"],
        raises=False,
    )
    combined = capsys.readouterr().out + capsys.readouterr().err
    assert "dsn-marker" not in combined


# --------------------------------------------------------------------------
# Mutation discipline
# --------------------------------------------------------------------------


def test_no_mutation_or_commit_when_password_validation_fails(
    monkeypatch, capsys
):
    _apply_tester_posture(monkeypatch)
    db = _FakeAuthDb()
    code, _captured = _run_main(
        monkeypatch,
        capsys,
        argv=["--email", "fresh@example.com", "--role", "admin"],
        db=db,
        getpass_responses=["", ""],
    )
    assert code == 2
    assert db.commit_count == 0
    with db.get_session() as session:
        assert session.get(User, "fresh@example.com") is None


def test_successful_mutation_commits_exactly_once(monkeypatch, capsys):
    _apply_tester_posture(monkeypatch)
    db = _FakeAuthDb()
    email = "once@example.com"
    _run_main(
        monkeypatch,
        capsys,
        argv=["--email", email, "--role", "admin"],
        db=db,
        getpass_responses=["test-only-password-1", "test-only-password-1"],
        raises=False,
    )
    assert db.commit_count == 1
    _run_main(
        monkeypatch,
        capsys,
        argv=["--email", email],
        db=db,
        getpass_responses=["test-only-password-2", "test-only-password-2"],
        raises=False,
    )
    assert db.commit_count == 1


# --------------------------------------------------------------------------
# Database unavailability (no DSN leak)
# --------------------------------------------------------------------------


def test_main_fails_when_database_unavailable_without_printing_dsn(
    monkeypatch, capsys
):
    _apply_tester_posture(monkeypatch)
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://hidden-dsn-user:hidden-dsn-pass@hidden-host/hidden-db",
    )
    monkeypatch.setattr(tap.sys, "stdin", _FakeStdin(True))
    monkeypatch.setattr(
        tap.sys,
        "argv",
        [
            "tester_account_provision",
            "--email",
            "admin@example.com",
            "--role",
            "admin",
        ],
    )
    monkeypatch.setattr(tap, "load_guardian_db_from_env", lambda: None)
    with pytest.raises(SystemExit) as exc:
        tap.main()
    assert exc.value.code == 2
    captured = capsys.readouterr()
    combined = captured.out + captured.err
    assert "authentication database unavailable" in combined
    assert "hidden-dsn" not in combined


def test_main_fails_when_loader_raises_without_printing_dsn(monkeypatch, capsys):
    _apply_tester_posture(monkeypatch)
    monkeypatch.setattr(tap.sys, "stdin", _FakeStdin(True))
    monkeypatch.setattr(
        tap.sys,
        "argv",
        [
            "tester_account_provision",
            "--email",
            "admin@example.com",
            "--role",
            "admin",
        ],
    )

    def _raise():
        raise RuntimeError("postgresql://leaked-dsn-marker@leaked-host/db")

    monkeypatch.setattr(tap, "load_guardian_db_from_env", _raise)
    with pytest.raises(SystemExit) as exc:
        tap.main()
    assert exc.value.code == 2
    captured = capsys.readouterr()
    combined = captured.out + captured.err
    assert "authentication database unavailable" in combined
    assert "leaked-dsn-marker" not in combined


# --------------------------------------------------------------------------
# --help works without runtime configuration or database access
# --------------------------------------------------------------------------


def test_help_succeeds_without_runtime_or_database(monkeypatch, capsys):
    monkeypatch.delenv("GUARDIAN_AUTH_MODE", raising=False)
    monkeypatch.delenv("GUARDIAN_EXPOSURE_MODE", raising=False)
    monkeypatch.delenv("CODEXIFY_SUPPORTED_PROFILE", raising=False)
    monkeypatch.setattr(tap.sys, "argv", ["tester_account_provision", "--help"])
    with pytest.raises(SystemExit) as exc:
        tap.main()
    assert exc.value.code == 0
    captured = capsys.readouterr()
    assert "--email" in captured.out
    assert "--role" in captured.out
