from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.account_observability import invites
from guardian.account_observability.invites import (
    InviteConflictError,
    InviteValidationError,
    complete_registration_attribution,
    create_invite,
    disable_invite,
    generate_invite_token,
    hash_invite_token,
    record_invite_audit,
    resolve_invite,
    revoke_invite,
)
from guardian.db.models import (
    AccountObservabilityAccountMetadata,
    AccountObservabilityGuestIdentity,
    AccountObservabilityInviteLink,
    AuditLog,
    Base,
    EventGraphEvent,
    User,
)

NOW = datetime(2026, 7, 24, 16, 0, tzinfo=timezone.utc)


@pytest.fixture()
def session_factory():
    engine = create_engine(
        "sqlite+pysqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    tables = [
        User.__table__,
        AccountObservabilityInviteLink.__table__,
        AccountObservabilityGuestIdentity.__table__,
        AccountObservabilityAccountMetadata.__table__,
        AuditLog.__table__,
        EventGraphEvent.__table__,
    ]
    Base.metadata.create_all(engine, tables=tables)
    factory = sessionmaker(bind=engine, future=True, autoflush=False)
    try:
        yield factory
    finally:
        Base.metadata.drop_all(engine, tables=list(reversed(tables)))


def _seed_user(session: Session, user_id: str = "operator") -> User:
    user = User(
        id=user_id,
        username=user_id,
        password_hash="not-used",
        role="admin",
        created_at=NOW,
    )
    session.add(user)
    session.commit()
    return user


def _create_invite(session: Session, name: str = "Wave"):
    row, token = create_invite(
        session,
        created_by_user_id="operator",
        name=name,
        now=NOW,
    )
    session.commit()
    return row, token


def _all_strings(value: object) -> list[str]:
    if isinstance(value, dict):
        return [item for pair in value.items() for item in _all_strings(pair)]
    if isinstance(value, (list, tuple, set)):
        return [item for part in value for item in _all_strings(part)]
    return [value] if isinstance(value, str) else []


def test_token_has_256_bits_and_url_safe_shape():
    token = generate_invite_token()

    assert len(token) >= 42
    assert re.fullmatch(r"[A-Za-z0-9_-]+", token)
    assert token != generate_invite_token()


def test_only_hash_is_persisted_and_raw_token_is_returned_once(session_factory):
    with session_factory() as session:
        _seed_user(session)
        row, token = _create_invite(session)

        assert token
        assert row.token_hash == hash_invite_token(token)
        assert len(row.token_hash) == 64
        assert token not in row.token_hash
        assert not hasattr(row, "raw_token")


def test_duplicate_token_hash_is_rejected(session_factory, monkeypatch):
    with session_factory() as session:
        _seed_user(session)
        first, token = _create_invite(session)
        monkeypatch.setattr(invites, "generate_invite_token", lambda: token)

        with pytest.raises(InviteConflictError):
            create_invite(
                session,
                created_by_user_id="operator",
                name="Duplicate",
                now=NOW,
            )
        session.rollback()
        assert session.get(AccountObservabilityInviteLink, first.invite_id)


def test_past_expiry_is_rejected(session_factory):
    with session_factory() as session:
        _seed_user(session)
        with pytest.raises(InviteValidationError):
            create_invite(
                session,
                created_by_user_id="operator",
                name="Past",
                expires_at=NOW - timedelta(seconds=1),
                now=NOW,
            )


def test_active_invite_resolves_and_invalid_resolution_creates_no_guest(
    session_factory,
):
    with session_factory() as session:
        _seed_user(session)
        row, token = _create_invite(session)

        result = resolve_invite(
            session, token=token, guest_cookie=None, now=NOW
        )
        session.commit()
        assert result.result == "attributed"
        assert result.guest_id
        guest_count = session.query(AccountObservabilityGuestIdentity).count()
        assert guest_count == 1

        invalid = resolve_invite(
            session, token="not-the-token", guest_cookie=None, now=NOW
        )
        session.commit()
        assert invalid.result is None
        assert session.query(AccountObservabilityGuestIdentity).count() == 1
        assert (
            row.invite_id
            == session.get(
                AccountObservabilityGuestIdentity, result.guest_id
            ).first_invite_id
        )


@pytest.mark.parametrize("transition", ["disable", "revoke"])
def test_disabled_and_revoked_invites_fail_closed(session_factory, transition):
    with session_factory() as session:
        _seed_user(session)
        row, token = _create_invite(session)
        if transition == "disable":
            disable_invite(session, row.invite_id, now=NOW)
        else:
            revoke_invite(session, row.invite_id, now=NOW)
        session.commit()

        result = resolve_invite(
            session, token=token, guest_cookie=None, now=NOW
        )
        assert result.result is None
        session.commit()
        assert session.query(AccountObservabilityGuestIdentity).count() == 0


def test_expired_invite_uses_same_unavailable_result(session_factory):
    with session_factory() as session:
        _seed_user(session)
        row, token = create_invite(
            session,
            created_by_user_id="operator",
            name="Short lived",
            expires_at=NOW + timedelta(seconds=1),
            now=NOW,
        )
        session.commit()
        result = resolve_invite(
            session,
            token=token,
            guest_cookie=None,
            now=NOW + timedelta(seconds=2),
        )
        assert result.result is None
        assert session.get(AccountObservabilityInviteLink, row.invite_id)
        assert session.query(AccountObservabilityGuestIdentity).count() == 0


def test_first_touch_is_immutable_and_malformed_cookie_is_absent(
    session_factory,
):
    with session_factory() as session:
        _seed_user(session)
        first, first_token = _create_invite(session, "First")
        second, second_token = _create_invite(session, "Second")

        first_result = resolve_invite(
            session, token=first_token, guest_cookie="malformed", now=NOW
        )
        session.commit()
        second_result = resolve_invite(
            session,
            token=second_token,
            guest_cookie=first_result.guest_id,
            now=NOW,
        )
        session.commit()

        guest = session.get(
            AccountObservabilityGuestIdentity, first_result.guest_id
        )
        assert first_result.result == "attributed"
        assert second_result.result == "already_attributed"
        assert guest.first_invite_id == first.invite_id
        assert guest.first_invite_id != second.invite_id


def test_unknown_guest_cookie_never_selects_caller_guest_id(session_factory):
    supplied = str(uuid4())
    with session_factory() as session:
        _seed_user(session)
        _, token = _create_invite(session)
        result = resolve_invite(
            session, token=token, guest_cookie=supplied, now=NOW
        )
        session.commit()

        assert result.guest_id != supplied
        assert session.get(AccountObservabilityGuestIdentity, supplied) is None


def test_registration_conversion_is_attributed_idempotent_and_survives_revoke(
    session_factory,
):
    with session_factory() as session:
        _seed_user(session)
        invite, token = _create_invite(session)
        resolution = resolve_invite(
            session, token=token, guest_cookie=None, now=NOW
        )
        session.commit()
        revoke_invite(session, invite.invite_id, now=NOW)
        session.commit()

        user = User(
            id="alice",
            username="alice",
            password_hash="not-used",
            role="guest",
            created_at=NOW,
        )
        session.add(user)
        session.commit()
        converted = complete_registration_attribution(
            session,
            user_id="alice",
            guest_cookie=resolution.guest_id,
            registered_at=NOW,
        )
        session.commit()
        metadata = session.get(AccountObservabilityAccountMetadata, "alice")
        guest = session.get(
            AccountObservabilityGuestIdentity, resolution.guest_id
        )

        assert converted.attributed is True
        assert metadata.acquisition_invite_id == invite.invite_id
        assert metadata.prior_guest_id == resolution.guest_id
        assert metadata.attribution_method == "first_party_first_touch"
        assert metadata.attribution_confidence == "verified"
        assert guest.converted_at.replace(tzinfo=timezone.utc) == NOW

        later_invite, later_token = _create_invite(session, "Later")
        later_resolution = resolve_invite(
            session,
            token=later_token,
            guest_cookie=resolution.guest_id,
            now=NOW,
        )
        session.commit()
        assert later_resolution.result == "already_attributed"
        assert (
            session.get(
                AccountObservabilityAccountMetadata, "alice"
            ).acquisition_invite_id
            == invite.invite_id
        )
        assert later_invite.invite_id != invite.invite_id

        repeated = complete_registration_attribution(
            session,
            user_id="alice",
            guest_cookie=resolution.guest_id,
            registered_at=NOW + timedelta(days=1),
        )
        session.commit()
        assert repeated.created is False
        assert (
            session.get(
                AccountObservabilityAccountMetadata, "alice"
            ).registered_at.replace(tzinfo=timezone.utc)
            == NOW
        )


def test_existing_acquisition_is_never_overwritten(session_factory):
    with session_factory() as session:
        _seed_user(session)
        first, first_token = _create_invite(session, "First")
        second, second_token = _create_invite(session, "Second")
        resolution = resolve_invite(
            session, token=second_token, guest_cookie=None, now=NOW
        )
        session.commit()
        user = User(
            id="already-attributed",
            username="already-attributed",
            password_hash="not-used",
            role="guest",
            created_at=NOW,
        )
        session.add(user)
        session.add(
            AccountObservabilityAccountMetadata(
                user_id=user.id,
                registered_at=NOW,
                acquisition_invite_id=first.invite_id,
                prior_guest_id=None,
                attribution_method="first_party_first_touch",
                attribution_confidence="verified",
                created_at=NOW,
                updated_at=NOW,
            )
        )
        session.commit()

        result = complete_registration_attribution(
            session,
            user_id=user.id,
            guest_cookie=resolution.guest_id,
            registered_at=NOW,
        )
        session.commit()
        assert result.created is False
        assert (
            session.get(
                AccountObservabilityAccountMetadata, user.id
            ).acquisition_invite_id
            == first.invite_id
        )
        assert first_token not in str(result)


def test_system_and_seeded_accounts_are_excluded(session_factory):
    with session_factory() as session:
        for user_id in ("local", "system:worker", "seeded:demo"):
            user = User(
                id=user_id,
                username=user_id,
                password_hash="not-used",
                role="guest",
                created_at=NOW,
            )
            session.add(user)
        session.commit()

        for user_id in ("local", "system:worker", "seeded:demo"):
            result = complete_registration_attribution(
                session,
                user_id=user_id,
                guest_cookie=None,
                registered_at=NOW,
            )
            assert result.skipped_reason == "ineligible_identity"
        session.commit()
        assert session.query(AccountObservabilityAccountMetadata).count() == 0


def test_audit_rows_contain_bounded_ids_but_no_raw_token_or_cookie(
    session_factory,
):
    with session_factory() as session:
        _seed_user(session)
        invite, token = _create_invite(session)

        class FakeAuditSession:
            def __init__(self):
                self.objects = []

            def add(self, value):
                self.objects.append(value)

            def scalar(self, _statement):
                return None

        audit_session = FakeAuditSession()
        record_invite_audit(
            audit_session,
            action="invite_created",
            invite_id=invite.invite_id,
            actor_id="operator",
            request_id="req_invite_test",
            result="attributed",
            occurred_at=NOW,
        )

        values = _all_strings(
            [getattr(value, "__dict__", {}) for value in audit_session.objects]
        )
        assert token not in values
        assert all("token" not in value.lower() for value in values)
