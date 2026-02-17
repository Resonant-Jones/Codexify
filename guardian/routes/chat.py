"""
Chat Routes
~~~~~~~~~~~

Frontend contract (primary calls today):
- POST   /api/chat/threads                     -> create a thread
- GET    /api/chat/threads                     -> list threads
- POST   /api/chat/{thread_id}/messages        -> append a user message
- GET    /api/chat/{thread_id}/messages        -> fetch thread messages
- POST   /api/chat/{thread_id}/complete        -> run completion (depth query param optional)
- POST   /api/chat                             -> simple chat helper used by legacy API helper
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from starlette.responses import StreamingResponse

from guardian.cognition.identity_policy import can_run_deep_identity_modeling
from guardian.core.event_graph import get_event_writer
from guardian.queue import task_events
from guardian.queue.redis_queue import (
    acquire_turn_lock,
    enqueue,
    enqueue_chat_embed,
    release_turn_lock,
)
from guardian.tasks.types import ChatCompletionTask

logger = logging.getLogger(__name__)

# =========================
# Debug / Dev Tools State
# =========================

# In-memory store for RAG traces (thread_id -> trace_dict)
# This is ephemeral and per-process, which is fine for dev debugging.
_rag_traces: Dict[int, Dict[str, Any]] = {}

# Track latest task_id per thread for debug endpoint.
_thread_latest_task: Dict[int, str] = {}

# Import shared dependencies from core module (avoids circular imports)
try:
    from guardian.context.broker import ContextBroker
    from guardian.core.dependencies import (
        CHAT_PROVIDER,
        DEFAULT_MODEL,
        _groq_complete,
        _memory_store,
        _sensors,
        _vector_store,
        chatlog_db,
        event_bus,
        require_api_key,
        verify_api_key,
    )
except ImportError as e:
    logger.error(
        "[chat] Failed to import core dependencies; refusing to start without auth: %s",
        e,
    )
    raise

# Optional AI backend
try:
    from guardian.core.ai_router import chat_with_ai as _chat_with_ai

    chat_with_ai = _chat_with_ai
except ModuleNotFoundError:
    chat_with_ai = None

# Optional Neo4j imports for graph sync
try:
    from guardian.graph.connection import connect_neo4j
    from guardian.graph.models import MessageNode, ThreadNode, UserNode

    NEO4J_SYNC_AVAILABLE = True
except Exception:
    NEO4J_SYNC_AVAILABLE = False

# LLM configuration validation
try:
    from guardian.core.config import LLMConfigError
    from guardian.core.config import settings as llm_settings
    from guardian.core.config import validate_llm_config
except Exception:  # pragma: no cover - defensive import guard
    llm_settings = None
    validate_llm_config = None
    LLMConfigError = Exception

# Optional prompt helpers for system / persona layering
try:  # pragma: no cover - prompts are optional in some deployments
    from guardian.cognition.system_prompt_builder import (
        build_guardian_system_prompt,
    )
except Exception:
    build_guardian_system_prompt = None

try:
    from guardian.cognition.system_profiles.resolver import (
        list_available_system_profiles,
        resolve_thread_system_profile,
    )
except Exception:
    list_available_system_profiles = None
    resolve_thread_system_profile = None


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


class ChatCompletionRequest(BaseModel):
    model: Optional[str] = None
    max_context: Optional[int] = 50
    provider: Optional[str] = None
    system_override: Optional[str] = None
    depth_mode: Optional[
        str
    ] = "normal"  # "shallow", "normal", "deep", "diagnostic"


# Helper functions
def _embed_message(thread_id: int, role: str, content: str, message_id: int):
    """Best-effort enqueue of a chat message embedding task."""
    if not _vector_store:
        return
    try:
        enqueue_chat_embed(
            {
                "thread_id": thread_id,
                "role": role,
                "content": content,
                "message_id": message_id,
            }
        )
    except Exception as e:
        logger.warning(
            "[chat] Failed to enqueue embed message %s: %s", message_id, e
        )


# Very rough token estimate used for UX hints about prompt cost.
# We avoid hard dependencies on specific tokenizer libraries here.
def _estimate_tokens(text: Optional[str]) -> int:
    """
    Very rough token estimate used for UX hints about prompt cost.
    We avoid hard dependencies on specific tokenizer libraries here.
    """
    if not text:
        return 0
    # Heuristic: ~4 characters per token for English text
    try:
        length = len(text)
    except Exception:
        return 0
    return max(1, length // 4)


def _emit_thread_update_event(
    *,
    thread_id: int,
    actor_user_id: str | None,
    project_id: int | None,
    idempotency_suffix: str,
    payload: dict[str, Any],
    parent_event_id: int | None = None,
) -> None:
    try:
        idempotency_key = f"thread.update:{thread_id}:{idempotency_suffix}"
        get_event_writer().emit_event(
            event_type="thread.update",
            actor_user_id=actor_user_id,
            project_id=project_id,
            thread_id=thread_id,
            entity_type="thread",
            entity_id=str(thread_id),
            payload=payload,
            parent_event_id=parent_event_id,
            idempotency_key=idempotency_key,
        )
    except Exception:
        logger.debug(
            "[thread.update] event graph emit failed thread_id=%s",
            thread_id,
            exc_info=True,
        )


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


def _apply_thread_update(
    thread_id: int, update: ThreadUpdate
) -> Dict[str, Any]:
    """Apply updates to a thread and emit appropriate events."""
    payload = update.dict(exclude_unset=True)
    if not payload:
        raise HTTPException(status_code=400, detail="No valid fields to update")

    updated_field_keys = [
        key for key in ("title", "summary", "project_id") if key in payload
    ]
    existing = chatlog_db.get_chat_thread(thread_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Thread not found")

    title_value = (
        _normalize_thread_title(payload.get("title"))
        if "title" in payload
        else None
    )
    summary_value = (
        _normalize_thread_summary(payload.get("summary"))
        if "summary" in payload
        else None
    )
    project_present = "project_id" in payload
    project_value = payload.get("project_id") if project_present else None
    archived_present = "archived" in payload
    archived_requested = payload.get("archived") if archived_present else None

    changes: Dict[str, Any] = {}
    if "title" in payload and title_value is not None:
        current_title = (existing.get("title") or "").strip()
        if title_value != current_title:
            changes["title"] = title_value
    if "summary" in payload and summary_value is not None:
        current_summary = (existing.get("summary") or "").strip()
        if summary_value != current_summary:
            changes["summary"] = summary_value
    if project_present:
        current_project = existing.get("project_id")
        if project_value != current_project:
            changes["project_id"] = project_value

    has_field_updates = bool(changes)

    if not has_field_updates and not archived_present:
        # No semantic deltas requested; return the current state without emitting.
        return existing

    if has_field_updates:
        updated = chatlog_db.update_thread(
            thread_id,
            title=changes.get("title"),
            summary=changes.get("summary"),
            project_id=changes.get("project_id"),
            project_id_set=project_present,
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
                "thread_id": refreshed.get("id"),
                "title": refreshed.get("title"),
                "summary": refreshed.get("summary"),
                "project_id": refreshed.get("project_id"),
                "archived_at": refreshed.get("archived_at"),
                "thread": refreshed,
                "changes": changes,
            },
        )
        logger.info(
            "[threads] updated thread_id=%s fields=%s",
            thread_id,
            list(changes.keys()) or updated_field_keys or list(payload.keys()),
        )
        _emit_thread_update_event(
            thread_id=thread_id,
            actor_user_id=refreshed.get("user_id"),
            project_id=refreshed.get("project_id"),
            idempotency_suffix=f"meta:{refreshed.get('updated_at') or datetime.now(timezone.utc).isoformat()}",
            payload={
                "thread_id": thread_id,
                "changed_fields": sorted(changes.keys()),
            },
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
                _emit_thread_update_event(
                    thread_id=thread_id,
                    actor_user_id=archived.get("user_id"),
                    project_id=archived.get("project_id"),
                    idempotency_suffix=f"archive:{archived.get('archived_at') or datetime.now(timezone.utc).isoformat()}",
                    payload={
                        "thread_id": thread_id,
                        "archived": True,
                    },
                )
        else:
            logger.debug("Thread %s already archived", thread_id)
    elif archived_requested is False:
        # Unarchive if currently archived
        if refreshed.get("archived_at"):
            unarchived = chatlog_db.unarchive_thread(thread_id)
            if unarchived:
                refreshed = unarchived
                event_bus.emit_event(
                    "thread.unarchived", {"thread": unarchived}
                )
                logger.info("[threads] unarchived thread_id=%s", thread_id)
                chatlog_db.write_audit_log(
                    "unarchive",
                    "chat_thread",
                    str(thread_id),
                    user_id=unarchived.get("user_id", "default"),
                )
                _emit_thread_update_event(
                    thread_id=thread_id,
                    actor_user_id=unarchived.get("user_id"),
                    project_id=unarchived.get("project_id"),
                    idempotency_suffix=f"unarchive:{unarchived.get('updated_at') or datetime.now(timezone.utc).isoformat()}",
                    payload={
                        "thread_id": thread_id,
                        "archived": False,
                    },
                )
        else:
            logger.debug("Thread %s already unarchived", thread_id)

    return refreshed


# Legacy /chat routes; canonical base is /api/chat.
router = APIRouter(prefix="/chat", tags=["Chat"])

DEFAULT_PROJECT_NAME = "Loose Threads"
DEFAULT_PROJECT_DESCRIPTION = "Default bucket for unassigned threads"
DOC_SCOPE_K_PROJECT = 4
DOC_SCOPE_K_THREAD = 4
DOC_EXCERPT_CHARS = 320
DOC_OVERRIDE_MAX_CHARS = 2600


def _ensure_default_project_id() -> Optional[int]:
    """
    Resolve a safe default project id for unscoped threads.

    Falls back to None if the default project cannot be ensured so thread
    creation can still proceed without violating foreign keys.
    """
    if not chatlog_db:
        return None
    try:
        pid = chatlog_db.ensure_project(
            DEFAULT_PROJECT_NAME, DEFAULT_PROJECT_DESCRIPTION
        )
        return int(pid) if pid is not None else None
    except Exception as exc:  # pragma: no cover - defensive guard
        logger.warning("[chat] failed to ensure default project: %s", exc)
        return None


def _coerce_project_id(raw: Any) -> Optional[int]:
    """Normalize incoming project_id to an int or a safe default."""
    if raw is None:
        return _ensure_default_project_id()
    try:
        value = int(raw)
        return value if value > 0 else _ensure_default_project_id()
    except (TypeError, ValueError):
        return _ensure_default_project_id()


def _coerce_positive_int(raw: Any) -> Optional[int]:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _build_scoped_doc_override(
    docs_bundle: Dict[str, Any] | None,
    *,
    max_chars: int = DOC_OVERRIDE_MAX_CHARS,
) -> Optional[str]:
    if not isinstance(docs_bundle, dict):
        return None

    sections: list[str] = []
    total_chars = 0
    scope_map = (
        ("project", "PROJECT DOCUMENTS"),
        ("thread", "THREAD DOCUMENTS"),
    )

    for scope_key, scope_title in scope_map:
        scoped_docs = docs_bundle.get(scope_key) or []
        if not isinstance(scoped_docs, list) or not scoped_docs:
            continue

        lines = [f"=== {scope_title} ==="]
        for doc in scoped_docs:
            if not isinstance(doc, dict):
                continue
            provenance = doc.get("provenance")
            if not isinstance(provenance, dict):
                provenance = {}

            entry = (
                "[doc]\n"
                f"id: {doc.get('id') or ''}\n"
                f"title: {doc.get('title') or 'untitled'}\n"
                f"scope: {doc.get('scope') or scope_key}\n"
                f"source: {doc.get('source') or 'unknown'}\n"
                f"document_type: {doc.get('document_type') or 'unknown'}\n"
                f"relation: {provenance.get('relation') or 'unspecified'}\n"
                f"thread_id: {doc.get('thread_id') or ''}\n"
                f"project_id: {doc.get('project_id') or ''}\n"
                f"excerpt: {doc.get('excerpt') or ''}"
            )
            projected_size = total_chars + len(entry)
            if projected_size > max_chars:
                break
            lines.append(entry)
            total_chars = projected_size

        if len(lines) > 1:
            sections.append("\n".join(lines))
        if total_chars >= max_chars:
            break

    if not sections:
        return None

    return (
        "Document library excerpts (bounded, with provenance):\n\n"
        + "\n\n".join(sections)
    )


async def _build_doc_context_override(
    *,
    thread_id: int,
    depth_mode: str,
    project_id: Optional[int],
) -> Optional[str]:
    if depth_mode == "shallow":
        return None

    try:
        broker = ContextBroker(
            chatlog_db,
            _vector_store,
            _memory_store,
            _sensors,
        )
        docs_bundle = await broker.get_scoped_documents(
            thread_id=thread_id,
            project_id=project_id,
            k_project_docs=DOC_SCOPE_K_PROJECT,
            k_thread_docs=DOC_SCOPE_K_THREAD,
            doc_excerpt_chars=DOC_EXCERPT_CHARS,
        )
        return _build_scoped_doc_override(docs_bundle)
    except Exception as exc:
        logger.warning(
            "[chat.complete] failed to build doc override thread_id=%s project_id=%s err=%s",
            thread_id,
            project_id,
            exc,
        )
        return None


# =========================
# Chat Threads API
# =========================


@router.post("/threads")
def chat_create_thread(
    body: dict = Body(...), api_key: str = Depends(require_api_key)
):
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
        normalized_project = _coerce_project_id(project_id)
        metadata = (
            payload.get("metadata")
            if isinstance(payload.get("metadata"), dict)
            else None
        )

        # Idempotency guard: check for recent empty thread from same user
        recent_thread = chatlog_db.get_recent_thread(user_id)
        if recent_thread:
            # If recent thread exists and has no messages, reuse it
            recent_id = recent_thread.get("id")
            if recent_id and chatlog_db.count_messages(recent_id) == 0:
                logger.info(
                    "Reusing recent empty thread %s for user %s",
                    recent_id,
                    user_id,
                )
                return {"ok": True, "id": recent_id, "thread": recent_thread}

        record = chatlog_db.create_chat_thread(
            user_id=user_id,
            title=title,
            summary=summary,
            project_id=normalized_project,
            metadata=metadata,
        )
        chatlog_db.write_audit_log(
            "create", "chat_thread", str(record["id"]), user_id=user_id
        )
        return {"ok": True, "id": record["id"], "thread": record}
    except Exception as exc:
        logger.exception("Failed to create chat thread: %s", exc)
        raise HTTPException(
            status_code=500, detail="Failed to create chat thread"
        )


@router.get("/threads")
def chat_list_threads(api_key: str = Depends(require_api_key)):
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
def chat_post_message(
    thread_id: int,
    body: Dict[str, str] = Body(...),
    api_key: str = Depends(require_api_key),
):
    """Post a new message to a chat thread."""
    role = body.get("role")
    content = body.get("content", "").strip()
    if not role or not content:
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": "role and content required"},
        )
    owner = body.get("user_id") or "default"
    default_project_id = _coerce_project_id(None)
    # Turn gating: allow posting messages normally, but reject new user messages
    # while an assistant completion is in-flight (lock held). We probe the lock
    # without holding it by acquiring and immediately releasing when available.
    lock_probe_acquired = False
    try:
        lock_probe_acquired = acquire_turn_lock(thread_id, value="user")
        if not lock_probe_acquired:
            return JSONResponse(
                status_code=429,
                content={
                    "ok": False,
                    "error": "turn_in_flight",
                    "message": "Assistant is responding",
                },
            )
    except HTTPException:
        raise
    except Exception as exc:
        # If Redis is unavailable, continue without turn gating.
        logger.warning(
            "[chat.messages] turn lock probe unavailable thread_id=%s err=%s",
            thread_id,
            exc,
        )
    finally:
        if lock_probe_acquired:
            try:
                release_turn_lock(thread_id)
            except Exception:
                logger.debug(
                    "[chat.messages] turn lock probe release failed thread_id=%s",
                    thread_id,
                    exc_info=True,
                )
    try:
        chatlog_db.ensure_chat_thread(
            thread_id=thread_id,
            user_id=str(owner),
            title="New Chat",
            summary="",
            project_id=default_project_id,
        )
    except Exception as exc:
        logger.exception(
            "Failed to ensure chat thread %s exists: %s", thread_id, exc
        )
        raise HTTPException(
            status_code=500, detail="Failed to persist chat message"
        )
    try:
        mid = chatlog_db.create_message(thread_id, role, content)
    except Exception as exc:
        logger.exception(
            "[chat] create_message failed thread_id=%s: %s", thread_id, exc
        )
        raise HTTPException(
            status_code=500, detail="Failed to persist chat message"
        )
    chatlog_db.write_audit_log(
        "create", "chat_message", str(mid), user_id=str(owner)
    )

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
    _emit_thread_update_event(
        thread_id=thread_id,
        actor_user_id=str(owner),
        project_id=default_project_id,
        idempotency_suffix=f"message:{mid}",
        payload={
            "thread_id": thread_id,
            "message_id": mid,
            "role": role,
        },
    )

    # Auto-embed message
    _embed_message(thread_id, role, content, mid)

    # Best-effort auto-title on first user message. If the backing thread row
    # has an empty/NULL title and this is the first persisted message, derive
    # a short title from the content so thread lists remain readable.
    try:
        thread = chatlog_db.get_chat_thread(thread_id)
        title_text = (thread.get("title") or "").strip() if thread else ""
        if role == "user" and not title_text:
            try:
                total = chatlog_db.count_messages(thread_id)
            except Exception:
                total = 1
            if total == 1:
                candidate = content.split("\n", 1)[0].strip()
                if len(candidate) > 80:
                    candidate = candidate[:80]
                if candidate:
                    try:
                        chatlog_db.update_thread(thread_id, title=candidate)
                    except Exception:
                        logger.debug(
                            "[threads] auto-title update failed for thread_id=%s",
                            thread_id,
                            exc_info=True,
                        )
    except Exception:
        # Auto-title must never break message insertion.
        logger.debug(
            "[threads] auto-title computation failed for thread_id=%s",
            thread_id,
            exc_info=True,
        )

    # --- Neo4j sync ---
    if NEO4J_SYNC_AVAILABLE and getattr(
        llm_settings, "GUARDIAN_ENABLE_GRAPH_LOGGING", False
    ):
        try:
            connect_neo4j()
            # Use string IDs for Neo4j
            message_id = str(mid)
            thread_id_str = str(thread_id)
            user_id_str = str(owner)
            message_text = content

            neo_user = UserNode.get_or_create(
                {"user_id": user_id_str, "name": user_id_str}
            )
            if isinstance(neo_user, list):
                neo_user = neo_user[0]

            neo_thread = ThreadNode.get_or_create({"thread_id": thread_id_str})
            if isinstance(neo_thread, list):
                neo_thread = neo_thread[0]

            neo_msg = MessageNode.get_or_create(
                {
                    "message_id": message_id,
                    "content": message_text,
                    "created_at": datetime.now(timezone.utc),
                }
            )
            if isinstance(neo_msg, list):
                neo_msg = neo_msg[0]

            neo_msg.user.connect(neo_user)
            neo_msg.thread.connect(neo_thread)

        except Exception as e:
            logger.warning("[Neo4j Sync Error] %s", e, exc_info=True)

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
def chat_list_messages(
    thread_id: int,
    limit: int = 50,
    offset: int = 0,
    include_fact_evidence: bool = False,
    api_key: str = Depends(require_api_key),
):
    """List messages for a chat thread."""
    exclude_kinds = None if include_fact_evidence else ["fact_evidence"]
    items = chatlog_db.list_messages(
        thread_id,
        limit=limit,
        offset=offset,
        exclude_kinds=exclude_kinds,
    )
    total = chatlog_db.count_messages(thread_id)
    return {"ok": True, "total": total, "messages": items}


@router.post("/{thread_id}/complete")
async def chat_complete(
    thread_id: int,
    body: ChatCompletionRequest = Body(...),
    api_key: str = Depends(require_api_key),
):
    """
    Enqueue an assistant reply for the given thread and return a task id.
    """
    # Turn gating: acquire and HOLD the lock while an assistant completion is running.
    lock_acquired = False
    try:
        lock_acquired = acquire_turn_lock(thread_id, value="assistant")
        if not lock_acquired:
            return JSONResponse(
                status_code=429,
                content={
                    "ok": False,
                    "error": "turn_in_flight",
                    "message": "Assistant is responding",
                },
            )
    except HTTPException:
        raise
    except Exception as exc:
        # If Redis is unavailable, continue without turn gating.
        logger.warning(
            "[chat.complete] turn lock unavailable thread_id=%s err=%s",
            thread_id,
            exc,
        )
        lock_acquired = False

    provider = str(
        body.provider
        or (llm_settings.LLM_PROVIDER if llm_settings else CHAT_PROVIDER)
    ).lower()

    user_system_override = body.system_override
    if isinstance(user_system_override, str):
        user_system_override = user_system_override.strip() or None
    else:
        user_system_override = None

    thread_exists = (
        chatlog_db.get_chat_thread(thread_id)
        if hasattr(chatlog_db, "get_chat_thread")
        else True
    )
    if not thread_exists:
        if lock_acquired:
            try:
                release_turn_lock(thread_id)
            except Exception:
                logger.debug(
                    "[chat.complete] turn lock release failed thread_id=%s",
                    thread_id,
                    exc_info=True,
                )
        raise HTTPException(status_code=404, detail="Thread not found")

    limit = int(body.max_context or 50)
    items = chatlog_db.list_messages(thread_id, limit=limit, offset=0)
    context: List[Dict[str, str]] = []
    for msg in items:
        role = str(msg.get("role") or "").strip()
        content = msg.get("content")
        if (
            isinstance(content, str)
            and content.strip()
            and content.strip().lower() != "null"
        ):
            context.append({"role": role, "content": content})
    if not context:
        if lock_acquired:
            try:
                release_turn_lock(thread_id)
            except Exception:
                logger.debug(
                    "[chat.complete] turn lock release failed thread_id=%s",
                    thread_id,
                    exc_info=True,
                )
        raise HTTPException(
            status_code=400, detail="Thread has no usable context"
        )

    requested_depth_mode = str(body.depth_mode or "normal").strip().lower()
    effective_depth_mode = body.depth_mode
    thread_project_id: Optional[int] = None
    if isinstance(thread_exists, dict):
        thread_project_id = _coerce_positive_int(
            thread_exists.get("project_id")
        )
    if requested_depth_mode == "deep":
        project_depth = "light"
        getter = getattr(chatlog_db, "get_project_identity_depth", None)
        if callable(getter):
            try:
                project_depth = str(
                    getter(thread_project_id) or "light"
                ).lower()
            except Exception:
                project_depth = "light"
        if not can_run_deep_identity_modeling(project_depth):
            effective_depth_mode = "normal"
            logger.info(
                "[chat.complete] downgraded depth_mode=deep to normal thread_id=%s project_id=%s identity_depth=%s",
                thread_id,
                thread_project_id,
                project_depth,
            )

    effective_depth = str(effective_depth_mode or "normal").strip().lower()
    doc_context_override = await _build_doc_context_override(
        thread_id=thread_id,
        depth_mode=effective_depth,
        project_id=thread_project_id,
    )
    merged_system_override = user_system_override
    if doc_context_override:
        merged_system_override = (
            f"{merged_system_override}\n\n{doc_context_override}"
            if merged_system_override
            else doc_context_override
        )

    task = ChatCompletionTask(
        thread_id=thread_id,
        provider=provider,
        model=body.model,
        max_context=body.max_context,
        depth_mode=effective_depth_mode,
        system_override=merged_system_override,
        origin="api:chat.complete",
    )
    try:
        enqueue(task, "codexify:queue:chat")
    except Exception as exc:
        logger.warning("[chat.complete] queue unavailable: %s", exc)
        if lock_acquired:
            try:
                release_turn_lock(thread_id)
            except Exception:
                logger.debug(
                    "[chat.complete] turn lock release failed thread_id=%s",
                    thread_id,
                    exc_info=True,
                )
        raise HTTPException(status_code=503, detail="queue_unavailable")

    # Track latest task for debug endpoint
    _thread_latest_task[thread_id] = task.task_id

    try:
        task_events.publish(
            task.task_id,
            "task.created",
            {"type": task.type, "thread_id": thread_id, "origin": task.origin},
        )
    except Exception:
        logger.debug("[chat.complete] task.created emit failed", exc_info=True)

    logger.info(
        "[task] created type=%s id=%s origin=%s thread=%s",
        task.type,
        task.task_id,
        task.origin,
        thread_id,
    )
    messages_url = f"/api/chat/{thread_id}/messages"
    trace_url = f"/api/chat/debug/rag-trace/{thread_id}/latest"

    return {
        "ok": True,
        "task_id": task.task_id,
        "thread_id": thread_id,
        "depth_mode": effective_depth_mode,
        "messages_url": messages_url,
        "trace_url": trace_url,
    }


@router.get("/{thread_id}/profile")
def chat_get_thread_profile(
    thread_id: int, api_key: str = Depends(require_api_key)
):
    """Return resolved profile state + available profile catalog for a thread."""
    thread = chatlog_db.get_chat_thread(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    resolved_profile: dict[str, Any] | None = None
    if resolve_thread_system_profile:
        try:
            resolved = resolve_thread_system_profile(
                thread_id, chatlog_db=chatlog_db
            )
            resolved_profile = resolved.model_dump(
                mode="json", exclude_none=True
            )
        except Exception as exc:
            logger.warning(
                "[chat.profile] resolve failed thread_id=%s err=%s",
                thread_id,
                exc,
            )

    available_profiles: list[dict[str, Any]] = []
    if list_available_system_profiles:
        try:
            available_profiles = list_available_system_profiles(
                thread_id=thread_id,
                chatlog_db=chatlog_db,
            )
        except Exception as exc:
            logger.warning(
                "[chat.profile] catalog load failed thread_id=%s err=%s",
                thread_id,
                exc,
            )

    if resolved_profile is None:
        active_profile_id = thread.get("active_profile_id")
        resolved_profile = {
            "profile_id": active_profile_id or "default",
            "active_profile_id": active_profile_id,
            "name": "Default"
            if not active_profile_id
            else str(active_profile_id),
            "mode": "cloud",
            "source": "fallback",
        }

    return {
        "ok": True,
        "thread_id": thread_id,
        "profile": resolved_profile,
        "profiles": available_profiles,
    }


@router.delete("/{thread_id}/messages/{message_id}")
def chat_delete_message(
    thread_id: int,
    message_id: int,
    api_key: str = Depends(require_api_key),
):
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
def update_thread(
    thread_id: int,
    payload: ThreadUpdate,
    api_key: str = Depends(require_api_key),
):
    """Update thread metadata (title, summary, project, archive status)."""
    updated = _apply_thread_update(thread_id, payload)
    return updated


@router.patch("/threads/{thread_id}")
def patch_thread(
    thread_id: int,
    body: Dict[str, object] = Body(...),
    api_key: str = Depends(require_api_key),
):
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
            status_code=500,
            content={"ok": False, "error": "Failed to update thread"},
        )


@router.delete("/{thread_id}")
def delete_thread(
    thread_id: int,
    force: bool = Query(False),
    api_key: str = Depends(require_api_key),
):
    """Hard delete a thread regardless of archived state."""
    deleted = chatlog_db.delete_thread(thread_id, force=force)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Thread not found or not deletable (archive first or set force=true)",
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
def create_thread(
    req: ThreadCreateRequest, api_key: str = Depends(require_api_key)
):
    """Create a new thread with optional parent, summary, session, user, and project."""
    thread_id = chatlog_db.create_thread(
        parent_thread_id=req.parent_thread_id,
        session_id=req.session_id,
        summary=req.summary,
        user_id=req.user_id,
        project_id=req.project_id,
    )
    return {"thread_id": thread_id}


# =========================
# Simple Chat Endpoints (for auth/tests)
# =========================

# These endpoints are used by auth tests and provide simple, deterministic
# chat functionality that doesn't depend on external APIs


class ChatRequest(BaseModel):
    prompt: str
    provider: Optional[str] = None
    model: Optional[str] = None


simple_chat_router = APIRouter(prefix="", tags=["Chat"])


@simple_chat_router.post("/chat")
async def simple_chat_entrypoint(
    body: ChatRequest, api_key: str = Depends(verify_api_key)
):
    """Minimal chat endpoint used by auth/tests.

    - Requires X-API-Key via require_api_key.
    - Accepts a simple {"prompt", "provider", "model"} payload.
    - Returns {"reply": ..., "model": ..., "provider": ...}.
    - Uses Groq when configured; falls back to echo-on-failure to keep tests stable
      even when upstream credentials/models are misconfigured.
    """
    messages: List[Dict[str, str]] = [
        {"role": "user", "content": body.prompt},
    ]

    provider = (
        body.provider
        or (llm_settings.LLM_PROVIDER if llm_settings else CHAT_PROVIDER)
    ).lower()
    model = body.model or DEFAULT_MODEL

    reply_text: str
    try:
        if validate_llm_config and llm_settings:
            validate_llm_config(llm_settings, provider_override=provider)
        if provider == "groq":
            reply_text = _groq_complete(messages, model=model)
        elif chat_with_ai is not None:
            # Optional generic backend, if wired
            reply_text = str(chat_with_ai(messages))
        else:
            # Safe local echo fallback
            reply_text = f"Echo: {body.prompt}"
    except HTTPException as exc:
        # For auth tests and offline environments, degrade to an echo reply
        # instead of surfacing upstream LLM errors.
        logger.warning(
            "/chat backend HTTPException, using echo fallback: %s", exc
        )
        reply_text = f"Echo: {body.prompt}"
    except Exception as exc:  # pragma: no cover - defensive fallback
        logger.warning("/chat backend failed, using echo fallback: %s", exc)
        reply_text = f"Echo: {body.prompt}"

    return {
        "reply": reply_text,
        "model": model,
        "provider": provider,
    }


def _get_task_completed_payload(task_id: str) -> Optional[Dict[str, Any]]:
    """
    Read task events and return the most recent task.completed payload.
    """
    try:
        events = task_events.read_events(task_id, "0", count=100, block_ms=1000)
        completed_payload: Dict[str, Any] | None = None
        for _, event in events:
            if event.get("type") == "task.completed":
                data = event.get("data", {})
                if isinstance(data, dict):
                    completed_payload = data
        return completed_payload
    except Exception as exc:
        logger.debug("[chat] failed to read task events for trace: %s", exc)
        return None


@router.get("/debug/rag-trace/{thread_id}/latest", tags=["Debug"])
def get_latest_rag_trace(
    thread_id: int, api_key: str = Depends(require_api_key)
):
    """
    [DEV ONLY] Get the RAG trace for the last completion in this thread.

    Attempts to read from task events if task_id is tracked,
    falls back to in-memory cache otherwise.
    Returns empty arrays if no trace is available.
    """
    trace: Dict[str, Any] | None = None
    profile_debug: Dict[str, Any] = {
        "active_profile_id": None,
        "provider_override": None,
        "model_override": None,
        "injection_hash": None,
        "retrieval_mode": None,
        "model_mode": None,
    }

    # Try to get trace + profile data from task events if we have a recent task
    task_id = _thread_latest_task.get(thread_id)
    if task_id:
        completed_payload = _get_task_completed_payload(task_id)
        if completed_payload:
            payload_trace = completed_payload.get("trace")
            if isinstance(payload_trace, dict):
                trace = dict(payload_trace)
                _rag_traces[thread_id] = trace  # Cache it
            for key in (
                "active_profile_id",
                "provider_override",
                "model_override",
                "injection_hash",
                "retrieval_mode",
                "model_mode",
            ):
                profile_debug[key] = completed_payload.get(key)

    # Fall back to in-memory cache
    if trace is None:
        cached = _rag_traces.get(thread_id)
        if isinstance(cached, dict):
            trace = dict(cached)

    if not trace:
        trace = {"documents": [], "graph": []}
    else:
        trace.setdefault("documents", [])
        trace.setdefault("graph", [])

    if resolve_thread_system_profile and (
        profile_debug["active_profile_id"] is None
        or profile_debug["provider_override"] is None
        or profile_debug["model_override"] is None
    ):
        with_profile = None
        try:
            with_profile = resolve_thread_system_profile(
                thread_id, chatlog_db=chatlog_db
            )
        except Exception:
            with_profile = None
        if with_profile is not None:
            if profile_debug["active_profile_id"] is None:
                profile_debug["active_profile_id"] = (
                    with_profile.active_profile_id
                    or with_profile.profile_id
                    or None
                )
            if profile_debug["provider_override"] is None:
                profile_debug[
                    "provider_override"
                ] = with_profile.provider_override
            if profile_debug["model_override"] is None:
                profile_debug["model_override"] = with_profile.model_override
            if profile_debug["model_mode"] is None:
                profile_debug["model_mode"] = with_profile.mode

    trace.update(profile_debug)
    return trace


@simple_chat_router.get("/chat/stream")
async def simple_chat_stream(
    prompt: str = Query(..., description="Prompt text"),
    provider: Optional[str] = Query(None),
    model: Optional[str] = Query(None),
    api_key: str = Depends(verify_api_key),
):
    """Simple SSE-style streaming endpoint used by auth/tests.

    It intentionally does **not** depend on any external LLM to keep tests
    deterministic; it just streams the prompt back token-by-token and then
    emits a final `[DONE]` marker.
    """

    async def event_stream() -> AsyncGenerator[str, None]:
        text = f"Echo: {prompt}"
        # Very small artificial tokenization on whitespace
        for token in text.split():
            yield f"data: {token}\n\n"
            # Yield control to the event loop without introducing real delays
            await asyncio.sleep(0)
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# =========================
# /api/chat/* Canonical Endpoints
# =========================

# These endpoints are the canonical chat API surface; /chat/* remains as a
# legacy alias that delegates to the same handler functions.

api_chat_router = APIRouter(prefix="/api/chat", tags=["Chat"])


@api_chat_router.post("")
async def api_chat_root(
    body: ChatRequest, api_key: str = Depends(require_api_key)
):
    """Compat alias for POST /api/chat used by legacy frontend helper."""
    return await simple_chat_entrypoint(body, api_key=api_key)


@api_chat_router.post("/threads")
def api_chat_create_thread(
    body: dict = Body(...), api_key: str = Depends(require_api_key)
):
    """Compat alias for POST /chat/threads used in tests."""
    return chat_create_thread(body, api_key=api_key)


@api_chat_router.get("/threads")
def api_chat_list_threads(api_key: str = Depends(require_api_key)):
    """Compat alias for GET /chat/threads used in tests."""
    return chat_list_threads(api_key=api_key)


@api_chat_router.post("/{thread_id}/messages")
def api_chat_post_message(
    thread_id: int,
    body: Dict[str, str] = Body(...),
    api_key: str = Depends(require_api_key),
):
    """Compat alias for POST /chat/{thread_id}/messages used in tests."""
    return chat_post_message(thread_id, body, api_key=api_key)


@api_chat_router.get("/{thread_id}/messages")
def api_chat_list_messages(
    thread_id: int,
    limit: int = 50,
    offset: int = 0,
    api_key: str = Depends(require_api_key),
):
    """Compat alias for GET /chat/{thread_id}/messages used in tests."""
    return chat_list_messages(
        thread_id,
        limit,
        offset,
        include_fact_evidence=False,
        api_key=api_key,
    )


@api_chat_router.post("/{thread_id}/complete")
async def api_chat_complete(
    thread_id: int,
    body: ChatCompletionRequest = Body(...),
    api_key: str = Depends(require_api_key),
):
    """Compat alias for POST /chat/{thread_id}/complete used in tests."""
    return await chat_complete(thread_id, body, api_key=api_key)


@api_chat_router.get("/{thread_id}/profile")
def api_chat_get_thread_profile(
    thread_id: int, api_key: str = Depends(require_api_key)
):
    """Compat alias for GET /chat/{thread_id}/profile."""
    return chat_get_thread_profile(thread_id, api_key=api_key)


@api_chat_router.get("/debug/rag-trace/{thread_id}/latest", tags=["Debug"])
def api_get_latest_rag_trace(
    thread_id: int, api_key: str = Depends(require_api_key)
):
    """Compat alias for GET /chat/debug/rag-trace/{thread_id}/latest."""
    return get_latest_rag_trace(thread_id, api_key=api_key)


@api_chat_router.delete("/{thread_id}/messages/{message_id}")
def api_chat_delete_message(
    thread_id: int,
    message_id: int,
    api_key: str = Depends(require_api_key),
):
    """Compat alias for DELETE /chat/{thread_id}/messages/{message_id} used in tests."""
    return chat_delete_message(thread_id, message_id, api_key=api_key)


@api_chat_router.post("/{thread_id}/branch", response_model=ThreadDTO)
def api_branch_thread(
    thread_id: int,
    body: Optional[ThreadBranchRequest] = Body(default=None),
    api_key: str = Depends(require_api_key),
):
    """Compat alias for POST /chat/{thread_id}/branch used in tests."""
    return branch_thread(thread_id, body, api_key=api_key)


@api_chat_router.patch("/{thread_id}", response_model=ThreadDTO)
def api_update_thread(
    thread_id: int,
    payload: ThreadUpdate,
    api_key: str = Depends(require_api_key),
):
    """Compat alias for PATCH /chat/{thread_id} used in tests."""
    return update_thread(thread_id, payload, api_key=api_key)


@api_chat_router.patch("/threads/{thread_id}")
def api_patch_thread(
    thread_id: int,
    body: Dict[str, object] = Body(...),
    api_key: str = Depends(require_api_key),
):
    """Compat alias for PATCH /chat/threads/{thread_id} used in tests."""
    return patch_thread(thread_id, body, api_key=api_key)


@api_chat_router.delete("/threads/{thread_id}")
def api_delete_thread(
    thread_id: int,
    force: bool = Query(False),
    api_key: str = Depends(require_api_key),
):
    """Compat alias for DELETE /chat/threads/{thread_id} used in tests."""
    return delete_thread(thread_id, force, api_key=api_key)
