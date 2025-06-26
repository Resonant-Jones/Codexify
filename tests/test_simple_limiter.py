"""
Simple Rate Limiter Tests
----------------------
Basic tests for rate limiting functionality.
"""

import asyncio
import time
import pytest

from guardian.utils.rate_limiter import SimpleRateLimiter, rate_limit

@pytest.mark.asyncio
async def test_simple_rate_limit():
    """Test basic rate limiting."""
    limiter = SimpleRateLimiter(rate=5.0)  # 5 ops/sec
    timestamps = []
    
    # Make several acquisitions
    for _ in range(3):
        await limiter.acquire()
        timestamps.append(time.time())
    
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

@pytest.mark.asyncio
async def test_decorator():
    """Test rate limit decorator."""
    timestamps = []
    
    @rate_limit(2.0)  # 2 ops/sec
    async def test_func():
        timestamps.append(time.time())
    
    # Make several calls
    for _ in range(3):
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

@pytest.mark.asyncio
async def test_concurrent():
    """Test concurrent rate limiting."""
    limiter = SimpleRateLimiter(rate=10.0)  # 10 ops/sec
    results = []
    
    async def worker():
        await limiter.acquire()
        results.append(time.time())
    
    # Launch concurrent tasks
    tasks = [worker() for _ in range(5)]
    await asyncio.gather(*tasks)
    
    # Sort timestamps
    results.sort()
    
    # Check intervals
    intervals = [
        results[i+1] - results[i]
        for i in range(len(results)-1)
    ]
    
    # Should maintain minimum interval of 0.1 seconds
    min_interval = 0.1  # 10 ops/sec = 0.1s between ops
    assert all(i >= min_interval * 0.9 for i in intervals), (
        f"Intervals should be >= {min_interval}s (with 10% tolerance)"
    )

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=strict"])
