"""Shared chat completion assembly/execution service.

This module centralizes completion orchestration so API routes/workers do not
fork context assembly, prompt construction, provider routing, or persistence.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Callable, Dict, Optional
from urllib.parse import unquote

from fastapi import HTTPException

from guardian.cognition.prompts import (
    build_context_system_message as _compat_build_context_system_message,
)
from guardian.cognition.prompts import build_context_system_message_with_meta
from guardian.command_bus.contracts import (
    CommandBusInvokeResult,
    InvokeArguments,
    InvokeRequest,
)
from guardian.command_bus.invoke import execute_invoke
from guardian.command_bus.store import CommandBusStore
from guardian.context.broker import ContextBroker
from guardian.context.retrieval_router_policy import (
    RETRIEVAL_OVERRIDE_CONVERSATION,
    RETRIEVAL_OVERRIDE_NONE,
    RETRIEVAL_OVERRIDE_PERSONAL_KNOWLEDGE,
    RETRIEVAL_OVERRIDE_PROJECT,
    SOURCE_MODE_CONVERSATION,
    SOURCE_MODE_OBSIDIAN_ONLY,
    SOURCE_MODE_PERSONAL_KNOWLEDGE,
    SOURCE_MODE_PROJECT,
    normalize_retrieval_override_mode,
    normalize_source_mode,
    resolve_retrieval_plan,
)
from guardian.core import dependencies, event_bus
from guardian.core.ai_router import (
    build_openai_vision_content,
    chat_with_ai,
    normalize_completion_output,
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
    model_supports_capability,
    normalize_model_id,
    normalize_provider,
    resolve_provider_for_model,
)
from guardian.obsidian.indexer import OBSIDIAN_NAMESPACE
from guardian.protocol_tokens import LoopStopReason, ToolTurnState
from guardian.queue.redis_queue import (
    CANDIDATE_INGEST_QUEUE,
    get_redis_connection,
)
from guardian.tasks.types import ChatCompletionTask

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


async def _build_messages_for_llm_compat(
    task: ChatCompletionTask,
    *,
    user_id: str | None = None,
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
    accepts_user_id = False
    if signature is not None:
        accepts_user_id = any(
            parameter.kind == inspect.Parameter.VAR_KEYWORD or name == "user_id"
            for name, parameter in signature.parameters.items()
        )
    if accepts_user_id:
        return await builder(task, user_id=user_id)
    return await builder(task)


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
    normalized_source_mode = _normalize_source_mode(source_mode)
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
    tool_turn_state: ToolTurnState = ToolTurnState.NOT_STARTED,
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
        tool_turn_state=ToolTurnState.RUNNING,
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
            tool_loop["toolTurnState"] = ToolTurnState.BLOCKED.value
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
            ToolTurnState.BLOCKED.value,
        }:
            tool_loop["toolTurnState"] = ToolTurnState.BLOCKED.value
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
            _thread_config_value(
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
    request_user_id: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    _ = request_user_id
    try:
        return await broker.assemble(
            thread_id,
            query=query,
            depth_mode=depth_mode,
            user_id=user_id,
            project_id=project_id,
            source_mode=source_mode,
            retrieval_override=retrieval_override,
        )
    except TypeError as exc:
        error_text = str(exc)
        retrieval_override_error = "retrieval_override" in error_text
        source_mode_error = "source_mode" in error_text
        project_id_error = "project_id" in error_text
        if not (
            retrieval_override_error or source_mode_error or project_id_error
        ):
            raise
        if retrieval_override_error and not (
            source_mode_error or project_id_error
        ):
            return await broker.assemble(
                thread_id,
                query=query,
                depth_mode=depth_mode,
                user_id=user_id,
                project_id=project_id,
                source_mode=source_mode,
            )
        return await broker.assemble(
            thread_id,
            query=query,
            depth_mode=depth_mode,
            user_id=user_id,
        )


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

    supports_vision = model_supports_capability(
        provider, model, "vision", settings
    )
    last_user_index = _find_last_message_index(messages, "user")
    if last_user_index < 0:
        return messages, routing_meta

    updated = [
        dict(message) if isinstance(message, dict) else message
        for message in messages
    ]

    if supports_vision:
        image_urls = [
            str(item.get("src") or "").strip() for item in image_attachments
        ]
        image_urls = [url for url in image_urls if url]
        if not image_urls:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Image attachments are missing source URLs; "
                    "unable to route to a vision-capable model."
                ),
            )
        text = ""
        if isinstance(latest_user_meta, dict):
            text = str(latest_user_meta.get("text") or "")
        updated[last_user_index] = {
            "role": "user",
            "content": build_openai_vision_content(text, image_urls),
        }
        routing_meta["image_routing_path"] = "vlm"
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


def build_sanitized_payload_summary(
    messages: list[dict[str, str]] | None,
    bundle: dict[str, Any] | None,
    *,
    provider: str | None,
    model: str | None,
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
    if isinstance(prompt_meta, dict):
        retrieval_meta = prompt_meta.get("context") or {}
        docs_meta = prompt_meta.get("docs") or {}

    semantic_injected = bool(
        (retrieval_meta.get("semantic") or {}).get("injected")
    )
    memory_injected = bool((retrieval_meta.get("memory") or {}).get("injected"))
    graph_injected = bool((retrieval_meta.get("graph") or {}).get("injected"))
    federated_injected = bool(
        (retrieval_meta.get("federated") or {}).get("injected")
    )
    linked_document_injected = bool(docs_meta.get("injected"))

    obsidian_count = (
        len((bundle or {}).get("obsidian") or [])
        if isinstance(bundle, dict)
        else 0
    )
    # Obsidian entries are injected via the semantic context block.
    obsidian_injected = bool(obsidian_count and semantic_injected)

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
        "has_user_system_override": bool(
            (bundle or {}).get("user_system_override")
            if isinstance(bundle, dict)
            else False
        ),
        "resolved_provider": (provider or "").strip() or None,
        "resolved_model": (model or "").strip() or None,
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
        "obsidian_injected": obsidian_injected,
    }

    summary["retrieval_injected"] = any(
        summary[key]
        for key in (
            "semantic_injected",
            "memory_injected",
            "graph_injected",
            "federated_injected",
            "linked_document_injected",
            "obsidian_injected",
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
    obsidian_semantic_count = _count_items_with_namespace(
        semantic_hits,
        OBSIDIAN_NAMESPACE,
    )
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

    if obsidian_semantic_count > 0:
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
        requested_source_mode=_source_mode_from_origin(
            getattr(task, "origin", None)
        ),
        settings=settings,
    )
    provider = thread_execution.provider
    routing_debug_metadata = _task_routing_debug_metadata(task)
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
        content = render_content_for_inference(msg.get("content"))
        if content and content.strip() and content.strip().lower() != "null":
            context.append({"role": role, "content": content})

    if not context:
        raise ValueError("thread_has_no_usable_context")

    depth = str(task.depth_mode or "normal").strip().lower()
    task_user_id = str(user_id or getattr(task, "user_id", "") or "").strip()
    user_for_context = (thread_info or {}).get("user_id", "default")
    context_user_id = task_user_id or user_for_context
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
    try:
        broker = ContextBroker(
            dependencies.chatlog_db,
            dependencies._vector_store,
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
    except Exception as exc:
        logger.warning(
            "[chat-completion] context assemble failed depth=%s err=%s",
            depth,
            exc,
        )
        bundle = {}
    else:
        trace_candidate = trace

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

    try:
        retrieval_plan = resolve_retrieval_plan(
            retrieval_query,
            depth,
            active_thread_id=thread_id,
            active_project_id=project_id_for_prompt,
            active_persona=_active_persona_context_from_prompt_meta(
                prompt_meta
            ),
        )
        if isinstance(trace, dict):
            trace = dict(trace)
            trace[RETRIEVAL_PLAN_TRACE_KEY] = _serialize_retrieval_plan_trace(
                plan=retrieval_plan,
                user_depth=depth,
            )
    except Exception as exc:
        logger.warning(
            "[chat-completion] retrieval plan resolution failed depth=%s err=%s",
            depth,
            exc,
        )

    if isinstance(trace_candidate, dict):
        _persist_thread_trace_candidate(task, trace)

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


def run_chat_completion_task(
    task: ChatCompletionTask,
    *,
    user_id: str | None = None,
    token_callback: Callable[[str], None] | None = None,
    chunk_callback: Callable[[str], None] | None = None,
    cancel_check: Callable[[], bool] | None = None,
    persist_assistant_message: bool = True,
) -> dict[str, Any]:
    """Execute one completion with shared context assembly/provider routing."""
    build_result: tuple[
        list[dict[str, str]],
        str,
        str,
        dict[str, Any],
        dict[str, Any] | None,
    ] = asyncio.run(_build_messages_for_llm_compat(task, user_id=user_id))
    messages_for_llm, provider, model, bundle, trace = build_result

    settings = get_settings()
    requested_source_mode = (
        str(getattr(task, "requested_source_mode", "") or "").strip() or None
    )
    messages_for_llm, routing_meta = _apply_image_attachment_routing(
        messages_for_llm,
        bundle=bundle,
        provider=provider,
        model=model,
        settings=settings,
    )
    routing_debug_metadata = _task_routing_debug_metadata(task)

    payload_summary = build_sanitized_payload_summary(
        messages_for_llm,
        bundle,
        provider=provider,
        model=model,
        requested_source_mode=requested_source_mode,
    )
    payload_summary.update(
        {
            "image_routing_path": routing_meta.get("image_routing_path"),
            "image_attachment_count": routing_meta.get(
                "image_attachment_count", 0
            ),
            "derived_image_context_injected": routing_meta.get(
                "derived_image_context_injected", False
            ),
        }
    )
    payload_summary.update(routing_debug_metadata)
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
    retrieval_provenance = _build_retrieval_provenance(
        requested_source_mode=requested_source_mode,
        normalized_source_mode=trace_source_mode,
        bundle=bundle if isinstance(bundle, dict) else None,
    )
    payload_summary["retrieval_provenance"] = retrieval_provenance
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

    request_id = _completion_request_id(task)
    tool_loop = _tool_loop_observability(task)
    assistant_raw_output: Any = ""
    assistant_text = ""
    streamed_any = False
    if provider == "local":
        token_stream = stream_local(
            messages_for_llm,
            model,
            reasoning_mode=getattr(task, "reasoning_mode", None),
            temperature=getattr(task, "temperature", None),
        )
        try:
            for token in token_stream:
                if cancel_check and cancel_check():
                    raise ChatTaskCancelled("task_cancelled")
                if token:
                    streamed_any = True
                    assistant_text += token
                    if token_callback:
                        token_callback(token)
                    if chunk_callback:
                        chunk_callback(token)
        finally:
            token_stream.close()

        # Defensive fallback: some local providers may return a full completion
        # without producing incremental stream chunks (or our stream parser yields none).
        # We still want a completion persisted, but we must avoid emitting a duplicate
        # message to the UI when streaming already happened.
        if not assistant_text.strip():
            assistant_raw_output = chat_with_ai(
                messages_for_llm,
                model=model,
                provider=provider,
                reasoning_mode=getattr(task, "reasoning_mode", None),
                temperature=getattr(task, "temperature", None),
                prompt_meta=(
                    dict(bundle.get("_prompt_meta") or {})
                    if isinstance(bundle, dict)
                    else None
                ),
            )
            normalized = normalize_completion_output(assistant_raw_output)
            assistant_text = str(normalized.get("assistant_text") or "")
        else:
            assistant_raw_output = assistant_text
    else:
        if cancel_check and cancel_check():
            raise ChatTaskCancelled("task_cancelled")
        assistant_raw_output = chat_with_ai(
            messages_for_llm,
            model=model,
            provider=provider,
            reasoning_mode=getattr(task, "reasoning_mode", None),
            temperature=getattr(task, "temperature", None),
            prompt_meta=(
                dict(bundle.get("_prompt_meta") or {})
                if isinstance(bundle, dict)
                else None
            ),
        )
        assistant_text = str(assistant_raw_output or "")
        if token_callback:
            token_callback(assistant_text)

    normalized_output = normalize_completion_output(assistant_raw_output)
    if normalized_output["kind"] == "tool_decision":
        tool_decision = dict(normalized_output["tool_decision"] or {})
        tool_turn_id = str(uuid.uuid4())
        assistant_text, tool_loop, command_result = _execute_bounded_tool_turn(
            task=task,
            tool_decision=tool_decision,
            request_id=request_id,
            tool_turn_id=tool_turn_id,
            messages_for_llm=messages_for_llm,
            provider=provider,
            model=model,
            reasoning_mode=getattr(task, "reasoning_mode", None),
            temperature=getattr(task, "temperature", None),
            token_callback=token_callback,
            chunk_callback=chunk_callback,
        )
        _attach_tool_loop_metadata(
            payload_summary,
            tool_loop=tool_loop,
            request_id=request_id,
        )
        normalized_output = {
            "kind": "assistant",
            "assistant_text": assistant_text,
        }
    elif normalized_output["kind"] == "malformed_tool_decision":
        tool_loop = _tool_loop_observability(
            task,
            tool_turn_state=ToolTurnState.FAILED,
            loop_stop_reason=LoopStopReason.TOOL_TURN_MALFORMED,
        )
        _attach_tool_loop_metadata(
            payload_summary,
            tool_loop=tool_loop,
            request_id=request_id,
        )
        assistant_text = (
            str(normalized_output.get("assistant_text") or "").strip()
            or "Tool decision was malformed."
        )
        if token_callback and assistant_text:
            token_callback(assistant_text)
        normalized_output = {
            "kind": "assistant",
            "assistant_text": assistant_text,
        }
    else:
        assistant_text = str(normalized_output.get("assistant_text") or "")
        _attach_tool_loop_metadata(
            payload_summary,
            tool_loop=tool_loop,
            request_id=request_id,
        )
        if token_callback and assistant_text and not streamed_any:
            token_callback(assistant_text)

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
        "bundle": bundle,
        "trace": trace,
        "thread_id": task.thread_id,
        "payload_summary": payload_summary,
        "retrieval_provenance": retrieval_provenance,
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
