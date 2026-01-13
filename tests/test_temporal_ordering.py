"""Unit tests for temporal ordering behavior without a live database."""

from unittest.mock import MagicMock

from sqlalchemy import or_

from guardian.core import db as db_module
from guardian.db.models import ChatMessage


class _SessionContext:
    def __init__(self, session):
        self._session = session

    def __enter__(self):
        return self._session

    def __exit__(self, exc_type, exc, tb):
        return False


class _QueryRecorder:
    def __init__(self):
        self.filter_by_kwargs = []
        self.filters = []
        self.order_by_args = None
        self.limit_val = None
        self.offset_val = None

    def filter_by(self, **kwargs):
        self.filter_by_kwargs.append(kwargs)
        return self

    def filter(self, *args):
        self.filters.extend(args)
        return self

    def order_by(self, *args):
        self.order_by_args = args
        return self

    def limit(self, val):
        self.limit_val = val
        return self

    def offset(self, val):
        self.offset_val = val
        return self

    def all(self):
        return []


def _build_db(query):
    session = MagicMock()
    session.query.return_value = query
    db = db_module._PostgresGuardianDB.__new__(db_module._PostgresGuardianDB)
    db.get_session = lambda: _SessionContext(session)
    return db, query


def test_list_messages_orders_by_event_at_then_id():
    db, query = _build_db(_QueryRecorder())

    db.list_messages(123, limit=10, offset=5)

    assert query.order_by_args is not None
    assert str(query.order_by_args[0]) == str(ChatMessage.event_at.asc())
    assert str(query.order_by_args[1]) == str(ChatMessage.id.asc())


def test_list_messages_exclude_kinds_applies_filter():
    db, query = _build_db(_QueryRecorder())
    exclude = ["fact_evidence", "tool"]

    db.list_messages(123, exclude_kinds=exclude)

    expected = str(
        or_(
            ChatMessage.kind.is_(None),
            ChatMessage.kind.notin_(exclude),
        )
    )
    assert any(str(expr) == expected for expr in query.filters)


def test_list_messages_by_date_range_orders_by_event_at():
    db, query = _build_db(_QueryRecorder())

    db.list_messages_by_date_range(123, start_date="2024-01-01T00:00:00Z")

    assert query.order_by_args is not None
    assert str(query.order_by_args[0]) == str(ChatMessage.event_at.asc())
    assert str(query.order_by_args[1]) == str(ChatMessage.id.asc())
