"""
Guardian Loop Controller
~~~~~~~~~~~~~~~~~~~~~~~~

Scaffolds a Guardian loop pass that inspects state, proposes repair tasks,
optionally enqueues them, and logs actions for later audit integration.
"""

import logging
import os
from typing import Any, Optional

import psycopg

from guardian.agent_task_queue import enqueue_agent_task
from guardian.core.dependencies import PG_DSN
from guardian.db.guardian_event_log import (
    log_guardian_event as log_guardian_event_db,
)
from guardian.tools.state_inspector import get_codexify_state

logger = logging.getLogger(__name__)

MAX_LOOP_DEPTH = 3


def _resolve_event_log_dsn() -> Optional[str]:
    return (
        PG_DSN
        or os.getenv("GUARDIAN_DATABASE_URL")
        or os.getenv("DATABASE_URL")
    )


def _fetch_timeline_events(thread_id: str) -> list[dict[str, Any]]:
    dsn = _resolve_event_log_dsn()
    if not dsn:
        logger.debug("[guardian_loop] timeline fetch skipped (no DB DSN)")
        return []
    try:
        with psycopg.connect(dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT ts, event_type, origin, summary, payload
                    FROM guardian_event_log
                    WHERE thread_id = %s
                    ORDER BY ts ASC
                    """,
                    (thread_id,),
                )
                rows = cur.fetchall()
        return [
            {
                "ts": row[0],
                "type": row[1],
                "origin": row[2],
                "summary": row[3],
                "payload": row[4],
            }
            for row in rows
        ]
    except Exception as exc:
        logger.warning("[guardian_loop] timeline fetch failed: %s", exc)
        return []


def _log_guardian_event(
    *,
    thread_id: str,
    event_type: str,
    summary: str,
    prompt: str,
    reason: str,
    task_id: Optional[str],
    status: str,
) -> None:
    dsn = _resolve_event_log_dsn()
    if not dsn:
        logger.debug("[guardian_loop] event log skipped (no DB DSN)")
        return

    payload = {
        "prompt": prompt,
        "reason": reason,
        "task_id": task_id,
        "status": status,
    }
    try:
        with psycopg.connect(dsn) as conn:
            log_guardian_event_db(
                conn,
                persona_tag="guardian",
                event_type=event_type,
                summary=summary,
                origin="guardian_loop",
                thread_id=thread_id,
                payload=payload,
            )
    except Exception as exc:
        logger.warning("[guardian_loop] event log failed: %s", exc)


def guardian_loop(
    thread_id: str,
    autonomy: str = "propose_only",
    depth: int = 0,
) -> dict:
    """
    Run Guardian loop pass against a thread.

    autonomy: "propose_only" | "auto" (default: propose_only)
    """
    if depth > MAX_LOOP_DEPTH:
        print(
            f"[Guardian] Max recursion depth {MAX_LOOP_DEPTH} reached. Halting loop."
        )
        return {
            "thread_id": thread_id,
            "autonomy": autonomy,
            "results": [],
            "reentered": False,
            "depth": depth,
        }

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
        event_type = "proposal" if status == "proposed" else "autonomy_decision"
        summary = (
            "Proposed guardian task"
            if status == "proposed"
            else "Enqueued guardian task"
        )
        _log_guardian_event(
            thread_id=thread_id,
            event_type=event_type,
            summary=summary,
            prompt=task["prompt"],
            reason=task["reason"],
            task_id=task_id,
            status=status,
        )

    reentered = False
    if autonomy == "auto":
        timeline = _fetch_timeline_events(thread_id)
        last_action = next(
            (
                e
                for e in reversed(timeline)
                if e["type"] in {"result_injected", "autonomy_decision"}
            ),
            None,
        )
        if (
            last_action
            and last_action["type"] == "result_injected"
            and depth < MAX_LOOP_DEPTH
        ):
            dsn = _resolve_event_log_dsn()
            if dsn:
                try:
                    with psycopg.connect(dsn) as conn:
                        log_guardian_event_db(
                            conn,
                            persona_tag="guardian",
                            thread_id=thread_id,
                            event_type="loop_reentry",
                            origin="guardian_loop",
                            summary=(
                                "Re-entered loop at depth " f"{depth + 1}"
                            ),
                            payload={
                                "trigger": last_action,
                                "depth": depth + 1,
                            },
                        )
                except Exception as exc:
                    logger.warning(
                        "[guardian_loop] loop reentry log failed: %s", exc
                    )
            logger.info(
                "[guardian_loop] reentering loop after result injection"
            )
            reentered = True
            guardian_loop(
                thread_id,
                autonomy="auto",
                depth=depth + 1,
            )

    return {
        "thread_id": thread_id,
        "autonomy": autonomy,
        "results": results,
        "reentered": reentered,
        "depth": depth,
    }
