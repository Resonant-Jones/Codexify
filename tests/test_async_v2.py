"""
Async Control V2 Tests
------------------
Tests for improved async rate limiting, debouncing, and throttling.
"""

import asyncio
import logging
import time
from typing import List

import pytest

pytestmark = pytest.mark.asyncio

from guardian.utils.async_control_v2 import (
    rate_limited,
    debounced,
    throttled
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.mark.asyncio
async def test_rate_limiting():
    """Test rate limiting."""
    call_times: List[float] = []
    
    @rate_limited("test", rate=2.0)
    async def rate_limited_func() -> None:
        call_times.append(time.time())
        await asyncio.sleep(0.1)  # Simulate work
    
    # Make rapid calls
    tasks = [rate_limited_func() for _ in range(5)]
    await asyncio.gather(*tasks)
    
    # Verify rate limiting
    intervals = [
        call_times[i+1] - call_times[i]
        for i in range(len(call_times)-1)
    ]
    assert all(interval >= 0.5 for interval in intervals), f"Intervals: {intervals}"

@pytest.mark.asyncio
async def test_debounce():
    """Test debouncing."""
    call_count = 0
    last_value = None
    
    @debounced(wait=0.5)
    async def debounced_func(value: int) -> int:
        nonlocal call_count, last_value
        call_count += 1
        last_value = value
        await asyncio.sleep(0.1)  # Simulate work
        return value
    
    # Make rapid calls
    values = []
    for i in range(5):
        result = await debounced_func(i)
        values.append(result)
        await asyncio.sleep(0.1)
    
    # Wait for final debounced call
    await asyncio.sleep(0.6)
    
    # Should only be called once with last value
    assert call_count == 1, f"Expected 1 call but got {call_count}"
    assert last_value == 4, f"Expected last value 4 but got {last_value}"
    assert all(v is None for v in values[:-1]), "Intermediate calls should return None"
    assert values[-1] == 4, "Final call should return last value"

@pytest.mark.asyncio
async def test_throttle():
    """Test throttling."""
    call_times: List[float] = []
    results: List[bool] = []
    
    @throttled(rate=2.0)
    async def throttled_func() -> bool:
        call_times.append(time.time())
        await asyncio.sleep(0.1)  # Simulate work
        return True
    
    # Make rapid calls
    for _ in range(5):
        result = await throttled_func()
        results.append(result is not None)
        await asyncio.sleep(0.1)
    
    # Verify throttling
    successful_calls = len([r for r in results if r])
    assert 2 <= successful_calls <= 3, f"Expected 2-3 successful calls, got {successful_calls}"
    
    if len(call_times) > 1:
        intervals = [
            call_times[i+1] - call_times[i]
            for i in range(len(call_times)-1)
        ]
        assert all(interval >= 0.5 for interval in intervals), f"Intervals: {intervals}"

@pytest.mark.asyncio
async def test_concurrent_rate_limiting():
    """Test rate limiting under concurrent load."""
    results = []
    start_time = time.time()
    
    @rate_limited("concurrent_test", rate=5.0)
    async def limited_func(i: int) -> int:
        await asyncio.sleep(0.1)  # Simulate work
        return i
    
    # Launch many concurrent tasks
    tasks = [limited_func(i) for i in range(10)]
    results = await asyncio.gather(*tasks)
    duration = time.time() - start_time
    
    # Verify results and timing
    assert len(results) == 10, "All tasks should complete"
    assert duration >= 2.0, f"Duration {duration} should be >= 2.0 seconds"
    assert list(results) == list(range(10)), "Results should maintain order"

@pytest.mark.asyncio
async def test_debounce_cancellation():
    """Test debounce cancellation behavior."""
    call_count = 0
    
    @debounced(wait=0.5)
    async def debounced_func() -> int:
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.1)  # Simulate work
        return call_count
    
    # Start multiple calls that should be debounced
    task1 = asyncio.create_task(debounced_func())
    await asyncio.sleep(0.1)
    task2 = asyncio.create_task(debounced_func())
    await asyncio.sleep(0.1)
    task3 = asyncio.create_task(debounced_func())
    
    # Wait for all tasks
    results = await asyncio.gather(task1, task2, task3)
    
    # Only the last call should execute
    assert call_count == 1, f"Should only execute once, got {call_count} executions"
    assert all(r is None for r in results[:-1]), "Cancelled calls should return None"
    assert results[-1] == 1, "Last call should return result"

@pytest.mark.asyncio
async def test_throttle_bursts():
    """Test throttle behavior with bursts."""
    successes = []
    
    @throttled(rate=2.0)
    async def throttled_func() -> bool:
        successes.append(True)
        await asyncio.sleep(0.1)  # Simulate work
        return True
    
    # Test burst behavior
    for _ in range(3):
        # Burst of calls
        tasks = [throttled_func() for _ in range(5)]
        results = await asyncio.gather(*tasks)
        successful = len([r for r in results if r is not None])
        assert 1 <= successful <= 2, f"Expected 1-2 successful calls per burst, got {successful}"
        await asyncio.sleep(1.0)  # Wait for throttle to reset
    
    # Should allow approximately 2 calls per second per burst
    total_successes = len(successes)
    assert 5 <= total_successes <= 7, f"Expected 5-7 total successful calls, got {total_successes}"

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=strict"])
