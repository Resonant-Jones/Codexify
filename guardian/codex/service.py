from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

import yaml

from guardian.codex.models import CodexEntry
from guardian.core.config import get_settings

settings = get_settings()

# Root directory for Codex entries (defaults to <DATA_STORAGE_PATH>/codex)
CODEX_ROOT = (
    Path(os.getenv("CODEX_ROOT") or settings.DATA_STORAGE_PATH)
    .expanduser()
    .resolve()
    / "codex"
)


def _ensure_root() -> Path:
    CODEX_ROOT.mkdir(parents=True, exist_ok=True)
    return CODEX_ROOT


def _parse_datetime(
    value: str | None, fallback: datetime | None = None
) -> datetime | None:
    if not value:
        return fallback
    try:
        cleaned = (
            value.replace("Z", "+00:00") if isinstance(value, str) else value
        )
        dt = datetime.fromisoformat(cleaned)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return fallback


def _split_frontmatter(raw: str) -> tuple[dict, str]:
    """Split a markdown document into (frontmatter_dict, body)."""
    if not raw.startswith("---"):
        return {}, raw

    lines = raw.splitlines()
    if len(lines) < 3:
        return {}, raw

    end_index = None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            end_index = idx
            break

    if end_index is None:
        return {}, raw

    frontmatter_raw = "\n".join(lines[1:end_index])
    body = "\n".join(lines[end_index + 1 :])
    data = yaml.safe_load(frontmatter_raw) if frontmatter_raw.strip() else {}
    return (data or {}), body


def _entry_id(path: Path) -> str:
    """Derive a stable ID from the relative path and a short hash."""
    try:
        rel = path.relative_to(CODEX_ROOT)
        base = rel.with_suffix("").as_posix().replace("/", "_")
    except ValueError:
        base = path.stem
    digest = hashlib.sha1(str(path).encode("utf-8")).hexdigest()[:8]
    return f"{base}_{digest}"


def _parse_entry(path: Path, include_body: bool = False) -> CodexEntry:
    raw_text = path.read_text(encoding="utf-8")
    fm, body = _split_frontmatter(raw_text)

    created_at = _parse_datetime(
        fm.get("created_at"),
        fallback=datetime.fromtimestamp(path.stat().st_ctime, tz=timezone.utc),
    )
    updated_at = _parse_datetime(
        fm.get("updated_at"),
        fallback=datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc),
    )

    message_ids = fm.get("message_ids") or []
    if not isinstance(message_ids, list):
        message_ids = [message_ids]

    entry = CodexEntry(
        id=fm.get("id") or _entry_id(path),
        title=fm.get("title") or path.stem,
        path=path,
        ext="codex",
        created_at=created_at,
        updated_at=updated_at,
        thread_id=fm.get("thread_id"),
        message_ids=[str(m) for m in message_ids if m],
        author_id=fm.get("author"),
        heat_score=None
        if fm.get("heat_score") is None
        else float(fm.get("heat_score")),
        frontmatter=fm,
        body=body if include_body else None,
    )
    return entry


def _iter_entry_paths() -> Iterable[Path]:
    root = _ensure_root()
    return root.glob("**/*.cdx")


def list_codex_entries() -> list[CodexEntry]:
    """List all Codex entries without loading their bodies."""
    entries = [
        _parse_entry(path, include_body=False) for path in _iter_entry_paths()
    ]
    return sorted(
        entries,
        key=lambda e: e.created_at or datetime.now(timezone.utc),
        reverse=True,
    )


def find_entry_path(entry_id: str) -> Path | None:
    for path in _iter_entry_paths():
        if _entry_id(path) == entry_id or path.stem == entry_id:
            return path
    return None


def load_codex_entry(entry_id: str) -> CodexEntry:
    """Load a single Codex entry including its body."""
    path = find_entry_path(entry_id)
    if not path:
        raise FileNotFoundError(f"Codex entry {entry_id} not found")
    return _parse_entry(path, include_body=True)


def read_codex_body(entry: CodexEntry) -> str:
    """Return the markdown body for an entry, loading from disk if necessary."""
    if entry.body is not None:
        return entry.body
    reloaded = load_codex_entry(entry.id)
    return reloaded.body or ""


def read_raw_entry(entry_id: str) -> tuple[CodexEntry, str]:
    """Return (entry, raw file contents) for export."""
    path = find_entry_path(entry_id)
    if not path:
        raise FileNotFoundError(f"Codex entry {entry_id} not found")
    content = path.read_text(encoding="utf-8")
    entry = _parse_entry(path, include_body=True)
    return entry, content
