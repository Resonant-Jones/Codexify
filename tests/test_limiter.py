"""
Rate Limiter Tests
---------------
Comprehensive tests for rate limiting functionality.
"""

import asyncio
import time
import pytest

pytestmark = pytest.mark.asyncio

from guardian.utils.rate_limiter import rate_limit, SimpleRateLimiter

@pytest.fixture
async def limiter():
    """Provide a test rate limiter."""
    return SimpleRateLimiter(rate=10.0)

async def test_basic_limiting():
    """Test basic rate limiting."""
    timestamps = []
    
    @rate_limit(2.0)  # 2 ops/sec
    async def test_func():
        timestamps.append(time.time())
    
    # Make 5 calls
    for _ in range(5):
        await test_func()
    
    # Check intervals
    intervals = [
        timestamps[i+1] - timestamps[i]
        for i in range(len(timestamps)-1)
    ]
    
    # Should maintain minimum interval of 0.5 seconds
    min_interval = 0.5  # 2 ops/sec = 0.5s between ops
    assert all(i >= min_interval * 0.9 for i in intervals), (
        f"Intervals should be >= {min_interval}s (with 10% tolerance)"
    )

async def test_concurrent_limiting():
    """Test rate limiting under concurrent load."""
    timestamps = []
    
    @rate_limit(5.0)  # 5 ops/sec
    async def test_func():
        timestamps.append(time.time())
        await asyncio.sleep(0.1)  # Simulate work
    
    # Launch concurrent tasks
    tasks = [test_func() for _ in range(10)]
    await asyncio.gather(*tasks)
    
    # Sort timestamps
    timestamps.sort()
    
    # Check intervals
    intervals = [
        timestamps[i+1] - timestamps[i]
        for i in range(len(timestamps)-1)
    ]
    
    # Should maintain minimum interval of 0.2 seconds
    min_interval = 0.2  # 5 ops/sec = 0.2s between ops
    assert all(i >= min_interval * 0.9 for i in intervals), (
        f"Intervals should be >= {min_interval}s (with 10% tolerance)"
    )

async def test_direct_limiter_usage(limiter):
    """Test using rate limiter directly."""
    timestamps = []
    
    # Make several acquisitions
    for _ in range(5):
        await limiter.acquire()
        timestamps.append(time.time())
    
    # Check intervals
    intervals = [
        timestamps[i+1] - timestamps[i]
        for i in range(len(timestamps)-1)
    ]
    
    # Should maintain minimum interval of 0.1 seconds
    min_interval = 0.1  # 10 ops/sec = 0.1s between ops
    assert all(i >= min_interval * 0.9 for i in intervals), (
        f"Intervals should be >= {min_interval}s (with 10% tolerance)"
    )

async def test_error_handling():
    """Test rate limiting with errors."""
    error_count = 0
    
    @rate_limit(5.0)
    async def failing_func():
        nonlocal error_count
        error_count += 1
        raise ValueError("Test error")
    
    # Try multiple calls
    for _ in range(3):
        with pytest.raises(ValueError):
            await failing_func()
    
    # Should allow all error calls through
    assert error_count == 3

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

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=strict"])
