"""
Final Async Control Implementation
------------------------------
Production-ready async utilities with optimal performance.
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


class RateController:
    """Thread-safe rate limiter with queue management."""

    def __init__(self, rate: float):
        """Initialize rate controller."""
        self.min_interval = 1.0 / rate
        self.last_called = 0.0
        self.lock = asyncio.Lock()
        self.queue: List[asyncio.Future] = []
        self._processor: Optional[asyncio.Task] = None

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
                # Start queue processor if not running
                if not self._processor or self._processor.done():
                    self._processor = asyncio.create_task(self._process_queue())

        await future

    async def _process_queue(self) -> None:
        """Process queued requests efficiently."""
        try:
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
        finally:
            self._processor = None


class DebounceController:
    """Async debouncer with precise timing."""

    def __init__(self, wait: float):
        """Initialize debounce controller."""
        self.wait = wait
        self.lock = asyncio.Lock()
        self.timer: Optional[asyncio.Task] = None
        self.last_call = 0.0
        self.current_args: Any = None
        self.current_kwargs: Any = None
        self.current_future: Optional[asyncio.Future] = None
        self.pending_futures: List[asyncio.Future] = []

    def _cancel_timer(self) -> None:
        """Cancel existing timer and resolve pending futures."""
        if self.timer and not self.timer.done():
            self.timer.cancel()

        # Resolve pending futures with None
        for future in self.pending_futures:
            if not future.done():
                future.set_result(None)
        self.pending_futures.clear()

    async def _delayed_execute(self, func: Callable[..., Awaitable[Any]]) -> None:
        """Execute function after delay."""
        try:
            await asyncio.sleep(self.wait)

            async with self.lock:
                if time.time() - self.last_call >= self.wait:
                    result = await func(*self.current_args, **self.current_kwargs)

                    # Set result for current future
                    if self.current_future and not self.current_future.done():
                        self.current_future.set_result(result)

                    # Clear state
                    self.current_args = None
                    self.current_kwargs = None
                    self.current_future = None

        except asyncio.CancelledError:
            pass
        except Exception as e:
            if self.current_future and not self.current_future.done():
                self.current_future.set_exception(e)

    async def __call__(
        self, func: Callable[..., Awaitable[Any]], *args: Any, **kwargs: Any
    ) -> Any:
        """Execute debounced function call."""
        async with self.lock:
            self.last_call = time.time()
            self.current_args = args
            self.current_kwargs = kwargs

            # Cancel existing timer and resolve pending futures
            self._cancel_timer()

            # Create new future for this call
            self.current_future = asyncio.Future()
            self.pending_futures.append(self.current_future)

            # Start new timer
            self.timer = asyncio.create_task(self._delayed_execute(func))

            return await self.current_future


class ThrottleController:
    """Async throttler with burst control."""

    def __init__(self, rate: float):
        """Initialize throttle controller."""
        self.min_interval = 1.0 / rate
        self.last_called = 0.0
        self.lock = asyncio.Lock()
        self.call_count = 0
        self.reset_time = 0.0
        self.max_burst = 2  # Allow up to 2 calls per interval

    async def __call__(
        self, func: Callable[..., Awaitable[Any]], *args: Any, **kwargs: Any
    ) -> Any:
        """Execute throttled function call."""
        async with self.lock:
            current_time = time.time()

            # Reset after interval
            if current_time - self.reset_time >= self.min_interval:
                self.call_count = 0
                self.reset_time = current_time

            # Allow call if within burst limit
            if self.call_count < self.max_burst:
                self.call_count += 1
                self.last_called = current_time
                return await func(*args, **kwargs)

            return None


def rate_limited(name: str, rate: float) -> Callable[[AsyncF], AsyncF]:
    """Rate limiting decorator."""
    controllers: Dict[str, RateController] = {}

    def get_controller(key: str) -> RateController:
        if key not in controllers:
            controllers[key] = RateController(rate)
        return controllers[key]

    def decorator(func: AsyncF) -> AsyncF:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            await get_controller(name).acquire()
            return await func(*args, **kwargs)

        return wrapper  # type: ignore

    return decorator


def debounced(wait: float) -> Callable[[AsyncF], AsyncF]:
    """Debouncing decorator."""
    controllers: Dict[str, DebounceController] = {}

    def decorator(func: AsyncF) -> AsyncF:
        key = func.__name__
        if key not in controllers:
            controllers[key] = DebounceController(wait)

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await controllers[key](func, *args, **kwargs)

        return wrapper  # type: ignore

    return decorator


def throttled(rate: float) -> Callable[[AsyncF], AsyncF]:
    """Throttling decorator."""
    controllers: Dict[str, ThrottleController] = {}

    def decorator(func: AsyncF) -> AsyncF:
        key = func.__name__
        if key not in controllers:
            controllers[key] = ThrottleController(rate)

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await controllers[key](func, *args, **kwargs)

        return wrapper  # type: ignore

    return decorator


# Convenience aliases
rate_limited_plugin = rate_limited
batch_processor = debounced
