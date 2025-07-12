# 🔮 foresight_agent.py
"""
This agent provides predictive insights or nudges based on prior memory logs,
health data, and optionally calendar events or behavior patterns.
"""

import logging
from typing import Any, Optional

from memoryos.memoryos import Memoryos

ForesightResponse = dict[str, Any]

logger = logging.getLogger(__name__)

# --- Constants for better maintainability ---
CONTEXT_STRESS = "stress"

STATUS_OK = "ok"
STATUS_NUDGE = "nudge"
STATUS_ERROR = "error"


def _handle_stress_foresight(
    memory_client: Memoryos, timeframe: str
) -> ForesightResponse:
    """Handles foresight logic specifically for the 'stress' context."""
    # Constants for stress logic
    STRESS_TIMEFRAME = "last_14d"
    STRESS_LOG_THRESHOLD = 10

    stress_logs = memory_client.fetch_memory(
        query="stress", timeframe=STRESS_TIMEFRAME, tags=["ritual", "log"], limit=50
    )
    if len(stress_logs) > STRESS_LOG_THRESHOLD:
        return {
            "status": STATUS_NUDGE,
            "message": "Recent logs suggest a stress trend. Consider preparing a grounding ritual or journaling soon.",
        }
    return {
        "status": STATUS_OK,
        "message": f"Stress levels appear stable over the past two weeks. No action needed right now.",
    }


# --- Strategy map for scalable context handling ---
FORESIGHT_STRATEGIES = {
    CONTEXT_STRESS: _handle_stress_foresight,
    # Future contexts can be added here easily:
    # "sleep": _handle_sleep_foresight,
}


def run_foresight(
    memory_client: Memoryos,
    context: str,
    timeframe: str = "next_48h",
) -> ForesightResponse:
    """
    Generate predictive nudges or status reports based on user context and timeframes.

    Args:
        memory_client: The configured Memoryos instance from the factory.
        context: Category like 'stress' or 'sleep' to focus foresight.
        timeframe: String defining how far ahead to analyze (e.g., 'next_48h').

    Returns:
        A dictionary containing foresight status and a human-readable message.
    """
    logger.debug(f"Foresight triggered with context={context}, timeframe={timeframe}")

    strategy = FORESIGHT_STRATEGIES.get(context)

    if not strategy:
        logger.warning(f"No foresight strategy found for context: {context}")
        return {
            "status": STATUS_OK,
            "message": f"No foresight analysis available for context '{context}'.",
        }

    try:
        return strategy(memory_client, timeframe)
    except Exception as e:
        logger.error(f"MemoryOS error during foresight for context '{context}': {e}")
        return {
            "status": STATUS_ERROR,
            "message": "Unable to access memory logs for foresight prediction.",
        }
