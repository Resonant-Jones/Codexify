"""Tests for the deterministic retention cleanup service (Slice 3)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from guardian.account_observability.retention import CleanupReceipt, run_cleanup
from guardian.account_observability.tokens import (
    PRESENCE_IDLE_EXPIRY_SECONDS,
    PRESENCE_ROW_RETENTION_DAYS,
)
from guardian.db.models import (
    AccountObservabilityAccountMetadata,
    AccountObservabilityGuestIdentity,
    AccountObservabilityInviteLink,
    AccountObservabilityPresenceSession,
    User,
)


@pytest.fixture(scope="function")
def db_session():
    engine = create_engine("sqlite:///:memory:", echo=False)
    # Enable FK constraints for SQLite
    from sqlalchemy import event

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    User.__table__.create(engine, checkfirst=True)
    AccountObservabilityInviteLink.__table__.create(engine, checkfirst=True)
    AccountObservabilityGuestIdentity.__table__.create(engine, checkfirst=True)
    AccountObservabilityAccountMetadata.__table__.create(engine, checkfirst=True)
    AccountObservabilityPresenceSession.__table__.create(engine, checkfirst=True)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()
    engine.dispose()


def _seed_user(session, user_id: str) -> None:
    user = User(id=user_id, username=f"test_{user_id[:8]}", password_hash="hash", role="admin")
    session.add(user)
    session.flush()


def _seed_presence(session, presence_id: str, user_id: str | None, guest_id: str | None,
                   started_at: datetime, last_seen_at: datetime, ended_at: datetime | None = None) -> None:
    row = AccountObservabilityPresenceSession(
        presence_session_id=presence_id,
        user_id=user_id,
        guest_id=guest_id,
        invite_id=None,
        started_at=started_at,
        last_seen_at=last_seen_at,
        ended_at=ended_at,
        created_at=started_at,  # Explicit: SQLite may not run server_default
    )
    session.add(row)
    session.flush()


def _seed_guest(session, guest_id: str, created_at: datetime, converted_at: datetime | None = None) -> None:
    guest = AccountObservabilityGuestIdentity(
        guest_id=guest_id,
        first_invite_id=None,
        created_at=created_at,
        converted_at=converted_at,
    )
    session.add(guest)
    session.flush()


def _seed_account_metadata(session, user_id: str, prior_guest_id: str | None = None) -> None:
    meta = AccountObservabilityAccountMetadata(
        user_id=user_id,
        registered_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        prior_guest_id=prior_guest_id,
    )
    session.add(meta)
    session.flush()


class TestIdleSessionExpiry:
    def test_idle_sessions_are_ended(self, db_session):
        now = datetime(2026, 7, 25, 12, 0, 0, tzinfo=timezone.utc)
        old_active = datetime(2026, 7, 25, 11, 0, 0, tzinfo=timezone.utc)
        recent_active = datetime(2026, 7, 25, 11, 59, 0, tzinfo=timezone.utc)

        _seed_user(db_session, "user-idle")
        _seed_presence(db_session, "p-old", "user-idle", None, old_active, old_active)
        _seed_presence(db_session, "p-recent", "user-idle", None, recent_active, recent_active)

        receipt = run_cleanup(db_session, now=now)
        assert receipt.expired_session_count >= 1

        # Old session should be ended
        old_row = db_session.get(AccountObservabilityPresenceSession, "p-old")
        assert old_row.ended_at is not None

    def test_recent_sessions_are_untouched(self, db_session):
        now = datetime(2026, 7, 25, 12, 0, 0, tzinfo=timezone.utc)
        recent = datetime(2026, 7, 25, 11, 59, 30, tzinfo=timezone.utc)

        _seed_user(db_session, "user-recent")
        _seed_presence(db_session, "p-recent", "user-recent", None, recent, recent)

        receipt = run_cleanup(db_session, now=now)
        row = db_session.get(AccountObservabilityPresenceSession, "p-recent")
        assert row.ended_at is None  # still active


class TestPresenceRowDeletion:
    def test_rows_older_than_30_days_are_deleted(self, db_session):
        now = datetime(2026, 7, 25, 12, 0, 0, tzinfo=timezone.utc)
        very_old = datetime(2026, 6, 1, tzinfo=timezone.utc)

        _seed_user(db_session, "user-old")
        _seed_presence(db_session, "p-old-del", "user-old", None, very_old, very_old, ended_at=very_old)

        receipt = run_cleanup(db_session, now=now)
        assert receipt.deleted_presence_count >= 1

        row = db_session.get(AccountObservabilityPresenceSession, "p-old-del")
        assert row is None

    def test_rows_newer_than_30_days_remain(self, db_session):
        now = datetime(2026, 7, 25, 12, 0, 0, tzinfo=timezone.utc)
        recent = datetime(2026, 7, 20, tzinfo=timezone.utc)

        _seed_user(db_session, "user-new")
        _seed_presence(db_session, "p-new", "user-new", None, recent, recent)

        receipt = run_cleanup(db_session, now=now)
        row = db_session.get(AccountObservabilityPresenceSession, "p-new")
        assert row is not None


class TestAccountDeletion:
    def test_account_deletion_cascades_to_presence(self, db_session):
        """CASCADE FK ensures deleting a user removes their presence rows."""
        _seed_user(db_session, "user-cascade")
        _seed_presence(
            db_session, "p-cascade", "user-cascade", None,
            datetime(2026, 7, 1, tzinfo=timezone.utc),
            datetime(2026, 7, 1, tzinfo=timezone.utc),
        )

        # Delete the user
        user = db_session.get(User, "user-cascade")
        db_session.delete(user)
        db_session.flush()

        # Presence should be gone (CASCADE)
        row = db_session.get(AccountObservabilityPresenceSession, "p-cascade")
        assert row is None


class TestGuestLineageCleanup:
    def test_eligible_old_guest_is_deleted(self, db_session):
        now = datetime(2026, 7, 25, 12, 0, 0, tzinfo=timezone.utc)
        old_created = datetime(2026, 1, 1, tzinfo=timezone.utc)

        _seed_guest(db_session, "guest-old", old_created)

        receipt = run_cleanup(db_session, now=now)
        assert receipt.deleted_guest_count is not None
        assert receipt.deleted_guest_count >= 1

        guest = db_session.get(AccountObservabilityGuestIdentity, "guest-old")
        assert guest.deleted_at is not None

    def test_converted_guest_with_metadata_is_deferred(self, db_session):
        now = datetime(2026, 7, 25, 12, 0, 0, tzinfo=timezone.utc)
        old_created = datetime(2026, 1, 1, tzinfo=timezone.utc)

        _seed_user(db_session, "user-guest")
        _seed_guest(db_session, "guest-converted", old_created, converted_at=old_created)
        _seed_account_metadata(db_session, "user-guest", prior_guest_id="guest-converted")

        receipt = run_cleanup(db_session, now=now)
        assert receipt.deferred_guest_count is not None
        assert receipt.deferred_guest_count >= 1
        assert receipt.deferred_guest_reason is not None

        # Guest should NOT be deleted
        guest = db_session.get(AccountObservabilityGuestIdentity, "guest-converted")
        assert guest.deleted_at is None

    def test_invite_definitions_survive_guest_cleanup(self, db_session):
        """Guest cleanup must never delete invite definitions."""
        now = datetime(2026, 7, 25, 12, 0, 0, tzinfo=timezone.utc)
        old_created = datetime(2026, 1, 1, tzinfo=timezone.utc)

        # Create the user first (FK constraint)
        _seed_user(db_session, "user-1")
        # Create an invite
        invite = AccountObservabilityInviteLink(
            invite_id="inv-1",
            token_hash="abc123",
            name="test invite",
            created_by_user_id="user-1",
            status="active",
        )
        db_session.add(invite)
        _seed_guest(db_session, "guest-inv", old_created)

        receipt = run_cleanup(db_session, now=now)
        # Invite should still exist
        invite_row = db_session.get(AccountObservabilityInviteLink, "inv-1")
        assert invite_row is not None


class TestCleanupIdempotency:
    def test_repeated_cleanup_is_idempotent(self, db_session):
        now = datetime(2026, 7, 25, 12, 0, 0, tzinfo=timezone.utc)
        old_time = datetime(2026, 6, 1, tzinfo=timezone.utc)

        _seed_user(db_session, "user-idem")
        _seed_presence(db_session, "p-idem", "user-idem", None, old_time, old_time, ended_at=old_time)

        first = run_cleanup(db_session, now=now)
        second = run_cleanup(db_session, now=now)

        # Second run should find nothing new to delete
        assert second.deleted_presence_count == 0
        assert second.expired_session_count == 0


class TestCleanupReceipt:
    def test_receipt_has_accurate_cutoffs(self, db_session):
        now = datetime(2026, 7, 25, 12, 0, 0, tzinfo=timezone.utc)
        receipt = run_cleanup(db_session, now=now, dry_run=True)

        assert receipt.execution_timestamp == now
        expected_presence = datetime.fromtimestamp(
            now.timestamp() - (PRESENCE_ROW_RETENTION_DAYS * 86400),
            tz=timezone.utc,
        )
        assert abs((receipt.cutoff_presence_30d - expected_presence).total_seconds()) < 1
        assert receipt.dry_run is True

    def test_dry_run_does_not_mutate(self, db_session):
        now = datetime(2026, 7, 25, 12, 0, 0, tzinfo=timezone.utc)
        old_time = datetime(2026, 6, 1, tzinfo=timezone.utc)

        _seed_user(db_session, "user-dry")
        _seed_presence(db_session, "p-dry", "user-dry", None, old_time, old_time)

        receipt = run_cleanup(db_session, now=now, dry_run=True)
        assert receipt.dry_run is True

        # Row should still exist
        row = db_session.get(AccountObservabilityPresenceSession, "p-dry")
        assert row is not None
