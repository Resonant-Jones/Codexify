"""Redis-backed per-thread turn lock helpers."""

from __future__ import annotations

import logging
import os
from typing import Optional

from guardian.queue.redis_queue import _with_reconnect

logger = logging.getLogger(__name__)

_DEFAULT_TTL_SECONDS = 180


def _lock_ttl_seconds() -> int:
    raw = os.getenv("CODEXIFY_TURN_LOCK_TTL_SECONDS", str(_DEFAULT_TTL_SECONDS))
    try:
        value = int(raw)
    except Exception:
        value = _DEFAULT_TTL_SECONDS
    return max(15, value)


def turn_lock_key(thread_id: int) -> str:
    return f"turn_lock:{int(thread_id)}"


def acquire_turn_lock(
    thread_id: int,
    owner: str,
    *,
    ttl_seconds: int | None = None,
) -> bool:
    """Acquire a per-thread lock using SET NX EX semantics."""
    key = turn_lock_key(thread_id)
    ttl = max(1, int(ttl_seconds or _lock_ttl_seconds()))

    def _acquire(client) -> bool:
        return bool(client.set(key, owner, nx=True, ex=ttl))

    acquired = bool(_with_reconnect(_acquire))
    if not acquired:
        logger.info("[turn-lock] in-flight thread_id=%s key=%s", thread_id, key)
    return acquired


def release_turn_lock(thread_id: int, owner: str) -> bool:
    """Release lock only when current owner matches."""
    key = turn_lock_key(thread_id)

    def _release(client) -> bool:
        released = client.eval(
            """
            if redis.call('GET', KEYS[1]) == ARGV[1] then
                return redis.call('DEL', KEYS[1])
            end
            return 0
            """,
            1,
            key,
            owner,
        )
        return bool(released)

    return bool(_with_reconnect(_release))


def get_turn_lock_owner(thread_id: int) -> str | None:
    """Return lock owner for diagnostics."""
    key = turn_lock_key(thread_id)

    def _get_owner(client) -> str | None:
        value = client.get(key)
        return str(value) if value is not None else None

    return _with_reconnect(_get_owner)
