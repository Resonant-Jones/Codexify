from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from guardian.codex.lineage import ensure_lineage_exists, parse_lineage
from guardian.codex.service import (
    list_codex_entries,
    load_codex_entry,
    read_codex_body,
    read_raw_entry,
    save_codex_entry,
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
        "trigger_message_id": entry.trigger_message_id,
        "lineage_missing": entry.lineage_missing,
        "author_id": entry.author_id,
        "heat_score": entry.heat_score,
        "created_from": entry.created_from,
        "retrieval_enabled": entry.retrieval_enabled,
        "project_id": entry.project_id,
        "persona_id": entry.persona_id,
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


# ---------------------------------------------------------------------------
# Save and Draft endpoints
# ---------------------------------------------------------------------------

class CodexEntrySaveRequest(BaseModel):
    title: str
    body: str
    thread_id: int | None = None
    source_thread_id: int | None = None
    source_message_id: int | None = None
    trigger_message_id: int | None = None
    message_ids: list[int] | None = None
    author_id: str | None = None
    created_from: str | None = None
    retrieval_enabled: bool = False
    project_id: int | None = None
    persona_id: str | None = None


class CodexDraftRequest(BaseModel):
    thread_id: int
    trigger_message_id: int | None = None


@router.post("/api/codex/entries", tags=["codex"])
async def save_codex_entry_route(
    body: CodexEntrySaveRequest,
    api_key: str = Depends(require_api_key),
) -> dict:
    """Persist a Codex Entry artifact."""
    _ = api_key
    try:
        entry = save_codex_entry(
            title=body.title,
            body=body.body,
            thread_id=str(body.thread_id) if body.thread_id else None,
            source_thread_id=str(body.source_thread_id) if body.source_thread_id else None,
            source_message_id=str(body.source_message_id) if body.source_message_id else None,
            trigger_message_id=str(body.trigger_message_id) if body.trigger_message_id else None,
            message_ids=[str(m) for m in body.message_ids] if body.message_ids else None,
            author_id=body.author_id,
            created_from=body.created_from or "slash_command",
            retrieval_enabled=body.retrieval_enabled,
            project_id=str(body.project_id) if body.project_id else None,
            persona_id=body.persona_id,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "ok": True,
        "entry": {
            "id": entry.id,
            "title": entry.title,
            "created_at": _iso(entry.created_at),
            "thread_id": entry.thread_id,
            "source_thread_id": entry.source_thread_id,
            "source_message_id": entry.source_message_id,
            "trigger_message_id": entry.trigger_message_id,
            "created_from": entry.created_from,
            "retrieval_enabled": entry.retrieval_enabled,
        },
    }


@router.post("/api/codex/entries/draft", tags=["codex"])
async def generate_codex_draft(
    body: CodexDraftRequest,
    api_key: str = Depends(require_api_key),
) -> dict:
    """Generate a Codex Entry draft from prior thread context.

    The draft body is derived from the preceding messages in the thread
    window, not from the command text itself.  The trigger_message_id
    records which message invoked the command; source lineage records
    the prior message(s) that fed the draft.
    """
    _ = api_key
    thread_id = body.thread_id
    trigger_message_id = body.trigger_message_id

    if chatlog_db is None:
        raise HTTPException(status_code=503, detail="Chat log backend unavailable")

    # Fetch recent messages from the thread
    try:
        items = chatlog_db.list_messages(thread_id, limit=50, offset=0)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch thread messages: {e}")

    if not items:
        return {
            "ok": True,
            "draft": None,
            "reason": "no_context",
            "detail": "Thread has no prior messages to draft from.",
        }

    # Sort by message id ascending
    try:
        items = sorted(items, key=lambda m: m.get("id") or 0)
    except Exception:
        pass

    # Find the trigger message
    trigger_idx: int | None = None
    if trigger_message_id is not None:
        for idx, item in enumerate(items):
            mid = _coerce_thread_id(item.get("id"))
            if mid == trigger_message_id:
                trigger_idx = idx
                break
    elif items:
        # If no trigger specified, the last message is the trigger
        trigger_idx = len(items) - 1

    if trigger_idx is None:
        return {
            "ok": True,
            "draft": None,
            "reason": "no_trigger",
            "detail": "Could not locate the trigger message in thread history.",
        }

    # Source context: messages *before* the trigger, excluding the trigger
    prior_items = items[:trigger_idx]
    if not prior_items:
        return {
            "ok": True,
            "draft": None,
            "reason": "empty_source",
            "detail": "No prior messages available to generate a draft from. "
                       "Send at least one message before invoking /codex_entry.",
        }

    trigger_item = items[trigger_idx]
    trigger_mid = _coerce_thread_id(trigger_item.get("id"))

    # Collect source message IDs
    source_message_ids: list[int] = []
    source_bodies: list[str] = []
    last_source_mid: int | None = None
    for item in prior_items:
        mid = _coerce_thread_id(item.get("id"))
        content = item.get("content")
        if mid is not None:
            source_message_ids.append(mid)
            last_source_mid = mid
        if isinstance(content, str) and content.strip():
            source_bodies.append(content.strip())

    if not source_bodies:
        return {
            "ok": True,
            "draft": None,
            "reason": "empty_source",
            "detail": "Prior messages contained no usable text content.",
        }

    # Build a simple draft title from the first source message
    draft_title = _derive_draft_title(source_bodies[0])

    # Assemble draft body from the prior context
    draft_body = _assemble_draft_body(source_bodies)

    # Derive first and last source message IDs for the range
    first_source_mid = source_message_ids[0] if source_message_ids else last_source_mid

    return {
        "ok": True,
        "draft": {
            "title": draft_title,
            "body": draft_body,
            "lineage": {
                "thread_id": thread_id,
                "trigger_message_id": trigger_mid,
                "source_message_ids": source_message_ids,
                "first_source_message_id": first_source_mid,
                "last_source_message_id": last_source_mid,
            },
            "source_summary": _derive_source_summary(prior_items),
        },
    }


def _derive_draft_title(first_body: str) -> str:
    """Derive a short draft title from the first source message body."""
    cleaned = first_body[:120].strip().replace("\n", " ")
    # Remove leading slash commands
    cleaned = re.sub(r"^/\S+\s*", "", cleaned)
    if len(cleaned) > 80:
        cleaned = cleaned[:77].rsplit(" ", 1)[0] + "..."
    return cleaned or "Codex Entry"


def _assemble_draft_body(source_bodies: list[str]) -> str:
    """Assemble a markdown draft body from prior context messages."""
    parts: list[str] = []
    for idx, body_text in enumerate(source_bodies):
        role = "user" if idx % 2 == 0 else "assistant"
        label = "User" if role == "user" else "Assistant"
        parts.append(f"## {label}\n\n{body_text}\n")
    return "\n".join(parts)


def _derive_source_summary(prior_items: list[dict]) -> str:
    """Derive a short human-readable summary of the source context."""
    roles: list[str] = []
    for item in prior_items:
        role = str(item.get("role") or "").strip().lower()
        roles.append(role or "unknown")
    user_count = roles.count("user")
    assistant_count = roles.count("assistant")
    return (
        f"{len(prior_items)} messages "
        f"({user_count} user, {assistant_count} assistant)"
    )
