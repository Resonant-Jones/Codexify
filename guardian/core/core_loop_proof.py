"""Experimental core-loop proof lane service.

This module keeps the proof lane small and explicit: it can create or load a
thread, record a user turn, route a provider/model choice through the existing
selection helpers, run retrieval proof when requested, emit operator-visible
events, and persist a safe thread metadata snapshot.

The lane is intentionally experimental and does not invoke a real provider
completion call.
"""

from __future__ import annotations

import copy
import hashlib
import json
import logging
import os
import uuid
from datetime import UTC, datetime
from typing import Any

from guardian.context.broker import ContextBroker
from guardian.context.retrieval_router_policy import (
    SOURCE_MODE_PROJECT,
)
from guardian.core import dependencies, event_bus
from guardian.core.chat_completion_service import resolve_thread_completion_settings
from guardian.core.config import get_settings
from guardian.core.llm_catalog import first_enabled_provider
from guardian.core.provider_registry import (
    normalize_provider,
    resolve_provider_capability,
)
from guardian.core.provider_truth import build_provider_truth

logger = logging.getLogger(__name__)

CORE_LOOP_PROOF_ENV = "CODEXIFY_ENABLE_CORE_LOOP_PROOF"
CORE_LOOP_PROOF_METADATA_KEY = "core_loop_proof"
CORE_LOOP_PROOF_THREAD_TITLE = "Core Loop Proof"
CORE_LOOP_PROOF_THREAD_SUMMARY = "Experimental proof lane for the chat core loop"
CORE_LOOP_PROOF_MAX_MESSAGE_CHARS = 12_000


def core_loop_proof_enabled() -> bool:
    value = os.getenv(CORE_LOOP_PROOF_ENV, "")
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _normalize_text(value: Any) -> str:
    return str(value or "").strip()


def _digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _request_account_id(request_user_scope: Any) -> str:
    account_id = _normalize_text(getattr(request_user_scope, "account_id", None))
    if account_id:
        return account_id
    user_id = _normalize_text(getattr(request_user_scope, "user_id", None))
    if user_id:
        return user_id
    return _normalize_text(dependencies.get_single_user_id())


def _thread_owner_id(thread: dict[str, Any] | None) -> str:
    if not isinstance(thread, dict):
        return ""
    return _normalize_text(thread.get("user_id"))


def _extract_thread_metadata(thread: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(thread, dict):
        return {}
    for key in ("metadata", "thread_config"):
        raw = thread.get(key)
        if isinstance(raw, dict):
            return copy.deepcopy(raw)
        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
            except Exception:
                continue
            if isinstance(parsed, dict):
                return copy.deepcopy(parsed)
    return {}


def _merge_proof_metadata(
    thread: dict[str, Any] | None,
    proof_state: dict[str, Any],
) -> dict[str, Any]:
    metadata = _extract_thread_metadata(thread)
    metadata[CORE_LOOP_PROOF_METADATA_KEY] = copy.deepcopy(proof_state)
    return metadata


def _first_non_empty_text(
    item: dict[str, Any],
    keys: tuple[str, ...],
) -> str | None:
    for key in keys:
        value = _normalize_text(item.get(key))
        if value:
            return value
    return None


def _collect_retrieval_sources(
    context: dict[str, Any],
) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    for bucket_name, bucket_label in (
        ("semantic", "semantic"),
        ("obsidian", "obsidian"),
        ("memory", "memory"),
        ("graph", "graph"),
        ("personal_facts", "personal_facts"),
    ):
        bucket = context.get(bucket_name)
        if not isinstance(bucket, list):
            continue
        for index, item in enumerate(bucket):
            if not isinstance(item, dict):
                continue
            content_text = _first_non_empty_text(
                item,
                ("content", "text", "snippet", "excerpt", "summary"),
            )
            sources.append(
                {
                    "source_group": bucket_label,
                    "source_id": _first_non_empty_text(
                        item,
                        (
                            "source_id",
                            "document_id",
                            "message_id",
                            "node_id",
                            "memory_id",
                            "id",
                        ),
                    )
                    or f"{bucket_label}:{index}",
                    "source_label": _first_non_empty_text(
                        item,
                        (
                            "title",
                            "name",
                            "label",
                            "kind",
                            "source_type",
                            "namespace",
                        ),
                    )
                    or bucket_label,
                    "source_content_hash": (
                        _digest_text(content_text) if content_text else None
                    ),
                }
            )

    docs = context.get("docs")
    if isinstance(docs, dict):
        for doc_group in ("project", "thread", "global"):
            bucket = docs.get(doc_group)
            if not isinstance(bucket, list):
                continue
            for index, item in enumerate(bucket):
                if not isinstance(item, dict):
                    continue
                content_text = _first_non_empty_text(
                    item,
                    ("content", "text", "snippet", "excerpt", "summary"),
                )
                sources.append(
                    {
                        "source_group": f"docs:{doc_group}",
                        "source_id": _first_non_empty_text(
                            item,
                            ("source_id", "document_id", "id"),
                        )
                        or f"docs:{doc_group}:{index}",
                        "source_label": _first_non_empty_text(
                            item,
                            (
                                "title",
                                "name",
                                "label",
                                "filename",
                                "document_type",
                            ),
                        )
                        or f"docs:{doc_group}",
                        "source_content_hash": (
                            _digest_text(content_text) if content_text else None
                        ),
                    }
                )
    return sources


def _emit_proof_event(
    *,
    events: list[dict[str, Any]],
    event_type: str,
    thread_id: int,
    safe_metadata: dict[str, Any],
    tenant_id: str,
) -> dict[str, Any]:
    event = {
        "event_id": str(uuid.uuid4()),
        "thread_id": thread_id,
        "event_type": event_type,
        "timestamp": _utc_now_iso(),
        "safe_metadata": copy.deepcopy(safe_metadata),
    }
    events.append(event)
    try:
        event_bus.emit_event(
            f"core_loop_proof.{event_type}",
            event,
            tenant_id=tenant_id,
        )
    except Exception:
        logger.debug(
            "[core-loop-proof] event bus emit failed event_type=%s thread_id=%s",
            event_type,
            thread_id,
            exc_info=True,
        )
    return event


def _ensure_thread(
    chatlog_db: Any,
    *,
    thread_id: int | None,
    owner_id: str,
    project_id: int | None,
) -> tuple[dict[str, Any], bool]:
    created_new = False
    if thread_id is None:
        thread = chatlog_db.create_chat_thread(
            user_id=owner_id,
            title=CORE_LOOP_PROOF_THREAD_TITLE,
            summary=CORE_LOOP_PROOF_THREAD_SUMMARY,
            project_id=project_id,
        )
        created_new = True
    else:
        thread = chatlog_db.get_chat_thread(thread_id)
        if thread is None:
            ensure_thread = getattr(chatlog_db, "ensure_chat_thread", None)
            if not callable(ensure_thread):
                raise RuntimeError("chat_db_missing_ensure_thread")
            thread = ensure_thread(
                thread_id,
                user_id=owner_id,
                title=CORE_LOOP_PROOF_THREAD_TITLE,
                summary=CORE_LOOP_PROOF_THREAD_SUMMARY,
                project_id=project_id,
            )
            created_new = True
        elif _thread_owner_id(thread) and _thread_owner_id(thread) != owner_id:
            raise PermissionError("Thread does not belong to the authenticated account")

    if not isinstance(thread, dict):
        raise RuntimeError("thread_store_returned_invalid_payload")
    if thread.get("id") is None:
        raise RuntimeError("thread_store_missing_thread_id")
    return thread, created_new


def _safe_provider_metadata(
    *,
    selected_provider: str,
    selected_model: str | None,
    routing_source: str,
    provider_hint: str | None,
    settings: Any,
    requested_provider: str | None,
) -> dict[str, Any]:
    capability = resolve_provider_capability(selected_provider, settings)
    truth = build_provider_truth(
        selected_provider,
        settings,
        capability=capability,
        attempted=False,
        executed=False,
        completed=False,
    )
    provider_hint_used = routing_source == "request_hint"
    fallback_used = bool(provider_hint and routing_source != "request_hint")
    return {
        "provider_selected": selected_provider,
        "provider_model": selected_model,
        "provider_reason": routing_source,
        "provider_hint": provider_hint,
        "provider_hint_used": provider_hint_used,
        "fallback_used": fallback_used,
        "requested_provider": requested_provider,
        "available": bool(capability.get("available")),
        "enabled": bool(capability.get("enabled")),
        "authorized": bool(capability.get("authorized")),
        "truth": truth,
        "invoked": False,
        "execution": "skipped_for_proof_lane",
    }


async def _build_retrieval_proof(
    *,
    chatlog_db: Any,
    thread: dict[str, Any],
    thread_id: int,
    owner_id: str,
    query_text: str,
    source_mode: str,
) -> dict[str, Any]:
    vector_store = dependencies.get_vector_store()
    broker = ContextBroker(
        chatlog_db,
        vector_store,
        getattr(dependencies, "_memory_store", None),
        getattr(dependencies, "_sensors", None),
        settings=get_settings(),
    )
    context, rag_trace = await broker.assemble(
        thread_id,
        query_text,
        depth_mode="normal",
        project_id=thread.get("project_id"),
        user_id=owner_id,
        source_mode=source_mode or SOURCE_MODE_PROJECT,
    )
    provenance = dict(rag_trace.get("retrieval_provenance") or {})
    source_hit_counts = dict(provenance.get("source_hit_counts") or {})
    retrieval_status = _normalize_text(provenance.get("retrieval_status"))
    if not retrieval_status:
        retrieval_status = "unknown"
    sources = _collect_retrieval_sources(context)

    return {
        "retrieval_enabled": True,
        "enabled": True,
        "executed": bool(rag_trace.get("retrieval_executed")),
        "retrieval_status": retrieval_status,
        "status": retrieval_status,
        "absence_reason": rag_trace.get("retrieval_absence_reason"),
        "source_mode": rag_trace.get("source_mode"),
        "widen_reason": rag_trace.get("widen_reason"),
        "query_chars": len(query_text),
        "query_hash": _digest_text(query_text),
        "result_count": len(sources),
        "source_ids": [str(item.get("source_id") or "") for item in sources],
        "source_labels": [str(item.get("source_label") or "") for item in sources],
        "source_content_hashes": [
            str(item.get("source_content_hash") or "")
            for item in sources
            if item.get("source_content_hash")
        ],
        "sources": sources,
        "source_hit_counts": source_hit_counts,
        "proof_capable": any(int(v or 0) > 0 for v in source_hit_counts.values()),
        "retrieval_summary": {
            "messages": len(context.get("messages") or []),
            "semantic": len(context.get("semantic") or []),
            "docs": sum(
                len(context.get("docs", {}).get(key, []) or [])
                for key in ("project", "thread", "global")
            ),
            "memory": len(context.get("memory") or []),
            "graph": len(context.get("graph") or []),
        },
    }


def _safe_failed_result(
    *,
    request_id: str,
    thread_id: int | None,
    status_code: int,
    status: str,
    error_code: str,
    error_message: str,
    events: list[dict[str, Any]],
    thread_state: dict[str, Any] | None = None,
    provider: dict[str, Any] | None = None,
    retrieval: dict[str, Any] | None = None,
    assistant_message: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "ok": False,
        "http_status": status_code,
        "status": status,
        "request_id": request_id,
        "thread_id": thread_id,
        "thread_state": thread_state,
        "provider": provider,
        "provider_metadata": provider,
        "retrieval_proof": retrieval,
        "retrieval": retrieval,
        "assistant_message": assistant_message,
        "message": assistant_message,
        "events": events,
        "error": {
            "code": error_code,
            "message": error_message,
        },
    }


async def run_core_loop_proof(
    *,
    chatlog_db: Any,
    request_user_scope: Any,
    message: str,
    thread_id: int | None = None,
    provider_hint: str | None = None,
    retrieval_enabled: bool = True,
    retrieval_query: str | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    if not core_loop_proof_enabled():
        return {
            "ok": False,
            "http_status": 404,
            "status": "disabled",
            "request_id": request_id or str(uuid.uuid4()),
            "thread_id": thread_id,
            "thread_state": None,
            "provider": None,
            "provider_metadata": None,
            "retrieval": None,
            "retrieval_proof": None,
            "assistant_message": None,
            "message": None,
            "events": [],
            "error": {
                "code": "CORE_LOOP_PROOF_DISABLED",
                "message": "Not Found",
            },
        }

    cleaned_message = _normalize_text(message)
    if not cleaned_message:
        return {
            "ok": False,
            "http_status": 422,
            "status": "invalid_request",
            "request_id": request_id or str(uuid.uuid4()),
            "thread_id": thread_id,
            "thread_state": None,
            "provider": None,
            "provider_metadata": None,
            "retrieval": None,
            "retrieval_proof": None,
            "assistant_message": None,
            "message": None,
            "events": [],
            "error": {
                "code": "message_required",
                "message": "message is required",
            },
        }

    if len(cleaned_message) > CORE_LOOP_PROOF_MAX_MESSAGE_CHARS:
        return {
            "ok": False,
            "http_status": 413,
            "status": "invalid_request",
            "request_id": request_id or str(uuid.uuid4()),
            "thread_id": thread_id,
            "thread_state": None,
            "provider": None,
            "provider_metadata": None,
            "retrieval": None,
            "retrieval_proof": None,
            "assistant_message": None,
            "message": None,
            "events": [],
            "error": {
                "code": "message_too_large",
                "message": (
                    f"message exceeds {CORE_LOOP_PROOF_MAX_MESSAGE_CHARS} characters"
                ),
            },
        }

    current_request_id = _normalize_text(request_id) or str(uuid.uuid4())
    owner_id = _request_account_id(request_user_scope)
    events: list[dict[str, Any]] = []
    thread: dict[str, Any] | None = None
    created_new = False

    try:
        thread, created_new = _ensure_thread(
            chatlog_db,
            thread_id=thread_id,
            owner_id=owner_id,
            project_id=None,
        )
        resolved_thread_id = int(thread["id"])
        message_count_before = int(chatlog_db.count_messages(resolved_thread_id) or 0)
        _emit_proof_event(
            events=events,
            event_type="request_received",
            thread_id=resolved_thread_id,
            safe_metadata={
                "request_id": current_request_id,
                "message_chars": len(cleaned_message),
                "message_hash": _digest_text(cleaned_message),
                "retrieval_enabled": bool(retrieval_enabled),
                "provider_hint_present": bool(_normalize_text(provider_hint)),
                "thread_id_requested": thread_id,
            },
            tenant_id=owner_id,
        )
        _emit_proof_event(
            events=events,
            event_type="thread_loaded_or_created",
            thread_id=resolved_thread_id,
            safe_metadata={
                "request_id": current_request_id,
                "created_new": created_new,
                "message_count_before": message_count_before,
                "thread_owner": _thread_owner_id(thread),
            },
            tenant_id=owner_id,
        )

        user_message_id = chatlog_db.create_message(
            resolved_thread_id,
            "user",
            cleaned_message,
            user_id=owner_id,
        )

        settings = get_settings()
        provider_hint_text = _normalize_text(provider_hint)
        provider_hint_candidate = (
            normalize_provider(provider_hint_text) if provider_hint_text else None
        )
        hint_capability = (
            resolve_provider_capability(provider_hint_candidate, settings)
            if provider_hint_candidate
            else None
        )
        hint_allowed = bool(
            hint_capability
            and hint_capability.get("enabled")
            and hint_capability.get("authorized")
        )
        requested_provider_for_routing = (
            provider_hint_candidate if hint_allowed else None
        )
        thread_settings = resolve_thread_completion_settings(
            thread,
            requested_provider=requested_provider_for_routing,
            requested_model=None,
            requested_reasoning_mode=None,
            requested_source_mode=None,
            settings=settings,
        )
        selected_provider = _normalize_text(thread_settings.provider)
        if not selected_provider:
            selected_provider = (
                _normalize_text(first_enabled_provider(settings=settings)) or "local"
            )
        selected_model = _normalize_text(thread_settings.model) or None
        if thread_settings.has_thread_config:
            routing_source = "thread_config"
        elif provider_hint_candidate and hint_allowed:
            routing_source = "request_hint"
        elif provider_hint_candidate and not hint_allowed:
            routing_source = "request_hint_fallback"
        else:
            routing_source = "runtime_default"
        provider_metadata = _safe_provider_metadata(
            selected_provider=selected_provider,
            selected_model=selected_model,
            routing_source=routing_source,
            provider_hint=provider_hint_text or None,
            settings=settings,
            requested_provider=requested_provider_for_routing,
        )
        provider_metadata["thread_completion"] = {
            "source_mode": thread_settings.source_mode,
            "reasoning_mode": thread_settings.reasoning_mode,
            "has_thread_config": thread_settings.has_thread_config,
        }
        _emit_proof_event(
            events=events,
            event_type="provider_selected",
            thread_id=resolved_thread_id,
            safe_metadata={
                "request_id": current_request_id,
                "provider_selected": provider_metadata["provider_selected"],
                "provider_reason": provider_metadata["provider_reason"],
                "provider_hint_used": provider_metadata["provider_hint_used"],
                "fallback_used": provider_metadata["fallback_used"],
                "provider_available": provider_metadata["available"],
                "provider_enabled": provider_metadata["enabled"],
            },
            tenant_id=owner_id,
        )

        retrieval_metadata: dict[str, Any] = {
            "retrieval_enabled": bool(retrieval_enabled),
            "enabled": bool(retrieval_enabled),
            "executed": False,
            "retrieval_status": "disabled",
            "status": "disabled",
            "absence_reason": "retrieval_disabled",
            "source_mode": thread_settings.source_mode,
            "widen_reason": None,
            "query_chars": 0,
            "query_hash": None,
            "result_count": 0,
            "source_ids": [],
            "source_labels": [],
            "source_content_hashes": [],
            "sources": [],
            "source_hit_counts": {},
            "proof_capable": False,
            "retrieval_summary": {
                "messages": 0,
                "semantic": 0,
                "docs": 0,
                "memory": 0,
                "graph": 0,
            },
        }
        retrieval_query_text = _normalize_text(retrieval_query) or cleaned_message
        if retrieval_enabled:
            _emit_proof_event(
                events=events,
                event_type="retrieval_started",
                thread_id=resolved_thread_id,
                safe_metadata={
                    "request_id": current_request_id,
                    "query_chars": len(retrieval_query_text),
                    "query_hash": _digest_text(retrieval_query_text),
                    "source_mode": thread_settings.source_mode,
                },
                tenant_id=owner_id,
            )
            try:
                retrieval_metadata = await _build_retrieval_proof(
                    chatlog_db=chatlog_db,
                    thread=thread,
                    thread_id=resolved_thread_id,
                    owner_id=owner_id,
                    query_text=retrieval_query_text,
                    source_mode=thread_settings.source_mode,
                )
            except Exception as exc:
                logger.warning(
                    "[core-loop-proof] retrieval proof failed thread_id=%s",
                    resolved_thread_id,
                    exc_info=True,
                )
                retrieval_metadata = {
                    "retrieval_enabled": True,
                    "enabled": True,
                    "executed": False,
                    "retrieval_status": "failed",
                    "status": "failed",
                    "absence_reason": "retrieval_proof_error",
                    "source_mode": thread_settings.source_mode,
                    "widen_reason": None,
                    "query_chars": len(retrieval_query_text),
                    "query_hash": _digest_text(retrieval_query_text),
                    "result_count": 0,
                    "source_ids": [],
                    "source_labels": [],
                    "source_content_hashes": [],
                    "sources": [],
                    "source_hit_counts": {},
                    "proof_capable": False,
                    "retrieval_summary": {
                        "messages": 0,
                        "semantic": 0,
                        "docs": 0,
                        "memory": 0,
                        "graph": 0,
                    },
                    "error": {
                        "type": exc.__class__.__name__,
                        "message": "retrieval proof failed",
                    },
                }
            _emit_proof_event(
                events=events,
                event_type="retrieval_completed",
                thread_id=resolved_thread_id,
                safe_metadata={
                    "request_id": current_request_id,
                    "retrieval_status": retrieval_metadata.get("status"),
                    "retrieval_executed": retrieval_metadata.get("executed"),
                    "proof_capable": retrieval_metadata.get("proof_capable"),
                    "source_hit_counts": retrieval_metadata.get("source_hit_counts"),
                    "absence_reason": retrieval_metadata.get("absence_reason"),
                },
                tenant_id=owner_id,
            )

        _emit_proof_event(
            events=events,
            event_type="response_started",
            thread_id=resolved_thread_id,
            safe_metadata={
                "request_id": current_request_id,
                "provider_selected": provider_metadata["provider_selected"],
                "retrieval_status": retrieval_metadata.get("status"),
            },
            tenant_id=owner_id,
        )

        assistant_content = (
            f"Core loop proof complete for thread {resolved_thread_id}. "
            f"provider={provider_metadata['provider_selected']} "
            f"retrieval={retrieval_metadata.get('status')} "
            f"events={len(events) + 1}"
        )
        assistant_message_id = chatlog_db.create_message(
            resolved_thread_id,
            "assistant",
            assistant_content,
            user_id=owner_id,
        )

        proof_state = {
            "request_id": current_request_id,
            "status": "completed",
            "thread_id": resolved_thread_id,
            "created_new": created_new,
            "message_count": int(chatlog_db.count_messages(resolved_thread_id) or 0),
            "last_event_id": None,
            "provider": provider_metadata,
            "retrieval": retrieval_metadata,
            "message_ids": {
                "user": user_message_id,
                "assistant": assistant_message_id,
            },
        }
        _emit_proof_event(
            events=events,
            event_type="response_completed",
            thread_id=resolved_thread_id,
            safe_metadata={
                "request_id": current_request_id,
                "assistant_message_id": assistant_message_id,
                "message_count": proof_state["message_count"],
                "status": proof_state["status"],
            },
            tenant_id=owner_id,
        )
        proof_state["last_event_id"] = events[-1]["event_id"] if events else None

        metadata_written = False
        metadata_payload = _merge_proof_metadata(thread, proof_state)
        update_metadata = getattr(chatlog_db, "update_thread_metadata", None)
        if callable(update_metadata):
            try:
                metadata_written = bool(
                    update_metadata(resolved_thread_id, metadata_payload)
                )
            except Exception:
                logger.debug(
                    "[core-loop-proof] thread metadata write failed thread_id=%s",
                    resolved_thread_id,
                    exc_info=True,
                )
        proof_state["metadata_written"] = metadata_written
        proof_state["metadata_keys"] = [CORE_LOOP_PROOF_METADATA_KEY]
        if not metadata_written:
            proof_state["status"] = "completed_degraded"

        updated_thread = None
        get_thread = getattr(chatlog_db, "get_chat_thread", None)
        if callable(get_thread):
            try:
                updated_thread = get_thread(resolved_thread_id)
            except Exception:
                logger.debug(
                    "[core-loop-proof] thread reload failed thread_id=%s",
                    resolved_thread_id,
                    exc_info=True,
                )
        thread_state = {
            "thread_id": resolved_thread_id,
            "created_at": thread.get("created_at"),
            "updated_at": (
                updated_thread.get("updated_at")
                if isinstance(updated_thread, dict)
                else thread.get("updated_at")
            ),
            "message_count": proof_state["message_count"],
            "last_event_id": proof_state["last_event_id"],
            "status": proof_state["status"],
        }
        provider_summary = {
            "selected": provider_metadata["provider_selected"],
            "reason": provider_metadata["provider_reason"],
            "provider_selected": provider_metadata["provider_selected"],
            "provider_reason": provider_metadata["provider_reason"],
            "provider_hint_used": provider_metadata["provider_hint_used"],
            "fallback_used": provider_metadata["fallback_used"],
        }
        assistant_message = {
            "id": assistant_message_id,
            "role": "assistant",
            "content": assistant_content,
        }
        retrieval_proof = dict(retrieval_metadata)

        return {
            "ok": True,
            "http_status": 200,
            "status": proof_state["status"],
            "request_id": current_request_id,
            "thread_id": resolved_thread_id,
            "thread_state": thread_state,
            "provider": provider_summary,
            "provider_metadata": provider_metadata,
            "retrieval_proof": retrieval_proof,
            "retrieval": retrieval_metadata,
            "assistant_message": assistant_message,
            "message": assistant_message,
            "events": events,
            "proof_record": proof_state,
        }
    except PermissionError as exc:
        _emit_proof_event(
            events=events,
            event_type="request_failed",
            thread_id=(
                int(thread["id"])
                if isinstance(thread, dict) and thread.get("id")
                else int(thread_id or 0) or 0
            ),
            safe_metadata={
                "request_id": current_request_id,
                "error_type": exc.__class__.__name__,
                "error_message": "forbidden",
                "error_code": "forbidden",
            },
            tenant_id=owner_id,
        )
        return _safe_failed_result(
            request_id=current_request_id,
            thread_id=thread_id,
            status_code=403,
            status="failed",
            error_code="forbidden",
            error_message=str(exc),
            events=events,
        )
    except Exception as exc:
        thread_event_id = (
            int(thread["id"])
            if isinstance(thread, dict) and thread.get("id")
            else int(thread_id or 0) or 0
        )
        _emit_proof_event(
            events=events,
            event_type="request_failed",
            thread_id=thread_event_id,
            safe_metadata={
                "request_id": current_request_id,
                "error_type": exc.__class__.__name__,
                "error_message": "core loop proof failed",
                "error_code": "core_loop_proof_failed",
            },
            tenant_id=owner_id,
        )
        logger.exception(
            "[core-loop-proof] lane failed request_id=%s", current_request_id
        )
        return _safe_failed_result(
            request_id=current_request_id,
            thread_id=thread_event_id,
            status_code=500,
            status="failed",
            error_code="core_loop_proof_failed",
            error_message="Core loop proof failed",
            events=events,
        )


__all__ = [
    "CORE_LOOP_PROOF_ENV",
    "CORE_LOOP_PROOF_METADATA_KEY",
    "CORE_LOOP_PROOF_THREAD_SUMMARY",
    "CORE_LOOP_PROOF_THREAD_TITLE",
    "core_loop_proof_enabled",
    "run_core_loop_proof",
]
