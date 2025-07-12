import pytest
from unittest.mock import MagicMock, call

from guardian.core.orchestrator.agents.ritual_agent import trigger_ritual


@pytest.fixture
def mock_memory_client():
    """Provides a mocked Memoryos client instance."""
    client = MagicMock()
    # The ritual_agent calls `client.add_memory(...)`
    client.add_memory = MagicMock()
    return client


def test_trigger_known_ritual_success(mock_memory_client):
    """
    Tests that a known ritual is triggered successfully, returns the correct
    message, and logs the event to memory.
    """
    ritual_name = "evening_grounding"

    # Act
    response = trigger_ritual(mock_memory_client, ritual_name)

    # Assert response
    assert response["status"] == "success"
    assert "Evening grounding ritual activated" in response["message"]

    # Assert memory call
    mock_memory_client.add_memory.assert_called_once()
    expected_call = call(
        user_input=f"Ritual triggered: {ritual_name}",
        agent_response=response["message"],
        meta_data={"tags": ["ritual", "log", ritual_name]},
    )
    mock_memory_client.add_memory.assert_has_calls([expected_call])


def test_trigger_unknown_ritual(mock_memory_client):
    """
    Tests that an unknown ritual returns an error status but still logs
    the attempt to memory.
    """
    ritual_name = "non_existent_ritual"

    # Act
    response = trigger_ritual(mock_memory_client, ritual_name)

    # Assert response
    assert response["status"] == "error"
    assert f"Ritual '{ritual_name}' is not recognized" in response["message"]

    # Assert memory call
    mock_memory_client.add_memory.assert_called_once()
    expected_call = call(
        user_input=f"Ritual triggered: {ritual_name}",
        agent_response=response["message"],
        meta_data={"tags": ["ritual", "log", ritual_name]},
    )
    mock_memory_client.add_memory.assert_has_calls([expected_call])


def test_trigger_ritual_memory_logging_fails(mock_memory_client):
    """
    Tests that if logging to memory fails, the ritual's primary response
    is still returned correctly.
    """
    ritual_name = "daily_checkin"
    error_message = "Database connection failed"
    mock_memory_client.add_memory.side_effect = Exception(error_message)

    # Act
    response = trigger_ritual(mock_memory_client, ritual_name)

    # Assert response is still correct despite logging failure
    assert response["status"] == "success"
    assert "Daily check-in ritual initiated" in response["message"]

    # Assert that the call to add_memory was attempted
    mock_memory_client.add_memory.assert_called_once()


@pytest.mark.parametrize(
    "ritual_name, expected_message_part",
    [
        ("evening_grounding", "Evening grounding ritual activated"),
        ("daily_checkin", "Daily check-in ritual initiated"),
        ("morning_initiation", "Morning initiation ritual complete"),
    ],
)
def test_all_known_rituals(mock_memory_client, ritual_name, expected_message_part):
    """
    Tests all defined rituals to ensure they return success and the correct message.
    """
    # Act
    response = trigger_ritual(mock_memory_client, ritual_name)

    # Assert
    assert response["status"] == "success"
    assert expected_message_part in response["message"]
    mock_memory_client.add_memory.assert_called_once_with(
        user_input=f"Ritual triggered: {ritual_name}",
        agent_response=response["message"],
        meta_data={"tags": ["ritual", "log", ritual_name]},
    )