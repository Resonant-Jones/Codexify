"""
Memory Routes
~~~~~~~~~~~~~

Memory management endpoints for ephemeral, midterm, and longterm storage.
Includes memory pruning, search, and history retrieval.
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Import shared context (initialized via guardian.core.dependencies in app startup)
chatlog_db = None
require_api_key = lambda x: x


def bind_dependencies(*, chatlog_db_instance, require_api_key_func):
    """
    Bind runtime dependencies for memory routes.

    This function should be called after guardian_api initializes its globals
    to ensure memory routes have access to the database and auth function.

    Args:
        chatlog_db_instance: Initialized ChatDB instance
        require_api_key_func: API key validation dependency function
    """
    global chatlog_db, require_api_key
    chatlog_db = chatlog_db_instance
    require_api_key = require_api_key_func
    logger.info("[memory] dependencies bound successfully")


# User context dependency for extracting user ID from request headers
def get_current_user(
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
) -> str:
    """
    Determine the current user for memory operations.

    - If X-User-Id header is present, use it.
    - Otherwise, default to \"default\" (single-user dev/test behavior).
    """
    return x_user_id or "default"


# Memory retention configuration
MEMORY_RETENTION_DAYS = int(os.getenv("MEMORY_RETENTION_DAYS", "90"))
EPHEMERAL_MEMORY: List[Dict[str, Any]] = []

# Prune expired midterm memories at startup
try:
    # Use timezone-aware UTC timestamps to avoid deprecation warnings
    cutoff = (
        datetime.now(datetime.UTC) - timedelta(days=MEMORY_RETENTION_DAYS)
    ).isoformat()
    pruned = chatlog_db.prune_midterm(cutoff)
    if pruned:
        logger.info("[memory] pruned %d expired midterm entries", pruned)
except Exception as _e:
    logger.debug("[memory] prune skipped: %s", _e)


def _silo_valid(s: str) -> bool:
    return s in ("ephemeral", "midterm", "longterm")


router = APIRouter(prefix="/api/memory", tags=["Memory"])


class MemoryCreate(BaseModel):
    """Request model for creating memory entries."""

    content: str
    tags: List[str] = Field(default_factory=list)
    pinned: bool = False


@router.get("/{silo}")
def memory_list(
    silo: str,
    limit: int = 50,
    offset: int = 0,
    current_user: str = Depends(get_current_user),
):
    """
    List memory entries from the specified silo for the authenticated user.

    Args:
        silo: Memory silo (ephemeral, midterm, longterm)
        limit: Maximum number of entries to return
        offset: Starting offset for pagination
        current_user: Authenticated user ID (injected)

    Returns:
        Memory entries and total count for the authenticated user
    """
    if not _silo_valid(silo):
        return JSONResponse(
            status_code=400, content={"ok": False, "error": "invalid silo"}
        )
    if silo == "ephemeral":
        # Filter ephemeral memory by user_id
        user_items = [
            e for e in EPHEMERAL_MEMORY if e.get("user_id") == current_user
        ]
        items = user_items[offset : offset + limit]
        return {"ok": True, "count": len(user_items), "entries": items}
    # Filter database memories by user_id
    items = chatlog_db.list_memories(
        silo, user_id=current_user, limit=limit, offset=offset
    )
    count = chatlog_db.count_memories(silo, user_id=current_user)
    return {"ok": True, "count": count, "entries": items}


@router.post("/{silo}")
def memory_create(
    silo: str,
    body: MemoryCreate = Body(...),
    current_user: str = Depends(get_current_user),
):
    """
    Create a new memory entry in the specified silo for the authenticated user.

    Args:
        silo: Memory silo (ephemeral, midterm, longterm)
        body: Memory entry data with content, tags, and pinned flag
        current_user: Authenticated user ID (injected)

    Returns:
        Created entry ID or full entry for ephemeral
    """
    if not _silo_valid(silo):
        return JSONResponse(
            status_code=400, content={"ok": False, "error": "invalid silo"}
        )
    content = body.content.strip()
    tags = ",".join(body.tags or [])
    pinned = bool(body.pinned)
    if not content:
        return JSONResponse(
            status_code=400, content={"ok": False, "error": "content required"}
        )
    if silo == "ephemeral":
        entry = {
            "id": len(EPHEMERAL_MEMORY) + 1,
            "user_id": current_user,
            "silo": "ephemeral",
            "content": content,
            "tags": tags,
            "pinned": pinned,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        EPHEMERAL_MEMORY.append(entry)
        return {"ok": True, "entry": entry}

    # Ensure chatlog_db is initialized even if bind_dependencies was not called
    if chatlog_db is None:
        from guardian.core.dependencies import chatlog_db as core_chatlog_db
        from guardian.core.dependencies import init_database

        init_database()
        if core_chatlog_db is None:
            raise RuntimeError("chatlog_db is not initialised")
        globals()["chatlog_db"] = core_chatlog_db

    eid = chatlog_db.add_memory(
        current_user, silo, content, tags=tags, pinned=pinned
    )
    chatlog_db.write_audit_log(
        "create", "memory_entry", str(eid), user_id=current_user
    )
    return {"ok": True, "id": eid}


@router.patch("/{silo}/{entry_id}")
def memory_update(
    silo: str,
    entry_id: int,
    body: Dict[str, object] = Body(...),
    current_user: str = Depends(get_current_user),
):
    """
    Update an existing memory entry for the authenticated user.

    Args:
        silo: Memory silo
        entry_id: Entry ID to update
        body: Updated fields (content, tags, pinned)
        current_user: Authenticated user ID (injected)

    Returns:
        Success status
    """
    if not _silo_valid(silo):
        return JSONResponse(
            status_code=400, content={"ok": False, "error": "invalid silo"}
        )
    if silo == "ephemeral":
        for e in EPHEMERAL_MEMORY:
            if e.get("id") == entry_id and e.get("user_id") == current_user:
                if "content" in body:
                    e["content"] = str(body["content"])
                if "tags" in body:
                    e["tags"] = ",".join(body.get("tags", []) or [])
                if "pinned" in body:
                    e["pinned"] = bool(body["pinned"])
                e["updated_at"] = datetime.now(timezone.utc).isoformat()
                return {"ok": True}
        return JSONResponse(
            status_code=404, content={"ok": False, "error": "not found"}
        )
    # Verify ownership before updating
    existing = chatlog_db.get_memory(entry_id)
    if not existing or existing.get("user_id") != current_user:
        return JSONResponse(
            status_code=404, content={"ok": False, "error": "not found"}
        )
    chatlog_db.update_memory(
        entry_id,
        content=body.get("content"),
        tags=(
            ",".join(body.get("tags", []) or [])
            if body.get("tags") is not None
            else None
        ),
        pinned=body.get("pinned") if body.get("pinned") is not None else None,
    )
    chatlog_db.write_audit_log(
        "update", "memory_entry", str(entry_id), user_id=current_user
    )
    return {"ok": True}


@router.delete("/{silo}/{entry_id}")
def memory_delete(
    silo: str,
    entry_id: int,
    current_user: str = Depends(get_current_user),
):
    """
    Delete a memory entry for the authenticated user.

    Args:
        silo: Memory silo
        entry_id: Entry ID to delete
        current_user: Authenticated user ID (injected)

    Returns:
        Success status
    """
    if not _silo_valid(silo):
        return JSONResponse(
            status_code=400, content={"ok": False, "error": "invalid silo"}
        )
    if silo == "ephemeral":
        idx = next(
            (
                i
                for i, e in enumerate(EPHEMERAL_MEMORY)
                if e.get("id") == entry_id and e.get("user_id") == current_user
            ),
            -1,
        )
        if idx >= 0:
            EPHEMERAL_MEMORY.pop(idx)
            return {"ok": True}
        return JSONResponse(
            status_code=404, content={"ok": False, "error": "not found"}
        )
    # Verify ownership before deleting
    existing = chatlog_db.get_memory(entry_id)
    if not existing or existing.get("user_id") != current_user:
        return JSONResponse(
            status_code=404, content={"ok": False, "error": "not found"}
        )
    chatlog_db.delete_memory(entry_id)
    chatlog_db.write_audit_log(
        "delete", "memory_entry", str(entry_id), user_id=current_user
    )
    return {"ok": True}


# Additional memory endpoints


@router.get("/health/memory", tags=["Health"])
def health_memory(current_user: str = Depends(get_current_user)):
    """
    Get health status of memory silos for the authenticated user.

    Args:
        current_user: Authenticated user ID (injected)

    Returns:
        Count of memory entries per silo for the authenticated user
    """
    # Filter ephemeral memory by user
    user_ephemeral_count = len(
        [e for e in EPHEMERAL_MEMORY if e.get("user_id") == current_user]
    )
    return {
        "ok": True,
        "silos": {
            "ephemeral": user_ephemeral_count,
            "midterm": chatlog_db.count_memories(
                "midterm", user_id=current_user
            ),
            "longterm": chatlog_db.count_memories(
                "longterm", user_id=current_user
            ),
        },
    }


# GitHub-specific memory search
github_router = APIRouter(prefix="/api/github", tags=["Memory", "GitHub"])


@github_router.get("/search", summary="Search GitHub memory (github silo)")
def github_memory_search(
    query: str = Query(
        ...,
        description="Search query string (full‑text over GitHub issues/PRs)",
    ),
    repo: Optional[str] = Query(
        None,
        description="Optional owner/repo filter (e.g. Resonant-Jones/guardian-backend)",
    ),
    limit: int = Query(
        20, ge=1, le=100, description="Maximum number of results to return"
    ),
    current_user: str = Depends(get_current_user),
):
    """
    Search the GitHub documents that were ingested into the `memory_entries`
    table (silo='github') for the authenticated user. Supports an optional `repo` filter.

    Args:
        query: Search query string
        repo: Optional repository filter
        limit: Maximum number of results
        current_user: Authenticated user ID (injected)

    Returns:
        GitHub memory search results
    """
    try:
        rows = chatlog_db.search_github_memory(
            query, repo=repo, limit=limit, user_id=current_user
        )
        results = []
        for r in rows:
            payload = r.get("payload") or {}
            results.append(
                {
                    "id": r["id"],
                    "key": r["key"],
                    "repo": payload.get("repo"),
                    "type": payload.get("type"),
                    "title": payload.get("title"),
                    "url": payload.get("url"),
                    "state": payload.get("state"),
                    "created_at": payload.get("created_at"),
                }
            )
        return {"ok": True, "count": len(results), "results": results}
    except Exception as exc:
        logger.error("GitHub memory search failed: %s", exc)
        raise HTTPException(
            status_code=500, detail="GitHub memory search failed"
        )


# General search and history endpoints
search_router = APIRouter(tags=["Memory"])


@search_router.get("/search", summary="Search memory entries")
def search(
    query: str = Query(..., description="Search query string"),
    limit: int = Query(10, ge=1, le=100),
    current_user: str = Depends(get_current_user),
):
    """
    Search the Guardian memory entries matching the query string for the authenticated user.

    Args:
        query: The search query
        limit: Maximum number of results to return
        current_user: Authenticated user ID (injected)

    Returns:
        List of matching memory entries for the authenticated user
    """
    try:
        rows = chatlog_db.search_memory(query, limit, user_id=current_user)
        results = [
            {
                "timestamp": r["timestamp"],
                "command": r["command"],
                "tag": r["tag"],
                "agent": r["agent"],
            }
            for r in rows
        ]
        logger.info(
            f"Search performed with query: {query}, results found: {len(results)}"
        )
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail="Search operation failed")
    return results


@search_router.get(
    "/history", summary="Retrieve history entries with optional filters"
)
def history(
    limit: int = Query(
        10, ge=1, le=100, description="Maximum number of entries to return"
    ),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    agent: Optional[str] = Query(None, description="Filter by agent"),
    start_date: Optional[str] = Query(
        None,
        description="Filter entries from this date (inclusive), format YYYY-MM-DD",
    ),
    end_date: Optional[str] = Query(
        None,
        description="Filter entries up to this date (inclusive), format YYYY-MM-DD",
    ),
    current_user: str = Depends(get_current_user),
):
    """
    Retrieve history entries from Guardian memory for the authenticated user with optional filtering.

    Args:
        limit: Maximum number of entries to return
        tag: Filter entries by tag
        agent: Filter entries by agent
        start_date: Filter entries from this date (inclusive)
        end_date: Filter entries up to this date (inclusive)
        current_user: Authenticated user ID (injected)

    Returns:
        List of filtered history entries for the authenticated user
    """
    # Validate date formats
    start_dt = None
    end_dt = None
    try:
        if start_date:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        if end_date:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError as ve:
        logger.error(f"Invalid date format in history filters: {ve}")
        raise HTTPException(
            status_code=400, detail="Invalid date format. Use YYYY-MM-DD."
        )

    try:
        rows = chatlog_db.history_entries(
            limit=limit, tag=tag, agent=agent, user_id=current_user
        )
        filtered_rows = []
        for r in rows:
            entry_dt = datetime.fromisoformat(r["timestamp"])
            if start_dt and entry_dt < start_dt:
                continue
            if end_dt and entry_dt > end_dt:
                continue
            filtered_rows.append(r)
        results = [
            {
                "timestamp": r["timestamp"],
                "command": r["command"],
                "tag": r["tag"],
                "agent": r["agent"],
            }
            for r in filtered_rows
        ]
        logger.info(
            f"History retrieved with filters - tag: {tag}, agent: {agent}, start_date: {start_date}, end_date: {end_date}, entries returned: {len(results)}"
        )
    except Exception as e:
        logger.error(f"Failed to retrieve history entries: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve history entries"
        )
    return results


# Log and summarize endpoints (for memory event storage)


class LogEntry(BaseModel):
    command: str
    tag: Optional[str] = None
    agent: Optional[str] = "system"


class SummaryEntry(BaseModel):
    parent_id: int
    summary: str
    tag: Optional[str] = None
    agent: Optional[str] = "system"


log_router = APIRouter(tags=["Memory"])


@log_router.post("/log", summary="Log a command entry")
def log_entry(entry: LogEntry, current_user: str = Depends(get_current_user)):
    """
    Log a command entry into the Guardian memory database for the authenticated user.

    Args:
        entry: The log entry data
        current_user: Authenticated user ID (injected)

    Returns:
        Confirmation message with timestamp
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    try:
        chatlog_db.insert_memory_event(
            content=entry.command,
            tag=entry.tag,
            agent=entry.agent or "system",
            type_="log",
            parent_id=None,
            user_id=current_user,
        )
        logger.info(f"Log entry stored: {entry.command}")
    except Exception as e:
        logger.error(f"Failed to store log entry: {e}")
        raise HTTPException(status_code=500, detail="Failed to store log entry")
    return {"result": "Log stored!", "timestamp": timestamp}


@log_router.post("/summarize", summary="Store a summary entry")
def summarize_entry(
    entry: SummaryEntry, current_user: str = Depends(get_current_user)
):
    """
    Store a summary related to a parent entry in the Guardian memory database for the authenticated user.

    Args:
        entry: The summary entry data
        current_user: Authenticated user ID (injected)

    Returns:
        Confirmation message with timestamp
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    try:
        chatlog_db.insert_memory_event(
            content=entry.summary,
            tag=entry.tag,
            agent=entry.agent or "system",
            type_="summary",
            parent_id=entry.parent_id,
            user_id=current_user,
        )
        logger.info(f"Summary entry stored for parent_id {entry.parent_id}")
    except Exception as e:
        logger.error(f"Failed to store summary entry: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to store summary entry"
        )
    return {"result": "Summary stored!", "timestamp": timestamp}
