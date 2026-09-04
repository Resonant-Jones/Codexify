"""Remove redundant Project ownership envelopes from descriptions.

Classifies every Project before mutating any row.  A conflicting legacy
envelope aborts the revision; matching envelopes are then replaced with their
exact decoded human descriptions.  Canonical ownership in ``projects.user_id``
and every Project/thread identity and relationship remain unchanged.

Revision ID: c3d9e4f6a8b1
Revises: b2c8d0e3f5a7
Create Date: 2026-09-04 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op

from guardian.core.project_ownership import (
    PROJECT_OWNERSHIP_AUTHORITY_CONFLICT,
    ProjectOwnershipClassification,
    classify_project_ownership,
)

revision: str = "c3d9e4f6a8b1"
down_revision: str | Sequence[str] | None = "b2c8d0e3f5a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _classify_projects(
    connection,
) -> list[tuple[dict[str, object], ProjectOwnershipClassification]]:
    rows = (
        connection.execute(
            sa.text("SELECT id, user_id, description FROM projects ORDER BY id")
        )
        .mappings()
        .all()
    )
    classified = [(dict(row), classify_project_ownership(row)) for row in rows]
    if any(result.has_authority_conflict for _, result in classified):
        raise RuntimeError(PROJECT_OWNERSHIP_AUTHORITY_CONFLICT)
    return classified


def upgrade() -> None:
    """Safely unwrap matching envelopes after a complete conflict scan."""

    connection = op.get_bind()
    classified = _classify_projects(connection)

    for row, result in classified:
        if not result.has_matching_legacy_envelope:
            continue
        connection.execute(
            sa.text(
                "UPDATE projects SET description = :description WHERE id = :project_id"
            ),
            {
                "description": result.human_description,
                "project_id": row["id"],
            },
        )


def downgrade() -> None:
    """No-op: never recreate a legacy Project ownership authority envelope."""

    return None
