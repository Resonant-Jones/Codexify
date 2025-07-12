# 🙏 ritual_agent.py
"""
This agent handles the triggering of pre-defined rituals and logs their
execution to memory using the injected memory client.
"""

import logging
from memoryos.memoryos import Memoryos

logger = logging.getLogger(__name__)


def trigger_ritual(memory_client: Memoryos, name: str) -> dict:
    """Triggers a ritual and logs it to memory using the injected client."""
    logger.info(f"Ritual '{name}' triggered.")
    response = {}

    if name == "evening_grounding":
        response = {
            "status": "success",
            "message": "Evening grounding ritual activated: breath, stillness, and ambient focus engaged.",
        }
    elif name == "daily_checkin":
        response = {
            "status": "success",
            "message": "Daily check-in ritual initiated. Prompt dispatched for reflection.",
        }
    elif name == "morning_initiation":
        response = {
            "status": "success",
            "message": "Morning initiation ritual complete: light music, intention set, ready for day.",
        }
    else:
        logger.warning(f"Attempted to trigger unknown ritual: {name}")
        response = {
            "status": "error",
            "message": f"Ritual '{name}' is not recognized or not yet implemented.",
        }

    # Log the execution of the ritual to memory
    try:
        memory_client.add_memory(
            user_input=f"Ritual triggered: {name}",
            agent_response=response.get("message", "No message."),
            meta_data={"tags": ["ritual", "log", name]},
        )
    except Exception as e:
        logger.error(f"Failed to log ritual '{name}' to memory: {e}")

    return response
