"""Node-addressed profile-to-profile direct messaging routes.

Social identity and same-node private-messaging API.  Every operation
resolves authority from the authenticated user's owned canonical profile;
caller-supplied identity is never trusted, email is never exposed, and no
Guardian/model/retrieval/memory work is performed by any path here.

Route posture: registered under the ``direct_messages`` label and enabled
only on the hosted/private test profile (``v1-friends-family-web``).  All
other supported profiles leave the label unlisted, which the route-governance
machinery treats as quarantined.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from guardian.core.db import load_guardian_db_from_env
from guardian.core.dependencies import RequestUserScope, get_request_user_scope
from guardian.db.models import User
from guardian.messaging import service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Direct Messages"])


def _db():
    db = load_guardian_db_from_env()
    if db is None:
        raise HTTPException(
            status_code=503,
            detail="Direct messaging database unavailable",
        )
    return db


def _require_owner_id(request_user_scope: RequestUserScope, session) -> str:
    owner_id = str(request_user_scope.user_id or "").strip()
    if not owner_id:
        raise HTTPException(status_code=401, detail="Missing authenticated user")
    if session.get(User, owner_id) is None:
        raise HTTPException(status_code=404, detail="user not found")
    return owner_id


def _profile_address(profile) -> tuple[str, str]:
    """Return the profile's resolved (node_id, profile_id) protocol address."""
    assert profile.node_id is not None  # ensured by service
    assert profile.profile_id is not None  # ensured by service
    return profile.node_id, profile.profile_id


# ── Request models ────────────────────────────────────────────────────────


class SocialIdentityRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)

    model_config = ConfigDict(extra="forbid")


class ResolveRelationshipRequest(BaseModel):
    destination_node_id: str = Field(min_length=1, max_length=64)
    destination_profile_id: str = Field(min_length=1, max_length=64)

    model_config = ConfigDict(extra="forbid")


class CreateConversationRequest(BaseModel):
    origin_project_id: int | None = None
    origin_thread_id: int | None = None
    project_id: int | None = None

    model_config = ConfigDict(extra="forbid")


class ConversationPlacementRequest(BaseModel):
    project_id: int | None = None

    model_config = ConfigDict(extra="forbid")


class SendMessageRequest(BaseModel):
    body: str
    client_message_key: str | None = Field(default=None, max_length=128)

    model_config = ConfigDict(extra="forbid")


# ── Social identity ───────────────────────────────────────────────────────


@router.put("/api/profile/social-identity")
def put_social_identity(
    body: SocialIdentityRequest = Body(...),
    request_user_scope: RequestUserScope = Depends(get_request_user_scope),
) -> dict[str, Any]:
    """Deliberately claim (or rename) the caller's social username.

    The username is validated against the conservative V1 grammar, rejected
    when reserved or already claimed on this node, and never derived from
    the account email.
    """
    db = _db()
    with db.get_session() as session:
        owner_id = _require_owner_id(request_user_scope, session)
        profile = service.get_or_create_owned_profile(session, owner_id)
        profile = service.claim_username(session, profile, body.username)
        return {
            "ok": True,
            "profile": service.social_profile_payload(profile),
        }


@router.get("/api/profile/social-identity")
def get_social_identity(
    request_user_scope: RequestUserScope = Depends(get_request_user_scope),
) -> dict[str, Any]:
    """Read the caller's own social identity (Node_ID + Profile_ID)."""
    db = _db()
    with db.get_session() as session:
        owner_id = _require_owner_id(request_user_scope, session)
        profile = service.get_or_create_owned_profile(session, owner_id)
        return {
            "ok": True,
            "profile": service.social_profile_payload(profile),
        }


# ── Discovery ─────────────────────────────────────────────────────────────


@router.get("/api/direct-messages/profiles")
def search_profiles(
    q: str = Query(default="", max_length=64),
    limit: int = Query(default=20, ge=1, le=20),
    request_user_scope: RequestUserScope = Depends(get_request_user_scope),
) -> dict[str, Any]:
    """Username-oriented social discovery.

    Authenticated and bounded.  Responses contain only deliberately social
    fields (node_id, profile_id, username, display_name, avatar) — email,
    owning_user_id, credentials, and private account state are never
    included.
    """
    db = _db()
    with db.get_session() as session:
        _require_owner_id(request_user_scope, session)
        profiles = service.search_profiles(session, q, limit=limit)
        return {"ok": True, "profiles": profiles}


# ── Relationships ──────────────────────────────────────────────────────────


@router.post("/api/direct-messages/relationships")
def resolve_relationship(
    body: ResolveRelationshipRequest = Body(...),
    request_user_scope: RequestUserScope = Depends(get_request_user_scope),
) -> dict[str, Any]:
    """Resolve/create the canonical relationship for an addressed peer pair."""
    db = _db()
    with db.get_session() as session:
        owner_id = _require_owner_id(request_user_scope, session)
        profile = service.get_or_create_owned_profile(session, owner_id)
        relationship = service.resolve_or_create_relationship(
            session,
            profile,
            body.destination_node_id,
            body.destination_profile_id,
        )
        caller_node_id, caller_profile_id = _profile_address(profile)
        return {
            "ok": True,
            "relationship": service.relationship_payload(
                session, relationship, caller_node_id, caller_profile_id
            ),
        }


@router.get("/api/direct-messages/relationships")
def list_relationships(
    limit: int = Query(default=100, ge=1, le=200),
    request_user_scope: RequestUserScope = Depends(get_request_user_scope),
) -> dict[str, Any]:
    """Return only direct relationships containing the caller's profile."""
    db = _db()
    with db.get_session() as session:
        owner_id = _require_owner_id(request_user_scope, session)
        profile = service.get_or_create_owned_profile(session, owner_id)
        relationships = service.list_relationships_for_profile(
            session, profile, limit=limit
        )
        return {"ok": True, "relationships": relationships}


@router.post("/api/direct-messages/relationships/{relationship_id}/conversations")
def create_relationship_conversation(
    relationship_id: str,
    body: CreateConversationRequest = Body(...),
    request_user_scope: RequestUserScope = Depends(get_request_user_scope),
) -> dict[str, Any]:
    """Create one new Conversation inside a caller-participating Relationship."""
    db = _db()
    with db.get_session() as session:
        owner_id = _require_owner_id(request_user_scope, session)
        profile = service.get_or_create_owned_profile(session, owner_id)
        relationship = session.get(service.DirectMessageRelationship, relationship_id)
        if relationship is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "relationship_not_found",
                    "message": "relationship not found",
                },
            )
        conversation = service.create_conversation(
            session,
            relationship,
            profile,
            origin_project_id=body.origin_project_id,
            origin_thread_id=body.origin_thread_id,
            project_id=body.project_id,
            placement_override_provided="project_id" in body.model_fields_set,
        )
        caller_node_id, caller_profile_id = _profile_address(profile)
        return {
            "ok": True,
            "conversation": service.conversation_payload(
                session, conversation, caller_node_id, caller_profile_id
            ),
        }


@router.get("/api/direct-messages/relationships/{relationship_id}/conversations")
def list_relationship_conversations(
    relationship_id: str,
    limit: int = Query(default=100, ge=1, le=200),
    request_user_scope: RequestUserScope = Depends(get_request_user_scope),
) -> dict[str, Any]:
    """List every caller-visible Conversation in one Relationship."""
    db = _db()
    with db.get_session() as session:
        owner_id = _require_owner_id(request_user_scope, session)
        profile = service.get_or_create_owned_profile(session, owner_id)
        relationship = session.get(service.DirectMessageRelationship, relationship_id)
        if relationship is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "relationship_not_found",
                    "message": "relationship not found",
                },
            )
        conversations = service.list_conversations_for_relationship(
            session, relationship, profile, limit=limit
        )
        return {"ok": True, "conversations": conversations}


@router.patch("/api/direct-messages/conversations/{conversation_id}/placement")
def move_conversation_placement(
    conversation_id: str,
    body: ConversationPlacementRequest = Body(...),
    request_user_scope: RequestUserScope = Depends(get_request_user_scope),
) -> dict[str, Any]:
    """Move only the caller's participant-local Project placement."""
    db = _db()
    with db.get_session() as session:
        owner_id = _require_owner_id(request_user_scope, session)
        profile = service.get_or_create_owned_profile(session, owner_id)
        conversation = session.get(service.DirectMessageConversation, conversation_id)
        if conversation is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "conversation_not_found",
                    "message": "conversation not found",
                },
            )
        service.set_conversation_placement(
            session, conversation, profile, body.project_id
        )
        caller_node_id, caller_profile_id = _profile_address(profile)
        return {
            "ok": True,
            "conversation": service.conversation_payload(
                session, conversation, caller_node_id, caller_profile_id
            ),
        }


# ── Conversations ─────────────────────────────────────────────────────────


@router.get("/api/direct-messages/conversations")
def list_conversations(
    limit: int = Query(default=100, ge=1, le=200),
    request_user_scope: RequestUserScope = Depends(get_request_user_scope),
) -> dict[str, Any]:
    """Participant-scoped conversation list ordered by durable activity."""
    db = _db()
    with db.get_session() as session:
        owner_id = _require_owner_id(request_user_scope, session)
        profile = service.get_or_create_owned_profile(session, owner_id)
        conversations = service.list_conversations_for_profile(
            session, profile, limit=limit
        )
        return {"ok": True, "conversations": conversations}


@router.get("/api/direct-messages/conversations/{conversation_id}")
def get_conversation(
    conversation_id: str,
    request_user_scope: RequestUserScope = Depends(get_request_user_scope),
) -> dict[str, Any]:
    """Read one conversation (authenticated participants only)."""
    db = _db()
    with db.get_session() as session:
        owner_id = _require_owner_id(request_user_scope, session)
        profile = service.get_or_create_owned_profile(session, owner_id)
        conversation = session.get(service.DirectMessageConversation, conversation_id)
        if conversation is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "conversation_not_found",
                    "message": "conversation not found",
                },
            )
        caller_node_id, caller_profile_id = _profile_address(profile)
        return {
            "ok": True,
            "conversation": service.conversation_payload(
                session, conversation, caller_node_id, caller_profile_id
            ),
        }


@router.get("/api/direct-messages/conversations/{conversation_id}/messages")
def read_messages(
    conversation_id: str,
    limit: int = Query(default=100, ge=1, le=200),
    before_id: str | None = Query(default=None, max_length=64),
    request_user_scope: RequestUserScope = Depends(get_request_user_scope),
) -> dict[str, Any]:
    """Participant-scoped, deterministic, bounded message readback."""
    db = _db()
    with db.get_session() as session:
        owner_id = _require_owner_id(request_user_scope, session)
        profile = service.get_or_create_owned_profile(session, owner_id)
        conversation = session.get(service.DirectMessageConversation, conversation_id)
        if conversation is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "conversation_not_found",
                    "message": "conversation not found",
                },
            )
        caller_node_id, caller_profile_id = _profile_address(profile)
        messages = service.list_messages(
            session,
            conversation,
            caller_node_id,
            caller_profile_id,
            limit=limit,
            before_id=before_id,
        )
        return {"ok": True, "messages": messages}


@router.post("/api/direct-messages/conversations/{conversation_id}/messages")
def send_message(
    conversation_id: str,
    body: SendMessageRequest = Body(...),
    request_user_scope: RequestUserScope = Depends(get_request_user_scope),
) -> dict[str, Any]:
    """Durably persist one plain-text message.

    Sender authority is derived from the authenticated user's owned profile
    only.  Persistence is synchronous Postgres truth — an HTTP success means
    the message is durably stored.  Idempotent replays return the original
    message unchanged.  No Guardian execution, retrieval, memory mutation,
    embedding, or ordinary chat-thread work occurs.
    """
    db = _db()
    with db.get_session() as session:
        owner_id = _require_owner_id(request_user_scope, session)
        profile = service.get_or_create_owned_profile(session, owner_id)
        conversation = session.get(service.DirectMessageConversation, conversation_id)
        if conversation is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "conversation_not_found",
                    "message": "conversation not found",
                },
            )
        message, replayed = service.create_message(
            session,
            conversation,
            profile,
            body.body,
            body.client_message_key,
        )
        addresses = service.participant_addresses(session, conversation)
        recipient = next(
            (
                address
                for address in addresses
                if address[1] != message.sender_profile_id
            ),
            None,
        )
        if recipient is None:  # pragma: no cover - defensive
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "message_unavailable",
                    "message": "Message unavailable",
                },
            )
        destination_node_id, destination_profile_id = recipient
        return {
            "ok": True,
            "replayed": replayed,
            "message": service.message_payload(
                message,
                message.sender_node_id,
                message.sender_profile_id,
                destination_node_id,
                destination_profile_id,
            ),
        }


__all__ = ["router"]
