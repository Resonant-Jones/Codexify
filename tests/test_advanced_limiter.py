"""
Advanced Rate Limiter Tests
-----------------------
Edge cases and error handling tests.
"""

import asyncio
import time
import pytest

from guardian.utils.rate_limiter import SimpleRateLimiter, rate_limit

@pytest.mark.asyncio
async def test_error_propagation():
    """Test that errors propagate correctly through rate limiter."""
    error_count = 0
    
    @rate_limit(5.0)  # 5 ops/sec
    async def failing_func():
        nonlocal error_count
        error_count += 1
        raise ValueError("Test error")
    
    # Try multiple calls
    for _ in range(3):
        with pytest.raises(ValueError):
            await failing_func()
    
    # Should allow all error calls through
    assert error_count == 3, "All error calls should be executed"

@pytest.mark.asyncio
async def test_high_frequency():
    """Test rate limiting at high frequencies."""
    limiter = SimpleRateLimiter(rate=50.0)  # 50 ops/sec
    timestamps = []
    
    # Make rapid acquisitions
    for _ in range(10):
        await limiter.acquire()
        timestamps.append(time.time())
    
    # Check total duration
    duration = timestamps[-1] - timestamps[0]
    expected_duration = 9 * (1.0 / 50.0)  # Time for 9 intervals at 50 ops/sec
    
    assert duration >= expected_duration * 0.9, (
        f"Duration {duration} should be >= {expected_duration}s "
        "(with 10% tolerance)"
    )

@pytest.mark.asyncio
async def test_mixed_durations():
    """Test rate limiting with varying operation durations."""
    timestamps = []
    
    @rate_limit(4.0)  # 4 ops/sec
    async def variable_func(sleep_time: float):
        timestamps.append(time.time())
        await asyncio.sleep(sleep_time)
    
    # Mix of fast and slow operations
    await variable_func(0.1)  # Fast
    await variable_func(0.3)  # Slow
    await variable_func(0.1)  # Fast
    
    # Check intervals
    intervals = [
        timestamps[i+1] - timestamps[i]
        for i in range(len(timestamps)-1)
    ]
    
    # Should maintain minimum interval regardless of operation duration
    min_interval = 0.25  # 4 ops/sec = 0.25s between ops
    assert all(i >= min_interval * 0.9 for i in intervals), (
        f"Intervals should be >= {min_interval}s (with 10% tolerance)"
    )

@pytest.mark.asyncio
async def test_task_cancellation():
    """Test rate limiting behavior with task cancellation."""
    limiter = SimpleRateLimiter(rate=2.0)  # 2 ops/sec
    
    async def slow_task():
        await limiter.acquire()
        await asyncio.sleep(1.0)
        return "completed"
    
    # Start task and cancel it
    task = asyncio.create_task(slow_task())
    await asyncio.sleep(0.1)  # Let it start
    task.cancel()
    
    try:
        await task
    except asyncio.CancelledError:
        pass
    
    # Should be able to acquire immediately after cancellation
    start_time = time.time()
    await limiter.acquire()
    duration = time.time() - start_time
    
    assert duration < 0.5, (
        "Should not wait full interval after cancellation"
    )

@pytest.mark.asyncio
async def test_concurrent_bursts():
    """Test handling concurrent bursts of requests."""
    limiter = SimpleRateLimiter(rate=10.0)  # 10 ops/sec
    results = []
    
    async def worker(id: int):
        for i in range(3):
            await limiter.acquire()
            results.append((id, i, time.time()))
            await asyncio.sleep(0.05)  # Simulate work
    
    # Launch concurrent workers
    workers = [worker(i) for i in range(3)]
    await asyncio.gather(*workers)
    
    # Sort by timestamp
    results.sort(key=lambda x: x[2])
    
    # Check intervals between operations
    intervals = [
        results[i+1][2] - results[i][2]
        for i in range(len(results)-1)
    ]
    
    min_interval = 0.1  # 10 ops/sec = 0.1s between ops
    assert all(i >= min_interval * 0.9 for i in intervals), (
        f"Intervals should be >= {min_interval}s (with 10% tolerance)"
    )

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=strict"])
