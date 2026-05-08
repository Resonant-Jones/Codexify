from __future__ import annotations

from guardian.cognition.prompts import build_context_system_message_with_meta


def test_connector_context_renders_as_distinct_section() -> None:
    bundle = {
        "semantic": [{"content": "semantic hit"}],
        "memory": [{"text": "memory hit"}],
        "graph": [{"text": "graph hit"}],
        "federated": [{"content": "federated hit"}],
        "connector_context": [
            {
                "connector_id": "obsidian",
                "query_text": "memory decay",
                "title": "Decay Note",
                "snippet": "Obsidian connector snippet",
                "metadata": {"filename": "note.md"},
                "score": 0.93,
            }
        ],
    }

    message, meta = build_context_system_message_with_meta(bundle)

    assert message is not None
    assert "**Connector Context: Obsidian**" in message
    assert "Obsidian connector snippet" in message
    assert "**Semantic Context:**" in message
    assert "**Memory Context:**" in message
    assert "**Graph Context:**" in message
    assert "**Federated Context:**" in message
    assert meta["connector_context"]["count"] == 1
    assert meta["connector_context"]["injected"] is True
    assert meta["connector_context"]["connectors"] == {"obsidian": 1}
    assert meta["semantic"]["injected"] is True
    assert meta["memory"]["injected"] is True
    assert meta["graph"]["injected"] is True
    assert meta["federated"]["injected"] is True


def test_empty_connector_context_does_not_render_section() -> None:
    bundle = {
        "semantic": [{"content": "semantic hit"}],
        "connector_context": [],
    }

    message, meta = build_context_system_message_with_meta(bundle)

    assert message is not None
    assert "**Connector Context:" not in message
    assert "**Semantic Context:**" in message
    assert meta["connector_context"]["count"] == 0
    assert meta["connector_context"]["injected"] is False
