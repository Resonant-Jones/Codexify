"""
Chat Routes
~~~~~~~~~~~

Chat thread and message management endpoints.
Includes thread creation, messaging, completion, branching, and lineage tracking.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError, ConfigDict

logger = logging.getLogger(__name__)

# Import shared context
try:
    from guardian.guardian_api import (
        chatlog_db,
        require_api_key,
        _groq_complete,
        event_bus,
        _vector_store,
        _memory_store,
        _sensors,
        DEFAULT_MODEL,
    )
    from guardian.context.broker import ContextBroker
except ImportError as e:
    logger.warning(f"[chat] Import warning: {e}")
    chatlog_db = None
    require_api_key = lambda x: x
    _groq_complete = None
    event_bus = None
    ContextBroker = None
    _vector_store = None
    _memory_store = None
    _sensors = None
    DEFAULT_MODEL = None

# Optional Neo4j imports for graph sync
try:
    from guardian.db.neo import UserNode, MessageNode, ThreadNode    NEO4J_SYNC_AVAILABLE = True
    NEO4J_SYNC_AVAILABLE = True
except Exception:
    NEO4J_SYNC_AVAILABLE = False


# Pydantic models for thread operations
class ThreadDTO(BaseModel):
    id: int
    user_id: str
    title: str
    summary: str = ""
    project_id: Optional[int] = None
    parent_id: Optional[int] = None
    archived_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ThreadUpdate(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    project_id: Optional[int] = None
    archived: Optional[bool] = None


class ThreadBranchRequest(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    project_id: Optional[int] = None


class ThreadCreateRequest(BaseModel):
    parent_thread_id: int = None
    session_id: str = None
    summary: str = ""
    user_id: str = "default"
    project_id: str = None


# Helper functions
def _normalize_thread_title(raw: Optional[str]) -> Optional[str]:
    if raw is None:
        return None
    text = str(raw).strip()
    return text or "New Chat"


def _normalize_thread_summary(raw: Optional[str]) -> Optional[str]:
    if raw is None:
        return None
    return str(raw).strip()


def _apply_thread_update(thread_id: int, update: ThreadUpdate) -> Dict[str, Any]:
    """Apply updates to a thread and emit appropriate events."""
    payload = update.dict(exclude_unset=True)
    if not payload:
        raise HTTPException(status_code=400, detail="No valid fields to update")

    updated_field_keys = [key for key in ("title", "summary", "project_id") if key in payload]
    existing = chatlog_db.get_chat_thread(thread_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Thread not found")

    title_value = _normalize_thread_title(payload.get("title")) if "title" in payload else None
    summary_value = _normalize_thread_summary(payload.get("summary")) if "summary" in payload else None
    project_present = "project_id" in payload
    project_value = payload.get("project_id") if project_present else None
    archived_present = "archived" in payload
    archived_requested = payload.get("archived") if archived_present else None

    has_field_updates = any(
        field is not None for field in (
            title_value if "title" in payload else None,
            summary_value if "summary" in payload else None,
            project_value if project_present else None,
        )
    ) or project_present and payload.get("project_id") is None

    if not has_field_updates and not archived_present:
        raise HTTPException(status_code=400, detail="No valid fields to update")

    if has_field_updates:
        updated = chatlog_db.update_thread(
            thread_id,
            title=title_value if "title" in payload else None,
            summary=(summary_value if "summary" in payload else None),
            project_id=project_value if project_present else None,
        )
        if not updated:
            raise HTTPException(status_code=404, detail="Thread not found")

    refreshed = chatlog_db.get_chat_thread(thread_id)
    if not refreshed:
        raise HTTPException(status_code=404, detail="Thread not found")

    if has_field_updates:
        chatlog_db.write_audit_log(
            "update",
            "chat_thread",
            str(thread_id),
            user_id=refreshed.get("user_id", "default"),
        )
        event_bus.emit_event(
            "thread.updated",
            {
                "thread": refreshed,
                "changes": {key: payload.get(key) for key in updated_field_keys},
            },
        )
        logger.info(
            "[threads] updated thread_id=%s fields=%s",
            thread_id,
            updated_field_keys or list(payload.keys()),
        )

    if archived_requested is True:
        # Archive if not already archived
        if not refreshed.get("archived_at"):
            archived = chatlog_db.archive_thread(thread_id)
            if archived:
                refreshed = archived
                event_bus.emit_event("thread.archived", {"thread": archived})
                logger.info("[threads] archived thread_id=%s", thread_id)
                chatlog_db.write_audit_log(
                    "archive",
                    "chat_thread",
                    str(thread_id),
                    user_id=archived.get("user_id", "default"),
                )
        else:
            logger.debug("Thread %s already archived", thread_id)
    elif archived_requested is False:
        # Unarchive if currently archived
        if refreshed.get("archived_at"):
            unarchived = chatlog_db.unarchive_thread(thread_id)
            if unarchived:
                refreshed = unarchived
                event_bus.emit_event("thread.unarchived", {"thread": unarchived})
                logger.info("[threads] unarchived thread_id=%s", thread_id)
                chatlog_db.write_audit_log(
                    "unarchive",
                    "chat_thread",
                    str(thread_id),
                    user_id=unarchived.get("user_id", "default"),
                )
        else:
            logger.debug("Thread %s already unarchived", thread_id)

    return refreshed


router = APIRouter(prefix="/chat", tags=["Chat"])


# =========================
# Chat Threads API
# =========================

@router.post("/threads")
def chat_create_thread(body: dict = Body(...)):
    """Create a chat thread and return identifier metadata."""
    try:
        payload = body or {}
        raw_title = payload.get("title")
        title = (
            str(raw_title).strip() if raw_title is not None else "New Chat"
        ) or "New Chat"
        raw_user = payload.get("user_id")
        user_id = str(raw_user) if raw_user not in (None, "") else "default"
        raw_summary = payload.get("summary")
        summary = str(raw_summary).strip() if raw_summary is not None else ""
        project_id = payload.get("project_id")
        normalized_project: Optional[int] = None
        if project_id is not None:
            try:
                normalized_project = int(project_id)
            except (TypeError, ValueError):
                normalized_project = None
        if normalized_project is None:
            # default to Loose Threads (id=1)
            normalized_project = 1

        # Idempotency guard: check for recent empty thread from same user
        recent_thread = chatlog_db.get_recent_thread(user_id)
        if recent_thread:
            # If recent thread exists and has no messages, reuse it
            recent_id = recent_thread.get("id")
            if recent_id and chatlog_db.count_messages(recent_id) == 0:
                logger.info(
                    "Reusing recent empty thread %s for user %s", recent_id, user_id
                )
                return {"ok": True, "id": recent_id, "thread": recent_thread}

        record = chatlog_db.create_chat_thread(
            user_id=user_id,
            title=title,
            summary=summary,
            project_id=normalized_project,
        )
        chatlog_db.write_audit_log(
            "create", "chat_thread", str(record["id"]), user_id=user_id
        )
        return {"ok": True, "id": record["id"], "thread": record}
    except Exception as exc:
        logger.exception("Failed to create chat thread: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to create chat thread")


@router.get("/threads")
def chat_list_threads():
    """Return the list of persisted chat threads."""
    try:
        threads = chatlog_db.list_chat_threads()
        return {"ok": True, "threads": threads}
    except Exception as exc:
        logger.exception("Failed to list chat threads: %s", exc)
        return {"ok": True, "threads": []}


# =========================
# Chat Messages API
# =========================

@router.post("/{thread_id}/messages")
def chat_post_message(thread_id: int, body: Dict[str, str] = Body(...)):
    """Post a new message to a chat thread."""
    role = body.get("role")
    content = body.get("content", "").strip()
    if not role or not content:
        return JSONResponse(
            status_code=400, content={"ok": False, "error": "role and content required"}
        )
    owner = body.get("user_id") or "default"
    try:
        chatlog_db.ensure_chat_thread(
            thread_id=thread_id,
            user_id=str(owner),
            title="New Chat",
            summary="",
            project_id=1,  # always assign to Loose Threads by default
        )
    except Exception as exc:
        logger.exception("Failed to ensure chat thread %s exists: %s", thread_id, exc)
        raise HTTPException(status_code=500, detail="Failed to persist chat message")
    mid = chatlog_db.create_message(thread_id, role, content)
    chatlog_db.write_audit_log("create", "chat_message", str(mid), user_id=str(owner))

    # Emit event for real-time updates
    event_bus.emit_event(
        "message.created",
        {
            "thread_id": thread_id,
            "message_id": mid,
            "role": role,
            "content": content,
        },
    )

    # --- Neo4j sync ---
    if NEO4J_SYNC_AVAILABLE:
        try:
            import uuid
            # Use string IDs for Neo4j
            message_id = str(mid)
            thread_id_str = str(thread_id)
            user_id_str = str(owner)
            message_text = content

            neo_user = UserNode.nodes.get_or_none(user_id=user_id_str)
            if not neo_user:
                neo_user = UserNode(user_id=user_id_str, name=user_id_str).save()

            neo_thread = ThreadNode.nodes.get_or_none(thread_id=thread_id_str)
            if not neo_thread:
                neo_thread = ThreadNode(thread_id=thread_id_str).save()

            neo_msg = MessageNode(
                message_id=message_id,
                content=message_text,
                created_at=datetime.utcnow()
            ).save()

            neo_msg.user.connect(neo_user)
            neo_msg.thread.connect(neo_thread)

        except Exception as e:
            logger.warning(f"[Neo4j Sync Error] {e}")

    return {
        "ok": True,
        "message": {
            "id": mid,
            "thread_id": thread_id,
            "role": role,
            "content": content,
        },
    }


@router.get("/{thread_id}/messages")
def chat_list_messages(thread_id: int, limit: int = 50, offset: int = 0):
    """List messages for a chat thread."""
    items = chatlog_db.list_messages(thread_id, limit=limit, offset=offset)
    total = chatlog_db.count_messages(thread_id)
    return {"ok": True, "total": total, "messages": items}


@router.post("/{thread_id}/complete")
async def chat_complete(thread_id: int, body: Dict[str, Any] = Body(default_factory=dict)):
    """
    Generate an assistant reply for the given thread using the configured provider
    and persist it as a new message (role='assistant'). Emits message.created.
    Optional body:
      - model: override model name
      - max_context: how many recent messages to include (default 50)
    """
    try:
        limit = int(body.get("max_context") or 50)
        items = chatlog_db.list_messages(thread_id, limit=limit, offset=0)

        # Shape OpenAI-style messages; drop empty or literal "null" content
        context: List[Dict[str, str]] = []
        for m in items:
            role = str(m.get("role") or "").strip()
            content = m.get("content")
            if isinstance(content, str) and content.strip() and content.strip().lower() != "null":
                context.append({"role": role, "content": content})

        if not context:
            raise HTTPException(status_code=400, detail="Thread has no usable context")

        # Build ContextBroker bundle using latest user message as query
        latest_message = ""
        for m in reversed(items):
            if str(m.get("role") or "").strip() == "user":
                lm = str(m.get("content") or "").strip()
                if lm:
                    latest_message = lm
                    break

        depth = str(body.get("depth") or "normal").strip().lower()
        bundle: Optional[Dict[str, Any]] = None
        try:
            broker = ContextBroker(chatlog_db, _vector_store, _memory_store, _sensors)
            bundle = await broker.assemble(thread_id, query=latest_message, depth=depth)
        except Exception as e:
            logger.warning("[context] broker assemble failed (depth=%s): %s", depth, e)
            bundle = None

        model = body.get("model") or DEFAULT_MODEL
        assistant_text = _groq_complete(context, model=model, context=bundle)

        mid = chatlog_db.create_message(thread_id, "assistant", assistant_text)
        try:
            chatlog_db.write_audit_log("create", "chat_message", str(mid), user_id="bot")
        except Exception:
            pass

        try:
            event_bus.emit_event("message.created", {"thread_id": thread_id, "message_id": mid, "role": "assistant"})
        except Exception:
            logger.debug("[live] emit message.created failed", exc_info=True)

        return {"ok": True, "message": {"id": mid, "thread_id": thread_id, "role": "assistant", "content": assistant_text}}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("complete failed: %s", exc)
        raise HTTPException(status_code=500, detail="completion_failed")


@router.delete("/{thread_id}/messages/{message_id}")
def chat_delete_message(thread_id: int, message_id: int):
    """Delete a message from a chat thread."""
    chatlog_db.delete_message(thread_id, message_id)
    chatlog_db.write_audit_log(
        "delete", "chat_message", str(message_id), user_id="default"
    )
    return {"ok": True}


# =========================
# Thread Management
# =========================

@router.post("/{thread_id}/branch", response_model=ThreadDTO)
def branch_thread(
    thread_id: int,
    body: Optional[ThreadBranchRequest] = Body(default=None),
    api_key: str = Depends(require_api_key),
):
    """Create a branch (child thread) from an existing thread."""
    payload = body or ThreadBranchRequest()
    parent = chatlog_db.get_chat_thread(thread_id)
    if not parent:
        raise HTTPException(status_code=404, detail="Thread not found")

    title = _normalize_thread_title(payload.title)
    if title is None:
        base_title = parent.get("title") or "New Chat"
        title = f"{base_title} (branch)"

    summary = _normalize_thread_summary(payload.summary)
    if summary is None:
        summary = parent.get("summary") or ""

    project_id: Optional[int]
    if payload.project_id is not None:
        project_id = payload.project_id
    else:
        project_id = parent.get("project_id")
        try:
            project_id = int(project_id) if project_id is not None else None
        except (TypeError, ValueError):
            project_id = None

    child = chatlog_db.create_chat_thread(
        user_id=parent.get("user_id", "default"),
        title=title,
        summary=summary,
        project_id=project_id,
        parent_id=parent["id"],
    )

    chatlog_db.write_audit_log(
        "create",
        "chat_thread",
        str(child["id"]),
        user_id=child.get("user_id", "default"),
    )

    event_bus.emit_event(
        "thread.branch",
        {
            "parent": {
                "id": parent.get("id"),
                "title": parent.get("title"),
                "archived_at": parent.get("archived_at"),
                "project_id": parent.get("project_id"),
            },
            "child": child,
        },
    )

    return child


@router.patch("/{thread_id}", response_model=ThreadDTO)
def update_thread(thread_id: int, payload: ThreadUpdate, api_key: str = Depends(require_api_key)):
    """Update thread metadata (title, summary, project, archive status)."""
    updated = _apply_thread_update(thread_id, payload)
    return updated


@router.patch("/threads/{thread_id}")
def patch_thread(thread_id: int, body: Dict[str, object] = Body(...)):
    """Alternative PATCH endpoint for thread updates (less strict validation)."""
    try:
        update = ThreadUpdate(**(body or {}))
        refreshed = _apply_thread_update(thread_id, update)
        return {"ok": True, "thread": refreshed}
    except ValidationError as err:
        logger.warning("Invalid payload for thread update: %s", err)
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": "Invalid payload"},
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to update chat thread %s: %s", thread_id, exc)
        return JSONResponse(
            status_code=500, content={"ok": False, "error": "Failed to update thread"}
        )


@router.delete("/{thread_id}")
def delete_thread(thread_id: int, force: bool = Query(False)):
    """Hard delete a thread regardless of archived state."""
    deleted = chatlog_db.delete_thread(thread_id, force=force)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Thread not found or not deletable (archive first or set force=true)"
        )
    try:
        event_bus.emit_event("thread.deleted", {"thread_id": thread_id})
    except Exception:
        pass
    logger.info("[threads] deleted thread_id=%s", thread_id)
    return {"ok": True}


# =========================
# Thread Lineage Endpoints
# =========================

threads_router = APIRouter(prefix="/threads", tags=["Threads"])


@threads_router.get("")
def list_threads(
    user_id: str = Query(None, description="Filter by user_id"),
    project_id: str = Query(None, description="Filter by project_id"),
    api_key: str = Depends(require_api_key),
):
    """List all threads. Optionally filter by user or project."""
    try:
        items = chatlog_db.list_threads(user_id=user_id, project_id=project_id)
        return {"threads": items}
    except Exception as exc:
        if (
            "no such table" in str(exc).lower()
            or getattr(exc, "pgcode", None) == "42P01"
        ):
            return {"threads": []}
        logger.exception("Thread listing failed")
        raise HTTPException(status_code=500, detail="Thread listing failed")


@threads_router.post("")
def create_thread_alias(
    req: ThreadCreateRequest, api_key: str = Depends(require_api_key)
):
    """Create a new thread (alias endpoint)."""
    thread_id = chatlog_db.create_thread(
        parent_thread_id=req.parent_thread_id,
        session_id=req.session_id,
        summary=req.summary,
        user_id=req.user_id,
        project_id=req.project_id,
    )
    return {"thread_id": thread_id}


# Single thread endpoints
thread_router = APIRouter(prefix="/thread", tags=["Threads"])


@thread_router.get("/{thread_id}")
def get_thread(thread_id: int, api_key: str = Depends(require_api_key)):
    """Get details for a specific thread by thread_id."""
    row = chatlog_db.get_thread(thread_id)
    if not row:
        raise HTTPException(status_code=404, detail="Thread not found")
    return {
        "thread_id": row[0],
        "parent_thread_id": row[1],
        "session_id": row[2],
        "summary": row[3],
        "created_at": row[4],
        "user_id": row[5],
        "project_id": row[6],
    }


@thread_router.get("/{thread_id}/children")
def get_child_threads(thread_id: int, api_key: str = Depends(require_api_key)):
    """List all child threads for a parent thread."""
    rows = chatlog_db.get_child_threads(thread_id)
    results = [
        {
            "thread_id": row.get("id"),
            "user_id": row.get("user_id"),
            "title": row.get("title"),
            "summary": row.get("summary"),
            "project_id": row.get("project_id"),
            "parent_id": row.get("parent_id"),
            "archived_at": row.get("archived_at"),
            "created_at": row.get("created_at"),
            "updated_at": row.get("updated_at"),
        }
        for row in rows
    ]
    return {"children": results}


@thread_router.get("/{thread_id}/summary")
def get_thread_summary(thread_id: int, api_key: str = Depends(require_api_key)):
    """Get the summary for a thread."""
    summary = chatlog_db.get_thread_summary(thread_id)
    return {"thread_id": thread_id, "summary": summary}


@thread_router.post("")
def create_thread(req: ThreadCreateRequest, api_key: str = Depends(require_api_key)):
    """Create a new thread with optional parent, summary, session, user, and project."""
    thread_id = chatlog_db.create_thread(
        parent_thread_id=req.parent_thread_id,
        session_id=req.session_id,
        summary=req.summary,
        user_id=req.user_id,
        project_id=req.project_id,
    )
    return {"thread_id": thread_id}
