# 🧠 pulse_orchestrator.py
"""
This is the command interpreter that receives Gemma's structured outputs,
routes them to appropriate agents, and returns their responses.

Gemma speaks in structured language (dict-like), and this orchestrator
translates her will into agentic action.
"""

import json
from guardian.core.orchestrator.agents.ritual_agent import trigger_ritual
from guardian.core.orchestrator.agents.health_agent import get_health_summary
from guardian.core.orchestrator.agents.memory_agent import fetch_memory
from guardian.core.orchestrator.agents.foresight_agent import run_foresight

def orchestrate(command: dict):
    action = command.get("action")
    params = command.get("params", {})

    if action == "get_health_summary":
        return get_health_summary(**params)

    elif action == "trigger_ritual":
        return trigger_ritual(**params)

    elif action == "fetch_memory":
        return fetch_memory(**params)

    elif action == "run_foresight":
        return run_foresight(**params)

    elif action == "run_model":
        from guardian.core.orchestrator.model_loader import load_model_backend
        prompt = params.get("prompt", "")
        model = load_model_backend("default")
        response = model.generate(prompt)
        return {
            "status": "ok",
            "response": response
        }

    else:
        return {"error": f"Unknown action '{action}'."}

# Example usage for testing
if __name__ == "__main__":
    test_command = {
        "action": "trigger_ritual",
        "params": {
            "name": "evening_grounding"
        }
    }
    result = orchestrate(test_command)
    print(json.dumps(result, indent=2))