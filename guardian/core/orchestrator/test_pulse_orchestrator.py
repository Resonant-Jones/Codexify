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
    time.sleep(0.01)
    return {"status": "success", "message": "I finished on time"}



# --- Helper decorator for patching common dependencies ---
def patch_orchestrator_common(test_func):
    """
    Decorator to patch pulse_orchestrator dependencies for orchestrate tests.
    """
    return patch("guardian.core.orchestrator.pulse_orchestrator.get_memoryos_instance", return_value=None)(
        patch("guardian.core.orchestrator.pulse_orchestrator.settings")(
            patch("guardian.core.orchestrator.pulse_orchestrator.AGENT_ACTIONS")(test_func)
        )
    )


@pytest.mark.parametrize(
    "mock_agent,timeout,expected_status,expected_in_message",
    [
        (mock_slow_agent, 0.1, "error", "timed out"),
        (mock_fast_agent, 0.1, "success", "I finished on time"),
    ],
)
@patch_orchestrator_common
def test_orchestrate_agent_timeout_and_success(
    mock_agent_actions: MagicMock,
    mock_settings: MagicMock,
    mock_get_memoryos: MagicMock,
    mock_agent,
    timeout,
    expected_status,
    expected_in_message
):
    """
    Verify that the orchestrator handles both timeout and successful completion cases.
    """
    mock_settings.AGENT_TIMEOUT_SECONDS = timeout
    mock_agent_actions.get.return_value = mock_agent

    command = {"action": "run_foresight", "params": {}}
    result = orchestrate(command)

    assert result["status"] == expected_status
    assert expected_in_message in result["message"] or expected_in_message == result.get("message")
