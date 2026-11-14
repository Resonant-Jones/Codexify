"""Accepted ordinary-chat account custody, not connector permission or transport.

The resolver is a prerequisite seam only. No tool is enabled and no provider
credential is accessed here. A consumer must recheck live connector scope and
revocation inside the existing Command Bus execution boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from guardian.core.project_ownership import classify_project_ownership
from guardian.db.models import ChatCompletionAttempt, ChatThread, Project, User
from guardian.tasks.chat_deadline import (
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


def resolve_accepted_chat_account(
    db: Any,
    task: Any,
    *,
    command_id: str,
    args_hash: str,
) -> AcceptedChatAccountBinding:
    """Re-read original ownership and live attempt state before future dispatch.

    No account is selected from task.user_id: that field is only compared with
    the persisted accepting-account snapshot. No lock spans provider I/O.
    An earlier return value cannot authorize retries or a later invocation.
    """
    from guardian.core.preview_access import is_private_preview, role_for_preview_email
    from guardian.queue.redis_queue import is_cancelled

    denied = "accepted_chat_account_unavailable"
    try:
        if (
            str(task.origin or "").split("|", 1)[0] != "api:chat.complete"
            or getattr(task, "hosted_room_invocation", None) is not None
            or not command_id
            or len(args_hash) != 64
            or any(c not in "0123456789abcdef" for c in args_hash)
        ):
            raise ChatAccountCustodyUnavailable(denied)
        with db._sa_session() as session:
            attempt = (
                session.query(ChatCompletionAttempt)
                .filter_by(request_id=task.request_id)
                .with_for_update()
                .one_or_none()
            )
            if attempt is None or (
                attempt.backend_task_id != task.task_id
                or attempt.thread_id != task.thread_id
                or attempt.turn_id != task.turn_id
                or not attempt.accepted_account_id
                or attempt.accepted_account_id != task.user_id
                or attempt.completed_message_id is not None
                or attempt.terminal_event_type is not None
            ):
                raise ChatAccountCustodyUnavailable(denied)
            account_id = attempt.accepted_account_id
            thread = (
                session.query(ChatThread).filter_by(id=attempt.thread_id).one_or_none()
            )
            user = session.query(User).filter_by(id=account_id).one_or_none()
            if thread is None or user is None or thread.user_id != account_id:
                raise ChatAccountCustodyUnavailable(denied)
            if thread.project_id is not None:
                project = (
                    session.query(Project).filter_by(id=thread.project_id).one_or_none()
                )
                ownership = classify_project_ownership(project)
                if (
                    ownership.canonical_owner_id != account_id
                    or ownership.has_authority_conflict
                ):
                    raise ChatAccountCustodyUnavailable(denied)
            if (
                is_private_preview()
                and role_for_preview_email(user.email or user.id) is None
            ):
                raise ChatAccountCustodyUnavailable(denied)
            deadline = parse_accepted_chat_task_deadline(
                attempt.deadline_snapshot or {}
            )
            if (
                deadline is None
                or deadline != accepted_chat_deadline_for_task(task)
                or datetime.now(timezone.utc) >= deadline.work_deadline_at
            ):
                raise ChatAccountCustodyUnavailable(denied)
            if attempt.accepted_at is None:
                raise ChatAccountAcceptancePending("accepted_chat_account_pending")
            if (
                not attempt.tool_turn_id
                or attempt.tool_checkpoint_at is None
                or attempt.tool_command_id != command_id
                or attempt.tool_args_hash != args_hash
            ):
                raise ChatAccountCustodyUnavailable(denied)
            if is_cancelled(attempt.backend_task_id):
                raise ChatAccountCustodyUnavailable(denied)
            return AcceptedChatAccountBinding(
                account_id=account_id,
                request_id=attempt.request_id,
                backend_task_id=attempt.backend_task_id,
                thread_id=attempt.thread_id,
                turn_id=attempt.turn_id,
                tool_turn_id=attempt.tool_turn_id,
                command_id=attempt.tool_command_id,
                args_hash=attempt.tool_args_hash,
            )
    except ChatAccountCustodyUnavailable:
        raise
    except Exception:
        raise ChatAccountCustodyUnavailable(denied) from None
