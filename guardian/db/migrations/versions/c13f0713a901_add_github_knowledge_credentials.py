"""add user-scoped GitHub Knowledge connection credentials

Revision ID: c13f0713a901
Revises: ab71d5ce9604
Create Date: 2026-11-13
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "c13f0713a901"
down_revision: str | Sequence[str] | None = "ab71d5ce9604"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the narrow non-OAuth token record for the GitHub Knowledge connection."""
    op.create_table(
        "github_knowledge_credentials",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("encrypted_token", sa.Text(), nullable=False),
        sa.Column(
            "repositories",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            nullable=False,
        ),
        sa.Column(
            "validation_status",
            sa.String(length=32),
            nullable=False,
            server_default="unvalidated",
        ),
        sa.Column("last_validated_at", sa.TIMESTAMP(timezone=True), nullable=True),
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
        sa.CheckConstraint(
            "validation_status IN "
            "('unvalidated', 'valid', 'authorization_error', "
            "'transport_error', 'provider_error')",
            name="ck_github_knowledge_credentials_validation_status",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_github_knowledge_credentials_user"),
    )


def downgrade() -> None:
    op.drop_table("github_knowledge_credentials")
