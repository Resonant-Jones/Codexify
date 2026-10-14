"""Real route/service consent proof; PostgreSQL race proof is separate."""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import event, func, select, update
from sqlalchemy.orm import Session

from guardian.db.models import (
    DirectMessage,
    DirectMessageConsent,
    DirectMessageConversation,
    DirectMessageConversationPlacement,
    DirectMessageRelationship,
    MessageRequest,
    MessageRequestAttempt,
    MessageRequestSuppression,
    UserProfile,
)
from guardian.messaging import requests as domain
from tests.routes.test_direct_messages import (
    _claim_username,
    _make_client,
    _two_profiles,
    dm_engine,
    seeded,
)


def _send(client, peer, note="Hello from A", key="attempt-a"):
    return client.post(
        "/api/direct-messages/requests",
        json={
            "destination_node_id": peer["node_id"],
            "destination_profile_id": peer["profile_id"],
            "note": note,
            "client_request_key": key,
        },
    )


def _new_pair(seeded):
    return _two_profiles(seeded, established=False)


def _pending(seeded):
    a, b, pa, pb = _new_pair(seeded)
    response = _send(a, pb)
    assert response.status_code == 200, response.text
    return a, b, pa, pb, response.json()["request"]


def _count(session, model):
    return session.scalar(select(func.count()).select_from(model))


def test_neutral_relationship_cannot_bypass_consent(seeded):
    a, b, pa, pb = _new_pair(seeded)
    pair = a.post(
        "/api/direct-messages/relationships",
        json={
            "destination_node_id": pb["node_id"],
            "destination_profile_id": pb["profile_id"],
        },
    ).json()["relationship"]
    route = (
        f"/api/direct-messages/relationships/{pair['relationship_id']}/conversations"
    )
    assert a.post(route, json={}).status_code == 403
    assert b.post(route, json={}).status_code == 403
    c = _make_client(seeded, "user-c@example.com")
    assert c.post(route, json={}).status_code == 404
    with Session(seeded) as session:
        assert _count(session, DirectMessageRelationship) == 1
        assert _count(session, DirectMessageConversation) == 0
        assert _count(session, DirectMessageConsent) == 0


def test_discover_request_accept_converse_and_durable_readback(seeded):
    a, b, pa, pb, request = _pending(seeded)
    assert request["state"] == "pending"
    assert request["conversation_id"] is None
    assert a.get("/api/direct-messages/requests").json()["requests"][0]["outgoing"]
    assert not b.get("/api/direct-messages/requests").json()["requests"][0]["outgoing"]
    discovery = a.get("/api/direct-messages/profiles", params={"q": "bob"}).json()[
        "profiles"
    ]
    assert discovery[0]["profile_id"] == pb["profile_id"]
    for result in (discovery, request, b.get("/api/direct-messages/requests").json()):
        assert "@example.com" not in str(result)
        assert "user_id" not in str(result)
        assert "origin_project_id" not in str(result)
    accepted = b.post(f"/api/direct-messages/requests/{request['request_id']}/accept")
    assert accepted.status_code == 200, accepted.text
    accepted = accepted.json()["request"]
    assert accepted["state"] == "accepted"
    conv = accepted["conversation_id"]
    with Session(seeded) as session:
        assert _count(session, DirectMessageConversation) == 1
        assert _count(session, DirectMessage) == 1
        assert _count(session, DirectMessageConversationPlacement) == 2
        assert (
            session.get(DirectMessage, accepted["first_message_id"]).sender_profile_id
            == pa["profile_id"]
        )
        consent = session.get(DirectMessageConsent, request["relationship_id"])
        assert (consent.source, consent.request_id) == (
            "accepted_request",
            request["request_id"],
        )
    for client, body, key in ((a, "A reply", "a-message"), (b, "B reply", "b-message")):
        response = client.post(
            f"/api/direct-messages/conversations/{conv}/messages",
            json={"body": body, "client_message_key": key},
        )
        assert response.status_code == 200
    for client in (a, b):
        messages = client.get(
            f"/api/direct-messages/conversations/{conv}/messages"
        ).json()["messages"]
        assert [m["content"]["body"] for m in messages] == [
            "Hello from A",
            "A reply",
            "B reply",
        ]
        assert messages[0]["source"]["profile_id"] == pa["profile_id"]
        assert client.get("/api/direct-messages/requests").json()["requests"] == []
    c = _make_client(seeded, "user-c@example.com")
    assert c.get("/api/direct-messages/relationships").json()["relationships"] == []
    assert c.get(f"/api/direct-messages/conversations/{conv}").status_code == 404
    assert (
        c.get(f"/api/direct-messages/conversations/{conv}/messages").status_code == 404
    )


def test_duplicate_attempt_and_pending_direction(seeded):
    a, b, pa, pb, request = _pending(seeded)
    repeated = _send(a, pb)
    assert repeated.json()["replayed"] is True
    assert repeated.json()["request"]["request_id"] == request["request_id"]
    equivalent = _send(a, pb, key="another-key")
    assert equivalent.status_code == 200
    assert equivalent.json()["request"]["request_id"] == request["request_id"]
    assert _send(a, pb, note="Changed text").status_code == 409
    assert _send(a, pb, note="Other intro", key="other-attempt").status_code == 409
    with Session(seeded) as session:
        assert _count(session, MessageRequest) == 1
        assert _count(session, MessageRequestAttempt) == 2
        assert _count(session, DirectMessageConversation) == 0


@pytest.mark.parametrize(
    "action,actor",
    [
        ("accept", "sender"),
        ("decline", "sender"),
        ("withdraw", "recipient"),
        ("accept", "stranger"),
        ("decline", "stranger"),
        ("withdraw", "stranger"),
    ],
)
def test_transition_actor_boundary_no_existence_leak(seeded, action, actor):
    a, b, pa, pb, request = _pending(seeded)
    client = (
        a
        if actor == "sender"
        else b
        if actor == "recipient"
        else _make_client(seeded, "user-c@example.com")
    )
    denied = client.post(
        f"/api/direct-messages/requests/{request['request_id']}/{action}"
    )
    absent = client.post(f"/api/direct-messages/requests/not-a-request/{action}")
    assert denied.status_code == absent.status_code == 404
    assert denied.json() == absent.json()
    with Session(seeded) as session:
        assert session.get(MessageRequest, request["request_id"]).state == "pending"
        assert _count(session, DirectMessage) == 0


def test_acceptance_retry_materializes_once_and_preserves_chronology(seeded):
    a, b, pa, pb, request = _pending(seeded)
    old_time = datetime.now(timezone.utc) - timedelta(days=2)
    with Session(seeded) as session:
        stored = session.get(MessageRequest, request["request_id"])
        stored.created_at = old_time
        session.commit()
    path = f"/api/direct-messages/requests/{request['request_id']}/accept"
    accepted = b.post(path).json()["request"]
    repeat = b.post(path).json()
    assert repeat["replayed"] is True
    assert repeat["request"]["conversation_id"] == accepted["conversation_id"]
    with Session(seeded) as session:
        assert (
            _count(session, DirectMessageConversation)
            == _count(session, DirectMessage)
            == 1
        )
        stored = session.get(MessageRequest, request["request_id"])
        first = session.get(DirectMessage, stored.first_message_id)
        assert first.created_at == stored.transitioned_at
        assert stored.created_at < first.created_at
        assert first.sender_profile_id == pa["profile_id"]
    assert _send(a, pb).json()["replayed"] is True
    assert _send(a, pb, key="new-solicitation").status_code == 400
    assert (
        a.post(
            f"/api/direct-messages/relationships/{request['relationship_id']}/conversations",
            json={},
        ).status_code
        == 200
    )


def test_acceptance_rollback_has_no_partial_conversation_message_or_consent(
    seeded, monkeypatch
):
    a, b, pa, pb, request = _pending(seeded)
    original = domain._materialize

    def fail_after_staging(*args):
        original(*args)
        raise RuntimeError("injected before commit")

    monkeypatch.setattr(domain, "_materialize", fail_after_staging)
    with pytest.raises(RuntimeError, match="injected before commit"):
        b.post(f"/api/direct-messages/requests/{request['request_id']}/accept")
    with Session(seeded) as session:
        assert session.get(MessageRequest, request["request_id"]).state == "pending"
        assert _count(session, DirectMessageConversation) == 0
        assert _count(session, DirectMessage) == 0
        assert _count(session, DirectMessageConsent) == 0
        assert _count(session, DirectMessageConversationPlacement) == 0
    monkeypatch.setattr(domain, "_materialize", original)
    assert (
        b.post(
            f"/api/direct-messages/requests/{request['request_id']}/accept"
        ).status_code
        == 200
    )


def test_reverse_initiation_accepts_original_note_and_retains_reverse_note(seeded):
    a, b, pa, pb, request = _pending(seeded)
    reverse = _send(b, pa, note="Hello from B", key="attempt-b")
    assert reverse.status_code == 200, reverse.text
    result = reverse.json()["request"]
    assert result["request_id"] == request["request_id"]
    assert result["state"] == "accepted"
    assert _send(b, pa, note="Hello from B", key="attempt-b").json()["replayed"] is True
    assert (
        b.post(f"/api/direct-messages/requests/{request['request_id']}/accept").json()[
            "replayed"
        ]
        is True
    )
    with Session(seeded) as session:
        assert (
            _count(session, MessageRequest)
            == _count(session, DirectMessageConversation)
            == 1
        )
        messages = session.scalars(
            select(DirectMessage).order_by(DirectMessage.created_at, DirectMessage.id)
        ).all()
        assert [(m.sender_profile_id, m.body) for m in messages] == [
            (pa["profile_id"], "Hello from A"),
            (pb["profile_id"], "Hello from B"),
        ]


def test_decline_separate_suppression_generic_failure_and_recipient_reinitiation(
    seeded,
):
    a, b, pa, pb, request = _pending(seeded)
    path = f"/api/direct-messages/requests/{request['request_id']}"
    assert b.post(path + "/decline").json()["request"]["state"] == "declined"
    assert b.post(path + "/decline").json()["replayed"]
    failure = _send(a, pb, key="try-again")
    assert failure.status_code == 400
    assert failure.json()["detail"]["error"] == "message_request_unavailable"
    assert "suppression" not in failure.text and "declined" not in failure.text
    with Session(seeded) as session:
        policy = session.get(
            MessageRequestSuppression, (pa["profile_id"], pb["profile_id"])
        )
        assert policy.source_request_id == request["request_id"]
        assert policy.cleared_at is None
        assert _count(session, DirectMessage) == 0
    reverse = _send(
        b, pa, note="I would like to connect now", key="recipient-initiates"
    )
    assert reverse.status_code == 200
    new_request = reverse.json()["request"]
    assert new_request["request_id"] != request["request_id"]
    assert new_request["state"] == "pending"
    assert (
        a.post(
            f"/api/direct-messages/requests/{new_request['request_id']}/accept"
        ).status_code
        == 200
    )
    with Session(seeded) as session:
        assert (
            session.get(
                MessageRequestSuppression, (pa["profile_id"], pb["profile_id"])
            ).cleared_at
            is not None
        )
        assert session.get(MessageRequest, request["request_id"]).state == "declined"
        first = session.scalar(select(DirectMessage))
        assert first.sender_profile_id == pb["profile_id"]


def test_withdrawal_terminal_retains_pair_and_never_materializes(seeded):
    a, b, pa, pb, request = _pending(seeded)
    path = f"/api/direct-messages/requests/{request['request_id']}"
    assert a.post(path + "/withdraw").json()["request"]["state"] == "withdrawn"
    assert a.post(path + "/withdraw").json()["replayed"]
    assert b.post(path + "/accept").status_code == 409
    assert a.get("/api/direct-messages/requests").json()["requests"] == []
    assert (
        b.get("/api/direct-messages/requests", params={"history": True}).json()[
            "requests"
        ][0]["state"]
        == "withdrawn"
    )
    with Session(seeded) as session:
        assert _count(session, DirectMessageRelationship) == 1
        assert (
            _count(session, DirectMessage)
            == _count(session, DirectMessageConversation)
            == 0
        )
        assert _count(session, MessageRequestSuppression) == 0
    assert _send(a, pb, key="fresh-attempt").status_code == 200


@pytest.mark.parametrize("sweep", ["list", "accept"])
def test_30_day_expiry_is_durable_and_historical(seeded, monkeypatch, sweep):
    a, b, pa, pb, request = _pending(seeded)
    expires = datetime.fromisoformat(request["expires_at"])
    monkeypatch.setattr(domain, "_now", lambda: expires)
    if sweep == "accept":
        assert (
            b.post(
                f"/api/direct-messages/requests/{request['request_id']}/accept"
            ).status_code
            == 409
        )
    else:
        assert b.get("/api/direct-messages/requests").json()["requests"] == []
    with Session(seeded) as session:
        stored = session.get(MessageRequest, request["request_id"])
        assert stored.state == "expired"
        assert stored.transitioned_at == stored.expires_at
        assert _count(session, DirectMessage) == 0
    assert (
        a.get("/api/direct-messages/requests", params={"history": True}).json()[
            "requests"
        ][0]["state"]
        == "expired"
    )


def test_history_retention_is_participant_local(seeded):
    a, b, pa, pb, request = _pending(seeded)
    path = f"/api/direct-messages/requests/{request['request_id']}"
    assert a.post(path + "/archive").status_code == 409
    b.post(path + "/decline")
    assert (
        a.get("/api/direct-messages/request-history-preferences").json()[
            "auto_hide_terminal"
        ]
        is False
    )
    assert (
        len(a.get("/api/direct-messages/requests?history=true").json()["requests"]) == 1
    )
    assert (
        a.put(
            "/api/direct-messages/request-history-preferences",
            json={"auto_hide_terminal": True},
        ).status_code
        == 200
    )
    assert a.get("/api/direct-messages/requests?history=true").json()["requests"] == []
    assert (
        len(b.get("/api/direct-messages/requests?history=true").json()["requests"]) == 1
    )
    assert b.post(path + "/archive").status_code == 200
    assert b.post(path + "/archive").status_code == 200
    assert b.get("/api/direct-messages/requests?history=true").json()["requests"] == []
    with Session(seeded) as session:
        assert session.get(MessageRequest, request["request_id"]).state == "declined"
        assert _count(session, MessageRequestSuppression) == 1


def test_cleanup_does_not_hide_accepted_messages_or_other_account_history(seeded):
    a, b, pa, pb, request = _pending(seeded)
    accepted = b.post(
        f"/api/direct-messages/requests/{request['request_id']}/accept"
    ).json()["request"]
    a.put(
        "/api/direct-messages/request-history-preferences",
        json={"auto_hide_terminal": True},
    )
    assert (
        len(a.get("/api/direct-messages/requests?history=true").json()["requests"]) == 1
    )
    assert (
        a.post(
            f"/api/direct-messages/requests/{request['request_id']}/archive"
        ).status_code
        == 200
    )
    assert (
        len(b.get("/api/direct-messages/requests?history=true").json()["requests"]) == 1
    )
    assert (
        len(
            a.get(
                f"/api/direct-messages/conversations/{accepted['conversation_id']}/messages"
            ).json()["messages"]
        )
        == 1
    )


def test_username_initiation_gate_and_existing_conversation_continuity(seeded):
    a, b, pa, pb, request = _pending(seeded)
    accepted = b.post(
        f"/api/direct-messages/requests/{request['request_id']}/accept"
    ).json()["request"]
    with seeded.begin() as connection:
        connection.execute(
            update(UserProfile)
            .where(UserProfile.profile_id == pa["profile_id"])
            .values(username=None, username_state="unset")
        )
    assert a.get("/api/direct-messages/profiles?q=bob").status_code == 403
    assert _send(a, pb, key="new-key").status_code == 403
    assert (
        a.post(
            f"/api/direct-messages/conversations/{accepted['conversation_id']}/messages",
            json={"body": "Still participating"},
        ).status_code
        == 200
    )
    assert (
        a.post(
            f"/api/direct-messages/relationships/{request['relationship_id']}/conversations",
            json={},
        ).status_code
        == 200
    )


def test_bounded_rate_and_validation(seeded):
    a, b, pa, pb = _new_pair(seeded)
    for index in range(10):
        request = _send(a, pb, key=f"budget-{index}").json()["request"]
        assert (
            a.post(
                f"/api/direct-messages/requests/{request['request_id']}/withdraw"
            ).status_code
            == 200
        )
    assert _send(a, pb, key="over-budget").status_code == 429
    assert _send(a, pb, key="budget-0").json()["replayed"] is True
    assert _send(a, pb, note=" ", key="bad-note").status_code == 422
    assert _send(a, pb, key=" ").status_code == 422


def test_same_node_auth_and_no_unrelated_mutation(seeded):
    a, b, pa, pb = _new_pair(seeded)
    remote = dict(pb, node_id="node-remote")
    assert _send(a, remote).status_code == 422
    missing = dict(pb, profile_id="missing-profile")
    assert _send(a, missing).status_code == 404
    missing_owner = _make_client(seeded, "missing-user")
    assert _send(missing_owner, pb).status_code == 404
    writes = []

    def capture(connection, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE")):
            writes.append(statement)

    event.listen(seeded, "before_cursor_execute", capture)
    try:
        request = _send(a, pb).json()["request"]
        assert (
            b.post(
                f"/api/direct-messages/requests/{request['request_id']}/accept"
            ).status_code
            == 200
        )
    finally:
        event.remove(seeded, "before_cursor_execute", capture)
    for statement in writes:
        assert not any(
            name in statement
            for name in (
                "chat_threads",
                "chat_messages",
                "projects",
                "contacts",
                "memory",
                "embeddings",
                "federation",
            )
        )


def test_message_send_cannot_bypass_missing_consent_even_with_a_conversation_row(
    seeded,
):
    a, b, pa, pb = _new_pair(seeded)
    pair = a.post(
        "/api/direct-messages/relationships",
        json={
            "destination_node_id": pb["node_id"],
            "destination_profile_id": pb["profile_id"],
        },
    ).json()["relationship"]
    now = datetime.now(timezone.utc)
    with Session(seeded) as session:
        session.add(
            DirectMessageConversation(
                id="unauthorized-row",
                relationship_id=pair["relationship_id"],
                created_by_profile_id=pa["profile_id"],
                kind="direct",
                created_at=now,
                latest_activity_at=now,
            )
        )
        session.commit()
    response = a.post(
        "/api/direct-messages/conversations/unauthorized-row/messages",
        json={"body": "Cannot bypass"},
    )
    assert response.status_code == 403
    with Session(seeded) as session:
        assert _count(session, DirectMessage) == 0


def test_daily_request_budget_across_hour_boundaries(seeded, monkeypatch):
    a, b, pa, pb = _new_pair(seeded)
    now = datetime.now(timezone.utc)
    for hour in range(5):
        instant = now + timedelta(hours=hour, seconds=hour)
        monkeypatch.setattr(domain, "_now", lambda instant=instant: instant)
        for attempt in range(10):
            result = _send(a, pb, key=f"daily-{hour}-{attempt}")
            assert result.status_code == 200
            request = result.json()["request"]
            assert (
                a.post(
                    f"/api/direct-messages/requests/{request['request_id']}/withdraw"
                ).status_code
                == 200
            )
    monkeypatch.setattr(domain, "_now", lambda: now + timedelta(hours=6))
    assert _send(a, pb, key="daily-over-budget").status_code == 429
    assert _send(a, pb, key="daily-0-0").json()["replayed"] is True


@pytest.mark.parametrize(
    "extra",
    [
        "sender_profile_id",
        "user_id",
        "account_id",
        "origin_project_id",
        "origin_thread_id",
        "content_type",
    ],
)
def test_request_body_cannot_inject_identity_scope_or_content_authority(seeded, extra):
    a, b, pa, pb = _new_pair(seeded)
    response = a.post(
        "/api/direct-messages/requests",
        json={
            "destination_node_id": pb["node_id"],
            "destination_profile_id": pb["profile_id"],
            "note": "Human plain text",
            "client_request_key": "scope-test",
            extra: "forged",
        },
    )
    assert response.status_code == 422
    with Session(seeded) as session:
        assert _count(session, MessageRequest) == _count(session, DirectMessage) == 0
