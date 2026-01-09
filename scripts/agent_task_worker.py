#!/usr/bin/env python
"""
Agent Task Worker
~~~~~~~~~~~~~~~~~

Background worker that processes agent tasks from the Redis queue.
Routes tasks to the appropriate plugin backend using manifest entrypoints.

Usage:
    python scripts/agent_task_worker.py
"""

import json
import logging
import os
import sys
import time
from typing import Dict, Optional
from uuid import uuid4

import requests

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from guardian.agent_task_queue import AGENT_TASK_QUEUE, update_task_status  # noqa: E402
from guardian.plugins.plugin_loader import load_all_manifests  # noqa: E402
from guardian.plugins.plugin_manifest import PluginManifest  # noqa: E402
from guardian.queue.redis_queue import get_redis_client  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

RESULT_STORE = os.environ.get("AGENT_RESULT_STORE", "codexify:agent_results")
PLUGIN_TIMEOUT = int(os.environ.get("PLUGIN_TIMEOUT", "15"))

# Plugin manifest table indexed by agent ID (loaded on startup)
PLUGIN_BY_ID: Dict[str, PluginManifest] = {}


def load_plugins() -> None:
    """Load plugin manifests and index by ID."""
    global PLUGIN_BY_ID
    manifests = load_all_manifests()
    PLUGIN_BY_ID = {m.id: m for m in manifests}
    logger.info("📦 Loaded %d plugin(s): %s", len(PLUGIN_BY_ID), list(PLUGIN_BY_ID.keys()))


def route_task_to_plugin(agent: str, prompt: str, thread_id: str) -> str:
    """
    Route a task to the appropriate plugin via HTTP POST.

    Args:
        agent: Plugin/agent identifier (must match manifest id)
        prompt: The prompt to send
        thread_id: Thread context ID

    Returns:
        Result string from plugin or error message
    """
    plugin = PLUGIN_BY_ID.get(agent)

    if not plugin:
        error_msg = f"[ERROR] Plugin '{agent}' not found"
        logger.warning(error_msg)
        return error_msg

    logger.info("  → Routing to plugin: %s at %s", plugin.name, plugin.entrypoint)

    try:
        resp = requests.post(
            plugin.entrypoint,
            json={
                "action": "generate",
                "payload": {
                    "prompt": prompt,
                    "thread_id": thread_id,
                },
            },
            timeout=PLUGIN_TIMEOUT,
        )

        if resp.status_code == 200:
            result = resp.json().get("result", "[EMPTY]")
            logger.info("  ← Plugin returned result (%d chars)", len(str(result)))
            return result
        else:
            error_msg = f"[ERROR] {agent} plugin returned status {resp.status_code}"
            logger.error(error_msg)
            return error_msg

    except requests.exceptions.Timeout:
        error_msg = f"[ERROR] Plugin '{agent}' timed out after {PLUGIN_TIMEOUT}s"
        logger.error(error_msg)
        return error_msg
    except requests.exceptions.ConnectionError as e:
        error_msg = f"[ERROR] Cannot connect to plugin '{agent}' at {plugin.entrypoint}: {e}"
        logger.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"[ERROR] Exception during plugin call: {e}"
        logger.error(error_msg)
        return error_msg


def run_agent_stub(agent: str, prompt: str) -> str:
    """
    Fallback stub for when no plugin is available.

    Args:
        agent: Agent identifier
        prompt: Prompt payload

    Returns:
        Simulated response string
    """
    agent_name = agent or "unknown"
    return f"[{agent_name.upper()} STUB] No plugin available, echoing: {prompt}"


def run_worker() -> None:
    """Main worker loop."""
    logger.info("🔄 Agent Task Worker started...")
    logger.info("   Queue: %s", AGENT_TASK_QUEUE)
    logger.info("   Redis: %s", os.environ.get("REDIS_URL", "redis://localhost:6379"))
    logger.info("   Result store: %s", RESULT_STORE)
    logger.info("   Plugin timeout: %ds", PLUGIN_TIMEOUT)

    # Load plugins on startup
    load_plugins()

    redis_client = get_redis_client()

    while True:
        task_id: Optional[str] = None
        try:
            _, raw = redis_client.blpop(AGENT_TASK_QUEUE)
            task = json.loads(raw)

            # Ensure we always have a stable identifier for status/result writes
            task_id = task.get("task_id") or str(uuid4())
            agent = str(task.get("agent") or "unknown")
            prompt = task.get("prompt", "")
            thread_id = task.get("thread_id", "unknown")

            logger.info(
                "🧠 Processing task: agent=%s thread=%s task_id=%s",
                agent,
                thread_id,
                task_id,
            )
            update_task_status(task_id, "running")

            # Route to plugin if available, otherwise use stub
            if agent in PLUGIN_BY_ID:
                result = route_task_to_plugin(agent, prompt, thread_id)
            else:
                logger.warning("  ⚠ No plugin for '%s', using stub", agent)
                result = run_agent_stub(agent, prompt)

            # Store result in Redis
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
