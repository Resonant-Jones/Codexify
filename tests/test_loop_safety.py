"""
Event Loop Safety Tests
-------------------
Tests for event loop safety in rate limiting.
"""

import asyncio
import time
import pytest

from guardian.utils.event_safe_limiter import RateLimiter, rate_limit
from guardian.config import Config

@pytest.mark.asyncio
async def test_basic_rate_limit():
    """Test basic rate limiting in current loop."""
    limiter = RateLimiter(rate=10.0)  # 10 ops/sec
    timestamps = []
    
    for _ in range(3):
        await limiter.acquire()
        timestamps.append(time.time())
    
    intervals = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]
    min_interval = 0.1  # 10 ops/sec = 0.1s between ops
    
    assert all(i >= min_interval * 0.9 for i in intervals), (
        f"Intervals should be >= {min_interval}s (with 10% tolerance)"
    )

@pytest.mark.asyncio
async def test_safe_mode_limit():
    """Test rate limiting in safe mode."""
    try:
        Config.SAFE_MODE = True
        Config.SAFE_MODE_RATE_LIMIT = 2.0  # 2 ops/sec
        
        limiter = RateLimiter(rate=10.0)
        timestamps = []
        
        for _ in range(3):
            await limiter.acquire()
            timestamps.append(time.time())
        
        intervals = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]
        min_interval = 1.0 / Config.SAFE_MODE_RATE_LIMIT
        
        assert all(i >= min_interval * 0.9 for i in intervals), (
            f"Safe mode intervals should be >= {min_interval}s (with 10% tolerance)"
        )
    finally:
        Config.SAFE_MODE = False

@pytest.mark.asyncio
async def test_loop_isolation():
    """Test rate limiter isolation between event loops."""
    async def run_in_new_loop():
        # This runs in a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Try to use limiter from parent loop
            limiter = RateLimiter(rate=10.0)
            await limiter.acquire()
            return None
        except RuntimeError as e:
            return e
        finally:
            loop.close()
    
    # Run in task with new loop
    error = await run_in_new_loop()
    assert error is not None, "Should have raised RuntimeError"
    assert "event loop" in str(error), f"Wrong error: {error}"

@pytest.mark.asyncio
async def test_concurrent_workers():
    """Test concurrent workers each with their own limiter."""
    results = []
    errors = []
    
    async def worker(worker_id: int):
        try:
            # Each worker gets its own limiter
            limiter = RateLimiter(rate=20.0)
            for i in range(3):
                await limiter.acquire()
                results.append((time.time(), worker_id))
                await asyncio.sleep(0.05)
        except Exception as e:
            errors.append(e)
    
    workers = [worker(i) for i in range(3)]
    await asyncio.gather(*workers)
    
    assert not errors, f"Workers produced errors: {errors}"
    
    # Verify timing
    results.sort(key=lambda x: x[0])
    timestamps = [r[0] for r in results]
    intervals = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]
    min_interval = 0.05  # 20 ops/sec = 0.05s between ops
    
    assert all(i >= min_interval * 0.9 for i in intervals), (
        f"Intervals should be >= {min_interval}s (with 10% tolerance)"
    )

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=strict"])
