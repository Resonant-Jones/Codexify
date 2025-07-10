"""
Async Control V2
-------------
Refined async utilities with improved debouncing and throttling.
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
    """Thread-safe rate limiter."""

    def __init__(self, rate: float):
        """Initialize rate controller."""
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


class DebounceState:
    """State for a debounced function."""

    def __init__(self, wait: float):
        """Initialize debounce state."""
        self.wait = wait
        self.lock = asyncio.Lock()
        self.timer: Optional[asyncio.Task] = None
        self.last_call = 0.0
        self.pending_calls: List[tuple[Any, Any, asyncio.Future]] = []
        self.executing = False

    async def schedule(
        self, func: Callable[..., Awaitable[Any]], args: Any, kwargs: Any
    ) -> Any:
        """Schedule a debounced call."""
        future = asyncio.Future()

        async with self.lock:
            self.last_call = time.time()

            # Cancel existing timer
            if self.timer and not self.timer.done():
                self.timer.cancel()

            # Clear pending calls with None
            while self.pending_calls:
                _, _, f = self.pending_calls.pop(0)
                if not f.done():
                    f.set_result(None)

            # Add new call
            self.pending_calls.append((args, kwargs, future))

            # Start new timer
            self.timer = asyncio.create_task(self._execute(func))

        return await future

    async def _execute(self, func: Callable[..., Awaitable[Any]]) -> None:
        """Execute after wait period."""
        try:
            await asyncio.sleep(self.wait)

            async with self.lock:
                if not self.pending_calls:
                    return

                # Get last pending call
                args, kwargs, future = self.pending_calls[-1]
                self.pending_calls.clear()

                # Execute function
                try:
                    result = await func(*args, **kwargs)
                    if not future.done():
                        future.set_result(result)
                except Exception as e:
                    if not future.done():
                        future.set_exception(e)

        except asyncio.CancelledError:
            pass


class ThrottleState:
    """State for a throttled function."""

    def __init__(self, rate: float):
        """Initialize throttle state."""
        self.min_interval = 1.0 / rate
        self.last_called = 0.0
        self.lock = asyncio.Lock()
        self.call_count = 0
        self.reset_time = 0.0

    async def execute(
        self, func: Callable[..., Awaitable[Any]], args: Any, kwargs: Any
    ) -> Any:
        """Execute throttled function."""
        async with self.lock:
            current_time = time.time()

            # Reset after interval
            if current_time - self.reset_time >= self.min_interval:
                self.call_count = 0
                self.reset_time = current_time

            # Check if we can execute
            if self.call_count < 2:  # Allow 2 calls per interval
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
    states: Dict[str, DebounceState] = {}

    def decorator(func: AsyncF) -> AsyncF:
        key = func.__name__
        if key not in states:
            states[key] = DebounceState(wait)

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await states[key].schedule(func, args, kwargs)

        return wrapper  # type: ignore

    return decorator


def throttled(rate: float) -> Callable[[AsyncF], AsyncF]:
    """Throttling decorator."""
    states: Dict[str, ThrottleState] = {}

    def decorator(func: AsyncF) -> AsyncF:
        key = func.__name__
        if key not in states:
            states[key] = ThrottleState(rate)

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await states[key].execute(func, args, kwargs)

        return wrapper  # type: ignore

    return decorator


# Convenience aliases
rate_limited_plugin = rate_limited
batch_processor = debounced
