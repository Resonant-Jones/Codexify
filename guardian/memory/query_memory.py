"""
Memory Query Module
-----------------
Provides efficient, cached access to memory storage.
"""

import json
import logging
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from guardian.cache import lru_cache_safe, memoize_to_disk
from guardian.config import Config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MemoryStore:
    """Memory storage and query interface."""

    def __init__(self, db_path: str = "guardian/memory/store.db"):
        """
        Initialize memory store.

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT,
                    tags TEXT
                )
            """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON memories(timestamp)
            """
            )

    @lru_cache_safe(maxsize=1000, expire=300)  # Cache 1000 results for 5 minutes
    def query_by_time(
        self,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Query memories by time range.

        Args:
            start_time: Start of time range (ISO format)
            end_time: End of time range (ISO format)
            limit: Maximum number of results

        Returns:
            List[Dict[str, Any]]: Matching memories
        """
        query = "SELECT * FROM memories WHERE 1=1"
        params = []

        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time)

        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)

            return [
                {
                    "id": row["id"],
                    "timestamp": row["timestamp"],
                    "content": row["content"],
                    "metadata": json.loads(row["metadata"] or "{}"),
                    "tags": row["tags"].split(",") if row["tags"] else [],
                }
                for row in cursor.fetchall()
            ]

    @memoize_to_disk(expire=3600)  # Cache for 1 hour
    def query_by_tags(self, tags: List[str], limit: int = 100) -> List[Dict[str, Any]]:
        """
        Query memories by tags.

        Args:
            tags: List of tags to match
            limit: Maximum number of results

        Returns:
            List[Dict[str, Any]]: Matching memories
        """
        placeholders = ",".join("?" * len(tags))
        query = f"""
            SELECT * FROM memories 
            WHERE tags LIKE ?
            ORDER BY timestamp DESC
            LIMIT ?
        """

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, [f"%{tag}%" for tag in tags] + [limit])

            return [
                {
                    "id": row["id"],
                    "timestamp": row["timestamp"],
                    "content": row["content"],
                    "metadata": json.loads(row["metadata"] or "{}"),
                    "tags": row["tags"].split(",") if row["tags"] else [],
                }
                for row in cursor.fetchall()
            ]

    @lru_cache_safe(maxsize=100, expire=60)  # Cache 100 results for 1 minute
    def query_by_content(
        self, search_text: str, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Query memories by content text.

        Args:
            search_text: Text to search for
            limit: Maximum number of results

        Returns:
            List[Dict[str, Any]]: Matching memories
        """
        query = """
            SELECT * FROM memories 
            WHERE content LIKE ?
            ORDER BY timestamp DESC
            LIMIT ?
        """

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, [f"%{search_text}%", limit])

            return [
                {
                    "id": row["id"],
                    "timestamp": row["timestamp"],
                    "content": row["content"],
                    "metadata": json.loads(row["metadata"] or "{}"),
                    "tags": row["tags"].split(",") if row["tags"] else [],
                }
                for row in cursor.fetchall()
            ]


# Global memory store instance
memory_store = MemoryStore()


# Convenience functions
def query_memory(
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    tags: Optional[List[str]] = None,
    search_text: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    Query memories with caching.

    Args:
        start_time: Start of time range
        end_time: End of time range
        tags: Tags to match
        search_text: Text to search for
        limit: Maximum results

    Returns:
        List[Dict[str, Any]]: Matching memories
    """
    if tags:
        return memory_store.query_by_tags(tags, limit)
    elif search_text:
        return memory_store.query_by_content(search_text, limit)
    else:
        return memory_store.query_by_time(start_time, end_time, limit)
