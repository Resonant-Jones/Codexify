"""
Async Performance Utilities
------------------------
Async-aware decorators and patterns for efficient resource usage.
"""

import asyncio
import functools
import logging
import time
from typing import Any, Callable, Dict, TypeVar, Optional, Awaitable

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Type variables
F = TypeVar("F", bound=Callable[..., Any])
AsyncF = TypeVar("AsyncF", bound=Callable[..., Awaitable[Any]])


class RateLimiter:
    """Thread-safe rate limiter."""

    def __init__(self, rate_limit: float):
        """
        Initialize rate limiter.

        Args:
            rate_limit: Maximum calls per second
        """
        self.min_interval = 1.0 / rate_limit
        self.last_called: float = 0
        self.lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Acquire rate limit slot."""
        async with self.lock:
            current_time = time.time()
            elapsed = current_time - self.last_called

            if elapsed < self.min_interval:
                wait_time = self.min_interval - elapsed
                await asyncio.sleep(wait_time)

            self.last_called = time.time()


def async_rate_limited(
    name: str, rate_limit: float, burst_size: int = 1
) -> Callable[[AsyncF], AsyncF]:
    """
    Async-aware rate limiting decorator.

    Args:
        name: Name for logging
        rate_limit: Maximum calls per second
        burst_size: Maximum burst size

    Returns:
        Callable: Decorated function
    """
    limiters: Dict[str, RateLimiter] = {}

    def get_limiter(key: str) -> RateLimiter:
        if key not in limiters:
            limiters[key] = RateLimiter(rate_limit)
        return limiters[key]

    def decorator(func: AsyncF) -> AsyncF:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            limiter = get_limiter(name)
            await limiter.acquire()

            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in rate limited function {name}: {e}")
                raise

        return wrapper  # type: ignore

    return decorator


class Debouncer:
    """Async debouncer."""

    def __init__(self, wait: float):
        """
        Initialize debouncer.

        Args:
            wait: Time to wait in seconds
        """
        self.wait = wait
        self.task: Optional[asyncio.Task] = None
        self.lock = asyncio.Lock()

    async def debounce(
        self, func: Callable[..., Awaitable[Any]], *args: Any, **kwargs: Any
    ) -> Any:
        """
        Debounce function call.

        Args:
            func: Function to debounce
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Any: Function result
        """
        async with self.lock:
            if self.task and not self.task.done():
                self.task.cancel()

            async def delayed():
                await asyncio.sleep(self.wait)
                return await func(*args, **kwargs)

            self.task = asyncio.create_task(delayed())
            return await self.task


def async_debounce(wait: float) -> Callable[[AsyncF], AsyncF]:
    """
    Async-aware debounce decorator.

    Args:
        wait: Time to wait in seconds

    Returns:
        Callable: Decorated function
    """
    debouncers: Dict[str, Debouncer] = {}

    def decorator(func: AsyncF) -> AsyncF:
        key = func.__name__

        if key not in debouncers:
            debouncers[key] = Debouncer(wait)

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await debouncers[key].debounce(func, *args, **kwargs)

        return wrapper  # type: ignore

    return decorator


def async_throttle(rate: float) -> Callable[[AsyncF], AsyncF]:
    """
    Async-aware throttle decorator.

    Args:
        rate: Maximum calls per second

    Returns:
        Callable: Decorated function
    """
    min_interval = 1.0 / rate
    last_called: Dict[str, float] = {}
    locks: Dict[str, asyncio.Lock] = {}

    def get_lock(key: str) -> asyncio.Lock:
        if key not in locks:
            locks[key] = asyncio.Lock()
        return locks[key]

    def decorator(func: AsyncF) -> AsyncF:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            key = func.__name__
            lock = get_lock(key)

            async with lock:
                current_time = time.time()

                if key in last_called:
                    elapsed = current_time - last_called[key]
                    if elapsed < min_interval:
                        # Too soon, skip call
                        logger.debug(f"Throttled call to {func.__name__}")
                        return None

                last_called[key] = current_time
                return await func(*args, **kwargs)

        return wrapper  # type: ignore

    return decorator


# Convenience aliases
async_rate_limited_plugin_runner = async_rate_limited
async_batch_processor = async_debounce
