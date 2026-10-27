from __future__ import annotations

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.db.models import Base, UserSettings
from guardian.services import iddb_settings_service


@pytest.fixture()
def settings_session_factory():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine, tables=[UserSettings.__table__])
    Session = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, future=True
    )
    iddb_settings_service._set_session_factory(Session)
    return Session


def test_user_settings_persist_across_reads_and_writes(
    settings_session_factory,
):
    first = iddb_settings_service.upsert_user_settings(
        "u1",
        {
            "memory_mode": "light",
            "diary_requires_unlock": True,
            "allow_sensitive_modeling": False,
        },
    )
    assert first == {
        "memory_mode": "light",
        "diary_requires_unlock": True,
        "allow_sensitive_modeling": False,
    }

    repeat = iddb_settings_service.get_user_settings("u1")
    assert repeat == first

    second = iddb_settings_service.upsert_user_settings(
        "u1",
        {"allow_sensitive_modeling": True},
    )
    assert second == {
        "memory_mode": "light",
        "diary_requires_unlock": True,
        "allow_sensitive_modeling": True,
    }
    assert iddb_settings_service.get_user_settings("u1") == second

    other = iddb_settings_service.upsert_user_settings(
        "u2",
        {"memory_mode": "deep"},
    )
    assert other == {
        "memory_mode": "deep",
        "diary_requires_unlock": False,
        "allow_sensitive_modeling": False,
    }
    assert iddb_settings_service.get_user_settings("u1") == second
    assert iddb_settings_service.get_user_settings("u2") == other


def test_default_compatibility_row_is_read_only(settings_session_factory):
    Session = settings_session_factory
    with Session() as session:
        session.add(
            UserSettings(
                user_id="default",
                memory_mode="none",
                diary_requires_unlock=True,
                allow_sensitive_modeling=True,
            )
        )
        session.commit()

    assert iddb_settings_service.get_user_settings("missing-user") == {
        "memory_mode": "none",
        "diary_requires_unlock": True,
        "allow_sensitive_modeling": True,
    }

    with pytest.raises(HTTPException) as excinfo:
        iddb_settings_service.upsert_user_settings(
            "default",
            {"memory_mode": "deep"},
        )
    assert excinfo.value.status_code == 403


def test_default_fallback_does_not_pollute_regular_writes(
    settings_session_factory,
):
    Session = settings_session_factory
    with Session() as session:
        session.add(
            UserSettings(
                user_id="default",
                memory_mode="light",
                diary_requires_unlock=False,
                allow_sensitive_modeling=True,
            )
        )
        session.commit()

    created = iddb_settings_service.upsert_user_settings(
        "u3",
        {"memory_mode": "deep"},
    )
    assert created == {
        "memory_mode": "deep",
        "diary_requires_unlock": False,
        "allow_sensitive_modeling": False,
    }
    assert iddb_settings_service.get_user_settings("u3") == created


# ── Automatic collection consent ──────────────────────────────────────


def _enable_consent(user_id: str, state: str = "enabled") -> dict:
    return iddb_settings_service.set_automatic_memory_suggestions_consent(
        user_id, state, actor_user_id=user_id
    )


def test_consent_defaults_to_unset_and_is_not_effective(settings_session_factory):
    record = iddb_settings_service.read_automatic_memory_suggestions_consent("u1")
    assert record["state"] == "unset"
    assert record["effective"] is False
    assert record["recorded_by_user_id"] is None
    assert iddb_settings_service.is_automatic_memory_collection_enabled("u1") is False


def test_consent_is_account_scoped(settings_session_factory):
    _enable_consent("u1")

    owner = iddb_settings_service.read_automatic_memory_suggestions_consent("u1")
    assert owner["state"] == "enabled"
    assert owner["effective"] is True
    assert owner["recorded_by_user_id"] == "u1"
    assert owner["policy_version"] == iddb_settings_service.CONSENT_POLICY_VERSION

    other = iddb_settings_service.read_automatic_memory_suggestions_consent("u2")
    assert other["state"] == "unset"
    assert other["effective"] is False
    assert iddb_settings_service.is_automatic_memory_collection_enabled("u2") is False


def test_legacy_default_row_can_never_grant_consent(settings_session_factory):
    Session = settings_session_factory
    with Session() as session:
        session.add(
            UserSettings(
                user_id="default",
                memory_mode="light",
                automatic_memory_suggestions="enabled",
                consent_policy_version=iddb_settings_service.CONSENT_POLICY_VERSION,
                consent_recorded_by_user_id="default",
            )
        )
        session.commit()

    inherited = iddb_settings_service.read_automatic_memory_suggestions_consent("u9")
    assert inherited["state"] == "unset"
    assert inherited["effective"] is False

    legacy_self = iddb_settings_service.read_automatic_memory_suggestions_consent(
        "default"
    )
    assert legacy_self["state"] == "unset"
    assert legacy_self["effective"] is False
    assert legacy_self["reason"] == "ambiguous_account"
    assert (
        iddb_settings_service.is_automatic_memory_collection_enabled("default")
        is False
    )


def _insert_row_ignoring_check_constraint(Session, row) -> None:
    """Store a row whose value the constraint would normally reject.

    The database constraint is the first line of defence; this simulates a
    legacy or corrupt row so the read-side fail-closed path can be proven.
    """
    bind = Session.kw["bind"]
    with bind.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.exec_driver_sql("PRAGMA ignore_check_constraints=ON")
    try:
        with Session() as session:
            session.add(row)
            session.commit()
    finally:
        with bind.connect().execution_options(
            isolation_level="AUTOCOMMIT"
        ) as conn:
            conn.exec_driver_sql("PRAGMA ignore_check_constraints=OFF")


def test_consent_is_fail_closed_on_missing_invalid_stale_and_foreign_actor(
    settings_session_factory,
):
    Session = settings_session_factory

    _insert_row_ignoring_check_constraint(
        Session,
        UserSettings(
            user_id="u-invalid",
            automatic_memory_suggestions="bogus",
            consent_policy_version=iddb_settings_service.CONSENT_POLICY_VERSION,
            consent_recorded_by_user_id="u-invalid",
        ),
    )
    with Session() as session:
        session.add(
            UserSettings(
                user_id="u-stale",
                automatic_memory_suggestions="enabled",
                consent_policy_version="0",
                consent_recorded_by_user_id="u-stale",
            )
        )
        session.add(
            UserSettings(
                user_id="u-foreign",
                automatic_memory_suggestions="enabled",
                consent_policy_version=iddb_settings_service.CONSENT_POLICY_VERSION,
                consent_recorded_by_user_id="someone-else",
            )
        )
        session.add(
            UserSettings(
                user_id="u-unrecorded",
                automatic_memory_suggestions="enabled",
                consent_policy_version=iddb_settings_service.CONSENT_POLICY_VERSION,
            )
        )
        session.commit()

    expectations = {
        "u-invalid": "invalid_state",
        "u-stale": "stale_policy_version",
        "u-foreign": "actor_mismatch",
        "u-unrecorded": "not_recorded",
    }
    for user_id, reason in expectations.items():
        record = iddb_settings_service.read_automatic_memory_suggestions_consent(
            user_id
        )
        assert record["effective"] is False, user_id
        assert record["reason"] == reason
        assert (
            iddb_settings_service.is_automatic_memory_collection_enabled(user_id)
            is False
        )


def test_consent_survives_service_reinitialization(settings_session_factory):
    _enable_consent("u1")

    # A fresh session factory models a service/session reinitialization: the
    # consent record must still be present and effective.
    iddb_settings_service._set_session_factory(settings_session_factory)

    record = iddb_settings_service.read_automatic_memory_suggestions_consent("u1")
    assert record["state"] == "enabled"
    assert record["effective"] is True
    assert record["recorded_by_user_id"] == "u1"
    assert record["recorded_at"] is not None
    assert record["updated_at"] is not None


def test_consent_write_rejects_a_mismatched_actor(settings_session_factory):
    with pytest.raises(HTTPException) as excinfo:
        iddb_settings_service.set_automatic_memory_suggestions_consent(
            "u1", "enabled", actor_user_id="someone-else"
        )
    assert excinfo.value.status_code == 403


def test_consent_write_rejects_an_invalid_state(settings_session_factory):
    with pytest.raises(HTTPException) as excinfo:
        iddb_settings_service.set_automatic_memory_suggestions_consent(
            "u1", "maybe", actor_user_id="u1"
        )
    assert excinfo.value.status_code == 400


def test_consent_write_rejects_the_legacy_default_account(settings_session_factory):
    with pytest.raises(HTTPException) as excinfo:
        iddb_settings_service.set_automatic_memory_suggestions_consent(
            "default", "enabled", actor_user_id="default"
        )
    assert excinfo.value.status_code == 403


def test_identity_settings_write_cannot_overwrite_consent(settings_session_factory):
    _enable_consent("u1")

    iddb_settings_service.upsert_user_settings("u1", {"memory_mode": "light"})

    record = iddb_settings_service.read_automatic_memory_suggestions_consent("u1")
    assert record["state"] == "enabled"
    assert record["effective"] is True


def test_memory_mode_never_grants_consent(settings_session_factory):
    iddb_settings_service.upsert_user_settings("u1", {"memory_mode": "deep"})

    record = iddb_settings_service.read_automatic_memory_suggestions_consent("u1")
    assert record["state"] == "unset"
    assert record["effective"] is False
    assert (
        iddb_settings_service.is_automatic_memory_collection_enabled("u1") is False
    )


def test_pausing_keeps_the_consent_record_and_other_settings(settings_session_factory):
    iddb_settings_service.upsert_user_settings("u1", {"memory_mode": "light"})
    _enable_consent("u1", "enabled")
    _enable_consent("u1", "paused")

    record = iddb_settings_service.read_automatic_memory_suggestions_consent("u1")
    assert record["state"] == "paused"
    assert record["effective"] is False
    assert record["recorded_by_user_id"] == "u1"
    assert iddb_settings_service.get_user_settings("u1")["memory_mode"] == "light"
