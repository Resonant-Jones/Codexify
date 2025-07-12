# 🩺 health_agent.py
"""
This agent provides a summary of key health metrics such as heart rate, HRV,
sleep hours, etc., potentially pulled from Apple HealthKit or similar APIs.
"""

import logging
from typing import Optional

from memoryos.memoryos import Memoryos

logger = logging.getLogger(__name__)


# TODO: Replace with actual HealthKit API call integration when available
def get_health_summary(
    memory_client: Memoryos,
    timeframe: str = "last_week",
    metrics: Optional[list[str]] = None,
) -> dict:
    if metrics is None:
        metrics = ["heart_rate", "HRV", "sleep"]

    # Example static values; later pull from HealthKit / local cache
    mock_data = {
        "heart_rate": "Average 78 bpm",
        "HRV": "Average 48 ms",
        "sleep": "Average 6.2 hours/night",
    }

    result = {m: mock_data.get(m, "Data not available") for m in metrics}

    # Attempt to save the summary to memory, but don't let it block the response.
    try:
        memory_client.save(
            title=f"Health Summary ({timeframe})",
            content=f"Summary of {metrics} for {timeframe}: {result}",
            tags=["health", "summary", timeframe],
        )
    except Exception as e:
        logger.warning(f"Failed to save health summary to memory: {e}")

    logger.debug(
        f"Returning health summary for timeframe: {timeframe} with metrics: {metrics}"
    )

    return {"status": "ok", "summary": result, "timeframe": timeframe}


def get_past_health_entries(
    memory_client: Memoryos, query: str = "health summary"
) -> list[str]:
    return memory_client.query(query)
