from __future__ import annotations

from guardian.cognition.prompts import build_context_system_message_with_meta


def test_connector_context_renders_and_sets_meta() -> None:
    bundle = {
        "semantic": [{"content": "semantic context line"}],
        "memory": [
            {
                "text": "memory anchor line",
                "metadata": {
                    "source_created_at": "2026-02-08T14:05:00+00:00",
                    "source_thread_id": "thread-abc",
                    "turn_index": 7,
                    "role": "assistant",
                },
            }
        ],
        "graph": [{"text": "graph context line"}],
        "federated": [{"text": "federated context line"}],
        "connector_context": [
            {
                "connector_id": "obsidian",
                "title": "Memory Note",
                "content": "obsidian connector context line",
            },
            {
                "connector_id": "obsidian",
                "metadata": {"text": "obsidian metadata-backed line"},
            },
        ],
    }

    message, meta = build_context_system_message_with_meta(bundle)

    assert message is not None
    assert "**Semantic Context:**" in message
    assert "**Memory Context:**" in message
    assert "**Graph Context:**" in message
    assert "**Federated Context:**" in message
    assert "**Connector Context: Obsidian**" in message
    assert "obsidian connector context line" in message
    assert "obsidian metadata-backed line" in message
    assert meta["connector_context"]["count"] == 2
    assert meta["connector_context"]["injected"] is True
    assert meta["connector_context"]["connectors"]["obsidian"] == 2


def test_empty_connector_context_does_not_render_section() -> None:
    bundle = {"semantic": [{"text": "semantic context line"}]}

    message, meta = build_context_system_message_with_meta(bundle)

    assert message is not None
    assert "**Connector Context:" not in message
    assert meta["connector_context"]["count"] == 0
    assert meta["connector_context"]["injected"] is False
