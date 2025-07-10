"""
System Diagnostics Plugin Tests
-----------------------------
Test suite for system diagnostics functionality.
"""

import json
import logging
import pytest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

from guardian.plugins.system_diagnostics.main import SystemDiagnostics, DiagnosticResult
from guardian.codex_awareness import CodexAwareness
from guardian.metacognition import MetacognitionEngine
from guardian.threads.thread_manager import ThreadManager

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def load_config():
    plugin_dir = Path(__file__).parent.parent
    with open(plugin_dir / "plugin.json", "r") as f:
        return json.load(f)["config"]


@pytest.mark.asyncio
async def test_monitor_initialization():
    # Arrange
    config = load_config()
    diagnostics = SystemDiagnostics(config)
    diagnostics.codex = MagicMock(spec=CodexAwareness)
    diagnostics.metacognition = MagicMock(spec=MetacognitionEngine)
    diagnostics.thread_manager = MagicMock(spec=ThreadManager)

    # Act & Assert
    for monitor_type in config["monitors"]:
        if config["monitors"][monitor_type]:
            assert monitor_type in diagnostics.monitors


@pytest.mark.asyncio
async def test_memory_monitor():
    config = load_config()
    diagnostics = SystemDiagnostics(config)
    diagnostics.codex = MagicMock(spec=CodexAwareness)
    diagnostics.metacognition = MagicMock(spec=MetacognitionEngine)
    diagnostics.thread_manager = MagicMock(spec=ThreadManager)

    memory_info = {"usage_percent": 75.0, "total": 16384, "used": 12288, "free": 4096}
    diagnostics.thread_manager.get_memory_info.return_value = memory_info

    result = await diagnostics.monitors["memory"].check()

    assert result.check_type == "memory"
    assert result.status == "healthy"
    assert result.value >= 0
    assert result.metadata == memory_info


@pytest.mark.asyncio
async def test_thread_monitor():
    config = load_config()
    diagnostics = SystemDiagnostics(config)
    diagnostics.codex = MagicMock(spec=CodexAwareness)
    diagnostics.metacognition = MagicMock(spec=MetacognitionEngine)
    diagnostics.thread_manager = MagicMock(spec=ThreadManager)

    thread_info = {"active_count": 10, "dead_count": 2, "total_created": 12}
    diagnostics.thread_manager.get_thread_info.return_value = thread_info

    result = await diagnostics.monitors["threads"].check()

    assert result.check_type == "threads"
    assert result.status == "healthy"
    assert result.value == 2
    assert "threads" in result.metadata


@pytest.mark.asyncio
async def test_plugin_monitor():
    config = load_config()
    diagnostics = SystemDiagnostics(config)
    diagnostics.codex = MagicMock(spec=CodexAwareness)
    diagnostics.metacognition = MagicMock(spec=MetacognitionEngine)
    diagnostics.thread_manager = MagicMock(spec=ThreadManager)

    plugin1 = MagicMock()
    plugin1.name = "plugin1"
    plugin1.health_check.return_value = {"status": "healthy"}

    plugin2 = MagicMock()
    plugin2.name = "plugin2"
    plugin2.health_check.return_value = {"status": "warning"}

    diagnostics.thread_manager.get_plugins.return_value = [plugin1, plugin2]

    result = await diagnostics.monitors["plugins"].check()

    assert result.check_type == "plugins"
    assert result.status == "healthy"
    assert result.value == 1  # One unhealthy plugin
    assert len(result.metadata["plugins"]) == 2


@pytest.mark.asyncio
async def test_agent_monitor():
    config = load_config()
    diagnostics = SystemDiagnostics(config)
    diagnostics.codex = MagicMock(spec=CodexAwareness)
    diagnostics.metacognition = MagicMock(spec=MetacognitionEngine)
    diagnostics.thread_manager = MagicMock(spec=ThreadManager)

    agent1 = AsyncMock()
    agent1.name = "agent1"
    agent1.get_status.return_value = {"status": "healthy"}

    agent2 = AsyncMock()
    agent2.name = "agent2"
    agent2.get_status.return_value = {"status": "healthy"}

    diagnostics.thread_manager.get_agents.return_value = [agent1, agent2]

    result = await diagnostics.monitors["agents"].check()

    assert result.check_type == "agents"
    assert result.status in ["healthy", "warning", "critical"]
    assert result.value == 0  # No unhealthy agents
    assert len(result.metadata["agents"]) == 2


@pytest.mark.asyncio
async def test_performance_monitor():
    config = load_config()
    diagnostics = SystemDiagnostics(config)
    diagnostics.codex = MagicMock(spec=CodexAwareness)
    diagnostics.metacognition = MagicMock(spec=MetacognitionEngine)
    diagnostics.thread_manager = MagicMock(spec=ThreadManager)

    metrics = {
        "response_time": 100,
        "throughput": 1000,
        "cpu_usage": 60,
        "memory_usage": 70,
    }
    diagnostics.thread_manager.get_performance_metrics.return_value = metrics

    result = await diagnostics.monitors["performance"].check()

    assert result.check_type == "performance"
    assert result.status == "healthy"
    assert result.value == 100
    assert "throughput" in result.metadata


@pytest.mark.asyncio
async def test_error_monitor():
    config = load_config()
    diagnostics = SystemDiagnostics(config)
    diagnostics.codex = MagicMock(spec=CodexAwareness)
    diagnostics.metacognition = MagicMock(spec=MetacognitionEngine)
    diagnostics.thread_manager = MagicMock(spec=ThreadManager)

    diagnostics.check_results = [
        DiagnosticResult("test", "healthy", None),
        DiagnosticResult("test", "error", None),
        DiagnosticResult("test", "healthy", None),
        DiagnosticResult("test", "error", None),
    ]

    result = await diagnostics.monitors["errors"].check()

    assert result.check_type == "errors"
    assert result.status == "warning"
    assert result.value == 0.5  # 50% error rate


@pytest.mark.asyncio
async def test_alert_generation():
    config = load_config()
    diagnostics = SystemDiagnostics(config)
    diagnostics.codex = MagicMock(spec=CodexAwareness)
    diagnostics.metacognition = MagicMock(spec=MetacognitionEngine)
    diagnostics.thread_manager = MagicMock(spec=ThreadManager)

    results = {
        "memory": {"status": "warning", "value": 90.0, "threshold": 80.0},
        "threads": {"status": "critical", "value": 10, "threshold": 5},
    }

    await diagnostics._check_alerts(results)

    diagnostics.codex.store_memory.assert_called()
    diagnostics.thread_manager.update_metrics.assert_called()


@pytest.mark.asyncio
async def test_error_handling():
    config = load_config()
    diagnostics = SystemDiagnostics(config)
    diagnostics.codex = MagicMock(spec=CodexAwareness)
    diagnostics.metacognition = MagicMock(spec=MetacognitionEngine)
    diagnostics.thread_manager = MagicMock(spec=ThreadManager)

    component = "test_component"
    error = Exception("Test error")

    for _ in range(config["failure_handling"]["max_retries"] + 2):
        await diagnostics._handle_error(component, error)

    assert (
        diagnostics.error_count[component]
        >= config["failure_handling"]["max_retries"] - 1
    )


@pytest.mark.asyncio
async def test_diagnostic_loop():
    config = load_config()
    diagnostics = SystemDiagnostics(config)
    diagnostics.codex = MagicMock(spec=CodexAwareness)
    diagnostics.metacognition = MagicMock(spec=MetacognitionEngine)
    diagnostics.thread_manager = MagicMock(spec=ThreadManager)

    diagnostics.running = True
    diagnostics._start_diagnostic_thread()

    import asyncio

    await asyncio.sleep(2)

    assert diagnostics.last_check is not None
    assert len(diagnostics.check_results) > 0


@pytest.mark.asyncio
async def test_result_storage():
    config = load_config()
    diagnostics = SystemDiagnostics(config)
    diagnostics.codex = MagicMock(spec=CodexAwareness)
    diagnostics.metacognition = MagicMock(spec=MetacognitionEngine)
    diagnostics.thread_manager = MagicMock(spec=ThreadManager)

    results = {"test": {"status": "healthy", "value": 100, "threshold": 200}}

    diagnostics._store_results(results)

    assert len(diagnostics.check_results) > 0
    diagnostics.codex.store_memory.assert_called_once()


def test_diagnostic_result():
    result = DiagnosticResult(
        check_type="test",
        status="healthy",
        value=100,
        threshold=200,
        metadata={"test": "data"},
    )

    assert result.check_type == "test"
    assert result.status == "healthy"
    assert result.value == 100
    assert result.threshold == 200
    assert result.metadata["test"] == "data"

    result_dict = result.to_dict()
    assert "check_type" in result_dict
    assert "status" in result_dict
    assert "value" in result_dict
    assert "threshold" in result_dict
    assert "metadata" in result_dict
    assert "timestamp" in result_dict
    assert "anomaly_score" in result_dict
