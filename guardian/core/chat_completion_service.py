"""Shared chat completion assembly/execution service.

This module centralizes completion orchestration so API routes/workers do not
fork context assembly, prompt construction, provider routing, or persistence.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime
from typing import Any, Callable, Dict, Optional

from fastapi import HTTPException

from guardian.cognition.prompts import (
    build_context_system_message as _compat_build_context_system_message,
)
from guardian.cognition.prompts import build_context_system_message_with_meta
from guardian.context.broker import ContextBroker
from guardian.core import dependencies, event_bus
from guardian.core.ai_router import (
    build_openai_vision_content,
    chat_with_ai,
    stream_local,
)
from guardian.core.chat_attachments import (
    extract_attachments_and_text,
    render_content_for_inference,
)
from guardian.core.config import (
    LLMConfigError,
    get_settings,
    validate_llm_config,
)
from guardian.core.provider_registry import model_supports_capability
from guardian.tasks.types import ChatCompletionTask

logger = logging.getLogger(__name__)

try:  # pragma: no cover - prompts are optional in some deployments
    from guardian.cognition.system_prompt_builder import (
        build_guardian_system_prompt,
    )
except Exception:  # pragma: no cover - optional dependency
    build_guardian_system_prompt = None


class ChatTaskCancelled(RuntimeError):
    """Raised when a caller-provided cancellation check aborts completion."""


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


def _find_last_message_index(messages: list[dict[str, Any]], role: str) -> int:
    target_role = str(role or "").strip().lower()
    for index in range(len(messages) - 1, -1, -1):
        message = messages[index]
        if not isinstance(message, dict):
            continue
        if str(message.get("role") or "").strip().lower() == target_role:
            return index
    return -1


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


def _interpret_image_attachments(
    image_attachments: list[dict[str, Any]],
    *,
    settings: Any,
) -> list[dict[str, Any]] | None:
    vision_model = str(getattr(settings, "GROQ_VISION_MODEL", "") or "").strip()
    api_key = str(getattr(settings, "GROQ_API_KEY", "") or "").strip()
    if not vision_model or not api_key:
        return None

    prompt = (
        "Describe the image for downstream reasoning. "
        "If the image includes readable text, extract it."
    )
    interpretations: list[dict[str, Any]] = []
    for attachment in image_attachments:
        src = str(attachment.get("src") or "").strip()
        if not src:
            continue
        try:
            content = build_openai_vision_content(prompt, [src])
            summary = chat_with_ai(
                [{"role": "user", "content": content}],
                model=vision_model,
                provider="groq",
            )
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Image interpreter failed: {exc}",
            ) from exc
        interpretations.append(
            {
                "label": _format_image_label(attachment),
                "summary": str(summary or "").strip(),
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
        "linked_document_count": linked_document_count,
        "has_user_system_override": bool(
            (bundle or {}).get("user_system_override")
            if isinstance(bundle, dict)
            else False
        ),
        "resolved_provider": (provider or "").strip() or None,
        "resolved_model": (model or "").strip() or None,
        "semantic_injected": bool(
            (retrieval_meta.get("semantic") or {}).get("injected")
        ),
        "memory_injected": bool(
            (retrieval_meta.get("memory") or {}).get("injected")
        ),
        "graph_injected": bool(
            (retrieval_meta.get("graph") or {}).get("injected")
        ),
        "federated_injected": bool(
            (retrieval_meta.get("federated") or {}).get("injected")
        ),
        "linked_document_injected": bool(docs_meta.get("injected")),
    }

    summary["retrieval_injected"] = any(
        summary[key]
        for key in (
            "semantic_injected",
            "memory_injected",
            "graph_injected",
            "federated_injected",
            "linked_document_injected",
        )
    )

    # For callers that later update to reflect a fallback provider/model.
    summary.setdefault("final_provider", summary["resolved_provider"])
    summary.setdefault("final_model", summary["resolved_model"])
    return summary


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

    sources = []
    for scope in ("thread", "project"):
        items = docs.get(scope)
        if isinstance(items, list):
            sources.extend(
                [(scope, item) for item in items if isinstance(item, dict)]
            )

    if not sources:
        return None, 0

    lines: list[str] = []
    for scope, item in sources:
        title = str(item.get("title") or item.get("id") or "document").strip()
        excerpt = str(item.get("excerpt") or "").strip()
        provenance = item.get("provenance")
        relation = ""
        if isinstance(provenance, dict):
            relation = str(provenance.get("relation") or "").strip().lower()
        relation_prefix = f"[{relation}] " if relation else ""
        scope_prefix = "[thread] " if scope == "thread" else "[project] "
        prefix = scope_prefix + relation_prefix
        if excerpt:
            lines.append(f"- {prefix}{title}: {excerpt}")
        else:
            lines.append(f"- {prefix}{title}")

    if not lines:
        return None, 0

    return (
        "Linked document excerpts are available for this conversation. "
        "Use them when they help answer the user's request.\n\n"
        "Documents:\n" + "\n".join(lines),
        len(sources),
    )


async def build_messages_for_llm(
    task: ChatCompletionTask,
) -> tuple[
    list[dict[str, str]],
    str,
    str,
    dict[str, Any],
    dict[str, Any] | None,
]:
    """Build contextual messages and provider/model selection for one task."""
    settings = get_settings()
    provider = (
        (task.provider or settings.LLM_PROVIDER or dependencies.CHAT_PROVIDER)
        .strip()
        .lower()
    )

    if validate_llm_config:
        try:
            validate_llm_config(settings, provider_override=provider)
        except LLMConfigError as exc:
            logger.warning(
                "[chat-completion] LLM config error provider=%s detail=%s",
                provider,
                exc,
            )

    user_system_override = task.system_override
    if isinstance(user_system_override, str):
        user_system_override = user_system_override.strip() or None
    else:
        user_system_override = None

    thread_id = task.thread_id
    thread_info = (
        dependencies.chatlog_db.get_chat_thread(thread_id)
        if hasattr(dependencies.chatlog_db, "get_chat_thread")
        else None
    )
    if not thread_info:
        raise ValueError("thread_not_found")

    limit = int(task.max_context or 50)
    items = dependencies.chatlog_db.list_messages(
        thread_id, limit=limit, offset=0
    )
    try:
        items = sorted(items, key=lambda m: m.get("id") or 0)
    except Exception:
        pass

    context: list[dict[str, str]] = []
    latest_user_meta: dict[str, Any] | None = None
    for msg in items:
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

    latest_message = ""
    for msg in reversed(items):
        if str(msg.get("role") or "").strip() == "user":
            lm = render_content_for_inference(msg.get("content"))
            if lm:
                latest_message = lm
                break

    depth = str(task.depth_mode or "normal").strip().lower()
    user_for_context = (thread_info or {}).get("user_id", "default")

    bundle: dict[str, Any] = {}
    trace: dict[str, Any] | None = None
    try:
        broker = ContextBroker(
            dependencies.chatlog_db,
            dependencies._vector_store,
            dependencies._memory_store,
            dependencies._sensors,
            settings=settings,
        )
        bundle, trace = await broker.assemble(
            thread_id,
            query=latest_message,
            depth_mode=depth,
            user_id=user_for_context,
        )
        if user_system_override:
            bundle.setdefault("user_system_override", user_system_override)
    except Exception as exc:
        logger.warning(
            "[chat-completion] context assemble failed depth=%s err=%s",
            depth,
            exc,
        )
        bundle = {}

    messages_for_llm: list[dict[str, str]] = []
    prompt_meta: dict[str, Any] = {}

    project_id_for_prompt: int | None = None
    if thread_info:
        try:
            raw_project_id = thread_info.get("project_id")
            if raw_project_id is not None:
                project_id_for_prompt = int(raw_project_id)
        except (TypeError, ValueError):
            project_id_for_prompt = None

    try:
        if build_guardian_system_prompt:
            system_content, prompt_meta = build_guardian_system_prompt(
                user_id=user_for_context,
                project_id=project_id_for_prompt,
                depth=depth,
                bundle=bundle,
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

    if isinstance(bundle, dict):
        try:
            existing_meta = bundle.get("_prompt_meta") or {}
            merged_meta = dict(existing_meta)
            merged_meta.update(prompt_meta or {})
            bundle["_prompt_meta"] = merged_meta
        except Exception:
            bundle["_prompt_meta"] = dict(prompt_meta or {})

    messages_for_llm.append({"role": "system", "content": system_content})

    doc_message, doc_count = _build_document_context_message(bundle)
    if doc_message:
        messages_for_llm.append({"role": "system", "content": doc_message})

    context_message, context_meta = build_context_system_message_with_meta(
        bundle
    )
    if context_message:
        messages_for_llm.append({"role": "system", "content": context_message})
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
    messages_for_llm.extend(context)

    model = task.model
    if not model and provider == "local":
        model = (
            settings.LOCAL_LLM_MODEL
            or settings.DEFAULT_LOCAL_MODEL
            or settings.LLM_MODEL
            or ""
        )
    if not model:
        model = dependencies.DEFAULT_MODEL or ""

    return messages_for_llm, provider, model, bundle, trace


def run_chat_completion_task(
    task: ChatCompletionTask,
    *,
    token_callback: Callable[[str], None] | None = None,
    cancel_check: Callable[[], bool] | None = None,
    persist_assistant_message: bool = True,
) -> dict[str, Any]:
    """Execute one completion with shared context assembly/provider routing."""
    messages_for_llm, provider, model, bundle, trace = asyncio.run(
        build_messages_for_llm(task)
    )

    settings = get_settings()
    messages_for_llm, routing_meta = _apply_image_attachment_routing(
        messages_for_llm,
        bundle=bundle,
        provider=provider,
        model=model,
        settings=settings,
    )

    payload_summary = build_sanitized_payload_summary(
        messages_for_llm,
        bundle,
        provider=provider,
        model=model,
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

    assistant_text = ""
    if provider == "local":
        streamed_any = False
        token_stream = stream_local(
            messages_for_llm,
            model,
            reasoning_mode=getattr(task, "reasoning_mode", None),
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
        finally:
            token_stream.close()

        # Defensive fallback: some local providers may return a full completion
        # without producing incremental stream chunks (or our stream parser yields none).
        # We still want a completion persisted, but we must avoid emitting a duplicate
        # message to the UI when streaming already happened.
        if not assistant_text.strip():
            assistant_text = str(
                chat_with_ai(
                    messages_for_llm,
                    model=model,
                    provider=provider,
                    reasoning_mode=getattr(task, "reasoning_mode", None),
                )
            )
            # Only emit via callback when nothing was streamed.
            if token_callback and (not streamed_any) and assistant_text:
                token_callback(assistant_text)
    else:
        if cancel_check and cancel_check():
            raise ChatTaskCancelled("task_cancelled")
        assistant_text = str(
            chat_with_ai(
                messages_for_llm,
                model=model,
                provider=provider,
                reasoning_mode=getattr(task, "reasoning_mode", None),
            )
        )
        if token_callback:
            token_callback(assistant_text)

    result: dict[str, Any] = {
        "assistant_text": assistant_text,
        "provider": provider,
        "model": model,
        "bundle": bundle,
        "trace": trace,
        "thread_id": task.thread_id,
        "payload_summary": payload_summary,
    }

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
