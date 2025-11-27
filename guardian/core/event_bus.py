"""Durable event bus backed by the chat database with in-memory fanout."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from guardian.core.chat_db import ChatDB

logger = logging.getLogger(__name__)

_store: ChatDB | None = None
_fallback_emitter: Callable[[str, dict[str, Any]], None] | None = None  # type: ignore[name-defined]


@dataclass
class _Subscriber:
    """Lightweight wrapper for an in-memory subscriber queue."""

    loop: asyncio.AbstractEventLoop
    queue: asyncio.Queue


_subscribers: list[_Subscriber] = []


def configure_event_store(store: ChatDB) -> None:
    """Register the durable store used for persisting events."""
    global _store
    _store = store
    try:
        store.ensure_event_outbox()
    except Exception:  # pragma: no cover - defensive logging
        logger.exception("[outbox] failed to ensure events_outbox table")
        raise
    logger.info("[outbox] event store configured (%s)", type(store).__name__)


def configure_fallback_emitter(
    emitter: Callable[[str, dict[str, Any]], None]
) -> None:
    """Register an in-memory fallback emitter used when no store is configured."""
    global _fallback_emitter
    _fallback_emitter = emitter


def emit_event(
    topic: str, payload: dict[str, Any], *, tenant_id: str = "default"
) -> None:
    """Persist an event or fall back to the in-memory hub."""
    if _store is not None:
        _store.append_event(topic, payload, tenant_id=tenant_id)
        _publish_in_memory(topic, payload, tenant_id)
        return
    if _fallback_emitter is not None:
        _fallback_emitter(topic, payload)
        _publish_in_memory(topic, payload, tenant_id)
    else:
        _publish_in_memory(topic, payload, tenant_id)
        if not _subscribers:
            logger.debug(
                "Dropping event %s; no event store, fallback, or in-memory subscribers",
                topic,
            )


def fetch_events_after(last_id: int, limit: int = 100) -> list[dict[str, Any]]:
    """Return events whose IDs are greater than ``last_id`` ordered ascending."""
    if _store is None:
        return []
    return _store.list_events_after(last_id, limit)


def delete_events_through(
    last_id: int, tenant_id: str | None = None
) -> None:
    """Delete events with IDs less than or equal to ``last_id`` from the store."""
    if _store is None:
        return
    _store.delete_events_through(last_id, tenant_id)


def is_persistent_enabled() -> bool:
    """Return True when a durable event store is configured."""
    return _store is not None


def reset() -> None:
    """Test helper to clear configured store and fallback."""
    global _store, _fallback_emitter
    _store = None
    _fallback_emitter = None
    _subscribers.clear()


def subscribe_in_memory() -> asyncio.Queue:
    """Register an in-memory subscriber and return its queue."""

    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()
    _subscribers.append(_Subscriber(loop=loop, queue=queue))
    return queue


def unsubscribe_in_memory(queue: asyncio.Queue) -> None:
    """Remove a queue from the in-memory subscriber list."""

    for idx, subscriber in enumerate(list(_subscribers)):
        if subscriber.queue is queue:
            _subscribers.pop(idx)
            break


def _publish_in_memory(
    topic: str, payload: dict[str, Any], tenant_id: str
) -> None:
    """Send an event payload to all in-memory subscribers."""

    if not _subscribers:
        return

    message = {"type": topic, "data": payload, "tenant_id": tenant_id}

    stale: list[_Subscriber] = []
    for subscriber in list(_subscribers):
        try:
            subscriber.loop.call_soon_threadsafe(
                subscriber.queue.put_nowait,
                message,
            )
        except RuntimeError:
            # Event loop is closed; drop this subscriber.
            stale.append(subscriber)

    if stale:
        for subscriber in stale:
            with contextlib.suppress(ValueError):
                _subscribers.remove(subscriber)
