from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response

from guardian.codex.lineage import ensure_lineage_exists, parse_lineage
from guardian.codex.service import (
    list_codex_entries,
    load_codex_entry,
    read_codex_body,
    read_raw_entry,
)

try:
    from guardian.core.dependencies import (
        chatlog_db,
        get_single_user_id,
        require_api_key,
    )
except Exception:  # pragma: no cover - defensive import fallback
    chatlog_db = None

    def get_single_user_id() -> str:  # type: ignore[unused-ignore]
        return "local"

    def require_api_key(api_key: str = "") -> str:  # type: ignore[unused-argument]
        return api_key


router = APIRouter()


def _iso(dt) -> str | None:
    return dt.isoformat() if dt else None


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-")
    return slug.lower() or "codex-entry"


def _summary_payload(entry) -> dict:
    return {
        "id": entry.id,
        "title": entry.title,
        "ext": entry.ext,
        "created_at": _iso(entry.created_at),
        "updated_at": _iso(entry.updated_at),
        "thread_id": entry.thread_id,
        "source_thread_id": entry.source_thread_id,
        "source_message_id": entry.source_message_id,
        "lineage_missing": entry.lineage_missing,
        "author_id": entry.author_id,
        "heat_score": entry.heat_score,
    }


def _coerce_thread_id(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _users_match(resource_user_id: str | None, current_user_id: str) -> bool:
    resource = (resource_user_id or "").strip()
    current = (current_user_id or "").strip()
    if not resource or not current:
        return False
    if resource == current:
        return True
    pair = {resource.lower(), current.lower()}
    # Backward-compatible single-user aliases found in existing local data.
    return pair.issubset({"default", "local"})


def _entry_owner_user_id(entry) -> str | None:
    thread_id = _coerce_thread_id(entry.source_thread_id or entry.thread_id)
    if thread_id is not None and chatlog_db is not None:
        try:
            thread = chatlog_db.get_chat_thread(thread_id)
        except Exception:
            thread = None
        if isinstance(thread, dict):
            owner = thread.get("user_id")
            if isinstance(owner, str) and owner.strip():
                return owner.strip()
    author = entry.author_id or entry.frontmatter.get("author")
    if isinstance(author, str) and author.strip():
        return author.strip()
    return None


def _ensure_entry_access(
    entry,
    *,
    lineage_verified: bool = False,
) -> None:
    owner = _entry_owner_user_id(entry)
    current_user = get_single_user_id()
    if owner is None and lineage_verified:
        # In single-user deployments, verified lineage can serve as
        # ownership proof when older codex files lack explicit author metadata.
        return
    if owner is None:
        raise HTTPException(
            status_code=403,
            detail="Codex entry ownership could not be verified",
        )
    if not _users_match(owner, current_user):
        raise HTTPException(status_code=403, detail="Forbidden")


@router.get("/api/codex/entries", tags=["codex"])
async def codex_entries(
    api_key: str = Depends(require_api_key),
) -> list[dict]:
    _ = api_key
    entries = list_codex_entries()
    visible: list[dict[str, Any]] = []
    for entry in entries:
        try:
            _ensure_entry_access(entry)
        except HTTPException:
            continue
        visible.append(_summary_payload(entry))
    return visible


@router.get("/api/codex/entries/{entry_id}", tags=["codex"])
async def codex_entry(
    entry_id: str,
    api_key: str = Depends(require_api_key),
) -> dict:
    _ = api_key
    try:
        entry = load_codex_entry(entry_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Codex entry not found")
    _ensure_entry_access(entry)

    return {
        **_summary_payload(entry),
        "message_ids": entry.message_ids,
        "body": read_codex_body(entry),
    }


@router.get("/api/codex/{entry_id}/source", tags=["codex"])
async def codex_entry_source(
    entry_id: str,
    api_key: str = Depends(require_api_key),
) -> dict:
    _ = api_key
    try:
        entry = load_codex_entry(entry_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Codex entry not found")

    try:
        lineage = parse_lineage(entry.frontmatter)
        ensure_lineage_exists(lineage)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    _ensure_entry_access(entry, lineage_verified=True)

    payload: dict[str, object] = {
        "codex_entry_id": entry.id,
        "source_thread_id": lineage.source_thread_id,
        "source_message_id": lineage.source_message_id,
    }

    message_index = None
    if entry.message_ids:
        try:
            message_index = entry.message_ids.index(
                str(lineage.source_message_id)
            )
        except ValueError:
            message_index = None
    if message_index is not None:
        payload["message_index"] = message_index

    return payload


@router.get("/api/codex/entries/{entry_id}/export", tags=["codex"])
async def export_codex_entry(
    entry_id: str,
    api_key: str = Depends(require_api_key),
):
    _ = api_key
    try:
        entry, raw = read_raw_entry(entry_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Codex entry not found")
    _ensure_entry_access(entry)

    filename = f"{_slugify(entry.title)}.md"
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Content-Type": "text/markdown; charset=utf-8",
    }
    return Response(content=raw, media_type="text/markdown", headers=headers)
