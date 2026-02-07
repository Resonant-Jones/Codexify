"""WebSocket connection registry with topic subscriptions."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any, Protocol


class WSConnection(Protocol):
    """Protocol for websocket-like connections used by the manager."""

    async def send_json(self, payload: dict[str, Any]) -> None:
        ...


class WSConnectionManager:
    """Track connections and route topic broadcasts to subscribers only."""

    def __init__(self) -> None:
        self._connections: set[WSConnection] = set()
        self._topics: dict[str, set[WSConnection]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def register(self, connection: WSConnection) -> None:
        async with self._lock:
            self._connections.add(connection)

    async def unregister(self, connection: WSConnection) -> None:
        async with self._lock:
            self._connections.discard(connection)
            stale_topics = []
            for topic, subscribers in self._topics.items():
                subscribers.discard(connection)
                if not subscribers:
                    stale_topics.append(topic)
            for topic in stale_topics:
                self._topics.pop(topic, None)

    async def subscribe(self, connection: WSConnection, topic: str) -> None:
        if not topic:
            raise ValueError("topic must be non-empty")
        async with self._lock:
            self._connections.add(connection)
            self._topics[topic].add(connection)

    async def unsubscribe(self, connection: WSConnection, topic: str) -> None:
        async with self._lock:
            subscribers = self._topics.get(topic)
            if not subscribers:
                return
            subscribers.discard(connection)
            if not subscribers:
                self._topics.pop(topic, None)

    async def broadcast(self, topic: str, payload: dict[str, Any]) -> None:
        async with self._lock:
            targets = list(self._topics.get(topic, set()))
        stale: list[WSConnection] = []
        for connection in targets:
            try:
                await connection.send_json(payload)
            except Exception:
                stale.append(connection)
        for connection in stale:
            await self.unregister(connection)

    def subscriber_count(self, topic: str) -> int:
        return len(self._topics.get(topic, set()))

    def connection_count(self) -> int:
        return len(self._connections)
