"""Immutable Narrative Log
========================

Allows certain narrative summaries to be locked as immutable so
they cannot be modified later.

Usage example::

    from guardian.modules.immutable_log import ImmutableLog

    log = ImmutableLog()
    entry_id = log.add_entry("Initial text", immutable=True)
    # log.update_entry(entry_id, "new")  # would raise ValueError
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict
from uuid import uuid4

from pydantic import BaseModel, Field


class NarrativeEntry(BaseModel):
    """Single narrative entry."""

    id: str = Field(..., description="Entry ID")
    timestamp: datetime = Field(..., description="Creation time")
    narrative: str = Field(..., description="Narrative text")
    immutable: bool = Field(False, description="Locked from modification")


class ImmutableLog:
    """In-memory immutable log."""

    def __init__(self) -> None:
        self._entries: Dict[str, NarrativeEntry] = {}

    def add_entry(self, narrative: str, immutable: bool = False) -> str:
        entry = NarrativeEntry(
            id=str(uuid4()),
            timestamp=datetime.now(timezone.utc),
            narrative=narrative,
            immutable=immutable,
        )
        self._entries[entry.id] = entry
        return entry.id

    def update_entry(self, entry_id: str, narrative: str) -> None:
        entry = self._entries.get(entry_id)
        if not entry:
            raise KeyError("entry not found")
        if entry.immutable:
            raise ValueError("entry is immutable")
        entry.narrative = narrative

    def get_entry(self, entry_id: str) -> NarrativeEntry:
        entry = self._entries.get(entry_id)
        if not entry:
            raise KeyError("entry not found")
        return entry
