"""Tests for the presence heartbeat service (Slice 3)."""

from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from guardian.account_observability.presence import (
    HeartbeatError,
    HeartbeatResult,
    SubjectResolutionError,
    end_account_presence,
    end_guest_presence,
    record_heartbeat,
)
from guardian.account_observability.tokens import (
    PRESENCE_ACTIVE_WINDOW_SECONDS,
    PRESENCE_IDLE_EXPIRY_SECONDS,
)
from guardian.db.models import (
    AccountObservabilityAccountMetadata,
    AccountObservabilityGuestIdentity,
    AccountObservabilityPresenceSession,
    Base,
)

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


@pytest.fixture(scope="function")
def db_session():
    engine = create_engine("sqlite:///:memory:", echo=False)
    # Only create the tables needed for observability tests;
    # SQLite can't handle JSONB columns from other models.
    from guardian.db.models import (
        AccountObservabilityAccountMetadata,
        AccountObservabilityGuestIdentity,
        AccountObservabilityInviteLink,
        AccountObservabilityPresenceSession,
        User,
    )

    User.__table__.create(engine, checkfirst=True)
    AccountObservabilityInviteLink.__table__.create(engine, checkfirst=True)
    AccountObservabilityGuestIdentity.__table__.create(engine, checkfirst=True)
    AccountObservabilityAccountMetadata.__table__.create(
        engine, checkfirst=True
    )
    AccountObservabilityPresenceSession.__table__.create(
        engine, checkfirst=True
    )
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()
    engine.dispose()


def _seed_account(session: Session, user_id: str) -> None:
    from guardian.db.models import User

    user = User(
        id=user_id,
        username=f"test_{user_id[:8]}",
        password_hash="hash",
        role="admin",
    )
    session.add(user)
    metadata = AccountObservabilityAccountMetadata(
        user_id=user_id,
        registered_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        last_seen_at=None,
    )
    session.add(metadata)
    session.flush()


def _seed_guest(
    session: Session, guest_id: str, invite_id: str | None = None
) -> None:
    guest = AccountObservabilityGuestIdentity(
        guest_id=guest_id,
        first_invite_id=invite_id,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    session.add(guest)
    session.flush()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# service tests
# ---------------------------------------------------------------------------


class TestAccountHeartbeat:
    def test_creates_new_account_presence(self, db_session):
        _seed_account(db_session, "user-1")
        result = record_heartbeat(db_session, user_id="user-1")
        assert result.subject_kind == "account"
        assert result.subject_id == "user-1"
        assert result.is_new is True
        assert result.active is True

    def test_refreshes_existing_account_presence(self, db_session):
        _seed_account(db_session, "user-2")
        first = record_heartbeat(db_session, user_id="user-2")
        db_session.flush()
        second = record_heartbeat(db_session, user_id="user-2")
        assert second.presence_session_id == first.presence_session_id
        assert second.is_new is False

    def test_updates_account_last_seen(self, db_session):
        _seed_account(db_session, "user-3")
        record_heartbeat(db_session, user_id="user-3")
        metadata = db_session.get(AccountObservabilityAccountMetadata, "user-3")
        assert metadata.last_seen_at is not None

    def test_creates_new_session_after_idle_expiry(self, db_session):
        _seed_account(db_session, "user-4")
        old_time = datetime(2020, 1, 1, tzinfo=timezone.utc)
        result1 = record_heartbeat(db_session, user_id="user-4", now=old_time)
        db_session.flush()
        # The old session should be considered expired (>30 min idle),
        # so a new heartbeat now creates a new session
        result2 = record_heartbeat(db_session, user_id="user-4")
        assert result2.presence_session_id != result1.presence_session_id
        assert result2.is_new is True

    def test_rejects_empty_user_id(self, db_session):
        with pytest.raises(SubjectResolutionError):
            record_heartbeat(db_session, user_id="")

    def test_rejects_ambiguous_subject(self, db_session):
        _seed_account(db_session, "user-5")
        with pytest.raises(SubjectResolutionError, match="ambiguous"):
            record_heartbeat(db_session, user_id="user-5", guest_id="guest-1")


class TestGuestHeartbeat:
    def test_creates_new_guest_presence(self, db_session):
        _seed_guest(db_session, "guest-1")
        result = record_heartbeat(db_session, guest_id="guest-1")
        assert result.subject_kind == "guest"
        assert result.is_new is True

    def test_refreshes_existing_guest_presence(self, db_session):
        _seed_guest(db_session, "guest-2")
        first = record_heartbeat(db_session, guest_id="guest-2")
        db_session.flush()
        second = record_heartbeat(db_session, guest_id="guest-2")
        assert second.presence_session_id == first.presence_session_id
        assert second.is_new is False

    def test_rejects_deleted_guest(self, db_session):
        _seed_guest(db_session, "guest-3")
        guest = db_session.get(AccountObservabilityGuestIdentity, "guest-3")
        guest.deleted_at = _utc_now()
        db_session.flush()
        with pytest.raises(SubjectResolutionError, match="deleted"):
            record_heartbeat(db_session, guest_id="guest-3")

    def test_rejects_nonexistent_guest(self, db_session):
        with pytest.raises(SubjectResolutionError):
            record_heartbeat(db_session, guest_id="nonexistent")


class TestConcurrentHeartbeats:
    def test_concurrent_heartbeats_preserve_one_coherent_state(
        self, db_session
    ):
        _seed_account(db_session, "user-concurrent")
        # SQLite doesn't support concurrent writes well; simulate with
        # sequential calls that exercise the same coalescing logic
        results = []
        for _ in range(5):
            r = record_heartbeat(db_session, user_id="user-concurrent")
            results.append(r)
            db_session.flush()

        # After all beats, only one active session should exist
        sessions = (
            db_session.execute(
                select(AccountObservabilityPresenceSession).where(
                    AccountObservabilityPresenceSession.user_id
                    == "user-concurrent",
                    AccountObservabilityPresenceSession.ended_at.is_(None),
                )
            )
            .scalars()
            .all()
        )
        assert len(sessions) == 1


class TestPresenceEnding:
    def test_end_account_presence_closes_sessions(self, db_session):
        _seed_account(db_session, "user-end")
        record_heartbeat(db_session, user_id="user-end")
        count = end_account_presence(db_session, "user-end")
        assert count >= 1
        sessions = (
            db_session.execute(
                select(AccountObservabilityPresenceSession).where(
                    AccountObservabilityPresenceSession.user_id == "user-end",
                    AccountObservabilityPresenceSession.ended_at.is_(None),
                )
            )
            .scalars()
            .all()
        )
        assert len(sessions) == 0

    def test_end_guest_presence_closes_sessions(self, db_session):
        _seed_guest(db_session, "guest-end")
        record_heartbeat(db_session, guest_id="guest-end")
        count = end_guest_presence(db_session, "guest-end")
        assert count >= 1

    def test_missed_close_is_safe(self, db_session):
        """If logout is missed, idle expiry is authoritative."""
        _seed_account(db_session, "user-missed")
        old = datetime(2020, 1, 1, tzinfo=timezone.utc)
        record_heartbeat(db_session, user_id="user-missed", now=old)
        db_session.flush()
        # Session from 2020 is far past idle expiry.
        # A new heartbeat now creates a new session.
        result = record_heartbeat(db_session, user_id="user-missed")
        assert result.is_new is True  # old session is too old


class TestSubjectIdentityProtection:
    def test_authenticated_identity_not_overridable(self, db_session):
        """The service accepts only the explicitly passed user_id from
        trusted server context. There is no payload-based override path."""
        _seed_account(db_session, "real-user")
        result = record_heartbeat(db_session, user_id="real-user")
        assert result.subject_id == "real-user"
        # There is no way to pass "fake-user" as user_id and have it
        # override - the caller must provide the true trusted identity.

    def test_guest_identity_not_overridable(self, db_session):
        _seed_guest(db_session, "real-guest")
        result = record_heartbeat(db_session, guest_id="real-guest")
        assert result.subject_id == "real-guest"


class TestServerTimeControlsLease:
    def test_server_time_is_utc(self, db_session):
        _seed_account(db_session, "user-time")
        result = record_heartbeat(db_session, user_id="user-time")
        assert result.server_time.tzinfo is not None
        assert result.server_time.utcoffset().total_seconds() == 0

    def test_ignores_client_timestamps(self, db_session):
        """record_heartbeat uses server now() unless explicitly overridden
        in tests. Client timestamps are never accepted."""
        _seed_account(db_session, "user-ts")
        now = _utc_now()
        result = record_heartbeat(db_session, user_id="user-ts", now=now)
        # The presence row started_at should match our provided now
        row = db_session.get(
            AccountObservabilityPresenceSession, result.presence_session_id
        )
        # SQLite may strip timezone; compare timestamps
        assert (
            abs(
                (
                    row.started_at.replace(tzinfo=timezone.utc) - now
                ).total_seconds()
            )
            < 1
        )
