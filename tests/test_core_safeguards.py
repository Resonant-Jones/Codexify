"""
Core Safeguard Tests
-----------------
Basic tests for rate limiting and throttling functionality.
"""

import asyncio
import logging
import time
from typing import List

import pytest

pytestmark = pytest.mark.asyncio

from guardian.config import Config
from guardian.utils.safeguard import throttle, rate_limited

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.mark.asyncio
async def test_basic_throttling():
    """Test basic throttling functionality."""
    calls = []
    
    @throttle(rate=5.0)  # 5 calls per second
    async def throttled_func():
        calls.append(time.time())
        await asyncio.sleep(0.1)  # Simulate work
    
    # Make several rapid calls
    start_time = time.time()
    for _ in range(10):
        await throttled_func()
    duration = time.time() - start_time
    
    # Calculate intervals between calls
    intervals = [
        calls[i+1] - calls[i]
        for i in range(len(calls)-1)
    ]
    
    # Should take at least 2 seconds for 10 calls at 5/sec
    assert duration >= 2.0, f"Duration {duration} should be >= 2.0 seconds"
    
    # Should maintain minimum interval of 0.2 seconds
    min_interval = 1.0 / 5.0  # 5 calls per second = 0.2s between calls
    assert all(i >= min_interval for i in intervals), (
        f"All intervals should be >= {min_interval}s"
    )

@pytest.mark.asyncio
async def test_rate_limiting():
    """Test rate limiting decorator."""
    results: List[float] = []
    
    @rate_limited("test", rate=2.0)  # 2 calls per second
    async def limited_func():
        results.append(time.time())
        await asyncio.sleep(0.1)  # Simulate work
    
    # Make several rapid calls
    start_time = time.time()
    tasks = [limited_func() for _ in range(5)]
    await asyncio.gather(*tasks)
    duration = time.time() - start_time
    
    # Calculate intervals
    intervals = [
        results[i+1] - results[i]
        for i in range(len(results)-1)
    ]
    
    # Should take at least 2 seconds for 5 calls at 2/sec
    assert duration >= 2.0, f"Duration {duration} should be >= 2.0 seconds"
    
    # Should maintain minimum interval of 0.5 seconds
    min_interval = 1.0 / 2.0  # 2 calls per second = 0.5s between calls
    assert all(i >= min_interval for i in intervals), (
        f"All intervals should be >= {min_interval}s"
    )

@pytest.mark.asyncio
async def test_concurrent_rate_limiting():
    """Test rate limiting under concurrent load."""
    results = []
    
    @rate_limited("concurrent_test", rate=5.0)
    async def limited_func(i: int):
        results.append((i, time.time()))
        await asyncio.sleep(0.1)  # Simulate work
        return i
    
    # Launch concurrent tasks
    start_time = time.time()
    tasks = [limited_func(i) for i in range(10)]
    await asyncio.gather(*tasks)
    duration = time.time() - start_time
    
    # Sort results by timestamp
    sorted_results = sorted(results, key=lambda x: x[1])
    
    # Calculate intervals
    intervals = [
        sorted_results[i+1][1] - sorted_results[i][1]
        for i in range(len(sorted_results)-1)
    ]
    
    # Should take at least 2 seconds for 10 calls at 5/sec
    assert duration >= 2.0, f"Duration {duration} should be >= 2.0 seconds"
    
    # Should maintain minimum interval
    min_interval = 1.0 / 5.0  # 5 calls per second = 0.2s between calls
    assert all(i >= min_interval for i in intervals), (
        f"All intervals should be >= {min_interval}s"
    )
    
    # Order should be preserved
    original_order = [r[0] for r in results]
    assert original_order == list(range(10)), (
        "Results should maintain original order"
    )

@pytest.mark.asyncio
async def test_safe_mode_rate_limiting():
    """Test rate limiting in safe mode."""
    Config.SAFE_MODE = True
    calls = []
    
    @rate_limited("safe_test", rate=5.0)
    async def limited_func():
        calls.append(time.time())
        await asyncio.sleep(0.1)
    
    # Make several rapid calls
    start_time = time.time()
    for _ in range(5):
        await limited_func()
    duration = time.time() - start_time
    
    # In safe mode, rate should be reduced
    expected_rate = Config.SAFE_MODE_RATE_LIMIT
    min_duration = (5 - 1) / expected_rate  # Time for 5 calls at reduced rate
    
    assert duration >= min_duration, (
        f"Duration {duration} should be >= {min_duration} in safe mode"
    )
    
    # Reset safe mode
    Config.SAFE_MODE = False

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=strict"])
