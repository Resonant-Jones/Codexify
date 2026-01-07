from __future__ import annotations

import re
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Response

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
