"""
Rate Limiter Module
----------------
Simple, reliable rate limiting implementation.
"""

import asyncio
import logging
import time
from typing import Any, Callable, Dict, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimpleRateLimiter:
    """Basic rate limiter with precise timing."""

    def __init__(self, rate: float):
        """
        Initialize rate limiter.

        Args:
            rate: Maximum operations per second
        """
        self.min_interval = 1.0 / rate
        self.last_call = 0.0
        self.lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Wait until rate limit allows execution."""
        async with self.lock:
            now = time.time()
            elapsed = now - self.last_call

            if elapsed < self.min_interval:
                await asyncio.sleep(self.min_interval - elapsed)

            self.last_call = time.time()


def rate_limit(rate: float):
    """
    Simple rate limiting decorator.

    Args:
        rate: Maximum operations per second
    """
    limiter = SimpleRateLimiter(rate)

    def decorator(func):
        async def wrapper(*args, **kwargs):
            await limiter.acquire()
            return await func(*args, **kwargs)

        return wrapper

    return decorator


# Example usage:
if __name__ == "__main__":

    @rate_limit(2.0)  # 2 operations per second
    async def test_func():
        print(f"Called at {time.time()}")

    async def main():
        for _ in range(5):
            await test_func()

    asyncio.run(main())
