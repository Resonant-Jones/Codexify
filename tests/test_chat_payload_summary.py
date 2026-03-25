from __future__ import annotations

from guardian.core.chat_completion_service import (
    build_sanitized_payload_summary,
)


def test_build_sanitized_payload_summary_counts_and_sanitizes():
    messages = [
        {"role": "system", "content": "=== IMPRINT_ZERO ===\nPersona guidance"},
        {"role": "user", "content": "User secret message"},
        {"role": "assistant", "content": "Assistant reply"},
    ]
    bundle = {
        "semantic": [{"id": 1}, {"id": 2}],
        "memory": [{"id": 10}],
        "graph": [{"id": "g1"}],
        "docs": {"thread": [{"title": "Doc1"}]},
        "user_system_override": "override block",
    }

    summary = build_sanitized_payload_summary(
        messages, bundle, provider="groq", model="llama3"
    )

    assert summary["has_system_prompt"] is True
    assert summary["persona_or_imprint_present"] is True
    assert summary["message_count"] == 3
    assert summary["semantic_count"] == 2
    assert summary["memory_count"] == 1
    assert summary["graph_count"] == 1
    assert summary["linked_document_count"] == 1
    assert summary["has_user_system_override"] is True
    assert summary["resolved_provider"] == "groq"
    assert summary["resolved_model"] == "llama3"
    assert summary["payload_char_count"] > 0
    assert summary["payload_estimated_tokens"] >= 1

    # Ensure no raw payload text is echoed back.
    for value in summary.values():
        if isinstance(value, str):
            assert "User secret message" not in value
            assert "Assistant reply" not in value
