from __future__ import annotations

from guardian.core.chat_completion_service import (
    _filter_image_refusal_semantic_context,
    _should_skip_history_message_for_image_turn,
)


def test_image_turn_skips_prior_assistant_refusal_message() -> None:
    latest_user_meta = {
        "attachments": [
            {
                "kind": "image",
                "id": "img-1",
                "src": "/media/images/img-1.png",
                "name": "img-1.png",
            }
        ]
    }
    message = {
        "role": "assistant",
        "content": (
            "Since I can't view images directly, I'll focus on what you might "
            "be feeling instead."
        ),
    }

    assert _should_skip_history_message_for_image_turn(
        message, latest_user_meta
    )


def test_non_refusal_history_message_is_preserved() -> None:
    latest_user_meta = {
        "attachments": [
            {
                "kind": "image",
                "id": "img-1",
                "src": "/media/images/img-1.png",
                "name": "img-1.png",
            }
        ]
    }

    assert not _should_skip_history_message_for_image_turn(
        {
            "role": "assistant",
            "content": "I can help describe the colors and shapes if you want.",
        },
        latest_user_meta,
    )


def test_history_filter_is_noop_without_image_attachments() -> None:
    assert not _should_skip_history_message_for_image_turn(
        {
            "role": "assistant",
            "content": "Since I can't view images directly, I'll focus on text.",
        },
        {"attachments": []},
    )


def test_image_turn_filters_refusal_snippets_from_semantic_context() -> None:
    latest_user_meta = {
        "attachments": [
            {
                "kind": "image",
                "id": "img-1",
                "src": "/media/images/img-1.png",
                "name": "img-1.png",
            }
        ]
    }
    semantic_items = [
        {
            "id": "doc-1",
            "snippet": "Since I can't view images directly, I'll focus on general terms.",
        },
        {
            "id": "doc-2",
            "snippet": "Useful design feedback: increase contrast and reduce clutter.",
        },
    ]

    filtered = _filter_image_refusal_semantic_context(
        semantic_items, latest_user_meta
    )

    assert filtered == [semantic_items[1]]
