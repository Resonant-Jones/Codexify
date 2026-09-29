"""Durable authorization for task-event streams."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from guardian.core.db import get_chat_completion_attempt_by_task_id, load_guardian_db_from_env
from guardian.core.dependencies import RequestUserScope
from guardian.core.hosted_room_session import HostedRoomGuestPrincipal
from guardian.core.thread_access import ThreadReadAccess, require_thread_read_access


def authorize_task_event_read(
    backend_task_id: str,
    principal: RequestUserScope | HostedRoomGuestPrincipal,
    *,
    chatlog_db: Any,
) -> ThreadReadAccess:
    """Resolve a backend task ID to its canonical thread and authorize it.

    Postgres completion-attempt state is the only task-to-thread authority.
    Redis is intentionally absent from this function and is reached only by
    the caller after this decision succeeds.
    """
    if chatlog_db is None:
        raise HTTPException(status_code=503, detail="Task authorization unavailable")

    attempt = get_chat_completion_attempt_by_task_id(chatlog_db, backend_task_id)
    if attempt is None:
        raise HTTPException(status_code=404, detail="Task not found")

    thread_id = attempt.get("thread_id")
    if not isinstance(thread_id, int):
        raise HTTPException(status_code=404, detail="Task not found")

    if isinstance(principal, HostedRoomGuestPrincipal):
        guardian_db = load_guardian_db_from_env()
        if guardian_db is None:
            raise HTTPException(status_code=503, detail="Thread authorization unavailable")
        with guardian_db.get_session() as session:
            return require_thread_read_access(
                thread_id,
                principal,
                session=session,
            )

    return require_thread_read_access(
        thread_id,
        principal,
        thread_lookup=chatlog_db.get_chat_thread,
    )
