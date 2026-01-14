"""Unit tests for personal facts CRUD logic without a live database."""

from types import SimpleNamespace

from guardian.core import db as db_module
from guardian.db.models import PersonalFactRevision


class _SessionContext:
    def __init__(self, session):
        self._session = session

    def __enter__(self):
        return self._session

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeSession:
    def __init__(self, fact):
        self._fact = fact
        self.added = []
        self.committed = False

    def query(self, model):
        return self

    def filter_by(self, **kwargs):
        return self

    def first(self):
        return self._fact

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.committed = True


def _build_db(fact):
    session = _FakeSession(fact)
    db = db_module._PostgresGuardianDB.__new__(db_module._PostgresGuardianDB)
    db.get_session = lambda: _SessionContext(session)
    return db, session


def test_update_fact_creates_value_revision():
    fact = SimpleNamespace(
        id=1,
        user_id="user",
        key="location",
        value="old",
        status="candidate",
        confidence=0.5,
        is_active=True,
        last_confirmed_at=None,
        created_at=None,
        updated_at=None,
    )
    db, session = _build_db(fact)

    updated = db.update_fact(1, value="new", actor="system")

    assert updated["value"] == "new"
    assert any(isinstance(obj, PersonalFactRevision) for obj in session.added)
    revision = next(
        obj for obj in session.added if isinstance(obj, PersonalFactRevision)
    )
    assert revision.action == "value_updated"
    assert revision.field_changed == "value"
    assert revision.old_value == "old"
    assert revision.new_value == "new"
    assert session.committed is True


def test_update_fact_sets_last_confirmed_at_on_verify():
    fact = SimpleNamespace(
        id=2,
        user_id="user",
        key="name",
        value="Sam",
        status="candidate",
        confidence=0.5,
        is_active=True,
        last_confirmed_at=None,
        created_at=None,
        updated_at=None,
    )
    db, session = _build_db(fact)

    updated = db.update_fact(2, status="verified", actor="user")

    assert updated["status"] == "verified"
    assert fact.last_confirmed_at is not None
    assert session.committed is True


def test_deactivate_fact_archives_and_revises():
    fact = SimpleNamespace(
        id=3,
        user_id="user",
        key="timezone",
        value="UTC",
        status="verified",
        confidence=0.8,
        is_active=True,
        last_confirmed_at=None,
        created_at=None,
        updated_at=None,
    )
    db, session = _build_db(fact)

    updated = db.deactivate_fact(3, actor="system")

    assert updated["status"] == "archived"
    assert updated["is_active"] is False
    revision = next(
        obj for obj in session.added if isinstance(obj, PersonalFactRevision)
    )
    assert revision.action == "deactivated"
    assert revision.field_changed == "is_active"
    assert session.committed is True
