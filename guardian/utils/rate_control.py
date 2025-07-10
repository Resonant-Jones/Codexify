"""
Rate Control Module
----------------
Async-aware rate limiting, debouncing, and throttling.
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
AsyncF = TypeVar("AsyncF", bound=Callable[..., Awaitable[Any]])


class RateLimiter:
    """Thread-safe rate limiter."""

    def __init__(self, rate_limit: float):
        """Initialize rate limiter."""
        self.min_interval = 1.0 / rate_limit
        self.last_called = 0.0
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


class Debouncer:
    """Async debouncer."""

    def __init__(self, wait: float):
        """Initialize debouncer."""
        self.wait = wait
        self.lock = asyncio.Lock()
        self.last_call = 0.0
        self.scheduled_call: Optional[asyncio.Task] = None
        self.current_args: Any = None
        self.current_kwargs: Any = None

    async def __call__(
        self, func: Callable[..., Awaitable[Any]], *args: Any, **kwargs: Any
    ) -> Any:
        """Execute debounced function."""
        async with self.lock:
            self.last_call = time.time()
            self.current_args = args
            self.current_kwargs = kwargs

            # Cancel previous scheduled call
            if self.scheduled_call and not self.scheduled_call.done():
                self.scheduled_call.cancel()

            # Schedule new call
            self.scheduled_call = asyncio.create_task(self._execute(func))

            try:
                return await self.scheduled_call
            except asyncio.CancelledError:
                return None

    async def _execute(self, func: Callable[..., Awaitable[Any]]) -> Any:
        """Execute after wait period."""
        await asyncio.sleep(self.wait)

        async with self.lock:
            if time.time() - self.last_call >= self.wait:
                return await func(*self.current_args, **self.current_kwargs)


class Throttler:
    """Async throttler."""

    def __init__(self, rate: float):
        """Initialize throttler."""
        self.min_interval = 1.0 / rate
        self.last_called = 0.0
        self.lock = asyncio.Lock()

    async def __call__(
        self, func: Callable[..., Awaitable[Any]], *args: Any, **kwargs: Any
    ) -> Any:
        """Execute throttled function."""
        async with self.lock:
            current_time = time.time()
            elapsed = current_time - self.last_called

            if elapsed < self.min_interval:
                return None

            self.last_called = current_time
            return await func(*args, **kwargs)


def rate_limited(name: str, rate: float) -> Callable[[AsyncF], AsyncF]:
    """Rate limiting decorator."""
    limiters: Dict[str, RateLimiter] = {}

    def get_limiter(key: str) -> RateLimiter:
        if key not in limiters:
            limiters[key] = RateLimiter(rate)
        return limiters[key]

    def decorator(func: AsyncF) -> AsyncF:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            limiter = get_limiter(name)
            await limiter.acquire()
            return await func(*args, **kwargs)

        return wrapper  # type: ignore

    return decorator


def debounced(wait: float) -> Callable[[AsyncF], AsyncF]:
    """Debouncing decorator."""
    debouncers: Dict[str, Debouncer] = {}

    def decorator(func: AsyncF) -> AsyncF:
        key = func.__name__
        if key not in debouncers:
            debouncers[key] = Debouncer(wait)

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await debouncers[key](func, *args, **kwargs)

        return wrapper  # type: ignore

    return decorator


def throttled(rate: float) -> Callable[[AsyncF], AsyncF]:
    """Throttling decorator."""
    throttlers: Dict[str, Throttler] = {}

    def decorator(func: AsyncF) -> AsyncF:
        key = func.__name__
        if key not in throttlers:
            throttlers[key] = Throttler(rate)

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await throttlers[key](func, *args, **kwargs)

        return wrapper  # type: ignore

    return decorator


# Convenience aliases
rate_limited_plugin = rate_limited
batch_processor = debounced
