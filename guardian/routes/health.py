"""
Health Routes
~~~~~~~~~~~~~

Health check endpoints for monitoring subsystem status.
Mounted without a prefix to preserve public paths like /health/chat.
"""

import logging
from fastapi import APIRouter

logger = logging.getLogger(__name__)

# Create unprefixed router to preserve /health/chat path
router = APIRouter(tags=["Health"])


@router.get("/health")
def health():
    """Base health check endpoint for system-level monitoring."""
    return {"status": "ok"}


@router.get("/health/chat")
def health_chat():
    """Get health status of chat subsystem."""
    # Lazy import to avoid circular dependency - guardian_api imports this module,
    # so we can't import from it at module level. By the time this handler runs,
    # guardian_api is fully loaded and these symbols are available.
    from guardian.guardian_api import chatlog_db, DB_BACKEND

    try:
        threads = chatlog_db.count_chat_threads()
        messages = chatlog_db.count_all_messages()
    except Exception as _e:
        logger.warning("[health/chat] check failed: %s", _e)
        threads = 0
        messages = 0
    return {"ok": True, "threads": threads, "messages": messages, "backend": DB_BACKEND}
