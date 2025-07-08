"""
Async System Tests
---------------
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
from guardian.threads.async_executor import plugin_executor
from guardian.utils.async_performance import (
    async_rate_limited,
    async_debounce,
    async_throttle
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
    for i in range(10)  # Reduced size for faster tests
]

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
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
    
    manifest_path = Config.PLUGIN_DIR / "plugin_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    yield Config
    
    # Cleanup
    if manifest_path.exists():
        manifest_path.unlink()

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
async def test_rate_limiting():
    """Test async rate limiting."""
    call_times: List[float] = []
    
    @async_rate_limited("test", rate_limit=2.0)
    async def rate_limited_func() -> None:
        call_times.append(time.time())
        await asyncio.sleep(0.1)  # Simulate work
    
    # Make rapid calls
    tasks = [rate_limited_func() for _ in range(5)]
    await asyncio.gather(*tasks)
    
    # Verify rate limiting
    intervals = [
        call_times[i+1] - call_times[i]
        for i in range(len(call_times)-1)
    ]
    assert all(interval >= 0.5 for interval in intervals)

@pytest.mark.asyncio
async def test_debounce():
    """Test async debouncing."""
    call_count = 0
    result = None
    
    @async_debounce(wait=0.5)
    async def debounced_func(value: int) -> int:
        nonlocal call_count
        call_count += 1
        return value
    
    # Make rapid calls
    for i in range(5):
        result = await debounced_func(i)
        await asyncio.sleep(0.1)
    
    # Wait for debounce
    await asyncio.sleep(0.6)
    
    # Should only be called once with last value
    assert call_count == 1
    assert result == 4

@pytest.mark.asyncio
async def test_throttle():
    """Test async throttling."""
    call_times: List[float] = []
    
    @async_throttle(rate=2.0)
    async def throttled_func() -> None:
        call_times.append(time.time())
    
    # Make rapid calls
    for _ in range(5):
        await throttled_func()
        await asyncio.sleep(0.1)
    
    # Should have fewer calls due to throttling
    assert len(call_times) < 5
    
    if len(call_times) > 1:
        intervals = [
            call_times[i+1] - call_times[i]
            for i in range(len(call_times)-1)
        ]
        assert all(interval >= 0.5 for interval in intervals)

# Create a mock plugin for testing
class MockPlugin:
    @staticmethod
    async def execute(*args: Any, **kwargs: Any) -> Dict[str, str]:
        await asyncio.sleep(0.1)  # Simulate work
        return {"status": "success"}

@pytest.mark.asyncio
async def test_plugin_execution(monkeypatch):
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
    
    # Verify rate limiting
    duration = time.time() - start_time
    assert duration >= 2.0, f"Duration {duration} should be >= 2.0 seconds"
    assert len(results) == 3
    assert all(r["status"] == "success" for r in results)
    
    # Cleanup
    del sys.modules['guardian.plugins.test_plugin']

@pytest.mark.asyncio
async def test_full_system(monkeypatch):
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
    for event in TEST_EVENTS:
        memory_logger.log_event(**event)
        await asyncio.sleep(0.01)
    
    # Test concurrent plugin execution
    tasks = []
    for _ in range(5):
        task = asyncio.create_task(
            plugin_executor.execute_plugin("memory_analyzer")
        )
        tasks.append(task)
    
    # Wait for tasks
    results = await asyncio.gather(*tasks)
    
    # Verify results
    await memory_logger.flush()
    assert Config.SAFE_MODE  # Safety should be maintained
    assert all(r["status"] == "success" for r in results)
    
    # Verify rate limiting worked
    duration = time.time() - start_time
    assert duration >= 2.0, f"Duration {duration} should be >= 2.0 seconds"
    
    # Cleanup
    del sys.modules['guardian.plugins.memory_analyzer']

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=strict"])
