"""make uploaded_documents.project_id required and canonicalize default project

Revision ID: d1a6b9f2c4e7
Revises: b7c1d9e0f2a3
Create Date: 2026-02-21

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d1a6b9f2c4e7"
down_revision: str | Sequence[str] | None = "b7c1d9e0f2a3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


DEFAULT_PROJECT_NAME = "General"
DEFAULT_PROJECT_DESCRIPTION = (
    "Default bucket for unassigned threads and documents"
)


def _resolve_default_project_id(bind) -> int:
    general_id = bind.execute(
        sa.text(
            """
            SELECT id
            FROM projects
            WHERE lower(trim(name)) = lower(:name)
            ORDER BY id ASC
            LIMIT 1
            """
        ),
        {"name": DEFAULT_PROJECT_NAME},
    ).scalar()
    if general_id is not None:
        return int(general_id)

    loose_id = bind.execute(
        sa.text(
            """
            SELECT id
            FROM projects
            WHERE lower(trim(name)) = 'loose threads'
            ORDER BY id ASC
            LIMIT 1
            """
        )
    ).scalar()
    if loose_id is not None:
        bind.execute(
            sa.text(
                """
                UPDATE projects
                SET name = :name,
                    description = COALESCE(NULLIF(description, ''), :description)
                WHERE id = :project_id
                """
            ),
            {
                "name": DEFAULT_PROJECT_NAME,
                "description": DEFAULT_PROJECT_DESCRIPTION,
                "project_id": int(loose_id),
            },
        )
        return int(loose_id)

    bind.execute(
        sa.text(
            """
            INSERT INTO projects (name, description)
            VALUES (:name, :description)
            """
        ),
        {
            "name": DEFAULT_PROJECT_NAME,
            "description": DEFAULT_PROJECT_DESCRIPTION,
        },
    )
    inserted_id = bind.execute(
        sa.text(
            """
            SELECT id
            FROM projects
            WHERE lower(trim(name)) = lower(:name)
            ORDER BY id DESC
            LIMIT 1
            """
        ),
        {"name": DEFAULT_PROJECT_NAME},
    ).scalar()
    if inserted_id is None:
        raise RuntimeError(
            "Failed to resolve default project id during migration"
        )
    return int(inserted_id)


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    default_project_id = _resolve_default_project_id(bind)

    # Backfill legacy rows that were uploaded without project provenance.
    op.execute(
        sa.text(
            """
            UPDATE uploaded_documents
            SET project_id = :project_id
            WHERE project_id IS NULL
            """
        ),
        {"project_id": default_project_id},
    )

    op.alter_column(
        "uploaded_documents",
        "project_id",
        existing_type=sa.Integer(),
        nullable=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        "uploaded_documents",
        "project_id",
        existing_type=sa.Integer(),
        nullable=True,
    )
