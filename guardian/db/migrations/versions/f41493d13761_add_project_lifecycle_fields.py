"""add project lifecycle fields

Revision ID: f41493d13761
Revises: 9c66e490a42b
Create Date: 2026-08-30 09:16:14.751151

"""
from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f41493d13761"
down_revision: str | Sequence[str] | None = "9c66e490a42b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "projects", sa.Column("system_role", sa.String(length=32), nullable=True)
    )
    op.add_column(
        "projects",
        sa.Column("archived_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )

    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            UPDATE projects
            SET system_role = 'general'
            WHERE name = 'General'
              AND system_role IS NULL
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE projects
            SET system_role = 'imports'
            WHERE name = 'Imports'
              AND system_role IS NULL
            """
        )
    )

    op.create_check_constraint(
        "projects_system_role_check",
        "projects",
        "system_role IS NULL OR system_role IN ('general','imports')",
    )
    op.create_index(
        "uq_projects_user_id_system_role",
        "projects",
        ["user_id", "system_role"],
        unique=True,
        postgresql_where=sa.text("system_role IS NOT NULL"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("uq_projects_user_id_system_role", table_name="projects")
    op.drop_constraint(
        "projects_system_role_check", "projects", type_="check"
    )
    op.drop_column("projects", "archived_at")
    op.drop_column("projects", "system_role")
