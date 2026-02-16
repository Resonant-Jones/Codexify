"""Chat embedding worker for queued chat embed tasks."""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone
from typing import Any

from redis.exceptions import TimeoutError as RedisTimeoutError

from guardian.queue.redis_queue import dequeue_chat_embed
from guardian.vector.store import VectorStore

logger = logging.getLogger(__name__)

QUEUE_NAME = os.getenv("CHAT_EMBED_QUEUE_NAME", "codexify:queue:chat-embed")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def process_chat_embed_task(
    payload: dict[str, Any] | None,
    *,
    vector_store: VectorStore | None = None,
) -> bool:
    if not payload or not isinstance(payload, dict):
        logger.warning("[chat-embed] invalid payload=%r", payload)
        return False

    content = payload.get("content")
    if not isinstance(content, str) or not content.strip():
        logger.warning("[chat-embed] missing content payload=%r", payload)
        return False

    meta = {
        "thread_id": payload.get("thread_id"),
        "role": payload.get("role"),
        "message_id": payload.get("message_id"),
        "timestamp": _utc_now_iso(),
        "source": "chat",
    }

    store = vector_store or VectorStore()
    try:
        store.add_texts([{"text": content, "meta": meta}])
        logger.info(
            "[chat-embed] embedded message_id=%s thread_id=%s",
            payload.get("message_id"),
            payload.get("thread_id"),
        )
        return True
    except Exception as exc:
        logger.warning("[chat-embed] embedding failed err=%s", exc)
        return False


def run_forever() -> None:
    logger.info("[chat-embed] worker started queue=%s", QUEUE_NAME)
    while True:
        try:
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
        process_chat_embed_task(payload)


if __name__ == "__main__":
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    run_forever()
