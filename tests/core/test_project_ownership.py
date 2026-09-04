from __future__ import annotations

import inspect
import json

from guardian.core.project_ownership import (
    CANONICAL_COLUMN_ONLY,
    ENVELOPE_ABSENT,
    ENVELOPE_CONFLICTING,
    ENVELOPE_MATCHING,
    LEGACY_LOCAL_OWNER,
    MATCHING_LEGACY_ENVELOPE,
    PROJECT_OWNERSHIP_AUTHORITY_CONFLICT,
    classify_project_ownership,
    project_row_for_presentation,
)


def _envelope(owner_id: str, description: str) -> str:
    return json.dumps(
        {
            "__codexify_project_owner__": True,
            "owner_user_id": owner_id,
            "description": description,
        },
        ensure_ascii=False,
        sort_keys=True,
    )


def test_canonical_column_only_plain_description() -> None:
    result = classify_project_ownership(
        {"user_id": "account-a", "description": "Plain human text"}
    )

    assert result.classification == CANONICAL_COLUMN_ONLY
    assert result.canonical_owner_id == "account-a"
    assert result.human_description == "Plain human text"
    assert result.legacy_envelope_state == ENVELOPE_ABSENT


def test_matching_envelope_recovers_description_exactly() -> None:
    description = "  Leading, trailing, and unicode: café\nsecond line  "
    project = {
        "id": 7,
        "user_id": "account-a",
        "description": _envelope("account-a", description),
    }

    result = classify_project_ownership(project)

    assert result.classification == MATCHING_LEGACY_ENVELOPE
    assert result.legacy_envelope_state == ENVELOPE_MATCHING
    assert result.has_matching_legacy_envelope is True
    assert result.human_description == description
    assert project_row_for_presentation(project, result)["description"] == description


def test_conflicting_envelope_never_selects_a_winner() -> None:
    result = classify_project_ownership(
        {
            "user_id": "canonical-owner",
            "description": _envelope("embedded-owner", "description"),
        }
    )

    assert result.classification == PROJECT_OWNERSHIP_AUTHORITY_CONFLICT
    assert result.legacy_envelope_state == ENVELOPE_CONFLICTING
    assert result.has_authority_conflict is True
    assert result.canonical_owner_id == "canonical-owner"
    assert result.legacy_owner_id == "embedded-owner"


def test_local_column_only_is_deferred_legacy_owner() -> None:
    result = classify_project_ownership(
        {"user_id": "local", "description": "Local description"}
    )

    assert result.classification == LEGACY_LOCAL_OWNER
    assert result.legacy_envelope_state == ENVELOPE_ABSENT
    assert result.canonical_owner_id == "local"


def test_local_matching_envelope_is_deferred_but_safe_to_unwrap() -> None:
    result = classify_project_ownership(
        {
            "user_id": "local",
            "description": _envelope("local", "  exact local text  "),
        }
    )

    assert result.classification == LEGACY_LOCAL_OWNER
    assert result.legacy_envelope_state == ENVELOPE_MATCHING
    assert result.has_matching_legacy_envelope is True
    assert result.human_description == "  exact local text  "


def test_local_conflicting_envelope_is_blocking_conflict() -> None:
    result = classify_project_ownership(
        {
            "user_id": "local",
            "description": _envelope("account-a", "description"),
        }
    )

    assert result.classification == PROJECT_OWNERSHIP_AUTHORITY_CONFLICT
    assert result.legacy_envelope_state == ENVELOPE_CONFLICTING


def test_malformed_and_non_envelope_json_remain_description_content() -> None:
    descriptions = (
        '{"__codexify_project_owner__": true',
        '{"owner_user_id": "account-b", "description": "ordinary json"}',
        '{"__codexify_project_owner__": false, "owner_user_id": "account-b"}',
    )

    for description in descriptions:
        result = classify_project_ownership(
            {"user_id": "account-a", "description": description}
        )
        assert result.classification == CANONICAL_COLUMN_ONLY
        assert result.legacy_envelope_state == ENVELOPE_ABSENT
        assert result.human_description == description


def test_classifier_has_no_authenticated_identity_input() -> None:
    assert tuple(inspect.signature(classify_project_ownership).parameters) == (
        "project",
    )

    result = classify_project_ownership(
        {
            "user_id": "account-a",
            "description": _envelope("account-b", "description"),
            "authenticated_account_id": "account-b",
        }
    )
    assert result.classification == PROJECT_OWNERSHIP_AUTHORITY_CONFLICT
    assert result.canonical_owner_id == "account-a"
