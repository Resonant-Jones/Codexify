# 🔮 foresight_agent.py
"""
This agent provides predictive insights or nudges based on prior memory logs,
health data, and optionally calendar events or behavior patterns.
"""

import logging
from typing import Any, Optional

from memoryos_mcp.memoryos.memoryos import Memoryos

ForesightResponse = dict[str, Any]

logger = logging.getLogger(__name__)


def run_foresight(
    memory_client: Memoryos,
    context: Optional[str] = None,
    timeframe: str = "next_48h",
) -> ForesightResponse:
    """
    Generate predictive nudges or status reports based on user context and timeframes.

    Args:
        memory_client: The configured Memoryos instance from the factory.
        context: Optional category like 'stress' or 'sleep' to focus foresight.
        timeframe: String defining how far ahead to analyze (e.g., 'next_48h').

    Returns:
        A dictionary containing foresight status and a human-readable message.
    """
    logger.debug(f"Foresight triggered with context={context}, timeframe={timeframe}")
    if context == "stress":
        try:
            # Use the injected memory_client, not a locally created one
            stress_logs = memory_client.fetch_memory(
                query="stress", timeframe="last_14d", tags=["ritual", "log"], limit=50
            )
            if len(stress_logs) > 10:
                return {
                    "status": "nudge",
                    "message": "Recent logs suggest a stress trend. Consider preparing a grounding ritual or journaling soon.",
                }
            else:
                return {
                    "status": "ok",
                    "message": f"Stress levels appear stable over the past two weeks. No action needed right now.",
                }
        except Exception as e:
            logger.error(f"MemoryOS error during foresight: {e}")
            return {
                "status": "error",
                "message": "Unable to access memory logs for foresight prediction.",
            }
    return {
        "status": "ok",
        "message": f"No significant foresight flags detected for context '{context}' in {timeframe}.",
    }
