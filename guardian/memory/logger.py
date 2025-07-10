"""
Memory Logger Module
------------------
Provides structured logging for memory events with support for multiple backends
(JSONL and SQLite) and extensible for future compression/summarization.
"""

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from guardian.config.system_config import system_config

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class MemoryEvent:
    """Represents a structured memory event."""

    def __init__(
        self,
        source: str,
        event_type: str,
        payload: Dict[str, Any],
        tags: List[str],
        timestamp: Optional[datetime] = None,
    ):
        self.source = source
        self.event_type = event_type
        self.payload = payload
        self.tags = tags
        self.timestamp = timestamp or datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary representation."""
        return {
            "source": self.source,
            "event_type": self.event_type,
            "payload": self.payload,
            "tags": self.tags,
            "timestamp": self.timestamp.isoformat(),
        }


class MemoryLogger:
    """Base class for memory logging backends."""

    def log_event(self, event: MemoryEvent) -> bool:
        """Log a memory event."""
        raise NotImplementedError

    def query_events(
        self,
        source: Optional[str] = None,
        event_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Query memory events."""
        raise NotImplementedError


class JSONLMemoryLogger(MemoryLogger):
    """JSONL-based memory logger."""

    def __init__(self, log_dir: Path):
        self.log_dir = log_dir
        self.current_log = self._get_current_log()
        self.max_file_size = 10 * 1024 * 1024  # 10MB

    def _get_current_log(self) -> Path:
        """Get or create current log file."""
        current = self.log_dir / f"memory_{datetime.utcnow().strftime('%Y%m')}.jsonl"
        current.parent.mkdir(parents=True, exist_ok=True)
        return current

    def _rotate_log_if_needed(self) -> None:
        """Rotate log file if it exceeds max size."""
        if self.current_log.stat().st_size > self.max_file_size:
            self.current_log = self._get_current_log()

    def log_event(self, event: MemoryEvent) -> bool:
        """Log event to JSONL file."""
        try:
            self._rotate_log_if_needed()
            with open(self.current_log, "a") as f:
                json.dump(event.to_dict(), f)
                f.write("\n")
            return True
        except Exception as e:
            logger.error(f"Failed to log event: {e}")
            return False

    def query_events(
        self,
        source: Optional[str] = None,
        event_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Query events from JSONL files."""
        results = []
        count = 0

        # Get all log files in reverse chronological order
        log_files = sorted(self.log_dir.glob("memory_*.jsonl"), reverse=True)

        for log_file in log_files:
            if count >= limit:
                break

            try:
                with open(log_file, "r") as f:
                    for line in f:
                        if count >= limit:
                            break

                        event = json.loads(line)
                        if self._matches_criteria(
                            event, source, event_type, tags, start_time, end_time
                        ):
                            results.append(event)
                            count += 1

            except Exception as e:
                logger.error(f"Error reading log file {log_file}: {e}")

        return results

    def _matches_criteria(
        self,
        event: Dict[str, Any],
        source: Optional[str],
        event_type: Optional[str],
        tags: Optional[List[str]],
        start_time: Optional[datetime],
        end_time: Optional[datetime],
    ) -> bool:
        """Check if event matches query criteria."""
        if source and event["source"] != source:
            return False

        if event_type and event["event_type"] != event_type:
            return False

        if tags and not all(tag in event["tags"] for tag in tags):
            return False

        event_time = datetime.fromisoformat(event["timestamp"])

        if start_time and event_time < start_time:
            return False

        if end_time and event_time > end_time:
            return False

        return True


class SQLiteMemoryLogger(MemoryLogger):
    """SQLite-based memory logger."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """Initialize SQLite database."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memory_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    tags TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON memory_events(timestamp)
            """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_source_type 
                ON memory_events(source, event_type)
            """
            )

    def log_event(self, event: MemoryEvent) -> bool:
        """Log event to SQLite database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO memory_events 
                    (source, event_type, payload, tags, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        event.source,
                        event.event_type,
                        json.dumps(event.payload),
                        json.dumps(event.tags),
                        event.timestamp.isoformat(),
                    ),
                )
            return True
        except Exception as e:
            logger.error(f"Failed to log event: {e}")
            return False

    def query_events(
        self,
        source: Optional[str] = None,
        event_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Query events from SQLite database."""
        query = "SELECT * FROM memory_events WHERE 1=1"
        params = []

        if source:
            query += " AND source = ?"
            params.append(source)

        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)

        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time.isoformat())

        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time.isoformat())

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(query, params)
                results = []

                for row in cursor:
                    event = {
                        "source": row[1],
                        "event_type": row[2],
                        "payload": json.loads(row[3]),
                        "tags": json.loads(row[4]),
                        "timestamp": row[5],
                    }

                    # Filter by tags if specified
                    if tags:
                        event_tags = set(event["tags"])
                        if all(tag in event_tags for tag in tags):
                            results.append(event)
                    else:
                        results.append(event)

                return results[:limit]

        except Exception as e:
            logger.error(f"Failed to query events: {e}")
            return []


class MemoryLogManager:
    """Manages memory logging across multiple backends."""

    def __init__(self):
        self.log_dir = system_config.get_path("memory_dir")
        self.backends: Dict[str, MemoryLogger] = {}
        self._init_backends()

    def _init_backends(self) -> None:
        """Initialize configured logging backends."""
        # Initialize JSONL backend
        jsonl_dir = self.log_dir / "jsonl"
        self.backends["jsonl"] = JSONLMemoryLogger(jsonl_dir)

        # Initialize SQLite backend
        sqlite_path = self.log_dir / "memory.db"
        self.backends["sqlite"] = SQLiteMemoryLogger(sqlite_path)

    def log_event(
        self,
        source: str,
        event_type: str,
        payload: Dict[str, Any],
        tags: List[str],
        backend: str = "sqlite",
    ) -> bool:
        """
        Log a memory event using specified backend.

        Args:
            source: Event source identifier
            event_type: Type of event
            payload: Event data
            tags: Event tags for categorization
            backend: Backend to use ('jsonl' or 'sqlite')

        Returns:
            bool: True if event was logged successfully
        """
        if backend not in self.backends:
            logger.error(f"Unknown backend: {backend}")
            return False

        event = MemoryEvent(source, event_type, payload, tags)
        return self.backends[backend].log_event(event)

    def query_events(self, backend: str = "sqlite", **kwargs) -> List[Dict[str, Any]]:
        """
        Query memory events from specified backend.

        Args:
            backend: Backend to query ('jsonl' or 'sqlite')
            **kwargs: Query parameters (source, event_type, tags, etc.)

        Returns:
            List[Dict[str, Any]]: Matching events
        """
        if backend not in self.backends:
            logger.error(f"Unknown backend: {backend}")
            return []

        return self.backends[backend].query_events(**kwargs)


# Global memory log manager instance
memory_logger = MemoryLogManager()

# Example usage:
if __name__ == "__main__":
    # Log test event
    memory_logger.log_event(
        source="test",
        event_type="example",
        payload={"message": "Test event"},
        tags=["test", "example"],
    )

    # Query events
    events = memory_logger.query_events(source="test", tags=["example"], limit=10)

    print("\nQueried Events:")
    print(json.dumps(events, indent=2))
