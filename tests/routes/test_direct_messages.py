"""Focused route/service tests for node-addressed direct messaging.

Covers social identity, discovery privacy, canonical conversation
resolution, durable messaging, idempotency, authorization isolation, and
route posture — against an in-memory SQLite schema built from the real ORM
metadata, with the real service and route code paths.
"""

from __future__ import annotations

import importlib
import uuid
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.core.dependencies import RequestUserScope
from guardian.db.models import (
    Base,
    DirectMessage,
    DirectMessageConversation,
    DirectMessageConversationPlacement,
    DirectMessageRelationship,
    DirectMessageRelationshipParticipant,
    ThreadSpaceNode,
    User,
    UserProfile,
)
from guardian.routes.direct_messages import router as dm_router

REPO_ROOT = Path(__file__).resolve().parents[2]

TABLE_ORDER = (
    User.__table__,
    ThreadSpaceNode.__table__,
    UserProfile.__table__,
    DirectMessageRelationship.__table__,
    DirectMessageRelationshipParticipant.__table__,
    DirectMessageConversation.__table__,
    DirectMessageConversationPlacement.__table__,
    DirectMessage.__table__,
)


def _new_engine(
    db_url: str = "sqlite+pysqlite:///:memory:", *, create_tables: bool = True
):
    engine = create_engine(
        db_url,
        future=True,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    if create_tables:
        User.__table__.create(engine)
        with engine.begin() as connection:
            connection.execute(
                text(
                    "CREATE TABLE projects ("
                    "id INTEGER PRIMARY KEY, "
                    "user_id VARCHAR(255) NOT NULL, "
                    "name VARCHAR(255) NOT NULL"
                    ")"
                )
            )
            connection.execute(
                text(
                    "CREATE TABLE chat_threads ("
                    "id INTEGER PRIMARY KEY, "
                    "user_id VARCHAR(255) NOT NULL, "
                    "title VARCHAR(512) NOT NULL, "
                    "project_id INTEGER NULL REFERENCES projects(id)"
                    ")"
                )
            )
        for table in TABLE_ORDER[1:]:
            table.create(engine)
    return engine


class _FakeDb:
    """Minimal get_session()-shaped database façade for the route seam."""

    def __init__(self, engine):
        self._factory = sessionmaker(bind=engine, autoflush=False)

    def get_session(self):
        return self._factory()


@pytest.fixture
def dm_engine():
    engine = _new_engine()
    try:
        yield engine
    finally:
        engine.dispose()


def _seed_users(session):
    for user_id in ("user-a@example.com", "user-b@example.com", "user-c@example.com"):
        session.add(
            User(
                id=user_id,
                username=user_id.split("@")[0],
                email=user_id,
                password_hash="not-a-real-password-hash",
                role="guest",
            )
        )
    session.commit()


def _seed_project_origins(engine):
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO projects (id, user_id, name) VALUES "
                "(101, 'user-a@example.com', 'Alpha Project'), "
                "(102, 'user-a@example.com', 'Alpha Archive'), "
                "(201, 'user-b@example.com', 'Bravo Project')"
            )
        )
        connection.execute(
            text(
                "INSERT INTO chat_threads (id, user_id, title, project_id) VALUES "
                "(1001, 'user-a@example.com', 'Alpha Thread', 101), "
                "(2001, 'user-b@example.com', 'Bravo Thread', 201)"
            )
        )


def _make_client(engine, user_id: str | None = "user-a@example.com"):
    """Build a minimal app hosting the DM router with auth overridden."""
    app = FastAPI()
    app.include_router(dm_router)
    from guardian.core.dependencies import get_request_user_scope

    def _override_scope():
        if user_id is None:
            return RequestUserScope(user_id="")
        return RequestUserScope(
            user_id=user_id,
            subject_id=user_id,
            account_id=user_id,
            multi_user_enabled=True,
        )

    app.dependency_overrides[get_request_user_scope] = _override_scope
    return TestClient(app)


@pytest.fixture
def seeded(monkeypatch, dm_engine):
    with dm_engine.begin() as connection:
        connection.execute(text("SELECT 1"))
    session = sessionmaker(bind=dm_engine)()
    try:
        _seed_users(session)
    finally:
        session.close()
    _seed_project_origins(dm_engine)

    monkeypatch.setattr(
        "guardian.routes.direct_messages._db", lambda: _FakeDb(dm_engine)
    )
    return dm_engine


def _claim_username(client, username: str):
    response = client.put("/api/profile/social-identity", json={"username": username})
    return response


# ── Social identity ───────────────────────────────────────────────────────


def test_existing_user_starts_with_unset_username(seeded):
    client = _make_client(seeded, "user-a@example.com")
    response = client.get("/api/profile/social-identity")
    assert response.status_code == 200
    profile = response.json()["profile"]
    assert profile["username"] is None
    assert profile["username_state"] == "unset"
    assert profile["profile_id"]
    assert profile["node_id"].startswith("node-")


def test_claim_username_is_deliberate_and_normalized(seeded):
    client = _make_client(seeded, "user-a@example.com")
    response = _claim_username(client, "  Zac-J0nes_99  ")
    assert response.status_code == 200
    profile = response.json()["profile"]
    assert profile["username"] == "zac-j0nes_99"
    assert profile["username_state"] == "active"
    # Canonical lowercase is preserved on readback.
    again = client.get("/api/profile/social-identity")
    assert again.json()["profile"]["username"] == "zac-j0nes_99"


def test_username_case_collision_rejected(seeded):
    client_a = _make_client(seeded, "user-a@example.com")
    client_b = _make_client(seeded, "user-b@example.com")
    assert _claim_username(client_a, "Zac").status_code == 200
    assert _claim_username(client_b, "zac").status_code == 409
    assert _claim_username(client_b, "ZAC").status_code == 409


def test_reserved_and_invalid_usernames_rejected(seeded):
    client = _make_client(seeded, "user-a@example.com")
    for bad, expected_code in (
        ("guardian", "username_reserved"),
        ("Admin", "username_reserved"),
        ("ab", "username_length"),
        ("a" * 33, "username_length"),
        ("has space", "username_grammar"),
        ("emoji🔥name", "username_grammar"),
        ("-leading", "username_grammar"),
        ("trailing-", "username_grammar"),
        ("___", "username_grammar"),
    ):
        response = _claim_username(client, bad)
        assert response.status_code == 422, bad
        assert response.json()["detail"]["error"] == expected_code, bad
    # Nothing was claimed along the way.
    assert (
        client.get("/api/profile/social-identity").json()["profile"]["username"] is None
    )


def test_rename_keeps_profile_id_and_conversations(seeded):
    client_a = _make_client(seeded, "user-a@example.com")
    client_b = _make_client(seeded, "user-b@example.com")

    claimed = _claim_username(client_a, "alpha")
    assert claimed.status_code == 200
    profile_a = claimed.json()["profile"]
    profile_b = _claim_username(client_b, "bravo").json()["profile"]

    relationship = client_a.post(
        "/api/direct-messages/relationships",
        json={
            "destination_node_id": profile_b["node_id"],
            "destination_profile_id": profile_b["profile_id"],
        },
    ).json()["relationship"]
    conversation_id = client_a.post(
        f"/api/direct-messages/relationships/{relationship['relationship_id']}"
        "/conversations",
        json={},
    ).json()["conversation"]["conversation_id"]

    renamed = _claim_username(client_a, "alpha-2")
    assert renamed.status_code == 200
    assert renamed.json()["profile"]["profile_id"] == profile_a["profile_id"]
    assert renamed.json()["profile"]["username"] == "alpha-2"

    # Existing conversations still resolve for the same profile identity.
    listing = client_a.get("/api/direct-messages/conversations")
    assert listing.status_code == 200
    assert [c["conversation_id"] for c in listing.json()["conversations"]] == [
        conversation_id
    ]


# ── Node identity ─────────────────────────────────────────────────────────


def test_single_canonical_local_node_across_profiles(seeded):
    client_a = _make_client(seeded, "user-a@example.com")
    client_b = _make_client(seeded, "user-b@example.com")
    node_a = client_a.get("/api/profile/social-identity").json()["profile"]["node_id"]
    node_b = client_b.get("/api/profile/social-identity").json()["profile"]["node_id"]
    assert node_a == node_b
    # Stable across repeated resolution.
    assert (
        client_a.get("/api/profile/social-identity").json()["profile"]["node_id"]
        == node_a
    )


def test_nonlocal_destination_rejected_without_federation(seeded):
    client_a = _make_client(seeded, "user-a@example.com")
    local = client_a.get("/api/profile/social-identity").json()["profile"]
    fake_node_id = "node-" + "f" * 32
    response = client_a.post(
        "/api/direct-messages/relationships",
        json={
            "destination_node_id": fake_node_id,
            "destination_profile_id": local["profile_id"],
        },
    )
    assert response.status_code == 422
    assert response.json()["detail"]["error"] == "unsupported_nonlocal_destination"
    # No relationship was created for the nonlocal attempt.
    assert (
        client_a.get("/api/direct-messages/relationships").json()["relationships"]
        == []
    )


# ── Discovery privacy ─────────────────────────────────────────────────────


def test_search_resolves_safe_social_identity(seeded):
    client_a = _make_client(seeded, "user-a@example.com")
    client_b = _make_client(seeded, "user-b@example.com")
    _claim_username(client_a, "searcher")
    claimed = _claim_username(client_b, "Zac")
    assert claimed.status_code == 200
    profile_b = claimed.json()["profile"]

    with seeded.begin() as connection:
        connection.execute(
            UserProfile.__table__.update()
            .where(UserProfile.user_id == "user-b@example.com")
            .values(display_name="Zac The Tester")
        )

    response = client_a.get("/api/direct-messages/profiles", params={"q": "za"})
    assert response.status_code == 200
    results = response.json()["profiles"]
    assert len(results) == 1
    hit = results[0]
    assert hit["node_id"] == profile_b["node_id"]
    assert hit["profile_id"] == profile_b["profile_id"]
    assert hit["username"] == "zac"
    assert hit["display_name"] == "Zac The Tester"
    for key in hit:
        assert key in {
            "node_id",
            "profile_id",
            "username",
            "username_state",
            "display_name",
            "avatar_url",
        }
    assert "email" not in hit
    assert "user_id" not in hit


def test_unclaimed_usernames_are_not_discoverable(seeded):
    client = _make_client(seeded, "user-a@example.com")
    response = client.get("/api/direct-messages/profiles", params={"q": "user"})
    assert response.status_code == 200
    assert response.json()["profiles"] == []


# ── Conversations ─────────────────────────────────────────────────────────


def _two_profiles(seeded):
    client_a = _make_client(seeded, "user-a@example.com")
    client_b = _make_client(seeded, "user-b@example.com")
    profile_a = _claim_username(client_a, "alice").json()["profile"]
    profile_b = _claim_username(client_b, "bob").json()["profile"]
    assert profile_a["node_id"] == profile_b["node_id"]
    return client_a, client_b, profile_a, profile_b


def test_relationship_resolve_is_canonical_without_creating_conversation(seeded):
    client_a, client_b, profile_a, profile_b = _two_profiles(seeded)
    payload_ab = {
        "destination_node_id": profile_b["node_id"],
        "destination_profile_id": profile_b["profile_id"],
    }
    payload_ba = {
        "destination_node_id": profile_a["node_id"],
        "destination_profile_id": profile_a["profile_id"],
    }

    first = client_a.post("/api/direct-messages/relationships", json=payload_ab)
    assert first.status_code == 200
    relationship_id = first.json()["relationship"]["relationship_id"]

    repeated = client_a.post("/api/direct-messages/relationships", json=payload_ab)
    reverse = client_b.post("/api/direct-messages/relationships", json=payload_ba)
    assert repeated.status_code == 200
    assert reverse.status_code == 200
    assert repeated.json()["relationship"]["relationship_id"] == relationship_id
    assert reverse.json()["relationship"]["relationship_id"] == relationship_id

    for client in (client_a, client_b):
        listing = client.get("/api/direct-messages/relationships")
        assert listing.status_code == 200
        assert [
            item["relationship_id"] for item in listing.json()["relationships"]
        ] == [relationship_id]

    client_c = _make_client(seeded, "user-c@example.com")
    assert client_c.get("/api/direct-messages/relationships").json()[
        "relationships"
    ] == []

    with seeded.connect() as connection:
        assert connection.execute(
            select(DirectMessageRelationship.id)
        ).scalars().all() == [relationship_id]
        assert connection.execute(select(DirectMessageConversation.id)).all() == []


def test_relationship_membership_is_only_canonical_participant_authority():
    assert "direct_message_conversation_participants" not in Base.metadata.tables
    assert "participant_pair_key" not in DirectMessageConversation.__table__.columns
    assert DirectMessageConversation.__table__.c.relationship_id.nullable is False


def test_relationship_owns_multiple_distinct_conversations(seeded):
    client_a, _client_b, _profile_a, profile_b = _two_profiles(seeded)
    relationship = client_a.post(
        "/api/direct-messages/relationships",
        json={
            "destination_node_id": profile_b["node_id"],
            "destination_profile_id": profile_b["profile_id"],
        },
    ).json()["relationship"]
    relationship_id = relationship["relationship_id"]

    first = client_a.post(
        f"/api/direct-messages/relationships/{relationship_id}/conversations",
        json={},
    )
    second = client_a.post(
        f"/api/direct-messages/relationships/{relationship_id}/conversations",
        json={},
    )
    assert first.status_code == 200
    assert second.status_code == 200
    first_conversation = first.json()["conversation"]
    second_conversation = second.json()["conversation"]
    assert first_conversation["conversation_id"] != second_conversation[
        "conversation_id"
    ]
    assert first_conversation["relationship_id"] == relationship_id
    assert second_conversation["relationship_id"] == relationship_id

    listing = client_a.get(
        f"/api/direct-messages/relationships/{relationship_id}/conversations"
    )
    assert listing.status_code == 200
    listed_ids = {
        conversation["conversation_id"]
        for conversation in listing.json()["conversations"]
    }
    assert listed_ids == {
        first_conversation["conversation_id"],
        second_conversation["conversation_id"],
    }

    with seeded.connect() as connection:
        rows = connection.execute(
            select(DirectMessageConversation.relationship_id)
        ).scalars().all()
    assert rows == [relationship_id, relationship_id]


def test_project_origin_defaults_creator_placement_and_stays_immutable(seeded):
    client_a, client_b, profile_a, profile_b = _two_profiles(seeded)
    relationship_id = client_a.post(
        "/api/direct-messages/relationships",
        json={
            "destination_node_id": profile_b["node_id"],
            "destination_profile_id": profile_b["profile_id"],
        },
    ).json()["relationship"]["relationship_id"]

    created = client_a.post(
        f"/api/direct-messages/relationships/{relationship_id}/conversations",
        json={"origin_project_id": 101},
    )
    assert created.status_code == 200
    conversation = created.json()["conversation"]
    conversation_id = conversation["conversation_id"]
    assert conversation["origin"] == {
        "created_by_profile_id": profile_a["profile_id"],
        "origin_project_id": 101,
        "origin_thread_id": None,
        "created_at": conversation["created_at"],
    }
    assert conversation["placement"]["project_id"] == 101

    with seeded.connect() as connection:
        placements = connection.execute(
            select(
                DirectMessageConversationPlacement.profile_id,
                DirectMessageConversationPlacement.project_id,
            ).where(
                DirectMessageConversationPlacement.conversation_id
                == conversation_id
            )
        ).all()
    assert dict(placements) == {
        profile_a["profile_id"]: 101,
        profile_b["profile_id"]: None,
    }

    peer_view = client_b.get(
        f"/api/direct-messages/conversations/{conversation_id}"
    )
    assert peer_view.status_code == 200
    peer_conversation = peer_view.json()["conversation"]
    assert peer_conversation["origin"]["created_by_profile_id"] == profile_a[
        "profile_id"
    ]
    assert peer_conversation["origin"]["origin_project_id"] is None
    assert peer_conversation["origin"]["origin_thread_id"] is None
    assert peer_conversation["placement"]["project_id"] is None
    assert "peer_placement" not in peer_conversation

    moved = client_a.patch(
        f"/api/direct-messages/conversations/{conversation_id}/placement",
        json={"project_id": 102},
    )
    assert moved.status_code == 200
    assert moved.json()["conversation"]["placement"]["project_id"] == 102
    assert moved.json()["conversation"]["origin"]["origin_project_id"] == 101

    unscoped = client_a.patch(
        f"/api/direct-messages/conversations/{conversation_id}/placement",
        json={"project_id": None},
    )
    assert unscoped.status_code == 200
    assert unscoped.json()["conversation"]["placement"]["project_id"] is None
    assert unscoped.json()["conversation"]["origin"]["origin_project_id"] == 101


def test_thread_origin_requires_owner_access_and_matching_project(seeded):
    client_a, client_b, profile_a, profile_b = _two_profiles(seeded)
    relationship_id = client_a.post(
        "/api/direct-messages/relationships",
        json={
            "destination_node_id": profile_b["node_id"],
            "destination_profile_id": profile_b["profile_id"],
        },
    ).json()["relationship"]["relationship_id"]
    route = f"/api/direct-messages/relationships/{relationship_id}/conversations"

    created = client_a.post(
        route,
        json={"origin_project_id": 101, "origin_thread_id": 1001},
    )
    assert created.status_code == 200
    conversation = created.json()["conversation"]
    assert conversation["origin"]["origin_project_id"] == 101
    assert conversation["origin"]["origin_thread_id"] == 1001
    assert conversation["placement"]["project_id"] == 101

    peer = client_b.get(
        f"/api/direct-messages/conversations/{conversation['conversation_id']}"
    ).json()["conversation"]
    assert peer["origin"]["origin_project_id"] is None
    assert peer["origin"]["origin_thread_id"] is None

    inaccessible_project = client_a.post(route, json={"origin_project_id": 201})
    assert inaccessible_project.status_code == 404
    assert inaccessible_project.json()["detail"]["error"] == (
        "origin_project_id_not_found"
    )

    inaccessible_thread = client_a.post(route, json={"origin_thread_id": 2001})
    assert inaccessible_thread.status_code == 404
    assert inaccessible_thread.json()["detail"]["error"] == (
        "origin_thread_id_not_found"
    )

    mismatch = client_a.post(
        route,
        json={"origin_project_id": 102, "origin_thread_id": 1001},
    )
    assert mismatch.status_code == 422
    assert mismatch.json()["detail"]["error"] == (
        "origin_thread_project_mismatch"
    )

    with seeded.connect() as connection:
        count = connection.execute(
            select(DirectMessageConversation.id)
        ).scalars().all()
    assert count == [conversation["conversation_id"]]


def test_pair_resolution_is_relationship_scoped_and_endpoint_replaced(seeded):
    """One canonical Relationship per unordered pair; the old pair-resolve
    conversation endpoint is gone, and every new Conversation is distinct."""
    client_a, client_b, profile_a, profile_b = _two_profiles(seeded)
    payload_ab = {
        "destination_node_id": profile_b["node_id"],
        "destination_profile_id": profile_b["profile_id"],
    }
    payload_ba = {
        "destination_node_id": profile_a["node_id"],
        "destination_profile_id": profile_a["profile_id"],
    }

    first = client_a.post("/api/direct-messages/relationships", json=payload_ab)
    assert first.status_code == 200
    relationship = first.json()["relationship"]
    relationship_id = relationship["relationship_id"]
    assert len(relationship["participants"]) == 2

    repeat = client_a.post("/api/direct-messages/relationships", json=payload_ab)
    reverse = client_b.post("/api/direct-messages/relationships", json=payload_ba)
    assert repeat.json()["relationship"]["relationship_id"] == relationship_id
    assert reverse.json()["relationship"]["relationship_id"] == relationship_id

    # Conversation creation is now explicit and always yields a new ID.
    first_conversation = client_a.post(
        f"/api/direct-messages/relationships/{relationship_id}/conversations",
        json={},
    )
    second_conversation = client_a.post(
        f"/api/direct-messages/relationships/{relationship_id}/conversations",
        json={},
    )
    assert first_conversation.status_code == 200
    assert second_conversation.status_code == 200
    assert (
        first_conversation.json()["conversation"]["conversation_id"]
        != second_conversation.json()["conversation"]["conversation_id"]
    )

    # The legacy one-pair-one-conversation resolve endpoint is removed.
    legacy = client_a.post("/api/direct-messages/conversations", json=payload_ab)
    assert legacy.status_code == 405

    # The old global conversation list still shows participant conversations.
    listing = client_a.get("/api/direct-messages/conversations")
    assert len(listing.json()["conversations"]) == 2
    client_c = _make_client(seeded, "user-c@example.com")
    assert (
        client_c.get("/api/direct-messages/conversations").json()["conversations"]
        == []
    )


def test_self_dm_rejected(seeded):
    client_a, _client_b, profile_a, _profile_b = _two_profiles(seeded)
    response = client_a.post(
        "/api/direct-messages/relationships",
        json={
            "destination_node_id": profile_a["node_id"],
            "destination_profile_id": profile_a["profile_id"],
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "self_direct_message_not_allowed"


def test_nonexistent_recipient_handled_safely(seeded):
    client_a, _client_b, profile_a, _profile_b = _two_profiles(seeded)
    response = client_a.post(
        "/api/direct-messages/relationships",
        json={
            "destination_node_id": profile_a["node_id"],
            "destination_profile_id": uuid.uuid4().hex,
        },
    )
    assert response.status_code == 404
    assert response.json()["detail"]["error"] == "recipient_profile_not_found"


# ── Messaging ─────────────────────────────────────────────────────────────


def _started_conversation(seeded):
    client_a, client_b, profile_a, profile_b = _two_profiles(seeded)
    relationship = client_a.post(
        "/api/direct-messages/relationships",
        json={
            "destination_node_id": profile_b["node_id"],
            "destination_profile_id": profile_b["profile_id"],
        },
    ).json()["relationship"]
    conversation = client_a.post(
        f"/api/direct-messages/relationships/{relationship['relationship_id']}"
        "/conversations",
        json={},
    ).json()["conversation"]
    return client_a, client_b, profile_a, profile_b, conversation


def test_durable_send_reply_and_readback(seeded):
    client_a, client_b, profile_a, profile_b, conversation = _started_conversation(
        seeded
    )
    conversation_id = conversation["conversation_id"]

    sent = client_a.post(
        f"/api/direct-messages/conversations/{conversation_id}/messages",
        json={"body": "hello zac"},
    )
    assert sent.status_code == 200
    message = sent.json()["message"]
    assert sent.json()["replayed"] is False
    assert message["protocol_version"] == "1.0"
    assert message["conversation_id"] == conversation_id
    assert message["message_id"]
    assert message["source"] == {
        "node_id": profile_a["node_id"],
        "profile_id": profile_a["profile_id"],
    }
    assert message["destination"] == {
        "node_id": profile_b["node_id"],
        "profile_id": profile_b["profile_id"],
    }
    assert message["content"] == {"type": "text/plain", "body": "hello zac"}

    # B reads the exact persisted message.
    read_a = client_b.get(
        f"/api/direct-messages/conversations/{conversation_id}/messages"
    )
    assert read_a.status_code == 200
    bodies = [m["content"]["body"] for m in read_a.json()["messages"]]
    assert bodies == ["hello zac"]

    # B replies; A reads both in chronological order.
    reply = client_b.post(
        f"/api/direct-messages/conversations/{conversation_id}/messages",
        json={"body": "hello alice"},
    )
    assert reply.status_code == 200
    assert reply.json()["message"]["source"]["profile_id"] == profile_b["profile_id"]
    read_b = client_a.get(
        f"/api/direct-messages/conversations/{conversation_id}/messages"
    )
    bodies = [m["content"]["body"] for m in read_b.json()["messages"]]
    assert bodies == ["hello zac", "hello alice"]


def test_persistence_survives_reopen(tmp_path):
    db_url = f"sqlite+pysqlite:///{tmp_path / 'dm.db'}"
    engine = _new_engine(db_url)
    session = sessionmaker(bind=engine)()
    _seed_users(session)
    session.close()
    engine.dispose()

    import guardian.messaging.service as service_module

    def _flow(engine):
        db = _FakeDb(engine)
        with db.get_session() as session:
            profile_a = service_module.get_or_create_owned_profile(
                session, "user-a@example.com"
            )
            profile_b = service_module.get_or_create_owned_profile(
                session, "user-b@example.com"
            )
            relationship = service_module.resolve_or_create_relationship(
                session,
                profile_a,
                profile_b.node_id,
                profile_b.profile_id,
            )
            conversation = service_module.create_conversation(
                session, relationship, profile_a
            )
            message, _replayed = service_module.create_message(
                session, conversation, profile_a, "durable text"
            )
            return relationship.id, conversation.id, message.id

    relationship_id, conversation_id, message_id = _flow(engine)

    # Reopen: a fresh engine against the same file, simulating restart.
    engine2 = _new_engine(db_url, create_tables=False)
    try:
        session2 = sessionmaker(bind=engine2)()
        stored = session2.get(DirectMessage, message_id)
        assert stored is not None
        assert stored.body == "durable text"
        assert stored.conversation_id == conversation_id
        conversation = session2.get(DirectMessageConversation, conversation_id)
        assert conversation is not None
        assert conversation.relationship_id == relationship_id
        assert session2.get(DirectMessageRelationship, relationship_id) is not None
        session2.close()
    finally:
        engine2.dispose()


def test_idempotent_replay_does_not_duplicate(seeded):
    client_a, _client_b, _p_a, _p_b, conversation = _started_conversation(seeded)
    conversation_id = conversation["conversation_id"]
    payload = {"body": "sent once", "client_message_key": "client-key-1"}

    first = client_a.post(
        f"/api/direct-messages/conversations/{conversation_id}/messages",
        json=payload,
    )
    assert first.status_code == 200
    assert first.json()["replayed"] is False
    first_id = first.json()["message"]["message_id"]

    replay = client_a.post(
        f"/api/direct-messages/conversations/{conversation_id}/messages",
        json=payload,
    )
    assert replay.status_code == 200
    assert replay.json()["replayed"] is True
    assert replay.json()["message"]["message_id"] == first_id

    with seeded.begin() as connection:
        count = connection.execute(
            select(DirectMessage).where(
                DirectMessage.conversation_id == conversation_id
            )
        ).fetchall()
    assert len(count) == 1

    # A different key creates a genuinely new message.
    third = client_a.post(
        f"/api/direct-messages/conversations/{conversation_id}/messages",
        json={"body": "sent once", "client_message_key": "client-key-2"},
    )
    assert third.status_code == 200
    assert third.json()["replayed"] is False
    assert third.json()["message"]["message_id"] != first_id


def test_blank_and_oversized_messages_rejected(seeded):
    client_a, _client_b, _p_a, _p_b, conversation = _started_conversation(seeded)
    conversation_id = conversation["conversation_id"]

    for payload, code in (
        ({"body": ""}, "message_body_required"),
        ({"body": "   \n  "}, "message_body_required"),
        ({"body": "x" * 32_001}, "message_body_too_large"),
    ):
        response = client_a.post(
            f"/api/direct-messages/conversations/{conversation_id}/messages",
            json=payload,
        )
        assert response.status_code == 422
        assert response.json()["detail"]["error"] == code


def test_pagination_is_bounded_and_deterministic(seeded):
    client_a, client_b, _p_a, _p_b, conversation = _started_conversation(seeded)
    conversation_id = conversation["conversation_id"]
    for index in range(5):
        response = client_a.post(
            f"/api/direct-messages/conversations/{conversation_id}/messages",
            json={"body": f"message-{index}"},
        )
        assert response.status_code == 200

    page = client_b.get(
        f"/api/direct-messages/conversations/{conversation_id}/messages",
        params={"limit": 2},
    )
    bodies = [m["content"]["body"] for m in page.json()["messages"]]
    assert bodies == ["message-0", "message-1"]

    before_id = page.json()["messages"][1]["message_id"]
    earlier = client_b.get(
        f"/api/direct-messages/conversations/{conversation_id}/messages",
        params={"limit": 2, "before_id": before_id},
    )
    assert [m["content"]["body"] for m in earlier.json()["messages"]] == ["message-0"]


# ── Authorization / isolation ─────────────────────────────────────────────


def test_nonparticipant_reads_and_sends_denied(seeded):
    client_a, _client_b, _p_a, _p_b, conversation = _started_conversation(seeded)
    conversation_id = conversation["conversation_id"]
    client_c = _make_client(seeded, "user-c@example.com")

    assert (
        client_c.get(
            f"/api/direct-messages/conversations/{conversation_id}"
        ).status_code
        == 404
    )
    assert (
        client_c.get(
            f"/api/direct-messages/conversations/{conversation_id}/messages"
        ).status_code
        == 404
    )
    send = client_c.post(
        f"/api/direct-messages/conversations/{conversation_id}/messages",
        json={"body": "intruder"},
    )
    assert send.status_code == 404

    # Sender authority is derived from auth, never from the request body.
    impersonation = client_c.post(
        f"/api/direct-messages/conversations/{conversation_id}/messages",
        json={
            "body": "impersonation",
            "client_message_key": "k",
            "sender_profile_id": _p_a["profile_id"],
        },
    )
    assert impersonation.status_code == 404 or impersonation.status_code == 422
    with seeded.begin() as connection:
        rows = connection.execute(
            select(DirectMessage).where(
                DirectMessage.conversation_id == conversation_id
            )
        ).fetchall()
    assert len(rows) == 0


def test_peer_payloads_never_expose_email_or_user_id(seeded):
    client_a, client_b, _p_a, _p_b, conversation = _started_conversation(seeded)
    conversation_id = conversation["conversation_id"]
    client_a.post(
        f"/api/direct-messages/conversations/{conversation_id}/messages",
        json={"body": "hello zac"},
    )

    surfaces = [
        client_b.get("/api/direct-messages/profiles", params={"q": "alice"}).json(),
        client_b.get(f"/api/direct-messages/conversations/{conversation_id}").json(),
        client_b.get(
            f"/api/direct-messages/conversations/{conversation_id}/messages"
        ).json(),
        client_b.get("/api/direct-messages/conversations").json(),
    ]

    def _forbidden(node, path="root"):
        if isinstance(node, dict):
            for key, value in node.items():
                assert key not in {
                    "email",
                    "user_id",
                    "owning_user_id",
                    "password_hash",
                }, f"forbidden key {key!r} at {path}"
                _forbidden(value, f"{path}.{key}")
        elif isinstance(node, list):
            for index, item in enumerate(node):
                _forbidden(item, f"{path}[{index}]")

    for surface in surfaces:
        _forbidden(surface)

    # A's own identity view is the only place its user_id-adjacent data may
    # not appear, and it must not either — social identity only.
    own = client_a.get("/api/profile/social-identity").json()
    assert "email" not in str(own)
    assert "user_id" not in own.get("profile", {})


def test_conversation_payload_carries_caller_relative_peer(seeded):
    """The conversation payload exposes the OTHER participant as `peer`,
    mirroring the relationship payload shape, so the portable floating
    window can title itself without guessing from participant order."""
    client_a, client_b, profile_a, profile_b, conversation = _started_conversation(
        seeded
    )
    conversation_id = conversation["conversation_id"]

    alice_view = client_a.get(
        f"/api/direct-messages/conversations/{conversation_id}"
    ).json()["conversation"]
    bob_view = client_b.get(
        f"/api/direct-messages/conversations/{conversation_id}"
    ).json()["conversation"]

    assert alice_view["peer"]["profile_id"] == profile_b["profile_id"]
    assert bob_view["peer"]["profile_id"] == profile_a["profile_id"]
    # `participants` still carries both profiles (no regression).
    assert {p["profile_id"] for p in alice_view["participants"]} == {
        profile_a["profile_id"],
        profile_b["profile_id"],
    }


def test_dm_source_never_touches_guardian_chat_or_federation(seeded):
    """Structural isolation: the DM domain imports none of the Guardian
    chat, memory, embedding, Hosted Room, or federation machinery."""
    import ast

    sources = {
        REPO_ROOT / "guardian" / "routes" / "direct_messages.py",
        REPO_ROOT / "guardian" / "messaging" / "__init__.py",
        REPO_ROOT / "guardian" / "messaging" / "tokens.py",
        REPO_ROOT / "guardian" / "messaging" / "envelope.py",
        REPO_ROOT / "guardian" / "messaging" / "service.py",
    }
    forbidden_prefixes = (
        "guardian.core.chat",
        "guardian.core.hosted_room",
        "guardian.core.memory",
        "guardian.federation",
        "guardian.routes.federation",
        "backend.rag",
        "backend.embeddings",
        "guardian.memory",
        "guardian.embeddings",
    )
    for path in sources:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)
        for module in imports:
            assert not module.startswith(
                forbidden_prefixes
            ), f"{module!r} imported by {path.name}"


# ── Route posture ─────────────────────────────────────────────────────────


@pytest.fixture
def friends_family_app(monkeypatch, tmp_path):
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-api-key")
    monkeypatch.setenv("ENABLE_CONNECTOR_WORKER", "0")
    monkeypatch.setenv("CODEXIFY_SUPPORTED_PROFILE", "v1-friends-family-web")
    monkeypatch.setenv("CODEXIFY_EMBEDDINGS_BACKEND", "mock")
    monkeypatch.setenv("STORAGE_BASE_PATH", str(tmp_path / "media"))

    import guardian.guardian_api as guardian_api

    guardian_api = importlib.reload(guardian_api)
    try:
        yield guardian_api
    finally:
        monkeypatch.setenv("CODEXIFY_SUPPORTED_PROFILE", "v1-local-core-web-mcp")
        importlib.reload(guardian_api)


@pytest.fixture
def default_profile_app(monkeypatch, tmp_path):
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-api-key")
    monkeypatch.setenv("ENABLE_CONNECTOR_WORKER", "0")
    monkeypatch.setenv("CODEXIFY_SUPPORTED_PROFILE", "v1-local-core-web-mcp")
    monkeypatch.setenv("CODEXIFY_EMBEDDINGS_BACKEND", "mock")
    monkeypatch.setenv("STORAGE_BASE_PATH", str(tmp_path / "media"))

    import guardian.guardian_api as guardian_api

    guardian_api = importlib.reload(guardian_api)
    try:
        yield guardian_api
    finally:
        importlib.reload(guardian_api)


def test_direct_messages_enabled_on_hosted_test_profile(friends_family_app):
    guardian_api = friends_family_app
    enabled = guardian_api.app.state.supported_profile_enabled_labels
    assert "direct_messages" in enabled
    paths = set(guardian_api.app.openapi().get("paths", {}))
    assert "/api/direct-messages/conversations" in paths
    assert "/api/direct-messages/relationships" in paths
    assert "/api/direct-messages/profiles" in paths
    assert "/api/profile/social-identity" in paths


def test_direct_messages_quarantined_on_default_profile(default_profile_app):
    guardian_api = default_profile_app
    enabled = getattr(guardian_api.app.state, "supported_profile_enabled_labels", set())
    assert "direct_messages" not in enabled
    paths = set(guardian_api.app.openapi().get("paths", {}))
    assert "/api/direct-messages/conversations" not in paths
    assert "/api/direct-messages/relationships" not in paths
    assert "/api/profile/social-identity" not in paths


# ── Inbox projection (latest-message preview + listing privacy) ──────────


def _inbox_relationship(client_a, client_b, profile_a, profile_b):
    return client_a.post(
        "/api/direct-messages/relationships",
        json={
            "destination_node_id": profile_b["node_id"],
            "destination_profile_id": profile_b["profile_id"],
        },
    ).json()["relationship"]


def _inbox_conversation(client_a, relationship_id, body=None):
    response = client_a.post(
        f"/api/direct-messages/relationships/{relationship_id}/conversations",
        json=body or {},
    )
    assert response.status_code == 200
    return response.json()["conversation"]


def _inbox_send(client, conversation_id, body, key=None):
    payload = {"body": body}
    if key is not None:
        payload["client_message_key"] = key
    response = client.post(
        f"/api/direct-messages/conversations/{conversation_id}/messages",
        json=payload,
    )
    assert response.status_code == 200
    return response.json()


def test_inbox_listing_is_participant_scoped_and_third_party_gets_404(seeded):
    client_a, client_b, profile_a, profile_b = _two_profiles(seeded)
    client_c = _make_client(seeded, "user-c@example.com")
    _claim_username(client_c, "carol")
    relationship_id = _inbox_relationship(
        client_a, client_b, profile_a, profile_b
    )["relationship_id"]
    first = _inbox_conversation(client_a, relationship_id)
    second = _inbox_conversation(client_a, relationship_id)

    a_listing = client_a.get("/api/direct-messages/conversations").json()[
        "conversations"
    ]
    b_listing = client_b.get("/api/direct-messages/conversations").json()[
        "conversations"
    ]
    assert {c["conversation_id"] for c in a_listing} == {
        first["conversation_id"],
        second["conversation_id"],
    }
    assert {c["conversation_id"] for c in b_listing} == {
        first["conversation_id"],
        second["conversation_id"],
    }

    assert client_c.get("/api/direct-messages/conversations").json()[
        "conversations"
    ] == []
    denied = client_c.get(
        f"/api/direct-messages/conversations/{first['conversation_id']}"
    )
    assert denied.status_code == 404
    assert denied.json()["detail"]["error"] == "conversation_not_found"


def test_inbox_three_conversations_stay_distinct_with_stable_relationship(seeded):
    client_a, client_b, profile_a, profile_b = _two_profiles(seeded)
    relationship_id = _inbox_relationship(
        client_a, client_b, profile_a, profile_b
    )["relationship_id"]

    first = _inbox_conversation(client_a, relationship_id)
    second = _inbox_conversation(client_a, relationship_id)
    third = _inbox_conversation(client_a, relationship_id)

    ids = [
        first["conversation_id"],
        second["conversation_id"],
        third["conversation_id"],
    ]
    assert len(set(ids)) == 3
    for conversation in (first, second, third):
        assert conversation["relationship_id"] == relationship_id

    listing = client_a.get("/api/direct-messages/conversations").json()[
        "conversations"
    ]
    assert [c["conversation_id"] for c in listing] == list(reversed(ids))
    for conversation in listing:
        assert conversation["relationship_id"] == relationship_id


def test_inbox_latest_message_projection_matches_its_conversation(seeded):
    client_a, client_b, profile_a, profile_b = _two_profiles(seeded)
    relationship_id = _inbox_relationship(
        client_a, client_b, profile_a, profile_b
    )["relationship_id"]
    first = _inbox_conversation(client_a, relationship_id)
    second = _inbox_conversation(client_a, relationship_id)

    sent_first = _inbox_send(client_a, first["conversation_id"], "hello one")
    sent_second_a = _inbox_send(client_b, second["conversation_id"], "hello two-a")
    sent_second_b = _inbox_send(
        client_a, second["conversation_id"], "hello two-b final"
    )

    listing = {
        c["conversation_id"]: c
        for c in client_a.get("/api/direct-messages/conversations").json()[
            "conversations"
        ]
    }
    assert listing[first["conversation_id"]]["latest_message"]["message_id"] == (
        sent_first["message"]["message_id"]
    )
    assert listing[second["conversation_id"]]["latest_message"]["message_id"] == (
        sent_second_b["message"]["message_id"]
    )
    assert listing[first["conversation_id"]]["latest_message"]["preview"] == "hello one"
    assert (
        listing[second["conversation_id"]]["latest_message"]["preview"]
        == "hello two-b final"
    )
    assert (
        listing[second["conversation_id"]]["latest_message"]["sender_profile_id"]
        == profile_a["profile_id"]
    )
    # A conversation without messages projects a null latest_message.
    empty = _inbox_conversation(client_a, relationship_id)
    refreshed = {
        c["conversation_id"]: c
        for c in client_a.get("/api/direct-messages/conversations").json()[
            "conversations"
        ]
    }
    assert refreshed[empty["conversation_id"]]["latest_message"] is None


def test_inbox_latest_message_preview_is_bounded(seeded):
    client_a, client_b, profile_a, profile_b = _two_profiles(seeded)
    relationship_id = _inbox_relationship(
        client_a, client_b, profile_a, profile_b
    )["relationship_id"]
    conversation = _inbox_conversation(client_a, relationship_id)
    long_body = ("word " * 40).strip()  # > 160 chars once joined with spaces
    assert len(long_body) > 160
    _inbox_send(client_a, conversation["conversation_id"], long_body)

    listing = client_a.get("/api/direct-messages/conversations").json()[
        "conversations"
    ]
    preview = next(
        c["latest_message"]["preview"]
        for c in listing
        if c["conversation_id"] == conversation["conversation_id"]
    )
    assert len(preview) == 161
    assert preview.endswith("…")
    assert preview.startswith(long_body[:150])


def test_inbox_activity_ordering_is_deterministic(seeded):
    client_a, client_b, profile_a, profile_b = _two_profiles(seeded)
    relationship_id = _inbox_relationship(
        client_a, client_b, profile_a, profile_b
    )["relationship_id"]
    first = _inbox_conversation(client_a, relationship_id)
    second = _inbox_conversation(client_a, relationship_id)

    # No activity: newest conversation first (server order, id desc).
    listing = client_a.get("/api/direct-messages/conversations").json()[
        "conversations"
    ]
    assert [c["conversation_id"] for c in listing] == [
        second["conversation_id"],
        first["conversation_id"],
    ]

    # Activity on the older conversation moves it to the top.
    _inbox_send(client_b, first["conversation_id"], "bump")
    listing = client_a.get("/api/direct-messages/conversations").json()[
        "conversations"
    ]
    assert [c["conversation_id"] for c in listing] == [
        first["conversation_id"],
        second["conversation_id"],
    ]
    assert listing[0]["latest_message"]["preview"] == "bump"


def test_inbox_payload_never_exposes_email_or_user_id(seeded):
    client_a, client_b, profile_a, profile_b = _two_profiles(seeded)
    relationship_id = _inbox_relationship(
        client_a, client_b, profile_a, profile_b
    )["relationship_id"]
    conversation = _inbox_conversation(client_a, relationship_id)
    _inbox_send(client_a, conversation["conversation_id"], "private hello")

    surfaces = [
        client_a.get("/api/direct-messages/conversations").json(),
        client_b.get("/api/direct-messages/conversations").json(),
        client_a.get(
            f"/api/direct-messages/conversations/{conversation['conversation_id']}"
        ).json(),
        client_a.get("/api/direct-messages/relationships").json(),
    ]

    def _forbidden(node, path="root"):
        if isinstance(node, dict):
            for key, value in node.items():
                assert key not in {"email", "user_id", "owning_user_id"}, (
                    f"forbidden key {key!r} at {path}"
                )
                _forbidden(value, f"{path}.{key}")
        elif isinstance(node, list):
            for index, item in enumerate(node):
                _forbidden(item, f"{path}[{index}]")
        elif isinstance(node, str):
            assert "@" not in node and node != "user-a@example.com", (
                f"suspicious string at {path}"
            )

    for surface in surfaces:
        _forbidden(surface)


def test_inbox_hides_unauthorized_origin_from_peer_listing(seeded):
    client_a, client_b, profile_a, profile_b = _two_profiles(seeded)
    relationship_id = _inbox_relationship(
        client_a, client_b, profile_a, profile_b
    )["relationship_id"]
    conversation = _inbox_conversation(
        client_a, relationship_id, body={"origin_project_id": 101}
    )

    a_listing = client_a.get("/api/direct-messages/conversations").json()[
        "conversations"
    ]
    b_listing = client_b.get("/api/direct-messages/conversations").json()[
        "conversations"
    ]
    a_row = next(
        c for c in a_listing if c["conversation_id"] == conversation["conversation_id"]
    )
    b_row = next(
        c for c in b_listing if c["conversation_id"] == conversation["conversation_id"]
    )
    assert a_row["origin"]["origin_project_id"] == 101
    assert b_row["origin"]["origin_project_id"] is None
    assert b_row["origin"]["origin_thread_id"] is None


def test_inbox_never_exposes_peer_placement(seeded):
    client_a, client_b, profile_a, profile_b = _two_profiles(seeded)
    relationship_id = _inbox_relationship(
        client_a, client_b, profile_a, profile_b
    )["relationship_id"]
    conversation = _inbox_conversation(client_a, relationship_id)

    moved = client_a.patch(
        f"/api/direct-messages/conversations/{conversation['conversation_id']}/placement",
        json={"project_id": 101},
    )
    assert moved.status_code == 200

    a_listing = client_a.get("/api/direct-messages/conversations").json()[
        "conversations"
    ]
    b_listing = client_b.get("/api/direct-messages/conversations").json()[
        "conversations"
    ]
    a_row = next(
        c for c in a_listing if c["conversation_id"] == conversation["conversation_id"]
    )
    b_row = next(
        c for c in b_listing if c["conversation_id"] == conversation["conversation_id"]
    )
    assert a_row["placement"]["project_id"] == 101
    assert b_row["placement"]["project_id"] is None
    assert "peer_placement" not in a_row
    assert "peer_placement" not in b_row


def test_inbox_participant_local_placement_stays_isolated(seeded):
    client_a, client_b, profile_a, profile_b = _two_profiles(seeded)
    relationship_id = _inbox_relationship(
        client_a, client_b, profile_a, profile_b
    )["relationship_id"]
    conversation = _inbox_conversation(client_a, relationship_id)

    client_b.patch(
        f"/api/direct-messages/conversations/{conversation['conversation_id']}/placement",
        json={"project_id": 201},
    )

    a_listing = client_a.get("/api/direct-messages/conversations").json()[
        "conversations"
    ]
    a_row = next(
        c for c in a_listing if c["conversation_id"] == conversation["conversation_id"]
    )
    assert a_row["placement"]["project_id"] is None
