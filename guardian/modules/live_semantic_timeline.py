"""Live Semantic Timeline
=======================

A rolling index of narrative events so the Companion can perform
"time travel" queries. Old events are automatically discarded to
keep the store ephemeral.

Usage example::

    from guardian.modules.live_semantic_timeline import SemanticTimeline, TimelineEvent
    from datetime import datetime, timezone

    timeline = SemanticTimeline(ttl_seconds=3600)
    timeline.add_event(TimelineEvent(timestamp=datetime.now(timezone.utc),
                                    narrative="Walked in the park", user_id="alice"))
    recent = timeline.query("park")
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import List

from pydantic import BaseModel, Field


class TimelineEvent(BaseModel):
    """Represents a short narrative summary."""

    timestamp: datetime = Field(..., description="Event timestamp")
    narrative: str = Field(..., description="Narrative text")
    user_id: str = Field(..., description="Owning user ID")


class SemanticTimeline:
    """In-memory semantic timeline with automatic TTL cleanup."""

    def __init__(self, ttl_seconds: int = 86_400) -> None:
        self.ttl_seconds = ttl_seconds
        self._events: List[TimelineEvent] = []
        self._lock = Lock()

    def add_event(self, event: TimelineEvent) -> None:
        """Add an event and discard old ones."""
        with self._lock:
            self._events.append(event)
            self._discard_old_locked()

    def query(self, keyword: str, limit: int = 10) -> List[TimelineEvent]:
        """Return recent events containing the keyword."""
        with self._lock:
            self._discard_old_locked()
            matched = [
                e for e in self._events if keyword.lower() in e.narrative.lower()
            ]
            return matched[-limit:]

    def _discard_old_locked(self) -> None:
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=self.ttl_seconds)
        self._events = [e for e in self._events if e.timestamp > cutoff]
