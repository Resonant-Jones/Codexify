"""Voice turn worker.

Executes STT -> shared completion -> optional TTS, then emits terminal task event.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError

from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError

from guardian.core import dependencies, event_bus
from guardian.core.chat_completion_service import (
    ChatTaskCancelled,
    run_chat_completion_task,
)
from guardian.queue import task_events
from guardian.queue.redis_queue import (
    clear_cancelled,
    dequeue,
    get_redis_client,
    is_cancelled,
)
from guardian.queue.turn_lock import release_turn_lock
from guardian.tasks.types import (
    ChatCompletionTask,
    VoiceTurnTask,
    task_from_dict,
)
from guardian.voice.audio_assets import save_message_audio_asset
from guardian.voice.client import synthesize, transcribe
from guardian.voice.config import get_voice_runtime_config
from guardian.voice.runtime import (
    VOICE_HEARTBEAT_INTERVAL_SECONDS,
    VOICE_HEARTBEAT_KEY,
    VOICE_HEARTBEAT_TTL_SECONDS,
    VOICE_QUEUE_NAME,
)
from guardian.voice.service import VoiceTimeoutError, VoiceValidationError

logger = logging.getLogger(__name__)

QUEUE_NAME = VOICE_QUEUE_NAME
CONCURRENCY = int(os.getenv("VOICE_WORKER_CONCURRENCY", "1"))


def _safe_publish(task_id: str, event_type: str, data: dict) -> None:
    try:
        task_events.publish(task_id, event_type, data)
    except Exception as exc:
        logger.warning("[voice-worker] failed to publish event: %s", exc)


def _publish_worker_heartbeat(status: str = "idle") -> None:
    payload = {
        "worker": "voice",
        "status": status,
        "queue": QUEUE_NAME,
        "ts": int(time.time()),
    }
    try:
        client = get_redis_client()
        client.setex(
            VOICE_HEARTBEAT_KEY,
            max(5, VOICE_HEARTBEAT_TTL_SECONDS),
            json.dumps(payload),
        )
    except Exception as exc:
        logger.debug("[voice-worker] heartbeat update failed: %s", exc)


def _run_voice_task(task: VoiceTurnTask) -> None:
    cfg = get_voice_runtime_config()
    _safe_publish(
        task.task_id,
        "task.running",
        {"type": task.type, "thread_id": task.thread_id, "origin": task.origin},
    )

    try:
        if is_cancelled(task.task_id):
            _safe_publish(
                task.task_id,
                "task.cancelled",
                {"thread_id": task.thread_id},
            )
            clear_cancelled(task.task_id)
            return

        try:
            audio_bytes = base64.b64decode(task.audio_b64)
        except Exception as exc:
            raise VoiceValidationError(f"invalid_audio_payload:{exc}") from exc

        _safe_publish(
            task.task_id,
            "task.progress",
            {"stage": "stt.start", "thread_id": task.thread_id},
        )
        transcript = transcribe(
            audio_bytes,
            task.audio_mime,
            provider=task.stt_provider,
            timeout_seconds=cfg.stt_timeout_seconds,
        )

        user_message_id = dependencies.chatlog_db.create_message(
            task.thread_id,
            "user",
            transcript,
        )
        try:
            dependencies.chatlog_db.write_audit_log(
                "create",
                "chat_message",
                str(user_message_id),
                user_id="default",
            )
        except Exception:
            pass

        try:
            event_bus.emit_event(
                "message.created",
                {
                    "thread_id": task.thread_id,
                    "message_id": user_message_id,
                    "role": "user",
                    "content": transcript,
                },
            )
        except Exception:
            logger.debug("[voice-worker] emit user message.created failed")

        _safe_publish(
            task.task_id,
            "task.progress",
            {
                "stage": "completion.start",
                "thread_id": task.thread_id,
                "transcript": transcript,
                "user_message_id": user_message_id,
            },
        )

        completion_origin = "worker:voice_turn"
        if task.turn_id:
            completion_origin = f"{completion_origin}|turn_id={task.turn_id}"
        completion_task = ChatCompletionTask(
            user_id="local",
            thread_id=task.thread_id,
            provider=task.completion_provider,
            model=task.completion_model,
            max_context=task.max_context,
            depth_mode=task.depth_mode,
            system_override=task.system_override,
            origin=completion_origin,
        )
        if task.turn_id:
            completion_task.turn_id = task.turn_id

        try:
            from guardian.core.config import settings as llm_settings

            llm_settings.LLM_REQUEST_TIMEOUT_SECONDS = (
                cfg.completion_timeout_seconds
            )
        except Exception:
            pass

        with ThreadPoolExecutor(max_workers=1) as completion_pool:
            completion_future = completion_pool.submit(
                run_chat_completion_task,
                completion_task,
                user_id=completion_task.user_id,
                token_callback=lambda token: _safe_publish(
                    task.task_id,
                    "task.progress",
                    {
                        "stage": "completion.token",
                        "thread_id": task.thread_id,
                        "token": token,
                    },
                ),
                cancel_check=lambda: is_cancelled(task.task_id),
                persist_assistant_message=True,
            )
            try:
                completion_result = completion_future.result(
                    timeout=cfg.completion_timeout_seconds
                )
            except FutureTimeoutError as exc:
                completion_future.cancel()
                raise VoiceTimeoutError("completion_timeout") from exc

        assistant_message_id = int(completion_result.get("message_id") or 0)
        assistant_text = str(completion_result.get("assistant_text") or "")

        audio_asset = None
        if task.tts_enabled and assistant_text.strip():
            _safe_publish(
                task.task_id,
                "task.progress",
                {"stage": "tts.start", "thread_id": task.thread_id},
            )
            audio_bytes, fmt = synthesize(
                assistant_text,
                provider=task.tts_provider,
                voice=task.voice,
                output_format=task.output_format,
                timeout_seconds=cfg.tts_timeout_seconds,
            )
            audio_asset = save_message_audio_asset(
                message_id=assistant_message_id,
                text=assistant_text,
                provider=(task.tts_provider or cfg.tts_provider or "")
                .strip()
                .lower(),
                voice=(
                    task.voice or os.getenv("CODEXIFY_DEFAULT_VOICE") or "alloy"
                ).strip(),
                audio_bytes=audio_bytes,
                audio_format=fmt,
                delivery_variants_json={
                    "requested_format": task.output_format,
                    "source": "voice_turn",
                },
            )

        _safe_publish(
            task.task_id,
            "task.completed",
            {
                "status": "succeeded",
                "task_id": task.task_id,
                "thread_id": task.thread_id,
                "transcript": transcript,
                "user_message_id": user_message_id,
                "assistant_message_id": assistant_message_id,
                "assistant_text": assistant_text,
                "audio_asset": audio_asset,
                "timings": {
                    "stt_timeout_seconds": cfg.stt_timeout_seconds,
                    "completion_timeout_seconds": cfg.completion_timeout_seconds,
                    "tts_timeout_seconds": cfg.tts_timeout_seconds,
                },
            },
        )
    except ChatTaskCancelled:
        _safe_publish(
            task.task_id,
            "task.cancelled",
            {"thread_id": task.thread_id},
        )
        clear_cancelled(task.task_id)
    except VoiceTimeoutError as exc:
        _safe_publish(
            task.task_id,
            "task.failed",
            {"thread_id": task.thread_id, "error": str(exc)},
        )
    except VoiceValidationError as exc:
        _safe_publish(
            task.task_id,
            "task.failed",
            {
                "thread_id": task.thread_id,
                "error": f"voice_validation:{exc}",
            },
        )
    except Exception as exc:
        _safe_publish(
            task.task_id,
            "task.failed",
            {"thread_id": task.thread_id, "error": str(exc)},
        )
        logger.exception(
            "[voice-worker] task failed id=%s thread=%s err=%s",
            task.task_id,
            task.thread_id,
            exc,
        )
    finally:
        owner = (task.turn_lock_owner or "").strip()
        if owner:
            try:
                release_turn_lock(task.thread_id, owner)
            except Exception as exc:
                logger.warning(
                    "[voice-worker] failed releasing turn lock thread=%s owner=%s err=%s",
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
            "[voice-worker] outbox disabled; falling back to in-memory: %s",
            exc,
        )


def run_forever() -> None:
    _initialize_worker()
    _publish_worker_heartbeat("starting")
    logger.info(
        "[voice-worker] started queue=%s concurrency=%s",
        QUEUE_NAME,
        CONCURRENCY,
    )
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        last_heartbeat = 0.0
        while True:
            now = time.time()
            if now - last_heartbeat >= max(1, VOICE_HEARTBEAT_INTERVAL_SECONDS):
                _publish_worker_heartbeat("idle")
                last_heartbeat = now

            try:
                payload = dequeue(QUEUE_NAME, block=True, timeout=5)
            except RedisTimeoutError:
                continue
            except RedisConnectionError as exc:
                logger.warning(
                    "[voice-worker] dequeue error; continuing: %s", exc
                )
                time.sleep(1.0)
                continue

            if not payload:
                continue

            _publish_worker_heartbeat("active")
            last_heartbeat = time.time()

            try:
                task = task_from_dict(payload)
            except Exception as exc:
                logger.warning("[voice-worker] invalid task payload: %s", exc)
                continue

            if not isinstance(task, VoiceTurnTask):
                logger.warning(
                    "[voice-worker] skipping non-voice task type=%s id=%s",
                    task.type,
                    task.task_id,
                )
                continue

            if is_cancelled(task.task_id):
                _safe_publish(
                    task.task_id,
                    "task.cancelled",
                    {"type": task.type, "origin": task.origin},
                )
                clear_cancelled(task.task_id)
                continue

            executor.submit(_run_voice_task, task)


if __name__ == "__main__":
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    run_forever()
