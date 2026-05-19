from __future__ import annotations

import hashlib
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, List, Optional, Tuple

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


def _coerce_bool_fm(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    normalized = str(value).strip().lower()
    return normalized in {"1", "true", "yes", "y"}


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
    message_ids = [str(m) for m in message_ids if m]

    source_thread_id = fm.get("source_thread_id") or fm.get("thread_id")
    source_message_id = (
        fm.get("source_message_id")
        or fm.get("message_id")
        or (message_ids[0] if message_ids else None)
    )
    trigger_message_id = fm.get("trigger_message_id")
    lineage_missing = source_thread_id in (None, "") or source_message_id in (
        None,
        "",
    )

    retrieval_enabled_raw = _coerce_bool_fm(fm.get("retrieval_enabled"))

    entry = CodexEntry(
        id=fm.get("id") or _entry_id(path),
        title=fm.get("title") or path.stem,
        path=path,
        ext="codex",
        created_at=created_at,
        updated_at=updated_at,
        thread_id=str(source_thread_id)
        if source_thread_id
        else fm.get("thread_id"),
        source_thread_id=(
            str(source_thread_id)
            if source_thread_id not in (None, "")
            else None
        ),
        source_message_id=(
            str(source_message_id)
            if source_message_id not in (None, "")
            else None
        ),
        trigger_message_id=(
            str(trigger_message_id)
            if trigger_message_id not in (None, "")
            else None
        ),
        message_ids=message_ids,
        lineage_missing=lineage_missing,
        author_id=fm.get("author"),
        heat_score=(
            None
            if fm.get("heat_score") is None
            else float(fm.get("heat_score"))
        ),
        frontmatter=fm,
        body=body if include_body else None,
        created_from=fm.get("created_from"),
        retrieval_enabled=(
            retrieval_enabled_raw if retrieval_enabled_raw is not None else False
        ),
        project_id=fm.get("project_id"),
        persona_id=fm.get("persona_id"),
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


def _build_frontmatter_block(fm: dict) -> str:
    """Serialize a frontmatter dict to a YAML block with --- delimiters."""
    if not fm:
        return ""
    dumped = yaml.dump(fm, default_flow_style=False, allow_unicode=True, sort_keys=False)
    return f"---\n{dumped}---\n"


def save_codex_entry(
    *,
    title: str,
    body: str,
    thread_id: str | None = None,
    source_thread_id: str | None = None,
    source_message_id: str | None = None,
    trigger_message_id: str | None = None,
    message_ids: list[str] | None = None,
    author_id: str | None = None,
    created_from: str | None = None,
    retrieval_enabled: bool = False,
    project_id: str | None = None,
    persona_id: str | None = None,
    heat_score: float | None = None,
    entry_id: str | None = None,
) -> CodexEntry:
    """Persist a new Codex Entry as a .cdx file on disk.

    Returns the parsed CodexEntry after saving.
    """
    root = _ensure_root()
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()

    # Build frontmatter
    fm: dict[str, Any] = {}
    if title:
        fm["title"] = title
    fm["created_at"] = now_iso
    fm["updated_at"] = now_iso
    if thread_id:
        fm["thread_id"] = str(thread_id)
    if source_thread_id:
        fm["source_thread_id"] = str(source_thread_id)
    if source_message_id:
        fm["source_message_id"] = str(source_message_id)
    if trigger_message_id:
        fm["trigger_message_id"] = str(trigger_message_id)
    if message_ids:
        fm["message_ids"] = [str(m) for m in message_ids if m]
    if author_id:
        fm["author"] = str(author_id)
    if created_from:
        fm["created_from"] = str(created_from)
    fm["retrieval_enabled"] = bool(retrieval_enabled)
    if project_id:
        fm["project_id"] = str(project_id)
    if persona_id:
        fm["persona_id"] = str(persona_id)
    if heat_score is not None:
        fm["heat_score"] = float(heat_score)

    # Derive a stable filename
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", title).strip("-").lower() or "codex-entry"
    timestamp = now.strftime("%Y%m%d-%H%M%S")
    filename = f"{slug}-{timestamp}.cdx"
    filepath = root / filename

    # If an explicit entry_id is provided, inject it
    if entry_id:
        fm["id"] = str(entry_id)

    # Assemble and write
    frontmatter_block = _build_frontmatter_block(fm)
    content = f"{frontmatter_block}\n{body}\n"
    filepath.write_text(content, encoding="utf-8")

    return _parse_entry(filepath, include_body=True)
