from guardian.cognition.prompts import build_context_system_message


def test_memory_context_renders_chronological_anchors():
    bundle = {
        "memory": [
            {
                "text": "First imported line",
                "metadata": {
                    "source_created_at": "2026-02-08T14:05:00+00:00",
                    "source_thread_id": "thread-abc",
                    "turn_index": 7,
                    "role": "assistant",
                },
            }
        ]
    }

    rendered = build_context_system_message(bundle)

    assert rendered is not None
    assert "**Memory Context:**" in rendered
    assert (
        "- [2026-02-08 14:05 | thread:thread-abc | turn:7 | assistant] "
        "First imported line"
    ) in rendered


def test_memory_context_uses_fallbacks_for_missing_fields():
    bundle = {
        "memory": [
            {
                "text": "Fallback line",
                "metadata": {
                    "imported_at": "2026-02-08T16:30:00+00:00",
                    "thread_id": 12,
                },
            },
            {
                "text": "Unknown line",
                "metadata": {},
            },
        ]
    }

    rendered = build_context_system_message(bundle)

    assert rendered is not None
    assert (
        "- [2026-02-08 16:30 | thread:12 | turn:? | role:unknown] "
        "Fallback line"
    ) in rendered
    assert (
        "- [timestamp:unknown | thread:unknown | turn:? | role:unknown] "
        "Unknown line"
    ) in rendered
