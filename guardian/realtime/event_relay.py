"""In-memory event relay that fans out event bus messages to WS subscribers."""

from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass
from typing import Any

from guardian.core import event_bus
from guardian.ws.manager import WSConnectionManager


@dataclass
class RelayHandle:
    """Relay lifecycle handle."""

    task: asyncio.Task[None]
    stop_event: asyncio.Event


async def run_event_relay(
    manager: WSConnectionManager,
    *,
    stop_event: asyncio.Event,
    poll_timeout: float = 0.25,
) -> None:
    """Forward event bus messages to topic subscribers."""

    queue = event_bus.subscribe_in_memory()
    try:
        while not stop_event.is_set():
            try:
                message = await asyncio.wait_for(
                    queue.get(), timeout=poll_timeout
                )
            except asyncio.TimeoutError:
                continue
            if not isinstance(message, dict):
                continue
            topic = str(message.get("type") or "").strip()
            if not topic:
                continue
            await manager.broadcast(topic, message)
    finally:
        event_bus.unsubscribe_in_memory(queue)


def start_event_relay(manager: WSConnectionManager) -> RelayHandle:
    """Start relay loop on the current event loop."""

    stop_event = asyncio.Event()
    task = asyncio.create_task(run_event_relay(manager, stop_event=stop_event))
    return RelayHandle(task=task, stop_event=stop_event)


async def stop_event_relay(handle: RelayHandle) -> None:
    """Stop relay task and await completion."""

    handle.stop_event.set()
    handle.task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await handle.task
