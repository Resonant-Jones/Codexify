"""
Async Debounce Module
------------------
Improved async debouncing with proper cancellation.
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


class AsyncDebouncer:
    """Async debouncer with proper cancellation and result handling."""

    def __init__(self, wait: float):
        """Initialize debouncer."""
        self.wait = wait
        self.lock = asyncio.Lock()
        self.scheduled_task: Optional[asyncio.Task] = None
        self.last_call_time = 0.0
        self.current_args: Any = None
        self.current_kwargs: Any = None
        self.current_future: Optional[asyncio.Future] = None
        self.pending_futures: List[asyncio.Future] = []

    def _cancel_scheduled(self) -> None:
        """Cancel any scheduled execution."""
        if self.scheduled_task and not self.scheduled_task.done():
            self.scheduled_task.cancel()

        # Resolve any pending futures with None
        for future in self.pending_futures:
            if not future.done():
                future.set_result(None)
        self.pending_futures.clear()

    async def _delayed_execute(self, func: Callable[..., Awaitable[Any]]) -> None:
        """Execute the function after delay."""
        try:
            await asyncio.sleep(self.wait)

            async with self.lock:
                if time.time() - self.last_call_time >= self.wait:
                    # Execute function with most recent args
                    result = await func(*self.current_args, **self.current_kwargs)

                    # Set result for all pending futures
                    if self.current_future and not self.current_future.done():
                        self.current_future.set_result(result)

                    # Clear state
                    self.current_args = None
                    self.current_kwargs = None
                    self.current_future = None

        except asyncio.CancelledError:
            # Task was cancelled, futures should be resolved already
            pass
        except Exception as e:
            # Propagate error to futures
            if self.current_future and not self.current_future.done():
                self.current_future.set_exception(e)

    async def __call__(
        self, func: Callable[..., Awaitable[Any]], *args: Any, **kwargs: Any
    ) -> Any:
        """Execute debounced function call."""
        async with self.lock:
            self.last_call_time = time.time()
            self.current_args = args
            self.current_kwargs = kwargs

            # Cancel any existing scheduled execution
            self._cancel_scheduled()

            # Create new future for this call
            self.current_future = asyncio.Future()
            self.pending_futures.append(self.current_future)

            # Schedule new execution
            self.scheduled_task = asyncio.create_task(self._delayed_execute(func))

            return await self.current_future


def debounced(wait: float) -> Callable[[AsyncF], AsyncF]:
    """
    Debouncing decorator with proper async handling.

    Args:
        wait: Time to wait in seconds

    Returns:
        Callable: Decorated function
    """
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
