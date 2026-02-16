from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional


@dataclass
class CodexEntry:
    """Lightweight representation of a Codex entry stored on disk."""

    id: str
    title: str
    path: Path
    ext: str = "codex"
    created_at: datetime | None = None
    updated_at: datetime | None = None
    thread_id: str | None = None
    source_thread_id: str | None = None
    source_message_id: str | None = None
    message_ids: list[str] = field(default_factory=list)
    lineage_missing: bool = False
    author_id: str | None = None
    heat_score: float | None = None
    body: str | None = None
    frontmatter: dict = field(default_factory=dict)
