"""
Agent Task Queue
~~~~~~~~~~~~~~~~

Redis-backed task queue for delegating prompts to agent backends
(Codex, Claude, etc.) after user confirmation. This decouples
conversational confirmation from long-running agent execution.
"""

import json
import logging
import os
import uuid
from typing import Any, Dict, Literal, Optional

from guardian.queue.redis_queue import dequeue, enqueue, get_redis_client

logger = logging.getLogger(__name__)

AGENT_TASK_QUEUE = os.environ.get("AGENT_TASK_QUEUE", "codexify:agent_tasks")
AGENT_TASK_STATUS_PREFIX = "codexify:agent_task_status:"
RESULT_STORE = os.environ.get("AGENT_RESULT_STORE", "codexify:agent_results")


def enqueue_agent_task(
    agent: Literal["codex", "claude"],
    prompt: str,
    thread_id: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Enqueue an agent task for background execution.

    Args:
        agent: Target agent ("codex" or "claude")
        prompt: The prompt to send to the agent
        thread_id: The thread ID for context
        metadata: Optional additional metadata

    Returns:
        task_id: Unique identifier for the queued task
    """
    task_id = str(uuid.uuid4())
    payload = {
        "task_id": task_id,
        "agent": agent,
        "prompt": prompt,
        "thread_id": thread_id,
        "status": "queued",
        "metadata": metadata or {},
    }

    enqueue(payload, AGENT_TASK_QUEUE)

    # Store initial status
    _set_task_status(task_id, "queued")

    logger.info(
        "[agent_task_queue] enqueued task_id=%s agent=%s thread=%s",
        task_id,
        agent,
        thread_id,
    )
    return task_id


def dequeue_agent_task(
    *, block: bool = True, timeout: Optional[int] = None
) -> Optional[Dict[str, Any]]:
    """
    Dequeue an agent task for processing.

    Args:
        block: Whether to block waiting for a task
        timeout: Timeout in seconds (None for infinite)

    Returns:
        Task payload dict or None if no task available
    """
    return dequeue(AGENT_TASK_QUEUE, block=block, timeout=timeout)


def get_task_status(task_id: str) -> Optional[str]:
    """
    Get the current status of a task.

    Args:
        task_id: The task identifier

    Returns:
        Status string or None if not found
    """
    try:
        client = get_redis_client()
        status = client.get(f"{AGENT_TASK_STATUS_PREFIX}{task_id}")
        return status if status else None
    except Exception as e:
        logger.warning("[agent_task_queue] failed to get status for %s: %s", task_id, e)
        return None


def _set_task_status(task_id: str, status: str, ttl: int = 86400) -> None:
    """
    Set the status of a task with TTL.

    Args:
        task_id: The task identifier
        status: Status string (queued, running, completed, failed)
        ttl: Time-to-live in seconds (default 24h)
    """
    try:
        client = get_redis_client()
        client.setex(f"{AGENT_TASK_STATUS_PREFIX}{task_id}", ttl, status)
    except Exception as e:
        logger.warning("[agent_task_queue] failed to set status for %s: %s", task_id, e)


def update_task_status(task_id: str, status: str) -> None:
    """
    Update the status of a task.

    Args:
        task_id: The task identifier
        status: New status (queued, running, completed, failed)
    """
    _set_task_status(task_id, status)
    logger.debug("[agent_task_queue] task=%s status=%s", task_id, status)


def inject_result_to_thread(task_id: str) -> bool:
    """Fetch completed agent result and inject into thread as a system message."""
    client = get_redis_client()
    raw = client.hget(RESULT_STORE, task_id)
    if not raw:
        return False

    result_obj = json.loads(raw)
    thread_id = result_obj["thread_id"]
    content = result_obj["result"]

    # TODO: Replace with actual thread manager write
    print(f"[THREAD:{thread_id}] SYSTEM: {content}")
    return True
