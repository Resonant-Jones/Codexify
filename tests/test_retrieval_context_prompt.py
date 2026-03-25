from __future__ import annotations

from guardian.cognition.prompts import build_context_system_message_with_meta


def test_context_system_message_with_meta_injects_semantic_and_memory():
    bundle = {
        "semantic": [{"text": "foo"}],
        "memory": [
            {"text": "bar", "metadata": {"source_created_at": "2024-01-01"}}
        ],
        "graph": [{"text": "graph fact"}],
    }

    message, meta = build_context_system_message_with_meta(bundle)

    assert message is not None
    assert "Semantic Context" in message
    assert "Memory Context" in message
    assert "Graph Context" in message
    assert meta["semantic"]["injected"] is True
    assert meta["semantic"]["count"] == 1
    assert meta["memory"]["injected"] is True
    assert meta["memory"]["count"] == 1
    assert meta["graph"]["injected"] is True
    assert meta["graph"]["count"] == 1
