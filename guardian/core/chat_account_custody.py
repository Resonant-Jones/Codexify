"""Resolve ordinary-chat identity from original custody and live authority.

Consumers separately authorize any evidence read, model exposure, or connector
call. A resolution is ephemeral and must be repeated on retry.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from guardian.core.db import has_native_ordinary_chat_origin
from guardian.core.project_ownership import classify_project_ownership
from guardian.db.models import (
    ChatCompletionAttempt,
    ChatMessage,
    ChatThread,
    Project,
    User,
)
from guardian.tasks.chat_deadline import (
    AcceptedChatTaskDeadline,
    accepted_chat_deadline_for_task,
    parse_accepted_chat_task_deadline,
)


class ChatAccountCustodyUnavailable(ValueError):
    """Bounded refusal; contains no account, credential or content values."""


class ChatAccountAcceptancePending(ChatAccountCustodyUnavailable):
    """Queue published before acceptance acknowledgement; never execute yet.

    Future dispatch must reconcile/retry within the original deadline rather
    than silently losing work or treating this as permission. This slice adds
    no scheduler or retry behavior.
    """


def ordinary_chat_acceptance_account(task: Any, scope: Any) -> str | None:
    """Consume route-resolved context, never manufacture it from a queue task."""
    if scope is None:
        return None
    from guardian.core.dependencies import RequestUserScope

    if (
        not isinstance(scope, RequestUserScope)
        or not scope.user_id
        or scope.user_id != str(task.user_id or "")
        or (scope.account_id and scope.account_id != scope.user_id)
        or str(task.origin or "").split("|", 1)[0] != "api:chat.complete"
        or getattr(task, "hosted_room_invocation", None) is not None
    ):
        raise ChatAccountCustodyUnavailable("account_acceptance_unavailable")
    # Legacy local API-key/debug scopes carry no independently resolved account
    # principal. Keep their existing lifecycle, without creating new custody.
    # External subject IDs may legitimately differ from canonical account IDs.
    if not scope.account_id:
        return None
    return scope.account_id


@dataclass(frozen=True)
class AcceptedChatAccountBinding:
    """Ephemeral verified lineage; not a bearer capability or provider grant."""

    account_id: str
    request_id: str
    backend_task_id: str
    thread_id: int
    turn_id: str
    tool_turn_id: str
    command_id: str
    args_hash: str


@dataclass(frozen=True)
class AcceptedChatWorkIdentity:
    """Ephemeral identity before a tool decision. Project placement grants no scope."""

    account_id: str
    request_id: str
    backend_task_id: str
    thread_id: int
    turn_id: str
    accepted_user_message_id: int
    current_project_id: int | None


def eligible_chat_source_id(
    session: Session,
    *,
    message_id: int,
    account_id: str,
    thread_id: int,
    lock_source: bool = False,
) -> int | None:
    """Check the exact ordinary user source without selecting its body."""
    if type(message_id) is not int or not 0 < message_id < 2**63:
        return None
    query = session.query(ChatMessage.extra_meta).filter_by(
        id=message_id,
        thread_id=thread_id,
        user_id=account_id,
        role="user",
        kind="chat",
        hosted_room_participant_id=None,
        sender_display_name_snapshot=None,
    )
    if lock_source:
        # Acceptance must hold source eligibility through the attempt insert.
        query = query.with_for_update(read=True)
    if has_native_ordinary_chat_origin(query.scalar()):
        return message_id
    return None


_DENIED = "accepted_chat_account_unavailable"


@contextmanager
def _live_accepted_chat(
    db: Any, task: Any
) -> Iterator[
    tuple[Session, ChatCompletionAttempt, ChatThread, AcceptedChatTaskDeadline]
]:
    from guardian.core.preview_access import is_private_preview, role_for_preview_email

    try:
        if (
            str(task.origin or "").split("|", 1)[0] != "api:chat.complete"
            or getattr(task, "hosted_room_invocation", None) is not None
        ):
            raise ChatAccountCustodyUnavailable(_DENIED)
        with db._sa_session() as session:
            attempt = (
                session.query(ChatCompletionAttempt)
                .filter_by(request_id=task.request_id)
                .with_for_update()
                .one_or_none()
            )
            if attempt is None or (
                attempt.request_id != task.request_id
                or attempt.backend_task_id != task.task_id
                or attempt.thread_id != task.thread_id
                or attempt.turn_id != task.turn_id
                or not attempt.accepted_account_id
                or attempt.accepted_account_id != task.user_id
                or attempt.completed_message_id is not None
                or attempt.terminal_event_type is not None
            ):
                raise ChatAccountCustodyUnavailable(_DENIED)
            account_id = attempt.accepted_account_id
            thread = (
                session.query(ChatThread).filter_by(id=attempt.thread_id).one_or_none()
            )
            user = session.query(User).filter_by(id=account_id).one_or_none()
            if thread is None or user is None or thread.user_id != account_id:
                raise ChatAccountCustodyUnavailable(_DENIED)
            if thread.project_id is not None:
                project = (
                    session.query(Project).filter_by(id=thread.project_id).one_or_none()
                )
                ownership = classify_project_ownership(project)
                if (
                    ownership.canonical_owner_id != account_id
                    or ownership.has_authority_conflict
                ):
                    raise ChatAccountCustodyUnavailable(_DENIED)
            if (
                is_private_preview()
                and role_for_preview_email(user.email or user.id) is None
            ):
                raise ChatAccountCustodyUnavailable(_DENIED)
            deadline = parse_accepted_chat_task_deadline(
                attempt.deadline_snapshot or {}
            )
            if (
                deadline is None
                or deadline != accepted_chat_deadline_for_task(task)
                or datetime.now(timezone.utc) >= deadline.work_deadline_at
            ):
                raise ChatAccountCustodyUnavailable(_DENIED)
            if attempt.accepted_at is None:
                raise ChatAccountAcceptancePending("accepted_chat_account_pending")
            yield session, attempt, thread, deadline
    except ChatAccountCustodyUnavailable:
        raise
    except Exception:
        raise ChatAccountCustodyUnavailable(_DENIED) from None


def resolve_accepted_chat_work_identity(db: Any, task: Any) -> AcceptedChatWorkIdentity:
    """Resolve accepted source identity without a checkpoint or a Recall grant."""
    from guardian.queue.redis_queue import is_cancelled

    with _live_accepted_chat(db, task) as (session, attempt, thread, deadline):
        source_id = attempt.accepted_user_message_id
        queued_source_id = getattr(task, "latest_turn_message_id", None)
        if (
            source_id is None
            or type(queued_source_id) is not int
            or queued_source_id != source_id
            or eligible_chat_source_id(
                session,
                message_id=source_id,
                account_id=attempt.accepted_account_id,
                thread_id=attempt.thread_id,
            )
            is None
            or is_cancelled(attempt.backend_task_id)
            or datetime.now(timezone.utc) >= deadline.work_deadline_at
        ):
            raise ChatAccountCustodyUnavailable(_DENIED)
        return AcceptedChatWorkIdentity(
            account_id=attempt.accepted_account_id,
            request_id=attempt.request_id,
            backend_task_id=attempt.backend_task_id,
            thread_id=attempt.thread_id,
            turn_id=attempt.turn_id,
            accepted_user_message_id=source_id,
            current_project_id=thread.project_id,
        )


def resolve_accepted_chat_account(
    db: Any,
    task: Any,
    *,
    command_id: str,
    args_hash: str,
) -> AcceptedChatAccountBinding:
    """Re-read live custody and require the exact existing frozen decision."""
    from guardian.queue.redis_queue import is_cancelled

    if (
        not command_id
        or not isinstance(args_hash, str)
        or len(args_hash) != 64
        or any(c not in "0123456789abcdef" for c in args_hash)
    ):
        raise ChatAccountCustodyUnavailable(_DENIED)
    with _live_accepted_chat(db, task) as (_, attempt, _, _):
        if (
            not attempt.tool_turn_id
            or attempt.tool_checkpoint_at is None
            or attempt.tool_command_id != command_id
            or attempt.tool_args_hash != args_hash
            or is_cancelled(attempt.backend_task_id)
        ):
            raise ChatAccountCustodyUnavailable(_DENIED)
        return AcceptedChatAccountBinding(
            account_id=attempt.accepted_account_id,
            request_id=attempt.request_id,
            backend_task_id=attempt.backend_task_id,
            thread_id=attempt.thread_id,
            turn_id=attempt.turn_id,
            tool_turn_id=attempt.tool_turn_id,
            command_id=attempt.tool_command_id,
            args_hash=attempt.tool_args_hash,
        )
