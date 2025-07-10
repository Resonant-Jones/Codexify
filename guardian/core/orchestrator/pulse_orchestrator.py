# 🧠 pulse_orchestrator.py
"""
This is the command interpreter that receives Gemma's structured outputs,
routes them to appropriate agents, and returns their responses.

Gemma speaks in structured language (dict-like), and this orchestrator
translates her will into agentic action.
"""

import json
import logging
from concurrent.futures import TimeoutError

from pebble import ProcessPool

from guardian.core.config import settings
from guardian.core.client_factory import get_memoryos_instance
from guardian.core.orchestrator.agents.foresight_agent import run_foresight
from guardian.core.orchestrator.agents.health_agent import get_health_summary
from guardian.core.orchestrator.agents.memory_agent import fetch_memory
from guardian.core.orchestrator.agents.ritual_agent import trigger_ritual

logger = logging.getLogger(__name__)

# Map action strings to their corresponding agent functions for cleaner, scalable routing.
AGENT_ACTIONS = {
    "get_health_summary": get_health_summary,
    "trigger_ritual": trigger_ritual,
    "fetch_memory": fetch_memory,
    "run_foresight": run_foresight,
}


def _execute_agent_task(agent_function, params: dict):
    """
    Internal helper to run the agent in a separate process.
    This allows for isolation and timeout control.
    """
    # Each process gets its own singleton instance from the factory.
    # The lru_cache on get_memoryos_instance is per-process.
    memory_client = get_memoryos_instance()
    return agent_function(memory_client=memory_client, **params)


def orchestrate(command: dict):
    action = command.get("action")
    params = command.get("params", {})
    logger.info(f"Orchestrating action: {action} with params: {params}")

    # Handle the 'run_model' action separately as it has a unique setup.
    if action == "run_model":
        try:
            from guardian.core.orchestrator.model_loader import load_model_backend

            prompt = params.get("prompt", "")
            model = load_model_backend("default")
            response = model.generate(prompt)
            logger.info("Action 'run_model' executed successfully")
            return {"status": "ok", "response": response}
        except Exception as e:
            logger.exception(f"Error executing 'run_model' action: {e}")
            return {"status": "error", "message": f"Failed to run model: {e}"}

    # Look up the agent function from our mapping.
    agent_function = AGENT_ACTIONS.get(action)

    if not agent_function:
        logger.warning(f"Unknown action received: {action}")
        return {"status": "error", "message": f"Unknown action '{action}'."}

    # Execute the agent function in a separate process to enforce a timeout.
    try:
        with ProcessPool() as pool:
            future = pool.schedule(
                function=_execute_agent_task,
                args=[agent_function, params],
                timeout=settings.AGENT_TIMEOUT_SECONDS,
            )
            result = future.result()  # Blocks until completion or timeout

        logger.info(f"Action '{action}' executed successfully")
        return result
    except TimeoutError:
        logger.error(
            f"Action '{action}' timed out after {settings.AGENT_TIMEOUT_SECONDS} seconds."
        )
        return {"status": "error", "message": f"Action '{action}' timed out."}
    except Exception as e:
        # Log the full exception traceback for effective debugging.
        logger.exception(
            f"An unexpected error occurred while executing action '{action}'"
        )
        # Return a standardized error response to the caller.
        return {
            "status": "error",
            "message": f"An unexpected error occurred in the agent for action '{action}'.",
            "details": str(e),
        }



# Example usage for testing
if __name__ == "__main__":
    test_command = {"action": "trigger_ritual", "params": {"name": "evening_grounding"}}
    result = orchestrate(test_command)
    print(json.dumps(result, indent=2))
