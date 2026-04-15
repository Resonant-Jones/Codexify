from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import yaml
from fastapi import APIRouter, Body, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator

from guardian.codex import service as codex_service
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
    thread_id = entry.source_thread_id or entry.thread_id
    return {
        "id": entry.id,
        "title": entry.title,
        "ext": entry.ext,
        "created_at": _iso(entry.created_at),
        "updated_at": _iso(entry.updated_at),
        "thread_id": entry.thread_id,
        "source_thread_id": entry.source_thread_id,
        "source_message_id": entry.source_message_id,
        "lineage_missing": thread_id in (None, ""),
        "author_id": entry.author_id,
        "heat_score": entry.heat_score,
    }


def _entry_detail_payload(entry) -> dict[str, Any]:
    return {
        **_summary_payload(entry),
        "message_ids": entry.message_ids,
        "body": read_codex_body(entry),
        "frontmatter": entry.frontmatter,
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


class CodexEntryCreateRequest(BaseModel):
    entry_type: str = Field(alias="type")
    content: str
    thread_id: int = Field(alias="threadId", gt=0)
    source_message_id: int | None = Field(
        default=None, alias="sourceMessageId", gt=0
    )
    project_id: int | None = Field(default=None, alias="projectId", gt=0)
    metadata: dict[str, Any] | None = None

    model_config = ConfigDict(
        populate_by_name=True,
        extra="forbid",
    )

    @field_validator("entry_type")
    @classmethod
    def _validate_entry_type(cls, value: str) -> str:
        value = str(value).strip()
        if value != "note":
            raise ValueError("type must be note")
        return value

    @field_validator("content")
    @classmethod
    def _validate_content(cls, value: str) -> str:
        text = str(value).strip()
        if not text:
            raise ValueError("content is required")
        return text

    @field_validator("metadata", mode="before")
    @classmethod
    def _validate_metadata(cls, value: Any) -> dict[str, Any] | None:
        if value is None:
            return None
        if not isinstance(value, dict):
            raise ValueError("metadata must be an object")
        return value


def _build_entry_id(title: str) -> str:
    slug = _slugify(title)
    return f"{slug}-{uuid4().hex[:8]}"


def _entry_path(entry_id: str) -> Path:
    root = codex_service.CODEX_ROOT
    root.mkdir(parents=True, exist_ok=True)
    return root / f"{entry_id}.cdx"


def _write_codex_entry(
    *,
    entry_id: str,
    title: str,
    author: str,
    content: str,
    thread_id: int,
    source_message_id: int | None,
    project_id: int | None,
    metadata: dict[str, Any] | None,
) -> Path:
    now = datetime.now(timezone.utc).isoformat()
    frontmatter: dict[str, Any] = {
        "id": entry_id,
        "title": title,
        "type": "note",
        "created_at": now,
        "updated_at": now,
        "author": author,
        "thread_id": thread_id,
        "source_thread_id": thread_id,
        "source_message_id": source_message_id,
        "message_id": source_message_id,
        "message_ids": [source_message_id]
        if source_message_id is not None
        else [],
    }
    if project_id is not None:
        frontmatter["project_id"] = project_id
    if metadata is not None:
        frontmatter["metadata"] = metadata

    path = _entry_path(entry_id)
    raw = (
        "---\n"
        + yaml.safe_dump(frontmatter, sort_keys=False).strip()
        + "\n---\n"
        + content
    )
    path.write_text(raw, encoding="utf-8")
    return path


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

    return _entry_detail_payload(entry)


@router.post("/api/codex/entries", tags=["codex"], status_code=201)
async def create_codex_entry(
    body: CodexEntryCreateRequest = Body(...),
    api_key: str = Depends(require_api_key),
) -> dict:
    _ = api_key

    lineage = parse_lineage(
        {
            "source_thread_id": body.thread_id,
            "source_message_id": body.source_message_id,
        }
    )
    try:
        ensure_lineage_exists(lineage)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))

    current_user = get_single_user_id()
    title = "Retrieval posture diff note"
    entry_id = _build_entry_id(title)
    _write_codex_entry(
        entry_id=entry_id,
        title=title,
        author=current_user,
        content=body.content,
        thread_id=body.thread_id,
        source_message_id=body.source_message_id,
        project_id=body.project_id,
        metadata=body.metadata,
    )

    try:
        entry = load_codex_entry(entry_id)
    except FileNotFoundError as e:  # pragma: no cover - defensive
        raise HTTPException(status_code=500, detail=str(e))
    return {"ok": True, "entry": _entry_detail_payload(entry)}


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
    if lineage.source_message_id is not None and entry.message_ids:
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
