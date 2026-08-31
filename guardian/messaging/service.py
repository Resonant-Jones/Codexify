"""Durable same-node direct-messaging service.

This module owns the bounded persistence domain for node-addressed
profile-to-profile private messaging.  It performs no model inference, no
retrieval, no memory mutation, and no Guardian chat work; it never touches
``chat_threads``, ``chat_messages``, Hosted Rooms, or federation transport.

Authorization authority is derived exclusively from the authenticated
user's owned profile.  Caller-supplied identity is never trusted.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from guardian.db.models import (
    DirectMessage,
    DirectMessageConversation,
    DirectMessageConversationParticipant,
    ThreadSpaceNode,
    UserProfile,
)
from guardian.messaging.envelope import (
    build_message_envelope,
    envelope_payload,
)
from guardian.messaging.tokens import (
    normalize_username,
    validate_username_state,
)

# ── Bounds ────────────────────────────────────────────────────────────────

_MAX_BODY_LENGTH = 32_000  # matches Hosted Room message bound
_MAX_CLIENT_KEY_LENGTH = 128
_MAX_SEARCH_RESULTS = 20
_DEFAULT_PAGE_LIMIT = 100
_MAX_PAGE_LIMIT = 200

_LOCAL_NODE_NAME_ENV = "CODEXIFY_LOCAL_NODE_NAME"
_DEFAULT_LOCAL_NODE_NAME = "Codexify Local Node"


def _err(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status,
        detail={"error": code, "message": message},
    )


# ── Node identity ─────────────────────────────────────────────────────────


def _new_node_id() -> str:
    return "node-" + uuid.uuid4().hex


def get_or_create_local_node(session) -> ThreadSpaceNode:
    """Resolve the one canonical local node, creating it on first use.

    The row is persisted in Postgres, so the local Node_ID is stable across
    backend restarts without deriving from hostname, IP, endpoint, or
    container identity.  Concurrency is handled by retrying on the unique
    primary-key conflict.
    """
    node = session.scalar(
        select(ThreadSpaceNode)
        .order_by(ThreadSpaceNode.created_at.asc(), ThreadSpaceNode.node_id.asc())
        .limit(1)
    )
    if node is not None:
        return node

    name = (os.getenv(_LOCAL_NODE_NAME_ENV) or "").strip() or (_DEFAULT_LOCAL_NODE_NAME)
    node = ThreadSpaceNode(
        node_id=_new_node_id(),
        name=name,
        status="active",
    )
    session.add(node)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        node = session.scalar(
            select(ThreadSpaceNode)
            .order_by(ThreadSpaceNode.created_at.asc(), ThreadSpaceNode.node_id.asc())
            .limit(1)
        )
        if node is None:  # pragma: no cover - defensive
            raise _err(500, "local_node_unavailable", "Local node identity unavailable")
    session.refresh(node)
    return node


def local_node_id(session) -> str:
    return get_or_create_local_node(session).node_id


# ── Profile identity ──────────────────────────────────────────────────────


def ensure_profile_identity(session, profile: UserProfile) -> UserProfile:
    """Backfill the durable social fields on a canonical profile.

    ``profile_id`` is minted once per profile row and is the durable social
    actor token; ``node_id`` anchors the profile to the canonical local
    node.  Neither value is ever derived from email or account metadata.
    """
    changed = False
    if not profile.profile_id:
        profile.profile_id = uuid.uuid4().hex
        changed = True
    if not profile.node_id:
        profile.node_id = local_node_id(session)
        changed = True
    if changed:
        session.commit()
        session.refresh(profile)
    return profile


def get_or_create_owned_profile(session, user_id: str) -> UserProfile:
    """Resolve the canonical social profile owned by an authenticated user.

    Mirrors the lazy profile-creation behavior of the presentation profile
    surface while minting durable social identity on first use.
    """
    profile = session.scalar(select(UserProfile).where(UserProfile.user_id == user_id))
    if profile is not None:
        return ensure_profile_identity(session, profile)

    profile = UserProfile(user_id=user_id)
    profile.profile_id = uuid.uuid4().hex
    profile.node_id = local_node_id(session)
    profile.username_state = "unset"
    session.add(profile)
    try:
        session.commit()
    except IntegrityError:
        # A concurrent request created the profile first.
        session.rollback()
        profile = session.scalar(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        if profile is None:  # pragma: no cover - defensive
            raise _err(500, "profile_unavailable", "Social profile unavailable")
        return ensure_profile_identity(session, profile)
    session.refresh(profile)
    return profile


def claim_username(session, profile: UserProfile, raw_username: Any) -> UserProfile:
    """Deliberately claim (or rename) the profile's social username.

    The username is validated against the conservative V1 grammar, reserved
    names are rejected, uniqueness is Node-scoped and case-insensitive by
    construction (stored lowercase), and the value is never derived from
    email.  Username is a discovery alias only — conversations and messages
    bind to ``profile_id`` and survive renames.
    """
    if not isinstance(raw_username, str):
        raise _err(
            422,
            "username_required",
            "username must be a non-empty string",
        )
    try:
        normalized = normalize_username(raw_username)
    except ValueError as exc:
        message = str(exc)
        code = message.split(":", 1)[0]
        raise _err(422, code, message.split(":", 1)[1].strip()) from exc

    profile = ensure_profile_identity(session, profile)

    existing = session.scalar(
        select(UserProfile).where(
            UserProfile.node_id == profile.node_id,
            UserProfile.username == normalized,
            UserProfile.id != profile.id,
        )
    )
    if existing is not None:
        raise _err(
            409,
            "username_taken",
            "username is already claimed on this node",
        )

    profile.username = normalized
    profile.username_state = validate_username_state("active")
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise _err(
            409,
            "username_taken",
            "username is already claimed on this node",
        ) from None
    session.refresh(profile)
    return profile


# ── Safe peer-facing payloads ─────────────────────────────────────────────


def social_profile_payload(profile: UserProfile) -> dict[str, Any]:
    """The deliberately social, safe profile payload.

    Contains only social addressing and presentation fields.  ``user_id``,
    email, credentials, recovery state, and private account metadata never
    appear here.
    """
    return {
        "node_id": profile.node_id,
        "profile_id": profile.profile_id,
        "username": profile.username,
        "username_state": profile.username_state,
        "display_name": profile.display_name,
        "avatar_url": profile.avatar_url,
    }


def search_profiles(
    session, raw_query: Any, limit: int = _MAX_SEARCH_RESULTS
) -> list[dict[str, Any]]:
    """Username-oriented social discovery.

    Authenticated, bounded, and case-insensitive.  Only profiles with an
    actively claimed username are discoverable; responses expose social
    fields only.
    """
    query = str(raw_query or "").strip().lower()
    if not query:
        return []

    escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    pattern = escaped + "%"

    rows = (
        session.execute(
            select(UserProfile)
            .where(
                UserProfile.username_state == "active",
                UserProfile.username.like(pattern, escape="\\"),
            )
            .order_by(UserProfile.username.asc())
            .limit(min(max(int(limit), 1), _MAX_SEARCH_RESULTS))
        )
        .scalars()
        .all()
    )
    return [social_profile_payload(profile) for profile in rows]


# ── Conversations ─────────────────────────────────────────────────────────


def participant_pair_key(
    first_node_id: str,
    first_profile_id: str,
    second_node_id: str,
    second_profile_id: str,
) -> str:
    """Canonical unordered pair key for one-to-one conversation identity."""
    addresses = sorted(
        [
            f"{first_node_id}:{first_profile_id}",
            f"{second_node_id}:{second_profile_id}",
        ]
    )
    return "|".join(addresses)


def resolve_or_create_conversation(
    session,
    sender_profile: UserProfile,
    destination_node_id: Any,
    destination_profile_id: Any,
) -> DirectMessageConversation:
    """Atomically resolve the canonical one-to-one conversation.

    Nonlocal destinations are rejected as unsupported without any federation
    attempt.  The same unordered participant-address pair always resolves to
    the same conversation, enforced by the pair-key unique constraint.
    """
    dest_node = str(destination_node_id or "").strip()
    dest_profile = str(destination_profile_id or "").strip()
    if not dest_node or not dest_profile:
        raise _err(
            422,
            "destination_required",
            "destination_node_id and destination_profile_id are required",
        )

    sender_profile = ensure_profile_identity(session, sender_profile)
    local_node = get_or_create_local_node(session)
    assert sender_profile.node_id is not None  # ensured above
    assert sender_profile.profile_id is not None  # ensured above
    if dest_node != local_node.node_id:
        raise _err(
            422,
            "unsupported_nonlocal_destination",
            "Cross-node delivery is not supported; this node only delivers "
            "same-node direct messages",
        )
    if dest_profile == sender_profile.profile_id:
        raise _err(
            400,
            "self_direct_message_not_allowed",
            "a direct conversation requires two distinct profiles",
        )

    recipient = session.scalar(
        select(UserProfile).where(UserProfile.profile_id == dest_profile)
    )
    if recipient is None:
        raise _err(
            404,
            "recipient_profile_not_found",
            "recipient profile does not exist on this node",
        )
    recipient = ensure_profile_identity(session, recipient)

    pair_key = participant_pair_key(
        sender_profile.node_id,
        sender_profile.profile_id,
        recipient.node_id,
        recipient.profile_id,
    )
    existing = session.scalar(
        select(DirectMessageConversation).where(
            DirectMessageConversation.participant_pair_key == pair_key
        )
    )
    if existing is not None:
        return existing

    conversation = DirectMessageConversation(
        id=uuid.uuid4().hex,
        kind="direct",
        participant_pair_key=pair_key,
    )
    session.add(conversation)
    session.flush()

    # Canonical sorted participant order keeps the row set deterministic.
    addresses = sorted(
        [
            (sender_profile.node_id, sender_profile.profile_id),
            (recipient.node_id, recipient.profile_id),
        ],
        key=lambda address: (address[0], address[1]),
    )
    for node_id, profile_id in addresses:
        session.add(
            DirectMessageConversationParticipant(
                id=uuid.uuid4().hex,
                conversation_id=conversation.id,
                node_id=node_id,
                profile_id=profile_id,
            )
        )

    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        existing = session.scalar(
            select(DirectMessageConversation).where(
                DirectMessageConversation.participant_pair_key == pair_key
            )
        )
        if existing is None:  # pragma: no cover - defensive
            raise _err(500, "conversation_unavailable", "Conversation unavailable")
        return existing

    session.refresh(conversation)
    return conversation


def participant_addresses(
    session, conversation: DirectMessageConversation
) -> list[tuple[str, str]]:
    """Return each participant's (node_id, profile_id) address."""
    rows = session.scalars(
        select(DirectMessageConversationParticipant)
        .where(DirectMessageConversationParticipant.conversation_id == conversation.id)
        .order_by(
            DirectMessageConversationParticipant.node_id.asc(),
            DirectMessageConversationParticipant.profile_id.asc(),
        )
    ).all()
    return [(row.node_id, row.profile_id) for row in rows]


def require_participant(
    session,
    conversation: DirectMessageConversation,
    caller_node_id: str,
    caller_profile_id: str,
) -> None:
    """Fail closed when the caller's profile is not a participant.

    Nonparticipants receive ``conversation_not_found`` so foreign
    conversations do not leak existence.
    """
    participant = session.scalar(
        select(DirectMessageConversationParticipant).where(
            DirectMessageConversationParticipant.conversation_id == conversation.id,
            DirectMessageConversationParticipant.profile_id == caller_profile_id,
            DirectMessageConversationParticipant.node_id == caller_node_id,
        )
    )
    if participant is None:
        raise _err(
            404,
            "conversation_not_found",
            "conversation not found",
        )


def _get_conversation_or_404(
    session, conversation_id: Any
) -> DirectMessageConversation:
    conversation = session.get(DirectMessageConversation, str(conversation_id))
    if conversation is None:
        raise _err(
            404,
            "conversation_not_found",
            "conversation not found",
        )
    return conversation


def list_conversations_for_profile(
    session, profile: UserProfile, limit: int = _DEFAULT_PAGE_LIMIT
) -> list[dict[str, Any]]:
    """Participant-scoped conversation list ordered by durable activity."""
    profile = ensure_profile_identity(session, profile)
    assert profile.node_id is not None  # ensured above
    assert profile.profile_id is not None  # ensured above
    page_limit = min(max(int(limit), 1), _MAX_PAGE_LIMIT)

    conversation_ids = session.scalars(
        select(DirectMessageConversationParticipant.conversation_id).where(
            DirectMessageConversationParticipant.profile_id == profile.profile_id,
            DirectMessageConversationParticipant.node_id == profile.node_id,
        )
    ).all()
    if not conversation_ids:
        return []

    conversations = session.scalars(
        select(DirectMessageConversation)
        .where(DirectMessageConversation.id.in_(conversation_ids))
        .order_by(
            DirectMessageConversation.latest_activity_at.desc(),
            DirectMessageConversation.id.desc(),
        )
        .limit(page_limit)
    ).all()
    return [
        conversation_payload(session, conversation, profile.node_id, profile.profile_id)
        for conversation in conversations
    ]


def _participant_social_payloads(
    session, conversation: DirectMessageConversation
) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    for node_id, profile_id in participant_addresses(session, conversation):
        profile = session.scalar(
            select(UserProfile).where(UserProfile.profile_id == profile_id)
        )
        if profile is None:
            payloads.append({"node_id": node_id, "profile_id": profile_id})
            continue
        payloads.append(social_profile_payload(profile))
    return payloads


def conversation_payload(
    session,
    conversation: DirectMessageConversation,
    caller_node_id: str,
    caller_profile_id: str,
) -> dict[str, Any]:
    """Safe participant-visible conversation payload."""
    require_participant(session, conversation, caller_node_id, caller_profile_id)
    return {
        "conversation_id": conversation.id,
        "kind": conversation.kind,
        "created_at": conversation.created_at,
        "latest_activity_at": conversation.latest_activity_at,
        "participants": _participant_social_payloads(session, conversation),
    }


# ── Messages ──────────────────────────────────────────────────────────────


def message_payload(
    message: DirectMessage,
    source_node_id: str,
    source_profile_id: str,
    destination_node_id: str,
    destination_profile_id: str,
) -> dict[str, Any]:
    """Transport-neutral peer-facing message payload."""
    envelope = build_message_envelope(
        message_id=message.id,
        conversation_id=message.conversation_id,
        source_node_id=source_node_id,
        source_profile_id=source_profile_id,
        destination_node_id=destination_node_id,
        destination_profile_id=destination_profile_id,
        content_type=message.content_type,
        body=message.body,
        created_at=message.created_at,
    )
    return envelope_payload(envelope)


def list_messages(
    session,
    conversation: DirectMessageConversation,
    caller_node_id: str,
    caller_profile_id: str,
    limit: int = _DEFAULT_PAGE_LIMIT,
    before_id: str | None = None,
) -> list[dict[str, Any]]:
    """Participant-scoped chronological message readback.

    Messages order deterministically by ``(created_at, id)`` ascending with
    a bounded ``before_id`` cursor for pagination.
    """
    require_participant(session, conversation, caller_node_id, caller_profile_id)
    page_limit = min(max(int(limit), 1), _MAX_PAGE_LIMIT)

    addresses = participant_addresses(session, conversation)

    stmt = select(DirectMessage).where(DirectMessage.conversation_id == conversation.id)
    if before_id:
        cursor = session.get(DirectMessage, str(before_id))
        if cursor is not None:
            stmt = stmt.where(
                (DirectMessage.created_at < cursor.created_at)
                | (
                    (DirectMessage.created_at == cursor.created_at)
                    & (DirectMessage.id < cursor.id)
                )
            )
    stmt = stmt.order_by(DirectMessage.created_at.asc(), DirectMessage.id.asc()).limit(
        page_limit
    )

    messages = session.scalars(stmt).all()
    payloads: list[dict[str, Any]] = []
    for message in messages:
        sender_node_id = message.sender_node_id
        recipient_address = next(
            (
                address
                for address in addresses
                if address[1] != message.sender_profile_id
            ),
            None,
        )
        if recipient_address is None:  # pragma: no cover - defensive
            continue
        destination_node_id, destination_profile_id = recipient_address
        payloads.append(
            message_payload(
                message,
                sender_node_id,
                message.sender_profile_id,
                destination_node_id,
                destination_profile_id,
            )
        )
    return payloads


def create_message(
    session,
    conversation: DirectMessageConversation,
    sender_profile: UserProfile,
    body: Any,
    client_message_key: str | None = None,
) -> tuple[DirectMessage, bool]:
    """Durably persist one plain-text message and update activity.

    Returns ``(message, replayed)`` where ``replayed=True`` means an
    identical idempotency-keyed message already existed and was returned
    unchanged — retries never duplicate.
    """
    if not isinstance(body, str):
        raise _err(
            422,
            "message_body_required",
            "message body must be a non-empty string",
        )
    text = body.strip()
    if not text:
        raise _err(
            422,
            "message_body_required",
            "message body must not be blank",
        )
    if len(text) > _MAX_BODY_LENGTH:
        raise _err(
            422,
            "message_body_too_large",
            f"message body must not exceed {_MAX_BODY_LENGTH} characters",
        )

    key: str | None = None
    if client_message_key is not None:
        key = str(client_message_key).strip()
        if not key:
            raise _err(
                422,
                "client_message_key_invalid",
                "client_message_key must not be blank",
            )
        if len(key) > _MAX_CLIENT_KEY_LENGTH:
            raise _err(
                422,
                "client_message_key_invalid",
                f"client_message_key must not exceed {_MAX_CLIENT_KEY_LENGTH} characters",
            )

    sender_profile = ensure_profile_identity(session, sender_profile)
    assert sender_profile.node_id is not None  # ensured above
    assert sender_profile.profile_id is not None  # ensured above
    require_participant(
        session, conversation, sender_profile.node_id, sender_profile.profile_id
    )

    now = datetime.now(timezone.utc)
    message = DirectMessage(
        id=uuid.uuid4().hex,
        conversation_id=conversation.id,
        sender_node_id=sender_profile.node_id,
        sender_profile_id=sender_profile.profile_id,
        content_type="text/plain",
        body=text,
        client_message_key=key,
        created_at=now,
    )
    conversation.latest_activity_at = now
    session.add(message)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        existing = session.scalar(
            select(DirectMessage).where(
                DirectMessage.conversation_id == conversation.id,
                DirectMessage.sender_profile_id == sender_profile.profile_id,
                DirectMessage.client_message_key == key,
            )
        )
        if existing is None:  # pragma: no cover - defensive
            raise _err(500, "message_unavailable", "Message unavailable")
        return existing, True

    session.refresh(message)
    return message, False


__all__ = [
    "DirectMessage",
    "DirectMessageConversation",
    "ThreadSpaceNode",
    "UserProfile",
    "claim_username",
    "conversation_payload",
    "create_message",
    "ensure_profile_identity",
    "get_or_create_local_node",
    "get_or_create_owned_profile",
    "list_conversations_for_profile",
    "list_messages",
    "local_node_id",
    "message_payload",
    "participant_addresses",
    "participant_pair_key",
    "require_participant",
    "resolve_or_create_conversation",
    "search_profiles",
    "social_profile_payload",
]
