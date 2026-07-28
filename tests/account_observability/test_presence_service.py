from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.account_observability.presence import (
    SubjectResolutionError,
    end_account_presence,
    record_heartbeat,
)
from guardian.db.models import (
    AccountObservabilityAccountMetadata,
    AccountObservabilityGuestIdentity,
    AccountObservabilityInviteLink,
    AccountObservabilityPresenceSession,
    Base,
    User,
)


@pytest.fixture()
def db_session() -> Session:
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
    factory = sessionmaker(bind=engine, autoflush=False, future=True)
    with factory() as session:
        yield session
    Base.metadata.drop_all(engine, tables=list(reversed(tables)))
    engine.dispose()


def _user(user_id: str) -> User:
    return User(
        id=user_id,
        username=user_id,
        password_hash="test-hash",
        role="guest",
    )


def test_account_heartbeat_creates_and_coalesces_presence(
    db_session: Session,
) -> None:
    started = datetime(2026, 7, 28, 12, 0, tzinfo=timezone.utc)
    db_session.add(_user("account-1"))
    db_session.flush()
    db_session.add(
        AccountObservabilityAccountMetadata(
            user_id="account-1", registered_at=started
        )
    )
    db_session.commit()

    first = record_heartbeat(db_session, user_id="account-1", now=started)
    second = record_heartbeat(
        db_session,
        user_id="account-1",
        now=started + timedelta(seconds=60),
    )
    db_session.commit()

    rows = db_session.scalars(select(AccountObservabilityPresenceSession)).all()
    metadata = db_session.get(AccountObservabilityAccountMetadata, "account-1")
    assert first.is_new is True
    assert second.is_new is False
    assert second.presence_session_id == first.presence_session_id
    assert len(rows) == 1
    assert rows[0].last_seen_at == (started + timedelta(seconds=60)).replace(
        tzinfo=None
    )
    assert metadata is not None
    assert metadata.last_seen_at == (started + timedelta(seconds=60)).replace(
        tzinfo=None
    )


def test_guest_heartbeat_requires_live_server_issued_identity(
    db_session: Session,
) -> None:
    started = datetime(2026, 7, 28, 12, 0, tzinfo=timezone.utc)
    db_session.add(
        AccountObservabilityGuestIdentity(id="guest-1", created_at=started)
    )
    db_session.commit()

    result = record_heartbeat(db_session, guest_id="guest-1", now=started)
    assert result.subject_kind == "guest"

    db_session.get(
        AccountObservabilityGuestIdentity, "guest-1"
    ).deleted_at = started
    db_session.flush()
    with pytest.raises(SubjectResolutionError, match="deleted"):
        record_heartbeat(
            db_session,
            guest_id="guest-1",
            now=started + timedelta(minutes=1),
        )


@pytest.mark.parametrize(
    "kwargs",
    [{}, {"user_id": "account-1", "guest_id": "guest-1"}],
)
def test_heartbeat_requires_exactly_one_subject(
    db_session: Session, kwargs: dict[str, str]
) -> None:
    with pytest.raises(SubjectResolutionError, match="exactly one"):
        record_heartbeat(db_session, **kwargs)


def test_idle_heartbeat_ends_old_lease_and_starts_new_one(
    db_session: Session,
) -> None:
    started = datetime(2026, 7, 28, 12, 0, tzinfo=timezone.utc)
    db_session.add(_user("account-1"))
    db_session.commit()
    first = record_heartbeat(db_session, user_id="account-1", now=started)
    second = record_heartbeat(
        db_session,
        user_id="account-1",
        now=started + timedelta(minutes=31),
    )
    db_session.commit()

    rows = db_session.scalars(
        select(AccountObservabilityPresenceSession).order_by(
            AccountObservabilityPresenceSession.started_at
        )
    ).all()
    assert first.presence_session_id != second.presence_session_id
    assert rows[0].ended_at == (started + timedelta(minutes=31)).replace(
        tzinfo=None
    )
    assert rows[1].ended_at is None


def test_logout_hook_ends_open_account_leases(db_session: Session) -> None:
    started = datetime(2026, 7, 28, 12, 0, tzinfo=timezone.utc)
    db_session.add(_user("account-1"))
    db_session.commit()
    record_heartbeat(db_session, user_id="account-1", now=started)
    ended = end_account_presence(
        db_session, "account-1", now=started + timedelta(seconds=1)
    )
    db_session.commit()
    row = db_session.scalar(select(AccountObservabilityPresenceSession))
    assert ended == 1
    assert row is not None
    assert row.ended_at == (started + timedelta(seconds=1)).replace(tzinfo=None)
