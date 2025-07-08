"""
Safeguard Tests
------------
Tests for backend safeguards and rate limiting.
"""

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import List

import pytest

pytestmark = pytest.mark.asyncio

from guardian.config import Config
from guardian.utils.safeguard import (
    safe_model_call,
    safe_plugin_execution,
    memory_query,
    throttle
)
from guardian.utils.safe_logger import SafeLogger
from guardian.plugin_manager import SafePluginManager
from guardian.memory.query_memory import MemoryStore

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.mark.asyncio
async def test_model_call_rate_limiting():
    """Test model API call rate limiting."""
    call_count = 0
    
    @safe_model_call
    async def mock_model_call(text: str) -> str:
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.1)  # Simulate API call
        return f"Response to: {text}"
    
    # Make rapid calls
    tasks = []
    for i in range(30):  # Try to exceed MAX_MODEL_CALLS_PER_MIN
        task = asyncio.create_task(
            mock_model_call(f"Query {i}")
        )
        tasks.append(task)
    
    results = await asyncio.gather(*tasks)
    successful_calls = len([r for r in results if r is not None])
    
    # Should be limited to MAX_MODEL_CALLS_PER_MIN
    assert successful_calls <= Config.MAX_MODEL_CALLS_PER_MIN, (
        f"Expected <= {Config.MAX_MODEL_CALLS_PER_MIN} calls, "
        f"got {successful_calls}"
    )

@pytest.mark.asyncio
async def test_plugin_execution_limits():
    """Test plugin execution rate limiting."""
    manager = SafePluginManager()
    
    # Create test plugin
    test_plugin_dir = Path("test_plugin")
    test_plugin_dir.mkdir(exist_ok=True)
    
    with open(test_plugin_dir / "plugin.json", "w") as f:
        json.dump({
            "name": "test_plugin",
            "version": "1.0.0",
            "description": "Test plugin",
            "author": "Test",
            "rate_limit": "5/sec"
        }, f)
    
    with open(test_plugin_dir / "main.py", "w") as f:
        f.write("""
async def init_plugin():
    return True

async def execute():
    return "executed"
        """)
    
    # Load plugin
    plugin = await manager.load_plugin(test_plugin_dir)
    assert plugin is not None
    
    # Make rapid calls
    results = []
    start_time = time.time()
    
    for _ in range(10):
        result = await plugin.execute()
        results.append(result is not None)
        await asyncio.sleep(0.1)
    
    duration = time.time() - start_time
    successful_calls = len([r for r in results if r])
    
    # Should be rate limited
    assert successful_calls <= 5, f"Expected <= 5 calls, got {successful_calls}"
    assert duration >= 1.0, f"Duration {duration} should be >= 1.0 seconds"

@pytest.mark.asyncio
async def test_memory_query_caching():
    """Test memory query caching and rate limiting."""
    store = MemoryStore(":memory:")  # Use in-memory SQLite
    
    # Add test data
    await store.store_memory(
        "Test content",
        "2023-01-01T00:00:00Z",
        {"test": True},
        ["test"]
    )
    
    # Make rapid queries
    results = []
    start_time = time.time()
    
    for _ in range(10):
        result = await store.query_by_tags(["test"])
        results.append(len(result))
        await asyncio.sleep(0.1)
    
    duration = time.time() - start_time
    
    # Should use cache after first query
    assert all(r == results[0] for r in results), "Results should be consistent"
    assert duration < 2.0, "Cached queries should be fast"

@pytest.mark.asyncio
async def test_safe_logger_batching():
    """Test logger batching and rate limiting."""
    test_log_dir = Path("test_logs")
    logger = SafeLogger("test", test_log_dir)
    
    # Generate rapid log events
    for i in range(100):
        await logger.info(f"Test log {i}")
    
    # Wait for auto-flush
    await asyncio.sleep(Config.MEMORY_FLUSH_INTERVAL + 0.1)
    
    # Check log files
    log_files = list(test_log_dir.glob("*.jsonl"))
    assert len(log_files) > 0, "Should create log files"
    
    # Count total events
    total_events = 0
    for log_file in log_files:
        with open(log_file) as f:
            events = [line for line in f if line.strip()]
            total_events += len(events)
    
    # Should have all events despite rate limiting
    assert total_events == 100, f"Expected 100 events, got {total_events}"
    
    # Cleanup
    await logger.close()
    for file in log_files:
        file.unlink()
    test_log_dir.rmdir()

@pytest.mark.asyncio
async def test_concurrent_plugin_limits():
    """Test concurrent plugin execution limits."""
    manager = SafePluginManager()
    
    # Create multiple test plugins
    plugin_results = []
    
    for i in range(Config.MAX_CONCURRENT_PLUGINS + 2):
        plugin_dir = Path(f"test_plugin_{i}")
        plugin_dir.mkdir(exist_ok=True)
        
        with open(plugin_dir / "plugin.json", "w") as f:
            json.dump({
                "name": f"test_plugin_{i}",
                "version": "1.0.0",
                "description": f"Test plugin {i}",
                "author": "Test"
            }, f)
        
        with open(plugin_dir / "main.py", "w") as f:
            f.write("""
async def init_plugin():
    return True
            """)
    
    # Try to load more than MAX_CONCURRENT_PLUGINS
    await manager.load_all_plugins()
    
    # Should be limited
    assert len(manager.plugins) <= Config.MAX_CONCURRENT_PLUGINS, (
        f"Expected <= {Config.MAX_CONCURRENT_PLUGINS} plugins, "
        f"got {len(manager.plugins)}"
    )
    
    # Cleanup
    for i in range(Config.MAX_CONCURRENT_PLUGINS + 2):
        plugin_dir = Path(f"test_plugin_{i}")
        for file in plugin_dir.glob("*"):
            file.unlink()
        plugin_dir.rmdir()

@pytest.mark.asyncio
async def test_throttled_operations():
    """Test general throttling decorator."""
    results: List[float] = []
    
    @throttle(rate=5.0)  # 5 ops/sec
    async def throttled_op() -> None:
        results.append(time.time())
        await asyncio.sleep(0.1)
    
    # Make rapid calls
    tasks = [throttled_op() for _ in range(10)]
    await asyncio.gather(*tasks)
    
    # Check intervals
    intervals = [
        results[i+1] - results[i]
        for i in range(len(results)-1)
    ]
    
    # Should maintain minimum interval of 0.2 seconds
    assert all(interval >= 0.2 for interval in intervals), (
        f"Intervals should be >= 0.2: {intervals}"
    )

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=strict"])
