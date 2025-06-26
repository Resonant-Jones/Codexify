"""
Global Rate Limiting Tests
----------------------
Tests for system-wide rate limiting coordination.
"""

import asyncio
import time
import pytest

from guardian.utils.system_rate_limiter import RateLimiter, rate_limit
from guardian.config import Config

@pytest.mark.asyncio
async def test_coordinated_limiting():
    """Test rate limiting coordination across multiple limiters."""
    limiter1 = RateLimiter(rate=10.0)  # 10 ops/sec
    limiter2 = RateLimiter(rate=10.0)  # 10 ops/sec
    results = []
    
    async def worker(limiter: RateLimiter, worker_id: int):
        for i in range(3):
            await limiter.acquire()
            results.append((time.time(), worker_id, i))
            await asyncio.sleep(0.05)  # Simulate work
    
    # Run workers concurrently
    tasks = [
        worker(limiter1, 1),
        worker(limiter2, 2)
    ]
    await asyncio.gather(*tasks)
    
    # Sort by timestamp
    results.sort(key=lambda x: x[0])
    timestamps = [r[0] for r in results]
    
    # Check intervals
    intervals = [
        timestamps[i+1] - timestamps[i]
        for i in range(len(timestamps)-1)
    ]
    
    # System-wide rate should be enforced
    min_interval = 0.1  # Combined rate of 10 ops/sec
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
async def test_recovery():
    """Test rate limiter recovery after bursts."""
    limiter = RateLimiter(rate=5.0)  # 5 ops/sec
    timestamps = []
    
    # Initial burst
    for _ in range(3):
        await limiter.acquire()
        timestamps.append(time.time())
    
    # Wait for recovery
    await asyncio.sleep(1.0)
    
    # Second burst
    for _ in range(3):
        await limiter.acquire()
        timestamps.append(time.time())
    
    # Check intervals within each burst
    def check_burst(start_idx: int):
        burst_intervals = [
            timestamps[i+1] - timestamps[i]
            for i in range(start_idx, start_idx + 2)
        ]
        min_interval = 0.2  # 5 ops/sec = 0.2s between ops
        assert all(i >= min_interval * 0.9 for i in burst_intervals), (
            f"Burst intervals should be >= {min_interval}s "
            "(with 10% tolerance)"
        )
    
    check_burst(0)  # First burst
    check_burst(3)  # Second burst

@pytest.mark.asyncio
async def test_concurrent_load():
    """Test rate limiting under concurrent load."""
    limiter = RateLimiter(rate=20.0)  # 20 ops/sec
    results = []
    errors = []
    
    async def worker(worker_id: int):
        try:
            for i in range(5):
                await limiter.acquire()
                results.append((time.time(), worker_id, i))
                await asyncio.sleep(0.05)  # Simulate work
        except Exception as e:
            errors.append(e)
    
    # Launch concurrent workers
    workers = [worker(i) for i in range(5)]
    await asyncio.gather(*workers)
    
    assert not errors, f"Concurrent test produced errors: {errors}"
    
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
