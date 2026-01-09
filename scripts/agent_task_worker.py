#!/usr/bin/env python
"""
Agent Task Worker
~~~~~~~~~~~~~~~~~

Background worker that processes agent tasks from the Redis queue.
Routes tasks to the appropriate agent backend (Codex, Claude).

Usage:
    python scripts/agent_task_worker.py
"""

import json
import logging
import os
import sys
import time
from uuid import uuid4

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from guardian.agent_task_queue import AGENT_TASK_QUEUE, update_task_status  # noqa: E402
from guardian.queue.redis_queue import get_redis_client  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

RESULT_STORE = os.environ.get("AGENT_RESULT_STORE", "codexify:agent_results")


def run_agent_stub(agent: str, prompt: str) -> str:
    """
    Simulate agent execution and return a placeholder response.

    Args:
        agent: Agent identifier (codex, claude, etc.)
        prompt: Prompt payload to echo back
    """
    agent_name = agent or "unknown"
    return f"[{agent_name.upper()}] simulated response to: {prompt}"


def run_worker() -> None:
    """Main worker loop."""
    logger.info("🔄 Agent Task Worker started...")
    logger.info("   Queue: %s", AGENT_TASK_QUEUE)
    logger.info(
        "   Redis: %s", os.environ.get("REDIS_URL", "redis://localhost:6379")
    )
    logger.info("   Result store: %s", RESULT_STORE)

    redis_client = get_redis_client()

    while True:
        task_id: str | None = None
        try:
            _, raw = redis_client.blpop(AGENT_TASK_QUEUE)
            task = json.loads(raw)
            # Ensure we always have a stable identifier for status/result writes.
            task_id = task.get("task_id") or str(uuid4())
            agent = str(task.get("agent") or "unknown")
            prompt = task.get("prompt", "")
            thread_id = task.get("thread_id", "unknown")

            logger.info(
                "🧠 Running agent task: %s on thread %s", agent, thread_id
            )
            update_task_status(task_id, "running")

            result = run_agent_stub(agent, prompt)

            redis_client.hset(
                RESULT_STORE,
                task_id,
                json.dumps(
                    {
                        "result": result,
                        "status": "done",
                        "thread_id": thread_id,
                        "agent": agent,
                    }
                ),
            )
            update_task_status(task_id, "completed")
            logger.info("✅ Task %s complete", task_id)

        except KeyboardInterrupt:
            logger.info("🛑 Worker stopped by user")
            break
        except Exception as e:
            if task_id:
                update_task_status(task_id, "failed")
            logger.error("Worker error: %s", e)
            time.sleep(1)  # Brief pause before retry


if __name__ == "__main__":
    run_worker()
