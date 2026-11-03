"""Concurrency proof for recipient-local direct-message read cursors.

The read cursor advances to a caller-asserted watermark and must never move
backwards, even when two read mutations for the same conversation race.

This module proves the invariant against **real PostgreSQL** with genuinely
concurrent sessions.  SQLite serializes writers differently and cannot
exercise a read-compare-write race, so a passing SQLite test would not prove
anything about the production engine.

Two races are covered:

1. **Existing-cursor advancement.**  Two transactions read the same current
   cursor, then write different watermarks.  Without serialization the
   *older* watermark can land last and move the cursor backwards.
2. **Initial insertion.**  Two transactions both observe "no cursor yet" and
   both try to insert the same primary key, which raises a uniqueness error
   instead of yielding an idempotent result.

Requires ``TEST_DATABASE_URL`` (or ``DATABASE_URL``) and psycopg; skips
otherwise.
"""

from __future__ import annotations

import os
import threading
import uuid

import pytest

try:
    import psycopg  # type: ignore
except ImportError:  # pragma: no cover
    psycopg = None

import sqlalchemy as sa
from sqlalchemy import event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from guardian.db.models import (
    Base,
    DirectMessage,
    DirectMessageConversation,
    DirectMessageReadCursor,
    DirectMessageRelationship,
    DirectMessageRelationshipParticipant,
    ThreadSpaceNode,
    User,
    UserProfile,
)
from guardian.messaging import service as messaging_service

# Thread-local switch used by the forced-interleaving test to hold one
# writer immediately before its cursor write.
_pause_writer = threading.local()


def _admin_database_url(base_url: str) -> str:
    return (
        make_url(base_url)
        .set(drivername="postgresql", database="postgres")
        .render_as_string(hide_password=False)
    )


def _database_url(base_url: str, database_name: str) -> str:
    return (
        make_url(base_url)
        .set(database=database_name)
        .render_as_string(hide_password=False)
    )


@pytest.fixture
def postgres_engine():
    """A real PostgreSQL engine with the messaging schema created."""
    if psycopg is None:
        pytest.skip("psycopg not installed")

    base_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not base_url:
        pytest.skip("TEST_DATABASE_URL or DATABASE_URL environment variable required")

    admin_url = _admin_database_url(base_url)
    database_name = f"codexify_readrace_{uuid.uuid4().hex[:12]}"
    database_url = _database_url(base_url, database_name)

    try:
        admin_connection = psycopg.connect(admin_url, autocommit=True)
    except Exception as exc:  # pragma: no cover - environment specific
        pytest.skip(f"Unable to connect to admin database: {exc}")

    try:
        with admin_connection.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE {database_name}")
    except psycopg.Error as exc:  # pragma: no cover - environment specific
        pytest.skip(f"Unable to create test database: {exc.sqlstate}")
    finally:
        admin_connection.close()

    engine = sa.create_engine(database_url, future=True)
    # The full schema, created from the canonical metadata so the foreign
    # keys (users, threadspace_nodes, messages) resolve exactly as they do in
    # production.
    Base.metadata.create_all(bind=engine)

    try:
        yield engine
    finally:
        engine.dispose()
        cleanup_connection = psycopg.connect(admin_url, autocommit=True)
        try:
            with cleanup_connection.cursor() as cursor:
                cursor.execute(
                    "SELECT pg_terminate_backend(pid) "
                    "FROM pg_stat_activity WHERE datname = %s",
                    (database_name,),
                )
                cursor.execute(f"DROP DATABASE IF EXISTS {database_name}")
        finally:
            cleanup_connection.close()


def _seed_conversation(engine):
    """Seed one conversation with two participants and three ordered messages."""
    import datetime

    now = datetime.datetime.now(datetime.timezone.utc)
    node_id = "node-race"
    profile_ids = [f"profile-{uuid.uuid4().hex[:12]}" for _ in range(2)]
    relationship_id = f"rel-{uuid.uuid4().hex[:12]}"
    conversation_id = f"conv-{uuid.uuid4().hex[:12]}"

    with engine.begin() as connection:
        connection.execute(
            sa.insert(ThreadSpaceNode.__table__).values(
                node_id=node_id,
                name="Race Node",
                status="active",
                created_at=now,
                updated_at=now,
            )
        )
        for profile_id in profile_ids:
            user_id = f"user-{uuid.uuid4().hex[:12]}"
            connection.execute(
                sa.insert(User.__table__).values(
                    id=user_id,
                    username=user_id,
                    email=f"{user_id}@example.invalid",
                    password_hash="!not-a-real-hash!",
                    role="guest",
                    created_at=now,
                )
            )
            connection.execute(
                sa.insert(UserProfile.__table__).values(
                    user_id=user_id,
                    profile_id=profile_id,
                    node_id=node_id,
                    display_name="Race Participant",
                    accent_color="default",
                    created_at=now,
                    updated_at=now,
                )
            )
        connection.execute(
            sa.insert(DirectMessageRelationship.__table__).values(
                id=relationship_id,
                participant_pair_key=f"{profile_ids[0]}:{profile_ids[1]}",
                created_at=now,
                updated_at=now,
            )
        )
        for profile_id in profile_ids:
            connection.execute(
                sa.insert(DirectMessageRelationshipParticipant.__table__).values(
                    id=f"part-{uuid.uuid4().hex[:12]}",
                    relationship_id=relationship_id,
                    node_id=node_id,
                    profile_id=profile_id,
                    created_at=now,
                )
            )
        connection.execute(
            sa.insert(DirectMessageConversation.__table__).values(
                id=conversation_id,
                relationship_id=relationship_id,
                created_by_profile_id=profile_ids[0],
                kind="direct",
                created_at=now,
                latest_activity_at=now,
            )
        )
        message_ids = []
        for index in range(3):
            message_id = f"msg-{uuid.uuid4().hex[:12]}"
            message_ids.append(message_id)
            connection.execute(
                sa.insert(DirectMessage.__table__).values(
                    id=message_id,
                    conversation_id=conversation_id,
                    sender_node_id=node_id,
                    sender_profile_id=profile_ids[0],
                    content_type="text/plain",
                    body=f"message {index}",
                    created_at=now + datetime.timedelta(seconds=index),
                )
            )

    return {
        "conversation_id": conversation_id,
        "relationship_id": relationship_id,
        "profile_id": profile_ids[1],
        "message_ids": message_ids,
    }


def _profile(engine, profile_id):
    with Session(engine) as session:
        return session.scalars(
            sa.select(UserProfile).where(UserProfile.profile_id == profile_id)
        ).first()


def _conversation(engine, conversation_id):
    with Session(engine) as session:
        return session.get(DirectMessageConversation, conversation_id)


def _cursor_position(engine, conversation_id, profile_id):
    """Return the ordinal position of the cursor's watermark message.

    Returns None when no cursor exists.  Position is derived from
    ``(created_at, id)`` so it matches the service's ordering exactly.
    """
    with Session(engine) as session:
        cursor_row = session.get(
            DirectMessageReadCursor, (conversation_id, profile_id)
        )
        if cursor_row is None or cursor_row.last_read_message_id is None:
            return None
        message = session.get(DirectMessage, cursor_row.last_read_message_id)
        if message is None:
            return None
        return (message.created_at, message.id)


def _message_positions(engine, message_ids):
    with Session(engine) as session:
        result = {}
        for message_id in message_ids:
            message = session.get(DirectMessage, message_id)
            result[message_id] = (message.created_at, message.id)
        return result


def _advance(session, profile, conversation, watermark_message_id):
    """Advance the cursor on a dedicated session (does not commit)."""
    return messaging_service.advance_read_cursor(
        session, profile, conversation, watermark_message_id
    )


def test_concurrent_advances_never_move_the_cursor_backwards(postgres_engine):
    """Two racing watermarks must leave the cursor at the newest position.

    Without serialization, request A (older watermark) can commit *after*
    request B (newer watermark), leaving the cursor pointing at the older
    message — the cursor moved backwards.

    The interleaving is forced rather than left to timing.  Request A is
    paused immediately before its write, request B runs to completion, and
    only then is A allowed to write.  With serialization A holds the
    participant lock across the whole operation, so B cannot complete first;
    A's pause therefore expires, A commits, and B then advances past A.
    """
    seeded = _seed_conversation(postgres_engine)
    message_ids = seeded["message_ids"]
    older, newer = message_ids[1], message_ids[2]

    profile = _profile(postgres_engine, seeded["profile_id"])
    conversation = _conversation(postgres_engine, seeded["conversation_id"])

    # Both transactions observe the same starting point.
    with Session(postgres_engine) as setup_session:
        _advance(setup_session, profile, conversation, message_ids[0])
        setup_session.commit()

    errors: list[Exception] = []
    lock = threading.Lock()
    b_finished = threading.Event()

    def pause_a_before_write(conn, cursor, statement, parameters, context, executemany):
        """Hold request A just before it writes the cursor."""
        if not getattr(_pause_writer, "active", False):
            return
        head = statement.strip().upper()
        if not head.startswith(("UPDATE", "INSERT")):
            return
        if "direct_message_read_cursors" not in statement:
            return
        _pause_writer.active = False
        # Wait for B to finish.  Under correct serialization B is blocked on
        # A's lock and cannot finish, so this wait expires and A proceeds.
        b_finished.wait(timeout=3.0)

    def racer_b() -> None:
        try:
            with Session(postgres_engine) as session:
                session_conversation = session.get(
                    DirectMessageConversation, seeded["conversation_id"]
                )
                session_profile = session.scalars(
                    sa.select(UserProfile).where(
                        UserProfile.profile_id == seeded["profile_id"]
                    )
                ).first()
                _advance(session, session_profile, session_conversation, newer)
                session.commit()
        except Exception as exc:  # pragma: no cover - surfaced by assertion
            with lock:
                errors.append(exc)
        finally:
            b_finished.set()

    def racer_a() -> None:
        try:
            with Session(postgres_engine) as session:
                session_conversation = session.get(
                    DirectMessageConversation, seeded["conversation_id"]
                )
                session_profile = session.scalars(
                    sa.select(UserProfile).where(
                        UserProfile.profile_id == seeded["profile_id"]
                    )
                ).first()
                _pause_writer.active = True
                _advance(session, session_profile, session_conversation, older)
                session.commit()
        except Exception as exc:  # pragma: no cover - surfaced by assertion
            with lock:
                errors.append(exc)

    event.listen(postgres_engine, "before_cursor_execute", pause_a_before_write)
    try:
        thread_a = threading.Thread(target=racer_a)
        thread_b = threading.Thread(target=racer_b)
        thread_a.start()
        thread_b.start()
        thread_a.join(timeout=60)
        thread_b.join(timeout=60)
    finally:
        event.remove(postgres_engine, "before_cursor_execute", pause_a_before_write)

    assert not errors, f"racing advances raised: {errors}"

    final_position = _cursor_position(
        postgres_engine, seeded["conversation_id"], seeded["profile_id"]
    )
    expected_position = _message_positions(postgres_engine, [newer])[newer]

    assert final_position == expected_position, (
        "the cursor moved backwards: the older watermark won the race "
        f"(final={final_position}, expected={expected_position})"
    )


def test_concurrent_initial_insertion_is_idempotent(postgres_engine):
    """Two simultaneous first-reads must not raise a uniqueness error.

    Both transactions observe "no cursor yet" and both try to insert the same
    primary key.  Without serialization the second insert raises an
    IntegrityError instead of the operation being idempotent.
    """
    seeded = _seed_conversation(postgres_engine)
    message_id = seeded["message_ids"][0]

    barrier = threading.Barrier(2)
    errors: list[Exception] = []
    lock = threading.Lock()

    def racer() -> None:
        try:
            with Session(postgres_engine) as session:
                session_conversation = session.get(
                    DirectMessageConversation, seeded["conversation_id"]
                )
                session_profile = session.scalars(
                    sa.select(UserProfile).where(
                        UserProfile.profile_id == seeded["profile_id"]
                    )
                ).first()
                session.scalar(
                    sa.select(DirectMessageReadCursor).where(
                        DirectMessageReadCursor.conversation_id
                        == seeded["conversation_id"],
                        DirectMessageReadCursor.profile_id
                        == seeded["profile_id"],
                    )
                )
                barrier.wait(timeout=30)
                _advance(session, session_profile, session_conversation, message_id)
                session.commit()
        except Exception as exc:  # pragma: no cover - surfaced by assertion
            with lock:
                errors.append(exc)

    threads = [threading.Thread(target=racer) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)

    assert not errors, f"concurrent first-read raised: {errors}"

    with Session(postgres_engine) as session:
        rows = session.scalars(
            sa.select(DirectMessageReadCursor).where(
                DirectMessageReadCursor.conversation_id
                == seeded["conversation_id"],
                DirectMessageReadCursor.profile_id == seeded["profile_id"],
            )
        ).all()
    assert len(rows) == 1, f"expected exactly one cursor row, got {len(rows)}"
    assert rows[0].last_read_message_id == message_id


def test_stale_watermark_after_newer_never_regresses(postgres_engine):
    """A strictly older watermark submitted later must not move the cursor.

    This is the sequential form of the same invariant: the service must
    refuse to advance backwards even without concurrency.
    """
    seeded = _seed_conversation(postgres_engine)
    older, newer = seeded["message_ids"][0], seeded["message_ids"][2]

    with Session(postgres_engine) as session:
        session_profile = session.scalars(
            sa.select(UserProfile).where(
                UserProfile.profile_id == seeded["profile_id"]
            )
        ).first()
        session_conversation = session.get(
            DirectMessageConversation, seeded["conversation_id"]
        )
        messaging_service.advance_read_cursor(
            session, session_profile, session_conversation, newer
        )
        session.commit()

    with Session(postgres_engine) as session:
        session_profile = session.scalars(
            sa.select(UserProfile).where(
                UserProfile.profile_id == seeded["profile_id"]
            )
        ).first()
        session_conversation = session.get(
            DirectMessageConversation, seeded["conversation_id"]
        )
        messaging_service.advance_read_cursor(
            session, session_profile, session_conversation, older
        )
        session.commit()

    positions = _message_positions(postgres_engine, [older, newer])
    final_position = _cursor_position(
        postgres_engine, seeded["conversation_id"], seeded["profile_id"]
    )
    assert final_position == positions[newer], (
        "an older watermark regressed the cursor: "
        f"final={final_position}, expected={positions[newer]}"
    )
