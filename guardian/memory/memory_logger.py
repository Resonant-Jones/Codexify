"""
Memory Logger Module
-----------------
Efficient event logging with batch processing.
"""

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from guardian.utils.performance import batch_flush
from guardian.config import Config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MemoryLogger:
    """Memory event logger with batched writes."""

    def __init__(
        self,
        log_dir: str = "guardian/memory/logs",
        batch_size: int = 20,
        flush_interval: float = 5.0,
        compact_mode: bool = False,
    ):
        """
        Initialize memory logger.

        Args:
            log_dir: Directory for log files
            batch_size: Events per batch
            flush_interval: Seconds between flushes
            compact_mode: Use compact logging format
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.compact_mode = compact_mode

        self.buffer: List[Dict[str, Any]] = []
        self.current_log_file = self._get_log_file()

        # Start batch processing
        try:
            asyncio.get_running_loop().create_task(self._process_buffer())
        except RuntimeError:
            # Imported outside a loop – task will start later
            pass

    def _get_log_file(self) -> Path:
        """Get current log file path."""
        timestamp = time.strftime("%Y%m%d")
        return self.log_dir / f"memory_{timestamp}.jsonl"

    async def _process_buffer(self) -> None:
        """Process buffered events."""
        while True:
            if len(self.buffer) >= self.batch_size:
                await self._flush_buffer()
            await asyncio.sleep(self.flush_interval)

    async def _flush_buffer(self) -> None:
        """Flush buffered events to disk."""
        if not self.buffer:
            return

        try:
            # Get current buffer
            events = self.buffer.copy()
            self.buffer.clear()

            # Update log file path
            self.current_log_file = self._get_log_file()

            # Write events
            with open(self.current_log_file, "a") as f:
                for event in events:
                    if self.compact_mode:
                        # Compact format
                        minimal = {
                            "ts": event["timestamp"],
                            "src": event["source"],
                            "type": event["event_type"],
                        }
                        if event.get("payload"):
                            minimal["p"] = event["payload"]
                        if event.get("tags"):
                            minimal["t"] = event["tags"]
                        f.write(json.dumps(minimal) + "\n")
                    else:
                        # Full format
                        f.write(json.dumps(event) + "\n")

        except Exception as e:
            logger.error(f"Failed to flush memory buffer: {e}")
            # Restore events to buffer
            self.buffer.extend(events)

    def log_event(
        self,
        source: str,
        event_type: str,
        payload: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> None:
        """
        Log memory event.

        Args:
            source: Event source
            event_type: Type of event
            payload: Event data
            tags: Event tags
        """
        event = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.%f"),
            "source": source,
            "event_type": event_type,
        }

        if payload:
            event["payload"] = payload
        if tags:
            event["tags"] = tags

        self.buffer.append(event)

        # Flush if buffer full
        if len(self.buffer) >= self.batch_size:
            asyncio.create_task(self._flush_buffer())


# Global logger instance with compact mode from config
memory_logger = MemoryLogger(compact_mode=getattr(Config, "COMPACT_LOGGING", False))
