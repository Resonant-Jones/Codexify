"""Focused tests for canonical ChatMessage provenance persistence."""

from __future__ import annotations

import inspect
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker

from guardian.core.chat_db import ChatDB, validate_message_provenance
from guardian.core.db import GuardianDB, _PostgresGuardianDB
from guardian.core.pgdb import PgDB
from guardian.db.models import (
    ChatMessage,
    ChatThread,
    HostedRoom,
    HostedRoomInvite,
    HostedRoomParticipant,
    Project,
    User,
)


@compiles(JSONB, "sqlite")
def _compile_jsonb_for_sqlite(_type, _compiler, **_kwargs):
    return "JSON"


class TrackingSession(Session):
    pass


@pytest.fixture
def orm_db():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    for table in (
        User.__table__,
        Project.__table__,
        ChatThread.__table__,
        HostedRoom.__table__,
        HostedRoomInvite.__table__,
        HostedRoomParticipant.__table__,
        ChatMessage.__table__,
    ):
        table.create(engine)

    now = datetime.now(timezone.utc)
    with engine.begin() as connection:
        connection.execute(
            User.__table__.insert().values(
                id="owner-1",
                username="owner",
                password_hash="hash",
                role="guest",
                created_at=now,
            )
        )
        connection.execute(
            Project.__table__.insert().values(
                user_id="owner-1",
                name="General",
                description="Default",
                created_at=now,
                updated_at=now,
            )
        )
        connection.execute(
            ChatThread.__table__.insert().values(
                id=1,
                user_id="owner-1",
                title="Room thread",
            )
        )
        connection.execute(
            HostedRoom.__table__.insert().values(
                id="room-1",
                owner_account_id="owner-1",
                backing_thread_id=1,
                title="Test Room",
                slug="test-room",
                status="active",
                enabled_agent_ids="[]",
                created_at=now,
                updated_at=now,
            )
        )
        connection.execute(
            HostedRoomParticipant.__table__.insert().values(
                id="part-guest",
                room_id="room-1",
                invitation_id=None,
                bound_account_id=None,
                display_name="Jane Guest",
                kind="human",
                role="member",
                state="active",
                joined_at=now,
                removed_at=None,
                created_at=now,
            )
        )

    def assign_sqlite_message_id(_mapper, connection, target):
        if target.id is None:
            target.id = (
                connection.execute(
                    select(ChatMessage.id).order_by(ChatMessage.id.desc()).limit(1)
                ).scalar()
                or 0
            ) + 1

    event.listen(ChatMessage, "before_insert", assign_sqlite_message_id)
    commit_count = []

    def count_commit(_session):
        commit_count.append(True)

    event.listen(TrackingSession, "after_commit", count_commit)
    db = _PostgresGuardianDB.__new__(_PostgresGuardianDB)
    db.SessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        class_=TrackingSession,
    )
    yield db, engine, commit_count
    event.remove(TrackingSession, "after_commit", count_commit)
    event.remove(ChatMessage, "before_insert", assign_sqlite_message_id)
    engine.dispose()


def _message_row(engine, message_id):
    with engine.begin() as connection:
        return connection.execute(
            select(ChatMessage).where(ChatMessage.id == message_id)
        ).one()


def test_orm_ordinary_message_is_backward_compatible(orm_db):
    db, engine, commit_count = orm_db

    message_id = db.create_message(1, "user", "ordinary text")

    row = _message_row(engine, message_id)
    assert isinstance(message_id, int)
    assert row.role == "user"
    assert row.content == "ordinary text"
    assert row.thread_id == 1
    assert row.hosted_room_participant_id is None
    assert row.sender_display_name_snapshot is None
    assert len(commit_count) == 1


def test_orm_persists_provenance_atomically_without_content_prefix(orm_db):
    db, engine, commit_count = orm_db
    statements = []

    def capture_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(statement.upper())

    event.listen(engine, "before_cursor_execute", capture_sql)
    content = "ordinary text\nGuardian: @Guardian\nmultiline body"

    message_id = db.create_message(
        1,
        "user",
        content,
        hosted_room_participant_id="part-guest",
        sender_display_name_snapshot="Jane Guest",
    )

    event.remove(engine, "before_cursor_execute", capture_sql)
    row = _message_row(engine, message_id)
    assert row.content == content
    assert row.role == "user"
    assert row.thread_id == 1
    assert row.hosted_room_participant_id == "part-guest"
    assert row.sender_display_name_snapshot == "Jane Guest"
    assert (
        sum("INSERT INTO CHAT_MESSAGES" in statement for statement in statements)
        == 1
    )
    assert not any("UPDATE CHAT_MESSAGES" in statement for statement in statements)
    assert len(commit_count) == 1


@pytest.mark.parametrize(
    ("participant_id", "snapshot"),
    [
        ("part-guest", None),
        (None, "Jane Guest"),
        ("", "Jane Guest"),
        ("part-guest", ""),
        ("   ", "Jane Guest"),
        ("part-guest", "   "),
    ],
)
def test_orm_rejects_invalid_provenance_before_session_commit(
    orm_db, participant_id, snapshot
):
    db, engine, commit_count = orm_db

    with pytest.raises(ValueError):
        db.create_message(
            1,
            "user",
            "should not persist",
            hosted_room_participant_id=participant_id,
            sender_display_name_snapshot=snapshot,
        )

    with engine.begin() as connection:
        assert connection.execute(select(ChatMessage)).all() == []
    assert len(commit_count) == 0


class FakeCursor:
    def __init__(self):
        self.executions = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, query, params):
        self.executions.append((query, params))

    def fetchone(self):
        return {"id": 41}


class FakeConnection:
    def __init__(self):
        self.cursor_instance = FakeCursor()
        self.commits = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, _exc, _tb):
        if exc_type is None:
            self.commits += 1
        return False

    def cursor(self):
        return self.cursor_instance


def _fake_pgdb():
    db = PgDB.__new__(PgDB)
    connection = FakeConnection()
    db.get_chat_thread = lambda _thread_id: {"user_id": "owner-1"}
    db._connect = lambda: connection
    db._chat_threads_supports_last_interaction_at = lambda: True
    return db, connection


def test_pgdb_persists_provenance_in_initial_insert_and_one_transaction():
    db, connection = _fake_pgdb()

    message_id = db.create_message(
        1,
        "assistant",
        "Guardian: response\n@Guardian",
        hosted_room_participant_id="part-guest",
        sender_display_name_snapshot="Jane Guest",
    )

    assert message_id == 41
    assert len(connection.cursor_instance.executions) == 2
    insert_sql, insert_params = connection.cursor_instance.executions[0]
    assert "hosted_room_participant_id" in insert_sql
    assert "sender_display_name_snapshot" in insert_sql
    assert insert_params[-2:] == ("part-guest", "Jane Guest")
    assert not any(
        "update chat_messages" in query.lower()
        for query, _params in connection.cursor_instance.executions
    )
    assert connection.commits == 1


def test_pgdb_legacy_positional_call_remains_valid():
    db, connection = _fake_pgdb()

    assert db.create_message(1, "user", "legacy", None, "owner-1") == 41
    insert_params = connection.cursor_instance.executions[0][1]
    assert insert_params[-2:] == (None, None)


@pytest.mark.parametrize(
    ("participant_id", "snapshot"),
    [
        ("part-guest", None),
        (None, "Jane Guest"),
        ("", "Jane Guest"),
        ("part-guest", ""),
        ("   ", "Jane Guest"),
        ("part-guest", "   "),
    ],
)
def test_pgdb_rejects_invalid_provenance_before_connect(
    participant_id, snapshot
):
    db, connection = _fake_pgdb()

    with pytest.raises(ValueError):
        db.create_message(
            1,
            "user",
            "should not persist",
            hosted_room_participant_id=participant_id,
            sender_display_name_snapshot=snapshot,
        )

    assert connection.cursor_instance.executions == []
    assert connection.commits == 0


def test_interface_parity_and_keyword_only_compatibility():
    signatures = [
        inspect.signature(ChatDB.create_message),
        inspect.signature(PgDB.create_message),
        inspect.signature(_PostgresGuardianDB.create_message),
    ]
    for signature in signatures:
        for name in (
            "hosted_room_participant_id",
            "sender_display_name_snapshot",
        ):
            parameter = signature.parameters[name]
            assert parameter.annotation in ("str | None", str | None)
            assert parameter.default is None
            assert parameter.kind is inspect.Parameter.KEYWORD_ONLY


def test_guardian_db_facade_forwards_both_provenance_values():
    calls = []

    class FakeImplementation:
        def create_message(self, *args, **kwargs):
            calls.append((args, kwargs))
            return 77

    facade = GuardianDB.__new__(GuardianDB)
    facade._impl = FakeImplementation()

    result = facade.create_message(
        1,
        "user",
        "forwarded",
        hosted_room_participant_id="part-guest",
        sender_display_name_snapshot="Jane Guest",
    )

    assert result == 77
    assert calls == [
        (
            (1, "user", "forwarded"),
            {
                "hosted_room_participant_id": "part-guest",
                "sender_display_name_snapshot": "Jane Guest",
            },
        )
    ]


@pytest.mark.parametrize(
    ("participant_id", "snapshot", "valid"),
    [
        (None, None, True),
        ("part-guest", "Jane Guest", True),
        ("part-guest", None, False),
        (None, "Jane Guest", False),
        ("", "Jane Guest", False),
        ("part-guest", "", False),
        ("   ", "Jane Guest", False),
        ("part-guest", "   ", False),
    ],
)
def test_pair_validation_matrix(participant_id, snapshot, valid):
    if valid:
        validate_message_provenance(participant_id, snapshot)
    else:
        with pytest.raises(ValueError):
            validate_message_provenance(participant_id, snapshot)
