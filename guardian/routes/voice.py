"""Voice capabilities, turn-based ingest, and message read-aloud routes."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
import os
import time
import uuid
from functools import lru_cache
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Response,
    UploadFile,
)
from pydantic import BaseModel

from guardian.core.db import load_guardian_db_from_env
from guardian.core.dependencies import chatlog_db, require_api_key
from guardian.core.storage import create_storage_from_env
from guardian.db.models import ChatMessage, MessageAudioAsset
from guardian.queue import task_events
from guardian.queue.redis_queue import enqueue, get_redis_client
from guardian.queue.turn_lock import (
    acquire_turn_lock,
    release_turn_lock,
    turn_lock_key,
)
from guardian.voice.audio_assets import (
    compute_text_hash,
    find_cached_asset,
    save_message_audio_asset,
)
from guardian.voice.client import synthesize
from guardian.voice.config import get_voice_runtime_config
from guardian.voice.runtime import (
    STREAM_PROXY_ENABLED,
    SUPPORTED_INPUT_MIME,
    SUPPORTED_STT_PROVIDERS,
    SUPPORTED_TTS_PROVIDERS,
    VOICE_HEARTBEAT_KEY,
    VOICE_QUEUE_NAME,
)
from guardian.voice.service import VoiceValidationError, normalize_audio_input

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/voice", tags=["Voice"])
_storage = create_storage_from_env()

_DEDUPE_KEY_PREFIX = "codexify:voice:turn:dedupe"


class SpeakRequest(BaseModel):
    provider: str | None = None
    voice: str | None = None
    output_format: str | None = None
    force_regenerate: bool = False


class SpeakResponse(BaseModel):
    message_id: int
    audio_asset: dict[str, Any]
    cached: bool
    text_hash: str


@lru_cache(maxsize=1)
def _get_voice_turn_task_cls():
    try:
        from guardian.tasks.types import VoiceTurnTask
    except Exception:
        return None
    return VoiceTurnTask


def _dedupe_key(thread_id: int, turn_id: str, audio_sha256: str) -> str:
    return f"{_DEDUPE_KEY_PREFIX}:{thread_id}:{turn_id}:{audio_sha256}"


def _normalize_turn_id(raw: str | None) -> str:
    value = (raw or "").strip()
    if not value:
        return "legacy"
    try:
        return str(uuid.UUID(value)).lower()
    except Exception:
        return "legacy"


def _task_terminal_status(task_id: str) -> str:
    stream_key = f"codexify:task:{task_id}:events"
    try:
        client = get_redis_client()
        rows = client.xrevrange(stream_key, count=20)
    except Exception:
        return "in_flight"

    for _, fields in rows or []:
        event_type = str(fields.get("type") or "").strip().lower()
        if event_type == "task.completed":
            return "succeeded"
        if event_type in {"task.failed", "task.cancelled"}:
            return "failed"
    return "in_flight"


def _get_dedupe_hit(
    *,
    thread_id: int,
    turn_id: str,
    audio_sha256: str,
) -> dict[str, Any] | None:
    key = _dedupe_key(thread_id, turn_id, audio_sha256)
    try:
        client = get_redis_client()
        raw = client.get(key)
    except Exception:
        return None

    if not raw:
        return None
    try:
        payload = json.loads(raw)
    except Exception:
        return None

    task_id = str(payload.get("task_id") or "").strip()
    if not task_id:
        return None
    return {
        "deduped": True,
        "task_id": task_id,
        "status": _task_terminal_status(task_id),
    }


def _set_dedupe_record(
    *,
    thread_id: int,
    turn_id: str,
    audio_sha256: str,
    task_id: str,
    ttl_seconds: int,
) -> None:
    key = _dedupe_key(thread_id, turn_id, audio_sha256)
    payload = {
        "task_id": task_id,
        "created_at": int(time.time()),
    }
    try:
        client = get_redis_client()
        client.setex(key, max(1, int(ttl_seconds)), json.dumps(payload))
    except Exception:
        logger.debug("[voice.turn] failed writing dedupe record", exc_info=True)


def _voice_worker_available() -> bool:
    try:
        client = get_redis_client()
        return bool(client.get(VOICE_HEARTBEAT_KEY))
    except Exception:
        return False


def _configured_provider(
    provider: str | None,
    *,
    supported: tuple[str, ...],
    local_voice_base_url: str | None,
) -> str | None:
    value = str(provider or "").strip().lower()
    if not value:
        return None
    if value not in supported:
        return None
    if (
        value in {"local_openai_compatible", "whispercpp"}
        and not local_voice_base_url
    ):
        return None
    return value


def _load_message(message_id: int) -> ChatMessage | None:
    db = chatlog_db or load_guardian_db_from_env()
    if not db or not hasattr(db, "get_session"):
        return None
    with db.get_session() as session:
        row = session.query(ChatMessage).filter_by(id=message_id).first()
        return row


def _load_audio_asset(asset_id: int) -> MessageAudioAsset | None:
    db = chatlog_db or load_guardian_db_from_env()
    if not db or not hasattr(db, "get_session"):
        return None
    with db.get_session() as session:
        return session.query(MessageAudioAsset).filter_by(id=asset_id).first()


def _content_type_for_format(fmt: str | None) -> str:
    value = str(fmt or "wav").strip().lower()
    if value in {"mp3", "mpeg"}:
        return "audio/mpeg"
    if value in {"ogg", "opus"}:
        return "audio/ogg"
    return "audio/wav"


def _with_stream_url(asset: dict[str, Any]) -> dict[str, Any]:
    payload = dict(asset or {})
    if not STREAM_PROXY_ENABLED:
        payload.pop("stream_url", None)
        return payload
    asset_id = payload.get("id")
    if isinstance(asset_id, int) and asset_id > 0:
        payload["stream_url"] = f"/api/voice/audio/{asset_id}"
    return payload


async def _await_terminal_task_event(
    task_id: str,
    *,
    timeout_seconds: int,
) -> tuple[str, dict[str, Any]]:
    deadline = time.monotonic() + timeout_seconds
    last_id = "0-0"

    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("voice_turn_timeout")

        block_ms = max(100, min(15_000, int(remaining * 1000)))
        events = await asyncio.to_thread(
            task_events.read_events,
            task_id,
            last_id,
            block_ms=block_ms,
            count=100,
        )
        if not events:
            continue

        for event_id, event in events:
            last_id = event_id
            event_type = str(event.get("type") or "")
            if event_type in {
                "task.completed",
                "task.failed",
                "task.cancelled",
            }:
                return event_type, (event.get("data") or {})


@router.get("/capabilities")
def voice_capabilities(
    response: Response,
    api_key: str = Depends(require_api_key),
):
    cfg = get_voice_runtime_config()
    response.headers["Cache-Control"] = "private, max-age=30"

    routes_enabled = bool(cfg.routes_enabled)
    turns_config_enabled = bool(cfg.turns_enabled)
    tts_configured = _configured_provider(
        cfg.tts_provider,
        supported=SUPPORTED_TTS_PROVIDERS,
        local_voice_base_url=cfg.local_voice_base_url,
    )
    stt_configured = _configured_provider(
        cfg.stt_provider,
        supported=SUPPORTED_STT_PROVIDERS,
        local_voice_base_url=cfg.local_voice_base_url,
    )
    worker_present = _voice_worker_available()

    read_aloud_enabled = bool(routes_enabled and tts_configured)
    turn_based_enabled = bool(
        routes_enabled
        and turns_config_enabled
        and stt_configured
        and worker_present
    )

    read_aloud_reason = None
    if not read_aloud_enabled:
        if not routes_enabled:
            read_aloud_reason = "routes_disabled"
        elif not cfg.tts_provider:
            read_aloud_reason = "provider_missing"
        elif not tts_configured:
            read_aloud_reason = "misconfigured"
        else:
            read_aloud_reason = "unknown"

    turn_based_reason = None
    if not turn_based_enabled:
        if not routes_enabled:
            turn_based_reason = "routes_disabled"
        elif not turns_config_enabled:
            turn_based_reason = "feature_gated"
        elif not stt_configured:
            turn_based_reason = "misconfigured"
        elif not worker_present:
            turn_based_reason = "worker_missing"
        else:
            turn_based_reason = "unknown"

    return {
        "read_aloud_enabled": read_aloud_enabled,
        "turn_based_enabled": turn_based_enabled,
        "read_aloud_reason": read_aloud_reason,
        "turn_based_reason": turn_based_reason,
        "voice_routes_enabled": routes_enabled,
        "voice_turns_enabled": turns_config_enabled,
        "stream_proxy_enabled": bool(STREAM_PROXY_ENABLED),
        "provider_default": cfg.tts_provider,
        "voice_default": (
            os.getenv("CODEXIFY_DEFAULT_VOICE") or "alloy"
        ).strip(),
        "providers_supported": {
            "tts": list(SUPPORTED_TTS_PROVIDERS),
            "stt": list(SUPPORTED_STT_PROVIDERS),
        },
        "providers_configured": {
            "tts": tts_configured,
            "stt": stt_configured,
        },
        "supported_input_mime": list(SUPPORTED_INPUT_MIME),
        "limits": {
            "max_upload_bytes": cfg.input_max_bytes,
            "max_duration_s": cfg.max_duration_seconds,
        },
    }


@router.get("/audio/{asset_id}")
def stream_audio_asset(
    asset_id: int,
    api_key: str = Depends(require_api_key),
):
    if not STREAM_PROXY_ENABLED:
        raise HTTPException(status_code=404, detail="route_not_found")
    asset = _load_audio_asset(asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="audio_asset_not_found")

    try:
        raw = _storage.download_file(asset.src_url)
    except Exception:
        raise HTTPException(status_code=404, detail="audio_asset_not_found")

    media_type = _content_type_for_format(asset.internal_format)
    return Response(content=raw, media_type=media_type)


@router.post("/turn")
async def voice_turn(
    thread_id: int = Form(...),
    audio_file: UploadFile = File(...),
    turn_id: str | None = Form(None),
    stt_provider: str | None = Form(None),
    tts_enabled: bool = Form(True),
    tts_provider: str | None = Form(None),
    voice: str | None = Form(None),
    output_format: str | None = Form(None),
    completion_provider: str | None = Form(None),
    completion_model: str | None = Form(None),
    depth_mode: str | None = Form(None),
    system_override: str | None = Form(None),
    max_context: int | None = Form(None),
    api_key: str = Depends(require_api_key),
):
    cfg = get_voice_runtime_config()

    # 1) Feature gate
    if not cfg.turns_enabled:
        raise HTTPException(status_code=403, detail="voice_turns_disabled")

    # 2) Worker heartbeat gate
    if not _voice_worker_available():
        raise HTTPException(status_code=503, detail="voice_worker_missing")

    if not chatlog_db or not hasattr(chatlog_db, "get_chat_thread"):
        raise HTTPException(status_code=503, detail="chat_db_unavailable")
    thread = chatlog_db.get_chat_thread(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="thread_not_found")

    voice_turn_task_cls = _get_voice_turn_task_cls()
    if voice_turn_task_cls is None:
        raise HTTPException(
            status_code=503, detail="voice_turn_task_unavailable"
        )

    audio_raw = await audio_file.read()

    # 3) MIME + limits + normalization
    try:
        normalized_audio, normalized_mime, audio_meta = normalize_audio_input(
            audio_raw,
            audio_file.content_type,
            cfg=cfg,
        )
    except VoiceValidationError as exc:
        detail = str(exc)
        if detail.startswith("payload_too_large:"):
            raise HTTPException(status_code=413, detail="payload_too_large")
        if detail.startswith("duration_exceeded:"):
            raise HTTPException(status_code=400, detail="duration_exceeded")
        if detail.startswith("invalid_mime:"):
            raise HTTPException(status_code=400, detail=detail)
        if detail == "normalization_failed":
            raise HTTPException(status_code=400, detail="normalization_failed")
        raise HTTPException(status_code=400, detail=detail)

    normalized_turn_id = _normalize_turn_id(turn_id)
    audio_sha256 = hashlib.sha256(audio_raw).hexdigest()

    # 4) Dedupe before lock/enqueue
    dedupe_hit = _get_dedupe_hit(
        thread_id=thread_id,
        turn_id=normalized_turn_id,
        audio_sha256=audio_sha256,
    )
    if dedupe_hit:
        return dedupe_hit

    task = voice_turn_task_cls(
        thread_id=thread_id,
        audio_b64=base64.b64encode(normalized_audio).decode("ascii"),
        audio_mime=normalized_mime,
        stt_provider=stt_provider,
        tts_enabled=bool(tts_enabled),
        tts_provider=tts_provider,
        voice=voice,
        output_format=output_format,
        completion_provider=completion_provider,
        completion_model=completion_model,
        max_context=max_context,
        depth_mode=depth_mode,
        system_override=system_override,
        turn_id=normalized_turn_id,
        origin=f"api:voice.turn|turn_id={normalized_turn_id}",
    )
    task.turn_lock_owner = task.task_id

    # 5) Acquire lock
    try:
        locked = acquire_turn_lock(thread_id, task.turn_lock_owner)
    except Exception as exc:
        logger.warning("[voice.turn] turn lock unavailable: %s", exc)
        raise HTTPException(status_code=503, detail="turn_lock_unavailable")
    if not locked:
        raise HTTPException(status_code=429, detail="turn_in_flight")

    # 6) Enqueue
    try:
        enqueue(task, VOICE_QUEUE_NAME)
    except Exception as exc:
        logger.warning("[voice.turn] queue unavailable: %s", exc)
        try:
            release_turn_lock(thread_id, task.turn_lock_owner)
        except Exception:
            logger.debug(
                "[voice.turn] failed releasing lock after queue error",
                exc_info=True,
            )
        raise HTTPException(status_code=503, detail="queue_unavailable")

    _set_dedupe_record(
        thread_id=thread_id,
        turn_id=normalized_turn_id,
        audio_sha256=audio_sha256,
        task_id=task.task_id,
        ttl_seconds=cfg.turn_dedupe_ttl_seconds,
    )

    try:
        task_events.publish(
            task.task_id,
            "task.created",
            {
                "type": task.type,
                "thread_id": thread_id,
                "origin": task.origin,
                "turn_id": normalized_turn_id,
                "lock": turn_lock_key(thread_id),
                "duration_seconds": audio_meta.get("duration_seconds"),
                "sample_rate_hz": audio_meta.get("sample_rate_hz"),
                "channels": audio_meta.get("channels"),
                "size_bytes": audio_meta.get("size_bytes"),
            },
        )
    except Exception:
        logger.debug("[voice.turn] task.created emit failed", exc_info=True)

    wait_budget = (
        cfg.stt_timeout_seconds
        + cfg.completion_timeout_seconds
        + (cfg.tts_timeout_seconds if tts_enabled else 0)
        + 10
    )

    try:
        event_type, payload = await _await_terminal_task_event(
            task.task_id,
            timeout_seconds=wait_budget,
        )
    except TimeoutError:
        raise HTTPException(status_code=504, detail="voice_turn_timeout")

    if event_type == "task.completed":
        payload.setdefault("task_id", task.task_id)
        payload.setdefault("thread_id", thread_id)
        payload.setdefault("status", "succeeded")
        payload.setdefault("deduped", False)
        return payload

    if event_type == "task.cancelled":
        raise HTTPException(status_code=409, detail="voice_turn_cancelled")

    error = str(payload.get("error") or "voice_turn_failed")
    if error.startswith("voice_validation:invalid_mime:"):
        raise HTTPException(
            status_code=400,
            detail=error.removeprefix("voice_validation:"),
        )
    if error.startswith("voice_validation:payload_too_large"):
        raise HTTPException(status_code=413, detail="payload_too_large")
    if error.startswith("voice_validation:duration_exceeded"):
        raise HTTPException(status_code=400, detail="duration_exceeded")
    if error.startswith("voice_validation:normalization_failed"):
        raise HTTPException(status_code=400, detail="normalization_failed")
    if error.endswith("_timeout"):
        raise HTTPException(status_code=504, detail=error)
    raise HTTPException(status_code=500, detail=error)


@router.post("/messages/{message_id}/speak", response_model=SpeakResponse)
def speak_message(
    message_id: int,
    request: SpeakRequest,
    api_key: str = Depends(require_api_key),
):
    row = _load_message(message_id)
    if not row:
        raise HTTPException(status_code=404, detail="message_not_found")

    text = str(row.content or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="message_content_empty")

    cfg = get_voice_runtime_config()
    provider = (request.provider or cfg.tts_provider or "").strip().lower()
    voice = (
        request.voice or os.getenv("CODEXIFY_DEFAULT_VOICE") or "alloy"
    ).strip()
    output_format = (
        (request.output_format or cfg.internal_format or "wav").strip().lower()
    )

    text_hash = compute_text_hash(text)
    if not request.force_regenerate:
        cached = find_cached_asset(
            message_id=message_id,
            provider=provider,
            voice=voice,
            text_hash=text_hash,
        )
        if cached:
            return SpeakResponse(
                message_id=message_id,
                audio_asset=_with_stream_url(cached),
                cached=True,
                text_hash=text_hash,
            )

    try:
        audio_bytes, fmt = synthesize(
            text,
            provider=provider,
            voice=voice,
            output_format=output_format,
            timeout_seconds=cfg.tts_timeout_seconds,
        )
    except VoiceValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"tts_failed:{exc}")

    asset = save_message_audio_asset(
        message_id=message_id,
        text=text,
        provider=provider,
        voice=voice,
        audio_bytes=audio_bytes,
        audio_format=fmt,
        delivery_variants_json={
            "requested_format": output_format,
            "stream_proxy_enabled": bool(STREAM_PROXY_ENABLED),
        },
    )
    return SpeakResponse(
        message_id=message_id,
        audio_asset=_with_stream_url(asset),
        cached=False,
        text_hash=text_hash,
    )
