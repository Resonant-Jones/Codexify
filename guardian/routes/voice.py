"""Voice turn + message read-aloud routes."""

from __future__ import annotations

import asyncio
import base64
import logging
import time
from typing import Any, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from guardian.core.db import load_guardian_db_from_env
from guardian.core.dependencies import chatlog_db, require_api_key
from guardian.db.models import ChatMessage
from guardian.queue import task_events
from guardian.queue.redis_queue import enqueue
from guardian.queue.turn_lock import acquire_turn_lock, turn_lock_key
from guardian.tasks.types import VoiceTurnTask
from guardian.voice.audio_assets import (
    compute_text_hash,
    find_cached_asset,
    save_message_audio_asset,
)
from guardian.voice.client import synthesize
from guardian.voice.config import get_voice_runtime_config
from guardian.voice.service import (
    VoiceValidationError,
    enforce_audio_input_limits,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/voice", tags=["Voice"])

VOICE_QUEUE_NAME = os.getenv("VOICE_QUEUE_NAME", "codexify:queue:voice")


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


def _load_message(message_id: int) -> ChatMessage | None:
    db = chatlog_db or load_guardian_db_from_env()
    if not db or not hasattr(db, "get_session"):
        return None
    with db.get_session() as session:
        row = session.query(ChatMessage).filter_by(id=message_id).first()
        return row


@router.post("/turn")
async def voice_turn(
    thread_id: int = Form(...),
    audio_file: UploadFile = File(...),
    stt_provider: str | None = Form(None),
    tts_enabled: bool = Form(True),
    tts_provider: str | None = Form(None),
    voice: str | None = Form(None),
    output_format: str | None = Form(None),
    completion_provider: str | None = Form(None),
    completion_model: str | None = Form(None),
    depth_mode: str | None = Form(None),
    system_override: str | None = Form(None),
    api_key: str = Depends(require_api_key),
):
    if not chatlog_db or not hasattr(chatlog_db, "get_chat_thread"):
        raise HTTPException(status_code=503, detail="chat_db_unavailable")

    thread = chatlog_db.get_chat_thread(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="thread_not_found")

    audio_bytes = await audio_file.read()
    cfg = get_voice_runtime_config()
    try:
        duration = enforce_audio_input_limits(
            audio_bytes,
            audio_file.content_type,
            cfg=cfg,
        )
    except VoiceValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    task = VoiceTurnTask(
        thread_id=thread_id,
        audio_b64=base64.b64encode(audio_bytes).decode("ascii"),
        audio_mime=audio_file.content_type,
        stt_provider=stt_provider,
        tts_enabled=bool(tts_enabled),
        tts_provider=tts_provider,
        voice=voice,
        output_format=output_format,
        completion_provider=completion_provider,
        completion_model=completion_model,
        depth_mode=depth_mode,
        system_override=system_override,
        origin="api:voice.turn",
    )
    task.turn_lock_owner = task.task_id

    try:
        locked = acquire_turn_lock(thread_id, task.turn_lock_owner)
    except Exception as exc:
        logger.warning("[voice.turn] turn lock unavailable: %s", exc)
        raise HTTPException(status_code=503, detail="turn_lock_unavailable")

    if not locked:
        raise HTTPException(status_code=429, detail="turn_in_flight")

    try:
        enqueue(task, VOICE_QUEUE_NAME)
    except Exception as exc:
        logger.warning("[voice.turn] queue unavailable: %s", exc)
        # Lock owner is task_id; lock TTL is short and worker never received task.
        # To avoid stale lock on queue failure we release immediately.
        try:
            from guardian.queue.turn_lock import release_turn_lock

            release_turn_lock(thread_id, task.turn_lock_owner)
        except Exception:
            logger.debug(
                "[voice.turn] failed releasing lock after queue error",
                exc_info=True,
            )
        raise HTTPException(status_code=503, detail="queue_unavailable")

    try:
        task_events.publish(
            task.task_id,
            "task.created",
            {
                "type": task.type,
                "thread_id": thread_id,
                "origin": task.origin,
                "lock": turn_lock_key(thread_id),
                "duration_seconds": duration,
            },
        )
    except Exception:
        logger.debug("[voice.turn] task.created emit failed", exc_info=True)

    # Route waits for terminal event while worker executes internally.
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
        return payload

    if event_type == "task.cancelled":
        raise HTTPException(status_code=409, detail="voice_turn_cancelled")

    error = str(payload.get("error") or "voice_turn_failed")
    if error.startswith("voice_validation:"):
        raise HTTPException(status_code=400, detail=error)
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
                audio_asset=cached,
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
        delivery_variants_json={"requested_format": output_format},
    )
    return SpeakResponse(
        message_id=message_id,
        audio_asset=asset,
        cached=False,
        text_hash=text_hash,
    )
