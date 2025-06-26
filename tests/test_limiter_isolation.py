"""
Rate Limiter Isolation Tests
------------------------
Tests for event loop and thread isolation in rate limiting.
"""

import asyncio
import time
import pytest
import threading
from concurrent.futures import ThreadPoolExecutor

from guardian.utils.event_safe_limiter import RateLimiter, rate_limit
from guardian.config import Config

@pytest.mark.asyncio
async def test_loop_safety():
    """Test rate limiter safety across event loops."""
    # Create limiter in test loop
    main_limiter = RateLimiter(rate=10.0)
    
    def run_in_thread():
        """Run limiter in separate thread with new event loop."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def worker():
            try:
                # Try to use main limiter in new loop
                await main_limiter.acquire()
                return False  # Shouldn't reach here
            except RuntimeError as e:
                return "event loop" in str(e)
        
        try:
            return loop.run_until_complete(worker())
        finally:
            loop.close()
    
    # Run in thread pool to avoid blocking
    with ThreadPoolExecutor() as pool:
        result = await asyncio.get_event_loop().run_in_executor(
            pool, run_in_thread
        )
    
    assert result, "Should have caught event loop error"

@pytest.mark.asyncio
async def test_thread_safety():
    """Test rate limiter safety across threads."""
    # Create limiter in main thread
    main_limiter = RateLimiter(rate=10.0)
    results = []
    
    def thread_worker():
        """Try to use limiter in different thread."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def use_limiter():
                await main_limiter.acquire()
            
            loop.run_until_complete(use_limiter())
            results.append(False)  # Shouldn't reach here
        except RuntimeError as e:
            results.append("event loop" in str(e))
        finally:
            loop.close()
    
    # Run in separate thread
    thread = threading.Thread(target=thread_worker)
    thread.start()
    thread.join()
    
    assert results[0], "Should have caught event loop error"

@pytest.mark.asyncio
async def test_concurrent_limiters():
    """Test multiple limiters in same loop."""
    limiter1 = RateLimiter(rate=10.0)
    limiter2 = RateLimiter(rate=10.0)
    results = []
    
    async def worker(limiter, id):
        await limiter.acquire()
        results.append((time.time(), id))
    
    # Run concurrent tasks
    await asyncio.gather(
        worker(limiter1, 1),
        worker(limiter2, 2)
    )
    
    # Check timing
    assert len(results) == 2, "Both operations should complete"
    if len(results) == 2:
        interval = abs(results[0][0] - results[1][0])
        assert interval >= 0.1 * 0.9, (
            f"Operations too close: {interval}s < 0.1s"
        )

@pytest.mark.asyncio
async def test_safe_mode_consistency():
    """Test safe mode consistency across limiters."""
    try:
        Config.SAFE_MODE = True
        Config.SAFE_MODE_RATE_LIMIT = 2.0  # 2 ops/sec
        
        limiter1 = RateLimiter(rate=10.0)
        limiter2 = RateLimiter(rate=20.0)
        results = []
        
        # Test both limiters
        for limiter in [limiter1, limiter2]:
            start = time.time()
            await limiter.acquire()
            await limiter.acquire()
            duration = time.time() - start
            results.append(duration)
        
        # Both should be limited to safe mode rate
        min_interval = 1.0 / Config.SAFE_MODE_RATE_LIMIT
        assert all(d >= min_interval * 0.9 for d in results), (
            f"Safe mode intervals should be >= {min_interval}s"
        )
    finally:
        Config.SAFE_MODE = False

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=strict"])
