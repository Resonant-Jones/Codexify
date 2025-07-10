"""
Event-Safe Rate Limiter
--------------------
Thread-safe async rate limiting with event loop safety.
"""

import asyncio
import logging
import time
from typing import Dict, Optional

from guardian.config import Config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GlobalCoordinator:
    """Coordinates system-wide rate limiting."""

    _instances: Dict[int, "GlobalCoordinator"] = {}
    _lock = asyncio.Lock()

    def __init__(self):
        """Initialize coordinator."""
        self._loop = asyncio.get_running_loop()
        self._loop_id = id(self._loop)
        self.last_operation = 0.0
        self.operation_count = 0
        self.lock = asyncio.Lock()

    @classmethod
    async def get_instance(cls) -> "GlobalCoordinator":
        """Get or create instance for current event loop."""
        loop = asyncio.get_running_loop()
        loop_id = id(loop)

        if loop_id not in cls._instances:
            async with cls._lock:
                if loop_id not in cls._instances:
                    cls._instances[loop_id] = cls()
        return cls._instances[loop_id]

    async def check_rate(self, min_interval: float) -> None:
        """
        Check and enforce system-wide rate limiting.

        Args:
            min_interval: Minimum time between operations
        """
        if self._loop != asyncio.get_running_loop():
            raise RuntimeError("GlobalCoordinator used in wrong event loop")

        async with self.lock:
            current_time = time.time()
            elapsed = current_time - self.last_operation

            # Apply safe mode rate reduction if enabled
            if Config.SAFE_MODE:
                safe_interval = 1.0 / Config.SAFE_MODE_RATE_LIMIT
                min_interval = max(min_interval, safe_interval)

            if elapsed < min_interval:
                delay = min_interval - elapsed
                await asyncio.sleep(delay)

            self.last_operation = time.time()
            self.operation_count += 1


class RateLimiter:
    """Thread-safe rate limiter with event loop safety."""

    def __init__(self, rate: float):
        """
        Initialize rate limiter.

        Args:
            rate: Maximum operations per second
        """
        self._loop = asyncio.get_running_loop()
        self._loop_id = id(self._loop)
        self.min_interval = 1.0 / rate
        self.last_operation = 0.0
        self.lock = asyncio.Lock()

    async def acquire(self) -> None:
        """
        Acquire permission to proceed.

        Raises:
            RuntimeError: If used in wrong event loop
        """
        current_loop = asyncio.get_running_loop()
        if current_loop is not self._loop:
            raise RuntimeError(
                "RateLimiter must be created and used in same event loop"
            )

        # Get coordinator for current loop
        coordinator = await GlobalCoordinator.get_instance()
        await coordinator.check_rate(self.min_interval)

        # Enforce local limits
        async with self.lock:
            current_time = time.time()
            elapsed = current_time - self.last_operation

            if elapsed < self.min_interval:
                delay = self.min_interval - elapsed
                await asyncio.sleep(delay)

            self.last_operation = time.time()


def rate_limit(rate: float):
    """
    Rate limiting decorator.

    Args:
        rate: Maximum operations per second
    """

    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Create limiter in current event loop
            limiter = RateLimiter(rate)
            await limiter.acquire()
            return await func(*args, **kwargs)

        return wrapper

    return decorator


# Convenience aliases
rate_limited = rate_limit
