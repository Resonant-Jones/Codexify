import time
import unittest
from unittest.mock import patch

from guardian.core.orchestrator.pulse_orchestrator import orchestrate


def mock_slow_agent(*args, **kwargs):
    """A mock agent function that simulates a long-running task."""
    time.sleep(0.2)
    return {"status": "success", "message": "I eventually finished"}


def mock_fast_agent(*args, **kwargs):
    """A mock agent function that runs quickly."""
    time.sleep(0.01)
    return {"status": "success", "message": "I finished on time"}


class TestPulseOrchestratorTimeouts(unittest.TestCase):
    @patch("guardian.core.orchestrator.pulse_orchestrator.get_memoryos_instance")
    @patch("guardian.core.orchestrator.pulse_orchestrator.settings")
    @patch("guardian.core.orchestrator.pulse_orchestrator.AGENT_ACTIONS")
    def test_orchestrate_agent_timeout(
        self, mock_agent_actions, mock_settings, mock_get_memoryos
    ):
        """
        Verify that the orchestrator returns a timeout error if an agent takes too long.
        """
        # Configure a short timeout for the test
        mock_settings.AGENT_TIMEOUT_SECONDS = 0.1

        # Mock the expensive client creation to isolate the test to timeout logic
        mock_get_memoryos.return_value = None

        # Make the orchestrator use our slow mock for the 'run_foresight' action
        mock_agent_actions.get.return_value = mock_slow_agent

        command = {"action": "run_foresight", "params": {}}
        result = orchestrate(command)

        # Assert that the result is a timeout error
        self.assertEqual(result["status"], "error")
        self.assertIn("timed out", result["message"])
        self.assertIn("run_foresight", result["message"])

    @patch("guardian.core.orchestrator.pulse_orchestrator.get_memoryos_instance")
    @patch("guardian.core.orchestrator.pulse_orchestrator.settings")
    @patch("guardian.core.orchestrator.pulse_orchestrator.AGENT_ACTIONS")
    def test_orchestrate_agent_success_within_timeout(
        self, mock_agent_actions, mock_settings, mock_get_memoryos
    ):
        """
        Verify that the orchestrator returns a successful result if an agent finishes on time.
        """
        # Configure a timeout that the agent will beat
        mock_settings.AGENT_TIMEOUT_SECONDS = 0.1

        # Mock the expensive client creation to isolate the test to timeout logic.
        # This prevents the test from timing out due to model loading in a new process.
        mock_get_memoryos.return_value = None

        # Make the orchestrator use our fast mock for the 'run_foresight' action
        mock_agent_actions.get.return_value = mock_fast_agent

        command = {"action": "run_foresight", "params": {}}
        result = orchestrate(command)

        # Assert that the result is a success
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["message"], "I finished on time")


if __name__ == "__main__":
    unittest.main()
