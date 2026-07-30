from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, event, inspect, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.compiler import compiles

from guardian.db.migrations.versions.b2c3d4e5f6a8_add_hosted_room_persistence import (
    INVITE_STATUSES,
    PARTICIPANT_KINDS,
    PARTICIPANT_ROLES,
    PARTICIPANT_STATES,
    ROOM_STATUSES,
)
from guardian.db.models import (
    ChatMessage,
    ChatThread,
    HOSTED_ROOM_INVITE_STATUSES,
    HOSTED_ROOM_PARTICIPANT_KINDS,
    HOSTED_ROOM_PARTICIPANT_ROLES,
    HOSTED_ROOM_PARTICIPANT_STATES,
    HOSTED_ROOM_STATUSES,
    HostedRoom,
    HostedRoomInvite,
    HostedRoomParticipant,
    Project,
    User,
)


@compiles(JSONB, "sqlite")
def _compile_jsonb_for_sqlite(_type, _compiler, **_kwargs):
    return "JSON"


@pytest.fixture
def hosted_room_engine():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    for table in (
        User.__table__,
        Project.__table__,
        ChatThread.__table__,
        ChatMessage.__table__,
        HostedRoom.__table__,
        HostedRoomInvite.__table__,
        HostedRoomParticipant.__table__,
    ):
        table.create(engine)

    with engine.begin() as connection:
        connection.execute(
            User.__table__.insert(),
            {
                "id": "owner-account",
                "username": "room-owner",
                "password_hash": "not-a-real-password-hash",
                "role": "guest",
            },
        )
        connection.execute(
            ChatThread.__table__.insert(),
            [
                {
                    "id": 101,
                    "user_id": "owner-account",
                    "title": "Room thread one",
                },
                {
                    "id": 102,
                    "user_id": "owner-account",
                    "title": "Room thread two",
                },
            ],
        )
        connection.execute(
            ChatMessage.__table__.insert(),
            {
                "id": 1001,
                "thread_id": 101,
                "user_id": "owner-account",
                "role": "user",
                "content": "Canonical transcript content",
            },
        )

    try:
        yield engine
    finally:
        engine.dispose()


def _room_values(
    *,
    room_id: str = "room-1",
    thread_id: int = 101,
    slug: str = "room-one",
) -> dict[str, object]:
    return {
        "id": room_id,
        "owner_account_id": "owner-account",
        "backing_thread_id": thread_id,
        "title": "Hosted room",
        "slug": slug,
        "status": "active",
        "enabled_agent_ids": ["guardian", "luna"],
    }


def _invite_values(
    *,
    invite_id: str = "invite-1",
    token_hash: str = "a" * 64,
) -> dict[str, object]:
    return {
        "id": invite_id,
        "room_id": "room-1",
        "intended_display_name": "Invited guest",
        "token_hash": token_hash,
        "status": "pending",
    }


def test_hosted_room_model_and_migration_domains_match_exactly() -> None:
    assert set(ROOM_STATUSES) == HOSTED_ROOM_STATUSES
    assert set(INVITE_STATUSES) == HOSTED_ROOM_INVITE_STATUSES
    assert set(PARTICIPANT_KINDS) == HOSTED_ROOM_PARTICIPANT_KINDS
    assert set(PARTICIPANT_ROLES) == HOSTED_ROOM_PARTICIPANT_ROLES
    assert set(PARTICIPANT_STATES) == HOSTED_ROOM_PARTICIPANT_STATES


def test_hosted_room_uses_one_canonical_thread_without_transcript_duplication(
    hosted_room_engine,
) -> None:
    room = HostedRoom(**_room_values())
    assert room.status == "active"
    assert room.enabled_agent_ids == ["guardian", "luna"]

    with hosted_room_engine.begin() as connection:
        connection.execute(HostedRoom.__table__.insert(), _room_values())
        stored_room = (
            connection.execute(
                select(HostedRoom.__table__).where(HostedRoom.id == "room-1")
            )
            .mappings()
            .one()
        )
        stored_message = connection.execute(
            select(ChatMessage.content).where(ChatMessage.id == 1001)
        ).scalar_one()

    assert stored_room["backing_thread_id"] == 101
    assert stored_message == "Canonical transcript content"
    assert not {
        "content",
        "message",
        "messages",
        "transcript",
    } & set(HostedRoom.__table__.columns.keys())
    assert not {
        "content",
        "message",
        "messages",
        "transcript",
    } & set(HostedRoomInvite.__table__.columns.keys())
    assert not {
        "content",
        "message",
        "messages",
        "transcript",
    } & set(HostedRoomParticipant.__table__.columns.keys())


def test_hosted_room_domains_uniqueness_and_bounded_agent_configuration(
    hosted_room_engine,
) -> None:
    with hosted_room_engine.begin() as connection:
        connection.execute(HostedRoom.__table__.insert(), _room_values())

    invalid_rows = (
        _room_values(room_id="room-invalid-status", thread_id=102, slug="bad-status")
        | {"status": "paused"},
        _room_values(room_id="room-duplicate-thread", slug="other-slug"),
        _room_values(room_id="room-duplicate-slug", thread_id=102),
        _room_values(room_id="room-invalid-slug", thread_id=102, slug="not safe"),
        _room_values(room_id="room-agent-overflow", thread_id=102, slug="overflow")
        | {"enabled_agent_ids": ["x" * 5000]},
    )

    for values in invalid_rows:
        with pytest.raises(IntegrityError), hosted_room_engine.begin() as connection:
            connection.execute(HostedRoom.__table__.insert(), values)

    with pytest.raises(IntegrityError), hosted_room_engine.begin() as connection:
        connection.execute(
            HostedRoom.__table__.insert(),
            _room_values(room_id="room-bad-closed", thread_id=102, slug="bad-closed")
            | {"status": "closed"},
        )

    closed_at = datetime.now(timezone.utc)
    with hosted_room_engine.begin() as connection:
        connection.execute(
            HostedRoom.__table__.insert(),
            _room_values(room_id="room-closed", thread_id=102, slug="closed-room")
            | {"status": "closed", "closed_at": closed_at},
        )


def test_hosted_room_invite_stores_only_a_unique_hash_and_enforces_lifecycle(
    hosted_room_engine,
) -> None:
    invite = HostedRoomInvite(**_invite_values())
    assert invite.status == "pending"
    assert invite.intended_display_name == "Invited guest"

    with hosted_room_engine.begin() as connection:
        connection.execute(HostedRoom.__table__.insert(), _room_values())
        connection.execute(HostedRoomInvite.__table__.insert(), _invite_values())

    invite_columns = set(HostedRoomInvite.__table__.columns.keys())
    assert "token_hash" in invite_columns
    assert {
        "token",
        "invite_token",
        "raw_token",
        "access_token",
        "bearer",
    }.isdisjoint(invite_columns)

    invalid_invites = (
        _invite_values(invite_id="invite-invalid", token_hash="b" * 64)
        | {"status": "unknown"},
        _invite_values(invite_id="invite-duplicate", token_hash="a" * 64),
        _invite_values(invite_id="invite-bad-accepted", token_hash="c" * 64)
        | {"status": "accepted"},
        _invite_values(invite_id="invite-bad-revoked", token_hash="d" * 64)
        | {"status": "revoked"},
        _invite_values(invite_id="invite-bad-expired", token_hash="e" * 64)
        | {"status": "expired"},
    )
    for values in invalid_invites:
        with pytest.raises(IntegrityError), hosted_room_engine.begin() as connection:
            connection.execute(HostedRoomInvite.__table__.insert(), values)

    transition_time = datetime.now(timezone.utc)
    with hosted_room_engine.begin() as connection:
        connection.execute(
            HostedRoomInvite.__table__.insert(),
            [
                _invite_values(invite_id="invite-accepted", token_hash="f" * 64)
                | {
                    "status": "accepted",
                    "accepted_at": transition_time,
                    "revoked_at": None,
                    "expired_at": None,
                },
                _invite_values(invite_id="invite-revoked", token_hash="1" * 64)
                | {
                    "status": "revoked",
                    "accepted_at": None,
                    "revoked_at": transition_time,
                    "expired_at": None,
                },
                _invite_values(invite_id="invite-expired", token_hash="2" * 64)
                | {
                    "status": "expired",
                    "accepted_at": None,
                    "revoked_at": None,
                    "expired_at": transition_time,
                },
            ],
        )


def test_hosted_room_participant_kinds_roles_and_optional_guest_binding(
    hosted_room_engine,
) -> None:
    owner = HostedRoomParticipant(
        id="participant-owner",
        room_id="room-1",
        bound_account_id="owner-account",
        display_name="Owner",
        kind="human",
        role="owner",
        state="active",
    )
    member = HostedRoomParticipant(
        id="participant-member",
        room_id="room-1",
        invitation_id="invite-1",
        bound_account_id=None,
        display_name="Guest",
        kind="human",
        role="member",
        state="active",
    )
    agent = HostedRoomParticipant(
        id="participant-agent",
        room_id="room-1",
        bound_account_id=None,
        display_name="Guardian",
        kind="agent",
        role="agent",
        state="active",
        actor_source="resident",
        actor_ref="guardian",
    )
    assert owner.kind == "human" and owner.role == "owner"
    assert member.kind == "human" and member.bound_account_id is None
    assert agent.kind == "agent" and agent.bound_account_id is None

    with hosted_room_engine.begin() as connection:
        connection.execute(HostedRoom.__table__.insert(), _room_values())
        connection.execute(HostedRoomInvite.__table__.insert(), _invite_values())
        connection.execute(
            HostedRoomParticipant.__table__.insert(),
            [
                {
                    "id": participant.id,
                    "room_id": participant.room_id,
                    "invitation_id": participant.invitation_id,
                    "bound_account_id": participant.bound_account_id,
                    "display_name": participant.display_name,
                    "kind": participant.kind,
                    "role": participant.role,
                    "state": participant.state,
                    "actor_source": participant.actor_source,
                    "actor_ref": participant.actor_ref,
                }
                for participant in (owner, member, agent)
            ],
        )

    with hosted_room_engine.connect() as connection:
        guest_account_id = connection.execute(
            select(HostedRoomParticipant.bound_account_id).where(
                HostedRoomParticipant.id == "participant-member"
            )
        ).scalar_one()
    assert guest_account_id is None


def test_hosted_room_participant_constraints_fail_closed(
    hosted_room_engine,
) -> None:
    with hosted_room_engine.begin() as connection:
        connection.execute(HostedRoom.__table__.insert(), _room_values())
        connection.execute(HostedRoomInvite.__table__.insert(), _invite_values())
        connection.execute(
            HostedRoomParticipant.__table__.insert(),
            {
                "id": "participant-member",
                "room_id": "room-1",
                "invitation_id": "invite-1",
                "display_name": "Guest",
                "kind": "human",
                "role": "member",
                "state": "active",
            },
        )

    invalid_participants = (
        {
            "id": "participant-agent-member",
            "room_id": "room-1",
            "display_name": "Invalid",
            "kind": "agent",
            "role": "member",
            "state": "active",
        },
        {
            "id": "participant-human-agent",
            "room_id": "room-1",
            "display_name": "Invalid",
            "kind": "human",
            "role": "agent",
            "state": "active",
        },
        {
            "id": "participant-agent-account",
            "room_id": "room-1",
            "bound_account_id": "owner-account",
            "display_name": "Invalid",
            "kind": "agent",
            "role": "agent",
            "state": "active",
        },
        {
            "id": "participant-owner-unbound",
            "room_id": "room-1",
            "display_name": "Invalid",
            "kind": "human",
            "role": "owner",
            "state": "active",
        },
        {
            "id": "participant-invalid-state",
            "room_id": "room-1",
            "display_name": "Invalid",
            "kind": "human",
            "role": "member",
            "state": "unknown",
        },
        {
            "id": "participant-duplicate-invite",
            "room_id": "room-1",
            "invitation_id": "invite-1",
            "display_name": "Duplicate",
            "kind": "human",
            "role": "member",
            "state": "active",
        },
        {
            "id": "participant-removed-without-time",
            "room_id": "room-1",
            "display_name": "Removed",
            "kind": "human",
            "role": "member",
            "state": "removed",
        },
    )
    for values in invalid_participants:
        with pytest.raises(IntegrityError), hosted_room_engine.begin() as connection:
            connection.execute(HostedRoomParticipant.__table__.insert(), values)

    with hosted_room_engine.begin() as connection:
        connection.execute(
            HostedRoomParticipant.__table__.insert(),
            {
                "id": "participant-removed",
                "room_id": "room-1",
                "display_name": "Former guest",
                "kind": "human",
                "role": "member",
                "state": "removed",
                "removed_at": datetime.now(timezone.utc),
            },
        )


def test_hosted_room_schema_omits_presence_telemetry_and_contact_identity(
    hosted_room_engine,
) -> None:
    inspector = inspect(hosted_room_engine)
    prohibited = {
        "contact_id",
        "ip_address",
        "hashed_ip",
        "user_agent",
        "device_fingerprint",
        "latitude",
        "longitude",
        "last_seen",
        "online",
        "online_status",
        "behavioral",
    }
    for table_name in (
        "hosted_rooms",
        "hosted_room_invites",
        "hosted_room_participants",
    ):
        columns = {column["name"] for column in inspector.get_columns(table_name)}
        assert prohibited.isdisjoint(columns)
