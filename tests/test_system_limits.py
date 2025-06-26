"""
System-Wide Rate Limiting Tests
---------------------------
Tests for system-wide rate limiting coordination.
"""

import asyncio
import time
import pytest

from guardian.utils.rate_limiter import SimpleRateLimiter, rate_limit
from guardian.config import Config

@pytest.mark.asyncio
async def test_system_wide_limit():
    """Test system-wide rate limiting across multiple limiters."""
    # Create multiple limiters
    limiter1 = SimpleRateLimiter(rate=10.0)  # 10 ops/sec
    limiter2 = SimpleRateLimiter(rate=10.0)  # 10 ops/sec
    timestamps = []
    
    async def worker(limiter: SimpleRateLimiter):
        for _ in range(3):
            await limiter.acquire()
            timestamps.append(time.time())
            await asyncio.sleep(0.05)  # Simulate work
    
    # Run workers concurrently using both limiters
    tasks = [
        worker(limiter1),
        worker(limiter2)
    ]
    await asyncio.gather(*tasks)
    
    # Sort timestamps
    timestamps.sort()
    
    # Check intervals
    intervals = [
        timestamps[i+1] - timestamps[i]
        for i in range(len(timestamps)-1)
    ]
    
    # Each limiter allows 10 ops/sec, so combined should maintain
    # minimum interval of 0.1 seconds
    min_interval = 0.1
    assert all(i >= min_interval * 0.9 for i in intervals), (
        f"Intervals should be >= {min_interval}s (with 10% tolerance)"
    )

@pytest.mark.asyncio
async def test_safe_mode_limiting():
    """Test rate limiting in safe mode."""
    try:
        # Enable safe mode
        Config.SAFE_MODE = True
        
        limiter = SimpleRateLimiter(rate=10.0)  # 10 ops/sec
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
        
        # In safe mode, rate should be reduced
        safe_rate = Config.SAFE_MODE_RATE_LIMIT
        min_interval = 1.0 / safe_rate
        
        assert all(i >= min_interval * 0.9 for i in intervals), (
            f"Safe mode intervals should be >= {min_interval}s "
            "(with 10% tolerance)"
        )
    finally:
        # Reset safe mode
        Config.SAFE_MODE = False

@pytest.mark.asyncio
async def test_burst_recovery():
    """Test system recovery after burst operations."""
    limiter = SimpleRateLimiter(rate=5.0)  # 5 ops/sec
    timestamps = []
    
    # Initial burst
    for _ in range(3):
        await limiter.acquire()
        timestamps.append(time.time())
    
    # Wait for system to recover
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
async def test_system_stress():
    """Test system behavior under stress."""
    limiter = SimpleRateLimiter(rate=20.0)  # 20 ops/sec
    results = []
    errors = []
    
    async def stress_worker(id: int):
        try:
            for i in range(5):
                await limiter.acquire()
                results.append((id, i, time.time()))
                # Random work simulation
                await asyncio.sleep(0.05 if i % 2 == 0 else 0.1)
        except Exception as e:
            errors.append(e)
    
    # Launch many concurrent workers
    workers = [stress_worker(i) for i in range(5)]
    await asyncio.gather(*workers)
    
    assert not errors, f"Stress test produced errors: {errors}"
    
    # Sort by timestamp
    results.sort(key=lambda x: x[2])
    
    # Check intervals between operations
    intervals = [
        results[i+1][2] - results[i][2]
        for i in range(len(results)-1)
    ]
    
    min_interval = 0.05  # 20 ops/sec = 0.05s between ops
    assert all(i >= min_interval * 0.9 for i in intervals), (
        f"Intervals should be >= {min_interval}s (with 10% tolerance)"
    )

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=strict"])
