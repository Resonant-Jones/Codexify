"""
SafeGuard Module
--------------
Centralized protection mechanisms for rate limiting, throttling, and resource management.
"""

import asyncio
import functools
import logging
from typing import Any, Callable, Dict, Optional, TypeVar

from guardian.config import Config
from guardian.utils.async_final import rate_limited, debounced, throttled
from guardian.cache import memoize_to_disk, lru_cache_safe

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Type variables
F = TypeVar("F", bound=Callable[..., Any])


class SafeGuardManager:
    """Manages system-wide safety mechanisms."""

    def __init__(self):
        """Initialize safety manager."""
        self.model_call_count = 0
        self.last_reset = 0.0
        self.lock = asyncio.Lock()

    def can_make_model_call(self) -> bool:
        """Check if model call is allowed under current rate limits."""
        import time

        current_time = time.time()

        # Reset counter after a minute
        if current_time - self.last_reset >= 60:
            self.model_call_count = 0
            self.last_reset = current_time

        return self.model_call_count < Config.MAX_MODEL_CALLS_PER_MIN

    async def increment_model_calls(self) -> None:
        """Safely increment model call counter."""
        async with self.lock:
            self.model_call_count += 1


# Global manager instance
safe_guard = SafeGuardManager()


def safe_model_call(func: F) -> F:
    """
    Decorator for protecting model API calls.

    Args:
        func: Function to protect

    Returns:
        Wrapped function with rate limiting
    """

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        if not safe_guard.can_make_model_call():
            logger.warning("Model call rate limit exceeded")
            return None

        try:
            await safe_guard.increment_model_calls()
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Model call failed: {e}")
            return None

    return wrapper  # type: ignore


def safe_plugin_execution(
    rate: float = Config().DEFAULT_RATE_LIMIT,
) -> Callable[[F], F]:
    """
    Combined decorator for safe plugin execution.

    Args:
        rate: Maximum calls per second

    Returns:
        Decorator function
    """

    def decorator(func: F) -> F:
        # Use a live instance for settings resolution
        settings = Config()
        # Apply rate limiting
        rate_limited_func = rate_limited(
            "plugin_execution",
            rate=rate if not settings.SAFE_MODE else settings.SAFE_MODE_RATE_LIMIT,
        )(func)
        # Add caching if enabled
        if settings.CACHE_ENABLED:
            cached_func = lru_cache_safe(maxsize=100, expire=300)(rate_limited_func)
            return cached_func  # type: ignore
        return rate_limited_func  # type: ignore

    return decorator


def safe_memory_query(func: F) -> F:
    """
    Decorator for protecting memory queries.

    Args:
        func: Function to protect

    Returns:
        Protected function
    """
    # Apply disk caching
    cached_func = memoize_to_disk(expire=3600)(func)

    # Add rate limiting
    rate_limited_func = rate_limited("memory_query", rate=5.0)(  # 5 queries per second
        cached_func
    )

    return rate_limited_func  # type: ignore


def debounced_input(wait: float = 0.5) -> Callable[[F], F]:
    """
    Decorator for debouncing rapid input.

    Args:
        wait: Debounce wait time in seconds

    Returns:
        Decorator function
    """
    return debounced(wait)


def throttled_operation(rate: float = 2.0) -> Callable[[F], F]:
    """
    Decorator for throttling operations.

    Args:
        rate: Maximum operations per second

    Returns:
        Decorator function
    """
    return throttled(rate)


# Convenience aliases
model_call = safe_model_call
plugin_execution = safe_plugin_execution
memory_query = safe_memory_query
debounce = debounced_input
throttle = throttled_operation
