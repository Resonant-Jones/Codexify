import time
from unittest.mock import patch, MagicMock
import pytest

from guardian.core.orchestrator.pulse_orchestrator import orchestrate


def mock_slow_agent(*args, **kwargs):
    """A mock agent function that simulates a long-running task."""
    time.sleep(0.2)
    return {"status": "success", "message": "I eventually finished"}


def mock_fast_agent(*args, **kwargs):
    """A mock agent function that runs quickly."""
    print(">>> mock_fast_agent was called")
    time.sleep(0.01)
    return {"status": "success", "message": "I finished on time"}


@patch("guardian.core.orchestrator.pulse_orchestrator.get_memoryos_instance", return_value=None)
@patch("guardian.core.orchestrator.pulse_orchestrator.settings")
@patch("guardian.core.orchestrator.pulse_orchestrator.AGENT_ACTIONS")
def test_orchestrate_agent_timeout(
    mock_agent_actions: MagicMock, mock_settings: MagicMock, mock_get_memoryos: MagicMock
):
    """
    Verify that the orchestrator returns a timeout error if an agent takes too long.
    """
    # Configure a short timeout for the test
    mock_settings.AGENT_TIMEOUT_SECONDS = 5

    # Make the orchestrator use our slow mock for the 'run_foresight' action
    mock_agent_actions.get.return_value = mock_fast_agent

    command = {"action": "run_foresight", "params": {}}
    result = orchestrate(command)

    # Assert that the result is a timeout error
    assert result["status"] == "error"
    assert "timed out" in result["message"]
    assert "run_foresight" in result["message"]


@patch("guardian.core.orchestrator.pulse_orchestrator.get_memoryos_instance", return_value=None)
@patch("guardian.core.orchestrator.pulse_orchestrator.settings")
@patch("guardian.core.orchestrator.pulse_orchestrator.AGENT_ACTIONS")
def test_orchestrate_agent_success_within_timeout(
    mock_agent_actions: MagicMock, mock_settings: MagicMock, mock_get_memoryos: MagicMock
):
    """
    Verify that the orchestrator returns a successful result if an agent finishes on time.
    """
    # Configure a timeout that the agent will beat
    mock_settings.AGENT_TIMEOUT_SECONDS = 5

    # Mock the expensive client creation to isolate the test to timeout logic.
    # This prevents the test from timing out due to model loading in a new process.

    # Make the orchestrator use our fast mock for the 'run_foresight' action
    mock_agent_actions.get.return_value = mock_fast_agent

    command = {"action": "run_foresight", "params": {}}
    result = orchestrate(command)
    print(f">>> Orchestrate returned result: {result}")

    # Assert that the result is a success
    assert result["status"] == "success"
    assert result["message"] == "I finished on time"
