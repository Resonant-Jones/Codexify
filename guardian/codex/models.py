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
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    thread_id: Optional[str] = None
    message_ids: List[str] = field(default_factory=list)
    author_id: Optional[str] = None
    heat_score: Optional[float] = None
    body: Optional[str] = None
    frontmatter: dict = field(default_factory=dict)

