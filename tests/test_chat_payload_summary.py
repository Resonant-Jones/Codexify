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
        "obsidian": [{"id": "o1"}],
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
    assert summary["obsidian_count"] == 1
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


def test_payload_summary_retrieval_injection_flags():
    messages = [
        {"role": "system", "content": "=== BASE SYSTEM ==="},
        {"role": "system", "content": "**Semantic Context:**\n- item"},
    ]

    bundle = {
        "semantic": [{"text": "doc1"}, {"text": "doc2"}],
        "obsidian": [{"text": "obsidian note"}],
        "memory": [{"text": "mem"}],
        "graph": [],
        "docs": {"thread": [{"title": "T1"}]},
        "_prompt_meta": {
            "context": {
                "semantic": {"count": 2, "injected": True},
                "memory": {"count": 1, "injected": False},
                "graph": {"count": 0, "injected": False},
                "federated": {"count": 0, "injected": False},
            },
            "docs": {"count": 1, "injected": True},
        },
    }

    summary = build_sanitized_payload_summary(
        messages, bundle, provider="groq", model="llama3"
    )

    assert summary["semantic_injected"] is True
    assert summary["obsidian_injected"] is True
    assert summary["memory_injected"] is False
    assert summary["linked_document_injected"] is True
    assert summary["retrieval_injected"] is True
    assert summary["semantic_count"] == 2
    assert summary["memory_count"] == 1
