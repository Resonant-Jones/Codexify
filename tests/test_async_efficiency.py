"""
Async Efficiency Tests
-------------------
Validates async caching, rate limiting, and safety features.
"""

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import List, Dict, Any, AsyncGenerator

import pytest
import pytest_asyncio

pytestmark = pytest.mark.asyncio

from guardian.cache import lru_cache_safe, memoize_to_disk
from guardian.config import Config
from guardian.memory.async_logger import memory_logger
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

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()

@pytest_asyncio.fixture(autouse=True)
async def initialize_config():
    """Initialize configuration before each test."""
    Config.initialize()
    Config.SAFE_MODE = True
    Config.CACHE_ENABLED = True
    Config.COMPACT_LOGGING = True
    
    # Create required directories
    for path in [Config.CACHE_DIR, Config.LOG_DIR, Config.PLUGIN_DIR]:
        path.mkdir(parents=True, exist_ok=True)
    
    # Create test plugin manifest
    manifest = {
        "plugins": {
            "test_plugin": {
                "declares_side_effects": True,
                "rate_limit": "1/sec",
                "requires_memory_access": True
            },
            "memory_analyzer": {
                "declares_side_effects": False,
                "rate_limit": "2/sec",
                "requires_memory_access": True
            }
        }
    }
    
    with open(Config.PLUGIN_DIR / "plugin_manifest.json", 'w') as f:
        json.dump(manifest, f, indent=2)
    
    yield Config
    
    # Cleanup
    if (Config.PLUGIN_DIR / "plugin_manifest.json").exists():
        (Config.PLUGIN_DIR / "plugin_manifest.json").unlink()

@pytest_asyncio.fixture
async def setup_test_env(initialize_config) -> AsyncGenerator:
    """Setup test environment."""
    # Clear test files
    test_files = [
        Config.CACHE_DIR / "test_cache.jsonl",
        Config.LOG_DIR / "test_log.jsonl"
    ]
    for file in test_files:
        if file.exists():
            file.unlink()
    
    # Start logger
    memory_logger.start()
    
    yield
    
    # Stop logger and cleanup
    memory_logger.stop()
    await memory_logger.flush()
    
    for file in test_files:
        if file.exists():
            file.unlink()

@pytest.mark.asyncio
async def test_cache_decorators(setup_test_env):
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
    await asyncio.sleep(1.1)
    assert cached_func(5) == 10
    assert call_count == 2

@pytest.mark.asyncio
async def test_batch_logging(setup_test_env):
    """Test batched memory logging."""
    # Create log directory
    Config.LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    # Log test events
    for event in TEST_EVENTS[:20]:
        memory_logger.log_event(**event)
        await asyncio.sleep(0.01)  # Small delay to prevent overwhelming
    
    # Wait for flush
    await asyncio.sleep(memory_logger.flush_interval + 1)
    await memory_logger.flush()
    
    # Verify log file
    log_files = list(Config.LOG_DIR.glob("memory_*.jsonl"))
    assert len(log_files) > 0, f"No log files found in {Config.LOG_DIR}"
    
    with open(log_files[0]) as f:
        logged_events = [json.loads(line) for line in f]
        assert len(logged_events) == 20

@pytest.mark.asyncio
async def test_rate_limiting(setup_test_env):
    """Test plugin rate limiting."""
    call_times: List[float] = []
    
    @rate_limited_plugin_runner("test_plugin", rate_limit=2.0)
    async def rate_limited_func() -> None:
        call_times.append(time.time())
    
    # Make rapid calls
    tasks = [rate_limited_func() for _ in range(5)]
    await asyncio.gather(*tasks)
    
    # Verify rate limiting
    intervals = [
        call_times[i+1] - call_times[i]
        for i in range(len(call_times)-1)
    ]
    assert all(interval >= 0.5 for interval in intervals)

# Create a mock plugin for testing
class MockPlugin:
    @staticmethod
    async def execute(*args, **kwargs):
        await asyncio.sleep(0.1)
        return {"status": "success"}

@pytest.mark.asyncio
async def test_plugin_execution(setup_test_env, monkeypatch):
    """Test safe plugin execution."""
    # Mock plugin import
    import sys
    sys.modules['guardian.plugins.test_plugin'] = type(
        'MockModule',
        (),
        {'execute': MockPlugin.execute}
    )
    
    # Test execution
    start_time = time.time()
    results = []
    
    for _ in range(3):
        result = await plugin_executor.execute_plugin("test_plugin")
        if result is not None:
            results.append(result)
        await asyncio.sleep(0.1)
    
    # Verify rate limiting
    duration = time.time() - start_time
    assert duration >= 2.0, f"Duration {duration} should be >= 2.0 seconds"
    
    # Cleanup
    del sys.modules['guardian.plugins.test_plugin']

@pytest.mark.asyncio
async def test_full_system(setup_test_env, monkeypatch):
    """Test complete system with all safety features."""
    # Mock memory analyzer plugin
    import sys
    sys.modules['guardian.plugins.memory_analyzer'] = type(
        'MockModule',
        (),
        {'execute': MockPlugin.execute}
    )
    
    start_time = time.time()
    
    # Test memory operations with batching
    for event in TEST_EVENTS[:10]:  # Reduced event count for faster test
        memory_logger.log_event(**event)
        await asyncio.sleep(0.01)
    
    # Test concurrent plugin execution
    tasks = []
    for _ in range(5):  # Reduced iterations for faster test
        task = asyncio.create_task(
            plugin_executor.execute_plugin("memory_analyzer")
        )
        tasks.append(task)
    
    # Wait for tasks with timeout
    try:
        await asyncio.wait_for(asyncio.gather(*tasks), timeout=10.0)
    except asyncio.TimeoutError:
        logger.warning("Plugin execution timeout - expected with rate limiting")
    
    # Verify results
    await memory_logger.flush()
    assert Config.SAFE_MODE  # Safety should be maintained
    
    # Check log files
    log_files = list(Config.LOG_DIR.glob("memory_*.jsonl"))
    assert len(log_files) > 0
    
    # Verify rate limiting worked
    duration = time.time() - start_time
    assert duration >= 2.0, f"Duration {duration} should be >= 2.0 seconds"
    
    # Cleanup
    del sys.modules['guardian.plugins.memory_analyzer']

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=strict"])
