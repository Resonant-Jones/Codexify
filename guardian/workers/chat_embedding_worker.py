"""Chat embedding worker for queued chat embed tasks."""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any

from redis.exceptions import TimeoutError as RedisTimeoutError

from guardian.config.db_defaults import DEFAULT_PG_DSN
from guardian.core.db import GuardianDB
from guardian.db.models import ChatMessage
from guardian.queue.redis_queue import (
    dequeue_chat_embed,
    dequeue_chat_import_embed,
)
from guardian.vector.store import VectorStore

logger = logging.getLogger(__name__)

QUEUE_NAME = os.getenv("CHAT_EMBED_QUEUE_NAME", "codexify:queue:chat-embed")
IMPORT_QUEUE_NAME = os.getenv(
    "CHAT_IMPORT_EMBED_QUEUE_NAME", "codexify:queue:chat-import-embed"
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _thread_namespace(thread_id: Any) -> str:
    if thread_id is None:
        return "global"
    return f"thread:{thread_id}"


def _get_db() -> GuardianDB:
    db_url = os.getenv("DATABASE_URL") or DEFAULT_PG_DSN
    return GuardianDB(db_url)


def _load_message(db: GuardianDB, message_id: str) -> dict[str, Any] | None:
    with db.get_session() as session:
        message = session.query(ChatMessage).filter_by(id=message_id).first()
        if not message:
            return None
        return {
            "id": message.id,
            "thread_id": message.thread_id,
            "role": message.role,
            "content": message.content,
            "extra_meta": dict(message.extra_meta or {}),
        }


def _update_embedding_status(
    db: GuardianDB,
    message_id: str,
    *,
    status: str,
    error: str | None,
    started_at: datetime | None,
    completed_at: datetime | None,
) -> None:
    with db.get_session() as session:
        message = session.query(ChatMessage).filter_by(id=message_id).first()
        if not message:
            return
        meta = dict(message.extra_meta or {})
        meta["embedding_status"] = status
        meta["embedding_error"] = error
        meta["embedding_started_at"] = (
            started_at.isoformat() if started_at is not None else None
        )
        meta["embedding_completed_at"] = (
            completed_at.isoformat() if completed_at is not None else None
        )
        message.extra_meta = meta
        session.commit()


def process_chat_embed_task(
    payload: dict[str, Any] | None,
    *,
    vector_store: VectorStore | None = None,
    db: GuardianDB | None = None,
) -> bool:
    if not payload or not isinstance(payload, dict):
        logger.warning("[chat-embed] invalid payload=%r", payload)
        return False

    message_id = payload.get("message_id")
    message_id_str = str(message_id).strip() if message_id is not None else ""
    if message_id_str and db is None:
        db = _get_db()
    stored_message = None
    if db is not None and message_id_str:
        stored_message = _load_message(db, message_id_str)
        if (
            stored_message
            and stored_message["extra_meta"].get("embedding_status") == "ready"
        ):
            logger.info(
                "[chat-embed] already ready message_id=%s thread_id=%s",
                message_id_str,
                stored_message.get("thread_id"),
            )
            return True

    content = payload.get("content")
    if not isinstance(content, str) or not content.strip():
        if stored_message and isinstance(stored_message.get("content"), str):
            content = stored_message["content"]
    if not isinstance(content, str) or not content.strip():
        logger.warning("[chat-embed] missing content payload=%r", payload)
        if db is not None and message_id_str:
            now = datetime.now(timezone.utc)
            _update_embedding_status(
                db,
                message_id_str,
                status="failed",
                error="content_missing",
                started_at=now,
                completed_at=now,
            )
        return False

    started_at = datetime.now(timezone.utc)
    if db is not None and message_id_str:
        _update_embedding_status(
            db,
            message_id_str,
            status="processing",
            error=None,
            started_at=started_at,
            completed_at=None,
        )

    payload_meta = payload.get("meta")
    if not isinstance(payload_meta, dict):
        payload_meta = {}
    meta = {
        "thread_id": payload.get("thread_id")
        if payload.get("thread_id") is not None
        else payload_meta.get("thread_id"),
        "namespace": _thread_namespace(
            payload.get("thread_id")
            if payload.get("thread_id") is not None
            else payload_meta.get("thread_id")
        ),
        "role": payload.get("role") or payload_meta.get("role"),
        "message_id": message_id
        if message_id is not None
        else payload_meta.get("message_id"),
        "timestamp": _utc_now_iso(),
        "source": payload.get("source") or payload_meta.get("source") or "chat",
    }
    for key, value in payload_meta.items():
        if value is None:
            continue
        if key not in meta:
            meta[key] = value
    meta["embedding_status"] = "processing"

    store = vector_store or VectorStore()
    try:
        store.add_texts([{"text": content, "meta": meta}])
        if db is not None and message_id_str:
            completed_at = datetime.now(timezone.utc)
            _update_embedding_status(
                db,
                message_id_str,
                status="ready",
                error=None,
                started_at=started_at,
                completed_at=completed_at,
            )
        logger.info(
            "[chat-embed] embedded message_id=%s thread_id=%s",
            message_id
            if message_id is not None
            else payload_meta.get("message_id"),
            payload.get("thread_id"),
        )
        return True
    except Exception as exc:
        if db is not None and message_id_str:
            completed_at = datetime.now(timezone.utc)
            _update_embedding_status(
                db,
                message_id_str,
                status="failed",
                error=str(exc) or exc.__class__.__name__,
                started_at=started_at,
                completed_at=completed_at,
            )
        logger.warning("[chat-embed] embedding failed err=%s", exc)
        return False


def run_forever() -> None:
    try:
        shared_vector_store = VectorStore()
    except Exception as exc:
        logger.error(
            "[chat-embed] %s",
            json.dumps(
                {
                    "event": "chat_embed_worker_boot_failure",
                    "queue": QUEUE_NAME,
                    "error": str(exc),
                },
                sort_keys=True,
            ),
        )
        raise SystemExit(1) from exc

    logger.info(
        "[chat-embed] worker started queue=%s import_queue=%s",
        QUEUE_NAME,
        IMPORT_QUEUE_NAME,
    )
    while True:
        try:
            payload = dequeue_chat_import_embed(block=False)
            if payload is None:
                payload = dequeue_chat_embed(block=True, timeout=5)
        except RedisTimeoutError:
            logger.debug("[chat-embed] redis idle timeout; continuing")
            continue
        except Exception as exc:
            logger.warning("[chat-embed] dequeue error; continuing: %s", exc)
            time.sleep(1.0)
            continue

        if not payload:
            continue
        process_chat_embed_task(payload, vector_store=shared_vector_store)


if __name__ == "__main__":
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    run_forever()
