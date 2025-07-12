# 📚 memory_agent.py
"""
This agent is responsible for querying and retrieving information from MemoryOS
using the injected memory client.
"""

import logging
from typing import Optional
from memoryos.memoryos import Memoryos

logger = logging.getLogger(__name__)


def fetch_memory(memory_client: Memoryos, query: str, limit: int = 10) -> dict:
    """Fetches memories based on a query using the injected client."""
    logger.debug(f"Fetching memory with query: '{query}'")
    try:
        results = memory_client.query(query, limit=limit)
        return {"status": "ok", "memories": results}
    except Exception as e:
        logger.error(f"Error fetching memory: {e}")
        return {"status": "error", "message": f"Failed to fetch memory: {e}"}


def save_memory_entry(
    memory_client: Memoryos, content: str, tags: Optional[list[str]] = None
) -> dict:
    """Saves a new memory entry using the injected client."""
    logger.info(f"Saving memory entry with tags={tags}")
    try:
        # Use the existing add_memory method from the Memoryos class
        memory_client.add_memory(
            user_input="System Log",
            agent_response=content,
            meta_data={"tags": tags or []},
        )
        return {"status": "ok", "message": "Memory entry saved successfully."}
    except Exception as e:
        logger.error(f"Error saving memory: {e}")
        return {"status": "error", "message": str(e)}
