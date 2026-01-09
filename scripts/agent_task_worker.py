#!/usr/bin/env python
"""
Agent Task Worker
~~~~~~~~~~~~~~~~~

Background worker that processes agent tasks from the Redis queue.
Routes tasks to the appropriate agent backend (Codex, Claude).

Usage:
    python scripts/agent_task_worker.py
"""

import logging
import os
import sys
import time

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from guardian.agent_task_queue import (
    dequeue_agent_task,
    update_task_status,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def process_task(task: dict) -> None:
    """
    Process a single agent task.

    Args:
        task: Task payload from queue
    """
    task_id = task.get("task_id", "unknown")
    agent = task.get("agent", "unknown")
    prompt = task.get("prompt", "")
    thread_id = task.get("thread_id", "unknown")

    logger.info(
        "🧠 Processing task: agent=%s thread=%s task_id=%s",
        agent,
        thread_id,
        task_id,
    )

    update_task_status(task_id, "running")

    try:
        # TODO: Route to actual agent implementation
        # For now, simulate agent execution
        if agent == "codex":
            # TODO: Call Codex/OpenAI API
            logger.info("  → Routing to Codex agent...")
            time.sleep(2)  # Simulate processing
            result = f"[Codex stub] Processed: {prompt[:50]}..."

        elif agent == "claude":
            # TODO: Call Claude/Anthropic API
            logger.info("  → Routing to Claude agent...")
            time.sleep(2)  # Simulate processing
            result = f"[Claude stub] Processed: {prompt[:50]}..."

        else:
            logger.warning("  → Unknown agent: %s", agent)
            result = f"Unknown agent: {agent}"

        update_task_status(task_id, "completed")
        logger.info("✅ Completed: task_id=%s result=%s", task_id, result[:100])

    except Exception as e:
        update_task_status(task_id, "failed")
        logger.error("❌ Failed: task_id=%s error=%s", task_id, e)


def run_worker() -> None:
    """Main worker loop."""
    logger.info("🔄 Agent Task Worker started...")
    logger.info("   Queue: %s", os.environ.get("AGENT_TASK_QUEUE", "codexify:agent_tasks"))
    logger.info("   Redis: %s", os.environ.get("REDIS_URL", "redis://localhost:6379"))

    while True:
        try:
            task = dequeue_agent_task(block=True, timeout=30)

            if task is None:
                # Timeout, continue waiting
                continue

            process_task(task)

        except KeyboardInterrupt:
            logger.info("🛑 Worker stopped by user")
            break
        except Exception as e:
            logger.error("Worker error: %s", e)
            time.sleep(1)  # Brief pause before retry


if __name__ == "__main__":
    run_worker()
