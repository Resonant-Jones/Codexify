"""
Async Control Module
-----------------
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


class AsyncRateLimiter:
    """Thread-safe async rate limiter."""

    def __init__(self, rate: float):
        """Initialize rate limiter."""
        self.min_interval = 1.0 / rate
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


class AsyncDebouncer:
    """Async debouncer with proper cancellation."""

    def __init__(self, wait: float):
        """Initialize debouncer."""
        self.wait = wait
        self.lock = asyncio.Lock()
        self.timer: Optional[asyncio.Task] = None
        self.future: Optional[asyncio.Future] = None
        self.args: Any = None
        self.kwargs: Any = None

    def _cancel_timer(self) -> None:
        """Cancel existing timer if any."""
        if self.timer and not self.timer.done():
            self.timer.cancel()
        if self.future and not self.future.done():
            self.future.set_result(None)

    async def _execute(self, func: Callable[..., Awaitable[Any]]) -> None:
        """Execute the debounced function."""
        try:
            await asyncio.sleep(self.wait)
            result = await func(*self.args, **self.kwargs)
            if self.future and not self.future.done():
                self.future.set_result(result)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            if self.future and not self.future.done():
                self.future.set_exception(e)

    async def __call__(
        self, func: Callable[..., Awaitable[Any]], *args: Any, **kwargs: Any
    ) -> Any:
        """Call the debounced function."""
        async with self.lock:
            self._cancel_timer()

            self.args = args
            self.kwargs = kwargs
            self.future = asyncio.Future()

            self.timer = asyncio.create_task(self._execute(func))

            return await self.future


class AsyncThrottler:
    """Async throttler with proper timing."""

    def __init__(self, rate: float):
        """Initialize throttler."""
        self.min_interval = 1.0 / rate
        self.last_called = 0.0
        self.lock = asyncio.Lock()

    async def __call__(
        self, func: Callable[..., Awaitable[Any]], *args: Any, **kwargs: Any
    ) -> Any:
        """Call the throttled function."""
        async with self.lock:
            current_time = time.time()
            elapsed = current_time - self.last_called

            if elapsed < self.min_interval:
                return None

            self.last_called = current_time
            return await func(*args, **kwargs)


def rate_limited(name: str, rate: float) -> Callable[[AsyncF], AsyncF]:
    """Rate limiting decorator."""
    limiters: Dict[str, AsyncRateLimiter] = {}

    def get_limiter(key: str) -> AsyncRateLimiter:
        if key not in limiters:
            limiters[key] = AsyncRateLimiter(rate)
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
    debouncers: Dict[str, AsyncDebouncer] = {}

    def decorator(func: AsyncF) -> AsyncF:
        key = func.__name__
        if key not in debouncers:
            debouncers[key] = AsyncDebouncer(wait)

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await debouncers[key](func, *args, **kwargs)

        return wrapper  # type: ignore

    return decorator


def throttled(rate: float) -> Callable[[AsyncF], AsyncF]:
    """Throttling decorator."""
    throttlers: Dict[str, AsyncThrottler] = {}

    def decorator(func: AsyncF) -> AsyncF:
        key = func.__name__
        if key not in throttlers:
            throttlers[key] = AsyncThrottler(rate)

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await throttlers[key](func, *args, **kwargs)

        return wrapper  # type: ignore

    return decorator


# Convenience aliases
rate_limited_plugin = rate_limited
batch_processor = debounced
