"""Route-neutral preparation for explicit Hosted Room Guardian invocations."""

from __future__ import annotations

from dataclasses import dataclass
import uuid
from typing import Any

from sqlalchemy import func, select

from guardian.core.hosted_room_completion_context import (
    HostedRoomCompletionValidationError,
    ValidatedHostedRoomCompletionContext,
    validate_hosted_room_completion_context,
)
from guardian.core.request_correlation import normalize_request_id
from guardian.db.models import ChatThread, HostedRoom, HostedRoomParticipant
from guardian.hosted_rooms.actor_tokens import (
    GUARDIAN_REF,
    RESIDENT_SOURCE,
)
from guardian.tasks.types import ChatCompletionTask, HostedRoomInvocationMetadata


class HostedRoomInvocationPreparationError(RuntimeError):
    """Safe, bounded failure raised before an invocation reaches enqueue."""

    _CODES = frozenset(
        {
            "hosted_room_not_found",
            "hosted_room_inactive",
            "hosted_room_thread_mismatch",
            "hosted_room_source_message_invalid",
            "hosted_room_actor_invalid",
            "hosted_room_actor_inactive",
            "hosted_room_requester_invalid",
            "hosted_room_authority_revoked",
        }
    )

    def __init__(self, code: str) -> None:
        self.code = (
            code
            if code in self._CODES
            else "hosted_room_source_message_invalid"
        )
        super().__init__(self.code)


@dataclass(frozen=True)
class PreparedHostedRoomGuardianInvocation:
    """Validated identities and canonical task ready for shared enqueue."""

    room_id: str
    thread_id: int
    source_message_id: int
    guardian_participant_id: str
    validated_context: ValidatedHostedRoomCompletionContext
    task: ChatCompletionTask
    turn_id: str
    request_id: str


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _fail(code: str) -> None:
    raise HostedRoomInvocationPreparationError(code)


def prepare_hosted_room_guardian_invocation(
    chatlog_db: Any,
    *,
    room_id: str,
    source_message_id: int,
    actor_participant_id: str,
    requester_authority: str,
    requester_participant_id: str | None,
    request_id: str,
) -> PreparedHostedRoomGuardianInvocation:
    """Validate a room invocation and construct the canonical chat task.

    Authentication and cookie/session parsing remain route responsibilities.
    This operation accepts only the resulting authority context and never
    accepts or returns credentials.
    """

    normalized_room_id = _clean(room_id)
    normalized_actor_id = _clean(actor_participant_id)
    normalized_requester_id = _clean(requester_participant_id) or None
    normalized_request_id, _ = normalize_request_id(request_id)
    if not normalized_room_id or not normalized_actor_id:
        _fail("hosted_room_actor_invalid")
    if isinstance(source_message_id, bool) or not isinstance(source_message_id, int):
        _fail("hosted_room_source_message_invalid")
    if source_message_id <= 0:
        _fail("hosted_room_source_message_invalid")

    with chatlog_db.get_session() as session:
        room = session.get(HostedRoom, normalized_room_id)
        if room is None:
            _fail("hosted_room_not_found")
        if _clean(room.status) != "active":
            _fail("hosted_room_inactive")
        if not room.backing_thread_id or session.get(
            ChatThread, room.backing_thread_id
        ) is None:
            _fail("hosted_room_thread_mismatch")

        active_guardians = session.scalars(
            select(HostedRoomParticipant).where(
                HostedRoomParticipant.room_id == room.id,
                HostedRoomParticipant.kind == "agent",
                HostedRoomParticipant.role == "agent",
                HostedRoomParticipant.state == "active",
                HostedRoomParticipant.actor_source == RESIDENT_SOURCE,
                HostedRoomParticipant.actor_ref == GUARDIAN_REF,
            )
        ).all()
        if len(active_guardians) != 1:
            _fail("hosted_room_actor_invalid")
        if active_guardians[0].id != normalized_actor_id:
            _fail("hosted_room_actor_invalid")

        metadata = HostedRoomInvocationMetadata(
            room_id=normalized_room_id,
            source_message_id=source_message_id,
            actor_participant_id=normalized_actor_id,
            actor_source=RESIDENT_SOURCE,
            actor_ref=GUARDIAN_REF,
            requester_authority=requester_authority,
            requester_participant_id=normalized_requester_id,
        )
        turn_id = str(uuid.uuid4())
        task = ChatCompletionTask(
            request_id=normalized_request_id,
            user_id=room.owner_account_id,
            thread_id=room.backing_thread_id,
            latest_turn_message_id=source_message_id,
            provider=None,
            model=None,
            selection_source=None,
            provider_pinned=False,
            max_context=50,
            depth_mode="normal",
            hosted_room_invocation=metadata,
            origin=f"api:hosted_room.invoke|turn_id={turn_id}",
        )
        task.turn_id = turn_id

    try:
        validated_context = validate_hosted_room_completion_context(
            chatlog_db,
            task,
        )
    except HostedRoomCompletionValidationError as exc:
        raise HostedRoomInvocationPreparationError(exc.code) from exc

    return PreparedHostedRoomGuardianInvocation(
        room_id=validated_context.room_id,
        thread_id=validated_context.thread_id,
        source_message_id=validated_context.source_message_id,
        guardian_participant_id=validated_context.actor_participant_id,
        validated_context=validated_context,
        task=task,
        turn_id=turn_id,
        request_id=normalized_request_id,
    )


__all__ = [
    "HostedRoomInvocationPreparationError",
    "PreparedHostedRoomGuardianInvocation",
    "prepare_hosted_room_guardian_invocation",
]
