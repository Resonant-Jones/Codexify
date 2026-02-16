from __future__ import annotations

import re

from fastapi import APIRouter, HTTPException, Response

from guardian.codex.lineage import ensure_lineage_exists, parse_lineage
from guardian.codex.service import (
    list_codex_entries,
    load_codex_entry,
    read_codex_body,
    read_raw_entry,
)

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


@router.get("/api/codex/entries", tags=["codex"])
async def codex_entries() -> list[dict]:
    entries = list_codex_entries()
    return [_summary_payload(e) for e in entries]


@router.get("/api/codex/entries/{entry_id}", tags=["codex"])
async def codex_entry(entry_id: str) -> dict:
    try:
        entry = load_codex_entry(entry_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Codex entry not found")

    return {
        **_summary_payload(entry),
        "message_ids": entry.message_ids,
        "body": read_codex_body(entry),
    }


@router.get("/api/codex/{entry_id}/source", tags=["codex"])
async def codex_entry_source(entry_id: str) -> dict:
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
async def export_codex_entry(entry_id: str):
    try:
        entry, raw = read_raw_entry(entry_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Codex entry not found")

    filename = f"{_slugify(entry.title)}.md"
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Content-Type": "text/markdown; charset=utf-8",
    }
    return Response(content=raw, media_type="text/markdown", headers=headers)
