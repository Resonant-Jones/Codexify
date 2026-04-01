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
