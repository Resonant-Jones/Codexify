from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest

from guardian.core import event_bus
from guardian.realtime.event_relay import run_event_relay
from guardian.ws.manager import WSConnectionManager


@pytest.mark.asyncio
async def test_subscribe_unsubscribe_by_topic() -> None:
    manager = WSConnectionManager()
    ws = AsyncMock()

    await manager.register(ws)
    await manager.subscribe(ws, "topic.alpha")

    assert manager.subscriber_count("topic.alpha") == 1

    await manager.unsubscribe(ws, "topic.alpha")

    assert manager.subscriber_count("topic.alpha") == 0


@pytest.mark.asyncio
async def test_broadcast_routes_only_to_subscribed_connections() -> None:
    manager = WSConnectionManager()
    ws_alpha = AsyncMock()
    ws_beta = AsyncMock()

    await manager.subscribe(ws_alpha, "topic.alpha")
    await manager.subscribe(ws_beta, "topic.beta")

    payload = {"type": "topic.alpha", "data": {"ok": True}}
    await manager.broadcast("topic.alpha", payload)

    ws_alpha.send_json.assert_called_once_with(payload)
    ws_beta.send_json.assert_not_called()


@pytest.mark.asyncio
async def test_unregister_removes_connection_from_all_topics() -> None:
    manager = WSConnectionManager()
    ws = AsyncMock()

    await manager.subscribe(ws, "topic.alpha")
    await manager.subscribe(ws, "topic.beta")
    assert manager.connection_count() == 1

    await manager.unregister(ws)

    assert manager.connection_count() == 0
    assert manager.subscriber_count("topic.alpha") == 0
    assert manager.subscriber_count("topic.beta") == 0


@pytest.mark.asyncio
async def test_event_relay_forwards_in_memory_events_to_subscribers() -> None:
    manager = WSConnectionManager()
    ws = AsyncMock()
    await manager.subscribe(ws, "relay.topic")

    stop_event = asyncio.Event()
    relay_task = asyncio.create_task(
        run_event_relay(manager, stop_event=stop_event)
    )
    try:
        # Give relay loop a tick to register its in-memory subscription.
        await asyncio.sleep(0.01)
        event_bus.emit_event("relay.topic", {"value": 1})
        await asyncio.sleep(0.05)
        ws.send_json.assert_called_once()
        sent_payload = ws.send_json.call_args[0][0]
        assert sent_payload["type"] == "relay.topic"
    finally:
        stop_event.set()
        relay_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await relay_task
