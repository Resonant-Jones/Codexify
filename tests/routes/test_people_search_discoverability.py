"""Focused People-search discoverability tests.

Covers the same-node username-search seam with synthetic accounts only:

1. A partial handle — including the conventional ``@`` sigil the People UI
   displays — finds a profile that deliberately claimed a username.
2. A profile that never claimed a username is excluded, and is
   indistinguishable from a profile that does not exist.
3. Finding a profile does not authorize messaging; request, block, and
   consent rules still apply.
4. A cleared, too-short, or failing query behaves correctly.
5. Discovery is same-node: another node's profile is out of scope.

No real user data, no network, and no federation.
"""

from __future__ import annotations

import pytest
from sqlalchemy.orm import sessionmaker

from guardian.db.models import ThreadSpaceNode, User, UserProfile
from tests.routes.test_direct_messages import (  # noqa: F401
    _claim_username,
    _make_client,
    dm_engine,
    seeded,
)

PEER_USERNAME = "resonant-jones"


def _search(client, query: str):
    response = client.get("/api/direct-messages/profiles", params={"q": query})
    assert response.status_code == 200, response.text
    return response


def _peer_profile(client) -> dict:
    """A peer that deliberately claimed a username (the discoverable state)."""
    claimed = _claim_username(client, PEER_USERNAME)
    assert claimed.status_code == 200, claimed.text
    return claimed.json()["profile"]


# ── 1. Partial handle finds a discoverable profile ─────────────────────────


def test_partial_handle_finds_a_claimed_same_node_profile(seeded):  # noqa: F811
    client_a = _make_client(seeded, "user-a@example.com")
    client_b = _make_client(seeded, "user-b@example.com")
    assert _claim_username(client_a, "searcher").status_code == 200
    peer = _peer_profile(client_b)

    # The People UI renders handles as "@username", so the sigil form is the
    # one a person actually types.
    for query in ("@resonant-", "@resonant-jones", "resonant-", "resonant-jones"):
        results = _search(client_a, query).json()["profiles"]
        assert len(results) == 1, (query, results)
        assert results[0]["profile_id"] == peer["profile_id"]
        assert results[0]["username"] == PEER_USERNAME
        assert results[0]["node_id"] == peer["node_id"]


def test_partial_handle_match_is_case_insensitive(seeded):  # noqa: F811
    client_a = _make_client(seeded, "user-a@example.com")
    client_b = _make_client(seeded, "user-b@example.com")
    assert _claim_username(client_a, "searcher").status_code == 200
    peer = _peer_profile(client_b)

    for query in ("@RESONANT-", "@Resonant-Jones", "ReSoNaNt-"):
        results = _search(client_a, query).json()["profiles"]
        assert len(results) == 1, (query, results)
        assert results[0]["profile_id"] == peer["profile_id"]


def test_unclaimed_username_is_not_discoverable(seeded):  # noqa: F811
    client_a = _make_client(seeded, "user-a@example.com")
    client_b = _make_client(seeded, "user-b@example.com")
    assert _claim_username(client_a, "searcher").status_code == 200
    # user-b never claims a username, so it never opted into discovery.
    _make_client(seeded, "user-b@example.com").get("/api/profile/social-identity")

    assert _search(client_a, "user-b").json()["profiles"] == []


# ── 2. A non-discoverable profile leaks nothing ────────────────────────────


def test_private_profile_is_indistinguishable_from_a_missing_one(seeded):  # noqa: F811
    client_a = _make_client(seeded, "user-a@example.com")
    client_b = _make_client(seeded, "user-b@example.com")
    assert _claim_username(client_a, "searcher").status_code == 200
    # user-b exists and is a real account but never claimed a username.
    assert (
        client_b.get("/api/profile/social-identity").json()["profile"]["username"]
        is None
    )

    private_payload = _search(client_a, "user-b").json()
    missing_payload = _search(client_a, "nobody-here").json()

    assert private_payload["profiles"] == []
    assert private_payload == missing_payload


def test_search_results_disclose_only_social_fields(seeded):  # noqa: F811
    client_a = _make_client(seeded, "user-a@example.com")
    client_b = _make_client(seeded, "user-b@example.com")
    assert _claim_username(client_a, "searcher").status_code == 200
    _peer_profile(client_b)

    hit = _search(client_a, "@resonant-jones").json()["profiles"][0]
    assert set(hit) == {
        "node_id",
        "profile_id",
        "username",
        "username_state",
        "display_name",
        "avatar_url",
    }
    assert "user-b@example.com" not in str(hit)
    assert "user_id" not in hit
    assert "email" not in hit


# ── 3. Discovery is not messaging authority ────────────────────────────────


def test_discovered_profile_does_not_authorize_messaging(seeded):  # noqa: F811
    client_a = _make_client(seeded, "user-a@example.com")
    client_b = _make_client(seeded, "user-b@example.com")
    assert _claim_username(client_a, "searcher").status_code == 200
    peer = _peer_profile(client_b)

    # Discovery yields the peer address, nothing more.
    found = _search(client_a, "@resonant-jones").json()["profiles"][0]
    assert found["profile_id"] == peer["profile_id"]

    relationship = client_a.post(
        "/api/direct-messages/relationships",
        json={
            "destination_node_id": peer["node_id"],
            "destination_profile_id": peer["profile_id"],
        },
    )
    assert relationship.status_code == 200, relationship.text
    relationship_id = relationship.json()["relationship"]["relationship_id"]

    # Resolving a Relationship is not consent: creating a Conversation in it
    # still requires accepted consent.
    conversation = client_a.post(
        f"/api/direct-messages/relationships/{relationship_id}/conversations",
        json={},
    )
    assert conversation.status_code == 403, conversation.text

    # And a message request is pending until the recipient accepts it.
    request = client_a.post(
        "/api/direct-messages/requests",
        json={
            "destination_node_id": peer["node_id"],
            "destination_profile_id": peer["profile_id"],
            "note": "Hello from search",
            "client_request_key": "search-discovered-key",
        },
    )
    assert request.status_code in (200, 201, 202), request.text
    body = request.json()
    assert body["request"]["state"] in ("pending", "sent"), body


def test_discovered_profile_does_not_bypass_a_decline_suppression(seeded):  # noqa: F811
    """A recipient's decline is directional suppression. Discovery still
    resolves the peer — discovery is not the authorization surface — but a
    fresh solicitation is refused."""
    client_a = _make_client(seeded, "user-a@example.com")
    client_b = _make_client(seeded, "user-b@example.com")
    assert _claim_username(client_a, "searcher").status_code == 200
    peer = _peer_profile(client_b)

    first = client_a.post(
        "/api/direct-messages/requests",
        json={
            "destination_node_id": peer["node_id"],
            "destination_profile_id": peer["profile_id"],
            "note": "Hello from search",
            "client_request_key": "suppression-first-key",
        },
    )
    assert first.status_code in (200, 201, 202), first.text
    request_id = first.json()["request"]["request_id"]

    declined = client_b.post(
        f"/api/direct-messages/requests/{request_id}/decline"
    )
    assert declined.status_code == 200, declined.text

    assert len(_search(client_a, "@resonant-jones").json()["profiles"]) == 1

    second = client_a.post(
        "/api/direct-messages/requests",
        json={
            "destination_node_id": peer["node_id"],
            "destination_profile_id": peer["profile_id"],
            "note": "Again from search",
            "client_request_key": "suppression-second-key",
        },
    )
    assert second.status_code == 400, second.text
    assert second.json()["detail"]["error"] == "message_request_unavailable"


# ── 4. Cleared, too-short, and failing queries ────────────────────────────


def test_cleared_and_too_short_queries_return_no_results(seeded):  # noqa: F811
    client_a = _make_client(seeded, "user-a@example.com")
    client_b = _make_client(seeded, "user-b@example.com")
    assert _claim_username(client_a, "searcher").status_code == 200
    _peer_profile(client_b)

    assert _search(client_a, "").json()["profiles"] == []
    assert _search(client_a, "   ").json()["profiles"] == []
    # A single character is too short to be a meaningful prefix query.
    assert _search(client_a, "@").json()["profiles"] == []
    assert _search(client_a, "r").json()["profiles"] == []


def test_search_without_a_claimed_username_fails_closed(seeded):  # noqa: F811
    client_a = _make_client(seeded, "user-a@example.com")
    client_b = _make_client(seeded, "user-b@example.com")
    _peer_profile(client_b)
    # The searcher never claimed a username, so it cannot discover others.
    response = client_a.get("/api/direct-messages/profiles", params={"q": "resonant"})
    assert response.status_code == 403
    assert response.json()["detail"]["error"] == "messaging_username_required"


# ── 5. Discovery is same-node ──────────────────────────────────────────────


def test_other_node_profile_is_out_of_scope(seeded):  # noqa: F811
    client_a = _make_client(seeded, "user-a@example.com")
    assert _claim_username(client_a, "searcher").status_code == 200

    with sessionmaker(bind=seeded)() as session:
        session.add(ThreadSpaceNode(node_id="node-elsewhere", name="Elsewhere"))
        session.flush()
        session.add(
            UserProfile(
                user_id="user-c@example.com",
                profile_id="c" * 32,
                node_id="node-elsewhere",
                username="resonant-remote",
                username_state="active",
                display_name="Remote Person",
            )
        )
        session.commit()

    results = _search(client_a, "resonant").json()["profiles"]
    assert results == []


def test_result_ordering_is_stable(seeded):  # noqa: F811
    client_a = _make_client(seeded, "user-a@example.com")
    assert _claim_username(client_a, "searcher").status_code == 200

    handles = ("resonant-zoe", "resonant-amy", "resonant-mid")
    with sessionmaker(bind=seeded)() as session:
        node_id = session.query(ThreadSpaceNode).first().node_id
        for index, username in enumerate(handles):
            user_id = f"extra-{index}@example.com"
            session.add(
                User(
                    id=user_id,
                    username=f"extra-{index}",
                    email=user_id,
                    password_hash="not-a-real-password-hash",
                    role="guest",
                )
            )
            session.flush()
            session.add(
                UserProfile(
                    user_id=user_id,
                    profile_id=str(index) * 32,
                    node_id=node_id,
                    username=username,
                    username_state="active",
                    display_name=None,
                )
            )
        session.commit()

    first = _search(client_a, "resonant").json()["profiles"]
    second = _search(client_a, "resonant").json()["profiles"]

    assert [hit["username"] for hit in first] == [
        "resonant-amy",
        "resonant-mid",
        "resonant-zoe",
    ]
    assert first == second


# ── The normalizer itself ─────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("@resonant-", "resonant-"),
        ("resonant-", "resonant-"),
        ("  @Resonant-Jones  ", "resonant-jones"),
        ("@", ""),
        ("", ""),
        (None, ""),
    ],
)
def test_normalize_search_query(raw, expected):
    from guardian.messaging.service import normalize_search_query

    assert normalize_search_query(raw) == expected
