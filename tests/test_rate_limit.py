"""
Rate Limit Tests
-------------
Simple tests for rate limiting functionality.
"""

import asyncio
import time
import pytest

pytestmark = pytest.mark.asyncio

from guardian.utils.rate_limiter import rate_limit

@pytest.mark.asyncio
async def test_rate_limit():
    """Test basic rate limiting."""
    timestamps = []
    
    @rate_limit(2.0)  # 2 operations per second
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

@pytest.mark.asyncio
async def test_concurrent_calls():
    """Test rate limiting with concurrent calls."""
    timestamps = []
    
    @rate_limit(5.0)  # 5 operations per second
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

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=strict"])
