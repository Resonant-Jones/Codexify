"""Chat completion worker for async tasks."""

from __future__ import annotations

import asyncio
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from redis.exceptions import TimeoutError as RedisTimeoutError

from guardian.context.broker import ContextBroker
from guardian.core import dependencies, event_bus
from guardian.core.ai_router import chat_with_ai, stream_local
from guardian.core.config import (
    LLMConfigError,
    get_settings,
    validate_llm_config,
)
from guardian.queue import task_events
from guardian.queue.redis_queue import clear_cancelled, dequeue, is_cancelled
from guardian.tasks.types import ChatCompletionTask, task_from_dict

logger = logging.getLogger(__name__)

QUEUE_NAME = os.getenv("CHAT_QUEUE_NAME", "codexify:queue:chat")
CONCURRENCY = int(os.getenv("CHAT_WORKER_CONCURRENCY", "2"))


try:  # pragma: no cover - prompts are optional in some deployments
    from codexify.system_prompt_builder import build_guardian_system_prompt
except Exception:  # pragma: no cover - optional dependency
    build_guardian_system_prompt = None


def _safe_publish(task_id: str, event_type: str, data: dict) -> None:
    try:
        task_events.publish(task_id, event_type, data)
    except Exception as exc:
        logger.warning("[chat-worker] failed to publish event: %s", exc)


def _estimate_tokens(text: str | None) -> int:
    if not text:
        return 0
    try:
        length = len(text)
    except Exception:
        return 0
    return max(1, length // 4)


def _embed_message(thread_id: int, role: str, content: str, message_id: int):
    if not dependencies._vector_store:
        return
    try:
        meta = {
            "thread_id": thread_id,
            "role": role,
            "message_id": message_id,
            "timestamp": datetime.utcnow().isoformat(),
            "source": "chat",
        }
        dependencies._vector_store.add_texts([{"text": content, "meta": meta}])
    except Exception as exc:
        logger.warning(
            "[chat-worker] failed to auto-embed message %s: %s",
            message_id,
            exc,
        )


async def _build_messages_for_llm(
    task: ChatCompletionTask,
) -> tuple[
    list[dict[str, str]], str, str, dict[str, Any], dict[str, Any] | None
]:
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
                "[chat-worker] LLM config error provider=%s detail=%s",
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
        raise ValueError("thread_has_no_usable_context")

    latest_message = ""
    for msg in reversed(items):
        if str(msg.get("role") or "").strip() == "user":
            lm = str(msg.get("content") or "").strip()
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
            "[chat-worker] context assemble failed depth=%s err=%s", depth, exc
        )
        bundle = {}

    messages_for_llm: list[dict[str, str]] = []

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
                    "[chat-worker] large system prompt user=%s project_id=%s est_tokens=%s",
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
        logger.warning("[chat-worker] failed to build system prompt: %s", exc)
        system_content = (
            "You are Guardian, a careful and honest AI assistant. "
            "Answer concisely, avoid speculation, and clearly mark any uncertainty."
        )

    messages_for_llm.append({"role": "system", "content": system_content})
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


def _run_chat_task(task: ChatCompletionTask) -> None:
    _safe_publish(
        task.task_id,
        "task.running",
        {"type": task.type, "origin": task.origin, "thread_id": task.thread_id},
    )
    logger.info(
        "[task] running type=%s id=%s origin=%s thread=%s",
        task.type,
        task.task_id,
        task.origin,
        task.thread_id,
    )

    try:
        messages_for_llm, provider, model, bundle, trace = asyncio.run(
            _build_messages_for_llm(task)
        )
    except Exception as exc:
        _safe_publish(
            task.task_id,
            "task.failed",
            {"error": str(exc), "thread_id": task.thread_id},
        )
        logger.exception(
            "[task] failed type=%s id=%s err=%s", task.type, task.task_id, exc
        )
        return

    if is_cancelled(task.task_id):
        _safe_publish(
            task.task_id,
            "task.cancelled",
            {"thread_id": task.thread_id, "origin": task.origin},
        )
        clear_cancelled(task.task_id)
        logger.info("[task] cancelled type=%s id=%s", task.type, task.task_id)
        return

    assistant_text = ""
    try:
        if provider == "local":
            token_stream = stream_local(
                messages_for_llm,
                model,
            )
            try:
                for token in token_stream:
                    if is_cancelled(task.task_id):
                        token_stream.close()
                        _safe_publish(
                            task.task_id,
                            "task.cancelled",
                            {"thread_id": task.thread_id},
                        )
                        clear_cancelled(task.task_id)
                        logger.info(
                            "[task] cancelled type=%s id=%s",
                            task.type,
                            task.task_id,
                        )
                        return
                    assistant_text += token
                    _safe_publish(
                        task.task_id,
                        "task.progress",
                        {"token": token, "thread_id": task.thread_id},
                    )
            finally:
                token_stream.close()
        else:
            assistant_text = str(
                chat_with_ai(messages_for_llm, model=model, provider=provider)
            )
            _safe_publish(
                task.task_id,
                "task.progress",
                {"token": assistant_text, "thread_id": task.thread_id},
            )
    except Exception as exc:
        _safe_publish(
            task.task_id,
            "task.failed",
            {"error": str(exc), "thread_id": task.thread_id},
        )
        logger.exception(
            "[task] failed type=%s id=%s err=%s", task.type, task.task_id, exc
        )
        return

    try:
        mid = dependencies.chatlog_db.create_message(
            task.thread_id, "assistant", assistant_text
        )
        try:
            dependencies.chatlog_db.write_audit_log(
                "create", "chat_message", str(mid), user_id="bot"
            )
        except Exception:
            pass

        try:
            event_bus.emit_event(
                "message.created",
                {
                    "thread_id": task.thread_id,
                    "message_id": mid,
                    "role": "assistant",
                },
            )
        except Exception:
            logger.debug("[chat-worker] emit message.created failed")

        _embed_message(task.thread_id, "assistant", assistant_text, mid)

        _safe_publish(
            task.task_id,
            "task.completed",
            {
                "thread_id": task.thread_id,
                "message_id": mid,
                "provider": provider,
                "model": model,
            },
        )
        logger.info(
            "[task] completed type=%s id=%s thread=%s",
            task.type,
            task.task_id,
            task.thread_id,
        )
    except Exception as exc:
        _safe_publish(
            task.task_id,
            "task.failed",
            {"error": str(exc), "thread_id": task.thread_id},
        )
        logger.exception(
            "[task] failed type=%s id=%s err=%s", task.type, task.task_id, exc
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


def run_forever() -> None:
    _initialize_worker()
    logger.info(
        "[chat-worker] started queue=%s concurrency=%s",
        QUEUE_NAME,
        CONCURRENCY,
    )
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        while True:
            try:
                payload = dequeue(QUEUE_NAME, block=True, timeout=5)
            except RedisTimeoutError:
                logger.debug("[chat-worker] redis idle timeout; continuing")
                continue

            if not payload:
                continue
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
            if is_cancelled(task.task_id):
                _safe_publish(
                    task.task_id,
                    "task.cancelled",
                    {"type": task.type, "origin": task.origin},
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
