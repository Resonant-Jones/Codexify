"""
System Rate Limiter
----------------
Thread-safe async rate limiting with system-wide coordination.
"""

import asyncio
import logging
import time
from typing import Dict, Optional

from guardian.config import Config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GlobalRateCoordinator:
    """Coordinates system-wide rate limiting."""

    _instance: Optional["GlobalRateCoordinator"] = None
    _lock = asyncio.Lock()

    def __init__(self):
        """Initialize coordinator."""
        self.last_operation = 0.0
        self.operation_count = 0
        self.lock = asyncio.Lock()

    @classmethod
    async def get_instance(cls) -> "GlobalRateCoordinator":
        """Get or create singleton instance."""
        async with cls._lock:
            if not cls._instance:
                cls._instance = cls()
            return cls._instance

    async def check_rate(self, min_interval: float) -> None:
        """
        Check and enforce system-wide rate limiting.

        Args:
            min_interval: Minimum time between operations
        """
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
    """Thread-safe rate limiter with system coordination."""

    def __init__(self, rate: float):
        """
        Initialize rate limiter.

        Args:
            rate: Maximum operations per second
        """
        self.min_interval = 1.0 / rate
        self.last_operation = 0.0
        self.lock = asyncio.Lock()
        self._coordinator = None

    async def _get_coordinator(self) -> GlobalRateCoordinator:
        """Get or create coordinator instance."""
        if not self._coordinator:
            self._coordinator = await GlobalRateCoordinator.get_instance()
        return self._coordinator

    async def acquire(self) -> None:
        """
        Acquire permission to proceed.
        Enforces both local and system-wide rate limits.
        """
        # First check system-wide limits
        coordinator = await self._get_coordinator()
        await coordinator.check_rate(self.min_interval)

        # Then enforce local limits
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
    limiter = RateLimiter(rate)

    def decorator(func):
        async def wrapper(*args, **kwargs):
            await limiter.acquire()
            return await func(*args, **kwargs)

        return wrapper

    return decorator


# Convenience aliases
rate_limited = rate_limit
