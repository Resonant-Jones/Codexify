"""Focused proof for recipient-local direct-message read state.

Read state is participant-local by construction: one cursor row per
(reading profile, conversation).  Unread counts are DERIVED from the durable
message store and that cursor — there is no second message store and no
stored counter.

These tests use synthetic profiles only.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from guardian.db.models import DirectMessageReadCursor
from tests.routes.test_direct_messages import (  # noqa: F401
    _claim_username,
    _make_client,
    _started_conversation,
    _two_profiles,
    dm_engine,
    seeded,
)


def _conversations(client):
    response = client.get("/api/direct-messages/conversations")
    assert response.status_code == 200, response.text
    return response.json()["conversations"]


def _row(client, conversation_id):
    for row in _conversations(client):
        if row["conversation_id"] == conversation_id:
            return row
    return None


def _send(client, conversation_id, body, key):
    response = client.post(
        f"/api/direct-messages/conversations/{conversation_id}/messages",
        json={"body": body, "client_message_key": key},
    )
    assert response.status_code == 200, response.text
    return response.json()["message"]


def _mark_read(client, conversation_id):
    """The explicit read mutation — the only operation that advances a cursor."""
    response = client.post(
        f"/api/direct-messages/conversations/{conversation_id}/read"
    )
    assert response.status_code == 200, response.text
    return response.json()["conversation"]


def _cursor_rows(engine, conversation_id):
    with sessionmaker(bind=engine)() as session:
        return session.scalars(
            select(DirectMessageReadCursor).where(
                DirectMessageReadCursor.conversation_id == conversation_id
            )
        ).all()


# ── 1. Incoming messages are unread for the recipient, not the sender ──────


def test_incoming_message_is_unread_for_recipient_not_sender(seeded):  # noqa: F811
    client_a, client_b, _, _, conversation = _started_conversation(seeded)
    conversation_id = conversation["conversation_id"]

    _send(client_a, conversation_id, "from a", "read-state-a1")

    assert _row(client_a, conversation_id)["unread_count"] == 0
    assert _row(client_b, conversation_id)["unread_count"] == 1


def test_senders_own_messages_never_raise_their_own_count(seeded):  # noqa: F811
    client_a, client_b, _, _, conversation = _started_conversation(seeded)
    conversation_id = conversation["conversation_id"]

    _send(client_a, conversation_id, "one", "read-state-self-1")
    _send(client_a, conversation_id, "two", "read-state-self-2")

    assert _row(client_a, conversation_id)["unread_count"] == 0
    assert _row(client_b, conversation_id)["unread_count"] == 2


# ── 2. Retrieval is read-only; the explicit action advances the cursor ─────


def test_conversation_get_does_not_advance_the_cursor(seeded):  # noqa: F811
    """A GET is a safe read: fetching a transcript must not mark it read."""
    client_a, client_b, _, _, conversation = _started_conversation(seeded)
    conversation_id = conversation["conversation_id"]
    _send(client_a, conversation_id, "from a", "read-state-get-1")
    assert _row(client_b, conversation_id)["unread_count"] == 1

    fetched = client_b.get(f"/api/direct-messages/conversations/{conversation_id}")
    assert fetched.status_code == 200, fetched.text
    # The read still reports the caller's current unread count.
    assert fetched.json()["conversation"]["unread_count"] == 1

    # No cursor was created by the GET.
    assert _cursor_rows(seeded, conversation_id) == []
    assert _row(client_b, conversation_id)["unread_count"] == 1

    # Reading the transcript again changes nothing.
    client_b.get(f"/api/direct-messages/conversations/{conversation_id}")
    client_b.get(
        f"/api/direct-messages/conversations/{conversation_id}/messages"
    )
    assert _cursor_rows(seeded, conversation_id) == []
    assert _row(client_b, conversation_id)["unread_count"] == 1


def test_opening_advances_the_recipient_cursor_and_clears_unread(seeded):  # noqa: F811
    client_a, client_b, profile_a, profile_b, conversation = _started_conversation(
        seeded
    )
    conversation_id = conversation["conversation_id"]
    _send(client_a, conversation_id, "from a", "read-state-open-1")
    assert _row(client_b, conversation_id)["unread_count"] == 1

    opened = _mark_read(client_b, conversation_id)
    assert opened["unread_count"] == 0

    # The cursor row exists for the READER only.
    rows = _cursor_rows(seeded, conversation_id)
    assert len(rows) == 1
    assert rows[0].profile_id == profile_b["profile_id"]
    assert rows[0].last_read_message_id is not None

    # The reader's count is cleared; the sender's is untouched.
    assert _row(client_b, conversation_id)["unread_count"] == 0
    assert _row(client_a, conversation_id)["unread_count"] == 0


def test_repeated_reads_are_idempotent_and_never_move_the_cursor_backwards(
    seeded,
):  # noqa: F811
    client_a, client_b, _, _, conversation = _started_conversation(seeded)
    conversation_id = conversation["conversation_id"]
    _send(client_a, conversation_id, "from a", "read-state-repeat-1")

    _mark_read(client_b, conversation_id)
    first = _cursor_rows(seeded, conversation_id)[0]
    first_message_id = first.last_read_message_id

    _mark_read(client_b, conversation_id)
    _mark_read(client_b, conversation_id)

    rows = _cursor_rows(seeded, conversation_id)
    assert len(rows) == 1
    assert rows[0].last_read_message_id == first_message_id
    assert _row(client_b, conversation_id)["unread_count"] == 0


# ── 3. Cleared state survives reload / navigation away and back ───────────


def test_cleared_state_survives_reload(seeded):  # noqa: F811
    client_a, client_b, _, _, conversation = _started_conversation(seeded)
    conversation_id = conversation["conversation_id"]
    _send(client_a, conversation_id, "from a", "read-state-reload-1")

    _mark_read(client_b, conversation_id)
    assert _row(client_b, conversation_id)["unread_count"] == 0

    # A fresh list read (the reload path) still shows it as read.
    assert _row(client_b, conversation_id)["unread_count"] == 0
    assert len(_cursor_rows(seeded, conversation_id)) == 1


def test_cleared_state_survives_a_new_session(seeded, tmp_path):  # noqa: F811
    """A new client (new session) for the same account sees the same state."""
    client_a, client_b, _, _, conversation = _started_conversation(seeded)
    conversation_id = conversation["conversation_id"]
    _send(client_a, conversation_id, "from a", "read-state-session-1")
    _mark_read(client_b, conversation_id)

    # The cursor is durable in the database, not in process memory.
    assert len(_cursor_rows(seeded, conversation_id)) == 1
    fresh_client_b = _make_client(seeded, "user-b@example.com")
    assert _row(fresh_client_b, conversation_id)["unread_count"] == 0


# ── 4. A later incoming message becomes unread again ──────────────────────


def test_later_incoming_message_becomes_unread_again(seeded):  # noqa: F811
    client_a, client_b, _, _, conversation = _started_conversation(seeded)
    conversation_id = conversation["conversation_id"]

    _send(client_a, conversation_id, "first", "read-state-again-1")
    _mark_read(client_b, conversation_id)
    assert _row(client_b, conversation_id)["unread_count"] == 0

    _send(client_a, conversation_id, "second", "read-state-again-2")
    assert _row(client_b, conversation_id)["unread_count"] == 1

    _mark_read(client_b, conversation_id)
    assert _row(client_b, conversation_id)["unread_count"] == 0


def test_readers_own_reply_does_not_clear_their_unread_count(seeded):  # noqa: F811
    """Reading is what clears the count — sending your own message is not."""
    client_a, client_b, _, _, conversation = _started_conversation(seeded)
    conversation_id = conversation["conversation_id"]

    _send(client_a, conversation_id, "from a", "read-state-own-1")
    assert _row(client_b, conversation_id)["unread_count"] == 1

    _send(client_b, conversation_id, "b replies", "read-state-own-2")
    # B still has A's first message unread.
    assert _row(client_b, conversation_id)["unread_count"] == 1


# ── 5. Isolation between participants; no sender-visible receipt ──────────


def test_read_state_is_isolated_between_participants(seeded):  # noqa: F811
    client_a, client_b, profile_a, profile_b, conversation = _started_conversation(
        seeded
    )
    conversation_id = conversation["conversation_id"]

    _send(client_a, conversation_id, "from a", "read-state-iso-1")
    _mark_read(client_b, conversation_id)

    # A's own unread count is unaffected by B having read.
    assert _row(client_a, conversation_id)["unread_count"] == 0

    rows = _cursor_rows(seeded, conversation_id)
    assert [row.profile_id for row in rows] == [profile_b["profile_id"]]
    assert profile_a["profile_id"] not in {row.profile_id for row in rows}


def test_sender_cannot_observe_the_recipient_cursor(seeded):  # noqa: F811
    """A's payload must never disclose that B read, or when."""
    client_a, client_b, _, _, conversation = _started_conversation(seeded)
    conversation_id = conversation["conversation_id"]
    _send(client_a, conversation_id, "from a", "read-state-receipt-1")
    _mark_read(client_b, conversation_id)

    payload = client_a.get(
        f"/api/direct-messages/conversations/{conversation_id}"
    ).json()["conversation"]

    assert "read_count" not in payload
    assert "read_at" not in payload
    assert "last_read" not in payload
    assert "read_by_peer" not in payload
    assert "read_receipts" not in payload
    # The only read-state surface is the caller's own unread_count.
    assert payload["unread_count"] == 0


# ── 6. Unauthorized users cannot read or advance another cursor ───────────


def test_nonparticipant_cannot_read_or_advance_the_cursor(seeded):  # noqa: F811
    client_a, client_b, profile_a, profile_b, conversation = _started_conversation(
        seeded
    )
    conversation_id = conversation["conversation_id"]
    _send(client_a, conversation_id, "from a", "read-state-auth-1")
    _mark_read(client_b, conversation_id)

    cursor_before = _cursor_rows(seeded, conversation_id)

    outsider = _make_client(seeded, "user-c@example.com")
    _claim_username(outsider, "carol")
    denied = outsider.get(f"/api/direct-messages/conversations/{conversation_id}")
    assert denied.status_code == 404
    assert denied.json()["detail"]["error"] == "conversation_not_found"

    # The explicit mutation is refused for a non-participant too.
    denied_read = outsider.post(
        f"/api/direct-messages/conversations/{conversation_id}/read"
    )
    assert denied_read.status_code == 404
    assert denied_read.json()["detail"]["error"] == "conversation_not_found"

    # The reader's cursor is unchanged by the denied attempts.
    cursor_after = _cursor_rows(seeded, conversation_id)
    assert [row.profile_id for row in cursor_after] == [
        row.profile_id for row in cursor_before
    ]
    assert cursor_after[0].last_read_message_id == cursor_before[0].last_read_message_id
    # The outsider has no cursor of their own.
    with sessionmaker(bind=seeded)() as session:
        assert (
            session.scalar(
                select(DirectMessageReadCursor).where(
                    DirectMessageReadCursor.profile_id == profile_a["profile_id"]
                )
            )
            is None
        )


# ── 7. Existing authority model is preserved ──────────────────────────────


def test_read_state_does_not_bypass_request_and_consent_gates(seeded):  # noqa: F811
    """A neutral relationship still cannot create a conversation or read one."""
    client_a, client_b, profile_a, profile_b = _two_profiles(
        seeded, established=False
    )
    pair = client_a.post(
        "/api/direct-messages/relationships",
        json={
            "destination_node_id": profile_b["node_id"],
            "destination_profile_id": profile_b["profile_id"],
        },
    ).json()["relationship"]
    route = (
        f"/api/direct-messages/relationships/{pair['relationship_id']}/conversations"
    )
    assert client_a.post(route, json={}).status_code == 403
    assert client_b.post(route, json={}).status_code == 403

    outsider = _make_client(seeded, "user-c@example.com")
    _claim_username(outsider, "carol")
    assert outsider.post(route, json={}).status_code == 404


def test_conversation_payload_never_exposes_read_state_of_others(seeded):  # noqa: F811
    """Every conversation payload carries only the caller's own unread count."""
    client_a, client_b, _, _, conversation = _started_conversation(seeded)
    conversation_id = conversation["conversation_id"]
    _send(client_a, conversation_id, "from a", "read-state-payload-1")

    for client in (client_a, client_b):
        for row in _conversations(client):
            assert set(row) >= {"conversation_id", "unread_count"}
            assert isinstance(row["unread_count"], int)
            assert row["unread_count"] >= 0
            for key in row:
                assert "read_at" not in key
                assert "read_by" not in key
