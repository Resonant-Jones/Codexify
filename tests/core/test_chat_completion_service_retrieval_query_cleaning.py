from __future__ import annotations

from guardian.core.chat_completion_service import _clean_retrieval_query


def test_clean_retrieval_query_strips_sender_tag_and_guardian_mention() -> None:
    assert (
        _clean_retrieval_query(
            "[Ada]: please explain @guardian how project scope works"
        )
        == "please explain how project scope works"
    )


def test_clean_retrieval_query_returns_empty_string_for_missing_input() -> None:
    assert _clean_retrieval_query(None) == ""
