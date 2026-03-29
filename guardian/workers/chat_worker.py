"""Chat completion worker for async tasks.

This worker is intentionally thin: orchestration and routing live in
`guardian.core.chat_completion_service.run_chat_completion_task`.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress
from dataclasses import replace
from typing import Any

from fastapi import HTTPException
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError

from guardian.audio import tts_trigger
from guardian.cognition.system_profiles.resolver import (
    resolve_thread_system_profile,
)
from guardian.context.broker import ContextBroker
from guardian.core import chat_completion_service as _chat_completion_service
from guardian.core import dependencies, event_bus
from guardian.core.ai_router import chat_with_ai, stream_local
from guardian.core.chat_completion_service import ChatTaskCancelled
from guardian.core.config import (
    LLMConfigError,
    Settings,
    get_settings,
    validate_llm_config,
)
from guardian.core.db import GuardianDB
from guardian.core.llm_catalog import (
    first_enabled_provider,
    first_model_for_provider,
    resolve_provider_for_model,
)
from guardian.core.metrics import CHAT_TURN_METADATA_PERSIST_FAILURES_TOTAL
from guardian.core.provider_registry import (
    default_model_for_provider,
    normalize_provider,
    resolve_provider_capability,
    validate_provider_model_selection,
)
from guardian.core.provider_truth import build_provider_truth
from guardian.queue import task_events
from guardian.queue.redis_queue import (
    clear_cancelled,
    dequeue,
    get_redis_client,
    is_cancelled,
)
from guardian.queue.turn_lock import release_turn_lock
from guardian.tasks.types import ChatCompletionTask, task_from_dict
from guardian.voice.audio_assets import (
    compute_text_hash,
    find_cached_asset,
    save_message_audio_asset,
    upsert_message_audio_asset_status,
)
from guardian.voice.runtime import assistant_message_audio_autogenerate_enabled

logger = logging.getLogger(__name__)

build_guardian_system_prompt = (
    _chat_completion_service.build_guardian_system_prompt
)
_embed_message = _chat_completion_service._embed_message
_ORIGINAL_BUILD_MESSAGES_FOR_LLM = (
    _chat_completion_service.build_messages_for_llm
)
_ORIGINAL_BUILD_CONTEXT_SYSTEM_MESSAGE_WITH_META = (
    _chat_completion_service.build_context_system_message_with_meta
)


def build_context_system_message(bundle: dict[str, Any] | None) -> str | None:
    """Compatibility seam for legacy tests/hooks that patch this symbol."""
    message, _meta = _ORIGINAL_BUILD_CONTEXT_SYSTEM_MESSAGE_WITH_META(bundle)
    return message


def _build_context_system_message_with_meta_compat(
    bundle: dict[str, Any] | None,
) -> tuple[str | None, dict[str, Any]]:
    message, meta = _ORIGINAL_BUILD_CONTEXT_SYSTEM_MESSAGE_WITH_META(bundle)
    renderer = globals().get("build_context_system_message")
    if callable(renderer):
        try:
            compat_message = renderer(bundle)
        except Exception:
            compat_message = None
        if isinstance(compat_message, str):
            cleaned = compat_message.strip()
            if cleaned:
                message = cleaned
    return message, meta


def _resolve_media_items(*_args: Any, **_kwargs: Any) -> list[Any]:
    return []


def _build_media_system_message(_items: list[Any]) -> str | None:
    return None


def _maybe_add_vision_summary(
    _items: list[Any], _provider: str
) -> dict[str, Any] | None:
    return None


QUEUE_NAME = os.getenv("CHAT_QUEUE_NAME", "codexify:queue:chat")
CONCURRENCY = int(os.getenv("CHAT_WORKER_CONCURRENCY", "2"))
WORKER_HEARTBEAT_KEY = os.getenv(
    "CHAT_WORKER_HEARTBEAT_KEY", "codexify:worker:chat:heartbeat"
)
WORKER_HEARTBEAT_TTL_SECONDS = int(
    os.getenv("CHAT_WORKER_HEARTBEAT_TTL_SECONDS", "45")
)

_MEDIA_DB: GuardianDB | None = None
_MEDIA_MARKER_RE = re.compile(
    r"<!--\s*cfy-media:(image|document):([a-fA-F0-9-]+)\s*-->"
)
_TURN_ID_ORIGIN_RE = re.compile(
    r"(?:^|\|)turn_id=(?P<turn_id>[a-f0-9-]{36})(?:\||$)",
    flags=re.IGNORECASE,
)
_TURN_COMPLETION_ANCHOR_PREFIX = "codexify:chat:turn-anchor"
_TURN_COMPLETION_ANCHOR_TTL_SECONDS = int(
    os.getenv("CHAT_TURN_COMPLETION_ANCHOR_TTL_SECONDS", "86400")
)
_MIRRORED_LIVE_EVENT_TYPES = {
    "task.running",
    "task.completed",
    "task.failed",
    "task.cancelled",
}
_ASSISTANT_AUDIO_EXECUTOR = ThreadPoolExecutor(
    max_workers=max(
        1,
        int(os.getenv("CHAT_WORKER_AUDIO_AUTOGENERATE_CONCURRENCY", "1")),
    )
)


def _coerce_message_id(raw: Any) -> int | None:
    try:
        value = int(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _extract_turn_id(task: ChatCompletionTask) -> str:
    explicit = str(getattr(task, "turn_id", "") or "").strip()
    if explicit:
        return explicit
    origin = str(getattr(task, "origin", "") or "")
    match = _TURN_ID_ORIGIN_RE.search(origin)
    return match.group("turn_id").strip().lower() if match else ""


def _persist_turn_id_metadata(
    *, thread_id: int, message_id: int, turn_id: str
) -> bool:
    """Persist turn correlation key in chat_messages.extra_meta."""
    if not turn_id:
        return True
    chatlog_db = getattr(dependencies, "chatlog_db", None)
    if chatlog_db is None:
        return False

    connect = getattr(chatlog_db, "_connect", None)
    if not callable(connect):
        logger.debug(
            "[chat-worker] chatlog_db has no _connect; skipping turn metadata update"
        )
        return False

    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            """
            UPDATE chat_messages
            SET extra_meta = COALESCE(extra_meta, '{}'::jsonb) || %s::jsonb
            WHERE thread_id = %s
              AND id = %s
            RETURNING id
            """,
            (json.dumps({"turn_id": turn_id}), thread_id, message_id),
        )
        row = cur.fetchone()
        return bool(row)


def _persist_message_extra_meta(
    *, thread_id: int, message_id: int, payload: dict[str, Any]
) -> bool:
    chatlog_db = getattr(dependencies, "chatlog_db", None)
    if chatlog_db is None:
        return False

    connect = getattr(chatlog_db, "_connect", None)
    if not callable(connect):
        return False

    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            """
            UPDATE chat_messages
            SET extra_meta = COALESCE(extra_meta, '{}'::jsonb) || %s::jsonb
            WHERE thread_id = %s
              AND id = %s
            RETURNING id
            """,
            (json.dumps(payload or {}), thread_id, message_id),
        )
        row = cur.fetchone()
        return bool(row)


def _turn_completion_anchor_key(thread_id: int, turn_id: str) -> str:
    return ":".join((_TURN_COMPLETION_ANCHOR_PREFIX, str(thread_id), turn_id))


def _cache_turn_completion_anchor(
    *, thread_id: int, message_id: int, turn_id: str
) -> bool:
    if not turn_id:
        return True
    try:
        client = get_redis_client()
        client.setex(
            _turn_completion_anchor_key(thread_id, turn_id),
            max(60, _TURN_COMPLETION_ANCHOR_TTL_SECONDS),
            str(message_id),
        )
        return True
    except Exception:
        logger.debug(
            "[chat-worker] failed to cache turn completion anchor thread_id=%s turn_id=%s message_id=%s",
            thread_id,
            turn_id,
            message_id,
            exc_info=True,
        )
        return False


def _cached_turn_completion_anchor(
    *, thread_id: int, turn_id: str
) -> int | None:
    if not turn_id:
        return None
    try:
        client = get_redis_client()
        cached = client.get(_turn_completion_anchor_key(thread_id, turn_id))
    except Exception:
        logger.debug(
            "[chat-worker] failed to read cached turn completion anchor thread_id=%s turn_id=%s",
            thread_id,
            turn_id,
            exc_info=True,
        )
        return None
    return _coerce_message_id(cached)


def _record_turn_metadata_persist_failure(reason: str) -> None:
    try:
        CHAT_TURN_METADATA_PERSIST_FAILURES_TOTAL.labels(
            reason=str(reason or "unknown")
        ).inc()
    except Exception:
        logger.debug(
            "[chat-worker] failed to record metadata persist metric reason=%s",
            reason,
            exc_info=True,
        )


def _coerce_row_message_id(row: Any) -> int | None:
    if row is None:
        return None
    if isinstance(row, dict):
        return _coerce_message_id(row.get("id"))
    if isinstance(row, (tuple, list)):
        return _coerce_message_id(row[0] if row else None)
    try:
        return _coerce_message_id(row["id"])  # type: ignore[index]
    except Exception:
        return _coerce_message_id(getattr(row, "id", None))


def _find_assistant_message_id_by_turn_id(
    *, thread_id: int, turn_id: str
) -> int | None:
    if not turn_id:
        return None
    try:
        client = get_redis_client()
        using_fake_cache = hasattr(client, "_values") or (
            client.__class__.__name__ == "_FakeRedis"
        )
    except Exception:
        client = None
        using_fake_cache = False

    if using_fake_cache:
        return _cached_turn_completion_anchor(
            thread_id=thread_id,
            turn_id=turn_id,
        )

    chatlog_db = getattr(dependencies, "chatlog_db", None)
    if chatlog_db is None:
        return _cached_turn_completion_anchor(
            thread_id=thread_id,
            turn_id=turn_id,
        )
    connect = getattr(chatlog_db, "_connect", None)
    if not callable(connect):
        return _cached_turn_completion_anchor(
            thread_id=thread_id,
            turn_id=turn_id,
        )
    try:
        with connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT id
                FROM chat_messages
                WHERE thread_id = %s
                  AND role = 'assistant'
                  AND COALESCE(extra_meta, '{}'::jsonb)->>'turn_id' = %s
                ORDER BY id ASC
                LIMIT 1
                """,
                (thread_id, turn_id),
            )
            message_id = _coerce_row_message_id(cur.fetchone())
            if message_id is not None:
                return message_id
    except Exception:
        logger.debug(
            "[chat-worker] failed turn_id lookup thread_id=%s turn_id=%s",
            thread_id,
            turn_id,
            exc_info=True,
        )
    return _cached_turn_completion_anchor(thread_id=thread_id, turn_id=turn_id)


def _find_assistant_message_for_turn(
    *, thread_id: int, turn_id: str
) -> int | None:
    """Return an existing assistant message id for the turn when present."""
    return _find_assistant_message_id_by_turn_id(
        thread_id=thread_id,
        turn_id=turn_id,
    )


def _publish_worker_heartbeat(status: str = "idle") -> None:
    payload = {
        "worker": "chat",
        "status": status,
        "queue": QUEUE_NAME,
        "ts": int(time.time()),
    }
    try:
        client = get_redis_client()
        client.setex(
            WORKER_HEARTBEAT_KEY,
            max(5, WORKER_HEARTBEAT_TTL_SECONDS),
            json.dumps(payload),
        )
    except Exception as exc:
        logger.debug("[chat-worker] heartbeat update failed: %s", exc)


def _safe_emit_live_event(event_type: str, payload: dict[str, Any]) -> None:
    try:
        event_bus.emit_event(event_type, payload)
    except Exception as exc:
        logger.debug(
            "[chat-worker] failed to mirror live event type=%s err=%s",
            event_type,
            exc,
        )


def _safe_publish(task_id: str, event_type: str, data: dict) -> dict[str, Any]:
    """Best-effort event publishing with explicit visibility signaling.

    Never raise from the worker hot-path.
    """
    payload: dict
    try:
        payload = dict(data) if isinstance(data, dict) else {"data": data}
    except Exception:
        payload = {"data": str(data)}

    try:
        publish_result = task_events.publish_with_visibility(
            task_id, event_type, payload
        )
    except Exception as exc:
        visibility_scope = task_events.classify_event_visibility(event_type)
        publish_result = {
            "ok": False,
            "task_id": task_id,
            "event_type": event_type,
            "visibility_scope": visibility_scope,
            "terminal_visibility": visibility_scope == "terminal",
            "execution_continued": True,
            "event_id": None,
            "failure_class": exc.__class__.__name__,
            "error": str(exc),
        }

    if not publish_result.get("ok"):
        log_level = (
            logging.ERROR
            if publish_result.get("terminal_visibility")
            else logging.WARNING
        )
        logger.log(
            log_level,
            (
                "[chat-worker] task_event_visibility_degraded "
                "task_id=%s event_type=%s visibility_scope=%s "
                "failure_class=%s execution_continued=%s err=%s"
            ),
            task_id,
            event_type,
            publish_result.get("visibility_scope"),
            publish_result.get("failure_class"),
            publish_result.get("execution_continued"),
            publish_result.get("error"),
        )

    if event_type in _MIRRORED_LIVE_EVENT_TYPES:
        mirror_payload = dict(payload)
        mirror_payload.setdefault("task_id", task_id)
        _safe_emit_live_event(event_type, mirror_payload)

    return publish_result


def _describe_task_error(exc: Exception) -> str:
    if isinstance(exc, HTTPException):
        detail = getattr(exc, "detail", "")
        if isinstance(detail, (dict, list)):
            try:
                return json.dumps(detail)
            except Exception:
                return str(detail)
        if detail:
            return str(detail)
    return str(exc) or exc.__class__.__name__


def _task_error_metadata(exc: Exception) -> dict[str, Any]:
    if isinstance(exc, HTTPException):
        detail = getattr(exc, "detail", None)
        if isinstance(detail, dict):
            return dict(detail)
    metadata = getattr(exc, "metadata", None)
    if isinstance(metadata, dict):
        return dict(metadata)
    return {}


def _classify_runtime_status(detail: str) -> str | None:
    lowered = str(detail or "").strip().lower()
    if not lowered:
        return None
    if "timed out" in lowered or "read timeout" in lowered:
        return "timeout"
    if "connection refused" in lowered:
        return "connection_refused"
    if "failed to resolve" in lowered or "name resolution" in lowered:
        return "dns_error"
    return None


def _completion_truth(
    *,
    accepted: bool,
    attempted: bool,
    fallback_attempted: bool,
    executed: bool,
    completed: bool,
) -> dict[str, bool]:
    return {
        "accepted": bool(accepted),
        "attempted": bool(attempted),
        "fallback_attempted": bool(fallback_attempted),
        "executed": bool(executed),
        "completed": bool(completed),
    }


def _should_attempt_provider_fallback(exc: Exception) -> bool:
    if isinstance(exc, ChatTaskCancelled):
        return False
    if isinstance(exc, LLMConfigError):
        return True
    if isinstance(exc, HTTPException):
        detail = getattr(exc, "detail", None)
        if isinstance(detail, dict):
            failure_kind = str(detail.get("failure_kind") or "").strip().lower()
            if failure_kind in {
                "provider_timeout",
                "transport_error",
                "provider_unavailable",
                "provider_http_error",
                "http_error",
                "request_error",
                "auth_config_error",
            }:
                return True
        return exc.status_code >= 500
    return True


def _fallback_provider_candidates(
    *,
    attempted_provider: str | None,
    settings: Settings,
) -> list[tuple[str, str]]:
    current = normalize_provider(attempted_provider)
    requested_order = list(getattr(settings, "LLM_FALLBACK_ORDER", []) or [])
    normalized_order: list[str] = []
    seen: set[str] = set()
    preferred_candidates = [current]
    if current != "local":
        preferred_candidates.append("local")
    preferred_candidates.extend(requested_order)
    for raw in preferred_candidates:
        provider = normalize_provider(raw)
        if not provider or provider in seen:
            continue
        seen.add(provider)
        normalized_order.append(provider)
    candidates: list[tuple[str, str]] = []
    for provider in normalized_order:
        if provider == current:
            continue
        model = _normalize_model_override(
            first_model_for_provider(provider, settings=settings)
            or default_model_for_provider(provider, settings)
        )
        if not model:
            continue
        if provider == "local":
            candidates.append((provider, model))
            continue
        valid, _reason = validate_provider_model_selection(
            provider_id=provider,
            model_id=model,
            settings=settings,
        )
        if not valid:
            continue
        candidates.append((provider, model))
    return candidates


def _assistant_message_audio_autogenerate_effective_enabled() -> bool:
    raw = os.getenv("CODEXIFY_ASSISTANT_MESSAGE_AUDIO_AUTOGENERATE")
    if raw is None:
        return True
    return assistant_message_audio_autogenerate_enabled()


def _assistant_message_audio_voice() -> str:
    value = (os.getenv("CODEXIFY_DEFAULT_VOICE") or "assistant").strip()
    return value or "assistant"


def _assistant_message_audio_provider_key() -> tuple[str, str | None]:
    target = tts_trigger.get_selected_tts_plugin_target()
    plugin_id = str(target.get("plugin_id") or "").strip()
    base_url = str(target.get("base_url") or "").strip() or None
    return plugin_id or "tts_plugin", base_url


def _assistant_message_audio_variants(
    *,
    thread_id: int,
    message_id: int,
    task_id: str,
    turn_id: str,
    status: str,
    plugin_id: str,
    plugin_base_url: str | None,
    generation_provider: str | None = None,
    error: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "status": status,
        "source": "assistant_message_autogenerate",
        "thread_id": thread_id,
        "message_id": message_id,
        "message_role": "assistant",
        "task_id": task_id,
        "turn_id": turn_id or None,
        "plugin_id": plugin_id,
        "plugin_base_url": plugin_base_url,
    }
    if generation_provider:
        payload["generation_provider"] = generation_provider
    if error:
        payload["error"] = {
            str(key): value
            for key, value in error.items()
            if value not in (None, "", [], {})
        }
    return payload


def _generate_assistant_message_audio_artifact(
    *,
    thread_id: int,
    message_id: int,
    assistant_text: str,
    task_id: str,
    turn_id: str,
    provider_key: str,
    voice: str,
    plugin_base_url: str | None,
) -> None:
    request_id = f"assistant-message-{message_id}"
    result = tts_trigger.generate_tts_artifact_with_result(
        assistant_text,
        metadata={
            "request_id": request_id,
            "thread_id": str(thread_id),
            "message_id": str(message_id),
            "task_id": task_id,
            "turn_id": turn_id,
            "source": "assistant_message_autogenerate",
        },
    )

    if result.ok and result.audio_bytes:
        asset = save_message_audio_asset(
            message_id=message_id,
            text=assistant_text,
            provider=provider_key,
            voice=voice,
            audio_bytes=result.audio_bytes,
            audio_format=result.audio_format or "wav",
            delivery_variants_json=_assistant_message_audio_variants(
                thread_id=thread_id,
                message_id=message_id,
                task_id=task_id,
                turn_id=turn_id,
                status="ready",
                plugin_id=result.plugin_id or provider_key,
                plugin_base_url=result.base_url or plugin_base_url,
                generation_provider=result.provider,
            ),
        )
        audio_url = str(
            asset.get("stream_url") or asset.get("src_url") or ""
        ).strip()
        logger.info(
            "[chat-worker] assistant_message_audio_ready thread_id=%s message_id=%s task_id=%s plugin_id=%s provider=%s asset_id=%s final_status=%s audio_url_present=%s bytes=%s",
            thread_id,
            message_id,
            task_id,
            result.plugin_id or provider_key,
            result.provider or "none",
            asset.get("id"),
            asset.get("status") or "ready",
            bool(audio_url),
            result.artifact_bytes,
        )
        return

    failed_asset = upsert_message_audio_asset_status(
        message_id=message_id,
        text=assistant_text,
        provider=provider_key,
        voice=voice,
        status="failed",
        audio_format=result.audio_format or "wav",
        delivery_variants_json=_assistant_message_audio_variants(
            thread_id=thread_id,
            message_id=message_id,
            task_id=task_id,
            turn_id=turn_id,
            status="failed",
            plugin_id=result.plugin_id or provider_key,
            plugin_base_url=result.base_url or plugin_base_url,
            generation_provider=result.provider,
            error={
                "code": result.error_code or "tts_generation_failed",
                "message": result.error_message
                or "Assistant message audio generation failed",
                "failure_kind": result.failure_kind,
            },
        ),
        error={
            "code": result.error_code or "tts_generation_failed",
            "message": result.error_message
            or "Assistant message audio generation failed",
            "failure_kind": result.failure_kind,
        },
    )
    logger.warning(
        "[chat-worker] assistant_message_audio_failed thread_id=%s message_id=%s task_id=%s plugin_id=%s final_status=%s audio_url_present=%s error_code=%s failure_kind=%s",
        thread_id,
        message_id,
        task_id,
        result.plugin_id or provider_key,
        failed_asset.get("status") or "failed",
        bool(
            str(
                failed_asset.get("stream_url")
                or failed_asset.get("src_url")
                or ""
            ).strip()
        ),
        result.error_code or "none",
        result.failure_kind or "none",
    )


def _schedule_assistant_message_audio_generation(
    *,
    thread_id: int,
    message_id: int,
    assistant_text: str,
    task_id: str,
    turn_id: str,
) -> bool:
    if not _assistant_message_audio_autogenerate_effective_enabled():
        logger.info(
            "[chat-worker] assistant_message_audio_skipped thread_id=%s message_id=%s task_id=%s reason=feature_disabled",
            thread_id,
            message_id,
            task_id,
        )
        return False
    if not assistant_text.strip():
        logger.info(
            "[chat-worker] assistant_message_audio_skipped thread_id=%s message_id=%s task_id=%s reason=empty_text",
            thread_id,
            message_id,
            task_id,
        )
        return False

    provider_key, plugin_base_url = _assistant_message_audio_provider_key()
    voice = _assistant_message_audio_voice()
    text_hash = compute_text_hash(assistant_text)

    try:
        cached_asset = find_cached_asset(
            message_id=message_id,
            provider=provider_key,
            voice=voice,
            text_hash=text_hash,
        )
    except Exception:
        logger.warning(
            "[chat-worker] assistant_message_audio_cache_probe_failed thread_id=%s message_id=%s task_id=%s",
            thread_id,
            message_id,
            task_id,
            exc_info=True,
        )
        cached_asset = None
    if cached_asset:
        cached_url = str(
            cached_asset.get("stream_url") or cached_asset.get("src_url") or ""
        ).strip()
        logger.info(
            "[chat-worker] assistant_message_audio_cached thread_id=%s message_id=%s task_id=%s provider=%s final_status=%s audio_url_present=%s",
            thread_id,
            message_id,
            task_id,
            provider_key,
            cached_asset.get("status") or "ready",
            bool(cached_url),
        )
        return False

    try:
        upsert_message_audio_asset_status(
            message_id=message_id,
            text=assistant_text,
            provider=provider_key,
            voice=voice,
            status="pending",
            delivery_variants_json=_assistant_message_audio_variants(
                thread_id=thread_id,
                message_id=message_id,
                task_id=task_id,
                turn_id=turn_id,
                status="pending",
                plugin_id=provider_key,
                plugin_base_url=plugin_base_url,
            ),
        )
    except Exception:
        logger.warning(
            "[chat-worker] assistant_message_audio_pending_write_failed thread_id=%s message_id=%s task_id=%s",
            thread_id,
            message_id,
            task_id,
            exc_info=True,
        )

    try:
        _ASSISTANT_AUDIO_EXECUTOR.submit(
            _generate_assistant_message_audio_artifact,
            thread_id=thread_id,
            message_id=message_id,
            assistant_text=assistant_text,
            task_id=task_id,
            turn_id=turn_id,
            provider_key=provider_key,
            voice=voice,
            plugin_base_url=plugin_base_url,
        )
    except Exception:
        logger.warning(
            "[chat-worker] assistant_message_audio_schedule_failed thread_id=%s message_id=%s task_id=%s",
            thread_id,
            message_id,
            task_id,
            exc_info=True,
        )
        try:
            upsert_message_audio_asset_status(
                message_id=message_id,
                text=assistant_text,
                provider=provider_key,
                voice=voice,
                status="failed",
                delivery_variants_json=_assistant_message_audio_variants(
                    thread_id=thread_id,
                    message_id=message_id,
                    task_id=task_id,
                    turn_id=turn_id,
                    status="failed",
                    plugin_id=provider_key,
                    plugin_base_url=plugin_base_url,
                    error={
                        "code": "schedule_failed",
                        "message": "Assistant message audio generation could not be scheduled",
                    },
                ),
                error={
                    "code": "schedule_failed",
                    "message": "Assistant message audio generation could not be scheduled",
                },
            )
        except Exception:
            logger.warning(
                "[chat-worker] assistant_message_audio_schedule_failure_persist_failed thread_id=%s message_id=%s task_id=%s",
                thread_id,
                message_id,
                task_id,
                exc_info=True,
            )
        return False

    logger.info(
        "[chat-worker] assistant_message_audio_pending thread_id=%s message_id=%s task_id=%s provider=%s",
        thread_id,
        message_id,
        task_id,
        provider_key,
    )
    return True


def _normalize_provider_override(value: Any) -> str | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    normalized = normalize_provider(raw)
    return normalized or None


def _normalize_model_override(value: Any) -> str | None:
    normalized = str(value or "").strip()
    if normalized.lower() in {"", "auto"}:
        return None
    return normalized or None


def extract_assistant_response(text: str) -> str:
    """Normalize model output to the final assistant-visible response."""

    if not text:
        return text

    if "System Response ===" in text:
        return text.split("System Response ===")[-1].strip()

    if "=== SCRATCHPAD ===" in text:
        return text.split("=== SCRATCHPAD ===")[-1].strip()

    return text.strip()


def _extract_visible_stream_text(chunk: Any) -> str:
    """Enforce the public stream contract: content only, never reasoning."""

    if isinstance(chunk, str):
        return chunk

    if not isinstance(chunk, dict):
        return ""

    delta = chunk.get("delta")
    if isinstance(delta, dict):
        content = delta.get("content")
        if isinstance(content, str):
            return content
        if content is not None:
            return str(content)
        # Explicitly ignore reasoning/thinking deltas.
        return ""

    content = chunk.get("content")
    if isinstance(content, str):
        return content
    if "content" in chunk and content is not None:
        return str(content)

    message = chunk.get("message")
    if isinstance(message, dict):
        nested_content = message.get("content")
        if isinstance(nested_content, str):
            return nested_content
        if nested_content is not None:
            return str(nested_content)

    return ""


def _sanitize_assistant_result_payload(result: dict[str, Any]) -> None:
    """Strip provider-specific reasoning fields from the public assistant payload."""

    result.pop("thinking", None)
    result.pop("reasoning", None)

    execution = result.get("execution")
    if isinstance(execution, dict):
        execution.pop("thinking", None)
        execution.pop("reasoning", None)


def _degraded_provider_model_fallback(
    *,
    provider: str,
    requested_model: str | None,
    reason: str | None,
    settings: Settings,
) -> str | None:
    if "no chat-capable models" not in str(reason or "").lower():
        return None

    logger.error(
        "[chat-worker] no chat-capable models after resolution; attempting degraded fallback provider=%s",
        provider,
    )
    try:
        capability = resolve_provider_capability(provider, settings)
    except Exception:
        logger.warning(
            "[chat-worker] degraded fallback capability lookup failed provider=%s",
            provider,
            exc_info=True,
        )
        return None

    fallback_models = [
        candidate
        for candidate in (
            _normalize_model_override(item.get("id"))
            for item in (capability.get("models") or [])
            if isinstance(item, dict)
        )
        if candidate
    ]
    if not fallback_models:
        return None

    normalized_requested = _normalize_model_override(requested_model)
    selected_model = (
        normalized_requested
        if normalized_requested in fallback_models
        else fallback_models[0]
    )
    logger.warning(
        "[chat-worker] using fallback model set due to classification failure provider=%s model=%s",
        provider,
        selected_model,
    )
    return selected_model


class AssistantPersistenceError(RuntimeError):
    def __init__(self, message: str, *, metadata: dict[str, Any] | None = None):
        super().__init__(message)
        self.metadata = dict(metadata or {})


def _coerce_build_messages_result(
    payload: Any,
) -> tuple[
    list[dict[str, str]],
    str,
    str,
    dict[str, Any],
    dict[str, Any] | None,
]:
    if not isinstance(payload, tuple) or len(payload) < 3:
        raise RuntimeError("invalid_build_messages_result")

    messages = list(payload[0] or [])
    provider = str(payload[1] or "").strip().lower()
    model = str(payload[2] or "").strip()
    bundle = (
        dict(payload[3])
        if len(payload) > 3 and isinstance(payload[3], dict)
        else {}
    )
    if len(payload) >= 7:
        trace = payload[6] if isinstance(payload[6], dict) else None
    elif len(payload) > 4 and isinstance(payload[4], dict):
        trace = payload[4]
    else:
        trace = None
    return messages, provider, model, bundle, trace


def _merge_system_messages(
    messages: list[dict[str, str]],
    *,
    extras: list[str] | None = None,
) -> list[dict[str, str]]:
    extras = [item for item in (extras or []) if str(item or "").strip()]
    merged_parts: list[str] = []
    other_messages: list[dict[str, str]] = []

    for message in messages:
        role = str(message.get("role") or "").strip().lower()
        content = str(message.get("content") or "").strip()
        if role == "system":
            if content and content not in merged_parts:
                merged_parts.append(content)
            continue
        other_messages.append(message)

    for extra in extras:
        cleaned = str(extra or "").strip()
        if cleaned and cleaned not in merged_parts:
            merged_parts.append(cleaned)

    if not merged_parts:
        return messages

    return [
        {"role": "system", "content": "\n\n".join(merged_parts)},
        *other_messages,
    ]


def _compat_context_system_message_with_meta(
    bundle: dict[str, Any] | None,
) -> tuple[str | None, dict[str, Any]]:
    """Bridge older build_context_system_message patch points to the new meta API."""

    message, meta = _ORIGINAL_BUILD_CONTEXT_SYSTEM_MESSAGE_WITH_META(bundle)

    compat_message: str | None
    try:
        compat_message = build_context_system_message(bundle)
    except Exception:
        compat_message = None

    final_message = message
    if compat_message and compat_message.strip():
        if final_message and final_message.strip():
            if compat_message.strip() != final_message.strip():
                final_message = "\n\n".join(
                    [final_message.strip(), compat_message.strip()]
                )
        else:
            final_message = compat_message

    return final_message, meta


def _compat_resolve_task(task: ChatCompletionTask) -> ChatCompletionTask:
    settings = get_settings()
    profile = None
    try:
        profile = resolve_thread_system_profile(
            task.thread_id,
            chatlog_db=getattr(dependencies, "chatlog_db", None),
        )
    except Exception:
        profile = None

    requested_provider = _normalize_provider_override(task.provider)
    requested_model = _normalize_model_override(task.model)
    selection_source = (
        str(getattr(task, "selection_source", "") or "").strip() or None
    )
    provider_pinned = bool(getattr(task, "provider_pinned", False))
    model_resolved_provider: str | None = None

    provider = requested_provider
    model = requested_model

    if model:
        try:
            resolved_provider = resolve_provider_for_model(
                model, settings=settings
            )
        except Exception:
            if provider is None:
                raise
            logger.debug(
                "[chat-worker] model/provider resolution lookup failed provider=%s model=%s",
                provider,
                model,
                exc_info=True,
            )
            resolved_provider = None
        if resolved_provider:
            model_resolved_provider = _normalize_provider_override(
                resolved_provider
            )
            if provider and provider != resolved_provider:
                valid, reason = validate_provider_model_selection(
                    provider_id=provider,
                    model_id=model,
                    settings=settings,
                )
                if not valid:
                    raise LLMConfigError(
                        reason or "Requested model is not available"
                    )
            provider = _normalize_provider_override(
                provider or resolved_provider
            )
        elif provider is None:
            raise LLMConfigError(f"Requested model '{model}' is not available")

    if provider is None:
        provider = _normalize_provider_override(
            getattr(profile, "provider_override", None)
        )
        if provider and selection_source is None:
            selection_source = "profile"

    if provider is None:
        provider = _normalize_provider_override(
            settings.LLM_PROVIDER
            or getattr(dependencies, "CHAT_PROVIDER", None)
        )
        if provider and selection_source is None:
            selection_source = "default"

    if provider is None:
        provider = _normalize_provider_override(
            first_enabled_provider(settings=settings)
        )
        if provider and selection_source is None:
            selection_source = "default"

    if model is None:
        model = _normalize_model_override(
            getattr(profile, "model_override", None)
        )
    if model is None and provider:
        model = _normalize_model_override(
            default_model_for_provider(provider, settings)
            or first_model_for_provider(provider, settings=settings)
        )

    if provider and isinstance(settings, Settings):
        explicit_model_bound_provider = bool(
            requested_model
            and model_resolved_provider
            and provider == model_resolved_provider
            and requested_provider is None
        )
        if not explicit_model_bound_provider:
            valid, reason = validate_provider_model_selection(
                provider_id=provider,
                model_id=model,
                settings=settings,
            )
            if not valid:
                fallback_model = _degraded_provider_model_fallback(
                    provider=provider,
                    requested_model=model,
                    reason=reason,
                    settings=settings,
                )
                if fallback_model is None:
                    raise LLMConfigError(
                        reason or "Provider/model selection is invalid"
                    )
                model = fallback_model

    return replace(
        task,
        provider=provider,
        model=model,
        requested_provider=requested_provider,
        requested_model=requested_model,
        selection_source=selection_source
        or (
            "explicit" if (requested_provider or requested_model) else "default"
        ),
        provider_pinned=provider_pinned,
    )


def _sync_build_messages_compat_seams() -> None:
    _chat_completion_service.get_settings = get_settings
    _chat_completion_service.validate_llm_config = validate_llm_config
    _chat_completion_service.ContextBroker = ContextBroker
    _chat_completion_service.build_guardian_system_prompt = (
        build_guardian_system_prompt
    )
    _chat_completion_service.build_context_system_message_with_meta = (
        _build_context_system_message_with_meta_compat
    )


async def _build_messages_for_llm(
    task: ChatCompletionTask,
) -> tuple[
    list[dict[str, str]],
    str,
    str,
    dict[str, Any],
    Any,
    Any,
    dict[str, Any] | None,
]:
    resolved_task = _compat_resolve_task(task)
    _sync_build_messages_compat_seams()
    messages, provider, model, bundle, trace = _coerce_build_messages_result(
        await _ORIGINAL_BUILD_MESSAGES_FOR_LLM(resolved_task)
    )
    provider = _normalize_provider_override(resolved_task.provider) or provider
    model = _normalize_model_override(resolved_task.model) or model

    extra_system_messages: list[str] = []
    media_items = _resolve_media_items(resolved_task, bundle, provider=provider)
    media_system_message = _build_media_system_message(media_items)
    if media_system_message:
        extra_system_messages.append(str(media_system_message))
    _maybe_add_vision_summary(media_items, provider)

    merged_messages = _merge_system_messages(
        messages,
        extras=extra_system_messages,
    )
    return merged_messages, provider, model, bundle, None, None, trace


def _run_chat_completion_task_compat(
    task: ChatCompletionTask,
    *,
    token_callback: Any = None,
    cancel_check: Any = None,
    persist_assistant_message: bool = True,
) -> dict[str, Any]:
    build_result = asyncio.run(_build_messages_for_llm(task))
    (
        messages_for_llm,
        provider,
        model,
        bundle,
        trace,
    ) = _coerce_build_messages_result(build_result)
    payload_summary = _chat_completion_service.build_sanitized_payload_summary(
        messages_for_llm,
        bundle,
        provider=provider,
        model=model,
    )
    settings = get_settings()
    attempted_provider = provider
    attempted_model = model
    selection_source = str(
        getattr(task, "selection_source", "") or ""
    ).strip() or (
        "explicit"
        if (
            _normalize_provider_override(
                getattr(task, "requested_provider", None) or task.provider
            )
            or _normalize_model_override(
                getattr(task, "requested_model", None) or task.model
            )
        )
        else "default"
    )
    provider_pinned = bool(getattr(task, "provider_pinned", False))
    completion_truth = _completion_truth(
        accepted=True,
        attempted=False,
        fallback_attempted=False,
        executed=False,
        completed=False,
    )

    def _execute_completion(
        execution_provider: str,
        execution_model: str,
    ) -> str:
        assistant_output = ""
        if execution_provider == "local":
            streamed_any = False
            token_stream = stream_local(
                messages_for_llm,
                execution_model,
                reasoning_mode=getattr(task, "reasoning_mode", None),
            )
            try:
                for token in token_stream:
                    if cancel_check and cancel_check():
                        raise ChatTaskCancelled("task_cancelled")
                    visible_token = _extract_visible_stream_text(token)
                    if visible_token:
                        streamed_any = True
                        assistant_output += visible_token
                        if token_callback:
                            token_callback(visible_token)
            finally:
                token_stream.close()

            if not assistant_output.strip():
                assistant_output = _extract_visible_stream_text(
                    chat_with_ai(
                        messages_for_llm,
                        model=execution_model,
                        provider=execution_provider,
                        reasoning_mode=getattr(task, "reasoning_mode", None),
                        prompt_meta=(
                            dict(bundle.get("_prompt_meta") or {})
                            if isinstance(bundle, dict)
                            else None
                        ),
                    )
                )
                if token_callback and (not streamed_any) and assistant_output:
                    token_callback(extract_assistant_response(assistant_output))
            return assistant_output

        if cancel_check and cancel_check():
            raise ChatTaskCancelled("task_cancelled")
        assistant_output = _extract_visible_stream_text(
            chat_with_ai(
                messages_for_llm,
                model=execution_model,
                provider=execution_provider,
                reasoning_mode=getattr(task, "reasoning_mode", None),
                prompt_meta=(
                    dict(bundle.get("_prompt_meta") or {})
                    if isinstance(bundle, dict)
                    else None
                ),
            )
        )
        if token_callback:
            token_callback(extract_assistant_response(assistant_output))
        return assistant_output

    fallback_reason: str | None = None
    failure_meta: dict[str, Any] = {}
    final_provider = provider
    final_model = model
    try:
        completion_truth["attempted"] = True
        assistant_text = _execute_completion(provider, model)
        completion_truth["executed"] = True
    except Exception as exc:
        failure_meta = _task_error_metadata(exc)
        should_rescue = bool(
            selection_source != "explicit"
            and not provider_pinned
            and _should_attempt_provider_fallback(exc)
        )
        fallback_candidates = _fallback_provider_candidates(
            attempted_provider=provider,
            settings=settings,
        )
        failure_meta.update(
            {
                "provider": provider,
                "model": model,
                "attempted_provider": attempted_provider,
                "attempted_model": attempted_model,
                "resolved_provider": provider,
                "resolved_model": model,
                "selection_source": selection_source,
                "fallback_reason": fallback_reason,
                "completion_truth": completion_truth,
            }
        )
        if not should_rescue or not fallback_candidates:
            detail = getattr(exc, "detail", None)
            if isinstance(detail, dict):
                detail.update(failure_meta)
            else:
                exc.metadata = failure_meta
            raise
        completion_truth["fallback_attempted"] = True
        rescued = False
        fallback_errors: list[str] = []
        for fallback_provider, fallback_model in fallback_candidates:
            logger.warning(
                "[chat-worker] provider_rescue_start attempted_provider=%s attempted_model=%s selection_source=%s provider_pinned=%s fallback_provider=%s fallback_model=%s",
                provider,
                model,
                selection_source,
                provider_pinned,
                fallback_provider,
                fallback_model,
            )
            try:
                assistant_text = _execute_completion(
                    fallback_provider, fallback_model
                )
                fallback_reason = (
                    "cloud_failure_local_rescue"
                    if fallback_provider == "local" and provider != "local"
                    else f"{provider}_failure_{fallback_provider}_rescue"
                )
                final_provider = fallback_provider
                final_model = fallback_model
                completion_truth["executed"] = True
                rescued = True
                break
            except Exception as fallback_exc:
                fallback_errors.append(_describe_task_error(fallback_exc))
        if not rescued:
            if fallback_errors:
                failure_meta["fallback_errors"] = fallback_errors
            detail = getattr(exc, "detail", None)
            if isinstance(detail, dict):
                detail.update(failure_meta)
            else:
                exc.metadata = failure_meta
            raise
        payload_summary["final_provider"] = final_provider
        payload_summary["final_model"] = final_model

    logger.debug("[llm] raw_output=%s", assistant_text)
    assistant_text = extract_assistant_response(assistant_text)

    if not assistant_text.strip():
        assistant_text = "No assistant response was generated."

    attempted_provider_truth = build_provider_truth(
        attempted_provider,
        settings,
        attempted=True,
        executed=bool(
            completion_truth["executed"]
            and attempted_provider == final_provider
        ),
        completed=bool(
            completion_truth["executed"]
            and attempted_provider == final_provider
        ),
    )
    final_provider_truth = build_provider_truth(
        final_provider,
        settings,
        attempted=bool(
            completion_truth["fallback_attempted"]
            or attempted_provider == final_provider
        ),
        executed=completion_truth["executed"],
        completed=False,
    )

    payload_summary.update(
        {
            "attempted_provider": attempted_provider,
            "attempted_model": attempted_model,
            "resolved_provider": provider,
            "resolved_model": model,
            "final_provider": final_provider,
            "final_model": final_model,
            "fallback_reason": fallback_reason,
            "completion_truth": completion_truth,
            "attempted_provider_truth": attempted_provider_truth,
            "final_provider_truth": final_provider_truth,
        }
    )

    execution = {
        "attempted_provider": attempted_provider,
        "attempted_model": attempted_model,
        "final_provider": final_provider,
        "final_model": final_model,
        "fallback_triggered": bool(completion_truth.get("fallback_attempted")),
    }

    result: dict[str, Any] = {
        "assistant_text": assistant_text,
        "provider": final_provider,
        "model": final_model,
        "attempted_provider": attempted_provider,
        "attempted_model": attempted_model,
        "resolved_provider": provider,
        "resolved_model": model,
        "selection_source": selection_source,
        "fallback_reason": fallback_reason,
        "upstream_status": failure_meta.get("upstream_status"),
        "provider_error": failure_meta.get("provider_error"),
        "transport_classification": failure_meta.get(
            "transport_classification"
        ),
        "provider_failure_kind": failure_meta.get("failure_kind"),
        "provider_failure_message": failure_meta.get("message"),
        "completion_truth": completion_truth,
        "attempted_provider_truth": attempted_provider_truth,
        "final_provider_truth": final_provider_truth,
        "execution": execution,
        "bundle": bundle,
        "trace": trace,
        "thread_id": task.thread_id,
        "payload_summary": payload_summary,
    }
    _sanitize_assistant_result_payload(result)

    if not persist_assistant_message:
        return result

    try:
        message_id = dependencies.chatlog_db.create_message(
            task.thread_id,
            "assistant",
            assistant_text,
        )
    except Exception as exc:
        persistence_meta = {
            "error": "assistant_message_persist_failed",
            "message": "Assistant generation succeeded but persistence failed",
            "attempted_provider": attempted_provider,
            "attempted_model": attempted_model,
            "resolved_provider": provider,
            "resolved_model": model,
            "final_provider": final_provider,
            "final_model": final_model,
            "selection_source": selection_source,
            "fallback_reason": fallback_reason,
            "assistant_text_chars": len(assistant_text),
            "persistence_outcome": "failed",
            "completion_truth": completion_truth,
            "attempted_provider_truth": attempted_provider_truth,
            "final_provider_truth": final_provider_truth,
            "execution": execution,
        }
        logger.error(
            "[chat-worker] assistant_message_persist_failed thread_id=%s attempted_provider=%s attempted_model=%s final_provider=%s final_model=%s chars=%s",
            task.thread_id,
            attempted_provider,
            attempted_model,
            final_provider,
            final_model,
            len(assistant_text),
            exc_info=True,
        )
        raise AssistantPersistenceError(
            "assistant_message_persist_failed",
            metadata=persistence_meta,
        ) from exc
    result["message_id"] = message_id
    result["persistence_outcome"] = "persisted"
    completion_truth["completed"] = True
    final_provider_truth["completed"] = True

    with suppress(Exception):
        _persist_message_extra_meta(
            thread_id=task.thread_id,
            message_id=message_id,
            payload={
                "attempted_provider": attempted_provider,
                "attempted_model": attempted_model,
                "resolved_provider": provider,
                "resolved_model": model,
                "final_provider": final_provider,
                "final_model": final_model,
                "selection_source": selection_source,
                "fallback_reason": fallback_reason,
                "payload_summary": payload_summary,
                "completion_truth": completion_truth,
                "attempted_provider_truth": attempted_provider_truth,
                "final_provider_truth": final_provider_truth,
                "execution": execution,
            },
        )

    with suppress(Exception):
        dependencies.chatlog_db.write_audit_log(
            "create",
            "chat_message",
            str(message_id),
            user_id="bot",
        )

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


run_chat_completion_task = _run_chat_completion_task_compat


def _run_chat_task(task: ChatCompletionTask) -> None:
    run_id = uuid.uuid4().hex
    started = time.monotonic()
    turn_id = _extract_turn_id(task)
    _safe_publish(
        task.task_id,
        "task.running",
        {
            "run_id": run_id,
            "type": task.type,
            "origin": task.origin,
            "thread_id": task.thread_id,
            "turn_id": turn_id,
        },
    )
    logger.info(
        "[task] running type=%s id=%s run_id=%s origin=%s thread=%s turn_id=%s",
        task.type,
        task.task_id,
        run_id,
        task.origin,
        task.thread_id,
        turn_id,
    )

    try:
        existing_message_id = _find_assistant_message_for_turn(
            thread_id=task.thread_id,
            turn_id=turn_id,
        )
        if existing_message_id is not None:
            duration_ms = int((time.monotonic() - started) * 1000)
            logger.warning(
                "[chat-worker] duplicate_turn_detected thread_id=%s turn_id=%s task_id=%s existing_message_id=%s",
                task.thread_id,
                turn_id,
                task.task_id,
                existing_message_id,
            )
            _safe_publish(
                task.task_id,
                "task.completed",
                {
                    "run_id": run_id,
                    "duration_ms": duration_ms,
                    "thread_id": task.thread_id,
                    "turn_id": turn_id,
                    "message_id": existing_message_id,
                    "provider": task.provider,
                    "model": task.model,
                    "selection_source": "turn_id_dedupe",
                    "catalog_version_hash": None,
                },
            )
            return

        if is_cancelled(task.task_id):
            _safe_publish(
                task.task_id,
                "task.cancelled",
                {
                    "run_id": run_id,
                    "thread_id": task.thread_id,
                    "origin": task.origin,
                    "turn_id": turn_id,
                },
            )
            clear_cancelled(task.task_id)
            logger.info(
                "[task] cancelled type=%s id=%s run_id=%s turn_id=%s",
                task.type,
                task.task_id,
                run_id,
                turn_id,
            )
            return

        if turn_id:
            existing_message_id = _find_assistant_message_id_by_turn_id(
                thread_id=task.thread_id,
                turn_id=turn_id,
            )
            if existing_message_id is not None:
                duration_ms = int((time.monotonic() - started) * 1000)
                logger.warning(
                    "[chat-worker] duplicate_turn_prevented thread_id=%s turn_id=%s task_id=%s message_id=%s",
                    task.thread_id,
                    turn_id,
                    task.task_id,
                    existing_message_id,
                )
                _safe_publish(
                    task.task_id,
                    "task.completed",
                    {
                        "run_id": run_id,
                        "duration_ms": duration_ms,
                        "thread_id": task.thread_id,
                        "turn_id": turn_id,
                        "message_id": existing_message_id,
                        "deduplicated": True,
                        "provider": task.provider,
                        "model": task.model,
                    },
                )
                logger.info(
                    "[task] completed type=%s id=%s run_id=%s thread=%s turn_id=%s message_id=%s deduplicated=%s",
                    task.type,
                    task.task_id,
                    run_id,
                    task.thread_id,
                    turn_id,
                    existing_message_id,
                    True,
                )
                return

        result = run_chat_completion_task(
            task,
            token_callback=lambda token: _safe_publish(
                task.task_id,
                "task.progress",
                {
                    "run_id": run_id,
                    "token": (
                        token[:4096] if isinstance(token, str) else token
                    ),
                    "thread_id": task.thread_id,
                },
            ),
            cancel_check=lambda: is_cancelled(task.task_id),
            persist_assistant_message=True,
        )
        message_id = _coerce_message_id(result.get("message_id"))
        if message_id is None:
            logger.error(
                "[chat-worker] completion_missing_message thread_id=%s turn_id=%s task_id=%s",
                task.thread_id,
                turn_id,
                task.task_id,
            )
            raise RuntimeError("assistant_message_missing")

        cached_anchor = _cache_turn_completion_anchor(
            thread_id=task.thread_id,
            message_id=message_id,
            turn_id=turn_id,
        )
        if turn_id and not cached_anchor:
            logger.warning(
                "[chat-worker] turn_completion_anchor_cache_failed thread_id=%s turn_id=%s task_id=%s message_id=%s",
                task.thread_id,
                turn_id,
                task.task_id,
                message_id,
            )
        if turn_id:
            try:
                persisted = _persist_turn_id_metadata(
                    thread_id=task.thread_id,
                    message_id=message_id,
                    turn_id=turn_id,
                )
                if not persisted:
                    logger.warning(
                        "[chat-worker] completion_turn_metadata_missing thread_id=%s turn_id=%s task_id=%s message_id=%s",
                        task.thread_id,
                        turn_id,
                        task.task_id,
                        message_id,
                    )
                    logger.warning(
                        "[chat-worker] turn_id_metadata_persist_failed reason=persist_returned_false thread_id=%s turn_id=%s task_id=%s message_id=%s",
                        task.thread_id,
                        turn_id,
                        task.task_id,
                        message_id,
                    )
                    _record_turn_metadata_persist_failure(
                        "persist_returned_false"
                    )
            except Exception as exc:
                logger.warning(
                    "[chat-worker] turn_id_metadata_persist_failed reason=exception thread_id=%s turn_id=%s task_id=%s message_id=%s err=%s",
                    task.thread_id,
                    turn_id,
                    task.task_id,
                    message_id,
                    exc,
                    exc_info=True,
                )
                _record_turn_metadata_persist_failure("exception")
        if turn_id:
            canonical_message_id = _find_assistant_message_id_by_turn_id(
                thread_id=task.thread_id,
                turn_id=turn_id,
            )
            if (
                canonical_message_id is not None
                and canonical_message_id != message_id
            ):
                logger.warning(
                    "[chat-worker] completion_duplicate_turn_detected thread_id=%s turn_id=%s task_id=%s canonical_message_id=%s duplicate_message_id=%s",
                    task.thread_id,
                    turn_id,
                    task.task_id,
                    canonical_message_id,
                    message_id,
                )
                message_id = canonical_message_id

        logger.info(
            "[chat-worker] assistant_message_persisted thread_id=%s turn_id=%s task_id=%s assistant_message_id=%s",
            task.thread_id,
            turn_id,
            task.task_id,
            message_id,
        )
        assistant_text = str(result.get("assistant_text") or "")
        audio_autogenerate_scheduled = False
        try:
            audio_autogenerate_scheduled = (
                _schedule_assistant_message_audio_generation(
                    thread_id=task.thread_id,
                    message_id=message_id,
                    assistant_text=assistant_text,
                    task_id=task.task_id,
                    turn_id=turn_id,
                )
            )
        except Exception:
            logger.warning(
                "[chat-worker] assistant_message_audio_schedule_unexpected_failure thread_id=%s message_id=%s task_id=%s",
                task.thread_id,
                message_id,
                task.task_id,
                exc_info=True,
            )
        duration_ms = int((time.monotonic() - started) * 1000)
        _safe_publish(
            task.task_id,
            "task.completed",
            {
                "run_id": run_id,
                "duration_ms": duration_ms,
                "thread_id": task.thread_id,
                "turn_id": turn_id,
                "message_id": message_id,
                "provider": result.get("provider"),
                "model": result.get("model"),
                "attempted_provider": result.get("attempted_provider"),
                "attempted_model": result.get("attempted_model"),
                "resolved_provider": result.get("resolved_provider"),
                "resolved_model": result.get("resolved_model"),
                "selection_source": result.get("selection_source"),
                "fallback_reason": result.get("fallback_reason"),
                "upstream_status": result.get("upstream_status"),
                "provider_error": result.get("provider_error"),
                "transport_classification": result.get(
                    "transport_classification"
                ),
                "provider_failure_kind": result.get("provider_failure_kind"),
                "provider_failure_message": result.get(
                    "provider_failure_message"
                ),
                "completion_truth": result.get("completion_truth"),
                "attempted_provider_truth": result.get(
                    "attempted_provider_truth"
                ),
                "final_provider_truth": result.get("final_provider_truth"),
                "execution": result.get("execution"),
                "persistence_outcome": result.get("persistence_outcome"),
                "catalog_version_hash": result.get("catalog_version_hash"),
                "assistant_message_audio_autogenerate": audio_autogenerate_scheduled,
                "payload_summary": result.get("payload_summary"),
            },
        )
        logger.info(
            "[task] completed type=%s id=%s run_id=%s thread=%s turn_id=%s message_id=%s",
            task.type,
            task.task_id,
            run_id,
            task.thread_id,
            turn_id,
            message_id,
        )
    except ChatTaskCancelled:
        _safe_publish(
            task.task_id,
            "task.cancelled",
            {
                "run_id": run_id,
                "thread_id": task.thread_id,
                "origin": task.origin,
                "turn_id": turn_id,
            },
        )
        clear_cancelled(task.task_id)
        logger.info(
            "[task] cancelled type=%s id=%s run_id=%s turn_id=%s",
            task.type,
            task.task_id,
            run_id,
            turn_id,
        )
    except Exception as exc:
        duration_ms = int((time.monotonic() - started) * 1000)
        error_detail = _describe_task_error(exc)
        error_metadata = _task_error_metadata(exc)
        failure_payload = {
            "run_id": run_id,
            "duration_ms": duration_ms,
            "error": error_detail,
            "error_type": exc.__class__.__name__,
            "thread_id": task.thread_id,
            "origin": task.origin,
            "turn_id": turn_id,
        }
        for key in (
            "provider",
            "model",
            "attempted_provider",
            "attempted_model",
            "resolved_provider",
            "resolved_model",
            "selection_source",
            "fallback_reason",
            "upstream_status",
            "provider_error",
            "transport_classification",
            "failure_kind",
            "message",
            "persistence_outcome",
            "completion_truth",
            "attempted_provider_truth",
            "final_provider_truth",
        ):
            value = error_metadata.get(key)
            if value is not None:
                normalized_key = (
                    "provider_failure_message" if key == "message" else key
                )
                failure_payload[normalized_key] = value
        runtime_status = _classify_runtime_status(error_detail)
        if runtime_status:
            failure_payload["runtime_status"] = runtime_status
        if task.provider:
            failure_payload["provider"] = task.provider
        if task.model:
            failure_payload["model"] = task.model
        _safe_publish(
            task.task_id,
            "task.failed",
            failure_payload,
        )
        _safe_emit_live_event(
            "completion.error",
            {
                **failure_payload,
                "task_id": task.task_id,
            },
        )
        logger.exception(
            "[task] failed type=%s id=%s run_id=%s turn_id=%s err=%s",
            task.type,
            task.task_id,
            run_id,
            turn_id,
            exc,
        )
    finally:
        owner = str(getattr(task, "turn_lock_owner", "") or "").strip()
        if not owner:
            owner = str(task.task_id or "").strip()
        if owner:
            try:
                released = release_turn_lock(task.thread_id, owner)
                if not released:
                    logger.debug(
                        "[turn-lock] release skipped thread=%s owner=%s",
                        task.thread_id,
                        owner,
                    )
            except Exception as exc:
                logger.warning(
                    "[turn-lock] release failed thread=%s owner=%s err=%s",
                    task.thread_id,
                    owner,
                    exc,
                )


def _initialize_worker() -> None:
    db = dependencies.init_database()
    if db is None:
        raise RuntimeError("chatlog_db not configured")
    dependencies.init_services(db)
    try:
        if dependencies.ENABLE_OUTBOX:
            event_bus.configure_event_store(db)
    except Exception as exc:
        logger.warning(
            "[chat-worker] outbox disabled; falling back to in-memory: %s",
            exc,
        )
    _publish_worker_heartbeat("starting")


def run_forever() -> None:
    _initialize_worker()
    logger.info(
        "[chat-worker] started queue=%s concurrency=%s",
        QUEUE_NAME,
        CONCURRENCY,
    )
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        while True:
            _publish_worker_heartbeat("idle")
            try:
                payload = dequeue(QUEUE_NAME, block=True, timeout=5)
            except RedisTimeoutError:
                logger.debug("[chat-worker] redis idle timeout; continuing")
                continue
            except RedisConnectionError as exc:
                logger.warning(
                    "[chat-worker] dequeue error; continuing: %s", exc
                )
                time.sleep(1.0)
                continue

            if not payload:
                continue
            _publish_worker_heartbeat("active")
            try:
                task = task_from_dict(payload)
            except Exception as exc:
                logger.warning("[chat-worker] invalid task payload: %s", exc)
                continue
            if not isinstance(task, ChatCompletionTask):
                logger.warning(
                    "[chat-worker] skipping non-chat task type=%s id=%s",
                    task.type,
                    task.task_id,
                )
                continue
            if isinstance(payload, dict):
                raw_turn_id = payload.get("turn_id")
                if isinstance(raw_turn_id, str) and raw_turn_id.strip():
                    task.turn_id = raw_turn_id.strip()
                raw_owner = payload.get("turn_lock_owner")
                if isinstance(raw_owner, str) and raw_owner.strip():
                    task.turn_lock_owner = raw_owner.strip()
            if is_cancelled(task.task_id):
                _safe_publish(
                    task.task_id,
                    "task.cancelled",
                    {
                        "type": task.type,
                        "origin": task.origin,
                        "turn_id": _extract_turn_id(task),
                    },
                )
                clear_cancelled(task.task_id)
                logger.info(
                    "[task] cancelled type=%s id=%s", task.type, task.task_id
                )
                continue
            executor.submit(_run_chat_task, task)


if __name__ == "__main__":
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    run_forever()
