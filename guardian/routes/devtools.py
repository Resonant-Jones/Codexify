"""
Devtools Routes
~~~~~~~~~~~~~~~

Development and debugging endpoints for inspecting system state.
These endpoints are intended for local development and debugging only.
"""

import json
import logging
import os

from fastapi import APIRouter

from guardian.agent_task_queue import enqueue_agent_task, get_task_status
from guardian.plugins.plugin_loader import load_all_manifests
from guardian.queue.redis_queue import get_redis_client
from guardian.tools.state_inspector import get_codexify_state

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dev", tags=["Devtools"])
RESULT_STORE = os.environ.get("AGENT_RESULT_STORE", "codexify:agent_results")


@router.get("/state/{thread_id}")
def get_dev_state(thread_id: str):
    """
    Get the current state of a thread for debugging purposes.

    Performs a full health check across MVP-critical surfaces:
    - Thread existence and message count
    - Persona attachment status
    - Context bundle readiness
    - Linked documents and images
    - Agent target readiness

    Args:
        thread_id: The thread identifier to inspect

    Returns:
        Structured state report as JSON
    """
    logger.info(
        "[devtools] state inspection requested for thread=%s", thread_id
    )
    return get_codexify_state(thread_id)


@router.get("/plugins")
def list_plugins():
    """
    List all registered plugins.

    Scans the plugins directory for manifest.json files and returns
    the parsed plugin manifests.

    Returns:
        List of plugin manifest dictionaries
    """
    logger.info("[devtools] plugin list requested")
    return [manifest.model_dump() for manifest in load_all_manifests()]


@router.post("/delegate")
def delegate_agent_task(agent: str, prompt: str, thread_id: str):
    """
    Delegate a task to an agent for background execution.

    Enqueues a task for the specified agent (codex or claude) to process
    asynchronously. The task will be picked up by the agent worker.

    Args:
        agent: Target agent ("codex" or "claude")
        prompt: The prompt to send to the agent
        thread_id: The thread ID for context

    Returns:
        task_id: Unique identifier for tracking the task
    """
    logger.info(
        "[devtools] delegate requested agent=%s thread=%s", agent, thread_id
    )
    task_id = enqueue_agent_task(agent, prompt, thread_id)  # type: ignore[arg-type]
    return {"task_id": task_id}


@router.get("/task/{task_id}/status")
def get_delegate_task_status(task_id: str):
    """
    Get the status of a delegated task.

    Args:
        task_id: The task identifier

    Returns:
        Status information for the task
    """
    status = get_task_status(task_id)
    return {"task_id": task_id, "status": status or "unknown"}


@router.get("/results/{task_id}")
def get_task_result(task_id: str):
    """
    Get the result of a delegated task from the result store.

    Args:
        task_id: The task identifier

    Returns:
        Result payload if available, otherwise pending status
    """
    client = get_redis_client()
    raw = client.hget(RESULT_STORE, task_id)
    if not raw:
        return {"status": "pending"}
    return json.loads(raw)
