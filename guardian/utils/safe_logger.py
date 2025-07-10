"""
Safe Async Logger
--------------
Thread-safe async logging with batching and rate limiting.
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from guardian.config.core import Config
from guardian.utils.safeguard import throttle, debounce

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BatchLogger:
    """Batched async logging with safeguards."""

    def __init__(
        self,
        log_dir: Path,
        batch_size: Optional[int] = None,
        flush_interval: Optional[float] = None,
        max_buffer: Optional[int] = None,
    ):
        cfg = Config()  # Now you have the full Settings instance
        self.batch_size = batch_size or cfg.MEMORY_BATCH_SIZE
        self.flush_interval = flush_interval or cfg.MEMORY_FLUSH_INTERVAL
        self.max_buffer = max_buffer or cfg.MAX_MEMORY_BUFFER
        """
        Initialize batch logger.
        
        Args:
            log_dir: Directory for log files
            batch_size: Events per batch
            flush_interval: Seconds between forced flushes
            max_buffer: Maximum events in memory
        """
        self.log_dir = log_dir
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.max_buffer = max_buffer

        self.buffer: List[Dict[str, Any]] = []
        self.pending_writes: Set[str] = set()
        self.last_flush = time.time()
        self.lock = asyncio.Lock()

        # Create log directory
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Start background flush task if event loop exists
        try:
            loop = asyncio.get_running_loop()
            self.flush_task = loop.create_task(self._auto_flush())
        except RuntimeError:
            # No running loop at init time, disable auto-flush
            self.flush_task = None

    @throttle(rate=10.0)  # Limit to 10 logs/sec
    async def log(self, event: Dict[str, Any], level: str = "INFO") -> None:
        """
        Log an event with rate limiting.

        Args:
            event: Event data to log
            level: Log level
        """
        async with self.lock:
            # Add metadata
            event_with_meta = {
                "timestamp": datetime.utcnow().isoformat(),
                "level": level,
                **event,
            }

            # Add to buffer
            self.buffer.append(event_with_meta)

            # Check if we should flush
            if len(self.buffer) >= self.batch_size:
                await self.flush()
            elif len(self.buffer) >= self.max_buffer:
                # Emergency flush if buffer is full
                logger.warning("Buffer full - emergency flush")
                await self.flush()

    @debounce(wait=0.1)  # Debounce rapid flushes
    async def flush(self) -> None:
        """Flush buffered events to disk."""
        async with self.lock:
            if not self.buffer:
                return

            # Get current buffer and clear
            current_buffer = self.buffer
            self.buffer = []

            # Generate log file name
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            log_file = self.log_dir / f"events_{timestamp}.jsonl"

            try:
                # Write events
                with open(log_file, "a") as f:
                    for event in current_buffer:
                        f.write(json.dumps(event) + "\n")

                self.last_flush = time.time()
                logger.debug(f"Flushed {len(current_buffer)} events to {log_file}")

            except Exception as e:
                logger.error(f"Failed to flush events: {e}")
                # Return events to buffer
                self.buffer.extend(current_buffer)

    async def _auto_flush(self) -> None:
        """Background task to auto-flush periodically."""
        while True:
            try:
                await asyncio.sleep(self.flush_interval)

                # Check if flush needed
                current_time = time.time()
                if (
                    current_time - self.last_flush >= self.flush_interval
                    and self.buffer
                ):
                    await self.flush()

            except asyncio.CancelledError:
                # Final flush on cancellation
                if self.buffer:
                    await self.flush()
                break
            except Exception as e:
                logger.error(f"Auto-flush error: {e}")

    async def close(self) -> None:
        """Clean shutdown of logger."""
        # Cancel auto-flush task
        if self.flush_task:
            self.flush_task.cancel()
            try:
                await self.flush_task
            except asyncio.CancelledError:
                pass

        # Final flush
        await self.flush()


class SafeLogger:
    """Thread-safe logger with batching and rate limiting."""

    def __init__(self, name: str, log_dir: Optional[Path] = None):
        """
        Initialize safe logger.

        Args:
            name: Logger name
            log_dir: Optional custom log directory
        """
        self.name = name
        settings = Config()
        self.log_dir = log_dir or Path(settings.LOG_DIR) / name
        self.batch_logger = BatchLogger(self.log_dir)

    @throttle(rate=20.0)  # Limit INFO logs
    async def info(self, message: str, **kwargs: Any) -> None:
        """Log INFO level message."""
        await self.batch_logger.log({"message": message, **kwargs}, level="INFO")

    @throttle(rate=50.0)  # Allow more DEBUG logs
    async def debug(self, message: str, **kwargs: Any) -> None:
        """Log DEBUG level message."""
        if Config.VERBOSE_LOGGING:
            await self.batch_logger.log({"message": message, **kwargs}, level="DEBUG")

    @throttle(rate=5.0)  # Limit WARNING logs
    async def warning(self, message: str, **kwargs: Any) -> None:
        """Log WARNING level message."""
        await self.batch_logger.log({"message": message, **kwargs}, level="WARNING")

    @throttle(rate=2.0)  # Strictly limit ERROR logs
    async def error(self, message: str, **kwargs: Any) -> None:
        """Log ERROR level message."""
        await self.batch_logger.log({"message": message, **kwargs}, level="ERROR")

    async def close(self) -> None:
        """Clean shutdown of logger."""
        await self.batch_logger.close()


# Global logger instances
system_logger = SafeLogger("system")
memory_logger = SafeLogger("memory")
plugin_logger = SafeLogger("plugins")
