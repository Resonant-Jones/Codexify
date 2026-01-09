"""
Guardian Loop Controller
~~~~~~~~~~~~~~~~~~~~~~~~

Scaffolds a Guardian loop pass that inspects state, proposes repair tasks,
optionally enqueues them, and logs actions for later audit integration.
"""

from typing import Optional

from guardian.agent_task_queue import enqueue_agent_task
from guardian.tools.state_inspector import get_codexify_state


def log_guardian_event(
    *, thread_id: str, prompt: str, result: str, reason: str
) -> None:
    # TODO: Store to event graph or audit trail
    print(f"[LOG] Guardian reason: {reason} -> {prompt} ({result})")


def guardian_loop(thread_id: str, autonomy: str = "propose_only") -> dict:
    """
    Run Guardian loop pass against a thread.

    autonomy: "propose_only" | "auto" (default: propose_only)
    """
    state = get_codexify_state(thread_id)
    proposed_tasks = []

    if state["thread_exists"] and state["messages_loaded"] == 0:
        proposed_tasks.append(
            {
                "agent": "codex",
                "prompt": "Summarize thread context and propose opening message.",
                "reason": "Thread exists but has no messages.",
            }
        )

    if (
        state["documents_linked"] > 0
        and not state["context_bundle"]["vector_context_ready"]
    ):
        proposed_tasks.append(
            {
                "agent": "codex",
                "prompt": "Index all linked documents for thread use.",
                "reason": "Documents exist but vector context is missing.",
            }
        )

    results = []
    for task in proposed_tasks:
        task_id: Optional[str] = None
        if autonomy == "auto":
            task_id = enqueue_agent_task(
                task["agent"], task["prompt"], thread_id
            )

        status = "proposed" if not task_id else "enqueued"
        results.append(
            {
                "status": status,
                "task_id": task_id,
                "reason": task["reason"],
                "prompt": task["prompt"],
            }
        )
        log_guardian_event(
            thread_id=thread_id,
            prompt=task["prompt"],
            result=status,
            reason=task["reason"],
        )

    return {"thread_id": thread_id, "autonomy": autonomy, "results": results}
