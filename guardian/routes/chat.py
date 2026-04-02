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
import json
import logging
import os
import time
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional

from fastapi import (
    APIRouter,
    Body,
    Depends,
    Header,
    HTTPException,
    Query,
    Request,
)
from fastapi.responses import JSONResponse
from pydantic import (
    BaseModel,
    ConfigDict,
    StrictStr,
    ValidationError,
    field_validator,
)
from starlette.responses import StreamingResponse

from guardian.cognition.identity_policy import can_run_deep_identity_modeling
from guardian.core.chat_completion_service import (
    DEBUG_LATEST_COMPLETION_TASK_ID_METADATA_KEY,
    DEBUG_LATEST_RAG_TRACE_METADATA_KEY,
    DEBUG_RAG_TRACE_CANDIDATE_METADATA_KEY,
    _merge_thread_metadata_patch,
    resolve_thread_completion_settings,
)
from guardian.core.event_graph import get_event_writer
from guardian.depth import (
    DepthDowngradeReason,
    DepthMode,
    ProjectDepthState,
    classify_project_identity_depth,
    normalize_project_identity_depth,
    normalize_requested_depth_raw,
    project_requested_depth_mode,
    resolve_depth,
)
from guardian.protocol_tokens import AcceptanceStatus, ErrorCode, TaskEventType
from guardian.queue import task_events
from guardian.queue.redis_queue import (
    QueueEnqueueError,
    RedisOperationTimeout,
    enqueue,
    enqueue_chat_embed,
    run_with_redis_timeout,
)
from guardian.queue.turn_lock import (
    TurnLockEnvelope,
    acquire_turn_lock,
    build_turn_lock_envelope,
    clear_turn_lock,
    get_turn_lock,
    release_turn_lock,
    turn_lock_is_stale,
)
from guardian.routes.health import _classify_chat_worker_heartbeat
from guardian.tasks.types import ChatCompletionTask
from guardian.voice.audio_assets import list_message_audio_assets

logger = logging.getLogger(__name__)
COMPLETION_SERVICE_UNAVAILABLE_MESSAGE = (
    "Completion service unavailable — check Docker/Redis."
)
COMPLETION_ACCEPTANCE_STATUS_ACCEPTED = AcceptanceStatus.ACCEPTED.value
COMPLETION_ACCEPTANCE_STATUS_ACCEPTED_DEGRADED = (
    AcceptanceStatus.ACCEPTED_DEGRADED.value
)
COMPLETION_ACCEPTANCE_WARNING_TASK_CREATED_PUBLISH_FAILED = (
    "task_created_event_publish_failed"
)
COMPLETION_ACCEPTANCE_WARNING_TASK_CREATED_MISSING_EVENT_ID = (
    "task_created_event_missing_event_id"
)
TASK_EVENT_TYPE_TASK_CREATED = TaskEventType.TASK_CREATED.value
CHAT_COMPLETE_ENQUEUE_ERROR_CODE = ErrorCode.CHAT_COMPLETE_ENQUEUE_FAILED.value
CHAT_COMPLETE_TASK_CREATED_EVENT_ERROR_CODE = (
    ErrorCode.CHAT_COMPLETE_TASK_CREATED_EVENT_FAILED.value
)
CHAT_WORKER_HEARTBEAT_KEY = os.getenv(
    "CHAT_WORKER_HEARTBEAT_KEY", "codexify:worker:chat:heartbeat"
)


def _completion_service_unavailable(reason: str) -> HTTPException:
    return HTTPException(
        status_code=503,
        detail={
            "error": "completion_service_unavailable",
            "reason": reason,
            "message": COMPLETION_SERVICE_UNAVAILABLE_MESSAGE,
        },
    )


def _run_completion_redis_op(fn, *, reason: str, log_message: str):
    try:
        return run_with_redis_timeout(fn)
    except (RedisOperationTimeout, Exception) as exc:
        logger.warning(log_message, exc)
        raise _completion_service_unavailable(reason)


def _best_effort_release_turn_lock(
    thread_id: int,
    owner: str | TurnLockEnvelope,
    *,
    log_message: str,
) -> None:
    try:
        run_with_redis_timeout(lambda: release_turn_lock(thread_id, owner))
    except TypeError:
        raise
    except (RedisOperationTimeout, Exception):
        logger.debug(log_message, exc_info=True)


def _task_terminal_event(task_id: str) -> dict[str, Any]:
    """Return terminal-state evidence for a task event stream."""

    return task_events.describe_terminal_state(task_id)


def _chat_worker_heartbeat_age_seconds() -> float | None:
    evidence = _chat_worker_heartbeat_evidence()
    age_seconds = evidence.get("age_seconds")
    return float(age_seconds) if isinstance(age_seconds, (int, float)) else None


def _chat_worker_heartbeat_evidence() -> dict[str, Any]:
    """Inspect the chat worker heartbeat key and classify freshness."""

    evidence: dict[str, Any] = {
        "key": CHAT_WORKER_HEARTBEAT_KEY,
        "state": "unknown",
        "age_seconds": None,
        "detected": False,
        "reason": "unknown",
        "error": None,
    }
    try:
        from guardian.queue.redis_queue import get_redis_client

        client = run_with_redis_timeout(get_redis_client)
        raw_heartbeat = run_with_redis_timeout(
            lambda: client.get(CHAT_WORKER_HEARTBEAT_KEY)
        )
        if not raw_heartbeat:
            evidence["state"] = "missing"
            evidence["reason"] = "heartbeat_missing"
            return evidence

        evidence["detected"] = True
        heartbeat_payload: dict[str, Any] = {}
        try:
            if isinstance(raw_heartbeat, (bytes, bytearray)):
                heartbeat_payload = json.loads(raw_heartbeat.decode("utf-8"))
            else:
                heartbeat_payload = json.loads(str(raw_heartbeat))
        except Exception:
            evidence["reason"] = "heartbeat_parse_failed"
            return evidence

        ts = heartbeat_payload.get("ts")
        if not isinstance(ts, (int, float)):
            evidence["reason"] = "heartbeat_timestamp_missing"
            return evidence

        age_seconds = max(0.0, round(time.time() - float(ts), 3))
        evidence["age_seconds"] = age_seconds
        evidence["state"] = _classify_chat_worker_heartbeat(True, age_seconds)
        evidence["reason"] = "ok"
        return evidence
    except (RedisOperationTimeout, Exception) as exc:
        evidence["reason"] = "redis_unavailable"
        evidence["error"] = f"{type(exc).__name__}: {exc}"
        return evidence


def _turn_lock_payload(
    lock: TurnLockEnvelope | None,
    *,
    thread_id: int,
    owner: str,
    turn_id: str,
) -> dict[str, Any]:
    if isinstance(lock, TurnLockEnvelope):
        return asdict(lock)
    return asdict(
        build_turn_lock_envelope(
            thread_id,
            owner,
            turn_id=turn_id,
            source="api:chat.complete",
        )
    )


def _request_id_from_request(request: Request | None) -> str | None:
    if request is None:
        return None
    state = getattr(request, "state", None)
    request_id = getattr(state, "request_id", None)
    if request_id is None:
        return None
    normalized = str(request_id).strip()
    return normalized or None


def _publish_completion_start_event(
    *,
    task: ChatCompletionTask,
    thread_id: int,
    turn_id: str,
) -> dict[str, Any]:
    """Publish the lifecycle-start breadcrumb and normalize failure details."""

    payload = {
        "type": task.type,
        "thread_id": thread_id,
        "origin": task.origin,
        "turn_id": turn_id,
    }
    try:
        publish_result = task_events.publish_with_visibility(
            task.task_id,
            TASK_EVENT_TYPE_TASK_CREATED,
            payload,
        )
    except Exception as exc:
        visibility_scope = task_events.classify_event_visibility(
            TASK_EVENT_TYPE_TASK_CREATED
        )
        return {
            "ok": False,
            "task_id": task.task_id,
            "event_type": TASK_EVENT_TYPE_TASK_CREATED,
            "visibility_scope": visibility_scope,
            "terminal_visibility": visibility_scope == "terminal",
            "execution_continued": True,
            "event_id": None,
            "error_code": CHAT_COMPLETE_TASK_CREATED_EVENT_ERROR_CODE,
            "failure_class": exc.__class__.__name__,
            "error": str(exc),
            "exception": exc,
        }

    if isinstance(publish_result, dict):
        if not publish_result.get("ok"):
            raise task_events.TaskEventPublishError.from_publish_result(
                publish_result
            ) from (
                publish_result.get("exception")
                if isinstance(publish_result.get("exception"), BaseException)
                else None
            )
        return publish_result

    visibility_scope = task_events.classify_event_visibility(
        TASK_EVENT_TYPE_TASK_CREATED
    )
    return {
        "ok": False,
        "task_id": task.task_id,
        "event_type": TASK_EVENT_TYPE_TASK_CREATED,
        "visibility_scope": visibility_scope,
        "terminal_visibility": visibility_scope == "terminal",
        "execution_continued": True,
        "event_id": None,
        "error_code": CHAT_COMPLETE_TASK_CREATED_EVENT_ERROR_CODE,
        "failure_class": "InvalidPublishResult",
        "error": (
            "unexpected result type: " f"{type(publish_result).__name__}"
        ),
        "exception": TypeError(
            f"unexpected result type: {type(publish_result).__name__}"
        ),
    }
    raise task_events.TaskEventPublishError.from_publish_result(failure) from (
        failure["exception"]
        if isinstance(failure.get("exception"), BaseException)
        else None
    )


def _completion_acceptance_outcome(
    publish_result: dict[str, Any],
) -> tuple[str, list[str]]:
    """Translate start-event visibility into a narrow acceptance status."""

    if not publish_result.get("ok"):
        return (
            COMPLETION_ACCEPTANCE_STATUS_ACCEPTED_DEGRADED,
            [COMPLETION_ACCEPTANCE_WARNING_TASK_CREATED_PUBLISH_FAILED],
        )

    event_id = str(publish_result.get("event_id") or "").strip()
    if not event_id:
        return (
            COMPLETION_ACCEPTANCE_STATUS_ACCEPTED_DEGRADED,
            [COMPLETION_ACCEPTANCE_WARNING_TASK_CREATED_MISSING_EVENT_ID],
        )

    return COMPLETION_ACCEPTANCE_STATUS_ACCEPTED, []


def _recover_orphaned_turn_lock(thread_id: int) -> bool:
    stale_lock = _run_completion_redis_op(
        lambda: get_turn_lock(thread_id),
        reason="turn_lock_unavailable",
        log_message="[chat.complete] stale turn lock probe unavailable: %s",
    )
    if stale_lock is None or not turn_lock_is_stale(stale_lock):
        return False

    terminal_evidence = _task_terminal_event(stale_lock.owner_task_id)
    terminal_state = str(
        terminal_evidence.get("state")
        if isinstance(terminal_evidence, dict)
        else "unknown"
    )
    heartbeat_evidence = _chat_worker_heartbeat_evidence()
    heartbeat_state = str(
        heartbeat_evidence.get("state")
        if isinstance(heartbeat_evidence, dict)
        else "unknown"
    )

    # Recovery rule:
    # - terminal task evidence is enough to clear the stale lock.
    # - otherwise, the task stream must be nonterminal and the worker heartbeat
    #   must be stale/dead/missing. We do not recover when either evidence
    #   source is unknown, and we never recover on lease age alone.
    recoverable = False
    recovery_reason = "unrecoverable_state"
    if terminal_state == "terminal":
        recoverable = True
        recovery_reason = "terminal_task_event"
    elif terminal_state == "nonterminal" and heartbeat_state in {
        "stale",
        "dead",
        "missing",
    }:
        recoverable = True
        recovery_reason = f"nonterminal_task_and_{heartbeat_state}_heartbeat"

    if not recoverable:
        logger.warning(
            "[chat.complete] stale turn lock recovery denied thread_id=%s owner_task_id=%s terminal_state=%s terminal_reason=%s worker_state=%s worker_reason=%s",
            thread_id,
            stale_lock.owner_task_id,
            terminal_state,
            terminal_evidence.get("reason")
            if isinstance(terminal_evidence, dict)
            else "unknown",
            heartbeat_state,
            heartbeat_evidence.get("reason")
            if isinstance(heartbeat_evidence, dict)
            else "unknown",
        )
        return False

    cleared = _run_completion_redis_op(
        lambda: clear_turn_lock(thread_id, expected=stale_lock),
        reason="turn_lock_unavailable",
        log_message="[chat.complete] stale turn lock clear unavailable: %s",
    )
    if cleared and hasattr(chatlog_db, "write_audit_log"):
        chatlog_db.write_audit_log(
            "recover_orphaned_turn_lock",
            "chat_thread",
            str(thread_id),
            user_id="system",
        )
        logger.info(
            "[chat.complete] stale turn lock recovered thread_id=%s owner_task_id=%s recovery_reason=%s terminal_state=%s worker_state=%s",
            thread_id,
            stale_lock.owner_task_id,
            recovery_reason,
            terminal_state,
            heartbeat_state,
        )
    return cleared


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
    from neomodel import db as neo4j_db

    from guardian.graph.connection import connect_neo4j
    from guardian.graph.models import MessageNode, ThreadNode, UserNode

    NEO4J_SYNC_AVAILABLE = True
except Exception:
    neo4j_db = None
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
    thread_config: Optional[Dict[str, Any]] = None

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


class ThreadConfigUpdate(BaseModel):
    providerId: StrictStr | None = None
    modelId: StrictStr | None = None
    inferenceMode: StrictStr | None = None
    retrievalSource: StrictStr | None = None
    personaId: StrictStr | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator(
        "providerId",
        "modelId",
        "inferenceMode",
        "retrievalSource",
        "personaId",
        mode="before",
    )
    @classmethod
    def _normalize_config_text(cls, value: Any) -> Any:
        if isinstance(value, str):
            cleaned = value.strip()
            if not cleaned:
                raise ValueError("value cannot be blank")
            return cleaned
        return value


class ThreadCreateRequest(BaseModel):
    parent_thread_id: int = None
    session_id: str = None
    summary: str = ""
    user_id: str = "default"
    project_id: str = None


class ChatMessageCreateRequest(BaseModel):
    thread_id: Optional[int] = None
    draft_tab_id: Optional[str] = None
    role: str
    content: str
    user_id: Optional[str] = "default"
    title: Optional[str] = None
    summary: Optional[str] = None
    project_id: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class ChatCompletionRequest(BaseModel):
    model: Optional[str] = None
    max_context: Optional[int] = 50
    provider: Optional[str] = None
    reasoning_mode: Optional[str] = None
    system_override: Optional[str] = None
    turn_id: Optional[str] = None
    source_mode: Optional[str] = "project"
    depth_mode: Optional[
        str
    ] = "deep"  # "shallow", "normal", "deep", "diagnostic"


# Helper functions
def _embed_message(thread_id: int, role: str, content: str, message_id: int):
    """Best-effort enqueue of a chat message embedding task."""
    if not _vector_store:
        return
    try:
        run_with_redis_timeout(
            lambda: enqueue_chat_embed(
                {
                    "thread_id": thread_id,
                    "role": role,
                    "content": content,
                    "message_id": message_id,
                }
            )
        )
    except NameError:
        logger.exception(
            "[chat] enqueue_chat_embed is unavailable; cannot enqueue message_id=%s",
            message_id,
        )
        raise
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


def _attach_message_audio_metadata(
    items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    assistant_message_ids = [
        _coerce_message_id(item.get("id"))
        for item in items
        if str(item.get("role") or "").strip().lower() == "assistant"
    ]
    normalized_ids = [
        message_id for message_id in assistant_message_ids if message_id
    ]
    if not normalized_ids:
        return items

    try:
        audio_assets = list_message_audio_assets(
            message_ids=normalized_ids,
            preferred_source="assistant_message_autogenerate",
        )
    except Exception:
        logger.warning(
            "[chat.messages] failed to load message audio assets",
            exc_info=True,
        )
        audio_assets = {}

    for item in items:
        if str(item.get("role") or "").strip().lower() != "assistant":
            continue
        message_id = _coerce_message_id(item.get("id"))
        if message_id is None:
            continue
        asset = audio_assets.get(message_id)
        if not asset:
            item["audio_status"] = "unavailable"
            item["audio_url"] = None
            item["audio_mime_type"] = None
            item["audio_duration_ms"] = None
            continue

        duration_seconds = asset.get("duration_seconds")
        try:
            audio_duration_ms = (
                int(float(duration_seconds) * 1000)
                if duration_seconds is not None
                else None
            )
        except (TypeError, ValueError):
            audio_duration_ms = None
        delivery_variants = (
            asset.get("delivery_variants_json")
            if isinstance(asset.get("delivery_variants_json"), dict)
            else {}
        )
        error = asset.get("error")
        if not error and isinstance(delivery_variants, dict):
            candidate = delivery_variants.get("error")
            if isinstance(candidate, dict):
                error = candidate

        audio_status = (
            str(asset.get("status") or "unavailable").strip() or "unavailable"
        )
        audio_url = (
            str(asset.get("stream_url") or asset.get("src_url") or "").strip()
            or None
        )
        if audio_status == "ready" and not audio_url:
            logger.warning(
                "[chat.messages] assistant_audio_inconsistent thread_id=%s message_id=%s status=ready audio_url_present=false",
                item.get("thread_id"),
                message_id,
            )
            audio_status = "unavailable"

        item["audio_status"] = audio_status
        item["audio_url"] = audio_url
        item["audio_mime_type"] = asset.get("mime_type")
        item["audio_duration_ms"] = audio_duration_ms
        logger.debug(
            "[chat.messages] assistant_audio thread_id=%s message_id=%s status=%s audio_url_present=%s mime_type=%s",
            item.get("thread_id"),
            message_id,
            item["audio_status"],
            bool(item["audio_url"]),
            item["audio_mime_type"],
        )
        if item["audio_status"] == "failed" and error:
            if isinstance(error, dict):
                item["audio_error"] = str(
                    error.get("message")
                    or error.get("code")
                    or "Audio unavailable"
                )
            else:
                item["audio_error"] = str(error)
        elif "audio_error" in item:
            item.pop("audio_error", None)
    return items


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


def _derive_thread_title_from_content(content: str) -> str:
    first_line = (content or "").strip().split("\n", 1)[0].strip()
    if not first_line:
        return "New Chat"
    if len(first_line) > 80:
        return first_line[:80]
    return first_line


def _graph_ingest_query_debug_enabled() -> bool:
    if not getattr(llm_settings, "GUARDIAN_ENABLE_GRAPH_LOGGING", False):
        return False
    raw_flag = os.getenv("GUARDIAN_ENABLE_GRAPH_INGEST_QUERY_DEBUG", "")
    return str(raw_flag).strip().lower() in {"1", "true", "yes", "on"}


def _execute_neo4j_ingest_cypher(
    query: str, params: Dict[str, Any]
) -> tuple[Any, Any]:
    if neo4j_db is None:
        return [], None
    if _graph_ingest_query_debug_enabled():
        logger.debug(
            "[chat.ingest.neo4j] cypher=%s param_keys=%s",
            query.strip(),
            sorted(params.keys()),
        )
    return neo4j_db.cypher_query(query, params)


def _sync_live_ingest_message_to_neo4j(
    *,
    message_id: str,
    thread_id: str,
    user_id: str,
    message_text: str,
    created_at: datetime,
) -> None:
    """
    Upsert the live-ingest graph nodes and relationships with a safe chained
    MERGE flow so the write path never emits disconnected same-scope MATCH
    patterns.
    """
    query = """
    MERGE (user:UserNode {user_id: $user_id})
    ON CREATE SET
        user.uuid = $user_uuid,
        user.name = $user_name,
        user.created_at = $user_created_at
    MERGE (thread:ThreadNode {thread_id: $thread_id})
    ON CREATE SET
        thread.uuid = $thread_uuid,
        thread.created_at = $thread_created_at
    MERGE (message:MessageNode {message_id: $message_id})
    ON CREATE SET
        message.uuid = $message_uuid,
        message.content = $message_content,
        message.created_at = $message_created_at
    WITH message, user, thread
    MERGE (message)-[:SENT_BY]->(user)
    MERGE (message)-[:PART_OF]->(thread)
    RETURN elementId(message) AS message_element_id
    """
    _execute_neo4j_ingest_cypher(
        query,
        {
            "user_id": user_id,
            "user_name": user_id,
            "user_uuid": uuid.uuid4().hex,
            "user_created_at": created_at,
            "thread_id": thread_id,
            "thread_uuid": uuid.uuid4().hex,
            "thread_created_at": created_at,
            "message_id": message_id,
            "message_uuid": uuid.uuid4().hex,
            "message_content": message_text,
            "message_created_at": created_at,
        },
    )


def _persist_message_to_thread(
    *,
    thread_id: int,
    role: str,
    content: str,
    owner: str,
    requested_project_id: Any = None,
) -> Dict[str, Any]:
    default_project_id = _coerce_project_id(requested_project_id)
    lock_probe_owner = "api:chat.messages:user_probe"
    lock_probe_acquired = False
    try:
        lock_probe_acquired = run_with_redis_timeout(
            lambda: acquire_turn_lock(thread_id, lock_probe_owner)
        )
        if not lock_probe_acquired:
            raise HTTPException(
                status_code=429,
                detail={
                    "ok": False,
                    "error": "turn_in_flight",
                    "message": "Assistant is responding",
                },
            )
    except HTTPException:
        raise
    except TypeError:
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
                run_with_redis_timeout(
                    lambda: release_turn_lock(thread_id, lock_probe_owner)
                )
            except TypeError:
                raise
            except (RedisOperationTimeout, Exception):
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

    project_for_event = default_project_id
    try:
        refreshed_thread = chatlog_db.get_chat_thread(thread_id)
        thread_project = (
            refreshed_thread.get("project_id")
            if isinstance(refreshed_thread, dict)
            else None
        )
        project_for_event = _coerce_project_id(thread_project)
    except Exception:
        project_for_event = default_project_id

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
        project_id=project_for_event,
        idempotency_suffix=f"message:{mid}",
        payload={
            "thread_id": thread_id,
            "message_id": mid,
            "role": role,
        },
    )

    _embed_message(thread_id, role, content, mid)

    # Best-effort auto-title on first user message.
    try:
        thread = chatlog_db.get_chat_thread(thread_id)
        title_text = (thread.get("title") or "").strip() if thread else ""
        if role == "user" and not title_text:
            try:
                total = chatlog_db.count_messages(thread_id)
            except Exception:
                total = 1
            if total == 1:
                candidate = _derive_thread_title_from_content(content)
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
            message_id = str(mid)
            thread_id_str = str(thread_id)
            user_id_str = str(owner)
            message_text = content
            created_at = datetime.now(timezone.utc)

            _sync_live_ingest_message_to_neo4j(
                message_id=message_id,
                thread_id=thread_id_str,
                user_id=user_id_str,
                message_text=message_text,
                created_at=created_at,
            )

        except Exception as e:
            logger.warning("[Neo4j Sync Error] %s", e, exc_info=True)

    return {
        "id": mid,
        "thread_id": thread_id,
        "role": role,
        "content": content,
    }


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

DOC_SCOPE_K_PROJECT = 4
DOC_SCOPE_K_THREAD = 4
DOC_EXCERPT_CHARS = 320
DOC_OVERRIDE_MAX_CHARS = 2600
DEFAULT_PROJECT_NAME = "General"
DEFAULT_PROJECT_DESCRIPTION = "Default bucket for unassigned threads"


def _ensure_default_project_id() -> Optional[int]:
    """
    Resolve a safe default project id for unscoped threads.

    Falls back to None if the default project cannot be ensured so thread
    creation can still proceed without violating foreign keys.
    """
    if not chatlog_db:
        return None
    ensure_default_project = getattr(chatlog_db, "ensure_default_project", None)
    if not callable(ensure_default_project):
        # Some DB backends (e.g., PostgresChatLogDB) may not implement this shim.
        return None
    try:
        pid = ensure_default_project()
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


def _thread_config_payload_value(
    payload: dict[str, Any], *keys: str
) -> str | None:
    for key in keys:
        raw = payload.get(key)
        if raw is None:
            continue
        text = str(raw).strip()
        if text:
            return text
    return None


def _thread_config_inference_mode(provider: str, model: str) -> str:
    try:
        from guardian.core.ai_router import resolve_local_reasoning_directive
    except Exception:
        resolve_local_reasoning_directive = None

    if provider != "local" or resolve_local_reasoning_directive is None:
        return "fast"
    if not llm_settings:
        return "fast"

    directive = resolve_local_reasoning_directive(model, settings=llm_settings)
    if directive.mode == "think":
        return "think"
    return "fast"


def _build_thread_config_snapshot(
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from guardian.core.provider_registry import (
        default_model_for_provider,
        normalize_model_id,
        normalize_provider,
    )

    payload = payload or {}
    raw_provider = _thread_config_payload_value(
        payload,
        "providerId",
        "provider_id",
        "provider",
    )
    default_provider = (
        getattr(llm_settings, "LLM_PROVIDER", None)
        if llm_settings
        else CHAT_PROVIDER
    )
    provider = normalize_provider(raw_provider or default_provider)

    raw_model = _thread_config_payload_value(
        payload,
        "modelId",
        "model_id",
        "model",
    )
    model = normalize_model_id(raw_model) if raw_model is not None else ""
    if not model:
        if llm_settings is not None:
            try:
                model = default_model_for_provider(provider, llm_settings)
            except Exception:
                model = ""
        if not model:
            model = normalize_model_id(DEFAULT_MODEL)

    raw_inference_mode = _thread_config_payload_value(
        payload,
        "inferenceMode",
        "inference_mode",
        "reasoningMode",
        "reasoning_mode",
    )
    inference_mode = (
        raw_inference_mode.strip().lower()
        if raw_inference_mode is not None
        else _thread_config_inference_mode(provider, model)
    )

    raw_retrieval_source = _thread_config_payload_value(
        payload,
        "retrievalSource",
        "retrieval_source",
        "sourceMode",
        "source_mode",
    )
    retrieval_source = (
        raw_retrieval_source.strip().lower()
        if raw_retrieval_source
        else "project"
    )

    raw_persona_id = (
        payload["personaId"]
        if "personaId" in payload
        else payload.get("persona_id")
    )
    persona_id = None
    if raw_persona_id is not None:
        persona_text = str(raw_persona_id).strip()
        persona_id = persona_text or None

    return {
        "providerId": provider,
        "modelId": model,
        "inferenceMode": inference_mode,
        "retrievalSource": retrieval_source,
        "personaId": persona_id,
    }


def _thread_config_payload_dict(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except Exception:
            return {}
        if isinstance(parsed, dict):
            return dict(parsed)
    return {}


def _extract_thread_config(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    value = raw.get("thread_config")
    if value is None:
        value = raw.get("threadConfig")
    if isinstance(value, dict):
        return dict(value)
    parsed = _thread_config_payload_dict(value)
    return parsed or None


def _merge_thread_config_update(
    existing_config: Any, patch: ThreadConfigUpdate
) -> dict[str, Any]:
    base_config = _build_thread_config_snapshot(
        _thread_config_payload_dict(existing_config)
    )
    patch_values = patch.model_dump(exclude_unset=True)
    if not patch_values:
        raise HTTPException(status_code=400, detail="No valid fields to update")

    for key in (
        "providerId",
        "modelId",
        "inferenceMode",
        "retrievalSource",
    ):
        if key in patch_values and patch_values[key] is None:
            raise HTTPException(
                status_code=400,
                detail=f"{key} cannot be null",
            )

    merged_payload = dict(base_config)
    merged_payload.update(patch_values)
    return _build_thread_config_snapshot(merged_payload)


def _persist_thread_config_snapshot(
    thread_id: int, thread_config: dict[str, Any]
) -> None:
    from guardian.core.pgdb import PgDB
    from guardian.db.models import ChatThread

    if not isinstance(chatlog_db, PgDB):
        return

    with chatlog_db._sa_session() as session:
        thread = session.get(ChatThread, thread_id)
        if thread is None:
            raise RuntimeError(
                f"chat thread {thread_id} not found while persisting thread_config"
            )
        thread.thread_config = thread_config


def _coerce_positive_int(raw: Any) -> Optional[int]:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _normalize_turn_id(raw: Any) -> str:
    """Return a normalized UUID turn_id; generate one when missing/invalid."""
    if isinstance(raw, str):
        candidate = raw.strip()
        if candidate:
            try:
                return str(uuid.UUID(candidate))
            except ValueError:
                logger.debug(
                    "[chat.complete] invalid turn_id=%s; generating server-side UUID",
                    candidate,
                )
    return str(uuid.uuid4())


def _normalize_task_identity(raw: Any) -> str | None:
    """Return a canonical UUID task identity or None when invalid."""
    candidate = str(raw or "").strip()
    if not candidate:
        return None
    try:
        return str(uuid.UUID(candidate))
    except ValueError:
        return None


def _coerce_message_meta(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return {}
        try:
            parsed = json.loads(text)
        except Exception:
            return {}
        return dict(parsed) if isinstance(parsed, dict) else {}
    return {}


def _coerce_message_id(raw: Any) -> int | None:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _coerce_execution_payload(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None

    normalized: dict[str, Any] = {}
    for key in (
        "attempted_provider",
        "attempted_model",
        "final_provider",
        "final_model",
    ):
        value = raw.get(key)
        if not isinstance(value, str):
            return None
        trimmed = value.strip()
        if not trimmed:
            return None
        normalized[key] = trimmed

    fallback_triggered = raw.get("fallback_triggered")
    if isinstance(fallback_triggered, bool):
        normalized["fallback_triggered"] = fallback_triggered
    elif isinstance(fallback_triggered, (int, float)):
        normalized["fallback_triggered"] = bool(fallback_triggered)
    elif isinstance(fallback_triggered, str):
        normalized[
            "fallback_triggered"
        ] = fallback_triggered.strip().lower() in {"1", "true", "yes", "on"}
    else:
        return None

    return normalized


def _fetch_message_extra_meta(
    *, thread_id: int, message_ids: list[int]
) -> dict[int, dict[str, Any]]:
    if not message_ids:
        return {}
    connect = getattr(chatlog_db, "_connect", None)
    if not callable(connect):
        return {}

    try:
        with connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, extra_meta
                    FROM chat_messages
                    WHERE thread_id = %s
                      AND id = ANY(%s::int[])
                    """,
                    (thread_id, message_ids),
                )
                rows = cur.fetchall() or []
    except Exception:
        logger.debug(
            "[chat.messages] failed to backfill extra_meta thread_id=%s",
            thread_id,
            exc_info=True,
        )
        return {}

    backfill: dict[int, dict[str, Any]] = {}
    for row in rows:
        raw_id: Any = None
        raw_meta: Any = None
        if isinstance(row, dict):
            raw_id = row.get("id")
            raw_meta = row.get("extra_meta")
        elif hasattr(row, "keys"):
            row_map = dict(row)  # psycopg row mapping
            raw_id = row_map.get("id")
            raw_meta = row_map.get("extra_meta")
        elif isinstance(row, (list, tuple)) and len(row) >= 2:
            raw_id = row[0]
            raw_meta = row[1]

        message_id = _coerce_message_id(raw_id)
        if message_id is None:
            continue
        meta = _coerce_message_meta(raw_meta)
        if meta:
            backfill[message_id] = meta
    return backfill


def _fetch_thread_metadata(thread_id: int) -> dict[str, Any]:
    getter = getattr(chatlog_db, "get_chat_thread", None)
    if callable(getter):
        try:
            thread = getter(thread_id)
        except Exception:
            thread = None
        if isinstance(thread, dict):
            metadata = _coerce_message_meta(thread.get("metadata"))
            if metadata:
                return metadata

    connect = getattr(chatlog_db, "_connect", None)
    if not callable(connect):
        return {}

    try:
        with connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT metadata
                    FROM chat_threads
                    WHERE id = %s
                    """,
                    (thread_id,),
                )
                row = cur.fetchone()
    except Exception:
        logger.debug(
            "[chat.trace] failed to read thread metadata thread_id=%s",
            thread_id,
            exc_info=True,
        )
        return {}

    if row is None:
        return {}
    if isinstance(row, dict):
        return _coerce_message_meta(row.get("metadata"))
    if hasattr(row, "keys"):
        return _coerce_message_meta(dict(row).get("metadata"))
    if isinstance(row, (list, tuple)) and row:
        return _coerce_message_meta(row[0])
    return {}


def _thread_trace_entry(
    metadata: dict[str, Any],
    *,
    key: str,
    thread_id: int,
    task_id: str | None = None,
) -> dict[str, Any] | None:
    entry = metadata.get(key)
    if not isinstance(entry, dict):
        return None

    entry_task_id = str(entry.get("task_id") or "").strip()
    if task_id is not None and entry_task_id != task_id:
        return None

    entry_thread_id = _coerce_positive_int(entry.get("thread_id"))
    if entry_thread_id is not None and entry_thread_id != thread_id:
        return None

    trace = entry.get("trace")
    if not isinstance(trace, dict):
        return None
    return dict(trace)


def _thread_latest_task_id(
    thread_id: int,
    metadata: dict[str, Any],
) -> str | None:
    task_id = _thread_latest_task.get(thread_id)
    if task_id:
        return task_id
    fallback = _normalize_task_identity(
        metadata.get(DEBUG_LATEST_COMPLETION_TASK_ID_METADATA_KEY)
    )
    if fallback:
        _thread_latest_task[thread_id] = fallback
    return fallback


def _persist_thread_latest_task_id(thread_id: int, task_id: str) -> None:
    normalized = _normalize_task_identity(task_id)
    if normalized is None:
        return
    _merge_thread_metadata_patch(
        thread_id,
        {DEBUG_LATEST_COMPLETION_TASK_ID_METADATA_KEY: normalized},
    )


def _persist_thread_latest_rag_trace(
    thread_id: int,
    task_id: str,
    trace: dict[str, Any],
) -> None:
    normalized = _normalize_task_identity(task_id)
    if normalized is None or not isinstance(trace, dict):
        return
    _merge_thread_metadata_patch(
        thread_id,
        {
            DEBUG_LATEST_COMPLETION_TASK_ID_METADATA_KEY: normalized,
            DEBUG_LATEST_RAG_TRACE_METADATA_KEY: {
                "task_id": normalized,
                "thread_id": thread_id,
                "trace": dict(trace),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        },
    )


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


def map_internal_depth_mode(
    requested_depth_raw: str, effective_depth_mode: DepthMode
) -> str:
    """
    Map API contract depth to runtime/broker depth_mode.

    Contract-only task: internal RAG/broker depth behavior must remain unchanged.
    """
    if requested_depth_raw == "deep":
        return "deep" if effective_depth_mode == "deep" else "normal"
    return requested_depth_raw


def normalize_source_mode(raw: Any) -> str:
    value = str(raw or "").strip().lower()
    return "personal_knowledge" if value == "personal_knowledge" else "project"


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
            # If recent thread exists and has no messages, reuse it.
            recent_id = recent_thread.get("id")
            if recent_id and chatlog_db.count_messages(recent_id) == 0:
                logger.info(
                    "Reusing recent empty thread %s for user %s",
                    recent_id,
                    user_id,
                )
                return {
                    "ok": True,
                    "id": recent_id,
                    "thread": recent_thread,
                }

        thread_config = _build_thread_config_snapshot(payload)
        record = chatlog_db.create_chat_thread(
            user_id=user_id,
            title=title,
            summary=summary,
            project_id=normalized_project,
            metadata=metadata,
        )
        _persist_thread_config_snapshot(int(record["id"]), thread_config)
        if isinstance(record, dict):
            record["thread_config"] = thread_config
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
def chat_list_threads(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user_id: Optional[str] = Query(default=None),
    project_id: Optional[int] = Query(default=None),
    api_key: str = Depends(require_api_key),
):
    """Return the list of persisted chat threads."""
    try:
        threads = chatlog_db.list_chat_threads(
            limit=limit,
            offset=offset,
            user_id=user_id,
            project_id=project_id,
        )
        return {
            "ok": True,
            "threads": threads,
            "limit": limit,
            "offset": offset,
            "next_offset": offset + len(threads),
            "has_more": len(threads) >= limit,
        }
    except Exception as exc:
        logger.exception("Failed to list chat threads: %s", exc)
        return {
            "ok": True,
            "threads": [],
            "limit": limit,
            "offset": offset,
            "next_offset": offset,
            "has_more": False,
        }


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
    try:
        message = _persist_message_to_thread(
            thread_id=thread_id,
            role=role,
            content=content,
            owner=str(owner),
            requested_project_id=body.get("project_id"),
        )
    except HTTPException as exc:
        if exc.status_code == 429 and isinstance(exc.detail, dict):
            return JSONResponse(status_code=429, content=exc.detail)
        raise
    return {"ok": True, "message": message}


@router.post("/messages")
def chat_post_message_create_on_send(
    body: ChatMessageCreateRequest = Body(...),
    api_key: str = Depends(require_api_key),
):
    """
    Post a message to an existing thread or create a thread on first send.

    This is the draft-friendly endpoint:
    - when `thread_id` is provided, it appends to that thread
    - when `thread_id` is null, it creates a thread and persists the first message
    """
    role = (body.role or "").strip()
    content = (body.content or "").strip()
    if not role or not content:
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": "role and content required"},
        )
    owner = str(body.user_id or "default")
    requested_thread_id = _coerce_positive_int(body.thread_id)
    created_thread = False
    created_thread_id: Optional[int] = None
    thread_record: Optional[Dict[str, Any]] = None

    if requested_thread_id is None:
        requested_title = (
            _normalize_thread_title(body.title)
            if body.title is not None
            else None
        )
        title = requested_title or _derive_thread_title_from_content(content)
        summary = (
            _normalize_thread_summary(body.summary)
            if body.summary is not None
            else ""
        ) or ""
        metadata: Dict[str, Any] = {}
        if isinstance(body.metadata, dict):
            metadata.update(body.metadata)
        if body.draft_tab_id:
            metadata["draft_tab_id"] = str(body.draft_tab_id)
        normalized_project = _coerce_project_id(body.project_id)
        try:
            thread_record = chatlog_db.create_chat_thread(
                user_id=owner,
                title=title,
                summary=summary,
                project_id=normalized_project,
                metadata=metadata or None,
            )
            created_thread_id = int(thread_record["id"])
            requested_thread_id = created_thread_id
            created_thread = True
            chatlog_db.write_audit_log(
                "create",
                "chat_thread",
                str(created_thread_id),
                user_id=owner,
            )
        except Exception as exc:
            logger.exception(
                "Failed to create thread during create-on-send: %s", exc
            )
            raise HTTPException(
                status_code=500, detail="Failed to create chat thread"
            )

    assert requested_thread_id is not None
    try:
        message = _persist_message_to_thread(
            thread_id=requested_thread_id,
            role=role,
            content=content,
            owner=owner,
            requested_project_id=body.project_id,
        )
    except HTTPException as exc:
        if exc.status_code == 429 and isinstance(exc.detail, dict):
            return JSONResponse(status_code=429, content=exc.detail)
        if created_thread and created_thread_id is not None:
            try:
                chatlog_db.delete_thread(created_thread_id, force=True)
            except Exception:
                logger.warning(
                    "[chat.messages] failed to rollback created thread_id=%s after HTTP failure",
                    created_thread_id,
                    exc_info=True,
                )
        raise
    except Exception:
        if created_thread and created_thread_id is not None:
            try:
                chatlog_db.delete_thread(created_thread_id, force=True)
            except Exception:
                logger.warning(
                    "[chat.messages] failed to rollback created thread_id=%s after message failure",
                    created_thread_id,
                    exc_info=True,
                )
        raise

    if thread_record is None:
        thread_record = chatlog_db.get_chat_thread(requested_thread_id)
    return {
        "ok": True,
        "created_thread": created_thread,
        "thread_id": requested_thread_id,
        "thread": thread_record,
        "message": message,
        "draft_tab_id": body.draft_tab_id,
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
    normalized_items: list[dict[str, Any]] = []
    missing_meta_ids: list[int] = []
    for raw_item in items:
        if not isinstance(raw_item, dict):
            continue
        item = dict(raw_item)
        message_id = _coerce_message_id(item.get("id"))
        execution = _coerce_execution_payload(item.get("execution"))
        metadata = _coerce_message_meta(item.get("metadata"))
        if not metadata:
            metadata = _coerce_message_meta(item.get("extra_meta"))
        if metadata:
            item["metadata"] = metadata
            if execution is None:
                execution = _coerce_execution_payload(metadata.get("execution"))
            if execution:
                item["execution"] = execution
            turn_id_raw = metadata.get("turn_id")
            if isinstance(turn_id_raw, str) and turn_id_raw.strip():
                item["turn_id"] = turn_id_raw.strip()
        elif message_id is not None:
            missing_meta_ids.append(message_id)
        normalized_items.append(item)

    if missing_meta_ids:
        backfill = _fetch_message_extra_meta(
            thread_id=thread_id,
            message_ids=missing_meta_ids,
        )
        if backfill:
            for item in normalized_items:
                message_id = _coerce_message_id(item.get("id"))
                if message_id is None or "metadata" in item:
                    continue
                metadata = backfill.get(message_id)
                if not metadata:
                    continue
                item["metadata"] = metadata
                execution = _coerce_execution_payload(item.get("execution"))
                if execution is None:
                    execution = _coerce_execution_payload(
                        metadata.get("execution")
                    )
                if execution:
                    item["execution"] = execution
                turn_id_raw = metadata.get("turn_id")
                if isinstance(turn_id_raw, str) and turn_id_raw.strip():
                    item["turn_id"] = turn_id_raw.strip()

    normalized_items = _attach_message_audio_metadata(normalized_items)
    total = chatlog_db.count_messages(thread_id)
    return {"ok": True, "total": total, "messages": normalized_items}


@router.post("/{thread_id}/complete")
async def chat_complete(
    thread_id: int,
    body: ChatCompletionRequest = Body(...),
    request: Request = None,
    api_key: str = Depends(require_api_key),
    request_id: str | None = Header(None, alias="X-Request-ID"),
):
    """
    Enqueue an assistant reply for the given thread and return a task id.
    """
    turn_id = _normalize_turn_id(body.turn_id)
    source_mode = normalize_source_mode(body.source_mode)

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
        raise HTTPException(status_code=404, detail="Thread not found")

    thread_execution = resolve_thread_completion_settings(
        thread_exists if isinstance(thread_exists, dict) else None,
        requested_provider=body.provider,
        requested_model=body.model,
        requested_reasoning_mode=body.reasoning_mode,
        requested_source_mode=source_mode,
        settings=llm_settings,
    )
    provider = thread_execution.provider
    model = thread_execution.model
    reasoning_mode = thread_execution.reasoning_mode
    source_mode = thread_execution.source_mode

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
        raise HTTPException(
            status_code=400, detail="Thread has no usable context"
        )

    requested_depth_raw = normalize_requested_depth_raw(body.depth_mode)
    # Binary projection: deep iff raw request is exactly "deep".
    requested_depth_mode: DepthMode = project_requested_depth_mode(
        requested_depth_raw
    )
    depth_downgrade_reason: DepthDowngradeReason | None = None
    thread_project_id: Optional[int] = None
    if isinstance(thread_exists, dict):
        thread_project_id = _coerce_positive_int(
            thread_exists.get("project_id")
        )
    if thread_project_id is None:
        try:
            # Optional backend seam: infer project association from thread profile.
            profile_getter = getattr(chatlog_db, "get_thread_profile", None)
            if callable(profile_getter):
                profile = profile_getter(thread_id)
                inferred_project_id: Any = None
                if isinstance(profile, dict):
                    inferred_project_id = profile.get("project_id")
                    if not isinstance(inferred_project_id, int):
                        thread_payload = profile.get("thread")
                        if isinstance(thread_payload, dict):
                            inferred_project_id = thread_payload.get(
                                "project_id"
                            )
                if isinstance(inferred_project_id, int):
                    thread_project_id = _coerce_positive_int(
                        inferred_project_id
                    )
        except Exception as exc:
            logger.debug(
                "[chat.complete] failed to infer project_id from thread profile thread_id=%s err=%s",
                thread_id,
                exc,
            )
    thread_has_project = thread_project_id is not None

    project_identity_depth_raw: str | None = None
    project_identity_depth_norm = normalize_project_identity_depth(None)
    project_depth_state: ProjectDepthState = "missing"
    policy_allows_deep = False

    if requested_depth_raw == "deep" and thread_has_project:
        try:
            getter = getattr(chatlog_db, "get_project_identity_depth", None)
            if callable(getter):
                raw_project_depth = getter(thread_project_id)
                project_identity_depth_raw = (
                    None
                    if raw_project_depth is None
                    else str(raw_project_depth)
                )
            else:
                project_identity_depth_raw = "__missing_project_depth_getter__"
            project_identity_depth_norm = normalize_project_identity_depth(
                project_identity_depth_raw
            )
            project_depth_state = classify_project_identity_depth(
                project_identity_depth_raw
            )
            if project_depth_state == "known":
                policy_allows_deep = bool(
                    can_run_deep_identity_modeling(project_identity_depth_norm)
                )
        except Exception:
            logger.exception(
                "[chat.complete] depth resolution failed thread_id=%s project_id=%s",
                thread_id,
                thread_project_id,
            )
            project_identity_depth_raw = "__depth_resolution_exception__"
            project_identity_depth_norm = normalize_project_identity_depth(
                project_identity_depth_raw
            )
            project_depth_state = classify_project_identity_depth(
                project_identity_depth_raw
            )
            policy_allows_deep = False

    effective_depth_mode, depth_downgrade_reason = resolve_depth(
        requested_depth_raw,
        thread_has_project=thread_has_project,
        project_depth_state=project_depth_state,
        project_identity_depth_norm=project_identity_depth_norm,
        policy_allows_deep=policy_allows_deep,
    )
    if requested_depth_mode == "deep" and effective_depth_mode == "light":
        logger.info(
            "[chat.complete] downgraded depth_mode=deep thread_id=%s project_id=%s reason=%s",
            thread_id,
            thread_project_id,
            depth_downgrade_reason,
        )

    internal_depth_mode = map_internal_depth_mode(
        requested_depth_raw, effective_depth_mode
    )
    doc_context_override = await _build_doc_context_override(
        thread_id=thread_id,
        depth_mode=internal_depth_mode,
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
        model=model,
        requested_provider=body.provider,
        requested_model=body.model,
        selection_source="explicit" if (provider or body.model) else "default",
        provider_pinned=bool(str(provider or "").strip()),
        reasoning_mode=reasoning_mode,
        max_context=body.max_context,
        depth_mode=internal_depth_mode,
        system_override=merged_system_override,
        # Temporary transport bridge: carry turn_id and source_mode via origin
        # until ChatCompletionTask gains typed fields for both values.
        origin=f"api:chat.complete|turn_id={turn_id}|source_mode={source_mode}",
    )
    task.turn_id = turn_id
    task_identity = _normalize_task_identity(getattr(task, "task_id", None))
    if task_identity is None:
        logger.error(
            "[chat.complete] invalid task identity thread_id=%s turn_id=%s task_type=%s",
            thread_id,
            turn_id,
            getattr(task, "type", "unknown"),
        )
        raise _completion_service_unavailable("task_identity_invalid")
    task.task_id = task_identity
    task.turn_lock_owner = task_identity

    locked = _run_completion_redis_op(
        lambda: acquire_turn_lock(thread_id, task.turn_lock_owner),
        reason="turn_lock_unavailable",
        log_message="[chat.complete] turn lock unavailable: %s",
    )
    if not locked:
        if _recover_orphaned_turn_lock(thread_id):
            locked = _run_completion_redis_op(
                lambda: acquire_turn_lock(thread_id, task.turn_lock_owner),
                reason="turn_lock_unavailable",
                log_message="[chat.complete] turn lock unavailable after recovery: %s",
            )
        if not locked:
            raise HTTPException(status_code=429, detail="turn_in_flight")

    task.turn_lock = _turn_lock_payload(
        locked if isinstance(locked, TurnLockEnvelope) else None,
        thread_id=thread_id,
        owner=task.turn_lock_owner,
        turn_id=turn_id,
    )

    queue_name = "codexify:queue:chat"

    try:
        run_with_redis_timeout(lambda: enqueue(task, queue_name))
    except QueueEnqueueError as exc:
        _best_effort_release_turn_lock(
            thread_id,
            task.turn_lock_owner,
            log_message="[chat.complete] failed to release lock after enqueue error",
        )
        logger.error(
            "[chat.complete] enqueue failed",
            extra={
                "error_code": "CHAT_COMPLETE_ENQUEUE_FAILED",
                "request_id": request_id,
                "thread_id": thread_id,
                "depth_mode": internal_depth_mode,
                "turn_id": turn_id,
                "queue_name": exc.queue_name,
                "exception_class": type(exc).__name__,
                "cause_class": type(exc.__cause__).__name__
                if exc.__cause__
                else None,
            },
            exc_info=exc,
        )
        detail = _completion_service_unavailable("queue_unavailable").detail
        if isinstance(detail, dict):
            detail = {**detail, "error_code": "CHAT_COMPLETE_ENQUEUE_FAILED"}
        raise HTTPException(status_code=503, detail=detail)
    except (RedisOperationTimeout, Exception) as exc:
        _best_effort_release_turn_lock(
            thread_id,
            task.turn_lock_owner,
            log_message="[chat.complete] failed to release lock after enqueue error",
        )
        logger.warning(
            "[chat.complete] queue unavailable error_code=%s: %s",
            CHAT_COMPLETE_ENQUEUE_ERROR_CODE,
            exc,
        )
        raise _completion_service_unavailable("queue_unavailable")

    # Track latest task for debug endpoint
    _thread_latest_task[thread_id] = task_identity
    _persist_thread_latest_task_id(thread_id, task_identity)

    task_created_publish_error: task_events.TaskEventPublishError | None = None
    try:
        task_created_publish_result = _publish_completion_start_event(
            task=task,
            thread_id=thread_id,
            turn_id=turn_id,
        )
    except task_events.TaskEventPublishError as exc:
        task_created_publish_error = exc
        task_created_publish_result = exc.to_publish_result()
        cause_class = exc.cause_class
        if cause_class is None and isinstance(exc.__cause__, BaseException):
            cause_class = exc.__cause__.__class__.__name__
        logger.error(
            (
                "[chat.complete] error_code=%s task_event_error_code=%s "
                "task.created publish failed request_id=%s thread_id=%s "
                "task_id=%s turn_id=%s depth_mode=%s event_type=%s "
                "cause_class=%s"
            ),
            CHAT_COMPLETE_TASK_CREATED_EVENT_ERROR_CODE,
            exc.error_code,
            _request_id_from_request(request),
            thread_id,
            task_identity,
            turn_id,
            internal_depth_mode,
            exc.event_type,
            cause_class,
        )
    acceptance_status, acceptance_warnings = _completion_acceptance_outcome(
        task_created_publish_result
    )

    if task_created_publish_error is None:
        log_level = (
            logging.INFO
            if acceptance_status == COMPLETION_ACCEPTANCE_STATUS_ACCEPTED
            else logging.WARNING
        )
        logger.log(
            log_level,
            (
                "[task] created type=%s id=%s origin=%s thread=%s "
                "acceptance_status=%s acceptance_warnings=%s "
                "task_created_visibility_scope=%s task_created_event_id=%s "
                "task_created_failure_class=%s"
            ),
            task.type,
            task_identity,
            task.origin,
            thread_id,
            acceptance_status,
            acceptance_warnings,
            task_created_publish_result.get("visibility_scope"),
            task_created_publish_result.get("event_id"),
            task_created_publish_result.get("failure_class"),
        )

    messages_url = f"/api/chat/{thread_id}/messages"
    trace_url = f"/api/chat/debug/rag-trace/{thread_id}/latest"

    response = {
        "ok": True,
        "acceptance_status": acceptance_status,
        "acceptance_warnings": acceptance_warnings,
        "task_id": task_identity,
        "turn_id": turn_id,
        "thread_id": thread_id,
        "source_mode": source_mode,
        "depth_mode": internal_depth_mode,
        "requested_depth_mode": requested_depth_mode,
        "effective_depth_mode": effective_depth_mode,
        "depth_downgrade_reason": depth_downgrade_reason,
        "messages_url": messages_url,
        "trace_url": trace_url,
    }

    completed_payload = _get_task_completed_payload(task_identity, block_ms=0)
    execution = None
    if isinstance(completed_payload, dict):
        execution = _coerce_execution_payload(
            completed_payload.get("execution")
        )
        if execution is None:
            execution = _coerce_execution_payload(
                {
                    "attempted_provider": completed_payload.get(
                        "attempted_provider"
                    ),
                    "attempted_model": completed_payload.get("attempted_model"),
                    "final_provider": completed_payload.get("provider")
                    or completed_payload.get("final_provider"),
                    "final_model": completed_payload.get("model")
                    or completed_payload.get("final_model"),
                    "fallback_triggered": (
                        completed_payload.get("completion_truth", {}) or {}
                    ).get("fallback_attempted"),
                }
            )
    if execution is not None:
        response["execution"] = execution

    return response


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


@router.patch("/threads/{thread_id}/config")
def patch_thread_config(
    thread_id: int,
    body: ThreadConfigUpdate = Body(...),
    api_key: str = Depends(require_api_key),
):
    """Update the durable thread execution contract without starting a run."""
    existing = chatlog_db.get_chat_thread(thread_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Thread not found")

    updated_config = _merge_thread_config_update(
        existing.get("thread_config"), body
    )
    _persist_thread_config_snapshot(thread_id, updated_config)
    return {
        "ok": True,
        "thread_id": thread_id,
        "thread_config": updated_config,
    }


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
    thread_payload = None
    get_chat_thread = getattr(chatlog_db, "get_chat_thread", None)
    if callable(get_chat_thread):
        try:
            thread_payload = get_chat_thread(thread_id)
        except Exception:
            thread_payload = None

    if isinstance(thread_payload, dict):
        return {
            "thread_id": thread_payload.get("id"),
            "parent_thread_id": thread_payload.get("parent_id"),
            "session_id": None,
            "summary": thread_payload.get("summary"),
            "created_at": thread_payload.get("created_at"),
            "user_id": thread_payload.get("user_id"),
            "project_id": thread_payload.get("project_id"),
            "thread_config": _extract_thread_config(thread_payload),
        }

    row = getattr(chatlog_db, "get_thread", lambda _thread_id: None)(thread_id)
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
        "thread_config": None,
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
            "thread_config": _extract_thread_config(row),
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


def _get_task_completed_payload(
    task_id: str, *, block_ms: int = 1000
) -> Optional[Dict[str, Any]]:
    """
    Read task events and return the most recent task.completed payload.
    """
    try:
        events = task_events.read_events(
            task_id, "0", count=100, block_ms=block_ms
        )
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
    payload_summary: Dict[str, Any] | None = None
    metadata = _fetch_thread_metadata(thread_id)
    profile_debug: Dict[str, Any] = {
        "active_profile_id": None,
        "provider_override": None,
        "model_override": None,
        "injection_hash": None,
        "retrieval_mode": None,
        "model_mode": None,
    }

    # Try to get trace + profile data from task events if we have a recent task.
    task_id = _thread_latest_task_id(thread_id, metadata)
    if task_id:
        completed_payload = _get_task_completed_payload(task_id)
        if isinstance(completed_payload, dict):
            payload_trace = completed_payload.get("trace")
            if isinstance(payload_trace, dict):
                trace = dict(payload_trace)
                _rag_traces[thread_id] = trace  # Cache it
                _persist_thread_latest_rag_trace(thread_id, task_id, trace)
            elif trace is None:
                candidate_trace = _thread_trace_entry(
                    metadata,
                    key=DEBUG_RAG_TRACE_CANDIDATE_METADATA_KEY,
                    thread_id=thread_id,
                    task_id=task_id,
                )
                if candidate_trace is not None:
                    trace = candidate_trace
                    _rag_traces[thread_id] = trace
                    _persist_thread_latest_rag_trace(
                        thread_id,
                        task_id,
                        trace,
                    )
            if isinstance(completed_payload.get("payload_summary"), dict):
                payload_summary = dict(completed_payload.get("payload_summary"))
                if trace is not None:
                    trace["payload_summary"] = payload_summary
                    _rag_traces[thread_id] = trace
            for key in (
                "active_profile_id",
                "provider_override",
                "model_override",
                "injection_hash",
                "retrieval_mode",
                "model_mode",
            ):
                profile_debug[key] = completed_payload.get(key)

    if trace is None:
        persisted = _thread_trace_entry(
            metadata,
            key=DEBUG_LATEST_RAG_TRACE_METADATA_KEY,
            thread_id=thread_id,
        )
        if persisted is not None:
            trace = persisted

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

    if payload_summary is not None:
        trace["payload_summary"] = payload_summary

    trace.setdefault("thread_id", thread_id)
    trace.setdefault("project_id", None)
    trace.setdefault("depth_mode", None)
    trace.setdefault("source_mode", None)
    trace.setdefault("widen_reason", "none")

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
def api_chat_list_threads(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user_id: Optional[str] = Query(default=None),
    project_id: Optional[int] = Query(default=None),
    api_key: str = Depends(require_api_key),
):
    """Compat alias for GET /chat/threads used in tests."""
    return chat_list_threads(
        limit=limit,
        offset=offset,
        user_id=user_id,
        project_id=project_id,
        api_key=api_key,
    )


@api_chat_router.post("/{thread_id}/messages")
def api_chat_post_message(
    thread_id: int,
    body: Dict[str, str] = Body(...),
    api_key: str = Depends(require_api_key),
):
    """Compat alias for POST /chat/{thread_id}/messages used in tests."""
    return chat_post_message(thread_id, body, api_key=api_key)


@api_chat_router.post("/messages")
def api_chat_post_message_create_on_send(
    body: ChatMessageCreateRequest = Body(...),
    api_key: str = Depends(require_api_key),
):
    """Compat alias for POST /chat/messages used by draft tabs."""
    return chat_post_message_create_on_send(body, api_key=api_key)


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
    request: Request = None,
    api_key: str = Depends(require_api_key),
    request_id: str | None = Header(None, alias="X-Request-ID"),
):
    """Compat alias for POST /chat/{thread_id}/complete used in tests."""
    return await chat_complete(
        thread_id,
        body,
        request=request,
        api_key=api_key,
        request_id=request_id,
    )


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


@api_chat_router.patch("/threads/{thread_id}/config")
def api_patch_thread_config(
    thread_id: int,
    body: ThreadConfigUpdate = Body(...),
    api_key: str = Depends(require_api_key),
):
    """Compat alias for PATCH /chat/threads/{thread_id}/config."""
    return patch_thread_config(thread_id, body, api_key=api_key)


@api_chat_router.delete("/threads/{thread_id}")
def api_delete_thread(
    thread_id: int,
    force: bool = Query(False),
    api_key: str = Depends(require_api_key),
):
    """Compat alias for DELETE /chat/threads/{thread_id} used in tests."""
    return delete_thread(thread_id, force, api_key=api_key)
