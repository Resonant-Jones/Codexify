"""The canonical local node is identified, not inferred from the age of a row.

ADR-079 requires the local-node resolver to ensure "one stable canonical
local node row".  Selecting the oldest row cannot promise that: two rows
written in the same clock tick tie, and the old tie-break was the node id,
so a foreign row whose id sorted ahead was adopted as "local".

These tests pin the property that the age-based resolver could not hold:
the resolver returns the row that is *marked* local, whatever else exists
in the table, and the database refuses to hold two local rows.
"""

from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.db.models import ThreadSpaceNode
from guardian.messaging.service import get_or_create_local_node

# A fixed instant, so "same clock tick" is exact rather than incidental.
_TICK = datetime(2026, 1, 1, 12, 0, 0)
_EARLIER = datetime(2025, 12, 31, 12, 0, 0)


@pytest.fixture()
def node_engine():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    ThreadSpaceNode.__table__.create(engine)
    try:
        yield engine
    finally:
        engine.dispose()


def test_the_resolver_mints_exactly_one_local_node(node_engine):
    """First use creates the local node, and every later read returns it."""
    with sessionmaker(bind=node_engine)() as session:
        minted = get_or_create_local_node(session)

        assert minted.is_local is True
        assert get_or_create_local_node(session).node_id == minted.node_id

        rows = session.query(ThreadSpaceNode).all()
        assert len(rows) == 1


def test_a_foreign_row_in_the_same_tick_is_never_adopted(node_engine):
    """The regression this change fixes.

    The foreign row shares the local row's ``created_at`` exactly, and its
    node id sorts *ahead* of the local one.  The age-based resolver ordered
    by ``(created_at, node_id)`` and returned the foreign row -- which is
    how a People search could end up scoped to a remote node.
    """
    with sessionmaker(bind=node_engine)() as session:
        session.add(
            ThreadSpaceNode(
                node_id="node-zzzzzzzz",
                name="Local",
                is_local=True,
                created_at=_TICK,
            )
        )
        session.add(
            ThreadSpaceNode(
                node_id="node-aaaaaaaa",
                name="Elsewhere",
                is_local=False,
                created_at=_TICK,
            )
        )
        session.commit()

        resolved = get_or_create_local_node(session)

        assert resolved.node_id == "node-zzzzzzzz"
        assert resolved.name == "Local"


def test_an_older_foreign_row_does_not_become_the_local_node(node_engine):
    """A row recorded earlier than the local node is not the local node."""
    with sessionmaker(bind=node_engine)() as session:
        session.add(
            ThreadSpaceNode(
                node_id="node-remote",
                name="Remote",
                is_local=False,
                created_at=_EARLIER,
            )
        )
        session.commit()

        resolved = get_or_create_local_node(session)

        assert resolved.is_local is True
        assert resolved.node_id != "node-remote"


def test_the_database_refuses_a_second_local_node(node_engine):
    """At most one local row, enforced by the database and not by convention."""
    with sessionmaker(bind=node_engine)() as session:
        session.add(
            ThreadSpaceNode(node_id="node-one", name="Local", is_local=True)
        )
        session.commit()

        session.add(
            ThreadSpaceNode(node_id="node-two", name="Other", is_local=True)
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()


def test_a_foreign_row_is_never_minted_as_local(node_engine):
    """The resolver does not adopt an existing foreign row."""
    with sessionmaker(bind=node_engine)() as session:
        session.add(
            ThreadSpaceNode(
                node_id="node-elsewhere",
                name="Elsewhere",
                is_local=False,
                created_at=_TICK,
            )
        )
        session.commit()

        resolved = get_or_create_local_node(session)

        assert resolved.is_local is True
        assert resolved.node_id != "node-elsewhere"
        assert session.query(ThreadSpaceNode).count() == 2
