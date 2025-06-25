# 🧠 memory_agent.py
"""
This agent interfaces with the Codex-style memory logs,
retrieving entries based on tags, timestamps, or keywords.
"""

import logging
import os
from datetime import datetime
from typing import Optional, Union

from memoryOS.core import MemoryManager

logger = logging.getLogger(__name__)
# For demo purposes, define a simple memory log directory
MEMORY_DIR = "codex_memory"

memory = MemoryManager("memory_store.json")


def fetch_memory(
    tag: Optional[str] = None, keyword: Optional[str] = None
) -> dict[str, Union[str, list[dict[str, str]]]]:
    logger.info(f"Fetching memory with tag={tag} and keyword={keyword}")
    try:
        results = memory.fetch_memory(tag=tag, keyword=keyword)
        if results:
            return {"status": "ok", "results": results}
        else:
            return {"status": "ok", "results": "No relevant entries found."}
    except Exception as e:
        logger.error(f"Error fetching memory: {e}")
        return {
            "status": "error",
            "message": str(e),
        }


def save_memory_entry(
    content: str, tags: Optional[list[str]] = None, timestamp: Optional[str] = None
) -> dict:
    logger.info(f"Saving memory entry with tags={tags}")
    try:
        entry = {
            "type": "memory",
            "content": content,
            "tags": tags or [],
            "timestamp": timestamp or datetime.utcnow().isoformat(),
        }
        memory.log_event(user_id="system", agent="memory_agent", data=entry)
        return {"status": "ok", "message": "Memory entry saved successfully."}
    except Exception as e:
        logger.error(f"Error saving memory: {e}")
        return {"status": "error", "message": str(e)}
