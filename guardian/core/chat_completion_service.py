"""Shared chat completion assembly/execution service.

This module centralizes completion orchestration so API routes/workers do not
fork context assembly, prompt construction, provider routing, or persistence.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Callable, Dict, Optional, Sequence
from urllib.parse import unquote

from fastapi import HTTPException

from guardian.cognition.prompts import (
    build_context_system_message as _compat_build_context_system_message,
)
from guardian.cognition.prompts import build_context_system_message_with_meta
from guardian.command_bus.contracts import (
    ActorSpec,
    BoundedToolTurnInvocation,
    BoundedToolTurnResult,
    CommandBusInvokeResult,
    InvokeArguments,
    InvokeRequest,
)
from guardian.command_bus.invoke import execute_invoke
from guardian.command_bus.store import CommandBusStore
from guardian.context.broker import ContextBroker
from guardian.context.context_directive_resolver import (
    CONTEXT_REQUEST_PLANS_ORIGIN_KEY,
    SUPPORTED_CONTEXT_REQUEST_CONNECTOR_ID,
    SUPPORTED_CONTEXT_REQUEST_INVOCATION,
    SUPPORTED_CONTEXT_REQUEST_KIND,
)
from guardian.context.retrieval_router_policy import (
    RETRIEVAL_OVERRIDE_CONVERSATION,
    RETRIEVAL_OVERRIDE_NONE,
    RETRIEVAL_OVERRIDE_PERSONAL_KNOWLEDGE,
    RETRIEVAL_OVERRIDE_PROJECT,
    SOURCE_MODE_CONVERSATION,
    SOURCE_MODE_OBSIDIAN_ONLY,
    SOURCE_MODE_PERSONAL_KNOWLEDGE,
    SOURCE_MODE_PROJECT,
    SOURCE_MODE_WORKSPACE,
    normalize_retrieval_override_mode,
    normalize_source_mode,
    resolve_context_assembly_policy,
    resolve_retrieval_plan,
    source_mode_boundary_label,
)
from guardian.core import dependencies, event_bus
from guardian.core.ai_router import (
    _encode_image_url_to_base64,
    _image_turn_vision_unsupported_detail,
    build_openai_vision_content,
    chat_with_ai,
    messages_contain_image_payload,
    normalize_completion_output,
    resolve_local_execution_model,
    resolve_model_vision_capability_state,
    stream_local,
)
from guardian.core.candidate_trace_store import store_candidate_trace
from guardian.core.chat_attachments import (
    extract_attachments_and_text,
    render_content_for_inference,
)
from guardian.core.config import (
    LLMConfigError,
    get_settings,
    validate_llm_config,
)
from guardian.core.llm_catalog import first_enabled_provider
from guardian.core.provider_registry import (
    default_model_for_provider,
    normalize_model_id,
    normalize_provider,
    resolve_provider_for_model,
)
from guardian.obsidian.indexer import OBSIDIAN_NAMESPACE
from guardian.protocol_tokens import (
    ContextRequestStatus,
    ErrorCode,
    ImageRoutingPath,
    LoopStopReason,
    ToolLoopStopReason,
    ToolTurnState,
    TraceSnapshotAbsenceReason,
    TraceSuppressionReason,
)
from guardian.queue.redis_queue import (
    CANDIDATE_INGEST_QUEUE,
    get_redis_connection,
)
from guardian.tasks.types import ChatCompletionTask, TaskLifecycleState
from guardian.vector.store import VectorStore

try:  # pragma: no cover - import is runtime-scoped for workspace freshness
    from backend.rag.embedder import Embedder as _WorkspaceVectorEmbedder
except Exception:  # pragma: no cover - fallback when embedder import fails
    _WorkspaceVectorEmbedder = None

logger = logging.getLogger(__name__)
RETRIEVAL_PLAN_TRACE_KEY = "retrieval_plan"
DEBUG_LATEST_COMPLETION_TASK_ID_METADATA_KEY = "debug_latest_completion_task_id"
DEBUG_RAG_TRACE_CANDIDATE_METADATA_KEY = "debug_rag_trace_candidate"
DEBUG_LATEST_RAG_TRACE_METADATA_KEY = "debug_latest_rag_trace"
_LOCAL_IMAGE_CAPTIONER_MODEL_NAME = "Salesforce/blip-image-captioning-base"
_LOCAL_IMAGE_CAPTIONER: tuple[Any, Any] | None = None
_LOCAL_IMAGE_CAPTIONER_ATTEMPTED = False

try:  # pragma: no cover - prompts are optional in some deployments
    from guardian.cognition.system_prompt_builder import (
        build_guardian_system_prompt,
    )
except Exception:  # pragma: no cover - optional dependency
    build_guardian_system_prompt = None

try:  # pragma: no cover - profile store may be unavailable in some tests
    from guardian.cognition.system_profiles.resolver import (
        resolve_thread_system_profile,
    )
except Exception:  # pragma: no cover - optional dependency
    resolve_thread_system_profile = None


class ChatTaskCancelled(RuntimeError):
    """Raised when a caller-provided cancellation check aborts completion."""


class ToolLoopExecutionError(RuntimeError):
    """Raised when the bounded tool loop cannot complete safely."""

    def __init__(self, message: str, *, metadata: dict[str, Any] | None = None):
        self.metadata = dict(metadata or {})
        super().__init__(message)


def _extract_latest_turn_message_id(task: Any) -> int | None:
    raw_value = getattr(task, "latest_turn_message_id", None)
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _command_bus_app() -> Any:
    from guardian.guardian_api import app as guardian_app

    return guardian_app


def _tool_loop_identity_fields(
    *,
    task: ChatCompletionTask,
    tool_turn_id: str | None,
    tool_turn_state: str,
    loop_stop_reason: str,
    command_run_id: str | None,
    message_id: int | None = None,
) -> dict[str, Any]:
    request_id = str(getattr(task, "task_id", "") or "").strip() or None
    latest_turn_message_id = _extract_latest_turn_message_id(task)
    resolved_message_id = (
        message_id if message_id is not None else latest_turn_message_id
    )
    payload: dict[str, Any] = {
        "messageId": resolved_message_id,
        "requestId": request_id,
        "toolTurnId": tool_turn_id,
        "toolTurnState": tool_turn_state,
        "loopStopReason": loop_stop_reason,
        "commandRunId": command_run_id,
        "message_id": resolved_message_id,
        "request_id": request_id,
        "tool_turn_id": tool_turn_id,
        "tool_turn_state": tool_turn_state,
        "loop_stop_reason": loop_stop_reason,
        "command_run_id": command_run_id,
    }
    return payload


def _tool_turn_invoke_arguments(raw: Any) -> InvokeArguments:
    if isinstance(raw, InvokeArguments):
        return raw
    if isinstance(raw, dict):
        if any(
            key in raw for key in ("path_params", "query", "headers", "body")
        ):
            return InvokeArguments(
                path_params=dict(raw.get("path_params") or {}),
                query=dict(raw.get("query") or {}),
                headers=dict(raw.get("headers") or {}),
                body=raw.get("body"),
            )
        return InvokeArguments(body=dict(raw))
    return InvokeArguments(body=raw)


def _sanitize_command_run_payload(payload: dict[str, Any]) -> dict[str, Any]:
    sanitized = {
        "run_id": payload.get("run_id"),
        "status": payload.get("status"),
        "invoke_version": payload.get("invoke_version"),
        "manifest_version": payload.get("manifest_version"),
        "events_url": payload.get("events_url"),
        "error": payload.get("error"),
        "warning": payload.get("warning"),
        "policy_warnings": payload.get("policy_warnings"),
        "inline_result": payload.get("inline_result"),
    }
    return {key: value for key, value in sanitized.items() if value is not None}


def _tool_result_prompt(
    *,
    tool_turn_id: str,
    decision: dict[str, Any],
    command_result: dict[str, Any],
) -> str:
    payload = {
        "tool_turn_id": tool_turn_id,
        "command_id": decision.get("command_id"),
        "arguments": decision.get("arguments") or {},
        "command_result": _sanitize_command_run_payload(command_result),
        "instruction": (
            "Use the tool result to answer the user directly. "
            "Do not choose another tool."
        ),
    }
    return "Tool result injection:\n" + json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _append_tool_result_message(
    messages: list[dict[str, Any]],
    *,
    tool_turn_id: str,
    decision: dict[str, Any],
    command_result: dict[str, Any],
) -> list[dict[str, Any]]:
    next_messages = [
        dict(message)
        for message in (messages or [])
        if isinstance(message, dict)
    ]
    next_messages.append(
        {
            "role": "system",
            "content": _tool_result_prompt(
                tool_turn_id=tool_turn_id,
                decision=decision,
                command_result=command_result,
            ),
        }
    )
    return next_messages


def _tool_turn_completion_result(
    *,
    task: ChatCompletionTask,
    assistant_text: str,
    provider: str,
    model: str,
    bundle: dict[str, Any] | None,
    trace: dict[str, Any] | None,
    payload_summary: dict[str, Any],
    tool_turn_id: str | None,
    tool_turn_state: str,
    loop_stop_reason: str,
    command_run_id: str | None,
    command_status: str | None = None,
    command_error: dict[str, Any] | None = None,
    message_id: int | None = None,
    execution: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "assistant_text": assistant_text,
        "provider": provider,
        "model": model,
        "bundle": bundle,
        "trace": trace,
        "thread_id": task.thread_id,
        "payload_summary": payload_summary,
        "toolTurnId": tool_turn_id,
        "toolTurnState": tool_turn_state,
        "loopStopReason": loop_stop_reason,
        "commandRunId": command_run_id,
        "tool_turn_id": tool_turn_id,
        "tool_turn_state": tool_turn_state,
        "loop_stop_reason": loop_stop_reason,
        "command_run_id": command_run_id,
    }
    result.update(
        _tool_loop_identity_fields(
            task=task,
            tool_turn_id=tool_turn_id,
            tool_turn_state=tool_turn_state,
            loop_stop_reason=loop_stop_reason,
            command_run_id=command_run_id,
            message_id=message_id,
        )
    )
    if execution is not None:
        result["execution"] = execution
    if command_status is not None:
        result["command_status"] = command_status
    if command_error is not None:
        result["command_error"] = command_error
    return result


def _execute_completion_attempt(
    *,
    task: ChatCompletionTask,
    messages_for_llm: list[dict[str, Any]],
    provider: str,
    model: str,
    bundle: dict[str, Any] | None,
    token_callback: Callable[[str], None] | None = None,
    chunk_callback: Callable[[str], None] | None = None,
    cancel_check: Callable[[], bool] | None = None,
) -> Any:
    if callable(cancel_check) and cancel_check():
        raise ChatTaskCancelled()

    reasoning_mode = getattr(task, "reasoning_mode", None)
    temperature = getattr(task, "temperature", None)
    settings = get_settings()

    if provider == "local":
        stream = stream_local(
            messages_for_llm,
            model,
            reasoning_mode=reasoning_mode,
            settings=settings,
            temperature=temperature,
        )
        if isinstance(stream, str):
            return stream

        collected: list[str] = []
        for chunk in stream:
            if callable(cancel_check) and cancel_check():
                raise ChatTaskCancelled()
            text = str(chunk or "")
            if not text:
                continue
            collected.append(text)
            if token_callback:
                token_callback(text)
            if callable(chunk_callback):
                chunk_callback(text)
        return "".join(collected)

    return chat_with_ai(
        messages_for_llm,
        model=model,
        provider=provider,
        reasoning_mode=reasoning_mode,
        temperature=temperature,
        settings=settings,
        prompt_meta=(bundle or {}).get("_prompt_meta")
        if isinstance(bundle, dict)
        else None,
    )


async def _build_messages_for_llm_compat(
    task: ChatCompletionTask,
    *,
    user_id: str | None = None,
    enable_memory_preselection_trace: bool | None = None,
    enable_memory_preselection_active: bool | None = None,
    memory_preselection_candidate_headers: Sequence[dict[str, Any]] | None = None,
    memory_preselection_persona_id: str | None = None,
    memory_preselection_identity_depth: str | None = None,
    memory_preselection_include_diary_excluded: bool | None = None,
) -> tuple[
    list[dict[str, str]],
    str,
    str,
    dict[str, Any],
    dict[str, Any] | None,
]:
    builder = build_messages_for_llm
    try:
        signature = inspect.signature(builder)
    except (TypeError, ValueError):
        signature = None
    accepts_kwargs = False
    if signature is not None:
        accepts_kwargs = any(
            parameter.kind == inspect.Parameter.VAR_KEYWORD
            for parameter in signature.parameters.values()
        )

    def _accepts(name: str) -> bool:
        return accepts_kwargs or (
            signature is not None and name in signature.parameters
        )

    call_kwargs: dict[str, Any] = {}
    if _accepts("user_id"):
        call_kwargs["user_id"] = user_id
    if (
        enable_memory_preselection_trace is not None
        and _accepts("enable_memory_preselection_trace")
    ):
        call_kwargs["enable_memory_preselection_trace"] = bool(
            enable_memory_preselection_trace
        )
    if (
        enable_memory_preselection_active is not None
        and _accepts("enable_memory_preselection_active")
    ):
        call_kwargs["enable_memory_preselection_active"] = bool(
            enable_memory_preselection_active
        )
    if (
        memory_preselection_candidate_headers is not None
        and _accepts("memory_preselection_candidate_headers")
    ):
        call_kwargs["memory_preselection_candidate_headers"] = (
            memory_preselection_candidate_headers
        )
    if (
        memory_preselection_persona_id is not None
        and _accepts("memory_preselection_persona_id")
    ):
        call_kwargs["memory_preselection_persona_id"] = (
            memory_preselection_persona_id
        )
    if (
        memory_preselection_identity_depth is not None
        and _accepts("memory_preselection_identity_depth")
    ):
        call_kwargs["memory_preselection_identity_depth"] = (
            memory_preselection_identity_depth
        )
    if (
        memory_preselection_include_diary_excluded is not None
        and _accepts("memory_preselection_include_diary_excluded")
    ):
        call_kwargs["memory_preselection_include_diary_excluded"] = bool(
            memory_preselection_include_diary_excluded
        )

    return await builder(task, **call_kwargs)


def build_context_system_message(bundle: dict[str, Any] | None) -> str | None:
    """Backward-compatible helper returning only the rendered context message.

    The canonical implementation now lives in
    ``build_context_system_message_with_meta`` inside cognition.prompts. This
    wrapper preserves the older symbol expected by worker shims/tests without
    forking prompt assembly logic.
    """

    return _compat_build_context_system_message(bundle)


def _estimate_tokens(text: str | None) -> int:
    if not text:
        return 0
    try:
        length = len(text)
    except Exception:
        return 0
    return max(1, length // 4)


def _source_mode_from_origin(origin: Any) -> str:
    text = str(origin or "").strip()
    if not text:
        return SOURCE_MODE_PROJECT
    for segment in text.split("|")[1:]:
        key, _, value = segment.partition("=")
        if key.strip() == "source_mode":
            return normalize_source_mode(value.strip())
    return SOURCE_MODE_PROJECT


def _requested_source_mode_from_task(task: Any) -> str | None:
    raw_requested_source_mode = getattr(task, "requested_source_mode", None)
    if raw_requested_source_mode is not None:
        requested_source_mode = str(raw_requested_source_mode).strip()
        if requested_source_mode:
            return normalize_source_mode(requested_source_mode)
    origin_source_mode = _source_mode_from_origin(getattr(task, "origin", None))
    if origin_source_mode:
        return normalize_source_mode(origin_source_mode)
    return None


def _slash_intent_from_origin(origin: Any) -> dict[str, Any] | None:
    text = str(origin or "").strip()
    if not text:
        return None

    for segment in text.split("|")[1:]:
        key, _, value = segment.partition("=")
        if key.strip() != "slash_intent":
            continue
        raw_value = unquote(value.strip())
        if not raw_value:
            return None
        try:
            parsed = json.loads(raw_value)
        except Exception:
            logger.debug(
                "[chat-completion] failed to decode slash intent origin segment",
                exc_info=True,
            )
            return None
        return parsed if isinstance(parsed, dict) else None
    return None


def _retrieval_override_from_origin(origin: Any) -> dict[str, Any] | None:
    text = str(origin or "").strip()
    if not text:
        return None

    for segment in text.split("|")[1:]:
        key, _, value = segment.partition("=")
        if key.strip() != "retrieval_override":
            continue
        raw_value = unquote(value.strip())
        if not raw_value:
            return None
        try:
            parsed = json.loads(raw_value)
        except Exception:
            logger.debug(
                "[chat-completion] failed to decode retrieval override origin segment",
                exc_info=True,
            )
            return None
        return parsed if isinstance(parsed, dict) else None
    return None


def _context_request_plans_from_origin(origin: Any) -> list[dict[str, Any]]:
    text = str(origin or "").strip()
    if not text:
        return []

    for segment in text.split("|")[1:]:
        key, _, value = segment.partition("=")
        if key.strip() != CONTEXT_REQUEST_PLANS_ORIGIN_KEY:
            continue
        raw_value = unquote(value.strip())
        if not raw_value:
            return []
        try:
            parsed = json.loads(raw_value)
        except Exception:
            logger.debug(
                "[chat-completion] failed to decode context request plans origin segment",
                exc_info=True,
            )
            return []
        if isinstance(parsed, list):
            return [item for item in parsed if isinstance(item, dict)]
        if isinstance(parsed, dict):
            nested = parsed.get("context_request_plans") or parsed.get("plans")
            if isinstance(nested, list):
                return [item for item in nested if isinstance(item, dict)]
        return []
    return []


def _supported_obsidian_context_request_plans(
    task: Any,
) -> list[dict[str, Any]]:
    raw_plans = getattr(task, "context_request_plans", None)
    if raw_plans is None:
        raw_plans = _context_request_plans_from_origin(
            getattr(task, "origin", None)
        )
    if not isinstance(raw_plans, list):
        return []

    supported: list[dict[str, Any]] = []
    for plan in raw_plans:
        if not isinstance(plan, dict):
            continue
        if not isinstance(parsed, list):
            return []
        return [dict(plan) for plan in parsed if isinstance(plan, dict)]
    return []


def _supported_obsidian_context_request_plans(
    task: Any,
) -> list[dict[str, Any]]:
    supported_plans: list[dict[str, Any]] = []
    for plan in _context_request_plans_from_origin(
        getattr(task, "origin", None)
    ):
        request_kind = (
            str(plan.get("request_kind") or plan.get("requestKind") or "")
            .strip()
            .lower()
        )
        connector_id = (
            str(plan.get("connector_id") or plan.get("connectorId") or "")
            .strip()
            .lower()
        )
        invocation = str(plan.get("invocation") or "").strip().lower()
        query_text = str(
            plan.get("query_text") or plan.get("queryText") or ""
        ).strip()
        if (
            request_kind != SUPPORTED_CONTEXT_REQUEST_KIND
            or connector_id != SUPPORTED_CONTEXT_REQUEST_CONNECTOR_ID
            or invocation != SUPPORTED_CONTEXT_REQUEST_INVOCATION
            or not query_text
        ):
            continue

        normalized_plan = dict(plan)
        normalized_plan["request_kind"] = SUPPORTED_CONTEXT_REQUEST_KIND
        normalized_plan["connector_id"] = SUPPORTED_CONTEXT_REQUEST_CONNECTOR_ID
        normalized_plan["invocation"] = SUPPORTED_CONTEXT_REQUEST_INVOCATION
        normalized_plan["query_text"] = query_text
        normalized_plan["status"] = (
            str(normalized_plan.get("status") or "").strip()
            or ContextRequestStatus.ACCEPTED_NOT_EXECUTED.value
        )
        normalized_plan["execution_required"] = False
        supported_plans.append(normalized_plan)
    return supported_plans


def _context_request_result_record(
    plan: dict[str, Any],
    *,
    status: str,
    result_count: int,
    injected: bool,
    error: str | None = None,
) -> dict[str, Any]:
    record = {
        "request_kind": str(
            plan.get("request_kind") or plan.get("requestKind") or ""
        ).strip()
        or SUPPORTED_CONTEXT_REQUEST_KIND,
        "connector_id": str(
            plan.get("connector_id") or plan.get("connectorId") or ""
        ).strip()
        or SUPPORTED_CONTEXT_REQUEST_CONNECTOR_ID,
        "invocation": str(plan.get("invocation") or "").strip()
        or SUPPORTED_CONTEXT_REQUEST_INVOCATION,
        "query_text": str(
            plan.get("query_text") or plan.get("queryText") or ""
        ).strip(),
        "status": status,
        "result_count": int(result_count),
        "injected": bool(injected),
    }
    if error:
        record["error"] = error
    return record


def _sanitize_context_request_error(exc: Exception) -> str:
    text = re.sub(r"/[^\s]+", "[redacted]", str(exc))
    text = re.sub(r"[A-Za-z]:\\\\[^\s]+", "[redacted]", text)
    return f"{exc.__class__.__name__}: {text}"


async def _apply_context_request_plans(
    *,
    broker: ContextBroker,
    task: Any,
    bundle: dict[str, Any],
    user_id: str,
    project_id: int | None,
) -> list[dict[str, Any]]:
    if not isinstance(bundle, dict):
        return []

    context_request_results: list[dict[str, Any]] = []
    connector_context = list(bundle.get("connector_context") or [])

    for plan in _context_request_plans_from_origin(
        getattr(task, "origin", None)
    ):
        request_kind = (
            str(plan.get("request_kind") or plan.get("requestKind") or "")
            .strip()
            .lower()
        )
        connector_id = (
            str(plan.get("connector_id") or plan.get("connectorId") or "")
            .strip()
            .lower()
        )
        invocation = str(plan.get("invocation") or "").strip().lower()
        status = str(plan.get("status") or "").strip().lower()
        if request_kind != "read_only_context_request":
            continue
        if connector_id != "obsidian":
            continue
        if invocation != "turn_scoped":
            continue
        if status != ContextRequestStatus.ACCEPTED_NOT_EXECUTED.value:
            continue

        supported = (
            request_kind == SUPPORTED_CONTEXT_REQUEST_KIND
            and connector_id == SUPPORTED_CONTEXT_REQUEST_CONNECTOR_ID
            and invocation == SUPPORTED_CONTEXT_REQUEST_INVOCATION
        )

        if not supported:
            context_request_results.append(
                _context_request_result_record(
                    plan,
                    status=ContextRequestStatus.FAILED.value,
                    result_count=0,
                    injected=False,
                    error="unsupported_context_request_plan",
                )
            )
            continue

        query_text = str(
            plan.get("query_text") or plan.get("queryText") or ""
        ).strip()
        normalized_plan = {
            "request_kind": SUPPORTED_CONTEXT_REQUEST_KIND,
            "connector_id": SUPPORTED_CONTEXT_REQUEST_CONNECTOR_ID,
            "invocation": SUPPORTED_CONTEXT_REQUEST_INVOCATION,
            "query_text": query_text,
            "status": ContextRequestStatus.ACCEPTED_NOT_EXECUTED.value,
            "execution_required": False,
        }

        if not query_text:
            context_request_results.append(
                _context_request_result_record(
                    normalized_plan,
                    status=ContextRequestStatus.FAILED.value,
                    result_count=0,
                    injected=False,
                    error="blank_query_text",
                )
            )
            continue

        try:
            items = await broker.retrieve_obsidian_context_command(
                query=query_text,
                user_id=user_id,
                project_id=project_id,
                k=int(plan.get("k") or plan.get("limit") or 4),
                retrieval_policy=plan.get("retrieval_policy")
                if isinstance(plan.get("retrieval_policy"), dict)
                else None,
            )
        except Exception as exc:
            context_request_results.append(
                _context_request_result_record(
                    normalized_plan,
                    status=ContextRequestStatus.FAILED.value,
                    result_count=0,
                    injected=False,
                    error=_sanitize_context_request_error(exc),
                )
            )
            continue

        item_count = len(items)
        if item_count:
            connector_context.extend(items)
            status = ContextRequestStatus.EXECUTED.value
        else:
            status = ContextRequestStatus.NO_RESULTS.value
        context_request_results.append(
            _context_request_result_record(
                normalized_plan,
                status=status,
                result_count=item_count,
                injected=bool(item_count),
            )
        )

    bundle["connector_context"] = connector_context
    bundle["context_request_results"] = context_request_results
    return context_request_results


def _image_attachment_count_from_origin(origin: Any) -> int | None:
    text = str(origin or "").strip()
    if not text:
        return None

    for segment in text.split("|")[1:]:
        key, _, value = segment.partition("=")
        if key.strip() != "image_attachment_count":
            continue
        try:
            count = int(str(value).strip())
        except (TypeError, ValueError):
            return None
        return count if count > 0 else None
    return None


def _retrieval_override_from_task(task: Any) -> dict[str, Any] | None:
    raw_override = getattr(task, "retrieval_override", None)
    if raw_override is None:
        raw_override = _retrieval_override_from_origin(
            getattr(task, "origin", None)
        )
    return _normalize_retrieval_override(raw_override)


def _effective_source_mode_for_broker_assembly(
    source_mode: Any,
    retrieval_override: dict[str, Any] | None,
) -> str:
    effective_source_mode = normalize_source_mode(source_mode)
    if effective_source_mode == SOURCE_MODE_OBSIDIAN_ONLY:
        return effective_source_mode
    if not isinstance(retrieval_override, dict):
        return effective_source_mode

    raw_mode = retrieval_override.get("mode")
    normalized_mode = str(raw_mode or "").strip().lower()
    if not normalized_mode or normalized_mode == RETRIEVAL_OVERRIDE_NONE:
        return effective_source_mode
    if normalized_mode == RETRIEVAL_OVERRIDE_PROJECT:
        return SOURCE_MODE_PROJECT
    if normalized_mode == RETRIEVAL_OVERRIDE_PERSONAL_KNOWLEDGE:
        return SOURCE_MODE_PERSONAL_KNOWLEDGE
    if normalized_mode == RETRIEVAL_OVERRIDE_CONVERSATION:
        return SOURCE_MODE_CONVERSATION
    if normalize_retrieval_override_mode(raw_mode) is None:
        logger.debug(
            "[chat-completion] ignoring unsupported retrieval override mode=%s",
            raw_mode,
        )
        return effective_source_mode

    return effective_source_mode


def _normalize_retrieval_override(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if isinstance(value, dict):
        override = dict(value)
    else:
        try:
            override = dict(vars(value))
        except Exception:
            return None
    if not override:
        return None
    mode = _clean_thread_config_text(override.get("mode"))
    if mode is not None:
        override["mode"] = mode.lower()
    return override


def _retrieval_override_mode(value: Any) -> str | None:
    override = _normalize_retrieval_override(value)
    if not override:
        return None
    mode = _clean_thread_config_text(override.get("mode"))
    return mode.lower() if mode else None


def _resolve_effective_source_mode_for_assembly(
    source_mode: Any,
    retrieval_override: Any,
) -> str:
    normalized_source_mode = normalize_source_mode(source_mode)
    if normalized_source_mode == SOURCE_MODE_OBSIDIAN_ONLY:
        return normalized_source_mode
    override_mode = _retrieval_override_mode(retrieval_override)
    if override_mode == "project":
        return "project"
    if override_mode == "personal_knowledge":
        return "personal_knowledge"
    if override_mode in {"none", "conversation"}:
        return normalized_source_mode
    return normalized_source_mode


def _broker_memory_preselection_kwargs(
    *,
    enable_memory_preselection_trace: bool | None = None,
    enable_memory_preselection_active: bool | None = None,
    memory_preselection_candidate_headers: Sequence[dict[str, Any]] | None = None,
    memory_preselection_persona_id: str | None = None,
    memory_preselection_identity_depth: str | None = None,
    memory_preselection_include_diary_excluded: bool | None = None,
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {}
    if enable_memory_preselection_trace is True:
        kwargs["enable_memory_preselection_trace"] = True
    if enable_memory_preselection_active is True:
        kwargs["enable_memory_preselection_active"] = True
    if memory_preselection_candidate_headers is not None:
        kwargs["memory_preselection_candidate_headers"] = (
            memory_preselection_candidate_headers
        )
    if memory_preselection_persona_id is not None:
        kwargs["memory_preselection_persona_id"] = (
            memory_preselection_persona_id
        )
    if memory_preselection_identity_depth is not None:
        kwargs["memory_preselection_identity_depth"] = (
            memory_preselection_identity_depth
        )
    if memory_preselection_include_diary_excluded is not None:
        kwargs["memory_preselection_include_diary_excluded"] = bool(
            memory_preselection_include_diary_excluded
        )
    return kwargs


def _task_routing_debug_metadata(task: Any) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    slash_intent = getattr(task, "slash_intent", None)
    if slash_intent is None:
        slash_intent = _slash_intent_from_origin(getattr(task, "origin", None))
    elif isinstance(slash_intent, str):
        slash_intent = _clean_thread_config_text(slash_intent)
    if slash_intent is not None:
        metadata["slash_intent"] = slash_intent
    retrieval_override = _retrieval_override_from_task(task)
    if retrieval_override is not None:
        metadata["retrieval_override"] = retrieval_override
    image_attachment_count = _image_attachment_count_from_origin(
        getattr(task, "origin", None)
    )
    if image_attachment_count is not None:
        metadata["image_attachment_count"] = image_attachment_count
    return metadata


def _completion_request_id(task: Any) -> str:
    request_id = str(getattr(task, "request_id", "") or "").strip()
    if request_id:
        return request_id
    return str(getattr(task, "task_id", "") or "").strip()


def _build_candidate_trace(
    task: Any,
    *,
    assistant_text: str,
    provider: str | None,
    model: str | None,
) -> dict[str, Any] | None:
    request_id = _completion_request_id(task)
    thread_id = str(getattr(task, "thread_id", "") or "").strip()
    if not request_id or not thread_id:
        return None
    return {
        "thread_id": thread_id,
        "request_id": request_id,
        "candidates": [
            {
                "content": assistant_text,
                "provider": provider,
                "model": model,
                "selected": True,
            }
        ],
        "selection_strategy": "single_candidate",
        "created_at": datetime.now(UTC).isoformat(),
    }


def _enqueue_candidate_ingest(task_payload: dict[str, Any]) -> None:
    redis = get_redis_connection()
    redis.rpush(CANDIDATE_INGEST_QUEUE, json.dumps(task_payload, default=str))


def _tool_loop_observability(
    task: Any,
    *,
    tool_turn_state: ToolTurnState = ToolTurnState.IDLE,
    loop_stop_reason: LoopStopReason = LoopStopReason.MODEL_FINAL_ANSWER,
    tool_turn_id: str | None = None,
    command_run_id: str | None = None,
) -> dict[str, Any]:
    return {
        "messageId": _coerce_message_id(
            getattr(task, "latest_turn_message_id", None)
        ),
        "requestId": _completion_request_id(task),
        "toolTurnId": tool_turn_id,
        "toolTurnState": tool_turn_state.value,
        "loopStopReason": loop_stop_reason.value,
        "commandRunId": command_run_id,
    }


def _resolve_command_bus_app() -> Any:
    from guardian.guardian_api import app as guardian_app

    return guardian_app


def _build_tool_result_reinjection_message(
    *,
    tool_loop: dict[str, Any],
    command_result: dict[str, Any],
    tool_decision: dict[str, Any],
) -> dict[str, str]:
    payload = {
        "tool_loop": dict(tool_loop),
        "command_result": dict(command_result),
        "tool_decision": dict(tool_decision),
    }
    return {
        "role": "system",
        "content": (
            "Bounded tool result for one final assistant answer:\n"
            f"{json.dumps(payload, default=str, sort_keys=True)}"
        ),
    }


def _attach_tool_loop_metadata(
    payload_summary: dict[str, Any],
    *,
    tool_loop: dict[str, Any],
    request_id: str,
) -> None:
    payload_summary["tool_loop"] = dict(tool_loop)
    payload_summary["command_run_id"] = tool_loop.get("commandRunId")
    payload_summary["tool_turn_state"] = tool_loop.get("toolTurnState")
    payload_summary["loop_stop_reason"] = tool_loop.get("loopStopReason")
    payload_summary["tool_turn_id"] = tool_loop.get("toolTurnId")
    payload_summary["request_id"] = request_id
    payload_summary["message_id"] = tool_loop.get("messageId")


def _workspace_completion_vector_store() -> VectorStore:
    """Build a fresh vector-store handle for workspace-scoped completions."""
    store = VectorStore()
    if _WorkspaceVectorEmbedder is None:
        return store
    try:
        store.embedder = _WorkspaceVectorEmbedder(
            store=store.store,
            chroma_path=store.chroma_path,
            collection=store.collection,
        )
        store._embedder_factory_token = id(_WorkspaceVectorEmbedder)
    except Exception:
        logger.debug(
            "[chat-completion] fresh workspace vector store rebuild failed",
            exc_info=True,
        )
    return store
    payload_summary["requestId"] = request_id
    payload_summary["messageId"] = tool_loop.get("messageId")


def _execute_bounded_tool_turn(
    *,
    task: Any,
    tool_decision: dict[str, Any],
    request_id: str,
    tool_turn_id: str,
    messages_for_llm: list[dict[str, str]],
    provider: str,
    model: str,
    reasoning_mode: Any,
    temperature: Any,
    token_callback: Callable[[str], None] | None,
    chunk_callback: Callable[[str], None] | None,
) -> tuple[str, dict[str, Any], dict[str, Any]]:
    command_id = str(tool_decision.get("command_id") or "").strip()
    arguments = tool_decision.get("arguments") or {}
    tool_loop = _tool_loop_observability(
        task,
        tool_turn_state=ToolTurnState.COMMAND_DISPATCHED,
        loop_stop_reason=LoopStopReason.TOOL_TURN_COMPLETED,
        tool_turn_id=tool_turn_id,
    )

    store = CommandBusStore(db=getattr(dependencies, "chatlog_db", None))
    invoke_request = InvokeRequest(
        invoke_version="1.0",
        command_id=command_id,
        actor={
            "kind": "human",
            "id": str(getattr(task, "user_id", "") or "").strip() or "local",
        },
        arguments=InvokeArguments.model_validate(arguments),
        idempotency_key=f"{request_id}:{tool_turn_id}",
    )
    command_status = "failed"
    try:
        command_bus_result = asyncio.run(
            execute_invoke(
                payload=invoke_request,
                auth_subject=str(getattr(task, "user_id", "") or "").strip()
                or "local",
                inbound_headers={},
                store=store,
                app=_resolve_command_bus_app(),
                execution_lane="tools",
                allow_write_execution=True,
                confirmation_granted=False,
            )
        )
        command_result = CommandBusInvokeResult.model_validate(
            command_bus_result
        ).model_dump(mode="json")
        tool_loop["commandRunId"] = command_result["run_id"]

        command_status = str(command_result.get("status") or "").strip().lower()
        if command_status == "blocked":
            tool_loop["toolTurnState"] = ToolTurnState.FAILED.value
            tool_loop["loopStopReason"] = LoopStopReason.TOOL_TURN_BLOCKED.value
        elif command_status == "failed":
            tool_loop["toolTurnState"] = ToolTurnState.FAILED.value
            tool_loop["loopStopReason"] = LoopStopReason.TOOL_TURN_FAILED.value
        else:
            tool_loop["toolTurnState"] = ToolTurnState.COMPLETED.value
    except Exception as exc:
        command_result = {
            "run_id": None,
            "status": "failed",
            "error": str(exc),
            "events_url": None,
            "warning": None,
            "policy_warnings": [],
        }
        tool_loop["toolTurnState"] = ToolTurnState.FAILED.value
        tool_loop["loopStopReason"] = LoopStopReason.TOOL_TURN_FAILED.value

    followup_messages = list(messages_for_llm)
    followup_messages.append(
        _build_tool_result_reinjection_message(
            tool_loop=tool_loop,
            command_result=command_result,
            tool_decision=tool_decision,
        )
    )
    final_raw_output = chat_with_ai(
        followup_messages,
        model=model,
        provider=provider,
        reasoning_mode=reasoning_mode,
        temperature=temperature,
        prompt_meta=None,
    )
    final_normalized = normalize_completion_output(final_raw_output)
    if final_normalized["kind"] == "assistant":
        final_text = str(final_normalized.get("assistant_text") or "")
        if final_text.strip() and token_callback:
            token_callback(final_text)
        if command_status not in {"blocked", "failed"}:
            tool_loop[
                "loopStopReason"
            ] = LoopStopReason.TOOL_TURN_COMPLETED.value
        return final_text, tool_loop, command_result

    def _apply_tool_turn_limit() -> None:
        if tool_loop["toolTurnState"] not in {
            ToolTurnState.FAILED.value,
            ToolTurnState.COMMAND_DISPATCHED.value,
        }:
            tool_loop["toolTurnState"] = ToolTurnState.LIMIT_REACHED.value
        if tool_loop["loopStopReason"] not in {
            LoopStopReason.TOOL_TURN_FAILED.value,
            LoopStopReason.TOOL_TURN_BLOCKED.value,
            LoopStopReason.TOOL_TURN_MALFORMED.value,
        }:
            tool_loop[
                "loopStopReason"
            ] = LoopStopReason.TOOL_TURN_LIMIT_REACHED.value

    if final_normalized["kind"] == "malformed_tool_decision":
        _apply_tool_turn_limit()
        final_text = "Tool loop stopped after one bounded turn."
        if token_callback:
            token_callback(final_text)
        return final_text, tool_loop, command_result

    _apply_tool_turn_limit()
    final_text = "Tool loop stopped after one bounded turn."
    if token_callback:
        token_callback(final_text)
    return final_text, tool_loop, command_result


@dataclass(frozen=True)
class ThreadCompletionSettings:
    provider: str
    model: str
    reasoning_mode: str | None
    source_mode: str
    # Request-scoped persona selector copied from the thread config.
    persona_id: str | None = None
    has_thread_config: bool = False


_THREAD_CONFIG_PROVIDER_KEYS = (
    "providerId",
    "provider_id",
    "provider",
)
_THREAD_CONFIG_MODEL_KEYS = ("modelId", "model_id", "model")
_THREAD_CONFIG_INFERENCE_MODE_KEYS = (
    "inferenceMode",
    "inference_mode",
    "reasoning_mode",
)
_THREAD_CONFIG_RETRIEVAL_SOURCE_KEYS = (
    "retrievalSource",
    "retrieval_source",
    "source_mode",
)
_THREAD_CONFIG_PERSONA_KEYS = ("personaId", "persona_id")


def _clean_thread_config_text(value: Any) -> str | None:
    if value is None:
        return None
    try:
        text = str(value).strip()
    except Exception:
        return None
    return text or None


def _thread_config_payload(
    thread_info: dict[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(thread_info, dict):
        return {}
    raw_config = thread_info.get("thread_config")
    if isinstance(raw_config, dict):
        return raw_config
    if isinstance(raw_config, str):
        try:
            parsed = json.loads(raw_config)
        except Exception:
            return {}
        if isinstance(parsed, dict):
            return parsed
    return {}


def _thread_config_value(
    thread_config: dict[str, Any], keys: tuple[str, ...]
) -> str | None:
    for key in keys:
        if key not in thread_config:
            continue
        value = _clean_thread_config_text(thread_config.get(key))
        if value:
            return value
    return None


def _normalize_reasoning_mode(value: Any) -> str | None:
    text = _clean_thread_config_text(value)
    if not text:
        return None
    normalized = text.lower()
    if normalized == "default":
        return None
    return normalized


def _runtime_provider(settings: Any) -> str:
    return normalize_provider(
        getattr(settings, "LLM_PROVIDER", None)
        or getattr(dependencies, "CHAT_PROVIDER", None)
    )


def _runtime_model_for_provider(provider: str, settings: Any) -> str:
    if provider == "local":
        return (
            normalize_model_id(getattr(settings, "LOCAL_LLM_MODEL", None))
            or normalize_model_id(
                getattr(settings, "DEFAULT_LOCAL_MODEL", None)
            )
            or normalize_model_id(getattr(settings, "LLM_MODEL", None))
            or ""
        )
    return (
        normalize_model_id(getattr(dependencies, "DEFAULT_MODEL", None)) or ""
    )


def resolve_thread_completion_settings(
    thread_info: dict[str, Any] | None,
    *,
    requested_provider: str | None = None,
    requested_model: str | None = None,
    requested_reasoning_mode: str | None = None,
    requested_source_mode: str | None = None,
    settings: Any | None = None,
) -> ThreadCompletionSettings:
    settings = settings or get_settings()
    thread_config = _thread_config_payload(thread_info)
    has_thread_config = bool(thread_config)

    if has_thread_config:
        provider_text = _thread_config_value(
            thread_config, _THREAD_CONFIG_PROVIDER_KEYS
        )
        provider = (
            normalize_provider(provider_text)
            if provider_text
            else _runtime_provider(settings)
        )

        model_text = _thread_config_value(
            thread_config, _THREAD_CONFIG_MODEL_KEYS
        )
        model = normalize_model_id(model_text) if model_text else ""
        if not model:
            model = _runtime_model_for_provider(provider, settings)

        reasoning_mode = _normalize_reasoning_mode(
            _thread_config_value(
                thread_config, _THREAD_CONFIG_INFERENCE_MODE_KEYS
            )
        )
        source_mode = normalize_source_mode(
            requested_source_mode
            or _thread_config_value(
                thread_config, _THREAD_CONFIG_RETRIEVAL_SOURCE_KEYS
            )
            or SOURCE_MODE_PROJECT
        )
        persona_id = _thread_config_value(
            thread_config, _THREAD_CONFIG_PERSONA_KEYS
        )
        return ThreadCompletionSettings(
            provider=provider,
            model=model,
            reasoning_mode=reasoning_mode,
            source_mode=source_mode,
            persona_id=persona_id,
            has_thread_config=True,
        )

    provider = normalize_provider(
        requested_provider
        or getattr(settings, "LLM_PROVIDER", None)
        or getattr(dependencies, "CHAT_PROVIDER", None)
    )
    model = normalize_model_id(requested_model) or _runtime_model_for_provider(
        provider, settings
    )
    reasoning_mode = _normalize_reasoning_mode(requested_reasoning_mode)
    source_mode = normalize_source_mode(requested_source_mode)

    return ThreadCompletionSettings(
        provider=provider,
        model=model,
        reasoning_mode=reasoning_mode,
        source_mode=source_mode,
        persona_id=None,
        has_thread_config=False,
    )


async def _assemble_context_bundle(
    broker: ContextBroker,
    *,
    thread_id: int,
    query: str,
    depth_mode: str,
    user_id: str,
    project_id: int | None,
    source_mode: str,
    retrieval_override: dict[str, Any] | None = None,
    retrieval_policy: dict[str, Any] | None = None,
    request_user_id: str | None = None,
    enable_memory_preselection_trace: bool | None = None,
    enable_memory_preselection_active: bool | None = None,
    memory_preselection_candidate_headers: Sequence[dict[str, Any]] | None = None,
    memory_preselection_persona_id: str | None = None,
    memory_preselection_identity_depth: str | None = None,
    memory_preselection_include_diary_excluded: bool | None = None,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    _ = request_user_id
    memory_preselection_kwargs = _broker_memory_preselection_kwargs(
        enable_memory_preselection_trace=enable_memory_preselection_trace,
        enable_memory_preselection_active=enable_memory_preselection_active,
        memory_preselection_candidate_headers=memory_preselection_candidate_headers,
        memory_preselection_persona_id=memory_preselection_persona_id,
        memory_preselection_identity_depth=memory_preselection_identity_depth,
        memory_preselection_include_diary_excluded=memory_preselection_include_diary_excluded,
    )
    assemble_kwargs = dict(
        thread_id=thread_id,
        query=query,
        depth_mode=depth_mode,
        user_id=user_id,
        project_id=project_id,
        source_mode=source_mode,
        retrieval_override=retrieval_override,
        retrieval_policy=retrieval_policy,
    )
    assemble_kwargs.update(memory_preselection_kwargs)
    try:
        return await broker.assemble(**assemble_kwargs)
    except TypeError as exc:
        error_text = str(exc)
        retrieval_override_error = "retrieval_override" in error_text
        retrieval_policy_error = "retrieval_policy" in error_text
        source_mode_error = "source_mode" in error_text
        project_id_error = "project_id" in error_text
        preselection_error = "memory_preselection" in error_text
        if not (
            retrieval_override_error
            or retrieval_policy_error
            or source_mode_error
            or project_id_error
            or preselection_error
        ):
            raise
        if preselection_error:
            retry_kwargs = dict(assemble_kwargs)
            for key in (
                "enable_memory_preselection_trace",
                "enable_memory_preselection_active",
                "memory_preselection_candidate_headers",
                "memory_preselection_persona_id",
                "memory_preselection_identity_depth",
                "memory_preselection_include_diary_excluded",
            ):
                retry_kwargs.pop(key, None)
            return await broker.assemble(**retry_kwargs)
        if retrieval_override_error and not (
            retrieval_policy_error or source_mode_error or project_id_error
        ):
            assemble_kwargs = dict(
                thread_id=thread_id,
                query=query,
                depth_mode=depth_mode,
                user_id=user_id,
                project_id=project_id,
                source_mode=source_mode,
            )
            if not retrieval_policy_error:
                assemble_kwargs["retrieval_policy"] = retrieval_policy
            return await broker.assemble(
                **assemble_kwargs,
            )
        assemble_kwargs = dict(
            thread_id=thread_id,
            query=query,
            depth_mode=depth_mode,
            user_id=user_id,
        )
        if not retrieval_policy_error:
            assemble_kwargs["retrieval_policy"] = retrieval_policy
        return await broker.assemble(**assemble_kwargs)


def _find_last_message_index(messages: list[dict[str, Any]], role: str) -> int:
    target_role = str(role or "").strip().lower()
    for index in range(len(messages) - 1, -1, -1):
        message = messages[index]
        if not isinstance(message, dict):
            continue
        if str(message.get("role") or "").strip().lower() == target_role:
            return index
    return -1


def _coerce_message_id(raw: Any) -> int | None:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def split_history_and_latest_turn(
    messages: list[dict[str, Any]] | None,
    *,
    latest_turn_message_id: int | None = None,
) -> dict[str, Any]:
    """Partition thread messages into prior history and the latest user turn."""

    safe_messages = [
        dict(message)
        for message in (messages or [])
        if isinstance(message, dict)
    ]
    explicit_latest_turn_message_id = _coerce_message_id(latest_turn_message_id)
    if explicit_latest_turn_message_id is not None:
        for index, message in enumerate(safe_messages):
            if (
                _coerce_message_id(message.get("id"))
                != explicit_latest_turn_message_id
            ):
                continue
            if str(message.get("role") or "").strip().lower() != "user":
                return {"history": safe_messages[:index], "latest_turn": None}
            return {
                "history": safe_messages[:index],
                "latest_turn": message,
            }
        return {"history": safe_messages, "latest_turn": None}
    latest_user_index = _find_last_message_index(safe_messages, "user")
    if latest_user_index < 0:
        return {"history": safe_messages, "latest_turn": None}
    return {
        "history": safe_messages[:latest_user_index],
        "latest_turn": safe_messages[latest_user_index],
    }


def _latest_turn_instruction_message(
    completion_assembly: dict[str, Any] | None,
) -> str | None:
    """Return the explicit instruction for latest-turn-only answering."""

    if not isinstance(completion_assembly, dict):
        return None
    latest_turn = completion_assembly.get("latest_turn")
    if not isinstance(latest_turn, dict):
        return None
    return (
        "Completion targeting guidance:\n"
        "- Use prior messages as context only.\n"
        "- Treat the most recent user message as the only response target.\n"
        "- Do not re-answer older turns unless the most recent user message "
        "explicitly asks you to revisit them."
    )


def _trace_content_snippet(content: Any, *, limit: int = 240) -> str | None:
    text = render_content_for_inference(content).strip()
    if not text:
        return None
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def _latest_turn_trace_fields(
    latest_turn: dict[str, Any] | None,
    *,
    retrieval_query: str | None,
) -> dict[str, Any]:
    if not isinstance(latest_turn, dict):
        return {}

    fields: dict[str, Any] = {
        "retrieval_query": str(retrieval_query or ""),
        "retrieval_target": "latest_turn",
        "retrieval_query_matches_latest_turn": True,
    }

    latest_turn_id = latest_turn.get("id")
    if latest_turn_id is not None:
        fields["latest_turn_message_id"] = latest_turn_id

    latest_turn_content = _trace_content_snippet(latest_turn.get("content"))
    if latest_turn_content is not None:
        fields["latest_turn_content"] = latest_turn_content

    return fields


def _image_attachments_from_meta(
    latest_user_meta: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    attachments = []
    if isinstance(latest_user_meta, dict):
        attachments = latest_user_meta.get("attachments") or []
    images: list[dict[str, Any]] = []
    for attachment in attachments:
        if not isinstance(attachment, dict):
            continue
        kind = str(attachment.get("kind") or "").strip().lower()
        if kind != "image":
            continue
        images.append(attachment)
    return images


_IMAGE_REFUSAL_PATTERNS = (
    re.compile(
        r"\b(?:i\s+)?(?:can(?:not|'t)|unable\s+to)\s+"
        r"(?:directly\s+)?(?:see|view|analyze|inspect)\s+"
        r"(?:the\s+)?images?\b",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:i\s+)?(?:can(?:not|'t)|unable\s+to)\s+"
        r"(?:directly\s+)?view\s+(?:or\s+analyze\s+)?images?\b",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:i\s+)?(?:can(?:not|'t)|unable\s+to)\s+"
        r"(?:directly\s+)?see\s+(?:the\s+)?image\b",
        flags=re.IGNORECASE,
    ),
)


def _assistant_image_refusal_message(content: Any) -> bool:
    text = " ".join(str(content or "").split()).strip()
    if not text:
        return False
    return any(pattern.search(text) for pattern in _IMAGE_REFUSAL_PATTERNS)


def _should_skip_history_message_for_image_turn(
    message: dict[str, Any],
    latest_user_meta: dict[str, Any] | None,
) -> bool:
    if not isinstance(message, dict):
        return False
    if str(message.get("role") or "").strip().lower() != "assistant":
        return False
    if not _image_attachments_from_meta(latest_user_meta):
        return False
    return _assistant_image_refusal_message(message.get("content"))


def _semantic_context_item_text(item: Any) -> str:
    if not isinstance(item, dict):
        return ""
    return str(
        item.get("content") or item.get("snippet") or item.get("text") or ""
    ).strip()


def _build_retrieval_suppression_item(
    item: dict[str, Any],
    *,
    suppression_reason: str,
    policy_reason: str,
    retrieval_lane: str,
    thread_id: int | None,
    project_id: int | None,
    retrieval_policy: dict[str, Any] | None,
) -> dict[str, Any]:
    metadata = item.get("metadata") if isinstance(item, dict) else None
    if not isinstance(metadata, dict):
        metadata = {}
    score_value: float | None = None
    try:
        raw_score = item.get("score")
        if raw_score is not None and not isinstance(raw_score, bool):
            score_value = float(raw_score)
    except (TypeError, ValueError):
        score_value = None
    item_thread_id = item.get("thread_id")
    if item_thread_id in (None, ""):
        item_thread_id = thread_id
    item_project_id = item.get("project_id")
    if item_project_id in (None, ""):
        item_project_id = project_id
    return {
        "id": str(item.get("id") or metadata.get("id") or ""),
        "source_type": str(
            item.get("source_type")
            or metadata.get("source_type")
            or "retrieval"
        ).strip()
        or "retrieval",
        "role": str(
            item.get("role")
            or metadata.get("role")
            or metadata.get("author_role")
            or metadata.get("speaker_role")
            or "retrieval"
        ).strip()
        or "retrieval",
        "thread_id": item_thread_id,
        "project_id": item_project_id,
        "retrieval_lane": str(item.get("retrieval_lane") or retrieval_lane),
        "score": score_value,
        "policy_reason": policy_reason,
        "retrieval_policy": dict(retrieval_policy or {}),
        "suppressed": True,
        "suppression_reason": suppression_reason,
    }


def _merge_retrieval_suppression_summaries(
    *summaries: dict[str, Any] | None,
) -> dict[str, Any] | None:
    merged_items: list[dict[str, Any]] = []
    counts_by_reason: dict[str, int] = {}
    for summary in summaries:
        if not isinstance(summary, dict):
            continue
        items = summary.get("items")
        if isinstance(items, list):
            merged_items.extend(
                [item for item in items if isinstance(item, dict)]
            )
        counts = summary.get("counts_by_reason")
        if isinstance(counts, dict):
            for reason, count in counts.items():
                reason_text = str(reason or "").strip()
                if not reason_text:
                    continue
                try:
                    numeric_count = int(count)
                except (TypeError, ValueError):
                    continue
                if numeric_count <= 0:
                    continue
                counts_by_reason[reason_text] = (
                    counts_by_reason.get(reason_text, 0) + numeric_count
                )
    if not merged_items and not counts_by_reason:
        return None
    return {
        "count": len(merged_items)
        if merged_items
        else sum(counts_by_reason.values()),
        "items": merged_items,
        "counts_by_reason": counts_by_reason,
    }


def _semantic_suppression_trace_item(
    item: dict[str, Any],
    *,
    suppression_reason: str,
) -> dict[str, Any]:
    return {
        "suppressed": True,
        "suppression_reason": suppression_reason,
        "source_type": str(item.get("source_type") or "semantic_context"),
        "role": str(item.get("role") or "assistant"),
        "thread_id": item.get("thread_id"),
        "project_id": item.get("project_id"),
        "retrieval_lane": str(item.get("retrieval_lane") or "semantic"),
        "score": item.get("score"),
        "policy_reason": item.get("policy_reason"),
    }


def _filter_image_refusal_semantic_context(
    semantic_items: Any,
    latest_user_meta: dict[str, Any] | None,
    *,
    suppression_trace: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None] | list[dict[str, Any]]:
    if not _image_attachments_from_meta(latest_user_meta):
        filtered = [
            item for item in semantic_items or [] if isinstance(item, dict)
        ]
        if isinstance(suppression_trace, dict):
            suppression_trace.setdefault("items", [])
            suppression_trace.setdefault("summary", {"total_suppressed": 0})
            return filtered
        return filtered, None
    filtered: list[dict[str, Any]] = []
    suppressed_items: list[dict[str, Any]] = []
    suppressed_trace_items: list[dict[str, Any]] = []
    suppression_reason = (
        TraceSuppressionReason.ASSISTANT_VISION_REFUSAL_ON_IMAGE_TURN.value
    )
    for item in semantic_items or []:
        if not isinstance(item, dict):
            continue
        if _assistant_image_refusal_message(_semantic_context_item_text(item)):
            suppressed_items.append(
                _build_retrieval_suppression_item(
                    item,
                    suppression_reason=suppression_reason,
                    policy_reason=suppression_reason,
                    retrieval_lane=str(
                        item.get("retrieval_lane") or "thread_semantic"
                    ),
                    thread_id=item.get("thread_id"),
                    project_id=item.get("project_id"),
                    retrieval_policy=item.get("retrieval_policy")
                    if isinstance(item.get("retrieval_policy"), dict)
                    else None,
                )
            )
            suppressed_trace_items.append(
                _semantic_suppression_trace_item(
                    item,
                    suppression_reason=suppression_reason,
                )
            )
            continue
        filtered.append(item)

    suppression_summary = _merge_retrieval_suppression_summaries(
        None
        if not suppressed_items
        else {
            "count": len(suppressed_items),
            "items": suppressed_items,
            "counts_by_reason": {suppression_reason: len(suppressed_items)},
            "counts_by_reason": {suppression_reason: len(suppressed_items)},
        }
    )
    if isinstance(suppression_trace, dict):
        suppression_trace["items"] = suppressed_trace_items
        suppression_trace["summary"] = {
            "total_suppressed": len(suppressed_trace_items),
            suppression_reason: len(suppressed_trace_items),
        }
        return filtered
    return filtered, suppression_summary


def _format_image_label(attachment: dict[str, Any]) -> str:
    label = str(attachment.get("name") or "").strip()
    if not label:
        label = str(attachment.get("id") or "").strip()
    return label or "image"


def _build_interpreter_context(
    interpretations: list[dict[str, Any]],
) -> str:
    lines = [
        "Derived image context (interpreted; the chat model did not see the raw image):"
    ]
    for idx, item in enumerate(interpretations, start=1):
        label = str(item.get("label") or "").strip() or "image"
        summary = str(item.get("summary") or "").strip()
        if summary:
            lines.append(f"Image {idx} ({label}): {summary}")
        else:
            lines.append(f"Image {idx} ({label}): [no description]")
    return "\n".join(lines).strip()


def _load_local_image_captioner() -> tuple[Any, Any] | None:
    global _LOCAL_IMAGE_CAPTIONER, _LOCAL_IMAGE_CAPTIONER_ATTEMPTED

    if _LOCAL_IMAGE_CAPTIONER is not None:
        return _LOCAL_IMAGE_CAPTIONER
    if _LOCAL_IMAGE_CAPTIONER_ATTEMPTED:
        return None
    if not bool(getattr(dependencies, "ENABLE_BLIP_MODEL", False)):
        return None

    _LOCAL_IMAGE_CAPTIONER_ATTEMPTED = True
    try:
        from transformers import BlipForConditionalGeneration, BlipProcessor
    except Exception as exc:
        logger.debug(
            "[chat-completion] local BLIP imports unavailable: %s", exc
        )
        return None

    try:
        processor = BlipProcessor.from_pretrained(
            _LOCAL_IMAGE_CAPTIONER_MODEL_NAME,
            use_fast=False,
        )
        model = BlipForConditionalGeneration.from_pretrained(
            _LOCAL_IMAGE_CAPTIONER_MODEL_NAME
        )
        try:
            model.eval()
        except Exception:
            pass
    except Exception as exc:
        logger.warning(
            "[chat-completion] local BLIP captioner unavailable: %s", exc
        )
        return None

    _LOCAL_IMAGE_CAPTIONER = (processor, model)
    return _LOCAL_IMAGE_CAPTIONER


def _download_image_bytes(src: str) -> bytes | None:
    source = str(src or "").strip()
    if not source:
        return None

    if source.startswith("data:"):
        try:
            from base64 import b64decode
        except Exception:
            return None
        _, _, payload = source.partition(",")
        if not payload:
            return None
        try:
            return b64decode(payload)
        except Exception:
            return None

    try:
        import requests

        response = requests.get(source, timeout=30)
        response.raise_for_status()
        return response.content
    except Exception as exc:
        logger.debug(
            "[chat-completion] failed to download image for interpretation: %s",
            exc,
        )
        return None


def _truncate_url_for_log(url: str, maxlen: int = 120) -> str:
    """Truncate a URL for safe logging."""
    if len(url) <= maxlen:
        return url
    return url[: maxlen - 3] + "..."


def _convert_image_url_to_data_url(raw_url: str) -> str | None:
    """Convert an image URL to a base64 data URL suitable for external providers.

    Uses the existing _encode_image_url_to_base64 helper (which handles
    local /media/ paths, file-system reads, and remote HTTP fetches) and
    prepends the appropriate ``data:image/<mime>;base64,`` prefix.
    """
    if not raw_url:
        return None

    # Data URLs are already provider-compatible.
    if raw_url.startswith("data:"):
        return raw_url

    try:
        encoded = _encode_image_url_to_base64(raw_url)
    except Exception:
        return None

    if not encoded:
        return None

    lower = raw_url.lower()
    if ".png" in lower:
        mime = "image/png"
    elif ".webp" in lower:
        mime = "image/webp"
    elif ".gif" in lower:
        mime = "image/gif"
    else:
        mime = "image/jpeg"

    return f"data:{mime};base64,{encoded}"


def _caption_image_with_local_blip(src: str) -> str | None:
    captioner = _load_local_image_captioner()
    if captioner is None:
        return None

    image_bytes = _download_image_bytes(src)
    if not image_bytes:
        return None

    try:
        from io import BytesIO

        from PIL import Image
    except Exception as exc:
        logger.debug(
            "[chat-completion] PIL unavailable for local image captioning: %s",
            exc,
        )
        return None

    processor, model = captioner
    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    inputs = processor(images=image, return_tensors="pt")
    try:
        import torch
    except Exception:
        torch = None  # type: ignore[assignment]

    if torch is not None:
        with torch.inference_mode():
            output = model.generate(**inputs, max_new_tokens=32)
    else:
        output = model.generate(**inputs, max_new_tokens=32)
    caption = processor.decode(output[0], skip_special_tokens=True)
    normalized = " ".join(str(caption or "").split()).strip()
    return normalized or None


def _caption_image_with_groq_vision(src: str, *, settings: Any) -> str | None:
    vision_model = str(getattr(settings, "GROQ_VISION_MODEL", "") or "").strip()
    api_key = str(getattr(settings, "GROQ_API_KEY", "") or "").strip()
    if not vision_model or not api_key:
        return None

    prompt = (
        "Describe the image for downstream reasoning. "
        "If the image includes readable text, extract it."
    )
    content = build_openai_vision_content(prompt, [src])
    summary = chat_with_ai(
        [{"role": "user", "content": content}],
        model=vision_model,
        provider="groq",
    )
    normalized = " ".join(str(summary or "").split()).strip()
    return normalized or None


def _interpret_image_attachments(
    image_attachments: list[dict[str, Any]],
    *,
    settings: Any,
) -> list[dict[str, Any]] | None:
    valid_attachments = []
    for attachment in image_attachments:
        if not isinstance(attachment, dict):
            continue
        src = str(attachment.get("src") or "").strip()
        if not src:
            continue
        valid_attachments.append((attachment, src))

    if not valid_attachments:
        return None

    if bool(getattr(dependencies, "ENABLE_BLIP_MODEL", False)):
        local_interpretations: list[dict[str, Any]] = []
        for attachment, src in valid_attachments:
            try:
                summary = _caption_image_with_local_blip(src)
            except Exception as exc:
                logger.warning(
                    "[chat-completion] local BLIP caption failed; falling back to cloud vision: %s",
                    exc,
                )
                local_interpretations = []
                break
            if not summary:
                local_interpretations = []
                break
            local_interpretations.append(
                {
                    "label": _format_image_label(attachment),
                    "summary": summary,
                }
            )
        if local_interpretations and len(local_interpretations) == len(
            valid_attachments
        ):
            return local_interpretations

    interpretations: list[dict[str, Any]] = []
    for attachment, src in valid_attachments:
        try:
            summary = _caption_image_with_groq_vision(src, settings=settings)
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Image interpreter failed: {exc}",
            ) from exc
        if not summary:
            continue
        interpretations.append(
            {
                "label": _format_image_label(attachment),
                "summary": summary,
            }
        )
    if not interpretations:
        return None
    return interpretations


def _apply_image_attachment_routing(
    messages: list[dict[str, Any]],
    *,
    bundle: dict[str, Any] | None,
    provider: str,
    model: str,
    settings: Any,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    latest_user_meta = None
    if isinstance(bundle, dict):
        attachment_meta = bundle.get("_attachment_meta")
        if isinstance(attachment_meta, dict):
            latest_user_meta = attachment_meta.get("latest_user")

    image_attachments = _image_attachments_from_meta(latest_user_meta)
    image_attachment_count = len(image_attachments)
    routing_meta = {
        "image_routing_path": "none",
        "image_attachment_count": image_attachment_count,
        "derived_image_context_injected": False,
    }
    if not image_attachments:
        return messages, routing_meta

    vision_support_state = resolve_model_vision_capability_state(
        provider,
        model,
        settings,
    )
    last_user_index = _find_last_message_index(messages, "user")
    if last_user_index < 0:
        return messages, routing_meta

    updated = [
        dict(message) if isinstance(message, dict) else message
        for message in messages
    ]

    if vision_support_state is False:
        raise HTTPException(
            status_code=400,
            detail=_image_turn_vision_unsupported_detail(
                provider=provider,
                model=model,
                image_attachment_count=image_attachment_count,
                capability_state="unsupported",
            ),
        )

    if vision_support_state is True:
        image_urls = [
            str(item.get("src") or "").strip() for item in image_attachments
        ]
        image_urls = [url for url in image_urls if url]
        if not image_urls:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "provider_request_failed",
                    "error_code": ErrorCode.CHAT_COMPLETE_IMAGE_PAYLOAD_MISSING.value,
                    "provider": provider,
                    "model": model,
                    "message": (
                        "Image attachments are missing source URLs; "
                        "unable to route to a vision-capable model."
                    ),
                    "image_attachment_count": image_attachment_count,
                },
            )
        # Convert remote/localhost URLs to base64 data URLs so external
        # providers (OpenAI, Anthropic, Groq, etc.) can actually fetch the
        # image bytes.  The Ollama path does this in
        # _transform_messages_for_ollama_vision; this brings the same
        # behaviour to all other vision-capable providers.
        resolved_image_urls: list[str] = []
        for raw_url in image_urls:
            data_url = _convert_image_url_to_data_url(raw_url)
            if data_url:
                resolved_image_urls.append(data_url)
            else:
                logger.warning(
                    "[image-routing] failed to encode image as data URL, "
                    "falling back to raw URL for provider=%s: %s",
                    provider,
                    _truncate_url_for_log(raw_url),
                )
                resolved_image_urls.append(raw_url)
        text = ""
        if isinstance(latest_user_meta, dict):
            text = str(latest_user_meta.get("text") or "")
        updated[last_user_index] = {
            "role": "user",
            "content": build_openai_vision_content(text, resolved_image_urls),
        }
        routing_meta[
            "image_routing_path"
        ] = ImageRoutingPath.NATIVE_MULTIMODAL_VISION.value
        return updated, routing_meta

    interpretations = _interpret_image_attachments(
        image_attachments, settings=settings
    )
    if not interpretations:
        raise HTTPException(
            status_code=400,
            detail=(
                "Image attachments present but no valid vision-capable model "
                "or interpreter is available."
            ),
        )

    context_block = _build_interpreter_context(interpretations)
    user_text = ""
    if isinstance(latest_user_meta, dict):
        user_text = str(latest_user_meta.get("text") or "").strip()
    stitched = context_block
    if user_text:
        stitched = f"{context_block}\n\n{user_text}"

    updated[last_user_index] = {
        "role": "user",
        "content": stitched,
    }
    routing_meta["image_routing_path"] = "interpreter"
    routing_meta["derived_image_context_injected"] = True
    return updated, routing_meta


def _image_routing_absence_reason(
    *,
    image_attachment_count: int,
    image_routing_path: str | None,
    provider: str,
    requested_model: str | None,
    resolved_model: str | None,
    settings: Any,
) -> str | None:
    normalized_routing_path = str(image_routing_path or "").strip().lower()
    if normalized_routing_path and normalized_routing_path != "none":
        return None
    if image_attachment_count <= 0:
        return TraceSnapshotAbsenceReason.IMAGE_ROUTING_NOT_EVALUATED.value

    normalized_requested_model = normalize_model_id(requested_model)
    normalized_resolved_model = normalize_model_id(resolved_model)
    if (
        normalize_provider(provider) == "local"
        and normalized_requested_model
        and normalized_requested_model != normalized_resolved_model
    ):
        vision_support_state = resolve_model_vision_capability_state(
            provider,
            resolved_model or normalized_resolved_model or "",
            settings,
        )
        if vision_support_state is not True:
            return (
                TraceSnapshotAbsenceReason.LOCAL_MODEL_SUBSTITUTION_SELECTED_NONVISION_MODEL.value
            )
    if (
        resolve_model_vision_capability_state(
            provider,
            resolved_model or normalized_resolved_model or "",
            settings,
        )
        is True
    ):
        return (
            TraceSnapshotAbsenceReason.VISION_MODEL_SELECTED_BUT_IMAGE_PAYLOAD_NOT_ROUTED.value
        )
    return TraceSnapshotAbsenceReason.IMAGE_ROUTING_NOT_EVALUATED.value


def _resolve_image_routing_trace(
    *,
    messages_for_llm: list[dict[str, Any]],
    routing_meta: dict[str, Any],
    provider: str,
    model: str,
    requested_model: str | None,
    settings: Any,
) -> tuple[str | None, str | None]:
    image_attachment_count = int(
        routing_meta.get("image_attachment_count", 0) or 0
    )
    if image_attachment_count <= 0:
        return (
            None,
            TraceSnapshotAbsenceReason.IMAGE_ROUTING_NOT_EVALUATED.value,
        )

    raw_path = str(routing_meta.get("image_routing_path") or "").strip().lower()
    provider_ready_image_payload_present = messages_contain_image_payload(
        messages_for_llm
    )
    vision_support_state = resolve_model_vision_capability_state(
        provider,
        model,
        settings,
    )

    if raw_path in {
        ImageRoutingPath.INTERPRETER.value,
        ImageRoutingPath.NATIVE_MULTIMODAL_VISION.value,
    }:
        if raw_path == ImageRoutingPath.NATIVE_MULTIMODAL_VISION.value:
            if provider_ready_image_payload_present:
                return ImageRoutingPath.NATIVE_MULTIMODAL_VISION.value, None
            return (
                None,
                TraceSnapshotAbsenceReason.VISION_MODEL_SELECTED_BUT_IMAGE_PAYLOAD_NOT_ROUTED.value,
            )
        return ImageRoutingPath.INTERPRETER.value, None

    if provider_ready_image_payload_present and vision_support_state is True:
        return ImageRoutingPath.NATIVE_MULTIMODAL_VISION.value, None

    if vision_support_state is True:
        return (
            None,
            TraceSnapshotAbsenceReason.VISION_MODEL_SELECTED_BUT_IMAGE_PAYLOAD_NOT_ROUTED.value,
        )

    return (
        None,
        _image_routing_absence_reason(
            image_attachment_count=image_attachment_count,
            image_routing_path=raw_path or None,
            provider=provider,
            requested_model=requested_model,
            resolved_model=model,
            settings=settings,
        ),
    )


def _normalize_completion_image_routing_truth(
    *,
    task: Any,
    provider: str,
    model: str,
    settings: Any,
    messages_for_llm: list[dict[str, Any]],
    routing_meta: dict[str, Any] | None,
    trace: dict[str, Any] | None = None,
    payload_summary: dict[str, Any] | None = None,
    result: dict[str, Any] | None = None,
) -> tuple[int, str | None, str | None]:
    def _positive_int(raw: Any) -> int:
        try:
            value = int(raw)
        except (TypeError, ValueError):
            return 0
        return value if value > 0 else 0

    routing_meta = dict(routing_meta or {})
    trace = dict(trace or {}) if isinstance(trace, dict) else {}
    payload_summary = (
        dict(payload_summary or {}) if isinstance(payload_summary, dict) else {}
    )
    result = dict(result or {}) if isinstance(result, dict) else {}

    image_attachment_count = max(
        (
            count
            for count in (
                _positive_int(routing_meta.get("image_attachment_count")),
                _positive_int(payload_summary.get("image_attachment_count")),
                _positive_int(trace.get("image_attachment_count")),
                _positive_int(result.get("image_attachment_count")),
                _positive_int(
                    _image_attachment_count_from_origin(
                        getattr(task, "origin", None)
                    )
                ),
            )
            if count > 0
        ),
        default=0,
    )

    for text_candidate in (
        result.get("retrieval_query"),
        trace.get("latest_turn_content"),
        trace.get("retrieval_query"),
        payload_summary.get("retrieval_query"),
        payload_summary.get("latest_turn_content"),
    ):
        text = str(text_candidate or "").strip()
        if (
            "Attached image:" in text
            or "cfy-media:image:" in text
            or "cfy-media-src:" in text
        ):
            image_attachment_count = max(image_attachment_count, 1)

    if image_attachment_count <= 0:
        return (
            0,
            None,
            TraceSnapshotAbsenceReason.IMAGE_ROUTING_NOT_EVALUATED.value,
        )

    derived_image_context_injected = any(
        bool(candidate.get("derived_image_context_injected"))
        for candidate in (routing_meta, payload_summary, trace, result)
        if isinstance(candidate, dict)
    )
    if derived_image_context_injected:
        return image_attachment_count, ImageRoutingPath.INTERPRETER.value, None

    def _first_non_empty_path(*candidates: dict[str, Any] | None) -> str | None:
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            value = (
                str(candidate.get("image_routing_path") or "").strip().lower()
            )
            if value:
                return value
        return None

    existing_path = _first_non_empty_path(
        result,
        payload_summary,
        trace,
        routing_meta,
    )

    provider_ready_image_payload_present = messages_contain_image_payload(
        messages_for_llm
    )
    vision_support_state = resolve_model_vision_capability_state(
        provider,
        model,
        settings,
    )
    if (
        existing_path == ImageRoutingPath.NATIVE_MULTIMODAL_VISION.value
        and provider_ready_image_payload_present
        and vision_support_state is True
    ):
        return (
            image_attachment_count,
            ImageRoutingPath.NATIVE_MULTIMODAL_VISION.value,
            None,
        )
    if existing_path == ImageRoutingPath.INTERPRETER.value:
        return image_attachment_count, ImageRoutingPath.INTERPRETER.value, None
    if provider_ready_image_payload_present and vision_support_state is True:
        return (
            image_attachment_count,
            ImageRoutingPath.NATIVE_MULTIMODAL_VISION.value,
            None,
        )
    return (
        image_attachment_count,
        None,
        _image_routing_absence_reason(
            image_attachment_count=image_attachment_count,
            image_routing_path=None,
            provider=provider,
            requested_model=getattr(task, "requested_model", None),
            resolved_model=model,
            settings=settings,
        ),
    )


def build_sanitized_payload_summary(
    messages: list[dict[str, str]] | None,
    bundle: dict[str, Any] | None,
    *,
    provider: str | None,
    model: str | None,
    requested_provider: str | None = None,
    requested_model: str | None = None,
    requested_source_mode: str | None = None,
) -> dict[str, Any]:
    """Build a minimal, non-sensitive summary of the outbound provider payload.

    The summary is intentionally counts/flags-only to avoid persisting raw prompt
    content while still enabling diagnostics of the assembled payload that
    reaches the provider.
    """

    safe_messages = messages or []
    message_count = len(safe_messages)

    try:
        payload_char_count = len(
            json.dumps(safe_messages, ensure_ascii=False, separators=(",", ":"))
        )
    except Exception:
        payload_char_count = sum(
            len(str(m.get("role") or "")) + len(str(m.get("content") or ""))
            for m in safe_messages
            if isinstance(m, dict)
        )

    payload_estimated_tokens = (
        max(1, payload_char_count // 4) if payload_char_count else 0
    )

    system_messages = [
        str(m.get("content") or "")
        for m in safe_messages
        if str(m.get("role") or "").strip().lower() == "system"
    ]
    joined_system_text = "\n".join(system_messages).lower()
    persona_or_imprint_present = any(
        marker in joined_system_text
        for marker in (
            "=== imprint_zero",
            "=== persona",
            "persona:",
            "imprint",
            "user-provided persona instructions",
        )
    )

    prompt_meta = None
    if isinstance(bundle, dict):
        prompt_meta = bundle.get("_prompt_meta")
    if isinstance(prompt_meta, dict):
        persona_or_imprint_present = persona_or_imprint_present or bool(
            prompt_meta.get("persona_has_body")
        )
        persona_or_imprint_present = persona_or_imprint_present or (
            str(prompt_meta.get("resolved_imprint_source") or "").strip()
            not in {"", "system_default"}
        )

    docs = (bundle or {}).get("docs") if isinstance(bundle, dict) else None
    linked_document_count = 0
    if isinstance(docs, dict):
        for key in ("thread", "project", "library"):
            value = docs.get(key)
            if isinstance(value, list):
                linked_document_count += len(value)
        if not linked_document_count:
            linked_document_count = sum(
                len(v) for v in docs.values() if isinstance(v, list)
            )
    elif isinstance(docs, list):
        linked_document_count = len(docs)

    retrieval_meta = {}
    docs_meta = {}
    verified_personal_facts_meta: dict[str, Any] = {}
    if isinstance(prompt_meta, dict):
        retrieval_meta = prompt_meta.get("context") or {}
        docs_meta = prompt_meta.get("docs") or {}
        verified_personal_facts_meta = (
            retrieval_meta.get("verified_personal_facts")
            or retrieval_meta.get("personal_facts")
            or {}
        )

    semantic_injected = bool(
        (retrieval_meta.get("semantic") or {}).get("injected")
    )
    memory_injected = bool((retrieval_meta.get("memory") or {}).get("injected"))
    graph_injected = bool((retrieval_meta.get("graph") or {}).get("injected"))
    federated_injected = bool(
        (retrieval_meta.get("federated") or {}).get("injected")
    )
    linked_document_injected = bool(docs_meta.get("injected"))
    connector_context_meta = retrieval_meta.get("connector_context") or {}
    connector_context_injected = bool(connector_context_meta.get("injected"))
    connector_context_count = (
        len((bundle or {}).get("connector_context") or [])
        if isinstance(bundle, dict)
        else 0
    )

    obsidian_context_meta = retrieval_meta.get("obsidian")
    obsidian_context_count = 0
    obsidian_context_injected = False
    if isinstance(obsidian_context_meta, dict):
        obsidian_context_count = int(obsidian_context_meta.get("count") or 0)
        obsidian_context_injected = bool(obsidian_context_meta.get("injected"))

    obsidian_count = len(_obsidian_semantic_hits_from_bundle(bundle))
    if obsidian_context_count > obsidian_count:
        obsidian_count = obsidian_context_count
    # Obsidian entries are injected through the semantic context block, so the
    # count only becomes meaningful when semantic injection actually happened.
    obsidian_injected = bool(
        obsidian_context_injected or (obsidian_count and semantic_injected)
    )
    verified_personal_facts_injected = bool(
        verified_personal_facts_meta.get("injected")
    )
    verified_personal_fact_ids = [
        item
        for item in (
            verified_personal_facts_meta.get("fact_ids")
            or verified_personal_facts_meta.get("included_ids")
            or []
        )
        if item is not None
    ]

    summary = {
        "version": 1,
        "has_system_prompt": bool(system_messages),
        "payload_char_count": int(payload_char_count),
        "payload_estimated_tokens": int(payload_estimated_tokens),
        "message_count": message_count,
        "persona_or_imprint_present": bool(persona_or_imprint_present),
        "semantic_count": (
            len((bundle or {}).get("semantic") or [])
            if isinstance(bundle, dict)
            else 0
        ),
        "memory_count": (
            len((bundle or {}).get("memory") or [])
            if isinstance(bundle, dict)
            else 0
        ),
        "graph_count": (
            len((bundle or {}).get("graph") or [])
            if isinstance(bundle, dict)
            else 0
        ),
        "obsidian_count": obsidian_count,
        "linked_document_count": linked_document_count,
        "connector_context_count": connector_context_count,
        "has_user_system_override": bool(
            (bundle or {}).get("user_system_override")
            if isinstance(bundle, dict)
            else False
        ),
        "resolved_provider": (provider or "").strip() or None,
        "resolved_model": (model or "").strip() or None,
        "requested_provider": (
            str(requested_provider).strip() or None
            if requested_provider is not None
            else None
        ),
        "requested_model": (
            str(requested_model).strip() or None
            if requested_model is not None
            else None
        ),
        "source_mode": None,
        "effective_source_mode": None,
        "requested_source_mode": (
            str(requested_source_mode).strip() or None
            if requested_source_mode is not None
            else None
        ),
        "semantic_injected": semantic_injected,
        "memory_injected": memory_injected,
        "graph_injected": graph_injected,
        "federated_injected": federated_injected,
        "linked_document_injected": linked_document_injected,
        "connector_context_injected": connector_context_injected,
        "obsidian_injected": obsidian_injected,
        "verified_personal_facts_injected": verified_personal_facts_injected,
        "verified_personal_fact_ids": verified_personal_fact_ids,
        "verified_personal_facts_count": int(
            verified_personal_facts_meta.get("count") or 0
        ),
    }
    summary["graph_hit_count"] = summary["graph_count"]
    summary["graph_enrichment_status"] = (
        "not_used_yet"
        if summary["graph_hit_count"] == 0
        else "graph_hits_present"
    )

    summary["retrieval_injected"] = any(
        summary[key]
        for key in (
            "semantic_injected",
            "memory_injected",
            "graph_injected",
            "federated_injected",
            "linked_document_injected",
            "connector_context_injected",
            "obsidian_injected",
            "verified_personal_facts_injected",
        )
    )
    summary["normalized_source_mode"] = summary["source_mode"]

    # For callers that later update to reflect a fallback provider/model.
    summary.setdefault("final_provider", summary["resolved_provider"])
    summary.setdefault("final_model", summary["resolved_model"])
    return summary


def _namespace_from_hit(hit: Any) -> str | None:
    if not isinstance(hit, dict):
        return None
    metadata = hit.get("metadata")
    if not isinstance(metadata, dict):
        metadata = hit.get("meta")
    if not isinstance(metadata, dict):
        return None
    namespace = str(metadata.get("namespace") or "").strip()
    return namespace or None


def _count_items_with_namespace(
    items: list[Any] | None,
    namespace: str,
) -> int:
    if not isinstance(items, list) or not namespace:
        return 0
    normalized_namespace = str(namespace).strip()
    if not normalized_namespace:
        return 0
    return sum(
        1 for item in items if _namespace_from_hit(item) == normalized_namespace
    )


def _count_items_with_prefix(
    items: list[Any] | None,
    prefix: str,
) -> int:
    if not isinstance(items, list) or not prefix:
        return 0
    normalized_prefix = str(prefix).strip()
    if not normalized_prefix:
        return 0
    return sum(
        1
        for item in items
        if (_namespace_from_hit(item) or "").startswith(normalized_prefix)
    )


def _obsidian_semantic_hits_from_bundle(
    bundle: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if not isinstance(bundle, dict):
        return []

    obsidian_hits = [
        item
        for item in (bundle.get("obsidian") or [])
        if isinstance(item, dict)
    ]
    if obsidian_hits:
        return obsidian_hits

    semantic_hits = [
        item
        for item in (bundle.get("semantic") or [])
        if isinstance(item, dict)
    ]
    return [
        item
        for item in semantic_hits
        if _namespace_from_hit(item) == OBSIDIAN_NAMESPACE
    ]


def _build_retrieval_provenance(
    *,
    requested_source_mode: str | None,
    normalized_source_mode: str | None,
    bundle: dict[str, Any] | None,
) -> dict[str, Any]:
    semantic_hits = []
    if isinstance(bundle, dict):
        semantic_hits = [
            item
            for item in (bundle.get("semantic") or [])
            if isinstance(item, dict)
        ]
    thread_semantic_count = _count_items_with_prefix(semantic_hits, "thread:")
    obsidian_semantic_hits = [
        item
        for item in semantic_hits
        if _namespace_from_hit(item) == OBSIDIAN_NAMESPACE
    ]
    if not obsidian_semantic_hits:
        obsidian_semantic_hits = _obsidian_semantic_hits_from_bundle(bundle)
    obsidian_semantic_count = len(obsidian_semantic_hits)
    other_semantic_count = max(
        len(semantic_hits) - thread_semantic_count - obsidian_semantic_count,
        0,
    )

    docs = bundle.get("docs") if isinstance(bundle, dict) else None
    project_document_count = 0
    thread_document_count = 0
    global_document_count = 0
    other_document_count = 0
    if isinstance(docs, dict):
        for key, value in docs.items():
            if not isinstance(value, list):
                continue
            count = len([item for item in value if isinstance(item, dict)])
            if key == "project":
                project_document_count = count
            elif key == "thread":
                thread_document_count = count
            elif key == "global":
                global_document_count = count
            else:
                other_document_count += count
    elif isinstance(docs, list):
        other_document_count = len(
            [item for item in docs if isinstance(item, dict)]
        )
    memory_count = (
        len(
            [
                item
                for item in (bundle or {}).get("memory", [])
                if isinstance(item, dict)
            ]
        )
        if isinstance(bundle, dict)
        else 0
    )
    graph_count = (
        len(
            [
                item
                for item in (bundle or {}).get("graph", [])
                if isinstance(item, dict)
            ]
        )
        if isinstance(bundle, dict)
        else 0
    )

    source_hit_counts = {
        "semantic_total": len(semantic_hits),
        "thread_semantic": thread_semantic_count,
        "obsidian_semantic": obsidian_semantic_count,
        "other_semantic": other_semantic_count,
        "project_documents": project_document_count,
        "thread_documents": thread_document_count,
        "global_documents": global_document_count,
        "other_documents": other_document_count,
        "memory": memory_count,
        "graph": graph_count,
    }

    if normalized_source_mode == SOURCE_MODE_WORKSPACE:
        local_result_count = (
            len(semantic_hits) + project_document_count + thread_document_count
        )
        if local_result_count <= 0 and obsidian_semantic_count > 0:
            local_result_count = obsidian_semantic_count
        retrieval_status = (
            "workspace_local_success"
            if local_result_count > 0
            else "no_workspace_results"
        )
    elif obsidian_semantic_count > 0:
        if (
            thread_semantic_count == 0
            and other_semantic_count == 0
            and project_document_count == 0
            and thread_document_count == 0
            and global_document_count == 0
            and other_document_count == 0
            and memory_count == 0
            and graph_count == 0
        ):
            retrieval_status = "obsidian_only_success"
        else:
            retrieval_status = "obsidian_with_additional_results"
    else:
        retrieval_status = "no_obsidian_results"

    return {
        "requested_source_mode": (
            str(requested_source_mode).strip() or None
            if requested_source_mode is not None
            else None
        ),
        "normalized_source_mode": (
            str(normalized_source_mode).strip() or None
            if normalized_source_mode is not None
            else None
        ),
        "source_hit_counts": source_hit_counts,
        "retrieval_status": retrieval_status,
    }


def _build_model_selection_metadata(
    *,
    requested_provider: str | None,
    requested_model: str | None,
    attempted_provider: str | None,
    attempted_model: str | None,
    resolved_provider: str | None = None,
    resolved_model: str | None = None,
    final_provider: str | None,
    final_model: str | None,
    selection_source: str | None,
    fallback_reason: str | None,
    model_resolution: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "requested_provider": (
            str(requested_provider).strip() or None
            if requested_provider is not None
            else None
        ),
        "requested_model": (
            str(requested_model).strip() or None
            if requested_model is not None
            else None
        ),
        "attempted_provider": (
            str(attempted_provider).strip() or None
            if attempted_provider is not None
            else None
        ),
        "attempted_model": (
            str(attempted_model).strip() or None
            if attempted_model is not None
            else None
        ),
        "resolved_provider": (
            str(resolved_provider).strip() or None
            if resolved_provider is not None
            else None
        ),
        "resolved_model": (
            str(resolved_model).strip() or None
            if resolved_model is not None
            else None
        ),
        "final_provider": (
            str(final_provider).strip() or None
            if final_provider is not None
            else None
        ),
        "final_model": (
            str(final_model).strip() or None
            if final_model is not None
            else None
        ),
        "selection_source": (
            str(selection_source).strip() or None
            if selection_source is not None
            else None
        ),
        "fallback_reason": (
            str(fallback_reason).strip() or None
            if fallback_reason is not None
            else None
        ),
        "policy_reason": None,
        "model_resolution": None,
    }
    if isinstance(model_resolution, dict):
        payload["model_resolution"] = dict(model_resolution)
        source = str(model_resolution.get("source") or "").strip()
        if source:
            payload["policy_reason"] = source
        failure_kind = str(model_resolution.get("failure_kind") or "").strip()
        if failure_kind:
            payload["model_resolution_failure_kind"] = failure_kind
        message = str(model_resolution.get("message") or "").strip()
        if message:
            payload["model_resolution_message"] = message
    if not payload.get("policy_reason"):
        if fallback_reason:
            payload["policy_reason"] = fallback_reason
        elif (
            payload.get("requested_model")
            and payload.get("final_model")
            and payload["requested_model"] != payload["final_model"]
        ):
            payload["policy_reason"] = "requested_model_not_selected"
        elif (
            payload.get("requested_provider")
            and payload.get("final_provider")
            and payload["requested_provider"] != payload["final_provider"]
        ):
            payload["policy_reason"] = "requested_provider_not_selected"
    return payload


def _build_model_selection_trace(
    *,
    requested_provider: str | None,
    requested_model: str | None,
    attempted_provider: str | None,
    attempted_model: str | None,
    resolved_provider: str | None,
    resolved_model: str | None,
    final_provider: str | None,
    final_model: str | None,
    selection_source: str | None,
    fallback_reason: str | None,
    model_resolution: dict[str, Any] | None,
) -> dict[str, Any]:
    settings = get_settings()
    normalized_requested_provider = (
        str(requested_provider or "").strip().lower() or None
    )
    normalized_requested_model = normalize_model_id(requested_model)
    normalized_attempted_provider = (
        str(attempted_provider or "").strip().lower() or None
    )
    normalized_attempted_model = normalize_model_id(attempted_model)
    normalized_final_provider = (
        str(final_provider or "").strip().lower() or None
    )
    normalized_final_model = normalize_model_id(final_model)
    selection_source_text = str(selection_source or "").strip() or None
    local_chat_model = normalize_model_id(
        getattr(settings, "LOCAL_CHAT_MODEL", None)
    )
    model_resolution_source = selection_source_text
    model_resolution_message: str | None = None
    policy_reason = fallback_reason or selection_source_text

    if (
        normalized_final_provider == "local"
        and normalized_final_model
        and normalized_requested_model
        and normalized_requested_model != normalized_final_model
        and local_chat_model
        and normalized_final_model == local_chat_model
    ):
        model_resolution_source = "LOCAL_CHAT_MODEL"
        policy_reason = "LOCAL_CHAT_MODEL"
        model_resolution_message = (
            f"requested model '{normalized_requested_model}' was overridden "
            f"by configured local chat model '{normalized_final_model}' from "
            "LOCAL_CHAT_MODEL"
        )
    elif fallback_reason:
        model_resolution_message = str(fallback_reason).strip() or None

    model_resolution: dict[str, Any] = {
        "source": model_resolution_source,
        "message": model_resolution_message,
    }
    return {
        "requested_provider": normalized_requested_provider,
        "requested_model": normalized_requested_model,
        "attempted_provider": normalized_attempted_provider,
        "attempted_model": normalized_attempted_model,
        "final_provider": normalized_final_provider,
        "final_model": normalized_final_model,
        "selection_source": selection_source_text,
        "policy_reason": policy_reason,
        "fallback_reason": fallback_reason,
        "model_resolution": model_resolution,
    }


def _build_retrieval_posture(
    *,
    source_mode: str | None,
    retrieval_override: dict[str, Any] | None,
    widen_reason: str | None,
) -> dict[str, Any] | None:
    normalized_source_mode = str(source_mode or "").strip().lower()
    if not normalized_source_mode:
        return None

    retrieval_override_mode = None
    if isinstance(retrieval_override, dict):
        override_mode = retrieval_override.get("mode")
        if override_mode not in (None, ""):
            retrieval_override_mode = str(override_mode).strip().lower() or None

    return {
        "source_mode": normalized_source_mode,
        "boundary_label": source_mode_boundary_label(normalized_source_mode),
        "retrieval_override_mode": retrieval_override_mode,
        "widen_reason": str(widen_reason or "none"),
        "conversation_only": normalized_source_mode == SOURCE_MODE_CONVERSATION,
    }


def _preserve_workspace_evidence_fields(
    target: dict[str, Any],
    source: dict[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(target, dict) or not isinstance(source, dict):
        return target

    def _positive_int(raw: Any) -> int:
        try:
            value = int(raw)
        except (TypeError, ValueError):
            return 0
        return value if value > 0 else 0

    for key in ("semantic_count", "obsidian_count"):
        source_count = _positive_int(source.get(key))
        if source_count <= 0:
            continue
        target_count = _positive_int(target.get(key))
        if source_count > target_count:
            target[key] = source_count

    for key in (
        "semantic_injected",
        "obsidian_injected",
        "retrieval_injected",
    ):
        if bool(source.get(key)):
            target[key] = True

    return target


def _embed_message(
    thread_id: int, role: str, content: str, message_id: int
) -> None:
    if not dependencies._vector_store:
        return
    try:
        meta = {
            "thread_id": thread_id,
            "role": role,
            "message_id": message_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "source": "chat",
        }
        dependencies._vector_store.add_texts([{"text": content, "meta": meta}])
    except Exception as exc:
        logger.warning(
            "[chat-completion] failed to auto-embed message %s: %s",
            message_id,
            exc,
        )


def _build_document_context_message(
    bundle: dict[str, Any] | None,
) -> tuple[str | None, int]:
    if not isinstance(bundle, dict):
        return None, 0

    docs = bundle.get("docs")
    if not isinstance(docs, dict):
        return None, 0

    thread_docs = docs.get("thread")
    project_docs = docs.get("project")
    thread_items = (
        [item for item in thread_docs if isinstance(item, dict)]
        if isinstance(thread_docs, list)
        else []
    )
    project_items = (
        [item for item in project_docs if isinstance(item, dict)]
        if isinstance(project_docs, list)
        else []
    )

    sources: list[tuple[str, dict[str, Any]]] = [
        ("thread", item) for item in thread_items
    ] + [("project", item) for item in project_items]
    if not sources:
        return None, 0

    thread_only = bool(thread_items) and not project_items
    project_only = bool(project_items) and not thread_items
    if thread_only:
        message_prefix = (
            "Thread-linked document excerpts are available for this "
            "conversation. Use them when they help answer the user's "
            "request.\n\nThread documents:\n"
        )
    elif project_only:
        message_prefix = (
            "Project-linked document excerpts are available for this "
            "conversation. Use them when they help answer the user's "
            "request.\n\nProject documents:\n"
        )
    else:
        message_prefix = (
            "Linked document excerpts are available for this conversation. "
            "Use them when they help answer the user's request.\n\n"
            "Documents:\n"
        )

    lines: list[str] = []
    for scope, item in sources:
        title = str(item.get("title") or item.get("id") or "document").strip()
        excerpt = str(item.get("excerpt") or "").strip()
        provenance = item.get("provenance")
        relation = ""
        if isinstance(provenance, dict):
            relation = str(provenance.get("relation") or "").strip().lower()
        relation_prefix = f"[{relation}] " if relation else ""
        if thread_only or project_only:
            prefix = relation_prefix
        else:
            scope_prefix = "[thread] " if scope == "thread" else "[project] "
            prefix = scope_prefix + relation_prefix
        if excerpt:
            lines.append(f"- {prefix}{title}: {excerpt}")
        else:
            lines.append(f"- {prefix}{title}")

    if not lines:
        return None, 0

    return (message_prefix + "\n".join(lines), len(sources))


def _active_persona_context_from_prompt_meta(
    prompt_meta: dict[str, Any] | None,
) -> str | None:
    if not isinstance(prompt_meta, dict):
        return None
    resolved_persona_id = prompt_meta.get("resolved_persona_id")
    if resolved_persona_id is None:
        return None
    text = str(resolved_persona_id).strip()
    return text or None


def _serialize_retrieval_plan_trace(
    *,
    plan: Any,
    user_depth: str,
) -> dict[str, Any]:
    normalized_user_depth = str(user_depth or "").strip().lower() or "auto"
    return {
        "intent": plan.intent.value,
        "user_depth": normalized_user_depth,
        "resolved_depth": plan.effective_depth.value,
        "primary_scope": plan.default_scope.value,
        "time_mode": plan.time_mode.value,
        "graph_allowance": plan.graph_allowance.value,
        "retrieval_needed": bool(plan.retrieval_needed),
        "allow_global_fallback": bool(plan.allow_global_fallback),
        "escalation_order": [step.value for step in plan.escalation_order],
        "reasons": [str(reason) for reason in plan.reasons],
    }


def _merge_thread_metadata_patch(
    thread_id: int,
    patch: dict[str, Any],
) -> bool:
    if thread_id <= 0 or not isinstance(patch, dict) or not patch:
        return False

    chatlog_db = getattr(dependencies, "chatlog_db", None)
    if chatlog_db is None:
        return False

    connect = getattr(chatlog_db, "_connect", None)
    if callable(connect):
        try:
            with connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE chat_threads
                        SET metadata = COALESCE(metadata, '{}'::jsonb) || %s::jsonb,
                            updated_at = now()
                        WHERE id = %s
                        """,
                        (json.dumps(patch), thread_id),
                    )
                    rowcount = getattr(cur, "rowcount", 0)
                    return bool(rowcount)
        except Exception:
            logger.debug(
                "[chat-completion] failed to merge thread metadata thread_id=%s",
                thread_id,
                exc_info=True,
            )

    getter = getattr(chatlog_db, "get_chat_thread", None)
    updater = getattr(chatlog_db, "update_thread_metadata", None)
    if not callable(updater):
        return False

    metadata: dict[str, Any] = {}
    if callable(getter):
        try:
            thread = getter(thread_id)
        except Exception:
            thread = None
        if isinstance(thread, dict):
            raw_metadata = thread.get("metadata")
            if isinstance(raw_metadata, dict):
                metadata.update(raw_metadata)
            elif isinstance(raw_metadata, str):
                try:
                    parsed = json.loads(raw_metadata)
                except Exception:
                    parsed = None
                if isinstance(parsed, dict):
                    metadata.update(parsed)

    metadata.update(patch)
    try:
        return bool(updater(thread_id, metadata))
    except Exception:
        logger.debug(
            "[chat-completion] failed to update thread metadata thread_id=%s",
            thread_id,
            exc_info=True,
        )
        return False


def _persist_thread_trace_candidate(
    task: ChatCompletionTask,
    trace: dict[str, Any] | None,
) -> None:
    if not isinstance(trace, dict):
        return

    task_id = str(getattr(task, "task_id", "") or "").strip()
    thread_id = int(getattr(task, "thread_id", 0) or 0)
    if not task_id or thread_id <= 0:
        return

    patch = {
        DEBUG_LATEST_COMPLETION_TASK_ID_METADATA_KEY: task_id,
        DEBUG_RAG_TRACE_CANDIDATE_METADATA_KEY: {
            "task_id": task_id,
            "thread_id": thread_id,
            "trace": dict(trace),
            "updated_at": datetime.now(UTC).isoformat(),
        },
    }
    if not _merge_thread_metadata_patch(thread_id, patch):
        logger.debug(
            "[chat-completion] failed to persist rag trace candidate thread_id=%s task_id=%s",
            thread_id,
            task_id,
        )


async def build_messages_for_llm(
    task: ChatCompletionTask,
    *,
    user_id: str | None = None,
    enable_memory_preselection_trace: bool | None = None,
    enable_memory_preselection_active: bool | None = None,
    memory_preselection_candidate_headers: Sequence[dict[str, Any]] | None = None,
    memory_preselection_persona_id: str | None = None,
    memory_preselection_identity_depth: str | None = None,
    memory_preselection_include_diary_excluded: bool | None = None,
) -> tuple[
    list[dict[str, str]],
    str,
    str,
    dict[str, Any],
    dict[str, Any] | None,
]:
    """Build contextual messages and provider/model selection for one task."""
    settings = get_settings()
    raw_task_provider = str(task.provider or "").strip()
    provider = (
        normalize_provider(raw_task_provider) if raw_task_provider else ""
    )
    thread_id = task.thread_id
    thread_info: dict[str, Any] | None = (
        dependencies.chatlog_db.get_chat_thread(thread_id)
        if hasattr(dependencies.chatlog_db, "get_chat_thread")
        else None
    )
    if not thread_info:
        raise ValueError("thread_not_found")

    thread_execution = resolve_thread_completion_settings(
        thread_info,
        requested_provider=task.provider,
        requested_model=task.model,
        requested_reasoning_mode=task.reasoning_mode,
        requested_source_mode=_requested_source_mode_from_task(task),
        settings=settings,
    )
    provider = thread_execution.provider
    routing_debug_metadata = _task_routing_debug_metadata(task)
    requested_source_mode = _requested_source_mode_from_task(task)
    effective_source_mode = _effective_source_mode_for_broker_assembly(
        thread_execution.source_mode,
        routing_debug_metadata.get("retrieval_override"),
    )

    user_system_override = task.system_override
    if isinstance(user_system_override, str):
        user_system_override = user_system_override.strip() or None
    else:
        user_system_override = None

    resolved_profile = None
    if resolve_thread_system_profile is not None:
        try:
            resolved_profile = resolve_thread_system_profile(
                thread_id,
                chatlog_db=getattr(dependencies, "chatlog_db", None),
            )
        except Exception as exc:
            logger.debug(
                "[chat-completion] thread profile resolution failed thread_id=%s err=%s",
                thread_id,
                exc,
            )
            resolved_profile = None

    profile_provider = None
    profile_model = None
    profile_temperature = None
    if resolved_profile is not None:
        raw_profile_provider = getattr(
            resolved_profile, "provider_override", None
        )
        if raw_profile_provider is not None:
            profile_provider = normalize_provider(raw_profile_provider)
        raw_profile_model = getattr(resolved_profile, "model_override", None)
        if raw_profile_model is not None:
            profile_model = normalize_model_id(raw_profile_model)
        profile_temperature = getattr(
            resolved_profile, "temperature_override", None
        )

    if not provider and task.model:
        try:
            raw_inferred_provider = resolve_provider_for_model(
                task.model, settings=settings
            )
            inferred_provider = (
                normalize_provider(raw_inferred_provider)
                if raw_inferred_provider is not None
                else None
            )
        except Exception:
            inferred_provider = None
        if inferred_provider:
            provider = inferred_provider

    if not provider and profile_provider:
        provider = profile_provider

    if not provider:
        raw_provider = str(
            settings.LLM_PROVIDER or dependencies.CHAT_PROVIDER or ""
        ).strip()
        if raw_provider:
            provider = normalize_provider(raw_provider)

    if not provider:
        first_provider = first_enabled_provider(settings=settings)
        if first_provider:
            provider = normalize_provider(first_provider)

    if validate_llm_config and provider:
        try:
            validate_llm_config(settings, provider_override=provider)
        except LLMConfigError as exc:
            logger.warning(
                "[chat-completion] LLM config error provider=%s detail=%s",
                provider,
                exc,
            )

    limit = int(task.max_context or 50)
    items = dependencies.chatlog_db.list_messages(
        thread_id, limit=limit, offset=0
    )
    try:
        items = sorted(items, key=lambda m: m.get("id") or 0)
    except Exception:
        pass

    explicit_latest_turn_message_id = _coerce_message_id(
        getattr(task, "latest_turn_message_id", None)
    )
    turn_split = split_history_and_latest_turn(
        items,
        latest_turn_message_id=explicit_latest_turn_message_id,
    )
    history_messages = turn_split["history"]
    latest_turn = turn_split["latest_turn"]
    if latest_turn is None:
        if explicit_latest_turn_message_id is not None:
            raise ValueError("thread_target_turn_missing")
        raise ValueError("thread_has_no_usable_context")

    conversation_messages = [*history_messages, latest_turn]
    # Retrieval must follow the latest user turn, not earlier history.
    retrieval_query = render_content_for_inference(latest_turn.get("content"))
    latest_turn_trace_fields = _latest_turn_trace_fields(
        latest_turn,
        retrieval_query=retrieval_query,
    )

    context: list[dict[str, str]] = []
    latest_user_meta: dict[str, Any] | None = None
    for msg in conversation_messages:
        role = str(msg.get("role") or "").strip()
        raw_content = msg.get("content")
        if isinstance(raw_content, str):
            attachments, clean_text = extract_attachments_and_text(raw_content)
            if role == "user":
                latest_user_meta = {
                    "id": msg.get("id"),
                    "text": clean_text,
                    "attachments": attachments,
                }
        if _should_skip_history_message_for_image_turn(msg, latest_user_meta):
            continue
        content = render_content_for_inference(msg.get("content"))
        if content and content.strip() and content.strip().lower() != "null":
            context.append({"role": role, "content": content})

    if not context:
        raise ValueError("thread_has_no_usable_context")

    depth = str(task.depth_mode or "normal").strip().lower()
    task_user_id = str(user_id or getattr(task, "user_id", "") or "").strip()
    user_for_context = (
        str(
            (thread_info or {}).get("user_id")
            or dependencies.get_single_user_id()
            or "default"
        ).strip()
        or "default"
    )
    context_user_id = user_for_context or task_user_id
    source_mode = effective_source_mode

    project_id_for_prompt: int | None = None
    if thread_info:
        try:
            raw_project_id = thread_info.get("project_id")
            if raw_project_id is not None:
                project_id_for_prompt = int(raw_project_id)
        except (TypeError, ValueError):
            project_id_for_prompt = None

    bundle: dict[str, Any] = {}
    trace: dict[str, Any] | None = None
    trace_candidate: dict[str, Any] | None = None
    assembly_succeeded = False
    retrieval_policy_obj: Any | None = None
    retrieval_policy: dict[str, Any] | None = None
    broker: ContextBroker | None = None
    try:
        effective_source_mode = _resolve_effective_source_mode_for_assembly(
            source_mode,
            routing_debug_metadata.get("retrieval_override"),
        )
        retrieval_policy_obj = resolve_context_assembly_policy(
            retrieval_query,
            depth,
            source_mode=effective_source_mode,
            retrieval_override=routing_debug_metadata.get("retrieval_override"),
            active_thread_id=thread_id,
            active_project_id=project_id_for_prompt,
            active_persona=None,
        )
        retrieval_policy = retrieval_policy_obj.as_dict()
        broker_vector_store = dependencies._vector_store
        if source_mode in {SOURCE_MODE_WORKSPACE, SOURCE_MODE_OBSIDIAN_ONLY}:
            broker_vector_store = _workspace_completion_vector_store()
        broker = ContextBroker(
            dependencies.chatlog_db,
            broker_vector_store,
            dependencies._memory_store,
            dependencies._sensors,
            settings=settings,
        )
        bundle, trace = await _assemble_context_bundle(
            broker,
            thread_id=thread_id,
            query=retrieval_query,
            depth_mode=depth,
            user_id=context_user_id,
            request_user_id=task_user_id or None,
            project_id=project_id_for_prompt,
            source_mode=source_mode,
            retrieval_override=routing_debug_metadata.get("retrieval_override"),
            retrieval_policy=retrieval_policy,
            enable_memory_preselection_trace=enable_memory_preselection_trace,
            enable_memory_preselection_active=enable_memory_preselection_active,
            memory_preselection_candidate_headers=memory_preselection_candidate_headers,
            memory_preselection_persona_id=memory_preselection_persona_id,
            memory_preselection_identity_depth=memory_preselection_identity_depth,
            memory_preselection_include_diary_excluded=memory_preselection_include_diary_excluded,
        )
        if thread_execution.persona_id:
            # Thread config personaId is request-scoped input, not actor
            # replacement. It only selects the persona layer for this request.
            bundle["requested_persona"] = thread_execution.persona_id
        if user_system_override:
            bundle.setdefault("user_system_override", user_system_override)
        if task_user_id:
            prompt_meta = dict(bundle.get("_prompt_meta") or {})
            prompt_meta["request_user_id"] = task_user_id
            bundle["_prompt_meta"] = prompt_meta
        assembly_succeeded = True
    except Exception as exc:
        logger.warning(
            "[chat-completion] context assemble failed depth=%s err=%s",
            depth,
            exc,
        )
        bundle = {}
    else:
        trace_candidate = trace

    if assembly_succeeded and isinstance(bundle, dict):
        try:
            context_request_results = await _apply_context_request_plans(
                broker=broker,
                task=task,
                bundle=bundle,
                user_id=context_user_id,
                project_id=project_id_for_prompt,
            )
        except Exception as exc:
            logger.warning(
                "[chat-completion] context request plan application failed depth=%s err=%s",
                depth,
                exc,
            )
            context_request_results = []
    if isinstance(trace, dict):
        trace = dict(trace)
        trace["context_request_results"] = list(context_request_results)

    if (
        isinstance(bundle, dict)
        and bundle.get("retrieval_status") == "no_obsidian_results"
    ):
        raise ValueError("Obsidian-only retrieval returned no results")

    if isinstance(bundle, dict):
        if thread_execution.persona_id:
            # Keep the request-scoped selector with the bundle so the prompt
            # builder can resolve the correct persona layer.
            bundle["requested_persona"] = thread_execution.persona_id
        if user_system_override:
            bundle.setdefault("user_system_override", user_system_override)

    messages_for_llm: list[dict[str, str]] = []
    prompt_meta: dict[str, Any] = {}
    retrieved_context_messages: list[dict[str, str]] = []
    completion_assembly = {
        "history": history_messages,
        "latest_turn": latest_turn,
        "retrieved_context": retrieved_context_messages,
        "context_request_results": context_request_results,
    }
    completion_assembly.update(latest_turn_trace_fields)
    identity_context = {
        "preferred_name": getattr(task, "preferred_name", None),
        "profession": getattr(task, "profession", None),
        "guardian_name": getattr(task, "guardian_name", None),
    }

    try:
        if build_guardian_system_prompt:
            system_content, prompt_meta = build_guardian_system_prompt(
                user_id=user_for_context,
                project_id=project_id_for_prompt,
                depth=depth,
                bundle=bundle,
                profile=resolved_profile,
                identity_context=identity_context,
            )
            token_est = prompt_meta.get(
                "estimated_tokens", _estimate_tokens(system_content)
            )
            if token_est > 2048:
                logger.warning(
                    "[chat-completion] large system prompt user=%s project_id=%s est_tokens=%s",
                    user_for_context,
                    project_id_for_prompt,
                    token_est,
                )
        else:
            system_content = (
                "You are Guardian, the Codexify assistant. "
                "You must be honest, precise, and safe. "
                "Prefer clear, structured answers for a busy software engineer. "
                "If you are uncertain, say so explicitly and avoid fabrication."
            )
    except Exception as exc:
        logger.warning(
            "[chat-completion] failed to build system prompt: %s", exc
        )
        system_content = (
            "You are Guardian, a careful and honest AI assistant. "
            "Answer concisely, avoid speculation, and clearly mark any uncertainty."
        )

    latest_turn_instruction = _latest_turn_instruction_message(
        completion_assembly
    )

    if isinstance(bundle, dict):
        try:
            existing_meta = bundle.get("_prompt_meta") or {}
            merged_meta = dict(existing_meta)
            merged_meta.update(prompt_meta or {})
            bundle["_prompt_meta"] = merged_meta
        except Exception:
            bundle["_prompt_meta"] = dict(prompt_meta or {})

    messages_for_llm.append({"role": "system", "content": system_content})
    if latest_turn_instruction:
        messages_for_llm.append(
            {"role": "system", "content": latest_turn_instruction}
        )

    doc_message, doc_count = _build_document_context_message(bundle)
    if doc_message:
        retrieved_context_messages.append(
            {"role": "system", "content": doc_message}
        )

    context_message, context_meta = build_context_system_message_with_meta(
        bundle
    )
    if isinstance(context_meta, dict):
        obsidian_hits = _obsidian_semantic_hits_from_bundle(
            bundle if isinstance(bundle, dict) else None
        )
        semantic_meta = context_meta.get("semantic")
        semantic_injected = bool(
            semantic_meta.get("injected")
            if isinstance(semantic_meta, dict)
            else False
        )
        context_meta["obsidian"] = {
            "count": len(obsidian_hits),
            "injected": bool(obsidian_hits and semantic_injected),
        }
    if context_message:
        retrieved_context_messages.append(
            {"role": "system", "content": context_message}
        )
    prompt_meta["context"] = context_meta
    prompt_meta.setdefault("docs", {})
    prompt_meta["docs"].update(
        {"count": doc_count, "injected": bool(doc_message)}
    )
    if isinstance(bundle, dict):
        try:
            merged_meta = dict(bundle.get("_prompt_meta") or {})
            merged_meta.update(prompt_meta or {})
            bundle["_prompt_meta"] = merged_meta
        except Exception:
            bundle["_prompt_meta"] = dict(prompt_meta or {})
        bundle["_attachment_meta"] = {
            "latest_user": latest_user_meta,
        }
        bundle["_completion_assembly"] = completion_assembly

    if trace is None:
        trace = dict(latest_turn_trace_fields)
    if isinstance(trace, dict):
        trace = dict(trace)
        trace.update(latest_turn_trace_fields)
        trace.update(routing_debug_metadata)
        trace.setdefault("source_mode", effective_source_mode)
        trace["context_request_results"] = list(context_request_results)

    if retrieval_policy_obj is not None and isinstance(trace, dict):
        try:
            trace = dict(trace)
            trace[RETRIEVAL_PLAN_TRACE_KEY] = _serialize_retrieval_plan_trace(
                plan=retrieval_policy_obj.plan,
                user_depth=depth,
            )
            trace["retrieval_policy"] = retrieval_policy_obj.as_dict()
        except Exception as exc:
            logger.warning(
                "[chat-completion] retrieval policy serialization failed depth=%s err=%s",
                depth,
                exc,
            )

    if isinstance(bundle, dict):
        (
            semantic_items,
            image_suppression,
        ) = _filter_image_refusal_semantic_context(
            bundle.get("semantic"),
            latest_user_meta,
        )
        bundle["semantic"] = semantic_items
        merged_suppression = _merge_retrieval_suppression_summaries(
            bundle.get("retrieval_suppression"),
            image_suppression,
        )
        if merged_suppression is not None:
            bundle["retrieval_suppression"] = merged_suppression
            if isinstance(trace, dict):
                trace = dict(trace)
                trace["retrieval_suppression"] = merged_suppression

    if isinstance(trace_candidate, dict):
        _persist_thread_trace_candidate(task, trace)

    payload_summary: dict[str, Any] = {}
    attachment_meta = (
        bundle.get("_attachment_meta") if isinstance(bundle, dict) else None
    )
    latest_user_attachment_meta = (
        attachment_meta.get("latest_user")
        if isinstance(attachment_meta, dict)
        else None
    )
    image_attachment_count = len(
        _image_attachments_from_meta(latest_user_attachment_meta)
    )
    retrieval_policy = None
    retrieval_executed = None
    retrieval_absence_reason = None
    if isinstance(trace, dict):
        retrieval_policy = trace.get("effective_policy") or trace.get(
            "retrieval_policy"
        )
        retrieval_executed = trace.get("retrieval_executed")
        retrieval_absence_reason = trace.get("retrieval_absence_reason")
    if retrieval_executed is None:
        retrieval_executed = bool(
            trace.get(RETRIEVAL_PLAN_TRACE_KEY, {}).get("retrieval_needed")
            if isinstance(trace, dict)
            and isinstance(trace.get(RETRIEVAL_PLAN_TRACE_KEY), dict)
            else False
        )
    retrieval_provenance = _build_retrieval_provenance(
        requested_source_mode=requested_source_mode,
        normalized_source_mode=trace.get("source_mode")
        if isinstance(trace, dict)
        else effective_source_mode,
        bundle=bundle if isinstance(bundle, dict) else None,
    )

    retrieval_suppression = (
        bundle.get("_retrieval_suppression_trace")
        if isinstance(bundle, dict)
        else {"items": [], "summary": {"total_suppressed": 0}}
    )
    if not isinstance(retrieval_suppression, dict):
        retrieval_suppression = {
            "items": [],
            "summary": {"total_suppressed": 0},
        }

    retained_result_count = 0
    if retrieval_executed and retrieval_absence_reason is None:
        if isinstance(bundle, dict):
            for key in ("semantic", "obsidian", "memory", "graph"):
                retained_result_count += len(
                    [
                        item
                        for item in bundle.get(key, [])
                        if isinstance(item, dict)
                    ]
                )
            docs_value = bundle.get("docs")
            if isinstance(docs_value, dict):
                for key in ("project", "thread", "global"):
                    retained_result_count += len(
                        [
                            item
                            for item in docs_value.get(key, [])
                            if isinstance(item, dict)
                        ]
                    )
    if retained_result_count <= 0:
        retrieval_absence_reason = (
            TraceSnapshotAbsenceReason.RETRIEVAL_NO_CANDIDATES.value
        )

    if isinstance(trace, dict):
        trace["retrieval_policy"] = retrieval_policy
        trace["retrieval_provenance"] = retrieval_provenance
        trace["retrieval_suppression"] = dict(retrieval_suppression)
        trace["retrieval_executed"] = retrieval_executed
        trace["retrieval_absence_reason"] = retrieval_absence_reason
    payload_summary["retrieval_policy"] = retrieval_policy
    payload_summary["retrieval_provenance"] = retrieval_provenance
    payload_summary["retrieval_suppression"] = dict(retrieval_suppression)
    payload_summary["retrieval_executed"] = retrieval_executed
    payload_summary["retrieval_absence_reason"] = retrieval_absence_reason

    messages_for_llm.extend(retrieved_context_messages)
    messages_for_llm.extend(context)

    model = normalize_model_id(thread_execution.model)
    if not model:
        model = normalize_model_id(task.model)
    if not model and profile_model:
        model = profile_model
    if not model and provider:
        model = (
            default_model_for_provider(provider, settings)
            or dependencies.DEFAULT_MODEL
            or ""
        )
    if not model:
        model = dependencies.DEFAULT_MODEL or ""

    temperature = getattr(task, "temperature", None)
    if temperature is None and profile_temperature is not None:
        temperature = profile_temperature

    task.provider = provider or None
    task.model = model or None
    task.temperature = temperature if temperature is not None else None

    return messages_for_llm, provider, model, bundle, trace


def _execute_bounded_tool_turn_completion(
    task: ChatCompletionTask,
    *,
    messages_for_llm: list[dict[str, Any]],
    provider: str,
    model: str,
    bundle: dict[str, Any] | None,
    trace: dict[str, Any] | None,
    base_payload_summary: dict[str, Any],
    token_callback: Callable[[str], None] | None = None,
    chunk_callback: Callable[[str], None] | None = None,
    cancel_check: Callable[[], bool] | None = None,
) -> dict[str, Any]:
    current_messages = [dict(message) for message in messages_for_llm]
    request_id = str(getattr(task, "task_id", "") or "").strip() or None
    latest_turn_message_id = _extract_latest_turn_message_id(task)
    final_provider = provider
    final_model = model
    tool_turn_id: str | None = None
    tool_turn_state = ToolTurnState.IDLE.value
    loop_stop_reason = ToolLoopStopReason.PLAIN_ANSWER.value
    command_run_id: str | None = None
    command_status: str | None = None
    command_error: dict[str, Any] | None = None
    execution: dict[str, Any] | None = None
    model_selection: dict[str, Any] | None = _build_model_selection_trace(
        requested_provider=str(
            getattr(task, "requested_provider", None)
            or getattr(task, "provider", None)
            or ""
        ),
        requested_model=str(
            getattr(task, "requested_model", None)
            or getattr(task, "model", None)
            or ""
        ),
        attempted_provider=provider,
        attempted_model=model,
        resolved_provider=provider,
        resolved_model=model,
        final_provider=final_provider,
        final_model=final_model,
        selection_source=str(getattr(task, "selection_source", "") or ""),
        fallback_reason=None,
        model_resolution=None,
    )

    def _build_result(
        *,
        assistant_text: str,
        tool_turn_state_value: str,
        loop_stop_reason_value: str,
    ) -> dict[str, Any]:
        payload_summary = dict(base_payload_summary or {})
        payload_summary.update(
            build_sanitized_payload_summary(
                current_messages,
                bundle,
                provider=final_provider,
                model=final_model,
            )
        )
        for key in (
            "source_mode",
            "effective_source_mode",
            "normalized_source_mode",
            "requested_source_mode",
            "effective_policy",
            "retrieval_posture",
            "retrieval_provenance",
            "retrieval_suppression",
            "semantic_count",
            "obsidian_count",
            "semantic_injected",
            "obsidian_injected",
            "retrieval_injected",
            "image_routing_path",
            "image_routing_absence_reason",
            "image_attachment_count",
            "derived_image_context_injected",
        ):
            if key in base_payload_summary:
                payload_summary[key] = base_payload_summary[key]
        _preserve_workspace_evidence_fields(
            payload_summary,
            base_payload_summary,
        )
        payload_summary.update(
            {
                "messageId": latest_turn_message_id,
                "requestId": request_id,
                "toolTurnId": tool_turn_id,
                "toolTurnState": tool_turn_state_value,
                "loopStopReason": loop_stop_reason_value,
                "commandRunId": command_run_id,
                "message_id": latest_turn_message_id,
                "request_id": request_id,
                "tool_turn_id": tool_turn_id,
                "tool_turn_state": tool_turn_state_value,
                "loop_stop_reason": loop_stop_reason_value,
                "command_run_id": command_run_id,
            }
        )
        if model_selection is not None:
            payload_summary["model_selection"] = dict(model_selection)
            payload_summary["requested_provider"] = model_selection[
                "requested_provider"
            ]
            payload_summary["requested_model"] = model_selection[
                "requested_model"
            ]
            payload_summary["final_provider"] = model_selection[
                "final_provider"
            ]
            payload_summary["final_model"] = model_selection["final_model"]
            payload_summary["selection_source"] = model_selection[
                "selection_source"
            ]
            payload_summary["policy_reason"] = model_selection["policy_reason"]
            payload_summary["fallback_reason"] = model_selection[
                "fallback_reason"
            ]
            payload_summary["model_resolution"] = model_selection[
                "model_resolution"
            ]
            if isinstance(trace, dict):
                trace["model_selection"] = dict(model_selection)
        if command_status is not None:
            payload_summary["command_status"] = command_status
        if command_error is not None:
            payload_summary["command_error"] = command_error
        if execution is not None:
            payload_summary["execution"] = execution
        return _tool_turn_completion_result(
            task=task,
            assistant_text=assistant_text,
            provider=final_provider,
            model=final_model,
            bundle=bundle,
            trace=trace,
            payload_summary=payload_summary,
            tool_turn_id=tool_turn_id,
            tool_turn_state=tool_turn_state_value,
            loop_stop_reason=loop_stop_reason_value,
            command_run_id=command_run_id,
            command_status=command_status,
            command_error=command_error,
            message_id=latest_turn_message_id,
            execution=execution,
        )

    first_output = _execute_completion_attempt(
        task=task,
        messages_for_llm=current_messages,
        provider=provider,
        model=model,
        bundle=bundle,
        token_callback=token_callback,
        chunk_callback=chunk_callback,
        cancel_check=cancel_check,
    )
    normalized_first_output = normalize_completion_output(first_output)
    if normalized_first_output.kind != "tool_decision":
        assistant_text = normalized_first_output.text or ""
        if not assistant_text.strip():
            assistant_text = "No assistant response was generated."
        execution = {
            "attempted_provider": provider,
            "attempted_model": model,
            "final_provider": provider,
            "final_model": model,
            "fallback_triggered": False,
            "tool_turn_used": False,
        }
        return _build_result(
            assistant_text=assistant_text,
            tool_turn_state_value=ToolTurnState.IDLE.value,
            loop_stop_reason_value=ToolLoopStopReason.PLAIN_ANSWER.value,
        )

    tool_turn_id = str(uuid.uuid4())
    if not normalized_first_output.command_id:
        raise ToolLoopExecutionError(
            "tool_decision_missing_command_id",
            metadata=_tool_loop_identity_fields(
                task=task,
                tool_turn_id=tool_turn_id,
                tool_turn_state=ToolTurnState.FAILED.value,
                loop_stop_reason=ToolLoopStopReason.TOOL_DECISION_INVALID.value,
                command_run_id=None,
            ),
        )

    tool_turn_state = ToolTurnState.DECISION_RECEIVED.value
    invocation = BoundedToolTurnInvocation(
        tool_turn_id=tool_turn_id,
        request_id=request_id or tool_turn_id,
        command_id=normalized_first_output.command_id,
        actor=ActorSpec(
            kind="system",
            id=request_id or tool_turn_id,
            session_id=tool_turn_id,
        ),
        arguments=_tool_turn_invoke_arguments(
            normalized_first_output.arguments or {}
        ),
        idempotency_key=(
            f"{request_id or tool_turn_id}:{tool_turn_id}:{normalized_first_output.command_id}"
        ),
    )
    invoke_request = InvokeRequest(
        invoke_version="1.0",
        command_id=invocation.command_id,
        actor=invocation.actor,
        arguments=invocation.arguments,
        idempotency_key=invocation.idempotency_key,
    )
    from guardian.routes import command_bus as command_bus_routes

    try:
        invoke_result = execute_invoke(
            payload=invoke_request,
            auth_subject=invocation.actor.id,
            inbound_headers={},
            store=command_bus_routes._store,
            app=_command_bus_app(),
            execution_lane="tools",
            allow_write_execution=False,
            confirmation_granted=False,
        )
        command_result = (
            asyncio.run(invoke_result)
            if inspect.isawaitable(invoke_result)
            else invoke_result
        )
    except Exception as exc:
        command_error = {
            "error": str(exc),
            "error_type": exc.__class__.__name__,
        }
        raise ToolLoopExecutionError(
            "tool_command_execution_failed",
            metadata=_tool_loop_identity_fields(
                task=task,
                tool_turn_id=tool_turn_id,
                tool_turn_state=ToolTurnState.FAILED.value,
                loop_stop_reason=ToolLoopStopReason.TOOL_COMMAND_FAILED.value,
                command_run_id=None,
            )
            | {
                "command_id": normalized_first_output.command_id,
                "command_error": command_error,
            },
        ) from exc

    if not isinstance(command_result, dict):
        command_result = {"inline_result": command_result}
    command_run_id = str(command_result.get("run_id") or "").strip() or None
    command_status = str(command_result.get("status") or "").strip() or None
    if command_status == "blocked":
        loop_stop_reason = ToolLoopStopReason.TOOL_COMMAND_BLOCKED.value
    tool_turn_state = ToolTurnState.COMMAND_DISPATCHED.value

    current_messages = _append_tool_result_message(
        current_messages,
        tool_turn_id=tool_turn_id,
        decision={
            "command_id": normalized_first_output.command_id,
            "arguments": normalized_first_output.arguments or {},
        },
        command_result=command_result,
    )
    tool_turn_state = ToolTurnState.RESULT_REINJECTED.value
    second_output = _execute_completion_attempt(
        task=task,
        messages_for_llm=current_messages,
        provider=provider,
        model=model,
        bundle=bundle,
        token_callback=token_callback,
        chunk_callback=chunk_callback,
        cancel_check=cancel_check,
    )
    normalized_second_output = normalize_completion_output(second_output)
    if normalized_second_output.kind == "tool_decision":
        raise ToolLoopExecutionError(
            "tool_turn_limit_reached",
            metadata=_tool_loop_identity_fields(
                task=task,
                tool_turn_id=tool_turn_id,
                tool_turn_state=ToolTurnState.LIMIT_REACHED.value,
                loop_stop_reason=ToolLoopStopReason.TOOL_TURN_LIMIT_REACHED.value,
                command_run_id=command_run_id,
            )
            | {
                "command_id": normalized_second_output.command_id,
            },
        )

    assistant_text = normalized_second_output.text or ""
    if not assistant_text.strip():
        assistant_text = "No assistant response was generated."
    loop_stop_reason = ToolLoopStopReason.TOOL_TURN_COMPLETED.value
    tool_turn_state = ToolTurnState.COMPLETED.value
    execution = {
        "attempted_provider": provider,
        "attempted_model": model,
        "final_provider": provider,
        "final_model": model,
        "fallback_triggered": False,
        "tool_turn_used": True,
    }
    return _build_result(
        assistant_text=assistant_text,
        tool_turn_state_value=tool_turn_state,
        loop_stop_reason_value=loop_stop_reason,
    )


def run_chat_completion_task(
    task: ChatCompletionTask,
    *,
    user_id: str | None = None,
    enable_memory_preselection_trace: bool | None = None,
    enable_memory_preselection_active: bool | None = None,
    memory_preselection_candidate_headers: Sequence[dict[str, Any]] | None = None,
    memory_preselection_persona_id: str | None = None,
    memory_preselection_identity_depth: str | None = None,
    memory_preselection_include_diary_excluded: bool | None = None,
    token_callback: Callable[[str], None] | None = None,
    chunk_callback: Callable[[str], None] | None = None,
    cancel_check: Callable[[], bool] | None = None,
    persist_assistant_message: bool = True,
) -> dict[str, Any]:
    """Execute one completion with shared context assembly/provider routing."""
    compat_builder = _build_messages_for_llm_compat
    try:
        compat_signature = inspect.signature(compat_builder)
    except (TypeError, ValueError):
        compat_signature = None
    compat_accepts_kwargs = False
    if compat_signature is not None:
        compat_accepts_kwargs = any(
            parameter.kind == inspect.Parameter.VAR_KEYWORD
            for parameter in compat_signature.parameters.values()
        )

    def _compat_accepts(name: str) -> bool:
        return compat_accepts_kwargs or (
            compat_signature is not None and name in compat_signature.parameters
        )

    compat_call_kwargs: dict[str, Any] = {}
    if _compat_accepts("user_id"):
        compat_call_kwargs["user_id"] = user_id
    if (
        enable_memory_preselection_trace is not None
        and _compat_accepts("enable_memory_preselection_trace")
    ):
        compat_call_kwargs["enable_memory_preselection_trace"] = bool(
            enable_memory_preselection_trace
        )
    if (
        enable_memory_preselection_active is not None
        and _compat_accepts("enable_memory_preselection_active")
    ):
        compat_call_kwargs["enable_memory_preselection_active"] = bool(
            enable_memory_preselection_active
        )
    if (
        memory_preselection_candidate_headers is not None
        and _compat_accepts("memory_preselection_candidate_headers")
    ):
        compat_call_kwargs["memory_preselection_candidate_headers"] = (
            memory_preselection_candidate_headers
        )
    if (
        memory_preselection_persona_id is not None
        and _compat_accepts("memory_preselection_persona_id")
    ):
        compat_call_kwargs["memory_preselection_persona_id"] = (
            memory_preselection_persona_id
        )
    if (
        memory_preselection_identity_depth is not None
        and _compat_accepts("memory_preselection_identity_depth")
    ):
        compat_call_kwargs["memory_preselection_identity_depth"] = (
            memory_preselection_identity_depth
        )
    if (
        memory_preselection_include_diary_excluded is not None
        and _compat_accepts("memory_preselection_include_diary_excluded")
    ):
        compat_call_kwargs["memory_preselection_include_diary_excluded"] = bool(
            memory_preselection_include_diary_excluded
        )

    build_result: tuple[
        list[dict[str, str]],
        str,
        str,
        dict[str, Any],
        dict[str, Any] | None,
    ] = asyncio.run(compat_builder(task, **compat_call_kwargs))
    messages_for_llm, provider, model, bundle, trace = build_result

    settings = get_settings()
    requested_source_mode = (
        str(getattr(task, "requested_source_mode", "") or "").strip() or None
    )
    requested_provider = normalize_provider(
        getattr(task, "requested_provider", None)
    ) or normalize_provider(getattr(task, "provider", None))
    requested_model = normalize_model_id(
        getattr(task, "requested_model", None)
    ) or normalize_model_id(getattr(task, "model", None))
    messages_for_llm, routing_meta = _apply_image_attachment_routing(
        messages_for_llm,
        bundle=bundle,
        provider=provider,
        model=model,
        settings=settings,
    )
    routing_debug_metadata = _task_routing_debug_metadata(task)
    image_attachment_count = int(
        routing_meta.get("image_attachment_count", 0) or 0
    )
    routing_debug_image_attachment_count = int(
        routing_debug_metadata.get("image_attachment_count", 0) or 0
    )
    if routing_debug_image_attachment_count > image_attachment_count:
        image_attachment_count = routing_debug_image_attachment_count
        routing_meta["image_attachment_count"] = image_attachment_count
    if image_attachment_count <= 0 and isinstance(trace, dict):
        latest_turn_image_hint = str(
            trace.get("retrieval_query")
            or trace.get("latest_turn_content")
            or ""
        ).strip()
        if (
            "Attached image:" in latest_turn_image_hint
            or "cfy-media:image:" in latest_turn_image_hint
        ):
            image_attachment_count = 1
            routing_meta["image_attachment_count"] = image_attachment_count
    if image_attachment_count <= 0:
        try:
            raw_messages = dependencies.chatlog_db.list_messages(
                task.thread_id,
                limit=50,
                offset=0,
            )
            try:
                raw_messages = sorted(
                    raw_messages, key=lambda item: item.get("id") or 0
                )
            except Exception:
                pass
            latest_split = split_history_and_latest_turn(
                raw_messages,
                latest_turn_message_id=_extract_latest_turn_message_id(task),
            )
            latest_turn_message = latest_split.get("latest_turn")
            if isinstance(latest_turn_message, dict):
                latest_turn_content = str(
                    latest_turn_message.get("content") or ""
                ).strip()
                if latest_turn_content:
                    attachments, _ = extract_attachments_and_text(
                        latest_turn_content
                    )
                    image_attachment_count = len(
                        [
                            item
                            for item in attachments
                            if isinstance(item, dict)
                            and str(item.get("kind") or "").strip().lower()
                            == "image"
                        ]
                    )
                    if image_attachment_count > 0:
                        routing_meta[
                            "image_attachment_count"
                        ] = image_attachment_count
        except Exception:
            logger.debug(
                "[chat-completion] image attachment inference from thread messages failed",
                exc_info=True,
            )
    if image_attachment_count <= 0:
        for candidate_message in reversed(messages_for_llm):
            if not isinstance(candidate_message, dict):
                continue
            if (
                str(candidate_message.get("role") or "").strip().lower()
                != "user"
            ):
                continue
            candidate_content = candidate_message.get("content")
            if isinstance(
                candidate_content, list
            ) and messages_contain_image_payload([candidate_message]):
                image_attachment_count = 1
                routing_meta["image_attachment_count"] = image_attachment_count
                break
            candidate_text = str(candidate_content or "").strip()
            if (
                "Attached image:" in candidate_text
                or "cfy-media:image:" in candidate_text
            ):
                image_attachment_count = 1
                routing_meta["image_attachment_count"] = image_attachment_count
                break
    payload_summary: dict[str, Any] = {}
    (
        image_attachment_count,
        image_routing_path,
        image_routing_absence_reason,
    ) = _normalize_completion_image_routing_truth(
        task=task,
        provider=provider,
        model=model,
        settings=settings,
        messages_for_llm=messages_for_llm,
        routing_meta=routing_meta,
        trace=trace,
        payload_summary=payload_summary,
    )

    payload_summary = build_sanitized_payload_summary(
        messages_for_llm,
        bundle,
        provider=provider,
        model=model,
        requested_provider=requested_provider,
        requested_model=requested_model,
        requested_source_mode=requested_source_mode,
    )
    payload_summary.update(
        {
            "image_routing_path": image_routing_path,
            "image_routing_absence_reason": image_routing_absence_reason,
            "image_attachment_count": image_attachment_count,
            "derived_image_context_injected": routing_meta.get(
                "derived_image_context_injected", False
            ),
        }
    )
    payload_summary.update(routing_debug_metadata)
    if isinstance(trace, dict):
        trace = dict(trace)
        trace["image_routing_path"] = image_routing_path
        trace["image_attachment_count"] = image_attachment_count
        trace["image_routing_absence_reason"] = image_routing_absence_reason
    trace_source_mode = (
        trace.get("source_mode") if isinstance(trace, dict) else None
    )
    effective_policy = (
        trace.get("effective_policy") if isinstance(trace, dict) else None
    )
    payload_summary["source_mode"] = trace_source_mode
    payload_summary["effective_source_mode"] = trace_source_mode
    payload_summary["normalized_source_mode"] = trace_source_mode
    payload_summary["effective_policy"] = effective_policy
    if isinstance(trace, dict) and trace.get("retrieval_policy") is not None:
        payload_summary["retrieval_policy"] = trace.get("retrieval_policy")
    model_resolution = None
    if provider == "local":
        try:
            local_model_resolution = resolve_local_execution_model(
                settings=settings,
                requested_model=requested_model or model,
            )
            model_resolution = local_model_resolution.as_dict()
        except Exception:
            model_resolution = None
    selection_source = (
        str(getattr(task, "selection_source", "") or "").strip() or None
    )
    if isinstance(model_resolution, dict):
        resolution_source = str(model_resolution.get("source") or "").strip()
        if resolution_source:
            selection_source = resolution_source
    if not selection_source:
        selection_source = (
            "explicit" if (requested_provider or requested_model) else "default"
        )
    attempted_provider = requested_provider or provider
    attempted_model = requested_model or model
    resolved_provider = provider
    resolved_model = model
    final_provider = provider
    final_model = (
        str(model_resolution.get("model") or "").strip()
        if isinstance(model_resolution, dict)
        else ""
    ) or model
    fallback_reason = None
    if isinstance(model_resolution, dict):
        fallback_reason = (
            str(model_resolution.get("message") or "").strip() or None
        )
    payload_summary["requested_provider"] = requested_provider
    payload_summary["requested_model"] = requested_model
    payload_summary["attempted_provider"] = attempted_provider
    payload_summary["attempted_model"] = attempted_model
    payload_summary["resolved_provider"] = resolved_provider
    payload_summary["resolved_model"] = resolved_model
    payload_summary["final_provider"] = final_provider
    payload_summary["final_model"] = final_model
    payload_summary["selection_source"] = selection_source
    payload_summary["fallback_reason"] = fallback_reason
    if isinstance(model_resolution, dict):
        payload_summary["model_resolution"] = model_resolution
    retrieval_provenance = _build_retrieval_provenance(
        requested_source_mode=requested_source_mode,
        normalized_source_mode=trace_source_mode,
        bundle=bundle if isinstance(bundle, dict) else None,
    )
    payload_summary["retrieval_provenance"] = retrieval_provenance
    if (
        isinstance(trace, dict)
        and trace.get("retrieval_suppression") is not None
    ):
        payload_summary["retrieval_suppression"] = trace.get(
            "retrieval_suppression"
        )
    retrieval_posture = _build_retrieval_posture(
        source_mode=trace_source_mode,
        retrieval_override=routing_debug_metadata.get("retrieval_override"),
        widen_reason=(
            trace.get("widen_reason") if isinstance(trace, dict) else None
        ),
    )
    if retrieval_posture is not None:
        payload_summary["retrieval_posture"] = retrieval_posture
        if isinstance(trace, dict):
            trace = dict(trace)
            trace["retrieval_posture"] = retrieval_posture
    if (
        isinstance(trace, dict)
        and trace.get("context_request_results") is not None
    ):
        payload_summary["context_request_results"] = list(
            trace.get("context_request_results") or []
        )
    model_selection = _build_model_selection_metadata(
        requested_provider=requested_provider,
        requested_model=requested_model,
        attempted_provider=attempted_provider,
        attempted_model=attempted_model,
        resolved_provider=resolved_provider,
        resolved_model=resolved_model,
        final_provider=final_provider,
        final_model=final_model,
        selection_source=selection_source,
        fallback_reason=fallback_reason,
        model_resolution=model_resolution,
    )
    payload_summary["model_selection"] = model_selection
    if isinstance(trace, dict):
        trace = dict(trace)
        trace["model_selection"] = model_selection
        trace.setdefault("requested_provider", requested_provider)
        trace.setdefault("requested_model", requested_model)
    if isinstance(bundle, dict):
        prompt_meta = dict(bundle.get("_prompt_meta") or {})
        prompt_meta["images"] = {
            "routing_path": routing_meta.get("image_routing_path"),
            "attachment_count": routing_meta.get("image_attachment_count", 0),
            "derived_context_injected": routing_meta.get(
                "derived_image_context_injected", False
            ),
        }
        bundle["_prompt_meta"] = prompt_meta

    result = _execute_bounded_tool_turn_completion(
        task,
        messages_for_llm=messages_for_llm,
        provider=provider,
        model=model,
        bundle=bundle,
        trace=trace,
        base_payload_summary=payload_summary,
        token_callback=token_callback,
        chunk_callback=chunk_callback,
        cancel_check=cancel_check,
    )
    assistant_text = str(result.get("assistant_text") or "")
    payload_summary = dict(result.get("payload_summary") or payload_summary)
    payload_summary["requested_provider"] = requested_provider
    payload_summary["requested_model"] = requested_model
    payload_summary["attempted_provider"] = attempted_provider
    payload_summary["attempted_model"] = attempted_model
    payload_summary["resolved_provider"] = resolved_provider
    payload_summary["resolved_model"] = resolved_model
    payload_summary["final_provider"] = final_provider
    payload_summary["final_model"] = final_model
    payload_summary["selection_source"] = selection_source
    payload_summary["fallback_reason"] = fallback_reason
    if isinstance(model_resolution, dict):
        payload_summary["model_resolution"] = model_resolution
    payload_summary["model_selection"] = model_selection
    result_payload_summary = result.get("payload_summary")
    merged_payload_summary = dict(payload_summary or {})
    if isinstance(result_payload_summary, dict):
        merged_payload_summary.update(result_payload_summary)
    base_retrieval_posture = (
        payload_summary.get("retrieval_posture")
        if isinstance(payload_summary, dict)
        else None
    )
    if merged_payload_summary.get("retrieval_posture") is None and isinstance(
        base_retrieval_posture, dict
    ):
        merged_payload_summary["retrieval_posture"] = dict(
            base_retrieval_posture
        )
    _preserve_workspace_evidence_fields(
        merged_payload_summary,
        payload_summary,
    )
    payload_summary = merged_payload_summary
    request_id = str(result.get("requestId") or _completion_request_id(task))
    trace_result = (
        result.get("trace") if isinstance(result.get("trace"), dict) else None
    )
    trace_fallback = trace_result
    if trace_fallback is None and isinstance(trace, dict):
        trace_fallback = dict(trace)

    (
        image_attachment_count,
        image_routing_path,
        image_routing_absence_reason,
    ) = _normalize_completion_image_routing_truth(
        task=task,
        provider=provider,
        model=model,
        settings=settings,
        messages_for_llm=messages_for_llm,
        routing_meta=routing_meta,
        trace=trace_fallback,
        payload_summary=payload_summary,
        result=result,
    )
    payload_summary["image_attachment_count"] = image_attachment_count
    payload_summary["image_routing_path"] = image_routing_path
    payload_summary[
        "image_routing_absence_reason"
    ] = image_routing_absence_reason
    result["image_attachment_count"] = image_attachment_count
    result["image_routing_path"] = image_routing_path
    result["image_routing_absence_reason"] = image_routing_absence_reason
    if isinstance(trace_result, dict):
        trace_result["image_attachment_count"] = image_attachment_count
        trace_result["image_routing_path"] = image_routing_path
        trace_result[
            "image_routing_absence_reason"
        ] = image_routing_absence_reason
        result["trace"] = trace_result
    elif isinstance(trace_fallback, dict):
        trace_fallback["image_attachment_count"] = image_attachment_count
        trace_fallback["image_routing_path"] = image_routing_path
        trace_fallback[
            "image_routing_absence_reason"
        ] = image_routing_absence_reason
        result["trace"] = trace_fallback

    candidate_trace = _build_candidate_trace(
        task,
        assistant_text=assistant_text,
        provider=provider,
        model=model,
    )
    if candidate_trace is not None:
        try:
            store_candidate_trace(candidate_trace)
        except Exception:
            logger.warning(
                "[chat-completion] candidate_trace_store_failed thread_id=%s request_id=%s",
                task.thread_id,
                _completion_request_id(task),
                exc_info=True,
            )
        request_id = str(candidate_trace.get("request_id") or "").strip()
        thread_id_raw = getattr(task, "thread_id", None)
        try:
            thread_id = int(thread_id_raw)
        except (TypeError, ValueError):
            thread_id = 0
        if request_id and thread_id > 0:
            task_payload = {
                "request_id": request_id,
                "thread_id": thread_id,
                "candidate_trace_id": request_id,
                "created_at": str(candidate_trace.get("created_at") or ""),
                "payload": dict(candidate_trace),
            }
            try:
                _enqueue_candidate_ingest(task_payload)
                logger.info(
                    "[chat-completion] candidate_trace_ingest_enqueued thread_id=%s request_id=%s candidate_trace_id=%s",
                    thread_id,
                    request_id,
                    request_id,
                )
            except Exception:
                logger.warning(
                    "[chat-completion] candidate_trace_ingest_enqueue_failed thread_id=%s request_id=%s",
                    thread_id,
                    request_id,
                    exc_info=True,
                )

    result: dict[str, Any] = {
        "assistant_text": assistant_text,
        "provider": provider,
        "model": model,
        "requested_provider": requested_provider,
        "requested_model": requested_model,
        "attempted_provider": attempted_provider,
        "attempted_model": attempted_model,
        "resolved_provider": resolved_provider,
        "resolved_model": resolved_model,
        "final_provider": final_provider,
        "final_model": final_model,
        "selection_source": selection_source,
        "fallback_reason": fallback_reason,
        "requested_provider": getattr(task, "requested_provider", None),
        "requested_model": getattr(task, "requested_model", None),
        "final_provider": provider,
        "final_model": model,
        "bundle": bundle,
        "trace": trace,
        "thread_id": task.thread_id,
        "payload_summary": payload_summary,
        "retrieval_provenance": retrieval_provenance,
        "retrieval_suppression": payload_summary.get("retrieval_suppression"),
        "model_selection": model_selection,
        "messageId": payload_summary.get("message_id"),
        "requestId": request_id,
        "toolTurnId": payload_summary.get("tool_turn_id"),
        "toolTurnState": payload_summary.get("tool_turn_state"),
        "loopStopReason": payload_summary.get("loop_stop_reason"),
        "commandRunId": payload_summary.get("command_run_id"),
        "tool_loop": dict(payload_summary.get("tool_loop") or {}),
    }
    if isinstance(trace, dict):
        result["latest_turn_message_id"] = trace.get("latest_turn_message_id")
        result["retrieval_query"] = trace.get("retrieval_query")
        result["retrieval_target"] = trace.get("retrieval_target")
        result["retrieval_query_matches_latest_turn"] = trace.get(
            "retrieval_query_matches_latest_turn"
        )
        if trace.get("retrieval_posture") is not None:
            result["retrieval_posture"] = trace.get("retrieval_posture")
        result["retrieval_policy"] = trace.get("retrieval_policy")
        result["retrieval_suppression"] = trace.get("retrieval_suppression")
        result["retrieval_executed"] = trace.get("retrieval_executed")
        result["retrieval_absence_reason"] = trace.get(
            "retrieval_absence_reason"
        )
        result["image_routing_path"] = trace.get("image_routing_path")
        result["image_routing_absence_reason"] = trace.get(
            "image_routing_absence_reason"
        )
    if isinstance(payload_summary, dict):
        result["model_selection"] = payload_summary.get("model_selection")
    result["payload_summary"] = payload_summary

    # Final assembly boundary: re-normalize image-routing truth after all
    # result and payload-summary merges have settled, so persistence and task
    # events cannot retain stale "image_routing_not_evaluated" values for
    # known image turns.
    final_trace = result.get("trace")
    if not isinstance(final_trace, dict) and isinstance(trace, dict):
        final_trace = dict(trace)
    (
        image_attachment_count,
        image_routing_path,
        image_routing_absence_reason,
    ) = _normalize_completion_image_routing_truth(
        task=task,
        provider=provider,
        model=model,
        settings=settings,
        messages_for_llm=messages_for_llm,
        routing_meta=routing_meta,
        trace=final_trace,
        payload_summary=payload_summary,
        result=result,
    )
    payload_summary["image_attachment_count"] = image_attachment_count
    payload_summary["image_routing_path"] = image_routing_path
    payload_summary[
        "image_routing_absence_reason"
    ] = image_routing_absence_reason
    result["image_attachment_count"] = image_attachment_count
    result["image_routing_path"] = image_routing_path
    result["image_routing_absence_reason"] = image_routing_absence_reason
    if isinstance(final_trace, dict):
        final_trace["image_attachment_count"] = image_attachment_count
        final_trace["image_routing_path"] = image_routing_path
        final_trace[
            "image_routing_absence_reason"
        ] = image_routing_absence_reason
        result["trace"] = final_trace

    if not persist_assistant_message:
        return result

    message_id = dependencies.chatlog_db.create_message(
        task.thread_id,
        "assistant",
        assistant_text,
    )
    result["message_id"] = message_id

    try:
        dependencies.chatlog_db.write_audit_log(
            "create",
            "chat_message",
            str(message_id),
            user_id="bot",
        )
    except Exception:
        pass

    try:
        event_bus.emit_event(
            "message.created",
            {
                "thread_id": task.thread_id,
                "message_id": message_id,
                "role": "assistant",
            },
        )
    except Exception:
        logger.debug("[chat-completion] emit message.created failed")

    _embed_message(task.thread_id, "assistant", assistant_text, message_id)
    return result
