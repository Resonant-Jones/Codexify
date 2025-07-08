"""
Efficiency and Safety Tests
-------------------------
Validates caching, rate limiting, and safety features.
"""

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import List, Dict, Any

import pytest

pytestmark = pytest.mark.asyncio

from guardian.cache import lru_cache_safe, memoize_to_disk
from guardian.config import Config
from guardian.memory.memory_logger import memory_logger
from guardian.memory.query_memory import memory_store
from guardian.threads.plugin_executor import plugin_executor
from guardian.utils.performance import (
    debounce,
    throttle,
    batch_flush,
    rate_limited_plugin_runner
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test data
TEST_EVENTS = [
    {
        "source": "test",
        "event_type": "cache_test",
        "payload": {"test_id": i},
        "tags": ["test", "cache"]
    }
    for i in range(50)
]

@pytest.fixture
def setup_test_env():
    """Setup test environment."""
    # Enable test mode
    Config.SAFE_MODE = True
    Config.CACHE_ENABLED = True
    Config.COMPACT_LOGGING = True
    
    # Clear test files
    test_files = [
        Config.CACHE_DIR / "test_cache.jsonl",
        Config.LOG_DIR / "test_log.jsonl"
    ]
    for file in test_files:
        if file.exists():
            file.unlink()
    
    yield
    
    # Cleanup
    for file in test_files:
        if file.exists():
            file.unlink()

def test_cache_decorators(setup_test_env):
    """Test caching decorators."""
    call_count = 0
    
    @lru_cache_safe(maxsize=10, expire=1)
    def cached_func(x: int) -> int:
        nonlocal call_count
        call_count += 1
        return x * 2
    
    # Test cache hit
    assert cached_func(5) == 10
    assert cached_func(5) == 10
    assert call_count == 1
    
    # Test cache expiration
    time.sleep(1.1)
    assert cached_func(5) == 10
    assert call_count == 2
    
    # Test disk cache
    call_count = 0
    
    @memoize_to_disk(expire=1)
    def disk_cached_func(x: int) -> int:
        nonlocal call_count
        call_count += 1
        return x * 3
    
    assert disk_cached_func(5) == 15
    assert disk_cached_func(5) == 15
    assert call_count == 1

async def test_batch_logging(setup_test_env):
    """Test batched memory logging."""
    # Log test events
    for event in TEST_EVENTS[:20]:
        memory_logger.log_event(**event)
    
    # Wait for flush
    await asyncio.sleep(Config.MEMORY_FLUSH_INTERVAL + 1)
    
    # Verify log file
    log_files = list(Config.LOG_DIR.glob("memory_*.jsonl"))
    assert len(log_files) > 0
    
    with open(log_files[0]) as f:
        logged_events = [json.loads(line) for line in f]
        assert len(logged_events) == 20

def test_rate_limiting(setup_test_env):
    """Test plugin rate limiting."""
    call_times: List[float] = []
    
    @rate_limited_plugin_runner("test_plugin", rate_limit=2.0)
    def rate_limited_func() -> None:
        call_times.append(time.time())
    
    # Make rapid calls
    for _ in range(5):
        rate_limited_func()
    
    # Verify rate limiting
    intervals = [
        call_times[i+1] - call_times[i]
        for i in range(len(call_times)-1)
    ]
    assert all(interval >= 0.5 for interval in intervals)

async def test_plugin_execution(setup_test_env):
    """Test safe plugin execution."""
    # Configure test plugin
    test_plugin = {
        "declares_side_effects": True,
        "rate_limit": "1/sec",
        "requires_memory_access": True
    }
    
    manifest = Config.load_plugin_manifest()
    if manifest:
        manifest["plugins"]["test_plugin"] = test_plugin
        
        with open(Config.PLUGIN_DIR / "plugin_manifest.json", 'w') as f:
            json.dump(manifest, f, indent=2)
    
    # Test execution
    start_time = time.time()
    results = []
    
    for _ in range(3):
        result = plugin_executor.execute_plugin("test_plugin")
        if result is not None:
            results.append(result)
        await asyncio.sleep(0.1)
    
    # Verify rate limiting
    duration = time.time() - start_time
    assert duration >= 2.0  # Should take at least 2 seconds due to rate limit

@pytest.mark.asyncio
async def test_full_system(setup_test_env):
    """Test complete system with all safety features."""
    # Initialize components
    Config.initialize()
    
    # Test memory operations
    for event in TEST_EVENTS:
        memory_logger.log_event(**event)
    
    # Test plugin execution
    tasks = []
    for _ in range(10):
        task = asyncio.create_task(
            plugin_executor.execute_plugin("memory_analyzer")
        )
        tasks.append(task)
    
    # Wait for tasks
    await asyncio.gather(*tasks)
    
    # Verify results
    assert memory_logger.buffer == []  # Should be flushed
    assert Config.SAFE_MODE  # Safety should be maintained

if __name__ == "__main__":
    pytest.main([__file__])
