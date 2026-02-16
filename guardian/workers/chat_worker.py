"""Chat completion worker for async tasks."""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import json
import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Iterable

from redis.exceptions import TimeoutError as RedisTimeoutError

from guardian.cognition.prompts import build_context_system_message
from guardian.context.broker import ContextBroker
from guardian.core import dependencies, event_bus
from guardian.core.ai_router import chat_with_ai, stream_local
from guardian.core.config import (
    LLMConfigError,
    get_settings,
    is_cloud_provider,
    validate_llm_config,
)
from guardian.core.db import GuardianDB
from guardian.core.message_guard import (
    EMPTY_ASSISTANT_FALLBACK,
    guard_assistant_message_content,
)
from guardian.db.models import UploadedDocument, UploadedImage
from guardian.queue import task_events
from guardian.queue.redis_queue import (
    clear_cancelled,
    dequeue,
    is_cancelled,
    release_turn_lock,
)
from guardian.tasks.types import ChatCompletionTask, task_from_dict
from guardian.utils.groq_helpers import run_groq_vision_url

logger = logging.getLogger(__name__)

QUEUE_NAME = os.getenv("CHAT_QUEUE_NAME", "codexify:queue:chat")
CONCURRENCY = int(os.getenv("CHAT_WORKER_CONCURRENCY", "2"))

_MEDIA_DB: GuardianDB | None = None
_MEDIA_MARKER_RE = re.compile(
    r"<!--\s*cfy-media:(image|document):([a-fA-F0-9-]+)\s*-->"
)


try:  # pragma: no cover - prompts are optional in some deployments
    from guardian.cognition.system_prompt_builder import (
        build_guardian_system_prompt,
    )
except Exception:  # pragma: no cover - optional dependency
    build_guardian_system_prompt = None

try:
    from guardian.cognition.system_profiles.resolver import (
        ResolvedSystemProfile,
        resolve_thread_system_profile,
    )
except Exception:  # pragma: no cover - optional dependency
    ResolvedSystemProfile = Any  # type: ignore[assignment,misc]

    def resolve_thread_system_profile(
        thread_id: int, *, chatlog_db: Any | None = None
    ):
        return None


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
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "chat",
        }
        dependencies._vector_store.add_texts([{"text": content, "meta": meta}])
    except Exception as exc:
        logger.warning(
            "[chat-worker] failed to auto-embed message %s: %s",
            message_id,
            exc,
        )


def _get_media_db() -> GuardianDB | None:
    global _MEDIA_DB
    if _MEDIA_DB is not None:
        return _MEDIA_DB
    db_url = os.getenv("DATABASE_URL") or os.getenv("GUARDIAN_DATABASE_URL")
    if not db_url:
        return None
    try:
        _MEDIA_DB = GuardianDB(db_url)
    except Exception as exc:
        logger.warning("[chat-worker] media DB unavailable: %s", exc)
        _MEDIA_DB = None
    return _MEDIA_DB


def _extract_media_markers(text: str | None) -> list[tuple[str, str]]:
    if not text:
        return []
    return [(m.group(1), m.group(2)) for m in _MEDIA_MARKER_RE.finditer(text)]


def _absolute_media_url(src_url: str | None) -> str | None:
    if not src_url:
        return None
    raw = str(src_url).strip()
    if raw.startswith("http://") or raw.startswith("https://"):
        return raw

    base = (
        os.getenv("PUBLIC_MEDIA_BASE_URL")
        or os.getenv("PUBLIC_API_BASE_URL")
        or os.getenv("GUARDIAN_API_BASE_URL")
        or os.getenv("API_BASE_URL")
        or os.getenv("BASE_URL")
        or os.getenv("PUBLIC_BASE_URL")
        or os.getenv("VITE_API_BASE_URL")
        or ""
    ).strip()

    if base.endswith("/api"):
        base = base[: -len("/api")]

    if not base:
        return raw

    base = base.rstrip("/")
    path = raw if raw.startswith("/") else f"/{raw}"
    return f"{base}{path}"


def _coerce_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _matches_scope(
    *,
    row_thread_id: Any,
    row_project_id: Any,
    thread_id: int | None,
    project_id: int | None,
) -> bool:
    row_tid = _coerce_int(row_thread_id)
    row_pid = _coerce_int(row_project_id)

    if row_tid is not None and thread_id is not None and row_tid != thread_id:
        return False
    if row_pid is not None and project_id is not None and row_pid != project_id:
        return False
    return True


def _resolve_media_items(
    markers: Iterable[tuple[str, str]],
    thread_id: int | None,
    project_id: int | None,
) -> list[dict[str, Any]]:
    db = _get_media_db()
    if not db:
        return []
    items: list[dict[str, Any]] = []
    unique = {(kind, media_id) for kind, media_id in markers if media_id}
    with db.get_session() as session:
        for kind, media_id in sorted(unique):
            if kind == "image":
                row = (
                    session.query(UploadedImage).filter_by(id=media_id).first()
                )
                if not row:
                    logger.info(
                        "[chat-worker] media marker missing kind=image id=%s",
                        media_id,
                    )
                    continue
                if not _matches_scope(
                    row_thread_id=row.thread_id,
                    row_project_id=row.project_id,
                    thread_id=thread_id,
                    project_id=project_id,
                ):
                    logger.info(
                        "[chat-worker] media marker scope mismatch kind=image id=%s",
                        media_id,
                    )
                    continue
                abs_url = _absolute_media_url(row.src_url) or ""
                if abs_url and not abs_url.startswith("http"):
                    logger.info(
                        "[chat-worker] media url not absolute kind=image id=%s src=%s",
                        media_id,
                        abs_url,
                    )
                items.append(
                    {
                        "kind": "image",
                        "id": row.id,
                        "src_url": abs_url,
                        "filename": row.filename,
                    }
                )
            elif kind == "document":
                row = (
                    session.query(UploadedDocument)
                    .filter_by(id=media_id)
                    .first()
                )
                if not row:
                    logger.info(
                        "[chat-worker] media marker missing kind=document id=%s",
                        media_id,
                    )
                    continue
                if not _matches_scope(
                    row_thread_id=row.thread_id,
                    row_project_id=row.project_id,
                    thread_id=thread_id,
                    project_id=project_id,
                ):
                    logger.info(
                        "[chat-worker] media marker scope mismatch kind=document id=%s",
                        media_id,
                    )
                    continue
                abs_url = _absolute_media_url(row.src_url) or ""
                if abs_url and not abs_url.startswith("http"):
                    logger.info(
                        "[chat-worker] media url not absolute kind=document id=%s src=%s",
                        media_id,
                        abs_url,
                    )
                items.append(
                    {
                        "kind": "document",
                        "id": row.id,
                        "src_url": abs_url,
                        "filename": row.filename,
                    }
                )
    return items


def _build_media_system_message(
    media_items: list[dict[str, Any]]
) -> str | None:
    if not media_items:
        return None
    lines = ["User uploaded media attachments:"]
    for item in media_items:
        label = item.get("filename") or item.get("id") or "attachment"
        src = item.get("src_url") or ""
        kind = item.get("kind") or "media"
        lines.append(f"- {kind}: {label} ({src})")
    return "\n".join(lines)


def _maybe_add_vision_summary(
    media_items: list[dict[str, Any]], provider: str
) -> str | None:
    if not media_items:
        return None
    if provider != "groq":
        return None
    image = next((i for i in media_items if i.get("kind") == "image"), None)
    if not image:
        return None
    src_url = image.get("src_url")
    if not isinstance(src_url, str) or not src_url.strip():
        return None
    if not src_url.startswith("http"):
        logger.info(
            "[chat-worker] groq vision skipped (non-absolute url) src=%s",
            src_url,
        )
        return None
    try:
        summary = run_groq_vision_url(src_url, "Describe this image briefly.")
    except Exception as exc:
        logger.warning("[chat-worker] groq vision failed: %s", exc)
        return None
    if not summary:
        return None
    label = image.get("filename") or image.get("id") or "image"
    return f"Vision summary for {label}: {summary}"


async def _build_messages_for_llm(
    task: ChatCompletionTask,
) -> tuple[
    list[dict[str, str]],
    str,
    str,
    dict[str, Any],
    dict[str, Any] | None,
    ResolvedSystemProfile | None,
    dict[str, Any],
]:
    settings = get_settings()
    provider = (
        (task.provider or settings.LLM_PROVIDER or dependencies.CHAT_PROVIDER)
        .strip()
        .lower()
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

    profile: ResolvedSystemProfile | None = None
    try:
        profile = resolve_thread_system_profile(
            thread_id,
            chatlog_db=dependencies.chatlog_db,
        )
    except Exception as exc:
        logger.warning(
            "[chat-worker] system profile resolve failed thread_id=%s err=%s",
            thread_id,
            exc,
        )
        profile = None

    if profile and profile.provider_override:
        provider = profile.provider_override.strip().lower()

    if is_cloud_provider(provider) and not settings.ALLOW_CLOUD_PROVIDERS:
        raise LLMConfigError(
            "Cloud providers are disabled (ALLOW_CLOUD_PROVIDERS=false). Set LLM_PROVIDER=local or enable cloud explicitly."
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

    limit = int(task.max_context or 50)
    items = dependencies.chatlog_db.list_messages(
        thread_id, limit=limit, offset=0
    )
    with contextlib.suppress(Exception):
        items = sorted(items, key=lambda m: m.get("id") or 0)

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
                profile=profile,
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

    system_sections = [system_content]
    context_message = build_context_system_message(bundle)
    if context_message:
        system_sections.append("=== CONTEXT BUNDLE ===\n" + context_message)

    media_note: str | None = None
    vision_note: str | None = None
    # Attach media references/vision summaries for any upload markers.
    try:
        markers: list[tuple[str, str]] = []
        for msg in context:
            markers.extend(_extract_media_markers(msg.get("content")))
        if markers:
            media_items = _resolve_media_items(
                markers, thread_id=thread_id, project_id=project_id_for_prompt
            )
            media_note = _build_media_system_message(media_items)
            vision_note = _maybe_add_vision_summary(media_items, provider)
    except Exception as exc:
        logger.warning("[chat-worker] media attachment parsing failed: %s", exc)

    if media_note:
        system_sections.append("=== MEDIA ATTACHMENTS ===\n" + media_note)
    if vision_note:
        system_sections.append("=== VISION SUMMARY ===\n" + vision_note)

    single_system_message = "\n\n".join(
        block.strip() for block in system_sections if block and block.strip()
    )
    messages_for_llm.append(
        {"role": "system", "content": single_system_message}
    )
    messages_for_llm.extend(context)

    model = task.model
    if not model and profile and profile.model_override:
        model = profile.model_override
    if not model and provider == "local":
        model = (
            settings.LOCAL_LLM_MODEL
            or settings.DEFAULT_LOCAL_MODEL
            or settings.LLM_MODEL
            or ""
        )
    if not model:
        model = dependencies.DEFAULT_MODEL or ""

    model_mode = (profile.mode if profile and profile.mode else None) or (
        "local" if provider == "local" else "cloud"
    )
    injection_seed = {
        "active_profile_id": (profile.active_profile_id if profile else None),
        "profile_id": profile.profile_id if profile else None,
        "provider": provider,
        "model": model,
        "depth_mode": depth,
        "system_prompt": (
            messages_for_llm[0].get("content", "")
            if messages_for_llm and messages_for_llm[0].get("role") == "system"
            else ""
        ),
    }
    injection_hash = hashlib.sha256(
        json.dumps(injection_seed, sort_keys=True, ensure_ascii=True).encode(
            "utf-8"
        )
    ).hexdigest()[:16]

    runtime_meta = {
        "injection_hash": injection_hash,
        "retrieval_mode": depth,
        "model_mode": model_mode,
    }

    return (
        messages_for_llm,
        provider,
        model,
        bundle,
        trace,
        profile,
        runtime_meta,
    )


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
        (
            messages_for_llm,
            provider,
            model,
            bundle,
            trace,
            profile,
            runtime_meta,
        ) = asyncio.run(_build_messages_for_llm(task))
        logger.info(
            "[chat-worker] runtime_meta thread=%s active_profile_id=%s injection_hash=%s retrieval_mode=%s model_mode=%s provider=%s model=%s",
            task.thread_id,
            profile.active_profile_id if profile else None,
            runtime_meta.get("injection_hash"),
            runtime_meta.get("retrieval_mode"),
            runtime_meta.get("model_mode"),
            provider,
            model,
        )
        if is_cancelled(task.task_id):
            _safe_publish(
                task.task_id,
                "task.cancelled",
                {"thread_id": task.thread_id, "origin": task.origin},
            )
            clear_cancelled(task.task_id)
            logger.info(
                "[task] cancelled type=%s id=%s", task.type, task.task_id
            )
            return

        assistant_text = ""
        try:
            if provider == "local":
                temperature_override = (
                    profile.temperature_override
                    if profile and profile.temperature_override is not None
                    else None
                )
                token_stream = stream_local(
                    messages_for_llm,
                    model,
                    temperature=temperature_override,
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
                    chat_with_ai(
                        messages_for_llm, model=model, provider=provider
                    )
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
                "[task] failed type=%s id=%s err=%s",
                task.type,
                task.task_id,
                exc,
            )
            return

        try:
            assistant_text = guard_assistant_message_content(
                "assistant",
                assistant_text,
                thread_id=task.thread_id,
                origin="chat_worker",
            )
        except ValueError:
            logger.warning(
                "[chat-worker] blank assistant content replaced thread_id=%s",
                task.thread_id,
            )
            assistant_text = EMPTY_ASSISTANT_FALLBACK

        try:
            mid = dependencies.chatlog_db.create_message(
                task.thread_id, "assistant", assistant_text
            )
            with contextlib.suppress(Exception):
                dependencies.chatlog_db.write_audit_log(
                    "create", "chat_message", str(mid), user_id="bot"
                )

            try:
                event_bus.emit_event(
                    "message.created",
                    {
                        "thread_id": task.thread_id,
                        "message_id": mid,
                        "role": "assistant",
                        "content": assistant_text,
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
                    "trace": trace or {},
                    "active_profile_id": (
                        profile.active_profile_id if profile else None
                    ),
                    "provider_override": (
                        profile.provider_override if profile else None
                    ),
                    "model_override": (
                        profile.model_override if profile else None
                    ),
                    "temperature_override": (
                        profile.temperature_override if profile else None
                    ),
                    "injection_hash": runtime_meta.get("injection_hash"),
                    "retrieval_mode": runtime_meta.get("retrieval_mode"),
                    "model_mode": runtime_meta.get("model_mode"),
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
                "[task] failed type=%s id=%s err=%s",
                task.type,
                task.task_id,
                exc,
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
    finally:
        # Always clear the per-thread turn lock on completion/cancel/failure.
        try:
            release_turn_lock(task.thread_id)
        except Exception:
            logger.debug(
                "[chat-worker] turn lock release failed thread_id=%s",
                task.thread_id,
                exc_info=True,
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
