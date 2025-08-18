import asyncio
from typing import Any, AsyncIterator, Dict, List


class EventBus:
    def __init__(self) -> None:
        self._subscribers: List[asyncio.Queue] = []

    async def publish(self, message: Dict[str, Any]) -> None:
        for q in list(self._subscribers):
            try:
                await q.put(message)
            except Exception:
                continue

    async def subscribe(self) -> AsyncIterator[Dict[str, Any]]:
        q: asyncio.Queue = asyncio.Queue()
        self._subscribers.append(q)
        try:
            while True:
                msg = await q.get()
                yield msg
        finally:
            try:
                self._subscribers.remove(q)
            except ValueError:
                pass


bus = EventBus()

