from __future__ import annotations

from guardian.cognition.prompts import (
    _rag_hint_block,
    build_context_system_message_with_meta,
)


def _fact(
    *,
    key: str,
    value: str,
    status: str = "verified",
    is_active: bool = True,
) -> dict[str, object]:
    return {
        "key": key,
        "value": value,
        "status": status,
        "confidence": 0.9,
        "is_active": is_active,
    }


def test_personal_facts_render_into_context_system_message_when_present():
    bundle = {
        "personal_facts": [
            _fact(key="location", value="NYC"),
            _fact(key="occupation", value="software engineer"),
        ]
    }

    message, meta = build_context_system_message_with_meta(bundle)

    assert message is not None
    assert "Personal Facts:" in message
    assert "- location: NYC" in message
    assert "- occupation: software engineer" in message
    assert meta["personal_facts"]["count"] == 2
    assert meta["personal_facts"]["injected"] is True


def test_no_personal_facts_block_is_rendered_when_absent():
    bundle = {"semantic": [{"text": "project note"}]}

    message, meta = build_context_system_message_with_meta(bundle)

    assert message is not None
    assert "Personal Facts:" not in message
    assert meta["personal_facts"]["count"] == 0
    assert meta["personal_facts"]["injected"] is False


def test_rendered_personal_facts_exclude_non_verified_entries():
    bundle = {
        "personal_facts": [
            _fact(key="location", value="candidate-town", status="candidate"),
            _fact(key="occupation", value="disputed-role", status="disputed"),
            _fact(
                key="timezone",
                value="retired-zone",
                status="verified",
                is_active=False,
            ),
            _fact(key="home_base", value="NYC"),
        ]
    }

    message, meta = build_context_system_message_with_meta(bundle)

    assert message is not None
    assert "Personal Facts:" in message
    assert "- home_base: NYC" in message
    assert "candidate-town" not in message
    assert "disputed-role" not in message
    assert "retired-zone" not in message
    assert meta["personal_facts"]["count"] == 1
    assert meta["personal_facts"]["injected"] is True


def test_rag_hint_block_truthful_about_personal_fact_availability():
    available_bundle = {"personal_facts": [_fact(key="location", value="NYC")]}
    available_result = _rag_hint_block(available_bundle)

    assert "Verified personal facts are available." in available_result
    assert (
        "Semantic/doc context was not retrieved for this turn."
        in available_result
    )
    assert (
        "Personal-memory evidence was not retrieved for this turn."
        in available_result
    )
    assert "Graph context was unavailable for this turn." in available_result

    unavailable_bundle = {"semantic": [{"text": "project note"}]}
    unavailable_result = _rag_hint_block(unavailable_bundle)

    assert (
        "Verified personal facts were not retrieved for this turn."
        in unavailable_result
    )
