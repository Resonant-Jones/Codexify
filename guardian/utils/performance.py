"""
Performance Utilities
------------------
Provides decorators and patterns for efficient resource usage.
"""

import asyncio
import functools
import logging
import time
from typing import Any, Callable, List, Optional, TypeVar, Dict
from collections import deque

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Type variables
F = TypeVar("F", bound=Callable[..., Any])
T = TypeVar("T")


def debounce(wait: float) -> Callable[[F], F]:
    """
    Decorator to debounce function calls.
    Only executes after wait period with no subsequent calls.

    Args:
        wait: Time to wait in seconds

    Returns:
        Callable: Decorated function
    """

    def decorator(func: F) -> F:
        last_called = 0.0
        timer: Optional[asyncio.TimerHandle] = None
        cached_args: tuple = ()
        cached_kwargs: Dict = {}

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            nonlocal last_called, timer, cached_args, cached_kwargs

            current_time = time.time()
            cached_args = args
            cached_kwargs = kwargs

            # Cancel previous timer if it exists
            if timer:
                timer.cancel()

            # Update last called time
            last_called = current_time

            async def delayed_call() -> None:
                await asyncio.sleep(wait)
                if time.time() - last_called >= wait:
                    func(*cached_args, **cached_kwargs)

            # Schedule new timer
            timer = asyncio.create_task(delayed_call())  # type: ignore

        return wrapper  # type: ignore

    return decorator


def throttle(rate: float) -> Callable[[F], F]:
    """
    Decorator to throttle function calls to specified rate.

    Args:
        rate: Maximum calls per second

    Returns:
        Callable: Decorated function
    """
    min_interval = 1.0 / rate

    def decorator(func: F) -> F:
        last_called = 0.0

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            nonlocal last_called

            current_time = time.time()
            elapsed = current_time - last_called

            if elapsed < min_interval:
                # Too soon, skip call
                logger.debug(f"Throttled call to {func.__name__}")
                return None

            last_called = current_time
            return func(*args, **kwargs)

        return wrapper  # type: ignore

    return decorator


async def batch_flush(
    buffer: List[Any], every_secs: float, flush_func: Callable[[List[Any]], Any]
) -> None:
    """
    Coroutine pattern for batch processing with timed flushes.

    Args:
        buffer: List to store items
        every_secs: Flush interval in seconds
        flush_func: Function to call with buffered items
    """
    while True:
        if buffer:
            try:
                await flush_func(buffer.copy())
                buffer.clear()
            except Exception as e:
                logger.error(f"Error flushing buffer: {e}")

        await asyncio.sleep(every_secs)


class RateLimitedRunner:
    """Rate-limited execution manager for plugins."""

    def __init__(self, name: str, rate_limit: float = 2.0):
        """
        Initialize rate limiter.

        Args:
            name: Name for logging
            rate_limit: Maximum calls per second
        """
        self.name = name
        self.min_interval = 1.0 / rate_limit
        self.last_called = 0.0
        self.call_history: deque = deque(maxlen=100)

    def can_run(self) -> bool:
        """Check if execution is allowed."""
        current_time = time.time()
        elapsed = current_time - self.last_called

        if elapsed < self.min_interval:
            logger.warning(
                f"Plugin {self.name} exceeded rate limit "
                f"({1.0/self.min_interval:.1f}/sec)"
            )
            return False

        return True

    def record_call(self) -> None:
        """Record successful execution."""
        self.last_called = time.time()
        self.call_history.append(self.last_called)

    def get_call_count(self, window_secs: float = 60.0) -> int:
        """
        Get number of calls in recent time window.

        Args:
            window_secs: Time window in seconds

        Returns:
            int: Number of calls in window
        """
        current_time = time.time()
        return sum(1 for t in self.call_history if current_time - t <= window_secs)


def rate_limited_plugin_runner(
    plugin_name: str, rate_limit: float = 2.0
) -> Callable[[F], F]:
    """
    Decorator for rate-limited plugin execution.

    Args:
        plugin_name: Plugin name for logging
        rate_limit: Maximum calls per second

    Returns:
        Callable: Decorated function
    """
    limiter = RateLimitedRunner(plugin_name, rate_limit)

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not limiter.can_run():
                return None

            result = func(*args, **kwargs)
            limiter.record_call()
            return result

        return wrapper  # type: ignore

    return decorator
