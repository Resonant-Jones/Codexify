"""Tests for event payload coherence contracts."""

from guardian.core.event_contracts import (
    MESSAGE_CREATED_TOPIC,
    coerce_event_payload,
)


def test_message_created_contract_normalizes_payload() -> None:
    payload = {
        "thread_id": "7",
        "message_id": "42",
        "role": "assistant",
        "content": "Hello",
    }
    normalized = coerce_event_payload(MESSAGE_CREATED_TOPIC, payload)
    assert normalized is not None
    assert normalized["thread_id"] == 7
    assert normalized["message_id"] == 42
    assert normalized["message"]["id"] == 42
    assert normalized["message"]["thread_id"] == 7
    assert normalized["message"]["role"] == "assistant"
    assert normalized["message"]["content"] == "Hello"


def test_message_created_contract_drops_empty_content() -> None:
    payload = {
        "thread_id": 1,
        "message_id": 2,
        "role": "user",
        "content": "   ",
    }
    normalized = coerce_event_payload(MESSAGE_CREATED_TOPIC, payload)
    assert normalized is None
