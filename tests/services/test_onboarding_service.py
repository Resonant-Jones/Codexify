from __future__ import annotations
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from guardian.db.models import Base, User, UserOnboardingState, UserSettings
from guardian.services import onboarding_service as service


@pytest.fixture
def sessions(tmp_path):
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'state.db'}")
    Base.metadata.create_all(
        engine,
        tables=[User.__table__, UserSettings.__table__, UserOnboardingState.__table__],
    )
    factory = sessionmaker(engine)
    with factory() as session:
        session.add_all(
            [
                User(id=user, username=user, password_hash="unused")
                for user in ("a", "b")
            ]
        )
        session.commit()
    yield factory
    engine.dispose()


def test_defaults_do_not_create_row(sessions):
    with sessions() as session:
        assert service.read_state(session, "a") == service.DEFAULT_STATE
        assert session.get(UserOnboardingState, "a") is None


def test_partial_patch_ownership_fresh_session_and_iddb_isolation(sessions):
    with sessions() as session:
        session.add(UserSettings(user_id="a", memory_mode="light"))
        session.commit()
        service.patch_state(
            session, "a", {"status": "in_progress", "last_step_key": "identity"}
        )
    with sessions() as session:
        result = service.patch_state(session, "a", {"contextual_tips_enabled": False})
        assert (
            result["status"] == "in_progress" and result["last_step_key"] == "identity"
        )
        assert service.read_state(session, "b") == service.DEFAULT_STATE
        assert session.get(UserOnboardingState, "b") is None
        assert session.get(UserSettings, "a").memory_mode == "light"
        assert len(session.scalars(select(UserSettings)).all()) == 1
    with sessions() as session:
        assert service.read_state(session, "a")["contextual_tips_enabled"] is False


@pytest.mark.parametrize("owner", [None, "", "default", "nonexistent"])
def test_no_legacy_fallback(sessions, owner):
    with sessions() as session, pytest.raises(HTTPException):
        service.read_state(session, owner)
