from __future__ import annotations

from guardian.core import chat_completion_service


def test_image_turn_refusal_history_is_skipped_only_when_images_exist() -> None:
    latest_user_meta = {
        "attachments": [
            {
                "kind": "image",
                "src": "https://example.test/image.png",
                "name": "Test.png",
            }
        ]
    }
    refusal_message = {
        "role": "assistant",
        "content": "I cannot directly view the image.",
    }
    non_refusal_message = {
        "role": "assistant",
        "content": "I can help with that.",
    }

    assert chat_completion_service._should_skip_history_message_for_image_turn(
        refusal_message,
        latest_user_meta,
    )
    assert not chat_completion_service._should_skip_history_message_for_image_turn(
        non_refusal_message,
        latest_user_meta,
    )
    assert not chat_completion_service._should_skip_history_message_for_image_turn(
        refusal_message,
        None,
    )


def test_image_turn_refusal_semantic_context_is_filtered() -> None:
    latest_user_meta = {
        "attachments": [
            {
                "kind": "image",
                "src": "https://example.test/image.png",
                "name": "Test.png",
            }
        ]
    }
    semantic_items = [
        {
            "content": "I cannot see the image directly.",
            "label": "refusal",
        },
        {
            "content": "This chart looks like a rising trend.",
            "label": "signal",
        },
        {"content": "plain text fallback", "label": "fallback"},
    ]

    filtered = chat_completion_service._filter_image_refusal_semantic_context(
        semantic_items,
        latest_user_meta,
    )

    assert [item["label"] for item in filtered] == ["signal", "fallback"]


def test_non_image_turn_context_is_left_alone() -> None:
    semantic_items = [
        {"content": "I cannot see the image directly.", "label": "refusal"},
        {"content": "This chart looks like a rising trend.", "label": "signal"},
    ]

    filtered = chat_completion_service._filter_image_refusal_semantic_context(
        semantic_items,
        None,
    )

    assert [item["label"] for item in filtered] == ["refusal", "signal"]
