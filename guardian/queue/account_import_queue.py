"""Dedicated Redis queue for durable OpenAI account-export imports."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from guardian.queue.redis_queue import dequeue, enqueue

QUEUE_NAME = os.getenv(
    "ACCOUNT_IMPORT_QUEUE_NAME", "codexify:queue:account-import"
)
TASK_TYPE = "openai_account_import"


def enqueue_account_import(job_id: str, *, user_id: str) -> None:
    enqueue(
        {
            "type": TASK_TYPE,
            "job_id": str(job_id),
            "user_id": str(user_id),
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
        QUEUE_NAME,
    )


def dequeue_account_import(
    *, block: bool = True, timeout: int | None = None
) -> dict[str, Any] | None:
    return dequeue(QUEUE_NAME, block=block, timeout=timeout)
