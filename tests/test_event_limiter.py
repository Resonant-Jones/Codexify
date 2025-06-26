"""
Event-Loop Safe Rate Limiter Tests
------------------------------
Tests for event-loop safe rate limiting implementation.
"""

import asyncio
import time
import pytest

from guardian.utils.event_safe_limiter import RateLimiter, rate_limit
from guardian.config import Config

@pytest.mark.asyncio
async def test_basic_limiting():
    """Test basic rate limiting in single event loop."""
    limiter = RateLimiter(rate=10.0)  # 10 ops/sec
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
    
    min_interval = 0.1  # 10 ops/sec = 0.1s between ops
    assert all(i >= min_interval * 0.9 for i in intervals), (
        f"Intervals should be >= {min_interval}s (with 10% tolerance)"
    )

@pytest.mark.asyncio
async def test_concurrent_workers():
    """Test rate limiting with concurrent workers."""
    results = []
    
    async def worker(worker_id: int):
        # Create limiter inside worker for proper event loop binding
        limiter = RateLimiter(rate=10.0)
        for i in range(3):
            await limiter.acquire()
            results.append((time.time(), worker_id, i))
            await asyncio.sleep(0.05)  # Simulate work
    
    # Run multiple workers
    workers = [worker(i) for i in range(3)]
    await asyncio.gather(*workers)
    
    # Sort by timestamp
    results.sort(key=lambda x: x[0])
    timestamps = [r[0] for r in results]
    
    # Check intervals
    intervals = [
        timestamps[i+1] - timestamps[i]
        for i in range(len(timestamps)-1)
    ]
    
    min_interval = 0.1  # 10 ops/sec = 0.1s between ops
    assert all(i >= min_interval * 0.9 for i in intervals), (
        f"Intervals should be >= {min_interval}s (with 10% tolerance)"
    )

@pytest.mark.asyncio
async def test_safe_mode():
    """Test rate limiting in safe mode."""
    try:
        # Enable safe mode with reduced rate
        Config.SAFE_MODE = True
        Config.SAFE_MODE_RATE_LIMIT = 2.0  # 2 ops/sec in safe mode
        
        limiter = RateLimiter(rate=10.0)  # 10 ops/sec normally
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
        
        # In safe mode, should use reduced rate
        min_interval = 1.0 / Config.SAFE_MODE_RATE_LIMIT
        assert all(i >= min_interval * 0.9 for i in intervals), (
            f"Safe mode intervals should be >= {min_interval}s "
            "(with 10% tolerance)"
        )
    finally:
        # Reset safe mode
        Config.SAFE_MODE = False

@pytest.mark.asyncio
async def test_event_loop_safety():
    """Test rate limiter event loop safety."""
    limiter = RateLimiter(rate=10.0)  # Created in test loop
    
    async def other_loop_task():
        try:
            await limiter.acquire()
            assert False, "Should have raised RuntimeError"
        except RuntimeError as e:
            assert "same event loop" in str(e)
    
    # Run task in different event loop
    other_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(other_loop)
    
    try:
        with pytest.raises(RuntimeError) as exc_info:
            await other_loop.run_until_complete(other_loop_task())
        assert "same event loop" in str(exc_info.value)
    finally:
        other_loop.close()

@pytest.mark.asyncio
async def test_high_concurrency():
    """Test rate limiting under high concurrency."""
    results = []
    errors = []
    
    async def worker(worker_id: int):
        try:
            limiter = RateLimiter(rate=20.0)  # 20 ops/sec
            for i in range(5):
                await limiter.acquire()
                results.append((time.time(), worker_id, i))
                await asyncio.sleep(0.05)  # Simulate work
        except Exception as e:
            errors.append(e)
    
    # Launch many concurrent workers
    workers = [worker(i) for i in range(5)]
    await asyncio.gather(*workers)
    
    assert not errors, f"High concurrency test produced errors: {errors}"
    
    # Sort by timestamp
    results.sort(key=lambda x: x[0])
    timestamps = [r[0] for r in results]
    
    # Check intervals
    intervals = [
        timestamps[i+1] - timestamps[i]
        for i in range(len(timestamps)-1)
    ]
    
    min_interval = 0.05  # 20 ops/sec = 0.05s between ops
    assert all(i >= min_interval * 0.9 for i in intervals), (
        f"Intervals should be >= {min_interval}s (with 10% tolerance)"
    )

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=strict"])
