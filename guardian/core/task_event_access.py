"""Task-event stream resource authorization (ADR-091 + ADR-092).

``task_id`` is an identifier, never authority. Redis task-event state is
transport and never decides ownership. The durable ``ChatCompletionAttempt``
binding is the only task-to-resource authority, and the canonical thread it
resolves to is the authorization resource:

    task_id
      -> ChatCompletionAttempt.backend_task_id
      -> canonical thread_id
      -> require_thread_read_access(...)
      -> only then Redis task-event transport

This module expresses the already-accepted ADR-092 principal-resolution and
mixed-lane contract for exactly one protected surface: task-event SSE. It
introduces no new identity, ownership, or credential-class semantics.

The ordering below is load-bearing and is the whole point of the repair:
principal resolution (including mixed-lane rejection) happens before the
durable task lookup, durable lineage resolution happens before thread
authorization, and thread authorization happens before any Redis event read.
A denied request therefore performs zero Redis consumption and cannot reveal
whether foreign task-event data exists.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Union

from fastapi import HTTPException, Request

from guardian.core.auth import (
    ACCOUNT_SESSION_PURPOSE,
    OPERATOR_SESSION_PURPOSE,
    get_verified_session_token_purpose,
    resolve_account_session_subject,
)
from guardian.core.db import (
    get_chat_completion_attempt_by_task_id,
    load_guardian_db_from_env,
)
from guardian.core.dependencies import (
    RequestUserScope,
    _auth_mode,
    get_request_user_scope,
)
from guardian.core.hosted_room_session import (
    HostedRoomGuestPrincipal,
    decode_principal,
    extract_session_token_from_request,
)
from guardian.core.preview_access import is_private_preview, require_preview_principal
from guardian.core.thread_access import require_thread_read_access

TaskEventPrincipal = Union[RequestUserScope, HostedRoomGuestPrincipal]

ACCOUNT_LANE = "account"
GUEST_LANE = "hosted_room_guest"
OPERATOR_LANE = "operator"

#: Presence-only marker for signed selector material whose purpose is absent,
#: malformed, or unclassifiable. Per ADR-092 such material establishes neither
#: the account nor the operator lane and is never account authority; it is
#: evidence of a presented lane, never of a valid one.
_UNCLASSIFIED_SIGNED_SELECTOR = "unclassifiable_signed_selector"

MIXED_PRINCIPAL_DETAIL = {
    "error": "mixed_principal_credentials",
    "message": "Conflicting authentication contexts",
}


@dataclass(frozen=True)
class TaskEventAuthorization:
    """Bounded proof that a caller may consume one task's event stream."""

    task_id: str
    thread_id: int
    principal: TaskEventPrincipal
    principal_kind: str


def _text(value: object) -> str:
    return str(value or "").strip()


def _signed_selector_material(request: Request) -> list[str]:
    """Nonempty ``Authorization`` bearer / ``gc_session`` selector material.

    Order is deterministic (bearer before cookie) so a client presenting the
    same credential lane through both selectors resolves predictably.
    """
    material: list[str] = []
    authorization = request.headers.get("Authorization") or ""
    if authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
        if token:
            material.append(token)
    cookie = _text(request.cookies.get("gc_session"))
    if cookie:
        material.append(cookie)
    return material


def _raw_operator_selector_present(request: Request) -> bool:
    """True when nonempty raw Guardian key material is presented.

    On this route a raw key is declared **operator-selector** material only.
    It is never a service capability and never an account credential, so it
    can fill exactly one role here.
    """
    return bool(
        _text(request.headers.get("X-API-Key"))
        or _text(request.headers.get("X-Guardian-Key"))
    )


def _account_selector(request: Request) -> str | None:
    for token in _signed_selector_material(request):
        if get_verified_session_token_purpose(token) == ACCOUNT_SESSION_PURPOSE:
            return token
    return None


def _classify_principal_lanes(request: Request) -> set[str]:
    """Classify credential *presence* across principal lanes.

    Detection happens before validating any credential and before any task,
    thread, room, or Redis lookup. Purpose is read from the signed material
    itself; an unverified purpose is presence evidence only.
    """
    lanes: set[str] = set()
    signed = _signed_selector_material(request)
    purposes = {get_verified_session_token_purpose(token) for token in signed}

    if OPERATOR_SESSION_PURPOSE in purposes:
        lanes.add(OPERATOR_LANE)
    if ACCOUNT_SESSION_PURPOSE in purposes:
        lanes.add(ACCOUNT_LANE)
    if _raw_operator_selector_present(request):
        lanes.add(OPERATOR_LANE)
    if extract_session_token_from_request(request):
        lanes.add(GUEST_LANE)
    if signed and not purposes.intersection(
        {ACCOUNT_SESSION_PURPOSE, OPERATOR_SESSION_PURPOSE}
    ):
        lanes.add(_UNCLASSIFIED_SIGNED_SELECTOR)
    return lanes


def _reject_mixed_lanes(lanes: set[str]) -> None:
    """Reject mixed principal lanes before any protected resource lookup.

    The response reveals neither credential's validity nor the existence of a
    task, thread, or room.
    """
    if len(lanes) > 1:
        raise HTTPException(status_code=400, detail=dict(MIXED_PRINCIPAL_DETAIL))


def _remote_multi_principal_boundary() -> bool:
    """True at the remote/private-preview boundary ADR-092 governs.

    Deliberate local/single-user identity resolution stays governed by the
    local runtime-mode contract and remains outside the remote mixed-lane rule.
    """
    return is_private_preview() or _auth_mode() == "remote"


def _account_principal(subject: str) -> RequestUserScope:
    return RequestUserScope(
        user_id=subject,
        subject_id=subject,
        account_id=subject,
        multi_user_enabled=True,
    )


def resolve_task_event_principal(request: Request) -> TaskEventPrincipal:
    """Resolve exactly one typed principal for the task-event surface.

    Resolves a canonical authenticated account scope or an eligible Hosted
    Room guest principal. There is no precedence and no cross-lane fallback:
    a request must intentionally present one principal lane.
    """
    guest_token = extract_session_token_from_request(request)

    if not _remote_multi_principal_boundary():
        # Local single-user posture keeps its existing identity contract.
        if guest_token:
            return decode_principal(guest_token)
        return get_request_user_scope(request)

    _reject_mixed_lanes(_classify_principal_lanes(request))

    if guest_token:
        # Purpose-scoped guest principal; never reinterpreted as an account.
        return decode_principal(guest_token)

    account_selector = _account_selector(request)
    if account_selector is None:
        raise HTTPException(status_code=401, detail="Account session required")

    subject = resolve_account_session_subject(account_selector)
    if is_private_preview():
        preview = require_preview_principal(request)
        if preview.email != subject:
            raise HTTPException(status_code=401, detail="Account session mismatch")
    return _account_principal(subject)


def _task_not_found() -> HTTPException:
    return HTTPException(
        status_code=404, detail={"error": "not_found", "message": "Task not found"}
    )


def resolve_task_thread_id(chatlog_db, task_id: str) -> int:
    """Resolve the canonical thread for a task through its durable attempt.

    Fails closed when no durable ``ChatCompletionAttempt`` binds the task.
    Ownership is never inferred from Redis payloads, task IDs, event contents,
    debug fields, request IDs, or frontend state.
    """
    attempt = get_chat_completion_attempt_by_task_id(chatlog_db, task_id)
    if not attempt:
        raise _task_not_found()
    raw_thread_id = attempt.get("thread_id")
    if raw_thread_id is None:
        raise _task_not_found()
    try:
        return int(raw_thread_id)
    except (TypeError, ValueError):
        raise _task_not_found() from None


def authorize_task_event_stream(
    *, task_id: str, request: Request, chatlog_db
) -> TaskEventAuthorization:
    """Authorize a task-event stream against canonical durable authority.

    Callers must invoke this before creating any transport side effect. On
    denial this raises before ``task_events.read_events`` can be called, so a
    denied request performs zero Redis event reads.
    """
    principal = resolve_task_event_principal(request)
    thread_id = resolve_task_thread_id(chatlog_db, task_id)

    if isinstance(principal, HostedRoomGuestPrincipal):
        db = load_guardian_db_from_env()
        if db is None:
            raise HTTPException(
                status_code=503, detail="Hosted Room database unavailable"
            )
        with db.get_session() as session:
            # Guest authority is room-scoped: the guest may read only the
            # backing thread of its currently valid room membership.
            require_thread_read_access(thread_id, principal, session=session)
        principal_kind = GUEST_LANE
    else:
        require_thread_read_access(
            thread_id,
            principal,
            thread_lookup=chatlog_db.get_chat_thread,
        )
        principal_kind = ACCOUNT_LANE

    return TaskEventAuthorization(
        task_id=task_id,
        thread_id=thread_id,
        principal=principal,
        principal_kind=principal_kind,
    )