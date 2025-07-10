"""
Async Core Module
--------------
Core async utilities for rate limiting, debouncing, and throttling.
"""

import asyncio
import functools
import logging
import time
from typing import Any, Callable, Dict, List, TypeVar, Optional, Awaitable

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
        self.queue: List[asyncio.Future] = []

    async def acquire(self) -> None:
        """Acquire rate limit slot."""
        future = asyncio.Future()

        async with self.lock:
            self.queue.append(future)

            if len(self.queue) == 1:  # First in queue
                current_time = time.time()
                elapsed = current_time - self.last_called

                if elapsed < self.min_interval:
                    wait_time = self.min_interval - elapsed
                    await asyncio.sleep(wait_time)

                self.last_called = time.time()
                future.set_result(None)
            else:
                # Schedule next execution
                asyncio.create_task(self._process_queue())

        await future

    async def _process_queue(self) -> None:
        """Process queued requests."""
        while True:
            async with self.lock:
                if not self.queue:
                    break

                current_time = time.time()
                elapsed = current_time - self.last_called

                if elapsed < self.min_interval:
                    await asyncio.sleep(self.min_interval - elapsed)

                self.last_called = time.time()
                future = self.queue.pop(0)
                future.set_result(None)


class AsyncDebouncer:
    """Async debouncer with proper cancellation."""

    def __init__(self, wait: float):
        """Initialize debouncer."""
        self.wait = wait
        self.lock = asyncio.Lock()
        self.timer: Optional[asyncio.Task] = None
        self.current_args: Any = None
        self.current_kwargs: Any = None
        self.pending_futures: List[asyncio.Future] = []

    async def __call__(
        self, func: Callable[..., Awaitable[Any]], *args: Any, **kwargs: Any
    ) -> Any:
        """Execute debounced function call."""
        future = asyncio.Future()

        async with self.lock:
            # Cancel existing timer
            if self.timer and not self.timer.done():
                self.timer.cancel()

                # Resolve pending futures with None
                for f in self.pending_futures:
                    if not f.done():
                        f.set_result(None)
                self.pending_futures.clear()

            # Update current call info
            self.current_args = args
            self.current_kwargs = kwargs
            self.pending_futures.append(future)

            # Start new timer
            self.timer = asyncio.create_task(self._execute(func))

        return await future

    async def _execute(self, func: Callable[..., Awaitable[Any]]) -> None:
        """Execute after wait period."""
        try:
            await asyncio.sleep(self.wait)

            async with self.lock:
                result = await func(*self.current_args, **self.current_kwargs)

                # Resolve all pending futures with result
                for future in self.pending_futures:
                    if not future.done():
                        future.set_result(result)
                self.pending_futures.clear()

        except asyncio.CancelledError:
            pass
        except Exception as e:
            for future in self.pending_futures:
                if not future.done():
                    future.set_exception(e)


class AsyncThrottler:
    """Async throttler with burst control."""

    def __init__(self, rate: float):
        """Initialize throttler."""
        self.min_interval = 1.0 / rate
        self.last_called = 0.0
        self.lock = asyncio.Lock()
        self.call_count = 0
        self.reset_timer: Optional[asyncio.Task] = None

    async def __call__(
        self, func: Callable[..., Awaitable[Any]], *args: Any, **kwargs: Any
    ) -> Any:
        """Execute throttled function."""
        async with self.lock:
            current_time = time.time()
            elapsed = current_time - self.last_called

            # Reset call count after interval
            if elapsed >= self.min_interval:
                self.call_count = 0
                self.last_called = current_time

            # Allow call if within rate limit
            if self.call_count < int(1 / self.min_interval):
                self.call_count += 1
                return await func(*args, **kwargs)

            return None


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
            await get_limiter(name).acquire()
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
