"""Canonical Project ownership and bounded legacy-envelope classification.

``projects.user_id`` is the sole durable ownership authority.  The legacy
description envelope is inspected only so old rows can recover their human
description and be classified for safe migration; it never supplies or
overrides an owner.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping

LEGACY_PROJECT_OWNER_SENTINEL = "__codexify_project_owner__"

CANONICAL_COLUMN_ONLY = "canonical_column_only"
MATCHING_LEGACY_ENVELOPE = "matching_legacy_envelope"
PROJECT_OWNERSHIP_AUTHORITY_CONFLICT = "project_ownership_authority_conflict"
LEGACY_LOCAL_OWNER = "legacy_local_owner"

ENVELOPE_ABSENT = "absent"
ENVELOPE_MATCHING = "matching"
ENVELOPE_CONFLICTING = "conflicting"


def _row_value(row: Any, field: str) -> Any:
    if row is None:
        return None
    if isinstance(row, Mapping):
        return row.get(field)
    return getattr(row, field, None)


@dataclass(frozen=True)
class ProjectOwnershipClassification:
    """Bounded compatibility result with no request-identity input."""

    classification: str
    canonical_owner_id: str
    human_description: str
    legacy_envelope_state: str
    legacy_owner_id: str | None = None

    @property
    def has_legacy_envelope(self) -> bool:
        return self.legacy_envelope_state != ENVELOPE_ABSENT

    @property
    def has_matching_legacy_envelope(self) -> bool:
        return self.legacy_envelope_state == ENVELOPE_MATCHING

    @property
    def has_authority_conflict(self) -> bool:
        return self.classification == PROJECT_OWNERSHIP_AUTHORITY_CONFLICT


def classify_project_ownership(
    project: Any,
) -> ProjectOwnershipClassification:
    """Classify one Project using only its persisted canonical row values.

    Malformed JSON and JSON without the exact legacy sentinel remain ordinary
    user-visible description content.  Human description text from a genuine
    envelope is returned byte-for-byte as decoded by ``json.loads``; it is not
    stripped or otherwise reinterpreted.
    """

    canonical_owner_id = str(_row_value(project, "user_id") or "").strip()
    raw_description = _row_value(project, "description")
    description_text = "" if raw_description is None else str(raw_description)

    try:
        payload = json.loads(description_text)
    except (TypeError, ValueError, json.JSONDecodeError):
        payload = None

    if (
        not isinstance(payload, dict)
        or payload.get(LEGACY_PROJECT_OWNER_SENTINEL) is not True
    ):
        classification = (
            LEGACY_LOCAL_OWNER
            if canonical_owner_id == "local"
            else CANONICAL_COLUMN_ONLY
        )
        return ProjectOwnershipClassification(
            classification=classification,
            canonical_owner_id=canonical_owner_id,
            human_description=description_text,
            legacy_envelope_state=ENVELOPE_ABSENT,
        )

    legacy_owner_id = str(payload.get("owner_user_id") or "").strip() or None
    decoded_description = payload.get("description")
    human_description = "" if decoded_description is None else str(decoded_description)

    if legacy_owner_id != canonical_owner_id:
        return ProjectOwnershipClassification(
            classification=PROJECT_OWNERSHIP_AUTHORITY_CONFLICT,
            canonical_owner_id=canonical_owner_id,
            human_description=human_description,
            legacy_envelope_state=ENVELOPE_CONFLICTING,
            legacy_owner_id=legacy_owner_id,
        )

    classification = (
        LEGACY_LOCAL_OWNER
        if canonical_owner_id == "local"
        else MATCHING_LEGACY_ENVELOPE
    )
    return ProjectOwnershipClassification(
        classification=classification,
        canonical_owner_id=canonical_owner_id,
        human_description=human_description,
        legacy_envelope_state=ENVELOPE_MATCHING,
        legacy_owner_id=legacy_owner_id,
    )


def project_row_for_presentation(
    project: Any,
    classification: ProjectOwnershipClassification | None = None,
) -> dict[str, Any]:
    """Return a detached Project row with compatibility description recovery."""

    if isinstance(project, Mapping):
        row = dict(project)
    else:
        row = {
            field: _row_value(project, field)
            for field in (
                "id",
                "user_id",
                "name",
                "description",
                "icon",
                "identity_depth",
                "system_role",
                "archived_at",
                "created_at",
                "updated_at",
            )
            if _row_value(project, field) is not None
        }
    result = classification or classify_project_ownership(project)
    if result.has_legacy_envelope:
        row["description"] = result.human_description
    row.pop("owner_user_id", None)
    return row
