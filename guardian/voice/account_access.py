"""Canonical thread authority shared by voice admission and execution."""

from fastapi import HTTPException

from guardian.core.dependencies import RequestUserScope
from guardian.core.thread_access import require_thread_read_access


def require_voice_thread_access(db, thread_id: int, scope: RequestUserScope):
    if not db or not callable(getattr(db, "get_chat_thread", None)):
        raise HTTPException(status_code=503, detail="chat_db_unavailable")
    thread = db.get_chat_thread(thread_id)
    if thread is None:
        raise HTTPException(status_code=404, detail="thread_not_found")
    if (
        scope.multi_user_enabled
        and not str(scope.account_id or scope.user_id or "").strip()
    ):
        raise HTTPException(status_code=401, detail="Missing authenticated user")
    return require_thread_read_access(thread_id, scope, thread=thread)
