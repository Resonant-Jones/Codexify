"""add authenticated principals table

Revision ID: e3f2a1b4c5d6
Revises: 4c9d1e2f3a5b, d4e5f6a7b8c9
Create Date: 2026-04-12

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e3f2a1b4c5d6"
down_revision: str | Sequence[str] | None = (
    "4c9d1e2f3a5b",
    "d4e5f6a7b8c9",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "authenticated_principals",
        sa.Column("account_id", sa.String(length=255), nullable=False),
        sa.Column("subject_id", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("account_id"),
        sa.UniqueConstraint(
            "subject_id",
            name="uq_authenticated_principals_subject_id",
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("authenticated_principals")
