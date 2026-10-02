"""Additive storage proof; SQLite constraints are not Postgres race proof."""
from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from guardian.db.models import (
    DirectMessage,
    DirectMessageConsent,
    DirectMessageConversation,
    DirectMessageRelationship,
    MessageRequest,
    MessageRequestAttempt,
    MessageRequestPreferences,
    MessageRequestSuppression,
    MessageRequestVisibility,
    ThreadSpaceNode,
    UserProfile,
)
from guardian.messaging.tokens import (
    DM_CONSENT_SOURCES,
    MESSAGE_REQUEST_STATES,
    DirectMessageConsentSource,
    MessageRequestState,
    validate_dm_consent_source,
    validate_message_request_state,
)
from tests.routes.test_direct_messages import _new_engine, _seed_users

NOW = datetime(2026, 10, 2, tzinfo=timezone.utc)
NEW_MODELS = (
    MessageRequest,
    MessageRequestAttempt,
    DirectMessageConsent,
    MessageRequestSuppression,
    MessageRequestPreferences,
    MessageRequestVisibility,
)
MIGRATION = (
    Path(__file__).resolve().parents[2]
    / "guardian/db/migrations/versions/9e52b1d3c8fa_add_message_request_consent.py"
)


def _migration(connection, action):
    spec = importlib.util.spec_from_file_location(
        "request_storage_migration", MIGRATION
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with Operations.context(MigrationContext.configure(connection)):
        getattr(module, action)()


@pytest.fixture
def request_storage():
    engine = _new_engine(create_request_tables=False)
    with Session(engine) as session:
        _seed_users(session)
        session.add(
            ThreadSpaceNode(node_id="node-local", name="Local", status="active")
        )
        session.flush()
        for suffix in ("a", "b", "c"):
            session.add(
                UserProfile(
                    user_id=f"user-{suffix}@example.com",
                    profile_id=f"profile-{suffix}",
                    node_id="node-local",
                    username_state="unset",
                )
            )
        session.flush()
        session.add_all(
            [
                DirectMessageRelationship(
                    id="historical-pair",
                    participant_pair_key="old-pair",
                    created_at=NOW,
                    updated_at=NOW,
                ),
                DirectMessageRelationship(
                    id="neutral-pair",
                    participant_pair_key="new-pair",
                    created_at=NOW,
                    updated_at=NOW,
                ),
            ]
        )
        session.flush()
        session.add(
            DirectMessageConversation(
                id="old-conversation",
                relationship_id="historical-pair",
                created_by_profile_id="profile-a",
                kind="direct",
                created_at=NOW,
                latest_activity_at=NOW,
            )
        )
        session.flush()
        session.add(
            DirectMessage(
                id="old-message",
                conversation_id="old-conversation",
                sender_node_id="node-local",
                sender_profile_id="profile-a",
                content_type="text/plain",
                body="Historic text",
                client_message_key="historic-key",
                created_at=NOW,
            )
        )
        session.commit()
    with engine.begin() as connection:
        _migration(connection, "upgrade")
    try:
        yield engine
    finally:
        engine.dispose()


def _request(
    identity="request-1", sender="profile-a", recipient="profile-b", **overrides
):
    fields = dict(
        id=identity,
        relationship_id="neutral-pair",
        sender_profile_id=sender,
        recipient_profile_id=recipient,
        note="Hello",
        state="pending",
        created_at=NOW,
        expires_at=NOW + timedelta(days=30),
    )
    fields.update(overrides)
    return MessageRequest(**fields)


def test_migration_preserves_history_without_fabricating_requests(request_storage):
    with Session(request_storage) as session:
        historical = session.get(DirectMessageConsent, "historical-pair")
        assert historical.source == "historical_conversation"
        assert historical.request_id is None
        assert historical.established_at.replace(tzinfo=timezone.utc) == NOW
        assert session.get(DirectMessageConsent, "neutral-pair") is None
        assert session.scalars(select(MessageRequest)).all() == []
        message = session.get(DirectMessage, "old-message")
        assert (
            message.conversation_id,
            message.sender_profile_id,
            message.body,
            message.client_message_key,
        ) == ("old-conversation", "profile-a", "Historic text", "historic-key")
        conversation = session.get(DirectMessageConversation, "old-conversation")
        assert (
            conversation.relationship_id,
            conversation.origin_project_id,
            conversation.origin_thread_id,
        ) == ("historical-pair", None, None)


def test_schema_matches_orm_and_downgrade_preserves_existing_domain(request_storage):
    inspector = inspect(request_storage)
    for model in NEW_MODELS:
        assert {
            column["name"] for column in inspector.get_columns(model.__tablename__)
        } == set(model.__table__.columns.keys())
    with request_storage.begin() as connection:
        _migration(connection, "downgrade")
    tables = set(inspect(request_storage).get_table_names())
    assert not {m.__tablename__ for m in NEW_MODELS} & tables
    with Session(request_storage) as session:
        assert session.get(DirectMessage, "old-message").body == "Historic text"
        assert session.get(DirectMessageRelationship, "neutral-pair") is not None


def test_database_directional_pending_uniqueness_not_unordered_pair(request_storage):
    with Session(request_storage) as session:
        session.add(_request())
        session.commit()
        session.add(_request("reverse", sender="profile-b", recipient="profile-a"))
        session.commit()  # service resolves affirmative reverse intent; index is directional
        session.add(_request("duplicate-direction"))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
        original = session.get(MessageRequest, "request-1")
        original.state = "withdrawn"
        original.transitioned_at = NOW
        session.commit()
        session.add(_request("new-attempt"))
        session.commit()


@pytest.mark.parametrize(
    "overrides",
    [
        {"state": "unknown"},
        {"recipient_profile_id": "profile-a"},
        {"note": "   "},
        {"note": "x" * 32001},
        {"expires_at": NOW},
        {"state": "withdrawn"},
        {"state": "accepted", "transitioned_at": NOW},
        {"state": "pending", "transitioned_at": NOW},
    ],
)
def test_database_rejects_invalid_shared_request_state(request_storage, overrides):
    with Session(request_storage) as session:
        session.add(_request(**overrides))
        with pytest.raises(IntegrityError):
            session.commit()


def test_sender_key_binding_and_local_visibility_preserve_shared_truth(request_storage):
    with Session(request_storage) as session:
        session.add(_request(state="declined", transitioned_at=NOW))
        session.commit()
        session.add(
            MessageRequestAttempt(
                id="attempt-1",
                request_id="request-1",
                sender_profile_id="profile-a",
                recipient_profile_id="profile-b",
                client_request_key="logical-attempt",
                note="Hello",
                created_at=NOW,
            )
        )
        session.add(
            MessageRequestSuppression(
                sender_profile_id="profile-a",
                recipient_profile_id="profile-b",
                source_request_id="request-1",
                created_at=NOW,
            )
        )
        session.add(
            MessageRequestPreferences(
                profile_id="profile-a", auto_hide_terminal=True, updated_at=NOW
            )
        )
        session.add(
            MessageRequestVisibility(
                request_id="request-1", profile_id="profile-a", hidden_at=NOW
            )
        )
        session.commit()
        session.add(
            MessageRequestAttempt(
                id="attempt-2",
                request_id="request-1",
                sender_profile_id="profile-a",
                recipient_profile_id="profile-b",
                client_request_key="logical-attempt",
                note="Changed text",
                created_at=NOW,
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
        assert session.get(MessageRequest, "request-1").state == "declined"
        assert session.get(MessageRequestVisibility, ("request-1", "profile-b")) is None
        assert (
            session.get(
                MessageRequestSuppression, ("profile-a", "profile-b")
            ).cleared_at
            is None
        )
        assert session.get(DirectMessage, "old-message") is not None


def test_canonical_tokens_reject_unknown_vocabulary():
    assert MESSAGE_REQUEST_STATES == {
        "pending",
        "accepted",
        "declined",
        "withdrawn",
        "expired",
    }
    assert DM_CONSENT_SOURCES == {"historical_conversation", "accepted_request"}
    for state in MessageRequestState:
        assert validate_message_request_state(state) == state.value
    for source in DirectMessageConsentSource:
        assert validate_dm_consent_source(source) == source.value
    with pytest.raises(ValueError):
        validate_message_request_state("archived")
    with pytest.raises(ValueError):
        validate_dm_consent_source("relationship_exists")
