"""Real PostgreSQL migrations and independent-connection race proof."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Barrier
import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Session

from guardian.db.models import (
    DirectMessage,
    DirectMessageConsent,
    DirectMessageConversation,
    MessageRequest,
    MessageRequestAttempt,
    User,
)
from guardian.messaging import service
from guardian.messaging import requests as domain
from guardian.messaging.tokens import MessageRequestState
from tests.migration.test_direct_messaging_migration import (
    temporary_postgres,
    _upgrade_to,
    _downgrade_to,
)

PREVIOUS = "8d41a0c2b7ef"
REVISION = "9e52b1d3c8fa"


def _pair(engine, suffix):
    addresses = []
    with Session(engine) as session:
        for side in ("a", "b"):
            owner = f"proof-{suffix}-{side}"
            session.add(
                User(
                    id=owner,
                    username=owner,
                    password_hash="not-a-real-hash",
                    role="guest",
                )
            )
        session.commit()
        for side in ("a", "b"):
            profile = service.get_or_create_owned_profile(
                session, f"proof-{suffix}-{side}"
            )
            profile = service.claim_username(session, profile, f"proof-{suffix}-{side}")
            addresses.append((profile.node_id, profile.profile_id))
    return addresses


def _initiate(engine, owner, peer, key, note="Intro", barrier=None):
    with Session(engine) as session:
        profile = service.get_or_create_owned_profile(session, owner)
        if barrier:
            barrier.wait(timeout=10)
        request, replayed = domain.create_request(session, profile, *peer, note, key)
        return request.id, request.state, request.conversation_id, replayed


def _accept(engine, owner, request_id, barrier=None):
    with Session(engine) as session:
        profile = service.get_or_create_owned_profile(session, owner)
        if barrier:
            barrier.wait(timeout=10)
        result, replayed = domain.transition_request(
            session, profile, request_id, MessageRequestState.ACCEPTED
        )
        return result.id, result.conversation_id, result.first_message_id, replayed


def _race(functions):
    barrier = Barrier(len(functions))
    with ThreadPoolExecutor(max_workers=len(functions)) as executor:
        futures = [executor.submit(fn, barrier) for fn in functions]
        return [f.result(timeout=20) for f in futures]


def test_postgres_migration_and_concurrent_consent(temporary_postgres):
    config, url = temporary_postgres
    _upgrade_to(config, PREVIOUS)
    engine = sa.create_engine(
        url,
        future=True,
        connect_args={"options": "-c statement_timeout=15000 -c lock_timeout=10000"},
    )
    try:
        # Honest pre-migration Conversation, not a synthetic request.
        pa, pb = _pair(engine, "historical")
        with Session(engine) as session:
            owner = service.get_or_create_owned_profile(session, "proof-historical-a")
            relationship = service.resolve_or_create_relationship(session, owner, *pb)
            old_pair = relationship.id
            now = datetime.now(timezone.utc)
            session.add(
                DirectMessageConversation(
                    id="historical-conversation",
                    relationship_id=old_pair,
                    created_by_profile_id=pa[1],
                    kind="direct",
                    created_at=now,
                    latest_activity_at=now,
                )
            )
            session.flush()
            session.add(
                DirectMessage(
                    id="historical-message",
                    conversation_id="historical-conversation",
                    sender_node_id=pa[0],
                    sender_profile_id=pa[1],
                    content_type="text/plain",
                    body="Preserve me",
                    client_message_key="historic-key",
                    created_at=now,
                )
            )
            session.commit()
        _upgrade_to(config, REVISION)
        with Session(engine) as session:
            consent = session.get(DirectMessageConsent, old_pair)
            assert (
                consent.source == "historical_conversation"
                and consent.request_id is None
            )
            assert (
                session.scalar(sa.select(sa.func.count()).select_from(MessageRequest))
                == 0
            )
            sender = service.get_or_create_owned_profile(session, "proof-historical-a")
            existing = session.get(DirectMessageConversation, "historical-conversation")
            service.create_message(
                session, existing, sender, "Historical continuation", "historic-next"
            )

        # Simultaneous same-key retries use independent connections.
        pa, pb = _pair(engine, "duplicate")
        results = _race(
            [
                lambda barrier: _initiate(
                    engine, "proof-duplicate-a", pb, "same-key", barrier=barrier
                )
                for _ in range(4)
            ]
        )
        assert len({r[0] for r in results}) == 1
        assert sum(not r[3] for r in results) == 1
        request_id = results[0][0]
        accepted = _race(
            [
                lambda barrier: _accept(
                    engine, "proof-duplicate-b", request_id, barrier=barrier
                )
                for _ in range(4)
            ]
        )
        assert len({r[1] for r in accepted}) == len({r[2] for r in accepted}) == 1
        assert sum(not r[3] for r in accepted) == 1
        with Session(engine) as session:
            assert (
                session.scalar(
                    sa.select(sa.func.count())
                    .select_from(DirectMessage)
                    .where(DirectMessage.conversation_id == accepted[0][1])
                )
                == 1
            )
            assert session.get(DirectMessage, accepted[0][2]).sender_profile_id == pa[1]

        # Simultaneous opposite directions must never deadlock across Profile FKs.
        pa, pb = _pair(engine, "reverse")
        results = _race(
            [
                lambda barrier: _initiate(
                    engine, "proof-reverse-a", pb, "reverse-a", "A note", barrier
                ),
                lambda barrier: _initiate(
                    engine, "proof-reverse-b", pa, "reverse-b", "B note", barrier
                ),
            ]
        )
        assert len({r[0] for r in results}) == 1
        with Session(engine) as session:
            request = session.get(MessageRequest, results[0][0])
            assert request.state == "accepted"
            assert (
                session.scalar(
                    sa.select(sa.func.count())
                    .select_from(DirectMessageConversation)
                    .where(
                        DirectMessageConversation.relationship_id
                        == request.relationship_id
                    )
                )
                == 1
            )
            messages = session.scalars(
                sa.select(DirectMessage)
                .where(DirectMessage.conversation_id == request.conversation_id)
                .order_by(DirectMessage.created_at, DirectMessage.id)
            ).all()
            assert len(messages) == 2
            assert messages[0].id == request.first_message_id
            assert messages[0].sender_profile_id == request.sender_profile_id
            assert {m.body for m in messages} == {"A note", "B note"}
            assert (
                session.scalar(
                    sa.select(sa.func.count())
                    .select_from(MessageRequestAttempt)
                    .where(MessageRequestAttempt.request_id == request.id)
                )
                == 2
            )
        _downgrade_to(config, PREVIOUS)
        with Session(engine) as session:
            assert (
                session.get(DirectMessage, "historical-message").body == "Preserve me"
            )
            assert (
                session.get(DirectMessageConversation, "historical-conversation")
                is not None
            )
    finally:
        engine.dispose()
