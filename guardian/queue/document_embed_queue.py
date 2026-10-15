"""Queue helpers for document embedding tasks."""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any

from guardian.queue.redis_queue import dequeue, enqueue

QUEUE_NAME = os.getenv(
    "DOCUMENT_EMBED_QUEUE_NAME", "codexify:queue:document-embed"
)
TASK_TYPE = "document_embed"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def enqueue_document_embed(
    doc_id: str,
    *,
    origin: str,
    metadata: dict[str, Any] | None = None,
) -> str:
    task_id = str(uuid.uuid4())
    payload = {
        "task_id": task_id,
        "type": TASK_TYPE,
        "origin": origin,
        "doc_id": doc_id,
        "created_at": _utc_now_iso(),
        "metadata": metadata or {},
    }
    enqueue(payload, QUEUE_NAME)
    return task_id


def dequeue_document_embed(
    *, block: bool = True, timeout: int | None = None
) -> dict[str, Any] | None:
    return dequeue(QUEUE_NAME, block=block, timeout=timeout)
