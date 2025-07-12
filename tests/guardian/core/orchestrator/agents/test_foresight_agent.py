import pytest
from unittest.mock import MagicMock
from guardian.core.orchestrator.agents.foresight_agent import (
    run_foresight,
    STATUS_NUDGE,
    STATUS_OK,
    CONTEXT_STRESS,
)


@pytest.fixture
def mock_memory_client() -> MagicMock:
    """Fixture to create a mock Memoryos client."""
    return MagicMock()


def test_foresight_stress_returns_nudge_on_high_log_count(mock_memory_client: MagicMock):
    """
    Verify a 'nudge' is returned when the memory client finds many stress logs.
    """
    # Configure the mock to return a list of 15 items (which is > threshold of 10)
    mock_memory_client.fetch_memory.return_value = ["log"] * 15

    response = run_foresight(mock_memory_client, context=CONTEXT_STRESS)

    # Assert that the correct call was made to the memory client
    mock_memory_client.fetch_memory.assert_called_once_with(
        query="stress", timeframe="last_14d", tags=["ritual", "log"], limit=50
    )
    assert response["status"] == STATUS_NUDGE
    assert "stress trend" in response["message"]


def test_foresight_stress_returns_ok_on_low_log_count(mock_memory_client: MagicMock):
    """Verify an 'ok' status is returned when stress logs are few."""
    # Configure the mock to return only 5 items
    mock_memory_client.fetch_memory.return_value = ["log"] * 5

    response = run_foresight(mock_memory_client, context=CONTEXT_STRESS)

    assert response["status"] == STATUS_OK
    assert "stable" in response["message"]


def test_foresight_handles_unknown_context_gracefully(mock_memory_client: MagicMock):
    """Verify the agent doesn't crash and returns a safe response for unknown contexts."""
    response = run_foresight(mock_memory_client, context="unknown_context")

    assert response["status"] == STATUS_OK
    assert "No foresight analysis available" in response["message"]
    mock_memory_client.fetch_memory.assert_not_called()