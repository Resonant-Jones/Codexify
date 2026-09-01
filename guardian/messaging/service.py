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
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from guardian.db.models import (
    DirectMessage,
    DirectMessageConversation,
    DirectMessageConversationPlacement,
    DirectMessageRelationship,
    DirectMessageRelationshipParticipant,
    Project,
    ChatThread,
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


# ── Relationships and conversations ───────────────────────────────────────


def participant_pair_key(
    first_node_id: str,
    first_profile_id: str,
    second_node_id: str,
    second_profile_id: str,
) -> str:
    """Canonical unordered pair key for one direct relationship."""
    addresses = sorted(
        [
            f"{first_node_id}:{first_profile_id}",
            f"{second_node_id}:{second_profile_id}",
        ]
    )
    return "|".join(addresses)


def _resolve_local_peer(
    session,
    sender_profile: UserProfile,
    destination_node_id: Any,
    destination_profile_id: Any,
) -> tuple[UserProfile, UserProfile]:
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
    assert sender_profile.node_id is not None
    assert sender_profile.profile_id is not None
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
            "a direct relationship requires two distinct profiles",
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
    return sender_profile, recipient


def resolve_or_create_relationship(
    session,
    sender_profile: UserProfile,
    destination_node_id: Any,
    destination_profile_id: Any,
) -> DirectMessageRelationship:
    """Atomically resolve one canonical relationship for an address pair."""
    sender_profile, recipient = _resolve_local_peer(
        session,
        sender_profile,
        destination_node_id,
        destination_profile_id,
    )
    assert sender_profile.node_id is not None
    assert sender_profile.profile_id is not None
    assert recipient.node_id is not None
    assert recipient.profile_id is not None

    pair_key = participant_pair_key(
        sender_profile.node_id,
        sender_profile.profile_id,
        recipient.node_id,
        recipient.profile_id,
    )
    existing = session.scalar(
        select(DirectMessageRelationship).where(
            DirectMessageRelationship.participant_pair_key == pair_key
        )
    )
    if existing is not None:
        return existing

    relationship = DirectMessageRelationship(
        id=uuid.uuid4().hex,
        participant_pair_key=pair_key,
    )
    session.add(relationship)
    session.flush()

    addresses = sorted(
        [
            (sender_profile.node_id, sender_profile.profile_id),
            (recipient.node_id, recipient.profile_id),
        ],
        key=lambda address: (address[0], address[1]),
    )
    for node_id, profile_id in addresses:
        session.add(
            DirectMessageRelationshipParticipant(
                id=uuid.uuid4().hex,
                relationship_id=relationship.id,
                node_id=node_id,
                profile_id=profile_id,
            )
        )

    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        existing = session.scalar(
            select(DirectMessageRelationship).where(
                DirectMessageRelationship.participant_pair_key == pair_key
            )
        )
        if existing is None:  # pragma: no cover - defensive
            raise _err(500, "relationship_unavailable", "Relationship unavailable")
        return existing

    session.refresh(relationship)
    return relationship


def relationship_participant_addresses(
    session, relationship: DirectMessageRelationship
) -> list[tuple[str, str]]:
    rows = session.scalars(
        select(DirectMessageRelationshipParticipant)
        .where(DirectMessageRelationshipParticipant.relationship_id == relationship.id)
        .order_by(
            DirectMessageRelationshipParticipant.node_id.asc(),
            DirectMessageRelationshipParticipant.profile_id.asc(),
        )
    ).all()
    return [(row.node_id, row.profile_id) for row in rows]


def require_relationship_participant(
    session,
    relationship: DirectMessageRelationship,
    caller_node_id: str,
    caller_profile_id: str,
) -> None:
    participant = session.scalar(
        select(DirectMessageRelationshipParticipant).where(
            DirectMessageRelationshipParticipant.relationship_id == relationship.id,
            DirectMessageRelationshipParticipant.profile_id == caller_profile_id,
            DirectMessageRelationshipParticipant.node_id == caller_node_id,
        )
    )
    if participant is None:
        raise _err(404, "relationship_not_found", "relationship not found")


def relationship_payload(
    session,
    relationship: DirectMessageRelationship,
    caller_node_id: str,
    caller_profile_id: str,
) -> dict[str, Any]:
    require_relationship_participant(
        session, relationship, caller_node_id, caller_profile_id
    )
    addresses = relationship_participant_addresses(session, relationship)
    profiles = session.scalars(
        select(UserProfile).where(
            UserProfile.profile_id.in_([profile_id for _, profile_id in addresses])
        )
    ).all()
    by_profile_id = {profile.profile_id: profile for profile in profiles}
    participants = [
        social_profile_payload(by_profile_id[profile_id])
        for _node_id, profile_id in addresses
        if profile_id in by_profile_id
    ]
    peer = next(
        (
            participant
            for participant in participants
            if participant["profile_id"] != caller_profile_id
        ),
        None,
    )
    return {
        "relationship_id": relationship.id,
        "participants": participants,
        "peer": peer,
        "created_at": relationship.created_at.isoformat(),
        "updated_at": relationship.updated_at.isoformat(),
    }


def list_relationships_for_profile(
    session, profile: UserProfile, limit: int = _DEFAULT_PAGE_LIMIT
) -> list[dict[str, Any]]:
    profile = ensure_profile_identity(session, profile)
    assert profile.node_id is not None
    assert profile.profile_id is not None
    page_limit = min(max(int(limit), 1), _MAX_PAGE_LIMIT)
    relationship_ids = session.scalars(
        select(DirectMessageRelationshipParticipant.relationship_id).where(
            DirectMessageRelationshipParticipant.profile_id == profile.profile_id,
            DirectMessageRelationshipParticipant.node_id == profile.node_id,
        )
    ).all()
    if not relationship_ids:
        return []
    relationships = session.scalars(
        select(DirectMessageRelationship)
        .where(DirectMessageRelationship.id.in_(relationship_ids))
        .order_by(
            DirectMessageRelationship.updated_at.desc(),
            DirectMessageRelationship.id.asc(),
        )
        .limit(page_limit)
    ).all()
    return [
        relationship_payload(session, relationship, profile.node_id, profile.profile_id)
        for relationship in relationships
    ]


def _get_relationship_or_404(
    session, relationship_id: Any
) -> DirectMessageRelationship:
    relationship = session.get(DirectMessageRelationship, str(relationship_id))
    if relationship is None:
        raise _err(404, "relationship_not_found", "relationship not found")
    return relationship


def _coerce_source_id(raw_value: Any, field: str) -> int | None:
    if raw_value is None:
        return None
    if isinstance(raw_value, bool):
        raise _err(422, f"{field}_invalid", f"{field} must be an integer")
    try:
        value = int(raw_value)
    except (TypeError, ValueError) as exc:
        raise _err(422, f"{field}_invalid", f"{field} must be an integer") from exc
    if value <= 0:
        raise _err(422, f"{field}_invalid", f"{field} must be positive")
    return value


def _owned_project_id(
    session,
    profile: UserProfile,
    raw_project_id: Any,
    *,
    field: str,
) -> int | None:
    project_id = _coerce_source_id(raw_project_id, field)
    if project_id is None:
        return None
    accessible = session.scalar(
        select(Project.id).where(
            Project.id == project_id,
            Project.user_id == profile.user_id,
        )
    )
    if accessible is None:
        raise _err(404, f"{field}_not_found", f"{field} not found")
    return project_id


def _validated_origin(
    session,
    creator_profile: UserProfile,
    origin_project_id: Any,
    origin_thread_id: Any,
) -> tuple[int | None, int | None]:
    project_id = _owned_project_id(
        session,
        creator_profile,
        origin_project_id,
        field="origin_project_id",
    )
    thread_id = _coerce_source_id(origin_thread_id, "origin_thread_id")
    if thread_id is None:
        return project_id, None

    thread = session.execute(
        select(ChatThread.id, ChatThread.project_id).where(
            ChatThread.id == thread_id,
            ChatThread.user_id == creator_profile.user_id,
        )
    ).one_or_none()
    if thread is None:
        raise _err(404, "origin_thread_id_not_found", "origin_thread_id not found")

    thread_project_id = thread.project_id
    if project_id is None and thread_project_id is not None:
        project_id = _owned_project_id(
            session,
            creator_profile,
            thread_project_id,
            field="origin_project_id",
        )
    elif project_id != thread_project_id:
        raise _err(
            422,
            "origin_thread_project_mismatch",
            "origin_thread_id does not belong to origin_project_id",
        )
    return project_id, thread_id


def create_conversation(
    session,
    relationship: DirectMessageRelationship,
    creator_profile: UserProfile,
    *,
    origin_project_id: Any = None,
    origin_thread_id: Any = None,
    project_id: Any = None,
    placement_override_provided: bool = False,
) -> DirectMessageConversation:
    """Create a new distinct conversation with bounded immutable provenance."""
    creator_profile = ensure_profile_identity(session, creator_profile)
    assert creator_profile.node_id is not None
    assert creator_profile.profile_id is not None
    require_relationship_participant(
        session,
        relationship,
        creator_profile.node_id,
        creator_profile.profile_id,
    )
    resolved_origin_project_id, resolved_origin_thread_id = _validated_origin(
        session,
        creator_profile,
        origin_project_id,
        origin_thread_id,
    )
    if placement_override_provided:
        creator_project_id = _owned_project_id(
            session,
            creator_profile,
            project_id,
            field="project_id",
        )
    else:
        creator_project_id = resolved_origin_project_id

    now = datetime.now(timezone.utc)
    conversation = DirectMessageConversation(
        id=uuid.uuid4().hex,
        relationship_id=relationship.id,
        created_by_profile_id=creator_profile.profile_id,
        origin_project_id=resolved_origin_project_id,
        origin_thread_id=resolved_origin_thread_id,
        kind="direct",
        created_at=now,
        latest_activity_at=now,
    )
    relationship.updated_at = now
    session.add(conversation)
    session.flush()

    for _node_id, participant_profile_id in relationship_participant_addresses(
        session, relationship
    ):
        session.add(
            DirectMessageConversationPlacement(
                id=uuid.uuid4().hex,
                conversation_id=conversation.id,
                profile_id=participant_profile_id,
                project_id=(
                    creator_project_id
                    if participant_profile_id == creator_profile.profile_id
                    else None
                ),
                created_at=now,
                updated_at=now,
            )
        )

    session.commit()
    session.refresh(conversation)
    return conversation


def list_conversations_for_relationship(
    session,
    relationship: DirectMessageRelationship,
    profile: UserProfile,
    limit: int = _DEFAULT_PAGE_LIMIT,
) -> list[dict[str, Any]]:
    profile = ensure_profile_identity(session, profile)
    assert profile.node_id is not None
    assert profile.profile_id is not None
    require_relationship_participant(
        session, relationship, profile.node_id, profile.profile_id
    )
    page_limit = min(max(int(limit), 1), _MAX_PAGE_LIMIT)
    conversations = session.scalars(
        select(DirectMessageConversation)
        .where(DirectMessageConversation.relationship_id == relationship.id)
        .order_by(
            DirectMessageConversation.latest_activity_at.desc(),
            DirectMessageConversation.created_at.desc(),
            DirectMessageConversation.id.asc(),
        )
        .limit(page_limit)
    ).all()
    latest_by_conversation = latest_message_for_conversations(
        session, [conversation.id for conversation in conversations]
    )
    return [
        conversation_payload(
            session,
            conversation,
            profile.node_id,
            profile.profile_id,
            latest_message=latest_by_conversation.get(conversation.id),
        )
        for conversation in conversations
    ]


def participant_addresses(
    session, conversation: DirectMessageConversation
) -> list[tuple[str, str]]:
    """Return canonical Relationship participant protocol addresses."""
    relationship = _get_relationship_or_404(session, conversation.relationship_id)
    return relationship_participant_addresses(session, relationship)


def require_participant(
    session,
    conversation: DirectMessageConversation,
    caller_node_id: str,
    caller_profile_id: str,
) -> None:
    """Authorize a conversation through canonical Relationship membership."""
    relationship = session.get(DirectMessageRelationship, conversation.relationship_id)
    if relationship is None:
        raise _err(404, "conversation_not_found", "conversation not found")
    try:
        require_relationship_participant(
            session, relationship, caller_node_id, caller_profile_id
        )
    except HTTPException as exc:
        if exc.status_code == 404:
            raise _err(
                404,
                "conversation_not_found",
                "conversation not found",
            ) from None
        raise


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

    relationship_ids = session.scalars(
        select(DirectMessageRelationshipParticipant.relationship_id).where(
            DirectMessageRelationshipParticipant.profile_id == profile.profile_id,
            DirectMessageRelationshipParticipant.node_id == profile.node_id,
        )
    ).all()
    if not relationship_ids:
        return []

    conversations = session.scalars(
        select(DirectMessageConversation)
        .where(DirectMessageConversation.relationship_id.in_(relationship_ids))
        .order_by(
            DirectMessageConversation.latest_activity_at.desc(),
            DirectMessageConversation.id.desc(),
        )
        .limit(page_limit)
    ).all()
    latest_by_conversation = latest_message_for_conversations(
        session, [conversation.id for conversation in conversations]
    )
    return [
        conversation_payload(
            session,
            conversation,
            profile.node_id,
            profile.profile_id,
            latest_message=latest_by_conversation.get(conversation.id),
        )
        for conversation in conversations
    ]


# ── Inbox latest-message projection ──────────────────────────────────────

_MAX_LATEST_PREVIEW_CHARS = 160


def _latest_preview(body: str) -> str:
    """Bounded single-line preview for Inbox rows.

    The full body remains available only through the message readback
    route; the projection never emits the complete body.
    """
    compact = " ".join(str(body or "").split())
    if len(compact) <= _MAX_LATEST_PREVIEW_CHARS:
        return compact
    return compact[:_MAX_LATEST_PREVIEW_CHARS] + "…"


def latest_message_for_conversations(
    session, conversation_ids: list[str]
) -> dict[str, DirectMessage]:
    """One bounded query: each conversation's latest message.

    The winner per conversation is determined with the same ordering as
    the message readback list — ``(created_at DESC, id DESC)`` — so the
    projected message is always the newest participant-visible message
    for the Inbox row.  This is a single round trip for the whole page;
    it never fetches message history per row.
    """
    if not conversation_ids:
        return {}
    ranked = (
        select(
            DirectMessage.id.label("message_id"),
            func.row_number()
            .over(
                partition_by=DirectMessage.conversation_id,
                order_by=(
                    DirectMessage.created_at.desc(),
                    DirectMessage.id.desc(),
                ),
            )
            .label("rank"),
        )
        .where(DirectMessage.conversation_id.in_(conversation_ids))
        .subquery()
    )
    messages = session.scalars(
        select(DirectMessage).where(
            DirectMessage.id.in_(
                select(ranked.c.message_id).where(ranked.c.rank == 1)
            )
        )
    ).all()
    return {message.conversation_id: message for message in messages}


def latest_message_projection(message: DirectMessage) -> dict[str, Any]:
    """Bounded participant-visible latest-message projection."""
    return {
        "message_id": message.id,
        "sender_profile_id": message.sender_profile_id,
        "preview": _latest_preview(message.body),
        "created_at": message.created_at,
    }


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


def _profile_can_access_project(
    session, profile: UserProfile, project_id: int | None
) -> bool:
    if project_id is None:
        return False
    return (
        session.scalar(
            select(Project.id).where(
                Project.id == project_id,
                Project.user_id == profile.user_id,
            )
        )
        is not None
    )


def _profile_can_access_thread(
    session, profile: UserProfile, thread_id: int | None
) -> bool:
    if thread_id is None:
        return False
    return (
        session.scalar(
            select(ChatThread.id).where(
                ChatThread.id == thread_id,
                ChatThread.user_id == profile.user_id,
            )
        )
        is not None
    )


def _placement_for_profile(
    session,
    conversation: DirectMessageConversation,
    profile_id: str,
) -> DirectMessageConversationPlacement | None:
    return session.scalar(
        select(DirectMessageConversationPlacement).where(
            DirectMessageConversationPlacement.conversation_id == conversation.id,
            DirectMessageConversationPlacement.profile_id == profile_id,
        )
    )


def set_conversation_placement(
    session,
    conversation: DirectMessageConversation,
    profile: UserProfile,
    project_id: Any,
) -> DirectMessageConversationPlacement:
    """Update only the caller's local Project placement."""
    profile = ensure_profile_identity(session, profile)
    assert profile.node_id is not None
    assert profile.profile_id is not None
    require_participant(session, conversation, profile.node_id, profile.profile_id)
    resolved_project_id = _owned_project_id(
        session,
        profile,
        project_id,
        field="project_id",
    )
    now = datetime.now(timezone.utc)
    placement = _placement_for_profile(session, conversation, profile.profile_id)
    if placement is None:
        placement = DirectMessageConversationPlacement(
            id=uuid.uuid4().hex,
            conversation_id=conversation.id,
            profile_id=profile.profile_id,
            created_at=now,
        )
        session.add(placement)
    placement.project_id = resolved_project_id
    placement.updated_at = now
    session.commit()
    session.refresh(placement)
    return placement


def conversation_payload(
    session,
    conversation: DirectMessageConversation,
    caller_node_id: str,
    caller_profile_id: str,
    *,
    latest_message: DirectMessage | None = None,
) -> dict[str, Any]:
    """Safe participant-visible conversation payload."""
    require_participant(session, conversation, caller_node_id, caller_profile_id)
    caller_profile = session.scalar(
        select(UserProfile).where(
            UserProfile.profile_id == caller_profile_id,
            UserProfile.node_id == caller_node_id,
        )
    )
    if caller_profile is None:  # pragma: no cover - defensive
        raise _err(404, "conversation_not_found", "conversation not found")
    placement = _placement_for_profile(session, conversation, caller_profile_id)
    visible_origin_project_id = (
        conversation.origin_project_id
        if _profile_can_access_project(
            session, caller_profile, conversation.origin_project_id
        )
        else None
    )
    visible_origin_thread_id = (
        conversation.origin_thread_id
        if _profile_can_access_thread(
            session, caller_profile, conversation.origin_thread_id
        )
        else None
    )
    if latest_message is None:
        latest_message = latest_message_for_conversations(
            session, [conversation.id]
        ).get(conversation.id)
    return {
        "conversation_id": conversation.id,
        "relationship_id": conversation.relationship_id,
        "kind": conversation.kind,
        "created_at": conversation.created_at,
        "latest_activity_at": conversation.latest_activity_at,
        "participants": _participant_social_payloads(session, conversation),
        "origin": {
            "created_by_profile_id": conversation.created_by_profile_id,
            "origin_project_id": visible_origin_project_id,
            "origin_thread_id": visible_origin_thread_id,
            "created_at": conversation.created_at,
        },
        "placement": {
            "project_id": placement.project_id if placement is not None else None,
            "created_at": placement.created_at if placement is not None else None,
            "updated_at": placement.updated_at if placement is not None else None,
        },
        "latest_message": (
            latest_message_projection(latest_message)
            if latest_message is not None
            else None
        ),
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
    "DirectMessageConversationPlacement",
    "DirectMessageRelationship",
    "ThreadSpaceNode",
    "UserProfile",
    "claim_username",
    "conversation_payload",
    "create_conversation",
    "create_message",
    "ensure_profile_identity",
    "get_or_create_local_node",
    "get_or_create_owned_profile",
    "latest_message_for_conversations",
    "latest_message_projection",
    "list_conversations_for_profile",
    "list_conversations_for_relationship",
    "list_messages",
    "list_relationships_for_profile",
    "local_node_id",
    "message_payload",
    "participant_addresses",
    "participant_pair_key",
    "relationship_payload",
    "require_participant",
    "resolve_or_create_relationship",
    "search_profiles",
    "set_conversation_placement",
    "social_profile_payload",
]
