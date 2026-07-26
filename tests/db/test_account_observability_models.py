"""Focused SQLAlchemy tests for dormant account-observability persistence."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, event, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.db.models import (
    AccountObservabilityAccountMetadata,
    AccountObservabilityGuestIdentity,
    AccountObservabilityInviteLink,
    AccountObservabilityPresenceSession,
    Base,
    User,
)


TABLES = [
    User.__table__,
    AccountObservabilityInviteLink.__table__,
    AccountObservabilityGuestIdentity.__table__,
    AccountObservabilityAccountMetadata.__table__,
    AccountObservabilityPresenceSession.__table__,
]

PROHIBITED_COLUMN_NAMES = {
    "raw_ip",
    "hashed_ip",
    "ip_address",
    "user_agent",
    "fingerprint",
    "page_path",
    "route_path",
    "message_id",
    "thread_id",
    "project_id",
    "prompt",
    "response_content",
    "referrer_url",
    "latitude",
    "longitude",
    "postal_code",
    "city",
    "asn",
    "isp",
}


@pytest.fixture()
def db_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine, tables=TABLES)
    factory = sessionmaker(bind=engine, autoflush=False, future=True)
    with factory() as session:
        yield session
    Base.metadata.drop_all(bind=engine, tables=list(reversed(TABLES)))
    engine.dispose()


def _timestamp_pair() -> tuple[datetime, datetime]:
    started = datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc)
    return started, started + timedelta(minutes=1)


def _user(user_id: str) -> User:
    return User(
        id=user_id,
        username=user_id,
        password_hash="test-password-hash",
        role="guest",
    )


def _invite(operator_id: str, invite_id: str = "invite-1") -> AccountObservabilityInviteLink:
    return AccountObservabilityInviteLink(
        id=invite_id,
        token_hash=f"hash-{invite_id}",
        name="Test invite",
        created_by_user_id=operator_id,
        status="active",
    )


def test_all_four_tables_are_registered_in_canonical_metadata() -> None:
    table_names = set(Base.metadata.tables)
    assert {
        "account_observability_invite_links",
        "account_observability_guest_identities",
        "account_observability_account_metadata",
        "account_observability_presence_sessions",
    } <= table_names


def test_account_metadata_is_keyed_only_to_canonical_user_identity() -> None:
    table = AccountObservabilityAccountMetadata.__table__
    assert [column.name for column in table.primary_key.columns] == ["user_id"]
    assert {
        (foreign_key.parent.name, foreign_key.target_fullname)
        for foreign_key in table.foreign_keys
    } >= {("user_id", "users.id")}
    assert not {
        "username",
        "email",
        "display_name",
        "password_hash",
        "role",
        "permissions",
        "auth_token",
        "session_token",
    } & set(table.columns)


def test_invite_token_hash_is_unique_and_status_is_constrained(db_session: Session) -> None:
    db_session.add(_user("operator"))
    db_session.flush()
    db_session.add(_invite("operator", "invite-1"))
    db_session.commit()

    duplicate = _invite("operator", "invite-2")
    duplicate.token_hash = "hash-invite-1"
    db_session.add(duplicate)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    invalid = _invite("operator", "invite-invalid")
    invalid.status = "expired"
    db_session.add(invalid)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


@pytest.mark.parametrize(
    "user_id,guest_id",
    [("account-1", "guest-1"), (None, None)],
)
def test_presence_requires_exactly_one_subject(
    db_session: Session, user_id: str | None, guest_id: str | None
) -> None:
    started, last_seen = _timestamp_pair()
    db_session.add(_user("account-1"))
    db_session.add(
        AccountObservabilityPresenceSession(
            id=f"invalid-{user_id or 'neither'}",
            user_id=user_id,
            guest_id=guest_id,
            started_at=started,
            last_seen_at=last_seen,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_valid_account_and_guest_presence_rows_succeed(db_session: Session) -> None:
    started, last_seen = _timestamp_pair()
    db_session.add_all([_user("account-1"), _user("operator")])
    db_session.flush()
    db_session.add(_invite("operator"))
    db_session.flush()
    db_session.add(
        AccountObservabilityGuestIdentity(
            id="guest-1", first_invite_id="invite-1"
        )
    )
    db_session.flush()
    db_session.add_all(
        [
            AccountObservabilityPresenceSession(
                id="account-presence-1",
                user_id="account-1",
                started_at=started,
                last_seen_at=last_seen,
                country_code="US",
                region_code="US-NY",
            ),
            AccountObservabilityPresenceSession(
                id="guest-presence-1",
                guest_id="guest-1",
                invite_id="invite-1",
                started_at=started,
                last_seen_at=last_seen,
            ),
        ]
    )
    db_session.commit()
    assert db_session.scalar(select(AccountObservabilityPresenceSession).where(
        AccountObservabilityPresenceSession.id == "account-presence-1"
    )) is not None


@pytest.mark.parametrize(
    "field, value",
    [
        ("last_seen_at", datetime(2026, 7, 24, 11, 59, tzinfo=timezone.utc)),
        ("ended_at", datetime(2026, 7, 24, 11, 59, tzinfo=timezone.utc)),
    ],
)
def test_invalid_presence_timestamp_ordering_is_rejected(
    db_session: Session, field: str, value: datetime
) -> None:
    started, last_seen = _timestamp_pair()
    values = {
        "id": f"invalid-{field}",
        "user_id": "account-1",
        "started_at": started,
        "last_seen_at": last_seen,
    }
    values[field] = value
    db_session.add(_user("account-1"))
    db_session.add(AccountObservabilityPresenceSession(**values))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_region_requires_country(db_session: Session) -> None:
    started, last_seen = _timestamp_pair()
    db_session.add(_user("account-1"))
    db_session.add(
        AccountObservabilityPresenceSession(
            id="invalid-region",
            user_id="account-1",
            started_at=started,
            last_seen_at=last_seen,
            region_code="US-NY",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()


@pytest.mark.parametrize(
    "method, confidence",
    [("not_first_party", "verified"), ("first_party_first_touch", "certain")],
)
def test_attribution_values_are_canonical(
    db_session: Session, method: str, confidence: str
) -> None:
    started, _last_seen = _timestamp_pair()
    db_session.add_all([_user("account-1"), _user("operator")])
    db_session.add(_invite("operator"))
    db_session.add(
        AccountObservabilityAccountMetadata(
            user_id="account-1",
            registered_at=started,
            acquisition_invite_id="invite-1",
            attribution_method=method,
            attribution_confidence=confidence,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_account_deletion_removes_metadata_and_account_presence(
    db_session: Session,
) -> None:
    started, last_seen = _timestamp_pair()
    account = _user("account-1")
    db_session.add(account)
    db_session.flush()
    db_session.add(
        AccountObservabilityAccountMetadata(
            user_id="account-1", registered_at=started
        )
    )
    db_session.add(
        AccountObservabilityPresenceSession(
            id="account-presence-1",
            user_id="account-1",
            started_at=started,
            last_seen_at=last_seen,
        )
    )
    db_session.commit()

    db_session.delete(account)
    db_session.commit()
    assert db_session.get(AccountObservabilityAccountMetadata, "account-1") is None
    assert db_session.get(AccountObservabilityPresenceSession, "account-presence-1") is None


def test_guest_deletion_removes_guest_presence_without_deleting_invite(
    db_session: Session,
) -> None:
    started, last_seen = _timestamp_pair()
    guest = AccountObservabilityGuestIdentity(
        id="guest-1", first_invite_id="invite-1"
    )
    db_session.add_all([_user("operator"), _user("account-1")])
    db_session.flush()
    db_session.add(_invite("operator"))
    db_session.flush()
    db_session.add(guest)
    db_session.flush()
    db_session.add(
        AccountObservabilityAccountMetadata(
            user_id="account-1",
            registered_at=started,
            acquisition_invite_id="invite-1",
            prior_guest_id="guest-1",
            attribution_method="first_party_first_touch",
            attribution_confidence="verified",
        )
    )
    db_session.add(
        AccountObservabilityPresenceSession(
            id="guest-presence-1",
            guest_id="guest-1",
            invite_id="invite-1",
            started_at=started,
            last_seen_at=last_seen,
        )
    )
    db_session.commit()

    db_session.delete(guest)
    db_session.commit()
    assert db_session.get(AccountObservabilityInviteLink, "invite-1") is not None
    assert db_session.get(AccountObservabilityPresenceSession, "guest-presence-1") is None
    metadata = db_session.get(AccountObservabilityAccountMetadata, "account-1")
    assert metadata is not None
    assert metadata.acquisition_invite_id == "invite-1"
    assert metadata.prior_guest_id is None


def test_new_tables_have_no_prohibited_columns() -> None:
    for table in TABLES[1:]:
        assert not PROHIBITED_COLUMN_NAMES & set(table.columns), table.name
