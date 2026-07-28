from __future__ import annotations

from contextlib import nullcontext
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.account_observability.retention import run_cleanup
from guardian.cron.executor import execute_cron_job
from guardian.db.models import (
    AccountObservabilityAccountMetadata,
    AccountObservabilityGuestIdentity,
    AccountObservabilityInviteLink,
    AccountObservabilityPresenceSession,
    Base,
    User,
)


def _session() -> tuple[Session, object]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _foreign_keys(dbapi_connection, _record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    tables = [
        User.__table__,
        AccountObservabilityInviteLink.__table__,
        AccountObservabilityGuestIdentity.__table__,
        AccountObservabilityAccountMetadata.__table__,
        AccountObservabilityPresenceSession.__table__,
    ]
    Base.metadata.create_all(engine, tables=tables)
    return sessionmaker(bind=engine, autoflush=False, future=True)(), engine


def test_cleanup_expires_idle_rows_deletes_old_presence_and_unconverted_guests() -> (
    None
):
    session, engine = _session()
    try:
        now = datetime(2026, 7, 28, 12, 0, tzinfo=timezone.utc)
        old = now - timedelta(days=31)
        session.add(
            User(id="account-1", username="account-1", password_hash="h")
        )
        session.flush()
        session.add(
            AccountObservabilityGuestIdentity(
                id="guest-old", created_at=now - timedelta(days=91)
            )
        )
        session.add(
            AccountObservabilityPresenceSession(
                id="presence-old",
                user_id="account-1",
                started_at=old,
                last_seen_at=old,
                created_at=old,
                updated_at=old,
            )
        )
        session.commit()

        receipt = run_cleanup(session, now=now)
        session.commit()

        assert receipt.expired_session_count == 1
        assert receipt.deleted_presence_count == 1
        assert receipt.deleted_guest_count == 1
        assert (
            session.get(AccountObservabilityPresenceSession, "presence-old")
            is None
        )
        assert (
            session.get(AccountObservabilityGuestIdentity, "guest-old") is None
        )
    finally:
        session.close()
        engine.dispose()


def test_cleanup_preserves_converted_guest_lineage_and_account_attribution() -> (
    None
):
    session, engine = _session()
    try:
        now = datetime(2026, 7, 28, 12, 0, tzinfo=timezone.utc)
        guest = AccountObservabilityGuestIdentity(
            id="guest-converted",
            created_at=now - timedelta(days=91),
            converted_at=now - timedelta(days=90),
        )
        session.add_all(
            [
                User(id="account-1", username="account-1", password_hash="h"),
                guest,
            ]
        )
        session.flush()
        from guardian.db.models import AccountObservabilityInviteLink

        session.add(
            AccountObservabilityInviteLink(
                id="invite-1",
                token_hash="hash-invite-1",
                name="Test invite",
                created_by_user_id="account-1",
            )
        )
        session.flush()
        session.add(
            AccountObservabilityAccountMetadata(
                user_id="account-1",
                registered_at=now - timedelta(days=90),
                acquisition_invite_id="invite-1",
                prior_guest_id=guest.id,
                attribution_method="first_party_first_touch",
                attribution_confidence="verified",
            )
        )
        session.commit()

        receipt = run_cleanup(session, now=now)
        session.commit()

        assert receipt.deleted_guest_count == 0
        assert (
            session.get(AccountObservabilityGuestIdentity, guest.id) is not None
        )
        assert (
            session.get(
                AccountObservabilityAccountMetadata, "account-1"
            ).prior_guest_id
            == guest.id
        )
    finally:
        session.close()
        engine.dispose()


def test_cleanup_is_registered_with_existing_cron_executor() -> None:
    session, engine = _session()
    try:

        class _Database:
            def get_session(self):
                return nullcontext(session)

        result = execute_cron_job(
            job_type="account_observability_retention",
            payload=None,
            db=_Database(),
        )
        assert result["ok"] is True
        assert result["job_type"] == "account_observability_retention"
        assert result["result"]["expired_session_count"] == 0
    finally:
        session.close()
        engine.dispose()
