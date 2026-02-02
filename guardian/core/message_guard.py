"""Chat message content guards shared across database implementations."""

from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

EMPTY_ASSISTANT_FALLBACK = (
    "The assistant returned an empty response. "
    "This usually indicates an upstream model/provider error. "
    "Please retry."
)


def _get_guardian_env() -> str:
    return os.getenv("GUARDIAN_ENV", "development").strip().lower()


def _is_blank_content(content: str | None) -> bool:
    if content is None:
        return True
    if not isinstance(content, str):
        return False
    return not content.strip()


def guard_assistant_message_content(
    role: str,
    content: str | None,
    *,
    thread_id: int | None = None,
    origin: str | None = None,
) -> str:
    """Ensure assistant messages are never persisted with blank content."""
    role_normalized = (role or "").strip().lower()
    if role_normalized != "assistant":
        return content if content is not None else ""

    if not _is_blank_content(content):
        return content if content is not None else ""

    env_mode = _get_guardian_env()
    content_len = len(content) if isinstance(content, str) else 0
    logger_args = (thread_id, role, content_len, origin, env_mode)

    if env_mode in ("production", "prod"):
        logger.warning(
            "[chat-db] blank assistant content; using fallback thread_id=%s role=%s len=%s origin=%s env=%s",
            *logger_args,
        )
        return EMPTY_ASSISTANT_FALLBACK

    logger.error(
        "[chat-db] refusing to persist blank assistant content thread_id=%s role=%s len=%s origin=%s env=%s",
        *logger_args,
    )
    raise ValueError("Refusing to persist empty assistant message content.")
