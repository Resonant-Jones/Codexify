from __future__ import annotations

from guardian.core import chat_completion_service
from guardian.protocol_tokens import TraceSuppressionReason


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
    assert (
        not chat_completion_service._should_skip_history_message_for_image_turn(
            non_refusal_message,
            latest_user_meta,
        )
    )
    assert (
        not chat_completion_service._should_skip_history_message_for_image_turn(
            refusal_message,
            None,
        )
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

    (
        filtered,
        suppression,
    ) = chat_completion_service._filter_image_refusal_semantic_context(
        semantic_items,
        latest_user_meta,
    )

    assert [item["label"] for item in filtered] == ["signal", "fallback"]
    assert suppression is not None
    assert suppression["count"] == 1
    assert suppression["items"][0]["suppression_reason"] == (
        TraceSuppressionReason.ASSISTANT_VISION_REFUSAL_ON_IMAGE_TURN.value
    )


def test_non_image_turn_context_is_left_alone() -> None:
    semantic_items = [
        {"content": "I cannot see the image directly.", "label": "refusal"},
        {"content": "This chart looks like a rising trend.", "label": "signal"},
    ]

    (
        filtered,
        suppression,
    ) = chat_completion_service._filter_image_refusal_semantic_context(
        semantic_items,
        None,
    )

    assert [item["label"] for item in filtered] == ["refusal", "signal"]
    assert suppression is None


def test_image_turn_refusal_semantic_context_records_suppression_trace() -> (
    None
):
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
            "content": "I can't view the image.",
            "label": "refusal",
            "source_type": "semantic_context",
            "role": "assistant",
            "thread_id": 17,
            "project_id": 8,
            "retrieval_lane": "semantic",
            "score": 0.12,
            "policy_reason": "assistant_vision_refusal_on_image_turn",
        },
        {
            "content": "This chart looks like a rising trend.",
            "label": "signal",
        },
    ]
    suppression_trace: dict[str, object] = {}

    filtered = chat_completion_service._filter_image_refusal_semantic_context(
        semantic_items,
        latest_user_meta,
        suppression_trace=suppression_trace,
    )

    assert [item["label"] for item in filtered] == ["signal"]
    assert suppression_trace["summary"] == {
        "total_suppressed": 1,
        "assistant_vision_refusal_on_image_turn": 1,
    }
    assert suppression_trace["items"] == [
        {
            "suppressed": True,
            "suppression_reason": "assistant_vision_refusal_on_image_turn",
            "source_type": "semantic_context",
            "role": "assistant",
            "thread_id": 17,
            "project_id": 8,
            "retrieval_lane": "semantic",
            "score": 0.12,
            "policy_reason": "assistant_vision_refusal_on_image_turn",
        }
    ]
