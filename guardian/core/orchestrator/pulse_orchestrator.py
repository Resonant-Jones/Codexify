# 🧠 pulse_orchestrator.py
"""
This is the command interpreter that receives Gemma's structured outputs,
routes them to appropriate agents, and returns their responses.

Gemma speaks in structured language (dict-like), and this orchestrator
translates her will into agentic action.
"""

import json
import logging
from memoryos_mcp.memoryos.memoryos import Memoryos
from guardian.core.orchestrator.agents.foresight_agent import run_foresight
from guardian.core.orchestrator.agents.health_agent import get_health_summary
from guardian.core.orchestrator.agents.memory_agent import fetch_memory
from guardian.core.orchestrator.agents.ritual_agent import trigger_ritual

logger = logging.getLogger(__name__)


def orchestrate(command: dict):
    action = command.get("action")
    params = command.get("params", {})
    logger.info(f"Orchestrating action: {action} with params: {params}")

    if action == "get_health_summary":
        result = get_health_summary(**params)
        logger.info("Action 'get_health_summary' executed successfully")
        return result

    elif action == "trigger_ritual":
        result = trigger_ritual(**params)
        logger.info("Action 'trigger_ritual' executed successfully")
        return result

    elif action == "fetch_memory":
        result = fetch_memory(**params)
        logger.info("Action 'fetch_memory' executed successfully")
        return result

    elif action == "run_foresight":
        result = run_foresight(**params)
        logger.info("Action 'run_foresight' executed successfully")
        return result

    elif action == "run_model":
        from guardian.core.orchestrator.model_loader import load_model_backend

        prompt = params.get("prompt", "")
        model = load_model_backend("default")
        response = model.generate(prompt)
        logger.info("Action 'run_model' executed successfully")
        return {"status": "ok", "response": response}

    else:
        logger.warning(f"Unknown action received: {action}")
        return {"error": f"Unknown action '{action}'."}


# Example usage for testing
if __name__ == "__main__":
    test_command = {"action": "trigger_ritual", "params": {"name": "evening_grounding"}}
    result = orchestrate(test_command)
    print(json.dumps(result, indent=2))
